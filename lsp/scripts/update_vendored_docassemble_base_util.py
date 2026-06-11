from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TARGETS = {
    "docassemble.base.util": REPO_ROOT / "src" / "docassemble_lsp" / "data" / "vendored_docassemble_base_util.pyi",
    "docassemble.base.functions": REPO_ROOT
    / "src"
    / "docassemble_lsp"
    / "data"
    / "vendored_docassemble_base_functions.pyi",
    "docassemble.base.error": REPO_ROOT / "src" / "docassemble_lsp" / "data" / "vendored_docassemble_base_error.pyi",
}


def _load_core_definitions():
    source_root = str(REPO_ROOT / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)

    from docassemble_lsp.core import python_modules as core_modules

    return core_modules


def _load_tree(module_name: str) -> tuple[Path, ast.Module]:
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin in {None, "built-in", "frozen"}:
        raise SystemExit(f"Could not resolve {module_name}")

    origin = spec.origin
    if origin is None:
        raise SystemExit(f"Could not resolve {module_name}")

    source_path = Path(origin)
    source = source_path.read_text(encoding="utf-8")
    return source_path, ast.parse(source)


def _annotation_text(annotation: ast.expr | None, *, default: str = "Any") -> str:
    if annotation is None:
        return default
    return ast.unparse(annotation)


def _render_arg(argument: ast.arg, *, defaulted: bool, allow_untyped_self: bool = False) -> str:
    if allow_untyped_self and argument.arg in {"self", "cls"} and argument.annotation is None:
        rendered = argument.arg
    else:
        rendered = f"{argument.arg}: {_annotation_text(argument.annotation)}"
    if defaulted:
        rendered += " = ..."
    return rendered


def _render_arguments(arguments: ast.arguments, *, is_method: bool) -> str:
    parts: list[str] = []
    positional = [*arguments.posonlyargs, *arguments.args]
    positional_defaults = [False] * (len(positional) - len(arguments.defaults)) + [True] * len(arguments.defaults)

    for index, argument in enumerate(arguments.posonlyargs):
        parts.append(
            _render_arg(
                argument,
                defaulted=positional_defaults[index],
                allow_untyped_self=is_method,
            )
        )
    if arguments.posonlyargs:
        parts.append("/")

    offset = len(arguments.posonlyargs)
    for index, argument in enumerate(arguments.args):
        parts.append(
            _render_arg(
                argument,
                defaulted=positional_defaults[offset + index],
                allow_untyped_self=is_method,
            )
        )

    if arguments.vararg is not None:
        parts.append(f"*{arguments.vararg.arg}: {_annotation_text(arguments.vararg.annotation)}")
    elif arguments.kwonlyargs:
        parts.append("*")

    for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults):
        parts.append(
            _render_arg(
                argument,
                defaulted=default is not None,
                allow_untyped_self=False,
            )
        )

    if arguments.kwarg is not None:
        parts.append(f"**{arguments.kwarg.arg}: {_annotation_text(arguments.kwarg.annotation)}")

    return ", ".join(parts)


def _render_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    supported = {"classmethod", "staticmethod", "property"}
    lines: list[str] = []
    for decorator in node.decorator_list:
        text = ast.unparse(decorator)
        if text in supported:
            lines.append(f"@{text}")
    return lines


def _render_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, *, indent: str = "", is_method: bool = False
) -> list[str]:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    arguments = _render_arguments(node.args, is_method=is_method)
    returns = _annotation_text(node.returns)
    lines = [f"{indent}{decorator}" for decorator in _render_decorators(node)]
    lines.append(f"{indent}{prefix} {node.name}({arguments}) -> {returns}:")
    docstring = ast.get_docstring(node)
    if docstring:
        body_indent = f"{indent}    "
        if "\n" in docstring:
            lines.append(f'{body_indent}"""')
            for doc_line in docstring.splitlines():
                lines.append(f"{body_indent}{doc_line}")
            lines.append(f'{body_indent}"""')
        else:
            lines.append(f'{body_indent}"""{docstring}"""')
    lines.append(f"{indent}    ...")
    return lines


def _render_class(node: ast.ClassDef) -> list[str]:
    bases = [ast.unparse(base) for base in node.bases]
    bases.extend(f"{keyword.arg}={ast.unparse(keyword.value)}" for keyword in node.keywords if keyword.arg)
    suffix = f"({', '.join(bases)})" if bases else ""
    lines = [f"class {node.name}{suffix}:"]

    docstring = ast.get_docstring(node)
    if docstring:
        if "\n" in docstring:
            lines.append('    """')
            for doc_line in docstring.splitlines():
                lines.append(f"    {doc_line}")
            lines.append('    """')
        else:
            lines.append(f'    """{docstring}"""')

    members: list[str] = []
    for child in node.body:
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        members.extend(_render_function(child, indent="    ", is_method=True))

    if not members:
        lines.append("    ...")
        return lines

    lines.extend(members)
    return lines


def _support_import_lines(rendered_lines: list[str]) -> list[str]:
    imports: list[str] = []
    rendered_text = "\n".join(rendered_lines)
    if "Any" in rendered_text:
        imports.append("from typing import Any")
    if "ast." in rendered_text:
        imports.append("import ast")
    if "Enum" in rendered_text:
        imports.append("from enum import Enum")
    return imports


def _render_placeholder(name: str, detail: str) -> list[str]:
    if detail == "class":
        return [f"class {name}:", "    ..."]
    if detail == "function":
        return [f"def {name}(*args: Any, **kwargs: Any) -> Any: ..."]
    return [f"{name}: Any"]


def _render_stub(tree: ast.Module, *, module_name: str, module_path: Path) -> str:
    core_modules = _load_core_definitions()
    module_index = core_modules.load_python_module_index(module_path)
    exported_names = dict.fromkeys(core_modules._python_module_public_names(module_index))
    local_nodes = {
        node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }

    body_lines: list[str] = []
    for name in exported_names:
        node = local_nodes.get(name)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body_lines.extend(_render_function(node))
            body_lines.append("")
            continue

        if isinstance(node, ast.ClassDef):
            body_lines.extend(_render_class(node))
            body_lines.append("")
            continue

        body_lines.extend(_render_placeholder(name, core_modules.python_module_symbol_detail(module_path, name)))
        body_lines.append("")

    lines = [
        "from __future__ import annotations",
        "",
        *_support_import_lines(body_lines),
        "",
        f'"""Generated fallback stub for {module_name}."""',
        "",
        *body_lines,
    ]

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    targets: list[Path] = []
    for module_name, target in TARGETS.items():
        source_path, tree = _load_tree(module_name)
        target.write_text(_render_stub(tree, module_name=module_name, module_path=source_path), encoding="utf-8")
        targets.append(target)

    subprocess.run(["uv", "run", "ruff", "check", "--fix", *map(str, targets)], check=True)
    subprocess.run(["uv", "run", "ruff", "format", *map(str, targets)], check=True)


if __name__ == "__main__":
    main()
