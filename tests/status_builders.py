from __future__ import annotations

from typing import Any

from nw_demo import config
from nw_demo.messages import make_status


def _capture(
    payload: dict[str, Any],
    *,
    logical_id: str,
    phase: str,
    attempt_no: int | None = None,
    captured_at: str = "2026-04-27T10:00:02+00:00",
) -> dict[str, Any]:
    return {
        "logical_id": logical_id,
        "attempt_no": attempt_no,
        "phase": phase,
        "captured_at": captured_at,
        "payload": payload,
        "truncated": False,
        "original_size": None,
        "preview": None,
    }


def _traffic(previous_peer: dict[str, Any], next_peer: dict[str, Any], *, capture_seq: int = 4) -> dict[str, Any]:
    return {
        "capture_seq": capture_seq,
        "captured_at": "2026-04-27T10:00:02+00:00",
        "previous_peer": previous_peer,
        "next_peer": next_peer,
        "recent": [
            {
                "direction": "previous_peer",
                "flow": "last_received",
                "peer_node_id": previous_peer.get("peer_node_id"),
                "peer_role": previous_peer.get("peer_role"),
                "hop_state": previous_peer.get("hop_state"),
                "failure_reason": previous_peer.get("failure_reason"),
                "capture": previous_peer.get("last_received"),
            }
        ],
    }


