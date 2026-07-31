import * as os from "node:os";
import * as path from "node:path";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  realpathSync,
  rmSync,
  writeFileSync,
} from "node:fs";
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

function minimumVSCodeVersion(): string {
  const pkgPath = path.resolve(__dirname, "../../package.json");
  const pkg = JSON.parse(readFileSync(pkgPath, "utf8")) as {
    engines?: { vscode?: string };
  };
  return (pkg.engines?.vscode ?? "1.0").replace(/[^\d.]/g, "");
}

function versionAtLeast(version: string, minimum: string): boolean {
  const toTuple = (value: string) => value.split(".").map((part) => parseInt(part, 10) || 0);
  const a = toTuple(version);
  const b = toTuple(minimum);
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const da = a[i] ?? 0;
    const db = b[i] ?? 0;
    if (da !== db) {
      return da > db;
    }
  }
  return true;
}

function readProductVersion(appDir: string): string | undefined {
  try {
    const raw = readFileSync(path.join(appDir, "Contents/Resources/app/product.json"), "utf8");
    const version = JSON.parse(raw)?.version;
    return typeof version === "string" ? version : undefined;
  } catch {
    return undefined;
  }
}

function findOnPath(names: string[]): string | undefined {
  const dirs = (process.env.PATH ?? "").split(path.delimiter);
  for (const dir of dirs) {
    for (const name of names) {
      const candidate = path.join(dir, name);
      if (existsSync(candidate)) {
        return candidate;
      }
    }
  }
  return undefined;
}

function findSystemVSCodeExecutablePath(): string | undefined {
  if (process.platform !== "darwin") {
    return undefined;
  }
  const appDirs = new Set([
    "/Applications/Visual Studio Code.app",
    "/Applications/Visual Studio Code - Insiders.app",
  ]);
  const codeCli = findOnPath(["code", "code-insiders"]);
  if (codeCli) {
    try {
      appDirs.add(path.resolve(realpathSync(codeCli), "../../../../.."));
    } catch {}
  }
  for (const appDir of appDirs) {
    const executable = path.join(appDir, "Contents/MacOS/Code");
    if (!existsSync(executable)) {
      continue;
    }
    const version = readProductVersion(appDir);
    const minimum = minimumVSCodeVersion();
    if (version !== undefined && !versionAtLeast(version, minimum)) {
      console.warn(
        `System VS Code ${version} is older than engines.vscode ${minimum}; falling back to download`,
      );
      continue;
    }
    return executable;
  }
  return undefined;
}

function darwinExecutablePath(executablePath: string): string {
  if (process.platform === "darwin") {
    return executablePath.replace(/\/MacOS\/(Electron|Code)$/, "/MacOS/Code");
  }
  return executablePath;
}

function versionDirOf(executablePath: string): string {
  return path.resolve(executablePath, "../../../../");
}

function pruneStaleVersions(cacheDir: string, keepDir: string | undefined): void {
  if (!existsSync(cacheDir)) {
    return;
  }
  const keep = keepDir ? path.resolve(keepDir) : undefined;
  for (const entry of readdirSync(cacheDir)) {
    if (!entry.startsWith("vscode-darwin-")) {
      continue;
    }
    const dir = path.join(cacheDir, entry);
    if (keep && path.resolve(dir) === keep) {
      continue;
    }
    console.log(`Pruning stale VS Code install: ${dir}`);
    rmSync(dir, { recursive: true, force: true });
  }
}

async function main(): Promise<void> {
  const extensionDevelopmentPath = path.resolve(__dirname, "../..");
  const extensionTestsPath = path.resolve(__dirname, "./suite/index");
  const cacheDir = path.resolve(__dirname, "../../.vscode-test");
  const sandboxExtensionsDir = path.join(cacheDir, "extensions");

  let vscodeExecutablePath: string;
  let downloadedDir: string | undefined;
  if (process.env.DOCASSEMBLE_LSP_USE_SYSTEM_VSCODE === "1") {
    const systemPath = findSystemVSCodeExecutablePath();
    if (systemPath) {
      vscodeExecutablePath = systemPath;
      console.log(`Using system VS Code: ${vscodeExecutablePath}`);
    } else {
      console.warn(
        "DOCASSEMBLE_LSP_USE_SYSTEM_VSCODE=1 set, but no suitable system VS Code was found; falling back to download",
      );
      vscodeExecutablePath = darwinExecutablePath(
        await downloadAndUnzipVSCode({ cachePath: cacheDir }),
      );
      downloadedDir = versionDirOf(vscodeExecutablePath);
    }
  } else {
    vscodeExecutablePath = darwinExecutablePath(
      await downloadAndUnzipVSCode({ cachePath: cacheDir }),
    );
    downloadedDir = versionDirOf(vscodeExecutablePath);
  }
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
    pruneStaleVersions(cacheDir, downloadedDir);
  }
}

void main();
