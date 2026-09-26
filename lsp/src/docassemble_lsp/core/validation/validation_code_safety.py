"""Conservative checks for off-screen reads in question validation code.

Static analysis here only understands direct variable paths and explicit
``defined()`` / ``.hasattr()`` guards. Dynamic aliases and computed names are
intentionally not inferred; see ``docs/validation-code-safety.md``.
"""

from __future__ import annotations

import ast
import builtins
import re
from collections.abc import Mapping
from typing import Any

from docassemble_lsp.core.field_keys import FIELD_MODIFIER_KEYS
from docassemble_lsp.core.line_helpers import (
    _is_internal_metadata_key,
    _path,
    _safe_ast_parse,
)

_BUILTIN_NAMES = frozenset(dir(builtins)) | {
    "defined",
    "validation_error",
    "DAValidationError",
}

# docassemble binds these names as list-item indices while asking list
# questions (``docassemble/base/parse.py``).
_LIST_ITEM_INDICES = frozenset({"i", "j", "k", "l", "m", "n"})
_SUBSCRIPT_INDEX_RE = re.compile(r"\[([A-Za-z_]\w*)\]")


def _canonical_variable(value: str) -> str:
    try:
        expression = _safe_ast_parse(value, mode="eval").body
    except SyntaxError:
        return value.strip()
    return _path(expression) or value.strip()


def _field_targets(fields: Any) -> list[str] | None:
    """Return raw declared field strings, or None when fields are dynamic."""
    if isinstance(fields, Mapping):
        keys = {
            key
            for key in fields
            if isinstance(key, str) and not _is_internal_metadata_key(key)
        }
        if keys == {"code"}:
            return None
        items = [fields]
    elif isinstance(fields, list):
        items = fields
    else:
        return None

    targets: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        target = item.get("field")
        if isinstance(target, str):
            targets.append(target)
            continue
        for key, value in item.items():
            if (
                isinstance(key, str)
                and key not in FIELD_MODIFIER_KEYS
                and not _is_internal_metadata_key(key)
                and isinstance(value, str)
            ):
                targets.append(value)
                break
    return targets


def _need_targets(need: Any) -> list[str]:
    targets: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str):
            targets.append(value)
        elif isinstance(value, list):
            for child in value:
                add(child)
        elif isinstance(value, Mapping):
            for key, child in value.items():
                if isinstance(key, str) and key.lower() in {"pre", "post"}:
                    add(child)

    add(need)
    return targets


def _implicit_indices(targets: list[str]) -> set[str]:
    """Return docassemble list-item index names referenced by declared targets."""
    return {
        name
        for target in targets
        for name in _SUBSCRIPT_INDEX_RE.findall(target)
        if name in _LIST_ITEM_INDICES
    }


def _matches_declared(name: str, declared: set[str]) -> bool:
    """Match *name* against declared paths using a ``.``-anchored prefix rule."""
    return name in declared or any(name.startswith(path + ".") for path in declared)


def _guarded_by_true(expr: ast.AST) -> set[str]:
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        return _guarded_by_false(expr.operand)
    if isinstance(expr, ast.BoolOp):
        guard_sets = [_guarded_by_true(value) for value in expr.values]
        if isinstance(expr.op, ast.And):
            return set().union(*guard_sets)
        if isinstance(expr.op, ast.Or) and guard_sets:
            return set.intersection(*guard_sets)
        return set()
    if not isinstance(expr, ast.Call):
        return set()

    if (
        isinstance(expr.func, ast.Name)
        and expr.func.id == "defined"
        and expr.args
        and isinstance(expr.args[0], ast.Constant)
        and isinstance(expr.args[0].value, str)
    ):
        return {_canonical_variable(expr.args[0].value)}
    if (
        isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "hasattr"
        and expr.args
        and isinstance(expr.args[0], ast.Constant)
        and isinstance(expr.args[0].value, str)
    ):
        receiver = _path(expr.func.value)
        attribute = _canonical_variable(expr.args[0].value)
        if receiver and attribute:
            return {
                attribute
                if attribute == receiver or attribute.startswith(receiver + ".")
                else f"{receiver}.{attribute}"
            }
    return set()


def _guarded_by_false(expr: ast.AST) -> set[str]:
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        return _guarded_by_true(expr.operand)
    if isinstance(expr, ast.BoolOp):
        guard_sets = [_guarded_by_false(value) for value in expr.values]
        if isinstance(expr.op, ast.Or):
            return set().union(*guard_sets)
        if isinstance(expr.op, ast.And) and guard_sets:
            return set.intersection(*guard_sets)
    return set()


