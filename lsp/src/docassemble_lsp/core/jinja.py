from __future__ import annotations

import functools
import multiprocessing
import os
import re
import signal
import sys
import threading
import warnings
from collections.abc import Iterable, MutableMapping
from dataclasses import dataclass
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

import jinja2
import jinja2.nodes
import jinja2.sandbox
import jinja2.visitor

from docassemble_lsp.core.messages import MessageCode, format_message

try:  # pragma: no cover - depends on the platform
    import resource as _resource
except ImportError:  # pragma: no cover - Windows has no resource module
    _resource = None

_JINJA_SYNTAX_RE = re.compile(r"({{.*?}}|{%-?.*?-?%}|{#.*?#})", re.DOTALL)

#: Rendered where a Jinja include cannot be resolved. Validation skips the
#: documents that contain it because the included content is unknown.
_UNRESOLVED_INCLUDE_SENTINEL = "__docassemble_lsp_unresolved_include__"

#: Rendered in place of a value that only the server supplies (``jinja data``
#: or docassemble's Jinja context). Each substitution gets its own token, so
#: two unknown values can never be mistaken for each other or for a value
#: the author wrote.
_UNKNOWN_VALUE_PREFIX = "__docassemble_lsp_unknown_"

#: Name of the internal function wrapped around template expressions of
#: ``{% include %}`` tags so each include site can resolve itself at render
#: time and report failures against its own line.
_INCLUDE_RESOLVER_NAME = "__docassemble_lsp_resolve_include__"


@dataclass(frozen=True, slots=True)
class JinjaRenderLimits:
    """Resource bounds applied to a single Jinja render.

    ``source_characters`` is checked before parsing, so an oversized source
    is never processed. ``output_characters`` stops rendering as soon as the
    accumulated template output passes the cap. ``wall_seconds`` is enforced
    by the parent process, which kills a render that outlives it.
    ``cpu_seconds`` and ``address_space_headroom_bytes`` become the render
    process's ``RLIMIT_CPU`` and ``RLIMIT_AS``. macOS does not enforce
    address-space limits, so that limit is skipped there and the wall
    timeout remains the bound. A render is never run in the parent
    process: if the bounded render process cannot be created, the render
    is refused instead.
    """

    source_characters: int = 4 * 1024 * 1024
    output_characters: int = 16 * 1024 * 1024
    wall_seconds: float = 5.0
    cpu_seconds: int = 12
    address_space_headroom_bytes: int = 512 * 1024 * 1024


#: Default bounds for one Jinja render.
JINJA_RENDER_LIMITS = JinjaRenderLimits()

#: Grace period for reaping a render process after it replies or is killed.
_REAP_SECONDS = 5.0


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


def contains_placeholder(content: object) -> bool:
    """Return True when rendered ``content`` still contains a server placeholder.

    Workspace-aware checks resolve names against the rest of the interview,
    so a value that was substituted for an unknown server value must not be
    resolved as if the author had written it. Non-string values cannot
    contain a placeholder.
    """
    return isinstance(content, str) and _UNKNOWN_VALUE_PREFIX in content


@dataclass(frozen=True, slots=True)
class _UnknownValueSite:
    """The template site one unknown value was substituted at.

    ``template_name`` is the immediate template (``None`` for the file being
    rendered), while ``line_number`` is the line reported to the user: the
    outermost include line or the render root's call site.
    """

    template_name: str | None
    line_number: int
    variable_name: str | None


