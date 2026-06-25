import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

import * as vscode from "vscode";

import {
  getApi,
  updateConfiguration,
  resetConfiguration,
  waitFor,
  waitForState,
  SkipTest,
  python3Available,
  quoteForShell,
  mockServerPath,
} from "./test-utils";

type TestCase = {
  name: string;
  run: () => Promise<void>;
};

// ---- Helper: write a YAML file into the test workspace and return its URI ----
async function writeTestFile(
  workspaceDir: string,
  name: string,
  content: string,
): Promise<vscode.Uri> {
  const filePath = path.join(workspaceDir, name);
  fs.writeFileSync(filePath, content, "utf8");
  return vscode.Uri.file(filePath);
}

// ---- Shared helper: start language server with optional extra config ----
async function startServer(extraConfig?: Array<[string, unknown]>): Promise<void> {
  await resetConfiguration();
  await updateConfiguration("docassemble-lsp.enabled", true);
  await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
  await updateConfiguration("docassemble-lsp.interpreter", []);
  if (extraConfig) {
    for (const [key, val] of extraConfig) {
      await updateConfiguration(key, val);
    }
  }
  const api = await getApi();
  await api.restart();
  await waitForState(api, "running");
}

// ---- 3 module completion tests ----
function buildModuleCompletionTests(): TestCase[] {
  const skip = () => {
    if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST !== "1" || !python3Available()) {
      throw new SkipTest();
    }
  };

  const workspaceDir = () => process.env.DOCASSEMBLE_TEST_WORKSPACE ?? "";

  return [
    {
      name: "module completions with dot prefix return textEdit",
      run: async () => {
        skip();
        await startServer();

        const uri = await writeTestFile(
          workspaceDir(),
          "test_modules_dot_prefix.yml",
          "modules:\n  - .\n",
        );
        try {
          const document = await vscode.workspace.openTextDocument(uri);
          await vscode.window.showTextDocument(document);
          const pos = new vscode.Position(1, 5);

          const list = await vscode.commands.executeCommand<vscode.CompletionList>(
            "vscode.executeCompletionItemProvider",
            uri,
            pos,
          );

          const items = list?.items ?? [];
          const labels = items.map((i) => (typeof i.label === "string" ? i.label : i.label.label));
          assert.ok(
            labels.includes(".utils"),
            `Expected .utils in labels, got [${labels.join(", ")}]`,
          );
          assert.ok(
            labels.includes(".helpers"),
            `Expected .helpers in labels, got [${labels.join(", ")}]`,
          );
          assert.ok(
            !labels.some((l) => l.startsWith("docassemble.")),
            `Vendored modules should not appear, got [${labels.filter((l) => l.startsWith("docassemble.")).join(", ")}]`,
          );

          const utilsItem = items.find(
            (i) => (typeof i.label === "string" ? i.label : i.label.label) === ".utils",
          );
          assert.ok(utilsItem, "Expected .utils completion item");
          const te = utilsItem!.textEdit as vscode.TextEdit | undefined;
          if (te) {
            assert.equal(te.range.start.character, 4);
            assert.equal(te.range.end.character, 5);
            assert.equal(te.newText, ".utils");
          } else {
            // Fallback: item may carry range + insertText separately
            const itemRange = utilsItem!.range;
            assert.ok(itemRange, "Expected range on item");
            const simpleRange = "start" in itemRange! ? itemRange : itemRange.replacing;
            assert.equal(simpleRange.start.character, 4);
            assert.equal(simpleRange.end.character, 5);
            assert.equal(utilsItem!.insertText, ".utils");
          }
        } finally {
          fs.rmSync(uri.fsPath, { force: true });
        }
      },
    },
    {
      name: "module completions filter by relative partial prefix",
      run: async () => {
        skip();
        await startServer();

        const uri = await writeTestFile(
          workspaceDir(),
          "test_modules_partial.yml",
          "modules:\n  - .help\n",
        );
        try {
          const document = await vscode.workspace.openTextDocument(uri);
          await vscode.window.showTextDocument(document);
          const pos = new vscode.Position(1, 7);

          const list = await vscode.commands.executeCommand<vscode.CompletionList>(
            "vscode.executeCompletionItemProvider",
            uri,
            pos,
          );

          const items = list?.items ?? [];
          const labels = items.map((i) => (typeof i.label === "string" ? i.label : i.label.label));
          assert.ok(labels.includes(".helpers"), `Expected .helpers in labels`);
          assert.ok(!labels.includes(".utils"), `.utils should be filtered out`);
          assert.ok(
            !labels.some((l) => l.startsWith("docassemble.")),
            `Vendored modules should not appear`,
          );
        } finally {
          fs.rmSync(uri.fsPath, { force: true });
        }
      },
    },
    {
      name: "module completions never include vendored modules",
      run: async () => {
        skip();
        await startServer();

        const uri = await writeTestFile(
          workspaceDir(),
          "test_modules_no_vendored.yml",
          "modules:\n  - util\n",
        );
        try {
          const document = await vscode.workspace.openTextDocument(uri);
          await vscode.window.showTextDocument(document);
          const pos = new vscode.Position(1, 6);

          const list = await vscode.commands.executeCommand<vscode.CompletionList>(
            "vscode.executeCompletionItemProvider",
            uri,
            pos,
          );

          const items = list?.items ?? [];
          const labels = items.map((i) => (typeof i.label === "string" ? i.label : i.label.label));
          assert.ok(labels.includes(".utils"), `Expected .utils in labels`);
          assert.ok(
            !labels.some((l) => l.startsWith("docassemble.")),
            `Vendored modules should not appear, got [${labels.filter((l) => l.startsWith("docassemble.")).join(", ")}]`,
          );
        } finally {
          fs.rmSync(uri.fsPath, { force: true });
        }
      },
    },
  ];
}

