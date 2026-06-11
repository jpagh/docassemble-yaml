# Release Gate

This file defines the concrete v1 gate to use before treating a build
of `docassemble-lsp` as release-ready. It is intentionally
internal-facing and separate from the final README.

For the longer-form architecture and implementation plan, use the docs
set under `docs/`:

- `docs/ARCHITECTURE.md` defines the intended internal architecture.
- `docs/SUBAGENT_GUIDE.md` explains how to hand bounded work to small
  implementation agents.
- `docs/FEATURE_PATTERNS.md` documents feature-family implementation
  patterns.
- `docs/ROADMAP.md` tracks release-readiness and follow-up work.

## Automated Gate

The full automated suite must be green:

```bash
ruff check --fix && just test type
```

That runs the full pytest suite and mypy.

The following feature areas must remain covered by the committed test
suite:

- Diagnostics and validator parity:
  - `tests/test_diagnostics.py`
  - `tests/test_cli.py`
- Completion, hover, and schema parity:
  - `tests/test_schema.py`
  - `tests/test_lsp.py`
- Process-level LSP session coverage:
  - `tests/test_lsp_process.py`
- Protocol features including document links and semantic tokens:
  - `tests/test_lsp.py`
  - `tests/test_lsp_process.py`
- Document facts and public core API surface:
  - `tests/test_document_facts.py`
  - `tests/test_core_api.py`
- Definitions, references, and workspace symbols:
  - `tests/test_definitions.py`
  - `tests/test_lsp.py`
  - `tests/test_references_integration.py`
- Formatting:
  - `tests/test_formatting.py`
  - `tests/test_lsp.py`
- Diagnostic-backed code actions:
  - `tests/test_lsp.py`

The automated gate includes the committed regression fixtures under
`pytest`:

- `tests/test_cli.py` asserts the expected exit codes for:
  - `tests/fixtures/regressions/large_valid_interview.yml`
  - `tests/fixtures/regressions/large_invalid_interview.yml` -
    `tests/fixtures/regressions/large_warning_convention_interview.yml`
    -
    `tests/fixtures/demo_package/docassemble/demo/data/questions`
- `tests/test_diagnostics.py` asserts the expected diagnostic-code
  sets for the large regression fixtures and Jinja regressions.
- `tests/test_references_integration.py` covers the realistic package
  fixtures as semantic integration targets in addition to the CLI
  directory check above.

## Extension Status

An external VS Code extension has been built and connected to this
language server.

Current status:

- the language-server core is covered by automated tests
- the stdio/protocol boundary has process-level integration tests
- the VS Code extension exists outside this repository and can start
  the LSP
- committed CLI and fixture regression checks are already part of
  `pytest`
- there are no required manual CLI commands in the release gate
- `README.md` now documents the extension-backed workflow for end
  users
- 1.0 remains blocked on completing extension-level integration
  coverage against the extension gate below

## Extension Gate

Run the extension gate against a realistic Docassemble YAML package
before marking the release as 1.0. The checked-in fixture at
`tests/fixtures/demo_package` is the canonical target
for all steps below unless noted.

### Automation (monorepo integration suite)

The extension integration suite lives at
`../vscode/src/test/suite/extension.test.ts`. Run it from the
repository root with `just test-real-ext` (or
`cd vscode && npm run test:real-lsp-extension`). It exercises the
language server over the full LSP protocol with the canonical fixture
as the workspace root. The suite must assert:

- **diagnostics** — open `main.yml` with a deliberate schema error;
  confirm the expected code appears in `publishDiagnostics`; fix the
  error; confirm the cleared notification arrives
- **completions** — request completions inside a `metadata:` block;
  confirm `title` and `documentation` are in the item list
- **hover** — request hover on the `question:` key; confirm the
  response is non-null and contains `"question"`
- **document symbols** — request `textDocument/documentSymbol` on
  `main.yml`; confirm at least one block symbol is returned
- **definitions** — request `textDocument/definition` on a `def` or
  `event` symbol that is defined in an included file; confirm the
  response resolves to the correct file and line
- **references** — request `textDocument/references` on the same
  symbol; confirm cross-file references are returned
- **workspace symbols** — request `workspace/symbol` with a known
  `event` name; confirm the symbol appears in the result
- **document links** — request `textDocument/documentLink` on a file
  with `include:`; confirm the resolved `target` URI points to the
  correct file
- **formatting** — open a document with a code block containing
  non-standard Python style; request `textDocument/formatting`;
  confirm a non-empty edit list is returned
- **quick fixes** — open a document with a C102 convention violation;
  confirm the code action list contains a convert-to-explicit action
  and the source fix-all action

### Manual smoke check (against a real package checkout)

Before each release, perform a quick manual pass in VS Code with a
real Docassemble package (not the checked-in fixture). Verify:

- diagnostics appear and clear in real time as you edit
- completions and hover activate without noticeable latency
- go-to-definition and find-references navigate to correct locations
- formatting produces a valid YAML document

The goal is to keep LSP and CLI behavior stable enough that extension
work stays mostly protocol wiring, configuration, packaging, and
integration coverage rather than more semantic churn. Internal Python
APIs are greenfield and can change freely when that makes the LSP/CLI
cleaner.

## Capability Matrix

Use this matrix as the working contract for expanding LSP behavior. A
cell marked `yes` is part of the intended v1 behavior, `partial` means
the behavior exists but needs sharper coverage or UX, `planned` means
it is a good fit for the current architecture work, and `no` means it
is out of scope unless the release boundary changes.

