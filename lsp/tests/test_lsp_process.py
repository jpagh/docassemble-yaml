from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "demo_package"
QUESTIONS_ROOT = PACKAGE_FIXTURE_ROOT / "docassemble" / "demo" / "data" / "questions"
MAIN_PATH = QUESTIONS_ROOT / "main.yml"
WORKFLOW_PATH = PACKAGE_FIXTURE_ROOT / "docassemble" / "demo" / "workflow.py"


class _PipeCollector(threading.Thread):
    def __init__(self, stream: Any, sink: bytearray) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._sink = sink

    def run(self) -> None:
        while True:
            chunk = self._stream.read(4096)
            if not chunk:
                return
            self._sink.extend(chunk)


class _LspMessageReader(threading.Thread):
    def __init__(self, stream: Any, sink: queue.Queue[dict[str, Any]]) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._sink = sink
        self.error: BaseException | None = None

    def run(self) -> None:
        buffer = bytearray()

        try:
            while True:
                chunk = self._stream.read(4096)
                if not chunk:
                    return
                buffer.extend(chunk)

                while True:
                    header_end = buffer.find(b"\r\n\r\n")
                    if header_end == -1:
                        break

                    header_block = bytes(buffer[:header_end]).decode("ascii")
                    content_length: int | None = None
                    for line in header_block.split("\r\n"):
                        name, _, value = line.partition(":")
                        if name.lower() == "content-length":
                            content_length = int(value.strip())
                            break

                    if content_length is None:
                        raise ValueError("Missing Content-Length header")

                    message_end = header_end + 4 + content_length
                    if len(buffer) < message_end:
                        break

                    body = bytes(buffer[header_end + 4 : message_end])
                    del buffer[:message_end]
                    self._sink.put(json.loads(body.decode("utf-8")))
        except BaseException as exc:  # pragma: no cover - surfaced by test helper
            self.error = exc


