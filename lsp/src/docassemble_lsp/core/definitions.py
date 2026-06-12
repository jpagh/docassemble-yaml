from __future__ import annotations

import ast
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from docassemble_lsp.core.definition_models import (
    BlockScalarRegion,
    DefinitionTarget,
    EventHelperOccurrence,
    ReferenceRequest,
    WorkspaceSymbolTarget,
)
from docassemble_lsp.core.document_facts import build_document_facts
from docassemble_lsp.core.field_keys import FIELD_ITEM_KNOWN_KEYS
from docassemble_lsp.core.files import (
    _discover_package_roots,
    collect_template_file_names,
    detect_docassemble_package,
    discover_templates_dir,
    resolve_static_target,
    safe_iterdir,
)
from docassemble_lsp.core.python_modules import (
    VENDORED_MODULE_NAMES,
    collect_class_names,
    collect_non_exception_class_names,
    compute_da_object_subclasses,
    load_python_module_index,
    resolve_python_module_source,
)
from docassemble_lsp.core.python_navigation import PythonNavigationService
from docassemble_lsp.core.python_navigation import (
    _iter_top_level_list_items as _iter_yaml_list_items,
)
from docassemble_lsp.core.python_paths import (
    is_python_path as _is_python_path,
)
from docassemble_lsp.core.python_paths import (
    is_yaml_path as _is_yaml_path,
)
from docassemble_lsp.core.python_paths import (
    path_from_uri_or_path as _path_from_uri_or_path,
)
from docassemble_lsp.core.python_paths import (
    resolve_package_qualified_path_with_base,
)
from docassemble_lsp.core.schema_models import HoverInfo
from docassemble_lsp.core.workspace import WorkspaceIndex, WorkspaceYamlSources
from docassemble_lsp.core.workspace_navigation import WorkspaceNavigationService
from docassemble_lsp.core.workspace_symbols import WorkspaceSymbolService
from docassemble_lsp.core.yaml_shared import (
    _BLOCK_SCALAR_MARKERS,
    _EVENT_REFERENCE_KEYS,
    _FIELD_CONDITION_KEYS,
    _FILE_REFERENCE_KEYS,
    _FILE_REFERENCE_LIST_PARENTS,
    _KEY_VALUE_RE,
    _LIST_ITEM_VALUE_RE,
    _MAKO_EXPRESSION_RE,
    _ancestor_keys,
    _NON_ATTACHMENT_FILE_KEYS,
    _PYTHON_BLOCK_KEYS,
    _STATIC_FILE_PARENT_KEYS,
    _block_scalar_region_from_key_line,
    _clean_value,
    _clean_value_and_range,
    _document_lines,
    _iter_mako_block_regions,
    _line_col_to_offset,
    _precompute_parent_keys,
)

logger = logging.getLogger(__name__)

_EVENT_HELPER_ARGUMENT_INDEX = {
    "url_action": 0,
    "action_menu_item": 1,
}


def _match_value_context_with_range(
    source: str,
    line: int,
    character: int,
) -> tuple[str | None, str | None, int, int]:
    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]

    list_match = _LIST_ITEM_VALUE_RE.match(text)
    if list_match is not None:
        raw_value = list_match.group(2)
        value, start, end = _clean_value_and_range(raw_value, list_match.start(2), list_match.end(2))
        if value and ":" in value and start <= character <= end:
            ancestors = _ancestor_keys(source, line)
            parent = ancestors[0] if ancestors else None
            if parent in _FILE_REFERENCE_LIST_PARENTS:
                return (parent, value, start, end)

    key_match = _KEY_VALUE_RE.match(text)
    if key_match is not None:
        raw_value = key_match.group(3)
        value, start, end = _clean_value_and_range(raw_value, key_match.start(3), key_match.end(3))
        if value and value not in _BLOCK_SCALAR_MARKERS:
            # Check for a package-qualified list item: ``- docassemble.pkg:file.path``
            # KEY_VALUE_RE splits it as key=``docassemble.pkg``, value=``file.path``.
            # If the cursor sits anywhere in the full ``pkg:path`` span, return the
            # reconstructed reference so callers can navigate to the target file.
            between = text[key_match.end(1) : key_match.start(2)]
            if "-" in between and "." in key_match.group(2):
                key_name = key_match.group(2).strip()
                full_value = f"{key_name}:{value}"
                full_start = key_match.start(2)
                if full_start <= character <= end:
                    ancestors = _ancestor_keys(source, line)
                    parent = ancestors[0] if ancestors else None
                    if parent in _FILE_REFERENCE_LIST_PARENTS:
                        return (parent, full_value, full_start, end)
            if start <= character <= end:
                return (key_match.group(2).strip(), value, start, end)

    list_match = _LIST_ITEM_VALUE_RE.match(text)
    if list_match is not None and ":" not in list_match.group(2):
        raw_value = list_match.group(2)
        value, start, end = _clean_value_and_range(raw_value, list_match.start(2), list_match.end(2))
        if value:
            if start <= character <= end:
                ancestors = _ancestor_keys(source, line)
                parent = ancestors[0] if ancestors else None
                return (parent, value, start, end)

    return (None, None, 0, 0)


