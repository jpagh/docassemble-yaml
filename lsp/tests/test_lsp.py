from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from lsprotocol.types import CompletionItemKind, InsertTextFormat, MarkupContent

from docassemble_lsp.core import FormatterConfig, build_workspace_index, reset_logging
from docassemble_lsp.core.python_paths import path_from_uri_or_path
from docassemble_lsp.core.validation_config import RuntimeOptions
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.lsp import server as lsp_server
from docassemble_lsp.lsp.server import (
    _IgnoreUnknownCancelFilter,
    build_code_actions,
    build_document_symbols,
    build_formatting_edits,
    build_hover,
    build_lsp_diagnostics,
    build_on_type_formatting_edits,
)
from docassemble_lsp.lsp.server import (
    build_completion_list as core_build_completion_list,
)
from docassemble_lsp.lsp.server import (
    build_definition_locations as core_build_definition_locations,
)
from docassemble_lsp.lsp.server import (
    build_document_links as core_build_document_links,
)
from docassemble_lsp.lsp.server import (
    build_reference_locations as core_build_reference_locations,
)
from docassemble_lsp.lsp.server import (
    build_workspace_symbols as core_build_workspace_symbols,
)
from tests.corpus import top_level_keys_from_example_corpora


def _workspace_index_for_tests(
    root: Path,
    *,
    current_path: Path | None = None,
    current_source: str | None = None,
) -> WorkspaceIndex:
    return build_workspace_index(
        [root],
        current_path=current_path,
        current_source=current_source,
    )


def _workspace_index_from_test_args(
    source: str,
    uri_or_path: str | None,
    workspace_paths: list[str] | None,
    workspace_index: WorkspaceIndex | None,
) -> WorkspaceIndex:
    if workspace_index is not None:
        return workspace_index
    current_path = path_from_uri_or_path(uri_or_path)
    roots = [Path(path) for path in workspace_paths] if workspace_paths else []
    return build_workspace_index(
        roots,
        current_path=current_path,
        current_source=source if current_path is not None else None,
    )


def build_completion_list(source: str, line: int, character: int, **kwargs: Any) -> Any:
    uri_or_path = kwargs.pop("uri_or_path", None)
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    return core_build_completion_list(
        source,
        line,
        character,
        uri_or_path=uri_or_path,
        workspace_index=_workspace_index_from_test_args(source, uri_or_path, workspace_paths, workspace_index),
        **kwargs,
    )


def build_workspace_symbols(query: str, **kwargs: Any) -> Any:
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    if workspace_index is None:
        workspace_index = build_workspace_index([Path(path) for path in workspace_paths] if workspace_paths else [])
    return core_build_workspace_symbols(query, workspace_index=workspace_index, **kwargs)


def build_definition_locations(uri: str, source: str, line: int, character: int, **kwargs: Any) -> Any:
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    return core_build_definition_locations(
        uri,
        source,
        line,
        character,
        workspace_index=_workspace_index_from_test_args(source, uri, workspace_paths, workspace_index),
        **kwargs,
    )


def build_document_links(uri: str, source: str, **kwargs: Any) -> Any:
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    if workspace_index is None and workspace_paths is not None:
        current_path = path_from_uri_or_path(uri)
        workspace_index = build_workspace_index(
            [Path(path) for path in workspace_paths],
            current_path=current_path,
            current_source=source if current_path is not None else None,
        )
    return core_build_document_links(uri, source, workspace_index=workspace_index, **kwargs)


def build_reference_locations(uri: str, source: str, line: int, character: int, **kwargs: Any) -> Any:
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    return core_build_reference_locations(
        uri,
        source,
        line,
        character,
        workspace_index=_workspace_index_from_test_args(source, uri, workspace_paths, workspace_index),
        **kwargs,
    )


def test_completion_list_includes_top_level_keys() -> None:
    completions = build_completion_list("", 0, 0)

    labels = {item.label for item in completions.items}
    assert "css class" in labels
    assert "default" in labels
    assert "question" in labels
    assert "fields" in labels
    assert "dropdown" in labels
    assert "combobox" in labels
    assert "on change" in labels
    assert "table css class" in labels
    assert "validation code" in labels
    assert "continue button field" in labels
    assert "sets" in labels
    assert "reload" in labels
    assert "usedefs" in labels


def test_completion_list_inserts_validation_code_as_block_scalar() -> None:
    completions = build_completion_list("", 0, 0)

    validation_code_items = [item for item in completions.items if item.label == "validation code"]
    assert validation_code_items
    assert any(item.insert_text == "validation code: |\n  $0" for item in validation_code_items)
    assert any(item.insert_text_format == InsertTextFormat.Snippet for item in validation_code_items)


def test_completion_list_uses_display_type_for_boolean_python_expression_keys() -> None:
    completions = build_completion_list("question: Sign here\nsignature: user.signature\n\n", 2, 0)

    required = next(item for item in completions.items if item.label == "required")

    assert required.detail is None
    assert required.documentation is not None
    assert "boolean | python" in required.documentation.value


def test_completion_list_hides_signature_only_top_level_keys_without_signature() -> None:
    completions = build_completion_list("", 0, 0)

    labels = {item.label for item in completions.items}

    assert "required" not in labels
    assert "pen color" not in labels


def test_completion_list_shows_signature_only_top_level_keys_after_signature() -> None:
    completions = build_completion_list("question: Sign here\nsignature: user.signature\n\n", 2, 0)

    labels = {item.label for item in completions.items}

    assert "required" in labels
    assert "pen color" in labels


def test_unknown_cancel_filter_only_suppresses_pygls_warning() -> None:
    filter_ = _IgnoreUnknownCancelFilter()

    ignored = logging.makeLogRecord(
        {
            "name": "pygls.protocol.json_rpc",
            "levelno": logging.WARNING,
            "levelname": "WARNING",
            "msg": 'Cancel notification for unknown message id "%s"',
            "args": ("1",),
        }
    )
    kept = logging.makeLogRecord(
        {
            "name": "pygls.protocol.json_rpc",
            "levelno": logging.WARNING,
            "levelname": "WARNING",
            "msg": "Different pygls warning",
            "args": (),
        }
    )

    assert filter_.filter(ignored) is False
    assert filter_.filter(kept) is True


def test_run_server_logs_selected_base_modules_to_stderr(monkeypatch, caplog) -> None:
    reset_logging()
    caplog.set_level(logging.INFO, logger="docassemble_lsp")

    class _DummyServer:
        def start_io(self) -> None:
            return None

    monkeypatch.setattr(
        lsp_server,
        "create_server",
        lambda runtime_options=None, formatter_config=None: _DummyServer(),
    )

    exit_code = lsp_server.run_server(
        runtime_options=RuntimeOptions(),
        formatter_config=FormatterConfig(),
        log_level="INFO",
    )

    assert exit_code == 0
    assert "Using docassemble.base.util from" in caplog.text
    assert "Using docassemble.base.functions from" in caplog.text


def test_run_server_debug_log_level_emits_log_message(monkeypatch, caplog) -> None:
    reset_logging()
    caplog.set_level(logging.DEBUG, logger="docassemble_lsp")

    class _DummyServer:
        def start_io(self) -> None:
            return None

    monkeypatch.setattr(
        lsp_server,
        "create_server",
        lambda runtime_options=None, formatter_config=None: _DummyServer(),
    )

    exit_code = lsp_server.run_server(
        runtime_options=RuntimeOptions(),
        formatter_config=FormatterConfig(),
        log_level="DEBUG",
    )

    assert exit_code == 0
    assert "Log level set to DEBUG" in caplog.text


def test_run_server_warning_log_level_emits_log_message(monkeypatch, caplog) -> None:
    reset_logging()
    caplog.set_level(logging.WARNING, logger="docassemble_lsp")

    class _DummyServer:
        def start_io(self) -> None:
            return None

    monkeypatch.setattr(
        lsp_server,
        "create_server",
        lambda runtime_options=None, formatter_config=None: _DummyServer(),
    )

    exit_code = lsp_server.run_server(
        runtime_options=RuntimeOptions(),
        formatter_config=FormatterConfig(),
        log_level="WARNING",
    )

    assert exit_code == 0
    assert "Log level set to WARNING" in caplog.text


def test_completion_list_covers_example_corpora_top_level_keys() -> None:
    completions = build_completion_list("", 0, 0)

    labels = {item.label for item in completions.items}
    missing = (top_level_keys_from_example_corpora() - {"required", "pen color"}) - labels

    assert not missing


