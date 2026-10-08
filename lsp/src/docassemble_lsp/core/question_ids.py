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
the planned ID, so both agree on the same deterministic assignment.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class MissingQuestionId:
    """A question block without an ID and the ID the fixer should add."""

    line: int
    question_text: str
    generated_id: str
    id_line: int | None = None


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


def _yaml_documents(source: str) -> tuple[CommentedMap, ...]:
    parser = YAML()
    parser.allow_duplicate_keys = False
    try:
        loaded = list(parser.load_all(normalize_yaml_for_parser(source)))
    except YAMLError:
        return ()
    return tuple(document for document in loaded if isinstance(document, CommentedMap))


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
        if isinstance(id_value, str) and id_value.strip():
            author_ids.add(id_value.strip())

    used = set(author_ids)
    planned: list[MissingQuestionId] = []
    for document in documents:
        question_key = _find_key(document, "question")
        if question_key is None:
            continue
        question = document.get(question_key)
        if not isinstance(question, str) or not question.strip():
            continue

        id_key = _find_key(document, "id")
        id_value = document.get(id_key) if id_key is not None else None
        has_id = id_value is not None and (
            not isinstance(id_value, str) or bool(id_value.strip())
        )
        if has_id:
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
