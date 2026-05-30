from __future__ import annotations

import asyncio
from typing import Any, cast

from . import config
from .base import BaseNode
from .messages import iso_now, json_roundtrip
from .routing import (
    ROUTE_BACKUP,
    ROUTE_PRIMARY,
    ROUTE_STATE_BYPASS_ACTIVE,
    ROUTE_STATE_FAILED,
    ROUTE_STATE_PRIMARY,
    default_detail_routing,
    initialize_event_route_metadata,
    make_route_trace_entry,
    validate_route_edge,
)
from .transport import send_request


LATENCY_HIGH_THRESHOLD_MS = 200


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
        backup_downstream_host: str | None = None,
        backup_downstream_port: int | None = None,
    ) -> None:
        super().__init__("local-agent", listen_host, listen_port, controller_host, controller_port, control_token)
        self.host_host = host_host
        self.host_port = host_port
        self.downstream_host = downstream_host
        self.downstream_port = downstream_port
        self.backup_downstream_host = backup_downstream_host
        self.backup_downstream_port = backup_downstream_port
        self.seq_no = 0
        self.last_fault_signature: str | None = None
        self.last_host_state_signature: tuple[object, ...] | None = None
        self.latest_input_state: dict[str, Any] | None = None
        self.latest_input_result: dict[str, Any] | None = None
        self.last_detected_fault: str | None = None
        self.last_emitted_event: dict[str, Any] | None = None
        self.last_downstream_result: dict[str, Any] | None = None
        self.last_routing_detail: dict[str, Any] = default_detail_routing(
            primary_downstream="r1",
            backup_downstream="r1b" if backup_downstream_host is not None and backup_downstream_port is not None else None,
            active_downstream="r1",
        )
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
        self.last_routing_detail = default_detail_routing(
            primary_downstream="r1",
            backup_downstream="r1b" if self._has_backup_downstream() else None,
            active_downstream="r1",
        )

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
            "routing": json_roundtrip(self.last_routing_detail),
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
        if host_state["latency_ms"] >= LATENCY_HIGH_THRESHOLD_MS:
            return "LATENCY_HIGH"
        return None

    def _host_state_signature(self, host_state: dict[str, Any]) -> tuple[object, ...]:
        return (
            host_state.get("cpu_usage"),
            host_state.get("memory_usage"),
            host_state.get("service_state"),
            host_state.get("latency_ms"),
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

    def _handle_no_selected_event(self, detected_fault: str | None) -> None:
        if detected_fault is not None:
            self.last_downstream_result = {
                "status": "suppressed_duplicate_fault",
                "fault": detected_fault,
                "event_id": self.last_emitted_event.get("event_id") if self.last_emitted_event else None,
            }
            return
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

    def _record_host_response(self, response: dict[str, Any], *, hop_state: str, failure_reason: str | None = None) -> None:
        self.record_peer_message(
            "previous_peer",
            "last_received",
            response,
            peer_node_id="host-simulator",
            peer_role="host",
            hop_state=hop_state,
            failure_reason=failure_reason,
            logical_id="get_host_state",
            phase="host_response",
        )

    def _handle_paused_host_response(self, response: dict[str, Any]) -> None:
        self._record_host_response(response, hop_state="paused", failure_reason="paused")
        self.latest_input_result = {"status": "fetch_failed", "reason": "host_paused", "source": "host"}
        self.last_detected_fault = None
        self.last_downstream_result = {"status": "not_attempted", "reason": "host_paused"}

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
                    "fault_mode": "NORMAL" if event_type == "HOST_STATE_UPDATE" else event_type,
                },
            }
        )

    def _has_backup_downstream(self) -> bool:
        return self.backup_downstream_host is not None and self.backup_downstream_port is not None

    def _set_routing_detail(
        self,
        *,
        route_state: str,
        active_route: str,
        active_downstream: str,
        event_id: str,
        failed_downstream: str | None = None,
        reroute_reason: str | None = None,
    ) -> None:
        self.last_routing_detail = {
            "route_state": route_state,
            "active_route": active_route,
            "primary_downstream": "r1",
            "backup_downstream": "r1b" if self._has_backup_downstream() else None,
            "active_downstream": active_downstream,
            "failed_downstream": failed_downstream,
            "reroute_reason": reroute_reason,
            "event_id": event_id,
            "route_generation": self.last_routing_detail.get("route_generation", 0) + 1,
        }

    def _append_route_trace(
        self,
        event: dict[str, Any],
        *,
        from_node: str = "local-agent",
        to_node: str,
        route_id: str,
        result: str,
        failure_reason: str | None = None,
    ) -> None:
        route_trace = event.setdefault("route_trace", [])
        if isinstance(route_trace, list):
            route_trace.append(
                make_route_trace_entry(
                    from_node=from_node,
                    to_node=to_node,
                    route_id=route_id,
                    attempt_no=1,
                    phase="event_forward",
                    result=result,
                    failure_reason=failure_reason,
                )
            )

    def _validated_downstream_error(self, response: dict[str, Any] | None, *, event_id: str) -> dict[str, str] | None:
        if response is None:
            return None
        downstream_error = response.get("downstream_error")
        if not isinstance(downstream_error, dict):
            return None
        downstream_error_fields = cast(dict[object, object], downstream_error)
        failed_hop = downstream_error_fields.get("failed_hop")
        suspected_node = downstream_error_fields.get("suspected_node")
        failure_reason = downstream_error_fields.get("failure_reason")
        if not isinstance(failed_hop, str) or not isinstance(suspected_node, str) or not isinstance(failure_reason, str):
            return None
        if failed_hop.count("->") != 1:
            return None
        from_node, to_node = failed_hop.split("->")
        try:
            route_id = validate_route_edge(from_node, to_node)
        except ValueError:
            return None
        if route_id != ROUTE_PRIMARY or to_node != suspected_node:
            return None
        response_event_id = downstream_error_fields.get("event_id")
        if isinstance(response_event_id, str) and response_event_id != event_id:
            return None
        return {
            "failed_hop": failed_hop,
            "suspected_node": suspected_node,
            "failure_reason": failure_reason,
            "from_node": from_node,
            "to_node": to_node,
            "route_id": route_id,
        }

    def _set_event_routing(
        self,
        event: dict[str, Any],
        *,
        route_state: str,
        active_route: str,
        failed_hop: str | None = None,
        suspected_node: str | None = None,
        reroute_reason: str | None = None,
    ) -> None:
        event["routing"] = {
            "route_state": route_state,
            "active_route": active_route,
            "failed_hop": failed_hop,
            "suspected_node": suspected_node,
            "reroute_reason": reroute_reason,
        }

    async def _send_event_to_downstream(
        self,
        event: dict[str, Any],
        *,
        to_node: str,
        route_id: str,
        host: str,
        port: int,
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        event_id = str(event["event_id"])
        self.record_peer_message(
            "next_peer",
            "last_sent",
            event,
            peer_node_id=to_node,
            peer_role="relay",
            hop_state="request_sent",
            logical_id=event_id,
            attempt_no=1,
            phase="event_forward",
        )
        try:
            response = await send_request(
                host,
                port,
                event,
                expect_response=True,
                timeout=config.AGENT_DOWNSTREAM_RESPONSE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            self.record_peer_state("next_peer", peer_node_id=to_node, peer_role="relay", hop_state="timeout", failure_reason="timeout")
            self._append_route_trace(event, to_node=to_node, route_id=route_id, result="timeout", failure_reason="timeout")
            return False, None, "timeout"
        except OSError:
            self.record_peer_state("next_peer", peer_node_id=to_node, peer_role="relay", hop_state="connection_error", failure_reason="connection_error")
            self._append_route_trace(event, to_node=to_node, route_id=route_id, result="connection_error", failure_reason="connection_error")
            return False, None, "connection_error"

        if not isinstance(response, dict) or response.get("msg_type") != "ACK":
            self.record_peer_message(
                "next_peer",
                "last_received",
                response,
                peer_node_id=to_node,
                peer_role="relay",
                hop_state="invalid_response",
                failure_reason="ack_missing",
                logical_id=event_id,
                attempt_no=1,
                phase="downstream_response",
            )
            self._append_route_trace(event, to_node=to_node, route_id=route_id, result="ack_missing", failure_reason="ack_missing")
            return False, json_roundtrip(response) if isinstance(response, dict) else None, "ack_missing"

        self.record_peer_message(
            "next_peer",
            "last_received",
            response,
            peer_node_id=to_node,
            peer_role="relay",
            hop_state="acknowledged",
            logical_id=event_id,
            attempt_no=1,
            phase="downstream_ack",
        )
        self._append_route_trace(event, to_node=to_node, route_id=route_id, result="acknowledged")
        return True, json_roundtrip(response), None

    async def _deliver_event(self, event: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        routed_event = initialize_event_route_metadata(event)
        event_id = str(routed_event["event_id"])
        primary_ok, primary_response, primary_reason = await self._send_event_to_downstream(
            routed_event,
            to_node="r1",
            route_id=ROUTE_PRIMARY,
            host=self.downstream_host,
            port=self.downstream_port,
        )
        if primary_ok:
            self._set_event_routing(routed_event, route_state=ROUTE_STATE_PRIMARY, active_route=ROUTE_PRIMARY)
            self._set_routing_detail(route_state=ROUTE_STATE_PRIMARY, active_route=ROUTE_PRIMARY, active_downstream="r1", event_id=event_id)
            self.last_downstream_result = {"status": "acknowledged", "event_id": event_id, "active_route": ROUTE_PRIMARY, "ack": primary_response}
            return routed_event, True

        downstream_error = self._validated_downstream_error(primary_response, event_id=event_id)
        failed_hop = downstream_error["failed_hop"] if downstream_error is not None else "local-agent->r1"
        suspected_node = downstream_error["suspected_node"] if downstream_error is not None else "r1"
        reroute_reason = downstream_error["failure_reason"] if downstream_error is not None else primary_reason
        if downstream_error is not None:
            self._append_route_trace(
                routed_event,
                from_node=downstream_error["from_node"],
                to_node=downstream_error["to_node"],
                route_id=downstream_error["route_id"],
                result="failed",
                failure_reason=downstream_error["failure_reason"],
            )

        self._set_event_routing(
            routed_event,
            route_state=ROUTE_STATE_FAILED,
            active_route=ROUTE_PRIMARY,
            failed_hop=failed_hop,
            suspected_node=suspected_node,
            reroute_reason=reroute_reason,
        )
        self._set_routing_detail(
            route_state=ROUTE_STATE_FAILED,
            active_route=ROUTE_PRIMARY,
            active_downstream="r1",
            event_id=event_id,
            failed_downstream=suspected_node,
            reroute_reason=reroute_reason,
        )
        if not self._has_backup_downstream():
            self.last_downstream_result = {"status": "send_failed", "reason": primary_reason, "event_id": event_id, "active_route": ROUTE_PRIMARY}
            return routed_event, False

        backup_host = self.backup_downstream_host
        backup_port = self.backup_downstream_port
        if backup_host is None or backup_port is None:
            self.last_downstream_result = {"status": "send_failed", "reason": primary_reason, "event_id": event_id, "active_route": ROUTE_PRIMARY}
            return routed_event, False

        self._set_event_routing(
            routed_event,
            route_state=ROUTE_STATE_BYPASS_ACTIVE,
            active_route=ROUTE_BACKUP,
            failed_hop=failed_hop,
            suspected_node=suspected_node,
            reroute_reason=reroute_reason,
        )
        self._set_routing_detail(
            route_state=ROUTE_STATE_BYPASS_ACTIVE,
            active_route=ROUTE_BACKUP,
            active_downstream="r1b",
            event_id=event_id,
            failed_downstream=suspected_node,
            reroute_reason=reroute_reason,
        )
        backup_ok, backup_response, backup_reason = await self._send_event_to_downstream(
            routed_event,
            to_node="r1b",
            route_id=ROUTE_BACKUP,
            host=backup_host,
            port=backup_port,
        )
        if backup_ok:
            self.last_downstream_result = {
                "status": "acknowledged",
                "event_id": event_id,
                "active_route": ROUTE_BACKUP,
                "primary_failure_reason": primary_reason,
                "ack": backup_response,
            }
            return routed_event, True

        self._set_event_routing(
            routed_event,
            route_state=ROUTE_STATE_FAILED,
            active_route=ROUTE_BACKUP,
            failed_hop="local-agent->r1b",
            suspected_node="r1b",
            reroute_reason=primary_reason,
        )
        self._set_routing_detail(
            route_state=ROUTE_STATE_FAILED,
            active_route=ROUTE_BACKUP,
            active_downstream="r1b",
            event_id=event_id,
            failed_downstream="r1b",
            reroute_reason=primary_reason,
        )
        self.last_downstream_result = {
            "status": "send_failed",
            "reason": backup_reason,
            "event_id": event_id,
            "active_route": ROUTE_BACKUP,
            "primary_failure_reason": primary_reason,
        }
        return routed_event, False

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

                host_state = response.get("host_state") if isinstance(response, dict) else None
                if isinstance(response, dict) and response.get("msg_type") == "ERROR" and response.get("reason") == "paused":
                    self._handle_paused_host_response(response)
                    await self.publish_status(note="host 일시정지")
                    await asyncio.sleep(config.AGENT_POLL_SECONDS)
                    continue

                if not isinstance(host_state, dict):
                    self._record_host_response(
                        response if isinstance(response, dict) else {"response": response},
                        hop_state="invalid_response",
                        failure_reason="invalid_host_state",
                    )
                    self.latest_input_result = {"status": "invalid_response", "source": "host"}
                    self.last_downstream_result = {"status": "not_attempted", "reason": "invalid_host_state"}
                    await self.publish_status(note="host 상태 응답 이상")
                    await asyncio.sleep(config.AGENT_POLL_SECONDS)
                    continue

                assert isinstance(response, dict)
                self._record_host_response(response, hop_state="acknowledged")

                self.latest_input_state = json_roundtrip(host_state)
                self.latest_input_result = {"status": "ok", "source": "host"}
                detected_fault = self._detect_fault(host_state)
                self.last_detected_fault = detected_fault
                host_state_signature = self._host_state_signature(host_state)
                event_type = self._select_event_type(host_state, detected_fault)
                if event_type is None:
                    self._handle_no_selected_event(detected_fault)
                elif detected_fault is None or detected_fault != self.last_fault_signature:
                    event = self._build_event(event_type, host_state)
                    delivered_event, delivered = await self._deliver_event(event)
                    self.last_emitted_event = json_roundtrip(delivered_event)
                    if not delivered:
                        await self.publish_status(note=f"{delivered_event['event_id']} 전송 실패")
                        await asyncio.sleep(config.AGENT_POLL_SECONDS)
                        continue

                    self.last_fault_signature = detected_fault
                    self.last_host_state_signature = host_state_signature
                    await self.publish_status(note=f"이벤트 생성 {delivered_event['event_id']}")
                else:
                    self.last_downstream_result = {
                        "status": "suppressed_duplicate_fault",
                        "fault": detected_fault,
                        "event_id": self.last_emitted_event.get("event_id") if self.last_emitted_event else None,
                    }
            await asyncio.sleep(config.AGENT_POLL_SECONDS)
