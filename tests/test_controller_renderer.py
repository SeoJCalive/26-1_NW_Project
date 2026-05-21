from __future__ import annotations

import io
import os
import unittest
from unittest.mock import Mock, patch

from nw_demo import config
from nw_demo.controller_ui import ControllerUI, InPlaceRenderer, _display_cell_width, _fit_display_text


class SpyInPlaceRenderer(InPlaceRenderer):
    def __init__(self) -> None:
        super().__init__(io.StringIO())
        self.render_count = 0
        self.force_repaint_count = 0

    def render(self, lines: list[str]) -> None:
        self.render_count += 1

    def force_repaint(self) -> None:
        self.force_repaint_count += 1


class InPlaceRendererTests(unittest.TestCase):
    def test_fit_display_text_uses_korean_display_width(self) -> None:
        for width in (8, 12, 20):
            fitted = _fit_display_text("상태=실행 중", width)

            self.assertLessEqual(_display_cell_width(fitted), width)
            if width < _display_cell_width("상태=실행 중"):
                self.assertTrue(fitted.endswith("~"))

    def test_fit_display_text_truncates_mixed_korean_ascii_by_cells(self) -> None:
        fitted = _fit_display_text("CPU 급등 evt-host-1-7", 12)

        self.assertLessEqual(_display_cell_width(fitted), 12)
        self.assertTrue(fitted.endswith("~"))

    def test_fit_display_text_sanitizes_control_characters_to_single_line(self) -> None:
        fitted = _fit_display_text("red\nblue\rgreen\t\x1b[31m", 40)

        self.assertNotIn("\n", fitted)
        self.assertNotIn("\r", fitted)
        self.assertNotIn("\t", fitted)
        self.assertNotIn("\x1b", fitted)
        self.assertLessEqual(_display_cell_width(fitted), 40)

    def test_render_moves_cursor_to_prompt_row_after_frame(self) -> None:
        stream = io.StringIO()
        renderer = InPlaceRenderer(stream)

        with patch("nw_demo.controller_ui.shutil.get_terminal_size", return_value=os.terminal_size((80, 3))):
            renderer.render(["line 1", "line 2"])

        output = stream.getvalue()
        self.assertIn("\x1b[1;1H\x1b[2Kline 1", output)
        self.assertIn("\x1b[2;1H\x1b[2Kline 2", output)
        self.assertTrue(output.endswith("\x1b[3;1H\x1b[2K"))

    def test_render_keeps_prompt_row_below_shorter_followup_frame(self) -> None:
        stream = io.StringIO()
        renderer = InPlaceRenderer(stream)

        with patch("nw_demo.controller_ui.shutil.get_terminal_size", return_value=os.terminal_size((80, 3))):
            renderer.render(["line 1", "line 2"])
        stream.seek(0)
        stream.truncate(0)
        with patch("nw_demo.controller_ui.shutil.get_terminal_size", return_value=os.terminal_size((80, 2))):
            renderer.render(["updated line 1"])

        output = stream.getvalue()
        self.assertIn("updated line 1", output)
        self.assertTrue(output.endswith("\x1b[2;1H\x1b[2K"))
        self.assertNotIn("\x1b[2;1H\x1b[J", output)

    def test_render_reserves_bottom_row_for_prompt_when_frame_is_taller_than_terminal(self) -> None:
        stream = io.StringIO()
        renderer = InPlaceRenderer(stream)

        with patch("nw_demo.controller_ui.shutil.get_terminal_size", return_value=os.terminal_size((80, 4))):
            renderer.render(["line 1", "line 2", "line 3", "line 4", "line 5"])

        output = stream.getvalue()
        self.assertIn("\x1b[1;1H\x1b[2Kline 1", output)
        self.assertIn("\x1b[2;1H\x1b[2Kline 2", output)
        self.assertIn("\x1b[3;1H\x1b[2K... 2개 줄 생략됨", output)
        self.assertNotIn("\x1b[4;1H\x1b[2Kline", output)
        self.assertTrue(output.endswith("\x1b[4;1H\x1b[2K"))

    def test_force_repaint_clears_screen_and_invalidates_cached_lines(self) -> None:
        stream = io.StringIO()
        renderer = InPlaceRenderer(stream)

        with patch("nw_demo.controller_ui.shutil.get_terminal_size", return_value=os.terminal_size((80, 3))):
            renderer.render(["line 1", "line 2"])
        stream.seek(0)
        stream.truncate(0)

        renderer.force_repaint()
        with patch("nw_demo.controller_ui.shutil.get_terminal_size", return_value=os.terminal_size((80, 3))):
            renderer.render(["line 1", "line 2"])

        output = stream.getvalue()
        self.assertTrue(output.startswith("\x1b[H\x1b[J"))
        self.assertIn("\x1b[1;1H\x1b[2Kline 1", output)
        self.assertIn("\x1b[2;1H\x1b[2Kline 2", output)

    def test_render_prompt_rewrites_only_bottom_prompt_row(self) -> None:
        stream = io.StringIO()
        renderer = InPlaceRenderer(stream)

        with patch("nw_demo.controller_ui.shutil.get_terminal_size", return_value=os.terminal_size((80, 4))):
            renderer.render_prompt("overview")

        self.assertEqual(stream.getvalue(), "\x1b[4;1H\x1b[2Kviewer> overview\x1b[?25h")


class ControllerUIInteractiveLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_blank_enter_does_not_force_full_repaint_or_frame_render(self) -> None:
        controller = ControllerUI(
            control_host=config.DEFAULT_HOST,
            control_port=config.CONTROLLER_PORT,
            node_endpoints=config.NODE_ENDPOINTS,
        )
        renderer = SpyInPlaceRenderer()
        controller._renderer = renderer
        controller._read_in_place_line = Mock(side_effect=["", None])

        with patch("nw_demo.controller_ui.sys.stdin.isatty", return_value=True):
            await controller._interactive_command_loop(scripted_demo=False)

        self.assertEqual(renderer.force_repaint_count, 0)
        self.assertEqual(renderer.render_count, 0)
        self.assertFalse(controller.control_activity_log)


if __name__ == "__main__":
    unittest.main()
