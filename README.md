# anaconda-mcp

## Installation & Usage

### For pip users:
```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Or using uv
uv pip install -e ".[dev]"
```

### For conda users:
```bash
# Create/update development environment
conda env create -f environment-dev.yml

# Or update existing environment
conda env update -f environment-dev.yml --prune

# Activate
conda activate anaconda-mcp-dev
```

### Using the Makefile:
```bash
# Setup conda dev environment
make setup

# Install pre-commit hooks
make pre-commit-install

# Run tests
make test

# Run linting
make lint

# Auto-fix and format code
make ruff-fix

# Run type checking
make mypy

# Run all pre-commit checks
make pre-commit-all
```

## Pre-commit Workflow

1. Install hooks:
   ```bash
   make pre-commit-install
   ```

2. Hooks will run automatically on `git commit`

3. Run manually on all files:
   ```bash
   make pre-commit-all
   ```

4. Update hooks to latest versions:
   ```bash
   make pre-commit-update
   ```

## Testing Workflow

1. Run all tests:
   ```bash
   make test
   ```

2. Run with coverage:
   ```bash
   make test-coverage
   ```

3. Run specific test markers:
   ```bash
   make test-functional
   make test-integration
   ```

## Code Quality Workflow

1. Check code quality:
   ```bash
   make lint         # Check with Ruff
   make mypy         # Check types
   ```

2. Auto-fix issues:
   ```bash
   make ruff-fix     # Fix and format
   ```

3. Format only:
   ```bash
   make format
   ```

# CLI Quick Reference

## Commands

### serve
Start MCP servers from configuration file.

```bash
anaconda-mcp serve [--config PATH] [--host HOST] [--port PORT]
```

**Examples:**
```bash
anaconda-mcp serve
anaconda-mcp serve --port 8888
anaconda-mcp -v serve --config custom.toml
```

### compose
Compose multiple MCP servers into one.

```bash
anaconda-mcp compose [OPTIONS]
```

**Options:**
- `-p, --pyproject PATH` - Path to pyproject.toml
- `-n, --name NAME` - Name for composed server
- `-c, --conflict-resolution STRATEGY` - Conflict strategy (prefix/suffix/ignore/error/override)
- `--include SERVER` - Include specific servers (repeatable)
- `--exclude SERVER` - Exclude specific servers (repeatable)
- `-o, --output PATH` - Output file
- `--output-format FORMAT` - Output format (text/json)

**Examples:**
```bash
anaconda-mcp compose
anaconda-mcp compose --name my-server
anaconda-mcp compose --include conda_environments --include jupyter_server
anaconda-mcp compose --exclude legacy_server
anaconda-mcp compose --conflict-resolution prefix --output composed.json --output-format json
```

### discover
Discover available MCP servers.

```bash
anaconda-mcp discover [--pyproject PATH] [--output-format FORMAT]
```

**Examples:**
```bash
anaconda-mcp discover
anaconda-mcp discover --output-format json
anaconda-mcp discover -p /path/to/pyproject.toml
```

## Global Options

```bash
-h, --help          Show help
-v, --verbose       Enable verbose logging
```