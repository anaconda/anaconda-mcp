"""
Unified pytest configuration for MCP tool tests (all transport profiles).

``--mcp-profile`` selects client edge + upstream (http-http, stdio-http, stdio-stdio).
Fixtures adapt server lifecycle and call_tool without duplicating test modules.

Authentication support:
- ``auth_state`` fixture detects login status at session start
- Credentials from .env file (local) or environment variables (CI)
- Tests can use markers: @pytest.mark.auth_required, @pytest.mark.auth_enhanced
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import tempfile
import time
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
from common.constants.test_data import ENV_NAME
from common.utils.auth_service import AuthState, detect_auth_state
from common.utils.conda_utils import _conda_env_prefix, _get_conda_exe, _get_env_python_exe
from common.utils.mcp_client import _initialize_session
from common.utils.stdio_client import (
    _recv,
    _send,
    _write_profile_config,
)
from mcp_compose_profiles import PROFILES_BY_SLUG, ClientEdge

logger = logging.getLogger(__name__)

# Cache auth state at module load to avoid repeated detection
_AUTH_STATE_CACHE: AuthState | None = None

_INIT_BODY = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "preflight", "version": "1.0"},
    },
}
_SSE_HEADERS = {"Accept": "application/json, text/event-stream"}

_SCRIPT_PATH = (Path(__file__).resolve().parent / "scripts" / "start-http-server.sh").resolve()

_MCP_TOOLS_DIR = Path(__file__).resolve().parent
_DEFAULT_HTML_REPORT = _MCP_TOOLS_DIR / "reports" / "report.html"

# When ``--start-server`` captures anaconda-mcp + mcp-compose stdout, failed tests
# attach a tail of this file to the pytest-html report (see ``pytest_runtest_makereport``).
_MCP_SERVER_LOG_PATH_KEY = pytest.StashKey[Path | None]()
# STDIO profiles: stderr of ``conda run … anaconda-mcp serve`` is redirected to a temp file
# (module-scoped ``stdio_mcp_module`` and function-scoped ``stdio_server``).
_MCP_STDIO_MODULE_LOG_PATH_KEY = pytest.StashKey[Path | None]()
_MCP_STDIO_HANG_LOG_PATH_KEY = pytest.StashKey[Path | None]()
_MCP_SERVER_LOG_TAIL_CHARS = 48_000


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--mcp-profile",
        default=os.environ.get("MCP_PROFILE", "http-http"),
        choices=sorted(PROFILES_BY_SLUG.keys()),
        help=(
            "Transport profile: client→compose and compose→conda. Also reads MCP_PROFILE env var. (default: http-http)"
        ),
    )
    parser.addoption(
        "--server-url",
        default=os.environ.get("MCP_SERVER_URL", "http://localhost:9888/mcp"),
        help="MCP endpoint URL when client edge is HTTP (http-http profile).",
    )
    parser.addoption(
        "--compose-port",
        default=int(os.environ.get("MCP_COMPOSE_PORT", "9888")),
        type=int,
        help="Port embedded in generated http-http config / URL (default: 9888).",
    )
    parser.addoption(
        "--downstream-port",
        default=int(os.environ.get("MCP_DOWNSTREAM_PORT", "5041")),
        type=int,
        help="environments_mcp_server streamable-http port (default: 5041).",
    )
    parser.addoption(
        "--python-version",
        default=None,
        metavar="VERSION",
        help="Server Python version label for reports (e.g. '3.13').",
    )
    parser.addoption(
        "--start-server",
        action="store_true",
        default=os.environ.get("MCP_QA_START_SERVER", "0") == "1",
        help=(
            "Auto-start MCP server for http-http via start-http-server.sh. "
            "Requires --server-conda-env with anaconda-mcp installed. "
            "Env: MCP_QA_START_SERVER=1."
        ),
    )
    parser.addoption(
        "--server-conda-env",
        default=os.environ.get("MCP_SERVER_CONDA_ENV", "anaconda-mcp-server"),
        metavar="ENV",
        help="Conda env with anaconda-mcp (stdio profiles and --start-server).",
    )
    parser.addoption(
        "--skip-hang-stress",
        action="store_true",
        default=False,
        help=(
            "Skip tests marked hang_stress (KI-011 warm-iteration loops). "
            "Use for a shorter run or when mcp-compose is flaky after a prior hang. "
            "Env MCP_QA_SKIP_HANG_STRESS=1 is equivalent."
        ),
    )


def _load_dotenv() -> None:
    """Load .env file from repo root if it exists."""
    env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if not env_file.exists():
        return

    logger.debug("Loading environment from %s", env_file)
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
                    logger.debug("Loaded %s from .env", key)
    except Exception as e:
        logger.warning("Failed to load .env: %s", e)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """
    Default pytest-html output under ``tests/qa/mcp_tools/reports/report.html``
    (self-contained), cwd-independent. Omit with ``pytest --html=...`` or
    uninstall pytest-html.

    Also loads .env file, detects auth state, and registers auth markers.
    """
    global _AUTH_STATE_CACHE

    _load_dotenv()

    # Detect auth state early so token is available for mcp_compose_profiles
    _AUTH_STATE_CACHE = detect_auth_state()
    logger.info("Auth state: %s", _AUTH_STATE_CACHE)

    # Export token to env so mcp_compose_profiles.py can use it
    if _AUTH_STATE_CACHE.logged_in and _AUTH_STATE_CACHE.token:
        os.environ["ANACONDA_AUTH_API_KEY"] = _AUTH_STATE_CACHE.token

    config.addinivalue_line("markers", "auth_independent: Tool works without authentication")
    config.addinivalue_line("markers", "auth_required: Tool requires authentication to return results")
    config.addinivalue_line("markers", "auth_enhanced: Tool works with/without auth, different results")

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
        url = config.getoption("--server-url")
        if url:
            os.environ["MCP_SERVER_URL"] = url
    except ValueError:
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
    try:
        dp = config.getoption("--downstream-port")
        os.environ["MCP_DOWNSTREAM_PORT"] = str(dp)
    except ValueError:
        pass


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Optional skip of KI-011 ``hang_stress`` tests via ``--skip-hang-stress`` / env."""
    skip_hang = bool(config.getoption("--skip-hang-stress"))
    if os.environ.get("MCP_QA_SKIP_HANG_STRESS", "").lower() in ("1", "true", "yes"):
        skip_hang = True
    if skip_hang:
        reason = (
            "Skipped: --skip-hang-stress or MCP_QA_SKIP_HANG_STRESS "
            "(omits KI-011 warm-iteration stress; use when mcp-compose is unstable)"
        )
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
        log_path=stash.get(_MCP_SERVER_LOG_PATH_KEY, None),
        extra_name="mcp-server.log (tail)",
        header=(
            "Tail of anaconda-mcp / mcp-compose process log "
            "(--start-server). Full file on disk until session teardown.\n\n"
        ),
    )
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


