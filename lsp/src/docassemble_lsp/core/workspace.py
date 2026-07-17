from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

from docassemble_lsp.core.definition_models import DefinitionTarget
from docassemble_lsp.core.document_facts import DocumentFact, build_document_facts
from docassemble_lsp.core.field_keys import (
    FIELD_ITEM_KNOWN_KEYS as _FIELD_ITEM_KNOWN_KEYS,
)
from docassemble_lsp.core.files import collect_yaml_files, detect_docassemble_package
from docassemble_lsp.core.yaml_shared import (
    _KEY_VALUE_RE,
    _clean_value,
    _clean_value_and_range,
    _document_lines,
    _precompute_parent_keys,
)


@dataclass(frozen=True, slots=True)
class YamlSource:
    path: Path
    text: str


@dataclass(frozen=True, slots=True)
class WorkspaceYamlSources:
    sources: tuple[YamlSource, ...]

    @classmethod
    def from_roots(
        cls,
        search_roots: list[Path],
        *,
        current_path: Path | None = None,
        current_source: str | None = None,
        overlays: Mapping[Path, str] | None = None,
    ) -> WorkspaceYamlSources:
        sources: list[YamlSource] = []
        seen_paths: set[Path] = set()

        if overlays:
            resolved_items = sorted(
                ((path.resolve(), text) for path, text in overlays.items()),
                key=lambda x: x[0],
            )
            for resolved, text in resolved_items:
                sources.append(YamlSource(resolved, text))
                seen_paths.add(resolved)

        if current_path is not None and current_source is not None:
            resolved_current_path = current_path.resolve()
            if resolved_current_path not in seen_paths:
                sources.append(YamlSource(resolved_current_path, current_source))
                seen_paths.add(resolved_current_path)

        if search_roots:
            for candidate in collect_yaml_files(search_roots):
                resolved_candidate = candidate.resolve()
                if resolved_candidate in seen_paths:
                    continue
                try:
                    candidate_source = candidate.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                sources.append(YamlSource(resolved_candidate, candidate_source))
                seen_paths.add(resolved_candidate)

        return cls(tuple(sources))

    @classmethod
    def from_source_dict(cls, source_cache: dict[Path, str]) -> WorkspaceYamlSources:
        return cls(tuple(YamlSource(path, text) for path, text in source_cache.items()))

    def as_source_dict(self) -> dict[Path, str]:
        return {source.path: source.text for source in self.sources}

    def as_candidate_pairs(self) -> list[tuple[Path, str]]:
        return [(source.path, source.text) for source in self.sources]

    def with_current_document(self, current_path: Path, current_source: str) -> WorkspaceYamlSources:
        resolved_current_path = current_path.resolve()
        return WorkspaceYamlSources(
            (
                YamlSource(resolved_current_path, current_source),
                *(source for source in self.sources if source.path != resolved_current_path),
            )
        )

    def with_overlays(self, overlays: Mapping[Path, str]) -> WorkspaceYamlSources:
        sorted_overlays = sorted(overlays.items(), key=lambda x: x[0].resolve())
        resolved_overlays = {p.resolve(): t for p, t in sorted_overlays}
        kept = [s for s in self.sources if s.path not in resolved_overlays]
        new_sources = [YamlSource(p, t) for p, t in resolved_overlays.items()] + kept
        return WorkspaceYamlSources(tuple(new_sources))


