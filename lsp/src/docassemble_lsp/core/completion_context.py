from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from docassemble_lsp.core.completion_registry import CompletionContext
from docassemble_lsp.core.completion_rules import CompletionScope, SchemaMetadata
from docassemble_lsp.core.field_keys import (
    BOOLEAN_DATATYPES,
    FIELD_ITEM_KNOWN_KEYS_LOWER,
    FIELD_KEY_BLOCKED_DATATYPES,
    FIELD_KEY_COMPATIBLE_DATATYPES,
    FIELDS_ITEM_FILE_BOOLEAN_KEYS,
    FIELDS_ITEM_FILE_COMPLEX_KEYS,
    FIELDS_ITEM_FILE_STRING_KEYS,
    FILE_LIKE_DATATYPES,
    MULTIPLE_CHOICE_DATATYPES,
    MULTIPLE_CHOICE_INPUT_TYPES,
)
from docassemble_lsp.core.schema_models import CompletionCandidate
from docassemble_lsp.core.validation import types_of_blocks
from docassemble_lsp.core.validation_config import RuntimeOptions
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_shared import _line_indent

_KEY_RE = re.compile(r"^\s*(?:-\s*)?([\w/-][\w /-]*?)\s*:")
_VALUE_RE = re.compile(r"^(\s*)(?:-\s*)?([\w/-][\w /-]*?)\s*:\s*([^\s#]*)$")
_TOP_LEVEL_KEY_RE = re.compile(r"^([^:#][^:]*?)\s*:")
_LIST_ITEM_RE = re.compile(r"^(\s*)-\s*(.*)$")
_LIST_ITEM_KEY_RE = re.compile(r"^(\s*)-\s*([\w/-][\w /-]*?)\s*:\s*(.*?)\s*$")
_LIST_ITEM_ANY_KEY_RE = re.compile(r"^(\s*)-\s*([^:#][^:]*?)\s*:\s*(.*?)\s*$")
_REVIEW_ITEM_KEYS = {
    "label",
    "action",
    "button",
    "css class",
    "field",
    "fields",
    "help",
    "note",
    "html",
    "raw html",
    "show if",
}
_BUTTON_COMMANDS = (
    "continue",
    "restart",
    "refresh",
    "signin",
    "register",
    "exit",
    "logout",
    "exit_logout",
    "leave",
    "new_session",
)
_FILE_FIELD_KEYS = frozenset(
    FIELDS_ITEM_FILE_STRING_KEYS
    + FIELDS_ITEM_FILE_COMPLEX_KEYS
    + FIELDS_ITEM_FILE_BOOLEAN_KEYS
    + ("file css class",)
)

# Datatype values that parse.py remaps at parse time
_DATATYPE_REMAPPING: dict[str, str] = {
    "radio": "text",
    "combobox": "text",
    "datalist": "text",
    "dropdown": "text",
    "pulldown": "text",
    "ajax": "text",
    "area": "text",
    "hidden": "text",
    "mlarea": "ml",
}

# Mutual visibility modifier conflicts (parser raises DASourceError)
# Includes same-modifier-pair conflicts AND JS ↔ non-JS cross conflicts.
# Same-group cross-modifier conflicts (e.g., show if + enable if) are NOT
# included because they depend on code-ness, which is unknown at completion time.
_JS_MODIFIERS = frozenset({"js show if", "js hide if", "js enable if", "js disable if"})
_NON_JS_MODIFIERS = frozenset({"show if", "hide if", "enable if", "disable if"})

_VISIBILITY_CONFLICTS: dict[str, frozenset[str]] = {
    "show if": frozenset({"hide if"} | _JS_MODIFIERS),
    "hide if": frozenset({"show if"} | _JS_MODIFIERS),
    "enable if": frozenset({"disable if"} | _JS_MODIFIERS),
    "disable if": frozenset({"enable if"} | _JS_MODIFIERS),
    "js show if": frozenset({"js hide if"} | _NON_JS_MODIFIERS),
    "js hide if": frozenset({"js show if"} | _NON_JS_MODIFIERS),
    "js enable if": frozenset({"js disable if"} | _NON_JS_MODIFIERS),
    "js disable if": frozenset({"js enable if"} | _NON_JS_MODIFIERS),
}

_VISIBILITY_MODIFIER_KEYS = frozenset(_VISIBILITY_CONFLICTS)

