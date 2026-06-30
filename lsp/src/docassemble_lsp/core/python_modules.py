from __future__ import annotations

import ast
import importlib.util
import logging
from collections.abc import Iterable
from pathlib import Path

from docassemble_lsp.core.definition_models import (
    DefinitionTarget,
    PythonModuleIndex,
    PythonModuleResolution,
    PythonModuleSymbol,
)
from docassemble_lsp.core.files import _discover_package_roots, find_nearest_pyproject_dir
from docassemble_lsp.core.line_helpers import _safe_ast_parse
from docassemble_lsp.core.python_paths import (
    docassemble_package_dir,
    normalize_module_name,
)
from docassemble_lsp.core.workspace import WorkspaceIndex

logger = logging.getLogger(__name__)

_VENDORED_PYTHON_MODULES = {
    "docassemble.base.util": Path(__file__).resolve().parent.parent / "data" / "vendored_docassemble_base_util.pyi",
    "docassemble.base.functions": Path(__file__).resolve().parent.parent
    / "data"
    / "vendored_docassemble_base_functions.pyi",
    "docassemble.base.error": Path(__file__).resolve().parent.parent / "data" / "vendored_docassemble_base_error.pyi",
}

VENDORED_MODULE_NAMES: tuple[str, ...] = tuple(_VENDORED_PYTHON_MODULES.keys())

_python_module_index_cache: dict[Path, tuple[PythonModuleIndex, float]] = {}

PYTHON_BUILTIN_EXCEPTIONS = frozenset(
    {
        "BaseException",
        "Exception",
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "BufferError",
        "EOFError",
        "ImportError",
        "LookupError",
        "MemoryError",
        "NameError",
        "OSError",
        "ReferenceError",
        "RuntimeError",
        "StopIteration",
        "StopAsyncIteration",
        "SyntaxError",
        "SystemError",
        "TypeError",
        "ValueError",
        "Warning",
        "BytesWarning",
        "DeprecationWarning",
        "EncodingWarning",
        "FutureWarning",
        "ImportWarning",
        "PendingDeprecationWarning",
        "ResourceWarning",
        "RuntimeWarning",
        "SyntaxWarning",
        "UnicodeWarning",
        "UserWarning",
        "FloatingPointError",
        "GeneratorExit",
        "IndentationError",
        "IndexError",
        "KeyError",
        "KeyboardInterrupt",
        "ModuleNotFoundError",
        "NotImplementedError",
        "OverflowError",
        "RecursionError",
        "SystemExit",
        "TabError",
        "TimeoutError",
        "UnboundLocalError",
        "UnicodeDecodeError",
        "UnicodeEncodeError",
        "UnicodeError",
        "UnicodeTranslateError",
        "ZeroDivisionError",
        "BlockingIOError",
        "ChildProcessError",
        "ConnectionError",
        "BrokenPipeError",
        "ConnectionAbortedError",
        "ConnectionRefusedError",
        "ConnectionResetError",
        "FileExistsError",
        "FileNotFoundError",
        "InterruptedError",
        "IsADirectoryError",
        "NotADirectoryError",
        "PermissionError",
        "ProcessLookupError",
    }
)


def _yaml_search_paths(current_path: Path | None, workspace_index: WorkspaceIndex) -> list[Path]:
    if workspace_index.search_roots:
        return list(workspace_index.search_roots)
    if current_path is None:
        return []

    project_root = find_nearest_pyproject_dir(current_path.resolve())
    return [project_root or current_path.parent]


def python_search_paths(current_path: Path | None, workspace_index: WorkspaceIndex) -> list[Path]:
    if workspace_index.search_roots:
        paths: list[Path] = []
        seen: set[Path] = set()

        def _add(p: Path) -> None:
            if p not in seen:
                seen.add(p)
                paths.append(p)

        for root in workspace_index.search_roots:
            resolved = root.resolve()
            pkg_dir = docassemble_package_dir(resolved)
            if pkg_dir is not None:
                _add(pkg_dir.parent.parent)
            else:
                _add(resolved)

        for pr in _discover_package_roots(workspace_index.search_roots):
            _add(pr)

        logger.debug("python_search_paths -> %s", paths)
        return paths
    if current_path is None:
        return []

    package_dir = docassemble_package_dir(current_path)
    if package_dir is not None:
        return [package_dir.parent.parent]
    return _yaml_search_paths(current_path, workspace_index)


