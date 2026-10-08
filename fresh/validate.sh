#!/usr/bin/env bash
# Minimal sanity check for the Fresh bundle: the manifest parses, its grammar
# paths and plugin entries exist, and the grammar file is non-empty. (Fresh
# itself validates the schema on install.)
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
import json, os, sys

manifest = json.load(open("package.json"))
fresh = manifest["fresh"]
if manifest.get("type") != "bundle":
    sys.exit(f"expected a bundle manifest, got type={manifest.get('type')!r}")

checked = []
for lang in fresh.get("languages", []):
    grammar = lang.get("grammar", {}).get("file")
    if not grammar:
        continue
    if not os.path.isfile(grammar) or os.path.getsize(grammar) == 0:
        sys.exit(f"grammar file missing or empty for {lang['id']}: {grammar}")
    checked.append(f"{lang['id']} -> {grammar}")

for plugin in fresh.get("plugins", []):
    entry = plugin["entry"]
    if not os.path.isfile(entry):
        sys.exit(f"plugin entry missing: {entry}")
    checked.append(f"plugin -> {entry}")

if not checked:
    sys.exit("manifest declares no grammars or plugins")

print("ok: " + "; ".join(checked))
PY
