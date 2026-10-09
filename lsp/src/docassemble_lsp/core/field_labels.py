"""Plan promoting a screen's question text into a field label.

W502 reports fields on multi-field screens that have no usable label. The
only automatic fix promotes the screen's question text to the label of the
first offending input field; every later offender stays reported so the
author decides what each remaining field should say. The question text is
promoted at most once per screen: once a field carries it, planning
declines, which is what makes repeated runs no-ops.

The planner is parser-backed: it reads the ruamel.yaml document that holds
the diagnostic line (the same shape ``question_ids`` uses) and returns a
plan describing the single safe edit, or ``None`` when no safe edit exists.

``None`` is returned when:

- the screen's question text is missing, blank, or not a string,
- the question text already labels one of the screen's fields,
- the diagnostic is not anchored to the first offending input field,
- the first offender is a code-only or presentation item,
- the offending item already has the key the fix would add, so the edit
  would produce a duplicate key (``no label`` shorthand next to an
  existing ``field``), or the ``no label`` value cannot become a ``field``
  target.

``plan_multifield_label`` is the only public entry point; the fixer turns
the plan into a source edit. It accepts the fix pass's already-parsed
documents so a pass with many W502 diagnostics plans them all from one
parse; the plan and the declines are the same as when it parses itself,
because both paths run the same per-line planning function.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ruamel.yaml.comments import CommentedMap

from docassemble_lsp.core.accessibility import (
    _extract_field_label,
    _extract_field_variable,
    field_lacks_usable_label,
)
from docassemble_lsp.core.line_helpers import _lc_key_line, _lc_line
from docassemble_lsp.core.question_ids import _find_key, _yaml_documents

FieldLabelKind = Literal["insert-label", "fill-label", "convert-no-label"]


@dataclass(frozen=True, slots=True)
class FieldLabelPlan:
    """A single safe edit that labels one field from the question text."""

    line: int
    kind: FieldLabelKind
    key_line: int
    question_text: str
    field_target: str | None = None


def _field_items(document: CommentedMap) -> list[CommentedMap]:
    fields_key = _find_key(document, "fields")
    if fields_key is None:
        return []
    fields = document.get(fields_key)
    if isinstance(fields, CommentedMap):
        fields = [fields]
    if not isinstance(fields, list):
        return []
    return [field for field in fields if isinstance(field, CommentedMap)]


def _question_text(document: CommentedMap) -> str | None:
    question_key = _find_key(document, "question")
    if question_key is None:
        return None
    value: Any = document.get(question_key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _question_already_labels_another_field(
    fields: list[CommentedMap], question_text: str
) -> bool:
    target = question_text.strip()
    return any(_extract_field_label(field).strip() == target for field in fields)


def _field_key_line(field: CommentedMap, name: str) -> int | None:
    key = _find_key(field, name)
    if key is None:
        return None
    return _lc_key_line(field, key)


def _target_plan(field: CommentedMap, question_text: str) -> FieldLabelPlan | None:
    line = _lc_line(field)
    label_line = _field_key_line(field, "label")
    field_line = _field_key_line(field, "field")
    no_label_line = _field_key_line(field, "no label")

    if label_line is None and no_label_line is None and field_line is not None:
        return FieldLabelPlan(
            line=line,
            kind="insert-label",
            key_line=field_line,
            question_text=question_text,
        )

    if label_line is not None and field_line is not None and no_label_line is None:
        # W502 only reports a blank explicit label, so replacing its value is
        # a single safe edit that does not add a duplicate ``label`` key.
        return FieldLabelPlan(
            line=line,
            kind="fill-label",
            key_line=label_line,
            question_text=question_text,
        )

    if label_line is None and no_label_line is not None:
        # ``no label: variable`` is a shorthand for the label text "no label"
        # plus the save target. The fix rewrites it into an explicit pair, so
        # the item must not already carry a ``field`` key of its own.
        if field_line is not None:
            return None
        target = _extract_field_variable(field)
        if not target or "\n" in target:
            return None
        return FieldLabelPlan(
            line=line,
            kind="convert-no-label",
            key_line=no_label_line,
            question_text=question_text,
            field_target=target,
        )

    return None


def _plan_for_document(
    document: CommentedMap, diagnostic_line: int
) -> FieldLabelPlan | None:
    fields = _field_items(document)
    if len(fields) <= 1:
        return None

    offending = [field for field in fields if field_lacks_usable_label(field)]
    if not offending or _lc_line(offending[0]) != diagnostic_line:
        return None

    question_text = _question_text(document)
    if question_text is None:
        return None
    if _question_already_labels_another_field(fields, question_text):
        return None
    return _target_plan(offending[0], question_text)


def plan_multifield_label(
    source: str,
    diagnostic_line: int,
    *,
    documents: tuple[CommentedMap, ...] | None = None,
) -> FieldLabelPlan | None:
    """Return the W502 edit for *diagnostic_line*, or ``None`` to decline.

    *documents* lets a caller that already parsed *source* (the shared
    fix-pass context in ``fixes.py``) plan against that parse; when it is
    ``None`` the source is parsed here. The plan and the declines are the
    same either way, because both paths run the same per-line planning.
    """
    if documents is None:
        documents = _yaml_documents(source)
    for document in documents:
        plan = _plan_for_document(document, diagnostic_line)
        if plan is not None:
            return plan
    return None
