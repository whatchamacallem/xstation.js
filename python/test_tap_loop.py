# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP suite server, tap_loop.py, in forked children over pipes,
# with roots in `build/` whose settings are the checkout's with the gold's
# overflow_bytes, and its error texts against the gold. The driver it runs
# is the real test_all.py, on a small suite and on failing_suite, the suite
# that fails by design: the pushes and the reply are compared with what the
# test reads from the same driver, run by the test with the command line the
# request must build, the times it writes to stderr aside. Each child writes
# how its work ended to a file, or to stderr with the failure when that
# write fails, then kills itself whatever happened, so the handler it
# registers never reaches another test.

import functools, harness, json, os, re, signal, subprocess, sys, tap_loop
import tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The driver the server runs, which the test runs too.
_DRIVER_PATH = os.path.join(_ROOT_PATH, "python", "test_all.py")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_tap_loop"

# A size chosen by its writer, small: a blob over it would stream.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# A size chosen by its writer: the most the test reads from a pipe at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The most seconds a run of the driver by the test may take.
_CHILD_SECONDS: int = harness.gold_get(f"{_GOLD_ID}.child_seconds")

# How a child ends when the loop returns at the end of its input.
_ENDING_RETURNED = "returned"

# How a child ends when the loop exits 1.
_ENDING_FAILED = "exit 1"

# The exit code of the driver when the failing tests are those expected.
_DRIVER_PASSED = 0

# The exit code of the driver when they are not.
_DRIVER_FAILED = 1

# A run of digits, such as the seconds the driver writes to stderr.
_DIGITS = re.compile(r"[0-9]+")

# A `tap.run` in short names: `normal-test`, failfast, 1 failure, 2 suites.
_RUN_SHORT = (
    b'{"0":{"t":"tap.run","i":1},"category":"normal-test","failfast":true,'
    b'"failures":1,"modules":["test_tap_producer","failing_suite"]}\r'
)

# The words of the command the driver gets for that request.
_WORDS_SHORT = [
    "--stream",
    "--normal-test",
    "--failfast",
    "--failures",
    "1",
    "--module",
    "test_tap_producer",
    "--module",
    "failing_suite",
]

# A `tap.run` in full names: `smoke-test`, no failfast, none failing, 1 suite.
_RUN_FULL = (
    b'{"0":{"type":"tap.run","id":7},"category":"smoke-test",'
    b'"failfast":false,"failures":0,"modules":["test_tap_producer"]}\r'
)

# The words of the command the driver gets for that request.
_WORDS_FULL = [
    "--stream",
    "--smoke-test",
    "--failures",
    "0",
    "--module",
    "test_tap_producer",
]

# A `tap.run` of the failing suite that expects none of its failures.
_RUN_FAILED = (
    b'{"0":{"t":"tap.run","i":2},"category":"normal-test",'
    b'"failfast":false,"failures":0,"modules":["failing_suite"]}\r'
)

# The words of the command the driver gets for that request.
_WORDS_FAILED = [
    "--stream",
    "--normal-test",
    "--failures",
    "0",
    "--module",
    "failing_suite",
]

# A reply on the engine tty, which the server awaits none of.
_REPLY_STRAY = b'{"0":{"t":"tap.run","r":1}}\r'

# A request of a type the server has no handler for.
_TYPE_UNKNOWN = b'{"0":{"t":"no.such","i":1}}\r'

# A request cut before the CR that ends its line.
_LINE_CUT = b'{"0":{"t":"tap.run","i":1}}'


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# Splits output into its lines, none of which carries a blob.
def _lines_split(output: bytes) -> list[dict[str, Any]]:
    return [json.loads(text) for text in output.split(b"\r")[:-1]]


# The `tap.line` push of a line of the stream in the name form given.
def _push_make(text: str, full: bool) -> dict[str, Any]:
    header = {"type": "tap.line"} if full else {"t": "tap.line"}
    return {"0": header, "language": "python", "text": text}


