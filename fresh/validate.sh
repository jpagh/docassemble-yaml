#!/usr/bin/env bash
# Minimal language-pack sanity check: the manifest parses and its grammar path
# exists. (Fresh itself validates the schema on install.)
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
import json, os, sys
manifest = json.load(open("package.json"))
grammar = manifest["fresh"]["grammar"]["file"]
if not os.path.exists(grammar):
    sys.exit(f"grammar file missing: {grammar}")
print(f"ok: {manifest['name']} -> {grammar}")
PY
