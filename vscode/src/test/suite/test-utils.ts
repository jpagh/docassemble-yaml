import * as path from "node:path";
import * as vscode from "vscode";

export type ServerState = "idle" | "disabled" | "missing" | "running" | "error" | "stopped";

export type ServerStateSnapshot = {
  state: ServerState;
  resolvedCommand?: string;
  lastError?: string;
};

export type DocassembleExtensionApi = {
  restart(): Promise<void>;
  showOutput(): void;
  showSetupHelp(): Promise<void>;
  getServerState(): ServerStateSnapshot;
};

export const EXTENSION_ID = "jackadamson.vscode-docassemble";

export async function getApi(): Promise<DocassembleExtensionApi> {
  const extension = vscode.extensions.getExtension<DocassembleExtensionApi>(EXTENSION_ID);
  if (!extension) throw new Error(`Expected extension ${EXTENSION_ID} to be available.`);
  const api = await extension.activate();
  if (!api) throw new Error(`${EXTENSION_ID}.activate() returned undefined`);
  return api;
}

export async function updateConfiguration<T>(section: string, value: T): Promise<void> {
  await vscode.workspace
    .getConfiguration()
    .update(section, value, vscode.ConfigurationTarget.Global);
}

export async function resetConfiguration(): Promise<void> {
  await updateConfiguration("docassemble-lsp.enabled", false);
  await updateConfiguration("docassemble-lsp.importStrategy", undefined);
  await updateConfiguration("docassemble-lsp.command", undefined);
  await updateConfiguration("docassemble-lsp.interpreter", undefined);
  await updateConfiguration("docassemble-lsp.env", undefined);
  await updateConfiguration("docassemble-lsp.trace.server", undefined);
  await updateConfiguration("docassemble-lsp.showNotifications", undefined);
  await updateConfiguration("editor.formatOnType", undefined);
  await updateConfiguration("editor.insertSpaces", undefined);
  await updateConfiguration("editor.tabSize", undefined);
}

export async function waitForState(
  api: DocassembleExtensionApi,
  expectedState: ServerState,
  timeoutMs = 5000,
): Promise<ServerStateSnapshot> {
  for (let attempt = 0; attempt < timeoutMs / 100; attempt += 1) {
    const snapshot = api.getServerState();
    if (snapshot.state === expectedState) {
      return snapshot;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(
    `Timed out waiting for state ${expectedState}; last state was ${api.getServerState().state}.`,
  );
}

export function mockServerPath(): string {
  const extension = vscode.extensions.getExtension(EXTENSION_ID);
  if (!extension) throw new Error(`Expected extension ${EXTENSION_ID} to be available.`);
  return path.join(extension.extensionPath, "dist", "test", "fixtures", "mock-lsp-server.js");
}

export function quoteForShell(value: string): string {
  if (process.platform === "win32") {
    return `"${value.replaceAll('"', '\\"')}"`;
  }
  return `'${value.replaceAll("'", "'\\''")}'`;
}

export async function waitFor(predicate: () => boolean, timeoutMs = 5000): Promise<void> {
  for (let attempt = 0; attempt < timeoutMs / 50; attempt += 1) {
    if (predicate()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error("Timed out waiting for condition.");
}

export function python3Available(): boolean {
  return commandExists("python3");
}

function commandExists(command: string): boolean {
  if (path.isAbsolute(command) || command.includes(path.sep)) {
    return isExecutable(command);
  }
  const pathValue = process.env.PATH;
  if (!pathValue) return false;
  for (const directory of pathValue.split(path.delimiter).filter(Boolean)) {
    const candidate = path.join(directory, command);
    if (isExecutable(candidate)) return true;
  }
  return false;
}

function isExecutable(candidatePath: string): boolean {
  try {
    const fs = require("node:fs") as typeof import("node:fs");
    fs.accessSync(candidatePath, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

export class SkipTest extends Error {}