@pytest.fixture(scope="session")
def server_url(request: pytest.FixtureRequest) -> str:
    return str(request.config.getoption("--server-url"))


@pytest.fixture(scope="session", autouse=True)
def mcp_server(request: pytest.FixtureRequest, server_url: str):
    """Start or verify HTTP server (http-http only)."""
    if PROFILES_BY_SLUG[request.config.getoption("--mcp-profile")].client != ClientEdge.HTTP:
        yield None
        return

    server_proc: subprocess.Popen | None = None
    log_path: Path | None = None
    log_file = None

    if request.config.getoption("--start-server"):
        conda_env = request.config.getoption("--server-conda-env")
        port = _port_from_url(server_url)

        if not _SCRIPT_PATH.exists():
            pytest.fail(
                f"Server start script not found: {_SCRIPT_PATH}\n"
                "Ensure tests/qa/mcp_tools/scripts/start-http-server.sh exists."
            )
        conda_exe = _get_conda_exe()
        if conda_exe == "conda" and not shutil.which("conda"):
            pytest.fail("conda not found in PATH; cannot auto-start the server.")

        log_file = tempfile.NamedTemporaryFile(mode="w", suffix="-anaconda-mcp.log", delete=False)
        log_path = Path(log_file.name)
        request.config.stash[_MCP_SERVER_LOG_PATH_KEY] = log_path

        logger.info("Starting MCP server (conda env: %s, port: %s, conda: %s)", conda_env, port, conda_exe)
        env = os.environ.copy()
        # Terms acceptance required by main branch
        # Use env var if set (CI), otherwise fall back to default
        env["ANACONDA_MCP_ACCEPTED_TERMS"] = os.environ.get("ANACONDA_MCP_ACCEPTED_TERMS", "true")
        env["ANACONDA_MCP_ACCEPTED_TERMS_VERSION"] = os.environ.get("ANACONDA_MCP_ACCEPTED_TERMS_VERSION", "2026-05-19")
        # Ensure auth token is passed to subprocess
        if _AUTH_STATE_CACHE and _AUTH_STATE_CACHE.token:
            env["ANACONDA_AUTH_API_KEY"] = _AUTH_STATE_CACHE.token
        server_proc = subprocess.Popen(
            [conda_exe, "run", "-n", conda_env, "--no-capture-output", "bash", str(_SCRIPT_PATH), port],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )

        def _on_timeout() -> None:
            server_proc.kill()
            log_file.flush()
            try:
                tail = log_path.read_text()[-3000:]
            except Exception:
                tail = "(could not read log)"
            logger.error("MCP server did not become ready within 60 s. Log tail:\n%s", tail)
            pytest.fail(
                f"MCP server at {server_url} did not become ready within 60 s.\n"
                f"Conda env: '{conda_env}'\n"
                f"Log ({log_path}):\n{tail}"
            )

        _wait_for_server(server_url, timeout=60, on_timeout=_on_timeout)
        logger.info("MCP server is ready at %s", server_url)
    else:
        _assert_server_reachable(server_url)

    yield

    if server_proc is not None:
        logger.info("Stopping MCP server (pid %s)", server_proc.pid)
        try:
            os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            server_proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        try:
            if log_file is not None:
                log_file.close()
            if log_path is not None:
                log_path.unlink(missing_ok=True)
        except Exception:
            pass


