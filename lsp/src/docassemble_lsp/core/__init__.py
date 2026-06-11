from __future__ import annotations

from importlib import import_module

_PUBLIC_EXPORTS = {
    "DocumentFact": ("docassemble_lsp.core.document_facts", "DocumentFact"),
    "Diagnostic": ("docassemble_lsp.core.diagnostics", "Diagnostic"),
    "FixResult": ("docassemble_lsp.core.fixes", "FixResult"),
    "FormatResult": ("docassemble_lsp.core.formatting", "FormatResult"),
    "FormatterConfig": ("docassemble_lsp.core.formatting", "FormatterConfig"),
    "WorkspaceIndex": ("docassemble_lsp.core.workspace", "WorkspaceIndex"),
    "analyze_path": ("docassemble_lsp.core.diagnostics", "analyze_path"),
    "analyze_text": ("docassemble_lsp.core.diagnostics", "analyze_text"),
    "build_document_facts": ("docassemble_lsp.core.document_facts", "build_document_facts"),
    "build_workspace_index": ("docassemble_lsp.core.definitions", "build_workspace_index"),
    "collect_yaml_files": ("docassemble_lsp.core.files", "collect_yaml_files"),
    "configure_logging": ("docassemble_lsp.core.logging", "configure_logging"),
    "reset_logging": ("docassemble_lsp.core.logging", "reset_logging"),
    "fix_path": ("docassemble_lsp.core.fixes", "fix_path"),
    "fix_text": ("docassemble_lsp.core.fixes", "fix_text"),
    "format_path": ("docassemble_lsp.core.formatting", "format_path"),
    "format_text": ("docassemble_lsp.core.formatting", "format_text"),
    "get_completions": ("docassemble_lsp.core.schema", "get_completions"),
    "get_hover": ("docassemble_lsp.core.schema", "get_hover"),
    "resolve_definition_targets": ("docassemble_lsp.core.definitions", "resolve_definition_targets"),
    "resolve_python_hover": ("docassemble_lsp.core.definitions", "resolve_python_hover"),
    "resolve_reference_targets": ("docassemble_lsp.core.definitions", "resolve_reference_targets"),
    "resolve_workspace_symbol_targets": ("docassemble_lsp.core.definitions", "resolve_workspace_symbol_targets"),
}


def __getattr__(name: str):
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = export
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_PUBLIC_EXPORTS.keys()))


__all__ = [
    "DocumentFact",
    "Diagnostic",
    "FixResult",
    "FormatResult",
    "FormatterConfig",
    "WorkspaceIndex",
    "analyze_path",
    "analyze_text",
    "build_document_facts",
    "build_workspace_index",
    "collect_yaml_files",
    "configure_logging",
    "reset_logging",
    "fix_path",
    "fix_text",
    "format_path",
    "format_text",
    "get_completions",
    "get_hover",
    "resolve_definition_targets",
    "resolve_python_hover",
    "resolve_reference_targets",
    "resolve_workspace_symbol_targets",
]
