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


REASON_CLASSES = {
    "shipped-block-python-injection": ("python", None),
    "shipped-block-mako-wrapper": ("other", "string"),
}


def fixtures() -> dict[str, list[str]]:
    return json.loads((HERE / "fixtures.json").read_text())


def check_expected_differences() -> None:
    expected = json.loads((HERE / "expected-differences.json").read_text())
    if not isinstance(expected, list):
        fail("expected-differences.json must be a list")
    seen = set()
    spec = json.loads((HERE / "categories.json").read_text())
    categories = {"other"} | {r["category"] for r in spec["rules"] + spec["embedded"]}
    for entry in expected:
        required = {
            "pair",
            "fixture",
            "line",
            "start",
            "end",
            "ref",
            "cand",
            "reasonClass",
            "reason",
        }
        if set(entry) != required:
            fail(
                f"expected-differences entry requires exactly {sorted(required)}: {entry}"
            )
        pair, fixture = entry["pair"], entry["fixture"]
        if pair not in fixtures() or fixture not in fixtures()[pair]:
            fail(f"unknown pair/fixture: {entry}")
        if (
            entry["reasonClass"] not in REASON_CLASSES
            or not entry["reason"].strip()
            or "\n" in entry["reason"]
        ):
            fail(f"unknown reason class or missing explanation: {entry}")
        cand, ref = REASON_CLASSES[entry["reasonClass"]]
        if (
            pair != "canonical"
            or entry["cand"] != cand
            or (ref and entry["ref"] != ref)
        ):
            fail(f"reason class does not apply to this category pair: {entry}")
        if (
            entry["ref"] not in categories
            or entry["cand"] not in categories
            or entry["ref"] == entry["cand"]
        ):
            fail(f"invalid category difference: {entry}")
        lines = (
            (HERE.parents[1] / "grammars/fixtures" / fixture).read_text().splitlines()
        )
        if not all(type(entry[key]) is int for key in ("line", "start", "end")):
            fail(f"coordinates must be integers: {entry}")
        if not 1 <= entry["line"] <= len(lines) or not 0 <= entry["start"] < entry[
            "end"
        ] <= len(lines[entry["line"] - 1]):
            fail(f"invalid codepoint coordinates: {entry}")
        for column in range(entry["start"], entry["end"]):
            position = (pair, fixture, entry["line"], column)
            if position in seen:
                fail(f"duplicate/overlapping expected difference: {entry}")
            seen.add(position)


def check_fixture() -> None:
    corpus = fixtures()
    if set(corpus) != {"canonical", "compatibility"}:
        fail("fixtures.json must declare both engine pairs")
    if (
        "sample.yml" not in corpus["compatibility"]
        or "unicode.yml" not in corpus["canonical"]
    ):
        fail("existing Fresh corpus and canonical Unicode coverage are required")
    for pair, names in corpus.items():
        if not names or len(names) != len(set(names)):
            fail(f"empty or duplicate fixtures: {pair}")
        for name in names:
            if Path(name).name != name:
                fail(f"fixture must be a basename: {name}")
            text = (HERE.parents[1] / "grammars/fixtures" / name).read_text()
            if pair == "compatibility" and not text.isascii():
                fail(f"compatibility fixture must remain ASCII-only: {name}")
            try:
                documents = list(yaml.safe_load_all(text))
            except yaml.YAMLError as error:
                fail(f"fixture {name} is not valid YAML: {error}")
            if not documents:
                fail(f"fixture {name} has no YAML documents")
    unicode_text = (HERE.parents[1] / "grammars/fixtures/unicode.yml").read_text()
    if (
        not any(ord(char) > 0xFFFF for char in unicode_text)
        or "\u0301" not in unicode_text
    ):
        fail("Unicode fixture must exercise astral characters and combining marks")


def main() -> int:
    json.loads((HERE / "node" / "package.json").read_text())
    check_categories()
    check_expected_differences()
    check_fixture()
    print("scope-parity inputs OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
