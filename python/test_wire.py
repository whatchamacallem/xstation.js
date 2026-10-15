#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The wire test: starts Linux ttyd, from a checkout of ttyd beside this
# project, serving bootstrap.html and running a copy of bootstrap.py made
# in a directory under build/, then speaks ttyd's protocol to the program
# as the page does, rung by rung: over one WebSocket, then over two at
# once, and last over one while ttyd is killed. ttyd's log is copied to
# stderr whole. It stops at the first failed check with the measurement
# that failed and exits 1; on success it prints one line per rung and
# exits 0. Standard library only, and ttyd is the one program it starts:
#
#     python3 python/test_wire.py

import argparse, base64, collections, contextlib, hashlib, http.client, json
import os, re, select, shutil, signal, socket, subprocess, sys, tempfile, time
import types
from collections.abc import Callable, Generator
from typing import Any, cast

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

_BOOTSTRAP_PATH = os.path.join(_PYTHON_PATH, "bootstrap.py")

# 1 MiB in 32 byte units: 23 random ASCII characters, then 2, 3 and 4 bytes.
_BIG_ASCII_PER_UNIT = 23
_BIG_UNITS = 32768
_BIG_WIDE_TEXT = "\u00e9\u4e2d\U0001f600"

# Where the copy of bootstrap.py and its modules go, in a directory each run.
_BUILD_PATH = os.path.join(os.path.dirname(_PYTHON_PATH), "build")

# The terminal size the first message gives.
_COLUMNS = 80
_ROWS = 24

_CREDENTIAL = "user:pass"

# A module that exits with the code its argument gives.
_EXIT_SOURCE = "import sys\n\nsys.exit(int(sys.argv[1]))\n"

_INDEX_PATH = os.path.join(_PYTHON_PATH, "bootstrap.html")

# The lines lines.py prints, 1 to this.
_LINES_COUNT = 100000
_LINES_SOURCE = f"for n in range(1, {_LINES_COUNT} + 1):\n    print(n)\n"

_LISTENING_PATTERN = re.compile(r" Listening on port: (\d+)$")

_MADE_UP_PATH = "/other.js"

# The fields of each message the program sends, by type.
_MESSAGE_FIELDS: dict[str, dict[str, type[object]]] = {
    "exit": {"name": str, "code": int},
    "hello": {
        "pid": int,
        "python": str,
        "bootstrap": str,
        "sha256": str,
        "modules": str,
        "started": float,
    },
    "modules": {"entries": list},
    "out": {"stream": str, "data": str},
    "saved": {"name": str, "bytes": int, "sha256": str},
    "started": {"name": str, "pid": int, "args": list},
}

# Holds 2, 3 and 4 byte characters, and the split lands inside the last.
_NON_ASCII_TEXT = "na\u00efve \u65e5\u672c\u8a9e \U0001f600 \u00e9t\u00e9"
_NON_ASCII_SPLIT_CHARACTER = "\U0001f600"

_POLL_SECONDS = 0.05

