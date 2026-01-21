export PYTHONPATH := src

.DEFAULT_GOAL := help
ifdef CONDA_PREFIX
  PYTHON ?= $(CONDA_PREFIX)/bin/python
else
  PYTHON ?= $(shell command -v python3 2>/dev/null || command -v python)
endif
PIP := $(PYTHON) -m pip
PROJECT := anaconda-mcp
DIST_DIR := dist
BUILD_DIR := build
MCP_SERVER_PORT   ?= 8888
ENV_NAME ?= anaconda-mcp-dev
CONDA    ?= conda

PRE_COMMIT ?= $(PYTHON) -m pre_commit
RUFF       ?= $(PYTHON) -m ruff
MYPY       ?= $(PYTHON) -m mypy
PYTEST     ?= $(PYTHON) -m pytest
TOX        ?= $(PYTHON) -m tox

MYPY_SRCS ?= src
RUFF_SRCS ?= src tests
MYPY_ARGS ?=
MYPY_CACHE ?= .mypy_cache

# Conda build settings
CONDA_BUILD_DIR := build/conda
CONDA_RECIPE_DIR := conda-build


.PHONY: wheel install install-dev uninstall clean-artifacts clean-dist clean run help mypy mypy-install-types mypy-clean setup clean-setup setup-no-venv activate test test-pytest test-tox test-functional test-integration which-python conda-build conda-install

which-python: ## Show Python executable being used
	@echo "PYTHON      = $(PYTHON)"
	@$(PYTHON) -c "import sys; print('sys.executable =', sys.executable)"
	@echo "CONDA_PREFIX= '$(CONDA_PREFIX)'"


clean-artifacts: ## Remove build artifacts and __pycache__
	@echo "Cleaning build artifacts..."
	rm -rf $(DIST_DIR) $(BUILD_DIR) *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo "Done."

clean-cache: ## Clean pytest, mypy, ruff caches
	@echo "Cleaning caches..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache .tox
	@echo "Done."

clean: clean-artifacts clean-cache ## Clean all build artifacts and caches

clean-dist: clean ## Clean + purge pip cache (best-effort)
	-$(PIP) cache purge || true