class _LspSession:
    def __init__(
        self, cli_args: list[str] | None = None, *, cwd: Path | None = None, extra_pythonpath: Path | None = None
    ) -> None:
        self._cli_args = cli_args or []
        self._cwd = cwd or REPO_ROOT
        self._extra_pythonpath = extra_pythonpath
        self._messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self._pending: list[dict[str, Any]] = []
        self._next_id = 0
        self._stderr = bytearray()
        self._process: subprocess.Popen[bytes] | None = None
        self._stdout_reader: _LspMessageReader | None = None
        self._stderr_reader: _PipeCollector | None = None

    def __enter__(self) -> _LspSession:
        env = os.environ.copy()
        source_root = str(REPO_ROOT / "src")
        paths = [source_root]
        if self._extra_pythonpath is not None:
            paths.append(str(self._extra_pythonpath.resolve()))
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)

        self._process = subprocess.Popen(
            [sys.executable, "-m", "docassemble_lsp", "lsp", *self._cli_args],
            cwd=self._cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        assert self._process.stdin is not None
        assert self._process.stdout is not None
        assert self._process.stderr is not None

        self._stdout_reader = _LspMessageReader(self._process.stdout, self._messages)
        self._stdout_reader.start()
        self._stderr_reader = _PipeCollector(self._process.stderr, self._stderr)
        self._stderr_reader.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        process = self._require_process()
        if process.poll() is None:
            try:
                self.request("shutdown", None, timeout=2.0)
            except AssertionError:
                pass
            except BrokenPipeError:
                pass

            try:
                self.notify("exit", None)
            except BrokenPipeError:
                pass

            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2.0)

    def initialize(self, root_path: Path, *, capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "processId": None,
                "rootUri": root_path.resolve().as_uri(),
                "workspaceFolders": [{"uri": root_path.resolve().as_uri(), "name": root_path.name}],
                "capabilities": capabilities or {},
                "clientInfo": {"name": "pytest"},
            },
        )
        self.notify("initialized", {})
        return result

    def notify(self, method: str, params: dict[str, Any] | None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    def request(self, method: str, params: dict[str, Any] | None, *, timeout: float = 5.0) -> Any:
        self._next_id += 1
        request_id = self._next_id
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

        message = self._wait_for(lambda candidate: candidate.get("id") == request_id, timeout=timeout)
        if "error" in message:
            raise AssertionError(f"LSP request {method} failed: {message['error']}")
        return message.get("result")

    def wait_for_notification(
        self,
        method: str,
        *,
        timeout: float = 5.0,
        predicate: Any | None = None,
    ) -> dict[str, Any]:
        return self._wait_for(
            lambda candidate: (
                candidate.get("method") == method and (predicate(candidate) if predicate is not None else True)
            ),
            timeout=timeout,
        )

    def _send(self, payload: dict[str, Any]) -> None:
        process = self._require_process()
        assert process.stdin is not None
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        process.stdin.write(header)
        process.stdin.write(body)
        process.stdin.flush()

    def _wait_for(self, predicate: Any, *, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout

        while True:
            for index, candidate in enumerate(self._pending):
                if predicate(candidate):
                    return self._pending.pop(index)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(self._timeout_message())

            if self._stdout_reader is not None and self._stdout_reader.error is not None:
                raise AssertionError(f"LSP reader failed: {self._stdout_reader.error}") from self._stdout_reader.error

            try:
                candidate = self._messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise AssertionError(self._timeout_message()) from exc

            if predicate(candidate):
                return candidate
            self._pending.append(candidate)

    def _timeout_message(self) -> str:
        process = self._require_process()
        stderr = self._stderr.decode("utf-8", errors="replace").strip()
        parts = [f"Timed out waiting for LSP message; returncode={process.poll()}"]
        if self._pending:
            parts.append(f"pending={self._pending!r}")
        if stderr:
            parts.append(f"stderr={stderr}")
        return " | ".join(parts)

    def _require_process(self) -> subprocess.Popen[bytes]:
        if self._process is None:
            raise AssertionError("LSP process has not been started")
        return self._process


def _position(source: str, needle: str, occurrence: int = 1) -> tuple[int, int]:
    count = 0
    for line_number, line in enumerate(source.splitlines()):
        offset = 0
        while True:
            character = line.find(needle, offset)
            if character == -1:
                break
            count += 1
            if count == occurrence:
                return line_number, character + 1
            offset = character + len(needle)
    raise AssertionError(f"Could not find {needle!r} occurrence {occurrence}")


def _did_open_params(path: Path, text: str) -> dict[str, Any]:
    return {
        "textDocument": {
            "uri": path.resolve().as_uri(),
            "languageId": "yaml",
            "version": 1,
            "text": text,
        }
    }


def _wait_for_stderr_contains(session: _LspSession, substrings: list[str], *, timeout: float = 5.0) -> str:
    deadline = time.monotonic() + timeout

    while True:
        stderr = session._stderr.decode("utf-8", errors="replace")
        if all(substring in stderr for substring in substrings):
            return stderr

        process = session._require_process()
        if process.poll() is not None:
            raise AssertionError(f"LSP process exited before stderr contained expected text: {stderr}")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f"Timed out waiting for stderr text: {stderr}")

        time.sleep(min(0.01, remaining))


def test_lsp_process_publishes_and_clears_diagnostics_on_change(tmp_path: Path) -> None:
    source_path = tmp_path / "broken.yml"
    invalid_source = "---\nquestion: Hello\nfoo: bar\n"
    valid_source = "---\nquestion: Hello\n"
    source_path.write_text(invalid_source, encoding="utf-8")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, invalid_source))

        first_publish = session.wait_for_notification(
            "textDocument/publishDiagnostics",
            predicate=lambda message: message["params"]["uri"] == source_path.resolve().as_uri(),
        )
        assert [diagnostic["code"] for diagnostic in first_publish["params"]["diagnostics"]] == ["E301"]

        session.notify(
            "textDocument/didChange",
            {
                "textDocument": {"uri": source_path.resolve().as_uri(), "version": 2},
                "contentChanges": [{"text": valid_source}],
            },
        )

        second_publish = session.wait_for_notification(
            "textDocument/publishDiagnostics",
            predicate=lambda message: (
                message["params"]["uri"] == source_path.resolve().as_uri() and message["params"]["diagnostics"] == []
            ),
        )
        assert second_publish["params"]["diagnostics"] == []


def test_lsp_process_accepts_stdio_flag(tmp_path: Path) -> None:
    with _LspSession(["--stdio"]) as session:
        result = session.initialize(tmp_path)

    assert result["serverInfo"]["name"]


