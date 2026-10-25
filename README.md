# docassemble-yaml

Monorepo for the docassemble-lsp language server, its VS Code extension, and
optional support for the Fresh and Kakoune terminal editors.

- **`lsp/`** — Python language server (CalVer versioned; published to PyPI as
  `docassemble-lsp`)
- **`vscode/`** — VS Code extension (same version as lsp/)
- **`fresh/`** — Fresh language pack (syntax highlighting + LSP wiring); see
  [`docs/FRESH.md`](docs/FRESH.md) for the investigation and setup
- **`kakoune/`** — manually activated giallo.kak highlighting example; see
  [`docs/KAKOUNE.md`](docs/KAKOUNE.md) for evidence and limitations

## Install

The language server and CLI are published to PyPI as `docassemble-lsp`:

```bash
uv tool install docassemble-lsp
# or: pipx install docassemble-lsp
```

Editor setup is covered in [`lsp/README.md`](lsp/README.md),
[`vscode/README.md`](vscode/README.md), [`fresh/README.md`](fresh/README.md), and
[`kakoune/README.md`](kakoune/README.md).

## Required tools

| Tool | Used by | Purpose |
|------|---------|---------|
| `mise` | root, lsp, vscode | Tool/task runner — all commands via `mise run` |
| `uv` | lsp | Python package manager, runs scripts and tests |
| `tombi` | root, lsp, vscode | TOML formatter (`mise run //lsp:format`/`mise run //vscode:format` includes TOML; `tombi format` standalone) |
| `ruff` | lsp | Python linter and formatter (`mise run //lsp:lint`/`mise run //lsp:format`) |
| `pyrefly` | lsp | Python type checker (`mise run //lsp:type`) |
| `pytest` | lsp | Python test runner (`mise run //lsp:test`) |
| `bump-my-version` | root | Unified version bump (`mise run bump`) |
| `gh` | root | Creates the GitHub Release (`mise run deploy` / `mise run release:github`) |
| `aube` | vscode | Node package manager (replaces npm); mise-managed |
| `node` | vscode | Node runtime (aube auto-switches) |
| `typescript` / `esbuild` | vscode | TS compile + bundler (mise-managed) |
| `oxlint` / `oxfmt` | vscode | TS/JS linter and formatter (`mise run //vscode:lint`/`mise run //vscode:format`) |

## Quick start

```bash
mise run check   # lint, type, and test the whole monorepo
mise run bump    # bump version (patch)
mise run deploy  # full release (see RELEASE.md)
```

## Development

### Running the LSP from a dev checkout

The `lsp:lsp` mise task runs the language server from the working tree against `lsp/.venv`.

For VS Code integration, set `docassemble-lsp.command` to point at the task from the monorepo root (the `--cd` flag works from any cwd):

```json
"docassemble-lsp.command": "mise run --cd /path/to/docassemble-yaml //lsp:lsp"
```

The `//lsp:lsp` monorepo-task reference resolves to the `lsp` task in `lsp/.mise.toml`.

See `AGENTS.md` for agent guidance, `lsp/README.md` and `vscode/README.md` for per-project documentation.

## License

MIT — see [`LICENSE`](LICENSE). Third-party notices, including the MIT
attribution for [DAYamlChecker](https://github.com/SuffolkLITLab/DAYamlChecker),
are in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
