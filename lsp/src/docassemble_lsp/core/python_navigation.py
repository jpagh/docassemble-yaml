from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from docassemble_lsp.core.definition_models import (
    BlockScalarRegion,
    DefinitionTarget,
    PythonCompletionTarget,
    PythonNamespaceBinding,
)
from docassemble_lsp.core.line_helpers import _safe_ast_parse
from docassemble_lsp.core.python_modules import (
    PYTHON_BUILTIN_EXCEPTIONS,
    VENDORED_MODULE_NAMES,
    compute_da_object_subclasses,
    module_completion_members,
    python_module_symbol_detail,
    python_module_symbol_details,
    resolve_python_module_path,
)
from docassemble_lsp.core.python_paths import (
    is_yaml_path,
    normalize_module_name,
    path_from_uri_or_path,
)
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_shared import (
    _BLOCK_SCALAR_MARKERS,
    _KEY_VALUE_RE,
    _LIST_ITEM_VALUE_RE,
    _MAKO_EXPRESSION_RE,
    _PYTHON_BLOCK_KEYS,
    _PYTHON_MODULE_REFERENCE_KEYS,
    _ancestor_keys,
    _append_reference_target,
    _block_scalar_region_from_key_line,
    _clean_value,
    _document_lines,
    _iter_mako_block_regions,
    _line_col_to_offset,
    _line_indent,
    _value_range,
)

_PYTHON_VALUE_KEY_SUFFIXES = {
    ("if",),
    ("prevent going back",),
    ("back button",),
    ("allowed to set",),
    ("hide continue button",),
    ("disable continue button",),
    ("list collect",),
    ("list collect", "enable"),
    ("list collect", "is final"),
    ("list collect", "allow append"),
    ("list collect", "allow delete"),
    ("mandatory",),
    ("initial",),
    ("use objects",),
    ("gathered",),
    ("required",),
    ("rows",),
    ("sort key",),
    ("sort reverse",),
    ("filter",),
    ("email template",),
    ("keep for training",),
    ("validate",),
    ("accept",),
    ("maximum image size",),
    ("image upload type",),
    ("object labeler",),
    ("help generator",),
    ("image generator",),
    ("disabled",),
    ("address autocomplete",),
    ("label above field",),
    ("floating label",),
    ("grid", "width"),
    ("grid", "label width"),
    ("grid", "offset"),
    ("grid", "start"),
    ("grid", "end"),
    ("item grid", "width"),
    ("skip undefined",),
    ("redact",),
    ("update references",),
    ("editable",),
    ("pdf/a",),
    ("pdftk",),
    ("tagged pdf",),
    ("manual code",),
    ("code",),
}
_PYTHON_LIST_VALUE_SUFFIXES = {
    ("need",),
    ("need", "pre"),
    ("need", "post"),
    ("require",),
    ("field variables",),
    ("raw field variables",),
}
_PYTHON_CHILD_VALUE_PARENTS = {
    "on change",
    "field code",
    "manual",
}
_PYTHON_COMPLETION_PREFIX_RE = re.compile(r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\.?)$")

_USING_KWARGS: dict[str, str] = {
    "object_type": "DAObject subclass for new items",
    "auto_gather": "Whether to gather items automatically (bool)",
    "complete_attribute": "Required attribute name for item completion (str)",
    "there_are_any": "Whether any items exist (bool)",
    "there_is_another": "Whether there is another item (bool)",
    "gathered": "Whether all items have been gathered (bool)",
    "ask_number": "Whether to ask for number of items (bool)",
    "minimum_number": "Minimum number of items (int)",
}

_PYTHON_KEYWORDS = frozenset(
    {
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "match",
        "case",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    }
)

_EXPRESSION_KEYWORDS = frozenset(
    {
        "True",
        "False",
        "None",
        "and",
        "or",
        "not",
        "in",
        "is",
        "if",
        "else",
        "lambda",
    }
)

