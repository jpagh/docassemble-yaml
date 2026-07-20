from __future__ import annotations

import logging
from pathlib import Path

from docassemble_lsp.core.definition_models import DocumentLinkTarget
from docassemble_lsp.core.files import (
    resolve_static_target,
    resolve_template_names,
    templates_dir_for_path,
)
from docassemble_lsp.core.python_modules import resolve_python_module_path
from docassemble_lsp.core.python_paths import (
    module_name_from_python_path,
    normalize_module_name,
    path_from_uri_or_path,
    resolve_package_qualified_path_with_base,
)
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_shared import (
    _ATTACHMENT_FILE_KEYS,
    _FILE_REFERENCE_KEYS,
    _FILE_REFERENCE_LIST_PARENTS,
    _KEY_VALUE_RE,
    _LIST_ITEM_VALUE_RE,
    _NON_ATTACHMENT_FILE_KEYS,
    _precompute_parent_keys,
    _STATIC_FILE_PARENT_KEYS,
    _ancestor_keys,
    _clean_value_and_range,
    _document_lines,
    _is_list_key_match,
)

logger = logging.getLogger(__name__)


def _resolved_local_target(current_path: Path, value: str) -> Path | None:
    if not value or ":" in value:
        return None
    try:
        target = (current_path.parent / value).resolve()
        return target if target.exists() else None
    except OSError as exc:
        logger.warning(
            "Local link resolution failed for %r from %s: %s", value, current_path, exc
        )
        return None


def _resolved_package_qualified_target(
    value: str,
    search_roots: tuple[Path, ...],
    *,
    relative_base: str | None = None,
) -> Path | None:
    if not value or ":" not in value:
        return None
    try:
        return resolve_package_qualified_path_with_base(
            value, list(search_roots), relative_base
        )
    except OSError as exc:
        logger.warning(
            "Package-qualified link resolution failed for %r: %s", value, exc
        )
        return None


def _append_link(
    links: list[DocumentLinkTarget],
    seen: set[tuple[int, int, int, Path]],
    *,
    line: int,
    start_character: int,
    end_character: int,
    target_path: Path,
) -> None:
    key = (line, start_character, end_character, target_path)
    if key in seen:
        return
    seen.add(key)
    links.append(
        DocumentLinkTarget(
            line=line,
            start_character=start_character,
            end_character=end_character,
            target_path=target_path,
        )
    )


def _workspace_module_paths_by_name(workspace_index: WorkspaceIndex) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for module_path in workspace_index.all_module_paths:
        module_name = module_name_from_python_path(module_path)
        if module_name is not None:
            paths.setdefault(module_name, module_path)
    return paths


