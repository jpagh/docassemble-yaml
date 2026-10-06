"""Diff the scope-parity JSON emitted by src/main.rs and tokenize.mjs.

Usage: compare.py REFERENCE.json CANDIDATE.json

Per character, both sides are reduced to one highlight category from the
shared categories.json. Any mismatch outside ``expected-differences.json``
fails the test; expected entries document why a difference is acceptable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED_PATH = HERE / "expected-differences.json"


def expand(line: dict) -> list[str]:
    """Expand runs into one category per character."""
    length = len(line["text"])
    categories = ["other"] * length
    for start, end, category in line["runs"]:
        for index in range(start, min(end, length)):
            categories[index] = category
    return categories


def mismatch_runs(reference: list[str], candidate: list[str]):
    """Yield contiguous (start, end, ref_category, cand_category) runs."""
    start = None
    ref_category = cand_category = ""
    for index in range(min(len(reference), len(candidate)) + 1):
        differs = (
            index < len(reference)
            and index < len(candidate)
            and reference[index] != candidate[index]
        )
        if differs and start is None:
            start = index
            ref_category = reference[index]
            cand_category = candidate[index]
        elif not differs and start is not None:
            yield start, index, ref_category, cand_category
            start = None


def expected_entries() -> list[dict]:
    if not EXPECTED_PATH.exists():
        return []
    return json.loads(EXPECTED_PATH.read_text())


def is_expected(entry: dict, line_number: int, run) -> bool:
    start, end, ref_category, cand_category = run
    return (
        entry.get("line") == line_number
        and entry.get("start") <= start
        and entry.get("end") >= end
        and entry.get("ref") == ref_category
        and entry.get("cand") == cand_category
    )


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    reference = json.loads(Path(sys.argv[1]).read_text())
    candidate = json.loads(Path(sys.argv[2]).read_text())
    expected = expected_entries()

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
        if ref_line["text"] != cand_line["text"]:
            print(f"line {ref_line['line']}: fixture text differs", file=sys.stderr)
            return 1
        ref_categories = expand(ref_line)
        cand_categories = expand(cand_line)
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
                "Fix the grammar, or add an entry with a reason to "
                f"{EXPECTED_PATH.name}",
                file=sys.stderr,
            )
        return 1

    print(
        f"scope parity OK: {len(reference['lines'])} lines, "
        f"{len(expected)} documented difference(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
