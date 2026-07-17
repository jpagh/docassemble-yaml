from __future__ import annotations

import logging
import os
import shlex

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore # Python < 3.11
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DayamlProjectConfig:
    project_root: Path
    yaml_path: Path | None
    conventions: frozenset[str]
    ignore_codes: frozenset[str]
    cli_args: tuple[str, ...]
    check_cli_args: tuple[str, ...]
    format_cli_args: tuple[str, ...]
    lsp_cli_args: tuple[str, ...]


def _normalize_ignore_codes(raw_codes: object) -> frozenset[str]:
    if isinstance(raw_codes, str):
        values = raw_codes.split(",")
    elif isinstance(raw_codes, (list, tuple)):
        values = []
        for item in raw_codes:
            if isinstance(item, str):
                values.extend(item.split(","))
    else:
        return frozenset()
    return frozenset(code.strip().upper() for code in values if code.strip())


def _normalize_cli_args(raw_args: object) -> tuple[str, ...]:
    if isinstance(raw_args, str):
        return tuple(shlex.split(raw_args))
    if isinstance(raw_args, (list, tuple)):
        return tuple(item for item in raw_args if isinstance(item, str))
    return ()


def _tool_mapping(pyproject: dict[str, object]) -> dict[str, object]:
    tool_section = pyproject.get("tool")
    return tool_section if isinstance(tool_section, dict) else {}


def _tool_config_section(tool_section: dict[str, object], *names: str) -> dict[str, object] | None:
    for name in names:
        section = tool_section.get(name)
        if isinstance(section, dict):
            return section
    return None


def load_dayaml_project_config(project_dir: Path) -> DayamlProjectConfig | None:
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.is_file():
        return None

    with pyproject_path.open("rb") as stream:
        pyproject = tomllib.load(stream)

    tool_section = _tool_mapping(pyproject)
    docassemble_lsp_section = _tool_config_section(tool_section, "docassemble-lsp", "docassemble_lsp")
    if docassemble_lsp_section is None:
        return None

    yaml_path: Path | None = None
    yaml_path_value = docassemble_lsp_section.get("yaml_path")
    if isinstance(yaml_path_value, str) and yaml_path_value.strip():
        yaml_path = Path(yaml_path_value)
    if yaml_path is not None and not yaml_path.is_absolute():
        yaml_path = project_dir / yaml_path

    ignore_codes_raw = docassemble_lsp_section.get("ignore-codes", docassemble_lsp_section.get("ignore_codes", ()))
    return DayamlProjectConfig(
        project_root=project_dir,
        yaml_path=yaml_path,
        conventions=_normalize_ignore_codes(docassemble_lsp_section.get("conventions", ())),
        ignore_codes=_normalize_ignore_codes(ignore_codes_raw),
        cli_args=_normalize_cli_args(docassemble_lsp_section.get("args", ())),
        check_cli_args=_normalize_cli_args(docassemble_lsp_section.get("check_args", ())),
        format_cli_args=_normalize_cli_args(docassemble_lsp_section.get("format_args", ())),
        lsp_cli_args=_normalize_cli_args(docassemble_lsp_section.get("lsp_args", ())),
    )


def find_nearest_pyproject_dir(path: Path) -> Path | None:
    candidate = path if path.is_dir() else path.parent
    for directory in (candidate, *candidate.parents):
        if (directory / "pyproject.toml").is_file():
            return directory
    return None


def detect_docassemble_package(path: Path) -> Path | None:
    """Detect a docassemble package root from a file path.

    Walks up from *path* looking for::

        <root>/pyproject.toml
        <root>/docassemble/<pkg>/__init__.py
        <root>/docassemble/<pkg>/data/

    Returns the root directory (containing pyproject.toml), or *None*.
    """
    candidate = path if path.is_dir() else path.parent
    cached = _detect_package_cache.get(candidate)
    if cached is not None:
        root, mtime = cached
        pyproject = root / "pyproject.toml"
        try:
            if pyproject.stat().st_mtime == mtime:
                return root
        except OSError:
            pass
    for directory in (candidate, *candidate.parents):
        pyproject = directory / "pyproject.toml"
        if not pyproject.is_file():
            continue
        docassemble_dir = directory / "docassemble"
        if not docassemble_dir.is_dir():
            continue
        for pkg_dir in safe_iterdir(docassemble_dir):
            if not pkg_dir.is_dir():
                continue
            if (pkg_dir / "__init__.py").is_file() and (pkg_dir / "data").is_dir():
                _detect_package_cache[candidate] = (
                    directory,
                    pyproject.stat().st_mtime,
                )
                return directory
    return None