# `tap.run` with a blob over `_OVERFLOW_BYTES`, one small suite, not recursing.
def _blob_line(size: int) -> bytes:
    text = (
        f'{{"0":{{"t":"tap.run","i":1,"b":1}},"1":{{"s":{size}}},'
        f'"category":"smoke-test","failfast":false,"failures":0,'
        f'"modules":["test_tap_producer"]}}\r'
    )
    return text.encode("utf-8") + bytes(size)


# The text with each run of digits made `0`, so that two runs' times agree.
def _digits_mask(text: str) -> str:
    return _DIGITS.sub("0", text)


# Reads a pipe to its end and closes it.
def _pipe_drain(fd: int) -> bytes:
    data = bytearray()
    while chunk := os.read(fd, _READ_BYTES):
        data += chunk
    os.close(fd)
    return bytes(data)


# The lines a run of the driver wrote to stdout, its stderr and exit code.
class DriverRun(NamedTuple):
    code: int
    lines: list[str]
    errors: str


# Runs the driver with the words given, its input empty, as the server does.
def _driver_run(words: list[str]) -> DriverRun:
    done = subprocess.run(
        [sys.executable, _DRIVER_PATH, *words],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=_CHILD_SECONDS,
    )
    *lines, rest = done.stdout.decode("utf-8").split("\n")
    if rest:
        raise AssertionError(
            f"the driver's output ends inside a line: {rest!r}"
        )
    return DriverRun(done.returncode, lines, done.stderr.decode("utf-8"))


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(
    work: Callable[[int, int], str], read_fd: int, write_fd: int, path: str
) -> None:
    try:
        try:
            ending = work(read_fd, write_fd)
        except SystemExit as error:
            ending = f"exit {error.code}"
        except BaseException:
            ending = traceback.format_exc()
        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(ending)
        except BaseException:
            # The parent finds no ending, so the failure and it go to stderr.
            sys.stderr.write(
                f"{traceback.format_exc()}the ending not written: {ending}\n"
            )
            sys.stderr.flush()
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# The work of a child that prepares the root and says what it returned.
def _prepare_once(root: str, read_fd: int, write_fd: int) -> str:
    return json.dumps(tap_loop.loop_prepare(root))


# The work of a child that prepares the root and serves the pipes to the end.
def _suites_serve(root: str, read_fd: int, write_fd: int) -> str:
    tap_loop.loop_prepare(root)
    tap_loop.loop_run(read_fd, write_fd, root)
    return _ENDING_RETURNED


