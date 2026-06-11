# docassemble-yaml

Monorepo for the docassemble-lsp language server and its VS Code extension.

- **`lsp/`** — Python language server (CalVer versioned)
- **`vscode/`** — VS Code extension (same version as lsp/)

## Quick start

```bash
just test       # run all unit tests
just gate       # full pre-release gate
just bump       # bump version (default: patch)
```

See `lsp/README.md` and `vscode/README.md` for per-project documentation.