# Promotion rules for fields_item scope.
# Each tuple: (condition_fn(entries, keys), promoted_keys)
# All matching rules contribute their promoted keys into a single sort.
_TOP_LEVEL_PROMOTIONS: list[tuple[Callable[[set[str]], bool], frozenset[str]]] = [
    (
        lambda keys: "mako" in keys and "def" not in keys,
        frozenset({"def"}),
    ),
    (
        lambda keys: "def" in keys and "mako" not in keys,
        frozenset({"mako"}),
    ),
]

_FIELD_PROMOTIONS: list[
    tuple[Callable[[dict[str, Any], set[str]], bool], frozenset[str]]
] = [
    (
        lambda entries, keys: (
            entries.get("input type", "").lower() == "ajax" and "action" not in keys
        ),
        frozenset({"action"}),
    ),
    (
        lambda entries, keys: "label" in keys and "field" not in keys,
        frozenset({"field"}),
    ),
    (
        lambda entries, keys: "field" in keys and "label" not in keys,
        frozenset({"label"}),
    ),
    (
        lambda entries, keys: (
            (
                (entries.get("datatype") or "").lower() in MULTIPLE_CHOICE_DATATYPES
                or (entries.get("input type") or "").lower()
                in MULTIPLE_CHOICE_INPUT_TYPES
            )
            and "choices" not in keys
            and "code" not in keys
        ),
        frozenset({"choices", "code"}),
    ),
]

_TOP_LEVEL_EXCLUSIVE_TYPES = {
    key.lower(): {partner.lower() for partner in (config.get("partners") or [])}
    for key, config in types_of_blocks.items()
    if config.get("exclusive", True)
}

_SIGNATURE_ONLY_TOP_LEVEL_KEYS = frozenset({"required", "pen color"})
_LIST_ITEM_SCOPES = {
    "metadata_author_item",
    "attachment_field_variable_item",
    "sections_item",
    "table_column_item",
    "objects_item",
    "objects_from_file_item",
    "on_change_item",
    "include_item",
    "imports_item",
    "modules_item",
    "translations_item",
    "reset_item",
    "order_item",
    "review_item",
    "review_field_item",
    "attachment_item",
    "fields_item",
    "action_button_item",
    "need_item",
    "terms_item",
}


def build_completion_context(
    source: str,
    line: int,
    character: int,
    *,
    uri_or_path: str | Path | None,
    workspace_index: WorkspaceIndex,
    metadata: SchemaMetadata,
    runtime_options: RuntimeOptions | None = None,
) -> CompletionContext:
    scope = completion_scope(source, line, character)
    scope_entries = _current_scope_entries(source, line, scope)
    current_field_datatype = (
        (scope_entries.get("datatype") or "").lower() if scope_entries else ""
    )

    return CompletionContext(
        source=source,
        line=line,
        character=character,
        uri_or_path=uri_or_path,
        workspace_index=workspace_index,
        metadata=metadata,
        scope=scope,
        line_prefix=line_at(source, line)[:character],
        show_if_variable_candidates=lambda callback_source, callback_line, line_prefix: (
            _show_if_variable_candidates(
                callback_source,
                callback_line,
                line_prefix,
                metadata=metadata,
            )
        ),
        button_command_candidates=_button_command_candidates,
        filter_property_candidates=lambda candidates, source, line, scope: (
            _filter_property_candidates(
                candidates, source, line, scope, existing_entries=scope_entries
            )
        ),
        should_suppress_shorthand=_should_suppress_shorthand,
        current_field_datatype=current_field_datatype,
        runtime_options=runtime_options,
        indent=" " * runtime_options.indent if runtime_options is not None else "  ",
    )


