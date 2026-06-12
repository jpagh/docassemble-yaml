# Each doc, apply this to each block
import argparse
import ast
import dataclasses
import logging
import re
import sys
from collections.abc import Mapping
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Literal, Optional, cast

import esprima  # type: ignore[import-untyped]
from mako.exceptions import (  # type: ignore[import-untyped]
    CompileException,
    SyntaxException,
)
from mako.template import Template as MakoTemplate  # type: ignore[import-untyped]
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.error import MarkedYAMLError

from docassemble_lsp.core.accessibility import (
    find_accessibility_findings,
)
from docassemble_lsp.core.field_keys import (
    FIELD_ITEM_KNOWN_KEYS_LOWER,
    FIELD_JS_MODIFIER_KEYS,
    FIELD_MAKO_KEYS,
    FIELD_MODIFIER_KEYS,
    FIELD_OBJECT_KEYS,
    FIELD_PY_MODIFIER_KEYS,
    FIELDS_ITEM_NOTE_KEYS,
)
from docassemble_lsp.core.field_validators import (
    FieldChoiceValidator,
    FieldConditionValidator,
    FieldDatatypeValidator,
)
from docassemble_lsp.core.files import (
    collect_dayaml_cli_args,
    collect_dayaml_ignore_codes,
    collect_yaml_files,
    templates_dir_for_path,
)
from docassemble_lsp.core.formatting import FormatterConfig, format_yaml_string
from docassemble_lsp.core.jinja import (
    contains_jinja_syntax,
    has_jinja_header,
    preprocess_jinja,
)
from docassemble_lsp.core.line_helpers import (
    _is_internal_metadata_key,
    _lc_key_line,
    _lc_line,
    _relative_value_line,
)
from docassemble_lsp.core.messages import MessageCode, format_message, is_experimental_code
from docassemble_lsp.core.python_paths import path_from_uri_or_path
from docassemble_lsp.core.validation_config import (
    RuntimeOptions,
    YAMLError,
    parse_ignore_codes,
)
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_parsing import (
    DOCUMENT_MATCH,
    normalize_yaml_document_for_parser,
)
from docassemble_lsp.core.yaml_shared import (
    _ATTACHMENT_FILE_KEYS,
    _BLOCK_SCALAR_MARKERS,
    _EVENT_REFERENCE_KEYS,
    _FILE_REFERENCE_KEYS,
    _FILE_REFERENCE_LIST_PARENTS,
    _KEY_VALUE_RE,
    _LIST_ITEM_VALUE_RE,
    _PYTHON_BLOCK_KEYS,
    _PYTHON_MODULE_REFERENCE_KEYS,
    _clean_value_and_range,
    _document_lines,
    _iter_mako_block_regions,
    _precompute_parent_keys,
)

logger = logging.getLogger(__name__)
_RuamelYAML = YAML
_RuamelDuplicateKeyError = DuplicateKeyError
_RuamelMarkedYAMLError = MarkedYAMLError

# Unresolved spec questions — tracked in docs/ROADMAP.md:
# * DA is fine with mixed case it looks like (i.e. Subquestion, vs subquestion)
# * what is "order"
# * can template and terms show up in same place?
# * can features and question show up in same place?
# * is "gathered" a valid attr?
# * handle "response"
# * labels above fields?


__all__ = [
    "find_errors_from_string",
    "find_errors",
]


class _ProgressOutput:
    def __init__(self) -> None:
        self._line_active = False

    def dot(self) -> None:
        print(".", end="", flush=True)
        self._line_active = True

    def line(self, message: str) -> None:
        if self._line_active:
            print()
            self._line_active = False
        print(message)

    def finish(self) -> None:
        if self._line_active:
            print()
            self._line_active = False


# Global identifiers for _extract_conditional_fields_from_doc below. Should cover all show/hide style modifiers
_IDENTIFIER_RE = re.compile(r"[A-Za-z_]\w*")
_SIMPLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_]\w*$")
_JS_VAL_RE = re.compile(
    r"""val\s*\(\s*["']([^"']+)["']\s*\)"""
)  # matches val("fieldName") or val('fieldName') and captures fieldName
_SHOW_STYLE_MODIFIERS = {
    "show if",
    "enable if",
    "js show if",
    "js enable if",
}
_HIDE_STYLE_MODIFIERS = {
    "hide if",
    "disable if",
    "js hide if",
    "js disable if",
}
_CONDITIONAL_MODIFIERS = _SHOW_STYLE_MODIFIERS | _HIDE_STYLE_MODIFIERS
_YAML_ERROR_LINE_RE = re.compile(r"line (\d+), column \d+")
_YAML_ERROR_TRAILING_LINE_RE = re.compile(r"\(line: (\d+)\)")
_FIELD_PRESENTATION_KEYS = FIELDS_ITEM_NOTE_KEYS


# Ensure that if there's a space in the str, it's between quotes.
space_in_str = re.compile("^[^ ]*['\"].* .*['\"][^ ]*$")
# ValidatorError is a 3-tuple of (error_message, line_number, message_code)
# where message_code is from MessageCode constants.
ValidatorError = tuple[str, int, str]


def _normalize_validator_error(err: object) -> ValidatorError:
    if not isinstance(err, tuple):
        raise TypeError(
            "Validator errors must be tuples of "
            "(message: str, line_number: int, code: str); "
            f"got {type(err).__name__}: {err!r}"
        )
    if len(err) != 3:
        raise ValueError(
            "Validator errors must be 3-tuples of "
            "(message: str, line_number: int, code: str); "
            f"got length {len(err)}: {err!r}"
        )

    err_msg, err_line, err_code = err
    if not isinstance(err_msg, str):
        raise TypeError(f"Validator error message must be a string; got {type(err_msg).__name__}: {err!r}")
    if not isinstance(err_line, int):
        raise TypeError(f"Validator error line number must be an int; got {type(err_line).__name__}: {err!r}")
    if not isinstance(err_code, str):
        raise TypeError(f"Validator error code must be a string; got {type(err_code).__name__}: {err!r}")

    return (err_msg, err_line, err_code)


def _validator_error(code: str, line_number: int = 1, **kwargs: Any) -> ValidatorError:
    return (format_message(code, **kwargs), line_number, code)


def _yaml_error(
    *,
    code: str,
    line_number: int,
    file_name: str,
    err_str: str | None = None,
    **kwargs: Any,
) -> "YAMLError":
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


def _variable_candidates(var_expr: str) -> set[str]:
    expr = var_expr.strip()
    candidates = {expr}
    if "." in expr:
        parts = expr.split(".")
        for i in range(len(parts), 0, -1):
            candidates.add(".".join(parts[:i]))
    expanded = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        expanded.add(candidate)
        # Accept both full indexed paths and their base paths, e.g.:
        # children[i].parents["Other"] -> children[i].parents
        while candidate.endswith("]") and "[" in candidate:  # pragma: no branch
            candidate = candidate[: candidate.rfind("[")].strip()
            if candidate:  # pragma: no branch
                expanded.add(candidate)
    return expanded


_ILLEGAL_VARIABLE_AST_NODES: tuple[type[ast.AST], ...] = tuple(
    node_type
    for node_type in (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ExceptHandler,
        ast.ClassDef,
        ast.Return,
        ast.Delete,
        ast.Assign,
        getattr(ast, "TypeAlias", None),
        ast.AugAssign,
        ast.AnnAssign,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.If,
        ast.With,
        ast.AsyncWith,
        getattr(ast, "Match", None),
        ast.Raise,
        ast.Try,
        getattr(ast, "TryStar", None),
        ast.Assert,
        ast.Import,
        ast.ImportFrom,
        ast.Global,
        ast.Nonlocal,
        ast.Pass,
        ast.Break,
        ast.Continue,
        ast.BoolOp,
        ast.NamedExpr,
        ast.BinOp,
        ast.UnaryOp,
        ast.Lambda,
        ast.IfExp,
        ast.Dict,
        ast.Set,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Await,
        ast.Yield,
        ast.YieldFrom,
        ast.Compare,
        ast.Call,
        ast.FormattedValue,
        ast.JoinedStr,
        ast.List,
        ast.Tuple,
        ast.Starred,
    )
    if node_type is not None
)


# Docassemble reserved names that should not be used as interview variable names.
# Sources: special.md (Reserved names, Variables set by docassemble, Iterators)
_DOCASSEMBLE_RESERVED_NAMES: frozenset[str] = frozenset(
    {
        # Variables set by docassemble internally
        "_internal",
        "nav",
        "url_args",
        "role_needed",
        "session_local",
        "device_local",
        "user_local",
        # Iterator variables ``x`, ``i``–``n`` are NOT included here even though
        # special.md says "you should never set these variables yourself."
        # The parser does not reject them, and they have legitimate uses:
        # ``x.attribute`` for generic-object attribute access and ``x[i]`` for
        # single-page list-collection patterns.  Bare ``x`` as a field target
        # is unusual but technically valid and allowed.
        # Variables that interviews can set (with special meaning)
        "role",
        "speak_text",
        "track_location",
        "multi_user",
        "menu_items",
        "allow_cron",
        # Event variables
        "incoming_email",
        "role_event",
        "cron_hourly",
        "cron_daily",
        "cron_weekly",
        "cron_monthly",
        # Other reserved names
        "caller",
        "loop",
        "row_index",
        "row_item",
        "self",
        "STOP_RENDERING",
        "user_dict",
    }
)


def _is_docassemble_reserved_name(varname: str) -> bool:
    """Check if a plain variable name is a Docassemble reserved name.

    Only checks simple identifiers (not dotted or indexed access),
    since dotted names like ``user.name`` refer to object attributes
    rather than top-level interview variables.
    """
    return "." not in varname and "[" not in varname and varname in _DOCASSEMBLE_RESERVED_NAMES


def _invalid_field_variable_name(varname: Any) -> bool:
    if not isinstance(varname, str):
        return True
    if re.search(r"[\n\r\(\)\{\}\*\^\#]", varname):
        return True
    try:
        tree = ast.parse(varname)
    except SyntaxError:
        return True
    return any(isinstance(node, _ILLEGAL_VARIABLE_AST_NODES) for node in ast.walk(tree))


class YAMLStr:
    """Should be a direct YAML string, not a list or dict"""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, str):
            self.errors = [_validator_error(MessageCode.YAML_STRING_TYPE, value=x)]


class MakoText:
    """A string that will be run through a Mako template from DA. Needs to have valid Mako template"""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, str):
            self.errors = [_validator_error(MessageCode.YAML_STRING_TYPE, value=x)]
            return
        try:
            self.template = MakoTemplate(x, strict_undefined=True, input_encoding="utf-8")
        except SyntaxException as ex:
            self.errors = [
                _validator_error(
                    MessageCode.MAKO_SYNTAX_ERROR,
                    ex.lineno,
                    error=str(ex),
                )
            ]
        except CompileException as ex:
            self.errors = [
                _validator_error(
                    MessageCode.MAKO_COMPILE_ERROR,
                    ex.lineno,
                    error=str(ex),
                )
            ]


# Docassemble bracket commands that require content after the command name.
# Commands like [FILE path], [QR text], [YOUTUBE id] need a value.
# Commands like [NO_EMOJIS], [BR], [NEWLINE] are self-contained.
_BRACKET_COMMANDS_REQUIRING_CONTENT: frozenset[str] = frozenset(
    {
        "FILE",
        "FIELD",
        "TARGET",
        "QR",
        "YOUTUBE",
        "VIMEO",
    }
)
# Regex to find bracket commands: captures command name and the content inside.
_BRACKET_COMMAND_RE = re.compile(r"\[([A-Z][A-Z_]+)\s*([^\]]*)\]")

# Mako syntax patterns used to detect templating in field labels.
# Mirrors the parser's ``match_mako`` regex from docassemble/base/parse.py.
_MAKO_SYNTAX_RE = re.compile(r"<%|\$\{|% if|% for|% while|##")


def _contains_mako_syntax(text: str) -> bool:
    """Check if a text string contains Mako templating syntax."""
    return bool(_MAKO_SYNTAX_RE.search(text))


