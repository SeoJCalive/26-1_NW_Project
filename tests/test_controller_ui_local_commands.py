from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from nw_sim import config
from nw_sim.controller_ui import ControllerUI
from nw_sim.messages import make_control


class ControllerUILocalCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_local_command_switches_focus_without_broadcast(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("focus r1")

        self.assertFalse(should_exit)
        self.assertEqual(controller.focus_node, "r1")
        self.assertIn("r1", message or "")
        self.assertTrue(any("r1" in entry for entry in controller.control_activity_log))
        controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_accepts_focus_whitespace_without_broadcast(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("  focus   r1  ")

        self.assertFalse(should_exit)
        self.assertEqual(controller.focus_node, "r1")
        self.assertIn("r1", message or "")
        controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_accepts_backup_relay_focus_without_broadcast(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("focus r1b")

        self.assertFalse(should_exit)
        self.assertEqual(controller.focus_node, "r1b")
        self.assertIn("r1b", message or "")
        controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_accepts_focus_aliases_without_broadcast(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, host_message = await controller.handle_local_command("focus host")

        self.assertFalse(should_exit)
        self.assertEqual(controller.focus_node, "host-simulator")
        self.assertIn("host-simulator", host_message or "")

        should_exit, local_message = await controller.handle_local_command("focus agent")

        self.assertFalse(should_exit)
        self.assertEqual(controller.focus_node, "local-agent")
        self.assertIn("local-agent", local_message or "")
        controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_returns_to_overview_without_broadcast(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="monitor",
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("overview")

        self.assertFalse(should_exit)
        self.assertIsNone(controller.focus_node)
        self.assertIn("overview", message or "")
        controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_accepts_focus_all_alias_without_broadcast(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            focus_node="local-agent",
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("focus all")

        self.assertFalse(should_exit)
        self.assertIsNone(controller.focus_node)
        self.assertIn("overview", message or "")
        controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_rejects_invalid_focus_forms_without_broadcast(self) -> None:
        for command in [
            "focus",
            "focus unknown-node",
            "focus host-simulation",
            "focus local",
            "overview extra",
            "focus all extra",
            "FOCUS r1",
        ]:
            with self.subTest(command=command):
                controller = ControllerUI(
                    control_host=config.DEFAULT_HOST,
                    control_port=config.CONTROLLER_PORT,
                    node_endpoints=config.NODE_ENDPOINTS,
                    focus_node="monitor",
                )
                controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

                should_exit, message = await controller.handle_local_command(command)

                self.assertFalse(should_exit)
                self.assertEqual(controller.focus_node, "monitor")
                self.assertIn("focus", message or "")
                self.assertTrue(controller.control_activity_log)
                controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_help_documents_focus_commands(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("help")

        self.assertFalse(should_exit)
        self.assertIn("focus <node>", message or "")
        self.assertIn("overview", message or "")
        controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_exit_stops_controller_without_broadcast(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("exit")

        self.assertTrue(should_exit)
        self.assertIsNone(message)
        self.assertTrue(controller._stop_requested)
        controller._broadcast_control.assert_not_awaited()

    async def test_handle_local_command_routes_kill_through_monitoring_surface(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            control_token="token-123",
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("kill monitor")

        self.assertFalse(should_exit)
        self.assertIsNone(message)
        controller._broadcast_control.assert_awaited_once()
        broadcast_call = controller._broadcast_control.await_args
        if broadcast_call is None:
            raise AssertionError("_broadcast_control was not awaited")
        outbound = broadcast_call.args[0]
        self.assertEqual(outbound["command"], "shutdown")
        self.assertEqual(outbound["target"], "monitor")
        self.assertEqual(outbound["control_token"], "token-123")

    async def test_handle_local_command_reports_parser_errors_without_broadcast(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        should_exit, message = await controller.handle_local_command("pause bogus")

        self.assertFalse(should_exit)
        self.assertIn("알 수 없는 node 대상", message or "")
        controller._broadcast_control.assert_not_awaited()

    async def test_remote_raw_control_request_is_forwarded_without_wrapper(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
            control_token="token-123",
        )
        controller._broadcast_control = AsyncMock()  # type: ignore[method-assign]

        message = make_control("shutdown", "monitor", control_token="token-123")
        await controller._apply_remote_request(message)

        controller._broadcast_control.assert_awaited_once_with(message)

    async def test_broadcast_logs_rejected_control_responses(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints={"monitor": config.NODE_ENDPOINTS["monitor"]},
            control_token="token-123",
        )

        async def rejected(*args, **kwargs):
            return {"ok": False, "reason": "invalid_token", "node_id": "monitor"}

        from unittest.mock import patch

        with patch("nw_sim.controller_ui.send_request", new=AsyncMock(side_effect=rejected)):
            await controller._broadcast_control(make_control("shutdown", "monitor"))

        self.assertTrue(any("제어 거부" in entry for entry in controller.control_activity_log))


if __name__ == "__main__":
    unittest.main()
