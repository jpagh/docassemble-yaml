from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from docassemble_lsp.core.accessibility import AccessibilityLintOptions


@dataclass(frozen=True)
class RuntimeOptions:
    accessibility_error_on_widgets: frozenset[str] = field(default_factory=frozenset)
    enabled_conventions: frozenset[str] = field(default_factory=frozenset)
    ignore_codes: frozenset[str] = field(default_factory=frozenset)
    show_warnings: bool = True
    indent: int = 2

    def accessibility_options(self) -> AccessibilityLintOptions:
        return AccessibilityLintOptions(
            error_on_widgets=self.accessibility_error_on_widgets
        )

    def convention_enabled(self, code: str) -> bool:
        normalized = code.strip().upper()
        return (
            "ALL" in self.enabled_conventions or normalized in self.enabled_conventions
        )

    def allows_code(self, code: str | None) -> bool:
        if code is None:
            return True
        normalized = code.strip().upper()
        if normalized in self.ignore_codes:
            return False
        if normalized.startswith("C"):
            return self.convention_enabled(normalized)
        if normalized.startswith("W") and not self.show_warnings:
            return False
        return True


def parse_ignore_codes(raw_codes: str) -> frozenset[str]:
    return frozenset(
        code.strip().upper() for code in raw_codes.split(",") if code.strip()
    )


def message_severity(code: str | None) -> Literal["error", "warning", "convention"]:
    if code is None:
        return "error"
    if code.startswith("E"):
        return "error"
    if code.startswith("W"):
        return "warning"
    if code.startswith("C"):
        return "convention"
    return "error"


class YAMLError:
    def __init__(
        self,
        *,
        err_str: str,
        line_number: int,
        file_name: str,
        experimental: bool = True,
        code: str | None = None,
    ):
        self.err_str = err_str
        self.line_number = line_number
        self.file_name = file_name
        self.experimental = experimental
        self.code = code

    @property
    def severity(self) -> Literal["error", "warning", "convention"]:
        if self.code is not None:
            return message_severity(self.code)
        lowered = self.err_str.lower()
        if lowered.startswith("info:"):
            return "convention"
        if lowered.startswith("warning:"):
            return "warning"
        return "error"

    def __str__(self):
        return self.format()

    def format(self, *, show_experimental: bool = True) -> str:
        code_prefix = f"[{self.code}] " if self.code else ""
        if not self.experimental and show_experimental:
            return f"REAL ERROR: {code_prefix}At {self.file_name}:{self.line_number}: {self.err_str}"
        return f"{code_prefix}At {self.file_name}:{self.line_number}: {self.err_str}"
