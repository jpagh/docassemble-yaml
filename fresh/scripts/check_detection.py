"""Check Fresh's portable path regex against the shared detection corpus."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / "fresh/docassemble.ts").read_text()
pattern = re.search(r"const DOCASSEMBLE_PATH = /(.*)/;", source).group(1)
# This JS regex uses only syntax shared with Python; no runtime code is shared.
detection = re.compile(pattern.replace(r"\/", "/"))
for case in json.loads((ROOT / "fixtures/detection/paths.json").read_text()):
    actual = bool(detection.search(case["path"].replace("\\", "/")))
    assert actual == case["fresh"], case
print("PASS: Fresh detection matches every shared path case")