_MAKO_LINE_KEYWORDS = _EXPRESSION_KEYWORDS | frozenset(
    {
        "elif",
        "for",
        "while",
        "try",
        "except",
        "finally",
        "with",
        "endif",
        "endfor",
        "endwhile",
        "endtry",
        "endwith",
    }
)


def _iter_top_level_list_items(source: str, key_name: str) -> list[tuple[int, str]]:
    lines = _document_lines(source)
    items: list[tuple[int, str]] = []
    in_block = False
    block_indent = 0

    for line_index, text in enumerate(lines):
        if text.strip() == "---":
            in_block = False
            continue

        if not text.startswith((" ", "\t")):
            match = _KEY_VALUE_RE.match(text)
            if match is not None and match.group(2).strip() == key_name and not match.group(3).strip():
                in_block = True
                block_indent = len(match.group(1))
                continue
            in_block = False
            continue

        if not in_block:
            continue

        if text.strip() and _line_indent(text) <= block_indent:
            in_block = False
            continue

        match = _LIST_ITEM_VALUE_RE.match(text)
        if match is None:
            continue

        value = _clean_value(match.group(2).strip())
        if value:
            items.append((line_index, value))

    return items


def _parse_import_binding(
    entry: str,
    current_path: Path | None,
    workspace_index: WorkspaceIndex,
) -> list[PythonNamespaceBinding]:
    statement = entry if entry.lstrip().startswith(("from ", "import ")) else f"import {entry}"
    try:
        node = _safe_ast_parse(statement).body[0]
    except SyntaxError:
        return []

    bindings: list[PythonNamespaceBinding] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            module_name = normalize_module_name(alias.name, current_path)
            if module_name is None:
                continue
            bindings.append(
                PythonNamespaceBinding(
                    kind="module_namespace",
                    module_name=module_name,
                    module_path=resolve_python_module_path(module_name, current_path, workspace_index),
                    alias=alias.asname or alias.name.rsplit(".", 1)[-1],
                )
            )
        return bindings

    if not isinstance(node, ast.ImportFrom):
        return []

    base_module = "." * node.level + (node.module or "")
    module_name = normalize_module_name(base_module, current_path)
    if module_name is None:
        return []
    module_path = resolve_python_module_path(module_name, current_path, workspace_index)
    for alias in node.names:
        if alias.name == "*":
            bindings.append(
                PythonNamespaceBinding(
                    kind="module_star",
                    module_name=module_name,
                    module_path=module_path,
                )
            )
            continue
        bindings.append(
            PythonNamespaceBinding(
                kind="symbol",
                module_name=module_name,
                module_path=module_path,
                alias=alias.asname or alias.name,
                imported_name=alias.name,
            )
        )
    return bindings


def _iter_included_yaml_paths(
    source: str,
    current_path: Path | None,
) -> list[Path]:
    """Yield YAML file paths referenced via ``include:`` with simple names.

    Only yields non-package-qualified includes (no ``:`` in the entry).
    Package-qualified includes (``docassemble.pkg.file``) are resolved
    by the flat model via ``modules:`` / ``imports:`` discovery instead.
    """
    if current_path is None:
        return []
    paths: list[Path] = []
    for _line, entry in _iter_top_level_list_items(source, "include"):
        if not entry or ":" in entry:
            continue
        candidate = (current_path.parent / entry).resolve()
        if candidate.is_file() and is_yaml_path(candidate):
            paths.append(candidate)
    return paths


