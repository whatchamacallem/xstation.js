# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the stdio loop on text streams: the transcript DATA/07_mcp_stdio.txt
# replayed against the tools of API/mcp/tools.json, a permit tool refused and
# never run, a plain tool run, an output flushed for each response, and a
# line that is not a JSON object ending the loop with an exception. No process
# is started.

import contextlib, functools, io, json, mcp, mcp_stdio, os, unittest
from collections.abc import Callable
from typing import Any

# The root of the checkout.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The transcript of an external agent driving the server over stdio.
_TRANSCRIPT_PATH = os.path.join(_ROOT_PATH, "DATA", "07_mcp_stdio.txt")

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


# Reads the transcript: the lines the client sends, the lines expected back.
def _transcript_read() -> tuple[list[str], list[str]]:
    sent: list[str] = []
    expected: list[str] = []
    with open(_TRANSCRIPT_PATH, encoding="utf-8") as file:
        for line in file.read().splitlines():
            if line.startswith("#"):
                continue
            _, direction, text = line.split(" ", 2)
            if direction == "CLIENT->STDIO":
                sent.append(text)
            else:
                expected.append(text)
    return sent, expected


# Runs the loop on the text and returns the exit code and the output.
def _run(register: Callable[[mcp.Server], None], text: str) -> tuple[int, str]:
    stdout = io.StringIO()
    code = mcp_stdio.stdio_run(register, io.StringIO(text), stdout)
    return code, stdout.getvalue()


# Registers the server tools of the API file and records the calls that run.
class Recorder:
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
        recorder = Recorder()
        text = "".join(line + "\n" for line in sent)
        code, output = _run(recorder.server_fill, text)
        self.assertEqual(code, 0)
        self.assertEqual(output.splitlines(), expected)
        self.assertEqual(recorder.calls, [])

    # No input ends the loop with exit code 0 and no output.
    def test_input_empty(self) -> None:
        self.assertEqual(_run(Recorder().server_fill, ""), (0, ""))

    # A notification writes nothing.
    def test_notification_silent(self) -> None:
        text = _INITIALIZED_LINE + "\n"
        self.assertEqual(_run(Recorder().server_fill, text), (0, ""))

    # A last line with no newline is still a message.
    def test_line_unterminated(self) -> None:
        code, output = _run(Recorder().server_fill, _PING_LINE)
        self.assertEqual((code, output), (0, _PING_REPLY + "\n"))

    # A permit tool is refused with code `-32000` and its function never runs.
    def test_permit_refused(self) -> None:
        recorder = Recorder()
        code, output = _run(recorder.plain_fill, _PERMIT_LINE + "\n")
        self.assertEqual((code, output), (0, _PERMIT_REPLY + "\n"))
        self.assertEqual(recorder.calls, [])

    # A tool that needs no permit runs, beside a refused one.
    def test_plain_runs(self) -> None:
        recorder = Recorder()
        text = _PERMIT_LINE + "\n" + _PLAIN_LINE + "\n"
        code, output = _run(recorder.plain_fill, text)
        self.assertEqual(code, 0)
        self.assertEqual(output.splitlines(), [_PERMIT_REPLY, _PLAIN_REPLY])
        self.assertEqual(recorder.calls, ["plain"])

    # Each response is flushed as it is written, and a notification is not.
    def test_flush_each(self) -> None:
        stdout = FlushCounter()
        lines = [_PING_LINE, _INITIALIZED_LINE, _PING_LINE]
        stdin = io.StringIO("".join(line + "\n" for line in lines))
        code = mcp_stdio.stdio_run(Recorder().server_fill, stdin, stdout)
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
        with self.assertRaises(ValueError):
            mcp_stdio.stdio_run(
                Recorder().nan_fill, io.StringIO(line + "\n"), stdout
            )
        self.assertEqual(stdout.getvalue(), "")


# Tests the loop and the runner on input that is not valid.
class TestErrors(unittest.TestCase):
    # A line that is not JSON raises, after the responses before it are out.
    def test_line_malformed(self) -> None:
        stdout = io.StringIO()
        stdin = io.StringIO(_PING_LINE + '\n{"jsonrpc"\n' + _PING_LINE + "\n")
        with self.assertRaises(ValueError):
            mcp_stdio.stdio_run(Recorder().server_fill, stdin, stdout)
        self.assertEqual(stdout.getvalue(), _PING_REPLY + "\n")

    # A line that is JSON but not an object raises, as does a blank line.
    def test_line_object(self) -> None:
        for line in ("[1]", "5", '"x"', "null", ""):
            with self.subTest(line=line):
                stdout = io.StringIO()
                with self.assertRaises(ValueError):
                    mcp_stdio.stdio_run(
                        Recorder().server_fill,
                        io.StringIO(line + "\n"),
                        stdout,
                    )
                self.assertEqual(stdout.getvalue(), "")

    # The runner refuses to start without `--root`, with usage exit code 2.
    def test_root_required(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                mcp_stdio.stdio_serve([])
        self.assertEqual(caught.exception.code, 2)
