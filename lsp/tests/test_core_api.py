from __future__ import annotations

import pytest

import docassemble_lsp.core as core
from docassemble_lsp.core.validation_config import RuntimeOptions


def test_core_public_exports_match_supported_surface() -> None:
    assert set(core.__all__) == {
        "DocumentFact",
        "Diagnostic",
        "FixResult",
        "FormatResult",
        "FormatterConfig",
        "WorkspaceIndex",
        "analyze_path",
        "analyze_text",
        "build_document_facts",
        "build_workspace_index",
        "collect_yaml_files",
        "configure_logging",
        "fix_path",
        "fix_text",
        "format_path",
        "format_text",
        "get_completions",
        "get_hover",
        "reset_logging",
        "resolve_definition_targets",
        "resolve_python_hover",
        "resolve_reference_targets",
        "resolve_workspace_symbol_targets",
    }


@pytest.mark.parametrize(
    "name",
    [
        "CompletionCandidate",
        "DEFAULT_LINT_MODE",
        "DefinitionTarget",
        "HoverInfo",
        "RuntimeOptions",
        "WorkspaceSymbolTarget",
        "completion_scope",
        "diagnostic_to_dict",
        "load_schema",
    ],
)
def test_core_does_not_export_internal_helpers(name: str) -> None:
    assert name not in core.__all__
    with pytest.raises(AttributeError):
        getattr(core, name)


def test_core_fix_text_expands_all_field_label_shorthands() -> None:
    result = core.fix_text(
        "question: Hi\nfields:\n  - Name: user.name\n  - Age: user.age\n",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C102"})),
    )

    assert result.changed is True
    assert result.text == (
        "question: Hi\nfields:\n  - label: Name\n    field: user.name\n  - label: Age\n    field: user.age\n"
    )


def test_core_fix_text_rewrites_radio_datatype_with_choices_to_input_type() -> None:
    result = core.fix_text(
        'question: Hi\nfields:\n  - label: May we text you?\n    field: texting_allowed\n    datatype: radio\n    choices:\n      - "A"\n      - "B"\n',
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C103"})),
    )

    assert result.changed is True
    assert result.text == (
        'question: Hi\nfields:\n  - label: May we text you?\n    field: texting_allowed\n    input type: radio\n    choices:\n      - "A"\n      - "B"\n'
    )


def test_core_fix_text_skips_conventions_without_opt_in() -> None:
    result = core.fix_text("question: Hi\nfields:\n  - Name: user.name\n")

    assert result.changed is False
    assert result.text == "question: Hi\nfields:\n  - Name: user.name\n"