def _python_namespace_bindings(
    source: str,
    current_path: Path | None,
    workspace_index: WorkspaceIndex,
) -> list[PythonNamespaceBinding]:
    bindings: list[PythonNamespaceBinding] = []
    seen_modules: set[Path] = set()

    for module_name in VENDORED_MODULE_NAMES:
        mod_path = resolve_python_module_path(module_name, current_path, workspace_index)
        if mod_path is not None and mod_path not in seen_modules:
            seen_modules.add(mod_path)
            bindings.append(
                PythonNamespaceBinding(
                    kind="module_star",
                    module_name=module_name,
                    module_path=mod_path,
                )
            )

    # All Python modules in the package (flat model).
    for mod_path in workspace_index.all_module_paths:
        if mod_path not in seen_modules:
            seen_modules.add(mod_path)
            bindings.append(
                PythonNamespaceBinding(
                    kind="module_star",
                    module_name=str(mod_path),
                    module_path=mod_path,
                )
            )

    # Fallback for non-package YAML files: follow includes to discover bindings.
    if workspace_index.package_root is None:
        for include_path in _iter_included_yaml_paths(source, current_path):
            if include_path in seen_modules:
                continue
            seen_modules.add(include_path)
            try:
                include_source = include_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            bindings.extend(
                _python_namespace_bindings(
                    include_source,
                    include_path,
                    workspace_index,
                )
            )

    for _line, entry in _iter_top_level_list_items(source, "modules"):
        normalized_module_name = normalize_module_name(entry, current_path)
        if normalized_module_name is None:
            continue
        bindings.append(
            PythonNamespaceBinding(
                kind="module_star",
                module_name=normalized_module_name,
                module_path=resolve_python_module_path(normalized_module_name, current_path, workspace_index),
            )
        )
    for _line, entry in _iter_top_level_list_items(source, "imports"):
        bindings.extend(_parse_import_binding(entry, current_path, workspace_index))

    return bindings


def enclosing_block_scalar_region(source: str, line: int) -> BlockScalarRegion | None:
    lines = _document_lines(source)
    for key_line in range(min(line, len(lines) - 1), -1, -1):
        text = lines[key_line]
        if text.strip() == "---":
            break
        match = _KEY_VALUE_RE.match(text)
        if match is None:
            continue
        raw_value = match.group(3).strip()
        if raw_value not in _BLOCK_SCALAR_MARKERS:
            continue
        region = _block_scalar_region_from_key_line(lines, key_line, match.group(2).strip(), len(match.group(1)))
        if region.content_start_line <= line <= region.end_line:
            return region
    return None


def _python_completion_prefix_in_text(text: str, line: int, character: int) -> tuple[tuple[str, ...], str] | None:
    lines = text.splitlines() or [""]
    line_index = min(max(line - 1, 0), len(lines) - 1)
    prefix_text = lines[line_index][: max(character, 0)]
    match = _PYTHON_COMPLETION_PREFIX_RE.search(prefix_text)
    if match is None:
        return None

    expression = match.group(1)
    if expression.endswith("."):
        chain = tuple(part for part in expression[:-1].split(".") if part)
        return (chain, "")

    parts = expression.split(".")
    return (tuple(parts[:-1]), parts[-1])


def _key_path(source: str, line: int, key_name: str) -> tuple[str, ...]:
    ancestors = tuple(reversed(_ancestor_keys(source, line)))
    return (*ancestors, key_name)


def _path_has_suffix(path: tuple[str, ...], suffixes: set[tuple[str, ...]]) -> bool:
    return any(len(path) >= len(suffix) and path[-len(suffix) :] == suffix for suffix in suffixes)


def _is_objects_value_path(path: tuple[str, ...]) -> bool:
    return len(path) >= 2 and path[0] == "objects"


def _scalar_python_completion_prefix_at_position(
    source: str,
    line: int,
    character: int,
) -> tuple[tuple[str, ...], str] | None:
    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]
    match = _KEY_VALUE_RE.match(text)
    if match is None:
        return None
    key_name = match.group(2).strip()
    key_path = _key_path(source, line, key_name)
    parent = key_path[-2] if len(key_path) >= 2 else None
    if (
        not _path_has_suffix(key_path, _PYTHON_VALUE_KEY_SUFFIXES)
        and parent not in _PYTHON_CHILD_VALUE_PARENTS
        and not _is_objects_value_path(key_path)
    ):
        return None
    raw_value = match.group(3)
    trimmed = raw_value.strip()
    start_character, _end_character = _value_range(raw_value, match.start(3), match.end(3))
    if character < start_character:
        return None
    if not trimmed:
        if _is_objects_value_path(key_path):
            return ((), "")
        return None
    if trimmed in _BLOCK_SCALAR_MARKERS:
        return None
    local_character = max(character - start_character, 0)
    return _python_completion_prefix_in_text(trimmed, 1, local_character)


