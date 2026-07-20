"""Packet 1 – Baseline Inventory drift tests.

These tests codify the declared key inventories and fail fast when a centralized
list drifts from its stated composition.  No semantic behavior is tested here;
the goal is to keep the inventory honest.
"""

from __future__ import annotations

from docassemble_lsp.core.field_keys import (
    FIELD_ITEM_KNOWN_KEYS,
    FIELDS_ITEM_BASE_STRING_KEYS,
    FIELDS_ITEM_BASE_TEMPLATE_KEYS,
    FIELDS_ITEM_CHOICE_BOOLEAN_KEYS,
    FIELDS_ITEM_CHOICE_DEFAULT_KEYS,
    FIELDS_ITEM_CHOICE_TOGGLE_KEYS,
    FIELDS_ITEM_CHOICE_VALUE_KEYS,
    FIELDS_ITEM_CHOICE_VALUE_TEMPLATE_KEYS,
    FIELDS_ITEM_CONDITION_BOOLEAN_KEYS,
    FIELDS_ITEM_CONDITION_EXPRESSION_KEYS,
    FIELDS_ITEM_CONDITION_JS_KEYS,
    FIELDS_ITEM_FILE_BOOLEAN_KEYS,
    FIELDS_ITEM_FILE_COMPLEX_KEYS,
    FIELDS_ITEM_FILE_STRING_KEYS,
    FIELDS_ITEM_LAYOUT_BOOLEAN_KEYS,
    FIELDS_ITEM_LAYOUT_OBJECT_KEYS,
    FIELDS_ITEM_LAYOUT_PYTHON_EXPR_KEYS,
    FIELDS_ITEM_LAYOUT_STRING_KEYS,
    FIELDS_ITEM_ML_KEYS,
    FIELDS_ITEM_NOTE_KEYS,
    FIELDS_ITEM_SPECIAL_BOOLEAN_OR_ARRAY_KEYS,
    FIELDS_ITEM_SPECIAL_ENUM_KEYS,
    FIELDS_ITEM_SPECIAL_INTEGER_KEYS,
    FIELDS_ITEM_SPECIAL_OBJECT_KEYS,
    FIELDS_ITEM_SPECIAL_PYTHON_EXPR_KEYS,
    FIELDS_ITEM_SPECIAL_STRING_KEYS,
)
from docassemble_lsp.core.schema import load_schema
from docassemble_lsp.core.validation import all_dict_keys

# ---------------------------------------------------------------------------
# Field item key inventory
# ---------------------------------------------------------------------------

