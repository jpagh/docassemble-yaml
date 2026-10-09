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
from docassemble_lsp.core.question_ids import (
    has_usable_id,
    plan_missing_question_ids,
)
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
        runtime_options=RuntimeOptions(
            enabled_conventions=frozenset({"C102"}), show_warnings=False
        ),
    )

    assert result.changed is True
    assert result.text == (
        "question: Hi\nfields:\n  - label: Name\n    field: user.name\n  - label: Age\n    field: user.age\n"
    )


def test_core_fix_text_rewrites_radio_datatype_with_choices_to_input_type() -> None:
    result = core.fix_text(
        'question: Hi\nfields:\n  - label: May we text you?\n    field: texting_allowed\n    datatype: radio\n    choices:\n      - "A"\n      - "B"\n',
        runtime_options=RuntimeOptions(
            enabled_conventions=frozenset({"C103"}), show_warnings=False
        ),
    )

    assert result.changed is True
    assert result.text == (
        'question: Hi\nfields:\n  - label: May we text you?\n    field: texting_allowed\n    input type: radio\n    choices:\n      - "A"\n      - "B"\n'
    )


def test_core_fix_text_skips_conventions_without_opt_in() -> None:
    source = "id: hi\nquestion: Hi\nfields:\n  - Name: user.name\n"
    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source


_MISSING_ID_SOURCE = (
    "---\nquestion: What is your name?\n---\nquestion: WHAT is your NAME!?\n"
)


def test_core_fix_text_generates_unique_lowercase_ids() -> None:
    result = core.fix_text(_MISSING_ID_SOURCE)

    assert result.changed is True
    assert result.applied_codes == ("W608", "W608")
    assert 'id: "what is your name"\n' in result.text
    # The second screen differs only in case and punctuation, so the
    # uniqueness pass suffixes it instead of reusing the first ID.
    assert 'id: "what is your name 2"\n' in result.text


def test_core_fix_text_normalizes_apostrophes_punctuation_and_accents() -> None:
    source = (
        "---\nquestion: We didn\u2019t find Caf\u00e9\n"
        "---\nquestion: ${city_only_address}\n"
    )
    result = core.fix_text(source)

    assert 'id: "we didnt find caf\u00e9"\n' in result.text
    assert 'id: "city only address"\n' in result.text


def test_core_fix_text_keeps_mako_directives_literal_in_generated_id() -> None:
    source = (
        "question: |\n"
        "  % if filled_by_attorney:\n"
        "  Does ${ users[0] } want to be the guardian?\n"
        "  % else:\n"
        "  Do you want to be the guardian?\n"
        "  % endif\n"
    )
    result = core.fix_text(source)

    assert (
        'id: "if filled by attorney does users 0 want to be the guardian '
        'else do you want to be the guardian endif"\n'
    ) in result.text
    assert "% if filled_by_attorney:" in result.text


def test_core_fix_text_avoids_author_written_ids() -> None:
    source = "---\nid: hello world\nquestion: Other\n---\nquestion: Hello, World!\n"
    result = core.fix_text(source)

    assert result.text.count("id:") == 2
    assert 'id: "hello world 2"\n' in result.text


def test_core_fix_text_fills_empty_id_in_place() -> None:
    result = core.fix_text("question: Hello there\nid: # TODO\n")

    assert result.changed is True
    assert result.text == 'question: Hello there\nid: "hello there" # TODO\n'


def test_core_fix_text_missing_id_is_idempotent() -> None:
    first = core.fix_text(_MISSING_ID_SOURCE)
    second = core.fix_text(first.text)

    assert second.changed is False
    assert second.text == first.text
    assert second.applied_codes == ()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, False),
        ("", False),
        ("   ", False),
        ("\t\n", False),
        ("hello", True),
        (" hello ", True),
        (42, True),
        (0, True),
        (False, True),
        ([], True),
        ({}, True),
    ],
)
def test_has_usable_id_matches_w608_presence(value: object, expected: bool) -> None:
    assert has_usable_id(value) == expected


@pytest.mark.parametrize(
    "id_line",
    [None, "id:\n", 'id: ""\n', 'id: "  "\n', "id: 42\n", "id: hello\n"],
)
def test_missing_id_rule_and_plan_agree_on_presence(id_line: str | None) -> None:
    source = "question: Hello\n" + (id_line or "")

    reported = [
        diagnostic
        for diagnostic in core.analyze_text(source, path="sample.yml")
        if diagnostic.code == "W608"
    ]
    planned = plan_missing_question_ids(source)

    assert bool(reported) == bool(planned)


@pytest.mark.parametrize(
    "source", ["question: Hello\nid: 42\n", 'question: Hello\nid: "  "\n']
)
def test_core_fix_text_leaves_non_string_and_blank_ids_alone(
    source: str,
) -> None:
    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source
    assert result.applied_codes == ()