def _scan_bracket_markup_errors(text: str) -> list[ValidatorError]:
    """Scan a text string for obviously malformed Docassemble bracket commands.

    Reports empty commands like ``[FILE]`` or ``[QR]`` that are missing
    required content.  Does not validate the content (file paths, YouTube IDs,
    etc.) — only the presence of content for commands that require it.
    """
    errors: list[ValidatorError] = []
    for m in _BRACKET_COMMAND_RE.finditer(text):
        command = m.group(1)
        content = m.group(2).strip()
        if command in _BRACKET_COMMANDS_REQUIRING_CONTENT and not content:
            line_number = text[: m.start()].count("\n") + 1
            errors.append(
                _validator_error(
                    MessageCode.MARKUP_BRACKET_EMPTY,
                    line_number=line_number,
                    command=command,
                )
            )
    return errors


class MakoMarkdownText(MakoText):
    """A string that will be run through a Mako template from DA, then through a markdown formatter. Needs to have valid Mako template"""

    def __init__(self, x):
        super().__init__(x)
        if isinstance(x, str):
            self.errors.extend(_scan_bracket_markup_errors(x))


class PythonText:
    """A full multiline python script. Should have valid python syntax. i.e. a code block

    This validator parses the Python using the stdlib ast module and reports
    SyntaxError with the line number from the parsed code so the caller can
    translate it into the YAML file line number.
    """

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, str):
            self.errors = [
                _validator_error(
                    MessageCode.PYTHON_CODE_TYPE,
                    value_type=type(x).__name__,
                )
            ]
            return
        try:
            ast.parse(x)
        except SyntaxError as ex:
            # ex.lineno gives line number within the code block
            lineno = ex.lineno or 1
            msg = ex.msg or str(ex)
            self.errors = [_validator_error(MessageCode.PYTHON_SYNTAX_ERROR, lineno, message=msg)]


class AcceptFieldValue:
    """Validates the ``accept`` modifier on a Docassemble file-upload field.

    DA evaluates ``accept`` as a Python expression at runtime, so the YAML
    value must be a Python string literal.  This means the MIME type string
    needs an extra layer of quoting:

    * ``accept: "'application/pdf,image/jpeg'"``  (YAML double-quotes wrapping
      a Python single-quoted string)
    * ``accept: |`` followed by ``"application/pdf,image/jpeg"`` on the next
      line (block scalar whose content is a double-quoted Python string)

    A common mistake is writing the MIME string bare, e.g.
    ``accept: application/pdf`` — YAML delivers ``application/pdf`` to DA,
    which parses as Python division (``application / pdf``) and raises a
    ``NameError`` at runtime.
    """

    _HINT = (
        "accept must be a Python string literal. "
        "Wrap the MIME types in quotes so DA can eval them: "
        "accept: \"'application/pdf,image/jpeg,image/png,image/tiff'\""
    )

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, str):
            self.errors = [
                _validator_error(
                    MessageCode.PYTHON_CODE_TYPE,
                    value_type=type(x).__name__,
                )
            ]
            return
        try:
            tree = ast.parse(x.strip(), mode="eval")
        except SyntaxError as ex:
            lineno = ex.lineno or 1
            msg = ex.msg or str(ex)
            self.errors = [
                (
                    f"{self._HINT}. Parser message: {msg}",
                    lineno,
                    MessageCode.PYTHON_SYNTAX_ERROR,
                )
            ]
            return
        if not (isinstance(tree.body, ast.Constant) and isinstance(tree.body.value, str)):
            self.errors = [
                (
                    f"{self._HINT}. Got a {type(tree.body).__name__} expression instead of a string literal.",
                    1,
                    MessageCode.PYTHON_SYNTAX_ERROR,
                )
            ]


class ValidationCode(PythonText):
    """Validator for question-level `validation code`.

    In addition to Python syntax checking (inherited from PythonText), this
    emits a *warning* if the code does not call `validation_error(...)`,
    because validation code should normally call that function to explain
    validation failures to the user.
    """

    def __init__(self, x):
        super().__init__(x)
        # If there are already syntax errors, skip the usage check
        if self.errors:
            return
        try:
            tree = ast.parse(x)
        except SyntaxError:
            return
        # Walk AST and search for a call to validation_error(...)
        calls_validation_error = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "validation_error":
                    calls_validation_error = True
                    break
        if not calls_validation_error:
            # Suppress warning for transformation-only code blocks.
            # This includes assignments (even behind conditionals) and common
            # mutation helpers like define(...), which are intentionally used to
            # normalize output in many interviews.
            has_assignment = any(isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)) for n in ast.walk(tree))
            has_define_call = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "define"
                for n in ast.walk(tree)
            )
            has_expr_call = any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) for n in ast.walk(tree))
            has_raise_or_assert = any(isinstance(n, (ast.Raise, ast.Assert)) for n in ast.walk(tree))
            if (has_assignment or has_define_call or has_expr_call) and not has_raise_or_assert:
                return

            # Otherwise, emit a warning suggesting use of validation_error().
            # Use line number 1 because we don't have a more specific mapping here
            self.errors.append(_validator_error(MessageCode.VALIDATION_CODE_MISSING_VALIDATION_ERROR))


class NeedDirective:
    """Validator for top-level `need` directives.

    Upstream docassemble accepts either a string or a list whose items are
    strings or dicts containing only `pre` / `post`, with those values also
    constrained to strings or lists of strings.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.NEED_TYPE)]
            return

        for item in x:
            if isinstance(item, Mapping):
                item_keys = {key for key in item.keys() if isinstance(key, str) and not _is_internal_metadata_key(key)}
                if not item_keys or not item_keys.issubset({"pre", "post"}):
                    self.errors.append(_validator_error(MessageCode.NEED_DICT_KEYS, _lc_line(item)))
                    continue
                for phase in ("pre", "post"):
                    if phase not in item:
                        continue
                    phase_value = item[phase]
                    if isinstance(phase_value, str):
                        phase_items = [phase_value]
                    elif isinstance(phase_value, list):
                        phase_items = phase_value
                    else:
                        self.errors.append(
                            _validator_error(
                                MessageCode.NEED_PHASE_TYPE,
                                _lc_key_line(item, phase),
                                phase=phase,
                            )
                        )
                        continue
                    if any(not isinstance(sub_item, str) for sub_item in phase_items):
                        self.errors.append(
                            _validator_error(
                                MessageCode.NEED_ITEM_STRING,
                                _lc_key_line(item, phase),
                            )
                        )
            elif not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.NEED_ITEM_STRING))


class OnChangeDirective:
    """Validator for top-level `on change` blocks."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, Mapping):
            self.errors = [_validator_error(MessageCode.ON_CHANGE_TYPE)]
            return

        for key, value in x.items():
            if _is_internal_metadata_key(key):
                continue
            if not (isinstance(key, str) and isinstance(value, str)):
                self.errors.append(
                    _validator_error(
                        MessageCode.ON_CHANGE_ENTRY_TYPE,
                        _lc_key_line(x, key),
                    )
                )


class ActionButtonsDirective:
    """Validator for top-level `action buttons` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, Mapping):
            content_keys = {key for key in x.keys() if isinstance(key, str) and not _is_internal_metadata_key(key)}
            if content_keys == {"code"}:
                return
            self.errors = [_validator_error(MessageCode.ACTION_BUTTONS_TYPE)]
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.ACTION_BUTTONS_TYPE)]
            return

        for item in x:
            if not isinstance(item, Mapping):
                self.errors.append(_validator_error(MessageCode.ACTION_BUTTON_ITEM_TYPE))
                continue

            action = item.get("action")
            target = item.get("new window")
            arguments = item.get("arguments", {})
            label = item.get("label")
            color = item.get("color", "primary")
            icon = item.get("icon")
            placement = item.get("placement")
            css_class = item.get("css class")
            forget_prior = item.get("forget prior", False)

            if not isinstance(action, str):
                self.errors.append(_validator_error(MessageCode.ACTION_BUTTON_ACTION_TYPE, _lc_line(item)))
            if target is not None and not isinstance(target, (bool, str)):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_NEW_WINDOW_TYPE,
                        _lc_key_line(item, "new window"),
                    )
                )
            if not isinstance(arguments, Mapping):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_ARGUMENTS_TYPE,
                        _lc_key_line(item, "arguments"),
                    )
                )
            else:
                if any(isinstance(value, (list, dict)) for value in arguments.values()):
                    self.errors.append(
                        _validator_error(
                            MessageCode.ACTION_BUTTON_ARGUMENT_ITEM_TYPE,
                            _lc_key_line(item, "arguments"),
                        )
                    )
            if not isinstance(label, str):
                self.errors.append(_validator_error(MessageCode.ACTION_BUTTON_LABEL_TYPE, _lc_line(item)))
            if not isinstance(color, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_COLOR_TYPE,
                        _lc_key_line(item, "color"),
                    )
                )
            if icon is not None and not isinstance(icon, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_ICON_TYPE,
                        _lc_key_line(item, "icon"),
                    )
                )
            if placement is not None and not isinstance(placement, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_PLACEMENT_TYPE,
                        _lc_key_line(item, "placement"),
                    )
                )
            if css_class is not None and not isinstance(css_class, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_CSS_CLASS_TYPE,
                        _lc_key_line(item, "css class"),
                    )
                )
            if not isinstance(forget_prior, bool):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_FORGET_PRIOR_TYPE,
                        _lc_key_line(item, "forget prior"),
                    )
                )


class TranslationsDirective:
    """Validator for top-level `translations` blocks."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.TRANSLATIONS_TYPE)]
            return

        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.TRANSLATIONS_ITEM_TYPE, index))
                continue
            if not item.endswith((".xlsx", ".xlf", ".xliff")):
                self.errors.append(_validator_error(MessageCode.TRANSLATIONS_SUFFIX, index, item=item))
                continue
            parts = item.split(":")
            if len(parts) == 1:
                continue
            if len(parts) == 2 and parts[0].startswith("docassemble.") and parts[1].startswith("data/sources/"):
                continue
            self.errors.append(_validator_error(MessageCode.TRANSLATIONS_PATH, index, item=item))


class IfDirective:
    """Validator for top-level `if` directives."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, (str, list)):
            return
        self.errors = [_validator_error(MessageCode.IF_TYPE)]


class RequireDirective:
    """Validator for top-level `require` directives."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, list):
            return
        self.errors = [_validator_error(MessageCode.REQUIRE_TYPE)]


class TermsDirective:
    """Validator for top-level `terms` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, dict):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.TERMS_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, Mapping):
                self.errors.append(_validator_error(MessageCode.TERMS_ITEM_TYPE, index))


class AutoTermsDirective:
    """Validator for top-level `auto terms` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, dict):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.AUTO_TERMS_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, Mapping):
                self.errors.append(_validator_error(MessageCode.AUTO_TERMS_ITEM_TYPE, index))


class IncludeDirective:
    """Validator for top-level `include` blocks.

    Docassemble accepts either a single path string or a list of path strings.
    Paths may be plain local filenames or package-qualified like
    ``docassemble.PackageName:data/questions/file.yml``.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.INCLUDE_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.INCLUDE_ITEM_TYPE, index))


class ModulesDirective:
    """Validator for top-level `modules` blocks.

    Docassemble accepts either a single module name string or a list of module
    name strings (e.g. ``docassemble.base.util``).
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.MODULES_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.MODULES_ITEM_TYPE, index))


class ImportsDirective:
    """Validator for top-level `imports` blocks.

    Docassemble accepts either a single import statement string or a list of
    import statement strings (e.g. ``import json`` or ``from math import sqrt``).
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.IMPORTS_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.IMPORTS_ITEM_TYPE, index))


class MetadataDirective:
    """Validator for top-level `metadata` blocks.

    Docassemble always expects ``metadata`` to be a YAML mapping (dictionary).
    A scalar or list is not a valid metadata block.
    """

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, Mapping):
            self.errors = [_validator_error(MessageCode.METADATA_TYPE)]


class FeaturesDirective:
    """Validator for top-level ``features`` blocks."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, Mapping):
            self.errors = [_validator_error(MessageCode.FEATURES_TYPE)]


