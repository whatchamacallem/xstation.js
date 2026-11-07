#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The log program: python3 python/xsjs_log.py ROOT [--thread ui|ai|server]
# [--type TYPE] [--grep TEXT] [--follow] prints the timeline of a root, the
# table `line` of its `_verbose.sqlite`, opened read only, one line per entry,
# `seq at thread text`, in `seq` order, the order the server wrote them. A
# newline in a text prints as `\n`, so that an entry stays one line. An
# entry's type is the first `"type"` field of its text, since a line's header
# comes first in every form it is noted in. `--follow` keeps reading as the
# file grows, until SIGINT, which exits 130. The modules beside this file are
# imported inside the functions that use them, after their bytecode has been
# sent to build/.

import argparse, contextlib, os, pathlib, re, signal, sqlite3, sys, time, types
from collections.abc import Iterator
from typing import NamedTuple

# The directory that holds this file and the modules it imports.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The file in the root that holds the lines.
_FILE_NAME = "_verbose.sqlite"

# The threads a line is stored under.
_THREADS = ("ui", "ai", "server")

# The statement that reads the rows past a `seq`, in `seq` order.
_ROWS_SELECT = (
    "SELECT seq, at, thread, text FROM line WHERE seq > ? ORDER BY seq"
)

# The `seq` before the first row.
_SEQ_START = 0

# The field that names a line's type, in the compact JSON of every form.
_TYPE_FIELD = re.compile(r'"type":"([^"]*)"')

# What a newline of a text prints as.
_NEWLINE_PRINTED = "\\n"

# The wait between two reads of a followed file.
_POLL_SECONDS = 0.05

# What a signal's number is added to for the exit code, as a shell does.
_SIGNAL_BASE = 128

# Bytecode of the modules the functions below import goes in `build/pycache`.
sys.pycache_prefix = os.path.join(
    os.path.dirname(_PYTHON_PATH), "build", "pycache"
)


# One row of the table `line`.
class LogEntry(NamedTuple):
    seq: int
    at: int
    thread: str
    text: str


# Opens the root's log read only, raising when the root has none.
def _file_open(root: str) -> sqlite3.Connection:
    from internationalization import i18n

    path = os.path.abspath(os.path.join(root, _FILE_NAME))
    if not os.path.exists(path):
        raise FileNotFoundError(i18n("xsjs_log.file_missing", path))
    uri = pathlib.Path(path).as_uri()
    return sqlite3.connect(f"{uri}?mode=ro", uri=True)


# The entries past the `seq`, in `seq` order.
def _entries_after(connection: sqlite3.Connection, seq: int) -> list[LogEntry]:
    rows: list[tuple[int, int, str, str]] = connection.execute(
        _ROWS_SELECT, (seq,)
    ).fetchall()
    return [LogEntry(*row) for row in rows]


# The type of a text, none when it holds no `"type"` field.
def _type_find(text: str) -> str | None:
    found = _TYPE_FIELD.search(text)
    return None if found is None else found[1]


# Whether the entry passes every filter given.
def _entry_passes(
    entry: LogEntry,
    thread: str | None,
    line_type: str | None,
    grep: str | None,
) -> bool:
    return (
        (thread is None or entry.thread == thread)
        and (line_type is None or _type_find(entry.text) == line_type)
        and (grep is None or grep in entry.text)
    )


# The entries that pass the filters, in `seq` order, the demo test's check.
def lines_read(
    root: str,
    *,
    thread: str | None = None,
    line_type: str | None = None,
    grep: str | None = None,
) -> list[LogEntry]:
    with contextlib.closing(_file_open(root)) as connection:
        entries = _entries_after(connection, _SEQ_START)
    return [
        entry
        for entry in entries
        if _entry_passes(entry, thread, line_type, grep)
    ]


# Yields what `lines_read` returns, then each passing entry as it is written.
def lines_follow(
    root: str,
    *,
    thread: str | None = None,
    line_type: str | None = None,
    grep: str | None = None,
) -> Iterator[LogEntry]:
    seq = _SEQ_START
    with contextlib.closing(_file_open(root)) as connection:
        while True:
            for entry in _entries_after(connection, seq):
                seq = entry.seq
                if _entry_passes(entry, thread, line_type, grep):
                    yield entry
            time.sleep(_POLL_SECONDS)


# The printed line of an entry, `seq at thread text`.
def entry_text(entry: LogEntry) -> str:
    text = entry.text.replace("\n", _NEWLINE_PRINTED)
    return f"{entry.seq} {entry.at} {entry.thread} {text}"


# Exits with 128 plus the signal's number, as a shell reports it.
def _signal_exit(number: int, frame: types.FrameType | None) -> None:
    sys.exit(_SIGNAL_BASE + number)


# The parser of the program's arguments.
def _parser_make() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print the timeline of a root's _verbose.sqlite, one line"
        " per entry: seq, time, thread and text.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "root", metavar="ROOT", help="the root that holds the log"
    )
    parser.add_argument(
        "--thread", choices=_THREADS, help="print this thread's entries"
    )
    parser.add_argument(
        "--type",
        dest="line_type",
        metavar="TYPE",
        help="print the entries of this line type, named whole",
    )
    parser.add_argument(
        "--grep",
        metavar="TEXT",
        help="print the entries whose text holds this text, plain and not a"
        " pattern",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="keep reading as the file grows, until SIGINT",
    )
    return parser


# Prints the timeline by the arguments after the program's name.
def log_run(argv: list[str]) -> int:
    parsed = _parser_make().parse_args(argv)
    # A program started in the background inherits SIGINT ignored.
    if parsed.follow:
        signal.signal(signal.SIGINT, _signal_exit)
    read = lines_follow if parsed.follow else lines_read
    for entry in read(
        parsed.root,
        thread=parsed.thread,
        line_type=parsed.line_type,
        grep=parsed.grep,
    ):
        print(entry_text(entry), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(log_run(sys.argv[1:]))
