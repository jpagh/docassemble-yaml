from __future__ import annotations

from pathlib import Path

from docassemble_lsp.core import analyze_text
from docassemble_lsp.core.messages import MessageCode
from docassemble_lsp.core.validation import all_dict_keys
from docassemble_lsp.core.validation_config import RuntimeOptions
from tests.corpus import (
    expected_codes_from_fixture_id,
    installed_example_top_level_keys,
    regression_fixture_documents,
    regression_fixture_text,
    repo_example_corpus_root,
    standalone_installed_example_blocks,
)


def test_analyze_text_surfaces_unknown_keys() -> None:
    diagnostics = analyze_text("---\nfoo: bar\n", path="sample.yml")

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E301" in codes
    assert "E306" in codes


def test_analyze_text_reports_signature_only_top_level_keys_without_signature() -> None:
    diagnostics = analyze_text("question: Sign here\nrequired: False\npen color: blue\n", path="sample.yml")

    e301 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E301")
    assert "required" in e301.message
    assert "pen color" in e301.message


def test_analyze_text_allows_signature_only_top_level_keys_with_signature() -> None:
    diagnostics = analyze_text(
        "question: Sign here\nsignature: user.signature\nrequired: False\npen color: blue\n",
        path="sample.yml",
    )

    assert "E301" not in {diagnostic.code for diagnostic in diagnostics}


def test_analyze_text_supports_jinja_include_from_source_directory(tmp_path: Path) -> None:
    included = tmp_path / "included.yml"
    included.write_text("question: Included question\n", encoding="utf-8")

    source = tmp_path / "interview.yml"
    content = '# use jinja\n{% include "included.yml" %}\nmandatory: True\n'

    diagnostics = analyze_text(content, path=str(source))

    assert diagnostics == []


def test_analyze_text_can_disallow_field_label_shorthand_by_option() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - Name: user.name\n",
        path="sample.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C102"})),
    )

    c102 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "C102")
    assert c102.line == 3
    assert c102.severity == "convention"


def test_analyze_text_hides_conventions_without_opt_in() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - Name: user.name\n",
        path="sample.yml",
    )

    assert {diagnostic.code for diagnostic in diagnostics} == set()


def test_analyze_text_allows_shorthand_label_named_like_modifier() -> None:
    diagnostics = analyze_text(
        "---\nquestion: Code?\nfields:\n  - Code: user_code\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E411" not in codes


def test_label_only_field_item_reports_missing_field_target() -> None:
    diagnostics = analyze_text(
        "question: |\n  How's the weather?\nfields:\n  - label: This is the label\n",
        path="sample.yml",
    )

    e414 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E414")
    assert e414.line == 4


def test_field_only_item_reports_missing_label() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field: user.name\n",
        path="sample.yml",
    )

    e415 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E415")
    assert e415.line == 3


def test_field_target_must_be_plain_text() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field:\n      x: 1\n    label: Name\n",
        path="sample.yml",
    )

    e416 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E416")
    assert e416.line == 4


def test_shorthand_field_target_must_be_valid_variable_name() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - Name: user name\n",
        path="sample.yml",
    )

    e417 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E417")
    assert e417.line == 3


def test_field_target_reports_docassemble_reserved_name() -> None:
    """Field targets using Docassemble reserved names should produce E931."""
    for reserved in ("nav", "url_args", "role", "self"):
        diagnostics = analyze_text(
            f"question: Hi\nfields:\n  - field: {reserved}\n    label: Reserved\n",
            path="sample.yml",
        )
        codes = {diagnostic.code for diagnostic in diagnostics}
        assert "E931" in codes, f"Expected E931 for reserved name {reserved!r}"


def test_field_target_allows_dotted_reserved_name() -> None:
    """Dotted names starting with a reserved prefix should NOT trigger E931 (object attributes are fine)."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field: user.role\n    label: User role\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E931" not in codes


def test_field_target_allows_generic_object_attribute_access() -> None:
    """Dotted access like ``x.decedent`` (generic object attribute) should NOT trigger E931."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Decedent\n    field: x.decedent\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E931" not in codes
    assert "C104" not in codes


def test_field_target_allows_iterator_names() -> None:
    """Bare `x` and `x[i]` are legitimate generic-object / list-collect patterns and should NOT trigger E931."""
    for source in (
        "question: Hi\nfields:\n  - field: x\n    label: X value\n",
        "question: Hi\nfields:\n  - field: x[i]\n    label: X indexed\n",
    ):
        diagnostics = analyze_text(source, path="sample.yml")
        codes = {diagnostic.code for diagnostic in diagnostics}
        assert "E931" not in codes, f"Unexpected E931 for:\n{source}"


def test_field_target_allows_bare_iterator_names_in_sets() -> None:
    """Bare iterator variable names in `sets` should NOT trigger E931."""
    diagnostics = analyze_text(
        "question: Hi\nsets: x\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E931" not in codes


def test_field_target_reports_underscore_prefix_convention() -> None:
    """Field targets starting with underscore should produce C104 convention warning."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field: _my_var\n    label: Custom\n",
        path="sample.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C104"})),
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "C104" in codes


def test_field_target_reports_underscore_prefix_for_dotted_name() -> None:
    """Dotted names where the top-level part starts with underscore should still trigger C104."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field: _internal.temp\n    label: Temp\n",
        path="sample.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C104"})),
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "C104" in codes


def test_sets_directive_reports_reserved_name() -> None:
    """The `sets` directive should produce E931 for Docassemble reserved names."""
    diagnostics = analyze_text(
        "question: Hi\nsets: nav\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E931" in codes

    diagnostics = analyze_text(
        "question: Hi\nsets:\n  - url_args\n  - role\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E931" in codes


def test_sets_directive_allows_non_reserved_names() -> None:
    """The `sets` directive should NOT produce E931 for normal variable names."""
    diagnostics = analyze_text(
        "question: Hi\nsets: user.name\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E931" not in codes


def test_explicit_label_and_shorthand_key_reports_overwrite_syntax_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Explicit\n    Name: user.name\n    field: user.name\n",
        path="sample.yml",
    )

    e418 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E418")
    assert e418.line == 4


def test_label_above_field_is_not_treated_as_shorthand_label() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Letterhead\n    label above field: True\n    field: user.letterhead\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E418" not in codes


def test_floating_label_is_not_treated_as_shorthand_label() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Name\n    floating label: True\n    field: user.name\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E418" not in codes


def test_multiple_choice_field_requires_choices() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n",
        path="sample.yml",
    )

    e419 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E419")
    assert e419.line == 5


def test_ajax_field_requires_action() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    input type: ajax\n",
        path="sample.yml",
    )

    e420 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E420")
    assert e420.line == 5


def test_ajax_field_cannot_declare_choices_directly() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    input type: ajax\n    action: choose_thing\n    choices:\n      - A\n",
        path="sample.yml",
    )

    e421 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E421")
    assert e421.line == 5


def test_note_and_html_cannot_be_combined_in_single_field() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - note: Hello\n    html: <b>Hello</b>\n",
        path="sample.yml",
    )

    e423 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E423")
    assert e423.line == 4


def test_non_dict_field_list_item_is_rejected() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - just text\n",
        path="sample.yml",
    )

    e424 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E424")
    assert e424.line == 1


def test_object_field_exclude_and_default_formats_follow_upstream_rules() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices: things\n    exclude:\n      bad: 1\n    default:\n      bad: 1\n",
        path="sample.yml",
    )

    e426 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E426")
    e427 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E427")
    assert e426.line == 7
    assert e427.line == 9


def test_hidden_field_invalid_datatype_follows_upstream_rule() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field: upload\n    input type: hidden\n    datatype: file\n",
        path="sample.yml",
    )

    e425 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E425")
    assert e425.line == 5


def test_yesnoradio_choices_errors_that_boolean_overrides_choices() -> None:
    diagnostics = analyze_text(
        'question: Hi\nfields:\n  - label: May we text you?\n    field: texting_allowed\n    datatype: yesnoradio\n    choices:\n      - "A"\n      - "B"\n    required: False\n',
        path="sample.yml",
    )

    e534 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E534")
    assert e534.line == 6
    assert e534.severity == "error"


def test_yesnomaybe_code_errors_that_boolean_overrides_code() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: May we contact you?\n    field: contact_allowed\n    datatype: yesnomaybe\n    code: contact_choices\n",
        path="sample.yml",
    )

    e534 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E534")
    assert e534.line == 6
    assert e534.severity == "error"


def test_radio_datatype_with_choices_prefers_input_type_convention() -> None:
    diagnostics = analyze_text(
        'question: Hi\nfields:\n  - label: May we text you?\n    field: texting_allowed\n    datatype: radio\n    choices:\n      - "A"\n      - "B"\n    required: False\n',
        path="sample.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C103"})),
    )

    c103 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "C103")
    assert c103.line == 5
    assert c103.severity == "convention"


def test_analyze_text_can_ignore_specific_codes() -> None:
    diagnostics = analyze_text(
        "---\nfoo: bar\n",
        path="sample.yml",
        runtime_options=RuntimeOptions(ignore_codes=frozenset({"E301", "E306"})),
    )

    assert diagnostics == []


def test_runtime_options_allows_code_respects_show_warnings() -> None:
    opts = RuntimeOptions(show_warnings=False)
    assert opts.allows_code("W503") is False
    assert opts.allows_code("E301") is True
    assert opts.allows_code(None) is True

    opts_default = RuntimeOptions()
    assert opts_default.allows_code("W503") is True


