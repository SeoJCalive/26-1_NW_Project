from __future__ import annotations

import unittest
import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

from nw_demo.local_agent import LocalAgent
from nw_demo.routing import ROUTE_BACKUP, ROUTE_PRIMARY, ROUTE_STATE_BYPASS_ACTIVE, ROUTE_STATE_FAILED
from nw_demo.messages import json_roundtrip


def build_host_state(**overrides: object) -> dict[str, Any]:
    state: dict[str, Any] = {
        "host_id": "host-1",
        "cpu_usage": 24,
        "memory_usage": 48,
        "service_state": "UP",
        "latency_ms": 33,
        "last_update_time": "2026-04-29T13:40:00+00:00",
    }
    state.update(overrides)
    return state


class LocalAgentEventPolicyTests(unittest.IsolatedAsyncioTestCase):
    def test_normal_host_state_change_emits_visibility_event(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        host_state = build_host_state()

        event_type = agent._select_event_type(host_state, detected_fault=None)
        if event_type is None:
            self.fail("normal host state did not produce visibility event")
        event = agent._build_event(event_type, host_state)

        self.assertEqual(event_type, "HOST_STATE_UPDATE")
        self.assertEqual(event["msg_type"], "EVENT")
        self.assertEqual(event["event_type"], "HOST_STATE_UPDATE")
        self.assertEqual(event["severity"], "INFO")
        self.assertEqual(event["payload"]["fault_mode"], "NORMAL")

    def test_unchanged_normal_host_state_stays_idle_after_successful_emit(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        host_state = build_host_state()
        agent.last_host_state_signature = agent._host_state_signature(host_state)

        self.assertIsNone(agent._select_event_type(host_state, detected_fault=None))

    def test_repeated_fault_is_suppressed_until_fault_signature_changes(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        host_state = build_host_state(cpu_usage=96)
        agent.last_fault_signature = "CPU_SPIKE"

        self.assertIsNone(agent._select_event_type(host_state, detected_fault="CPU_SPIKE"))

    def test_suppressed_repeated_fault_preserves_fault_signature(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        agent.last_fault_signature = "CPU_SPIKE"
        agent.last_emitted_event = {"event_id": "evt-host-1-1"}

        agent._handle_no_selected_event("CPU_SPIKE")

        self.assertEqual(agent.last_fault_signature, "CPU_SPIKE")
        self.assertEqual(agent.last_emitted_event, {"event_id": "evt-host-1-1"})
        self.assertEqual(agent.last_downstream_result, {"status": "suppressed_duplicate_fault", "fault": "CPU_SPIKE", "event_id": "evt-host-1-1"})

    async def test_agent_uses_backup_route_after_primary_failure_with_same_event_id(self) -> None:
        agent = LocalAgent(
            "127.0.0.1",
            9102,
            "127.0.0.1",
            9110,
            "127.0.0.1",
            9101,
            "127.0.0.1",
            9103,
            backup_downstream_host="127.0.0.1",
            backup_downstream_port=9106,
        )
        event = agent._build_event("CPU_SPIKE", build_host_state(cpu_usage=96))
        captured_messages: list[dict[str, Any]] = []

        async def primary_timeout_then_backup_ack(host: str, port: int, message: dict[str, Any], **kwargs: object) -> dict[str, object]:
            captured_messages.append(json_roundtrip(message))
            if port == 9103:
                raise asyncio.TimeoutError
            return {"msg_type": "ACK", "ack_for": message["event_id"], "from_node": "r1b"}

        with patch("nw_demo.local_agent.send_request", new=AsyncMock(side_effect=primary_timeout_then_backup_ack)):
            delivered_event, delivered = await agent._deliver_event(event)

        self.assertTrue(delivered)
        self.assertEqual([message["event_id"] for message in captured_messages], [event["event_id"], event["event_id"]])
        self.assertEqual([message["route_trace"] for message in captured_messages], [[], delivered_event["route_trace"][:1]])
        self.assertEqual(delivered_event["routing"]["route_state"], ROUTE_STATE_BYPASS_ACTIVE)
        self.assertEqual(delivered_event["routing"]["active_route"], ROUTE_BACKUP)
        self.assertEqual(delivered_event["routing"]["failed_hop"], "local-agent->r1")
        self.assertEqual(delivered_event["routing"]["suspected_node"], "r1")
        self.assertEqual(delivered_event["route_trace"][0]["from_node"], "local-agent")
        self.assertEqual(delivered_event["route_trace"][0]["to_node"], "r1")
        self.assertEqual(delivered_event["route_trace"][0]["route_id"], ROUTE_PRIMARY)
        self.assertEqual(delivered_event["route_trace"][0]["result"], "timeout")
        self.assertEqual(delivered_event["route_trace"][1]["to_node"], "r1b")
        self.assertEqual(delivered_event["route_trace"][1]["route_id"], ROUTE_BACKUP)
        self.assertEqual(delivered_event["route_trace"][1]["result"], "acknowledged")
        if agent.last_downstream_result is None:
            self.fail("agent did not store downstream result")
        self.assertEqual(agent.last_downstream_result["active_route"], ROUTE_BACKUP)
        self.assertEqual(agent.last_routing_detail["route_state"], ROUTE_STATE_BYPASS_ACTIVE)
        self.assertEqual(agent.last_routing_detail["active_downstream"], "r1b")

    async def test_agent_reports_failed_primary_when_no_backup_is_configured(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        event = agent._build_event("CPU_SPIKE", build_host_state(cpu_usage=96))

        with patch("nw_demo.local_agent.send_request", new=AsyncMock(side_effect=ConnectionError)):
            delivered_event, delivered = await agent._deliver_event(event)

        self.assertFalse(delivered)
        self.assertEqual(delivered_event["routing"]["route_state"], ROUTE_STATE_FAILED)
        self.assertEqual(delivered_event["routing"]["active_route"], ROUTE_PRIMARY)
        self.assertEqual(delivered_event["route_trace"][0]["to_node"], "r1")
        self.assertEqual(delivered_event["route_trace"][0]["result"], "connection_error")

    def test_agent_detects_faults_from_raw_observations_without_host_semantic_fields(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)

        cases = [
            (build_host_state(cpu_usage=96), "CPU_SPIKE"),
            (build_host_state(service_state="DOWN"), "SERVICE_DOWN"),
            (build_host_state(latency_ms=260), "LATENCY_HIGH"),
            (build_host_state(), None),
        ]
        for host_state, expected_fault in cases:
            with self.subTest(expected_fault=expected_fault):
                self.assertEqual(agent._detect_fault(host_state), expected_fault)
                event_type = expected_fault or "HOST_STATE_UPDATE"
                event = agent._build_event(event_type, host_state)
                self.assertEqual(event["payload"]["fault_mode"], expected_fault or "NORMAL")

    def test_agent_ignores_contradictory_legacy_host_semantic_fields(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        host_state = build_host_state(fault_mode="CPU_SPIKE", latency_state="HIGH")

        detected_fault = agent._detect_fault(host_state)
        event_type = agent._select_event_type(host_state, detected_fault)
        if event_type is None:
            self.fail("normal raw observation should emit HOST_STATE_UPDATE")
        event = agent._build_event(event_type, host_state)

        self.assertIsNone(detected_fault)
        self.assertEqual(event["event_type"], "HOST_STATE_UPDATE")
        self.assertEqual(event["payload"]["fault_mode"], "NORMAL")

    def test_agent_fault_precedence_remains_cpu_service_latency(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)

        self.assertEqual(agent._detect_fault(build_host_state(cpu_usage=96, service_state="DOWN", latency_ms=260)), "CPU_SPIKE")
        self.assertEqual(agent._detect_fault(build_host_state(service_state="DOWN", latency_ms=260)), "SERVICE_DOWN")


if __name__ == "__main__":
    unittest.main()