class SetsDirective:
    """Validator for top-level ``sets`` and ``only sets`` blocks.

    Docassemble accepts either a single variable name string or a list of
    variable name strings.  These tell the dependency solver which variables
    the block defines when the variable names cannot be detected automatically.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            self._check_reserved_name(x)
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.SETS_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.SETS_ITEM_TYPE, index))
            else:
                self._check_reserved_name(item)

    def _check_reserved_name(self, varname: str) -> None:
        stripped = varname.strip()
        top_level_var = stripped.split(".")[0].split("[")[0].strip()
        if top_level_var.startswith("_"):
            self.errors.append(_validator_error(MessageCode.FIELD_TARGET_UNDERSCORE, value_repr=repr(varname)))
        elif _is_docassemble_reserved_name(stripped):
            self.errors.append(_validator_error(MessageCode.RESERVED_DA_NAME, value_repr=repr(varname), context=""))


class EventDirective:
    """Validator for top-level ``event`` blocks.

    Docassemble treats event names as strings, but parser behavior also accepts
    a list of event name strings.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.EVENT_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.EVENT_ITEM_TYPE, index))


class PythonBool:
    """Some text that needs to explicitly be a python bool, i.e. True, False, bool(1), but not 1"""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, (bool, str)):
            return
        self.errors = [_validator_error(MessageCode.PYTHON_BOOL_TYPE, value_type=type(x).__name__)]


# ---------------------------------------------------------------------------
# Packet 4: Question Modifier validators
# ---------------------------------------------------------------------------


class ReconsiderDirective:
    """Validator for ``reconsider`` blocks.

    Parser accepts: True/False, a single variable name string, or a list of
    variable name strings.  A mapping at the top level is invalid.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, (bool, str)):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.RECONSIDER_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.RECONSIDER_ITEM_TYPE, index))


class UndefineDirective:
    """Validator for ``undefine`` blocks.

    Parser accepts: a single variable name string or a list of strings.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.UNDEFINE_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.UNDEFINE_ITEM_TYPE, index))


class SupersedesDirective:
    """Validator for ``supersedes`` blocks.

    Parser accepts: a single block ID string or a list of block ID strings.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.SUPERSEDES_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.SUPERSEDES_ITEM_TYPE, index))


class DependsOnDirective:
    """Validator for ``depends on`` blocks.

    Parser accepts: a single variable name string or a list of strings.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.DEPENDS_ON_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.DEPENDS_ON_ITEM_TYPE, index))


class RoleDirective:
    """Validator for ``role`` blocks.

    Parser accepts: a single role name string or a list of role name strings.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.ROLE_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.ROLE_ITEM_TYPE, index))


class AllowedToSetDirective:
    """Validator for ``allowed to set`` blocks.

    Parser accepts: a Python expression string (evaluated to a list at runtime)
    or a plain list of variable name strings.  A bare mapping is invalid.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, (str, list)):
            return
        self.errors = [_validator_error(MessageCode.ALLOWED_TO_SET_TYPE)]


class ProgressDirective:
    """Validator for ``progress`` blocks.

    Parser accepts: an integer (0–100) or None.  Strings and lists are invalid.
    """

    def __init__(self, x):
        self.errors = []
        if x is None or isinstance(x, int):
            return
        self.errors = [_validator_error(MessageCode.PROGRESS_TYPE)]


class JSShowIf:
    """Validator for js show if/hide if/enable if/disable if field modifiers, checking:
    1) Valid JavaScript syntax (accounting for Mako expressions)
    2) Presence of at least one val() call
    3) That val() calls use quoted string literals for variable names
    """

    def __init__(
        self,
        x,
        modifier_key="js show if",
        screen_variables=None,
        has_dynamic_fields: bool = False,
    ):
        self.errors = []
        self.screen_variables = screen_variables or set()
        self._has_dynamic_fields = has_dynamic_fields
        if not isinstance(x, str):
            self.errors = [
                _validator_error(
                    MessageCode.JS_MODIFIER_TYPE,
                    modifier_key=modifier_key,
                    value_type=type(x).__name__,
                )
            ]
            return

        # Now check JavaScript syntax by removing Mako expressions first
        js_to_check = x
        mako_pattern = re.compile(r"\$\{[^}]*\}", re.DOTALL)
        js_to_check = mako_pattern.sub("true", js_to_check)

        try:
            parsed = esprima.parseScript(js_to_check, tolerant=False, loc=True).toDict()
        except esprima.Error as ex:
            self.errors.append(
                _validator_error(
                    MessageCode.JS_INVALID_SYNTAX,
                    getattr(ex, "lineNumber", 1) or 1,
                    modifier_key=modifier_key,
                    error=str(ex),
                )
            )
            return

        val_calls = []
        stack = [parsed]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("type") == "CallExpression":
                    callee = node.get("callee")
                    if isinstance(callee, dict) and callee.get("type") == "Identifier" and callee.get("name") == "val":
                        val_calls.append(node)
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):  # pragma: no branch
                stack.extend(node)

        if not val_calls:
            self.errors.append(
                _validator_error(
                    MessageCode.JS_MISSING_VAL_CALL,
                    modifier_key=modifier_key,
                )
            )

        for call in val_calls:
            args = call.get("arguments") or []
            valid_arg = (
                len(args) == 1
                and isinstance(args[0], dict)
                and args[0].get("type") == "Literal"
                and isinstance(args[0].get("value"), str)
            )
            if valid_arg:
                var_name = args[0].get("value")
                if self.screen_variables and not self._references_screen_variable(var_name):
                    caveat = (
                        " (unable to fully validate screen variables because this screen uses fields: code)"
                        if self._has_dynamic_fields
                        else ""
                    )
                    self.errors.append(
                        _validator_error(
                            MessageCode.JS_UNKNOWN_SCREEN_FIELD,
                            (call.get("loc", {}).get("start", {}).get("line", 1) or 1),
                            modifier_key=modifier_key,
                            var_name=var_name,
                            caveat=caveat,
                        )
                    )
                continue
            bad_arg = "<missing>"
            if args:
                first_arg = args[0]
                bad_arg = first_arg.get("raw") or first_arg.get("name") or first_arg.get("type", "<unknown>")
            self.errors.append(
                _validator_error(
                    MessageCode.JS_VAL_ARG_NOT_QUOTED,
                    (call.get("loc", {}).get("start", {}).get("line", 1) or 1),
                    bad_arg=bad_arg,
                )
            )

    def _references_screen_variable(self, var_expr):
        if not isinstance(var_expr, str):
            return False
        for candidate in _variable_candidates(var_expr):
            if candidate in self.screen_variables:
                return True
        return False


class ShowIf:
    """Validator for show if field modifier (non-js variants)
    Checks that if show if uses variable/code pattern, the referenced variable
    is defined on the same screen.
    """

    def __init__(self, x, context=None):
        self.errors = []
        self.context = context or {}

        if isinstance(x, str):
            # Shorthand form: show if: variable_name
            # This is only valid if variable_name refers to a yes/no field on the same screen
            if ":" not in x and " " not in x:  # pragma: no branch
                # We can't validate this here without screen context
                # This will be validated at a higher level with fields context
                pass
            elif x.startswith("variable:") or x.startswith("code:"):  # pragma: no branch
                # Malformed - these should be YAML dict format
                self.errors.append(_validator_error(MessageCode.SHOW_IF_MALFORMED, value=x))
        elif isinstance(x, dict):  # pragma: no branch
            # YAML dict form
            if "variable" in x:  # pragma: no branch
                # First method: show if: { variable: field_name, is: value }
                # Can only reference fields on the same screen - we'll validate in context
                pass
            elif "code" in x:
                # Third method: show if: { code: python_code }
                # Validate Python syntax for the provided code block
                code_block = x.get("code")
                if not isinstance(code_block, str):
                    self.errors.append(_validator_error(MessageCode.SHOW_IF_CODE_TYPE))
                else:
                    try:
                        ast.parse(code_block)
                    except SyntaxError as ex:
                        lineno = ex.lineno or 1
                        msg = ex.msg or str(ex)
                        self.errors.append(
                            _validator_error(
                                MessageCode.SHOW_IF_CODE_SYNTAX,
                                lineno,
                                message=msg,
                            )
                        )
            else:
                self.errors.append(_validator_error(MessageCode.SHOW_IF_DICT_KEYS))


