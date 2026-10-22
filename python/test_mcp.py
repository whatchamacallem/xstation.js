# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the MCP server on messages handed to it, the client against a server
# through direct function calls and through a transport that answers later,
# with the tools of API/mcp/tools.json. No transport and no process is used.

import functools, json, mcp, os, unittest
from i18n import i18n
from typing import Any

# The root of the checkout.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The reply to `initialize` as the test server writes it.
_INITIALIZE_REPLY = (
    '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",'
    '"capabilities":{"tools":{}},'
    '"serverInfo":{"name":"xsjs-test","version":"1"}}}'
)

# The `initialize` request the test client sends.
_INITIALIZE_REQUEST = (
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":'
    '{"protocolVersion":"2025-06-18","capabilities":{},'
    '"clientInfo":{"name":"xsjs-client","version":"2"}}}'
)

# The schema of a tool that takes nothing.
_EMPTY_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

# The error member a server answers to a message that is no request.
_INVALID_ERROR: dict[str, Any] = {"code": -32600, "message": "no"}


# Reads the tool entries of one side of the API file, "browser" or "server".
def _entries_read(side: str) -> list[dict[str, Any]]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data[side]["result"]["tools"]


# Finds the entry of the named tool on one side of the API file.
def _entry_find(side: str, name: str) -> dict[str, Any]:
    for entry in _entries_read(side):
        if entry["name"] == name:
            return entry
    raise AssertionError(f"no tool {name} on the {side} side")


# Builds a tool from an entry of the API file.
def _tool_make(entry: dict[str, Any]) -> mcp.Tool:
    permit = entry.get("_meta", {}).get("xsjs", {}).get("permit", False)
    return mcp.Tool(
        entry["name"], entry["description"], entry["inputSchema"], permit
    )


# Builds a result that holds one block of text.
def _result_make(text: str) -> mcp.ToolResult:
    return mcp.ToolResult([{"type": "text", "text": text}], False)


# Builds a request, leaving out `params` when there are none.
def _request_make(
    request_id: Any, method: str, params: Any = None
) -> mcp.Message:
    request: mcp.Message = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        request["params"] = params
    return request


