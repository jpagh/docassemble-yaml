from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import black
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError

from docassemble_lsp.core.jinja import contains_jinja_syntax, has_jinja_header
from docassemble_lsp.core.yaml_parsing import normalize_yaml_for_parser


# Black's target_versions follow the installed black version (see pyproject.toml dependencies).
@dataclass
class FormatterConfig:
    python_keys: set[str] = field(default_factory=lambda: {"code", "validation code"})
    black_line_length: int = 88
    indent: int = 2
    convert_tabs_to_spaces: bool = False
    strip_trailing_whitespace: bool = True


@dataclass(frozen=True, slots=True)
class FormatResult:
    text: str
    changed: bool
    error: str | None = None


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _convert_tabs_to_spaces(text: str) -> str:
    return text.replace("\t", "  ")


def _strip_common_indent(lines: list[str]) -> tuple[list[str], int]:
    indents = []
    for line in lines:
        if line.strip():
            indents.append(len(line) - len(line.lstrip(" ")))

    if not indents:
        return lines, 0

    min_indent = min(indents)
    dedented = []
    for line in lines:
        if len(line) >= min_indent:
            dedented.append(line[min_indent:])
        else:
            dedented.append(line.lstrip() if line.strip() else "")
    return dedented, min_indent


def _reindent_python(text: str, target_indent: int) -> str:
    result_lines = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip(" ")
        leading = len(line) - len(stripped)
        if leading > 0 and leading % 4 == 0:
            levels = leading // 4
            new_indent = " " * (levels * target_indent)
            result_lines.append(new_indent + stripped)
        else:
            result_lines.append(line)
    return "".join(result_lines)


def _reindent(text: str, indent: int) -> str:
    if indent <= 0:
        return text

    padding = " " * indent
    lines = text.splitlines(keepends=True)
    result = []
    for line in lines:
        if line.strip():
            result.append(padding + line)
        else:
            result.append(line)
    return "".join(result)


def format_python_code(
    code: str,
    config: FormatterConfig | None = None,
    original_indent: int = 0,
) -> str:
    if config is None:
        config = FormatterConfig()

    code = _normalize_newlines(code)
    lines = code.splitlines(keepends=True)
    dedented_lines, removed_indent = _strip_common_indent(lines)
    dedented_text = "".join(dedented_lines)

    if not dedented_text.endswith("\n"):
        dedented_text += "\n"

    mode = black.Mode(
        line_length=config.black_line_length,
    )
    try:
        formatted = black.format_file_contents(dedented_text, fast=False, mode=mode)
    except black.NothingChanged:
        formatted = dedented_text

    formatted = _reindent_python(formatted, config.indent)

    if config.strip_trailing_whitespace:
        formatted = "\n".join(line.rstrip() for line in formatted.splitlines())
        if formatted and not formatted.endswith("\n"):
            formatted += "\n"

    if removed_indent > 0:
        formatted = _reindent(formatted, removed_indent)

    if original_indent > 0:
        formatted = _reindent(formatted, original_indent)

    return formatted


def _count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _find_block_body_span(lines: list[str], header_line: int) -> tuple[int, int, int]:
    header_indent = _count_leading_spaces(lines[header_line])
    start = header_line + 1
    if start >= len(lines):
        return start, start - 1, 0

    line_index = start
    first_body_indent: int | None = None
    while line_index < len(lines):
        line = lines[line_index]
        if line.strip() == "":
            line_index += 1
            continue

        leading = _count_leading_spaces(line)

        if first_body_indent is None:
            if leading <= header_indent:
                break
            first_body_indent = leading
            line_index += 1
            continue

        if leading < first_body_indent:
            break

        line_index += 1

    end = line_index - 1
    if first_body_indent is None:
        first_body_indent = header_indent + 2

    return start, end, first_body_indent


