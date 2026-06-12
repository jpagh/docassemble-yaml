from __future__ import annotations

import os
import time

from docassemble_lsp.core import build_workspace_index
from docassemble_lsp.core.files import (
    _discover_package_roots,
    collect_template_file_names,
    detect_docassemble_package,
    discover_templates_dir,
)
from docassemble_lsp.core.workspace import WorkspaceIndex, WorkspaceYamlSources


def test_detect_docassemble_package_valid_structure(tmp_path) -> None:
    """detect_docassemble_package returns root for valid docassemble package."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    yaml_file = pkg_dir / "data" / "questions" / "main.yml"
    yaml_file.parent.mkdir(parents=True)
    yaml_file.write_text("question: Hi\n", encoding="utf-8")

    result = detect_docassemble_package(yaml_file)
    assert result == tmp_path


def test_detect_docassemble_package_missing_pyproject(tmp_path) -> None:
    """detect_docassemble_package returns None without pyproject.toml."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    result = detect_docassemble_package(pkg_dir / "data")
    assert result is None


def test_detect_docassemble_package_missing_init(tmp_path) -> None:
    """detect_docassemble_package returns None without __init__.py."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    result = detect_docassemble_package(pkg_dir / "data")
    assert result is None


def test_detect_docassemble_package_missing_data_dir(tmp_path) -> None:
    """detect_docassemble_package returns None without data/ directory."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    result = detect_docassemble_package(pkg_dir)
    assert result is None


def test_detect_docassemble_package_non_docassemble_dir(tmp_path) -> None:
    """detect_docassemble_package returns None for a plain directory."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    (tmp_path / "some_file.yml").write_text("question: Hi\n", encoding="utf-8")

    result = detect_docassemble_package(tmp_path / "some_file.yml")
    assert result is None


def test_workspace_yaml_sources_overlay_current_document(tmp_path) -> None:
    source_path = tmp_path / "interview.yml"
    source_path.write_text("question: Saved\n", encoding="utf-8")

    sources = WorkspaceYamlSources.from_roots(
        [tmp_path],
        current_path=source_path,
        current_source="question: Unsaved\n",
    )

    assert sources.as_candidate_pairs() == [(source_path.resolve(), "question: Unsaved\n")]
    assert sources.as_source_dict() == {source_path.resolve(): "question: Unsaved\n"}


def test_workspace_yaml_sources_skip_non_utf8_files(tmp_path) -> None:
    valid_path = tmp_path / "valid.yml"
    valid_path.write_text("question: Valid\n", encoding="utf-8")
    invalid_path = tmp_path / "invalid.yml"
    invalid_path.write_bytes(b"\xff")

    sources = WorkspaceYamlSources.from_roots([tmp_path])

    assert sources.as_candidate_pairs() == [(valid_path.resolve(), "question: Valid\n")]


def test_workspace_yaml_sources_can_rebuild_from_source_dict(tmp_path) -> None:
    source_path = tmp_path / "interview.yml"
    source_cache = {source_path.resolve(): "question: Cached\n"}

    sources = WorkspaceYamlSources.from_source_dict(source_cache)

    assert sources.as_candidate_pairs() == [(source_path.resolve(), "question: Cached\n")]


def test_workspace_index_bundles_sources(tmp_path) -> None:
    main_path = tmp_path / "main.yml"
    main_path.write_text("include:\n  - shared.yml\n", encoding="utf-8")
    shared_path = tmp_path / "shared.yml"
    shared_path.write_text("question: Shared\n", encoding="utf-8")

    index = WorkspaceIndex.from_yaml_roots([tmp_path])

    assert index.as_source_dict()[main_path.resolve()] == "include:\n  - shared.yml\n"
    assert index.search_roots == (tmp_path.resolve(),)
    assert index.document_facts(main_path.resolve())[0].name == "include"


def test_workspace_index_can_represent_single_current_document(tmp_path) -> None:
    source_path = tmp_path / "unsaved.yml"

    index = WorkspaceIndex.from_current_document(
        source_path,
        "question: Unsaved\n",
    )

    assert index.as_candidate_pairs() == [(source_path.resolve(), "question: Unsaved\n")]
    assert index.search_roots == ()
    assert index.document_facts(source_path)[0].name == "Unsaved"


def test_workspace_index_can_overlay_current_document(tmp_path) -> None:
    source_path = tmp_path / "interview.yml"
    source_path.write_text("question: Saved\n", encoding="utf-8")

    index = WorkspaceIndex.from_yaml_roots(
        [tmp_path],
    )
    updated_index = index.with_current_document(
        source_path,
        "question: Unsaved\n",
    )

    assert index.as_candidate_pairs() == [(source_path.resolve(), "question: Saved\n")]
    assert updated_index.as_candidate_pairs() == [(source_path.resolve(), "question: Unsaved\n")]
    assert updated_index.search_roots == (tmp_path.resolve(),)
    assert index.document_facts(source_path)[0].name == "Saved"
    assert updated_index.document_facts(source_path)[0].name == "Unsaved"


def test_detect_not_cached_none(tmp_path) -> None:
    """detect_docassemble_package does not cache None results."""
    # Non-package directory — result should be None and NOT cached.
    result = detect_docassemble_package(tmp_path / "some_file.yml")
    assert result is None

    # Now create the package structure.
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    # Should now find the package (not a stale None cache entry).
    result = detect_docassemble_package(tmp_path / "some_file.yml")
    assert result == tmp_path


def test_detect_positive_cache_hit(tmp_path) -> None:
    """detect_docassemble_package caches positive results and serves them."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    yaml_file = pkg_dir / "data" / "questions" / "main.yml"
    yaml_file.parent.mkdir(parents=True)
    yaml_file.write_text("question: Hi\n", encoding="utf-8")

    # First call — should find and cache.
    result1 = detect_docassemble_package(yaml_file)
    assert result1 == tmp_path

    # Second call — should hit cache.
    result2 = detect_docassemble_package(yaml_file)
    assert result2 == tmp_path
    assert result2 is result1  # same object from cache


