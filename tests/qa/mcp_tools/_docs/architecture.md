# Stack architecture — `mcp_tools`

What the system under test looks like: how products are wired together, what transports connect them, and what version options exist on each layer.

---

## Products and conda environment

The **whole server-side chain** runs inside **one conda environment** (passed as `--server-conda-env`):

- **Python:** single interpreter for all imports — typically **3.10–3.13**; must match all package pins.
- **Versions:** independently pinned `anaconda-mcp`, `mcp-compose`, `environments-mcp`, `anaconda-connector` (conda/pip/editable). Must be mutually compatible at runtime.
- **Transports ① and ②:** configuration choices, not separate installs — see diagram below.

```mermaid
flowchart LR
  subgraph clients["MCP clients  ·  outside the conda env"]
    CL["IDE / CLI / tests / HTTP client"]
  end

  subgraph cenv["One conda environment  ·  Python 3.10–3.13"]
    subgraph amp["Process: anaconda-mcp serve"]
      direction TB
      AM["anaconda-mcp<br/>· package version"]
      MC["mcp-compose<br/>· package version (overridable)"]
      AM --> MC
    end

    subgraph ems["Subprocess: python -m anaconda_mcp.conda_mcp_lite"]
      direction TB
      EM["conda_mcp_lite<br/>· vendored in anaconda-mcp"]
      AC["conda CLI<br/>· user's discovered conda exe"]
      EM --> AC
    end

    MC <-->|"② upstream MCP<br/>STDIO subprocess"| EM
  end

  CL <-->|"① outer MCP<br/>HTTP or STDIO"| AM
```

- **①** — transport between the **MCP client** and **`anaconda-mcp`**: streamable HTTP or STDIO.
- **②** — transport between **`mcp-compose`** and the vendored **`anaconda_mcp.conda_mcp_lite`** sub-server: **STDIO subprocess** (the vendored server is stdio-only). Independent of ①.
- **`conda_mcp_lite` → `conda` CLI** — shells out to the user's discovered conda executable; not a third MCP wire.
- **`mcp-compose`** ships as a dependency of `anaconda-mcp`; it can be **overridden** (fork / git) to test transport fixes without changing `anaconda-mcp` itself.

### Version options per product

| Product | How to change the version |
|---------|--------------------------|
| **`anaconda-mcp`** | Release or editable checkout (`pip install -e …`) in the server env |
| **`mcp-compose`** | Transitive dep; override with `pip install` (fork / git) — see [`README.md`](../README.md) |
| **`environments-mcp`** | Release or editable in the **same** env as `anaconda-mcp` |
| **`anaconda-connector-conda`** | Conda/pip pin; must be importable as `anaconda_connector_conda` or tools fail to register |

---

## Two-hop transport matrix (`--mcp-profile`)

Each `--mcp-profile` value fixes both **①** and **②** independently.
Canonical TOML is generated from [`tests/qa/shared/mcp_compose_profiles.py`](../../shared/mcp_compose_profiles.py) — tests do **not** select transport by editing the packaged `mcp_compose.toml`.

| Profile | ① client → anaconda-mcp | ② mcp-compose → conda (vendored) | Why we care |
|---------|--------------------------|--------------------------------------|-------------|
| `http-http` | Streamable HTTP | STDIO subprocess | HTTP outer client path; matches `start-http-server.sh` |
| `stdio-http` | STDIO | STDIO subprocess | Equivalent to `stdio-stdio` now (conda is stdio-only); kept for compatibility |
| `stdio-stdio` | STDIO | STDIO subprocess | All-stdio; used for hang / stress regressions |

**Not covered by default:** `http-stdio` (HTTP outer, STDIO upstream) is valid for mcp-compose but omitted until the product explicitly needs it — see `mcp_compose_profiles.py`.

---

See [`configuration.md`](configuration.md) for CLI options and CI setup, [`test_design.md`](test_design.md) for how profiles translate to fixtures.
