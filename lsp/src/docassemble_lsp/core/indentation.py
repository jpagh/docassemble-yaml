from __future__ import annotations

import re


def leading_whitespace(text: str) -> str:
    match = re.match(r"^(\s*)", text)
    return match.group(1) if match is not None else ""


def indent_unit_between(parent_indent: str, child_indent: str, *, fallback: str) -> str:
    if child_indent.startswith(parent_indent):
        unit = child_indent[len(parent_indent) :]
        if unit:
            return unit
    return fallback


def infer_indent_unit(source: str, line: int, *, fallback: str = "  ") -> str:
    lines = source.splitlines()
    if not lines:
        return fallback

    bounded_line = min(max(line, 0), len(lines) - 1)
    current_indent = leading_whitespace(lines[bounded_line])
    if not current_indent:
        return fallback

    for index in range(max(bounded_line - 1, 0), -1, -1):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        candidate_indent = leading_whitespace(text)
        if len(candidate_indent) >= len(current_indent):
            continue
        if current_indent.startswith(candidate_indent):
            indent_unit = current_indent[len(candidate_indent) :]
            if indent_unit:
                return indent_unit

    return current_indent or fallback
