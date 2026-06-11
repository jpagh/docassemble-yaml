# docassemble-yaml

Monorepo for the docassemble-lsp language server and its VS Code extension.

- **`lsp/`** — Python language server (CalVer versioned)
- **`vscode/`** — VS Code extension (same version as lsp/)

## Required tools

| Tool | Used by | Purpose |
|------|---------|---------|
| `just` | root, lsp, vscode | Command runner — all recipes via `mod` modules |
| `uv` | root, lsp | Python package manager, runs scripts and test commands |
| `prek` | root, lsp, vscode | Pre-commit hooks — runs taplo, ruff, mypy, pytest, oxlint, oxfmt |
| `taplo` | root, lsp, vscode | TOML formatter (prek hook and manual `just lsp format`) |
| `ruff` | lsp | Python linter and formatter (prek hook and `just lsp lint`/`format`) |
| `mypy` | lsp | Python type checker (prek hook and `just lsp type`) |
| `pytest` | lsp | Python test runner (prek hook and `just lsp test`) |
| `bump-my-version` | root | Unified version bump (`just bump`) |
| `node` / `npm` | vscode | Build, test, and package the VS Code extension |
| `esbuild` | vscode | JavaScript/TypeScript bundler (npm dev dependency) |
| `typescript` | vscode | TypeScript compiler (npm dev dependency) |
| `oxlint` / `oxfmt` | vscode | JavaScript/TypeScript linter and formatter (prek hooks) |

## Quick start

```bash
just test       # run all unit tests
just gate       # full pre-release gate
just bump       # bump version (default: patch)
```

See `AGENTS.md` for agent guidance, `lsp/README.md` and
`vscode/README.md` for per-project documentation.
