from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from difflib import get_close_matches
from itertools import pairwise
from pathlib import Path

from docassemble_lsp.core.completion_registry import format_property_insert_text
from docassemble_lsp.core.completion_rules import get_property_rule
from docassemble_lsp.core.diagnostics import Diagnostic, analyze_text
from docassemble_lsp.core.field_keys import INPUT_TYPE_DATATYPES
from docassemble_lsp.core.field_labels import FieldLabelPlan, plan_multifield_label
from docassemble_lsp.core.jinja import has_jinja_header
from docassemble_lsp.core.messages import MessageCode
from docassemble_lsp.core.question_ids import (
    plan_duplicate_question_ids,
    plan_missing_question_ids,
)
from docassemble_lsp.core.schema import load_schema
from docassemble_lsp.core.validation_config import RuntimeOptions
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_shared import _BLOCK_SCALAR_MARKERS, _document_lines
from docassemble_lsp.core.yesno_shortcuts import plan_yesno_shortcut

logger = logging.getLogger(__name__)

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
class FixRejection:
    code: str
    title: str
    reason: str


@dataclass(frozen=True, slots=True)
class FixValidation:
    accepted: tuple[ResolvedFix, ...] = ()
    rejected: tuple[FixRejection, ...] = ()


@dataclass(frozen=True, slots=True)
class FixResult:
    text: str
    changed: bool
    applied_codes: tuple[str, ...] = ()
    rejected: tuple[FixRejection, ...] = ()


FixProvider = Callable[[str, Diagnostic, int | None], list[ResolvedFix]]


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

_EMPTY_ID_LINE_RE = re.compile(
    r"""^(\s*)(?:-\s+)?id\s*:\s*(?:(?P<quote>["'])(?P=quote))?\s*(?P<comment>#.*)?$""",
    re.IGNORECASE,
)

_DUPLICATE_ID_LINE_RE = re.compile(
    r"""^(\s*)(?P<marker>-\s+)?(?P<key>id)\s*:\s*(?P<value>.*)$""",
    re.IGNORECASE,
)


def _yaml_comment_start(text: str) -> int | None:
    """Return the index where a trailing YAML comment starts, if any."""
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\" and quote == '"':
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or text[index - 1].isspace()):
            return index
    return None


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
            _key_indent, key_name = key_match.groups()
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


def _missing_question_id_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    """W608: insert the planned unique id before the question key."""
    if diagnostic.code != "W608":
        return []

    plan = {entry.line: entry for entry in plan_missing_question_ids(source)}
    target = diagnostic.line
    if target not in plan and preferred_line is not None:
        target = preferred_line + 1
    entry = plan.get(target)
    if entry is None:
        return []

    quoted = json.dumps(entry.generated_id, ensure_ascii=False)
    title = f"Add missing id {quoted}"
    lines = _document_lines(source)

    if entry.id_line is not None:
        # The block already has an empty `id:` key: fill it in rather than
        # inserting a second key, which would be a duplicate YAML key.
        line_index = entry.id_line - 1
        if line_index < 0 or line_index >= len(lines):
            return []
        text = lines[line_index]
        match = _EMPTY_ID_LINE_RE.match(text)
        if match is None:
            return []
        indent = match.group(1)
        comment = match.group("comment")
        replacement = f"{indent}id: {quoted}"
        if comment:
            replacement = f"{replacement} {comment}"
        return [
            ResolvedFix(
                code="W608",
                title=title,
                edit=SourceEdit(
                    start_line=line_index,
                    start_character=0,
                    end_line=line_index,
                    end_character=len(text),
                    new_text=replacement,
                ),
            )
        ]

    line_index = entry.line - 1
    if line_index < 0 or line_index >= len(lines):
        return []
    text = lines[line_index]
    indent = text[: len(text) - len(text.lstrip())]
    return [
        ResolvedFix(
            code="W608",
            title=title,
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=f"{indent}id: {quoted}\n{text}",
            ),
        )
    ]


