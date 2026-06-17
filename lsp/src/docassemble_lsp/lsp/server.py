from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from lsprotocol.types import (
    INITIALIZED,
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_DOCUMENT_LINK,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_FORMATTING,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_ON_TYPE_FORMATTING,
    TEXT_DOCUMENT_REFERENCES,
    TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    WORKSPACE_DID_CHANGE_WATCHED_FILES,
    WORKSPACE_SYMBOL,
    CodeAction,
    CodeActionKind,
    CodeActionParams,
    Command,
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionOptions,
    DefinitionParams,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidChangeWatchedFilesParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentFormattingParams,
    DocumentLink,
    DocumentLinkOptions,
    DocumentLinkParams,
    DocumentOnTypeFormattingOptions,
    DocumentOnTypeFormattingParams,
    DocumentSymbol,
    DocumentSymbolParams,
    HoverParams,
    InitializedParams,
    InsertTextFormat,
    Location,
    LocationLink,
    LogMessageParams,
    MarkupContent,
    MarkupKind,
    MessageType,
    Position,
    PublishDiagnosticsParams,
    Range,
    ReferenceParams,
    SemanticTokens,
    SemanticTokensLegend,
    SemanticTokensParams,
    SymbolKind,
    TextDocumentPositionParams,
    TextEdit,
    TraceValue,
    WorkspaceEdit,
    WorkspaceSymbol,
    WorkspaceSymbolParams,
)
from lsprotocol.types import (
    Diagnostic as LspDiagnostic,
)
from lsprotocol.types import (
    Hover as LspHover,
)
from pygls.lsp.server import LanguageServer

from docassemble_lsp import __version__
from docassemble_lsp.core import (
    Diagnostic,
    FormatterConfig,
    analyze_text,
    build_document_facts,
    build_workspace_index,
    configure_logging,
    format_text,
    get_completions,
    get_hover,
    resolve_definition_targets,
    resolve_reference_targets,
    resolve_workspace_symbol_targets,
)
from docassemble_lsp.core.definitions import overlay_workspace_documents, python_discovery_signature
from docassemble_lsp.core.document_links import resolve_document_link_targets
from docassemble_lsp.core.files import clear_detect_package_cache
from docassemble_lsp.core.fixes import SourceEdit, resolve_diagnostic_fixes, resolve_fix_all_fixes
from docassemble_lsp.core.indentation import indent_unit_between, infer_indent_unit, leading_whitespace
from docassemble_lsp.core.python_modules import clear_module_index_cache, resolve_python_module_source
from docassemble_lsp.core.python_navigation import enclosing_block_scalar_region
from docassemble_lsp.core.python_paths import path_from_uri_or_path
from docassemble_lsp.core.schema import load_schema
from docassemble_lsp.core.semantic_tokens import (
    SEMANTIC_TOKEN_MODIFIERS,
    SEMANTIC_TOKEN_TYPES,
    build_semantic_token_spans,
    encode_semantic_tokens,
)
from docassemble_lsp.core.validation_config import RuntimeOptions
from docassemble_lsp.core.workspace import WorkspaceIndex

_PYGLS_JSON_RPC_LOGGER = "pygls.protocol.json_rpc"
_UNKNOWN_CANCEL_WARNING_PREFIX = 'Cancel notification for unknown message id "'


class _IgnoreUnknownCancelFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.name == _PYGLS_JSON_RPC_LOGGER
            and record.levelno >= logging.WARNING
            and record.getMessage().startswith(_UNKNOWN_CANCEL_WARNING_PREFIX)
        )


logger = logging.getLogger(__name__)


def _configure_pygls_logging() -> None:
    pygls_logger = logging.getLogger(_PYGLS_JSON_RPC_LOGGER)
    if any(isinstance(existing_filter, _IgnoreUnknownCancelFilter) for existing_filter in pygls_logger.filters):
        return
    pygls_logger.addFilter(_IgnoreUnknownCancelFilter())


@dataclass(frozen=True, slots=True)
class ServerFeatures:
    diagnostics_source: str = "docassemble-lsp"


_YAML_KEY_RE = re.compile(r"^(\s*)(?:-\s*)?([^:#][^:]*?)\s*:")
_FIELDS_KEY_RE = re.compile(r"^(\s*)fields:\s*$")
_ACTION_BUTTONS_KEY_RE = re.compile(r"^(\s*)action buttons:\s*$")
_OBJECTS_KEY_RE = re.compile(r"^(\s*)objects:\s*$")
_OBJECTS_ITEM_RE = re.compile(r"^(\s*)-\s+([^:#][^:]*?)\s*:\s*(.*?)\s*$")
_SIMPLE_LIST_ITEM_RE = re.compile(r"^(\s*)-\s+(.*)$")
_SIMPLE_LIST_BLOCK_KEYS = frozenset({"include", "modules"})
_BLOCK_SCALAR_KEY_RE = re.compile(r"^(\s*)(-\s*)?([^:#][^:]*?)\s*:\s*(\||>|\|-|>-|\|\+|>\+)\s*$")
_BLOCK_SCALAR_MARKERS = {"|", ">", "|-", ">-", "|+", ">+"}
_PYTHON_BLOCK_KEYS = frozenset({"code", "validation code"})
_DOCASSEMBLE_FIX_ALL_KIND = "source.fixAll.docassemble-lsp"


