"""Tests for scripts/dev_workflow.py — internal tooling, not shipped in the conda package."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# scripts/ is not a package so we add it to sys.path for import.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from dev_workflow import (
    PR_DESCRIPTION_FILE,
    SESAME_DEFAULT_PATH,
    TASK_CONTEXT_FILE,
    _extract_ticket_id,
    _find_sesame,
    _get_current_branch,
    _get_claude_desktop_config_path,
    _load_json,
    _save_json,
    _sesame_mcp_entry,
    cmd_setup,
    cmd_task,
    cmd_pr,
)


# ---------------------------------------------------------------------------
# _extract_ticket_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("feature/PROJ-123-add-cart", "PROJ-123"),
        ("PROJ-123: fix login", "PROJ-123"),
        ("no ticket here", None),
        ("ABC-99 and DEF-1", "ABC-99"),  # first match wins
        ("", None),
        ("lower-case-abc-1", None),      # must be uppercase
    ],
)
def test_extract_ticket_id(text, expected):
    assert _extract_ticket_id(text) == expected


# ---------------------------------------------------------------------------
# _find_sesame
# ---------------------------------------------------------------------------


def test_find_sesame_uses_provided_path(tmp_path):
    fake = tmp_path / "sesame"
    fake.touch()
    assert _find_sesame(fake) == fake


def test_find_sesame_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="Sesame binary not found"):
        _find_sesame(tmp_path / "no-sesame")


def test_find_sesame_falls_back_to_default(tmp_path, monkeypatch):
    fake_default = tmp_path / "sesame"
    fake_default.touch()
    monkeypatch.setattr("dev_workflow.SESAME_DEFAULT_PATH", fake_default)
    assert _find_sesame(None) == fake_default


# ---------------------------------------------------------------------------
# _get_current_branch
# ---------------------------------------------------------------------------


def test_get_current_branch_returns_name():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="feature/PROJ-123-test\n", returncode=0)
        assert _get_current_branch() == "feature/PROJ-123-test"


def test_get_current_branch_returns_empty_on_error():
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
        assert _get_current_branch() == ""


# ---------------------------------------------------------------------------
# _load_json / _save_json
# ---------------------------------------------------------------------------


def test_load_json_returns_empty_for_missing_file(tmp_path):
    assert _load_json(tmp_path / "missing.json") == {}


def test_load_json_returns_empty_for_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    assert _load_json(bad) == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    data = {"mcpServers": {"sesame": {"command": "/usr/bin/sesame"}}}
    _save_json(path, data)
    assert _load_json(path) == data


def test_save_json_creates_parent_dirs(tmp_path):
    nested = tmp_path / "a" / "b" / "config.json"
    _save_json(nested, {"key": "value"})
    assert nested.exists()


# ---------------------------------------------------------------------------
# _sesame_mcp_entry
# ---------------------------------------------------------------------------


def test_sesame_mcp_entry_contains_binary_path(tmp_path):
    binary = tmp_path / "sesame"
    binary.touch()
    entry = _sesame_mcp_entry(binary)
    assert entry["command"] == str(binary)
    assert "args" in entry


# ---------------------------------------------------------------------------
# cmd_setup
# ---------------------------------------------------------------------------


def test_cmd_setup_registers_sesame_in_claude_desktop(tmp_path, monkeypatch):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    config_path = tmp_path / "claude_desktop_config.json"

    monkeypatch.setattr("dev_workflow._get_claude_desktop_config_path", lambda: config_path)

    cmd_setup(sesame_path=fake_sesame, target="claude-desktop")

    config = _load_json(config_path)
    assert "sesame" in config["mcpServers"]
    assert config["mcpServers"]["sesame"]["command"] == str(fake_sesame)


def test_cmd_setup_registers_sesame_in_claude_code(tmp_path, monkeypatch):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    config_path = tmp_path / ".claude.json"

    monkeypatch.setattr("dev_workflow._CLAUDE_CODE_CONFIG_PATH", config_path)

    cmd_setup(sesame_path=fake_sesame, target="claude-code")

    config = _load_json(config_path)
    assert "sesame" in config["mcpServers"]


def test_cmd_setup_skips_if_already_registered(tmp_path, monkeypatch, capsys):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    config_path = tmp_path / "claude_desktop_config.json"
    existing = {"mcpServers": {"sesame": {"command": "/old/path"}}}
    _save_json(config_path, existing)

    monkeypatch.setattr("dev_workflow._get_claude_desktop_config_path", lambda: config_path)

    cmd_setup(sesame_path=fake_sesame, target="claude-desktop")

    # Should not overwrite existing entry
    config = _load_json(config_path)
    assert config["mcpServers"]["sesame"]["command"] == "/old/path"
    captured = capsys.readouterr()
    assert "already registered" in captured.out


def test_cmd_setup_registers_both_targets(tmp_path, monkeypatch):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    desktop_config = tmp_path / "claude_desktop_config.json"
    code_config = tmp_path / ".claude.json"

    monkeypatch.setattr("dev_workflow._get_claude_desktop_config_path", lambda: desktop_config)
    monkeypatch.setattr("dev_workflow._CLAUDE_CODE_CONFIG_PATH", code_config)

    cmd_setup(sesame_path=fake_sesame, target="all")

    assert "sesame" in _load_json(desktop_config)["mcpServers"]
    assert "sesame" in _load_json(code_config)["mcpServers"]


# ---------------------------------------------------------------------------
# cmd_task
# ---------------------------------------------------------------------------


def test_cmd_task_creates_branch_and_stub(tmp_path, monkeypatch, capsys):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        cmd_task(ticket_id="PROJ-123", sesame_path=fake_sesame, no_branch=False)

    # Branch creation was attempted
    branch_call = mock_run.call_args_list[0][0][0]
    assert "git" in branch_call
    assert "checkout" in branch_call

    # Stub file created
    assert (tmp_path / ".task-context.md").exists()

    # Prompt printed
    captured = capsys.readouterr()
    assert "PROJ-123" in captured.out
    assert "Paste" in captured.out


def test_cmd_task_no_branch_skips_git(tmp_path, monkeypatch):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)

    with patch("subprocess.run") as mock_run:
        cmd_task(ticket_id="PROJ-123", sesame_path=fake_sesame, no_branch=True)

    mock_run.assert_not_called()


def test_cmd_task_exits_with_message_on_dirty_working_tree(tmp_path, monkeypatch, capsys):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)

    dirty_status = "M  scripts/dev_workflow.py\nM  tests/test_dev_workflow.py\n"

    with (
        patch("subprocess.run") as mock_run,
        pytest.raises(SystemExit) as exc_info,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout=dirty_status, stderr="")
        cmd_task(ticket_id="PROJ-123", sesame_path=fake_sesame, no_branch=False)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "uncommitted changes" in captured.err
    assert "scripts/dev_workflow.py" in captured.err
    assert "git stash" in captured.err
    assert "--no-branch" in captured.err


def test_cmd_task_switches_to_existing_branch(tmp_path, monkeypatch, capsys):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)

    # First call returns 128 (branch exists), second call (checkout) returns 0
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=128, stdout="", stderr="branch already exists"),
            MagicMock(returncode=0),
        ]
        cmd_task(ticket_id="PROJ-123", sesame_path=fake_sesame, no_branch=False)

    captured = capsys.readouterr()
    assert "already exists" in captured.out
    assert "feature/proj-123" in captured.out

    # Second call should be `git checkout <branch>` (no -b)
    second_call_args = mock_run.call_args_list[1][0][0]
    assert "-b" not in second_call_args


def test_cmd_task_does_not_overwrite_existing_context(tmp_path, monkeypatch):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)
    existing = "## What to build\nAlready filled in.\n"
    (tmp_path / ".task-context.md").write_text(existing)

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        cmd_task(ticket_id="PROJ-123", sesame_path=fake_sesame, no_branch=False)

    # Should not overwrite
    assert (tmp_path / ".task-context.md").read_text() == existing


def test_cmd_task_prompt_contains_ticket_id(tmp_path, monkeypatch, capsys):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        cmd_task(ticket_id="MYTEAM-99", sesame_path=fake_sesame, no_branch=False)

    assert "MYTEAM-99" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cmd_pr
# ---------------------------------------------------------------------------


def test_cmd_pr_exits_when_not_on_branch(tmp_path, monkeypatch):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)

    with (
        patch("dev_workflow._get_current_branch", return_value=""),
        pytest.raises(SystemExit) as exc_info,
    ):
        cmd_pr(sesame_path=fake_sesame, draft=True, title=None)

    assert exc_info.value.code == 1


def test_cmd_pr_prints_prompt_with_ticket_id(tmp_path, monkeypatch, capsys):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)

    with (
        patch("dev_workflow._get_current_branch", return_value="feature/PROJ-456-checkout"),
        patch("builtins.input", side_effect=KeyboardInterrupt),
        pytest.raises(SystemExit),
    ):
        cmd_pr(sesame_path=fake_sesame, draft=True, title=None)

    captured = capsys.readouterr()
    assert "PROJ-456" in captured.out
    assert "Paste" in captured.out


def test_cmd_pr_includes_task_context_in_prompt(tmp_path, monkeypatch, capsys):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".task-context.md").write_text("## What to build\nSpecial context.\n")

    with (
        patch("dev_workflow._get_current_branch", return_value="feature/PROJ-123-with-context"),
        patch("builtins.input", side_effect=KeyboardInterrupt),
        pytest.raises(SystemExit),
    ):
        cmd_pr(sesame_path=fake_sesame, draft=True, title=None)

    assert "Special context" in capsys.readouterr().out


def test_cmd_pr_saves_description_and_calls_gh(tmp_path, monkeypatch):
    fake_sesame = tmp_path / "sesame"
    fake_sesame.touch()
    monkeypatch.chdir(tmp_path)

    pr_body_lines = iter(["## Summary", "Adds checkout flow.", ""])

    with (
        patch("dev_workflow._get_current_branch", return_value="feature/PROJ-456-checkout"),
        patch("builtins.input", side_effect=[*["## Summary", "Adds checkout flow."], EOFError()]),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        cmd_pr(sesame_path=fake_sesame, draft=True, title=None)

    assert (tmp_path / ".pr-description.md").exists()
    gh_args = mock_run.call_args[0][0]
    assert "gh" in gh_args
    assert "--draft" in gh_args