# Gives each test a scratch root in `build/` with the small blob limit.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the root with the small blob limit.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)
        self.settings_write(False)

    # Writes the root's settings, the setting `debug` as given.
    def settings_write(self, debug: bool) -> None:
        values = harness.settings_copy()
        values["overflow_bytes"] = _OVERFLOW_BYTES
        values["debug"] = debug
        path = os.path.join(self.root, "settings.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(values, file)

    # Runs the work in a child fed the data, returns its ending and output.
    def child_run(
        self, work: Callable[[int, int], str], data: bytes
    ) -> tuple[str, bytes]:
        input_read, input_write = os.pipe()
        os.set_blocking(input_write, False)
        self.assertEqual(os.write(input_write, data), len(data))
        os.close(input_write)
        output_read, output_write = os.pipe()
        path = os.path.join(self.scratch, "ending.txt")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(output_read)
            _child_end(work, input_read, output_write, path)
        os.close(input_read)
        os.close(output_write)
        output = _pipe_drain(output_read)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(path)
        return ending, output

    # Serves the data in a child, returns the ending and the lines written.
    def serve_read(self, data: bytes) -> tuple[str, list[dict[str, Any]]]:
        work = functools.partial(_suites_serve, self.root)
        ending, output = self.child_run(work, data)
        return ending, _lines_split(output)

    # Checks each line pushed, the reply's exit code and stderr, times aside.
    def served_check(
        self,
        lines: list[dict[str, Any]],
        run: DriverRun,
        header: dict[str, Any],
        full: bool,
    ) -> None:
        *pushes, reply = lines
        expected = [_push_make(text, full) for text in run.lines]
        self.assertEqual(pushes, expected)
        self.assertEqual(sorted(reply), ["0", "code", "stderr"])
        self.assertEqual(reply["0"], header)
        self.assertEqual(reply["code"], run.code)
        self.assertEqual(
            _digits_mask(reply["stderr"]), _digits_mask(run.errors)
        )

    # Checks the one line written is an `error` line with the header given.
    def error_check(
        self, lines: list[dict[str, Any]], header: dict[str, Any], text: str
    ) -> None:
        (line,) = lines
        self.assertEqual(line["0"], header)
        self.assertEqual(line["message"], text)


# `loop_prepare`: the settings read, nothing made in the root.
class TestPrepare(ScratchCase):
    # The root gains nothing, and nothing is returned or written.
    def test_prepare_bare(self) -> None:
        work = functools.partial(_prepare_once, self.root)
        ending, output = self.child_run(work, b"")
        self.assertEqual(output, b"")
        self.assertIsNone(json.loads(ending))
        self.assertEqual(os.listdir(self.root), ["settings.json"])


# `loop_run` over pipes: the runs served, the lines pushed, the refusals.
class TestRun(ScratchCase):
    # Each line of the driver's stream is pushed, then its code and stderr.
    def test_run_served(self) -> None:
        ending, lines = self.serve_read(_RUN_SHORT)
        self.assertEqual(ending, _ENDING_RETURNED)
        run = _driver_run(_WORDS_SHORT)
        self.assertEqual(run.code, _DRIVER_PASSED)
        self.served_check(lines, run, {"t": "tap.run", "r": 1}, False)

    # In debug mode the pushes and the reply have full names.
    def test_run_full(self) -> None:
        self.settings_write(True)
        ending, lines = self.serve_read(_RUN_FULL)
        self.assertEqual(ending, _ENDING_RETURNED)
        run = _driver_run(_WORDS_FULL)
        self.assertEqual(run.code, _DRIVER_PASSED)
        self.served_check(lines, run, {"type": "tap.run", "reply": 7}, True)

    # A run whose failing tests are not those expected replies its code.
    def test_run_failed(self) -> None:
        ending, lines = self.serve_read(_RUN_FAILED)
        self.assertEqual(ending, _ENDING_RETURNED)
        run = _driver_run(_WORDS_FAILED)
        self.assertEqual(run.code, _DRIVER_FAILED)
        self.served_check(lines, run, {"t": "tap.run", "r": 2}, False)

    # A line carrying `r` is refused before dispatch, with no id answered.
    def test_reply_refused(self) -> None:
        ending, lines = self.serve_read(_REPLY_STRAY)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("tap_loop_reply_unknown")
        self.error_check(lines, {"t": "error"}, text)

    # A type with no handler gets one `error` line with its id.
    def test_type_unknown(self) -> None:
        ending, lines = self.serve_read(_TYPE_UNKNOWN)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("dispatch_handler_unknown")
        self.error_check(lines, {"t": "error", "r": 1}, text)

    # The input ending inside a line: an `error` line with no id.
    def test_end_partial(self) -> None:
        ending, lines = self.serve_read(_LINE_CUT)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("tap_loop_input_partial")
        self.error_check(lines, {"t": "error"}, text)

    # A blob over `overflow_bytes` is refused before its line is served.
    def test_blob_refused(self) -> None:
        line = _blob_line(_OVERFLOW_BYTES * 2 + 1)
        ending, lines = self.serve_read(line)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("tap_loop_blob_refused")
        self.error_check(lines, {"t": "error"}, text)
