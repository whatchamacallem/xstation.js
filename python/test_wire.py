#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The wire test: starts Linux ttyd, from a checkout of ttyd beside this
# project, serving bootstrap.html and running bootstrap.py --session, then
# speaks ttyd's protocol to the program as the page does, rung by rung:
# over one WebSocket, then over two at once, and last over one while ttyd
# is killed. It stops at the first failed check with the
# measurement that failed and exits 1; on success it prints one line per
# rung and exits 0. Standard library only:
#
#     python3 python/test_wire.py

from __future__ import annotations

import argparse
import base64
import collections
import contextlib
import hashlib
import http.client
import json
import os
import re
import select
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Generator
from types import FrameType
from typing import Any, cast

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# What ttyd runs for each connection, from _PYTHON_PATH.
_BOOTSTRAP_ARGUMENTS = ["python3", "bootstrap.py", "--session"]

# vmstat's lines to receive before cancelling it.
_CANCEL_AFTER_LINES = 5

# The terminal size the first message gives.
_COLUMNS = 80
_ROWS = 24

_CREDENTIAL = "user:pass"

# 1 MiB of UTF-8: units of 23 random ASCII characters and three of 2, 3
# and 4 bytes, 32 bytes a unit.
_DIGEST_ASCII_PER_UNIT = 23
_DIGEST_UNITS = 32768
_DIGEST_WIDE_TEXT = "\u00e9\u4e2d\U0001f600"

_INDEX_PATH = os.path.join(_PYTHON_PATH, "bootstrap.html")

_LISTENING_PATTERN = re.compile(r" Listening on port: (\d+)$")

_MADE_UP_PATH = "/other.js"

# The fields of each message the program sends, by type.
_MESSAGE_FIELDS: dict[str, dict[str, type[object]]] = {
    "count": {
        "received_messages": int,
        "received_bytes": int,
        "sent_messages": int,
        "sent_bytes": int,
    },
    "digest": {"id": int, "bytes": int, "characters": int, "sha256": str},
    "exit": {"id": int, "code": int, "lines": int, "cancelled": bool},
    "hello": {"pid": int, "python": str, "columns": int, "rows": int},
    "line": {"id": int, "n": int, "text": str},
    "pong": {"id": int},
    "reply": {"id": int, "text": str},
    "size": {"columns": int, "rows": int},
    "started": {"id": int, "pid": int, "argv": list},
    "stat": {
        "hostname": str,
        "kernel": str,
        "uptime": float,
        "loadavg": list,
        "mem_available_kib": int,
        "pid": int,
    },
    "tick": {"n": int, "time": float},
}

# Holds 2, 3 and 4 byte characters; the split lands inside the last.
_NON_ASCII_TEXT = "na\u00efve \u65e5\u672c\u8a9e \U0001f600 \u00e9t\u00e9"
_NON_ASCII_SPLIT_CHARACTER = "\U0001f600"

# The seq line at which PAUSE goes, and how long until RESUME follows.
_PAUSE_AT_LINE = 25000
_RESUME_AFTER_SECONDS = 1

_PING_COUNT = 10
_PING_SECONDS = 1

_POLL_SECONDS = 0.05

_RESIZE_COLUMNS = 100
_RESIZE_ROWS = 30

_RUN_TIMEOUT_SECONDS = 120

_SEQ_LINES = 100000

_STAT_APART_SECONDS = 5

_STOP_WAIT_SECONDS = 5

_TICK_COUNT = 10

_TTYD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(_PYTHON_PATH)), "ttyd", "build", "ttyd"
)
_TTYD_OPTIONS = [
    "--writable",
    "--check-origin",
    "--cwd",
    _PYTHON_PATH,
    "--index",
    _INDEX_PATH,
]

# The ticks to receive on each of two clients at once.
_TWO_CLIENTS_TICKS = 3

_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_WEBSOCKET_OPCODE_BINARY = 0x2
_WEBSOCKET_OPCODE_CLOSE = 0x8
_WEBSOCKET_OPCODE_CONTINUATION = 0x0
_WEBSOCKET_OPCODE_PING = 0x9
_WEBSOCKET_OPCODE_PONG = 0xA
_WEBSOCKET_CLOSE_NORMAL = 1000


class CheckFailed(Exception):
    pass


