from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletionCandidate:
    label: str
    insert_text: str
    # detail is always None — type info is surfaced in the
    # documentation/hover header instead.
    detail: str | None = None
    documentation: str | None = None
    filter_text: str | None = None
    is_value: bool = False
    is_snippet: bool = False
    uses_snippet_text: bool = False
    display_kind: str | None = None
    trigger_suggest: bool = False


@dataclass(frozen=True, slots=True)
class HoverInfo:
    contents: str
