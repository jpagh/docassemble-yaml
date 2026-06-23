from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DefinitionTarget:
    path: Path
    line: int
    start_character: int
    end_character: int


@dataclass(frozen=True, slots=True)
class WorkspaceSymbolTarget:
    path: Path
    line: int
    start_character: int
    end_character: int
    name: str
    kind: str
    container_name: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentLinkTarget:
    line: int
    start_character: int
    end_character: int
    target_path: Path


@dataclass(frozen=True, slots=True)
class PythonCompletionTarget:
    label: str
    detail: str
    documentation: str | None = None
    text_edit_range: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class PythonModuleSymbol:
    kind: str
    target: DefinitionTarget | None
    methods: dict[str, DefinitionTarget]
    imported_module_path: Path | None = None
    imported_name: str | None = None
    docstring: str | None = None
    bases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PythonModuleIndex:
    symbols: dict[str, PythonModuleSymbol]
    exported_names: tuple[str, ...] | None = None
    custom_datatype_names: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ReferenceRequest:
    kind: str
    name: str
    target_path: Path | None = None


@dataclass(frozen=True, slots=True)
class PythonNamespaceBinding:
    kind: str
    module_name: str
    module_path: Path | None
    alias: str | None = None
    imported_name: str | None = None


@dataclass(frozen=True, slots=True)
class PythonModuleResolution:
    module_name: str
    path: Path | None
    source_kind: str


@dataclass(frozen=True, slots=True)
class PythonSymbolQuery:
    module_name: str
    module_path: Path | None
    chain: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PythonChainOccurrence:
    parts: tuple[str, ...]
    ranges: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True, slots=True)
class BlockScalarRegion:
    key_name: str
    key_line: int
    content_start_line: int
    end_line: int
    content_indent: int
    text: str


@dataclass(frozen=True, slots=True)
class PythonDeclarationQuery:
    query: PythonSymbolQuery
    target: DefinitionTarget


@dataclass(frozen=True, slots=True)
class EventHelperOccurrence:
    name: str
    line: int
    start_character: int
    end_character: int


@dataclass(frozen=True, slots=True)
class MakoBlockRegion:
    code_text: str
    is_expression: bool
    is_module_level: bool
    content_start_offset: int
    content_end_offset: int