class Ttyd:
    def __init__(self, options: list[str], version: str, deadline: float):
        self.version = version
        self.deadline = deadline
        # ttyd's stderr lines so far, and what follows the last of them.
        self.lines: list[str] = []
        self.partial = b""
        self.port = 0
        self.killed = False
        self.stderr_ended = False
        self.fd, write_fd = os.pipe()
        try:
            # In a session of its own, so a ^C reaches only this script.
            self.process = subprocess.Popen(
                [
                    _TTYD_PATH,
                    "--port",
                    "0",
                    "--interface",
                    "127.0.0.1",
                    *options,
                    *_BOOTSTRAP_ARGUMENTS,
                ],
                cwd=_PYTHON_PATH,
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

    # Answers the match of the first line from the start'th on that the
    # pattern finds, reading ttyd's stderr until one comes.
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

    def stop(self) -> None:
        # The session is gone once all of it has exited; until ttyd is
        # waited for, its pid is its own.
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
        # Set before ttyd is made to end the connection, which is then
        # recorded, not failed.
        self.end_expected = False
        # Set once ttyd's end of the TCP connection is read.
        self.ended = False
        self.ttyd_messages = 0
        self.ttyd_pings = 0
        self.title = ""
        self.preferences: Any = None
        # The output after the last whole line.
        self.stream = b""
        self.hello: dict[str, Any] = {}
        # The client's figures for count: lines and bytes, less newlines.
        self.sent_lines = 0
        self.sent_bytes = 0
        self.received_lines = 0
        self.received_bytes = 0
        self.tick_n = 0
        self.tick_times: list[float] = []
        self.ping_id = 0
        self.pings: collections.deque[tuple[int, float]] = collections.deque()
        self.round_trips: list[float] = []
        self.say_id = 0
        self.says: collections.deque[int] = collections.deque()
        self.replies: dict[int, str] = {}
        self.started: dict[int, dict[str, Any]] = {}
        self.lines: dict[int, list[str]] = {}
        self.exits: dict[int, dict[str, Any]] = {}
        # Called with the say's id and n of each line message.
        self.line_watch: Callable[[int, int], None] | None = None
        self.digest_id = 0
        self.digests_asked: set[int] = set()
        self.digests: dict[int, dict[str, Any]] = {}
        self.stats_asked = 0
        self.stats: list[dict[str, Any]] = []
        self.sizes_asked = 0
        self.sizes: list[dict[str, Any]] = []
        # The client's sent lines and bytes as each count went.
        self.counts_asked: collections.deque[tuple[int, int]] = (
            collections.deque()
        )
        self.counts: list[dict[str, Any]] = []
        self.timers: list[tuple[float, Callable[[], None]]] = []
        self.handlers: dict[str, Callable[[dict[str, Any]], None]] = {
            "count": self.count_take,
            "digest": self.digest_take,
            "exit": self.exit_take,
            "hello": self.hello_take,
            "line": self.line_take,
            "pong": self.pong_take,
            "reply": self.reply_take,
            "size": self.size_take,
            "started": self.started_take,
            "stat": self.stat_take,
            "tick": self.tick_take,
        }
        self.frames_handle()

    def close_send(self) -> None:
        self.close_sent = True
        self.frame_send(
            _WEBSOCKET_OPCODE_CLOSE, _WEBSOCKET_CLOSE_NORMAL.to_bytes(2, "big")
        )

    def count_send(self) -> None:
        self.line_send({"type": "count"})
        self.counts_asked.append((self.sent_lines, self.sent_bytes))

    # The program's figures leave out this reply and count the request.
    def count_take(self, message: dict[str, Any]) -> None:
        if not self.counts_asked:
            raise CheckFailed(f"count came unasked: {message}")
        sent_lines, sent_bytes = self.counts_asked.popleft()
        figures = {
            "received_messages": sent_lines,
            "received_bytes": sent_bytes,
            "sent_messages": self.received_lines,
            "sent_bytes": self.received_bytes,
        }
        if any(message[name] != value for name, value in figures.items()):
            raise CheckFailed(
                f"the program's count {message} differs from the client's"
                f" {figures}"
            )
        self.counts.append(message)

    def digest_send(self, text: str) -> int:
        self.digest_id += 1
        self.digests_asked.add(self.digest_id)
        self.line_send({"type": "digest", "id": self.digest_id, "text": text})
        return self.digest_id

    def digest_take(self, message: dict[str, Any]) -> None:
        if message["id"] not in self.digests_asked - self.digests.keys():
            raise CheckFailed(f"digest came unasked: {message}")
        self.digests[message["id"]] = message

    def exit_take(self, message: dict[str, Any]) -> None:
        say_id = message["id"]
        if say_id not in self.started or say_id in self.exits:
            raise CheckFailed(f"exit for no running command: {message}")
        if message["lines"] != len(self.lines[say_id]):
            raise CheckFailed(
                f"exit says {message['lines']} lines where"
                f" {len(self.lines[say_id])} line messages came: {message}"
            )
        self.exits[say_id] = message

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

    def hello_take(self, message: dict[str, Any]) -> None:
        if self.hello:
            raise CheckFailed(f"a second hello came: {message}")
        self.hello = message

    # Handles one line of the program's output.
    def line_handle(self, line: bytes) -> None:
        message = message_parse(line)
        if not self.hello and message["type"] != "hello":
            raise CheckFailed(
                f"the program's first line isn't hello: {line!r}"
            )
        self.handlers[message["type"]](message)
        self.received_lines += 1
        self.received_bytes += len(line)

    # Sends a line of input to the program as one ttyd message.
    def line_send(self, message: dict[str, Any]) -> None:
        line = self.line_count(message)
        self.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + line)

    # Counts a line of input as sent. Answers it with its newline.
    def line_count(self, message: dict[str, Any]) -> bytes:
        line = json.dumps(message, ensure_ascii=False).encode()
        self.sent_lines += 1
        self.sent_bytes += len(line)
        return line + b"\n"

    def line_take(self, message: dict[str, Any]) -> None:
        say_id = message["id"]
        if say_id not in self.started or say_id in self.exits:
            raise CheckFailed(f"line for no running command: {message}")
        lines = self.lines[say_id]
        if message["n"] != len(lines) + 1:
            raise CheckFailed(
                f"line {message['n']} came after line {len(lines)}: {message}"
            )
        lines.append(message["text"])
        if self.line_watch:
            self.line_watch(say_id, message["n"])

    def ping_send(self) -> None:
        self.ping_id += 1
        self.pings.append((self.ping_id, time.monotonic()))
        self.line_send({"type": "ping", "id": self.ping_id})

    def pong_take(self, message: dict[str, Any]) -> None:
        if not self.pings:
            raise CheckFailed(f"pong came with no ping outstanding: {message}")
        ping_id, sent_at = self.pings.popleft()
        if message["id"] != ping_id:
            raise CheckFailed(
                f"pong {message['id']} came when the oldest outstanding ping"
                f" was {ping_id}"
            )
        self.round_trips.append(time.monotonic() - sent_at)

    def reply_take(self, message: dict[str, Any]) -> None:
        if not self.says or message["id"] != self.says[0]:
            raise CheckFailed(
                f"reply {message['id']} came when the oldest unanswered say"
                f" was {self.says[0] if self.says else 'none'}: {message}"
            )
        self.says.popleft()
        self.replies[message["id"]] = message["text"]

    def resize_send(self, columns: int, rows: int) -> None:
        self.sizes_asked += 1
        self.frame_send(
            _WEBSOCKET_OPCODE_BINARY,
            b"1" + json.dumps({"columns": columns, "rows": rows}).encode(),
        )

    # Counts a say as sent and awaiting its reply. Answers its id and line.
    def say_line(self, text: str) -> tuple[int, bytes]:
        self.say_id += 1
        self.says.append(self.say_id)
        line = self.line_count(
            {"type": "say", "id": self.say_id, "text": text}
        )
        return self.say_id, line

    def say_send(self, text: str) -> int:
        say_id, line = self.say_line(text)
        self.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + line)
        return say_id

    def size_send(self) -> None:
        self.sizes_asked += 1
        self.line_send({"type": "size"})

    def size_take(self, message: dict[str, Any]) -> None:
        if len(self.sizes) == self.sizes_asked:
            raise CheckFailed(f"size came unasked: {message}")
        self.sizes.append(message)

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

    def started_take(self, message: dict[str, Any]) -> None:
        say_id = message["id"]
        if say_id not in self.replies or say_id in self.started:
            raise CheckFailed(f"started for no answered say: {message}")
        if not all(type(word) is str for word in message["argv"]):
            raise CheckFailed(f"started's argv isn't all strings: {message}")
        self.started[say_id] = message
        self.lines[say_id] = []

    def stat_send(self) -> None:
        self.stats_asked += 1
        self.line_send({"type": "stat"})

    def stat_take(self, message: dict[str, Any]) -> None:
        if len(self.stats) == self.stats_asked:
            raise CheckFailed(f"stat came unasked: {message}")
        loadavg = message["loadavg"]
        if len(loadavg) != 3 or any(
            type(load) is not float for load in loadavg
        ):
            raise CheckFailed(f"stat's loadavg isn't 3 floats: {message}")
        self.stats.append(message)

    def tick_take(self, message: dict[str, Any]) -> None:
        if message["n"] != self.tick_n + 1:
            raise CheckFailed(f"tick {message['n']} came after {self.tick_n}")
        self.tick_n = message["n"]
        self.tick_times.append(time.monotonic())

    def timer_add(self, due: float, callback: Callable[[], None]) -> None:
        self.timers.append((due, callback))
        self.timers.sort(key=lambda timer: timer[0])

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
                self.preferences = json.loads(message[1:])
            except json.JSONDecodeError as error:
                raise CheckFailed(
                    f"{self.ttyd.version}'s preferences aren't JSON: {error}:"
                    f" {message!r}"
                ) from error
        else:
            *lines, self.stream = (self.stream + message[1:]).split(b"\r\n")
            for line in lines:
                self.line_handle(line)

    # Reads and handles what ttyd sends, firing the timers that come due,
    # until done answers True.
    def wait(self, done: Callable[[], bool], what: str) -> None:
        wires_wait([self], done, what)


