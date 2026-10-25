"""The shared conversion CLI must preserve the installed Fresh grammar."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BuildSyntaxTests(unittest.TestCase):
    def test_shared_cli_preserves_committed_fresh_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "Docassemble.sublime-syntax"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "grammars/scripts/build_syntax.py"),
                    "--output",
                    str(output),
                ],
                check=True,
            )
            self.assertEqual(
                output.read_bytes(),
                (ROOT / "fresh/grammars/Docassemble.sublime-syntax").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
