#!/usr/bin/env node
// Wrapper for the VS Code macOS test runner.
//
// The Electron binary on macOS ARM64 switches to Node.js mode when
// ELECTRON_RUN_AS_NODE=1 is set, rejecting Electron/VS Code CLI flags.
// This wrapper spawns the binary with that variable removed.  It does
// nothing window-management-related.

import { spawn } from "node:child_process";

const bin = process.env.VSCODE_ELECTRON_BIN;
if (!bin) {
  console.error("VSCODE_ELECTRON_BIN is not set");
  process.exit(1);
}

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

const child = spawn(bin, process.argv.slice(2), {
  stdio: "inherit",
  env,
});

child.on("close", (code) => {
  process.exit(code ?? 1);
});

child.on("error", (err) => {
  console.error(err);
  process.exit(1);
});
