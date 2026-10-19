# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the level filter, the ring, the database that holds each line the
# moment it is logged, the lines of the page threads and the three levels of
# the external call. The only program a test starts is the interpreter that
# runs it. The scratch directories go under `build/`.

import contextlib, os, sqlite3, sys, tempfile, time, unittest, verbose
from typing import Any, cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# Where the bytecode of a started program that imports the module goes.
_PYCACHE_PATH = os.path.join(_BUILD_PATH, "pycache")

# The directory that holds the module, which a started program imports from.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The file in the root that holds the lines.
_FILE_NAME = "_verbose.sqlite"

# A count of lines greater than any ring a test makes.
_HISTORY_ALL = 100

# Reads every row of the table, in the order they were written.
_SELECT_ROWS = "SELECT seq, at, thread, level, text FROM line ORDER BY seq"

# The columns the table has: id, name, type, not null, default and key.
_COLUMNS = [
    (0, "seq", "INTEGER", 0, None, 1),
    (1, "at", "INTEGER", 1, None, 0),
    (2, "thread", "TEXT", 1, None, 0),
    (3, "level", "INTEGER", 1, None, 0),
    (4, "text", "TEXT", 1, None, 0),
]

# A program that writes a line to each stream in turn and exits with code 3.
_OUTPUT_PROGRAM = (
    "import sys\n"
    "print('alpha', flush=True)\n"
    "print('beta', file=sys.stderr, flush=True)\n"
    "sys.exit(3)\n"
)

# A program that exits with the code in its first argument.
_EXIT_PROGRAM = "import sys; sys.exit(int(sys.argv[1]))"

# A program that writes its arguments as a list.
_ARGS_PROGRAM = "import sys; print(sys.argv[1:], flush=True)"

# A program that makes the file that its first argument names.
_MARKER_PROGRAM = "import sys; open(sys.argv[1], 'w').close()"

# A program that logs two lines and ends at once, without cleaning up.
_HARD_PROGRAM = (
    "import os, sys\n"
    "sys.pycache_prefix = sys.argv[3]\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import verbose\n"
    "verbose.log_open(sys.argv[2], 5)\n"
    "verbose.level_set(2)\n"
    "verbose.log(1, 'first')\n"
    "verbose.log(2, 'second')\n"
    "os._exit(7)\n"
)


# Makes a scratch directory in `build/` that goes after the log is closed.
def _scratch_make(case: unittest.TestCase) -> str:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
    case.addCleanup(scratch.cleanup)
    case.addCleanup(verbose.log_close)
    return scratch.name


# Opens the log in a scratch directory at a level, and returns the directory.
def _log_ready(case: unittest.TestCase, ring: int, level: int) -> str:
    path = _scratch_make(case)
    verbose.log_open(path, ring)
    verbose.level_set(level)
    return path


# Runs a query on the database in the directory with a connection of its own.
def _query_read(path: str, sql: str) -> list[Any]:
    database = os.path.join(path, _FILE_NAME)
    with contextlib.closing(sqlite3.connect(database)) as connection:
        return connection.execute(sql).fetchall()


# Reads every row of the table with a connection of its own.
def _rows_read(path: str) -> list[Any]:
    return _query_read(path, _SELECT_ROWS)


# Returns the texts of the lines.
def _texts_get(lines: list[verbose.LogLine]) -> list[str]:
    return [line.text for line in lines]


# Returns the texts of the whole ring, oldest first.
def _ring_texts() -> list[str]:
    return _texts_get(verbose.history_get(_HISTORY_ALL))


# Runs a call with the output descriptors of this process set to files.
def _call_captured(
    level: int, argv: list[str], path: str
) -> tuple[int, str, str]:
    out_path = os.path.join(path, "out.txt")
    err_path = os.path.join(path, "err.txt")
    sys.stdout.flush()
    sys.stderr.flush()
    saved_out = os.dup(1)
    saved_err = os.dup(2)
    try:
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            os.dup2(out.fileno(), 1)
            os.dup2(err.fileno(), 2)
            try:
                code = verbose.call(level, argv)
            finally:
                os.dup2(saved_out, 1)
                os.dup2(saved_err, 2)
    finally:
        os.close(saved_out)
        os.close(saved_err)
    with open(out_path, encoding="utf-8") as file:
        out_text = file.read()
    with open(err_path, encoding="utf-8") as file:
        err_text = file.read()
    return code, out_text, err_text


