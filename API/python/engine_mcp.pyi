from typing import Any

from jslb import Object

# Handler of the `mcp` line: the payload is one JSON-RPC message for the
# server's `mcp.Server`. A response goes back as another `mcp` line; a
# notification gets nothing. The line itself never carries `i`.
def mcp(line: Object, **message: Any) -> None: ...
