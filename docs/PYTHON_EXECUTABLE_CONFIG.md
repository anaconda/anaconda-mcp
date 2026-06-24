# Python Executable Configuration

The `anaconda-mcp` package spawns the conda sub-server (`anaconda_mcp.conda_mcp_lite`) as a stdio subprocess. To ensure this subprocess uses the correct Python interpreter, especially in restricted environments like Claude Desktop, we support multiple configuration methods.

## Configuration Methods (Priority Order)

### Environment Variable Handling

The `PYTHON_EXECUTABLE` environment variable is automatically loaded via Pydantic Settings with the `ANACONDA_MCP_` prefix. This means:

- **Direct usage:** `ANACONDA_MCP_PYTHON_EXECUTABLE=/path/to/python`
- **Auto-prefixed:** The `Settings` class handles the prefix automatically
- **Type validation:** Pydantic ensures the value is a valid string or None

### 1. Environment Variable (Highest Priority)

Set the `ANACONDA_MCP_PYTHON_EXECUTABLE` environment variable:

```bash
export ANACONDA_MCP_PYTHON_EXECUTABLE=/path/to/your/python
python -m anaconda_mcp serve
```

**Claude Desktop Config Example:**
```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/Users/user/anaconda3/envs/myenv/bin/python",
      "args": ["-m", "anaconda_mcp", "serve"],
      "env": {
        "ANACONDA_MCP_PYTHON_EXECUTABLE": "/Users/user/anaconda3/envs/myenv/bin/python",
        "MCP_COMPOSE_CONFIG_DIR": "/Users/user/anaconda3/envs/myenv/lib/python3.12/site-packages/anaconda_mcp"
      }
    }
  }
}
```

### 2. Automatic Detection (Default)

If no environment variable is set, `anaconda-mcp` automatically uses `sys.executable` - the same Python interpreter that's running `anaconda-mcp` itself.

```bash
# No configuration needed!
python -m anaconda_mcp serve
```

**Claude Desktop Config Example:**
```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/Users/user/anaconda3/envs/myenv/bin/python",
      "args": ["-m", "anaconda_mcp", "serve"]
    }
  }
}
```

## How It Works

1. **Template-Based Rendering**: The `mcp_compose.toml.template` file contains a `{{PYTHON_EXECUTABLE}}` placeholder
2. **Runtime Resolution**: At startup, `anaconda-mcp` renders the template to a temporary file, replacing the placeholder with:
   - The value of `ANACONDA_MCP_PYTHON_EXECUTABLE` if set, or
   - The value of `sys.executable` (the current Python interpreter)
3. **Subprocess Spawning**: The rendered config is used to spawn subprocesses with the correct Python path

## Use Cases

### Use Case 1: Same Environment (Most Common)

Both `anaconda-mcp` and the conda sub-server are in the same conda environment.

**Solution:** No configuration needed! Just use the Python from that environment:

```json
{
  "command": "/path/to/env/bin/python",
  "args": ["-m", "anaconda_mcp", "serve"]
}
```

### Use Case 2: Different Environments

You want `anaconda-mcp` to run in one environment but spawn servers in a different environment.

**Solution:** Set the environment variable:

```json
{
  "command": "/path/to/env1/bin/python",
  "args": ["-m", "anaconda_mcp", "serve"],
  "env": {
    "ANACONDA_MCP_PYTHON_EXECUTABLE": "/path/to/env2/bin/python"
  }
}
```

### Use Case 3: System Python vs Conda Environment

You're running `anaconda-mcp` with system Python but want subprocesses to use conda environment Python.

**Solution:** Set the environment variable to point to your conda environment:

```bash
export ANACONDA_MCP_PYTHON_EXECUTABLE=/path/to/conda/env/bin/python
python -m anaconda_mcp serve
```

## Troubleshooting

### Issue: `[Errno 2] No such file or directory: 'python'`

**Cause:** The subprocess can't find the Python executable in PATH.

**Solution:** Either:
1. Use `python -m anaconda_mcp` instead of the `anaconda-mcp` command
2. Set `ANACONDA_MCP_PYTHON_EXECUTABLE` environment variable
3. Ensure you're using the template-based configuration

### Issue: Subprocesses use wrong Python version

**Cause:** Multiple Python installations, and PATH resolution is ambiguous.

**Solution:** Explicitly set `ANACONDA_MCP_PYTHON_EXECUTABLE`:

```bash
which python  # Find your desired Python
export ANACONDA_MCP_PYTHON_EXECUTABLE=/path/shown/above
python -m anaconda_mcp serve
```

## Files Involved

- `config.py` - Contains `Settings` class with `ANACONDA_MCP_PYTHON_EXECUTABLE` field
- `utils.py` - Contains `_render_config_template()` function for template rendering
- `mcp_compose.toml.template` - Template with `{{PYTHON_EXECUTABLE}}` placeholder
- `mcp_compose.toml` - Fallback config (used if template doesn't exist)
- `cli.py` - Calls `_render_config_template()` in the `serve` command

## Development Notes

If you're modifying the configuration:

1. **Edit the template file**: `mcp_compose.toml.template` (NOT `mcp_compose.toml`)
2. Use `{{PYTHON_EXECUTABLE}}` wherever you need the Python path
3. The template is automatically rendered at runtime - changes take effect immediately on next run
4. The `mcp_compose.toml` file is only used as a fallback if the template doesn't exist

**Important**: Any changes to `mcp_compose.toml` will be ignored if `mcp_compose.toml.template` exists, since the template takes precedence.

Example command in template:
```toml
command = ["{{PYTHON_EXECUTABLE}}", "-m", "anaconda_mcp.conda_mcp_lite"]
```

### Adding More Placeholders

If you need to add more dynamic configuration:

1. Add the setting to `config.py`:
   ```python
   class Settings(BaseSettings):
       ANACONDA_MCP_CUSTOM_VALUE: str | None = None
   ```

2. Add placeholder to template:
   ```toml
   custom_setting = "{{CUSTOM_VALUE}}"
   ```

3. Update `utils.py` to replace the placeholder:
   ```python
   content = content.replace('{{CUSTOM_VALUE}}', settings.ANACONDA_MCP_CUSTOM_VALUE or 'default')
   ```
