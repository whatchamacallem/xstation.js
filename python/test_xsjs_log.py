# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the log program on logs that the server's own `verbose` writes
# outside debug mode, in a scratch root in `build/`, beside rows of the page
# threads `ui` and `ai`, which no server function writes any more, put by the
# test's own SQL into the same table: each log reads back as stored and in
# order, whether the server holds it open or has ended; the filters of both
# readings; the printed form of an entry; a follow that reads what the file
# holds, then each line as it is written, by this process and by another that
# waits first; the refused arguments; a follow that SIGINT ends in a forked
# child; and the program run as a script. The lines, the cases and the texts
# are the gold's.

import contextlib, harness, io, itertools, os, runpy, signal, sqlite3
import switches, sys, tempfile, time, traceback, unittest, verbose, xsjs_log
from collections.abc import Callable
from typing import Any, cast

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_xsjs_log"

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The program, which a test runs as a script.
_PROGRAM_PATH = os.path.join(_ROOT_PATH, "python", "xsjs_log.py")

# The file in the root that holds the lines.
_FILE_NAME = "_verbose.sqlite"

# The thread that a line from the server itself is stored under.
_SERVER_THREAD = "server"

# The largest file of the log, as the checkout sets it.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The statement that stores a row of a page thread in the log's table.
_PAGE_INSERT = "INSERT INTO line (at, thread, text) VALUES (?, ?, ?)"

# The statement that reads the times of the server's rows, in order.
_SERVER_SELECT = "SELECT at FROM line WHERE thread = 'server' ORDER BY seq"

# The exit code of a follow that SIGINT ended.
_INTERRUPTED_CODE: int = harness.gold_get(f"{_GOLD_ID}.interrupted_code")

# The exit code of arguments the parser refuses.
_USAGE_CODE: int = harness.gold_get(f"{_GOLD_ID}.usage_code")

# The seconds a child waits before it writes, so that a follow waits for it.
_WRITE_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.write_seconds")

# The text a child writes while a follow waits.
_LATER_TEXT: str = harness.gold_get(f"{_GOLD_ID}.later_text")