def test_detect_positive_invalidated_by_pyproject_mtime(tmp_path) -> None:
    """detect_docassemble_package re-evaluates when pyproject.toml mtime changes."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    yaml_file = pkg_dir / "data" / "questions" / "main.yml"
    yaml_file.parent.mkdir(parents=True)
    yaml_file.write_text("question: Hi\n", encoding="utf-8")

    # First call — caches positive result.
    result1 = detect_docassemble_package(yaml_file)
    assert result1 == tmp_path

    # Advance pyproject.toml's mtime to simulate external modification.
    future = time.time() + 60
    os.utime(pyproject, (future, future))

    # Second call — cache invalidated by mtime mismatch, re-evaluates.
    result2 = detect_docassemble_package(yaml_file)
    assert result2 == tmp_path


def test_discover_templates_dir(tmp_path) -> None:
    """discover_templates_dir finds data/templates/ under a known package root."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    template_dir = pkg_dir / "data" / "templates"
    template_dir.mkdir(parents=True)

    result = discover_templates_dir(tmp_path)
    assert result == template_dir.resolve()


def test_discover_templates_dir_none_when_no_templates(tmp_path) -> None:
    """discover_templates_dir returns None when no data/templates/ exists."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    # Create data/ but not data/templates/
    (pkg_dir / "data" / "questions").mkdir(parents=True)

    result = discover_templates_dir(tmp_path)
    assert result is None


def test_discover_templates_dir_none_when_no_package(tmp_path) -> None:
    """discover_templates_dir returns None when the path is not a package root."""
    result = discover_templates_dir(tmp_path)
    assert result is None


def test_collect_template_file_names(tmp_path) -> None:
    """collect_template_file_names returns file names from the templates dir."""
    (tmp_path / "letter.docx").write_text("", encoding="utf-8")
    (tmp_path / "form.pdf").write_text("", encoding="utf-8")
    (tmp_path / "reference.docx").write_text("", encoding="utf-8")
    (tmp_path / ".DS_Store").write_text("", encoding="utf-8")  # dotfiles are regular files, included
    (tmp_path / "subdir").mkdir()  # directories are excluded

    names = collect_template_file_names(tmp_path)
    assert names == frozenset({"letter.docx", "form.pdf", "reference.docx", ".DS_Store"})


def test_collect_template_file_names_empty(tmp_path) -> None:
    """collect_template_file_names returns empty frozenset for empty dir."""
    names = collect_template_file_names(tmp_path)
    assert names == frozenset()


def test_workspace_index_templates_dir_populated(tmp_path) -> None:
    """WorkspaceIndex eagerly populates package_templates_dirs and template_file_names."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    questions_dir = pkg_dir / "data" / "questions"
    template_dir = pkg_dir / "data" / "templates"
    questions_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    (template_dir / "letter.docx").write_text("placeholder", encoding="utf-8")
    (template_dir / "form.pdf").write_text("placeholder", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    source_path = questions_dir / "main.yml"
    source_path.write_text("question: Hi\n", encoding="utf-8")

    index = build_workspace_index([tmp_path], current_path=source_path, current_source="question: Hi\n")

    assert index.package_root == tmp_path
    assert tmp_path.resolve() in index.package_templates_dirs
    assert index.package_templates_dirs[tmp_path.resolve()] == template_dir.resolve()
    assert index.templates_dir_for(source_path) == template_dir.resolve()
    assert index.template_file_names == frozenset({"letter.docx", "form.pdf"})


def test_workspace_index_templates_dir_none_when_no_templates(tmp_path) -> None:
    """WorkspaceIndex leaves templates fields as defaults when no data/templates/."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    questions_dir = pkg_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    source_path = questions_dir / "main.yml"
    source_path.write_text("question: Hi\n", encoding="utf-8")

    index = build_workspace_index([tmp_path], current_path=source_path, current_source="question: Hi\n")

    assert index.package_root == tmp_path
    assert index.package_templates_dirs == {}
    assert index.template_file_names == frozenset()


def test_workspace_index_templates_propagate_through_with_overlays(tmp_path) -> None:
    """package_templates_dirs and template_file_names propagate through with_overlays()."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    questions_dir = pkg_dir / "data" / "questions"
    template_dir = pkg_dir / "data" / "templates"
    questions_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    (template_dir / "letter.docx").write_text("placeholder", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    source_path = questions_dir / "main.yml"
    source_path.write_text("question: Saved\n", encoding="utf-8")

    index = build_workspace_index([tmp_path], current_path=source_path, current_source="question: Saved\n")
    overlaid = index.with_overlays({source_path: "question: Overlaid\n"})

    assert tmp_path.resolve() in overlaid.package_templates_dirs
    assert overlaid.package_templates_dirs[tmp_path.resolve()] == template_dir.resolve()
    assert overlaid.template_file_names == frozenset({"letter.docx"})


def test_workspace_index_templates_propagate_through_with_current_document(tmp_path) -> None:
    """package_templates_dirs and template_file_names propagate through with_current_document()."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    questions_dir = pkg_dir / "data" / "questions"
    template_dir = pkg_dir / "data" / "templates"
    questions_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    (template_dir / "letter.docx").write_text("placeholder", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    source_path = questions_dir / "main.yml"
    source_path.write_text("question: Saved\n", encoding="utf-8")

    index = WorkspaceIndex.from_yaml_roots([tmp_path])
    updated = index.with_current_document(source_path, "question: Updated\n")

    assert updated.package_templates_dirs == {}  # from_yaml_roots doesn't populate
    assert updated.template_file_names == frozenset()


def test_workspace_index_field_var_decls_through_overlays(tmp_path) -> None:
    """Field var declarations from ALL overlay paths are present after with_overlays()."""
    main_a = tmp_path / "a.yml"
    main_b = tmp_path / "b.yml"
    main_a.write_text("question: A\n", encoding="utf-8")
    main_b.write_text("question: B\n", encoding="utf-8")

    base = WorkspaceIndex.from_yaml_roots([tmp_path])
    assert base.all_field_var_names == frozenset()

    overlaid = base.with_overlays(
        {
            main_a: "fields:\n  - field: name_a\n",
            main_b: "fields:\n  - field: name_b\n",
        }
    )

    assert "name_a" in overlaid.all_field_var_names
    assert "name_b" in overlaid.all_field_var_names
    assert len(overlaid.all_field_var_names) == 2


def test_templates_dir_fallback_still_works(tmp_path) -> None:
    """When no workspace_index is available, templates_dir_for_path lazy fallback still resolves templates."""
    pkg_dir = tmp_path / "docassemble" / "demo"
    questions_dir = pkg_dir / "data" / "questions"
    template_dir = pkg_dir / "data" / "templates"
    questions_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    (template_dir / "letter.docx").write_text("placeholder", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    yaml_path = questions_dir / "main.yml"
    yaml_path.write_text("question: Hi\n", encoding="utf-8")

    from docassemble_lsp.core.files import templates_dir_for_path

    tdir = templates_dir_for_path(yaml_path)
    assert tdir == template_dir.resolve()


def test_discover_package_roots_mtime(tmp_path) -> None:
    """_discover_package_roots re-evaluates when search root mtime changes."""
    # Create a valid package inside tmp_path.
    pkg_dir = tmp_path / "docassemble" / "demo"
    pkg_dir.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    # First discovery — caches result.
    roots1 = _discover_package_roots([tmp_path])
    assert roots1 == [tmp_path.resolve()]

    # Advance tmp_path's mtime.
    future = time.time() + 60
    os.utime(tmp_path, (future, future))

    # Second discovery — mtime mismatch causes re-discovery.
    roots2 = _discover_package_roots([tmp_path])
    assert roots2 == [tmp_path.resolve()]


def test_workspace_index_templates_multi_package(tmp_path) -> None:
    """Multi-package workspace: each file resolves to its own package's templates dir."""
    # Package A: docassemble/alpha
    alpha_root = tmp_path / "alpha_pkg"
    alpha_pkg = alpha_root / "docassemble" / "alpha"
    alpha_questions = alpha_pkg / "data" / "questions"
    alpha_templates = alpha_pkg / "data" / "templates"
    alpha_questions.mkdir(parents=True)
    alpha_templates.mkdir(parents=True)
    (alpha_templates / "alpha_form.docx").write_text("alpha", encoding="utf-8")
    (alpha_root / "pyproject.toml").write_text("[project]\nname = 'alpha'\n", encoding="utf-8")
    (alpha_pkg / "__init__.py").write_text("", encoding="utf-8")

    # Package B: docassemble/beta
    beta_root = tmp_path / "beta_pkg"
    beta_pkg = beta_root / "docassemble" / "beta"
    beta_questions = beta_pkg / "data" / "questions"
    beta_templates = beta_pkg / "data" / "templates"
    beta_questions.mkdir(parents=True)
    beta_templates.mkdir(parents=True)
    (beta_templates / "beta_form.docx").write_text("beta", encoding="utf-8")
    (beta_templates / "shared.docx").write_text("shared", encoding="utf-8")
    (beta_root / "pyproject.toml").write_text("[project]\nname = 'beta'\n", encoding="utf-8")
    (beta_pkg / "__init__.py").write_text("", encoding="utf-8")

    # Workspace root is the parent directory containing both packages.
    workspace_root = tmp_path
    alpha_source = alpha_questions / "alpha_main.yml"
    alpha_source.write_text("question: Alpha\n", encoding="utf-8")
    beta_source = beta_questions / "beta_main.yml"
    beta_source.write_text("question: Beta\n", encoding="utf-8")

    index = build_workspace_index([workspace_root])

    # Both package roots should be in the mapping.
    assert alpha_root.resolve() in index.package_templates_dirs
    assert beta_root.resolve() in index.package_templates_dirs
    assert index.package_templates_dirs[alpha_root.resolve()] == alpha_templates.resolve()
    assert index.package_templates_dirs[beta_root.resolve()] == beta_templates.resolve()

    # templates_dir_for should resolve each file to its own package.
    assert index.templates_dir_for(alpha_source) == alpha_templates.resolve()
    assert index.templates_dir_for(beta_source) == beta_templates.resolve()

    # Aggregated template names include files from both packages.
    assert index.template_file_names == frozenset({"alpha_form.docx", "beta_form.docx", "shared.docx"})