def _document_lines(source: str) -> list[str]:
    return source.splitlines() or [""]


def _severity_to_lsp(value: str) -> DiagnosticSeverity:
    if value == "warning":
        return DiagnosticSeverity.Warning
    if value == "convention":
        return DiagnosticSeverity.Information
    return DiagnosticSeverity.Error


def _diagnostic_range(source: str, line_number: int) -> Range:
    lines = _document_lines(source)
    line_index = min(max(line_number - 1, 0), len(lines) - 1)
    line_text = lines[line_index]
    end_character = max(len(line_text), 1)
    return Range(
        start=Position(line=line_index, character=0),
        end=Position(line=line_index, character=end_character),
    )


def build_lsp_diagnostics(
    uri: str,
    source: str,
    *,
    runtime_options: RuntimeOptions | None = None,
    workspace_index: WorkspaceIndex | None = None,
) -> list[LspDiagnostic]:
    diagnostics = analyze_text(source, path=uri, runtime_options=runtime_options, workspace_index=workspace_index)
    return [
        LspDiagnostic(
            range=_diagnostic_range(source, diagnostic.line),
            message=diagnostic.message,
            severity=_severity_to_lsp(diagnostic.severity),
            source=diagnostic.source,
            code=diagnostic.code,
        )
        for diagnostic in diagnostics
    ]


def build_completion_list(
    source: str,
    line: int,
    character: int,
    *,
    uri_or_path: str | None = None,
    workspace_index: WorkspaceIndex,
    runtime_options: RuntimeOptions | None = None,
) -> CompletionList:
    items = []
    for index, candidate in enumerate(
        get_completions(
            source,
            line,
            character,
            uri_or_path=uri_or_path,
            workspace_index=workspace_index,
            runtime_options=runtime_options,
        )
    ):
        if candidate.display_kind == "property":
            kind = CompletionItemKind.Property
        elif candidate.display_kind == "snippet":
            kind = CompletionItemKind.Snippet
        elif candidate.display_kind == "keyword":
            kind = CompletionItemKind.Keyword
        elif candidate.display_kind == "class":
            kind = CompletionItemKind.Class
        elif candidate.is_value:
            kind = CompletionItemKind.Value
        elif candidate.is_snippet:
            kind = CompletionItemKind.Snippet
        else:
            kind = CompletionItemKind.Property
        text_edit = None
        if candidate.text_edit_range is not None:
            text_edit = TextEdit(
                range=Range(
                    start=Position(line=line, character=candidate.text_edit_range[0]),
                    end=Position(line=line, character=candidate.text_edit_range[1]),
                ),
                new_text=candidate.insert_text,
            )

        items.append(
            CompletionItem(
                label=candidate.label,
                kind=kind,
                detail=candidate.detail,
                filter_text=candidate.filter_text,
                documentation=(
                    MarkupContent(kind=MarkupKind.Markdown, value=candidate.documentation)
                    if candidate.documentation
                    else None
                ),
                insert_text=candidate.insert_text,
                insert_text_format=(
                    InsertTextFormat.Snippet if candidate.is_snippet or candidate.uses_snippet_text else None
                ),
                text_edit=text_edit,
                command=(
                    Command(title="Trigger Suggest", command="editor.action.triggerSuggest")
                    if candidate.trigger_suggest
                    else None
                ),
                sort_text=f"{index:04d}",
            )
        )
    return CompletionList(is_incomplete=False, items=items)


def build_hover(
    source: str,
    line: int,
    character: int,
    *,
    uri_or_path: str | None = None,
    workspace_index: WorkspaceIndex | None = None,
) -> LspHover | None:
    hover = get_hover(source, line, character, workspace_index=workspace_index, uri_or_path=uri_or_path)
    if hover is not None:
        return LspHover(contents=MarkupContent(kind=MarkupKind.Markdown, value=hover.contents))

    if workspace_index is not None and workspace_index.symbol_registry:
        from docassemble_lsp.core.definitions import resolve_python_hover

        python_hover = resolve_python_hover(source, line, character, workspace_index=workspace_index)
        if python_hover is not None:
            return LspHover(contents=MarkupContent(kind=MarkupKind.Markdown, value=python_hover.contents))

    return None


def build_formatting_edits(
    source: str,
    *,
    config: FormatterConfig | None = None,
) -> list[TextEdit]:
    result = format_text(source, config=config)
    if result.error is not None or not result.changed:
        return []

    lines = _document_lines(source)
    end_position = Position(line=len(lines) - 1, character=len(lines[-1]))
    return [
        TextEdit(
            range=Range(start=Position(line=0, character=0), end=end_position),
            new_text=result.text,
        )
    ]


