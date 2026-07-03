from __future__ import annotations

import re
from pathlib import Path

from docassemble_lsp.core.definition_models import BlockScalarRegion, DefinitionTarget, MakoBlockRegion

_BLOCK_SCALAR_MARKERS = frozenset({"|", ">", "|-", ">-", "|+", ">+"})

_FILE_REFERENCE_KEYS = frozenset(
    {
        "include",
        "template file",
        "rtf template file",
        "docx reference file",
        "pdf template file",
        "docx template file",
        "content file",
        "initial yaml",
        "additional yaml",
    }
)

_FILE_REFERENCE_LIST_PARENTS = frozenset(
    {
        "include",
        "modules",
        "translations",
        "initial yaml",
        "additional yaml",
    }
)

_NON_ATTACHMENT_FILE_KEYS = frozenset({"include", "initial yaml", "additional yaml"})
_ATTACHMENT_FILE_KEYS = _FILE_REFERENCE_KEYS - _NON_ATTACHMENT_FILE_KEYS

_EVENT_REFERENCE_KEYS = frozenset({"action", "error action", "check in"})

_FIELD_CONDITION_KEYS = frozenset({"show if", "hide if", "enable if", "disable if"})

_STATIC_FILE_PARENT_KEYS = frozenset({"css", "javascript"})

_PYTHON_MODULE_REFERENCE_KEYS = frozenset({"imports", "modules"})

_PYTHON_BLOCK_KEYS = frozenset({"code", "validation code"})

_KEY_VALUE_RE = re.compile(r"^(\s*)(?:-\s*)?([^:#][^:]*?)\s*:\s*(.*?)\s*$")
_LIST_ITEM_VALUE_RE = re.compile(r"^(\s*)-\s*(.*?)\s*$")
_MAKO_EXPRESSION_RE = re.compile(r"\$\{([^}]*)\}")
_MAKO_BLOCK_RE = re.compile(r"<%(=?|!)(?![a-zA-Z])(.*?)%>", re.DOTALL)
_MAKO_BLOCK_OPEN_RE = re.compile(r"<%(=?|!)(?![a-zA-Z])([^%]*)$", re.MULTILINE)


def _document_lines(source: str) -> list[str]:
    return source.splitlines() or [""]


def _line_indent(text: str) -> int:
    return len(text) - len(text.lstrip(" "))


def _strip_inline_comment(value: str) -> str:
    comment_index = value.find(" #")
    if comment_index != -1:
        return value[:comment_index].rstrip()
    return value.strip()


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _clean_value(value: str) -> str:
    return _strip_quotes(_strip_inline_comment(value))


def _clean_value_and_range(raw_value: str, start: int, end: int) -> tuple[str, int, int]:
    del end
    leading_offset = len(raw_value) - len(raw_value.lstrip())
    value_text = raw_value[leading_offset:]
    comment_index = value_text.find(" #")
    if comment_index != -1:
        value_text = value_text[:comment_index]
    value_text = value_text.rstrip()

    value_start = start + leading_offset
    value_end = value_start + len(value_text)
    if len(value_text) >= 2 and value_text[0] == value_text[-1] and value_text[0] in {'"', "'"}:
        value_start += 1
        value_end -= 1
        value_text = value_text[1:-1]
    return (value_text, value_start, value_end)


def _value_range(raw_value: str, start: int, end: int) -> tuple[int, int]:
    start_character = start + len(raw_value) - len(raw_value.lstrip())
    end_character = end - len(raw_value) + len(raw_value.rstrip())
    return (start_character, end_character)


