from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from docassemble_lsp.core.completion_rules import (
    CompletionScope,
    PropertyRule,
    SchemaMetadata,
)
from docassemble_lsp.core.definition_models import PythonCompletionTarget
from docassemble_lsp.core import field_keys
from docassemble_lsp.core.field_keys import BOOLEAN_DATATYPES
from docassemble_lsp.core.python_modules import VENDORED_MODULE_NAMES
from docassemble_lsp.core.python_navigation import resolve_python_completion_targets
from docassemble_lsp.core.python_paths import path_from_uri_or_path
from docassemble_lsp.core.schema_insert_text import contextualize_completion_candidates
from docassemble_lsp.core.schema_models import CompletionCandidate
from docassemble_lsp.core.schema_snippets import (
    shorthand_candidates as build_shorthand_candidates,
)
from docassemble_lsp.core.validation_config import RuntimeOptions
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_shared import _ATTACHMENT_FILE_KEYS, _LIST_ITEM_VALUE_RE

_VALUE_RE = re.compile(r"^(\s*)(?:-\s*)?([\w/-][\w /-]*?)\s*:\s*([^\s#]*)$")

ShowIfVariableCandidates = Callable[[str, int, str], list[CompletionCandidate]]
ButtonCommandCandidates = Callable[[str, int, str], list[CompletionCandidate]]
PropertyCandidateFilter = Callable[[list[CompletionCandidate], str, int, CompletionScope], list[CompletionCandidate]]
ShorthandSuppression = Callable[[str, int, CompletionScope], bool]


@dataclass(frozen=True, slots=True)
class CompletionContext:
    source: str
    line: int
    character: int
    uri_or_path: str | Path | None
    workspace_index: WorkspaceIndex
    metadata: SchemaMetadata
    scope: CompletionScope
    line_prefix: str
    show_if_variable_candidates: ShowIfVariableCandidates
    button_command_candidates: ButtonCommandCandidates
    filter_property_candidates: PropertyCandidateFilter
    should_suppress_shorthand: ShorthandSuppression
    current_field_datatype: str = ""
    runtime_options: RuntimeOptions | None = None
    indent: str = "  "


CompletionProvider = Callable[[CompletionContext], list[CompletionCandidate] | None]


@dataclass(frozen=True, slots=True)
class CompletionRegistry:
    providers: tuple[CompletionProvider, ...]

    @classmethod
    def default(cls) -> CompletionRegistry:
        return cls(
            providers=(
                python_completion_provider,
                _file_value_completion_provider,
                value_completion_provider,
                property_completion_provider,
            )
        )

    def candidates(self, context: CompletionContext) -> list[CompletionCandidate]:
        for provider in self.providers:
            candidates = provider(context)
            if candidates is not None:
                return candidates
        return []


def property_type(rule: PropertyRule) -> str:
    display_value_types = rule.display_value_types or rule.value_types
    return " | ".join(display_value_types) if display_value_types else "any"


def enum_values(rule: PropertyRule) -> list[str]:
    return list(rule.enum_values)


def property_documentation(prop_name: str, rule: PropertyRule) -> str | None:
    parts: list[str] = [f"**{prop_name}** `{property_type(rule)}`"]

    if rule.description:
        parts.append(rule.description)

    if rule.comment:
        url_match = re.search(r"https?://\S+", rule.comment)
        if url_match:
            parts.append(f"[Docassemble Documentation]({url_match.group(0)})")
        else:
            parts.append(rule.comment)

    return "\n\n".join(parts) if parts else None


def property_insert_text(prop_name: str, rule: PropertyRule) -> str:
    if rule.insert_kind == "object":
        return f"{prop_name}:\n  $0"
    if rule.insert_kind == "array":
        return f"{prop_name}:\n  - $0"
    if rule.insert_kind == "block_scalar":
        return f"{prop_name}: |\n  $0"
    return f"{prop_name}: $0"


def format_property_insert_text(prop_name: str, rule: PropertyRule, *, indent: str = "") -> str:
    """YAML key:value text for *rule*, with optional absolute *indent*.

    Unlike ``property_insert_text`` the result has no snippet placeholders,
    making it suitable for direct insertion (e.g. code-action fixes).
    """
    text = property_insert_text(prop_name, rule).replace("$0", "")
    if not indent:
        return text
    return "\n".join(f"{indent}{line}" for line in text.split("\n"))


_KEYWORD_SPACE_SUFFIX = frozenset(
    {
        "if",
        "elif",
        "for",
        "while",
        "except",
        "with",
        "def",
        "class",
        "return",
        "raise",
        "yield",
        "import",
        "from",
        "as",
        "async",
        "await",
        "lambda",
        "del",
        "global",
        "nonlocal",
        "assert",
        "and",
        "or",
        "not",
        "in",
        "is",
    }
)

