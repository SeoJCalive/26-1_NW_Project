from __future__ import annotations

import unittest

from nw_demo import config, controller_ui

from tests.status_builders import (
    build_host_status,
    build_local_agent_status,
    build_monitor_status,
    build_relay_status,
)


class NodeViewContractTests(unittest.TestCase):
    def _require_controller_api(self, name: str, purpose: str):
        candidate = getattr(controller_ui, name, None)
        if candidate is None:
            self.fail(
                f"controller_ui.{name} is missing; {purpose} is not implemented yet. "
                "Task 1 expects an explicit failing contract for this capability."
            )
        return candidate

    def test_normalized_node_view_contract_for_host_payload(self) -> None:
        normalize_node_view = self._require_controller_api(
            "normalize_node_view",
            "normalized per-node model contract",
        )

        now = 1000.0
        status = build_host_status()
        node_view = normalize_node_view(
            node_id="host-simulator",
            status=status,
            last_seen=now,
            now=now,
        )

        self.assertEqual(node_view["node_id"], "host-simulator")
        self.assertEqual(node_view["role"], "host")
        self.assertEqual(node_view["reported_state"], status["state"])
        self.assertEqual(node_view["observed_liveness"], "live")
        self.assertEqual(node_view["last_seen"], now)
        self.assertEqual(node_view["details"]["host_state"]["host_id"], config.HOST_ID)
        self.assertNotIn("fault_mode", node_view["details"]["host_state"])
        self.assertNotIn("latency_state", node_view["details"]["host_state"])
        self.assertEqual(node_view["details"]["detail"]["fault_type"], "CPU_SPIKE")
        self.assertEqual(node_view["details"]["detail"]["traffic"]["previous_peer"]["peer_role"], "agent")
        self.assertIn("pause", node_view["controls"])
        self.assertIn("kill", node_view["controls"])
        self.assertEqual(node_view["controls"]["pause"]["command"], "pause")
        self.assertEqual(node_view["controls"]["kill"]["command"], "shutdown")

    def test_liveness_transition_contract_unknown_live_stale_offline(self) -> None:
        derive_node_liveness = self._require_controller_api(
            "derive_node_liveness",
            "liveness transition contract",
        )

        now = 1000.0
        refresh = config.STATUS_REFRESH_SECONDS

        self.assertEqual(derive_node_liveness(last_seen=None, now=now), "unknown")
        self.assertEqual(derive_node_liveness(last_seen=now, now=now), "live")
        self.assertEqual(derive_node_liveness(last_seen=now - (refresh * 3), now=now), "stale")
        self.assertEqual(derive_node_liveness(last_seen=now - (refresh * 8), now=now), "offline")

    def test_pause_and_kill_are_not_collapsed_into_the_same_state(self) -> None:
        normalize_node_view = self._require_controller_api(
            "normalize_node_view",
            "pause-vs-kill distinction contract",
        )

        now = 1000.0
        paused_view = normalize_node_view(
            node_id="r1",
            status=build_relay_status(node_id="r1", state="일시정지", note="일시정지됨"),
            last_seen=now,
            now=now,
            kill_requested=False,
        )
        kill_requested_view = normalize_node_view(
            node_id="r1",
            status=build_relay_status(node_id="r1", state="실행 중", note="종료 요청 수신"),
            last_seen=now,
            now=now,
            kill_requested=True,
        )

        self.assertEqual(paused_view["reported_state"], "일시정지")
        self.assertEqual(paused_view["observed_liveness"], "live")
        self.assertEqual(kill_requested_view["reported_state"], "실행 중")
        self.assertEqual(kill_requested_view["observed_liveness"], "kill_requested")
        self.assertNotEqual(paused_view["observed_liveness"], kill_requested_view["observed_liveness"])

    def test_role_specific_details_survive_normalization(self) -> None:
        normalize_node_view = self._require_controller_api(
            "normalize_node_view",
            "role-specific STATUS detail preservation contract",
        )

        now = 1000.0
        agent_status = build_local_agent_status()
        agent_view = normalize_node_view(
            node_id="local-agent",
            status=agent_status,
            last_seen=now,
            now=now,
        )

        self.assertEqual(agent_view["role"], "agent")
        self.assertEqual(agent_view["details"]["last_event"]["event_id"], agent_status["last_event"]["event_id"])
        self.assertEqual(agent_view["details"]["last_event"]["payload"]["fault_mode"], "CPU_SPIKE")
        self.assertEqual(agent_view["details"]["detail"]["detected_fault"], "CPU_SPIKE")
        self.assertEqual(agent_view["details"]["detail"]["downstream_result"]["status"], "acknowledged")
        self.assertEqual(agent_view["details"]["detail"]["traffic"]["next_peer"]["peer_node_id"], "r1")

    def test_relay_details_expose_pending_retry_and_forwarding_structure(self) -> None:
        normalize_node_view = self._require_controller_api(
            "normalize_node_view",
            "relay detail contract",
        )

        relay_view = normalize_node_view(
            node_id="r1",
            status=build_relay_status(node_id="r1"),
            last_seen=1000.0,
            now=1000.0,
        )

        relay_detail = relay_view["details"]["detail"]
        self.assertEqual(relay_detail["recent_received_event_ids"][0], f"evt-{config.HOST_ID}-7")
        self.assertEqual(relay_detail["pending_ack_state"][0]["state"], "retrying")
        self.assertEqual(relay_detail["last_downstream_result"]["status"], "acknowledged")
        self.assertEqual(relay_detail["last_forwarded_result"]["status"], "forwarded")
        self.assertEqual(relay_detail["traffic"]["next_peer"]["last_received"]["attempt_no"], 2)

    def test_monitor_details_expose_sink_side_processing_structure(self) -> None:
        normalize_node_view = self._require_controller_api(
            "normalize_node_view",
            "monitor detail contract",
        )

        monitor_view = normalize_node_view(
            node_id="monitor",
            status=build_monitor_status(),
            last_seen=1000.0,
            now=1000.0,
        )

        monitor_detail = monitor_view["details"]["detail"]
        self.assertEqual(monitor_detail["recent_event_summaries"][0]["event_id"], f"evt-{config.HOST_ID}-7")
        self.assertEqual(monitor_detail["last_sink_result"]["status"], "logged")
        self.assertEqual(monitor_detail["last_ack_result"]["status"], "acknowledged")
        self.assertEqual(monitor_detail["traffic"]["next_peer"]["hop_state"], "not_applicable")

    def test_sparse_role_details_degrade_gracefully(self) -> None:
        normalize_node_view = self._require_controller_api(
            "normalize_node_view",
            "sparse role detail contract",
        )

        relay_view = normalize_node_view(
            node_id="r2",
            status={
                "msg_type": "STATUS",
                "node_id": "r2",
                "state": "실행 중",
                "queue_length": 0,
                "pending_ack_count": 0,
                "retry_total": 0,
                "duplicate_dropped": 0,
                "note": "초기화됨",
                "detail": {"role": "relay", "pending_ack_state": []},
            },
            last_seen=1000.0,
            now=1000.0,
        )

        self.assertEqual(relay_view["observed_liveness"], "live")
        self.assertEqual(relay_view["details"]["detail"]["pending_ack_state"], [])
        self.assertNotIn("last_downstream_result", relay_view["details"]) 

    def test_controller_status_replacement_drops_omitted_last_event(self) -> None:
        controller = controller_ui.ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._apply_status(build_local_agent_status())
        idle_status = build_local_agent_status()
        idle_status.pop("last_event", None)
        idle_status["detail"]["detected_fault"] = None
        idle_status["detail"]["emitted_event"] = None
        idle_status["detail"]["downstream_result"] = {"status": "idle", "reason": "no_fault"}
        controller._apply_status(idle_status)

        stored = controller.node_status["local-agent"]
        self.assertNotIn("last_event", stored)
        self.assertEqual(stored["detail"]["downstream_result"]["status"], "idle")

    def test_controller_derives_not_started_for_unseen_peer(self) -> None:
        controller = controller_ui.ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        relay_status = build_relay_status(node_id="r1")
        relay_status["detail"]["traffic"]["next_peer"]["hop_state"] = "unknown"
        controller._apply_status(relay_status)

        frame = "\n".join(controller._build_frame_lines(scripted_demo=False))
        self.assertIn("hop summary: prev=acknowledged next=not_started", frame)


if __name__ == "__main__":
    unittest.main()
