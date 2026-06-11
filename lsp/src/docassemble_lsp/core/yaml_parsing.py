from __future__ import annotations

import re

DOCUMENT_MATCH = re.compile(r"^---[ \t]*\r?$", flags=re.MULTILINE)
_REMOVE_TRAILING_DOTS_RE = re.compile(r"[\n\r]+\.\.\.$")
_TAB_RE = re.compile(r"\t")


def normalize_yaml_for_parser(text: str) -> str:
    return _TAB_RE.sub("  ", text)


def normalize_yaml_document_for_parser(source_code: str) -> str:
    return _REMOVE_TRAILING_DOTS_RE.sub("", normalize_yaml_for_parser(source_code))
