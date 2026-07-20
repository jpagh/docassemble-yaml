from __future__ import annotations

from pathlib import Path
from typing import Any

from docassemble_lsp.core import build_workspace_index
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.lsp.server import (
    build_definition_locations as core_build_definition_locations,
)
from docassemble_lsp.lsp.server import (
    build_reference_locations as core_build_reference_locations,
)

FIXTURE_PACKAGE_ROOT = (
    Path(__file__).resolve().parent / "fixtures" / "reference_package"
)
FIXTURE_QUESTIONS_ROOT = (
    FIXTURE_PACKAGE_ROOT / "docassemble" / "demo" / "data" / "questions"
)
DEMO_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "demo_package"
DEMO_QUESTIONS_ROOT = DEMO_FIXTURE_ROOT / "docassemble" / "demo" / "data" / "questions"
DEMO_WORKFLOW_PATH = DEMO_FIXTURE_ROOT / "docassemble" / "demo" / "workflow.py"


def _workspace_index_from_test_args(
    source: str,
    uri: str,
    workspace_paths: list[str] | None,
    workspace_index: WorkspaceIndex | None,
) -> WorkspaceIndex:
    if workspace_index is not None:
        return workspace_index
    current_path = Path(uri.removeprefix("file://"))
    return build_workspace_index(
        [Path(path) for path in workspace_paths] if workspace_paths else [],
        current_path=current_path,
        current_source=source,
    )


def build_definition_locations(
    uri: str, source: str, line: int, character: int, **kwargs: Any
) -> Any:
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    return core_build_definition_locations(
        uri,
        source,
        line,
        character,
        workspace_index=_workspace_index_from_test_args(
            source, uri, workspace_paths, workspace_index
        ),
        **kwargs,
    )


def build_reference_locations(
    uri: str, source: str, line: int, character: int, **kwargs: Any
) -> Any:
    workspace_paths = kwargs.pop("workspace_paths", None)
    workspace_index = kwargs.pop("workspace_index", None)
    return core_build_reference_locations(
        uri,
        source,
        line,
        character,
        workspace_index=_workspace_index_from_test_args(
            source, uri, workspace_paths, workspace_index
        ),
        **kwargs,
    )


def _line_index(source: str, needle: str) -> int:
    return next(
        index for index, line in enumerate(source.splitlines()) if needle in line
    )


def _nth_line_index(source: str, needle: str, occurrence: int) -> int:
    matches = [
        index for index, line in enumerate(source.splitlines()) if needle in line
    ]
    return matches[occurrence - 1]


def test_reference_locations_fixture_package_resolves_yaml_targets_from_reference_values() -> (
    None
):
    source_path = FIXTURE_QUESTIONS_ROOT / "main.yml"
    source = source_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    target_line = _line_index(source, "shared.yml")
    locations = build_reference_locations(
        source_path.as_uri(),
        source,
        target_line,
        source_lines[target_line].index("shared.yml") + 1,
        workspace_paths=[str(FIXTURE_PACKAGE_ROOT)],
    )

    secondary_source = (FIXTURE_QUESTIONS_ROOT / "secondary.yml").read_text(
        encoding="utf-8"
    )
    cross_ref_source = (FIXTURE_QUESTIONS_ROOT / "cross_ref.yml").read_text(
        encoding="utf-8"
    )

    assert [
        (Path(location.uri.removeprefix("file://")).name, location.range.start.line)
        for location in locations
    ] == [
        ("main.yml", _line_index(source, "shared.yml")),
        ("main.yml", _nth_line_index(source, "shared.yml", 2)),
        ("cross_ref.yml", _line_index(cross_ref_source, "shared.yml")),
        ("cross_ref.yml", _nth_line_index(cross_ref_source, "shared.yml", 2)),
        ("secondary.yml", _line_index(secondary_source, "shared.yml")),
        ("shared.yml", 0),
    ]


