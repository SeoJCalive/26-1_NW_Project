from __future__ import annotations

import unittest
from typing import Any

from nw_demo.local_agent import LocalAgent


def build_host_state(**overrides: object) -> dict[str, Any]:
    state: dict[str, Any] = {
        "host_id": "host-1",
        "cpu_usage": 24,
        "memory_usage": 48,
        "service_state": "UP",
        "latency_state": "NORMAL",
        "latency_ms": 33,
        "fault_mode": "NORMAL",
        "last_update_time": "2026-04-29T13:40:00+00:00",
    }
    state.update(overrides)
    return state


class LocalAgentEventPolicyTests(unittest.TestCase):
    def test_normal_host_state_change_emits_visibility_event(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        host_state = build_host_state()

        event_type = agent._select_event_type(host_state, detected_fault=None)
        event = agent._build_event(event_type, host_state)

        self.assertEqual(event_type, "HOST_STATE_UPDATE")
        self.assertEqual(event["msg_type"], "EVENT")
        self.assertEqual(event["event_type"], "HOST_STATE_UPDATE")
        self.assertEqual(event["severity"], "INFO")

    def test_unchanged_normal_host_state_stays_idle_after_successful_emit(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        host_state = build_host_state()
        agent.last_host_state_signature = agent._host_state_signature(host_state)

        self.assertIsNone(agent._select_event_type(host_state, detected_fault=None))

    def test_repeated_fault_is_suppressed_until_fault_signature_changes(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        host_state = build_host_state(cpu_usage=96, fault_mode="CPU_SPIKE")
        agent.last_fault_signature = "CPU_SPIKE"

        self.assertIsNone(agent._select_event_type(host_state, detected_fault="CPU_SPIKE"))


if __name__ == "__main__":
    unittest.main()
