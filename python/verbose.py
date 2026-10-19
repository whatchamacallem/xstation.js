# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The server's verbose log: a level, a ring of the latest lines, the `_verbose`
# database in the root that holds every line the moment it is logged, and the
# one place the engine starts an external program. It depends on no other
# engine module but the strings.

import collections, os, shlex, sqlite3, subprocess, time
from i18n import i18n
from typing import IO, NamedTuple, cast

# The file in the root that holds the lines.
_FILE_NAME = "_verbose.sqlite"

# The highest level, the one that says everything.
_LEVEL_MAX = 2

# The thread that a line from the server itself is stored under.
_SERVER_THREAD = "server"

# The threads of the page, whose lines reach the server from the page.
_PAGE_THREADS = ("ui", "ai")

# How many nanoseconds the clock counts in a millisecond.
_NANOSECONDS_PER_MILLISECOND = 1_000_000

# The pragmas that set the journal and the sync mode of the file.
_PRAGMAS = ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=NORMAL")

# The statement that finds the `line` table in a database.
_TABLE_FIND = (
    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'line'"
)

# The DDL of the `line` table, as the SQL file of the API holds it.
_LINE_DDL = """
CREATE TABLE line (
    seq    INTEGER PRIMARY KEY,
    at     INTEGER NOT NULL,
    thread TEXT    NOT NULL,
    level  INTEGER NOT NULL,
    text   TEXT    NOT NULL
) STRICT;
"""

# The statement that stores one line.
_LINE_INSERT = "INSERT INTO line (at, thread, level, text) VALUES (?, ?, ?, ?)"

# The line that opens the Markdown code block of a level 1 call's output.
_FENCE_OPEN = "```text"

# The line that closes the Markdown code block of a level 1 call's output.
_FENCE_CLOSE = "```"


# One line: milliseconds since the epoch, its level, its text.
class LogLine(NamedTuple):
    at: int
    level: int
    text: str


# The state of the log, which is empty until the log is opened.
class _LogState:
    # Starts with no level, no ring and no file.
    def __init__(self) -> None:
        self.level: int | None = None
        self.ring: collections.deque[LogLine] | None = None
        self.connection: sqlite3.Connection | None = None


# The one log of the process.
_STATE = _LogState()


# Raises unless the level is 0, 1 or 2.
def _level_check(level: int) -> None:
    if not 0 <= level <= _LEVEL_MAX:
        raise ValueError(i18n("verbose.level_invalid", level, _LEVEL_MAX))


# Returns the file and the ring, and raises before the log is opened.
def _open_get() -> tuple[sqlite3.Connection, collections.deque[LogLine]]:
    if _STATE.connection is None or _STATE.ring is None:
        raise RuntimeError(i18n("verbose.not_open"))
    return _STATE.connection, _STATE.ring


# Opens `_verbose.sqlite` in the root, with an empty ring of that many lines.
def log_open(root: str, ring: int) -> None:
    if _STATE.connection is not None:
        raise RuntimeError(i18n("verbose.open_twice"))
    lines = collections.deque[LogLine](maxlen=ring)
    connection = sqlite3.connect(os.path.join(root, _FILE_NAME))
    for pragma in _PRAGMAS:
        connection.execute(pragma)
    if connection.execute(_TABLE_FIND).fetchone() is None:
        connection.execute(_LINE_DDL)
    _STATE.ring = lines
    _STATE.connection = connection


# Closes the file and returns the log to its state before it was opened.
def log_close() -> None:
    if _STATE.connection is not None:
        _STATE.connection.close()
    _STATE.level = None
    _STATE.ring = None
    _STATE.connection = None


# Sets the level: 0 only what must be said, 1 Markdown progress, 2 everything.
def level_set(level: int) -> None:
    _level_check(level)
    _STATE.level = level


# Writes one line to `_verbose`, unbuffered, and to the ring of `verbose_ring`.
def log(level: int, text: str) -> None:
    _level_check(level)
    connection, ring = _open_get()
    if _STATE.level is None:
        raise RuntimeError(i18n("verbose.level_unset"))
    if level > _STATE.level:
        return
    at = time.time_ns() // _NANOSECONDS_PER_MILLISECOND
    line = LogLine(at, level, text)
    with connection:
        connection.execute(
            _LINE_INSERT, (line.at, _SERVER_THREAD, line.level, line.text)
        )
    ring.append(line)


# The last `count` lines of the ring, oldest first.
def history_get(count: int) -> list[LogLine]:
    if count < 0:
        raise ValueError(i18n("verbose.count_invalid", count))
    _, ring = _open_get()
    lines = list(ring)
    return lines[max(0, len(lines) - count) :]


# Writes the lines of the page thread `ui` or `ai` to `_verbose` as one batch.
def lines_put(thread: str, lines: list[LogLine]) -> None:
    if thread not in _PAGE_THREADS:
        raise ValueError(i18n("verbose.thread_unknown", thread))
    for line in lines:
        _level_check(line.level)
    connection, _ = _open_get()
    with connection:
        connection.executemany(
            _LINE_INSERT,
            [(line.at, thread, line.level, line.text) for line in lines],
        )


# Runs the program with its output logged, in a block at level 1, raw at 2.
def _call_piped(level: int, argv: list[str]) -> int:
    command = shlex.join(argv)
    log(level, i18n("verbose.call_run", command))
    with subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    ) as process:
        if level == 1:
            log(level, _FENCE_OPEN)
        for output in cast(IO[str], process.stdout):
            log(level, output.rstrip("\n"))
        if level == 1:
            log(level, _FENCE_CLOSE)
    code: int = process.returncode
    log(level, i18n("verbose.call_exit", command, code))
    return code


# Runs an external program, the one place that does. Returns its exit code.
def call(level: int, argv: list[str]) -> int:
    _level_check(level)
    if level == 0:
        return subprocess.run(argv).returncode
    return _call_piped(level, argv)
