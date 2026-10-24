# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handler of the `mcp` line: the payload is one `JSON-RPC` message for the
# server's MCP server, and the payload of the reply is its response, if it
# gives one. After an exception the handler returns a `dispatch.Failure` of
# that reply and the exception, which the main loop writes, then raises.

import dispatch, jslb, mcp
from internationalization import i18n


# The state the registration sets, which is empty until then.
class _McpState:
    # Starts with no MCP server.
    def __init__(self) -> None:
        self.server: mcp.Server | None = None


# The one state of the module.
_STATE = _McpState()


# Returns the MCP server, raising before the handler is registered.
def _server_get() -> mcp.Server:
    if _STATE.server is None:
        raise RuntimeError(i18n("engine_mcp.not_registered"))
    return _STATE.server


# Passes the message to the MCP server and replies with its response.
def mcp_message(
    line: jslb.Object, **message: object
) -> jslb.Object | dispatch.Failure | None:
    server = _server_get()
    response = server.message_handle(message)
    error = server.failure_take()
    if response is None:
        # A notification never runs, so a failure here cannot arise.
        if error is not None:
            raise error
        return None
    reply = dispatch.reply_make(line, **response)
    if error is not None:
        return dispatch.Failure(reply, error)
    return reply


# Registers the handler, with the MCP server that answers the messages.
def handlers_register(server: mcp.Server) -> None:
    _STATE.server = server
    dispatch.handler_register("mcp", 0, mcp_message)
