# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the `mcp` line through the dispatcher: the exchange that opens a
# session between the AI worker and the server, against the tools of
# `API/mcp/tools.json`, the members of a message handed to the MCP server as
# they came, its response put in the payload of the reply and nothing replied
# when it gives none. No process is started.

import dispatch, engine_mcp, jslb, json, mcp, os, unittest, unittest.mock
from collections.abc import Callable
from i18n import i18n
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The `initialize` request the AI worker's MCP client sends the server.
_INITIALIZE_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "hyperposition-engine", "version": "0"},
    },
}

# The notification the client sends once the `initialize` reply is in.
_INITIALIZED_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
}

# The `tools/list` request the client sends after the notification.
_LIST_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
}

# The response to `initialize`: the pinned revision, `tools`, the server.
_INITIALIZE_RESPONSE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "protocolVersion": "2025-06-18",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "xsjs-server", "version": "0"},
    },
}

# The wire id of the line that carries `initialize`.
_INITIALIZE_WIRE = 7

# The wire id of the line that carries `tools/list`.
_LIST_WIRE = 8

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


# Builds a tool from an entry of the API file, never a permit tool.
def _tool_make(entry: dict[str, Any]) -> mcp.Tool:
    return mcp.Tool(
        entry["name"], entry["description"], entry["inputSchema"], False
    )


# The response to `tools/list`: each tool of the API file, with no permit.
def _list_response() -> dict[str, Any]:
    tools = [
        {
            "name": entry["name"],
            "description": entry["description"],
            "inputSchema": entry["inputSchema"],
        }
        for entry in _entries_read()
    ]
    return {"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}}


# Stands for the function of a tool that the test never calls.
def _tool_refuse(arguments: dict[str, Any]) -> mcp.ToolResult:
    raise AssertionError("a tool was called")


# Answers a call with the text `hi`.
def _tool_echo(arguments: dict[str, Any]) -> mcp.ToolResult:
    return mcp.ToolResult([{"type": "text", "text": "hi"}], False)


# Makes the server's MCP server with the tools of the API file.
def _server_make() -> mcp.Server:
    server = mcp.Server("xsjs-server", "0")
    for entry in _entries_read():
        server.tool_register(_tool_make(entry), _tool_refuse)
    return server


# Gives each test an empty handler table and no registration.
class IsolatedCase(unittest.TestCase):
    # Patches the table and the state until the test ends.
    def setUp(self) -> None:
        table = unittest.mock.patch.dict(_HANDLERS_TARGET, {}, clear=True)
        state = unittest.mock.patch(_SERVER_TARGET, None)
        for patcher in (table, state):
            patcher.start()
            self.addCleanup(patcher.stop)

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the exchange with a real MCP server.
class TestExchange(IsolatedCase):
    # Opening a session answers `initialize` and `tools/list` only.
    def test_session_opened(self) -> None:
        engine_mcp.handlers_register(_server_make())
        lines = [
            _line_make(_INITIALIZE_WIRE, **_INITIALIZE_MESSAGE),
            _line_make(None, **_INITIALIZED_MESSAGE),
            _line_make(_LIST_WIRE, **_LIST_MESSAGE),
        ]
        replies: list[tuple[int | None, dict[str, Any]]] = []
        for line in lines:
            reply = dispatch.line_dispatch(line)
            if reply is not None:
                replies.append((reply[0]["r"], jslb.payload_of(reply)))
        expected = [
            (_INITIALIZE_WIRE, _INITIALIZE_RESPONSE),
            (_LIST_WIRE, _list_response()),
        ]
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
        message = i18n("mcp.method_unknown", "nothing/here")
        self.assertEqual(payload["error"]["message"], message)

    # A request that came as a push, with no wire id, cannot be answered.
    def test_request_pushed(self) -> None:
        engine_mcp.handlers_register(_server_make())
        line = _line_make(None, jsonrpc="2.0", id=1, method="ping")
        self.raise_check(
            ValueError,
            i18n("dispatch.notification_replied", "mcp", 0),
            lambda: dispatch.line_dispatch(line),
        )


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
    def test_called_early(self) -> None:
        line = _line_make(None, **_MESSAGES[3])
        self.raise_check(
            RuntimeError,
            i18n("engine_mcp.not_registered"),
            lambda: engine_mcp.mcp_message(line, **_MESSAGES[3]),
        )

    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_mcp.handlers_register(_server_make())
        self.raise_check(
            ValueError,
            i18n("dispatch.handler_twice", "mcp", 0),
            lambda: engine_mcp.handlers_register(_server_make()),
        )