def test_lsp_process_logs_selected_base_modules_to_stderr(tmp_path: Path) -> None:
    with _LspSession(cli_args=["--log-level", "INFO"]) as session:
        session.initialize(tmp_path)
        stderr = _wait_for_stderr_contains(
            session,
            [
                "Using docassemble.base.util from",
                "Using docassemble.base.functions from",
            ],
        )

    assert "Using docassemble.base.util from" in stderr
    assert "Using docassemble.base.functions from" in stderr


def test_lsp_process_debug_log_level_emits_log_message(tmp_path: Path) -> None:
    with _LspSession(cli_args=["--log-level", "DEBUG"]) as session:
        session.initialize(tmp_path)
        stderr = _wait_for_stderr_contains(session, ["Log level set to DEBUG"])

    assert "Log level set to DEBUG" in stderr


def test_lsp_process_default_log_level_emits_log_message(tmp_path: Path) -> None:
    with _LspSession() as session:
        session.initialize(tmp_path)
        stderr = _wait_for_stderr_contains(session, ["Log level set to WARNING"])

    assert "Log level set to WARNING" in stderr


def test_lsp_process_publishes_field_shorthand_convention_when_enabled(tmp_path: Path) -> None:
    source_path = tmp_path / "shorthand.yml"
    source = "question: Hi\nfields:\n  - Name: user.name\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession(["--conventions", "C102"]) as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        publish = session.wait_for_notification(
            "textDocument/publishDiagnostics",
            predicate=lambda message: message["params"]["uri"] == source_path.resolve().as_uri(),
        )

    diagnostics = publish["params"]["diagnostics"]
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["C102"]


def test_lsp_process_offers_code_action_for_field_shorthand_convention(tmp_path: Path) -> None:
    source_path = tmp_path / "shorthand.yml"
    source = "question: Hi\nfields:\n  - Name: user.name\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession(["--conventions", "C102"]) as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        publish = session.wait_for_notification(
            "textDocument/publishDiagnostics",
            predicate=lambda message: message["params"]["uri"] == source_path.resolve().as_uri(),
        )

        actions = session.request(
            "textDocument/codeAction",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "range": {
                    "start": {"line": 2, "character": 0},
                    "end": {"line": 2, "character": len("  - Name: user.name")},
                },
                "context": {"diagnostics": publish["params"]["diagnostics"]},
            },
        )

    assert [action["title"] for action in actions] == [
        "Convert to explicit label/field keys",
        "Fix all auto-fixable docassemble-lsp issues",
    ]
    text_edits = actions[0]["edit"]["changes"][source_path.resolve().as_uri()]
    assert [text_edit["newText"] for text_edit in text_edits] == ["  - label: Name\n    field: user.name"]


def test_lsp_process_offers_source_fix_all_for_field_shorthand_conventions(tmp_path: Path) -> None:
    source_path = tmp_path / "shorthand.yml"
    source = "question: Hi\nfields:\n  - Name: user.name\n  - Age: user.age\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession(["--conventions", "C102"]) as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        publish = session.wait_for_notification(
            "textDocument/publishDiagnostics",
            predicate=lambda message: message["params"]["uri"] == source_path.resolve().as_uri(),
        )

        actions = session.request(
            "textDocument/codeAction",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "range": {
                    "start": {"line": 2, "character": 0},
                    "end": {"line": 2, "character": len("  - Name: user.name")},
                },
                "context": {
                    "diagnostics": publish["params"]["diagnostics"],
                    "only": ["source.fixAll"],
                },
            },
        )

    assert [action["title"] for action in actions] == ["Fix all auto-fixable docassemble-lsp issues"]
    text_edits = actions[0]["edit"]["changes"][source_path.resolve().as_uri()]
    assert [text_edit["newText"] for text_edit in text_edits] == [
        "  - label: Name\n    field: user.name",
        "  - label: Age\n    field: user.age",
    ]


def test_lsp_process_reads_conventions_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nconventions = ["C102"]\n',
        encoding="utf-8",
    )
    source_path = tmp_path / "shorthand.yml"
    source = "question: Hi\nfields:\n  - Name: user.name\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession(cwd=tmp_path) as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        publish = session.wait_for_notification(
            "textDocument/publishDiagnostics",
            predicate=lambda message: message["params"]["uri"] == source_path.resolve().as_uri(),
        )

    diagnostics = publish["params"]["diagnostics"]
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["C102"]


