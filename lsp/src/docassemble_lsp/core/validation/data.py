"""Data block and ML-related validators (E928-E930, E531/E532)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from docassemble_lsp.core.messages import MessageCode
from docassemble_lsp.core.validation_config import YAMLError


def validate_data_block(
    doc_keys_lower: dict[str, str],
    doc: dict[str, Any],
    line_number: int,
    input_file: str,
) -> list[YAMLError]:
    """Cross-validate ``data`` block shapes (E928-E930)."""
    from docassemble_lsp.core.line_helpers import _lc_key_line
    from docassemble_lsp.core.validation.blocks import _absolute_document_line
    from docassemble_lsp.core.validation.blocks import _yaml_error

    errors: list[YAMLError] = []
    has_data = "data" in doc_keys_lower
    if has_data and "variable name" in doc_keys_lower:
        data_key = doc_keys_lower["data"]
        data_value = doc.get(data_key)
        if data_value is not None and not isinstance(data_value, (Mapping, list)):
            errors.append(
                _yaml_error(
                    code=MessageCode.DATA_TYPE,
                    line_number=_absolute_document_line(
                        line_number, _lc_key_line(doc, data_key)
                    ),
                    file_name=input_file,
                )
            )
        var_name_key = doc_keys_lower["variable name"]
        var_name_value = doc.get(var_name_key)
        if var_name_value is not None and not isinstance(var_name_value, str):
            errors.append(
                _yaml_error(
                    code=MessageCode.DATA_VARIABLE_NAME_TYPE,
                    line_number=_absolute_document_line(
                        line_number, _lc_key_line(doc, var_name_key)
                    ),
                    file_name=input_file,
                )
            )
        if "use objects" in doc_keys_lower:
            uo_key = doc_keys_lower["use objects"]
            uo_value = doc.get(uo_key)
            if uo_value is not None and not isinstance(uo_value, (bool, str)):
                errors.append(
                    _yaml_error(
                        code=MessageCode.DATA_USE_OBJECTS_TYPE,
                        line_number=_absolute_document_line(
                            line_number, _lc_key_line(doc, uo_key)
                        ),
                        file_name=input_file,
                    )
                )
    return errors
