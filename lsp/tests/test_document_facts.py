from __future__ import annotations

from docassemble_lsp.core import build_document_facts
from docassemble_lsp.core.document_facts import _build_document_facts_cached


def test_build_document_facts_collects_documents_and_top_level_keys() -> None:
    facts = build_document_facts(
        "---\nid: intro\nquestion: Hello\nfields:\n  - Name: user.name\n---\nmandatory: True\ncode: |\n  ready = True\n"
    )

    assert [fact.name for fact in facts] == ["intro", "code"]
    assert facts[0].start_line == 1
    assert facts[0].selection_line == 1
    assert [key.name for key in facts[0].keys] == ["id", "question", "fields"]
    assert [key.name for key in facts[1].keys] == ["mandatory", "code"]


def test_build_document_facts_uses_question_text_when_no_id_exists() -> None:
    facts = build_document_facts("question: Hello there\nfield: user.name\n")

    assert len(facts) == 1
    assert facts[0].name == "Hello there"
    assert facts[0].selection_line == 0


def test_build_document_facts_multiple_yaml_documents() -> None:
    source = "---\nid: first\nkey: val\n---\nid: second\nfoo: bar\n"
    facts = build_document_facts(source)
    assert len(facts) == 2
    assert facts[0].name == "first"
    assert facts[0].start_line == 1
    assert facts[0].end_line == 2
    assert facts[0].selection_line == 1
    assert facts[1].name == "second"
    assert facts[1].start_line == 4
    assert facts[1].end_line == 5
    assert facts[1].selection_line == 4


def test_build_document_facts_comment_only_dropped() -> None:
    facts = build_document_facts("# hello\n")
    assert len(facts) == 0


def test_build_document_facts_id_only() -> None:
    facts = build_document_facts("id: \n")
    assert len(facts) == 1
    assert facts[0].name == "id"


def test_build_document_facts_non_preferred_keys() -> None:
    facts = build_document_facts("foo: bar\n")
    assert len(facts) == 1
    assert facts[0].name == "foo"
    assert facts[0].selection_line == 0


def test_build_document_facts_block_scalar_name_key() -> None:
    facts = build_document_facts("id: |\n  hello\n")
    assert len(facts) == 1
    assert facts[0].name == "id"


def test_build_document_facts_nested_keys_at_top_level_only() -> None:
    facts = build_document_facts("outer:\n  inner: x\nother: y\n")
    assert len(facts) == 1
    assert len(facts[0].keys) == 2
    key_names = [k.name for k in facts[0].keys]
    assert "inner" not in key_names


def test_build_document_facts_empty_source_returns_empty_list() -> None:
    assert build_document_facts("") == []


def test_build_document_facts_only_document_separators_returns_empty_list() -> None:
    assert build_document_facts("---\n---\n") == []


def test_build_document_facts_empty_preferred_key_falls_back_to_key_name() -> None:
    facts = build_document_facts("question:\n")
    assert len(facts) == 1
    assert facts[0].name == "question"


def test_build_document_facts_id_wins_over_other_preferred_keys() -> None:
    facts = build_document_facts("id: foo\nquestion: Hello\n")
    assert len(facts) == 1
    assert facts[0].name == "foo"


def test_build_document_facts_block_scalar_question_falls_back_to_question() -> None:
    facts = build_document_facts("question: |\n  hello\n")
    assert len(facts) == 1
    assert facts[0].name == "question"


def test_build_document_facts_event_key_used_for_name() -> None:
    facts = build_document_facts("event: done\n")
    assert len(facts) == 1
    assert facts[0].name == "done"


def test_build_document_facts_blank_lines_and_comments_skipped() -> None:
    facts = build_document_facts("\n# comment\nid: intro\n\nquestion: Hello\n")
    assert len(facts) == 1
    assert [key.name for key in facts[0].keys] == ["id", "question"]


def test_build_document_facts_code_key_without_value() -> None:
    facts = build_document_facts("code: |\n")
    assert len(facts) == 1
    assert facts[0].name == "code"


def test_build_document_facts_caches() -> None:
    source = "question: CacheCheck\n"
    first = build_document_facts(source)
    second = build_document_facts(source)
    assert first == second
    assert _build_document_facts_cached.cache_info().hits >= 1


def test_build_document_facts_event_wins_over_question() -> None:
    facts = build_document_facts("event: done\nquestion: Hello\n")

    assert len(facts) == 1
    assert facts[0].name == "done"
    assert facts[0].selection_line == 0


def test_build_document_facts_attachment_wins_over_code() -> None:
    facts = build_document_facts("attachment: result.docx\ncode: |\n  ready = True\n")

    assert len(facts) == 1
    assert facts[0].name == "result.docx"


