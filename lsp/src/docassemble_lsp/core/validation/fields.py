"""Field-level diagnostic rules (E401-E536) extracted from the validation monolith.

This module consolidates:

- Field item validators (``DAFields``, ``DAPythonVar``, ``ObjectsAttrType``)
- Field modifier validators (``JSShowIf``, ``ShowIf``)
- Field value validators (``AcceptFieldValue``, ``ValidationCode``)
- Generic building blocks used by the above (``MakoText``, ``PythonText``, etc.)
- Shared constants and helpers
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from typing import Any

import esprima  # type: ignore[import-untyped]
from mako.exceptions import CompileException, SyntaxException  # type: ignore[import-untyped]
from mako.template import Template as MakoTemplate  # type: ignore[import-untyped]

from docassemble_lsp.core.field_keys import (
    FIELD_ITEM_KNOWN_KEYS,
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
from docassemble_lsp.core.field_validators import _validator_error as _validator_error
from docassemble_lsp.core.line_helpers import (
    _is_internal_metadata_key,
    _lc_key_line,
    _lc_line,
    _relative_value_line,
    _safe_ast_parse,
)
from docassemble_lsp.core.messages import MessageCode
from docassemble_lsp.core.validation_config import RuntimeOptions

# ---------------------------------------------------------------------------
# Shared regex constants
# ---------------------------------------------------------------------------

_IDENTIFIER_RE = re.compile(r"[A-Za-z_]\w*")
_SIMPLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_]\w*$")
_JS_VAL_RE = re.compile(r"""val\s*\(\s*["']([^"']+)["']\s*\)""")

# Ensure that if there's a space in the str, it's between quotes.
space_in_str = re.compile("^[^ ]*['\"].* .*['\"][^ ]*$")

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

_FIELD_PRESENTATION_KEYS = FIELDS_ITEM_NOTE_KEYS

# Docassemble bracket commands that require content after the command name.
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
_BRACKET_COMMAND_RE = re.compile(r"\[([A-Z][A-Z_]+)\s*([^\]]*)\]")

# Mako syntax patterns used to detect templating in field labels.
_MAKO_SYNTAX_RE = re.compile(r"<%|\$\{|% if|% for|% while|##")

# ---------------------------------------------------------------------------
# Shared type / helpers
# ---------------------------------------------------------------------------

# ValidatorError is a 3-tuple of (error_message, line_number, message_code)
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
        raise TypeError(
            f"Validator error message must be a string; got {type(err_msg).__name__}: {err!r}"
        )
    if not isinstance(err_line, int):
        raise TypeError(
            f"Validator error line number must be an int; got {type(err_line).__name__}: {err!r}"
        )
    if not isinstance(err_code, str):
        raise TypeError(
            f"Validator error code must be a string; got {type(err_code).__name__}: {err!r}"
        )
    return (err_msg, err_line, err_code)


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
        while candidate.endswith("]") and "[" in candidate:
            candidate = candidate[: candidate.rfind("[")].strip()
            if candidate:
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


_DOCASSEMBLE_RESERVED_NAMES: frozenset[str] = frozenset(
    {
        "_internal",
        "nav",
        "url_args",
        "role_needed",
        "session_local",
        "device_local",
        "user_local",
        "role",
        "speak_text",
        "track_location",
        "multi_user",
        "menu_items",
        "allow_cron",
        "incoming_email",
        "role_event",
        "cron_hourly",
        "cron_daily",
        "cron_weekly",
        "cron_monthly",
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
    return (
        "." not in varname
        and "[" not in varname
        and varname in _DOCASSEMBLE_RESERVED_NAMES
    )


def _invalid_field_variable_name(varname: Any) -> bool:
    if not isinstance(varname, str):
        return True
    if re.search(r"[\n\r\(\)\{\}\*\^\#]", varname):
        return True
    try:
        tree = _safe_ast_parse(varname)
    except SyntaxError:
        return True
    return any(isinstance(node, _ILLEGAL_VARIABLE_AST_NODES) for node in ast.walk(tree))


def _contains_mako_syntax(text: str) -> bool:
    return bool(_MAKO_SYNTAX_RE.search(text))


def _scan_bracket_markup_errors(text: str) -> list[ValidatorError]:
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


# ---------------------------------------------------------------------------
# Generic string/content validators
# ---------------------------------------------------------------------------


class MakoText:
    """A string that will be run through a Mako template from DA. Needs to have valid Mako template."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, str):
            self.errors = [_validator_error(MessageCode.YAML_STRING_TYPE, value=x)]
            return
        try:
            self.template = MakoTemplate(
                x, strict_undefined=True, input_encoding="utf-8"
            )
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