# Encodes a value as compact JSON text with its keys in order.
def _text_make(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


# Hands a message to a server and returns the response it must give.
def _response_get(server: mcp.Server, message: mcp.Message) -> mcp.Message:
    response = server.message_handle(message)
    if response is None:
        raise AssertionError(f"no response to {message}")
    return response


# Carries the messages of a client to a server and the responses back.
class DirectLink:
    # Makes a client whose transport is a call of the server.
    def __init__(self, server: mcp.Server) -> None:
        self.server = server
        self.sent: list[mcp.Message] = []
        self.log: list[str] = []
        self.results: list[Any] = []
        self.client = mcp.Client("xsjs-client", "2", self.message_send)

    # Logs a message, gives it to the server and feeds back the response.
    def message_send(self, message: mcp.Message) -> None:
        self.sent.append(message)
        self.log.append(message["method"])
        response = self.server.message_handle(message)
        if response is not None:
            self.client.message_handle(response)

    # Logs a callback and keeps what it received.
    def result_keep(self, result: Any) -> None:
        self.log.append("callback")
        self.results.append(result)


# Tests the server on messages handed to it directly.
class TestServer(unittest.TestCase):
    # Registers the server tools and two browser tools of the API file.
    def setUp(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.server = mcp.Server("xsjs-test", "1")
        self.entries = _entries_read("server")
        self.entries.append(_entry_find("browser", "kv_get"))
        self.entries.append(_entry_find("browser", "console_run"))
        for entry in self.entries:
            self.server.tool_register(
                _tool_make(entry),
                functools.partial(self.tool_run, entry["name"]),
            )

    # Records a call of the named tool and answers with the name as text.
    def tool_run(self, name: str, arguments: dict[str, Any]) -> mcp.ToolResult:
        self.calls.append((name, arguments))
        return _result_make(name)

    # Raises the error given, as a tool function that fails does.
    def tool_raise(
        self, error: Exception, arguments: dict[str, Any]
    ) -> mcp.ToolResult:
        raise error

    # Registers a tool that raises the error given when it is called.
    def failing_register(self, error: Exception) -> None:
        self.server.tool_register(
            mcp.Tool("fail", "Fails.", _EMPTY_SCHEMA, False),
            functools.partial(self.tool_raise, error),
        )

    # The initialize reply holds the revision, tools only and the identity.
    def test_initialize_reply(self) -> None:
        params = {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "external-agent", "version": "0"},
        }
        request = _request_make(1, "initialize", params)
        response = _response_get(self.server, request)
        self.assertEqual(_text_make(response), _INITIALIZE_REPLY)

    # A notification, known or not, is never answered.
    def test_notification_none(self) -> None:
        for method in ("notifications/initialized", "notifications/unknown"):
            message = {"jsonrpc": "2.0", "method": method}
            self.assertIsNone(self.server.message_handle(message))

    # Ping answers an empty result and echoes a number or a string id.
    def test_ping_reply(self) -> None:
        response = _response_get(self.server, _request_make(3, "ping"))
        self.assertEqual(
            _text_make(response), '{"jsonrpc":"2.0","id":3,"result":{}}'
        )
        response = _response_get(self.server, _request_make("a", "ping"))
        self.assertEqual(
            _text_make(response), '{"jsonrpc":"2.0","id":"a","result":{}}'
        )

    # The listed tools equal the API file entry by entry, key order included.
    def test_list_shape(self) -> None:
        response = _response_get(self.server, _request_make(2, "tools/list"))
        tools = response["result"]["tools"]
        self.assertEqual(_text_make(tools), _text_make(self.entries))
        self.assertEqual(len(tools), 4)

    # Only a permit tool carries `_meta`.
    def test_list_permit(self) -> None:
        response = _response_get(self.server, _request_make(2, "tools/list"))
        tools = response["result"]["tools"]
        self.assertEqual(
            [tool["name"] for tool in tools if "_meta" in tool],
            ["console_run"],
        )
        self.assertEqual(tools[3]["_meta"], {"xsjs": {"permit": True}})

    # A call passes the arguments to the function and returns its result.
    def test_call_result(self) -> None:
        params = {"name": "kv_get", "arguments": {"ref": "/a/b"}}
        response = _response_get(
            self.server, _request_make(5, "tools/call", params)
        )
        self.assertEqual(
            response,
            {
                "jsonrpc": "2.0",
                "id": 5,
                "result": {
                    "content": [{"type": "text", "text": "kv_get"}],
                    "isError": False,
                },
            },
        )
        self.assertEqual(self.calls, [("kv_get", {"ref": "/a/b"})])

    # The server only lists the permit flag: it runs a permit tool called.
    def test_call_permit(self) -> None:
        arguments = {"text": "ls", "timeout_seconds": 1}
        params = {"name": "console_run", "arguments": arguments}
        response = _response_get(
            self.server, _request_make(5, "tools/call", params)
        )
        self.assertEqual(response["result"]["isError"], False)
        self.assertEqual(self.calls, [("console_run", arguments)])

    # A result flagged as an error is still a result, not an error response.
    def test_call_flagged(self) -> None:
        flagged = mcp.ToolResult([{"type": "text", "text": "bad"}], True)
        self.server.tool_register(
            mcp.Tool("flag", "Flags.", _EMPTY_SCHEMA, False),
            lambda arguments: flagged,
        )
        params = {"name": "flag", "arguments": {}}
        response = _response_get(
            self.server, _request_make(6, "tools/call", params)
        )
        self.assertNotIn("error", response)
        self.assertEqual(
            response["result"],
            {"content": [{"type": "text", "text": "bad"}], "isError": True},
        )

    # Absent arguments reach the function as an empty object.
    def test_call_bare(self) -> None:
        response = _response_get(
            self.server, _request_make(6, "tools/call", {"name": "kv_get"})
        )
        self.assertIn("result", response)
        self.assertEqual(self.calls, [("kv_get", {})])

    # An exception of a tool function becomes an error response with a stack.
    def test_call_raises(self) -> None:
        self.failing_register(ValueError("boom"))
        params = {"name": "fail", "arguments": {}}
        response = _response_get(
            self.server, _request_make(7, "tools/call", params)
        )
        self.assertNotIn("result", response)
        self.assertEqual(response["id"], 7)
        self.assertEqual(response["error"]["code"], -32603)
        self.assertEqual(response["error"]["message"], "boom")
        self.assertIn("ValueError: boom", response["error"]["data"]["stack"])

    # An `RpcError` of a tool function keeps its code and data.
    def test_error_kept(self) -> None:
        self.failing_register(mcp.RpcError(-32000, "no", {"why": 1}))
        params = {"name": "fail", "arguments": {}}
        response = _response_get(
            self.server, _request_make(8, "tools/call", params)
        )
        self.assertEqual(
            _text_make(response),
            '{"jsonrpc":"2.0","id":8,"error":'
            '{"code":-32000,"message":"no","data":{"why":1}}}',
        )

    # An `RpcError` with no data answers an error with no `data` member.
    def test_data_absent(self) -> None:
        self.failing_register(mcp.RpcError(-32000, "no"))
        params = {"name": "fail", "arguments": {}}
        response = _response_get(
            self.server, _request_make(8, "tools/call", params)
        )
        self.assertEqual(
            _text_make(response),
            '{"jsonrpc":"2.0","id":8,"error":{"code":-32000,"message":"no"}}',
        )

    # A tool nobody registered is invalid params, named in the message.
    def test_call_unknown(self) -> None:
        params = {"name": "nothing", "arguments": {}}
        response = _response_get(
            self.server, _request_make(9, "tools/call", params)
        )
        self.assertEqual(response["error"]["code"], -32602)
        self.assertEqual(
            response["error"]["message"], i18n("mcp.tool_unknown", "nothing")
        )
        self.assertEqual(self.calls, [])

    # Params without a name or with arguments that are no object are invalid.
    def test_call_params(self) -> None:
        cases: list[Any] = [
            None,
            [],
            {},
            {"arguments": {}},
            {"name": 1, "arguments": {}},
            {"name": "kv_get", "arguments": []},
        ]
        for params in cases:
            with self.subTest(params=params):
                response = _response_get(
                    self.server, _request_make(10, "tools/call", params)
                )
                self.assertEqual(response["id"], 10)
                self.assertEqual(response["error"]["code"], -32602)
                self.assertEqual(
                    response["error"]["message"], i18n("mcp.call_params")
                )
        self.assertEqual(self.calls, [])

    # An unknown method is not found, named in the message, with the same id.
    def test_method_unknown(self) -> None:
        for request_id in (11, "b"):
            response = _response_get(
                self.server, _request_make(request_id, "foo/bar")
            )
            self.assertEqual(response["id"], request_id)
            self.assertEqual(response["error"]["code"], -32601)
            self.assertEqual(
                response["error"]["message"],
                i18n("mcp.method_unknown", "foo/bar"),
            )

    # A message that is no request is invalid, with the id only if it is valid.
    def test_request_invalid(self) -> None:
        cases: list[tuple[mcp.Message, Any]] = [
            ({"id": 1, "method": "ping"}, 1),
            ({"jsonrpc": "2.0", "id": 2}, 2),
            ({"jsonrpc": "1.0", "id": 3, "method": "ping"}, 3),
            ({"jsonrpc": "2.0", "id": True, "method": "ping"}, None),
            ({"jsonrpc": "2.0", "id": None, "method": "ping"}, None),
            ({"jsonrpc": "2.0", "id": [1], "method": "ping"}, None),
            ({"jsonrpc": "2.0", "method": 5}, None),
        ]
        for message, reply_id in cases:
            with self.subTest(message=message):
                response = _response_get(self.server, message)
                self.assertEqual(response["id"], reply_id)
                self.assertEqual(response["error"]["code"], -32600)
                self.assertEqual(
                    response["error"]["message"], i18n("mcp.request_invalid")
                )

    # Registering a name twice raises.
    def test_tool_twice(self) -> None:
        tool = _tool_make(self.entries[0])
        with self.assertRaises(ValueError) as caught:
            self.server.tool_register(tool, lambda arguments: _result_make(""))
        self.assertEqual(
            str(caught.exception), i18n("mcp.tool_twice", tool.name)
        )


# Tests the client against a server and against a transport that is slow.
class TestClient(unittest.TestCase):
    # Makes a server with the tools the API file lists and a client on it.
    def setUp(self) -> None:
        self.server = mcp.Server("xsjs-test", "1")
        self.entries = _entries_read("server")
        self.entries.append(_entry_find("browser", "kv_get"))
        self.entries.append(_entry_find("browser", "console_run"))
        for entry in self.entries:
            self.server.tool_register(
                _tool_make(entry),
                functools.partial(self.tool_run, entry["name"]),
            )
        self.rig = DirectLink(self.server)

    # Answers with the name of the tool as text.
    def tool_run(self, name: str, arguments: dict[str, Any]) -> mcp.ToolResult:
        return _result_make(name)

    # Initializing sends the request, then the notification, then calls back.
    def test_initialize_flow(self) -> None:
        self.rig.client.initialize_send(self.rig.result_keep)
        self.assertEqual(
            self.rig.log,
            ["initialize", "notifications/initialized", "callback"],
        )
        self.assertEqual(_text_make(self.rig.sent[0]), _INITIALIZE_REQUEST)
        self.assertEqual(
            _text_make(self.rig.sent[1]),
            '{"jsonrpc":"2.0","method":"notifications/initialized"}',
        )
        self.assertEqual(
            self.rig.results,
            [
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "xsjs-test", "version": "1"},
                }
            ],
        )

    # Ids run from 1 in each client, and a notification takes none.
    def test_ids_count(self) -> None:
        self.rig.client.initialize_send(self.rig.result_keep)
        self.rig.client.tools_list(self.rig.result_keep)
        self.rig.client.tool_call("kv_get", {}, self.rig.result_keep)
        ids = [message["id"] for message in self.rig.sent if "id" in message]
        self.assertEqual(ids, [1, 2, 3])
        other = DirectLink(self.server)
        other.client.tools_list(other.result_keep)
        self.assertEqual(other.sent[0]["id"], 1)

    # The tools passed on equal the ones registered, `permit` read back.
    def test_tools_list(self) -> None:
        self.rig.client.tools_list(self.rig.result_keep)
        self.assertEqual(
            self.rig.results,
            [[_tool_make(entry) for entry in self.entries]],
        )
        permits = [tool.permit for tool in self.rig.results[0]]
        self.assertEqual(permits, [False, False, False, True])

    # The result passed on is the tool's content and error flag.
    def test_tool_call(self) -> None:
        arguments = {"ref": "/a/b"}
        self.rig.client.tool_call("kv_get", arguments, self.rig.result_keep)
        self.assertEqual(self.rig.results, [_result_make("kv_get")])
        self.assertEqual(
            _text_make(self.rig.sent[0]),
            '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":'
            '{"name":"kv_get","arguments":{"ref":"/a/b"}}}',
        )

    # An error response raises out of `message_handle`, with no callback.
    def test_tool_error(self) -> None:
        with self.assertRaises(mcp.RpcError) as caught:
            self.rig.client.tool_call("nothing", {}, self.rig.result_keep)
        self.assertEqual(caught.exception.code, -32602)
        self.assertEqual(
            str(caught.exception), i18n("mcp.tool_unknown", "nothing")
        )
        self.assertIsNone(caught.exception.data)
        self.assertEqual(self.rig.results, [])

    # An error response carries its data to the exception.
    def test_error_data(self) -> None:
        client = mcp.Client("c", "0", lambda message: None)
        client.tools_list(lambda tools: None)
        reply = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "no", "data": {"why": 1}},
        }
        with self.assertRaises(mcp.RpcError) as caught:
            client.message_handle(reply)
        self.assertEqual(caught.exception.code, -32000)
        self.assertEqual(str(caught.exception), "no")
        self.assertEqual(caught.exception.data, {"why": 1})

    # A reply that comes later reaches the callback once, and only once.
    def test_reply_later(self) -> None:
        outbox: list[mcp.Message] = []
        results: list[mcp.ToolResult] = []
        client = mcp.Client("c", "0", outbox.append)
        client.tool_call("kv_get", {"ref": "/a/b"}, results.append)
        self.assertEqual(results, [])
        reply = _response_get(self.server, outbox[0])
        client.message_handle(reply)
        self.assertEqual(results, [_result_make("kv_get")])
        with self.assertRaises(ValueError) as caught:
            client.message_handle(reply)
        self.assertEqual(str(caught.exception), i18n("mcp.reply_unknown", 1))

    # A result with no `isError` member is not an error.
    def test_error_absent(self) -> None:
        outbox: list[mcp.Message] = []
        results: list[mcp.ToolResult] = []
        client = mcp.Client("c", "0", outbox.append)
        client.tool_call("kv_get", {}, results.append)
        client.message_handle(
            {"jsonrpc": "2.0", "id": 1, "result": {"content": []}}
        )
        self.assertEqual(results, [mcp.ToolResult([], False)])

    # A reply nobody asked for raises.
    def test_reply_unknown(self) -> None:
        with self.assertRaises(ValueError) as caught:
            self.rig.client.message_handle(
                {"jsonrpc": "2.0", "id": 99, "result": {}}
            )
        self.assertEqual(str(caught.exception), i18n("mcp.reply_unknown", 99))

    # An error response ends the wait for its id, so a second one is unknown.
    def test_error_pops(self) -> None:
        client = mcp.Client("c", "0", lambda message: None)
        client.tools_list(lambda tools: None)
        reply = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "no"},
        }
        with self.assertRaises(mcp.RpcError) as refused:
            client.message_handle(reply)
        self.assertEqual(refused.exception.code, -32000)
        self.assertEqual(str(refused.exception), "no")
        with self.assertRaises(ValueError) as caught:
            client.message_handle(reply)
        self.assertEqual(str(caught.exception), i18n("mcp.reply_unknown", 1))

    # A reply whose id is not an integer raises and leaves the wait in place.
    def test_id_refused(self) -> None:
        results: list[list[mcp.Tool]] = []
        client = mcp.Client("c", "0", lambda message: None)
        client.tools_list(results.append)
        replies: list[mcp.Message] = [
            {"jsonrpc": "2.0", "id": True, "result": {"tools": []}},
            {"jsonrpc": "2.0", "id": 1.0, "result": {"tools": []}},
            {"jsonrpc": "2.0", "id": "1", "result": {"tools": []}},
            {"jsonrpc": "2.0", "id": None, "error": _INVALID_ERROR},
        ]
        for reply in replies:
            with self.subTest(reply=reply):
                with self.assertRaises(ValueError) as caught:
                    client.message_handle(reply)
                self.assertEqual(
                    str(caught.exception),
                    i18n("mcp.reply_id_refused", repr(reply["id"])),
                )
        self.assertEqual(results, [])
        client.message_handle(
            {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        )
        self.assertEqual(results, [[]])

    # A request or a notification sent to the client raises.
    def test_request_received(self) -> None:
        for method in ("ping", "notifications/tools/list_changed"):
            with self.subTest(method=method):
                with self.assertRaises(ValueError) as caught:
                    self.rig.client.message_handle(
                        {"jsonrpc": "2.0", "id": 1, "method": method}
                    )
                self.assertEqual(
                    str(caught.exception),
                    i18n("mcp.message_unexpected", method),
                )