def _duplicate_block_id_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    """W609: rename a later duplicate id to its planned unique replacement."""
    if diagnostic.code != "W609":
        return []

    plan = {entry.line: entry for entry in plan_duplicate_question_ids(source)}
    target = diagnostic.line
    if target not in plan and preferred_line is not None:
        target = preferred_line + 1
    entry = plan.get(target)
    if entry is None:
        return []

    lines = _document_lines(source)
    line_index = entry.line - 1
    if line_index < 0 or line_index >= len(lines):
        return []
    text = lines[line_index]
    match = _DUPLICATE_ID_LINE_RE.match(text)
    if match is None:
        return []

    indent = match.group(1)
    marker = match.group("marker") or ""
    key = match.group("key")
    value = match.group("value")
    quoted = json.dumps(entry.replacement_id, ensure_ascii=False)
    replacement = f"{indent}{marker}{key}: {quoted}"
    comment_index = _yaml_comment_start(value)
    if comment_index is not None:
        replacement = f"{replacement} {value[comment_index:].rstrip()}"

    return [
        ResolvedFix(
            code="W609",
            title=f"Rename duplicate id to {quoted}",
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=replacement,
            ),
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


_W502_LABEL_TITLE = "Use the question text as this field's label"
_MULTIFIELD_LABEL_SAFE_TARGET_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[[^\]\n]+\])*$"
)


def _needs_block_label(question_text: str) -> bool:
    """Return True when the text must be written as a block label.

    Mako line directives only work at the start of a line, so a label that
    carries them is written as a block scalar that keeps those lines intact.
    Multi-line question text uses a block label too so it stays readable.
    """
    if "\n" in question_text:
        return True
    return any(line.lstrip().startswith("%") for line in question_text.splitlines())


def _label_definition(
    question_text: str, *, content_indent: str, comment: str = ""
) -> str:
    """Return the ``label: ...`` text for *question_text*.

    Block content lines are indented by *content_indent*; callers add the
    leading indentation to the first line themselves. *comment* is appended
    to the header so an existing trailing YAML comment survives the edit.
    """
    if _needs_block_label(question_text):
        keeps_final_newline = question_text.endswith("\n")
        header = f"label: {'|' if keeps_final_newline else '|-'}{comment}"
        body = question_text[:-1] if keeps_final_newline else question_text
        rendered = "\n".join(
            f"{content_indent}{line}" if line else "" for line in body.split("\n")
        )
        return f"{header}\n{rendered}"
    quoted = json.dumps(question_text, ensure_ascii=False)
    return f"label: {quoted}{comment}"


def _field_target_text(target: str) -> str:
    if _MULTIFIELD_LABEL_SAFE_TARGET_RE.match(target):
        return target
    return json.dumps(target, ensure_ascii=False)


def _insert_label_fix(
    plan: FieldLabelPlan, line_index: int, text: str
) -> list[ResolvedFix]:
    """Add a label key in front of an existing ``field`` key."""
    match = re.match(r"^(\s*)(-\s+)?field\s*:", text, re.IGNORECASE)
    if match is None:
        return []
    indent = match.group(1)
    marker = match.group(2) or ""
    content_indent = " " * (len(indent) + len(marker) + 2)
    definition = _label_definition(plan.question_text, content_indent=content_indent)
    if marker:
        rest = text[len(indent) + len(marker) :]
        new_text = f"{indent}{marker}{definition}\n{indent}  {rest}"
    else:
        new_text = f"{indent}{definition}\n{text}"
    return [
        ResolvedFix(
            code="W502",
            title=_W502_LABEL_TITLE,
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=new_text,
            ),
        )
    ]


