import jslb, mcp

# `settings.put`: rewrites settings.json in the root, debug mode only.
def settings_put(
    line: jslb.Object, *, settings: dict[str, object]
) -> jslb.Object: ...

# `source.put`: one blob, written as `main_loop/<name>` in the root, debug.
def source_put(line: jslb.Object, *, name: str) -> jslb.Object: ...

# `system.restart`: execs Python itself to serve `main_loop`, debug only.
def system_restart(line: jslb.Object, *, main_loop: str) -> None: ...

# Registers the two tools of the server on the MCP server.
def tools_register(server: mcp.Server, root: str, debug: bool) -> None: ...

# Registers the three handlers, with the root and the debug gate they need.
def handlers_register(root: str, debug: bool) -> None: ...
