"""Real kak-lsp v22 configuration/stdio checks; no UI-menu claims or server mocks."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
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
        if hasattr(self, "buffer"):
            commands = (
                f"evaluate-commands -buffer {quote(self.buffer)} %{{ {commands} }}"
            )
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
