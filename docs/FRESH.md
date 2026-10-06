# Fresh editor support — investigation

Status: prototype verified against Fresh 0.5.2 (Homebrew), September 2026.
Deliverable prototype lives in [`fresh/`](../fresh/README.md).

## TL;DR

- Fresh is a good fit for both goals. It highlights with **syntect**
  (TextMate/Sublime grammars) and speaks LSP natively — no editor fork or
  TypeScript plugin is required.
- An **installable language pack** (`package.json` + one `.sublime-syntax`
  + `fresh.lsp`) gets Docassemble highlighting and auto-starts
  `docassemble-lsp`, including diagnostics, completion, hover, navigation,
  symbols, code actions, formatting, semantic tokens, inlay hints and
  folding. This is verified end-to-end with the pack in `fresh/`.
- The main work is **grammar conversion**, not LSP: syntect only understands a
  subset of `.sublime-syntax` (no `begin`/`end`), so the VS Code TextMate
  grammars are lowered by `fresh/scripts/build_syntax.py`. The prototype
  already reproduces the VS Code look for Docassemble keys, Mako `${...}` /
  `<%...%>`, Jinja `{{...}}` / `{%...%}`, and the Python injection for `code:`,
  `if:`, `need:`, `show if:` and `script:`.
- One product decision is required: Docassemble files are plain `.yml`.
  The pack deliberately claims **no extension** and detection is configured
  with path globs (e.g. `**/data/questions/**/*.yml`), so Fresh does not
  hijack every YAML file. A one-line config can claim `.yml` globally for
  users who want that.
- Known gaps: Fresh has no `textDocument/documentLink` support (ctrl-click
  include paths), no `workspace/didChangeWatchedFiles` (external edits to
  `.py`/`.yml` are not re-indexed until a save inside Fresh), and LSP
  semantic tokens are off by default.

## How Fresh supports a new language

Fresh loads language packs from `~/.config/fresh/languages/packages/<name>/`.
A pack is a `package.json` whose `fresh` block carries up to three things
(`crates/fresh-editor-core/src/packages.rs`,
`crates/fresh-editor-core/src/primitives/grammar/loader.rs`):

| `fresh` key | Effect |
|---|---|
| `grammar` | loads `<file>.sublime-syntax`; maps `extensions` → grammar; optional `shortName` alias. (The `firstLine` field in the schema is not wired up in 0.5.2.) |
| `language` | comment prefix, tab size, auto-indent, formatter |
| `lsp` | command, args, auto-start, initialization options — registered under the pack name as the language id |

Pack `lsp`/`language` entries are applied only if the user hasn't defined the
same language: `config.lsp.entry(lang).or_insert(pack_config)`. Overriding in
`~/.config/fresh/config.json` therefore replaces the whole entry.

Language detection is config-driven (`crates/fresh-editor-core/src/language_detect.rs`):
exact filename → glob → extension, all from `[languages.<id>]`. Grammar
resolution then reconciles the config id with a grammar entry by name
(`detected_language.rs:align_with_config_id`). This is what lets a pack avoid
claiming `.yml`:

```json
{ "languages": { "docassemble": {
    "filenames": ["**/data/questions/**/*.yml"],
    "grammar": "docassemble" } } }
```

Glob with `/` matches the full path, `**` crosses directories. `grammar` can
be the pack's `shortName` or display name.

Fresh's LSP client (`crates/fresh-editor/src/services/lsp/manager.rs`,
`services/lsp/async_handler.rs`) advertises and handles:

- synchronization (`didOpen`/`didChange`/`didSave`), diagnostics,
  completion + resolve, hover, definition/declaration/typeDefinition,
  implementation, references, document symbols, workspace symbols,
  code actions + resolve, formatting + range formatting, rename,
  signature help, folding ranges, inlay hints, semantic tokens
  (full/delta/range), server-initiated edits and dynamic registration.
- It does **not** implement document links, watched files, or
  `workspace/didChangeConfiguration` (the server logs that notification as
  unknown today).

