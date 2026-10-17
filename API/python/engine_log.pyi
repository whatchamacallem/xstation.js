from typing import Any

from jslb import Object

# Handlers of the `log.*` lines on the wire.

# `log.put`: lines from the page, stored in `log` in debug mode; no reply.
def log_put(line: Object, *, lines: list[dict[str, Any]]) -> None: ...

# `log.follow`: from now on every server log line is pushed as
# `log.line`; reply empty.
def log_follow(line: Object) -> Object: ...

# `log.tail`: reply with the last `count` lines.
def log_tail(line: Object, *, count: int) -> Object: ...
