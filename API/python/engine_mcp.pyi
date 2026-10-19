import jslb

# `mcp`: the payload is a `JSON-RPC` message for the server's MCP server.
def mcp_message(
    line: jslb.Object, **message: object
) -> jslb.Object | None: ...