def _list_item_python_completion_prefix_at_position(
    source: str,
    line: int,
    character: int,
) -> tuple[tuple[str, ...], str] | None:
    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]
    match = _LIST_ITEM_VALUE_RE.match(text)
    if match is None or ":" in match.group(2):
        return None

    key_path = tuple(reversed(_ancestor_keys(source, line)))
    if not _path_has_suffix(key_path, _PYTHON_LIST_VALUE_SUFFIXES):
        return None

    raw_value = match.group(2)
    trimmed = raw_value.strip()
    if not trimmed:
        return None

    start_character, _end_character = _value_range(raw_value, match.start(2), match.end(2))
    if character < start_character:
        return None
    local_character = max(character - start_character, 0)
    return _python_completion_prefix_in_text(trimmed, 1, local_character)


def _python_completion_prefix_at_position(source: str, line: int, character: int) -> tuple[tuple[str, ...], str] | None:
    region = enclosing_block_scalar_region(source, line)
    if region is not None and (
        region.key_name in _PYTHON_BLOCK_KEYS
        or _is_objects_value_path(_key_path(source, region.key_line, region.key_name))
    ):
        local_line = line - region.content_start_line + 1
        local_character = max(character - region.content_indent, 0)
        prefix = _python_completion_prefix_in_text(region.text, local_line, local_character)
        if prefix is not None:
            return prefix

    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]

    cursor_offset = _line_col_to_offset(lines, line, character)
    for mako_region in _iter_mako_block_regions(source):
        if mako_region.is_expression:
            continue
        if not (mako_region.content_start_offset <= cursor_offset < mako_region.content_end_offset):
            continue
        local_offset = cursor_offset - mako_region.content_start_offset
        code_before = mako_region.code_text[:local_offset]
        local_line = code_before.count("\n")
        last_nl = code_before.rfind("\n")
        local_char = local_offset - last_nl - 1 if last_nl != -1 else local_offset
        prefix = _python_completion_prefix_in_text(mako_region.code_text, local_line + 1, local_char)
        if prefix is not None:
            return prefix

    for match in _MAKO_EXPRESSION_RE.finditer(text):
        if not (match.start(1) <= character <= match.end(1) + 1):
            continue
        prefix = _python_completion_prefix_in_text(match.group(1), 1, character - match.start(1))
        if prefix is not None:
            return prefix

    stripped = text.lstrip()
    if stripped.startswith("%"):
        percent_index = text.index("%")
        statement = text[percent_index + 1 :].lstrip()
        if statement:
            statement_start = percent_index + 1 + len(text[percent_index + 1 :]) - len(statement)
            if character >= statement_start:
                prefix = _python_completion_prefix_in_text(statement, 1, character - statement_start)
                if prefix is not None:
                    return prefix

    return _scalar_python_completion_prefix_at_position(
        source, line, character
    ) or _list_item_python_completion_prefix_at_position(
        source,
        line,
        character,
    )


def _add_python_completion_entry(
    entries: dict[str, PythonCompletionTarget],
    label: str,
    detail: str,
    partial: str,
) -> None:
    # Use case-insensitive substring matching so that e.g. "x" matches
    # "except" and "Exception", "exc" matches both, "ept" matches "except", etc.
    # This is the same matching strategy used by the value completion provider
    # for YAML enum values (see ``value_completion_provider``).
    if partial and partial.lower() not in label.lower():
        return
    entries.setdefault(label, PythonCompletionTarget(label=label, detail=detail))


