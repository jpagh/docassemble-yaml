from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from docassemble_lsp.core.validation import find_errors, find_errors_from_string
from docassemble_lsp.core.validation_config import RuntimeOptions, YAMLError
from docassemble_lsp.core.workspace import WorkspaceIndex

Severity = Literal["error", "warning", "convention"]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    line: int
    message: str
    severity: Severity
    code: str | None = None
    source: str = "docassemble-lsp"


def _from_yaml_error(error: YAMLError) -> Diagnostic:
    return Diagnostic(
        line=error.line_number,
        message=error.err_str,
        severity=error.severity,
        code=error.code,
    )


def analyze_text(
    text: str,
    *,
    path: str = "<memory>",
    runtime_options: RuntimeOptions | None = None,
    workspace_index: WorkspaceIndex | None = None,
) -> list[Diagnostic]:
    return [
        _from_yaml_error(error)
        for error in find_errors_from_string(
            text,
            input_file=path,
            runtime_options=runtime_options,
            workspace_index=workspace_index,
        )
    ]


def analyze_path(
    path: str | Path,
    *,
    runtime_options: RuntimeOptions | None = None,
) -> list[Diagnostic]:
    return [
        _from_yaml_error(error)
        for error in find_errors(
            str(path),
            runtime_options=runtime_options,
        )
    ]


def diagnostic_to_dict(diagnostic: Diagnostic) -> dict[str, object]:
    return asdict(diagnostic)