# Fails unless the reply to `echo <text>` is what the brief's echo gives.
def echo_check(wire: Wire, say_id: int, text: str) -> None:
    expected = (
        f"{text}\n{len(text)} characters, {len(text.encode())} bytes in UTF-8"
    )
    if wire.replies[say_id] != expected:
        raise CheckFailed(
            f"echo's reply is {wire.replies[say_id]!r}, not {expected!r}"
        )


# Fails unless hello gives the size the first message sent and its pid runs
# bootstrap.py --session.
def hello_check(wire: Wire) -> None:
    hello = wire.hello
    if (hello["columns"], hello["rows"]) != (_COLUMNS, _ROWS):
        raise CheckFailed(
            f"hello {hello} after a first message of {_COLUMNS}x{_ROWS}"
        )
    with open(f"/proc/{hello['pid']}/cmdline", "rb") as cmdline_file:
        cmdline = cmdline_file.read().split(b"\0")[:-1]
    if cmdline != [argument.encode() for argument in _BOOTSTRAP_ARGUMENTS]:
        raise CheckFailed(f"hello's pid {hello['pid']} runs {cmdline}")


# Answers ttyd's status and body for a GET of the path.
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


# Answers the line's JSON object, failing unless it is of a known type with
# exactly that type's fields, each of its type.
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


