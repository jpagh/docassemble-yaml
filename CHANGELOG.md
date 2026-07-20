# Changelog

## [Unreleased]

### Added

- [LSP] Add `|` value completion for string-typed keys; remove `key (block)` property completions.

### Fixed

- [LSP] Go-to-definition on aliased Python imports (`import X as Y`, `from . import X as Y`) now jumps to the import statement. The resolved module file is also offered as a secondary target for `import X as Y` aliases. Non-aliased imports continue to resolve directly to the module or symbol definition.

## [26.7.0] - 2026-07-09

### Added

- [VSCODE] `docassemble-lsp.showNotifications` setting now has integration tests that verify warnings are shown or suppressed per the configured level (`off`/`onError`/`onWarning`/`always`). The setting documentation in `vscode/README.md` has been expanded to describe each value.

### Removed

- [CLI] The legacy `docassemble_lsp.core.validation:main()` entry point and its `process_file` helper have been removed. Use `docassemble-lsp` (the new `cli.py`) instead.

### Fixed

- [LSP] Fixed autocomplete for the `decoration` field.
- [LSP] Completion parent-key resolution on multi-line list items and list-item mapping siblings now resolves correctly (e.g., `c: 2` inside `- b: 1` no longer inherits `b` as its parent). Fixes completions inside list-item mappings.
- [LSP] Package root detection now works from all `WorkspaceIndex` constructors, not only `build_workspace_index`. Module resolution is now correct when the workspace is built via `from_yaml_roots` or `from_current_document`.
- [LSP] Module index cache is now invalidated for sibling modules when a `.py` file is saved (previously only the saved file was evicted). Saving a package's `__init__.py` correctly evicts cached modules in that directory.
- [LSP] Completion label for `.using()` now includes the closing parenthesis (was `.using(`).
- [CLI] `--conventions` and `--ignore-codes` config args are no longer passed to the `format` command, which does not accept them.
- [LSP] Works with docassemble 1.10.x on systems that lack native libraries like `libcairo`. The language server no longer crashes when the installed docassemble version imports optional system-dependent packages (e.g. `cairosvg`) during module resolution.

## [26.6.3] - 2026-06-23

### Added

- [LSP] Module completions in `modules:` blocks now emit a `TextEdit` with exact replacement range, bypassing VS Code's word-boundary heuristics for dotted names. Workspace modules always receive a dotted prefix (`.mymodule`) and explicit `textEdit` range. Vendored docassemble modules (`docassemble.base.*`) are excluded from `modules:` completions.
- [LSP] **C103** generalized convention: `datatype: area`, `datatype: hidden`, `datatype: radio`, `datatype: dropdown`, `datatype: pulldown`, `datatype: combobox`, `datatype: datalist`, and `datatype: ajax` now all suggest using `input type: <value>` instead (these are input-type concerns that the parser remaps at parse time). Previously only `area` was covered (C105).
- [LSP] Completions for `.using()` keyword arguments in `objects:` block values: `auto_gather=`, `there_are_any=`, `there_is_another=`, `complete_attribute=`, `object_type=`, and others now offered when typing inside a `.using()` call. When `object_type=` is detected, DAObject subclass names are suggested as values. Typing a class name followed by `.` suggests `.using(`.
- [VSCODE] Docassemble YAML files now default `editor.suggest.matchOnWordStartOnly` to `false`, enabling VS Code's substring matching for completion filtering. This makes partial-word searches like `phone` find `microphone`.
- [VSCODE] Integration tests for module completions, include completions, and on-type formatting, gated behind `DOCASSEMBLE_LSP_ENABLE_REAL_TEST=1`.

### Changed

- **C103** now covers all input-type-as-datatype values; **C105** is reserved/available for future use. Users with `C105` in their config should migrate to `C103`.
- [LSP] Removed `filterText` from completion items. With `editor.suggest.matchOnWordStartOnly` now `false`, VS Code's fuzzy matching on the `label` alone suffices for compound property names and module completions.
- [VSCODE] Output channel changed from `OutputChannel` to `LogOutputChannel` for structured logging.
- [VSCODE] `vscode-languageclient` upgraded from `^9.0.1` to `^10.0.0`.

### Fixed

- [LSP] Fix All code action now works correctly (was broken in certain client states).
- [VSCODE] Fix All code action now appears in VSCode.

## [26.6.2] - 2026-06-16

### Added

