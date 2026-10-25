# Docassemble highlighting in Kakoune

A sourceable filetype plugin using [giallo.kak](https://github.com/Yukaii/giallo.kak),
not a new highlighter. Tested with **Kakoune 2026.05.21** and
**giallo-kak 0.4.0 (66d0731)** / giallo 0.5.2 on macOS arm64.
See [the investigation](../docs/KAKOUNE.md) for evidence and limitations.
No kak-lsp integration is included.

## Install

Install Kakoune (for example, `brew install kakoune`). Install the tested
giallo release from [v0.4.0](https://github.com/Yukaii/giallo.kak/releases/tag/v0.4.0):

```sh
# macOS Apple Silicon; choose the matching archive on other platforms.
mkdir -p "$HOME/.local/bin"
curl -fsSL https://github.com/Yukaii/giallo.kak/releases/download/v0.4.0/giallo-kak-aarch64-apple-darwin.tar.gz |
  tar -xz -C "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"
kak -version
giallo-kak --version
```

From this repository's root, copy the **generated** grammars and the plugin:

```sh
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
mkdir -p "$config_home/giallo.kak/grammars" "$config_home/kak"
cp kakoune/grammars/*.json "$config_home/giallo.kak/grammars/"
cp kakoune/config.toml "$config_home/giallo.kak/config.toml"
cp kakoune/rc/docassemble.kak "$config_home/kak/docassemble.kak"
```

For an existing installation, **merge** `config.toml` instead of overwriting it.
If `XDG_CONFIG_HOME` is set, adjust `grammars_path` in the copied config to that
absolute directory. giallo 0.4.0 requires the explicit path setting; merely
copying files to the default directory is not enough. Restart giallo/Kakoune
after changing grammars (they load at server startup).

Add to `$config_home/kak/kakrc`, in this order:

```kak
evaluate-commands %sh{ giallo-kak init }
set-option global giallo_auto_enable false
source %sh{ printf '%s/kak/docassemble.kak' "${XDG_CONFIG_HOME:-$HOME/.config}" }
```

Disable upstream auto-enable **before opening files** so it does not highlight
all YAML independently of this plugin. Sourcing the Docassemble plugin repeatedly
is safe; do not repeatedly load the upstream `giallo-kak init` integration.
No keybindings are installed or changed.

## Automatic and explicit activation

Opening either `.yml` or `.yaml` beneath a `data/questions/` directory, at any
depth, sets buffer `filetype=docassemble`, `giallo_lang=docassemble`, two-space
`indentwidth`/`tabstop`, and buffer-local comment options (`comment_line='#'`,
no block comment delimiters). Kakoune core ships no comment command and this
plugin installs no mappings, so the comment options are there for your own
comment mapping to read (YAML has no block comments).
Ordinary YAML is left alone, including `notdata/questions/`,
`data/questions-old/`, and `data/questions.yml`. There is no workspace crawl
or content sniffing; a package metadata file is not required.

For an interview elsewhere (including `grammars/fixtures/sample.yml`):

```kak
edit /absolute/path/to/interview.yml
docassemble-enable
```

To stop highlighting and restore the buffer's previous filetype and effective
indent/comment settings:

```kak
docassemble-disable
```

Disabling opts this buffer out of automatic detection until `docassemble-enable`
or an explicit `set-option buffer filetype docassemble`. A direct change to
another filetype also tears down Docassemble without immediately re-claiming
YAML. No unrelated buffer is affected. Restored settings are buffer-local
snapshots (not re-inherited from subsequently changed global defaults).

Automatic activation follows renamed paths on the next display, write or reload;
Kakoune has no rename hook. Explicit activation survives renames.
Reloading and repeated activation do not add duplicate hooks/highlighters.
To unload, disable active buffers, then `remove-hooks global docassemble`.

## Themes and troubleshooting

Giallo maps TextMate scopes through its theme to generated `giallo_*` faces,
independent of Kakoune's standard colour scheme. The example uses
`catppuccin-frappe`; no custom Kakoune face definitions are needed. Switching
filetype lets Kakoune tear down/recreate its normal YAML window highlighter;
this plugin does not manually remove it.

If there is no colour, check `giallo-kak --version`, the configured grammar path,
and `:giallo-debug`; stop a stale server with `:giallo-stop-server`. Ensure the
upstream integration was loaded first. With giallo missing or failing, filetype
and editing settings still apply; after fixing installation, run
`:docassemble-disable` then `:docassemble-enable` to retry.

The sample covers YAML, embedded Python, Mako, Jinja and JavaScript. Try
`kakoune/fixtures/unicode.yml` with explicit activation for accents/emoji. Edits
need not be saved. After a pause, `:giallo-force-update` can refresh delayed
colours; giallo's macOS clock fallback can delay updates within one second.
The upstream shared server is not stopped when just one buffer is disabled.

## Develop and check

Canonical sources remain `grammars/textmate/*.json`; do not edit generated
`kakoune/grammars/` files. Packaging changes only registration metadata:

```sh
MISE_EXPERIMENTAL=1 mise run //kakoune:grammar:sync
MISE_EXPERIMENTAL=1 mise run //kakoune:check
```

Checks always run formatting/lint, packaging staleness and the plugin's own
shell decision block against [shared detection cases](../fixtures/detection/README.md).
With `kak` installed, deterministic headless tests exercise the actual hooks,
settings restoration, filetype/rename/reload lifecycle, repeated sourcing,
plain YAML isolation and missing/failing giallo (no server required).
Without Kakoune those tests print **SKIP** and succeed.

With both `kak` and `giallo-kak`, the live smoke check automatically activates a
nested `.yaml` through this plugin, and retains all shared-boundary,
per-injection omission, unsaved Unicode and removal assertions. Otherwise it
prints **SKIP** and exits successfully. Optional executable overrides:
`KAKOUNE_BIN` / `GIALLO_KAK_BIN` (paths or PATH names).
The root check includes these fast tasks; no tools are downloaded by probes.

The clean-HOME installation route and explicit activation were also exercised
with the normal giallo theme. Visual equivalence, interactive idle timing and
large-buffer behaviour remain manual, not cross-engine parity guarantees.
