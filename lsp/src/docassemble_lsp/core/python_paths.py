from __future__ import annotations

from pathlib import Path

from docassemble_lsp.core.files import detect_docassemble_package, safe_iterdir


def path_from_uri_or_path(uri_or_path: str | Path | None) -> Path | None:
    if uri_or_path is None:
        return None
    if isinstance(uri_or_path, Path):
        return uri_or_path
    text = str(uri_or_path)
    if text.startswith("file://"):
        from urllib.parse import unquote, urlparse

        parsed = urlparse(text)
        return Path(unquote(parsed.path))
    return Path(text)


def is_yaml_path(path: Path) -> bool:
    return path.suffix.lower() in {".yml", ".yaml"}


def is_python_path(path: Path) -> bool:
    return path.suffix.lower() == ".py"


def docassemble_package_dir(path: Path) -> Path | None:
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if candidate.parent.name == "docassemble":
            return candidate
    return None


def docassemble_package_name(path: Path) -> str | None:
    package_dir = docassemble_package_dir(path)
    if package_dir is None:
        return None
    return f"docassemble.{package_dir.name}"


def module_name_from_python_path(path: Path) -> str | None:
    package_dir = docassemble_package_dir(path)
    if package_dir is None:
        return None

    resolved = path.resolve()
    try:
        relative = resolved.relative_to(package_dir)
    except ValueError:
        return None

    if relative.suffix != ".py":
        return None

    module_parts = ["docassemble", package_dir.name, *relative.with_suffix("").parts]
    if module_parts[-1] == "__init__":
        module_parts.pop()
    return ".".join(module_parts)


def normalize_module_name(module_name: str, current_path: Path | None) -> str | None:
    if not module_name:
        return None
    if not module_name.startswith("."):
        return module_name

    if current_path is None:
        return None

    package_name = docassemble_package_name(current_path)
    if package_name is None:
        return None
    return f"{package_name}{module_name}"


def _strip_matching_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def _safe_package_relative_path(value: str) -> Path | None:
    path = Path(value)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        return None
    return path


def _candidate_package_dirs(package_name: str, search_roots: list[Path]) -> list[Path]:
    package_parts = package_name.split(".")
    if not package_parts or any(not part for part in package_parts):
        return []

    candidates: list[Path] = []
    seen: set[Path] = set()

    def append(candidate: Path) -> None:
        try:
            resolved = candidate.resolve()
        except OSError:
            return
        if resolved in seen:
            return
        seen.add(resolved)
        candidates.append(resolved)

    for root in search_roots:
        resolved_root = root.resolve()
        append(resolved_root.joinpath(*package_parts))

        package_dir = docassemble_package_dir(resolved_root)
        if package_dir is not None and docassemble_package_name(package_dir) == package_name:
            append(package_dir)

        # Scan subdirectories for packages matching this name.
        if resolved_root.is_dir():
            for subdir in safe_iterdir(resolved_root):
                if subdir.is_dir():
                    pr = detect_docassemble_package(subdir)
                    if pr is not None:
                        docassemble_dir = pr / "docassemble"
                        if docassemble_dir.is_dir():
                            for pkg_subdir in safe_iterdir(docassemble_dir):
                                if pkg_subdir.is_dir() and (pkg_subdir / "__init__.py").is_file():
                                    if docassemble_package_name(pkg_subdir) == package_name:
                                        append(pkg_subdir)

    return candidates


def resolve_package_qualified_path(
    value: str,
    search_roots: list[Path],
) -> Path | None:
    """Resolve a Docassemble package-qualified path like ``docassemble.pkg:relative/path``.

    Returns the resolved filesystem path if the target exists within any of the
    provided search roots, or ``None`` if it cannot be found.
    """
    text = _strip_matching_quotes(value)
    colon_idx = text.find(":")
    if colon_idx == -1:
        return None
    package_name = text[:colon_idx]
    file_path = text[colon_idx + 1 :]
    if not package_name or not file_path:
        return None

    relative_path = _safe_package_relative_path(file_path)
    if relative_path is None:
        return None

    for package_dir in _candidate_package_dirs(package_name, search_roots):
        candidate = package_dir / relative_path
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_relative_to(package_dir):
            return resolved
    return None


def resolve_package_qualified_path_with_base(
    value: str,
    search_roots: list[Path],
    relative_base: str | None = None,
) -> Path | None:
    """Like :func:`resolve_package_qualified_path` but prepends *relative_base*
    to the file path when the path does not already start with ``data/``.

    This matches Docassemble's ``package_question_filename()`` behaviour,
    where a bare filename like ``assembly_line.yml`` is treated as
    ``data/questions/assembly_line.yml``.
    """
    text = _strip_matching_quotes(value)
    colon_idx = text.find(":")
    if colon_idx == -1:
        return None
    package_name = text[:colon_idx]
    file_path = text[colon_idx + 1 :]
    if not package_name or not file_path:
        return None

    if relative_base is not None and not file_path.startswith("data/"):
        file_path = f"{relative_base}/{file_path}"

    relative_path = _safe_package_relative_path(file_path)
    if relative_path is None:
        return None

    for package_dir in _candidate_package_dirs(package_name, search_roots):
        candidate = package_dir / relative_path
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_relative_to(package_dir):
            return resolved
    return None