def _keywords_for_context(source: str, line: int, character: int) -> frozenset | None:
    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]

    for match in _MAKO_EXPRESSION_RE.finditer(text):
        if match.start(1) <= character <= match.end(1) + 1:
            return _EXPRESSION_KEYWORDS

    cursor_offset = _line_col_to_offset(lines, line, character)
    for mako_region in _iter_mako_block_regions(source):
        if mako_region.is_expression:
            continue
        if mako_region.content_start_offset <= cursor_offset < mako_region.content_end_offset:
            return _PYTHON_KEYWORDS

    if text.lstrip().startswith("%"):
        return _MAKO_LINE_KEYWORDS

    region = enclosing_block_scalar_region(source, line)
    if region is not None and (
        region.key_name in _PYTHON_BLOCK_KEYS
        or _is_objects_value_path(_key_path(source, region.key_line, region.key_name))
    ):
        return _PYTHON_KEYWORDS

    scalar_prefix = _scalar_python_completion_prefix_at_position(source, line, character)
    if scalar_prefix is not None:
        return _EXPRESSION_KEYWORDS

    list_prefix = _list_item_python_completion_prefix_at_position(source, line, character)
    if list_prefix is not None:
        return _EXPRESSION_KEYWORDS

    return None


def _imported_symbol_completion_detail(binding: PythonNamespaceBinding) -> str:
    if binding.module_path is None or binding.imported_name is None:
        return "symbol"
    return python_module_symbol_detail(binding.module_path, binding.imported_name)


def _is_objects_value_completion_position(source: str, line: int, character: int) -> bool:
    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]
    match = _KEY_VALUE_RE.match(text)
    if match is not None:
        raw_value = match.group(3)
        start_character, _end_character = _value_range(raw_value, match.start(3), match.end(3))
        if character >= start_character:
            key_name = match.group(2).strip()
            return _is_objects_value_path(_key_path(source, line, key_name))
    region = enclosing_block_scalar_region(source, line)
    if region is not None and _is_objects_value_path(_key_path(source, region.key_line, region.key_name)):
        local_line = line - region.content_start_line + 1
        if local_line == 1:
            if ".using(" in region.text.splitlines()[0]:
                return False
            return True
        local_lines = region.text.splitlines()
        if local_line <= len(local_lines):
            local_text = local_lines[local_line - 1]
            local_char = max(character - region.content_indent, 0)
            obj_type_idx = local_text.find("object_type")
            if obj_type_idx != -1:
                eq_idx = local_text.find("=", obj_type_idx)
                if eq_idx != -1 and local_char > eq_idx:
                    return True
        return False
    return False


def _using_kwarg_completions(partial: str) -> list[PythonCompletionTarget]:
    matched = [
        PythonCompletionTarget(label=f"{name}=", detail="kwarg", documentation=_USING_KWARGS[name])
        for name in _USING_KWARGS
        if not partial or partial.lower() in name.lower()
    ]
    matched.sort(
        key=lambda c: (
            0 if partial and c.label.lower().startswith(partial.lower()) else 1,
            c.label,
        )
    )
    return matched


def _da_object_subclass_completions(
    workspace_index: WorkspaceIndex,
    source: str,
    current_path: Path | None,
    partial: str,
) -> list[PythonCompletionTarget] | None:
    class_names: set[str] = set(workspace_index.all_da_object_subclass_names)
    if workspace_index.package_root is None:
        vendored_paths: list[Path] = []
        for module_name in VENDORED_MODULE_NAMES:
            mod_path = resolve_python_module_path(module_name, current_path, workspace_index)
            if mod_path is not None:
                vendored_paths.append(mod_path)
        if vendored_paths:
            class_names = set(compute_da_object_subclasses(vendored_paths, workspace_index=workspace_index))
    for _line, entry in _iter_top_level_list_items(source, "imports"):
        for binding in _parse_import_binding(entry, current_path, workspace_index):
            if binding.alias is not None:
                class_names.add(binding.alias)
    if class_names:
        matched = [
            PythonCompletionTarget(label=name, detail="class")
            for name in class_names
            if not partial or partial.lower() in name.lower()
        ]
        matched.sort(
            key=lambda c: (
                0 if partial and c.label.lower().startswith(partial.lower()) else 1,
                c.label,
            )
        )
        return matched
    return None


