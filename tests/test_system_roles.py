from __future__ import annotations

import unittest

from nw_demo import config
from nw_demo.relay import RelayNode
from nw_demo.system import ROLE_START_ORDER, build_role


class SystemRoleRegistryTests(unittest.TestCase):
    def test_backup_relay_nodes_are_registered_with_ports_and_roles(self) -> None:
        self.assertEqual(config.NODE_ENDPOINTS["r1b"], (config.DEFAULT_HOST, config.RELAY_R1B_PORT))
        self.assertEqual(config.NODE_ENDPOINTS["r2b"], (config.DEFAULT_HOST, config.RELAY_R2B_PORT))
        self.assertEqual(config.ROLE_TO_NODE_ID["relay-r1b"], "r1b")
        self.assertEqual(config.ROLE_TO_NODE_ID["relay-r2b"], "r2b")
        self.assertIn("r1b", config.NODE_ORDER)
        self.assertIn("r2b", config.NODE_ORDER)

    def test_backup_relay_roles_build_as_relay_nodes(self) -> None:
        r1b = build_role("relay-r1b", "127.0.0.1", 9106, "127.0.0.1", 9110, None)
        r2b = build_role("relay-r2b", "127.0.0.1", 9107, "127.0.0.1", 9110, None)

        if not isinstance(r1b, RelayNode):
            self.fail("relay-r1b did not build as RelayNode")
        if not isinstance(r2b, RelayNode):
            self.fail("relay-r2b did not build as RelayNode")
        self.assertEqual(r1b.node_id, "r1b")
        self.assertEqual(r2b.node_id, "r2b")
        self.assertEqual(r1b._downstream_target_label(), "r2b")
        self.assertEqual(r2b._downstream_target_label(), "monitor")

    def test_supervisor_starts_backup_relays_before_agent(self) -> None:
        self.assertIn("relay-r1b", ROLE_START_ORDER)
        self.assertIn("relay-r2b", ROLE_START_ORDER)
        self.assertLess(ROLE_START_ORDER.index("relay-r2b"), ROLE_START_ORDER.index("relay-r1b"))
        self.assertLess(ROLE_START_ORDER.index("relay-r1b"), ROLE_START_ORDER.index("agent"))


if __name__ == "__main__":
    unittest.main()
