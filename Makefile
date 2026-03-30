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
MCP_SERVER_PORT   ?= 4041
ENV_NAME ?= anaconda-mcp-dev
CONDA    ?= conda

# Docker settings
DOCKER_IMAGE ?= anaconda-mcp
DOCKER_FROM_SRC ?= false  # Set to 'true' to build from source instead of conda channels

# Anaconda Cloud channel token (required for Docker builds).
# Obtain from the Anaconda Cloud organization administrator.
# Export before building: export ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=<your-token>
ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN ?=

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

# Dev workflow settings (internal tooling — not shipped in the conda package)
# Override SESAME_PATH if Sesame is not installed at the default location.
SESAME_PATH ?=
DEV_WORKFLOW := $(PYTHON) scripts/dev_workflow.py


.PHONY: wheel install install-dev uninstall clean-artifacts clean-dist clean run help mypy mypy-install-types mypy-clean setup clean-setup setup-no-venv activate test test-pytest test-tox test-functional test-integration which-python conda-build conda-install docker-build docker-build-from-source docker-run _check-docker-token gh-install gh-auth sesame-install workflow-setup _workflow-setup-register workflow-setup-desktop workflow-setup-code task-start pr pr-create

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

docker-build: _check-docker-token ## Build the Docker image (requires ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN env var)
	@echo "Building Docker image $(DOCKER_IMAGE)..."
ifeq ($(DOCKER_FROM_SRC),true)
	@echo "Building from source..."
	ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=$(ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN) \
	  docker buildx build \
	    --secret id=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN,env=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN \
	    --build-arg FROM_SOURCE=true \
	    -t $(DOCKER_IMAGE) \
	    --load .
else
	@echo "Building from conda channels..."
	ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=$(ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN) \
	  docker buildx build \
	    --secret id=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN,env=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN \
	    --build-arg FROM_SOURCE=false \
	    -t $(DOCKER_IMAGE) \
	    --load .
endif
	@echo "Done."

_check-docker-token:
	@if [ -z "$(ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN)" ]; then \
		echo "" ; \
		echo "ERROR: ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN is not set." ; \
		echo "" ; \
		echo "This token is required to access the private Anaconda Cloud conda channel." ; \
		echo "Obtain it from the Anaconda Cloud organization administrator, then either:" ; \
		echo "" ; \
		echo "  export ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=<your-token>" ; \
		echo "  make docker-build" ; \
		echo "" ; \
		echo "Or pass it inline:" ; \
		echo "" ; \
		echo "  make docker-build ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=<your-token>" ; \
		echo "" ; \
		exit 1 ; \
	fi

docker-build-from-source: ## Build the Docker image from local source code
	@echo "Building Docker image $(DOCKER_IMAGE) from source..."
	$(MAKE) docker-build DOCKER_FROM_SRC=true

docker-run: ## Run the Docker container in streamable-http mode with port mapping
	@echo "Running $(DOCKER_IMAGE) in streamable-http mode on port 4041..."
	docker run -it -p 4041:4041 --rm $(DOCKER_IMAGE)

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

claude-desktop-setup-config: ## Configure Claude Desktop with Anaconda MCP (STDIO transport)
	@echo "Configuring Claude Desktop with Anaconda MCP..."
	$(PYTHON) -m anaconda_mcp.cli claude-desktop setup-config --force
	@echo "Done. Restart Claude Desktop to apply changes."

claude-desktop-setup-config-http: ## Configure Claude Desktop with Anaconda MCP (HTTP transport)
	@echo "Configuring Claude Desktop with Anaconda MCP (HTTP transport)..."
	$(PYTHON) -m anaconda_mcp.cli claude-desktop setup-config --transport streamable-http --force
	@echo "Done. Restart Claude Desktop to apply changes."
	@echo "Remember to start the server with: make serve"

claude-desktop-show: ## Show current Claude Desktop configuration
	@echo "Current Claude Desktop configuration:"
	$(PYTHON) -m anaconda_mcp.cli claude-desktop show

claude-desktop-remove-config: ## Remove Anaconda MCP from Claude Desktop configuration
	@echo "Removing Anaconda MCP from Claude Desktop..."
	$(PYTHON) -m anaconda_mcp.cli claude-desktop remove-config
	@echo "Done."

claude-desktop-path: ## Show Claude Desktop config file path
	@echo "Claude Desktop config file path:"
	$(PYTHON) -m anaconda_mcp.cli claude-desktop path

# =============================================================================
# Developer workflow (internal Anaconda tooling — NOT shipped in the conda pkg)
# No API key required — uses your Claude Desktop or Claude Code Business subscription.
# Requires: Sesame installed  |  gh CLI authenticated
# Override sesame location with: make task-start TICKET=PROJ-123 SESAME_PATH=/path/to/sesame
# =============================================================================

gh-install: ## [internal] Install gh CLI via conda-forge into the current conda environment
	@echo "Installing gh CLI from conda-forge..."
	$(CONDA) install -c conda-forge gh -y
	@echo "✅  gh installed. Run 'make gh-auth' to authenticate."

gh-auth: ## [internal] Authenticate gh CLI with GitHub (opens browser)
	@echo "Authenticating gh CLI with GitHub..."
	@gh auth login

sesame-install: ## [internal] Install or update Sesame on this machine (requires gh CLI authenticated)
	@echo "Installing Sesame..."
	@gh api repos/Anaconda-Sandbox/sesame/contents/install \
		-H "Accept: application/vnd.github.raw+json" | bash
	@echo "✅  Sesame installed. Default binary: ~/.local/share/sesame/venv/bin/sesame"

workflow-setup: gh-install gh-auth sesame-install _workflow-setup-register ## [internal] Full onboarding: install gh, authenticate, install Sesame, register in Claude Desktop + Claude Code
	@echo ""
	@echo "✅  Onboarding complete! Restart Claude Desktop to apply changes."
	@echo "    Then run: make task-start TICKET=<your-ticket>"

_workflow-setup-register: ## [internal] Register Sesame in Claude Desktop + Claude Code (run once after cloning)
	@$(DEV_WORKFLOW) setup $(if $(SESAME_PATH),--sesame-path $(SESAME_PATH),)

workflow-setup-desktop: ## [internal] Register Sesame in Claude Desktop only
	@$(DEV_WORKFLOW) setup --target claude-desktop $(if $(SESAME_PATH),--sesame-path $(SESAME_PATH),)

workflow-setup-code: ## [internal] Register Sesame in Claude Code only
	@$(DEV_WORKFLOW) setup --target claude-code $(if $(SESAME_PATH),--sesame-path $(SESAME_PATH),)


task-start: ## [internal] Generate task context prompt for Claude + create branch (TICKET=PROJ-123)
	@if [ -z "$(TICKET)" ]; then \
		echo "❌  Usage: make task-start TICKET=PROJ-123"; exit 1; \
	fi
	@$(DEV_WORKFLOW) task $(TICKET) $(if $(SESAME_PATH),--sesame-path $(SESAME_PATH),)

pr: ## [internal] Write .pr-prompt.md and print one-liner for Claude (Sesame + Filesystem required)
	@$(DEV_WORKFLOW) pr $(if $(SESAME_PATH),--sesame-path $(SESAME_PATH),) $(if $(TITLE),--title "$(TITLE)",)

pr-create: ## [internal] Open the draft PR once Claude has written .pr-description.md
	@$(DEV_WORKFLOW) pr-create $(if $(TITLE),--title "$(TITLE)",)

help: ## List all options in the Makefile
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
