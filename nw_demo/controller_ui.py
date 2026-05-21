from __future__ import annotations

import asyncio
import contextlib
import hashlib
import inspect
import json
import os
import select
import shutil
import sys
import termios
import threading
import time
import tty
import unicodedata
from collections import deque
from typing import Any, Awaitable, Callable, Protocol

from . import config
from .controller_client import build_requests
from .messages import decode_message, make_control
from .transport import send_request


_NODE_ROLES = {
    "host-simulator": "host",
    "local-agent": "agent",
    "r1": "relay",
    "r2": "relay",
    "r1b": "relay",
    "r2b": "relay",
    "monitor": "monitor",
}

_VALID_FOCUS_TARGETS = tuple(config.NODE_ORDER)
_FOCUS_TARGET_ALIASES = {
    "host": "host-simulator",
    "agent": "local-agent",
}
_FOCUSED_NODE_ACTIVITY_LIMIT = 10

_STATUS_BASE_FIELDS = {
    "msg_type",
    "node_id",
    "state",
    "queue_length",
    "pending_ack_count",
    "retry_total",
    "duplicate_dropped",
    "note",
}

_STALE_STATUS_MULTIPLIER = 2.5
_OFFLINE_STATUS_MULTIPLIER = 6.0

_DISPLAY_EVENT_TYPES = {
    "HOST_STATE_UPDATE": "상태 갱신",
    "CPU_SPIKE": "CPU 급등",
    "SERVICE_DOWN": "서비스 장애",
    "LATENCY_HIGH": "지연 증가",
}
_DISPLAY_SEVERITIES = {
    "INFO": "정보",
    "WARN": "주의",
    "ERROR": "위험",
}
_DISPLAY_SERVICE_STATES = {
    "UP": "정상",
    "DOWN": "중단",
}
_DISPLAY_FAULT_MODES = {
    "NORMAL": "정상",
    "CPU_SPIKE": "CPU 급등",
    "SERVICE_DOWN": "서비스 장애",
    "LATENCY_HIGH": "지연 증가",
}
_DISPLAY_HOP_STATES = {
    "acknowledged": "확인 완료",
    "timeout": "응답 시간 초과",
    "retrying": "재시도 중",
    "not_started": "대기 중",
    "not_applicable": "다음 구간 없음",
    "unknown": "알 수 없음",
}
_DISPLAY_ROUTE_STATES = {
    "PRIMARY": "기본 경로",
    "BYPASS_ACTIVE": "우회 경로 사용",
    "DEGRADED": "성능 저하",
    "FAILED": "전달 실패",
}
_DISPLAY_ROUTE_IDS = {
    "primary": "primary",
    "backup": "backup",
}


def _role_for_node(node_id: str) -> str:
    return _NODE_ROLES.get(node_id, "unknown")


def _status_indicates_kill_request(status: dict[str, Any], kill_requested: bool) -> bool:
    if kill_requested:
        return True
    note = status.get("note")
    return isinstance(note, str) and note == "종료 요청 수신"


def derive_node_liveness(last_seen: float | None, now: float, kill_requested: bool = False) -> str:
    if last_seen is None:
        return "unknown"

    elapsed = max(0.0, now - last_seen)
    stale_after = config.STATUS_REFRESH_SECONDS * _STALE_STATUS_MULTIPLIER
    offline_after = config.STATUS_REFRESH_SECONDS * _OFFLINE_STATUS_MULTIPLIER

    if elapsed > offline_after:
        return "offline"
    if elapsed > stale_after:
        return "stale"
    if kill_requested:
        return "kill_requested"
    return "live"


def normalize_node_view(
    node_id: str,
    status: dict[str, Any] | None,
    last_seen: float | None,
    now: float,
    kill_requested: bool = False,
) -> dict[str, Any]:
    status_data = dict(status or {})
    kill_requested = _status_indicates_kill_request(status_data, kill_requested)
    details = {key: value for key, value in status_data.items() if key not in _STATUS_BASE_FIELDS}
    return {
        "node_id": node_id,
        "role": _role_for_node(node_id),
        "reported_state": str(status_data.get("state", "UNKNOWN")),
        "observed_liveness": derive_node_liveness(last_seen=last_seen, now=now, kill_requested=kill_requested),
        "last_seen": last_seen,
        "queue_length": status_data.get("queue_length", 0),
        "pending_ack_count": status_data.get("pending_ack_count", 0),
        "retry_total": status_data.get("retry_total", 0),
        "duplicate_dropped": status_data.get("duplicate_dropped", 0),
        "note": status_data.get("note", "-"),
        "details": details,
        "kill_requested": kill_requested,
        "controls": {
            "start": {"command": "start", "target": node_id},
            "pause": {"command": "pause", "target": node_id},
            "reset": {"command": "reset", "target": node_id},
            "kill": {"command": "shutdown", "target": node_id},
        },
    }


def _format_node_state(node_view: dict[str, Any]) -> str:
    observed_liveness = node_view["observed_liveness"]
    reported_state = node_view["reported_state"]
    if observed_liveness == "unknown":
        return "UNKNOWN"
    if observed_liveness == "live":
        return reported_state
    return f"{reported_state}({observed_liveness})"


def _format_last_seen(last_seen: float | None, now: float) -> str:
    if last_seen is None:
        return "never"
    return f"{max(0.0, now - last_seen):.1f}s ago"


def _format_control_summary(node_view: dict[str, Any]) -> str:
    controls = node_view["controls"]
    return (
        f"start={controls['start']['target']} "
        f"pause={controls['pause']['target']} "
        f"reset={controls['reset']['target']} "
        f"kill={controls['kill']['target']}"
    )


def _safe_text(value: Any) -> str:
    text = str(value)
    safe_characters: list[str] = []
    for character in text:
        if character in {"\n", "\r", "\t"}:
            safe_characters.append(" ")
        elif ord(character) >= 32 and ord(character) != 127:
            safe_characters.append(character)
    return "".join(safe_characters)


def _display_cell_width(text: str) -> int:
    width = 0
    for character in text:
        if unicodedata.combining(character):
            continue
        if unicodedata.east_asian_width(character) in {"F", "W"}:
            width += 2
        else:
            width += 1
    return width


def _iter_display_cells(text: str) -> list[tuple[str, int]]:
    cells: list[tuple[str, int]] = []
    for character in text:
        if unicodedata.combining(character):
            cells.append((character, 0))
        elif unicodedata.east_asian_width(character) in {"F", "W"}:
            cells.append((character, 2))
        else:
            cells.append((character, 1))
    return cells


def _display_keyword(value: Any, mapping: dict[str, str]) -> str:
    text = _safe_text(value if value not in {None, ""} else "-")
    return mapping.get(text, text)


def _fit_display_text(value: Any, width: int) -> str:
    text = _safe_text(value)
    if width <= 0:
        return ""
    if _display_cell_width(text) <= width:
        return text
    if width == 1:
        return "~"

    target_width = width - 1
    used_width = 0
    fitted_characters: list[str] = []
    for character, cell_width in _iter_display_cells(text):
        if used_width + cell_width > target_width:
            break
        fitted_characters.append(character)
        used_width += cell_width
    return "".join(fitted_characters) + "~"


