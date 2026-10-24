# Serves the server's MCP tools as newline delimited JSON-RPC on stdio. Each
# input line is parsed by `jslb.json_decode`, the decoders' door for bad
# numbers. After a request answered with an exception it writes the answer,
# then raises the exception, so the process exits 1: fail loud.

from collections.abc import Callable
from typing import TextIO

import mcp

# Serves the tools `register` adds to a new `mcp.Server` on the two streams.
def stdio_run(
    register: Callable[[mcp.Server], None], stdin: TextIO, stdout: TextIO
) -> int: ...

# Returns the exit code.
def stdio_serve(argv: list[str]) -> int: ...
