from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import jinja2

from docassemble_lsp.core.messages import MessageCode

_JINJA_SYNTAX_RE = re.compile(r"({{.*?}}|{%-?.*?-?%}|{#.*?#})", re.DOTALL)


@dataclass(frozen=True, slots=True)
class JinjaError:
    code: str
    message: str
    line_number: int = 1


def contains_jinja_syntax(content: str) -> bool:
    return _JINJA_SYNTAX_RE.search(content) is not None


def _first_jinja_line(content: str) -> int:
    for index, line in enumerate(content.splitlines(), start=1):
        if contains_jinja_syntax(line):
            return index
    return 1


def has_jinja_header(content: str) -> bool:
    first_line = content.split("\n", 1)[0].rstrip()
    return first_line == "# use jinja"


class _SilentUndefined(jinja2.Undefined):
    def __str__(self) -> str:
        return ""

    def __iter__(self):
        return iter([])

    def __len__(self) -> int:
        return 0

    def __getattr__(self, name: str) -> "_SilentUndefined":
        if name.startswith("_"):
            raise AttributeError(name)
        return _SilentUndefined()

    def __getitem__(self, key: object) -> "_SilentUndefined":  # type: ignore[override]
        return _SilentUndefined()

    def __call__(self, *args: object, **kwargs: object) -> "_SilentUndefined":  # type: ignore[override]
        return _SilentUndefined()


def preprocess_jinja(content: str, *, input_file: str | None = None) -> tuple[str, list[JinjaError]]:
    loader = None
    if input_file and input_file != "<string input>":
        parent = Path(input_file).expanduser().resolve().parent
        loader = jinja2.FileSystemLoader(str(parent))

    env = jinja2.Environment(
        loader=loader,
        undefined=_SilentUndefined,
        keep_trailing_newline=True,
    )

    try:
        template = env.from_string(content)
    except jinja2.exceptions.TemplateSyntaxError as ex:
        return content, [
            JinjaError(
                code=MessageCode.JINJA2_SYNTAX_ERROR,
                message=f"Jinja2 syntax error at line {ex.lineno}: {ex.message}",
                line_number=ex.lineno or 1,
            )
        ]

    try:
        rendered = template.render()
    except jinja2.exceptions.TemplateError as ex:
        line_number = getattr(ex, "lineno", None) or _first_jinja_line(content)
        return content, [
            JinjaError(
                code=MessageCode.JINJA2_TEMPLATE_ERROR,
                message=f"Jinja2 template error: {ex}",
                line_number=line_number,
            )
        ]

    return rendered, []
