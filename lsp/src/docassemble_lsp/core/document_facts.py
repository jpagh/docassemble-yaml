from __future__ import annotations

import re
from dataclasses import dataclass

_TOP_LEVEL_KEY_RE = re.compile(r"^([^:#][^:]*?)\s*:\s*(.*)$")
_BLOCK_SCALAR_MARKERS = {"|", ">", "|-", ">-", "|+", ">+"}
_PREFERRED_NAME_KEYS = (
    "id",
    "event",
    "def",
    "question",
    "attachment",
    "attachments",
    "objects",
    "fields",
    "code",
)


@dataclass(frozen=True, slots=True)
class TopLevelKeyFact:
    name: str
    value: str
    line: int


@dataclass(frozen=True, slots=True)
class DocumentFact:
    name: str
    start_line: int
    end_line: int
    selection_line: int
    keys: tuple[TopLevelKeyFact, ...]


def _document_lines(source: str) -> list[str]:
    return source.splitlines() or [""]


def _document_ranges(lines: list[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0

    for index, text in enumerate(lines):
        if text.strip() != "---":
            continue
        if index > start:
            ranges.append((start, index - 1))
        start = index + 1

    if start < len(lines):
        ranges.append((start, len(lines) - 1))

    if not ranges and lines:
        ranges.append((0, len(lines) - 1))

    return ranges


def _top_level_key_facts(
    lines: list[str], start: int, end: int
) -> tuple[TopLevelKeyFact, ...]:
    facts: list[TopLevelKeyFact] = []
    for line_index in range(start, end + 1):
        text = lines[line_index]
        if text.strip() == "---" or text.startswith((" ", "\t")):
            continue
        match = _TOP_LEVEL_KEY_RE.match(text)
        if match is None:
            continue
        facts.append(
            TopLevelKeyFact(
                name=match.group(1).strip(),
                value=match.group(2).strip(),
                line=line_index,
            )
        )
    return tuple(facts)


def _display_value(value: str) -> str:
    stripped = value.strip().strip('"').strip("'")
    if not stripped or stripped in _BLOCK_SCALAR_MARKERS:
        return ""
    return stripped


def _document_name(
    keys: tuple[TopLevelKeyFact, ...], doc_index: int
) -> tuple[str, int]:
    keyed = {fact.name: fact for fact in keys}

    for preferred in _PREFERRED_NAME_KEYS:
        fact = keyed.get(preferred)
        if fact is None:
            continue
        if preferred == "id":
            value = _display_value(fact.value)
            return (value or "id", fact.line)

        value = _display_value(fact.value)
        return (value or preferred, fact.line)

    if keys:
        return (keys[0].name, keys[0].line)

    return (f"Document {doc_index + 1}", 0)


def build_document_facts(source: str) -> list[DocumentFact]:
    lines = _document_lines(source)
    facts: list[DocumentFact] = []

    for doc_index, (start, end) in enumerate(_document_ranges(lines)):
        key_facts = _top_level_key_facts(lines, start, end)
        if not key_facts:
            continue

        name, selection_line = _document_name(key_facts, doc_index)
        facts.append(
            DocumentFact(
                name=name,
                start_line=start,
                end_line=end,
                selection_line=selection_line,
                keys=key_facts,
            )
        )

    return facts
