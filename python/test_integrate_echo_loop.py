# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the echo main loop joined to everything it calls into, in forked
# children over pipes, with roots in `build/` whose settings are the
# checkout's with the gold's sizes. One input holds `echo` requests, one with
# a blob over overflow_bytes, and `tap.line` pushes between them, served in
# turn through the real `dispatch`, the real codec of `jslb`, the settings
# the real `settings` reads, and the real `engine_tap`, which appends to the
# root's TAP file and logs in the root's log of the real `verbose`, opened
# first by the child as `bootstrap.py` opens it. The input ends with the
# browser's `error` line or with a line of no handler, after the echoes are
# written. The output is read from the pipe, and the TAP file, the log and
# the cache from the root. Each child writes how its work ended to a file,
# or to stderr with the failure when that write fails, then kills itself
# whatever happened, so the handlers it registers never reach another test.

import contextlib, echo_loop, functools, harness, json, os, signal, sqlite3
import sys, tempfile, traceback, unittest, verbose
from collections.abc import Callable
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_echo_loop"

# A size chosen by its writer, small: a blob over it streams to the cache.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# A size chosen by its writer: the most the loop reads, so lines split.
_CHUNK_BYTES: int = harness.gold_get(f"{_GOLD_ID}.chunk_bytes")

# A blob that streams, over `_OVERFLOW_BYTES`.
_STREAMED_BYTES = _OVERFLOW_BYTES * 2 + 1

# A size chosen by its writer: the most the test reads from the pipe.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# How a child ends when the loop returns at the end of its input.
_ENDING_RETURNED = "returned"

# How a child ends when the loop exits 1.
_ENDING_FAILED = "exit 1"

# The payload of each `echo` request, which its reply carries back.
_PAYLOAD: dict[str, Any] = {"text": "the payload of the test", "count": 3}

# A request of a type the echo loop has no handler for.
_TYPE_UNKNOWN = b'{"0":{"t":"no.such","i":3}}\r'

# The browser's `error` line: a message, a stack and a cause, no `r`.
_BROWSER_ERROR = (
    b'{"0":{"t":"error"},"message":"page fault","stack":"at page",'
    b'"cause":{"message":"first fault","stack":"at first"}}\r'
)

# The line that ends the root's TAP file after that line.
_BAIL_LINE = "Bail out! page fault"

# The TAP file of the TypeScript stream in a root.
_TAP_FILE = os.path.join("tap", "typescript.tap")

# The directory in a root that holds the blobs over `overflow_bytes`.
_CACHE_DIRECTORY = "cache"

# The log of the server in a root, as `verbose` names it.
_LOG_NAME = "_verbose.sqlite"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# A line's JSON object and the bytes of each of its blobs.
class ParsedLine(NamedTuple):
    line: dict[str, Any]
    blobs: list[bytes]


# The bytes of an `echo` request with the id, the payload and the blobs.
def _echo_make(request_id: int, blobs: list[bytes]) -> bytes:
    header = {"t": "echo", "i": request_id, "b": len(blobs)}
    line: dict[str, Any] = {"0": header}
    for index, blob in enumerate(blobs, 1):
        line[str(index)] = {"s": len(blob)}
    line.update(_PAYLOAD)
    text = json.dumps(line, separators=(",", ":"))
    return text.encode("utf-8") + b"\r" + b"".join(blobs)


# The bytes of a `tap.line` push of the TypeScript stream.
def _tap_make(text: str) -> bytes:
    line = {"0": {"t": "tap.line"}, "language": "typescript", "text": text}
    return json.dumps(line, separators=(",", ":")).encode("utf-8") + b"\r"


# Splits output into its lines, each with the bytes of its blobs.
def _lines_split(output: bytes) -> list[ParsedLine]:
    lines: list[ParsedLine] = []
    rest = output
    while rest:
        text, rest = rest.split(b"\r", 1)
        line: dict[str, Any] = json.loads(text)
        blobs: list[bytes] = []
        for index in range(1, line["0"].get("b", 0) + 1):
            size: int = line[str(index)]["s"]
            blobs.append(rest[:size])
            rest = rest[size:]
        lines.append(ParsedLine(line, blobs))
    return lines


# Reads a pipe to its end and closes it.
def _pipe_drain(fd: int) -> bytes:
    data = bytearray()
    while chunk := os.read(fd, _READ_BYTES):
        data += chunk
    os.close(fd)
    return bytes(data)


