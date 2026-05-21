from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import AsyncMock, patch

from nw_demo.system import LocalProcessSupervisor


class SupervisorTokenPropagationTests(unittest.IsolatedAsyncioTestCase):
    async def test_supervisor_passes_control_token_via_env_not_argv(self) -> None:
        recorded_calls: list[tuple[tuple[object, ...], dict[str, Any]]] = []

        class FakeProcess:
            def __init__(self) -> None:
                self.returncode = 0

            def terminate(self) -> None:
                return None

            async def wait(self) -> int:
                return 0

        async def fake_create_subprocess_exec(*args, **kwargs):
            recorded_calls.append((args, kwargs))
            return FakeProcess()

        supervisor = LocalProcessSupervisor("127.0.0.1", 9110, "secret-token")

        with patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=fake_create_subprocess_exec)):
            with patch("asyncio.sleep", new=AsyncMock()):
                await supervisor.start()

        self.assertTrue(recorded_calls)
        first_args, first_kwargs = recorded_calls[0]
        self.assertEqual(first_args[0:3], ("bash", "-lc", first_args[2]))
        self.assertNotIn("--control-token", str(first_args[2]))
        self.assertEqual(first_kwargs["env"]["NW_CONTROL_TOKEN"], "secret-token")


if __name__ == "__main__":
    unittest.main()
