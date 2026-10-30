# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the stdio loop in process on pipes, with a real `mcp.Server` that
# serves the tool a register function of the test adds to it: one server
# made and given to the register function, each line parsed and answered by
# it, each response written as compact JSON and out on the pipe as it is
# written, while the loop still waits on its input, a notification writing
# nothing, the exception of a tool raised once its answer is out, and a line
# that is not a JSON object, or holds a bad number, ending the loop with an
# exception, its texts against the gold. Then the runner refuses a command
# line with no root, its usage error on a pipe that is the stderr of a
# forked child. The loop that waits on its input and the runner run in
# forked children, each of which writes how it ended to a file under
# build/, then kills itself.

import harness, json, mcp, mcp_stdio, os, select, signal, sys, tempfile
import traceback, unittest
from collections.abc import Callable
from typing import Any, TextIO

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_mcp_stdio"

# The most seconds a wait on the child takes, a default chosen by its writer.
_CHILD_SECONDS: int = harness.gold_get(f"{_GOLD_ID}.child_seconds")

# The most bytes read from a pipe at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The file in its scratch directory a child writes how its work ended to.
_ENDING_NAME = "ending.txt"

# The message of the error the tool of the test raises.
_FAIL_MESSAGE = "boom"

# The tool of the test, which raises its error.
_FAIL_TOOL = mcp.Tool(
    "fail",
    "Raises the error of the test.",
    {"type": "object", "properties": {}},
    False,
)

# A ping request as a client writes it.
_PING_LINE = '{"jsonrpc":"2.0","id":1,"method":"ping"}'

# The response to it.
_PING_REPLY = '{"jsonrpc":"2.0","id":1,"result":{}}'

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

# A call of the tool of the test, which raises.
_FAIL_LINE = (
    '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":'
    '{"name":"fail","arguments":{}}}'
)

# The id of that call.
_FAIL_ID = 4


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The response to `tools/list`: the tool of the test, as MCP lists one.
def _list_reply() -> dict[str, Any]:
    tool = {
        "name": _FAIL_TOOL.name,
        "description": _FAIL_TOOL.description,
        "inputSchema": _FAIL_TOOL.input_schema,
    }
    return {"jsonrpc": "2.0", "id": 2, "result": {"tools": [tool]}}


# Takes what is in the pipe now, its write end still open.
def _pipe_take(descriptor: int) -> str:
    data = b""
    while select.select([descriptor], [], [], 0)[0]:
        data += os.read(descriptor, _READ_BYTES)
    return data.decode("utf-8")


# Reads a pipe up to a newline, each wait bounded.
def _line_wait(descriptor: int) -> str:
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


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(work: Callable[[], str], path: str) -> None:
    try:
        try:
            ending = work()
        except SystemExit as error:
            ending = f"exit {error.code}"
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Runs `stdio_run` in this process on pipes, with the tool of the test.
class PipeCase(unittest.TestCase):
    # Makes the scratch directory, with no server registered yet.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.ending_path = os.path.join(scratch.name, _ENDING_NAME)
        self.servers: list[mcp.Server] = []
        self.running: set[int] = set()
        self.addCleanup(self.children_kill)
        self.error = ValueError(_FAIL_MESSAGE)

    # Registers the tool of the test on the server, and keeps the server.
    def register(self, server: mcp.Server) -> None:
        self.servers.append(server)
        server.tool_register(_FAIL_TOOL, self.fail_run)

    # The tool of the test, which raises its error.
    def fail_run(self, arguments: dict[str, Any]) -> mcp.ToolResult:
        raise self.error

    # A closed pipe of the text as stdin, a pipe as stdout and its read end.
    def streams_open(self, text: str) -> tuple[TextIO, TextIO, int]:
        input_read, input_write = os.pipe()
        data = text.encode("utf-8")
        self.assertEqual(os.write(input_write, data), len(data))
        os.close(input_write)
        output_read, output_write = os.pipe()
        self.addCleanup(os.close, output_read)
        stdin = open(input_read, encoding="utf-8")
        self.addCleanup(stdin.close)
        stdout = open(output_write, "w", encoding="utf-8")
        self.addCleanup(stdout.close)
        return stdin, stdout, output_read

    # Runs the loop on the text, returns its code and the output out so far.
    def loop_run(self, text: str) -> tuple[int, str]:
        stdin, stdout, output = self.streams_open(text)
        code = mcp_stdio.stdio_run(self.register, stdin, stdout)
        return code, _pipe_take(output)

    # Returns the loop's `kind` exception on the text, and the output so far.
    def failure_run(
        self, text: str, kind: type[BaseException]
    ) -> tuple[BaseException, str]:
        stdin, stdout, output = self.streams_open(text)
        with self.assertRaises(kind) as caught:
            mcp_stdio.stdio_run(self.register, stdin, stdout)
        return caught.exception, _pipe_take(output)

    # Forks a child that runs the work, and returns its pid.
    def child_fork(self, work: Callable[[], str]) -> int:
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child_end(work, self.ending_path)
        self.running.add(pid)
        return pid

    # Reaps the child, which killed itself, and returns how its work ended.
    def child_ending(self, pid: int) -> str:
        _, status = os.waitpid(pid, 0)
        self.running.remove(pid)
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(self.ending_path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(self.ending_path)
        return ending

    # Kills and reaps the children a failed test left.
    def children_kill(self) -> None:
        for pid in self.running:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)


