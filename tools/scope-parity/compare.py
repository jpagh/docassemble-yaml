"""Diff the scope-parity JSON emitted by src/main.rs and tokenize.mjs.

Usage: compare.py REFERENCE.json CANDIDATE.json --pair PAIR --fixture NAME

Per character, both sides are reduced to one highlight category from the
shared categories.json. Any mismatch outside ``expected-differences.json``
fails the test; expected entries document why a difference is acceptable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from offsets import normalize

HERE = Path(__file__).resolve().parent
EXPECTED_PATH = HERE / "expected-differences.json"


def mismatch_runs(reference: list[str], candidate: list[str]):
    """Yield contiguous (start, end, ref_category, cand_category) runs."""
    start = 0
    while start < len(reference):
        if reference[start] == candidate[start]:
            start += 1
            continue
        pair = reference[start], candidate[start]
        end = start + 1
        while end < len(reference) and (reference[end], candidate[end]) == pair:
            end += 1
        yield start, end, *pair
        start = end


def expected_entries() -> list[dict]:
    if not EXPECTED_PATH.exists():
        return []
    return json.loads(EXPECTED_PATH.read_text())


def is_expected(entry: dict, line_number: int, run) -> bool:
    start, end, ref_category, cand_category = run
    return (
        entry.get("line") == line_number
        and entry.get("start") == start
        and entry.get("end") == end
        and entry.get("ref") == ref_category
        and entry.get("cand") == cand_category
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--pair", choices=["canonical", "compatibility"], required=True)
    parser.add_argument("--fixture", required=True)
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text())
    candidate = json.loads(args.candidate.read_text())
    expected = [
        entry
        for entry in expected_entries()
        if entry["pair"] == args.pair and entry["fixture"] == args.fixture
    ]
    mode, engine = (
        ("shipped", "giallo")
        if args.pair == "canonical"
        else ("compatibility", "syntect")
    )
    if (
        reference["engine"] != "vscode-textmate"
        or reference["referenceMode"] != mode
        or candidate["engine"] != engine
    ):
        raise ValueError("wrong engine pair or reference mode")

    if len(reference["lines"]) != len(candidate["lines"]):
        print(
            f"line count differs: reference={len(reference['lines'])} "
            f"candidate={len(candidate['lines'])}",
            file=sys.stderr,
        )
        return 1

    failures = 0
    matched_expected: set[int] = set()
    for ref_line, cand_line in zip(reference["lines"], candidate["lines"]):
        if (
            ref_line["line"] != cand_line["line"]
            or ref_line["text"] != cand_line["text"]
        ):
            print(f"line {ref_line['line']}: fixture text differs", file=sys.stderr)
            return 1
        ref_categories = normalize(ref_line, reference["offsetUnit"])
        cand_categories = normalize(cand_line, candidate["offsetUnit"])
        for run in mismatch_runs(ref_categories, cand_categories):
            matched = None
            for index, entry in enumerate(expected):
                if is_expected(entry, ref_line["line"], run):
                    matched = index
                    break
            if matched is not None:
                matched_expected.add(matched)
                continue
            failures += 1
            start, end, ref_category, cand_category = run
            print(
                f"line {ref_line['line']:>3} col {start:>3}-{end:<3} "
                f"ref={ref_category:<10} cand={cand_category:<10} "
                f"| {ref_line['text']}"
            )
            print(
                " " * (len(f"line {ref_line['line']:>3} col {start:>3}  ") + start)
                + "^" * (end - start)
            )

    stale = [
        entry for index, entry in enumerate(expected) if index not in matched_expected
    ]
    for entry in stale:
        print(
            f"stale expected difference (no longer present): "
            f"line {entry['line']} {entry['start']}-{entry['end']} — "
            f"{entry.get('reason', 'no reason given')}",
            file=sys.stderr,
        )

    if failures or stale:
        print(
            f"\n{failures} unexpected mismatch run(s), {len(stale)} stale entry(ies)",
            file=sys.stderr,
        )
        if failures:
            print(
                "Investigate drift; approved intentional differences require a reason in "
                f"{EXPECTED_PATH.name}",
                file=sys.stderr,
            )
        return 1

    print(
        f"{args.pair} parity OK ({args.fixture}, codepoints): {len(reference['lines'])} lines, "
        f"{len(expected)} documented difference(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
