import dispatch, jslb, mcp

# `mcp`: a `JSON-RPC` message, after an exception a `dispatch.Failure`.
def mcp_message(
    line: jslb.Object, **message: object
) -> jslb.Object | dispatch.Failure | None: ...

# Registers the handler of `mcp` lines for the server given.
def handlers_register(server: mcp.Server) -> None: ...