# The thread and text of each line of the root's log, in order.
def _log_read(root: str) -> list[tuple[str, str]]:
    path = os.path.join(root, _LOG_NAME)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        cursor = connection.execute(_LOG_QUERY)
        rows: list[tuple[str, str]] = cursor.fetchall()
    return rows


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


# Child: opens the log as `bootstrap.py` does, prepares the root, serves pipes.
def _session_serve(root: str, read_fd: int, write_fd: int) -> str:
    path = os.path.join(root, "settings.json")
    with open(path, encoding="utf-8") as file:
        values: dict[str, Any] = json.load(file)
    verbose.log_open(root, values["verbose_ring"])
    echo_loop.loop_prepare(root)
    echo_loop.loop_run(read_fd, write_fd, root)
    return _ENDING_RETURNED


# Gives each test a scratch root in `build/` whose settings stream small.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the root with the changed settings.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)
        values = harness.settings_copy()
        values["overflow_bytes"] = _OVERFLOW_BYTES
        values["chunk_bytes"] = _CHUNK_BYTES
        path = os.path.join(self.root, "settings.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(values, file)

    # Serves the data in a child, returns its ending and the lines written.
    def session_run(self, data: bytes) -> tuple[str, list[ParsedLine]]:
        input_read, input_write = os.pipe()
        output_read, output_write = os.pipe()
        path = os.path.join(self.scratch, "ending.txt")
        work = functools.partial(_session_serve, self.root)
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(input_write)
            os.close(output_read)
            _child_end(work, input_read, output_write, path)
        os.close(input_read)
        os.close(output_write)
        view = memoryview(data)
        while view:
            view = view[os.write(input_write, view) :]
        os.close(input_write)
        output = _pipe_drain(output_read)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(path)
        return ending, _lines_split(output)

    # The text of the root's TAP file.
    def tap_read(self) -> str:
        path = os.path.join(self.root, _TAP_FILE)
        with open(path, encoding="utf-8") as file:
            return file.read()

    # Checks a reply carries the request's id, payload and blob bytes.
    def echo_check(
        self, parsed: ParsedLine, request_id: int, expected: list[bytes]
    ) -> None:
        line, blobs = parsed
        header = {"t": "echo", "r": request_id, "b": len(expected)}
        sizes = {
            str(index): {"s": len(blob)}
            for index, blob in enumerate(expected, 1)
        }
        self.assertEqual(line, {"0": header, **sizes, **_PAYLOAD})
        self.assertEqual(blobs, expected)


# Sessions served by the loop and every module it calls into.
class TestSession(ScratchCase):
    # Echo, push, fail: echoes out, pushes, bail in TAP, logged, blob cached.
    def test_session_served(self) -> None:
        first = [b"abc", bytes(range(256))]
        streamed = [bytes(index % 256 for index in range(_STREAMED_BYTES))]
        pushed = ["ok 1 - first", "ok 2 - second"]
        data = b"".join(
            [
                _echo_make(1, first),
                _tap_make(pushed[0]),
                _echo_make(2, streamed),
                _tap_make(pushed[1]),
                _BROWSER_ERROR,
            ]
        )
        ending, lines = self.session_run(data)
        self.assertEqual(ending, _ENDING_FAILED)
        self.assertEqual(len(lines), 2)
        self.echo_check(lines[0], 1, first)
        self.echo_check(lines[1], 2, streamed)
        tap = "".join(text + "\n" for text in [*pushed, _BAIL_LINE])
        self.assertEqual(self.tap_read(), tap)
        texts = [
            _text_get("engine_tap_browser_failed"),
            "at page",
            _text_get("engine_tap_browser_cause"),
            "at first",
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)
        cache = os.path.join(self.root, _CACHE_DIRECTORY)
        self.assertEqual(len(os.listdir(cache)), 1)

    # Echo, push, unhandled: echo out, `error` by id, push only in TAP, no log.
    def test_session_failed(self) -> None:
        first = [b"abc"]
        pushed = "ok 1 - first"
        data = _echo_make(1, first) + _tap_make(pushed) + _TYPE_UNKNOWN
        ending, lines = self.session_run(data)
        self.assertEqual(ending, _ENDING_FAILED)
        self.assertEqual(len(lines), 2)
        self.echo_check(lines[0], 1, first)
        error, blobs = lines[1]
        self.assertEqual(error["0"], {"t": "error", "r": 3})
        message = _text_get("dispatch_handler_unknown")
        self.assertEqual(error["message"], message)
        self.assertEqual(blobs, [])
        self.assertEqual(self.tap_read(), pushed + "\n")
        self.assertEqual(_log_read(self.root), [])
