"""List collect cross-validation (E933)."""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from typing import Any

from docassemble_lsp.core.field_keys import FIELD_ITEM_KNOWN_KEYS
from docassemble_lsp.core.validation_config import YAMLError

_IDENTIFIER_RE = re.compile(r"[A-Za-z_]\w*")
_MAKO_BLOCK_RE = re.compile(r"<%(.*?)%>", re.DOTALL)


def _extract_field_saveas(field_item: Mapping[str, Any]) -> str | None:
    """Extract the ``field:`` target variable from a field item, handling shorthand."""
    from docassemble_lsp.core.line_helpers import _is_internal_metadata_key

    if "field" in field_item and isinstance(field_item["field"], str):
        text = field_item["field"].strip()
        return text if text else None
    for key, value in field_item.items():
        if not isinstance(key, str) or _is_internal_metadata_key(key):
            continue
        if key in FIELD_ITEM_KNOWN_KEYS:
            continue
        if isinstance(value, str):
            text = value.strip()
            return text if text else None
    return None


def _code_refs_screen(code: str, screen_bases: set[str], iterators: set[str]) -> bool:
    if not code.strip():
        return False
    from docassemble_lsp.core.line_helpers import _safe_ast_parse

    try:
        tree = _safe_ast_parse(code.strip(), mode="eval")
    except SyntaxError:
        try:
            tree = _safe_ast_parse(code.strip(), mode="exec")
        except SyntaxError:
            ids = set(_IDENTIFIER_RE.findall(code))
            return bool(ids & screen_bases or ids & iterators)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    return bool(names & screen_bases or names & iterators)


def _label_mako_refs_screen(
    label_text: str, screen_bases: set[str], iterators: set[str]
) -> bool:
    """Return True iff any Mako expression inside label_text references a
    screen-defined variable or iterator. Off-screen ${ clients } returns False.
    """
    from docassemble_lsp.core.yaml_shared import _iter_mako_expressions

    found_expr = False
    for expr, _, _ in _iter_mako_expressions(label_text):
        found_expr = True
        if _code_refs_screen(expr, screen_bases, iterators):
            return True
    for match in _MAKO_BLOCK_RE.finditer(label_text):
        found_expr = True
        if _code_refs_screen(match.group(1), screen_bases, iterators):
            return True
    # Mako line directives ("% if ...", "% for ...") inside a label
    for line in label_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("%"):
            found_expr = True
            if _code_refs_screen(stripped[1:], screen_bases, iterators):
                return True
    # If we saw Mako expressions but none referenced screen vars, this is
    # off-screen-only Mako (e.g. ${ clients }) -> not an error.
    if found_expr:
        return False
    # Fallback: no extractable expression but still has Mako; check the
    # raw label for literal screen/iterator words as a conservative fallback.
    if screen_bases or iterators:
        ids = set(_IDENTIFIER_RE.findall(label_text))
        if ids & screen_bases or ids & iterators:
            return True
    return False


def validate_list_collect_mako_labels(
    doc_keys_lower: dict[str, str],
    doc: dict[str, Any],
    line_number: int,
    input_file: str,
) -> list[YAMLError]:
    """Check that ``list collect`` blocks don't have Mako in field labels.

    Narrowed: only flag Mako that references a same-screen variable or the
    list iterator (``i``/``j``/``x`` …).  Off-screen ``${ clients }`` is
    allowed and works at runtime — see TextObject per-row rendering in
    ``docassemble.base.parse.Question.ask``.
    """
    from docassemble_lsp.core.line_helpers import (
        _is_internal_metadata_key,
        _lc_key_line,
    )
    from docassemble_lsp.core.messages import MessageCode
    from docassemble_lsp.core.validation.blocks import (
        _absolute_document_line,
        _yaml_error,
    )
    from docassemble_lsp.core.validation.fields import _contains_mako_syntax

    errors: list[YAMLError] = []

    if "list collect" in doc_keys_lower and "fields" in doc_keys_lower:
        lc_key = doc_keys_lower["list collect"]
        lc_value = doc.get(lc_key)
        if lc_value is True or isinstance(lc_value, Mapping):
            fields_key = doc_keys_lower["fields"]
            fields_value = doc.get(fields_key)
            if isinstance(fields_value, list):
                # Build screen-variable and iterator sets once for the whole
                # question block — any label referencing any of them is
                # considered screen-dependent.
                screen_bases: set[str] = set()
                iterators: set[str] = set()
                for item in fields_value:
                    if not isinstance(item, Mapping):
                        continue
                    saveas = _extract_field_saveas(item)
                    if not saveas:
                        continue
                    m = re.match(r"^([A-Za-z_]\w*)", saveas.strip())
                    if m:
                        screen_bases.add(m.group(1))
                    for im in re.finditer(r"\[([ijklmnx])\]", saveas):
                        iterators.add(im.group(1))
                # ``x`` is the generic list-collect alias (Question.ask sets
                # ``x = ...`` alongside the typed iterator).  Include it so
                # ``${ x }`` is correctly flagged while ``${ clients }`` is
                # not.
                iterators.add("x")

                for field_item in fields_value:
                    if not isinstance(field_item, Mapping):
                        continue
                    label_text: str | None = None
                    label_line: int | None = None
                    if "label" in field_item and isinstance(field_item["label"], str):
                        label_text = field_item["label"]
                        label_line = _lc_key_line(field_item, "label")
                    else:
                        for key, value in field_item.items():
                            if (
                                isinstance(key, str)
                                and not _is_internal_metadata_key(key)
                                and isinstance(value, str)
                            ):
                                label_text = key
                                label_line = _lc_key_line(field_item, key)
                                break
                    if (
                        label_text is not None
                        and label_line is not None
                        and _contains_mako_syntax(label_text)
                        and _label_mako_refs_screen(label_text, screen_bases, iterators)
                    ):
                        errors.append(
                            _yaml_error(
                                code=MessageCode.LIST_COLLECT_LABEL_HAS_MAKO,
                                line_number=_absolute_document_line(
                                    line_number, label_line
                                ),
                                file_name=input_file,
                                label=label_text,
                            )
                        )

    return errors
