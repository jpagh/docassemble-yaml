# Roadmap

The architecture packet set and the 15-packet YAML semantics
implementation are both complete and validated. The remaining work is
now release-readiness and selective hardening rather than broad
internal restructuring or new semantic coverage.

## Completed Work

Two major packet sets have been completed and their planning documents
retired:

**Architecture packets (retired):**

1. completion and hover parity for enum-like values
2. field-variable definition and reference semantics
3. package-qualified file resolution for definitions, references, and
   document links
4. semantic tokens for conservative Docassemble regions
5. extension-gate definition and README/user-doc updates

**Parser-backed YAML semantics (all 15 packets implemented):**

Completions, hover, diagnostics, quick fixes, and validation for the
full Docassemble YAML grammar — initial blocks, question core,
modifiers, fields, datatypes, choices, conditions, documents,
review/table, list collect, objects/data, language/terms, reserved
names, and markup. Every packet was cross-checked against upstream
docs and `docassemble.base.parse`.

The implementation state is tracked in `RELEASE_GATE.md`, while this
file tracks the remaining release-readiness work.

## Current Validation Baseline

The current in-repo gate is:

```bash
mise run //lsp:check
```

That gate runs the full pytest suite and mypy. It should stay green
before any work is considered complete.

## Next Plan

All 15 parser-backed YAML semantics packets have been implemented and
are now part of the codebase. The work covered completions, hover,
diagnostics, quick fixes, and validation for the full Docassemble YAML
grammar, cross-checked against upstream docs and parser behavior. The
packet descriptions and implementation notes have been retired; the
current rule data lives in `src/docassemble_lsp/core/`.

### 1. Execute The Extension Gate

The highest-priority next step is outside this repository: implement
or run the VS Code extension integration gate described in
`RELEASE_GATE.md`.

The extension gate should prove the shipped editor workflow against
the canonical fixture, including diagnostics, completions, hover,
document symbols, definitions, references, workspace symbols,
document links, formatting, and quick fixes.

### 2. Smoke-Test A Real Package

After the automated extension gate exists, run the manual smoke check
against a real Docassemble package checkout. Record any failures as
narrow issues with reproduction snippets or fixtures.

### 3. Release Candidate Polish

Once the extension gate and real-package smoke pass are clean, prepare
the release boundary:

- confirm install instructions point to the actual extension delivery
  channel
- confirm `README.md` matches the supported feature set
- confirm `RELEASE_GATE.md` describes only current release blockers
- run `mise run //lsp:check` from a clean checkout or
  equivalent clean environment

### 4. Optional Hardening Backlog

These are useful follow-ups, but they should not displace the
extension gate unless the gate exposes a related defect:

- add fixture coverage for more package-qualified asset families
- add hover for semantic symbol families such as `event`, `def`, and
  field variables if the UX proves useful
- consider more context-aware diagnostics for `event` and `def` uses
- expand semantic tokens only for regions that are easy to classify
  conservatively
- continue moving repeated parsing or scanning into focused services
  when new features reveal duplication
- **composable validators** — extract OR/AND validator patterns for
  blocks that accept either a single-entry dict or a code block, to
  reduce nesting in `validation.py`
- **`required_attrs`** — consider adding a required-attribute system to
  the block-type definitions so missing mandatory keys produce their
  own diagnostic instead of being silently skipped

## Unresolved Spec Questions

These are parser-parity questions that need upstream investigation
before they can be validated with confidence. They are not release
blockers but should be resolved before the next major feature cycle:

- Does Docassemble accept mixed-case keys like ``Subquestion`` (vs.
  ``subquestion``)?
- What is the ``order`` key's semantic scope?
- Can ``template`` and ``terms`` coexist in the same YAML document?
- Can ``features`` and ``question`` coexist in the same YAML document?
- Is ``gathered`` a valid Docassemble key?
- Should validation handle the ``response`` block?
- Can labels appear above a ``fields`` list item?

## Relationship To RELEASE_GATE.md

`RELEASE_GATE.md` remains the release contract, capability matrix, and
status summary. Update it when the extension gate status, release
blockers, or supported feature contract changes.
