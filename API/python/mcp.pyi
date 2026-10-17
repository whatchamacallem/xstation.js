from collections.abc import Callable
from typing import Any, NamedTuple

# A JSON-RPC 2.0 message as a dict: `jsonrpc`, then `id`, `method`,
# `params`, `result` or `error` as the kind requires.
Message = dict[str, Any]

# A tool as `tools/list` returns it; `permit` goes into `_meta.xsjs`.
class Tool(NamedTuple):
    name: str
    description: str
    input_schema: dict[str, Any]
    permit: bool

# The result of a call: content blocks and whether it is an error.
class ToolResult(NamedTuple):
    content: list[dict[str, Any]]
    is_error: bool

# A JSON-RPC error with its code, raised by a method and sent as `error`.
class RpcError(Exception):
    code: int
    data: Any

# The MCP server: `initialize`, `notifications/initialized`, `ping`,
# `tools/list`, `tools/call`. Transport-agnostic.
class Server:
    def __init__(self, name: str, version: str, protocol_version: str) -> None: ...
    # Registers a tool and the function that runs it on its arguments.
    def tool_register(self, tool: Tool, fn: Callable[[dict[str, Any]], ToolResult]) -> None: ...
    # Handles one message. Returns the response, or None for a
    # notification. A method's raise becomes an `error` response.
    def message_handle(self, message: Message) -> Message | None: ...

# The MCP client: sends through `send`, receives through
# `message_handle`, matches responses by id.
class Client:
    def __init__(self, name: str, version: str, protocol_version: str, send: Callable[[Message], None]) -> None: ...
    # Feeds a message the transport received.
    def message_handle(self, message: Message) -> None: ...
    # Sends `initialize`, then `notifications/initialized` on its reply,
    # and calls `fn` with the server's capabilities.
    def initialize_send(self, fn: Callable[[dict[str, Any]], None]) -> None: ...
    def tools_list(self, fn: Callable[[list[Tool]], None]) -> None: ...
    def tool_call(self, name: str, arguments: dict[str, Any], fn: Callable[[ToolResult], None]) -> None: ...
