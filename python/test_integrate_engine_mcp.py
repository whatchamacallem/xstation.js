# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests engine_mcp with its real callees in forked children: lines of the
# gold written as wire bytes, read by the real jslb decoder and served by
# the real dispatcher on a real MCP server, each reply encoded by the real
# jslb encoder and read back from its JSON text. The server has two tools,
# plain functions of this module: one answers the JSON text of its
# arguments and one raises. The exchange that opens a session, a tool's
# answer to the arguments the decoder read, a tool's exception as the
# `Failure` whose reply the dispatcher gave its `r`, and a request pushed
# with no wire id, which the dispatcher refuses for the reply it gets. Each
# child writes how its work ended to a file, or to stderr when that write
# fails, then kills itself.

import engine_mcp, functools, harness, json, os, signal, sys, tempfile
import traceback, unittest
from collections.abc import Callable
from typing import Any, NoReturn

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_engine_mcp"

# The limits of the decoder, as the checkout sets them.
_LINE_MAX: int = harness.setting_get("line_max")
_BLOB_MAX: int = harness.setting_get("blob_max")
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# The text of the exception that the failing tool raises.
_TOOL_FAILURE = "boom"

# The file in the scratch directory that a child writes how it ended to.
_ENDING_NAME = "ending.json"


# A value of this module's gold as JSON holds it, which is not to be changed.
def _gold_raw(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The bytes of gold lines on the wire: each its JSON text and its CR.
def _gold_bytes(*names: str) -> bytes:
    data = b""
    for name in names:
        line = _gold_raw(f"lines.{name}")
        text = json.dumps(line, ensure_ascii=False, separators=(",", ":"))
        data += text.encode("utf-8") + b"\r"
    return data


# The echo tool: answers the JSON text of its arguments, in their order.
def _echo_run(arguments: dict[str, Any]) -> engine_mcp.mcp.ToolResult:
    text = json.dumps(arguments, separators=(",", ":"))
    return engine_mcp.mcp.ToolResult([{"type": "text", "text": text}], False)


# The failing tool: raises, as a tool that fails does.
def _fail_run(arguments: dict[str, Any]) -> NoReturn:
    raise ValueError(_TOOL_FAILURE)


# A new server with the gold's name and tools, the echo then the failing one.
def _server_make() -> engine_mcp.mcp.Server:
    identity = _gold_raw("lines.initialize_reply")["result"]["serverInfo"]
    server = engine_mcp.mcp.Server(identity["name"], identity["version"])
    echo, fail = _gold_raw("lines.list_reply")["result"]["tools"]
    for entry, run in ((echo, _echo_run), (fail, _fail_run)):
        tool = engine_mcp.mcp.Tool(
            entry["name"], entry["description"], entry["inputSchema"], False
        )
        server.tool_register(tool, run)
    return server


# Refuses a blob that streams: no line of these tests carries one.
def _sink_refuse(header: engine_mcp.jslb.Object) -> NoReturn:
    raise AssertionError(f"a blob came that streams: {header}")


# The lines of the bytes, read by the real decoder with the checkout's limits.
def _lines_decode(data: bytes) -> list[engine_mcp.jslb.Object]:
    decoder = engine_mcp.jslb.LineDecoder(
        _LINE_MAX, _BLOB_MAX, _OVERFLOW_BYTES, _sink_refuse
    )
    return decoder.bytes_feed(data)


# The JSON text of a reply as the real encoder writes it, read back.
def _reply_read(reply: engine_mcp.jslb.Object) -> object:
    (piece,) = engine_mcp.jslb.line_encode(reply)
    if not isinstance(piece, bytes):
        raise AssertionError(f"the reply's text is not bytes: {piece!r}")
    return json.loads(piece)


# Dispatch result as JSON: a reply read back, or a `Failure`'s with its error.
def _result_read(result: object) -> object:
    if result is None:
        return None
    if isinstance(result, engine_mcp.dispatch.Failure):
        error = result.error
        reply = _reply_read(result.reply)
        return {"failure": [reply, type(error).__name__, str(error)]}
    if not isinstance(result, engine_mcp.jslb.Object):
        raise AssertionError(f"the result is not a reply: {result!r}")
    return _reply_read(result)


# In a child: registers on a new server, returns what each line of `data` gave.
def _lines_serve(data: bytes) -> list[object]:
    engine_mcp.handlers_register(_server_make())
    return [
        _result_read(engine_mcp.dispatch.line_dispatch(line))
        for line in _lines_decode(data)
    ]


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


# Gives each test a scratch directory in `build/`, runs its work in children.
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


# Tests the `mcp` lines served through the dispatcher.
class TestServe(ScratchCase):
    # Opening a session replies to `initialize` and `tools/list` only.
    def test_session_served(self) -> None:
        data = _gold_bytes("initialize", "initialized", "list")
        expected = [
            _gold_raw("lines.initialize_reply"),
            None,
            _gold_raw("lines.list_reply"),
        ]
        work = functools.partial(_lines_serve, data)
        self.assertEqual(self.child_value(work), expected)

    # A tool answers the arguments the decoder read, in their order.
    def test_tool_served(self) -> None:
        work = functools.partial(_lines_serve, _gold_bytes("call"))
        expected = [_gold_raw("lines.call_reply")]
        self.assertEqual(self.child_value(work), expected)

    # A tool's exception is the `isError` reply of a `Failure`, its `r` set.
    def test_failure_served(self) -> None:
        work = functools.partial(_lines_serve, _gold_bytes("call_fail"))
        (ended,) = self.child_value(work)
        reply, kind, message = ended["failure"]
        self.assertEqual([kind, message], ["ValueError", _TOOL_FAILURE])
        result = reply.pop("result")
        self.assertEqual(reply, _gold_raw("lines.call_fail_reply"))
        self.assertIs(result["isError"], True)
        (block,) = result["content"]
        self.assertEqual(block["type"], "text")
        cascade = json.loads(block["text"])
        self.assertEqual(sorted(cascade), ["message", "stack"])
        self.assertEqual(cascade["message"], message)
        self.assertTrue(cascade["stack"].endswith(f"{kind}: {message}"))

    # A request pushed with no wire id is refused for the reply it gets.
    def test_push_refused(self) -> None:
        self.child_raise(
            functools.partial(_lines_serve, _gold_bytes("ping_pushed")),
            ValueError,
            _text_get("dispatch_notification_replied"),
        )