def safe_iterdir(path: Path) -> list[Path]:
    try:
        return sorted(path.iterdir())
    except OSError as exc:
        logger.warning("Skipping unreadable directory %s: %s", path, exc)
        return []


def resolve_static_target(current_path: Path, value: str) -> Path | None:
    if not value or ":" in value:
        return None
    for parent in (current_path.parent, *current_path.parent.parents):
        candidate = parent / "static" / value
        try:
            if candidate.exists():
                return candidate.resolve()
            if (parent / "questions").is_dir():
                return None
        except OSError as exc:
            logger.debug("Static target check failed for %s: %s", candidate, exc)
            return None
    return None


_discover_package_roots_cache: dict[frozenset[Path], tuple[list[Path], dict[Path, float]]] = {}
_detect_package_cache: dict[Path, tuple[Path, float]] = {}
_templates_dir_cache: dict[Path, tuple[Path, float]] = {}
_TEMPLATE_NAMES_CACHE: dict[Path, tuple[frozenset[str], float]] = {}


def _all_mtimes_match(mtimes: dict[Path, float]) -> bool:
    for path, cached_mtime in mtimes.items():
        try:
            if path.stat().st_mtime != cached_mtime:
                return False
        except OSError:
            return False
    return True


def _discover_package_roots(search_roots: Iterable[Path]) -> list[Path]:
    """Find all unique docassemble package roots reachable from *search_roots*.

    For each root, first checks whether the root itself is a package root
    (by walking up via :func:`detect_docassemble_package`).  If not, scans
    immediate subdirectories for packages.  Only directories one level below
    each search root are checked — packages nested deeper (e.g. inside a
    subdirectory of a subdirectory) are not discovered.
    """
    key = frozenset(root.resolve() for root in search_roots)
    cached = _discover_package_roots_cache.get(key)
    if cached is not None:
        cached_results, cached_mtimes = cached
        if _all_mtimes_match(cached_mtimes):
            return cached_results

    results: list[Path] = []
    seen: set[Path] = set()
    for root in search_roots:
        resolved = root.resolve()
        pr = detect_docassemble_package(resolved)
        if pr is not None and pr not in seen:
            seen.add(pr)
            results.append(pr)
        elif resolved.is_dir():
            for subdir in safe_iterdir(resolved):
                if subdir.is_dir() and not is_default_ignored_dir(subdir.name):
                    pr = detect_docassemble_package(subdir)
                    if pr is not None and pr not in seen:
                        seen.add(pr)
                        results.append(pr)
    mtimes = {}
    for root in search_roots:
        resolved = root.resolve()
        try:
            mtimes[resolved] = resolved.stat().st_mtime
        except OSError:
            pass
    _discover_package_roots_cache[key] = (results, mtimes)
    if results:
        logger.debug("_discover_package_roots(%s) -> %s", list(search_roots), results)
    return results


def clear_detect_package_cache(paths: Iterable[Path] | None = None) -> None:
    """Clear the ``detect_docassemble_package``, ``templates_dir_for_path``,
    and template name caches.

    When *paths* is ``None`` (default), all caches are cleared entirely.
    When *paths* is provided, only the specified paths are evicted.
    """
    if paths is None:
        _detect_package_cache.clear()
        _templates_dir_cache.clear()
        _TEMPLATE_NAMES_CACHE.clear()
    else:
        for path in paths:
            _detect_package_cache.pop(path, None)
            _detect_package_cache.pop(path.parent, None)
            _templates_dir_cache.pop(path, None)
            _TEMPLATE_NAMES_CACHE.pop(path, None)