# Answers the pids here that are watched, in the session or children of
# the parent, sorted.
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


# Answers the seconds left before the overall timeout, failing once past.
def remaining(deadline: float, what: str) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise CheckFailed(
            f"gave up after {_RUN_TIMEOUT_SECONDS} s waiting for {what}"
        )
    return left


def rung_concurrent(wire: Wire) -> str:
    pongs_before = len(wire.round_trips)
    ticks_before = wire.tick_n
    start = time.monotonic()
    for index in range(_PING_COUNT):
        wire.timer_add(start + index * _PING_SECONDS, wire.ping_send)
    run_id = wire.say_send("run vmstat 1")
    wire.wait(
        lambda: (
            run_id in wire.lines
            and len(wire.lines[run_id]) >= _CANCEL_AFTER_LINES
        ),
        f"{_CANCEL_AFTER_LINES} lines of vmstat",
    )
    cancel_id = wire.say_send("cancel")
    wire.wait(lambda: run_id in wire.exits, "vmstat's exit")
    if cancel_id not in wire.replies:
        raise CheckFailed("vmstat's exit came before the cancel's reply")
    ticks_at_exit = wire.tick_n
    wire.wait(
        lambda: (
            wire.tick_n > ticks_at_exit
            and len(wire.round_trips) == pongs_before + _PING_COUNT
        ),
        f"a tick after vmstat's exit and {_PING_COUNT} pongs",
    )
    counts_before = len(wire.counts)
    wire.count_send()
    wire.wait(lambda: len(wire.counts) > counts_before, "count")
    started = wire.started[run_id]
    run_check(wire, run_id, ["vmstat", "1"])
    if wire.replies[cancel_id] != f"cancelled pid {started['pid']}":
        raise CheckFailed(
            f"cancel's reply is {wire.replies[cancel_id]!r}, not"
            f" 'cancelled pid {started['pid']}'"
        )
    exit_message = wire.exits[run_id]
    if (
        exit_message["code"] != -signal.SIGTERM
        or not exit_message["cancelled"]
    ):
        raise CheckFailed(
            f"vmstat's exit isn't by SIGTERM and cancelled: {exit_message}"
        )
    count = wire.counts[-1]
    trips = wire.round_trips[pongs_before:]
    return (
        f"vmstat 1 as pid {started['pid']} streamed"
        f" {len(wire.lines[run_id])} lines while {_PING_COUNT} pings on the"
        f" {_PING_SECONDS} s timer got {len(trips)} pongs in order, round"
        f" trip {min(trips) * 1000:.1f} to {max(trips) * 1000:.1f} ms;"
        f" cancel: exit code {exit_message['code']} cancelled, lines"
        f" {exit_message['lines']} equal to the line messages received;"
        f" ticks {ticks_before + 1} to {wire.tick_n} consecutive,"
        f" {wire.tick_n - ticks_at_exit} after the exit; count received"
        f" {count['received_messages']} messages,"
        f" {count['received_bytes']} bytes, sent {count['sent_messages']}"
        f" messages, {count['sent_bytes']} bytes, equal to the client's"
    )


