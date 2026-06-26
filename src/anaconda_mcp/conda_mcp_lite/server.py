#!/usr/bin/env python3
"""
Minimal conda MCP server. Single file. Depends only on fastmcp.

Wraps conda via subprocess. Discovers the conda executable using a
multi-step strategy that handles GUI-launched agents (no shell, minimal PATH).

Pattern for shell probe from VS Code's shell environment resolution:
https://github.com/microsoft/vscode/blob/d44e26a3/src/vs/platform/shell/node/shellEnv.ts
"""

# ---------------------------------------------------------------------------
# Vendored from Anaconda-Sandbox/conda-mcp-lite (commit ba79965), MIT.
# Kept functionally identical on vendoring; production hardening (channel
# governance, destructive annotations, stdout hygiene) is applied separately.
# Entry point: anaconda_mcp/conda_mcp_lite/__main__.py -> __init__.main().
# ---------------------------------------------------------------------------

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

logger = logging.getLogger(__name__)
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

mcp = FastMCP("Environments MCP Server")

# ─── Module-level cache ──────────────────────────────────────────────────────

_conda_exe: Path | None = None
_conda_info: dict | None = None


# ─── Channel Governance ──────────────────────────────────────────────────────

_ALLOW_CHANNEL_OVERRIDE = os.environ.get("ANACONDA_MCP_ALLOW_CHANNEL_OVERRIDE", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_CHANNEL_PARAMS = {"channels", "override_channels"}


def _strip_params(fn: Callable, params_to_strip: set[str]) -> Callable:
    # FastMCP derives the tool schema from the callable signature, so dropping
    # parameters here hides them from the agent; the wrapper also ignores them at runtime.
    sig = inspect.signature(fn)
    new_params = [p for name, p in sig.parameters.items() if name not in params_to_strip]

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        for param in params_to_strip:
            kwargs.pop(param, None)
        return await fn(*args, **kwargs)

    wrapper.__dict__["__signature__"] = sig.replace(parameters=new_params)
    return wrapper


# ─── Conda Discovery ─────────────────────────────────────────────────────────


def find_conda_exe() -> Path:
    """
    Find the conda executable. Priority chain, first valid match wins.

    1. CONDA_EXE env var (set by conda activation)
    2. _CONDA_ROOT/bin/conda (set by conda shell hook)
    3. shutil.which("conda") (condabin on PATH)
    4a. Unix: interactive shell probe
    4b. Windows: registry AutoRun hook
    5. Windows: registry Uninstall key (always written by installer)
    6. Fail with actionable error
    """
    if (exe := os.environ.get("CONDA_EXE")) and Path(exe).is_file():
        logger.info(f"Found conda via CONDA_EXE: {exe}")
        return Path(exe)
    elif root := os.environ.get("_CONDA_ROOT"):
        candidate = Path(root) / "bin" / "conda"
        if candidate.is_file():
            logger.info(f"Found conda via _CONDA_ROOT: {candidate}")
            return candidate

    if found := shutil.which("conda"):
        logger.info(f"Found conda via PATH: {found}")
        return Path(found)

    if platform.system() != "Windows":
        if exe := _probe_conda_from_shell():
            logger.info(f"Found conda via shell probe: {exe}")
            return Path(exe)
    else:
        if exe := _find_conda_from_registry_autorun():
            logger.info(f"Found conda via registry AutoRun: {exe}")
            return Path(exe)
        if exe := _find_conda_from_registry_uninstall():
            logger.info(f"Found conda via registry Uninstall: {exe}")
            return Path(exe)

    raise RuntimeError(
        "Could not find conda executable. "
        "Set CONDA_EXE in your MCP client config's env block. "
        'Example: {"env": {"CONDA_EXE": "/path/to/conda"}}'
    )


def _probe_conda_from_shell(timeout: float = 5.0) -> str | None:
    """
    Unix: spawn the user's interactive shell to extract CONDA_EXE.

    conda init writes to interactive shell RC files (.bashrc, .zshrc),
    so we need -i to source them. A unique marker isolates the value
    from shell noise (motd, prompt strings, etc).
    """
    shell = os.environ.get("SHELL")
    if not shell:
        return None

    mark = uuid.uuid4().hex[:12]
    command = f'echo "{mark}${{CONDA_EXE}}{mark}"'

    shell_name = os.path.basename(shell)
    if shell_name in ("tcsh", "csh"):
        args = [shell, "-ic", command]
    else:
        args = [shell, "-i", "-c", command]

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        match = re.search(f"{mark}(.+?){mark}", result.stdout)
        if match:
            conda_exe = match.group(1).strip()
            if conda_exe and Path(conda_exe).is_file():
                return conda_exe
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def _find_conda_from_registry_autorun() -> str | None:
    """
    Windows: check cmd.exe AutoRun registry key for conda hook path.
    Set by 'conda init cmd.exe'. Contains path to conda_hook.bat
    from which we can derive the conda root.
    """
    if sys.platform != "win32":
        return None
    import winreg

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, r"Software\Microsoft\Command Processor") as key:
                autorun, _ = winreg.QueryValueEx(key, "AutoRun")
                for part in autorun.replace('"', "").split("&"):
                    part = part.strip()
                    if "conda" in part.lower() and part.endswith(".bat"):
                        hook_path = Path(part)
                        root = hook_path.parent.parent
                        conda_exe = root / "Scripts" / "conda.exe"
                        if conda_exe.is_file():
                            return str(conda_exe)
        except OSError:
            continue

    return None


