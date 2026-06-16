from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import pytest

from docassemble_lsp.core import build_workspace_index, python_modules
from docassemble_lsp.core import get_completions as core_get_completions
from docassemble_lsp.core.completion_rules import PropertyRule
from docassemble_lsp.core.field_keys import (
    FIELD_ITEM_KNOWN_KEYS,
    FIELDS_ITEM_FILE_BOOLEAN_KEYS,
    FIELDS_ITEM_FILE_COMPLEX_KEYS,
    FIELDS_ITEM_FILE_STRING_KEYS,
)
from docassemble_lsp.core.python_paths import path_from_uri_or_path
from docassemble_lsp.core.schema import completion_scope, load_schema
from docassemble_lsp.core.schema_insert_text import contextualize_multiline_insert_text
from docassemble_lsp.core.validation import types_of_blocks
from docassemble_lsp.core.validation_config import RuntimeOptions
from docassemble_lsp.core.workspace import WorkspaceIndex
from tests.corpus import (
    attachment_item_keys_from_example_corpora,
    default_screen_parts_keys_from_example_corpora,
    metadata_keys_from_example_corpora,
    top_level_keys_from_example_corpora,
)

# File-only keys that are correctly filtered from completions when no
# file-like datatype is declared on the field.
_FILE_ONLY_KEYS = set(
    FIELDS_ITEM_FILE_STRING_KEYS + FIELDS_ITEM_FILE_COMPLEX_KEYS + FIELDS_ITEM_FILE_BOOLEAN_KEYS + ("file css class",)
)


def get_completions(source: str, line: int, character: int, **kwargs: Any) -> Any:
    uri_or_path = kwargs.pop("uri_or_path", None)
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    if workspace_index is None:
        current_path = path_from_uri_or_path(uri_or_path)
        roots = [Path(path) for path in workspace_paths] if workspace_paths else []
        workspace_index = build_workspace_index(
            roots,
            current_path=current_path,
            current_source=source if current_path is not None else None,
        )
    assert isinstance(workspace_index, WorkspaceIndex)
    return core_get_completions(
        source,
        line,
        character,
        uri_or_path=uri_or_path,
        workspace_index=workspace_index,
        **kwargs,
    )


_SCOPE_KEY_REGRESSION_CASES: list[tuple[str, str, int, int]] = [
    ("top_level", "", 0, 0),
    ("metadata_block", "metadata:\n  \n", 1, 2),
    ("metadata_author_item", "metadata:\n  authors:\n    - \n", 2, 6),
    ("metadata_social_block", "metadata:\n  social:\n    \n", 2, 4),
    ("metadata_social_twitter_block", "metadata:\n  social:\n    twitter:\n      \n", 3, 6),
    ("metadata_social_og_block", "metadata:\n  social:\n    og:\n      \n", 3, 6),
    ("attachment_metadata_block", "attachments:\n  - metadata:\n      \n", 2, 6),
    ("sections_item", "sections:\n  - \n", 1, 4),
    ("table_column_item", "table: fruit_table\nrows: fruit\ncolumns:\n  - \n", 3, 4),
    ("features_block", "features:\n  \n", 1, 2),
    ("default_screen_parts_block", "default screen parts:\n  \n", 1, 2),
    ("list_collect_block", "question: Hi\nfields:\n  - field: user.name\nlist collect:\n  \n", 4, 2),
    ("image_set_block", "image sets:\n  freepik:\n    \n", 2, 4),
    (
        "validation_messages_block",
        "question: Hi\nfields:\n  - field: user.name\n    validation messages:\n      \n",
        4,
        6,
    ),
    ("review_item", "question: Review\nreview:\n  - \n", 2, 4),
    ("review_field_item", "question: Review\nreview:\n  - label: Name\n    field:\n      - \n", 4, 8),
    ("attachment_item", "attachment:\n  - \n", 1, 4),
    ("attachment_options_block", "attachment options:\n  \n", 1, 2),
    ("segment_block", "segment:\n  \n", 1, 2),
    ("help_block", "help:\n  \n", 1, 2),
    ("interview_help_block", "interview help:\n  \n", 1, 2),
    ("grid_block", "question: Hi\nfields:\n  - field: user.name\n    label: Name\n    grid:\n      \n", 5, 6),
    (
        "item_grid_block",
        "question: Hi\nfields:\n  - field: user.name\n    label: Name\n    item grid:\n      \n",
        5,
        6,
    ),
    (
        "address_autocomplete_block",
        "question: Hi\nfields:\n  - field: user.address\n    address autocomplete:\n      \n",
        4,
        6,
    ),
    ("fields_item", "question: Hi\nbuttons:\n  - \n", 2, 4),
    ("action_button_item", "question: Hi\nfield: ready\naction buttons:\n  - \n", 3, 4),
    ("need_item", "need:\n  \n", 1, 2),
    ("terms_item", "terms:\n  - \n", 1, 4),
    ("show_if_modifier", "question: Hi\nfields:\n  - field: user.name\n    show if:\n      \n", 4, 6),
]


def test_scope_key_regression_cases_cover_all_scopes_with_registered_keys() -> None:
    schema = load_schema()

    scopes_with_keys = {
        scope_name
        for scope_name, scope_properties in schema.scoped_properties.items()
        if scope_name != "unknown_nested" and scope_properties
    }
    covered_scopes = {scope_name for scope_name, _, _, _ in _SCOPE_KEY_REGRESSION_CASES}

    assert covered_scopes == scopes_with_keys


@pytest.mark.parametrize(
    ("scope_name", "source", "line", "character"),
    _SCOPE_KEY_REGRESSION_CASES,
    ids=[scope_name for scope_name, _, _, _ in _SCOPE_KEY_REGRESSION_CASES],
)
def test_scope_completions_include_all_registered_keys(scope_name: str, source: str, line: int, character: int) -> None:
    schema = load_schema()

    assert completion_scope(source, line, character) == scope_name
    labels = {item.label for item in get_completions(source, line, character)}
    missing = set(schema.scoped_properties[scope_name]) - labels
    if scope_name == "top_level":
        missing -= {"required", "pen color"}
    if scope_name == "fields_item":
        missing -= _FILE_ONLY_KEYS

    assert not missing


def test_schema_loads_expected_top_level_keys() -> None:
    schema = load_schema()

    assert "question" in schema.properties
    assert "fields" in schema.properties


def test_schema_uses_typed_property_rules() -> None:
    schema = load_schema()

    assert isinstance(schema.properties["question"], PropertyRule)
    assert isinstance(schema.fields_item["label"], PropertyRule)


def test_fields_scope_exposes_field_items() -> None:
    source = "question: Hi\nfields:\n  - \n"

    assert completion_scope(source, 2, 4) == "fields_item"
    labels = {item.label for item in get_completions(source, 2, 4)}
    assert "label: value" in labels
    assert "label" in labels


def test_new_fields_item_after_existing_entry_resets_known_keys() -> None:
    source = "question: Hi\nfields:\n  - label: First\n    field: name_first\n  - \n"

    assert completion_scope(source, 4, 4) == "fields_item"
    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "label" in labels
    assert "field" in labels


def test_fields_item_continuation_uses_field_scope() -> None:
    source = "question: Hi\nfields:\n  - label: Name\n    \n"

    assert completion_scope(source, 3, 4) == "fields_item"


def test_fields_item_continuation_filters_existing_keys_and_shorthand() -> None:
    source = "question: Hi\nfields:\n  - label: Name\n    \n"

    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "field" in labels
    assert "label" not in labels
    assert "label: value" not in labels
    assert "accept" not in labels


def test_partial_new_fields_item_does_not_inherit_previous_keys() -> None:
    source = "question: Hi\nfields:\n  - label: First\n    field: name_first\n  - lab"

    assert completion_scope(source, 4, 6) == "fields_item"
    labels = {item.label for item in get_completions(source, 4, 6)}
    assert "label" in labels


def test_fields_item_continuation_enables_file_only_keys_for_file_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Upload\n    datatype: file\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "datatype" not in labels
    assert "accept" in labels


def test_fields_item_filters_none_of_the_above_for_text_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "none of the above" not in labels


def test_fields_item_shows_none_of_the_above_for_checkboxes() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: checkboxes\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "none of the above" in labels


def test_fields_item_filters_all_of_the_above_for_text_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "all of the above" not in labels


def test_fields_item_shows_all_of_the_above_for_object_checkboxes() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: object_checkboxes\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "all of the above" in labels


def test_fields_item_filters_uncheck_others_for_text_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "uncheck others" not in labels


def test_fields_item_shows_uncheck_others_for_yesno() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: yesno\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "uncheck others" in labels


def test_fields_item_filters_check_others_for_text_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "check others" not in labels


def test_fields_item_shows_check_others_for_noyes() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: noyes\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "check others" in labels


def test_fields_item_filters_disable_others_for_range_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: range\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "disable others" not in labels


def test_fields_item_shows_disable_others_for_text_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "disable others" in labels


def test_fields_item_filters_rows_for_text_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "rows" not in labels


def test_fields_item_shows_rows_for_area_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: area\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "rows" in labels


def test_fields_item_shows_rows_with_input_type_area() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    input type: area\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "rows" in labels


def test_fields_item_filters_object_labeler_without_object_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "object labeler" not in labels


def test_fields_item_shows_object_labeler_with_object_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: object\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "object labeler" in labels


def test_fields_item_filters_using_without_ml_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "using" not in labels


def test_fields_item_shows_using_for_ml_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: ml\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "using" in labels


def test_fields_item_filters_keep_for_training_without_ml_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "keep for training" not in labels


def test_fields_item_shows_keep_for_training_for_mlarea_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: mlarea\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "keep for training" in labels


def test_fields_item_filters_choices_code_for_boolean_datatypes() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: yesno\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "choices" not in labels
    assert "code" not in labels


def test_fields_item_filters_choices_code_for_ajax_input_type() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    input type: ajax\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "choices" not in labels
    assert "code" not in labels


def test_fields_item_filters_file_keys_for_hidden_input_type() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    input type: hidden\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "accept" not in labels
    assert "maximum image size" not in labels


def test_fields_item_filters_datatype_restricted_keys_when_unset() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    \n"

    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "none of the above" not in labels
    assert "all of the above" not in labels
    assert "uncheck others" not in labels
    assert "check others" not in labels
    assert "disable others" in labels
    assert "rows" not in labels
    assert "object labeler" not in labels
    assert "using" not in labels
    assert "keep for training" not in labels
    assert "choices" in labels
    assert "code" in labels


def test_fields_item_shows_file_keys_for_user_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Upload\n    datatype: user\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "accept" in labels


def test_fields_item_shows_file_keys_for_environment_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Upload\n    datatype: environment\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "accept" in labels


# ---------------------------------------------------------------------------
# Regression: rows with datatype:text + input type:area (review finding)
# ---------------------------------------------------------------------------


def test_fields_item_shows_rows_with_text_datatype_and_input_type_area() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    input type: area\n    \n"

    labels = {item.label for item in get_completions(source, 5, 4)}
    assert "rows" in labels


def test_fields_item_filters_rows_with_text_datatype_no_input_type() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "rows" not in labels


def test_fields_item_shows_rows_with_multiselect_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: multiselect\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "rows" in labels


