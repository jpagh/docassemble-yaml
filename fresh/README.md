# Docassemble support for Fresh

A [Fresh](https://github.com/sinelaw/fresh) bundle for Docassemble
interviews: syntax highlighting that matches the VS Code extension
(`vscode/syntaxes/*.tmLanguage.json`), zero-config detection of interview
files, and `docassemble-lsp` wiring.

- `package.json` — bundle manifest (grammar, language settings, LSP, plugin).
- `docassemble.ts` — detection plugin (see
  [Detect Docassemble YAML files](#detect-docassemble-yaml-files)).
- `grammars/Docassemble.sublime-syntax` — generated grammar (committed).
- `scripts/build_syntax.py` — regenerates it from the VS Code TextMate
  grammars. Run it after editing those:

  ```bash
  uv run --project lsp python fresh/scripts/build_syntax.py
  ```

- `validate.sh` — manifest sanity check (`mise run //fresh:check`).

## Install

Install the pack from this monorepo subdirectory:

1. Open the command palette (`Ctrl+P`, then `>`), run
   **Package: Install from URL**, and enter:

   ```
   https://github.com/jpagh/docassemble-yaml#fresh
   ```

   (A local checkout works too: `/path/to/docassemble-yaml#fresh`.)

2. Restart Fresh, or run **Package: Reload**.

Check it loaded:

```bash
fresh --cmd grammar list | grep Docassemble
```

## Detect Docassemble YAML files

Docassemble interviews are ordinary `.yml` files, so nothing in a language
pack manifest can claim them without also claiming every other YAML file.
The pack's plugin instead watches for files under a package's
`data/questions/` directory (subdirectories included) — where docassemble
itself looks for interviews — and switches those buffers to the
`docassemble` language. That is what routes them to the grammar and the
language server. Every other YAML file (GitHub Actions, Kubernetes, …)
stays YAML and starts no server.

Interviews kept outside `data/questions/` are still covered by the ordinary
Fresh config route. Fresh detects these before the file opens, so the plugin
never has to act:

```json
{
  "languages": {
    "docassemble": {
      "filenames": [
        "**/my-interviews/**/*.yml"
      ],
      "grammar": "docassemble"
    }
  }
}
```

`filenames` entries containing `*`/`?` are globs; a pattern with a `/` is
matched against the full path, and `**` crosses directories. Exact filenames
are also accepted.

If every `.yml` file you open really is Docassemble, you can skip the globs
and claim the extension globally:

```json
{
  "languages": {
    "docassemble": { "extensions": ["yml"], "grammar": "docassemble" }
  }
}
```

### What the plugin does about the language server

Switching the language also points the buffer at `docassemble-lsp`. Fresh's
normal auto-start brings the server up on the next render, and the plugin
sends one wake-up request so that also happens in sessions that do not
render (a daemon with no attached client). A file opened *after* the server
is already running joins it on first interaction (edit, hover,
completion); run **docassemble: Reattach language server** from the command
palette to attach it immediately. Fresh only sends `textDocument/didOpen`
for buffers it had already classified when the server started.

## Language server

The pack registers `docassemble-lsp lsp` (stdio) for the `docassemble`
language, auto-starting it when an interview opens. Install the server so
the command is on `PATH`:

```bash
uv tool install docassemble-lsp
# or: pipx install docassemble-lsp
```

If the server lives in a project virtualenv, override the whole entry in
`~/.config/fresh/config.json` — user config replaces the pack's entry rather
than merging with it, so repeat `command`/`args`:

```json
{
  "lsp": {
    "docassemble": {
      "command": "uv",
      "args": [
        "run", "--project", "/path/to/your/project",
        "docassemble-lsp", "lsp"
      ],
      "auto_start": true,
      "root_markers": ["docassemble", "pyproject.toml", ".git"]
    }
  }
}
```

`root_markers` is worth setting: the server scans the package rooted at the
directory Fresh passes in `initialize`. The nearest ancestor containing one of
the markers wins; without a marker, only the file's own directory is indexed
and cross-file navigation misses the rest of the package.

## Completions

Fresh shows the completion popup on request by default — press `Ctrl+Space`.
For VS Code-style suggestions while typing, enable auto-show in
`~/.config/fresh/config.json`:

```json
{ "editor": { "completion_popup_auto_show": true } }
```

With auto-show on, word characters trigger after `quick_suggestions_delay_ms`
(150 ms default) and the server's trigger characters (`:`, space, `.`) trigger
immediately. Set `quick_suggestions: false` to trigger only on those
characters.

## Enable semantic highlighting

Fresh disables LSP semantic tokens by default. Enable them in
`~/.config/fresh/config.json`:

```json
{ "editor": { "enable_semantic_tokens_full": true } }
```

## What works

| Feature | Fresh | Notes |
|---|---|---|
| Diagnostics | yes | inline markers, status-bar count, `F8` navigation |
| Completion | yes | server triggers on `:`, space, `.` |
| Hover, definition, references, implementation | yes | |
| Document/workspace symbols | yes | |
| Code actions / quick fixes | yes | |
| Formatting (document and range) | yes | |
| Semantic tokens | yes | off by default, see above |
| Inlay hints, folding ranges | yes | |
| Document links (ctrl-click includes) | no | Fresh has no `textDocument/documentLink` client support |
| External `.py`/`.yml` change notifications | no | Fresh does not send `workspace/didChangeWatchedFiles`; saving inside Fresh re-indexes |

## Grammar development

The pack itself is checked by `mise run //fresh:check` (ruff formatting and
lint, `validate.sh`, and a staleness check that regenerates the grammar and
compares it byte-for-byte). That runs as part of `mise run check`.

The generated grammar is additionally validated against the original VS Code
TextMate grammars by a scope-parity test:

```bash
mise run //tools/scope-parity:test
```

It tokenizes `tools/scope-parity/fixtures/sample.yml` with vscode-textmate
(the VS Code engine) and with syntect (Fresh's engine) and diffs the
per-character highlight categories. See `tools/scope-parity/README.md` for
the documented reference patches and how to add fixture cases.

Regenerate the grammar after editing `vscode/syntaxes/*.tmLanguage.json`:

```bash
uv run --project lsp python fresh/scripts/build_syntax.py
```

The plugin (`docassemble.ts`) is not compiled or bundled; Fresh transpiles it
at load time. To type-check it against the editor API, point a `tsconfig.json`
at Fresh's `types/fresh.d.ts` (written to `~/.config/fresh/types/`) and run
`npx tsc --noEmit`.

## Attribution

The grammar is generated from the TextMate grammars shipped in this
repository's VS Code extension. The YAML base grammar is derived from
[textmate/yaml.tmbundle](https://github.com/textmate/yaml.tmbundle) (MIT);
the Mako and Jinja grammars come from the same `vscode/syntaxes/` directory.
