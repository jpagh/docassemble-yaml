from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from docassemble_lsp.core.definition_models import (
    DefinitionTarget,
    EventHelperOccurrence,
    ReferenceRequest,
)
from docassemble_lsp.core.field_keys import FIELD_ITEM_KNOWN_KEYS
from docassemble_lsp.core.python_paths import resolve_package_qualified_path
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_shared import (
    _EVENT_REFERENCE_KEYS,
    _FIELD_CONDITION_KEYS,
    _FILE_REFERENCE_KEYS,
    _FILE_REFERENCE_LIST_PARENTS,
    _KEY_VALUE_RE,
    _LIST_ITEM_VALUE_RE,
    _append_reference_target,
    _clean_value_and_range,
    _document_lines,
    _is_list_key_match,
    _precompute_parent_keys,
)


def _append_symbol_occurrence(
    targets: list[DefinitionTarget],
    *,
    path: Path,
    line: int,
    start_character: int,
    end_character: int,
    include_declaration: bool,
    is_declaration: bool,
) -> None:
    if is_declaration and not include_declaration:
        return
    _append_reference_target(targets, path, line, start_character, end_character)


@dataclass(frozen=True, slots=True)
class WorkspaceNavigationService:
    workspace_index: WorkspaceIndex
    event_helper_occurrences: Callable[[str], Iterable[EventHelperOccurrence]]

    def symbol_occurrences(
        self,
        request: ReferenceRequest,
        *,
        include_declaration: bool,
    ) -> list[DefinitionTarget]:
        targets: list[DefinitionTarget] = []
        for candidate, source in self.workspace_index.as_candidate_pairs():
            targets.extend(
                self._scan_symbol_occurrences(
                    source,
                    request,
                    candidate,
                    include_declaration=include_declaration,
                )
            )
        return targets

    def file_references(self, request: ReferenceRequest, *, include_declaration: bool) -> list[DefinitionTarget]:
        targets: list[DefinitionTarget] = []
        for candidate, source in self.workspace_index.as_candidate_pairs():
            targets.extend(
                self._scan_symbol_occurrences(source, request, candidate.resolve(), include_declaration=True)
            )

        if include_declaration and request.target_path is not None:
            _append_reference_target(targets, request.target_path, 0, 0, 0)

        return targets

    def field_var_declarations(self, request: ReferenceRequest) -> list[DefinitionTarget]:
        """Return every fields-block declaration site for the named field variable."""
        targets: list[DefinitionTarget] = []
        for candidate, source in self.workspace_index.as_candidate_pairs():
            lines = _document_lines(source)
            parents = _precompute_parent_keys(source)
            for line_index, text in enumerate(lines):
                key_match = _KEY_VALUE_RE.match(text)
                if key_match is None:
                    continue
                key_name = key_match.group(2).strip()
                raw_value = key_match.group(3)
                value, start_character, end_character = _clean_value_and_range(
                    raw_value, key_match.start(3), key_match.end(3)
                )
                if not value or value != request.name or ":" in value:
                    continue
                parent = parents[line_index]
                if parent != "fields":
                    continue
                if key_name == "field" or key_name not in FIELD_ITEM_KNOWN_KEYS:
                    _append_reference_target(targets, candidate, line_index, start_character, end_character)
        targets.sort(key=lambda t: (str(t.path), t.line, t.start_character, t.end_character))
        return targets

    def _scan_symbol_occurrences(
        self,
        source: str,
        request: ReferenceRequest,
        path: Path,
        *,
        include_declaration: bool,
    ) -> list[DefinitionTarget]:
        targets: list[DefinitionTarget] = []
        lines = _document_lines(source)
        parents = _precompute_parent_keys(source)

        for line_index, text in enumerate(lines):
            list_match = _LIST_ITEM_VALUE_RE.match(text)
            if list_match is not None:
                raw_value = list_match.group(2)
                value, start_character, end_character = _clean_value_and_range(
                    raw_value,
                    list_match.start(2),
                    list_match.end(2),
                )
                parent = parents[line_index]
                if (
                    request.kind == "file"
                    and parent in _FILE_REFERENCE_LIST_PARENTS
                    and request.target_path is not None
                    and ":" in value
                ):
                    pkg_resolved = resolve_package_qualified_path(value, list(self.workspace_index.search_roots))
                    if pkg_resolved is not None and pkg_resolved == request.target_path:
                        _append_reference_target(targets, path, line_index, start_character, end_character)
                    continue

            key_match = _KEY_VALUE_RE.match(text)
            if key_match is not None:
                key_name = key_match.group(2).strip()
                raw_value = key_match.group(3)
                value, start_character, end_character = _clean_value_and_range(
                    raw_value,
                    key_match.start(3),
                    key_match.end(3),
                )
                if request.kind == "def" and key_name in {"def", "usedefs"} and value == request.name:
                    _append_symbol_occurrence(
                        targets,
                        path=path,
                        line=line_index,
                        start_character=start_character,
                        end_character=end_character,
                        include_declaration=include_declaration,
                        is_declaration=key_name == "def",
                    )
                    continue
                if (
                    request.kind == "event"
                    and key_name in {"event", *_EVENT_REFERENCE_KEYS}
                    and ":" not in value
                    and value == request.name
                ):
                    _append_symbol_occurrence(
                        targets,
                        path=path,
                        line=line_index,
                        start_character=start_character,
                        end_character=end_character,
                        include_declaration=include_declaration,
                        is_declaration=key_name == "event",
                    )
                    continue
                if request.kind == "field_var" and value == request.name and ":" not in value:
                    parent = parents[line_index]
                    if parent == "fields" and (key_name == "field" or key_name not in FIELD_ITEM_KNOWN_KEYS):
                        _append_symbol_occurrence(
                            targets,
                            path=path,
                            line=line_index,
                            start_character=start_character,
                            end_character=end_character,
                            include_declaration=include_declaration,
                            is_declaration=True,
                        )
                        continue
                    if key_name == "variable" and parent in _FIELD_CONDITION_KEYS:
                        _append_symbol_occurrence(
                            targets,
                            path=path,
                            line=line_index,
                            start_character=start_character,
                            end_character=end_character,
                            include_declaration=include_declaration,
                            is_declaration=False,
                        )
                        continue
                if request.kind == "file":
                    parent = parents[line_index]
                    if key_name in _FILE_REFERENCE_KEYS or parent == "objects from file":
                        if request.target_path is not None and value:
                            if ":" not in value:
                                resolved = (path.parent / value).resolve()
                                if resolved == request.target_path:
                                    _append_reference_target(targets, path, line_index, start_character, end_character)
                            else:
                                pkg_resolved = resolve_package_qualified_path(
                                    value, list(self.workspace_index.search_roots)
                                )
                                if pkg_resolved is not None and pkg_resolved == request.target_path:
                                    _append_reference_target(targets, path, line_index, start_character, end_character)
                    elif (
                        parent in _FILE_REFERENCE_LIST_PARENTS
                        and _is_list_key_match(text, key_match)
                        and "." in key_name
                    ):
                        # Package-qualified list item: ``- docassemble.pkg:file.path``
                        # KEY_VALUE_RE split it as key=``pkg.name``, value=``file.path``.
                        full_value = f"{key_name}:{value}"
                        if request.target_path is not None:
                            pkg_resolved = resolve_package_qualified_path(
                                full_value, list(self.workspace_index.search_roots)
                            )
                            if pkg_resolved is not None and pkg_resolved == request.target_path:
                                _append_reference_target(
                                    targets, path, line_index, key_match.start(2), key_match.end(3)
                                )
                    continue

            list_match = _LIST_ITEM_VALUE_RE.match(text)
            if list_match is None or ":" in list_match.group(2):
                continue
            raw_value = list_match.group(2)
            value, start_character, end_character = _clean_value_and_range(
                raw_value,
                list_match.start(2),
                list_match.end(2),
            )
            parent = parents[line_index]
            if request.kind == "def" and parent == "usedefs" and value == request.name:
                _append_symbol_occurrence(
                    targets,
                    path=path,
                    line=line_index,
                    start_character=start_character,
                    end_character=end_character,
                    include_declaration=include_declaration,
                    is_declaration=False,
                )
                continue
            if request.kind == "file" and parent in _FILE_REFERENCE_LIST_PARENTS and request.target_path is not None:
                if value and ":" not in value and (path.parent / value).resolve() == request.target_path:
                    _append_reference_target(targets, path, line_index, start_character, end_character)

        if request.kind == "event":
            for occurrence in self.event_helper_occurrences(source):
                if occurrence.name != request.name:
                    continue
                _append_symbol_occurrence(
                    targets,
                    path=path,
                    line=occurrence.line,
                    start_character=occurrence.start_character,
                    end_character=occurrence.end_character,
                    include_declaration=include_declaration,
                    is_declaration=False,
                )

        targets.sort(key=lambda target: (target.line, target.start_character, target.end_character))
        return targets
