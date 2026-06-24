import * as assert from "node:assert/strict";
import * as path from "node:path";

import * as vscode from "vscode";

import {
  getApi,
  updateConfiguration,
  resetConfiguration,
  waitForState,
  waitFor,
  mockServerPath,
  quoteForShell,
  python3Available,
  SkipTest,
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
      name: "fix-all code action (source.fixAll.docassemble-lsp) triggers correctly",
      run: async () => {
        if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST !== "1" || !python3Available()) {
          throw new SkipTest();
        }

        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        const api = await getApi();
        await api.restart();
        await waitForState(api, "running");

        const document = await vscode.workspace.openTextDocument({
          language: "docassemble",
          content: "question: |\n  test\nfoobar: bad\n",
        });
        await vscode.window.showTextDocument(document);

        await waitFor(() =>
          vscode.languages.getDiagnostics(document.uri).some((d) => String(d.code) === "E301"),
        );

        const codeActions = await vscode.commands.executeCommand<vscode.CodeAction[]>(
          "vscode.executeCodeActionProvider",
          document.uri,
          new vscode.Range(0, 0, 2, 0),
        );

        const fixAll = codeActions?.find((a) => a.kind?.value === "source.fixAll.docassemble-lsp");
        assert.ok(fixAll, "Expected fix-all code action");
        assert.equal(fixAll.title, "Fix all auto-fixable docassemble-lsp issues");
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
  let skipped = 0;
  const failures: Array<{ name: string; error: unknown }> = [];

  for (const test of tests) {
    try {
      await test.run();
      passed += 1;
      console.log(`    ok ${test.name}`);
    } catch (error) {
      if (error instanceof SkipTest) {
        skipped += 1;
        console.log(`    - ${test.name}`);
      } else {
        failures.push({ name: test.name, error });
        console.log(`    ${failures.length}) ${test.name}`);
      }
    } finally {
      await resetConfiguration();
    }
  }

  console.log(`  ${passed} passing`);
  if (skipped > 0) {
    console.log(`  ${skipped} pending`);
  }

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
