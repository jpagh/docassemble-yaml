from __future__ import annotations

import functools
import re
from collections.abc import Iterable, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jinja2
import jinja2.nodes
import jinja2.visitor

from docassemble_lsp.core.messages import MessageCode, format_message

_JINJA_SYNTAX_RE = re.compile(r"({{.*?}}|{%-?.*?-?%}|{#.*?#})", re.DOTALL)

#: Rendered where a Jinja include cannot be resolved. Validation skips the
#: documents that contain it because the included content is unknown.
_UNRESOLVED_INCLUDE_SENTINEL = "__docassemble_lsp_unresolved_include__"

#: Name of the internal function wrapped around template expressions of
#: ``{% include %}`` tags so each include site can resolve itself at render
#: time and report failures against its own line.
_INCLUDE_RESOLVER_NAME = "__docassemble_lsp_resolve_include__"


@dataclass(frozen=True, slots=True)
class JinjaIssue:
    """A render error or warning carrying its code, message, and line."""

    code: str
    message: str
    line_number: int


@dataclass(frozen=True, slots=True)
class JinjaRenderResult:
    text: str
    errors: tuple[JinjaIssue, ...] = ()
    warnings: tuple[JinjaIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class _IncludeSite:
    line_number: int
    display_name: str
    ignore_missing: bool
    containing_template: str | None


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


def contains_unresolved_include(content: str) -> bool:
    """Return True when rendering left an unresolved include in ``content``."""
    return _UNRESOLVED_INCLUDE_SENTINEL in content


class _SilentUndefined(jinja2.Undefined):
    def __str__(self) -> str:
        return ""

    def __iter__(self):
        return iter([])

    def __len__(self) -> int:
        return 0

    def __getattr__(self, name: str) -> _SilentUndefined:
        if name.startswith("_"):
            raise AttributeError(name)
        return _SilentUndefined()

    def __getitem__(self, key: object) -> _SilentUndefined:  # type: ignore[override]
        return _SilentUndefined()

    def __call__(self, *args: object, **kwargs: object) -> _SilentUndefined:
        return _SilentUndefined()


def _include_candidates(node: jinja2.nodes.Include) -> tuple[str, ...] | None:
    """Return the statically named include candidates, or None when dynamic."""
    template = node.template
    if isinstance(template, jinja2.nodes.Const):
        if isinstance(template.value, str):
            return (template.value,)
        return None
    if isinstance(template, (jinja2.nodes.List, jinja2.nodes.Tuple)):
        candidates: list[str] = []
        for item in template.items:
            if not isinstance(item, jinja2.nodes.Const) or not isinstance(
                item.value, str
            ):
                return None
            candidates.append(item.value)
        return tuple(candidates)
    return None


def _dynamic_include_name(template: jinja2.nodes.Node) -> str:
    if isinstance(template, jinja2.nodes.Name):
        return template.name
    if isinstance(template, jinja2.nodes.Getattr):
        parts: list[str] = []
        current: jinja2.nodes.Node = template
        while isinstance(current, jinja2.nodes.Getattr):
            parts.append(current.attr)
            current = current.node
        if isinstance(current, jinja2.nodes.Name):
            parts.append(current.name)
            return ".".join(reversed(parts))
    return "<expression>"


def _include_display_name(node: jinja2.nodes.Include) -> str:
    candidates = _include_candidates(node)
    if candidates is not None:
        return ", ".join(repr(candidate) for candidate in candidates)
    return _dynamic_include_name(node.template)


def _iter_include_names(value: object) -> Iterable[str]:
    """Yield the template names an evaluated include expression refers to."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str):
                yield item


class _IncludeResilientEnvironment(jinja2.Environment):
    """Environment that turns missing Jinja templates into warnings.

    Jinja raises ``TemplateNotFound`` when an included template does not
    exist, which aborts validation of the whole file. Every ``{% include %}``
    site instead resolves its candidates at render time and falls back to an
    internal sentinel so the remaining documents render; the orchestrator
    skips the documents that contain the sentinel. Sites that use
    ``ignore missing`` fall back to an empty template and produce no warning.

    ``_parse`` is a private Jinja hook, used deliberately: wrapping the
    include expression in the AST is the only way to attribute an include
    failure to its own line. The resolver returns ``Template`` objects, which
    relies on ``Environment.get_template`` accepting a template instance as
    well as a name (typed ``str | Template`` since Jinja 3.1). That contract
    is covered by
    ``test_environment_get_template_passes_through_template_instances``, so a
    Jinja upgrade that breaks it fails loudly here rather than silently
    resolving the wrong template.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._include_sites: dict[int, _IncludeSite] = {}
        self._next_include_site_id = 1
        self._failed_include_sites: set[int] = set()
        self._outermost_site_by_template: dict[str, int] = {}
        environment_globals: MutableMapping[str, Any] = self.globals
        environment_globals[_INCLUDE_RESOLVER_NAME] = self._resolve_include

    def _parse(
        self, source: str, name: str | None, filename: str | None
    ) -> jinja2.nodes.Template:
        tree = super()._parse(source, name, filename)
        return _IncludeSiteTransformer(self, name).visit(tree)

    def register_include_site(
        self, node: jinja2.nodes.Include, containing_template: str | None
    ) -> int:
        site_id = self._next_include_site_id
        self._next_include_site_id += 1
        self._include_sites[site_id] = _IncludeSite(
            line_number=node.lineno or 1,
            display_name=_include_display_name(node),
            ignore_missing=node.ignore_missing,
            containing_template=containing_template,
        )
        return site_id

    def failed_include_warnings(self) -> list[JinjaIssue]:
        warnings: list[JinjaIssue] = []
        for site_id in sorted(self._failed_include_sites):
            site = self._include_sites[site_id]
            outermost_site_id = self._outermost_site(site_id)
            label = site.display_name
            if outermost_site_id != site_id and site.containing_template is not None:
                label = f"{label} (included by {site.containing_template!r})"
            warnings.append(
                JinjaIssue(
                    code=MessageCode.JINJA_INCLUDE_UNRESOLVED,
                    message=format_message(
                        MessageCode.JINJA_INCLUDE_UNRESOLVED,
                        names=label,
                    ),
                    line_number=self._include_sites[outermost_site_id].line_number,
                )
            )
        return warnings

    def _resolve_include(self, value: object, site_id: int) -> jinja2.Template:
        if self.loader is not None:
            for name in _iter_include_names(value):
                try:
                    template = self.get_template(name)
                except jinja2.TemplateNotFound:
                    continue
                if template.name is not None:
                    self._outermost_site_by_template.setdefault(
                        template.name, self._outermost_site(site_id)
                    )
                return template
        if self._include_sites[site_id].ignore_missing:
            return self._empty_template
        self._failed_include_sites.add(site_id)
        return self._sentinel_template

    def _outermost_site(self, site_id: int) -> int:
        """Return the top-level include site a nested site belongs to."""
        containing_template = self._include_sites[site_id].containing_template
        if containing_template is None:
            return site_id
        return self._outermost_site_by_template.get(containing_template, site_id)

    @functools.cached_property
    def _sentinel_template(self) -> jinja2.Template:
        return self.from_string(_UNRESOLVED_INCLUDE_SENTINEL)

    @functools.cached_property
    def _empty_template(self) -> jinja2.Template:
        return self.from_string("")


class _IncludeSiteTransformer(jinja2.visitor.NodeTransformer):
    """Wraps every ``{% include %}`` expression in a site resolver call."""

    def __init__(
        self, environment: _IncludeResilientEnvironment, containing_template: str | None
    ) -> None:
        super().__init__()
        self._environment = environment
        self._containing_template = containing_template

    def visit_Include(self, node: jinja2.nodes.Include) -> jinja2.nodes.Node:
        site_id = self._environment.register_include_site(
            node, self._containing_template
        )
        resolver = jinja2.nodes.Call(
            jinja2.nodes.Name(_INCLUDE_RESOLVER_NAME, "load"),
            [node.template, jinja2.nodes.Const(site_id)],
            [],
            None,
            None,
        )
        resolver.set_ctx("load")
        node.template = resolver
        return node


def _error_result(
    content: str, *, code: str, message: str, line_number: int
) -> JinjaRenderResult:
    return JinjaRenderResult(
        text=content,
        errors=(JinjaIssue(code=code, message=message, line_number=line_number),),
    )


def preprocess_jinja(
    content: str, *, input_file: str | None = None
) -> JinjaRenderResult:
    loader = None
    if input_file and input_file != "<string input>":
        parent = Path(input_file).expanduser().resolve().parent
        loader = jinja2.FileSystemLoader(str(parent))

    environment = _IncludeResilientEnvironment(
        loader=loader,
        undefined=_SilentUndefined,
        keep_trailing_newline=True,
    )

    try:
        template = environment.from_string(content)
    except jinja2.exceptions.TemplateSyntaxError as ex:
        return _error_result(
            content,
            code=MessageCode.JINJA2_SYNTAX_ERROR,
            message=f"Jinja2 syntax error at line {ex.lineno}: {ex.message}",
            line_number=ex.lineno or 1,
        )

    try:
        rendered = template.render()
    except jinja2.exceptions.TemplateError as ex:
        return _error_result(
            content,
            code=MessageCode.JINJA2_TEMPLATE_ERROR,
            message=f"Jinja2 template error: {ex}",
            line_number=getattr(ex, "lineno", None) or _first_jinja_line(content),
        )

    return JinjaRenderResult(
        text=rendered,
        warnings=tuple(environment.failed_include_warnings()),
    )