def test_lsp_process_returns_completions_for_open_document(tmp_path: Path) -> None:
    source_path = tmp_path / "metadata.yml"
    source = "metadata:\n  "
    source_path.write_text(source, encoding="utf-8")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        completions = session.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "position": {"line": 1, "character": 2},
            },
        )

    labels = {item["label"] for item in completions["items"]}
    assert "title" in labels
    assert "documentation" in labels


def test_lsp_process_returns_hover_for_known_key(tmp_path: Path) -> None:
    source_path = tmp_path / "hover.yml"
    source = "question: Hello\n"
    source_path.write_text(source, encoding="utf-8")
    line, character = _position(source, "question")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        hover = session.request(
            "textDocument/hover",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "position": {"line": line, "character": character},
            },
        )

    assert hover is not None
    assert "question" in hover["contents"]["value"]


def test_lsp_process_resolves_definition_across_fixture_workspace() -> None:
    source = MAIN_PATH.read_text(encoding="utf-8")
    line, character = _position(source, "case_title")

    with _LspSession() as session:
        session.initialize(PACKAGE_FIXTURE_ROOT)
        session.notify("textDocument/didOpen", _did_open_params(MAIN_PATH, source))

        locations = session.request(
            "textDocument/definition",
            {
                "textDocument": {"uri": MAIN_PATH.resolve().as_uri()},
                "position": {"line": line, "character": character},
            },
        )

    assert [(location["targetUri"], location["targetRange"]["start"]["line"]) for location in locations] == [
        (WORKFLOW_PATH.resolve().as_uri(), 0)
    ]


def test_lsp_process_returns_workspace_symbols_from_fixture_workspace() -> None:
    with _LspSession() as session:
        session.initialize(PACKAGE_FIXTURE_ROOT)

        symbols = session.request("workspace/symbol", {"query": "workflow_reset"})

    assert any(symbol["name"] == "workflow_reset" for symbol in symbols)


def test_lsp_process_returns_document_links_for_local_files(tmp_path: Path) -> None:
    included = tmp_path / "included.yml"
    included.write_text("question: Included\n", encoding="utf-8")
    source_path = tmp_path / "main.yml"
    source = 'include:\n  - "included.yml" # comment\n'
    source_path.write_text(source, encoding="utf-8")

    with _LspSession() as session:
        result = session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        links = session.request(
            "textDocument/documentLink",
            {"textDocument": {"uri": source_path.resolve().as_uri()}},
        )

    assert result["capabilities"]["documentLinkProvider"]["resolveProvider"] is False
    assert links == [
        {
            "range": {
                "start": {"line": 1, "character": source.splitlines()[1].index("included.yml")},
                "end": {
                    "line": 1,
                    "character": source.splitlines()[1].index("included.yml") + len("included.yml"),
                },
            },
            "target": included.resolve().as_uri(),
            "tooltip": "Open included.yml",
        }
    ]


def test_lsp_process_returns_document_links_for_modules_includes_and_static_files(tmp_path: Path) -> None:
    package_dir = tmp_path / "docassemble" / "demo"
    questions = package_dir / "data" / "questions"
    static = package_dir / "data" / "static"
    questions.mkdir(parents=True)
    static.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    helper = package_dir / "helper.py"
    helper.write_text("def do_stuff():\n    return None\n", encoding="utf-8")
    included = questions / "included.yml"
    included.write_text("question: Included\n", encoding="utf-8")
    stylesheet = static / "style.css"
    stylesheet.write_text("", encoding="utf-8")
    script = static / "app.js"
    script.write_text("", encoding="utf-8")
    source_path = questions / "main.yml"
    source = "include:\n  - included.yml\nmodules:\n  - .helper\nfeatures:\n  css:\n    - style.css\n  javascript:\n    - app.js\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        links = session.request(
            "textDocument/documentLink",
            {"textDocument": {"uri": source_path.resolve().as_uri()}},
        )

    targets_by_text = {
        source.splitlines()[link["range"]["start"]["line"]].strip().removeprefix("- "): link for link in links
    }
    assert targets_by_text["included.yml"]["target"] == included.resolve().as_uri()
    assert targets_by_text[".helper"]["target"] == helper.resolve().as_uri()
    assert targets_by_text["style.css"]["target"] == stylesheet.resolve().as_uri()
    assert targets_by_text["app.js"]["target"] == script.resolve().as_uri()
    assert targets_by_text["included.yml"]["tooltip"] == "Open included.yml"
    assert targets_by_text[".helper"]["tooltip"] == "Open helper.py"


