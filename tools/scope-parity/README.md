# Grammar engine checks

Shared sources and corpus are owned by [`grammars/`](../../grammars/README.md).
This directory owns the reusable tokenizers, category mapping, comparison, and
explicit compatibility exceptions. Editor installation/packaging stays outside
this harness.

```bash
MISE_EXPERIMENTAL=1 mise run //tools/scope-parity:check # deterministic; no Rust/editor binaries
MISE_EXPERIMENTAL=1 mise run //tools/scope-parity:test:shipped # unmodified TextMate assertions
MISE_EXPERIMENTAL=1 mise run //tools/scope-parity:test:reference # reference mode stays distinct
MISE_EXPERIMENTAL=1 mise run //tools/scope-parity:test # BOTH engine pairs; builds Rust
MISE_EXPERIMENTAL=1 mise run //tools/scope-parity:gate # check + Rust formatting/clippy/theme tests + both pairs
MISE_EXPERIMENTAL=1 mise run //kakoune:check # separate editor update checks; loud skip without tools
MISE_EXPERIMENTAL=1 mise run check # GUI-free main validation, no Rust requirement
```

The two comparisons in `run.sh` are intentionally **not interchangeable**:

| Pair | Reference | Candidate | Corpus |
|---|---|---|---|
| `canonical` (canonical **rules**) | shipped, unmodified `vscode-textmate` | giallo 0.5.2 + builtin dependencies, **name/injectTo metadata adaptation only** | sample, regions, Unicode |
| `compatibility` | explicitly rewritten TextMate reference | generated Fresh grammar, syntect 5.3.0 | sample, regions (ASCII) |

Dependencies are locked in `node/package-lock.json` and `Cargo.lock`:
`vscode-textmate` 9.3.2, `vscode-oniguruma` 2.0.1, `tm-grammars` 1.32.22,
syntect 5.3.0, giallo 0.5.2. The canonical comparison is **not universal engine
equivalence, not a VS Code visual claim**, and does not test VS Code's installed
built-in grammar versions. Metadata adaptation is an explicit transformation,
not a canonical TextMate rule or the three compatibility-reference rewrites.

### giallo's styles-only public API

`src/bin/giallo.rs` uses the library, never Kakoune. It starts from
`Registry::builtin()`, adds canonical grammars with the same name/injection-target
metadata as Kakoune packaging, then links. Builtin language dependencies differ
from the Node lockfile and syntect defaults. No canonical regex/rule changes occur.

The public API exposes token text/styles, **not scope stacks**. `src/lib.rs`
generates a diagnostic theme from `categories.json`: unique foreground colours
encode ordinary scope-atom prefixes; a separate background channel encodes
embedded languages so Python strings/comments still reduce to `python`.
Both whitespace and same-style merging are disabled; concatenated token text is
checked against each source line. Colour inversion rejects unknown colours.
The Rust probe independently highlights synthetic scope stacks covering **every
category**, verifies unique colours and inner-rule/embedded precedence against
the scope reducer, and deliberately assigns the wrong comment colour to prove
that a wrong theme category is observable. This runs in `gate`, not `check`.

### Explicit offset normalization

Adapters identify their native `offsetUnit`: JS TextMate indices are **UTF-16
code units**, syntect offsets and giallo token-text lengths are **UTF-8 bytes**.
Adapters exclude real/virtual newline positions (giallo also retains a trailing
empty line, which is explicitly omitted). `offsets.py` converts run boundaries to
Unicode **codepoints**, not grapheme clusters, before comparison. It rejects
split surrogate pairs, split UTF-8 sequences, gaps, overlaps and incomplete
streams. `test_offsets.py` tests astral emoji, combining marks and CJK conversion;
`test_compare.py` compares UTF-16 and UTF-8 streams with unequal native lengths.
The canonical Unicode fixture actually runs through both engines, not merely an
ASCII offset equivalence assumption. Compatibility fixtures remain ASCII-only
as an existing contract, although syntect also declares its byte units.

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

Both engines reduce scope stacks to `categories.json` (embedded languages
override internal scopes; otherwise the innermost matching scope and first
matching prefix rule win). Embedded Python, JavaScript, and HTML collapse to one
category: this tests region boundaries, not internal language tokenization.
`expected-differences.json` records pair-scoped accepted category differences;
compatibility still has **zero exceptions**. Exact matches and stale detection
are described below.

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