def _check_line_for_document_link(
    source: str,
    line_index: int,
    text: str,
    *,
    current_path: Path,
    search_roots: tuple[Path, ...] = (),
    templates_dir: Path | None = None,
    template_file_names: frozenset[str] = frozenset(),
    workspace_index: WorkspaceIndex | None = None,
    workspace_module_paths: dict[str, Path] | None = None,
) -> DocumentLinkTarget | None:
    """Check a single line for a document-link target.

    Returns the first matching :class:`DocumentLinkTarget` on the line, or
    ``None``.  This replicates the line-level logic of
    :func:`resolve_document_link_targets` for a single position.
    """
    ancestors = _ancestor_keys(source, line_index)
    parent = ancestors[0] if ancestors else None

    # ---- Pattern 1: list item with colon — package-qualified ref -----------
    list_match = _LIST_ITEM_VALUE_RE.match(text)
    if list_match is not None:
        value, start_character, end_character = _clean_value_and_range(
            list_match.group(2),
            list_match.start(2),
            list_match.end(2),
        )
        if parent in _FILE_REFERENCE_LIST_PARENTS and ":" in value:
            relative_base = (
                "data/questions" if parent in _NON_ATTACHMENT_FILE_KEYS else None
            )
            target_path = _resolved_package_qualified_target(
                value, search_roots, relative_base=relative_base
            )
            if target_path is not None:
                return DocumentLinkTarget(
                    line=line_index,
                    start_character=start_character,
                    end_character=end_character,
                    target_path=target_path,
                )

    # ---- Pattern 2: key-value line ----------------------------------------
    key_match = _KEY_VALUE_RE.match(text)
    if key_match is not None:
        key_name = key_match.group(2).strip()
        value, start_character, end_character = _clean_value_and_range(
            key_match.group(3),
            key_match.start(3),
            key_match.end(3),
        )
        if key_name in _FILE_REFERENCE_KEYS or parent == "objects from file":
            target_path = None

            # ── Fast path: known template in validated names cache ──
            if (
                key_name in _ATTACHMENT_FILE_KEYS
                and templates_dir is not None
                and value in template_file_names
            ):
                target_path = (templates_dir / value).resolve()

            # ── Slow path: fallback resolution ──
            if target_path is None:
                target_path = _resolved_local_target(current_path, value)
                if target_path is None and search_roots:
                    relative_base = (
                        "data/questions"
                        if key_name in _NON_ATTACHMENT_FILE_KEYS
                        else None
                    )
                    target_path = _resolved_package_qualified_target(
                        value, search_roots, relative_base=relative_base
                    )
                if target_path is None and templates_dir is not None:
                    if value in template_file_names:
                        target_path = (templates_dir / value).resolve()
                    else:
                        try:
                            template_path = (templates_dir / value).resolve()
                            if template_path.exists():
                                target_path = template_path
                        except OSError:
                            pass

            if target_path is not None:
                return DocumentLinkTarget(
                    line=line_index,
                    start_character=start_character,
                    end_character=end_character,
                    target_path=target_path,
                )

        # Package-qualified list item: ``- docassemble.pkg:relative/path``
        if (
            search_roots
            and parent in _FILE_REFERENCE_LIST_PARENTS
            and _is_list_key_match(text, key_match)
            and value
            and "." in key_name
        ):
            full_value = f"{key_name}:{value}"
            relative_base = (
                "data/questions" if parent in _NON_ATTACHMENT_FILE_KEYS else None
            )
            target_path = _resolved_package_qualified_target(
                full_value, search_roots, relative_base=relative_base
            )
            if target_path is not None:
                return DocumentLinkTarget(
                    line=line_index,
                    start_character=key_match.start(2),
                    end_character=key_match.end(3),
                    target_path=target_path,
                )

    # ---- Pattern 3: list item without colon — local / module ref ----------
    list_match = _LIST_ITEM_VALUE_RE.match(text)
    if list_match is not None and ":" not in list_match.group(2):
        value, start_character, end_character = _clean_value_and_range(
            list_match.group(2),
            list_match.start(2),
            list_match.end(2),
        )
        if parent in _STATIC_FILE_PARENT_KEYS:
            target_path = resolve_static_target(current_path, value)
            if target_path is not None:
                return DocumentLinkTarget(
                    line=line_index,
                    start_character=start_character,
                    end_character=end_character,
                    target_path=target_path,
                )
            return None
        if parent not in _FILE_REFERENCE_LIST_PARENTS:
            return None
        if parent == "modules":
            if workspace_index is not None:
                normalized = normalize_module_name(value, current_path)
                if normalized is not None:
                    if workspace_module_paths is None:
                        workspace_module_paths = _workspace_module_paths_by_name(
                            workspace_index
                        )
                    target_path = workspace_module_paths.get(normalized)
                    if target_path is None:
                        try:
                            target_path = resolve_python_module_path(
                                normalized, current_path, workspace_index
                            )
                        except Exception:
                            target_path = None
                    if target_path is not None:
                        return DocumentLinkTarget(
                            line=line_index,
                            start_character=start_character,
                            end_character=end_character,
                            target_path=target_path,
                        )
            return None
        target_path = _resolved_local_target(current_path, value)
        if target_path is not None:
            return DocumentLinkTarget(
                line=line_index,
                start_character=start_character,
                end_character=end_character,
                target_path=target_path,
            )

    return None


