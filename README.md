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