class AttachmentBlockDirective:
    """Validator for top-level ``attachment`` and ``attachments`` blocks.

    Validates the static structure of attachment list items based on parser
    behavior in ``Question.process_attachment``. The parser accepts both a
    single dict and a list of dicts, so this validator handles both forms.

    Docassemble parser-backed validation:
    - Each attachment item must be a dictionary.
    - ``name``, ``filename``, ``description`` -- plain text.
    - ``variable name`` -- plain text.
    - ``metadata`` -- a dictionary.
    - ``content file`` -- text, list of text, or dict with single key ``code``.
    - ``code`` (for PDF/DOCX fields) -- plain text (Python expression).
    - ``field variables`` / ``raw field variables`` -- a list.
    - ``valid formats`` -- a string, list, or dict with single key ``code``.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, Mapping):
            items = [x]
        elif isinstance(x, list):
            items = x
        else:
            self.errors = [_validator_error(MessageCode.ATTACHMENT_ITEM_MUST_BE_DICT)]
            return

        for item in items:
            if not isinstance(item, Mapping):
                self.errors.append(_validator_error(MessageCode.ATTACHMENT_ITEM_MUST_BE_DICT, _lc_line(item)))
                continue
            self._validate_item(item)

    def _validate_item(self, item: Mapping) -> None:
        # name must be plain text (parser: defaults to word("Document"))
        if "name" in item and not isinstance(item["name"], str):
            self.errors.append(_validator_error(MessageCode.ATTACHMENT_NAME_TYPE, _lc_key_line(item, "name")))

        # filename must be plain text (parser: defaults to '')
        if "filename" in item and not isinstance(item["filename"], str):
            self.errors.append(_validator_error(MessageCode.ATTACHMENT_FILENAME_TYPE, _lc_key_line(item, "filename")))

        # variable name must be plain text (parser: raises if None, otherwise str)
        if "variable name" in item and not isinstance(item["variable name"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.ATTACHMENT_VARIABLE_NAME_TYPE,
                    _lc_key_line(item, "variable name"),
                )
            )

        # metadata must be a dict (parser: raises on non-dict)
        if "metadata" in item and not isinstance(item["metadata"], Mapping):
            self.errors.append(_validator_error(MessageCode.ATTACHMENT_METADATA_TYPE, _lc_key_line(item, "metadata")))

        # metadata entries must be bool, string, or list of strings (parser-backed)
        if "metadata" in item and isinstance(item["metadata"], Mapping):
            for key, val in item["metadata"].items():
                if _is_internal_metadata_key(key):
                    continue
                if isinstance(val, (bool, str)):
                    continue
                if isinstance(val, list) and all(isinstance(sub, str) for sub in val):
                    continue
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_METADATA_ENTRY_TYPE,
                        _lc_key_line(item["metadata"], key),
                        data_type=type(val).__name__,
                        key_name=str(key),
                    )
                )

        # content file must be text, list of text, or dict with single key 'code' (parser-backed)
        if "content file" in item:
            cf = item["content file"]
            if isinstance(cf, str):
                pass
            elif isinstance(cf, list):
                for idx, cf_item in enumerate(cf):
                    if not isinstance(cf_item, str):
                        self.errors.append(
                            _validator_error(
                                MessageCode.ATTACHMENT_CONTENT_FILE_TYPE,
                                _seq_item_line(cf, idx),
                            )
                        )
            elif isinstance(cf, Mapping):
                # Filter out internal metadata keys (__line__, __key_lines__, __value_lines__)
                content_keys = {k for k in cf if isinstance(k, str) and not _is_internal_metadata_key(k)}
                if not (content_keys == {"code"} and isinstance(cf.get("code"), str)):
                    self.errors.append(
                        _validator_error(
                            MessageCode.ATTACHMENT_CONTENT_FILE_TYPE,
                            _lc_key_line(item, "content file"),
                        )
                    )
            else:
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_CONTENT_FILE_TYPE,
                        _lc_key_line(item, "content file"),
                    )
                )

        # code must be plain text (parser-backed Python expression for PDF/DOCX fields)
        if "code" in item and not isinstance(item["code"], str):
            self.errors.append(_validator_error(MessageCode.ATTACHMENT_CODE_TYPE, _lc_key_line(item, "code")))

        # field variables / raw field variables must be lists (parser-backed)
        for fv_key in ("field variables", "raw field variables"):
            if fv_key in item and not isinstance(item[fv_key], list):
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_FIELD_VARIABLES_TYPE,
                        _lc_key_line(item, fv_key),
                    )
                )

        # valid formats must be string, list, or dict with single key 'code' (parser-backed)
        if "valid formats" in item:
            vf = item["valid formats"]
            if isinstance(vf, str):
                pass
            elif isinstance(vf, list):
                pass
            elif isinstance(vf, Mapping):
                # Filter out internal metadata keys (__line__, __key_lines__, __value_lines__)
                content_keys = {k for k in vf if isinstance(k, str) and not _is_internal_metadata_key(k)}
                if not (content_keys == {"code"} and isinstance(vf.get("code"), str)):
                    self.errors.append(
                        _validator_error(
                            MessageCode.ATTACHMENT_VALID_FORMATS_TYPE,
                            _lc_key_line(item, "valid formats"),
                        )
                    )
            else:
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_VALID_FORMATS_TYPE,
                        _lc_key_line(item, "valid formats"),
                    )
                )


class ReviewBlockDirective:
    """Validator for top-level ``review`` blocks.

    Docassemble parser-backed validation from ``Question.__init__``:
    - ``review`` must be a list (single dict is wrapped).
    - Each review item must be a dictionary.
    - If ``label`` is present, ``field`` or ``fields`` must also be present.
    - If ``field`` or ``fields`` is present, ``label`` must also be present.
    - ``note``, ``html``, ``raw html`` -- plain text.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, Mapping):
            items = [x]
        elif isinstance(x, list):
            items = x
        else:
            self.errors = [_validator_error(MessageCode.REVIEW_TYPE)]
            return

        for item in items:
            if not isinstance(item, Mapping):
                self.errors.append(_validator_error(MessageCode.REVIEW_ITEM_TYPE, _lc_line(item)))
                continue
            self._validate_item(item)

    def _validate_item(self, item: Mapping) -> None:
        has_label = "label" in item
        has_field = "field" in item or "fields" in item
        is_presentation = any(k in item for k in ("note", "html", "raw html"))

        if has_label and not has_field and not is_presentation:
            self.errors.append(_validator_error(MessageCode.REVIEW_LABEL_REQUIRES_FIELD, _lc_key_line(item, "label")))

        if has_field and not has_label:
            self.errors.append(_validator_error(MessageCode.REVIEW_FIELD_REQUIRES_LABEL, _lc_line(item)))

        for pk in ("note", "html", "raw html"):
            if pk in item and not isinstance(item[pk], str):
                self.errors.append(_validator_error(MessageCode.REVIEW_NOTE_TYPE, _lc_key_line(item, pk)))

        # show if: string or list of strings (parser-backed)
        if "show if" in item:
            show_if_val = item["show if"]
            if not isinstance(show_if_val, (str, list)):
                self.errors.append(_validator_error(MessageCode.REVIEW_SHOW_IF_TYPE, _lc_key_line(item, "show if")))
            elif isinstance(show_if_val, list):
                for sub_idx, sub_item in enumerate(show_if_val):
                    if not isinstance(sub_item, str):
                        self.errors.append(
                            _validator_error(MessageCode.REVIEW_SHOW_IF_TYPE, _seq_item_line(show_if_val, sub_idx))
                        )

        # help: plain text (parser accepts string, dict, or list; string is the common case)
        if "help" in item and not isinstance(item["help"], str):
            self.errors.append(_validator_error(MessageCode.REVIEW_HELP_TYPE, _lc_key_line(item, "help")))

        # action: plain text
        if "action" in item and not isinstance(item["action"], str):
            self.errors.append(_validator_error(MessageCode.REVIEW_ACTION_TYPE, _lc_key_line(item, "action")))

        # button: plain text
        if "button" in item and not isinstance(item["button"], str):
            self.errors.append(_validator_error(MessageCode.REVIEW_BUTTON_TYPE, _lc_key_line(item, "button")))

        # css class: plain text
        if "css class" in item and not isinstance(item["css class"], str):
            self.errors.append(_validator_error(MessageCode.REVIEW_CSS_CLASS_TYPE, _lc_key_line(item, "css class")))


class TableBlockDirective:
    """Validator for the value of the ``table`` key.

    Docassemble parser-backed: ``table`` must be a string (variable name) or
    a dict (when combined with ``rows`` and ``columns`` in the same block).
    A scalar other than string is invalid.
    """

    def __init__(self, x):
        self.errors = []
        # The parser accepts a string (variable name) or a dict
        # (when the table block is expressed as a dict).
        if not isinstance(x, (str, dict)):
            self.errors = [_validator_error(MessageCode.TABLE_TYPE)]
            return


class DAPythonVar:
    """Things that need to be defined as a docassemble var, i.e. abc or x.y['a']"""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, str):
            self.errors = [_validator_error(MessageCode.PYTHON_VAR_TYPE, value=x)]
        elif " " in x and not space_in_str.search(x):
            self.errors = [_validator_error(MessageCode.PYTHON_VAR_WHITESPACE, value=x)]


class ObjectsAttrType:
    def __init__(self, x):
        # The full typing description of the var — usage deferred until a consumer needs type-punning on the objects block value.
        self.errors = []
        if not (isinstance(x, list) or isinstance(x, dict)):
            self.errors = [_validator_error(MessageCode.OBJECTS_BLOCK_TYPE, value=x)]
        # for entry in x:
        #   ...