- [LSP] `include:` and `modules:` blocks now get `- ` auto-continuation on Enter (same behavior as `objects:` blocks).
- [LSP] `DAEmpty` now appears as a completion candidate in `objects:` block values (it is a standalone class in `docassemble.base.util` that does not inherit from `DAObject`).
- [LSP] Relative module name completions in `modules:` blocks: typing `.func` now suggests `.functions` (strips leading dot for matching, prepends it in the label). Workspace modules always get the `.` prefix. Vendored modules only appear when the user types an absolute prefix.

### Fixed

- [LSP] `action buttons:` list items now get property-key completions when the cursor is at property-indent level inside an existing item (not just at the `- ` line). Same fix applied to `need:` and `terms:`/`auto terms:` items.
- [LSP] Pressing Enter after a `- key: value` line in `action buttons:` now indents to property level (matching the existing `fields:` behavior).
- [LSP] Pressing Enter after a bare `- ` or `- |` line in `action buttons:`, `fields:`, `need:`, or other complex-list blocks now indents to property level instead of staying at the `- ` indent.
- [LSP] `modules:` list items with a leading dot (`.func`) no longer show zero completions. The completion guard regex and list-item detection regex now include `.` in their character classes, and `filter_text` is set to the bare stem so client-side word-boundary filtering works correctly.
- [LSP] **E446** (action button arguments must be plain items): false positive when arguments contain plain values — internal metadata keys (`__key_lines__`/`__value_lines__`) injected by the line-tracking helper were being treated as dict values and incorrectly flagged. The check now skips internal metadata keys.
- [LSP] **E414** (label requires field): false positive for shorthand labels `Value`, `Code`, and `HTML` — the reserved-key filter used case-insensitive comparison (`key.lower()`), which incorrectly excluded these keys because their lowercase forms (`value`, `code`, `html`) are in the known-field-keys set. Changed to case-sensitive comparison, matching the actual docassemble parser behavior.
- [LSP] **E901** (attachment item must be a dictionary): false positive when an attachment value is a string (e.g., `${ fruit_table }` — a Mako variable reference). The docassemble parser accepts string attachment values as runtime content. `AttachmentBlockDirective` now accepts strings.
- [LSP] **E309 → C106** (nested visibility logic): downgraded from error to convention. Three levels of `show if`/`hide if` nesting is valid YAML that works at runtime; the threshold of 2 is a style opinion, not an error or even a warning. Hidden by default; opt in with `--conventions ALL` or `--conventions C106`.
- [LSP] New test `test_example_corpus_has_no_error_diagnostics` validates all 966 example files in the corpus produce no error-severity diagnostics.
- [LSP] **W601** (cross-doc undefined event): no longer reported when the event name contains a Mako expression (`${...}`), since Mako expressions are dynamically resolved at runtime.
- [LSP] **W601** hover tooltip for Mako expression event names now says "dynamic Mako expression, cannot be statically resolved" instead of the misleading "not defined in the workspace".
- [LSP] The startup log message "Log level set to ..." is now emitted at DEBUG level instead of the configured log level, so it only appears when debugging.

## [26.6.1] - 2026-06-15

### Fixed

- [LSP] Multi-package workspace: each YAML file now resolves template references against its own package's `data/templates/` directory.

## [1.0.0] - 2026-06-10

### Added

- [VSCODE] Bundled `docassemble-lsp` server ships inside the VSIX — no separate install needed. Dependencies are installed at build time (pure Python only, no compiled extensions).
- [VSCODE] Python extension integration: server uses the Python extension's active environment for interpreter resolution when running the bundled server or `fromEnvironment` mode.
- [VSCODE] `docassemble-lsp.importStrategy` setting: `"useBundled"` (default) runs the shipped server via the Python interpreter; `"fromEnvironment"` runs `python -m docassemble_lsp lsp` or a custom command string.
- [VSCODE] `docassemble-lsp.interpreter` setting: override the Python interpreter for bundled or fromEnvironment modes.
- [VSCODE] `docassemble-lsp.command` setting: full shell command for `fromEnvironment` mode (supports `uv run`, direct paths, etc.).
- [VSCODE] `docassemble-lsp.showNotifications` setting: control when server notifications are shown.
- [VSCODE] `DOCASSEMBLE_LSP_LOG_LEVEL` environment variable: set the server's log level via `docassemble-lsp.env` (levels: DEBUG, INFO, WARNING, ERROR, CRITICAL).
- [VSCODE] Commands to restart the language server and show the language server output.
- [VSCODE] A status bar indicator and setup-help command for optional language server discovery, troubleshooting, and restarting.
- [VSCODE] Python syntax highlighting for `show if` values in both block-scalar (`show if: |`) and inline (`show if: <expr>`) forms.