_FIELD_ITEM_SUBGROUPS: tuple[tuple[str, ...], ...] = (
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


def test_field_item_known_keys_equals_subgroup_union() -> None:
    """FIELD_ITEM_KNOWN_KEYS must be the exact union of all declared sub-groups.

    Fails when a key is added to a sub-group without flowing through to the
    composite frozenset, or when a key lands in the composite set without
    belonging to any declared sub-group.
    """
    union = frozenset(key for group in _FIELD_ITEM_SUBGROUPS for key in group)

    extra_in_composite = FIELD_ITEM_KNOWN_KEYS - union
    missing_from_composite = union - FIELD_ITEM_KNOWN_KEYS

    assert not extra_in_composite, (
        f"Keys in FIELD_ITEM_KNOWN_KEYS but in no sub-group: {sorted(extra_in_composite)}"
    )
    assert not missing_from_composite, (
        f"Keys in a sub-group but missing from FIELD_ITEM_KNOWN_KEYS: {sorted(missing_from_composite)}"
    )


def test_field_item_subgroups_have_no_duplicates() -> None:
    """No key should appear in more than one sub-group (avoids silent masking)."""
    seen: dict[str, str] = {}
    for group in _FIELD_ITEM_SUBGROUPS:
        for key in group:
            if key in seen:
                raise AssertionError(
                    f"Key {key!r} appears in multiple sub-groups (also seen in {seen[key]!r})"
                )
            seen[key] = repr(group[:3])  # first few keys as identification


def test_ml_field_keys_included_in_known_keys() -> None:
    """ML-specific field keys must be present in FIELD_ITEM_KNOWN_KEYS.

    These are valid only for ml/mlarea datatypes but must not trigger false-
    positive unknown-key diagnostics for users with machine-learning fields.
    """
    for key in FIELDS_ITEM_ML_KEYS:
        assert key in FIELD_ITEM_KNOWN_KEYS, (
            f"ML field key {key!r} is missing from FIELD_ITEM_KNOWN_KEYS. "
            "Add it to FIELDS_ITEM_ML_KEYS and ensure that group is included in the composite."
        )


# ---------------------------------------------------------------------------
# Top-level key inventory
# ---------------------------------------------------------------------------

# Keys allowed only when the block contains a `signature:` directive.
_SIGNATURE_ONLY_TOP_LEVEL_KEYS = frozenset({"required", "pen color"})


def test_top_level_completion_keys_are_valid_by_validation() -> None:
    """Every key offered in top-level completions must be accepted by the validator.

    A completion key not present in all_dict_keys (nor in the signature-only
    exception set) would produce a spurious E301 whenever a user accepts the
    completion suggestion.
    """
    schema = load_schema()
    allowed_lower = {k.lower() for k in all_dict_keys} | {
        k.lower() for k in _SIGNATURE_ONLY_TOP_LEVEL_KEYS
    }

    gaps = {key for key in schema.top_level if key.lower() not in allowed_lower}

    assert not gaps, (
        f"These top-level completion keys are not in all_dict_keys (would always produce E301): "
        f"{sorted(gaps)}\n"
        "Either add them to all_dict_keys in validation.py or remove them from _TOP_LEVEL_RULES "
        "in completion_rules.py."
    )


def test_all_dict_keys_baseline_coverage() -> None:
    """A minimum set of well-known top-level keys must remain in all_dict_keys.

    This catches accidental removal of common keys from the allowed-key tuple.
    """
    baseline = {
        "question",
        "fields",
        "code",
        "event",
        "mandatory",
        "initial",
        "include",
        "objects",
        "features",
        "metadata",
        "modules",
        "sections",
        "table",
        "review",
        "attachment",
        "template",
        "signature",
        "yesno",
        "noyes",
        "choices",
        "buttons",
        "need",
        "on change",
        "default screen parts",
        "default language",
        "interview help",
    }
    all_keys_lower = {k.lower() for k in all_dict_keys}
    missing = baseline - all_keys_lower

    assert not missing, (
        f"Baseline top-level keys were removed from all_dict_keys: {sorted(missing)}"
    )


def test_all_dict_keys_have_completions_or_are_explicitly_excluded() -> None:
    """Every key in all_dict_keys must have a completion rule or be
    explicitly excluded with a documented reason."""
    schema = load_schema()
    completion_keys_lower = {k.lower() for k in schema.top_level}

    # Keys intentionally excluded from completions, with reasons.
    excluded: dict[str, str] = {
        "extras": "Parser-known but rarely used; no clear authoring value.",
        "orelse": "Parser-known; ambiguous standalone meaning.",
        "disable others": "Field-level only, not a top-level key in practice.",
        "show if": "Field-level or modifier; not a standalone top-level key.",
        "hide if": "Field-level or modifier; not a standalone top-level key.",
        "js show if": "Field-level or modifier; not a standalone top-level key.",
        "js hide if": "Field-level or modifier; not a standalone top-level key.",
        "enable if": "Field-level or modifier; not a standalone top-level key.",
        "disable if": "Field-level or modifier; not a standalone top-level key.",
        "js enable if": "Field-level or modifier; not a standalone top-level key.",
        "js disable if": "Field-level or modifier; not a standalone top-level key.",
    }

    all_keys_lower = {k.lower() for k in all_dict_keys}
    missing = all_keys_lower - completion_keys_lower - {k.lower() for k in excluded}

    assert not missing, (
        f"These all_dict_keys have no completion rule and are not in the exclusion list: "
        f"{sorted(missing)}\n"
        "Either add them to _TOP_LEVEL_RULES in completion_rules.py or add them to "
        "the excluded dict in this test with a documented reason."
    )