def resolve_python_module_source(
    module_name: str,
    *,
    current_path: Path | None = None,
    workspace_index: WorkspaceIndex,
) -> PythonModuleResolution:
    normalized = normalize_module_name(module_name, current_path)
    if normalized is None:
        return PythonModuleResolution(module_name=module_name, path=None, source_kind="unresolved")
    vendored_path = _VENDORED_PYTHON_MODULES.get(normalized)

    for root in python_search_paths(current_path, workspace_index):
        base = root.joinpath(*normalized.split("."))
        python_file = base.with_suffix(".py")
        if python_file.is_file():
            return PythonModuleResolution(
                module_name=normalized,
                path=python_file.resolve(),
                source_kind="workspace",
            )
        init_file = base / "__init__.py"
        if init_file.is_file():
            return PythonModuleResolution(
                module_name=normalized,
                path=init_file.resolve(),
                source_kind="workspace",
            )

    try:
        spec = importlib.util.find_spec(normalized)
    except ImportError:
        spec = None
    if spec is None or spec.origin in {None, "built-in", "frozen"}:
        if vendored_path is not None and vendored_path.is_file():
            return PythonModuleResolution(
                module_name=normalized,
                path=vendored_path.resolve(),
                source_kind="vendored",
            )
        return PythonModuleResolution(module_name=normalized, path=None, source_kind="unresolved")

    origin_str = spec.origin
    if origin_str is None:
        return PythonModuleResolution(module_name=normalized, path=None, source_kind="unresolved")
    origin = Path(origin_str)
    if not origin.exists() or origin.suffix != ".py":
        if vendored_path is not None and vendored_path.is_file():
            return PythonModuleResolution(
                module_name=normalized,
                path=vendored_path.resolve(),
                source_kind="vendored",
            )
        return PythonModuleResolution(module_name=normalized, path=None, source_kind="unresolved")
    return PythonModuleResolution(
        module_name=normalized,
        path=origin.resolve(),
        source_kind="environment",
    )


def resolve_python_module_path(
    module_name: str,
    current_path: Path | None,
    workspace_index: WorkspaceIndex,
) -> Path | None:
    return resolve_python_module_source(
        module_name,
        current_path=current_path,
        workspace_index=workspace_index,
    ).path


def _document_lines(source: str) -> list[str]:
    return source.splitlines() or [""]


def _is_custom_datatype(base: ast.expr) -> bool:
    if isinstance(base, ast.Name) and base.id == "CustomDataType":
        return True
    if isinstance(base, ast.Attribute) and base.attr == "CustomDataType":
        return True
    return False


def _python_definition_target(
    module_path: Path,
    lines: list[str],
    node: ast.AST,
) -> DefinitionTarget | None:
    lineno = getattr(node, "lineno", None)
    col_offset = getattr(node, "col_offset", None)
    if lineno is None or col_offset is None:
        return None
    return DefinitionTarget(
        path=module_path,
        line=lineno - 1,
        start_character=col_offset,
        end_character=len(lines[lineno - 1]),
    )


def _python_all_exports(tree: ast.Module) -> tuple[str, ...] | None:
    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
                value = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                value = node.value

        if value is None:
            continue

        try:
            exported = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return None
        if not isinstance(exported, (list, tuple, set)):
            return None
        names = tuple(item for item in exported if isinstance(item, str))
        if len(names) != len(exported):
            return None
        return names
    return None


def _iter_top_level_assigned_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Assign):
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        return tuple(name for name in names if name != "__all__")
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id != "__all__":
        return (node.target.id,)
    return ()


def _python_imported_module_symbol(
    module_name: str,
    *,
    imported_name: str | None,
    current_path: Path,
    workspace_index: WorkspaceIndex | None = None,
) -> PythonModuleSymbol:
    wi = workspace_index if workspace_index is not None else WorkspaceIndex.empty()
    return PythonModuleSymbol(
        kind="module" if imported_name is None else "symbol",
        target=None,
        methods={},
        imported_module_path=resolve_python_module_path(module_name, current_path, wi),
        imported_name=imported_name,
    )


def _python_module_public_names(index: PythonModuleIndex) -> tuple[str, ...]:
    if index.exported_names is not None:
        return index.exported_names
    return tuple(name for name in index.symbols if not name.startswith("_"))