class DAFields:
    object_field_keys = frozenset(FIELD_OBJECT_KEYS)
    modifier_keys = frozenset(FIELD_MODIFIER_KEYS)
    mako_keys = frozenset(FIELD_MAKO_KEYS)
    js_modifier_keys = FIELD_JS_MODIFIER_KEYS
    py_modifier_keys = FIELD_PY_MODIFIER_KEYS
    _reserved_field_keys_lower = FIELD_ITEM_KNOWN_KEYS_LOWER

    def __init__(self, x, runtime_options: RuntimeOptions | None = None):
        self.errors = []
        self.has_dynamic_fields_code = False
        self.runtime_options = runtime_options or RuntimeOptions()
        if isinstance(x, dict):
            content_keys = {key for key in x.keys() if not _is_internal_metadata_key(key)}
            if content_keys == {"code"}:
                if not isinstance(x.get("code"), str):
                    self.errors = [
                        _validator_error(MessageCode.FIELDS_CODE_TYPE, value_type=type(x.get("code")).__name__)
                    ]
                return
            x = [x]
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.FIELDS_TYPE, value=x)]
            return
        self._validate_field_modifiers(x)

    def _line_for(self, field_item, code_line=1):
        return _lc_line(field_item) + max(code_line - 1, 0)

    def _key_line_for(self, field_item, key, code_line=1):
        return _lc_key_line(field_item, key) + max(code_line - 1, 0)

    def _value_line_for(self, mapping, key, code_line=1):
        return _relative_value_line(mapping, key, code_line)

    def _extract_field_name(self, field_item):
        if not isinstance(field_item, dict):
            return None
        if isinstance(field_item.get("field"), str):
            return field_item["field"]
        for key, value in field_item.items():
            if isinstance(key, str) and key.lower() in self._reserved_field_keys_lower:
                continue
            if isinstance(value, str):
                return value
        return None

    def _shorthand_label_keys(self, field_item):
        if not isinstance(field_item, dict):
            return []
        return [
            key
            for key in field_item
            if isinstance(key, str)
            and not _is_internal_metadata_key(key)
            and key.lower() not in self._reserved_field_keys_lower
        ]

    def _is_shorthand_label_key(self, field_item, field_key):
        if not isinstance(field_item, dict):
            return False
        if (
            isinstance(field_key, str) and field_key.lower() in self._reserved_field_keys_lower
        ) or _is_internal_metadata_key(field_key):
            return False
        if "field" in field_item or "label" in field_item:
            return False
        return isinstance(field_item.get(field_key), str)

    def _validate_field_target(self, field_item, target_key, *, label_key=None):
        target_value = field_item.get(target_key)
        if not isinstance(target_value, str):
            self.errors.append(
                _validator_error(MessageCode.FIELD_TARGET_NOT_PLAIN_TEXT, self._value_line_for(field_item, target_key))
            )
            return False
        stripped_target = target_value.strip()
        if _invalid_field_variable_name(stripped_target):
            context = f" for key {label_key!r}" if label_key is not None else ""
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_TARGET_INVALID_VARIABLE,
                    self._value_line_for(field_item, target_key),
                    value_repr=repr(stripped_target),
                    context=context,
                )
            )
            return False
        # Check for reserved Docassemble names and underscore-prefixed names.
        # Only flag bare reserved names (no dot/bracket access) since dotted
        # names like ``x.attribute`` are normal generic-object attribute access.
        # The underscore check still applies to the top-level part since
        # ``_internal.temp`` starts with underscore regardless of dotted form.
        top_level_var = stripped_target.split(".")[0].split("[")[0].strip()
        if top_level_var.startswith("_"):
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_TARGET_UNDERSCORE,
                    self._value_line_for(field_item, target_key),
                    value_repr=repr(stripped_target),
                )
            )
        elif _is_docassemble_reserved_name(stripped_target):
            context = f" for key {label_key!r}" if label_key is not None else ""
            self.errors.append(
                _validator_error(
                    MessageCode.RESERVED_DA_NAME,
                    self._value_line_for(field_item, target_key),
                    value_repr=repr(stripped_target),
                    context=context,
                )
            )
        return True

    def _validate_field_item_structure(self, field_item):
        shorthand_keys = self._shorthand_label_keys(field_item)
        presentation_keys = [key for key in _FIELD_PRESENTATION_KEYS if key in field_item]
        if len(presentation_keys) > 1:
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_PRESENTATION_KEY_CONFLICT, self._key_line_for(field_item, presentation_keys[1])
                )
            )

        if "label" in field_item and "field" not in field_item:
            self.errors.append(
                _validator_error(MessageCode.FIELD_ITEM_MISSING_TARGET, self._key_line_for(field_item, "label"))
            )

        input_type = field_item.get("input type")
        if "field" in field_item and "label" not in field_item and input_type != "hidden":
            self.errors.append(
                _validator_error(MessageCode.FIELD_ITEM_MISSING_LABEL, self._key_line_for(field_item, "field"))
            )

        if "label" in field_item and shorthand_keys:
            previous_label = field_item.get("label")
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_LABEL_OVERWRITE,
                    self._key_line_for(field_item, shorthand_keys[0]),
                    label_key=shorthand_keys[0],
                    previous_label=str(previous_label),
                )
            )
        elif len(shorthand_keys) > 1:
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_LABEL_OVERWRITE,
                    self._key_line_for(field_item, shorthand_keys[1]),
                    label_key=shorthand_keys[1],
                    previous_label=shorthand_keys[0],
                )
            )

        if shorthand_keys:
            label_key = shorthand_keys[0]
            field_name = field_item.get(label_key)
            self.errors.append(
                _validator_error(
                    MessageCode.FIELDS_LABEL_SHORTHAND_DISALLOWED,
                    self._key_line_for(field_item, label_key),
                    label_key=label_key,
                    field_name=str(field_name),
                )
            )

        if "field" in field_item:
            self._validate_field_target(field_item, "field")
        elif shorthand_keys:
            self._validate_field_target(field_item, shorthand_keys[0], label_key=shorthand_keys[0])

    def _validate_field_item_configuration(self, field_item):
        dt_validator = FieldDatatypeValidator(field_item)
        for err in dt_validator.errors:
            self.errors.append(err)
        choice_validator = FieldChoiceValidator(field_item)
        for err in choice_validator.errors:
            self.errors.append(err)

        datatype = field_item.get("datatype")
        datatype_normalized = datatype.strip().lower() if isinstance(datatype, str) else None

        if "exclude" in field_item and isinstance(field_item["exclude"], Mapping):
            self.errors.append(
                _validator_error(MessageCode.FIELD_EXCLUDE_INVALID_FORMAT, self._key_line_for(field_item, "exclude"))
            )

        if (
            datatype_normalized in {"object", "object_radio", "object_multiselect", "object_checkboxes"}
            and "default" in field_item
            and not isinstance(field_item["default"], (list, str))
        ):
            self.errors.append(
                _validator_error(MessageCode.FIELD_DEFAULT_INVALID_FORMAT, self._key_line_for(field_item, "default"))
            )

    def _validate_python_modifier(self, modifier_key, modifier_value, field_item, screen_variables):
        def references_screen_variable(var_expr):
            if not isinstance(var_expr, str):  # pragma: no cover
                return False
            candidates = _variable_candidates(var_expr)
            if any(candidate in screen_variables for candidate in candidates):
                return True
            # In generic-object screens, x.<attr> often aliases another object path
            # like children[i].<attr>. Allow suffix match only when one side is x.<...>.
            for candidate in candidates:
                if candidate.startswith("x.") and any(
                    screen_var.endswith("." + candidate.split(".", 1)[1]) for screen_var in screen_variables
                ):
                    return True
            for screen_var in screen_variables:
                if screen_var.startswith("x.") and any(
                    candidate.endswith("." + screen_var.split(".", 1)[1]) for candidate in candidates
                ):
                    return True
            return False

        if isinstance(modifier_value, dict):
            if "variable" in modifier_value and "code" not in modifier_value:
                ref_var = modifier_value.get("variable")
                if not isinstance(ref_var, str):
                    self.errors.append(
                        _validator_error(
                            MessageCode.FIELD_MODIFIER_VARIABLE_TYPE,
                            self._key_line_for(field_item, modifier_key),
                            modifier_key=modifier_key,
                            value_type=type(ref_var).__name__,
                        )
                    )
                elif not references_screen_variable(ref_var):
                    self.errors.append(
                        _validator_error(
                            MessageCode.FIELD_MODIFIER_UNKNOWN_VARIABLE_DICT,
                            self._key_line_for(field_item, modifier_key),
                            modifier_key=modifier_key,
                            ref_var=ref_var,
                        )
                    )
            elif "code" in modifier_value:
                code_text = modifier_value.get("code")
                validator = PythonText(code_text)
                for err in validator.errors:
                    err_msg, err_line, _err_code = _normalize_validator_error(err)
                    self.errors.append(
                        _validator_error(
                            MessageCode.FIELD_MODIFIER_CODE_ERROR,
                            self._value_line_for(modifier_value, "code", err_line),
                            modifier_key=modifier_key,
                            error=err_msg.lower(),
                        )
                    )
                if modifier_key == "show if" and isinstance(code_text, str) and not validator.errors:
                    same_screen_refs = self._find_screen_variable_references_in_code(code_text, screen_variables)
                    if same_screen_refs:
                        refs = ", ".join(sorted(same_screen_refs))
                        self.errors.append(
                            _validator_error(
                                MessageCode.FIELD_MODIFIER_SAME_SCREEN_CODE,
                                self._key_line_for(field_item, modifier_key),
                                modifier_key=modifier_key,
                                references=refs,
                            )
                        )
            else:
                self.errors.append(
                    _validator_error(
                        MessageCode.FIELD_MODIFIER_DICT_KEYS,
                        self._key_line_for(field_item, modifier_key),
                        modifier_key=modifier_key,
                    )
                )
        elif isinstance(modifier_value, str) and ":" not in modifier_value:  # pragma: no branch
            if not references_screen_variable(modifier_value):
                self.errors.append(
                    _validator_error(
                        MessageCode.FIELD_MODIFIER_UNKNOWN_VARIABLE_STRING,
                        self._key_line_for(field_item, modifier_key),
                        modifier_key=modifier_key,
                        modifier_value=modifier_value,
                    )
                )

    def _find_screen_variable_references_in_code(self, code_text, screen_variables):
        try:
            tree = ast.parse(code_text)
        except SyntaxError:
            return set()

        name_refs = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        matches = set()
        for screen_var in screen_variables:
            if _SIMPLE_IDENTIFIER_RE.match(screen_var) and screen_var in name_refs:
                matches.add(screen_var)
                continue
            # For dotted/indexed vars, require explicit textual reference.
            if _find_variable_reference_lines(code_text, screen_var):
                matches.add(screen_var)
        return matches

    def _validate_condition_and_validation_keys(self, field_item: dict[str, Any]) -> None:
        cond_validator = FieldConditionValidator(field_item)
        for err in cond_validator.errors:
            self.errors.append(err)

    def _validate_object_field_choices(self, field_item):
        datatype = field_item.get("datatype")
        is_object_style_field = (isinstance(datatype, str) and datatype.lower().startswith("object")) or any(
            key in field_item for key in self.object_field_keys
        )
        if not is_object_style_field:
            return

        choices_value = field_item.get("choices")
        if isinstance(choices_value, Mapping) and (
            {key for key in choices_value.keys() if not _is_internal_metadata_key(key)} == {"code"}
        ):
            self.errors.append(
                _validator_error(
                    MessageCode.OBJECT_FIELD_CHOICES_CODE_DICT,
                    self._key_line_for(field_item, "choices"),
                )
            )

    def _field_item_has_content_target(self, field_item: dict[str, Any]) -> bool:
        content_keys = {key for key in field_item.keys() if isinstance(key, str) and not _is_internal_metadata_key(key)}
        if content_keys == {"code"}:
            return True
        if content_keys & {"note", "html", "raw html"}:
            return True
        return self._extract_field_name(field_item) is not None

    def _validate_field_modifiers(self, fields_list):
        self.has_dynamic_fields_code = any(
            isinstance(field_item, dict)
            and "code" in field_item
            and len({key for key in field_item.keys() if key != "code" and not _is_internal_metadata_key(key)}) == 0
            for field_item in fields_list
        )
        screen_variables = set()
        for field_item in fields_list:
            if not isinstance(field_item, dict):
                continue
            field_var_name = self._extract_field_name(field_item)
            if field_var_name and not _invalid_field_variable_name(field_var_name.strip()):
                screen_variables.add(field_var_name)

        for index, field_item in enumerate(fields_list):
            if not isinstance(field_item, dict):
                self.errors.append(
                    _validator_error(MessageCode.FIELD_ITEM_MUST_BE_DICT, _seq_item_line(fields_list, index))
                )
                continue

            self._validate_field_item_structure(field_item)
            self._validate_field_item_configuration(field_item)

            if not self._field_item_has_content_target(field_item):
                if "label" not in field_item and "field" not in field_item:
                    self.errors.append(
                        _validator_error(MessageCode.FIELD_ITEM_MISSING_TARGET, self._line_for(field_item))
                    )
                continue

            self._validate_object_field_choices(field_item)
            self._validate_field_accept(field_item)
            self._validate_field_modifier_key_case(field_item)
            self._validate_field_mako_keys(field_item)
            self._validate_field_js_modifiers(field_item, screen_variables)
            self._validate_field_py_modifiers(field_item, screen_variables)
            self._validate_condition_and_validation_keys(field_item)

    def _validate_field_accept(self, field_item):
        if "accept" in field_item:
            validator = AcceptFieldValue(field_item["accept"])
            for err in validator.errors:
                err_msg, err_line, err_code = _normalize_validator_error(err)
                self.errors.append(
                    (
                        err_msg,
                        self._value_line_for(field_item, "accept", err_line),
                        err_code,
                    )
                )

    def _validate_field_modifier_key_case(self, field_item):
        for field_key in field_item:
            if isinstance(field_key, str) and not _is_internal_metadata_key(field_key):
                if (
                    field_key not in self.modifier_keys
                    and field_key.lower() in self.modifier_keys
                    and not self._is_shorthand_label_key(field_item, field_key)
                ):
                    self.errors.append(
                        (
                            f'Invalid field key "{field_key}". docassemble field modifier keys are case-sensitive; use "{field_key.lower()}"',
                            self._key_line_for(field_item, field_key),
                            MessageCode.FIELD_MODIFIER_DICT_KEYS,
                        )
                    )

    def _validate_field_mako_keys(self, field_item):
        for field_key in field_item:
            if isinstance(field_key, str) and not _is_internal_metadata_key(field_key):
                if field_key in self.mako_keys:
                    the_mako = MakoText(str(field_item[field_key]))
                    for err in the_mako.errors:
                        err_msg, err_line, err_code = _normalize_validator_error(err)
                        self.errors.append(
                            (
                                f"{field_key} value has {err_msg}",
                                self._value_line_for(field_item, field_key, err_line),
                                err_code,
                            )
                        )

    def _validate_field_py_modifiers(self, field_item, screen_variables):
        for py_key in self.py_modifier_keys:
            if py_key in field_item:
                self._validate_python_modifier(py_key, field_item[py_key], field_item, screen_variables)

    def _validate_field_js_modifiers(self, field_item, screen_variables):
        """Validate JavaScript modifier keys on a field item."""
        for js_key in self.js_modifier_keys:
            if js_key in field_item:
                validator = JSShowIf(
                    field_item[js_key],
                    modifier_key=js_key,
                    screen_variables=screen_variables,
                    has_dynamic_fields=self.has_dynamic_fields_code,
                )
                for err in validator.errors:
                    err_msg, err_line, err_code = _normalize_validator_error(err)
                    self.errors.append((err_msg, self._value_line_for(field_item, js_key, err_line), err_code))


# type notes what the value for that dictionary key is,

# More notes:
# mandatory can only be used on:
# question, code, objects, attachment, data, data from code

# Composable validators (tracked in docs/ROADMAP.md):
#   One validator that works with just lists of single entry dicts with a str as the key,
#   and a DAPythonVar as the value, and another that expects a code block, then an OR
#   validator that takes both and works with either.
# Works with smaller blocks, prevents a lot of duplicate nested code
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
    "help": {},  # Deferred: free-form content; shape depends on upstream context.
    "fields": {"type": DAFields},
    "buttons": {},  # Deferred: already validated by DAFields at field level.
    "field": {"type": DAPythonVar},
    "template": {},  # Deferred: free-form template body; shape depends on upstream context.
    "content": {},  # Deferred: free-form content; shape depends on upstream context.
    "reconsider": {"type": ReconsiderDirective},
    "depends on": {"type": DependsOnDirective},
    "need": {"type": NeedDirective},
    "attachment": {"type": AttachmentBlockDirective},
    "attachments": {"type": AttachmentBlockDirective},
    "review": {"type": ReviewBlockDirective},
    "table": {"type": TableBlockDirective},
    "rows": {},  # Deferred: already validated by TableBlockDirective.
    "columns": {},  # Deferred: already validated by TableBlockDirective.
    "allow reordering": {},  # Deferred: already validated by DAFields at field level.
    "delete buttons": {},  # Deferred: already validated by DAFields at field level.
    "validation code": {
        "type": ValidationCode,
    },
    "translations": {"type": TranslationsDirective},
    "include": {"type": IncludeDirective},
    "default screen parts": {},  # Deferred: free-form screen part configuration; shape depends on upstream context.
    "metadata": {"type": MetadataDirective},
    "modules": {"type": ModulesDirective},
    "imports": {"type": ImportsDirective},
    "sections": {},  # Deferred: free-form list of section names; shape depends on upstream context.
    "interview help": {},  # Deferred: free-form help content; shape depends on upstream context.
    "def": {
        "type": DAPythonVar,
    },
    "mako": {
        "type": MakoText,
    },
    "usedefs": {},  # Deferred: free-form content; shape depends on upstream context.
    "default role": {},  # Deferred: free-form role name string; shape depends on upstream context.
    "default language": {"type": YAMLStr},
    "default validation messages": {},  # Deferred: free-form validation message mapping; shape depends on upstream context.
    "machine learning storage": {},  # Deferred: runtime-only shape; no static validation possible.
    "scan for variables": {"type": PythonBool},
    "show if": {
        "type": ShowIf,
    },
    "if": {"type": IfDirective},
    "sets": {"type": SetsDirective},
    "only sets": {"type": SetsDirective},
    "initial": {},  # Deferred: runtime-only initial values; no static validation possible.
    "event": {"type": EventDirective},
    "comment": {"type": YAMLStr},
    "generic object": {"type": DAPythonVar},
    "variable name": {"type": YAMLStr},
    "data from code": {},  # Deferred: runtime-only shape; no static validation possible.
    "back button label": {},  # Deferred: free-form plain text label; shape depends on upstream context.
    "continue button label": {
        "type": YAMLStr,
    },
    "decoration": {},  # Deferred: free-form decoration text; shape depends on upstream context.
    "yesno": {"type": DAPythonVar},
    "noyes": {"type": DAPythonVar},
    "yesnomaybe": {"type": DAPythonVar},
    "noyesmaybe": {"type": DAPythonVar},
    "reset": {},  # Deferred: free-form list of variable names; shape depends on upstream context.
    "on change": {"type": OnChangeDirective},
    "require": {"type": RequireDirective},
    "action buttons": {"type": ActionButtonsDirective},
    "image sets": {},  # Deferred: already validated by image_set_block in completion rules.
    "images": {},  # Deferred: free-form image configuration; shape depends on upstream context.
    "continue button field": {
        "type": DAPythonVar,
    },
    "disable others": {},  # Deferred: already validated by DAFields at field level.
    "order": {},  # Deferred: free-form list of block IDs; shape depends on upstream context.
    "undefine": {"type": UndefineDirective},
    "supersedes": {"type": SupersedesDirective},
    "role": {"type": RoleDirective},
    "allowed to set": {"type": AllowedToSetDirective},
    "progress": {"type": ProgressDirective},
    "language": {"type": YAMLStr},
    "section": {"type": YAMLStr},
}