def _objects_on_type_prefix(source: str, line: int) -> str | None:
    if line <= 0:
        return None

    lines = _document_lines(source)
    if line >= len(lines):
        return None

    previous_line = lines[line - 1]
    item_match = _OBJECTS_ITEM_RE.match(previous_line)
    if item_match is None:
        return None

    value = item_match.group(3).strip()
    if not value or value in _BLOCK_SCALAR_MARKERS:
        return None

    item_indent = item_match.group(1)
    for search_index in range(line - 2, -1, -1):
        candidate = lines[search_index]
        if not candidate.strip():
            continue

        candidate_indent = leading_whitespace(candidate)
        if len(candidate_indent) >= len(item_indent):
            continue

        match = _OBJECTS_KEY_RE.match(candidate)
        if match is None:
            return None
        if match.group(1) != candidate_indent:
            return None
        return f"{item_indent}- "

    return None


def _simple_list_on_type_prefix(source: str, line: int) -> str | None:
    if line <= 0:
        return None

    lines = _document_lines(source)
    if line >= len(lines):
        return None

    previous_line = lines[line - 1]
    item_match = _SIMPLE_LIST_ITEM_RE.match(previous_line)
    if item_match is None:
        return None

    value = item_match.group(2).strip()
    if not value or value in _BLOCK_SCALAR_MARKERS:
        return _simple_list_empty_or_block_scalar_prefix(source, line, item_match)

    item_indent = item_match.group(1)
    for search_index in range(line - 2, -1, -1):
        candidate = lines[search_index]
        if not candidate.strip():
            continue

        candidate_indent = leading_whitespace(candidate)
        if len(candidate_indent) >= len(item_indent):
            continue

        match = _YAML_KEY_RE.match(candidate)
        if match is None:
            return None
        key_name = match.group(2).strip()
        if key_name not in _SIMPLE_LIST_BLOCK_KEYS:
            return None
        if match.group(1) != candidate_indent:
            return None
        return f"{item_indent}- "

    return None


def _simple_list_empty_or_block_scalar_prefix(source: str, line: int, item_match: re.Match[str]) -> str | None:
    item_indent = item_match.group(1)
    indent_unit = infer_indent_unit(source, line - 1, fallback="  ")

    for search_index in range(line - 2, -1, -1):
        candidate = _document_lines(source)[search_index]
        if not candidate.strip():
            continue

        candidate_indent = leading_whitespace(candidate)
        if len(candidate_indent) >= len(item_indent):
            continue

        match = _YAML_KEY_RE.match(candidate)
        if match is None:
            return None
        if match.group(1) != candidate_indent:
            return None
        key_name = match.group(2).strip()
        if key_name in _SIMPLE_LIST_BLOCK_KEYS:
            return f"{item_indent}- "
        return f"{item_indent}{indent_unit}"

    return None


def _default_indent_unit(*, insert_spaces: bool, tab_size: int) -> str:
    return " " * max(tab_size, 1) if insert_spaces else "\t"


def _block_scalar_on_type_prefix(source: str, line: int, *, insert_spaces: bool, tab_size: int) -> str | None:
    if line <= 0:
        return None

    lines = _document_lines(source)
    if line >= len(lines):
        return None

    previous_line = lines[line - 1]
    match = _BLOCK_SCALAR_KEY_RE.match(previous_line)
    if match is None:
        return None

    indent_unit = infer_indent_unit(
        source,
        line - 1,
        fallback=_default_indent_unit(insert_spaces=insert_spaces, tab_size=tab_size),
    )
    mapping_indent = match.group(1)
    if match.group(2):
        mapping_indent = f"{mapping_indent}{indent_unit}"
    return f"{mapping_indent}{indent_unit}"


def _python_block_on_type_prefix(source: str, line: int, *, insert_spaces: bool, tab_size: int) -> str | None:
    if line <= 0:
        return None

    lines = _document_lines(source)
    if line >= len(lines):
        return None

    region = enclosing_block_scalar_region(source, line)
    if region is None or region.key_name not in _PYTHON_BLOCK_KEYS:
        return None

    indent_unit = _default_indent_unit(insert_spaces=insert_spaces, tab_size=tab_size)

    for prev in range(line - 1, region.content_start_line - 1, -1):
        prev_text = lines[prev]
        if not prev_text.strip():
            continue
        if len(prev_text) <= region.content_indent:
            continue
        stripped = prev_text.strip()
        if not stripped:
            continue
        prev_indent = leading_whitespace(prev_text)
        if stripped.endswith(":"):
            return prev_indent + indent_unit
        return prev_indent

    return indent_unit


def _fields_on_type_prefix(source: str, line: int, *, insert_spaces: bool, tab_size: int) -> str | None:
    if line <= 0:
        return None

    lines = _document_lines(source)
    if line >= len(lines):
        return None

    previous_line = lines[line - 1]
    item_match = _OBJECTS_ITEM_RE.match(previous_line)
    if item_match is None:
        return None

    value = item_match.group(3).strip()
    if not value or value in _BLOCK_SCALAR_MARKERS:
        return None

    item_indent = item_match.group(1)
    for search_index in range(line - 2, -1, -1):
        candidate = lines[search_index]
        if not candidate.strip():
            continue

        candidate_indent = leading_whitespace(candidate)
        if len(candidate_indent) >= len(item_indent):
            continue

        match = _FIELDS_KEY_RE.match(candidate)
        if match is None:
            match = _ACTION_BUTTONS_KEY_RE.match(candidate)
        if match is None:
            return None
        if match.group(1) != candidate_indent:
            return None
        indent_unit = indent_unit_between(
            match.group(1),
            item_indent,
            fallback=_default_indent_unit(insert_spaces=insert_spaces, tab_size=tab_size),
        )
        return f"{item_indent}{indent_unit}"

    return None


