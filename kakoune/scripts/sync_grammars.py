"""Package canonical TextMate rules with only giallo registration metadata."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def packaged_grammars():
    for source in sorted((ROOT / "grammars/textmate").glob("*.json")):
        grammar = json.loads(source.read_text())
        injection = source.stem.endswith("-injection")
        grammar["name"] = (
            f"docassemble-{source.stem}"
            if injection
            else f"docassemble-{source.name.split('.')[0]}"
        )
        if source.name == "yaml.tmLanguage.json":
            grammar["name"] = "docassemble"
        if injection:
            # giallo links external injections by grammar name, not scopeName.
            grammar["injectTo"] = ["docassemble"]
        name = (
            "docassemble.tmLanguage.json"
            if source.name == "yaml.tmLanguage.json"
            else source.name
        )
        yield name, json.dumps(grammar, indent=2, ensure_ascii=False) + "\n"


def sync(check=False):
    destination = ROOT / "kakoune/grammars"
    for name, expected in packaged_grammars():
        target = destination / name
        if check:
            if not target.exists() or target.read_text() != expected:
                raise SystemExit(
                    f"{target} is stale; run mise run //kakoune:grammar:sync"
                )
        else:
            destination.mkdir(parents=True, exist_ok=True)
            target.write_text(expected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    sync(parser.parse_args().check)
