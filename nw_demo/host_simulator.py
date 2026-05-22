from __future__ import annotations

import asyncio
from typing import Any

from . import config
from .base import BaseNode
from .messages import iso_now


class HostSimulator(BaseNode):
    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        controller_host: str,
        controller_port: int,
        control_token: str | None = None,
    ) -> None:
        super().__init__("host-simulator", listen_host, listen_port, controller_host, controller_port, control_token)
        self._tick = 0
        self._fault_type: str | None = None
        self._fault_end_monotonic: float | None = None
        self.state: dict[str, Any] = {}
        self._run_task: asyncio.Task[Any] | None = None
        self._apply_normal_state()

    def _configure_default_traffic_peers(self) -> None:
        self.record_peer_state("previous_peer", peer_node_id="local-agent", peer_role="agent", hop_state="unknown")
        self.record_peer_state("next_peer", hop_state="not_applicable")

    async def start(self) -> None:
        await self.start_background()
        self._run_task = asyncio.create_task(self._run_loop(), name="host-simulator-run")
        self._tasks.append(self._run_task)

    async def reset_state(self) -> None:
        await super().reset_state()
        self._tick = 0
        self._fault_type = None
        self._fault_end_monotonic = None
        self._apply_normal_state()

    async def on_control(self, message: dict[str, Any]) -> None:
        await super().on_control(message)
        if message.get("command") == "set_fault":
            params = message.get("params", {})
            enabled = bool(params.get("enabled", True))
            fault_type = params.get("fault_type")
            if enabled:
                self._fault_type = str(fault_type)
                self._fault_end_monotonic = None
                self._apply_fault_state(self._fault_type)
                await self.publish_status(note=f"fault 켜짐: {self._fault_type}")
                return
            if self._fault_type == fault_type or fault_type in {None, "all"}:
                self._fault_type = None
                self._fault_end_monotonic = None
                self._apply_normal_state()
            await self.publish_status(note=f"fault 꺼짐: {fault_type}")
            return
        if message.get("command") != "inject_fault":
            return
        params = message.get("params", {})
        self._fault_type = params.get("fault_type")
        try:
            duration_sec = int(params.get("duration_sec", 6))
        except (TypeError, ValueError):
            await self.publish_status(note="fault duration 파라미터 오류")
            return
        self._fault_end_monotonic = asyncio.get_running_loop().time() + duration_sec
        self._apply_fault_state(str(self._fault_type))
        await self.publish_status(note=f"fault 주입: {self._fault_type}")

    def snapshot(self) -> dict[str, Any]:
        return dict(self.state)

    async def publish_status(self, extra: dict[str, Any] | None = None, note: str | None = None) -> None:
        host_state = self.snapshot()
        payload = {
            "host_state": host_state,
            "detail": {
                "role": "host",
                "tick": self._tick,
                "fault_active": self._fault_type is not None,
                "fault_type": self._fault_type,
                "host_state": host_state,
                "traffic": self.traffic_snapshot(),
            },
        }
        if extra:
            payload.update(extra)
        await super().publish_status(extra=payload, note=note)

    async def handle_network_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if message.get("kind") == "get_host_state":
            response = {"kind": "host_state", "host_state": self.snapshot()}
            self.record_peer_message(
                "previous_peer",
                "last_received",
                message,
                peer_node_id="local-agent",
                peer_role="agent",
                hop_state="request_received",
                logical_id="get_host_state",
                phase="host_request",
            )
            self.record_peer_message(
                "previous_peer",
                "last_sent",
                response,
                peer_node_id="local-agent",
                peer_role="agent",
                hop_state="acknowledged",
                logical_id="get_host_state",
                phase="host_response",
            )
            return response
        return await super().handle_network_message(message)

    def _apply_normal_state(self) -> None:
        phase = self._tick % 4
        self.state = {
            "host_id": config.HOST_ID,
            "cpu_usage": 18 + (phase * 4),
            "memory_usage": 42 + (phase * 3),
            "service_state": "UP",
            "latency_ms": 24 + (phase * 6),
            "last_update_time": iso_now(),
        }

    def _apply_fault_state(self, fault_type: str) -> None:
        self._apply_normal_state()
        if fault_type == "CPU_SPIKE":
            self.state.update({"cpu_usage": 96})
        elif fault_type == "SERVICE_DOWN":
            self.state.update({"service_state": "DOWN"})
        elif fault_type == "LATENCY_HIGH":
            self.state.update({"latency_ms": 260})
        self.state["last_update_time"] = iso_now()

    async def _run_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while not self.stopped:
            if self.running:
                self._tick += 1
                if self._fault_type and (self._fault_end_monotonic is None or loop.time() < self._fault_end_monotonic):
                    self._apply_fault_state(self._fault_type)
                else:
                    self._fault_type = None
                    self._apply_normal_state()
                await self.publish_status(note=f"호스트 tick {self._tick}")
            await asyncio.sleep(config.TICK_SECONDS)
