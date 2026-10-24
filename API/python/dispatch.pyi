# The handlers of the server by line type and version. A handler takes the
# line and its payload as keywords and returns the reply, None for a
# notification, or a `Failure`: a reply the main loop writes before it fails
# with the failure's error, so an answer is never lost to the fault after it.
#
# `error_make` writes a cascade as nested `cause` entries: the exception's
# own `message`, and as `stack` its traceback without its chain, then under
# `cause` its `__cause__`, or else its `__context__` unless
# `__suppress_context__` is set, and so on, the first failure innermost.
# The line takes the name form of the line it answers. With no line to
# answer, `full` picks it: the caller's setting `debug`, or True before the
# settings exist, so that in debug mode every line uses the full names.

from collections.abc import Callable
from typing import Any, NamedTuple, TypeAlias

import jslb

# A reply the main loop writes before it raises `error`.
class Failure(NamedTuple):
    reply: jslb.Object
    error: BaseException

# A handler takes the line and its payload as keywords and returns the reply.
Handler: TypeAlias = Callable[..., jslb.Object | Failure | None]

# Registers `fn` for one type and version. A second registration raises.
def handler_register(type: str, version: int, fn: Handler) -> None: ...

# Calls `fn(line, **payload_of(line))`. Returns the reply with `r`, or None.
def line_dispatch(line: jslb.Object) -> jslb.Object | Failure | None: ...

# Builds a reply to `line` with `r` set and the payload and blobs given.
def reply_make(
    line: jslb.Object, blobs: list[jslb.Object] = ..., **payload: Any
) -> jslb.Object: ...

# Builds the one `error` line for a raise, its cascade under `cause`.
def error_make(
    line: jslb.Object | None, error: BaseException, full: bool
) -> jslb.Object: ...

# The cascade of an exception as the payload `error_make` writes.
def cause_make(error: BaseException) -> dict[str, Any]: ...

# The next `i` for the port, from 102: 101 is the first line's.
def id_next(port: str) -> int: ...
