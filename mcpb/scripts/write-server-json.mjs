#!/usr/bin/env node
/*
 * Copyright (c) Anaconda, Inc.
 *
 * Apache-2.0 License
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..");
const tag = process.argv[2] || process.env.GITHUB_REF_NAME;
const fileSha256 = process.argv[3] || process.env.MCPB_SHA256;

if (!tag || !fileSha256) {
  console.error("Usage: node mcpb/scripts/write-server-json.mjs <tag> <mcpb-sha256>");
  process.exit(1);
}

if (!/^[a-f0-9]{64}$/.test(fileSha256)) {
  console.error(`Invalid SHA-256: ${fileSha256}`);
  process.exit(1);
}

const normalizedTag = tag.startsWith("v") ? tag : `v${tag}`;
const version = normalizedTag.replace(/^v/, "");

const server = {
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  name: "io.github.anaconda/anaconda-mcp",
  title: "Anaconda MCP",
  description: "Beta conda env/package MCP server; requires conda, auth, and Beta Terms.",
  websiteUrl: "https://www.anaconda.com/docs/cli-reference/anaconda-mcp/getting-started",
  repository: {
    url: "https://github.com/anaconda/anaconda-mcp",
    source: "github",
    id: "1098842262",
  },
  version,
  packages: [
    {
      registryType: "mcpb",
      identifier: `https://github.com/anaconda/anaconda-mcp/releases/download/${normalizedTag}/anaconda-mcp.mcpb`,
      fileSha256,
      transport: {
        type: "stdio",
      },
    },
  ],
  _meta: {
    "io.modelcontextprotocol.registry/publisher-provided": {
      tool: "github-actions",
      package: "mcpb",
      entrypoint: "ana mcp serve",
      feedbackUrl: "https://anaconda.canny.io/anaconda-mcp-beta",
      requirements: [
        "Miniconda, Anaconda Distribution, or another working conda installation",
        "An Anaconda account or API key",
        "Accepted Anaconda MCP Beta Terms",
      ],
    },
  },
};

fs.writeFileSync(path.join(repoRoot, "server.json"), `${JSON.stringify(server, null, 2)}\n`);
