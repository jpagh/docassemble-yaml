import * as assert from "node:assert/strict";

import * as vscode from "vscode";

import { getApi, updateConfiguration, resetConfiguration, waitForState } from "./test-utils";

const CONFIG_SECTION = "docassemble-lsp";

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
      name: "notification preferences (showNotifications) are respected",
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