def build_on_type_formatting_edits(
    source: str,
    line: int,
    character: int,
    trigger: str,
    *,
    insert_spaces: bool = True,
    tab_size: int = 2,
) -> list[TextEdit]:
    if trigger != "\n":
        return []

    lines = _document_lines(source)
    if line < 0 or line >= len(lines):
        return []

    current_line = lines[line]
    if current_line.strip():
        return []

    desired_prefix = _objects_on_type_prefix(source, line)
    if desired_prefix is None:
        desired_prefix = _fields_on_type_prefix(
            source,
            line,
            insert_spaces=insert_spaces,
            tab_size=tab_size,
        )
    if desired_prefix is None:
        desired_prefix = _simple_list_on_type_prefix(source, line)
    if desired_prefix is None:
        desired_prefix = _block_scalar_on_type_prefix(
            source,
            line,
            insert_spaces=insert_spaces,
            tab_size=tab_size,
        )
    if desired_prefix is None:
        desired_prefix = _python_block_on_type_prefix(
            source,
            line,
            insert_spaces=insert_spaces,
            tab_size=tab_size,
        )
    if desired_prefix is None:
        return []

    replace_end = min(max(character, 0), len(current_line))
    if current_line[:replace_end] == desired_prefix:
        return []

    return [
        TextEdit(
            range=Range(
                start=Position(line=line, character=0),
                end=Position(line=line, character=replace_end),
            ),
            new_text=desired_prefix,
        )
    ]


def _key_symbol_kind(key_name: str) -> SymbolKind:
    if key_name in {"code", "validation code", "mako"}:
        return SymbolKind.Function
    if key_name in {
        "fields",
        "buttons",
        "review",
        "attachment",
        "attachments",
        "objects",
        "sections",
        "imports",
        "modules",
        "translations",
        "columns",
        "action buttons",
        "metadata",
        "default screen parts",
    }:
        return SymbolKind.Object
    return SymbolKind.Property


def _workspace_symbol_kind(kind: str) -> SymbolKind:
    if kind == "event":
        return SymbolKind.Event
    if kind == "def":
        return SymbolKind.Function
    if kind == "id":
        return SymbolKind.Module
    if kind == "attachment":
        return SymbolKind.File
    if kind == "objects":
        return SymbolKind.Class
    if kind == "fields":
        return SymbolKind.Struct
    if kind == "question":
        return SymbolKind.String
    if kind == "code":
        return SymbolKind.Function
    return SymbolKind.Module


def build_document_symbols(source: str) -> list[DocumentSymbol]:
    lines = _document_lines(source)
    symbols: list[DocumentSymbol] = []

    for fact in build_document_facts(source):
        children: list[DocumentSymbol] = []
        for key_fact in fact.keys:
            end_character = len(lines[key_fact.line])
            key_range = Range(
                start=Position(line=key_fact.line, character=0),
                end=Position(line=key_fact.line, character=end_character),
            )
            children.append(
                DocumentSymbol(
                    name=key_fact.name,
                    kind=_key_symbol_kind(key_fact.name),
                    range=key_range,
                    selection_range=key_range,
                    detail=key_fact.value or None,
                )
            )

        selection_end = len(lines[fact.selection_line])
        document_end = len(lines[fact.end_line])
        symbols.append(
            DocumentSymbol(
                name=fact.name,
                kind=SymbolKind.Module,
                range=Range(
                    start=Position(line=fact.start_line, character=0),
                    end=Position(line=fact.end_line, character=document_end),
                ),
                selection_range=Range(
                    start=Position(line=fact.selection_line, character=0),
                    end=Position(line=fact.selection_line, character=selection_end),
                ),
                children=children,
            )
        )

    return symbols


def build_workspace_symbols(
    query: str,
    *,
    workspace_index: WorkspaceIndex,
) -> list[WorkspaceSymbol]:
    return [
        WorkspaceSymbol(
            location=Location(
                uri=target.path.as_uri(),
                range=Range(
                    start=Position(line=target.line, character=target.start_character),
                    end=Position(line=target.line, character=target.end_character),
                ),
            ),
            name=target.name,
            kind=_workspace_symbol_kind(target.kind),
            container_name=target.container_name,
        )
        for target in resolve_workspace_symbol_targets(
            query,
            workspace_index=workspace_index,
        )
    ]


def _line_key_range(source: str, line: int) -> tuple[str, int, int] | None:
    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]
    match = _YAML_KEY_RE.match(text)
    if match is None:
        return None
    return (match.group(2).strip(), match.start(2), match.end(2))


def _has_unknown_keys_diagnostic(diagnostics: list[LspDiagnostic]) -> bool:
    for diagnostic in diagnostics:
        if diagnostic.code != "E301":
            continue
        return True
    return False


