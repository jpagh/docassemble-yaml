from __future__ import annotations

from dataclasses import dataclass

# Semantic tokens are intentionally disabled for text-content markup.
#
# The TextMate grammar already provides rich, multi-color highlighting
# inside Mako expressions (${...}) and bracket commands ([FILE ...],
# [FIELD ...], etc.) — function names, strings, parentheses, and
# delimiters each get distinct colors.
#
# When the LSP emits a single "macro" semantic token for the entire
# span (e.g. the full `${question(...)}` expression or `[FILE x.jpg]`),
# VS Code's semantic-token layer overrides the TextMate grammar's
# fine-grained coloring, reducing everything to one color.
#
# Rejected approaches that would NOT fix this:
# - Emitting boundary-only tokens: semantic tokens apply per span,
#   not per character-class; there is no way to "punch through" to
#   the TextMate grammar for sub-spans inside a token.
# - Switching to a different token type: any non-empty semantic token
#   covering the span would still override the TextMate grammar.
#
# The block-scalar tracking infrastructure (used to detect Python code
# blocks) is kept so future work can add semantic tokens for
# non-text-content constructs (e.g. YAML key classification) without
# reintroducing this conflict.

SEMANTIC_TOKEN_TYPES: list[str] = []
SEMANTIC_TOKEN_MODIFIERS: list[str] = []


@dataclass(frozen=True, slots=True)
class SemanticTokenSpan:
    line: int
    start_character: int
    length: int
    token_type: int


def build_semantic_token_spans(source: str) -> list[SemanticTokenSpan]:  # noqa: ARG001
    return []


def encode_semantic_tokens(spans: list[SemanticTokenSpan]) -> list[int]:
    data: list[int] = []
    prev_line = 0
    prev_start = 0
    for span in spans:
        delta_line = span.line - prev_line
        delta_start = span.start_character if delta_line > 0 else span.start_character - prev_start
        data.extend([delta_line, delta_start, span.length, span.token_type, 0])
        prev_line = span.line
        prev_start = span.start_character
    return data
