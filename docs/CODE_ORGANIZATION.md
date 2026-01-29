# Code Organization for Python Executable Configuration

## Module Structure

```
src/anaconda_mcp/
├── config.py                      # Configuration management
│   └── Settings class
│       └── ANACONDA_MCP_PYTHON_EXECUTABLE field
│
├── utils.py                       # Utility functions
│   └── _render_config_template()
│       ├── Reads template or fallback config
│       ├── Gets python_executable from settings
│       └── Returns path to rendered temp file
│
├── cli.py                         # CLI commands
│   └── serve() command
│       ├── Imports _render_config_template
│       └── Calls it before starting server
│
└── mcp_compose.toml.template     # Template file
    └── Contains {{PYTHON_EXECUTABLE}} placeholder
```

## Data Flow

```
1. User runs command
   ↓
2. Pydantic Settings loads ANACONDA_MCP_PYTHON_EXECUTABLE from environment
   ↓
3. cli.serve() calls _render_config_template(config_path)
   ↓
4. utils._render_config_template():
   - Checks for .toml.template file
   - Reads settings.ANACONDA_MCP_PYTHON_EXECUTABLE or sys.executable
   - Replaces {{PYTHON_EXECUTABLE}} placeholder
   - Writes to temporary file
   - Returns temp file path
   ↓
5. mcp-compose uses rendered config
   ↓
6. Subprocess spawns with correct Python interpreter
```

## Environment Variable Loading

```python
# config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=f"{ENV_VAR_PREFIX}_",  # "ANACONDA_MCP_"
        env_file=".env",
    )
    PYTHON_EXECUTABLE: str | None = None
```

**How it works:**
- Pydantic automatically reads `ANACONDA_MCP_ANACONDA_MCP_PYTHON_EXECUTABLE` from environment
- Returns `None` if not set (handled gracefully in utils.py)

## Template Rendering

```python
# utils.py
def _render_config_template(config_path: str) -> str:
    python_executable = settings.PYTHON_EXECUTABLE or sys.executable
    # ... render template ...
    return rendered_path
```

**Priority logic:**
1. Use `settings.ANACONDA_MCP_PYTHON_EXECUTABLE` if set
2. Fall back to `sys.executable`
3. Handle Windows path escaping
4. Write to temp file (thread-safe)
