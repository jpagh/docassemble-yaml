# docassemble-lsp

Use this file as the first stop for repo-specific agent guidance. For
deeper detail, read:

- `docs/ARCHITECTURE.md` for the internal layer model and invariants
- `docs/FEATURE_PATTERNS.md` for feature-family workflows
- `docs/SUBAGENT_GUIDE.md` for bounded implementation handoffs
- `RELEASE_GATE.md` for the release contract and automated gate
- `docs/ROADMAP.md` for current release-readiness priorities

## Setup

- Python >=3.10, uses `uv` as package/dependency manager
- `uv venv && source .venv/bin/activate`
- `uv sync --group dev` (dev deps: docassemble-base,
  docassemble-webapp, mypy, pytest, pytest-cov)
- Always `uv run` — never invoke tools from `.venv` directly

## Commands

| Purpose | Command |
|---------|---------|
| Full test suite | `uv run pytest -q -n auto` (or `just test`) |
| Single test file | `uv run pytest tests/test_lsp.py -q` |
| Single test | `uv run pytest tests/test_lsp.py::test_foo -q` |
| Type check | `uv run mypy .` (or `just type`) |
| Lint + auto-fix | `uv run ruff check --fix` |
| Format | `uv run ruff format` |
| Everything check | `prek run -a` (all hooks: vendored stubs, taplo, Ruff, mypy, pytest) |
| Faster CI check | `uv run ruff check --fix && just test type` |
| CLI validate | `uv run python -m docassemble_lsp check path/to/file.yml` |
| List diagnostic codes | `uv run python -m docassemble_lsp codes` |
| Regenerate vendored stubs | `uv run python scripts/update_vendored_docassemble_base_util.py` |
| Semantic diff (code review) | `sem diff` (use like `git diff`; adds semantic information to comparisons) |

`justfile` is intentionally small: `just test`, `just type`, and
`just test-versions`. `prek run -a` is the all-hook check from
`prek.toml`; it also formats TOML and regenerates vendored stubs, so
it is broader than the normal feature-development gate.

## Architecture

- Two entry points: `src/docassemble_lsp/cli.py:main` and
  `src/docassemble_lsp/lsp/server.py` (LSP over stdio)
- The LSP is single-root/single-project; other Docassemble packages
  and Python modules are dependencies, not separate workspace roots
- Stable contract: CLI behavior and LSP protocol behavior. Internal
  Python APIs can change when that improves the design
- Shared core API in `src/docassemble_lsp/core/__init__.py`; semantic
  logic belongs in `src/docassemble_lsp/core/`
- `src/docassemble_lsp/lsp/server.py` should stay a thin adapter for
  protocol translation and index lifecycle
- `WorkspaceIndex` (`src/docassemble_lsp/core/workspace.py`) owns
  workspace YAML sources, open-document overlays, document facts,
  package roots, and Python/module caches
- Include graphs and asset references are derived by focused services
  such as `workspace_navigation.py` and `document_links.py`, not owned
  by `WorkspaceIndex`
- `DocumentFacts` (`src/docassemble_lsp/core/document_facts.py`) is
  the reusable document-structure layer
- Completion behavior belongs in `completion_context.py` /
  `completion_registry.py` / `completion_rules.py`, with `schema.py`
  kept as a facade

## Implementation Workflow

Before coding, answer these questions:

1. Is this CLI-visible, LSP-visible, or both?
2. Is the behavior local to one document or workspace-aware?
3. Is it schema-backed, document-fact-backed, Python-aware, or
   protocol-only?
4. Which existing feature family is the closest architectural match?
5. Which focused test file is the first validation target?

If the request touches Docassemble YAML keys, values, completions,
hover, parser-backed diagnostics, or invalid combinations, inspect the
current rule data in `completion_rules.py` and `validation.py` before
changing behavior.

## Feature Routing

