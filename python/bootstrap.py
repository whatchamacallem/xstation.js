# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Runs until a signal ends it, speaking one JSON object per line each way
# over its terminal, as ttyd runs it for the page:
#
#     ttyd --writable --index bootstrap.html python3 bootstrap.py

from __future__ import annotations

import ast
import contextlib
import datetime
import hashlib
import json
import os
import platform
import pwd
import selectors
import shlex
import signal
import subprocess
import sys
import time
import tty
from collections.abc import Callable, Generator
from types import FrameType
from typing import Any, NoReturn

# calc's operators, by the ast node that names each.
_CALC_OPERATORS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: lambda left, right: left + right,
    ast.Div: lambda left, right: left / right,
    ast.FloorDiv: lambda left, right: left // right,
    ast.Mod: lambda left, right: left % right,
    ast.Mult: lambda left, right: left * right,
    ast.Pow: lambda left, right: left**right,
    ast.Sub: lambda left, right: left - right,
}
# calc refuses a power of integers whose result would pass this many bits,
# as computing it could take minutes.
_CALC_POWER_MAX_BITS = 1 << 16

_HELP_TEXT = (
    "help: this list\n"
    "time: the local time and UTC\n"
    "stat: the host's figures\n"
    "whoami: user name, uid and working directory\n"
    "ls [path]: a directory's entries with their sizes in bytes\n"
    "sha256 <text>: the SHA-256 of the text's UTF-8 bytes\n"
    "calc <expr>: arithmetic on numbers with - + * / // % ** and ()\n"
    "echo <text>: the text, and its length in characters and bytes\n"
    "count: messages and bytes received and sent\n"
    "run <words>: runs a command, streaming its output\n"
    "cancel: stops the running command"
)

# The fields of each type of message from the page, besides type.
_INPUT_FIELDS: dict[str, dict[str, type[Any]]] = {
    "count": {},
    "digest": {"id": int, "text": str},
    "ping": {"id": int},
    "say": {"id": int, "text": str},
    "size": {},
    "stat": {},
}

_LOADAVG_PATH = "/proc/loadavg"
_MEMINFO_AVAILABLE_PREFIX = "MemAvailable:"
_MEMINFO_PATH = "/proc/meminfo"

# The most taken from a descriptor in one read.
_READ_SIZE = 1 << 16

_TICK_SECONDS = 1.0

_UPTIME_PATH = "/proc/uptime"


# A command run for a say, from its start until its exit is sent.
class Command:
    def __init__(
        self,
        say_id: int,
        argv: list[str],
        process: subprocess.Popen[bytes],
        output: int,
    ) -> None:
        self.say_id = say_id
        self.argv = argv
        self.process = process
        # The read end of the pipe its stdout and stderr go to.
        self.output = output
        self.output_open = True
        # What it wrote after its last newline.
        self.partial = bytearray()
        self.lines = 0
        self.cancelled = False


