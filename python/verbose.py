# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The server's verbose log and the shell's runner. Outside debug mode the log
# is the `_verbose` database in the root that holds every line the moment it
# is logged, with no level, held to `blob_max` bytes by `PRAGMA
# max_page_count` over its `page_size`, so that a line that needs a page past
# it fails with SQLite's `SQLITE_FULL`, raised and never caught. In debug mode
# no role opens it, and a line logged is a note of the console role in the
# audit, as the console's start and end of dash are the only lines a server
# logs there. The shell's runner is the one place the engine starts an
# external program, whose levels are the only verbose levels the server has
# and whose input and output it passes through at every level. It depends on
# no other engine module but the audit, the switches and the strings.

import audit, os, shlex, sqlite3, subprocess, switches, sys, time
from internationalization import i18n

# The file in the root that holds the lines.
_FILE_NAME = "_verbose.sqlite"

# The highest level of the runner, the one that runs the verbose command line.
_LEVEL_MAX = 2

# The thread that a line from the server itself is stored under.
_SERVER_THREAD = "server"

# The thread of the audit's note that a line logged in debug mode becomes.
_CONSOLE_THREAD = "console"

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


# The state of the log, which is empty until the log is opened.
class _LogState:
    # Starts with no file.
    def __init__(self) -> None:
        self.connection: sqlite3.Connection | None = None


# The one log of the process.
_STATE = _LogState()


# Raises unless the runner's level is 0, 1 or 2.
def _level_check(level: int) -> None:
    if not 0 <= level <= _LEVEL_MAX:
        raise ValueError(i18n("verbose.level_invalid", level, _LEVEL_MAX))


# Returns the file, and raises before the log is opened.
def _open_get() -> sqlite3.Connection:
    if _STATE.connection is None:
        raise RuntimeError(i18n("verbose.not_open"))
    return _STATE.connection


# Opens the root's `_verbose.sqlite`, held to `blob_max` bytes.
def log_open(root: str, blob_max: int) -> None:
    if _STATE.connection is not None:
        raise RuntimeError(i18n("verbose.open_twice"))
    connection = sqlite3.connect(os.path.join(root, _FILE_NAME))
    page_size = connection.execute("PRAGMA page_size").fetchone()[0]
    connection.execute(f"PRAGMA max_page_count = {blob_max // page_size}")
    for pragma in _PRAGMAS:
        connection.execute(pragma)
    if connection.execute(_TABLE_FIND).fetchone() is None:
        connection.execute(_LINE_DDL)
    _STATE.connection = connection


# Closes the file and returns the log to its state before it was opened.
def log_close() -> None:
    _open_get().close()
    _STATE.connection = None


# Writes a line to `_verbose`, in debug mode a note of console in the audit.
def log(text: str) -> None:
    at = time.time_ns() // _NANOSECONDS_PER_MILLISECOND
    if switches.debug:
        audit.note_put(_CONSOLE_THREAD, at, text)
        return
    connection = _open_get()
    with connection:
        connection.execute(_LINE_INSERT, (at, _SERVER_THREAD, text))


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
