# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the stdio loop on text streams: the transcript DATA/07_mcp_stdio.txt
# replayed against the tools of API/mcp/tools.json, a permit tool refused and
# never run, a plain tool run, an output flushed for each response, and a
# line that is not a JSON object ending the loop with an exception. Then tests
# the script as a process started the way an external agent starts it, on a
# root in build/ that holds a copy of the checkout's settings.json.

import contextlib, functools, io, json, mcp, mcp_stdio, os, select, shutil
import subprocess, sys, tempfile, unittest
from collections.abc import Callable
from i18n import i18n
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

# The transcript of an external agent driving the server over stdio.
_TRANSCRIPT_PATH = os.path.join(_ROOT_PATH, "DATA", "07_mcp_stdio.txt")

# The direction of a transcript line that the client sends.
_CLIENT_DIRECTION = "CLIENT->STDIO"

# The most seconds a wait on the child takes, a default chosen by its writer.
_CHILD_SECONDS = 30

# The most bytes read from the output of the child at once.
_READ_BYTES = 65536

# The first line of the traceback the child writes when it raises.
_TRACEBACK_HEAD = "Traceback (most recent call last):\n"

# The schema of a tool that takes nothing.
_EMPTY_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

# A ping request as a client writes it.
_PING_LINE = '{"jsonrpc":"2.0","id":1,"method":"ping"}'

# The response to it.
_PING_REPLY = '{"jsonrpc":"2.0","id":1,"result":{}}'

# A call of a permit tool.
_PERMIT_LINE = (
    '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":'
    '{"name":"source_put","arguments":{"name":"a.py","text":"x"}}}'
)

# The response that refuses it.
_PERMIT_REPLY = (
    '{"jsonrpc":"2.0","id":2,"error":{"code":-32000,"message":'
    '"source_put needs a permit and stdio has no UI to ask"}}'
)

# A call of a tool that needs no permit.
_PLAIN_LINE = (
    '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":'
    '{"name":"plain","arguments":{}}}'
)

# The response to it.
_PLAIN_REPLY = (
    '{"jsonrpc":"2.0","id":3,"result":{"content":'
    '[{"type":"text","text":"plain"}],"isError":false}}'
)

# The notification that follows a client's `initialize`.
_INITIALIZED_LINE = '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# A line that is not JSON, with the newline the loop reads with it.
_MALFORMED_LINE = '{"jsonrpc"\n'


# Reads the tool entries of the server side of the API file.
def _entries_read() -> list[dict[str, Any]]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data["server"]["result"]["tools"]


# Builds a tool from an entry of the API file.
def _tool_make(entry: dict[str, Any]) -> mcp.Tool:
    permit = entry.get("_meta", {}).get("xsjs", {}).get("permit", False)
    return mcp.Tool(
        entry["name"], entry["description"], entry["inputSchema"], permit
    )


# Reads the transcript in order: the direction and the text of each line.
def _transcript_steps() -> list[tuple[str, str]]:
    steps: list[tuple[str, str]] = []
    with open(_TRANSCRIPT_PATH, encoding="utf-8") as file:
        for line in file.read().splitlines():
            if line.startswith("#"):
                continue
            _, direction, text = line.split(" ", 2)
            steps.append((direction, text))
    return steps


# Reads the transcript: the lines the client sends, the lines expected back.
def _transcript_read() -> tuple[list[str], list[str]]:
    sent: list[str] = []
    expected: list[str] = []
    for direction, text in _transcript_steps():
        if direction == _CLIENT_DIRECTION:
            sent.append(text)
        else:
            expected.append(text)
    return sent, expected


# Runs the loop on the text and returns the exit code and the output.
def _loop_run(
    register: Callable[[mcp.Server], None], text: str
) -> tuple[int, str]:
    stdout = io.StringIO()
    code = mcp_stdio.stdio_run(register, io.StringIO(text), stdout)
    return code, stdout.getvalue()