_KEYWORD_COLON_SUFFIX = frozenset(
    {
        "else",
        "try",
        "finally",
    }
)


def python_insert_text(source: str, line: int, character: int, label: str) -> str:
    line_text = _line_at(source, line)
    if 0 < character <= len(line_text) and line_text[character - 1] == ":":
        if character == len(line_text) or line_text[character] != " ":
            return f" {label}"
    return label


def _line_at(source: str, line: int) -> str:
    lines = source.splitlines()
    if not lines:
        return ""
    if line < 0:
        return ""
    if line >= len(lines):
        return lines[-1]
    return lines[line]


def python_completion_provider(
    context: CompletionContext,
) -> list[CompletionCandidate] | None:
    python_targets = resolve_python_completion_targets(
        context.source,
        context.line,
        context.character,
        uri_or_path=context.uri_or_path,
        workspace_index=context.workspace_index,
    )
    if not python_targets:
        return None
    return [
        CompletionCandidate(
            label=target.label,
            insert_text=_keyword_insert_text(target)
            or python_insert_text(
                context.source,
                context.line,
                context.character,
                target.label,
            ),
            display_kind="keyword" if target.detail == "keyword" else "class" if target.detail == "exception" else None,
            documentation=target.documentation,
            text_edit_range=target.text_edit_range,
        )
        for target in python_targets
    ]


def _keyword_insert_text(target: PythonCompletionTarget) -> str | None:
    if target.detail != "keyword":
        return None
    label = target.label
    if label in _KEYWORD_COLON_SUFFIX:
        return f"{label}:"
    if label in _KEYWORD_SPACE_SUFFIX:
        return f"{label} "
    return None


def _value_supports_block_scalar(context: CompletionContext, key: str) -> bool:
    if context.scope != "fields_item":
        return True
    compatible = field_keys.FIELD_KEY_COMPATIBLE_DATATYPES.get(key)
    if compatible is None:
        return True
    return context.current_field_datatype in compatible


def _should_offer_block_scalar_pipe(prop: PropertyRule, partial_value: str) -> bool:
    return (
        "string" in prop.value_types
        and prop.insert_kind == "scalar"
        and (partial_value == "" or partial_value.startswith("|"))
    )


def value_completion_provider(
    context: CompletionContext,
) -> list[CompletionCandidate] | None:
    scope_properties = context.metadata.scoped_properties[context.scope]
    value_match = _VALUE_RE.match(context.line_prefix)
    if value_match:
        key = value_match.group(2)
        partial_value = value_match.group(3)
        show_if_variable_candidates = context.show_if_variable_candidates(
            context.source,
            context.line,
            context.line_prefix,
        )
        if show_if_variable_candidates:
            return show_if_variable_candidates
        prop = scope_properties.get(key) or context.metadata.all_known_properties.get(key)
        if prop is not None:
            values = enum_values(prop)
            candidates: list[CompletionCandidate] = [
                CompletionCandidate(
                    label=value,
                    insert_text=value,
                    is_value=True,
                )
                for value in values
                if partial_value.lower() in value.lower()
            ]

            if _should_offer_block_scalar_pipe(prop, partial_value) and _value_supports_block_scalar(context, key):
                candidates.append(
                    CompletionCandidate(
                        label="|",
                        insert_text="|\n  $0",
                        is_snippet=True,
                        is_value=True,
                        detail="Block scalar (multi-line string)",
                    )
                )

            candidates.sort(
                key=lambda c: (
                    0 if c.label == "|" else 1,
                    0 if c.label.lower().startswith(partial_value.lower()) else 1,
                    c.label,
                )
            )

            # For ``datatype:``, also include custom datatypes from
            # CustomDataType subclasses discovered during workspace indexing.
            if key == "datatype":
                for custom_name in sorted(context.workspace_index.all_custom_datatype_names):
                    if partial_value.lower() in custom_name.lower() and not any(
                        c.label == custom_name for c in candidates
                    ):
                        candidates.append(
                            CompletionCandidate(
                                label=custom_name,
                                insert_text=custom_name,
                                is_value=True,
                            )
                        )

            # For ``generic object:``, include DAObject subclass names from
            # workspace indexing.
            if key == "generic object":
                for class_name in sorted(context.workspace_index.all_da_object_subclass_names):
                    if partial_value.lower() in class_name.lower() and not any(
                        c.label == class_name for c in candidates
                    ):
                        candidates.append(
                            CompletionCandidate(
                                label=class_name,
                                insert_text=class_name,
                                is_value=True,
                            )
                        )

            # For ``default:`` inside a fields_item, suggest True/False
            # when the field's datatype is a boolean type.
            if (
                context.scope == "fields_item"
                and key == "default"
                and context.current_field_datatype in BOOLEAN_DATATYPES
            ):
                for value in ("True", "False"):
                    if partial_value.lower() in value.lower() and not any(c.label == value for c in candidates):
                        candidates.append(
                            CompletionCandidate(
                                label=value,
                                insert_text=value,
                                is_value=True,
                            )
                        )

            return candidates

        button_command_candidates = context.button_command_candidates(context.source, context.line, context.line_prefix)
        if button_command_candidates:
            return button_command_candidates
    return None


