# docassemble-yaml

Monorepo for the docassemble-lsp language server and its VS Code extension.

- **`lsp/`** — Python language server (CalVer versioned)
- **`vscode/`** — VS Code extension (same version as lsp/)

## Required tools

| Tool | Used by | Purpose |
|------|---------|---------|
| `mise` | root, lsp, vscode | Tool/task runner — all commands via `mise run` |
| `uv` | lsp | Python package manager, runs scripts and tests |
| `tombi` | root, lsp, vscode | TOML formatter (`mise run //lsp:format`/`mise run //vscode:format` includes TOML; `tombi format` standalone) |
| `ruff` | lsp | Python linter and formatter (`mise run //lsp:lint`/`mise run //lsp:format`) |
| `mypy` | lsp | Python type checker (`mise run //lsp:type`) |
| `pytest` | lsp | Python test runner (`mise run //lsp:test`) |
| `bump-my-version` | root | Unified version bump (`mise run bump`) |
| `aube` | vscode | Node package manager (replaces npm); mise-managed |
| `node` | vscode | Node runtime (aube auto-switches) |
| `typescript` / `esbuild` | vscode | TS compile + bundler (mise-managed) |
| `oxlint` / `oxfmt` | vscode | TS/JS linter and formatter (`mise run //vscode:lint`/`mise run //vscode:format`) |

## Quick start

```bash
mise run check   # lint, type, and test the whole monorepo
mise run bump    # bump version (patch)
```

See `AGENTS.md` for agent guidance, `lsp/README.md` and
`vscode/README.md` for per-project documentation.
