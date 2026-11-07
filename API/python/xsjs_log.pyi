# `python3 python/xsjs_log.py ROOT [--thread ui|ai|server] [--type TYPE]
# [--grep TEXT] [--follow]`, standard library only, prints the timeline of a
# root: the table `line` of its `_verbose.sqlite`, opened read only, one line
# per entry, `seq at thread text`, in `seq` order, the order the server wrote
# them, each line flushed as it is printed. `at` prints as stored, milliseconds
# since the epoch. A newline in a text, as in a stack, prints as `\n`, so that
# an entry stays one line; the functions keep the text as stored. The root is
# `~/.cache/xsjs/root` for the serve program and `build/test_demo-*/root` for a
# failed demo test, which keeps its root.
#
# An entry passes when it passes every filter given. `thread` takes one
# thread's entries. `grep` takes the texts that hold its text, plain and not a
# pattern. `line_type` takes the entries of one line type, named whole: an
# entry's type is the first `"type"` field of its text, since the header comes
# first in every form a line is noted in, rendered, sized or as its header
# alone, and a text with no such field has no type.
#
# `--follow` prints what the file holds, then keeps reading as the file grows,
# as the wire test reads a TAP file, until SIGINT, which exits 130. A root with
# no `_verbose.sqlite` raises `xsjs_log.file_missing`, with `--follow` too.

from collections.abc import Iterator
from typing import NamedTuple

# One row of the table `line`.
class LogEntry(NamedTuple):
    seq: int
    at: int
    thread: str
    text: str

# The entries that pass the filters, in `seq` order, the demo test's check.
def lines_read(
    root: str,
    *,
    thread: str | None = ...,
    line_type: str | None = ...,
    grep: str | None = ...,
) -> list[LogEntry]: ...

# Yields what `lines_read` returns, then each passing entry as it is written.
def lines_follow(
    root: str,
    *,
    thread: str | None = ...,
    line_type: str | None = ...,
    grep: str | None = ...,
) -> Iterator[LogEntry]: ...

# The printed line of an entry, `seq at thread text`.
def entry_text(entry: LogEntry) -> str: ...

# Prints the timeline by the arguments after the program's name.
def log_run(argv: list[str]) -> int: ...
