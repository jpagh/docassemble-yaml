from __future__ import annotations

import os
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from docassemble_lsp.core.python_modules import (
    clear_module_index_cache,
    compute_da_object_subclasses,
    load_python_module_index,
    module_completion_members,
    python_module_symbol_detail,
    resolve_python_symbol_chain,
)
from docassemble_lsp.core.workspace import WorkspaceIndex


@pytest.fixture(autouse=True)
def _clear_cache() -> Generator[None, None, None]:
    clear_module_index_cache(None)
    yield
    clear_module_index_cache(None)


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
    result = resolve_python_symbol_chain(
        pkg / "helpers.py", ("FOO",), workspace_index=idx
    )
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


def test_load_python_module_index_empty_file(tmp_path: Path) -> None:
    mod_path = tmp_path / "empty.py"
    _write_py_file(mod_path, "")
    index = load_python_module_index(mod_path)
    assert index.symbols == {}
    assert index.exported_names is None


def test_load_python_module_index_syntax_error(tmp_path: Path) -> None:
    mod_path = tmp_path / "broken.py"
    _write_py_file(mod_path, "def broken(:\n")
    index = load_python_module_index(mod_path)
    assert index.symbols == {}


def test_load_python_module_index_non_utf8(tmp_path: Path) -> None:
    mod_path = tmp_path / "nonutf8.py"
    mod_path.write_bytes(b"\xff\xfe\x00\x00")
    index = load_python_module_index(mod_path)
    assert index.symbols == {}


def test_load_python_module_index_all_export_valid(tmp_path: Path) -> None:
    mod_path = tmp_path / "with_all.py"
    _write_py_file(mod_path, '__all__ = ("FOO",)\nFOO = 1\n')
    index = load_python_module_index(mod_path)
    assert index.exported_names == ("FOO",)
    assert "FOO" in index.symbols


def test_load_python_module_index_all_export_missing(tmp_path: Path) -> None:
    mod_path = tmp_path / "all_missing.py"
    _write_py_file(mod_path, '__all__ = ("MISSING",)\n')
    index = load_python_module_index(mod_path)
    assert index.exported_names == ("MISSING",)
    assert "MISSING" in index.symbols


def test_load_python_module_index_all_export_non_strings(tmp_path: Path) -> None:
    mod_path = tmp_path / "all_numbers.py"
    _write_py_file(mod_path, "__all__ = [1, 2]\n")
    index = load_python_module_index(mod_path)
    assert index.exported_names is None


def test_load_python_module_index_class_inheritance_chains(tmp_path: Path) -> None:
    mod_path = tmp_path / "classes.py"
    _write_py_file(mod_path, "class A: pass\nclass B(A): pass\nclass C(B): pass\n")
    index = load_python_module_index(mod_path)
    assert index.symbols["A"].bases == ()
    assert index.symbols["B"].bases == ("A",)
    assert index.symbols["C"].bases == ("B",)


def test_load_python_module_index_daobject_subclass(tmp_path: Path) -> None:
    mod_path = tmp_path / "mything.py"
    _write_py_file(mod_path, "class MyThing(DAObject): pass\n")
    index = load_python_module_index(mod_path)
    assert index.symbols["MyThing"].bases == ("DAObject",)


def test_compute_da_object_subclasses_multi_level(tmp_path: Path) -> None:
    pkg = tmp_path / "docassemble" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "mymodel.py").write_text(
        "class A(DAObject): pass\nclass B(A): pass\nclass C(B): pass\n"
    )
    idx = WorkspaceIndex.empty_for_roots((tmp_path.resolve(),))
    result = compute_da_object_subclasses([pkg / "mymodel.py"], workspace_index=idx)
    assert result == {"DAObject", "A", "B", "C", "DAEmpty"}


def test_compute_da_object_subclasses_diamond(tmp_path: Path) -> None:
    pkg = tmp_path / "docassemble" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "mymodel.py").write_text(
        "class A(DAObject): pass\nclass B(DAObject): pass\nclass C(A, B): pass\n"
    )
    idx = WorkspaceIndex.empty_for_roots((tmp_path.resolve(),))
    result = compute_da_object_subclasses([pkg / "mymodel.py"], workspace_index=idx)
    assert result == {"DAObject", "A", "B", "C", "DAEmpty"}


def test_clear_module_index_cache_bulk(tmp_path: Path) -> None:
    mod_a = tmp_path / "module_a.py"
    mod_b = tmp_path / "module_b.py"
    _write_py_file(mod_a, "A = 1\n")
    _write_py_file(mod_b, "B = 2\n")
    index_a = load_python_module_index(mod_a)
    index_b = load_python_module_index(mod_b)
    clear_module_index_cache(None)
    index_a_reloaded = load_python_module_index(mod_a)
    index_b_reloaded = load_python_module_index(mod_b)
    assert index_a_reloaded is not index_a
    assert index_b_reloaded is not index_b


def test_clear_module_index_cache_repeated(tmp_path: Path) -> None:
    mod_path = tmp_path / "module.py"
    _write_py_file(mod_path, "X = 1\n")
    load_python_module_index(mod_path)
    clear_module_index_cache([mod_path])
    clear_module_index_cache([mod_path])
    index_reloaded = load_python_module_index(mod_path)
    assert "X" in index_reloaded.symbols


def test_python_module_symbol_detail_function_docstring(tmp_path: Path) -> None:
    mod_path = tmp_path / "mymod.py"
    _write_py_file(mod_path, 'def foo():\n    """My doc."""\n')
    assert python_module_symbol_detail(mod_path, "foo") == "function"


def test_python_module_symbol_detail_reexport(tmp_path: Path) -> None:
    pkg = tmp_path / "docassemble" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "other.py").write_text("FOO = 1\n")
    (pkg / "main.py").write_text("from .other import FOO as BAR\n")
    result = python_module_symbol_detail(pkg / "main.py", "BAR")
    assert result == "symbol"


def test_python_module_symbol_detail_reexport_cycle(tmp_path: Path) -> None:
    pkg = tmp_path / "docassemble" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "mod_a.py").write_text("from .mod_b import x as a\n")
    (pkg / "mod_b.py").write_text("from .mod_a import a as x\n")
    result = python_module_symbol_detail(pkg / "mod_a.py", "a")
    assert result == "symbol"


def test_module_completion_members_empty(tmp_path: Path) -> None:
    mod_path = tmp_path / "empty.py"
    _write_py_file(mod_path, "")
    assert module_completion_members(mod_path, ()) == {}
    assert module_completion_members(mod_path, ("missing",)) == {}


def test_module_completion_members_public_only(tmp_path: Path) -> None:
    mod_path = tmp_path / "mymod.py"
    _write_py_file(mod_path, "FOO = 1\n_BAR = 2\n")
    result = module_completion_members(mod_path, ())
    assert result == {"FOO": "symbol"}


def test_module_completion_members_class_methods(tmp_path: Path) -> None:
    mod_path = tmp_path / "mymod.py"
    _write_py_file(
        mod_path, "class MyClass:\n    def pub(self): pass\n    def _priv(self): pass\n"
    )
    result = module_completion_members(mod_path, ("MyClass",))
    assert result == {"pub": "method", "_priv": "method"}


def test_clear_module_index_cache_directory_evicts_children(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("X=1\n")
    b = tmp_path / "b.py"
    b.write_text("Y=1\n")
    index_a = load_python_module_index(a)
    index_b = load_python_module_index(b)
    clear_module_index_cache([tmp_path])
    assert load_python_module_index(a) is not index_a
    assert load_python_module_index(b) is not index_b
