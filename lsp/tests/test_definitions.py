from __future__ import annotations

from pathlib import Path
from typing import Any

from docassemble_lsp.core import (
    build_workspace_index,
    python_modules,
)
from docassemble_lsp.core import (
    resolve_definition_targets as core_resolve_definition_targets,
)
from docassemble_lsp.core import (
    resolve_reference_targets as core_resolve_reference_targets,
)
from docassemble_lsp.core import (
    resolve_workspace_symbol_targets as core_resolve_workspace_symbol_targets,
)
from docassemble_lsp.core.python_paths import (
    path_from_uri_or_path,
    resolve_package_qualified_path,
)
from docassemble_lsp.core.workspace import WorkspaceIndex


def _workspace_index_for_tests(
    root: Path,
    *,
    current_path: Path | None = None,
    current_source: str | None = None,
) -> WorkspaceIndex:
    return build_workspace_index(
        [root],
        current_path=current_path,
        current_source=current_source,
    )


def _workspace_index_from_test_args(
    source: str,
    uri_or_path: str | Path | None,
    workspace_paths: list[Path] | None,
    workspace_index: WorkspaceIndex | None,
) -> WorkspaceIndex:
    if workspace_index is not None:
        return workspace_index
    current_path = path_from_uri_or_path(uri_or_path)
    roots = workspace_paths or (
        [current_path.parent] if current_path is not None else []
    )
    return build_workspace_index(
        roots,
        current_path=current_path,
        current_source=source if current_path else None,
    )


def resolve_definition_targets(
    source: str, line: int, character: int, **kwargs: Any
) -> Any:
    uri_or_path = kwargs.pop("uri_or_path", None)
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    return core_resolve_definition_targets(
        source,
        line,
        character,
        uri_or_path=uri_or_path,
        workspace_index=_workspace_index_from_test_args(
            source, uri_or_path, workspace_paths, workspace_index
        ),
        **kwargs,
    )


def resolve_reference_targets(
    source: str, line: int, character: int, **kwargs: Any
) -> Any:
    uri_or_path = kwargs.pop("uri_or_path", None)
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    return core_resolve_reference_targets(
        source,
        line,
        character,
        uri_or_path=uri_or_path,
        workspace_index=_workspace_index_from_test_args(
            source, uri_or_path, workspace_paths, workspace_index
        ),
        **kwargs,
    )


def resolve_workspace_symbol_targets(query: str, **kwargs: Any) -> Any:
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    if workspace_index is None:
        workspace_index = build_workspace_index(workspace_paths or [])
    return core_resolve_workspace_symbol_targets(
        query, workspace_index=workspace_index, **kwargs
    )


def test_resolve_definition_targets_for_usedefs_points_to_def(tmp_path) -> None:
    source_path = tmp_path / "interview.yml"
    source = "---\ndef: my_explanation\ncode: |\n  return 'hello'\n---\nusedefs:\n  - my_explanation\nmandatory: True\n"

    targets = resolve_definition_targets(
        source, 6, len("  - my_explanation") - 2, uri_or_path=source_path
    )

    assert len(targets) == 1
    assert targets[0].path == source_path
    assert targets[0].line == 1


def test_resolve_python_module_source_prefers_workspace_package(tmp_path) -> None:
    util_path = tmp_path / "docassemble" / "base" / "util.py"
    util_path.parent.mkdir(parents=True)
    util_path.write_text("class Address:\n    pass\n", encoding="utf-8")

    resolution = python_modules.resolve_python_module_source(
        "docassemble.base.util",
        workspace_index=build_workspace_index([tmp_path]),
    )

    assert resolution.source_kind == "workspace"
    assert resolution.path == util_path.resolve()


def test_resolve_python_module_source_falls_back_to_vendored(monkeypatch) -> None:
    monkeypatch.setattr(python_modules.importlib.util, "find_spec", lambda _name: None)

    resolution = python_modules.resolve_python_module_source(
        "docassemble.base.util",
        workspace_index=WorkspaceIndex.empty(),
    )

    assert resolution.source_kind == "vendored"
    assert resolution.path is not None
    assert resolution.path.name == "vendored_docassemble_base_util.pyi"


def test_resolve_python_module_source_falls_back_to_vendored_functions(
    monkeypatch,
) -> None:
    monkeypatch.setattr(python_modules.importlib.util, "find_spec", lambda _name: None)

    resolution = python_modules.resolve_python_module_source(
        "docassemble.base.functions",
        workspace_index=WorkspaceIndex.empty(),
    )

    assert resolution.source_kind == "vendored"
    assert resolution.path is not None
    assert resolution.path.name == "vendored_docassemble_base_functions.pyi"


def test_python_module_symbol_details_respect_all_and_imported_exports(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    package_dir.mkdir(parents=True)
    (package_dir / "shared.py").write_text(
        "class ExportedClass:\n    pass\n\ndef exported_function():\n    return 1\n",
        encoding="utf-8",
    )
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "from docassemble.demo.shared import ExportedClass, exported_function\n"
        "__all__ = ['ExportedClass', 'exported_function']\n"
        "def hidden_helper():\n    return 2\n",
        encoding="utf-8",
    )

    details = python_modules.python_module_symbol_details(helper_path)

    assert details == {
        "ExportedClass": "class",
        "exported_function": "function",
    }