class MakoMarkdownText(MakoText):
    """A string that will be run through a Mako template, then through a markdown formatter."""

    def __init__(self, x):
        super().__init__(x)
        if isinstance(x, str):
            self.errors.extend(_scan_bracket_markup_errors(x))


class PythonText:
    """A full multiline python script. Should have valid python syntax."""

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
            _safe_ast_parse(x)
        except SyntaxError as ex:
            lineno = ex.lineno or 1
            msg = ex.msg or str(ex)
            self.errors = [
                _validator_error(MessageCode.PYTHON_SYNTAX_ERROR, lineno, message=msg)
            ]


# ---------------------------------------------------------------------------
# Field value validators
# ---------------------------------------------------------------------------


class AcceptFieldValue:
    """Validates the ``accept`` modifier on a Docassemble file-upload field."""

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
            tree = _safe_ast_parse(x.strip(), mode="eval")
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
        if not (
            isinstance(tree.body, ast.Constant) and isinstance(tree.body.value, str)
        ):
            self.errors = [
                (
                    f"{self._HINT}. Got a {type(tree.body).__name__} expression instead of a string literal.",
                    1,
                    MessageCode.PYTHON_SYNTAX_ERROR,
                )
            ]


class ValidationCode(PythonText):
    """Validator for question-level ``validation code``."""

    def __init__(self, x):
        super().__init__(x)
        if self.errors:
            return
        try:
            tree = _safe_ast_parse(x)
        except SyntaxError:
            return
        calls_validation_error = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "validation_error":
                    calls_validation_error = True
                    break
        if not calls_validation_error:
            has_assignment = any(
                isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign))
                for n in ast.walk(tree)
            )
            has_define_call = any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "define"
                for n in ast.walk(tree)
            )
            has_expr_call = any(
                isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                for n in ast.walk(tree)
            )
            has_raise_or_assert = any(
                isinstance(n, (ast.Raise, ast.Assert)) for n in ast.walk(tree)
            )
            if (
                has_assignment or has_define_call or has_expr_call
            ) and not has_raise_or_assert:
                return
            self.errors.append(
                _validator_error(MessageCode.VALIDATION_CODE_MISSING_VALIDATION_ERROR)
            )


# ---------------------------------------------------------------------------
# Simple field-level validators
# ---------------------------------------------------------------------------