def test_reference_locations_fixture_package_resolves_asset_targets() -> None:
    docx_target = FIXTURE_QUESTIONS_ROOT / "templates" / "letter.docx"
    main_source = (FIXTURE_QUESTIONS_ROOT / "main.yml").read_text(encoding="utf-8")
    secondary_source = (FIXTURE_QUESTIONS_ROOT / "secondary.yml").read_text(
        encoding="utf-8"
    )
    cross_ref_source = (FIXTURE_QUESTIONS_ROOT / "cross_ref.yml").read_text(
        encoding="utf-8"
    )
    docx_locations = build_reference_locations(
        docx_target.as_uri(),
        docx_target.read_text(encoding="utf-8"),
        0,
        0,
        workspace_paths=[str(FIXTURE_PACKAGE_ROOT)],
    )
    assert [
        (Path(location.uri.removeprefix("file://")).name, location.range.start.line)
        for location in docx_locations
    ] == [
        ("cross_ref.yml", _line_index(cross_ref_source, "letter.docx")),
        ("main.yml", _line_index(main_source, "templates/letter.docx")),
        ("secondary.yml", _line_index(secondary_source, "templates/letter.docx")),
        ("letter.docx", 0),
    ]

    pdf_target = FIXTURE_QUESTIONS_ROOT / "forms" / "notice.pdf"
    pdf_locations = build_reference_locations(
        pdf_target.as_uri(),
        pdf_target.read_text(encoding="utf-8"),
        0,
        0,
        workspace_paths=[str(FIXTURE_PACKAGE_ROOT)],
    )
    assert [
        (Path(location.uri.removeprefix("file://")).name, location.range.start.line)
        for location in pdf_locations
    ] == [
        ("main.yml", _line_index(main_source, "forms/notice.pdf")),
        ("notice.pdf", 0),
    ]

    markdown_target = FIXTURE_QUESTIONS_ROOT / "content" / "disclaimer.md"
    markdown_locations = build_reference_locations(
        markdown_target.as_uri(),
        markdown_target.read_text(encoding="utf-8"),
        0,
        0,
        workspace_paths=[str(FIXTURE_PACKAGE_ROOT)],
    )
    assert [
        (Path(location.uri.removeprefix("file://")).name, location.range.start.line)
        for location in markdown_locations
    ] == [
        ("cross_ref.yml", _line_index(cross_ref_source, "disclaimer.md")),
        ("main.yml", _line_index(main_source, "content/disclaimer.md")),
        ("secondary.yml", _line_index(secondary_source, "content/disclaimer.md")),
        ("disclaimer.md", 0),
    ]

    source_path = FIXTURE_QUESTIONS_ROOT / "main.yml"
    source = source_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    target_line = _line_index(source, "objects/object-map.yml")
    object_map_locations = build_reference_locations(
        source_path.as_uri(),
        source,
        target_line,
        source_lines[target_line].index("objects/object-map.yml") + 1,
        workspace_paths=[str(FIXTURE_PACKAGE_ROOT)],
    )
    assert [
        (Path(location.uri.removeprefix("file://")).name, location.range.start.line)
        for location in object_map_locations
    ] == [
        ("main.yml", _line_index(source, "objects/object-map.yml")),
        ("secondary.yml", _line_index(secondary_source, "objects/object-map.yml")),
        ("object-map.yml", 0),
    ]


def test_definition_locations_fixture_package_qualified_include_resolves_to_shared_yml() -> (
    None
):
    cross_ref_path = FIXTURE_QUESTIONS_ROOT / "cross_ref.yml"
    source = cross_ref_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    pkg_ref = "docassemble.demo:data/questions/shared.yml"
    target_line = _line_index(source, pkg_ref)

    locations = build_definition_locations(
        cross_ref_path.as_uri(),
        source,
        target_line,
        source_lines[target_line].index(pkg_ref) + 5,
        workspace_paths=[str(FIXTURE_PACKAGE_ROOT)],
    )

    assert len(locations) == 1
    assert Path(locations[0].target_uri.removeprefix("file://")).name == "shared.yml"
    assert locations[0].target_range.start.line == 0


def test_definition_locations_fixture_package_qualified_template_file_resolves_to_docx() -> (
    None
):
    cross_ref_path = FIXTURE_QUESTIONS_ROOT / "cross_ref.yml"
    source = cross_ref_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    pkg_ref = "docassemble.demo:data/questions/templates/letter.docx"
    target_line = _line_index(source, pkg_ref)

    locations = build_definition_locations(
        cross_ref_path.as_uri(),
        source,
        target_line,
        source_lines[target_line].index(pkg_ref) + 5,
        workspace_paths=[str(FIXTURE_PACKAGE_ROOT)],
    )

    assert len(locations) == 1
    assert Path(locations[0].target_uri.removeprefix("file://")).name == "letter.docx"


def test_definition_locations_demo_package_resolves_modules_symbol() -> None:
    source_path = DEMO_QUESTIONS_ROOT / "main.yml"
    source = source_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    target_line = next(
        index for index, line in enumerate(source_lines) if "case_title(" in line
    )

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        target_line,
        source_lines[target_line].index("case_title") + 1,
        workspace_paths=[str(DEMO_FIXTURE_ROOT)],
    )

    assert [
        (
            Path(location.target_uri.removeprefix("file://")).name,
            location.target_range.start.line,
        )
        for location in locations
    ] == [
        ("workflow.py", 0),
    ]


