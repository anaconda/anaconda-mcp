import os
import sys
import tempfile
from pathlib import Path

from anaconda_mcp.config import settings


def _render_config_template(config_path: str) -> str:
    """Render config template by replacing {{PYTHON_EXECUTABLE}} with sys.executable.

    Creates a temporary rendered config file from the template.
    Supports multiple ways to specify the Python executable:
    1. Environment variable: ANACONDA_MCP_PYTHON_EXECUTABLE
    2. sys.executable (default)

    Returns the path to the rendered config file.
    """

    config_file = Path(config_path)

    template_path = config_file.parent / f"{config_file.name}.template"

    # If template exists, use it; otherwise use the config file itself
    source_path = template_path if template_path.exists() else config_file

    if not source_path.exists():
        return config_path

    content = source_path.read_text()

    # Determine which Python executable to use
    # Priority: 1. Environment variable, 2. sys.executable
    python_executable = settings.python_executable or sys.executable

    # Replace the placeholder with the Python executable
    # Escape backslashes for Windows paths
    python_path = python_executable.replace("\\", "\\\\")
    content = content.replace("{{PYTHON_EXECUTABLE}}", python_path)
    content = content.replace('"python"', f'"{python_path}"')  # Fallback for non-template

    rendered_fd, rendered_path = tempfile.mkstemp(suffix=".toml", prefix="mcp_compose_")
    try:
        with open(rendered_fd, "w") as f:
            f.write(content)
    except:
        os.close(rendered_fd)
        raise

    return rendered_path
