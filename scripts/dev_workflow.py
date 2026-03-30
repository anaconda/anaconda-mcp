"""
dev_workflow.py — Internal Anaconda engineering tooling. NOT shipped in the conda package.

Architecture
------------
It requires Sesame (https://github.com/Anaconda-Sandbox/sesame) registered
as an MCP server in those clients, so Claude already has access to Jira, Confluence,
Slack, and GitHub when the developer opens a conversation.

This script provides two things:
  1. `setup`  — registers Sesame into Claude Desktop and/or Claude Code config once,
                 so engineers don't have to configure it manually.
  2. `task`   — generates a ready-to-paste prompt the developer runs in Claude Desktop
                 or Claude Code to get task context for a Jira ticket. Also creates
                 the git branch and a .task-context.md stub they fill in from Claude's
                 response.
  3. `pr`     — generates a ready-to-paste prompt the developer runs in Claude Desktop
                 or Claude Code to produce a PR description. Reads .task-context.md if
                 present and opens the PR via `gh pr create` once the developer pastes
                 the output back.

Usage (via Makefile)
--------------------
  make workflow-setup          # one-time: register Sesame in Claude Desktop + Claude Code
  make task-start TICKET=PROJ-123    # generate task context prompt + create branch
  make pr                      # generate PR description prompt + open draft PR

Usage (directly)
----------------
  python scripts/dev_workflow.py setup
  python scripts/dev_workflow.py task PROJ-123
  python scripts/dev_workflow.py pr [--title "..."] [--no-draft]

Requirements
------------
  - Sesame installed: https://github.com/Anaconda-Sandbox/sesame
  - Claude Desktop (business subscription) OR Claude Code authenticated
  - gh CLI authenticated (for `pr` subcommand)
  - NO Anthropic API key required
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SESAME_DEFAULT_PATH = Path.home() / ".local/share/sesame/venv/bin/sesame"
TASK_CONTEXT_FILE = Path(".task-context.md")
TASK_PROMPT_FILE = Path(".task-prompt.md")
PR_DESCRIPTION_FILE = Path(".pr-description.md")
PR_PROMPT_FILE = Path(".pr-prompt.md")

# Claude Desktop config paths per OS
_CLAUDE_DESKTOP_CONFIG_PATHS = {
    "darwin": Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    "linux": Path.home() / ".config" / "Claude" / "claude_desktop_config.json",
    "win32": Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json",
}

# Claude Code MCP config (global, all platforms)
_CLAUDE_CODE_CONFIG_PATH = Path.home() / ".claude.json"

# ---------------------------------------------------------------------------
# Prompt templates
# The developer pastes these into their Claude Desktop / Claude Code session.
# Claude already has Sesame as an MCP tool, so it can call jira_get_issue etc.
# ---------------------------------------------------------------------------

_TASK_CONTEXT_PROMPT = """\
Please read the file at {prompt_path} for full instructions, then carry them out.
"""

_TASK_CONTEXT_INSTRUCTIONS = """\
# Task setup instructions for {ticket_id}

You have access to Sesame tools (Jira, Confluence, Slack, GitHub) and the
Filesystem connector. Follow these steps exactly:

## Step 1 — Gather context using Sesame
1. Call jira_get_issue("{ticket_id}") — get the full ticket with description and ACs
2. Call confluence_search with the ticket summary to find related design docs, ADRs, business rules
3. Call slack_search("{ticket_id}") to find team decisions or caveats about this work
4. Call github_search_issues with the ticket summary to find related past PRs

## Step 2 — Write the output file
Using your Filesystem write tool, write the gathered context to:
  {context_path}

Use exactly this structure:

## What to build
(2-3 sentences summarising the goal)

## Acceptance criteria
- [ ] each criterion from the ticket

## Business rules in scope
(rules found in Confluence or Jira — reference source by name)

## Related past PRs / decisions
(from GitHub and Slack — title and key insight only)

## Files likely touched
(your best guess from the context found)

## Edge cases to watch
(3-5 specific things to consider before writing code)

Write only the markdown to the file. Confirm when done.
"""

_PR_DESCRIPTION_PROMPT = """\
Please read the file at {prompt_path} for full instructions, then carry them out.
"""

_PR_DESCRIPTION_INSTRUCTIONS = """\
# PR description instructions for branch: {branch}

You have access to Sesame tools (Jira, Confluence, Slack, GitHub) and the
Filesystem connector. Follow these steps exactly:

## Step 1 — Read existing task context
Read the file at {context_path} for context already gathered.
If the file is empty or missing, proceed without it.