def _suggest_using_completions(
    source: str,
    line: int,
    character: int,
    workspace_index: WorkspaceIndex,
    current_path: Path | None,
) -> list[PythonCompletionTarget] | None:
    region = enclosing_block_scalar_region(source, line)
    if region is not None:
        if not _is_objects_value_path(_key_path(source, region.key_line, region.key_name)):
            return None
        local_line = line - region.content_start_line + 1
        local_char = max(character - region.content_indent, 0)
        text = region.text
        lines_list = text.splitlines()
        if local_line > len(lines_list):
            return None
        local_text = lines_list[local_line - 1]
        cursor_text = "\n".join(lines_list[: local_line - 1])
        if cursor_text:
            cursor_text += "\n"
        cursor_text += local_text[:local_char]
    else:
        lines = _document_lines(source)
        text = lines[min(max(line, 0), len(lines) - 1)]
        match = _KEY_VALUE_RE.match(text)
        if match is None:
            return None
        key_name = match.group(2).strip()
        if not _is_objects_value_path(_key_path(source, line, key_name)):
            return None
        raw_value = match.group(3)
        start_character, _end_character = _value_range(raw_value, match.start(3), match.end(3))
        if character < start_character:
            return None
        cursor_text = text[match.start(3) : character]

    using_idx = cursor_text.rfind(".using(")
    if using_idx == -1:
        return None

    after_using = cursor_text[using_idx + len(".using(") :]

    depth = 1
    for ch in after_using:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth <= 0:
                return None

    after_stripped = after_using.rstrip()
    if not after_stripped or after_stripped[-1] in (",", "("):
        return _using_kwarg_completions("") or None

    last_sep = max(after_stripped.rfind(","), after_stripped.rfind("("))
    if last_sep >= 0:
        partial_kwarg = after_stripped[last_sep + 1 :].strip()
        if "=" not in partial_kwarg:
            return _using_kwarg_completions(partial_kwarg) or None
    elif "=" not in after_stripped:
        return _using_kwarg_completions(after_stripped.strip()) or None

    nested = 0
    last_eq = -1
    for i, ch in enumerate(after_using):
        if ch == "(":
            nested += 1
        elif ch == ")":
            nested -= 1
        elif ch == "=" and nested == 0:
            last_eq = i

    if last_eq >= 0:
        kwarg_text = after_using[:last_eq].rstrip()
        kwarg_name = kwarg_text.replace(",", " ").split()[-1] if kwarg_text else ""
        if kwarg_name == "object_type":
            partial_value = after_using[last_eq + 1 :].strip()
            candidates = _da_object_subclass_completions(workspace_index, source, current_path, partial_value)
            if candidates is not None:
                return candidates

    return None


def _python_completion_candidates_from_bindings(
    bindings: list[PythonNamespaceBinding],
    base_chain: tuple[str, ...],
    partial: str,
    *,
    keywords: frozenset | None = None,
    builtins: frozenset | None = None,
) -> list[PythonCompletionTarget]:
    entries: dict[str, PythonCompletionTarget] = {}

    if not base_chain:
        for binding in bindings:
            if binding.kind == "module_star":
                for label, detail in python_module_symbol_details(binding.module_path).items():
                    _add_python_completion_entry(entries, label, detail, partial)
                continue
            if binding.alias is None:
                continue
            detail = "module" if binding.kind == "module_namespace" else _imported_symbol_completion_detail(binding)
            _add_python_completion_entry(entries, binding.alias, detail, partial)
        if keywords is not None:
            for kw in keywords:
                _add_python_completion_entry(entries, kw, "keyword", partial)
        if builtins is not None:
            for exc in builtins:
                _add_python_completion_entry(entries, exc, "exception", partial)
        return sorted(entries.values(), key=lambda entry: entry.label)

    for binding in bindings:
        if binding.kind == "module_namespace":
            if binding.alias != base_chain[0]:
                continue
            members = module_completion_members(binding.module_path, base_chain[1:])
            for label, detail in members.items():
                _add_python_completion_entry(entries, label, detail, partial)
            continue

        if binding.kind == "module_star":
            members = module_completion_members(binding.module_path, base_chain)
            for label, detail in members.items():
                _add_python_completion_entry(entries, label, detail, partial)
            continue

        if binding.alias != base_chain[0] or binding.imported_name is None:
            continue
        members = module_completion_members(binding.module_path, (binding.imported_name, *base_chain[1:]))
        for label, detail in members.items():
            _add_python_completion_entry(entries, label, detail, partial)

    return sorted(entries.values(), key=lambda entry: entry.label)


