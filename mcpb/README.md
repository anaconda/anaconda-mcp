<!--
  ~ Copyright (c) Anaconda, Inc.
  ~
  ~ Apache-2.0 License
-->

# Anaconda MCP - MCPB Bundle

This directory builds the MCPB package for installing Anaconda MCP in desktop MCP clients.

The bundle includes pinned `ana` CLI binaries from `anaconda/anaconda-cli`. At runtime, a small Node.js launcher selects the right binary for the current platform and runs:

```bash
ana mcp serve
```

`ana` installs and runs its managed Anaconda MCP runtime on first launch. Users do not need to create an `anaconda-mcp` conda environment before installing the bundle.

## Requirements

- Node.js from the host MCP client runtime
- macOS Apple Silicon, Linux x86_64/aarch64, or Windows x86_64
- Network access on first launch so `ana` can install its managed runtime
- An Anaconda login and accepted Anaconda MCP Beta Terms before tool calls will succeed

The bundle exposes optional install-time configuration for an Anaconda API key and Beta Terms acceptance. If those fields are left unset, the server falls back to the user's existing Anaconda login and terms configuration.

## Build

Install Node.js, then run:

```bash
make build
```

The build downloads and verifies the pinned `ana` release assets listed in `ana-assets.sha256`, then creates `anaconda-mcp.mcpb`.

To use a different `ana` release while testing:

```bash
make build ANA_CLI_VERSION=v0.2.0
```

If the release changes, update `ana-assets.sha256` with the matching upstream asset checksums and the `# anaconda-mcp runtime:` version installed by that `ana` release.

## Registry Publishing

The root `server.json` is stamped during the release workflow after `anaconda-mcp.mcpb` is built. `write-server-json.mjs` fills in the GitHub Release URL, the server version, and the MCPB SHA-256 before `mcp-publisher publish` runs.

MCP Registry publishing runs only for stable tags. Before building the MCPB, the release workflow verifies that the pinned `ana` release installs the same `anaconda-mcp` version as the tag being published. If they differ, bump the pinned `ana` release and checksums before publishing the stable registry package.

## Bundle Structure

```text
mcpb/
├── manifest.json          # Bundle metadata
├── ana-assets.sha256      # Pinned ana release checksums
├── src/
│   └── server.js          # Platform-selecting launcher
├── scripts/
│   ├── fetch-ana-assets.sh
│   ├── set-version.mjs
│   ├── verify-runtime-version.mjs
│   └── write-server-json.mjs
└── bin/                   # Generated at build time; not tracked
```
