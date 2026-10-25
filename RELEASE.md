# Release Contract

Release contract for `docassemble-yaml` (LSP + VS Code extension). Internal-facing — for longer docs see `docs/`.

## How to Release

```bash
mise run //vscode:test       # extension tests (mock server)
DOCASSEMBLE_LSP_ENABLE_REAL_TEST=1 mise run //vscode:test:real-lsp  # full real-server extension tests

mise run deploy              # gate, bump, publish VSIX, create the GitHub Release
```

`mise run deploy` runs, in order:

1. `gate` — the full pre-release check.
2. `bump` — bumps `lsp/pyproject.toml`, `vscode/package.json`, `CHANGELOG.md`, and `VERSION`, commits, and pushes the `v{new_version}` tag.
3. `//vscode:publish` — packages and publishes the VSIX.
4. `release:github` — creates the GitHub Release whose body is the new `CHANGELOG.md` section followed by GitHub's auto-generated notes. Publishing that release triggers the PyPI workflow (below).

The steps are separate tasks, so a failure after the bump does not force another version: retry with `mise run release:github` (or `mise run //vscode:publish`) directly. `mise run publish` is the same as `deploy` without the release step.

To inspect the release notes without touching GitHub:

```bash
scripts/github-release.sh --dry-run
```

Build the VSIX alone from `vscode/`:
```bash
mise run //vscode:package
```

## PyPI Publishing

`docassemble-lsp` is published to PyPI from `lsp/` by
`.github/workflows/python-publish.yml`, using PyPI **Trusted Publishing** (OIDC, no
API token secret). The workflow runs when a GitHub Release is published, or on
manual `workflow_dispatch`.

It builds the sdist and wheel with `uv build` and refuses to publish when the
release tag does not match the version in `lsp/pyproject.toml` (the version
`mise run bump` updates), so a release created from a stale tag fails instead
of publishing the wrong package.

One-time setup:

- PyPI → Account → Publishing → **Add a new pending publisher**:
  - PyPI project name: `docassemble-lsp`
  - Owner: `jpagh`
  - Repository name: `docassemble-yaml`
  - Workflow name: `python-publish.yml`
  - Environment name: `pypi`
- GitHub → repository Settings → Environments → create `pypi` (optionally add
  required reviewers). The name must match the workflow's `environment` and the
  PyPI publisher.

## Pre-release Gate

The automated gate must be green:

```bash
mise run //lsp:check
```

This runs ruff, pyrefly, and the full pytest suite across all supported Python versions. The following test areas are the gate:

- Diagnostics + validator parity: `test_diagnostics.py`, `test_cli.py`
- Completion + hover + schema parity: `test_schema.py`, `test_lsp.py`
- Process-level LSP sessions: `test_lsp_process.py`
- Protocol features: `test_lsp.py`, `test_lsp_process.py`
- Document facts + core API: `test_document_facts.py`, `test_core_api.py`
- Definitions + references: `test_definitions.py`, `test_lsp.py`, `test_references_integration.py`
- Formatting: `test_formatting.py`, `test_lsp.py`

## Shared Grammar Gate

