# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the echo main loop in forked children over pipes, with roots in
# `build/`. Each child kills itself when its work ends, so the handler it
# registers never reaches another test.

import echo_loop, functools, json, os, signal, sys, tempfile, traceback
import unittest
from collections.abc import Callable
from i18n import i18n
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The settings file of the checkout, which holds a valid settings object.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# A size chosen by its writer, small: a blob over it streams to the cache.
_OVERFLOW_BYTES = 4096

# A size chosen by its writer: the most the loop reads, so lines split.
_CHUNK_BYTES = 1000

# A size chosen by its writer: a blob that streams, over `_OVERFLOW_BYTES`.
_STREAMED_BYTES = _OVERFLOW_BYTES * 2 + 1

# A size chosen by its writer: the most the test reads from the pipe.
_READ_BYTES = 65536

# How a child ends when the loop returns at the end of its input.
_ENDING_RETURNED = "returned"

# How a child ends when the loop exits 1.
_ENDING_FAILED = "exit 1"

# The payload of each `echo` request, which its reply carries back.
_PAYLOAD: dict[str, Any] = {"text": "the payload of the test", "count": 3}

# A reply on the engine tty, which the echo loop awaits none of.
_REPLY_STRAY = b'{"0":{"t":"echo","r":1}}\r'

# How that reply is rendered in a message.
_STRAY_RENDERED = '{"0":{"t":"echo","r":1}}'

# A request of a type the echo loop has no handler for.
_TYPE_UNKNOWN = b'{"0":{"t":"no.such","i":1}}\r'

# A request cut before the CR that ends its line.
_LINE_CUT = b'{"0":{"t":"echo","i":1}}'


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
        ending = work(read_fd, write_fd)
    except SystemExit as error:
        ending = f"exit {error.code}"
    except BaseException:
        ending = traceback.format_exc()
    with open(path, "w", encoding="utf-8") as file:
        file.write(ending)
    os.kill(os.getpid(), signal.SIGKILL)


# The work of a child that prepares the root and says what it returned.
def _prepare_once(root: str, read_fd: int, write_fd: int) -> str:
    return json.dumps(echo_loop.loop_prepare(root))


# The work of a child that prepares the root and echoes the pipes to the end.
def _echo_serve(root: str, read_fd: int, write_fd: int) -> str:
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
        with open(_SETTINGS_PATH, encoding="utf-8") as file:
            values: dict[str, Any] = json.load(file)
        values["overflow_bytes"] = _OVERFLOW_BYTES
        values["chunk_bytes"] = _CHUNK_BYTES
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


# `loop_prepare`: the cache directory made, no database, no `seq`.
class TestPrepare(ScratchCase):
    # The root gains only the empty cache directory, and the map is empty.
    def test_prepare_bare(self) -> None:
        work = functools.partial(_prepare_once, self.root)
        ending, output = self.child_run(work, b"")
        self.assertEqual(output, b"")
        self.assertEqual(json.loads(ending), {})
        names = sorted(os.listdir(self.root))
        self.assertEqual(names, ["cache", "settings.json"])
        self.assertEqual(os.listdir(os.path.join(self.root, "cache")), [])


# `loop_run` over pipes: the echoes, a streamed blob, refusals and the end.
class TestEcho(ScratchCase):
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
        message = i18n("echo_loop.reply_unknown", _STRAY_RENDERED)
        self.error_check(lines, {"t": "error"}, message)

    # A type with no handler gets one `error` line with its id.
    def test_type_unknown(self) -> None:
        ending, lines = self.echo_read(_TYPE_UNKNOWN)
        self.assertEqual(ending, _ENDING_FAILED)
        message = i18n("dispatch.handler_unknown", "no.such", 0)
        self.error_check(lines, {"t": "error", "r": 1}, message)

    # The end of the input inside a line is an `error` line with no id.
    def test_end_partial(self) -> None:
        ending, lines = self.echo_read(_LINE_CUT)
        self.assertEqual(ending, _ENDING_FAILED)
        message = i18n("echo_loop.input_partial")
        self.error_check(lines, {"t": "error"}, message)
