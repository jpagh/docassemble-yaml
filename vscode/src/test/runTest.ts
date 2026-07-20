import * as os from "node:os";
import * as path from "node:path";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

import {
  runTests,
  downloadAndUnzipVSCode,
  resolveCliPathFromVSCodeExecutablePath,
} from "@vscode/test-electron";

function seedTestWorkspace(): string {
  const workspaceDir = mkdtempSync(path.join(os.tmpdir(), "docassemble-test-"));
  const pkgDir = path.join(workspaceDir, "docassemble", "testpkg");
  const dataDir = path.join(pkgDir, "data");
  mkdirSync(dataDir, { recursive: true });

  writeFileSync(path.join(workspaceDir, "pyproject.toml"), "", "utf8");
  writeFileSync(path.join(pkgDir, "__init__.py"), "", "utf8");
  writeFileSync(path.join(pkgDir, "utils.py"), "def helper():\n    pass\n", "utf8");
  writeFileSync(path.join(pkgDir, "helpers.py"), "def do_stuff():\n    pass\n", "utf8");
  writeFileSync(path.join(dataDir, "other.yml"), "question: Other\n", "utf8");
  const subDir = path.join(dataDir, "sub");
  mkdirSync(subDir, { recursive: true });
  writeFileSync(path.join(subDir, "nested.yml"), "question: Nested\n", "utf8");

  return workspaceDir;
}

async function main(): Promise<void> {
  const extensionDevelopmentPath = path.resolve(__dirname, "../..");
  const extensionTestsPath = path.resolve(__dirname, "./suite/index");
  const cacheDir = path.resolve(__dirname, "../../.vscode-test");
  const sandboxExtensionsDir = path.join(cacheDir, "extensions");

  const vscodeExecutablePath = await downloadAndUnzipVSCode({ cachePath: cacheDir });
  const cliPath = resolveCliPathFromVSCodeExecutablePath(vscodeExecutablePath);

  if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST === "1") {
    const hasPythonExt =
      existsSync(sandboxExtensionsDir) &&
      readdirSync(sandboxExtensionsDir).some((entry) => entry.startsWith("ms-python.python"));

    if (!hasPythonExt) {
      console.log("Installing ms-python.python into test sandbox...");
      const result = spawnSync(
        cliPath,
        [
          "--install-extension",
          "ms-python.python",
          "--extensions-dir",
          sandboxExtensionsDir,
          "--force",
        ],
        { encoding: "utf8", timeout: 60000 },
      );

      if (result.status !== 0) {
        console.error(
          `Warning: Failed to install ms-python.python: ${(result.stderr || result.stdout || "").trim()}`,
        );
      } else {
        console.log("Installed ms-python.python");
      }
    } else {
      console.log("ms-python.python already present in test sandbox");
    }
  }

  // Pass the local LSP project path so tests can start the server via
  // `uv run --project <path> docassemble-lsp lsp` without needing it on PATH.
  const lspProject = path.resolve(__dirname, "../../../lsp");
  const testEnv: Record<string, string> = {
    DOCASSEMBLE_LSP_PROJECT: lspProject,
  };

  // Pass --headless on every platform by default, unless the user opts out
  // with DOCASSEMBLE_LSP_SHOW_WINDOW=1.  Linux/Windows fully suppress the
  // window; macOS ignores --headless (see microsoft/vscode-test#290).
  const launchArgs: string[] =
    process.env.DOCASSEMBLE_LSP_SHOW_WINDOW === "1" ? [] : ["--headless"];

  // Seed a temp workspace with docassemble package structure for real tests.
  let workspaceDir: string | undefined;
  if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST === "1") {
    workspaceDir = seedTestWorkspace();
    launchArgs.push(workspaceDir);
    testEnv.DOCASSEMBLE_TEST_WORKSPACE = workspaceDir;
  }

  // On macOS, use a wrapper that strips ELECTRON_RUN_AS_NODE from the
  // environment.  When that variable is set, the ARM64 Electron binary
  // switches to Node.js mode and rejects VS Code flags like
  // --no-sandbox and --extensionTestsPath.  The wrapper does nothing
  // window-management-related.
  try {
    if (process.platform === "darwin" && process.env.ELECTRON_RUN_AS_NODE) {
      const wrapper = path.resolve(__dirname, "../../scripts/vscode-test-wrapper.mjs");
      await runTests({
        extensionDevelopmentPath,
        extensionTestsPath,
        vscodeExecutablePath: wrapper,
        extensionTestsEnv: { ...testEnv, VSCODE_ELECTRON_BIN: vscodeExecutablePath },
        launchArgs,
      });
    } else {
      await runTests({
        extensionDevelopmentPath,
        extensionTestsPath,
        vscodeExecutablePath,
        extensionTestsEnv: testEnv,
        launchArgs,
      });
    }
  } finally {
    if (workspaceDir) {
      rmSync(workspaceDir, { recursive: true, force: true });
    }
  }
}

void main();
