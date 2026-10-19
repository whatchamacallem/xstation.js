# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The dispatcher: handlers registered by line type and version, the call of
# the one a line names, and the reply and error lines and ids it builds.

import jslb, traceback
from collections.abc import Callable
from i18n import i18n
from typing import Any, TypeAlias

# A handler takes the line and its payload as keywords and returns the reply.
Handler: TypeAlias = Callable[..., jslb.Object | None]

# The registered handlers, by type and version.
_HANDLERS: dict[tuple[str, int], Handler] = {}

# The last id given to each port.
_IDS: dict[str, int] = {}


# Says whether a header uses full names, which spell the type as `type`.
def _header_full(header: jslb.Object) -> bool:
    return "type" in header


# Registers `fn` for one type and version. A second registration raises.
def handler_register(type: str, version: int, fn: Handler) -> None:
    if (type, version) in _HANDLERS:
        raise ValueError(i18n("dispatch.handler_twice", type, version))
    _HANDLERS[(type, version)] = fn


# Calls `fn(line, **payload_of(line))`. Returns the reply with `r`, or None.
def line_dispatch(line: jslb.Object) -> jslb.Object | None:
    header: jslb.Object = line[0]
    name: str = jslb.field_get(header, "type")
    version: int = jslb.field_get(header, "version")
    fn = _HANDLERS.get((name, version))
    if fn is None:
        raise LookupError(i18n("dispatch.handler_unknown", name, version))
    request_id: int | None = jslb.field_get(header, "id")
    reply = fn(line, **jslb.payload_of(line))
    if request_id is None:
        if reply is not None:
            raise ValueError(
                i18n("dispatch.notification_replied", name, version)
            )
        return None
    if reply is None:
        raise ValueError(
            i18n("dispatch.request_unanswered", name, version, request_id)
        )
    key = "reply" if _header_full(reply[0]) else "r"
    reply[0][key] = request_id
    return reply


# Builds a reply to `line` with `r` set and the payload and blobs given.
def reply_make(
    line: jslb.Object, blobs: list[jslb.Object] | None = None, **payload: Any
) -> jslb.Object:
    header = jslb.header_make(
        jslb.field_get(line[0], "type"),
        reply=jslb.field_get(line[0], "id"),
        full=_header_full(line[0]),
    )
    return jslb.line_make(header, [] if blobs is None else blobs, **payload)


# Builds the one `error` line for a raise: `message`, `stack`, `r` when `i`.
def error_make(line: jslb.Object | None, error: BaseException) -> jslb.Object:
    header = jslb.header_make(
        "error",
        reply=None if line is None else jslb.field_get(line[0], "id"),
        full=line is not None and _header_full(line[0]),
    )
    stack = "".join(traceback.format_exception(error)).removesuffix("\n")
    return jslb.line_make(header, [], message=str(error), stack=stack)


# The next `i` for the port, from 1.
def id_next(port: str) -> int:
    _IDS[port] = _IDS.get(port, 0) + 1
    return _IDS[port]
