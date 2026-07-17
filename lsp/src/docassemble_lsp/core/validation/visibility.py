"""Visibility/nesting validators (E535, E536, C106).

These checks handle field visibility nesting, show-if conflicts,
and cross-document guard matching.
"""

from __future__ import annotations

from typing import Any

from docassemble_lsp.core.validation_config import YAMLError


def validate_nesting_depth(
    doc: dict[str, Any],
    line_number: int,
    input_file: str,
) -> list[YAMLError]:
    """Check screen visibility nesting depth (C106)."""
    from docassemble_lsp.core.messages import MessageCode
    from docassemble_lsp.core.validation.blocks import (
        _absolute_document_line,
        _lc_line,
        _yaml_error,
    )
    from docassemble_lsp.core.validation.blocks import (
        _max_screen_visibility_nesting_depth as _max_nesting,
    )

    errors: list[YAMLError] = []
    nesting_depth, nesting_line = _max_nesting(doc)
    if nesting_depth > 2:
        errors.append(
            _yaml_error(
                code=MessageCode.NESTED_VISIBILITY_LOGIC,
                line_number=_absolute_document_line(line_number, nesting_line or _lc_line(doc)),
                file_name=input_file,
                depth=nesting_depth,
            )
        )
    return errors


def collect_conditional_fields(
    doc: dict[str, Any],
    line_number: int,
) -> list[dict[str, Any]]:
    from docassemble_lsp.core.validation.blocks import (
        _extract_conditional_fields_from_doc,
    )

    return _extract_conditional_fields_from_doc(doc, line_number)
