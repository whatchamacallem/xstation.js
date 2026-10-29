# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handler of the `mcp` line in forked children, each registered
# with the real dispatcher on a real MCP server, so the server and the
# handler never reach another test. The server has two tools, plain
# functions of this module: one answers the JSON text of its arguments and
# one raises. The handler is called as the dispatcher calls it on lines of
# the gold: the exchange that opens a session, nothing replied to a
# notification, a reply without `r` to a request that came as a push, each
# message the server takes answered, a tool's arguments passed on in their
# order, and after an exception a result named `Failure` holding the reply
# and the exception, the cascade the server writes read back. A failure the
# server keeps when no response comes raises. The registration is read from
# the dispatcher, which refuses a second one of the type. Each child writes
# how its work ended to a file, or to stderr when that write fails, then
# kills itself.

import engine_mcp, functools, harness, json, os, re, signal, sys, tempfile
import traceback, unittest
from collections.abc import Callable
from typing import Any, NoReturn

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_mcp"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The text of the exception that the failing tool raises.
_TOOL_FAILURE = "boom"

# The file in the scratch directory that a child writes how it ended to.
_ENDING_NAME = "ending.json"


# A copy of a value of this module's gold, its number keys made `int`.
def _gold_value(name: str) -> Any:
    return _keys_number(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A value of this module's gold as JSON holds it, which is not to be changed.
def _gold_raw(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# A copy of a JSON value with each number key an `int`, at every depth.
def _keys_number(value: Any) -> Any:
    if isinstance(value, dict):
        made: dict[int | str, Any] = {}
        for key, item in value.items():
            number = _NUMBER_KEY.fullmatch(key) is not None
            made[int(key) if number else key] = _keys_number(item)
        return made
    if isinstance(value, list):
        return [_keys_number(item) for item in value]
    return value


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The payload of a line: its string keys, in the order they came.
def _payload_of(line: dict[int | str, Any]) -> dict[str, Any]:
    return {key: value for key, value in line.items() if isinstance(key, str)}


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    return fn(line, **_payload_of(line))


# The echo tool: answers the JSON text of its arguments, in their order.
def _echo_run(arguments: dict[str, Any]) -> engine_mcp.mcp.ToolResult:
    text = json.dumps(arguments, separators=(",", ":"))
    return engine_mcp.mcp.ToolResult([{"type": "text", "text": text}], False)


# The failing tool: raises, as a tool that fails does.
def _fail_run(arguments: dict[str, Any]) -> NoReturn:
    raise ValueError(_TOOL_FAILURE)


# A new server named as the gold's `initialize` reply, with the gold's tools:
# the echo tool and the failing one, in the order `tools/list` gives them.
def _server_make() -> engine_mcp.mcp.Server:
    identity = _gold_value("lines.initialize_reply")["result"]["serverInfo"]
    server = engine_mcp.mcp.Server(identity["name"], identity["version"])
    echo, fail = _gold_value("lines.list_reply")["result"]["tools"]
    for entry, run in ((echo, _echo_run), (fail, _fail_run)):
        tool = engine_mcp.mcp.Tool(
            entry["name"], entry["description"], entry["inputSchema"], False
        )
        server.tool_register(tool, run)
    return server


# What a handler returned, made JSON: a `Failure` as its reply and its error.
def _result_read(result: object) -> object:
    if isinstance(result, engine_mcp.dispatch.Failure):
        error = result.error
        return {"failure": [result.reply, type(error).__name__, str(error)]}
    return result


# The work of a child: registers on a new server, then handles each line.
def _lines_handle(lines: list[Any]) -> list[object]:
    engine_mcp.handlers_register(_server_make())
    return [
        _result_read(_handler_call(engine_mcp.mcp_message, line))
        for line in lines
    ]


# The work of a child: registers on a new server, leaves it the failure of a
# request it handles alone, then calls the handler on the line.
def _failure_left(line: Any) -> object:
    server = _server_make()
    engine_mcp.handlers_register(server)
    server.message_handle(_payload_of(_gold_value("lines.unknown")))
    return _handler_call(engine_mcp.mcp_message, line)


# The work of a child: registers, then registers the handler's type again.
def _register_twice() -> None:
    engine_mcp.handlers_register(_server_make())
    engine_mcp.dispatch.handler_register("mcp", 0, engine_mcp.mcp_message)


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(work: Callable[[], object], path: str) -> None:
    try:
        try:
            ending: dict[str, object] = {"returned": work()}
        except BaseException as error:
            ending = {
                "raised": [type(error).__name__, str(error)],
                "trace": traceback.format_exc(),
            }
        text = json.dumps(ending)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
    except BaseException:
        # The parent finds no ending, so the failure goes to stderr.
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a scratch directory in `build/` and runs its work in
# children.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name

    # Runs the work in a forked child and returns how it ended.
    def child_run(self, work: Callable[[], object]) -> dict[str, Any]:
        path = os.path.join(self.scratch, _ENDING_NAME)
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child_end(work, path)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending: dict[str, Any] = json.load(file)
        os.remove(path)
        return ending

    # Runs the work in a child and returns what it returned.
    def child_value(self, work: Callable[[], object]) -> Any:
        ending = self.child_run(work)
        if "raised" in ending:
            self.fail(ending["trace"])
        return ending["returned"]

    # Runs the work in a child and checks the type and the text it raised.
    def child_raise(
        self,
        work: Callable[[], object],
        kind: type[BaseException],
        message: str,
    ) -> None:
        ending = self.child_run(work)
        if "returned" in ending:
            self.fail(f"nothing was raised: {ending['returned']!r}")
        expected = [kind.__name__, message]
        self.assertEqual(ending["raised"], expected, ending["trace"])

    # Checks a cascade the server wrote of an exception of the type and text.
    def cascade_check(
        self, cascade: dict[str, Any], kind: str, message: str
    ) -> None:
        self.assertEqual(sorted(cascade), ["message", "stack"])
        self.assertEqual(cascade["message"], message)
        self.assertTrue(cascade["stack"].endswith(f"{kind}: {message}"))


# Tests the exchange that opens a session, and the answers after a fault.
class TestExchange(ScratchCase):
    # Opening a session replies to `initialize` and `tools/list` only.
    def test_session_opened(self) -> None:
        names = ("initialize", "initialized", "list")
        lines = [_gold_value(f"lines.{name}") for name in names]
        expected = [
            _gold_raw("lines.initialize_reply"),
            None,
            _gold_raw("lines.list_reply"),
        ]
        work = functools.partial(_lines_handle, lines)
        self.assertEqual(self.child_value(work), expected)

    # A request pushed with no wire id gets a reply without `r`.
    def test_request_pushed(self) -> None:
        work = functools.partial(
            _lines_handle, [_gold_value("lines.ping_pushed")]
        )
        expected = [_gold_raw("lines.ping_pushed_reply")]
        self.assertEqual(self.child_value(work), expected)

    # An error response is the reply of a `Failure` holding the exception.
    def test_error_response(self) -> None:
        work = functools.partial(_lines_handle, [_gold_value("lines.unknown")])
        (ended,) = self.child_value(work)
        reply, kind, message = ended["failure"]
        text = _text_get("mcp_method_unknown")
        self.assertEqual([kind, message], ["RpcError", text])
        cascade = reply["error"].pop("data")
        self.assertEqual(reply, _gold_raw("lines.unknown_reply"))
        self.cascade_check(cascade, kind, text)

    # A tool's exception is the `isError` reply of a `Failure` holding it.
    def test_tool_raises(self) -> None:
        work = functools.partial(_lines_handle, [_gold_value("lines.call")])
        (ended,) = self.child_value(work)
        reply, kind, message = ended["failure"]
        self.assertEqual([kind, message], ["ValueError", _TOOL_FAILURE])
        result = reply.pop("result")
        self.assertEqual(reply, _gold_raw("lines.call_reply"))
        self.assertIs(result["isError"], True)
        (block,) = result["content"]
        self.assertEqual(block["type"], "text")
        self.cascade_check(json.loads(block["text"]), kind, message)


# Tests how the message reaches the server and the response comes back.
class TestPass(ScratchCase):
    # Each message the server takes is answered, a notification by nothing.
    def test_messages_answered(self) -> None:
        work = functools.partial(_lines_handle, _gold_value("lines.passed"))
        expected = _gold_raw("lines.passed_replies")
        self.assertEqual(self.child_value(work), expected)

    # A tool gets the arguments of the call as they came, in their order.
    def test_arguments_passed(self) -> None:
        line = _gold_value("lines.call_echo")
        work = functools.partial(_lines_handle, [line])
        expected = [_gold_raw("lines.call_echo_reply")]
        self.assertEqual(self.child_value(work), expected)

    # The response is the payload of the reply, and the wire id is separate.
    def test_response_replied(self) -> None:
        work = functools.partial(_lines_handle, [_gold_value("lines.ping")])
        expected = [_gold_raw("lines.ping_reply")]
        self.assertEqual(self.child_value(work), expected)

    # A failure the server keeps when no response comes raises: a `Failure`
    # needs a reply.
    def test_failure_unanswered(self) -> None:
        line = _gold_value("lines.initialized")
        self.child_raise(
            functools.partial(_failure_left, line),
            engine_mcp.mcp.RpcError,
            _text_get("mcp_method_unknown"),
        )

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.initialized")
        self.child_raise(
            functools.partial(_handler_call, engine_mcp.mcp_message, line),
            RuntimeError,
            _text_get("engine_mcp_not_registered"),
        )

    # The handler is registered under `mcp` at version 0, which the
    # dispatcher then refuses to register again.
    def test_handlers_registered(self) -> None:
        self.child_raise(
            _register_twice,
            ValueError,
            _text_get("dispatch_handler_twice"),
        )