@pytest.fixture(scope="module")
def session_id(mcp_server, server_url: str, compose_profile) -> str | None:
    if compose_profile.client != ClientEdge.HTTP:
        return None
    sid: str | None = _initialize_session(server_url, client_name="api-tools-test")
    return sid


def _terminate_process_tree(proc: subprocess.Popen) -> None:
    """
    Terminate a process and all its children.

    On Unix: uses os.killpg() to kill the process group.
    On Windows: uses taskkill /T to kill the process tree (child processes included).

    This is critical for proper cleanup of anaconda-mcp which spawns child servers
    (environments-mcp, conda-meta-mcp) that would otherwise keep ports locked.
    """
    try:
        if os.name != "nt":
            # Unix: kill process group
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            # Windows: use taskkill /T to kill entire process tree
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=10,
            )
    except (ProcessLookupError, PermissionError, OSError, subprocess.TimeoutExpired):
        # Fallback: just kill the main process
        proc.kill()

    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Process %s did not terminate after kill", proc.pid)


@contextmanager
def _stdio_server_context(
    *,
    conda_env: str,
    slug: str,
    compose_port: int,
    downstream_port: int,
    log_prefix: str,
    stash_key: pytest.StashKey,
    client_name: str,
    label: str,
    config: pytest.Config,
) -> Iterator[subprocess.Popen]:
    """
    Spawn, initialise and yield a STDIO MCP server process; tear it down on exit.

    Uses direct Python executable (not `conda run`) to match real IDE integrations.
    This avoids stdin/stdout forwarding issues that occur with `conda run` on Windows.
    """
    config_path = _write_profile_config(
        slug,
        conda_env,
        compose_port=compose_port,
        downstream_port=downstream_port,
    )
    logger.info("Starting %s STDIO MCP (profile=%s, config=%s)", label, slug, config_path)

    # Get Python executable directly from conda env (matches real IDE integrations)
    python_exe = _get_env_python_exe(conda_env)
    logger.info("Using Python executable: %s", python_exe)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # Terms acceptance required by main branch
    # Use env var if set (CI), otherwise fall back to default
    env["ANACONDA_MCP_ACCEPTED_TERMS"] = os.environ.get("ANACONDA_MCP_ACCEPTED_TERMS", "true")
    env["ANACONDA_MCP_ACCEPTED_TERMS_VERSION"] = os.environ.get("ANACONDA_MCP_ACCEPTED_TERMS_VERSION", "2026-05-19")
    # Ensure auth token is passed to subprocess
    # Token should already be in os.environ from pytest_configure, but explicit is safer
    if _AUTH_STATE_CACHE and _AUTH_STATE_CACHE.token:
        env["ANACONDA_AUTH_API_KEY"] = _AUTH_STATE_CACHE.token

    stderr_log = tempfile.NamedTemporaryFile(
        prefix=log_prefix,
        suffix="-stderr.log",
        delete=False,
    )
    stderr_path = Path(stderr_log.name)
    config.stash[stash_key] = stderr_path

    # start_new_session=True uses os.setsid() on Unix, CREATE_NEW_PROCESS_GROUP on Windows
    popen_kwargs: dict = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": stderr_log,
        "env": env,
    }
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    else:
        # On Windows, use CREATE_NEW_PROCESS_GROUP for proper termination
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    # Launch anaconda-mcp directly via Python executable (not conda run)
    # This matches how real IDE integrations work and avoids Windows pipe issues
    proc = subprocess.Popen(
        [
            python_exe,
            "-m",
            "anaconda_mcp",
            "serve",
            "--config",
            str(config_path),
        ],
        **popen_kwargs,
    )

    try:
        # Wait for server to initialize downstream connections before sending request
        time.sleep(15)
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
        init_resp = _recv(proc, timeout=60)
        logger.info(
            "%s STDIO server ready — serverInfo: %s",
            label,
            init_resp.get("result", {}).get("serverInfo"),
        )
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    except Exception as exc:
        proc.kill()
        # Wait for process to fully terminate before accessing files (especially on Windows)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        try:
            stderr_log.close()
        except OSError:
            pass
        # Small delay on Windows to allow file handles to be released
        if os.name == "nt":
            time.sleep(0.5)
        # Preserve stderr log for debugging
        stderr_content = ""
        try:
            with open(stderr_path) as f:
                stderr_content = f.read()
        except Exception:
            pass
        # Try to clean up files, but don't fail if still locked (Windows)
        try:
            stderr_path.unlink(missing_ok=True)
        except PermissionError:
            logger.warning("Could not delete stderr log (file locked): %s", stderr_path)
        config.stash[stash_key] = None
        try:
            config_path.unlink(missing_ok=True)
        except PermissionError:
            logger.warning("Could not delete config (file locked): %s", config_path)
        pytest.fail(f"STDIO {label} server did not become ready: {exc}\n\nServer stderr:\n{stderr_content[-4000:]}")

    try:
        yield proc
    finally:
        logger.info("Tearing down STDIO %s server (pid=%s)", label, proc.pid)
        _terminate_process_tree(proc)
        try:
            stderr_log.close()
        except OSError:
            pass
        # Delay on Windows to allow file handles to be released
        if os.name == "nt":
            time.sleep(1.0)
        try:
            stderr_path.unlink(missing_ok=True)
        except PermissionError:
            logger.warning("Could not delete stderr log (file locked): %s", stderr_path)
        config.stash[stash_key] = None
        try:
            config_path.unlink(missing_ok=True)
        except PermissionError:
            logger.warning("Could not delete config (file locked): %s", config_path)


