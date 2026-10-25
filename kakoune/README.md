# Docassemble highlighting in Kakoune (manual example)

A prototype using [giallo.kak](https://github.com/Yukaii/giallo.kak), not a new
highlighting plugin. Tested with **Kakoune 2026.05.21** and
**giallo-kak 0.4.0 (66d0731)** / giallo 0.5.2 on macOS arm64.
See [the investigation](../docs/KAKOUNE.md) for evidence and limitations.
This example does **not** detect interviews or configure kak-lsp.

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

From this repository's root, copy the **generated** grammar package:

```sh
mkdir -p "$HOME/.config/giallo.kak/grammars"
cp kakoune/grammars/*.json "$HOME/.config/giallo.kak/grammars/"
cp kakoune/config.toml "$HOME/.config/giallo.kak/config.toml"
```

For an existing installation, **merge** `config.toml` instead of overwriting it.
If `XDG_CONFIG_HOME` is set, put the config there and adjust `grammars_path` to
that directory. giallo 0.4.0 requires the explicit path setting; merely copying
the files to the default directory is not enough. Restart giallo/Kakoune after
changing grammar files (they load at server startup).

## Activate by hand

In Kakoune, load the upstream integration and disable its default auto-enable
**before opening another buffer**:

```kak
evaluate-commands %sh{ giallo-kak init }
set-option global giallo_auto_enable false
```

Open an interview, e.g. `:edit /absolute/path/to/grammars/fixtures/sample.yml`,
and run these buffer-local commands:

```kak
set-option buffer giallo_lang docassemble
giallo-enable
try %{ remove-highlighter window/yaml }
```

This sets only giallo's language, not Kakoune's `filetype`; other YAML buffers
remain untouched. The final command avoids layering the built-in YAML
highlighter over giallo's ranges. No detection or activation hooks are shipped.
The upstream plugin itself supplies edit/idle refresh hooks once enabled.

The sample demonstrates YAML keys/comments/values, Python in `code:` / `if:` /
`show if:`, Mako `${...}` and `<%doc>`, Jinja `{{...}}` and `{%...%}`,
and JavaScript in `script:`. Open `kakoune/fixtures/unicode.yml` and repeat
activation to check accented characters/emoji before embedded regions. Edit a
region without saving; run `:giallo-force-update` after a pause if needed.
Use `:giallo-disable` to stop highlighting this buffer (it does not restore the
removed built-in YAML highlighter). `:giallo-stop-server` stops the shared server.

## Develop and check

Canonical sources remain `grammars/textmate/*.json`. This package changes only
registration metadata: unique `name`s and injection `injectTo`, plus the YAML
packaging filename. Rules, scopes and selectors are unchanged. Do not edit
`kakoune/grammars/` by hand:

```sh
mise run //kakoune:grammar:sync
mise run //kakoune:check
```

The check always verifies packaging staleness, metadata-only adaptation, lint
and formatting. With `kak` and `giallo-kak` on PATH it also runs a bounded
headless test in fresh temporary HOME directories: shared boundaries, per-
injection omission controls, unsaved Unicode content and removal of an embedded
region. Otherwise it prints **SKIP** and exits successfully. Optional executable
overrides: `KAKOUNE_BIN` and `GIALLO_KAK_BIN` (paths or PATH names).
The normal root check includes this task; no tools are downloaded by the probe.
In environments requiring mise's monorepo feature flag, prefix commands with
`MISE_EXPERIMENTAL=1`.

This is a small giallo-only smoke check, **not** cross-engine scope parity or a
visual/theme equivalence test. Large-buffer chunking, interactive idle timing,
and other editor/LSP integration are outside this prototype's proof.
