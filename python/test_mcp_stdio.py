# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the stdio loop on text streams with a double of `mcp`, the module it
# imports inside itself: one server made and given to the register function,
# each line parsed and handed to the server, each response written as compact
# JSON and flushed, a notification writing nothing, an exception the server
# keeps raised once its answer is out, and a line that is not a JSON object,
# or holds a bad number, ending the loop with an exception, its texts against
# the gold. Then tests the script as a process started the way an external
# agent starts it, the real server answering against the tools of
# API/mcp/tools.json, on a root in build/ that holds a copy of the checkout's
# settings.json.

import contextlib, harness, io, json, mcp_stdio, os, select, shutil
import subprocess, sys, tempfile, types, unittest, unittest.mock
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
_GOLD_ID = "python.test_mcp_stdio"

# The most seconds a wait on the child takes, a default chosen by its writer.
_CHILD_SECONDS: int = harness.gold_get(f"{_GOLD_ID}.child_seconds")

# The most bytes read from the output of the child at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The first line of the traceback the child writes when it raises.
_TRACEBACK_HEAD = "Traceback (most recent call last):\n"

# The call of the double that makes the server, as `stdio_run` names it.
_SERVER_MADE = ("server_make", "xsjs-server", "0")

# A ping request as a client writes it.
_PING_LINE = '{"jsonrpc":"2.0","id":1,"method":"ping"}'

# The response to it.
_PING_REPLY = '{"jsonrpc":"2.0","id":1,"result":{}}'

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

# A ping whose params hold a number that overflows a double.
_OVERFLOW_LINE = (
    '{"jsonrpc":"2.0","id":1,"method":"ping","params":{"x":1e400}}'
)

# A call of a tool that raises.
_FAIL_LINE = (
    '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":'
    '{"name":"fail","arguments":{}}}'
)

# The answer the server double gives that call, an error result.
_FAIL_REPLY = (
    '{"jsonrpc":"2.0","id":4,"result":{"content":'
    '[{"type":"text","text":"boom"}],"isError":true}}'
)

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


# A double of `mcp.Server`: records each call, answers what the test queued.
class ServerDouble:
    # Starts with no call recorded and no answer queued.
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answers: dict[str, list[Any]] = {}

    # Records a call and returns its next queued answer, which must exist.
    def call_answer(self, name: str, *args: Any) -> Any:
        self.calls.append((name, *args))
        if not self.answers.get(name):
            raise AssertionError(f"the server double has no answer: {name}")
        return self.answers[name].pop(0)

    # `mcp.Server(name, version)`, as `stdio_run` makes its server.
    def server_make(self, name: str, version: str) -> Any:
        return self.call_answer("server_make", name, version)

    # `Server.message_handle`, as `stdio_run` calls it on each line.
    def message_handle(self, message: dict[str, Any]) -> Any:
        return self.call_answer("message_handle", message)

    # `Server.failure_take`, as `stdio_run` calls it after each line.
    def failure_take(self) -> Any:
        return self.call_answer("failure_take")


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


# Runs `stdio_run` in this process with `mcp`, which it imports, a double.
class DoubleCase(unittest.TestCase):
    # Makes the server double.
    def setUp(self) -> None:
        self.double_make()

    # Makes a new server double, which answers its own making.
    def double_make(self) -> None:
        self.server = ServerDouble()
        self.server.answers["server_make"] = [self.server]
        self.registered: list[Any] = []

    # Queues the responses `message_handle` gives, and no failure for each.
    def replies_queue(self, replies: list[str | None]) -> None:
        self.server.answers["message_handle"] = [
            None if reply is None else json.loads(reply) for reply in replies
        ]
        self.server.answers["failure_take"] = [None] * len(replies)

    # Runs the loop on the text to `stdout`, `mcp` patched to the double.
    def loop_run(self, text: str, stdout: io.StringIO) -> int:
        double = types.SimpleNamespace(Server=self.server.server_make)
        with unittest.mock.patch.dict(sys.modules, {"mcp": double}):
            return mcp_stdio.stdio_run(
                self.registered.append, io.StringIO(text), stdout
            )

    # Checks the server was made and registered once, then got each line.
    def calls_check(self, sent: list[str]) -> None:
        calls: list[tuple[Any, ...]] = [_SERVER_MADE]
        for line in sent:
            calls += [("message_handle", json.loads(line)), ("failure_take",)]
        self.assertEqual(self.server.calls, calls)
        self.assertEqual(self.registered, [self.server])