def _match_value_context(source: str, line: int, character: int) -> tuple[str | None, str | None]:
    key_or_parent, value, _start, _end = _match_value_context_with_range(source, line, character)
    return (key_or_parent, value)


_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _extract_symbol_at_position(source: str, line: int, character: int) -> str | None:
    """Extract the Python identifier at the given cursor position.

    Only returns a simple identifier (alphanumeric + underscore, no dots).
    For dotted chains like ``helper_utils.plus_one``, the cursor must be
    on the segment of interest (e.g. ``plus_one``) to resolve just that name.
    """
    lines = _document_lines(source)
    if line < 0 or line >= len(lines):
        return None
    text = lines[line]
    if character < 0 or character > len(text):
        return None
    start = character
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
        start -= 1
    end = character
    while end < len(text) and (text[end].isalnum() or text[end] == "_"):
        end += 1
    if start == end:
        return None
    word = text[start:end]
    if not _WORD_RE.fullmatch(word):
        return None
    return word


def _collect_python_modules(package_root: Path) -> frozenset[Path]:
    """Collect top-level .py files in the docassemble package's Python directory.

    Only collects ``*.py`` files directly inside ``docassemble/<pkg>/``,
    not subdirectories.  This avoids indexing alembic migrations, test
    utilities, or other nested Python files that aren't part of the
    application module surface.  Cross-package discovery
    (``_discover_cross_package_modules``) uses ``rglob`` because we
    don't control external package layout.
    """
    docassemble_dir = package_root / "docassemble"
    if not docassemble_dir.is_dir():
        return frozenset()
    modules: set[Path] = set()
    for pkg_dir in safe_iterdir(docassemble_dir):
        if not pkg_dir.is_dir() or not (pkg_dir / "__init__.py").is_file():
            continue
        for py_file in pkg_dir.glob("*.py"):
            modules.add(py_file.resolve())
    return frozenset(modules)


_CROSS_PKG_LIST_KEYS = frozenset({"modules", "imports", "include"})
_CROSS_PACKAGE_RE = re.compile(r"^docassemble\.(\w+)")


def python_discovery_signature(source: str) -> frozenset[str]:
    refs: set[str] = set()
    for key in _CROSS_PKG_LIST_KEYS:
        for _line, entry in _iter_yaml_list_items(source, key):
            pkg_match = _CROSS_PACKAGE_RE.match(entry)
            if pkg_match is not None:
                refs.add(f"docassemble.{pkg_match.group(1)}")
    return frozenset(refs)


def _discover_cross_package_modules(
    yaml_sources: WorkspaceYamlSources,
    package_root: Path,
    search_roots: tuple[Path, ...] = (),
) -> frozenset[Path]:
    """Discover Python modules from external docassemble packages.

    Scans ``modules:``, ``imports:``, and ``include:`` list items in all
    YAML sources for ``docassemble.<pkg>`` references, then resolves each
    unique package from the Python environment and returns all its Python
    module paths.

    Only the directive contexts listed above are scanned — code blocks
    and string values are ignored to avoid false positives.
    """
    seen_pkgs: set[str] = set()
    external_paths: set[Path] = set()
    for source in yaml_sources.sources:
        for pkg_name in sorted(python_discovery_signature(source.text)):
            if pkg_name in seen_pkgs:
                continue
            seen_pkgs.add(pkg_name)

            # Build a lightweight workspace index with search roots.
            pkg_index = WorkspaceIndex.empty_for_roots(search_roots)
            # Resolve the package's __init__ to find its location.
            try:
                resolution = resolve_python_module_source(
                    f"{pkg_name}.__init__",
                    current_path=source.path,
                    workspace_index=pkg_index,
                )
            except (ModuleNotFoundError, ValueError):
                logger.debug(
                    "Cross-package %s referenced from %s not found in environment",
                    pkg_name,
                    source.path,
                )
                continue

            if resolution.path is None or resolution.source_kind not in (
                "workspace",
                "environment",
            ):
                logger.debug(
                    "Cross-package %s referenced from %s could not be resolved (kind=%s)",
                    pkg_name,
                    source.path,
                    resolution.source_kind if resolution.path else "none",
                )
                continue

            pkg_dir = resolution.path.resolve().parent
            # Skip if this is our own package.
            try:
                pkg_dir.relative_to(package_root)
                continue
            except ValueError:
                pass

            # If it's a docassemble package (has data/questions/), collect only
            # top-level .py files to avoid alembic, tests, etc. Otherwise,
            # fall back to a full recursive scan.
            if (pkg_dir / "data" / "questions").is_dir():
                for py_file in pkg_dir.glob("*.py"):
                    external_paths.add(py_file.resolve())
            else:
                for py_file in pkg_dir.rglob("*.py"):
                    external_paths.add(py_file.resolve())

    return frozenset(external_paths)


