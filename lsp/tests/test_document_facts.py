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