def templates_dir_for_path(path: Path) -> Path | None:
    """Find the ``data/templates`` directory for the docassemble package
    that contains *path*.

    Returns *None* if *path* is not inside a recognised package or the
    package has no templates directory.
    """
    cached = _templates_dir_cache.get(path)
    if cached is not None:
        result, mtime = cached
        try:
            if result.stat().st_mtime == mtime:
                return result
        except OSError:
            pass
    import time

    t0 = time.perf_counter()
    pr = detect_docassemble_package(path)
    if pr is None:
        logger.debug("templates_dir_for_path(%s) -> None (no package root)", path)
        return None
    docassemble_dir = pr / "docassemble"
    if not docassemble_dir.is_dir():
        logger.debug("templates_dir_for_path(%s) -> None (no docassemble dir under root)", path)
        return None
    for pkg_dir in safe_iterdir(docassemble_dir):
        if pkg_dir.is_dir() and (pkg_dir / "__init__.py").is_file():
            tdir = pkg_dir / "data" / "templates"
            if tdir.is_dir():
                elapsed = (time.perf_counter() - t0) * 1000
                result = tdir.resolve()
                _templates_dir_cache[path] = (result, result.stat().st_mtime)
                logger.debug(
                    "templates_dir_for_path(%s) -> %s (%.1fms)",
                    path,
                    result,
                    elapsed,
                )
                return result
    logger.debug("templates_dir_for_path(%s) -> None (no templates dir)", path)
    return None


def discover_templates_dir(package_root: Path) -> Path | None:
    """Find the ``data/templates`` directory under a known package root.

    This is the eager equivalent of ``templates_dir_for_path`` for callers
    that already know the package root (no file-to-root walk needed).
    Returns the first ``<package_root>/docassemble/<pkg>/data/templates/``
    directory found, or *None*.
    """
    docassemble_dir = package_root / "docassemble"
    if not docassemble_dir.is_dir():
        return None
    for pkg_dir in safe_iterdir(docassemble_dir):
        if pkg_dir.is_dir() and (pkg_dir / "__init__.py").is_file():
            tdir = pkg_dir / "data" / "templates"
            if tdir.is_dir():
                return tdir.resolve()
    return None


def collect_template_file_names(templates_dir: Path) -> frozenset[str]:
    """Return the set of regular file names in *templates_dir* (flat, non-recursive)."""
    return frozenset(f.name for f in safe_iterdir(templates_dir) if f.is_file())


def resolve_template_names(templates_dir: Path | None) -> frozenset[str]:
    """Return validated template file names, checking dir mtime cache.

    On cache miss (first call or file add/remove since last check), re-scans
    *templates_dir* and caches the result keyed by the directory mtime.
    On cache hit, returns the cached set with no filesystem access.

    Returns an empty frozenset when *templates_dir* is ``None``.
    """
    if templates_dir is None:
        return frozenset()

    cached = _TEMPLATE_NAMES_CACHE.get(templates_dir)
    if cached is not None:
        names, mtime = cached
        try:
            if templates_dir.stat().st_mtime == mtime:
                return names
        except OSError:
            pass

    names = collect_template_file_names(templates_dir)
    try:
        _TEMPLATE_NAMES_CACHE[templates_dir] = (names, templates_dir.stat().st_mtime)
    except OSError:
        pass
    return names


def _collect_yaml_from_package_data(package_root: Path, *, include_default_ignores: bool) -> list[Path]:
    """Collect all YAML files from ``docassemble/<pkg>/data/`` under *package_root*."""
    yaml_files: list[Path] = []
    docassemble_dir = package_root / "docassemble"
    if docassemble_dir.is_dir():
        for pkg_dir in safe_iterdir(docassemble_dir):
            if pkg_dir.is_dir() and (pkg_dir / "__init__.py").is_file():
                data_dir = pkg_dir / "data"
                if data_dir.is_dir():
                    for root, dirnames, filenames in os.walk(data_dir, topdown=True):
                        root_path = Path(root)
                        if include_default_ignores:
                            if is_default_ignored_dir(root_path.name):
                                dirnames[:] = []
                                continue
                            dirnames[:] = [d for d in dirnames if not is_default_ignored_dir(d)]
                        for filename in filenames:
                            if filename.lower().endswith((".yml", ".yaml")):
                                yaml_files.append(root_path / filename)
    return yaml_files


