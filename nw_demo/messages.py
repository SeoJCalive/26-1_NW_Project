from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def encode_message(message: dict[str, Any]) -> str:
    return json.dumps(message, sort_keys=True)


def decode_message(raw_message: str) -> dict[str, Any]:
    return json.loads(raw_message)


def json_roundtrip(message: dict[str, Any]) -> dict[str, Any]:
    return decode_message(encode_message(message))


def make_ack(ack_for: str, from_node: str) -> dict[str, Any]:
    return {
        "msg_type": "ACK",
        "ack_for": ack_for,
        "from_node": from_node,
        "timestamp": iso_now(),
    }


def make_control(
    command: str,
    target: str,
    params: dict[str, Any] | None = None,
    control_token: str | None = None,
) -> dict[str, Any]:
    message = {
        "msg_type": "CONTROL",
        "command": command,
        "target": target,
        "params": params or {},
        "timestamp": iso_now(),
    }
    if control_token:
        message["control_token"] = control_token
    return message


def make_status(
    node_id: str,
    state: str,
    queue_length: int,
    pending_ack_count: int,
    retry_total: int,
    duplicate_dropped: int,
    note: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message = {
        "msg_type": "STATUS",
        "node_id": node_id,
        "state": state,
        "queue_length": queue_length,
        "pending_ack_count": pending_ack_count,
        "retry_total": retry_total,
        "duplicate_dropped": duplicate_dropped,
        "note": note,
        "timestamp": iso_now(),
    }
    if extra:
        message.update(extra)
    return message


def make_status_report(status: dict[str, Any], control_token: str | None = None) -> dict[str, Any]:
    if not control_token:
        return status
    return {
        "msg_type": "STATUS_REPORT",
        "control_token": control_token,
        "status": status,
        "timestamp": iso_now(),
    }
