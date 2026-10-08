from __future__ import annotations

import pytest

from docassemble_lsp import core
from docassemble_lsp.core.fixes import (
    ResolvedFix,
    SourceEdit,
    resolve_diagnostic_fixes,
    validate_fix_candidates,
)
from docassemble_lsp.core.messages import MessageCode, message_severity
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


_C102_SOURCE = "question: Hi\nfields:\n  - Name: user.name\n"
_C102_OPTIONS = RuntimeOptions(enabled_conventions=frozenset({"C102"}))


def _replace_source_fix(
    source: str, new_text: str, *, code: str = "C102"
) -> ResolvedFix:
    lines = source.splitlines() or [""]
    return ResolvedFix(
        code=code,
        title=f"Replace source with {new_text!r}",
        edit=SourceEdit(
            start_line=0,
            start_character=0,
            end_line=len(lines) - 1,
            end_character=len(lines[-1]),
            new_text=new_text,
        ),
    )


def _c102_diagnostics(source: str, options: RuntimeOptions) -> list[core.Diagnostic]:
    return core.analyze_text(source, path="sample.yml", runtime_options=options)


def test_validate_fix_candidates_accepts_real_convention_fix() -> None:
    diagnostics = _c102_diagnostics(_C102_SOURCE, _C102_OPTIONS)
    fixes = resolve_diagnostic_fixes(_C102_SOURCE, diagnostics)

    validation = validate_fix_candidates(
        _C102_SOURCE,
        fixes,
        diagnostics=diagnostics,
        path="sample.yml",
        runtime_options=_C102_OPTIONS,
    )

    assert [fix.code for fix in validation.accepted] == ["C102"]
    assert validation.rejected == ()


def test_validate_fix_candidates_rejects_candidate_that_introduces_new_finding() -> (
    None
):
    diagnostics = _c102_diagnostics(_C102_SOURCE, _C102_OPTIONS)
    fix = _replace_source_fix(_C102_SOURCE, "---\nfoo: bar\n")

    validation = validate_fix_candidates(
        _C102_SOURCE,
        [fix],
        diagnostics=diagnostics,
        path="sample.yml",
        runtime_options=_C102_OPTIONS,
    )

    assert validation.accepted == ()
    assert len(validation.rejected) == 1
    assert "E301" in validation.rejected[0].reason
    assert "E306" in validation.rejected[0].reason


def test_validate_fix_candidates_rejects_candidate_that_removes_nothing() -> None:
    diagnostics = _c102_diagnostics(_C102_SOURCE, _C102_OPTIONS)
    fix = _replace_source_fix(
        _C102_SOURCE, "question: Hello\nfields:\n  - Name: user.name\n"
    )

    validation = validate_fix_candidates(
        _C102_SOURCE,
        [fix],
        diagnostics=diagnostics,
        path="sample.yml",
        runtime_options=_C102_OPTIONS,
    )

    assert validation.accepted == ()
    assert len(validation.rejected) == 1
    assert "does not reduce" in validation.rejected[0].reason
    assert "C102" in validation.rejected[0].reason


def test_validate_fix_candidates_honours_ignored_codes() -> None:
    options = RuntimeOptions(
        enabled_conventions=frozenset({"C102"}),
        ignore_codes=frozenset({"E301", "E306"}),
    )
    diagnostics = _c102_diagnostics(_C102_SOURCE, options)
    fix = _replace_source_fix(_C102_SOURCE, "---\nfoo: bar\n")

    validation = validate_fix_candidates(
        _C102_SOURCE,
        [fix],
        diagnostics=diagnostics,
        path="sample.yml",
        runtime_options=options,
    )

    assert [resolved.code for resolved in validation.accepted] == ["C102"]


def test_validate_fix_candidates_honours_enabled_conventions() -> None:
    radio_source = (
        "question: Hi\nfields:\n  - label: Name\n    field: user.name\n"
        '    datatype: radio\n    choices:\n      - "A"\n'
    )
    fix = _replace_source_fix(_C102_SOURCE, radio_source)

    both_enabled = RuntimeOptions(enabled_conventions=frozenset({"C102", "C103"}))
    diagnostics = _c102_diagnostics(_C102_SOURCE, both_enabled)
    rejected = validate_fix_candidates(
        _C102_SOURCE,
        [fix],
        diagnostics=diagnostics,
        path="sample.yml",
        runtime_options=both_enabled,
    )
    assert rejected.accepted == ()
    assert "C103" in rejected.rejected[0].reason

    only_c102 = RuntimeOptions(enabled_conventions=frozenset({"C102"}))
    diagnostics = _c102_diagnostics(_C102_SOURCE, only_c102)
    accepted = validate_fix_candidates(
        _C102_SOURCE,
        [fix],
        diagnostics=diagnostics,
        path="sample.yml",
        runtime_options=only_c102,
    )
    assert [resolved.code for resolved in accepted.accepted] == ["C102"]


def test_validate_fix_candidates_rejects_parse_failure_even_when_ignored() -> None:
    options = RuntimeOptions(
        enabled_conventions=frozenset({"C102"}),
        ignore_codes=frozenset({"E102"}),
    )
    diagnostics = _c102_diagnostics(_C102_SOURCE, options)
    fix = _replace_source_fix(_C102_SOURCE, "fields: [\n")

    validation = validate_fix_candidates(
        _C102_SOURCE,
        [fix],
        diagnostics=diagnostics,
        path="sample.yml",
        runtime_options=options,
    )

    assert validation.accepted == ()
    assert "parse failure" in validation.rejected[0].reason
    assert "E102" in validation.rejected[0].reason


def test_validate_fix_candidates_rejects_overlapping_accepted_batch() -> None:
    source = "question: Hi\nfields:\n  - Name: user.name\n  - Age: user.age\n"
    options = RuntimeOptions(enabled_conventions=frozenset({"C102"}))
    diagnostics = _c102_diagnostics(source, options)
    name_line = "  - Name: user.name"
    fixes = [
        ResolvedFix(
            code="C102",
            title="Expand Name",
            edit=SourceEdit(
                2,
                0,
                2,
                len(name_line),
                new_text="  - label: Name\n    field: user.name",
            ),
        ),
        ResolvedFix(
            code="C102",
            title="Expand Age",
            edit=SourceEdit(
                2,
                0,
                2,
                len(name_line),
                new_text="  - label: Age\n    field: user.age",
            ),
        ),
    ]

    validation = validate_fix_candidates(
        source,
        fixes,
        diagnostics=diagnostics,
        path="sample.yml",
        runtime_options=options,
    )

    assert validation.accepted == ()
    assert len(validation.rejected) == 2
    assert all("overlapping" in rejection.reason for rejection in validation.rejected)


def test_fix_text_rejects_jinja_rendered_files_without_rewriting() -> None:
    source = "# use jinja\nquestion: Hi\nfields:\n  - Name: user.name\n"

    result = core.fix_text(source, runtime_options=_C102_OPTIONS)

    assert result.changed is False
    assert result.text == source
    assert result.applied_codes == ()
    assert len(result.rejected) == 1
    assert result.rejected[0].code == "C102"
    assert "Jinja" in result.rejected[0].reason


def test_message_code_c105_not_reserved() -> None:
    with pytest.raises(AttributeError):
        _ = MessageCode.C105


def test_message_severity_uses_code_prefix() -> None:
    assert message_severity("E301") == "error"
    assert message_severity("W502") == "warning"
    assert message_severity("C102") == "convention"
    assert message_severity("UNKNOWN") == "error"
    assert message_severity(None) == "error"