# Tests which lines the level lets through and what the log refuses.
class TestLevel(unittest.TestCase):
    # A line above the level is dropped from the ring and the database.
    def test_level_filter(self) -> None:
        path = _log_ready(self, 10, 1)
        verbose.log(0, "zero")
        verbose.log(1, "one")
        verbose.log(2, "two")
        self.assertEqual(_ring_texts(), ["zero", "one"])
        verbose.level_set(2)
        verbose.log(2, "three")
        verbose.level_set(0)
        verbose.log(0, "four")
        verbose.log(1, "five")
        self.assertEqual(_ring_texts(), ["zero", "one", "three", "four"])
        rows = _rows_read(path)
        self.assertEqual(
            [row[4] for row in rows], ["zero", "one", "three", "four"]
        )
        self.assertEqual([row[3] for row in rows], [0, 1, 2, 0])

    # A level outside 0 to 2 raises and changes nothing.
    def test_level_unknown(self) -> None:
        path = _log_ready(self, 10, 1)
        with self.assertRaises(ValueError):
            verbose.level_set(3)
        with self.assertRaises(ValueError):
            verbose.level_set(-1)
        with self.assertRaises(ValueError):
            verbose.log(3, "high")
        with self.assertRaises(ValueError):
            verbose.log(-1, "low")
        with self.assertRaises(ValueError):
            verbose.call(3, [sys.executable, "-c", ""])
        verbose.log(1, "still one")
        self.assertEqual(_ring_texts(), ["still one"])
        self.assertEqual(len(_rows_read(path)), 1)

    # A line logged before the level is set raises and is not written.
    def test_level_unset(self) -> None:
        path = _scratch_make(self)
        verbose.log_open(path, 10)
        with self.assertRaises(RuntimeError):
            verbose.log(0, "early")
        self.assertEqual(_ring_texts(), [])
        self.assertEqual(_rows_read(path), [])

    # Every use of the log before it is opened raises.
    def test_log_unopened(self) -> None:
        _scratch_make(self)
        verbose.level_set(2)
        with self.assertRaises(RuntimeError):
            verbose.log(0, "early")
        with self.assertRaises(RuntimeError):
            verbose.history_get(1)
        with self.assertRaises(RuntimeError):
            verbose.lines_put("ui", [])

    # Closing the log forgets the file, the ring and the level.
    def test_close_resets(self) -> None:
        path = _log_ready(self, 10, 2)
        verbose.log(2, "before")
        verbose.log_close()
        verbose.log_close()
        with self.assertRaises(RuntimeError):
            verbose.log(0, "closed")
        with self.assertRaises(RuntimeError):
            verbose.history_get(1)
        verbose.log_open(path, 10)
        with self.assertRaises(RuntimeError):
            verbose.log(0, "unset")


# Tests the ring and the history it gives back.
class TestRing(unittest.TestCase):
    # The ring keeps the newest lines that fit, oldest first.
    def test_ring_order(self) -> None:
        path = _log_ready(self, 3, 2)
        for number in range(5):
            verbose.log(number % 3, f"line {number}")
        self.assertEqual(_ring_texts(), ["line 2", "line 3", "line 4"])
        self.assertEqual(len(_rows_read(path)), 5)

    # A ring of no lines keeps nothing and the database still has the line.
    def test_ring_empty(self) -> None:
        path = _log_ready(self, 0, 1)
        verbose.log(1, "kept")
        self.assertEqual(_ring_texts(), [])
        self.assertEqual(len(_rows_read(path)), 1)

    # The history is the last count lines, oldest first, or all if fewer.
    def test_history_counts(self) -> None:
        _log_ready(self, 10, 1)
        self.assertEqual(verbose.history_get(5), [])
        for text in ["a", "b", "c"]:
            verbose.log(1, text)
        expected: dict[int, list[str]] = {
            0: [],
            1: ["c"],
            2: ["b", "c"],
            3: ["a", "b", "c"],
            4: ["a", "b", "c"],
        }
        for count, texts in expected.items():
            self.assertEqual(_texts_get(verbose.history_get(count)), texts)

    # A negative count raises.
    def test_history_negative(self) -> None:
        _log_ready(self, 10, 1)
        with self.assertRaises(ValueError):
            verbose.history_get(-1)

    # A line holds the time in milliseconds, its level and its text.
    def test_line_fields(self) -> None:
        _log_ready(self, 10, 1)
        before = time.time_ns() // 1_000_000
        verbose.log(1, "text")
        after = time.time_ns() // 1_000_000
        (line,) = verbose.history_get(1)
        self.assertTrue(before <= line.at <= after)
        self.assertEqual(line, verbose.LogLine(line.at, 1, "text"))