# Tests the loop on lines that are messages.
class TestLoop(DoubleCase):
    # A session goes to the server line by line, a None reply writing nothing.
    def test_session_replay(self) -> None:
        steps = _session_steps()
        self.replies_queue([reply for _, reply in steps])
        stdout = io.StringIO()
        text = "".join(sent + "\n" for sent, _ in steps)
        self.assertEqual(self.loop_run(text, stdout), 0)
        expected = [reply for _, reply in steps if reply is not None]
        self.assertEqual(stdout.getvalue().splitlines(), expected)
        self.calls_check([sent for sent, _ in steps])

    # No input ends the loop with exit code 0 and no output.
    def test_input_empty(self) -> None:
        stdout = io.StringIO()
        self.assertEqual(self.loop_run("", stdout), 0)
        self.assertEqual(stdout.getvalue(), "")
        self.calls_check([])

    # A notification writes nothing.
    def test_notification_silent(self) -> None:
        self.replies_queue([None])
        stdout = io.StringIO()
        self.assertEqual(self.loop_run(_INITIALIZED_LINE + "\n", stdout), 0)
        self.assertEqual(stdout.getvalue(), "")
        self.calls_check([_INITIALIZED_LINE])

    # A last line with no newline is still a message.
    def test_line_unterminated(self) -> None:
        self.replies_queue([_PING_REPLY])
        stdout = io.StringIO()
        self.assertEqual(self.loop_run(_PING_LINE, stdout), 0)
        self.assertEqual(stdout.getvalue(), _PING_REPLY + "\n")
        self.calls_check([_PING_LINE])

    # Each response is flushed as it is written, and a notification is not.
    def test_flush_each(self) -> None:
        lines = [_PING_LINE, _INITIALIZED_LINE, _PING_LINE]
        self.replies_queue([_PING_REPLY, None, _PING_REPLY])
        stdout = FlushCounter()
        text = "".join(line + "\n" for line in lines)
        self.assertEqual(self.loop_run(text, stdout), 0)
        self.assertEqual(stdout.flushes, 2)
        self.assertEqual(stdout.getvalue(), (_PING_REPLY + "\n") * 2)
        self.calls_check(lines)

    # The exception the server keeps is raised once its answer is flushed.
    def test_failure_raised(self) -> None:
        error = ValueError("boom")
        self.server.answers["message_handle"] = [json.loads(_FAIL_REPLY)]
        self.server.answers["failure_take"] = [error]
        stdout = FlushCounter()
        text = _FAIL_LINE + "\n" + _PING_LINE + "\n"
        with self.assertRaises(ValueError) as caught:
            self.loop_run(text, stdout)
        self.assertIs(caught.exception, error)
        self.assertEqual(stdout.getvalue(), _FAIL_REPLY + "\n")
        self.assertEqual(stdout.flushes, 1)
        self.calls_check([_FAIL_LINE])


# Tests the loop and the runner on input that is not valid.
class TestErrors(DoubleCase):
    # Checks the error is `mcp_stdio.line_malformed` of a `WireError` cause.
    def malformed_check(
        self, error: BaseException, cause_name: str, error_name: str
    ) -> None:
        cause = error.__cause__
        self.assertEqual(type(cause).__name__, "WireError")
        self.assertEqual(str(cause), _text_get(cause_name))
        self.assertEqual(str(error), _text_get(error_name))

    # A line that is not JSON raises, after the responses before it are out.
    def test_line_malformed(self) -> None:
        self.replies_queue([_PING_REPLY])
        stdout = io.StringIO()
        text = _PING_LINE + "\n" + _MALFORMED_LINE + _PING_LINE + "\n"
        with self.assertRaises(ValueError) as caught:
            self.loop_run(text, stdout)
        self.malformed_check(
            caught.exception,
            "jslb_text_not_json_delimiter",
            "mcp_stdio_line_malformed_delimiter",
        )
        self.assertEqual(stdout.getvalue(), _PING_REPLY + "\n")
        self.calls_check([_PING_LINE])

    # A number that overflows a double is refused by the decoder at read.
    def test_number_overflow(self) -> None:
        stdout = io.StringIO()
        with self.assertRaises(ValueError) as caught:
            self.loop_run(_OVERFLOW_LINE + "\n", stdout)
        self.malformed_check(
            caught.exception,
            "jslb_number_overflow",
            "mcp_stdio_line_malformed_overflow",
        )
        self.assertEqual(stdout.getvalue(), "")
        self.calls_check([])

    # A line that is JSON but not an object raises.
    def test_line_object(self) -> None:
        for line in ("[1]", "5", '"x"', "null"):
            with self.subTest(line=line):
                self.double_make()
                stdout = io.StringIO()
                with self.assertRaises(ValueError) as caught:
                    self.loop_run(line + "\n", stdout)
                self.assertEqual(
                    str(caught.exception), _text_get("mcp_stdio_line_object")
                )
                self.assertEqual(stdout.getvalue(), "")
                self.calls_check([])

    # A blank line is not JSON and raises.
    def test_line_blank(self) -> None:
        stdout = io.StringIO()
        with self.assertRaises(ValueError) as caught:
            self.loop_run("\n", stdout)
        self.malformed_check(
            caught.exception,
            "jslb_text_not_json_blank",
            "mcp_stdio_line_malformed_blank",
        )
        self.assertEqual(stdout.getvalue(), "")
        self.calls_check([])

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
