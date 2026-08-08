from __future__ import annotations

from pathlib import Path

import pytest

from docassemble_lsp.core.files import (
    collect_dayaml_cli_args,
    collect_dayaml_conventions,
    collect_dayaml_ignore_codes,
    find_nearest_dayaml_config_dir,
    load_dayaml_project_config,
)

_DEDICATED_CONFIG_FILENAMES = (
    "docassemble-lsp.toml",
    ".docassemble-lsp.toml",
    ".config/docassemble-lsp.toml",
)


@pytest.mark.parametrize("filename", _DEDICATED_CONFIG_FILENAMES)
def test_load_dayaml_config_from_dedicated_files(tmp_path: Path, filename: str) -> None:
    config_path = tmp_path / filename
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        'conventions = ["C102"]\n'
        'ignore-codes = ["E301"]\n'
        'args = ["--indent", "4"]\n'
        "lsp_args = ['--no-warnings']\n",
        encoding="utf-8",
    )

    config = load_dayaml_project_config(tmp_path)

    assert config is not None
    assert config.conventions == frozenset({"C102"})
    assert config.ignore_codes == frozenset({"E301"})
    assert config.cli_args == ("--indent", "4")
    assert config.lsp_cli_args == ("--no-warnings",)
    assert config.yaml_path is None


def test_dedicated_config_takes_precedence_over_pyproject_section(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.docassemble-lsp]\nconventions = ["C103"]\n', encoding="utf-8"
    )
    (tmp_path / "docassemble-lsp.toml").write_text(
        'conventions = ["C102"]\n', encoding="utf-8"
    )

    config = load_dayaml_project_config(tmp_path)

    assert config is not None
    assert config.conventions == frozenset({"C102"})


def test_pyproject_without_section_does_not_shadow_dedicated_config_in_same_dir(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example'\n", encoding="utf-8"
    )
    (tmp_path / "docassemble-lsp.toml").write_text(
        'conventions = ["C102"]\n', encoding="utf-8"
    )

    config = load_dayaml_project_config(tmp_path)

    assert config is not None
    assert config.conventions == frozenset({"C102"})


def test_find_nearest_config_dir_walks_up_past_sectionless_pyproject(
    tmp_path: Path,
) -> None:
    # An intermediate pyproject.toml without a docassemble-lsp section must
    # not stop discovery of a dedicated config file in a parent directory.
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example'\n", encoding="utf-8"
    )
    (tmp_path / "docassemble-lsp.toml").write_text(
        'conventions = ["C102"]\n', encoding="utf-8"
    )
    nested = tmp_path / "docs" / "interviews"
    nested.mkdir(parents=True)

    assert find_nearest_dayaml_config_dir(nested) == tmp_path
    assert collect_dayaml_conventions([nested]) == frozenset({"C102"})
    assert collect_dayaml_ignore_codes([nested]) == frozenset()
    assert collect_dayaml_cli_args([nested]) == ()


def test_find_nearest_config_dir_returns_none_without_config(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)

    assert find_nearest_dayaml_config_dir(nested) is None
    assert collect_dayaml_conventions([nested]) == frozenset()


def test_nested_project_config_is_used_alone_without_root_merge(
    tmp_path: Path,
) -> None:
    """A config in a nested project fully replaces the root config for
    documents in that project — conventions are never merged across levels."""
    (tmp_path / "docassemble-lsp.toml").write_text(
        'conventions = ["C102"]\n', encoding="utf-8"
    )
    project = tmp_path / "project"
    project.mkdir()
    (project / "docassemble-lsp.toml").write_text(
        'conventions = ["C103"]\n', encoding="utf-8"
    )

    project_config = load_dayaml_project_config(project)
    root_config = load_dayaml_project_config(tmp_path)

    assert project_config is not None
    assert root_config is not None
    assert project_config.conventions == frozenset({"C103"})
    assert root_config.conventions == frozenset({"C102"})
    assert find_nearest_dayaml_config_dir(project) == project
    assert collect_dayaml_conventions([project]) == frozenset({"C103"})


def test_dedicated_config_yaml_path_resolves_relative_to_project_dir(
    tmp_path: Path,
) -> None:
    (tmp_path / "docassemble-lsp.toml").write_text(
        "yaml_path = 'docassemble'\n", encoding="utf-8"
    )

    config = load_dayaml_project_config(tmp_path)

    assert config is not None
    assert config.yaml_path == tmp_path / "docassemble"


def test_dedicated_config_with_tool_section_uses_top_level_keys(
    tmp_path: Path,
) -> None:
    # A dedicated file is read as a bare mapping; a [tool.docassemble-lsp]
    # section inside it is not consulted.
    (tmp_path / "docassemble-lsp.toml").write_text(
        '[tool.docassemble-lsp]\nconventions = ["C102"]\n', encoding="utf-8"
    )

    config = load_dayaml_project_config(tmp_path)

    assert config is not None
    assert config.conventions == frozenset()
