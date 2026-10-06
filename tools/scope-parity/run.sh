#!/usr/bin/env bash
# Scope-parity test: tokenize the fixture with the original VS Code TextMate
# grammars (vscode-textmate) and with the generated Fresh grammar (syntect),
# then diff the per-character highlight categories.
#
# Usage: tools/scope-parity/run.sh
set -euo pipefail
cd "$(dirname "$0")"
REPO_ROOT="$(cd ../.. && pwd)"

GRAMMAR="$REPO_ROOT/fresh/grammars/Docassemble.sublime-syntax"
FIXTURE="fixtures/sample.yml"

# Always test freshly generated output, so a stale committed grammar cannot
# hide a converter regression.
(cd "$REPO_ROOT" && uv run --project lsp python fresh/scripts/build_syntax.py)

if [ ! -d node/node_modules ]; then
  echo "installing reference tokenizer dependencies (one time)..."
  (cd node && npm install --silent)
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "tokenizing with syntect (candidate)..."
cargo run --quiet --release --manifest-path Cargo.toml -- \
  "$GRAMMAR" "$FIXTURE" categories.json > "$WORK/candidate.json"

echo "tokenizing with vscode-textmate (reference)..."
node node/tokenize.mjs "$FIXTURE" categories.json > "$WORK/reference.json"

python3 compare.py "$WORK/reference.json" "$WORK/candidate.json"