def test_analyze_text_hides_warnings_with_show_warnings_false() -> None:
    source = """\
---
attachments:
  - filename: test.docx
"""
    diagnostics = analyze_text(source, path="sample.yml")
    codes = {d.code for d in diagnostics if d.code}
    assert "W503" in codes

    diagnostics_no_warn = analyze_text(
        source,
        path="sample.yml",
        runtime_options=RuntimeOptions(show_warnings=False),
    )
    codes_no_warn = {d.code for d in diagnostics_no_warn if d.code}
    assert "W503" not in codes_no_warn


def test_file_wide_tagged_pdf_suppresses_warning() -> None:
    source = """\
---
features:
  tagged pdf: true
---
attachments:
  - filename: test.docx
"""
    diagnostics = analyze_text(source, path="sample.yml")
    codes = {d.code for d in diagnostics if d.code}
    assert "W503" not in codes


def test_file_wide_tagged_pdf_inline_syntax_suppresses_warning() -> None:
    source = """\
---
features: {tagged pdf: true}
---
attachments:
  - filename: test.docx
"""
    diagnostics = analyze_text(source, path="sample.yml")
    codes = {d.code for d in diagnostics if d.code}
    assert "W503" not in codes


def test_file_wide_tagged_pdf_respects_explicit_false() -> None:
    source = """\
---
features:
  tagged pdf: true
---
features:
  tagged pdf: false
attachments:
  - filename: test.docx
"""
    diagnostics = analyze_text(source, path="sample.yml")
    codes = {d.code for d in diagnostics if d.code}
    assert "W503" in codes


def test_object_labeler_requires_object_datatype() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    datatype: text\n    object labeler: thing_label\n",
        path="sample.yml",
    )

    e422 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E422")
    assert e422.line == 6


def test_need_phrase_must_be_text_or_list() -> None:
    diagnostics = analyze_text(
        "question: Hi\nneed:\n  invalid: value\n",
        path="sample.yml",
    )

    e428 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E428")
    assert e428.line == 2


def test_need_dict_only_allows_pre_or_post_keys() -> None:
    diagnostics = analyze_text(
        "question: Hi\nneed:\n  - wrong: value\n",
        path="sample.yml",
    )

    e429 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E429")
    assert e429.line == 3


def test_need_pre_and_post_must_be_text_or_list() -> None:
    diagnostics = analyze_text(
        "question: Hi\nneed:\n  - post:\n      bad: value\n",
        path="sample.yml",
    )

    e430 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E430")
    assert e430.line == 3


def test_need_items_must_be_text_strings() -> None:
    diagnostics = analyze_text(
        "question: Hi\nneed:\n  - pre:\n      - ok\n      - 5\n",
        path="sample.yml",
    )

    e431 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E431")
    assert e431.line == 3


def test_on_change_must_be_dictionary() -> None:
    diagnostics = analyze_text(
        "on change: nope\n",
        path="sample.yml",
    )

    e432 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E432")
    assert e432.line == 1


def test_on_change_cannot_have_other_top_level_keys() -> None:
    diagnostics = analyze_text(
        "question: Hi\non change:\n  user.name: |\n    x = 1\n",
        path="sample.yml",
    )

    e433 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E433")
    assert e433.line == 2


def test_on_change_entries_must_map_strings_to_python_code() -> None:
    diagnostics = analyze_text(
        "on change:\n  user.name:\n    bad: value\n",
        path="sample.yml",
    )

    e434 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E434")
    assert e434.line == 2


def test_action_buttons_must_be_list_or_code_dict() -> None:
    diagnostics = analyze_text(
        "question: Hi\naction buttons: nope\n",
        path="sample.yml",
    )

    e435 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E435")
    assert e435.line == 2


def test_action_button_arguments_must_be_plain_items() -> None:
    diagnostics = analyze_text(
        "question: Hi\naction buttons:\n  - label: Run\n    action: go\n    arguments:\n      bad:\n        nested: value\n",
        path="sample.yml",
    )

    e446 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E446")
    assert e446.line == 5


def test_translations_must_be_list() -> None:
    diagnostics = analyze_text(
        "translations: nope\n",
        path="sample.yml",
    )

    e447 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E447")
    assert e447.line == 1


def test_translations_items_must_be_text_with_valid_suffix_and_path() -> None:
    diagnostics = analyze_text(
        "translations:\n  - 5\n  - wrong.txt\n  - package:wrong.xlsx\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E448" in codes
    assert "E449" in codes
    assert "E450" in codes


def test_if_must_be_text_or_list() -> None:
    diagnostics = analyze_text(
        "if:\n  bad: value\n",
        path="sample.yml",
    )

    e451 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E451")
    assert e451.line == 1


def test_require_must_be_list_and_have_dict_orelse() -> None:
    diagnostics = analyze_text(
        "require: nope\n",
        path="sample.yml",
    )
    e452 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E452")
    assert e452.line == 1

    diagnostics = analyze_text(
        "require:\n  - user.name\n",
        path="sample.yml",
    )
    e453 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E453")
    assert e453.line == 1

    diagnostics = analyze_text(
        "require:\n  - user.name\norelse: nope\n",
        path="sample.yml",
    )
    e454 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E454")
    assert e454.line == 3


def test_terms_and_auto_terms_shapes_follow_upstream_list_rules() -> None:
    diagnostics = analyze_text(
        "terms: nope\nauto terms: nope\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E455" in codes
    assert "E457" in codes

    diagnostics = analyze_text(
        "terms:\n  - nope\nauto terms:\n  - nope\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E456" in codes
    assert "E458" in codes


def test_default_language_must_be_string() -> None:
    """The `default language` key must be a plain string, not a list or object."""
    diagnostics = analyze_text(
        "default language: en\n",
        path="sample.yml",
    )
    assert "E103" not in {diagnostic.code for diagnostic in diagnostics}

    diagnostics = analyze_text(
        "default language:\n  - en\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E103" in codes


def test_language_modifier_accepts_plain_string() -> None:
    """The `language` key (as a block modifier) must be a plain string."""
    diagnostics = analyze_text(
        "question: Hi\nlanguage: es\n",
        path="sample.yml",
    )
    assert "E103" not in {diagnostic.code for diagnostic in diagnostics}

    diagnostics = analyze_text(
        "question: Hi\nlanguage:\n  - es\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E103" in codes


def test_validator_known_top_level_keys_cover_installed_example_corpus() -> None:
    missing = installed_example_top_level_keys() - set(all_dict_keys) - {"required", "pen color"}

    assert not missing


def test_analyze_text_accepts_installed_example_standalone_block_forms() -> None:
    failures: list[str] = []

    for block_name, path, source in standalone_installed_example_blocks():
        codes = {diagnostic.code for diagnostic in analyze_text(source, path=path)}
        if "E306" in codes:
            failures.append(f"{block_name} ({path})")

    assert not failures


def test_example_corpus_has_no_error_diagnostics() -> None:
    failures: list[str] = []

    for path in sorted(repo_example_corpus_root().rglob("*.yml")):
        text = path.read_text(encoding="utf-8")
        runtime_options = RuntimeOptions(show_warnings=False)
        diagnostics = analyze_text(text, path=str(path), runtime_options=runtime_options)
        errors = [d for d in diagnostics if d.code and d.code.startswith("E")]
        for error in errors:
            failures.append(f"{path}:{error.line}: {error.code} {error.message}")

    assert not failures, "\n".join(failures)


def test_analyze_text_accepts_response_family_block_forms() -> None:
    cases = [
        "---\nresponse: ok\n",
        "---\nbinaryresponse: ok\ncontent type: application/octet-stream\nresponse code: 200\n",
        "---\nall_variables: true\ninclude_internal: true\nresponse code: 200\n",
        "---\nresponse filename: out.txt\ncontent type: text/plain\n",
        "---\nredirect url: https://example.com\n",
        "---\nnull response: true\nresponse code: 204\n",
        "---\nbackgroundresponse: ok\n",
        "---\naction: refresh\n",
    ]

    for content in cases:
        assert analyze_text(content, path="sample.yml") == []


def test_analyze_text_accepts_crlf_multi_document_streams() -> None:
    diagnostics = analyze_text(
        "---\r\nmetadata:\r\n  title: Example\r\n---\r\nquestion: Hi\r\n",
        path="sample.yml",
    )

    assert diagnostics == []


def test_empty_question_value_reports_yaml_string_error_instead_of_crashing() -> None:
    diagnostics = analyze_text("question:\n", path="sample.yml")

    e103 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E103")
    assert e103.line == 1


def test_validation_code_c101_anchors_to_validation_code_key_line() -> None:
    content = """---
question: Event
fields:
    - Start: event.begin
    - End: event.end
validation code: |
    if event.end < event.begin:
        raise DAValidationError('End must be after start', field='event.end')
"""

    diagnostics = analyze_text(
        content,
        path="sample.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C101"})),
    )

    c101 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "C101")
    assert c101.line == 6


def test_yaml_parse_error_anchors_to_problem_line() -> None:
    diagnostics = analyze_text(
        "---\nquestion: Hello\nfield: x\nbad: [unclosed\n",
        path="sample.yml",
    )

    e102 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E102")
    assert e102.line == 4
    assert e102.message.startswith("while parsing a flow sequence: expected ',' or ']', but got '<stream end>'")
    assert 'in "<unicode string>"' not in e102.message
    assert "bad: [unclosed" in e102.message


def test_jinja_syntax_error_anchors_to_template_line() -> None:
    diagnostics = analyze_text(
        "# use jinja\n---\nid: jinja_syntax\nquestion: {% if %}\n",
        path="sample.yml",
    )

    e201 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E201")
    assert e201.line == 4


def test_jinja_template_error_anchors_to_template_line() -> None:
    diagnostics = analyze_text(
        "# use jinja\n---\nid: jinja_template\nquestion: {{ [1]|map('missing_filter')|list }}\n",
        path="sample.yml",
    )

    e202 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E202")
    assert e202.line == 4


def test_top_level_jinja_without_header_reports_missing_header_hint() -> None:
    diagnostics = analyze_text(
        "{% set jinja_documents_available = ({'x': 1}) %}\n---\nquestion: Hi\n",
        path="sample.yml",
    )

    e102 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E102")
    assert e102.line == 1
    assert "# use jinja" in e102.message
    assert "{% set jinja_documents_available" in e102.message


def test_python_code_syntax_anchors_to_code_body_line() -> None:
    diagnostics = analyze_text(
        "---\ncode: |\n  if True\n    x = 1\n",
        path="sample.yml",
    )

    e122 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E122")
    assert e122.line == 3


def test_js_show_if_syntax_anchors_to_modifier_body_line() -> None:
    diagnostics = analyze_text(
        '---\nquestion: Test\nfields:\n  - Fruit: fruit\n  - Broken: broken\n    js show if: |\n      (val("fruit") === "apple"\n',
        path="sample.yml",
    )

    e204 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E204")
    assert e204.line == 7


def test_nested_visibility_anchors_to_deepest_field_line() -> None:
    diagnostics = analyze_text(
        "---\nquestion: Test\nfields:\n  - Fruit: fruit\n    datatype: yesnoradio\n  - Vegetable: vegetable\n    datatype: yesnoradio\n    show if: fruit\n  - Grain: grain\n    datatype: yesnoradio\n    show if: vegetable\n  - Dairy: dairy\n    datatype: yesnoradio\n    show if: grain\n",
        path="sample.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C106"})),
    )

    c106 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "C106")
    assert c106.line == 12