def resolve_document_link_target_at(
    source: str,
    line: int,
    character: int,
    *,
    uri_or_path: str | Path | None = None,
    search_roots: tuple[Path, ...] = (),
    workspace_index: WorkspaceIndex | None = None,
) -> DocumentLinkTarget | None:
    """Return the :class:`DocumentLinkTarget` at ``(line, character)``, or
    ``None`` if the cursor is not on a recognised file/module reference.

    Unlike :func:`resolve_document_link_targets`, this does **not** scan
    every line of the document — it only checks the single line at the
    cursor position.
    """
    current_path = path_from_uri_or_path(uri_or_path)
    if current_path is None:
        return None
    templates_dir = (
        workspace_index.templates_dir_for(current_path)
        if workspace_index is not None
        else None
    )
    if templates_dir is None:
        templates_dir = templates_dir_for_path(current_path)
    template_file_names = resolve_template_names(templates_dir)
    lines = _document_lines(source)
    if not (0 <= line < len(lines)):
        return None
    text = lines[line]
    target = _check_line_for_document_link(
        source,
        line,
        text,
        current_path=current_path,
        search_roots=search_roots,
        templates_dir=templates_dir,
        template_file_names=template_file_names,
        workspace_index=workspace_index,
    )
    if (
        target is not None
        and target.start_character <= character <= target.end_character
    ):
        return target
    return None


