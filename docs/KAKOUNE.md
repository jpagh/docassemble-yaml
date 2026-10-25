# Kakoune highlighting — investigation

Status: manually activated prototype verified with **Kakoune 2026.05.21**,
**giallo-kak 0.4.0 (66d0731)** and its **giallo 0.5.2** dependency,
on macOS arm64. Installable example: [`kakoune/`](../kakoune/README.md).
No auto-detection, kak-lsp integration, cross-engine harness, or support matrix
is included here.

## Result

The canonical TextMate **rules load directly**, without Fresh's syntect
conversion. YAML, embedded Python, Mako, Jinja and JavaScript reach Kakoune's
ranges highlighter. A small **metadata-only packaging adaptation** is necessary;
copying all six canonical JSON files verbatim is not sufficient. This is not a
claim of VS Code visual parity or complete Docassemble grammar coverage.

## Environment and loading

Commands used:

```sh
kak -version                      # Kakoune 2026.05.21
giallo-kak --version              # giallo-kak 0.4.0 (66d0731)
giallo-kak init                    # embedded upstream Kakoune integration
```

The tested giallo binary came from the upstream v0.4.0 release archive
`giallo-kak-aarch64-apple-darwin.tar.gz`; the example documents that pinned
install route. No local Rust build or patched plugin was used. Source inspected:
upstream `registry_loader.rs`, `main.rs`, `config.rs`, `highlight.rs`,
`highlighting.rs`, `rc/giallo.kak`; giallo 0.5.2 `registry.rs` and
`grammars/{raw,compiled,injections}.rs`.

Observed by copying unmodified `grammars/textmate/*.json` into a clean custom
grammar directory and running `giallo-kak --verbose list-grammars`:

- YAML and Mako load.
- All three injections fail JSON parsing: **missing field `name`**.
- Jinja fails: **Tried to replace grammar `jinja` after linking** (a built-in
  name collision).

The front end starts with `Registry::builtin()`, adds custom grammars, then
calls `link_grammars()`. It loads a custom directory only when `grammars_path`
is explicitly configured. It reads config from
`$XDG_CONFIG_HOME/giallo.kak/config.toml`, falling back to
`$HOME/.config/giallo.kak/config.toml`. Aliases come from JSON `fileTypes` and
from the filename before the first dot. The canonical YAML has no `fileTypes`;
a copy still named `yaml.tmLanguage.json` would claim `yaml`, not an independent
Docassemble alias. The listing command alone is not proof of successful
highlighting; the real-editor range assertions below are the proof.

### Narrow adaptation

`kakoune/scripts/sync_grammars.py` generates all six committed packaging files:

- YAML becomes `docassemble.tmLanguage.json`, with `name: docassemble`.
- Mako/Jinja get unique `docassemble-mako` / `docassemble-jinja` names.
- Each injection gets a unique `docassemble-*-injection` name and
  `injectTo: ["docassemble"]`.

`scopeName`, `injectionSelector`, regexes, patterns, repositories and includes
are unchanged. The generator does not lower or repair rules. Unit tests compare
all other fields to the canonical sources and check committed output for
staleness. Fresh's existing converter was reviewed but is unnecessary and
incompatible with direct TextMate loading here.

`injectTo` is required because giallo links external injections **by target
grammar name**, not by scope name or by scanning selector text. VS Code supplies
registration separately in its manifest; this metadata supplies the analogous
registration for giallo. The example config maps `docassemble` to the independent
filename alias; activation explicitly sets buffer `giallo_lang`, never claims
`.yml` globally.

### Dependencies

`source.python` and `source.js` resolve from giallo's built-ins.
`source.mako` and `source.jinja` resolve from the packaged shared grammars by
scope name, despite their unique registration names. This is supported by both
source inspection and observed Python `def`/`return`/logical-operator scopes,
Mako doc comments, shared Jinja variable/tag scopes and JS `var` reaching the
editor. No external dependency download or alternative Python grammar is needed.
The YAML injection's `source.yaml` includes continue to resolve to giallo's
built-in YAML; they are deliberately not rewritten.

## Scope-to-face evidence and shared corpus