# need a list of blocks; certain attributes imply certain blocks, and block out other things,
# like question and code

# Not all blocks are necessary: comment can be by itself, and attachment can be with question, or alone

# ordered by priority
# required_attrs feature (tracked in docs/ROADMAP.md)
types_of_blocks: dict[str, dict[str, Any]] = {
    "include": {
        "exclusive": True,
        "allowed_attrs": ["include"],
    },
    "features": {  # don't get an error, but code and question attributes aren't recognized
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
    },  # maybe?
    "list collect": {
        "exclusive": True,
        "partners": ["question"],
    },
    "translations": {},
    "modules": {},
    "def": {"exclusive": False},  # Can coexist with mako/question/code blocks
    "mako": {},  # standalone mako blocks
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

#######
# These things are from DA's source code. Since this should be lightweight,
# I don't want to directly include things from DA. We'll see if that works.
#
# Last updated: 1.7.7, 484736005270dd6107
#######

# All of the known dictionary keys: from docassemble/base/parse.py:2186, in Question.__init__
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
) + (  # things that are only present in tables, features, etc., i.e. non question blocks.
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
    yaml = _RuamelYAML()
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


def _seq_item_line(seq: Any, index: int) -> int:
    lc = getattr(seq, "lc", None)
    if lc is not None:
        item_getter = getattr(lc, "item", None)
        if callable(item_getter):
            try:
                line_info = item_getter(index)
            except (AttributeError, IndexError, KeyError, TypeError):
                line_info = None
            if isinstance(line_info, tuple) and len(line_info) >= 1:
                line = line_info[0]
                if isinstance(line, int):
                    return line + 1
    return _lc_line(seq)


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
        if key in modifier_keys:  # pragma: no branch
            continue
        if isinstance(value, str):
            return value
    return None


def _extract_names_from_python_expr(expr: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(expr)
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
        # Keep raw condition as a fallback for textual matching
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
        # Avoid prefix false positives like matching "foo.bar" inside "foo.bar2".
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
        tree = ast.parse(code)
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

        # The condition line itself is a guard context for references inside
        # the test expression (e.g., if showifdef("x") and x: ...).
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

    return max((depth(var) for var in adjacency.keys()), default=(0, None), key=lambda result: result[0])


_TAGGED_PDF_TRUE_RE = re.compile(
    r"tagged\s+pdf\s*:\s*(true|yes|1|on)\b",
    re.IGNORECASE,
)


def _detect_file_wide_tagged_pdf(full_content: str) -> bool:
    """Check raw YAML text for a file-wide ``tagged pdf: true`` setting.

    Uses a regex scan over each YAML document section to avoid a second
    full YAML parse pass.  A false positive is harmless — it only suppresses
    an accessibility warning.
    """
    for source_code in DOCUMENT_MATCH.split(full_content):
        source_code = normalize_yaml_document_for_parser(source_code)
        if _TAGGED_PDF_TRUE_RE.search(source_code):
            return True
    return False


def _validate_cross_document(
    full_content: str,
    current_path: Path,
    input_file: str | None,
    workspace_index: WorkspaceIndex,
) -> list[YAMLError]:
    from docassemble_lsp.core.definitions import (
        _event_helper_occurrences,
        _iter_block_scalar_regions,
    )  # lazy: definitions pulls in heavy modules not needed at module level
    from docassemble_lsp.core.python_modules import resolve_python_module_path
    from docassemble_lsp.core.python_paths import (
        docassemble_package_name,
        normalize_module_name,
    )

    def _module_path(value: str) -> Path | None:
        try:
            mname = normalize_module_name(value, current_path)
            if mname is not None:
                return resolve_python_module_path(mname, current_path, workspace_index)
        except Exception:
            logger.exception("Failed to resolve module path for %r", value)
        return None

    errors: list[YAMLError] = []
    lines = _document_lines(full_content)
    templates_dir = workspace_index.templates_dir_for(current_path)
    if templates_dir is None:
        templates_dir = templates_dir_for_path(current_path)
    parents = _precompute_parent_keys(full_content)
    own_package = docassemble_package_name(current_path) if current_path is not None else None

    for line_index, text in enumerate(lines):
        key_match = _KEY_VALUE_RE.match(text)
        if key_match is not None:
            key_name = key_match.group(2).strip()
            raw_value = key_match.group(3)
            value, _, _ = _clean_value_and_range(raw_value, key_match.start(3), key_match.end(3))
            if not value or ":" in value or value in _BLOCK_SCALAR_MARKERS:
                continue

            if key_name in _EVENT_REFERENCE_KEYS:
                if value not in workspace_index.all_event_names:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            name=value,
                        )
                    )
                continue

            if key_name == "usedefs":
                if value not in workspace_index.all_def_names:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_UNDEFINED_DEF,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            name=value,
                        )
                    )
                continue

            if key_name in _PYTHON_MODULE_REFERENCE_KEYS:
                # Only warn for missing modules in the current package.
                # External packages may not be checked out — that's normal.
                if own_package is not None:
                    mname = normalize_module_name(value, current_path)
                    if mname is not None and not mname.startswith(f"{own_package}.") and mname != own_package:
                        continue
                if _module_path(value) is None:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_MISSING_FILE,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            path=value,
                        )
                    )
                continue

            if key_name in _FILE_REFERENCE_KEYS or key_name in _FILE_REFERENCE_LIST_PARENTS:
                if key_name == "translations":
                    continue
                if ":" not in value:
                    resolved = (current_path.parent / value).resolve()
                    if not resolved.exists() and key_name in _ATTACHMENT_FILE_KEYS and templates_dir is not None:
                        resolved = (templates_dir / value).resolve()
                    if not resolved.exists():
                        code = (
                            MessageCode.CROSS_DOC_MISSING_TEMPLATE
                            if key_name in _ATTACHMENT_FILE_KEYS
                            else MessageCode.CROSS_DOC_MISSING_FILE
                        )
                        errors.append(
                            _yaml_error(
                                code=code,
                                line_number=line_index + 1,
                                file_name=input_file or str(current_path),
                                path=value,
                            )
                        )
                continue

        list_match = _LIST_ITEM_VALUE_RE.match(text)
        if list_match is not None:
            raw_value = list_match.group(2)
            value, _, _ = _clean_value_and_range(raw_value, list_match.start(2), list_match.end(2))
            if not value or ":" in value:
                continue
            parent = parents[line_index]

            if parent == "usedefs":
                if value not in workspace_index.all_def_names:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_UNDEFINED_DEF,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            name=value,
                        )
                    )
                continue

            if parent in _EVENT_REFERENCE_KEYS:
                if value not in workspace_index.all_event_names:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            name=value,
                        )
                    )
                continue

            if parent in _PYTHON_MODULE_REFERENCE_KEYS:
                # Only warn for missing modules in the current package.
                if own_package is not None:
                    mname = normalize_module_name(value, current_path)
                    if mname is not None and not mname.startswith(f"{own_package}.") and mname != own_package:
                        continue
                if _module_path(value) is None:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_MISSING_FILE,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            path=value,
                        )
                    )
                continue

            if parent in _FILE_REFERENCE_LIST_PARENTS or parent in _ATTACHMENT_FILE_KEYS:
                if parent == "translations":
                    continue
                resolved = (current_path.parent / value).resolve()
                if not resolved.exists() and parent in _ATTACHMENT_FILE_KEYS and templates_dir is not None:
                    resolved = (templates_dir / value).resolve()
                if not resolved.exists():
                    code = (
                        MessageCode.CROSS_DOC_MISSING_TEMPLATE
                        if parent in _ATTACHMENT_FILE_KEYS
                        else MessageCode.CROSS_DOC_MISSING_FILE
                    )
                    errors.append(
                        _yaml_error(
                            code=code,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            path=value,
                        )
                    )
                continue

    for region in _iter_block_scalar_regions(full_content):
        if region.key_name not in _PYTHON_BLOCK_KEYS:
            continue
        for occurrence in _event_helper_occurrences(region.text):
            if occurrence.name not in workspace_index.all_event_names:
                errors.append(
                    _yaml_error(
                        code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
                        line_number=region.content_start_line + occurrence.line + 1,
                        file_name=input_file or str(current_path),
                        name=occurrence.name,
                    )
                )

    for mako_region in _iter_mako_block_regions(full_content):
        if mako_region.is_expression:
            continue
        for occurrence in _event_helper_occurrences(mako_region.code_text):
            if occurrence.name not in workspace_index.all_event_names:
                content_before = full_content[: mako_region.content_start_offset]
                base_line = content_before.count("\n")
                errors.append(
                    _yaml_error(
                        code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
                        line_number=base_line + occurrence.line + 1,
                        file_name=input_file or str(current_path),
                        name=occurrence.name,
                    )
                )

    return errors


