from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import AsyncMock, patch

from nw_demo.monitor import Monitor
from nw_demo.relay import RelayNode
from nw_demo.routing import (
    BACKUP_PATH,
    PRIMARY_PATH,
    ROUTE_BACKUP,
    ROUTE_PRIMARY,
    ROUTE_STATE_BYPASS_ACTIVE,
    ROUTE_STATE_PRIMARY,
    default_detail_routing,
    fault_localization_from_event,
    initialize_event_route_metadata,
    make_route_trace_entry,
    route_id_for_edge,
    validate_route_edge,
)
from tests.status_builders import build_relay_status


def _event_without_route_trace() -> dict[str, object]:
    return {
        "msg_type": "EVENT",
        "event_id": "evt-host-1-7",
        "seq_no": 7,
        "host_id": "host-1",
        "agent_id": "agent-1",
        "event_type": "CPU_SPIKE",
        "severity": "WARN",
        "timestamp": "2026-05-21T00:00:00+00:00",
        "payload": {"cpu": 96},
    }


class BypassRoutingContractTests(unittest.IsolatedAsyncioTestCase):
    def test_route_paths_allow_only_primary_and_backup_edges(self) -> None:
        self.assertEqual(PRIMARY_PATH, ("local-agent", "r1", "r2", "monitor"))
        self.assertEqual(BACKUP_PATH, ("local-agent", "r1b", "r2b", "monitor"))
        self.assertEqual(route_id_for_edge("r1", "r2"), ROUTE_PRIMARY)
        self.assertEqual(route_id_for_edge("r1b", "r2b"), ROUTE_BACKUP)
        self.assertIsNone(route_id_for_edge("r1", "r2b"))
        self.assertIsNone(route_id_for_edge("r1b", "r2"))

        with self.assertRaises(ValueError):
            validate_route_edge("r1", "r2b")
        with self.assertRaises(ValueError):
            validate_route_edge("r1b", "r2")

    def test_event_route_metadata_is_additive_and_backward_compatible(self) -> None:
        event = _event_without_route_trace()
        routed_event = initialize_event_route_metadata(event)

        self.assertEqual(routed_event["event_id"], event["event_id"])
        self.assertEqual(routed_event["route_trace"], [])
        self.assertEqual(routed_event["routing"]["route_state"], ROUTE_STATE_PRIMARY)
        self.assertEqual(routed_event["routing"]["active_route"], ROUTE_PRIMARY)
        self.assertNotIn("route_trace", event)

    def test_route_trace_entry_rejects_cross_path_mesh(self) -> None:
        entry = make_route_trace_entry(
            from_node="r1",
            to_node="r2",
            route_id=ROUTE_PRIMARY,
            attempt_no=1,
            phase="downstream_event",
            result="acknowledged",
            timestamp="2026-05-21T00:00:00+00:00",
        )
        self.assertEqual(entry["from_node"], "r1")
        self.assertEqual(entry["to_node"], "r2")

        with self.assertRaises(ValueError):
            make_route_trace_entry(
                from_node="r1",
                to_node="r2b",
                route_id=ROUTE_BACKUP,
                attempt_no=1,
                phase="downstream_event",
                result="timeout",
            )

        with self.assertRaises(ValueError):
            make_route_trace_entry(
                from_node="r1",
                to_node="r2",
                route_id=ROUTE_BACKUP,
                attempt_no=1,
                phase="downstream_event",
                result="timeout",
            )

        with self.assertRaises(ValueError):
            make_route_trace_entry(
                from_node="r1b",
                to_node="r2b",
                route_id=ROUTE_PRIMARY,
                attempt_no=1,
                phase="downstream_event",
                result="timeout",
            )

    def test_detail_routing_is_additive_to_existing_traffic_detail(self) -> None:
        status = build_relay_status()
        detail = status["detail"]
        detail["routing"] = default_detail_routing(
            event_id="evt-host-1-7",
            primary_downstream="r2",
            backup_downstream=None,
        )

        self.assertEqual(detail["routing"]["route_state"], ROUTE_STATE_PRIMARY)
        self.assertEqual(detail["routing"]["active_downstream"], "r2")
        self.assertIn("traffic", detail)
        self.assertEqual(detail["traffic"]["next_peer"]["peer_node_id"], "r2")

    def test_fault_localization_does_not_guess_when_route_trace_is_missing(self) -> None:
        localization = fault_localization_from_event(_event_without_route_trace())

        self.assertEqual(localization["failure_scope"], "unknown")
        self.assertIsNone(localization["failed_hop"])
        self.assertIsNone(localization["suspected_node"])
        self.assertEqual(localization["confidence"], "low")
        self.assertEqual(localization["basis"], "route_trace_unavailable")

    def test_fault_localization_treats_forwarded_route_trace_as_non_failure(self) -> None:
        event = initialize_event_route_metadata(_event_without_route_trace())
        event["route_trace"].append(
            make_route_trace_entry(
                from_node="r1b",
                to_node="r2b",
                route_id=ROUTE_BACKUP,
                attempt_no=1,
                phase="downstream_event",
                result="forwarded",
            )
        )

        localization = fault_localization_from_event(event)

        self.assertEqual(localization["failure_scope"], "unknown")
        self.assertEqual(localization["basis"], "route_trace_no_failed_hop")

    async def test_backup_relay_appends_only_backup_route_trace_to_outbound_event(self) -> None:
        relay = RelayNode("r1b", "127.0.0.1", 9106, "127.0.0.1", 9110, "127.0.0.1", 9107)
        relay.processing_delay = 0
        event = initialize_event_route_metadata(_event_without_route_trace())
        event["routing"] = {
            "route_state": ROUTE_STATE_BYPASS_ACTIVE,
            "active_route": ROUTE_BACKUP,
            "failed_hop": "local-agent->r1",
            "suspected_node": "r1",
            "reroute_reason": "timeout",
        }
        captured_outbound: list[dict[str, Any]] = []

        async def ack_downstream(host: str, port: int, message: dict[str, Any], **kwargs: object) -> dict[str, object]:
            captured_outbound.append(message)
            return {"msg_type": "ACK", "ack_for": message["event_id"], "from_node": "r2b"}

        with patch("nw_demo.relay.send_request", new=AsyncMock(side_effect=ack_downstream)):
            ack = await relay.handle_network_message(event)

        if ack is None:
            self.fail("relay did not ACK backup event")
        self.assertEqual(ack["msg_type"], "ACK")
        self.assertNotIn("downstream_error", ack)
        self.assertEqual(len(captured_outbound), 1)
        outbound_trace = captured_outbound[0]["route_trace"]
        self.assertEqual(outbound_trace[-1]["from_node"], "r1b")
        self.assertEqual(outbound_trace[-1]["to_node"], "r2b")
        self.assertEqual(outbound_trace[-1]["route_id"], ROUTE_BACKUP)
        self.assertEqual(outbound_trace[-1]["result"], "forwarded")

    async def test_primary_relay_rejects_backup_route_event_without_cross_forwarding(self) -> None:
        relay = RelayNode("r1", "127.0.0.1", 9103, "127.0.0.1", 9110, "127.0.0.1", 9104)
        event = initialize_event_route_metadata(_event_without_route_trace())
        event["routing"] = {
            "route_state": ROUTE_STATE_BYPASS_ACTIVE,
            "active_route": ROUTE_BACKUP,
            "failed_hop": "local-agent->r1",
            "suspected_node": "r1",
            "reroute_reason": "timeout",
        }

        with patch("nw_demo.relay.send_request", new=AsyncMock()) as send_request:
            response = await relay.handle_network_message(event)

        if response is None:
            self.fail("relay did not return route mismatch response")
        self.assertEqual(response["msg_type"], "ERROR")
        self.assertEqual(response["reason"], "route_mismatch")
        send_request.assert_not_awaited()
        if relay.last_downstream_result is None:
            self.fail("relay did not store route mismatch result")
        self.assertEqual(relay.last_downstream_result["reason"], "route_mismatch")

    async def test_primary_relay_preserves_paused_downstream_error_in_final_failure(self) -> None:
        relay = RelayNode("r1", "127.0.0.1", 9103, "127.0.0.1", 9110, "127.0.0.1", 9104)
        relay.processing_delay = 0
        event = initialize_event_route_metadata(_event_without_route_trace())

        async def paused_downstream(host: str, port: int, message: dict[str, Any], **kwargs: object) -> dict[str, object]:
            return {"msg_type": "ERROR", "reason": "paused", "node_id": "r2", "payload": {"raw": True}}

        with patch("nw_demo.relay.send_request", new=AsyncMock(side_effect=paused_downstream)):
            response = await relay.handle_network_message(event)

        if response is None:
            self.fail("relay did not return final delivery failure")
        self.assertEqual(response["msg_type"], "ERROR")
        self.assertEqual(response["reason"], "delivery_failed")
        downstream_error = response.get("downstream_error")
        if not isinstance(downstream_error, dict):
            self.fail("relay did not preserve downstream_error")
        self.assertEqual(downstream_error["failed_hop"], "r1->r2")
        self.assertEqual(downstream_error["suspected_node"], "r2")
        self.assertEqual(downstream_error["failure_reason"], "paused")
        self.assertEqual(downstream_error["downstream_node_id"], "r2")
        self.assertEqual(downstream_error["event_id"], event["event_id"])
        self.assertEqual(downstream_error["basis"], "reported_downstream_error")
        self.assertNotIn("payload", downstream_error)
        self.assertNotIn("raw", downstream_error)
        self.assertEqual(relay.last_downstream_result, {
            "status": "delivery_failed",
            "event_id": event["event_id"],
            "attempts": 3,
            "last_outcome": "ack_missing",
            "downstream_error": downstream_error,
        })

    async def test_monitor_publishes_trace_unavailable_fallback_for_legacy_event(self) -> None:
        monitor = Monitor("127.0.0.1", 9105, "127.0.0.1", 9110)

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            ack = await monitor.handle_network_message(_event_without_route_trace())

        if ack is None:
            self.fail("monitor did not ACK legacy event")
        self.assertEqual(ack["msg_type"], "ACK")
        self.assertEqual(monitor.last_route_trace, [])
        route_summary = monitor.last_route_summary
        if route_summary is None:
            self.fail("monitor did not store route summary")
        self.assertEqual(route_summary["route_state"], ROUTE_STATE_PRIMARY)
        fault_localization = monitor.last_fault_localization
        if fault_localization is None:
            self.fail("monitor did not store fault localization")
        self.assertEqual(fault_localization["failure_scope"], "unknown")

        await_args = send_request.await_args
        if await_args is None:
            self.fail("monitor did not publish status")
        status = await_args.args[2]
        if not isinstance(status, dict):
            self.fail("published status is not a dictionary")
        detail = status["detail"]
        self.assertEqual(detail["last_route_trace"], [])
        self.assertEqual(detail["last_route_summary"]["route_state"], ROUTE_STATE_PRIMARY)
        self.assertEqual(detail["last_fault_localization"]["basis"], "route_trace_unavailable")

    async def test_monitor_localizes_primary_failure_from_backup_route_event_without_overclaiming(self) -> None:
        monitor = Monitor("127.0.0.1", 9105, "127.0.0.1", 9110)
        event = initialize_event_route_metadata(_event_without_route_trace())
        event["routing"] = {
            "route_state": ROUTE_STATE_BYPASS_ACTIVE,
            "active_route": ROUTE_BACKUP,
            "failed_hop": "local-agent->r1",
            "suspected_node": "r1",
            "reroute_reason": "connection_error",
        }
        event["route_trace"] = [
            make_route_trace_entry(
                from_node="local-agent",
                to_node="r1",
                route_id=ROUTE_PRIMARY,
                attempt_no=1,
                phase="event_forward",
                result="connection_error",
                failure_reason="connection_error",
                timestamp="2026-05-21T00:00:01+00:00",
            ),
            make_route_trace_entry(
                from_node="r1b",
                to_node="r2b",
                route_id=ROUTE_BACKUP,
                attempt_no=1,
                phase="downstream_event",
                result="forwarded",
                timestamp="2026-05-21T00:00:02+00:00",
            ),
            make_route_trace_entry(
                from_node="r2b",
                to_node="monitor",
                route_id=ROUTE_BACKUP,
                attempt_no=1,
                phase="downstream_event",
                result="forwarded",
                timestamp="2026-05-21T00:00:03+00:00",
            ),
        ]

        with patch("nw_demo.base.send_request", new=AsyncMock()) as send_request:
            ack = await monitor.handle_network_message(event)

        if ack is None:
            self.fail("monitor did not ACK backup event")
        self.assertEqual(ack["msg_type"], "ACK")
        route_summary = monitor.last_route_summary
        if route_summary is None:
            self.fail("monitor did not store route summary")
        fault_localization = monitor.last_fault_localization
        if fault_localization is None:
            self.fail("monitor did not store fault localization")
        self.assertEqual(route_summary["route_state"], ROUTE_STATE_BYPASS_ACTIVE)
        self.assertEqual(route_summary["active_route"], ROUTE_BACKUP)
        self.assertEqual(fault_localization["failed_hop"], "local-agent->r1")
        self.assertEqual(fault_localization["suspected_node"], "r1")
        self.assertEqual(fault_localization["confidence"], "medium")
        self.assertEqual(fault_localization["basis"], "route_trace_failed_hop")
        self.assertEqual(monitor.traffic_snapshot()["previous_peer"]["peer_node_id"], "r2b")

        await_args = send_request.await_args
        if await_args is None:
            self.fail("monitor did not publish status")
        status = await_args.args[2]
        if not isinstance(status, dict):
            self.fail("published status is not a dictionary")
        detail = status["detail"]
        self.assertEqual(detail["last_route_summary"]["active_route"], ROUTE_BACKUP)
        self.assertEqual(detail["last_fault_localization"]["failure_scope"], "hop")
        self.assertEqual(detail["traffic"]["previous_peer"]["peer_node_id"], "r2b")


if __name__ == "__main__":
    unittest.main()