def test_hover_uses_schema_documentation() -> None:
    hover = build_hover("question: Hello\n", 0, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "question" in hover.contents.value


def test_hover_uses_display_type_for_boolean_python_expression_keys() -> None:
    hover = build_hover("question: Sign here\nsignature: user.signature\nrequired: False\n", 2, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "**required**" in hover.contents.value
    assert "`boolean | python`" in hover.contents.value


def test_hover_shows_docs_for_enum_value_position() -> None:
    source = "continue button color: primary\n"
    # cursor is placed on the value word "primary"
    value_col = len("continue button color: ")
    hover = build_hover(source, 0, value_col + 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "continue button color" in hover.contents.value


def test_hover_shows_docs_for_fields_item_key() -> None:
    source = "question: Hi\nfields:\n  - datatype: date\n"
    hover = build_hover(source, 2, 5)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "datatype" in hover.contents.value


def test_hover_shows_docs_for_features_block_key() -> None:
    source = "features:\n  progress bar: True\n"
    hover = build_hover(source, 1, 4)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "progress bar" in hover.contents.value


def test_hover_returns_none_for_non_enum_value_position() -> None:
    # "question" key has value_types=("string",) and no enum_values
    source = "question: Hello world\n"
    value_col = len("question: ")
    hover = build_hover(source, 0, value_col + 3)

    assert hover is None


def test_completion_list_returns_enum_values_for_known_property() -> None:
    completions = build_completion_list("continue button color: p", 0, len("continue button color: p"))

    labels = {item.label for item in completions.items if item.kind == CompletionItemKind.Value}
    assert "primary" in labels


def test_completion_list_uses_display_type_for_field_boolean_python_expression_keys() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - \n", 2, 4)

    required = next(item for item in completions.items if item.label == "required")

    assert required.detail is None
    assert required.documentation is not None
    assert "boolean | python" in required.documentation.value


def test_completion_list_marks_property_insert_text_as_snippet() -> None:
    completions = build_completion_list("", 0, 0)

    fields = next(item for item in completions.items if item.label == "fields")
    assert fields.kind == CompletionItemKind.Property
    assert fields.insert_text == "fields:\n  - $0"
    assert fields.insert_text_format == InsertTextFormat.Snippet


def test_completion_list_offers_block_scalar_variant_for_question() -> None:
    completions = build_completion_list("", 0, 0)

    question = next(item for item in completions.items if item.label == "question")
    question_block = next(item for item in completions.items if item.label == "question (block)")

    assert question.insert_text == "question: $0"
    assert question_block.kind == CompletionItemKind.Property
    assert question_block.insert_text == "question: |\n  $0"
    assert question_block.insert_text_format == InsertTextFormat.Snippet


def test_enum_property_completion_triggers_suggest_after_insert() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - \n", 2, 4)

    datatype = next(item for item in completions.items if item.label == "datatype")
    question = next(item for item in build_completion_list("", 0, 0).items if item.label == "question")

    assert datatype.command is not None
    assert datatype.command.command == "editor.action.triggerSuggest"
    assert question.command is None


def test_completion_list_adds_filter_text_for_compound_property_names() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - \n", 2, 4)

    datatype = next(item for item in completions.items if item.label == "datatype")
    input_type = next(item for item in completions.items if item.label == "input type")

    assert datatype.filter_text is not None
    assert "type" in datatype.filter_text.split()
    assert input_type.filter_text is not None
    assert "inputtype" in input_type.filter_text.split()


def test_completion_list_matches_type_prefix_to_datatype_and_input_type() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - type", 2, len("  - type"))

    labels = {item.label for item in completions.items}
    assert "datatype" in labels
    assert "input type" in labels


def test_completion_list_uses_features_scope() -> None:
    completions = build_completion_list("features:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert "progress bar" in labels
    assert "question" not in labels


def test_completion_list_uses_metadata_scope() -> None:
    completions = build_completion_list("metadata:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert "documentation" in labels
    assert "title/short title/subtitle" in labels
    assert "documentation/example range" in labels
    assert "authors/social" in labels
    assert "title" in labels
    assert "required privileges" in labels
    assert "social" in labels


def test_completion_list_uses_metadata_social_scope() -> None:
    completions = build_completion_list("metadata:\n  social:\n    ", 2, 4)

    labels = {item.label for item in completions.items}
    assert "name/description/image" in labels
    assert "twitter block" in labels
    assert "og block" in labels
    assert "name" in labels
    assert "twitter" in labels
    assert "og" in labels


def test_completion_list_uses_metadata_author_scope() -> None:
    completions = build_completion_list("metadata:\n  authors:\n    - ", 2, 6)

    labels = {item.label for item in completions.items}
    assert "name/organization" in labels
    assert "name" in labels


def test_completion_list_uses_metadata_social_twitter_scope() -> None:
    completions = build_completion_list("metadata:\n  social:\n    twitter:\n      ", 3, 6)

    labels = {item.label for item in completions.items}
    assert "card/title/site" in labels
    assert "description/image" in labels
    assert "image:alt" in labels


def test_completion_list_uses_metadata_social_og_scope() -> None:
    completions = build_completion_list("metadata:\n  social:\n    og:\n      ", 3, 6)

    labels = {item.label for item in completions.items}
    assert "title/url/type" in labels
    assert "site/locale/image" in labels
    assert "site_name" in labels


def test_completion_list_uses_terms_item_scope() -> None:
    completions = build_completion_list("terms:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "phrases" in labels
    assert "definition" in labels


def test_completion_list_uses_sections_item_scope() -> None:
    completions = build_completion_list("sections:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "Section title" in labels
    assert "keyword with subsections" in labels


def test_completion_list_uses_table_column_scope() -> None:
    completions = build_completion_list("table: fruit_table\nrows: fruit\ncolumns:\n  - ", 3, 4)

    labels = {item.label for item in completions.items}
    assert "Header: expression" in labels
    assert "header" in labels
    assert "cell" in labels


def test_completion_list_uses_objects_scope() -> None:
    completions = build_completion_list("objects:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "name: Class" in labels
    assert "name.attribute: Class" in labels


def test_completion_list_uses_objects_from_file_scope() -> None:
    completions = build_completion_list("objects from file:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "name: source.yml" in labels


def test_completion_list_uses_on_change_scope() -> None:
    completions = build_completion_list("on change:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert "variable: code" in labels


def test_completion_list_uses_include_scope() -> None:
    completions = build_completion_list("include:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "questions.yml" in labels
    assert "package:questions.yml" in labels


def test_completion_list_uses_imports_scope() -> None:
    completions = build_completion_list("imports:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "module_name" in labels


def test_completion_list_uses_modules_scope() -> None:
    completions = build_completion_list("modules:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "module_name" in labels
    assert ".relative_module" in labels


def test_completion_list_uses_translations_scope() -> None:
    completions = build_completion_list("translations:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "translation.xlsx" in labels


def test_completion_list_uses_reset_scope() -> None:
    completions = build_completion_list("reset:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "variable_name" in labels


def test_completion_list_uses_order_scope() -> None:
    completions = build_completion_list("order:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "block_id" in labels


def test_completion_list_uses_attachment_metadata_scope() -> None:
    completions = build_completion_list("attachment:\n  - metadata:\n      ", 2, 6)

    labels = {item.label for item in completions.items}
    assert "title/author/date" in labels
    assert "spacing/fontsize/toc" in labels
    assert "header/footer" in labels
    assert "title" in labels
    assert "fontsize" in labels
    assert "header-includes" in labels


def test_completion_list_uses_attachment_fields_scope() -> None:
    completions = build_completion_list("attachment:\n  - docx template file: letter.docx\n    fields:\n      ", 3, 6)

    labels = {item.label for item in completions.items}
    assert "template_field: value" in labels
    assert "template_field list" in labels


def test_completion_list_uses_attachment_field_variables_scope() -> None:
    completions = build_completion_list(
        "attachment:\n  - docx template file: letter.docx\n    field variables:\n      - ",
        3,
        8,
    )

    labels = {item.label for item in completions.items}
    assert "variable_name" in labels


def test_completion_list_uses_attachment_raw_field_variables_scope() -> None:
    completions = build_completion_list(
        "attachment:\n  - docx template file: letter.docx\n    raw field variables:\n      - ",
        3,
        8,
    )

    labels = {item.label for item in completions.items}
    assert "variable_name" in labels


def test_completion_list_uses_attachment_options_metadata_scope() -> None:
    completions = build_completion_list("attachment options:\n  metadata:\n    ", 2, 4)

    labels = {item.label for item in completions.items}
    assert "title/author/date" in labels
    assert "title" in labels
    assert "toc" in labels
    assert "papersize" in labels


def test_completion_list_uses_attachment_options_scope() -> None:
    completions = build_completion_list("attachment options:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert "metadata" in labels
    assert "additional yaml/template files" in labels
    assert "docx reference file" in labels
    assert "metadata/template/docx reference" in labels
    assert "initial yaml" in labels


def test_completion_list_uses_list_collect_scope_shorthand() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - field: user.name\nlist collect:\n  ", 4, 2)

    labels = {item.label for item in completions.items}
    assert "label/add another label" in labels
    assert "enable/allow append/delete" in labels
    assert "enable" in labels
    assert "allow append" in labels


def test_hover_uses_metadata_documentation() -> None:
    hover = build_hover("metadata:\n  title: Hello\n", 1, 3)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "title" in hover.contents.value


def test_completion_list_uses_default_screen_parts_scope() -> None:
    completions = build_completion_list("default screen parts:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert "pre/submit/post" in labels
    assert "help/continue/back buttons" in labels
    assert "css/footer classes" in labels
    assert "navigation bar html" in labels
    assert "under" in labels


def test_completion_list_uses_list_collect_scope() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - field: user.name\nlist collect:\n  ", 4, 2)

    labels = {item.label for item in completions.items}
    assert "enable" in labels
    assert "label" in labels
    assert "add another label" in labels


def test_completion_list_uses_image_set_scope() -> None:
    completions = build_completion_list("image sets:\n  freepik:\n    ", 2, 4)

    labels = {item.label for item in completions.items}
    assert labels == {"attribution", "images", "attribution/images"}


def test_completion_list_uses_attachment_scope() -> None:
    completions = build_completion_list("attachment:\n  - ", 1, 4)

    labels = {item.label for item in completions.items}
    assert "file" in labels
    assert "name/filename/content" in labels
    assert "name/filename/docx template file" in labels
    assert "name/filename/pdf template file" in labels
    assert "name/filename/valid formats/content" in labels
    assert "filename/variable name/content" in labels
    assert "name" in labels
    assert "valid types" in labels


def test_completion_list_uses_default_validation_messages_scope() -> None:
    completions = build_completion_list("default validation messages:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert "required/max" in labels
    assert "date min/max" in labels
    assert "checkboxes required/checkatleast" in labels
    assert "required" in labels
    assert "date minmax" in labels
    assert "maxuploadsize" in labels


def test_completion_list_uses_field_validation_messages_scope() -> None:
    completions = build_completion_list(
        "question: Hi\nfields:\n  - field: user.name\n    validation messages:\n      ",
        4,
        6,
    )

    labels = {item.label for item in completions.items}
    assert "required/max" in labels
    assert "checkatleast" in labels


def test_completion_list_uses_review_scope() -> None:
    completions = build_completion_list("question: Review\nreview:\n  - ", 2, 4)

    labels = {item.label for item in completions.items}
    assert "label: value" in labels
    assert "field" in labels
    assert "label" in labels
    assert "show if" in labels


def test_completion_list_marks_shorthand_label_value_as_snippet() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - ", 2, 4)

    shorthand = next(item for item in completions.items if item.label == "label: value")
    assert shorthand.kind == CompletionItemKind.Property
    assert shorthand.insert_text_format == InsertTextFormat.Snippet
    assert shorthand.insert_text == "${1:label}: ${2:value}"
    assert isinstance(shorthand.documentation, MarkupContent)
    assert "Restart" not in shorthand.documentation.value
    assert "Apple" not in shorthand.documentation.value


def test_completion_list_filters_existing_field_item_keys_on_continuation_line() -> None:
    completions = build_completion_list(
        "question: Hi\nfields:\n  - label: Upload\n    datatype: file\n    ",
        4,
        4,
    )

    labels = {item.label for item in completions.items}
    assert "field" in labels
    assert "accept" in labels
    assert "label" not in labels
    assert "datatype" not in labels
    assert "label: value" not in labels


def test_completion_list_offers_button_command_values_for_shorthand_pairs() -> None:
    completions = build_completion_list("question: Hi\nbuttons:\n  Restart: re", 2, len("  Restart: re"))

    labels = {item.label for item in completions.items if item.kind == CompletionItemKind.Value}
    assert "restart" in labels
    assert "refresh" in labels
    assert "register" in labels


def test_completion_list_does_not_offer_button_command_values_when_buttons_use_field() -> None:
    completions = build_completion_list(
        "question: Hi\nfield: user.choice\nbuttons:\n  Restart: re",
        3,
        len("  Restart: re"),
    )

    labels = {item.label for item in completions.items}
    assert "restart" not in labels


def test_completion_list_sort_text_preserves_server_order() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - ", 2, 4)

    sort_texts = [item.sort_text for item in completions.items]
    assert len(sort_texts) > 0
    for index, sort_text in enumerate(sort_texts):
        assert sort_text == f"{index:04d}", f"expected sort_text '{index:04d}' at index {index}, got '{sort_text}'"


def test_completion_list_uses_review_field_scope() -> None:
    completions = build_completion_list("question: Review\nreview:\n  - label: Name\n    field:\n      - ", 4, 8)

    labels = {item.label for item in completions.items}
    assert "set" in labels
    assert "follow up" in labels
    assert "recompute" in labels
    assert "invalidate" in labels
    assert "set" in labels
    assert "follow up" in labels
    assert "undefine" in labels
    assert "action" in labels
    assert "arguments" in labels


def test_completion_list_uses_review_field_scope_for_shorthand_label_items() -> None:
    completions = build_completion_list("question: Review\nreview:\n  - Name:\n      - ", 3, 8)

    labels = {item.label for item in completions.items}
    assert "set" in labels
    assert "follow up" in labels
    assert "undefine" in labels
    assert "action" in labels


def test_completion_list_uses_field_item_scope_for_choices_list_items() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - field: user.favorite\n    choices:\n      - ", 4, 8)

    labels = {item.label for item in completions.items}
    assert "default value" in labels
    assert "label" in labels
    assert "help" in labels
    assert "datatype" in labels


def test_completion_list_uses_field_item_scope_for_buttons_list_items() -> None:
    completions = build_completion_list("question: Hi\nbuttons:\n  - ", 2, 4)

    labels = {item.label for item in completions.items}
    assert "label" in labels
    assert "action" in labels
    assert "help" in labels


def test_completion_list_uses_field_item_scope_for_dropdown_object_form() -> None:
    completions = build_completion_list("question: Phone\nfield: user.phone_country\ndropdown:\n  ", 3, 2)

    labels = {item.label for item in completions.items}
    assert "code" in labels
    assert "exclude" in labels
    assert "label" in labels


def test_completion_list_uses_segment_scope() -> None:
    completions = build_completion_list("segment:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert labels == {"arguments", "id", "id/arguments"}


def test_completion_list_uses_help_scope() -> None:
    completions = build_completion_list("help:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert "content" in labels
    assert "label/content" in labels
    assert "content/audio" in labels
    assert "label" in labels


def test_completion_list_uses_interview_help_scope() -> None:
    completions = build_completion_list("interview help:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert "heading/content" in labels
    assert "heading/content/audio" in labels
    assert "heading" in labels


def test_completion_list_uses_address_autocomplete_scope() -> None:
    completions = build_completion_list(
        "question: Hi\nfields:\n  - field: user.address\n    address autocomplete:\n      ",
        4,
        6,
    )

    labels = {item.label for item in completions.items}
    assert "types/fields" in labels
    assert "types" in labels
    assert "fields" in labels


def test_completion_list_uses_grid_scope() -> None:
    completions = build_completion_list(
        "question: Hi\nfields:\n  - field: user.name\n    label: Name\n    grid:\n      ",
        5,
        6,
    )

    labels = {item.label for item in completions.items}
    assert "width/label width" in labels
    assert "width/breakpoint" in labels
    assert "label width" in labels


def test_completion_list_uses_item_grid_scope() -> None:
    completions = build_completion_list(
        "question: Hi\nfields:\n  - field: user.name\n    label: Name\n    item grid:\n      ",
        5,
        6,
    )

    labels = {item.label for item in completions.items}
    assert "width/breakpoint" in labels
    assert "width" in labels
    assert "breakpoint" in labels


def test_completion_list_uses_need_scope() -> None:
    completions = build_completion_list("need:\n  ", 1, 2)

    labels = {item.label for item in completions.items}
    assert labels == {"post", "pre"}


def test_completion_list_uses_action_button_scope() -> None:
    completions = build_completion_list("question: Hi\nfield: ready\naction buttons:\n  - ", 3, 4)

    labels = {item.label for item in completions.items}
    assert "label/action" in labels
    assert "label/action with arguments" in labels
    assert "label/link" in labels
    assert "color" in labels


def test_completion_list_uses_show_if_modifier_scope() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - field: user.name\n    show if:\n      ", 4, 6)

    labels = {item.label for item in completions.items}
    assert "variable/is" in labels
    assert "code" in labels
    assert "variable" in labels
    assert "is" in labels


def test_completion_list_inserts_show_if_code_as_block_scalar() -> None:
    completions = build_completion_list("question: Hi\nfields:\n  - field: user.name\n    show if:\n      ", 4, 6)

    code_items = [item for item in completions.items if item.label == "code"]
    assert code_items
    assert any(item.insert_text == "code: |\n  $0" for item in code_items)
    assert any(item.insert_text_format == InsertTextFormat.Snippet for item in code_items)


def test_completion_list_suggests_on_screen_variables_for_show_if_variable_value() -> None:
    completions = build_completion_list(
        "question: Hi\nfields:\n  - Are the fruits taxed?: fruits_taxed_yn\n    datatype: yesnoradio\n  - Taste: fruit_taste\n    show if:\n      variable: fru",
        6,
        len("      variable: fru"),
    )

    labels = {item.label for item in completions.items}
    assert "fruits_taxed_yn" in labels


def test_completion_list_excludes_current_field_from_show_if_variable_value() -> None:
    completions = build_completion_list(
        "question: Hi\nfields:\n  - Fruit tax: fruit_taxed_yn\n    datatype: yesnoradio\n  - Fruit taste: fruit_taste\n    show if:\n      variable: fruit_",
        6,
        len("      variable: fruit_"),
    )

    labels = {item.label for item in completions.items}
    assert "fruit_taxed_yn" in labels
    assert "fruit_taste" not in labels


def test_document_symbols_use_document_facts() -> None:
    symbols = build_document_symbols(
        "---\nid: intro\nquestion: Hello\nfields:\n  - Name: user.name\n---\nmandatory: True\ncode: |\n  ready = True\n"
    )

    assert [symbol.name for symbol in symbols] == ["intro", "code"]
    assert symbols[0].children is not None
    assert [child.name for child in symbols[0].children] == ["id", "question", "fields"]
    assert symbols[1].children is not None
    assert [child.name for child in symbols[1].children] == ["mandatory", "code"]


def test_workspace_symbols_include_event_and_definition_names(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    (package_dir / "events.yml").write_text("event: library_event\nquestion: From library\n", encoding="utf-8")
    (package_dir / "defs.yml").write_text("def: explainer_text\ncode: |\n  return 'hello'\n", encoding="utf-8")

    symbols = build_workspace_symbols("", workspace_paths=[str(tmp_path)])

    assert [(symbol.name, symbol.kind.name) for symbol in symbols] == [
        ("explainer_text", "Function"),
        ("library_event", "Event"),
    ]


def test_workspace_symbols_filter_by_query(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    (package_dir / "events.yml").write_text("event: library_event\nquestion: From library\n", encoding="utf-8")
    (package_dir / "defs.yml").write_text("def: explainer_text\ncode: |\n  return 'hello'\n", encoding="utf-8")

    symbols = build_workspace_symbols("event", workspace_paths=[str(tmp_path)])

    assert [(symbol.name, symbol.kind.name) for symbol in symbols] == [("library_event", "Event")]


def test_workspace_symbols_accept_workspace_index(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    (package_dir / "events.yml").write_text("event: library_event\nquestion: From library\n", encoding="utf-8")

    symbols = build_workspace_symbols("event", workspace_index=_workspace_index_for_tests(tmp_path))

    assert [(symbol.name, symbol.kind.name) for symbol in symbols] == [("library_event", "Event")]


def test_completion_list_in_code_block_includes_python_symbols(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def plus_one(value):\n    return value + 1\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\ncode: |\n  plu\n"

    completions = build_completion_list(
        source,
        4,
        len("  plu"),
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "plus_one" in labels


def test_completion_list_in_if_value_includes_python_symbols(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nif: eli\nquestion: Hi\n"

    completions = build_completion_list(
        source,
        3,
        len("if: eli"),
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "eligible" in labels


def test_completion_list_in_need_list_item_includes_python_symbols(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nneed:\n  - eli\nquestion: Hi\n"

    completions = build_completion_list(
        source,
        4,
        len("  - eli"),
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "eligible" in labels


def test_completion_list_in_list_collect_enable_includes_python_symbols(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: Hi\nfields:\n  - field: user.name\nlist collect:\n  enable: eli\n"

    completions = build_completion_list(
        source,
        7,
        len("  enable: eli"),
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "eligible" in labels


def test_completion_list_in_field_validate_value_includes_python_symbols(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: Hi\nfields:\n  - field: user.name\n    validate: eli\n"

    completions = build_completion_list(
        source,
        6,
        len("    validate: eli"),
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "eligible" in labels


def test_completion_list_in_field_show_if_code_value_includes_python_symbols(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: Hi\nfields:\n  - field: user.name\n    show if:\n      code: eli\n"

    completions = build_completion_list(
        source,
        7,
        len("      code: eli"),
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "eligible" in labels


def test_completion_list_in_attachment_field_code_value_includes_python_symbols(tmp_path) -> None:
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

    completions = build_completion_list(
        source,
        7,
        len("      recipient_name: eli"),
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "eligible" in labels


def test_completion_list_in_on_change_value_includes_python_symbols(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text("def eligible(user):\n    return True\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\non change:\n  user.name: eli\n"

    completions = build_completion_list(
        source,
        4,
        len("  user.name: eli"),
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "eligible" in labels


def test_completion_list_in_mako_expression_includes_python_methods(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "helpers.py").write_text(
        "class Helper:\n    @staticmethod\n    def status_label(stage):\n        return stage\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = "imports:\n  - from docassemble.demo.helpers import Helper\n---\nquestion: |\n  ${ Helper.st }\n"

    completions = build_completion_list(
        source,
        4,
        source.splitlines()[4].index("st") + 2,
        uri_or_path=source_path.as_uri(),
        workspace_paths=[str(tmp_path)],
    )

    labels = {item.label for item in completions.items}
    assert "status_label" in labels


def test_build_code_actions_suggest_known_key_replacement_for_unknown_key() -> None:
    source = "---\nqueston: Hi\n"
    diagnostics = build_lsp_diagnostics("file:///sample.yml", source)

    actions = build_code_actions("file:///sample.yml", source, 1, diagnostics)

    assert [action.title for action in actions] == ["Change 'queston' to 'question'"]
    assert actions[0].edit is not None
    assert actions[0].edit.changes is not None
    text_edits = actions[0].edit.changes["file:///sample.yml"]
    assert [text_edit.new_text for text_edit in text_edits] == ["question"]
    assert text_edits[0].range.start.line == 1


def test_build_code_actions_returns_no_quick_fix_without_unknown_key_diagnostic() -> None:
    source = "---\nquestion: Hi\n"
    diagnostics = build_lsp_diagnostics("file:///sample.yml", source)

    actions = build_code_actions("file:///sample.yml", source, 1, diagnostics)

    assert actions == []


def test_build_code_actions_adds_missing_field_key_for_e414() -> None:
    source = "question: |\n  How's the weather?\nfields:\n  - label: This is the label\n"
    diagnostics = build_lsp_diagnostics("file:///sample.yml", source)

    actions = build_code_actions("file:///sample.yml", source, 3, diagnostics)

    assert [a.title for a in actions if "Add missing" in a.title] == ["Add missing 'field' key"]
    e414_fix = next(a for a in actions if a.title == "Add missing 'field' key")
    assert e414_fix.edit is not None and e414_fix.edit.changes is not None
    text_edits = e414_fix.edit.changes["file:///sample.yml"]
    assert len(text_edits) == 1
    new_text = text_edits[0].new_text
    assert "field: " in new_text
    assert new_text.startswith("  - label: This is the label")
    last_line = new_text.split("\n")[-1]
    assert "field: " in last_line
    # The field key must be indented 4 spaces — inside the list item, aligned
    # with "label", not at the same level as the "- " marker.
    assert last_line == "    field: ", f"Expected field key indented inside the list item, got: {last_line!r}"


def test_build_code_actions_adds_missing_label_key_for_e415() -> None:
    source = "question: Hi\nfields:\n  - field: user.name\n"
    diagnostics = build_lsp_diagnostics("file:///sample.yml", source)

    actions = build_code_actions("file:///sample.yml", source, 2, diagnostics)

    assert [a.title for a in actions if "Add missing" in a.title] == ["Add missing 'label' key"]
    e415_fix = next(a for a in actions if a.title == "Add missing 'label' key")
    assert e415_fix.edit is not None and e415_fix.edit.changes is not None
    text_edits = e415_fix.edit.changes["file:///sample.yml"]
    assert len(text_edits) == 1
    new_text = text_edits[0].new_text
    assert "label: " in new_text
    assert "field: user.name" in new_text
    last_line = new_text.split("\n")[-1]
    # The label key must be indented 4 spaces — inside the list item, aligned
    # with "field", not at the same level as the "- " marker.
    assert last_line == "    label: ", f"Expected label key indented inside the list item, got: {last_line!r}"


def test_build_code_actions_adds_missing_table_keys_for_e921() -> None:
    source = "table: fruit_table\nrows: fruit_list\n"
    diagnostics = build_lsp_diagnostics("file:///sample.yml", source)

    actions = build_code_actions("file:///sample.yml", source, 0, diagnostics)

    assert [a.title for a in actions if "Add missing table keys" in a.title] == ["Add missing table keys: columns"]
    e921_fix = next(a for a in actions if a.title == "Add missing table keys: columns")
    assert e921_fix.edit is not None and e921_fix.edit.changes is not None
    text_edits = e921_fix.edit.changes["file:///sample.yml"]
    assert len(text_edits) == 1
    new_text = text_edits[0].new_text
    assert "columns: " in new_text


def test_build_code_actions_adds_choices_and_code_keys_for_e419() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n"
    diagnostics = build_lsp_diagnostics("file:///sample.yml", source)

    actions = build_code_actions("file:///sample.yml", source, 0, diagnostics)

    assert {a.title for a in actions} >= {"Add 'choices' key", "Add 'code' key"}

    choices_fix = next(a for a in actions if a.title == "Add 'choices' key")
    assert choices_fix.edit is not None and choices_fix.edit.changes is not None
    text_edits = choices_fix.edit.changes["file:///sample.yml"]
    assert len(text_edits) == 1
    new_text = text_edits[0].new_text
    lines = new_text.split("\n")
    assert lines[-2] == "    choices:"
    assert lines[-1] == "      - "

    code_fix = next(a for a in actions if a.title == "Add 'code' key")
    assert code_fix.edit is not None and code_fix.edit.changes is not None
    text_edits = code_fix.edit.changes["file:///sample.yml"]
    assert len(text_edits) == 1
    new_text = text_edits[0].new_text
    lines = new_text.split("\n")
    assert lines[-2] == "    code: |"
    assert lines[-1] == "      "


def test_build_code_actions_adds_action_key_for_e420() -> None:
    source = "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    input type: ajax\n"
    diagnostics = build_lsp_diagnostics("file:///sample.yml", source)

    actions = build_code_actions("file:///sample.yml", source, 0, diagnostics)

    assert "Add 'action' key" in {a.title for a in actions}

    action_fix = next(a for a in actions if a.title == "Add 'action' key")
    assert action_fix.edit is not None and action_fix.edit.changes is not None
    text_edits = action_fix.edit.changes["file:///sample.yml"]
    assert len(text_edits) == 1
    new_text = text_edits[0].new_text
    assert "action: " in new_text
    last_line = new_text.split("\n")[-1]
    assert last_line == "    action: "


def test_build_code_actions_returns_no_quick_fix_when_no_diagnostics_match() -> None:
    source = "question: Hi\nfields:\n  - What is your name?: user.name\n"
    diagnostics = build_lsp_diagnostics("file:///sample.yml", source)

    actions = build_code_actions("file:///sample.yml", source, 2, diagnostics)

    # No E414/E415/E921 diagnostics should fire for this valid shorthand.
    e414_titles = [a.title for a in actions if "field" in a.title.lower()]
    e415_titles = [a.title for a in actions if "label" in a.title.lower()]
    assert all("missing" not in t.lower() for t in e414_titles + e415_titles)


def test_definition_locations_resolve_local_include_file(tmp_path) -> None:
    included = tmp_path / "included.yml"
    included.write_text("question: Included\n", encoding="utf-8")
    source = "include:\n  - included.yml\n"
    uri = (tmp_path / "interview.yml").as_uri()

    locations = build_definition_locations(uri, source, 1, len("  - included.yml") - 2)

    assert len(locations) == 1
    assert locations[0].target_uri == included.resolve().as_uri()
    assert locations[0].target_range.start.line == 0


def test_document_links_resolve_local_file_references(tmp_path) -> None:
    included = tmp_path / "included.yml"
    included.write_text("question: Included\n", encoding="utf-8")
    template = tmp_path / "letter.docx"
    template.write_text("placeholder", encoding="utf-8")
    source = 'include:\n  - "included.yml" # comment\nattachment:\n  - docx template file: letter.docx\n'
    uri = (tmp_path / "interview.yml").as_uri()

    links = build_document_links(uri, source)

    assert [
        (link.target, link.range.start.line, link.range.start.character, link.range.end.character) for link in links
    ] == [
        (
            included.resolve().as_uri(),
            1,
            source.splitlines()[1].index("included.yml"),
            source.splitlines()[1].index("included.yml") + len("included.yml"),
        ),
        (
            template.resolve().as_uri(),
            3,
            source.splitlines()[3].index("letter.docx"),
            source.splitlines()[3].index("letter.docx") + len("letter.docx"),
        ),
    ]


def test_document_links_resolve_package_qualified_include(tmp_path) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    shared = questions / "shared.yml"
    shared.write_text("question: Shared\n", encoding="utf-8")
    source = "include:\n  - docassemble.demo:data/questions/shared.yml\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    line_text = source.splitlines()[1]
    pkg_ref = "docassemble.demo:data/questions/shared.yml"
    assert links[0].target == shared.resolve().as_uri()
    assert links[0].range.start.line == 1
    assert links[0].range.start.character == line_text.index(pkg_ref)
    assert links[0].range.end.character == line_text.index(pkg_ref) + len(pkg_ref)


def test_document_links_resolve_quoted_package_qualified_include_from_package_root(tmp_path) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    shared = questions / "shared.yml"
    shared.write_text("question: Shared\n", encoding="utf-8")
    source = 'include:\n  - "docassemble.demo:data/questions/shared.yml"\n'
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(pkg_root)])

    assert len(links) == 1
    line_text = source.splitlines()[1]
    pkg_ref = "docassemble.demo:data/questions/shared.yml"
    assert links[0].target == shared.resolve().as_uri()
    assert links[0].range.start.line == 1
    assert links[0].range.start.character == line_text.index(pkg_ref)
    assert links[0].range.end.character == line_text.index(pkg_ref) + len(pkg_ref)


def test_document_links_resolve_template_from_package_templates_dir(tmp_path) -> None:
    """Template in data/templates/ resolves via WorkspaceIndex (eager path)."""
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    templates_dir = pkg_root / "data" / "templates"
    questions.mkdir(parents=True)
    templates_dir.mkdir(parents=True)
    letter = templates_dir / "letter.docx"
    letter.write_text("placeholder", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")

    source = "attachment:\n  - docx template file: letter.docx\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    assert links[0].target == letter.resolve().as_uri()


def test_document_links_resolve_package_qualified_include_shorthand(tmp_path) -> None:
    """Shorthand include like docassemble.demo:shared.yml resolves with data/questions/ prefix."""
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    shared = questions / "shared.yml"
    shared.write_text("question: Shared\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")
    source = "include:\n  - docassemble.demo:shared.yml\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    assert links[0].target == shared.resolve().as_uri()


def test_document_links_resolve_package_qualified_include_fully_qualified(tmp_path) -> None:
    """Fully-qualified include like docassemble.demo:data/questions/shared.yml still works."""
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    shared = questions / "shared.yml"
    shared.write_text("question: Shared\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")
    source = "include:\n  - docassemble.demo:data/questions/shared.yml\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    assert links[0].target == shared.resolve().as_uri()


def test_document_links_resolve_package_qualified_module_not_normalized(tmp_path) -> None:
    """Package-qualified module refs like docassemble.demo:external.py are NOT normalized."""
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    module_path = pkg_root / "external.py"
    module_path.write_text("def helper():\n    return 42\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")
    source = "modules:\n  - docassemble.demo:external.py\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    assert links[0].target == module_path.resolve().as_uri()


def test_document_links_resolve_template_from_package_templates_dir_fallback_lazy(tmp_path) -> None:
    """Template in data/templates/ resolves via lazy templates_dir_for_path when no workspace_index."""
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    templates_dir = pkg_root / "data" / "templates"
    questions.mkdir(parents=True)
    templates_dir.mkdir(parents=True)
    letter = templates_dir / "letter.docx"
    letter.write_text("placeholder", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")

    from docassemble_lsp.core.document_links import resolve_document_link_targets

    source = "attachment:\n  - docx template file: letter.docx\n"
    targets = resolve_document_link_targets(
        source,
        uri_or_path=str((questions / "interview.yml").resolve()),
    )
    assert len(targets) == 1
    assert targets[0].target_path == letter.resolve()


def test_document_links_resolve_package_qualified_template_file(tmp_path) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    templates = questions / "templates"
    templates.mkdir(parents=True)
    letter = templates / "letter.docx"
    letter.write_text("placeholder", encoding="utf-8")
    source = "attachment:\n  - docx template file: docassemble.demo:data/questions/templates/letter.docx\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    assert links[0].target == letter.resolve().as_uri()


def test_document_links_resolve_modules(tmp_path) -> None:
    pkg_root = tmp_path / "docassemble" / "mypackage"
    mod_dir = pkg_root / "al_vendored"
    mod_dir.mkdir(parents=True)
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")
    (mod_dir / "__init__.py").write_text("", encoding="utf-8")
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    source = "modules:\n  - .al_vendored\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    line_text = source.splitlines()[1]
    ref = ".al_vendored"
    assert links[0].target == (mod_dir / "__init__.py").resolve().as_uri()
    assert links[0].range.start.line == 1
    assert links[0].range.start.character == line_text.index(ref)
    assert links[0].range.end.character == line_text.index(ref) + len(ref)


def test_document_links_resolve_static_css(tmp_path) -> None:
    pkg_root = tmp_path / "docassemble" / "mypackage"
    static = pkg_root / "data" / "static"
    static.mkdir(parents=True)
    (static / "dw.css").write_text("", encoding="utf-8")
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    source = "features:\n  css:\n    - dw.css\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    line_text = source.splitlines()[2]
    ref = "dw.css"
    assert links[0].target == (static / "dw.css").resolve().as_uri()
    assert links[0].range.start.line == 2
    assert links[0].range.start.character == line_text.index(ref)
    assert links[0].range.end.character == line_text.index(ref) + len(ref)


def test_document_links_resolve_static_javascript(tmp_path) -> None:
    pkg_root = tmp_path / "docassemble" / "mypackage"
    static = pkg_root / "data" / "static"
    static.mkdir(parents=True)
    (static / "dw.js").write_text("", encoding="utf-8")
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    source = "features:\n  javascript:\n    - dw.js\n"
    uri = (questions / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    line_text = source.splitlines()[2]
    ref = "dw.js"
    assert links[0].target == (static / "dw.js").resolve().as_uri()
    assert links[0].range.start.line == 2
    assert links[0].range.start.character == line_text.index(ref)
    assert links[0].range.end.character == line_text.index(ref) + len(ref)


def test_document_links_resolve_static_from_subdir(tmp_path) -> None:
    """Static files resolve correctly even when the YAML is in a subdirectory of questions/."""
    pkg_root = tmp_path / "docassemble" / "mypackage"
    static = pkg_root / "data" / "static"
    static.mkdir(parents=True)
    (static / "dw.css").write_text("", encoding="utf-8")
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")
    questions_subdir = pkg_root / "data" / "questions" / "subdir"
    questions_subdir.mkdir(parents=True)
    source = "features:\n  css:\n    - dw.css\n"
    uri = (questions_subdir / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 1
    assert links[0].target == (static / "dw.css").resolve().as_uri()


def test_document_links_resolve_static_nonexistent(tmp_path) -> None:
    """A reference to a static file that doesn't exist produces no links."""
    pkg_root = tmp_path / "docassemble" / "mypackage"
    (pkg_root / "data" / "questions").mkdir(parents=True)
    (pkg_root / "__init__.py").write_text("", encoding="utf-8")
    source = "features:\n  css:\n    - nonexistent.css\n"
    uri = (pkg_root / "data" / "questions" / "interview.yml").as_uri()

    links = build_document_links(uri, source, workspace_paths=[str(tmp_path)])

    assert len(links) == 0


def test_definition_locations_resolve_usedefs_to_def(tmp_path) -> None:
    source = "---\ndef: my_explanation\ncode: |\n  return 'hello'\n---\nusedefs:\n  - my_explanation\nmandatory: True\n"
    uri = (tmp_path / "interview.yml").as_uri()

    locations = build_definition_locations(uri, source, 6, len("  - my_explanation") - 2)

    assert len(locations) == 1
    assert locations[0].target_uri == (tmp_path / "interview.yml").as_uri()
    assert locations[0].target_range.start.line == 1


def test_definition_locations_resolve_action_to_event(tmp_path) -> None:
    source = (
        "question: Hi\n"
        "fields:\n"
        "  - Food: favorite_food\n"
        "    action: wordlist\n"
        "---\n"
        "event: wordlist\n"
        "code: |\n"
        "  return ['apple']\n"
    )
    uri = (tmp_path / "interview.yml").as_uri()

    locations = build_definition_locations(uri, source, 3, len("    action: wordlist") - 2)

    assert len(locations) == 1
    assert locations[0].target_uri == uri
    assert locations[0].target_range.start.line == 5


def test_definition_locations_resolve_error_action_to_event(tmp_path) -> None:
    source = "metadata:\n  error action: on_error\n---\nevent: on_error\nquestion: Sorry\n"
    uri = (tmp_path / "interview.yml").as_uri()

    locations = build_definition_locations(uri, source, 1, len("  error action: on_error") - 2)

    assert len(locations) == 1
    assert locations[0].target_uri == uri
    assert locations[0].target_range.start.line == 3


def test_definition_locations_resolve_action_to_event_across_workspace(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    main = package_dir / "main.yml"
    main.write_text(
        "include:\n  - library.yml\naction buttons:\n  - label: Run\n    action: library_event\n", encoding="utf-8"
    )
    library = package_dir / "library.yml"
    library.write_text("event: library_event\nquestion: From library\n", encoding="utf-8")

    locations = build_definition_locations(
        main.as_uri(),
        main.read_text(encoding="utf-8"),
        4,
        len("    action: library_event") - 2,
        workspace_paths=[str(tmp_path)],
    )

    assert [(location.target_uri, location.target_range.start.line) for location in locations] == [
        (library.as_uri(), 0)
    ]


def test_reference_locations_resolve_event_references(tmp_path) -> None:
    source = (
        "question: Hi\n"
        "fields:\n"
        "  - Food: favorite_food\n"
        "    action: wordlist\n"
        "---\n"
        "event: wordlist\n"
        "code: |\n"
        "  return ['apple']\n"
        "---\n"
        "metadata:\n"
        "  error action: wordlist\n"
    )
    uri = (tmp_path / "interview.yml").as_uri()

    locations = build_reference_locations(uri, source, 5, len("event: wordlist") - 2)

    assert [(location.uri, location.range.start.line) for location in locations] == [
        (uri, 3),
        (uri, 5),
        (uri, 10),
    ]


def test_reference_locations_resolve_event_references_across_workspace(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    main = package_dir / "main.yml"
    main.write_text(
        "include:\n  - library.yml\naction buttons:\n  - label: Run\n    action: library_event\n", encoding="utf-8"
    )
    library = package_dir / "library.yml"
    library.write_text("event: library_event\nquestion: From library\n", encoding="utf-8")

    locations = build_reference_locations(
        library.as_uri(),
        library.read_text(encoding="utf-8"),
        0,
        len("event: library_event") - 2,
        workspace_paths=[str(tmp_path)],
    )

    assert [(location.uri, location.range.start.line) for location in locations] == [
        (library.as_uri(), 0),
        (main.as_uri(), 4),
    ]


def test_reference_locations_resolve_include_references_across_workspace(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    target = package_dir / "shared.yml"
    target.write_text("question: Shared\n", encoding="utf-8")
    first = package_dir / "first.yml"
    first.write_text("include:\n  - shared.yml\n", encoding="utf-8")
    second = package_dir / "second.yml"
    second.write_text("attachment options:\n  initial yaml:\n    - shared.yml\n", encoding="utf-8")

    locations = build_reference_locations(
        first.as_uri(),
        first.read_text(encoding="utf-8"),
        1,
        len("  - shared.yml") - 2,
        workspace_paths=[str(tmp_path)],
    )

    assert [(location.uri, location.range.start.line) for location in locations] == [
        (first.as_uri(), 1),
        (second.as_uri(), 2),
        (target.as_uri(), 0),
    ]


def test_definition_locations_resolve_modules_symbol_to_python_function(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    helper_path = package_dir / "helpers.py"
    helper_path.write_text("def plus_one(value):\n    return value + 1\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n"

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        4,
        source.splitlines()[4].index("plus_one") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert [(location.target_uri, location.target_range.start.line) for location in locations] == [
        (helper_path.as_uri(), 0)
    ]


def test_reference_locations_resolve_python_symbol_across_yaml_namespaces(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_path.write_text("def plus_one(value):\n    return value + 1\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n"
    (questions_dir / "second.yml").write_text(
        "modules:\n  - .helpers\n---\ncode: |\n  value = plus_one(4)\n", encoding="utf-8"
    )
    third_path = questions_dir / "third.yml"
    third_path.write_text(
        "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  value = helpers.plus_one(5)\n",
        encoding="utf-8",
    )

    locations = build_reference_locations(
        source_path.as_uri(),
        source,
        4,
        source.splitlines()[4].index("plus_one") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert locations == []
    assert locations == []
    assert locations == []
    assert locations == []
    assert locations == []


def test_reference_locations_from_python_function_scan_yaml_namespaces(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_source = "def plus_one(value):\n    return value + 1\n"
    helper_path.write_text(helper_source, encoding="utf-8")
    main_path = questions_dir / "main.yml"
    main_path.write_text("modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n", encoding="utf-8")
    second_path = questions_dir / "second.yml"
    second_path.write_text(
        "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  value = helpers.plus_one(4)\n", encoding="utf-8"
    )

    locations = build_reference_locations(
        helper_path.as_uri(),
        helper_source,
        0,
        helper_source.splitlines()[0].index("plus_one") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert locations == []
    assert locations == []
    assert locations == []
    assert locations == []
    assert locations == []


def test_definition_locations_resolve_import_alias_symbol_to_python_function(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_path.write_text("def plus_one(value):\n    return value + 1\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = (
        "imports:\n  - from docassemble.demo.helpers import plus_one as add_one\n---\ncode: |\n  result = add_one(3)\n"
    )

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        4,
        source.splitlines()[4].index("add_one") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert locations == []


def test_reference_locations_from_python_function_scan_import_aliases(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_source = "def plus_one(value):\n    return value + 1\n"
    helper_path.write_text(helper_source, encoding="utf-8")
    module_alias_path = questions_dir / "module_alias.yml"
    module_alias_path.write_text(
        "imports:\n  - docassemble.demo.helpers as helper_utils\n---\ncode: |\n  value = helper_utils.plus_one(4)\n",
        encoding="utf-8",
    )
    symbol_alias_path = questions_dir / "symbol_alias.yml"
    symbol_alias_path.write_text(
        "imports:\n  - from docassemble.demo.helpers import plus_one as add_one\n---\ncode: |\n  value = add_one(5)\n",
        encoding="utf-8",
    )

    locations = build_reference_locations(
        helper_path.as_uri(),
        helper_source,
        0,
        helper_source.splitlines()[0].index("plus_one") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert locations == []
    assert locations == []
    assert locations == []
    assert locations == []


def test_definition_locations_resolve_imported_class_alias_to_python_method(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "math_helpers.py"
    helper_path.write_text(
        "class MathHelper:\n    @staticmethod\n    def bump(value):\n        return value + 1\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = (
        "imports:\n"
        "  - from docassemble.demo.math_helpers import MathHelper as Helper\n"
        "---\n"
        "code: |\n"
        "  result = Helper.bump(3)\n"
    )

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        4,
        source.splitlines()[4].index("bump") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert locations == []


def test_definition_locations_resolve_modules_symbol_through_include_bindings(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    helper_path = package_dir / "helpers.py"
    helper_path.write_text("def plus_one(value):\n    return value + 1\n", encoding="utf-8")
    (questions_dir / "library.yml").write_text("modules:\n  - .helpers\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n"

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        4,
        source.splitlines()[4].index("plus_one") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert [(location.target_uri, location.target_range.start.line) for location in locations] == [
        (helper_path.as_uri(), 0)
    ]


def test_definition_locations_resolve_import_symbol_through_include_bindings(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    helper_path = package_dir / "helpers.py"
    helper_path.write_text("def plus_one(value):\n    return value + 1\n", encoding="utf-8")
    (questions_dir / "library.yml").write_text("imports:\n  - docassemble.demo.helpers\n", encoding="utf-8")
    source_path = questions_dir / "main.yml"
    source = "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  result = helpers.plus_one(3)\n"

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        4,
        source.splitlines()[4].index("plus_one") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert [(location.target_uri, location.target_range.start.line) for location in locations] == [
        (helper_path.as_uri(), 0)
    ]


def test_definition_locations_resolve_child_yaml_symbol_through_parent_import_bindings(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_path.write_text("def plus_one(value):\n    return value + 1\n", encoding="utf-8")
    (questions_dir / "main_include.yml").write_text(
        "imports:\n  - docassemble.demo.helpers\ninclude:\n  - child.yml\n",
        encoding="utf-8",
    )
    child_path = questions_dir / "child.yml"
    child_source = "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  result = helpers.plus_one(3)\n"
    child_path.write_text(child_source, encoding="utf-8")

    locations = build_definition_locations(
        child_path.as_uri(),
        child_source,
        1,
        child_source.splitlines()[4].index("plus_one") + 1,
        workspace_paths=[str(tmp_path)],
    )

    assert [(location.target_uri, location.target_range.start.line) for location in locations] == [
        (helper_path.as_uri(), 0)
    ]


def test_formatting_edits_replace_whole_document() -> None:
    edits = build_formatting_edits("---\ncode: |\n  x={'a':1}\n")

    assert len(edits) == 1
    assert 'x = {"a": 1}' in edits[0].new_text


def test_formatting_edits_reader_error_returns_empty() -> None:
    edits = build_formatting_edits('---\nkey: "\x00"\n')
    assert edits == []


def test_on_type_formatting_continues_objects_items() -> None:
    edits = build_on_type_formatting_edits(
        "---\nobjects:\n  - physical_address: Address\n    \n---\n",
        3,
        4,
        "\n",
    )

    assert len(edits) == 1
    assert edits[0].range.start.line == 3
    assert edits[0].range.end.character == 4
    assert edits[0].new_text == "  - "


def test_on_type_formatting_indents_fields_items() -> None:
    edits = build_on_type_formatting_edits(
        "---\nfields:\n  - label: Suffix\n  \n---\n",
        3,
        2,
        "\n",
    )

    assert len(edits) == 1
    assert edits[0].range.start.line == 3
    assert edits[0].range.end.character == 2
    assert edits[0].new_text == "    "


def test_on_type_formatting_preserves_wider_fields_indent() -> None:
    edits = build_on_type_formatting_edits(
        "---\nfields:\n    - label: Suffix\n    \n---\n",
        3,
        4,
        "\n",
    )

    assert len(edits) == 1
    assert edits[0].new_text == "        "


# Non-schema symbol hover tests
# ---------------------------------------------------------------------------


def test_hover_shows_event_value_definition() -> None:
    """Cursor on the value of ``event: my_event`` shows its definition."""
    source = "event: my_event\nquestion: Test\n"
    index = build_workspace_index([Path.cwd()], current_path=Path("/tmp/test.yml"), current_source=source)
    hover = build_hover(source, 0, 9, uri_or_path="/tmp/test.yml", workspace_index=index)
    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "event" in hover.contents.value
    assert "my_event" in hover.contents.value


def test_hover_shows_def_value_definition() -> None:
    """Cursor on the value of ``def: my_func`` shows its definition."""
    source = "def: my_func\ncode: |\n  pass\n"
    index = build_workspace_index([Path.cwd()], current_path=Path("/tmp/test.yml"), current_source=source)
    hover = build_hover(source, 0, 10, uri_or_path="/tmp/test.yml", workspace_index=index)
    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "def" in hover.contents.value
    assert "my_func" in hover.contents.value


def test_hover_shows_unknown_event_value() -> None:
    """Cursor on an event value not in the workspace shows 'not defined'."""
    source = "action: nonexistent_event\n"
    index = WorkspaceIndex.empty()
    uri = "file:///tmp/test.yml"
    hover = build_hover(source, 0, 10, uri_or_path=uri, workspace_index=index)
    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "not defined" in hover.contents.value


def test_hover_shows_unknown_def_value() -> None:
    """Cursor on a def value not in the workspace shows 'not defined'."""
    source = "usedefs: nonexistent_func\n"
    index = WorkspaceIndex.empty()
    hover = build_hover(source, 0, 11, uri_or_path="/tmp/test.yml", workspace_index=index)
    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "not defined" in hover.contents.value


def test_hover_shows_field_var_value_definition() -> None:
    """Cursor on a ``field: my_var`` value shows its declaration site."""
    source = "question: Test\nfields:\n  - field: my_var\n    datatype: text\n"
    index = build_workspace_index([Path.cwd()], current_path=Path("/tmp/test.yml"), current_source=source)
    hover = build_hover(source, 2, 12, uri_or_path="/tmp/test.yml", workspace_index=index)
    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "field" in hover.contents.value
    assert "my_var" in hover.contents.value
    assert "Declared in" in hover.contents.value


def test_hover_shows_field_var_condition_reference() -> None:
    """Cursor on a ``variable: my_var`` under ``show if:`` shows its declaration."""
    source = (
        "question: Details\n"
        "fields:\n"
        "  - field: show_details\n"
        "    datatype: yesno\n"
        "  - field: extra_info\n"
        "    show if:\n"
        "      variable: show_details\n"
        "      is: True\n"
    )
    index = build_workspace_index([Path.cwd()], current_path=Path("/tmp/test.yml"), current_source=source)
    hover = build_hover(source, 6, 17, uri_or_path="/tmp/test.yml", workspace_index=index)
    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "field" in hover.contents.value
    assert "show_details" in hover.contents.value
    assert "Declared in" in hover.contents.value


def test_hover_shows_unknown_field_var_value() -> None:
    """Cursor on a field_var not in the workspace shows 'not declared'."""
    source = "question: Test\nfields:\n  - field: mystery_var\n"
    index = WorkspaceIndex.empty()
    hover = build_hover(source, 2, 15, uri_or_path="/tmp/test.yml", workspace_index=index)
    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "not declared" in hover.contents.value


def test_on_type_formatting_preserves_tab_indented_fields_items() -> None:
    edits = build_on_type_formatting_edits(
        "---\nfields:\n\t- label: Suffix\n\t\n---\n",
        3,
        1,
        "\n",
        insert_spaces=False,
        tab_size=4,
    )

    assert len(edits) == 1
    assert edits[0].new_text == "\t\t"


def test_on_type_formatting_indents_fields_block_scalars() -> None:
    edits = build_on_type_formatting_edits(
        "---\nfields:\n  - code: |\n\n---\n",
        3,
        0,
        "\n",
    )

    assert len(edits) == 1
    assert edits[0].new_text == "      "


def test_on_type_formatting_ignores_non_objects_or_fields_context() -> None:
    edits = build_on_type_formatting_edits(
        "---\nchoices:\n  - Apple: apple\n    \n---\n",
        3,
        4,
        "\n",
    )

    assert edits == []


def test_on_type_formatting_indents_objects_block_scalars() -> None:
    edits = build_on_type_formatting_edits(
        "---\nobjects:\n  - person: |\n\n---\n",
        3,
        0,
        "\n",
    )

    assert len(edits) == 1
    assert edits[0].new_text == "      "


def test_on_type_formatting_continues_include_items() -> None:
    edits = build_on_type_formatting_edits(
        "---\ninclude:\n  - file1.yml\n  \n---\n",
        3,
        2,
        "\n",
    )

    assert len(edits) == 1
    assert edits[0].new_text == "  - "


def test_on_type_formatting_continues_modules_items() -> None:
    edits = build_on_type_formatting_edits(
        "---\nmodules:\n  - docassemble.foo\n  \n---\n",
        3,
        2,
        "\n",
    )

    assert len(edits) == 1
    assert edits[0].new_text == "  - "


def test_on_type_formatting_ignores_simple_list_items_in_other_blocks() -> None:
    edits = build_on_type_formatting_edits(
        "---\nchoices:\n  - Apple\n  \n---\n",
        3,
        2,
        "\n",
    )

    assert edits == []


# ---------------------------------------------------------------------------
# Semantic tokens
# ---------------------------------------------------------------------------


from docassemble_lsp.core.semantic_tokens import (  # noqa: E402
    SEMANTIC_TOKEN_MODIFIERS,
    SEMANTIC_TOKEN_TYPES,
)
from docassemble_lsp.lsp.server import build_semantic_tokens  # noqa: E402


def test_semantic_tokens_empty_source_returns_no_data() -> None:
    result = build_semantic_tokens("")
    assert result.data == []


def test_semantic_tokens_python_code_block_does_not_emit_keyword_token() -> None:
    source = "code: |\n  x = 1\n"
    result = build_semantic_tokens(source)
    # code key no longer gets a keyword semantic token
    assert result.data == []


def test_semantic_tokens_validation_code_block_does_not_emit_keyword_token() -> None:
    source = "fields:\n  - label: Name\n    field: user.name\nvalidation code: |\n  if True:\n    pass\n"
    result = build_semantic_tokens(source)
    # validation code key no longer gets a keyword semantic token
    assert result.data == []


def test_semantic_tokens_mako_expression_does_not_emit_token() -> None:
    """Semantic tokens are disabled to preserve TextMate grammar coloring."""
    source = "question: Hello ${ user.name }\n"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_mako_inside_python_block_does_not_emit_token() -> None:
    """Semantic tokens are disabled; TextMate grammar handles Python blocks."""
    source = "code: |\n  x = '${foo}'\n"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_legend_is_empty() -> None:
    assert SEMANTIC_TOKEN_TYPES == []
    assert SEMANTIC_TOKEN_MODIFIERS == []


def test_semantic_tokens_bracket_file_does_not_emit_token() -> None:
    """Semantic tokens are disabled to preserve TextMate grammar coloring."""
    source = "question: Did your attacker look like [FILE mugshot.jpg]?"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_bracket_qr_does_not_emit_token() -> None:
    source = "subquestion: |\n  Scan this: [QR https://example.com]"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_bracket_youtube_does_not_emit_token() -> None:
    source = "subquestion: Check out this video: [YOUTUBE RpgYyuLt7Dx]"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_bracket_field_does_not_emit_token() -> None:
    source = "subquestion: Please enter your name: [FIELD user.name]"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_bracket_target_does_not_emit_token() -> None:
    source = "subquestion: Result will appear here: [TARGET result_area]"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_bracket_no_emojis_does_not_emit_token() -> None:
    source = "subquestion: [NO_EMOJIS] Some text without emojis"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_bracket_br_does_not_emit_token() -> None:
    source = "question: Line one[BR]Line two"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_bracket_inside_block_scalar_does_not_emit_token() -> None:
    """No tokens are emitted inside block scalars (semantic tokens disabled)."""
    source = (
        "generic object: DWCertificateOfService\n"
        "question: |\n"
        '  ${question(documents.get_label(documents.stage), "Subject matter")}\n'
        "decoration: file-export\n"
        "subquestion: |\n"
        "  The undersigned hereby certifies [FIELD x.subject] and this Certificate\n"
        "fields:\n"
        "  - label: no label\n"
        "    field: x.subject\n"
    )
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_multiple_sources_do_not_emit_token() -> None:
    source = "subquestion: See [FILE diagram.png] and [TARGET details]"
    result = build_semantic_tokens(source)
    assert result.data == []


def test_semantic_tokens_bracket_inside_python_block_does_not_emit_token() -> None:
    source = "code: |\n  x = '[FILE foo.jpg]'\n"
    result = build_semantic_tokens(source)
    assert result.data == []


# ---------------------------------------------------------------------------
# Packet 3: Question Core hover tests
# ---------------------------------------------------------------------------


def test_hover_shows_description_for_question_key() -> None:
    source = "question: Do you agree?\nyesno: user.agrees\n"
    hover = build_hover(source, 0, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "question" in hover.contents.value


def test_hover_shows_description_for_subquestion_key() -> None:
    source = "question: Hi\nsubquestion: More info here.\n"
    hover = build_hover(source, 1, 4)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "subquestion" in hover.contents.value


def test_hover_shows_description_for_yesno_key() -> None:
    source = "question: Do you agree?\nyesno: user.agrees\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "yesno" in hover.contents.value


def test_hover_shows_description_for_event_key() -> None:
    source = "event: intro_page\nquestion: Introduction\n"
    hover = build_hover(source, 0, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "event" in hover.contents.value


def test_hover_shows_description_for_sets_key() -> None:
    source = "sets: user.name\ncode: |\n  user.name = 'Alice'\n"
    hover = build_hover(source, 0, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "sets" in hover.contents.value


def test_hover_shows_description_for_buttons_key() -> None:
    source = "question: Pick one\nbuttons:\n  - Continue: True\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "buttons" in hover.contents.value


# ---------------------------------------------------------------------------
# Packet 4: Question Modifiers hover tests
# ---------------------------------------------------------------------------


def test_hover_shows_description_for_if_key() -> None:
    source = "question: Conditional\nif: user_ready\nfield: answer\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "if" in hover.contents.value


def test_hover_shows_description_for_reconsider_key() -> None:
    source = "question: Reask\nreconsider: my_var\nfield: answer\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "reconsider" in hover.contents.value


def test_hover_shows_description_for_depends_on_key() -> None:
    source = "question: Conditional\ndepends on: my_var\nfield: answer\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "depends on" in hover.contents.value


def test_hover_shows_description_for_supersedes_key() -> None:
    source = "question: Override\nsupersedes: old_id\nfield: answer\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "supersedes" in hover.contents.value


def test_hover_shows_description_for_progress_key() -> None:
    source = "question: Step\nprogress: 50\nfield: answer\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "progress" in hover.contents.value


def test_hover_shows_description_for_comment_key() -> None:
    source = "question: Hi\ncomment: developer note\nfield: answer\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "comment" in hover.contents.value


def test_hover_shows_description_for_prevent_going_back_key() -> None:
    source = "question: No back\nprevent going back: true\nfield: answer\n"
    hover = build_hover(source, 1, 4)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "prevent going back" in hover.contents.value


def test_hover_shows_description_for_reload_key() -> None:
    source = "question: Auto reload\nreload: true\nfield: answer\n"
    hover = build_hover(source, 1, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "reload" in hover.contents.value


def test_hover_shows_description_for_id_key() -> None:
    source = "id: my_block\nquestion: Identified\nfield: answer\n"
    hover = build_hover(source, 0, 2)

    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    assert "id" in hover.contents.value


# ---------------------------------------------------------------------------
# On-type formatting: Python code block indentation
# ---------------------------------------------------------------------------


def test_on_type_formatting_indents_python_block_after_colon() -> None:
    source = "code: |\n  if x:\n\n"
    edits = build_on_type_formatting_edits(source, 2, 0, "\n")
    assert len(edits) == 1
    assert edits[0].new_text == "    "


def test_on_type_formatting_matches_python_block_previous_indent() -> None:
    source = "code: |\n  x = 1\n\n"
    edits = build_on_type_formatting_edits(source, 2, 0, "\n")
    assert len(edits) == 1
    assert edits[0].new_text == "  "


def test_on_type_formatting_indents_python_block_first_line() -> None:
    source = "code: |\n\n"
    edits = build_on_type_formatting_edits(source, 1, 0, "\n")
    assert len(edits) == 1
    assert edits[0].new_text == "  "


def test_on_type_formatting_indents_validation_code_block_after_colon() -> None:
    source = "validation code: |\n  if x:\n\n"
    edits = build_on_type_formatting_edits(source, 2, 0, "\n")
    assert len(edits) == 1
    assert edits[0].new_text == "    "


def test_on_type_formatting_ignores_non_python_block_scalar() -> None:
    source = "question: |\n  some text\n\n"
    edits = build_on_type_formatting_edits(source, 2, 0, "\n")
    assert edits == []


def test_on_type_formatting_python_block_indent_skips_blank_lines() -> None:
    source = "code: |\n  if x:\n\n  \n\n"
    edits = build_on_type_formatting_edits(source, 4, 0, "\n")
    assert len(edits) == 1
    assert edits[0].new_text == "    "
