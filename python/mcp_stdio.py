#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The stdio transport of the MCP server, so an external agent drives the
# server's tools directly: newline delimited `JSON-RPC` on stdin and stdout.
# Run as python3 python/mcp_stdio.py --root ROOT. Each input line is parsed
# by `jslb.json_decode`, the decoders' door for bad numbers. A line that is
# not a JSON object is a hard error: the exception reaches stderr and the
# exit code is 1. After a request answered with an exception it writes the
# answer, then raises the exception, so the process exits 1: fail loud.
# The modules beside this file are imported inside the functions that use
# them, after their bytecode has been sent to build/.

import argparse, io, json, os, sys
from collections.abc import Callable
from typing import Any, TextIO, cast

# The directory that holds this file and the modules it imports.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The encoding of stdin and stdout, which MCP's stdio transport fixes.
_ENCODING = "utf-8"

# The name the server reports to a client.
_SERVER_NAME = "xsjs-server"

# The version the server reports to a client.
_SERVER_VERSION = "0"

# The settings file in the root.
_SETTINGS_NAME = "settings.json"

# Bytecode of the modules the functions below import goes in `build/pycache`.
sys.pycache_prefix = os.path.join(
    os.path.dirname(_PYTHON_PATH), "build", "pycache"
)


# Parses one input line, raising when it is not a JSON object.
def _line_parse(number: int, line: str) -> dict[str, Any]:
    import jslb
    from internationalization import i18n

    try:
        message: object = jslb.json_decode(line)
    except jslb.WireError as error:
        raise ValueError(
            i18n("mcp_stdio.line_malformed", number, error)
        ) from error
    if not isinstance(message, dict):
        raise ValueError(i18n("mcp_stdio.line_object", number))
    return cast(dict[str, Any], message)


# Encodes a message as compact JSON text.
def _text_make(message: dict[str, Any]) -> str:
    return json.dumps(message, ensure_ascii=False, separators=(",", ":"))


# Serves the tools `register` adds to a new `mcp.Server` on a pair of streams.
def stdio_run(
    register: Callable[[Any], None], stdin: TextIO, stdout: TextIO
) -> int:
    import mcp

    server = mcp.Server(_SERVER_NAME, _SERVER_VERSION)
    register(server)
    for number, line in enumerate(stdin, 1):
        response = server.message_handle(_line_parse(number, line))
        if response is not None:
            stdout.write(_text_make(response) + "\n")
            stdout.flush()
        error = server.failure_take()
        if error is not None:
            raise error
    return 0


# Serves the server's MCP tools as newline delimited `JSON-RPC` on stdio.
def stdio_serve(argv: list[str]) -> int:
    import engine_system, settings

    parser = argparse.ArgumentParser(
        description="Serve the server's MCP tools as newline delimited"
        " JSON-RPC on stdin and stdout."
    )
    parser.add_argument("--root", required=True, help="the server's root")
    root: str = parser.parse_args(argv).root
    loaded = settings.settings_load(os.path.join(root, _SETTINGS_NAME))
    debug: bool = loaded["debug"]
    # The streams take the transport's encoding in place of the locale's.
    for stream in (sys.stdin, sys.stdout):
        cast(io.TextIOWrapper, stream).reconfigure(encoding=_ENCODING)
    return stdio_run(
        lambda server: engine_system.tools_register(server, root, debug),
        sys.stdin,
        sys.stdout,
    )


if __name__ == "__main__":
    sys.exit(stdio_serve(sys.argv[1:]))
