# docassemble-lsp

## Project Documentation

The internal architecture and implementation roadmap live under `docs/`:

- `docs/ARCHITECTURE.md` explains the shared LSP/CLI architecture and service boundaries.
- `docs/SUBAGENT_GUIDE.md` gives small implementation agents a safe workflow for future changes.
- `docs/FEATURE_PATTERNS.md` documents where each feature family should be extended.
- `docs/ROADMAP.md` tracks the current release-readiness and hardening plan.

## CLI

Validate interviews:

```bash
uv run python -m docassemble_lsp check path/to/interview.yml
```

List known diagnostic codes, severities, and summaries:

```bash
uv run python -m docassemble_lsp codes
```

Fail on warnings and conventions as well as errors:

```bash
uv run python -m docassemble_lsp check --strict path/to/interview.yml
```

This is useful for pre-commit or pre-deploy gates where you want any reported finding to block the build, while still preserving the original diagnostic severities in the output.

Example pre-commit hook:

```yaml
- repo: local
  hooks:
    - id: docassemble-lsp-check
      name: docassemble-lsp check
      entry: uv run python -m docassemble_lsp check --strict
      language: system
      files: '\.(ya?ml)$'
```

## VS Code Extension

A VS Code extension connects to this language server and brings Docassemble YAML support into the editor. The extension source is at [`../vscode/`](../vscode/) in this repository. See its [`README.md`](../vscode/README.md) for installation and development instructions.

Once installed, any `.yml` file inside a Docassemble package workspace opens with the following features active:

- **Diagnostics** — errors, warnings, and convention violations appear inline as you type and on save.
- **Completions** — top-level block keys, scoped sub-keys, enum values, and field variables are offered at the cursor position.
- **Hover** — hold the cursor over any supported key to see its documentation and allowed values.
- **Document symbols** — the outline panel lists all interview blocks in the current file.
- **Go to definition / find references** — navigate from an `event` name, `def` block, field variable, include path, or asset reference to its definition and find references across the workspace.
- **Workspace symbols** — search across the workspace for `event` and `def` entities with the symbol picker.
- **Document links** — local and package-qualified include paths and file-valued keys are ctrl-clickable.
- **Semantic highlighting** — well-known Docassemble code and template regions are exposed through semantic tokens.
- **Formatting** — whole-document formatting and on-type indentation for `fields` blocks.
- **Quick fixes** — deterministic fixes for known diagnostics such as field-shorthand convention violations.

### Extension Configuration

Convention rules can be enabled per project in `pyproject.toml`:

```toml
[tool.docassemble-lsp]
conventions = ["C102"]
```

The server resolves config per document — each file uses the nearest config found by walking up from the file's own directory — so no per-extension configuration is needed, and multi-root workspaces get per-project behavior: each project's files follow their own config file.

Projects without a `pyproject.toml` (e.g. a plain interview repository) can use a dedicated config file instead — `docassemble-lsp.toml`, `.docassemble-lsp.toml`, or `.config/docassemble-lsp.toml`, in that order of precedence within a directory:

```toml
conventions = ["C102"]
ignore-codes = ["E301"]
```

The server walks up to the nearest config file, and a dedicated file wins over the `[tool.docassemble-lsp]` pyproject section in the same directory. The dedicated files accept the same keys as the pyproject section (`conventions`, `ignore-codes`, `yaml_path`, `args`, `check_args`, `format_args`, `lsp_args`).

Explicit `--conventions`/`--ignore-codes` flags on the `lsp` command apply to every document on top of the per-project config. The generic `args`/`lsp_args` keys are read from the server's working directory only (not per project); prefer the structured `conventions` and `ignore-codes` keys for per-project behavior.

### Troubleshooting Completions

If autocomplete isn't showing classes or custom datatypes you expect:

- **Just created a new `.py` file?** Save any YAML file in the package. The LSP rebuilds its workspace index on save.
- **Installed a new docassemble package in `.venv`?** Restart the language server (Cmd+Shift+P → "Docassemble: Restart Language Server").
- **Renamed a class or datatype?** Save any YAML file to trigger a re-index.

The LSP uses a flat "over-offer" model: it indexes every Python module in your package and makes all classes available in completions, regardless of which YAML file declares the ``modules:`` directive. Docassemble catches any out-of-scope classes at runtime.

## Fixtures And Development

The repo keeps a small package fixture modeled on a real Docassemble app include stack at `tests/fixtures/demo_package`. It mirrors the `main.yml -> x_main_include.yml -> x_events.yml` shape from a larger package while staying small enough for CI-backed navigation tests.

For local smoke testing against a real package checkout during development:

```bash
uv run python -m docassemble_lsp check /path/to/docassemble-demo/docassemble/demo/data/questions
```

That real-package run is useful for manual validation, but tests should keep using the checked-in fixture so CI does not depend on an external repository.