def python_module_symbol_detail(
    module_path: Path | None,
    name: str,
    *,
    _seen: set[tuple[Path, str]] | None = None,
) -> str:
    if module_path is None:
        return "symbol"

    symbol = load_python_module_index(module_path).symbols.get(name)
    if symbol is None:
        return "symbol"
    if symbol.kind != "symbol":
        return symbol.kind
    if symbol.imported_module_path is None or symbol.imported_name is None:
        return "symbol"

    seen = set() if _seen is None else _seen
    key = (symbol.imported_module_path.resolve(), symbol.imported_name)
    if key in seen:
        return "symbol"
    seen.add(key)
    return python_module_symbol_detail(symbol.imported_module_path, symbol.imported_name, _seen=seen)


def load_python_module_index(
    module_path: Path,
    *,
    workspace_index: WorkspaceIndex | None = None,
) -> PythonModuleIndex:
    cached = _python_module_index_cache.get(module_path)
    if cached is not None:
        index, mtime = cached
        try:
            if module_path.stat().st_mtime == mtime:
                return index
        except OSError:
            pass

    try:
        source = module_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        result = PythonModuleIndex(symbols={})
        _python_module_index_cache[module_path] = (result, module_path.stat().st_mtime)
        return result

    try:
        tree = _safe_ast_parse(source)
    except SyntaxError:
        result = PythonModuleIndex(symbols={})
        _python_module_index_cache[module_path] = (result, module_path.stat().st_mtime)
        return result

    lines = _document_lines(source)
    symbols: dict[str, PythonModuleSymbol] = {}
    custom_datatypes: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            target = _python_definition_target(module_path, lines, node)
            if target is not None:
                symbols[node.name] = PythonModuleSymbol(
                    kind="function", target=target, methods={}, docstring=ast.get_docstring(node)
                )
            continue

        if isinstance(node, ast.ClassDef):
            methods: dict[str, DefinitionTarget] = {}
            for child in node.body:
                if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                target = _python_definition_target(module_path, lines, child)
                if target is not None:
                    methods[child.name] = target

            target = _python_definition_target(module_path, lines, node)
            if target is not None:
                base_names = tuple(base.id for base in node.bases if isinstance(base, ast.Name))
                symbols[node.name] = PythonModuleSymbol(
                    kind="class",
                    target=target,
                    methods=methods,
                    docstring=ast.get_docstring(node),
                    bases=base_names,
                )

            # Check for CustomDataType subclasses and extract name attribute.
            if any(_is_custom_datatype(base) for base in node.bases):
                for item in node.body:
                    if isinstance(item, ast.Assign) and item.targets:
                        target_name = item.targets[0]
                        if isinstance(target_name, ast.Name) and target_name.id == "name":
                            if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                                custom_datatypes.add(item.value.value)
                            break
            continue

        assigned_names = _iter_top_level_assigned_names(node)
        if assigned_names:
            target = _python_definition_target(module_path, lines, node)
            for name in assigned_names:
                symbols[name] = PythonModuleSymbol(kind="symbol", target=target, methods={})
            continue

        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = normalize_module_name(alias.name, module_path)
                if module_name is None:
                    continue
                alias_name = alias.asname or alias.name.split(".", 1)[0]
                symbols[alias_name] = _python_imported_module_symbol(
                    module_name,
                    imported_name=None,
                    current_path=module_path,
                    workspace_index=workspace_index,
                )
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        base_module = "." * node.level + (node.module or "")
        module_name = normalize_module_name(base_module, module_path)
        if module_name is None:
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            symbols[alias.asname or alias.name] = _python_imported_module_symbol(
                module_name,
                imported_name=alias.name,
                current_path=module_path,
                workspace_index=workspace_index,
            )

    # Second pass: detect exception classes by checking inheritance chains.
    # Collect base class names for each class definition.
    class_bases: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            base_ids = [base.id for base in node.bases if isinstance(base, ast.Name)]
            class_bases[node.name] = base_ids

    # Iteratively resolve which classes inherit from BaseException or a known
    # exception superclass (directly or transitively).  A class whose name ends
    # with ``Error``, ``Exception``, or ``Warning`` is also treated as an
    # exception, even if the declared base chain is opaque (e.g. re-exported
    # under a different name).
    exception_names: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name, bases in class_bases.items():
            if name in exception_names:
                continue
            if any(
                base in PYTHON_BUILTIN_EXCEPTIONS
                or base in exception_names
                or base.endswith(("Error", "Exception", "Warning"))
                for base in bases
            ):
                exception_names.add(name)
                changed = True

    for name in exception_names:
        if name in symbols and symbols[name].kind == "class":
            old = symbols[name]
            symbols[name] = PythonModuleSymbol(
                kind="exception",
                target=old.target,
                methods=old.methods,
                docstring=old.docstring,
                bases=old.bases,
            )

    exported_names = _python_all_exports(tree)
    if exported_names is not None:
        for name in exported_names:
            symbols.setdefault(name, PythonModuleSymbol(kind="symbol", target=None, methods={}))

    result = PythonModuleIndex(
        symbols=symbols,
        exported_names=exported_names,
        custom_datatype_names=frozenset(custom_datatypes),
    )
    _python_module_index_cache[module_path] = (result, module_path.stat().st_mtime)
    return result


