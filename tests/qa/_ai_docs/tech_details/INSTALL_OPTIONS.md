# Installation Options

## Option A: Install from Conda Channels

**Use when**: Testing a published release version. No codebase needed.

```bash
# Create environment with all dependencies
conda create --name anaconda-mcp-testing \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  anaconda-mcp environments-mcp-server

# Activate
conda activate anaconda-mcp-testing

# Verify
anaconda-mcp --help

# Check installed versions
conda list | grep -E "anaconda-mcp|environments-mcp"
```

To install specific versions (package and/or Python):
```bash
# Specific package versions
conda create --name anaconda-mcp-testing \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  anaconda-mcp=0.1.2 environments-mcp-server=0.1.7

# Specific Python version (e.g., 3.10, 3.11, 3.12, 3.13)
conda create --name anaconda-mcp-py310 \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=3.10 anaconda-mcp environments-mcp-server
```

---

## Option B: Install from Source

**Use when**: Testing unpublished code (specific branch/tag/commit) OR running pytest suite.

### Step 1: Clone and Select Version

```bash
# Clone repository
git clone git@github.com:anaconda/anaconda-mcp.git
cd anaconda-mcp

# Option: Use latest main
git checkout main && git pull

# Option: Use specific tag
git tag --list
git checkout v0.1.2
```

### Step 2: Setup Environment

```bash
# Add required channels
conda config --add channels conda-forge
conda config --add channels datalayer
conda config --add channels anaconda-cloud/label/dev
conda config --add channels 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/'

# Create dev environment
make setup
conda activate anaconda-mcp-dev

# Verify
anaconda-mcp --help

# Check installed versions
conda list | grep -E "anaconda-mcp|environments-mcp"
```

### Step 3: Run Tests (optional)

```bash
# Run pytest suite
make test

# Run with coverage
make test-coverage
```

### Windows Notes

On Windows, use `python -m anaconda_mcp` instead of `anaconda-mcp` CLI (see [PI-001](../_tracking/KNOWN_ISSUES.md#pi-001)).

```cmd
REM Create dev environment
conda env create -f environment-dev.yml
conda activate anaconda-mcp-dev

REM Install in editable mode
pip install -e .

REM Run from source
python -m anaconda_mcp serve --delay 5
```

See [WINDOWS_SETUP.md](./tests/e2e/setup/WINDOWS_SETUP.md) for detailed Windows instructions.

---

## Option C: Install Local mcp-compose for E2E Testing

**Use when**: Testing local mcp-compose changes (e.g., bug fixes, new features) with the full stack.

### Step 1: Create Conda Environment with All Dependencies

```bash
conda create --name anaconda-mcp-rc2-py313 \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=3.13 \
  anaconda-mcp=1.0.0.rc.2 \
  environments-mcp-server=1.0.0.rc.2 \
  anaconda-connector-core=0.1.11 \
  anaconda-connector-conda=0.1.11 \
  anaconda-connector-utilities=0.1.11
```

### Step 2: Install Local mcp-compose

#### Editable Install (Recommended for Development)

```bash
conda activate anaconda-mcp-rc2-py313
pip install -e /path/to/mcp-compose
```

The `-e` (editable) flag uses your local source files directly. Changes to the source are immediately reflected without reinstalling.

#### Regular Install from Local Source

```bash
conda activate anaconda-mcp-rc2-py313
pip install /path/to/mcp-compose
```

This installs a copy. You need to reinstall after each change.

#### PYTHONPATH Override (No Install)

```bash
conda activate anaconda-mcp-rc2-py313
PYTHONPATH=/path/to/mcp-compose python -m mcp_compose ...
```

Temporarily overrides the installed version. Useful for quick tests.

### Verify Installation

Check which mcp-compose is being used:

```bash
python -c "from mcp_compose.http_client import streamable_http_client_compat; import inspect; print(inspect.getfile(streamable_http_client_compat))"
```

**Expected output for editable install:**
```
/path/to/mcp-compose/mcp_compose/http_client.py
```

**Expected output for conda install:**
```
/opt/miniconda3/envs/anaconda-mcp-rc2-py313/lib/python3.13/site-packages/mcp_compose/http_client.py
```

### Reverting to Conda Version

To go back to the conda-installed version:

```bash
pip uninstall mcp-compose
conda install -c datalayer mcp-compose
```