# A module that raises, so the interpreter's own exit reports it.
_RAISE_SOURCE = f"raise ValueError({_NON_ASCII_TEXT!r})\n"

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
_TTYD_OPTIONS = [
    "--writable",
    "--check-origin",
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


class CheckFailed(Exception):
    pass


# A module's run on one wire: its start, what it wrote, and its exit.
class Run:
    def __init__(self, started: dict[str, Any]) -> None:
        self.started = started
        self.streams = {"stdout": bytearray(), "stderr": bytearray()}
        self.outs = 0
        self.exit: dict[str, Any] | None = None
        # The module list that came after the exit.
        self.modules: list[dict[str, Any]] | None = None

    # Returns what the module wrote on the stream, decoded as `UTF-8`.
    def text(self, stream_name: str) -> str:
        return self.streams[stream_name].decode()


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
        # What ttyd sent that isn't yet a whole frame.
        self.unread = bytearray(rest)
        # The frames so far of a message ttyd sends in more than one.
        self.fragments: bytearray | None = None
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
        # The output after the last whole line.
        self.stream = b""
        self.received_lines = 0
        self.hellos: list[dict[str, Any]] = []
        # The latest module list, and how many lists have come.
        self.modules: list[dict[str, Any]] = []
        self.modules_count = 0
        # The saved answers due, oldest first, as this client computes them.
        self.saves_due: collections.deque[dict[str, Any]] = collections.deque()
        self.saves: list[dict[str, Any]] = []
        # The runs sent and not yet started, as name and args.
        self.runs_due: collections.deque[tuple[str, list[str]]] = (
            collections.deque()
        )
        self.runs: list[Run] = []
        self.handlers: dict[str, Callable[[dict[str, Any]], None]] = {
            "exit": self.exit_take,
            "hello": self.hello_take,
            "modules": self.modules_take,
            "out": self.out_take,
            "saved": self.saved_take,
            "started": self.started_take,
        }
        self.frames_handle()

    # Sends a close frame with the normal code.
    def close_send(self) -> None:
        self.close_sent = True
        self.frame_send(
            _WEBSOCKET_OPCODE_CLOSE, _WEBSOCKET_CLOSE_NORMAL.to_bytes(2, "big")
        )

    # Records the running module's exit.
    def exit_take(self, message: dict[str, Any]) -> None:
        run = self.run_running(message)
        if message["name"] != run.started["name"]:
            raise CheckFailed(f"exit {message} for {run.started}")
        run.exit = message

    # Sends one WebSocket frame, masked as a client's must be.
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
        self.sock.settimeout(remaining(self.ttyd.deadline, "ttyd to read"))
        self.sock.sendall(bytes(head) + mask + masked)

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

    # Records a hello, which only a restart repeats, and never mid run.
    def hello_take(self, message: dict[str, Any]) -> None:
        if self.runs and self.runs[-1].exit is None:
            raise CheckFailed(f"hello came while a module ran: {message}")
        self.hellos.append(message)

    # Sends the bytes to the running module's stdin.
    def in_send(self, data: bytes) -> None:
        self.line_send(
            {"type": "in", "data": base64.b64encode(data).decode("ascii")}
        )

    # Handles one line of the program's output.
    def line_handle(self, line: bytes) -> None:
        message = message_parse(line)
        if not self.hellos and message["type"] != "hello":
            raise CheckFailed(
                f"the program's first line isn't hello: {line!r}"
            )
        self.handlers[message["type"]](message)
        self.received_lines += 1

    # Sends a line of input to the program as one ttyd message.
    def line_send(self, message: dict[str, Any]) -> None:
        self.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + message_line(message))

    # Records a module list, and keeps the first after an exit with the run.
    def modules_take(self, message: dict[str, Any]) -> None:
        entries: list[dict[str, Any]] = []
        for entry in cast(list[object], message["entries"]):
            if type(entry) is not dict:
                raise CheckFailed(f"modules has an entry {entry!r}")
            fields = cast(dict[str, Any], entry)
            if fields.keys() != {"name", "bytes", "sha256"} or (
                type(fields["name"]),
                type(fields["bytes"]),
                type(fields["sha256"]),
            ) != (str, int, str):
                raise CheckFailed(f"modules has an entry {entry!r}")
            entries.append(fields)
        self.modules = entries
        self.modules_count += 1
        last = self.runs[-1] if self.runs else None
        if last is not None and last.exit is not None and last.modules is None:
            last.modules = self.modules

    # Adds what the running module wrote to its stream.
    def out_take(self, message: dict[str, Any]) -> None:
        run = self.run_running(message)
        if message["stream"] not in run.streams:
            raise CheckFailed(f"out on no stream of a module: {message}")
        run.streams[message["stream"]] += base64.b64decode(
            message["data"], validate=True
        )
        run.outs += 1

    # Counts a put as due its saved answer. Returns its line.
    def put_line(self, name: str, text: str) -> bytes:
        data = text.encode()
        self.saves_due.append(
            {
                "type": "saved",
                "name": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
        return message_line({"type": "put", "name": name, "text": text})

    # Sends a put as one ttyd message.
    def put_send(self, name: str, text: str) -> None:
        self.frame_send(
            _WEBSOCKET_OPCODE_BINARY, b"0" + self.put_line(name, text)
        )

    # Returns the running module, failing on the message when none runs.
    def run_running(self, message: dict[str, Any]) -> Run:
        if not self.runs or self.runs[-1].exit is not None:
            raise CheckFailed(f"{message['type']} with no module running")
        return self.runs[-1]

    # Sends a run, due its started answer.
    def run_send(self, name: str, args: list[str]) -> None:
        self.runs_due.append((name, args))
        self.line_send({"type": "run", "name": name, "args": args})

    # Records a saved answer, failing unless it is the oldest put's as due.
    def saved_take(self, message: dict[str, Any]) -> None:
        if not self.saves_due:
            raise CheckFailed(f"saved came unasked: {message}")
        due = self.saves_due.popleft()
        if message != due:
            raise CheckFailed(f"saved {message} where {due} was due")
        self.saves.append(message)

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

    # Sends the first message, which starts the program, with ttyd's token.
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

    # Records a module's start, failing unless it is the oldest run's.
    def started_take(self, message: dict[str, Any]) -> None:
        if self.runs and self.runs[-1].exit is None:
            raise CheckFailed(f"started while a module ran: {message}")
        if not self.runs_due:
            raise CheckFailed(f"started came unasked: {message}")
        name, args = self.runs_due.popleft()
        if (message["name"], message["args"]) != (name, args):
            raise CheckFailed(f"started {message} for run {name} {args}")
        self.runs.append(Run(message))

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
            *lines, self.stream = (self.stream + message[1:]).split(b"\n")
            for line in lines:
                self.line_handle(line)

    # Sends a message of a type with no fields.
    def type_send(self, kind: str) -> None:
        self.line_send({"type": kind})

    # Handles what ttyd sends until done answers True.
    def wait(self, done: Callable[[], bool], what: str) -> None:
        wires_wait([self], done, what)


# Fails unless hello's pid is ttyd's child running its command, as hello says.
def hello_check(wire: Wire, hello: dict[str, Any]) -> None:
    command = wire.ttyd.command
    with open(f"/proc/{hello['pid']}/cmdline", "rb") as cmdline_file:
        cmdline = cmdline_file.read().split(b"\0")[:-1]
    if cmdline != [argument.encode() for argument in command]:
        raise CheckFailed(f"hello's pid {hello['pid']} runs {cmdline}")
    parent = process_parent(hello["pid"])
    if parent != wire.ttyd.process.pid:
        raise CheckFailed(
            f"hello's pid {hello['pid']} is the child of {parent}, not of"
            f" ttyd's {wire.ttyd.process.pid}"
        )
    with open(command[1], "rb") as bootstrap_file:
        digest = hashlib.sha256(bootstrap_file.read()).hexdigest()
    expected = {
        "bootstrap": command[1],
        "sha256": digest,
        "modules": command[2],
    }
    for name, value in expected.items():
        if hello[name] != value:
            raise CheckFailed(f"hello's {name} is {hello[name]}, not {value}")


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


# Returns the message as a line of JSON, characters as they are, `UTF-8`.
def message_line(message: dict[str, Any]) -> bytes:
    return json.dumps(message, ensure_ascii=False).encode() + b"\n"


# Returns the line's JSON object, failing unless its fields match its type.
def message_parse(line: bytes) -> dict[str, Any]:
    if not line.isascii() or b"\r" in line or b"\n" in line:
        raise CheckFailed(f"the program sent a line not ASCII JSON: {line!r}")
    try:
        parsed: Any = json.loads(line)
    except json.JSONDecodeError as error:
        raise CheckFailed(
            f"the program sent a line that isn't JSON ({error}): {line[:200]!r}"
        ) from error
    if not isinstance(parsed, dict):
        raise CheckFailed(f"the program sent a line not an object: {line!r}")
    message = cast(dict[str, Any], parsed)
    if message.get("type") not in _MESSAGE_FIELDS:
        raise CheckFailed(f"the program sent no known type: {line[:200]!r}")
    fields = _MESSAGE_FIELDS[message["type"]]
    if message.keys() != {"type", *fields}:
        raise CheckFailed(
            f"the program's {message['type']} has fields {sorted(message)},"
            f" not {sorted(['type', *fields])}"
        )
    for name, kind in fields.items():
        if type(message[name]) is not kind:
            raise CheckFailed(
                f"the program's {message['type']} has {name}"
                f" {message[name]!r}, not of type {kind.__name__}"
            )
    return message


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


# Returns the seconds left before the overall timeout, failing once past.
def remaining(deadline: float, what: str) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise CheckFailed(
            f"gave up after {_RUN_TIMEOUT_SECONDS} s waiting for {what}"
        )
    return left


# Puts 1 MiB of 1, 2, 3 and 4 byte characters. Returns a summary.
def rung_big_put(wire: Wire) -> str:
    ascii_text = base64.b64encode(
        os.urandom(_BIG_UNITS * _BIG_ASCII_PER_UNIT * 3 // 4)
    ).decode()
    text = "".join(
        ascii_text[index : index + _BIG_ASCII_PER_UNIT] + _BIG_WIDE_TEXT
        for index in range(
            0, _BIG_UNITS * _BIG_ASCII_PER_UNIT, _BIG_ASCII_PER_UNIT
        )
    )
    start = time.monotonic()
    modules_before = wire.modules_count
    wire.put_send("big.py", text)
    wire.wait(
        lambda: not wire.saves_due and wire.modules_count > modules_before,
        "big.py's saved answer and the module list after it",
    )
    seconds = time.monotonic() - start
    saved = wire.saves[-1]
    saved_check(wire, saved)
    return (
        f"big.py of {saved['bytes']} bytes ({len(text)} characters) saved"
        f" with sha256 {saved['sha256'][:12]} equal to this client's and to"
        f" the file's, {seconds:.2f} s from the put"
    )


# Closes with a module running and checks all of it ends. Returns a summary.
def rung_close(wire: Wire) -> str:
    run, _ = run_ready(wire, "stdin.py")
    module_pid = run.started["pid"]
    seconds = session_close(wire, [], wire.ttyd.process.pid)
    return (
        f"with stdin.py running as pid {module_pid}: close"
        f" {_WEBSOCKET_CLOSE_NORMAL} answered with {wire.close_code}; ttyd"
        f" logged the program, pid {wire.hellos[-1]['pid']}, killed with"
        f" signal {int(signal.SIGHUP)} (SIGHUP); it, its module and every"
        f" module it ran (pids {sorted(run_pids(wire))}) were gone and ttyd"
        f" had no child {seconds:.3f} s after the close; {wire.ttyd_pings}"
        " ttyd pings answered"
    )


# Starts the program and checks the title, preferences, hello and modules.
def rung_hello(wire: Wire) -> str:
    sent_at = time.time()
    wire.start_send()
    wire.wait(lambda: wire.modules_count == 1, "hello and the module list")
    hello = wire.hellos[0]
    hello_check(wire, hello)
    received_at = time.time()
    if not sent_at <= hello["started"] <= received_at:
        raise CheckFailed(
            f"hello's started {hello['started']} is outside the first"
            f" message's {sent_at} to its receipt's {received_at}"
        )
    title = f"{' '.join(wire.ttyd.command)} ({socket.gethostname()})"
    if wire.title != title:
        raise CheckFailed(f"ttyd's title is {wire.title!r}, not {title!r}")
    if wire.modules != []:
        raise CheckFailed(f"a new directory's module list is {wire.modules}")
    return (
        f"ttyd title {wire.title!r}, its command and host; ttyd preferences"
        f" {json.dumps(wire.preferences)}; hello pid {hello['pid']}, ttyd's"
        f" child running {' '.join(wire.ttyd.command)}, python"
        f" {hello['python']}, sha256 {hello['sha256'][:12]} equal to"
        f" bootstrap.py's, started {hello['started'] - sent_at:.3f} s after"
        " the first message went; module list empty"
    )


# Runs a module that forks, kills it, and checks both end. Returns a summary.
def rung_kill(wire: Wire) -> str:
    wire.put_send("sleeper.py", _SLEEPER_SOURCE)
    run, line = run_ready(wire, "sleeper.py")
    words = line.split()
    if words[:2] != ["pids", str(run.started["pid"])]:
        raise CheckFailed(f"sleeper.py's first line is {line!r}")
    forked = int(words[2])
    killed_at = time.monotonic()
    wire.type_send("kill")
    wire.wait(lambda: run.modules is not None, "sleeper.py's exit")
    exit_message = cast(dict[str, Any], run.exit)
    if exit_message["code"] != -signal.SIGTERM:
        raise CheckFailed(f"sleeper.py's exit is {exit_message}")
    pid = run.started["pid"]
    seconds = processes_wait(wire, {pid, forked}, pid, pid, killed_at)
    return (
        f"sleeper.py as pid {run.started['pid']} forked pid {forked}; kill:"
        f" exit code {exit_message['code']} (SIGTERM), both pids gone"
        f" {seconds:.3f} s after the kill"
    )


# Runs a module printing many lines, checking none is lost. Returns a summary.
def rung_lines(wire: Wire) -> str:
    wire.put_send("lines.py", _LINES_SOURCE)
    start = time.monotonic()
    run = run_wait(wire, "lines.py", [])
    seconds = time.monotonic() - start
    expected = "".join(f"{n}\n" for n in range(1, _LINES_COUNT + 1))
    if run.text("stdout") != expected:
        lines = run.text("stdout").split("\n")
        unequal = next(
            (n, line) for n, line in enumerate(lines, 1) if line != str(n)
        )
        raise CheckFailed(
            f"lines.py printed {len(lines) - 1} lines, line {unequal[0]}"
            f" {unequal[1]!r}"
        )
    run_exit_check(run, 0)
    return (
        f"lines.py printed {_LINES_COUNT} lines in {run.outs} out messages,"
        f" {seconds:.2f} s from the run to the module list after the exit,"
        " all of them in order; exit code 0"
    )


# Puts a module whole and split two ways, checking each. Returns a summary.
def rung_put(wire: Wire) -> str:
    wire.put_send("report.py", _REPORT_SOURCE)
    # The same put split inside a character in two messages, then two frames.
    line = wire.put_line("report.py", _REPORT_SOURCE)
    split = line.index(_NON_ASCII_SPLIT_CHARACTER.encode()) + 2
    wire.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + line[:split])
    wire.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + line[split:])
    line = wire.put_line("report.py", _REPORT_SOURCE)
    wire.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + line[:split], False)
    wire.frame_send(_WEBSOCKET_OPCODE_CONTINUATION, line[split:])
    wire.wait(
        lambda: not wire.saves_due and wire.modules_count == 4,
        "three saved answers and their module lists",
    )
    saved = wire.saves[-1]
    saved_check(wire, saved)
    return (
        f"report.py put whole, then split at byte {split} of {len(line)},"
        f" inside U+{ord(_NON_ASCII_SPLIT_CHARACTER):04X}, across two ttyd"
        " messages, then across two frames of one WebSocket message; each"
        f" saved {saved['bytes']} bytes, sha256 {saved['sha256'][:12]} equal"
        " to this client's and to the file's; module list"
        f" {[entry['name'] for entry in wire.modules]}"
    )