def rung_control(wire: Wire) -> str:
    wire.resize_send(_RESIZE_COLUMNS, _RESIZE_ROWS)
    wire.wait(lambda: len(wire.sizes) == wire.sizes_asked, "size")
    wire.size_send()
    wire.wait(lambda: len(wire.sizes) == wire.sizes_asked, "size's reply")
    for size in wire.sizes[-2:]:
        if (size["columns"], size["rows"]) != (_RESIZE_COLUMNS, _RESIZE_ROWS):
            raise CheckFailed(
                f"size {size} after a resize to {_RESIZE_COLUMNS}x"
                f"{_RESIZE_ROWS}"
            )
    stats_before = len(wire.stats)
    wire.stat_send()
    wire.timer_add(time.monotonic() + _STAT_APART_SECONDS, wire.stat_send)
    wire.wait(lambda: len(wire.stats) == stats_before + 2, "two stats")
    first, second = wire.stats[-2:]
    if second["uptime"] <= first["uptime"]:
        raise CheckFailed(
            f"uptime went from {first['uptime']} to {second['uptime']} in"
            f" {_STAT_APART_SECONDS} s"
        )
    if not first["pid"] == second["pid"] == wire.hello["pid"]:
        raise CheckFailed(
            f"stat's pid went {first['pid']}, {second['pid']} where hello's"
            f" was {wire.hello['pid']}"
        )
    return (
        f"resize to {_RESIZE_COLUMNS}x{_RESIZE_ROWS}: size after SIGWINCH and"
        " on request both"
        f" {_RESIZE_COLUMNS}x{_RESIZE_ROWS}; stat {_STAT_APART_SECONDS} s"
        f" apart by the client's timer: uptime {first['uptime']} to"
        f" {second['uptime']} s, pid {second['pid']} both times as in hello;"
        f" host {second['hostname']}, kernel {second['kernel']}, loadavg"
        f" {second['loadavg']}, MemAvailable {second['mem_available_kib']}"
        " KiB"
    )


def rung_end(wire: Wire) -> str:
    seconds = session_close(wire, [], wire.ttyd.process.pid)
    commands = sorted(started["pid"] for started in wire.started.values())
    return (
        f"close {_WEBSOCKET_CLOSE_NORMAL} answered with"
        f" {wire.close_code}; ttyd logged the program, pid"
        f" {wire.hello['pid']}, killed with signal {int(signal.SIGHUP)}"
        " (SIGHUP); it, its session and the commands it ran (pids"
        f" {commands}) were gone and ttyd had no child {seconds:.3f} s after"
        f" the close; {wire.ttyd_pings} ttyd pings answered"
    )


