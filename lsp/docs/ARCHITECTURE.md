# Architecture

This document explains the intended internal architecture of
`docassemble-lsp` so future work can extend the LSP and CLI without
reintroducing one-off feature logic.

## Goal

The overall goal of this project is to provide a practical
Docassemble-aware semantic engine that serves both of these entry
points:

- the CLI, for validation and batch workflows
- the LSP server, for editor-driven interactive workflows

The LSP server is a **single-root/single-project** language server. It
operates on one workspace root at a time. Other Docassemble packages
and Python modules are discovered as dependencies of the root project,
not as independent workspace roots.

The stable contract is the behavior visible through the CLI and LSP
protocol. Internal Python APIs are allowed to change when that makes
the system easier to extend and reason about.

## Design Principles

1. Share one semantic model across CLI and LSP.
2. Keep `lsp/server.py` as a thin protocol adapter.
3. Prefer focused core services over feature-local rescans.
4. Use `WorkspaceIndex` as the source of truth for workspace-aware
   behavior.
5. Use multi-document overlays so all open unsaved buffers behave
   correctly before save. The LSP store tracks open documents and
   applies them as overlays on top of the saved workspace state.
6. Keep feature support conservative where Docassemble or embedded
   Python is dynamic.
7. Scale tests with feature risk and blast radius.

## Layer Model

### CLI And LSP Entry Points

- `src/docassemble_lsp/cli.py`
- `src/docassemble_lsp/lsp/server.py`

These entry points should do orchestration, argument/protocol
translation, and formatting of results. They should not become the
place where Docassemble semantics live.

### Shared Project Model

- `src/docassemble_lsp/core/workspace.py`
- `src/docassemble_lsp/core/document_facts.py`

This layer provides the shared model used by semantic features.

`WorkspaceIndex` is the central workspace model. It owns:

- workspace YAML source collection (collected from the single workspace
  root)
- open-document overlays (multi-document, tracked by the LSP store)
- per-file document facts built from YAML sources
- package root detection for Docassemble projects
- Python/module caches (class names, symbol registries, docstrings)
- search roots for Python/module-aware features

Include-parent relationships and asset references are not owned by
`WorkspaceIndex`. They are derived by navigation services
(`workspace_navigation.py`, `document_links.py`) from document facts.

`DocumentFacts` is the reusable document-structure layer. It turns a
YAML source into semantic facts that multiple features can consume
without reparsing the same shape independently.

### Semantic Routing And Focused Services

- `src/docassemble_lsp/core/definitions.py`
- `src/docassemble_lsp/core/workspace_navigation.py`
- `src/docassemble_lsp/core/workspace_symbols.py`
- `src/docassemble_lsp/core/python_navigation.py`
- `src/docassemble_lsp/core/python_modules.py`
- `src/docassemble_lsp/core/document_links.py`

This layer routes requests into focused services.

The intended pattern is:

1. detect what kind of semantic request the user is making
2. delegate to the narrowest focused service that can answer it
3. return simple core models back to the adapter

`definitions.py` is intentionally a router and coordinator. As more
feature families grow, the routing file may expand a little, but the
deeper logic should keep moving into focused services.

### Feature Systems

#### Completion And Hover

- `src/docassemble_lsp/core/schema.py`
- `src/docassemble_lsp/core/completion_context.py`
- `src/docassemble_lsp/core/completion_registry.py`
- `src/docassemble_lsp/core/completion_rules.py`
- `src/docassemble_lsp/core/field_keys.py`

The completion subsystem is split into three responsibilities:

- `completion_context.py`: source-context policy, scope detection,
  duplicate-key filtering, shorthand suppression, current-document
  entry understanding
- `completion_registry.py`: provider ordering, provider ownership,
  candidate construction helpers
- `schema.py`: thin facade for schema loading, completion dispatch,
  hover, and the public `completion_scope()` export

This is the preferred architecture for future completion work: new
behavior should usually extend the context layer, rules layer, or
provider layer rather than growing `schema.py` again.

#### Diagnostics, Fixes, And Formatting

- `src/docassemble_lsp/core/diagnostics.py`
- `src/docassemble_lsp/core/validation.py`
- `src/docassemble_lsp/core/fixes.py`
- `src/docassemble_lsp/core/formatting.py`

Diagnostics and fixes are shared by CLI and LSP. Validation remains a
relatively large subsystem, but the intended direction is still the
same: feature entry points should stay thin and deterministic fixes
should reuse shared fix resolution.

Formatting is also shared across entry points. Whole-document
formatting and on-type formatting are protocol features at the
boundary, but their semantic rules should still live in core helpers
rather than in the LSP handler bodies.

## Current Data Flow

### Workspace-Aware Semantic Request