class DAPythonVar:
    """Things that need to be defined as a docassemble var, i.e. abc or x.y['a']."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, str):
            self.errors = [_validator_error(MessageCode.PYTHON_VAR_TYPE, value=x)]
        elif " " in x and not space_in_str.search(x):
            self.errors = [_validator_error(MessageCode.PYTHON_VAR_WHITESPACE, value=x)]


class ObjectsAttrType:
    """Validator for top-level ``objects`` block values."""

    def __init__(self, x):
        self.errors = []
        if not (isinstance(x, list) or isinstance(x, dict)):
            self.errors = [_validator_error(MessageCode.OBJECTS_BLOCK_TYPE, value=x)]


# ---------------------------------------------------------------------------
# Field-modifier validators
# ---------------------------------------------------------------------------


class JSShowIf:
    """Validator for js show if/hide if/enable if/disable if field modifiers."""

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
                    if (
                        isinstance(callee, dict)
                        and callee.get("type") == "Identifier"
                        and callee.get("name") == "val"
                    ):
                        val_calls.append(node)
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
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
                if self.screen_variables and not self._references_screen_variable(
                    var_name
                ):
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
                bad_arg = (
                    first_arg.get("raw")
                    or first_arg.get("name")
                    or first_arg.get("type", "<unknown>")
                )
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
    """Validator for show if field modifier (non-js variants)."""

    def __init__(self, x, context=None):
        self.errors = []
        self.context = context or {}

        if isinstance(x, str):
            if ":" not in x and " " not in x:
                pass
            elif x.startswith("variable:") or x.startswith("code:"):
                self.errors.append(
                    _validator_error(MessageCode.SHOW_IF_MALFORMED, value=x)
                )
        elif isinstance(x, dict):
            if "variable" in x:
                pass
            elif "code" in x:
                code_block = x.get("code")
                if not isinstance(code_block, str):
                    self.errors.append(_validator_error(MessageCode.SHOW_IF_CODE_TYPE))
                else:
                    try:
                        _safe_ast_parse(code_block)
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


# ---------------------------------------------------------------------------
# DAFields — the main field-section validator
# ---------------------------------------------------------------------------


class DAFields:
    """Validator for ``fields`` blocks (both list and single-dict form)."""

    object_field_keys = frozenset(FIELD_OBJECT_KEYS)
    modifier_keys = frozenset(FIELD_MODIFIER_KEYS)
    mako_keys = frozenset(FIELD_MAKO_KEYS)
    js_modifier_keys = FIELD_JS_MODIFIER_KEYS
    py_modifier_keys = FIELD_PY_MODIFIER_KEYS
    _reserved_field_keys = FIELD_ITEM_KNOWN_KEYS

    def __init__(self, x, runtime_options: RuntimeOptions | None = None):
        self.errors = []
        self.has_dynamic_fields_code = False
        self.runtime_options = runtime_options or RuntimeOptions()
        if isinstance(x, dict):
            content_keys = {
                key for key in x.keys() if not _is_internal_metadata_key(key)
            }
            if content_keys == {"code"}:
                if not isinstance(x.get("code"), str):
                    self.errors = [
                        _validator_error(
                            MessageCode.FIELDS_CODE_TYPE,
                            value_type=type(x.get("code")).__name__,
                        )
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
            if isinstance(key, str) and key in self._reserved_field_keys:
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
            and key not in self._reserved_field_keys
        ]

    def _is_shorthand_label_key(self, field_item, field_key):
        if not isinstance(field_item, dict):
            return False
        if (
            isinstance(field_key, str) and field_key in self._reserved_field_keys
        ) or _is_internal_metadata_key(field_key):
            return False
        if "field" in field_item or "label" in field_item:
            return False
        return isinstance(field_item.get(field_key), str)

    def _validate_field_target(self, field_item, target_key, *, label_key=None):
        target_value = field_item.get(target_key)
        if not isinstance(target_value, str):
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_TARGET_NOT_PLAIN_TEXT,
                    self._value_line_for(field_item, target_key),
                )
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
        presentation_keys = [
            key for key in _FIELD_PRESENTATION_KEYS if key in field_item
        ]
        if len(presentation_keys) > 1:
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_PRESENTATION_KEY_CONFLICT,
                    self._key_line_for(field_item, presentation_keys[1]),
                )
            )

        if "label" in field_item and "field" not in field_item:
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_ITEM_MISSING_TARGET,
                    self._key_line_for(field_item, "label"),
                )
            )

        input_type = field_item.get("input type")
        if (
            "field" in field_item
            and "label" not in field_item
            and input_type != "hidden"
        ):
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_ITEM_MISSING_LABEL,
                    self._key_line_for(field_item, "field"),
                )
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
            self._validate_field_target(
                field_item, shorthand_keys[0], label_key=shorthand_keys[0]
            )

    def _validate_field_item_configuration(self, field_item):
        dt_validator = FieldDatatypeValidator(field_item)
        for err in dt_validator.errors:
            self.errors.append(err)
        choice_validator = FieldChoiceValidator(field_item)
        for err in choice_validator.errors:
            self.errors.append(err)

        datatype = field_item.get("datatype")
        datatype_normalized = (
            datatype.strip().lower() if isinstance(datatype, str) else None
        )

        if "exclude" in field_item and isinstance(field_item["exclude"], Mapping):
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_EXCLUDE_INVALID_FORMAT,
                    self._key_line_for(field_item, "exclude"),
                )
            )

        if (
            datatype_normalized
            in {"object", "object_radio", "object_multiselect", "object_checkboxes"}
            and "default" in field_item
            and not isinstance(field_item["default"], (list, str))
        ):
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_DEFAULT_INVALID_FORMAT,
                    self._key_line_for(field_item, "default"),
                )
            )

    def _validate_python_modifier(
        self, modifier_key, modifier_value, field_item, screen_variables
    ):
        def references_screen_variable(var_expr):
            if not isinstance(var_expr, str):
                return False
            candidates = _variable_candidates(var_expr)
            if any(candidate in screen_variables for candidate in candidates):
                return True
            for candidate in candidates:
                if candidate.startswith("x.") and any(
                    screen_var.endswith("." + candidate.split(".", 1)[1])
                    for screen_var in screen_variables
                ):
                    return True
            for screen_var in screen_variables:
                if screen_var.startswith("x.") and any(
                    candidate.endswith("." + screen_var.split(".", 1)[1])
                    for candidate in candidates
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
                if (
                    modifier_key == "show if"
                    and isinstance(code_text, str)
                    and not validator.errors
                ):
                    same_screen_refs = self._find_screen_variable_references_in_code(
                        code_text, screen_variables
                    )
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
        elif isinstance(modifier_value, str) and ":" not in modifier_value:
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
            tree = _safe_ast_parse(code_text)
        except SyntaxError:
            return set()

        name_refs = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        matches = set()
        for screen_var in screen_variables:
            if _SIMPLE_IDENTIFIER_RE.match(screen_var) and screen_var in name_refs:
                matches.add(screen_var)
                continue
            # For dotted/indexed vars, require explicit textual reference.
            if screen_var in code_text:
                matches.add(screen_var)
        return matches

    def _validate_condition_and_validation_keys(
        self, field_item: dict[str, Any]
    ) -> None:
        cond_validator = FieldConditionValidator(field_item)
        for err in cond_validator.errors:
            self.errors.append(err)

    def _validate_object_field_choices(self, field_item):
        datatype = field_item.get("datatype")
        is_object_style_field = (
            isinstance(datatype, str) and datatype.lower().startswith("object")
        ) or any(key in field_item for key in self.object_field_keys)
        if not is_object_style_field:
            return

        choices_value = field_item.get("choices")
        if isinstance(choices_value, Mapping) and (
            {key for key in choices_value.keys() if not _is_internal_metadata_key(key)}
            == {"code"}
        ):
            self.errors.append(
                _validator_error(
                    MessageCode.OBJECT_FIELD_CHOICES_CODE_DICT,
                    self._key_line_for(field_item, "choices"),
                )
            )

    def _field_item_has_content_target(self, field_item: dict[str, Any]) -> bool:
        content_keys = {
            key
            for key in field_item.keys()
            if isinstance(key, str) and not _is_internal_metadata_key(key)
        }
        if content_keys == {"code"}:
            return True
        if content_keys & {"note", "html", "raw html"}:
            return True
        return self._extract_field_name(field_item) is not None

    def _validate_field_modifiers(self, fields_list):
        self.has_dynamic_fields_code = any(
            isinstance(field_item, dict)
            and "code" in field_item
            and len(
                {
                    key
                    for key in field_item.keys()
                    if key != "code" and not _is_internal_metadata_key(key)
                }
            )
            == 0
            for field_item in fields_list
        )
        screen_variables = set()
        for field_item in fields_list:
            if not isinstance(field_item, dict):
                continue
            field_var_name = self._extract_field_name(field_item)
            if field_var_name and not _invalid_field_variable_name(
                field_var_name.strip()
            ):
                screen_variables.add(field_var_name)

        for index, field_item in enumerate(fields_list):
            if not isinstance(field_item, dict):
                self.errors.append(
                    _validator_error(
                        MessageCode.FIELD_ITEM_MUST_BE_DICT,
                        _seq_item_line(fields_list, index),
                    )
                )
                continue

            self._validate_field_item_structure(field_item)
            self._validate_field_item_configuration(field_item)

            if not self._field_item_has_content_target(field_item):
                if "label" not in field_item and "field" not in field_item:
                    self.errors.append(
                        _validator_error(
                            MessageCode.FIELD_ITEM_MISSING_TARGET,
                            self._line_for(field_item),
                        )
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
                self._validate_python_modifier(
                    py_key, field_item[py_key], field_item, screen_variables
                )

    def _validate_field_js_modifiers(self, field_item, screen_variables):
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
                    self.errors.append(
                        (
                            err_msg,
                            self._value_line_for(field_item, js_key, err_line),
                            err_code,
                        )
                    )


# ---------------------------------------------------------------------------
# Helpers used by fields.py internally
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "AcceptFieldValue",
    "DAFields",
    "DAPythonVar",
    "FieldChoiceValidator",
    "FieldConditionValidator",
    "FieldDatatypeValidator",
    "JSShowIf",
    "MakoMarkdownText",
    "MakoText",
    "ObjectsAttrType",
    "PythonText",
    "ShowIf",
    "ValidationCode",
    "ValidatorError",
    "_CONDITIONAL_MODIFIERS",
    "_DOCASSEMBLE_RESERVED_NAMES",
    "_FIELD_PRESENTATION_KEYS",
    "_HIDE_STYLE_MODIFIERS",
    "_IDENTIFIER_RE",
    "_ILLEGAL_VARIABLE_AST_NODES",
    "_JS_VAL_RE",
    "_MAKO_SYNTAX_RE",
    "_SHOW_STYLE_MODIFIERS",
    "_SIMPLE_IDENTIFIER_RE",
    "_BRACKET_COMMANDS_REQUIRING_CONTENT",
    "_BRACKET_COMMAND_RE",
    "_contains_mako_syntax",
    "_invalid_field_variable_name",
    "_is_docassemble_reserved_name",
    "_normalize_validator_error",
    "_scan_bracket_markup_errors",
    "_seq_item_line",
    "_variable_candidates",
    "_validator_error",
    "space_in_str",
]