def test_core_fix_text_missing_id_with_other_id_shapes_is_idempotent() -> None:
    source = (
        "---\nid: 42\nquestion: Numeric\n"
        '---\nid: "  "\nquestion: Blank\n'
        "---\nquestion: Missing\n"
    )
    first = core.fix_text(source)
    second = core.fix_text(first.text)

    assert first.applied_codes == ("W608",)
    assert first.text.count("id:") == 3
    assert 'id: "missing"\n' in first.text
    assert second.changed is False
    assert second.text == first.text


def test_core_fix_text_declines_missing_id_in_jinja_template() -> None:
    source = "# use jinja\nquestion: Hi {{ name }}\n"

    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source


_DUPLICATE_ID_SOURCE = (
    "---\nid: shared\nquestion: First\n"
    "---\nid: shared\nquestion: Second\n"
    "---\nid: shared\nquestion: Third\n"
)


def test_core_fix_text_renames_later_duplicate_ids_with_counter() -> None:
    result = core.fix_text(_DUPLICATE_ID_SOURCE)

    assert result.changed is True
    assert result.applied_codes == ("W609", "W609")
    # The first occurrence keeps its ID; later ones get a deterministic suffix.
    assert result.text == (
        "---\nid: shared\nquestion: First\n"
        '---\nid: "shared 2"\nquestion: Second\n'
        '---\nid: "shared 3"\nquestion: Third\n'
    )


def test_core_fix_text_duplicate_id_skips_taken_suffixes() -> None:
    source = (
        "---\nid: shared\nquestion: First\n"
        "---\nid: shared 2\nquestion: Author suffix\n"
        "---\nid: shared\nquestion: Second\n"
    )
    result = core.fix_text(source)

    assert result.applied_codes == ("W609",)
    assert 'id: "shared 3"\n' in result.text
    assert "id: shared 2\n" in result.text


def test_core_fix_text_duplicate_id_keeps_author_text() -> None:
    source = (
        "---\nid: Caf\u00e9 Question!\nquestion: First\n"
        "---\nid: Caf\u00e9 Question!\nquestion: Second\n"
    )
    result = core.fix_text(source)

    assert 'id: "Caf\u00e9 Question! 2"\n' in result.text


def test_core_fix_text_duplicate_id_preserves_key_case_and_comment() -> None:
    source = (
        "---\nid: shared\nquestion: First\n"
        "---\nID: shared  # keep me\nquestion: Second\n"
    )
    result = core.fix_text(source)

    assert 'ID: "shared 2" # keep me\n' in result.text


def test_core_fix_text_duplicate_id_fix_is_idempotent() -> None:
    first = core.fix_text(_DUPLICATE_ID_SOURCE)
    second = core.fix_text(first.text)

    assert second.changed is False
    assert second.text == first.text
    assert second.applied_codes == ()


def test_core_fix_text_duplicate_and_missing_ids_stay_unique() -> None:
    source = (
        "---\nid: x\nquestion: First\n---\nid: x\nquestion: Second\n---\nquestion: x\n"
    )
    result = core.fix_text(source)

    assert result.changed is True
    assert 'id: "x 2"\n' in result.text
    assert 'id: "x 3"\n' in result.text
    assert not [
        diagnostic
        for diagnostic in core.analyze_text(result.text, path="sample.yml")
        if diagnostic.code in {"W608", "W609"}
    ]


def test_core_fix_text_renames_duplicate_ids_on_non_question_blocks() -> None:
    source = (
        "---\nid: shared\ncode: |\n  a = 1\n"
        "---\nid: shared\nmandatory: True\ncode: |\n  b = 1\n"
    )
    result = core.fix_text(source)

    assert result.applied_codes == ("W609",)
    assert 'id: "shared 2"\n' in result.text


_W502_SOURCE = (
    "id: colors\n"
    "question: What is your favorite color?\n"
    "fields:\n"
    "  - field: favorite_color\n"
    "  - field: backup_color\n"
)
_W502_LABEL = '  - label: "What is your favorite color?"\n'


def test_core_fix_text_labels_first_multifield_offender() -> None:
    result = core.fix_text(_W502_SOURCE)

    assert result.changed is True
    assert result.applied_codes == ("W502",)
    assert result.rejected == ()
    assert result.text == (
        "id: colors\n"
        "question: What is your favorite color?\n"
        "fields:\n"
        f"{_W502_LABEL}"
        "    field: favorite_color\n"
        "  - field: backup_color\n"
    )


