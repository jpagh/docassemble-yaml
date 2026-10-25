# Grammar engine checks

Shared sources and corpus are owned by [`grammars/`](../../grammars/README.md).
This directory owns the reusable tokenizers, category mapping, comparison, and
explicit compatibility exceptions. Editor installation/packaging stays outside
this harness.

```bash
mise run //tools/scope-parity:test:shipped  # direct unmodified shipped TextMate tests
mise run //tools/scope-parity:test:reference # compatibility mode is explicit and distinct
mise run //tools/scope-parity:test          # transformed-reference vs syntect parity
mise run //tools/scope-parity:check         # format, lint, inputs, reference-mode test
mise run //tools/scope-parity:gate          # check + shipped tests + clippy + parity
```

## Direct shipped TextMate tests (no patches)

`node/tokenize-shipped.test.mjs` tokenizes `grammars/fixtures/sample.yml` using
**unmodified** `vscode/syntaxes/*.json` packaging copies. The tokenizer reads the
VS Code manifest for grammar paths and injection registration. It resolves
external includes (Python, JavaScript, HTML) from locked `tm-grammars`, using
`vscode-textmate` and `vscode-oniguruma`. These exercise the shipped grammar
rules, not a VS Code installation's exact built-in dependency versions.

The direct tests assert YAML, Mako, Jinja, and Python-injection scopes and retain
a known shipped block-body limitation. They run via `//grammars:check` in the
main `mise run check`. **No compatibility rewrite is applied in this mode.**
To inspect raw scopes:

```bash
node tools/scope-parity/node/tokenize.mjs grammars/fixtures/sample.yml \
  tools/scope-parity/categories.json --scopes
```

## Transformed compatibility-reference parity

`run.sh` generates a temporary candidate (without rewriting the committed Fresh
artifact), tokenizes the shared corpus twice, then diffs per-character categories:

| Side | Engine | Grammars |
|---|---|---|
| Compatibility reference | `vscode-textmate` + `vscode-oniguruma` | `grammars/textmate/*.json` **with the patches below**, manifest injection targets |
| Candidate | `syntect` 5.3 (`yaml-load`) | Fresh-format output from `grammars/scripts/build_syntax.py` |

The tokenizer defaults to **shipped** mode. Only the explicit
`--compatibility-reference` flag enables `node/compatibility-reference.mjs`.
Output identifies the mode. This parity result is **not** equivalence to
unmodified shipped TextMate behavior. It preserves the pre-extraction converter
contract, including its existing intentional differences; it does not fix them.
The full Rust comparison remains runnable explicitly and in the release gate.

Both engines reduce scope stacks to `categories.json` (the most specific
matching prefix wins). Embedded Python, JavaScript, and HTML collapse to one
category: this tests region boundaries, not internal language tokenization.
`expected-differences.json` (currently empty) records additional accepted
category differences, with reasons; resolved entries fail as stale.

### Existing reference patches

These three classes of rewrite were already present before extraction. They
model the converter's intended engine compatibility, **not canonical fixes**:

1. `end: "^(?=\S)|(?!\G)"` → `"^(?=\S)"`, and
   `"(?=\S)|(?!\G)"` → `"(?=\S)"`. The existing reference compensates for
   vscode-textmate's per-line `\G` behavior in scalar bodies and Python/JS
   injections. The converter's match/push regions stay open across lines.
2. `begin: "^(?=([ ]+)(?! ))"` → `"^([ ]+)(?! )"`. The reference consumes
   indentation to preserve the capture used by end back-references; the original
   zero-width lookahead does not provide the expected capture in this engine.
3. The block-body `name: source.mako` wrapper becomes
   `string.unquoted.block.yaml` and its nested patterns are removed. The existing
   converter restores the upstream string scope while retaining Mako/Jinja
   content patterns. The unmodified shipped wrapper does not engage as intended
   under vscode-textmate and can trap later injections.

Without these patches, many existing corpus lines differ. In particular the
shipped `code: |` body on line 20 currently receives YAML scopes rather than the
reference's Python region. The direct test intentionally preserves this known
limitation. Do not change canonical grammars to make parity pass.

### Existing conversion exceptions

The converter also retains these choices: YAML `prototype` is renamed to avoid
syntect's reserved auto-injection context; dangling `#block-python` is dropped;
Mako and Jinja are inlined; Python injections are explicitly inserted into YAML
node contexts (not a global prototype); the YAML comment end `(?!\G)` becomes
`$`; captures keep names but drop nested patterns (including the invalid indent
indicator). Other unsupported include forms can be dropped by the lowerer.
See [the conversion notes](../../docs/FRESH.md#grammar-conversion-the-real-work)
and the converter's source comments for the original rationale.

## Extending the shared corpus

Edit `grammars/fixtures/sample.yml`, keeping it ASCII-only: TextMate reports
UTF-16 offsets, syntect reports bytes. Add direct assertions for shipped behavior
independently of compatibility-reference parity. If a parity difference is
intentional, add an entry to `expected-differences.json`:

```json
{ "line": 12, "start": 4, "end": 9, "ref": "other", "cand": "meta",
  "reason": "why this is acceptable" }
```

Use `tokenize.mjs --scopes --compatibility-reference` to debug the transformed
reference; omit the latter flag to inspect actual unmodified shipped rules.