# A value of this module's gold.
def _gold_value(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# Writes rows of a page thread to the root's log by a connection of its own.
def _page_put(root: str, thread: str, lines: list[tuple[int, str]]) -> None:
    path = os.path.join(root, _FILE_NAME)
    rows = [(at, thread, text) for at, text in lines]
    with contextlib.closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.executemany(_PAGE_INSERT, rows)


# The time of each row of the server in the root's log, in order.
def _server_times(root: str) -> list[int]:
    path = os.path.join(root, _FILE_NAME)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        rows: list[tuple[int]] = connection.execute(_SERVER_SELECT).fetchall()
    return [at for (at,) in rows]


# Writes the gold's log to the root's open log, returns its entries in order.
def _log_write(root: str) -> list[xsjs_log.LogEntry]:
    rows: list[tuple[int, str, str]] = []
    for write in _gold_value("log.page_writes"):
        thread: str = write["thread"]
        lines = [(line["at"], line["text"]) for line in write["lines"]]
        _page_put(root, thread, lines)
        rows.extend((at, thread, text) for at, text in lines)
    texts: list[str] = _gold_value("log.server_texts")
    for text in texts:
        verbose.log(text)
    times = _server_times(root)[-len(texts) :]
    rows.extend((at, _SERVER_THREAD, text) for at, text in zip(times, texts))
    return [xsjs_log.LogEntry(seq, *row) for seq, row in enumerate(rows, 1)]


# The printed line of each entry, in order.
def _entries_printed(entries: list[xsjs_log.LogEntry]) -> list[str]:
    return [xsjs_log.entry_text(entry) for entry in entries]


# The bytes of the file.
def _file_bytes(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# The code `log_run` returns for the arguments, and the lines it printed.
def _run_printed(arguments: list[str]) -> tuple[int, list[str]]:
    with contextlib.redirect_stdout(io.StringIO()) as output:
        code = xsjs_log.log_run(arguments)
    return code, output.getvalue().splitlines()


# In the forked child: waits, writes a line, and dies with the log still open.
def _later_write(root: str) -> None:
    try:
        time.sleep(_WRITE_SECONDS)
        verbose.log_open(root, _BLOB_MAX)
        verbose.log(_LATER_TEXT)
    except BaseException:
        # The parent's follow waits on, so the failure goes to stderr.
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# In the forked child: follows the root, stdout on the pipe, exits as it ends.
def _follow_exit(root: str, write_fd: int) -> None:
    code = 1
    try:
        with (
            open(write_fd, "w", encoding="utf-8") as output,
            contextlib.redirect_stdout(output),
        ):
            xsjs_log.log_run([root, "--follow"])
    except SystemExit as ending:
        code = cast(int, ending.code)
    except BaseException:
        # The parent finds the wrong code, so the failure goes to stderr.
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
    finally:
        os._exit(code)


# Follows the root in a child for `count` lines, then ends it by SIGINT.
def _follow_interrupted(root: str, count: int) -> tuple[list[str], int]:
    read_fd, write_fd = os.pipe()
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        _follow_exit(root, write_fd)
    os.close(write_fd)
    with open(read_fd, encoding="utf-8") as output:
        try:
            printed = [
                output.readline().removesuffix("\n") for _ in range(count)
            ]
            os.kill(pid, signal.SIGINT)
            status = os.waitpid(pid, 0)[1]
        except BaseException:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            raise
    return printed, os.waitstatus_to_exitcode(status)


# Gives each test an empty root in a scratch directory of `build/`.
class RootCase(unittest.TestCase):
    # Makes the root, which goes when the test ends, outside debug mode.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.root = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        saved = switches.switches_get()
        self.addCleanup(switches.switches_apply, saved)
        switches.switches_apply({**saved, "debug": False})

    # Opens the root's log until the test ends, as a running server holds it.
    def log_ready(self) -> None:
        verbose.log_open(self.root, _BLOB_MAX)
        self.addCleanup(verbose.log_close)

    # Writes the gold's log and closes it, as a server that ended leaves it.
    def log_ended(self) -> list[xsjs_log.LogEntry]:
        verbose.log_open(self.root, _BLOB_MAX)
        try:
            return _log_write(self.root)
        finally:
            verbose.log_close()


# Tests the reading of a whole log.
class TestRead(RootCase):
    # Every line reads back as stored, in the order the server wrote them.
    def test_lines_read(self) -> None:
        entries = self.log_ended()
        self.assertEqual(xsjs_log.lines_read(self.root), entries)

    # A log the server holds open reads the same, each line once it is written.
    def test_log_open(self) -> None:
        self.log_ready()
        entries = _log_write(self.root)
        self.assertEqual(xsjs_log.lines_read(self.root), entries)
        verbose.log(_LATER_TEXT)
        last = xsjs_log.lines_read(self.root)[-1]
        self.assertEqual(last.seq, len(entries) + 1)
        self.assertEqual(last.text, _LATER_TEXT)

    # A log with no lines reads as no entries.
    def test_log_empty(self) -> None:
        self.log_ready()
        self.assertEqual(xsjs_log.lines_read(self.root), [])

    # A reading leaves the file as it was.
    def test_file_unchanged(self) -> None:
        self.log_ended()
        path = os.path.join(self.root, _FILE_NAME)
        before = _file_bytes(path)
        xsjs_log.lines_read(self.root)
        self.assertEqual(_file_bytes(path), before)

    # A root with no log raises at every reading, and gains no file.
    def test_log_missing(self) -> None:
        previous = signal.getsignal(signal.SIGINT)
        self.addCleanup(signal.signal, signal.SIGINT, previous)
        path = os.path.join(self.root, _FILE_NAME)
        text: str = _gold_value("texts.xsjs_log_file_missing")
        uses: list[Callable[[], object]] = [
            lambda: xsjs_log.lines_read(self.root),
            lambda: next(xsjs_log.lines_follow(self.root)),
            lambda: xsjs_log.log_run([self.root]),
            lambda: xsjs_log.log_run([self.root, "--follow"]),
        ]
        for use in uses:
            with self.assertRaises(FileNotFoundError) as caught:
                use()
            self.assertEqual(str(caught.exception), text.replace("{0}", path))
        self.assertFalse(os.path.exists(path))


# Tests the filters of both readings.
class TestFilter(RootCase):
    # An entry of a reading passes every filter given, and no other does.
    def test_filters_read(self) -> None:
        self.log_ended()
        for case, gold in _gold_value("passes").items():
            with self.subTest(case=case):
                entries = xsjs_log.lines_read(self.root, **gold["filters"])
                seqs = [entry.seq for entry in entries]
                self.assertEqual(seqs, gold["seqs"])

    # A follow passes the entries a reading passes, in the same order.
    def test_filters_followed(self) -> None:
        self.log_ended()
        for case, gold in _gold_value("passes").items():
            with self.subTest(case=case):
                followed = xsjs_log.lines_follow(self.root, **gold["filters"])
                entries = itertools.islice(followed, len(gold["seqs"]))
                seqs = [entry.seq for entry in entries]
                self.assertEqual(seqs, gold["seqs"])


# Tests the printed form of an entry.
class TestEntry(unittest.TestCase):
    # An entry prints as one line, each newline of its text as a backslash n.
    def test_entry_printed(self) -> None:
        for case, gold in _gold_value("printed").items():
            with self.subTest(case=case):
                entry = xsjs_log.LogEntry(*gold["entry"])
                self.assertEqual(xsjs_log.entry_text(entry), gold["text"])


# Tests the reading that keeps on as the file grows.
class TestFollow(RootCase):
    # The lines held come first, then each line as it is written.
    def test_lines_followed(self) -> None:
        self.log_ready()
        entries = _log_write(self.root)
        followed = xsjs_log.lines_follow(self.root)
        held = list(itertools.islice(followed, len(entries)))
        self.assertEqual(held, entries)
        verbose.log(_LATER_TEXT)
        at = _server_times(self.root)[-1]
        seq = len(entries) + 1
        expected = xsjs_log.LogEntry(seq, at, _SERVER_THREAD, _LATER_TEXT)
        self.assertEqual(next(followed), expected)
        _page_put(self.root, "ui", [(60, "page line")])
        expected = xsjs_log.LogEntry(seq + 1, 60, "ui", "page line")
        self.assertEqual(next(followed), expected)

    # A line written later that fails a filter is passed over.
    def test_later_filtered(self) -> None:
        self.log_ready()
        entries = _log_write(self.root)
        passing = [entry for entry in entries if entry.thread == "ai"]
        followed = xsjs_log.lines_follow(self.root, thread="ai")
        held = list(itertools.islice(followed, len(passing)))
        self.assertEqual(held, passing)
        verbose.log(_LATER_TEXT)
        _page_put(self.root, "ai", [(70, "page line")])
        seq = len(entries) + 2
        expected = xsjs_log.LogEntry(seq, 70, "ai", "page line")
        self.assertEqual(next(followed), expected)

    # A line another process writes while the follow waits is read as it comes.
    def test_follow_waits(self) -> None:
        entries = self.log_ended()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _later_write(self.root)
        followed = xsjs_log.lines_follow(self.root)
        read = list(itertools.islice(followed, len(entries) + 1))
        self.assertEqual(read[:-1], entries)
        self.assertEqual(read[-1].seq, len(entries) + 1)
        self.assertEqual(read[-1].text, _LATER_TEXT)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)


# Tests the run of the program by its arguments.
class TestRun(RootCase):
    # A run prints every entry, one line each, and returns 0.
    def test_timeline_printed(self) -> None:
        expected = _entries_printed(self.log_ended())
        self.assertEqual(_run_printed([self.root]), (0, expected))

    # Each option filters what the run prints.
    def test_options_taken(self) -> None:
        entries = self.log_ended()
        for case, gold in _gold_value("runs").items():
            with self.subTest(case=case):
                chosen = [entries[seq - 1] for seq in gold["seqs"]]
                printed = _run_printed([self.root, *gold["arguments"]])
                self.assertEqual(printed, (0, _entries_printed(chosen)))

    # Arguments the parser refuses exit with its code.
    def test_arguments_refused(self) -> None:
        for case, arguments in _gold_value("refused").items():
            with self.subTest(case=case):
                with (
                    contextlib.redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as caught,
                ):
                    xsjs_log.log_run(arguments)
                self.assertEqual(caught.exception.code, _USAGE_CODE)

    # A follow prints the lines held, and SIGINT ends it with the shell's code.
    def test_follow_interrupted(self) -> None:
        entries = self.log_ended()
        printed, code = _follow_interrupted(self.root, len(entries))
        self.assertEqual(printed, _entries_printed(entries))
        self.assertEqual(code, _INTERRUPTED_CODE)

    # Run as a script, the program prints the timeline and exits with 0.
    def test_script_run(self) -> None:
        expected = _entries_printed(self.log_ended())
        self.addCleanup(setattr, sys, "argv", sys.argv)
        pipe_action = signal.getsignal(signal.SIGPIPE)
        self.addCleanup(signal.signal, signal.SIGPIPE, pipe_action)
        sys.argv = [_PROGRAM_PATH, self.root]
        with (
            contextlib.redirect_stdout(io.StringIO()) as output,
            self.assertRaises(SystemExit) as caught,
        ):
            runpy.run_path(_PROGRAM_PATH, run_name="__main__")
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(output.getvalue().splitlines(), expected)