def _suggest_known_key_replacement(key_name: str) -> str | None:
    schema = load_schema()
    known_keys = sorted(set(schema.all_known_properties) | set(schema.top_level))
    if key_name in known_keys:
        return None
    matches = get_close_matches(key_name, known_keys, n=1, cutoff=0.75)
    if not matches:
        return None
    return matches[0]


def _diagnostic_from_lsp(diagnostic: LspDiagnostic) -> Diagnostic:
    severity = "error"
    if diagnostic.severity == DiagnosticSeverity.Warning:
        severity = "warning"
    elif diagnostic.severity == DiagnosticSeverity.Information:
        severity = "convention"

    return Diagnostic(
        line=diagnostic.range.start.line + 1,
        message=diagnostic.message,
        severity=severity,
        code=str(diagnostic.code) if diagnostic.code is not None else None,
        source=diagnostic.source or "docassemble-lsp",
    )


def _text_edit_from_source_edit(edit: SourceEdit) -> TextEdit:
    return TextEdit(
        range=Range(
            start=Position(line=edit.start_line, character=edit.start_character),
            end=Position(line=edit.end_line, character=edit.end_character),
        ),
        new_text=edit.new_text,
    )


def build_code_actions(
    uri: str,
    source: str,
    line: int,
    diagnostics: list[LspDiagnostic],
    *,
    only_kinds: list[str] | None = None,
) -> list[CodeAction]:
    requested_kinds = set(only_kinds or [])
    wants_quick_fix = not requested_kinds or CodeActionKind.QuickFix in requested_kinds
    wants_fix_all = not requested_kinds or bool(
        requested_kinds & {CodeActionKind.SourceFixAll, "source.fixAll", _DOCASSEMBLE_FIX_ALL_KIND}
    )

    core_diagnostics = [_diagnostic_from_lsp(diagnostic) for diagnostic in diagnostics]
    actions: list[CodeAction] = []

    if wants_quick_fix:
        fixes = resolve_diagnostic_fixes(source, core_diagnostics, preferred_line=line)
        for fix in fixes:
            actions.append(
                CodeAction(
                    title=fix.title,
                    kind=CodeActionKind.QuickFix,
                    diagnostics=diagnostics,
                    is_preferred=True,
                    edit=WorkspaceEdit(changes={uri: [_text_edit_from_source_edit(fix.edit)]}),
                )
            )

    if wants_fix_all:
        fix_all_fixes = resolve_fix_all_fixes(source, core_diagnostics)
        if fix_all_fixes:
            actions.append(
                CodeAction(
                    title="Fix all auto-fixable docassemble-lsp issues",
                    kind=_DOCASSEMBLE_FIX_ALL_KIND,
                    diagnostics=diagnostics,
                    edit=WorkspaceEdit(changes={uri: [_text_edit_from_source_edit(fix.edit) for fix in fix_all_fixes]}),
                )
            )

    return actions


def _origin_range(source: str, line: int, character: int) -> Range | None:
    """Return the source-range of the identifier at ``(line, character)``.

    Walks outward from *character* to find the non-whitespace extent on the
    line — this gives VS Code an explicit ``originSelectionRange`` so it can
    draw the underline without inferring the span from the result.
    """
    from docassemble_lsp.core.definitions import _match_value_context_with_range

    _key_or_parent, _value, start_char, end_char = _match_value_context_with_range(source, line, character)
    if start_char == 0 and end_char == 0:
        return None
    return Range(
        start=Position(line=line, character=start_char),
        end=Position(line=line, character=end_char),
    )


def build_definition_locations(
    uri: str,
    source: str,
    line: int,
    character: int,
    *,
    workspace_index: WorkspaceIndex,
) -> list[LocationLink]:
    origin_range = _origin_range(source, line, character)
    return [
        LocationLink(
            origin_selection_range=origin_range,
            target_uri=target.path.as_uri(),
            target_range=Range(
                start=Position(line=target.line, character=target.start_character),
                end=Position(line=target.line, character=target.end_character),
            ),
            target_selection_range=Range(
                start=Position(line=target.line, character=target.start_character),
                end=Position(line=target.line, character=target.end_character),
            ),
        )
        for target in resolve_definition_targets(
            source,
            line,
            character,
            uri_or_path=uri,
            workspace_index=workspace_index,
        )
    ]


def build_reference_locations(
    uri: str,
    source: str,
    line: int,
    character: int,
    *,
    include_declaration: bool = True,
    workspace_index: WorkspaceIndex,
) -> list[Location]:
    return [
        Location(
            uri=target.path.as_uri(),
            range=Range(
                start=Position(line=target.line, character=target.start_character),
                end=Position(line=target.line, character=target.end_character),
            ),
        )
        for target in resolve_reference_targets(
            source,
            line,
            character,
            uri_or_path=uri,
            include_declaration=include_declaration,
            workspace_index=workspace_index,
        )
    ]


