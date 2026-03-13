# DESK-1401: conda_create_environment returns 403 Forbidden despite valid authentication

**Jira**: [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401)

**Severity**: Major

**Platform**: macOS

**Version**:
- anaconda-mcp: 1.0.0.rc.2
- environments-mcp-server: 1.0.0.rc.2
- anaconda-auth: 0.13.1.dev3

## Description

MCP conda operations that require channel access fail with HTTP 403 Forbidden on `repo.anaconda.cloud`, even though authentication is fully configured and the same operations succeed in terminal.

## Affected Operations

| Operation | Status | Requires Channel Access |
|-----------|--------|------------------------|
| `conda_list_environments` | Works | No — reads local environment registry |
| `conda_list_environment_packages` | Works | No — reads installed package metadata from disk |
| `conda_remove_environment` | Works | No — deletes environment folder from disk |
| `conda_create_environment` | 403 | Yes — downloads repodata.json + packages |
| `conda_install_packages` | 403 | Yes — downloads repodata.json + packages |
| `conda_remove_packages` | 403 | Yes — downloads repodata.json for dependency solving |

**Pattern**: Any operation requiring contact with `repo.anaconda.cloud` fails with 403. Operations that only access local filesystem succeed.

## Reproduction

**Option A — Standard prerequisites:**
```bash
anaconda login
anaconda whoami                          # verify logged in
anaconda token install                   # install token
anaconda token config                    # configure channels
conda config --show default_channels     # verify repo.anaconda.cloud
conda config --show channel_settings     # verify anaconda-auth handler
```

**Option B — Manual .condarc adjustment** (if `channel_settings` is empty after Option A):
```bash
# Edit ~/.condarc and add:
channel_settings:
  - channel: https://repo.anaconda.cloud/*
    auth: anaconda-auth
```

**Then:**
1. Restart Claude Desktop
2. Verify terminal works:
   ```bash
   conda activate anaconda-mcp-rc2-py313
   conda create -n test python=3.11 -y   # succeeds
   ```
3. Via Claude Desktop: "Create environment e2e-test with Python 3.11" — **403 Forbidden**

## Evidence

| Check | Result |
|-------|--------|
| `anaconda-auth` in MCP env | installed (0.13.1.dev3) |
| `anaconda whoami` from MCP env | authenticated |
| `channel_settings` configured | `anaconda-auth` handler |
| `default_channels` | points to `repo.anaconda.cloud` |
| Terminal `conda create` | works |
| MCP `conda_create_environment` | 403 Forbidden |

## Root Cause Hypothesis

`environments-mcp-server` spawns conda in a way that doesn't trigger the `anaconda-auth` plugin (possibly missing environment variables, subprocess isolation, or invoking conda as library instead of CLI).

## Impact

- Cannot create environments or install packages via MCP when `default_channels` points to `repo.anaconda.cloud`
- AUTH-002 blocked — authenticated flows fail (credentials not passed)
- AUTH-001a passing — anonymous users correctly get 403 (expected behavior)

---

## Detailed Request/Response Log

### 1. conda_list_environments — SUCCESS

**Request:**
```json
{
  "name": "conda_list_environments",
  "arguments": {}
}
```

**Response:**
```json
{
  "is_error": false,
  "error_description": "",
  "tool_result": {
    "environments": [
      {"name": "metal", "path": "/Users/iiliukhina/.anaconda-desktop-alpha/micromamba/envs/metal"},
      {"name": "tedtfeb23202", "path": "/Users/iiliukhina/.anaconda-desktop-alpha/micromamba/envs/metal/envs/tedtfeb23202"},
      {"name": "testfeb2321", "path": "/Users/iiliukhina/.anaconda-desktop-alpha/micromamba/envs/metal/envs/testfeb2321"},
      {"name": "connector-env", "path": "/Users/iiliukhina/.anaconda-desktop-integration-test/micromamba/envs/connector-env"},
      {"name": "connector-env", "path": "/Users/iiliukhina/.anaconda-desktop-itest/micromamba/envs/connector-env"},
      {"name": "miniconda3", "path": "/Users/iiliukhina/.anaconda-desktop-itest/miniconda3"},
      {"name": "metal", "path": "/Users/iiliukhina/.anaconda-desktop/micromamba/envs/metal"},
      {"name": "miniconda3", "path": "/opt/miniconda3"},
      {"name": "anaconda-mcp-dev", "path": "/opt/miniconda3/envs/anaconda-mcp-dev"},
      {"name": "anaconda-mcp-dev", "path": "/opt/miniconda3/envs/anaconda-mcp-dev/envs/anaconda-mcp-dev"},
      {"name": "anaconda-mcp-qa", "path": "/opt/miniconda3/envs/anaconda-mcp-qa"},
      {"name": "base", "path": "/opt/miniconda3/envs/anaconda-mcp-rc2-pyX313"},
      {"name": "auth-test", "path": "/opt/miniconda3/envs/auth-test"},
      {"name": "auth-test-1", "path": "/opt/miniconda3/envs/auth-test-1"},
      {"name": "auth-test-3", "path": "/opt/miniconda3/envs/auth-test-3"},
      {"name": "testmarch13_05", "path": "/opt/miniconda3/envs/testmarch13_05"},
      {"name": "testmarch13_7", "path": "/opt/miniconda3/envs/testmarch13_7"},
      {"name": "testmarch13_8", "path": "/opt/miniconda3/envs/testmarch13_8"}
    ]
  }
}
```

