from collections.abc import Callable
from typing import Any

from jslb import Object

# A handler takes the line and its payload as keywords, and returns the
# reply's payload and blobs as a line without a header, or None for a
# notification.
Handler = Callable[..., Object | None]

# Registers `fn` for one type and version. A second registration of the
# same pair raises.
def handler_register(type: str, version: int, fn: Handler) -> None: ...

# Looks up the handler by the line's type and version and calls
# `fn(line, **payload_of(line))`. Returns the reply line with `r` set
# when the request had `i`, or None. An unknown type or version raises.
def line_dispatch(line: Object) -> Object | None: ...

# Builds a reply to `line` with `r` set and the payload and blobs given.
def reply_make(line: Object, blobs: list[Object] = ..., **payload: Any) -> Object: ...

# Builds the one `error` line for a raise: `message` and `stack` as text,
# `r` set when the request had `i`.
def error_make(line: Object | None, error: BaseException) -> Object: ...

# The next `i` for the port, from 1.
def id_next(port: str) -> int: ...
