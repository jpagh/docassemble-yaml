"""Plan expanding a yes/no shortcut into an explicit single-field screen.

W510 reports the four question-level yes/no shortcuts (``yesno``,
``noyes``, ``yesnomaybe``, ``noyesmaybe``). The only automatic fix expands
one shortcut into an explicit ``fields`` screen whose single field keeps
the question text as its accessible label through the ``no label``
shorthand, with the radio datatype that matches the shortcut:
``yesnoradio``/``noyesradio`` for the boolean variants and
``yesnomaybe``/``noyesmaybe`` for the three-state ones.

The planner is parser-backed: it reads the ruamel.yaml document that holds
the diagnostic line (the same shape ``question_ids`` and ``field_labels``
use) and returns a plan describing the single safe edit, or ``None`` when
no safe edit exists.

``None`` is returned when:

- the document already has a ``fields`` block, because merging a shortcut
  into it is a semantic change,
- more than one shortcut is present, because one replacement per shortcut
  would write more than one ``fields`` key,
- the shortcut value is missing, blank, or not a string, so there is no
  target to move into the field, or
- the diagnostic line is not the shortcut's key line.

``plan_yesno_shortcut`` is the only public entry point; the fixer turns
the plan into a source edit.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ruamel.yaml.comments import CommentedMap

from docassemble_lsp.core.line_helpers import _lc_key_line
from docassemble_lsp.core.question_ids import _find_key, _yaml_documents

YESNO_SHORTCUTS: tuple[str, ...] = ("yesno", "noyes", "yesnomaybe", "noyesmaybe")

_MAYBE_SHORTCUTS = frozenset({"yesnomaybe", "noyesmaybe"})
_PLAIN_TARGET_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


def shortcut_datatype(shortcut: str) -> str:
    """Return the explicit datatype that matches *shortcut*."""
    if shortcut in _MAYBE_SHORTCUTS:
        return shortcut
    return f"{shortcut}radio"


@dataclass(frozen=True, slots=True)
class YesNoShortcutPlan:
    """A single safe edit that expands one yes/no shortcut."""

    key_line: int
    shortcut: str
    target: str
    datatype: str


def _shortcut_target(value: str) -> str:
    if _PLAIN_TARGET_RE.match(value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _present_shortcuts(document: CommentedMap) -> tuple[str, ...]:
    return tuple(shortcut for shortcut in YESNO_SHORTCUTS if shortcut in document)


def _plan_for_document(
    document: CommentedMap, diagnostic_line: int
) -> YesNoShortcutPlan | None:
    present = _present_shortcuts(document)
    if len(present) != 1:
        return None

    shortcut = present[0]
    if _lc_key_line(document, shortcut) != diagnostic_line:
        return None
    if _find_key(document, "fields") is not None:
        return None

    value = document.get(shortcut)
    if not isinstance(value, str) or not value.strip():
        return None

    return YesNoShortcutPlan(
        key_line=diagnostic_line,
        shortcut=shortcut,
        target=_shortcut_target(value.strip()),
        datatype=shortcut_datatype(shortcut),
    )


def plan_yesno_shortcut(source: str, diagnostic_line: int) -> YesNoShortcutPlan | None:
    """Return the W510 edit for *diagnostic_line*, or ``None`` to decline."""
    for document in _yaml_documents(source):
        plan = _plan_for_document(document, diagnostic_line)
        if plan is not None:
            return plan
    return None
