import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from anaconda_mcp.utils import _render_config_template


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory for config files."""
    return tmp_path


@pytest.fixture
def sample_template(temp_config_dir):
    """Create a sample template file."""
    template_content = """
[composer]
name = "test-server"

[[servers.proxied.streamable-http]]
name = "test"
command = ["{{PYTHON_EXECUTABLE}}", "-m", "test_module"]
"""
    template_path = temp_config_dir / "config.toml.template"
    template_path.write_text(template_content)
    return str(temp_config_dir / "config.toml")


@pytest.fixture
def sample_config_with_python(temp_config_dir):
    """Create a sample config file with 'python' literal."""
    config_content = """
[composer]
name = "test-server"

[[servers.proxied.streamable-http]]
name = "test"
command = ["python", "-m", "test_module"]
"""
    config_path = temp_config_dir / "config.toml"
    config_path.write_text(config_content)
    return str(config_path)


def test_render_template_with_placeholder(sample_template):
    """Test that template placeholders are replaced with sys.executable."""
    with patch("anaconda_mcp.utils.get_auth_token", return_value="fake-token"):
        rendered_path = _render_config_template(sample_template)

    try:
        with open(rendered_path) as f:
            content = f.read()

        # Check that placeholder was replaced
        assert "{{PYTHON_EXECUTABLE}}" not in content
        assert sys.executable.replace("\\", "\\\\") in content or sys.executable in content
        assert "-m" in content
        assert "test_module" in content
    finally:
        # Cleanup
        Path(rendered_path).unlink(missing_ok=True)


def test_render_template_with_env_var(sample_template, monkeypatch):
    """Test that environment variable takes precedence."""
    custom_python = "/custom/path/to/python"

    # Mock the settings object with proper attribute
    with (
        patch("anaconda_mcp.utils.settings") as mock_settings,
        patch("anaconda_mcp.utils.get_auth_token", return_value="fake-token"),
    ):
        mock_settings.configure_mock(python_executable=custom_python, anaconda_domain="anaconda.com")

        rendered_path = _render_config_template(sample_template)

        try:
            with open(rendered_path) as f:
                content = f.read()

            # Check that custom path was used
            assert custom_python in content
            assert sys.executable not in content or sys.executable == custom_python
        finally:
            Path(rendered_path).unlink(missing_ok=True)


def test_render_fallback_to_sys_executable(sample_template):
    """Test that sys.executable is used when no env var is set."""
    with (
        patch("anaconda_mcp.utils.settings") as mock_settings,
        patch("anaconda_mcp.utils.get_auth_token", return_value="fake-token"),
    ):
        mock_settings.configure_mock(python_executable=None, anaconda_domain="anaconda.com")

        rendered_path = _render_config_template(sample_template)

        try:
            with open(rendered_path) as f:
                content = f.read()

            # Should use sys.executable
            assert sys.executable.replace("\\", "\\\\") in content or sys.executable in content
        finally:
            Path(rendered_path).unlink(missing_ok=True)


def test_render_python_literal_fallback(sample_config_with_python):
    """Test that 'python' literal is replaced even without template."""
    with patch("anaconda_mcp.utils.get_auth_token", return_value="fake-token"):
        rendered_path = _render_config_template(sample_config_with_python)

    try:
        with open(rendered_path) as f:
            content = f.read()

        # The function should replace "python" with sys.executable
        lines_with_python = [line for line in content.split("\n") if "python" in line.lower()]
        # Should have the command line with sys.executable instead of just "python"
        assert any(sys.executable in line or sys.executable.replace("\\", "\\\\") in line for line in lines_with_python)
    finally:
        Path(rendered_path).unlink(missing_ok=True)


def test_render_nonexistent_config(temp_config_dir):
    """Test that function handles nonexistent config gracefully."""
    nonexistent = str(temp_config_dir / "nonexistent.toml")
    result = _render_config_template(nonexistent)

    assert result == nonexistent


def test_render_creates_temp_file(sample_template):
    """Test that rendered config is written to a temp file."""
    with patch("anaconda_mcp.utils.get_auth_token", return_value="fake-token"):
        rendered_path = _render_config_template(sample_template)

    try:
        assert rendered_path.startswith(tempfile.gettempdir())
        assert "mcp_compose_" in rendered_path
        assert rendered_path.endswith(".toml")

        assert Path(rendered_path).exists()
    finally:
        Path(rendered_path).unlink(missing_ok=True)


def test_render_template_preserves_structure(sample_template):
    """Test that template rendering preserves TOML structure."""

    # when
    with patch("anaconda_mcp.utils.get_auth_token", return_value="fake-token"):
        rendered_path = _render_config_template(sample_template)

    try:
        # then
        with open(rendered_path) as f:
            content = f.read()
        assert "[composer]" in content
        assert "name = " in content
        assert "[[servers.proxied.streamable-http]]" in content
        assert "command = [" in content
    finally:
        Path(rendered_path).unlink(missing_ok=True)