class Session:
    def __init__(self) -> None:
        self.command: Command | None = None
        # What the page wrote after its last newline.
        self.input_partial = bytearray()
        self.received_bytes = 0
        self.received_messages = 0
        self.sent_bytes = 0
        self.sent_messages = 0
        # Set while a command starts, when a signal couldn't yet kill it.
        self.starting = False
        self.signal_deferred: int | None = None
        self.tick_n = 1
        self.tick_start = 0.0
        self.selector = selectors.DefaultSelector()
        self.selector.register(0, selectors.EVENT_READ, self.input_read)
        self.wake_reader, wake_writer = os.pipe()
        os.set_blocking(wake_writer, False)
        self.selector.register(
            self.wake_reader, selectors.EVENT_READ, self.wake_read
        )
        signal.set_wakeup_fd(wake_writer)
        for signal_number in (signal.SIGCHLD, signal.SIGWINCH):
            signal.signal(signal_number, signal_wake)
        for signal_number in (signal.SIGHUP, signal.SIGTERM):
            signal.signal(signal_number, self.signal_end)

    # Sends SIGTERM to the command's process group. Answers the reply.
    def command_cancel(self) -> str:
        if self.command is None:
            return "cancel: nothing is running"
        os.killpg(self.command.process.pid, signal.SIGTERM)
        self.command.cancelled = True
        return f"cancelled pid {self.command.process.pid}"

    # Sends the command's exit once its output has ended and it has exited.
    def command_end(self) -> None:
        command = self.command
        if (
            command is None
            or command.output_open
            or command.process.poll() is None
        ):
            return
        self.command = None
        self.send(
            {
                "type": "exit",
                "id": command.say_id,
                "code": command.process.returncode,
                "lines": command.lines,
                "cancelled": command.cancelled,
            }
        )

    def command_kill(self) -> None:
        if self.command is not None:
            os.killpg(self.command.process.pid, signal.SIGKILL)

    # Reads the command's output and sends its whole lines; at EOF, sends
    # what is left as a line, and its exit once it has exited.
    def command_read(self, command: Command) -> None:
        chunk = os.read(command.output, _READ_SIZE)
        command.partial += chunk
        if chunk:
            if b"\n" not in chunk:
                return
            *lines, command.partial = command.partial.split(b"\n")
        else:
            lines = [command.partial] if command.partial else []
        self.send(*(self.line_message(command, line) for line in lines))
        if not chunk:
            self.selector.unregister(command.output)
            os.close(command.output)
            command.output_open = False
            self.command_end()

    # Starts the say's command, unless one is running, and replies.
    def command_start(self, say_id: int, words: str) -> None:
        if self.command is not None:
            running = self.command
            self.reply_send(
                say_id,
                f"run: {shlex.join(running.argv)} is still running as pid"
                f" {running.process.pid}; cancel it first",
            )
            return
        try:
            argv = shlex.split(words)
        except ValueError as error:
            self.reply_send(say_id, f"run: {error}")
            return
        if not argv:
            self.reply_send(say_id, "run: no command given")
            return
        reader, writer = os.pipe()
        try:
            with self.signals_deferred():
                command = Command(
                    say_id,
                    argv,
                    subprocess.Popen(
                        argv,
                        stdin=subprocess.DEVNULL,
                        stdout=writer,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    ),
                    reader,
                )
                self.command = command
        except (OSError, ValueError) as error:
            os.close(reader)
            self.reply_send(say_id, f"run: {error}")
            return
        finally:
            os.close(writer)
        self.selector.register(
            reader, selectors.EVENT_READ, lambda: self.command_read(command)
        )
        pid = command.process.pid
        self.send(
            {
                "type": "reply",
                "id": say_id,
                "text": f"started {shlex.join(argv)} as pid {pid}",
            },
            {"type": "started", "id": say_id, "pid": pid, "argv": argv},
        )

    # Answers the figures count reports, of what came before it.
    def counts(self) -> dict[str, int]:
        return {
            "received_messages": self.received_messages,
            "received_bytes": self.received_bytes,
            "sent_messages": self.sent_messages,
            "sent_bytes": self.sent_bytes,
        }

    def hello_send(self) -> None:
        size = os.get_terminal_size(0)
        self.send(
            {
                "type": "hello",
                "pid": os.getpid(),
                "python": platform.python_version(),
                "columns": size.columns,
                "rows": size.lines,
            }
        )
        self.tick_start = time.monotonic()

    # Reads the page's input and answers its whole lines in order, each
    # counted as received when answered.
    def input_read(self) -> None:
        chunk = os.read(0, _READ_SIZE)
        if not chunk:
            raise EOFError("the terminal closed")
        self.input_partial += chunk
        if b"\n" not in chunk:
            return
        *lines, self.input_partial = self.input_partial.split(b"\n")
        for line in lines:
            self.received_messages += 1
            self.received_bytes += len(line)
            self.message_answer(line)

    # Answers the line message for a line of the command's output.
    def line_message(
        self, command: Command, line: bytearray
    ) -> dict[str, Any]:
        command.lines += 1
        return {
            "type": "line",
            "id": command.say_id,
            "n": command.lines,
            "text": line.decode(errors="backslashreplace"),
        }

    # Answers the line that carries the message, counted as sent.
    def line_encode(self, message: dict[str, Any]) -> bytes:
        line = json.dumps(message).encode("ascii")
        self.sent_messages += 1
        self.sent_bytes += len(line)
        return line + b"\r\n"

    def loop(self) -> NoReturn:
        try:
            while True:
                deadline = self.tick_start + self.tick_n * _TICK_SECONDS
                timeout = max(deadline - time.monotonic(), 0)
                for key, _ in self.selector.select(timeout):
                    key.data()
                self.ticks_send()
        finally:
            self.command_kill()

    # Replies to a line from the page, which must hold a message of a known
    # type with exactly that type's fields.
    def message_answer(self, line: bytearray) -> None:
        message: dict[str, Any] = json.loads(line.decode())
        if (
            type(message) is not dict
            or message.get("type") not in _INPUT_FIELDS
        ):
            raise ValueError(f"not a message of a known type: {line[:80]!r}")
        kind: str = message["type"]
        fields = _INPUT_FIELDS[kind]
        if message.keys() != {"type", *fields} or any(
            type(message[name]) is not field_type
            for name, field_type in fields.items()
        ):
            raise ValueError(f"malformed {kind} message: {line[:80]!r}")
        if kind == "count":
            self.send({"type": "count"} | self.counts())
        elif kind == "digest":
            text: str = message["text"]
            data = text.encode()
            self.send(
                {
                    "type": "digest",
                    "id": message["id"],
                    "bytes": len(data),
                    "characters": len(text),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        elif kind == "ping":
            self.send({"type": "pong", "id": message["id"]})
        elif kind == "size":
            self.size_send()
        elif kind == "stat":
            self.send({"type": "stat"} | stat_measure())
        else:
            self.say_answer(message["id"], message["text"])

    def reply_send(self, say_id: int, text: str) -> None:
        self.send({"type": "reply", "id": say_id, "text": text})

    # Replies to a say with exactly one reply, running or cancelling a
    # command when it asks.
    def say_answer(self, say_id: int, text: str) -> None:
        word, _, argument = text.partition(" ")
        if word == "run":
            self.command_start(say_id, argument)
            return
        if word == "calc":
            reply = calc_text(argument.strip())
        elif word == "cancel":
            reply = self.command_cancel()
        elif word == "count":
            reply = "\n".join(
                f"{name}: {value}" for name, value in self.counts().items()
            )
        elif word == "echo":
            reply = (
                f"{argument}\n{len(argument)} characters,"
                f" {len(argument.encode())} bytes in UTF-8"
            )
        elif word == "help":
            reply = _HELP_TEXT
        elif word == "ls":
            reply = ls_text(argument.strip() or ".")
        elif word == "sha256":
            reply = hashlib.sha256(argument.encode()).hexdigest()
        elif word == "stat":
            reply = "\n".join(
                f"{name}: {value}" for name, value in stat_measure().items()
            )
        elif word == "time":
            reply = time_text()
        elif word == "whoami":
            reply = (
                f"user: {pwd.getpwuid(os.getuid()).pw_name}\n"
                f"uid: {os.getuid()}\ncwd: {os.getcwd()}"
            )
        else:
            reply = f"unknown command {word}; help lists them"
        self.reply_send(say_id, reply)

    # Writes the messages' lines to the terminal in one write, all of it.
    def send(self, *messages: dict[str, Any]) -> None:
        data = memoryview(b"".join(map(self.line_encode, messages)))
        while data:
            data = data[os.write(1, data) :]

    # Kills the command's process group, then dies of the signal, so ttyd
    # sees how the program ended; while a command starts, waits for it.
    def signal_end(self, signal_number: int, frame: FrameType | None) -> None:
        if self.starting:
            self.signal_deferred = signal_number
            return
        self.command_kill()
        signal.signal(signal_number, signal.SIG_DFL)
        signal.raise_signal(signal_number)

    # Holds SIGHUP and SIGTERM back while a command starts, until it is
    # known and so can be killed.
    @contextlib.contextmanager
    def signals_deferred(self) -> Generator[None]:
        self.starting = True
        try:
            yield
        finally:
            self.starting = False
            if self.signal_deferred is not None:
                self.signal_end(self.signal_deferred, None)

    def size_send(self) -> None:
        size = os.get_terminal_size(0)
        self.send(
            {"type": "size", "columns": size.columns, "rows": size.lines}
        )

    # Sends a tick for each deadline passed, in order.
    def ticks_send(self) -> None:
        ticks: list[dict[str, Any]] = []
        while (
            time.monotonic() >= self.tick_start + self.tick_n * _TICK_SECONDS
        ):
            ticks.append(
                {"type": "tick", "n": self.tick_n, "time": time.time()}
            )
            self.tick_n += 1
        self.send(*ticks)

    # Acts on the signals the wake-up pipe holds: a size for each SIGWINCH,
    # and the command's exit after a SIGCHLD.
    def wake_read(self) -> None:
        answers = {
            signal.SIGCHLD: self.command_end,
            signal.SIGWINCH: self.size_send,
        }
        for signal_number in os.read(self.wake_reader, _READ_SIZE):
            answers[signal.Signals(signal_number)]()


# Answers what the tree of an arithmetic expression comes to, refusing all
# but numbers, unary minus and the operators of _CALC_OPERATORS.
def calc_evaluate(node: ast.expr) -> Any:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -calc_evaluate(node.operand)
    if isinstance(node, ast.BinOp) and type(node.op) in _CALC_OPERATORS:
        left = calc_evaluate(node.left)
        right = calc_evaluate(node.right)
        if (
            isinstance(node.op, ast.Pow)
            and type(left) is int
            and type(right) is int
            and (left.bit_length() - 1) * right > _CALC_POWER_MAX_BITS
        ):
            raise ValueError(
                f"{left} ** {right} would pass {_CALC_POWER_MAX_BITS} bits"
            )
        return _CALC_OPERATORS[type(node.op)](left, right)
    raise ValueError(f"{type(node).__name__} is not allowed")


# Answers what the arithmetic comes to, or why calc refuses it.
def calc_text(expression: str) -> str:
    try:
        return str(calc_evaluate(ast.parse(expression, mode="eval").body))
    except (
        ArithmeticError,
        MemoryError,
        RecursionError,
        SyntaxError,
        ValueError,
    ) as error:
        return f"calc: {error}"


# Answers the directory's entries, sorted, each with its size in bytes and
# a trailing / for a directory. A symbolic link is listed as itself.
def ls_text(path: str) -> str:
    lines: list[str] = []
    try:
        with os.scandir(path) as iterator:
            for entry in sorted(iterator, key=lambda entry: entry.name):
                size = entry.stat(follow_symlinks=False).st_size
                slash = "/" if entry.is_dir(follow_symlinks=False) else ""
                lines.append(f"{size} {entry.name}{slash}")
    except OSError as error:
        return f"ls: {error}"
    return "\n".join(lines)


# Runs the session until a signal ends it.
def session_run() -> NoReturn:
    tty.setraw(0)
    session = Session()
    session.hello_send()
    session.loop()


# Lets the signal reach the wake-up pipe, which the loop reads.
def signal_wake(signal_number: int, frame: FrameType | None) -> None:
    pass


# Answers the host's figures, read from the kernel.
def stat_measure() -> dict[str, Any]:
    uname = os.uname()
    with open(_UPTIME_PATH) as file:
        uptime = float(file.read().split()[0])
    with open(_LOADAVG_PATH) as file:
        loadavg = [float(field) for field in file.read().split()[:3]]
    with open(_MEMINFO_PATH) as file:
        available = next(
            line for line in file if line.startswith(_MEMINFO_AVAILABLE_PREFIX)
        )
    return {
        "hostname": uname.nodename,
        "kernel": uname.release,
        "uptime": uptime,
        "loadavg": loadavg,
        "mem_available_kib": int(available.split()[1]),
        "pid": os.getpid(),
    }


# Answers the time now, local with its offset and in UTC, in ISO 8601.
def time_text() -> str:
    now = datetime.datetime.now(datetime.UTC)
    return f"local: {now.astimezone().isoformat()}\nUTC: {now.isoformat()}"


if __name__ == "__main__":
    if sys.argv[1:]:
        print(f"usage: {sys.argv[0]}", file=sys.stderr)
        sys.exit(2)
    session_run()
