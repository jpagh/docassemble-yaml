from __future__ import annotations

import os
import time
from pathlib import Path

from docassemble_lsp.core.python_modules import (
    clear_module_index_cache,
    compute_da_object_subclasses,
    load_python_module_index,
    resolve_python_symbol_chain,
)
from docassemble_lsp.core.workspace import WorkspaceIndex


def _write_py_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_module_index_cache_hits(tmp_path: Path) -> None:
    """load_python_module_index returns cached result on repeated calls."""
    mod_path = tmp_path / "mymodule.py"
    _write_py_file(mod_path, "FOO = 1\n")

    # First call — parses and caches.
    index1 = load_python_module_index(mod_path)
    assert "FOO" in index1.symbols

    # Second call — should hit cache (same object).
    index2 = load_python_module_index(mod_path)
    assert "FOO" in index2.symbols
    assert index2 is index1


def test_module_index_reparsed_on_mtime_change(tmp_path: Path) -> None:
    """load_python_module_index re-parses when file mtime changes."""
    mod_path = tmp_path / "mymodule.py"
    _write_py_file(mod_path, "VERSION = 1\n")

    # First call — caches the index.
    index1 = load_python_module_index(mod_path)
    assert index1.symbols["VERSION"] is not None

    # Modify the file and advance mtime.
    _write_py_file(mod_path, "VERSION = 2\n")
    future = time.time() + 60
    os.utime(mod_path, (future, future))

    # Second call — mtime mismatch, should re-parse.
    index2 = load_python_module_index(mod_path)
    assert index2 is not index1


def test_module_index_clear_single_path(tmp_path: Path) -> None:
    """clear_module_index_cache removes only the specified path."""
    mod_a = tmp_path / "module_a.py"
    mod_b = tmp_path / "module_b.py"
    _write_py_file(mod_a, "A = 1\n")
    _write_py_file(mod_b, "B = 2\n")

    # Load both modules (both cached).
    index_a = load_python_module_index(mod_a)
    index_b = load_python_module_index(mod_b)
    assert "A" in index_a.symbols
    assert "B" in index_b.symbols

    # Clear only module_a.
    clear_module_index_cache([mod_a])

    # module_a should be re-parsed (cache miss).
    index_a_reloaded = load_python_module_index(mod_a)
    assert "A" in index_a_reloaded.symbols
    assert index_a_reloaded is not index_a

    # module_b should still be cached.
    index_b_again = load_python_module_index(mod_b)
    assert index_b_again is index_b


def test_imported_module_uses_workspace_index(tmp_path: Path) -> None:
    pkg = tmp_path / "docassemble" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "utils.py").write_text("FOO = 1\n")
    (pkg / "helpers.py").write_text("from . import utils\n")
    idx = WorkspaceIndex.empty_for_roots((tmp_path.resolve(),))
    helpers_index = load_python_module_index(pkg / "helpers.py", workspace_index=idx)
    assert "utils" in helpers_index.symbols
    sym = helpers_index.symbols["utils"]
    assert sym.imported_name == "utils"
    assert sym.imported_module_path is not None
    assert sym.imported_module_path.resolve() == (pkg / "__init__.py").resolve()


def test_resolve_python_symbol_chain_cross_module(tmp_path: Path) -> None:
    pkg = tmp_path / "docassemble" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "utils.py").write_text("FOO = 1\n")
    (pkg / "helpers.py").write_text("from .utils import FOO\n")
    idx = WorkspaceIndex.empty_for_roots((tmp_path.resolve(),))
    result = resolve_python_symbol_chain(pkg / "helpers.py", ("FOO",), workspace_index=idx)
    assert len(result) == 1
    assert result[0].path == (pkg / "utils.py").resolve()


def test_compute_da_object_subclasses_with_workspace(tmp_path: Path) -> None:
    pkg = tmp_path / "docassemble" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "mymodel.py").write_text("class MyThing(DAObject):\n    pass\n")
    idx = WorkspaceIndex.empty_for_roots((tmp_path.resolve(),))
    result = compute_da_object_subclasses(
        [pkg / "mymodel.py"],
        workspace_index=idx,
    )
    assert "MyThing" in result