# Tests the database the log writes.
class TestDatabase(unittest.TestCase):
    # A second connection sees each line as soon as it is logged.
    def test_row_stored(self) -> None:
        path = _log_ready(self, 10, 1)
        for number, text in enumerate(["a", "b", "c"], 1):
            verbose.log(1, text)
            rows = _rows_read(path)
            self.assertEqual(len(rows), number)
            seq, at, thread, level, row_text = rows[-1]
            self.assertEqual(
                (seq, thread, level, row_text), (number, "server", 1, text)
            )
            self.assertEqual(at, verbose.history_get(1)[0].at)

    # A line above the level is not in the database.
    def test_row_dropped(self) -> None:
        path = _log_ready(self, 10, 1)
        verbose.log(2, "dropped")
        self.assertEqual(_rows_read(path), [])

    # The table has the columns of the DDL and is strict.
    def test_table_schema(self) -> None:
        path = _log_ready(self, 10, 1)
        self.assertEqual(
            _query_read(path, "PRAGMA table_info(line)"), _COLUMNS
        )
        strict = _query_read(
            path, "SELECT strict FROM pragma_table_list WHERE name = 'line'"
        )
        self.assertEqual(strict, [(1,)])

    # The file is in the write ahead log mode.
    def test_journal_mode(self) -> None:
        path = _log_ready(self, 10, 1)
        self.assertEqual(_query_read(path, "PRAGMA journal_mode"), [("wal",)])

    # A second open of the log raises and the first stays in use.
    def test_open_twice(self) -> None:
        path = _log_ready(self, 10, 1)
        with self.assertRaises(RuntimeError):
            verbose.log_open(path, 10)
        verbose.log(1, "still open")
        self.assertEqual(_ring_texts(), ["still open"])

    # A reopened file keeps its rows, adds to them and starts an empty ring.
    def test_log_reopen(self) -> None:
        path = _log_ready(self, 10, 1)
        verbose.log(1, "first")
        verbose.log_close()
        verbose.log_open(path, 10)
        verbose.level_set(1)
        self.assertEqual(_ring_texts(), [])
        verbose.log(1, "second")
        rows = _rows_read(path)
        self.assertEqual(
            [(row[0], row[4]) for row in rows], [(1, "first"), (2, "second")]
        )

    # The lines of a program that ends at once are in the database.
    def test_hard_exit(self) -> None:
        path = _scratch_make(self)
        argv = [
            sys.executable,
            "-c",
            _HARD_PROGRAM,
            _PYTHON_PATH,
            path,
            _PYCACHE_PATH,
        ]
        self.assertEqual(verbose.call(0, argv), 7)
        rows = _rows_read(path)
        self.assertEqual(
            [(row[2], row[3], row[4]) for row in rows],
            [("server", 1, "first"), ("server", 2, "second")],
        )


# Tests the lines of the page threads that are written to the database.
class TestPage(unittest.TestCase):
    # Page lines are stored under their thread, whatever the level.
    def test_page_lines(self) -> None:
        path = _log_ready(self, 10, 0)
        verbose.lines_put(
            "ui", [verbose.LogLine(10, 1, "a"), verbose.LogLine(20, 2, "b")]
        )
        verbose.lines_put("ai", [verbose.LogLine(30, 0, "c")])
        verbose.log(0, "d")
        rows = _rows_read(path)
        self.assertEqual(
            rows[:3],
            [
                (1, 10, "ui", 1, "a"),
                (2, 20, "ui", 2, "b"),
                (3, 30, "ai", 0, "c"),
            ],
        )
        self.assertEqual((rows[3][0], rows[3][2:]), (4, ("server", 0, "d")))

    # Page lines are not in the ring.
    def test_page_ring(self) -> None:
        _log_ready(self, 10, 2)
        verbose.lines_put("ui", [verbose.LogLine(10, 1, "a")])
        self.assertEqual(_ring_texts(), [])

    # A thread other than ui or ai raises and nothing is written.
    def test_page_thread(self) -> None:
        path = _log_ready(self, 10, 2)
        for thread in ["server", "console", ""]:
            with self.assertRaises(ValueError):
                verbose.lines_put(thread, [verbose.LogLine(1, 1, "x")])
        self.assertEqual(_rows_read(path), [])

    # A level outside 0 to 2 raises and nothing of the batch is written.
    def test_page_level(self) -> None:
        path = _log_ready(self, 10, 2)
        with self.assertRaises(ValueError):
            verbose.lines_put(
                "ui",
                [verbose.LogLine(1, 1, "ok"), verbose.LogLine(2, 3, "bad")],
            )
        self.assertEqual(_rows_read(path), [])

    # A batch with a row the table refuses writes none of its rows.
    def test_page_batch(self) -> None:
        path = _log_ready(self, 10, 2)
        with self.assertRaises(sqlite3.Error):
            verbose.lines_put(
                "ui",
                [
                    verbose.LogLine(1, 1, "ok"),
                    verbose.LogLine(cast(Any, "bad"), 1, "x"),
                ],
            )
        self.assertEqual(_rows_read(path), [])


