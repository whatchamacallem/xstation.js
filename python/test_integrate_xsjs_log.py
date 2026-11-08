# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests xsjs_log.py as a program, as a person starts it, on a log the real
# `verbose` writes outside debug mode in a scratch root in `build/`, the texts
# a server logs as it fails, each under the real strings of the browser's and
# the main loop's failures, a line in one rendered by the real `jslb`: the
# whole timeline, each option, a root given relative to the working
# directory, a root with no log, a refused option, a reader that leaves, and
# a follow of a log the server holds open, which SIGINT ends. The texts
# expected are the gold's, each `{n}` the time of the log's row `n`, which
# the test reads by SQL of its own.

import contextlib, harness, jslb, os, signal, sqlite3, subprocess, switches
import sys, tempfile, unittest, verbose
from internationalization import i18n
from typing import Any, IO, cast

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_integrate_xsjs_log"

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The program under test.
_PROGRAM_PATH = os.path.join(_ROOT_PATH, "python", "xsjs_log.py")

# The file in the root that holds the lines.
_FILE_NAME = "_verbose.sqlite"

# The largest file of the log, as the checkout sets it.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The statement that reads the time of each row of the log, in order.
_TIMES_SELECT = "SELECT at FROM line ORDER BY seq"

# The exit code of a program whose exception reached the top.
_RAISED_CODE = 1

# The exit code of a follow that SIGINT ended.
_INTERRUPTED_CODE: int = harness.gold_get(f"{_GOLD_ID}.interrupted_code")

# The exit code of arguments the parser refuses.
_USAGE_CODE: int = harness.gold_get(f"{_GOLD_ID}.usage_code")


# A value of this module's gold.
def _gold_value(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# Writes the failures to the open log, as a server without debug mode logs.
def _failures_write() -> None:
    texts: dict[str, str] = _gold_value("texts")
    verbose.log(i18n("engine_tap.browser_failed", texts["browser"]))
    verbose.log(texts["stack"])
    reply = jslb.line_make(
        jslb.header_make("kv.put", reply=102, full=True),
        [jslb.blob_make(b"note")],
        ref="/metaverse/demo/note",
    )
    refused = i18n("main_loop.reply_unknown", jslb.line_render(reply))
    verbose.log(i18n("main_loop.serve_failed", refused))


# The time of each row of the root's log, in order, read by SQL of its own.
def _times_read(root: str) -> list[int]:
    path = os.path.join(root, _FILE_NAME)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        rows: list[tuple[int]] = connection.execute(_TIMES_SELECT).fetchall()
    return [at for (at,) in rows]


# The text with each `{n}` the time of the root's row `n`.
def _times_filled(root: str, text: str) -> str:
    for index, at in enumerate(_times_read(root)):
        text = text.replace("{" + str(index) + "}", str(at))
    return text


# Runs the program to its end in the directory, the root given as named.
def _program_run(
    arguments: list[str], directory: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, _PROGRAM_PATH, *arguments],
        check=False,
        cwd=directory,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
    )


# Each test runs the program on a turn's log in a root of its own.
class TestProgram(unittest.TestCase):
    # Writes the failures and closes the log, as a server that ended does.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.root = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        saved = switches.switches_get()
        self.addCleanup(switches.switches_apply, saved)
        switches.switches_apply({**saved, "debug": False})
        verbose.log_open(self.root, _BLOB_MAX)
        try:
            _failures_write()
        finally:
            verbose.log_close()
        printed: list[str] = _gold_value("printed")
        self.printed = [_times_filled(self.root, text) for text in printed]

    # Raises unless the program ended with 0, printing the lines and no error.
    def printed_check(
        self, ended: subprocess.CompletedProcess[str], lines: list[str]
    ) -> None:
        self.assertEqual(ended.stderr, "")
        self.assertEqual(ended.stdout.splitlines(), lines)
        self.assertEqual(ended.returncode, 0)

    # The program prints the whole timeline, one line per entry, in order.
    def test_timeline_printed(self) -> None:
        self.printed_check(_program_run([self.root]), self.printed)

    # Each option takes the entries that pass it, and the options join.
    def test_options_taken(self) -> None:
        for case, gold in _gold_value("runs").items():
            with self.subTest(case=case):
                lines = [self.printed[index] for index in gold["printed"]]
                ended = _program_run([self.root, *gold["arguments"]])
                self.printed_check(ended, lines)

    # A root named from the working directory prints the same.
    def test_root_relative(self) -> None:
        directory, name = os.path.split(self.root)
        self.printed_check(_program_run([name], directory), self.printed)

    # A root with no log exits as a raised error does, naming the file.
    def test_log_missing(self) -> None:
        root = os.path.join(self.root, "absent")
        ended = _program_run([root])
        text: str = _gold_value("texts.xsjs_log_file_missing")
        path = os.path.join(root, _FILE_NAME)
        self.assertEqual(ended.stdout, "")
        self.assertIn(text.replace("{0}", path), ended.stderr)
        self.assertEqual(ended.returncode, _RAISED_CODE)

    # A thread that is none of the three exits with the parser's code.
    def test_thread_refused(self) -> None:
        ended = _program_run([self.root, "--thread", "console"])
        self.assertEqual(ended.stdout, "")
        self.assertEqual(ended.returncode, _USAGE_CODE)

    # A reader that leaves, as `head` does, ends the program with no error.
    def test_reader_left(self) -> None:
        verbose.log_open(self.root, _BLOB_MAX)
        self.addCleanup(verbose.log_close)
        later: dict[str, Any] = _gold_value("later")
        with subprocess.Popen(
            [sys.executable, _PROGRAM_PATH, self.root, "--follow"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        ) as program:
            try:
                output = cast(IO[str], program.stdout)
                for _ in self.printed:
                    output.readline()
                output.close()
                verbose.log(later["text"])
                errors = cast(IO[str], program.stderr).read()
                program.wait()
            finally:
                program.kill()
        self.assertEqual(errors, "")
        self.assertEqual(program.returncode, -signal.SIGPIPE)

    # A follow prints the held lines, a new line of the open log, and ends.
    def test_follow_live(self) -> None:
        verbose.log_open(self.root, _BLOB_MAX)
        self.addCleanup(verbose.log_close)
        later: dict[str, Any] = _gold_value("later")
        with subprocess.Popen(
            [sys.executable, _PROGRAM_PATH, self.root, "--follow"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        ) as program:
            try:
                output = cast(IO[str], program.stdout)
                held = [
                    output.readline().removesuffix("\n") for _ in self.printed
                ]
                self.assertEqual(held, self.printed)
                verbose.log(later["text"])
                printed = output.readline().removesuffix("\n")
                expected = _times_filled(self.root, later["printed"])
                self.assertEqual(printed, expected)
                program.send_signal(signal.SIGINT)
                rest, errors = program.communicate()
            finally:
                program.kill()
        self.assertEqual(rest, "")
        self.assertEqual(errors, "")
        self.assertEqual(program.returncode, _INTERRUPTED_CODE)
