from __future__ import annotations


def _flatten(*groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(key for group in groups for key in group)


FIELD_OBJECT_KEYS = ("object", "object multiselect", "object radio")

FIELD_MODIFIER_KEYS = (
    "code",
    "default",
    "default value",
    "hint",
    "help",
    "label",
    "datatype",
    "choices",
    "validation code",
    "show if",
    "hide if",
    "js show if",
    "js hide if",
    "enable if",
    "disable if",
    "js enable if",
    "js disable if",
)

FIELD_MAKO_KEYS = ("default", "hint", "label", "note")
FIELD_JS_MODIFIER_KEYS = ("js show if", "js hide if", "js enable if", "js disable if")
FIELD_PY_MODIFIER_KEYS = ("show if", "hide if", "enable if", "disable if")

FIELDS_ITEM_BASE_TEMPLATE_KEYS = ("label", "hint", "under text")

FIELDS_ITEM_BASE_STRING_KEYS = (
    "field",
    "help",
    "action",
    *FIELD_OBJECT_KEYS,
    "file css class",
    "group",
)

FIELDS_ITEM_NOTE_KEYS = ("note", "html", "raw html")

FIELDS_ITEM_CHOICE_VALUE_KEYS = ("choices", "exclude")
FIELDS_ITEM_CHOICE_DEFAULT_KEYS = ("default", "default value", "address autocomplete")
FIELDS_ITEM_CHOICE_VALUE_TEMPLATE_KEYS = ("value",)
FIELDS_ITEM_CHOICE_BOOLEAN_KEYS = ("all of the above", "none of the above")
FIELDS_ITEM_CHOICE_TOGGLE_KEYS = ("shuffle",)

FIELDS_ITEM_CONDITION_EXPRESSION_KEYS = FIELD_PY_MODIFIER_KEYS
FIELDS_ITEM_CONDITION_JS_KEYS = FIELD_JS_MODIFIER_KEYS
FIELDS_ITEM_CONDITION_BOOLEAN_KEYS = ("disabled", "required", "read only")

FIELDS_ITEM_LAYOUT_OBJECT_KEYS = ("grid", "item grid", "field metadata")
FIELDS_ITEM_LAYOUT_BOOLEAN_KEYS = ("label above field", "floating label")
FIELDS_ITEM_LAYOUT_PYTHON_EXPR_KEYS = ("rows",)

FIELDS_ITEM_LAYOUT_STRING_KEYS = (
    "min",
    "max",
    "minlength",
    "maxlength",
    "step",
    "scale",
    "inline",
    "inline width",
    "currency symbol",
    "css class",
)

FIELDS_ITEM_FILE_STRING_KEYS = ("maximum image size", "image upload type", "accept")
FIELDS_ITEM_FILE_COMPLEX_KEYS = ("allow privileges", "allow users")
FIELDS_ITEM_FILE_BOOLEAN_KEYS = ("persistent", "private")

# Datatypes that accept file-like upload fields
FILE_LIKE_DATATYPES = frozenset({"file", "files", "camera", "user", "environment", "camcorder", "microphone"})

# Datatype values that are really input-type concerns (remapped by the parser at parse time)
INPUT_TYPE_DATATYPES = frozenset(
    {
        "area",
        "hidden",
        "ajax",
        "radio",
        "dropdown",
        "pulldown",
        "combobox",
        "datalist",
    }
)

# Datatypes that shadow choices/code with a built-in boolean widget
# (choices/code are silently ignored at runtime by docassemble.base.parse)
BOOLEAN_DATATYPES = frozenset(
    {
        "yesno",
        "yesnowide",
        "yesnoradio",
        "noyes",
        "noyeswide",
        "noyesradio",
        "yesnomaybe",
        "noyesmaybe",
    }
)

# Datatypes that require choices or code (multiple choice)
MULTIPLE_CHOICE_DATATYPES = frozenset(
    {
        "object",
        "object_radio",
        "multiselect",
        "object_multiselect",
        "checkboxes",
        "object_checkboxes",
    }
)

# Input types that require choices or code (multiple choice)
MULTIPLE_CHOICE_INPUT_TYPES = frozenset({"radio", "combobox", "datalist", "dropdown"})

# Datatypes where disable others is blocked
DISABLE_OTHERS_BLOCKED_DTYPES = frozenset(
    {
        "file",
        "files",
        "range",
        "multiselect",
        "checkboxes",
        "camera",
        "user",
        "environment",
        "camcorder",
        "microphone",
        "object_multiselect",
        "object_checkboxes",
    }
)

# Datatypes compatible with uncheck others / check others
UNCHECK_CHECK_COMPATIBLE_DTYPES = frozenset({"yesno", "yesnowide", "noyes", "noyeswide"})

# Field keys restricted to specific datatypes
# Maps field key -> set of compatible datatype values
# Note: "rows" is intentionally absent here — it's handled by explicit logic
# in _filter_property_candidates that also considers input type: area.
FIELD_KEY_COMPATIBLE_DATATYPES: dict[str, frozenset[str]] = {
    "none of the above": frozenset({"checkboxes", "object_checkboxes", "object_radio"}),
    "all of the above": frozenset({"checkboxes", "object_checkboxes"}),
    "uncheck others": UNCHECK_CHECK_COMPATIBLE_DTYPES,
    "check others": UNCHECK_CHECK_COMPATIBLE_DTYPES,
    "using": frozenset({"ml", "mlarea"}),
    "keep for training": frozenset({"ml", "mlarea"}),
}

# Field keys blocked on specific datatypes (inverse pattern)
FIELD_KEY_BLOCKED_DATATYPES: dict[str, frozenset[str]] = {
    "disable others": DISABLE_OTHERS_BLOCKED_DTYPES,
}

FIELDS_ITEM_SPECIAL_PYTHON_EXPR_KEYS = ("code", "validate", "object labeler", "help generator", "image generator")
FIELDS_ITEM_SPECIAL_STRING_KEYS = ("validation code",)
FIELDS_ITEM_SPECIAL_BOOLEAN_OR_ARRAY_KEYS = ("disable others", "uncheck others", "check others")
FIELDS_ITEM_SPECIAL_OBJECT_KEYS = ("validation messages",)
FIELDS_ITEM_SPECIAL_INTEGER_KEYS = ("trigger at",)
FIELDS_ITEM_SPECIAL_ENUM_KEYS = ("datatype", "input type")

# Keys only valid for ml/mlarea datatypes (parse.py parse_fields)
FIELDS_ITEM_ML_KEYS = ("using", "keep for training")

FIELD_ITEM_KNOWN_KEYS = frozenset(
    _flatten(
        FIELDS_ITEM_BASE_TEMPLATE_KEYS,
        FIELDS_ITEM_BASE_STRING_KEYS,
        FIELDS_ITEM_NOTE_KEYS,
        FIELDS_ITEM_CHOICE_VALUE_KEYS,
        FIELDS_ITEM_CHOICE_DEFAULT_KEYS,
        FIELDS_ITEM_CHOICE_VALUE_TEMPLATE_KEYS,
        FIELDS_ITEM_CHOICE_BOOLEAN_KEYS,
        FIELDS_ITEM_CHOICE_TOGGLE_KEYS,
        FIELDS_ITEM_CONDITION_EXPRESSION_KEYS,
        FIELDS_ITEM_CONDITION_JS_KEYS,
        FIELDS_ITEM_CONDITION_BOOLEAN_KEYS,
        FIELDS_ITEM_LAYOUT_OBJECT_KEYS,
        FIELDS_ITEM_LAYOUT_BOOLEAN_KEYS,
        FIELDS_ITEM_LAYOUT_PYTHON_EXPR_KEYS,
        FIELDS_ITEM_LAYOUT_STRING_KEYS,
        FIELDS_ITEM_FILE_STRING_KEYS,
        FIELDS_ITEM_FILE_COMPLEX_KEYS,
        FIELDS_ITEM_FILE_BOOLEAN_KEYS,
        FIELDS_ITEM_SPECIAL_PYTHON_EXPR_KEYS,
        FIELDS_ITEM_SPECIAL_STRING_KEYS,
        FIELDS_ITEM_SPECIAL_BOOLEAN_OR_ARRAY_KEYS,
        FIELDS_ITEM_SPECIAL_OBJECT_KEYS,
        FIELDS_ITEM_SPECIAL_INTEGER_KEYS,
        FIELDS_ITEM_SPECIAL_ENUM_KEYS,
        FIELDS_ITEM_ML_KEYS,
    )
)
FIELD_ITEM_KNOWN_KEYS_LOWER = frozenset(key.lower() for key in FIELD_ITEM_KNOWN_KEYS)


__all__ = [
    "FIELD_ITEM_KNOWN_KEYS",
    "FIELD_ITEM_KNOWN_KEYS_LOWER",
    "FIELD_JS_MODIFIER_KEYS",
    "FIELD_MAKO_KEYS",
    "FIELD_MODIFIER_KEYS",
    "FIELD_OBJECT_KEYS",
    "FIELD_PY_MODIFIER_KEYS",
    "FIELDS_ITEM_BASE_STRING_KEYS",
    "FIELDS_ITEM_BASE_TEMPLATE_KEYS",
    "FIELDS_ITEM_CHOICE_BOOLEAN_KEYS",
    "FIELDS_ITEM_CHOICE_DEFAULT_KEYS",
    "FIELDS_ITEM_CHOICE_TOGGLE_KEYS",
    "FIELDS_ITEM_CHOICE_VALUE_KEYS",
    "FIELDS_ITEM_CHOICE_VALUE_TEMPLATE_KEYS",
    "FIELDS_ITEM_CONDITION_BOOLEAN_KEYS",
    "FIELDS_ITEM_CONDITION_EXPRESSION_KEYS",
    "FIELDS_ITEM_CONDITION_JS_KEYS",
    "FIELDS_ITEM_FILE_BOOLEAN_KEYS",
    "FIELDS_ITEM_FILE_COMPLEX_KEYS",
    "FIELDS_ITEM_FILE_STRING_KEYS",
    "FIELDS_ITEM_LAYOUT_BOOLEAN_KEYS",
    "FIELDS_ITEM_LAYOUT_OBJECT_KEYS",
    "FIELDS_ITEM_LAYOUT_PYTHON_EXPR_KEYS",
    "FIELDS_ITEM_LAYOUT_STRING_KEYS",
    "FIELDS_ITEM_NOTE_KEYS",
    "FIELDS_ITEM_ML_KEYS",
    "FIELDS_ITEM_SPECIAL_BOOLEAN_OR_ARRAY_KEYS",
    "FIELDS_ITEM_SPECIAL_ENUM_KEYS",
    "FIELDS_ITEM_SPECIAL_INTEGER_KEYS",
    "FIELDS_ITEM_SPECIAL_OBJECT_KEYS",
    "FIELDS_ITEM_SPECIAL_PYTHON_EXPR_KEYS",
    "FIELDS_ITEM_SPECIAL_STRING_KEYS",
    "FILE_LIKE_DATATYPES",
    "INPUT_TYPE_DATATYPES",
    "BOOLEAN_DATATYPES",
    "MULTIPLE_CHOICE_DATATYPES",
    "MULTIPLE_CHOICE_INPUT_TYPES",
    "DISABLE_OTHERS_BLOCKED_DTYPES",
    "UNCHECK_CHECK_COMPATIBLE_DTYPES",
    "FIELD_KEY_COMPATIBLE_DATATYPES",
    "FIELD_KEY_BLOCKED_DATATYPES",
]
