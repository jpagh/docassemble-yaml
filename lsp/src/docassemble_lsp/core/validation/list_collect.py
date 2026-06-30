"""List collect cross-validation (E933)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from docassemble_lsp.core.validation_config import YAMLError


def validate_list_collect_mako_labels(
    doc_keys_lower: dict[str, str],
    doc: dict[str, Any],
    line_number: int,
    input_file: str,
) -> list[YAMLError]:
    """Check that ``list collect`` blocks don't have Mako in field labels."""
    from docassemble_lsp.core.line_helpers import _is_internal_metadata_key, _lc_key_line
    from docassemble_lsp.core.messages import MessageCode
    from docassemble_lsp.core.validation.blocks import _absolute_document_line, _yaml_error
    from docassemble_lsp.core.validation.fields import _contains_mako_syntax

    errors: list[YAMLError] = []

    if "list collect" in doc_keys_lower and "fields" in doc_keys_lower:
        lc_key = doc_keys_lower["list collect"]
        lc_value = doc.get(lc_key)
        if lc_value is True or isinstance(lc_value, Mapping):
            fields_key = doc_keys_lower["fields"]
            fields_value = doc.get(fields_key)
            if isinstance(fields_value, list):
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
                            if isinstance(key, str) and not _is_internal_metadata_key(key) and isinstance(value, str):
                                label_text = key
                                label_line = _lc_key_line(field_item, key)
                                break
                    if label_text is not None and label_line is not None and _contains_mako_syntax(label_text):
                        errors.append(
                            _yaml_error(
                                code=MessageCode.LIST_COLLECT_LABEL_HAS_MAKO,
                                line_number=_absolute_document_line(line_number, label_line),
                                file_name=input_file,
                                label=label_text,
                            )
                        )

    return errors