def _build_flat_caches(
    module_paths: frozenset[Path],
) -> tuple[frozenset[str], frozenset[str], frozenset[str], dict[str, frozenset[DefinitionTarget]], dict[str, str]]:
    """Build flat caches of class names, non-exception class names, custom datatype names,
    a symbol registry, and a docstring map.

    The symbol registry maps each top-level name to all its definition
    locations across all module paths.  The docstring map stores the
    first docstring encountered per name so hover doesn't need to
    re-load individual module indexes.
    """
    logger.debug("Building flat caches from %d module paths", len(module_paths))
    classes: set[str] = set()
    non_exception_classes: set[str] = set()
    datatypes: set[str] = set()
    registry: dict[str, set[DefinitionTarget]] = {}
    docstrings: dict[str, str] = {}
    for mod_path in module_paths:
        index = load_python_module_index(mod_path)
        classes.update(collect_class_names(index))
        non_exception_classes.update(collect_non_exception_class_names(index))
        datatypes.update(index.custom_datatype_names)
        for name, sym in index.symbols.items():
            if sym.target is not None:
                registry.setdefault(name, set()).add(sym.target)
            if sym.docstring is not None and name not in docstrings:
                docstrings[name] = sym.docstring
    return (
        frozenset(classes),
        frozenset(non_exception_classes),
        frozenset(datatypes),
        {k: frozenset(v) for k, v in registry.items()},
        docstrings,
    )


@dataclass(frozen=True, slots=True)
class _VendoredStubData:
    class_names: frozenset[str]
    non_exception_class_names: frozenset[str]
    custom_datatype_names: frozenset[str]
    symbol_registry: dict[str, frozenset[DefinitionTarget]]
    docstring_registry: dict[str, str]
    vendored_paths: list[Path]


def _load_vendored_stubs() -> _VendoredStubData:
    vendored_mutable: dict[str, set[DefinitionTarget]] = {}
    vendored_docstrings: dict[str, str] = {}
    vendored_paths: list[Path] = []
    class_names: set[str] = set()
    non_exception_class_names: set[str] = set()
    custom_datatype_names: set[str] = set()

    for module_name in VENDORED_MODULE_NAMES:
        vendored_path = resolve_python_module_source(
            module_name,
            workspace_index=WorkspaceIndex.empty(),
        ).path
        if vendored_path is not None:
            vendored_paths.append(vendored_path)
            vendored_index = load_python_module_index(vendored_path)
            class_names |= collect_class_names(vendored_index)
            non_exception_class_names |= collect_non_exception_class_names(vendored_index)
            custom_datatype_names |= vendored_index.custom_datatype_names
            for name, sym in vendored_index.symbols.items():
                if sym.target is not None:
                    vendored_mutable.setdefault(name, set()).add(sym.target)
                if sym.docstring is not None and name not in vendored_docstrings:
                    vendored_docstrings[name] = sym.docstring

    return _VendoredStubData(
        class_names=frozenset(class_names),
        non_exception_class_names=frozenset(non_exception_class_names),
        custom_datatype_names=frozenset(custom_datatype_names),
        symbol_registry={k: frozenset(v) for k, v in vendored_mutable.items()},
        docstring_registry=vendored_docstrings,
        vendored_paths=vendored_paths,
    )


