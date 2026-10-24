# The Model Context Protocol server and client, transport agnostic, revision
# "2025-06-18" pinned: JSON-RPC 2.0 messages go in and out as dicts. MCP is a
# testing protocol for now: no AI is a requirement of the tests yet.
#
# Fail loud: an exception while a request is handled answers that request,
# then the server stops. A tool's exception answers with a `tools/call`
# result whose `isError` is true and whose one text content is the JSON text
# of the cascade, `message`, `stack` and nested `cause`, as
# `dispatch.cause_make` writes it. An `RpcError` or any other exception of a
# method answers with a JSON-RPC error whose `data` is that cascade.
# `failure_take` then returns the exception once: `engine_mcp` returns it as
# a `dispatch.Failure`, and `mcp_stdio` writes the answer, then raises it. A
# test driver reads `isError`, or the error, to tell an exception from the
# expected response. A message that is not a JSON-RPC 2.0 request is
# answered with -32600 and is no exception, as in TypeScript. Continuing
# after an exception is deferred, its design in TAP_PLAN.md section 5.4.

from collections.abc import Callable
from typing import Any, NamedTuple, TypeAlias

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
    code: int
    data: Any

# The MCP server.
class Server:
    def __init__(self, name: str, version: str) -> None: ...
    # Registers a tool and the function that runs it on its arguments.
    def tool_register(
        self, tool: Tool, fn: Callable[[dict[str, Any]], ToolResult]
    ) -> None: ...
    # Handles one message. Returns the response, or None for a notification.
    def message_handle(self, message: Message) -> Message | None: ...
    # The exception of the last request answered with one, then None.
    def failure_take(self) -> BaseException | None: ...

# The MCP client: sends through `send`, receives through `message_handle`.
class Client:
    def __init__(
        self, name: str, version: str, send: Callable[[Message], None]
    ) -> None: ...
    # Feeds a message the transport received.
    def message_handle(self, message: Message) -> None: ...
    # Sends `initialize`, then `notifications/initialized` on its reply.
    def initialize_send(
        self, fn: Callable[[dict[str, Any]], None]
    ) -> None: ...
    def tools_list(self, fn: Callable[[list[Tool]], None]) -> None: ...
    def tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
        fn: Callable[[ToolResult], None],
    ) -> None: ...
