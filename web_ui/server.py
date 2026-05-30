from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import signal
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from nw_sim import config
from nw_sim.controller_client import build_requests
from nw_sim.controller_ui import ControllerUI
from nw_sim.system import LocalProcessSupervisor


CONTROL_TOKEN_ENV_VAR = "NW_CONTROL_TOKEN"
STATIC_DIR = Path(__file__).resolve().parent / "static"
POWER_START_LOCK_SECONDS = 6.0
POWER_STOP_LOCK_SECONDS = 4.0
POWER_STOP_DRAIN_SECONDS = 1.5


class WebRuntime:
    def __init__(
        self,
        *,
        control_host: str,
        control_port: int,
        web_host: str,
        web_port: int,
        control_token: str,
        start_roles: bool,
        dynamic_node_ports: bool,
    ) -> None:
        self.control_host = control_host
        self.control_port = control_port
        self.web_host = web_host
        self.web_port = web_port
        self.control_token = control_token
        self.start_roles = start_roles
        self.dynamic_node_ports = dynamic_node_ports and start_roles
        self.node_endpoints = allocate_node_endpoints(control_host) if self.dynamic_node_ports else config.runtime_node_endpoints()
        self.controller = ControllerUI(
            control_host=control_host,
            control_port=control_port,
            node_endpoints=self.node_endpoints,
            control_token=control_token,
            public_external_control=False,
        )
        self.supervisor = (
            LocalProcessSupervisor(control_host, control_port, control_token, node_endpoints=self.node_endpoints) if start_roles else None
        )
        self.loop: asyncio.AbstractEventLoop | None = None
        self.control_server: asyncio.AbstractServer | None = None
        self.http_server: ThreadingHTTPServer | None = None
        self.http_thread: threading.Thread | None = None
        self._stop_event = asyncio.Event()
        self._power_lock: asyncio.Lock = asyncio.Lock()
        self._power_transition_until: float = 0.0

    async def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.control_server = await asyncio.start_server(
            self.controller._handle_control_connection,
            self.control_host,
            self.control_port,
        )
        self.controller._record_activity(f"Web UI 상태 수신 대기: {self.control_host}:{self.control_port}", "system")
        if self.supervisor is not None:
            await self.supervisor.start()
            self.controller._record_activity("Web UI runtime이 node role 프로세스를 시작했습니다", "system")

        handler = make_handler(self)
        self.http_server = ThreadingHTTPServer((self.web_host, self.web_port), handler)
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, name="web-ui-http", daemon=True)
        self.http_thread.start()
        self.controller._record_activity(f"Web UI HTTP surface: http://{self.web_host}:{self.web_port}", "system")

    async def stop(self) -> None:
        if self.http_server is not None:
            await asyncio.to_thread(self.http_server.shutdown)
            self.http_server.server_close()
        if self.http_thread is not None:
            self.http_thread.join(timeout=2.0)
        if self.supervisor is not None:
            await self.supervisor.stop()
        if self.control_server is not None:
            self.control_server.close()
            await self.control_server.wait_closed()
        self.controller._renderer.close()

    async def run(self, duration: float | None = None) -> None:
        await self.start()
        try:
            if duration is None:
                await self._stop_event.wait()
            else:
                await asyncio.sleep(duration)
        finally:
            await self.stop()

    def request_stop(self) -> None:
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self._stop_event.set)

    def snapshot(self) -> dict[str, Any]:
        snapshot = self.controller.runtime_state_snapshot()
        node_power = self.node_power_status()
        if node_power["state"] == "stopped":
            for node in snapshot.get("nodes", []):
                if isinstance(node, dict):
                    node["observed_liveness"] = "offline"
                    node["note"] = "Web UI 전원 꺼짐"
        snapshot["node_power"] = node_power
        return snapshot

    def node_power_status(self) -> dict[str, Any]:
        now = self.loop.time() if self.loop is not None else 0.0
        if self.supervisor is None:
            state = "external"
        elif self._power_transition_until > now:
            state = "transitioning"
        elif self.supervisor.is_running():
            state = "running"
        else:
            state = "stopped"
        return {
            "state": state,
            "can_control": self.supervisor is not None,
            "lock_remaining_sec": max(0.0, self._power_transition_until - now),
            "dynamic_ports": self.dynamic_node_ports,
            "node_endpoints": endpoint_payload(self.node_endpoints),
        }

    def node_port_conflicts(self) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        for node_id, endpoint in self.node_endpoints.items():
            host, port = endpoint
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.2)
                if probe.connect_ex((host, port)) == 0:
                    conflicts.append({"node_id": node_id, "host": host, "port": port})
        return conflicts

    def submit_command_line(self, line: str) -> dict[str, Any]:
        if self.loop is None:
            return {"ok": False, "reason": "runtime_not_started"}
        future = asyncio.run_coroutine_threadsafe(self._submit_command_line(line), self.loop)
        return future.result(timeout=3.0)

    def set_node_power(self, action: str) -> dict[str, Any]:
        if self.loop is None:
            return {"ok": False, "reason": "runtime_not_started"}
        future = asyncio.run_coroutine_threadsafe(self._set_node_power(action), self.loop)
        return future.result(timeout=POWER_START_LOCK_SECONDS + POWER_STOP_LOCK_SECONDS)

    async def _submit_command_line(self, line: str) -> dict[str, Any]:
        requests, should_exit, local_message = build_requests(line)
        if local_message:
            self.controller._record_activity(local_message, "control")
            return {"ok": False, "message": local_message}
        for request in requests:
            await self.controller._apply_remote_request(request)
        if should_exit:
            self._stop_event.set()
        return {"ok": True, "command": line, "should_exit": should_exit}

    async def _set_node_power(self, action: str) -> dict[str, Any]:
        if self.supervisor is None:
            return {"ok": False, "reason": "supervisor_disabled", "node_power": self.node_power_status()}
        if action not in {"start", "stop"}:
            return {"ok": False, "reason": "invalid_action", "node_power": self.node_power_status()}
        async with self._power_lock:
            now = self.loop.time() if self.loop is not None else 0.0
            if self._power_transition_until > now:
                return {"ok": False, "reason": "transition_in_progress", "node_power": self.node_power_status()}
            if action == "start":
                if not self.supervisor.is_running():
                    conflicts = self.node_port_conflicts()
                    if conflicts:
                        self.controller._record_activity("Web UI 전원 버튼: node port 점유로 시작을 중단했습니다", "system")
                        return {
                            "ok": False,
                            "reason": "port_conflict",
                            "conflicts": conflicts,
                            "node_power": self.node_power_status(),
                        }
                self._power_transition_until = now + POWER_START_LOCK_SECONDS
                await self.supervisor.start()
                self.controller._record_activity("Web UI 전원 버튼: node role 프로세스를 시작했습니다", "system")
                return {"ok": True, "action": action, "lock_sec": POWER_START_LOCK_SECONDS, "node_power": self.node_power_status()}

            self._power_transition_until = now + POWER_STOP_LOCK_SECONDS
            await asyncio.sleep(POWER_STOP_DRAIN_SECONDS)
            await self.supervisor.stop()
            self.controller._record_activity("Web UI 전원 버튼: node role 프로세스를 안전 종료했습니다", "system")
            return {"ok": True, "action": action, "lock_sec": POWER_STOP_LOCK_SECONDS, "node_power": self.node_power_status()}


