# Scope-parity test

Guards `fresh/scripts/build_syntax.py`: the generated
`fresh/grammars/Docassemble.sublime-syntax` must reduce the same text to the
same highlight categories as the original VS Code TextMate grammars it is
generated from.

```bash
mise run //tools/scope-parity:test      # the parity run (or: tools/scope-parity/run.sh)
mise run //tools/scope-parity:check     # fast: format, lint, input validation
mise run //tools/scope-parity:gate      # check + clippy + parity (pre-release)
```

`run.sh` regenerates the grammar, tokenizes `fixtures/sample.yml` twice, and
diffs the results per character:

| Side | Engine | Grammars |
|---|---|---|
| Reference | `vscode-textmate` + `vscode-oniguruma` (VS Code's engine) | `vscode/syntaxes/*.tmLanguage.json` and their injection selectors |
| Candidate | `syntect` 5.3 (`yaml-load`) | `fresh/grammars/Docassemble.sublime-syntax` |

Both sides reduce each scope stack to one category from `categories.json`
(the most specific scope that matches a prefix wins). Embedded languages
(Python, JavaScript, HTML) collapse to a single category: the converter is
responsible for *where* those regions start and stop, not for how `syntect`'s
Python grammar tokenizes them internally. `expected-differences.json` (empty
today) records any difference that is accepted on purpose; a difference that
is no longer present is reported as stale.

## Reference patches

`node/tokenize.mjs` applies three rewrites to the reference grammars before
tokenizing, all documented in the source. They are engine artifacts, not
grammar disagreements:

1. `end: "^(?=\S)|(?!\G)"` → `"^(?=\S)"`. TextMate's `\G` anchors to the end
   of the previous match and holds across a line boundary; vscode-textmate
   resets it per line, so block scalars and the Python injections
   (`code:`, `show if:`, `script:`) pop at the first character of the next
   line instead of holding the region open. The converter lowers these into
   match/push contexts where the region stays open, matching the intent.
2. `begin: "^(?=([ ]+)(?! ))"` → `"^([ ]+)(?! )"` for indentation-delimited
   regions. Their end back-references the begin's capture; vscode-oniguruma
   does not return a capture from a zero-width lookahead, so `\1` resolves to
   the empty string and the region never ends.
3. The docassemble block-scalar body's `name: source.mako` wrapper is restored
   to the upstream `string.unquoted.block.yaml` body. Under vscode-textmate
   the wrapper never engaged (content read as a plain scalar) and its
   injected context trapped subsequent `code:`/`if:` injections inside the
   scalar. The candidate scopes the body as a string and keeps Mako/Jinja as
   content patterns, so both sides agree and interpolation still works.

Without these, roughly half the fixture reports differences that come from
the engine rather than from the converter.

## Adding to the fixture

Edit `fixtures/sample.yml`. Keep it ASCII-only: vscode-textmate reports
UTF-16 offsets and syntect reports byte offsets, which only coincide for
ASCII. If a difference is expected, add an entry to
`expected-differences.json`:

```json
{ "line": 12, "start": 4, "end": 9, "ref": "other", "cand": "meta",
  "reason": "why this is acceptable" }
```

Regenerate the reference with the same script (`tokenize.mjs --scopes` prints
raw scope stacks if you need to debug an entry).
