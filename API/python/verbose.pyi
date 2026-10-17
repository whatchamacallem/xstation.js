from collections.abc import Callable
from typing import NamedTuple

# One log line: milliseconds since the epoch, its level, its text.
class LogLine(NamedTuple):
    at: int
    level: int
    text: str

# Sets the level: 0 only what must be said, 1 Markdown formatted progress,
# 2 everything raw. Lines above the level are not written.
def level_set(level: int) -> None: ...

# Writes one line to the log file under the root, unbuffered, and keeps
# it in the ring of the last `log_ring` lines from settings.
def log_write(level: int, text: str) -> None: ...

# The last `count` lines of the ring, oldest first.
def log_tail(count: int) -> list[LogLine]: ...

# Registers a callback for every line written from now on, so a handler
# can push `log.line` to a client that sent `log.follow`.
def log_follow(fn: Callable[[LogLine], None]) -> None: ...