@pytest.fixture(scope="module")
def stdio_mcp_module(request: pytest.FixtureRequest, compose_profile):
    """One mcp-compose process per module for STDIO client profiles (shared across tests in file)."""
    if compose_profile.client != ClientEdge.STDIO:
        # Must yield: this function contains ``yield`` below, so it is a generator;
        # ``return`` without yielding breaks pytest (ValueError: did not yield a value).
        yield None
        return

    with _stdio_server_context(
        conda_env=request.config.getoption("--server-conda-env"),
        slug=compose_profile.slug,
        compose_port=request.config.getoption("--compose-port"),
        downstream_port=request.config.getoption("--downstream-port"),
        log_prefix="anaconda-mcp-stdio-module-",
        stash_key=_MCP_STDIO_MODULE_LOG_PATH_KEY,
        client_name="mcp-tools-module",
        label="module",
        config=request.config,
    ) as proc:
        yield proc


@pytest.fixture(scope="module")
def call_tool(session_id, stdio_mcp_module, compose_profile):
    """Module-scoped tool invoker (HTTP or STDIO) matching --mcp-profile."""
    from common.utils.mcp_client import _call_tool as _http_call
    from common.utils.stdio_client import _call_tool_stdio

    if compose_profile.client == ClientEdge.HTTP:

        def _call(name: str, arguments: dict):
            return _http_call(name, arguments, session_id)

        return _call

    assert stdio_mcp_module is not None

    def _call(name: str, arguments: dict):
        return _call_tool_stdio(stdio_mcp_module, name, arguments)

    return _call


