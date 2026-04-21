from unittest import mock

import pytest
import readchar

from anaconda_mcp.wizard import multiselect_checkbox, single_select


def _keypresses_ending_with_enter(*keys):
    return list(keys) + [readchar.key.ENTER]


class TestMultiselectCheckbox:
    def _run(self, keypresses, choices, checked=()):
        with mock.patch("anaconda_mcp.wizard.readchar.readkey", side_effect=keypresses):
            with mock.patch("anaconda_mcp.wizard.Live"):
                with mock.patch("anaconda_mcp.wizard.console"):
                    return multiselect_checkbox("Pick", choices, checked=checked)

    def test_enter_with_nothing_checked_returns_empty(self):
        result = self._run(_keypresses_ending_with_enter(), ["cursor", "vscode"])
        assert result == []

    def test_space_toggles_item_on(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.SPACE), ["cursor", "vscode"])
        assert result == ["cursor"]

    def test_space_twice_toggles_item_off(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.SPACE, readchar.key.SPACE), ["cursor", "vscode"])
        assert result == []

    def test_down_then_space_selects_second_item(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.DOWN, readchar.key.SPACE), ["cursor", "vscode"])
        assert result == ["vscode"]

    def test_j_moves_down(self):
        result = self._run(_keypresses_ending_with_enter("j", readchar.key.SPACE), ["cursor", "vscode"])
        assert result == ["vscode"]

    def test_k_moves_up(self):
        result = self._run(
            _keypresses_ending_with_enter(readchar.key.DOWN, "k", readchar.key.SPACE),
            ["cursor", "vscode"],
        )
        assert result == ["cursor"]

    def test_up_at_top_stays_at_zero(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.UP, readchar.key.SPACE), ["cursor", "vscode"])
        assert result == ["cursor"]

    def test_down_at_bottom_stays_at_last(self):
        result = self._run(
            _keypresses_ending_with_enter(readchar.key.DOWN, readchar.key.DOWN, readchar.key.SPACE),
            ["cursor", "vscode"],
        )
        assert result == ["vscode"]

    def test_prechecked_items_returned_without_interaction(self):
        result = self._run(
            _keypresses_ending_with_enter(), ["cursor", "vscode", "windsurf"], checked=["cursor", "windsurf"]
        )
        assert result == ["cursor", "windsurf"]

    def test_prechecked_item_can_be_unchecked(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.SPACE), ["cursor", "vscode"], checked=["cursor"])
        assert result == []

    def test_select_multiple_items(self):
        result = self._run(
            _keypresses_ending_with_enter(
                readchar.key.SPACE,
                readchar.key.DOWN,
                readchar.key.SPACE,
                readchar.key.DOWN,
                readchar.key.SPACE,
            ),
            ["cursor", "vscode", "windsurf"],
        )
        assert result == ["cursor", "vscode", "windsurf"]

    def test_esc_no_longer_triggers_abort(self):
        with pytest.raises(StopIteration):
            self._run([readchar.key.ESC], ["cursor", "vscode"])

    def test_q_raises_keyboard_interrupt(self):
        with pytest.raises(KeyboardInterrupt):
            self._run(["q"], ["cursor", "vscode"])

    def test_ctrl_c_raises_keyboard_interrupt(self):
        with pytest.raises(KeyboardInterrupt):
            self._run([readchar.key.CTRL_C], ["cursor", "vscode"])

    def test_result_order_matches_choices_order(self):
        result = self._run(
            _keypresses_ending_with_enter(readchar.key.DOWN, readchar.key.SPACE, readchar.key.UP, readchar.key.SPACE),
            ["alpha", "beta", "gamma"],
        )
        assert result == ["alpha", "beta"]

    def test_single_choice_list(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.SPACE), ["only"])
        assert result == ["only"]


class TestSingleSelect:
    def _run(self, keypresses, choices, default=None):
        with mock.patch("anaconda_mcp.wizard.readchar.readkey", side_effect=keypresses):
            with mock.patch("anaconda_mcp.wizard.Live"):
                with mock.patch("anaconda_mcp.wizard.console"):
                    return single_select("Pick", choices, default=default)

    def test_enter_selects_first_item_by_default(self):
        result = self._run(_keypresses_ending_with_enter(), ["stdio", "streamable-http"])
        assert result == "stdio"

    def test_down_then_enter_selects_second(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.DOWN), ["stdio", "streamable-http"])
        assert result == "streamable-http"

    def test_default_positions_cursor(self):
        result = self._run(_keypresses_ending_with_enter(), ["global", "project", "both"], default="project")
        assert result == "project"

    def test_j_moves_down(self):
        result = self._run(_keypresses_ending_with_enter("j"), ["global", "project"])
        assert result == "project"

    def test_k_moves_up(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.DOWN, "k"), ["global", "project"])
        assert result == "global"

    def test_up_at_top_stays(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.UP), ["global", "project"])
        assert result == "global"

    def test_down_at_bottom_stays(self):
        result = self._run(
            _keypresses_ending_with_enter(readchar.key.DOWN, readchar.key.DOWN, readchar.key.DOWN),
            ["global", "project"],
        )
        assert result == "project"

    def test_esc_no_longer_triggers_abort(self):
        with pytest.raises(StopIteration):
            self._run([readchar.key.ESC], ["global", "project"])

    def test_q_raises_keyboard_interrupt(self):
        with pytest.raises(KeyboardInterrupt):
            self._run(["q"], ["global", "project"])

    def test_ctrl_c_raises_keyboard_interrupt(self):
        with pytest.raises(KeyboardInterrupt):
            self._run([readchar.key.CTRL_C], ["global", "project"])
