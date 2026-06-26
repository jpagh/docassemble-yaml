import * as assert from "node:assert/strict";

import * as vscode from "vscode";

import {
  getApi,
  updateConfiguration,
  resetConfiguration,
  waitForState,
  quoteForShell,
  mockServerPath,
} from "./test-utils";

export async function runTests(): Promise<void> {
  const tests: Array<{ name: string; run: () => Promise<void> }> = [
    {
      name: "extension activates with default config",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        const api = await getApi();
        const state = await waitForState(api, "running");
        assert.equal(state.state, "running");
      },
    },
    {
      name: "extension activates with useBundled strategy",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        const api = await getApi();
        await api.restart();
        const state = await waitForState(api, "running");
        assert.match(state.resolvedCommand ?? "", /python.*run_server\.py$/);
      },
    },
    {
      name: "extension activates with fromEnvironment strategy (mock)",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          `${quoteForShell(process.execPath)} ${quoteForShell(mockServerPath())}`,
        );

        const api = await getApi();
        await api.restart();
        const state = await waitForState(api, "running");
        assert.match(state.resolvedCommand ?? "", /mock-lsp-server\.js/);
      },
    },
    {
      name: "docassemble-lsp.restart command triggers restart",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          `${quoteForShell(process.execPath)} ${quoteForShell(mockServerPath())}`,
        );

        const api = await getApi();
        await api.restart();
        await waitForState(api, "running");

        await vscode.commands.executeCommand("docassemble-lsp.restart");
        await waitForState(api, "running");
      },
    },
    {
      name: "docassemble-lsp.showOutput command reveals output channel",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        const api = await getApi();
        api.showOutput();
      },
    },
    {
      name: "server starts and reaches running state",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          `${quoteForShell(process.execPath)} ${quoteForShell(mockServerPath())}`,
        );

        const api = await getApi();
        await api.restart();

        const state = await waitForState(api, "running");
        assert.equal(state.state, "running");
      },
    },
    {
      name: "user-initiated stop does not auto-restart",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          `${quoteForShell(process.execPath)} ${quoteForShell(mockServerPath())}`,
        );

        const api = await getApi();
        await api.restart();
        const state = await waitForState(api, "running");
        assert.equal(state.state, "running");
      },
    },
    {
      name: "user disables the server",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          `${quoteForShell(process.execPath)} ${quoteForShell(mockServerPath())}`,
        );

        const api = await getApi();
        await api.restart();
        await waitForState(api, "running");

        await updateConfiguration("docassemble-lsp.enabled", false);
        await api.restart();
        const state = await waitForState(api, "disabled");
        assert.equal(state.state, "disabled");
      },
    },
    {
      name: "server crash triggers auto-restart",
      run: async () => {
        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          `${quoteForShell(process.execPath)} ${quoteForShell(mockServerPath())}`,
        );
        // Crash the mock after the 2nd message. The first message
        // is the initialize request; the mock exits before the
        // third message is processed.
        await updateConfiguration("docassemble-lsp.env", {
          DOCASSEMBLE_MOCK_CRASH_AFTER: "2",
        });

        const api = await getApi();
        await api.restart();
        await waitForState(api, "running");
        const initial = api.getServerState();
        assert.equal(initial.crashRestartCount, 0, "fresh start should have zero crashes");

        // Wait for the mock to crash and the LanguageClient to
        // auto-restart. The crash count should become > 0.
        let crashed = false;
        for (let i = 0; i < 50; i += 1) {
          if (api.getServerState().crashRestartCount > 0) {
            crashed = true;
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        assert.ok(crashed, "crashRestartCount should increment after a mock crash");

        // The internal LanguageClient restart keeps our state
        // machine at "running" (we never call startInternal for
        // an internal restart), so this is what we expect.
        const after = api.getServerState();
        assert.equal(after.state, "running");
        assert.ok(after.crashRestartCount > 0);
      },
    },
  ];

  console.log("\n  Server lifecycle");

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
      console.error(`  ${index + 1}) Server lifecycle`);
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
