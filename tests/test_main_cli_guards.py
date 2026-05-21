from __future__ import annotations

import subprocess
import sys
import unittest


class MainCliGuardTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "main.py", *args],
            cwd="/home/tjwocjf0915/workspace/NW_project",
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_external_controller_requires_token(self) -> None:
        result = self._run("--controller", "--host", "127.0.0.1", "--port", "9110")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("외부 controller는 control token이 필요합니다", result.stderr)

    def test_standalone_role_requires_token_unless_opted_out(self) -> None:
        result = self._run("--role", "host")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Standalone role 'host-simulator'는 control token이 필요합니다", result.stderr)

    def test_focus_node_is_rejected_for_external_controller_mode(self) -> None:
        result = self._run("--controller", "--focus-node", "r1", "--control-token", "demo123")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--focus-node는 standalone controller UI(--role controller)에서만 사용할 수 있습니다.", result.stderr)

    def test_focus_node_is_rejected_for_non_controller_role(self) -> None:
        result = self._run("--role", "host", "--focus-node", "r1", "--control-token", "demo123")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--focus-node는 standalone controller UI(--role controller)에서만 사용할 수 있습니다.", result.stderr)


if __name__ == "__main__":
    unittest.main()
