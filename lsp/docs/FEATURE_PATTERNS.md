# Feature Patterns

This document explains how to add each major feature family in
`docassemble-lsp` without fighting the current architecture.

## Completion Features

### Preferred Path

1. decide whether the change is scope detection, provider behavior,
   candidate construction, or rule metadata
2. update the corresponding completion layer
3. validate direct completion behavior first
4. only then touch the LSP adapter if adapter translation must change

### Main Files

- `src/docassemble_lsp/core/completion_context.py`
- `src/docassemble_lsp/core/completion_registry.py`
- `src/docassemble_lsp/core/completion_rules.py`
- `src/docassemble_lsp/core/schema.py`
- `tests/test_schema.py`
- `tests/test_lsp.py`

### Use This Pattern When

- adding a new completion scope
- adding a new value or property provider rule
- adjusting duplicate-key filtering
- expanding shorthand handling
- aligning candidate documentation or insert text

### Avoid

- adding completion semantics directly to `lsp/server.py`
- putting new long-lived logic back into `schema.py`
- adding new property vocabularies in multiple places instead of
  centralizing them

## Hover Features

### Preferred Path

1. decide whether the hover data is schema-backed or
   semantic-symbol-backed
2. put shared meaning in a core service or model
3. have `schema.py` or a focused service expose the final hover
   payload
4. validate with direct hover tests and then LSP tests if needed

### Main Files

- `src/docassemble_lsp/core/schema.py`
- `src/docassemble_lsp/core/completion_registry.py`
- `tests/test_lsp.py`

### Avoid

- implementing hover as a one-off LSP-only branch with duplicate
  schema logic

## Definitions, References, And Workspace Symbols

### Preferred Path

1. detect the request kind in `definitions.py`
2. route to the correct focused service
3. keep occurrence scanning in the focused service, not the router
4. expose simple core targets back to the adapter

### Main Files

- `src/docassemble_lsp/core/definitions.py`
- `src/docassemble_lsp/core/workspace_navigation.py`
- `src/docassemble_lsp/core/workspace_symbols.py`
- `src/docassemble_lsp/core/python_navigation.py`
- `src/docassemble_lsp/core/python_modules.py`
- `tests/test_definitions.py`
- `tests/test_references_integration.py`
- `tests/test_lsp.py`

### Use This Pattern When

- adding a new symbol class for definitions or references
- adjusting navigation safety or reference-scan behavior
- extending Python-aware navigation
- extending file-reference semantics

### Avoid

- bypassing `WorkspaceIndex` for workspace-aware navigation
- widening navigation or reference support without a precise safety model
- duplicating path-scanning logic in both core and adapter layers

## Diagnostics

### Preferred Path

1. add the rule in the validation/diagnostics layer
2. make sure the rule has stable code, severity, and message behavior
3. if the rule is fixable, add a deterministic fix in `fixes.py`
4. validate with diagnostics tests first, then CLI or LSP tests as
   needed

### Main Files

- `src/docassemble_lsp/core/diagnostics.py`
- `src/docassemble_lsp/core/validation.py`
- `src/docassemble_lsp/core/messages.py`
- `src/docassemble_lsp/core/fixes.py`
- `tests/test_diagnostics.py`
- `tests/test_cli.py`
- `tests/test_lsp.py`

### Avoid

- emitting convention-style behavior without checking runtime options
- adding a quick fix for a rule that is not deterministic

## Code Actions And Fixes

### Preferred Path

1. map diagnostics to deterministic edits in `fixes.py`
2. keep the edit generator reusable by CLI and LSP
3. translate the resolved edits into LSP code actions in `server.py`
4. test both the fix resolver and the adapter behavior

### Main Files

- `src/docassemble_lsp/core/fixes.py`
- `src/docassemble_lsp/lsp/server.py`
- `tests/test_lsp.py`
- `tests/test_cli.py`

### Avoid

- building the edit directly in the LSP handler
- creating fixes that require speculative interpretation of user
  intent

## Formatting And On-Type Formatting

### Preferred Path

1. keep whole-document formatting in core formatting helpers
2. keep on-type indentation logic in small context helpers
3. have `server.py` only translate core results into `TextEdit`s
4. validate the smallest direct formatting tests first

### Main Files

- `src/docassemble_lsp/core/formatting.py`
- `src/docassemble_lsp/core/indentation.py`
- `src/docassemble_lsp/lsp/server.py`
- `tests/test_formatting.py`
- `tests/test_lsp.py`
- `tests/test_lsp_process.py`

### Avoid

- mixing large formatting semantics into the LSP handler body
- adding formatting rules that mutate structure without focused tests

## Document Links And Similar Protocol Features

### Preferred Path

1. implement link or range detection in a focused core helper
2. keep it local to the current document if the feature does not
   require workspace scanning
3. adapt the returned core targets into LSP models in `server.py`
4. test the builder and the process-level protocol request

### Main Files

- `src/docassemble_lsp/core/document_links.py`
- `src/docassemble_lsp/lsp/server.py`
- `tests/test_lsp.py`
- `tests/test_lsp_process.py`

### Avoid

- adding protocol-only logic with hidden semantic assumptions in the
  handler
- requiring a resolve round trip when the target is already known

## Python-Aware Navigation And Completion

### Preferred Path

1. isolate Python-aware context detection from YAML context detection
2. use `PythonNavigationService` for request-level logic
3. use `python_modules.py` for module lookup, search paths, and symbol
   resolution
4. keep behavior conservative when runtime Python semantics are
   ambiguous

### Main Files

- `src/docassemble_lsp/core/python_navigation.py`
- `src/docassemble_lsp/core/python_modules.py`
- `src/docassemble_lsp/core/definitions.py`
- `tests/test_definitions.py`
- `tests/test_lsp.py`
- `tests/test_references_integration.py`

### Avoid

- hand-rolling Python import or symbol resolution in unrelated feature
  files
- pretending dynamic runtime behavior is statically knowable when it
  is not

## Pure Protocol Features

### Preferred Path

1. decide whether the feature is really protocol-only or still needs a
   reusable core model
2. if it needs semantic detection, create a focused core helper first
3. keep `server.py` in the role of translator and lifecycle owner
4. add process-level coverage when protocol negotiation or capability
   advertisement matters

### Main Files

- `src/docassemble_lsp/lsp/server.py`
- `tests/test_lsp.py`
- `tests/test_lsp_process.py`

### Avoid

- expanding `server.py` into a second semantic layer

## Validation Commands

For any nontrivial feature family change:

```bash
uv run pytest tests/test_<family>.py -q
mise run //lsp:check
```

Use the narrowest discriminating test family first, then graduate to
the full gate.
