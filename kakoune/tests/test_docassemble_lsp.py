"""Real kak-lsp v22 configuration/stdio checks; no UI-menu claims or server mocks."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_highlighting import ROOT, Session, quote

KAK = shutil.which(os.environ.get("KAKOUNE_BIN", "kak"))
KAK_LSP = shutil.which(os.environ.get("KAK_LSP_BIN", "kak-lsp"))
GIALLO = shutil.which(os.environ.get("GIALLO_KAK_BIN", "giallo-kak"))
SERVER = shutil.which(os.environ.get("DOCASSEMBLE_LSP_BIN", "docassemble-lsp"))
PLUGIN = ROOT / "kakoune/rc/docassemble-lsp.kak"
FIXTURE = ROOT / "lsp/tests/fixtures/demo_package"


class JsonClient:
    """Real off-screen Kakoune window: observe rendered faces, not terminal pixels."""

    def __init__(self, kak, name, env):
        self.events = []
        self.errors = []
        self.process = subprocess.Popen(
            [kak, "-c", name, "-ui", "json", "-e", "rename-client probe"],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()
        self.process.stdin.write(
            json.dumps({"jsonrpc": "2.0", "method": "resize", "params": [40, 120]})
            + "\n"
        )
        self.process.stdin.flush()

    def read(self):
        for line in self.process.stdout:
            if line.strip():
                try:
                    self.events.append(json.loads(line))
                except json.JSONDecodeError:
                    self.errors.append(line)

    def close(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.process.stdin.close()
        self.reader.join(timeout=5)
        self.process.stdout.close()


def process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@unittest.skipUnless(KAK and KAK_LSP, "SKIP: LSP wiring requires kak and kak-lsp v22")
class DocassembleLspTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="docassemble-lsp-kak-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.log = self.home / "protocol.jsonl"
        self.name = "da23-" + uuid.uuid4().hex[:8]
        # Upstream launches kak/kak-lsp by name internally; honor overrides.
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        (bin_dir / "kak").symlink_to(KAK)
        (bin_dir / "kak-lsp").symlink_to(KAK_LSP)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("KAK_LSP_PROJECT_ROOT_")
            and key != "KAK_LSP_FORCE_PROJECT_ROOT"
        }
        self.env.update(
            HOME=str(self.home),
            XDG_CONFIG_HOME=str(self.home / ".config"),
            PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
            DOCASSEMBLE_TEST_SERVER=SERVER or "missing",
            DOCASSEMBLE_TEST_LOG=str(self.log),
        )
        # Exercise quoting of executable overrides too.
        self.proxy = self.home / "server with 'quotes'"
        self.proxy.write_text(
            "#!/bin/sh\nexec "
            + shlex.quote(sys.executable)
            + " "
            + shlex.quote(str(Path(__file__).with_name("lsp_stdio_probe.py")))
            + ' "$@"\n'
        )
        self.proxy.chmod(0o755)
        (bin_dir / "docassemble-lsp").symlink_to(self.proxy)
        rc = self.home / "upstream.kak"
        rc.write_bytes(subprocess.check_output([KAK_LSP], env=self.env, timeout=5))
        self.process = subprocess.Popen(
            [KAK, "-d", "-s", self.name],
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(self.close)
        self.wait_for(lambda: self.send("nop", check=False).returncode == 0)
        self.run_kak(f"source {quote(rc)}\nremove-hooks global lsp-filetype-yaml")
        self.run_kak(
            f"source {quote(PLUGIN)}\n"
            f"set-option global docassemble_lsp_command {quote(self.proxy)}\n"
            f"source {quote(ROOT / 'kakoune/rc/docassemble.kak')}\nlsp-enable"
        )

    def send(self, commands, check=True):
        return subprocess.run(
            [KAK, "-p", self.name],
            input=commands,
            text=True,
            env=self.env,
            check=check,
            capture_output=True,
            timeout=5,
        )

    def run_kak(self, commands):
        response = self.home / (uuid.uuid4().hex + ".response")
        if hasattr(self, "buffer") and not hasattr(self, "ui"):
            commands = (
                f"evaluate-commands -buffer {quote(self.buffer)} %{{ {commands} }}"
            )
        if hasattr(self, "ui"):
            commands = f"evaluate-commands -client probe %{{ {commands} }}"
        self.send(
            f"try %{{ {commands}\necho -to-file {quote(response)} ok }} "
            f"catch %{{ echo -to-file {quote(response)} %val{{error}} }}"
        )
        self.wait_for(lambda: response.exists() and bool(response.read_text()))
        self.assertEqual(response.read_text().strip(), "ok", commands)

    def wait_for(self, condition):
        # Generous: the root gate runs this alongside CPU-saturating suites.
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.05)
        debug = self.home / "debug-timeout"
        self.send(
            f"try %{{ evaluate-commands -buffer *debug* %{{ write -force {quote(debug)} }} }}",
            check=False,
        )
        time.sleep(0.1)
        self.fail(
            f"Timed out; protocol={self.messages()}; debug={debug.read_text() if debug.exists() else None}"
        )

    def messages(self):
        if not self.log.exists():
            return []
        # Ignore a final partial line while the recorder appends.
        return [
            json.loads(line)
            for line in self.log.read_text().splitlines(keepends=True)
            if line.endswith("\n")
        ]

    def option(self, name):
        output = self.home / "option"
        self.run_kak(f"echo -to-file {quote(output)} %opt{{{name}}}")
        return output.read_text().strip()

    def open(self, path, manual=False):
        self.run_kak(f"edit {quote(path)}")
        self.buffer = path
        if manual:
            self.run_kak("docassemble-enable")
        # No client idle events in a daemon: explicitly synchronize.
        self.run_kak("lsp-did-open")

    def replace(self, text):
        source = self.home / "replacement"
        source.write_text(text)
        self.run_kak(
            f"execute-keys '%<esc>'\nexecute-keys {quote('|cat ' + shlex.quote(str(source)) + '<ret>')}\n"
            "lsp-did-change"
        )

    def response(self, method):
        messages = self.messages()
        ids = {
            entry["message"]["id"]
            for entry in messages
            if entry["direction"] == "client"
            and entry["message"].get("method") == method
        }
        return [
            entry["message"]
            for entry in messages
            if entry["direction"] == "server" and entry["message"].get("id") in ids
        ]

    def request_features(self):
        count = len(self.response("textDocument/hover"))
        self.run_kak("select 1.2,1.2\nlsp-hover")
        self.wait_for(lambda: len(self.response("textDocument/hover")) > count)
        hover = self.response("textDocument/hover")[-1]
        self.assertIn("question", json.dumps(hover["result"]).lower())
        count = len(self.response("textDocument/completion"))
        self.run_kak("lsp-send textDocument/completion 1 3 1")
        self.wait_for(lambda: len(self.response("textDocument/completion")) > count)
        completion = self.response("textDocument/completion")[-1]
        result = completion["result"]
        items = result["items"] if isinstance(result, dict) else result
        self.assertIn("question", [item["label"].rstrip(": ") for item in items])

    def close(self):
        self.send("try %{ lsp-exit }\nkill!", check=False)
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def attach_window(self):
        self.ui = JsonClient(KAK, self.name, self.env)
        self.addCleanup(self.ui.close)
        self.wait_for(lambda: any(e["method"] == "draw" for e in self.ui.events))
        # Requests are explicit, not dependent on an off-screen window's idle hooks.
        self.run_kak("remove-hooks global lsp\nremove-hooks global lsp-breadcrumbs")

    def request(self, method, commands):
        count = len(self.response(method))
        self.run_kak(commands)
        self.wait_for(lambda: len(self.response(method)) > count)
        response = self.response(method)[-1]
        self.assertNotIn("error", response)
        return response["result"]

    def current_file(self):
        output = self.home / "current-file"
        self.run_kak(f"echo -to-file {quote(output)} %val{{buffile}}")
        return output.read_text().strip()

    def buffer_text(self):
        output = self.home / "buffer-content"
        self.run_kak(f"evaluate-commands -no-hooks %{{ write -force {quote(output)} }}")
        return output.read_text()

    @unittest.skipUnless(SERVER, "SKIP: real protocol test requires docassemble-lsp")
    def test_cross_file_workflows_spaces_and_shutdown(self):
        package = self.home / "demo package with spaces"
        shutil.copytree(FIXTURE, package)
        questions = package / "docassemble/demo/data/questions"
        main = questions / "main.yml"
        self.attach_window()
        # Opening a Python definition target must not require unrelated pylsp.
        self.run_kak("remove-hooks global lsp-filetype-python")
        self.open(main)
        self.wait_for(lambda: self.response("initialize"))
        initialize = next(
            e["message"]
            for e in self.messages()
            if e["message"].get("method") == "initialize"
        )
        self.assertEqual(initialize["params"]["rootUri"], package.as_uri())
        for line, column, target, target_line in (
            (16, 38, questions / "x_events.yml", 15),
            (11, 8, package / "docassemble/demo/workflow.py", 0),
        ):
            self.open(main)
            result = self.request(
                "textDocument/definition",
                f"select {line}.{column},{line}.{column}\nlsp-definition",
            )
            self.assertTrue(
                any(
                    loc.get("targetUri", loc.get("uri")) == target.as_uri()
                    and loc.get("targetSelectionRange", loc.get("range"))["start"][
                        "line"
                    ]
                    == target_line
                    for loc in result
                ),
                result,
            )
            self.wait_for(lambda target=target: self.current_file() == str(target))
        self.open(questions / "x_events.yml")
        references = self.request(
            "textDocument/references", "select 16.12,16.12\nlsp-references"
        )
        self.assertIn(main.as_uri(), {loc["uri"] for loc in references})
        self.assertTrue(
            any(
                loc["uri"] == main.as_uri() and loc["range"]["start"]["line"] == 21
                for loc in references
            )
        )
        # Read the real client's capability listing, not an inferred feature list.
        self.wait_for(lambda: self.current_file() != str(questions / "x_events.yml"))
        self.open(questions / "x_events.yml")
        self.run_kak("lsp-capabilities")
        self.wait_for(
            lambda: any(
                e["method"] == "info_show" and "LSP commands supported" in str(e)
                for e in self.ui.events
            )
        )
        listing = str(
            next(
                e
                for e in reversed(self.ui.events)
                if e["method"] == "info_show" and "LSP commands supported" in str(e)
            )
        )
        for command in (
            "lsp-definition",
            "lsp-references",
            "lsp-formatting",
            "lsp-code-actions",
            "lsp-semantic-tokens",
        ):
            self.assertIn(command, listing)
        self.assertNotIn("lsp-range-formatting", listing)
        self.assertNotIn("lsp-document-link", listing)
        self.assertNotIn("lsp-on-type-formatting", listing)
        self.assertFalse(
            initialize["params"]["capabilities"]["workspace"]["workspaceFolders"]
        )
        lifecycle = next(
            e["message"] for e in self.messages() if e["direction"] == "process"
        )
        command = subprocess.check_output(
            ["ps", "-p", str(lifecycle["clientPid"]), "-o", "command="], text=True
        )
        self.assertIn("kak-lsp", command)
        pids = list(lifecycle.values())
        self.assertTrue(all(process_alive(pid) for pid in pids))
        self.run_kak("lsp-exit")
        self.wait_for(lambda: all(not process_alive(pid) for pid in pids))
        self.assertTrue(
            any(e["message"].get("method") == "exit" for e in self.messages())
        )
        self.send("kill!")
        self.assertEqual(self.process.wait(timeout=5), 0)
        self.assertEqual(self.ui.process.wait(timeout=5), 0)
        self.assertEqual(self.ui.errors, [])
        self.assertNotEqual(self.send("nop", check=False).returncode, 0)

    @unittest.skipUnless(SERVER, "SKIP: real protocol test requires docassemble-lsp")
    def test_formatting_and_code_action_apply_unsaved_edits(self):
        path = self.home / "package with spaces/data/questions/edit.yml"
        path.parent.mkdir(parents=True)
        original = "code: |\n  total=1+2\n"
        path.write_text(original)
        self.attach_window()
        self.open(path)
        self.wait_for(lambda: self.response("initialize"))
        result = self.request("textDocument/formatting", "lsp-formatting-sync")
        self.assertTrue(result)
        self.wait_for(lambda: "total = 1 + 2" in self.buffer_text())
        # A whole-document edit must also cover the original trailing newline;
        # otherwise its own trailing newline is appended and every format adds a
        # blank line.
        edit = result[0]
        # The edit replaces document content and leaves the source's own final
        # line break outside its range, so no format can add a blank line.
        self.assertEqual(edit["range"]["end"], {"line": 1, "character": 11})
        self.assertFalse(edit["newText"].endswith("\n"))
        # The client applies the returned edit through its own deferred script, so
        # poll for the converged buffer instead of sampling mid-application.
        self.wait_for(lambda: self.buffer_text() == edit["newText"] + "\n")
        self.assertEqual(self.buffer_text(), "code: |\n  total = 1 + 2\n")
        # Idempotent: formatting the already-formatted buffer changes nothing.
        self.assertEqual(
            self.request("textDocument/formatting", "lsp-formatting-sync"), []
        )
        self.assertEqual(path.read_text(), original)
        self.replace("question: Hello\nfields:\n  - field: user_name\n")
        self.wait_for(lambda: "E415" in json.dumps(self.messages()))
        actions = self.request(
            "textDocument/codeAction", "select 3.5,3.5\nlsp-code-actions-sync quickfix"
        )
        self.assertEqual(len(actions), 1, actions)
        self.assertIn("edit", actions[0])
        expected = "question: Hello\nfields:\n  - field: user_name\n    label: \n"
        self.wait_for(lambda: self.buffer_text() == expected)
        self.assertEqual(path.read_text(), original)
        self.assertEqual(self.ui.errors, [])

    @unittest.skipUnless(
        SERVER and GIALLO, "SKIP: semantic interaction requires server and giallo-kak"
    )
    def test_optional_semantic_tokens_preserve_giallo_faces(self):
        config = self.home / ".config/giallo.kak"
        shutil.copytree(ROOT / "kakoune/grammars", config / "grammars")
        (config / "themes").mkdir()
        shutil.copy(ROOT / "kakoune/fixtures/scope-probe.json", config / "themes")
        (config / "config.toml").write_text(
            'themes_path = "~/.config/giallo.kak/themes"\n'
            + (ROOT / "kakoune/config.toml").read_text()
        )
        (self.home / "bin/giallo-kak").symlink_to(GIALLO)
        rc = self.home / "giallo.kak"
        rc.write_bytes(
            subprocess.check_output([GIALLO, "init"], env=self.env, timeout=5)
        )
        self.attach_window()
        self.run_kak(
            f"source {quote(rc)}\nset-option global giallo_auto_enable false\n"
            "set-option global giallo_theme docassemble-probe"
        )
        self.addCleanup(self.run_kak, "giallo-stop-server")
        path = self.home / "data/questions/sample.yml"
        path.parent.mkdir(parents=True)
        shutil.copy(ROOT / "grammars/fixtures/sample.yml", path)
        self.open(path)
        self.wait_for(lambda: "giallo_" in self.option("giallo_hl_ranges"))
        time.sleep(0.3)  # Same upstream bootstrap settling as Session.start().
        self.run_kak("set-option buffer giallo_last_update_ms 0\ngiallo-force-update")
        self.wait_for(lambda: "46." in self.option("giallo_hl_ranges"))
        self.assertNotIn("|", self.option("lsp_semantic_tokens_ranges"))
        self.assertFalse(self.response("textDocument/semanticTokens/full"))
        before = self.option("giallo_hl_ranges")
        self.wait_for(lambda: self.rendered_keyword_color() == "rgb:00ffff")
        result = self.request("textDocument/semanticTokens/full", "lsp-semantic-tokens")
        self.assertEqual(result["data"], [])
        legend = self.response("initialize")[0]["result"]["capabilities"][
            "semanticTokensProvider"
        ]["legend"]
        self.assertEqual(legend, {"tokenTypes": [], "tokenModifiers": []})
        self.assertNotIn("|", self.option("lsp_semantic_tokens_ranges"))
        self.assertEqual(self.option("giallo_hl_ranges"), before)
        draws = sum(e["method"] == "draw" for e in self.ui.events)
        self.run_kak("select 1.2,1.2")
        self.wait_for(
            lambda: sum(e["method"] == "draw" for e in self.ui.events) > draws
        )
        self.assertEqual(self.rendered_keyword_color(), "rgb:00ffff")
        self.assertEqual(self.ui.errors, [])
        # No overlapping semantic face exists in this server version. This is
        # non-interference evidence, not a safe precedence rule for future tokens.

    def rendered_keyword_color(self):
        draws = [e for e in self.ui.events if e["method"] == "draw"]
        if not draws:
            return None
        for line in draws[-1]["params"][0]:
            for atom in line:
                if "return" in atom["contents"]:
                    return atom["face"]["fg"]
        return None

    @unittest.skipUnless(SERVER, "SKIP: real protocol test requires docassemble-lsp")
    def test_fixture_root_and_language_id(self):
        # Exercise the documented PATH route, still recording the real server.
        self.run_kak("set-option global docassemble_lsp_command docassemble-lsp")
        self.open(FIXTURE / "docassemble/demo/data/questions/main.yml")
        self.wait_for(lambda: self.response("initialize"))
        initialize = next(
            e["message"]
            for e in self.messages()
            if e["message"].get("method") == "initialize"
        )
        self.assertEqual(initialize["params"]["rootUri"], FIXTURE.as_uri())
        self.wait_for(
            lambda: any(
                e["message"].get("method") == "textDocument/didOpen"
                for e in self.messages()
            )
        )
        opened = next(
            e["message"]
            for e in self.messages()
            if e["message"].get("method") == "textDocument/didOpen"
        )
        self.assertEqual(opened["params"]["textDocument"]["languageId"], "docassemble")
        self.assertEqual(self.option("filetype"), "docassemble")
        config = tomllib.loads(self.option("lsp_servers"))
        self.assertEqual(list(config), ["docassemble"])
        self.assertEqual(config["docassemble"]["command"], "docassemble-lsp")
        self.assertEqual(config["docassemble"]["args"], ["lsp"])

    def check_saved_and_unsaved_features(self, path, manual):
        path.parent.mkdir(parents=True, exist_ok=True)
        saved = "question: Hello\nfields: wrong\n"
        path.write_text(saved)
        self.open(path, manual=manual)
        self.wait_for(lambda: "Diagnostic" in self.option("lsp_inline_diagnostics"))
        self.assertIn("E406", json.dumps(self.messages()))
        self.request_features()
        self.replace("question: Unsaved\nfieldz: wrong\n")
        self.wait_for(
            lambda: any(
                e["message"].get("method") == "textDocument/publishDiagnostics"
                and "fieldz" in json.dumps(e["message"])
                for e in self.messages()
            )
        )
        self.wait_for(lambda: "Diagnostic" in self.option("lsp_inline_diagnostics"))
        self.request_features()
        self.assertEqual(path.read_text(), saved)
        self.assertTrue(
            any(
                e["message"].get("method") == "textDocument/didChange"
                for e in self.messages()
            )
        )

    @unittest.skipUnless(SERVER, "SKIP: real protocol test requires docassemble-lsp")
    def test_automatic_saved_and_unsaved_diagnostics_completion_hover(self):
        self.check_saved_and_unsaved_features(
            self.home / "pkg/data/questions/main.yaml", False
        )

    @unittest.skipUnless(SERVER, "SKIP: real protocol test requires docassemble-lsp")
    def test_manual_saved_and_unsaved_diagnostics_completion_hover(self):
        self.check_saved_and_unsaved_features(self.home / "interview.yml", True)
        initialize = next(
            e["message"]
            for e in self.messages()
            if e["message"].get("method") == "initialize"
        )
        self.assertEqual(initialize["params"]["rootUri"], self.home.as_uri())

    def test_missing_server_nonfatal_disable_and_reload(self):
        self.run_kak(
            "set-option global docassemble_lsp_command /missing/docassemble-lsp"
        )
        path = self.home / "data/questions/main.yaml"
        path.parent.mkdir(parents=True)
        path.write_text("question: Hello\n")
        self.open(path)
        self.assertEqual(self.option("filetype"), "docassemble")
        self.assertEqual(self.option("indentwidth"), "2")
        self.assertEqual(self.option("lsp_servers"), "")
        debug = self.home / "debug"
        self.run_kak(
            f"evaluate-commands -buffer *debug* %{{ write -force {quote(debug)} }}"
        )
        self.assertIn("set-option buffer docassemble_lsp_command", debug.read_text())
        self.run_kak(f"source {quote(PLUGIN)}\nsource {quote(PLUGIN)}")
        self.run_kak(f"set-option buffer docassemble_lsp_command {quote(self.proxy)}")
        self.assertIn("[docassemble]", self.option("lsp_servers"))
        self.run_kak("docassemble-lsp-disable")
        self.assertEqual(self.option("lsp_servers"), "")
        self.assertEqual(self.option("filetype"), "docassemble")
        self.run_kak("set-option buffer filetype yaml")
        self.assertNotEqual(self.option("lsp_language_id"), "docassemble")


@unittest.skipUnless(
    KAK and KAK_LSP and GIALLO,
    "SKIP: missing-server highlighting requires kak, kak-lsp and giallo-kak",
)
class MissingServerHighlightingTests(unittest.TestCase):
    def test_missing_server_keeps_real_giallo_ranges(self):
        with tempfile.TemporaryDirectory(prefix="docassemble-no-server-") as temp:
            session = Session(Path(temp).resolve(), KAK, GIALLO)
            try:
                session.start()
                rc = session.home / "lsp.kak"
                rc.write_bytes(
                    subprocess.check_output([KAK_LSP], env=session.env, timeout=5)
                )
                session.send(
                    f"source {quote(rc)}\nremove-hooks global lsp-filetype-yaml\n"
                    f"source {quote(PLUGIN)}\n"
                    "set-option buffer docassemble_lsp_command /missing/docassemble-lsp\nlsp-enable"
                )
                session.send(
                    "set-option buffer giallo_last_update_ms 0\ngiallo-force-update"
                )
                session.wait_for(lambda: session.color(21, 7) == "00FFFF")
                output = session.home / "lsp-servers"
                session.send(f"echo -to-file {quote(output)} %opt{{lsp_servers}}")
                deadline = time.monotonic() + 20
                while not output.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertEqual(output.read_text().strip(), "")
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
