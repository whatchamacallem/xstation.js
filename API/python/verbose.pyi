from typing import NamedTuple

# One line: milliseconds since the epoch and its text.
class LogLine(NamedTuple):
    at: int
    text: str

# Opens the root's `_verbose.sqlite`, held to `blob_max` bytes, an empty ring.
def log_open(root: str, ring: int, blob_max: int) -> None: ...

# Closes the file and returns the log to its state before it was opened.
def log_close() -> None: ...

# Writes a line to `_verbose` and the ring, `SQLITE_FULL` past `blob_max`.
def log(text: str) -> None: ...

# The last `count` lines of the ring, oldest first.
def history_get(count: int) -> list[LogLine]: ...

# Writes the lines of the page thread `ui` or `ai` to `_verbose` as one batch.
def lines_put(thread: str, lines: list[LogLine]) -> None: ...

# The last `count` lines of the page thread `ui` or `ai`, oldest first.
def tail_get(thread: str, count: int) -> list[LogLine]: ...

# The shell's runner: `argv` at level 0 or 1, `argv_verbose` raw at 2.
def exec(level: int, argv: list[str], argv_verbose: list[str]) -> int: ...