def test_lsp_process_formats_document_over_protocol(tmp_path: Path) -> None:
    source_path = tmp_path / "format.yml"
    source = "---\ncode: |\n  x={'a':1}\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        edits = session.request(
            "textDocument/formatting",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "options": {"tabSize": 2, "insertSpaces": True},
            },
        )

    assert len(edits) == 1
    assert 'x = {"a": 1}' in edits[0]["newText"]


def test_lsp_process_formats_tabs_to_spaces_when_enabled(tmp_path: Path) -> None:
    source_path = tmp_path / "tabs.yml"
    source = "question:\tHi\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession(["--convert-tabs-to-spaces"]) as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        edits = session.request(
            "textDocument/formatting",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "options": {"tabSize": 2, "insertSpaces": True},
            },
        )

    assert len(edits) == 1
    assert edits[0]["newText"] == "question:  Hi\n"


def test_lsp_process_indents_new_fields_line_on_type_formatting(tmp_path: Path) -> None:
    source_path = tmp_path / "fields.yml"
    source = "fields:\n  - label: First\n\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        edits = session.request(
            "textDocument/onTypeFormatting",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "position": {"line": 2, "character": 0},
                "ch": "\n",
                "options": {"tabSize": 2, "insertSpaces": True},
            },
        )

    assert edits == [
        {
            "range": {
                "start": {"line": 2, "character": 0},
                "end": {"line": 2, "character": 0},
            },
            "newText": "    ",
        }
    ]


def test_lsp_process_indents_fields_block_scalar_line_on_type_formatting(tmp_path: Path) -> None:
    source_path = tmp_path / "fields-block-scalar.yml"
    source = "fields:\n  - code: |\n\n"
    source_path.write_text(source, encoding="utf-8")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        edits = session.request(
            "textDocument/onTypeFormatting",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "position": {"line": 2, "character": 0},
                "ch": "\n",
                "options": {"tabSize": 2, "insertSpaces": True},
            },
        )

    assert edits == [
        {
            "range": {
                "start": {"line": 2, "character": 0},
                "end": {"line": 2, "character": 0},
            },
            "newText": "      ",
        }
    ]


def test_lsp_process_semantic_tokens_capability_and_response(tmp_path: Path) -> None:
    source_path = tmp_path / "code.yml"
    source = "code: |\n  x = 1\n"
    source_path.write_text(source, encoding="utf-8")

    capabilities = {
        "textDocument": {
            "semanticTokens": {
                "requests": {"full": True},
                "tokenTypes": [],
                "tokenModifiers": [],
                "formats": ["relative"],
                "augmentsSyntaxTokens": True,
            }
        }
    }

    with _LspSession() as session:
        result = session.initialize(tmp_path, capabilities=capabilities)
        session.notify("textDocument/didOpen", _did_open_params(source_path, source))

        tokens = session.request(
            "textDocument/semanticTokens/full",
            {"textDocument": {"uri": source_path.resolve().as_uri()}},
        )

    legend = result["capabilities"]["semanticTokensProvider"]["legend"]
    # Semantic tokens are disabled (empty legend) so the TextMate grammar
    # provides all text-content highlighting.
    assert legend["tokenTypes"] == []

    # With no semantic tokens, data is always empty.
    assert tokens["data"] == []