The root `mise run check` includes shared conversion-output tests and direct,
unmodified shipped TextMate fixture assertions (`//grammars:check`), Fresh
manifest/generated-artifact checks, and VS Code build/packaging-copy checks.
The root release `gate` additionally retains syntect parity against the explicitly
transformed compatibility reference (`//tools/scope-parity:gate`). These are
different guarantees: compatibility-reference parity does not assert equivalence
to the unmodified shipped TextMate grammar. See
[`grammars/README.md`](grammars/README.md) for ownership and regeneration, and the
[harness exceptions](tools/scope-parity/README.md#existing-reference-patches).

## Extension Status

The VS Code extension lives at `vscode/` in this monorepo. 1.0.0 has been shipped (VSIX built, version bumped). The extension test suite has 13 tests covering:

| Feature | Coverage |
|---------|----------|
| Server start (mock, bundled, local via uv) | 3 tests |
| Format on type | 1 test (mock server) |
| Diagnostics (E301 only) | 1 test (real server) |
| Completions (smoke) | 1 test (real server) |
| Hover (smoke) | 1 test (real server) |
| Document symbols (smoke) | 1 test (real server) |
| Code actions (E301 only) | 1 test (real server) |
| Language switch diagnostic clear | 1 test (mock server) |
| Disabled-state health | 1 test |
| Empty command handling | 1 test |

**Gaps**: definitions, references, workspace symbols, document links, rename, semantic tokens, folding, signature help — no extension-level test coverage.

## Extension Gate

Run before each release. Current gate:

- `mise run //vscode:test` — runs all 13 tests against mock server
- `DOCASSEMBLE_LSP_ENABLE_REAL_TEST=1 mise run //vscode:test:real-lsp` — runs real-server tests

A full extension gate (matching the aspirational assertion list in the v0 RELEASE_GATE) remains future work. See the gaps above.

## Capability Matrix

Ratings: `yes` = supported, `partial` = exists but needs sharper coverage/UX, `planned` = good fit for architecture, `no` = out of scope.

| Concept | Completion | Diagnostic | Hover | Definition | References | Notes |
|---------|-----------|-----------|-------|-----------|-----------|-------|
| Top-level keys | yes | yes | yes | yes | yes | Schema-backed keys, docs, snippets. Definitions/references now cover file references within top-level blocks. |
| Scoped block keys | yes | yes | yes | yes | yes | Fields, metadata, attachment, review, grid, and related nested scopes. |
| Enum-like values | yes | yes | yes | partial | planned | Completion/hover/diagnostics share registered enum values. Definition resolves custom datatype classes only. |
| Field variables | yes | yes | yes | yes | yes | Declarations and `show if`/`hide if` references fully navigable. |
| `event` blocks | yes | yes | yes | yes | yes | Cross-document reference validation included. |
| `def` blocks & `usedefs` | partial | yes | yes | yes | yes | Completion doesn't dynamically suggest existing `def` names as values. |
| Include YAML files | yes | yes | yes | yes | yes | Local and package-qualified includes navigable as document links and definition targets. |
| Package-qualified files | partial | yes | yes | yes | yes | Completion explicitly excludes `package:path` (manual typing). Resolution works. |
| Asset/template files | yes | yes | yes | yes | yes | File-valued keys (`.docx`, `.pdf`, etc.) with path completion and existence checks. |
| Python modules/imports | yes | yes | yes | yes | yes | Module and symbol navigation for installed/vendored packages. Missing-module diagnostics. |
| Python expressions in YAML | yes | yes | partial | yes | yes | Hover works for registered symbols, not raw expressions. |
| Mako/Jinja regions | partial | yes | partial | yes | yes | Mako completions exist; Jinja has no completion provider. Hover limited to known symbols. |
| Formatting | no | no | no | no | no | Whole-document formatting and on-type indentation are independent LSP features, not concept-specific. |
| Deterministic fixes | no | yes | no | no | no | Quick fixes and fix-all for safe, deterministic rewrites. |

## Architecture

Current implementation:

- `WorkspaceIndex`: workspace YAML sources, multi-document overlays, document facts, package roots, Python/module caches
- `DocumentFacts`: reusable YAML document structure (blocks, fields, events, defs, includes, assets, Python/template regions)
- `CompletionRegistry`: scopes, rules, snippets, duplicate-key policy
- Feature services (diagnostics, completion, hover, definition, references, workspace symbols, document links, formatting) share the common index — `lsp/server.py` is a thin protocol adapter

## Release Boundary

The current gate assumes this surface:

- diagnostics, completion, hover, document symbols
- definitions, references, workspace symbols
- document links (local file-like references and package-qualified)
- field-variable definitions and references
- semantic tokens (conservative Docassemble regions)
- formatting (whole-document and on-type indentation)
- small deterministic code actions

Not in scope: speculative type inference, runtime execution, unbounded refactors.

## README Policy

Keep `README.md` aligned with the capability matrix. If a feature moves from `partial`/`planned` to `yes`, update the README to reflect it.
