import * as assert from "node:assert/strict";
import * as vscode from "vscode";

import {
  getApi,
  updateConfiguration,
  resetConfiguration,
  waitForState,
  waitFor,
  mockServerPath,
  quoteForShell,
} from "./test-utils";

export async function runTests(): Promise<void> {
  const tests: Array<{ name: string; run: () => Promise<void> }> = [
    {
      name: "opening a .yml file with known issues produces diagnostics from mock server",
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

        const document = await vscode.workspace.openTextDocument({
          language: "docassemble",
          content: "mock diagnostic\n",
        });
        await vscode.window.showTextDocument(document);

        await waitFor(() => vscode.languages.getDiagnostics(document.uri).length > 0);
        const diags = vscode.languages.getDiagnostics(document.uri);
        assert.equal(diags.length, 1);
        assert.match(diags[0].message, /Mock diagnostic/i);
      },
    },

    {
      name: "diagnostics clear on file close",
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

        const document = await vscode.workspace.openTextDocument({
          language: "docassemble",
          content: "mock diagnostic\n",
        });
        await vscode.window.showTextDocument(document);
        await waitFor(() => vscode.languages.getDiagnostics(document.uri).length === 1);

        await vscode.commands.executeCommand("workbench.action.closeActiveEditor");

        await waitFor(() => vscode.languages.getDiagnostics(document.uri).length === 0);
      },
    },
  ];

  console.log("\n  Diagnostics tests");

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
      console.error(`  ${index + 1}) Diagnostics tests`);
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
