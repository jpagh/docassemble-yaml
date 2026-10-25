"""Guard the giallo package's intentionally metadata-only adaptation."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sync_grammars import ROOT, packaged_grammars, sync


class SyncGrammarsTests(unittest.TestCase):
    def test_packaged_rules_equal_canonical_sources(self):
        packaged = dict(packaged_grammars())
        self.assertEqual(len(packaged), 6)
        for source in (ROOT / "grammars/textmate").glob("*.json"):
            target = (
                "docassemble.tmLanguage.json"
                if source.name == "yaml.tmLanguage.json"
                else source.name
            )
            expected = json.loads(source.read_text())
            actual = json.loads(packaged[target])
            actual.pop("name")
            expected.pop("name", None)
            if source.stem.endswith("-injection"):
                self.assertEqual(actual.pop("injectTo"), ["docassemble"])
            self.assertEqual(actual, expected, source.name)

    def test_unique_registration_names_and_alias(self):
        grammars = {name: json.loads(text) for name, text in packaged_grammars()}
        names = [grammar["name"] for grammar in grammars.values()]
        self.assertEqual(len(set(names)), 6)
        self.assertTrue(all(name.startswith("docassemble") for name in names))
        self.assertEqual(grammars["docassemble.tmLanguage.json"]["name"], "docassemble")

    def test_committed_package_is_current(self):
        sync(check=True)
        expected = {name for name, _ in packaged_grammars()}
        actual = {path.name for path in (ROOT / "kakoune/grammars").glob("*.json")}
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
