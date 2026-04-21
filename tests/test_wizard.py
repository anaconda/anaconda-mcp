from unittest import mock

import pytest
import readchar

from anaconda_mcp.wizard import multiselect_checkbox, setup_wizard_page, single_select

_CLIENTS = ["claude-desktop", "cursor", "vscode", "windsurf"]
_SUPPORTS = [False, True, True, False]


def _keypresses_ending_with_enter(*keys):
    return list(keys) + [readchar.key.ENTER]


class TestSetupWizardPage:
    def _run(self, keypresses, clients=None, supports=None, initial=None):
        clients = clients or _CLIENTS
        supports = supports or _SUPPORTS
        initial = initial or set()
        with mock.patch("anaconda_mcp.wizard.readchar.readkey", side_effect=keypresses):
            with mock.patch("anaconda_mcp.wizard.Live"):
                with mock.patch("anaconda_mcp.wizard.console"):
                    return setup_wizard_page(clients, supports, initial)

    def _cell(self, results, client, scope):
        for c, s, checked in results:
            if c == client and s == scope:
                return checked
        return None

    def test_enter_with_no_interaction_all_unchecked(self):
        result = self._run(_keypresses_ending_with_enter())
        assert all(not checked for _, _, checked in result)

    def test_g_toggles_global_on_current_row(self):
        result = self._run(_keypresses_ending_with_enter("g"))
        assert self._cell(result, "claude-desktop", "global") is True

    def test_g_toggle_off_prechecked_global(self):
        initial = {(0, 0)}
        result = self._run(_keypresses_ending_with_enter("g"), initial=initial)
        assert self._cell(result, "claude-desktop", "global") is False

    def test_p_toggles_project_on_current_row(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.DOWN, "p"))
        assert self._cell(result, "cursor", "project") is True
        assert self._cell(result, "cursor", "global") is False

    def test_p_silently_ignored_on_global_only_client(self):
        result = self._run(_keypresses_ending_with_enter("p", "p", "p"))
        assert self._cell(result, "claude-desktop", "global") is False
        assert "project" not in [s for c, s, _ in result if c == "claude-desktop"]

    def test_g_and_p_independent_on_same_row(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.DOWN, "g", "p"))
        assert self._cell(result, "cursor", "global") is True
        assert self._cell(result, "cursor", "project") is True

    def test_project_column_absent_for_global_only_client(self):
        result = self._run(_keypresses_ending_with_enter())
        scopes = [s for c, s, _ in result if c == "claude-desktop"]
        assert "project" not in scopes

    def test_project_column_present_for_project_capable_client(self):
        result = self._run(_keypresses_ending_with_enter())
        scopes = [s for c, s, _ in result if c == "cursor"]
        assert "global" in scopes
        assert "project" in scopes

    def test_down_moves_to_next_row(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.DOWN, "g"))
        assert self._cell(result, "cursor", "global") is True
        assert self._cell(result, "claude-desktop", "global") is False

    def test_up_at_top_stays(self):
        result = self._run(_keypresses_ending_with_enter(readchar.key.UP, "g"))
        assert self._cell(result, "claude-desktop", "global") is True

    def test_down_at_bottom_stays(self):
        n = len(_CLIENTS)
        downs = [readchar.key.DOWN] * (n + 5)
        result = self._run(_keypresses_ending_with_enter(*downs, "g"))
        assert self._cell(result, _CLIENTS[-1], "global") is True

    def test_j_k_vim_navigation(self):
        result = self._run(_keypresses_ending_with_enter("j", "j", "g"))
        assert self._cell(result, "vscode", "global") is True

    def test_initial_state_pre_populates(self):
        initial = {(1, 0), (1, 1)}
        result = self._run(_keypresses_ending_with_enter(), initial=initial)
        assert self._cell(result, "cursor", "global") is True
        assert self._cell(result, "cursor", "project") is True
        assert self._cell(result, "claude-desktop", "global") is False

    def test_multiple_clients_global_and_project(self):
        result = self._run(
            _keypresses_ending_with_enter(
                "g",
                readchar.key.DOWN,
                "g",
                "p",
            )
        )
        assert self._cell(result, "claude-desktop", "global") is True
        assert self._cell(result, "cursor", "global") is True
        assert self._cell(result, "cursor", "project") is True

    def test_q_raises_keyboard_interrupt(self):
        with pytest.raises(KeyboardInterrupt):
            self._run(["q"])

    def test_ctrl_c_raises_keyboard_interrupt(self):
        with pytest.raises(KeyboardInterrupt):
            self._run([readchar.key.CTRL_C])


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
