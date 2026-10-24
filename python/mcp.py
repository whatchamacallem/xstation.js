# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The Model Context Protocol server and client, transport agnostic: `JSON-RPC
# 2.0` messages go in and out as dicts. The server answers `initialize`,
# `ping`, `tools/list` and `tools/call` and takes `notifications/initialized`,
# for the revision in `_PROTOCOL_VERSION`, with the capability `tools` only.
# MCP is a testing protocol for now: no AI is a requirement of the tests yet.
#
# Fail loud: an exception while a request is handled answers that request,
# then the server stops. A tool's exception, an `RpcError` it raises
# included, answers with a `tools/call` result whose `isError` is true and
# whose one text content is the JSON text of the cascade, `message`, `stack`
# and nested `cause`, as `dispatch.cause_make` writes it. An `RpcError` or
# any other exception of a method answers with a `JSON-RPC` error whose
# `data` is that cascade. `failure_take` then returns the exception once:
# `engine_mcp` returns it as a `dispatch.Failure`, and `mcp_stdio` writes the
# answer, then raises it. A test driver reads `isError`, or the error, to
# tell an exception from the expected response. A message that is not a
# `JSON-RPC 2.0` request is answered with -32600 and is no exception, as in
# TypeScript. Continuing after an exception is deferred, its design in
# TAP_PLAN.md section 5.4.

import dispatch, json
from collections.abc import Callable
from typing import Any, NamedTuple, TypeAlias, TypeGuard
from internationalization import i18n

# The only `JSON-RPC` version this module speaks.
_JSONRPC_VERSION = "2.0"

# The revision of the Model Context Protocol this module emulates.
_PROTOCOL_VERSION = "2025-06-18"

# The method that opens a session.
_METHOD_INITIALIZE = "initialize"

# The notification a client sends once the `initialize` reply is in.
_METHOD_INITIALIZED = "notifications/initialized"

# The method that checks the other side answers.
_METHOD_PING = "ping"

# The method that lists the tools.
_METHOD_TOOLS_LIST = "tools/list"

# The method that runs a tool.
_METHOD_TOOLS_CALL = "tools/call"

# The code of a message that is not a valid request.
_CODE_REQUEST_INVALID = -32600

# The code of a request for a method that is not served.
_CODE_METHOD_UNKNOWN = -32601

# The code of params that a method cannot use.
_CODE_PARAMS_INVALID = -32602

# The code of an exception that a method raised and is not an `RpcError`.
_CODE_INTERNAL_ERROR = -32603

# A `JSON-RPC 2.0` message as a dict: `jsonrpc`, then `id`, `method` and so on.
Message: TypeAlias = dict[str, Any]


# A tool as `tools/list` returns it. `permit` goes into `_meta.xsjs`.
class Tool(NamedTuple):
    name: str
    description: str
    input_schema: dict[str, Any]
    permit: bool


# The result of a call: content blocks and whether it is an error.
class ToolResult(NamedTuple):
    content: list[dict[str, Any]]
    is_error: bool


# A `JSON-RPC` error with its code, raised by a method and sent as `error`.
class RpcError(Exception):
    # Keeps the code and the data beside the message of the exception.
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


# Returns whether a decoded value is a JSON object.
def _object_is(value: object) -> TypeGuard[dict[str, Any]]:
    return isinstance(value, dict)


# Returns whether a value can be a request id, a number or a string.
def _id_valid(value: object) -> bool:
    return isinstance(value, int | str) and not isinstance(value, bool)


# Builds a response that carries a result.
def _result_make(request_id: Any, result: dict[str, Any]) -> Message:
    return {"jsonrpc": _JSONRPC_VERSION, "id": request_id, "result": result}


# Builds an error response, with `data` only when there is some.
def _error_make(
    request_id: Any, code: int, message: str, data: Any
) -> Message:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": _JSONRPC_VERSION, "id": request_id, "error": error}


