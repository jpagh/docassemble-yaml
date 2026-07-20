from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import Callable

from docassemble_lsp.core.completion_registry import format_property_insert_text
from docassemble_lsp.core.completion_rules import get_property_rule
from docassemble_lsp.core.diagnostics import Diagnostic, analyze_text
from docassemble_lsp.core.field_keys import INPUT_TYPE_DATATYPES
from docassemble_lsp.core.schema import load_schema
from docassemble_lsp.core.validation_config import RuntimeOptions
from docassemble_lsp.core.yaml_shared import _BLOCK_SCALAR_MARKERS

_YAML_KEY_RE = re.compile(r"^(\s*)(?:-\s*)?([^:#][^:]*?)\s*:")
_FIELD_LABEL_SHORTHAND_RE = re.compile(r"^(\s*)-\s*([^:]+?)\s*:\s*(.*?)\s*(#.*)?$")
_INPUT_TYPE_DATATYPE_RE = re.compile(
    r"^(\s*)datatype(\s*:\s*)("
    + "|".join(sorted(INPUT_TYPE_DATATYPES))
    + r")(\s*(?:#.*)?)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SourceEdit:
    start_line: int
    start_character: int
    end_line: int
    end_character: int
    new_text: str


@dataclass(frozen=True, slots=True)
class ResolvedFix:
    code: str
    title: str
    edit: SourceEdit
    supports_fix_all: bool = True
    supports_cli_fix: bool = True


@dataclass(frozen=True, slots=True)
class FixResult:
    text: str
    changed: bool
    applied_codes: tuple[str, ...] = ()


FixProvider = Callable[[str, Diagnostic, int | None], list[ResolvedFix]]


def _document_lines(source: str) -> list[str]:
    return source.splitlines() or [""]


def _line_key_range(source: str, line: int) -> tuple[str, int, int] | None:
    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]
    match = _YAML_KEY_RE.match(text)
    if match is None:
        return None
    return (match.group(2).strip(), match.start(2), match.end(2))


def _suggest_known_key_replacement(key_name: str) -> str | None:
    schema = load_schema()
    known_keys = sorted(set(schema.all_known_properties) | set(schema.top_level))
    if key_name in known_keys:
        return None
    matches = get_close_matches(key_name, known_keys, n=1, cutoff=0.75)
    if not matches:
        return None
    return matches[0]


def _field_label_shorthand_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    del preferred_line
    if diagnostic.code != "C102":
        return []

    lines = _document_lines(source)
    line_index = min(max(diagnostic.line - 1, 0), len(lines) - 1)
    text = lines[line_index]
    match = _FIELD_LABEL_SHORTHAND_RE.match(text)
    if match is None:
        return []

    indent, label, field_name, comment = match.groups()
    stripped_field_name = field_name.strip()
    if not stripped_field_name:
        return []

    continuation_indent = f"{indent}  "
    replacement = f"{indent}- label: {label.strip()}\n{continuation_indent}field: {stripped_field_name}{comment or ''}"
    return [
        ResolvedFix(
            code="C102",
            title="Convert to explicit label/field keys",
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=replacement,
            ),
            supports_fix_all=True,
            supports_cli_fix=True,
        )
    ]


def _unknown_key_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    if diagnostic.code != "E301":
        return []

    line_index = (
        preferred_line if preferred_line is not None else max(diagnostic.line - 1, 0)
    )
    key_range = _line_key_range(source, line_index)
    if key_range is None:
        return []

    key_name, start_character, end_character = key_range
    replacement = _suggest_known_key_replacement(key_name)
    if replacement is None:
        return []

    return [
        ResolvedFix(
            code="E301",
            title=f"Change '{key_name}' to '{replacement}'",
            edit=SourceEdit(
                start_line=line_index,
                start_character=start_character,
                end_line=line_index,
                end_character=end_character,
                new_text=replacement,
            ),
            supports_fix_all=False,
            supports_cli_fix=False,
        )
    ]


def _input_type_datatype_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    del preferred_line
    if diagnostic.code != "C103":
        return []

    lines = _document_lines(source)
    line_index = min(max(diagnostic.line - 1, 0), len(lines) - 1)
    text = lines[line_index]
    match = _INPUT_TYPE_DATATYPE_RE.match(text)
    if match is None:
        return []

    indent, separator, value, suffix = match.groups()
    replacement = f"{indent}input type{separator}{value}{suffix or ''}"
    return [
        ResolvedFix(
            code="C103",
            title=f"Use input type: {value}",
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=replacement,
            ),
            supports_fix_all=True,
            supports_cli_fix=True,
        )
    ]


_FIELD_ITEM_LABEL_RE = re.compile(r"^(\s*)(?:-\s+)?label(?=\s*:)")


