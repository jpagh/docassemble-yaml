# Changelog

## [Unreleased]

### Added

- [LSP] New warning `W510` reports the question-level yes/no shortcuts (`yesno`, `noyes`, `yesnomaybe`, `noyesmaybe`): prefer an explicit `fields` screen with a `datatype`. `--fix`, the quick fix, and fix-all expand a single shortcut into an explicit single-field screen whose field keeps the question text as its label (the `no label` shorthand) and gets the matching radio datatype — `yesnoradio`/`noyesradio` for the boolean variants and `yesnomaybe`/`noyesmaybe` for the three-state ones. A trailing comment on the shortcut line moves to the rewritten `fields:` line, targets that are not plain identifiers are quoted, and the fix declines when the screen already has a `fields` block or more than one shortcut, because merging would change semantics. Repeated runs make no further change and every candidate passes the fixer gate.
- [LSP] `W502` (a multi-field screen has a field with no usable label) now has a fix through `--fix`, the quick fix, and fix-all: the screen's question text becomes the label of the first offending input field, and any later offenders stay reported. The fix fills an existing blank `label` in place, rewrites a `no label: variable` shorthand as an explicit `label`/`field` pair, and writes a block label (keeping Mako `%` directives and line breaks intact) when the question text is multi-line. It declines when the question text is missing, blank, not a string, or already used as a label on the screen, when the diagnostic is not on the first offending input field, and when the edit would add a duplicate key; repeated runs make no further change, and every candidate passes the fixer gate.
- [LSP] Jinja values that only the server supplies (`jinja data`, docassemble's Jinja context) no longer render as empty text. Each substitution renders a distinct, parseable placeholder and is reported as warning `W610` at its template line, once per source site even when a loop or an included template renders it repeatedly; line attribution follows nested local includes and imported macros. Because every substitution gets its own placeholder, unknown `id` values no longer produce spurious missing-ID or duplicate-ID findings, and checks that would otherwise resolve a substituted value against the rest of the interview (events, defs, files, modules, `interview order` guards) or against a value shape (table `columns`, `data`) stay quiet when a placeholder is involved. Sandbox violations stay fatal `E208` errors and never become placeholders.
- [LSP] New warning `W609` reports a block whose `id` is already used earlier in the file. The first block keeps its ID and each later duplicate is renamed on fix with a deterministic `id 2`, `id 3`, … suffix that skips author-written IDs and every suffix already planned; ids are compared case-sensitively and empty or non-string ids stay with the existing `W608`/type findings. `--fix`, the quick fix, and fix-all apply it through the candidate gate, the line's key spelling and trailing comment are preserved, a repeated run makes no further change, and a missing `id` added in the same run receives a different ID so one run leaves every block unique.
- [LSP] Jinja rendering in `# use jinja` files is now sandboxed and bounded. Template code runs in a sandboxed environment, source and rendered output have size caps, and each render runs in a child process with a wall-clock timeout plus CPU and address-space rlimits (the address-space limit is skipped on macOS, where it is not enforced). A sandbox violation reports error `E208`, an oversized source reports `E211`, oversized output `E212`, a render over the wall timeout `E209`, and a render stopped at another resource limit `E210`; a render that exceeds a limit is reported instead of continuing.
- [LSP] New warning `W608` reports question blocks that have no `id`. `--fix`, the quick fix, and fix-all add a unique ID generated from the question text: letters, digits, and spaces are lowercased, apostrophes are dropped in place, other punctuation separates words, accented letters survive, and Mako text is kept literal. Generated IDs avoid every author-written ID in the file and every earlier generated ID, an existing empty `id:` key is filled in place, and repeated runs make no further change.
- [LSP] `docassemble-lsp` is published to PyPI; install the language server and CLI with `uv tool install docassemble-lsp` (or `pipx install docassemble-lsp`).
- [Fresh] The Docassemble pack is now a bundle with a detection plugin: `.yml` files under a package's `data/questions/` directory open as Docassemble (grammar + `docassemble-lsp`) with no configuration, while other YAML files stay YAML. Interviews kept elsewhere still use `languages.docassemble.filenames` in `~/.config/fresh/config.json`.

### Changed

- [LSP] The missing-ID rule (`W608`) and its fixer now share one predicate, `has_usable_id` in `core/question_ids.py`, for whether a block already declares an ID, so the reported blocks and the planned IDs cannot drift apart. Behaviour is unchanged for non-empty string, non-string, empty, and blank IDs.
- Relicensed the project from Apache-2.0 to MIT: the repository, the `docassemble-lsp` package, the VS Code extension, and the Fresh pack are now MIT. Releases already published under Apache-2.0 remain Apache-2.0.
- [CLI/LSP] `--fix` and the fix-all code action now re-check every candidate before writing: a fix is applied only when the result still parses, adds no finding of any code, and removes the finding it was made for. Rejected fixes are reported on stderr (CLI) or the log (LSP) and leave the file unchanged, and Jinja-rendered files are excluded from automatic rewriting.
- [CLI] `check` now builds a workspace index once per run and passes it through diagnostics. As a result the CLI also reports the existing cross-document checks (`W601`/`W602`, file references) that previously ran only in the language server.

### Fixed

- [LSP] Duplicate-block-ID findings (`W609`) in `# use jinja` files now name the first id's line in the original template instead of the rendered body's line. The message is mapped through the same rendered-to-source line map as the diagnostic anchor, so a shifted render no longer makes it quote a document separator or another unrelated line; plain YAML messages are unchanged.
- [LSP] The missing-ID rule (`W608`) no longer reports a question block whose `question` is not a usable string (for example a YAML list): there is no text to normalize, so the fixer could never offer an ID and the warning could never be satisfied. The string type check (`E103`) remains the only finding there, and the rule and the fixer now share one `has_usable_question_text` predicate in `core/question_ids.py`. Blocks with usable question text still report `W608` and still receive the generated-ID fix.
- [LSP] The multi-field label check (`W502`) now reports missing, blank, and `no label` field labels: internal ruamel position keys are no longer mistaken for field labels, and code-only and presentation (`note`/`html`/`raw html`) items are excluded.
- [LSP] Unknown-key findings (`E301`) now anchor to the line of the first offending key instead of the document start, in both single- and multi-document files, and in `# use jinja` templates where the rendered line is mapped back to the key's original source line. The finding still reports every unknown key of the document in one diagnostic; keys without position data (non-string keys, programmatic documents) keep the document-start fallback.
- [LSP] Unresolved `{% include %}` templates in `# use jinja` files no longer abort validation with `E202`. Each include site reports warning `W607` at its original template line, the YAML documents containing it are skipped, and the remaining documents are still validated with findings mapped back to their source lines. `ignore missing` and candidate lists keep their normal rendering behaviour, and one include site warns once however often it renders.
- [LSP] `W603` now detects field references with parsed Python reads instead of a line regex. A conditional field mentioned only in a Python comment or string literal no longer warns, and a bare assignment (`b = 1`) no longer warns, while genuine reads (bare names, attributes, subscripts) and augmented assignments (`b += 1`) still do. Unparsable code blocks are skipped; `E122` still reports the syntax error.
- [LSP] Accepting a key completion after replacing an existing key word in place no longer duplicates the separator. Selecting `hint` and typing `under ` used to produce `under text: : ...`; the completion's text edit now replaces the leftover `: ` as well.
- [LSP] `W601` no longer reports URL-style action buttons as undefined events. `action` values beginning with `/` or `?` (documented docassemble hyperlink actions, e.g. `/start/case_information`) are treated as links, not event references.
- [LSP] `W606` no longer reports docassemble-provided names or declared paths it could not see: implicit list indices (`i`–`n`), `generic object:` `x`, `generic list object:` `x`/`i`, `objects:` keys and top-level `code:` globals from anywhere in the interview, singular `field:` shorthand, attribute bases under subscripts, and reads that extend a declared path at a `.` boundary (e.g. `uploaded_signature[0].mimetype`).
- [CLI] `check` applies the same interview-wide `objects:`/`code:` definitions to `W606` as the language server.
- [LSP] Narrowed `E933` (`list collect` field label Mako check) to only flag Mako that references a same-screen variable or list iterator (`i`/`j`/`k`/`l`/`m`/`n`/`x`). For example, a label containing only an off-screen variable (e.g. `${ some_var }`) with `list collect: True` no longer produces a false positive.

## [26.8.1] - 2026-08-10

### Fixed

- [LSP] Fixed a crash that could kill the language server when resolving a Python module (e.g. go-to-definition on an import). Module sources are now located directly from `sys.path` without importing them.

## [26.8.0] - 2026-08-08

### Added

- [LSP] Add `|` value completion for string-typed keys; remove `key (block)` property completions.
- [LSP] Project configuration can now live in a dedicated file in addition to `pyproject.toml` — `docassemble-lsp.toml`, `.docassemble-lsp.toml`, or `.config/docassemble-lsp.toml`, found by walking up from the workspace root. Works for convention settings, ignored codes, `yaml_path`, and CLI args.
- [LSP] Config is now resolved per document: each file uses the config of its own project, so in a multi-project workspace every project's files follow their own `conventions`/`ignore-codes` settings instead of sharing one global config. `--conventions`/`--ignore-codes` passed to the `lsp` command still apply to every document.

### Changed

- [LSP] The Python formatter now honors `--indent` for code blocks whose indentation is not a multiple of 4 (e.g. `# fmt: off` regions): blocks are rebased against their smallest common indent instead of being left untouched.
- [LSP] DAObject subclass detection now follows import re-exports: a class re-exported via `from .internal import Thing as PublicThing` is recognized as a DAObject subclass, so completions and symbol resolution pick up the new name.
- [CLI] Removed the "REAL ERROR:" output prefix and the `experimental` code concept: all diagnostic codes are now reported uniformly.
- [VSCODE] The bundle script now parses `lsp/pyproject.toml` with a real TOML parser and preserves Python-version markers, so `tomli` is only bundled for Python < 3.11 (smaller `bundled/libs/`).
- [VSCODE] The bundled-server dependency install timeout is now configurable via `BUNDLE_SERVER_TIMEOUT` (default 5 minutes, previously hard-coded at 2).

### Fixed

- [LSP] Go-to-definition on aliased Python imports (`import X as Y`, `from . import X as Y`) now jumps to the import statement. The resolved module file is also offered as a secondary target for `import X as Y` aliases. Non-aliased imports continue to resolve directly to the module or symbol definition.
- [LSP] The document-link cache key is now deterministic (SHA-1 of source) instead of process-salted `hash()`, removing a cross-process serialization trap.
- [LSP] The workspace-index overlay cache now invalidates on a content-derived stamp (built-in `hash()`) of the open documents, and `_WorkspaceIndexStore` mutations are guarded by a lock.
- [LSP] Python module index caching now uses nanosecond-resolution mtimes, so rapid back-to-back rewrites of the same file reliably invalidate the cache.
- [LSP] Autocomplete now replaces your typed text as you'd expect for multi-word options. Typing `disable i` and accepting `disable if` gives you `disable if:` instead of `disable disable if:`. This applies everywhere in the YAML — keys, values, and file/module names.
- [VSCODE] The language server now starts in your workspace folder, so conventions enabled in the project's configuration actually take effect. Configuration changes (e.g. editing `docassemble-lsp.toml` or the `[tool.docassemble-lsp]` pyproject section) are picked up on save without a restart.
- [LSP] Autocomplete no longer rewrites a typed block-scalar marker (`|-`, `|+`, `|2`) into a plain `|` — the block-scalar completion is only offered for an empty value or a bare `|`.
- [LSP] Completion on a blank line inside a `code:`/`validation code:`/Mako block no longer inherits the previous line's text as the typed prefix.
- [VSCODE] Changes to `.config/docassemble-lsp.toml` are now watched and picked up on save like the other config file locations.
- [VSCODE] Document-link underlines are restored for unsaved (`untitled`) docassemble documents.

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