LSP is configured either per language in `config.json` (`[lsp.<id>]`) or in the
pack. Root discovery uses `root_markers` (nearest ancestor containing one of
the markers, default `[".git"]`, falling back to the file's directory), or a
plugin can set a per-language root. Semantic tokens are gated behind
`editor.enable_semantic_tokens_full` (default `false`).

## What the prototype does

`fresh/` contains:

- `package.json` — language pack manifest (`extensions: []`,
  `shortName: "docassemble"`, LSP command `docassemble-lsp lsp`).
- `grammars/Docassemble.sublime-syntax` — generated, committed.
- `scripts/build_syntax.py` — lowers the VS Code TextMate grammars to the
  syntect subset.
- `validate.sh`, `README.md` — install and configuration instructions.

`tools/scope-parity/` contains the scope-parity test described below.

Verified in an isolated `HOME` with Fresh 0.5.2 and a copy of
`lsp/tests/fixtures/demo_package`:

1. `fresh --cmd grammar list` shows `Docassemble` from the pack.
2. A file matching the glob opens with language **Docassemble** (status bar),
   not YAML.
3. The pack's LSP entry starts automatically: status line reads
   `LSP (docassemble) ready` / `LSP (on)`.
4. A deliberate `E306` error in a fixture file shows the gutter marker and
   `E:1` in the status line — diagnostics flow end-to-end.
5. Rendered colours (Dracula) show Docassemble key injection
   (`if: some_condition` parses as Python), `code: |` and `script: |` bodies
   as Python/JS, `${...}` and `<%doc>` as Mako, `{{...}}`/`{%...%}` as Jinja,
   and ordinary YAML comments/keys/values as normal YAML.

## Grammar conversion (the real work)

Syntect's `.sublime-syntax` loader (`syntect 5.3` with `yaml-load`) accepts a
much smaller language than Sublime Text:

- Supported: `match`, `include`, `push`/`pop`/`set`, inline pushed contexts,
  `captures` (plain scope names), `meta_scope`, `meta_content_scope`,
  `embed`+`escape`, `with_prototype`, `variables`, `first_line_match`, the
  reserved top-level `prototype` context.
- **Not** supported: `begin`/`end`, `contentName`, nested `patterns` inside
  captures, `applyEndPatternLast`, `while`.

Plus three sharp edges that cost debugging time and are worth knowing:

1. **Same-syntax includes must be bare context names** (`include: comment`).
   The Sublime `include: '#comment'` spelling parses to an empty name and
   silently matches nothing.
2. **Capture keys must be unquoted YAML integers** (`1:`, not `'1':`).
   syntect reads them with yaml-rust's `as_i64`, which only accepts real
   integers; quoted keys are dropped silently.
3. **Cross-syntax include needs `include: scope:source.python`**; the TextMate
   `include: source.python` form resolves only within the same grammar.

`build_syntax.py` performs the lowering:

- `begin`/`end` → `match` + `push` of an inline context, with `name` as both
  the match scope and the context `meta_scope`, `contentName` as
  `meta_content_scope`, and the end rule placed **before** the nested patterns
  (TextMate default) so embedded grammars can't swallow the closing delimiter.
- `#repository-entry` includes → bare names; `source.mako` → an inlined,
  `mako_`-prefixed context tree; `source.python`/`text.html.basic` →
  `scope:` references to grammars syntect already ships; `$self`/`$base`
  → the inlined Mako root.
- The VS Code `python-injection` (which targets `code:`, `if:`, `need:`,
  `show if:`, `on change:`, `script:`, `.using(`) is emitted as a
  `python_injection` context and included from the YAML `block-node`/
  `flow-node` contexts. It is *not* put in the reserved `prototype` context:
  a global prototype outranks a block scalar's own end pattern, so a `code: |`
  line following a multi-line scalar hijacked the parser and swallowed
  subsequent lines.
- YAML's own `prototype` repository entry is renamed to `yaml_prototype`,
  because the name is reserved by Sublime/syntect for auto-injection.
- Jinja is inlined (`jinja_` prefix) and tried wherever Mako is embedded, and
  the undefined `#block-python` reference in the base grammar is dropped.
- `beginCaptures`/`endCaptures` fall back to a shared `captures` map the way
  TextMate and vscode-textmate do (the Jinja `{% %}` delimiters rely on it).
- The comment rule's `(?!\G)` end becomes `$`: lowered verbatim, syntect pops
  the context at end of line but leaves parser state that makes the first
  character of the next line lose its scopes.
- Block-scalar bodies are scoped `string.unquoted.block.yaml` (upstream's
  scope) instead of the fork's ineffective `source.mako` wrapper, with Mako
  and Jinja kept as content patterns so `${...}`/`{{...}}` still highlight.
  The scope-parity reference applies the matching normalisation; see
  `tools/scope-parity/README.md`.

Source of truth stays `vscode/syntaxes/*.tmLanguage.json`; regenerate with:

```bash
uv run --project lsp python fresh/scripts/build_syntax.py
```

## Gaps and risks

| Area | Status |
|---|---|
| `begin`/`end` lowering fidelity | A scope-parity test compares the generated grammar against the original grammars under vscode-textmate (`mise run //tools/scope-parity:test`): 46 fixture lines, zero undocumented differences. The reference applies three documented engine patches (TextMate `\G`-across-lines, captures in zero-width lookaheads, and the fork's ineffective block-scalar Mako wrapper); see `tools/scope-parity/README.md`. |
| Capture-nested `patterns` | Dropped (only affects an "invalid indent indicator" scope in the YAML grammar). |
| Plain scalar scopes | The VS Code grammar names plain scalars `unquoted.plain.*.yaml`, which Fresh themes don't colour (the built-in YAML grammar uses `string.unquoted.*`). This matches VS Code's own behaviour but means plain values look flat in colour schemes that only style `string.*`. |
| `.yml` detection | Solved with user-config globs; a public pack cannot ship globs, so installation is two steps (install + config block). Claiming `.yml` is a one-line alternative for users who never edit other YAML. |
| Document links | Not available in Fresh (no client support). Includes/assets are still navigable through go-to-definition/references. |
| Watched files | Fresh does not send `workspace/didChangeWatchedFiles`; the server re-indexes on saves inside Fresh and on `didSave` of `.py`/`.yml`, but external changes need an LSP restart. |
| Semantic highlighting | Off by default; enable with `editor.enable_semantic_tokens_full`. |
| Server on PATH | The pack registers `docassemble-lsp lsp`; users with project venvs must override `[lsp.docassemble]` (user config replaces, not merges). Setting `root_markers: ["docassemble", "pyproject.toml", ".git"]` is recommended so the server indexes the package root. |
| Distribution | `Package: Install from URL` supports monorepo subpaths (`https://github.com/jpagh/docassemble-yaml#fresh`), and the [fresh-plugins-registry](https://github.com/sinelaw/fresh-plugins-registry) accepts a PR adding a `repository` entry with the same fragment. Both are unverified end-to-end (the install flow itself was read, not run through the UI). |
| Fresh version drift | Built and tested against 0.5.2; the pack targets the stable pack/LSP surface, which has been stable in the 0.5.x line. |

## Suggested next steps

1. Decide the detection default (globs vs. global `.yml`) and publish the
   pack — the prototype is installable as-is.
2. Extend the scope-parity fixture as the VS Code grammars gain constructs;
   the harness and reference patches are in `tools/scope-parity/`.
3. Optionally add a small TypeScript plugin for zero-config detection
   (`after_file_open` → `setBufferLanguage` when the path contains
   `/data/questions/`), but only if the config-glob step proves to be a
   adoption problem.

## Reproducing the sandbox used for verification

```bash
export HOME=/tmp/fresh-home                       # isolate Fresh state
mkdir -p $HOME/.config/fresh/languages/packages/docassemble
cp -R fresh/* $HOME/.config/fresh/languages/packages/docassemble/
cat > $HOME/.config/fresh/config.json <<'JSON'
{ "languages": { "docassemble": {
    "filenames": ["**/data/questions/**/*.yml"],
    "grammar": "docassemble" } } }
JSON
cd /path/to/a/docassemble-package
HOME=$HOME fresh --no-restore docassemble/<pkg>/data/questions/main.yml
```