def resolve_document_link_targets(
    source: str,
    *,
    uri_or_path: str | Path | None = None,
    search_roots: tuple[Path, ...] = (),
    workspace_index: WorkspaceIndex | None = None,
) -> list[DocumentLinkTarget]:
    current_path = path_from_uri_or_path(uri_or_path)
    if current_path is None:
        return []

    templates_dir = (
        workspace_index.templates_dir_for(current_path)
        if workspace_index is not None
        else None
    )
    if templates_dir is None:
        templates_dir = templates_dir_for_path(current_path)
    template_file_names = resolve_template_names(templates_dir)

    logger.debug(
        "Document links for %s: templates_dir=%s, search_roots=%s, template_files=%d",
        current_path,
        templates_dir,
        list(search_roots),
        len(template_file_names),
    )

    links: list[DocumentLinkTarget] = []
    seen: set[tuple[int, int, int, Path]] = set()
    workspace_module_paths: dict[str, Path] | None = None
    lines = _document_lines(source)
    parents = _precompute_parent_keys(source)
    for line_index, text in enumerate(lines):
        list_match = _LIST_ITEM_VALUE_RE.match(text)
        if list_match is not None:
            value, start_character, end_character = _clean_value_and_range(
                list_match.group(2),
                list_match.start(2),
                list_match.end(2),
            )
            parent = parents[line_index]
            if parent in _FILE_REFERENCE_LIST_PARENTS and ":" in value:
                relative_base = (
                    "data/questions" if parent in _NON_ATTACHMENT_FILE_KEYS else None
                )
                target_path = _resolved_package_qualified_target(
                    value, search_roots, relative_base=relative_base
                )
                if target_path is not None:
                    _append_link(
                        links,
                        seen,
                        line=line_index,
                        start_character=start_character,
                        end_character=end_character,
                        target_path=target_path,
                    )
                continue

        key_match = _KEY_VALUE_RE.match(text)
        if key_match is not None:
            key_name = key_match.group(2).strip()
            value, start_character, end_character = _clean_value_and_range(
                key_match.group(3),
                key_match.start(3),
                key_match.end(3),
            )
            parent = parents[line_index]
            if key_name in _FILE_REFERENCE_KEYS or parent == "objects from file":
                target_path = None

                # ── Fast path: known template in validated names cache ──
                if (
                    key_name in _ATTACHMENT_FILE_KEYS
                    and templates_dir is not None
                    and value in template_file_names
                ):
                    target_path = (templates_dir / value).resolve()

                # ── Slow path: fallback resolution ──
                if target_path is None:
                    target_path = _resolved_local_target(current_path, value)
                    if target_path is None and search_roots:
                        relative_base = (
                            "data/questions"
                            if key_name in _NON_ATTACHMENT_FILE_KEYS
                            else None
                        )
                        target_path = _resolved_package_qualified_target(
                            value, search_roots, relative_base=relative_base
                        )
                    if target_path is None and templates_dir is not None:
                        if value in template_file_names:
                            target_path = (templates_dir / value).resolve()
                        else:
                            try:
                                template_path = (templates_dir / value).resolve()
                                if template_path.exists():
                                    target_path = template_path
                            except OSError as exc:
                                logger.warning(
                                    "Template link resolution failed for %r: %s",
                                    value,
                                    exc,
                                )

                if target_path is not None:
                    _append_link(
                        links,
                        seen,
                        line=line_index,
                        start_character=start_character,
                        end_character=end_character,
                        target_path=target_path,
                    )
                continue

            # Package-qualified list item: ``- docassemble.pkg:relative/path``
            # The KEY_VALUE_RE captures ``pkg.name`` as key and ``path`` as value.
            if (
                search_roots
                and parent in _FILE_REFERENCE_LIST_PARENTS
                and _is_list_key_match(text, key_match)
                and value
                and "." in key_name
            ):
                full_value = f"{key_name}:{value}"
                relative_base = (
                    "data/questions" if parent in _NON_ATTACHMENT_FILE_KEYS else None
                )
                target_path = _resolved_package_qualified_target(
                    full_value, search_roots, relative_base=relative_base
                )
                if target_path is not None:
                    _append_link(
                        links,
                        seen,
                        line=line_index,
                        start_character=key_match.start(2),
                        end_character=key_match.end(3),
                        target_path=target_path,
                    )
            continue

        list_match = _LIST_ITEM_VALUE_RE.match(text)
        if list_match is None or ":" in list_match.group(2):
            continue
        value, start_character, end_character = _clean_value_and_range(
            list_match.group(2),
            list_match.start(2),
            list_match.end(2),
        )
        parent = parents[line_index]
        if parent in _STATIC_FILE_PARENT_KEYS:
            target_path = resolve_static_target(current_path, value)
            if target_path is not None:
                _append_link(
                    links,
                    seen,
                    line=line_index,
                    start_character=start_character,
                    end_character=end_character,
                    target_path=target_path,
                )
            continue
        if parent not in _FILE_REFERENCE_LIST_PARENTS:
            continue
        if parent == "modules":
            if workspace_index is not None:
                normalized = normalize_module_name(value, current_path)

                logger.debug(
                    "Module link: line=%d value=%r normalized=%r current_path=%s",
                    line_index,
                    value,
                    normalized,
                    current_path,
                )
                if normalized is not None:
                    if workspace_module_paths is None:
                        workspace_module_paths = _workspace_module_paths_by_name(
                            workspace_index
                        )
                    target_path = workspace_module_paths.get(normalized)
                    if target_path is not None:
                        logger.debug(
                            "Module link from workspace index: normalized=%r target_path=%s",
                            normalized,
                            target_path,
                        )
                    else:
                        try:
                            target_path = resolve_python_module_path(
                                normalized, current_path, workspace_index
                            )
                        except Exception as exc:
                            logger.debug(
                                "Module link resolution failed: normalized=%r error=%s",
                                normalized,
                                exc,
                            )
                            target_path = None
                    logger.debug(
                        "Module link resolved: normalized=%r target_path=%s",
                        normalized,
                        target_path,
                    )
                    if target_path is not None:
                        _append_link(
                            links,
                            seen,
                            line=line_index,
                            start_character=start_character,
                            end_character=end_character,
                            target_path=target_path,
                        )
            continue
        target_path = _resolved_local_target(current_path, value)

        logger.debug(
            "Local file link: line=%d parent=%r value=%r target_path=%s current_path=%s",
            line_index,
            parent,
            value,
            target_path,
            current_path,
        )
        if target_path is not None:
            _append_link(
                links,
                seen,
                line=line_index,
                start_character=start_character,
                end_character=end_character,
                target_path=target_path,
            )

    links.sort(
        key=lambda link: (
            link.line,
            link.start_character,
            link.end_character,
            str(link.target_path),
        )
    )
    logger.debug("Document links produced for %s: count=%d", current_path, len(links))
    return links
