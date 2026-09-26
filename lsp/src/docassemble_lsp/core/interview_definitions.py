"""Interview-wide definitions that live outside a single screen.

W606 needs to know about names that docassemble defines at the interview
level: ``objects:`` entries and global assignments from top-level ``code:``
blocks. Collection is deliberately conservative — malformed or dynamic
content is skipped, never fatal.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable

from docassemble_lsp.core.line_helpers import _path, _safe_ast_parse
from docassemble_lsp.core.yaml_shared import (
    _KEY_VALUE_RE,
    _clean_value,
    _document_lines,
    _iter_block_scalar_regions,
    _precompute_parent_keys,
)


def collect_interview_defined_names(sources: Iterable[str]) -> frozenset[str]:
    """Return every name defined by ``objects:`` or top-level ``code:`` blocks."""
    names: set[str] = set()
    for source in sources:
        names.update(collect_interview_defined_names_from_source(source))
    return frozenset(names)


def collect_interview_defined_names_from_source(source: str) -> frozenset[str]:
    """Return the interview-wide names defined by one YAML source."""
    return frozenset(_object_names(source) | _code_assigned_names(source))


def _object_names(source: str) -> set[str]:
    """Return keys declared under top-level ``objects:`` mappings/lists."""
    parents = _precompute_parent_keys(source)
    names: set[str] = set()
    for line_index, text in enumerate(_document_lines(source)):
        if parents[line_index] != "objects":
            continue
        match = _KEY_VALUE_RE.match(text)
        if match is None:
            continue
        key = _clean_value(match.group(2))
        if key:
            names.add(key)
    return names


def _code_assigned_names(source: str) -> set[str]:
    """Return names bound at module scope by top-level ``code:`` blocks."""
    parents = _precompute_parent_keys(source)
    names: set[str] = set()
    for region in _iter_block_scalar_regions(source):
        if region.key_name != "code" or parents[region.key_line] is not None:
            continue
        try:
            tree = _safe_ast_parse(region.text)
        except (SyntaxError, ValueError):
            continue
        names.update(_module_scope_bindings(tree))
    return names


def _module_scope_bindings(tree: ast.Module) -> set[str]:
    """Return names bound by ``exec(code, user_dict)`` semantics.

    Descends into nested module-level statement bodies, but not into
    ``def`` / ``class`` / ``lambda`` bodies, whose assignments are local.
    The function/class names themselves are bound at module scope.
    """
    names: set[str] = set()

    def visit(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            return
        if isinstance(node, ast.Lambda):
            return
        if isinstance(node, ast.ExceptHandler):
            if node.name:
                names.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
        elif isinstance(node, ast.comprehension):
            # Comprehension targets are local to the comprehension.
            visit(node.iter)
            for condition in node.ifs:
                visit(condition)
            return
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.asname:
                    names.add(alias.asname)
                elif alias.name != "*":
                    names.add(alias.name.split(".")[0])
            return
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
            return
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            path = _path(node)
            if path:
                names.add(path)
            return
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return names
