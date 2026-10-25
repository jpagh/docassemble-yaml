#!/usr/bin/env bash
# Keep canonical-rule and transformed compatibility comparisons distinct.
set -euo pipefail
cd "$(dirname "$0")"
REPO_ROOT="$(cd ../.. && pwd)"
if [ ! -d node/node_modules ]; then
  (cd node && npm ci --silent)
fi
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
GRAMMAR="$WORK/Docassemble.sublime-syntax"
uv run --quiet --no-project --with pyyaml python \
  "$REPO_ROOT/grammars/scripts/build_syntax.py" --output "$GRAMMAR"
cargo build --quiet --release --bins
status=0
for pair in compatibility canonical; do
  if [ "$pair" = compatibility ]; then
    echo 'COMPATIBILITY: three explicit TextMate rule rewrites vs generated Fresh/syntect (not shipped parity)'
  else
    echo 'CANONICAL RULES: shipped TextMate vs giallo (name/injectTo metadata adaptation only; builtin dependencies differ)'
  fi
  for fixture in $(python3 -c "import json; print(' '.join(json.load(open('fixtures.json'))['$pair']))"); do
    input="$REPO_ROOT/grammars/fixtures/$fixture"
    if [ "$pair" = compatibility ]; then
      target/release/scope-parity "$GRAMMAR" "$input" categories.json > "$WORK/candidate.json"
      node node/tokenize.mjs "$input" categories.json --compatibility-reference > "$WORK/reference.json"
    else
      target/release/giallo "$REPO_ROOT/grammars/textmate" "$input" categories.json "$WORK" > "$WORK/candidate.json"
      node node/tokenize.mjs "$input" categories.json > "$WORK/reference.json"
    fi
    python3 compare.py "$WORK/reference.json" "$WORK/candidate.json" --pair "$pair" --fixture "$fixture" || status=1
  done
done
exit "$status"