def _pad_display_text(value: Any, width: int) -> str:
    text = _fit_display_text(value, width)
    padding = max(0, width - _display_cell_width(text))
    return text + " " * padding


def _derive_peer_hop_state(
    peer_snapshot: dict[str, Any],
    node_last_seen: dict[str, float],
) -> str:
    hop_state = str(peer_snapshot.get("hop_state", "unknown"))
    peer_node_id = peer_snapshot.get("peer_node_id")
    if hop_state == "unknown" and isinstance(peer_node_id, str) and peer_node_id and peer_node_id not in node_last_seen:
        return "not_started"
    return hop_state


class FrameRenderer(Protocol):
    def render(self, lines: list[str]) -> None:
        ...

    def close(self) -> None:
        ...


class PlaintextRenderer:
    def __init__(self, stream: Any) -> None:
        self.stream = stream
        self._last_frame: str | None = None

    def render(self, lines: list[str]) -> None:
        frame = "\n".join(lines)
        if frame == self._last_frame:
            return
        self.stream.write(frame + "\n")
        self.stream.flush()
        self._last_frame = frame

    def close(self) -> None:
        return None


class InPlaceRenderer:
    def __init__(self, stream: Any) -> None:
        self.stream = stream
        self._last_lines: list[str] = []
        self._entered = False
        self._write_lock = threading.Lock()

    def render(self, lines: list[str]) -> None:
        terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        prompt_row = max(1, terminal_size.lines)
        max_frame_lines = max(1, prompt_row - 1)
        rendered_lines = list(lines[:max_frame_lines])
        if len(lines) > max_frame_lines:
            hidden_count = len(lines) - max_frame_lines
            rendered_lines[-1] = f"... {hidden_count}개 줄 생략됨: 터미널 높이를 늘리면 더 볼 수 있습니다"

        if not self._entered:
            self.stream.write("\x1b[?1049h\x1b[?25l\x1b[H")
            self._entered = True

        updates: list[str] = []
        max_lines = min(max(len(self._last_lines), len(rendered_lines)), max_frame_lines)
        for index in range(max_lines):
            new_line = rendered_lines[index] if index < len(rendered_lines) else ""
            old_line = self._last_lines[index] if index < len(self._last_lines) else None
            if new_line == old_line:
                continue
            updates.append(f"\x1b[{index + 1};1H\x1b[2K{new_line}")

        if len(rendered_lines) < len(self._last_lines) and len(rendered_lines) + 1 < prompt_row:
            updates.append(f"\x1b[{len(rendered_lines) + 1};1H\x1b[J")

        updates.append(f"\x1b[{prompt_row};1H\x1b[2K")

        if updates:
            with self._write_lock:
                self.stream.write("".join(updates))
                self.stream.flush()
        self._last_lines = rendered_lines

    def render_prompt(self, input_text: str) -> None:
        terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        prompt_row = max(1, terminal_size.lines)
        prompt = f"viewer> {input_text}"
        with self._write_lock:
            self.stream.write(f"\x1b[{prompt_row};1H\x1b[2K{prompt}\x1b[?25h")
            self.stream.flush()

    def force_repaint(self) -> None:
        if self._entered:
            with self._write_lock:
                self.stream.write("\x1b[H\x1b[J")
                self.stream.flush()
        self._last_lines = []

    def close(self) -> None:
        if self._entered:
            with self._write_lock:
                self.stream.write("\x1b[?25h\x1b[?1049l")
                self.stream.flush()
            self._entered = False