// ---- 2 include completion tests ----
function buildIncludeCompletionTests(): TestCase[] {
  const skip = () => {
    if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST !== "1" || !python3Available()) {
      throw new SkipTest();
    }
  };

  const dataDir = () => {
    const wd = process.env.DOCASSEMBLE_TEST_WORKSPACE ?? "";
    return path.join(wd, "docassemble", "testpkg", "data");
  };

  return [
    {
      name: "include item completes relative YAML paths",
      run: async () => {
        skip();
        await startServer();

        const uri = await writeTestFile(dataDir(), "test_include.yml", "include:\n  - \n");
        try {
          const document = await vscode.workspace.openTextDocument(uri);
          await vscode.window.showTextDocument(document);
          const pos = new vscode.Position(1, 4);

          const list = await vscode.commands.executeCommand<vscode.CompletionList>(
            "vscode.executeCompletionItemProvider",
            uri,
            pos,
          );

          const items = list?.items ?? [];
          const labels = items.map((i) => (typeof i.label === "string" ? i.label : i.label.label));
          assert.ok(
            labels.some((l) => l.replace(/\\/g, "/").endsWith("other.yml")),
            `Expected other.yml in labels, got [${labels.join(", ")}]`,
          );
          assert.ok(
            labels.some((l) => l.replace(/\\/g, "/").endsWith("sub/nested.yml")),
            `Expected sub/nested.yml in labels, got [${labels.join(", ")}]`,
          );
        } finally {
          fs.rmSync(uri.fsPath, { force: true });
        }
      },
    },
    {
      name: "include item filters by partial prefix",
      run: async () => {
        skip();
        await startServer();

        const uri = await writeTestFile(dataDir(), "test_include_sub.yml", "include:\n  - sub/\n");
        try {
          const document = await vscode.workspace.openTextDocument(uri);
          await vscode.window.showTextDocument(document);
          const pos = new vscode.Position(1, 7);

          const list = await vscode.commands.executeCommand<vscode.CompletionList>(
            "vscode.executeCompletionItemProvider",
            uri,
            pos,
          );

          const items = list?.items ?? [];
          const labels = items.map((i) => (typeof i.label === "string" ? i.label : i.label.label));
          assert.ok(
            labels.some((l) => l.replace(/\\/g, "/").endsWith("sub/nested.yml")),
            `Expected sub/nested.yml in labels, got [${labels.join(", ")}]`,
          );
          assert.ok(
            !labels.some((l) => l.replace(/\\/g, "/").endsWith("other.yml")),
            `other.yml should be filtered out, got [${labels.join(", ")}]`,
          );
        } finally {
          fs.rmSync(uri.fsPath, { force: true });
        }
      },
    },
  ];
}

