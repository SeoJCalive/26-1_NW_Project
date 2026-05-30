from __future__ import annotations

from collections import deque
from typing import Any

from . import config
from .base import BaseNode
from .messages import json_roundtrip, make_ack
from .routing import fault_localization_from_event, summarize_event_routing


class Monitor(BaseNode):
    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        controller_host: str,
        controller_port: int,
        control_token: str | None = None,
    ) -> None:
        super().__init__("monitor", listen_host, listen_port, controller_host, controller_port, control_token)
        self.event_log: deque[dict[str, Any]] = deque(maxlen=50)
        self.total_logged: int = 0
        self.recent_events: deque[str] = deque(maxlen=config.RECENT_EVENT_LIMIT)
        self.recent_event_summaries: deque[dict[str, Any]] = deque(maxlen=config.RECENT_EVENT_LIMIT)
        self.received_id_cache: set[str] = set()
        self.host_state_table: dict[str, dict[str, Any]] = {}
        self.last_seq_by_host: dict[str, int] = {}
        self.last_processed_event: dict[str, Any] | None = None
        self.last_sink_result: dict[str, Any] | None = None
        self.last_ack_result: dict[str, Any] | None = None
        self.last_route_trace: list[dict[str, Any]] = []
        self.last_route_summary: dict[str, Any] | None = None
        self.last_fault_localization: dict[str, Any] | None = None
        self.duplicate_count = 0
        self.out_of_order_count = 0
        self.drop_next_ack = False

    def _configure_default_traffic_peers(self) -> None:
        self.record_peer_state("previous_peer", peer_node_id="r2", peer_role="relay", hop_state="unknown")
        self.record_peer_state("next_peer", hop_state="not_applicable")

    async def reset_state(self) -> None:
        await super().reset_state()
        self.event_log.clear()
        self.total_logged = 0
        self.recent_events.clear()
        self.recent_event_summaries.clear()
        self.received_id_cache.clear()
        self.host_state_table.clear()
        self.last_seq_by_host.clear()
        self.last_processed_event = None
        self.last_sink_result = None
        self.last_ack_result = None
        self.last_route_trace = []
        self.last_route_summary = None
        self.last_fault_localization = None
        self.duplicate_count = 0
        self.out_of_order_count = 0
        self.drop_next_ack = False

    async def publish_status(self, extra: dict[str, Any] | None = None, note: str | None = None) -> None:
        payload = {
            "recent_events": list(self.recent_events),
            "host_state_table": json_roundtrip(self.host_state_table) if self.host_state_table else {},
            "out_of_order_count": self.out_of_order_count,
            "total_logged": self.total_logged,
            "duplicate_count": self.duplicate_count,
            "detail": {
                "role": "monitor",
                "recent_event_summaries": [
                    json_roundtrip(summary)
                    for summary in self.recent_event_summaries
                ],
                "last_processed_event": json_roundtrip(self.last_processed_event) if self.last_processed_event else None,
                "last_sink_result": json_roundtrip(self.last_sink_result) if self.last_sink_result else None,
                "last_ack_result": json_roundtrip(self.last_ack_result) if self.last_ack_result else None,
                "last_route_trace": [json_roundtrip(entry) for entry in self.last_route_trace],
                "last_route_summary": json_roundtrip(self.last_route_summary) if self.last_route_summary else None,
                "last_fault_localization": json_roundtrip(self.last_fault_localization) if self.last_fault_localization else None,
                "traffic": self.traffic_snapshot(),
            },
        }
        if extra:
            payload.update(extra)
        await super().publish_status(extra=payload, note=note)

    def _event_summary(self, event: dict[str, Any]) -> dict[str, Any]:
        route_summary = summarize_event_routing(event)
        return {
            "event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "severity": event.get("severity"),
            "host_id": event.get("host_id"),
            "seq_no": event.get("seq_no"),
            "timestamp": event.get("timestamp"),
            "route_state": route_summary.get("route_state"),
            "active_route": route_summary.get("active_route"),
            "failed_hop": route_summary.get("failed_hop"),
            "suspected_node": route_summary.get("suspected_node"),
            "reroute_reason": route_summary.get("reroute_reason"),
        }

    def _record_route_observation(self, event: dict[str, Any]) -> None:
        route_trace = event.get("route_trace")
        self.last_route_trace = [json_roundtrip(entry) for entry in route_trace if isinstance(entry, dict)] if isinstance(route_trace, list) else []
        self.last_route_summary = summarize_event_routing(event)
        self.last_fault_localization = fault_localization_from_event(event)

    def _upstream_peer_for_event(self, event: dict[str, Any]) -> str:
        route_summary = summarize_event_routing(event)
        if route_summary.get("active_route") == "backup":
            return "r2b"
        return "r2"

    async def on_control(self, message: dict[str, Any]) -> None:
        await super().on_control(message)
        if message.get("command") == "drop_next_ack":
            self.drop_next_ack = True
            self.last_ack_result = {"status": "drop_requested", "reason": "control"}
            await self.publish_status(note="Monitor가 다음 ACK를 드롭합니다")

    async def handle_network_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if not self.running:
            return {"msg_type": "ERROR", "reason": "paused", "node_id": self.node_id}
        if message.get("msg_type") != "EVENT":
            return {"msg_type": "ERROR", "reason": "invalid_event", "node_id": self.node_id}

        event = json_roundtrip(message)
        event_id = str(event["event_id"])
        event_summary = self._event_summary(event)
        self._record_route_observation(event)
        upstream_peer = self._upstream_peer_for_event(event)
        self.record_peer_message(
            "previous_peer",
            "last_received",
            event,
            peer_node_id=upstream_peer,
            peer_role="relay",
            hop_state="request_received",
            logical_id=event_id,
            phase="sink_event",
        )
        if event_id in self.received_id_cache:
            self.duplicate_count += 1
            self.duplicate_dropped += 1
            self.last_processed_event = event_summary
            self.last_sink_result = {"status": "duplicate_ignored", "event_id": event_id}
            will_drop_ack = self.drop_next_ack
            if will_drop_ack:
                self.drop_next_ack = False
                self.last_ack_result = {
                    "status": "dropped",
                    "event_id": event_id,
                    "duplicate": True,
                }
                self.record_peer_state("previous_peer", peer_node_id=upstream_peer, peer_role="relay", hop_state="ack_dropped", failure_reason="drop_next_ack")
                await self.publish_status(note=f"중복 {event_id}에 대한 ACK 1회 드롭")
                return None
            ack = make_ack(event_id, self.node_id)
            self.last_ack_result = {
                "status": "acknowledged",
                "event_id": event_id,
                "duplicate": True,
            }
            self.record_peer_message(
                "previous_peer",
                "last_sent",
                ack,
                peer_node_id=upstream_peer,
                peer_role="relay",
                hop_state="acknowledged",
                logical_id=event_id,
                phase="sink_ack",
            )
            await self.publish_status(note=f"중복 {event_id} 무시")
            return ack

        host_id = str(event["host_id"])
        seq_no = int(event["seq_no"])
        last_seq = self.last_seq_by_host.get(host_id, 0)
        if seq_no <= last_seq:
            self.out_of_order_count += 1
        self.last_seq_by_host[host_id] = max(last_seq, seq_no)
        self.received_id_cache.add(event_id)
        self.event_log.append(event)
        self.total_logged += 1
        self.recent_event_summaries.appendleft(event_summary)
        self.last_processed_event = event_summary
        self.recent_events.appendleft(
            f"{event['event_id']} {event['event_type']} {event['severity']} host={host_id} seq={seq_no}"
        )
        self.host_state_table[host_id] = {
            "event_type": event["event_type"],
            "severity": event["severity"],
            "payload": event["payload"],
            "timestamp": event["timestamp"],
        }
        self.last_sink_result = {
            "status": "logged",
            "event_id": event_id,
            "host_id": host_id,
            "seq_no": seq_no,
        }
        will_drop_ack = self.drop_next_ack
        if will_drop_ack:
            self.drop_next_ack = False
            self.last_ack_result = {
                "status": "dropped",
                "event_id": event_id,
                "duplicate": False,
            }
            self.record_peer_state("previous_peer", peer_node_id=upstream_peer, peer_role="relay", hop_state="ack_dropped", failure_reason="drop_next_ack")
            await self.publish_status(note=f"{event_id} ACK 의도적으로 드롭")
            return None
        ack = make_ack(event_id, self.node_id)
        self.last_ack_result = {
            "status": "acknowledged",
            "event_id": event_id,
            "duplicate": False,
        }
        self.record_peer_message(
            "previous_peer",
            "last_sent",
            ack,
            peer_node_id=upstream_peer,
            peer_role="relay",
            hop_state="acknowledged",
            logical_id=event_id,
            phase="sink_ack",
        )
        await self.publish_status(note=f"{event_id} 기록 완료")
        return ack
