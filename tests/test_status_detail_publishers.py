from __future__ import annotations

import unittest
from typing import Any, cast
from unittest.mock import AsyncMock, patch

from nw_demo.messages import make_ack
from nw_demo.local_agent import LocalAgent
from nw_demo.host_simulator import HostSimulator
from nw_demo.monitor import Monitor
from nw_demo.relay import RelayNode
from nw_demo.routing import ROUTE_BACKUP, ROUTE_PRIMARY, ROUTE_STATE_BYPASS_ACTIVE, initialize_event_route_metadata, make_route_trace_entry


def _captured_status(send_request: AsyncMock) -> dict[str, Any]:
    await_args = send_request.await_args
    if await_args is None:
        raise AssertionError("status was not published")
    return cast(dict[str, Any], await_args.args[2])


class StatusDetailPublisherTests(unittest.IsolatedAsyncioTestCase):
    async def test_host_publishes_structured_self_perspective_detail(self) -> None:
        host = HostSimulator("127.0.0.1", 9101, "127.0.0.1", 9110)
        host._tick = 4
        host._fault_type = "CPU_SPIKE"
        host._apply_fault_state("CPU_SPIKE")
        host.record_peer_message(
            "previous_peer",
            "last_received",
            {"kind": "get_host_state"},
            peer_node_id="local-agent",
            peer_role="agent",
            hop_state="request_received",
            logical_id="get_host_state",
            phase="host_request",
        )

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            await host.publish_status(note="호스트 tick 4")

        status = _captured_status(send_request)
        detail = status["detail"]
        self.assertEqual(status["host_state"]["host_id"], "host-1")
        self.assertEqual(detail["role"], "host")
        self.assertEqual(detail["tick"], 4)
        self.assertTrue(detail["fault_active"])
        self.assertEqual(detail["fault_type"], "CPU_SPIKE")
        self.assertEqual(detail["host_state"]["cpu_usage"], 96)
        self.assertNotIn("fault_mode", detail["host_state"])
        self.assertNotIn("latency_state", detail["host_state"])
        self.assertEqual(detail["traffic"]["previous_peer"]["peer_node_id"], "local-agent")
        self.assertEqual(detail["traffic"]["next_peer"]["hop_state"], "not_applicable")

    async def test_host_fault_can_be_manually_enabled_and_disabled(self) -> None:
        host = HostSimulator("127.0.0.1", 9101, "127.0.0.1", 9110)

        with patch("nw_demo.base.send_request", new=AsyncMock()):
            await host.on_control({"command": "set_fault", "params": {"fault_type": "SERVICE_DOWN", "enabled": True}})

        self.assertEqual(host.snapshot()["service_state"], "DOWN")
        self.assertNotIn("fault_mode", host.snapshot())
        self.assertNotIn("latency_state", host.snapshot())
        self.assertIsNone(host._fault_end_monotonic)

        with patch("nw_demo.base.send_request", new=AsyncMock()):
            await host.on_control({"command": "set_fault", "params": {"fault_type": "SERVICE_DOWN", "enabled": False}})

        self.assertEqual(host.snapshot()["service_state"], "UP")
        self.assertNotIn("fault_mode", host.snapshot())
        self.assertNotIn("latency_state", host.snapshot())
        self.assertIsNone(host._fault_type)

    async def test_paused_host_does_not_serve_host_state_to_agent(self) -> None:
        host = HostSimulator("127.0.0.1", 9101, "127.0.0.1", 9110)
        host.running = False

        response = await host.handle_network_message({"kind": "get_host_state"})

        self.assertEqual(response, {"msg_type": "ERROR", "reason": "paused", "node_id": "host-simulator"})
        traffic = host.traffic_snapshot()["previous_peer"]
        self.assertEqual(traffic["peer_node_id"], "local-agent")
        self.assertEqual(traffic["hop_state"], "paused")
        self.assertEqual(traffic["failure_reason"], "paused")
        self.assertEqual(traffic["last_sent"]["payload"], response)

    async def test_host_latency_fault_is_raw_observation_with_injection_metadata(self) -> None:
        host = HostSimulator("127.0.0.1", 9101, "127.0.0.1", 9110)
        host._fault_type = "LATENCY_HIGH"
        host._apply_fault_state("LATENCY_HIGH")

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            await host.publish_status(note="fault 켜짐: LATENCY_HIGH")

        status = _captured_status(send_request)
        detail = status["detail"]
        self.assertEqual(status["host_state"]["latency_ms"], 260)
        self.assertNotIn("fault_mode", status["host_state"])
        self.assertNotIn("latency_state", status["host_state"])
        self.assertTrue(detail["fault_active"])
        self.assertEqual(detail["fault_type"], "LATENCY_HIGH")

    async def test_local_agent_publishes_latest_input_fault_event_and_downstream_result(self) -> None:
        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        agent.latest_input_state = {
            "host_id": "host-1",
            "cpu_usage": 96,
            "memory_usage": 51,
            "service_state": "UP",
            "latency_ms": 28,
            "last_update_time": "2026-04-27T10:00:00+00:00",
        }
        agent.latest_input_result = {"status": "ok", "source": "host"}
        agent.last_detected_fault = "CPU_SPIKE"
        agent.last_emitted_event = agent._build_event("CPU_SPIKE", agent.latest_input_state)
        agent.last_downstream_result = {
            "status": "acknowledged",
            "event_id": agent.last_emitted_event["event_id"],
            "ack": {"msg_type": "ACK", "ack_for": agent.last_emitted_event["event_id"], "from_node": "r1"},
        }

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            await agent.publish_status(note=f"이벤트 생성 {agent.last_emitted_event['event_id']}")

        status = _captured_status(send_request)
        detail = status["detail"]
        self.assertEqual(status["last_event"]["event_id"], agent.last_emitted_event["event_id"])
        self.assertEqual(detail["latest_input_state"]["cpu_usage"], 96)
        self.assertEqual(detail["detected_fault"], "CPU_SPIKE")
        self.assertEqual(detail["emitted_event"]["event_id"], agent.last_emitted_event["event_id"])
        self.assertEqual(detail["downstream_result"]["status"], "acknowledged")
        self.assertEqual(detail["traffic"]["previous_peer"]["peer_node_id"], "host-simulator")
        self.assertEqual(detail["traffic"]["next_peer"]["peer_node_id"], "r1")

    async def test_relay_publishes_recent_received_pending_retry_and_forward_result_detail(self) -> None:
        relay = RelayNode("r1", "127.0.0.1", 9103, "127.0.0.1", 9110, "127.0.0.1", 9104)
        relay.recent_received_event_ids.extendleft(["evt-host-1-6", "evt-host-1-7"])
        relay.last_received_event = {
            "event_id": "evt-host-1-7",
            "event_type": "CPU_SPIKE",
            "seq_no": 7,
            "host_id": "host-1",
            "timestamp": "2026-04-27T10:00:01+00:00",
        }
        relay.pending_ack_detail["evt-host-1-7"] = {
            "event_id": "evt-host-1-7",
            "event_type": "CPU_SPIKE",
            "seq_no": 7,
            "downstream_target": "r2",
            "attempt": 2,
            "state": "retrying",
            "last_outcome": "retrying",
        }
        relay.pending_ack_table["evt-host-1-7"] = 1
        relay.last_downstream_result = {
            "status": "retry_pending",
            "event_id": "evt-host-1-7",
            "attempt": 2,
            "reason": "timeout",
        }
        relay.last_forwarded_result = {
            "status": "forwarded",
            "event_id": "evt-host-1-6",
            "attempts": 1,
            "downstream_target": "r2",
        }
        relay.record_peer_message(
            "previous_peer",
            "last_received",
            {"msg_type": "EVENT", "event_id": "evt-host-1-7", "event_type": "CPU_SPIKE", "seq_no": 7, "host_id": "host-1", "timestamp": "2026-04-27T10:00:01+00:00"},
            peer_node_id="local-agent",
            peer_role="agent",
            hop_state="request_received",
            logical_id="evt-host-1-7",
            phase="upstream_event",
        )
        relay.record_peer_message(
            "next_peer",
            "last_received",
            {"msg_type": "ACK", "ack_for": "evt-host-1-7", "from_node": "r2", "timestamp": "2026-04-27T10:00:03+00:00"},
            peer_node_id="r2",
            peer_role="relay",
            hop_state="acknowledged",
            logical_id="evt-host-1-7",
            attempt_no=2,
            phase="downstream_ack",
        )

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            await relay.publish_status(note="evt-host-1-7 재시도 1회")

        status = _captured_status(send_request)
        detail = status["detail"]
        self.assertEqual(detail["recent_received_event_ids"][0], "evt-host-1-7")
        self.assertEqual(detail["pending_ack_state"][0]["attempt"], 2)
        self.assertEqual(detail["last_downstream_result"]["reason"], "timeout")
        self.assertEqual(detail["last_forwarded_result"]["status"], "forwarded")
        self.assertEqual(detail["traffic"]["previous_peer"]["last_received"]["phase"], "upstream_event")
        self.assertEqual(detail["traffic"]["next_peer"]["peer_node_id"], "r2")

    async def test_relay_reset_during_delivery_does_not_crash_or_reuse_cleared_pending_detail(self) -> None:
        relay = RelayNode("r1", "127.0.0.1", 9103, "127.0.0.1", 9110, "127.0.0.1", 9104)
        event: dict[str, object] = {
            "msg_type": "EVENT",
            "event_id": "evt-host-1-9",
            "seq_no": 9,
            "host_id": "host-1",
            "event_type": "CPU_SPIKE",
            "timestamp": "2026-04-27T10:00:09+00:00",
        }

        async def reset_then_ack(*args: object, **kwargs: object) -> dict[str, object]:
            await relay.reset_state()
            return make_ack("evt-host-1-9", "r2")

        with patch.object(relay, "publish_status", new=AsyncMock()) as publish_status:
            with patch("nw_demo.relay.send_request", new=AsyncMock(side_effect=reset_then_ack)):
                accepted = await relay._deliver_with_retry(event)

        self.assertFalse(accepted)
        if relay.last_downstream_result is None:
            self.fail("relay did not store downstream result")
        self.assertEqual(relay.last_downstream_result["status"], "reset_interrupted")
        self.assertNotIn("evt-host-1-9", relay.pending_ack_table)
        self.assertNotIn("evt-host-1-9", relay.pending_ack_detail)
        self.assertTrue(publish_status.await_count >= 1)

    async def test_relay_publishes_upstream_receipt_before_downstream_delivery(self) -> None:
        relay = RelayNode("r1", "127.0.0.1", 9103, "127.0.0.1", 9110, "127.0.0.1", 9104)
        event: dict[str, object] = {
            "msg_type": "EVENT",
            "event_id": "evt-host-1-10",
            "seq_no": 10,
            "host_id": "host-1",
            "event_type": "CPU_SPIKE",
            "timestamp": "2026-04-27T10:00:10+00:00",
        }
        order: list[tuple[str, str | None, str | None]] = []

        async def publish_status(*, extra: object | None = None, note: str | None = None) -> None:
            snapshot = relay.traffic_snapshot()
            last_received = snapshot["previous_peer"]["last_received"]
            logical_id = last_received["logical_id"] if last_received else None
            order.append(("publish", note, logical_id))

        async def deliver_with_retry(delivered_event: dict[str, object]) -> bool:
            order.append(("deliver", None, str(delivered_event["event_id"])))
            return False

        with patch.object(relay, "publish_status", new=AsyncMock(side_effect=publish_status)):
            with patch.object(relay, "_deliver_with_retry", new=AsyncMock(side_effect=deliver_with_retry)):
                response = await relay.handle_network_message(event)

        if response is None:
            self.fail("relay did not return a response")
        self.assertEqual(response["msg_type"], "ERROR")
        self.assertEqual(order[0], ("publish", "evt-host-1-10 upstream 수신", "evt-host-1-10"))
        self.assertEqual(order[1], ("deliver", None, "evt-host-1-10"))

    async def test_status_publish_does_not_expose_control_token_in_status_payload(self) -> None:
        relay = RelayNode("r1", "127.0.0.1", 9103, "127.0.0.1", 9110, "127.0.0.1", 9104, control_token="secret-token")

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            await relay.publish_status(note="token hidden")

        outbound = _captured_status(send_request)
        self.assertEqual(outbound["msg_type"], "STATUS_REPORT")
        self.assertEqual(outbound["control_token"], "secret-token")
        self.assertNotIn("control_token", outbound["status"])

    async def test_monitor_publishes_sink_processing_summaries(self) -> None:
        monitor = Monitor("127.0.0.1", 9105, "127.0.0.1", 9110)
        monitor.recent_events.appendleft("evt-host-1-7 CPU_SPIKE WARN host=host-1 seq=7")
        monitor.recent_event_summaries.appendleft(
            {
                "event_id": "evt-host-1-7",
                "event_type": "CPU_SPIKE",
                "severity": "WARN",
                "host_id": "host-1",
                "seq_no": 7,
                "timestamp": "2026-04-27T10:00:01+00:00",
            }
        )
        monitor.host_state_table["host-1"] = {
            "event_type": "CPU_SPIKE",
            "severity": "WARN",
            "payload": {"cpu": 96},
            "timestamp": "2026-04-27T10:00:01+00:00",
        }
        monitor.last_processed_event = {
            "event_id": "evt-host-1-7",
            "event_type": "CPU_SPIKE",
            "severity": "WARN",
            "host_id": "host-1",
            "seq_no": 7,
            "timestamp": "2026-04-27T10:00:01+00:00",
        }
        monitor.last_sink_result = {"status": "logged", "event_id": "evt-host-1-7", "host_id": "host-1", "seq_no": 7}
        monitor.last_ack_result = {"status": "acknowledged", "event_id": "evt-host-1-7", "duplicate": False}
        monitor.event_log.append({"event_id": "evt-host-1-7"})

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            await monitor.publish_status(note="evt-host-1-7 기록 완료")

        status = _captured_status(send_request)
        detail = status["detail"]
        self.assertEqual(status["duplicate_count"], 0)
        self.assertEqual(status["total_logged"], 1)
        self.assertEqual(detail["recent_event_summaries"][0]["event_id"], "evt-host-1-7")
        self.assertEqual(detail["last_sink_result"]["status"], "logged")
        self.assertEqual(detail["last_ack_result"]["status"], "acknowledged")
        self.assertEqual(detail["traffic"]["previous_peer"]["peer_node_id"], "r2")
        self.assertEqual(detail["traffic"]["next_peer"]["hop_state"], "not_applicable")

    async def test_monitor_publishes_downstream_failure_attribution_from_event_fields(self) -> None:
        monitor = Monitor("127.0.0.1", 9105, "127.0.0.1", 9110)
        event = initialize_event_route_metadata({
            "msg_type": "EVENT",
            "event_id": "evt-host-1-7",
            "seq_no": 7,
            "host_id": "host-1",
            "agent_id": "agent-1",
            "event_type": "CPU_SPIKE",
            "severity": "WARN",
            "timestamp": "2026-05-21T00:00:00+00:00",
            "payload": {"cpu": 96},
        })
        event["routing"] = {
            "route_state": ROUTE_STATE_BYPASS_ACTIVE,
            "active_route": ROUTE_BACKUP,
            "failed_hop": "r1->r2",
            "suspected_node": "r2",
            "reroute_reason": "paused",
        }
        event["route_trace"] = [
            make_route_trace_entry(
                from_node="local-agent",
                to_node="r1",
                route_id=ROUTE_PRIMARY,
                attempt_no=1,
                phase="event_forward",
                result="ack_missing",
                failure_reason="ack_missing",
                timestamp="2026-05-21T00:00:01+00:00",
            ),
            make_route_trace_entry(
                from_node="r1",
                to_node="r2",
                route_id=ROUTE_PRIMARY,
                attempt_no=1,
                phase="event_forward",
                result="failed",
                failure_reason="paused",
                timestamp="2026-05-21T00:00:02+00:00",
            ),
            make_route_trace_entry(
                from_node="r1b",
                to_node="r2b",
                route_id=ROUTE_BACKUP,
                attempt_no=1,
                phase="event_forward",
                result="acknowledged",
                timestamp="2026-05-21T00:00:03+00:00",
            ),
        ]

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            ack = await monitor.handle_network_message(event)

        if ack is None:
            self.fail("monitor did not ACK attributed event")
        self.assertEqual(ack["msg_type"], "ACK")
        status = _captured_status(send_request)
        detail = status["detail"]
        self.assertEqual(detail["last_route_summary"]["failed_hop"], "r1->r2")
        self.assertEqual(detail["last_route_summary"]["suspected_node"], "r2")
        self.assertEqual(detail["last_route_summary"]["reroute_reason"], "paused")
        self.assertEqual(detail["last_fault_localization"]["failed_hop"], "r1->r2")
        self.assertEqual(detail["last_fault_localization"]["suspected_node"], "r2")
        self.assertEqual(detail["last_fault_localization"]["failure_reason"], "paused")
        self.assertEqual(detail["last_fault_localization"]["basis"], "route_trace_failed_hop")
        self.assertEqual(detail["last_route_trace"][1]["from_node"], "r1")
        self.assertEqual(detail["last_route_trace"][1]["to_node"], "r2")

    async def test_monitor_publishes_structured_ack_drop_visibility(self) -> None:
        monitor = Monitor("127.0.0.1", 9105, "127.0.0.1", 9110)
        monitor.last_ack_result = {"status": "dropped", "event_id": "evt-host-1-7", "duplicate": False}
        monitor.record_peer_state("previous_peer", peer_node_id="r2", peer_role="relay", hop_state="ack_dropped", failure_reason="drop_next_ack")

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            await monitor.publish_status(note="evt-host-1-7 ACK 의도적으로 드롭")

        status = _captured_status(send_request)
        detail = status["detail"]
        self.assertEqual(detail["last_ack_result"]["status"], "dropped")
        self.assertEqual(detail["traffic"]["previous_peer"]["hop_state"], "ack_dropped")
        self.assertEqual(detail["traffic"]["previous_peer"]["failure_reason"], "drop_next_ack")


if __name__ == "__main__":
    unittest.main()
