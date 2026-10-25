# Shared grammars

## Ownership

- `textmate/*.json` are the **canonical TextMate sources** for all editors,
  including the Python/Mako/Jinja injections. Edit these, never packaging copies.
  They were moved byte-for-byte from `vscode/syntaxes/`; their embedded attribution
  and repository licensing are unchanged.
- `scripts/build_syntax.py` owns the TextMate-to-syntect lowering. Its existing
  compatibility choices are documented in [the Fresh investigation](../docs/FRESH.md#grammar-conversion-the-real-work)
  and [the parity harness](../tools/scope-parity/README.md). This extraction does
  not fix unrelated grammars or make those choices canonical TextMate behavior.
- `fixtures/sample.yml` is the editor-independent, ASCII-only corpus shared by
  direct TextMate tests and transformed-reference parity. ASCII keeps UTF-16 and
  byte offsets comparable in that legacy fixture. Prefer new fixtures to avoid
  invalidating its line-specific assertions. `fixtures/regions.yml` adds dedent
  and multiline content shapes for both engine pairs; `fixtures/unicode.yml`
  exercises explicit UTF-16/UTF-8-to-codepoint normalization in the canonical pair.
- [`tools/scope-parity/`](../tools/scope-parity/README.md) owns reusable engine
  harnesses, category reduction, explicit reference patches, and intentional
  difference accounting; it consumes this directory's sources and corpus.
- VS Code owns **real-file packaging copies** in `vscode/syntaxes/`, its manifest,
  dependency resolution, and injection registration. Fresh owns its committed
  `fresh/grammars/Docassemble.sublime-syntax`, bundle manifest, and detection/LSP
  plugin. Kakoune owns generated metadata-adapted TextMate copies under
  `kakoune/grammars/` and a [filetype/detection plugin using giallo.kak](../kakoune/README.md).
  Installed editors do not need this shared directory or build tools.

## Edit and regenerate

After changing shared sources or the converter, run from the repository root:

```bash
mise run //vscode:grammar:sync
mise run //kakoune:grammar:sync
uv run --no-project --with pyyaml python grammars/scripts/build_syntax.py
mise run //grammars:check
mise run //fresh:check
mise run //kakoune:check
mise run //vscode:check
mise run //tools/scope-parity:test
```

Commit shared changes and regenerated packaging artifacts together. The old
`fresh/scripts/build_syntax.py` command remains a thin compatibility entry point.
The generated Fresh header deliberately retains its historical command and
`vscode/syntaxes` paths to preserve output bytes; those paths remain valid copies,
not the source of truth. Do not manually update the header during regeneration.

## Validation boundaries

`mise run check` (GUI-free) runs shared conversion tests, **unmodified shipped TextMate**
fixture assertions, both existing editor checks, input validation, offset/exception-accounting tests, and formatting. The shared
fast checks require no Rust toolchain or editor binaries; optional Kakoune checks
skip loudly without their tools.
VS Code builds fail on stale copies; Fresh checks compare regenerated output
byte-for-byte without overwriting it. A packaging test checks all six registered
grammars and the three injection targets. Kakoune's packaging tests enforce
metadata-only adaptation and stale-copy detection; its real-editor smoke check
skips loudly when Kakoune or giallo-kak is unavailable. With tools installed it
separately checks real buffer edit convergence against fresh full highlights. See the
[Kakoune investigation](../docs/KAKOUNE.md) for the observed shared-corpus
boundaries and the separate Unicode fixture.

`MISE_EXPERIMENTAL=1 mise run //tools/scope-parity:gate` builds the heavier
three-engine harness: **canonical rules** (unmodified shipped TextMate vs giallo,
with explicit name/injectTo metadata adaptation) and **transformed compatibility
reference** vs syntect/Fresh. Existing Fresh coverage is retained, with no
exceptions, and extended with regions. The canonical pair additionally exercises
Unicode offsets and documents two known shipped limitations as exact, stale-checked
exceptions. Neither pair claims universal equivalence or VS Code visual parity.

To add coverage, register a new fixture in `tools/scope-parity/fixtures.json`,
keep compatibility inputs ASCII, and add independent shipped assertions. Never
broaden exceptions to hide drift: each needs a known reason class and exact
pair/fixture/line/codepoint range. See the [harness contributor guide](../tools/scope-parity/README.md#extending-the-shared-corpus)
for commands, normalization, intentional-difference schema, stale detection, and
the separate Kakoune incremental checks. The root release `gate` also invokes
the harness, but launches VS Code; use the scoped parity gate for headless work.
