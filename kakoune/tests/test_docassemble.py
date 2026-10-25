"""Shared detection cases and real-plugin lifecycle, without a giallo server."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_highlighting import ROOT, quote

PLUGIN = ROOT / "kakoune/rc/docassemble.kak"
CASES = json.loads((ROOT / "fixtures/detection/paths.json").read_text())
KAK = shutil.which(os.environ.get("KAKOUNE_BIN", "kak"))


class DetectionTests(unittest.TestCase):
    def decision(self, path, **options):
        source = PLUGIN.read_text()
        shell = re.search(
            r"# BEGIN detection:.*?\n(.*?)# END detection", source, re.DOTALL
        )[1]
        env = dict(
            os.environ,
            kak_buffile=path,
            kak_opt_filetype="yaml",
            kak_opt_docassemble_disabled="false",
            kak_opt_docassemble_automatic="false",
        )
        env.update(options)
        return subprocess.check_output(["sh", "-eu", "-c", shell], env=env, text=True)

    def test_shared_corpus_through_plugin_shell(self):
        for case in CASES:
            with self.subTest(path=case["path"]):
                self.assertEqual(
                    "docassemble-enable" in self.decision(case["path"]), case["kakoune"]
                )

    def test_opt_out_and_user_language_are_respected(self):
        path = "data/questions/main.yml"
        self.assertEqual(self.decision(path, kak_opt_docassemble_disabled="true"), "")
        self.assertEqual(self.decision(path, kak_opt_filetype="python"), "")

    def test_automatic_rename_out_deactivates(self):
        self.assertIn(
            "docassemble-disable",
            self.decision("elsewhere.yml", kak_opt_docassemble_automatic="true"),
        )


@unittest.skipUnless(KAK, "SKIP: real plugin lifecycle requires kak (not giallo-kak)")
class DocassembleLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="docassemble-lifecycle-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.env = dict(
            os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config")
        )
        self.name = "da22-" + uuid.uuid4().hex[:8]
        self.process = subprocess.Popen(
            [KAK, "-d", "-s", self.name],
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(self.stop_session)
        # Generous: the root gate runs this alongside CPU-saturating suites.
        deadline = time.monotonic() + 20
        while subprocess.run(
            [KAK, "-p", self.name],
            input="nop",
            check=False,
            timeout=5,
            text=True,
            env=self.env,
            capture_output=True,
        ).returncode:
            if time.monotonic() > deadline:
                self.fail("Kakoune daemon failed to start")
            time.sleep(0.02)
        self.run_kak(f"source {quote(PLUGIN)}")

    def stop_session(self):
        subprocess.run(
            [KAK, "-p", self.name],
            input="kill!",
            check=False,
            timeout=5,
            text=True,
            env=self.env,
            capture_output=True,
        )
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def run_kak(self, commands):
        response = self.home / (uuid.uuid4().hex + ".response")
        if hasattr(self, "buffer"):
            commands = (
                f"evaluate-commands -buffer {quote(self.buffer)} %{{ {commands} }}"
            )
        subprocess.run(
            [KAK, "-p", self.name],
            input=f"try %{{ {commands}\necho -to-file {quote(response)} ok }} catch %{{ echo -to-file {quote(response)} %val{{error}} }}",
            text=True,
            env=self.env,
            check=True,
            capture_output=True,
            timeout=5,
        )
        # Generous: the root gate runs this alongside CPU-saturating suites.
        deadline = time.monotonic() + 20
        while not response.exists():
            if time.monotonic() > deadline:
                self.fail(f"Kakoune response timeout: {commands}")
            time.sleep(0.01)
        self.assertEqual(response.read_text().strip(), "ok", commands)

    def options(self, *names):
        output = self.home / "options"
        self.run_kak(
            "echo -to-file "
            + quote(output)
            + " "
            + " '|' ".join(f"%opt{{{name}}}" for name in names)
        )
        return [value.strip() for value in output.read_text().strip().split("|")]

    def open_path(self, relative):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("question: hello\n")
        self.run_kak(f"edit {quote(path)}")
        self.buffer = path
        return path

    def mock_giallo(self):
        self.run_kak("""
            declare-option str giallo_lang previous-language
            declare-option bool giallo_enabled false
            declare-option range-specs giallo_hl_ranges
            declare-option int enable_calls 0
            declare-option int disable_calls 0
            define-command giallo-enable %{
                set-option buffer giallo_enabled true
                set-option -add buffer enable_calls 1
                add-highlighter -override buffer/giallo ranges giallo_hl_ranges
            }
            define-command giallo-disable %{
                set-option buffer giallo_enabled false
                set-option -add buffer disable_calls 1
                remove-highlighter buffer/giallo
            }
        """)

    def test_every_corpus_path_uses_real_hooks(self):
        for i, case in enumerate(CASES):
            with self.subTest(path=case["path"]):
                # Prefixing keeps absolute/Windows cases inside the sandbox.
                self.open_path(
                    f"case-{i}/" + case["path"].replace("\\", "/").lstrip("/")
                )
                self.assertEqual(
                    self.options("filetype")[0] == "docassemble", case["kakoune"]
                )
                if not case["kakoune"]:
                    self.assertEqual(self.options("docassemble_active"), ["false"])

    def test_plain_yaml_and_explicit_activation_restore_settings(self):
        self.mock_giallo()
        self.open_path("elsewhere.yml")
        self.run_kak(
            "set-option buffer indentwidth 7; set-option buffer tabstop 9; set-option buffer comment_line '//'; set-option buffer comment_block_begin '/*'; set-option buffer comment_block_end '*/'"
        )
        names = (
            "filetype",
            "indentwidth",
            "tabstop",
            "comment_line",
            "comment_block_begin",
            "comment_block_end",
            "giallo_lang",
            "giallo_enabled",
        )
        original = self.options(*names)
        self.assertEqual(
            original, ["yaml", "7", "9", "//", "/*", "*/", "previous-language", "false"]
        )
        self.run_kak("docassemble-enable; docassemble-enable")
        self.assertEqual(
            self.options(*names),
            ["docassemble", "2", "2", "#", "", "", "docassemble", "true"],
        )
        self.assertEqual(self.options("enable_calls"), ["1"])
        self.run_kak("docassemble-disable; docassemble-disable")
        self.assertEqual(self.options(*names), original)
        self.assertEqual(self.options("disable_calls"), ["1"])
        self.run_kak("docassemble-detect")
        self.assertEqual(self.options(*names), original)
        self.assertEqual(self.options("enable_calls", "disable_calls"), ["1", "1"])
        self.run_kak(
            "add-highlighter buffer/giallo ranges giallo_hl_ranges; remove-highlighter buffer/giallo"
        )

    def test_filetype_changes_reload_and_rename(self):
        self.mock_giallo()
        self.open_path("pkg/data/questions/sub/dir/file.yaml")
        self.assertEqual(self.options("filetype", "enable_calls"), ["docassemble", "1"])
        self.run_kak("edit!; docassemble-detect; set-option buffer filetype yaml")
        self.assertEqual(self.options("filetype", "giallo_enabled"), ["yaml", "false"])
        self.run_kak("docassemble-detect")
        self.assertEqual(self.options("filetype"), ["yaml"])
        self.run_kak(
            "set-option buffer filetype docassemble; set-option buffer filetype docassemble"
        )
        self.assertEqual(self.options("filetype", "enable_calls"), ["docassemble", "2"])
        self.run_kak("set-option buffer filetype python")
        self.assertEqual(
            self.options("filetype", "giallo_enabled"), ["python", "false"]
        )
        self.run_kak("set-option buffer filetype yaml; docassemble-enable")
        # Explicit activation survives rename; automatic activation follows paths.
        self.run_kak(
            f"rename-buffer -file {quote(self.home / 'manual.yaml')}; docassemble-detect"
        )
        self.buffer = self.home / "manual.yaml"
        self.assertEqual(self.options("filetype"), ["docassemble"])
        self.open_path("other/data/questions/main.yml")
        self.run_kak(
            f"rename-buffer -file {quote(self.home / 'outside.yml')}; docassemble-detect"
        )
        self.buffer = self.home / "outside.yml"
        self.assertEqual(self.options("filetype", "giallo_enabled"), ["yaml", "false"])
        self.run_kak(
            f"rename-buffer -file {quote(self.home / 'other/data/questions/renamed.yaml')}; docassemble-detect"
        )
        self.buffer = self.home / "other/data/questions/renamed.yaml"
        self.assertEqual(
            self.options("filetype", "giallo_enabled"), ["docassemble", "true"]
        )

    def test_sourcing_twice_keeps_one_hook_and_existing_activation(self):
        self.mock_giallo()
        self.open_path("data/questions/main.yml")
        self.run_kak(f"source {quote(PLUGIN)}; source {quote(PLUGIN)}")
        self.assertEqual(self.options("enable_calls"), ["1"])
        self.run_kak("""
            declare-option int detect_calls 0
            define-command -override docassemble-detect %{ set-option -add buffer detect_calls 1 }
            set-option buffer filetype yaml
            set-option buffer filetype text
        """)
        # First event tears down, second event calls detection exactly once.
        self.assertEqual(self.options("detect_calls"), ["1"])
        self.run_kak("remove-hooks global docassemble; set-option buffer filetype yaml")
        self.assertEqual(self.options("detect_calls"), ["1"])

    def test_window_yaml_highlighter_follows_filetype(self):
        path = self.home / "data/questions/window.yaml"
        path.parent.mkdir(parents=True)
        path.write_text("question: hello\n")
        output = self.home / "window-result"
        commands = f"""
            source {quote(PLUGIN)}
            edit {quote(path)}
            # This fails if a competing built-in YAML highlighter remains.
            add-highlighter window/yaml group
            remove-highlighter window/yaml
            docassemble-disable
            # Standard YAML highlighting must have been recreated.
            remove-highlighter window/yaml
            set-option buffer filetype docassemble
            add-highlighter window/yaml group
            echo -to-file {quote(output)} ok
        """
        subprocess.run(
            [
                KAK,
                "-ui",
                "dummy",
                "-e",
                f"try %{{ {commands} }} catch %{{ echo -to-file {quote(output)} %val{{error}} }}; quit!",
            ],
            env=self.env,
            check=True,
            timeout=10,
            capture_output=True,
        )
        self.assertEqual(output.read_text().strip(), "ok")

    def test_preexisting_giallo_and_direct_filetype_restore(self):
        self.mock_giallo()
        self.open_path("elsewhere.yml")
        self.run_kak(
            "set-option buffer filetype python; giallo-enable; set-option buffer filetype docassemble"
        )
        self.assertEqual(
            self.options("giallo_lang", "giallo_enabled"), ["docassemble", "true"]
        )
        self.run_kak("docassemble-disable")
        self.assertEqual(
            self.options("filetype", "giallo_lang", "giallo_enabled"),
            ["python", "previous-language", "true"],
        )

    def test_missing_and_failing_giallo_are_soft(self):
        self.open_path("data/questions/main.yaml")
        self.assertEqual(
            self.options("filetype", "indentwidth", "comment_line"),
            ["docassemble", "2", "#"],
        )
        self.run_kak("docassemble-disable")
        self.mock_giallo()
        self.run_kak(
            "define-command -override giallo-enable %{ fail unsupported-buffer }; docassemble-enable"
        )
        self.assertEqual(
            self.options("filetype", "indentwidth", "comment_line"),
            ["docassemble", "2", "#"],
        )
        self.run_kak("docassemble-disable")
        self.assertEqual(self.options("filetype"), ["yaml"])


if __name__ == "__main__":
    unittest.main()