def test_lsp_process_python_watched_file_updates_completions(tmp_path: Path) -> None:
    """Modifying a Python file and sending watched-file notification should update completions."""
    (tmp_path / "pyproject.toml").write_text("[tool.docassemble-lsp]\n", encoding="utf-8")
    pkg_dir = tmp_path / "docassemble" / "mypkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    helper = pkg_dir / "helper.py"
    helper.write_text(
        "from docassemble.base.util import DAObject\nclass Person(DAObject):\n    pass\n",
        encoding="utf-8",
    )

    yaml_path = tmp_path / "interview.yml"
    yaml_source = "---\nmodules:\n  - .helper\n---\nobjects:\n  - person: \n"
    yaml_path.write_text(yaml_source, encoding="utf-8")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(yaml_path, yaml_source))

        completions = session.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": yaml_path.resolve().as_uri()},
                "position": {"line": 5, "character": 12},
            },
        )
        labels = {item["label"] for item in completions["items"]}
        assert "Person" in labels

        helper.write_text(
            helper.read_text(encoding="utf-8") + "\nclass Employee(DAObject):\n    pass\n",
            encoding="utf-8",
        )

        session.notify(
            "workspace/didChangeWatchedFiles",
            {"changes": [{"uri": helper.resolve().as_uri(), "type": 2}]},
        )

        completions2 = session.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": yaml_path.resolve().as_uri()},
                "position": {"line": 5, "character": 12},
            },
        )
        labels2 = {item["label"] for item in completions2["items"]}
        assert "Employee" in labels2


def test_lsp_process_rebuilds_workspace_index_on_watched_file_change(tmp_path: Path) -> None:
    source_path = tmp_path / "interview.yml"
    initial_content = "---\ndef: orig_var\n"
    updated_content = "---\ndef: new_var\n"
    source_path.write_text(initial_content, encoding="utf-8")

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, initial_content))

        session.wait_for_notification("textDocument/publishDiagnostics")

        # Close the document so the watched file change reads from disk
        session.notify("textDocument/didClose", {"textDocument": {"uri": source_path.resolve().as_uri()}})

        source_path.write_text(updated_content, encoding="utf-8")

        session.notify(
            "workspace/didChangeWatchedFiles",
            {
                "changes": [
                    {
                        "uri": source_path.resolve().as_uri(),
                        "type": 2,
                    }
                ]
            },
        )

        symbols = session.request("workspace/symbol", {"query": "new_var"})

    assert any(symbol["name"] == "new_var" for symbol in symbols)


def test_lsp_process_unsaved_def_appears_in_workspace_symbols(tmp_path: Path) -> None:
    """Unsaved document with a new def should appear in workspace symbols."""
    source_path = tmp_path / "overlay.yml"
    unsaved_source = "---\ndef: unsaved_def\n"

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, unsaved_source))

        symbols = session.request("workspace/symbol", {"query": "unsaved_def"})

    assert any(symbol["name"] == "unsaved_def" for symbol in symbols)


def test_lsp_process_unsaved_symbol_disappears_on_close(tmp_path: Path) -> None:
    """Closing an unsaved document should remove its symbols from workspace symbols."""
    source_path = tmp_path / "overlay.yml"
    unsaved_source = "---\ndef: temp_def\n"

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, unsaved_source))

        symbols_open = session.request("workspace/symbol", {"query": "temp_def"})
        assert any(symbol["name"] == "temp_def" for symbol in symbols_open)

        session.notify("textDocument/didClose", {"textDocument": {"uri": source_path.resolve().as_uri()}})

        symbols_closed = session.request("workspace/symbol", {"query": "temp_def"})

    assert not any(symbol["name"] == "temp_def" for symbol in symbols_closed)


def test_lsp_process_unsaved_event_resolved_across_overlays(tmp_path: Path) -> None:
    """An event defined in an unsaved overlay should be findable by definition from another file."""
    trigger_path = tmp_path / "trigger.yml"
    trigger_source = '---\ncode: |\n  url_action("overlay_event")\n'
    trigger_path.write_text(trigger_source, encoding="utf-8")

    overlay_path = tmp_path / "library.yml"
    overlay_source = '---\nevent: "overlay_event"\nquestion: From overlay\n'

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(trigger_path, trigger_source))
        session.notify("textDocument/didOpen", _did_open_params(overlay_path, overlay_source))

        line, character = _position(trigger_source, "overlay_event")
        locations = session.request(
            "textDocument/definition",
            {
                "textDocument": {"uri": trigger_path.resolve().as_uri()},
                "position": {"line": line, "character": character},
            },
        )

    assert any(loc["targetUri"] == overlay_path.resolve().as_uri() for loc in locations)


def test_lsp_process_formats_malformed_document_returns_empty(tmp_path: Path) -> None:
    """Formatting a malformed YAML document should return empty edits."""
    source_path = tmp_path / "malformed.yml"
    malformed_source = "---\nkey: [unclosed list\n"

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, malformed_source))

        edits = session.request(
            "textDocument/formatting",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "options": {"tabSize": 2, "insertSpaces": True},
            },
        )

    assert edits == []


