"""Source-named tests for native-offset conversion and strict stream coverage."""

import unittest

from offsets import boundaries, normalize


class OffsetTests(unittest.TestCase):
    def test_utf16_utf8_and_codepoint_boundaries(self):
        text = "a😀e\u0301中"
        self.assertEqual(
            boundaries(text, "utf16"), {0: 0, 1: 1, 3: 2, 4: 3, 5: 4, 6: 5}
        )
        self.assertEqual(
            boundaries(text, "utf8"), {0: 0, 1: 1, 5: 2, 6: 3, 8: 4, 11: 5}
        )
        self.assertEqual(boundaries(text, "codepoint"), dict(enumerate(range(6))))
        for unit, end, start in (("utf16", 6, 3), ("utf8", 11, 5), ("codepoint", 5, 2)):
            self.assertEqual(
                normalize(
                    {
                        "text": text,
                        "runs": [[0, start, "other"], [start, end, "string"]],
                    },
                    unit,
                ),
                ["other"] * 2 + ["string"] * 3,
            )

    def test_reject_split_surrogate_and_split_utf8_sequence(self):
        for unit, end in (("utf16", 1), ("utf8", 2)):
            with self.assertRaisesRegex(ValueError, "boundary"):
                normalize({"text": "😀", "runs": [[0, end, "other"]]}, unit)

    def test_reject_gaps_overlaps_incomplete_and_out_of_bounds(self):
        for runs in (
            [],
            [[1, 2, "other"]],
            [[0, 1, "other"], [0, 2, "string"]],
            [[0, 3, "other"]],
        ):
            with self.assertRaises(ValueError):
                normalize({"text": "ab", "runs": runs}, "utf8")
        self.assertEqual(normalize({"text": "", "runs": []}, "utf8"), [])
