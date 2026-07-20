from __future__ import annotations

from docassemble_lsp.core import build_document_facts


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