def _build_status(
    node_id: str,
    *,
    state: str = "실행 중",
    queue_length: int = 0,
    pending_ack_count: int = 0,
    retry_total: int = 0,
    duplicate_dropped: int = 0,
    note: str = "테스트 상태",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return make_status(
        node_id=node_id,
        state=state,
        queue_length=queue_length,
        pending_ack_count=pending_ack_count,
        retry_total=retry_total,
        duplicate_dropped=duplicate_dropped,
        note=note,
        extra=extra,
    )


def build_host_status(*, state: str = "실행 중", note: str = "호스트 tick 4") -> dict[str, Any]:
    host_state = {
        "host_id": config.HOST_ID,
        "cpu_usage": 96,
        "memory_usage": 51,
        "service_state": "UP",
        "latency_ms": 28,
        "last_update_time": "2026-04-27T10:00:00+00:00",
    }
    return _build_status(
        "host-simulator",
        state=state,
        note=note,
        extra={
            "host_state": host_state,
            "detail": {
                "role": "host",
                "tick": 4,
                "fault_active": True,
                "fault_type": "CPU_SPIKE",
                "host_state": host_state,
                "traffic": _traffic(
                    {
                        "peer_node_id": "local-agent",
                        "peer_role": "agent",
                        "hop_state": "acknowledged",
                        "failure_reason": None,
                        "last_received": _capture({"kind": "get_host_state"}, logical_id="get_host_state", phase="host_request"),
                        "last_sent": _capture(
                            {"kind": "host_state", "host_state": host_state},
                            logical_id="get_host_state",
                            phase="host_response",
                        ),
                    },
                    {
                        "peer_node_id": None,
                        "peer_role": None,
                        "hop_state": "not_applicable",
                        "failure_reason": None,
                        "last_received": None,
                        "last_sent": None,
                    },
                ),
            },
        },
    )


def build_local_agent_status(*, state: str = "실행 중", note: str = "이벤트 생성 evt-host-1-7") -> dict[str, Any]:
    host_state = {
        "host_id": config.HOST_ID,
        "cpu_usage": 96,
        "memory_usage": 51,
        "service_state": "UP",
        "latency_ms": 28,
        "last_update_time": "2026-04-27T10:00:00+00:00",
    }
    last_event: dict[str, Any] = {
        "msg_type": "EVENT",
        "event_id": f"evt-{config.HOST_ID}-7",
        "seq_no": 7,
        "host_id": config.HOST_ID,
        "agent_id": config.AGENT_ID,
        "event_type": "CPU_SPIKE",
        "severity": "WARN",
        "timestamp": "2026-04-27T10:00:01+00:00",
        "payload": {
            "cpu": 96,
            "memory": 51,
            "service_state": "UP",
            "latency_ms": 28,
            "fault_mode": "CPU_SPIKE",
        },
    }
    return _build_status(
        "local-agent",
        state=state,
        note=note,
        extra={
            "last_event": last_event,
            "detail": {
                "role": "agent",
                "latest_input_state": host_state,
                "latest_input_result": {"status": "ok", "source": "host"},
                "detected_fault": "CPU_SPIKE",
                "emitted_event": last_event,
                "downstream_result": {
                    "status": "acknowledged",
                    "event_id": last_event["event_id"],
                    "ack": {
                        "msg_type": "ACK",
                        "ack_for": last_event["event_id"],
                        "from_node": "r1",
                        "timestamp": "2026-04-27T10:00:02+00:00",
                    },
                },
                "traffic": _traffic(
                    {
                        "peer_node_id": "host-simulator",
                        "peer_role": "host",
                        "hop_state": "acknowledged",
                        "failure_reason": None,
                        "last_received": _capture(
                            {"kind": "host_state", "host_state": host_state},
                            logical_id="get_host_state",
                            phase="host_response",
                        ),
                        "last_sent": _capture({"kind": "get_host_state"}, logical_id="get_host_state", phase="host_request"),
                    },
                    {
                        "peer_node_id": "r1",
                        "peer_role": "relay",
                        "hop_state": "acknowledged",
                        "failure_reason": None,
                        "last_received": _capture(
                            {
                                "msg_type": "ACK",
                                "ack_for": last_event["event_id"],
                                "from_node": "r1",
                                "timestamp": "2026-04-27T10:00:02+00:00",
                            },
                            logical_id=last_event["event_id"],
                            attempt_no=1,
                            phase="downstream_ack",
                        ),
                        "last_sent": _capture(last_event, logical_id=last_event["event_id"], attempt_no=1, phase="event_forward"),
                    },
                ),
            },
        },
    )


def build_relay_status(
    node_id: str = "r1",
    *,
    state: str = "실행 중",
    queue_length: int = 1,
    pending_ack_count: int = 1,
    retry_total: int = 2,
    duplicate_dropped: int = 0,
    note: str = "evt-host-1-7 downstream ACK 수신",
) -> dict[str, Any]:
    event_id = f"evt-{config.HOST_ID}-7"
    previous_peer = {
        "peer_node_id": "local-agent" if node_id == "r1" else "r1",
        "peer_role": "agent" if node_id == "r1" else "relay",
        "hop_state": "acknowledged",
        "failure_reason": None,
        "last_received": _capture(
            {"msg_type": "EVENT", "event_id": event_id, "event_type": "CPU_SPIKE", "seq_no": 7, "host_id": config.HOST_ID, "timestamp": "2026-04-27T10:00:01+00:00"},
            logical_id=event_id,
            phase="upstream_event",
        ),
        "last_sent": _capture(
            {"msg_type": "ACK", "ack_for": event_id, "from_node": node_id, "timestamp": "2026-04-27T10:00:03+00:00"},
            logical_id=event_id,
            phase="upstream_ack",
        ),
    }
    next_peer = {
        "peer_node_id": "r2" if node_id == "r1" else "monitor",
        "peer_role": "relay" if node_id == "r1" else "monitor",
        "hop_state": "acknowledged",
        "failure_reason": None,
        "last_received": _capture(
            {"msg_type": "ACK", "ack_for": event_id, "from_node": "r2" if node_id == "r1" else "monitor", "timestamp": "2026-04-27T10:00:03+00:00"},
            logical_id=event_id,
            attempt_no=2,
            phase="downstream_ack",
        ),
        "last_sent": _capture(
            {"msg_type": "EVENT", "event_id": event_id, "event_type": "CPU_SPIKE", "seq_no": 7, "host_id": config.HOST_ID, "timestamp": "2026-04-27T10:00:01+00:00"},
            logical_id=event_id,
            attempt_no=2,
            phase="downstream_retry",
        ),
    }
    return _build_status(
        node_id,
        state=state,
        queue_length=queue_length,
        pending_ack_count=pending_ack_count,
        retry_total=retry_total,
        duplicate_dropped=duplicate_dropped,
        note=note,
        extra={
            "detail": {
                "role": "relay",
                "recent_received_event_ids": [event_id, f"evt-{config.HOST_ID}-6"],
                "last_received_event": {
                    "event_id": event_id,
                    "event_type": "CPU_SPIKE",
                    "seq_no": 7,
                    "host_id": config.HOST_ID,
                    "timestamp": "2026-04-27T10:00:01+00:00",
                },
                "pending_ack_state": [
                    {
                        "event_id": event_id,
                        "event_type": "CPU_SPIKE",
                        "seq_no": 7,
                        "downstream_target": "r2" if node_id == "r1" else "monitor",
                        "attempt": 2,
                        "state": "retrying",
                        "last_outcome": "retrying",
                    }
                ],
                "last_downstream_result": {
                    "status": "acknowledged",
                    "event_id": event_id,
                    "attempt": 2,
                    "ack": {
                        "msg_type": "ACK",
                        "ack_for": event_id,
                        "from_node": "r2" if node_id == "r1" else "monitor",
                        "timestamp": "2026-04-27T10:00:03+00:00",
                    },
                },
                "last_forwarded_result": {
                    "status": "forwarded",
                    "event_id": event_id,
                    "attempts": 2,
                    "downstream_target": "r2" if node_id == "r1" else "monitor",
                },
                "traffic": _traffic(previous_peer, next_peer),
            }
        },
    )


def build_monitor_status(*, state: str = "실행 중", note: str = "evt-host-1-7 기록 완료") -> dict[str, Any]:
    event_id = f"evt-{config.HOST_ID}-7"
    recent_events = [
        f"{event_id} CPU_SPIKE WARN host={config.HOST_ID} seq=7",
        f"evt-{config.HOST_ID}-6 SERVICE_DOWN ERROR host={config.HOST_ID} seq=6",
    ]
    host_state_table = {
        config.HOST_ID: {
            "event_type": "CPU_SPIKE",
            "severity": "WARN",
            "payload": {
                "cpu": 96,
                "memory": 51,
                "service_state": "UP",
                "latency_ms": 28,
                "fault_mode": "CPU_SPIKE",
            },
            "timestamp": "2026-04-27T10:00:01+00:00",
        }
    }
    return _build_status(
        "monitor",
        state=state,
        note=note,
        duplicate_dropped=1,
        extra={
            "recent_events": recent_events,
            "host_state_table": host_state_table,
            "out_of_order_count": 0,
            "total_logged": 2,
            "duplicate_count": 1,
            "detail": {
                "role": "monitor",
                "recent_event_summaries": [
                    {
                        "event_id": event_id,
                        "event_type": "CPU_SPIKE",
                        "severity": "WARN",
                        "host_id": config.HOST_ID,
                        "seq_no": 7,
                        "timestamp": "2026-04-27T10:00:01+00:00",
                    },
                    {
                        "event_id": f"evt-{config.HOST_ID}-6",
                        "event_type": "SERVICE_DOWN",
                        "severity": "ERROR",
                        "host_id": config.HOST_ID,
                        "seq_no": 6,
                        "timestamp": "2026-04-27T09:59:58+00:00",
                    },
                ],
                "last_processed_event": {
                    "event_id": event_id,
                    "event_type": "CPU_SPIKE",
                    "severity": "WARN",
                    "host_id": config.HOST_ID,
                    "seq_no": 7,
                    "timestamp": "2026-04-27T10:00:01+00:00",
                },
                "last_sink_result": {
                    "status": "logged",
                    "event_id": event_id,
                    "host_id": config.HOST_ID,
                    "seq_no": 7,
                },
                "last_ack_result": {
                    "status": "acknowledged",
                    "event_id": event_id,
                    "duplicate": False,
                },
                "last_route_trace": [],
                "last_route_summary": {
                    "route_state": "PRIMARY",
                    "active_route": "primary",
                    "failed_hop": None,
                    "suspected_node": None,
                    "reroute_reason": None,
                },
                "last_fault_localization": {
                    "failure_scope": "unknown",
                    "failed_hop": None,
                    "suspected_node": None,
                    "failure_reason": None,
                    "confidence": "low",
                    "basis": "route_trace_unavailable",
                },
                "traffic": _traffic(
                    {
                        "peer_node_id": "r2",
                        "peer_role": "relay",
                        "hop_state": "acknowledged",
                        "failure_reason": None,
                        "last_received": _capture(
                            {"msg_type": "EVENT", "event_id": event_id, "event_type": "CPU_SPIKE", "severity": "WARN", "host_id": config.HOST_ID, "seq_no": 7, "timestamp": "2026-04-27T10:00:01+00:00", "payload": {"cpu": 96}},
                            logical_id=event_id,
                            phase="sink_event",
                        ),
                        "last_sent": _capture(
                            {"msg_type": "ACK", "ack_for": event_id, "from_node": "monitor", "timestamp": "2026-04-27T10:00:03+00:00"},
                            logical_id=event_id,
                            phase="sink_ack",
                        ),
                    },
                    {
                        "peer_node_id": None,
                        "peer_role": None,
                        "hop_state": "not_applicable",
                        "failure_reason": None,
                        "last_received": None,
                        "last_sent": None,
                    },
                ),
            },
        },
    )