---

### 2. conda_create_environment — FAILED (403)

**Request:**
```json
{
  "name": "conda_create_environment",
  "arguments": {
    "environment_name": "e2e-test",
    "packages": ["python=3.11"]
  }
}
```

**Response:**
```json
{
  "is_error": true,
  "error_description": "There was an error while creating the environment. Details: ('conda', \"HTTP 403 Forbidden for url <https://repo.anaconda.cloud/repo/main/osx-arm64/repodata.json>\nElapsed: 00:00.060995\nCF-RAY: 9dbe7024fcc30d00-EWR\n\nYou do not have permission to access this resource.\n\nThis may indicate:\n  - The channel requires authentication. Check your credentials.\n  - You do not have access to this private channel or package.\n\nYou will need to modify your conda configuration to proceed.\nUse `conda config --show` to view your configuration's current state.\nFurther configuration help can be found at <https://conda.io/docs/config.html>.\n\")",
  "tool_result": {}
}
```

---

### 3. conda_install_packages — FAILED (403)

**Request:**
```json
{
  "name": "conda_install_packages",
  "arguments": {
    "packages": ["numpy"],
    "environment": "auth-test-1"
  }
}
```

**Response:**
```json
{
  "is_error": true,
  "error_description": "('conda', \"HTTP 403 Forbidden for url <https://repo.anaconda.cloud/repo/main/osx-arm64/repodata.json>\nElapsed: 00:00.075689\nCF-RAY: 9dbe70d13ebe0d00-EWR\n\nYou do not have permission to access this resource.\n\nThis may indicate:\n  - The channel requires authentication. Check your credentials.\n  - You do not have access to this private channel or package.\n\nYou will need to modify your conda configuration to proceed.\nUse `conda config --show` to view your configuration's current state.\nFurther configuration help can be found at <https://conda.io/docs/config.html>.\n\")",
  "tool_result": {}
}
```

---

### 4. conda_list_environment_packages (empty env) — SUCCESS

**Request:**
```json
{
  "name": "conda_list_environment_packages",
  "arguments": {
    "environment": "auth-test-1"
  }
}
```

**Response:**
```json
{
  "is_error": false,
  "error_description": "",
  "tool_result": {
    "packages": []
  }
}
```

---

### 5. conda_list_environment_packages (with packages) — SUCCESS

**Request:**
```json
{
  "name": "conda_list_environment_packages",
  "arguments": {
    "environment": "testmarch13_05"
  }
}
```

**Response:**
```json
{
  "is_error": false,
  "error_description": "",
  "tool_result": {
    "packages": [
      {"name": "python", "version": "3.14.3", "channel": "conda-forge", "base_url": "https://conda.anaconda.org/conda-forge"},
      {"name": "numpy", "version": "2.4.2", "channel": "conda-forge"},
      {"name": "pandas", "version": "3.0.1", "channel": "conda-forge"},
      {"name": "pip", "version": "26.0.1", "channel": "conda-forge"},
      {"name": "six", "version": "1.17.0", "channel": "conda-forge"},
      "...34 packages total..."
    ]
  }
}
```

---

### 6. conda_remove_packages — FAILED (403)

**Request:**
```json
{
  "name": "conda_remove_packages",
  "arguments": {
    "environment": "testmarch13_05",
    "packages": ["six"]
  }
}
```

**Response:**
```json
{
  "is_error": true,
  "error_description": "('conda', \"HTTP 403 Forbidden for url <https://repo.anaconda.cloud/repo/main/osx-arm64/repodata.json>\nElapsed: 00:00.028271\nCF-RAY: 9dbe72ec9da90d00-EWR\n\nYou do not have permission to access this resource.\n\nThis may indicate:\n  - The channel requires authentication. Check your credentials.\n  - You do not have access to this private channel or package.\n\nYou will need to modify your conda configuration to proceed.\nUse `conda config --show` to view your configuration's current state.\nFurther configuration help can be found at <https://conda.io/docs/config.html>.\n\")",
  "tool_result": {}
}
```

---

### 7. conda_remove_environment — SUCCESS

**Request:**
```json
{
  "name": "conda_remove_environment",
  "arguments": {
    "environment_name": "testmarch13_05"
  }
}
```

**Response:**
```json
{
  "is_error": false,
  "error_description": "",
  "tool_result": {
    "message": "Remove_all completed successfully",
    "prefix": "/opt/miniconda3/envs/testmarch13_05"
  }
}
```

---

## Conclusion

All 403 failures hit the same endpoint: `https://repo.anaconda.cloud/repo/main/osx-arm64/repodata.json`

This confirms the MCP subprocess does not pass `anaconda-auth` credentials when conda needs to contact channels.

## Related

- DESK-1358 (closed) — originally misdiagnosed as URL routing issue
- DESK-1391 (Windows) — may or may not be related, needs separate investigation