@dataclass(frozen=True, slots=True)
class PythonNavigationService:
    workspace_index: WorkspaceIndex

    def completion_targets(
        self,
        source: str,
        line: int,
        character: int,
        *,
        uri_or_path: str | Path | None = None,
    ) -> list[PythonCompletionTarget]:
        prefix = _python_completion_prefix_at_position(source, line, character)
        if prefix is None:
            return []

        current_path = path_from_uri_or_path(uri_or_path)

        using_candidates = _suggest_using_completions(source, line, character, self.workspace_index, current_path)
        if using_candidates is not None:
            return using_candidates

        # DAObject subclass + dot → offer .using(
        # Check both precomputed subclass names and import aliases from the current file.
        if _is_objects_value_completion_position(source, line, character):
            base_chain, partial = prefix
            if len(base_chain) == 1:
                known_name = base_chain[0] in self.workspace_index.all_da_object_subclass_names
                if not known_name:
                    for _line, entry in _iter_top_level_list_items(source, "imports"):
                        for binding in _parse_import_binding(entry, current_path, self.workspace_index):
                            if binding.alias == base_chain[0]:
                                known_name = True
                                break
                        if known_name:
                            break
                if known_name and (not partial or partial.lower() in ".using("):
                    start = character - 1 - len(partial)
                    return [
                        PythonCompletionTarget(
                            label=".using()",
                            detail="method",
                            text_edit_range=(start, character),
                        )
                    ]

        # Short-circuit objects: value completions: use precomputed DAObject
        # subclass names plus any import aliases from the current file's ``imports:``.
        if _is_objects_value_completion_position(source, line, character):
            _, partial = prefix
            candidates = _da_object_subclass_completions(self.workspace_index, source, current_path, partial)
            if candidates is not None:
                return candidates

        bindings = _python_namespace_bindings(
            source,
            current_path,
            self.workspace_index,
        )
        base_chain, partial = prefix
        keywords = _keywords_for_context(source, line, character)
        builtins = PYTHON_BUILTIN_EXCEPTIONS if keywords is not None else None
        candidates = _python_completion_candidates_from_bindings(
            bindings,
            base_chain,
            partial,
            keywords=keywords,
            builtins=builtins,
        )
        return candidates

    def module_targets(
        self,
        key_or_parent: str | None,
        value: str | None,
        current_path: Path | None,
    ) -> list[DefinitionTarget]:
        if key_or_parent not in _PYTHON_MODULE_REFERENCE_KEYS or value is None:
            return []

        if key_or_parent == "modules":
            # Package-qualified values (containing ":") are file references,
            # not module names — let the caller handle them.
            if ":" in value:
                return []
            module_name = normalize_module_name(value, current_path)
            if module_name is None:
                return []
            module_path = resolve_python_module_path(module_name, current_path, self.workspace_index)
            if module_path is None:
                return []
            return [DefinitionTarget(path=module_path, line=0, start_character=0, end_character=0)]

        targets: list[DefinitionTarget] = []
        for binding in _parse_import_binding(value, current_path, self.workspace_index):
            if binding.module_path is None:
                continue
            _append_reference_target(targets, binding.module_path, 0, 0, 0)
        return targets


def resolve_python_completion_targets(
    source: str,
    line: int,
    character: int,
    *,
    uri_or_path: str | Path | None = None,
    workspace_index: WorkspaceIndex,
) -> list[PythonCompletionTarget]:
    return PythonNavigationService(workspace_index).completion_targets(
        source,
        line,
        character,
        uri_or_path=uri_or_path,
    )
