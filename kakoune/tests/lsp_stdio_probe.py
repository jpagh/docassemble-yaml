"""Test-only transparent stdio recorder; the real kak-lsp still speaks to the server."""

import json
import os
import subprocess
import sys
import threading


def main():
    process = subprocess.Popen(
        [os.environ["DOCASSEMBLE_TEST_SERVER"], *sys.argv[1:]],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    lock = threading.Lock()
    with open(os.environ["DOCASSEMBLE_TEST_LOG"], "a") as log:
        log.write(
            json.dumps(
                {
                    "direction": "process",
                    "message": {
                        "serverPid": process.pid,
                        "recorderPid": os.getpid(),
                        "clientPid": os.getppid(),
                    },
                }
            )
            + "\n"
        )

    def relay(source, target, direction):
        while True:
            headers = []
            length = None
            while line := source.readline():
                headers.append(line)
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":", 1)[1])
                if line in (b"\r\n", b"\n"):
                    break
            if length is None:
                return
            body = source.read(length)
            with lock, open(os.environ["DOCASSEMBLE_TEST_LOG"], "a") as log:
                log.write(
                    json.dumps({"direction": direction, "message": json.loads(body)})
                    + "\n"
                )
            target.write(b"".join(headers) + body)
            target.flush()

    def receive():
        try:
            relay(sys.stdin.buffer, process.stdin, "client")
        finally:
            # A crashed/timed-out client must not leave a server waiting on stdin.
            process.stdin.close()

    incoming = threading.Thread(target=receive, daemon=True)
    incoming.start()
    try:
        relay(process.stdout, sys.stdout.buffer, "server")
    finally:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
