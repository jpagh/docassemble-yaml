set unstable

default:
    @just --list

# --- Python LSP server ---

# Run LSP tests (pass extra args after --)
test-lsp *args:
    cd lsp && uv run pytest {{args || '-q -n auto'}}

test-lsp-versions *args:
    cd lsp && uv run --python 3.10 --only-group test pytest {{args || '-q -n auto'}}
    cd lsp && uv run --python 3.11 --only-group test pytest {{args || '-q -n auto'}}
    cd lsp && uv run --python 3.12 --only-group test pytest {{args || '-q -n auto'}}
    cd lsp && uv run --python 3.13 --only-group test pytest {{args || '-q -n auto'}}
    cd lsp && uv run --python 3.14 --only-group test pytest {{args || '-q -n auto'}}

# Run mypy type checker on the LSP
type-lsp:
    cd lsp && uv run mypy .

# Lint LSP Python source (auto-fix)
lint-lsp:
    cd lsp && uv run ruff check --fix

# Format LSP Python source
format-lsp:
    cd lsp && uv run ruff format

# Run full pre-commit suite on the LSP
check-lsp:
    cd lsp && prek run -a

# --- VS Code extension ---

# Build VS Code extension
build-vscode:
    cd vscode && npm run build

# Run VS Code extension tests (mock server only)
test-vscode: build-vscode
    cd vscode && npm test

# Run real-LSP CLI+LSP smoke test (no VS Code needed)
test-real-smoke:
    cd lsp && uv run node ../vscode/scripts/real-lsp-smoke.mjs

# Run VS Code extension tests against real docassemble-lsp
test-real-ext: build-vscode
    cd vscode && npm run test:real-lsp-extension

# --- Versioning ---

# Bump unified version (default: patch). Pass 'minor' or 'major' for larger bumps.
bump *part="patch":
    bump-my-version {{part}}

# --- Combined ---

# Run all unit tests (LSP + VS Code mock-server)
test: test-lsp-versions test-vscode

# Full pre-release gate (lint + type + LSP tests + extension integration)
gate: lint-lsp type-lsp test-lsp-versions test-real-smoke test-real-ext