For definitions, references, workspace symbols, Python-aware
completions, document links, and similar features:

1. the LSP adapter receives a request
2. `server.py`'s `_WorkspaceIndexStore` builds or retrieves a
   `WorkspaceIndex` that includes all open-document overlays
3. the adapter calls a core entry point with the current source,
   position, and `workspace_index`
4. the core entry point routes to focused services
5. focused services query cached sources and document facts
6. the adapter converts returned core models into LSP types

The `_WorkspaceIndexStore` maintains the lifecycle:

- `_open_sources` tracks all open unsaved documents
- `_base_indexes` caches the disk-backed workspace index (per root)
- `update_source()` compares new text against the existing overlay; it
  only marks the Python cache dirty when the text actually changed
- `for_workspace()` returns the base index with all open overlays
  applied; it triggers a full Python-aware rebuild when any overlay
  has changed since the last full rebuild
- `for_workspace()` caches the last built overlaid index keyed by
  workspace root and overlay content fingerprint (`frozenset` of
  path/text pairs); subsequent requests with unchanged overlays skip
  the rebuild entirely
- `for_document()` updates a specific overlay then delegates to
  `for_workspace()`
- `clear()` is called on save and watched-file changes, forcing a
  fresh base index, clearing the overlaid cache, and marking Python
  caches as dirty when any unsaved overlays are open so cross-package
  discoveries from overlays survive the base rebuild
- open overlays are always preserved across `clear()` — the editor's
  buffer content takes precedence over disk

  If open overlays exist when `clear()` is called, `_needs_python_refresh`
  is set so the next access performs a full Python-aware rebuild rather
  than a lightweight overlay, ensuring that external module discoveries
  from unsaved `modules:` entries are not lost.

### CLI Validation Request

1. the CLI resolves arguments and runtime options
2. it calls shared core validation/diagnostic functions
3. it formats output for the command surface

The CLI should keep reusing shared semantic code instead of growing a
separate interpretation path.

## Architectural Invariants

Future work should preserve these invariants.

### 1. WorkspaceIndex Is The Shared Semantic Model

Workspace-aware semantic features should not independently crawl the
workspace when `WorkspaceIndex` already provides the relevant view.

Acceptable exceptions are tiny feature-local scans of the current
document when the feature is explicitly local and does not benefit
from shared indexing.

### 2. The LSP Server Is A Translator, Not A Brain

`src/docassemble_lsp/lsp/server.py` should mainly do three things:

- maintain index lifecycle for the active workspace
- call core feature entry points
- translate core results to `lsprotocol` models

If a change requires substantial Docassemble semantics inside the
handler body, that logic probably belongs in `core/`.

### 3. Feature Logic Should Be Organized By Semantic Family

Good examples:

- document links in `core/document_links.py`
- workspace symbol logic in `core/workspace_symbols.py`
- Python navigation logic in `core/python_navigation.py`

Bad direction:

- adding unrelated branches across several large files when a focused
  service would give the feature a stable home

### 4. Shared Helpers Should Follow Real Reuse

Add a new shared abstraction only when it removes repeated logic or
captures a stable feature family pattern. Avoid abstracting early
around one single feature addition.

### 5. Tests Define The Actual Behavioral Contract

The intended v1 contract is enforced by the committed tests and
summarized in `RELEASE_GATE.md`. New work should usually extend the
most specific test family first, then graduate to broader coverage if
the feature affects shared behavior.

## Current Implemented Surfaces

As of the current architecture state, the repo has shared
implementations for:

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
- deterministic code actions

## Completed Architecture Packets

The first architecture packet set is complete:

1. completion and hover parity for enum-like values
2. field-variable definition and reference semantics
3. package-qualified file resolution
4. narrow semantic-token support for well-known Docassemble regions
5. extension-gate definition and user-facing README updates

The next plan is tracked in `docs/ROADMAP.md`. The remaining work is
release-readiness and selective hardening rather than broad internal
restructuring.

## Public Surface Guidance

`src/docassemble_lsp/core/__init__.py` should continue to expose
high-value public entry points and keep internal helpers private by
default.

A good rule is:

- export things that make sense as stable CLI/LSP-facing semantic
  entry points
- keep internal registries, scope helpers, and routing details
  unexported unless there is a real external need

## How To Use This Document

- Use this file when deciding where new work belongs.
- Use `docs/SUBAGENT_GUIDE.md` when handing work to a small
  implementation agent.
- Use `docs/FEATURE_PATTERNS.md` when implementing a specific feature
  family.
- Use `docs/ROADMAP.md` to choose the next release-readiness or
  hardening slice.
- Use `RELEASE_GATE.md` for release contract, capability matrix, and
  implementation-status tracking.