def _find_conda_from_registry_uninstall() -> str | None:
    """
    Windows: find conda from the installer's Uninstall registry entry.
    Always written by the Anaconda/Miniconda installer, does NOT require
    'conda init' to have been run.
    """
    if sys.platform != "win32":
        return None
    import winreg

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Uninstall") as uninstall:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(uninstall, i)
                        if "conda" in subkey_name.lower() or "anaconda" in subkey_name.lower():
                            with winreg.OpenKey(uninstall, subkey_name) as subkey:
                                try:
                                    location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                    conda_exe = Path(location) / "Scripts" / "conda.exe"
                                    if conda_exe.is_file():
                                        return str(conda_exe)
                                except OSError:
                                    pass
                        i += 1
                    except OSError:
                        break
        except OSError:
            continue

    return None


# ─── Conda Runner ────────────────────────────────────────────────────────────


def _ensure_conda_exe() -> None:
    """Lazily discover the conda executable if not already set.

    The stdio entrypoint (``__init__.main``) sets ``_conda_exe`` at startup, but
    when this server is mounted in-process (no ``main()``), it stays ``None``
    until the first tool call. Discover it on demand so mounted tools work.
    """
    global _conda_exe
    if _conda_exe is None:
        _conda_exe = find_conda_exe()


async def run_conda(*args: str, positionals: list[str] | None = None) -> dict | list:
    """
    Run a conda command with --json, return parsed output.

    Any user-controlled positional specs (package names) are passed AFTER a
    ``--`` separator so conda can never interpret them as options (option
    injection). ``--json`` is placed BEFORE ``--`` so it stays a flag.
    Raises RuntimeError on failure.
    """
    await asyncio.to_thread(_ensure_conda_exe)
    cmd = [str(_conda_exe), *args, "--json"]
    if positionals:
        cmd += ["--", *positionals]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if not stdout.strip():
        raise RuntimeError(f"conda returned no output. Command: {' '.join(cmd)}\nstderr: {stderr.decode()}")

    try:
        data: dict | list = json.loads(stdout)
    except json.JSONDecodeError as err:
        raise RuntimeError(
            f"conda returned invalid JSON. Command: {' '.join(cmd)}\n"
            f"stdout: {stdout.decode()[:500]}\n"
            f"stderr: {stderr.decode()[:500]}"
        ) from err

    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(data.get("message", data["error"]))

    return data


