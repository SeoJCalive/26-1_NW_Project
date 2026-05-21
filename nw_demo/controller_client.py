from __future__ import annotations

import asyncio
import shlex
from typing import Any

from .messages import encode_message, make_control


HELP_TEXT = (
    "명령어: help, start [node], pause [node], reset [node|all], kill <node>, "
    "fault cpu|service|latency on|off|[sec], ackdrop, delay r1|r2 [sec], quit, exit"
)


VALID_NODE_TARGETS = {"all", "host-simulator", "local-agent", "r1", "r2", "monitor"}


def _resolve_target(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.lower()
    aliases = {
        "host": "host-simulator",
        "agent": "local-agent",
        "relay-r1": "r1",
        "relay-r2": "r2",
    }
    target = aliases.get(candidate, candidate)
    return target if target in VALID_NODE_TARGETS else None


def build_requests(line: str) -> tuple[list[dict[str, Any]], bool, str | None]:
    if not line:
        return [], False, None

    try:
        parts = shlex.split(line)
    except ValueError as error:
        return [], False, f"명령 파싱 오류: {error}"
    command = parts[0].lower()

    if command == "help":
        return [], False, HELP_TEXT

    if command in {"quit", "exit"}:
        return [{"kind": "shutdown", "display": f"제어 명령 -> all: {command} {{}}"}], True, None

    if command in {"start", "pause"}:
        target = _resolve_target(parts[1] if len(parts) > 1 else "all")
        if target is None:
            return [], False, f"알 수 없는 node 대상: {parts[1]}"
        return [
            {
                "kind": "control",
                "message": make_control(command, target),
                "display": f"제어 명령 -> {target}: {command} {{}}",
            }
        ], False, None

    if command == "reset":
        target = _resolve_target(parts[1] if len(parts) > 1 else "all")
        if target is None:
            return [], False, f"알 수 없는 node 대상: {parts[1]}"
        if target != "all":
            return [
                {
                    "kind": "control",
                    "message": make_control("reset", target),
                    "display": f"제어 명령 -> {target}: reset {{}}",
                }
            ], False, None
        return [
            {"kind": "reset_all", "display": "제어 명령 -> all: reset {}"},
        ], False, None

    if command == "kill":
        if len(parts) < 2:
            return [], False, "kill 명령에는 대상 node가 필요합니다: host-simulator|local-agent|r1|r2|monitor"
        target = _resolve_target(parts[1])
        if not target or target == "all":
            return [], False, f"kill 대상이 올바르지 않습니다: {parts[1]}"
        return [
            {
                "kind": "control",
                "message": make_control("shutdown", target),
                "display": f"제어 명령 -> {target}: shutdown {{}}",
            }
        ], False, None

    if command == "ackdrop":
        return [
            {
                "kind": "control",
                "message": make_control("drop_next_ack", "monitor"),
                "display": "제어 명령 -> monitor: drop_next_ack {}",
            }
        ], False, None

    if command == "fault":
        mapping = {"cpu": "CPU_SPIKE", "service": "SERVICE_DOWN", "latency": "LATENCY_HIGH"}
        fault_key = parts[1].lower() if len(parts) > 1 else "cpu"
        fault_type = mapping.get(fault_key, "CPU_SPIKE")
        mode = parts[2].lower() if len(parts) > 2 else "on"
        if mode in {"on", "off"}:
            params = {"fault_type": fault_type, "enabled": mode == "on"}
            return [
                {
                    "kind": "control",
                    "message": make_control("set_fault", "host-simulator", params),
                    "display": f"제어 명령 -> host-simulator: set_fault {params}",
                }
            ], False, None
        try:
            duration = int(mode)
        except ValueError:
            return [], False, f"fault mode가 올바르지 않습니다: {parts[2]}"
        params = {"fault_type": fault_type, "duration_sec": duration}
        return [
            {
                "kind": "control",
                "message": make_control("inject_fault", "host-simulator", params),
                "display": f"제어 명령 -> host-simulator: inject_fault {params}",
            }
        ], False, None

    if command == "delay":
        relay_name = parts[1].lower() if len(parts) > 1 else "r1"
        try:
            seconds = float(parts[2]) if len(parts) > 2 else 0.75
        except ValueError:
            return [], False, f"delay seconds가 올바르지 않습니다: {parts[2]}"
        target = "r1" if relay_name == "r1" else "r2"
        params = {"seconds": seconds}
        return [
            {
                "kind": "control",
                "message": make_control("set_delay", target, params),
                "display": f"제어 명령 -> {target}: set_delay {params}",
            }
        ], False, None

    return [], False, f"알 수 없는 명령어: {line}"


async def send_request(host: str, port: int, request: dict[str, Any]) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write((encode_message(request) + "\n").encode())
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def run_controller_client(host: str, port: int, control_token: str | None) -> None:
    print(f"외부 컨트롤러 연결 대상: {host}:{port}")
    print(HELP_TEXT)
    while True:
        try:
            line = await asyncio.to_thread(input, "controller> ")
        except EOFError:
            break

        requests, should_exit, local_message = build_requests(line.strip())
        if local_message:
            print(local_message)
            continue

        try:
            for request in requests:
                kind = request.get("kind")
                if kind == "control":
                    message = request.get("message")
                    if not isinstance(message, dict):
                        continue
                    outbound = dict(message)
                    if control_token:
                        outbound["control_token"] = control_token
                    await send_request(host, port, outbound)
                    continue
                if kind == "reset_all":
                    await send_request(host, port, make_control("reset", "all", control_token=control_token))
                    continue
                if kind == "shutdown":
                    outbound = dict(request)
                    if control_token:
                        outbound["control_token"] = control_token
                    await send_request(host, port, outbound)
        except OSError as error:
            print(f"컨트롤러 연결 실패: {error}")
            if should_exit:
                break
            continue

        if should_exit:
            break
