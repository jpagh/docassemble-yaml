"""Field-level validators extracted from DAFields.

These validators focus on specific semantic families:

- **FieldDatatypeValidator**: datatype-specific configuration checks
  (Packet 6 — Field Datatypes And Inputs).
- **FieldChoiceValidator**: choice/button configuration checks
  (Packet 7 — Choices And Buttons).
- **FieldConditionValidator**: condition and validation key checks
  (Packet 8 — Field Conditions And Validation).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from docassemble_lsp.core.field_keys import (
    BOOLEAN_DATATYPES,
    DISABLE_OTHERS_BLOCKED_DTYPES,
    FILE_LIKE_DATATYPES,
    INPUT_TYPE_DATATYPES,
    MULTIPLE_CHOICE_DATATYPES,
    MULTIPLE_CHOICE_INPUT_TYPES,
    UNCHECK_CHECK_COMPATIBLE_DTYPES,
)
from docassemble_lsp.core.line_helpers import (
    _is_internal_metadata_key,
    _lc_key_line,
    _relative_value_line,
)
from docassemble_lsp.core.line_helpers import _safe_ast_parse
from docassemble_lsp.core.messages import MessageCode, format_message


def _validator_error(
    code: str, line_number: int = 1, **kwargs: Any
) -> tuple[str, int, str]:
    """Build a standard validator error 3-tuple."""
    return (format_message(code, **kwargs), line_number, code)


def _is_code_form(value: object) -> bool:
    """True when the value is a {code: ...} dict (ignoring ruamel internal keys).

    Used by ``FieldConditionValidator`` to match parse.py's code-ness check
    for visibility modifier conflict detection.
    """
    if not isinstance(value, dict):
        return False
    content_keys = {
        k for k in value if isinstance(k, str) and not _is_internal_metadata_key(k)
    }
    return len(content_keys) == 1 and "code" in content_keys


# ---------------------------------------------------------------------------
# FieldDatatypeValidator  (Packet 6)
# ---------------------------------------------------------------------------


class FieldDatatypeValidator:
    """Validates datatype-specific field configuration (Packet 6)."""

    _FILE_SPECIFIC_KEYS = (
        "maximum image size",
        "image upload type",
        "accept",
        "file css class",
        "allow privileges",
        "allow users",
        "persistent",
        "private",
    )

    def __init__(self, field_item: dict[str, Any]) -> None:
        self.errors: list[tuple[str, int, str]] = []
        datatype = field_item.get("datatype")
        input_type = field_item.get("input type")
        datatype_normalized = (
            datatype.strip().lower() if isinstance(datatype, str) else None
        )
        input_type_normalized = (
            input_type.strip().lower() if isinstance(input_type, str) else None
        )

        if (
            input_type_normalized == "hidden"
            and datatype_normalized in FILE_LIKE_DATATYPES
        ):
            self.errors.append(
                _validator_error(
                    MessageCode.HIDDEN_FIELD_INVALID_DATATYPE,
                    _lc_key_line(field_item, "datatype"),
                )
            )

        if "object labeler" in field_item and not (
            isinstance(datatype_normalized, str)
            and datatype_normalized.startswith("object")
        ):
            self.errors.append(
                _validator_error(
                    MessageCode.OBJECT_LABELER_REQUIRES_OBJECT_DATATYPE,
                    _lc_key_line(field_item, "object labeler"),
                )
            )

        if input_type_normalized == "ajax":
            if "action" not in field_item:
                self.errors.append(
                    _validator_error(
                        MessageCode.AJAX_FIELD_MISSING_ACTION,
                        _lc_key_line(field_item, "input type"),
                    )
                )
            elif "choices" in field_item or "code" in field_item:
                self.errors.append(
                    _validator_error(
                        MessageCode.AJAX_FIELD_CANNOT_DECLARE_CHOICES,
                        _lc_key_line(field_item, "input type"),
                    )
                )

        requires_choices = (
            datatype_normalized in MULTIPLE_CHOICE_DATATYPES
            or input_type_normalized in MULTIPLE_CHOICE_INPUT_TYPES
        )
        if (
            requires_choices
            and "choices" not in field_item
            and "code" not in field_item
        ):
            anchor_key = (
                "datatype"
                if datatype_normalized in MULTIPLE_CHOICE_DATATYPES
                else "input type"
            )
            self.errors.append(
                _validator_error(
                    MessageCode.MULTIPLE_CHOICE_FIELD_MISSING_CHOICES,
                    _lc_key_line(field_item, anchor_key),
                )
            )

        if datatype_normalized in BOOLEAN_DATATYPES and (
            "choices" in field_item or "code" in field_item
        ):
            anchor_key = "choices" if "choices" in field_item else "code"
            self.errors.append(
                _validator_error(
                    MessageCode.BOOLEAN_DATATYPE_CHOICES_IGNORED,
                    _lc_key_line(field_item, anchor_key),
                    datatype=datatype_normalized,
                )
            )

        if datatype_normalized == "range" and not (
            "min" in field_item and "max" in field_item
        ):
            self.errors.append(
                _validator_error(
                    MessageCode.RANGE_MISSING_MIN_MAX,
                    _lc_key_line(field_item, "datatype"),
                )
            )

        if (
            datatype_normalized is not None
            and datatype_normalized not in FILE_LIKE_DATATYPES
        ):
            for file_key in self._FILE_SPECIFIC_KEYS:
                if file_key in field_item:
                    self.errors.append(
                        _validator_error(
                            MessageCode.FILE_KEY_WITHOUT_FILE_DATATYPE,
                            _lc_key_line(field_item, file_key),
                            key_name=file_key,
                            datatype=datatype_normalized,
                        )
                    )
        elif datatype_normalized is None:
            for file_key in self._FILE_SPECIFIC_KEYS:
                if file_key in field_item:
                    self.errors.append(
                        _validator_error(
                            MessageCode.FILE_KEY_WITHOUT_FILE_DATATYPE,
                            _lc_key_line(field_item, file_key),
                            key_name=file_key,
                            datatype="<unset>",
                        )
                    )

        if (
            datatype_normalized in INPUT_TYPE_DATATYPES
            and input_type_normalized != datatype_normalized
        ):
            self.errors.append(
                _validator_error(
                    MessageCode.DATATYPE_PREFER_INPUT_TYPE,
                    _lc_key_line(field_item, "datatype"),
                    datatype=datatype_normalized,
                )
            )

        if "rows" in field_item:
            dt_ok = datatype_normalized in ("area", "multiselect", "object_multiselect")
            it_ok = input_type_normalized == "area"
            if not dt_ok and not it_ok:
                self.errors.append(
                    _validator_error(
                        MessageCode.ROWS_WITHOUT_COMPATIBLE_TYPE,
                        _lc_key_line(field_item, "rows"),
                        input_type=input_type_normalized or "<unset>",
                        datatype=datatype_normalized or "<unset>",
                    )
                )


# ---------------------------------------------------------------------------
# FieldChoiceValidator  (Packet 7)
# ---------------------------------------------------------------------------


class FieldChoiceValidator:
    """Validates choice/button field configuration (Packet 7)."""

    def __init__(self, field_item: dict[str, Any]) -> None:
        self.errors: list[tuple[str, int, str]] = []

        datatype = field_item.get("datatype")
        datatype_normalized = (
            datatype.strip().lower() if isinstance(datatype, str) else None
        )

        # shuffle must be boolean
        if "shuffle" in field_item and not isinstance(field_item["shuffle"], bool):
            self.errors.append(
                _validator_error(
                    MessageCode.SHUFFLE_NOT_BOOLEAN,
                    _lc_key_line(field_item, "shuffle"),
                )
            )

        # disable others
        if "disable others" in field_item:
            if (
                datatype_normalized is not None
                and datatype_normalized in DISABLE_OTHERS_BLOCKED_DTYPES
            ):
                self.errors.append(
                    _validator_error(
                        MessageCode.DISABLE_OTHERS_INCOMPATIBLE_DATATYPE,
                        _lc_key_line(field_item, "disable others"),
                        datatype=datatype_normalized,
                    )
                )
            if not isinstance(field_item["disable others"], (bool, list)):
                self.errors.append(
                    _validator_error(
                        MessageCode.DISABLE_OTHERS_INVALID_TYPE,
                        _lc_key_line(field_item, "disable others"),
                    )
                )

        # uncheck others
        if "uncheck others" in field_item:
            if (
                datatype_normalized is not None
                and datatype_normalized not in UNCHECK_CHECK_COMPATIBLE_DTYPES
            ):
                self.errors.append(
                    _validator_error(
                        MessageCode.UNCHECK_OTHERS_REQUIRES_YESNO,
                        _lc_key_line(field_item, "uncheck others"),
                    )
                )
            if not isinstance(field_item["uncheck others"], (bool, list)):
                self.errors.append(
                    _validator_error(
                        MessageCode.UNCHECK_OTHERS_INVALID_TYPE,
                        _lc_key_line(field_item, "uncheck others"),
                    )
                )

        # check others
        if "check others" in field_item:
            if (
                datatype_normalized is not None
                and datatype_normalized not in UNCHECK_CHECK_COMPATIBLE_DTYPES
            ):
                self.errors.append(
                    _validator_error(
                        MessageCode.CHECK_OTHERS_REQUIRES_YESNO,
                        _lc_key_line(field_item, "check others"),
                    )
                )
            if not isinstance(field_item["check others"], (bool, list)):
                self.errors.append(
                    _validator_error(
                        MessageCode.CHECK_OTHERS_INVALID_TYPE,
                        _lc_key_line(field_item, "check others"),
                    )
                )

        # all of the above requires checkboxes/object_checkboxes
        if "all of the above" in field_item:
            if datatype_normalized is not None and datatype_normalized not in {
                "checkboxes",
                "object_checkboxes",
            }:
                self.errors.append(
                    _validator_error(
                        MessageCode.ALL_OF_THE_ABOVE_INCOMPATIBLE_DATATYPE,
                        _lc_key_line(field_item, "all of the above"),
                        datatype=datatype_normalized,
                    )
                )

        # none of the above requires checkboxes/object_checkboxes/object_radio
        if "none of the above" in field_item:
            if datatype_normalized is not None and datatype_normalized not in {
                "checkboxes",
                "object_checkboxes",
                "object_radio",
            }:
                self.errors.append(
                    _validator_error(
                        MessageCode.NONE_OF_THE_ABOVE_INCOMPATIBLE_DATATYPE,
                        _lc_key_line(field_item, "none of the above"),
                        datatype=datatype_normalized,
                    )
                )


# ---------------------------------------------------------------------------
# FieldConditionValidator  (Packet 8)
# ---------------------------------------------------------------------------


class FieldConditionValidator:
    """Validates field condition and validation keys (Packet 8)."""

    def __init__(self, field_item: dict[str, Any]) -> None:
        self.errors: list[tuple[str, int, str]] = []

        if "validate" in field_item:
            val_value = field_item["validate"]
            if not isinstance(val_value, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.VALIDATE_TYPE,
                        _lc_key_line(field_item, "validate"),
                        value_type=type(val_value).__name__,
                    )
                )
            else:
                try:
                    _safe_ast_parse(val_value, mode="eval")
                except SyntaxError as ex:
                    lineno = ex.lineno or 1
                    self.errors.append(
                        _validator_error(
                            MessageCode.VALIDATE_SYNTAX,
                            _relative_value_line(field_item, "validate", lineno),
                            message=ex.msg or str(ex),
                        )
                    )

        if "validation messages" in field_item:
            vm_value = field_item["validation messages"]
            if not isinstance(vm_value, Mapping):
                self.errors.append(
                    _validator_error(
                        MessageCode.VALIDATION_MESSAGES_TYPE,
                        _lc_key_line(field_item, "validation messages"),
                    )
                )
            else:
                for vm_key, vm_val in vm_value.items():
                    if _is_internal_metadata_key(vm_key):
                        continue
                    if not (isinstance(vm_key, str) and isinstance(vm_val, str)):
                        self.errors.append(
                            _validator_error(
                                MessageCode.VALIDATION_MESSAGES_ENTRY_TYPE,
                                _lc_key_line(vm_value, vm_key),
                            )
                        )

        if "trigger at" in field_item:
            ta_value = field_item["trigger at"]
            if not isinstance(ta_value, int) or ta_value < 2:
                self.errors.append(
                    _validator_error(
                        MessageCode.TRIGGER_AT_TYPE,
                        _lc_key_line(field_item, "trigger at"),
                        value_repr=repr(ta_value),
                    )
                )

        if "help generator" in field_item:
            hg_value = field_item["help generator"]
            if not isinstance(hg_value, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.HELP_GENERATOR_TYPE,
                        _lc_key_line(field_item, "help generator"),
                        value_type=type(hg_value).__name__,
                    )
                )
            else:
                try:
                    _safe_ast_parse(hg_value, mode="eval")
                except SyntaxError as ex:
                    lineno = ex.lineno or 1
                    self.errors.append(
                        _validator_error(
                            MessageCode.HELP_GENERATOR_SYNTAX,
                            _relative_value_line(field_item, "help generator", lineno),
                            message=ex.msg or str(ex),
                        )
                    )

        if "image generator" in field_item:
            ig_value = field_item["image generator"]
            if not isinstance(ig_value, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.IMAGE_GENERATOR_TYPE,
                        _lc_key_line(field_item, "image generator"),
                        value_type=type(ig_value).__name__,
                    )
                )
            else:
                try:
                    _safe_ast_parse(ig_value, mode="eval")
                except SyntaxError as ex:
                    lineno = ex.lineno or 1
                    self.errors.append(
                        _validator_error(
                            MessageCode.IMAGE_GENERATOR_SYNTAX,
                            _relative_value_line(field_item, "image generator", lineno),
                            message=ex.msg or str(ex),
                        )
                    )

        if "using" in field_item:
            using_value = field_item["using"]
            datatype = field_item.get("datatype")
            if isinstance(datatype, str) and datatype.strip().lower() in (
                "ml",
                "mlarea",
            ):
                if not isinstance(using_value, str):
                    self.errors.append(
                        _validator_error(
                            MessageCode.ML_USING_TYPE,
                            _lc_key_line(field_item, "using"),
                            value_type=type(using_value).__name__,
                        )
                    )

        if "keep for training" in field_item:
            kft_value = field_item["keep for training"]
            datatype = field_item.get("datatype")
            if isinstance(datatype, str) and datatype.strip().lower() in (
                "ml",
                "mlarea",
            ):
                if not isinstance(kft_value, (bool, str)):
                    self.errors.append(
                        _validator_error(
                            MessageCode.KEEP_FOR_TRAINING_TYPE,
                            _lc_key_line(field_item, "keep for training"),
                            value_type=type(kft_value).__name__,
                        )
                    )

        # --- Visibility modifier cross-key conflicts (matching parse.py) ---
        _NON_JS_VISIBILITY = frozenset(
            {"show if", "hide if", "enable if", "disable if"}
        )
        _JS_VISIBILITY = frozenset(
            {"js show if", "js hide if", "js enable if", "js disable if"}
        )

        present_keys = set(field_item)
        present_non_js = _NON_JS_VISIBILITY & present_keys
        present_js = _JS_VISIBILITY & present_keys

        # JS + non-JS mixing is always an error (parse.py lines 4209-4212, 4265-4268)
        if present_non_js and present_js:
            for key in sorted(present_non_js):
                for other in sorted(present_js):
                    self.errors.append(
                        _validator_error(
                            MessageCode.VISIBILITY_JS_NON_JS_MIX,
                            _lc_key_line(field_item, key),
                            key1=key,
                            key2=other,
                        )
                    )

        # Same-group cross-modifier conflicts (conditional on code-ness)
        # parse.py:4196-4203, 4252-4259
        for group in (_NON_JS_VISIBILITY, _JS_VISIBILITY):
            present = group & present_keys
            for key in sorted(present):
                for other in sorted(present):
                    if key < other:  # each unordered pair once
                        if field_item[key] is None or field_item[other] is None:
                            continue  # value not yet set — can't determine code-ness
                        if _is_code_form(field_item[key]) == _is_code_form(
                            field_item[other]
                        ):
                            self.errors.append(
                                _validator_error(
                                    MessageCode.VISIBILITY_MODIFIER_CONFLICT,
                                    _lc_key_line(field_item, key),
                                    key1=key,
                                    key2=other,
                                )
                            )


__all__ = [
    "FieldChoiceValidator",
    "FieldConditionValidator",
    "FieldDatatypeValidator",
]
