// Only the transformed parity reference may use these rewrites.
// They do not describe the unmodified grammar shipped to VS Code.

// vscode-textmate loses the TextMate `\\G` anchor at a line boundary, so the
// idiom `end: "^(?=\\S)|(?!\\G)"` (block scalar bodies, the Python
// `code:`/`show if:`/`script:` injections) pops at the first character of the
// following line instead of holding the region open.  The converter lowers
// those rules into match/push contexts where syntect keeps the region open,
// so the reference applies this narrow, documented rewrite to compare against
// the grammar's intent rather than that engine artifact.
const RULE_REWRITES = [
  {
    // TextMate `\\G` anchors to the end of the previous match, which holds
    // across a line boundary; vscode-textmate resets it per line, so the
    // region pops at the first character of the next line.
    field: "end",
    from: "^(?=\\S)|(?!\\G)",
    to: "^(?=\\S)",
  },
  {
    field: "end",
    from: "(?=\\S)|(?!\\G)",
    to: "(?=\\S)",
  },
  {
    // The end of these indentation-delimited regions back-references a
    // capture from a zero-width lookahead begin; vscode-oniguruma does not
    // return that group, so `\\1` resolves to the empty string and the
    // region never ends.  Consuming the indentation (as the upstream YAML
    // grammar does) records the capture.
    field: "begin",
    from: "^(?=([ ]+)(?! ))",
    to: "^([ ]+)(?! )",
  },
];

export function patchReferenceRule(rule) {
  if (!rule || typeof rule !== "object") return;
  for (const rewrite of RULE_REWRITES) {
    if (rule[rewrite.field] === rewrite.from) rule[rewrite.field] = rewrite.to;
  }
  // The docassemble fork wraps block-scalar bodies in `source.mako`; the
  // wrapper never engages under vscode-textmate (it only ever coloured the
  // body as unscoped text) and its injected context then traps the
  // `code:`/`if:` injections inside the scalar.  Restore the upstream
  // `string.unquoted.block.yaml` body; Mako still reaches the content
  // through its injection.
  if (rule.name === "source.mako" && rule.patterns) {
    rule.name = "string.unquoted.block.yaml";
    delete rule.patterns;
  }
  for (const child of Object.values(rule)) {
    if (Array.isArray(child)) child.forEach(patchReferenceRule);
    else if (child && typeof child === "object") patchReferenceRule(child);
  }
}
