from typing import NamedTuple

# One line: milliseconds since the epoch, its level, its text.
class LogLine(NamedTuple):
    at: int
    level: int
    text: str

# Sets the level: 0 only what must be said, 1 Markdown progress, 2 everything.
def level_set(level: int) -> None: ...

# Writes one line to `_verbose`, unbuffered, and to the ring of `verbose_ring`.
def log(level: int, text: str) -> None: ...

# The last `count` lines of the ring, oldest first.
def history_get(count: int) -> list[LogLine]: ...

# Runs an external program, the one place that does. Returns its exit code.
def call(level: int, argv: list[str]) -> int: ...
