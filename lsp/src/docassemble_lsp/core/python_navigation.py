from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from docassemble_lsp.core.definition_models import (
    BlockScalarRegion,
    DefinitionTarget,
    PythonCompletionTarget,
    PythonModuleSymbol,
    PythonNamespaceBinding,
)
from docassemble_lsp.core.line_helpers import _safe_ast_parse
from docassemble_lsp.core.python_modules import (
    PYTHON_BUILTIN_EXCEPTIONS,
    VENDORED_MODULE_NAMES,
    compute_da_object_subclasses,
    load_python_module_index,
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
    _PYTHON_BLOCK_KEYS,
    _PYTHON_MODULE_REFERENCE_KEYS,
    _ancestor_keys,
    _append_reference_target,
    _block_scalar_region_from_key_line,
    _clean_value,
    _document_lines,
    _iter_mako_block_regions,
    _iter_mako_expressions,
    _line_col_to_offset,
    _line_indent,
    _value_range,
)

_PYTHON_VALUE_KEY_SUFFIXES: set[tuple[str, ...]] = {
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
_PYTHON_LIST_VALUE_SUFFIXES: set[tuple[str, ...]] = {
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
_CALLEE_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
_CALL_KWARG_NAME_RE = re.compile(r"\s*([A-Za-z_]\w*)\s*")

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
            if (
                match is not None
                and match.group(2).strip() == key_name
                and not match.group(3).strip()
            ):
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
    statement = (
        entry if entry.lstrip().startswith(("from ", "import ")) else f"import {entry}"
    )
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
                    module_path=resolve_python_module_path(
                        module_name, current_path, workspace_index
                    ),
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
        submodule_name = f"{module_name}.{alias.name}"
        submodule_path = resolve_python_module_path(
            submodule_name, current_path, workspace_index
        )
        if submodule_path is not None:
            bindings.append(
                PythonNamespaceBinding(
                    kind="module_namespace",
                    module_name=submodule_name,
                    module_path=submodule_path,
                    alias=alias.asname or alias.name,
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
        mod_path = resolve_python_module_path(
            module_name, current_path, workspace_index
        )
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
                module_path=resolve_python_module_path(
                    normalized_module_name, current_path, workspace_index
                ),
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
        region = _block_scalar_region_from_key_line(
            lines, key_line, match.group(2).strip(), len(match.group(1))
        )
        if region.content_start_line <= line <= region.end_line:
            return region
    return None


def _python_completion_prefix_in_text(
    text: str, line: int, character: int
) -> tuple[tuple[str, ...], str] | None:
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
    return any(
        len(path) >= len(suffix) and path[-len(suffix) :] == suffix
        for suffix in suffixes
    )


def _is_objects_value_path(path: tuple[str, ...]) -> bool:
    return len(path) >= 2 and path[0] == "objects"


def _scalar_python_value_text_at_position(
    source: str,
    line: int,
    character: int,
) -> str | None:
    """Raw scalar value text before the cursor, or ``None`` outside a Python value.

    An empty value yields ``""`` (still a Python position — e.g. empty
    ``objects:`` values offer subclass names).
    """
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
    start_character, _end_character = _value_range(
        raw_value, match.start(3), match.end(3)
    )
    if character < start_character:
        return None
    if not trimmed:
        return ""
    if trimmed in _BLOCK_SCALAR_MARKERS:
        return None
    local_character = max(character - start_character, 0)
    return raw_value[:local_character]


def _scalar_python_completion_prefix_at_position(
    source: str,
    line: int,
    character: int,
) -> tuple[tuple[str, ...], str] | None:
    value_text = _scalar_python_value_text_at_position(source, line, character)
    if value_text is None:
        return None
    if not value_text:
        if _is_objects_value_completion_position(source, line, character):
            return ((), "")
        return None
    return _python_completion_prefix_in_text(value_text, 1, len(value_text))


def _list_item_python_value_text_at_position(
    source: str,
    line: int,
    character: int,
) -> str | None:
    """Raw list-item value text before the cursor in a Python list value."""
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

    start_character, _end_character = _value_range(
        raw_value, match.start(2), match.end(2)
    )
    if character < start_character:
        return None
    local_character = max(character - start_character, 0)
    return raw_value[:local_character]


def _list_item_python_completion_prefix_at_position(
    source: str,
    line: int,
    character: int,
) -> tuple[tuple[str, ...], str] | None:
    value_text = _list_item_python_value_text_at_position(source, line, character)
    if value_text is None:
        return None
    return _python_completion_prefix_in_text(value_text, 1, len(value_text))


def _python_code_text_at_position(source: str, line: int, character: int) -> str | None:
    """Python code text before the cursor, or ``None`` outside a Python context.

    Covers the same contexts the prefix logic handles: Python block scalars,
    Mako block regions, ``${...}`` expressions, ``%`` lines, and scalar/list
    Python values.
    """
    region = enclosing_block_scalar_region(source, line)
    if region is not None and (
        region.key_name in _PYTHON_BLOCK_KEYS
        or _is_objects_value_path(_key_path(source, region.key_line, region.key_name))
    ):
        local_line = line - region.content_start_line + 1
        local_character = max(character - region.content_indent, 0)
        region_lines = region.text.splitlines() or [""]
        if not (1 <= local_line <= len(region_lines)):
            return None
        before = "\n".join(region_lines[: local_line - 1])
        if before:
            before += "\n"
        return before + region_lines[local_line - 1][:local_character]

    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]

    cursor_offset = _line_col_to_offset(lines, line, character)
    for mako_region in _iter_mako_block_regions(source):
        if mako_region.is_expression:
            continue
        if not (
            mako_region.content_start_offset
            <= cursor_offset
            < mako_region.content_end_offset
        ):
            continue
        local_offset = cursor_offset - mako_region.content_start_offset
        return mako_region.code_text[:local_offset]

    for expr, expr_start, expr_end in _iter_mako_expressions(text):
        if not (expr_start <= character <= expr_end + 1):
            continue
        return expr[: max(character - expr_start, 0)]

    stripped = text.lstrip()
    if stripped.startswith("%"):
        percent_index = text.index("%")
        statement = text[percent_index + 1 :].lstrip()
        if statement:
            statement_start = (
                percent_index + 1 + len(text[percent_index + 1 :]) - len(statement)
            )
            if character >= statement_start:
                return statement[: character - statement_start]

    scalar_text = _scalar_python_value_text_at_position(source, line, character)
    if scalar_text is not None:
        return scalar_text
    return _list_item_python_value_text_at_position(
        source,
        line,
        character,
    )


def _python_completion_prefix_at_position(
    source: str,
    line: int,
    character: int,
    *,
    code_text: str | None = None,
) -> tuple[tuple[str, ...], str] | None:
    code = (
        _python_code_text_at_position(source, line, character)
        if code_text is None
        else code_text
    )
    if code is None:
        return None
    if not code:
        if _is_objects_value_completion_position(source, line, character):
            return ((), "")
        return None
    code_lines = code.splitlines() or [""]
    return _python_completion_prefix_in_text(code, len(code_lines), len(code_lines[-1]))


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

    for _expr, expr_start, expr_end in _iter_mako_expressions(text):
        if expr_start <= character <= expr_end + 1:
            return _EXPRESSION_KEYWORDS

    cursor_offset = _line_col_to_offset(lines, line, character)
    for mako_region in _iter_mako_block_regions(source):
        if mako_region.is_expression:
            continue
        if (
            mako_region.content_start_offset
            <= cursor_offset
            < mako_region.content_end_offset
        ):
            return _PYTHON_KEYWORDS

    if text.lstrip().startswith("%"):
        return _MAKO_LINE_KEYWORDS

    region = enclosing_block_scalar_region(source, line)
    if region is not None and (
        region.key_name in _PYTHON_BLOCK_KEYS
        or _is_objects_value_path(_key_path(source, region.key_line, region.key_name))
    ):
        return _PYTHON_KEYWORDS

    scalar_prefix = _scalar_python_completion_prefix_at_position(
        source, line, character
    )
    if scalar_prefix is not None:
        return _EXPRESSION_KEYWORDS

    list_prefix = _list_item_python_completion_prefix_at_position(
        source, line, character
    )
    if list_prefix is not None:
        return _EXPRESSION_KEYWORDS

    return None


def _imported_symbol_completion_detail(
    binding: PythonNamespaceBinding, *, workspace_index: WorkspaceIndex
) -> str:
    if binding.module_path is None or binding.imported_name is None:
        return "symbol"
    return python_module_symbol_detail(
        binding.module_path,
        binding.imported_name,
        workspace_index=workspace_index,
    )


def _is_objects_value_completion_position(
    source: str, line: int, character: int
) -> bool:
    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]
    match = _KEY_VALUE_RE.match(text)
    if match is not None:
        raw_value = match.group(3)
        start_character, _end_character = _value_range(
            raw_value, match.start(3), match.end(3)
        )
        if character >= start_character:
            key_name = match.group(2).strip()
            return _is_objects_value_path(_key_path(source, line, key_name))
    region = enclosing_block_scalar_region(source, line)
    if region is not None and _is_objects_value_path(
        _key_path(source, region.key_line, region.key_name)
    ):
        local_line = line - region.content_start_line + 1
        if local_line == 1:
            return ".using(" not in region.text.splitlines()[0]
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
        PythonCompletionTarget(
            label=f"{name}=", detail="kwarg", documentation=_USING_KWARGS[name]
        )
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
            mod_path = resolve_python_module_path(
                module_name, current_path, workspace_index
            )
            if mod_path is not None:
                vendored_paths.append(mod_path)
        if vendored_paths:
            class_names = set(
                compute_da_object_subclasses(
                    vendored_paths, workspace_index=workspace_index
                )
            )
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
        if not _is_objects_value_path(
            _key_path(source, region.key_line, region.key_name)
        ):
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
        start_character, _end_character = _value_range(
            raw_value, match.start(3), match.end(3)
        )
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
            candidates = _da_object_subclass_completions(
                workspace_index, source, current_path, partial_value
            )
            if candidates is not None:
                return candidates

    return None


def _skip_string(code_text: str, index: int) -> int:
    """Advance past a string literal starting at *index* (a quote char)."""
    quote = code_text[index]
    triple = code_text.startswith(quote * 3, index)
    end = index + 3 if triple else index + 1
    while end < len(code_text):
        char = code_text[end]
        if char == "\\":
            end += 2
            continue
        if char == quote:
            if triple:
                if code_text.startswith(quote * 3, end):
                    return end + 3
            else:
                return end + 1
        end += 1
    return len(code_text)


def _without_python_comments(code_text: str) -> str:
    """Replace comments with spaces while preserving source offsets."""
    chars = list(code_text)
    index = 0
    while index < len(chars):
        char = chars[index]
        if char in ("'", '"'):
            index = _skip_string(code_text, index)
            continue
        if char == "#":
            end = code_text.find("\n", index)
            if end == -1:
                end = len(chars)
            for comment_index in range(index, end):
                chars[comment_index] = " "
            index = end
            continue
        index += 1
    return "".join(chars)


def _is_matching_delimiter(open_char: str, close_char: str) -> bool:
    return (open_char, close_char) in {
        ("(", ")"),
        ("[", "]"),
        ("{", "}"),
    }


def _has_unquoted_char(text: str, wanted: frozenset[str]) -> bool:
    text = _without_python_comments(text)
    index = 0
    while index < len(text):
        char = text[index]
        if char in ("'", '"'):
            index = _skip_string(text, index)
            continue
        if char in wanted:
            return True
        index += 1
    return False


def _call_argument_context(
    code_text: str,
) -> tuple[tuple[str, ...] | None, str | None]:
    """Return ``(callee chain, arg text up to cursor)`` when the cursor sits
    inside an unbalanced function call in *code_text*."""
    code_text = _without_python_comments(code_text)
    delimiters: list[tuple[str, int]] = []
    index = 0
    while index < len(code_text):
        char = code_text[index]
        if char in ("'", '"'):
            index = _skip_string(code_text, index)
            continue
        if char in "([{":
            delimiters.append((char, index))
        elif (
            char in ")]}"
            and delimiters
            and _is_matching_delimiter(delimiters[-1][0], char)
        ):
            delimiters.pop()
        index += 1
    open_positions = [
        position for delimiter, position in delimiters if delimiter == "("
    ]
    if not open_positions:
        return None, None
    open_pos = open_positions[-1]
    callee_match = _CALLEE_RE.search(code_text[:open_pos])
    if callee_match is None:
        return None, None
    return tuple(callee_match.group(0).split(".")), code_text[open_pos + 1 :]


def _call_kwarg_partial(arg_text: str) -> str | None:
    """Return the partial kwarg name being typed, or ``None`` when the cursor
    is not at a kwarg-name position (e.g. typing a value)."""
    arg_text = _without_python_comments(arg_text)
    delimiters: list[str] = []
    last_sep = -1
    index = 0
    while index < len(arg_text):
        char = arg_text[index]
        if char in ("'", '"'):
            index = _skip_string(arg_text, index)
            continue
        if char in "([{":
            delimiters.append(char)
        elif char in ")]}":
            if delimiters and _is_matching_delimiter(delimiters[-1], char):
                delimiters.pop()
        elif char == "," and not delimiters:
            last_sep = index
        index += 1
    partial = arg_text[last_sep + 1 :].strip()
    if not partial:
        return ""
    if (
        delimiters
        or any(char in partial for char in ('"', "'"))
        or _has_unquoted_char(partial, frozenset("=()[]{}"))
    ):
        return None
    return partial


def _iter_top_level_segments(arg_text: str) -> list[str]:
    """Split call argument text on top-level commas (string-aware)."""
    arg_text = _without_python_comments(arg_text)
    segments: list[str] = []
    delimiters: list[str] = []
    start = 0
    index = 0
    while index <= len(arg_text):
        if index == len(arg_text):
            segments.append(arg_text[start:index])
            break
        char = arg_text[index]
        if char in ("'", '"'):
            index = _skip_string(arg_text, index)
            continue
        if char in "([{":
            delimiters.append(char)
        elif char in ")]}":
            if delimiters and _is_matching_delimiter(delimiters[-1], char):
                delimiters.pop()
        elif char == "," and not delimiters:
            segments.append(arg_text[start:index])
            start = index + 1
        index += 1
    return segments


def _top_level_assignment_name(segment: str) -> str | None:
    """Return a single top-level keyword name, if *segment* has one."""
    segment = _without_python_comments(segment)
    delimiters: list[str] = []
    index = 0
    while index < len(segment):
        char = segment[index]
        if char in ("'", '"'):
            index = _skip_string(segment, index)
            continue
        if char in "([{":
            delimiters.append(char)
        elif char in ")]}":
            if delimiters and _is_matching_delimiter(delimiters[-1], char):
                delimiters.pop()
        elif char == "=" and not delimiters:
            previous = segment[index - 1] if index else ""
            following = segment[index + 1] if index + 1 < len(segment) else ""
            if previous in "=!<>+-*/%@&|^:" or following in "=<>":
                index += 1
                continue
            match = _CALL_KWARG_NAME_RE.fullmatch(segment[:index])
            if match is not None:
                return match.group(1)
        index += 1
    return None


def _used_call_kwargs(arg_text: str) -> set[str]:
    used: set[str] = set()
    for segment in _iter_top_level_segments(arg_text):
        name = _top_level_assignment_name(segment)
        if name is not None:
            used.add(name)
    return used


def _positional_arg_count(arg_text: str) -> int:
    count = 0
    segments = _iter_top_level_segments(arg_text)
    for index, segment in enumerate(segments):
        stripped = segment.strip()
        if not stripped or _top_level_assignment_name(segment) is not None:
            continue
        # A star expansion has an unknown number of positional values. Do not
        # consume a fixed parameter slot based on it.
        if stripped.startswith("*"):
            continue
        if index < len(segments) - 1 or arg_text.rstrip().endswith(","):
            count += 1
    return count


def _module_star_exports_name(
    module_path: Path | None,
    name: str,
    workspace_index: WorkspaceIndex,
) -> bool:
    if module_path is None:
        return False
    index = load_python_module_index(module_path, workspace_index=workspace_index)
    if index.exported_names is not None:
        return name in index.exported_names
    return not name.startswith("_")


def _symbol_after_chain(
    module_path: Path,
    name: str,
    workspace_index: WorkspaceIndex,
    seen: set[tuple[Path, str]],
) -> PythonModuleSymbol | None:
    """Resolve *name* inside *module_path*, following re-export chains."""
    key = (module_path.resolve(), name)
    if key in seen:
        return None
    seen.add(key)
    index = load_python_module_index(module_path, workspace_index=workspace_index)
    symbol = index.symbols.get(name)
    if symbol is None:
        return None
    if symbol.kind == "function":
        return symbol
    if symbol.imported_module_path is not None and symbol.imported_name is not None:
        return _symbol_after_chain(
            symbol.imported_module_path,
            symbol.imported_name,
            workspace_index,
            seen,
        )
    return None


def _sibling_module_path(module_path: Path, name: str) -> Path | None:
    """Resolve *name* as a module or package sibling of *module_path*."""
    directory = module_path.parent
    sibling = directory / f"{name}.py"
    if sibling.is_file():
        return sibling.resolve()
    package = directory / name / "__init__.py"
    if package.is_file():
        return package.resolve()
    return None


def _symbol_after_chain_segments(
    module_path: Path,
    chain: tuple[str, ...],
    workspace_index: WorkspaceIndex,
    seen: set[tuple[Path, str]],
) -> PythonModuleSymbol | None:
    """Resolve *chain* of names through module boundaries to a function symbol.

    Intermediate names must resolve to imported modules (``import sub``, a
    re-export via ``from x import y``, or a sibling submodule); a function
    symbol is only returned when it is the final segment.
    """
    index = load_python_module_index(module_path, workspace_index=workspace_index)
    symbol = index.symbols.get(chain[0])
    if symbol is None:
        return None
    key = (module_path.resolve(), chain[0])
    if key in seen:
        return None
    seen.add(key)
    if symbol.kind == "function":
        return symbol if len(chain) == 1 else None

    target_path = symbol.imported_module_path
    if target_path is None:
        # Unresolvable import: fall back to a sibling module of the same name.
        if len(chain) == 1:
            return None
        sibling = _sibling_module_path(module_path, chain[0])
        if sibling is None:
            return None
        return _symbol_after_chain_segments(sibling, chain[1:], workspace_index, seen)

    if (
        target_path.resolve() == module_path.resolve()
        and symbol.imported_name is not None
    ):
        # ``from . import sub``: the symbol points back at the package itself;
        # hop to the sibling submodule instead of looping.
        if len(chain) == 1:
            return None
        sibling = _sibling_module_path(module_path, symbol.imported_name)
        if sibling is None:
            return None
        return _symbol_after_chain_segments(sibling, chain[1:], workspace_index, seen)

    delegated = (
        (symbol.imported_name,) if symbol.imported_name is not None else ()
    ) + chain[1:]
    if not delegated:
        return None
    return _symbol_after_chain_segments(
        target_path,
        delegated,
        workspace_index,
        seen,
    )


def _resolve_callable_symbol(
    callee_chain: tuple[str, ...],
    source: str,
    current_path: Path | None,
    workspace_index: WorkspaceIndex,
) -> PythonModuleSymbol | None:
    """Resolve a called name to its function symbol, or ``None``."""
    if not callee_chain:
        return None
    name = callee_chain[0]
    if name in _PYTHON_KEYWORDS or name in _EXPRESSION_KEYWORDS:
        return None
    bindings = _python_namespace_bindings(source, current_path, workspace_index)
    seen: set[tuple[Path, str]] = set()
    if len(callee_chain) == 1:
        for binding in bindings:
            if binding.module_path is None:
                continue
            if binding.kind == "module_star":
                if not _module_star_exports_name(
                    binding.module_path, name, workspace_index
                ):
                    continue
                symbol = _symbol_after_chain(
                    binding.module_path, name, workspace_index, seen
                )
            elif binding.kind == "symbol" and binding.alias == name:
                symbol = _symbol_after_chain(
                    binding.module_path,
                    binding.imported_name or name,
                    workspace_index,
                    seen,
                )
            else:
                continue
            if symbol is not None:
                return symbol
        return None

    for binding in bindings:
        if binding.kind != "module_namespace" or binding.alias != name:
            continue
        if binding.module_path is None:
            continue
        return _symbol_after_chain_segments(
            binding.module_path, callee_chain[1:], workspace_index, seen
        )
    return None


def _suggest_call_kwarg_completions(
    code_text: str,
    source: str,
    current_path: Path | None,
    workspace_index: WorkspaceIndex,
) -> list[PythonCompletionTarget] | None:
    """Suggest ``name=`` completions for the innermost call in *code_text*.

    Returns ``[]`` when the callee resolves but has no suggestible
    parameters (suppressing unrelated symbol completions), and ``None``
    when the position is not a call-argument kwarg slot or the callee
    cannot be resolved.
    """
    callee_chain, arg_text = _call_argument_context(code_text)
    if callee_chain is None or arg_text is None:
        return None
    partial = _call_kwarg_partial(arg_text)
    if partial is None:
        return None
    symbol = _resolve_callable_symbol(
        callee_chain, source, current_path, workspace_index
    )
    if symbol is None:
        return None

    used = _used_call_kwargs(arg_text)
    positional_remaining = _positional_arg_count(arg_text)
    names: dict[str, str] = {}
    for kind, param_name, default in symbol.parameters:
        if kind == "posonly":
            if positional_remaining > 0:
                positional_remaining -= 1
            continue
        if kind == "pos" and positional_remaining > 0:
            positional_remaining -= 1
            continue
        if param_name in used:
            continue
        names[param_name] = f"default: {default}" if default else ""

    matched = [
        PythonCompletionTarget(
            label=f"{name}=",
            detail="kwarg",
            documentation=documentation or None,
        )
        for name, documentation in names.items()
        if not partial or partial.lower() in name.lower()
    ]
    matched.sort(
        key=lambda candidate: (
            0 if partial and candidate.label.lower().startswith(partial.lower()) else 1,
            candidate.label,
        )
    )
    return matched


def _python_completion_candidates_from_bindings(
    bindings: list[PythonNamespaceBinding],
    base_chain: tuple[str, ...],
    partial: str,
    *,
    workspace_index: WorkspaceIndex,
    keywords: frozenset | None = None,
    builtins: frozenset | None = None,
) -> list[PythonCompletionTarget]:
    entries: dict[str, PythonCompletionTarget] = {}

    if not base_chain:
        for binding in bindings:
            if binding.kind == "module_star":
                for label, detail in python_module_symbol_details(
                    binding.module_path,
                    workspace_index=workspace_index,
                ).items():
                    _add_python_completion_entry(entries, label, detail, partial)
                continue
            if binding.alias is None:
                continue
            detail = (
                "module"
                if binding.kind == "module_namespace"
                else _imported_symbol_completion_detail(
                    binding, workspace_index=workspace_index
                )
            )
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
            members = module_completion_members(
                binding.module_path,
                base_chain[1:],
                workspace_index=workspace_index,
            )
            for label, detail in members.items():
                _add_python_completion_entry(entries, label, detail, partial)
            continue

        if binding.kind == "module_star":
            if not _module_star_exports_name(
                binding.module_path, base_chain[0], workspace_index
            ):
                continue
            members = module_completion_members(
                binding.module_path,
                base_chain,
                workspace_index=workspace_index,
            )
            for label, detail in members.items():
                _add_python_completion_entry(entries, label, detail, partial)
            continue

        if binding.alias != base_chain[0] or binding.imported_name is None:
            continue
        members = module_completion_members(
            binding.module_path,
            (binding.imported_name, *base_chain[1:]),
            workspace_index=workspace_index,
        )
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
        code_text = _python_code_text_at_position(source, line, character)
        current_path = path_from_uri_or_path(uri_or_path)

        using_candidates = _suggest_using_completions(
            source, line, character, self.workspace_index, current_path
        )
        if using_candidates is not None:
            return using_candidates

        # DAObject subclass + dot → offer .using(
        # Check both precomputed subclass names and import aliases from the current file.
        if _is_objects_value_completion_position(source, line, character):
            prefix = _python_completion_prefix_at_position(
                source, line, character, code_text=code_text
            )
            if prefix is None:
                return []
            base_chain, partial = prefix
            if len(base_chain) == 1:
                known_name = (
                    base_chain[0] in self.workspace_index.all_da_object_subclass_names
                )
                if not known_name:
                    for _line, entry in _iter_top_level_list_items(source, "imports"):
                        for binding in _parse_import_binding(
                            entry, current_path, self.workspace_index
                        ):
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
            _, partial = prefix
            candidates = _da_object_subclass_completions(
                self.workspace_index, source, current_path, partial
            )
            if candidates is not None:
                return candidates

        # Inside a function call: suggest the callee's keyword arguments.
        if code_text is not None:
            call_candidates = _suggest_call_kwarg_completions(
                code_text, source, current_path, self.workspace_index
            )
            if call_candidates is not None:
                return call_candidates

        prefix = _python_completion_prefix_at_position(
            source, line, character, code_text=code_text
        )
        if prefix is None:
            return []

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
            workspace_index=self.workspace_index,
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
            module_path = resolve_python_module_path(
                module_name, current_path, self.workspace_index
            )
            if module_path is None:
                return []
            return [
                DefinitionTarget(
                    path=module_path, line=0, start_character=0, end_character=0
                )
            ]

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