class _UnknownValueTracker:
    """Placeholders and warnings for one render's unknown values.

    ``placeholder_for`` assigns a fresh token to every substitution, so a
    site that renders repeatedly (a loop, or a template included twice)
    still produces distinct values and cannot look like a duplicate block
    ID. ``warn`` records at most one warning per site, so one source site
    warns once however often it renders.
    """

    def __init__(self) -> None:
        self._count = 0
        self._warnings: dict[_UnknownValueSite, JinjaIssue] = {}

    def placeholder_for(self, site: _UnknownValueSite) -> str:
        self.warn(site)
        self._count += 1
        return f"{_UNKNOWN_VALUE_PREFIX}{self._count}__"

    def warn(self, site: _UnknownValueSite) -> None:
        if site in self._warnings:
            return
        self._warnings[site] = JinjaIssue(
            code=MessageCode.JINJA_UNKNOWN_VALUE,
            message=format_message(
                MessageCode.JINJA_UNKNOWN_VALUE,
                name=site.variable_name or "value",
            ),
            line_number=site.line_number,
        )

    def issues(self) -> list[JinjaIssue]:
        return [
            self._warnings[site]
            for site in sorted(
                self._warnings,
                key=lambda site: (site.line_number, site.variable_name or ""),
            )
        ]


def _locate_unknown_value_site(
    variable_name: str | None,
) -> tuple[_UnknownValueTracker, _UnknownValueSite] | None:
    """Find the render frame that substituted an unknown value.

    Jinja's generated template code carries ``__jinja_template__`` in its
    globals, the same marker ``jinja2.debug`` uses to rewrite tracebacks.
    Walking to that frame gives the template and generated line, which
    ``Template.get_corresponding_lineno`` maps to a source line.

    The reported line always belongs to the file being rendered. A use
    inside an ``{% include %}`` is attributed to the outermost include
    site, mirroring unresolved includes; a use inside an imported macro or
    an inherited block is attributed to the call site in the render root.
    """
    innermost: tuple[jinja2.Template, int] | None = None
    root_line_number: int | None = None
    frame = sys._getframe(2)
    while frame is not None:
        template = frame.f_globals.get("__jinja_template__")
        if template is not None:
            if innermost is None:
                innermost = (template, frame.f_lineno)
            if template.name is None:
                root_line_number = template.get_corresponding_lineno(frame.f_lineno)
        frame = frame.f_back
    if innermost is None:
        return None

    template, generated_line = innermost
    environment = template.environment
    tracker = getattr(environment, "_unknown_values", None)
    if not isinstance(tracker, _UnknownValueTracker):
        return None

    line_number = template.get_corresponding_lineno(generated_line)
    if template.name is not None:
        include_sites = getattr(environment, "_include_sites", {})
        outermost_site_by_template = getattr(
            environment, "_outermost_site_by_template", {}
        )
        outermost_site_id = outermost_site_by_template.get(template.name)
        if outermost_site_id in include_sites:
            line_number = include_sites[outermost_site_id].line_number
        elif root_line_number is not None:
            line_number = root_line_number
    return tracker, _UnknownValueSite(
        template_name=template.name,
        line_number=line_number,
        variable_name=variable_name,
    )


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


class _SandboxViolationUndefined(jinja2.StrictUndefined):
    """Undefined returned for an unsafe sandbox attribute.

    ``_SilentUndefined`` renders unknown values as empty text, but a sandbox
    violation must never render silently: every use of this undefined raises
    the ``SecurityError`` the sandbox attached to it.
    """


class _PlaceholderUndefined(_SilentUndefined):
    """Undefined that renders a distinct placeholder for a server value.

    Every undefined name is assumed to be a value only the server supplies
    (``jinja data`` or docassemble's Jinja context), so rendering it as empty
    text both hides real errors and makes unrelated values look equal. A
    substitution instead renders a unique, parseable placeholder and records
    one warning per source site. Truth tests, iteration, length, indexing,
    attribute access, and calls keep their silent behaviour so the rest of
    the document still renders and validates.
    """

    def __str__(self) -> str:
        located = _locate_unknown_value_site(self._undefined_name)
        if located is None:
            return ""
        tracker, site = located
        return tracker.placeholder_for(site)

    def __getattr__(self, name: str) -> _PlaceholderUndefined:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._derive()

    def __getitem__(self, key: object) -> _PlaceholderUndefined:  # type: ignore[override]
        return self._derive()

    def __call__(self, *args: object, **kwargs: object) -> _PlaceholderUndefined:
        return self._derive()

    def _derive(self) -> _PlaceholderUndefined:
        """Return the undefined this one stands for, keeping its name."""
        return _PlaceholderUndefined(
            self._undefined_hint,
            self._undefined_obj,
            self._undefined_name,
            self._undefined_exception,
        )


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