def build_document_links(
    uri: str,
    source: str,
    *,
    workspace_index: WorkspaceIndex | None = None,
) -> list[DocumentLink]:
    search_roots = workspace_index.search_roots if workspace_index is not None else ()
    links: list[DocumentLink] = []
    for target in resolve_document_link_targets(
        source, uri_or_path=uri, search_roots=search_roots, workspace_index=workspace_index
    ):
        try:
            target_uri = target.target_path.as_uri()
        except Exception as exc:
            logger.warning("Skipping document link target %s: %s", target.target_path, exc)
            continue
        if target.start_character == target.end_character:
            continue
        links.append(
            DocumentLink(
                range=Range(
                    start=Position(line=target.line, character=target.start_character),
                    end=Position(line=target.line, character=target.end_character),
                ),
                target=target_uri,
                tooltip=f"Open {target.target_path.name}",
            )
        )
    logger.debug("LSP document links for %s: count=%d", uri, len(links))
    return links


def build_semantic_tokens(source: str) -> SemanticTokens:
    spans = build_semantic_token_spans(source)
    return SemanticTokens(data=encode_semantic_tokens(spans))


def _workspace_roots(root_path: str | None) -> list[Path]:
    return [Path(root_path)] if root_path else []


class _WorkspaceIndexStore:
    def __init__(self) -> None:
        self._open_sources: dict[Path, str] = {}
        self._open_signatures: dict[Path, frozenset[str]] = {}
        self._pending_signature_paths: set[Path] = set()
        self._removed_signatures: dict[Path, frozenset[str]] = {}
        self._base_indexes: dict[tuple[Path, ...], WorkspaceIndex] = {}
        self._needs_python_refresh: bool = False
        self._generation: int = 0
        self._cached_full: tuple[tuple[Path, ...], int, WorkspaceIndex] | None = None
        self._cached_document_links: dict[tuple[str, int, int], list[DocumentLink]] = {}

    def clear(self) -> None:
        self._base_indexes.clear()
        self._cached_full = None
        self._cached_document_links.clear()
        self._pending_signature_paths.clear()
        self._removed_signatures.clear()
        if self._open_sources:
            self._needs_python_refresh = True

    def _document_link_cache_key(self, uri: str, source: str) -> tuple[str, int, int]:
        return (uri, len(source), hash(source))

    def cached_document_links(self, uri: str, source: str) -> list[DocumentLink] | None:
        cached = self._cached_document_links.get(self._document_link_cache_key(uri, source))
        return list(cached) if cached is not None else None

    def store_document_links(self, uri: str, source: str, links: list[DocumentLink]) -> None:
        self._cached_document_links[self._document_link_cache_key(uri, source)] = list(links)

    def _evict_document_link_cache(self, uri: str) -> None:
        """Remove cached document links for *uri* only — other documents are unaffected."""
        self._cached_document_links = {k: v for k, v in self._cached_document_links.items() if k[0] != uri}

    def update_source(self, uri: str, source: str) -> None:
        path = path_from_uri_or_path(uri)
        if path is None:
            return
        path = path.resolve()
        existing = self._open_sources.get(path)
        if existing != source:
            self._evict_document_link_cache(uri)
            signature = python_discovery_signature(source)
            existing_signature = self._open_signatures.get(path)
            self._open_sources[path] = source
            self._open_signatures[path] = signature
            self._removed_signatures.pop(path, None)
            if existing_signature is None:
                self._pending_signature_paths.add(path)
            elif existing_signature != signature:
                self._needs_python_refresh = True
            self._generation += 1

    def remove_source(self, uri: str) -> None:
        path = path_from_uri_or_path(uri)
        if path is not None:
            path = path.resolve()
        if path is not None and path in self._open_sources:
            self._evict_document_link_cache(uri)
            del self._open_sources[path]
            signature = self._open_signatures.pop(path, frozenset())
            self._pending_signature_paths.discard(path)
            if self._open_sources:
                self._removed_signatures[path] = signature
            else:
                self._removed_signatures.clear()
                self._needs_python_refresh = False
                self._cached_full = None
            self._generation += 1

    def _base_for_roots(self, root_path: str | None) -> WorkspaceIndex:
        roots = tuple(_workspace_roots(root_path))
        index = self._base_indexes.get(roots)
        if index is None:
            index = build_workspace_index(list(roots))
            self._base_indexes[roots] = index
        return index

    def _check_pending_signatures(self, root_path: str | None) -> WorkspaceIndex | None:
        if not self._pending_signature_paths and not self._removed_signatures:
            return None
        base = self._base_for_roots(root_path)
        source_cache = base.as_source_dict()
        for path in self._pending_signature_paths:
            base_signature = python_discovery_signature(source_cache[path]) if path in source_cache else frozenset()
            if self._open_signatures.get(path, frozenset()) != base_signature:
                self._needs_python_refresh = True
                break
        if not self._needs_python_refresh:
            for path, signature in self._removed_signatures.items():
                base_signature = python_discovery_signature(source_cache[path]) if path in source_cache else frozenset()
                if signature != base_signature:
                    self._needs_python_refresh = True
                    break
        self._pending_signature_paths.clear()
        self._removed_signatures.clear()
        return base

    def for_workspace(self, root_path: str | None) -> WorkspaceIndex:
        if not self._open_sources:
            self._cached_full = None
            self._pending_signature_paths.clear()
            self._removed_signatures.clear()
            self._needs_python_refresh = False
            return self._base_for_roots(root_path)

        roots = tuple(_workspace_roots(root_path))
        checked_base = self._check_pending_signatures(root_path)

        if not self._needs_python_refresh:
            if (
                self._cached_full is not None
                and self._cached_full[0] == roots
                and self._cached_full[1] == self._generation
            ):
                return self._cached_full[2]
            base = checked_base if checked_base is not None else self._base_for_roots(root_path)
            index = overlay_workspace_documents(base, self._open_sources, refresh_python=False)
            self._cached_full = (roots, self._generation, index)
            return index

        base = checked_base if checked_base is not None else self._base_for_roots(root_path)
        index = overlay_workspace_documents(base, self._open_sources, refresh_python=True)
        self._needs_python_refresh = False
        self._cached_full = (roots, self._generation, index)
        return index

    def for_document(self, root_path: str | None, uri: str, source: str) -> WorkspaceIndex:
        self.update_source(uri, source)
        return self.for_workspace(root_path)


