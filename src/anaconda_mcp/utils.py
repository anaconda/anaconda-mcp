import os
import sys
import tempfile
from pathlib import Path

from anaconda_mcp.config import settings


def _render_config_template(config_path: str) -> str:
    """Render config template by replacing placeholders with runtime values.

    Creates a temporary rendered config file from the template.
    Supports the following placeholders:
    - {{PYTHON_EXECUTABLE}}: Python interpreter path
    - {{ANACONDA_DOMAIN}}: Anaconda domain (anaconda.com or stage.anaconda.com)
    - {{ANACONDA_TOKEN}}: Anaconda API token for authenticated services

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
    python_executable = settings.PYTHON_EXECUTABLE or sys.executable

    # Replace the placeholder with the Python executable
    # Escape backslashes for Windows paths
    python_path = python_executable.replace("\\", "\\\\")
    content = content.replace("{{PYTHON_EXECUTABLE}}", python_path)
    content = content.replace('"python"', f'"{python_path}"')  # Fallback for non-template

    # Replace Anaconda domain placeholder
    anaconda_domain = settings.ANACONDA_DOMAIN or "anaconda.com"
    content = content.replace("{{ANACONDA_DOMAIN}}", anaconda_domain)

    # Replace Anaconda token placeholder
    # Priority: 1. ANACONDA_MCP_ANACONDA_TOKEN, 2. ANACONDA_TOKEN env var
    anaconda_token = os.environ.get("ANACONDA_MCP_ANACONDA_TOKEN") or os.environ.get("ANACONDA_TOKEN", "")
    content = content.replace("{{ANACONDA_TOKEN}}", anaconda_token)

    rendered_fd, rendered_path = tempfile.mkstemp(suffix=".toml", prefix="mcp_compose_")
    try:
        with open(rendered_fd, "w") as f:
            f.write(content)
    except:
        os.close(rendered_fd)
        raise

    return rendered_path
