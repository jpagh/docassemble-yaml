"""Lower the VS Code TextMate grammars to a Fresh (syntect) syntax.

Fresh highlights with syntect, whose ``.sublime-syntax`` loader understands a
subset of Sublime's format:

  * ``match``/``include`` rules, ``push``/``pop``/``set`` and inline
    dynamically-pushed contexts
  * ``captures`` (plain scope names), ``meta_scope``, ``meta_content_scope``
  * ``variables``, ``embed``/``escape``, ``with_prototype`` and the reserved
    top-level ``prototype`` context
  * cross-syntax references only as ``include: scope:source.foo``

It does **not** understand ``begin``/``end``, ``contentName``, nested
``patterns`` inside captures, ``applyEndPatternLast`` or the TextMate
``include: source.foo`` form.  This script lowers those constructs so the
Docassemble YAML grammar keeps the highlighting the VS Code extension ships.

The source of truth stays ``vscode/syntaxes/*.tmLanguage.json``; run this
script after editing them::

    uv run --project lsp python fresh/scripts/build_syntax.py

The generated ``fresh/grammars/Docassemble.sublime-syntax`` is committed so
the language pack can be installed without Python.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
VSCODE_SYNTAXES = REPO_ROOT / "vscode" / "syntaxes"
DEFAULT_OUTPUT = REPO_ROOT / "fresh" / "grammars" / "Docassemble.sublime-syntax"

# TextMate `include: source.foo` forms that name a grammar syntect ships.
# Everything else cross-syntax is dropped rather than guessed at.
SCOPE_INCLUDES = {
    "source.python": "scope:source.python",
    "source.yaml": "scope:source.yaml",
    "text.html.basic": "scope:text.html.basic",
}

# YAML repository keys we cannot reuse verbatim:
#   * `prototype` is reserved by Sublime/syntect (auto-injected everywhere)
#   * `block-python` is a dangling include in the upstream grammar
YAML_RENAMES = {"prototype": "yaml_prototype"}
YAML_DROPS = {"block-python"}


class Lowerer:
    """Lowers one TextMate grammar into syntect-style contexts."""

    def __init__(
        self,
        prefix: str = "",
        context_rename: dict[str, str] | None = None,
        drop_contexts: set[str] | None = None,
        include_overrides: dict[str, str] | None = None,
    ) -> None:
        self.prefix = prefix
        self.context_rename = context_rename or {}
        self.drop_contexts = drop_contexts or set()
        self.include_overrides = include_overrides or {}
        self.contexts: dict[str, list[dict[str, Any]]] = {}

    # -- names -----------------------------------------------------------

    def context_name(self, key: str) -> str:
        if key in self.context_rename:
            return self.context_rename[key]
        return f"{self.prefix}_{key}" if self.prefix else key

    def context_ref(self, key: str) -> str | None:
        if key in self.drop_contexts:
            return None
        # syntect resolves same-syntax references by bare context name; the
        # Sublime `#name` spelling parses to an empty name and silently
        # matches nothing.
        return self.context_name(key)

    # -- includes --------------------------------------------------------

    def rewrite_include(self, include: str) -> str | None:
        if include in self.include_overrides:
            return self.include_overrides[include]
        if include.startswith("#"):
            return self.context_ref(include[1:])
        if include in ("$self", "$base"):
            return self.context_name("main")
        base, _, _sub = include.partition("#")
        if base in SCOPE_INCLUDES:
            return SCOPE_INCLUDES[base]
        if base.startswith(("source.", "text.")):
            return f"scope:{base}"
        # Local-only references (e.g. mako's `comment.block`) have no target
        # in the Fresh grammar; dropping them is better than a dangling
        # reference that syntect silently ignores.
        return None

    # -- rules -----------------------------------------------------------

    def lower(self, grammar: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        for key, body in grammar.get("repository", {}).items():
            if key in self.drop_contexts:
                continue
            self.contexts[self.context_name(key)] = self.lower_context(body)
        self.contexts[self.context_name("main")] = self.lower_rules(
            grammar.get("patterns", [])
        )
        return self.contexts

    def lower_context(self, body: Any) -> list[dict[str, Any]]:
        if isinstance(body, dict) and not any(
            k in body for k in ("begin", "match", "include")
        ):
            return self.lower_rules(body.get("patterns", []))
        return self.lower_rules([body])

    def lower_rules(self, rules: list[Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for rule in rules:
            out.extend(self.lower_rule(rule))
        return out

    def lower_rule(self, rule: dict[str, Any]) -> list[dict[str, Any]]:
        if rule.get("disabled"):
            return []
        if "include" in rule:
            ref = self.rewrite_include(rule["include"])
            return [{"include": ref}] if ref else []
        if "begin" in rule:
            return [self.lower_begin_end(rule)]
        if "match" in rule:
            return [self.lower_match(rule)]
        if "patterns" in rule:
            return self.lower_rules(rule["patterns"])
        return []

    def lower_match(self, rule: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {"match": rule["match"]}
        captures = self.lower_captures(rule.get("captures"))
        name = rule.get("name")
        if name:
            out["scope"] = name
        if captures:
            out["captures"] = captures
        return out

    def lower_begin_end(self, rule: dict[str, Any]) -> dict[str, Any]:
        """TextMate begin/end -> match + push of an inline context."""
        name = rule.get("name")
        # TextMate (and vscode-textmate) fall back to a shared `captures` map
        # for both delimiters when `beginCaptures`/`endCaptures` are absent;
        # the Jinja grammar relies on this for its `{% %}` delimiters.
        captures = self.lower_captures(
            rule.get("beginCaptures") or rule.get("captures")
        )

        outer: dict[str, Any] = {"match": rule["begin"]}
        if name:
            outer["scope"] = name
        if captures:
            outer["captures"] = captures

        body: list[dict[str, Any]] = []
        if rule.get("end") is not None:
            end: dict[str, Any] = {"match": rule["end"], "pop": True}
            end_captures = self.lower_captures(
                rule.get("endCaptures") or rule.get("captures")
            )
            if end_captures:
                end["captures"] = end_captures
            body.append(end)

        special: list[dict[str, Any]] = []
        if name:
            special.append({"meta_scope": name})
        if rule.get("contentName"):
            special.append({"meta_content_scope": rule["contentName"]})
        content = self.lower_rules(rule.get("patterns", []))

        # TextMate tries `end` before the content patterns unless
        # `applyEndPatternLast` says otherwise.  With the end rule last, an
        # embedded grammar (e.g. Python inside `${...}`) would consume the
        # closing delimiter as an error token and never pop.
        if rule.get("applyEndPatternLast"):
            inner = special + content + body
        else:
            inner = special + body + content

        outer["push"] = inner
        return outer

    def lower_captures(
        self, captures: dict[str, Any] | list[Any] | None
    ) -> dict[int, str] | None:
        if not captures:
            return None
        if isinstance(captures, list):
            captures = {str(index): value for index, value in enumerate(captures)}
        out: dict[int, str] = {}
        for index, capture in captures.items():
            name = None
            if isinstance(capture, dict):
                name = capture.get("name")
                # TextMate allows nested patterns inside a capture; syntect
                # only stores a scope name here, so the nested patterns are
                # dropped.
            elif isinstance(capture, str):
                name = capture
            if name:
                # syntect reads capture keys with yaml-rust's `as_i64`, which
                # only accepts real YAML integers -- a quoted "1" is silently
                # ignored.
                out[int(index)] = name
        return out or None


def build() -> dict[str, Any]:
    yaml_tm = json.loads((VSCODE_SYNTAXES / "yaml.tmLanguage.json").read_text())
    mako_tm = json.loads((VSCODE_SYNTAXES / "mako.tmLanguage.json").read_text())
    jinja_tm = json.loads((VSCODE_SYNTAXES / "jinja.tmLanguage.json").read_text())
    py_injection = json.loads((VSCODE_SYNTAXES / "python-injection.json").read_text())

    yaml_contexts = Lowerer(
        context_rename=YAML_RENAMES,
        drop_contexts=YAML_DROPS,
        include_overrides={
            # The VS Code grammar embeds Mako directly; point those at the
            # inlined Mako contexts instead.
            "source.mako": "mako_main",
        },
    ).lower(yaml_tm)
    mako_contexts = Lowerer(prefix="mako").lower(mako_tm)
    jinja_contexts = Lowerer(prefix="jinja").lower(jinja_tm)

    # Wherever the VS Code grammar embeds `source.mako`, also try Jinja: the
    # two template dialects are syntactically distinct and the extension ships
    # a grammar for each.  Hanging the include off the Mako root reaches the
    # nested embedding sites (block scalars) that a top-level patch misses.
    mako_contexts["mako_main"] = [{"include": "jinja_main"}] + mako_contexts[
        "mako_main"
    ]

    # The docassemble fork renames the block-scalar body's upstream
    # `string.unquoted.block.yaml` scope to `source.mako` and wraps the
    # content in the Mako grammar.  Under vscode-textmate the zero-width
    # wrapper never engages and the content reads as a plain scalar, so the
    # fork loses the string scope; keep the upstream string scope and keep
    # Mako/Jinja as content patterns (their `${...}`/`{{...}}` rules still
    # fire, and the block reads as a string in colour schemes).
    for rule in yaml_contexts.get("block-scalar", []):
        if isinstance(rule.get("push"), list):
            for inner in rule["push"]:
                if inner.get("scope") == "source.mako":
                    inner["scope"] = "string.unquoted.block.yaml"
                for body in (
                    inner.get("push", []) if isinstance(inner.get("push"), list) else []
                ):
                    if body.get("meta_scope") == "source.mako":
                        body["meta_scope"] = "string.unquoted.block.yaml"

    # The YAML comment rule ends with the zero-width TextMate idiom
    # `(?!\\G)`.  Lowered verbatim, syntect pops the context at end of line
    # but leaves parser state that makes its non-consuming-push loop guard
    # skip the first character of the next line -- visibly, the first key
    # after a comment loses its scopes.  `$` has the same effect for a
    # line comment and keeps the parser state clean.
    for rule in yaml_contexts.get("comment", []):
        if isinstance(rule.get("push"), list):
            for inner in rule["push"]:
                if inner.get("match") == "(?!\\G)":
                    inner["match"] = "$"

    # The Python injection grammar (`injectionSelector:
    # L:source.docassemble.yaml`) is lowered to a named context that the YAML
    # node contexts include explicitly.  A reserved `prototype` would inject
    # into *every* context including block scalars, where the `code: |` rule
    # would outrank the scalar's own end pattern and swallow the lines that
    # follow the scalar.
    injection = Lowerer(include_overrides={"source.mako": "mako_main"})
    python_injection = injection.lower_rules(py_injection.get("patterns", []))

    for node_context in ("block-node", "flow-node"):
        yaml_contexts[node_context] = [{"include": "python_injection"}] + yaml_contexts[
            node_context
        ]

    contexts: dict[str, list[dict[str, Any]]] = {"main": yaml_contexts.pop("main")}
    contexts.update(yaml_contexts)
    contexts.update(mako_contexts)
    contexts.update(jinja_contexts)
    contexts["python_injection"] = python_injection

    return {
        "name": "Docassemble",
        "file_extensions": ["dyml"],
        "scope": "source.docassemble.yaml",
        "version": 2,
        "contexts": contexts,
    }


HEADER = (
    "# Generated by fresh/scripts/build_syntax.py from\n"
    "# vscode/syntaxes/{yaml,mako,jinja}.tmLanguage.json and\n"
    "# python-injection.json. Do not edit by hand; regenerate instead.\n"
)


def render(grammar: dict[str, Any]) -> str:
    """Serialize a built grammar the way the committed file is written."""
    body = yaml.safe_dump(
        grammar, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    return HEADER + "%YAML 1.2\n---\n" + body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="output .sublime-syntax"
    )
    args = parser.parse_args()

    rendered = render(build())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(f"wrote {args.output} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
