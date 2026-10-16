#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The wire test: starts Linux ttyd, from a checkout of ttyd beside this
# project, serving bootstrap.html and running a copy of bootstrap.py made
# in a directory under build/, then types commands to the program through
# ttyd's protocol as the page does, rung by rung: over one WebSocket, then
# over new ones on the same ttyd, two at once, and last one while ttyd is
# killed. The program runs on ttyd's terminal, which echoes what is typed,
# so a check compares what the terminal shows, echo included, byte for
# byte wherever that is deterministic, and waits for the output it expects
# before typing more. ttyd's log is copied to stderr whole. It stops at the
# first failed check with the measurement that failed and exits 1; on
# success it prints one line per rung and exits 0. Standard library only,
# and ttyd is the one program it starts:
#
#     python3 python/test_wire.py

import argparse, base64, contextlib, hashlib, http.client, json, os, re, select
import shlex, shutil, signal, socket, subprocess, sys, tempfile, time, types
from collections.abc import Callable, Generator
from typing import Any, NamedTuple, cast

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

_BOOTSTRAP_PATH = os.path.join(_PYTHON_PATH, "bootstrap.py")

# The banner as the terminal shows it, then the prompt.
_BANNER_PATTERN = re.compile(
    rb"bootstrap (.+) sha256 ([0-9a-f]{64}) pid (\d+) python (\S+)"
    rb" modules (.+)\r\n\$ "
)

# 1 MiB in lines of `_LINE_BYTES` bytes and a newline: units, then ASCII.
_BIG_LINES = 256

# A unit: 23 random ASCII characters, then characters of 2, 3 and 4 bytes.
_BIG_ASCII_PER_UNIT = 23
_BIG_WIDE_TEXT = "\u00e9\u4e2d\U0001f600"

# Where the copy of bootstrap.py and its modules go, in a directory each run.
_BUILD_PATH = os.path.join(os.path.dirname(_PYTHON_PATH), "build")

# The terminal size the first message gives.
_COLUMNS = 80
_ROWS = 24

_CREDENTIAL = "user:pass"

# What the terminal takes, at the start of a line, as the end of input.
_EOF = b"\x04"

# Commands the bootstrapper refuses, each with the line it writes to stderr.
_ERRORS = [
    ("nosuch", "nosuch: not found"),
    ("not-a-name", "not-a-name: not a module name"),
    ("'unclosed", "'unclosed: No closing quotation"),
    ("put", "usage: put NAME"),
    ("put one two", "usage: put NAME"),
    ("ls extra", "usage: ls"),
    ("restart now", "usage: restart"),
]

# A module that exits with the code its argument gives.
_EXITER_SOURCE = "import sys\n\nsys.exit(int(sys.argv[1]))\n"

_INDEX_PATH = os.path.join(_PYTHON_PATH, "bootstrap.html")

# `^C`, and how the terminal echoes it.
_INTERRUPT = b"\x03"
_INTERRUPT_ECHO = b"^C"

# The most bytes a terminal line holds before its newline.
_LINE_BYTES = 4095

# The lines lines.py prints, 1 to this.
_LINES_COUNT = 100000
_LINES_SOURCE = f"for n in range(1, {_LINES_COUNT} + 1):\n    print(n)\n"

_LISTENING_PATTERN = re.compile(r" Listening on port: (\d+)$")

_MADE_UP_PATH = "/other.js"

# Holds 2, 3 and 4 byte characters, and the split lands inside the last.
_NON_ASCII_TEXT = "na\u00efve \u65e5\u672c\u8a9e \U0001f600 \u00e9t\u00e9"
_NON_ASCII_SPLIT_CHARACTER = "\U0001f600"

_POLL_SECONDS = 0.05

# What the bootstrapper writes when it waits for a command.
_PROMPT = b"$ "

# A module that raises, so the interpreter's own exit reports it.
_RAISER_SOURCE = f"raise ValueError({_NON_ASCII_TEXT!r})\n"

# A module that prints what it was given and where it runs.
_REPORT_SOURCE = f"""\
import os, sys

TEXT = {_NON_ASCII_TEXT!r}

print("argv", sys.argv[1:])
print("text", TEXT)
print("cwd", os.getcwd())
print("path", sys.path[0])
print("bootstrap", os.environ["XSJS_BOOTSTRAP"])
print("modules", os.environ["XSJS_MODULES"])
print("name", __name__)
print("stderr", TEXT, file=sys.stderr)
"""

# The arguments report.py runs with.
_RUN_ARGS = ["--who", "two words", _NON_ASCII_TEXT]

_RUN_TIMEOUT_SECONDS = 120

# The bytes shown on each side of where a transcript first differs.
_SHOWN_BYTES = 200

# A module that forks a second process, and both sleep until killed.
_SLEEPER_SOURCE = """\
import os, time

child = os.fork()
if child == 0:
    time.sleep(600)
    os._exit(0)
print("pids", os.getpid(), child)
time.sleep(600)
"""

# A module that says its pids, then prints each line of stdin until EOF.
_STDIN_SOURCE = """\
import os, sys

print("ready", os.getpid(), os.getppid())
count = 0
for line in sys.stdin:
    count += 1
    print("got", line, end="")
print("eof", count)
"""

_STOP_WAIT_SECONDS = 5

_TTYD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(_PYTHON_PATH)), "ttyd", "build", "ttyd"
)

# `--terminal-type dumb`, as deployed, so Python doesn't colour tracebacks.
_TTYD_OPTIONS = [
    "--writable",
    "--check-origin",
    "--terminal-type",
    "dumb",
    "--index",
    _INDEX_PATH,
]

# What update.py appends to the bootstrapper it runs under.
_UPDATE_LINE = b"# updated by update.py\n"
_UPDATE_SOURCE = f"""\
import hashlib, os

path = os.environ["XSJS_BOOTSTRAP"]
with open(path, "rb") as old_file:
    data = old_file.read() + {_UPDATE_LINE!r}
with open(path + ".new", "wb") as new_file:
    new_file.write(data)
os.replace(path + ".new", path)
print("sha256", hashlib.sha256(data).hexdigest())
"""

# ttyd's first log line, with its version and that of libwebsockets.
_VERSION_PATTERN = re.compile(r" N: (ttyd \S+ \(libwebsockets \S+\))$")

_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_WEBSOCKET_OPCODE_BINARY = 0x2
_WEBSOCKET_OPCODE_CLOSE = 0x8
_WEBSOCKET_OPCODE_CONTINUATION = 0x0
_WEBSOCKET_OPCODE_PING = 0x9
_WEBSOCKET_OPCODE_PONG = 0xA
_WEBSOCKET_CLOSE_NORMAL = 1000


# The bootstrapper's banner: its pid, its Python's version and its sha256.
class Banner(NamedTuple):
    pid: int
    python: str
    sha256: str


class CheckFailed(Exception):
    pass


