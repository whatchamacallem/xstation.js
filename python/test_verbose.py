# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the log, which writes every line it is given, the ring, the database
# that holds each line the moment it is logged, the lines of the page threads
# written and read back, and the three levels of the shell's runner. The only
# program a test starts is the interpreter that runs it. The scratch
# directories go under `build/`.

import contextlib, os, shlex, sqlite3, sys, tempfile, time, unittest
import unittest.mock, verbose
from collections.abc import Callable
from i18n import i18n
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

# The highest level of the runner, which the message of a level refused names.
_LEVEL_HIGHEST = 2

# A count of lines greater than any ring a test makes.
_HISTORY_ALL = 100

# Reads every row of the table, in the order they were written.
_SELECT_ROWS = "SELECT seq, at, thread, text FROM line ORDER BY seq"

# The columns the table has: id, name, type, not null, default and key.
_COLUMNS = [
    (0, "seq", "INTEGER", 0, None, 1),
    (1, "at", "INTEGER", 1, None, 0),
    (2, "thread", "TEXT", 1, None, 0),
    (3, "text", "TEXT", 1, None, 0),
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

# A program that writes what it reads from its input, quoted.
_INPUT_PROGRAM = "import sys; print(repr(sys.stdin.read()), flush=True)"

# A program that makes the file that its first argument names.
_MARKER_PROGRAM = "import sys; open(sys.argv[1], 'w').close()"

# A program that logs two lines and ends at once, without cleaning up.
_HARD_PROGRAM = (
    "import os, sys\n"
    "sys.pycache_prefix = sys.argv[3]\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import verbose\n"
    "verbose.log_open(sys.argv[2], 5)\n"
    "verbose.log('first')\n"
    "verbose.log('second')\n"
    "os._exit(7)\n"
)


# Makes a scratch directory in `build/` that goes when the test ends.
def _scratch_make(case: unittest.TestCase) -> str:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
    case.addCleanup(scratch.cleanup)
    return scratch.name


# Opens the log in a directory, then has it closed when the test ends.
def _log_open(case: unittest.TestCase, path: str, ring: int) -> None:
    verbose.log_open(path, ring)
    case.addCleanup(verbose.log_close)


# Opens the log in a scratch directory and returns the directory.
def _log_ready(case: unittest.TestCase, ring: int) -> str:
    path = _scratch_make(case)
    _log_open(case, path, ring)
    return path


# Calls `fn` and checks the type and the text of what it raises.
def _raise_check(
    case: unittest.TestCase,
    kind: type[Exception],
    message: str,
    fn: Callable[[], object],
) -> None:
    with case.assertRaises(kind) as caught:
        fn()
    case.assertEqual(str(caught.exception), message)


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


# Returns the progress lines of a run: its start, then its end with the code.
def _progress_texts(argv: list[str], code: int) -> tuple[str, str]:
    command = shlex.join(argv)
    return (
        i18n("verbose.exec_run", command),
        i18n("verbose.exec_exit", command, code),
    )


# Runs `fn` with the output descriptors of this process set to files.
def _output_captured(path: str, fn: Callable[[], int]) -> tuple[int, str, str]:
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
                code = fn()
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


# Runs `fn` with descriptor 0 of this process reading the bytes from a pipe.
def _input_given(data: bytes, fn: Callable[[], int]) -> int:
    read_fd, write_fd = os.pipe()
    os.write(write_fd, data)
    os.close(write_fd)
    saved = os.dup(0)
    try:
        os.dup2(read_fd, 0)
        return fn()
    finally:
        os.dup2(saved, 0)
        os.close(saved)
        os.close(read_fd)


# Runs at the level with text held in the buffers of both Python streams.
def _buffered_run(level: int, argv: list[str]) -> int:
    with (
        open(1, "w", encoding="utf-8", closefd=False) as out,
        open(2, "w", encoding="utf-8", closefd=False) as err,
        unittest.mock.patch("sys.stdout", out),
        unittest.mock.patch("sys.stderr", err),
    ):
        out.write("before ")
        err.write("before ")
        return verbose.exec(level, argv, argv)


# Tests that the log writes every line and what it refuses.
class TestLogAll(unittest.TestCase):
    # Every line given is in the ring and the database, with no level.
    def test_every_line(self) -> None:
        path = _log_ready(self, 10)
        for text in ["zero", "one", "two"]:
            verbose.log(text)
        self.assertEqual(_ring_texts(), ["zero", "one", "two"])
        rows = _rows_read(path)
        self.assertEqual([row[3] for row in rows], ["zero", "one", "two"])

    # A runner level outside 0 to 2 raises, runs nothing and logs nothing.
    def test_level_unknown(self) -> None:
        path = _log_ready(self, 10)
        program = [sys.executable, "-c", _MARKER_PROGRAM]
        argv = [*program, os.path.join(path, "ran")]
        for level in (3, -1):
            _raise_check(
                self,
                ValueError,
                i18n("verbose.level_invalid", level, _LEVEL_HIGHEST),
                lambda: verbose.exec(level, argv, argv),
            )
        self.assertFalse(os.path.exists(argv[-1]))
        self.assertEqual(_ring_texts(), [])
        self.assertEqual(_rows_read(path), [])

    # Every use of the log before it is opened raises, a close too.
    def test_log_unopened(self) -> None:
        message = i18n("verbose.not_open")
        uses: list[Callable[[], object]] = [
            lambda: verbose.log("early"),
            lambda: verbose.history_get(1),
            lambda: verbose.lines_put("ui", []),
            lambda: verbose.tail_get("ui", 1),
            verbose.log_close,
        ]
        for use in uses:
            _raise_check(self, RuntimeError, message, use)

    # A closed log refuses every use, a second close too, until it reopens.
    def test_log_closed(self) -> None:
        path = _log_ready(self, 10)
        verbose.log_close()
        self.addCleanup(verbose.log_open, path, 10)
        message = i18n("verbose.not_open")
        uses: list[Callable[[], object]] = [
            lambda: verbose.log("closed"),
            lambda: verbose.history_get(1),
            verbose.log_close,
        ]
        for use in uses:
            _raise_check(self, RuntimeError, message, use)

    # Closing the log forgets the ring, and the reopened log writes at once.
    def test_close_resets(self) -> None:
        path = _log_ready(self, 10)
        verbose.log("before")
        verbose.log_close()
        verbose.log_open(path, 10)
        self.assertEqual(_ring_texts(), [])
        verbose.log("after")
        self.assertEqual(_ring_texts(), ["after"])


# Tests the ring and the history it gives back.
class TestRing(unittest.TestCase):
    # The ring keeps the newest lines that fit, oldest first.
    def test_ring_order(self) -> None:
        path = _log_ready(self, 3)
        for number in range(5):
            verbose.log(f"line {number}")
        self.assertEqual(_ring_texts(), ["line 2", "line 3", "line 4"])
        self.assertEqual(len(_rows_read(path)), 5)

    # A ring of no lines keeps nothing and the database still has the line.
    def test_ring_empty(self) -> None:
        path = _log_ready(self, 0)
        verbose.log("kept")
        self.assertEqual(_ring_texts(), [])
        self.assertEqual(len(_rows_read(path)), 1)

    # The history is the last count lines, oldest first, or all if fewer.
    def test_history_counts(self) -> None:
        _log_ready(self, 10)
        self.assertEqual(verbose.history_get(5), [])
        for text in ["a", "b", "c"]:
            verbose.log(text)
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
        _log_ready(self, 10)
        _raise_check(
            self,
            ValueError,
            i18n("verbose.count_invalid", -1),
            lambda: verbose.history_get(-1),
        )

    # A line holds the time in milliseconds and its text, nothing else.
    def test_line_fields(self) -> None:
        _log_ready(self, 10)
        before = time.time_ns() // 1_000_000
        verbose.log("text")
        after = time.time_ns() // 1_000_000
        (line,) = verbose.history_get(1)
        self.assertTrue(before <= line.at <= after)
        self.assertEqual(line, verbose.LogLine(line.at, "text"))
        self.assertEqual(len(line), 2)


# Tests the database the log writes.
class TestDatabase(unittest.TestCase):
    # A second connection sees each line as soon as it is logged.
    def test_row_stored(self) -> None:
        path = _log_ready(self, 10)
        for number, text in enumerate(["a", "b", "c"], 1):
            verbose.log(text)
            rows = _rows_read(path)
            self.assertEqual(len(rows), number)
            seq, at, thread, row_text = rows[-1]
            self.assertEqual((seq, thread, row_text), (number, "server", text))
            self.assertEqual(at, verbose.history_get(1)[0].at)

    # The table has the columns of the DDL and is strict.
    def test_table_schema(self) -> None:
        path = _log_ready(self, 10)
        self.assertEqual(
            _query_read(path, "PRAGMA table_info(line)"), _COLUMNS
        )
        strict = _query_read(
            path, "SELECT strict FROM pragma_table_list WHERE name = 'line'"
        )
        self.assertEqual(strict, [(1,)])

    # The file is in the write ahead log mode.
    def test_journal_mode(self) -> None:
        path = _log_ready(self, 10)
        self.assertEqual(_query_read(path, "PRAGMA journal_mode"), [("wal",)])

    # A second open of the log raises and the first stays in use.
    def test_open_twice(self) -> None:
        path = _log_ready(self, 10)
        _raise_check(
            self,
            RuntimeError,
            i18n("verbose.open_twice"),
            lambda: verbose.log_open(path, 10),
        )
        verbose.log("still open")
        self.assertEqual(_ring_texts(), ["still open"])

    # A reopened file keeps its rows, adds to them and starts an empty ring.
    def test_log_reopen(self) -> None:
        path = _log_ready(self, 10)
        verbose.log("first")
        verbose.log_close()
        verbose.log_open(path, 10)
        self.assertEqual(_ring_texts(), [])
        verbose.log("second")
        rows = _rows_read(path)
        self.assertEqual(
            [(row[0], row[3]) for row in rows], [(1, "first"), (2, "second")]
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
        self.assertEqual(verbose.exec(0, argv, argv), 7)
        rows = _rows_read(path)
        self.assertEqual(
            [(row[2], row[3]) for row in rows],
            [("server", "first"), ("server", "second")],
        )


# Tests the lines of the page threads, written to the database and read back.
class TestPage(unittest.TestCase):
    # Page lines are stored under their thread, in order.
    def test_page_lines(self) -> None:
        path = _log_ready(self, 10)
        verbose.lines_put(
            "ui", [verbose.LogLine(10, "a"), verbose.LogLine(20, "b")]
        )
        verbose.lines_put("ai", [verbose.LogLine(30, "c")])
        verbose.log("d")
        rows = _rows_read(path)
        self.assertEqual(
            rows[:3],
            [(1, 10, "ui", "a"), (2, 20, "ui", "b"), (3, 30, "ai", "c")],
        )
        self.assertEqual((rows[3][0], rows[3][2:]), (4, ("server", "d")))

    # Page lines are not in the ring.
    def test_page_ring(self) -> None:
        _log_ready(self, 10)
        verbose.lines_put("ui", [verbose.LogLine(10, "a")])
        self.assertEqual(_ring_texts(), [])

    # A thread other than ui or ai raises and nothing is written.
    def test_page_thread(self) -> None:
        path = _log_ready(self, 10)
        for thread in ["server", "console", ""]:
            _raise_check(
                self,
                ValueError,
                i18n("verbose.thread_unknown", thread),
                lambda: verbose.lines_put(thread, [verbose.LogLine(1, "x")]),
            )
        self.assertEqual(_rows_read(path), [])

    # A batch with a row the strict table refuses writes none of its rows.
    def test_page_batch(self) -> None:
        path = _log_ready(self, 10)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "line[.]at"):
            verbose.lines_put(
                "ui",
                [
                    verbose.LogLine(1, "ok"),
                    verbose.LogLine(cast(Any, "bad"), "x"),
                ],
            )
        self.assertEqual(_rows_read(path), [])

    # The tail of a page thread is its newest lines, oldest first, its own.
    def test_page_tail(self) -> None:
        _log_ready(self, 10)
        a = verbose.LogLine(10, "a")
        b = verbose.LogLine(20, "b")
        c = verbose.LogLine(30, "c")
        d = verbose.LogLine(40, "d")
        verbose.lines_put("ui", [a, b, c])
        verbose.lines_put("ai", [d])
        verbose.log("e")
        expected: dict[int, list[verbose.LogLine]] = {
            0: [],
            1: [c],
            2: [b, c],
            3: [a, b, c],
            _HISTORY_ALL: [a, b, c],
        }
        for count, lines in expected.items():
            self.assertEqual(verbose.tail_get("ui", count), lines)
        self.assertEqual(verbose.tail_get("ai", _HISTORY_ALL), [d])

    # The tail reads the file, so it holds the lines of an earlier opening.
    def test_tail_reopen(self) -> None:
        path = _log_ready(self, 10)
        line = verbose.LogLine(10, "a")
        verbose.lines_put("ui", [line])
        verbose.log_close()
        verbose.log_open(path, 10)
        self.assertEqual(verbose.tail_get("ui", 1), [line])

    # A thread other than ui or ai and a negative count raise.
    def test_tail_refused(self) -> None:
        _log_ready(self, 10)
        for thread in ["server", "console", ""]:
            _raise_check(
                self,
                ValueError,
                i18n("verbose.thread_unknown", thread),
                lambda: verbose.tail_get(thread, 1),
            )
        _raise_check(
            self,
            ValueError,
            i18n("verbose.count_invalid", -1),
            lambda: verbose.tail_get("ui", -1),
        )


# Tests the shell's runner at its three levels.
class TestCommand(unittest.TestCase):
    # Level 0 returns the exit code of the program.
    def test_command_code(self) -> None:
        argv = [sys.executable, "-c", _EXIT_PROGRAM]
        self.assertEqual(verbose.exec(0, argv + ["0"], argv + ["0"]), 0)
        self.assertEqual(verbose.exec(0, argv + ["5"], argv + ["5"]), 5)

    # Level 0 passes the output through and logs nothing.
    def test_command_pass(self) -> None:
        path = _log_ready(self, 10)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        code, out, err = _output_captured(
            path, lambda: verbose.exec(0, argv, argv)
        )
        self.assertEqual((code, out, err), (3, "alpha\n", "beta\n"))
        self.assertEqual(_ring_texts(), [])
        self.assertEqual(_rows_read(path), [])

    # Every level writes what Python holds for both streams before it runs.
    def test_command_flushed(self) -> None:
        path = _log_ready(self, 10)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        for level in range(3):
            code, out, err = _output_captured(
                path, lambda: _buffered_run(level, argv)
            )
            self.assertEqual(
                (code, out, err), (3, "before alpha\n", "before beta\n")
            )

    # Level 1 passes the output through and logs its start and its exit.
    def test_command_progress(self) -> None:
        path = _log_ready(self, 10)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        code, out, err = _output_captured(
            path, lambda: verbose.exec(1, argv, argv)
        )
        self.assertEqual((code, out, err), (3, "alpha\n", "beta\n"))
        texts = list(_progress_texts(argv, 3))
        self.assertEqual(_ring_texts(), texts)
        self.assertEqual([row[3] for row in _rows_read(path)], texts)

    # Level 2 passes the output through raw and logs its start and exit.
    def test_command_raw(self) -> None:
        path = _log_ready(self, 10)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        code, out, err = _output_captured(
            path, lambda: verbose.exec(2, argv, argv)
        )
        self.assertEqual((code, out, err), (3, "alpha\n", "beta\n"))
        texts = list(_progress_texts(argv, 3))
        self.assertEqual(_ring_texts(), texts)
        self.assertEqual([row[3] for row in _rows_read(path)], texts)

    # Level 2 runs the verbose command line, levels 0 and 1 the plain one.
    def test_command_chosen(self) -> None:
        path = _log_ready(self, 10)
        program = [sys.executable, "-c", _ARGS_PROGRAM]
        argv = [*program, "plain"]
        argv_verbose = [*program, "--verbose", "x y"]
        listed = str(["plain"]) + "\n"
        listed_verbose = str(["--verbose", "x y"]) + "\n"
        printed = {0: listed, 1: listed, 2: listed_verbose}
        for level, expected in printed.items():
            code, out, _ = _output_captured(
                path, lambda: verbose.exec(level, argv, argv_verbose)
            )
            self.assertEqual((code, out), (0, expected))
        plain_run, plain_exit = _progress_texts(argv, 0)
        verbose_run, verbose_exit = _progress_texts(argv_verbose, 0)
        self.assertEqual(
            _ring_texts(), [plain_run, plain_exit, verbose_run, verbose_exit]
        )

    # Every level passes the input through, so a console reads its terminal.
    def test_command_input(self) -> None:
        path = _log_ready(self, 10)
        argv = [sys.executable, "-c", _INPUT_PROGRAM]
        for level in range(3):
            code, out, _ = _output_captured(
                path,
                lambda: _input_given(
                    b"typed", lambda: verbose.exec(level, argv, argv)
                ),
            )
            self.assertEqual((code, out), (0, repr("typed") + "\n"))

    # A program that cannot start raises at every level, logged at 1 and 2.
    def test_command_start(self) -> None:
        path = _log_ready(self, 10)
        absent = [os.path.join(path, "absent")]
        for level in range(3):
            with self.assertRaises(FileNotFoundError) as caught:
                verbose.exec(level, absent, absent)
            self.assertEqual(caught.exception.filename, absent[0])
        started = i18n("verbose.exec_run", shlex.join(absent))
        self.assertEqual(_ring_texts(), [started, started])

    # Level 0 needs no log and levels 1 and 2 refuse before they run.
    def test_command_unopened(self) -> None:
        path = _scratch_make(self)
        program = [sys.executable, "-c", _MARKER_PROGRAM]
        first = [*program, os.path.join(path, "first")]
        second = [*program, os.path.join(path, "second")]
        self.assertEqual(verbose.exec(0, first, first), 0)
        self.assertTrue(os.path.exists(first[-1]))
        for level in (1, 2):
            _raise_check(
                self,
                RuntimeError,
                i18n("verbose.not_open"),
                lambda: verbose.exec(level, second, second),
            )
        self.assertFalse(os.path.exists(second[-1]))
