# Moved: HTTP / STDIO MCP tool tests

The API tool regression suite now lives in **`tests/qa/mcp_tools/`** with profile-aware fixtures.

## Conda env for pytest / httpx

Use **`tests/qa/environment.yml`** (env name `anaconda-mcp-qa`):

```bash
conda env create -f tests/qa/environment.yml
conda activate anaconda-mcp-qa
```

Run examples (from repo root):

```bash
pytest tests/qa/mcp_tools -o addopts= --mcp-profile=http-http --server-url http://localhost:9888/mcp
pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio --server-conda-env anaconda-mcp-server
pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http --server-conda-env anaconda-mcp-server
```

See [`../mcp_tools/README.md`](../mcp_tools/README.md) for full details.

This folder is only a pointer for old links; tests were removed from here.
