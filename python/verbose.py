# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The server's verbose log: a ring of the latest lines and the `_verbose`
# database in the root that holds every line the moment it is logged, with no
# level; and the shell's runner, the one place the engine starts an external
# program, whose levels are the only verbose levels the server has and whose
# input and output it passes through at every level. It depends on no other
# engine module but the strings.

import collections, os, shlex, sqlite3, subprocess, sys, time
from i18n import i18n
from typing import NamedTuple

# The file in the root that holds the lines.
_FILE_NAME = "_verbose.sqlite"

# The highest level of the runner, the one that runs the verbose command line.
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
    text   TEXT    NOT NULL
) STRICT;
"""

# The statement that stores one line.
_LINE_INSERT = "INSERT INTO line (at, thread, text) VALUES (?, ?, ?)"

# The statement that reads the newest lines of one thread, newest first.
_TAIL_SELECT = (
    "SELECT at, text FROM line WHERE thread = ? ORDER BY seq DESC LIMIT ?"
)


# One line: milliseconds since the epoch and its text.
class LogLine(NamedTuple):
    at: int
    text: str


# The state of the log, which is empty until the log is opened.
class _LogState:
    # Starts with no ring and no file.
    def __init__(self) -> None:
        self.ring: collections.deque[LogLine] | None = None
        self.connection: sqlite3.Connection | None = None


# The one log of the process.
_STATE = _LogState()


# Raises unless the runner's level is 0, 1 or 2.
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
    connection, _ = _open_get()
    connection.close()
    _STATE.ring = None
    _STATE.connection = None


# Writes one line to `_verbose`, unbuffered, and to the ring of `verbose_ring`.
def log(text: str) -> None:
    connection, ring = _open_get()
    at = time.time_ns() // _NANOSECONDS_PER_MILLISECOND
    line = LogLine(at, text)
    with connection:
        connection.execute(_LINE_INSERT, (line.at, _SERVER_THREAD, line.text))
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
    connection, _ = _open_get()
    with connection:
        connection.executemany(
            _LINE_INSERT, [(line.at, thread, line.text) for line in lines]
        )


# The last `count` lines of the page thread `ui` or `ai`, oldest first.
def tail_get(thread: str, count: int) -> list[LogLine]:
    if thread not in _PAGE_THREADS:
        raise ValueError(i18n("verbose.thread_unknown", thread))
    if count < 0:
        raise ValueError(i18n("verbose.count_invalid", count))
    connection, _ = _open_get()
    rows: list[tuple[int, str]] = connection.execute(
        _TAIL_SELECT, (thread, count)
    ).fetchall()
    return [LogLine(at, text) for at, text in reversed(rows)]


# Runs the program on this process's input and output, after a flush of both.
def _run_through(argv: list[str]) -> int:
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.run(argv).returncode


# Runs the program passed through, its start and its exit logged.
def _run_logged(argv: list[str]) -> int:
    command = shlex.join(argv)
    log(i18n("verbose.exec_run", command))
    code = _run_through(argv)
    log(i18n("verbose.exec_exit", command, code))
    return code


# Runs `argv`, or `argv_verbose` at level 2, the one place a program starts.
def exec(level: int, argv: list[str], argv_verbose: list[str]) -> int:
    _level_check(level)
    if level == 0:
        return _run_through(argv)
    if level == 1:
        return _run_logged(argv)
    return _run_logged(argv_verbose)