class ControllerUI:
    def __init__(
        self,
        control_host: str,
        control_port: int,
        node_endpoints: dict[str, tuple[str, int]],
        control_token: str | None = None,
        public_external_control: bool = True,
        focus_node: str | None = None,
    ) -> None:
        self.control_host = control_host
        self.control_port = control_port
        self.node_endpoints = node_endpoints
        self.control_token = control_token
        self.public_external_control = public_external_control
        self.focus_node = focus_node
        self.node_status: dict[str, dict[str, Any]] = {}
        self.node_last_seen: dict[str, float] = {}
        self.system_activity_log: deque[str] = deque(maxlen=config.RECENT_ACTIVITY_LIMIT)
        self.control_activity_log: deque[str] = deque(maxlen=config.RECENT_ACTIVITY_LIMIT)
        self.node_activity_log: deque[str] = deque(maxlen=config.RECENT_ACTIVITY_LIMIT)
        self._tasks: list[asyncio.Task[Any]] = []
        self._stop_requested = False
        self._control_server: asyncio.AbstractServer | None = None
        self._renderer: FrameRenderer = self._create_renderer()
        self._input_waiting = False
        self._input_buffer = ""

    def _create_renderer(self) -> FrameRenderer:
        term = os.environ.get("TERM", "")
        if sys.stdout.isatty() and term and term.lower() != "dumb":
            return InPlaceRenderer(sys.stdout)
        return PlaintextRenderer(sys.stdout)

    def _record_activity(self, entry: str, section: str) -> None:
        entry = _safe_text(entry)
        if section == "system":
            self.system_activity_log.appendleft(entry)
        elif section == "control":
            self.control_activity_log.appendleft(entry)
        else:
            self.node_activity_log.appendleft(entry)

    def _focus_help_text(self) -> str:
        targets = "host|agent|r1|r2|monitor"
        return (
            f"{targets} 중 하나로 모니터 전환: focus <node>. "
            "전체 요약으로 복귀: overview 또는 focus all"
        )

    def _focus_command_hint(self) -> str:
        return "focus host|agent|r1|r2|r1b|r2b|monitor | overview | focus all"

    def _handle_focus_command(self, line: str) -> tuple[bool, str | None]:
        normalized = " ".join(line.strip().split())
        if not normalized:
            return False, None

        parts = normalized.split(" ")
        command = parts[0]
        if command not in {"focus", "overview"}:
            if command.lower() in {"focus", "overview"}:
                message = f"focus/overview 명령은 소문자로 입력하세요. {self._focus_help_text()}"
                self._record_activity(message, "control")
                return True, message
            return False, None

        previous_focus = self.focus_node
        if command == "overview":
            if len(parts) != 1:
                message = f"overview 명령은 추가 인자를 받지 않습니다. {self._focus_help_text()}"
                self._record_activity(message, "control")
                return True, message
            self.focus_node = None
            message = "모니터 화면 전환: 전체 overview"
            self._record_activity(message, "control")
            return True, message

        if len(parts) != 2:
            message = f"focus 명령에는 대상 node 하나가 필요합니다. {self._focus_help_text()}"
            self._record_activity(message, "control")
            return True, message

        target = _FOCUS_TARGET_ALIASES.get(parts[1], parts[1])
        if target == "all":
            self.focus_node = None
            message = "모니터 화면 전환: 전체 overview"
            self._record_activity(message, "control")
            return True, message

        if target not in _VALID_FOCUS_TARGETS:
            self.focus_node = previous_focus
            message = f"알 수 없는 focus 대상: {target}. {self._focus_help_text()}"
            self._record_activity(message, "control")
            return True, message

        self.focus_node = target
        message = f"모니터 화면 전환: {target}"
        self._record_activity(message, "control")
        return True, message

    def _focused_node_activity_entries(self, node_id: str) -> list[str]:
        node_prefix = f"{node_id}: "
        return [
            entry
            for entry in self.node_activity_log
            if entry.startswith(node_prefix)
        ][: _FOCUSED_NODE_ACTIVITY_LIMIT]

    def _node_title(self, node_id: str) -> str:
        titles = {
            "host-simulator": "Host Simulator 모니터링",
            "local-agent": "Local Agent 모니터링",
            "r1": "Relay R1 모니터링",
            "r2": "Relay R2 모니터링",
            "monitor": "Monitor 모니터링",
        }
        return titles.get(node_id, node_id)

    def runtime_state_snapshot(self, now: float | None = None) -> dict[str, Any]:
        now = time.monotonic() if now is None else now
        nodes = []
        for node_id in config.NODE_ORDER:
            status = self.node_status.get(node_id)
            last_seen = self.node_last_seen.get(node_id)
            nodes.append(
                normalize_node_view(
                    node_id,
                    status,
                    last_seen=last_seen,
                    now=now,
                )
            )
        return {
            "source": "controller_gateway_runtime_state",
            "data_path": ["STATUS_REPORT", "Controller/Gateway", "Web UI"],
            "generated_at_monotonic": now,
            "nodes": nodes,
            "activity": {
                "system": list(self.system_activity_log),
                "control": list(self.control_activity_log),
                "node": list(self.node_activity_log),
            },
        }

    def _traffic_summary(self, node_view: dict[str, Any]) -> str:
        traffic = ((node_view["details"].get("detail") or {}).get("traffic") or {})
        previous_peer = traffic.get("previous_peer") or {}
        next_peer = traffic.get("next_peer") or {}
        recent = traffic.get("recent") or []
        latest_capture = recent[0].get("capture") if recent else {}
        logical_id = latest_capture.get("logical_id", "-") if isinstance(latest_capture, dict) else "-"
        return (
            "  hop summary: prev={prev} next={next} last={logical}".format(
                prev=_safe_text(_derive_peer_hop_state(previous_peer, self.node_last_seen)),
                next=_safe_text(_derive_peer_hop_state(next_peer, self.node_last_seen)),
                logical=_safe_text(logical_id),
            )
        )

    def _format_payload_capture(self, capture: dict[str, Any] | None) -> str:
        if not capture:
            return "-"
        if capture.get("truncated"):
            return _safe_text(capture.get("preview", "<truncated>"))
        payload = capture.get("payload")
        if payload is None:
            return "-"
        return _safe_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def _append_focused_traffic_lines(self, lines: list[str], node_view: dict[str, Any]) -> None:
        detail = node_view["details"].get("detail") or {}
        traffic = detail.get("traffic") or {}
        previous_peer = traffic.get("previous_peer") or {}
        next_peer = traffic.get("next_peer") or {}
        recent = traffic.get("recent") or []
        lines.extend(
            [
                "송수신 구조화 모니터:",
                "  이전 노드: peer={peer} role={role} hop={hop} reason={reason}".format(
                    peer=_safe_text(previous_peer.get("peer_node_id", "-")),
                    role=_safe_text(previous_peer.get("peer_role", "-")),
                    hop=_safe_text(_derive_peer_hop_state(previous_peer, self.node_last_seen)),
                    reason=_safe_text(previous_peer.get("failure_reason", "-")),
                ),
                f"    받은 자료: {self._format_payload_capture(previous_peer.get('last_received'))}",
                f"    응답 자료: {self._format_payload_capture(previous_peer.get('last_sent'))}",
                "  다음 노드: peer={peer} role={role} hop={hop} reason={reason}".format(
                    peer=_safe_text(next_peer.get("peer_node_id", "-")),
                    role=_safe_text(next_peer.get("peer_role", "-")),
                    hop=_safe_text(_derive_peer_hop_state(next_peer, self.node_last_seen)),
                    reason=_safe_text(next_peer.get("failure_reason", "-")),
                ),
                f"    보낸 자료: {self._format_payload_capture(next_peer.get('last_sent'))}",
                f"    받은 응답: {self._format_payload_capture(next_peer.get('last_received'))}",
                "  최근 traffic lineage:",
            ]
        )
        if recent:
            for entry in list(recent)[: config.RECENT_ACTIVITY_SECTION_LIMIT]:
                capture = entry.get("capture") or {}
                lines.append(
                    "    - dir={direction} flow={flow} hop={hop} logical={logical} attempt={attempt} phase={phase}".format(
                        direction=_safe_text(entry.get("direction", "-")),
                        flow=_safe_text(entry.get("flow", "-")),
                        hop=_safe_text(entry.get("hop_state", "-")),
                        logical=_safe_text(capture.get("logical_id", "-")),
                        attempt=_safe_text(capture.get("attempt_no", "-")),
                        phase=_safe_text(capture.get("phase", "-")),
                    )
                )
        else:
            lines.append("    - 아직 traffic snapshot 없음")

    def _append_host_monitor_lines(self, lines: list[str], node_view: dict[str, Any]) -> None:
        host_state = node_view["details"].get("host_state", {})
        detail = node_view["details"].get("detail", {})
        if not host_state:
            lines.append("  세부 상태: 아직 host 상태 수신 없음")
            return
        lines.append(
            "  host_id={host_id} cpu={cpu}% mem={mem}% service={service} latency={latency}ms ({latency_state}) mode={mode}".format(
                host_id=host_state.get("host_id", "-"),
                cpu=host_state.get("cpu_usage", "-"),
                mem=host_state.get("memory_usage", "-"),
                service=host_state.get("service_state", "-"),
                latency=host_state.get("latency_ms", "-"),
                latency_state=host_state.get("latency_state", "-"),
                mode=host_state.get("fault_mode", "-"),
            )
        )
        lines.append(
            "  host detail: tick={tick} fault_active={active} fault_type={fault_type}".format(
                tick=detail.get("tick", "-"),
                active=detail.get("fault_active", False),
                fault_type=_safe_text(detail.get("fault_type", "-")),
            )
        )

    def _append_agent_monitor_lines(self, lines: list[str], node_view: dict[str, Any]) -> None:
        details = node_view["details"]
        last_event = details.get("last_event", {})
        detail = details.get("detail", {})
        if not last_event:
            lines.append("  최근 이벤트: 아직 생성된 이벤트 없음")
        else:
            payload = last_event.get("payload", {})
            lines.append(
                "  최근 이벤트: {event_id} type={event_type} severity={severity} seq={seq_no}".format(
                    event_id=_safe_text(last_event.get("event_id", "-")),
                    event_type=_safe_text(last_event.get("event_type", "-")),
                    severity=_safe_text(last_event.get("severity", "-")),
                    seq_no=last_event.get("seq_no", "-"),
                )
            )
            lines.append(
                "  payload: cpu={cpu}% mem={mem}% service={service} latency={latency}ms mode={mode}".format(
                    cpu=payload.get("cpu", "-"),
                    mem=payload.get("memory", "-"),
                    service=_safe_text(payload.get("service_state", "-")),
                    latency=payload.get("latency_ms", "-"),
                    mode=_safe_text(payload.get("fault_mode", "-")),
                )
            )
        lines.append(
            "  agent detail: input={input_status} fault={fault} downstream={downstream_status}".format(
                input_status=_safe_text((detail.get("latest_input_result") or {}).get("status", "-")),
                fault=_safe_text(detail.get("detected_fault", "-")),
                downstream_status=_safe_text((detail.get("downstream_result") or {}).get("status", "-")),
            )
        )

    def _append_relay_monitor_lines(self, lines: list[str], node_view: dict[str, Any]) -> None:
        lines.append(
            "  중계 지표: queue={queue} pending={pending} retries={retries} dup={dup}".format(
                queue=node_view["queue_length"],
                pending=node_view["pending_ack_count"],
                retries=node_view["retry_total"],
                dup=node_view["duplicate_dropped"],
            )
        )
        detail = node_view["details"].get("detail", {})
        recent_ids = detail.get("recent_received_event_ids") or []
        pending_ack_state = detail.get("pending_ack_state") or []
        pending_summary = pending_ack_state[0] if pending_ack_state else {}
        lines.append(
            "  relay detail: recent={recent} pending_state={pending_state} attempt={attempt}".format(
                recent=_safe_text(", ".join(str(event_id) for event_id in recent_ids[:2])) if recent_ids else "-",
                pending_state=_safe_text(pending_summary.get("state", "-")),
                attempt=pending_summary.get("attempt", "-"),
            )
        )
        lines.append(
            "  relay outcomes: downstream={downstream} forwarded={forwarded} reason={reason}".format(
                downstream=_safe_text((detail.get("last_downstream_result") or {}).get("status", "-")),
                forwarded=_safe_text((detail.get("last_forwarded_result") or {}).get("status", "-")),
                reason=_safe_text((detail.get("last_downstream_result") or {}).get("reason", "-")),
            )
        )
        lines.append(f"  최근 상태: {_safe_text(node_view['note'])}")

    def _append_monitor_monitor_lines(self, lines: list[str], node_view: dict[str, Any], terminal_width: int = 80) -> None:
        if self.focus_node == "monitor":
            self._append_focused_monitor_board_lines(lines, node_view, terminal_width)
            return

        lines.append(
            "  카운터: duplicates={duplicates} out_of_order={out_of_order} total_logged={total_logged}".format(
                duplicates=node_view["details"].get("duplicate_count", 0),
                out_of_order=node_view["details"].get("out_of_order_count", 0),
                total_logged=node_view["details"].get("total_logged", 0),
            )
        )
        detail = node_view["details"].get("detail", {})
        recent_events = list(node_view["details"].get("recent_events", []))[: config.RECENT_ACTIVITY_SECTION_LIMIT]
        if recent_events:
            lines.append("  최근 이벤트:")
            lines.extend(f"    - {_safe_text(entry)}" for entry in recent_events)
        else:
            lines.append("  최근 이벤트: 아직 없음")
        lines.append(
            "  sink detail: sink={sink} ack={ack}".format(
                sink=_safe_text((detail.get("last_sink_result") or {}).get("status", "-")),
                ack=_safe_text((detail.get("last_ack_result") or {}).get("status", "-")),
            )
        )

    def _format_monitor_event_summary(self, event: dict[str, Any]) -> str:
        return "식별자={event_id} | 종류={event_type} | 등급={severity} | 대상={host_id} | 순번={seq_no}".format(
            event_id=_safe_text(event.get("event_id", "-")),
            event_type=_display_keyword(event.get("event_type", "-"), _DISPLAY_EVENT_TYPES),
            severity=_display_keyword(event.get("severity", "-"), _DISPLAY_SEVERITIES),
            host_id=_safe_text(event.get("host_id", "-")),
            seq_no=_safe_text(event.get("seq_no", "-")),
        )

    def _append_monitor_host_state_lines(self, lines: list[str], host_state_table: dict[str, Any]) -> None:
        if not host_state_table:
            lines.extend(["  Host 최신 상태", "    아직 수신된 host 상태가 없습니다."])
            return

        lines.append("  Host 최신 상태")
        for host_id in sorted(host_state_table):
            host_state = host_state_table.get(host_id) or {}
            payload = host_state.get("payload") or {}
            lines.extend(
                [
                    f"    [{_safe_text(host_id)}]",
                    "      이벤트 : 종류={event_type} / 등급={severity}".format(
                        event_type=_display_keyword(host_state.get("event_type", "-"), _DISPLAY_EVENT_TYPES),
                        severity=_display_keyword(host_state.get("severity", "-"), _DISPLAY_SEVERITIES),
                    ),
                    "      자원   : CPU {cpu}% / 메모리 {memory}%".format(
                        cpu=_safe_text(payload.get("cpu", "-")),
                        memory=_safe_text(payload.get("memory", "-")),
                    ),
                    "      서비스 : 상태={service} / 지연={latency}ms / 장애={mode}".format(
                        service=_display_keyword(payload.get("service_state", "-"), _DISPLAY_SERVICE_STATES),
                        latency=_safe_text(payload.get("latency_ms", "-")),
                        mode=_display_keyword(payload.get("fault_mode", "-"), _DISPLAY_FAULT_MODES),
                    ),
                ]
            )

    def _append_monitor_recent_event_lines(self, lines: list[str], node_view: dict[str, Any]) -> None:
        detail = node_view["details"].get("detail", {})
        summaries = list(detail.get("recent_event_summaries") or [])[: config.RECENT_ACTIVITY_SECTION_LIMIT]
        if summaries:
            lines.append("  최근 알림/이벤트")
            for event in summaries:
                lines.append(f"    - {self._format_monitor_event_summary(event)}")
            return

        recent_events = list(node_view["details"].get("recent_events", []))[: config.RECENT_ACTIVITY_SECTION_LIMIT]
        if recent_events:
            lines.append("  최근 알림/이벤트")
            lines.extend(f"    - {_safe_text(entry)}" for entry in recent_events)
        else:
            lines.extend(["  최근 알림/이벤트", "    아직 표시할 알림이 없습니다."])

    def _format_monitor_ack_status(self, ack_result: dict[str, Any] | None) -> str:
        if not ack_result:
            return "아직 ACK 기록 없음"

        status = ack_result.get("status")
        event_id = _safe_text(ack_result.get("event_id", "-"))
        duplicate = bool(ack_result.get("duplicate", False))
        duplicate_text = "중복 확인 응답" if duplicate else "일반 확인 응답"
        if status == "acknowledged":
            return f"확인 응답 반환 완료 | 식별자={event_id} | 구분={duplicate_text}"
        if status == "dropped":
            return f"확인 응답 생략됨 | 식별자={event_id} | R2 재시도 관찰 대상 | 구분={duplicate_text}"
        if status == "drop_requested":
            reason = _safe_text(ack_result.get("reason", "-"))
            return f"다음 확인 응답 생략 예약 | 이유={reason}"
        return "확인 응답 상태={status} | 식별자={event_id} | 중복={duplicate}".format(
            status=_safe_text(status or "unknown"),
            event_id=event_id,
            duplicate="예" if duplicate else "아니오",
        )

    def _monitor_path_rows(self, node_view: dict[str, Any]) -> list[str]:
        detail = node_view["details"].get("detail", {})
        traffic = detail.get("traffic") or {}
        previous_peer = traffic.get("previous_peer") or {}
        upstream = _safe_text(previous_peer.get("peer_node_id") or "R2")
        hop_state = _derive_peer_hop_state(previous_peer, self.node_last_seen)
        hop_text = _display_keyword(hop_state, _DISPLAY_HOP_STATES)
        ack_result = detail.get("last_ack_result") or {}
        ack_status = ack_result.get("status")
        if not ack_result:
            ack_text = "확인 응답 대기"
        elif ack_status == "dropped":
            ack_text = "확인 응답 생략 / 재시도 유도"
        elif ack_status == "drop_requested":
            ack_text = "확인 응답 생략 예약"
        elif ack_status == "acknowledged":
            ack_text = "확인 응답 반환"
        else:
            ack_text = "확인 응답 상태 확인 중"
        return [
            f"수신 구간={upstream} -> monitor",
            f"구간 상태={hop_text}",
            f"응답 상태={ack_text}",
        ]

    def _monitor_route_rows(self, detail: dict[str, Any]) -> list[str]:
        route_summary = detail.get("last_route_summary") or {}
        if not route_summary:
            return ["경로 정보 없음"]
        rows = [
            "상태={state} / active={active}".format(
                state=_display_keyword(route_summary.get("route_state", "-"), _DISPLAY_ROUTE_STATES),
                active=_display_keyword(route_summary.get("active_route", "-"), _DISPLAY_ROUTE_IDS),
            )
        ]
        failed_hop = route_summary.get("failed_hop")
        if failed_hop:
            rows.append(f"관찰 실패 hop={_safe_text(failed_hop)}")
        suspected_node = route_summary.get("suspected_node")
        if suspected_node:
            rows.append(f"의심 node={_safe_text(suspected_node)}")
        reroute_reason = route_summary.get("reroute_reason")
        if reroute_reason:
            rows.append(f"우회 이유={_safe_text(reroute_reason)}")
        return rows

    def _monitor_fault_rows(self, detail: dict[str, Any]) -> list[str]:
        localization = detail.get("last_fault_localization") or {}
        if not localization:
            return ["진단 정보 없음"]
        rows = [
            f"범위={_safe_text(localization.get('failure_scope', '-'))}",
            f"근거={_safe_text(localization.get('basis', '-'))}",
            f"신뢰도={_safe_text(localization.get('confidence', '-'))}",
        ]
        failed_hop = localization.get("failed_hop")
        if failed_hop:
            rows.append(f"관찰 실패 hop={_safe_text(failed_hop)}")
        suspected_node = localization.get("suspected_node")
        if suspected_node:
            rows.append(f"의심 node={_safe_text(suspected_node)}")
        failure_reason = localization.get("failure_reason")
        if failure_reason:
            rows.append(f"관찰 이유={_safe_text(failure_reason)}")
        return rows

    def _monitor_card_lines(self, title: str, rows: list[str], width: int = 34) -> list[str]:
        width = max(12, width)
        inner_width = max(1, width - 4)
        card = [
            "+" + "-" * (width - 2) + "+",
            "| " + _pad_display_text(title, inner_width) + " |",
            "+" + "-" * (width - 2) + "+",
        ]
        body_rows = rows or ["-"]
        for row in body_rows:
            card.append("| " + _pad_display_text(row, inner_width) + " |")
        card.append("+" + "-" * (width - 2) + "+")
        return card

    def _append_monitor_card_pair(
        self,
        lines: list[str],
        left_title: str,
        left_rows: list[str],
        right_title: str,
        right_rows: list[str],
        card_width: int,
    ) -> None:
        left_card = self._monitor_card_lines(left_title, left_rows, width=card_width)
        right_card = self._monitor_card_lines(right_title, right_rows, width=card_width)
        card_height = max(len(left_card), len(right_card))
        blank_card_line = " " * len(left_card[0])
        for index in range(card_height):
            left = left_card[index] if index < len(left_card) else blank_card_line
            right = right_card[index] if index < len(right_card) else blank_card_line
            lines.append(f"  {left}  {right}")

    def _append_monitor_card_stack(self, lines: list[str], title: str, rows: list[str]) -> None:
        lines.extend(f"  {line}" for line in self._monitor_card_lines(title, rows, width=70))

    def _append_monitor_panel(self, lines: list[str], title: str, rows: list[str], row_width: int = 34) -> None:
        lines.append(f"  [{title}]")
        for row in rows or ["-"]:
            lines.append(f"    - {_fit_display_text(row, row_width)}")

    def _append_monitor_section_lines(self, lines: list[str], title: str, rows: list[str], width: int) -> None:
        available_width = max(1, width - 4)
        lines.append(f"  [{_fit_display_text(title, available_width)}]")
        for row in rows or ["-"]:
            lines.append(f"  - {_fit_display_text(row, available_width)}")

    def _append_monitor_plain_lines(self, lines: list[str], title: str, rows: list[str], width: int) -> None:
        lines.append(_fit_display_text(title, width))
        for row in rows or ["-"]:
            lines.append(_fit_display_text(f"- {row}", width))

    def _monitor_current_rows(self, last_processed_event: Any) -> list[str]:
        if not isinstance(last_processed_event, dict):
            return ["아직 기록된 이벤트 없음"]
        return [
            f"기록 완료: {_safe_text(last_processed_event.get('event_id', '-'))}",
            "종류={event_type} / 등급={severity}".format(
                event_type=_display_keyword(last_processed_event.get("event_type", "-"), _DISPLAY_EVENT_TYPES),
                severity=_display_keyword(last_processed_event.get("severity", "-"), _DISPLAY_SEVERITIES),
            ),
            "대상={host_id} / 순번={seq_no}".format(
                host_id=_safe_text(last_processed_event.get("host_id", "-")),
                seq_no=_safe_text(last_processed_event.get("seq_no", "-")),
            ),
        ]

    def _monitor_host_rows(self, host_state_table: dict[str, Any]) -> list[str]:
        if not host_state_table:
            return ["아직 수신된 host 상태 없음"]
        rows: list[str] = []
        for host_id in sorted(host_state_table):
            host_state = host_state_table.get(host_id) or {}
            payload = host_state.get("payload") or {}
            rows.extend(
                [
                    f"{_safe_text(host_id)}",
                    "종류={event_type} / 등급={severity}".format(
                        event_type=_display_keyword(host_state.get("event_type", "-"), _DISPLAY_EVENT_TYPES),
                        severity=_display_keyword(host_state.get("severity", "-"), _DISPLAY_SEVERITIES),
                    ),
                    "CPU={cpu}% / 메모리={memory}%".format(
                        cpu=_safe_text(payload.get("cpu", "-")),
                        memory=_safe_text(payload.get("memory", "-")),
                    ),
                    "서비스={service} / 지연={latency}ms".format(
                        service=_display_keyword(payload.get("service_state", "-"), _DISPLAY_SERVICE_STATES),
                        latency=_safe_text(payload.get("latency_ms", "-")),
                    ),
                    f"장애={_display_keyword(payload.get('fault_mode', '-'), _DISPLAY_FAULT_MODES)}",
                ]
            )
        return rows[:6]

    def _monitor_recent_event_rows(self, node_view: dict[str, Any]) -> list[str]:
        detail = node_view["details"].get("detail", {})
        summaries = list(detail.get("recent_event_summaries") or [])[: config.RECENT_ACTIVITY_SECTION_LIMIT]
        if summaries:
            return [self._format_monitor_event_summary(event) for event in summaries]

        recent_events = list(node_view["details"].get("recent_events", []))[: config.RECENT_ACTIVITY_SECTION_LIMIT]
        if recent_events:
            return [_safe_text(entry) for entry in recent_events]
        return ["아직 표시할 알림 없음"]

    def _monitor_health_rows(self, details: dict[str, Any]) -> list[str]:
        total_logged = details.get("total_logged", 0)
        duplicate_count = details.get("duplicate_count", 0)
        out_of_order_count = details.get("out_of_order_count", 0)
        rows = [
            f"저장={total_logged}",
            f"중복 차단={duplicate_count}",
            f"순서 역전={out_of_order_count}",
        ]
        if duplicate_count:
            rows.append("같은 식별자는 중복 저장 안 함")
        if out_of_order_count:
            rows.append("순번 역전 관찰 대상")
        return rows

    def _monitor_ack_rows(self, ack_result: dict[str, Any] | None) -> list[str]:
        if not ack_result:
            return ["아직 확인 응답 기록 없음"]

        status = ack_result.get("status")
        event_id = _safe_text(ack_result.get("event_id", "-"))
        duplicate = bool(ack_result.get("duplicate", False))
        duplicate_text = "중복 확인 응답" if duplicate else "일반 확인 응답"
        if status == "acknowledged":
            return ["확인 응답 반환 완료", f"식별자={event_id}", f"구분={duplicate_text}"]
        if status == "dropped":
            return ["확인 응답 생략됨", f"식별자={event_id}", "R2 재시도 관찰 대상", f"구분={duplicate_text}"]
        if status == "drop_requested":
            return ["다음 확인 응답 생략 예약", f"이유={_safe_text(ack_result.get('reason', '-'))}"]
        return [
            f"상태={_safe_text(status or 'unknown')}",
            f"식별자={event_id}",
            "중복=예" if duplicate else "중복=아니오",
        ]

    def _append_focused_monitor_board_lines(self, lines: list[str], node_view: dict[str, Any], terminal_width: int = 80) -> None:
        terminal_width = max(1, terminal_width)
        details = node_view["details"]
        detail = details.get("detail", {})
        last_processed_event = detail.get("last_processed_event")
        host_state_table = details.get("host_state_table") or {}
        sections = [
            ("처리 경로", self._monitor_path_rows(node_view)),
            ("경로 진단", self._monitor_route_rows(detail)),
            ("Trace 근거", self._monitor_fault_rows(detail)),
            ("현재 상황", self._monitor_current_rows(last_processed_event)),
            ("Host 최신 상태", self._monitor_host_rows(host_state_table)),
            ("전달 건강도", self._monitor_health_rows(details)),
            ("확인 응답 / 재시도", self._monitor_ack_rows(detail.get("last_ack_result"))),
            ("최근 알림/이벤트", self._monitor_recent_event_rows(node_view)),
        ]

        if terminal_width >= 96:
            card_width = max(34, (terminal_width - 4) // 2)
            lines.extend(["  Monitor 상황판", "  " + "=" * min(20, terminal_width - 2), ""])
            for index in range(0, len(sections), 2):
                left_title, left_rows = sections[index]
                if index + 1 < len(sections):
                    right_title, right_rows = sections[index + 1]
                else:
                    right_title, right_rows = "", []
                self._append_monitor_card_pair(lines, left_title, left_rows, right_title, right_rows, card_width)
                if index + 2 < len(sections):
                    lines.append("")
            return

        if terminal_width >= 72:
            card_width = max(12, terminal_width - 2)
            lines.extend(["  Monitor 상황판", "  " + "=" * min(20, terminal_width - 2), ""])
            for index, (title, rows) in enumerate(sections):
                lines.extend(f"  {line}" for line in self._monitor_card_lines(title, rows, width=card_width - 2))
                if index + 1 < len(sections):
                    lines.append("")
            return

        if terminal_width >= 48:
            lines.extend(["  Monitor 상황판", "  " + "-" * min(20, terminal_width - 2), ""])
            for index, (title, rows) in enumerate(sections):
                self._append_monitor_section_lines(lines, title, rows, terminal_width)
                if index + 1 < len(sections):
                    lines.append("")
            return

        lines.append(_fit_display_text("Monitor 상황판", terminal_width))
        for title, rows in sections:
            self._append_monitor_plain_lines(lines, title, rows, terminal_width)

    def _build_node_section(self, node_id: str, terminal_width: int = 80) -> list[str]:
        status = self.node_status.get(node_id, {})
        node_view = normalize_node_view(
            node_id=node_id,
            status=status,
            last_seen=self.node_last_seen.get(node_id),
            now=time.monotonic(),
        )
        now = time.monotonic()

        lines = [
            self._node_title(node_id),
            "  요약: state={state:<14} queue={queue:<2} pending={pending:<2} retries={retries:<2} dup={dup:<2}".format(
                state=_format_node_state(node_view),
                queue=node_view["queue_length"],
                pending=node_view["pending_ack_count"],
                retries=node_view["retry_total"],
                dup=node_view["duplicate_dropped"],
            ),
            "  관찰: liveness={liveness} reported={reported} last_seen={last_seen}".format(
                liveness=node_view["observed_liveness"],
                reported=node_view["reported_state"],
                last_seen=_format_last_seen(node_view["last_seen"], now),
            ),
            f"  비고: {_safe_text(node_view['note'])}",
            f"  제어: {_format_control_summary(node_view)}",
            self._traffic_summary(node_view),
        ]

        if node_id == "host-simulator":
            self._append_host_monitor_lines(lines, node_view)
        elif node_id == "local-agent":
            self._append_agent_monitor_lines(lines, node_view)
        elif node_id in {"r1", "r2"}:
            self._append_relay_monitor_lines(lines, node_view)
        elif node_id == "monitor":
            self._append_monitor_monitor_lines(lines, node_view, terminal_width)

        return lines

    def _build_focused_frame_lines(self, scripted_demo: bool, terminal_width: int = 80) -> list[str]:
        node_id = self.focus_node or config.NODE_ORDER[0]
        node_view = normalize_node_view(
            node_id=node_id,
            status=self.node_status.get(node_id, {}),
            last_seen=self.node_last_seen.get(node_id),
            now=time.monotonic(),
        )
        lines = [
            "=== 네트워크 프로젝트 최소 데모 ===",
            f"실행 모드: {'scripted controller focus' if scripted_demo else 'focused node monitor'}",
            f"focus node: {node_id}",
            self._external_controller_line(),
            "",
        ]
        lines.extend(self._build_node_section(node_id, terminal_width))
        if node_id != "monitor":
            lines.append("")
            self._append_focused_traffic_lines(lines, node_view)
        lines.extend(
            [
                "",
                "최근 제어 활동:",
            ]
        )
        if self.control_activity_log:
            lines.extend(f"  {entry}" for entry in list(self.control_activity_log)[: config.RECENT_ACTIVITY_SECTION_LIMIT])
        else:
            lines.append("  (아직 제어 활동 없음)")
        lines.extend(
            [
                "",
                "최근 노드 활동:",
            ]
        )
        node_activity_entries = self._focused_node_activity_entries(node_id)
        if node_activity_entries:
            lines.extend(f"  {entry}" for entry in node_activity_entries)
        else:
            lines.append("  (아직 해당 노드 활동 없음)")
        lines.extend(
            [
                "",
                "조작 방법:",
                "  help | start [node] | pause [node] | reset [node|all] | kill <node>",
                f"  {self._focus_command_hint()}",
                "  fault cpu|service|latency on|off|[sec] | ackdrop | delay r1|r2|r1b|r2b [sec] | quit | exit",
            ]
        )
        return [_fit_display_text(line, terminal_width) for line in lines]

    async def run(
        self,
        duration: float | None,
        scripted_demo: bool,
        startup: Callable[[], Awaitable[None]] | None = None,
        shutdown: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._control_server = await asyncio.start_server(self._handle_control_connection, self.control_host, self.control_port)
        self._record_activity(f"외부 컨트롤러 대기 중: {self.control_host}:{self.control_port}", "system")
        if startup is not None:
            await startup()
        self._tasks.append(asyncio.create_task(self._render_loop(scripted_demo), name="controller-render"))
        if sys.stdin.isatty() and not scripted_demo:
            self._tasks.append(asyncio.create_task(self._interactive_command_loop(scripted_demo), name="controller-input"))
        if scripted_demo:
            self._tasks.append(asyncio.create_task(self._scripted_demo(), name="controller-scripted"))
        try:
            if duration is None:
                while not self._stop_requested:
                    await asyncio.sleep(config.VIEWER_IDLE_SLEEP_SECONDS)
            else:
                await asyncio.sleep(duration)
        finally:
            self._stop_requested = True
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
            if shutdown is not None:
                await shutdown()
            if self._control_server is not None:
                self._control_server.close()
                await self._control_server.wait_closed()
            self._renderer.close()

    async def _scripted_demo(self) -> None:
        self._record_activity("자동 데모: CPU -> ACK 손실/재전송 -> SERVICE -> LATENCY", "system")
        await asyncio.sleep(config.SCRIPTED_STEP_SHORT_SECONDS)
        await self.send_control("drop_next_ack", "monitor")
        await asyncio.sleep(config.SCRIPTED_STEP_SHORT_SECONDS)
        await self.inject_fault("CPU_SPIKE", 6)
        await asyncio.sleep(config.SCRIPTED_STEP_LONG_SECONDS)
        await self.inject_fault("SERVICE_DOWN", 6)
        await asyncio.sleep(config.SCRIPTED_STEP_LONG_SECONDS)
        await self.inject_fault("LATENCY_HIGH", 6)

    async def _handle_control_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while not self._stop_requested:
                raw_request = await reader.readline()
                if not raw_request:
                    break
                request = decode_message(raw_request.decode().strip())
                if request.get("msg_type") == "STATUS_REPORT":
                    if self.control_token and request.get("control_token") != self.control_token:
                        continue
                    status = request.get("status")
                    if isinstance(status, dict) and status.get("msg_type") == "STATUS":
                        self._apply_status(status)
                    continue
                if self.control_token and request.get("control_token") != self.control_token:
                    continue
                if request.get("msg_type") == "STATUS":
                    self._apply_status(request)
                    continue
                await self._apply_remote_request(request)
        finally:
            writer.close()
            await writer.wait_closed()

    def _apply_status(self, message: dict[str, Any]) -> None:
        node_id = str(message["node_id"])
        previous = self.node_status.get(node_id, {})
        self.node_status[node_id] = dict(message)
        self.node_last_seen[node_id] = time.monotonic()
        note = message.get("note")
        if note and note != previous.get("note"):
            self._record_activity(f"{node_id}: {note}", "node")

    async def handle_local_command(self, line: str) -> tuple[bool, str | None]:
        stripped = line.strip()
        if stripped == "help":
            local_message = f"{build_requests(stripped)[2]} | {self._focus_help_text()}"
            self._record_activity(local_message, "control")
            return False, local_message

        focus_handled, focus_message = self._handle_focus_command(stripped)
        if focus_handled:
            return False, focus_message

        requests, should_exit, local_message = build_requests(stripped)
        if local_message:
            self._record_activity(local_message, "control")
            return should_exit, local_message
        for request in requests:
            await self._apply_remote_request(request)
        return should_exit, None

    async def _interactive_command_loop(self, scripted_demo: bool) -> None:
        while not self._stop_requested:
            try:
                if isinstance(self._renderer, InPlaceRenderer) and sys.stdin.isatty():
                    line_result = self._read_in_place_line(self._renderer)
                    line = await line_result if inspect.isawaitable(line_result) else line_result
                    if line is None:
                        break
                else:
                    self._input_waiting = True
                    line = await asyncio.to_thread(input, "viewer> ")
            except EOFError:
                break
            finally:
                self._input_waiting = False
            if not line.strip():
                continue
            should_exit, _ = await self.handle_local_command(line)
            if isinstance(self._renderer, InPlaceRenderer):
                self._renderer.force_repaint()
            self._renderer.render(self._build_frame_lines(scripted_demo))
            if should_exit:
                self._stop_requested = True
                break

    async def _read_in_place_line(self, renderer: InPlaceRenderer) -> str | None:
        file_descriptor = sys.stdin.fileno()
        previous_terminal_settings = termios.tcgetattr(file_descriptor)
        self._input_buffer = ""
        self._input_waiting = True
        renderer.render_prompt(self._input_buffer)
        try:
            tty.setcbreak(file_descriptor)
            no_echo_settings = termios.tcgetattr(file_descriptor)
            no_echo_settings[3] = no_echo_settings[3] & ~termios.ECHO
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, no_echo_settings)
            while not self._stop_requested:
                readable, _, _ = select.select([file_descriptor], [], [], 0)
                if not readable:
                    await asyncio.sleep(0.05)
                    continue
                character = self._read_input_character(file_descriptor)
                if character == "":
                    return None
                if character in {"\n", "\r"}:
                    return self._input_buffer
                if character == "\x03":
                    self._stop_requested = True
                    return None
                if character == "\x04":
                    if not self._input_buffer:
                        return None
                    continue
                if character in {"\x7f", "\b"}:
                    self._input_buffer = self._input_buffer[:-1]
                elif character == "\x1b":
                    self._discard_pending_escape_sequence(file_descriptor)
                elif character == "[":
                    bracket_text = self._consume_or_return_bracket_sequence(file_descriptor)
                    self._input_buffer += bracket_text
                elif character == "\t" or ord(character) >= 32:
                    self._input_buffer += character
                renderer.render_prompt(self._input_buffer)
        finally:
            with contextlib.suppress(OSError, termios.error):
                termios.tcsetattr(file_descriptor, termios.TCSADRAIN, previous_terminal_settings)
            self._input_waiting = False

    def _discard_pending_escape_sequence(self, file_descriptor: int) -> None:
        deadline = time.monotonic() + 0.2
        while time.monotonic() < deadline:
            readable, _, _ = select.select([file_descriptor], [], [], 0.05)
            if not readable:
                return
            character = self._read_input_character(file_descriptor)
            if character.isalpha() or character == "~":
                return

    def _consume_or_return_bracket_sequence(self, file_descriptor: int) -> str:
        readable, _, _ = select.select([file_descriptor], [], [], 0.2)
        if not readable:
            return "["
        character = self._read_input_character(file_descriptor)
        if character.isalpha() or character == "~":
            return ""
        return f"[{character}"

    def _read_input_character(self, file_descriptor: int) -> str:
        try:
            data = os.read(file_descriptor, 1)
        except OSError:
            return ""
        if not data:
            return ""
        return data.decode(errors="ignore")

    async def _apply_remote_request(self, request: dict[str, Any]) -> None:
        display = request.get("display")
        if isinstance(display, str) and display:
            self._record_activity(display, "control")

        if request.get("msg_type") == "CONTROL":
            await self._broadcast_control(request)
            return

        kind = request.get("kind")
        if kind == "control":
            message = request.get("message")
            if isinstance(message, dict):
                if self.control_token and "control_token" not in message:
                    message = dict(message)
                    message["control_token"] = self.control_token
                await self._broadcast_control(message)
            return

        if kind == "reset_all":
            await self._broadcast_control(make_control("reset", "all", control_token=self.control_token))
            self.system_activity_log.clear()
            self.control_activity_log.clear()
            self.node_activity_log.clear()
            self._record_activity("reset 이후 시스템 상태와 큐를 모두 초기화했습니다", "system")
            return

        if kind == "shutdown":
            self._stop_requested = True
            return

    async def send_control(self, command: str, target: str, params: dict[str, Any] | None = None) -> None:
        message = make_control(command, target, params, control_token=self.control_token)
        await self._broadcast_control(message)
        self._record_activity(f"제어 명령 -> {target}: {command} {params or {}}", "control")

    async def _broadcast_control(self, message: dict[str, Any]) -> None:
        outbound = dict(message)
        if self.control_token and "control_token" not in outbound:
            outbound["control_token"] = self.control_token
        target = str(outbound.get("target", "all"))
        targets = config.NODE_ORDER if target == "all" else [target]
        for node_id in targets:
            endpoint = self.node_endpoints.get(node_id)
            if endpoint is None:
                continue
            host, port = endpoint
            try:
                response = await send_request(
                    host,
                    port,
                    outbound,
                    expect_response=True,
                    timeout=config.CONTROL_REQUEST_TIMEOUT_SECONDS,
                )
                if isinstance(response, dict) and response.get("ok") is False:
                    reason = _safe_text(response.get("reason", "rejected"))
                    self._record_activity(f"{node_id}: 제어 거부 ({reason})", "control")
            except (OSError, asyncio.TimeoutError):
                self._record_activity(f"{node_id}: 제어 연결 실패", "control")

    def _external_controller_line(self) -> str:
        command = f"python main.py --controller --host {self.control_host} --port {self.control_port}"
        if not self.control_token:
            return f"외부 컨트롤러: {command}"
        if self.public_external_control:
            return f"외부 컨트롤러: {command} (같은 control token 필요)"
        token_fingerprint = hashlib.sha256(self.control_token.encode()).hexdigest()[:10]
        return (
            "외부 컨트롤러: 비공개 private control token 사용 중 - 화면에 토큰을 표시하지 않음 "
            f"(fingerprint={token_fingerprint}, 외부 접속 필요 시 명시적 --control-token으로 재시작)"
        )

    async def inject_fault(self, fault_type: str, duration_sec: int) -> None:
        await self.send_control(
            "inject_fault",
            "host-simulator",
            {"fault_type": fault_type, "duration_sec": duration_sec},
        )

    async def set_fault(self, fault_type: str, enabled: bool) -> None:
        await self.send_control(
            "set_fault",
            "host-simulator",
            {"fault_type": fault_type, "enabled": enabled},
        )

    async def _render_loop(self, scripted_demo: bool) -> None:
        while not self._stop_requested:
            terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns
            self._renderer.render(self._build_frame_lines(scripted_demo, terminal_width=terminal_width))
            if self._input_waiting and isinstance(self._renderer, InPlaceRenderer):
                self._renderer.render_prompt(self._input_buffer)
            await asyncio.sleep(config.STATUS_REFRESH_SECONDS)

    def _build_frame_lines(self, scripted_demo: bool, terminal_width: int | None = None) -> list[str]:
        terminal_width = 80 if terminal_width is None else max(1, terminal_width)
        if self.focus_node is not None:
            return self._build_focused_frame_lines(scripted_demo, terminal_width)
        lines = [
            "=== 네트워크 프로젝트 최소 데모 ===",
            "데이터 경로: Host Simulator -> Local Agent -> Relay R1 -> Relay R2 -> Monitor",
            f"실행 모드: {'scripted viewer' if scripted_demo else 'viewer only'}",
            self._external_controller_line(),
            "",
            "노드별 모니터링:",
        ]
        for node_id in config.NODE_ORDER:
            lines.extend(self._build_node_section(node_id, terminal_width))
            lines.append("")
        lines.append("최근 시스템 활동:")
        if self.system_activity_log:
            lines.extend(f"  {entry}" for entry in list(self.system_activity_log)[: config.RECENT_ACTIVITY_SECTION_LIMIT])
        else:
            lines.append("  (아직 시스템 활동 없음)")
        lines.extend(["", "최근 제어 활동:"])
        if self.control_activity_log:
            lines.extend(f"  {entry}" for entry in list(self.control_activity_log)[: config.RECENT_ACTIVITY_SECTION_LIMIT])
        else:
            lines.append("  (아직 제어 활동 없음)")
        lines.extend(["", "최근 노드 활동:"])
        if self.node_activity_log:
            lines.extend(f"  {entry}" for entry in list(self.node_activity_log)[: config.RECENT_ACTIVITY_SECTION_LIMIT])
        else:
            lines.append("  (아직 노드 활동 없음)")
        lines.extend(
            [
                "",
                "조작 방법:",
                "  help | start [node] | pause [node] | reset [node|all] | kill <node>",
                f"  {self._focus_command_hint()}",
                "  fault cpu|service|latency on|off|[sec] | ackdrop | delay r1|r2|r1b|r2b [sec] | quit | exit",
                "  interactive viewer mode에서는 같은 화면에서 viewer> 프롬프트로 명령 입력 가능",
            ]
        )
        return lines
