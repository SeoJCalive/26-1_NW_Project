from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from . import config
from .base import BaseNode
from .messages import json_roundtrip, make_ack
from .transport import send_request


REQUIRED_EVENT_FIELDS = {"msg_type", "event_id", "seq_no", "host_id", "event_type", "timestamp"}


class RelayNode(BaseNode):
    def __init__(
        self,
        node_id: str,
        listen_host: str,
        listen_port: int,
        controller_host: str,
        controller_port: int,
        downstream_host: str,
        downstream_port: int,
        control_token: str | None = None,
    ) -> None:
        super().__init__(node_id, listen_host, listen_port, controller_host, controller_port, control_token)
        self.downstream_host = downstream_host
        self.downstream_port = downstream_port
        self.received_id_cache: set[str] = set()
        self.pending_ack_table: dict[str, int] = {}
        self.pending_ack_detail: dict[str, dict[str, Any]] = {}
        self.recent_received_event_ids: deque[str] = deque(maxlen=config.RECENT_EVENT_LIMIT)
        self.last_received_event: dict[str, Any] | None = None
        self.last_downstream_result: dict[str, Any] | None = None
        self.last_forwarded_result: dict[str, Any] | None = None
        self.processing_delay = config.RELAY_DELAY_SECONDS
        self.delivery_failures = 0
        self._reset_generation = 0

    def _configure_default_traffic_peers(self) -> None:
        if self.node_id == "r1":
            self.record_peer_state("previous_peer", peer_node_id="local-agent", peer_role="agent", hop_state="unknown")
            self.record_peer_state("next_peer", peer_node_id="r2", peer_role="relay", hop_state="unknown")
        else:
            self.record_peer_state("previous_peer", peer_node_id="r1", peer_role="relay", hop_state="unknown")
            self.record_peer_state("next_peer", peer_node_id="monitor", peer_role="monitor", hop_state="unknown")

    def pending_ack_count(self) -> int:
        return len(self.pending_ack_table)

    async def reset_state(self) -> None:
        await super().reset_state()
        self._reset_generation += 1
        self.pending_ack_table.clear()
        self.pending_ack_detail.clear()
        self.received_id_cache.clear()
        self.recent_received_event_ids.clear()
        self.last_received_event = None
        self.last_downstream_result = None
        self.last_forwarded_result = None
        self.delivery_failures = 0
        self.processing_delay = config.RELAY_DELAY_SECONDS

    async def publish_status(self, extra: dict[str, Any] | None = None, note: str | None = None) -> None:
        payload = {
            "detail": {
                "role": "relay",
                "recent_received_event_ids": list(self.recent_received_event_ids),
                "last_received_event": json_roundtrip(self.last_received_event) if self.last_received_event else None,
                "pending_ack_state": [
                    json_roundtrip(detail)
                    for detail in self.pending_ack_detail.values()
                ],
                "last_downstream_result": json_roundtrip(self.last_downstream_result) if self.last_downstream_result else None,
                "last_forwarded_result": json_roundtrip(self.last_forwarded_result) if self.last_forwarded_result else None,
                "traffic": self.traffic_snapshot(),
            }
        }
        if extra:
            payload.update(extra)
        await super().publish_status(extra=payload, note=note)

    async def on_control(self, message: dict[str, Any]) -> None:
        await super().on_control(message)
        command = message.get("command")
        params = message.get("params", {})
        if command == "set_delay":
            try:
                requested_delay = float(params.get("seconds", config.RELAY_DELAY_SECONDS))
            except (TypeError, ValueError):
                await self.publish_status(note="delay 파라미터 오류")
                return
            self.processing_delay = min(requested_delay, config.MAX_RELAY_DELAY_SECONDS)
            await self.publish_status(note=f"delay 설정 {self.processing_delay:.2f}s")

    def _downstream_response_timeout(self) -> float:
        if self.node_id == "r2":
            return config.ACK_TIMEOUT_SECONDS
        return config.RELAY_DOWNSTREAM_RESPONSE_TIMEOUT_SECONDS

    def _is_valid_event(self, event: dict[str, object]) -> bool:
        return event.get("msg_type") == "EVENT" and REQUIRED_EVENT_FIELDS.issubset(event)

    def _downstream_target_label(self) -> str:
        return "monitor" if self.node_id == "r2" else "r2"

    def _event_summary(self, event: dict[str, object]) -> dict[str, Any]:
        return {
            "event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "seq_no": event.get("seq_no"),
            "host_id": event.get("host_id"),
            "timestamp": event.get("timestamp"),
        }

    async def handle_network_message(self, message: dict[str, object]) -> dict[str, object] | None:
        self.record_peer_message(
            "previous_peer",
            "last_received",
            message,
            peer_node_id=self._peer_store("previous_peer").get("peer_node_id"),
            peer_role=self._peer_store("previous_peer").get("peer_role"),
            hop_state="request_received",
            logical_id=str(message.get("event_id") or message.get("msg_type") or "unknown"),
            phase="upstream_event",
        )
        if not self.running:
            await self.publish_status(note=f"일시정지 상태로 {message.get('event_id', 'unknown')} 보류 중")
            response: dict[str, object] = {"msg_type": "ERROR", "reason": "paused", "node_id": self.node_id}
            self.record_peer_message(
                "previous_peer",
                "last_sent",
                response,
                peer_node_id=self._peer_store("previous_peer").get("peer_node_id"),
                peer_role=self._peer_store("previous_peer").get("peer_role"),
                hop_state="paused",
                failure_reason="paused",
                logical_id=str(message.get("event_id") or "unknown"),
                phase="upstream_response",
            )
            return response
        if not self._is_valid_event(message):
            self.last_downstream_result = {"status": "rejected", "reason": "invalid_event"}
            await self.publish_status(note="유효하지 않은 EVENT 폐기")
            response: dict[str, object] = {"msg_type": "ERROR", "reason": "invalid_event", "node_id": self.node_id}
            self.record_peer_message(
                "previous_peer",
                "last_sent",
                response,
                peer_node_id=self._peer_store("previous_peer").get("peer_node_id"),
                peer_role=self._peer_store("previous_peer").get("peer_role"),
                hop_state="rejected",
                failure_reason="invalid_event",
                logical_id=str(message.get("event_id") or "invalid_event"),
                phase="upstream_response",
            )
            return response

        event = json_roundtrip(dict(message))
        event_id = str(event["event_id"])
        self.recent_received_event_ids.appendleft(event_id)
        self.last_received_event = self._event_summary(event)
        await self.publish_status(note=f"{event_id} upstream 수신")
        if event_id in self.received_id_cache:
            self.duplicate_dropped += 1
            self.last_downstream_result = {
                "status": "duplicate_ack_replayed",
                "event_id": event_id,
                "downstream_target": self._downstream_target_label(),
            }
            self.last_forwarded_result = {
                "status": "upstream_ack_replayed",
                "event_id": event_id,
            }
            await self.publish_status(note=f"중복 {event_id} ACK 재전송")
            ack = make_ack(event_id, self.node_id)
            self.record_peer_message(
                "previous_peer",
                "last_sent",
                ack,
                peer_node_id=self._peer_store("previous_peer").get("peer_node_id"),
                peer_role=self._peer_store("previous_peer").get("peer_role"),
                hop_state="acknowledged",
                logical_id=event_id,
                phase="upstream_ack",
            )
            return ack
        if event_id in self.pending_ack_table:
            self.duplicate_dropped += 1
            self.last_downstream_result = {
                "status": "duplicate_pending",
                "event_id": event_id,
                "downstream_target": self._downstream_target_label(),
            }
            self.last_forwarded_result = {
                "status": "upstream_pending_error",
                "event_id": event_id,
            }
            await self.publish_status(note=f"중복 {event_id} 아직 pending 상태")
            response: dict[str, object] = {
                "msg_type": "ERROR",
                "reason": "pending",
                "event_id": event_id,
                "node_id": self.node_id,
            }
            self.record_peer_message(
                "previous_peer",
                "last_sent",
                response,
                peer_node_id=self._peer_store("previous_peer").get("peer_node_id"),
                peer_role=self._peer_store("previous_peer").get("peer_role"),
                hop_state="pending",
                failure_reason="pending",
                logical_id=event_id,
                phase="upstream_response",
            )
            return response

        accepted = await self._deliver_with_retry(event)
        if accepted:
            self.last_forwarded_result = {
                "status": "upstream_ack_ready",
                "event_id": event_id,
            }
            ack = make_ack(event_id, self.node_id)
            self.record_peer_message(
                "previous_peer",
                "last_sent",
                ack,
                peer_node_id=self._peer_store("previous_peer").get("peer_node_id"),
                peer_role=self._peer_store("previous_peer").get("peer_role"),
                hop_state="acknowledged",
                logical_id=event_id,
                phase="upstream_ack",
            )
            return ack
        self.last_forwarded_result = {
            "status": "upstream_error",
            "event_id": event_id,
            "reason": "delivery_failed",
        }
        response: dict[str, object] = {
            "msg_type": "ERROR",
            "reason": "delivery_failed",
            "event_id": event_id,
            "node_id": self.node_id,
        }
        self.record_peer_message(
            "previous_peer",
            "last_sent",
            response,
            peer_node_id=self._peer_store("previous_peer").get("peer_node_id"),
            peer_role=self._peer_store("previous_peer").get("peer_role"),
            hop_state="delivery_failed",
            failure_reason="delivery_failed",
            logical_id=event_id,
            phase="upstream_response",
        )
        return response

    async def _deliver_with_retry(self, event: dict[str, object]) -> bool:
        event_id = str(event["event_id"])
        generation = self._reset_generation
        self.pending_ack_table[event_id] = generation
        pending_detail: dict[str, Any] = {
            "event_id": event_id,
            "event_type": event.get("event_type"),
            "seq_no": event.get("seq_no"),
            "downstream_target": self._downstream_target_label(),
            "attempt": 0,
            "state": "pending",
            "last_outcome": "accepted",
        }
        self.pending_ack_detail[event_id] = pending_detail
        accepted = False
        reset_interrupted = False

        async def mark_reset_interrupted(attempt: int) -> None:
            nonlocal reset_interrupted
            reset_interrupted = True
            pending_detail.update({"state": "reset_interrupted", "last_outcome": "reset", "attempt": attempt})
            self.last_downstream_result = {
                "status": "reset_interrupted",
                "event_id": event_id,
                "attempt": attempt,
            }
            await self.publish_status(note=f"{event_id} 전달 대기 재설정")

        try:
            for attempt in range(1, config.MAX_RETRY_COUNT + 1):
                if self._reset_generation != generation:
                    await mark_reset_interrupted(attempt - 1)
                    break
                if self.processing_delay > 0:
                    await asyncio.sleep(self.processing_delay)
                if self._reset_generation != generation:
                    await mark_reset_interrupted(attempt - 1)
                    break
                pending_detail["attempt"] = attempt
                if attempt == 1:
                    pending_detail.update({"state": "waiting_ack", "last_outcome": "forwarded"})
                    self.record_peer_message(
                        "next_peer",
                        "last_sent",
                        event,
                        peer_node_id=self._peer_store("next_peer").get("peer_node_id"),
                        peer_role=self._peer_store("next_peer").get("peer_role"),
                        hop_state="request_sent",
                        logical_id=event_id,
                        attempt_no=attempt,
                        phase="downstream_event",
                    )
                    await self.publish_status(note=f"{event_id} downstream 전달")
                else:
                    self.retry_total += 1
                    pending_detail.update({"state": "retrying", "last_outcome": "retrying"})
                    self.record_peer_message(
                        "next_peer",
                        "last_sent",
                        event,
                        peer_node_id=self._peer_store("next_peer").get("peer_node_id"),
                        peer_role=self._peer_store("next_peer").get("peer_role"),
                        hop_state="retrying",
                        logical_id=event_id,
                        attempt_no=attempt,
                        phase="downstream_retry",
                    )
                    await self.publish_status(note=f"{event_id} 재시도 {attempt - 1}회")
                try:
                    response = await send_request(
                        self.downstream_host,
                        self.downstream_port,
                        json_roundtrip(event),
                        expect_response=True,
                        timeout=self._downstream_response_timeout(),
                    )
                    if self._reset_generation != generation:
                        await mark_reset_interrupted(attempt)
                        break
                    if isinstance(response, dict) and response.get("msg_type") == "ACK" and response.get("ack_for") == event_id:
                        accepted = True
                        self.record_peer_message(
                            "next_peer",
                            "last_received",
                            response,
                            peer_node_id=self._peer_store("next_peer").get("peer_node_id"),
                            peer_role=self._peer_store("next_peer").get("peer_role"),
                            hop_state="acknowledged",
                            logical_id=event_id,
                            attempt_no=attempt,
                            phase="downstream_ack",
                        )
                        pending_detail.update({
                            "state": "acknowledged",
                            "last_outcome": "ack_received",
                            "ack_from": response.get("from_node"),
                        })
                        self.last_downstream_result = {
                            "status": "acknowledged",
                            "event_id": event_id,
                            "attempt": attempt,
                            "ack": json_roundtrip(response),
                        }
                        await self.publish_status(note=f"{event_id} downstream ACK 수신")
                        break
                except asyncio.TimeoutError:
                    self.record_peer_state(
                        "next_peer",
                        peer_node_id=self._peer_store("next_peer").get("peer_node_id"),
                        peer_role=self._peer_store("next_peer").get("peer_role"),
                        hop_state="timeout",
                        failure_reason="timeout",
                    )
                    pending_detail.update({"state": "retry_pending", "last_outcome": "timeout"})
                    self.last_downstream_result = {
                        "status": "retry_pending",
                        "event_id": event_id,
                        "attempt": attempt,
                        "reason": "timeout",
                    }
                    if attempt == config.MAX_RETRY_COUNT:
                        break
                    await self.publish_status(note=f"{event_id} ACK 대기 timeout")
                except OSError:
                    self.record_peer_state(
                        "next_peer",
                        peer_node_id=self._peer_store("next_peer").get("peer_node_id"),
                        peer_role=self._peer_store("next_peer").get("peer_role"),
                        hop_state="connection_error",
                        failure_reason="connection_error",
                    )
                    pending_detail.update({"state": "retry_pending", "last_outcome": "connection_error"})
                    self.last_downstream_result = {
                        "status": "retry_pending",
                        "event_id": event_id,
                        "attempt": attempt,
                        "reason": "connection_error",
                    }
                    if attempt == config.MAX_RETRY_COUNT:
                        break
                    await self.publish_status(note=f"{event_id} downstream 연결 실패")
            if accepted:
                self.received_id_cache.add(event_id)
                self.last_forwarded_result = {
                    "status": "forwarded",
                    "event_id": event_id,
                    "attempts": pending_detail["attempt"],
                    "downstream_target": self._downstream_target_label(),
                }
                await self.publish_status(note=f"{event_id} upstream ACK 준비")
            elif not reset_interrupted:
                self.delivery_failures += 1
                self.last_downstream_result = {
                    "status": "delivery_failed",
                    "event_id": event_id,
                    "attempts": pending_detail["attempt"],
                    "last_outcome": pending_detail.get("last_outcome"),
                }
                self.last_forwarded_result = {
                    "status": "failed",
                    "event_id": event_id,
                    "downstream_target": self._downstream_target_label(),
                }
                await self.publish_status(note=f"{event_id} 전달 실패")
        finally:
            _ = self.pending_ack_table.pop(event_id, None)
            _ = self.pending_ack_detail.pop(event_id, None)
        return accepted