def _local_names(tree: ast.Module) -> tuple[set[str], set[str], set[str]]:
    locals_: set[str] = set()
    imports: set[str] = set()
    assigned_paths: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Param)):
            locals_.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            assigned_path = _path(node)
            if assigned_path:
                assigned_paths.add(assigned_path)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            locals_.add(node.name)
            locals_.update(
                arg.arg
                for arg in (
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                )
            )
            if node.args.vararg:
                locals_.add(node.args.vararg.arg)
            if node.args.kwarg:
                locals_.add(node.args.kwarg.arg)
        elif isinstance(node, ast.ClassDef):
            locals_.add(node.name)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                locals_.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            locals_.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            locals_.add(node.rest)
        elif isinstance(node, ast.Import):
            imports.update(
                alias.asname or alias.name.split(".")[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imports.update(alias.asname or alias.name for alias in node.names)
    return locals_, imports, assigned_paths


def _iter_variable_reads(tree: ast.Module):
    """Yield direct variable paths with the guard set active at each read."""
    locals_, imports, assigned_paths = _local_names(tree)
    active_guards: dict[int, set[str]] = {}

    def visit(node: ast.AST, guards: set[str]) -> None:
        active_guards[id(node)] = set(guards)
        if isinstance(node, ast.If):
            visit(node.test, guards)
            branch_guards = guards | _guarded_by_true(node.test)
            for child in node.body:
                visit(child, branch_guards)
            else_guards = guards | _guarded_by_false(node.test)
            for child in node.orelse:
                visit(child, else_guards)
            return
        if isinstance(node, ast.BoolOp):
            current = set(guards)
            for value in node.values:
                visit(value, current)
                if isinstance(node.op, ast.And):
                    current.update(_guarded_by_true(value))
                elif isinstance(node.op, ast.Or):
                    current.update(_guarded_by_false(value))
            return
        for child in ast.iter_child_nodes(node):
            visit(child, guards)

    visit(tree, set())

    parents = {
        id(child): parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    def is_attribute_base(node: ast.AST) -> bool:
        current = node
        parent = parents.get(id(current))
        while isinstance(parent, ast.Subscript) and parent.value is current:
            current = parent
            parent = parents.get(id(current))
        return isinstance(parent, ast.Attribute) and parent.value is current

    for node in ast.walk(tree):
        parent = parents.get(id(node))
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            parent_is_attribute = (
                isinstance(parent, ast.Attribute) and parent.value is node
            )
            parent_is_call = isinstance(parent, ast.Call) and parent.func is node
            if parent_is_attribute or parent_is_call or is_attribute_base(node):
                continue
            value_path = _path(node)
            if value_path is None:
                continue
            root = value_path.split(".", 1)[0]
            if root in locals_ or root in imports or value_path in assigned_paths:
                continue
            yield value_path, node.lineno, active_guards.get(id(node), set())
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if is_attribute_base(node):
                continue
            if isinstance(parent, ast.Call) and parent.func is node:
                continue
            if node.id in locals_ or node.id in imports or node.id in _BUILTIN_NAMES:
                continue
            yield node.id, node.lineno, active_guards.get(id(node), set())


def find_unguarded_offscreen_reads(
    doc: Mapping[str, Any],
    *,
    workspace_defined_names: frozenset[str] = frozenset(),
) -> list[tuple[str, int]]:
    """Return ``(variable, Python body line)`` for likely off-screen reads.

    The check is limited to statically declared question fields plus names
    defined by ``objects:`` / ``code:`` blocks elsewhere in the interview
    (*workspace_defined_names*). ``fields: {code: ...}`` and malformed/dynamic
    blocks are skipped rather than presenting incomplete static knowledge as
    certainty.
    """
    normalized = {
        key.lower(): value for key, value in doc.items() if isinstance(key, str)
    }
    if "validation code" not in normalized:
        return []
    raw_targets: list[str] = []
    if "fields" in normalized:
        field_targets = _field_targets(normalized["fields"])
        if field_targets is None:
            return []
        screen_fields = {_canonical_variable(target) for target in field_targets}
        raw_targets.extend(field_targets)
    elif isinstance(normalized.get("field"), str):
        singular_field = normalized["field"]
        screen_fields = {_canonical_variable(singular_field)}
        raw_targets.append(singular_field)
    else:
        return []
    if not isinstance(normalized["validation code"], str):
        return []
    try:
        tree = _safe_ast_parse(normalized["validation code"])
    except SyntaxError:
        return []

    need_targets = _need_targets(normalized.get("need"))
    raw_targets.extend(need_targets)
    on_screen = (
        screen_fields
        | {_canonical_variable(target) for target in need_targets}
        | _implicit_indices(raw_targets)
        | set(workspace_defined_names)
    )
    if "generic object" in normalized or "generic list object" in normalized:
        on_screen.add("x")
    if "generic list object" in normalized:
        on_screen.add("i")
    findings: dict[str, int] = {}
    for name, line, guards in _iter_variable_reads(tree):
        if _matches_declared(name, on_screen) or _matches_declared(name, guards):
            continue
        if name.split(".", 1)[0] in _BUILTIN_NAMES:
            continue
        findings.setdefault(name, line)
    return list(findings.items())