def test_interview_order_unmatched_guard_is_reported_once() -> None:
    diagnostics = analyze_text(
        """---
id: prior_one
question: First
fields:
  - A: a
  - B: b
    show if: a
---
id: prior_two
question: Second
fields:
  - C: c
  - Also B: b
    show if: c
---
mandatory: True
code: |
  b
""",
        path="sample.yml",
    )

    w603s = [diagnostic for diagnostic in diagnostics if diagnostic.code == "W603"]
    assert len(w603s) == 1
    assert w603s[0].line == 18
    assert w603s[0].severity == "warning"


def test_large_invalid_fixture_documents_match_expected_codes() -> None:
    aggregate_only_ids = {"WHOLEFILE_W603_interview_order_unmatched_guard"}
    runtime_options = RuntimeOptions(enabled_conventions=frozenset({"C101", "C106"}))

    for document_id, source in regression_fixture_documents("large_invalid_interview.yml"):
        if document_id in aggregate_only_ids:
            continue

        codes = {
            diagnostic.code
            for diagnostic in analyze_text(source, path=f"fixture:{document_id}", runtime_options=runtime_options)
            if diagnostic.code
        }
        expected = expected_codes_from_fixture_id(document_id)

        assert codes == expected, document_id


def test_large_invalid_fixture_whole_file_matches_expected_code_union() -> None:
    diagnostics = analyze_text(
        regression_fixture_text("large_invalid_interview.yml"),
        path="tests/fixtures/regressions/large_invalid_interview.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C101", "C106"})),
    )

    codes = {diagnostic.code for diagnostic in diagnostics if diagnostic.code}
    expected: set[str] = set()
    for document_id, _ in regression_fixture_documents("large_invalid_interview.yml"):
        expected.update(expected_codes_from_fixture_id(document_id))

    assert codes == expected


def test_large_valid_fixture_has_no_diagnostics() -> None:
    diagnostics = analyze_text(
        regression_fixture_text("large_valid_interview.yml"),
        path="tests/fixtures/regressions/large_valid_interview.yml",
    )

    assert diagnostics == []


def test_large_jinja_regression_fixtures_match_expected_codes() -> None:
    cases = {
        "large_invalid_jinja_syntax.yml": {"E201"},
        "large_invalid_jinja_template.yml": {"E202"},
        "large_warning_convention_interview.yml": {"W603"},
    }

    for fixture_name, expected_codes in cases.items():
        diagnostics = analyze_text(
            regression_fixture_text(fixture_name),
            path=f"tests/fixtures/regressions/{fixture_name}",
        )
        codes = {diagnostic.code for diagnostic in diagnostics if diagnostic.code}

        assert codes == expected_codes


def test_large_warning_fixture_can_enable_specific_convention_codes() -> None:
    diagnostics = analyze_text(
        regression_fixture_text("large_warning_convention_interview.yml"),
        path="tests/fixtures/regressions/large_warning_convention_interview.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C101"})),
    )

    codes = {diagnostic.code for diagnostic in diagnostics if diagnostic.code}
    assert codes == {"C101", "W603"}


# ---------------------------------------------------------------------------
# Packet 2: Initial block shape validation
# ---------------------------------------------------------------------------


