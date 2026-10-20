#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The stdio transport of the MCP server, so an external agent drives the
# server's tools directly: newline delimited `JSON-RPC` on stdin and stdout.
# Run as python3 python/mcp_stdio.py --root ROOT. A line that is not a JSON
# object is a hard error: the exception reaches stderr and the exit code is 1.

import argparse, engine_system, json, mcp, os, settings, sys
from collections.abc import Callable
from typing import TextIO, cast
from i18n import i18n

# The name the server reports to a client.
_SERVER_NAME = "xsjs-server"

# The version the server reports to a client.
_SERVER_VERSION = "0"

# The settings file in the root.
_SETTINGS_NAME = "settings.json"


# Parses one input line, raising when it is not a JSON object.
def _line_parse(number: int, line: str) -> mcp.Message:
    try:
        message: object = json.loads(line)
    except json.JSONDecodeError as error:
        raise ValueError(
            i18n("mcp_stdio.line_malformed", number, error)
        ) from error
    if not isinstance(message, dict):
        raise ValueError(i18n("mcp_stdio.line_object", number))
    return cast(mcp.Message, message)


# Encodes a message as compact JSON text, refusing NaN and infinities.
def _text_make(message: mcp.Message) -> str:
    return json.dumps(
        message, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


# Serves the tools `register` adds to a new server on a pair of streams.
def stdio_run(
    register: Callable[[mcp.Server], None], stdin: TextIO, stdout: TextIO
) -> int:
    server = mcp.Server(_SERVER_NAME, _SERVER_VERSION)
    register(server)
    for number, line in enumerate(stdin, 1):
        response = server.message_handle(_line_parse(number, line))
        if response is not None:
            stdout.write(_text_make(response) + "\n")
            stdout.flush()
    return 0


# Serves the server's MCP tools as newline delimited `JSON-RPC` on stdio.
def stdio_serve(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Serve the server's MCP tools as newline delimited"
        " JSON-RPC on stdin and stdout."
    )
    parser.add_argument("--root", required=True, help="the server's root")
    root: str = parser.parse_args(argv).root
    loaded = settings.settings_load(os.path.join(root, _SETTINGS_NAME))
    debug: bool = loaded["debug"]
    return stdio_run(
        lambda server: engine_system.tools_register(server, root, debug),
        sys.stdin,
        sys.stdout,
    )


if __name__ == "__main__":
    sys.exit(stdio_serve(sys.argv[1:]))
