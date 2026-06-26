set unstable

mod lsp
mod vscode

default:
    @just --list

check:
    #!/usr/bin/env bash
    echo "Running..."
    run() {
      if ! output=$("$@" 2>&1); then
        echo "$output" >&2
        exit 1
      fi
    }
    run taplo format
    run ruff check --fix lsp
    run ruff format lsp
    (cd lsp && run uv run mypy src/)
    (cd lsp && run uv run pytest tests -n auto)
    (cd vscode && run npm run lint)
    (cd vscode && run npm run format)
    echo "Complete"

# Run all unit tests (LSP + VS Code mock-server)
test: lsp::test vscode::test

# Full pre-release gate (lint + type + LSP tests + extension integration)
gate: lsp::lint lsp::type lsp::test-all-pythons vscode::test

# Bump unified version (default: patch). Pass 'minor' or 'major' for larger bumps.
bump *part="patch":
    bump-my-version bump {{ part }}
    git push --atomic origin HEAD --tags

publish: gate bump vscode::publish
