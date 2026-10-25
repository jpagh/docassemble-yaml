# Docassemble in Kakoune

A sourceable filetype plugin using [giallo.kak](https://github.com/Yukaii/giallo.kak),
not a new highlighter. Tested with **Kakoune 2026.05.21** and
**giallo-kak 0.4.0 (66d0731)** / giallo 0.5.2 on macOS arm64.
See [the investigation](../docs/KAKOUNE.md) for evidence and limitations.
Optional LSP wiring uses **kakoune-lsp 22.0.0** (binary name `kak-lsp`).
Highlighting and LSP are independently sourceable; neither requires the other.

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

## Optional diagnostics, completion and hover

Install [kakoune-lsp v22.0.0](https://github.com/kakoune-lsp/kakoune-lsp/releases/tag/v22.0.0)
and put `kak-lsp` on PATH. This example uses v22's **buffer `lsp_servers` TOML**,
not the legacy `kak-lsp.toml` configuration (`roots` and `root_globs` are not
interchangeable). Install the server on PATH, for example:

```sh
uv tool install docassemble-lsp
kak-lsp --version                 # 22.0.0
docassemble-lsp --help
cp kakoune/rc/docassemble-lsp.kak "$config_home/kak/docassemble-lsp.kak"
```

After your highlighting/filetype setup, add the following to kakrc **before
opening interviews**. Load upstream only once and call `lsp-enable` only once
(omit those lines if already present):

```kak
evaluate-commands %sh{ kak-lsp }
# Prevent upstream's default YAML server from attaching before manual activation.
remove-hooks global lsp-filetype-yaml
source %sh{ printf '%s/kak/docassemble-lsp.kak' "${XDG_CONFIG_HOME:-$HOME/.config}" }
lsp-enable
```

The wiring replaces (does not append to) `lsp_servers` for `filetype=docassemble`
and sets `lsp_language_id=docassemble`. Automatically detected interviews and
`:docassemble-enable` buffers both use `docassemble-lsp lsp` over stdio.
No keybindings are installed. Upstream supplies inline diagnostics, insert-idle
completion and `:lsp-hover` (place the cursor on e.g. `question`). Unsaved edits
are sent on upstream's idle hooks; `:lsp-did-change` explicitly synchronizes.
The filename need not have been saved after edits; for a new interview give it
a path with `:edit /absolute/path/new.yml` then `:docassemble-enable`.

**Do not attach a generic YAML server to the same buffer.** Removing the default
`lsp-filetype-yaml` hook above opts ordinary YAML out of LSP too, intentionally
avoiding a server starting while an outside-package interview is still YAML.
Remove or narrow any custom `filetype=yaml` / `filetype=.*` hooks that set
`lsp_servers` or reset `lsp_language_id`; source this wiring after other server
configuration. Inspect `:echo %opt{lsp_servers}` and
`:echo %opt{lsp_language_id}` in the interview: there must be only a
`[docassemble]` table and language `docassemble`. Do not combine this setup with
a legacy generic YAML association. If YAML already attached, restart the
session after correcting the hooks (changing filetype cannot undo a previous
server launch).

### Executable and virtualenv overrides

The executable option is a single PATH name or absolute path, **not a shell
command**; the plugin always supplies `args = ["lsp"]`. A global override applies
to all interviews; a buffer override applies only there. For example, after
sourcing the wiring:

```kak
set-option global docassemble_lsp_command '/absolute/path/to/docassemble-lsp'
# Development checkout: first run `cd /absolute/path/to/docassemble-yaml/lsp && uv sync`.
set-option global docassemble_lsp_command '/absolute/path/to/docassemble-yaml/lsp/.venv/bin/docassemble-lsp'
# Or an interview package's environment, with docassemble-lsp installed:
set-option buffer docassemble_lsp_command '/absolute/path/to/package/.venv/bin/docassemble-lsp'
docassemble-lsp-enable
```

Use absolute paths (no literal `~`); the editor's environment must include
needed runtime libraries too. The executable must be runnable in that environment.
A missing/non-executable command leaves `lsp_servers` empty and writes an
**actionable message in `*debug*`** explaining installation/override and retry.
It does not abort filetype activation or highlighting. Fix the option then run
`:docassemble-lsp-enable`. If an executable exists but fails at runtime, inspect
`*debug*` for upstream's launch/stderr error and use `:lsp-restart` after fixing it.

### Roots, disabling and independent operation

The tested table is:

```toml
[docassemble]
command = "docassemble-lsp"
args = ["lsp"]
root_globs = ["docassemble", "pyproject.toml", "setup.py", ".git"]
single_instance = false
```

In v22 **marker order takes precedence**: for each glob, kak-lsp searches from
the file's directory upwards and chooses its nearest matching ancestor; only
if that marker is absent at every ancestor does it try the next glob. This is
not nearest-among-all-markers. A `docassemble/` namespace directory selects the
usual package root; `pyproject.toml` supports modern/src-layout projects;
`setup.py` supports older packages; `.git` is the final project fallback.
With no marker it uses the file's directory (an interview outside any project).
A namespace directory at an outer ancestor intentionally wins over a closer
manifest; nested projects needing another rule should override the buffer's
`lsp_servers` table with an explicit `root = "/absolute/package"` instead of
`root_globs`. Upstream `KAK_LSP_FORCE_PROJECT_ROOT` and
`KAK_LSP_PROJECT_ROOT_DOCASSEMBLE*` environment variables also override detection;
unset these when reproducing. `single_instance=false` keeps package indexes
separate rather than sharing the first root across packages.

`:docassemble-lsp-disable` clears this buffer's association without changing
filetype/highlighting. `:docassemble-lsp-enable` retries/re-enables. Leaving the
Docassemble filetype clears its association. To unload, disable active buffers,
then `remove-hooks global docassemble-lsp`; leave upstream LSP available to other
languages, or use upstream `:lsp-disable` to stop it entirely.

For **LSP without giallo**, source upstream kak-lsp and this LSP file alone, then
set `filetype=docassemble`; optionally source `docassemble.kak` for automatic
filetype detection and manual commands (its missing-giallo failure is caught).
For **highlighting without LSP**, omit the LSP file entirely. Neither component
sources the other.

## Verified support matrix

Every row below is pinned to **Kakoune 2026.05.21, kakoune-lsp 22.0.0,
docassemble-lsp 26.10.0**, on macOS arm64; highlighting rows also use
**giallo-kak 0.4.0 (66d0731), giallo 0.5.2**. Other versions/platforms are
not certified. Evidence is in `tests/test_docassemble_lsp.py`,
`scripts/check_highlighting.py` and the [investigation](../docs/KAKOUNE.md#cross-file-workflows-and-support-matrix-25).
The real `:lsp-capabilities` listing is captured and asserted, not inferred
from the server's feature list.

### Verified functionality

| Functionality | What the automated check proves |
|---|---|
| Filetype and giallo | Automatic/explicit activation, YAML and embedded-language ranges, unsaved Unicode and edit convergence. |
| Diagnostics, completion, hover | Saved/unsaved diagnostic faces, completion JSON containing `question`, hover documentation. No visual menu/popup claim. |
| Cross-file definitions | `:lsp-definition` on `workflow_reset` in `main.yml` reaches `x_events.yml:16`; `case_title` reaches `workflow.py:1`. Both real response targets **and opened buffers** are asserted. |
| Cross-file references | `:lsp-references` at `x_events.yml:16` returns `main.yml` uses, including its action button. Real response locations are asserted; interactive result selection is not. |
| Package roots and spaces | A temporary copy of the committed demo package under `demo package with spaces` initializes at the package root, not `data/questions`. Executable paths with spaces/apostrophes are also covered. |
| Formatting | `:lsp-formatting-sync` applies a real server edit to an unsaved buffer (`total=1+2` becomes `total = 1 + 2`); disk bytes stay unchanged. See the final-newline limitation below. |
| Quick fixes | `:lsp-code-actions-sync quickfix` at a missing field label returns one E415 action and applies its `WorkspaceEdit`; exact resulting buffer bytes are asserted. Multi-action interactive menu selection is not tested. |
| Shutdown | After `:lsp-exit`, the actual kak-lsp, stdio recorder and server PIDs disappear. Kakoune then exits with status 0 and rejects further connections. v22 sends `exit` directly, not a `shutdown` request/response handshake. |
| Optional semantic-token request | With both highlighters enabled, `:lsp-semantic-tokens` returns empty data/legend and no semantic face ranges. giallo ranges remain identical and a JSON UI draw still renders Python `return` cyan in the probe theme. This is non-interference, **not overlap precedence**. |

### Client capabilities kak-lsp does not provide

| Capability | Tested boundary |
|---|---|
| Dynamic multi-root workspace folders | The actual initialize request has `workspace.workspaceFolders=false`. Keep separate package roots/server instances (`single_instance=false`), rather than claiming VS Code-style workspace-folder support. |
| Automatic on-type formatting | No on-type formatting command/hook or capability-list entry in v22. Use explicit whole-document formatting. Its initialize payload contains a generic `onTypeFormatting` structure; that alone does not prove an implemented workflow. |
| Clickable LSP document links | No document-link command or capability-list entry in v22, despite a generic `documentLink` initialize structure. Use definition navigation for supported paths/symbols instead; clickable link UI is not claimed. |

### Known limitations

| Limitation | Consequence / workaround |
|---|---|
| Formatting final newline | The server's whole-document edit ends **before** the original final LF but its replacement includes an LF. The verified client application therefore leaves an extra blank line for the tested buffer. The test asserts this exact result; byte-for-byte canonical formatter output/idempotence is not claimed. Remove the blank line manually if needed. No server patch is bundled here. |
| Semantic-token precedence unestablished | This server version deliberately emits **no** semantic tokens (empty legend and data). There is no overlapping semantic face to compare against `buffer/giallo`; future nonempty tokens require a new overlap test. This wiring installs no semantic-token hook: leave requests off by default with giallo. Explicit requests are optional and currently have no visible effect. |
| Unexercised client UI | Completion/hover appearance, choosing among multiple code actions/references, interactive idle latency and large-buffer behaviour remain manual. A JSON UI window verifies rendered keyword faces, not terminal pixel appearance. |
| Server range formatting unavailable | v22 has `lsp-range-formatting`, but this server does not advertise range formatting, so it is absent from the captured capability listing. Use whole-document formatting. |
| giallo updates / root priority | Initial FIFO handshakes can overlap and macOS rate-limit timing can delay refreshes. Root markers are priority-ordered, not nearest-among-all. See troubleshooting and the root rule above. |

### Try the committed cross-file package

No external package checkout is needed. From the repository root, open
`lsp/tests/fixtures/demo_package/docassemble/demo/data/questions/main.yml`
after the setup above. At line 16, put the cursor on `workflow_reset` and run
`:lsp-definition`; at line 11, try `case_title`. At `x_events.yml:16`,
`:lsp-references` finds the uses in `main.yml`. `:lsp-capabilities` shows the
commands available from this server. Copy the package first before trying
formatting or edits; the fixture of record is read-only for checks.

### LSP troubleshooting

- **No highlighting:** check the grammar path, upstream init order and
  `:giallo-debug`; see [themes and troubleshooting](#themes-and-troubleshooting).
- **No diagnostics:** confirm `filetype=docassemble`,
  `lsp_language_id=docassemble`, a single `[docassemble]` in `lsp_servers`, and
  that `lsp-enable` was called. Run `:lsp-did-open` / `:lsp-did-change`, then
  inspect `*debug*`. Remove competing generic YAML hooks and restart if one
  already launched a different server.
- **Wrong root / missing cross-file results:** check the root-marker priority
  [above](#roots-disabling-and-independent-operation), unset
  `KAK_LSP_FORCE_PROJECT_ROOT` / `KAK_LSP_PROJECT_ROOT_DOCASSEMBLE*`, or set
  explicit `root` in the buffer's server table. Open the demo package, not just
  an isolated copied interview. Restart with `:lsp-restart` after fixing root
  configuration.
- **Missing server:** install `docassemble-lsp` on the editor's PATH or use an
  absolute executable override, then `:docassemble-lsp-enable`. `*debug*` gives
  the retry instructions; highlighting remains independent.
- **Semantic-token choice:** do not add automatic `lsp-semantic-tokens` hooks
  with giallo. On the pinned server, explicit requests produce no ranges; that
  is expected, not a broken giallo setup. For custom hooks/server versions,
  remove the hook and clear stale ranges with
  `set-option buffer lsp_semantic_tokens_ranges` before comparing colours.

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
`//kakoune:lsp:test` additionally tests real kak-lsp/server stdio, package-root
initialization, saved/unsaved diagnostics and completion/hover responses,
cross-file YAML/Python navigation, references, formatting and quick-fix edits,
space-containing workspaces, PID-checked shutdown and optional semantic-token /
giallo non-interference. The last uses a real off-screen JSON UI window; its
idle hooks are disabled and requests are explicit for deterministic checks. It
loudly skips when tools are absent. Optional overrides: `KAK_LSP_BIN` /
`DOCASSEMBLE_LSP_BIN`; with giallo present it also proves highlighting survives a
missing server. The root check includes these fast tasks; no tools are downloaded
by probes. Headless tests assert diagnostic ranges and JSON responses, not visual
completion menus/hover popups; see the evidence document for that boundary.

The clean-HOME installation route and explicit activation were also exercised
with the normal giallo theme. Visual equivalence, interactive idle timing and
large-buffer behaviour remain manual, not cross-engine parity guarantees.
