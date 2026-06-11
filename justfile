set unstable

mod lsp
mod vscode

default:
    @just --list

# Run all unit tests (LSP + VS Code mock-server)
test: lsp::test-versions vscode::test

# Full pre-release gate (lint + type + LSP tests + extension integration)
gate: lsp::lint lsp::type lsp::test-versions test-real-smoke test-real-ext

# Bump unified version (default: patch). Pass 'minor' or 'major' for larger bumps.
bump *part="patch":
    bump-my-version {{part}}

# Run real-LSP CLI+LSP smoke test (no VS Code needed)
test-real-smoke:
    cd lsp && uv run node ../vscode/scripts/real-lsp-smoke.mjs

# Run VS Code extension tests against real docassemble-lsp
test-real-ext: vscode::build
    cd vscode && npm run test:real-lsp-extension