## Step 2 — Gather any missing context using Sesame
1. If ticket details are missing, call jira_get_issue("{ticket_id}")
2. Call slack_search("{ticket_id}") for any last-minute decisions or caveats
3. Call github_get_file_content for BUSINESS_RULES.md or CLAUDE.md in this repo if they exist

## Step 3 — Write the PR description
Using your Filesystem write tool, write the PR description to:
  {pr_path}

Use exactly this structure:

## Summary
(2-3 sentences: what changed and why)

## Acceptance criteria
- [ ] each item (map directly to Jira ACs)

## Business rules verified
(which rules from BUSINESS_RULES.md / Confluence this PR satisfies)

## Testing notes
(what was tested, how to verify locally)

## AI reviewer instruction
(one paragraph for @coderabbit/@claude naming specific business rules,
ACs, and edge cases to validate — referencing sources by name)

Write only the markdown to the file. Confirm when done.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_sesame(sesame_path: Path | None) -> Path:
    """Resolve the Sesame binary, raising a clear error if not found."""
    candidate = sesame_path or SESAME_DEFAULT_PATH
    if not candidate.exists():
        raise FileNotFoundError(
            f"Sesame binary not found at {candidate}.\n"
            "Install Sesame: https://github.com/Anaconda-Sandbox/sesame\n"
            "Or pass --sesame-path /path/to/sesame"
        )
    return candidate


