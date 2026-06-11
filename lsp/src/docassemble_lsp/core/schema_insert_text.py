from __future__ import annotations

from dataclasses import replace

from docassemble_lsp.core.schema_models import CompletionCandidate


def _convert_snippet_indent(leading: str, indent_unit: str) -> str:
    if not leading:
        return ""
    if set(leading) == {" "}:
        levels, remainder = divmod(len(leading), 2)
        return f"{indent_unit * levels}{' ' * remainder}"
    return leading


def contextualize_multiline_insert_text(insert_text: str, indent_unit: str = "  ") -> str:
    if "\n" not in insert_text:
        return insert_text

    snippet_lines = insert_text.split("\n")
    adjusted_lines = [snippet_lines[0]]

    for snippet_line in snippet_lines[1:]:
        leading = len(snippet_line) - len(snippet_line.lstrip())
        adjusted_lines.append(f"{_convert_snippet_indent(snippet_line[:leading], indent_unit)}{snippet_line[leading:]}")

    return "\n".join(adjusted_lines)


def contextualize_completion_candidates(
    candidates: list[CompletionCandidate], indent_unit: str = "  "
) -> list[CompletionCandidate]:
    return [
        replace(
            candidate,
            insert_text=contextualize_multiline_insert_text(candidate.insert_text, indent_unit=indent_unit),
        )
        if "\n" in candidate.insert_text
        else candidate
        for candidate in candidates
    ]