def _fill_label_fix(
    plan: FieldLabelPlan, line_index: int, text: str
) -> list[ResolvedFix]:
    """Fill a blank explicit ``label`` value in place."""
    match = re.match(r"^(\s*)(-\s+)?label\s*:\s*", text, re.IGNORECASE)
    if match is None:
        return []
    indent = match.group(1)
    marker = match.group(2) or ""
    content_indent = " " * (len(indent) + len(marker) + 2)
    remainder = text[match.end() :]
    comment_index = _yaml_comment_start(remainder)
    if comment_index is not None:
        value_part = remainder[:comment_index]
        comment = f" {remainder[comment_index:].strip()}"
    else:
        value_part = remainder
        comment = ""
    if value_part.strip() not in ("", "''", '""'):
        return []
    definition = _label_definition(
        plan.question_text, content_indent=content_indent, comment=comment
    )
    new_text = f"{indent}{marker}{definition}"
    return [
        ResolvedFix(
            code="W502",
            title=_W502_LABEL_TITLE,
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=new_text,
            ),
        )
    ]


def _convert_no_label_fix(
    plan: FieldLabelPlan, line_index: int, text: str
) -> list[ResolvedFix]:
    """Rewrite the ``no label: variable`` shorthand as ``label`` + ``field``."""
    match = re.match(r"^(\s*)(-\s+)?no\s+label\s*:\s*(.*)$", text, re.IGNORECASE)
    if match is None:
        return []
    indent = match.group(1)
    marker = match.group(2) or ""
    content_indent = " " * (len(indent) + len(marker) + 2)
    remainder = match.group(3)
    comment_index = _yaml_comment_start(remainder)
    comment = ""
    if comment_index is not None:
        comment = f" {remainder[comment_index:].strip()}"
    definition = _label_definition(plan.question_text, content_indent=content_indent)
    target = _field_target_text(plan.field_target or "")
    field_line = f"{indent}{'  ' if marker else ''}field: {target}{comment}"
    new_text = f"{indent}{marker}{definition}\n{field_line}"
    return [
        ResolvedFix(
            code="W502",
            title=_W502_LABEL_TITLE,
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=new_text,
            ),
        )
    ]


def _multifield_label_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    """W502: promote the screen's question text to the first unlabeled field."""
    del preferred_line
    if diagnostic.code != "W502":
        return []

    plan = plan_multifield_label(source, diagnostic.line)
    if plan is None:
        return []

    lines = _document_lines(source)
    line_index = plan.key_line - 1
    if line_index < 0 or line_index >= len(lines):
        return []
    text = lines[line_index]

    if plan.kind == "insert-label":
        return _insert_label_fix(plan, line_index, text)
    if plan.kind == "fill-label":
        return _fill_label_fix(plan, line_index, text)
    if plan.kind == "convert-no-label":
        return _convert_no_label_fix(plan, line_index, text)
    return []


def _yesno_shortcut_fixes(
    source: str, diagnostic: Diagnostic, preferred_line: int | None
) -> list[ResolvedFix]:
    """W510: expand a yes/no shortcut into an explicit single-field screen."""
    del preferred_line
    if diagnostic.code != "W510":
        return []

    plan = plan_yesno_shortcut(source, diagnostic.line)
    if plan is None:
        return []

    lines = _document_lines(source)
    line_index = plan.key_line - 1
    if line_index < 0 or line_index >= len(lines):
        return []
    text = lines[line_index]
    match = _YAML_KEY_RE.match(text)
    if match is None:
        return []

    indent = match.group(1)
    remainder = text[match.end() :]
    comment_index = _yaml_comment_start(remainder)
    comment = ""
    if comment_index is not None:
        comment = remainder[comment_index:].rstrip()
    fields_line = f"{indent}fields:{f' {comment}' if comment else ''}"
    new_text = "\n".join(
        (
            fields_line,
            f"{indent}  - no label: {plan.target}",
            f"{indent}    datatype: {plan.datatype}",
        )
    )
    return [
        ResolvedFix(
            code="W510",
            title=f"Expand '{plan.shortcut}' into an explicit field",
            edit=SourceEdit(
                start_line=line_index,
                start_character=0,
                end_line=line_index,
                end_character=len(text),
                new_text=new_text,
            ),
        )
    ]


