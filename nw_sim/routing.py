from __future__ import annotations

from typing import Any

from .messages import iso_now, json_roundtrip


ROUTE_PRIMARY = "primary"
ROUTE_BACKUP = "backup"

ROUTE_STATE_PRIMARY = "PRIMARY"
ROUTE_STATE_BYPASS_ACTIVE = "BYPASS_ACTIVE"
ROUTE_STATE_DEGRADED = "DEGRADED"
ROUTE_STATE_FAILED = "FAILED"

ROUTE_STATES = {
    ROUTE_STATE_PRIMARY,
    ROUTE_STATE_BYPASS_ACTIVE,
    ROUTE_STATE_DEGRADED,
    ROUTE_STATE_FAILED,
}

PRIMARY_PATH = ("local-agent", "r1", "r2", "monitor")
BACKUP_PATH = ("local-agent", "r1b", "r2b", "monitor")

ALLOWED_ROUTE_EDGES = {
    ("local-agent", "r1"): ROUTE_PRIMARY,
    ("r1", "r2"): ROUTE_PRIMARY,
    ("r2", "monitor"): ROUTE_PRIMARY,
    ("local-agent", "r1b"): ROUTE_BACKUP,
    ("r1b", "r2b"): ROUTE_BACKUP,
    ("r2b", "monitor"): ROUTE_BACKUP,
}


def route_id_for_edge(from_node: str, to_node: str) -> str | None:
    return ALLOWED_ROUTE_EDGES.get((from_node, to_node))


def validate_route_edge(from_node: str, to_node: str) -> str:
    route_id = route_id_for_edge(from_node, to_node)
    if route_id is None:
        raise ValueError(f"forbidden route edge: {from_node}->{to_node}")
    return route_id


def make_route_trace_entry(
    *,
    from_node: str,
    to_node: str,
    route_id: str,
    attempt_no: int,
    phase: str,
    result: str,
    failure_reason: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    edge_route_id = validate_route_edge(from_node, to_node)
    if route_id not in {ROUTE_PRIMARY, ROUTE_BACKUP}:
        raise ValueError(f"unknown route id: {route_id}")
    if route_id != edge_route_id:
        raise ValueError(f"route id {route_id} does not match edge {from_node}->{to_node}")
    return {
        "from_node": from_node,
        "to_node": to_node,
        "route_id": route_id,
        "attempt_no": attempt_no,
        "phase": phase,
        "result": result,
        "failure_reason": failure_reason,
        "timestamp": timestamp or iso_now(),
    }


def default_event_routing() -> dict[str, Any]:
    return {
        "route_state": ROUTE_STATE_PRIMARY,
        "active_route": ROUTE_PRIMARY,
        "failed_hop": None,
        "suspected_node": None,
        "reroute_reason": None,
    }


def initialize_event_route_metadata(event: dict[str, Any]) -> dict[str, Any]:
    routed_event = json_roundtrip(event)
    routed_event.setdefault("route_trace", [])
    routed_event.setdefault("routing", default_event_routing())
    return routed_event


def default_detail_routing(
    *,
    event_id: str | None = None,
    active_downstream: str | None = None,
    primary_downstream: str | None = None,
    backup_downstream: str | None = None,
) -> dict[str, Any]:
    return {
        "route_state": ROUTE_STATE_PRIMARY,
        "active_route": ROUTE_PRIMARY,
        "primary_downstream": primary_downstream,
        "backup_downstream": backup_downstream,
        "active_downstream": active_downstream or primary_downstream,
        "failed_downstream": None,
        "reroute_reason": None,
        "event_id": event_id,
        "route_generation": 0,
    }


def summarize_event_routing(event: dict[str, Any]) -> dict[str, Any]:
    routing = event.get("routing")
    if isinstance(routing, dict):
        return {
            "route_state": routing.get("route_state"),
            "active_route": routing.get("active_route"),
            "failed_hop": routing.get("failed_hop"),
            "suspected_node": routing.get("suspected_node"),
            "reroute_reason": routing.get("reroute_reason"),
        }
    return default_event_routing()


def fault_localization_from_event(event: dict[str, Any]) -> dict[str, Any]:
    trace = event.get("route_trace")
    if not isinstance(trace, list) or not trace:
        return {
            "failure_scope": "unknown",
            "failed_hop": None,
            "suspected_node": None,
            "failure_reason": None,
            "confidence": "low",
            "basis": "route_trace_unavailable",
        }

    success_results = {"acknowledged", "forwarded", "ok", "success"}
    failed_entries = [
        entry for entry in trace
        if isinstance(entry, dict) and entry.get("result") not in success_results
    ]
    if not failed_entries:
        return {
            "failure_scope": "unknown",
            "failed_hop": None,
            "suspected_node": None,
            "failure_reason": None,
            "confidence": "low",
            "basis": "route_trace_no_failed_hop",
        }

    failed_entry = failed_entries[-1]
    from_node = failed_entry.get("from_node")
    to_node = failed_entry.get("to_node")
    failed_hop = f"{from_node}->{to_node}" if from_node and to_node else None
    return {
        "failure_scope": "hop" if failed_hop else "unknown",
        "failed_hop": failed_hop,
        "suspected_node": to_node,
        "failure_reason": failed_entry.get("failure_reason") or failed_entry.get("result"),
        "confidence": "medium" if failed_hop else "low",
        "basis": "route_trace_failed_hop" if failed_hop else "route_trace_ambiguous",
    }
