from __future__ import annotations

from dataclasses import dataclass

from docassemble_lsp.core.definition_models import DefinitionTarget, ReferenceRequest, WorkspaceSymbolTarget
from docassemble_lsp.core.document_facts import DocumentFact
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_shared import _document_lines, _strip_quotes


def _strip_inline_comment_with_quotes(value: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value


def _clean_value(value: str) -> str:
    return _strip_quotes(_strip_inline_comment_with_quotes(value))


def workspace_symbol_kind(fact: DocumentFact) -> str:
    key_names = {key_fact.name for key_fact in fact.keys}
    if "event" in key_names:
        return "event"
    if "def" in key_names:
        return "def"
    if "id" in key_names:
        return "id"
    if "attachment" in key_names or "attachments" in key_names:
        return "attachment"
    if "objects" in key_names:
        return "objects"
    if "fields" in key_names:
        return "fields"
    if "question" in key_names:
        return "question"
    if "code" in key_names:
        return "code"
    return "document"


@dataclass(frozen=True, slots=True)
class WorkspaceSymbolService:
    workspace_index: WorkspaceIndex

    def definitions_for(self, request: ReferenceRequest) -> list[DefinitionTarget]:
        declaration_key = "def" if request.kind == "def" else "event"
        targets: list[DefinitionTarget] = []
        for candidate, source, facts in self.workspace_index.as_document_fact_entries():
            lines = _document_lines(source)
            for fact in facts:
                for key_fact in fact.keys:
                    if key_fact.name != declaration_key:
                        continue
                    if _clean_value(key_fact.value) != request.name:
                        continue
                    target = DefinitionTarget(
                        path=candidate,
                        line=key_fact.line,
                        start_character=0,
                        end_character=len(lines[key_fact.line]),
                    )
                    if target not in targets:
                        targets.append(target)
        return targets

    def symbols(self, query: str) -> list[WorkspaceSymbolTarget]:
        normalized_query = query.strip().lower()
        targets: list[WorkspaceSymbolTarget] = []

        for candidate, source, facts in self.workspace_index.as_document_fact_entries():
            lines = _document_lines(source)
            for fact in facts:
                symbol_name = fact.name
                if normalized_query and normalized_query not in symbol_name.lower():
                    continue
                selection_line = fact.selection_line
                line_text = lines[selection_line]
                targets.append(
                    WorkspaceSymbolTarget(
                        path=candidate,
                        line=selection_line,
                        start_character=0,
                        end_character=len(line_text),
                        name=symbol_name,
                        kind=workspace_symbol_kind(fact),
                    )
                )

        targets.sort(key=lambda target: (target.name.lower(), str(target.path), target.line, target.start_character))
        return targets
