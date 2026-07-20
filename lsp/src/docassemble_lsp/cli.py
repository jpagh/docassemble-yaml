from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence, TypeVar, overload

from docassemble_lsp.core import (
    Diagnostic,
    FormatterConfig,
    analyze_text,
    collect_yaml_files,
    configure_logging,
    fix_text,
    format_path,
    format_text,
)
from docassemble_lsp.core.diagnostics import diagnostic_to_dict
from docassemble_lsp.core.files import (
    collect_dayaml_cli_args,
    collect_dayaml_conventions,
    collect_dayaml_ignore_codes,
)
from docassemble_lsp.core.messages import MESSAGE_DEFINITIONS
from docassemble_lsp.core.validation_config import RuntimeOptions, parse_ignore_codes
from docassemble_lsp.lsp.server import run_server

_CODE_TOKEN_RE = re.compile(r"^[A-Za-z]\d+$")
_FORMATTING_SHARED_FLAGS = frozenset({"--convert-tabs-to-spaces"})
_NamespaceT = TypeVar("_NamespaceT")


def _is_code_list_token(token: str, *, allow_all: bool) -> bool:
    parts = [part.strip() for part in token.split(",") if part.strip()]
    if not parts:
        return False
    return all(
        (allow_all and part.lower() == "all") or _CODE_TOKEN_RE.fullmatch(part)
        for part in parts
    )


def _normalize_multi_value_code_options(argv: Sequence[str] | None) -> list[str] | None:
    if argv is None:
        return None

    normalized: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in {"--conventions", "--ignore-codes"}:
            allow_all = token == "--conventions"
            values: list[str] = []
            index += 1
            while index < len(argv):
                candidate = argv[index]
                if (
                    candidate == "--"
                    or candidate.startswith("-")
                    or not _is_code_list_token(candidate, allow_all=allow_all)
                ):
                    break
                values.append(candidate)
                index += 1
            normalized.append(token)
            if values:
                normalized.append(",".join(values))
            continue
        normalized.append(token)
        index += 1
    return normalized


def _materialize_args(args: Iterable[str] | None) -> list[str] | None:
    if args is None:
        return None
    if isinstance(args, Sequence):
        return list(args)
    return list(args)


class _CliArgumentParser(argparse.ArgumentParser):
    @overload
    def parse_args(
        self, args: Iterable[str] | None = None, namespace: None = None
    ) -> argparse.Namespace: ...

    @overload
    def parse_args(
        self, args: Iterable[str] | None, namespace: _NamespaceT
    ) -> _NamespaceT: ...

    @overload
    def parse_args(self, *, namespace: _NamespaceT) -> _NamespaceT: ...

    def parse_args(
        self, args: Iterable[str] | None = None, namespace: _NamespaceT | None = None
    ) -> argparse.Namespace | _NamespaceT:
        normalized_args = _normalize_multi_value_code_options(_materialize_args(args))
        return super().parse_args(normalized_args, namespace)

    @overload
    def parse_known_args(
        self, args: Iterable[str] | None = None, namespace: None = None
    ) -> tuple[argparse.Namespace, list[str]]: ...

    @overload
    def parse_known_args(
        self, args: Iterable[str] | None, namespace: _NamespaceT
    ) -> tuple[_NamespaceT, list[str]]: ...

    @overload
    def parse_known_args(
        self, *, namespace: _NamespaceT
    ) -> tuple[_NamespaceT, list[str]]: ...

    def parse_known_args(
        self, args: Iterable[str] | None = None, namespace: _NamespaceT | None = None
    ) -> tuple[argparse.Namespace | _NamespaceT, list[str]]:
        normalized_args = _normalize_multi_value_code_options(_materialize_args(args))
        return super().parse_known_args(normalized_args, namespace)


