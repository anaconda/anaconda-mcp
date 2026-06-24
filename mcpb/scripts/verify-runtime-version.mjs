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
const checksumsPath = path.resolve(__dirname, "..", "ana-assets.sha256");
const rawVersion = process.argv[2] || process.env.GITHUB_REF_NAME || process.env.VERSION;

if (!rawVersion) {
  console.error(
    "Usage: node mcpb/scripts/verify-runtime-version.mjs <anaconda-mcp-version-or-tag>",
  );
  process.exit(1);
}

const expectedVersion = rawVersion.replace(/^v/, "");
const checksums = fs.readFileSync(checksumsPath, "utf8");
const runtimeMatch = checksums.match(/^# anaconda-mcp runtime:\s*(\S+)\s*$/m);
const anaMatch = checksums.match(/^# ana-cli release:\s*(\S+)\s*$/m);

if (!runtimeMatch) {
  console.error(`Missing '# anaconda-mcp runtime: <version>' in ${checksumsPath}`);
  process.exit(1);
}

const runtimeVersion = runtimeMatch[1];

if (runtimeVersion !== expectedVersion) {
  const anaVersion = anaMatch?.[1] ?? "unknown";
  console.error(
    `Pinned ana ${anaVersion} installs anaconda-mcp ${runtimeVersion}, ` +
      `but this release is ${expectedVersion}. Update the pinned ana release and checksums ` +
      "before publishing the MCPB.",
  );
  process.exit(1);
}

console.log(`Pinned ana runtime matches anaconda-mcp ${expectedVersion}`);
