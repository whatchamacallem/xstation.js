# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP suite server, tap_loop.py, in forked children over pipes,
# with roots in `build/` whose settings are the checkout's with the gold's
# overflow_bytes, and its error texts against the gold. The driver it runs
# is a double, a script in the scratch directory run by python3 as the
# driver would be, put in place of test_all.py's file: it writes the words
# of its command line, one a line, so a test reads the command tap.run
# builds, or it ends its output inside a line, or it waits for a file the
# test makes, so a test sees a line pushed before the driver ends. Each
# child writes how its work ended to a file, or to stderr with the failure
# when that write fails, then kills itself whatever happened, so the handler
# it registers never reaches another test.

import functools, harness, json, os, select, signal, sys, tap_loop, tempfile
import traceback, types, unittest, unittest.mock
from collections.abc import Callable
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_tap_loop"

# A size chosen by its writer, small: a blob over it would stream.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# A size chosen by its writer: the most the test reads from a pipe at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The most seconds a wait on a child of a test may take.
_CHILD_SECONDS: int = harness.gold_get(f"{_GOLD_ID}.child_seconds")

# How a child ends when the loop returns at the end of its input.
_ENDING_RETURNED = "returned"

# How a child ends when the loop exits 1.
_ENDING_FAILED = "exit 1"

# The exit code of the double that writes its command line.
_DRIVER_CODE = 3

# What the double that writes its command line writes to stderr.
_DRIVER_ERRORS = "written to stderr\n"

# The double that writes the words of its command line, one a line.
_WORDS_SCRIPT = f"""import sys
for word in sys.argv[1:]:
    print(word, flush=True)
sys.stderr.write({_DRIVER_ERRORS!r})
sys.exit({_DRIVER_CODE})
"""

# The double that ends its output inside a line.
_CUT_SCRIPT = """import sys
sys.stdout.write("cut")
"""

# The double that writes a line, waits for the file named, then another.
_WAIT_SCRIPT = """import os, sys, time
print("first", flush=True)
deadline = time.monotonic() + {seconds}
while not os.path.exists({path!r}):
    if time.monotonic() > deadline:
        sys.exit("the file never came")
    time.sleep(0.01)
print("second", flush=True)
"""

# A `tap.run` in short names: `normal-test`, failfast, 2 failures, 2 suites.
_RUN_SHORT = (
    b'{"0":{"t":"tap.run","i":1},"category":"normal-test","failfast":true,'
    b'"failures":2,"modules":["test_first","test_second"]}\r'
)

# The words of the command the double gets for that request.
_WORDS_SHORT = [
    "--stream",
    "--normal-test",
    "--failfast",
    "--failures",
    "2",
    "--module",
    "test_first",
    "--module",
    "test_second",
]

# A `tap.run` in full names: `smoke-test`, no failfast, none failing, no suite.
_RUN_FULL = (
    b'{"0":{"type":"tap.run","id":7},"category":"smoke-test",'
    b'"failfast":false,"failures":0,"modules":[]}\r'
)

# The words of the command the double gets for that request.
_WORDS_FULL = ["--stream", "--smoke-test", "--failures", "0"]

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


# The `tap.line` push of a word in the name form given.
def _push_make(text: str, full: bool) -> dict[str, Any]:
    header = {"type": "tap.line"} if full else {"t": "tap.line"}
    return {"0": header, "language": "python", "text": text}


# The `tap.run` line with a blob of the size given, over `_OVERFLOW_BYTES`.
def _blob_line(size: int) -> bytes:
    text = (
        f'{{"0":{{"t":"tap.run","i":1,"b":1}},"1":{{"s":{size}}},'
        f'"category":"smoke-test","failfast":false,"failures":0,'
        f'"modules":[]}}\r'
    )
    return text.encode("utf-8") + bytes(size)


# Reads a pipe to its end and closes it.
def _pipe_drain(fd: int) -> bytes:
    data = bytearray()
    while chunk := os.read(fd, _READ_BYTES):
        data += chunk
    os.close(fd)
    return bytes(data)


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


# The work of a child that serves the pipes to the end, the driver a script.
def _suites_serve(root: str, driver: str, read_fd: int, write_fd: int) -> str:
    stand_in = types.SimpleNamespace(__file__=driver)
    with unittest.mock.patch.object(tap_loop, "test_all", stand_in):
        tap_loop.loop_prepare(root)
        tap_loop.loop_run(read_fd, write_fd, root)
    return _ENDING_RETURNED


# A forked child, the ends of its pipes the test holds, its ending's file.
class ChildRun(NamedTuple):
    pid: int
    input_fd: int
    output_fd: int
    path: str


