"""Regression checks for pair-scoped exact and stale difference accounting."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import compare


class CompareTests(unittest.TestCase):
    def run_comparison(self, expected, candidate_category="string"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = {
                "engine": "vscode-textmate",
                "referenceMode": "shipped",
                "offsetUnit": "utf16",
                "lines": [{"line": 1, "text": "😀é", "runs": [[0, 4, "other"]]}],
            }
            candidate = {
                "engine": "giallo",
                "offsetUnit": "utf8",
                "lines": [
                    {"line": 1, "text": "😀é", "runs": [[0, 7, candidate_category]]}
                ],
            }
            for name, value in (
                ("ref", reference),
                ("cand", candidate),
                ("expected", expected),
            ):
                (root / name).write_text(json.dumps(value))
            output = io.StringIO()
            with (
                patch.object(compare, "EXPECTED_PATH", root / "expected"),
                patch(
                    "sys.argv",
                    [
                        "compare",
                        str(root / "ref"),
                        str(root / "cand"),
                        "--pair",
                        "canonical",
                        "--fixture",
                        "unicode.yml",
                    ],
                ),
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(output),
            ):
                return compare.main(), output.getvalue()

    def entry(self, **kwargs):
        return {
            "pair": "canonical",
            "fixture": "unicode.yml",
            "line": 1,
            "start": 0,
            "end": 3,
            "ref": "other",
            "cand": "string",
            "reason": "test only",
            **kwargs,
        }

    def test_exact_normalized_exception(self):
        self.assertEqual(self.run_comparison([self.entry()])[0], 0)

    def test_unexpected_pair_and_fixture_scoping(self):
        for expected in (
            [],
            [self.entry(pair="compatibility")],
            [self.entry(fixture="sample.yml")],
        ):
            status, output = self.run_comparison(expected)
            self.assertEqual(status, 1)
            self.assertIn("1 unexpected mismatch", output)

    def test_stale_and_redundant_exceptions_fail(self):
        for expected, category in (
            ([self.entry()], "other"),
            ([self.entry(), self.entry()], "string"),
        ):
            status, output = self.run_comparison(expected, category)
            self.assertEqual(status, 1)
            self.assertIn("1 stale entry", output)

    def test_partial_run_is_not_an_exception(self):
        status, output = self.run_comparison([self.entry(end=4)])
        self.assertEqual(status, 1)
        self.assertIn("1 unexpected mismatch", output)
        self.assertIn("1 stale entry", output)

    def test_adjacent_mismatches_split_when_category_pair_changes(self):
        self.assertEqual(
            list(compare.mismatch_runs(["a", "b"], ["x", "y"])),
            [(0, 1, "a", "x"), (1, 2, "b", "y")],
        )