def _build_bootstrap_parser() -> argparse.ArgumentParser:
    parser = _CliArgumentParser(add_help=False, prog="docassemble-lsp")
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser("check", add_help=False)
    check_parser.add_argument("paths", nargs="*")

    format_parser = subparsers.add_parser("format", add_help=False)
    format_parser.add_argument("paths", nargs="*")

    subparsers.add_parser("lsp", add_help=False)
    subparsers.add_parser("codes", add_help=False)
    return parser


def _config_paths_for_argv(argv: Sequence[str]) -> tuple[str | None, list[Path]]:
    if not argv or argv[0] in {"-h", "--help"}:
        return (None, [])

    bootstrap_args, _unknown = _build_bootstrap_parser().parse_known_args(list(argv))
    command = getattr(bootstrap_args, "command", None)
    if command in {"check", "format"}:
        return (command, _default_paths(getattr(bootstrap_args, "paths", [])))
    if command == "lsp":
        return (command, [Path.cwd()])
    return (command, [])


def _config_cli_args_for_argv(argv: Sequence[str]) -> tuple[str, ...]:
    command, config_paths = _config_paths_for_argv(argv)
    if command is None or not config_paths:
        return ()

    cli_args = list(collect_dayaml_cli_args(config_paths, command_name=command))
    if command == "check":
        cli_args = [arg for arg in cli_args if arg not in _FORMATTING_SHARED_FLAGS]
    if command in {"check", "lsp"}:
        conventions = collect_dayaml_conventions(config_paths)
        if conventions:
            cli_args.extend(["--conventions", *sorted(conventions)])
        ignore_codes = collect_dayaml_ignore_codes(config_paths)
        if ignore_codes:
            cli_args.extend(["--ignore-codes", *sorted(ignore_codes)])
    return tuple(cli_args)


def _merge_config_args(
    raw_argv: Sequence[str], config_args: Sequence[str]
) -> list[str]:
    if not raw_argv or not config_args:
        return list(raw_argv)
    return [raw_argv[0], *config_args, *raw_argv[1:]]


def _default_paths(values: Sequence[str]) -> list[Path]:
    return [Path(value) for value in values] if values else [Path(".")]


def _print_diagnostic(path: Path, diagnostic: Diagnostic) -> None:
    code = f" [{diagnostic.code}]" if diagnostic.code else ""
    print(
        f"{path}:{diagnostic.line}: {diagnostic.severity}{code} {diagnostic.message}",
        file=sys.stdout,
    )


def _parsed_code_args(values: Sequence[str] | None) -> frozenset[str]:
    return parse_ignore_codes(",".join(values or []))


def _runtime_options_from_args(args: argparse.Namespace) -> RuntimeOptions:
    accessibility_widgets = frozenset(
        widget.strip().lower()
        for widget in getattr(args, "accessibility_error_on_widgets", [])
        if widget.strip()
    )
    return RuntimeOptions(
        accessibility_error_on_widgets=accessibility_widgets,
        enabled_conventions=_parsed_code_args(getattr(args, "conventions", None)),
        ignore_codes=_parsed_code_args(getattr(args, "ignore_codes", None)),
        show_warnings=not getattr(args, "no_warnings", False),
        indent=int(getattr(args, "indent", 2)),
    )


def _formatter_config_from_args(args: argparse.Namespace) -> FormatterConfig:
    # black target_versions follow the installed black; see FormatterConfig.
    return FormatterConfig(
        convert_tabs_to_spaces=bool(getattr(args, "convert_tabs_to_spaces", False)),
        indent=int(getattr(args, "indent", 2)),
    )


def _message_severity(code: str) -> str:
    if code.startswith("W"):
        return "warning"
    if code.startswith("C"):
        return "convention"
    return "error"


def _codes_command(_args: argparse.Namespace) -> int:
    rows = [
        (code, _message_severity(code), MESSAGE_DEFINITIONS[code].summary)
        for code in sorted(MESSAGE_DEFINITIONS)
    ]
    code_width = max(len(code) for code, _, _ in rows)
    severity_width = max(len(severity) for _, severity, _ in rows)

    for code, severity, summary in rows:
        print(
            f"{code:<{code_width}}  {severity:<{severity_width}}  {summary}",
            file=sys.stdout,
        )
    return 0