def find_errors_from_string(
    full_content: str,
    input_file: Optional[str] = None,
    runtime_options: Optional[RuntimeOptions] = None,
    _jinja_affected_sections: frozenset[int] | None = None,
    workspace_index: Optional[WorkspaceIndex] = None,
) -> list[YAMLError]:
    """Return list of YAMLError found in the given full_content string

    Args:
        full_content (str): Full YAML content as a string.
        _jinja_affected_sections: Internal — set of YAML document section
            indices (0-based) whose original source contained Jinja2 syntax.
            Type validators are skipped for those sections because rendered
            types may not reflect runtime values. Passed through from the
            ``# use jinja`` preprocessing branch.
    Returns:
        list[YAMLError]: List of YAMLError instances found in the content.
    """
    all_errors = []
    runtime_options = runtime_options or RuntimeOptions()

    if not input_file:
        input_file = "<string input>"

    # Pre-process Jinja2 templates before YAML parsing only when the file
    # explicitly opts in with '# use jinja' on the first line.
    if has_jinja_header(full_content):
        rendered, render_errors = preprocess_jinja(full_content, input_file=input_file)
        if render_errors:
            return [
                _yaml_error(
                    code=e.code,
                    line_number=e.line_number,
                    file_name=input_file,
                    err_str=e.message,
                )
                for e in render_errors
            ]
        # Strip the '# use jinja' header from the rendered output so the
        # recursive call does not re-enter this branch. Afterwards, remap
        # rendered line numbers back onto the original source lines.
        _, _sep, original_body = full_content.partition("\n")
        _, _sep, rendered_body = rendered.partition("\n")
        # Identify which YAML document sections (separated by ---) contained
        # Jinja2 syntax in the original source. Type validators are unreliable
        # for those sections because rendering can change types at runtime
        # (e.g. an include block rendered to None when a for-loop body is
        # empty). Sections without Jinja are still fully validated.
        original_sections = DOCUMENT_MATCH.split(original_body)
        jinja_affected: set[int] = set()
        for idx, section in enumerate(original_sections):
            if contains_jinja_syntax(section):
                jinja_affected.add(idx + 1)  # 1-based to match section_index in loop
        errors = find_errors_from_string(
            rendered_body,
            input_file=input_file,
            runtime_options=runtime_options,
            _jinja_affected_sections=frozenset(jinja_affected),
        )
        rendered_line_map = _map_rendered_lines_to_source_lines(
            original_body,
            rendered_body,
            source_start_line=2,
        )
        for err in errors:
            if err.code == MessageCode.YAML_PARSE_ERROR:
                problem_line = _extract_yaml_parse_problem_line(err.err_str)
                if problem_line is not None:
                    mapped_problem_line = rendered_line_map.get(problem_line, problem_line + 1)
                    err.line_number = mapped_problem_line
                    err.err_str = _rewrite_yaml_parse_error_lines(
                        err.err_str,
                        old_line=problem_line,
                        new_line=mapped_problem_line,
                    )
                    continue
            err.line_number = rendered_line_map.get(err.line_number, err.line_number + 1)
        return [error for error in errors if runtime_options.allows_code(error.code)]

    exclusive_keys = [key for key in types_of_blocks.keys() if types_of_blocks[key].get("exclusive", True)]
    yaml_parser = _make_yaml_parser()
    prior_conditional_fields: list[dict[str, Any]] = []
    line_number = 1
    section_index = 0

    file_wide_tagged_pdf = _detect_file_wide_tagged_pdf(full_content)
    accessibility_opts = dataclasses.replace(
        runtime_options.accessibility_options(),
        file_wide_tagged_pdf_enabled=file_wide_tagged_pdf,
    )
    for source_code in DOCUMENT_MATCH.split(full_content):
        section_index += 1
        lines_in_code = sum(source_line == "\n" for source_line in source_code)
        source_code = normalize_yaml_document_for_parser(source_code)
        try:
            doc = _with_line_metadata(yaml_parser.load(source_code))
        except Exception as errMess:
            if isinstance(errMess, DuplicateKeyError):
                # Extract just the key name from ruamel's verbose problem string:
                # 'found duplicate key "foo" with value ... (original value: ...)'
                key_match = re.match(r'found duplicate key "([^"]+)"', errMess.problem or "")
                key_name = key_match.group(1) if key_match else "unknown"
                dup_line = line_number
                if errMess.problem_mark is not None:
                    dup_line = line_number + errMess.problem_mark.line
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.YAML_DUPLICATE_KEY,
                        line_number=dup_line,
                        file_name=input_file,
                        key_name=key_name,
                    )
                )
            elif isinstance(errMess, MarkedYAMLError):
                if errMess.context_mark is not None:
                    errMess.context_mark.line += line_number - 1
                if errMess.problem_mark is not None:
                    errMess.problem_mark.line += line_number - 1
                local_problem_line = 1
                if errMess.context_mark is not None:
                    local_problem_line = errMess.context_mark.line - line_number + 2
                elif errMess.problem_mark is not None:
                    local_problem_line = errMess.problem_mark.line - line_number + 2
                problem_line = line_number
                if errMess.context_mark is not None:
                    problem_line = errMess.context_mark.line + 1
                elif errMess.problem_mark is not None:
                    problem_line = errMess.problem_mark.line + 1
                err_str = _format_missing_jinja_header_error(source_code, line_number=local_problem_line)
                if err_str is None:
                    err_str = _format_yaml_parse_error(errMess)
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.YAML_PARSE_ERROR,
                        line_number=problem_line,
                        file_name=input_file,
                        err_str=err_str,
                    )
                )
            else:
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.YAML_PARSE_ERROR,
                        line_number=line_number,
                        file_name=input_file,
                        error=str(errMess),
                    )
                )
            line_number += lines_in_code
            continue

        if doc is None:
            # Just YAML comments, that's fine
            line_number += lines_in_code
            continue
        if not isinstance(doc, dict):
            line_number += lines_in_code
            continue

        accessibility_findings = find_accessibility_findings(
            doc=doc,
            source_code=source_code,
            document_start_line=line_number,
            input_file=input_file,
            options=accessibility_opts,
        )
        for finding in accessibility_findings:
            all_errors.append(
                YAMLError(
                    err_str=finding.message,
                    line_number=finding.line_number,
                    file_name=input_file,
                    experimental=is_experimental_code(finding.code),
                    code=finding.code,
                )
            )

        doc_keys_lower = _lowercase_key_map(doc)
        non_meta_keys_lower = {
            key.lower() for key in doc.keys() if isinstance(key, str) and not _is_internal_metadata_key(key)
        }
        if non_meta_keys_lower == {"comment"}:
            # docassemble ignores comment-only blocks, but once another attribute
            # is present the block still needs a real question/directive type.
            pass
        else:
            any_types = [block for block in types_of_blocks.keys() if block in doc_keys_lower and block != "comment"]
            if len(any_types) == 0:
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.NO_POSSIBLE_TYPES,
                        line_number=line_number,
                        file_name=input_file,
                        document=doc,
                    )
                )
        posb_types = [block for block in exclusive_keys if block in doc_keys_lower]
        if len(posb_types) > 1:
            if len(posb_types) == 2 and posb_types[1] in (types_of_blocks[posb_types[0]].get("partners") or []):
                pass
            else:
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.TOO_MANY_TYPES,
                        line_number=line_number,
                        file_name=input_file,
                        possible_types=posb_types,
                    )
                )

        allowed_top_level_keys = _allowed_top_level_keys(doc_keys_lower)
        weird_keys = []
        for attr in doc.keys():
            if _is_internal_metadata_key(attr):
                continue
            if not isinstance(attr, str):
                # Non-string keys (e.g., bools) are not expected in DA interview files
                weird_keys.append(str(attr))
            elif attr.lower() not in allowed_top_level_keys:
                weird_keys.append(attr)
        if len(weird_keys) > 0:
            all_errors.append(
                _yaml_error(
                    code=MessageCode.UNKNOWN_KEYS,
                    line_number=line_number,
                    file_name=input_file,
                    keys=weird_keys,
                )
            )
        if "on change" in doc_keys_lower and len(non_meta_keys_lower) > 1:
            all_errors.append(
                _yaml_error(
                    code=MessageCode.ON_CHANGE_EXTRA_KEYS,
                    line_number=_absolute_document_line(line_number, _lc_key_line(doc, doc_keys_lower["on change"])),
                    file_name=input_file,
                )
            )
        if "require" in doc_keys_lower:
            require_key = doc_keys_lower["require"]
            require_value = doc.get(require_key)
            if isinstance(require_value, list):
                if "orelse" not in doc_keys_lower:
                    all_errors.append(
                        _yaml_error(
                            code=MessageCode.REQUIRE_ORELSE_MISSING,
                            line_number=_absolute_document_line(line_number, _lc_key_line(doc, require_key)),
                            file_name=input_file,
                        )
                    )
                else:
                    orelse_key = doc_keys_lower["orelse"]
                    if not isinstance(doc.get(orelse_key), Mapping):
                        all_errors.append(
                            _yaml_error(
                                code=MessageCode.REQUIRE_ORELSE_TYPE,
                                line_number=_absolute_document_line(line_number, _lc_key_line(doc, orelse_key)),
                                file_name=input_file,
                            )
                        )
        # Table key cross-validation: if any of table/rows/columns are present,
        # all three must be present (parser-backed).
        has_table = "table" in doc_keys_lower
        has_rows = "rows" in doc_keys_lower
        has_cols = "columns" in doc_keys_lower
        if (has_table or has_rows or has_cols) and not (has_table and has_rows and has_cols):
            table_key = doc_keys_lower.get("table") or doc_keys_lower.get("rows") or doc_keys_lower.get("columns")
            all_errors.append(
                _yaml_error(
                    code=MessageCode.TABLE_REQUIRED_KEYS,
                    line_number=_absolute_document_line(line_number, _lc_key_line(doc, table_key)),
                    file_name=input_file,
                )
            )

        # def/mako cross-validation: if either is present, both must be present.
        has_def = "def" in doc_keys_lower
        has_mako = "mako" in doc_keys_lower
        if (has_def or has_mako) and not (has_def and has_mako):
            present_key = "def" if has_def else "mako"
            missing_key = "mako" if has_def else "def"
            all_errors.append(
                _yaml_error(
                    code=MessageCode.DEF_MAKO_REQUIRED,
                    line_number=_absolute_document_line(line_number, _lc_key_line(doc, doc_keys_lower[present_key])),
                    file_name=input_file,
                    missing_key=missing_key,
                )
            )

        # Validate rows value is a string (Python expression) when present
        if has_rows:
            rows_key = doc_keys_lower["rows"]
            rows_value = doc.get(rows_key)
            if rows_value is not None and not isinstance(rows_value, str):
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.TABLE_ROWS_TYPE,
                        line_number=_absolute_document_line(line_number, _lc_key_line(doc, rows_key)),
                        file_name=input_file,
                    )
                )

        # Validate columns is a list when present
        if has_cols:
            cols_key = doc_keys_lower["columns"]
            cols_value = doc.get(cols_key)
            if cols_value is not None and not isinstance(cols_value, list):
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.TABLE_COLUMNS_TYPE,
                        line_number=_absolute_document_line(line_number, _lc_key_line(doc, cols_key)),
                        file_name=input_file,
                    )
                )
            elif isinstance(cols_value, list):
                for idx, col in enumerate(cols_value):
                    if not isinstance(col, Mapping):
                        all_errors.append(
                            _yaml_error(
                                code=MessageCode.TABLE_COLUMN_ITEM_TYPE,
                                line_number=_absolute_document_line(line_number, _seq_item_line(cols_value, idx)),
                                file_name=input_file,
                            )
                        )
                    else:
                        col_line = _seq_item_line(cols_value, idx)
                        if "header" in col and not isinstance(col["header"], str):
                            all_errors.append(
                                _yaml_error(
                                    code=MessageCode.TABLE_COLUMN_HEADER_TYPE,
                                    line_number=_absolute_document_line(line_number, col_line),
                                    file_name=input_file,
                                )
                            )
                        if "cell" in col and not isinstance(col["cell"], str):
                            all_errors.append(
                                _yaml_error(
                                    code=MessageCode.TABLE_COLUMN_CELL_TYPE,
                                    line_number=_absolute_document_line(line_number, col_line),
                                    file_name=input_file,
                                )
                            )

        # Data block cross-validation (parser-backed): when 'data' or 'data from code'
        # is present with 'variable name', validate shapes.
        has_data = "data" in doc_keys_lower
        if has_data and "variable name" in doc_keys_lower:
            data_key = doc_keys_lower["data"]
            data_value = doc.get(data_key)
            # Parser: when data is used with variable name, data must be a dict or list
            if data_value is not None and not isinstance(data_value, (Mapping, list)):
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.DATA_TYPE,
                        line_number=_absolute_document_line(line_number, _lc_key_line(doc, data_key)),
                        file_name=input_file,
                    )
                )
            # Parser: variable name must be plain text when used with data
            var_name_key = doc_keys_lower["variable name"]
            var_name_value = doc.get(var_name_key)
            if var_name_value is not None and not isinstance(var_name_value, str):
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.DATA_VARIABLE_NAME_TYPE,
                        line_number=_absolute_document_line(line_number, _lc_key_line(doc, var_name_key)),
                        file_name=input_file,
                    )
                )
            # Parser: use objects can be True, False, or 'objects'
            if "use objects" in doc_keys_lower:
                uo_key = doc_keys_lower["use objects"]
                uo_value = doc.get(uo_key)
                if uo_value is not None and not isinstance(uo_value, (bool, str)):
                    all_errors.append(
                        _yaml_error(
                            code=MessageCode.DATA_USE_OBJECTS_TYPE,
                            line_number=_absolute_document_line(line_number, _lc_key_line(doc, uo_key)),
                            file_name=input_file,
                        )
                    )

        # List collect + Mako label cross-validation (parser-backed):
        # When ``list collect`` is active, field labels must not contain Mako
        # templating, or else Docassemble will raise a runtime error.
        if "list collect" in doc_keys_lower and "fields" in doc_keys_lower:
            lc_key = doc_keys_lower["list collect"]
            lc_value = doc.get(lc_key)
            # Only flag when list collect is statically truthy
            # (True or a dict/Mapping).  Dynamic Python expressions cannot
            # be evaluated statically.
            if lc_value is True or isinstance(lc_value, Mapping):
                fields_key = doc_keys_lower["fields"]
                fields_value = doc.get(fields_key)
                if isinstance(fields_value, list):
                    for field_idx, field_item in enumerate(fields_value):
                        if not isinstance(field_item, Mapping):
                            continue
                        label_text: str | None = None
                        label_line: int | None = None
                        # Check explicit ``label`` key first
                        if "label" in field_item and isinstance(field_item["label"], str):
                            label_text = field_item["label"]
                            label_line = _lc_key_line(field_item, "label")
                        else:
                            # Check shorthand labels (first non-reserved key)
                            for key, value in field_item.items():
                                if (
                                    isinstance(key, str)
                                    and not _is_internal_metadata_key(key)
                                    and isinstance(value, str)
                                ):
                                    label_text = key
                                    label_line = _lc_key_line(field_item, key)
                                    break
                        if label_text is not None and label_line is not None and _contains_mako_syntax(label_text):
                            all_errors.append(
                                _yaml_error(
                                    code=MessageCode.LIST_COLLECT_LABEL_HAS_MAKO,
                                    line_number=_absolute_document_line(line_number, label_line),
                                    file_name=input_file,
                                    label=label_text,
                                )
                            )

        _run_type_validators = _jinja_affected_sections is None or section_index not in _jinja_affected_sections
        if _run_type_validators:
            for key in doc.keys():
                if not isinstance(key, str) or _is_internal_metadata_key(key):
                    continue
                lower_key = key.lower()
                if lower_key in big_dict and "type" in big_dict[lower_key]:
                    if lower_key == "fields":
                        test = big_dict[lower_key]["type"](doc[key], runtime_options=runtime_options)
                    else:
                        test = big_dict[lower_key]["type"](doc[key])
                    for err in test.errors:
                        err_msg, err_line, err_code = _normalize_validator_error(err)
                        mapped_line = _absolute_document_line(
                            line_number,
                            _relative_top_level_error_line(doc, key, err_line, err_code, source_code=source_code),
                        )
                        all_errors.append(
                            _yaml_error(
                                code=err_code,
                                err_str=err_msg,
                                line_number=mapped_line,
                                file_name=input_file,
                            )
                        )

        unmatched_refs = _find_unmatched_interview_order_references(doc, prior_conditional_fields)
        for field_var, ref_line in unmatched_refs:
            all_errors.append(
                _yaml_error(
                    code=MessageCode.INTERVIEW_ORDER_UNMATCHED_GUARD,
                    line_number=_absolute_document_line(line_number, _relative_value_line(doc, "code", ref_line)),
                    file_name=input_file,
                    field_var=field_var,
                )
            )

        nesting_depth, nesting_line = _max_screen_visibility_nesting_depth(doc)
        if nesting_depth > 2:
            all_errors.append(
                _yaml_error(
                    code=MessageCode.NESTED_VISIBILITY_LOGIC,
                    line_number=_absolute_document_line(line_number, nesting_line or _lc_line(doc)),
                    file_name=input_file,
                    depth=nesting_depth,
                )
            )

        prior_conditional_fields.extend(_extract_conditional_fields_from_doc(doc, line_number))

        line_number += lines_in_code

    if workspace_index is not None and input_file not in ("<memory>", "<string input>"):
        current_path = path_from_uri_or_path(input_file)
        if current_path and current_path.suffix in (".yml", ".yaml"):
            all_errors.extend(_validate_cross_document(full_content, current_path, input_file, workspace_index))

    return [error for error in all_errors if runtime_options.allows_code(error.code)]