def _field_label_without_target_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    """E414: 'label' key present without a corresponding 'field' key."""
    del preferred_line
    if diagnostic.code != "E414":
        return []

    lines = _document_lines(source)
    line_index = min(max(diagnostic.line - 1, 0), len(lines) - 1)
    text = lines[line_index]

    # Case 1: line has a `label:` key — add `field:` on the next line.
    label_match = _FIELD_ITEM_LABEL_RE.match(text)
    if label_match:
        indent = label_match.group(1)
        # If the line has a `- ` list marker (e.g. "- label: ..."), the new key
        # needs to be indented one level deeper to sit inside the list item.
        field_indent = indent + "  " if text[len(indent) :].startswith("- ") else indent
        replacement = f"{text}\n{field_indent}field: "
        return [
            ResolvedFix(
                code="E414",
                title="Add missing 'field' key",
                edit=SourceEdit(
                    start_line=line_index,
                    start_character=0,
                    end_line=line_index,
                    end_character=len(text),
                    new_text=replacement,
                ),
                supports_fix_all=False,
                supports_cli_fix=False,
            )
        ]

    # Case 2: bare text item with no label/field at all (line 1784 path).
    bare_match = re.match(r"^(\s*)-\s+(.*?)\s*$", text)
    if bare_match:
        indent, content = bare_match.groups()
        replacement = f"{indent}- field: {content}"
        return [
            ResolvedFix(
                code="E414",
                title="Convert to 'field' key",
                edit=SourceEdit(
                    start_line=line_index,
                    start_character=0,
                    end_line=line_index,
                    end_character=len(text),
                    new_text=replacement,
                ),
                supports_fix_all=False,
                supports_cli_fix=False,
            )
        ]

    return []


_FIELD_ITEM_FIELD_RE = re.compile(r"^(\s*)(?:-\s+)?field(?=\s*:)")


def _field_target_without_label_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    """E415: 'field' key present without a corresponding 'label' key."""
    del preferred_line
    if diagnostic.code != "E415":
        return []

    lines = _document_lines(source)
    line_index = min(max(diagnostic.line - 1, 0), len(lines) - 1)
    text = lines[line_index]

    field_match = _FIELD_ITEM_FIELD_RE.match(text)
    if not field_match:
        return []

    indent = field_match.group(1)
    # If the line has a `- ` list marker (e.g. "- field: ..."), the new key
    # needs to be indented one level deeper to sit inside the list item.
    label_indent = indent + "  " if text[len(indent) :].startswith("- ") else indent
    replacement = f"{text}\n{label_indent}label: "
    return [
        ResolvedFix(
            code="E415",
            title="Add missing 'label' key",
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=replacement,
            ),
            supports_fix_all=False,
            supports_cli_fix=False,
        )
    ]


_TABLE_REQUIRED_KEYS = frozenset({"table", "rows", "columns"})


def _table_missing_keys_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    """E921: table block missing one or more of table/rows/columns."""
    del preferred_line
    if diagnostic.code != "E921":
        return []

    lines = _document_lines(source)
    line_index = min(max(diagnostic.line - 1, 0), len(lines) - 1)
    text = lines[line_index]

    # Determine the indent of the key at the diagnostic line.
    indent_match = re.match(r"^(\s*)", text)
    indent = indent_match.group(1) if indent_match else ""

    # Collect keys present in the block (same or deeper indent).
    present_keys: set[str] = set()
    for line in lines:
        key_match = re.match(r"^(\s*)(\S+?)\s*:", line)
        if key_match:
            key_indent, key_name = key_match.groups()
            if key_name in _TABLE_REQUIRED_KEYS:
                present_keys.add(key_name)

    missing_keys = sorted(_TABLE_REQUIRED_KEYS - present_keys)
    if not missing_keys:
        return []

    # Build the text to append.
    additions = "\n".join(f"{indent}{key}: " for key in missing_keys)
    # Insert extra newline if the last line of the block is at the same indent
    replacement = f"{text}\n{additions}"

    return [
        ResolvedFix(
            code="E921",
            title=f"Add missing table keys: {', '.join(missing_keys)}",
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=replacement,
            ),
            supports_fix_all=False,
            supports_cli_fix=False,
        )
    ]


@dataclass(frozen=True, slots=True)
class _FieldItemBoundary:
    last_line: int
    text: str
    content_indent: str