class _IncludeResilientEnvironment(jinja2.sandbox.SandboxedEnvironment):
    """Sandboxed environment that turns missing Jinja templates into warnings.

    Template code runs in Jinja's sandbox, so access to unsafe attributes is
    refused. ``unsafe_undefined`` returns a strict undefined, which means an
    expression that reaches an unsafe attribute raises ``SecurityError``
    instead of rendering as empty text.

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
    resolving the wrong template. The dependency is capped below Jinja 4 for
    the same reason.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._include_sites: dict[int, _IncludeSite] = {}
        self._next_include_site_id = 1
        self._failed_include_sites: set[int] = set()
        self._outermost_site_by_template: dict[str, int] = {}
        self._unknown_values = _UnknownValueTracker()
        environment_globals: MutableMapping[str, Any] = self.globals
        environment_globals[_INCLUDE_RESOLVER_NAME] = self._resolve_include

    def _parse(
        self, source: str, name: str | None, filename: str | None
    ) -> jinja2.nodes.Template:
        tree = super()._parse(source, name, filename)
        return _IncludeSiteTransformer(self, name).visit(tree)

    def unsafe_undefined(self, obj: Any, attribute: str) -> jinja2.Undefined:
        """Return a strict undefined for an unsafe attribute access.

        Jinja's default undefined is silent, so a sandbox violation would
        render as empty text. Returning a strict undefined makes any use of
        the value raise the ``SecurityError`` attached to it.
        """
        return _SandboxViolationUndefined(
            f"access to attribute {attribute!r} of"
            f" {type(obj).__name__!r} object is unsafe.",
            name=attribute,
            obj=obj,
            exc=jinja2.exceptions.SecurityError,
        )

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

    def unknown_value_warnings(self) -> list[JinjaIssue]:
        """Return one warning for every site that substituted an unknown value."""
        return self._unknown_values.issues()

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


def _resource_limit_result(content: str, reason: str) -> JinjaRenderResult:
    return _error_result(
        content,
        code=MessageCode.JINJA_RENDER_RESOURCE_LIMIT,
        message=format_message(MessageCode.JINJA_RENDER_RESOURCE_LIMIT, reason=reason),
        line_number=_first_jinja_line(content),
    )


class _OutputLimitExceeded(Exception):
    """Raised internally when rendered output passes the configured cap."""


def _render_template_text(template: jinja2.Template, limits: JinjaRenderLimits) -> str:
    """Render ``template``, stopping as soon as the output cap is passed."""
    chunks: list[str] = []
    size = 0
    for chunk in template.generate():
        size += len(chunk)
        if size > limits.output_characters:
            raise _OutputLimitExceeded
        chunks.append(chunk)
    return "".join(chunks)


def _render_jinja(
    content: str, *, input_file: str | None, limits: JinjaRenderLimits
) -> JinjaRenderResult:
    """Render ``content`` in the current process.

    This runs inside the bounded render process; it is also the fallback
    when no child process can be created.
    """
    loader = None
    if input_file and input_file != "<string input>":
        parent = Path(input_file).expanduser().resolve().parent
        loader = jinja2.FileSystemLoader(str(parent))

    environment = _IncludeResilientEnvironment(
        loader=loader,
        undefined=_PlaceholderUndefined,
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
        rendered = _render_template_text(template, limits)
    except _OutputLimitExceeded:
        return _error_result(
            content,
            code=MessageCode.JINJA_OUTPUT_TOO_LARGE,
            message=format_message(
                MessageCode.JINJA_OUTPUT_TOO_LARGE, limit=limits.output_characters
            ),
            line_number=_first_jinja_line(content),
        )
    except jinja2.exceptions.SecurityError as ex:
        return _error_result(
            content,
            code=MessageCode.JINJA_SANDBOX_VIOLATION,
            message=format_message(MessageCode.JINJA_SANDBOX_VIOLATION, error=str(ex)),
            line_number=getattr(ex, "lineno", None) or _first_jinja_line(content),
        )
    except jinja2.exceptions.TemplateError as ex:
        return _error_result(
            content,
            code=MessageCode.JINJA2_TEMPLATE_ERROR,
            message=f"Jinja2 template error: {ex}",
            line_number=getattr(ex, "lineno", None) or _first_jinja_line(content),
        )
    except RecursionError:
        return _resource_limit_result(content, "the recursion limit was reached")
    except MemoryError:
        return _resource_limit_result(content, "memory was exhausted")
    except OverflowError:
        # Jinja's sandbox caps ``range`` and refuses values that cannot be
        # iterated; report the bound instead of crashing the render.
        return _resource_limit_result(
            content, "the sandbox refused an oversized value or range"
        )

    return JinjaRenderResult(
        text=rendered,
        warnings=tuple(environment.failed_include_warnings())
        + tuple(environment.unknown_value_warnings()),
    )


def _process_context():
    """Return the multiprocessing context used for bounded renders.

    The concrete context types (``ForkContext``/``SpawnContext``) are
    intentionally left to inference: typeshed does not declare ``Process``
    on the ``BaseContext`` they widen to.
    """
    if hasattr(os, "fork"):
        return multiprocessing.get_context("fork")
    return multiprocessing.get_context("spawn")


def _silence_standard_output() -> None:
    """Detach the render process from the stdio the LSP protocol uses.

    A forked render process inherits the server's stdout, where protocol
    messages are written. Redirecting it to the null device keeps a stray
    write from corrupting the protocol; stderr is left alone so a crash
    traceback reaches the host's log.
    """
    try:
        stdout_fd = sys.stdout.fileno()
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
    except (AttributeError, OSError, ValueError):  # pragma: no cover - defensive
        return
    try:
        os.dup2(devnull_fd, stdout_fd)
    except OSError:  # pragma: no cover - defensive
        pass
    finally:
        os.close(devnull_fd)


def _current_address_space_bytes() -> int | None:
    """Return this process's virtual address space when it is exposed."""
    try:
        with open("/proc/self/statm", encoding="ascii") as statm:
            pages = int(statm.read().split()[0])
        return pages * os.sysconf("SC_PAGE_SIZE")
    except (IndexError, OSError, ValueError):
        return None