The existing ASCII-only [`grammars/fixtures/sample.yml`](../grammars/fixtures/sample.yml)
already covers all needed boundaries; it is unchanged. The focused test opens
that exact file's bytes in a temporary copy. Its diagnostic TextMate theme
[`scope-probe.json`](../kakoune/fixtures/scope-probe.json) assigns unique colours
to selected scopes. giallo converts theme styles to generated faces
`giallo_0001`, etc., deduplicates identical styles, and emits byte-column ranges
in buffer option `giallo_hl_ranges`. These are not Kakoune semantic faces such
as `Keyword`: themes style scopes first, then giallo allocates faces. The check
reads actual buffer ranges and maps face names back to emitted definitions via
upstream's `GIALLO_DEBUG_FILE`; it does not assume stable face numbers.

Observed with all packaged grammars:

| Shared lines | Observation |
|---|---|
| 5–9, 38–46 | YAML keys and comments; line 46 `event` proves return to YAML after embedded blocks. |
| 14–15 | `${...}` gets `source.mako.expression` (blue). |
| 16 | `<%doc>` body gets `comment.block.mako` (grey). |
| 17 | `{{...}}` and `{%...%}` receive shared Jinja variable/tag scopes (magenta). |
| 20–22 | `code:` body gets Python scopes (green), `def`/`return` specifically receive Python keyword scopes (cyan). |
| 24 | `and not` receives Python logical-operator scope (cyan). Inline content is not uniformly wrapped in `source.python`. |
| 25–26 | `need:` list is present, but its bare `admin` has no diagnostic-theme colour; not independent proof of Python classification. |
| 28–29 | `show if:` body receives `source.python` (green). |
| 31–32 | `on change:` shorthand list remains YAML-looking; this fixture is not a Python mapping-body example. |
| 34–35 | `script:` `var` receives built-in `storage.type.js` (yellow). |

This deliberately records unproven cases rather than treating every uncoloured
span as an engine failure. Ordinary plain scalars can appear flat with the
normal theme. Colour presence is evidence for these selected scopes, not a full
scope-stack dump or a comprehensive grammar semantics test.

### Injection selectors

All selectors are retained verbatim. The committed check starts separate clean
sessions with each injection omitted in turn:

| Injection | Selector | Observed effect |
|---|---|---|
| Python | `L:source.docassemble.yaml` | Fires: removing it removes `def`/`return` and logical-operator colours, the `show if:` wrapper, and JS `var`. |
| Jinja | `L:source.docassemble.yaml -comment` | Fires: removing it removes the Jinja colours on line 17. Unicode fixture's YAML comment containing both template syntaxes remains a comment. |
| Mako | `R:source.docassemble.yaml -comment` | Registered; removing it makes **no visible difference in the shared corpus**, because base YAML already includes Mako. Mako support must not be attributed solely to this injection. |

A separate throwaway **selector-isolation experiment** confirmed that the Mako
selector can fire: empty only the temporary base grammar's `patterns` and
`repository` (preserving its root scope and registration), then highlight the
same corpus. With Mako injection present, line 14 `${...}` is blue and line 16's
doc body grey; with that injection omitted both are default. This controlled
experiment is not a shipped grammar change. Reproduce from repository root
with the same installed tools as the focused check:

```sh
python3 - <<'PY'
import json, pathlib, shutil, sys, tempfile, time
sys.path.insert(0, 'kakoune/scripts')
from check_highlighting import Session, quote
for omitted in (None, 'mako'):
    with tempfile.TemporaryDirectory() as home:
        s = Session(pathlib.Path(home).resolve(), shutil.which('kak'),
                    shutil.which('giallo-kak'), omitted)
        try:
            p = s.home / '.config/giallo.kak/grammars/docassemble.tmLanguage.json'
            grammar = json.loads(p.read_text())
            grammar.update(patterns=[], repository={})
            p.write_text(json.dumps(grammar))
            time.sleep(0.2)
            s.send(f'source {quote(s.rc)}\n'
                   'set-option global giallo_auto_enable false\n'
                   'set-option buffer giallo_lang docassemble\n'
                   'set-option buffer giallo_theme docassemble-probe\ngiallo-enable')
            s.wait_for(lambda: s.max_line() >= 46)
            print(omitted, s.color(14, 9), s.color(16, 12))
        finally:
            s.close()
PY
# None 0000FF 999999
# mako default default
```

