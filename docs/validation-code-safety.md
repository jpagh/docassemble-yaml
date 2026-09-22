# Validation-code off-screen read warning

`W606` is a conservative warning for direct variable reads in a screen's
`validation code` that are not declared by that screen's `fields` (including
`field:` shorthand) or `need:`. It is shared by CLI and LSP diagnostics through
the common validation pipeline.

The check understands direct Python name/attribute paths, assignments made in
the same validation block, imports, and these explicit guards:

- `defined("variable.path")`, including as a left-hand short-circuit operand
  with `and` or as an `if` condition;
- `object.hasattr("attribute")`, including as a left-hand short-circuit
  operand with `and` or as an `if` condition.

This is not runtime proof. Computed names, aliases, dynamic field-generation
code, helper functions that implement guards, exception-based checks, and
other control-flow/data-flow patterns are not modeled. Dynamic
`fields: {code: ...}` screens and Jinja-affected documents are skipped because
static field/source meaning is unknown.
When safety depends on a pattern the checker cannot see, declare the variable
with `need:` or restructure the check using a recognized guard. The warning
should be treated as a prompt to inspect the screen, not a claim that every
reported access will fail at runtime.