def _precompute_parent_keys(source: str) -> list[str | None]:
    """Return the immediate parent key for each line, computed in one forward pass.

    Returns a list parallel to ``_document_lines(source)`` where each entry
    is the key of the nearest enclosing YAML mapping for that line, or
    ``None`` if the line is not inside any mapping scope.

    This is O(n) — use it in per-line loops instead of calling O(n²)
    ``_ancestor_keys(source, line_index)`` for each line.
    """
    lines = _document_lines(source)
    parents: list[str | None] = [None] * len(lines)
    stack: list[tuple[int, str]] = []
    for i, text in enumerate(lines):
        if text.strip() == "---":
            stack = []
            continue
        current_indent = _line_indent(text) if text.strip() else 0
        trimmed = list(stack)
        while trimmed and trimmed[-1][0] >= current_indent:
            trimmed.pop()
        parents[i] = trimmed[-1][1] if trimmed else None
        match = _KEY_VALUE_RE.match(text)
        if match is not None:
            indent = len(match.group(1))
            key = match.group(2).strip()
            prefix = text[match.end(1) : match.start(2)]
            if prefix:
                indent += len(prefix)
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, key))
    return parents


def _ancestor_keys(source: str, line: int) -> list[str]:
    lines = _document_lines(source)
    if not lines or line <= 0:
        return []

    stack: list[tuple[int, str]] = []
    current_indent = _line_indent(lines[min(line, len(lines) - 1)])
    for index in range(line):
        text = lines[index]
        if text.strip() == "---":
            stack = []
            continue
        match = _KEY_VALUE_RE.match(text)
        if match is None:
            continue
        indent = len(match.group(1))
        key = match.group(2).strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))

    while stack and stack[-1][0] >= current_indent:
        stack.pop()

    return [key for _, key in reversed(stack)]


def _append_reference_target(
    targets: list[DefinitionTarget],
    path: Path,
    line: int,
    start_character: int,
    end_character: int,
) -> None:
    target = DefinitionTarget(
        path=path,
        line=line,
        start_character=start_character,
        end_character=end_character,
    )
    if target not in targets:
        targets.append(target)


def _is_list_key_match(text: str, match: re.Match[str]) -> bool:
    between = text[match.end(1) : match.start(2)]
    return "-" in between


def _block_scalar_region_from_key_line(
    lines: list[str], key_line: int, key_name: str, key_indent: int
) -> BlockScalarRegion:
    end_line = len(lines) - 1
    for line_index in range(key_line + 1, len(lines)):
        text = lines[line_index]
        if text.strip() == "---":
            end_line = line_index - 1
            break
        if text.strip() and _line_indent(text) <= key_indent:
            end_line = line_index - 1
            break
    content_start_line = key_line + 1
    content_lines = lines[content_start_line : end_line + 1]
    non_empty_indents = [_line_indent(text) for text in content_lines if text.strip()]
    content_indent = min(non_empty_indents) if non_empty_indents else key_indent + 2
    text = "\n".join(
        line[content_indent:] if line.strip() and len(line) >= content_indent else "" for line in content_lines
    )
    return BlockScalarRegion(
        key_name=key_name,
        key_line=key_line,
        content_start_line=content_start_line,
        end_line=end_line,
        content_indent=content_indent,
        text=text,
    )


def _line_col_to_offset(lines: list[str], line: int, character: int) -> int:
    offsets: list[int] = []
    cum = 0
    for text_line in lines:
        offsets.append(cum)
        cum += len(text_line) + 1
    if line >= len(offsets):
        return cum
    return offsets[line] + character


def _iter_mako_block_regions(source: str, *, include_incomplete: bool = True) -> list[MakoBlockRegion]:
    regions: list[MakoBlockRegion] = []
    for match in _MAKO_BLOCK_RE.finditer(source):
        modifier = match.group(1)
        content_start = match.start(2)
        content_end = match.end(2)
        code = match.group(2)
        regions.append(
            MakoBlockRegion(
                code_text=code,
                is_expression=(modifier == "="),
                is_module_level=(modifier == "!"),
                content_start_offset=content_start,
                content_end_offset=content_end,
            )
        )

    if include_incomplete:
        for match in _MAKO_BLOCK_OPEN_RE.finditer(source):
            if any(r.content_start_offset <= match.start(2) < r.content_end_offset for r in regions):
                continue
            modifier = match.group(1)
            code = match.group(2)
            regions.append(
                MakoBlockRegion(
                    code_text=code,
                    is_expression=(modifier == "="),
                    is_module_level=(modifier == "!"),
                    content_start_offset=match.start(2),
                    content_end_offset=match.end(2),
                )
            )

    return regions