def get_conda_info() -> dict:
    """Get cached conda info (root_prefix, envs, etc). Populated at startup."""
    global _conda_info
    _ensure_conda_exe()
    if _conda_info is None:
        result = subprocess.run(
            [str(_conda_exe), "info", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"conda info failed: {result.stderr}")
        _conda_info = json.loads(result.stdout)
    assert _conda_info is not None
    return _conda_info


def _reject_option_like(values: Sequence[str | None] | None, *, kind: str) -> str | None:
    """Return an error message if any value begins with '-' (option injection), else None."""
    for v in values or []:
        if isinstance(v, str) and v.startswith("-"):
            return f"Invalid {kind}: {v!r} may not begin with '-'"
    return None


# ─── Tools ───────────────────────────────────────────────────────────────────


@mcp.tool
async def list_environments() -> dict:
    """
    Lists all conda environments available on the system.

    WHEN TO USE:
    - User asks "what environments do I have?" or similar queries
    - User needs to choose an environment for package installation
    - Before deleting an environment, to verify the correct target
    - User is unsure which environment to activate or work with
    - User wants an overview of their conda setup

    WORKFLOW GUIDANCE:
    1. Call this tool to retrieve all environments
    2. Present results in a clear, readable format showing:
       - Environment names
       - File paths (prefix)
       - Key information about each environment
    3. If user is looking for a specific environment, help identify it from the list
    4. If list is empty or unexpected, explain what this means

    COMMON USE CASES:
    - "Show me my environments"
    - "What conda environments exist?"
    - "List all my projects"
    - "Which environments do I have?"

    COMMON FOLLOW-UP ACTIONS:
    - After listing, user may want to delete one of them
    - After listing, user may want to install packages into one
    - After listing, user may want to remove packages from one
    - After listing, user may want to create a new one

    OUTPUT FORMAT:
    Returns information about each environment including name and location.
    Present this to users in an easy-to-read format.

    """
    try:
        info = await asyncio.to_thread(get_conda_info)
        root_prefix = info["root_prefix"]
        env_paths = info["envs"]

        environments = []
        for env_path in env_paths:
            env_name = os.path.basename(env_path)
            if env_name == "" or env_name == "env":
                env_name = os.path.basename(os.path.dirname(env_path))
            if os.path.normpath(env_path) == os.path.normpath(root_prefix):
                env_name = "base"
            environments.append({"name": env_name, "path": env_path})

        return {"is_error": False, "error_description": "", "tool_result": {"environments": environments}}
    except Exception as ex:
        logger.error(f"Failed to list environments: {ex}")
        return {"is_error": True, "error_description": str(ex), "tool_result": None}


@mcp.tool
async def list_environment_packages(
    prefix: str | None = None,
    environment: str | None = None,
) -> dict:
    """
    Lists all packages installed in an existing conda environment.

    WHEN TO USE:
    - User wants to inspect what packages are installed in an environment
    - User needs to verify a package was successfully installed or removed
    - User is troubleshooting dependency or compatibility issues
    - User wants to audit or document their environment's contents
    - User is comparing packages across environments

    WORKFLOW GUIDANCE:
    1. If environment isn't specified, ask which environment to inspect
    2. Present results in a clear, readable format showing package names and versions
    3. If user is looking for a specific package, help identify it from the list
    4. If the environment is not found, suggest listing environments first to verify the name

    COMMON USE CASES:
    - "What packages are in my environment?" → list_environment_packages(environment="data-project")
    - "Is numpy installed?" → list_environment_packages(environment="ml-env")
    - "Show me what's in /home/user/envs/myenv" → list_environment_packages(prefix="/home/user/envs/myenv")
    - "What packages were recently added?"

    TROUBLESHOOTING SCENARIOS:
    - Missing imports: User gets ImportError and wants to verify if package is installed
    - Version conflicts: User wants to check which version of a package is installed
    - Environment audit: User wants a full list before sharing or replicating the environment

    Args:
        environment: Name of the environment (e.g., "data-analysis", "web-scraping")
        prefix: Full path to the environment (e.g., "/home/user/envs/myenv")

    Note: Provide either environment name OR prefix, not both.

    Returns: A dictionary containing the list of installed packages with name, version,
             build string, channel, platform, and dist_name for each package
    """
    if err := _reject_option_like([environment, prefix], kind="environment name or prefix"):
        return {"is_error": True, "error_description": err, "tool_result": None}
    try:
        args = ["list"]
        if prefix:
            args += ["-p", prefix]
        elif environment:
            args += ["-n", environment]
        else:
            return {"is_error": True, "error_description": "Provide environment name or prefix", "tool_result": None}

        packages = await run_conda(*args)
        trimmed = [
            {"name": p["name"], "version": p["version"], "channel": p.get("channel", "")}
            for p in packages
            if isinstance(p, dict)
        ]
        return {"is_error": False, "error_description": "", "tool_result": {"packages": trimmed}}
    except RuntimeError as ex:
        return {"is_error": True, "error_description": str(ex), "tool_result": None}
    except Exception as ex:
        logger.error(f"Failed to list installed packages: {ex}")
        return {"is_error": True, "error_description": f"Failed to list installed packages: {ex}", "tool_result": None}


async def create_environment(
    environment_name: str | None = None,
    prefix: str | None = None,
    packages: list[str] | None = None,
    channels: list[str] | None = None,
    override_channels: bool = False,
) -> dict:
    """
    Creates a new conda environment based on the user's project requirements.

    WHEN TO USE:
    - User describes a project goal or task (e.g., "I need to build a forecasting model")
    - User explicitly requests a new environment
    - User has discussed technical requirements and is ready to set up their workspace

    WORKFLOW GUIDANCE:
    1. If user's request is ambiguous, ask clarifying questions about their use case before calling
    2. Propose a meaningful environment name based on the project (not auto-generated)
    3. After creation, confirm: environment name, installed packages with versions, activation command

    CHANNEL COMPLIANCE:
    - Only install packages from user's configured channels
    - If a requested package isn't available in configured channels, explain the limitation and suggest alternatives

    Args:
        environment_name: Human-readable name reflecting project purpose (e.g., "forecasting-q1", "nlp-analysis")
        prefix: The prefix/path of the environment to create.
        packages: List of packages - infer from user's described goals if not explicitly provided
        channels: List of channels to use for package resolution
        override_channels: When True, use ONLY the specified channels (ignoring configured defaults)
    """
    if prefix is None and environment_name is None:
        return {"is_error": True, "error_description": "Provide prefix or environment name", "tool_result": None}

    if err := _reject_option_like([environment_name, prefix], kind="environment name or prefix"):
        return {"is_error": True, "error_description": err, "tool_result": None}
    if err := _reject_option_like(packages, kind="package spec"):
        return {"is_error": True, "error_description": err, "tool_result": None}
    if err := _reject_option_like(channels, kind="channel"):
        return {"is_error": True, "error_description": err, "tool_result": None}

    try:
        args = ["create", "-y"]
        if prefix:
            args += ["-p", prefix]
        elif environment_name:
            args += ["-n", environment_name]

        if channels:
            for ch in channels:
                args += ["-c", ch]
            if override_channels:
                args.append("--override-channels")

        result = await run_conda(*args, positionals=packages)
        prefix = result["prefix"] if isinstance(result, dict) and "prefix" in result else ""
        return {
            "is_error": False,
            "error_description": "",
            "tool_result": {"message": "Environment created successfully", "prefix": prefix},
        }
    except RuntimeError as ex:
        return {"is_error": True, "error_description": str(ex), "tool_result": None}
    except Exception as ex:
        logger.error(f"Failed to create environment: {ex}")
        return {
            "is_error": True,
            "error_description": f"There was an error while creating the environment. Details: {ex}",
            "tool_result": None,
        }


async def install_packages(
    packages: list[str],
    prefix: str | None = None,
    environment: str | None = None,
    channels: list[str] | None = None,
    override_channels: bool = False,
) -> dict:
    """
    Installs additional packages into an existing conda environment.

    WHEN TO USE:
    - User needs to add new packages to their current project
    - User encounters import errors and needs missing dependencies
    - User wants to expand environment capabilities (e.g., add visualization tools)
    - User explicitly requests package installation

    WORKFLOW GUIDANCE:
    1. If environment isn't specified, ask which environment to install into
    2. Verify packages are available in configured channels before attempting installation
    3. If installing multiple related packages, install them together in one call
    4. After installation, confirm which packages were installed and their versions

    CHANNEL COMPLIANCE:
    - Only install packages from user's configured channels
    - If a package isn't available, explain the issue and suggest alternatives
    - Use override_channels only when user explicitly specifies different channels

    COMMON USE CASES:
    - "Install pandas and numpy" → install_packages(["pandas", "numpy"], environment="my-env")
    - "Add matplotlib for plotting" → install_packages(["matplotlib"], environment="current-project")
    - "I need scikit-learn" → install_packages(["scikit-learn"], environment="ml-project")

    Args:
        packages: List of package names to install (e.g., ["pandas", "numpy", "matplotlib"])
        prefix: Full path to the environment (e.g., "/home/user/envs/myenv")
        environment: Name of the environment (e.g., "data-analysis")
        channels: List of channels to use for package resolution
        override_channels: When True, use ONLY the specified channels (ignoring configured defaults)

    Note: Provide either environment name OR prefix, not both. If prefix is provided, it takes precedence.
    """
    if prefix is None and environment is None:
        return {"is_error": True, "error_description": "No prefix or environment specified", "tool_result": None}

    if err := _reject_option_like([environment, prefix], kind="environment name or prefix"):
        return {"is_error": True, "error_description": err, "tool_result": None}
    if err := _reject_option_like(packages, kind="package spec"):
        return {"is_error": True, "error_description": err, "tool_result": None}
    if err := _reject_option_like(channels, kind="channel"):
        return {"is_error": True, "error_description": err, "tool_result": None}

    try:
        args = ["install", "-y"]
        if prefix:
            args += ["-p", prefix]
        elif environment:
            args += ["-n", environment]

        if channels:
            for ch in channels:
                args += ["-c", ch]
            if override_channels:
                args.append("--override-channels")

        result = await run_conda(*args, positionals=packages)
        message = (
            result["message"]
            if isinstance(result, dict) and "message" in result
            else f"Package(s) {packages} installed into {environment or prefix}"
        )
        return {"is_error": False, "error_description": "", "tool_result": {"message": message}}
    except RuntimeError as ex:
        return {"is_error": True, "error_description": str(ex), "tool_result": None}
    except Exception as ex:
        logger.error(f"Failed to install packages {packages}: {ex}")
        return {
            "is_error": True,
            "error_description": "It was not possible to install the packages.",
            "tool_result": None,
        }


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
async def remove_packages(
    environment: str | None = None,
    prefix: str | None = None,
    packages: list[str] | None = None,
) -> dict:
    """
    Removes one or more packages from an existing conda environment.

    WHEN TO USE:
    - User wants to remove unnecessary or conflicting packages
    - User needs to free up space by removing unused dependencies
    - User explicitly requests to uninstall/remove specific packages
    - User is troubleshooting package conflicts and needs to remove problematic packages
    - User wants to downgrade by removing current version before installing older one

    WORKFLOW GUIDANCE:
    1. ALWAYS confirm with the user before deletion - this operation removes packages permanently
    2. Verify the package names are correct (check for typos)
    3. Show which packages will be removed from which environment
    4. Warn if removing packages that might break dependencies
    5. After deletion, confirm which packages were successfully removed

    SAFETY CONSIDERATIONS:
    - Removing packages may break other packages that depend on them
    - Conda will typically remove dependent packages automatically - warn user about this
    - Cannot undo package removal (would need to reinstall)
    - If user seems uncertain about impact, suggest they verify dependencies first

    COMMON USE CASES:
    - "Remove pandas from my environment" → remove_packages(environment="data-project", packages=["pandas"])
    - "Uninstall tensorflow" → remove_packages(environment="ml-env", packages=["tensorflow"])
    - "Delete old-package and unused-lib" → remove_packages(
        environment="current", packages=["old-package", "unused-lib"]
        )

    TROUBLESHOOTING SCENARIOS:
    - Package conflicts: User wants to remove conflicting version
    - Space management: User needs to free up disk space
    - Clean slate: User wants minimal environment and will reinstall only what's needed

    Args:
        environment: Name of the environment (e.g., "data-analysis", "web-scraping")
        prefix: Full path to the environment (e.g., "/home/user/envs/myenv")
        packages: List of package names to remove (e.g., ["numpy", "pandas", "matplotlib"])

    Note: Provide either environment name OR prefix (not both), plus the packages to remove.

    Returns: A dictionary containing the server response with success status and removed packages
    """
    if packages is None:
        return {
            "is_error": True,
            "error_description": "Provide at least one package name to be deleted",
            "tool_result": None,
        }

    if prefix is None and environment is None:
        return {"is_error": True, "error_description": "No prefix or environment specified", "tool_result": None}

    if err := _reject_option_like([environment, prefix], kind="environment name or prefix"):
        return {"is_error": True, "error_description": err, "tool_result": None}
    if err := _reject_option_like(packages, kind="package spec"):
        return {"is_error": True, "error_description": err, "tool_result": None}

    try:
        args = ["remove", "-y"]
        if prefix:
            args += ["-p", prefix]
        elif environment:
            args += ["-n", environment]

        result = await run_conda(*args, positionals=packages)
        message = (
            result["message"]
            if isinstance(result, dict) and "message" in result
            else f"Package(s) {packages} removed from {environment or prefix}"
        )
        return {"is_error": False, "error_description": "", "tool_result": {"message": message}}
    except RuntimeError as ex:
        return {"is_error": True, "error_description": str(ex), "tool_result": None}
    except Exception as ex:
        logger.error(f"Failed to remove packages: {ex}")
        return {
            "is_error": True,
            "error_description": "There was an error while deleting the packages.",
            "tool_result": None,
        }


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
async def remove_environment(
    environment_name: str | None = None,
    prefix: str | None = None,
) -> dict:
    """
    Removes a conda environment permanently.

    WHEN TO USE:
    - User explicitly requests to delete/remove an environment
    - User wants to clean up unused or outdated environments
    - User is troubleshooting and needs a fresh environment start

    WORKFLOW GUIDANCE:
    1. ALWAYS confirm with the user before deletion - this is a destructive operation
    2. Show the environment name/prefix that will be deleted
    3. Verify this is the correct environment (list contents if unclear)
    4. After deletion, confirm the action was successful

    SAFETY CONSIDERATIONS:
    - This operation is irreversible - all packages and files in the environment will be lost
    - Double-check you're targeting the correct environment
    - If user seems uncertain, suggest listing environments first

    COMMON USE CASES:
    - "Remove the environment my-env"
    - "Delete the environment /User/myuser/anaconda3/env/my-env"
    - "Purge the environment my-env"

    Args:
        environment_name: The name of the environment to delete (e.g., "old-project")
        prefix: The full path to the environment (e.g., "/home/user/envs/myenv")

    Note: Provide either environment_name OR prefix, not both.

    Returns: A dictionary containing the server response to the environment removal
    """
    if (prefix is None and environment_name is None) or (prefix and environment_name):
        return {
            "is_error": True,
            "error_description": "Provide either a prefix or an environment name",
            "tool_result": None,
        }

    if err := _reject_option_like([environment_name, prefix], kind="environment name or prefix"):
        return {"is_error": True, "error_description": err, "tool_result": None}

    try:
        args = ["remove", "--all", "-y"]
        if prefix:
            args += ["-p", prefix]
        elif environment_name:
            args += ["-n", environment_name]

        result = await run_conda(*args)
        result_prefix = result["prefix"] if isinstance(result, dict) and "prefix" in result else (prefix or "")
        return {
            "is_error": False,
            "error_description": "",
            "tool_result": {"message": "Environment removed successfully", "prefix": result_prefix},
        }
    except RuntimeError as ex:
        return {"is_error": True, "error_description": str(ex), "tool_result": None}
    except Exception as ex:
        logger.error(f"Failed to delete the environment: {ex}")
        return {
            "is_error": True,
            "error_description": "There was an error while deleting the environment.",
            "tool_result": None,
        }


# ─── Tool Registration (channel-governed) ────────────────────────────────────
# create_environment / install_packages advertise channels/override_channels only when
# ANACONDA_MCP_ALLOW_CHANNEL_OVERRIDE is set; otherwise those params are stripped from the
# schema and ignored at runtime (managed-channel governance).
for _governed in (create_environment, install_packages):
    mcp.tool(_governed if _ALLOW_CHANNEL_OVERRIDE else _strip_params(_governed, _CHANNEL_PARAMS))
