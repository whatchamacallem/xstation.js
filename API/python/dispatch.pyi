from collections.abc import Callable
from typing import Any, TypeAlias

import jslb

# A handler takes the line and its payload as keywords and returns the reply.
Handler: TypeAlias = Callable[..., jslb.Object | None]

# Registers `fn` for one type and version. A second registration raises.
def handler_register(type: str, version: int, fn: Handler) -> None: ...

# Calls `fn(line, **payload_of(line))`. Returns the reply with `r`, or None.
def line_dispatch(line: jslb.Object) -> jslb.Object | None: ...

# Builds a reply to `line` with `r` set and the payload and blobs given.
def reply_make(
    line: jslb.Object, blobs: list[jslb.Object] = ..., **payload: Any
) -> jslb.Object: ...

# Builds the one `error` line for a raise: `message`, `stack`, `r` when `i`.
def error_make(
    line: jslb.Object | None, error: BaseException
) -> jslb.Object: ...

# The next `i` for the port, from 1.
def id_next(port: str) -> int: ...