# Builds the error response to a message that is not a valid request.
def _invalid_make(request_id: Any) -> Message:
    return _error_make(
        request_id, _CODE_REQUEST_INVALID, i18n("mcp.request_invalid"), None
    )


# Returns a tool as `tools/list` shows it, with `_meta` for a permit tool only.
def _tool_dict(tool: Tool) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": tool.input_schema,
    }
    if tool.permit:
        entry["_meta"] = {"xsjs": {"permit": True}}
    return entry


# Reads a tool out of one entry of a `tools/list` result.
def _tool_parse(entry: dict[str, Any]) -> Tool:
    xsjs = entry.get("_meta", {}).get("xsjs", {})
    return Tool(
        entry["name"],
        entry["description"],
        entry["inputSchema"],
        xsjs.get("permit", False),
    )


# Reads the tools out of a `tools/list` result.
def _tools_parse(result: dict[str, Any]) -> list[Tool]:
    return [_tool_parse(entry) for entry in result["tools"]]


# Reads a tool result out of a `tools/call` result.
def _result_parse(result: dict[str, Any]) -> ToolResult:
    return ToolResult(result["content"], result.get("isError", False))


# The MCP server, transport agnostic, revision `2025-06-18` pinned.
class Server:
    # Keeps the identity `initialize` reports and starts with no tools.
    def __init__(self, name: str, version: str) -> None:
        self._name = name
        self._version = version
        self._tools: dict[str, Tool] = {}
        self._calls: dict[str, Callable[[dict[str, Any]], ToolResult]] = {}
        self._failure: BaseException | None = None
        self._methods: dict[str, Callable[[Any], dict[str, Any]]] = {
            _METHOD_INITIALIZE: self._initialize_run,
            _METHOD_PING: self._ping_run,
            _METHOD_TOOLS_LIST: self._list_run,
            _METHOD_TOOLS_CALL: self._call_run,
        }

    # Registers a tool and the function that runs it on its arguments.
    def tool_register(
        self, tool: Tool, fn: Callable[[dict[str, Any]], ToolResult]
    ) -> None:
        if tool.name in self._tools:
            raise ValueError(i18n("mcp.tool_twice", tool.name))
        self._tools[tool.name] = tool
        self._calls[tool.name] = fn

    # Handles one message. Returns the response, or None for a notification.
    def message_handle(self, message: Message) -> Message | None:
        method = message.get("method")
        request_id = message.get("id")
        reply_id = request_id if _id_valid(request_id) else None
        version_ok = message.get("jsonrpc") == _JSONRPC_VERSION
        if not version_ok or not isinstance(method, str):
            return _invalid_make(reply_id)
        if "id" not in message:
            return None
        if reply_id is None:
            return _invalid_make(None)
        try:
            result = self._method_run(method, message.get("params"))
        except RpcError as error:
            self._failure = error
            return _error_make(
                reply_id, error.code, str(error), dispatch.cause_make(error)
            )
        except Exception as error:
            self._failure = error
            return _error_make(
                reply_id,
                _CODE_INTERNAL_ERROR,
                str(error),
                dispatch.cause_make(error),
            )
        return _result_make(reply_id, result)

    # The exception of the last request answered with one, then None.
    def failure_take(self) -> BaseException | None:
        failure = self._failure
        self._failure = None
        return failure

    # Runs the method a request names, raising `RpcError` for an unknown one.
    def _method_run(self, method: str, params: Any) -> dict[str, Any]:
        if method not in self._methods:
            raise RpcError(
                _CODE_METHOD_UNKNOWN, i18n("mcp.method_unknown", method)
            )
        return self._methods[method](params)

    # Answers `initialize` with the revision, capabilities and identity.
    def _initialize_run(self, params: Any) -> dict[str, Any]:
        return {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": self._name, "version": self._version},
        }

    # Answers `ping` with an empty result.
    def _ping_run(self, params: Any) -> dict[str, Any]:
        return {}

    # Answers `tools/list` with the tools in the order they were registered.
    def _list_run(self, params: Any) -> dict[str, Any]:
        return {"tools": [_tool_dict(tool) for tool in self._tools.values()]}

    # Answers `tools/call` by running the named tool on its arguments.
    def _call_run(self, params: Any) -> dict[str, Any]:
        if not _object_is(params):
            raise RpcError(_CODE_PARAMS_INVALID, i18n("mcp.call_params"))
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not _object_is(arguments):
            raise RpcError(_CODE_PARAMS_INVALID, i18n("mcp.call_params"))
        if name not in self._calls:
            raise RpcError(
                _CODE_PARAMS_INVALID, i18n("mcp.tool_unknown", name)
            )
        try:
            result = self._calls[name](arguments)
        except Exception as error:
            self._failure = error
            text = json.dumps(
                dispatch.cause_make(error),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            return {
                "content": [{"type": "text", "text": text}],
                "isError": True,
            }
        return {"content": result.content, "isError": result.is_error}


# The MCP client: sends through `send`, receives through `message_handle`.
class Client:
    # Keeps the identity to announce, the transport and the replies awaited.
    def __init__(
        self, name: str, version: str, send: Callable[[Message], None]
    ) -> None:
        self._name = name
        self._version = version
        self._send = send
        self._id_next = 1
        self._waiting: dict[int, Callable[[dict[str, Any]], None]] = {}

    # Feeds a message the transport received.
    def message_handle(self, message: Message) -> None:
        if "method" in message:
            raise ValueError(i18n("mcp.message_unexpected", message["method"]))
        reply_id: object = message["id"]
        if type(reply_id) is not int:
            raise ValueError(i18n("mcp.reply_id_refused", repr(reply_id)))
        if reply_id not in self._waiting:
            raise ValueError(i18n("mcp.reply_unknown", reply_id))
        fn = self._waiting.pop(reply_id)
        if "error" in message:
            error = message["error"]
            raise RpcError(error["code"], error["message"], error.get("data"))
        fn(message["result"])

    # Sends `initialize`, then `notifications/initialized` on its reply.
    def initialize_send(self, fn: Callable[[dict[str, Any]], None]) -> None:
        params: dict[str, Any] = {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": self._name, "version": self._version},
        }
        self._request_send(
            _METHOD_INITIALIZE,
            params,
            lambda result: self._initialized_send(fn, result),
        )

    # Asks for the tools of the server and passes them to `fn`.
    def tools_list(self, fn: Callable[[list[Tool]], None]) -> None:
        self._request_send(
            _METHOD_TOOLS_LIST, None, lambda result: fn(_tools_parse(result))
        )

    # Calls a tool of the server and passes its result to `fn`.
    def tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
        fn: Callable[[ToolResult], None],
    ) -> None:
        self._request_send(
            _METHOD_TOOLS_CALL,
            {"name": name, "arguments": arguments},
            lambda result: fn(_result_parse(result)),
        )

    # Sends a request with the next id and keeps `fn` for its reply.
    def _request_send(
        self,
        method: str,
        params: dict[str, Any] | None,
        fn: Callable[[dict[str, Any]], None],
    ) -> None:
        request_id = self._id_next
        self._id_next += 1
        self._waiting[request_id] = fn
        request: Message = {
            "jsonrpc": _JSONRPC_VERSION,
            "id": request_id,
            "method": method,
        }
        if params is not None:
            request["params"] = params
        self._send(request)

    # Sends the notification that follows the reply, then passes the result on.
    def _initialized_send(
        self, fn: Callable[[dict[str, Any]], None], result: dict[str, Any]
    ) -> None:
        self._send(
            {"jsonrpc": _JSONRPC_VERSION, "method": _METHOD_INITIALIZED}
        )
        fn(result)
