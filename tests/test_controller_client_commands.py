from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from nw_demo.controller_client import build_requests, run_controller_client


class ControllerClientCommandTests(unittest.TestCase):
    def test_start_and_pause_accept_node_targets(self) -> None:
        requests, should_exit, message = build_requests("pause r1")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["target"], "r1")
        self.assertEqual(requests[0]["message"]["command"], "pause")

        requests, should_exit, message = build_requests("start host")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["target"], "host-simulator")
        self.assertEqual(requests[0]["message"]["command"], "start")

        requests, should_exit, message = build_requests("pause r1b")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["target"], "r1b")
        self.assertEqual(requests[0]["message"]["command"], "pause")

        requests, should_exit, message = build_requests("pause bogus")
        self.assertEqual(requests, [])
        self.assertFalse(should_exit)
        self.assertIn("알 수 없는 node 대상", message or "")

    def test_reset_supports_node_specific_and_global_forms(self) -> None:
        requests, should_exit, message = build_requests("reset r2")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["kind"], "control")
        self.assertEqual(requests[0]["message"]["target"], "r2")
        self.assertEqual(requests[0]["message"]["command"], "reset")

        requests, should_exit, message = build_requests("reset r2b")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["target"], "r2b")
        self.assertEqual(requests[0]["message"]["command"], "reset")

        requests, should_exit, message = build_requests("reset")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["kind"], "reset_all")

    def test_kill_requires_specific_node_target(self) -> None:
        requests, should_exit, message = build_requests("kill monitor")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["target"], "monitor")
        self.assertEqual(requests[0]["message"]["command"], "shutdown")

        requests, should_exit, message = build_requests("kill r2b")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["target"], "r2b")
        self.assertEqual(requests[0]["message"]["command"], "shutdown")

        requests, should_exit, message = build_requests("kill")
        self.assertEqual(requests, [])
        self.assertFalse(should_exit)
        self.assertIn("대상 node가 필요", message or "")

        requests, should_exit, message = build_requests("kill all")
        self.assertEqual(requests, [])
        self.assertFalse(should_exit)
        self.assertIn("kill 대상이 올바르지 않습니다", message or "")

    def test_invalid_numbers_and_parse_errors_return_user_messages(self) -> None:
        requests, should_exit, message = build_requests("fault cpu nope")
        self.assertEqual(requests, [])
        self.assertFalse(should_exit)
        self.assertIn("fault mode가 올바르지 않습니다", message or "")

        requests, should_exit, message = build_requests("delay r1 nope")
        self.assertEqual(requests, [])
        self.assertFalse(should_exit)
        self.assertIn("delay seconds가 올바르지 않습니다", message or "")

        requests, should_exit, message = build_requests('kill "unterminated')
        self.assertEqual(requests, [])
        self.assertFalse(should_exit)
        self.assertIn("명령 파싱 오류", message or "")

    def test_fault_commands_support_manual_on_off(self) -> None:
        requests, should_exit, message = build_requests("fault service on")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["command"], "set_fault")
        self.assertEqual(requests[0]["message"]["target"], "host-simulator")
        self.assertEqual(requests[0]["message"]["params"], {"fault_type": "SERVICE_DOWN", "enabled": True})

        requests, should_exit, message = build_requests("fault service off")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["command"], "set_fault")
        self.assertEqual(requests[0]["message"]["params"], {"fault_type": "SERVICE_DOWN", "enabled": False})

        requests, should_exit, message = build_requests("fault latency on")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["command"], "set_fault")
        self.assertEqual(requests[0]["message"]["target"], "host-simulator")
        self.assertEqual(requests[0]["message"]["params"], {"fault_type": "LATENCY_HIGH", "enabled": True})

        requests, should_exit, message = build_requests("fault latency off")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["command"], "set_fault")
        self.assertEqual(requests[0]["message"]["params"], {"fault_type": "LATENCY_HIGH", "enabled": False})

    def test_fault_commands_keep_duration_form_for_controller_clients(self) -> None:
        requests, should_exit, message = build_requests("fault cpu 6")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["command"], "inject_fault")
        self.assertEqual(requests[0]["message"]["params"], {"fault_type": "CPU_SPIKE", "duration_sec": 6})

        requests, should_exit, message = build_requests("fault latency 6")
        self.assertFalse(should_exit)
        self.assertIsNone(message)
        self.assertEqual(requests[0]["message"]["command"], "inject_fault")
        self.assertEqual(requests[0]["message"]["params"], {"fault_type": "LATENCY_HIGH", "duration_sec": 6})

    def test_focus_commands_are_not_serialized_as_node_control_requests(self) -> None:
        for line in ["focus r1", "overview", "focus all"]:
            with self.subTest(line=line):
                requests, should_exit, message = build_requests(line)

                self.assertEqual(requests, [])
                self.assertFalse(should_exit)
                self.assertIn("알 수 없는 명령어", message or "")

    def test_exit_alias_requests_controller_shutdown(self) -> None:
        for line in ["quit", "exit"]:
            with self.subTest(line=line):
                requests, should_exit, message = build_requests(line)

                self.assertTrue(should_exit)
                self.assertIsNone(message)
                self.assertEqual(requests[0]["kind"], "shutdown")
                self.assertIn(line, requests[0]["display"])


class ControllerClientRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_sends_raw_control_message_with_token(self) -> None:
        with patch("builtins.input", side_effect=["kill monitor", EOFError]):
            with patch("nw_demo.controller_client.send_request", new=AsyncMock()) as send_request:
                await run_controller_client("127.0.0.1", 9110, "token-123")

        send_call = send_request.await_args
        if send_call is None:
            raise AssertionError("send_request was not awaited")
        outbound = send_call.args[2]
        self.assertEqual(outbound["msg_type"], "CONTROL")
        self.assertEqual(outbound["command"], "shutdown")
        self.assertEqual(outbound["target"], "monitor")
        self.assertEqual(outbound["control_token"], "token-123")

    async def test_runtime_sends_controller_shutdown_for_exit(self) -> None:
        with patch("builtins.input", side_effect=["exit"]):
            with patch("nw_demo.controller_client.send_request", new=AsyncMock()) as send_request:
                await run_controller_client("127.0.0.1", 9110, "token-123")

        send_call = send_request.await_args
        if send_call is None:
            raise AssertionError("send_request was not awaited")
        outbound = send_call.args[2]
        self.assertEqual(outbound["kind"], "shutdown")
        self.assertEqual(outbound["control_token"], "token-123")


if __name__ == "__main__":
    unittest.main()