@pytest.fixture
def fresh_session_id(mcp_server, server_url: str, compose_profile) -> str | None:
    if compose_profile.client != ClientEdge.HTTP:
        pytest.skip("fresh_session_id applies only to http-http (HTTP client edge)")
    sid: str | None = _initialize_session(server_url, client_name="api-tools-hang-test")
    return sid


@pytest.fixture
def stdio_server(request: pytest.FixtureRequest, compose_profile):
    """Function-scoped STDIO server for hang regressions (fresh process per test)."""
    if compose_profile.client != ClientEdge.STDIO:
        pytest.skip("stdio_server applies only to stdio-http / stdio-stdio")

    with _stdio_server_context(
        conda_env=request.config.getoption("--server-conda-env"),
        slug=compose_profile.slug,
        compose_port=request.config.getoption("--compose-port"),
        downstream_port=request.config.getoption("--downstream-port"),
        log_prefix="anaconda-mcp-stdio-hang-",
        stash_key=_MCP_STDIO_HANG_LOG_PATH_KEY,
        client_name="mcp-tools-hang",
        label="hang",
        config=request.config,
    ) as proc:
        yield proc


@pytest.fixture
def call_no_hang_unified(request: pytest.FixtureRequest, compose_profile):
    """Hang-safe tool call: HTTP uses httpx timeout; STDIO uses thread read timeout."""
    from common.utils.mcp_client import _call_no_hang as _http_no_hang
    from common.utils.stdio_client import _call_no_hang_stdio

    if compose_profile.client == ClientEdge.HTTP:
        sid = request.getfixturevalue("fresh_session_id")

        def http_call_no_hang(tool_name: str, arguments: dict, fail_msg: str):
            return _http_no_hang(tool_name, arguments, sid, fail_msg)

        return http_call_no_hang

    proc = request.getfixturevalue("stdio_server")

    def stdio_call_no_hang(tool_name: str, arguments: dict, fail_msg: str):
        return _call_no_hang_stdio(proc, tool_name, arguments, fail_msg)

    return stdio_call_no_hang