# Gives each test a scratch root in `build/` and a driver double in it.
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

    # Writes a driver double into the scratch directory and returns it.
    def driver_write(self, text: str) -> str:
        path = os.path.join(self.scratch, "driver.py")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path

    # Starts the work in a child on two new pipes, the input left open.
    def child_start(self, work: Callable[[int, int], str]) -> ChildRun:
        input_read, input_write = os.pipe()
        output_read, output_write = os.pipe()
        path = os.path.join(self.scratch, "ending.txt")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(input_write)
            os.close(output_read)
            _child_end(work, input_read, output_write, path)
        os.close(input_read)
        os.close(output_write)
        return ChildRun(pid, input_write, output_read, path)

    # Ends the input, reads the output to its end, returns it and the ending.
    def child_finish(self, child: ChildRun) -> tuple[str, bytes]:
        os.close(child.input_fd)
        output = _pipe_drain(child.output_fd)
        status = os.waitpid(child.pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(child.path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(child.path)
        return ending, output

    # Runs the work in a child fed the data, returns its ending and output.
    def child_run(
        self, work: Callable[[int, int], str], data: bytes
    ) -> tuple[str, bytes]:
        child = self.child_start(work)
        os.set_blocking(child.input_fd, False)
        self.assertEqual(os.write(child.input_fd, data), len(data))
        return self.child_finish(child)

    # Serves the data with the driver double, returns the ending and lines.
    def serve_read(
        self, script: str, data: bytes
    ) -> tuple[str, list[dict[str, Any]]]:
        driver = self.driver_write(script)
        work = functools.partial(_suites_serve, self.root, driver)
        ending, output = self.child_run(work, data)
        return ending, _lines_split(output)

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
    # Each word of the command is pushed, then the code and stderr replied.
    def test_run_served(self) -> None:
        ending, lines = self.serve_read(_WORDS_SCRIPT, _RUN_SHORT)
        self.assertEqual(ending, _ENDING_RETURNED)
        pushes = [_push_make(word, False) for word in _WORDS_SHORT]
        reply = {
            "0": {"t": "tap.run", "r": 1},
            "code": _DRIVER_CODE,
            "stderr": _DRIVER_ERRORS,
        }
        self.assertEqual(lines, [*pushes, reply])

    # In debug mode the pushes and the reply have full names.
    def test_run_full(self) -> None:
        self.settings_write(True)
        ending, lines = self.serve_read(_WORDS_SCRIPT, _RUN_FULL)
        self.assertEqual(ending, _ENDING_RETURNED)
        pushes = [_push_make(word, True) for word in _WORDS_FULL]
        reply = {
            "0": {"type": "tap.run", "reply": 7},
            "code": _DRIVER_CODE,
            "stderr": _DRIVER_ERRORS,
        }
        self.assertEqual(lines, [*pushes, reply])

    # A line of the driver is pushed before the driver ends.
    def test_line_streamed(self) -> None:
        go = os.path.join(self.scratch, "go")
        script = _WAIT_SCRIPT.format(seconds=_CHILD_SECONDS, path=go)
        driver = self.driver_write(script)
        work = functools.partial(_suites_serve, self.root, driver)
        child = self.child_start(work)
        os.write(child.input_fd, _RUN_SHORT)
        output = b""
        while not output.endswith(b"\r"):
            ready, _, _ = select.select(
                [child.output_fd], [], [], _CHILD_SECONDS
            )
            self.assertTrue(ready, f"no push in {_CHILD_SECONDS} s")
            output += os.read(child.output_fd, _READ_BYTES)
        self.assertEqual(_lines_split(output), [_push_make("first", False)])
        with open(go, "w", encoding="utf-8"):
            pass
        ending, rest = self.child_finish(child)
        self.assertEqual(ending, _ENDING_RETURNED)
        reply = {"0": {"t": "tap.run", "r": 1}, "code": 0, "stderr": ""}
        self.assertEqual(
            _lines_split(rest), [_push_make("second", False), reply]
        )

    # The driver's output ending inside a line fails the request it serves.
    def test_output_cut(self) -> None:
        ending, lines = self.serve_read(_CUT_SCRIPT, _RUN_SHORT)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("tap_loop_output_partial")
        self.error_check(lines, {"t": "error", "r": 1}, text)

    # A line carrying `r` is refused before dispatch, with no id answered.
    def test_reply_refused(self) -> None:
        ending, lines = self.serve_read(_WORDS_SCRIPT, _REPLY_STRAY)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("tap_loop_reply_unknown")
        self.error_check(lines, {"t": "error"}, text)

    # A type with no handler gets one `error` line with its id.
    def test_type_unknown(self) -> None:
        ending, lines = self.serve_read(_WORDS_SCRIPT, _TYPE_UNKNOWN)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("dispatch_handler_unknown")
        self.error_check(lines, {"t": "error", "r": 1}, text)

    # The input ending inside a line: an `error` line with no id.
    def test_end_partial(self) -> None:
        ending, lines = self.serve_read(_WORDS_SCRIPT, _LINE_CUT)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("tap_loop_input_partial")
        self.error_check(lines, {"t": "error"}, text)

    # A blob over `overflow_bytes` is refused before its line is served.
    def test_blob_refused(self) -> None:
        line = _blob_line(_OVERFLOW_BYTES * 2 + 1)
        ending, lines = self.serve_read(_WORDS_SCRIPT, line)
        self.assertEqual(ending, _ENDING_FAILED)
        text = _text_get("tap_loop_blob_refused")
        self.error_check(lines, {"t": "error"}, text)
