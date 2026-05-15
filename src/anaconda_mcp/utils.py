import os
import sys
import tempfile
from pathlib import Path

from anaconda_mcp.config import settings


def _render_config_template(config_path: str) -> str:
    """Render config template by replacing placeholders with runtime values.

    Creates a temporary rendered config file from the template.
    Placeholders:
        {{PYTHON_EXECUTABLE}} - resolved from ANACONDA_MCP_PYTHON_EXECUTABLE or sys.executable
        {{ANACONDA_TOKEN}} - resolved from anaconda-auth token (empty string if not authenticated)
        {{ANACONDA_DOMAIN}} - resolved from settings.ANACONDA_DOMAIN (e.g. anaconda.com, stage.anaconda.com)

    Returns the path to the rendered config file.
    """
    from anaconda_mcp.auth import get_auth_token

    config_file = Path(config_path)

    template_path = config_file.parent / f"{config_file.name}.template"

    source_path = template_path if template_path.exists() else config_file

    if not source_path.exists():
        return config_path

    content = source_path.read_text()

    python_executable = settings.PYTHON_EXECUTABLE or sys.executable
    python_path = python_executable.replace("\\", "\\\\")
    content = content.replace("{{PYTHON_EXECUTABLE}}", python_path)
    content = content.replace('"python"', f'"{python_path}"')

    anaconda_token = get_auth_token()
    if anaconda_token is None:
        raise RuntimeError("Not authenticated with Anaconda. Run 'anaconda-auth login' or sign in when prompted.")
    content = content.replace("{{ANACONDA_TOKEN}}", anaconda_token)

    content = content.replace("{{ANACONDA_DOMAIN}}", settings.ANACONDA_DOMAIN or "anaconda.com")

    rendered_fd, rendered_path = tempfile.mkstemp(suffix=".toml", prefix="mcp_compose_")
    try:
        with open(rendered_fd, "w") as f:
            f.write(content)
    except:
        os.close(rendered_fd)
        raise

    return rendered_path