def test_reference_locations_demo_package_resolves_method_across_include_stack() -> (
    None
):
    workflow_source = DEMO_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow_lines = workflow_source.splitlines()
    status_label_line = next(
        index for index, line in enumerate(workflow_lines) if "def status_label" in line
    )
    locations = build_reference_locations(
        DEMO_WORKFLOW_PATH.as_uri(),
        workflow_source,
        status_label_line,
        workflow_lines[status_label_line].index("status_label") + 1,
        workspace_paths=[str(DEMO_FIXTURE_ROOT)],
    )

    assert locations == []


def test_definition_locations_demo_package_resolves_child_include_python_binding() -> (
    None
):
    source_path = DEMO_QUESTIONS_ROOT / "x_events.yml"
    source = source_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    target_line = next(
        index
        for index, line in enumerate(source_lines)
        if "workflow.case_title" in line
    )

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        target_line,
        source_lines[target_line].index("case_title") + 1,
        workspace_paths=[str(DEMO_FIXTURE_ROOT)],
    )

    assert [
        (
            Path(location.target_uri.removeprefix("file://")).name,
            location.target_range.start.line,
        )
        for location in locations
    ] == [
        ("workflow.py", 0),
    ]


def test_definition_locations_demo_package_resolves_url_action_event() -> None:
    source_path = DEMO_QUESTIONS_ROOT / "main.yml"
    source = source_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    event_source = (DEMO_QUESTIONS_ROOT / "x_events.yml").read_text(encoding="utf-8")
    event_lines = event_source.splitlines()
    target_line = next(
        index
        for index, line in enumerate(source_lines)
        if 'url_action("workflow_reset")' in line
    )

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        target_line,
        source_lines[target_line].index("workflow_reset") + 1,
        workspace_paths=[str(DEMO_FIXTURE_ROOT)],
    )

    assert [
        (
            Path(location.target_uri.removeprefix("file://")).name,
            location.target_range.start.line,
        )
        for location in locations
    ] == [
        (
            "x_events.yml",
            next(
                index
                for index, line in enumerate(event_lines)
                if line.startswith("event: workflow_reset")
            ),
        ),
    ]


def test_definition_locations_demo_package_resolves_action_menu_item_event() -> None:
    source_path = DEMO_QUESTIONS_ROOT / "x_events.yml"
    source = source_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    event_line = next(
        index
        for index, line in enumerate(source_lines)
        if line.startswith("event: workflow_reset")
    )
    target_line = next(
        index
        for index, line in enumerate(source_lines)
        if '"workflow_reset"' in line and index < event_line
    )

    locations = build_definition_locations(
        source_path.as_uri(),
        source,
        target_line,
        source_lines[target_line].index("workflow_reset") + 1,
        workspace_paths=[str(DEMO_FIXTURE_ROOT)],
    )

    assert [
        (
            Path(location.target_uri.removeprefix("file://")).name,
            location.target_range.start.line,
        )
        for location in locations
    ] == [
        ("x_events.yml", event_line),
    ]


def test_reference_locations_demo_package_include_url_action_event_references() -> None:
    source_path = DEMO_QUESTIONS_ROOT / "x_events.yml"
    source = source_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    main_source = (DEMO_QUESTIONS_ROOT / "main.yml").read_text(encoding="utf-8")
    main_lines = main_source.splitlines()
    event_line = next(
        index
        for index, line in enumerate(source_lines)
        if line.startswith("event: workflow_reset")
    )
    helper_line = next(
        index
        for index, line in enumerate(source_lines)
        if '"workflow_reset"' in line and index < event_line
    )

    locations = build_reference_locations(
        source_path.as_uri(),
        source,
        event_line,
        source_lines[event_line].index("workflow_reset") + 1,
        workspace_paths=[str(DEMO_FIXTURE_ROOT)],
    )

    assert [
        (Path(location.uri.removeprefix("file://")).name, location.range.start.line)
        for location in locations
    ] == [
        ("x_events.yml", helper_line),
        ("x_events.yml", event_line),
        (
            "main.yml",
            next(
                index
                for index, line in enumerate(main_lines)
                if 'url_action("workflow_reset")' in line
            ),
        ),
        (
            "main.yml",
            next(
                index
                for index, line in enumerate(main_lines)
                if "action: workflow_reset" in line
            ),
        ),
    ]