def _get_current_branch() -> str:
    """Return the current git branch name, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def _extract_ticket_id(text: str) -> str | None:
    """Extract the first Jira-style ticket ID (e.g. PROJ-123) from a string."""
    match = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", text or "")
    return match.group(1) if match else None


def _get_uncommitted_files() -> list[str]:
    """Return a list of uncommitted files in the working tree."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def _create_branch(ticket_id: str, summary: str = "") -> tuple[str, bool]:
    """Create and checkout a git branch named after the ticket.

    If the branch already exists, switches to it instead of failing.
    Exits with a clear message if there are uncommitted changes that
    would be overwritten — never touches the working tree silently.
    Returns (branch_name, created) where created=False means it already existed.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower())[:40].strip("-")
    branch = f"feature/{ticket_id.lower()}-{slug}" if slug else f"feature/{ticket_id.lower()}"

    # Check for uncommitted changes before attempting any checkout
    dirty_files = _get_uncommitted_files()
    if dirty_files:
        files_list = "\n".join(f"    {f}" for f in dirty_files)
        print(
            f"\n❌  Cannot switch to '{branch}' — you have uncommitted changes:\n"
            f"{files_list}\n\n"
            "    To move forward, choose one of:\n"
            "      git add . && git commit -m 'wip: <description>'   # commit your work\n"
            "      git stash                                          # stash temporarily\n"
            "      make task-start TICKET=... --no-branch            # skip branch switching\n",
            file=sys.stderr,
        )
        sys.exit(1)

    result = subprocess.run(
        ["git", "checkout", "-b", branch],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return branch, True

    # Branch already exists — switch to it
    subprocess.run(["git", "checkout", branch], check=True)
    return branch, False


def _print_prompt_box(label: str, prompt: str) -> None:
    """Print a prompt in a clearly delimited box for easy copy-paste."""
    width = 70
    print(f"\n{'─' * width}")
    print(f"  📋  {label}")
    print(f"{'─' * width}")
    print(prompt.strip())
    print(f"{'─' * width}\n")


# ---------------------------------------------------------------------------
# Claude Desktop config helpers (reuse logic from anaconda_mcp.claude_desktop
# but kept self-contained so scripts/ has no import dependency on src/)
# ---------------------------------------------------------------------------


def _get_claude_desktop_config_path() -> Path | None:
    platform = sys.platform
    return _CLAUDE_DESKTOP_CONFIG_PATHS.get(platform)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _sesame_mcp_entry(sesame_binary: Path) -> dict:
    return {"command": str(sesame_binary), "args": []}


# ---------------------------------------------------------------------------
# Command: setup
# ---------------------------------------------------------------------------


def cmd_setup(sesame_path: Path | None, target: str) -> None:
    """
    Register Sesame as an MCP server in Claude Desktop and/or Claude Code.
    Engineers run this once after cloning the repo.
    """
    sesame_binary = _find_sesame(sesame_path)
    entry = _sesame_mcp_entry(sesame_binary)
    registered = []

    # --- Claude Desktop ---
    if target in ("all", "claude-desktop"):
        config_path = _get_claude_desktop_config_path()
        if config_path is None:
            print(f"⚠️  Claude Desktop: unsupported platform ({sys.platform}), skipping.")
        else:
            config = _load_json(config_path)
            config.setdefault("mcpServers", {})
            if "sesame" in config["mcpServers"]:
                print(f"✅  Claude Desktop: sesame already registered at {config_path}")
            else:
                config["mcpServers"]["sesame"] = entry
                _save_json(config_path, config)
                print(f"✅  Claude Desktop: sesame registered at {config_path}")
                print("    ⚠️  Restart Claude Desktop to apply the change.")
            registered.append("Claude Desktop")

    # --- Claude Code ---
    if target in ("all", "claude-code"):
        config_path = _CLAUDE_CODE_CONFIG_PATH
        config = _load_json(config_path)
        config.setdefault("mcpServers", {})
        if "sesame" in config["mcpServers"]:
            print(f"✅  Claude Code: sesame already registered at {config_path}")
        else:
            config["mcpServers"]["sesame"] = entry
            _save_json(config_path, config)
            print(f"✅  Claude Code: sesame registered at {config_path}")
        registered.append("Claude Code")

    if registered:
        print(f"\n💡  Sesame is now available as an MCP tool in: {', '.join(registered)}")
        print("    No API key needed — your Business subscription handles everything.")


# ---------------------------------------------------------------------------
# Command: task
# ---------------------------------------------------------------------------


def cmd_task(ticket_id: str, sesame_path: Path | None, no_branch: bool) -> None:
    """
    Create a git branch, write a .task-prompt.md with full instructions, and print
    a short one-liner for the developer to paste into Claude Desktop / Claude Code.
    Claude reads the prompt file, calls Sesame, and writes .task-context.md directly
    via the Filesystem connector — no copy-pasting of content required.
    """
    _find_sesame(sesame_path)  # validate early — fail fast if Sesame missing

    # Create branch
    if not no_branch:
        branch, created = _create_branch(ticket_id)
        if created:
            print(f"✅  Branch created: {branch}")
        else:
            print(f"✅  Branch already exists, switched to: {branch}")

    # Write full instructions to .task-prompt.md
    cwd = Path.cwd()
    instructions = _TASK_CONTEXT_INSTRUCTIONS.format(
        ticket_id=ticket_id,
        context_path=str(cwd / TASK_CONTEXT_FILE),
    )
    TASK_PROMPT_FILE.write_text(instructions, encoding="utf-8")

    # Print a short one-liner pointing Claude to the instructions file
    prompt = _TASK_CONTEXT_PROMPT.format(prompt_path=str(cwd / TASK_PROMPT_FILE))
    _print_prompt_box(
        "Paste this into Claude Desktop or Claude Code (Sesame + Filesystem must be connected)",
        prompt,
    )
    print(f"📄  Full instructions: {TASK_PROMPT_FILE}")
    print(f"📝  Claude will write context to: {TASK_CONTEXT_FILE}")
    print(f"    Commit {TASK_CONTEXT_FILE} with your PR once Claude is done.\n")


# ---------------------------------------------------------------------------
# Command: pr
# ---------------------------------------------------------------------------


def cmd_pr(sesame_path: Path | None, draft: bool, title: str | None) -> None:
    """
    Write a .pr-prompt.md with full instructions and print a short one-liner for
    the developer to paste into Claude Desktop / Claude Code.
    Claude reads the prompt file, calls Sesame, and writes .pr-description.md
    directly via the Filesystem connector.
    Once the file exists, `gh pr create` is called automatically.
    """
    _find_sesame(sesame_path)  # validate early

    branch = _get_current_branch()
    if not branch:
        print("❌  Not on a git branch. Commit your changes first.", file=sys.stderr)
        sys.exit(1)

    ticket_id = _extract_ticket_id(branch) or _extract_ticket_id(title or "")
    if not ticket_id:
        print(
            "⚠️  No Jira ticket ID found in branch name or --title.\n"
            "   Tip: name your branch feature/PROJ-123-... for full context."
        )
        ticket_id = "UNKNOWN"

    # Write full instructions to .pr-prompt.md
    cwd = Path.cwd()
    instructions = _PR_DESCRIPTION_INSTRUCTIONS.format(
        branch=branch,
        ticket_id=ticket_id,
        context_path=str(cwd / TASK_CONTEXT_FILE),
        pr_path=str(cwd / PR_DESCRIPTION_FILE),
    )
    PR_PROMPT_FILE.write_text(instructions, encoding="utf-8")

    pr_title = title or (
        f"{ticket_id}: {branch.split('/')[-1].replace('-', ' ').title()}"
        if ticket_id != "UNKNOWN"
        else branch
    )

    # Print a short one-liner pointing Claude to the instructions file
    prompt = _PR_DESCRIPTION_PROMPT.format(prompt_path=str(cwd / PR_PROMPT_FILE))
    _print_prompt_box(
        "Paste this into Claude Desktop or Claude Code (Sesame + Filesystem must be connected)",
        prompt,
    )
    print(f"📄  Full instructions: {PR_PROMPT_FILE}")
    print(f"📝  Claude will write the PR description to: {PR_DESCRIPTION_FILE}")
    print(f"    Once Claude confirms, run `make pr-create` to open the PR.\n")


def cmd_pr_create(draft: bool, title: str | None) -> None:
    """
    Open a GitHub PR using the .pr-description.md already written by Claude.
    Run this after `make pr` once Claude has confirmed it wrote the file.
    """
    if not PR_DESCRIPTION_FILE.exists():
        print(
            f"\n❌  {PR_DESCRIPTION_FILE} not found.\n"
            "    Run `make pr` first and wait for Claude to write the file.",
            file=sys.stderr,
        )
        sys.exit(1)

    branch = _get_current_branch()
    ticket_id = _extract_ticket_id(branch) or _extract_ticket_id(title or "")
    pr_title = title or (
        f"{ticket_id}: {branch.split('/')[-1].replace('-', ' ').title()}"
        if ticket_id
        else branch
    )

    gh_cmd = ["gh", "pr", "create", "--title", pr_title, "--body-file", str(PR_DESCRIPTION_FILE)]
    if draft:
        gh_cmd.append("--draft")

    print(f"\n🚀  Creating {'draft ' if draft else ''}PR via gh CLI...\n")
    try:
        subprocess.run(gh_cmd, check=True)
    except FileNotFoundError:
        print(
            "❌  GitHub CLI (gh) not found.\n"
            "   Install it from https://cli.github.com, then run:\n\n"
            f"   gh pr create --title '{pr_title}' --body-file {PR_DESCRIPTION_FILE}"
            + (" --draft" if draft else ""),
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"❌  gh pr create failed: {exc}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dev_workflow",
        description="Internal Anaconda dev workflow helpers (not shipped in the conda package).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- setup --
    setup_p = sub.add_parser(
        "setup",
        help="Register Sesame in Claude Desktop and/or Claude Code (run once).",
    )
    setup_p.add_argument(
        "--sesame-path", type=Path, default=None,
        help=f"Path to Sesame binary (default: {SESAME_DEFAULT_PATH})",
    )
    setup_p.add_argument(
        "--target",
        choices=["all", "claude-desktop", "claude-code"],
        default="all",
        help="Which client to configure (default: all).",
    )

    # -- task --
    task_p = sub.add_parser(
        "task",
        help="Generate a task context prompt for Claude Desktop / Claude Code.",
    )
    task_p.add_argument("ticket_id", help="Jira ticket ID, e.g. PROJ-123")
    task_p.add_argument(
        "--sesame-path", type=Path, default=None,
        help=f"Path to Sesame binary (default: {SESAME_DEFAULT_PATH})",
    )
    task_p.add_argument(
        "--no-branch", action="store_true",
        help="Skip creating a git branch.",
    )

    # -- pr --
    pr_p = sub.add_parser(
        "pr",
        help="Write .pr-prompt.md and print a one-liner for Claude Desktop / Claude Code.",
    )
    pr_p.add_argument(
        "--sesame-path", type=Path, default=None,
        help=f"Path to Sesame binary (default: {SESAME_DEFAULT_PATH})",
    )
    pr_p.add_argument(
        "--no-draft", action="store_true",
        help="Create a ready-for-review PR instead of a draft.",
    )
    pr_p.add_argument(
        "--title", default=None,
        help="PR title (defaults to a title derived from branch name and ticket ID).",
    )

    # -- pr-create --
    pr_create_p = sub.add_parser(
        "pr-create",
        help="Open a GitHub PR using the .pr-description.md already written by Claude.",
    )
    pr_create_p.add_argument(
        "--no-draft", action="store_true",
        help="Create a ready-for-review PR instead of a draft.",
    )
    pr_create_p.add_argument(
        "--title", default=None,
        help="PR title (defaults to a title derived from branch name and ticket ID).",
    )

    return parser


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = _build_parser().parse_args()

    if args.command == "setup":
        cmd_setup(sesame_path=args.sesame_path, target=args.target)
    elif args.command == "task":
        cmd_task(ticket_id=args.ticket_id, sesame_path=args.sesame_path, no_branch=args.no_branch)
    elif args.command == "pr":
        cmd_pr(sesame_path=args.sesame_path, draft=not args.no_draft, title=args.title)
    elif args.command == "pr-create":
        cmd_pr_create(draft=not args.no_draft, title=args.title)


if __name__ == "__main__":
    main()
