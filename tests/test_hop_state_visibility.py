from __future__ import annotations

import unittest

from nw_sim import config
from nw_sim.controller_ui import ControllerUI, normalize_node_view

from tests.status_builders import build_host_status, build_local_agent_status, build_monitor_status, build_relay_status


class HopStateVisibilityTests(unittest.TestCase):
    def test_relay_view_keeps_reported_state_separate_from_next_hop_failure(self) -> None:
        status = build_relay_status(node_id="r1")
        status["detail"]["traffic"]["next_peer"]["hop_state"] = "connection_error"
        status["detail"]["traffic"]["next_peer"]["failure_reason"] = "connection_error"

        node_view = normalize_node_view("r1", status, last_seen=1000.0, now=1000.0)

        self.assertEqual(node_view["reported_state"], "실행 중")
        self.assertEqual(node_view["observed_liveness"], "live")
        self.assertEqual(node_view["details"]["detail"]["traffic"]["next_peer"]["hop_state"], "connection_error")

    def test_integrated_summary_shows_hop_state_without_dumping_full_payload(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        relay_status = build_relay_status(node_id="r1")
        relay_status["detail"]["traffic"]["next_peer"]["hop_state"] = "connection_error"
        relay_status["detail"]["traffic"]["next_peer"]["failure_reason"] = "connection_error"
        controller._apply_status(relay_status)
        controller._apply_status(build_local_agent_status())

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))

        self.assertIn("hop summary: prev=acknowledged next=connection_error", frame)
        self.assertNotIn('"msg_type": "EVENT"', frame)

    def test_unknown_unseen_peer_is_rendered_as_not_started(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        relay_status = build_relay_status(node_id="r1")
        relay_status["detail"]["traffic"]["next_peer"]["hop_state"] = "unknown"
        relay_status["detail"]["traffic"]["previous_peer"]["hop_state"] = "unknown"
        controller._apply_status(relay_status)

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))
        self.assertIn("hop summary: prev=not_started next=not_started", frame)

    def test_partial_topology_host_only_keeps_other_nodes_not_started(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._apply_status(build_host_status())

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))
        self.assertIn("Host Simulator 모니터링", frame)
        self.assertIn("Local Agent 모니터링", frame)
        self.assertIn("Local Agent 모니터링\n  요약: state=UNKNOWN", frame)
        self.assertIn("hop summary: prev=unknown next=unknown last=-", frame)

    def test_partial_topology_host_agent_r1_monitor_without_r2_marks_r1_next_as_not_started(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._apply_status(build_host_status())
        controller._apply_status(build_local_agent_status())
        relay_status = build_relay_status(node_id="r1")
        relay_status["detail"]["traffic"]["next_peer"]["hop_state"] = "unknown"
        controller._apply_status(relay_status)
        controller._apply_status(build_monitor_status())

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))
        self.assertIn("Relay R1 모니터링", frame)
        self.assertIn("hop summary: prev=acknowledged next=not_started", frame)

    def test_partial_topology_host_agent_r1_without_r2_marks_r1_next_as_not_started(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._apply_status(build_host_status())
        controller._apply_status(build_local_agent_status())
        relay_status = build_relay_status(node_id="r1")
        relay_status["detail"]["traffic"]["next_peer"]["hop_state"] = "unknown"
        controller._apply_status(relay_status)

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))
        self.assertIn("Relay R1 모니터링", frame)
        self.assertIn("hop summary: prev=acknowledged next=not_started", frame)

    def test_partial_topology_host_and_agent_keeps_agent_idle_summary(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        agent_status = build_local_agent_status()
        agent_status.pop("last_event", None)
        agent_status["detail"]["detected_fault"] = None
        agent_status["detail"]["emitted_event"] = None
        agent_status["detail"]["downstream_result"] = {"status": "idle", "reason": "no_fault"}
        agent_status["detail"]["traffic"]["next_peer"]["hop_state"] = "idle"
        agent_status["detail"]["traffic"]["next_peer"]["failure_reason"] = "no_fault"
        controller._apply_status(build_host_status())
        controller._apply_status(agent_status)

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))
        self.assertIn("agent detail: input=ok fault=None downstream=idle", frame)
        self.assertIn("hop summary: prev=acknowledged next=idle", frame)

    def test_relay_timeout_hop_state_is_rendered(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        relay_status = build_relay_status(node_id="r1")
        relay_status["detail"]["traffic"]["next_peer"]["hop_state"] = "timeout"
        relay_status["detail"]["traffic"]["next_peer"]["failure_reason"] = "timeout"
        controller._apply_status(relay_status)

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))
        self.assertIn("hop summary: prev=acknowledged next=timeout", frame)

    def test_full_chain_baseline_keeps_acknowledged_hops(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._apply_status(build_host_status())
        controller._apply_status(build_local_agent_status())
        controller._apply_status(build_relay_status(node_id="r1"))
        controller._apply_status(build_relay_status(node_id="r2"))
        controller._apply_status(build_monitor_status())

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))
        self.assertIn("hop summary: prev=acknowledged next=acknowledged", frame)
        self.assertIn("sink detail: sink=logged ack=acknowledged", frame)

    def test_full_chain_plus_ack_drop_visibility(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._apply_status(build_host_status())
        controller._apply_status(build_local_agent_status())
        controller._apply_status(build_relay_status(node_id="r1"))
        controller._apply_status(build_relay_status(node_id="r2"))
        monitor_status = build_monitor_status()
        monitor_status["detail"]["last_ack_result"]["status"] = "dropped"
        monitor_status["detail"]["traffic"]["previous_peer"]["hop_state"] = "ack_dropped"
        monitor_status["detail"]["traffic"]["previous_peer"]["failure_reason"] = "drop_next_ack"
        controller._apply_status(monitor_status)

        frame = "\n".join(controller._build_frame_lines(scripted_scenario=False))
        self.assertIn("sink detail: sink=logged ack=dropped", frame)
        self.assertIn("hop summary: prev=ack_dropped next=not_applicable", frame)


if __name__ == "__main__":
    unittest.main()