def test_core_fix_text_labels_blank_and_no_label_shorthand_fields() -> None:
    blank = core.fix_text(
        "id: colors\nquestion: What is your favorite color?\n"
        "fields:\n  - label: ''\n    field: favorite_color\n  - field: other\n"
    )
    shorthand = core.fix_text(
        "id: colors\nquestion: What is your favorite color?\n"
        "fields:\n  - no label: favorite_color\n    default: blue\n"
        "  - field: other\n"
    )

    assert blank.changed is True
    assert blank.text == (
        "id: colors\nquestion: What is your favorite color?\nfields:\n"
        f"{_W502_LABEL}"
        "    field: favorite_color\n  - field: other\n"
    )
    assert shorthand.changed is True
    assert shorthand.text == (
        "id: colors\nquestion: What is your favorite color?\nfields:\n"
        f"{_W502_LABEL}"
        "    field: favorite_color\n    default: blue\n  - field: other\n"
    )


def test_core_fix_text_keeps_mako_directives_in_a_block_label() -> None:
    source = (
        "id: guardian\n"
        "question: |\n"
        "  % if filled_by_attorney:\n"
        "  Does ${ users[0] } want to be the guardian?\n"
        "  % else:\n"
        "  Do you want to be the guardian?\n"
        "  % endif\n"
        "fields:\n"
        "  - field: guardian_name\n"
        "  - field: guardian_email\n"
    )

    result = core.fix_text(source)

    assert result.changed is True
    assert result.text == (
        "id: guardian\n"
        "question: |\n"
        "  % if filled_by_attorney:\n"
        "  Does ${ users[0] } want to be the guardian?\n"
        "  % else:\n"
        "  Do you want to be the guardian?\n"
        "  % endif\n"
        "fields:\n"
        "  - label: |\n"
        "      % if filled_by_attorney:\n"
        "      Does ${ users[0] } want to be the guardian?\n"
        "      % else:\n"
        "      Do you want to be the guardian?\n"
        "      % endif\n"
        "    field: guardian_name\n"
        "  - field: guardian_email\n"
    )


def test_core_fix_text_labels_one_field_per_screen_and_is_idempotent() -> None:
    first = core.fix_text(_W502_SOURCE)
    second = core.fix_text(first.text)

    remaining = [
        diagnostic
        for diagnostic in core.analyze_text(first.text, path="sample.yml")
        if diagnostic.code == "W502"
    ]
    assert [diagnostic.line for diagnostic in remaining] == [6]
    assert second.changed is False
    assert second.text == first.text
    assert second.applied_codes == ()


def test_core_fix_text_declines_when_question_text_is_unavailable() -> None:
    source = "id: colors\nfields:\n  - field: favorite_color\n  - field: other\n"

    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source
    assert result.applied_codes == ()
    assert result.rejected == ()


def test_core_fix_text_declines_when_question_text_already_labels_a_field() -> None:
    source = (
        "id: colors\n"
        "question: What is your favorite color?\n"
        "fields:\n"
        "  - What is your favorite color?: favorite_color\n"
        "  - field: backup_color\n"
    )

    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source


def test_core_fix_text_declines_when_no_label_shorthand_already_has_a_field() -> None:
    source = (
        "id: colors\n"
        "question: What is your favorite color?\n"
        "fields:\n"
        "  - no label: favorite_color\n"
        "    field: favorite_color\n"
        "  - field: backup_color\n"
    )

    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source


def test_resolve_diagnostic_fixes_offers_w502_only_for_first_offender() -> None:
    diagnostics = core.analyze_text(_W502_SOURCE, path="sample.yml")

    fixes = resolve_diagnostic_fixes(
        _W502_SOURCE,
        [
            diagnostic
            for diagnostic in diagnostics
            if diagnostic.code == "W502" and diagnostic.line == 6
        ],
    )

    assert fixes == []


def test_validate_fix_candidates_accepts_w502_label_candidate() -> None:
    diagnostics = core.analyze_text(_W502_SOURCE, path="sample.yml")
    fixes = [
        fix
        for fix in resolve_diagnostic_fixes(_W502_SOURCE, diagnostics)
        if fix.code == "W502"
    ]

    validation = validate_fix_candidates(
        _W502_SOURCE,
        fixes,
        diagnostics=diagnostics,
        path="sample.yml",
    )

    assert [fix.code for fix in validation.accepted] == ["W502"]
    assert validation.rejected == ()


_YESNO_SHORTCUT_SOURCE = "id: agree\nquestion: Do you agree?\nyesno: user.agrees\n"


def test_core_fix_text_expands_yesno_shortcut() -> None:
    result = core.fix_text(_YESNO_SHORTCUT_SOURCE)

    assert result.changed is True
    assert result.applied_codes == ("W510",)
    assert result.rejected == ()
    assert result.text == (
        "id: agree\n"
        "question: Do you agree?\n"
        "fields:\n"
        "  - no label: user.agrees\n"
        "    datatype: yesnoradio\n"
    )


