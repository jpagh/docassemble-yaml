"""Fast structural checks for the scope-parity tooling.

Validates the JSON/YAML inputs so a broken fixture or mapping fails in
`mise run //tools/scope-parity:check` instead of inside the tokenizers.

Run via `mise run //tools/scope-parity:check` or::

    uv run --no-project --with pyyaml python lint.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_categories() -> None:
    categories = json.loads((HERE / "categories.json").read_text())
    for entry in categories["embedded"]:
        if not entry.get("scope") or not entry.get("category"):
            fail(f"embedded entry missing scope/category: {entry}")
    for rule in categories["rules"]:
        if not rule.get("prefix") or not rule.get("category"):
            fail(f"rule entry missing prefix/category: {rule}")


def check_expected_differences() -> None:
    expected = json.loads((HERE / "expected-differences.json").read_text())
    if not isinstance(expected, list):
        fail("expected-differences.json must be a list")
    for entry in expected:
        missing = {"line", "start", "end", "ref", "cand"} - entry.keys()
        if missing:
            fail(f"expected-differences entry missing {sorted(missing)}: {entry}")
        if not entry.get("reason"):
            fail(f"expected-differences entry needs a reason: {entry}")


def check_fixture() -> None:
    text = (HERE.parents[1] / "grammars" / "fixtures" / "sample.yml").read_text()
    try:
        text.encode("ascii")
    except UnicodeEncodeError as error:
        fail(f"fixture must be ASCII-only (offsets line up): {error}")
    try:
        documents = list(yaml.safe_load_all(text))
    except yaml.YAMLError as error:
        fail(f"fixture is not valid YAML: {error}")
    if not documents:
        fail("fixture has no YAML documents")


def main() -> int:
    json.loads((HERE / "node" / "package.json").read_text())
    check_categories()
    check_expected_differences()
    check_fixture()
    print("scope-parity inputs OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