| Docassemble concept | Completion | Diagnostic | Hover | Definition | References | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Top-level keys | yes | yes | yes | no | no | Schema-backed keys, docs, and snippets. |
| Scoped block keys | yes | yes | yes | no | no | Includes fields, metadata, attachment, review, grid, and related nested scopes. |
| Enum-like values | yes | partial | yes | no | no | Completion, hover, and diagnostic rules share the same registered enum values. Hover shows allowed values when the cursor is on either the key or the value position. |
| Field variables | yes | yes | planned | yes | yes | Field-variable declarations and `show if`/`hide if` style references are navigable. |
| `event` blocks | partial | partial | planned | yes | yes | Navigation exists; completions/diagnostics can become more context-aware. |
| `def` blocks and `usedefs` | partial | partial | planned | yes | yes | Navigation exists; hover and completion should share symbol facts. |
| Include YAML files | partial | partial | planned | yes | yes | Local and package-qualified includes are navigable and exposed as document links. |
| Package-qualified files | partial | planned | planned | yes | yes | Package-qualified local files resolve for supported definition and reference contexts. |
| Asset/template files | partial | partial | planned | yes | yes | References, definitions, and document links exist for common file-valued keys. |
| Python modules/imports | yes | partial | planned | yes | yes | Module and symbol navigation exists for supported static cases. |
| Python expressions in YAML | yes | yes | planned | yes | yes | Completion/navigation should continue to use conservative static parsing only. |
| Mako/Jinja regions | partial | yes | planned | partial | partial | Syntax validation and narrow semantic-token support exist; semantic behavior should stay limited and explicit. |
| Formatting | no | no | no | no | no | Whole-document formatting and on-type indentation are LSP features rather than concept-specific behavior. |
| Deterministic fixes | no | yes | no | no | no | Quick fixes and fix-all should remain limited to safe, deterministic rewrites. |

## Architecture Plan

The LSP server is a **single-root/single-project** language server. It
operates on one workspace root at a time. Other Docassemble packages
and Python modules are discovered as dependencies of the root project,
not as independent workspace roots.

Future LSP features should share a common project model instead of
each feature rescanning files or reinterpreting Docassemble structure
on its own.

Build toward these internal layers:

- `WorkspaceIndex`: tracks workspace YAML sources, multi-document open
  overlays, document facts, package root, Python/module caches (class
  names, symbol registries, docstrings), and cache invalidation.
  Include-parent relationships and asset references are derived by
  navigation services, not owned by the index.
- `DocumentFacts`: exposes reusable facts for YAML document
  boundaries, top-level blocks, fields, events, defs, includes,
  assets, Python regions, and template regions.
- `CompletionRegistry`: owns completion scopes, rule sets, snippets,
  duplicate-key policy, and scope regression cases in one place.
- Feature services: diagnostics, completion, hover, definition,
  references, workspace symbols, document links, and formatting should
  query the shared facts/index and leave `lsp/server.py` as a thin
  protocol adapter.

The first implementation step is to centralize workspace YAML source
collection and open-document overlay handling, then migrate
definitions, references, workspace symbols, and Python completion to
use that single source model.

Current implementation status:

- `WorkspaceIndex` is implemented as the concrete source model behind
  LSP/CLI semantic behavior. It supports workspace roots, cached YAML
  facts, empty indexes, single-document use, multi-document active
  overlays, and Python-aware rebuild on overlay changes.
- The LSP `_WorkspaceIndexStore` tracks all open unsaved documents
  (`_open_sources`) and caches disk-backed base indexes
  (`_base_indexes`). `for_workspace()` and `for_document()` apply all
  open overlays, triggering a full Python-aware rebuild when any
  overlay has changed since the last rebuild.
- Repeated workspace scans for symbols, references, Python module
  lookup, Python completions, and Python references now sit behind
  focused services over `WorkspaceIndex` instead of ad hoc per-feature
  loops in `definitions.py`.
- Document links are implemented for existing local file-valued
  Docassemble contexts, including `include`, YAML include-list
  parents, common template/content file keys, and `objects from file`
  values. Local and package-qualified supported paths resolve to
  `file:` targets without requiring a document-link resolve round
  trip.
- `CompletionRegistry` now provides the behavior-preserving provider
  dispatch behind `get_completions()` and owns Python, value, and
  property/snippet provider policy. `completion_context.py` owns
  source context policy for completion scopes, current-document
  entries, duplicate-key filtering, and shorthand suppression, leaving
  `schema.py` as a small facade for schema loading, completion
  dispatch, hover, and the public `completion_scope()` export.
- Field-variable definitions and references are implemented for
  conservative fields-block declarations and conditional `variable:`
  uses.
- Semantic tokens are implemented for a narrow set of well-known
  Docassemble regions, with process-level protocol coverage.

## Release Boundary

The current core gate assumes this v1 LSP surface:

- diagnostics
- completion
- hover
- document symbols
- definitions
- references
- workspace symbols
- document links for local file-like references
- package-qualified file definitions, references, and document links
- field-variable definitions and references
- semantic tokens for conservative Docassemble regions
- formatting
- small deterministic code actions

The gate does not imply support for:

- speculative type inference
- runtime execution
- unbounded refactors

The 1.0 boundary additionally requires:

- extension-level integration coverage (see Extension Gate above)

## README Policy

`README.md` now documents the shipped extension-backed workflow. It
covers the CLI, the VS Code extension feature set, and the
`pyproject.toml` convention configuration. Keep it aligned with the
extension gate and the capability matrix: if a feature is promoted
from `partial` or `planned` to `yes` in the matrix, update the README
to reflect that behavior.
