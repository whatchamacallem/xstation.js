# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests mcp_stdio.py as a process, started on pipes the way an external
# agent starts it, on a root in build/ that holds a copy of the checkout's
# settings.json: a session answered against the tools of API/mcp/tools.json,
# text outside ASCII in and out as `utf-8` whatever the locale, and a line
# that is not JSON ending the process with exit code 1 and a traceback on
# stderr, its texts against the gold.

import harness, json, os, select, shutil, subprocess, sys, tempfile, unittest
from typing import Any, IO, cast

# The root of the checkout.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# Where the child writes the bytecode of the modules it imports.
_PYCACHE_PATH = os.path.join(_BUILD_PATH, "pycache")

# The settings file of the checkout, which holds a valid settings object.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# The name of the settings file in a root.
_SETTINGS_NAME = "settings.json"

# The script an external agent starts.
_STDIO_PATH = os.path.join(_ROOT_PATH, "python", "mcp_stdio.py")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_mcp_stdio_process"

# The most seconds a wait on the child takes, a default chosen by its writer.
_CHILD_SECONDS: int = harness.gold_get(f"{_GOLD_ID}.child_seconds")

# The most bytes read from the output of the child at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The first line of the traceback the child writes when it raises.
_TRACEBACK_HEAD = "Traceback (most recent call last):\n"

# A ping whose id is a letter outside ASCII, as a client writes it.
_WIDE_LINE = '{"jsonrpc":"2.0","id":"\xe9","method":"ping"}'

# The response to it, in the `utf-8` codec MCP's stdio transport requires.
_WIDE_REPLY = '{"jsonrpc":"2.0","id":"\xe9","result":{}}'

# The encoding the child is told its streams have, which `utf-8` overrides.
_ENCODING_NARROW = "ascii"

# A client's `initialize` request, which opens a session.
_INITIALIZE_LINE = (
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":'
    '{"protocolVersion":"2025-06-18","capabilities":{},'
    '"clientInfo":{"name":"xsjs-test","version":"1"}}}'
)

# The response to it: the pinned revision, `tools`, the server's identity.
_INITIALIZE_REPLY = (
    '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",'
    '"capabilities":{"tools":{}},'
    '"serverInfo":{"name":"xsjs-server","version":"0"}}}'
)

# The notification that follows a client's `initialize`.
_INITIALIZED_LINE = '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# A client's `tools/list` request, after the notification.
_LIST_LINE = '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

# A line that is not JSON, with the newline the loop reads with it.
_MALFORMED_LINE = '{"jsonrpc"\n'

# The start of the traceback line of the decoder's error.
_WIRE_PREFIX = "jslb.WireError: "


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# Reads the tool entries of the server side of the API file.
def _entries_read() -> list[dict[str, Any]]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data["server"]["result"]["tools"]


# The response to `tools/list`: the server tools of the API file, no permit.
def _list_reply() -> str:
    tools = [
        {
            "name": entry["name"],
            "description": entry["description"],
            "inputSchema": entry["inputSchema"],
        }
        for entry in _entries_read()
    ]
    response = {"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}}
    return json.dumps(response, ensure_ascii=False, separators=(",", ":"))


# A session in order: each line the client sends and the reply due, if any.
def _session_steps() -> list[tuple[str, str | None]]:
    return [
        (_INITIALIZE_LINE, _INITIALIZE_REPLY),
        (_INITIALIZED_LINE, None),
        (_LIST_LINE, _list_reply()),
    ]


# Starts the script on a root with pipes on its streams, told they are ASCII.
def _child_start(root: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, _STDIO_PATH, "--root", root],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            "PYTHONPYCACHEPREFIX": _PYCACHE_PATH,
            "PYTHONIOENCODING": _ENCODING_NARROW,
        },
    )


# Kills the child unless it has ended, reaps it and closes its pipes.
def _child_stop(process: subprocess.Popen[bytes]) -> None:
    process.kill()
    process.wait(_CHILD_SECONDS)
    for stream in (process.stdin, process.stdout, process.stderr):
        cast(IO[bytes], stream).close()


# Writes text to the input of the child and flushes it.
def _line_write(process: subprocess.Popen[bytes], text: str) -> None:
    stdin = cast(IO[bytes], process.stdin)
    stdin.write(text.encode("utf-8"))
    stdin.flush()


# Reads the output of the child up to a newline, each wait bounded.
def _line_read(process: subprocess.Popen[bytes]) -> str:
    descriptor = cast(IO[bytes], process.stdout).fileno()
    data = b""
    while not data.endswith(b"\n"):
        ready, _, _ = select.select([descriptor], [], [], _CHILD_SECONDS)
        if not ready:
            raise AssertionError(f"no output for {_CHILD_SECONDS} s")
        chunk = os.read(descriptor, _READ_BYTES)
        if not chunk:
            raise AssertionError(f"the output ended after {data!r}")
        data += chunk
    return data.decode("utf-8")


# Tests the script as a process, on pipes, as an external agent runs it.
class TestProcess(unittest.TestCase):
    # Makes a root in `build/` that holds a copy of the checkout's settings.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name
        path = os.path.join(self.root, _SETTINGS_NAME)
        shutil.copyfile(_SETTINGS_PATH, path)

    # Starts the script on the root and stops it when the test ends.
    def child_start(self) -> subprocess.Popen[bytes]:
        process = _child_start(self.root)
        self.addCleanup(_child_stop, process)
        return process

    # A session replays line for line, then closing stdin exits with 0.
    def test_process_replay(self) -> None:
        process = self.child_start()
        for sent, reply in _session_steps():
            _line_write(process, sent + "\n")
            if reply is not None:
                self.assertEqual(_line_read(process), reply + "\n")
        output, errors = process.communicate(timeout=_CHILD_SECONDS)
        self.assertEqual((process.returncode, output, errors), (0, b"", b""))

    # Text outside ASCII comes in and goes out as `utf-8`, whatever the locale.
    def test_process_wide(self) -> None:
        process = self.child_start()
        _line_write(process, _WIDE_LINE + "\n")
        self.assertEqual(_line_read(process), _WIDE_REPLY + "\n")
        output, errors = process.communicate(timeout=_CHILD_SECONDS)
        self.assertEqual((process.returncode, output, errors), (0, b"", b""))

    # A line that is not JSON exits with 1 and a traceback on stderr.
    def test_process_malformed(self) -> None:
        process = self.child_start()
        output, errors = process.communicate(
            _MALFORMED_LINE.encode("utf-8"), timeout=_CHILD_SECONDS
        )
        self.assertEqual((process.returncode, output), (1, b""))
        text: str = errors.decode("utf-8")
        self.assertTrue(text.startswith(_TRACEBACK_HEAD))
        lines = text.splitlines()
        reasons = [
            line[len(_WIRE_PREFIX) :]
            for line in lines
            if line.startswith(_WIRE_PREFIX)
        ]
        self.assertEqual(reasons, [_text_get("jslb_text_not_json_delimiter")])
        self.assertEqual(
            lines[-1],
            "ValueError: " + _text_get("mcp_stdio_line_malformed_process"),
        )