# Runs modules that report, exit with a code and raise. Returns a summary.
def rung_run(wire: Wire) -> str:
    run = run_wait(wire, "report.py", _RUN_ARGS)
    modules = wire.hellos[-1]["modules"]
    expected = "".join(
        f"{name} {value}\n"
        for name, value in (
            ("argv", _RUN_ARGS),
            ("text", _NON_ASCII_TEXT),
            ("cwd", modules),
            ("path", modules),
            ("bootstrap", wire.ttyd.command[1]),
            ("modules", modules),
            ("name", "__main__"),
        )
    )
    if run.text("stdout") != expected:
        raise CheckFailed(
            f"report.py printed {run.text('stdout')!r} where {expected!r} was"
            " due"
        )
    if run.text("stderr") != f"stderr {_NON_ASCII_TEXT}\n":
        raise CheckFailed(f"report.py's stderr is {run.text('stderr')!r}")
    run_exit_check(run, 0)
    wire.put_send("exit.py", _EXIT_SOURCE)
    exited = run_wait(wire, "exit.py", ["3"])
    run_exit_check(exited, 3)
    wire.put_send("raise.py", _RAISE_SOURCE)
    raised = run_wait(wire, "raise.py", [])
    run_exit_check(raised, 1)
    traceback = raised.text("stderr").split("\n")
    last = [f"ValueError: {_NON_ASCII_TEXT}", ""]
    if traceback[0] != "Traceback (most recent call last):" or (
        traceback[-2:] != last
    ):
        raise CheckFailed(f"raise.py's stderr is {raised.text('stderr')!r}")
    return (
        f"report.py with args {_RUN_ARGS!r} as pid {run.started['pid']}:"
        f" {run.outs} out messages, stdout equal to this client's (argv, the"
        " text, working directory and first path the modules directory,"
        " XSJS_BOOTSTRAP, XSJS_MODULES, __main__), stderr equal, exit code 0,"
        " module list after the exit; exit.py 3 exited with 3; raise.py"
        f" exited with 1 after {len(traceback) - 1} lines of traceback ending"
        " in its ValueError"
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


# Runs a module reading stdin, sends it lines and EOF. Returns a summary.
def rung_stdin(wire: Wire) -> str:
    wire.put_send("stdin.py", _STDIN_SOURCE)
    run, line = run_ready(wire, "stdin.py")
    bootstrap_pid = wire.hellos[-1]["pid"]
    module_pid = run.started["pid"]
    if line != f"ready {module_pid} {bootstrap_pid}":
        raise CheckFailed(f"stdin.py's first line is {line!r}")
    cmdlines: list[bytes] = []
    for pid in (bootstrap_pid, module_pid):
        with open(f"/proc/{pid}/cmdline", "rb") as cmdline_file:
            cmdlines.append(cmdline_file.read())
    if cmdlines[0] != cmdlines[1]:
        raise CheckFailed(
            f"stdin.py's pid runs {cmdlines[1]!r}, not the bootstrapper's"
            f" {cmdlines[0]!r}"
        )
    whole = f"whole {_NON_ASCII_TEXT}\n".encode()
    wire.in_send(whole)
    halves = f"halves {_NON_ASCII_TEXT}\n".encode()
    split = halves.index(_NON_ASCII_SPLIT_CHARACTER.encode()) + 2
    wire.in_send(halves[:split])
    wire.in_send(halves[split:])
    wire.type_send("eof")
    wire.wait(lambda: run.modules is not None, "stdin.py's exit")
    expected = f"{line}\ngot {whole.decode()}got {halves.decode()}eof 2\n"
    if run.text("stdout") != expected:
        raise CheckFailed(
            f"stdin.py printed {run.text('stdout')!r} where {expected!r} was"
            " due"
        )
    run_exit_check(run, 0)
    return (
        f"stdin.py as pid {module_pid}, the child of the bootstrapper's pid"
        f" {bootstrap_pid} and running its command line, so no program was"
        f" started for it; in of a line whole, then of a line split at byte"
        f" {split} of {len(halves)} inside"
        f" U+{ord(_NON_ASCII_SPLIT_CHARACTER):04X} across two in messages,"
        " then eof: both lines echoed whole, exit code 0"
    )


# Kills ttyd under a client and checks what ends and how. Returns a summary.
def rung_ttyd_killed(ttyd: Ttyd) -> str:
    wire = websocket_open(ttyd, {})
    wire.start_send()
    wire.wait(lambda: wire.modules_count == 1, "hello and the module list")
    hello_check(wire, wire.hellos[0])
    pid = wire.hellos[0]["pid"]
    run, _ = run_ready(wire, "stdin.py")
    module_pid = run.started["pid"]
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
    if wire.close_code is None:
        end = (
            "the TCP connection ended with no close frame, which a browser"
            " reports as 1006"
        )
    else:
        end = (
            f"a close frame of code {wire.close_code}, reason"
            f" {wire.close_reason!r}, came and the TCP connection ended"
        )
    return (
        f"SIGKILL to {ttyd.version} with stdin.py running as pid"
        f" {module_pid} under pid {pid} reached its client:"
        f" {ended_seconds:.4f} s after the kill {end}; ttyd exited with"
        f" {status}; the program, its module and their sessions were gone"
        f" {gone_seconds:.3f} s after the kill"
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
        lambda: all(wire.modules_count == 1 for wire in wires),
        "both clients' hellos and module lists",
    )
    for wire in wires:
        hello_check(wire, wire.hellos[0])
    first_pid, second_pid = first.hellos[0]["pid"], second.hellos[0]["pid"]
    if first_pid == second_pid:
        raise CheckFailed(f"both clients' hellos have pid {first_pid}")
    for wire in wires:
        wire.run_send("stdin.py", [])
    wires_wait(
        wires,
        lambda: all(
            wire.runs and b"\n" in wire.runs[-1].streams["stdout"]
            for wire in wires
        ),
        "stdin.py's first line on both clients",
    )
    module_pids: list[int] = []
    for wire, word in ((first, "first"), (second, "second")):
        run = wire.runs[-1]
        pid = run.started["pid"]
        module_pids.append(pid)
        if process_parent(pid) != wire.hellos[0]["pid"]:
            raise CheckFailed(
                f"the {word} client's stdin.py, pid {pid}, isn't its"
                " program's child"
            )
        wire.in_send(f"{word}\n".encode())
        wire.type_send("eof")
    wires_wait(
        wires,
        lambda: all(wire.runs[-1].modules is not None for wire in wires),
        "both clients' stdin.py exits",
    )
    for wire, word, pid in (
        (first, "first", first_pid),
        (second, "second", second_pid),
    ):
        run = wire.runs[-1]
        expected = f"ready {run.started['pid']} {pid}\ngot {word}\neof 1\n"
        if run.text("stdout") != expected:
            raise CheckFailed(
                f"the {word} client's stdin.py printed"
                f" {run.text('stdout')!r} where {expected!r} was due"
            )
        run_exit_check(run, 0)
    first_seconds = session_close(first, [second], first_pid)
    modules_before = second.modules_count
    second.type_send("list")
    second.wait(
        lambda: second.modules_count > modules_before, "the second's list"
    )
    hello_check(second, second.hellos[0])
    second_seconds = session_close(second, [], second_pid)
    return (
        f"hellos with pids {first_pid} and {second_pid}; stdin.py ran on"
        f" both at once as pids {module_pids[0]} and {module_pids[1]}, each"
        " its own program's child, and each echoed only its own client's"
        f" line; the first closed with {_WEBSOCKET_CLOSE_NORMAL} answered"
        f" with {first.close_code}, pid {first_pid} killed with signal"
        f" {int(signal.SIGHUP)} (SIGHUP) and gone {first_seconds:.3f} s after"
        f" the close; then the second answered list with pid {second_pid}"
        f" still running; the second closed with {_WEBSOCKET_CLOSE_NORMAL}"
        f" answered with {second.close_code}, gone {second_seconds:.3f} s"
        " after the close"
    )


# Updates the bootstrapper from a module and restarts it. Returns a summary.
def rung_update(wire: Wire) -> str:
    bootstrap_path = wire.ttyd.command[1]
    with open(bootstrap_path, "rb") as bootstrap_file:
        updated = bootstrap_file.read() + _UPDATE_LINE
    digest = hashlib.sha256(updated).hexdigest()
    wire.put_send("update.py", _UPDATE_SOURCE)
    run = run_wait(wire, "update.py", [])
    if run.text("stdout") != f"sha256 {digest}\n":
        raise CheckFailed(f"update.py printed {run.text('stdout')!r}")
    run_exit_check(run, 0)
    modules_before = wire.modules_count
    wire.type_send("restart")
    wire.wait(
        lambda: len(wire.hellos) == 2 and wire.modules_count > modules_before,
        "the second hello and its module list",
    )
    first, second = wire.hellos
    hello_check(wire, second)
    if second["pid"] != first["pid"] or second["started"] <= first["started"]:
        raise CheckFailed(f"restart's hello {second} after hello {first}")
    if second["sha256"] != digest:
        raise CheckFailed(
            f"restart's hello has sha256 {second['sha256']}, not the updated"
            f" file's {digest}"
        )
    after = run_wait(wire, "report.py", [])
    run_exit_check(after, 0)
    return (
        f"update.py appended {len(_UPDATE_LINE)} bytes to"
        f" {os.path.basename(bootstrap_path)} and printed its sha256"
        f" {digest[:12]}, equal to this client's; restart: hello 2 with the"
        f" same pid {second['pid']}, started"
        f" {second['started'] - first['started']:.3f} s after hello 1, sha256"
        " equal to the updated file's; report.py then ran as pid"
        f" {after.started['pid']}, exit code 0"
    )


# Fails unless the run exited with the code and a module list followed.
def run_exit_check(run: Run, code: int) -> None:
    exit_message = cast(dict[str, Any], run.exit)
    if exit_message["code"] != code or run.modules is None:
        raise CheckFailed(
            f"{run.started['name']}'s exit is {exit_message} where code"
            f" {code} was due"
        )


# Returns the pids of every module the wire ran.
def run_pids(wire: Wire) -> set[int]:
    return {run.started["pid"] for run in wire.runs}


# Runs the module and returns its run once its first line has come.
def run_ready(wire: Wire, name: str) -> tuple[Run, str]:
    runs_before = len(wire.runs)
    wire.run_send(name, [])
    wire.wait(
        lambda: (
            len(wire.runs) > runs_before
            and b"\n" in wire.runs[-1].streams["stdout"]
        ),
        f"{name}'s first line",
    )
    run = wire.runs[-1]
    return run, run.text("stdout").split("\n")[0]


# Runs the module and returns its run once the list after its exit came.
def run_wait(wire: Wire, name: str, args: list[str]) -> Run:
    runs_before = len(wire.runs)
    wire.run_send(name, args)
    wire.wait(
        lambda: (
            len(wire.runs) > runs_before and wire.runs[-1].modules is not None
        ),
        f"{name}'s exit and the module list after it",
    )
    return wire.runs[-1]


# Fails unless the saved file holds what was put, and the list agrees.
def saved_check(wire: Wire, saved: dict[str, Any]) -> None:
    modules: str = wire.hellos[-1]["modules"]
    path = os.path.join(modules, saved["name"])
    with open(path, "rb") as module_file:
        data = module_file.read()
    on_disk = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    listed = [
        entry for entry in wire.modules if entry["name"] == saved["name"]
    ]
    if listed != [{"name": saved["name"], **on_disk}] or any(
        saved[name] != value for name, value in on_disk.items()
    ):
        raise CheckFailed(
            f"saved {saved}, listed {listed}, where {path} has {on_disk}"
        )


# Closes the wire and returns the seconds until all its processes are gone.
def session_close(wire: Wire, others: list[Wire], parent: int) -> float:
    pid = wire.hellos[-1]["pid"]
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
    ended = (
        rf"process (killed with signal|exited with code) (\d+), pid: {pid}$"
    )
    found = wire.ttyd.line_wait(
        re.compile(ended), 0, "ttyd's log of the program's end"
    )
    if found.group(1, 2) != ("killed with signal", str(int(signal.SIGHUP))):
        raise CheckFailed(f"ttyd logged: {found.string}")
    return processes_wait(wire, {pid, *run_pids(wire)}, pid, parent, closed_at)


# Exits with 128 plus the signal's number.
def signal_exit(signal_number: int, frame: types.FrameType | None) -> None:
    sys.exit(128 + signal_number)


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


# Handles what ttyd sends on each wire until done answers True.
def wires_wait(wires: list[Wire], done: Callable[[], bool], what: str) -> None:
    ttyd = wires[0].ttyd
    while not done():
        readers: list[socket.socket | int] = [
            wire.sock for wire in wires if not wire.ended
        ]
        if not ttyd.stderr_ended:
            readers.append(ttyd.fd)
        readable, _, _ = select.select(
            readers, [], [], remaining(ttyd.deadline, what)
        )
        if ttyd.fd in readable:
            ttyd.stderr_read()
        for wire in wires:
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
                    ("hello", rung_hello),
                    ("put", rung_put),
                    ("run", rung_run),
                    ("stdin", rung_stdin),
                    ("kill", rung_kill),
                    ("big put", rung_big_put),
                    ("lines", rung_lines),
                    ("update", rung_update),
                    ("close", rung_close),
                ):
                    print(f"{rung}: {check(wire)}", flush=True)
                # Last, as it ends ttyd.
                for rung, ttyd_check in (
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