def rung_framing(wire: Wire) -> str:
    wide = "".join(str(index % 10) for index in range(3 * _COLUMNS))
    wide_id = wire.say_send(f"echo {wide}")
    plain_id = wire.say_send(f"echo {_NON_ASCII_TEXT}")
    # The same line split inside a character, as two ttyd messages, then as
    # one ttyd message in two WebSocket frames.
    two_id, line = wire.say_line(f"echo {_NON_ASCII_TEXT}")
    split = line.index(_NON_ASCII_SPLIT_CHARACTER.encode()) + 2
    split_of = len(line)
    wire.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + line[:split])
    wire.frame_send(_WEBSOCKET_OPCODE_BINARY, b"0" + line[split:])
    fragmented_id, line = wire.say_line(f"echo {_NON_ASCII_TEXT}")
    fragment_split = line.index(_NON_ASCII_SPLIT_CHARACTER.encode()) + 2
    wire.frame_send(
        _WEBSOCKET_OPCODE_BINARY, b"0" + line[:fragment_split], False
    )
    wire.frame_send(_WEBSOCKET_OPCODE_CONTINUATION, line[fragment_split:])
    wire.wait(lambda: not wire.says, "the echoes' replies")
    echo_check(wire, wide_id, wide)
    for say_id in (plain_id, two_id, fragmented_id):
        echo_check(wire, say_id, _NON_ASCII_TEXT)

    ascii_text = base64.b64encode(
        os.urandom(_DIGEST_UNITS * _DIGEST_ASCII_PER_UNIT * 3 // 4)
    ).decode()
    text = "".join(
        ascii_text[index : index + _DIGEST_ASCII_PER_UNIT] + _DIGEST_WIDE_TEXT
        for index in range(
            0, _DIGEST_UNITS * _DIGEST_ASCII_PER_UNIT, _DIGEST_ASCII_PER_UNIT
        )
    )
    encoded = text.encode()
    digest_id = wire.digest_send(text)
    wire.wait(lambda: digest_id in wire.digests, "digest")
    digest = wire.digests[digest_id]
    expected = {
        "id": digest_id,
        "bytes": len(encoded),
        "characters": len(text),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
    if any(digest[name] != value for name, value in expected.items()):
        raise CheckFailed(f"digest {digest} where the client has {expected}")

    seq_start = time.monotonic()
    seq_id = wire.say_send(f"run seq 1 {_SEQ_LINES}")
    # Lines received when PAUSE went and when RESUME went.
    marks: list[int] = []

    def resume() -> None:
        wire.frame_send(_WEBSOCKET_OPCODE_BINARY, b"3")
        marks.append(len(wire.lines[seq_id]))

    def line_seen(say_id: int, n: int) -> None:
        if say_id == seq_id and n == _PAUSE_AT_LINE:
            wire.frame_send(_WEBSOCKET_OPCODE_BINARY, b"2")
            marks.append(n)
            wire.timer_add(time.monotonic() + _RESUME_AFTER_SECONDS, resume)

    wire.line_watch = line_seen
    wire.wait(
        lambda: seq_id in wire.exits and len(marks) == 2,
        "seq's exit and the RESUME",
    )
    seq_seconds = time.monotonic() - seq_start
    wire.line_watch = None
    run_check(wire, seq_id, ["seq", "1", str(_SEQ_LINES)])
    lines = wire.lines[seq_id]
    if len(lines) != _SEQ_LINES:
        raise CheckFailed(f"seq streamed {len(lines)} lines, not {_SEQ_LINES}")
    for n, line_text in enumerate(lines, 1):
        if line_text != str(n):
            raise CheckFailed(f"seq's line {n} is {line_text!r}")
    exit_message = wire.exits[seq_id]
    if exit_message["code"] != 0 or exit_message["cancelled"]:
        raise CheckFailed(f"seq's exit is {exit_message}")
    return (
        f"echo of {len(wide)} characters ({_COLUMNS} columns) came whole;"
        f" {_NON_ASCII_TEXT.encode('unicode_escape').decode()} echoed equal,"
        f" also split at byte {split} of {split_of}, inside"
        f" U+{ord(_NON_ASCII_SPLIT_CHARACTER):04X}, across two ttyd messages"
        " and across two frames of one WebSocket message; digest of"
        f" {len(encoded)} bytes ({len(text)} characters) sha256 equal;"
        f" seq {_SEQ_LINES} lines in {seq_seconds:.2f} s, n and text"
        f" consecutive, exit code 0 lines {exit_message['lines']}; PAUSE"
        f" went at line {marks[0]} and RESUME {_RESUME_AFTER_SECONDS} s"
        f" later at line {marks[1]}, {marks[1] - marks[0]} lines arriving"
        f" between: PAUSE is inert in {wire.ttyd.version} (its"
        " pty_pause returns at once), so this shows only that none went"
        " missing, not that pausing works"
    )


def rung_round_trip(wire: Wire) -> str:
    pongs_before = len(wire.round_trips)
    ticks_before = wire.tick_n
    start = time.monotonic()
    for index in range(_PING_COUNT):
        wire.timer_add(start + index * _PING_SECONDS, wire.ping_send)
    wire.wait(
        lambda: len(wire.round_trips) == pongs_before + _PING_COUNT,
        f"{_PING_COUNT} pongs",
    )
    if wire.tick_n == ticks_before:
        raise CheckFailed(f"no tick came during the {_PING_COUNT} pings")
    trips = wire.round_trips[pongs_before:]
    return (
        f"{_PING_COUNT} pings on the client's {_PING_SECONDS} s timer,"
        f" {len(trips)} pongs with the same ids in order, round trip"
        f" {min(trips) * 1000:.1f} to {max(trips) * 1000:.1f} ms; ticks"
        f" {ticks_before + 1} to {wire.tick_n} consecutive meanwhile; all"
        f" {wire.received_lines} lines so far JSON of a known type, none"
        " echoed"
    )


# Fails unless the say ran the command: its reply names the started
# message's pid, and that message holds the argv.
def run_check(wire: Wire, say_id: int, argv: list[str]) -> None:
    started = wire.started[say_id]
    reply = wire.replies[say_id]
    if started["argv"] != argv:
        raise CheckFailed(f"started {started} for argv {argv}")
    if not reply.startswith("started ") or not reply.endswith(
        f" as pid {started['pid']}"
    ):
        raise CheckFailed(f"run's reply {reply!r} for started {started}")


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
        ttyd.version,
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
        f"GET / 200, {len(page)} bytes, sha256 equal to"
        f" {os.path.basename(_INDEX_PATH)}'s;"
        f" /token {token_body.decode()}; {_MADE_UP_PATH} 404; with"
        " --credential:"
        " / 401 without it and 200 with it, /ws closed unanswered without"
        " it and 101 with it"
    )


def rung_ticks(wire: Wire) -> str:
    wire.start_send()
    wire.wait(lambda: bool(wire.hello), "hello")
    hello_check(wire)
    hello = wire.hello
    wire.wait(lambda: wire.tick_n == _TICK_COUNT, f"{_TICK_COUNT} ticks")
    gaps = [
        later - earlier
        for earlier, later in zip(wire.tick_times, wire.tick_times[1:])
    ]
    return (
        f"title {wire.title!r}, preferences"
        f" {json.dumps(wire.preferences)}, hello pid {hello['pid']} python"
        f" {hello['python']} {hello['columns']}x{hello['rows']} as sent;"
        f" ticks 1 to {wire.tick_n} consecutive, {min(gaps):.3f} to"
        f" {max(gaps):.3f} s apart"
    )


def rung_ttyd_killed(ttyd: Ttyd) -> str:
    wire = websocket_open(ttyd, {})
    wire.start_send()
    wire.wait(lambda: wire.tick_n > 0, "the first tick")
    hello_check(wire)
    pid = wire.hello["pid"]
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
    while left := processes_left({pid}, pid, pid):
        remaining(ttyd.deadline, f"processes {left} to end")
        time.sleep(_POLL_SECONDS)
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
        f"SIGKILL to {ttyd.version} after tick {wire.tick_n} from pid {pid}"
        f" reached its client: {ended_seconds:.4f} s after the kill {end};"
        f" ttyd exited with {status}; the program, its session"
        " and its children were gone"
        f" {time.monotonic() - killed_at:.3f} s after the kill"
    )