def build_workspace_index(
    search_roots: list[Path],
    *,
    current_path: Path | None = None,
    current_source: str | None = None,
    overlays: Mapping[Path, str] | None = None,
    existing_sources: WorkspaceYamlSources | None = None,
) -> WorkspaceIndex:
    from dataclasses import replace

    resolved_search_roots = tuple(root.resolve() for root in search_roots)
    if existing_sources is not None:
        sources = existing_sources.with_overlays(overlays) if overlays else existing_sources
        index = WorkspaceIndex(
            yaml_sources=sources,
            facts_by_path={source.path: tuple(build_document_facts(source.text)) for source in sources.sources},
            search_roots=resolved_search_roots,
        )
    else:
        index = WorkspaceIndex.from_yaml_roots(
            search_roots,
            current_path=current_path,
            current_source=current_source,
            overlays=overlays,
        )

    detect_path = current_path or (search_roots[0] if search_roots else None)
    package_root = detect_docassemble_package(detect_path) if detect_path is not None else None

    # Collect ALL package roots in the workspace.
    all_package_roots: list[Path] = []
    if package_root is not None:
        all_package_roots.append(package_root)
    if search_roots:
        discovered = _discover_package_roots(search_roots)
        for pr in discovered:
            if pr not in all_package_roots:
                all_package_roots.append(pr)

    # Build per-package templates dir mapping (pre-computed, no filesystem at resolution time).
    package_templates_dirs: dict[Path, Path] = {}
    for pr in all_package_roots:
        tdir = discover_templates_dir(pr)
        if tdir is not None:
            package_templates_dirs[pr.resolve()] = tdir.resolve()

    # Aggregate template filenames from ALL packages (for completions).
    all_names: set[str] = set()
    for tdir in package_templates_dirs.values():
        all_names.update(collect_template_file_names(tdir))
    template_file_names: frozenset[str] = frozenset(all_names)

    event_decls: dict[str, DefinitionTarget] = {}
    def_decls: dict[str, DefinitionTarget] = {}
    for source in index.yaml_sources.sources:
        for fact in index.facts_by_path.get(source.path, ()):
            for kf in fact.keys:
                value = _clean_value(kf.value)
                if kf.name == "event" and value:
                    event_decls.setdefault(
                        value,
                        DefinitionTarget(path=source.path, line=kf.line, start_character=0, end_character=0),
                    )
                elif kf.name == "def" and value:
                    def_decls.setdefault(
                        value,
                        DefinitionTarget(path=source.path, line=kf.line, start_character=0, end_character=0),
                    )
    all_event_names = frozenset(event_decls.keys())
    all_def_names = frozenset(def_decls.keys())

    # Build field_var_declarations and all_block_ids by scanning all sources.
    field_var_decls: dict[str, DefinitionTarget] = {}
    block_ids: set[str] = set()
    for source in index.yaml_sources.sources:
        for fact in index.facts_by_path.get(source.path, ()):
            for kf in fact.keys:
                value = _clean_value(kf.value)
                if kf.name == "id" and value:
                    block_ids.add(value)
        lines = _document_lines(source.text)
        parents = _precompute_parent_keys(source.text)
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
            if key_name == "field" or key_name not in FIELD_ITEM_KNOWN_KEYS:
                field_var_decls.setdefault(
                    value,
                    DefinitionTarget(
                        path=source.path,
                        line=line_index,
                        start_character=start_character,
                        end_character=end_character,
                    ),
                )
    all_field_var_names = frozenset(field_var_decls.keys())
    all_block_ids_frozen = frozenset(block_ids)

    workspace_module_paths: frozenset[Path] = frozenset()
    workspace_class_names: frozenset[str] = frozenset()
    workspace_non_exception: frozenset[str] = frozenset()
    workspace_custom_dt: frozenset[str] = frozenset()
    workspace_registry: dict[str, frozenset[DefinitionTarget]] = {}
    workspace_docstrings: dict[str, str] = {}

    if package_root is not None:
        workspace_module_paths = _collect_python_modules(package_root)
        cross_module_paths = _discover_cross_package_modules(index.yaml_sources, package_root, index.search_roots)
        workspace_module_paths = workspace_module_paths | cross_module_paths
        (
            workspace_class_names,
            workspace_non_exception,
            workspace_custom_dt,
            workspace_registry,
            workspace_docstrings,
        ) = _build_flat_caches(workspace_module_paths)

    vendored = _load_vendored_stubs()

    all_class_names = workspace_class_names | vendored.class_names
    all_non_exception_class_names = workspace_non_exception | vendored.non_exception_class_names
    all_custom_datatype_names = workspace_custom_dt | vendored.custom_datatype_names

    final_registry: dict[str, frozenset[DefinitionTarget]] = {}
    final_registry.update(workspace_registry)
    for name, targets in vendored.symbol_registry.items():
        merged = set(targets) | set(workspace_registry.get(name, frozenset()))
        final_registry[name] = frozenset(merged)

    final_docstrings: dict[str, str] = {}
    final_docstrings.update(vendored.docstring_registry)
    final_docstrings.update(workspace_docstrings)

    da_object_subclass_names = compute_da_object_subclasses(list(workspace_module_paths) + vendored.vendored_paths)

    return replace(
        index,
        package_root=package_root,
        all_custom_datatype_names=all_custom_datatype_names,
        all_class_names=all_class_names,
        all_non_exception_class_names=all_non_exception_class_names,
        all_da_object_subclass_names=da_object_subclass_names,
        all_module_paths=workspace_module_paths,
        symbol_registry=final_registry,
        docstring_registry=final_docstrings,
        all_event_names=all_event_names,
        all_def_names=all_def_names,
        event_declarations=event_decls,
        def_declarations=def_decls,
        all_field_var_names=all_field_var_names,
        field_var_declarations=field_var_decls,
        all_block_ids=all_block_ids_frozen,
        package_templates_dirs=package_templates_dirs,
        template_file_names=template_file_names,
    )


