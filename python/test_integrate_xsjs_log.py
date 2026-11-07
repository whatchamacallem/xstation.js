# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests xsjs_log.py as a program, as a person starts it, on a log the real
# `verbose` writes in a scratch root in `build/`, each text rendered by the
# real `jslb` under the real strings of the page's and the server's timeline
# lines: the whole timeline, each option, a root given relative to the working
# directory, a root with no log, a refused option, and a follow of a log the
# server holds open, which SIGINT ends. The texts expected are the gold's.

import harness, jslb, os, signal, subprocess, sys, tempfile, unittest, verbose
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

# The ring and the largest file of the log, as the checkout sets them.
_RING: int = harness.setting_get("verbose_ring")
_BLOB_MAX: int = harness.setting_get("blob_max")

# The exit code of a program whose exception reached the top.
_RAISED_CODE = 1

# The exit code of a follow that SIGINT ended.
_INTERRUPTED_CODE: int = harness.gold_get(f"{_GOLD_ID}.interrupted_code")

# The exit code of arguments the parser refuses.
_USAGE_CODE: int = harness.gold_get(f"{_GOLD_ID}.usage_code")

# The times of the page's lines, in the order they are written.
_SAY_AT = 10
_DISPATCH_AT = 20
_PUT_AT = 30

# The lines the server itself writes in the log.
_SERVER_LINES = 2


# A value of this module's gold.
def _gold_value(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# Writes a turn to the open log, as the page and the server note its lines.
def _turn_write() -> None:
    say = jslb.line_render(
        jslb.line_make(
            jslb.header_make("ai.say", id=102, full=True), [], text="1"
        )
    )
    put = jslb.line_render(
        jslb.line_make(
            jslb.header_make("kv.put", full=True),
            [jslb.blob_make(b"note")],
            ref="/metaverse/demo/note",
        )
    )
    submitted = i18n("queue.submit", "ui", "ai", say)
    verbose.lines_put("ui", [verbose.LogLine(_SAY_AT, submitted)])
    dispatched = i18n("queue.dispatch", "ai", "ui", say)
    notified = i18n("queue.notify", "ai", "server", put)
    verbose.lines_put(
        "ai",
        [
            verbose.LogLine(_DISPATCH_AT, dispatched),
            verbose.LogLine(_PUT_AT, notified),
        ],
    )
    verbose.log(i18n("main_loop.line_dispatch", put))
    verbose.log(i18n("main_loop.serve_failed", _gold_value("texts.failure")))


# The lines the program prints of the turn, the server's with their times.
def _printed_expected() -> list[str]:
    printed: list[str] = []
    for text in _gold_value("printed"):
        for index, line in enumerate(verbose.history_get(_SERVER_LINES)):
            text = text.replace("{" + str(index) + "}", str(line.at))
        printed.append(text)
    return printed


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
    # Writes the turn and closes the log, as a server that ended leaves it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.root = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        verbose.log_open(self.root, _RING, _BLOB_MAX)
        try:
            _turn_write()
            self.printed = _printed_expected()
        finally:
            verbose.log_close()

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

    # A follow prints the held lines, a new line of the open log, and ends.
    def test_follow_live(self) -> None:
        verbose.log_open(self.root, _RING, _BLOB_MAX)
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
                line = verbose.LogLine(later["at"], later["text"])
                verbose.lines_put("ui", [line])
                printed = output.readline().removesuffix("\n")
                self.assertEqual(printed, later["printed"])
                program.send_signal(signal.SIGINT)
                rest, errors = program.communicate()
            finally:
                program.kill()
        self.assertEqual(rest, "")
        self.assertEqual(errors, "")
        self.assertEqual(program.returncode, _INTERRUPTED_CODE)