def test_lsp_process_formats_reader_error_returns_empty(tmp_path: Path) -> None:
    """Formatting a document with null bytes should not crash."""
    source_path = tmp_path / "reader_error.yml"
    malformed_source = '---\nkey: "\x00"\n'

    with _LspSession() as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(source_path, malformed_source))

        edits = session.request(
            "textDocument/formatting",
            {
                "textDocument": {"uri": source_path.resolve().as_uri()},
                "options": {"tabSize": 2, "insertSpaces": True},
            },
        )

    assert edits == []


def _create_ext_package(ext_dir: Path) -> None:
    """Create an external docassemble package with a DAObject subclass."""
    ext_pkg = ext_dir / "docassemble" / "external"
    ext_pkg.mkdir(parents=True)
    (ext_pkg / "__init__.py").write_text("", encoding="utf-8")
    (ext_pkg / "helpers.py").write_text(
        "from docassemble.base.util import DAObject\nclass ExternalPerson(DAObject):\n    pass\n",
        encoding="utf-8",
    )


def test_lsp_process_unsaved_modules_adds_external_completions(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Adding modules: docassemble.external.helpers to an unsaved overlay should trigger cross-package discovery."""
    (tmp_path / "pyproject.toml").write_text("[tool.docassemble-lsp]\n", encoding="utf-8")
    pkg_dir = tmp_path / "docassemble" / "mypkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    ext_dir = tmp_path_factory.mktemp("ext_pkg")
    _create_ext_package(ext_dir)

    yaml_path = tmp_path / "interview.yml"
    initial_source = "---\nobjects:\n  - person: \n"
    updated_source = "---\nmodules:\n  - docassemble.external.helpers\n---\nobjects:\n  - person: \n"
    yaml_path.write_text(initial_source, encoding="utf-8")

    with _LspSession(extra_pythonpath=ext_dir) as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(yaml_path, initial_source))

        completions_before = session.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": yaml_path.resolve().as_uri()},
                "position": {"line": 2, "character": 12},
            },
        )
        labels_before = {item["label"] for item in completions_before["items"]}

        session.notify(
            "textDocument/didChange",
            {
                "textDocument": {"uri": yaml_path.resolve().as_uri(), "version": 2},
                "contentChanges": [{"text": updated_source}],
            },
        )

        completions_after = session.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": yaml_path.resolve().as_uri()},
                "position": {"line": 5, "character": 12},
            },
        )
        labels_after = {item["label"] for item in completions_after["items"]}

    assert "ExternalPerson" not in labels_before
    assert "ExternalPerson" in labels_after


def test_lsp_process_unsaved_external_completions_survive_watched_file(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """External completions from unsaved overlays should survive a watched-file invalidation."""
    (tmp_path / "pyproject.toml").write_text("[tool.docassemble-lsp]\n", encoding="utf-8")
    pkg_dir = tmp_path / "docassemble" / "mypkg"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "data").mkdir()

    ext_dir = tmp_path_factory.mktemp("ext_pkg")
    _create_ext_package(ext_dir)

    yaml_path = tmp_path / "interview.yml"
    yaml_source = "---\nmodules:\n  - docassemble.external.helpers\n---\nobjects:\n  - person: \n"
    yaml_path.write_text(yaml_source, encoding="utf-8")

    dummy_py = tmp_path / "dummy_module.py"
    dummy_py.write_text("x = 1\n", encoding="utf-8")

    with _LspSession(extra_pythonpath=ext_dir) as session:
        session.initialize(tmp_path)
        session.notify("textDocument/didOpen", _did_open_params(yaml_path, yaml_source))

        completions_before = session.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": yaml_path.resolve().as_uri()},
                "position": {"line": 5, "character": 12},
            },
        )
        labels_before = {item["label"] for item in completions_before["items"]}
        assert "ExternalPerson" in labels_before

        session.notify(
            "workspace/didChangeWatchedFiles",
            {"changes": [{"uri": dummy_py.resolve().as_uri(), "type": 2}]},
        )

        completions_after = session.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": yaml_path.resolve().as_uri()},
                "position": {"line": 5, "character": 12},
            },
        )
        labels_after = {item["label"] for item in completions_after["items"]}

    assert "ExternalPerson" in labels_after