### Changed

- [VSCODE] Raised the minimum supported VS Code version for the new extension runtime.
- [VSCODE] Docassemble documents now default to this extension as their formatter and enable `editor.formatOnType` unless the user overrides those settings.

## [0.3.11] - 2026-03-24

### Fixed

- [VSCODE] YAML syntax highlighting now properly resets in each block (`---`)

## [0.3.10] - 2025-11-24

### Added

- [VSCODE] JavaScript syntax highlighting for `script` blocks (without `<script>` tags). (#7)
- [VSCODE] Python syntax highlighting for `on change` blocks. (#6)

### Fixed

- [VSCODE] `.using()` pattern now closes properly when commented out. (#5)
- [VSCODE] Resolved VS Code conflict warning: "Overwriting grammar scope name to file mapping for scope source.yaml".

## [0.3.9] - 2025-02-27

- [VSCODE] Improved `code` block parsing.

## [0.3.8] - 2025-02-26

- [VSCODE] Added Python highlighting to all blocks' `need: ` expression and list items.

## [0.3.7] - 2025-02-26

- [VSCODE] Fixed an issue where Mako wasn't correctly applied in block-scalars (`|`), particularly on the first line (improves 0.3.5).
- [VSCODE] Fixed colons (`:`) being incorrectly highlighted as a YAML key and breaking subsequent highlighting in block-scalars (`|`). - [VSCODE] Removed hash (`#`) as a comment marker in Mako so that Markdown headers won't be commented out anymore.
- [VSCODE] Cleaned up and expanded Python highlighting to more `code` blocks like `attachment code` and `verification code`.
- [VSCODE] Updated YAML highlighting of values to be more Pythonic, so the only boolean values are `True` and `False` and the only null value is `None` (removed `true|TRUE`, `false|FALSE`, and `null|Null|NULL`).

## [0.3.6] - 2025-02-22

- [VSCODE] Added syntax highlighting to `validation code` blocks.

## [0.3.5] - 2025-02-22

- [VSCODE] Fixed Mako and HTML highlighting on the first line of multiline YAML (`|`). Fixed some inconsistencies with the `.using()` method's highlighting.

## [0.3.4] - 2025-02-19

- [VSCODE] Added Python highlighting to all blocks' `if: ` expression and (imperfectly) to `objects` blocks' `using()` method.

## [0.3.3] - 2025-02-18

- [VSCODE] Updated the demo image to show more variety and updated this CHANGELOG since I missed it before.

## [0.3.2] - 2025-02-18

- [VSCODE] Fixed an issue with node modules being included in the extension package. Cleaned up a lot of other dependencies and garbage.

## [0.3.1] - 2025-02-18

- [VSCODE] Improved syntax highlighting: Python `code` blocks now terminate on sub-keys (fixes 0.2.0's outstanding issue).
- [VSCODE] HTML terminates more consistently overall.
- [VSCODE] Mako expressions as keys in YAML key-pairs properly inherit the highlighting of the YAML key and retain otherwise proper Mako highlighting.

## [0.3.0] - 2023-04-16

- [VSCODE] Changed YAML highlighting of boolean values to match the interpretation of Docassemble. This removed all variations of `Yes|No|On|Off` from being highlighted as boolean values and leaves only `true|True|TRUE|false|False|FALSE`.

## [0.2.0] - 2023-02-27

- [VSCODE] Missed some updates from version 0.0.1 through 0.0.7, and then accidentally updated version to 0.2.0, and then missed including the changelog to that version as well. So this is being backfilled.
- [VSCODE] This release was prompted by, and includes, a partial fix for `code` blocks not releasing python syntax highlighting back to yaml, particularly in `question`->`fields`. Sub-keys still aren't released properly (e.g., `default`), so the workaround is to make the `code` block the last thing in the key. Subsequent keys are now properly highlighted.

## [0.0.1] - 2023-02-01

### Features

- [VSCODE] initial commit based on [Inline YAML Syntax Highlighting](https://github.com/monotykamary/inline-yaml)