def collect_dayaml_ignore_codes(paths: Iterable[Path]) -> frozenset[str]:
    ignore_codes: set[str] = set()
    seen_projects: set[Path] = set()

    for path in paths:
        project_dir = find_nearest_pyproject_dir(path.resolve())
        if project_dir is None:
            continue
        project_dir = project_dir.resolve()
        if project_dir in seen_projects:
            continue
        seen_projects.add(project_dir)
        project_config = load_dayaml_project_config(project_dir)
        if project_config is not None:
            ignore_codes.update(project_config.ignore_codes)

    return frozenset(ignore_codes)


def collect_dayaml_conventions(paths: Iterable[Path]) -> frozenset[str]:
    conventions: set[str] = set()
    seen_projects: set[Path] = set()

    for path in paths:
        project_dir = find_nearest_pyproject_dir(path.resolve())
        if project_dir is None:
            continue
        project_dir = project_dir.resolve()
        if project_dir in seen_projects:
            continue
        seen_projects.add(project_dir)
        project_config = load_dayaml_project_config(project_dir)
        if project_config is not None:
            conventions.update(project_config.conventions)

    return frozenset(conventions)


def collect_dayaml_cli_args(paths: Iterable[Path], *, command_name: str = "check") -> tuple[str, ...]:
    cli_args: list[str] = []
    seen_projects: set[Path] = set()

    for path in paths:
        project_dir = find_nearest_pyproject_dir(path.resolve())
        if project_dir is None:
            continue
        project_dir = project_dir.resolve()
        if project_dir in seen_projects:
            continue
        seen_projects.add(project_dir)
        project_config = load_dayaml_project_config(project_dir)
        if project_config is not None:
            cli_args.extend(project_config.cli_args)
            if command_name == "check":
                cli_args.extend(project_config.check_cli_args)
            elif command_name == "format":
                cli_args.extend(project_config.format_cli_args)
            elif command_name == "lsp":
                cli_args.extend(project_config.lsp_cli_args)

    return tuple(cli_args)


def resolve_collection_path(path: Path) -> Path:
    if not path.is_dir():
        return path

    project_config = load_dayaml_project_config(path.resolve())
    if project_config is None or project_config.yaml_path is None:
        return path
    return project_config.yaml_path


def is_default_ignored_dir(dirname: str) -> bool:
    return (
        dirname.startswith(".git")
        or dirname.startswith(".github")
        or dirname.startswith(".venv")
        or dirname == "build"
        or dirname == "dist"
        or dirname == "node_modules"
        or dirname == "sources"
    )


def _collect_yaml_files(
    paths: list[Path],
    *,
    check_all: bool = False,
    include_default_ignores: bool | None = None,
) -> list[Path]:
    if include_default_ignores is None:
        include_default_ignores = not check_all

    yaml_files: list[Path] = []
    for path in paths:
        path = resolve_collection_path(path)
        if path.is_dir():
            package_roots = _discover_package_roots([path])
            if package_roots:
                for pr in package_roots:
                    yaml_files.extend(
                        _collect_yaml_from_package_data(pr, include_default_ignores=include_default_ignores)
                    )
            else:
                for root, dirnames, filenames in os.walk(path, topdown=True):
                    root_path = Path(root)
                    if include_default_ignores:
                        if is_default_ignored_dir(root_path.name):
                            dirnames[:] = []
                            continue
                        dirnames[:] = [dirname for dirname in dirnames if not is_default_ignored_dir(dirname)]
                    for filename in filenames:
                        if filename.lower().endswith((".yml", ".yaml")):
                            yaml_files.append(root_path / filename)
        elif path.suffix.lower() in (".yml", ".yaml"):
            yaml_files.append(path)

    seen: set[Path] = set()
    result: list[Path] = []
    for yaml_file in yaml_files:
        resolved = yaml_file.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(yaml_file)
    return sorted(result)


def collect_yaml_files(
    paths: Iterable[str | Path],
    *,
    check_all: bool = False,
    include_default_ignores: bool | None = None,
) -> list[Path]:
    normalized = [path if isinstance(path, Path) else Path(path) for path in paths]
    return _collect_yaml_files(
        normalized or [Path(".")],
        check_all=check_all,
        include_default_ignores=include_default_ignores,
    )