# Returns the message of the error `json.loads` raises for the text.
def _decode_message(case: unittest.TestCase, text: str) -> str:
    with case.assertRaises(json.JSONDecodeError) as caught:
        json.loads(text)
    return str(caught.exception)


# Returns the message of the error `json.dumps` raises for NaN.
def _nan_message(case: unittest.TestCase) -> str:
    with case.assertRaises(ValueError) as caught:
        json.dumps(float("nan"), allow_nan=False)
    return str(caught.exception)


# Starts the script on a root with pipes on its three streams.
def _child_start(root: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, _STDIO_PATH, "--root", root],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPYCACHEPREFIX": _PYCACHE_PATH},
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


# Registers the server tools of the API file and records the calls that run.
class CallRecorder:
    # Starts with no calls.
    def __init__(self) -> None:
        self.calls: list[str] = []

    # Records a call of the named tool and answers with the name as text.
    def tool_run(self, name: str, arguments: dict[str, Any]) -> mcp.ToolResult:
        self.calls.append(name)
        return mcp.ToolResult([{"type": "text", "text": name}], False)

    # Registers the server tools of the API file.
    def server_fill(self, server: mcp.Server) -> None:
        for entry in _entries_read():
            server.tool_register(
                _tool_make(entry),
                functools.partial(self.tool_run, entry["name"]),
            )

    # Registers those and a tool that needs no permit.
    def plain_fill(self, server: mcp.Server) -> None:
        self.server_fill(server)
        server.tool_register(
            mcp.Tool("plain", "Plain.", _EMPTY_SCHEMA, False),
            functools.partial(self.tool_run, "plain"),
        )

    # Registers a tool that answers a number that JSON cannot hold.
    def nan_fill(self, server: mcp.Server) -> None:
        server.tool_register(
            mcp.Tool("nan", "Answers NaN.", _EMPTY_SCHEMA, False),
            lambda arguments: mcp.ToolResult([{"n": float("nan")}], False),
        )


# A text stream that counts its flushes.
class FlushCounter(io.StringIO):
    # Starts with no flushes.
    def __init__(self) -> None:
        super().__init__()
        self.flushes = 0

    # Counts the flush, then does it.
    def flush(self) -> None:
        self.flushes += 1
        super().flush()


# Tests the loop on lines that are messages.
class TestLoop(unittest.TestCase):
    # The transcript replays line for line, and the permit tool never runs.
    def test_transcript_replay(self) -> None:
        sent, expected = _transcript_read()
        recorder = CallRecorder()
        text = "".join(line + "\n" for line in sent)
        code, output = _loop_run(recorder.server_fill, text)
        self.assertEqual(code, 0)
        self.assertEqual(output.splitlines(), expected)
        self.assertEqual(recorder.calls, [])

    # No input ends the loop with exit code 0 and no output.
    def test_input_empty(self) -> None:
        self.assertEqual(_loop_run(CallRecorder().server_fill, ""), (0, ""))

    # A notification writes nothing.
    def test_notification_silent(self) -> None:
        text = _INITIALIZED_LINE + "\n"
        self.assertEqual(_loop_run(CallRecorder().server_fill, text), (0, ""))

    # A last line with no newline is still a message.
    def test_line_unterminated(self) -> None:
        code, output = _loop_run(CallRecorder().server_fill, _PING_LINE)
        self.assertEqual((code, output), (0, _PING_REPLY + "\n"))

    # A permit tool is refused with code `-32000` and its function never runs.
    def test_permit_refused(self) -> None:
        recorder = CallRecorder()
        code, output = _loop_run(recorder.plain_fill, _PERMIT_LINE + "\n")
        self.assertEqual((code, output), (0, _PERMIT_REPLY + "\n"))
        self.assertEqual(recorder.calls, [])

    # A tool that needs no permit runs, beside a refused one.
    def test_plain_runs(self) -> None:
        recorder = CallRecorder()
        text = _PERMIT_LINE + "\n" + _PLAIN_LINE + "\n"
        code, output = _loop_run(recorder.plain_fill, text)
        self.assertEqual(code, 0)
        self.assertEqual(output.splitlines(), [_PERMIT_REPLY, _PLAIN_REPLY])
        self.assertEqual(recorder.calls, ["plain"])

    # Each response is flushed as it is written, and a notification is not.
    def test_flush_each(self) -> None:
        stdout = FlushCounter()
        lines = [_PING_LINE, _INITIALIZED_LINE, _PING_LINE]
        stdin = io.StringIO("".join(line + "\n" for line in lines))
        code = mcp_stdio.stdio_run(CallRecorder().server_fill, stdin, stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.flushes, 2)
        self.assertEqual(stdout.getvalue(), (_PING_REPLY + "\n") * 2)

    # A response that holds NaN is not written and raises.
    def test_response_nan(self) -> None:
        line = (
            '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":'
            '{"name":"nan","arguments":{}}}'
        )
        stdout = io.StringIO()
        with self.assertRaises(ValueError) as caught:
            mcp_stdio.stdio_run(
                CallRecorder().nan_fill, io.StringIO(line + "\n"), stdout
            )
        self.assertEqual(str(caught.exception), _nan_message(self))
        self.assertEqual(stdout.getvalue(), "")