# Tests the external call at its three levels.
class TestCall(unittest.TestCase):
    # Level 0 returns the exit code of the program.
    def test_call_code(self) -> None:
        argv = [sys.executable, "-c", _EXIT_PROGRAM]
        self.assertEqual(verbose.call(0, argv + ["0"]), 0)
        self.assertEqual(verbose.call(0, argv + ["5"]), 5)

    # Level 0 passes the output through and logs nothing.
    def test_call_pass(self) -> None:
        path = _log_ready(self, 10, 2)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        code, out, err = _call_captured(0, argv, path)
        self.assertEqual((code, out, err), (3, "alpha\n", "beta\n"))
        self.assertEqual(_ring_texts(), [])
        self.assertEqual(_rows_read(path), [])

    # Level 1 logs Markdown progress with the output in a text block.
    def test_call_markdown(self) -> None:
        path = _log_ready(self, 10, 1)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        self.assertEqual(verbose.call(1, argv), 3)
        lines = verbose.history_get(_HISTORY_ALL)
        self.assertEqual([line.level for line in lines], [1] * 6)
        texts = _texts_get(lines)
        self.assertIn(sys.executable, texts[0])
        self.assertEqual(texts[1:5], ["```text", "alpha", "beta", "```"])
        self.assertIn(sys.executable, texts[5])
        self.assertTrue(texts[5].endswith(" 3."))
        self.assertEqual([row[4] for row in _rows_read(path)], texts)

    # Level 2 logs the output raw, with no block around it.
    def test_call_raw(self) -> None:
        path = _log_ready(self, 10, 2)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        self.assertEqual(verbose.call(2, argv), 3)
        lines = verbose.history_get(_HISTORY_ALL)
        self.assertEqual([line.level for line in lines], [2] * 4)
        texts = _texts_get(lines)
        self.assertIn(sys.executable, texts[0])
        self.assertEqual(texts[1:3], ["alpha", "beta"])
        self.assertTrue(texts[3].endswith(" 3."))
        self.assertEqual([row[4] for row in _rows_read(path)], texts)

    # A call above the level of the log writes nothing and still runs.
    def test_call_gated(self) -> None:
        path = _log_ready(self, 10, 1)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        self.assertEqual(verbose.call(2, argv), 3)
        verbose.level_set(0)
        self.assertEqual(verbose.call(1, argv), 3)
        self.assertEqual(_ring_texts(), [])
        self.assertEqual(_rows_read(path), [])

    # The arguments reach the program unchanged at every level.
    def test_call_flags(self) -> None:
        path = _log_ready(self, 10, 2)
        argv = [sys.executable, "-c", _ARGS_PROGRAM, "--verbose", "x y"]
        listed = str(["--verbose", "x y"])
        self.assertEqual(verbose.call(2, argv), 0)
        self.assertEqual(verbose.call(1, argv), 0)
        self.assertEqual(_ring_texts().count(listed), 2)
        code, out, _ = _call_captured(0, argv, path)
        self.assertEqual((code, out), (0, listed + "\n"))

    # A program that cannot start raises at every level.
    def test_call_start(self) -> None:
        path = _log_ready(self, 10, 2)
        absent = os.path.join(path, "absent")
        for level in range(3):
            with self.assertRaises(OSError):
                verbose.call(level, [absent])
        self.assertEqual(len(verbose.history_get(_HISTORY_ALL)), 2)

    # Level 0 needs no log and levels 1 and 2 refuse before they run.
    def test_call_unopened(self) -> None:
        path = _scratch_make(self)
        first = os.path.join(path, "first")
        second = os.path.join(path, "second")
        argv = [sys.executable, "-c", _MARKER_PROGRAM]
        self.assertEqual(verbose.call(0, argv + [first]), 0)
        self.assertTrue(os.path.exists(first))
        with self.assertRaises(RuntimeError):
            verbose.call(1, argv + [second])
        self.assertFalse(os.path.exists(second))
