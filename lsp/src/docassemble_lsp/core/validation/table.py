"""Table block validators (E921-E927)."""

from __future__ import annotations

from collections.abc import Mapping

from docassemble_lsp.core.field_validators import _validator_error
from docassemble_lsp.core.line_helpers import _lc_key_line
from docassemble_lsp.core.messages import MessageCode
from docassemble_lsp.core.validation.fields import _seq_item_line
from docassemble_lsp.core.validation_config import YAMLError


class TableBlockDirective:
    """Validator for the value of the ``table`` key.

    Docassemble parser-backed: ``table`` must be a string (variable name) or
    a dict (when combined with ``rows`` and ``columns`` in the same block).
    A scalar other than string is invalid.
    """

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, (str, dict)):
            self.errors = [_validator_error(MessageCode.TABLE_TYPE)]


def validate_table_block_in_doc(
    doc: Mapping,
    doc_keys_lower: dict[str, str],
    line_number: int,
    input_file: str,
) -> list[YAMLError]:
    """Cross-validate table/rows/columns keys in a document (E921-E927).

    Called from ``find_errors_from_string`` in ``orchestrator.py``.
    Returns a list of errors (may be empty).
    """
    from docassemble_lsp.core.validation.blocks import _absolute_document_line, _yaml_error

    errors: list[YAMLError] = []

    has_table = "table" in doc_keys_lower
    has_rows = "rows" in doc_keys_lower
    has_cols = "columns" in doc_keys_lower

    if (has_table or has_rows or has_cols) and not (has_table and has_rows and has_cols):
        table_key = doc_keys_lower.get("table") or doc_keys_lower.get("rows") or doc_keys_lower.get("columns")
        errors.append(
            _yaml_error(
                code=MessageCode.TABLE_REQUIRED_KEYS,
                line_number=_absolute_document_line(line_number, _lc_key_line(doc, table_key)),
                file_name=input_file,
            )
        )

    if has_rows:
        rows_key = doc_keys_lower["rows"]
        rows_value = doc.get(rows_key)
        if rows_value is not None and not isinstance(rows_value, str):
            errors.append(
                _yaml_error(
                    code=MessageCode.TABLE_ROWS_TYPE,
                    line_number=_absolute_document_line(line_number, _lc_key_line(doc, rows_key)),
                    file_name=input_file,
                )
            )

    if has_cols:
        cols_key = doc_keys_lower["columns"]
        cols_value = doc.get(cols_key)
        if cols_value is not None and not isinstance(cols_value, list):
            errors.append(
                _yaml_error(
                    code=MessageCode.TABLE_COLUMNS_TYPE,
                    line_number=_absolute_document_line(line_number, _lc_key_line(doc, cols_key)),
                    file_name=input_file,
                )
            )
        elif isinstance(cols_value, list):
            for idx, col in enumerate(cols_value):
                if not isinstance(col, Mapping):
                    errors.append(
                        _yaml_error(
                            code=MessageCode.TABLE_COLUMN_ITEM_TYPE,
                            line_number=_absolute_document_line(line_number, _seq_item_line(cols_value, idx)),
                            file_name=input_file,
                        )
                    )
                else:
                    col_line = _seq_item_line(cols_value, idx)
                    if "header" in col and not isinstance(col["header"], str):
                        errors.append(
                            _yaml_error(
                                code=MessageCode.TABLE_COLUMN_HEADER_TYPE,
                                line_number=_absolute_document_line(line_number, col_line),
                                file_name=input_file,
                            )
                        )
                    if "cell" in col and not isinstance(col["cell"], str):
                        errors.append(
                            _yaml_error(
                                code=MessageCode.TABLE_COLUMN_CELL_TYPE,
                                line_number=_absolute_document_line(line_number, col_line),
                                file_name=input_file,
                            )
                        )

    return errors