def _apply_resource_limits(
    *, platform: str, cpu_seconds: int, address_space_headroom_bytes: int
) -> None:
    """Set the render process's CPU and address-space limits.

    macOS accepts but does not enforce address-space limits, so that limit is
    skipped there and the parent's wall timeout remains the only bound.
    """
    if _resource is None:
        return
    cpu = max(1, int(cpu_seconds))
    _resource.setrlimit(_resource.RLIMIT_CPU, (cpu, cpu))
    if platform == "darwin":
        return
    current = _current_address_space_bytes()
    if current is None:
        return
    limit = current + address_space_headroom_bytes
    _resource.setrlimit(_resource.RLIMIT_AS, (limit, limit))


def _render_worker(
    connection: Connection,
    content: str,
    input_file: str | None,
    limits: JinjaRenderLimits,
) -> None:
    """Render one template in a dedicated, resource-limited process."""
    _silence_standard_output()
    try:
        _apply_resource_limits(
            platform=sys.platform,
            cpu_seconds=limits.cpu_seconds,
            address_space_headroom_bytes=limits.address_space_headroom_bytes,
        )
    except (OSError, ValueError):  # pragma: no cover - defensive
        pass
    result = _render_jinja(content, input_file=input_file, limits=limits)
    try:
        connection.send(result)
    except (BrokenPipeError, OSError):  # pragma: no cover - parent gave up
        pass
    finally:
        connection.close()


def _stopped_reason(exitcode: int | None) -> str:
    sigxcpu = getattr(signal, "SIGXCPU", None)
    if sigxcpu is not None and exitcode == -sigxcpu:
        return "the CPU time limit was reached"
    return (
        "the render process stopped unexpectedly; "
        "it may have exceeded its CPU or memory limit"
    )


