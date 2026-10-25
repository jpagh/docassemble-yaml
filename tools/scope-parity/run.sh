#!/usr/bin/env bash
# Compatibility parity: tokenize the shared fixture with explicitly patched
# TextMate reference grammars (vscode-textmate) and the generated Fresh grammar
# (syntect), then diff the per-character highlight categories.
#
# Usage: tools/scope-parity/run.sh
set -euo pipefail
cd "$(dirname "$0")"
REPO_ROOT="$(cd ../.. && pwd)"

FIXTURE="$REPO_ROOT/grammars/fixtures/sample.yml"

if [ ! -d node/node_modules ]; then
  echo "installing reference tokenizer dependencies (one time)..."
  (cd node && npm ci --silent)
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Test fresh output without changing the committed packaging artifact.
GRAMMAR="$WORK/Docassemble.sublime-syntax"
uv run --quiet --no-project --with pyyaml python \
  "$REPO_ROOT/grammars/scripts/build_syntax.py" --output "$GRAMMAR"

echo "tokenizing with syntect (candidate)..."
cargo run --quiet --release --manifest-path Cargo.toml -- \
  "$GRAMMAR" "$FIXTURE" categories.json > "$WORK/candidate.json"

echo "tokenizing with vscode-textmate (transformed compatibility reference)..."
node node/tokenize.mjs "$FIXTURE" categories.json --compatibility-reference > "$WORK/reference.json"

python3 compare.py "$WORK/reference.json" "$WORK/candidate.json"