def test_core_fix_text_uses_matching_datatype_for_shortcut_variants() -> None:
    cases = {
        "noyes": "noyesradio",
        "yesnomaybe": "yesnomaybe",
        "noyesmaybe": "noyesmaybe",
    }

    for shortcut, datatype in cases.items():
        result = core.fix_text(
            f"id: agree\nquestion: Agree?\n{shortcut}: user.agrees\n"
        )

        assert result.applied_codes == ("W510",), shortcut
        assert f"    datatype: {datatype}\n" in result.text, shortcut


def test_core_fix_text_preserves_shortcut_inline_comment() -> None:
    result = core.fix_text(
        "id: agree\nquestion: Do you agree?\nyesno: user.agrees  # keep me\n"
    )

    assert result.text == (
        "id: agree\n"
        "question: Do you agree?\n"
        "fields: # keep me\n"
        "  - no label: user.agrees\n"
        "    datatype: yesnoradio\n"
    )


def test_core_fix_text_quotes_non_identifier_shortcut_targets() -> None:
    result = core.fix_text(
        "id: agree\nquestion: Do you agree?\nyesno: user['agrees']\n"
    )

    assert "  - no label: \"user['agrees']\"\n" in result.text
    assert "    datatype: yesnoradio\n" in result.text


def test_core_fix_text_declines_shortcut_when_fields_exists() -> None:
    source = (
        "id: agree\nquestion: Do you agree?\n"
        "fields:\n  - no label: other\n    datatype: yesnoradio\n"
        "yesno: user.agrees\n"
    )

    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source


def test_core_fix_text_declines_shortcut_with_multiple_shortcuts() -> None:
    source = "id: agree\nquestion: Agree?\nyesno: a\nnoyes: b\n"

    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source


def test_core_fix_text_declines_shortcut_with_non_string_value() -> None:
    source = "id: agree\nquestion: Do you agree?\nyesno:\n  - bad\n"

    result = core.fix_text(source)

    assert result.changed is False
    assert result.text == source


def test_core_fix_text_expands_one_shortcut_per_document() -> None:
    source = (
        "---\nid: a\nquestion: A?\nyesno: a\n---\nid: b\nquestion: B?\nyesnomaybe: b\n"
    )

    result = core.fix_text(source)

    assert result.applied_codes == ("W510", "W510")
    assert result.text == (
        "---\nid: a\nquestion: A?\nfields:\n  - no label: a\n    datatype: yesnoradio\n"
        "---\nid: b\nquestion: B?\nfields:\n  - no label: b\n    datatype: yesnomaybe\n"
    )


def test_core_fix_text_yesno_shortcut_is_idempotent() -> None:
    first = core.fix_text(_YESNO_SHORTCUT_SOURCE)
    second = core.fix_text(first.text)

    assert second.changed is False
    assert second.text == first.text
    assert second.applied_codes == ()


def test_validate_fix_candidates_accepts_w510_shortcut_candidate() -> None:
    diagnostics = core.analyze_text(_YESNO_SHORTCUT_SOURCE, path="sample.yml")
    fixes = [
        fix
        for fix in resolve_diagnostic_fixes(_YESNO_SHORTCUT_SOURCE, diagnostics)
        if fix.code == "W510"
    ]

    validation = validate_fix_candidates(
        _YESNO_SHORTCUT_SOURCE,
        fixes,
        diagnostics=diagnostics,
        path="sample.yml",
    )

    assert [fix.code for fix in validation.accepted] == ["W510"]
    assert validation.rejected == ()


def test_resolve_diagnostic_fixes_uses_unknown_key_diagnostic_line() -> None:
    """E301 now anchors to the key, so the fix resolves without a cursor line."""
    source = "---\nid: checked\nquestion: Checked\nqueston: Hi\n"
    diagnostics = core.analyze_text(source, path="sample.yml")

    fixes = resolve_diagnostic_fixes(source, diagnostics)

    assert [(fix.code, fix.edit.start_line, fix.edit.new_text) for fix in fixes] == [
        ("E301", 3, "question")
    ]


_C102_SOURCE = "question: Hi\nfields:\n  - Name: user.name\n"
_C102_OPTIONS = RuntimeOptions(
    enabled_conventions=frozenset({"C102"}), show_warnings=False
)


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
        show_warnings=False,
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

    both_enabled = RuntimeOptions(
        enabled_conventions=frozenset({"C102", "C103"}), show_warnings=False
    )
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

    only_c102 = RuntimeOptions(
        enabled_conventions=frozenset({"C102"}), show_warnings=False
    )
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
        show_warnings=False,
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
    options = RuntimeOptions(
        enabled_conventions=frozenset({"C102"}), show_warnings=False
    )
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
