from __future__ import annotations

import unittest

from nw_sim.base import BaseNode, TRAFFIC_HISTORY_LIMIT, TRAFFIC_PAYLOAD_PREVIEW_LIMIT


class TrafficSnapshotBoundsTests(unittest.IsolatedAsyncioTestCase):
    async def test_recent_history_is_bounded(self) -> None:
        node = BaseNode("test-node", "127.0.0.1", 9992, "127.0.0.1", 9110)
        for index in range(TRAFFIC_HISTORY_LIMIT + 3):
            node.record_peer_message(
                "previous_peer",
                "last_received",
                {"msg_type": "EVENT", "event_id": f"evt-{index}"},
                peer_node_id="upstream",
                peer_role="relay",
                hop_state="request_received",
                logical_id=f"evt-{index}",
                phase="upstream_event",
            )
        snapshot = node.traffic_snapshot()
        self.assertEqual(len(snapshot["recent"]), TRAFFIC_HISTORY_LIMIT)
        self.assertEqual(snapshot["recent"][0]["capture"]["logical_id"], f"evt-{TRAFFIC_HISTORY_LIMIT + 2}")

    async def test_oversized_preview_is_capped(self) -> None:
        node = BaseNode("test-node", "127.0.0.1", 9992, "127.0.0.1", 9110)
        node.record_peer_message(
            "next_peer",
            "last_sent",
            {"blob": "y" * (TRAFFIC_PAYLOAD_PREVIEW_LIMIT + 200)},
            peer_node_id="downstream",
            peer_role="monitor",
            hop_state="request_sent",
            logical_id="evt-big",
            phase="downstream_event",
        )
        capture = node.traffic_snapshot()["next_peer"]["last_sent"]
        self.assertTrue(capture["truncated"])
        self.assertEqual(len(capture["preview"]), TRAFFIC_PAYLOAD_PREVIEW_LIMIT)


if __name__ == "__main__":
    unittest.main()