def _check_command(args: argparse.Namespace) -> int:
    configure_logging(level=args.log_level)
    paths = collect_yaml_files(_default_paths(args.paths), check_all=args.check_all)
    results: list[dict[str, object]] = []
    has_failure = False
    runtime_options = _runtime_options_from_args(args)
    formatter_config = _formatter_config_from_args(args)

    for path in paths:
        try:
            original = path.read_text(encoding="utf-8")
        except OSError as exc:
            has_failure = True
            if args.json:
                results.append({"path": str(path), "error": str(exc)})
            if not args.quiet and not args.json:
                print(f"{path}: error - {exc}", file=sys.stderr)
            continue

        working = original
        if args.fix:
            fix_result = fix_text(
                working, path=str(path), runtime_options=runtime_options
            )
            working = fix_result.text

        diagnostics = analyze_text(
            working, path=str(path), runtime_options=runtime_options
        )
        error_findings = [d for d in diagnostics if d.severity == "error"]

        should_format = (args.format_on_success and not error_findings) or args.check
        if should_format:
            format_result = format_text(working, config=formatter_config)
            working = format_result.text

        changed = working != original
        if changed:
            if args.check:
                has_failure = True
                if not args.quiet and not args.json:
                    print(f"would reformat: {path}", file=sys.stdout)
            else:
                path.write_text(working, encoding="utf-8")
                if not args.quiet and not args.json:
                    print(f"reformatted: {path}", file=sys.stdout)

        for diagnostic in diagnostics:
            entry = diagnostic_to_dict(diagnostic)
            entry["path"] = str(path)
            results.append(entry)
            if diagnostic.severity == "error" or (
                args.strict and diagnostic.severity in {"warning", "convention"}
            ):
                has_failure = True
            if not args.quiet and not args.json:
                _print_diagnostic(path, diagnostic)

    if args.json:
        json.dump(results, sys.stdout, indent=2)
        sys.stdout.write("\n")

    return 1 if has_failure else 0