def create_server(
    *,
    runtime_options: RuntimeOptions | None = None,
    formatter_config: FormatterConfig | None = None,
) -> LanguageServer:
    server = LanguageServer("docassemble-lsp", __version__)
    workspace_indexes = _WorkspaceIndexStore()

    def publish(uri: str) -> None:
        document = server.workspace.get_text_document(uri)
        index = workspace_indexes.for_workspace(server.workspace.root_path)
        server.text_document_publish_diagnostics(
            PublishDiagnosticsParams(
                uri=uri,
                diagnostics=build_lsp_diagnostics(
                    uri,
                    document.source,
                    runtime_options=runtime_options,
                    workspace_index=index,
                ),
            )
        )

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    def did_open(
        ls: LanguageServer,
        params: DidOpenTextDocumentParams,
    ) -> None:
        del ls
        workspace_indexes.update_source(params.text_document.uri, params.text_document.text)
        publish(params.text_document.uri)

    @server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def did_change(
        ls: LanguageServer,
        params: DidChangeTextDocumentParams,
    ) -> None:
        del ls
        document = server.workspace.get_text_document(params.text_document.uri)
        workspace_indexes.update_source(params.text_document.uri, document.source)
        publish(params.text_document.uri)

    @server.feature(TEXT_DOCUMENT_DID_SAVE)
    def did_save(ls: LanguageServer, params: DidSaveTextDocumentParams) -> None:
        del ls
        document = server.workspace.get_text_document(params.text_document.uri)
        workspace_indexes.update_source(params.text_document.uri, document.source)
        # When saving a .py file only the saved module's AST is stale —
        # YAML saves never modify Python files, so the workspace index stays valid.
        if params.text_document.uri.endswith(".py"):
            py_path = path_from_uri_or_path(params.text_document.uri)
            if py_path is not None:
                clear_module_index_cache([py_path])
                clear_detect_package_cache([py_path])
            # No workspace index rebuild needed — overlays handle it.
            publish(params.text_document.uri)
            return
        workspace_indexes.clear()
        workspace_indexes.for_workspace(server.workspace.root_path)
        publish(params.text_document.uri)

    @server.feature(TEXT_DOCUMENT_DID_CLOSE)
    def did_close(
        ls: LanguageServer,
        params: DidCloseTextDocumentParams,
    ) -> None:
        del ls
        workspace_indexes.remove_source(params.text_document.uri)

    @server.feature(INITIALIZED)
    def initialized(
        ls: LanguageServer,
        params: InitializedParams,
    ) -> None:
        del params
        if ls.protocol.trace not in (None, TraceValue.Off):
            ls.window_log_message(
                LogMessageParams(message=f"Workspace root: {ls.workspace.root_path}", type=MessageType.Log)
            )
        workspace_indexes.for_workspace(ls.workspace.root_path)

    @server.feature(WORKSPACE_DID_CHANGE_WATCHED_FILES)
    def did_change_watched_files(
        ls: LanguageServer,
        params: DidChangeWatchedFilesParams,
    ) -> None:
        del ls
        relevant = any(change.uri.endswith((".py", ".yml", ".yaml")) for change in params.changes)
        if relevant:
            workspace_indexes.clear()
            changed_paths = [p for change in params.changes if (p := path_from_uri_or_path(change.uri)) is not None]
            if changed_paths:
                clear_detect_package_cache(changed_paths)
            workspace_indexes.for_workspace(server.workspace.root_path)

    @server.feature(
        TEXT_DOCUMENT_COMPLETION,
        CompletionOptions(trigger_characters=[":", " ", "."]),
    )
    def completion(
        ls: LanguageServer,
        params: TextDocumentPositionParams,
    ) -> CompletionList:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return build_completion_list(
            document.source,
            params.position.line,
            params.position.character,
            uri_or_path=params.text_document.uri,
            workspace_index=workspace_indexes.for_document(
                ls.workspace.root_path,
                params.text_document.uri,
                document.source,
            ),
            runtime_options=runtime_options,
        )

    @server.feature(TEXT_DOCUMENT_HOVER)
    def hover(
        ls: LanguageServer,
        params: HoverParams,
    ) -> LspHover | None:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return build_hover(
            document.source,
            params.position.line,
            params.position.character,
            uri_or_path=params.text_document.uri,
            workspace_index=workspace_indexes.for_document(
                ls.workspace.root_path,
                params.text_document.uri,
                document.source,
            ),
        )

    @server.feature(TEXT_DOCUMENT_DEFINITION)
    def definition(
        ls: LanguageServer,
        params: DefinitionParams,
    ) -> list[LocationLink]:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return build_definition_locations(
            params.text_document.uri,
            document.source,
            params.position.line,
            params.position.character,
            workspace_index=workspace_indexes.for_document(
                ls.workspace.root_path,
                params.text_document.uri,
                document.source,
            ),
        )

    @server.feature(TEXT_DOCUMENT_REFERENCES)
    def references(
        ls: LanguageServer,
        params: ReferenceParams,
    ) -> list[Location]:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return build_reference_locations(
            params.text_document.uri,
            document.source,
            params.position.line,
            params.position.character,
            include_declaration=params.context.include_declaration,
            workspace_index=workspace_indexes.for_document(
                ls.workspace.root_path,
                params.text_document.uri,
                document.source,
            ),
        )

    @server.feature(TEXT_DOCUMENT_CODE_ACTION)
    def code_action(ls: LanguageServer, params: CodeActionParams) -> list[CodeAction]:
        del ls
        document = server.workspace.get_text_document(params.text_document.uri)
        return build_code_actions(
            params.text_document.uri,
            document.source,
            params.range.start.line,
            list(params.context.diagnostics),
            only_kinds=list(params.context.only) if params.context.only is not None else None,
        )

    @server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbol(
        ls: LanguageServer,
        params: DocumentSymbolParams,
    ) -> list[DocumentSymbol]:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return build_document_symbols(document.source)

    @server.feature(TEXT_DOCUMENT_DOCUMENT_LINK, DocumentLinkOptions(resolve_provider=False))
    def document_link(ls: LanguageServer, params: DocumentLinkParams) -> list[DocumentLink]:
        document = ls.workspace.get_text_document(params.text_document.uri)
        index = workspace_indexes.for_document(
            ls.workspace.root_path,
            params.text_document.uri,
            document.source,
        )
        cached_links = workspace_indexes.cached_document_links(params.text_document.uri, document.source)
        if cached_links is not None:
            logger.debug("LSP document link cache hit for %s: count=%d", params.text_document.uri, len(cached_links))
            return cached_links
        links = build_document_links(
            params.text_document.uri,
            document.source,
            workspace_index=index,
        )
        workspace_indexes.store_document_links(params.text_document.uri, document.source, links)
        return links

    @server.feature(WORKSPACE_SYMBOL)
    def workspace_symbol(ls: LanguageServer, params: WorkspaceSymbolParams) -> list[WorkspaceSymbol]:
        return build_workspace_symbols(
            params.query,
            workspace_index=workspace_indexes.for_workspace(ls.workspace.root_path),
        )

    @server.feature(TEXT_DOCUMENT_FORMATTING)
    def formatting(
        ls: LanguageServer,
        params: DocumentFormattingParams,
    ) -> list[TextEdit]:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return build_formatting_edits(document.source, config=formatter_config)

    @server.feature(
        TEXT_DOCUMENT_ON_TYPE_FORMATTING,
        DocumentOnTypeFormattingOptions(first_trigger_character="\n"),
    )
    def on_type_formatting(
        ls: LanguageServer,
        params: DocumentOnTypeFormattingParams,
    ) -> list[TextEdit]:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return build_on_type_formatting_edits(
            document.source,
            params.position.line,
            params.position.character,
            params.ch,
            insert_spaces=getattr(params.options, "insert_spaces", getattr(params.options, "insertSpaces", True)),
            tab_size=getattr(params.options, "tab_size", getattr(params.options, "tabSize", 2)),
        )

    @server.feature(
        TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
        SemanticTokensLegend(
            token_types=SEMANTIC_TOKEN_TYPES,
            token_modifiers=SEMANTIC_TOKEN_MODIFIERS,
        ),
    )
    def semantic_tokens_full(ls: LanguageServer, params: SemanticTokensParams) -> SemanticTokens:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return build_semantic_tokens(document.source)

    return server


def run_server(
    *,
    runtime_options: RuntimeOptions | None = None,
    formatter_config: FormatterConfig | None = None,
    log_level: str = "WARNING",
) -> int:
    configure_logging(level=log_level)
    _configure_pygls_logging()
    for module_name in ("docassemble.base.util", "docassemble.base.functions"):
        resolution = resolve_python_module_source(module_name, workspace_index=WorkspaceIndex.empty())
        path_text = str(resolution.path) if resolution.path is not None else "<unresolved>"
        logger.info("Using %s from %s: %s", resolution.module_name, resolution.source_kind, path_text)
    create_server(runtime_options=runtime_options, formatter_config=formatter_config).start_io()
    return 0