def _current_document_bounds(source: str, line: int) -> tuple[int, int]:
    lines = source.splitlines()
    if not lines:
        return (0, 0)

    bounded_line = min(max(line, 0), len(lines) - 1)
    start = 0
    for index in range(bounded_line, -1, -1):
        if lines[index].strip() == "---":
            start = index + 1
            break

    end = len(lines)
    for index in range(bounded_line + 1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break

    return (start, end)


def _current_document_top_level_keys(source: str, line: int) -> set[str]:
    lines = source.splitlines()
    if not lines:
        return set()

    start, end = _current_document_bounds(source, line)
    keys: set[str] = set()
    for text in lines[start:end]:
        if _line_indent(text) != 0:
            continue
        match = _TOP_LEVEL_KEY_RE.match(text)
        if match is not None:
            keys.add(match.group(1).strip())
    return keys


def _button_command_candidates(
    source: str, line: int, line_prefix: str
) -> list[CompletionCandidate]:
    value_match = _VALUE_RE.match(line_prefix)
    if value_match is None:
        return []
    ancestors = _ancestor_keys_reverse(source, line)
    nearest = ancestors[0] if ancestors else None
    if nearest != "buttons":
        return []

    if "field" in _current_document_top_level_keys(source, line):
        return []

    partial_value = value_match.group(3)
    return [
        CompletionCandidate(label=value, insert_text=value, is_value=True)
        for value in _BUTTON_COMMANDS
        if value.startswith(partial_value)
    ]


def _nearest_ancestor_key_line(source: str, line: int, target_key: str) -> int | None:
    lines = source.splitlines()
    if not lines or line < 0:
        return None

    bounded_line = min(line, len(lines) - 1)
    current_indent = _line_indent(lines[bounded_line])
    search_indent = current_indent + 1

    for index in range(bounded_line - 1, -1, -1):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        indent = _line_indent(text)
        if indent >= search_indent:
            continue

        match = _KEY_RE.match(text)
        if match is None:
            continue

        key = match.group(1)
        search_indent = indent
        if key == target_key:
            return index

    return None


def _extract_field_var_from_item(
    lines: list[str],
    start_line: int,
    *,
    item_indent: int,
    block_end: int,
    known_field_keys: set[str],
) -> str | None:
    list_item_match = _LIST_ITEM_ANY_KEY_RE.match(lines[start_line])
    if list_item_match is not None:
        key = list_item_match.group(2).strip()
        value = _normalize_scalar_value(list_item_match.group(3))
        if key == "field":
            return value or None
        if key not in known_field_keys and value:
            return value
        if key in known_field_keys:
            return None

    child_key_indent = item_indent + 2
    for index in range(start_line + 1, block_end):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        indent = _line_indent(text)
        if indent <= item_indent:
            break
        if indent != child_key_indent:
            continue

        value_match = _VALUE_RE.match(text)
        if value_match is None:
            continue
        if value_match.group(2) != "field":
            continue

        value = _normalize_scalar_value(value_match.group(3))
        if value:
            return value

    return None


def _current_screen_field_variables(
    source: str, line: int, metadata: SchemaMetadata
) -> list[str]:
    lines = source.splitlines()
    if not lines:
        return []

    fields_line = _nearest_ancestor_key_line(source, line, "fields")
    if fields_line is None:
        return []

    document_start, document_end = _current_document_bounds(source, line)
    if not (document_start <= fields_line < document_end):
        return []

    fields_indent = _line_indent(lines[fields_line])
    item_indent = fields_indent + 2
    current_item = _enclosing_list_item_start(source, line)
    known_field_keys = set(metadata.fields_item)
    variables: list[str] = []
    seen: set[str] = set()

    for index in range(fields_line + 1, document_end):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        indent = _line_indent(text)
        if indent <= fields_indent:
            break
        if indent != item_indent or _LIST_ITEM_RE.match(text) is None:
            continue
        if current_item is not None and index == current_item[0]:
            continue

        field_var = _extract_field_var_from_item(
            lines,
            index,
            item_indent=item_indent,
            block_end=document_end,
            known_field_keys=known_field_keys,
        )
        if field_var and field_var not in seen:
            seen.add(field_var)
            variables.append(field_var)

    return variables


def _show_if_variable_candidates(
    source: str,
    line: int,
    line_prefix: str,
    *,
    metadata: SchemaMetadata,
) -> list[CompletionCandidate]:
    value_match = _VALUE_RE.match(line_prefix)
    if value_match is None or value_match.group(2) != "variable":
        return []

    ancestors = _ancestor_keys_reverse(source, line)
    nearest = ancestors[0] if ancestors else None
    if nearest not in {"show if", "hide if", "enable if", "disable if"}:
        return []

    partial_value = value_match.group(3)
    return [
        CompletionCandidate(
            label=value,
            insert_text=value,
            is_value=True,
        )
        for value in _current_screen_field_variables(source, line, metadata)
        if value.startswith(partial_value)
    ]


def line_at(source: str, line: int) -> str:
    lines = source.splitlines()
    if not lines:
        return ""
    if line < 0:
        return ""
    if line >= len(lines):
        return lines[-1]
    return lines[line]


def _is_list_item_context(source: str, line: int) -> bool:
    return bool(re.match(r"^\s*-\s", line_at(source, line)))


def _normalize_scalar_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


def _enclosing_list_item_start(source: str, line: int) -> tuple[int, int] | None:
    lines = source.splitlines()
    if not lines:
        return None

    bounded_line = min(max(line, 0), len(lines) - 1)
    current_indent = _line_indent(lines[bounded_line])

    for index in range(bounded_line, -1, -1):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        match = _LIST_ITEM_RE.match(text)
        if match is None:
            continue

        indent = len(match.group(1))
        if indent > current_indent:
            continue

        return (index, indent)

    return None


def _enclosing_list_key(source: str, line: int) -> str | None:
    item_start = _enclosing_list_item_start(source, line)
    if item_start is None:
        return None

    ancestors = _ancestor_keys_reverse(source, item_start[0])
    return ancestors[0] if ancestors else None


def _is_existing_list_item_continuation(source: str, line: int) -> bool:
    if _is_list_item_context(source, line):
        return False

    item_start = _enclosing_list_item_start(source, line)
    if item_start is None:
        return False

    return _line_indent(line_at(source, line)) > item_start[1]


def _current_list_item_entries(source: str, line: int) -> dict[str, str | None]:
    lines = source.splitlines()
    item_start = _enclosing_list_item_start(source, line)
    if item_start is None:
        return {}

    start_line, item_indent = item_start
    item_key_indent = item_indent + 2
    entries: dict[str, str | None] = {}

    for index in range(start_line, min(line, len(lines))):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        if index == start_line:
            list_item_match = _LIST_ITEM_KEY_RE.match(text)
            if list_item_match is not None:
                entries[list_item_match.group(2)] = _normalize_scalar_value(
                    list_item_match.group(3)
                )
            continue

        if _line_indent(text) != item_key_indent:
            continue

        key_match = _KEY_RE.match(text)
        if key_match is None:
            continue

        value_match = _VALUE_RE.match(text)
        entries[key_match.group(1)] = _normalize_scalar_value(
            value_match.group(3) if value_match else None
        )

    return entries


def _nearest_mapping_anchor_line(source: str, line: int) -> int | None:
    lines = source.splitlines()
    if not lines or line <= 0:
        return None

    current_indent = _line_indent(lines[min(line, len(lines) - 1)])
    search_indent = current_indent

    for index in range(min(line - 1, len(lines) - 1), -1, -1):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        indent = _line_indent(text)
        if indent >= search_indent:
            continue

        if _KEY_RE.match(text) is None:
            continue

        return index

    return None


def _current_mapping_entries(source: str, line: int) -> dict[str, str | None]:
    lines = source.splitlines()
    if not lines:
        return {}

    anchor_line = _nearest_mapping_anchor_line(source, line)
    if anchor_line is None:
        return {}

    anchor_indent = _line_indent(lines[anchor_line])
    child_indent = anchor_indent + 2
    entries: dict[str, str | None] = {}

    for index in range(anchor_line + 1, min(line, len(lines))):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        indent = _line_indent(text)
        if indent <= anchor_indent:
            break
        if indent != child_indent:
            continue

        key_match = _KEY_RE.match(text)
        if key_match is None:
            continue

        value_match = _VALUE_RE.match(text)
        entries[key_match.group(1)] = _normalize_scalar_value(
            value_match.group(3) if value_match else None
        )

    return entries


def _current_top_level_entries(source: str, line: int) -> dict[str, str | None]:
    lines = source.splitlines()
    if not lines:
        return {}

    start, end = _current_document_bounds(source, line)
    entries: dict[str, str | None] = {}
    for index in range(start, min(line, end)):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue
        if _line_indent(text) != 0:
            continue

        key_match = _KEY_RE.match(text)
        if key_match is None:
            continue

        value_match = _VALUE_RE.match(text)
        entries[key_match.group(1)] = _normalize_scalar_value(
            value_match.group(3) if value_match else None
        )

    return entries


def _current_scope_entries(
    source: str, line: int, scope: CompletionScope
) -> dict[str, str | None]:
    if scope == "top_level" or _line_indent(line_at(source, line)) == 0:
        return _current_top_level_entries(source, line)

    if scope in _LIST_ITEM_SCOPES and _is_list_item_context(source, line):
        return {}

    if scope in _LIST_ITEM_SCOPES and _is_existing_list_item_continuation(source, line):
        return _current_list_item_entries(source, line)

    mapping_entries = _current_mapping_entries(source, line)
    return mapping_entries


def _effective_datatype(datatype: str) -> str:
    """Compute the effective runtime datatype after parse.py remapping.

    The docassemble parser remaps certain datatype values at parse time
    (e.g. ``radio`` → ``input type: radio, datatype: text``).  This helper
    applies the same remapping so that completion filters use the effective
    datatype, matching runtime behavior.
    """
    return _DATATYPE_REMAPPING.get(datatype, datatype)


def _filter_property_candidates(
    candidates: list[CompletionCandidate],
    source: str,
    line: int,
    scope: CompletionScope,
    existing_entries: dict[str, str | None] | None = None,
) -> list[CompletionCandidate]:
    if existing_entries is None:
        existing_entries = _current_scope_entries(source, line, scope)

    if not existing_entries:
        if scope == "top_level":
            return [
                candidate
                for candidate in candidates
                if candidate.label not in _SIGNATURE_ONLY_TOP_LEVEL_KEYS
            ]
        if scope == "fields_item":
            elevated = sorted(
                candidates, key=lambda c: (c.label not in {"label", "field"}, c.label)
            )
            result = [c for c in elevated if c.label not in _FILE_FIELD_KEYS]
            if _enclosing_list_key(source, line) == "fields":
                result = [c for c in result if c.label != "action"]
            return result
        return candidates

    existing_keys = set(existing_entries)

    if scope != "fields_item":
        filtered = [
            candidate
            for candidate in candidates
            if candidate.label not in existing_keys
        ]
        if scope == "show_if_modifier":
            if "code" in existing_keys:
                filtered = [
                    candidate
                    for candidate in filtered
                    if candidate.label not in {"variable", "is"}
                ]
            elif existing_keys & {"variable", "is"}:
                filtered = [
                    candidate for candidate in filtered if candidate.label != "code"
                ]
        if scope == "top_level":
            if "signature" not in existing_keys:
                filtered = [
                    candidate
                    for candidate in filtered
                    if candidate.label not in _SIGNATURE_ONLY_TOP_LEVEL_KEYS
                ]
            active_exclusive = {
                key.lower()
                for key in existing_keys
                if key.lower() in _TOP_LEVEL_EXCLUSIVE_TYPES
            }
            if active_exclusive:
                filtered = [
                    candidate
                    for candidate in filtered
                    if candidate.label.lower() not in _TOP_LEVEL_EXCLUSIVE_TYPES
                    or all(
                        candidate.label.lower() == active_key
                        or candidate.label.lower()
                        in _TOP_LEVEL_EXCLUSIVE_TYPES[active_key]
                        for active_key in active_exclusive
                    )
                ]
            promoted_top: set[str] = set()
            for top_cond, top_keys in _TOP_LEVEL_PROMOTIONS:
                if top_cond(existing_keys):
                    promoted_top.update(top_keys)
            if promoted_top:
                filtered = sorted(
                    filtered, key=lambda c: (c.label not in promoted_top, c.label)
                )
        return filtered

    declared_datatype = (existing_entries.get("datatype") or "").lower()
    input_type = (existing_entries.get("input type") or "").lower()
    effective_datatype = _effective_datatype(declared_datatype)
    file_context = declared_datatype in FILE_LIKE_DATATYPES or bool(
        existing_keys & _FILE_FIELD_KEYS
    )

    # --- Promotion: collect promoted keys from all matching rules ---
    promoted: set[str] = set()
    for condition, promoted_keys in _FIELD_PROMOTIONS:
        if condition(existing_entries, existing_keys):
            promoted.update(promoted_keys)

    if promoted:
        candidates = sorted(
            candidates, key=lambda c: (c.label not in promoted, c.label)
        )

    # --- Detect shorthand label pattern (e.g. - Name: user.name) ---
    # Any key not in FIELD_ITEM_KNOWN_KEYS_LOWER is treated as a shorthand
    # label/value pair, matching parse.py's behavior.  This means a typo in a
    # known key name will also suppress field/label completions until corrected
    # — this is intentional.
    has_shorthand = bool(existing_keys - FIELD_ITEM_KNOWN_KEYS_LOWER)
    field_filtered: list[CompletionCandidate] = []
    for candidate in candidates:
        if candidate.label in existing_keys:
            continue
        if candidate.label in _FILE_FIELD_KEYS and not file_context:
            continue
        if has_shorthand and candidate.label in ("field", "label"):
            continue

        # --- address autocomplete requires field to end in .address ---
        if candidate.label == "address autocomplete":
            field_value = (existing_entries.get("field") or "").lower().strip()
            if not field_value.endswith(".address"):
                continue

        # --- Datatype-based restriction checks ---
        # Generic compatible/blocked checks use the *effective* datatype
        # (accounting for parse.py remapping like radio → text).
        compatible = FIELD_KEY_COMPATIBLE_DATATYPES.get(candidate.label)
        if compatible is not None and effective_datatype not in compatible:
            continue
        blocked = FIELD_KEY_BLOCKED_DATATYPES.get(candidate.label)
        if blocked is not None and effective_datatype in blocked:
            continue

        # Special-case checks use the *declared* datatype (the literal
        # value the user wrote) because they depend on the YAML value,
        # not the post-remap runtime value.
        if candidate.label == "object labeler" and not declared_datatype.startswith(
            "object"
        ):
            continue
        if (
            candidate.label == "rows"
            and declared_datatype not in {"area", "multiselect", "object_multiselect"}
            and input_type != "area"
        ):
            continue

        # --- Mutual visibility modifier exclusion ---
        if candidate.label in _VISIBILITY_MODIFIER_KEYS:
            conflicted = _VISIBILITY_CONFLICTS.get(candidate.label, frozenset())
            if existing_keys & conflicted:
                continue

        # --- Input-type-based restriction checks ---
        if input_type == "ajax" and candidate.label in ("choices", "code"):
            continue
        if input_type == "hidden" and candidate.label in _FILE_FIELD_KEYS:
            continue

        # --- Boolean datatypes: choices/code are silently ignored at runtime ---
        if declared_datatype in BOOLEAN_DATATYPES and candidate.label in (
            "choices",
            "code",
        ):
            continue

        # --- trigger at is only meaningful with ajax input type ---
        if candidate.label == "trigger at" and input_type != "ajax":
            continue

        # --- action is only valid in fields: when input type is ajax ---
        if (
            candidate.label == "action"
            and input_type != "ajax"
            and _enclosing_list_key(source, line) == "fields"
        ):
            continue

        field_filtered.append(candidate)

    return field_filtered


def _should_suppress_shorthand(source: str, line: int, scope: CompletionScope) -> bool:
    return bool(_current_scope_entries(source, line, scope))


def _is_at_fields_item_key_level(source: str, line: int) -> bool:
    cursor_indent = _line_indent(line_at(source, line))
    item_start = _enclosing_list_item_start(source, line)
    if item_start is None:
        return False
    enclosing = _enclosing_list_key(source, line)
    if enclosing not in {"fields", "choices", "buttons", "dropdown", "combobox"}:
        return False
    return cursor_indent == item_start[1] + 2


def _ancestor_keys_reverse(source: str, line: int) -> list[str]:
    lines = source.splitlines()
    if not lines or line <= 0:
        return []

    current_indent = _line_indent(lines[min(line, len(lines) - 1)])
    search_indent = current_indent
    ancestors: list[str] = []

    for index in range(min(line - 1, len(lines) - 1), -1, -1):
        text = lines[index]
        if re.fullmatch(r"\s*(#.*)?", text):
            continue

        indent = _line_indent(text)
        if indent >= search_indent:
            continue

        match = _KEY_RE.match(text)
        if match:
            ancestors.append(match.group(1))
            search_indent = indent

    return ancestors


def completion_scope(source: str, line: int, character: int) -> CompletionScope:
    del character
    ancestors = _ancestor_keys_reverse(source, line)
    nearest = ancestors[0] if ancestors else None
    parent = ancestors[1] if len(ancestors) > 1 else None
    document_top_level_keys = _current_document_top_level_keys(source, line)

    if nearest == "twitter" and parent == "social":
        return "metadata_social_twitter_block"
    if nearest == "og" and parent == "social":
        return "metadata_social_og_block"
    if nearest == "social" and parent == "metadata":
        return "metadata_social_block"
    if nearest == "authors" and parent == "metadata":
        return "metadata_author_item"
    if nearest == "metadata" and parent is None:
        return "metadata_block"
    if nearest == "metadata" and parent in {
        "attachment",
        "attachments",
        "attachment options",
    }:
        return "attachment_metadata_block"
    if nearest == "fields" and any(
        key in {"attachment", "attachments"} for key in ancestors[1:]
    ):
        return "attachment_fields_block"
    if nearest in {"field variables", "raw field variables"} and any(
        key in {"attachment", "attachments"} for key in ancestors[1:]
    ):
        return "attachment_field_variable_item"
    if nearest == "objects" and _is_list_item_context(source, line):
        return "objects_item"
    if nearest == "objects from file" and _is_list_item_context(source, line):
        return "objects_from_file_item"
    if nearest == "on change":
        return "on_change_item"
    if nearest == "include" and _is_list_item_context(source, line):
        return "include_item"
    if nearest == "imports" and _is_list_item_context(source, line):
        return "imports_item"
    if nearest == "modules" and _is_list_item_context(source, line):
        return "modules_item"
    if nearest == "translations" and _is_list_item_context(source, line):
        return "translations_item"
    if nearest == "reset" and _is_list_item_context(source, line):
        return "reset_item"
    if nearest == "order" and _is_list_item_context(source, line):
        return "order_item"
    if nearest == "sections" or parent == "sections":
        return "sections_item"
    if "table" in document_top_level_keys and (
        nearest == "columns" or parent == "columns"
    ):
        return "table_column_item"
    if nearest in {"terms", "auto terms"} and _is_list_item_context(source, line):
        return "terms_item"
    if nearest in {
        "show if",
        "hide if",
        "enable if",
        "disable if",
    } and not _is_at_fields_item_key_level(source, line):
        return "show_if_modifier"
    if nearest == "features":
        return "features_block"
    if nearest == "default screen parts":
        return "default_screen_parts_block"
    if nearest == "list collect":
        return "list_collect_block"
    if nearest in {
        "default validation messages",
        "validation messages",
    } and not _is_at_fields_item_key_level(source, line):
        return "validation_messages_block"
    if (
        nearest in {"field", "fields"}
        and "review" in ancestors[1:]
        and _is_list_item_context(source, line)
    ):
        return "review_field_item"
    if (
        nearest not in _REVIEW_ITEM_KEYS
        and "review" in ancestors[1:]
        and _is_list_item_context(source, line)
    ):
        return "review_field_item"
    if nearest == "review":
        return "review_item"
    if parent in {"image sets", "images"}:
        return "image_set_block"
    if nearest == "attachment options":
        return "attachment_options_block"
    if nearest == "segment":
        return "segment_block"
    if nearest == "interview help":
        return "interview_help_block"
    if nearest == "help" and parent is None:
        return "help_block"
    if nearest == "address autocomplete" and not _is_at_fields_item_key_level(
        source, line
    ):
        return "address_autocomplete_block"
    if nearest in {"attachment", "attachments"}:
        return "attachment_item"
    if nearest == "grid" and not _is_at_fields_item_key_level(source, line):
        return "grid_block"
    if nearest == "item grid" and not _is_at_fields_item_key_level(source, line):
        return "item_grid_block"
    if nearest in {"choices", "buttons", "dropdown", "combobox"}:
        return "fields_item"
    if nearest == "fields" and parent not in {"attachment", "attachments"}:
        return "fields_item"
    enclosing_list_key = _enclosing_list_key(source, line)
    if enclosing_list_key in {"choices", "buttons", "dropdown", "combobox"}:
        return "fields_item"
    if enclosing_list_key == "fields" and parent not in {"attachment", "attachments"}:
        return "fields_item"
    if enclosing_list_key == "action buttons":
        return "action_button_item"
    if nearest == "action buttons":
        return "action_button_item"
    if enclosing_list_key in {"terms", "auto terms"}:
        return "terms_item"
    if enclosing_list_key == "need":
        return "need_item"
    if nearest == "need":
        return "need_item"
    if ancestors:
        return "unknown_nested"
    return "top_level"