def property_completion_provider(
    context: CompletionContext,
) -> list[CompletionCandidate]:
    if not re.fullmatch(r"\s*(?:-\s*)?[\w/.-][\w /.-]*", context.line_prefix) and not re.fullmatch(
        r"\s*(?:-\s*)?", context.line_prefix
    ):
        return []

    scope_properties = context.metadata.scoped_properties[context.scope]
    property_candidates = [
        CompletionCandidate(
            label=name,
            insert_text=property_insert_text(name, prop),
            documentation=property_documentation(name, prop),
            uses_snippet_text=True,
            trigger_suggest=(bool(prop.enum_values) or ("string" in prop.value_types and prop.insert_kind == "scalar")),
        )
        for name, prop in sorted(scope_properties.items())
    ]
    property_candidates = context.filter_property_candidates(
        property_candidates,
        context.source,
        context.line,
        context.scope,
    )

    shorthand_candidates: list[CompletionCandidate] = []
    suppress_shorthand = context.should_suppress_shorthand(context.source, context.line, context.scope)
    if not suppress_shorthand and (
        context.runtime_options is None or not context.runtime_options.convention_enabled("C102")
    ):
        shorthand_candidates = build_shorthand_candidates(context.scope, context.source, context.line)

    result = contextualize_completion_candidates(
        shorthand_candidates + property_candidates,
        indent_unit=context.indent,
    )
    return result


def _list_item_partial_value(context: CompletionContext) -> str:
    """Extract the partial value typed after ``- `` in a list item."""
    match = _LIST_ITEM_VALUE_RE.match(context.line_prefix)
    if match:
        return match.group(2).strip()
    return context.line_prefix.strip()


def _file_value_completion_provider(
    context: CompletionContext,
) -> list[CompletionCandidate] | None:
    scope = context.scope

    if scope in ("include_item", "translations_item", "objects_from_file_item"):
        return _complete_file_paths(context)

    if scope in ("modules_item", "imports_item"):
        return _complete_module_names(context)

    if scope == "reset_item":
        return _complete_variable_names(context)

    if scope == "order_item":
        return _complete_block_ids(context)

    # Check for attachment template file keys (key-value pattern, not list items).
    if context.workspace_index.template_file_names:
        value_match = _VALUE_RE.match(context.line_prefix)
        if value_match is not None and value_match.group(2) in _ATTACHMENT_FILE_KEYS:
            return _complete_attachment_template_paths(context)

    return None


def _complete_file_paths(
    context: CompletionContext,
) -> list[CompletionCandidate] | None:
    scope = context.scope
    partial = _list_item_partial_value(context)
    if ":" in partial:
        return None  # package-qualified — let the user type it manually

    current_path = path_from_uri_or_path(context.uri_or_path) if context.uri_or_path else None
    current_dir = current_path.parent if current_path else None

    # Determine allowed extensions.
    valid_suffixes: tuple[str, ...]
    if scope == "translations_item":
        valid_suffixes = (".xlsx", ".xlf", ".xliff")
    elif scope == "objects_from_file_item":
        valid_suffixes = (".yml", ".yaml", ".json")
    else:
        valid_suffixes = (".yml", ".yaml")

    candidates: list[CompletionCandidate] = []
    for source in context.workspace_index.yaml_sources.sources:
        if source.path.suffix.lower() not in valid_suffixes:
            continue
        # Compute relative path from current document directory.
        rel: str | None = None
        if current_dir is not None:
            rel = os.path.relpath(source.path, current_dir)
        if rel is None:
            rel = source.path.name
        if partial.lower() not in rel.lower():
            continue
        # Deduplicate by normalized path.
        if any(c.label == rel for c in candidates):
            continue
        candidates.append(CompletionCandidate(label=rel, insert_text=rel, is_value=True))

    if candidates:
        candidates.sort(
            key=lambda c: (
                0 if c.label.lower().startswith(partial.lower()) else 1,
                c.label,
            )
        )
    return candidates if candidates else None


