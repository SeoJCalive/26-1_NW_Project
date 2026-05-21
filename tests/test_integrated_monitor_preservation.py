from __future__ import annotations

import unittest

from nw_demo import config
from nw_demo.controller_ui import ControllerUI

from tests.status_builders import (
    build_host_status,
    build_local_agent_status,
    build_monitor_status,
    build_relay_status,
)


class IntegratedMonitorPreservationTests(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )

    def test_integrated_frame_keeps_current_node_order_visible(self) -> None:
        for message in [
            build_host_status(),
            build_local_agent_status(),
            build_relay_status(node_id="r1"),
            build_relay_status(node_id="r2", note="evt-host-1-7 upstream ACK 준비"),
            build_monitor_status(),
        ]:
            self.controller._apply_status(message)

        frame = "\n".join(self.controller._build_frame_lines(scripted_demo=False))

        self.assertIn("노드별 모니터링:", frame)
        for node_id in config.NODE_ORDER:
            self.assertIn(self.controller._node_title(node_id), frame)

    def test_integrated_frame_preserves_existing_role_specific_details(self) -> None:
        for message in [
            build_host_status(),
            build_local_agent_status(),
            build_relay_status(node_id="r1"),
            build_relay_status(node_id="r2"),
            build_monitor_status(),
        ]:
            self.controller._apply_status(message)

        frame = "\n".join(self.controller._build_frame_lines(scripted_demo=False))

        self.assertIn(config.HOST_ID, frame)
        self.assertIn(f"evt-{config.HOST_ID}-7", frame)
        self.assertIn("CPU_SPIKE", frame)
        self.assertIn("duplicates=1", frame)
        self.assertIn("queue=1", frame)

    def test_integrated_frame_exposes_liveness_and_node_scoped_control_hints(self) -> None:
        for message in [
            build_host_status(),
            build_local_agent_status(),
            build_relay_status(node_id="r1"),
            build_relay_status(node_id="r2"),
            build_monitor_status(),
        ]:
            self.controller._apply_status(message)

        frame = "\n".join(self.controller._build_frame_lines(scripted_demo=False))

        self.assertIn("관찰: liveness=live", frame)
        self.assertIn("제어: start=host-simulator", frame)
        self.assertIn("kill=monitor", frame)
        self.assertIn("hop summary:", frame)
        self.assertIn("relay detail:", frame)
        self.assertIn("agent detail:", frame)
        self.assertIn("sink detail:", frame)
        self.assertNotIn("현재 상황", frame)
        self.assertNotIn("확인 응답 / 재시도", frame)
        self.assertNotIn("Monitor 상황판", frame)
        self.assertNotIn("+----------------", frame)
        self.assertNotIn('"msg_type": "EVENT"', frame)
        self.assertNotIn('"payload":', frame)

    def test_overview_frame_documents_focus_switching_without_payload_dump(self) -> None:
        self.controller._apply_status(build_local_agent_status())

        frame = "\n".join(self.controller._build_frame_lines(scripted_demo=False))

        self.assertIn("focus host|agent|r1|r2|r1b|r2b|monitor", frame)
        self.assertIn("overview", frame)
        self.assertIn("focus all", frame)
        self.assertNotIn('"msg_type": "EVENT"', frame)
        self.assertNotIn('"payload":', frame)


if __name__ == "__main__":
    unittest.main()