def rung_two_clients(ttyd: Ttyd) -> str:
    first = websocket_open(ttyd, {})
    second = websocket_open(ttyd, {})
    wires = [first, second]
    for wire in wires:
        wire.start_send()
    wires_wait(
        wires,
        lambda: all(wire.tick_n >= _TWO_CLIENTS_TICKS for wire in wires),
        f"{_TWO_CLIENTS_TICKS} ticks on each of two clients",
    )
    for wire in wires:
        hello_check(wire)
    first_pid, second_pid = first.hello["pid"], second.hello["pid"]
    if first_pid == second_pid:
        raise CheckFailed(f"both clients' hellos have pid {first_pid}")
    say_id = first.say_send(f"echo {_NON_ASCII_TEXT}")
    wires_wait(wires, lambda: not first.says, "the first client's reply")
    echo_check(first, say_id, _NON_ASCII_TEXT)
    for wire in wires:
        wire.count_send()
    wires_wait(
        wires,
        lambda: not any(wire.counts_asked for wire in wires),
        "both clients' counts",
    )
    first_seconds = session_close(first, [second], first_pid)
    # A tick after the pong to a ping sent once the first program was gone.
    pongs_before = len(second.round_trips)
    second.ping_send()
    second.wait(
        lambda: len(second.round_trips) > pongs_before, "the second's pong"
    )
    ticks_at_pong = second.tick_n
    second.wait(
        lambda: second.tick_n > ticks_at_pong, "a tick after the second's pong"
    )
    hello_check(second)
    second_seconds = session_close(second, [], second_pid)
    first_count, second_count = first.counts[-1], second.counts[-1]
    return (
        f"hellos with pids {first_pid} and {second_pid}, each running"
        f" {' '.join(_BOOTSTRAP_ARGUMENTS)}; echo on the first replied"
        f" there, {len(second.replies)} replies on the second; counts equal"
        " to each client's: first received"
        f" {first_count['received_messages']} messages and sent"
        f" {first_count['sent_messages']}, second received"
        f" {second_count['received_messages']} and sent"
        f" {second_count['sent_messages']}; the first closed with"
        f" {_WEBSOCKET_CLOSE_NORMAL} answered with {first.close_code}, ttyd"
        f" logged pid {first_pid} killed with signal {int(signal.SIGHUP)}"
        f" (SIGHUP), gone {first_seconds:.3f} s after the close, its ticks 1"
        f" to {first.tick_n} consecutive; then the second's pong to a ping"
        f" and tick {ticks_at_pong + 1} after it, pid {second_pid} still"
        f" running; the second closed with {_WEBSOCKET_CLOSE_NORMAL}"
        f" answered with {second.close_code}, pid {second_pid} killed with"
        f" signal {int(signal.SIGHUP)}, gone {second_seconds:.3f} s after"
        f" the close, its ticks 1 to {second.tick_n} consecutive"
    )


