# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the echo main loop in forked children over pipes, with roots in
# `build/` whose settings are the checkout's with the gold's sizes and whose
# parameters are the run's with debug true, which a serving child sets as
# `bootstrap.py` does, and its error texts against the gold. Each child writes
# how its work ended to a file, or to stderr with the failure when that write
# fails, then kills itself whatever happened, so the handlers it registers
# never reach another test. The child opens the root's audit first, as
# `bootstrap.py` opens it in debug mode. The browser's `error` line goes to
# the real `engine_tap`, which ends the root's TAP file with a bail out, and
# the echo loop records no line of its own, so the audit holds no entry. A
# page thread's `audit.note` goes to the real `engine_audit`, which writes it
# into that same audit. With the parameter debug false the loop holds no TAP
# handler: the browser's `error` line ends it with nothing written.

import audit, echo_loop, functools, harness, json, os, signal, switches, sys
import tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_echo_loop"

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

# A reply on the engine tty, which the echo loop awaits none of.
_REPLY_STRAY = b'{"0":{"t":"echo","r":1}}\r'

# A request of a type the echo loop has no handler for.
_TYPE_UNKNOWN = b'{"0":{"t":"no.such","i":1}}\r'

# A request cut before the CR that ends its line.
_LINE_CUT = b'{"0":{"t":"echo","i":1}}'

# A `tap.line` push of the TypeScript stream.
_TAP_LINE = (
    b'{"0":{"t":"tap.line"},"language":"typescript","text":"ok 1 - x"}\r'
)

# The indent of each line of a note's body.
_NOTE_INDENT = "  "

# The text of a page thread's note.
_NOTE_TEXT = "the note of the page"

# An `audit.note` push of the page thread `ai`, as the page sends in debug.
_AUDIT_NOTE = (
    b'{"0":{"t":"audit.note"},"thread":"ai","at":1,"text":"'
    + _NOTE_TEXT.encode("utf-8")
    + b'"}\r'
)

# The TAP file of the TypeScript stream in a root.
_TAP_FILE = os.path.join("tap", "typescript.tap")

# The browser's `error` line: a message, a stack and a cause, no `r`.
_BROWSER_ERROR = (
    b'{"0":{"t":"error"},"message":"page fault","stack":"at page",'
    b'"cause":{"message":"first fault","stack":"at first"}}\r'
)

# The line that ends the root's TAP file after that line.
_BAIL_LINE = "Bail out! page fault\n"

# The directory of a root that holds the TAP files.
_TAP_DIRECTORY = "tap"


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
    return json.dumps(echo_loop.loop_prepare(root))


# Child: the root's parameters set, as `bootstrap.py` sets them, then echoes.
def _echo_serve(root: str, read_fd: int, write_fd: int) -> str:
    switches.switches_apply(switches.parameters_load(root))
    echo_loop.loop_prepare(root)
    echo_loop.loop_run(read_fd, write_fd, root)
    return _ENDING_RETURNED


# Child: opens the root's audit as `bootstrap.py` does, echoes to the end.
def _audited_serve(root: str, read_fd: int, write_fd: int) -> str:
    path = os.path.join(root, "settings.json")
    with open(path, encoding="utf-8") as file:
        values: dict[str, Any] = json.load(file)
    audit.audit_open(root, values["blob_max"], "engine")
    return _echo_serve(root, read_fd, write_fd)


# The label and body of each entry of the root's audit, in order.
def _audit_read(root: str) -> list[tuple[str, str]]:
    return [(entry.label, entry.body) for entry in audit.entries_read(root)]


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
        # The echo loop serves only a root in debug mode, whatever the run's.
        parameters = {**switches.switches_get(), "debug": True}
        switches.parameters_write(self.root, parameters)

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


# `loop_prepare`: the cache directory made, no database, no `seq`.
class TestPrepare(ScratchCase):
    # The root gains only the empty cache directory, and nothing is returned.
    def test_prepare_bare(self) -> None:
        work = functools.partial(_prepare_once, self.root)
        ending, output = self.child_run(work, b"")
        self.assertEqual(output, b"")
        self.assertIsNone(json.loads(ending))
        names = sorted(os.listdir(self.root))
        self.assertEqual(names, ["cache", "parameters.json", "settings.json"])
        self.assertEqual(os.listdir(os.path.join(self.root, "cache")), [])


