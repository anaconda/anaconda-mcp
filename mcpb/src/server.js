#!/usr/bin/env node
/*
 * Copyright (c) Anaconda, Inc.
 *
 * Apache-2.0 License
 */

"use strict";

const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const ANA_ASSETS = {
  "darwin-arm64": "ana-darwin-arm64",
  "linux-x64": "ana-linux-x86_64",
  "linux-arm64": "ana-linux-aarch64",
  "win32-x64": "ana-windows-x86_64.exe",
};

function fail(message) {
  console.error(`Anaconda MCP launcher error: ${message}`);
  process.exit(1);
}

const platformKey = `${process.platform}-${process.arch}`;
const assetName = ANA_ASSETS[platformKey];

if (!assetName) {
  fail(`unsupported platform ${platformKey}`);
}

const anaPath = path.resolve(__dirname, "..", "bin", assetName);
const CURRENT_TOS_VERSION = "2026-05-27";

if (!fs.existsSync(anaPath)) {
  fail(`bundled ana binary is missing: ${anaPath}`);
}

if (process.platform !== "win32") {
  try {
    fs.chmodSync(anaPath, 0o755);
  } catch (error) {
    console.error(
      `Anaconda MCP launcher warning: could not update permissions for ${anaPath}: ${error.message}`,
    );
  }
}

const childEnv = { ...process.env };
const apiKey = process.env.ANACONDA_MCPB_ANACONDA_API_KEY;

if (apiKey && !apiKey.startsWith("${user_config.")) {
  childEnv.ANACONDA_AUTH_API_KEY = apiKey;
}

if (process.env.ANACONDA_MCPB_ACCEPT_BETA_TERMS === "true") {
  childEnv.ANACONDA_MCP_ACCEPTED_TERMS = "true";
  childEnv.ANACONDA_MCP_ACCEPTED_TERMS_VERSION = CURRENT_TOS_VERSION;
}

delete childEnv.ANACONDA_MCPB_ANACONDA_API_KEY;
delete childEnv.ANACONDA_MCPB_ACCEPT_BETA_TERMS;

const child = spawn(anaPath, ["mcp", "serve"], {
  env: childEnv,
  stdio: "inherit",
});

for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(signal, () => {
    if (!child.killed) {
      child.kill(signal);
    }
  });
}

child.on("error", (error) => {
  fail(`failed to start ana: ${error.message}`);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.exit(1);
  }
  process.exit(code ?? 1);
});