# Closes the wire with 1000, serving the others meanwhile, then waits for
# ttyd's log of its program killed with SIGHUP, and for the program, its
# session, the commands it ran and the parent's children to be gone.
# Answers the seconds from the close until then.
def session_close(wire: Wire, others: list[Wire], parent: int) -> float:
    pid = wire.hello["pid"]
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
    watched = {pid, *(started["pid"] for started in wire.started.values())}
    while left := processes_left(watched, pid, parent):
        remaining(wire.ttyd.deadline, f"processes {left} to end")
        time.sleep(_POLL_SECONDS)
    return time.monotonic() - closed_at


def signal_exit(signal_number: int, frame: FrameType | None) -> None:
    sys.exit(128 + signal_number)


# Starts ttyd on a port of its choosing, read from its log, and stops it
# when done.
@contextlib.contextmanager
def ttyd_serve(
    options: list[str], version: str, deadline: float
) -> Generator[Ttyd]:
    ttyd = Ttyd(options, version, deadline)
    try:
        found = ttyd.line_wait(_LISTENING_PATTERN, 0, "ttyd to listen")
        ttyd.port = int(found.group(1))
        yield ttyd
    finally:
        ttyd.stop()


# Answers what ttyd sent up to the end of its headers, or all it sent if
# it closed the connection first.
def upgrade_read(sock: socket.socket, ttyd: Ttyd) -> bytes:
    data = b""
    while b"\r\n\r\n" not in data:
        sock.settimeout(remaining(ttyd.deadline, "ttyd's answer to /ws"))
        chunk = sock.recv(1 << 16)
        if not chunk:
            return data
        data += chunk
    return data


# Asks ttyd for a WebSocket on /ws from its own origin. Answers the socket
# and the key.
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


# Answers a Wire on a WebSocket to ttyd, failing unless ttyd accepted it
# with the tty subprotocol.
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


# Reads and handles what ttyd sends on each wire, firing the timers that
# come due, until done answers True.
def wires_wait(wires: list[Wire], done: Callable[[], bool], what: str) -> None:
    ttyd = wires[0].ttyd
    while True:
        for wire in wires:
            while wire.timers and wire.timers[0][0] <= time.monotonic():
                _, callback = wire.timers.pop(0)
                callback()
        if done():
            return
        timeout = remaining(ttyd.deadline, what)
        for wire in wires:
            if wire.timers:
                timeout = min(timeout, wire.timers[0][0] - time.monotonic())
        readers: list[socket.socket | int] = [
            wire.sock for wire in wires if not wire.ended
        ]
        if not ttyd.stderr_ended:
            readers.append(ttyd.fd)
        readable, _, _ = select.select(readers, [], [], max(timeout, 0))
        if ttyd.fd in readable:
            ttyd.stderr_read()
        for wire in wires:
            if wire.sock in readable:
                wire.socket_read()


def main() -> int:
    argparse.ArgumentParser(
        description="Run the wire test: bootstrap.py --session through"
        " Linux ttyd, from a standard library WebSocket client."
    ).parse_args()
    for signal_number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(signal_number, signal_exit)
    deadline = time.monotonic() + _RUN_TIMEOUT_SECONDS
    version = subprocess.run(
        [_TTYD_PATH, "--version"],
        capture_output=True,
        check=True,
        stdin=subprocess.DEVNULL,
        text=True,
    ).stdout.strip()
    rung = "5.1.1 serve"
    try:
        with ttyd_serve(_TTYD_OPTIONS, version, deadline) as ttyd:
            print(f"{rung}: {rung_serve(ttyd)}", flush=True)
            rung = "5.1.2 ticks"
            wire = websocket_open(ttyd, {})
            print(f"{rung}: {rung_ticks(wire)}", flush=True)
            for rung, check in (
                ("5.1.3 round trip", rung_round_trip),
                ("5.1.4 framing", rung_framing),
                ("5.1.5 control", rung_control),
                ("5.1.6 concurrent", rung_concurrent),
                ("end", rung_end),
            ):
                print(f"{rung}: {check(wire)}", flush=True)
            # Last, as it ends ttyd.
            for rung, ttyd_check in (
                ("5.4.3 two clients", rung_two_clients),
                ("5.4.2 ttyd killed", rung_ttyd_killed),
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