wheel: clean-artifacts ## Build a fresh wheel (isolated build)
	@echo "Ensuring build frontend..."
	$(PIP) install --upgrade build
	@echo "Building wheel (isolated env)…"
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m build --wheel
	@ls -lh $(DIST_DIR)/*.whl

install: wheel ## Build and install the package (production)
	@echo "Uninstalling previous $(PROJECT) (if any)…"
	-$(PIP) uninstall -y $(PROJECT) || true
	@echo "Installing new wheel (force, no cache)…"
	PIP_NO_CACHE_DIR=1 $(PIP) install --upgrade --force-reinstall $(DIST_DIR)/*.whl
	@echo "Installed."

install-dev: ## Install package in development mode with dev dependencies
	@echo "Installing $(PROJECT) in development mode with dev dependencies..."
	$(PIP) install -e ".[dev]"
	@echo "Installed."

uninstall: ## Uninstall the package from the current Python environment
	$(PIP) uninstall -y $(PROJECT)

run: ## Start the anaconda-mcp CLI
	@echo "Starting anaconda-mcp..."
	$(PYTHON) -m anaconda_mcp.cli

test: test-pytest ## Run all tests (alias for test-pytest)

test-pytest: ## Run all tests with pytest (current activated env)
	@echo "Running tests with pytest…"
	$(PYTEST) -s -vvv $(ARGS)

test-tox: ## Run tests using tox (matrix from tox.ini)
	@echo "Running tests with tox…"
	$(TOX) $(ARGS)

test-functional: ## Run only @pytest.mark.functional tests
	@echo "Running functional tests…"
	$(PYTEST) -s -vvv -m "functional and not integration" $(ARGS)

test-integration: ## Run only @pytest.mark.integration tests
	@echo "Running integration tests…"
	$(PYTEST) -s -vvv -m "integration and not functional" $(ARGS)

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage…"
	$(PYTEST) --cov=anaconda_mcp --cov-report=html --cov-report=term $(ARGS)

## Lint with Ruff (check only)
ruff ruff-check: ## Run Ruff checks (no changes)
	$(RUFF) check $(RUFF_SRCS) $(ARGS)

## Auto-fix with Ruff (no formatting)
fix: ## Run Ruff with --fix (auto-fix issues, no formatting)
	$(RUFF) check --fix $(RUFF_SRCS) $(ARGS)

## Auto-fix with Ruff (imports/pyupgrade/errors) and format
ruff-fix: ## Run Ruff with --fix then format
	$(RUFF) check --fix $(RUFF_SRCS) $(ARGS)
	$(RUFF) format $(RUFF_SRCS)

## Format only (no lint fixes)
format: ## Apply code formatting only
	$(RUFF) format $(RUFF_SRCS)

## Convenience alias to run all code-quality checks (no changes)
lint: ## Run static checks (Ruff)
	$(RUFF) check $(RUFF_SRCS)

## Install git hooks locally
pre-commit-install: ## Install pre-commit git hooks
	$(PRE_COMMIT) install

## Update hook versions in .pre-commit-config.yaml
pre-commit-update: ## Update pre-commit hooks to latest revisions
	$(PRE_COMMIT) autoupdate

## Run pre-commit on staged files
pre-commit: ## Run pre-commit on staged files
	$(PRE_COMMIT) run

## Run pre-commit on the entire repo (what CI usually does)
pre-commit-all: ## Run pre-commit on all files
	$(PRE_COMMIT) run --all-files

## Remove pre-commit caches (useful when hooks change a lot)
pre-commit-clean: ## Clear pre-commit cache
	$(PRE_COMMIT) clean

mypy: ## Run static type checks (mypy)
	$(MYPY) $(MYPY_ARGS) $(MYPY_SRCS)

mypy-install-types: ## Install missing type stubs (non-interactive)
	$(MYPY) --install-types --non-interactive $(MYPY_SRCS)

mypy-clean: ## Remove mypy cache
	rm -rf $(MYPY_CACHE)

shell: ## Open IPython with PYTHONPATH=src pre-set
	@echo "Launching IPython with PYTHONPATH=src"
	PYTHONPATH=src $(PYTHON) -m IPython

shell-reload: ## IPython with PYTHONPATH=src and autoreload enabled
	PYTHONPATH=src $(PYTHON) -m IPython --ext autoreload --InteractiveShellApp.exec_lines="%autoreload 2"

conda-build: ## Build conda package
	@echo "Building conda package..."
	@mkdir -p $(CONDA_BUILD_DIR)
	$(CONDA) build $(CONDA_RECIPE_DIR) --output-folder $(CONDA_BUILD_DIR)
	@echo "Conda package built in $(CONDA_BUILD_DIR)"

conda-install: conda-build ## Build and install conda package locally
	@echo "Installing conda package..."
	$(CONDA) install --use-local $(PROJECT) -y
	@echo "Done."

conda-index: ## Index the local conda channel
	@echo "Indexing conda channel..."
	$(CONDA) index $(CONDA_BUILD_DIR)
	@echo "Done."

setup: ## Create or update the dev conda env from environment-dev.yml
	@echo "Setting up Conda env: $(ENV_NAME)"
	@if $(CONDA) env list | awk '{print $$1}' | grep -qx '$(ENV_NAME)'; then \
		echo "Environment exists. Updating…"; \
		$(CONDA) env update -n $(ENV_NAME) -f environment-dev.yml --prune; \
	else \
		echo "Environment not found. Creating…"; \
		$(CONDA) env create -n $(ENV_NAME) -f environment-dev.yml; \
	fi
	@echo "Done. Activate with: conda activate $(ENV_NAME)"

setup-prod: ## Create or update production conda env from environment.yml
	@echo "Setting up production Conda env: $(PROJECT)"
	@if $(CONDA) env list | awk '{print $$1}' | grep -qx '$(PROJECT)'; then \
		echo "Environment exists. Updating…"; \
		$(CONDA) env update -n $(PROJECT) -f environment.yml --prune; \
	else \
		echo "Environment not found. Creating…"; \
		$(CONDA) env create -n $(PROJECT) -f environment.yml; \
	fi
	@echo "Done. Activate with: conda activate $(PROJECT)"

clean-setup: ## Remove the dev conda env and all build artifacts/dist (fresh start)
	@echo "Removing Conda env: $(ENV_NAME) (if present)…"
	-$(CONDA) env remove -n $(ENV_NAME) -y >/dev/null 2>&1 || true
	@$(MAKE) clean
	@echo "Clean reset complete."

activate: ## Show activation command (must be run manually)
	@echo "To activate the development environment, run:"
	@echo "  conda activate $(ENV_NAME)"

help: ## List all options in the Makefile
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