class Ttyd:
    # Starts ttyd in a session of its own with its stderr on a pipe.
    def __init__(
        self, options: list[str], command: list[str], deadline: float
    ) -> None:
        self.command = command
        # The path, until ttyd's log names its version.
        self.version = _TTYD_PATH
        self.deadline = deadline
        # ttyd's stderr lines so far, and what follows the last of them.
        self.lines: list[str] = []
        self.partial = b""
        self.port = 0
        self.killed = False
        self.stderr_ended = False
        self.fd, write_fd = os.pipe()
        try:
            # In a session of its own, so a `^C` reaches only this script.
            self.process = subprocess.Popen(
                [
                    _TTYD_PATH,
                    "--port",
                    "0",
                    "--interface",
                    "127.0.0.1",
                    *options,
                    *command,
                ],
                stdin=subprocess.DEVNULL,
                stdout=sys.stderr,
                stderr=write_fd,
                start_new_session=True,
            )
        finally:
            os.close(write_fd)

    # Sends ttyd the signal, after which its exit is awaited, not failed.
    def kill(self, signal_number: int) -> None:
        self.killed = True
        os.kill(self.process.pid, signal_number)

    # Copies whole lines to this script's stderr and keeps them.
    def lines_take(self, data: bytes) -> None:
        *complete, self.partial = (self.partial + data).split(b"\n")
        for line in complete:
            text = line.decode()
            self.lines.append(text)
            sys.stderr.write(f"{text}\n")
        sys.stderr.flush()

    # Returns the first match from the start'th line on, reading stderr for it.
    def line_wait(
        self, pattern: re.Pattern[str], start: int, what: str
    ) -> re.Match[str]:
        index = start
        while True:
            while index < len(self.lines):
                found = pattern.search(self.lines[index])
                if found:
                    return found
                index += 1
            readable, _, _ = select.select(
                [self.fd], [], [], remaining(self.deadline, what)
            )
            if readable:
                self.stderr_read()

    # Reads ttyd's stderr, failing on its end unless ttyd was killed.
    def stderr_read(self) -> None:
        data = os.read(self.fd, 1 << 16)
        if not data:
            if not self.killed:
                raise CheckFailed(
                    f"{self.version} exited with {self.process.wait()}"
                )
            self.stderr_ended = True
            return
        self.lines_take(data)

    # Stops ttyd and its session, then copies out the rest of its stderr.
    def stop(self) -> None:
        # Until ttyd is waited for, its pid names its session and no other.
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
        try:
            self.process.wait(_STOP_WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait()
        while data := os.read(self.fd, 1 << 16):
            self.lines_take(data)
        os.close(self.fd)
        if self.partial:
            sys.stderr.write(f"{self.partial.decode()}\n")
            sys.stderr.flush()


class Wire:
    # Takes the socket after the upgrade and handles any frames already read.
    def __init__(self, ttyd: Ttyd, sock: socket.socket, rest: bytes) -> None:
        self.ttyd = ttyd
        self.sock = sock
        # It never waits, as it is used only once `select` finds it ready.
        self.sock.setblocking(False)
        # What ttyd sent that isn't yet a whole frame.
        self.unread = bytearray(rest)
        # The frames so far of a message ttyd sends in more than one.
        self.fragments: bytearray | None = None
        # The frames queued that the socket hasn't yet taken.
        self.unsent = bytearray()
        self.close_sent = False
        self.close_code: int | None = None
        self.close_reason = b""
        # Set before ttyd is made to end the connection, so it is not failed.
        self.end_expected = False
        # Set once ttyd's end of the TCP connection is read.
        self.ended = False
        self.ttyd_messages = 0
        self.ttyd_pings = 0
        self.title = ""
        self.preferences: dict[str, Any] = {}
        # What the terminal showed, echo included, as ttyd relays it.
        self.output = bytearray()
        # The banners so far, the first and then one each restart.
        self.banners: list[Banner] = []
        # The pids that modules said they run as.
        self.module_pids: set[int] = set()
        self.frames_handle()

    # Queues a close frame with the normal code.
    def close_send(self) -> None:
        self.close_sent = True
        self.frame_send(
            _WEBSOCKET_OPCODE_CLOSE, _WEBSOCKET_CLOSE_NORMAL.to_bytes(2, "big")
        )

    # Sends the input, then returns the mark before it once the prompt shows.
    def command(self, data: bytes) -> int:
        mark = len(self.output)
        self.input_send(data)
        self.prompt_wait(mark, f"the prompt after {data[:40]!r}")
        return mark

    # Sends the input and fails unless the output to the prompt is expected.
    def command_check(self, data: bytes, expected: bytes) -> None:
        mark = self.command(data)
        self.transcript_check(mark, expected, f"{data[:40]!r}'s output")

    # Queues one WebSocket frame, masked as a client's must be.
    def frame_send(
        self, opcode: int, payload: bytes, final: bool = True
    ) -> None:
        head = bytearray([(0x80 if final else 0) | opcode])
        if len(payload) < 126:
            head.append(0x80 | len(payload))
        elif len(payload) < 1 << 16:
            head.append(0x80 | 126)
            head += len(payload).to_bytes(2, "big")
        else:
            head.append(0x80 | 127)
            head += len(payload).to_bytes(8, "big")
        mask = os.urandom(4)
        keys = (mask * (len(payload) // 4 + 1))[: len(payload)]
        masked = (
            int.from_bytes(payload, "big") ^ int.from_bytes(keys, "big")
        ).to_bytes(len(payload), "big")
        self.unsent += head + mask + masked

    # Handles each whole frame that has been read.
    def frames_handle(self) -> None:
        version = self.ttyd.version
        while len(self.unread) >= 2:
            first, second = self.unread[0], self.unread[1]
            if second & 0x80:
                raise CheckFailed(f"{version} sent a masked frame")
            length = second & 0x7F
            start = 2
            if length == 126:
                start = 4
            elif length == 127:
                start = 10
            if len(self.unread) < start:
                return
            if start > 2:
                length = int.from_bytes(self.unread[2:start], "big")
            if len(self.unread) < start + length:
                return
            payload = bytes(self.unread[start : start + length])
            del self.unread[: start + length]
            opcode = first & 0x0F
            if opcode == _WEBSOCKET_OPCODE_PING:
                self.ttyd_pings += 1
                self.frame_send(_WEBSOCKET_OPCODE_PONG, payload)
            elif opcode == _WEBSOCKET_OPCODE_CLOSE:
                if len(payload) < 2:
                    raise CheckFailed(f"{version} closed with no code")
                self.close_code = int.from_bytes(payload[:2], "big")
                self.close_reason = payload[2:]
                if not self.close_sent and not self.end_expected:
                    raise CheckFailed(
                        f"{version} closed the connection with"
                        f" {self.close_code}, reason {self.close_reason!r}"
                    )
            elif opcode == _WEBSOCKET_OPCODE_BINARY and self.fragments is None:
                self.fragments = bytearray(payload)
            elif (
                opcode == _WEBSOCKET_OPCODE_CONTINUATION
                and self.fragments is not None
            ):
                self.fragments += payload
            else:
                raise CheckFailed(
                    f"{version} sent a frame of opcode {opcode} out of turn"
                )
            if opcode in (
                _WEBSOCKET_OPCODE_BINARY,
                _WEBSOCKET_OPCODE_CONTINUATION,
            ) and (first & 0x80):
                message = bytes(cast(bytearray, self.fragments))
                self.fragments = None
                self.ttyd_message_handle(message)

    # Queues one line of the input a ttyd message.
    def input_lines_send(self, data: bytes) -> None:
        for line in data.splitlines(keepends=True):
            self.input_send(line)

    # Queues the input to the terminal as one ttyd message.
    def input_send(self, data: bytes) -> None:
        self.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + data)

    # Queues the input split by `split_offset` in two messages or two frames.
    def input_split_send(self, data: bytes, frames: bool) -> None:
        split = split_offset(data)
        if frames:
            self.frame_send(
                _WEBSOCKET_OPCODE_BINARY, b"0" + data[:split], False
            )
            self.frame_send(_WEBSOCKET_OPCODE_CONTINUATION, data[split:])
        else:
            self.input_send(data[:split])
            self.input_send(data[split:])

    # Answers whether the output from the mark on holds that many lines.
    def lines_after(self, mark: int, count: int) -> bool:
        return self.output.count(b"\r\n", mark) >= count

    # Waits for as many lines as expected, then fails unless they are it.
    def lines_check(self, mark: int, expected: bytes, what: str) -> None:
        count = expected.count(b"\r\n")
        self.wait(lambda: self.lines_after(mark, count), what)
        self.transcript_check(mark, expected, what)

    # Answers whether the output from the mark on ends with the prompt.
    def prompt_after(self, mark: int) -> bool:
        after = len(self.output) - mark
        return after >= len(_PROMPT) and self.output.endswith(_PROMPT)

    # Waits until the output from the mark on ends with the prompt.
    def prompt_wait(self, mark: int, what: str) -> None:
        self.wait(lambda: self.prompt_after(mark), what)

    # Reads from ttyd and handles its frames, failing on an unexpected drop.
    def socket_read(self) -> None:
        data = self.sock.recv(1 << 20)
        if not data:
            if self.close_code is None and not self.end_expected:
                raise CheckFailed(
                    f"{self.ttyd.version} dropped the connection with no"
                    " close frame"
                )
            self.ended = True
            return
        self.unread += data
        self.frames_handle()

    # Queues the first message, which starts the program, with ttyd's token.
    def start_send(self) -> None:
        status, body = http_get(self.ttyd, "/token", {})
        if status != 200:
            raise CheckFailed(f"GET /token answered {status}")
        token = json.loads(body)["token"]
        self.frame_send(
            _WEBSOCKET_OPCODE_BINARY,
            json.dumps(
                {"AuthToken": token, "columns": _COLUMNS, "rows": _ROWS}
            ).encode(),
        )

    # Fails unless the output from the mark on is expected, showing where not.
    def transcript_check(self, mark: int, expected: bytes, what: str) -> None:
        shown = bytes(self.output[mark:])
        if shown == expected:
            return
        at = next(
            (
                index
                for index, (one, other) in enumerate(zip(shown, expected))
                if one != other
            ),
            min(len(shown), len(expected)),
        )
        start = max(0, at - _SHOWN_BYTES)
        end = at + _SHOWN_BYTES
        raise CheckFailed(
            f"{what} through {self.ttyd.version} is {len(shown)} bytes where"
            f" {len(expected)} were due, unequal from byte {at}:"
            f" {shown[start:end]!r} where {expected[start:end]!r} was due"
        )

    # Handles one ttyd message: the title, the preferences, then output.
    def ttyd_message_handle(self, message: bytes) -> None:
        self.ttyd_messages += 1
        kind = message[:1]
        expected = (
            b"1"
            if self.ttyd_messages == 1
            else b"2"
            if self.ttyd_messages == 2
            else b"0"
        )
        if kind != expected:
            raise CheckFailed(
                f"{self.ttyd.version}'s message {self.ttyd_messages} is type"
                f" {kind!r}, not {expected!r}: {message[:60]!r}"
            )
        if kind == b"1":
            self.title = message[1:].decode()
        elif kind == b"2":
            try:
                preferences: object = json.loads(message[1:])
            except json.JSONDecodeError as error:
                raise CheckFailed(
                    f"{self.ttyd.version}'s preferences aren't JSON: {error}:"
                    f" {message!r}"
                ) from error
            if type(preferences) is not dict:
                raise CheckFailed(
                    f"{self.ttyd.version}'s preferences aren't an object:"
                    f" {message!r}"
                )
            self.preferences = cast(dict[str, Any], preferences)
        else:
            self.output += message[1:]

    # Sends as much of the queued frames as the socket takes.
    def unsent_send(self) -> None:
        sent = self.sock.send(self.unsent)
        del self.unsent[:sent]

    # Sends what is queued and handles what ttyd sends until done answers True.
    def wait(self, done: Callable[[], bool], what: str) -> None:
        wires_wait([self], done, what)


# Fails unless the text is the banner of ttyd's command, then the prompt.
def banner_check(wire: Wire, text: bytes) -> Banner:
    found = _BANNER_PATTERN.fullmatch(text)
    if found is None:
        raise CheckFailed(
            f"the program showed {text!r} through {wire.ttyd.version} where"
            " its banner and the prompt were due"
        )
    path, digest, pid, python, modules = (
        group.decode() for group in found.groups()
    )
    command = wire.ttyd.command
    with open(command[1], "rb") as bootstrap_file:
        file_digest = hashlib.sha256(bootstrap_file.read()).hexdigest()
    for name, value, expected in (
        ("path", path, command[1]),
        ("sha256", digest, file_digest),
        ("modules", modules, command[2]),
    ):
        if value != expected:
            raise CheckFailed(
                f"the banner's {name} is {value}, not {expected}"
            )
    program_check(wire.ttyd, int(pid))
    banner = Banner(int(pid), python, digest)
    wire.banners.append(banner)
    return banner


# Returns lines of `_LINE_BYTES` bytes of random ASCII and of wide characters.
def big_text() -> str:
    unit_bytes = _BIG_ASCII_PER_UNIT + len(_BIG_WIDE_TEXT.encode())
    units, rest = divmod(_LINE_BYTES, unit_bytes)
    lines: list[str] = []
    for _ in range(_BIG_LINES):
        ascii_text = base64.b64encode(os.urandom(_LINE_BYTES)).decode()
        line = "".join(
            ascii_text[index : index + _BIG_ASCII_PER_UNIT] + _BIG_WIDE_TEXT
            for index in range(
                0, units * _BIG_ASCII_PER_UNIT, _BIG_ASCII_PER_UNIT
            )
        )
        tail = units * _BIG_ASCII_PER_UNIT
        lines.append(f"{line}{ascii_text[tail : tail + rest]}\n")
    return "".join(lines)


# Describes how ttyd ended the connection, with a close frame or without.
def connection_end(wire: Wire) -> str:
    if wire.close_code is None:
        return (
            "the TCP connection ended with no close frame, which a browser"
            " reports as 1006"
        )
    return (
        f"a close frame of code {wire.close_code}, reason"
        f" {wire.close_reason!r}, came and the TCP connection ended"
    )


# Fails unless the module's file holds the data.
def file_check(wire: Wire, name: str, data: bytes) -> None:
    path = os.path.join(wire.ttyd.command[2], f"{name}.py")
    with open(path, "rb") as module_file:
        on_disk = module_file.read()
    if on_disk != data:
        raise CheckFailed(
            f"{path} has {len(on_disk)} bytes, sha256"
            f" {hashlib.sha256(on_disk).hexdigest()}, where {len(data)} bytes,"
            f" sha256 {hashlib.sha256(data).hexdigest()}, were put"
        )


# Returns ttyd's status and body for a GET of the path.
def http_get(
    ttyd: Ttyd, path: str, headers: dict[str, str]
) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection(
        "127.0.0.1", ttyd.port, timeout=remaining(ttyd.deadline, f"GET {path}")
    )
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


# Runs the module and returns the two numbers of its first line.
def module_ready(wire: Wire, name: str, word: str) -> tuple[int, int]:
    mark = len(wire.output)
    wire.input_send(f"{name}\n".encode())
    wire.wait(lambda: wire.lines_after(mark, 2), f"{name}'s first line")
    return ready_parse(wire, mark, name, word)


# Returns what `ls` lists for the directory, from its files as they are.
def modules_listing(modules: str) -> str:
    lines: list[str] = []
    for name in sorted(os.listdir(modules)):
        with open(os.path.join(modules, name), "rb") as module_file:
            data = module_file.read()
        digest = hashlib.sha256(data).hexdigest()
        lines.append(f"{len(data)} {digest} {name}\n")
    return "".join(lines)


# Returns the text as the terminal shows it: `UTF-8`, newlines as `\r\n`.
def on_terminal(text: str) -> bytes:
    return text.encode().replace(b"\n", b"\r\n")


# Returns the number of the process's parent.
def process_parent(pid: int) -> int:
    with open(f"/proc/{pid}/stat", "rb") as stat_file:
        stat = stat_file.read()
    # After the name in brackets: state, ppid.
    return int(stat[stat.rindex(b")") + 2 :].split()[1])


# Returns the sorted pids watched, in the session or children of the parent.
def processes_left(watched: set[int], session: int, parent: int) -> list[int]:
    left: list[int] = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/stat", "rb") as stat_file:
                stat = stat_file.read()
        except (FileNotFoundError, ProcessLookupError):
            # It ended between the listing and the reading.
            continue
        # After the name in brackets: state, ppid, pgrp, session.
        fields = stat[stat.rindex(b")") + 2 :].split()
        pid = int(name)
        if (
            pid in watched
            or int(fields[3]) == session
            or int(fields[1]) == parent
        ):
            left.append(pid)
    return sorted(left)


# Waits until the processes are gone. Returns the seconds since the start.
def processes_wait(
    wire: Wire, watched: set[int], session: int, parent: int, start: float
) -> float:
    while left := processes_left(watched, session, parent):
        remaining(wire.ttyd.deadline, f"processes {left} to end")
        time.sleep(_POLL_SECONDS)
    return time.monotonic() - start


# Waits for ttyd's log of the end of the program of that pid.
def program_end_wait(ttyd: Ttyd, pid: int) -> re.Match[str]:
    ended = (
        rf"process (killed with signal|exited with code) (\d+), pid: {pid}$"
    )
    return ttyd.line_wait(
        re.compile(ended), 0, "ttyd's log of the program's end"
    )


# Fails unless the pid is ttyd's child running its command.
def program_check(ttyd: Ttyd, pid: int) -> None:
    with open(f"/proc/{pid}/cmdline", "rb") as cmdline_file:
        cmdline = cmdline_file.read().split(b"\0")[:-1]
    if cmdline != [argument.encode() for argument in ttyd.command]:
        raise CheckFailed(f"the banner's pid {pid} runs {cmdline}")
    parent = process_parent(pid)
    if parent != ttyd.process.pid:
        raise CheckFailed(
            f"the banner's pid {pid} is the child of {parent}, not of"
            f" ttyd's {ttyd.process.pid}"
        )


# Returns the input that puts the source as the module, then ends input.
def put_input(name: str, source: str) -> bytes:
    return f"put {name}\n{source}".encode() + _EOF


# Puts the module via send, checks echo, saved line and file. Returns sha256.
def put_check(
    wire: Wire, name: str, source: str, send: Callable[[bytes], None]
) -> str:
    data = source.encode()
    digest = hashlib.sha256(data).hexdigest()
    mark = len(wire.output)
    send(put_input(name, source))
    wire.prompt_wait(mark, f"put {name}'s saved line")
    saved = f"saved {name}.py {len(data)} bytes sha256 {digest}\n"
    wire.transcript_check(
        mark,
        on_terminal(f"put {name}\n{source}{saved}") + _PROMPT,
        f"put {name}",
    )
    file_check(wire, name, data)
    return digest


# Fails unless the output from the mark on is the echo and the first line.
def ready_parse(
    wire: Wire, mark: int, name: str, word: str
) -> tuple[int, int]:
    shown = bytes(wire.output[mark:])
    found = re.fullmatch(
        re.escape(on_terminal(f"{name}\n{word} ")) + rb"(\d+) (\d+)\r\n",
        shown,
    )
    if found is None:
        raise CheckFailed(
            f"{name} showed {shown!r} where its echo and a line of {word}"
            f" and two numbers were due, through {wire.ttyd.version}"
        )
    wire.module_pids.add(int(found.group(1)))
    return int(found.group(1)), int(found.group(2))


# Returns the seconds left before the overall timeout, failing once past.
def remaining(deadline: float, what: str) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise CheckFailed(
            f"gave up after {_RUN_TIMEOUT_SECONDS} s waiting for {what}"
        )
    return left


# Runs report.py with the arguments and checks it all. Returns its command.
def report_check(wire: Wire, args: list[str]) -> str:
    line = shlex.join(["report", *args])
    bootstrap_path, modules = wire.ttyd.command[1:]
    shown = [
        line,
        f"argv {args}",
        f"text {_NON_ASCII_TEXT}",
        f"cwd {modules}",
        f"path {modules}",
        f"bootstrap {bootstrap_path}",
        f"modules {modules}",
        "name __main__",
        f"stderr {_NON_ASCII_TEXT}",
    ]
    wire.command_check(
        f"{line}\n".encode(),
        on_terminal("".join(f"{text}\n" for text in shown)) + _PROMPT,
    )
    return line


# Checks `^C` at the prompt and in a put abandons it. Returns a summary.
def rung_abandon(wire: Wire) -> str:
    abandoned = _INTERRUPT_ECHO + on_terminal("\n") + _PROMPT
    mark = wire.command(b"ls\n")
    listed = bytes(wire.output[mark:])
    wire.command_check(_INTERRUPT, abandoned)
    for line in ("put abandoned\n", "print(1)\n"):
        mark = len(wire.output)
        wire.input_send(line.encode())
        wire.lines_check(mark, on_terminal(line), f"the echo of {line!r}")
    wire.command_check(_INTERRUPT, abandoned)
    wire.command_check(b"ls\n", listed)
    path = os.path.join(wire.ttyd.command[2], "abandoned.py")
    if os.path.lexists(path):
        raise CheckFailed(f"{path} exists after its put was abandoned")
    # The lines after the echo of `ls`.
    files = listed.count(b"\r\n") - 1
    return (
        f"^C at the prompt showed {abandoned!r}; put abandoned and a line,"
        f" each echoed, then ^C showed the same; ls unchanged, listing"
        f" {files} files, none of them abandoned.py"
    )


# Starts the program and checks the title, preferences, banner and `ls`.
def rung_banner(wire: Wire) -> str:
    sent_at = time.monotonic()
    wire.start_send()
    wire.prompt_wait(0, "the banner and the prompt")
    seconds = time.monotonic() - sent_at
    banner = banner_check(wire, bytes(wire.output))
    title = f"{' '.join(wire.ttyd.command)} ({socket.gethostname()})"
    if wire.title != title:
        raise CheckFailed(
            f"{wire.ttyd.version}'s title is {wire.title!r}, not {title!r}"
        )
    wire.command_check(b"ls\n", on_terminal("ls\n") + _PROMPT)
    return (
        f"ttyd title {wire.title!r}, its command and host; ttyd preferences"
        f" {json.dumps(wire.preferences)}; banner pid {banner.pid}, ttyd's"
        f" child running {' '.join(wire.ttyd.command)}, python"
        f" {banner.python}, sha256 {banner.sha256[:12]} equal to"
        " bootstrap.py's, its path and modules directory those of the"
        f" command, then the prompt, {seconds:.3f} s after the first message"
        " went; ls listed nothing"
    )


# Puts 1 MiB of 1, 2, 3 and 4 byte characters. Returns a summary.
def rung_big_put(wire: Wire) -> str:
    text = big_text()
    messages_before = wire.ttyd_messages
    start = time.monotonic()
    digest = put_check(wire, "big", text, wire.input_lines_send)
    seconds = time.monotonic() - start
    lines = text.count("\n")
    messages = len(put_input("big", text).splitlines())
    return (
        f"big.py of {len(text.encode())} bytes ({len(text)} characters),"
        f" {lines} lines of {_LINE_BYTES} bytes and a newline,"
        f" sent as {messages} ttyd messages"
        " while reading: its echo, equal to what was sent, and saved with"
        f" sha256 {digest[:12]}, equal to this client's and to the file's,"
        f" came in {wire.ttyd_messages - messages_before} ttyd messages,"
        f" {seconds:.2f} s from the put to the prompt"
    )


# Closes with a module running and checks all of it ends. Returns a summary.
def rung_close(wire: Wire) -> str:
    module_pid, _ = module_ready(wire, "stdin", "ready")
    seconds = session_close(wire, [], wire.ttyd.process.pid)
    return (
        f"with stdin running as pid {module_pid}: close"
        f" {_WEBSOCKET_CLOSE_NORMAL} answered with {wire.close_code}; ttyd"
        f" logged the program, pid {wire.banners[-1].pid}, killed with"
        f" signal {int(signal.SIGHUP)} (SIGHUP); it, its module and every"
        f" module that told its pid (pids {sorted(wire.module_pids)}) were"
        f" gone and ttyd had no child {seconds:.3f} s after the close;"
        f" {wire.ttyd_pings} ttyd pings answered"
    )


# Ends input at a new program's prompt and checks it exits. Returns a summary.
def rung_eof(ttyd: Ttyd) -> str:
    wire = websocket_open(ttyd, {})
    wire.start_send()
    wire.prompt_wait(0, "the banner and the prompt")
    pid = banner_check(wire, bytes(wire.output)).pid
    mark = len(wire.output)
    wire.end_expected = True
    sent_at = time.monotonic()
    wire.input_send(_EOF)
    wire.wait(lambda: wire.ended, "the connection's end after ^D")
    ended_seconds = time.monotonic() - sent_at
    wire.sock.close()
    if len(wire.output) != mark:
        raise CheckFailed(
            f"after ^D the program showed {bytes(wire.output[mark:])!r}"
        )
    found = program_end_wait(ttyd, pid)
    if found.group(1, 2) != ("exited with code", "0"):
        raise CheckFailed(f"{ttyd.version} logged: {found.string}")
    gone_seconds = processes_wait(wire, {pid}, pid, pid, sent_at)
    return (
        f"^D at the prompt of pid {pid}: nothing shown; {ttyd.version}"
        f" logged it exited with code 0; {ended_seconds:.4f} s after the ^D"
        f" {connection_end(wire)}; pid {pid} and its session gone"
        f" {gone_seconds:.3f} s after it"
    )


# Sends commands the bootstrapper refuses and checks each. Returns a summary.
def rung_errors(wire: Wire) -> str:
    for line, error in _ERRORS:
        wire.command_check(
            f"{line}\n".encode(), on_terminal(f"{line}\n{error}\n") + _PROMPT
        )
    refused = "; ".join(f"{line!r}: {error!r}" for line, error in _ERRORS)
    return (
        f"{len(_ERRORS)} commands each showed its echo, its error and the"
        f" prompt, equal to this client's: {refused}"
    )


# Runs a module that forks, sends `^C`, and checks both end. Returns a summary.
def rung_interrupt(wire: Wire) -> str:
    put_check(wire, "sleeper", _SLEEPER_SOURCE, wire.input_send)
    pid, forked = module_ready(wire, "sleeper", "pids")
    interrupted_at = time.monotonic()
    mark = wire.command(_INTERRUPT)
    prompt_seconds = time.monotonic() - interrupted_at
    shown = bytes(wire.output[mark:])
    end = on_terminal(f"sleeper: exit {-int(signal.SIGINT)}\n") + _PROMPT
    if not shown.startswith(_INTERRUPT_ECHO) or not shown.endswith(end):
        raise CheckFailed(
            f"^C to sleeper showed {shown!r} through {wire.ttyd.version}"
        )
    seconds = processes_wait(wire, {pid, forked}, pid, pid, interrupted_at)
    return (
        f"sleeper as pid {pid} forked pid {forked}; ^C: its echo, then"
        f" {len(shown) - len(_INTERRUPT_ECHO) - len(end)} bytes of"
        f" tracebacks, then {end!r}, {prompt_seconds:.3f} s after the ^C;"
        f" both pids gone {seconds:.3f} s after it"
    )


# Runs a module printing many lines, checking none is lost. Returns a summary.
def rung_lines(wire: Wire) -> str:
    put_check(wire, "lines", _LINES_SOURCE, wire.input_send)
    expected = (
        on_terminal(
            "lines\n"
            + "".join(f"{number}\n" for number in range(1, _LINES_COUNT + 1))
        )
        + _PROMPT
    )
    messages_before = wire.ttyd_messages
    start = time.monotonic()
    mark = wire.command(b"lines\n")
    seconds = time.monotonic() - start
    wire.transcript_check(mark, expected, "lines")
    return (
        f"lines printed {_LINES_COUNT} lines, all of them in order and no"
        f" exit line, {len(expected)} bytes in"
        f" {wire.ttyd_messages - messages_before} ttyd messages,"
        f" {seconds:.2f} s from the command to the prompt"
    )


# Puts a module whole and split two ways, checking each. Returns a summary.
def rung_put(wire: Wire) -> str:
    digest = put_check(wire, "report", _REPORT_SOURCE, wire.input_send)
    put_check(
        wire,
        "report",
        _REPORT_SOURCE,
        lambda data: wire.input_split_send(data, False),
    )
    put_check(
        wire,
        "report",
        _REPORT_SOURCE,
        lambda data: wire.input_split_send(data, True),
    )
    data = _REPORT_SOURCE.encode()
    wire.command_check(
        b"ls\n",
        on_terminal(f"ls\n{len(data)} {digest} report.py\n") + _PROMPT,
    )
    put = put_input("report", _REPORT_SOURCE)
    return (
        f"report.py put whole, then split at byte {split_offset(put)} of"
        f" {len(put)}, inside U+{ord(_NON_ASCII_SPLIT_CHARACTER):04X}, across"
        " two ttyd messages, then across two frames of one WebSocket"
        f" message; each echoed and saved {len(data)} bytes, sha256"
        f" {digest[:12]}, equal to this client's and to the file's; ls"
        " listed it alone"
    )


# Runs modules that report, exit with a code and raise. Returns a summary.
def rung_run(wire: Wire) -> str:
    line = report_check(wire, _RUN_ARGS)
    put_check(wire, "exiter", _EXITER_SOURCE, wire.input_send)
    wire.command_check(
        b"exiter 3\n", on_terminal("exiter 3\nexiter: exit 3\n") + _PROMPT
    )
    put_check(wire, "raiser", _RAISER_SOURCE, wire.input_send)
    mark = wire.command(b"raiser\n")
    shown = bytes(wire.output[mark:])
    path = os.path.join(wire.ttyd.command[2], "raiser.py")
    head = on_terminal("raiser\nTraceback (most recent call last):\n")
    tail = (
        on_terminal(
            f'  File "{path}", line 1, in <module>\n    {_RAISER_SOURCE}'
            f"ValueError: {_NON_ASCII_TEXT}\nraiser: exit 1\n"
        )
        + _PROMPT
    )
    if not shown.startswith(head) or not shown.endswith(tail):
        raise CheckFailed(
            f"raiser showed {shown!r} through {wire.ttyd.version}"
        )
    # The lines between the echo and the exit line.
    traceback_lines = shown.count(b"\r\n") - 2
    return (
        f"{line} showed its echo, argv, the text, working directory and"
        " first path the modules directory, XSJS_BOOTSTRAP, XSJS_MODULES,"
        " __main__ and its stderr line, equal to this client's, and no exit"
        f" line; exiter 3 showed exiter: exit 3; raiser showed"
        f" {traceback_lines} lines of traceback, from its first line to its"
        " ValueError, then raiser: exit 1"
    )


# Checks the page, token, a made up path and credentials. Returns a summary.
def rung_serve(ttyd: Ttyd) -> str:
    with open(_INDEX_PATH, "rb") as index_file:
        page = index_file.read()
    page_sha256 = hashlib.sha256(page).hexdigest()
    status, body = http_get(ttyd, "/", {})
    if status != 200 or hashlib.sha256(body).hexdigest() != page_sha256:
        raise CheckFailed(
            f"GET / answered {status} with {len(body)} bytes, sha256"
            f" {hashlib.sha256(body).hexdigest()}; {_INDEX_PATH} has"
            f" {len(page)} bytes, sha256 {page_sha256}"
        )
    status, token_body = http_get(ttyd, "/token", {})
    if status != 200 or json.loads(token_body) != {"token": ""}:
        raise CheckFailed(f"GET /token answered {status} with {token_body!r}")
    status, _ = http_get(ttyd, _MADE_UP_PATH, {})
    if status != 404:
        raise CheckFailed(f"GET {_MADE_UP_PATH} answered {status}")
    credential = base64.b64encode(_CREDENTIAL.encode()).decode()
    authorization = {"Authorization": f"Basic {credential}"}
    with ttyd_serve(
        ["--credential", _CREDENTIAL, *_TTYD_OPTIONS],
        ttyd.command,
        ttyd.deadline,
    ) as guarded:
        status, _ = http_get(guarded, "/", {})
        if status != 401:
            raise CheckFailed(f"GET / without credentials answered {status}")
        status, body = http_get(guarded, "/", authorization)
        if status != 200 or hashlib.sha256(body).hexdigest() != page_sha256:
            raise CheckFailed(
                f"GET / with credentials answered {status} with"
                f" {len(body)} bytes"
            )
        sock, _ = upgrade_send(guarded, {})
        with sock:
            answer = upgrade_read(sock, guarded)
        if answer:
            raise CheckFailed(
                f"/ws without credentials answered {answer[:200]!r}"
            )
        wire = websocket_open(guarded, authorization)
        with wire.sock:
            wire.close_send()
            wire.wait(lambda: wire.close_code is not None, "the close")
        if wire.close_code != _WEBSOCKET_CLOSE_NORMAL:
            raise CheckFailed(
                f"{guarded.version} answered close"
                f" {_WEBSOCKET_CLOSE_NORMAL} with {wire.close_code}"
            )
    return (
        f"{ttyd.version}: GET / 200, {len(page)} bytes, sha256 equal to"
        f" {os.path.basename(_INDEX_PATH)}'s;"
        f" /token {token_body.decode()}; {_MADE_UP_PATH} 404; with"
        " --credential:"
        " / 401 without it and 200 with it, /ws closed unanswered without"
        " it and 101 with it"
    )


# Runs a module reading stdin, sends it lines and `^D`. Returns a summary.
def rung_stdin(wire: Wire) -> str:
    put_check(wire, "stdin", _STDIN_SOURCE, wire.input_send)
    module_pid, parent = module_ready(wire, "stdin", "ready")
    bootstrap_pid = wire.banners[-1].pid
    if parent != bootstrap_pid or process_parent(module_pid) != bootstrap_pid:
        raise CheckFailed(
            f"stdin's pid {module_pid}, with parent {parent}, isn't the"
            f" child of the bootstrapper's {bootstrap_pid}"
        )
    cmdlines: list[bytes] = []
    for pid in (bootstrap_pid, module_pid):
        with open(f"/proc/{pid}/cmdline", "rb") as cmdline_file:
            cmdlines.append(cmdline_file.read())
    if cmdlines[0] != cmdlines[1]:
        raise CheckFailed(
            f"stdin's pid runs {cmdlines[1]!r}, not the bootstrapper's"
            f" {cmdlines[0]!r}"
        )
    whole = f"whole {_NON_ASCII_TEXT}\n"
    mark = len(wire.output)
    wire.input_send(whole.encode())
    wire.lines_check(mark, on_terminal(f"{whole}got {whole}"), "whole")
    halves = f"halves {_NON_ASCII_TEXT}\n"
    mark = len(wire.output)
    wire.input_split_send(halves.encode(), False)
    wire.lines_check(mark, on_terminal(f"{halves}got {halves}"), "halves")
    wire.command_check(_EOF, on_terminal("eof 2\n") + _PROMPT)
    return (
        f"stdin as pid {module_pid}, the child of the bootstrapper's pid"
        f" {bootstrap_pid} and running its command line, so no program was"
        " started for it; a line whole, then a line split at byte"
        f" {split_offset(halves.encode())} of {len(halves.encode())} inside"
        f" U+{ord(_NON_ASCII_SPLIT_CHARACTER):04X} across two ttyd messages,"
        " each echoed, then got back whole; ^D: eof 2, then the prompt with"
        " no exit line"
    )


# Kills ttyd under a client and checks what ends and how. Returns a summary.
def rung_ttyd_killed(ttyd: Ttyd) -> str:
    wire = websocket_open(ttyd, {})
    wire.start_send()
    wire.prompt_wait(0, "the banner and the prompt")
    pid = banner_check(wire, bytes(wire.output)).pid
    module_pid, _ = module_ready(wire, "stdin", "ready")
    wire.end_expected = True
    killed_at = time.monotonic()
    ttyd.kill(signal.SIGKILL)
    wire.wait(lambda: wire.ended, "the connection's end")
    ended_seconds = time.monotonic() - killed_at
    wire.wait(lambda: ttyd.stderr_ended, "ttyd's exit")
    status = ttyd.process.wait()
    if status != -signal.SIGKILL:
        raise CheckFailed(f"{ttyd.version} exited with {status} on SIGKILL")
    wire.sock.close()
    processes_wait(wire, {pid, module_pid}, pid, pid, killed_at)
    gone_seconds = processes_wait(
        wire, set(), module_pid, module_pid, killed_at
    )
    return (
        f"SIGKILL to {ttyd.version} with stdin running as pid"
        f" {module_pid} under pid {pid} reached its client:"
        f" {ended_seconds:.4f} s after the kill {connection_end(wire)};"
        f" ttyd exited with {status}; the program, its module and their"
        f" sessions were gone {gone_seconds:.3f} s after the kill"
    )


# Checks two clients at once, each with its own program. Returns a summary.
def rung_two_clients(ttyd: Ttyd) -> str:
    first = websocket_open(ttyd, {})
    second = websocket_open(ttyd, {})
    wires = [first, second]
    for wire in wires:
        wire.start_send()
    wires_wait(
        wires,
        lambda: all(wire.prompt_after(0) for wire in wires),
        "both clients' banners and prompts",
    )
    first_pid, second_pid = (
        banner_check(wire, bytes(wire.output)).pid for wire in wires
    )
    if first_pid == second_pid:
        raise CheckFailed(f"both clients' banners have pid {first_pid}")
    marks = [len(wire.output) for wire in wires]
    for wire in wires:
        wire.input_send(b"stdin\n")
    wires_wait(
        wires,
        lambda: all(
            wire.lines_after(mark, 2) for wire, mark in zip(wires, marks)
        ),
        "stdin's first line on both clients",
    )
    words = ["first", "second"]
    module_pids: list[int] = []
    for wire, mark, word in zip(wires, marks, words):
        module_pid, parent = ready_parse(wire, mark, "stdin", "ready")
        pid = wire.banners[-1].pid
        if parent != pid or process_parent(module_pid) != pid:
            raise CheckFailed(
                f"the {word} client's stdin, pid {module_pid}, isn't its"
                " program's child"
            )
        module_pids.append(module_pid)
        wire.input_send(f"{word}\n".encode())
        wire.input_send(_EOF)
    wires_wait(
        wires,
        lambda: all(
            wire.prompt_after(mark) for wire, mark in zip(wires, marks)
        ),
        "both clients' stdin exits",
    )
    for wire, mark, word, module_pid in zip(wires, marks, words, module_pids):
        wire.transcript_check(
            mark,
            on_terminal(
                f"stdin\nready {module_pid} {wire.banners[-1].pid}\n{word}\n"
                f"got {word}\neof 1\n"
            )
            + _PROMPT,
            f"the {word} client's stdin",
        )
    first_seconds = session_close(first, [second], first_pid)
    program_check(ttyd, second_pid)
    second.command_check(
        b"ls\n",
        on_terminal(f"ls\n{modules_listing(ttyd.command[2])}") + _PROMPT,
    )
    second_seconds = session_close(second, [], second_pid)
    return (
        f"banners with pids {first_pid} and {second_pid}; stdin ran on both"
        f" at once as pids {module_pids[0]} and {module_pids[1]}, each its"
        " own program's child, and each showed only its own client's line;"
        f" the first closed with {_WEBSOCKET_CLOSE_NORMAL} answered with"
        f" {first.close_code}, pid {first_pid} killed with signal"
        f" {int(signal.SIGHUP)} (SIGHUP) and gone {first_seconds:.3f} s after"
        f" the close; then the second's ls, with pid {second_pid} still"
        " running, listed the modules directory as it is; the second closed"
        f" with {_WEBSOCKET_CLOSE_NORMAL} answered with {second.close_code},"
        f" gone {second_seconds:.3f} s after the close"
    )


# Updates the bootstrapper from a module and restarts it. Returns a summary.
def rung_update(wire: Wire) -> str:
    bootstrap_path = wire.ttyd.command[1]
    with open(bootstrap_path, "rb") as bootstrap_file:
        updated = bootstrap_file.read() + _UPDATE_LINE
    digest = hashlib.sha256(updated).hexdigest()
    put_check(wire, "update", _UPDATE_SOURCE, wire.input_send)
    wire.command_check(
        b"update\n", on_terminal(f"update\nsha256 {digest}\n") + _PROMPT
    )
    first = wire.banners[-1]
    restarted_at = time.monotonic()
    mark = wire.command(b"restart\n")
    seconds = time.monotonic() - restarted_at
    shown = bytes(wire.output[mark:])
    echo = on_terminal("restart\n")
    if not shown.startswith(echo):
        raise CheckFailed(
            f"restart showed {shown!r} through {wire.ttyd.version}"
        )
    second = banner_check(wire, shown[len(echo) :])
    if second.pid != first.pid or second.sha256 != digest:
        raise CheckFailed(
            f"restart's banner {second} after banner {first}, where pid"
            f" {first.pid} and sha256 {digest} were due"
        )
    line = report_check(wire, [])
    return (
        f"update appended {len(_UPDATE_LINE)} bytes to"
        f" {os.path.basename(bootstrap_path)} and printed its sha256"
        f" {digest[:12]}, equal to this client's; restart: a banner with the"
        f" same pid {second.pid} and that sha256, then the prompt,"
        f" {seconds:.3f} s after the command; {line} then showed what it did"
        " before"
    )


# Closes the wire and returns the seconds until all its processes are gone.
def session_close(wire: Wire, others: list[Wire], parent: int) -> float:
    pid = wire.banners[-1].pid
    wire.close_send()
    closed_at = time.monotonic()
    wires_wait(
        [wire, *others],
        lambda: wire.close_code is not None,
        "ttyd's close frame",
    )
    if wire.close_code != _WEBSOCKET_CLOSE_NORMAL:
        raise CheckFailed(
            f"{wire.ttyd.version} answered close {_WEBSOCKET_CLOSE_NORMAL}"
            f" with {wire.close_code}"
        )
    wire.sock.close()
    found = program_end_wait(wire.ttyd, pid)
    if found.group(1, 2) != ("killed with signal", str(int(signal.SIGHUP))):
        raise CheckFailed(f"{wire.ttyd.version} logged: {found.string}")
    return processes_wait(
        wire, {pid, *wire.module_pids}, pid, parent, closed_at
    )


# Exits with 128 plus the signal's number.
def signal_exit(signal_number: int, frame: types.FrameType | None) -> None:
    sys.exit(128 + signal_number)


# Returns the offset 2 bytes into the first `_NON_ASCII_SPLIT_CHARACTER`.
def split_offset(data: bytes) -> int:
    return data.index(_NON_ASCII_SPLIT_CHARACTER.encode()) + 2


# Starts ttyd on a port of its choosing, read from its log, then stops it.
@contextlib.contextmanager
def ttyd_serve(
    options: list[str], command: list[str], deadline: float
) -> Generator[Ttyd]:
    ttyd = Ttyd(options, command, deadline)
    try:
        found = ttyd.line_wait(_VERSION_PATTERN, 0, "ttyd's version")
        ttyd.version = found.group(1)
        found = ttyd.line_wait(_LISTENING_PATTERN, 0, "ttyd to listen")
        ttyd.port = int(found.group(1))
        yield ttyd
    finally:
        ttyd.stop()


# Returns what ttyd sent up to its headers' end, or all if it closed first.
def upgrade_read(sock: socket.socket, ttyd: Ttyd) -> bytes:
    data = b""
    while b"\r\n\r\n" not in data:
        sock.settimeout(remaining(ttyd.deadline, "ttyd's answer to /ws"))
        chunk = sock.recv(1 << 16)
        if not chunk:
            return data
        data += chunk
    return data


# Asks ttyd for a WebSocket on /ws from its origin. Returns the socket and key.
def upgrade_send(
    ttyd: Ttyd, headers: dict[str, str]
) -> tuple[socket.socket, str]:
    key = base64.b64encode(os.urandom(16)).decode()
    host = f"127.0.0.1:{ttyd.port}"
    sock = socket.create_connection(
        ("127.0.0.1", ttyd.port), remaining(ttyd.deadline, "ttyd's /ws")
    )
    lines = [
        "GET /ws HTTP/1.1",
        f"Host: {host}",
        f"Origin: http://{host}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Version: 13",
        "Sec-WebSocket-Protocol: tty",
        *(f"{name}: {value}" for name, value in headers.items()),
    ]
    sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
    return sock, key


# Returns a Wire on a WebSocket ttyd accepted with the tty subprotocol.
def websocket_open(ttyd: Ttyd, headers: dict[str, str]) -> Wire:
    sock, key = upgrade_send(ttyd, headers)
    data = upgrade_read(sock, ttyd)
    head, separator, rest = data.partition(b"\r\n\r\n")
    status, *header_lines = head.decode("latin-1").split("\r\n")
    if not separator or not status.startswith("HTTP/1.1 101 "):
        raise CheckFailed(f"{ttyd.version} answered /ws with {data[:200]!r}")
    answered: dict[str, str] = {}
    for header_line in header_lines:
        name, _, value = header_line.partition(":")
        answered[name.strip().lower()] = value.strip()
    accept = base64.b64encode(
        hashlib.sha1((key + _WEBSOCKET_GUID).encode()).digest()
    ).decode()
    if answered.get("sec-websocket-accept") != accept:
        raise CheckFailed(f"{ttyd.version} answered the key wrongly: {head!r}")
    if answered.get("sec-websocket-protocol") != "tty":
        raise CheckFailed(f"{ttyd.version} didn't choose tty: {head!r}")
    return Wire(ttyd, sock, rest)


# Sends what each wire queued and handles what ttyd sends until done.
def wires_wait(wires: list[Wire], done: Callable[[], bool], what: str) -> None:
    ttyd = wires[0].ttyd
    while not done() or any(wire.unsent for wire in wires):
        readers: list[socket.socket | int] = [
            wire.sock for wire in wires if not wire.ended
        ]
        writers = [wire.sock for wire in wires if wire.unsent]
        if not ttyd.stderr_ended:
            readers.append(ttyd.fd)
        readable, writable, _ = select.select(
            readers,
            writers,
            [],
            remaining(ttyd.deadline, f"{what} through {ttyd.version}"),
        )
        if ttyd.fd in readable:
            ttyd.stderr_read()
        for wire in wires:
            if wire.sock in writable:
                wire.unsent_send()
            if wire.sock in readable:
                wire.socket_read()


# Runs the rungs in order, printing a line each, and returns the exit code.
def main() -> int:
    argparse.ArgumentParser(
        description="Run the wire test: a copy of bootstrap.py through"
        " Linux ttyd, from a standard library WebSocket client."
    ).parse_args()
    for signal_number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(signal_number, signal_exit)
    deadline = time.monotonic() + _RUN_TIMEOUT_SECONDS
    os.makedirs(_BUILD_PATH, exist_ok=True)
    rung = "serve"
    try:
        with tempfile.TemporaryDirectory(
            prefix="test_wire-", dir=_BUILD_PATH
        ) as work_path:
            bootstrap_path = os.path.join(work_path, "bootstrap.py")
            shutil.copyfile(_BOOTSTRAP_PATH, bootstrap_path)
            command = [
                "python3",
                bootstrap_path,
                os.path.join(work_path, "modules"),
            ]
            with ttyd_serve(_TTYD_OPTIONS, command, deadline) as ttyd:
                print(f"{rung}: {rung_serve(ttyd)}", flush=True)
                wire = websocket_open(ttyd, {})
                for rung, check in (
                    ("banner", rung_banner),
                    ("put", rung_put),
                    ("errors", rung_errors),
                    ("run", rung_run),
                    ("stdin", rung_stdin),
                    ("interrupt", rung_interrupt),
                    ("abandon", rung_abandon),
                    ("big put", rung_big_put),
                    ("lines", rung_lines),
                    ("update", rung_update),
                    ("close", rung_close),
                ):
                    print(f"{rung}: {check(wire)}", flush=True)
                # Each on new WebSockets, and last the one that ends ttyd.
                for rung, ttyd_check in (
                    ("eof", rung_eof),
                    ("two clients", rung_two_clients),
                    ("ttyd killed", rung_ttyd_killed),
                ):
                    print(f"{rung}: {ttyd_check(ttyd)}", flush=True)
    except CheckFailed as failure:
        print(f"error: {rung}: {failure}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
