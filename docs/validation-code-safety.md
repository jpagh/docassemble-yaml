# Validation-code off-screen read warning

`W606` is a conservative warning for direct variable reads in a screen's
`validation code` that are not defined by that screen or the interview. It is
shared by CLI and LSP diagnostics through the common validation pipeline.

A read counts as defined when any of these hold:

- it equals a declared `fields:` (including `field:` shorthand) or `need:`
  path, or extends one at a `.` boundary — a declared `uploaded_signature`
  covers a read of `uploaded_signature[0].mimetype`;
- it is one of docassemble's implicit list-item indices (`i`, `j`, `k`, `l`,
  `m`, `n`) and a declared field, `field:`, or `need:` target uses that name
  as a subscript, e.g. `matters[i].category`;
- it is `x` for a `generic object:` block, or `x` and `i` for a
  `generic list object:` block;
- it is a key declared under `objects:` anywhere in the interview (including
  dotted keys such as `state.co_share_list`), or a name bound at module scope
  by a top-level `code:` block (imports, assignments, `for`/`except` targets,
  and dotted assignments). The workspace view comes from `WorkspaceIndex`, so
  open unsaved buffers are honored.

Subscripts are ignored when comparing paths: `obj[0].attr`, `obj[i].attr`, and
`obj.attr` are the same declared path.

The check also understands direct Python name/attribute paths, assignments
made in the same validation block, imports, and these explicit guards:

- `defined("variable.path")`, including as a left-hand short-circuit operand
  with `and` or as an `if` condition;
- `object.hasattr("attribute")`, including as a left-hand short-circuit
  operand with `and` or as an `if` condition.

This is not runtime proof. Computed names, aliases, dynamic field-generation
code, helper functions that implement guards, exception-based checks, and
other control-flow/data-flow patterns are not modeled. Dynamic
`fields: {code: ...}` screens and Jinja-affected documents are skipped because
static field/source meaning is unknown.

Workspace `code:` names are order-blind: a read of a global assigned in a
later code block is treated as defined. Names from unsaved edits are added to
the workspace set, but removed definitions are not retracted, matching the
existing `fields:` behavior. Malformed or unparsable `code:` blocks are
skipped.

When safety depends on a pattern the checker cannot see, declare the variable
with `need:` or restructure the check using a recognized guard. The warning
should be treated as a prompt to inspect the screen, not a claim that every
reported access will fail at runtime.
