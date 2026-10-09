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

- `lsp/src/docassemble_lsp/core/completion_context.py`
- `lsp/src/docassemble_lsp/core/completion_registry.py`
- `lsp/src/docassemble_lsp/core/completion_rules.py`
- `lsp/src/docassemble_lsp/core/schema.py`
- `lsp/tests/test_schema.py`
- `lsp/tests/test_lsp.py`

### Block scalar (`|`) value completion

- For any property whose `value_types` includes `"string"` and
  `insert_kind == "scalar"`, `value_completion_provider` emits a `|`
  candidate with `insert_text = "|\n  $0"` and `is_snippet=True`.
- For `fields_item` scope, the candidate is gated by
  `FIELD_KEY_COMPATIBLE_DATATYPES` against `context.current_field_datatype`.
- This is the canonical pattern for offering block-scalar bodies — prefer it
  over adding a per-key allow-list.

### Use This Pattern When

- adding a new completion scope
- adding a new value or property provider rule
- adjusting duplicate-key filtering
- expanding shorthand handling
- aligning candidate documentation or insert text

### Avoid

- adding completion semantics directly to `lsp/src/docassemble_lsp/lsp/server.py`
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

- `lsp/src/docassemble_lsp/core/schema.py`
- `lsp/src/docassemble_lsp/core/completion_registry.py`
- `lsp/tests/test_lsp.py`

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

- `lsp/src/docassemble_lsp/core/definitions.py`
- `lsp/src/docassemble_lsp/core/workspace_navigation.py`
- `lsp/src/docassemble_lsp/core/workspace_symbols.py`
- `lsp/src/docassemble_lsp/core/python_navigation.py`
- `lsp/src/docassemble_lsp/core/python_modules.py`
- `lsp/tests/test_definitions.py`
- `lsp/tests/test_references_integration.py`
- `lsp/tests/test_lsp.py`

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

- `lsp/src/docassemble_lsp/core/diagnostics.py`
- `lsp/src/docassemble_lsp/core/validation/orchestrator.py`
- `lsp/src/docassemble_lsp/core/messages.py`
- `lsp/src/docassemble_lsp/core/fixes.py`
- `lsp/tests/test_diagnostics.py`
- `lsp/tests/test_cli.py`
- `lsp/tests/test_lsp.py`

### Avoid

- emitting convention-style behavior without checking runtime options
- adding a quick fix for a rule that is not deterministic

### Jinja Include Rendering

`# use jinja` templates render before validation. A missing include
must not abort the render: `preprocess_jinja` wraps every `{% include %}`
site so it resolves its candidates at render time, and an unresolvable
site renders an internal sentinel plus a `W607` warning
anchored to the include line. `ignore missing` sites render nothing and
warn nothing, candidate lists are tried in order, and one source site
warns once no matter how many times it renders. Nested includes are
attributed to the outer include site that pulled in the containing
template.

`orchestrator.py` blanks the YAML documents that contain the sentinel
(preserving line numbers) and validates the rest, so findings in
remaining documents still map back to the original template lines.
Syntax errors and runtime errors keep their fatal `E201`/`E202`
behaviour; only unresolved includes become warnings.

### Jinja Server Values

Values that only the server supplies (``jinja data``, docassemble's Jinja
context, or an imported macro's context) are unknown at validation time.
Instead of rendering empty text, each substitution renders a distinct
placeholder (``__docassemble_lsp_unknown_<n>__``, a valid YAML scalar and
Python identifier) and records warning `W610` once per source site. The
placeholder is what keeps the surrounding YAML parseable and stops two
unknown values from looking like duplicates.

`contains_placeholder` in `jinja.py` identifies rendered content that
came from a server value. Checks that resolve names or value shapes must
skip such values: they cannot be resolved against the rest of the
interview, and a placeholder's string type says nothing about the runtime
type. Cross-document checks skip a value containing a placeholder, the
`interview order` guard check also skips a placeholder guard or a code
block that contains one, and the `table`/`data` shape checks skip a
placeholder where they expect a list or mapping. The `id` checks need no
special casing because every substitution receives its own placeholder.

## Code Actions And Fixes

### Preferred Path

1. map diagnostics to deterministic edits in `fixes.py`
2. keep the edit generator reusable by CLI and LSP
3. translate the resolved edits into LSP code actions in `server.py`
4. test both the fix resolver and the adapter behavior
5. route automatic rewriting through `validate_fix_candidates` and
   surface rejections instead of writing

### Candidate Gate

`validate_fix_candidates` re-checks a fix candidate before `--fix` or a
fix-all code action writes it. A candidate is accepted only when it
still parses, introduces no new finding of any code, and strictly
reduces the finding it was made for. Findings are compared per code
with the same runtime options and workspace context as the run, the
accepted batch is re-checked as a whole, and Jinja-rendered files are
never rewritten automatically. Rejections are reported on stderr by
the CLI and logged by the LSP server; a rejected candidate leaves the
file unchanged. Quick fixes requested explicitly for a single
diagnostic do not pass through the gate.

### Parser-Backed Planners

An edit that depends on parsed document structure — a screen's fields,
its question text, or a block's unique id — is planned in a small core
module (`question_ids.py`, `field_labels.py`, `yesno_shortcuts.py`) and
only turned into a `SourceEdit` by `fixes.py`. The planner parses the
source once, returns a frozen plan describing the one safe edit (or
`None` to decline), and never manipulates line text. That keeps the
fixer's line surgery mechanical, lets the rule and the fixer share one
predicate (for example `field_lacks_usable_label` or `shortcut_keys`),
and gives the decline cases a single tested home. One fix pass parses
each source once: `resolve_diagnostic_fixes` builds a `_FixPassContext`
whose documents are parsed on first use, and every document-backed
provider plans against those documents through the planner's optional
`documents` argument. The planner entry points still parse on their own
for direct callers, so the shared path plans and declines exactly like
the direct path.

### Main Files

- `lsp/src/docassemble_lsp/core/fixes.py`
- `lsp/src/docassemble_lsp/core/field_labels.py`
- `lsp/src/docassemble_lsp/core/yesno_shortcuts.py`
- `lsp/src/docassemble_lsp/lsp/server.py`
- `lsp/tests/test_lsp.py`
- `lsp/tests/test_cli.py`

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

- `lsp/src/docassemble_lsp/core/formatting.py`
- `lsp/src/docassemble_lsp/core/indentation.py`
- `lsp/src/docassemble_lsp/lsp/server.py`
- `lsp/tests/test_formatting.py`
- `lsp/tests/test_lsp.py`
- `lsp/tests/test_lsp_process.py`

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

- `lsp/src/docassemble_lsp/core/document_links.py`
- `lsp/src/docassemble_lsp/lsp/server.py`
- `lsp/tests/test_lsp.py`
- `lsp/tests/test_lsp_process.py`

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

- `lsp/src/docassemble_lsp/core/python_navigation.py`
- `lsp/src/docassemble_lsp/core/python_modules.py`
- `lsp/src/docassemble_lsp/core/definitions.py`
- `lsp/tests/test_definitions.py`
- `lsp/tests/test_lsp.py`
- `lsp/tests/test_references_integration.py`

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

- `lsp/src/docassemble_lsp/lsp/server.py`
- `lsp/tests/test_lsp.py`
- `lsp/tests/test_lsp_process.py`

### Avoid

- expanding `server.py` into a second semantic layer

## Validation Commands

For any nontrivial feature family change:

```bash
cd lsp && uv run pytest tests/test_<family>.py -q
cd .. && mise run //lsp:check
```

Use the narrowest discriminating test family first, then graduate to
the full gate.