def test_include_scalar_is_valid() -> None:
    diagnostics = analyze_text(
        "include: docassemble.demo:data/questions/questions.yml\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E459" not in codes


def test_include_list_is_valid() -> None:
    diagnostics = analyze_text(
        "include:\n  - docassemble.demo:data/questions/questions.yml\n  - local.yml\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E459" not in codes


def test_include_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "include:\n  key: value\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E459" in codes


def test_include_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "include:\n  - 123\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E460" in codes


def test_jinja_template_include_does_not_report_type_error() -> None:
    """Jinja2 templates can render include values to None at analysis time.
    Type validators should be skipped only for sections that actually contain
    Jinja syntax, so sections without Jinja are still validated."""
    # First section has Jinja — no type errors expected
    # Second section has no Jinja — type errors still reported
    diagnostics = analyze_text(
        "# use jinja\ninclude:\n{% for item in [] %}\n  - {{ item }}\n{% endfor %}\n---\ninclude:\n  key: value\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E459" in codes  # Second (non-Jinja) section should still fire
    assert "E460" not in codes


def test_modules_scalar_is_valid() -> None:
    diagnostics = analyze_text(
        "modules: docassemble.base.util\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E461" not in codes


def test_modules_list_is_valid() -> None:
    diagnostics = analyze_text(
        "modules:\n  - docassemble.base.util\n  - .my_module\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E461" not in codes


def test_modules_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "modules:\n  key: value\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E461" in codes


def test_modules_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "modules:\n  - 123\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E462" in codes


def test_imports_scalar_is_valid() -> None:
    diagnostics = analyze_text(
        "imports: import json\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E463" not in codes


def test_imports_list_is_valid() -> None:
    diagnostics = analyze_text(
        "imports:\n  - import json\n  - from math import sqrt\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E463" not in codes


def test_imports_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "imports:\n  key: value\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E463" in codes


def test_imports_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "imports:\n  - 123\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E464" in codes


def test_metadata_mapping_is_valid() -> None:
    diagnostics = analyze_text(
        "metadata:\n  title: My Interview\n  authors:\n    - name: Alice\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E465" not in codes


def test_metadata_scalar_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "metadata: just a string\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E465" in codes


def test_metadata_list_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "metadata:\n  - title\n  - authors\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E465" in codes


def test_initial_true_is_valid() -> None:
    diagnostics = analyze_text(
        "initial: True\ncode: |\n  x = 1\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_mandatory_true_is_valid() -> None:
    diagnostics = analyze_text(
        "mandatory: True\ncode: |\n  x = 1\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_mandatory_string_expression_is_valid() -> None:
    diagnostics = analyze_text(
        "mandatory: x > 1\ncode: |\n  x = 1\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_mandatory_integer_reports_python_bool_type() -> None:
    diagnostics = analyze_text(
        "mandatory: 42\ncode: |\n  x = 1\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E533" in codes


def test_scan_for_variables_bool_is_valid() -> None:
    diagnostics = analyze_text(
        "scan for variables: True\ncode: |\n  x = 1\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_features_mapping_is_valid() -> None:
    diagnostics = analyze_text(
        "features:\n  progress bar: True\n  question back button: True\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_features_scalar_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "features: nope\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E468" in codes


def test_features_list_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "features:\n  - nope\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E468" in codes


# ---------------------------------------------------------------------------
# Packet 3: Question Core shape validation
# ---------------------------------------------------------------------------


def test_question_string_value_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Do you agree?\nyesno: user.agrees\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_yesno_string_variable_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Do you agree?\nyesno: user.agrees\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E401" not in codes


def test_yesno_non_string_value_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Do you agree?\nyesno:\n  - bad\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E401" in codes


def test_noyes_string_variable_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Do you agree?\nnoyes: user.agrees\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E401" not in codes


def test_yesnomaybe_string_variable_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Do you agree?\nyesnomaybe: user.preference\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E401" not in codes


def test_noyesmaybe_string_variable_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Do you agree?\nnoyesmaybe: user.preference\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E401" not in codes


def test_event_string_value_is_valid() -> None:
    diagnostics = analyze_text(
        "event: intro_page\nquestion: Introduction\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E469" not in codes


def test_event_list_value_is_valid() -> None:
    diagnostics = analyze_text(
        "event:\n  - intro_page\n  - next_page\ncode: |\n  pass\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E469" not in codes
    assert "E470" not in codes


def test_event_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "event:\n  key: value\ncode: |\n  pass\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E469" in codes


def test_event_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "event:\n  - 123\ncode: |\n  pass\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E470" in codes


def test_continue_button_field_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Please continue\ncontinue button field: user_saw_intro\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E401" not in codes


def test_sets_string_is_valid() -> None:
    diagnostics = analyze_text(
        "sets: user.name\ncode: |\n  user.name = 'Alice'\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E466" not in codes


def test_sets_list_is_valid() -> None:
    diagnostics = analyze_text(
        "sets:\n  - user.name\n  - user.email\ncode: |\n  user.name = 'Alice'\n  user.email = 'a@b.com'\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E466" not in codes


def test_sets_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "sets:\n  key: value\ncode: |\n  pass\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E466" in codes


def test_sets_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "sets:\n  - 123\ncode: |\n  pass\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E467" in codes


def test_only_sets_string_is_valid() -> None:
    diagnostics = analyze_text(
        "only sets: user.name\ncode: |\n  user.name = 'Alice'\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E466" not in codes


def test_only_sets_list_is_valid() -> None:
    diagnostics = analyze_text(
        "only sets:\n  - user.name\n  - user.email\ncode: |\n  user.name = 'Alice'\n  user.email = 'a@b.com'\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E466" not in codes


def test_only_sets_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "only sets:\n  key: value\ncode: |\n  pass\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E466" in codes


# ---------------------------------------------------------------------------
# Packet 4: Question Modifiers shape validation
# ---------------------------------------------------------------------------


def test_reconsider_bool_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Reask?\nreconsider: true\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E471" not in codes


def test_reconsider_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Reask?\nreconsider: my_var\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E471" not in codes


def test_reconsider_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Reask?\nreconsider:\n  - my_var\n  - other_var\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E471" not in codes


def test_reconsider_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "question: Reask?\nreconsider:\n  key: value\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E471" in codes


def test_reconsider_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "question: Reask?\nreconsider:\n  - 123\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E472" in codes


def test_undefine_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Continue?\nundefine: my_var\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E473" not in codes


def test_undefine_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Continue?\nundefine:\n  - my_var\n  - other_var\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E473" not in codes


def test_undefine_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "question: Continue?\nundefine:\n  key: value\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E473" in codes


def test_undefine_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "question: Continue?\nundefine:\n  - 123\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E474" in codes


def test_supersedes_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Override\nsupersedes: old_block_id\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E475" not in codes


def test_supersedes_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Override\nsupersedes:\n  - old_block_id\n  - another_id\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E475" not in codes


def test_supersedes_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "question: Override\nsupersedes:\n  key: value\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E475" in codes


def test_supersedes_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "question: Override\nsupersedes:\n  - 123\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E476" in codes


def test_depends_on_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Conditional?\ndepends on: my_var\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E477" not in codes


def test_depends_on_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Conditional?\ndepends on:\n  - my_var\n  - other_var\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E477" not in codes


def test_depends_on_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "question: Conditional?\ndepends on:\n  key: value\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E477" in codes


def test_depends_on_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "question: Conditional?\ndepends on:\n  - 123\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E478" in codes


def test_role_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: For role\nrole: advocate\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E479" not in codes


def test_role_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: For role\nrole:\n  - advocate\n  - client\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E479" not in codes


def test_role_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "question: For role\nrole:\n  key: value\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E479" in codes


def test_role_list_with_non_string_item_reports_item_error() -> None:
    diagnostics = analyze_text(
        "question: For role\nrole:\n  - 123\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E480" in codes


def test_allowed_to_set_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Set?\nallowed to set: user.name\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E481" not in codes


def test_allowed_to_set_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Set?\nallowed to set:\n  - user.name\n  - user.email\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E481" not in codes


def test_allowed_to_set_mapping_reports_shape_error() -> None:
    diagnostics = analyze_text(
        "question: Set?\nallowed to set:\n  key: value\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E481" in codes


def test_progress_integer_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Step\nprogress: 50\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E482" not in codes


def test_progress_string_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Step\nprogress: halfway\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E482" in codes


def test_comment_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\ncomment: developer note\nfield: answer\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E401" not in codes


# ---------------------------------------------------------------------------
# Packet 6: Field Datatypes And Inputs
# ---------------------------------------------------------------------------


def test_range_datatype_requires_min_and_max() -> None:
    diagnostics = analyze_text(
        "question: Slide\nfields:\n  - label: Volume\n    field: volume\n    datatype: range\n",
        path="sample.yml",
    )
    e510 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E510")
    assert e510.line == 5


def test_range_datatype_with_min_and_max_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Slide\nfields:\n  - label: Volume\n    field: volume\n    datatype: range\n    min: 0\n    max: 100\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E510" not in codes


def test_file_key_without_file_datatype_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Upload\nfields:\n  - label: Pic\n    field: user_pic\n    datatype: text\n    maximum image size: 200\n",
        path="sample.yml",
    )
    e511 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E511")
    assert e511.line == 6


def test_file_key_with_file_datatype_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Upload\nfields:\n  - label: Pic\n    field: user_pic\n    datatype: file\n    maximum image size: 200\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E511" not in codes


def test_file_key_on_camera_datatype_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Take photo\nfields:\n  - label: Photo\n    field: user_photo\n    datatype: camera\n    accept: image/*\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E511" not in codes


def test_file_key_without_datatype_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Upload\nfields:\n  - label: Pic\n    field: user_pic\n    accept: image/*\n",
        path="sample.yml",
    )
    e511 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E511")
    assert e511.line == 5


def test_file_key_with_camcorder_datatype_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Record\nfields:\n  - label: Video\n    field: user_video\n    datatype: camcorder\n    maximum image size: 500\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E511" not in codes


def test_rows_without_area_or_multiselect_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Text\nfields:\n  - label: Name\n    field: user.name\n    rows: 5\n",
        path="sample.yml",
    )
    e512 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E512")
    assert e512.line == 5


def test_rows_with_area_input_type_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Essay\nfields:\n  - label: Bio\n    field: user_bio\n    input type: area\n    rows: 10\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E512" not in codes


def test_rows_with_multiselect_datatype_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Pick\nfields:\n  - label: Items\n    field: items\n    datatype: multiselect\n    rows: 6\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E512" not in codes


def test_rows_with_object_multiselect_datatype_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Pick\nfields:\n  - label: People\n    field: people\n    datatype: object_multiselect\n    rows: 4\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E512" not in codes


def test_rows_with_area_datatype_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Essay\nfields:\n  - label: Bio\n    field: user_bio\n    datatype: area\n    rows: 10\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E512" not in codes


def test_area_datatype_reports_convention() -> None:
    diagnostics = analyze_text(
        "question: Essay\nfields:\n  - label: Bio\n    field: user_bio\n    datatype: area\n    rows: 10\n",
        path="sample.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C105"})),
    )

    c105 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "C105")
    assert c105.line == 5
    assert c105.severity == "convention"


def test_area_datatype_convention_suppressed_with_input_type_area() -> None:
    diagnostics = analyze_text(
        "question: Essay\nfields:\n  - label: Bio\n    field: user_bio\n    datatype: area\n    input type: area\n    rows: 10\n",
        path="sample.yml",
        runtime_options=RuntimeOptions(enabled_conventions=frozenset({"C105"})),
    )
    codes = {d.code for d in diagnostics}
    assert "C105" not in codes


# -----------------------------------------------------------------------
# Packet 7: Choices And Buttons
# -----------------------------------------------------------------------


def test_shuffle_must_be_boolean() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    choices:\n      - A\n      - B\n    shuffle: yes\n",
        path="sample.yml",
    )

    e519 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E519")
    assert e519.line == 8


def test_shuffle_boolean_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    choices:\n      - A\n      - B\n    shuffle: True\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E519" not in codes


def test_disable_others_incompatible_datatype() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Upload\n    field: doc\n    datatype: file\n    disable others: True\n",
        path="sample.yml",
    )

    e513 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E513")
    assert e513.line == 6


def test_disable_others_valid_with_yesno() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Agree?\n    field: agreed\n    datatype: yesno\n    disable others: True\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E513" not in codes


def test_disable_others_invalid_type() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    choices:\n      - A\n      - B\n    disable others: string_value\n",
        path="sample.yml",
    )

    e514 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E514")
    assert e514.line == 8


def test_disable_others_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    datatype: yesno\n    disable others:\n      - other_var\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E514" not in codes


def test_disable_others_bool_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    datatype: yesno\n    disable others: True\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E514" not in codes


def test_uncheck_others_requires_yesno_datatype() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    datatype: text\n    uncheck others: True\n",
        path="sample.yml",
    )

    e515 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E515")
    assert e515.line == 6


def test_uncheck_others_with_yesno_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Agree?\n    field: agreed\n    datatype: yesno\n    uncheck others: True\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E515" not in codes
    assert "E516" not in codes


def test_uncheck_others_invalid_type() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Agree?\n    field: agreed\n    datatype: yesno\n    uncheck others: string_val\n",
        path="sample.yml",
    )

    e516 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E516")
    assert e516.line == 6


def test_check_others_requires_yesno_datatype() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    datatype: text\n    check others: True\n",
        path="sample.yml",
    )

    e517 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E517")
    assert e517.line == 6


def test_check_others_with_noyes_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Disagree?\n    field: disagreed\n    datatype: noyes\n    check others: True\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E517" not in codes
    assert "E518" not in codes


def test_check_others_invalid_type() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Disagree?\n    field: disagreed\n    datatype: noyes\n    check others: 42\n",
        path="sample.yml",
    )

    e518 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E518")
    assert e518.line == 6


def test_all_of_the_above_requires_checkboxes_datatype() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: things\n    datatype: text\n    all of the above: True\n",
        path="sample.yml",
    )

    e520 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E520")
    assert e520.line == 6


def test_all_of_the_above_with_checkboxes_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: things\n    datatype: checkboxes\n    choices:\n      - A\n      - B\n    all of the above: True\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E520" not in codes


def test_all_of_the_above_with_object_checkboxes_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: things\n    datatype: object_checkboxes\n    choices: thing_list\n    all of the above: True\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E520" not in codes


def test_none_of_the_above_requires_checkboxes_or_object_radio() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: things\n    datatype: text\n    none of the above: True\n",
        path="sample.yml",
    )

    e521 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E521")
    assert e521.line == 6


def test_none_of_the_above_with_checkboxes_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: things\n    datatype: checkboxes\n    choices:\n      - A\n      - B\n    none of the above: False\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E521" not in codes


def test_none_of_the_above_with_object_radio_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    datatype: object_radio\n    choices: thing_list\n    none of the above: 'Pick one'\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E521" not in codes


def test_disable_others_with_object_multiselect_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: things\n    datatype: object_multiselect\n    choices: thing_list\n    disable others: True\n",
        path="sample.yml",
    )

    e513 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E513")
    assert e513.line == 7


def test_disable_others_with_multiselect_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: things\n    datatype: multiselect\n    choices: thing_list\n    disable others: True\n",
        path="sample.yml",
    )

    e513 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E513")
    assert e513.line == 7


def test_disable_others_with_range_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Rate\n    field: rating\n    datatype: range\n    min: 1\n    max: 10\n    disable others: True\n",
        path="sample.yml",
    )

    e513 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E513")
    assert e513.line == 8


def test_disable_others_with_checkboxes_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: things\n    datatype: checkboxes\n    choices:\n      - A\n      - B\n    disable others: True\n",
        path="sample.yml",
    )

    e513 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E513")
    assert e513.line == 9


def test_choices_valid_scalar_list() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    choices:\n      - A\n      - B\n      - C\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert not {"E419", "E426", "E427"}.intersection(codes)


def test_choices_valid_dict_list() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    choices:\n      - Label A: value_a\n      - Label B: value_b\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert not {"E419", "E426", "E427"}.intersection(codes)


def test_choices_valid_label_value_dicts() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    choices:\n      - label: Label A\n        value: value_a\n      - label: Label B\n        value: value_b\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert not {"E419", "E426", "E427"}.intersection(codes)


def test_choices_via_code_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    code: my_choices\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E419" not in codes


def test_buttons_top_level_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Pick\nfield: choice\nbuttons:\n  - Label A: value_a\n  - Label B: value_b\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert not {"E301", "E435"}.intersection(codes)


def test_buttons_top_level_code_dict_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Pick\nfield: choice\nbuttons:\n  code: my_buttons\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert not {"E301", "E435"}.intersection(codes)


def test_choices_with_exclude_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    code: my_choices\n    exclude: skip_this\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E426" not in codes


def test_choices_with_exclude_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: choice\n    code: my_choices\n    exclude:\n      - skip_this\n      - also_this\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E426" not in codes


def test_choices_with_string_default_on_object_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices: thing_list\n    default: default_thing\n",
        path="sample.yml",
    )

    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E427" not in codes


# ---------------------------------------------------------------------------
# Packet 8: Field Conditions And Validation
# ---------------------------------------------------------------------------


def test_validate_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Age\n    field: age\n    validate: is_multiple_of_four\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E522" not in codes
    assert "E523" not in codes


def test_validate_lambda_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Age\n    field: age\n    validate: |\n      lambda y: True if y/4 == int(y/4) else validation_error('Need multiple of four')\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E522" not in codes
    assert "E523" not in codes


def test_validate_non_string_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Age\n    field: age\n    validate:\n      - bad\n",
        path="sample.yml",
    )
    e522 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E522")
    assert e522.line == 5


def test_validate_invalid_python_reports_syntax_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Age\n    field: age\n    validate: |\n      if True\n        x = 1\n",
        path="sample.yml",
    )
    e523 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E523")
    assert e523.line == 6


def test_validation_messages_dict_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Age\n    field: age\n    validation messages:\n      required: Please enter your age\n      number: Must be a number\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E524" not in codes
    assert "E525" not in codes


def test_validation_messages_non_dict_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Age\n    field: age\n    validation messages: just a string\n",
        path="sample.yml",
    )
    e524 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E524")
    assert e524.line == 5


def test_validation_messages_list_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Age\n    field: age\n    validation messages:\n      - bad\n",
        path="sample.yml",
    )
    e524 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E524")
    assert e524.line == 5


def test_validation_messages_entry_with_non_string_value_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Age\n    field: age\n    validation messages:\n      required:\n        bad: value\n",
        path="sample.yml",
    )
    e525 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E525")
    assert e525.line == 6


def test_trigger_at_integer_greater_than_one_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Word\n    field: word\n    input type: ajax\n    action: lookup\n    trigger at: 3\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E526" not in codes


def test_trigger_at_integer_one_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Word\n    field: word\n    input type: ajax\n    action: lookup\n    trigger at: 1\n",
        path="sample.yml",
    )
    e526 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E526")
    assert e526.line == 7


def test_trigger_at_string_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Word\n    field: word\n    input type: ajax\n    action: lookup\n    trigger at: three\n",
        path="sample.yml",
    )
    e526 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E526")
    assert e526.line == 7


def test_help_generator_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices: thing_list\n    help generator: |\n      lambda y: y.description\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E527" not in codes
    assert "E528" not in codes


def test_help_generator_non_string_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices: thing_list\n    help generator:\n      - bad\n",
        path="sample.yml",
    )
    e527 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E527")
    assert e527.line == 7


def test_help_generator_invalid_python_reports_syntax_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices: thing_list\n    help generator: |\n      if True\n        x = 1\n",
        path="sample.yml",
    )
    e528 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E528")
    assert e528.line == 8


def test_image_generator_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices: thing_list\n    image generator: |\n      lambda y: y.image_ref\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E529" not in codes
    assert "E530" not in codes


def test_image_generator_non_string_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices: thing_list\n    image generator:\n      - bad\n",
        path="sample.yml",
    )
    e529 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E529")
    assert e529.line == 7


def test_image_generator_invalid_python_reports_syntax_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Pick\n    field: thing\n    datatype: object\n    choices: thing_list\n    image generator: |\n      if True\n        x = 1\n",
        path="sample.yml",
    )
    e530 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E530")
    assert e530.line == 8


def test_using_string_with_ml_datatype_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Feedback\n    field: feedback\n    datatype: ml\n    using: sentiment_group\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E531" not in codes


def test_using_non_string_with_ml_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Feedback\n    field: feedback\n    datatype: ml\n    using:\n      - bad\n",
        path="sample.yml",
    )
    e531 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E531")
    assert e531.line == 6


def test_using_on_non_ml_datatype_is_not_validated() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Name\n    field: name\n    datatype: text\n    using: whatever\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E531" not in codes


def test_keep_for_training_bool_with_ml_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Feedback\n    field: feedback\n    datatype: mlarea\n    keep for training: True\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E532" not in codes


def test_keep_for_training_string_with_ml_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Feedback\n    field: feedback\n    datatype: ml\n    keep for training: user_consented\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E532" not in codes


def test_keep_for_training_integer_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Feedback\n    field: feedback\n    datatype: ml\n    keep for training: 42\n",
        path="sample.yml",
    )
    e532 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E532")
    assert e532.line == 6


def test_keep_for_training_on_non_ml_datatype_is_not_validated() -> None:
    diagnostics = analyze_text(
        "question: Test\nfields:\n  - label: Name\n    field: name\n    datatype: text\n    keep for training: 42\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E532" not in codes


# ---------------------------------------------------------------------------
# Visibility modifier cross-key conflicts (Packet 8)
# ---------------------------------------------------------------------------


def test_show_if_and_hide_if_same_code_ness_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Ex\n    field: x\n    show if: ready\n    hide if: gone\n",
        path="sample.yml",
    )
    e535 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E535")
    # Error is anchored on "hide if" (alphabetically first key in sorted pair)
    assert e535.line == 6


def test_show_if_and_hide_if_different_code_ness_no_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Ex\n    field: x\n    show if: ready\n    hide if:\n      code: gone\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E535" not in codes


def test_show_if_and_enable_if_same_code_ness_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Ex\n    field: x\n    show if: ready\n    enable if: some_cond\n",
        path="sample.yml",
    )
    e535 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E535")
    # Error is anchored on "enable if" (alphabetically first)
    assert e535.line == 6


def test_show_if_and_enable_if_different_code_ness_no_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Ex\n    field: x\n    show if: ready\n    enable if:\n      code: some_cond\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E535" not in codes


def test_non_js_and_js_mix_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Ex\n    field: x\n    show if: ready\n    js show if: val('ready') === true\n",
        path="sample.yml",
    )
    e536 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E536")
    # Error is anchored on "show if" (first in sorted non-JS keys)
    assert e536.line == 5


def test_js_show_if_and_js_enable_if_same_code_ness_reports_error() -> None:
    diagnostics = analyze_text(
        'question: Hi\nfields:\n  - label: Ex\n    field: x\n    js show if: val("ready")\n    js enable if: val("gone")\n',
        path="sample.yml",
    )
    e535 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E535")
    # Error is anchored on "js enable if" (alphabetically first)
    assert e535.line == 6


def test_js_show_if_and_js_hide_if_same_code_ness_reports_error() -> None:
    diagnostics = analyze_text(
        'question: Hi\nfields:\n  - label: Ex\n    field: x\n    js show if: val("a")\n    js hide if: val("b")\n',
        path="sample.yml",
    )
    e535 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E535")
    # Error is anchored on "js hide if" (alphabetically first)
    assert e535.line == 6


def test_multiple_conflicting_non_js_modifiers_all_reported() -> None:
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Ex\n    field: x\n    show if: a\n    hide if: b\n    enable if: c\n",
        path="sample.yml",
    )
    e535_codes = [d for d in diagnostics if d.code == "E535"]
    assert len(e535_codes) >= 2


def test_non_js_and_js_mix_reports_all_cross_pairs() -> None:
    """All 16 cross-pairs (4 non-JS × 4 JS) are reported."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Ex\n    field: x\n"
        "    show if: a\n    hide if: b\n    enable if: c\n    disable if: d\n"
        "    js show if: va\n    js hide if: vb\n    js enable if: vc\n    js disable if: vd\n",
        path="sample.yml",
    )
    e536_codes = [d for d in diagnostics if d.code == "E536"]
    assert len(e536_codes) == 16


def test_visibility_conflict_skipped_when_values_unset() -> None:
    """No false E535 when visibility modifier keys exist but values are None."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - label: Ex\n    field: x\n    show if:\n    hide if:\n",
        path="sample.yml",
    )
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert "E535" not in codes


# ---------------------------------------------------------------------------
# Packet 9: Documents And Attachments
# ---------------------------------------------------------------------------


def test_attachment_valid_single_dict() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: My Document\n  filename: my_document\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E901" not in codes


def test_attachment_valid_list() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  - name: Doc 1\n    filename: doc1\n  - name: Doc 2\n    filename: doc2\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E901" not in codes


def test_attachment_valid_with_full_metadata() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Report\n  filename: report\n  metadata:\n    title: Annual Report\n    author:\n      - John\n      - Jane\n    DoubleSpacing: True\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_attachment_non_dict_item_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  - 42\n",
        path="sample.yml",
    )
    e901 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E901")
    assert e901 is not None


def test_attachment_scalar_reports_item_error() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment: 42\n",
        path="sample.yml",
    )
    e901 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E901")
    assert e901 is not None


def test_attachment_name_must_be_string() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name:\n    - List Name\n  filename: doc\n",
        path="sample.yml",
    )
    e902 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E902")
    assert e902 is not None


def test_attachment_filename_must_be_string() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename:\n    - list\n",
        path="sample.yml",
    )
    e903 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E903")
    assert e903 is not None


def test_attachment_variable_name_must_be_string() -> None:
    diagnostics = analyze_text(
        "attachment:\n  name: Doc\n  filename: doc\n  variable name:\n    - list\n",
        path="sample.yml",
    )
    e904 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E904")
    assert e904 is not None


def test_attachment_metadata_must_be_dict() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  metadata: just a string\n",
        path="sample.yml",
    )
    e905 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E905")
    assert e905 is not None


def test_attachment_metadata_entry_with_invalid_type() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  metadata:\n    key: 42\n",
        path="sample.yml",
    )
    e910 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E910")
    assert e910 is not None


def test_attachment_valid_formats_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  valid formats:\n    - pdf\n    - rtf\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E906" not in codes


def test_attachment_valid_formats_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  valid formats: pdf\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E906" not in codes


def test_attachment_valid_formats_code_subkey_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  valid formats:\n    code: |\n      documents.valid_formats\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E906" not in codes


def test_attachment_valid_formats_invalid_shape() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  valid formats:\n    key: value\n",
        path="sample.yml",
    )
    e906 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E906")
    assert e906 is not None


def test_attachment_code_must_be_string() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  pdf template file: form.pdf\n  code:\n    - not_string\n",
        path="sample.yml",
    )
    e907 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E907")
    assert e907 is not None


def test_attachment_field_variables_must_be_list() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  pdf template file: form.pdf\n  field variables: not_a_list\n",
        path="sample.yml",
    )
    e908 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E908")
    assert e908 is not None


def test_attachment_content_file_string_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  content file: hello.md\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E909" not in codes


def test_attachment_content_file_list_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  content file:\n    - intro.md\n    - body.md\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E909" not in codes


def test_attachment_content_file_code_dict_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  content file:\n    code: the_content_file\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E909" not in codes


def test_attachment_content_file_invalid_shape() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  content file: 42\n",
        path="sample.yml",
    )
    e909 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E909")
    assert e909 is not None


def test_attachment_content_file_dict_missing_code_key() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  content file:\n    path: hello.md\n",
        path="sample.yml",
    )
    e909 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E909")
    assert e909 is not None


def test_attachments_list_valid() -> None:
    diagnostics = analyze_text(
        "question: Here are your documents\nattachments:\n  - name: Doc 1\n    filename: doc1\n  - name: Doc 2\n    filename: doc2\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_attachment_metadata_with_bool_entries_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Doc\n  filename: doc\n  metadata:\n    toc: True\n    DoubleSpacing: False\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E905" not in codes
    assert "E910" not in codes


def test_valid_attachment_snippet_has_no_diagnostics() -> None:
    """Regression: a typical attachment block from upstream examples."""
    diagnostics = analyze_text(
        "question: Here is your document\nattachment:\n  name: Hello World\n  filename: hello_world\n  content: |\n    Hello, world!\n  valid formats:\n    - pdf\n    - rtf\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


# ---------------------------------------------------------------------------
# Packet 10: Review And Table
# ---------------------------------------------------------------------------


def test_review_valid_list() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n  - label: Email\n    field: user.email\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E911" not in codes
    assert "E912" not in codes


def test_review_valid_single_dict() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  label: Name\n  field: user.name\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E911" not in codes


def test_review_scalar_reports_type_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview: just a string\n",
        path="sample.yml",
    )
    e911 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E911")
    assert e911 is not None


def test_review_item_non_dict_reports_item_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - just a string\n",
        path="sample.yml",
    )
    e912 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E912")
    assert e912 is not None


def test_review_item_label_without_field_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name only\n",
        path="sample.yml",
    )
    e913 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E913")
    assert e913 is not None


def test_review_item_field_without_label_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - field: user.name\n",
        path="sample.yml",
    )
    e914 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E914")
    assert e914 is not None


def test_review_item_fields_without_label_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - fields:\n      - user.name\n      - user.email\n",
        path="sample.yml",
    )
    e914 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E914")
    assert e914 is not None


def test_review_item_note_is_valid_without_label() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - note: Some informational text\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E913" not in codes


def test_review_item_note_invalid_type_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - note:\n      - list\n",
        path="sample.yml",
    )
    e915 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E915")
    assert e915 is not None


def test_table_without_columns_reports_missing_keys() -> None:
    diagnostics = analyze_text(
        "table: fruit_table\nrows: fruit_list\n",
        path="sample.yml",
    )
    e921 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E921")
    assert e921 is not None


def test_table_without_rows_reports_missing_keys() -> None:
    diagnostics = analyze_text(
        "table: fruit_table\ncolumns:\n  - header: Name\n    cell: name\n",
        path="sample.yml",
    )
    e921 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E921")
    assert e921 is not None


def test_table_with_all_three_keys_is_valid() -> None:
    diagnostics = analyze_text(
        "question: Fruit table\ntable: fruit_table\nrows: fruit_list\ncolumns:\n  - header: Name\n    cell: name\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E921" not in codes


def test_table_rows_non_string_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Fruit table\ntable: fruit_table\nrows:\n  - item1\ncolumns:\n  - header: Name\n    cell: name\n",
        path="sample.yml",
    )
    e923 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E923")
    assert e923 is not None


def test_table_columns_non_list_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Fruit table\ntable: fruit_table\nrows: fruit_list\ncolumns: just a string\n",
        path="sample.yml",
    )
    e924 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E924")
    assert e924 is not None


def test_table_column_item_non_dict_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Fruit table\ntable: fruit_table\nrows: fruit_list\ncolumns:\n  - just a string\n",
        path="sample.yml",
    )
    e925 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E925")
    assert e925 is not None


def test_review_valid_with_full_features() -> None:
    """Regression: a review block with label, field, action, and show if."""
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n    show if: user.defined\n  - label: Email\n    fields:\n      - user.email\n      - user.alt_email\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


def test_review_show_if_non_string_non_list_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n    show if:\n      obj: attr\n",
        path="sample.yml",
    )
    e916 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E916")
    assert e916 is not None


def test_review_show_if_list_with_non_string_item_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n    show if:\n      - user.defined\n      - 42\n",
        path="sample.yml",
    )
    e916 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E916")
    assert e916 is not None


def test_review_help_non_string_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n    help:\n      - list item\n",
        path="sample.yml",
    )
    e917 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E917")
    assert e917 is not None


def test_review_action_non_string_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n    action:\n      - list\n",
        path="sample.yml",
    )
    e918 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E918")
    assert e918 is not None


def test_review_button_non_string_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n    button:\n      - list\n",
        path="sample.yml",
    )
    e919 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E919")
    assert e919 is not None


def test_review_css_class_non_string_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n    css class:\n      - list\n",
        path="sample.yml",
    )
    e920 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E920")
    assert e920 is not None


def test_review_action_is_valid_string() -> None:
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    field: user.name\n    action: user.edit\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E918" not in codes


def test_review_show_if_list_is_valid() -> None:
    """Review show if accepts a list of variable names."""
    diagnostics = analyze_text(
        "question: Review your answers\nreview:\n  - label: Name\n    fields:\n      - user.name\n      - user.email\n    show if:\n      - user.defined\n      - user.active\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E916" not in codes


def test_table_column_header_non_string_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Fruit table\ntable: fruit_table\nrows: fruit_list\ncolumns:\n  - header:\n      - list\n    cell: name\n",
        path="sample.yml",
    )
    e926 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E926")
    assert e926 is not None


def test_table_column_cell_non_string_reports_error() -> None:
    diagnostics = analyze_text(
        "question: Fruit table\ntable: fruit_table\nrows: fruit_list\ncolumns:\n  - header: Name\n    cell:\n      - list\n",
        path="sample.yml",
    )
    e927 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E927")
    assert e927 is not None


def test_table_column_shorthand_is_valid() -> None:
    """Table columns can use shorthand key: value format."""
    diagnostics = analyze_text(
        "question: Fruit table\ntable: fruit_table\nrows: fruit_list\ncolumns:\n  - Name: name\n  - Email: email\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E926" not in codes
    assert "E927" not in codes


def test_table_column_header_cell_is_valid() -> None:
    """Table columns with string header and cell are valid."""
    diagnostics = analyze_text(
        "question: Fruit table\ntable: fruit_table\nrows: fruit_list\ncolumns:\n  - header: Name\n    cell: name\n  - header: Email\n    cell: email\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E926" not in codes
    assert "E927" not in codes


# Packet 12: Objects And Data
# ---------------------------------------------------------------------------


def test_data_block_string_reports_error() -> None:
    """When data is used with variable name, data as a string is still an error."""
    diagnostics = analyze_text(
        "variable name: people\ndata: just a string\n",
        path="sample.yml",
    )
    e928 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E928")
    assert e928 is not None


def test_data_block_list_is_valid() -> None:
    """When data is used with variable name, data can be a list (docassemble docs)."""
    diagnostics = analyze_text(
        "variable name: fruits\ndata:\n  - Apple\n  - Orange\n  - Peach\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E928" not in codes


def test_data_block_list_of_dicts_is_valid() -> None:
    """List of dicts is also valid (e.g. dashboard buttons)."""
    diagnostics = analyze_text(
        "variable name: dashboard_buttons_1\ndata:\n  - name: Create Documents\n    url: https://example.com\n    image: file-lines\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E928" not in codes


def test_data_block_list_with_use_objects_is_valid() -> None:
    """Documented pattern: use objects: True with data as a list (DAContext)."""
    diagnostics = analyze_text(
        "variable name: fruits\nuse objects: True\ndata:\n  - question: Apple\n    document: red fruit\n  - question: Orange\n    document: fruit that rhymes with nothing\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E928" not in codes


def test_data_block_with_variable_name_and_dict_is_valid() -> None:
    diagnostics = analyze_text(
        "variable name: people\nuse objects: objects\ndata:\n  object: Individual\n  module: docassemble.base.util\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E928" not in codes
    assert "E929" not in codes


def test_data_block_variable_name_must_be_string() -> None:
    diagnostics = analyze_text(
        "variable name:\n  - people\ndata:\n  object: Individual\n",
        path="sample.yml",
    )
    e929 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E929")
    assert e929 is not None


def test_data_block_use_objects_invalid_type_reports_error() -> None:
    diagnostics = analyze_text(
        "variable name: people\nuse objects:\n  - invalid\ndata:\n  object: Individual\n",
        path="sample.yml",
    )
    e930 = next(diagnostic for diagnostic in diagnostics if diagnostic.code == "E930")
    assert e930 is not None


def test_data_block_use_objects_valid_types_accepted() -> None:
    """use objects accepts True, False, 'objects', or a Python expression."""
    for val in ("True", "False", "objects"):
        diagnostics = analyze_text(
            f"variable name: people\nuse objects: {val}\ndata:\n  object: Individual\n",
            path="sample.yml",
        )
        assert "E930" not in {d.code for d in diagnostics}, f"E930 raised for use objects: {val}"


def test_data_block_without_variable_name_is_not_flagged() -> None:
    """data without variable name is allowed (not a data object block)."""
    diagnostics = analyze_text(
        "data: some_variable_name\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E928" not in codes


def test_data_object_from_fixture_is_valid() -> None:
    """Realistic data-objects.yml style block."""
    diagnostics = analyze_text(
        "variable name: people\nuse objects: objects\ndata:\n  object: Individual\n  module: docassemble.base.util\n  items:\n    - name:\n        object: IndividualName\n        item:\n          first: Fred\n          last: Smith\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert not codes


# ---------------------------------------------------------------------------
# Packet 15: Markup
# ---------------------------------------------------------------------------


def test_bracket_file_with_content_is_valid() -> None:
    """[FILE path] with a file reference is valid."""
    diagnostics = analyze_text(
        "question: See [FILE mugshot.jpg]\nyesno: seen_photo\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_file_empty_reports_error() -> None:
    """[FILE] without a path is an empty bracket command."""
    diagnostics = analyze_text(
        "question: See [FILE]\nyesno: seen_photo\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY in codes


def test_bracket_qr_with_content_is_valid() -> None:
    """[QR text] with content is valid."""
    diagnostics = analyze_text(
        "subquestion: Scan [QR https://example.com]\nquestion: Test\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_qr_empty_reports_error() -> None:
    """[QR] without text is an empty bracket command."""
    diagnostics = analyze_text(
        "question: Test\nsubquestion: Scan [QR]\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY in codes


def test_bracket_youtube_with_content_is_valid() -> None:
    """[YOUTUBE id] with a video ID is valid."""
    diagnostics = analyze_text(
        "subquestion: Watch [YOUTUBE RpgYyuLt7Dx]\nquestion: Test\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_youtube_empty_reports_error() -> None:
    """[YOUTUBE] without an ID is an empty bracket command."""
    diagnostics = analyze_text(
        "question: Test\nsubquestion: '[YOUTUBE]'\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY in codes


def test_bracket_vimeo_with_content_is_valid() -> None:
    """[VIMEO id] with a video ID is valid."""
    diagnostics = analyze_text(
        "subquestion: Watch [VIMEO 12345678]\nquestion: Test\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_vimeo_empty_reports_error() -> None:
    """[VIMEO] without an ID is an empty bracket command."""
    diagnostics = analyze_text(
        "question: Test\nsubquestion: '[VIMEO]'\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY in codes


def test_bracket_field_with_content_is_valid() -> None:
    """[FIELD name] with a field name is valid."""
    diagnostics = analyze_text(
        "subquestion: Enter [FIELD user.name]\nquestion: Test\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_field_empty_reports_error() -> None:
    """[FIELD] without a name is an empty bracket command."""
    diagnostics = analyze_text(
        "question: Test\nsubquestion: '[FIELD]'\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY in codes


def test_bracket_target_with_content_is_valid() -> None:
    """[TARGET name] with a target name is valid."""
    diagnostics = analyze_text(
        "subquestion: Result [TARGET area]\nquestion: Test\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_target_empty_reports_error() -> None:
    """[TARGET] without a name is an empty bracket command."""
    diagnostics = analyze_text(
        "question: Test\nsubquestion: '[TARGET]'\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY in codes


def test_bracket_no_emojis_is_valid_without_content() -> None:
    """[NO_EMOJIS] does not require content."""
    diagnostics = analyze_text(
        "subquestion: [NO_EMOJIS] Some plain text\nquestion: Test\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_br_is_valid_without_content() -> None:
    """[BR] does not require content."""
    diagnostics = analyze_text(
        "question: Line1[BR]Line2\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_newline_is_valid_without_content() -> None:
    """[NEWLINE] does not require content."""
    diagnostics = analyze_text(
        "subquestion: Line1[NEWLINE]Line2\nquestion: Test\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


def test_bracket_begin_two_col_is_valid_without_content() -> None:
    """[BEGIN_TWOCOL] does not require content."""
    diagnostics = analyze_text(
        "subquestion: [BEGIN_TWOCOL]Left[BREAK]Right[END_TWOCOL]\nquestion: Test\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert MessageCode.MARKUP_BRACKET_EMPTY not in codes


# ---------------------------------------------------------------------------
# List collect validation
# ---------------------------------------------------------------------------


def test_list_collect_bool_is_valid() -> None:
    """Boolean value for list collect should not produce type errors."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field: user.name\nlist collect: True\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E103" not in codes


def test_list_collect_string_is_valid() -> None:
    """String (Python expression) value for list collect should not produce type errors."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field: user.name\nlist collect: some_expression\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E103" not in codes


def test_list_collect_dict_is_valid() -> None:
    """Dict value for list collect should not produce type errors."""
    diagnostics = analyze_text(
        "question: Hi\nfields:\n  - field: user.name\nlist collect:\n  enable: True\n  label: Add item\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E103" not in codes


def test_list_collect_with_mako_in_explicit_label_reports_error() -> None:
    """Field label with Mako templating should produce E933 when list collect is active."""
    diagnostics = analyze_text(
        "question: Tell me about the fruit.\n"
        "fields:\n"
        "  - label: Fruit ${ i + 1 }\n"
        "    field: fruit[i].name.text\n"
        "list collect: True\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E933" in codes


def test_list_collect_with_mako_in_shorthand_label_reports_error() -> None:
    """Shorthand field label with Mako templating should produce E933 when list collect is active."""
    diagnostics = analyze_text(
        'question: Tell me about the fruit.\nfields:\n  - "Fruit ${ i + 1 }": fruit[i].name.text\nlist collect: True\n',
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E933" in codes


def test_list_collect_dict_form_with_mako_label_reports_error() -> None:
    """List collect in dict form should also trigger E933 when label has Mako."""
    diagnostics = analyze_text(
        "question: Tell me about the fruit.\n"
        "fields:\n"
        "  - label: Fruit ${ i + 1 }\n"
        "    field: fruit[i].name.text\n"
        "list collect:\n"
        "  enable: True\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E933" in codes


def test_list_collect_with_plain_label_is_valid() -> None:
    """Plain field label without Mako should NOT produce E933 when list collect is active."""
    diagnostics = analyze_text(
        "question: Tell me about the fruit.\n"
        "fields:\n"
        "  - label: Fruit name\n"
        "    field: fruit[i].name.text\n"
        "list collect: True\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E933" not in codes


def test_list_collect_false_with_mako_label_no_error() -> None:
    """When list collect is False, Mako in labels is allowed (no E933)."""
    diagnostics = analyze_text(
        "question: Tell me about the fruit.\n"
        "fields:\n"
        "  - label: Fruit ${ i + 1 }\n"
        "    field: fruit[i].name.text\n"
        "list collect: False\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E933" not in codes


def test_list_collect_python_expr_with_mako_label_no_error() -> None:
    """When list collect is a dynamic Python expression, Mako in labels is not flagged (E933 not produced)."""
    diagnostics = analyze_text(
        "question: Tell me about the fruit.\n"
        "fields:\n"
        "  - label: Fruit ${ i + 1 }\n"
        "    field: fruit[i].name.text\n"
        "list collect: some_variable\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E933" not in codes


def test_list_collect_mako_label_line_number() -> None:
    """E933 should point to the correct line number of the field label."""
    diagnostics = analyze_text(
        "question: Tell me about the fruit.\n"
        "fields:\n"
        "  - label: Fruit name\n"
        "    field: fruit[i].name.text\n"
        "  - label: Fruit ${ i + 1 }\n"
        "    field: fruit[i].seeds\n"
        "list collect: True\n",
        path="sample.yml",
    )
    e933 = next(d for d in diagnostics if d.code == "E933")
    assert e933.line == 5  # The second field item's label line


def test_list_collect_dict_label_key_with_mako_is_valid() -> None:
    """The ``list collect`` dict's own ``label`` key is designed for Mako text
    (per-item row label).  It should NOT trigger E933 — only field-item labels
    inside ``fields:`` are restricted."""
    diagnostics = analyze_text(
        "question: Tell me about the fruit.\n"
        "fields:\n"
        "  - label: Fruit name\n"
        "    field: fruit[i].name.text\n"
        "  - label: Number of seeds\n"
        "    field: fruit[i].seeds\n"
        "    datatype: number\n"
        "list collect:\n"
        "  enable: True\n"
        "  label: |\n"
        "    ${ fruit_name } ${ i + 1 }.\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E933" not in codes


# ---------------------------------------------------------------------------
# Def/Mako cross-validation (E934)
# ---------------------------------------------------------------------------


def test_def_without_mako_reports_error() -> None:
    """A 'def' key without 'mako' should produce E934 on the def line."""
    diagnostics = analyze_text(
        "def: my_func\ncode: |\n  x = 1\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E934" in codes
    e934 = next(d for d in diagnostics if d.code == "E934")
    assert e934.line == 1
    assert "mako" in e934.message


def test_mako_without_def_reports_error() -> None:
    """A 'mako' key without 'def' should produce E934 on the mako line."""
    diagnostics = analyze_text(
        "mako: |\n  Hello ${ name }\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E934" in codes
    e934 = next(d for d in diagnostics if d.code == "E934")
    assert e934.line == 1
    assert "def" in e934.message


def test_def_with_mako_is_valid() -> None:
    """When both 'def' and 'mako' are present, no E934 should fire."""
    diagnostics = analyze_text(
        "def: my_func\nmako: |\n  Hello ${ name }\ncode: |\n  x = 1\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E934" not in codes


def test_def_and_mako_both_absent_is_valid() -> None:
    """When neither 'def' nor 'mako' are present, no E934 should fire."""
    diagnostics = analyze_text(
        "question: Plain question\ncode: |\n  x = 1\n",
        path="sample.yml",
    )
    codes = {d.code for d in diagnostics}
    assert "E934" not in codes


def test_def_without_mako_line_number() -> None:
    """E934 should point to the exact line of the 'def' key, not line 1."""
    diagnostics = analyze_text(
        "code: |\n  x = 1\ndef: my_func\n",
        path="sample.yml",
    )
    e934 = next(d for d in diagnostics if d.code == "E934")
    assert e934.line == 3


def test_mako_without_def_line_number() -> None:
    """E934 should point to the exact line of the 'mako' key, not line 1."""
    diagnostics = analyze_text(
        "code: |\n  x = 1\nmako: |\n  Hello ${ name }\n",
        path="sample.yml",
    )
    e934 = next(d for d in diagnostics if d.code == "E934")
    assert e934.line == 3


# Cross-document diagnostics tests (require workspace_index)


def test_cross_doc_undefined_event_in_action() -> None:
    """W601 when action references an event not in any workspace doc."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    source = "action: nonexistent_event\n"
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        source,
        input_file="/tmp/test.yml",
        workspace_index=index,
    )
    w601 = [e for e in errors if e.code == "W601"]
    assert len(w601) == 1
    assert "nonexistent_event" in w601[0].err_str


def test_cross_doc_undefined_def_in_usedefs() -> None:
    """W602 when usedefs references a def not in any workspace doc."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    source = "usedefs: nonexistent_func\n"
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        source,
        input_file="/tmp/test.yml",
        workspace_index=index,
    )
    w602 = [e for e in errors if e.code == "W602"]
    assert len(w602) == 1
    assert "nonexistent_func" in w602[0].err_str


def test_cross_doc_missing_file_reference(tmp_path: Path) -> None:
    """W604 when include references a file that does not exist."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    yml_file = tmp_path / "test.yml"
    yml_file.write_text("include: missing.yml\n")
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        yml_file.read_text(),
        input_file=str(yml_file),
        workspace_index=index,
    )
    w604 = [e for e in errors if e.code == "W604"]
    assert len(w604) == 1
    assert "missing.yml" in w604[0].err_str


def test_cross_doc_no_error_when_event_is_defined(tmp_path: Path) -> None:
    """No W601 when the event IS defined in the workspace."""
    from docassemble_lsp.core.definitions import build_workspace_index
    from docassemble_lsp.core.validation import find_errors_from_string

    main_file = tmp_path / "main.yml"
    main_file.write_text("event: defined_event\n")
    second_file = tmp_path / "second.yml"
    second_file.write_text("action: defined_event\n")

    index = build_workspace_index([tmp_path])
    source = second_file.read_text()
    errors = find_errors_from_string(
        source,
        input_file=str(second_file),
        workspace_index=index,
    )
    w601 = [e for e in errors if e.code == "W601"]
    assert len(w601) == 0


def test_cross_doc_no_error_when_def_is_defined(tmp_path: Path) -> None:
    """No W602 when the def IS defined in the workspace."""
    from docassemble_lsp.core.definitions import build_workspace_index
    from docassemble_lsp.core.validation import find_errors_from_string

    main_file = tmp_path / "main.yml"
    main_file.write_text("def: defined_func\ncode: |\n  pass\n")
    second_file = tmp_path / "second.yml"
    second_file.write_text("usedefs: defined_func\n")

    index = build_workspace_index([tmp_path])
    source = second_file.read_text()
    errors = find_errors_from_string(
        source,
        input_file=str(second_file),
        workspace_index=index,
    )
    w602 = [e for e in errors if e.code == "W602"]
    assert len(w602) == 0


def test_cross_doc_module_scalar_undefined(tmp_path: Path) -> None:
    """W604 for a non-existent module in modules: (scalar form)."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    source = "modules: .fake\n"
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        source,
        input_file=str(tmp_path / "test.yml"),
        workspace_index=index,
    )
    w604 = [e for e in errors if e.code == "W604"]
    assert len(w604) == 1


def test_cross_doc_module_entry_undefined(tmp_path: Path) -> None:
    """W604 for a non-existent module in modules:."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    source = "modules:\n  - .fake\n"
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        source,
        input_file=str(tmp_path / "test.yml"),
        workspace_index=index,
    )
    w604 = [e for e in errors if e.code == "W604"]
    assert len(w604) == 1
    assert "fake" in w604[0].err_str


def test_cross_doc_no_error_when_file_exists(tmp_path: Path) -> None:
    """No W604 when the referenced file actually exists."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    existing_file = tmp_path / "existing.yml"
    existing_file.write_text("question: Test\n")
    yml_file = tmp_path / "main.yml"
    yml_file.write_text("include: existing.yml\n")

    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        yml_file.read_text(),
        input_file=str(yml_file),
        workspace_index=index,
    )
    w604 = [e for e in errors if e.code == "W604"]
    assert len(w604) == 0


def test_cross_doc_event_in_code_block() -> None:
    """W601 when url_action() references an unknown event inside a code: | block."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    source = "code: |\n  url_action('nonexistent_event')\n"
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        source,
        input_file="/tmp/test.yml",
        workspace_index=index,
    )
    w601 = [e for e in errors if e.code == "W601"]
    assert len(w601) == 1
    assert "nonexistent_event" in w601[0].err_str


def test_cross_doc_event_in_mako_block() -> None:
    """W601 when url_action() references an unknown event inside a Mako <% %> block."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    source = "question: Test\nsubquestion: |\n  <% url_action('nonexistent_event') %>\n"
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        source,
        input_file="/tmp/test.yml",
        workspace_index=index,
    )
    w601 = [e for e in errors if e.code == "W601"]
    assert len(w601) == 1
    assert "nonexistent_event" in w601[0].err_str


def test_cross_doc_imports_scalar_undefined(tmp_path: Path) -> None:
    """W604 for a non-existent module in imports: (scalar form)."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    source = "imports: .fake\n"
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        source,
        input_file=str(tmp_path / "test.yml"),
        workspace_index=index,
    )
    w604 = [e for e in errors if e.code == "W604"]
    assert len(w604) == 1


def test_cross_doc_imports_entry_undefined(tmp_path: Path) -> None:
    """W604 for a non-existent module in imports: (list form)."""
    from docassemble_lsp.core.validation import find_errors_from_string
    from docassemble_lsp.core.workspace import WorkspaceIndex

    source = "imports:\n  - .fake\n"
    index = WorkspaceIndex.empty()
    errors = find_errors_from_string(
        source,
        input_file=str(tmp_path / "test.yml"),
        workspace_index=index,
    )
    w604 = [e for e in errors if e.code == "W604"]
    assert len(w604) == 1
    assert "fake" in w604[0].err_str
