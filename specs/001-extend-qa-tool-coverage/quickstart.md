# Quickstart: Extend QA Tool Test Coverage

**Branch**: `001-extend-qa-tool-coverage`

## Prerequisites

1. **Test runner environment** (`anaconda-mcp-qa`):
   ```bash
   conda env create -f tests/qa/environment.yml
   conda activate anaconda-mcp-qa
   ```

2. **Server environment** (with all MCP servers):
   ```bash
   conda create -n anaconda-mcp-server python=3.13 -y
   conda activate anaconda-mcp-server
   pip install -e /path/to/anaconda-mcp
   pip install -e /path/to/environments-mcp
   pip install conda-meta-mcp  # provides 'cmm' command
   conda install -c anaconda-cloud -c conda-forge anaconda-connector-conda -y
   ```

3. **Authentication** (for search-mcp):
   ```bash
   export ANACONDA_TOKEN="your-anaconda-api-token"
   ```

4. **Network access**: Required for conda-meta-mcp (public channels) and search-mcp (anaconda.com API)

## Implementation Order

### Phase 1: Positive Tests (all tools)

1. **Extend tool constants** (`tests/qa/mcp_tools/common/constants/mcp_tools.py`):
   - Add missing environments-mcp tools: `CONDA_LIST_ENVIRONMENT_PACKAGES`, `CONDA_REMOVE_PACKAGES`
   - Add `CondaMetaTools` enum (9 tools)
   - Add `SearchTools` enum (5 tools)
   - Add argument enums for each tool

2. **Add test data** (`tests/qa/mcp_tools/common/constants/test_data.py`):
   - conda-meta-mcp: `KNOWN_IMPORT`, `SEARCH_PACKAGE`, `REPOQUERY_SPEC`, etc.
   - search-mcp: `SEARCH_QUERY_*` constants

3. **Create test files** (one per tool):
   - environments-mcp gaps: `test_list_environment_packages.py`, `test_remove_packages.py`, `test_remove_environment_happy.py`
   - conda-meta-mcp: 9 test files (`test_conda_meta_*.py`)
   - search-mcp: 5 test files (`test_search_*.py`)

### Phase 2: Complex Parameter Tests

Add additional test methods for tools with multiple usage patterns:
- `conda_create_environment`: by name, by prefix, with packages, with root_path
- `repoquery`: depends mode, whoneeds mode
- `search_packages`: basic, with channel filter, with platform filter

### Phase 3: Negative Tests

Add error-path test methods to existing files:
- Invalid environment names
- Nonexistent packages
- Empty queries (search-mcp)
- Invalid parameters

### Phase 4: Hang-Stress Tests

Add hang-stress variants for:
- `repoquery` (conda-meta-mcp)
- `search_packages` (search-mcp)

## Test File Template

```python
"""
Happy-path tests for {tool_name} tool.

Tests verify:
- {assertion 1}
- {assertion 2}
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import {ToolEnum}, {ArgsEnum}
from common.constants.test_data import {TEST_DATA}

logger = logging.getLogger(__name__)


@pytest.mark.slow
class Test{ToolName}:
    """
    Happy-path: {tool_name} with valid input must succeed.
    """

    def test_{scenario}_success(self, call_tool):
        """
        {Description of what this test verifies}.
        """
        response = call_tool(
            {ToolEnum}.{TOOL_NAME},
            {
                {ArgsEnum}.{ARG}: {value},
            },
        )
        # Assertions here
```

## Running Tests

```bash
# All new tests
pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http -k "conda_meta or search"

# Specific tool
pytest tests/qa/mcp_tools/test_conda_meta_repoquery.py -o addopts= --mcp-profile=stdio-http

# Hang-stress only
pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio -m hang_stress

# Skip hang-stress for quick runs
pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http --skip-hang-stress
```

## Validation

After implementation:
1. All 20 tools have at least one passing test
2. Tool coverage table in `test_design.md` updated
3. `mcp_tools.py` contains all 20 tools organized by server
4. Tests pass on declared supported profile (`stdio-http`)
