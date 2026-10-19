# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handler of the `mcp` line: the payload is one `JSON-RPC` message for the
# server's MCP server, and the payload of the reply is its response, if it
# gives one.

import dispatch, jslb, mcp
from i18n import i18n


# The state the registration sets, which is empty until then.
class _State:
    # Starts with no MCP server.
    def __init__(self) -> None:
        self.server: mcp.Server | None = None


# The one state of the module.
_STATE = _State()


# Returns the MCP server, raising before the handler is registered.
def _server_get() -> mcp.Server:
    if _STATE.server is None:
        raise RuntimeError(i18n("engine_mcp.not_registered"))
    return _STATE.server


# Passes the message to the MCP server and replies with its response.
def mcp_message(line: jslb.Object, **message: object) -> jslb.Object | None:
    response = _server_get().message_handle(message)
    if response is None:
        return None
    return dispatch.reply_make(line, **response)


# Registers the handler, with the MCP server that answers the messages.
def handlers_register(server: mcp.Server) -> None:
    _STATE.server = server
    dispatch.handler_register("mcp", 0, mcp_message)
