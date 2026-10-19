# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the `mcp` line through the dispatcher: the exchange of the transcript
# `DATA/01_boot.txt` between the AI worker and the server replayed against the
# tools of `API/mcp/tools.json`, the members of a message handed to the MCP
# server as they came, its response put in the payload of the reply and
# nothing replied when it gives none. No process is started.

import dispatch, engine_mcp, jslb, json, mcp, os, unittest, unittest.mock
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The transcript of a new tab, which holds the `mcp` lines of the server.
_TRANSCRIPT_PATH = os.path.join(_ROOT_PATH, "DATA", "01_boot.txt")

# The dotted name of the handler table that the tests patch.
_HANDLERS_TARGET = "dispatch._HANDLERS"

# The dotted name of the MCP server that the tests patch.
_SERVER_TARGET = "engine_mcp._STATE.server"

# The schema of a tool that takes nothing.
_EMPTY_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

# Messages as they arrive: a request, two responses and a notification.
_MESSAGES: list[dict[str, Any]] = [
    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}},
    {"jsonrpc": "2.0", "id": 3, "error": {"code": -32601, "message": "m"}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
]


# Builds a line with no blobs: an optional id and the message as the payload.
def _line_make(request_id: int | None = None, **message: Any) -> jslb.Object:
    header = jslb.header_make("mcp", id=request_id)
    return jslb.line_make(header, [], **message)


# Dispatches a line that must be answered and returns the reply.
def _reply_get(line: jslb.Object) -> jslb.Object:
    reply = dispatch.line_dispatch(line)
    if reply is None:
        raise AssertionError("the line was not answered")
    return reply


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


# Stands for the function of a tool that the test never calls.
def _tool_refuse(arguments: dict[str, Any]) -> mcp.ToolResult:
    raise AssertionError("a tool was called")


# Answers a call with the text `hi`.
def _tool_echo(arguments: dict[str, Any]) -> mcp.ToolResult:
    return mcp.ToolResult([{"type": "text", "text": "hi"}], False)


# Makes the server of the transcript with the tools of the API file.
def _server_make() -> mcp.Server:
    server = mcp.Server("xsjs-server", "0")
    for entry in _entries_read():
        server.tool_register(_tool_make(entry), _tool_refuse)
    return server


# Reads the `mcp` lines of the transcript: direction, wire id and message.
def _transcript_read() -> list[tuple[str, int | None, dict[str, Any]]]:
    exchange: list[tuple[str, int | None, dict[str, Any]]] = []
    with open(_TRANSCRIPT_PATH, encoding="utf-8") as file:
        for line in file.read().splitlines():
            if line.startswith("#"):
                continue
            _, direction, text = line.split(" ", 2)
            if direction not in ("AI->SERVER", "SERVER->AI"):
                continue
            message: dict[str, Any] = json.loads(text)
            header: dict[str, Any] = message.pop("0")
            if header["t"] != "mcp":
                continue
            number = header.get("r" if direction == "SERVER->AI" else "i")
            exchange.append((direction, number, message))
    return exchange


# Gives each test an empty handler table and no registration.
class IsolatedCase(unittest.TestCase):
    # Patches the table and the state until the test ends.
    def setUp(self) -> None:
        table = unittest.mock.patch.dict(_HANDLERS_TARGET, {}, clear=True)
        state = unittest.mock.patch(_SERVER_TARGET, None)
        for patcher in (table, state):
            patcher.start()
            self.addCleanup(patcher.stop)


# Tests the exchange with a real MCP server.
class TestExchange(IsolatedCase):
    # The transcript replays: each request gets the reply it shows.
    def test_transcript_replay(self) -> None:
        engine_mcp.handlers_register(_server_make())
        exchange = _transcript_read()
        replies: list[tuple[int | None, dict[str, Any]]] = []
        for direction, number, message in exchange:
            if direction != "AI->SERVER":
                continue
            reply = dispatch.line_dispatch(_line_make(number, **message))
            if reply is not None:
                replies.append((reply[0]["r"], jslb.payload_of(reply)))
        expected = [
            (number, message)
            for direction, number, message in exchange
            if direction == "SERVER->AI"
        ]
        self.assertEqual(len(expected), 2)
        self.assertEqual(replies, expected)

    # A tool call runs the tool and its result is the payload of the reply.
    def test_tool_call(self) -> None:
        server = mcp.Server("xsjs-server", "0")
        server.tool_register(
            mcp.Tool("echo", "Echo.", _EMPTY_SCHEMA, False), _tool_echo
        )
        engine_mcp.handlers_register(server)
        call = _line_make(
            5,
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "echo", "arguments": {}},
        )
        reply = _reply_get(call)
        self.assertEqual(reply[0]["r"], 5)
        self.assertEqual(
            jslb.payload_of(reply),
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "content": [{"type": "text", "text": "hi"}],
                    "isError": False,
                },
            },
        )

    # An error response is the payload of the reply like any other.
    def test_error_response(self) -> None:
        engine_mcp.handlers_register(_server_make())
        line = _line_make(8, jsonrpc="2.0", id=4, method="nothing/here")
        payload = jslb.payload_of(_reply_get(line))
        self.assertEqual(sorted(payload), ["error", "id", "jsonrpc"])
        self.assertEqual(payload["id"], 4)
        self.assertEqual(payload["error"]["code"], -32601)

    # A request that came as a push, with no wire id, cannot be answered.
    def test_request_pushed(self) -> None:
        engine_mcp.handlers_register(_server_make())
        line = _line_make(None, jsonrpc="2.0", id=1, method="ping")
        with self.assertRaises(ValueError):
            dispatch.line_dispatch(line)


# Tests how the message reaches the server and the response comes back.
class TestPass(IsolatedCase):
    # The server gets the members of the message as they came, in order.
    def test_members_passed(self) -> None:
        server = unittest.mock.Mock(spec=mcp.Server)
        server.message_handle.return_value = None
        engine_mcp.handlers_register(server)
        for message in _MESSAGES:
            with self.subTest(message=message):
                line = _line_make(None, **message)
                self.assertIsNone(dispatch.line_dispatch(line))
                passed = server.message_handle.call_args.args[0]
                self.assertEqual(passed, message)
                self.assertEqual(list(passed), list(message))

    # The response is the payload of the reply, and the wire id is separate.
    def test_response_replied(self) -> None:
        response = {"jsonrpc": "2.0", "id": 9, "result": {}}
        server = unittest.mock.Mock(spec=mcp.Server)
        server.message_handle.return_value = response
        engine_mcp.handlers_register(server)
        line = _line_make(3, jsonrpc="2.0", id=9, method="ping")
        reply = _reply_get(line)
        self.assertEqual(reply[0]["r"], 3)
        self.assertEqual(jslb.payload_of(reply), response)

    # No response means nothing to reply.
    def test_response_none(self) -> None:
        server = unittest.mock.Mock(spec=mcp.Server)
        server.message_handle.return_value = None
        engine_mcp.handlers_register(server)
        line = _line_make(2, **_MESSAGES[0])
        self.assertIsNone(engine_mcp.mcp_message(line, **_MESSAGES[0]))

    # Called before the registration the handler raises.
    def test_unregistered(self) -> None:
        line = _line_make(None, **_MESSAGES[3])
        with self.assertRaises(RuntimeError):
            engine_mcp.mcp_message(line, **_MESSAGES[3])

    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_mcp.handlers_register(_server_make())
        with self.assertRaises(ValueError):
            engine_mcp.handlers_register(_server_make())
