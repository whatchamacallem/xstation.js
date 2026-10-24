# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The dispatcher: handlers registered by line type and version, the call of
# the one a line names, and the reply and error lines and ids it builds. A
# handler may return a `Failure`, a reply the main loop writes before it
# fails with the failure's error, so an answer is never lost to the fault
# after it. An error line holds the cascade as nested `cause` entries, the
# first failure innermost. A line takes the name form of the line it
# answers; with none, `full`, the caller's setting `debug`, picks it.

import jslb, traceback
from collections.abc import Callable
from internationalization import i18n
from typing import Any, NamedTuple, TypeAlias

# The fixed id of the first line, `tap.start`, below those of `id_next`.
_FIRST_ID = 101


# A reply the main loop writes before it raises `error`.
class Failure(NamedTuple):
    reply: jslb.Object
    error: BaseException


# A handler takes the line and its payload as keywords and returns the reply.
Handler: TypeAlias = Callable[..., jslb.Object | Failure | None]

# The registered handlers, by type and version.
_HANDLERS: dict[tuple[str, int], Handler] = {}

# The last id given to each port.
_IDS: dict[str, int] = {}


# Says whether a header uses full names, which spell the type as `type`.
def _header_full(header: jslb.Object) -> bool:
    return "type" in header


# Returns the version of a line, which must be an integer and not a bool.
def _version_get(header: jslb.Object, name: str) -> int:
    version: object = jslb.field_get(header, "version")
    if type(version) is not int:
        raise ValueError(i18n("dispatch.version_refused", name, repr(version)))
    return version


# Returns the id of a line, None for a notification, else an integer from 1.
def _id_get(header: jslb.Object, name: str) -> int | None:
    request_id: object = jslb.field_get(header, "id")
    if request_id is None:
        return None
    if type(request_id) is not int or request_id < 1:
        raise ValueError(i18n("dispatch.id_refused", name, repr(request_id)))
    return request_id


# Registers `fn` for one type and version. A second registration raises.
def handler_register(type: str, version: int, fn: Handler) -> None:
    if (type, version) in _HANDLERS:
        raise ValueError(i18n("dispatch.handler_twice", type, version))
    _HANDLERS[(type, version)] = fn


# Calls `fn(line, **payload_of(line))`. Returns the reply with `r`, or None.
def line_dispatch(line: jslb.Object) -> jslb.Object | Failure | None:
    header: jslb.Object = line[0]
    name: str = jslb.field_get(header, "type")
    version = _version_get(header, name)
    request_id = _id_get(header, name)
    fn = _HANDLERS.get((name, version))
    if fn is None:
        raise LookupError(i18n("dispatch.handler_unknown", name, version))
    result = fn(line, **jslb.payload_of(line))
    if request_id is None:
        if result is not None:
            first = result.error if isinstance(result, Failure) else None
            raise ValueError(
                i18n("dispatch.notification_replied", name, version)
            ) from first
        return None
    if result is None:
        raise ValueError(
            i18n("dispatch.request_unanswered", name, version, request_id)
        )
    reply = result.reply if isinstance(result, Failure) else result
    key = "reply" if _header_full(reply[0]) else "r"
    reply[0][key] = request_id
    return result


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


# Builds the one `error` line for a raise, its cascade under `cause`.
def error_make(
    line: jslb.Object | None, error: BaseException, full: bool
) -> jslb.Object:
    header = jslb.header_make(
        "error",
        reply=None if line is None else jslb.field_get(line[0], "id"),
        full=full if line is None else _header_full(line[0]),
    )
    return jslb.line_make(header, [], **cause_make(error))


# The cascade of an exception as the payload `error_make` writes.
def cause_make(error: BaseException) -> dict[str, Any]:
    lines = traceback.format_exception(error, chain=False)
    cascade: dict[str, Any] = {
        "message": str(error),
        "stack": "".join(lines).removesuffix("\n"),
    }
    inner = error.__cause__
    if inner is None and not error.__suppress_context__:
        inner = error.__context__
    if inner is not None:
        cascade["cause"] = cause_make(inner)
    return cascade


# The next `i` for the port, from 102: 101 is the first line's.
def id_next(port: str) -> int:
    _IDS[port] = _IDS.get(port, _FIRST_ID) + 1
    return _IDS[port]