Thus giallo's selector implementation is usable, including the `L:` / `R:`
registration paths; the base grammar often shadows or duplicates R-priority
Mako matches. This does not prove equivalence of every selector edge case to
vscode-textmate.

## Unsaved buffers, Unicode and update limitations

[`kakoune/fixtures/unicode.yml`](../kakoune/fixtures/unicode.yml) is editor-specific;
non-ASCII is intentionally kept out of the shared corpus. The automated check
replaces the open buffer with it **without writing the file**:

- `café` and an emoji precede `${ 1 + 2 }` and `{{ café }}`. Their first byte
  columns are **14** and **27**, with the Jinja closing delimiter ending at
  byte **37**. The actual ranges align with these UTF-8 offsets.
- A Python string contains an accent and emoji; its line remains Python.
- A YAML comment containing `{{ ignored }} ${ ignored }` stays grey.
- An unsaved replacement removing the template expressions clears their
  colours; the next YAML key stays red. The disk bytes remain unchanged.

The upstream plugin writes the **buffer**, not the interview file, to its FIFO.
It has idle/insert hooks and rate limiting (50ms by default); the test explicitly
requests `giallo-force-update` after resetting the rate-limit timestamp, because
a headless daemon has no interactive idle events. On this macOS version the
plugin's BSD `date` fallback uses whole-second precision, so repeated updates
within one second can be delayed. For manual checks, pause and force an update.

Observed limitation: overlapping initial handshakes can transiently concatenate
FIFO snapshots (one probe produced roughly double the fixture's lines). The
check waits for the first response, allows bootstrap to settle, then explicitly
refreshes and requires the correct final line boundary. This is an upstream
transport/update issue, not repaired here. Large buffers, incremental reparse
windows, all Unicode scripts, grapheme rendering and interactive refresh timing
are not certified by this small test. The example manually removes the built-in
window YAML highlighter to avoid competing highlighting; disabling giallo does
not restore it.

## Reproduction and validation boundary

Follow [`kakoune/README.md`](../kakoune/README.md) for copy/config/manual activation.
The documented install and activation were also exercised by hand in a **clean
temporary HOME and XDG_CONFIG_HOME**, using the normal Catppuccin theme (not
just the diagnostic theme), loading `giallo-kak init`, opening an absolute
fixture path and reading nonempty ranges back from Kakoune. Unicode and an
unsaved template edit were exercised in that sandbox too.

Headless recipe (unlike an interactive client, daemon output from `echo` is
discarded): start `kak -d -s <short-session> /absolute/fixture.yml` in the
background, send commands using `kak -p`, and wrap buffer commands with
`evaluate-commands -buffer /absolute/fixture.yml %{ ... }`. Read ranges with:

```kak
evaluate-commands -no-hooks -buffer /absolute/fixture.yml %{
    nop %sh{ printf '%s' "$kak_opt_giallo_hl_ranges" > /absolute/ranges.txt }
}
```

Do not let the driving shell expand `%sh` variables (use a quoted heredoc).
Use a short session name because Unix socket path lengths are limited.
End with `giallo-stop-server` and **`kill!`**; `quit!` alone did not terminate
these headless sessions reliably.

Validation commands (prefix with `MISE_EXPERIMENTAL=1` where required):

```sh
mise run //kakoune:grammar:sync
mise run //kakoune:check             # real-editor assertions if tools on PATH
mise run check                     # full monorepo gate, including this check
```

With tools absent, the live portion loudly prints `SKIP` and exits 0; packaging
staleness and three unit tests still run. With tools present the live check takes
about five seconds locally. Executables resolve from PATH, with optional
`KAKOUNE_BIN` / `GIALLO_KAK_BIN` overrides; no temporary-machine paths are
committed. The test cleans up its own sessions and temporary HOME directories.
The Mako selector-isolation control above stays manual; visual appearance and
interactive idle timing also remain manual. No substantial converter/bridge or
giallo patch was needed, so no expansion approval was required.