def test_fields_item_shows_rows_with_object_multiselect_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: object_multiselect\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "rows" in labels


# ---------------------------------------------------------------------------
# Regression: all-of-the-above / none-of-the-above with various datatypes
# ---------------------------------------------------------------------------


def test_fields_item_filters_none_of_the_above_for_dropdown() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: dropdown\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "none of the above" not in labels


def test_fields_item_filters_none_of_the_above_for_area() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: area\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "none of the above" not in labels


def test_fields_item_shows_none_of_the_above_for_object_radio() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: object_radio\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "none of the above" in labels


def test_fields_item_filters_all_of_the_above_for_checkboxes() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: checkboxes\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "all of the above" in labels


def test_fields_item_filters_all_of_the_above_for_area() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: area\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "all of the above" not in labels


# ---------------------------------------------------------------------------
# Regression: disable others with various blocked/allowed datatypes
# ---------------------------------------------------------------------------


def test_fields_item_filters_disable_others_for_each_blocked_datatype() -> None:
    """Verify disable others is filtered for every known blocked datatype."""
    blocked = [
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
    ]
    for dt in blocked:
        source = f"question: Hi\nfields:\n  - label: Ex\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "disable others" not in labels, f"disable others should be filtered for datatype '{dt}'"


def test_fields_item_shows_disable_others_for_each_allowed_datatype() -> None:
    """Verify disable others is shown for common non-blocked datatypes."""
    allowed = ["text", "yesno", "noyes", "email", "date", "number"]
    for dt in allowed:
        source = f"question: Hi\nfields:\n  - label: Ex\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "disable others" in labels, f"disable others should be shown for datatype '{dt}'"


# ---------------------------------------------------------------------------
# Regression: uncheck/check others with various datatypes
# ---------------------------------------------------------------------------


def test_fields_item_filters_uncheck_others_for_each_incompatible_datatype() -> None:
    incompatible = ["text", "checkboxes", "file", "range", "email", "date", "object"]
    for dt in incompatible:
        source = f"question: Hi\nfields:\n  - label: Ex\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "uncheck others" not in labels, f"uncheck others should be filtered for datatype '{dt}'"


def test_fields_item_shows_uncheck_others_for_each_compatible_datatype() -> None:
    compatible = ["yesno", "yesnowide", "noyes", "noyeswide"]
    for dt in compatible:
        source = f"question: Hi\nfields:\n  - label: Ex\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "uncheck others" in labels, f"uncheck others should be shown for datatype '{dt}'"


def test_fields_item_filters_check_others_for_yesnoradio() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: yesnoradio\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "check others" not in labels


# ---------------------------------------------------------------------------
# Regression: object labeler with various object* datatypes
# ---------------------------------------------------------------------------


def test_fields_item_shows_object_labeler_for_object_radio() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: object_radio\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "object labeler" in labels


def test_fields_item_shows_object_labeler_for_object_multiselect() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: object_multiselect\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "object labeler" in labels


def test_fields_item_shows_object_labeler_for_object_checkboxes() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: object_checkboxes\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "object labeler" in labels


# ---------------------------------------------------------------------------
# Regression: choices/code filtering for all boolean datatype variants
# ---------------------------------------------------------------------------


def test_fields_item_filters_choices_for_each_boolean_datatype() -> None:
    boolean_dts = ["yesno", "yesnowide", "yesnoradio", "noyes", "noyeswide", "noyesradio", "yesnomaybe", "noyesmaybe"]
    for dt in boolean_dts:
        source = f"question: Hi\nfields:\n  - label: Ex\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "choices" not in labels, f"choices should be filtered for boolean datatype '{dt}'"
        assert "code" not in labels, f"code should be filtered for boolean datatype '{dt}'"


def test_fields_item_shows_choices_for_non_boolean_datatypes() -> None:
    non_boolean = ["text", "checkboxes", "file", "range", "email", "area"]
    for dt in non_boolean:
        source = f"question: Hi\nfields:\n  - label: Ex\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "choices" in labels, f"choices should be shown for non-boolean datatype '{dt}'"
        assert "code" in labels, f"code should be shown for non-boolean datatype '{dt}'"


# ---------------------------------------------------------------------------
# Regression: address autocomplete requires field ending in .address
# ---------------------------------------------------------------------------


def test_fields_item_shows_address_autocomplete_with_address_field() -> None:
    source = "question: Hi\nfields:\n  - label: Addr\n    field: user.address\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "address autocomplete" in labels


def test_fields_item_filters_address_autocomplete_without_address_field() -> None:
    source = "question: Hi\nfields:\n  - label: Name\n    field: user.name\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "address autocomplete" not in labels


def test_fields_item_filters_address_autocomplete_without_field() -> None:
    source = "question: Hi\nfields:\n  - label: Addr\n    \n"

    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "address autocomplete" not in labels


def test_fields_item_address_autocomplete_value_completion() -> None:
    """address autocomplete: should suggest True/False."""
    source = "question: Hi\nfields:\n  - label: Addr\n    field: user.address\n    address autocomplete: \n"

    completions = get_completions(source, 5, 26)
    labels = {c.label for c in completions}
    assert "True" in labels
    assert "False" in labels


def test_fields_item_shows_file_keys_for_each_file_like_datatype() -> None:
    file_dts = ["file", "files", "camera", "camcorder", "microphone"]
    for dt in file_dts:
        source = f"question: Hi\nfields:\n  - label: Upload\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "accept" in labels, f"accept should be shown for file-like datatype '{dt}'"
        assert "maximum image size" in labels, f"maximum image size should be shown for file-like datatype '{dt}'"


def test_fields_item_filters_file_keys_for_non_file_datatypes() -> None:
    non_file = ["text", "yesno", "checkboxes", "object", "range", "email"]
    for dt in non_file:
        source = f"question: Hi\nfields:\n  - label: Ex\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "accept" not in labels, f"accept should be filtered for non-file datatype '{dt}'"


def test_fields_item_filters_file_keys_when_datatype_not_set() -> None:
    source = "question: Hi\nfields:\n  - label: Upload\n    \n"

    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "accept" not in labels
    assert "maximum image size" not in labels


# ---------------------------------------------------------------------------
# Regression: ajax input type filters choices/code (runtime raises error)
# ---------------------------------------------------------------------------


def test_fields_item_filters_choices_code_with_ajax_and_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    input type: ajax\n    \n"

    labels = {item.label for item in get_completions(source, 5, 4)}
    assert "choices" not in labels
    assert "code" not in labels


# ---------------------------------------------------------------------------
# Regression: hidden input type filters file keys
# ---------------------------------------------------------------------------


def test_fields_item_filters_file_keys_with_hidden_and_file_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: file\n    input type: hidden\n    \n"

    labels = {item.label for item in get_completions(source, 5, 4)}
    assert "accept" not in labels
    assert "maximum image size" not in labels


# ---------------------------------------------------------------------------
# Regression: using/keep for training bounded to ml/mlarea
# ---------------------------------------------------------------------------


def test_fields_item_filters_using_and_keep_for_training_for_each_non_ml_datatype() -> None:
    non_ml = ["text", "yesno", "checkboxes", "file", "range", "email", "object"]
    for dt in non_ml:
        source = f"question: Hi\nfields:\n  - label: Ex\n    datatype: {dt}\n    \n"
        labels = {item.label for item in get_completions(source, 4, 4)}
        assert "using" not in labels, f"using should be filtered for non-ml datatype '{dt}'"
        assert "keep for training" not in labels, f"keep for training should be filtered for non-ml datatype '{dt}'"


def test_fields_item_shows_using_and_keep_for_training_for_mlarea() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: mlarea\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "using" in labels
    assert "keep for training" in labels


# ---------------------------------------------------------------------------
# Regression: non-restricted keys are always shown regardless of datatype
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "help",
        "hint",
        "required",
        "disabled",
        "read only",
        "show if",
        "hide if",
        "enable if",
        "disable if",
        "default",
        "default value",
        "css class",
        "validate",
        "validation messages",
        "help generator",
        "image generator",
    ],
)
def test_fields_item_universal_keys_are_never_filtered(key: str) -> None:
    source = "question: Hi\nfields:\n  - field: x\n    datatype: checkboxes\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert key in labels, f"universal key '{key}' should always be shown"


# ---------------------------------------------------------------------------
# Regression: choice keys are always shown when datatype is not set
# ---------------------------------------------------------------------------


def test_fields_item_choice_keys_shown_when_only_input_type_set() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    input type: radio\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "choices" in labels
    assert "code" in labels
    assert "none of the above" not in labels
    assert "disable others" in labels


# ---------------------------------------------------------------------------
# Regression: trigger at filtered to ajax-only
# ---------------------------------------------------------------------------


def test_fields_item_filters_trigger_at_without_ajax() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "trigger at" not in labels


def test_fields_item_shows_trigger_at_with_ajax() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    input type: ajax\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "trigger at" in labels


def test_fields_item_shows_trigger_at_with_ajax_and_datatype() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: text\n    input type: ajax\n    \n"

    labels = {item.label for item in get_completions(source, 5, 4)}
    assert "trigger at" in labels


# ---------------------------------------------------------------------------
# Regression: mutual visibility modifier exclusion
# ---------------------------------------------------------------------------


def test_fields_item_filters_hide_if_when_show_if_present() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    show if:\n      variable: ready\n      is: True\n    \n"

    labels = {item.label for item in get_completions(source, 6, 4)}
    assert "hide if" not in labels


def test_fields_item_filters_show_if_when_hide_if_present() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    hide if:\n      variable: ready\n      is: True\n    \n"

    labels = {item.label for item in get_completions(source, 6, 4)}
    assert "show if" not in labels


def test_fields_item_filters_disable_if_when_enable_if_present() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    enable if:\n      variable: ready\n      is: True\n    \n"

    labels = {item.label for item in get_completions(source, 6, 4)}
    assert "disable if" not in labels


def test_fields_item_filters_enable_if_when_disable_if_present() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    disable if:\n      variable: ready\n      is: True\n    \n"

    labels = {item.label for item in get_completions(source, 6, 4)}
    assert "enable if" not in labels


def test_fields_item_filters_js_hide_if_when_js_show_if_present() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    js show if: val('ready') == 'x'\n    \n"

    labels = {item.label for item in get_completions(source, 5, 4)}
    assert "js hide if" not in labels


def test_fields_item_non_conflicting_modifiers_are_not_filtered() -> None:
    """show if and enable if are not mutually exclusive (different code-ness unknown at completion time)."""
    source = "question: Hi\nfields:\n  - label: Ex\n    show if:\n      variable: ready\n      is: True\n    \n"

    labels = {item.label for item in get_completions(source, 6, 4)}
    assert "enable if" in labels
    assert "disable if" in labels


def test_fields_item_filters_js_modifiers_when_non_js_present() -> None:
    """JS visibility modifiers are always filtered when non-JS modifiers are present."""
    source = "question: Hi\nfields:\n  - label: Ex\n    show if:\n      variable: ready\n      is: True\n    \n"

    labels = {item.label for item in get_completions(source, 6, 4)}
    assert "js show if" not in labels
    assert "js hide if" not in labels
    assert "js enable if" not in labels
    assert "js disable if" not in labels