def overlay_workspace_documents(
    workspace_index: WorkspaceIndex,
    overlays: Mapping[Path, str],
    *,
    refresh_python: bool = False,
) -> WorkspaceIndex:
    if not overlays:
        return workspace_index
    if refresh_python:
        return build_workspace_index(
            list(workspace_index.search_roots),
            overlays=overlays,
            existing_sources=workspace_index.yaml_sources,
        )
    return workspace_index.with_overlays(overlays)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _event_helper_occurrences(text: str) -> list[EventHelperOccurrence]:
    parse_text = text
    first_line_offset = 0
    try:
        tree = ast.parse(parse_text)
    except SyntaxError:
        parse_text = text.lstrip()
        first_line_offset = len(text) - len(parse_text)
        try:
            tree = ast.parse(parse_text)
        except SyntaxError:
            return []

    occurrences: list[EventHelperOccurrence] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        helper_name = _call_name(node.func)
        if helper_name is None:
            continue
        argument_index = _EVENT_HELPER_ARGUMENT_INDEX.get(helper_name)
        if argument_index is None or len(node.args) <= argument_index:
            continue
        argument = node.args[argument_index]
        if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
            continue
        line_number = getattr(argument, "lineno", None)
        end_col_offset = getattr(argument, "end_col_offset", None)
        if line_number is None or end_col_offset is None:
            continue
        start_character = argument.col_offset + (first_line_offset if line_number == 1 else 0)
        end_character = end_col_offset + (first_line_offset if line_number == 1 else 0)
        literal_line = (
            parse_text.splitlines()[line_number - 1] if line_number - 1 < len(parse_text.splitlines()) else ""
        )
        literal_text = literal_line[argument.col_offset : end_col_offset]
        value_offset = literal_text.find(argument.value)
        if value_offset != -1:
            start_character = argument.col_offset + value_offset + (first_line_offset if line_number == 1 else 0)
            end_character = start_character + len(argument.value)
        occurrences.append(
            EventHelperOccurrence(
                name=argument.value,
                line=line_number - 1,
                start_character=start_character,
                end_character=end_character,
            )
        )

    occurrences.sort(key=lambda occurrence: (occurrence.line, occurrence.start_character, occurrence.end_character))
    return occurrences


def _event_helper_request_in_text(text: str, line: int, character: int) -> ReferenceRequest | None:
    for occurrence in _event_helper_occurrences(text):
        if occurrence.line != line:
            continue
        if occurrence.start_character <= character <= occurrence.end_character and ":" not in occurrence.name:
            return ReferenceRequest(kind="event", name=occurrence.name)
    return None


def _event_helper_request_at_position(source: str, line: int, character: int) -> ReferenceRequest | None:
    region = _enclosing_block_scalar_region(source, line)
    if region is not None and region.key_name in _PYTHON_BLOCK_KEYS:
        local_line = line - region.content_start_line
        local_character = max(character - region.content_indent, 0)
        request = _event_helper_request_in_text(region.text, local_line, local_character)
        if request is not None:
            return request

    lines = _document_lines(source)
    text = lines[min(max(line, 0), len(lines) - 1)]

    cursor_offset = _line_col_to_offset(lines, line, character)
    for mako_region in _iter_mako_block_regions(source):
        if mako_region.is_expression:
            continue
        if not (mako_region.content_start_offset <= cursor_offset < mako_region.content_end_offset):
            continue
        local_offset = cursor_offset - mako_region.content_start_offset
        code_before = mako_region.code_text[:local_offset]
        local_line = code_before.count("\n")
        last_nl = code_before.rfind("\n")
        local_char = local_offset - last_nl - 1 if last_nl != -1 else local_offset
        request = _event_helper_request_in_text(mako_region.code_text, local_line, local_char)
        if request is not None:
            return request

    for match in _MAKO_EXPRESSION_RE.finditer(text):
        if not (match.start(1) <= character <= match.end(1)):
            continue
        request = _event_helper_request_in_text(match.group(1), 0, character - match.start(1))
        if request is not None:
            return request

    stripped = text.lstrip()
    if not stripped.startswith("%"):
        return None

    percent_index = text.index("%")
    statement = text[percent_index + 1 :].lstrip()
    if not statement:
        return None
    statement_start = percent_index + 1 + len(text[percent_index + 1 :]) - len(statement)
    if character < statement_start:
        return None
    return _event_helper_request_in_text(statement, 0, character - statement_start)


