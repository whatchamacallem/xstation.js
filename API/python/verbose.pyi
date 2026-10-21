from typing import NamedTuple

# One line: milliseconds since the epoch and its text.
class LogLine(NamedTuple):
    at: int
    text: str

# Writes one line to `_verbose`, unbuffered, and to the ring of `verbose_ring`.
def log(text: str) -> None: ...

# The last `count` lines of the ring, oldest first.
def history_get(count: int) -> list[LogLine]: ...

# The shell's runner: `argv` at level 0 or 1, `argv_verbose` raw at 2.
def exec(level: int, argv: list[str], argv_verbose: list[str]) -> int: ...
