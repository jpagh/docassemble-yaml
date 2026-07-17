# docassemble-lsp

See `lsp/docs/` for architecture, feature patterns, and subagent handoffs.

## Commands

- **Lint/type/test** — `mise run check`
- **Validate YAML** — `uv run docassemble-lsp check path/to/file.yml`

## Key pointers

- **Entry points**: `cli.py:main` (CLI) and `lsp/server.py` (LSP)
- **Data**: `WorkspaceIndex` owns YAML/Python sources — use document overlays, not filesystem
- **No crawls**: don't add workspace scans; index already has data
- **macOS**: prefix `docassemble.base.*` imports with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
- **Parser**: cross-check `docassemble.base.parse` before changing parser-backed rules
- **Read** `lsp/docs/SUBAGENT_GUIDE.md` before making changes
- **Versioning**: CalVer (`YY.MM.patch`), `mise run bump` updates `lsp/` + `vscode/` + tags
