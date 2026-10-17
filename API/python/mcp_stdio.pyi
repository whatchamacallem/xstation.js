# The MCP stdio transport: newline-delimited JSON-RPC on stdin and stdout,
# serving the same `mcp.Server` and tools the engine serves over the `mcp`
# line, for an external agent. `python3 mcp_stdio.py --root <root>
# [--debug]`. Exits 0 at end of input, 1 on a fault.
def main(argv: list[str]) -> int: ...
