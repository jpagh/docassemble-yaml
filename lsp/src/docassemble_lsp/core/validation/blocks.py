"""Block-level definitions and detection.

- Data tables: ``big_dict``, ``types_of_blocks``, ``all_dict_keys``
- Top-level key checks (E301-E303)
- Directive classes for type validation (E428-E458)
- Shared helpers for block analysis
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from difflib import SequenceMatcher
from typing import Any, Optional

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import MarkedYAMLError

from docassemble_lsp.core.line_helpers import (
    _is_internal_metadata_key,
    _lc_key_line,
    _lc_line,
    _relative_value_line,
    _safe_ast_parse,
)
from docassemble_lsp.core.messages import (
    MessageCode,
    format_message,
    is_experimental_code,
)
from docassemble_lsp.core.validation.fields import (
    _CONDITIONAL_MODIFIERS,
    _HIDE_STYLE_MODIFIERS,
    _IDENTIFIER_RE,
    _JS_VAL_RE,
    _SIMPLE_IDENTIFIER_RE,
    DAFields,
    DAPythonVar,
    MakoMarkdownText,
    MakoText,
    ObjectsAttrType,
    PythonText,
    ShowIf,
    ValidationCode,
)
from docassemble_lsp.core.validation.attachments import AttachmentBlockDirective
from docassemble_lsp.core.validation.review import ReviewBlockDirective
from docassemble_lsp.core.validation.lists import (
    ActionButtonsDirective,
    AllowedToSetDirective,
    AutoTermsDirective,
    DependsOnDirective,
    EventDirective,
    FeaturesDirective,
    IfDirective,
    ImportsDirective,
    IncludeDirective,
    MetadataDirective,
    ModulesDirective,
    NeedDirective,
    OnChangeDirective,
    ProgressDirective,
    PythonBool,
    ReconsiderDirective,
    RequireDirective,
    RoleDirective,
    SetsDirective,
    SupersedesDirective,
    TermsDirective,
    TranslationsDirective,
    UndefineDirective,
    YAMLStr,
)
from docassemble_lsp.core.validation.table import TableBlockDirective
from docassemble_lsp.core.validation_config import YAMLError
from docassemble_lsp.core.yaml_parsing import (
    DOCUMENT_MATCH,
    normalize_yaml_document_for_parser,
)

# YAML error line detection — used when mapping error positions
_YAML_ERROR_LINE_RE = re.compile(r"line (\d+), column \d+")
_YAML_ERROR_TRAILING_LINE_RE = re.compile(r"\(line: (\d+)\)")


def _yaml_error(
    *,
    code: str,
    line_number: int,
    file_name: str,
    err_str: str | None = None,
    **kwargs: Any,
) -> YAMLError:
    return YAMLError(
        err_str=err_str if err_str is not None else format_message(code, **kwargs),
        line_number=line_number,
        file_name=file_name,
        experimental=is_experimental_code(code),
        code=code,
    )


def _map_rendered_lines_to_source_lines(
    source_text: str,
    rendered_text: str,
    *,
    source_start_line: int = 1,
) -> dict[int, int]:
    """Best-effort mapping from rendered line numbers back to source lines."""
    source_lines = source_text.splitlines()
    rendered_lines = rendered_text.splitlines()

    if not rendered_lines:
        return {}
    if not source_lines:
        return {line_no: source_start_line for line_no in range(1, len(rendered_lines) + 1)}

    line_map: dict[int, int] = {}
    matcher = SequenceMatcher(a=source_lines, b=rendered_lines, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(j2 - j1):
                line_map[j1 + offset + 1] = source_start_line + i1 + offset
            continue

        if tag == "replace":
            unmatched_source_by_text: dict[str, list[int]] = {}
            for source_index in range(i1, i2):
                unmatched_source_by_text.setdefault(source_lines[source_index], []).append(source_index)
            for rendered_index in range(j1, j2):
                candidates = unmatched_source_by_text.get(rendered_lines[rendered_index])
                if candidates:
                    line_map[rendered_index + 1] = source_start_line + candidates.pop(0)

    previous_line: int | None = None
    next_known_for_line: dict[int, int] = {}
    next_line: int | None = None
    for rendered_line in range(len(rendered_lines), 0, -1):
        if rendered_line in line_map:
            next_line = line_map[rendered_line]
        if next_line is not None:
            next_known_for_line[rendered_line] = next_line

    for rendered_line in range(1, len(rendered_lines) + 1):
        mapped_line = line_map.get(rendered_line)
        if mapped_line is not None:
            previous_line = mapped_line
            continue

        next_line = next_known_for_line.get(rendered_line)
        if previous_line is not None and next_line is not None:
            line_map[rendered_line] = previous_line
        elif previous_line is not None:
            line_map[rendered_line] = previous_line
        elif next_line is not None:
            line_map[rendered_line] = next_line
        else:
            line_map[rendered_line] = source_start_line

    return line_map


def _extract_yaml_parse_problem_line(err_str: str) -> int | None:
    match = _YAML_ERROR_LINE_RE.search(err_str)
    if match is None:
        return None
    return int(match.group(1))


def _find_top_level_key_line(source_code: str, key: str) -> int | None:
    key_re = re.compile(rf"^{re.escape(key)}\s*:", re.MULTILINE)
    match = key_re.search(source_code)
    if match is None:
        return None
    return source_code.count("\n", 0, match.start()) + 1


def _rewrite_yaml_parse_error_lines(
    err_str: str,
    *,
    old_line: int,
    new_line: int,
) -> str:
    updated = _YAML_ERROR_LINE_RE.sub(
        lambda match: match.group(0).replace(str(old_line), str(new_line), 1),
        err_str,
        count=1,
    )
    return _YAML_ERROR_TRAILING_LINE_RE.sub(f"(line: {new_line})", updated)


def _format_yaml_parse_error(err: MarkedYAMLError) -> str:
    context = (getattr(err, "context", None) or "").strip()
    problem = (getattr(err, "problem", None) or "").strip()

    if context and problem:
        message = f"{context}: {problem}"
    elif problem:
        message = problem
    elif context:
        message = context
    else:
        message = str(err).strip().splitlines()[0]

    snippet_mark = getattr(err, "context_mark", None) or getattr(err, "problem_mark", None)
    if snippet_mark is None:
        return message

    snippet = snippet_mark.get_snippet(indent=2, max_length=79).rstrip()
    snippet = _YAML_ERROR_TRAILING_LINE_RE.sub("", snippet).rstrip()
    if not snippet:
        return message
    return f"{message}\n{snippet}"


def _format_missing_jinja_header_error(source_code: str, *, line_number: int) -> str | None:
    lines = source_code.splitlines()
    if not (1 <= line_number <= len(lines)):
        return None

    offending_line = lines[line_number - 1]
    stripped = offending_line.lstrip()
    if not stripped.startswith(("{%", "{{", "{#")):
        return None

    indent = len(offending_line) - len(stripped)
    caret = " " * (2 + indent) + "^"
    return (
        "Jinja syntax detected without the required '# use jinja' header. "
        "Add '# use jinja' on the first line to enable Jinja preprocessing.\n"
        f"  {offending_line}\n"
        f"{caret}"
    )


# Type validators for each known YAML key.
# Keys with ``"type"`` point to a validator class; those without are deferred.
big_dict: dict[str, dict[str, Any]] = {
    "question": {
        "type": MakoMarkdownText,
    },
    "subquestion": {
        "type": MakoMarkdownText,
    },
    "mandatory": {"type": PythonBool},
    "code": {"type": PythonText},
    "objects": {
        "type": ObjectsAttrType,
    },
    "id": {
        "type": YAMLStr,
    },
    "ga id": {
        "type": YAMLStr,
    },
    "segment id": {
        "type": YAMLStr,
    },
    "features": {"type": FeaturesDirective},
    "terms": {"type": TermsDirective},
    "auto terms": {"type": AutoTermsDirective},
    "help": {},
    "fields": {"type": DAFields},
    "buttons": {},
    "field": {"type": DAPythonVar},
    "template": {},
    "content": {},
    "reconsider": {"type": ReconsiderDirective},
    "depends on": {"type": DependsOnDirective},
    "need": {"type": NeedDirective},
    "attachment": {"type": AttachmentBlockDirective},
    "attachments": {"type": AttachmentBlockDirective},
    "review": {"type": ReviewBlockDirective},
    "table": {"type": TableBlockDirective},
    "rows": {},
    "columns": {},
    "allow reordering": {},
    "delete buttons": {},
    "validation code": {
        "type": ValidationCode,
    },
    "translations": {"type": TranslationsDirective},
    "include": {"type": IncludeDirective},
    "default screen parts": {},
    "metadata": {"type": MetadataDirective},
    "modules": {"type": ModulesDirective},
    "imports": {"type": ImportsDirective},
    "sections": {},
    "interview help": {},
    "def": {
        "type": DAPythonVar,
    },
    "mako": {
        "type": MakoText,
    },
    "usedefs": {},
    "default role": {},
    "default language": {"type": YAMLStr},
    "default validation messages": {},
    "machine learning storage": {},
    "scan for variables": {"type": PythonBool},
    "show if": {
        "type": ShowIf,
    },
    "if": {"type": IfDirective},
    "sets": {"type": SetsDirective},
    "only sets": {"type": SetsDirective},
    "initial": {},
    "event": {"type": EventDirective},
    "comment": {"type": YAMLStr},
    "generic object": {"type": DAPythonVar},
    "variable name": {"type": YAMLStr},
    "data from code": {},
    "back button label": {},
    "continue button label": {
        "type": YAMLStr,
    },
    "decoration": {},
    "yesno": {"type": DAPythonVar},
    "noyes": {"type": DAPythonVar},
    "yesnomaybe": {"type": DAPythonVar},
    "noyesmaybe": {"type": DAPythonVar},
    "reset": {},
    "on change": {"type": OnChangeDirective},
    "require": {"type": RequireDirective},
    "action buttons": {"type": ActionButtonsDirective},
    "image sets": {},
    "images": {},
    "continue button field": {
        "type": DAPythonVar,
    },
    "disable others": {},
    "order": {},
    "undefine": {"type": UndefineDirective},
    "supersedes": {"type": SupersedesDirective},
    "role": {"type": RoleDirective},
    "allowed to set": {"type": AllowedToSetDirective},
    "progress": {"type": ProgressDirective},
    "language": {"type": YAMLStr},
    "section": {"type": YAMLStr},
}

# Block type metadata: which keys are exclusive, what partners/allowed_attrs they have.
types_of_blocks: dict[str, dict[str, Any]] = {
    "include": {
        "exclusive": True,
        "allowed_attrs": ["include"],
    },
    "features": {
        "exclusive": True,
        "allowed_attrs": [
            "features",
        ],
    },
    "objects": {
        "exclusive": True,
        "allowed_attrs": [
            "objects",
        ],
    },
    "objects from file": {
        "exclusive": True,
        "allowed_attrs": [
            "objects from file",
            "use objects",
        ],
    },
    "sections": {
        "exclusive": True,
        "allowed_attrs": [
            "sections",
        ],
    },
    "imports": {
        "exclusive": True,
        "allowed_attrs": [
            "imports",
        ],
    },
    "order": {
        "exclusive": True,
        "allowed_attrs": ["order"],
    },
    "attachment": {
        "exclusive": True,
        "partners": ["question"],
    },
    "attachments": {
        "exclusive": True,
        "partners": ["question"],
    },
    "template": {
        "exclusive": True,
        "allowed_attrs": [
            "template",
            "content",
            "language",
            "subject",
            "generic object",
            "content file",
            "reconsider",
        ],
        "partners": ["terms"],
    },
    "table": {
        "exclusive": True,
        "allowed_attrs": {
            "sort key",
            "filter",
        },
    },
    "list collect": {
        "exclusive": True,
        "partners": ["question"],
    },
    "translations": {},
    "modules": {},
    "def": {"exclusive": False},
    "mako": {},
    "auto terms": {"exclusive": True, "partners": ["question"]},
    "terms": {"exclusive": True, "partners": ["question", "template"]},
    "variable name": {"exclusive": True, "allowed_attrs": {"gathered", "data"}},
    "default language": {},
    "default validation messages": {},
    "reset": {},
    "on change": {},
    "images": {},
    "image sets": {},
    "default screen parts": {
        "allowed_attrs": [
            "default screen parts",
        ],
    },
    "metadata": {},
    "question": {
        "exclusive": True,
        "partners": ["auto terms", "terms", "attachment", "attachments"],
    },
    "action": {
        "exclusive": True,
    },
    "backgroundresponse": {
        "exclusive": True,
    },
    "response": {
        "exclusive": True,
        "allowed_attrs": [
            "event",
            "mandatory",
        ],
    },
    "binaryresponse": {
        "exclusive": True,
    },
    "all_variables": {
        "exclusive": True,
    },
    "response filename": {
        "exclusive": True,
    },
    "redirect url": {
        "exclusive": True,
    },
    "null response": {
        "exclusive": True,
    },
    "code": {},
    "comment": {"exclusive": False},
    "interview help": {
        "exclusive": True,
    },
    "machine learning storage": {},
}

# All known dictionary keys (from docassemble/base/parse.py Question.__init__)
all_dict_keys = (
    "features",
    "scan for variables",
    "only sets",
    "question",
    "code",
    "event",
    "translations",
    "default language",
    "on change",
    "sections",
    "progressive",
    "auto open",
    "section",
    "machine learning storage",
    "language",
    "prevent going back",
    "back button",
    "usedefs",
    "continue button label",
    "continue button color",
    "resume button label",
    "resume button color",
    "back button label",
    "back button color",
    "corner back button label",
    "skip undefined",
    "list collect",
    "mandatory",
    "attachment options",
    "script",
    "css",
    "initial",
    "default role",
    "command",
    "objects from file",
    "use objects",
    "data",
    "variable name",
    "data from code",
    "objects",
    "id",
    "ga id",
    "segment id",
    "segment",
    "supersedes",
    "order",
    "image sets",
    "images",
    "def",
    "mako",
    "interview help",
    "default screen parts",
    "default validation messages",
    "generic object",
    "generic list object",
    "comment",
    "metadata",
    "modules",
    "reset",
    "imports",
    "terms",
    "auto terms",
    "role",
    "include",
    "action buttons",
    "if",
    "validation code",
    "require",
    "orelse",
    "attachment",
    "attachments",
    "attachment code",
    "attachments code",
    "allow emailing",
    "allow downloading",
    "email subject",
    "email body",
    "email template",
    "email address default",
    "progress",
    "zip filename",
    "action",
    "backgroundresponse",
    "response",
    "binaryresponse",
    "all_variables",
    "response filename",
    "content type",
    "redirect url",
    "null response",
    "sleep",
    "include_internal",
    "css class",
    "table css class",
    "response code",
    "subquestion",
    "reload",
    "help",
    "audio",
    "video",
    "decoration",
    "signature",
    "under",
    "pre",
    "post",
    "right",
    "check in",
    "yesno",
    "noyes",
    "yesnomaybe",
    "noyesmaybe",
    "sets",
    "event",
    "choices",
    "buttons",
    "dropdown",
    "combobox",
    "field",
    "shuffle",
    "review",
    "need",
    "depends on",
    "target",
    "table",
    "rows",
    "columns",
    "require gathered",
    "allow reordering",
    "edit",
    "delete buttons",
    "confirm",
    "read only",
    "edit header",
    "confirm",
    "show if empty",
    "template",
    "content file",
    "content",
    "subject",
    "reconsider",
    "undefine",
    "continue button field",
    "fields",
    "indent",
    "url",
    "default",
    "datatype",
    "extras",
    "allowed to set",
    "show incomplete",
    "not available label",
    "always include editable files",
    "question metadata",
    "include attachment notice",
    "include download tab",
    "describe file types",
    "manual attachment list",
    "breadcrumb",
    "tabular",
    "hide continue button",
    "disable continue button",
    "gathered",
    "show if",
    "hide if",
    "js show if",
    "js hide if",
    "enable if",
    "disable if",
    "js enable if",
    "js disable if",
    "disable others",
) + (
    "filter",
    "sort key",
    "sort reverse",
)

_SIGNATURE_ONLY_TOP_LEVEL_KEYS = frozenset({"required", "pen color"})


def _lowercase_key_map(mapping: dict[Any, Any]) -> dict[str, str]:
    return {key.lower(): key for key in mapping.keys() if isinstance(key, str) and not _is_internal_metadata_key(key)}


def _allowed_top_level_keys(doc_keys_lower: dict[str, str]) -> set[str]:
    allowed_keys = set(all_dict_keys)
    if "signature" in doc_keys_lower:
        allowed_keys.update(_SIGNATURE_ONLY_TOP_LEVEL_KEYS)
    return allowed_keys


def _get_case_insensitive(mapping: dict[Any, Any], key: str, default: Any = None) -> Any:
    original_key = _lowercase_key_map(mapping).get(key.lower())
    if original_key is None:
        return default
    return mapping.get(original_key, default)


def _make_yaml_parser() -> YAML:
    yaml = YAML()
    yaml.allow_duplicate_keys = False
    return yaml


def _with_line_metadata(value: Any) -> Any:
    if isinstance(value, CommentedMap):
        converted: dict[Any, Any] = {}
        key_lines: dict[Any, int] = {}
        value_lines: dict[Any, int] = {}
        key_getter = getattr(value.lc, "key", None)
        value_getter = getattr(value.lc, "value", None)
        for key, item in value.items():
            converted[key] = _with_line_metadata(item)
            if callable(key_getter):
                try:
                    key_info = key_getter(key)
                except (AttributeError, KeyError, TypeError):
                    key_info = None
                if isinstance(key_info, tuple) and len(key_info) >= 1 and isinstance(key_info[0], int):
                    key_lines[key] = key_info[0] + 1
            if callable(value_getter):
                try:
                    value_info = value_getter(key)
                except (AttributeError, KeyError, TypeError):
                    value_info = None
                if isinstance(value_info, tuple) and len(value_info) >= 1 and isinstance(value_info[0], int):
                    value_lines[key] = value_info[0] + 1
        converted["__line__"] = value.lc.line + 1
        if key_lines:
            converted["__key_lines__"] = key_lines
        if value_lines:
            converted["__value_lines__"] = value_lines
        return converted
    if isinstance(value, CommentedSeq):
        return [_with_line_metadata(item) for item in value]
    return value


def _normalize_expr(expr: str) -> str:
    normalized = re.sub(r"\s+", "", expr or "")
    return normalized.replace('"', "'")


def _absolute_document_line(document_start_line: int, relative_line: int) -> int:
    return document_start_line + max(relative_line, 1) - 1


def _relative_top_level_error_line(
    doc: Mapping[Any, Any],
    key: Any,
    err_line: int,
    err_code: str,
    *,
    source_code: str,
) -> int:
    key_line = _lc_key_line(doc, key)
    if isinstance(key, str):
        source_key_line = _find_top_level_key_line(source_code, key)
        if source_key_line is not None:
            key_line = source_key_line

    lower_key = key.lower() if isinstance(key, str) else key
    if lower_key == "fields":
        return max(err_line, 1)
    if lower_key == "need":
        return key_line if err_line <= 1 else max(err_line, 1)
    if lower_key == "on change":
        return key_line if err_line <= 1 else max(err_line, 1)
    if lower_key == "action buttons":
        return key_line if err_line <= 1 else max(err_line, 1)
    if lower_key == "translations":
        return key_line if err_line <= 1 else max(err_line, 1)
    if lower_key == "if":
        return key_line if err_line <= 1 else max(err_line, 1)
    if lower_key == "require":
        return key_line if err_line <= 1 else max(err_line, 1)
    if err_code == MessageCode.VALIDATION_CODE_MISSING_VALIDATION_ERROR:
        return key_line

    value = doc.get(key)
    if lower_key == "show if" and isinstance(value, Mapping) and "code" in value:
        return _relative_value_line(value, "code", err_line)
    if isinstance(value, str):
        return _relative_value_line(doc, key, err_line)
    return key_line


def _contains_interview_order_marker(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return "interview_order" in lowered or "interview order" in lowered
    return False


def _is_interview_order_style_block(doc: dict[str, Any]) -> bool:
    mandatory = _get_case_insensitive(doc, "mandatory")
    mandatory_true = mandatory is True or (isinstance(mandatory, str) and mandatory.strip().lower() == "true")
    if mandatory_true:
        return True
    if _contains_interview_order_marker(_get_case_insensitive(doc, "id")):
        return True
    if _contains_interview_order_marker(_get_case_insensitive(doc, "comment")):
        return True
    return False


def _extract_field_var_name(field_item: Any) -> Optional[str]:
    if not isinstance(field_item, dict):
        return None
    modifier_keys = DAFields.modifier_keys
    for key, value in field_item.items():
        if key in modifier_keys:
            continue
        if isinstance(value, str):
            return value
    return None


def _extract_names_from_python_expr(expr: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = _safe_ast_parse(expr)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
    return names


def _extract_controller_vars_for_field_modifier(modifier_value: Any) -> set[str]:
    if isinstance(modifier_value, str):
        return set(_IDENTIFIER_RE.findall(modifier_value))
    if isinstance(modifier_value, dict):
        vars_found: set[str] = set()
        ref_var = modifier_value.get("variable")
        if isinstance(ref_var, str):
            vars_found.update(_IDENTIFIER_RE.findall(ref_var))
        code = modifier_value.get("code")
        if isinstance(code, str):
            vars_found.update(_extract_names_from_python_expr(code))
        return vars_found
    return set()


def _extract_vars_from_js_condition(cond: str) -> set[str]:
    if not isinstance(cond, str):
        return set()
    return {m.group(1) for m in _JS_VAL_RE.finditer(cond)}


def _invert_simple_comparison(cond: str) -> Optional[str]:
    m = re.match(r"^\s*(.+?)\s*(==|!=)\s*(.+?)\s*$", cond or "")
    if not m:
        return None
    left, op, right = m.groups()
    inv_op = "!=" if op == "==" else "=="
    return f"{left.strip()} {inv_op} {right.strip()}"


def _guard_candidates_for_modifier(modifier_key: str, modifier_value: Any) -> list[str]:
    is_hide = modifier_key in _HIDE_STYLE_MODIFIERS
    is_js = modifier_key.startswith("js ")
    guards: list[str] = []

    if is_js and isinstance(modifier_value, str):
        vars_found = sorted(_extract_vars_from_js_condition(modifier_value))
        for var_name in vars_found:
            if is_hide:
                guards.append(f"not ({var_name})")
                guards.append(f"not {var_name}")
            else:
                guards.append(var_name)
        guards.append(modifier_value.strip())
        return [guard for guard in guards if guard]

    if isinstance(modifier_value, str):
        cond = modifier_value.strip()
        if not cond:
            return guards
        if is_hide:
            guards.append(f"not ({cond})")
            guards.append(f"not {cond}")
            inverted = _invert_simple_comparison(cond)
            if inverted:
                guards.append(inverted)
        else:
            guards.append(cond)
        return guards

    if not isinstance(modifier_value, dict):
        return guards

    ref_var = modifier_value.get("variable")
    has_is = "is" in modifier_value
    is_val = modifier_value.get("is")
    code = modifier_value.get("code")

    if isinstance(ref_var, str):
        if has_is:
            if is_hide:
                guards.append(f"{ref_var} != {repr(is_val)}")
                guards.append(f"not ({ref_var} == {repr(is_val)})")
            else:
                guards.append(f"{ref_var} == {repr(is_val)}")
        else:
            if is_hide:
                guards.append(f"not ({ref_var})")
                guards.append(f"not {ref_var}")
            else:
                guards.append(ref_var)
    elif isinstance(code, str):
        if is_hide:
            guards.append(f"not ({code.strip()})")
        else:
            guards.append(code.strip())

    return [guard for guard in guards if guard]


def _extract_conditional_fields_from_doc(doc: dict[str, Any], line_number: int) -> list[dict[str, Any]]:
    fields = _get_case_insensitive(doc, "fields")
    if not isinstance(fields, list):
        return []

    conditional_fields: list[dict[str, Any]] = []
    for field_item in fields:
        field_var = _extract_field_var_name(field_item)
        if not field_var or not isinstance(field_item, dict):
            continue

        for modifier_key in _CONDITIONAL_MODIFIERS:
            if modifier_key not in field_item:
                continue
            modifier_value = field_item[modifier_key]
            guards = _guard_candidates_for_modifier(modifier_key, modifier_value)
            if not guards:
                continue
            conditional_fields.append(
                {
                    "field_var": field_var,
                    "guards": guards,
                    "line_number": _absolute_document_line(line_number, _lc_line(field_item)),
                }
            )
    return conditional_fields


def _find_variable_reference_lines(code: str, variable_expr: str) -> list[int]:
    lines = code.splitlines()
    if _SIMPLE_IDENTIFIER_RE.match(variable_expr):
        pattern = re.compile(rf"\b{re.escape(variable_expr)}\b")
    else:
        pattern = re.compile(rf"{re.escape(variable_expr)}(?!\w)")
    return [i + 1 for i, line in enumerate(lines) if pattern.search(line)]


def _statement_span(stmts: list[ast.stmt]) -> Optional[tuple[int, int]]:
    if not stmts:
        return None
    starts = [getattr(stmt, "lineno", None) for stmt in stmts]
    ends = [getattr(stmt, "end_lineno", getattr(stmt, "lineno", None)) for stmt in stmts]
    valid_starts = [x for x in starts if isinstance(x, int)]
    valid_ends = [x for x in ends if isinstance(x, int)]
    if not valid_starts or not valid_ends:
        return None
    return (min(valid_starts), max(valid_ends))


def _extract_branch_guards_by_line(code: str) -> dict[int, list[str]]:
    guards_by_line: dict[int, list[str]] = {}
    try:
        tree = _safe_ast_parse(code)
    except SyntaxError:
        return guards_by_line

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        cond = ast.get_source_segment(code, node.test)
        if not cond:
            try:
                cond = ast.unparse(node.test)
            except Exception:
                cond = ""
        if not cond:
            continue

        if isinstance(getattr(node, "lineno", None), int):
            guards_by_line.setdefault(node.lineno, []).append(cond)

        body_span = _statement_span(node.body)
        if body_span:
            for line in range(body_span[0], body_span[1] + 1):
                guards_by_line.setdefault(line, []).append(cond)

        orelse_span = _statement_span(node.orelse)
        if orelse_span:
            negated = f"not ({cond})"
            for line in range(orelse_span[0], orelse_span[1] + 1):
                guards_by_line.setdefault(line, []).append(negated)

    return guards_by_line


def _has_showifdef_guard(active_guards: list[str], field_var: str) -> bool:
    quoted_var = re.escape(field_var)
    showifdef_pattern = re.compile(rf"showifdef\s*\(\s*['\"]{quoted_var}['\"]\s*\)")
    return any(showifdef_pattern.search(guard or "") for guard in active_guards)


def _has_matching_guard(active_guards: list[str], expected_guards: list[str]) -> bool:
    expected_norm = [_normalize_expr(guard) for guard in expected_guards if guard]
    if not expected_norm:
        return True
    for guard in active_guards:
        guard_norm = _normalize_expr(guard)
        if any(expected in guard_norm for expected in expected_norm):
            return True
    return False


def _find_unmatched_interview_order_references(
    doc: dict[str, Any], conditional_fields: list[dict[str, Any]]
) -> list[tuple[str, int]]:
    code = _get_case_insensitive(doc, "code")
    if not isinstance(code, str):
        return []
    if not _is_interview_order_style_block(doc):
        return []

    guards_by_line = _extract_branch_guards_by_line(code)
    unmatched: list[tuple[str, int]] = []
    guards_by_field_var: dict[str, list[list[str]]] = {}
    for conditional in conditional_fields:
        field_var = conditional["field_var"]
        guards_by_field_var.setdefault(field_var, []).append(conditional["guards"])

    for field_var, expected_guard_sets in guards_by_field_var.items():
        for ref_line in _find_variable_reference_lines(code, field_var):
            active_guards = guards_by_line.get(ref_line, [])
            if _has_showifdef_guard(active_guards, field_var):
                continue
            if not any(_has_matching_guard(active_guards, expected_guards) for expected_guards in expected_guard_sets):
                unmatched.append((field_var, ref_line))
    return unmatched


def _max_screen_visibility_nesting_depth(doc: dict[str, Any]) -> tuple[int, int | None]:
    fields = _get_case_insensitive(doc, "fields")
    if not isinstance(fields, list):
        return (0, None)

    screen_vars = {field_var for field_var in (_extract_field_var_name(item) for item in fields) if field_var}
    if not screen_vars:
        return (0, None)

    adjacency: dict[str, set[str]] = {var: set() for var in screen_vars}
    field_lines: dict[str, int] = {}
    for field_item in fields:
        if not isinstance(field_item, dict):
            continue
        target_var = _extract_field_var_name(field_item)
        if not target_var:
            continue
        field_lines[target_var] = _lc_line(field_item)
        for modifier_key in ("show if", "hide if"):
            if modifier_key not in field_item:
                continue
            controllers = _extract_controller_vars_for_field_modifier(field_item[modifier_key])
            for controller in controllers:
                if controller in screen_vars:
                    adjacency.setdefault(controller, set()).add(target_var)

    visiting: set[str] = set()
    memo: dict[str, tuple[int, int | None]] = {}

    def depth(var_name: str) -> tuple[int, int | None]:
        if var_name in memo:
            return memo[var_name]
        if var_name in visiting:
            return (0, None)
        visiting.add(var_name)
        max_result: tuple[int, int | None] = (0, None)
        for child in adjacency.get(var_name, set()):
            child_depth, child_line = depth(child)
            candidate_depth = 1 + child_depth
            candidate_line = child_line if child_line is not None else field_lines.get(child)
            if candidate_depth > max_result[0]:
                max_result = (candidate_depth, candidate_line)
        visiting.remove(var_name)
        memo[var_name] = max_result
        return max_result

    return max(
        (depth(var) for var in adjacency.keys()),
        default=(0, None),
        key=lambda result: result[0],
    )


_TAGGED_PDF_TRUE_RE = re.compile(
    r"tagged\s+pdf\s*:\s*(true|yes|1|on)\b",
    re.IGNORECASE,
)


def _detect_file_wide_tagged_pdf(full_content: str) -> bool:
    for source_code in DOCUMENT_MATCH.split(full_content):
        source_code = normalize_yaml_document_for_parser(source_code)
        if _TAGGED_PDF_TRUE_RE.search(source_code):
            return True
    return False