def _iter_event_helper_occurrences(source: str) -> list[EventHelperOccurrence]:
    occurrences: list[EventHelperOccurrence] = []
    for region in _iter_block_scalar_regions(source):
        if region.key_name not in _PYTHON_BLOCK_KEYS:
            continue
        for occurrence in _event_helper_occurrences(region.text):
            occurrences.append(
                EventHelperOccurrence(
                    name=occurrence.name,
                    line=region.content_start_line + occurrence.line,
                    start_character=region.content_indent + occurrence.start_character,
                    end_character=region.content_indent + occurrence.end_character,
                )
            )

    for mako_region in _iter_mako_block_regions(source):
        if mako_region.is_expression:
            continue
        # Convert content_start_offset to (line, start_char) for occurrence mapping
        content_before = source[: mako_region.content_start_offset]
        base_line = content_before.count("\n")
        last_nl = content_before.rfind("\n")
        base_col = mako_region.content_start_offset - last_nl - 1 if last_nl != -1 else mako_region.content_start_offset
        for occurrence in _event_helper_occurrences(mako_region.code_text):
            occurrences.append(
                EventHelperOccurrence(
                    name=occurrence.name,
                    line=base_line + occurrence.line,
                    start_character=base_col + occurrence.start_character,
                    end_character=base_col + occurrence.end_character,
                )
            )

    for line_index, text in enumerate(_document_lines(source)):
        for match in _MAKO_EXPRESSION_RE.finditer(text):
            for occurrence in _event_helper_occurrences(match.group(1)):
                occurrences.append(
                    EventHelperOccurrence(
                        name=occurrence.name,
                        line=line_index + occurrence.line,
                        start_character=match.start(1) + occurrence.start_character,
                        end_character=match.start(1) + occurrence.end_character,
                    )
                )

        stripped = text.lstrip()
        if not stripped.startswith("%"):
            continue
        percent_index = text.index("%")
        statement = text[percent_index + 1 :].lstrip()
        if not statement:
            continue
        statement_start = percent_index + 1 + len(text[percent_index + 1 :]) - len(statement)
        for occurrence in _event_helper_occurrences(statement):
            occurrences.append(
                EventHelperOccurrence(
                    name=occurrence.name,
                    line=line_index + occurrence.line,
                    start_character=statement_start + occurrence.start_character,
                    end_character=statement_start + occurrence.end_character,
                )
            )

    return occurrences


def _enclosing_block_scalar_region(source: str, line: int) -> BlockScalarRegion | None:
    lines = _document_lines(source)
    for key_line in range(min(line, len(lines) - 1), -1, -1):
        text = lines[key_line]
        if text.strip() == "---":
            break
        match = _KEY_VALUE_RE.match(text)
        if match is None:
            continue
        raw_value = match.group(3).strip()
        if raw_value not in _BLOCK_SCALAR_MARKERS:
            continue
        region = _block_scalar_region_from_key_line(lines, key_line, match.group(2).strip(), len(match.group(1)))
        if region.content_start_line <= line <= region.end_line:
            return region
    return None


def _iter_block_scalar_regions(source: str) -> list[BlockScalarRegion]:
    lines = _document_lines(source)
    regions: list[BlockScalarRegion] = []
    line_index = 0
    while line_index < len(lines):
        text = lines[line_index]
        match = _KEY_VALUE_RE.match(text)
        if match is None:
            line_index += 1
            continue
        raw_value = match.group(3).strip()
        if raw_value not in _BLOCK_SCALAR_MARKERS:
            line_index += 1
            continue
        region = _block_scalar_region_from_key_line(lines, line_index, match.group(2).strip(), len(match.group(1)))
        regions.append(region)
        line_index = max(region.end_line + 1, line_index + 1)
    return regions


def _resolve_local_file_reference(
    current_path: Path | None,
    target: str,
    search_roots: tuple[Path, ...] = (),
    templates_dir: Path | None = None,
    *,
    relative_base: str | None = None,
) -> list[DefinitionTarget]:
    if current_path is None or not target:
        return []

    if ":" in target:
        resolved = resolve_package_qualified_path_with_base(target, list(search_roots), relative_base)
        if resolved is not None:
            return [DefinitionTarget(path=resolved, line=0, start_character=0, end_character=0)]
        return []

    resolved = (current_path.parent / target).resolve()
    if resolved.exists():
        return [DefinitionTarget(path=resolved, line=0, start_character=0, end_character=0)]

    if templates_dir is not None:
        template_path = (templates_dir / target).resolve()
        if template_path.exists():
            return [DefinitionTarget(path=template_path, line=0, start_character=0, end_character=0)]

    return []


def _resolve_def_reference(source: str, symbol_name: str, current_path: Path | None) -> list[DefinitionTarget]:
    if not symbol_name:
        return []

    target_path = current_path or Path(".")
    targets: list[DefinitionTarget] = []
    for fact in build_document_facts(source):
        for key_fact in fact.keys:
            if key_fact.name != "def":
                continue
            value = _clean_value(key_fact.value)
            if value != symbol_name:
                continue
            targets.append(
                DefinitionTarget(
                    path=target_path,
                    line=key_fact.line,
                    start_character=0,
                    end_character=len(_document_lines(source)[key_fact.line]),
                )
            )
    return targets


def _resolve_top_level_key_reference(
    source: str,
    *,
    key_name: str,
    symbol_name: str,
    current_path: Path | None,
) -> list[DefinitionTarget]:
    if not symbol_name:
        return []

    target_path = current_path or Path(".")
    lines = _document_lines(source)
    targets: list[DefinitionTarget] = []
    for fact in build_document_facts(source):
        for key_fact in fact.keys:
            if key_fact.name != key_name:
                continue
            value = _clean_value(key_fact.value)
            if value != symbol_name:
                continue
            targets.append(
                DefinitionTarget(
                    path=target_path,
                    line=key_fact.line,
                    start_character=0,
                    end_character=len(lines[key_fact.line]),
                )
            )
    return targets


