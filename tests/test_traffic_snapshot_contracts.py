from __future__ import annotations

import unittest

from nw_sim.base import BaseNode, TRAFFIC_PAYLOAD_PREVIEW_LIMIT

from tests.status_builders import (
    build_host_status,
    build_local_agent_status,
    build_monitor_status,
    build_relay_status,
)


class TrafficSnapshotContractTests(unittest.IsolatedAsyncioTestCase):
    def test_status_builders_expose_structured_traffic_schema(self) -> None:
        for status in [build_host_status(), build_local_agent_status(), build_relay_status(), build_monitor_status()]:
            traffic = status["detail"]["traffic"]
            self.assertIn("capture_seq", traffic)
            self.assertIn("previous_peer", traffic)
            self.assertIn("next_peer", traffic)
            self.assertIn("recent", traffic)
            self.assertIn("hop_state", traffic["previous_peer"])
            self.assertIn("last_received", traffic["previous_peer"])
            self.assertIn("last_sent", traffic["previous_peer"])

    async def test_base_node_records_bounded_structured_payload(self) -> None:
        node = BaseNode("test-node", "127.0.0.1", 9991, "127.0.0.1", 9110)
        node.record_peer_message(
            "previous_peer",
            "last_received",
            {"msg_type": "EVENT", "event_id": "evt-1"},
            peer_node_id="upstream",
            peer_role="relay",
            hop_state="request_received",
            logical_id="evt-1",
            phase="upstream_event",
        )
        snapshot = node.traffic_snapshot()
        self.assertEqual(snapshot["capture_seq"], 1)
        self.assertEqual(snapshot["previous_peer"]["peer_node_id"], "upstream")
        self.assertEqual(snapshot["previous_peer"]["last_received"]["logical_id"], "evt-1")
        self.assertFalse(snapshot["previous_peer"]["last_received"]["truncated"])

    async def test_base_node_truncates_oversized_payload_preview(self) -> None:
        node = BaseNode("test-node", "127.0.0.1", 9991, "127.0.0.1", 9110)
        node.record_peer_message(
            "next_peer",
            "last_sent",
            {"payload": "x" * (TRAFFIC_PAYLOAD_PREVIEW_LIMIT + 50)},
            peer_node_id="downstream",
            peer_role="monitor",
            hop_state="request_sent",
            logical_id="evt-big",
            phase="downstream_event",
        )
        capture = node.traffic_snapshot()["next_peer"]["last_sent"]
        self.assertTrue(capture["truncated"])
        self.assertIsNone(capture["payload"])
        self.assertEqual(len(capture["preview"]), TRAFFIC_PAYLOAD_PREVIEW_LIMIT)

    async def test_reset_state_replaces_previous_snapshot_tree(self) -> None:
        node = BaseNode("test-node", "127.0.0.1", 9991, "127.0.0.1", 9110)
        node.record_peer_message(
            "next_peer",
            "last_sent",
            {"msg_type": "EVENT", "event_id": "evt-1"},
            peer_node_id="downstream",
            peer_role="relay",
            hop_state="request_sent",
            logical_id="evt-1",
            phase="downstream_event",
        )
        await node.reset_state()
        snapshot = node.traffic_snapshot()
        self.assertEqual(snapshot["capture_seq"], 0)
        self.assertEqual(snapshot["recent"], [])
        self.assertIsNone(snapshot["next_peer"]["last_sent"])

    async def test_control_path_does_not_overwrite_existing_data_plane_peers(self) -> None:
        from nw_sim.local_agent import LocalAgent

        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        before = agent.traffic_snapshot()["previous_peer"]["peer_node_id"]
        await agent.on_control({"command": "pause", "target": "local-agent"})
        after = agent.traffic_snapshot()["previous_peer"]["peer_node_id"]
        self.assertEqual(before, "host-simulator")
        self.assertEqual(after, "host-simulator")

    async def test_subclass_reset_keeps_peer_descriptors(self) -> None:
        from nw_sim.local_agent import LocalAgent

        agent = LocalAgent("127.0.0.1", 9102, "127.0.0.1", 9110, "127.0.0.1", 9101, "127.0.0.1", 9103)
        before = agent.traffic_snapshot()
        await agent.reset_state()
        after = agent.traffic_snapshot()
        self.assertEqual(before["previous_peer"]["peer_node_id"], "host-simulator")
        self.assertEqual(after["previous_peer"]["peer_node_id"], "host-simulator")
        self.assertEqual(after["next_peer"]["peer_node_id"], "r1")


if __name__ == "__main__":
    unittest.main()
