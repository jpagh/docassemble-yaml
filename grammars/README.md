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
  byte offsets comparable. Extend it when adding constructs.
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

`mise run check` runs shared conversion tests, **unmodified shipped TextMate**
fixture assertions, both existing editor checks, input validation, and formatting.
VS Code builds fail on stale copies; Fresh checks compare regenerated output
byte-for-byte without overwriting it. A packaging test checks all six registered
grammars and the three injection targets. Kakoune's packaging tests enforce
metadata-only adaptation and stale-copy detection; its real-editor smoke check
skips loudly when Kakoune or giallo-kak is unavailable. See the
[Kakoune investigation](../docs/KAKOUNE.md) for the observed shared-corpus
boundaries and the separate Unicode fixture.

`mise run //tools/scope-parity:test` is a separate, heavier **transformed
compatibility-reference** comparison against syntect. `mise run gate` also runs
it. It is not proof that Fresh matches the unmodified shipped VS Code grammar:
see the documented reference exceptions and intentionally retained conversion
limitations in the harness README.
