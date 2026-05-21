from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import signal
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from nw_demo import config
from nw_demo.controller_client import build_requests
from nw_demo.controller_ui import ControllerUI
from nw_demo.system import LocalProcessSupervisor


CONTROL_TOKEN_ENV_VAR = "NW_CONTROL_TOKEN"
STATIC_DIR = Path(__file__).resolve().parent / "static"


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
    ) -> None:
        self.control_host = control_host
        self.control_port = control_port
        self.web_host = web_host
        self.web_port = web_port
        self.control_token = control_token
        self.start_roles = start_roles
        self.controller = ControllerUI(
            control_host=control_host,
            control_port=control_port,
            node_endpoints=config.NODE_ENDPOINTS,
            control_token=control_token,
            public_external_control=False,
        )
        self.supervisor = LocalProcessSupervisor(control_host, control_port, control_token) if start_roles else None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.control_server: asyncio.AbstractServer | None = None
        self.http_server: ThreadingHTTPServer | None = None
        self.http_thread: threading.Thread | None = None
        self._stop_event = asyncio.Event()

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
        return self.controller.runtime_state_snapshot()

    def submit_command_line(self, line: str) -> dict[str, Any]:
        if self.loop is None:
            return {"ok": False, "reason": "runtime_not_started"}
        future = asyncio.run_coroutine_threadsafe(self._submit_command_line(line), self.loop)
        return future.result(timeout=3.0)

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
    return parser.parse_args()


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