def _format_seconds(seconds: float) -> str:
    return f"{seconds:g}"


def _render_bounded(
    content: str, *, input_file: str | None, limits: JinjaRenderLimits
) -> JinjaRenderResult:
    """Render ``content`` in a bounded child process."""
    context = _process_context()
    receive_connection, send_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_render_worker,
        args=(send_connection, content, input_file, limits),
        daemon=True,
    )
    try:
        with warnings.catch_warnings():
            # A host process may be multi-threaded (test runners, editor
            # hosts), which makes Python 3.12+ warn about fork. The render
            # process only runs Jinja and never touches a parent lock, so
            # fork is deliberate and safe here.
            warnings.simplefilter("ignore", DeprecationWarning)
            process.start()
    except (AssertionError, OSError, RuntimeError, ValueError):
        # Process creation can be unavailable (a daemonic or restricted
        # parent). Bounded rendering is a precondition for rendering at
        # all: the in-process path is exactly the one the wall clock and
        # rlimits exist to bound, so refuse the render instead of falling
        # back to it. Upstream applies the same policy on platforms where
        # resource limits are unavailable.
        receive_connection.close()
        send_connection.close()
        return _error_result(
            content,
            code=MessageCode.JINJA_RENDER_UNAVAILABLE,
            message=format_message(MessageCode.JINJA_RENDER_UNAVAILABLE),
            line_number=_first_jinja_line(content),
        )

    # The child owns the write end now. Closing the parent's copy lets the
    # read end see EOF when the render finishes or is killed.
    send_connection.close()

    timed_out = threading.Event()

    def _abort() -> None:
        timed_out.set()
        process.kill()

    reply: JinjaRenderResult | None = None
    timer = threading.Timer(limits.wall_seconds, _abort)
    timer.start()
    try:
        try:
            reply = receive_connection.recv()
        except (EOFError, OSError):
            reply = None
    finally:
        timer.cancel()
        receive_connection.close()
        process.join(timeout=_REAP_SECONDS)
        if process.is_alive():  # pragma: no cover - defensive
            process.kill()
            process.join(timeout=_REAP_SECONDS)

    if reply is not None:
        return reply

    line_number = _first_jinja_line(content)
    if timed_out.is_set():
        return _error_result(
            content,
            code=MessageCode.JINJA_RENDER_TIMEOUT,
            message=format_message(
                MessageCode.JINJA_RENDER_TIMEOUT,
                seconds=_format_seconds(limits.wall_seconds),
            ),
            line_number=line_number,
        )
    return _error_result(
        content,
        code=MessageCode.JINJA_RENDER_RESOURCE_LIMIT,
        message=format_message(
            MessageCode.JINJA_RENDER_RESOURCE_LIMIT,
            reason=_stopped_reason(process.exitcode),
        ),
        line_number=line_number,
    )


def preprocess_jinja(
    content: str,
    *,
    input_file: str | None = None,
    limits: JinjaRenderLimits | None = None,
) -> JinjaRenderResult:
    """Render ``# use jinja`` source under sandbox and resource bounds.

    The source is rejected when it is longer than
    ``limits.source_characters``, and rendering runs in a child process with
    CPU and address-space rlimits. A render that outlives
    ``limits.wall_seconds`` is killed and reported as ``E209``. A sandbox
    violation or a render that passes a size limit is reported instead of
    being rendered. When the child process cannot be created at all, the
    render is refused with ``E213`` rather than falling back to an
    unbounded in-process render.
    """
    render_limits = limits if limits is not None else JINJA_RENDER_LIMITS
    source_size = len(content)
    if source_size > render_limits.source_characters:
        return _error_result(
            content,
            code=MessageCode.JINJA_SOURCE_TOO_LARGE,
            message=format_message(
                MessageCode.JINJA_SOURCE_TOO_LARGE,
                size=source_size,
                limit=render_limits.source_characters,
            ),
            line_number=1,
        )
    return _render_bounded(content, input_file=input_file, limits=render_limits)