// ---- 3 on-type formatting (newline indentation) tests ----
function buildOnTypeFormattingTests(): TestCase[] {
  const extraFormatConfig: Array<[string, unknown]> = [
    ["editor.formatOnType", true],
    ["editor.insertSpaces", true],
    ["editor.tabSize", 2],
  ];

  const skip = () => {
    if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST !== "1" || !python3Available()) {
      throw new SkipTest();
    }
  };

  return [
    {
      name: "newline indents modules list",
      run: async () => {
        skip();
        await startServer(extraFormatConfig);

        const document = await vscode.workspace.openTextDocument({
          language: "docassemble",
          content: "modules:\n  - utils\n\n",
        });
        await vscode.window.showTextDocument(document);
        const pos = new vscode.Position(2, 0);

        const edits = await vscode.commands.executeCommand<vscode.TextEdit[]>(
          "vscode.executeFormatOnTypeProvider",
          document.uri,
          pos,
          "\n",
          { insertSpaces: true, tabSize: 2 },
        );

        assert.ok(edits && edits.length > 0, "Expected format-on-type edits");
        assert.ok(
          edits![0].newText.startsWith("  - "),
          `Expected newText to start with "  - ", got "${edits![0].newText}"`,
        );
      },
    },
    {
      name: "newline indents include list",
      run: async () => {
        skip();
        await startServer(extraFormatConfig);

        const document = await vscode.workspace.openTextDocument({
          language: "docassemble",
          content: "include:\n  - other.yml\n\n",
        });
        await vscode.window.showTextDocument(document);
        const pos = new vscode.Position(2, 0);

        const edits = await vscode.commands.executeCommand<vscode.TextEdit[]>(
          "vscode.executeFormatOnTypeProvider",
          document.uri,
          pos,
          "\n",
          { insertSpaces: true, tabSize: 2 },
        );

        assert.ok(edits && edits.length > 0, "Expected format-on-type edits");
        assert.ok(
          edits![0].newText.startsWith("  - "),
          `Expected newText to start with "  - ", got "${edits![0].newText}"`,
        );
      },
    },
    {
      name: "newline indents objects list",
      run: async () => {
        skip();
        await startServer(extraFormatConfig);

        const document = await vscode.workspace.openTextDocument({
          language: "docassemble",
          content: "objects:\n  - person: Name\n\n",
        });
        await vscode.window.showTextDocument(document);
        const pos = new vscode.Position(2, 0);

        const edits = await vscode.commands.executeCommand<vscode.TextEdit[]>(
          "vscode.executeFormatOnTypeProvider",
          document.uri,
          pos,
          "\n",
          { insertSpaces: true, tabSize: 2 },
        );

        assert.ok(edits && edits.length > 0, "Expected format-on-type edits");
        assert.ok(
          edits![0].newText.startsWith("  - "),
          `Expected newText to start with "  - ", got "${edits![0].newText}"`,
        );
      },
    },
  ];
}

