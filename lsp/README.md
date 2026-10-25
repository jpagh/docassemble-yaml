# docassemble-lsp

Language server and command-line checker for [Docassemble](https://docassemble.org)
interview YAML. A shared workspace model gives interviews diagnostics,
completion, hover, navigation, formatting, and code actions; the CLI and editor
integrations are thin adapters over it.

## Installation

The package is published to PyPI as `docassemble-lsp`:

```bash
uv tool install docassemble-lsp
# or: pipx install docassemble-lsp
# or: pip install docassemble-lsp
```

This installs the `docassemble-lsp` command. Editors launch it in language
server mode over stdio (`docassemble-lsp lsp`).

## CLI

Validate interviews:

```bash
docassemble-lsp check path/to/interview.yml
```

List known diagnostic codes, severities, and summaries:

```bash
docassemble-lsp codes
```

Fail on warnings and conventions as well as errors:

```bash
docassemble-lsp check --strict path/to/interview.yml
```

This is useful for pre-commit or pre-deploy gates where you want any reported finding to block the build, while still preserving the original diagnostic severities in the output.

Example pre-commit hook:

```yaml
- repo: local
  hooks:
    - id: docassemble-lsp-check
      name: docassemble-lsp check
      entry: docassemble-lsp check --strict
      language: system
      files: '\.(ya?ml)$'
```

From a source checkout, the same commands run as `uv run python -m docassemble_lsp ...`.

## Editors

### VS Code

A VS Code extension connects to this language server and brings Docassemble YAML support into the editor. The extension source is at [`vscode/`](https://github.com/jpagh/docassemble-yaml/tree/main/vscode) in this repository; its [`README.md`](https://github.com/jpagh/docassemble-yaml/blob/main/vscode/README.md) covers installation and development.

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

#### Extension Configuration

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

#### Troubleshooting Completions

If autocomplete isn't showing classes or custom datatypes you expect:

- **Just created a new `.py` file?** Save any YAML file in the package. The LSP rebuilds its workspace index on save.
- **Installed a new docassemble package in `.venv`?** Restart the language server (Cmd+Shift+P → "Docassemble: Restart Language Server").
- **Renamed a class or datatype?** Save any YAML file to trigger a re-index.

The LSP uses a flat "over-offer" model: it indexes every Python module in your package and makes all classes available in completions, regardless of which YAML file declares the ``modules:`` directive. Docassemble catches any out-of-scope classes at runtime.

### Fresh

The [`fresh/`](https://github.com/jpagh/docassemble-yaml/tree/main/fresh) bundle adds Docassemble syntax highlighting, interview detection, and LSP wiring for the [Fresh](https://github.com/sinelaw/fresh) terminal editor. It launches this server as `docassemble-lsp lsp`; see [`fresh/README.md`](https://github.com/jpagh/docassemble-yaml/blob/main/fresh/README.md) for installation and configuration.

### Kakoune

The [`kakoune/`](https://github.com/jpagh/docassemble-yaml/tree/main/kakoune) bundle provides Docassemble detection, giallo highlighting and optional kakoune-lsp v22 stdio wiring. See [`kakoune/README.md`](https://github.com/jpagh/docassemble-yaml/blob/main/kakoune/README.md) for [installation](https://github.com/jpagh/docassemble-yaml/blob/main/kakoune/README.md#install), [LSP configuration](https://github.com/jpagh/docassemble-yaml/blob/main/kakoune/README.md#optional-diagnostics-completion-and-hover), [troubleshooting](https://github.com/jpagh/docassemble-yaml/blob/main/kakoune/README.md#lsp-troubleshooting), and the [version-pinned support matrix](https://github.com/jpagh/docassemble-yaml/blob/main/kakoune/README.md#verified-support-matrix). Cross-file navigation, formatting (including whole-document edit range and idempotence) and a quick-fix edit are exercised with the committed demo package; UI boundaries and optional semantic tokens are documented explicitly.

## Project Documentation

The internal architecture and implementation roadmap live under `docs/` in the repository:

- [`docs/ARCHITECTURE.md`](https://github.com/jpagh/docassemble-yaml/blob/main/docs/ARCHITECTURE.md) explains the shared LSP/CLI architecture and service boundaries.
- [`docs/SUBAGENT_GUIDE.md`](https://github.com/jpagh/docassemble-yaml/blob/main/docs/SUBAGENT_GUIDE.md) gives small implementation agents a safe workflow for future changes.
- [`docs/FEATURE_PATTERNS.md`](https://github.com/jpagh/docassemble-yaml/blob/main/docs/FEATURE_PATTERNS.md) documents where each feature family should be extended.
- [`docs/ROADMAP.md`](https://github.com/jpagh/docassemble-yaml/blob/main/docs/ROADMAP.md) tracks the current release-readiness and hardening plan.
- [`docs/INVENTORY.md`](https://github.com/jpagh/docassemble-yaml/blob/main/docs/INVENTORY.md) records the baseline Docassemble YAML key support surface.

## Fixtures And Development

The repo keeps a small package fixture modeled on a real Docassemble app include stack at `tests/fixtures/demo_package`. It mirrors the `main.yml -> x_main_include.yml -> x_events.yml` shape from a larger package while staying small enough for CI-backed navigation tests.

For local smoke testing against a real package checkout during development:

```bash
uv run python -m docassemble_lsp check /path/to/docassemble-demo/docassemble/demo/data/questions
```

That real-package run is useful for manual validation, but tests should keep using the checked-in fixture so CI does not depend on an external repository.