| Work type | Start with | Focused tests |
|-----------|------------|---------------|
| Completion / hover | `completion_context.py`, `completion_registry.py`, `completion_rules.py`, `schema.py` | `tests/test_schema.py`, `tests/test_lsp.py` |
| Diagnostics / fixes | `diagnostics.py`, `validation.py`, `messages.py`, `fixes.py` | `tests/test_diagnostics.py`, `tests/test_cli.py`, `tests/test_lsp.py` |
| Definitions / references | `definitions.py`, `workspace_navigation.py`, `workspace_symbols.py`, `python_navigation.py`, `python_modules.py` | `tests/test_definitions.py`, `tests/test_references_integration.py`, `tests/test_lsp.py` |
| Formatting / on-type indentation | `formatting.py`, `indentation.py`, `lsp/server.py` | `tests/test_formatting.py`, `tests/test_lsp.py`, `tests/test_lsp_process.py` |
| Document links / protocol features | `document_links.py`, `lsp/server.py` | `tests/test_lsp.py`, `tests/test_lsp_process.py` |
| Python-aware navigation / completion | `python_navigation.py`, `python_modules.py`, `definitions.py` | `tests/test_definitions.py`, `tests/test_lsp.py`, `tests/test_references_integration.py` |

## Code style

- Ruff for lint + formatting, line-length 120
- mypy for type checking (excludes
  `^build/|^src/docassemble_lsp/data/`)
- VS Code: ruff as formatter, organize imports on save
- Vendored Docassemble stubs live in `src/docassemble_lsp/data/*.pyi`;
  regenerate them with the script in the command table

## Test file mapping

| File | Coverage |
|------|----------|
| `test_schema.py` | Completion/hover internals |
| `test_lsp.py` | LSP adapter + feature integration |
| `test_lsp_process.py` | Protocol-level sessions |
| `test_definitions.py` | Semantic navigation |
| `test_references_integration.py` | Multi-file navigation |
| `test_diagnostics.py` | Validation rules |
| `test_cli.py` | CLI surface |
| `test_formatting.py` | Formatting |
| `test_document_facts.py` | Document facts |
| `test_core_api.py` | Public core API |
| `test_workspace.py` | WorkspaceIndex |
| `test_inventory.py` | Documentation/inventory drift checks |
| `test_vendor_checker_cli.py` | Vendored stub checker CLI |

`tests/corpus.py` is a shared helper for corpus-backed completion and
diagnostic parity tests, not a standalone test file.

## Fixtures

- `tests/fixtures/demo_package/` is the canonical
  realistic multi-file Docassemble package fixture
- `tests/fixtures/regressions/` contains large regression YAML files;
  keep `id` values aligned with expected diagnostic codes
- `tests/fixtures/examples/` contains the repo-owned Docassemble demo
  YAML corpus for drift tests
- `tests/fixtures/reference_package/` provides reference package
  fixtures for package-resolution behavior

## Versioning

The monorepo uses a single CalVer version (`YY.MM.patch`).
Both `lsp/` and `vscode/` are updated together from the root.

```bash
bump-my-version patch   # 26.6.0 → 26.6.1
bump-my-version minor   # 26.6.0 → 26.7.0 (bump month)
bump-my-version release # 26.6.0 → 27.1.0 (bump year)
```

Shorthand: `just bump` (patch) from the repo root.

This updates `lsp/pyproject.toml`, `vscode/package.json`, and
`vscode/CHANGELOG.md`, then commits and tags (`v{new_version}`).

`RELEASE_GATE.md` is the release contract. `docs/ROADMAP.md` tracks
remaining release-readiness work and follow-up hardening.

## Operational notes

- On macOS, if you directly import `docassemble.base.*` or
  `docassemble.webapp.*` from the local environment, prefix the
  command with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` so
  native-library imports can resolve
- Reading
  `.venv/lib/python3.10/site-packages/docassemble/base/parse.py`
  directly can be more reliable than importing parser modules when
  checking upstream parser behavior

## Common gotchas

- Don't add workspace crawls — `WorkspaceIndex` already has the data
- Don't grow `schema.py` back into a monolith; completion logic
  belongs in `completion_*.py`
- Use document overlays, not filesystem content, in LSP features
  (stale unsaved buffers)
- Rename is intentionally narrow (`def` and `event` only) — don't
  broaden unsafely
- Keep completion, hover, and diagnostics aligned when touching
  schema-backed features
- Keep Docassemble/Python static analysis conservative where runtime
  behavior is dynamic
- For parser-backed YAML semantics, cross-check upstream docs and
  `docassemble.base.parse` before changing rules

Read `docs/SUBAGENT_GUIDE.md` before making changes — it has the full
implementation workflow.