def _symbol_request(source: str, line: int, character: int, current_path: Path | None) -> ReferenceRequest | None:
    key_or_parent, value = _match_value_context(source, line, character)
    if key_or_parent is not None and value is not None:
        if key_or_parent in {"def", "usedefs"}:
            return ReferenceRequest(kind="def", name=value)
        if key_or_parent in {"event", *_EVENT_REFERENCE_KEYS} and ":" not in value:
            return ReferenceRequest(kind="event", name=value)
        ancestors = _ancestor_keys(source, line)
        parent = ancestors[0] if ancestors else None
        if (
            key_or_parent in _FILE_REFERENCE_KEYS
            or key_or_parent in _FILE_REFERENCE_LIST_PARENTS
            or parent == "objects from file"
        ):
            if not value:
                return None
            if ":" in value:
                # Normalise bare filenames like pkg:file.yml → pkg:data/questions/file.yml
                # for non-attachment file keys (include, initial yaml, additional yaml).
                name = value
                if key_or_parent in _NON_ATTACHMENT_FILE_KEYS:
                    _pkg, _path = name.split(":", 1)
                    if not _path.startswith("data/"):
                        name = f"{_pkg}:data/questions/{_path}"
                return ReferenceRequest(kind="file", name=name, target_path=None)
            if current_path is None:
                return None
            return ReferenceRequest(kind="file", name=value, target_path=(current_path.parent / value).resolve())
        if parent == "fields" and (key_or_parent == "field" or key_or_parent not in FIELD_ITEM_KNOWN_KEYS):
            if value and ":" not in value:
                return ReferenceRequest(kind="field_var", name=value)
        if key_or_parent == "variable" and parent in _FIELD_CONDITION_KEYS:
            if value and ":" not in value:
                return ReferenceRequest(kind="field_var", name=value)

    helper_request = _event_helper_request_at_position(source, line, character)
    if helper_request is not None:
        return helper_request

    if current_path is not None and not _is_yaml_path(current_path) and not _is_python_path(current_path):
        return ReferenceRequest(kind="file", name=current_path.name, target_path=current_path.resolve())

    return None


def _workspace_navigation_service(workspace_index: WorkspaceIndex) -> WorkspaceNavigationService:
    return WorkspaceNavigationService(workspace_index, _iter_event_helper_occurrences)


def _python_navigation_service(workspace_index: WorkspaceIndex) -> PythonNavigationService:
    return PythonNavigationService(workspace_index)


def _resolve_workspace_symbol_definitions(
    request: ReferenceRequest,
    workspace_index: WorkspaceIndex,
) -> list[DefinitionTarget]:
    return WorkspaceSymbolService(workspace_index).definitions_for(request)


def resolve_workspace_symbol_targets(
    query: str,
    *,
    workspace_index: WorkspaceIndex,
) -> list[WorkspaceSymbolTarget]:
    return WorkspaceSymbolService(workspace_index).symbols(query)


def resolve_reference_targets(
    source: str,
    line: int,
    character: int,
    *,
    uri_or_path: str | Path | None = None,
    include_declaration: bool = True,
    workspace_index: WorkspaceIndex,
) -> list[DefinitionTarget]:
    current_path = _path_from_uri_or_path(uri_or_path)

    request = _symbol_request(source, line, character, current_path)
    if request is None:
        return []

    if request.kind in {"def", "event", "field_var"}:
        if current_path is None and request.kind != "field_var":
            return []
        return _workspace_navigation_service(workspace_index).symbol_occurrences(
            request,
            include_declaration=include_declaration,
        )

    # For file references, resolve the target path if it wasn't set (package-qualified).
    effective_request = request
    if request.kind == "file" and request.target_path is None:
        resolved = resolve_package_qualified_path_with_base(request.name, list(workspace_index.search_roots), None)
        if resolved is None:
            return []
        effective_request = ReferenceRequest(kind="file", name=request.name, target_path=resolved)

    target_path = effective_request.target_path
    if target_path is None:
        return []

    del target_path
    return _workspace_navigation_service(workspace_index).file_references(
        effective_request,
        include_declaration=include_declaration,
    )


def resolve_python_hover(
    source: str,
    line: int,
    character: int,
    *,
    workspace_index: WorkspaceIndex,
) -> HoverInfo | None:
    """Provide hover documentation for Python symbols in YAML.

    Uses the flat symbol registry to look up the symbol at the cursor
    and return its docstring and type information.  Docstrings are
    pre-extracted during indexing, so this is a pure dict lookup with
    no module parsing at hover time.
    """
    if not workspace_index.symbol_registry:
        return None
    symbol_name = _extract_symbol_at_position(source, line, character)
    if symbol_name is None or symbol_name not in workspace_index.symbol_registry:
        return None

    targets = workspace_index.symbol_registry[symbol_name]
    if not targets:
        return None

    first_target = next(iter(targets))

    # Determine the symbol kind from the module index (still cached).
    kind_str: str = "symbol"
    module_index = load_python_module_index(first_target.path)
    sym = module_index.symbols.get(symbol_name)
    if sym is not None:
        kind_str = sym.kind

    kind_icon = {"function": "def", "class": "class", "symbol": "symbol"}.get(kind_str, "symbol")
    lines: list[str] = []
    lines.append(f"**{kind_icon}** `{symbol_name}`")
    lines.append("")
    doc = workspace_index.docstring_registry.get(symbol_name)
    if doc:
        lines.append(doc)
    lines.append("")
    lines.append(f"*Defined in `{first_target.path.name}:{first_target.line + 1}` — click to navigate*")
    return HoverInfo(contents="\n".join(lines))