def test_resolve_definition_targets_for_include_points_to_local_file(tmp_path) -> None:
    included = tmp_path / "included.yml"
    included.write_text("question: Included\n", encoding="utf-8")
    source_path = tmp_path / "interview.yml"
    source = "include:\n  - included.yml\n"

    targets = resolve_definition_targets(
        source, 1, len("  - included.yml") - 2, uri_or_path=source_path
    )

    assert len(targets) == 1
    assert targets[0].path == included.resolve()
    assert targets[0].line == 0


def test_resolve_definition_targets_for_package_qualified_include(tmp_path) -> None:
    pkg_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    pkg_dir.mkdir(parents=True)
    shared = pkg_dir / "shared.yml"
    shared.write_text("question: Shared\n", encoding="utf-8")
    source_path = pkg_dir / "interview.yml"
    source = "include:\n  - docassemble.demo:data/questions/shared.yml\n"
    pkg_ref = "docassemble.demo:data/questions/shared.yml"

    targets = resolve_definition_targets(
        source,
        1,
        source.splitlines()[1].index(pkg_ref) + 5,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert len(targets) == 1
    assert targets[0].path == shared.resolve()
    assert targets[0].line == 0


def test_resolve_definition_targets_for_package_qualified_include_from_package_roots(
    tmp_path,
) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    shared = questions / "shared.yml"
    shared.write_text("question: Shared\n", encoding="utf-8")
    source_path = questions / "interview.yml"
    source = "include:\n  - docassemble.demo:data/questions/shared.yml\n"
    pkg_ref = "docassemble.demo:data/questions/shared.yml"

    for workspace_root in (pkg_root, questions):
        targets = resolve_definition_targets(
            source,
            1,
            source.splitlines()[1].index(pkg_ref) + 5,
            uri_or_path=source_path,
            workspace_paths=[workspace_root],
        )

        assert len(targets) == 1
        assert targets[0].path == shared.resolve()


def test_resolve_definition_targets_for_quoted_package_qualified_include(
    tmp_path,
) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    shared = questions / "shared.yml"
    shared.write_text("question: Shared\n", encoding="utf-8")
    source_path = questions / "interview.yml"
    source = 'include:\n  - "docassemble.demo:data/questions/shared.yml"\n'
    pkg_ref = "docassemble.demo:data/questions/shared.yml"

    targets = resolve_definition_targets(
        source,
        1,
        source.splitlines()[1].index(pkg_ref) + 5,
        uri_or_path=source_path,
        workspace_paths=[pkg_root],
    )

    assert len(targets) == 1
    assert targets[0].path == shared.resolve()


def test_resolve_package_qualified_path_rejects_parent_traversal(tmp_path) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    pkg_root.mkdir(parents=True)
    outside = tmp_path / "secret.yml"
    outside.write_text("question: Secret\n", encoding="utf-8")

    assert (
        resolve_package_qualified_path("docassemble.demo:../../secret.yml", [tmp_path])
        is None
    )


def test_resolve_definition_targets_for_package_qualified_template_file(
    tmp_path,
) -> None:
    pkg_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    templates = pkg_dir / "templates"
    templates.mkdir(parents=True)
    letter = templates / "letter.docx"
    letter.write_text("placeholder", encoding="utf-8")
    source_path = pkg_dir / "interview.yml"
    source = "attachment:\n  - docx template file: docassemble.demo:data/questions/templates/letter.docx\n"
    pkg_ref = "docassemble.demo:data/questions/templates/letter.docx"

    targets = resolve_definition_targets(
        source,
        1,
        source.splitlines()[1].index(pkg_ref) + 5,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert len(targets) == 1
    assert targets[0].path == letter.resolve()
    assert targets[0].line == 0


def test_resolve_definition_targets_for_static_css_file_wins_over_python_symbol(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions = package_dir / "data" / "questions"
    static = package_dir / "data" / "static"
    questions.mkdir(parents=True)
    static.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "helpers.py").write_text(
        "def collapse_template():\n    return None\n", encoding="utf-8"
    )
    stylesheet = static / "collapse_template.css"
    stylesheet.write_text("", encoding="utf-8")
    source_path = questions / "interview.yml"
    source = "features:\n  css:\n    - collapse_template.css\n"
    ref = "collapse_template.css"

    targets = resolve_definition_targets(
        source,
        2,
        source.splitlines()[2].index(ref) + 3,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert [target.path for target in targets] == [stylesheet.resolve()]


def test_resolve_definition_targets_for_static_javascript_file_wins_over_python_symbol(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions = package_dir / "data" / "questions"
    static = package_dir / "data" / "static"
    questions.mkdir(parents=True)
    static.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "helpers.py").write_text(
        "def collapse_template():\n    return None\n", encoding="utf-8"
    )
    script = static / "collapse_template.js"
    script.write_text("", encoding="utf-8")
    source_path = questions / "interview.yml"
    source = "features:\n  javascript:\n    - collapse_template.js\n"
    ref = "collapse_template.js"

    targets = resolve_definition_targets(
        source,
        2,
        source.splitlines()[2].index(ref) + 3,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert [target.path for target in targets] == [script.resolve()]


def test_resolve_definition_targets_for_missing_static_file_does_not_fall_back_to_python_symbol(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions = package_dir / "data" / "questions"
    questions.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "helpers.py").write_text(
        "def collapse_template():\n    return None\n", encoding="utf-8"
    )
    source_path = questions / "interview.yml"
    source = "features:\n  css:\n    - collapse_template.css\n"
    ref = "collapse_template.css"

    targets = resolve_definition_targets(
        source,
        2,
        source.splitlines()[2].index(ref) + 3,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []


def test_resolve_reference_targets_for_quoted_package_qualified_include(
    tmp_path,
) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    shared = questions / "shared.yml"
    shared.write_text("question: Shared\n", encoding="utf-8")
    first = questions / "first.yml"
    first_source = 'include:\n  - "docassemble.demo:data/questions/shared.yml"\n'
    first.write_text(first_source, encoding="utf-8")
    second = questions / "second.yml"
    second.write_text(
        "include:\n  - docassemble.demo:data/questions/shared.yml\n", encoding="utf-8"
    )
    pkg_ref = "docassemble.demo:data/questions/shared.yml"

    targets = resolve_reference_targets(
        first_source,
        1,
        first_source.splitlines()[1].index(pkg_ref) + 5,
        uri_or_path=first,
        workspace_paths=[pkg_root],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("first.yml", 1),
        ("second.yml", 1),
        ("shared.yml", 0),
    ]


def test_resolve_definition_targets_for_objects_from_file_points_to_local_file(
    tmp_path,
) -> None:
    included = tmp_path / "object-map.yml"
    included.write_text("objects: []\n", encoding="utf-8")
    source_path = tmp_path / "interview.yml"
    source = "objects from file:\n  - claims: object-map.yml\n"

    targets = resolve_definition_targets(
        source, 1, len("  - claims: object-map.yml") - 3, uri_or_path=source_path
    )

    assert len(targets) == 1
    assert targets[0].path == included.resolve()
    assert targets[0].line == 0


def test_resolve_definition_targets_for_action_points_to_matching_event(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: Hi\n"
        "fields:\n"
        "  - Food: favorite_food\n"
        "    action: wordlist\n"
        "---\n"
        "event: wordlist\n"
        "code: |\n"
        "  return ['apple']\n"
    )

    targets = resolve_definition_targets(
        source, 3, len("    action: wordlist") - 2, uri_or_path=source_path
    )

    assert len(targets) == 1
    assert targets[0].path == source_path
    assert targets[0].line == 5


def test_resolve_definition_targets_for_error_action_points_to_matching_event(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "metadata:\n  error action: on_error\n---\nevent: on_error\nquestion: Sorry\n"
    )

    targets = resolve_definition_targets(
        source, 1, len("  error action: on_error") - 2, uri_or_path=source_path
    )

    assert len(targets) == 1
    assert targets[0].path == source_path
    assert targets[0].line == 3


def test_resolve_definition_targets_for_action_ignores_external_urls(tmp_path) -> None:
    source_path = tmp_path / "interview.yml"
    source = "action buttons:\n  - label: Visit\n    action: https://docassemble.org\n"

    targets = resolve_definition_targets(
        source,
        2,
        len("    action: https://docassemble.org") - 2,
        uri_or_path=source_path,
    )

    assert targets == []


def test_resolve_definition_targets_for_url_action_points_to_matching_event(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: Hi\n"
        "subquestion: |\n"
        '  ${ action_button_html(url_action("show_result"), label="Run") }\n'
        "---\n"
        "event: show_result\n"
        "question: Done\n"
    )

    targets = resolve_definition_targets(
        source,
        2,
        source.splitlines()[2].index("show_result") + 1,
        uri_or_path=source_path,
    )

    assert len(targets) == 1
    assert targets[0].path == source_path
    assert targets[0].line == 4


def test_resolve_reference_targets_for_usedefs_include_declaration(tmp_path) -> None:
    source_path = tmp_path / "interview.yml"
    source = "---\ndef: my_explanation\ncode: |\n  return 'hello'\n---\nusedefs:\n  - my_explanation\nmandatory: True\n"

    targets = resolve_reference_targets(
        source, 1, len("def: my_explanation") - 2, uri_or_path=source_path
    )

    assert [(target.path, target.line) for target in targets] == [
        (source_path, 1),
        (source_path, 6),
    ]


def test_resolve_reference_targets_for_action_include_declaration(tmp_path) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: Hi\n"
        "fields:\n"
        "  - Food: favorite_food\n"
        "    action: wordlist\n"
        "---\n"
        "event: wordlist\n"
        "code: |\n"
        "  return ['apple']\n"
        "---\n"
        "metadata:\n"
        "  error action: wordlist\n"
    )

    targets = resolve_reference_targets(
        source, 5, len("event: wordlist") - 2, uri_or_path=source_path
    )

    assert [(target.path, target.line) for target in targets] == [
        (source_path, 3),
        (source_path, 5),
        (source_path, 10),
    ]


def test_resolve_reference_targets_for_action_excludes_declaration_when_requested(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = "action buttons:\n  - label: Run\n    action: my_event\n---\nevent: my_event\nquestion: Done\n"

    targets = resolve_reference_targets(
        source,
        4,
        len("event: my_event") - 2,
        uri_or_path=source_path,
        include_declaration=False,
    )

    assert [(target.path, target.line) for target in targets] == [(source_path, 2)]


def test_resolve_reference_targets_for_event_include_helper_calls(tmp_path) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "code: |\n"
        '  menu_items.append(action_menu_item("Save", "save_screen"))\n'
        "---\n"
        "subquestion: |\n"
        '  ${ action_button_html(url_action("save_screen"), label="Run") }\n'
        "---\n"
        "event: save_screen\n"
        "question: Done\n"
    )

    targets = resolve_reference_targets(
        source, 6, len("event: save_screen") - 2, uri_or_path=source_path
    )

    assert [(target.path, target.line) for target in targets] == [
        (source_path, 1),
        (source_path, 4),
        (source_path, 6),
    ]


def test_resolve_reference_targets_for_included_file_scans_workspace(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    target = package_dir / "shared.yml"
    target.write_text("question: Shared\n", encoding="utf-8")
    first = package_dir / "first.yml"
    first.write_text("include:\n  - shared.yml\n", encoding="utf-8")
    second = package_dir / "second.yml"
    second.write_text(
        "attachment options:\n  initial yaml:\n    - shared.yml\n", encoding="utf-8"
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.docassemble-lsp]\nyaml_path = 'docassemble'\n", encoding="utf-8"
    )

    targets = resolve_reference_targets(
        first.read_text(encoding="utf-8"),
        1,
        len("  - shared.yml") - 2,
        uri_or_path=first,
        workspace_paths=[tmp_path],
    )

    assert [(entry.path.name, entry.line) for entry in targets] == [
        ("first.yml", 1),
        ("second.yml", 2),
        ("shared.yml", 0),
    ]


def test_resolve_reference_targets_can_use_workspace_index(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    main = package_dir / "main.yml"
    main.write_text(
        "action buttons:\n  - label: Run\n    action: library_event\n", encoding="utf-8"
    )
    library = package_dir / "library.yml"
    library.write_text(
        "event: library_event\nquestion: From library\n", encoding="utf-8"
    )

    targets = resolve_reference_targets(
        library.read_text(encoding="utf-8"),
        0,
        len("event: library_event") - 2,
        uri_or_path=library,
        workspace_index=_workspace_index_for_tests(tmp_path),
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("library.yml", 0),
        ("main.yml", 2),
    ]


def test_resolve_reference_targets_does_not_fallback_to_yaml_file_on_unrelated_cursor(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = "question: Hello there\n"

    targets = resolve_reference_targets(
        source,
        0,
        len("question: He"),
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []


def test_resolve_reference_targets_for_docx_template_file_from_target_file(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    template_dir = package_dir / "templates"
    template_dir.mkdir(parents=True)
    target = template_dir / "letter.docx"
    target.write_text("placeholder", encoding="utf-8")
    first = package_dir / "main.yml"
    first.write_text(
        "attachment:\n  - docx template file: templates/letter.docx\n", encoding="utf-8"
    )
    second = package_dir / "secondary.yml"
    second.write_text(
        "attachment:\n  - docx template file: templates/letter.docx\n", encoding="utf-8"
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.docassemble-lsp]\nyaml_path = 'docassemble'\n", encoding="utf-8"
    )

    targets = resolve_reference_targets(
        target.read_text(encoding="utf-8"),
        0,
        0,
        uri_or_path=target,
        workspace_paths=[tmp_path],
    )

    assert [(entry.path.name, entry.line) for entry in targets] == [
        ("main.yml", 1),
        ("secondary.yml", 1),
        ("letter.docx", 0),
    ]


def test_resolve_definition_targets_for_modules_symbol_in_mako_points_to_python_function(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "def plus_one(value):\n    return value + 1\n", encoding="utf-8"
    )
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n"

    targets = resolve_definition_targets(
        source,
        4,
        source.splitlines()[4].index("plus_one") + 1,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("helpers.py", 0)
    ]


def test_resolve_definition_targets_for_imports_namespace_points_to_python_method(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    helper_path = package_dir / "math_helpers.py"
    helper_path.write_text(
        "class MathHelper:\n    @staticmethod\n    def bump(value):\n        return value + 1\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = "imports:\n  - docassemble.demo.math_helpers\n---\ncode: |\n  result = math_helpers.MathHelper.bump(3)\n"

    targets = resolve_definition_targets(
        source,
        4,
        source.splitlines()[4].index("bump") + 1,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []


def test_resolve_definition_targets_for_modules_entry_points_to_python_module(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "def plus_one(value):\n    return value + 1\n", encoding="utf-8"
    )
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n"

    targets = resolve_definition_targets(
        source,
        1,
        len("  - .helpers") - 2,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("helpers.py", 0)
    ]


def test_resolve_definition_targets_for_package_qualified_modules_entry(
    tmp_path,
) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    module_path = pkg_root / "external.py"
    module_path.write_text("def helper():\n    return 42\n", encoding="utf-8")
    source_path = questions / "interview.yml"
    source = "modules:\n  - docassemble.demo:external.py\n"

    targets = resolve_definition_targets(
        source,
        1,
        source.splitlines()[1].index("docassemble.demo:external.py") + 5,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert len(targets) == 1
    assert targets[0].path == module_path.resolve()
    assert targets[0].line == 0


def test_resolve_reference_targets_for_package_qualified_modules_entry(
    tmp_path,
) -> None:
    pkg_root = tmp_path / "docassemble" / "demo"
    questions = pkg_root / "data" / "questions"
    questions.mkdir(parents=True)
    module_path = pkg_root / "external.py"
    module_path.write_text("def helper():\n    return 42\n", encoding="utf-8")
    source_path = questions / "interview.yml"
    source = "modules:\n  - docassemble.demo:external.py\n---\ncode: |\n  helper()\n"

    targets = resolve_reference_targets(
        source,
        1,
        source.splitlines()[1].index("docassemble.demo:external.py") + 5,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    # Two targets: the file declaration (line 0 of external.py) and the
    # file-reference occurrence in the modules list item (interview.yml line 1).
    assert len(targets) == 2
    target_paths = {t.path for t in targets}
    assert module_path.resolve() in target_paths
    assert source_path.resolve() in target_paths


def test_resolve_reference_targets_for_python_symbol_scans_yaml_modules_and_imports(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "def plus_one(value):\n    return value + 1\n", encoding="utf-8"
    )
    main_path = questions_dir / "main.yml"
    main_source = (
        "modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n"
    )
    second_path = questions_dir / "second.yml"
    second_path.write_text(
        "modules:\n  - .helpers\n---\ncode: |\n  value = plus_one(4)\n",
        encoding="utf-8",
    )
    third_path = questions_dir / "third.yml"
    third_path.write_text(
        "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  value = helpers.plus_one(5)\n",
        encoding="utf-8",
    )

    targets = resolve_reference_targets(
        main_source,
        4,
        main_source.splitlines()[4].index("plus_one") + 1,
        uri_or_path=main_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []


def test_resolve_reference_targets_from_python_function_scans_yaml_namespaces(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_source = "def plus_one(value):\n    return value + 1\n"
    helper_path.write_text(helper_source, encoding="utf-8")
    (questions_dir / "main.yml").write_text(
        "modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n",
        encoding="utf-8",
    )
    (questions_dir / "second.yml").write_text(
        "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  value = helpers.plus_one(4)\n",
        encoding="utf-8",
    )

    targets = resolve_reference_targets(
        helper_source,
        0,
        helper_source.splitlines()[0].index("plus_one") + 1,
        uri_or_path=helper_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []


def test_resolve_reference_targets_from_python_method_scans_yaml_namespaces(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "math_helpers.py"
    helper_source = "class MathHelper:\n    @staticmethod\n    def bump(value):\n        return value + 1\n"
    helper_path.write_text(helper_source, encoding="utf-8")
    (questions_dir / "main.yml").write_text(
        "modules:\n  - .math_helpers\n---\nquestion: |\n  ${ MathHelper.bump(3) }\n",
        encoding="utf-8",
    )
    (questions_dir / "second.yml").write_text(
        "imports:\n  - docassemble.demo.math_helpers\n---\ncode: |\n  value = math_helpers.MathHelper.bump(4)\n",
        encoding="utf-8",
    )

    targets = resolve_reference_targets(
        helper_source,
        2,
        helper_source.splitlines()[2].index("bump") + 1,
        uri_or_path=helper_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []
    assert targets == []
    assert targets == []
    assert targets == []
    assert targets == []


def test_resolve_definition_targets_for_imports_module_alias_points_to_python_function(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "def plus_one(value):\n    return value + 1\n", encoding="utf-8"
    )
    source_path = questions_dir / "main.yml"
    source = "imports:\n  - docassemble.demo.helpers as helper_utils\n---\ncode: |\n  result = helper_utils.plus_one(3)\n"

    targets = resolve_definition_targets(
        source,
        4,
        source.splitlines()[4].index("plus_one") + 1,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("helpers.py", 0)
    ]


def test_resolve_definition_targets_for_imported_symbol_alias_points_to_python_function(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "def plus_one(value):\n    return value + 1\n", encoding="utf-8"
    )
    source_path = questions_dir / "main.yml"
    source = "imports:\n  - from docassemble.demo.helpers import plus_one as add_one\n---\ncode: |\n  result = add_one(3)\n"

    targets = resolve_definition_targets(
        source,
        4,
        source.splitlines()[4].index("add_one") + 1,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []


def test_resolve_reference_targets_from_python_function_scans_import_aliases(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_source = "def plus_one(value):\n    return value + 1\n"
    helper_path.write_text(helper_source, encoding="utf-8")
    (questions_dir / "module_alias.yml").write_text(
        "imports:\n  - docassemble.demo.helpers as helper_utils\n---\ncode: |\n  value = helper_utils.plus_one(4)\n",
        encoding="utf-8",
    )
    (questions_dir / "symbol_alias.yml").write_text(
        "imports:\n  - from docassemble.demo.helpers import plus_one as add_one\n---\ncode: |\n  value = add_one(5)\n",
        encoding="utf-8",
    )

    targets = resolve_reference_targets(
        helper_source,
        0,
        helper_source.splitlines()[0].index("plus_one") + 1,
        uri_or_path=helper_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []
    assert targets == []
    assert targets == []
    assert targets == []
    assert targets == []


def test_resolve_definition_targets_for_imported_class_alias_points_to_python_method(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    helper_path = package_dir / "math_helpers.py"
    helper_path.write_text(
        "class MathHelper:\n    @staticmethod\n    def bump(value):\n        return value + 1\n",
        encoding="utf-8",
    )
    source_path = questions_dir / "main.yml"
    source = (
        "imports:\n"
        "  - from docassemble.demo.math_helpers import MathHelper as Helper\n"
        "---\n"
        "code: |\n"
        "  result = Helper.bump(3)\n"
    )

    targets = resolve_definition_targets(
        source,
        4,
        source.splitlines()[4].index("bump") + 1,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []


def test_resolve_reference_targets_from_python_method_scans_imported_class_alias(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "math_helpers.py"
    helper_source = "class MathHelper:\n    @staticmethod\n    def bump(value):\n        return value + 1\n"
    helper_path.write_text(helper_source, encoding="utf-8")
    alias_path = questions_dir / "class_alias.yml"
    alias_path.write_text(
        "imports:\n  - from docassemble.demo.math_helpers import MathHelper as Helper\n---\ncode: |\n  value = Helper.bump(4)\n",
        encoding="utf-8",
    )

    targets = resolve_reference_targets(
        helper_source,
        2,
        helper_source.splitlines()[2].index("bump") + 1,
        uri_or_path=helper_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []
    assert targets == []
    assert targets == []
    assert targets == []


def test_resolve_definition_targets_for_child_yaml_uses_parent_import_bindings(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "def plus_one(value):\n    return value + 1\n", encoding="utf-8"
    )
    (questions_dir / "main_include.yml").write_text(
        "imports:\n  - docassemble.demo.helpers\ninclude:\n  - child.yml\n",
        encoding="utf-8",
    )
    child_path = questions_dir / "child.yml"
    child_source = "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  result = helpers.plus_one(3)\n"
    child_path.write_text(child_source, encoding="utf-8")

    targets = resolve_definition_targets(
        child_source,
        1,
        child_source.splitlines()[4].index("plus_one") + 1,
        uri_or_path=child_path,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("helpers.py", 0)
    ]


def test_resolve_reference_targets_from_python_function_reaches_child_through_parent_import_bindings(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_source = "def plus_one(value):\n    return value + 1\n"
    helper_path.write_text(helper_source, encoding="utf-8")
    (questions_dir / "main_include.yml").write_text(
        "imports:\n  - docassemble.demo.helpers\ninclude:\n  - child.yml\n",
        encoding="utf-8",
    )
    (questions_dir / "child.yml").write_text(
        "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  result = helpers.plus_one(3)\n",
        encoding="utf-8",
    )

    targets = resolve_reference_targets(
        helper_source,
        0,
        helper_source.splitlines()[0].index("plus_one") + 1,
        uri_or_path=helper_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []
    assert targets == []
    assert targets == []
    assert targets == []


def test_resolve_definition_targets_for_modules_symbol_follows_include_bindings(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "def plus_one(value):\n    return value + 1\n", encoding="utf-8"
    )
    (questions_dir / "library.yml").write_text(
        "modules:\n  - .helpers\n", encoding="utf-8"
    )
    source_path = questions_dir / "main.yml"
    source = "modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n"

    targets = resolve_definition_targets(
        source,
        4,
        source.splitlines()[4].index("plus_one") + 1,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("helpers.py", 0)
    ]


def test_resolve_reference_targets_from_python_function_follows_include_bindings(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    helper_path = package_dir / "helpers.py"
    helper_source = "def plus_one(value):\n    return value + 1\n"
    helper_path.write_text(helper_source, encoding="utf-8")
    (questions_dir / "library.yml").write_text(
        "modules:\n  - .helpers\n", encoding="utf-8"
    )
    main_path = questions_dir / "main.yml"
    main_path.write_text(
        "modules:\n  - .helpers\n---\nquestion: |\n  Result: ${ plus_one(3) }\n",
        encoding="utf-8",
    )

    targets = resolve_reference_targets(
        helper_source,
        0,
        helper_source.splitlines()[0].index("plus_one") + 1,
        uri_or_path=helper_path,
        workspace_paths=[tmp_path],
    )

    assert targets == []
    assert targets == []
    assert targets == []
    assert targets == []


def test_resolve_definition_targets_for_import_symbol_follows_include_bindings(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions_dir = package_dir / "data" / "questions"
    questions_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    helper_path = package_dir / "helpers.py"
    helper_path.write_text(
        "def plus_one(value):\n    return value + 1\n", encoding="utf-8"
    )
    (questions_dir / "library.yml").write_text(
        "imports:\n  - docassemble.demo.helpers\n", encoding="utf-8"
    )
    source_path = questions_dir / "main.yml"
    source = "imports:\n  - docassemble.demo.helpers\n---\ncode: |\n  result = helpers.plus_one(3)\n"

    targets = resolve_definition_targets(
        source,
        4,
        source.splitlines()[4].index("plus_one") + 1,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("helpers.py", 0)
    ]


# ---------------------------------------------------------------------------
# Field-variable semantics (packet 02)
# ---------------------------------------------------------------------------


def test_resolve_definition_targets_for_field_key_declaration_returns_self(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: What is it?\nfields:\n  - field: user_name\n    datatype: text\n"
    )
    # cursor on "user_name" in "  - field: user_name" (line 2)
    line = 2
    char = source.splitlines()[line].index("user_name") + 3

    targets = resolve_definition_targets(source, line, char, uri_or_path=source_path)

    assert len(targets) == 1
    assert targets[0].path == source_path
    assert targets[0].line == line


def test_resolve_definition_targets_for_label_style_field_declaration_returns_self(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = "question: What is it?\nfields:\n  - Full name: user_name\n"
    line = 2
    char = source.splitlines()[line].index("user_name") + 2

    targets = resolve_definition_targets(source, line, char, uri_or_path=source_path)

    assert len(targets) == 1
    assert targets[0].path == source_path
    assert targets[0].line == line


def test_resolve_definition_targets_for_show_if_variable_points_to_field_declaration(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: What is it?\n"
        "fields:\n"
        "  - Full name: user_name\n"
        "  - field: show_details\n"
        "    datatype: yesno\n"
        "  - field: extra_info\n"
        "    show if:\n"
        "      variable: show_details\n"
        "      is: True\n"
    )
    # cursor on "show_details" in "      variable: show_details" (line 7)
    line = 7
    char = source.splitlines()[line].index("show_details") + 3

    targets = resolve_definition_targets(source, line, char, uri_or_path=source_path)

    assert len(targets) == 1
    assert targets[0].path == source_path
    assert targets[0].line == 3  # "  - field: show_details"


def test_resolve_definition_targets_for_hide_if_variable_points_to_field_declaration(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: Details\n"
        "fields:\n"
        "  - field: is_adult\n"
        "    datatype: yesno\n"
        "  - field: guardian_name\n"
        "    hide if:\n"
        "      variable: is_adult\n"
        "      is: True\n"
    )
    line = 6
    char = source.splitlines()[line].index("is_adult") + 3

    targets = resolve_definition_targets(source, line, char, uri_or_path=source_path)

    assert len(targets) == 1
    assert targets[0].path == source_path
    assert targets[0].line == 2  # "  - field: is_adult"


def test_resolve_definition_targets_for_field_var_returns_empty_for_unknown_variable(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: Details\n"
        "fields:\n"
        "  - field: guardian_name\n"
        "    show if:\n"
        "      variable: undeclared_var\n"
        "      is: True\n"
    )
    line = 4
    char = source.splitlines()[line].index("undeclared_var") + 3

    targets = resolve_definition_targets(source, line, char, uri_or_path=source_path)

    assert targets == []


def test_resolve_reference_targets_for_field_declaration_finds_show_if_uses(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: What is it?\n"
        "fields:\n"
        "  - field: show_details\n"
        "    datatype: yesno\n"
        "  - field: extra_info\n"
        "    show if:\n"
        "      variable: show_details\n"
        "      is: True\n"
        "  - field: more_info\n"
        "    hide if:\n"
        "      variable: show_details\n"
        "      is: False\n"
    )
    # cursor on declaration: "  - field: show_details" (line 2)
    line = 2
    char = source.splitlines()[line].index("show_details") + 3

    targets = resolve_reference_targets(source, line, char, uri_or_path=source_path)

    lines = [t.line for t in targets]
    assert 2 in lines  # declaration itself
    assert 6 in lines  # show if variable reference
    assert 10 in lines  # hide if variable reference


def test_resolve_reference_targets_for_field_var_excludes_declaration_when_requested(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: What is it?\n"
        "fields:\n"
        "  - field: flag\n"
        "    datatype: yesno\n"
        "  - field: detail\n"
        "    show if:\n"
        "      variable: flag\n"
        "      is: True\n"
    )
    line = 2
    char = source.splitlines()[line].index("flag") + 2

    targets = resolve_reference_targets(
        source, line, char, uri_or_path=source_path, include_declaration=False
    )

    lines = [t.line for t in targets]
    assert 2 not in lines  # declaration excluded
    assert 6 in lines  # show if reference included


def test_resolve_reference_targets_for_show_if_variable_finds_declaration(
    tmp_path,
) -> None:
    source_path = tmp_path / "interview.yml"
    source = (
        "question: What is it?\n"
        "fields:\n"
        "  - field: flag\n"
        "    datatype: yesno\n"
        "  - field: detail\n"
        "    show if:\n"
        "      variable: flag\n"
        "      is: True\n"
    )
    # cursor on "flag" in "      variable: flag" (line 6)
    line = 6
    char = source.splitlines()[line].index("flag") + 2

    targets = resolve_reference_targets(source, line, char, uri_or_path=source_path)

    lines = [t.line for t in targets]
    assert 2 in lines  # declaration
    assert 6 in lines  # reference itself


def test_resolve_definition_targets_for_field_var_scans_workspace_files(
    tmp_path,
) -> None:
    source_path = tmp_path / "main.yml"
    source = (
        "question: Details\n"
        "fields:\n"
        "  - field: guardian_name\n"
        "    show if:\n"
        "      variable: show_guardian\n"
        "      is: True\n"
    )
    # declaration lives in a separate file
    other_path = tmp_path / "other.yml"
    other_path.write_text(
        "question: Show it?\nfields:\n  - field: show_guardian\n    datatype: yesno\n",
        encoding="utf-8",
    )

    targets = resolve_definition_targets(
        source,
        4,
        source.splitlines()[4].index("show_guardian") + 3,
        uri_or_path=source_path,
        workspace_paths=[tmp_path],
    )

    assert len(targets) == 1
    assert targets[0].path == other_path.resolve()
    assert targets[0].line == 2


def test_resolve_reference_targets_for_field_var_scans_workspace_files(
    tmp_path,
) -> None:
    decl_path = tmp_path / "fields.yml"
    decl_source = "question: Name?\nfields:\n  - field: user_name\n    datatype: text\n"
    decl_path.write_text(decl_source, encoding="utf-8")
    ref_path = tmp_path / "conditional.yml"
    ref_path.write_text(
        "question: More?\nfields:\n  - field: extra\n    show if:\n      variable: user_name\n      is: x\n",
        encoding="utf-8",
    )

    # find-references from declaration in fields.yml
    targets = resolve_reference_targets(
        decl_source,
        2,
        decl_source.splitlines()[2].index("user_name") + 3,
        uri_or_path=decl_path,
        workspace_paths=[tmp_path],
    )

    file_lines = [(t.path.name, t.line) for t in targets]
    assert ("fields.yml", 2) in file_lines  # declaration
    assert ("conditional.yml", 4) in file_lines  # cross-file reference


def test_resolve_definition_targets_for_action_finds_event_in_workspace(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    main = package_dir / "main.yml"
    main.write_text(
        "include:\n  - library.yml\naction buttons:\n  - label: Run\n    action: library_event\n",
        encoding="utf-8",
    )
    library = package_dir / "library.yml"
    library.write_text(
        "event: library_event\nquestion: From library\n", encoding="utf-8"
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.docassemble-lsp]\nyaml_path = 'docassemble'\n", encoding="utf-8"
    )

    targets = resolve_definition_targets(
        main.read_text(encoding="utf-8"),
        4,
        len("    action: library_event") - 2,
        uri_or_path=main,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("library.yml", 0)
    ]


def test_resolve_definition_targets_can_use_workspace_index(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    main = package_dir / "main.yml"
    main_source = "action buttons:\n  - label: Run\n    action: library_event\n"
    main.write_text(main_source, encoding="utf-8")
    library = package_dir / "library.yml"
    library.write_text(
        "event: library_event\nquestion: From library\n", encoding="utf-8"
    )

    targets = resolve_definition_targets(
        main_source,
        2,
        len("    action: library_event") - 2,
        uri_or_path=main,
        workspace_index=_workspace_index_for_tests(tmp_path),
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("library.yml", 0)
    ]


def test_resolve_definition_targets_for_usedefs_finds_def_in_workspace(
    tmp_path,
) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    main = package_dir / "main.yml"
    main.write_text(
        "include:\n  - library.yml\nusedefs:\n  - shared_definition\n", encoding="utf-8"
    )
    library = package_dir / "library.yml"
    library.write_text(
        "def: shared_definition\ncode: |\n  return 'Shared'\n", encoding="utf-8"
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.docassemble-lsp]\nyaml_path = 'docassemble'\n", encoding="utf-8"
    )

    targets = resolve_definition_targets(
        main.read_text(encoding="utf-8"),
        3,
        len("  - shared_definition") - 2,
        uri_or_path=main,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("library.yml", 0)
    ]


def test_resolve_reference_targets_for_event_scans_workspace(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    main = package_dir / "main.yml"
    main.write_text(
        "include:\n  - library.yml\naction buttons:\n  - label: Run\n    action: library_event\n",
        encoding="utf-8",
    )
    library = package_dir / "library.yml"
    library.write_text(
        "event: library_event\nquestion: From library\n", encoding="utf-8"
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.docassemble-lsp]\nyaml_path = 'docassemble'\n", encoding="utf-8"
    )

    targets = resolve_reference_targets(
        library.read_text(encoding="utf-8"),
        0,
        len("event: library_event") - 2,
        uri_or_path=library,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("library.yml", 0),
        ("main.yml", 4),
    ]


def test_resolve_reference_targets_for_def_scans_workspace(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    main = package_dir / "main.yml"
    main.write_text(
        "include:\n  - library.yml\nusedefs:\n  - shared_definition\n", encoding="utf-8"
    )
    library = package_dir / "library.yml"
    library.write_text(
        "def: shared_definition\ncode: |\n  return 'Shared'\n", encoding="utf-8"
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.docassemble-lsp]\nyaml_path = 'docassemble'\n", encoding="utf-8"
    )

    targets = resolve_reference_targets(
        library.read_text(encoding="utf-8"),
        0,
        len("def: shared_definition") - 2,
        uri_or_path=library,
        workspace_paths=[tmp_path],
    )

    assert [(target.path.name, target.line) for target in targets] == [
        ("library.yml", 0),
        ("main.yml", 3),
    ]


def test_resolve_workspace_symbol_targets_include_event_and_def_names(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    events_path = package_dir / "events.yml"
    events_path.write_text(
        "event: library_event\nquestion: From library\n", encoding="utf-8"
    )
    defs_path = package_dir / "defs.yml"
    defs_path.write_text(
        "def: explainer_text\ncode: |\n  return 'hello'\n", encoding="utf-8"
    )

    targets = resolve_workspace_symbol_targets("", workspace_paths=[tmp_path])

    assert [
        (target.name, target.kind, target.path.name, target.line) for target in targets
    ] == [
        ("explainer_text", "def", "defs.yml", 0),
        ("library_event", "event", "events.yml", 0),
    ]


def test_resolve_workspace_symbol_targets_filter_by_query(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    (package_dir / "events.yml").write_text(
        "event: library_event\nquestion: From library\n", encoding="utf-8"
    )
    (package_dir / "defs.yml").write_text(
        "def: explainer_text\ncode: |\n  return 'hello'\n", encoding="utf-8"
    )

    targets = resolve_workspace_symbol_targets("event", workspace_paths=[tmp_path])

    assert [(target.name, target.kind) for target in targets] == [
        ("library_event", "event")
    ]


def test_resolve_workspace_symbol_targets_can_use_workspace_index(tmp_path) -> None:
    package_dir = tmp_path / "docassemble" / "demo" / "data" / "questions"
    package_dir.mkdir(parents=True)
    (package_dir / "events.yml").write_text(
        "event: library_event\nquestion: From library\n", encoding="utf-8"
    )

    targets = resolve_workspace_symbol_targets(
        "event", workspace_index=_workspace_index_for_tests(tmp_path)
    )

    assert [(target.name, target.kind) for target in targets] == [
        ("library_event", "event")
    ]