@dataclass(frozen=True, slots=True)
class WorkspaceIndex:
    yaml_sources: WorkspaceYamlSources
    facts_by_path: dict[Path, tuple[DocumentFact, ...]]
    search_roots: tuple[Path, ...] = ()
    package_root: Path | None = None
    all_custom_datatype_names: frozenset[str] = frozenset()
    all_class_names: frozenset[str] = frozenset()
    all_non_exception_class_names: frozenset[str] = frozenset()
    all_da_object_subclass_names: frozenset[str] = frozenset()
    all_module_paths: frozenset[Path] = frozenset()
    symbol_registry: dict[str, frozenset[DefinitionTarget]] = field(default_factory=dict)
    docstring_registry: dict[str, str] = field(default_factory=dict)
    all_event_names: frozenset[str] = frozenset()
    all_def_names: frozenset[str] = frozenset()
    event_declarations: dict[str, DefinitionTarget] = field(default_factory=dict)
    def_declarations: dict[str, DefinitionTarget] = field(default_factory=dict)
    all_field_var_names: frozenset[str] = frozenset()
    field_var_declarations: dict[str, DefinitionTarget] = field(default_factory=dict)
    all_block_ids: frozenset[str] = frozenset()
    package_templates_dirs: dict[Path, Path] = field(default_factory=dict)
    template_file_names: frozenset[str] = frozenset()

    @classmethod
    def empty(cls) -> WorkspaceIndex:
        return cls(yaml_sources=WorkspaceYamlSources(()), facts_by_path={}, search_roots=())

    @classmethod
    def empty_for_roots(cls, search_roots: tuple[Path, ...] = ()) -> WorkspaceIndex:
        return cls(
            yaml_sources=WorkspaceYamlSources(()),
            facts_by_path={},
            search_roots=search_roots,
        )

    @classmethod
    def from_yaml_roots(
        cls,
        search_roots: list[Path],
        *,
        current_path: Path | None = None,
        current_source: str | None = None,
        overlays: Mapping[Path, str] | None = None,
    ) -> WorkspaceIndex:
        resolved_search_roots = tuple(root.resolve() for root in search_roots)
        yaml_sources = WorkspaceYamlSources.from_roots(
            list(resolved_search_roots),
            current_path=current_path,
            current_source=current_source,
            overlays=overlays,
        )
        package_root = detect_docassemble_package(resolved_search_roots[0]) if resolved_search_roots else None
        return cls(
            yaml_sources=yaml_sources,
            facts_by_path={source.path: tuple(build_document_facts(source.text)) for source in yaml_sources.sources},
            search_roots=resolved_search_roots,
            package_root=package_root,
        )

    @classmethod
    def from_current_document(
        cls,
        current_path: Path,
        current_source: str,
        *,
        search_roots: list[Path] | None = None,
        overlays: Mapping[Path, str] | None = None,
    ) -> WorkspaceIndex:
        result = cls.from_yaml_roots(
            search_roots or [],
            current_path=current_path,
            current_source=current_source,
            overlays=overlays,
        )
        if result.package_root is None:
            pr = detect_docassemble_package(current_path)
            if pr is not None:
                result = replace(result, package_root=pr)
        return result

    def as_source_dict(self) -> dict[Path, str]:
        return self.yaml_sources.as_source_dict()

    def as_candidate_pairs(self) -> list[tuple[Path, str]]:
        return self.yaml_sources.as_candidate_pairs()

    def document_facts(self, path: Path) -> tuple[DocumentFact, ...]:
        return self.facts_by_path.get(path.resolve(), ())

    def as_document_fact_entries(
        self,
    ) -> list[tuple[Path, str, tuple[DocumentFact, ...]]]:
        return [(source.path, source.text, self.document_facts(source.path)) for source in self.yaml_sources.sources]

    def templates_dir_for(self, path: Path) -> Path | None:
        resolved = path.resolve()
        for pkg_root, tdir in self.package_templates_dirs.items():
            try:
                resolved.relative_to(pkg_root)
                return tdir
            except ValueError:
                continue
        return None

    def with_current_document(
        self,
        current_path: Path,
        current_source: str,
    ) -> WorkspaceIndex:
        yaml_sources = self.yaml_sources.with_current_document(current_path, current_source)
        return WorkspaceIndex(
            yaml_sources=yaml_sources,
            facts_by_path={source.path: tuple(build_document_facts(source.text)) for source in yaml_sources.sources},
            search_roots=self.search_roots,
            package_root=self.package_root,
            all_custom_datatype_names=self.all_custom_datatype_names,
            all_class_names=self.all_class_names,
            all_non_exception_class_names=self.all_non_exception_class_names,
            all_da_object_subclass_names=self.all_da_object_subclass_names,
            all_module_paths=self.all_module_paths,
            symbol_registry=self.symbol_registry,
            docstring_registry=self.docstring_registry,
            all_event_names=self.all_event_names,
            all_def_names=self.all_def_names,
            event_declarations=self.event_declarations,
            def_declarations=self.def_declarations,
            all_field_var_names=self.all_field_var_names,
            field_var_declarations=self.field_var_declarations,
            all_block_ids=self.all_block_ids,
            package_templates_dirs=self.package_templates_dirs,
            template_file_names=self.template_file_names,
        )

    def with_overlays(self, overlays: Mapping[Path, str]) -> WorkspaceIndex:
        if not overlays:
            return self
        yaml_sources = self.yaml_sources.with_overlays(overlays)
        overlay_paths = {p.resolve() for p in overlays}
        facts_by_path = dict(self.facts_by_path)
        for source in yaml_sources.sources:
            if source.path in overlay_paths or source.path not in facts_by_path:
                facts_by_path[source.path] = tuple(build_document_facts(source.text))
        event_decls = dict(self.event_declarations)
        def_decls = dict(self.def_declarations)
        field_var_decls = dict(self.field_var_declarations)
        block_ids: set[str] = set(self.all_block_ids)
        for path in overlay_paths:
            for fact in facts_by_path.get(path, ()):
                for kf in fact.keys:
                    value = _clean_value(kf.value)
                    if kf.name == "event" and value:
                        event_decls.setdefault(
                            value,
                            DefinitionTarget(
                                path=path,
                                line=kf.line,
                                start_character=0,
                                end_character=0,
                            ),
                        )
                    elif kf.name == "def" and value:
                        def_decls.setdefault(
                            value,
                            DefinitionTarget(
                                path=path,
                                line=kf.line,
                                start_character=0,
                                end_character=0,
                            ),
                        )
                    elif kf.name == "id" and value:
                        block_ids.add(value)
        # Field_var declarations require a deeper line-level scan.
        # Use yaml_sources (post-overlay) so unsaved edits are reflected.
        source_by_path = {s.path: s.text for s in yaml_sources.sources}
        for path in overlay_paths:
            source_text = source_by_path.get(path)
            if source_text is None:
                continue
            lines = _document_lines(source_text)
            parents = _precompute_parent_keys(source_text)
            for line_index, text in enumerate(lines):
                key_match = _KEY_VALUE_RE.match(text)
                if key_match is None:
                    continue
                key_name = key_match.group(2).strip()
                raw_value = key_match.group(3)
                value, start_character, end_character = _clean_value_and_range(
                    raw_value, key_match.start(3), key_match.end(3)
                )
                if not value or ":" in value:
                    continue
                parent = parents[line_index]
                if parent != "fields":
                    continue
                if key_name == "field" or key_name not in _FIELD_ITEM_KNOWN_KEYS:
                    field_var_decls.setdefault(
                        value,
                        DefinitionTarget(
                            path=path,
                            line=line_index,
                            start_character=start_character,
                            end_character=end_character,
                        ),
                    )
        return WorkspaceIndex(
            yaml_sources=yaml_sources,
            facts_by_path=facts_by_path,
            search_roots=self.search_roots,
            package_root=self.package_root,
            all_custom_datatype_names=self.all_custom_datatype_names,
            all_class_names=self.all_class_names,
            all_non_exception_class_names=self.all_non_exception_class_names,
            all_da_object_subclass_names=self.all_da_object_subclass_names,
            all_module_paths=self.all_module_paths,
            symbol_registry=self.symbol_registry,
            docstring_registry=self.docstring_registry,
            all_event_names=frozenset(event_decls.keys()),
            all_def_names=frozenset(def_decls.keys()),
            event_declarations=event_decls,
            def_declarations=def_decls,
            all_field_var_names=frozenset(field_var_decls.keys()),
            field_var_declarations=field_var_decls,
            all_block_ids=frozenset(block_ids),
            package_templates_dirs=self.package_templates_dirs,
            template_file_names=self.template_file_names,
        )