def collect_class_names(index: PythonModuleIndex) -> frozenset[str]:
    """Return all class and exception names from a Python module index."""
    return frozenset(name for name, symbol in index.symbols.items() if symbol.kind in ("class", "exception"))


def collect_non_exception_class_names(index: PythonModuleIndex) -> frozenset[str]:
    """Return class names excluding exception/error/warning names from a Python module index."""
    return frozenset(name for name, symbol in index.symbols.items() if symbol.kind == "class")


def compute_da_object_subclasses(
    module_paths: list[Path], *, workspace_index: WorkspaceIndex | None = None
) -> frozenset[str]:
    """Compute transitively all class names that inherit from DAObject."""
    base_to_subclasses: dict[str, set[str]] = {}
    for mod_path in module_paths:
        index = load_python_module_index(mod_path, workspace_index=workspace_index)
        for name, sym in index.symbols.items():
            if sym.bases:
                for base in sym.bases:
                    base_to_subclasses.setdefault(base, set()).add(name)
    subclasses: set[str] = set()
    worklist = ["DAObject"]
    while worklist:
        current = worklist.pop()
        if current in subclasses:
            continue
        subclasses.add(current)
        for child in base_to_subclasses.get(current, set()):
            if child not in subclasses:
                worklist.append(child)
    return frozenset(subclasses | {"DAEmpty"})


def python_module_symbol_details(module_path: Path | None) -> dict[str, str]:
    if module_path is None:
        return {}

    index = load_python_module_index(module_path)
    details: dict[str, str] = {}
    for name in _python_module_public_names(index):
        details[name] = python_module_symbol_detail(module_path, name)
    return details


def module_completion_members(module_path: Path | None, chain: tuple[str, ...]) -> dict[str, str]:
    if module_path is None:
        return {}

    index = load_python_module_index(module_path)
    if not chain:
        return python_module_symbol_details(module_path)

    symbol = index.symbols.get(chain[0])
    if symbol is None:
        return {}

    if symbol.imported_module_path is not None:
        delegated_chain = ((symbol.imported_name,) if symbol.imported_name is not None else ()) + chain[1:]
        return module_completion_members(symbol.imported_module_path, delegated_chain)

    if len(chain) == 1:
        return {name: "method" for name in symbol.methods}
    return {}


def clear_module_index_cache(paths: Iterable[Path] | None = None) -> None:
    """Clear the ``load_python_module_index`` cache.

    When *paths* is ``None`` (default), the entire cache is cleared.
    When *paths* is provided, only the specified module paths are
    evicted — other cached modules are preserved.
    """
    if paths is None:
        _python_module_index_cache.clear()
    else:
        for path in paths:
            _python_module_index_cache.pop(path, None)


def resolve_python_symbol_chain(
    module_path: Path | None,
    chain: tuple[str, ...],
    *,
    workspace_index: WorkspaceIndex | None = None,
) -> list[DefinitionTarget]:
    if module_path is None:
        return []
    if not chain:
        return [DefinitionTarget(path=module_path, line=0, start_character=0, end_character=0)]

    index = load_python_module_index(module_path, workspace_index=workspace_index)
    symbol = index.symbols.get(chain[0])
    if symbol is None:
        return []

    if symbol.imported_module_path is not None:
        delegated_chain = ((symbol.imported_name,) if symbol.imported_name is not None else ()) + chain[1:]
        return resolve_python_symbol_chain(
            symbol.imported_module_path, delegated_chain, workspace_index=workspace_index
        )

    if len(chain) == 1:
        return [symbol.target] if symbol.target is not None else []
    method_target = symbol.methods.get(chain[1])
    if method_target is None:
        return []
    return [method_target]