def resolve_definition_targets(
    source: str,
    line: int,
    character: int,
    *,
    uri_or_path: str | Path | None = None,
    workspace_index: WorkspaceIndex,
) -> list[DefinitionTarget]:
    from docassemble_lsp.core.document_links import resolve_document_link_target_at

    current_path = _path_from_uri_or_path(uri_or_path)

    # First check if the cursor is on a file/module reference that the document
    # link resolver already knows how to handle — this gives us the correct
    # source range for underlines while keeping the same resolution logic.
    if current_path is not None:
        link_target = resolve_document_link_target_at(
            source,
            line,
            character,
            uri_or_path=uri_or_path,
            search_roots=workspace_index.search_roots,
            workspace_index=workspace_index,
        )
        if link_target is not None:
            logger.debug(
                "Definition from doc link: line=%d range=%d-%d target=%s",
                link_target.line,
                link_target.start_character,
                link_target.end_character,
                link_target.target_path,
            )
            return [
                DefinitionTarget(
                    path=link_target.target_path,
                    line=0,
                    start_character=0,
                    end_character=0,
                )
            ]

    key_or_parent, value = _match_value_context(source, line, character)

    if current_path is not None and key_or_parent in _STATIC_FILE_PARENT_KEYS and value is not None:
        target_path = resolve_static_target(current_path, value)
        if target_path is None:
            return []
        return [DefinitionTarget(path=target_path, line=0, start_character=0, end_character=0)]

    # Flat-model go-to-def: look up symbol by name directly in the registry.
    if workspace_index.symbol_registry and current_path is not None:
        symbol_name = _extract_symbol_at_position(source, line, character)
        if symbol_name is not None and symbol_name in workspace_index.symbol_registry:
            return sorted(
                workspace_index.symbol_registry[symbol_name],
                key=lambda t: (t.path, t.line),
            )

    module_targets = _python_navigation_service(workspace_index).module_targets(
        key_or_parent,
        value,
        current_path,
    )
    if module_targets:
        return module_targets

    helper_request = _event_helper_request_at_position(source, line, character)
    if helper_request is not None:
        return _resolve_workspace_symbol_definitions(
            helper_request,
            workspace_index,
        )

    if key_or_parent is None or value is None:
        return []

    ancestors = _ancestor_keys(source, line)
    parent = ancestors[0] if ancestors else None

    if key_or_parent == "usedefs":
        return _resolve_workspace_symbol_definitions(
            ReferenceRequest(kind="def", name=value),
            workspace_index,
        )

    if key_or_parent in _EVENT_REFERENCE_KEYS and ":" not in value:
        return _resolve_workspace_symbol_definitions(
            ReferenceRequest(kind="event", name=value),
            workspace_index,
        )

    if key_or_parent in _FILE_REFERENCE_KEYS:
        relative_base = "data/questions" if key_or_parent in _NON_ATTACHMENT_FILE_KEYS else None
        tdir = workspace_index.templates_dir_for(current_path) if current_path is not None else None
        return _resolve_local_file_reference(
            current_path,
            value,
            workspace_index.search_roots,
            tdir,
            relative_base=relative_base,
        )

    if key_or_parent in _FILE_REFERENCE_LIST_PARENTS:
        relative_base = "data/questions" if key_or_parent in _NON_ATTACHMENT_FILE_KEYS else None
        tdir = workspace_index.templates_dir_for(current_path) if current_path is not None else None
        return _resolve_local_file_reference(
            current_path,
            value,
            workspace_index.search_roots,
            tdir,
            relative_base=relative_base,
        )

    if parent == "objects from file":
        tdir = workspace_index.templates_dir_for(current_path) if current_path is not None else None
        return _resolve_local_file_reference(
            current_path,
            value,
            workspace_index.search_roots,
            tdir,
        )

    if parent == "fields" and (key_or_parent == "field" or key_or_parent not in FIELD_ITEM_KNOWN_KEYS):
        if value and ":" not in value:
            return _workspace_navigation_service(workspace_index).field_var_declarations(
                ReferenceRequest(kind="field_var", name=value)
            )

    if key_or_parent == "variable" and parent in _FIELD_CONDITION_KEYS:
        if value and ":" not in value:
            return _workspace_navigation_service(workspace_index).field_var_declarations(
                ReferenceRequest(kind="field_var", name=value)
            )

    return []
