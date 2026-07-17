from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from docassemble_lsp.core.completion_context import (
    build_completion_context,
    completion_scope,
    line_at,
)
from docassemble_lsp.core.completion_registry import CompletionRegistry
from docassemble_lsp.core.completion_registry import (
    property_documentation as _documentation,
)
from docassemble_lsp.core.completion_rules import SchemaMetadata, load_rule_registry
from docassemble_lsp.core.files import templates_dir_for_path
from docassemble_lsp.core.schema_models import CompletionCandidate, HoverInfo
from docassemble_lsp.core.validation_config import RuntimeOptions
from docassemble_lsp.core.workspace import WorkspaceIndex


@lru_cache(maxsize=1)
def load_schema() -> SchemaMetadata:
    return load_rule_registry()


@lru_cache(maxsize=1)
def load_completion_registry() -> CompletionRegistry:
    return CompletionRegistry.default()


def get_completions(
    source: str,
    line: int,
    character: int,
    *,
    uri_or_path: str | Path | None = None,
    workspace_index: WorkspaceIndex,
    runtime_options: RuntimeOptions | None = None,
) -> list[CompletionCandidate]:
    context = build_completion_context(
        source,
        line,
        character,
        uri_or_path=uri_or_path,
        workspace_index=workspace_index,
        metadata=load_schema(),
        runtime_options=runtime_options,
    )
    return load_completion_registry().candidates(context)


def get_hover(
    source: str,
    line: int,
    character: int,
    *,
    workspace_index: WorkspaceIndex | None = None,
    uri_or_path: str | Path | None = None,
) -> HoverInfo | None:
    metadata = load_schema()
    scope = completion_scope(source, line, character)
    scope_properties = metadata.scoped_properties[scope]
    text = line_at(source, line)

    def document_link_hover() -> HoverInfo | None:
        if workspace_index is None:
            return None
        return _resolve_document_link_hover(
            source,
            line,
            character,
            workspace_index,
            uri_or_path=uri_or_path,
        )

    match = re.match(r"^(\s*(?:-\s*)?)([\w/-][\w /-]*?)(\s*:)(.*)", text)
    if match is None:
        return document_link_hover()

    key_prefix = match.group(1)
    key = match.group(2)
    key_separator = match.group(3)
    key_start = len(key_prefix)
    key_end = key_start + len(key)
    value_start = key_end + len(key_separator)

    prop = scope_properties.get(key) or metadata.all_known_properties.get(key)
    if prop is None:
        if workspace_index is not None and character >= value_start:
            return document_link_hover() or _resolve_non_schema_hover(
                source, line, character, workspace_index, uri_or_path=uri_or_path
            )
        return None

    on_key = key_start <= character <= key_end
    on_enum_value = character >= value_start and bool(prop.enum_values)
    if not on_key and not on_enum_value:
        if workspace_index is not None and character >= value_start:
            return document_link_hover() or _resolve_non_schema_hover(
                source, line, character, workspace_index, uri_or_path=uri_or_path
            )
        return None

    documentation = _documentation(key, prop)
    if documentation is None:
        return None
    return HoverInfo(contents=documentation)


def _file_hover(name: str, target_path: Path | None) -> HoverInfo:
    if target_path is None:
        return HoverInfo(contents=f"**file** `{name}`")
    exists = target_path.exists()
    status = "File exists on disk" if exists else "File not found"
    return HoverInfo(
        contents=(
            f"**file** `{name}`\n"
            f"→ `{target_path}`\n\n"
            f"{status}\n\n"
            f"[Open {target_path.name}]({target_path.as_uri()}) (cmd + click)"
        )
    )


def _resolve_document_link_hover(
    source: str,
    line: int,
    character: int,
    workspace_index: WorkspaceIndex,
    *,
    uri_or_path: str | Path | None = None,
) -> HoverInfo | None:
    from docassemble_lsp.core.document_links import resolve_document_link_target_at

    target = resolve_document_link_target_at(
        source,
        line,
        character,
        uri_or_path=uri_or_path,
        search_roots=workspace_index.search_roots,
        workspace_index=workspace_index,
    )
    if target is not None:
        lines = source.splitlines() or [""]
        name = lines[line][target.start_character : target.end_character]
        return _file_hover(name, target.target_path)
    return None


def _resolve_non_schema_hover(
    source: str,
    line: int,
    character: int,
    workspace_index: WorkspaceIndex,
    *,
    uri_or_path: str | Path | None = None,
) -> HoverInfo | None:
    from docassemble_lsp.core.definitions import _symbol_request
    from docassemble_lsp.core.python_paths import path_from_uri_or_path

    current_path = path_from_uri_or_path(uri_or_path) if uri_or_path is not None else None
    request = _symbol_request(source, line, character, current_path)

    if request is None:
        return None

    if request.kind == "event":
        decl = workspace_index.event_declarations.get(request.name)
        if decl is not None:
            location = f"`{decl.path.name}:{decl.line + 1}`"
            return HoverInfo(contents=f"**event** `{request.name}`\n\nDefined in {location}")
        if "${" in request.name:
            return HoverInfo(
                contents=f"**event** `{request.name}` — dynamic Mako expression, cannot be statically resolved"
            )
        return HoverInfo(contents=f"**event** `{request.name}` — not defined in the workspace")

    if request.kind == "def":
        decl = workspace_index.def_declarations.get(request.name)
        if decl is not None:
            location = f"`{decl.path.name}:{decl.line + 1}`"
            return HoverInfo(contents=f"**def** `{request.name}`\n\nDefined in {location}")
        return HoverInfo(contents=f"**def** `{request.name}` — not defined in the workspace")

    if request.kind == "field_var":
        decl = workspace_index.field_var_declarations.get(request.name)
        if decl is not None:
            location = f"`{decl.path.name}:{decl.line + 1}`"
            return HoverInfo(contents=f"**field** `{request.name}`\n\nDeclared in {location}")
        return HoverInfo(contents=f"**field** `{request.name}` — not declared in the workspace")

    if request.kind == "file":
        target_path = request.target_path
        if target_path is not None:
            if not target_path.exists():
                templates_dir = workspace_index.templates_dir_for(current_path) if current_path is not None else None
                if templates_dir is None:
                    templates_dir = templates_dir_for_path(target_path)
                if templates_dir is not None:
                    template_path = (templates_dir / request.name).resolve()
                    if template_path.exists():
                        target_path = template_path
        return _file_hover(request.name, target_path)

    return None
