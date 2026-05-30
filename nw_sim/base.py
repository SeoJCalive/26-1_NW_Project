from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import Any

from . import config
from .messages import decode_message, encode_message, iso_now, make_status, make_status_report
from .transport import send_request, write_json_line


TRAFFIC_HISTORY_LIMIT = 5
TRAFFIC_PAYLOAD_PREVIEW_LIMIT = 1200


class BaseNode:
    def __init__(
        self,
        node_id: str,
        listen_host: str,
        listen_port: int,
        controller_host: str,
        controller_port: int,
        control_token: str | None = None,
    ) -> None:
        self.node_id = node_id
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.controller_host = controller_host
        self.controller_port = controller_port
        self.control_token = control_token
        self.control_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.running = True
        self.stopped = False
        self.retry_total = 0
        self.duplicate_dropped = 0
        self.note = "초기화됨"
        self._tasks: list[asyncio.Task[Any]] = []
        self._server: asyncio.AbstractServer | None = None
        self._shutdown_event = asyncio.Event()
        self._reset_traffic_state()
        self._configure_default_traffic_peers()

    async def start(self) -> None:
        await self.start_background()

    async def start_background(self) -> None:
        self._server = await asyncio.start_server(self._handle_connection, self.listen_host, self.listen_port)
        self._tasks.append(asyncio.create_task(self._control_loop(), name=f"{self.node_id}-control"))
        self._tasks.append(asyncio.create_task(self._status_loop(), name=f"{self.node_id}-status"))

    async def wait_until_stopped(self) -> None:
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        if self.stopped:
            return
        self.stopped = True
        self._shutdown_event.set()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    def state_label(self) -> str:
        if self.stopped:
            return "중지"
        return "실행 중" if self.running else "일시정지"

    async def publish_status(self, extra: dict[str, Any] | None = None, note: str | None = None) -> None:
        if note is not None:
            self.note = note
        message = make_status(
            node_id=self.node_id,
            state=self.state_label(),
            queue_length=self.queue_length(),
            pending_ack_count=self.pending_ack_count(),
            retry_total=self.retry_total,
            duplicate_dropped=self.duplicate_dropped,
            note=self.note,
            extra=extra,
        )
        outbound = make_status_report(message, control_token=self.control_token)
        try:
            await send_request(
                self.controller_host,
                self.controller_port,
                outbound,
                expect_response=False,
                timeout=1.0,
            )
        except (OSError, asyncio.TimeoutError):
            pass

    def queue_length(self) -> int:
        return 0

    def pending_ack_count(self) -> int:
        return 0

    async def on_control(self, message: dict[str, Any]) -> None:
        command = message.get("command")
        if command == "start":
            self.running = True
            await self.publish_status(note="시작됨")
        elif command == "pause":
            self.running = False
            await self.publish_status(note="일시정지됨")
        elif command == "reset":
            await self.reset_state()
            await self.publish_status(note="재설정됨")
        elif command == "shutdown":
            await self.publish_status(note="종료 요청 수신")
            asyncio.create_task(self.stop())

    async def reset_state(self) -> None:
        self.retry_total = 0
        self.duplicate_dropped = 0
        self.note = "재설정됨"
        self._reset_traffic_state()
        self._configure_default_traffic_peers()

    async def handle_network_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        return {"ok": True, "node_id": self.node_id}

    def _configure_default_traffic_peers(self) -> None:
        return None

    def _reset_traffic_state(self) -> None:
        self._traffic_capture_seq = 0
        self._traffic_captured_at: str | None = None
        self._traffic_previous_peer = self._empty_peer_snapshot()
        self._traffic_next_peer = self._empty_peer_snapshot()
        self._traffic_recent: deque[dict[str, Any]] = deque(maxlen=TRAFFIC_HISTORY_LIMIT)

    def _empty_peer_snapshot(self) -> dict[str, Any]:
        return {
            "peer_node_id": None,
            "peer_role": None,
            "hop_state": "unknown",
            "failure_reason": None,
            "last_received": None,
            "last_sent": None,
        }

    def _sanitize_message_payload(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {key: value for key, value in payload.items() if key != "control_token"}
        return payload

    def _snapshot_json_payload(self, payload: Any) -> dict[str, Any]:
        sanitized = self._sanitize_message_payload(payload)
        encoded = json.dumps(sanitized, sort_keys=True, default=str)
        original_size = len(encoded)
        truncated = original_size > TRAFFIC_PAYLOAD_PREVIEW_LIMIT
        preview = encoded[:TRAFFIC_PAYLOAD_PREVIEW_LIMIT] if truncated else None
        if truncated:
            json_payload = None
        else:
            json_payload = json.loads(encode_message(sanitized))
        return {
            "payload": json_payload,
            "truncated": truncated,
            "original_size": original_size if truncated else None,
            "preview": preview,
        }

    def _peer_store(self, direction: str) -> dict[str, Any]:
        if direction == "previous_peer":
            return self._traffic_previous_peer
        if direction == "next_peer":
            return self._traffic_next_peer
        raise ValueError(f"unknown traffic direction: {direction}")

    def _set_peer_descriptor(
        self,
        direction: str,
        *,
        peer_node_id: str | None = None,
        peer_role: str | None = None,
        hop_state: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        peer = self._peer_store(direction)
        if peer_node_id is not None:
            peer["peer_node_id"] = peer_node_id
        if peer_role is not None:
            peer["peer_role"] = peer_role
        if hop_state is not None:
            peer["hop_state"] = hop_state
        peer["failure_reason"] = failure_reason

    def record_peer_state(
        self,
        direction: str,
        *,
        peer_node_id: str | None = None,
        peer_role: str | None = None,
        hop_state: str,
        failure_reason: str | None = None,
    ) -> None:
        self._set_peer_descriptor(
            direction,
            peer_node_id=peer_node_id,
            peer_role=peer_role,
            hop_state=hop_state,
            failure_reason=failure_reason,
        )

    def record_peer_message(
        self,
        direction: str,
        flow: str,
        payload: Any,
        *,
        peer_node_id: str | None = None,
        peer_role: str | None = None,
        hop_state: str,
        failure_reason: str | None = None,
        logical_id: str | None = None,
        attempt_no: int | None = None,
        phase: str,
    ) -> None:
        peer = self._peer_store(direction)
        self._traffic_capture_seq += 1
        captured_at = iso_now()
        payload_snapshot = self._snapshot_json_payload(payload)
        capture = {
            "logical_id": logical_id,
            "attempt_no": attempt_no,
            "phase": phase,
            "captured_at": captured_at,
            **payload_snapshot,
        }
        self._set_peer_descriptor(
            direction,
            peer_node_id=peer_node_id,
            peer_role=peer_role,
            hop_state=hop_state,
            failure_reason=failure_reason,
        )
        peer[flow] = capture
        self._traffic_captured_at = captured_at
        self._traffic_recent.appendleft(
            {
                "direction": direction,
                "flow": flow,
                "peer_node_id": peer["peer_node_id"],
                "peer_role": peer["peer_role"],
                "hop_state": peer["hop_state"],
                "failure_reason": peer["failure_reason"],
                "capture": capture,
            }
        )

    def traffic_snapshot(self) -> dict[str, Any]:
        return json.loads(
            encode_message(
                {
                    "capture_seq": self._traffic_capture_seq,
                    "captured_at": self._traffic_captured_at,
                    "previous_peer": self._traffic_previous_peer,
                    "next_peer": self._traffic_next_peer,
                    "recent": list(self._traffic_recent),
                }
            )
        )

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while not self.stopped:
                raw = await reader.readline()
                if not raw:
                    break
                message = decode_message(raw.decode().strip())
                if message.get("msg_type") == "CONTROL":
                    if self.control_token and message.get("control_token") != self.control_token:
                        await write_json_line(writer, {"ok": False, "reason": "invalid_token", "node_id": self.node_id})
                        continue
                    await self.control_queue.put(message)
                    control_response = {"ok": True, "node_id": self.node_id}
                    await write_json_line(writer, control_response)
                    continue
                response = await self.handle_network_message(message)
                if response is not None:
                    await write_json_line(writer, response)
        finally:
            writer.close()
            await writer.wait_closed()

    async def _control_loop(self) -> None:
        while not self.stopped:
            message = await self.control_queue.get()
            target = message.get("target")
            if target not in {self.node_id, "all"}:
                continue
            try:
                await self.on_control(message)
            except Exception:
                await self.publish_status(note="제어 명령 처리 실패")

    async def _status_loop(self) -> None:
        while not self.stopped:
            await self.publish_status()
            await asyncio.sleep(config.STATUS_REFRESH_SECONDS)
