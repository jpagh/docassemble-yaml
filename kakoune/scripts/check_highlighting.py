"""Bounded real-Kakoune/giallo smoke check, not a cross-engine parity test."""

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


class Session:
    def __init__(self, home, kak, giallo, omitted=None):
        self.home = home
        self.kak = kak
        self.name = "da21-" + uuid.uuid4().hex[:8]
        self.buffer = home / "pkg/data/questions/sub/dir/sample.yaml"
        self.buffer.parent.mkdir(parents=True)
        self.buffer.write_bytes((ROOT / "grammars/fixtures/sample.yml").read_bytes())
        config = home / ".config/giallo.kak"
        config.mkdir(parents=True)
        shutil.copytree(ROOT / "kakoune/grammars", config / "grammars")
        if omitted:
            (config / "grammars" / f"{omitted}-injection.json").unlink()
        (config / "themes").mkdir()
        shutil.copy(ROOT / "kakoune/fixtures/scope-probe.json", config / "themes")
        (config / "config.toml").write_text(
            'themes_path = "~/.config/giallo.kak/themes"\n'
            + (ROOT / "kakoune/config.toml").read_text()
        )
        # Upstream invokes both executables by name internally; honor overrides too.
        bin_dir = home / "bin"
        bin_dir.mkdir()
        (bin_dir / "kak").symlink_to(kak)
        (bin_dir / "giallo-kak").symlink_to(giallo)
        self.env = dict(
            os.environ,
            HOME=str(home),
            XDG_CONFIG_HOME=str(home / ".config"),
            PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
            GIALLO_DEBUG_FILE=str(home / "commands"),
        )
        rc = home / "giallo.kak"
        rc.write_bytes(
            subprocess.check_output([giallo, "init"], env=self.env, timeout=10)
        )
        self.process = subprocess.Popen(
            [kak, "-n", "-d", "-s", self.name, str(self.buffer)],
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.faces = {"default": "default"}
        self.ranges = []
        self.rc = rc

    def send(self, commands):
        subprocess.run(
            [self.kak, "-p", self.name],
            input=f"evaluate-commands -buffer {quote(self.buffer)} %{{ {commands} }}\n",
            text=True,
            env=self.env,
            check=True,
            timeout=5,
            capture_output=True,
        )

    def start(self):
        deadline = time.monotonic() + 5
        while True:
            try:
                self.send("nop")
                break
            except subprocess.CalledProcessError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.05)
        self.send(
            f"source {quote(self.rc)}\n"
            "set-option global giallo_auto_enable false\n"
            "set-option buffer giallo_theme docassemble-probe\n"
            f"source {quote(ROOT / 'kakoune/rc/docassemble.kak')}"
        )
        self.wait_for(lambda: self.color(5, 1) == "FF0000")
        # Let upstream's asynchronous initial handshakes settle before one explicit
        # refresh. Overlapping bootstrap FIFO writes can concatenate snapshots.
        time.sleep(0.3)
        self.send("set-option buffer giallo_last_update_ms 0\ngiallo-force-update")
        self.wait_for(lambda: self.max_line() == 46)

    def snapshot(self):
        commands = self.home / "commands"
        if commands.exists():
            for name, color in re.findall(
                r"set-face global (\w+) %\{rgb:([0-9a-fA-F]+)", commands.read_text()
            ):
                self.faces[name] = color.upper()
        output = self.home / "ranges"
        self.send(
            "nop %sh{ printf '%s' \"$kak_opt_giallo_hl_ranges\" > "
            + shlex.quote(str(output))
            + " }"
        )
        if output.exists():
            self.ranges = [
                (int(line), int(start), int(end), face)
                for line, start, end, face in re.findall(
                    r"(\d+)\.(\d+),\d+\.(\d+)\|([\w]+)", output.read_text()
                )
            ]

    def color(self, line, column):
        for row, start, end, face in self.ranges:
            if row == line and start <= column <= end:
                return self.faces.get(face, face)
        return None

    def max_line(self):
        return max((row for row, *_ in self.ranges), default=0)

    def wait_for(self, condition):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            self.snapshot()
            if condition():
                return
            time.sleep(0.1)
        raise AssertionError(
            f"Highlight timeout; ranges={self.ranges}; faces={self.faces}"
        )

    def close(self):
        try:
            self.send("try %{ giallo-stop-server }\nkill!")
        finally:
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def check(kak, giallo):
    for omitted in (None, "python", "jinja", "mako"):
        with tempfile.TemporaryDirectory(prefix="docassemble-kak-") as temp:
            session = Session(Path(temp).resolve(), kak, giallo, omitted)
            try:
                session.start()
                probes = [
                    (14, 9),
                    (16, 12),
                    (17, 6),
                    (20, 3),
                    (21, 7),
                    (24, 22),
                    (29, 3),
                    (35, 3),
                    (46, 1),
                ]
                observed = [session.color(*position) for position in probes]
                print(f"omitted={omitted}: {observed}")
                if omitted is None:
                    assert observed == [
                        "0000FF",
                        "999999",
                        "FF00FF",
                        "00FFFF",
                        "00FFFF",
                        "00FFFF",
                        "00FF00",
                        "FFFF00",
                        "FF0000",
                    ], observed
                    original = session.buffer.read_bytes()
                    # Replace buffer content, not the file: Unicode plus unsaved edit.
                    fixture = ROOT / "kakoune/fixtures/unicode.yml"
                    keys = "|cat " + shlex.quote(str(fixture)) + "<ret>"
                    session.send(f"execute-keys '%<esc>'\nexecute-keys {quote(keys)}")
                    session.send(
                        "set-option buffer giallo_last_update_ms 0\ngiallo-force-update"
                    )
                    session.wait_for(lambda session=session: session.max_line() == 10)
                    # Kakoune columns are UTF-8 bytes, not codepoints or UTF-16.
                    assert session.color(3, 13) == "default"
                    assert session.color(3, 14) == "0000FF"  # ${ after café + emoji
                    assert session.color(3, 27) == "FF00FF"  # {{ after café + emoji
                    assert session.color(3, 37) == "FF00FF"
                    assert session.color(6, 12) == "00FF00"
                    assert session.color(9, 6) == "999999"  # no injection into comment
                    assert session.color(10, 1) == "FF0000"  # back to YAML
                    session.send(
                        "select 3.1,3.37\nexecute-keys 'c  café 😀 no expression<esc>'"
                    )
                    session.send(
                        "set-option buffer giallo_last_update_ms 0\ngiallo-force-update"
                    )
                    session.wait_for(
                        lambda session=session: session.color(3, 14) == "default"
                    )
                    assert session.color(10, 1) == "FF0000"
                    assert session.buffer.read_bytes() == original, (
                        "Probe unexpectedly saved the buffer"
                    )
                elif omitted == "python":
                    assert session.color(20, 3) != "00FFFF"
                elif omitted == "jinja":
                    assert session.color(17, 6) != "FF00FF"
                elif omitted == "mako":
                    assert session.color(14, 9) == "0000FF"
            finally:
                session.close()


def main():
    kak = shutil.which(os.environ.get("KAKOUNE_BIN", "kak"))
    giallo = shutil.which(os.environ.get("GIALLO_KAK_BIN", "giallo-kak"))
    if not kak or not giallo:
        print(
            "SKIP: Kakoune/giallo highlighting check requires kak and giallo-kak on PATH "
            "(or KAKOUNE_BIN/GIALLO_KAK_BIN). Packaging checks still run."
        )
        return
    print(subprocess.check_output([kak, "-version"], text=True).strip())
    print(subprocess.check_output([giallo, "--version"], text=True).strip())
    check(str(Path(kak).resolve()), str(Path(giallo).resolve()))
    print(
        "PASS: plugin activation, giallo shared boundaries, injection controls, unsaved Unicode buffer"
    )


if __name__ == "__main__":
    main()
