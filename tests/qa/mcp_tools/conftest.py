from __future__ import annotations

import logging
import os
import signal
import subprocess
import tempfile
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from common.constants.test_data import ENV_NAME
from common.utils.conda_utils import _conda_env_prefix
from common.utils.stdio_client import (
    _recv,
    _send,
)
from mcp_compose_profiles import PROFILES_BY_SLUG

logger = logging.getLogger(__name__)

_MCP_TOOLS_DIR = Path(__file__).resolve().parent
_DEFAULT_HTML_REPORT = _MCP_TOOLS_DIR / "reports" / "report.html"

# STDIO profiles: stderr of ``conda run … anaconda-mcp serve`` is redirected to a temp file
# (module-scoped ``stdio_mcp_module`` and function-scoped ``stdio_server``).
_MCP_STDIO_MODULE_LOG_PATH_KEY = pytest.StashKey[Path | None]()
_MCP_STDIO_HANG_LOG_PATH_KEY = pytest.StashKey[Path | None]()
_MCP_SERVER_LOG_TAIL_CHARS = 48_000


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--mcp-profile",
        default=os.environ.get("MCP_PROFILE", "stdio-stdio"),
        choices=sorted(PROFILES_BY_SLUG.keys()),
        help="Native stdio profile label. Also reads MCP_PROFILE env var. (default: stdio-stdio)",
    )
    parser.addoption(
        "--python-version",
        default=None,
        metavar="VERSION",
        help="Server Python version label for reports (e.g. '3.13').",
    )
    parser.addoption(
        "--server-conda-env",
        default=os.environ.get("MCP_SERVER_CONDA_ENV", "anaconda-mcp-server"),
        metavar="ENV",
        help="Conda env with anaconda-mcp for native stdio serve.",
    )
    parser.addoption(
        "--skip-hang-stress",
        action="store_true",
        default=False,
        help=(
            "Skip tests marked hang_stress (KI-011 warm-iteration loops). "
            "Use for a shorter run when native stdio hang stress is unnecessary. "
            "Env MCP_QA_SKIP_HANG_STRESS=1 is equivalent."
        ),
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """
    Default pytest-html output under ``tests/qa/mcp_tools/reports/report.html``
    (self-contained), cwd-independent. Omit with ``pytest --html=...`` or
    uninstall pytest-html.
    """
    if config.pluginmanager.has_plugin("html"):
        try:
            if not config.getoption("htmlpath"):
                _DEFAULT_HTML_REPORT.parent.mkdir(parents=True, exist_ok=True)
                config.option.htmlpath = str(_DEFAULT_HTML_REPORT)
                if not config.getoption("self_contained_html"):
                    config.option.self_contained_html = True
        except (ValueError, AttributeError):
            pass

    try:
        env = config.getoption("--server-conda-env")
        if env:
            os.environ["MCP_SERVER_CONDA_ENV"] = env
    except ValueError:
        pass
    try:
        slug = config.getoption("--mcp-profile")
        if slug:
            os.environ["MCP_PROFILE"] = slug
    except ValueError:
        pass


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Optional skip of KI-011 ``hang_stress`` tests via ``--skip-hang-stress`` / env."""
    skip_hang = bool(config.getoption("--skip-hang-stress"))
    if os.environ.get("MCP_QA_SKIP_HANG_STRESS", "").lower() in ("1", "true", "yes"):
        skip_hang = True
    if skip_hang:
        reason = "Skipped: --skip-hang-stress or MCP_QA_SKIP_HANG_STRESS (omits KI-011 warm-iteration stress)"
        for item in items:
            if item.get_closest_marker("hang_stress"):
                item.add_marker(pytest.mark.skip(reason=reason))


def _append_html_log_tail(
    rep,
    *,
    log_path: Path | None,
    extra_name: str,
    header: str,
) -> None:
    if log_path is None or not log_path.is_file():
        return
    try:
        raw = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    tail = raw[-_MCP_SERVER_LOG_TAIL_CHARS:] if len(raw) > _MCP_SERVER_LOG_TAIL_CHARS else raw
    try:
        import pytest_html

        extra = pytest_html.extras.text(header + tail, name=extra_name)
        existing = list(getattr(rep, "extras", None) or [])
        rep.extras = existing + [extra]
    except Exception:
        logger.debug("Could not attach MCP log to html report", exc_info=True)


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Generator[None, Any, None]:
    """Append MCP server log tails to pytest-html for failed setup/call."""
    outcome = yield
    rep = outcome.get_result()
    if rep.when not in ("setup", "call") or not rep.failed:
        return
    if not item.config.pluginmanager.has_plugin("html"):
        return

    stash = item.config.stash
    _append_html_log_tail(
        rep,
        log_path=stash.get(_MCP_STDIO_MODULE_LOG_PATH_KEY, None),
        extra_name="mcp-stdio-module-stderr.log (tail)",
        header=(
            "Tail of STDERR from module-scoped STDIO MCP server "
            "(conda run … anaconda-mcp serve). JSON-RPC stays on stdout.\n\n"
        ),
    )
    _append_html_log_tail(
        rep,
        log_path=stash.get(_MCP_STDIO_HANG_LOG_PATH_KEY, None),
        extra_name="mcp-stdio-hang-stderr.log (tail)",
        header=("Tail of STDERR from function-scoped STDIO server (hang_stress / stdio_server).\n\n"),
    )


# ---------------------------------------------------------------------------
# Session / module fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def compose_profile(request: pytest.FixtureRequest):
    slug = request.config.getoption("--mcp-profile")
    return PROFILES_BY_SLUG[slug]


@contextmanager
def _stdio_server_context(
    *,
    conda_env: str,
    slug: str,
    log_prefix: str,
    stash_key: pytest.StashKey,
    client_name: str,
    label: str,
    config: pytest.Config,
) -> Iterator[subprocess.Popen]:
    """Spawn, initialise and yield a native stdio MCP server process; tear it down on exit."""
    logger.info("Starting %s native STDIO MCP serve (profile=%s)", label, slug)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["ANACONDA_MCP_ACCEPTED_TERMS"] = "true"
    env["ANACONDA_MCP_ACCEPTED_TERMS_VERSION"] = "2026-05-27"

    stderr_log = tempfile.NamedTemporaryFile(
        prefix=log_prefix,
        suffix="-stderr.log",
        delete=False,
    )
    stderr_path = Path(stderr_log.name)
    config.stash[stash_key] = stderr_path

    proc = subprocess.Popen(
        [
            "conda",
            "run",
            "-n",
            conda_env,
            "--no-capture-output",
            "anaconda-mcp",
            "serve",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr_log,
        start_new_session=True,
        env=env,
    )

    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": client_name, "version": "1.0"},
                },
            },
        )
        init_resp = _recv(proc, timeout=45)
        logger.info(
            "%s STDIO server ready — serverInfo: %s",
            label,
            init_resp.get("result", {}).get("serverInfo"),
        )
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    except Exception as exc:
        proc.kill()
        try:
            stderr_log.close()
        except OSError:
            pass
        stderr_path.unlink(missing_ok=True)
        config.stash[stash_key] = None
        pytest.fail(f"STDIO {label} server did not become ready: {exc}")

    try:
        yield proc
    finally:
        logger.info("Tearing down STDIO %s server (pid=%s)", label, proc.pid)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        try:
            stderr_log.close()
        except OSError:
            pass
        stderr_path.unlink(missing_ok=True)
        config.stash[stash_key] = None


@pytest.fixture(scope="module")
def stdio_mcp_module(request: pytest.FixtureRequest, compose_profile):
    with _stdio_server_context(
        conda_env=request.config.getoption("--server-conda-env"),
        slug=compose_profile.slug,
        log_prefix="anaconda-mcp-stdio-module-",
        stash_key=_MCP_STDIO_MODULE_LOG_PATH_KEY,
        client_name="mcp-tools-module",
        label="module",
        config=request.config,
    ) as proc:
        yield proc


@pytest.fixture(scope="module")
def call_tool(stdio_mcp_module):
    from common.utils.stdio_client import _call_tool_stdio

    assert stdio_mcp_module is not None

    def _call(name: str, arguments: dict):
        return _call_tool_stdio(stdio_mcp_module, name, arguments)

    return _call


@pytest.fixture
def stdio_server(request: pytest.FixtureRequest):
    compose_profile = PROFILES_BY_SLUG[request.config.getoption("--mcp-profile")]

    with _stdio_server_context(
        conda_env=request.config.getoption("--server-conda-env"),
        slug=compose_profile.slug,
        log_prefix="anaconda-mcp-stdio-hang-",
        stash_key=_MCP_STDIO_HANG_LOG_PATH_KEY,
        client_name="mcp-tools-hang",
        label="hang",
        config=request.config,
    ) as proc:
        yield proc


@pytest.fixture
def call_no_hang_unified(request: pytest.FixtureRequest):
    from common.utils.stdio_client import _call_no_hang_stdio

    proc = request.getfixturevalue("stdio_server")

    def stdio_call_no_hang(tool_name: str, arguments: dict, fail_msg: str):
        return _call_no_hang_stdio(proc, tool_name, arguments, fail_msg)

    return stdio_call_no_hang


@pytest.fixture(scope="module")
def conda_env():
    logger.info("Creating conda environment '%s'", ENV_NAME)
    subprocess.run(
        ["conda", "create", "-n", ENV_NAME, "python=3.11", "-y"],
        check=True,
    )
    prefix = _conda_env_prefix(ENV_NAME)
    logger.debug("Conda env '%s' prefix: %s", ENV_NAME, prefix)
    yield {"name": ENV_NAME, "prefix": prefix}
    logger.info("Removing conda environment '%s'", ENV_NAME)
    subprocess.run(
        ["conda", "remove", "-n", ENV_NAME, "--all", "-y"],
        check=False,
    )


@pytest.fixture(scope="module")
def cleanup_conda_env():
    registered: list[str] = []
    yield registered.append
    for name in registered:
        logger.info("Removing conda environment '%s'", name)
        subprocess.run(
            ["conda", "env", "remove", "-n", name, "-y"],
            check=False,
            capture_output=True,
        )


def pytest_sessionstart(session: pytest.Session) -> None:
    config = session.config
    metadata: dict | None = getattr(config, "_metadata", None)
    if metadata is None:
        return

    metadata["MCP profile"] = config.getoption("--mcp-profile")
    metadata["Server conda env"] = config.getoption("--server-conda-env")

    py_ver = config.getoption("--python-version")
    metadata["Server Python"] = py_ver if py_ver else "(not set — use --python-version)"