def _collect_text_replacements_for_doc(
    doc: Any, lines: list[str], config: FormatterConfig, path: tuple[str, ...] = ()
) -> list[tuple[int, int, str, tuple[str, ...]]]:
    replacements: list[tuple[int, int, str, tuple[str, ...]]] = []

    if isinstance(doc, CommentedMap):
        has_lc_key = hasattr(doc.lc, "key")
        for key, value in doc.items():
            key_str = str(key)
            current_path = path + (key_str,)

            if key_str in config.python_keys and isinstance(value, str) and has_lc_key:
                try:
                    key_line, _ = doc.lc.key(key)
                except Exception:
                    key_line = None

                if key_line is not None:
                    body_start, body_end, body_indent = _find_block_body_span(
                        lines, key_line
                    )

                    if body_end >= body_start:
                        formatted = format_python_code(
                            value, config, original_indent=body_indent
                        )

                        if _normalize_newlines(formatted) != _normalize_newlines(value):
                            replacements.append(
                                (body_start, body_end, formatted, current_path)
                            )
            elif isinstance(value, (CommentedMap, CommentedSeq)):
                replacements.extend(
                    _collect_text_replacements_for_doc(
                        value, lines, config, current_path
                    )
                )

    elif isinstance(doc, CommentedSeq):
        for idx, item in enumerate(doc):
            replacements.extend(
                _collect_text_replacements_for_doc(
                    item, lines, config, path + (str(idx),)
                )
            )

    return replacements


def _code_key_re(python_keys: set[str]) -> re.Pattern[str]:
    alternatives = "|".join(
        re.escape(key) for key in sorted(python_keys, key=len, reverse=True)
    )
    return re.compile(rf"^([ \t]*)({alternatives}):\s*[|>]", re.MULTILINE)


def _format_jinja_yaml_string(
    yaml_content: str,
    config: FormatterConfig,
) -> tuple[str, bool, str | None]:
    lines = yaml_content.splitlines(keepends=True)
    replacements: list[tuple[int, int, str]] = []
    pattern = _code_key_re(config.python_keys)

    for line_idx, line in enumerate(lines):
        if not pattern.match(line):
            continue

        body_start, body_end, _body_indent = _find_block_body_span(lines, line_idx)
        if body_end < body_start:
            continue

        body = "".join(lines[body_start : body_end + 1])
        if contains_jinja_syntax(body):
            continue

        try:
            formatted = format_python_code(body, config)
        except Exception:
            continue

        if _normalize_newlines(formatted) != _normalize_newlines(body):
            replacements.append((body_start, body_end, formatted))

    if not replacements:
        return yaml_content, False, None

    replacements.sort(key=lambda value: value[0], reverse=True)
    for start, end, new_text in replacements:
        new_lines = new_text.splitlines(keepends=True)
        if end >= start and not lines[end].endswith("\n") and new_lines:
            new_lines[-1] = new_lines[-1].rstrip("\n")
        lines[start : end + 1] = new_lines

    result = "".join(lines)
    return result, result != yaml_content, None


def format_yaml_string(
    yaml_content: str,
    config: FormatterConfig | None = None,
) -> tuple[str, bool, str | None]:
    if config is None:
        config = FormatterConfig()

    original_content = yaml_content
    if config.convert_tabs_to_spaces:
        yaml_content = _convert_tabs_to_spaces(yaml_content)

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    if has_jinja_header(yaml_content):
        result, _changed, _error = _format_jinja_yaml_string(yaml_content, config)
        return result, result != original_content, _error

    try:
        documents = list(yaml.load_all(normalize_yaml_for_parser(yaml_content)))
    except YAMLError as exc:
        return original_content, False, str(exc)

    lines = yaml_content.splitlines(keepends=True)
    all_replacements: list[tuple[int, int, str, tuple[str, ...]]] = []

    for doc in documents:
        if doc is None:
            continue
        all_replacements.extend(_collect_text_replacements_for_doc(doc, lines, config))

    if all_replacements:
        all_replacements.sort(key=lambda value: value[0], reverse=True)
        for start, end, new_text, _path in all_replacements:
            new_lines = new_text.splitlines(keepends=True)
            if end >= start and not lines[end].endswith("\n") and new_lines:
                new_lines[-1] = new_lines[-1].rstrip("\n")
            lines[start : end + 1] = new_lines

    result = "".join(lines)
    return result, result != original_content, None


def format_yaml_file(
    file_path: str | Path,
    config: FormatterConfig | None = None,
    write: bool = True,
) -> tuple[str, bool, str | None]:
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")

    formatted, changed, error = format_yaml_string(content, config)

    if changed and write:
        path.write_text(formatted, encoding="utf-8")

    return formatted, changed, error


def format_text(
    text: str,
    *,
    config: FormatterConfig | None = None,
) -> FormatResult:
    formatted, changed, error = format_yaml_string(text, config=config)
    return FormatResult(text=formatted, changed=changed, error=error)


def format_path(
    path: str | Path,
    *,
    config: FormatterConfig | None = None,
    write: bool = True,
) -> FormatResult:
    formatted, changed, error = format_yaml_file(path, config=config, write=write)
    return FormatResult(text=formatted, changed=changed, error=error)