def _format_command(args: argparse.Namespace) -> int:
    configure_logging(level=args.log_level)
    paths = collect_yaml_files(_default_paths(args.paths), check_all=args.check_all)
    changed_paths: list[str] = []
    formatter_config = _formatter_config_from_args(args)
    has_error = False

    for path in paths:
        try:
            result = format_path(path, config=formatter_config, write=not args.check)
        except OSError as exc:
            has_error = True
            if not args.quiet:
                print(f"{path}: error - {exc}", file=sys.stderr)
            continue
        if result.error is not None:
            has_error = True
            if not args.quiet:
                print(f"{path}: error - {result.error}", file=sys.stderr)
            continue
        if result.changed:
            changed_paths.append(str(path))
            if not args.quiet:
                status = "would reformat" if args.check else "reformatted"
                print(f"{status}: {path}", file=sys.stdout)

    return 1 if (args.check and changed_paths) or has_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = _CliArgumentParser(prog="docassemble-lsp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    codes_parser = subparsers.add_parser(
        "codes", help="List diagnostic codes, severities, and summaries"
    )
    codes_parser.set_defaults(func=_codes_command)

    check_parser = subparsers.add_parser(
        "check", help="Validate Docassemble YAML files"
    )
    check_parser.add_argument(
        "paths", nargs="*", help="Files or directories to validate"
    )
    check_parser.add_argument(
        "--json", action="store_true", help="Emit diagnostics as JSON"
    )
    check_parser.add_argument(
        "--no-warnings",
        action="store_true",
        help="Suppress warning diagnostics; only show errors",
    )
    check_parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress text output"
    )
    check_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on warnings and conventions as well as errors",
    )
    check_parser.add_argument(
        "--check-all",
        action="store_true",
        help="Do not skip build, dist, or hidden tool directories during traversal",
    )
    check_parser.add_argument(
        "--conventions",
        action="append",
        default=[],
        metavar="CODE",
        help="Enable convention diagnostics by code. Accepts multiple codes after one flag or comma-separated values; pass 'all' to enable every convention.",
    )
    check_parser.add_argument(
        "--ignore-codes",
        action="append",
        default=[],
        metavar="CODE",
        help="Ignore diagnostic codes. Accepts multiple codes after one flag or comma-separated values.",
    )
    check_parser.add_argument(
        "--fix",
        action="store_true",
        help="Rewrite files in place using docassemble-lsp's auto-fixable diagnostics before reporting results",
    )
    check_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help=argparse.SUPPRESS,
    )
    check_parser.add_argument(
        "--accessibility-error-on-widget",
        action="append",
        default=[],
        dest="accessibility_error_on_widgets",
        metavar="WIDGET",
        help="Treat a specific accessibility-sensitive widget as an error. Repeat to enable multiple widgets.",
    )
    check_parser.add_argument(
        "--format-on-success",
        action="store_true",
        help="Format files that pass YAML validation (no errors)",
    )
    check_parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: check what would be reformatted without writing, exit 1 if any file would change",
    )
    check_parser.add_argument(
        "--log-level",
        type=str.upper,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level for internal diagnostics (default: WARNING)",
    )
    check_parser.set_defaults(func=_check_command)

    format_parser = subparsers.add_parser(
        "format", help="Format embedded Python blocks"
    )
    format_parser.add_argument(
        "paths", nargs="*", help="Files or directories to format"
    )
    format_parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if files would change without writing edits",
    )
    format_parser.add_argument(
        "--quiet", action="store_true", help="Suppress text output"
    )
    format_parser.add_argument(
        "--check-all",
        action="store_true",
        help="Do not skip build, dist, or hidden tool directories during traversal",
    )
    format_parser.add_argument(
        "--convert-tabs-to-spaces",
        action="store_true",
        help="Replace literal tab characters in YAML files with two spaces while formatting.",
    )
    format_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Target Python block indentation width (default: 2)",
    )
    format_parser.add_argument(
        "--log-level",
        type=str.upper,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level for internal diagnostics (default: WARNING)",
    )
    format_parser.set_defaults(func=_format_command)

    lsp_parser = subparsers.add_parser("lsp", help="Run the stdio language server")
    lsp_parser.add_argument(
        "--stdio",
        action="store_true",
        help="Accepted for compatibility; stdio is already the default transport",
    )
    lsp_parser.add_argument(
        "--conventions",
        action="append",
        default=[],
        metavar="CODE",
        help="Enable convention diagnostics by code. Accepts multiple codes after one flag or comma-separated values; pass 'all' to enable every convention.",
    )
    lsp_parser.add_argument(
        "--ignore-codes",
        action="append",
        default=[],
        metavar="CODE",
        help="Ignore diagnostic codes. Accepts multiple codes after one flag or comma-separated values.",
    )
    lsp_parser.add_argument(
        "--convert-tabs-to-spaces",
        action="store_true",
        help="Replace literal tab characters in YAML files with two spaces when serving document formatting edits.",
    )
    lsp_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Number of spaces per indentation level for multi-line snippet continuations (default: 2)",
    )
    lsp_parser.add_argument(
        "--log-level",
        type=str.upper,
        default=os.environ.get("DOCASSEMBLE_LSP_LOG_LEVEL", "WARNING"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level for internal diagnostics (default: WARNING, overridable via DOCASSEMBLE_LSP_LOG_LEVEL)",
    )
    lsp_parser.set_defaults(
        func=lambda args: run_server(
            runtime_options=_runtime_options_from_args(args),
            formatter_config=_formatter_config_from_args(args),
            log_level=args.log_level,
        )
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(
        _merge_config_args(raw_argv, _config_cli_args_for_argv(raw_argv))
    )
    return int(args.func(args))