# `loop_run` over pipes: the echoes, a streamed blob, refusals and the end.
class TestEcho(ScratchCase):
    # Writes the root's parameters with debug false.
    def debug_off(self) -> None:
        parameters = {**switches.switches_get(), "debug": False}
        switches.parameters_write(self.root, parameters)

    # Runs the loop on the data, returns how it ended and the lines written.
    def echo_read(self, data: bytes) -> tuple[str, list[ParsedLine]]:
        work = functools.partial(_echo_serve, self.root)
        ending, output = self.child_run(work, data)
        return ending, _lines_split(output)

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

    # Checks the one line written is an `error` line with the header given.
    def error_check(
        self, lines: list[ParsedLine], header: dict[str, Any], message: str
    ) -> None:
        ((line, blobs),) = lines
        self.assertEqual(line["0"], header)
        self.assertEqual(line["message"], message)
        self.assertEqual(blobs, [])

    # Two requests with blobs in memory each get their echo, then the end.
    def test_echo_pair(self) -> None:
        first = [b"abc", bytes(range(256))]
        second = [b"\x00\r\n"]
        data = _echo_make(1, first) + _echo_make(2, second)
        ending, lines = self.echo_read(data)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(len(lines), 2)
        self.echo_check(lines[0], 1, first)
        self.echo_check(lines[1], 2, second)

    # A blob over `overflow_bytes` streams through the cache and comes back.
    def test_echo_streamed(self) -> None:
        blob = bytes(index % 256 for index in range(_STREAMED_BYTES))
        ending, lines = self.echo_read(_echo_make(1, [blob]))
        self.assertEqual(ending, _ENDING_RETURNED)
        (parsed,) = lines
        self.echo_check(parsed, 1, [blob])
        self.assertEqual(len(os.listdir(os.path.join(self.root, "cache"))), 1)

    # A line carrying `r` is refused before dispatch, with no id answered.
    def test_reply_refused(self) -> None:
        ending, lines = self.echo_read(_REPLY_STRAY)
        self.assertEqual(ending, _ENDING_FAILED)
        message = _text_get("echo_loop_reply_unknown")
        self.error_check(lines, {"t": "error"}, message)

    # A type with no handler gets one `error` line with its id.
    def test_type_unknown(self) -> None:
        ending, lines = self.echo_read(_TYPE_UNKNOWN)
        self.assertEqual(ending, _ENDING_FAILED)
        message = _text_get("dispatch_handler_unknown")
        self.error_check(lines, {"t": "error", "r": 1}, message)

    # The input ending inside a line: an `error` line, no id, full names.
    def test_end_partial(self) -> None:
        ending, lines = self.echo_read(_LINE_CUT)
        self.assertEqual(ending, _ENDING_FAILED)
        message = _text_get("echo_loop_input_partial")
        self.error_check(lines, {"type": "error"}, message)

    # A `tap.line` push is appended as a line to its file, nothing written.
    def test_tap_line(self) -> None:
        ending, lines = self.echo_read(_TAP_LINE)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(lines, [])
        path = os.path.join(self.root, _TAP_FILE)
        with open(path, encoding="utf-8") as file:
            self.assertEqual(file.read(), "ok 1 - x\n")

    # The browser's `error` line is bailed out, then exit 1, unanswered.
    def test_browser_error(self) -> None:
        work = functools.partial(_audited_serve, self.root)
        ending, output = self.child_run(work, _BROWSER_ERROR)
        self.assertEqual(ending, _ENDING_FAILED)
        self.assertEqual(output, b"")
        path = os.path.join(self.root, _TAP_FILE)
        with open(path, encoding="utf-8") as file:
            self.assertEqual(file.read(), _BAIL_LINE)
        self.assertEqual(_audit_read(self.root), [])

    # Outside debug mode the browser's `error` is exit 1 with no TAP file.
    def test_browser_quiet(self) -> None:
        self.debug_off()
        ending, lines = self.echo_read(_BROWSER_ERROR)
        self.assertEqual(ending, _ENDING_FAILED)
        self.assertEqual(lines, [])
        self.assertFalse(
            os.path.exists(os.path.join(self.root, _TAP_DIRECTORY))
        )

    # Outside debug mode a `tap.line` is a line of no handler.
    def test_tap_unknown(self) -> None:
        self.debug_off()
        ending, lines = self.echo_read(_TAP_LINE)
        self.assertEqual(ending, _ENDING_FAILED)
        message = _text_get("dispatch_handler_unknown_tap")
        self.error_check(lines, {"t": "error"}, message)
        self.assertFalse(
            os.path.exists(os.path.join(self.root, _TAP_DIRECTORY))
        )

    # A page thread's `audit.note` is a note of the audit, nothing written.
    def test_audit_note(self) -> None:
        work = functools.partial(_audited_serve, self.root)
        ending, output = self.child_run(work, _AUDIT_NOTE)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, b"")
        note = (_text_get("audit_note_label"), _NOTE_INDENT + _NOTE_TEXT)
        self.assertEqual(_audit_read(self.root), [note])