# Tests the loop on lines that are messages.
class TestLoop(PipeCase):
    # A session goes to the one server line by line, a notification silent.
    def test_session_replay(self) -> None:
        lines = [_INITIALIZE_LINE, _INITIALIZED_LINE, _LIST_LINE]
        code, output = self.loop_run("".join(line + "\n" for line in lines))
        self.assertEqual(code, 0)
        opened, listed = output.splitlines()
        self.assertEqual(opened, _INITIALIZE_REPLY)
        self.assertEqual(json.loads(listed), _list_reply())
        (server,) = self.servers
        self.assertIsInstance(server, mcp.Server)

    # No input ends the loop with exit code 0 and no output.
    def test_input_empty(self) -> None:
        self.assertEqual(self.loop_run(""), (0, ""))
        self.assertEqual(len(self.servers), 1)

    # A notification writes nothing.
    def test_notification_silent(self) -> None:
        self.assertEqual(self.loop_run(_INITIALIZED_LINE + "\n"), (0, ""))

    # A last line with no newline is still a message.
    def test_line_unterminated(self) -> None:
        self.assertEqual(self.loop_run(_PING_LINE), (0, _PING_REPLY + "\n"))

    # Responses are out as written, while the loop waits, notifications silent.
    def test_flush_each(self) -> None:
        input_read, input_write = os.pipe()
        output_read, output_write = os.pipe()

        # Serves the pipes in the child, once the parent's ends are closed.
        def pipes_serve() -> str:
            os.close(input_write)
            os.close(output_read)
            with (
                open(input_read, encoding="utf-8") as stdin,
                open(output_write, "w", encoding="utf-8") as stdout,
            ):
                return repr(mcp_stdio.stdio_run(self.register, stdin, stdout))

        pid = self.child_fork(pipes_serve)
        os.close(input_read)
        os.close(output_write)
        writer = open(input_write, "wb", buffering=0)
        self.addCleanup(writer.close)
        reader = open(output_read, "rb", buffering=0)
        self.addCleanup(reader.close)
        writer.write((_PING_LINE + "\n").encode("utf-8"))
        self.assertEqual(_line_wait(reader.fileno()), _PING_REPLY + "\n")
        lines = _INITIALIZED_LINE + "\n" + _PING_LINE + "\n"
        writer.write(lines.encode("utf-8"))
        self.assertEqual(_line_wait(reader.fileno()), _PING_REPLY + "\n")
        writer.close()
        self.assertEqual(reader.read(), b"")
        self.assertEqual(self.child_ending(pid), repr(0))

    # The exception of a tool is raised once its answer is out.
    def test_failure_raised(self) -> None:
        text = _FAIL_LINE + "\n" + _PING_LINE + "\n"
        error, output = self.failure_run(text, ValueError)
        self.assertIs(error, self.error)
        (line,) = output.splitlines()
        answer = json.loads(line)
        self.assertEqual(answer["id"], _FAIL_ID)
        self.assertIs(answer["result"]["isError"], True)
        (content,) = answer["result"]["content"]
        self.assertEqual(content["type"], "text")
        self.assertEqual(json.loads(content["text"])["message"], _FAIL_MESSAGE)


# Tests the loop and the runner on input that is not valid.
class TestErrors(PipeCase):
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
        text = _PING_LINE + "\n" + _MALFORMED_LINE + _PING_LINE + "\n"
        error, output = self.failure_run(text, ValueError)
        self.malformed_check(
            error,
            "jslb_text_not_json_delimiter",
            "mcp_stdio_line_malformed_delimiter",
        )
        self.assertEqual(output, _PING_REPLY + "\n")

    # A number that overflows a double is refused by the decoder at read.
    def test_number_overflow(self) -> None:
        error, output = self.failure_run(_OVERFLOW_LINE + "\n", ValueError)
        self.malformed_check(
            error, "jslb_number_overflow", "mcp_stdio_line_malformed_overflow"
        )
        self.assertEqual(output, "")

    # A line that is JSON but not an object raises.
    def test_line_object(self) -> None:
        for line in ("[1]", "5", '"x"', "null"):
            with self.subTest(line=line):
                error, output = self.failure_run(line + "\n", ValueError)
                self.assertEqual(
                    str(error), _text_get("mcp_stdio_line_object")
                )
                self.assertEqual(output, "")

    # A blank line is not JSON and raises.
    def test_line_blank(self) -> None:
        error, output = self.failure_run("\n", ValueError)
        self.malformed_check(
            error, "jslb_text_not_json_blank", "mcp_stdio_line_malformed_blank"
        )
        self.assertEqual(output, "")

    # Without `--root` the runner refuses, usage error on stderr, exit code 2.
    def test_root_required(self) -> None:
        error_read, error_write = os.pipe()

        # Runs the runner with stderr on the pipe, flushed before it ends.
        def runner_refused() -> str:
            os.close(error_read)
            os.dup2(error_write, 2)
            os.close(error_write)
            try:
                return repr(mcp_stdio.stdio_serve([]))
            finally:
                sys.stderr.flush()

        pid = self.child_fork(runner_refused)
        os.close(error_write)
        with open(error_read, "rb") as reader:
            errors = reader.read().decode("utf-8")
        self.assertEqual(self.child_ending(pid), "exit 2")
        last = errors.splitlines()[-1]
        expected = _text_get("argparse_root_required")
        self.assertTrue(last.endswith(expected), errors)
