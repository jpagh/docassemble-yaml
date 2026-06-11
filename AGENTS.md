# docassemble-lsp

First stop for repo-specific agent guidance. See `lsp/docs/` for
architecture, feature patterns, and subagent handoffs.

## Setup

- Python >=3.10, `uv` as package/dependency manager
- `uv venv && uv sync --group dev`
- Always `uv run` — never invoke tools from `.venv` directly

## Commands

| Purpose | Command |
|---------|---------|
| LSP tests | `just lsp test` |
| All Python versions | `just lsp test-versions` |
| Type check | `just lsp type` |
| Lint + fix | `just lsp lint` |
| Format | `just lsp format` |
| Full hooks check | `prek run -a` |
| CLI validate | `uv run python -m docassemble_lsp check path/to/file.yml` |
| List diagnostic codes | `uv run python -m docassemble_lsp codes` |
| Regenerate vendored stubs | `uv run lsp/scripts/update_vendored_docassemble_base_util.py` |
| Extension tests | `just vscode test` |
| Real extension tests | `just vscode test-real` |
| Extension smoke | `just test-real-smoke` |
| Version bump | `just bump` |

## Architecture

- **CLI** (`cli.py:main`) and **LSP** (`lsp/server.py`) — two entry points
- `WorkspaceIndex` owns all YAML sources, open-document overlays, Python caches
- `DocumentFacts` exposes reusable YAML structure (blocks, fields, events, includes)
- `CompletionRegistry` owns scopes, rules, snippets, duplicate-key policy
- Feature services (diagnostics, completions, hover, definitions, references, etc.) query shared facts/index
- `lsp/server.py` is a thin protocol adapter

## Implementation Workflow

Before coding: 1) CLI-visible, LSP-visible, or both? 2) Local or workspace-aware?
3) Schema-backed, fact-backed, Python-aware, or protocol-only?
4) Closest feature family? 5) First validation target (test file)?

If touching Docassemble YAML keys/values, check `completion_rules.py` and `validation.py` first.

## Code style

- Ruff for lint + formatting, line-length 120
- mypy for type checking (excludes `^build/|^src/docassemble_lsp/data/`)
- Vendored stubs in `src/docassemble_lsp/data/*.pyi`

## Feature Routing

| Work type | Start with | Focused tests |
|-----------|------------|---------------|
| Completion / hover | `completion_context.py`, `completion_registry.py`, `completion_rules.py`, `schema.py` | `test_schema.py`, `test_lsp.py` |
| Diagnostics / fixes | `diagnostics.py`, `validation.py`, `messages.py`, `fixes.py` | `test_diagnostics.py`, `test_cli.py`, `test_lsp.py` |
| Definitions / references | `definitions.py`, `workspace_navigation.py`, `workspace_symbols.py`, `python_navigation.py`, `python_modules.py` | `test_definitions.py`, `test_references_integration.py`, `test_lsp.py` |
| Formatting / indentation | `formatting.py`, `indentation.py`, `lsp/server.py` | `test_formatting.py`, `test_lsp.py`, `test_lsp_process.py` |
| Document links / protocol | `document_links.py`, `lsp/server.py` | `test_lsp.py`, `test_lsp_process.py` |
| Python navigation | `python_navigation.py`, `python_modules.py`, `definitions.py` | `test_definitions.py`, `test_lsp.py`, `test_references_integration.py` |

## Test files

- `test_schema.py`, `test_lsp.py` — completion/hover internals, LSP integration
- `test_lsp_process.py` — protocol-level sessions
- `test_definitions.py`, `test_references_integration.py` — semantic navigation
- `test_diagnostics.py`, `test_cli.py` — validation rules and CLI surface
- `test_formatting.py` — formatting
- `test_document_facts.py`, `test_core_api.py`, `test_workspace.py` — core API
- `test_inventory.py`, `test_vendor_checker_cli.py` — drift and stub checks

## Versioning

CalVer (`YY.MM.patch`). Both `lsp/` and `vscode/` updated together.
`just bump` (default: patch) from root. Updates `lsp/pyproject.toml`,
`vscode/package.json`, `vscode/CHANGELOG.md`, then commits and tags.

## Operational notes

- macOS: prefix imports of `docassemble.base.*` with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
- Read `.venv/lib/python*/site-packages/docassemble/base/parse.py` for parser behavior

## Common gotchas

- Don't add workspace crawls — `WorkspaceIndex` already has the data
- Use document overlays, not filesystem, in LSP features
- Rename is intentionally narrow (`def`, `event` only)
- Keep Docassemble/Python static analysis conservative where runtime is dynamic
- Cross-check `docassemble.base.parse` before changing parser-backed rules

Read `lsp/docs/SUBAGENT_GUIDE.md` before making changes.
