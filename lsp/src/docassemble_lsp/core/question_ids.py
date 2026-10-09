"""Question block ID generation and missing-ID planning.

Docassemble block IDs only have to be unique and readable, so generated
IDs keep letters, digits, and spaces (lowercased) and let every other
mark separate words. Apostrophes are dropped in place so ``didn't``
becomes ``didnt`` rather than ``didn t``, and Unicode-aware ``isalnum``
keeps accented letters. Mako expressions in the question text are left
literal: their delimiters separate words, so ``${city_only_address}``
becomes ``city only address`` instead of an empty or broken ID.

``plan_missing_question_ids`` parses a source file once and returns the
unique ID every question block without one should receive, in document
order. The validation rule reports those blocks and the fixer inserts
the planned ID, so both agree on the same deterministic assignment, and
both ask ``has_usable_id`` whether a block already declares an ID and
``has_usable_question_text`` whether its question can produce one.

``plan_duplicate_question_ids`` covers the other half of uniqueness: it
keeps the first block that uses an ID and plans the suffix for every
later block that repeats it. Missing-ID planning reserves those planned
replacements, so one fix run cannot hand the same ID to a missing block
and to a renamed duplicate.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeGuard

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

from docassemble_lsp.core.line_helpers import _lc_key_line
from docassemble_lsp.core.yaml_parsing import normalize_yaml_for_parser

_APOSTROPHE_RE = re.compile(r"['\u2018\u2019\u02bc]")
_WHITESPACE_RE = re.compile(r"\s+")
_DEFAULT_ID_BASE = "question"


def normalize_question_id(question: str) -> str:
    """Normalize question text into a candidate block ID."""
    text = _APOSTROPHE_RE.sub("", question)
    text = "".join(char if char.isalnum() else " " for char in text)
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def unique_question_id(
    base: str, *, reserved: Iterable[str], used: Iterable[str]
) -> str:
    """Return *base* or a deterministic ``<base> <n>`` suffix when taken.

    ``reserved`` holds IDs that must never be generated (author-written
    IDs in the file) and ``used`` holds IDs already claimed (earlier
    generated IDs). An empty base falls back to ``question`` so the
    result is still a lowercase alphanumeric ID.
    """
    reserved_set = set(reserved)
    used_set = set(used)
    candidate = base or _DEFAULT_ID_BASE
    if candidate not in reserved_set and candidate not in used_set:
        return candidate
    number = 2
    while (
        f"{candidate} {number}" in reserved_set or f"{candidate} {number}" in used_set
    ):
        number += 1
    return f"{candidate} {number}"


def has_usable_id(value: object) -> bool:
    """Return whether *value* means the block already declares an ID.

    A non-empty string is an ID. A non-string value (for example the
    numeric ``id: 42``) counts as present because the YAML string type
    check reports the value itself, so the missing-ID rule must not add a
    second finding. A missing key, a null value, and an empty or
    whitespace-only string all mean the block has no ID.

    The W608 rule and ``plan_missing_question_ids`` both call this so the
    reported blocks and the planned fixes cannot drift apart.
    """
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def has_usable_question_text(value: object) -> TypeGuard[str]:
    """Return whether *value* can be normalized into a generated ID.

    Only a non-empty string has text to normalize. Every other YAML value
    (a list, mapping, number, boolean, or null) is reported by the string
    type check and can never produce an ID, so the missing-ID rule must
    not add a second, unsatisfiable finding for it.

    The W608 rule and ``plan_missing_question_ids`` both call this so the
    reported blocks and the planned fixes cannot drift apart. The W510
    shortcut planner also calls it: expanding a shortcut whose block has
    no usable question text would leave the field with no accessible
    label, so it declines.
    """
    return isinstance(value, str) and bool(value.strip())


def usable_id(value: object) -> str | None:
    """Return *value* when it is a usable block ID, otherwise ``None``.

    Docassemble block IDs are non-empty strings. Non-string values are
    reported by the YAML string type check, and empty (or whitespace-only)
    strings count as missing, so neither is a duplicate candidate.
    """
    if isinstance(value, str) and has_usable_id(value):
        return value
    return None


@dataclass(frozen=True, slots=True)
class MissingQuestionId:
    """A question block without an ID and the ID the fixer should add."""

    line: int
    question_text: str
    generated_id: str
    id_line: int | None = None


@dataclass(frozen=True, slots=True)
class DuplicateQuestionId:
    """A later block reusing an earlier ID and the unique ID it should get."""

    line: int
    first_line: int
    duplicate_id: str
    replacement_id: str


def shorten_question_text(value: object, limit: int = 160) -> str:
    """Collapse whitespace and truncate question text for a diagnostic."""
    rendered = _WHITESPACE_RE.sub(" ", str(value or "")).strip()
    if len(rendered) <= limit:
        return rendered
    return rendered[: limit - 3] + "..."


def _find_key(document: CommentedMap, name: str) -> object | None:
    for key in document:
        if isinstance(key, str) and key.lower() == name:
            return key
    return None


def _id_entries(documents: tuple[CommentedMap, ...]) -> list[tuple[int, str]]:
    """Return ``(line, id)`` for every usable top-level ID in document order."""
    entries: list[tuple[int, str]] = []
    for document in documents:
        id_key = _find_key(document, "id")
        if id_key is None:
            continue
        id_value = usable_id(document.get(id_key))
        if id_value is None:
            continue
        entries.append((_lc_key_line(document, id_key), id_value))
    return entries


def _plan_duplicate_ids(
    documents: tuple[CommentedMap, ...],
) -> tuple[DuplicateQuestionId, ...]:
    entries = _id_entries(documents)
    all_ids = {entry_id for _, entry_id in entries}
    used = set(all_ids)
    first_seen: dict[str, int] = {}
    planned: list[DuplicateQuestionId] = []
    for line, entry_id in entries:
        first_line = first_seen.get(entry_id)
        if first_line is None:
            first_seen[entry_id] = line
            continue
        replacement = unique_question_id(entry_id, reserved=all_ids, used=used)
        used.add(replacement)
        planned.append(
            DuplicateQuestionId(
                line=line,
                first_line=first_line,
                duplicate_id=entry_id,
                replacement_id=replacement,
            )
        )
    return tuple(planned)


def _yaml_documents(source: str) -> tuple[CommentedMap, ...]:
    parser = YAML()
    parser.allow_duplicate_keys = False
    try:
        loaded = list(parser.load_all(normalize_yaml_for_parser(source)))
    except YAMLError:
        return ()
    return tuple(document for document in loaded if isinstance(document, CommentedMap))


def plan_duplicate_question_ids(source: str) -> tuple[DuplicateQuestionId, ...]:
    """Plan a unique ID for every block that repeats an earlier block ID.

    The first occurrence is never planned. Later occurrences receive the
    same ``<id> <n>`` suffix scheme as generated question IDs, and the
    counter skips every author-written ID in the file as well as every
    replacement already planned. Returns an empty tuple when the source
    does not parse (for example a ``# use jinja`` template).
    """
    documents = _yaml_documents(source)
    if not documents:
        return ()
    return _plan_duplicate_ids(documents)


def plan_missing_question_ids(source: str) -> tuple[MissingQuestionId, ...]:
    """Plan an ID for every question block that lacks one.

    Returns an empty tuple when the source does not parse (for example a
    ``# use jinja`` template), so no automatic rewrite is offered there.
    """
    documents = _yaml_documents(source)
    if not documents:
        return ()

    author_ids: set[str] = set()
    for document in documents:
        id_key = _find_key(document, "id")
        id_value = document.get(id_key) if id_key is not None else None
        usable = usable_id(id_value)
        if usable is not None:
            author_ids.add(usable.strip())

    # Duplicate replacements are about to claim their IDs, so a missing-ID
    # fix must not generate one of them as well.
    used = set(author_ids)
    used.update(entry.replacement_id for entry in _plan_duplicate_ids(documents))
    planned: list[MissingQuestionId] = []
    for document in documents:
        question_key = _find_key(document, "question")
        if question_key is None:
            continue
        question = document.get(question_key)
        if not has_usable_question_text(question):
            continue

        id_key = _find_key(document, "id")
        id_value = document.get(id_key) if id_key is not None else None
        if has_usable_id(id_value):
            continue

        base = normalize_question_id(question) or _DEFAULT_ID_BASE
        generated = unique_question_id(base, reserved=author_ids, used=used)
        used.add(generated)
        planned.append(
            MissingQuestionId(
                line=_lc_key_line(document, question_key),
                question_text=question,
                generated_id=generated,
                id_line=_lc_key_line(document, id_key) if id_key is not None else None,
            )
        )
    return tuple(planned)