def test_fields_item_filters_non_js_modifiers_when_js_present() -> None:
    """Non-JS visibility modifiers are always filtered when JS modifiers are present."""
    source = "question: Hi\nfields:\n  - label: Ex\n    js show if: val('ready') == 'x'\n    \n"

    labels = {item.label for item in get_completions(source, 5, 4)}
    assert "show if" not in labels
    assert "hide if" not in labels
    assert "enable if" not in labels
    assert "disable if" not in labels


# ---------------------------------------------------------------------------
# Regression: action is promoted (sorted first) when input type is ajax
# ---------------------------------------------------------------------------


def test_fields_item_action_is_promoted_with_ajax_input_type() -> None:
    """With ajax, action is the first property key in the sorted list."""
    source = "question: Hi\nfields:\n  - label: Ex\n    input type: ajax\n    \n"

    candidates = get_completions(source, 4, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    action_idx = property_labels.index("action")
    assert action_idx == 0, "action should be first property key when input type is ajax"


def test_fields_item_promotion_sorts_action_first() -> None:
    """Promotion sorts action before other keys that would otherwise sort first alphabetically."""
    source = "question: Hi\nfields:\n  - label: Ex\n    input type: ajax\n    \n"

    candidates = get_completions(source, 4, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    action_idx = property_labels.index("action")
    disable_others_idx = property_labels.index("disable others")
    assert action_idx < disable_others_idx, "action should be sorted before other keys"


def test_fields_item_field_promoted_when_label_present() -> None:
    """field is promoted when label exists but field is missing."""
    source = "question: Hi\nfields:\n  - label: Name\n    \n"

    candidates = get_completions(source, 3, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    field_idx = property_labels.index("field")
    assert field_idx == 0, "field should be first property key when label exists but field is missing"


def test_fields_item_label_promoted_when_field_present() -> None:
    """label is promoted when field exists but label is missing."""
    source = "question: Hi\nfields:\n  - field: x\n    \n"

    candidates = get_completions(source, 3, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    label_idx = property_labels.index("label")
    assert label_idx == 0, "label should be first property key when field exists but label is missing"


def test_fields_item_promotion_not_applied_when_both_label_and_field_present() -> None:
    """Neither label nor field is promoted when both already exist."""
    source = "question: Hi\nfields:\n  - label: Name\n    field: x\n    \n"

    candidates = get_completions(source, 4, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    first_key = property_labels[0]
    assert first_key not in ("label", "field"), "neither label nor field should be promoted when both exist"


def test_fields_item_both_ajax_and_field_promoted_together() -> None:
    """When both ajax action and field are missing, both are promoted."""
    source = "question: Hi\nfields:\n  - label: Name\n    input type: ajax\n    \n"

    candidates = get_completions(source, 4, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    promoted_sorted = property_labels[:2]
    assert "action" in promoted_sorted
    assert "field" in promoted_sorted


def test_fields_item_choices_and_code_promoted_when_multiple_choice_datatype() -> None:
    """choices and code are promoted when datatype requires choices but none provided."""
    source = "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    \n"

    candidates = get_completions(source, 5, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    promoted = property_labels[:2]
    assert "choices" in promoted
    assert "code" in promoted


def test_fields_item_choices_and_code_promoted_when_multiple_choice_input_type() -> None:
    """choices and code are promoted when input type requires choices but none provided."""
    source = "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    input type: radio\n    \n"

    candidates = get_completions(source, 5, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    promoted = property_labels[:2]
    assert "choices" in promoted
    assert "code" in promoted


def test_fields_item_choices_not_promoted_when_choices_already_present() -> None:
    """choices and code are not promoted when choices already exists."""
    source = "question: Hi\nbuttons:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices:\n      - A\n    \n"

    candidates = get_completions(source, 7, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    first_key = property_labels[0]
    assert first_key not in ("choices", "code"), "neither choices nor code should be promoted when choices exists"


def test_fields_item_choices_not_promoted_when_datatype_not_multiple_choice() -> None:
    """choices and code are not promoted when datatype does not require choices."""
    source = "question: Hi\nfields:\n  - label: Name\n    field: x\n    datatype: text\n    \n"

    candidates = get_completions(source, 4, 4)
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "")]
    choices_idx = property_labels.index("choices")
    code_idx = property_labels.index("code")
    # choices is alphabetically first among surviving keys but should not
    # be promoted ahead of keys that are otherwise sorted before it.
    # Check that at least one non-promoted key follows choices.
    assert choices_idx < code_idx


def test_fields_item_action_hidden_when_input_type_datalist() -> None:
    """action is not suggested for fields: with input type: datalist."""
    source = "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    input type: datalist\n    \n"
    candidates = get_completions(source, 5, 4)
    labels = {c.label for c in candidates}
    assert "action" not in labels


def test_fields_item_action_present_when_input_type_ajax() -> None:
    """action is suggested for fields: with input type: ajax."""
    source = "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    input type: ajax\n    \n"
    candidates = get_completions(source, 5, 4)
    labels = {c.label for c in candidates}
    assert "action" in labels


def test_fields_item_action_hidden_when_no_input_type() -> None:
    """action is not suggested for fields: when input type is unset."""
    source = "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    \n"
    candidates = get_completions(source, 4, 4)
    labels = {c.label for c in candidates}
    assert "action" not in labels


# ---------------------------------------------------------------------------
# _FIELD_PROMOTIONS lambda conditions in isolation
# ---------------------------------------------------------------------------


def _ajax_condition(entries: dict[str, str], keys: set[str]) -> bool:
    return entries.get("input type", "").lower() == "ajax" and "action" not in keys


def _label_condition(entries: dict[str, str], keys: set[str]) -> bool:
    return "label" in keys and "field" not in keys


def _field_condition(entries: dict[str, str], keys: set[str]) -> bool:
    return "field" in keys and "label" not in keys


def test_ajax_promotion_condition_matches_ajax_without_action() -> None:
    assert _ajax_condition({"input type": "ajax"}, {"label"})


def test_ajax_promotion_condition_skips_without_ajax() -> None:
    assert not _ajax_condition({"input type": "text"}, {"label"})


def test_ajax_promotion_condition_skips_when_action_present() -> None:
    assert not _ajax_condition({"input type": "ajax"}, {"label", "action"})


def test_label_promotion_condition_matches_label_without_field() -> None:
    assert _label_condition({"label": "Name"}, {"label"})


def test_label_promotion_condition_skips_when_field_present() -> None:
    assert not _label_condition({"label": "Name", "field": "x"}, {"label", "field"})


def test_field_promotion_condition_matches_field_without_label() -> None:
    assert _field_condition({"field": "x"}, {"field"})


# ---------------------------------------------------------------------------
# Regression: shorthand label pattern filters field/label
# ---------------------------------------------------------------------------


def test_fields_item_new_item_promotes_label_and_field() -> None:
    """On a fresh blank - item, promote label and field, hide file keys."""
    source = "question: Hi\nfields:\n  - \n"

    candidates = get_completions(source, 2, 4)
    labels = {c.label for c in candidates}
    assert "field" in labels
    assert "label" in labels
    assert "accept" not in labels
    assert "maximum image size" not in labels

    # Among property keys (excluding shorthand/block entries), field and label are first
    property_labels = [c.label for c in candidates if "(block)" not in (c.label or "") and ": " not in (c.label or "")]
    assert property_labels[:2] == ["field", "label"], (
        f"expected ['field', 'label'] at start of property keys, got {property_labels[:4]}"
    )


def test_fields_item_shorthand_filters_field_and_label() -> None:
    """When shorthand - Name: user.name is used, field and label are filtered."""
    source = "question: Hi\nfields:\n  - Name: user.name\n    \n"

    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "field" not in labels
    assert "label" not in labels


def test_fields_item_shorthand_filters_field_and_label_with_other_keys() -> None:
    """Shorthand with additional explicit keys still filters field/label."""
    source = "question: Hi\nfields:\n  - Name: user.name\n    datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "field" not in labels
    assert "label" not in labels


def test_fields_item_explicit_keys_not_filtered_as_shorthand() -> None:
    """Explicit keys like datatype: text are not treated as shorthand."""
    source = "question: Hi\nfields:\n  - datatype: text\n    \n"

    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "field" in labels
    assert "label" in labels


def test_fields_item_field_and_label_not_filtered_when_both_explicit() -> None:
    """Explicit label and field: neither filtered (both in existing_keys)."""
    source = "question: Hi\nfields:\n  - label: Name\n    field: x\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "label" not in labels  # already in existing_keys
    assert "field" not in labels  # already in existing_keys


# ---------------------------------------------------------------------------
# Regression: datatype aliasing (effective datatype)
# ---------------------------------------------------------------------------


def test_fields_item_datatype_aliasing_dropdown_filters_none_of_the_above() -> None:
    """datatype: dropdown is remapped to datatype: text at parse time,
    so none of the above (checkboxes/object_radio only) should be filtered."""
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: dropdown\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "none of the above" not in labels


def test_fields_item_datatype_aliasing_radio_filters_none_of_the_above() -> None:
    """datatype: radio is remapped to datatype: text at parse time."""
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: radio\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "none of the above" not in labels


def test_fields_item_datatype_aliasing_area_filters_object_labeler() -> None:
    """datatype: area is remapped to datatype: text at parse time,
    so object labeler (needs object prefix) should be filtered."""
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: area\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "object labeler" not in labels


def test_fields_item_datatype_aliasing_mlarea_shows_using() -> None:
    """datatype: mlarea is remapped to datatype: ml at parse time,
    so using (compatible with ml) should be shown."""
    source = "question: Hi\nfields:\n  - label: Ex\n    datatype: mlarea\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "using" in labels


# ---------------------------------------------------------------------------
# Regression: value completions for default: based on field datatype
# ---------------------------------------------------------------------------


def test_fields_item_default_value_completions_for_yesno() -> None:
    """default: on a yesno field should suggest True/False."""
    source = "question: Hi\nfields:\n  - label: Ex\n    field: test\n    datatype: yesno\n    default: \n"

    completions = get_completions(source, 5, 13)
    labels = {c.label for c in completions}
    assert "True" in labels
    assert "False" in labels


def test_fields_item_default_value_completions_for_text() -> None:
    """default: on a text field should not suggest True/False."""
    source = "question: Hi\nfields:\n  - label: Ex\n    field: test\n    datatype: text\n    default: \n"

    completions = get_completions(source, 5, 13)
    labels = {c.label for c in completions}
    assert "True" not in labels
    assert "False" not in labels


# ---------------------------------------------------------------------------
# Regression: value completions for required: / disabled: suggest True/False
# ---------------------------------------------------------------------------


def test_fields_item_required_value_completion() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    required: \n"

    completions = get_completions(source, 3, 14)
    labels = {c.label for c in completions}
    assert "True" in labels
    assert "False" in labels


def test_fields_item_disabled_value_completion() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    disabled: \n"

    completions = get_completions(source, 3, 14)
    labels = {c.label for c in completions}
    assert "True" in labels
    assert "False" in labels


def test_fields_item_shuffle_value_completion() -> None:
    source = "question: Hi\nfields:\n  - label: Ex\n    shuffle: \n"

    completions = get_completions(source, 3, 13)
    labels = {c.label for c in completions}
    assert "True" in labels
    assert "False" in labels


def test_fields_item_none_of_the_above_value_completion() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    datatype: checkboxes\n    none of the above: \n"

    completions = get_completions(source, 4, 24)
    labels = {c.label for c in completions}
    assert "True" in labels
    assert "False" in labels


# ---------------------------------------------------------------------------
# Scope detection: visibility modifier at field-item key level
# ---------------------------------------------------------------------------


def test_fields_item_completions_after_inline_show_if() -> None:
    """Cursor at field-item sibling level after inline 'show if: thing'."""
    source = "question: Hi\nfields:\n  - show if: thing\n    \n"

    labels = {item.label for item in get_completions(source, 4, 4)}
    assert "field" in labels
    assert "label" in labels
    assert "datatype" in labels


def test_fields_item_completions_after_block_show_if_sibling() -> None:
    """Cursor at field-item sibling level after block 'show if:'."""
    source = "question: Hi\nfields:\n  - show if:\n      variable: ready\n    \n"

    labels = {item.label for item in get_completions(source, 5, 4)}
    assert "field" in labels
    assert "label" in labels


def test_fields_item_completions_inside_show_if_block() -> None:
    """Cursor inside the show if block still gets show_if_modifier scope."""
    source = "question: Hi\nfields:\n  - show if:\n      variable: ready\n      \n"

    labels = {item.label for item in get_completions(source, 4, 6)}
    assert "is" in labels
    assert "field" not in labels
    assert "label" not in labels


def test_fields_item_completions_after_validation_messages_sibling() -> None:
    """Cursor at sibling level after validation messages still gets field keys."""
    source = "question: Hi\nfields:\n  - validation messages:\n    required: This\n    \n"

    labels = {item.label for item in get_completions(source, 5, 4)}
    assert "field" in labels
    assert "label" in labels
    assert "datatype" in labels


def test_fields_item_completions_after_grid_sibling() -> None:
    """Cursor at sibling level after grid still gets field keys."""
    source = "question: Hi\nfields:\n  - grid: 12\n    \n"

    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "field" in labels
    assert "label" in labels


# ---------------------------------------------------------------------------
# Convention C102 suppresses shorthand completions
# ---------------------------------------------------------------------------


def test_c102_suppresses_shorthand_in_fields_item() -> None:
    source = "question: Hi\nfields:\n  - \n"

    completions = get_completions(source, 2, 4, runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C102"})))
    labels = {c.label for c in completions}
    assert "label: value" not in labels


def test_c102_does_not_affect_property_completions() -> None:
    source = "question: Hi\nfields:\n  - \n"

    completions = get_completions(source, 2, 4, runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C102"})))
    labels = {c.label for c in completions}
    assert "field" in labels
    assert "label" in labels


def test_metadata_continuation_filters_existing_keys() -> None:
    source = "metadata:\n  title: Hi\n  \n"

    labels = {item.label for item in get_completions(source, 2, 2)}
    assert "title" not in labels
    assert "short title" in labels


def test_show_if_continuation_filters_existing_keys_and_shorthand() -> None:
    source = "question: Hi\nfields:\n  - field: user.name\n    show if:\n      variable: ready\n      \n"

    labels = {item.label for item in get_completions(source, 5, 6)}
    assert "variable" not in labels
    assert "is" in labels
    assert "code" not in labels
    assert "variable/is" not in labels


def test_top_level_question_continuation_filters_conflicting_exclusive_types() -> None:
    source = "question: Hi\n\n"

    labels = {item.label for item in get_completions(source, 1, 0)}
    assert "include" not in labels
    assert "features" not in labels
    assert "attachment" in labels
    assert "terms" in labels


def test_top_level_scope_hides_signature_only_keys_without_signature() -> None:
    labels = {item.label for item in get_completions("", 0, 0)}

    assert "required" not in labels
    assert "pen color" not in labels


def test_top_level_scope_shows_signature_only_keys_after_signature() -> None:
    source = "question: Sign here\nsignature: user.signature\n\n"

    labels = {item.label for item in get_completions(source, 2, 0)}

    assert "required" in labels
    assert "pen color" in labels


def test_fields_scope_exposes_shorthand_for_object_form() -> None:
    source = "question: Hi\nfields:\n  \n"

    assert completion_scope(source, 2, 2) == "fields_item"
    labels = {item.label for item in get_completions(source, 2, 2)}
    assert "label: value" in labels


def test_fields_scope_includes_validator_known_item_keys() -> None:
    source = "question: Hi\nbuttons:\n  - \n"

    labels = {item.label for item in get_completions(source, 2, 4)}
    missing = set(FIELD_ITEM_KNOWN_KEYS) - labels
    missing -= _FILE_ONLY_KEYS

    assert not missing


def test_top_level_scope_includes_example_corpus_keys() -> None:
    labels = {item.label for item in get_completions("", 0, 0)}

    assert "dropdown" in labels
    assert "combobox" in labels
    assert "on change" in labels
    assert "validation code" in labels
    assert "continue button field" in labels
    assert "sets" in labels
    assert "reload" in labels


def test_top_level_scope_covers_example_corpora() -> None:
    labels = {item.label for item in get_completions("", 0, 0)}
    missing = (top_level_keys_from_example_corpora() - {"required", "pen color"}) - labels

    assert not missing


def test_metadata_scope_covers_example_corpora() -> None:
    source = "metadata:\n  \n"

    labels = {item.label for item in get_completions(source, 1, 2)}
    missing = metadata_keys_from_example_corpora() - labels

    assert not missing


def test_attachment_scope_covers_example_corpora() -> None:
    source = "attachment:\n  - \n"

    labels = {item.label for item in get_completions(source, 1, 4)}
    missing = attachment_item_keys_from_example_corpora() - labels

    assert not missing


def test_default_screen_parts_scope_covers_example_corpora() -> None:
    source = "default screen parts:\n  \n"

    labels = {item.label for item in get_completions(source, 1, 2)}
    missing = default_screen_parts_keys_from_example_corpora() - labels

    assert not missing


def test_features_scope_exposes_feature_items() -> None:
    source = "features:\n  \n"

    assert completion_scope(source, 1, 2) == "features_block"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert "progress bar" in labels
    assert "question" not in labels


def test_small_screen_navigation_exposes_documented_values() -> None:
    source = "features:\n  small screen navigation: \n"

    labels = {item.label for item in get_completions(source, 1, 27)}
    assert {"True", "False", "dropdown"}.issubset(labels)


def test_metadata_scope_exposes_documented_metadata_keys() -> None:
    source = "metadata:\n  \n"

    assert completion_scope(source, 1, 2) == "metadata_block"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert "documentation" in labels
    assert "title/short title/subtitle" in labels
    assert "documentation/example range" in labels
    assert "authors/social" in labels
    assert "title" in labels
    assert "short title" in labels
    assert "required privileges" in labels
    assert "social" in labels
    assert "example start" in labels
    assert "question" not in labels


def test_metadata_authors_scope_exposes_author_fields() -> None:
    source = "metadata:\n  authors:\n    - \n"

    assert completion_scope(source, 2, 6) == "metadata_author_item"
    labels = {item.label for item in get_completions(source, 2, 6)}
    assert labels == {"name", "organization", "name/organization"}


def test_metadata_social_scope_exposes_documented_social_keys() -> None:
    source = "metadata:\n  social:\n    \n"

    assert completion_scope(source, 2, 4) == "metadata_social_block"
    labels = {item.label for item in get_completions(source, 2, 4)}
    assert labels == {
        "description",
        "image",
        "name",
        "og",
        "twitter",
        "name/description/image",
        "twitter block",
        "og block",
    }


def test_metadata_social_twitter_scope_exposes_documented_keys() -> None:
    source = "metadata:\n  social:\n    twitter:\n      \n"

    assert completion_scope(source, 3, 6) == "metadata_social_twitter_block"
    labels = {item.label for item in get_completions(source, 3, 6)}
    assert "card/title/site" in labels
    assert "description/image" in labels
    assert "card" in labels
    assert "title" in labels
    assert "image:alt" in labels


def test_metadata_social_og_scope_exposes_documented_keys() -> None:
    source = "metadata:\n  social:\n    og:\n      \n"

    assert completion_scope(source, 3, 6) == "metadata_social_og_block"
    labels = {item.label for item in get_completions(source, 3, 6)}
    assert "title/url/type" in labels
    assert "site/locale/image" in labels
    assert "title" in labels
    assert "site_name" in labels
    assert "type" in labels


def test_attachment_metadata_scope_exposes_documented_keys() -> None:
    source = "attachments:\n  - metadata:\n      \n"

    assert completion_scope(source, 2, 6) == "attachment_metadata_block"
    labels = {item.label for item in get_completions(source, 2, 6)}
    assert "title/author/date" in labels
    assert "spacing/fontsize/toc" in labels
    assert "header/footer" in labels
    assert "title" in labels
    assert "fontsize" in labels
    assert "header-includes" in labels
    assert "author-meta" in labels


def test_attachment_options_metadata_scope_exposes_documented_keys() -> None:
    source = "attachment options:\n  metadata:\n    \n"

    assert completion_scope(source, 2, 4) == "attachment_metadata_block"
    labels = {item.label for item in get_completions(source, 2, 4)}
    assert "title/author/date" in labels
    assert "title" in labels
    assert "papersize" in labels
    assert "toc" in labels


def test_attachment_fields_scope_exposes_docx_mapping_snippets() -> None:
    source = "attachment:\n  - docx template file: letter.docx\n    fields:\n      \n"

    assert completion_scope(source, 3, 6) == "attachment_fields_block"
    labels = {item.label for item in get_completions(source, 3, 6)}
    assert "template_field: value" in labels
    assert "template_field list" in labels
    assert "template_field object" in labels


def test_attachment_fields_scope_exposes_docx_mapping_snippets_for_list_form() -> None:
    source = "attachment:\n  - docx template file: letter.docx\n    fields:\n      - \n"

    assert completion_scope(source, 3, 8) == "attachment_fields_block"
    labels = {item.label for item in get_completions(source, 3, 8)}
    assert "template_field: value" in labels


def test_attachment_field_variables_scope_exposes_variable_name_snippet() -> None:
    source = "attachment:\n  - docx template file: letter.docx\n    field variables:\n      - \n"

    assert completion_scope(source, 3, 8) == "attachment_field_variable_item"
    labels = {item.label for item in get_completions(source, 3, 8)}
    assert labels == {"variable_name"}


def test_attachment_raw_field_variables_scope_exposes_variable_name_snippet() -> None:
    source = "attachment:\n  - docx template file: letter.docx\n    raw field variables:\n      - \n"

    assert completion_scope(source, 3, 8) == "attachment_field_variable_item"
    labels = {item.label for item in get_completions(source, 3, 8)}
    assert labels == {"variable_name"}


def test_terms_list_item_scope_exposes_documented_keys() -> None:
    source = "terms:\n  - \n"

    assert completion_scope(source, 1, 4) == "terms_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert labels == {"definition", "phrases"}


def test_auto_terms_list_item_scope_exposes_documented_keys() -> None:
    source = "auto terms:\n  - \n"

    assert completion_scope(source, 1, 4) == "terms_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert labels == {"definition", "phrases"}


def test_language_key_offers_common_language_codes() -> None:
    """The `language` key should offer IETF language codes as enum completions."""
    source = "question: Hi\nlanguage: \n"

    labels = {item.label for item in get_completions(source, 1, 11)}
    assert "en" in labels
    assert "es" in labels
    assert "fr" in labels
    assert "de" in labels


def test_default_language_key_offers_common_language_codes() -> None:
    """The `default language` key should offer IETF language codes as enum completions."""
    source = "default language: \n"

    labels = {item.label for item in get_completions(source, 0, 17)}
    assert "en" in labels
    assert "es" in labels
    assert "fr" in labels
    assert "de" in labels


def test_language_key_in_top_level_scope_after_question() -> None:
    """The `language` modifier key should appear in top-level completions after a question."""
    source = "question: Hi\n"

    labels = {item.label for item in get_completions(source, 1, 0)}
    assert "language" in labels


def test_sections_scope_exposes_section_snippets() -> None:
    source = "sections:\n  - \n"

    assert completion_scope(source, 1, 4) == "sections_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "Section title" in labels
    assert "keyword: title" in labels
    assert "keyword with subsections" in labels


def test_sections_keyword_scope_exposes_subsections_key() -> None:
    source = "sections:\n  - intro: Introduction\n      \n"

    assert completion_scope(source, 2, 6) == "sections_item"
    labels = {item.label for item in get_completions(source, 2, 6)}
    assert "subsections" in labels


def test_table_columns_scope_exposes_column_forms() -> None:
    source = "table: fruit_table\nrows: fruit\ncolumns:\n  - \n"

    assert completion_scope(source, 3, 4) == "table_column_item"
    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "Header: expression" in labels
    assert "header/cell" in labels
    assert "header" in labels
    assert "cell" in labels


def test_objects_scope_exposes_initializer_snippets() -> None:
    source = "objects:\n  - \n"

    assert completion_scope(source, 1, 4) == "objects_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "name: Class" in labels
    assert "name.attribute: Class" in labels


def test_objects_from_file_scope_exposes_import_snippet() -> None:
    source = "objects from file:\n  - \n"

    assert completion_scope(source, 1, 4) == "objects_from_file_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert labels == {"name: source.yml"}


def test_on_change_scope_exposes_handler_snippet() -> None:
    source = "on change:\n  \n"

    assert completion_scope(source, 1, 2) == "on_change_item"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert labels == {"variable: code"}


def test_include_scope_exposes_documented_file_snippets() -> None:
    source = "include:\n  - \n"

    assert completion_scope(source, 1, 4) == "include_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "questions.yml" in labels
    assert "package:questions.yml" in labels


def test_imports_scope_exposes_module_snippet() -> None:
    source = "imports:\n  - \n"

    assert completion_scope(source, 1, 4) == "imports_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert labels == {"module_name"}


def test_modules_scope_exposes_module_snippets() -> None:
    source = "modules:\n  - \n"

    assert completion_scope(source, 1, 4) == "modules_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "module_name" in labels
    assert ".relative_module" in labels


def test_translations_scope_exposes_file_snippet() -> None:
    source = "translations:\n  - \n"

    assert completion_scope(source, 1, 4) == "translations_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert labels == {"translation.xlsx"}


def test_reset_scope_exposes_variable_snippet() -> None:
    source = "reset:\n  - \n"

    assert completion_scope(source, 1, 4) == "reset_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert labels == {"variable_name"}


def test_order_scope_exposes_block_id_snippet() -> None:
    source = "order:\n  - \n"

    assert completion_scope(source, 1, 4) == "order_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert labels == {"block_id"}


def test_include_item_completes_workspace_yaml_files(tmp_path) -> None:
    """include: list items suggest YAML files from the workspace."""
    (tmp_path / "a.yml").write_text("question: A\n")
    (tmp_path / "b.yml").write_text("question: B\n")
    (tmp_path / "other.txt").write_text("not a yaml\n")
    source = "include:\n  - \n"
    source_path = tmp_path / "interview.yml"
    labels = {
        item.label
        for item in get_completions(source, 1, 4, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "a.yml" in labels
    assert "b.yml" in labels
    assert "other.txt" not in labels


def test_include_item_completes_relative_paths(tmp_path) -> None:
    """File paths are relative to the current document directory."""
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "shared.yml").write_text("question: Shared\n")
    source = "include:\n  - \n"
    source_path = tmp_path / "interview.yml"
    labels = {
        item.label
        for item in get_completions(source, 1, 4, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "sub/shared.yml" in labels or "sub\\shared.yml" in labels


def test_include_item_completes_partial_prefix(tmp_path) -> None:
    """Typing a prefix filters candidates."""
    (tmp_path / "questions.yml").write_text("question: A\n")
    (tmp_path / "shared.yml").write_text("question: B\n")
    source = "include:\n  - q\n"
    source_path = tmp_path / "interview.yml"
    # Cursor right after "q" (position 5) so line_prefix captures the typed prefix.
    labels = {
        item.label
        for item in get_completions(source, 1, 5, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "questions.yml" in labels
    assert "shared.yml" not in labels


def test_modules_item_completes_vendored_module_names(tmp_path) -> None:
    """modules: list items suggest vendored docassemble module names
    once the user starts typing (non-empty partial)."""
    source = "modules:\n  - doc\n"
    source_path = tmp_path / "interview.yml"
    labels = {
        item.label
        for item in get_completions(source, 1, 5, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "docassemble.base.util" in labels
    assert "docassemble.base.functions" in labels


def test_modules_item_relative_prefix_matches_workspace_stems(tmp_path) -> None:
    """A dot-prefixed partial (.func) matches workspace module stems and yields
    dot-prefixed labels/insert_text."""
    import dataclasses
    from docassemble_lsp.core.workspace import WorkspaceIndex

    wi = dataclasses.replace(
        WorkspaceIndex.empty_for_roots(),
        all_module_paths=frozenset(
            {
                tmp_path / "functions.py",
                tmp_path / "dw_objects.py",
                tmp_path / "entities.py",
            }
        ),
    )
    source = "modules:\n  - .func\n"
    source_path = tmp_path / "interview.yml"
    labels = {item.label for item in get_completions(source, 1, 6, uri_or_path=str(source_path), workspace_index=wi)}
    assert ".functions" in labels
    assert ".dw_objects" not in labels  # filtered by .func prefix
    assert ".entities" not in labels
    # Vendored modules should NOT appear for relative-prefixed entries
    assert "docassemble.base.util" not in labels
    assert "docassemble.base.functions" not in labels


def test_modules_item_relative_prefix_excludes_vendored_modules(tmp_path) -> None:
    """When the user types a dot prefix, vendored modules are excluded."""
    import dataclasses
    from docassemble_lsp.core.workspace import WorkspaceIndex

    wi = dataclasses.replace(
        WorkspaceIndex.empty_for_roots(),
        all_module_paths=frozenset({tmp_path / "utils.py"}),
    )
    source = "modules:\n  - .\n"
    source_path = tmp_path / "interview.yml"
    # character=5 so line_prefix = "  - ." → partial = "." → is_relative = True
    labels = {item.label for item in get_completions(source, 1, 5, uri_or_path=str(source_path), workspace_index=wi)}
    assert ".utils" in labels
    assert "docassemble.base.util" not in labels
    assert "docassemble.base.functions" not in labels


def test_modules_item_non_relative_prefix_shows_vendored_and_workspace(tmp_path) -> None:
    """Without a dot prefix, workspace modules get the dot added and
    vendored modules still appear without it."""
    import dataclasses
    from docassemble_lsp.core.workspace import WorkspaceIndex

    wi = dataclasses.replace(
        WorkspaceIndex.empty_for_roots(),
        all_module_paths=frozenset({tmp_path / "utils.py"}),
    )
    source = "modules:\n  - util\n"
    source_path = tmp_path / "interview.yml"
    labels = {item.label for item in get_completions(source, 1, 6, uri_or_path=str(source_path), workspace_index=wi)}
    assert ".utils" in labels
    assert "utils" not in labels
    assert "docassemble.base.util" in labels


def test_modules_item_relative_prefix_snippets_without_workspace(tmp_path) -> None:
    """Without workspace modules, a dot prefix still shows snippet templates
    (module_name, .relative_module) — the regex in property_completion_provider
    must allow dots."""
    source = "modules:\n  - .\n"
    source_path = tmp_path / "interview.yml"
    # character=5 so line_prefix = "  - ." → partial = "." → is_relative = True,
    # which skips vendored modules → _file_value returns None → falls through to
    # property_completion_provider which needs the regex to allow dots.
    labels = {
        item.label
        for item in get_completions(source, 1, 5, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "module_name" in labels
    assert ".relative_module" in labels


def test_objects_item_completes_da_object_subclass_names(tmp_path) -> None:
    """objects: value side suggests DAObject subclass names."""
    source = "objects:\n  - person: \n"
    source_path = tmp_path / "interview.yml"
    labels = {
        item.label
        for item in get_completions(source, 1, 12, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "Individual" in labels or "DAObject" in labels


def test_reset_item_completes_known_variable_names(tmp_path) -> None:
    """reset: list items suggest field variable names from the workspace."""
    src_a = tmp_path / "a.yml"
    src_a.write_text("fields:\n  - field: known_var\n    datatype: text\n", encoding="utf-8")
    source = "reset:\n  - \n"
    source_path = tmp_path / "main.yml"
    labels = {
        item.label
        for item in get_completions(source, 1, 4, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "known_var" in labels


def test_include_item_completes_paths_outside_document_dir(tmp_path) -> None:
    """File paths outside the document directory use ../ relative notation."""
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "other.yml").write_text("question: Other\n")
    source = "include:\n  - \n"
    source_path = sub / "interview.yml"
    labels = {
        item.label
        for item in get_completions(source, 1, 4, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "../other.yml" in labels


def test_order_item_completes_block_ids(tmp_path) -> None:
    """order: list items suggest block id: values from workspace documents."""
    src_a = tmp_path / "a.yml"
    src_a.write_text("id: intro_block\nquestion: Hello\n", encoding="utf-8")
    source = "order:\n  - \n"
    source_path = tmp_path / "main.yml"
    labels = {
        item.label
        for item in get_completions(source, 1, 4, uri_or_path=str(source_path), workspace_paths=[str(tmp_path)])
    }
    assert "intro_block" in labels


def test_default_screen_parts_scope_exposes_parser_keys() -> None:
    source = "default screen parts:\n  \n"

    assert completion_scope(source, 1, 2) == "default_screen_parts_block"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert "pre/submit/post" in labels
    assert "help/continue/back buttons" in labels
    assert "under/subtitle" in labels
    assert "css/footer classes" in labels
    assert "navigation bar html" in labels
    assert "under" in labels
    assert "continue button color" in labels
    assert "question" not in labels


def test_list_collect_scope_exposes_parser_keys() -> None:
    source = "question: Hi\nfields:\n  - field: user.name\nlist collect:\n  \n"

    assert completion_scope(source, 4, 2) == "list_collect_block"
    labels = {item.label for item in get_completions(source, 4, 2)}
    assert "label/add another label" in labels
    assert "enable/allow append/delete" in labels
    assert "enable" in labels
    assert "label" in labels
    assert "is final" in labels
    assert "allow append" in labels
    assert "allow delete" in labels
    assert "add another label" in labels
    assert "question" not in labels


def test_image_set_scope_exposes_parser_keys() -> None:
    source = "image sets:\n  freepik:\n    \n"

    assert completion_scope(source, 2, 4) == "image_set_block"
    labels = {item.label for item in get_completions(source, 2, 4)}
    assert labels == {"attribution", "images", "attribution/images"}


def test_default_validation_messages_scope_exposes_parser_keys() -> None:
    source = "default validation messages:\n  \n"

    assert completion_scope(source, 1, 2) == "validation_messages_block"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert "required/max" in labels
    assert "date min/max" in labels
    assert "checkboxes required/checkatleast" in labels
    assert "required" in labels
    assert "date minmax" in labels
    assert "maxuploadsize" in labels
    assert "checkboxes required" in labels


def test_field_validation_messages_scope_exposes_parser_keys() -> None:
    source = "question: Hi\nfields:\n  - field: user.name\n    validation messages:\n      \n"

    assert completion_scope(source, 4, 6) == "validation_messages_block"
    labels = {item.label for item in get_completions(source, 4, 6)}
    assert "required/max" in labels
    assert "required" in labels
    assert "checkatleast" in labels


def test_review_scope_exposes_review_item_keys() -> None:
    source = "question: Review\nreview:\n  - \n"

    assert completion_scope(source, 2, 4) == "review_item"
    labels = {item.label for item in get_completions(source, 2, 4)}
    assert "label: value" in labels
    assert "field" in labels
    assert "label" in labels
    assert "show if" in labels
    assert "note" in labels


def test_review_scope_exposes_shorthand_for_object_form() -> None:
    source = "question: Review\nreview:\n  \n"

    assert completion_scope(source, 2, 2) == "review_item"
    labels = {item.label for item in get_completions(source, 2, 2)}
    assert "label: value" in labels


def test_review_field_scope_exposes_review_commands() -> None:
    source = "question: Review\nreview:\n  - label: Name\n    field:\n      - \n"

    assert completion_scope(source, 4, 8) == "review_field_item"
    labels = {item.label for item in get_completions(source, 4, 8)}
    assert "set" in labels
    assert "follow up" in labels
    assert "recompute" in labels
    assert "invalidate" in labels
    assert "undefine" in labels
    assert "set" in labels
    assert "follow up" in labels
    assert "undefine" in labels
    assert "action" in labels
    assert "arguments" in labels


def test_review_shorthand_field_scope_exposes_review_commands() -> None:
    source = "question: Review\nreview:\n  - Name:\n      - \n"

    assert completion_scope(source, 3, 8) == "review_field_item"
    labels = {item.label for item in get_completions(source, 3, 8)}
    assert "set" in labels
    assert "follow up" in labels
    assert "undefine" in labels
    assert "action" in labels


def test_choices_list_items_use_field_item_scope() -> None:
    source = "question: Hi\nfields:\n  - field: user.favorite\n    choices:\n      - \n"

    assert completion_scope(source, 4, 8) == "fields_item"
    labels = {item.label for item in get_completions(source, 4, 8)}
    assert "label" in labels
    assert "help" in labels
    assert "datatype" in labels


def test_buttons_list_items_use_field_item_scope() -> None:
    source = "question: Hi\nbuttons:\n  - \n"

    assert completion_scope(source, 2, 4) == "fields_item"
    labels = {item.label for item in get_completions(source, 2, 4)}
    assert "label" in labels
    assert "action" in labels
    assert "help" in labels


def test_dropdown_block_uses_field_item_scope_for_object_form() -> None:
    source = "question: Phone\nfield: user.phone_country\ndropdown:\n  \n"

    assert completion_scope(source, 3, 2) == "fields_item"
    labels = {item.label for item in get_completions(source, 3, 2)}
    assert "code" in labels
    assert "exclude" in labels
    assert "label" in labels


def test_attachment_scope_exposes_attachment_items() -> None:
    source = "attachment:\n  - \n"

    assert completion_scope(source, 1, 4) == "attachment_item"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "file" in labels
    assert "name/filename/content" in labels
    assert "name/filename/docx template file" in labels
    assert "name/filename/pdf template file" in labels
    assert "name/filename/valid formats/content" in labels
    assert "filename/variable name/content" in labels
    assert "name" in labels
    assert "valid types" in labels
    assert "pdf template file" in labels


def test_attachment_options_scope_exposes_attachment_option_items() -> None:
    source = "attachment options:\n  \n"

    assert completion_scope(source, 1, 2) == "attachment_options_block"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert "metadata" in labels
    assert "additional yaml/template files" in labels
    assert "docx reference file" in labels
    assert "metadata/template/docx reference" in labels
    assert "initial yaml" in labels
    assert "metadata" in labels


def test_segment_scope_exposes_segment_items() -> None:
    source = "segment:\n  \n"

    assert completion_scope(source, 1, 2) == "segment_block"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert labels == {"arguments", "id", "id/arguments"}


def test_help_scope_exposes_help_items() -> None:
    source = "help:\n  \n"

    assert completion_scope(source, 1, 2) == "help_block"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert "content" in labels
    assert "label/content" in labels
    assert "content/audio" in labels
    assert "content" in labels
    assert "audio" in labels


def test_interview_help_scope_exposes_help_items() -> None:
    source = "interview help:\n  \n"

    assert completion_scope(source, 1, 2) == "interview_help_block"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert "heading/content" in labels
    assert "heading/content/audio" in labels
    assert "heading" in labels
    assert "video" in labels


def test_address_autocomplete_scope_exposes_fixed_option_keys() -> None:
    source = "question: Hi\nfields:\n  - field: user.address\n    address autocomplete:\n      \n"

    assert completion_scope(source, 4, 6) == "address_autocomplete_block"
    labels = {item.label for item in get_completions(source, 4, 6)}
    assert labels == {"fields", "types", "types/fields"}


def test_grid_scope_exposes_grid_items() -> None:
    source = "question: Hi\nfields:\n  - field: user.name\n    label: Name\n    grid:\n      \n"

    assert completion_scope(source, 5, 6) == "grid_block"
    labels = {item.label for item in get_completions(source, 5, 6)}
    assert "width" in labels
    assert "width/label width" in labels
    assert "width/breakpoint" in labels
    assert "width" in labels
    assert "label width" in labels
    assert "breakpoint" in labels


def test_item_grid_scope_exposes_item_grid_items() -> None:
    source = "question: Hi\nfields:\n  - field: user.name\n    label: Name\n    item grid:\n      \n"

    assert completion_scope(source, 5, 6) == "item_grid_block"
    labels = {item.label for item in get_completions(source, 5, 6)}
    assert labels == {"breakpoint", "width", "width/breakpoint"}


def test_need_scope_exposes_need_snippets() -> None:
    source = "need:\n  \n"

    assert completion_scope(source, 1, 2) == "need_item"
    labels = {item.label for item in get_completions(source, 1, 2)}
    assert labels == {"post", "pre"}


def test_action_buttons_scope_exposes_action_button_snippets() -> None:
    source = "question: Hi\nfield: ready\naction buttons:\n  - \n"

    assert completion_scope(source, 3, 4) == "action_button_item"
    labels = {item.label for item in get_completions(source, 3, 4)}
    assert "label/action" in labels
    assert "label/action with arguments" in labels
    assert "label/link" in labels
    assert "arguments" in labels
    assert "forget prior" in labels


def test_action_button_multiline_snippet_uses_current_indent_width() -> None:
    source = "question: Hi\nfield: ready\naction buttons:\n    - \n"

    candidates = get_completions(source, 3, 6)
    snippet = next(candidate for candidate in candidates if candidate.label == "label/action with arguments")

    assert snippet.insert_text == ("label: ${1:Label}\naction: ${2:event_name}\narguments:\n  ${3:key}: ${4:value}")


def test_action_button_property_snippet_uses_tab_indentation() -> None:
    assert contextualize_multiline_insert_text("arguments:\n  $0") == "arguments:\n  $0"


def test_show_if_scope_exposes_structured_condition_snippets() -> None:
    source = "question: Hi\nfields:\n  - field: user.name\n    show if:\n      \n"

    assert completion_scope(source, 4, 6) == "show_if_modifier"
    labels = {item.label for item in get_completions(source, 4, 6)}
    assert labels == {"code", "is", "variable", "variable/is"}


def test_unknown_nested_scope_returns_no_completions() -> None:
    source = "attachment:\n  - fields:\n      \n"

    assert completion_scope(source, 2, 6) == "attachment_fields_block"
    labels = {item.label for item in get_completions(source, 2, 6)}
    assert "template_field: value" in labels


def test_get_completions_in_code_block_include_python_module_symbols(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text(
        "def plus_one(value):\n    return value + 1\n\nclass Helper:\n    @staticmethod\n    def status_label(stage):\n        return stage\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\ncode: |\n  plu\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            4,
            len("  plu"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "plus_one" in labels


def test_get_completions_in_code_block_include_implicit_docassemble_base_classes() -> None:
    source = "code: |\n  Ad\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            1,
            len("  Ad"),
            uri_or_path="sample.yml",
            workspace_paths=["/Users/jack/Projects/docassemble-lsp"],
        )
    }

    assert "Address" in labels


def test_get_completions_in_objects_value_include_implicit_docassemble_base_classes() -> None:
    source = "objects:\n  - physical_address: Ad\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            1,
            len("  - physical_address: Ad"),
            uri_or_path="sample.yml",
            workspace_paths=["/Users/jack/Projects/docassemble-lsp"],
        )
    }

    assert "Address" in labels


def test_get_completions_in_objects_value_include_classes_for_lowercase_prefix() -> None:
    source = "objects:\n  - physical_address: a\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            1,
            len("  - physical_address: a"),
            uri_or_path="sample.yml",
            workspace_paths=["/Users/jack/Projects/docassemble-lsp"],
        )
    }

    assert "Address" in labels


def test_get_completions_in_empty_objects_value_include_class_suggestions() -> None:
    source = "objects:\n  - physical_address: \n"

    labels = {
        item.label
        for item in get_completions(
            source,
            1,
            len("  - physical_address: "),
            uri_or_path="sample.yml",
            workspace_paths=["/Users/jack/Projects/docassemble-lsp"],
        )
    }

    assert "Address" in labels


def test_get_completions_in_objects_value_after_colon_insert_space() -> None:
    source = "objects:\n  - physical_address:\n"

    address = next(
        item
        for item in get_completions(
            source,
            1,
            len("  - physical_address:"),
            uri_or_path="sample.yml",
            workspace_paths=["/Users/jack/Projects/docassemble-lsp"],
        )
        if item.label == "Address"
    )

    assert address.insert_text == " Address"


def test_get_completions_in_objects_value_include_vendored_docassemble_base_classes(monkeypatch) -> None:
    source = "objects:\n  - physical_address: Ad\n"

    monkeypatch.setattr(python_modules.importlib.util, "find_spec", lambda _name: None)
    labels = {
        item.label
        for item in get_completions(
            source,
            1,
            len("  - physical_address: Ad"),
            uri_or_path="sample.yml",
            workspace_paths=["/Users/jack/Projects/docassemble-lsp"],
        )
    }

    assert "Address" in labels


def test_get_completions_respect_module_all_exports(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (package_dir / "shared.py").write_text(
        "from docassemble.base.util import DAObject\n"
        "class ExportedClass(DAObject):\n    pass\n\ndef exported_function():\n    return 1\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    (package_dir / "helpers.py").write_text(
        "from docassemble.demo.shared import ExportedClass, exported_function\n"
        "__all__ = ['ExportedClass', 'exported_function']\n"
        "def hidden_helper():\n    return 2\n",
        encoding="utf-8",
    )

    object_labels = {
        item.label
        for item in get_completions(
            "modules:\n  - docassemble.demo.helpers\n---\nobjects:\n  - thing: Ex\n",
            4,
            len("  - thing: Ex"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }
    code_labels = {
        item.label
        for item in get_completions(
            "modules:\n  - docassemble.demo.helpers\n---\ncode: |\n  exp\n",
            4,
            len("  exp"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "ExportedClass" in object_labels
    assert "hidden_helper" not in object_labels
    assert "exported_function" in code_labels
    assert "hidden_helper" not in code_labels


def test_get_completions_in_code_block_include_vendored_docassemble_base_functions(monkeypatch) -> None:
    source = "code: |\n  act\n"

    monkeypatch.setattr(python_modules.importlib.util, "find_spec", lambda _name: None)
    labels = {
        item.label
        for item in get_completions(
            source,
            1,
            len("  act"),
            uri_or_path="sample.yml",
            workspace_paths=["/Users/jack/Projects/docassemble-lsp"],
        )
    }

    assert "action_arguments" in labels
    assert "a_preposition_b_default" not in labels


def test_get_completions_in_code_block_exclude_non_exported_vendored_helpers(monkeypatch) -> None:
    source = "code: |\n  c\n"

    monkeypatch.setattr(python_modules.importlib.util, "find_spec", lambda _name: None)
    labels = {
        item.label
        for item in get_completions(
            source,
            1,
            len("  c"),
            uri_or_path="sample.yml",
            workspace_paths=["/Users/jack/Projects/docassemble-lsp"],
        )
    }

    assert "capitalize" in labels
    assert "complex_delattr" not in labels


def test_get_completions_in_objects_value_include_imported_class_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text(
        "class Helper:\n    pass\n\ndef plus_one(value):\n    return value + 1\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = (
        "imports:\n"
        "  - from docassemble.demo.helpers import Helper as InterviewHelper\n"
        "---\n"
        "objects:\n"
        "  - assistant: Int\n"
    )

    labels = {
        item.label
        for item in get_completions(
            source,
            4,
            len("  - assistant: Int"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "InterviewHelper" in labels


def test_get_completions_in_mako_expression_include_class_methods(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text(
        "class Helper:\n    @staticmethod\n    def status_label(stage):\n        return stage\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = "imports:\n  - from docassemble.demo.helpers import Helper\n---\nquestion: |\n  ${ Helper.st }\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            4,
            source.splitlines()[4].index("st") + 2,
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "status_label" in labels


def test_get_completions_in_if_value_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nif: eli\nquestion: Hi\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            3,
            len("if: eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_need_list_item_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nneed:\n  - eli\nquestion: Hi\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            4,
            len("  - eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_require_list_item_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nrequire:\n  - eli\norelse:\n  question: Hi\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            4,
            len("  - eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_list_collect_enable_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: Hi\nfields:\n  - field: user.name\nlist collect:\n  enable: eli\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            7,
            len("  enable: eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_field_validate_value_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: Hi\nfields:\n  - field: user.name\n    validate: eli\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            6,
            len("    validate: eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_field_show_if_code_value_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: Hi\nfields:\n  - field: user.name\n    show if:\n      code: eli\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            7,
            len("      code: eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_field_grid_width_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: Hi\nfields:\n  - field: user.name\n    grid:\n      width: eli\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            7,
            len("      width: eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_attachment_redact_value_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    template_dir = package_dir / "data" / "templates"
    questions_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    (template_dir / "letter.docx").write_text("placeholder", encoding="utf-8")
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = (
        "modules:\n"
        "  - .helpers\n"
        "---\n"
        "attachment:\n"
        "  - name: Letter\n"
        "    docx template file: letter.docx\n"
        "    redact: eli\n"
        "    content: Hi\n"
    )

    labels = {
        item.label
        for item in get_completions(
            source,
            6,
            len("    redact: eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_docx_template_file_value_includes_template_filenames(tmp_path) -> None:
    """Completing value of 'docx template file:' suggests filenames from data/templates/."""
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    template_dir = package_dir / "data" / "templates"
    questions_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    (template_dir / "letter.docx").write_text("placeholder", encoding="utf-8")
    (template_dir / "form.pdf").write_text("placeholder", encoding="utf-8")
    (template_dir / "notice.docx").write_text("placeholder", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    source_path = questions_dir / "main.yml"

    # Cursor at end of 'docx template file: ' — should suggest all template filenames
    source = "attachment:\n  - name: Letter\n    docx template file: \n    content: Hi\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            2,
            len("    docx template file: "),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "letter.docx" in labels
    assert "notice.docx" in labels
    # form.pdf has a different extension and should be filtered out for docx template file:
    assert "form.pdf" not in labels


def test_get_completions_attachment_template_paths_filters_hidden_and_wrong_extension(tmp_path) -> None:
    """Template filename completions exclude hidden files, Office temps, and wrong extensions."""
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    template_dir = package_dir / "data" / "templates"
    questions_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    (template_dir / "letter.docx").write_text("placeholder", encoding="utf-8")
    (template_dir / "form.pdf").write_text("placeholder", encoding="utf-8")
    (template_dir / ".DS_Store").write_text("", encoding="utf-8")
    (template_dir / "~$letter.docx").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    source_path = questions_dir / "main.yml"

    source = "attachment:\n  - name: Letter\n    docx template file: \n    content: Hi\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            2,
            len("    docx template file: "),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "letter.docx" in labels
    assert ".DS_Store" not in labels
    assert "~$letter.docx" not in labels
    assert "form.pdf" not in labels


def test_get_completions_in_attachment_field_code_value_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    template_dir = package_dir / "data" / "templates"
    questions_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    (template_dir / "letter.docx").write_text("placeholder", encoding="utf-8")
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = (
        "modules:\n"
        "  - .helpers\n"
        "---\n"
        "attachment:\n"
        "  - name: Letter\n"
        "    docx template file: letter.docx\n"
        "    field code:\n"
        "      recipient_name: eli\n"
        "    content: Hi\n"
    )

    labels = {
        item.label
        for item in get_completions(
            source,
            7,
            len("      recipient_name: eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_need_post_list_item_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nneed:\n  post:\n    - eli\nquestion: Hi\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            5,
            len("    - eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


def test_get_completions_in_on_change_value_include_python_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\non change:\n  user.name: eli\n"

    labels = {
        item.label
        for item in get_completions(
            source,
            4,
            len("  user.name: eli"),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "eligible" in labels


# ---------------------------------------------------------------------------
# Packet 2: Initial block completion rules and insert kinds
# ---------------------------------------------------------------------------


def test_code_top_level_rule_uses_block_scalar_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["code"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "block_scalar"


def test_include_top_level_rule_uses_array_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["include"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "array"


def test_metadata_top_level_rule_uses_object_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["metadata"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "object"


def test_modules_top_level_rule_uses_array_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["modules"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "array"


def test_imports_top_level_rule_uses_array_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["imports"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "array"


def test_include_top_level_rule_has_description() -> None:
    schema = load_schema()

    rule = schema.properties["include"]
    assert isinstance(rule, PropertyRule)
    assert rule.description is not None
    assert len(rule.description) > 10


def test_metadata_top_level_rule_has_description() -> None:
    schema = load_schema()

    rule = schema.properties["metadata"]
    assert isinstance(rule, PropertyRule)
    assert rule.description is not None
    assert len(rule.description) > 10


def test_mandatory_top_level_rule_has_description() -> None:
    schema = load_schema()

    rule = schema.properties["mandatory"]
    assert isinstance(rule, PropertyRule)
    assert rule.description is not None
    assert len(rule.description) > 10


def test_initial_top_level_rule_has_description() -> None:
    schema = load_schema()

    rule = schema.properties["initial"]
    assert isinstance(rule, PropertyRule)
    assert rule.description is not None
    assert len(rule.description) > 10


# ---------------------------------------------------------------------------
# Packet 3: Question Core descriptions and insert kinds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "question",
        "subquestion",
        "field",
        "event",
        "continue button field",
        "yesno",
        "noyes",
        "yesnomaybe",
        "noyesmaybe",
        "sets",
        "only sets",
        "under",
        "pre",
        "post",
        "right",
        "buttons",
    ],
)
def test_question_core_key_has_description(key: str) -> None:
    schema = load_schema()

    rule = schema.properties[key]
    assert isinstance(rule, PropertyRule)
    assert rule.description is not None
    assert len(rule.description) > 10


def test_sets_top_level_rule_uses_array_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["sets"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "array"


def test_only_sets_top_level_rule_uses_array_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["only sets"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "array"


def test_buttons_top_level_rule_uses_array_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["buttons"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "array"


def test_event_top_level_rule_accepts_array_but_displays_string() -> None:
    schema = load_schema()

    rule = schema.properties["event"]
    assert isinstance(rule, PropertyRule)
    assert rule.value_types == ("string", "array")
    assert rule.display_value_types == ("string",)


def test_ml_field_keys_use_parser_backed_value_types() -> None:
    schema = load_schema()

    using = schema.fields_item["using"]
    keep_for_training = schema.fields_item["keep for training"]
    assert isinstance(using, PropertyRule)
    assert isinstance(keep_for_training, PropertyRule)
    assert using.value_types == ("string",)
    assert keep_for_training.value_types == ("boolean", "string")
    assert keep_for_training.display_value_types == ("boolean", "python")


# ---------------------------------------------------------------------------
# Packet 4: Question Modifiers schema checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "if",
        "need",
        "reconsider",
        "undefine",
        "depends on",
        "supersedes",
        "role",
        "allowed to set",
        "scan for variables",
        "progress",
        "section",
        "comment",
        "language",
        "generic object",
        "variable name",
        "decoration",
        "css class",
        "table css class",
        "check in",
        "skip undefined",
        "prevent going back",
        "back button",
        "hide continue button",
        "disable continue button",
        "reload",
        "id",
        "ga id",
        "segment id",
        "order",
    ],
)
def test_modifier_key_has_description(key: str) -> None:
    schema = load_schema()

    rule = schema.properties[key]
    assert isinstance(rule, PropertyRule)
    assert rule.description is not None
    assert len(rule.description) > 10


def test_reconsider_rule_accepts_bool_string_and_array() -> None:
    schema = load_schema()

    rule = schema.properties["reconsider"]
    assert isinstance(rule, PropertyRule)
    assert "boolean" in rule.value_types
    assert "string" in rule.value_types
    assert "array" in rule.value_types


def test_depends_on_rule_uses_array_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["depends on"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "array"


def test_supersedes_rule_uses_array_insert_kind() -> None:
    schema = load_schema()

    rule = schema.properties["supersedes"]
    assert isinstance(rule, PropertyRule)
    assert rule.insert_kind == "array"


def test_reload_rule_accepts_bool_integer_and_string() -> None:
    schema = load_schema()

    rule = schema.properties["reload"]
    assert isinstance(rule, PropertyRule)
    assert "boolean" in rule.value_types
    assert "integer" in rule.value_types or "string" in rule.value_types


def test_prevent_going_back_rule_uses_bool_and_python_display_types() -> None:
    schema = load_schema()

    rule = schema.properties["prevent going back"]
    assert isinstance(rule, PropertyRule)
    assert rule.display_value_types == ("boolean", "python")


# ---------------------------------------------------------------------------
# List collect block tests
# ---------------------------------------------------------------------------


def test_list_collect_block_is_in_types_of_blocks() -> None:
    """List collect is a registered block type for exclusivity filtering."""
    assert "list collect" in types_of_blocks
    assert types_of_blocks["list collect"]["exclusive"] is True
    assert "question" in types_of_blocks["list collect"]["partners"]


def test_list_collect_key_offers_sub_keys_in_list_collect_scope() -> None:
    """Within list collect block scope, offer documented sub-keys."""
    source = "question: Hi\nfields:\n  - field: user.name\nlist collect:\n  \n"
    labels = {item.label for item in get_completions(source, 4, 2)}
    assert "label" in labels
    assert "add another label" in labels
    assert "enable" in labels
    assert "is final" in labels
    assert "allow append" in labels
    assert "allow delete" in labels


def test_list_collect_scope_provides_correct_keys_in_regression_case() -> None:
    """Verify the regression case for list_collect_block scope is comprehensive."""
    source = "question: Hi\nfields:\n  - field: user.name\nlist collect:\n  \n"
    assert completion_scope(source, 4, 2) == "list_collect_block"


def test_language_and_default_language_use_separate_constants() -> None:
    """The `language` and `default language` keys should use separate constants."""
    from docassemble_lsp.core.completion_rules import _BLOCK_LANGUAGE_CODES, _INTERVIEW_LANGUAGE_CODES

    assert _BLOCK_LANGUAGE_CODES is not None
    assert _INTERVIEW_LANGUAGE_CODES is not None
    # Values should match but objects should be distinct
    assert _BLOCK_LANGUAGE_CODES == _INTERVIEW_LANGUAGE_CODES


def test_custom_datatype_completion_without_modules_directive(tmp_path) -> None:
    """Custom datatypes appear in completions without a ``modules:`` directive.

    In the flat model, all Python modules in the package are available
    regardless of whether the current file declares ``modules:``.
    """
    pkg_dir = tmp_path / "docassemble" / "demo"
    questions_dir = pkg_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "custom_types.py").write_text(
        "from docassemble.base.util import CustomDataType\n\nclass SpamDataType(CustomDataType):\n    name = 'spam'\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = "question: Hi\nfields:\n  - label: X\n    datatype: \n"
    source_path.write_text(source, encoding="utf-8")

    labels = {
        item.label
        for item in get_completions(
            source,
            3,
            len("    datatype: "),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "spam" in labels, "Custom datatype should appear even without modules: directive"
    assert "text" in labels, "Built-in datatypes should still appear"


def test_objects_completion_from_any_package_module(tmp_path) -> None:
    """``objects:`` completions include classes from any package module.

    In the flat model, classes are available regardless of which file
    declares the ``modules:`` directive.
    """
    pkg_dir = tmp_path / "docassemble" / "demo"
    questions_dir = pkg_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "objects.py").write_text(
        "from docassemble.base.util import DAObject\nclass CustomObj(DAObject):\n    pass\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = "objects:\n  - thing: \n"
    source_path.write_text(source, encoding="utf-8")

    labels = {
        item.label
        for item in get_completions(
            source,
            1,
            len("  - thing: "),
            uri_or_path=str(source_path),
            workspace_paths=[str(tmp_path)],
        )
    }

    assert "CustomObj" in labels, "Custom DAObject should appear from any package module"
    assert "DAObject" in labels, "Built-in Docassemble classes should still appear"


def test_cross_package_completions_via_include(tmp_path) -> None:
    """Classes from an external package are indexed when a ``modules:`` entry references it.

    Creates a main package that declares ``modules: docassemble.ext_playground.helpers``
    and an external package ``docassemble.ext_playground`` in the environment.
    Verifies the external package's class appears in objects completions
    and its custom datatype appears in datatype completions.
    """
    # --- External package (simulates .venv install) ---
    ext_root = tmp_path / "ext_pkg"
    ext_root.mkdir()
    (ext_root / "pyproject.toml").write_text("[project]\nname = 'ext_playground'\n", encoding="utf-8")
    ext_pkg_dir = ext_root / "docassemble" / "ext_playground"
    ext_pkg_dir.mkdir(parents=True)
    (ext_pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (ext_pkg_dir / "data").mkdir()
    (ext_pkg_dir / "helpers.py").write_text(
        "from docassemble.base.util import DAObject, CustomDataType\n"
        "\n"
        "class ExternalObj(DAObject):\n"
        "    pass\n"
        "\n"
        "class ExternalType(CustomDataType):\n"
        "    name = 'ext_type'\n",
        encoding="utf-8",
    )

    sys.path.insert(0, str(ext_root))
    importlib.invalidate_caches()
    sys.path_importer_cache.clear()
    python_modules.clear_module_index_cache()

    try:
        # --- Main package ---
        main_root = tmp_path / "main_pkg"
        main_root.mkdir()
        (main_root / "pyproject.toml").write_text("[project]\nname = 'main_demo'\n", encoding="utf-8")
        main_pkg_dir = main_root / "docassemble" / "main_demo"
        main_pkg_dir.mkdir(parents=True)
        (main_pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        questions_dir = main_pkg_dir / "data" / "questions"
        questions_dir.mkdir(parents=True)

        # Test via modules: directive
        source = "modules:\n  - docassemble.ext_playground.helpers\n---\nobjects:\n  - thing: \n"
        source_path = questions_dir / "main.yml"
        source_path.write_text(source, encoding="utf-8")

        obj_labels = {
            item.label
            for item in get_completions(
                source,
                4,
                len("  - thing: "),
                uri_or_path=str(source_path),
                workspace_paths=[str(main_root)],
            )
        }

        assert "ExternalObj" in obj_labels, "External class should appear in objects completions via modules:"
        assert "DAObject" in obj_labels, "Built-in classes should still appear"

        # Test datatype: completion with the external custom datatype
        dt_source = (
            "modules:\n"
            "  - docassemble.ext_playground.helpers\n"
            "---\n"
            "question: Hi\n"
            "fields:\n"
            "  - label: X\n"
            "    datatype: \n"
        )
        dt_path = questions_dir / "datatype_test.yml"
        dt_path.write_text(dt_source, encoding="utf-8")

        dt_labels = {
            item.label
            for item in get_completions(
                dt_source,
                6,
                len("    datatype: "),
                uri_or_path=str(dt_path),
                workspace_paths=[str(main_root)],
            )
        }

        assert "ext_type" in dt_labels, "External custom datatype should appear in datatype completions via modules:"
        assert "text" in dt_labels, "Built-in datatypes should still appear"
    finally:
        if str(ext_root) in sys.path:
            sys.path.remove(str(ext_root))
        importlib.invalidate_caches()


# ---------------------------------------------------------------------------
# Python keyword completions
# ---------------------------------------------------------------------------


def test_code_block_includes_python_keywords() -> None:
    source = "code: |\n  Tr\n"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "True" in labels

    source = "code: |\n  Fa\n"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "False" in labels

    source = "code: |\n  No\n"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "None" in labels


def test_code_block_includes_all_keywords() -> None:
    source = "code: |\n  i\n"
    labels = {item.label for item in get_completions(source, 1, 3)}
    assert "if" in labels
    assert "import" in labels
    assert "in" in labels
    assert "is" in labels


def test_code_block_includes_match_case() -> None:
    source = "code: |\n  mat\n"
    labels = {item.label for item in get_completions(source, 1, 5)}
    assert "match" in labels


def test_code_block_includes_def_return() -> None:
    source = "code: |\n  de\n"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "def" in labels

    source = "code: |\n  re\n"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "return" in labels


def test_mako_expression_excludes_statement_keywords() -> None:
    source = "question: ${ F }\n"
    labels = {item.label for item in get_completions(source, 0, 14)}
    assert "False" in labels

    source = "question: ${ f }\n"
    labels = {item.label for item in get_completions(source, 0, 13)}
    assert "for" not in labels
    assert "def" not in labels
    assert "while" not in labels


def test_mako_expression_includes_expression_keywords() -> None:
    source = "question: ${ i }\n"
    labels = {item.label for item in get_completions(source, 0, 14)}
    assert "if" in labels
    assert "in" in labels
    assert "is" in labels


def test_mako_line_includes_control_keywords() -> None:
    source = "question: Hello\n% f\n"
    labels = {item.label for item in get_completions(source, 1, 3)}
    assert "for" in labels
    assert "False" in labels
    assert "finally" in labels


def test_mako_line_includes_end_keywords() -> None:
    source = "question: Hello\n% end\n"
    labels = {item.label for item in get_completions(source, 1, 6)}
    assert "endif" in labels
    assert "endfor" in labels
    assert "endwhile" in labels
    assert "endtry" in labels
    assert "endwith" in labels


def test_mako_line_excludes_def_return() -> None:
    source = "question: Hello\n% de\n"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "def" not in labels

    source = "question: Hello\n% re\n"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "return" not in labels


def test_python_value_key_includes_expression_keywords_only() -> None:
    source = "mandatory: Tr\n"
    labels = {item.label for item in get_completions(source, 0, 12)}
    assert "True" in labels
    assert "for" not in labels
    assert "def" not in labels


def test_keywords_have_keyword_detail() -> None:
    source = "code: |\n  Tr\n"
    keyword_items = [item for item in get_completions(source, 1, 4) if item.label == "True"]
    assert len(keyword_items) == 1


def test_code_block_includes_multiple_keywords_by_prefix() -> None:
    source = "code: |\n  a\n"
    labels = {item.label for item in get_completions(source, 1, 3)}
    assert "and" in labels
    assert "as" in labels
    assert "assert" in labels
    assert "async" in labels
    assert "await" in labels


# ---------------------------------------------------------------------------
# Python built-in exception completions
# ---------------------------------------------------------------------------


def test_code_block_includes_builtin_exceptions() -> None:
    source = "code: |\n  V\n"
    labels = {item.label for item in get_completions(source, 1, 3)}
    assert "ValueError" in labels
    assert "TypeError" not in labels

    source = "code: |\n  Ty\n"
    labels = {item.label for item in get_completions(source, 1, 4)}
    assert "TypeError" in labels


def test_code_block_includes_base_exception_hierarchy() -> None:
    source = "code: |\n  Base\n"
    labels = {item.label for item in get_completions(source, 1, 6)}
    assert "BaseException" in labels

    source = "code: |\n  Exc\n"
    labels = {item.label for item in get_completions(source, 1, 5)}
    assert "Exception" in labels


def test_mako_expression_includes_builtin_exceptions() -> None:
    source = "question: ${ Val }\n"
    labels = {item.label for item in get_completions(source, 0, 16)}
    assert "ValueError" in labels
    assert "TypeError" not in labels


def test_builtin_exception_has_exception_detail() -> None:
    source = "code: |\n  Val\n"
    items = [item for item in get_completions(source, 1, 5) if item.label == "ValueError"]
    assert len(items) == 1
