from __future__ import annotations

from docassemble_lsp.core.yaml_shared import (
    _iter_mako_expressions,
    _precompute_parent_keys,
)


def test_precompute_parent_keys_handles_continuation() -> None:
    source = "objects:\n  - list:\n      - 1\n      - 2\n"
    parents = _precompute_parent_keys(source)
    assert parents[2] == "list"
    assert parents[3] == "list"


def test_precompute_parent_keys_handles_inline_list_continuation() -> None:
    source = "foo: [1,\n     2,\n     3]\n"
    parents = _precompute_parent_keys(source)
    assert parents[1] == "foo"


def test_precompute_parent_keys_handles_list_item_mapping_sibling() -> None:
    source = "a:\n  - b: 1\n    c: 2\n"
    parents = _precompute_parent_keys(source)
    assert parents[2] == "a"


def test_precompute_parent_keys_handles_nested_child_beneath_list_item() -> None:
    source = "a:\n  - b:\n      d: 1\n    c: 2\n"
    parents = _precompute_parent_keys(source)
    assert parents[2] == "b"
    assert parents[3] == "a"


def test_precompute_parent_keys_flat_is_none() -> None:
    source = "a: 1\nb: 2\n"
    parents = _precompute_parent_keys(source)
    assert parents[0] is None
    assert parents[1] is None


def test_iter_mako_expressions_matches_simple_expressions() -> None:
    text = "A ${foo(1)} and ${bar.baz()}"
    matches = list(_iter_mako_expressions(text))
    assert matches == [
        ("foo(1)", 4, 10),
        ("bar.baz()", 18, 27),
    ]


def test_iter_mako_expressions_spans_nested_braces() -> None:
    text = '${edit_button("x", label=f"Edit {M.parties[1].as_kind()}")}'
    matches = list(_iter_mako_expressions(text))
    assert matches == [
        (
            'edit_button("x", label=f"Edit {M.parties[1].as_kind()}")',
            2,
            len(text) - 1,
        )
    ]


def test_iter_mako_expressions_spans_triple_quoted_nested_expression() -> None:
    text = '${edit_button("x", label=f"""Edit {bold(M.x.as_kind("pl"))}""")}'
    matches = list(_iter_mako_expressions(text))
    assert len(matches) == 1
    content, start, end = matches[0]
    assert start == 2
    assert end == len(text) - 1
    assert 'label=f"""Edit {bold(M.x.as_kind("pl"))}"""' in content


def test_iter_mako_expressions_falls_back_for_stray_closing_brace() -> None:
    text = '${label("}")}'
    matches = list(_iter_mako_expressions(text))
    assert matches == [('label("', 2, 9)]


def test_iter_mako_expressions_falls_back_for_stray_open_brace() -> None:
    text = '${x("a{b")}'
    matches = list(_iter_mako_expressions(text))
    assert matches == [('x("a{b")', 2, 10)]


def test_iter_mako_expressions_mixed_balanced_and_broken() -> None:
    text = '${a()} ${x("a{b")}'
    matches = list(_iter_mako_expressions(text))
    assert matches == [("a()", 2, 5), ('x("a{b")', 9, 17)]