_FIX_PROVIDERS: dict[str, FixProvider] = {
    "C102": _field_label_shorthand_fixes,
    "C103": _input_type_datatype_fixes,
    "E301": _unknown_key_fixes,
    "E414": _field_label_without_target_fixes,
    "E415": _field_target_without_label_fixes,
    "W502": _multifield_label_fixes,
    "W510": _yesno_shortcut_fixes,
    "W608": _missing_question_id_fixes,
    "W609": _duplicate_block_id_fixes,
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
    for previous, current in pairwise(edits_with_offsets):
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


def _finding_counts(diagnostics: Sequence[Diagnostic]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for diagnostic in diagnostics:
        key = diagnostic.code or "<uncoded>"
        counts[key] = counts.get(key, 0) + 1
    return counts


_PARSE_FAILURE_CODES = frozenset(
    {MessageCode.YAML_DUPLICATE_KEY, MessageCode.YAML_PARSE_ERROR}
)


def _parse_failure_counts(
    text: str,
    *,
    path: str,
    runtime_options: RuntimeOptions | None,
    workspace_index: WorkspaceIndex | None,
) -> dict[str, int]:
    """Return parse-failure counts in *text*, even when the run ignores them.

    Parsing is a precondition for safe rewriting, so ``ignore_codes`` must not
    be able to hide a candidate that broke the document.
    """
    if runtime_options is None or not runtime_options.ignore_codes:
        return {}
    parse_options = replace(runtime_options, ignore_codes=frozenset())
    counts: dict[str, int] = {}
    for diagnostic in analyze_text(
        text,
        path=path,
        runtime_options=parse_options,
        workspace_index=workspace_index,
    ):
        if diagnostic.code in _PARSE_FAILURE_CODES:
            counts[diagnostic.code] = counts.get(diagnostic.code, 0) + 1
    return counts


def _candidate_assessment(
    candidate_text: str,
    baseline_counts: dict[str, int],
    baseline_parse_counts: dict[str, int],
    *,
    path: str,
    runtime_options: RuntimeOptions | None,
    workspace_index: WorkspaceIndex | None,
) -> tuple[dict[str, int], str | None]:
    """Return the candidate's finding counts and the reason to reject it."""
    candidate_counts = _finding_counts(
        analyze_text(
            candidate_text,
            path=path,
            runtime_options=runtime_options,
            workspace_index=workspace_index,
        )
    )
    new_codes = sorted(
        code
        for code, count in candidate_counts.items()
        if count > baseline_counts.get(code, 0)
    )
    if new_codes:
        return candidate_counts, f"introduces new finding(s): {', '.join(new_codes)}"
    candidate_parse_counts = _parse_failure_counts(
        candidate_text,
        path=path,
        runtime_options=runtime_options,
        workspace_index=workspace_index,
    )
    new_parse_failures = sorted(
        code
        for code, count in candidate_parse_counts.items()
        if count > baseline_parse_counts.get(code, 0)
    )
    if new_parse_failures:
        return (
            candidate_counts,
            f"introduces parse failure(s): {', '.join(new_parse_failures)}",
        )
    return candidate_counts, None


def validate_fix_candidates(
    source: str,
    fixes: Sequence[ResolvedFix],
    *,
    diagnostics: Sequence[Diagnostic] | None = None,
    path: str = "<memory>",
    runtime_options: RuntimeOptions | None = None,
    workspace_index: WorkspaceIndex | None = None,
) -> FixValidation:
    """Re-check fix candidates against the source they would rewrite.

    A candidate is accepted only when it still parses, introduces no new
    finding of any code, and strictly reduces the finding it was made for.
    Before and after finding counts are compared per code with the same
    runtime options and workspace context as the original run. The batch of
    accepted fixes is re-checked as a whole before it is returned, and
    Jinja-rendered files are never rewritten automatically.
    """
    if not fixes:
        return FixValidation()

    if has_jinja_header(source):
        return FixValidation(
            rejected=tuple(
                FixRejection(
                    code=fix.code,
                    title=fix.title,
                    reason="Jinja-rendered files are not rewritten automatically",
                )
                for fix in fixes
            )
        )

    if diagnostics is None:
        diagnostics = analyze_text(
            source,
            path=path,
            runtime_options=runtime_options,
            workspace_index=workspace_index,
        )
    baseline_counts = _finding_counts(diagnostics)
    baseline_parse_counts = _parse_failure_counts(
        source,
        path=path,
        runtime_options=runtime_options,
        workspace_index=workspace_index,
    )

    accepted: list[ResolvedFix] = []
    rejected: list[FixRejection] = []
    for fix in fixes:
        candidate = apply_resolved_fixes(source, [fix])
        if not candidate.changed:
            rejected.append(
                FixRejection(fix.code, fix.title, "candidate produces no change")
            )
            continue

        candidate_counts, reason = _candidate_assessment(
            candidate.text,
            baseline_counts,
            baseline_parse_counts,
            path=path,
            runtime_options=runtime_options,
            workspace_index=workspace_index,
        )
        if reason is None and candidate_counts.get(fix.code, 0) >= baseline_counts.get(
            fix.code, 0
        ):
            reason = f"does not reduce '{fix.code}' findings"
        if reason is not None:
            rejected.append(FixRejection(fix.code, fix.title, reason))
            continue
        accepted.append(fix)

    if len(accepted) > 1:
        try:
            combined = apply_resolved_fixes(source, list(accepted))
        except ValueError:
            combined_reason = "overlapping candidate edits"
        else:
            _, combined_reason = _candidate_assessment(
                combined.text,
                baseline_counts,
                baseline_parse_counts,
                path=path,
                runtime_options=runtime_options,
                workspace_index=workspace_index,
            )
        if combined_reason is not None:
            rejected.extend(
                FixRejection(fix.code, fix.title, combined_reason) for fix in accepted
            )
            accepted = []

    return FixValidation(accepted=tuple(accepted), rejected=tuple(rejected))


def fix_text(
    source: str,
    *,
    path: str = "<memory>",
    runtime_options: RuntimeOptions | None = None,
    workspace_index: WorkspaceIndex | None = None,
) -> FixResult:
    diagnostics = analyze_text(
        source,
        path=path,
        runtime_options=runtime_options,
        workspace_index=workspace_index,
    )
    cli_fixes = [
        fix
        for fix in resolve_diagnostic_fixes(source, diagnostics)
        if fix.supports_cli_fix
    ]
    validation = validate_fix_candidates(
        source,
        cli_fixes,
        diagnostics=diagnostics,
        path=path,
        runtime_options=runtime_options,
        workspace_index=workspace_index,
    )
    for rejection in validation.rejected:
        logger.info(
            "Rejected fix %s (%s) for %s: %s",
            rejection.code,
            rejection.title,
            path,
            rejection.reason,
        )
    if not validation.accepted:
        return FixResult(text=source, changed=False, rejected=validation.rejected)

    applied = apply_resolved_fixes(source, list(validation.accepted))
    return FixResult(
        text=applied.text,
        changed=applied.changed,
        applied_codes=applied.applied_codes,
        rejected=validation.rejected,
    )


def fix_path(
    path: str | Path,
    *,
    runtime_options: RuntimeOptions | None = None,
    workspace_index: WorkspaceIndex | None = None,
) -> FixResult:
    file_path = Path(path)
    original = file_path.read_text(encoding="utf-8")
    result = fix_text(
        original,
        path=str(file_path),
        runtime_options=runtime_options,
        workspace_index=workspace_index,
    )
    if result.changed:
        file_path.write_text(result.text, encoding="utf-8")
    return result
