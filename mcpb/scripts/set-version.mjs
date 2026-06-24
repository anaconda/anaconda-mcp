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
const mcpbDir = path.resolve(__dirname, "..");
const manifestPath = path.join(mcpbDir, "manifest.json");
const rawVersion = process.argv[2] || process.env.GITHUB_REF_NAME || process.env.VERSION;

if (!rawVersion) {
  console.error("Usage: node mcpb/scripts/set-version.mjs <version-or-tag>");
  process.exit(1);
}

const version = rawVersion.replace(/^v/, "");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
manifest.version = version;
fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