def _complete_module_names(
    context: CompletionContext,
) -> list[CompletionCandidate] | None:
    # Only activate when a workspace context exists (document path is set).
    # Without it, the snippet-based templates are more helpful.
    if not context.uri_or_path:
        return None

    partial = _list_item_partial_value(context)
    if ":" in partial:
        return None  # package-qualified file ref

    # Strip leading dot for relative module references so that
    # e.g. ".func" matches workspace stem "functions".
    is_relative = partial.startswith(".")
    match_partial = partial.lstrip(".") if is_relative else partial

    seen: set[str] = set()
    candidates: list[CompletionCandidate] = []

    # Vendored modules are never applicable in modules: blocks.
    if not is_relative and context.scope != "modules_item":
        for mod in VENDORED_MODULE_NAMES:
            if match_partial.lower() in mod.lower() and mod not in seen:
                seen.add(mod)
                candidates.append(CompletionCandidate(label=mod, insert_text=mod, is_value=True))

    # Workspace Python module paths.
    text_edit_range: tuple[int, int] | None = None
    for mod_path in sorted(context.workspace_index.all_module_paths):
        if text_edit_range is None:
            # Compute lazily: TextEdit range from start of list-item value
            # to cursor, bypassing VS Code's word-boundary heuristics for ".".
            list_match = _LIST_ITEM_VALUE_RE.match(context.line_prefix)
            value_start_col = list_match.start(2) if list_match else context.character
            text_edit_range = (value_start_col, context.character)
        name = mod_path.stem
        if name == "__init__":
            name = mod_path.parent.name
        if name and match_partial.lower() in name.lower() and name not in seen:
            seen.add(name)
            dotted = f".{name}"
            candidates.append(
                CompletionCandidate(
                    label=dotted,
                    insert_text=dotted,
                    is_value=True,
                    text_edit_range=text_edit_range,
                )
            )

    candidates.sort(
        key=lambda c: (
            0
            if c.label.lower().startswith(partial.lower())
            or (match_partial and c.label.startswith(".") and c.label[1:].lower().startswith(match_partial.lower()))
            else 1,
            c.label,
        )
    )
    return candidates if candidates else None


def _complete_variable_names(
    context: CompletionContext,
) -> list[CompletionCandidate] | None:
    partial = _list_item_partial_value(context)
    seen: set[str] = set()
    candidates: list[CompletionCandidate] = []
    wi = context.workspace_index
    for name in wi.all_field_var_names:
        if name in seen:
            continue
        if partial.lower() in name.lower():
            seen.add(name)
            candidates.append(CompletionCandidate(label=name, insert_text=name, is_value=True))
    for name in wi.all_def_names:
        if name in seen:
            continue
        if partial.lower() in name.lower():
            seen.add(name)
            candidates.append(CompletionCandidate(label=name, insert_text=name, is_value=True))
    candidates.sort(key=lambda c: (0 if c.label.lower().startswith(partial.lower()) else 1, c.label))
    return candidates if candidates else None


def _complete_block_ids(context: CompletionContext) -> list[CompletionCandidate] | None:
    partial = _list_item_partial_value(context)
    candidates: list[CompletionCandidate] = []
    for bid in context.workspace_index.all_block_ids:
        if partial.lower() in bid.lower():
            candidates.append(CompletionCandidate(label=bid, insert_text=bid, is_value=True))
    if candidates:
        candidates.sort(
            key=lambda c: (
                0 if c.label.lower().startswith(partial.lower()) else 1,
                c.label,
            )
        )
    return candidates if candidates else None


_ATTACHMENT_KEY_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "docx template file": (".docx",),
    "pdf template file": (".pdf",),
    "rtf template file": (".rtf",),
    "template file": (".tex",),
    "docx reference file": (".docx",),
    "content file": (".md", ".txt", ".html"),
    "initial yaml": (".yml", ".yaml"),
    "additional yaml": (".yml", ".yaml"),
}


def _complete_attachment_template_paths(
    context: CompletionContext,
) -> list[CompletionCandidate] | None:
    value_match = _VALUE_RE.match(context.line_prefix)
    if not value_match:
        return None
    key = value_match.group(2)
    partial_value = value_match.group(3)
    template_names = context.workspace_index.template_file_names
    if not template_names:
        return None

    valid_extensions = _ATTACHMENT_KEY_EXTENSIONS.get(key)

    candidates: list[CompletionCandidate] = []
    for name in sorted(template_names):
        # Exclude hidden files (e.g. .DS_Store) and Office temp files (e.g. ~$letter.docx)
        if name.startswith((".", "~$")):
            continue
        # Exclude files whose extension doesn't match the key
        if valid_extensions is not None and not name.lower().endswith(valid_extensions):
            continue
        if partial_value.lower() in name.lower():
            candidates.append(CompletionCandidate(label=name, insert_text=name, is_value=True))

    if candidates:
        candidates.sort(
            key=lambda c: (
                0 if c.label.lower().startswith(partial_value.lower()) else 1,
                c.label,
            )
        )
    return candidates if candidates else None
