from __future__ import annotations

import asyncio
from typing import Any

from . import config
from .base import BaseNode
from .messages import iso_now, json_roundtrip
from .transport import send_request


class LocalAgent(BaseNode):
    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        controller_host: str,
        controller_port: int,
        host_host: str,
        host_port: int,
        downstream_host: str,
        downstream_port: int,
        control_token: str | None = None,
    ) -> None:
        super().__init__("local-agent", listen_host, listen_port, controller_host, controller_port, control_token)
        self.host_host = host_host
        self.host_port = host_port
        self.downstream_host = downstream_host
        self.downstream_port = downstream_port
        self.seq_no = 0
        self.last_fault_signature: str | None = None
        self.last_host_state_signature: tuple[object, ...] | None = None
        self.latest_input_state: dict[str, Any] | None = None
        self.latest_input_result: dict[str, Any] | None = None
        self.last_detected_fault: str | None = None
        self.last_emitted_event: dict[str, Any] | None = None
        self.last_downstream_result: dict[str, Any] | None = None
        self._run_task: asyncio.Task[Any] | None = None

    def _configure_default_traffic_peers(self) -> None:
        self.record_peer_state("previous_peer", peer_node_id="host-simulator", peer_role="host", hop_state="unknown")
        self.record_peer_state("next_peer", peer_node_id="r1", peer_role="relay", hop_state="idle", failure_reason="no_fault")

    async def start(self) -> None:
        await self.start_background()
        self._run_task = asyncio.create_task(self._run_loop(), name="local-agent-run")
        self._tasks.append(self._run_task)

    async def reset_state(self) -> None:
        await super().reset_state()
        self.seq_no = 0
        self.last_fault_signature = None
        self.last_host_state_signature = None
        self.latest_input_state = None
        self.latest_input_result = None
        self.last_detected_fault = None
        self.last_emitted_event = None
        self.last_downstream_result = None

    async def publish_status(self, extra: dict[str, Any] | None = None, note: str | None = None) -> None:
        payload = self._status_extra()
        if extra:
            payload.update(extra)
        await super().publish_status(extra=payload, note=note)

    def _status_extra(self) -> dict[str, Any]:
        detail = {
            "role": "agent",
            "latest_input_state": json_roundtrip(self.latest_input_state) if self.latest_input_state else None,
            "latest_input_result": json_roundtrip(self.latest_input_result) if self.latest_input_result else None,
            "detected_fault": self.last_detected_fault,
            "emitted_event": json_roundtrip(self.last_emitted_event) if self.last_emitted_event else None,
            "downstream_result": json_roundtrip(self.last_downstream_result) if self.last_downstream_result else None,
            "traffic": self.traffic_snapshot(),
        }
        payload: dict[str, Any] = {"detail": detail}
        if self.last_emitted_event is not None:
            payload["last_event"] = json_roundtrip(self.last_emitted_event)
        return payload

    def _detect_fault(self, host_state: dict[str, Any]) -> str | None:
        if host_state["cpu_usage"] >= 90:
            return "CPU_SPIKE"
        if host_state["service_state"] != "UP":
            return "SERVICE_DOWN"
        if host_state["latency_state"] == "HIGH":
            return "LATENCY_HIGH"
        return None

    def _host_state_signature(self, host_state: dict[str, Any]) -> tuple[object, ...]:
        return (
            host_state.get("cpu_usage"),
            host_state.get("memory_usage"),
            host_state.get("service_state"),
            host_state.get("latency_state"),
            host_state.get("latency_ms"),
            host_state.get("fault_mode"),
        )

    def _select_event_type(self, host_state: dict[str, Any], detected_fault: str | None) -> str | None:
        host_state_signature = self._host_state_signature(host_state)
        if detected_fault is not None:
            if detected_fault == self.last_fault_signature:
                return None
            return detected_fault
        if host_state_signature != self.last_host_state_signature:
            return "HOST_STATE_UPDATE"
        return None

    def _build_event(self, event_type: str, host_state: dict[str, Any]) -> dict[str, Any]:
        self.seq_no += 1
        if event_type == "HOST_STATE_UPDATE":
            severity = "INFO"
        else:
            severity = "ERROR" if event_type == "SERVICE_DOWN" else "WARN"
        return json_roundtrip(
            {
                "msg_type": "EVENT",
                "event_id": f"evt-{config.HOST_ID}-{self.seq_no}",
                "seq_no": self.seq_no,
                "host_id": config.HOST_ID,
                "agent_id": config.AGENT_ID,
                "event_type": event_type,
                "severity": severity,
                "timestamp": iso_now(),
                "payload": {
                    "cpu": host_state["cpu_usage"],
                    "memory": host_state["memory_usage"],
                    "service_state": host_state["service_state"],
                    "latency_ms": host_state["latency_ms"],
                    "fault_mode": host_state["fault_mode"],
                },
            }
        )

    async def _run_loop(self) -> None:
        while not self.stopped:
            if self.running:
                try:
                    host_request = {"kind": "get_host_state"}
                    self.record_peer_message(
                        "previous_peer",
                        "last_sent",
                        host_request,
                        peer_node_id="host-simulator",
                        peer_role="host",
                        hop_state="request_sent",
                        logical_id="get_host_state",
                        phase="host_request",
                    )
                    response = await send_request(
                        self.host_host,
                        self.host_port,
                        host_request,
                        expect_response=True,
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    self.latest_input_result = {"status": "fetch_failed", "reason": "timeout", "source": "host"}
                    self.last_downstream_result = {"status": "not_attempted", "reason": "host_timeout"}
                    self.record_peer_state(
                        "previous_peer",
                        peer_node_id="host-simulator",
                        peer_role="host",
                        hop_state="timeout",
                        failure_reason="host_timeout",
                    )
                    await self.publish_status(note="host 상태 조회 실패")
                    await asyncio.sleep(config.AGENT_POLL_SECONDS)
                    continue
                except OSError:
                    self.latest_input_result = {"status": "fetch_failed", "reason": "connection_error", "source": "host"}
                    self.last_downstream_result = {"status": "not_attempted", "reason": "host_connection_error"}
                    self.record_peer_state(
                        "previous_peer",
                        peer_node_id="host-simulator",
                        peer_role="host",
                        hop_state="connection_error",
                        failure_reason="host_connection_error",
                    )
                    await self.publish_status(note="host 상태 조회 실패")
                    await asyncio.sleep(config.AGENT_POLL_SECONDS)
                    continue

                self.record_peer_message(
                    "previous_peer",
                    "last_received",
                    response,
                    peer_node_id="host-simulator",
                    peer_role="host",
                    hop_state="acknowledged",
                    logical_id="get_host_state",
                    phase="host_response",
                )

                host_state = response.get("host_state") if isinstance(response, dict) else None
                if not isinstance(host_state, dict):
                    self.latest_input_result = {"status": "invalid_response", "source": "host"}
                    self.last_downstream_result = {"status": "not_attempted", "reason": "invalid_host_state"}
                    self.record_peer_state(
                        "previous_peer",
                        peer_node_id="host-simulator",
                        peer_role="host",
                        hop_state="invalid_response",
                        failure_reason="invalid_host_state",
                    )
                    await self.publish_status(note="host 상태 응답 이상")
                    await asyncio.sleep(config.AGENT_POLL_SECONDS)
                    continue

                self.latest_input_state = json_roundtrip(host_state)
                self.latest_input_result = {"status": "ok", "source": "host"}
                detected_fault = self._detect_fault(host_state)
                self.last_detected_fault = detected_fault
                host_state_signature = self._host_state_signature(host_state)
                event_type = self._select_event_type(host_state, detected_fault)
                if event_type is None:
                    self.last_fault_signature = None
                    self.last_emitted_event = None
                    self.last_downstream_result = {"status": "idle", "reason": "no_fault"}
                    self.record_peer_state(
                        "next_peer",
                        peer_node_id="r1",
                        peer_role="relay",
                        hop_state="idle",
                        failure_reason="no_fault",
                    )
                elif detected_fault is None or detected_fault != self.last_fault_signature:
                    event = self._build_event(event_type, host_state)
                    self.last_emitted_event = json_roundtrip(event)
                    try:
                        self.record_peer_message(
                            "next_peer",
                            "last_sent",
                            event,
                            peer_node_id="r1",
                            peer_role="relay",
                            hop_state="request_sent",
                            logical_id=str(event["event_id"]),
                            attempt_no=1,
                            phase="event_forward",
                        )
                        response = await send_request(
                            self.downstream_host,
                            self.downstream_port,
                            event,
                            expect_response=True,
                            timeout=config.AGENT_DOWNSTREAM_RESPONSE_TIMEOUT_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        self.last_downstream_result = {
                            "status": "send_failed",
                            "reason": "timeout",
                            "event_id": event["event_id"],
                        }
                        self.record_peer_state(
                            "next_peer",
                            peer_node_id="r1",
                            peer_role="relay",
                            hop_state="timeout",
                            failure_reason="timeout",
                        )
                        await self.publish_status(note=f"{event['event_id']} 전송 실패")
                        await asyncio.sleep(config.AGENT_POLL_SECONDS)
                        continue
                    except OSError:
                        self.last_downstream_result = {
                            "status": "send_failed",
                            "reason": "connection_error",
                            "event_id": event["event_id"],
                        }
                        self.record_peer_state(
                            "next_peer",
                            peer_node_id="r1",
                            peer_role="relay",
                            hop_state="connection_error",
                            failure_reason="connection_error",
                        )
                        await self.publish_status(note=f"{event['event_id']} 전송 실패")
                        await asyncio.sleep(config.AGENT_POLL_SECONDS)
                        continue
                    if not isinstance(response, dict) or response.get("msg_type") != "ACK":
                        self.last_downstream_result = {
                            "status": "ack_missing",
                            "event_id": event["event_id"],
                            "response": json_roundtrip(response) if isinstance(response, dict) else None,
                        }
                        self.record_peer_message(
                            "next_peer",
                            "last_received",
                            response,
                            peer_node_id="r1",
                            peer_role="relay",
                            hop_state="invalid_response",
                            failure_reason="ack_missing",
                            logical_id=str(event["event_id"]),
                            attempt_no=1,
                            phase="downstream_response",
                        )
                        await self.publish_status(note=f"{event['event_id']} ACK 없음")
                        await asyncio.sleep(config.AGENT_POLL_SECONDS)
                        continue

                    self.record_peer_message(
                        "next_peer",
                        "last_received",
                        response,
                        peer_node_id="r1",
                        peer_role="relay",
                        hop_state="acknowledged",
                        logical_id=str(event["event_id"]),
                        attempt_no=1,
                        phase="downstream_ack",
                    )
                    self.last_fault_signature = detected_fault
                    self.last_host_state_signature = host_state_signature
                    self.last_downstream_result = {
                        "status": "acknowledged",
                        "event_id": event["event_id"],
                        "ack": json_roundtrip(response),
                    }
                    await self.publish_status(note=f"이벤트 생성 {event['event_id']}")
                else:
                    self.last_downstream_result = {
                        "status": "suppressed_duplicate_fault",
                        "fault": detected_fault,
                        "event_id": self.last_emitted_event.get("event_id") if self.last_emitted_event else None,
                    }
            await asyncio.sleep(config.AGENT_POLL_SECONDS)
