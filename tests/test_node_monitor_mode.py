from __future__ import annotations

import unittest

from nw_demo import config
from nw_demo.controller_ui import ControllerUI, _display_cell_width

from tests.status_builders import build_local_agent_status, build_monitor_status, build_relay_status


class NodeMonitorModeTests(unittest.TestCase):
    def _focused_monitor_frame(self, *, terminal_width: int, status: dict[str, object] | None = None) -> str:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="monitor",
        )
        if status is not None:
            controller._apply_status(status)
        return "\n".join(controller._build_frame_lines(scripted_demo=False, terminal_width=terminal_width))

    def assertFrameFitsWidth(self, frame: str, terminal_width: int) -> None:
        for line in frame.splitlines():
            self.assertLessEqual(_display_cell_width(line), terminal_width, line)

    def test_focused_monitor_renders_single_node_structured_lanes(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="r1",
        )
        controller._apply_status(build_relay_status(node_id="r1"))

        frame = "\n".join(controller._build_frame_lines(scripted_demo=False, terminal_width=80))

        self.assertIn("focused node monitor", frame)
        self.assertIn("focus node: r1", frame)
        self.assertIn("이전 노드:", frame)
        self.assertIn("다음 노드:", frame)
        self.assertIn("받은 자료:", frame)
        self.assertIn("보낸 자료:", frame)
        self.assertIn("최근 traffic lineage:", frame)
        self.assertNotIn("노드별 모니터링:", frame)

    def test_focused_monitor_renders_agent_and_monitor_role_details(self) -> None:
        agent_controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="local-agent",
        )
        agent_controller._apply_status(build_local_agent_status())
        agent_frame = "\n".join(agent_controller._build_frame_lines(scripted_demo=False, terminal_width=80))
        self.assertIn("agent detail:", agent_frame)
        self.assertIn("host_state", agent_frame)

        monitor_controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="monitor",
        )
        monitor_controller._apply_status(build_monitor_status())
        monitor_frame = "\n".join(monitor_controller._build_frame_lines(scripted_demo=False, terminal_width=80))
        self.assertIn("현재 상황", monitor_frame)
        self.assertIn("Host 최신 상태", monitor_frame)
        self.assertIn("최근 알림/이벤트", monitor_frame)
        self.assertIn("처리 경로", monitor_frame)
        self.assertIn("전달 건강도", monitor_frame)
        self.assertIn("수신 구간=r2 -> monitor", monitor_frame)
        self.assertIn("+", monitor_frame)
        self.assertNotIn("신호 흐름", monitor_frame)
        self.assertIn("확인 응답 / 재시도", monitor_frame)
        self.assertIn(config.HOST_ID, monitor_frame)
        self.assertIn("CPU 급등", monitor_frame)
        self.assertIn("순번=7", monitor_frame)
        self.assertIn("저장=2", monitor_frame)
        self.assertIn("중복 차단=1", monitor_frame)
        self.assertIn("순서 역전=0", monitor_frame)
        self.assertNotIn("sink detail:", monitor_frame)
        self.assertNotIn('"msg_type": "EVENT"', monitor_frame)
        self.assertNotIn('"payload":', monitor_frame)

    def test_focused_monitor_fits_width_fallbacks(self) -> None:
        expected_markers = {
            120: "+",
            80: "+",
            40: "처리 경로",
            20: "처리 경로",
        }
        for terminal_width, marker in expected_markers.items():
            with self.subTest(terminal_width=terminal_width):
                frame = self._focused_monitor_frame(terminal_width=terminal_width, status=build_monitor_status())

                self.assertIn("Monitor 상황판", frame)
                self.assertIn(marker, frame)
                self.assertIn("Host 최신 상태", frame)
                self.assertIn("확인 응답", frame)
                self.assertNotIn("신호 흐름", frame)
                self.assertNotIn('"msg_type": "EVENT"', frame)
                self.assertNotIn('"payload":', frame)
                self.assertFrameFitsWidth(frame, terminal_width)

    def test_focused_monitor_fits_long_and_malicious_values(self) -> None:
        status = build_monitor_status()
        long_event_id = "evt-host-with-very-very-long-id-1234567890"
        long_host_id = "host-with-very-very-long-id-abcdef"
        status["host_state_table"] = {
            long_host_id: {
                "event_type": "CPU_SPIKE",
                "severity": "WARN",
                "payload": {
                    "cpu": "96\nINJECTED",
                    "memory": "51\tTAB",
                    "service_state": "UP\rCR",
                    "latency_ms": "28\x1b[31m",
                    "fault_mode": "CPU_SPIKE",
                },
            }
        }
        status["detail"]["last_processed_event"]["event_id"] = long_event_id
        status["detail"]["last_processed_event"]["host_id"] = long_host_id
        status["detail"]["last_ack_result"]["event_id"] = long_event_id
        status["detail"]["recent_event_summaries"] = [
            {
                "event_id": long_event_id,
                "event_type": "CPU_SPIKE",
                "severity": "WARN",
                "host_id": long_host_id,
                "seq_no": 7,
            }
        ]

        frame = self._focused_monitor_frame(terminal_width=40, status=status)

        self.assertIn("~", frame)
        self.assertNotIn("INJECTED\n", frame)
        self.assertNotIn("\t", frame)
        self.assertNotIn("\r", frame)
        self.assertNotIn("\x1b", frame)
        self.assertFrameFitsWidth(frame, 40)

    def test_focused_monitor_renders_partial_topology_not_started_and_timeout_semantics(self) -> None:
        not_started_controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="r1",
        )
        relay_status = build_relay_status(node_id="r1")
        relay_status["detail"]["traffic"]["next_peer"]["hop_state"] = "unknown"
        not_started_controller._apply_status(relay_status)
        not_started_frame = "\n".join(not_started_controller._build_frame_lines(scripted_demo=False))
        self.assertIn("다음 노드: peer=r2 role=relay hop=not_started", not_started_frame)

        timeout_controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="r1",
        )
        timeout_status = build_relay_status(node_id="r1")
        timeout_status["detail"]["traffic"]["next_peer"]["hop_state"] = "timeout"
        timeout_status["detail"]["traffic"]["next_peer"]["failure_reason"] = "timeout"
        timeout_controller._apply_status(timeout_status)
        timeout_frame = "\n".join(timeout_controller._build_frame_lines(scripted_demo=False))
        self.assertIn("다음 노드: peer=r2 role=relay hop=timeout reason=timeout", timeout_frame)

    def test_runtime_focus_switch_reuses_existing_focused_and_overview_frames(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._apply_status(build_local_agent_status())
        controller._apply_status(build_relay_status(node_id="r1"))
        controller._apply_status(build_monitor_status())

        controller.focus_node = "local-agent"
        agent_frame = "\n".join(controller._build_frame_lines(scripted_demo=False))
        self.assertIn("focus node: local-agent", agent_frame)
        self.assertIn("Local Agent 모니터링", agent_frame)
        self.assertIn("agent detail:", agent_frame)
        self.assertNotIn("노드별 모니터링:", agent_frame)

        controller.focus_node = "r1"
        relay_frame = "\n".join(controller._build_frame_lines(scripted_demo=False))
        self.assertIn("focus node: r1", relay_frame)
        self.assertIn("Relay R1 모니터링", relay_frame)
        self.assertIn("relay detail:", relay_frame)
        self.assertNotIn("Local Agent 모니터링", relay_frame)

        controller.focus_node = "monitor"
        monitor_frame = "\n".join(controller._build_frame_lines(scripted_demo=False))
        self.assertIn("focus node: monitor", monitor_frame)
        self.assertIn("Monitor 모니터링", monitor_frame)
        self.assertIn("현재 상황", monitor_frame)
        self.assertIn("Host 최신 상태", monitor_frame)
        self.assertIn("최근 알림/이벤트", monitor_frame)
        self.assertIn("처리 경로", monitor_frame)
        self.assertIn("전달 건강도", monitor_frame)
        self.assertIn("확인 응답 / 재시도", monitor_frame)
        self.assertNotIn("신호 흐름", monitor_frame)
        self.assertNotIn("sink detail:", monitor_frame)

        controller.focus_node = None
        overview_frame = "\n".join(controller._build_frame_lines(scripted_demo=False))
        self.assertIn("노드별 모니터링:", overview_frame)
        self.assertIn("Local Agent 모니터링", overview_frame)
        self.assertIn("Relay R1 모니터링", overview_frame)
        self.assertIn("Monitor 모니터링", overview_frame)

    def test_runtime_focus_switch_renders_unknown_when_status_is_missing(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="monitor",
        )

        frame = "\n".join(controller._build_frame_lines(scripted_demo=False))

        self.assertIn("focus node: monitor", frame)
        self.assertIn("Monitor 모니터링", frame)
        self.assertIn("state=UNKNOWN", frame)
        self.assertIn("last_seen=never", frame)
        self.assertIn("아직 수신된 host 상태 없음", frame)
        self.assertIn("아직 표시할 알림 없음", frame)
        self.assertIn("아직 확인 응답 기록 없음", frame)

    def test_focused_monitor_renders_ack_drop_state_without_payload_dump(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="monitor",
        )
        status = build_monitor_status()
        status["detail"]["last_ack_result"] = {
            "status": "dropped",
            "event_id": f"evt-{config.HOST_ID}-7",
            "duplicate": False,
        }
        controller._apply_status(status)

        frame = "\n".join(controller._build_frame_lines(scripted_demo=False))

        self.assertIn("확인 응답 / 재시도", frame)
        self.assertIn("확인 응답 생략됨", frame)
        self.assertIn("R2 재시도 관찰 대상", frame)
        self.assertNotIn("sink detail:", frame)
        self.assertNotIn('"msg_type": "EVENT"', frame)

    def test_focused_monitor_renders_control_feedback_and_switching_hints(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="r1",
        )
        controller._record_activity("알 수 없는 focus 대상: bogus", "control")

        frame = "\n".join(controller._build_frame_lines(scripted_demo=False))

        self.assertIn("최근 제어 활동:", frame)
        self.assertIn("알 수 없는 focus 대상: bogus", frame)
        self.assertIn("조작 방법:", frame)
        self.assertIn("focus host|agent|r1|r2|monitor", frame)
        self.assertIn("overview", frame)
        self.assertIn("focus all", frame)
        self.assertIn("fault cpu|service|latency on|off|[sec]", frame)

    def test_focused_monitor_renders_only_current_node_activity_with_ten_line_limit(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="r1",
        )
        for index in range(11):
            controller._record_activity(f"r1: activity-{index}", "node")
        controller._record_activity("r2: hidden-global-activity", "node")

        frame = "\n".join(controller._build_frame_lines(scripted_demo=False))

        self.assertIn("최근 노드 활동:", frame)
        self.assertIn("r1: activity-10", frame)
        self.assertIn("r1: activity-1", frame)
        self.assertNotIn("r1: activity-0", frame)
        self.assertNotIn("r2: hidden-global-activity", frame)

    def test_focused_monitor_reports_empty_activity_for_current_node_only(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="r1",
        )
        controller._record_activity("r2: unrelated activity", "node")

        frame = "\n".join(controller._build_frame_lines(scripted_demo=False))

        self.assertIn("최근 노드 활동:", frame)
        self.assertIn("(아직 해당 노드 활동 없음)", frame)
        self.assertNotIn("r2: unrelated activity", frame)


if __name__ == "__main__":
    unittest.main()
