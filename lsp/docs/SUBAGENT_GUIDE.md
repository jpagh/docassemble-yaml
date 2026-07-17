# Subagent Guide

This guide explains how a future small subagent should work in
`docassemble-lsp` without relying on prior chat context.

## First Questions To Answer

Before implementing anything, answer these questions:

1. Is this a CLI-visible feature, an LSP-visible feature, or both?
2. Is the feature local to one document or workspace-aware?
3. Is it schema-backed, document-fact-backed, Python-aware, or
   protocol-only?
4. Which existing feature is the closest architectural match?
5. Which focused test file is the first validation target?

If you cannot answer those questions from the request alone, start by
reading:

- `docs/ARCHITECTURE.md`
- `docs/FEATURE_PATTERNS.md`
- `RELEASE_GATE.md`

If the request is about Docassemble YAML keys, allowed values, invalid
combinations, completions, hover, or parser-backed diagnostics,
inspect `src/docassemble_lsp/core/completion_rules.py` and
`src/docassemble_lsp/core/validation.py` for the current rule data
before coding.

## Repo Rules Of Thumb

### Use The Shared Semantic Model

If the feature depends on workspace files, include relationships,
open-document overlays, cached facts, or Python search roots, it
should probably use `WorkspaceIndex`.

### Keep The Adapter Thin

If you are working in `src/docassemble_lsp/lsp/server.py`, prefer to
add a `build_*` adapter plus a call into `core/` rather than
implementing semantic logic directly in the handler.

### Match Existing Service Boundaries

Use the nearest existing feature family as the implementation anchor.

Examples:

- new completion behavior: start from `completion_context.py` or
  `completion_registry.py`
- new def/ref style navigation: start from `definitions.py`, then move
  logic into a focused service
- new file-link-like protocol feature: imitate `document_links.py`
- new Python-aware feature: imitate `python_navigation.py` and
  `python_modules.py`

### Extend Tests At The Right Level

Prefer the smallest test family that can prove the feature.

- `tests/test_schema.py` for scope detection and direct completion
  behavior
- `tests/test_lsp.py` for LSP adapter builders and feature-family
  behavior
- `tests/test_definitions.py` for semantic navigation internals
- `tests/test_references_integration.py` for realistic multi-file
  behavior
- `tests/test_lsp_process.py` for protocol/session behavior
- `tests/test_diagnostics.py` for validation rules
- `tests/test_cli.py` for command-surface behavior

## Preferred Workflow For A Small Agent

1. Read the closest architecture and feature-pattern docs.
2. Find the nearest existing implementation to imitate.
3. Write or extend the focused test first when feasible.
4. Implement in `core/` before touching the LSP adapter, unless the
   feature is purely protocol translation.
5. Add or update adapter translation in `lsp/server.py`.
6. Run the smallest discriminating test family.
7. Run `mise run //lsp:check` before declaring the slice
   done.
8. Update `RELEASE_GATE.md` only if the implementation-status summary
   or supported contract meaningfully changed.
9. Update internal docs if the change creates a new reusable pattern
   or materially changes the architecture map.

## File Anchors By Work Type

### Shared Model And Routing

- `src/docassemble_lsp/core/workspace.py`
- `src/docassemble_lsp/core/document_facts.py`
- `src/docassemble_lsp/core/definitions.py`

### Completion And Hover

- `src/docassemble_lsp/core/completion_context.py`
- `src/docassemble_lsp/core/completion_registry.py`
- `src/docassemble_lsp/core/completion_rules.py`
- `src/docassemble_lsp/core/schema.py`
- `src/docassemble_lsp/core/field_keys.py`

### Navigation And Symbol Features

- `src/docassemble_lsp/core/workspace_navigation.py`
- `src/docassemble_lsp/core/workspace_symbols.py`
- `src/docassemble_lsp/core/python_navigation.py`
- `src/docassemble_lsp/core/python_modules.py`

### Validation, Fixes, Formatting

- `src/docassemble_lsp/core/diagnostics.py`
- `src/docassemble_lsp/core/validation.py`
- `src/docassemble_lsp/core/fixes.py`
- `src/docassemble_lsp/core/formatting.py`

### Protocol Adapter

- `src/docassemble_lsp/lsp/server.py`

## Common Failure Modes

### Reintroducing Per-Feature Workspace Scans

Do not add new workspace crawls when `WorkspaceIndex` already contains
the needed source view.

### Growing `schema.py` Back Into A Monolith

`schema.py` is now intentionally a slim facade. Prefer changes in:

- `completion_context.py`
- `completion_registry.py`
- `completion_rules.py`

### Ignoring Current-Document Overlays

If you use filesystem content directly in an LSP feature, you risk
stale results for unsaved documents. Prefer the source and
`workspace_index` passed into the request path.

### Letting Completion, Hover, And Diagnostics Drift

When a feature touches schema-backed meaning, check whether
completion, hover, and diagnostics should all stay aligned.

## When To Update RELEASE_GATE.md

Update `RELEASE_GATE.md` when one of these is true:

- a planned capability becomes implemented
- the architecture-status summary materially changes
- the release boundary or extension gate meaning changes
- a new test family becomes part of the committed release gate

Do not update it for every small refactor.

## Minimum Validation Standard

For a normal architectural slice:

1. run the focused test family first
2. fix any diagnostics or typing issues in touched files
3. run `mise run //lsp:check`

If the work is only documentation, validate changed files for
diagnostics and keep cross-links accurate.

## Handoff Template

When handing a roadmap item to another small agent, give it:

- the relevant section from `docs/ROADMAP.md`
- the exact files it should inspect first
- the focused test command it should run before the full gate
- the explicit out-of-scope boundaries

That keeps the work bounded and reduces architectural drift.