# Tests the loop and the runner on input that is not valid.
class TestErrors(unittest.TestCase):
    # A line that is not JSON raises, after the responses before it are out.
    def test_line_malformed(self) -> None:
        stdout = io.StringIO()
        text = _PING_LINE + "\n" + _MALFORMED_LINE + _PING_LINE + "\n"
        with self.assertRaises(ValueError) as caught:
            mcp_stdio.stdio_run(
                CallRecorder().server_fill, io.StringIO(text), stdout
            )
        message = _decode_message(self, _MALFORMED_LINE)
        self.assertEqual(
            str(caught.exception),
            i18n("mcp_stdio.line_malformed", 2, message),
        )
        self.assertEqual(stdout.getvalue(), _PING_REPLY + "\n")

    # A line that is JSON but not an object raises.
    def test_line_object(self) -> None:
        for line in ("[1]", "5", '"x"', "null"):
            with self.subTest(line=line):
                stdout = io.StringIO()
                with self.assertRaises(ValueError) as caught:
                    mcp_stdio.stdio_run(
                        CallRecorder().server_fill,
                        io.StringIO(line + "\n"),
                        stdout,
                    )
                self.assertEqual(
                    str(caught.exception), i18n("mcp_stdio.line_object", 1)
                )
                self.assertEqual(stdout.getvalue(), "")

    # A blank line is not JSON and raises.
    def test_line_blank(self) -> None:
        stdout = io.StringIO()
        with self.assertRaises(ValueError) as caught:
            mcp_stdio.stdio_run(
                CallRecorder().server_fill, io.StringIO("\n"), stdout
            )
        message = _decode_message(self, "\n")
        self.assertEqual(
            str(caught.exception),
            i18n("mcp_stdio.line_malformed", 1, message),
        )
        self.assertEqual(stdout.getvalue(), "")

    # The runner refuses to start without `--root`, with usage exit code 2.
    def test_root_required(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                mcp_stdio.stdio_serve([])
        self.assertEqual(caught.exception.code, 2)


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

    # The transcript replays line for line, then closing stdin exits with 0.
    def test_process_replay(self) -> None:
        process = self.child_start()
        for direction, text in _transcript_steps():
            if direction == _CLIENT_DIRECTION:
                _line_write(process, text + "\n")
            else:
                self.assertEqual(_line_read(process), text + "\n")
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
        message = _decode_message(self, _MALFORMED_LINE)
        self.assertTrue(text.startswith(_TRACEBACK_HEAD))
        self.assertEqual(
            text.splitlines()[-1],
            "ValueError: " + i18n("mcp_stdio.line_malformed", 1, message),
        )
