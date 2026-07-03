from __future__ import annotations

from docassemble_lsp.core.yaml_shared import _precompute_parent_keys


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
