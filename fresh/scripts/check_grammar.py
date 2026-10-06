"""Validate the committed Fresh language pack.

Checks that ``package.json`` and the grammar agree and that the committed
grammar is exactly what ``build_syntax.py`` produces (whitespace aside, the
output should be byte-identical -- if it is not, the file was edited by hand
or the generator changed without regenerating).

Run via ``mise run //fresh:check`` or::

    uv run --no-project --with pyyaml python fresh/scripts/check_grammar.py
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
sys.path.insert(0, str(HERE))

import build_syntax

COMMITTED = PACK / "grammars" / "Docassemble.sublime-syntax"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    manifest = json.loads((PACK / "package.json").read_text())
    grammar_path = PACK / manifest["fresh"]["grammar"]["file"]
    if grammar_path != COMMITTED:
        fail(f"manifest grammar path {grammar_path} is not {COMMITTED}")

    committed = COMMITTED.read_text()
    # The file starts with a comment header before the YAML directive.
    try:
        yaml.safe_load(committed.split("---", 1)[1])
    except yaml.YAMLError as error:
        fail(f"committed grammar is not valid YAML: {error}")

    expected = build_syntax.render(build_syntax.build())
    if expected != committed:
        diff = difflib.unified_diff(
            committed.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=str(COMMITTED),
            tofile="generated",
        )
        sys.stderr.writelines(diff)
        fail(
            "committed grammar is stale; run "
            "`uv run --project lsp python fresh/scripts/build_syntax.py`"
        )

    print("fresh pack OK: manifest, grammar YAML, and generator output agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