def find_errors(
    input_file: str,
    runtime_options: Optional[RuntimeOptions] = None,
) -> list[YAMLError]:
    """Return list of YAMLError found in the given input_file

    If the file starts with the ``# use jinja`` header, the content is
    pre-processed through Jinja2 (with undefined variables rendered as empty
    strings) and the rendered output is then validated as normal YAML.

    Args:
        input_file (str): Path to the YAML file to check.

    Returns:
        list[YAMLError]: List of YAMLError instances found in the file.
    """
    with open(input_file, "r", encoding="utf-8") as f:
        full_content = f.read()

    return find_errors_from_string(
        full_content,
        input_file=input_file,
        runtime_options=runtime_options,
    )


def process_file(
    input_file,
    quiet: bool = False,
    display_path: str | None = None,
    show_experimental: bool = False,
    runtime_options: Optional[RuntimeOptions] = None,
    ignore_codes: frozenset[str] = frozenset(),
    format_on_success: bool = False,
    formatter_config: FormatterConfig | None = None,
    ok_reporter: Callable[[], None] | None = None,
    line_reporter: Callable[[str], None] | None = None,
) -> Literal["ok", "warning", "error", "skipped"]:
    """Process a single file and report its validation status.

    Args:
        input_file: Path to the YAML file to check.
        quiet: If True, suppress output for successful and skipped files.
            Errors are still printed.
        display_path: Optional path string to use in output instead of the
            full ``input_file`` path (e.g. a relative path).
        show_experimental: If True, prefix non-experimental errors with
            ``REAL ERROR:``. The default is False.
    Returns:
        A string indicating the result of processing:
        - "ok": The file was checked and no errors were found.
                - "warning": The file was checked and only warnings/conventions were found.
                - "error": The file was checked and one or more errors were found.
        - "skipped": The file was not checked because it matches a known
          pattern of files to ignore.
    """
    for dumb_da_file in [
        "pgcodecache.yml",
        "title_documentation.yml",
        "documentation.yml",
        "docstring.yml",
        "example-list.yml",
        "examples.yml",
    ]:
        if input_file.endswith(dumb_da_file):
            if not quiet:
                message = f"skipped: {display_path or input_file}"
                if line_reporter is not None:
                    line_reporter(message)
                else:
                    print(message)
            return "skipped"

    with open(input_file, "r", encoding="utf-8") as f:
        full_content = f.read()

    is_jinja = has_jinja_header(full_content)

    all_errors = find_errors_from_string(
        full_content,
        input_file=display_path or input_file,
        runtime_options=runtime_options,
    )
    all_errors = [err for err in all_errors if err.code is None or err.code.upper() not in ignore_codes]

    error_findings = [err for err in all_errors if err.severity == "error"]
    warning_findings = [err for err in all_errors if err.severity == "warning"]
    convention_findings = [err for err in all_errors if err.severity == "convention"]

    reformatted = False
    if format_on_success and not error_findings:
        formatted, changed, _ = format_yaml_string(
            full_content,
            config=formatter_config,
        )
        if changed:
            with open(input_file, "w", encoding="utf-8") as f:
                f.write(formatted)
            reformatted = True

    if len(all_errors) == 0:
        if not quiet:
            if reformatted:
                message = f"reformatted: {display_path or input_file}"
                if line_reporter is not None:
                    line_reporter(message)
                else:
                    print(message)
            elif ok_reporter is not None:
                ok_reporter()
            else:
                label = "ok (jinja)" if is_jinja else "ok"
                print(f"{label}: {display_path or input_file}")
        return "ok"

    jinja_note = " (jinja)" if is_jinja else ""

    if error_findings:
        header = f"errors ({len(error_findings)}){jinja_note}: {display_path or input_file}"
        if line_reporter is not None:
            line_reporter(header)
        else:
            print(header)
        for err in error_findings:
            print(f"  {err.format(show_experimental=show_experimental)}")

    if not quiet and warning_findings:
        header = f"warnings ({len(warning_findings)}){jinja_note}: {display_path or input_file}"
        if line_reporter is not None:
            line_reporter(header)
        else:
            print(header)
        for err in warning_findings:
            print(f"  {err.format(show_experimental=show_experimental)}")

    if not quiet and convention_findings:
        header = f"conventions ({len(convention_findings)}){jinja_note}: {display_path or input_file}"
        if line_reporter is not None:
            line_reporter(header)
        else:
            print(header)
        for err in convention_findings:
            print(f"  {err.format(show_experimental=show_experimental)}")

    if reformatted and not quiet:
        message = f"reformatted: {display_path or input_file}"
        if line_reporter is not None:
            line_reporter(message)
        else:
            print(message)

    if error_findings:
        return "error"
    return "warning"


def _build_arg_parser(*, require_files: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Docassemble YAML files",
    )
    parser.add_argument(
        "files",
        nargs="+" if require_files else "*",
        type=Path,
        help="YAML files or directories to validate (directories are searched recursively)",
    )
    parser.add_argument(
        "--check-all",
        action="store_true",
        help=(
            "Do not ignore default directories during recursive search "
            "(.git*, .github*, build, dist, node_modules, sources)"
        ),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Do not print the summary line after processing",
    )
    parser.add_argument(
        "--format-on-success",
        action="store_true",
        help="Format files that pass YAML validation",
    )
    parser.add_argument(
        "--convert-tabs-to-spaces",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=("When formatting, replace literal tab characters in YAML files with two spaces"),
    )
    parser.add_argument(
        "--ignore-codes",
        default="",
        help=('Comma-separated diagnostic codes to suppress, for example: "E410,E301"'),
    )
    parser.add_argument(
        "--show-experimental",
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Prefix non-experimental errors with "REAL ERROR:" (default: off)',
    )
    parser.add_argument(
        "--accessibility-error-on-widget",
        dest="accessibility_error_on_widgets",
        action="append",
        default=[],
        metavar="WIDGET",
        help=(
            "Treat a specific accessibility-sensitive widget as an error. "
            "Repeat to enable multiple widgets. Default: none"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    raw_argv = sys.argv[1:] if argv is None else argv
    bootstrap_parser = _build_arg_parser(require_files=False)
    bootstrap_args, _ = bootstrap_parser.parse_known_args(raw_argv)
    bootstrap_files = bootstrap_args.files or [Path.cwd()]
    config_cli_args = collect_dayaml_cli_args(bootstrap_files)

    parser = _build_arg_parser(require_files=False)
    args = parser.parse_args([*config_cli_args, *raw_argv])
    if not args.files:
        args.files = [Path.cwd()]

    ignore_codes = collect_dayaml_ignore_codes(args.files) | parse_ignore_codes(args.ignore_codes)
    runtime_options = RuntimeOptions(
        accessibility_error_on_widgets=frozenset(
            widget.strip().lower() for widget in args.accessibility_error_on_widgets if widget.strip()
        )
    )
    formatter_config = (
        FormatterConfig(convert_tabs_to_spaces=args.convert_tabs_to_spaces) if args.format_on_success else None
    )

    cwd = Path.cwd().resolve()

    def _display(file_path: Path) -> Path:
        resolved = file_path.resolve()
        try:
            return resolved.relative_to(cwd)
        except ValueError:
            pass
        return resolved

    yaml_files = collect_yaml_files(args.files, include_default_ignores=not args.check_all)
    if not yaml_files:
        print("No YAML files found.", file=sys.stderr)
        return 1

    files_ok = 0
    files_warning = 0
    files_error = 0
    files_skipped = 0
    progress = _ProgressOutput() if not args.quiet else None

    for input_file in yaml_files:
        status = process_file(
            str(input_file),
            quiet=args.quiet,
            display_path=str(_display(input_file)),
            show_experimental=args.show_experimental,
            runtime_options=runtime_options,
            ignore_codes=ignore_codes,
            format_on_success=args.format_on_success,
            formatter_config=formatter_config,
            ok_reporter=progress.dot if progress is not None else None,
            line_reporter=progress.line if progress is not None else None,
        )
        if status == "ok":
            files_ok += 1
        elif status == "warning":
            files_warning += 1
        elif status == "error":
            files_error += 1
        else:
            files_skipped += 1

    if not args.quiet and not args.no_summary:
        cast(_ProgressOutput, progress).finish()
        total = files_ok + files_warning + files_error + files_skipped
        print(
            f"Summary: {files_ok} ok, {files_warning} warnings, {files_error} errors, {files_skipped} skipped ({total} total)"
        )
    elif progress is not None:
        progress.finish()

    return 1 if files_error > 0 else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
