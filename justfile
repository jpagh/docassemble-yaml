set unstable

mod lsp
mod vscode

default:
    @just --list

check:
    @taplo format
    @ruff check --fix lsp
    @ruff format lsp
    @cd lsp && uv run mypy src/
    @cd lsp && uv run pytest tests -n auto -p no:terminal
    @cd vscode && npm run lint
    @cd vscode && npm run format

# Run all unit tests (LSP + VS Code mock-server)
test: lsp::test-all-pythons vscode::test

# Full pre-release gate (lint + type + LSP tests + extension integration)
gate: lsp::lint lsp::type lsp::test-all-pythons test-real-smoke test-real-ext

# Bump unified version (default: patch). Pass 'minor' or 'major' for larger bumps.
bump *part="patch":
    bump-my-version bump {{part}}
    git push --atomic origin HEAD --tags

publish: gate bump vscode::publish

# Run real-LSP CLI+LSP smoke test (no VS Code needed)
test-real-smoke:
    cd lsp && uv run node ../vscode/scripts/real-lsp-smoke.mjs

# Run VS Code extension tests against real docassemble-lsp
test-real-ext: vscode::build
    cd vscode && npm run test:real-lsp-extension