def test_build_document_facts_def_wins_over_question() -> None:
    facts = build_document_facts("def: helper\nquestion: Hello\n")

    assert len(facts) == 1
    assert facts[0].name == "helper"


def test_build_document_facts_empty_block_scalar_preferred_key_falls_back() -> None:
    facts = build_document_facts("objects: |\ncode: |\n")

    assert len(facts) == 1
    assert facts[0].name == "objects"
    assert [key.name for key in facts[0].keys] == ["objects", "code"]


def test_build_document_facts_quoted_id_values_strip_quotes() -> None:
    double_quoted = build_document_facts('id: "intro"\n')
    single_quoted = build_document_facts("id: 'intro'\n")

    assert double_quoted[0].name == "intro"
    assert single_quoted[0].name == "intro"


def test_build_document_facts_id_with_block_scalar_marker_falls_back() -> None:
    for marker in ("|-", ">", ">-", "|+"):
        facts = build_document_facts(f"id: {marker}\n")
        assert len(facts) == 1
        assert facts[0].name == "id"


def test_build_document_facts_colon_in_value_kept() -> None:
    facts = build_document_facts("id: a: b\n")

    assert len(facts) == 1
    assert facts[0].name == "a: b"


def test_build_document_facts_indented_and_colon_lines_not_top_level() -> None:
    facts = build_document_facts("\tkey: val\n: odd\nid: x\n")

    assert len(facts) == 1
    assert [key.name for key in facts[0].keys] == ["id"]
    assert facts[0].selection_line == 2


def test_build_document_facts_block_scalar_content_lines_not_keys() -> None:
    facts = build_document_facts("code: |\n  x = 1\n  y = 2\nquestion: Hi\n")

    assert len(facts) == 1
    assert [key.name for key in facts[0].keys] == ["code", "question"]
    assert facts[0].end_line == 3


def test_build_document_facts_trailing_blank_lines_in_end_line() -> None:
    facts = build_document_facts("id: intro\n\n\n")

    assert len(facts) == 1
    assert facts[0].start_line == 0
    assert facts[0].end_line == 2


def test_build_document_facts_crlf_line_endings() -> None:
    facts = build_document_facts("id: intro\r\nquestion: Hello\r\n")

    assert len(facts) == 1
    assert facts[0].name == "intro"
    assert facts[0].start_line == 0
    assert facts[0].end_line == 1
    assert [key.name for key in facts[0].keys] == ["id", "question"]


def test_build_document_facts_comment_only_section_dropped() -> None:
    facts = build_document_facts("---\n# comment\n---\nid: x\n")

    assert len(facts) == 1
    assert facts[0].name == "x"
    assert facts[0].start_line == 3
    assert facts[0].end_line == 3


def test_build_document_facts_separator_immediately_after_keys() -> None:
    facts = build_document_facts("---\nid: first\n---\nid: second\n")

    assert len(facts) == 2
    assert facts[0].name == "first"
    assert facts[0].start_line == 1
    assert facts[0].end_line == 1
    assert facts[1].name == "second"
    assert facts[1].start_line == 3
    assert facts[1].end_line == 3


def test_build_document_facts_consecutive_separators_single_doc() -> None:
    facts = build_document_facts("---\n---\nid: x\n")

    assert len(facts) == 1
    assert facts[0].name == "x"
    assert facts[0].start_line == 2
    assert facts[0].end_line == 2


def test_build_document_facts_nested_keys_do_not_extend_document() -> None:
    facts = build_document_facts("---\nid: a\n  nested: v\n---\nid: b\n")

    assert len(facts) == 2
    assert facts[0].start_line == 1
    assert facts[0].end_line == 2
    assert [key.name for key in facts[0].keys] == ["id"]
    assert facts[1].start_line == 4


def test_build_document_facts_key_value_and_line_facts() -> None:
    facts = build_document_facts("fields: \ncode: |\n")

    assert len(facts) == 1
    keys = facts[0].keys
    assert keys[0].name == "fields"
    assert keys[0].value == ""
    assert keys[0].line == 0
    assert keys[1].name == "code"
    assert keys[1].value == "|"
    assert keys[1].line == 1


def test_build_document_facts_preferred_keys_per_document() -> None:
    facts = build_document_facts(
        "---\nid: first\nquestion: Hello\n---\nquestion: Second\n"
    )

    assert len(facts) == 2
    assert facts[0].name == "first"
    assert facts[0].selection_line == 1
    assert facts[1].name == "Second"
    assert facts[1].selection_line == 4