def _find_field_item_bounds(
    source: str, diagnostic_line: int
) -> _FieldItemBoundary | None:
    """Find the last content line and indent for the field item containing *diagnostic_line* (1-indexed)."""
    lines = _document_lines(source)
    line_index = min(max(diagnostic_line - 1, 0), len(lines) - 1)

    start = line_index
    while start >= 0:
        if lines[start].lstrip().startswith("- "):
            break
        start -= 1
    if start < 0:
        return None

    list_indent = len(lines[start]) - len(lines[start].lstrip())
    content_indent = " " * (list_indent + 2)

    end = start + 1
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            end += 1
            continue
        indent = len(line) - len(line.lstrip())
        if line.lstrip().startswith("- ") and indent == list_indent:
            break
        if indent <= list_indent:
            break
        end += 1

    last_line = end - 1
    return _FieldItemBoundary(
        last_line=last_line,
        text=lines[last_line],
        content_indent=content_indent,
    )


def _missing_choices_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    del preferred_line
    if diagnostic.code != "E419":
        return []

    bounds = _find_field_item_bounds(source, diagnostic.line)
    if bounds is None:
        return []

    choices_rule = get_property_rule("fields_item", "choices")
    code_rule = get_property_rule("fields_item", "code")
    if choices_rule is None or code_rule is None:
        return []
    choices_insert = format_property_insert_text(
        "choices", choices_rule, indent=bounds.content_indent
    )
    code_insert = format_property_insert_text(
        "code", code_rule, indent=bounds.content_indent
    )

    return [
        ResolvedFix(
            code="E419",
            title="Add 'choices' key",
            edit=SourceEdit(
                start_line=bounds.last_line,
                start_character=0,
                end_line=bounds.last_line,
                end_character=len(bounds.text),
                new_text=f"{bounds.text}\n{choices_insert}",
            ),
            supports_fix_all=False,
            supports_cli_fix=False,
        ),
        ResolvedFix(
            code="E419",
            title="Add 'code' key",
            edit=SourceEdit(
                start_line=bounds.last_line,
                start_character=0,
                end_line=bounds.last_line,
                end_character=len(bounds.text),
                new_text=f"{bounds.text}\n{code_insert}",
            ),
            supports_fix_all=False,
            supports_cli_fix=False,
        ),
    ]


def _ajax_missing_action_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    del preferred_line
    if diagnostic.code != "E420":
        return []

    bounds = _find_field_item_bounds(source, diagnostic.line)
    if bounds is None:
        return []

    action_rule = get_property_rule("fields_item", "action")
    if action_rule is None:
        return []
    action_insert = format_property_insert_text(
        "action", action_rule, indent=bounds.content_indent
    )

    return [
        ResolvedFix(
            code="E420",
            title="Add 'action' key",
            edit=SourceEdit(
                start_line=bounds.last_line,
                start_character=0,
                end_line=bounds.last_line,
                end_character=len(bounds.text),
                new_text=f"{bounds.text}\n{action_insert}",
            ),
            supports_fix_all=False,
            supports_cli_fix=False,
        ),
    ]


def _def_mako_missing_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    """E934: def/mako block missing one of the paired keys."""
    del preferred_line
    if diagnostic.code != "E934":
        return []

    lines = _document_lines(source)
    line_index = min(max(diagnostic.line - 1, 0), len(lines) - 1)
    text = lines[line_index]

    indent_match = re.match(r"^(\s*)", text)
    indent = indent_match.group(1) if indent_match else ""

    has_def = False
    has_mako = False
    for line in lines:
        key_match = re.match(r"^(\s*)(\S+?)\s*:", line)
        if key_match:
            key_name = key_match.group(2)
            has_def = has_def or key_name == "def"
            has_mako = has_mako or key_name == "mako"

    fixes: list[ResolvedFix] = []
    if has_def and not has_mako:
        mako_rule = get_property_rule("top_level", "mako")
        if mako_rule is not None:
            mako_insert = format_property_insert_text("mako", mako_rule, indent=indent)
            fixes.append(
                ResolvedFix(
                    code="E934",
                    title="Add 'mako' key",
                    edit=SourceEdit(
                        start_line=line_index,
                        start_character=0,
                        end_line=line_index,
                        end_character=len(text),
                        new_text=f"{text}\n{mako_insert}",
                    ),
                    supports_fix_all=False,
                    supports_cli_fix=False,
                )
            )
    if has_mako and not has_def:
        def_insert = f"{indent}def: name_here"
        if any(text.strip().endswith(m) for m in _BLOCK_SCALAR_MARKERS):
            new_text = f"{def_insert}\n{text}"
        else:
            new_text = f"{text}\n{def_insert}"
        fixes.append(
            ResolvedFix(
                code="E934",
                title="Add 'def' key",
                edit=SourceEdit(
                    start_line=line_index,
                    start_character=0,
                    end_line=line_index,
                    end_character=len(text),
                    new_text=new_text,
                ),
                supports_fix_all=False,
                supports_cli_fix=False,
            )
        )
    return fixes