@pytest.fixture(scope="module")
def conda_env():
    conda_exe = _get_conda_exe()
    logger.info("Creating conda environment '%s' (using %s)", ENV_NAME, conda_exe)
    subprocess.run(
        [conda_exe, "create", "-n", ENV_NAME, "python=3.11", "-y"],
        check=True,
    )
    prefix = _conda_env_prefix(ENV_NAME)
    logger.debug("Conda env '%s' prefix: %s", ENV_NAME, prefix)
    yield {"name": ENV_NAME, "prefix": prefix}
    logger.info("Removing conda environment '%s'", ENV_NAME)
    subprocess.run(
        [conda_exe, "remove", "-n", ENV_NAME, "--all", "-y"],
        check=False,
    )


@pytest.fixture(scope="module")
def cleanup_conda_env():
    conda_exe = _get_conda_exe()
    registered: list[str] = []
    yield registered.append
    for name in registered:
        logger.info("Removing conda environment '%s'", name)
        subprocess.run(
            [conda_exe, "env", "remove", "-n", name, "-y"],
            check=False,
            capture_output=True,
        )


def pytest_sessionstart(session: pytest.Session) -> None:
    global _AUTH_STATE_CACHE
    # Auth state already detected in pytest_configure (needed early for token export)
    if _AUTH_STATE_CACHE is None:
        _AUTH_STATE_CACHE = detect_auth_state()
        logger.info("Auth state: %s", _AUTH_STATE_CACHE)
        if _AUTH_STATE_CACHE.logged_in and _AUTH_STATE_CACHE.token:
            os.environ["ANACONDA_AUTH_API_KEY"] = _AUTH_STATE_CACHE.token

    config = session.config
    metadata: dict | None = getattr(config, "_metadata", None)
    if metadata is None:
        return

    metadata["MCP profile"] = config.getoption("--mcp-profile")
    metadata["Server URL"] = config.getoption("--server-url")
    metadata["Server conda env"] = config.getoption("--server-conda-env")
    metadata["Auth state"] = str(_AUTH_STATE_CACHE)

    py_ver = config.getoption("--python-version")
    metadata["Server Python"] = py_ver if py_ver else "(not set — use --python-version)"


def pytest_report_header(config: pytest.Config) -> list[str]:
    """Report auth state in test session header."""
    global _AUTH_STATE_CACHE
    if _AUTH_STATE_CACHE is None:
        _AUTH_STATE_CACHE = detect_auth_state()
    return [f"auth state: {_AUTH_STATE_CACHE}"]


@pytest.fixture(scope="session")
def auth_state() -> AuthState:
    """
    Session-scoped fixture providing authentication state.

    Detection priority:
    1. ANACONDA_AUTH_API_KEY environment variable
    2. No authentication available

    Usage in tests:
        def test_example(auth_state):
            if not auth_state.logged_in:
                pytest.skip("Requires authentication")
    """
    global _AUTH_STATE_CACHE
    if _AUTH_STATE_CACHE is None:
        _AUTH_STATE_CACHE = detect_auth_state()
    return _AUTH_STATE_CACHE


def _port_from_url(url: str) -> str:
    try:
        return url.rstrip("/").rsplit(":", 1)[-1].split("/")[0]
    except (IndexError, ValueError):
        return "9888"


def _wait_for_server(url: str, *, timeout: float, on_timeout) -> None:
    logger.info("Waiting for MCP server at %s (timeout=%ss)", url, timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.post(url, json=_INIT_BODY, headers=_SSE_HEADERS, timeout=3)
            logger.debug("Server probe: HTTP %s", r.status_code)
            if r.status_code in (200, 202, 406):
                return
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(2)
    on_timeout()


def _assert_server_reachable(url: str) -> None:
    logger.info("Checking MCP server reachability at %s", url)
    try:
        httpx.post(url, json=_INIT_BODY, headers=_SSE_HEADERS, timeout=5)
        logger.info("MCP server is reachable at %s", url)
    except httpx.ConnectError:
        logger.error("MCP server not reachable at %s", url)
        pytest.skip(f"MCP server not reachable at {url}.\nStart: {_SCRIPT_PATH}\nOr: pytest ... --start-server")