export async function runTests(): Promise<void> {
  const tests: TestCase[] = [
    {
      name: "defaults docassemble indentation to 2 spaces",
      run: async () => {
        await updateConfiguration("docassemble-lsp.enabled", false);

        const document = await vscode.workspace.openTextDocument({
          language: "docassemble",
          content: "---\n",
        });
        const editor = await vscode.window.showTextDocument(document);

        assert.equal(editor.options.tabSize, 2);
        assert.equal(editor.options.insertSpaces, true);
      },
    },
    {
      name: "stays healthy when the language server is disabled",
      run: async () => {
        await updateConfiguration("docassemble-lsp.enabled", false);

        const api = await getApi();

        const state = await waitForState(api, "disabled");
        assert.equal(state.state, "disabled");
      },
    },
    {
      name: "handles empty fromEnvironment command gracefully",
      run: async () => {
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration("docassemble-lsp.command", "");

        const api = await getApi();
        await api.restart();

        // The server may land in "running" (if docassemble-lsp is installed),
        // "missing" (if no python3), or "error" (if process failed).
        // The important thing is activation doesn't crash.
        await waitFor(() => {
          const s = api.getServerState();
          return s.state === "running" || s.state === "missing" || s.state === "error";
        });
      },
    },
    {
      name: "starts with a configured command",
      run: async () => {
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
      name: "formats on type through the language server",
      run: async () => {
        const logPath = path.join(os.tmpdir(), `docassemble-mock-lsp-${Date.now()}.log`);

        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          `${quoteForShell(process.execPath)} ${quoteForShell(mockServerPath())}`,
        );
        await updateConfiguration("docassemble-lsp.env", { DOCASSEMBLE_MOCK_LOG: logPath });

        const api = await getApi();
        await api.restart();
        await waitForState(api, "running");

        const document = await vscode.workspace.openTextDocument({
          language: "docassemble",
          content: "fields: {",
        });
        await vscode.window.showTextDocument(document);

        const position = new vscode.Position(0, 8); // after "{"
        const edits = await vscode.commands.executeCommand<vscode.TextEdit[]>(
          "vscode.executeFormatOnTypeProvider",
          document.uri,
          position,
          "{",
          { insertSpaces: true, tabSize: 2 },
        );

        assert.ok(edits && edits.length > 0, "Expected format-on-type edits from mock server");

        await waitFor(() => readLog(logPath).includes("textDocument/onTypeFormatting"));
      },
    },
    {
      name: "clears docassemble diagnostics after switching language mode to yaml",
      run: async () => {
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

        const yamlDocument = await vscode.languages.setTextDocumentLanguage(document, "yaml");

        assert.equal(yamlDocument.languageId, "yaml");
        await waitFor(() => vscode.languages.getDiagnostics(yamlDocument.uri).length === 0);
      },
    },
    {
      name: "starts with local docassemble-lsp via uv",
      run: async () => {
        const lspProject = process.env.DOCASSEMBLE_LSP_PROJECT;
        if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST !== "1" || !lspProject) {
          throw new SkipTest();
        }

        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "fromEnvironment");
        await updateConfiguration(
          "docassemble-lsp.command",
          `uv run --project ${quoteForShell(lspProject)} docassemble-lsp lsp`,
        );

        const api = await getApi();
        await api.restart();

        const state = await waitForState(api, "running");
        assert.match(state.resolvedCommand ?? "", /docassemble-lsp lsp$/);
      },
    },
    {
      name: "starts bundled server via interpreter",
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

        const state = await waitForState(api, "running");
        assert.match(state.resolvedCommand ?? "", /python.*run_server\.py$/);
      },
    },
    {
      name: "publishes diagnostics for invalid YAML key via bundled server",
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

        await waitFor(() => {
          const diags = vscode.languages.getDiagnostics(document.uri);
          return diags.some((d) => String(d.code) === "E301");
        });
      },
    },
    {
      name: "provides completions via bundled server",
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
          content: "question:\n  ",
        });
        await vscode.window.showTextDocument(document);
        const pos = new vscode.Position(1, 2);

        const items = await vscode.commands.executeCommand<vscode.CompletionList>(
          "vscode.executeCompletionItemProvider",
          document.uri,
          pos,
        );

        assert.ok(items, "Expected a completion list");
        assert.ok(items.items.length > 0, "Expected at least one completion item");
      },
    },
    {
      name: "provides hover info via bundled server",
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
          content: "question: |\n  test\n",
        });
        await vscode.window.showTextDocument(document);

        const hovers = await vscode.commands.executeCommand<vscode.Hover[]>(
          "vscode.executeHoverProvider",
          document.uri,
          new vscode.Position(0, 1),
        );

        assert.ok(hovers && hovers.length > 0, "Expected at least one hover result");
        assert.ok(hovers[0].contents.length > 0, "Expected hover content");
      },
    },
    {
      name: "provides document symbols via bundled server",
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
          content: "question: |\n  test\ncode: |\n  x = 1\n",
        });
        await vscode.window.showTextDocument(document);

        const symbols = await vscode.commands.executeCommand<vscode.DocumentSymbol[]>(
          "vscode.executeDocumentSymbolProvider",
          document.uri,
        );

        assert.ok(symbols && symbols.length > 0, "Expected document symbols");
      },
    },
    {
      name: "provides code actions for invalid key via bundled server",
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

        assert.ok(codeActions && codeActions.length > 0, "Expected code actions for diagnostic");
      },
    },
    {
      name: "provides fix-all code action for C102 conventions via bundled server",
      run: async () => {
        if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST !== "1" || !python3Available()) {
          throw new SkipTest();
        }

        const workspaceDir = process.env.DOCASSEMBLE_TEST_WORKSPACE;
        if (!workspaceDir) {
          throw new Error("DOCASSEMBLE_TEST_WORKSPACE not set");
        }

        // Write pyproject.toml enabling C102 conventions
        await fs.promises.writeFile(
          path.join(workspaceDir, "pyproject.toml"),
          '[tool.docassemble-lsp]\nconventions = ["C102"]\n',
          "utf-8",
        );

        // Write test YAML with C102 shorthand patterns
        const yamlUri = await writeTestFile(
          workspaceDir,
          "fix_all_shorthand.yml",
          "question: Hi\nfields:\n  - Name: user.name\n  - Age: user.age\n",
        );

        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        const api = await getApi();
        await api.restart();
        await waitForState(api, "running");

        const document = await vscode.workspace.openTextDocument(yamlUri);
        await vscode.window.showTextDocument(document);

        // Wait for C102 diagnostics
        await waitFor(() =>
          vscode.languages.getDiagnostics(document.uri).some((d) => String(d.code) === "C102"),
        );

        const codeActions = await vscode.commands.executeCommand<vscode.CodeAction[]>(
          "vscode.executeCodeActionProvider",
          document.uri,
          new vscode.Range(0, 0, 4, 0),
        );

        const fixAll = codeActions?.find((a) => a.kind?.value === "source.fixAll.docassemble-lsp");
        assert.ok(fixAll, "Expected fix-all code action");
        assert.equal(fixAll.title, "Fix all auto-fixable docassemble-lsp issues");

        // Apply the fix-all edit and verify the document content
        assert.ok(fixAll.edit, "Expected fix-all edit");
        const applied = await vscode.workspace.applyEdit(fixAll.edit);
        assert.ok(applied, "Expected edit to apply successfully");

        const text = document.getText();
        assert.ok(
          text.includes("label: Name\n    field: user.name"),
          "Expected Name shorthand expanded to explicit keys",
        );
        assert.ok(
          text.includes("label: Age\n    field: user.age"),
          "Expected Age shorthand expanded to explicit keys",
        );
      },
    },
    {
      name: "provides fix-all code action for C103 input-type datatype convention via bundled server",
      run: async () => {
        if (process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST !== "1" || !python3Available()) {
          throw new SkipTest();
        }

        const workspaceDir = process.env.DOCASSEMBLE_TEST_WORKSPACE;
        if (!workspaceDir) {
          throw new Error("DOCASSEMBLE_TEST_WORKSPACE not set");
        }

        // Write pyproject.toml enabling C103 conventions
        await fs.promises.writeFile(
          path.join(workspaceDir, "pyproject.toml"),
          '[tool.docassemble-lsp]\nconventions = ["C103"]\n',
          "utf-8",
        );

        // Write test YAML with datatype: hidden (should suggest input type: hidden)
        const yamlUri = await writeTestFile(
          workspaceDir,
          "fix_all_input_type_datatype.yml",
          "question: Hi\nfields:\n  - label: Ex\n    field: x\n    datatype: hidden\n",
        );

        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        const api = await getApi();
        await api.restart();
        await waitForState(api, "running");

        const document = await vscode.workspace.openTextDocument(yamlUri);
        await vscode.window.showTextDocument(document);

        // Wait for C103 diagnostics
        await waitFor(() =>
          vscode.languages.getDiagnostics(document.uri).some((d) => String(d.code) === "C103"),
        );

        const codeActions = await vscode.commands.executeCommand<vscode.CodeAction[]>(
          "vscode.executeCodeActionProvider",
          document.uri,
          new vscode.Range(0, 0, 4, 0),
        );

        const fixAll = codeActions?.find((a) => a.kind?.value === "source.fixAll.docassemble-lsp");
        assert.ok(fixAll, "Expected fix-all code action");
        assert.equal(fixAll.title, "Fix all auto-fixable docassemble-lsp issues");

        // Apply the fix-all edit and verify the document content
        assert.ok(fixAll.edit, "Expected fix-all edit");
        const applied = await vscode.workspace.applyEdit(fixAll.edit);
        assert.ok(applied, "Expected edit to apply successfully");

        const text = document.getText();
        assert.ok(
          text.includes("input type: hidden"),
          "Expected datatype: hidden replaced with input type: hidden",
        );
      },
    },
    {
      name: "starts with Python extension integration",
      run: async () => {
        if (!pythonExtensionAvailable()) {
          throw new SkipTest();
        }

        await resetConfiguration();
        await updateConfiguration("docassemble-lsp.enabled", true);
        await updateConfiguration("docassemble-lsp.importStrategy", "useBundled");
        await updateConfiguration("docassemble-lsp.interpreter", []);

        const api = await getApi();
        await api.restart();

        const state = await waitForState(api, "running");
        assert.ok(state.resolvedCommand, "Expected a resolved interpreter command");
        assert.doesNotMatch(
          state.resolvedCommand ?? "",
          /python3$/,
          "Expected Python extension to resolve a real interpreter, not fallback",
        );
      },
    },
    // ---- Real-server integration tests (gated) ----
    ...buildModuleCompletionTests(),
    ...buildIncludeCompletionTests(),
    ...buildOnTypeFormattingTests(),
  ];

  console.log("\n  Docassemble extension");

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
      console.error(`  ${index + 1}) Docassemble extension`);
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

function pythonExtensionAvailable(): boolean {
  return (
    process.env.DOCASSEMBLE_LSP_ENABLE_REAL_TEST === "1" &&
    !!vscode.extensions.getExtension("ms-python.python")
  );
}

function readLog(logPath: string): string {
  try {
    return fs.readFileSync(logPath, "utf8");
  } catch {
    return "";
  }
}