def _cross_doc_missing_file_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    del preferred_line
    if diagnostic.code != "W604":
        return []
    lines = _document_lines(source)
    line_index = min(max(diagnostic.line - 1, 0), len(lines) - 1)
    if line_index == len(lines) - 1:
        end_line, end_char = line_index, len(lines[line_index])
    else:
        end_line, end_char = line_index + 1, 0
    return [
        ResolvedFix(
            code="W604",
            title="Remove missing file/module reference",
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=end_line,
                end_character=end_char,
                new_text="",
            ),
            supports_fix_all=False,
            supports_cli_fix=False,
        )
    ]


_FIX_PROVIDERS: dict[str, FixProvider] = {
    "C102": _field_label_shorthand_fixes,
    "C103": _input_type_datatype_fixes,
    "E301": _unknown_key_fixes,
    "E414": _field_label_without_target_fixes,
    "E415": _field_target_without_label_fixes,
    "E921": _table_missing_keys_fixes,
    "E419": _missing_choices_fixes,
    "E420": _ajax_missing_action_fixes,
    "E934": _def_mako_missing_fixes,
    "W604": _cross_doc_missing_file_fixes,
    # W605 (CROSS_DOC_MISSING_TEMPLATE) intentionally omitted: template
    # path resolution depends on the package structure and templates_dir,
    # which a single-file fixer cannot reliably infer.
}


def resolve_diagnostic_fixes(
    source: str,
    diagnostics: list[Diagnostic],
    *,
    preferred_line: int | None = None,
) -> list[ResolvedFix]:
    resolved: list[ResolvedFix] = []
    for diagnostic in diagnostics:
        if diagnostic.code is None:
            continue
        provider = _FIX_PROVIDERS.get(diagnostic.code)
        if provider is None:
            continue
        resolved.extend(provider(source, diagnostic, preferred_line))

    deduped: list[ResolvedFix] = []
    seen: set[tuple[object, ...]] = set()
    for fix in resolved:
        key = (
            fix.code,
            fix.title,
            fix.edit.start_line,
            fix.edit.start_character,
            fix.edit.end_line,
            fix.edit.end_character,
            fix.edit.new_text,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fix)
    return deduped


def resolve_fix_all_fixes(
    source: str, diagnostics: list[Diagnostic]
) -> list[ResolvedFix]:
    return [
        fix
        for fix in resolve_diagnostic_fixes(source, diagnostics)
        if fix.supports_fix_all
    ]


def _line_start_offsets(source: str) -> list[int]:
    lines = source.splitlines(keepends=True)
    if not lines:
        return [0]
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)
    return offsets


def _position_to_offset(source: str, line: int, character: int) -> int:
    lines = _document_lines(source)
    bounded_line = min(max(line, 0), len(lines) - 1)
    bounded_character = min(max(character, 0), len(lines[bounded_line]))
    return _line_start_offsets(source)[bounded_line] + bounded_character


def apply_resolved_fixes(source: str, fixes: list[ResolvedFix]) -> FixResult:
    if not fixes:
        return FixResult(text=source, changed=False)

    edits_with_offsets = []
    for fix in fixes:
        start_offset = _position_to_offset(
            source, fix.edit.start_line, fix.edit.start_character
        )
        end_offset = _position_to_offset(
            source, fix.edit.end_line, fix.edit.end_character
        )
        edits_with_offsets.append((start_offset, end_offset, fix))

    edits_with_offsets.sort(key=lambda item: (item[0], item[1]))
    for previous, current in zip(edits_with_offsets, edits_with_offsets[1:]):
        if previous[1] > current[0]:
            raise ValueError("Overlapping fixes are not supported")

    updated = source
    for start_offset, end_offset, fix in reversed(edits_with_offsets):
        updated = updated[:start_offset] + fix.edit.new_text + updated[end_offset:]

    return FixResult(
        text=updated,
        changed=updated != source,
        applied_codes=tuple(fix.code for _, _, fix in edits_with_offsets),
    )


def fix_text(
    source: str,
    *,
    path: str = "<memory>",
    runtime_options: RuntimeOptions | None = None,
) -> FixResult:
    diagnostics = analyze_text(source, path=path, runtime_options=runtime_options)
    cli_fixes = [
        fix
        for fix in resolve_diagnostic_fixes(source, diagnostics)
        if fix.supports_cli_fix
    ]
    return apply_resolved_fixes(source, cli_fixes)


def fix_path(
    path: str | Path,
    *,
    runtime_options: RuntimeOptions | None = None,
) -> FixResult:
    file_path = Path(path)
    original = file_path.read_text(encoding="utf-8")
    result = fix_text(
        original,
        path=str(file_path),
        runtime_options=runtime_options,
    )
    if result.changed:
        file_path.write_text(result.text, encoding="utf-8")
    return result