## Intentional differences (closed reason classes)

The canonical pair currently has 54 exact run exceptions, in only these classes:

- `shipped-block-python-injection` (33): the **known shipped block-body
  limitation** in [Existing reference patches](#existing-reference-patches),
  especially patch 1 and the line-20 example. Shipped TextMate loses `code:` /
  `show if:` block Python regions; giallo retains them. Categories on the shipped
  side vary, but the candidate must be `python`.
- `shipped-block-mako-wrapper` (21): the **ineffective `source.mako` wrapper** in
  [Existing reference patches](#existing-reference-patches), patch 3. TextMate
  retains `string` on scalar/template text where giallo yields `other`.

These are observations, not fixes or approval of all possible engine differences.
Exceptions should **shrink when the shipped grammar is fixed**; stale detection
then forces their removal. No compatibility exception was added or changed.

`lint.py` machine-checks the minimal schema, closed reason classes, applicable
category pairs, known engine-pair/fixture names, category names, codepoint bounds,
and duplicate/overlapping entries. Each comparison selects only its pair/fixture
and matches **exact** contiguous `(line, start, end, ref, cand)` runs. Coordinates
are 1-based lines and 0-based, end-exclusive codepoints. An unexpected run fails;
a resolved, partially changed or redundant exception fails as stale. Adjacent
mismatches split when the category pair changes, so one exception cannot mask
several kinds of drift. Unit tests demonstrate unexpected, stale, redundant,
partial-run and wrong-pair/fixture failures.

## Extending the shared corpus

1. Prefer a new YAML file under `grammars/fixtures/`: `sample.yml` has existing
   line-specific assertions and must stay ASCII. `regions.yml` covers Python and
   conditional multiline bodies, Mako/Jinja scalar contents, dedents back into
   YAML and pasted-block content shapes. `unicode.yml` includes astral emoji,
   combining marks, non-ASCII identifiers/comments and post-template YAML.
2. Register it explicitly for each applicable pair in `fixtures.json`. Never
   remove the original Fresh corpus to make parity pass. Keep compatibility
   fixtures ASCII; put Unicode in the canonical pair.
3. Add shipped assertions in `node/tokenize-corpus.test.mjs` independently of
   compatibility-reference parity. `check` validates YAML, category/exception
   inputs, offsets, accounting, and shipped assertions. Use `gate` to catch
   actual three-engine drift and validate the diagnostic theme.
4. Investigate every new mismatch. Do not tune canonical grammars or converter
   rules just to pass. If intentional and approved, record an **exact** run with
   a documented reason class and one-line explanation, e.g.:

   ```json
   { "pair": "canonical", "fixture": "sample.yml", "line": 14,
     "start": 2, "end": 8, "ref": "string", "cand": "other",
     "reasonClass": "shipped-block-mako-wrapper",
     "reason": "Known ineffective source.mako scalar wrapper: TextMate keeps string scope; giallo leaves it unclassified." }
   ```

   A third class requires explicit investigation/approval, enum validation and
   documentation here; do not invent bespoke reasons for unrelated drift.

Use `tokenize.mjs --scopes --compatibility-reference` to debug the transformed
reference; omit the latter flag to inspect actual unmodified shipped scopes.

## Separate Kakoune incremental checks

`kakoune/scripts/check_highlighting.py` reuses real Kakoune/giallo session plumbing
and the shared regions fixture. It performs a single-character insert, line
deletion, multiline paste and indentation change; verifies the exact resulting
buffer content; and waits for **all** `(line, UTF-8 byte start/end, colour)` ranges
to equal those from a newly started independent full-highlight session of that
content after every edit. Each step must change the previous range snapshot,
and the original source file must remain untouched. It invokes the normal
`giallo-rehighlight` command used by the idle hook, with rate limiting disabled
for deterministic headless checks; this does not measure interactive idle timing.
These checks prove editor-path update convergence for those edits, **not engine
parity** or that giallo internally reparses incrementally. Missing editor tools
produce a loud skip. Main `check` retains the deterministic packaging checks and
runs these real editor checks when the binaries are present; the Rust engine
comparisons stay in the parity `gate`/opt-in `test`.