def make_handler(runtime: WebRuntime):
    class WebUIRequestHandler(BaseHTTPRequestHandler):
        server_version = "NWWebUI/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/health":
                self._send_json({"ok": True})
                return
            if parsed.path == "/api/state":
                self._send_json(runtime.snapshot())
                return
            self._serve_static(parsed.path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/power":
                self._handle_power_post()
                return
            if parsed.path != "/api/control":
                self._send_json({"ok": False, "reason": "not_found"}, HTTPStatus.NOT_FOUND)
                return
            payload = self._read_json_body()
            if not isinstance(payload, dict):
                self._send_json({"ok": False, "reason": "invalid_json"}, HTTPStatus.BAD_REQUEST)
                return
            line = payload.get("line")
            if not isinstance(line, str) or not line.strip():
                self._send_json({"ok": False, "reason": "missing_line"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                result = runtime.submit_command_line(line.strip())
            except Exception as error:
                result = {"ok": False, "reason": str(error)}
            self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)

        def _handle_power_post(self) -> None:
            payload = self._read_json_body()
            if not isinstance(payload, dict):
                self._send_json({"ok": False, "reason": "invalid_json"}, HTTPStatus.BAD_REQUEST)
                return
            action = payload.get("action")
            if not isinstance(action, str):
                self._send_json({"ok": False, "reason": "missing_action"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                result = runtime.set_node_power(action.strip().lower())
            except Exception as error:
                result = {"ok": False, "reason": str(error)}
            self._send_json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)

        def _read_json_body(self) -> Any:
            length = int(self.headers.get("content-length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                return json.loads(raw_body or "{}")
            except json.JSONDecodeError:
                return None

        def _serve_static(self, path: str) -> None:
            relative_path = "index.html" if path in {"", "/"} else path.lstrip("/")
            target = (STATIC_DIR / relative_path).resolve()
            if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
                self._send_json({"ok": False, "reason": "not_found"}, HTTPStatus.NOT_FOUND)
                return
            content_types = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "text/javascript; charset=utf-8",
            }
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", content_types.get(target.suffix, "application/octet-stream"))
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return WebUIRequestHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NW project runtime Web UI")
    parser.add_argument("--web-host", default=config.DEFAULT_HOST)
    parser.add_argument("--web-port", type=int, default=8080)
    parser.add_argument("--control-host", default=config.DEFAULT_HOST)
    parser.add_argument("--control-port", type=int, default=config.CONTROLLER_PORT)
    parser.add_argument("--control-token", default=None)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--no-supervisor", action="store_true", help="Do not start local node role processes.")
    parser.add_argument(
        "--fixed-node-ports",
        action="store_true",
        help="Use documented fixed node ports instead of allocating free ports for the supervised Web UI runtime.",
    )
    return parser.parse_args()


def allocate_node_endpoints(host: str) -> dict[str, tuple[str, int]]:
    endpoints: dict[str, tuple[str, int]] = {}
    sockets: list[socket.socket] = []
    try:
        for node_id in config.NODE_ORDER:
            reserved = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            reserved.bind((host, 0))
            reserved.listen(1)
            sockets.append(reserved)
            endpoints[node_id] = (host, reserved.getsockname()[1])
    finally:
        for reserved in sockets:
            reserved.close()
    return endpoints


def endpoint_payload(endpoints: dict[str, tuple[str, int]]) -> dict[str, dict[str, int | str]]:
    return {node_id: {"host": host, "port": port} for node_id, (host, port) in endpoints.items()}


async def async_main() -> None:
    args = parse_args()
    control_token = args.control_token or os.environ.get(CONTROL_TOKEN_ENV_VAR) or secrets.token_urlsafe(12)
    runtime = WebRuntime(
        control_host=args.control_host,
        control_port=args.control_port,
        web_host=args.web_host,
        web_port=args.web_port,
        control_token=control_token,
        start_roles=not args.no_supervisor,
        dynamic_node_ports=not args.fixed_node_ports,
    )
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, runtime.request_stop)
        except NotImplementedError:
            pass
    await runtime.run(duration=args.duration)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
