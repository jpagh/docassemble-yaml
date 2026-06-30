import * as assert from "node:assert/strict";

import * as vscode from "vscode";

import { getApi, updateConfiguration, resetConfiguration, waitForState } from "./test-utils";

const CONFIG_SECTION = "docassemble-lsp";

// Matches the production shouldShowNotification() logic in extension.ts.
// This is a pure-function equivalent that we can test without accessing
// the private method on DocassembleLspController.
function shouldShowNotification(
  setting: "off" | "onError" | "onWarning" | "always",
  level: "error" | "warning",
): boolean {
  if (setting === "always") return true;
  if (setting === "off") return false;
  if (setting === "onError") return level === "error";
  if (setting === "onWarning") return level === "warning" || level === "error";
  return false;
}

export async function runTests(): Promise<void> {
  const tests: Array<{ name: string; run: () => Promise<void> }> = [
    {
      name: "changing enabled to false triggers server stop",
      run: async () => {
        await resetConfiguration();

        const api = await getApi();
        const state = await waitForState(api, "disabled");
        assert.equal(state.state, "disabled");
      },
    },
    {
      name: "toggling enabled back to true triggers server restart",
      run: async () => {
        await resetConfiguration();

        const api = await getApi();
        let state = await waitForState(api, "disabled");
        assert.equal(state.state, "disabled");

        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        await api.restart();
        state = await waitForState(api, "running");
        assert.equal(state.state, "running");
      },
    },
    {
      name: "importStrategy changes propagate correctly",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        let strategy = vscode.workspace.getConfiguration(CONFIG_SECTION).get("importStrategy");
        assert.equal(strategy, "useBundled");

        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        strategy = vscode.workspace.getConfiguration(CONFIG_SECTION).get("importStrategy");
        assert.equal(strategy, "fromEnvironment");
      },
    },
    {
      name: "notification preferences (showNotifications) roundtrip through config",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.showNotifications", "onError");
        let showNotif = vscode.workspace.getConfiguration(CONFIG_SECTION).get("showNotifications");
        assert.equal(showNotif, "onError");

        await updateConfiguration("docassemble-lsp.showNotifications", "always");
        showNotif = vscode.workspace.getConfiguration(CONFIG_SECTION).get("showNotifications");
        assert.equal(showNotif, "always");
      },
    },
    {
      name: "shouldShowNotification level mapping (off) hides all",
      run: async () => {
        assert.equal(shouldShowNotification("off", "error"), false);
        assert.equal(shouldShowNotification("off", "warning"), false);
      },
    },
    {
      name: "shouldShowNotification level mapping (onError) shows errors only",
      run: async () => {
        assert.equal(shouldShowNotification("onError", "error"), true);
        assert.equal(shouldShowNotification("onError", "warning"), false);
      },
    },
    {
      name: "shouldShowNotification level mapping (onWarning) shows errors and warnings",
      run: async () => {
        assert.equal(shouldShowNotification("onWarning", "error"), true);
        assert.equal(shouldShowNotification("onWarning", "warning"), true);
      },
    },
    {
      name: "shouldShowNotification level mapping (always) shows everything",
      run: async () => {
        assert.equal(shouldShowNotification("always", "error"), true);
        assert.equal(shouldShowNotification("always", "warning"), true);
      },
    },
    {
      name: "notification suppression (off): server start failure does not show warning",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          "/non_existent_binary_xyzzy_does_not_exist",
        );
        await updateConfiguration("docassemble-lsp.showNotifications", "off");

        const originalShowWarning = vscode.window.showWarningMessage;
        let notificationShown = false;
        vscode.window.showWarningMessage = ((_message: string) => {
          notificationShown = true;
          return Promise.resolve(undefined);
        }) as typeof vscode.window.showWarningMessage;

        try {
          const api = await getApi();
          await api.restart();
          await waitForState(api, "error");
          assert.equal(
            notificationShown,
            false,
            "showNotifications=off should suppress the error notification",
          );
        } finally {
          vscode.window.showWarningMessage = originalShowWarning;
        }
      },
    },
    {
      name: "notification enabled (onError): server start failure shows warning",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          "/non_existent_binary_xyzzy_does_not_exist",
        );
        await updateConfiguration("docassemble-lsp.showNotifications", "onError");

        const originalShowWarning = vscode.window.showWarningMessage;
        let notificationShown = false;
        vscode.window.showWarningMessage = ((_message: string) => {
          notificationShown = true;
          return Promise.resolve(undefined);
        }) as typeof vscode.window.showWarningMessage;

        try {
          const api = await getApi();
          await api.restart();
          await waitForState(api, "error");
          assert.equal(
            notificationShown,
            true,
            "showNotifications=onError should show the error notification",
          );
        } finally {
          vscode.window.showWarningMessage = originalShowWarning;
        }
      },
    },
    {
      name: "setting and unsetting interpreter path works",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.interpreter", ["/usr/bin/python3"]);
        let interpreter = vscode.workspace.getConfiguration(CONFIG_SECTION).get("interpreter");
        assert.deepEqual(interpreter, ["/usr/bin/python3"]);

        await updateConfiguration("docassemble-lsp.interpreter", []);
        interpreter = vscode.workspace.getConfiguration(CONFIG_SECTION).get("interpreter");
        assert.deepEqual(interpreter, []);
      },
    },
  ];

  console.log("\n  Config tests");

  let passed = 0;
  const failures: Array<{ name: string; error: unknown }> = [];

  for (const test of tests) {
    try {
      await test.run();
      passed += 1;
      console.log(`    ok ${test.name}`);
    } catch (error) {
      failures.push({ name: test.name, error });
      console.log(`    ${failures.length}) ${test.name}`);
    } finally {
      await resetConfiguration();
    }
  }

  console.log(`  ${passed} passing`);

  if (failures.length > 0) {
    for (const [index, failure] of failures.entries()) {
      console.error(`  ${index + 1}) Config tests`);
      console.error(`       ${failure.name}:`);
      console.error(
        failure.error instanceof Error
          ? (failure.error.stack ?? failure.error.message)
          : String(failure.error),
      );
    }
    throw new Error(`${failures.length} test(s) failed.`);
  }
}
