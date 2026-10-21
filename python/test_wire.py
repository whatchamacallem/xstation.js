#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The wire test. ttyd as xsjs_install.ps1 builds it serves roots made under
# build/ as the start script makes the server root, running
# `python3 <root>/python/bootstrap.py --root <root>`, and a standard library
# WebSocket client speaks ttyd's protocol and JSLB to them as the page does,
# rung by rung, each rung under a timer. On the echo main loop file, which
# --main-loop names in the query: hello, echo, echo 1 MiB with control bytes,
# a blob of exactly blob_max echoed, echo 128 MiB as one message with ttyd's
# resident size, a second connection refused and a line announcing blobs one
# byte over blob_max refused; then the last line regression on the
# console role, and ttyd killed. On the stock main loop: the mcp lines that
# open a session and a tools/call, kv.put and kv.get, doc.put and doc.head,
# verbose.tail, an unknown type, a sequence of forwarded operations the test
# builds replayed, read back by a new program and a stale since refused, and
# system.restart serving the echo main loop after source.put; on a root whose
# setting debug is false, the same refused. Where a program writes its last
# line and exits, a lone loss of that line is a ttyd fault, reported with
# ttyd's version and never retried. Each stage and each rung is labelled
# smoke-test or normal-test: a smoke-test run, the default, runs the rungs
# labelled smoke-test and starts no ttyd for a stage with none, a normal-test
# run runs every rung, and a mislabel fails the run. It prints one line per
# rung that runs, ending with its label and seconds, and exits 0, or stops at
# the first failed check, names its rung and exits 1. ttyd's log is copied to
# stderr. Standard library only, and ttyd is the one program it starts:
#
#     python3 python/test_wire.py [--smoke-test | --normal-test]

import argparse, base64, collections, hashlib, http.client, json, os, re
import select, shutil, signal, socket, subprocess, sys, tempfile, time, types
from collections.abc import Callable
from typing import Any, NamedTuple, NoReturn, Self, TypeAlias, cast

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The checkout, which holds the `python` directory.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# The build directory: each run's roots, and the bytecode of what is imported.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# The ttyd the install script builds from the pinned release and its patches.
_TTYD_PATH = os.path.join(_BUILD_PATH, "ttyd", "ttyd")

# The script that builds ttyd, which a missing ttyd names.
_INSTALL_SCRIPT = "xsjs_install.ps1"

# The start of the name of the directory each run makes its roots in.
_WORK_PREFIX = "test_wire-"

# The checkout's settings, the object each root's settings are made from.
_SETTINGS_PATH = os.path.join(_CHECKOUT_PATH, "settings.json")

# The strings file, which the start script copies into the root.
_STRINGS_PATH = os.path.join(_CHECKOUT_PATH, "i18n", "en-US.json")

# The seed directory, which the start script copies into the root.
_SEED_PATH = os.path.join(_PYTHON_PATH, "seed")

# The modules the server runs, which the start script copies into the root.
_RUNTIME_MODULES = (
    "i18n",
    "jslb",
    "verbose",
    "settings",
    "substrate",
    "dispatch",
    "mcp",
    "mcp_stdio",
    "engine_kv",
    "engine_doc",
    "engine_db",
    "engine_turn",
    "engine_sql",
    "engine_verbose",
    "engine_tap",
    "engine_mcp",
    "engine_system",
    "main_loop",
    "bootstrap",
)

# The directory of a root that holds the main loop files.
_MAIN_LOOP_DIRECTORY = "main_loop"

# The main loop file that serves `echo`.
_ECHO_NAME = "echo_loop.py"

# That file in the checkout, beside this one.
_ECHO_PATH = os.path.join(_PYTHON_PATH, _ECHO_NAME)

# The main loop file name the `source_put` tool call writes.
_TOOL_NAME = "echo_tool.py"

# The file in a root whose lock one engine at a time holds.
_LOCK_NAME = "engine.lock"

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_CHECKOUT_PATH, "API", "mcp", "tools.json")

# The `initialize` request the AI worker's MCP client sends the server.
_INITIALIZE_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "hyperposition-engine", "version": "0"},
    },
}

# The notification the client sends once the `initialize` reply is in.
_INITIALIZED_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
}

# The `tools/list` request the client sends after the notification.
_LIST_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
}

# The response to `initialize`: the pinned revision, `tools`, the server.
_INITIALIZE_RESPONSE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "protocolVersion": "2025-06-18",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "xsjs-server", "version": "0"},
    },
}

# The `JSON-RPC` id of the tools call, after `initialize` and `tools/list`.
_CALL_ID = 3

# The name `argparse` shows, as `sys.argv` may be empty.
_PROGRAM_NAME = "test_wire.py"

# A default chosen by its writer: the seconds a rung runs before it fails.
_RUNG_SECONDS = 120.0

# A default chosen by its writer: the seconds ttyd has to exit on `SIGTERM`.
_STOP_SECONDS = 5.0

# The environment variable ttyd passes on to the server as the provider key.
_PROVIDER_VARIABLE = "XSJS_PROVIDER_KEY"

# The provider key ttyd's environment holds, which `hello` must carry.
_PROVIDER_KEY = "test-wire-key"

# ttyd's options as the start script gives them, but its port and its page.
_TTYD_OPTIONS = (
    "--interface",
    "127.0.0.1",
    "--writable",
    "--check-origin",
    "--terminal-type",
    "dumb",
    "--url-arg",
)

# The option, patched into the release, that sets ttyd's receive chunk size.
_BUFFER_OPTION = "--srv-buf-size"

# The query arguments that run the echo main loop file.
_ECHO_ARGS = ("--main-loop", _ECHO_NAME)

# The query arguments that run the console role.
_CONSOLE_ARGS = ("console",)

# The query arguments that run the stock main loop: none.
_STOCK_ARGS: tuple[str, ...] = ()

# The status of a request that succeeded.
_HTTP_OK = 200

# The id of `hello`, the first request on the engine tty.
_HELLO_ID = 1

# The payload fields of `hello`, in order.
_HELLO_FIELDS = [
    "bootstrap",
    "sha256",
    "pid",
    "root",
    "settings",
    "seq",
    "provider_key",
]

# The type of the line the echo main loop serves.
_ECHO_TYPE = "echo"

# A type no handler serves.
_UNKNOWN_TYPE = "unknown.type"

# The version of every line this client builds.
_LINE_VERSION = 0

# The CR that ends a JSLB line.
_LINE_END = b"\r"

# The tag `line_render` writes after the JSON text for each blob, by number.
_BLOB_TAG = '<blob "n"={}>'

# Text of 2, 3 and 4 byte characters for payloads, built from code points.
_WIDE_TEXT = (
    "na" + chr(0xEF) + "ve " + chr(0x65E5) + chr(0x672C) + " " + chr(0x1F600)
)

# The payload the small echoes carry.
_ECHO_PAYLOAD: dict[str, Any] = {
    "text": _WIDE_TEXT,
    "count": -3,
    "nested": {"list": [1, "two", None, True]},
}

# A small blob: the control bytes below space, CR and LF among them.
_SMALL_BYTES = bytes(range(32))

# The bytes of the 1 MiB echo and value: every byte value 4096 times.
_CONTROL_BYTES = bytes(range(256)) * 4096

# The bytes in a MiB.
_MIB = 1 << 20

# The blob bytes the large echo sends in all, 128 MiB.
_LARGE_BYTES = 128 * _MIB

# The database the kv rung writes in, which every new root has.
_FILES_DB = "_files"

# The ref the kv rung puts its value under.
_VALUE_REF = "/_files/test_wire/control.bin"

# The database the doc rung writes in, which every new root has.
_METAVERSE_DB = "metaverse"

# The id of the document the doc rung writes.
_DOCUMENT_ID = "test_wire"

# The version the first put of a document writes.
_DOCUMENT_VERSION = 1

# The document the doc rung writes: its header and a text.
_DOCUMENT_BODY: dict[int | str, Any] = {0: {"t": "note"}, "text": _WIDE_TEXT}

# The page thread whose lines the verbose rung puts and reads back.
_PAGE_THREAD = "ai"

# The server's own thread, whose ring the verbose rung reads.
_SERVER_THREAD = "server"

# How many lines the verbose rung puts, which carry no level.
_PUT_COUNT = 3

# How many of those lines the verbose rung reads back.
_TAIL_COUNT = 2

# The database the replay creates and fills, which no new root has.
_REPLAY_DB = "replay"

# The database the replay creates, writes in and drops again.
_DROPPED_DB = "replay_dropped"

# The table of text to text that the replay makes with `sql.run`.
_PAIR_DDL = (
    "CREATE TABLE pair (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT"
)

# The statement that fills the replay's table with its two rows.
_PAIR_INSERT = "INSERT INTO pair (key, value) VALUES (?, ?), (?, ?)"

# The statement that gives a row of the replay's table a new value.
_PAIR_UPDATE = "UPDATE pair SET value = ? WHERE key = ?"

# The statement that reads the replay's table back, by key.
_PAIR_SELECT = "SELECT key, value FROM pair ORDER BY key"

# The columns that statement reads.
_PAIR_COLUMNS = ("key", "value")

# The rows the replay puts in its table, each a key and a value.
_PAIR_ROWS = (("first", _WIDE_TEXT), ("second", "two"))

# The value the replay's update gives the second row.
_PAIR_VALUE = "three"

# The key in the replay's database of the value it puts, then deletes.
_SMALL_KEY = "blob/small"

# The key in the replay's database of the value over `overflow_bytes`.
_LARGE_KEY = "blob/large"

# The start of both of those keys, which `kv.list` reads back.
_BLOB_PREFIX = "blob/"

# The key the replay puts in the database it drops.
_DROPPED_KEY = "note"

# The id of the scene document the replay writes and gives its turns.
_SCENE_ID = "scene"

# The ref of that document's first version, the scene of the turns.
_SCENE_REF = f"/{_REPLAY_DB}/{_SCENE_ID}/{_DOCUMENT_VERSION}"

# The scene document the replay writes: its header and a text.
_SCENE_BODY: dict[int | str, Any] = {0: {"t": "scene"}, "text": _WIDE_TEXT}

# The turns the replay appends to its scene, each a role and a text.
_TURNS = (("user", _WIDE_TEXT), ("assistant", "two"))

# The summary that replaces the replay's turns, text JSON writes as it is.
_SUMMARY_TEXT = "the first two turns in one"

# Reads the scene's turns back: each number, and whether the summary is in it.
_TURN_SELECT = (
    "SELECT n, instr(content, ?) > 0 AS summarized FROM _turn"
    " WHERE scene = ? ORDER BY n"
)

# The columns that statement reads.
_TURN_COLUMNS = ("n", "summarized")

# The one turn compaction leaves: number 1, the summary in it, true as 1.
_TURN_ROWS = ((1, 1),)

# How many nanoseconds the clock counts in a millisecond.
_NANOSECONDS_PER_MILLISECOND = 1_000_000

# How many lines the last line regression prints, 1 to this.
_LINES_COUNT = 100000

# The regression's command: a subshell prints the lines and exits at once.
_LINES_COMMAND = (
    f'( i=1; while [ "$i" -le {_LINES_COUNT} ]; do echo "$i";'
    " i=$((i + 1)); done )"
)

# The prompt dash writes when it waits for a command.
_PROMPT = b"$ "

# The columns the first message gives the terminal.
_COLUMNS = 80

# The rows the first message gives the terminal.
_ROWS = 24

# ttyd's first log line, with its version and that of libwebsockets.
_VERSION_PATTERN = re.compile(r" N: (ttyd \S+ \(libwebsockets \S+\))$")

# ttyd's log line of the port it listens on.
_LISTENING_PATTERN = re.compile(r" Listening on port: (\d+)$")

# ttyd's log line of a program's end: how, its code or signal, its pid.
_ENDED_PATTERN = re.compile(
    r"process (killed with signal|exited with code) (\d+), pid: (\d+)$"
)

# How ttyd's log says a program exited with a code.
_EXITED_WORDS = "exited with code"

# The code a refused or failed program exits with.
_PROGRAM_FAILED = 1

# What RFC 6455 appends to the key before it is hashed into the accept value.
_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# The opcode of a frame that continues a message.
_OPCODE_CONTINUATION = 0x0

# The opcode of a binary frame, which carries every ttyd message.
_OPCODE_BINARY = 0x2

# The opcode of a frame that closes the connection.
_OPCODE_CLOSE = 0x8

# The opcode of a ping, which a pong answers.
_OPCODE_PING = 0x9

# The opcode of a pong.
_OPCODE_PONG = 0xA

# The code of a normal close.
_CLOSE_NORMAL = 1000

# The bytes shown on each side of where a transcript first differs.
_SHOWN_BYTES = 200

# The most bytes read from ttyd's socket or log at once.
_READ_BYTES = 1 << 20

# The exit code of a run with a failed check.
_EXIT_FAILED = 1

# The exit code of a run that `^C` ended.
_EXIT_INTERRUPTED = 130

# A shell's exit code for a signal is this plus the signal's number.
_SIGNAL_BASE = 128

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")

# A decoded JSLB line, the `jslb.Object` dict: headers at integer keys.
LineObject: TypeAlias = dict[int | str, Any]


# A check that failed, with the measurement that failed it.
class CheckFailed(Exception):
    pass


# A process's resident size and its peak, in KiB.
class MemoryUse(NamedTuple):
    resident: int
    peak: int


# A rung's time limit, which fails loud once it has passed.
class RungTimer:
    # Starts the rung's time.
    def __init__(self, rung: str, seconds: float) -> None:
        self.rung = rung
        self.seconds = seconds
        self.end = time.monotonic() + seconds

    # Returns the seconds left, failing the rung once there are none.
    def seconds_left(self, what: str) -> float:
        left = self.end - time.monotonic()
        if left <= 0:
            raise CheckFailed(
                f"the rung {self.rung} ran out of its {self.seconds:g} s"
                f" waiting for {what}"
            )
        return left


# The rung that runs, its timer and start, the labels, and each rung's line.
class RungLog:
    # Starts on ttyd, before any rung, checking the labels of the category.
    def __init__(self, chosen: str) -> None:
        import category

        self.book = category.LabelBook(chosen)
        self.rung = "ttyd"
        self.timer = RungTimer(self.rung, _RUNG_SECONDS)
        self.started = time.monotonic()

    # Names the rung that runs now and starts its timer and its seconds.
    def rung_start(self, rung: str) -> None:
        self.rung = rung
        self.timer = RungTimer(rung, _RUNG_SECONDS)
        self.started = time.monotonic()

    # Prints the summary of the rung that ran, its label and its seconds.
    def rung_print(self, summary: str, label: str) -> None:
        seconds = time.monotonic() - self.started
        print(f"{self.rung}: {summary} ({label}, {seconds:.3f} s)", flush=True)

    # Starts the opening rung of a stage, which runs whenever its stage does.
    def rung_open(self, rung: str, label: str) -> None:
        if not self.book.rung_enter(rung, label):
            raise CheckFailed(
                f"the opening rung {rung} does not run in this run, but its"
                " stage does"
            )
        self.rung_start(rung)

    # Runs a rung of the category under its timer and prints its summary.
    def rung_run(
        self, rung: str, label: str, check: Callable[[], str]
    ) -> None:
        if not self.book.rung_enter(rung, label):
            return
        self.rung_start(rung)
        self.rung_print(check(), label)


# ttyd serving one root, in a session of its own, its log read from a pipe.
class TtydServer:
    # Starts ttyd on a port of its choosing, running the root's bootstrap.
    def __init__(
        self, root: str, values: dict[str, Any], log: RungLog
    ) -> None:
        self.root = root
        self.log = log
        self.command = [
            "python3",
            os.path.join(root, "python", "bootstrap.py"),
            "--root",
            root,
        ]
        self.version = _TTYD_PATH
        self.lines: list[str] = []
        self.partial = b""
        self.port = 0
        self.killed = False
        self.log_ended = False
        environment = dict(os.environ)
        environment[_PROVIDER_VARIABLE] = _PROVIDER_KEY
        self.fd, write_fd = os.pipe()
        try:
            self.process = subprocess.Popen(
                [
                    _TTYD_PATH,
                    "--port",
                    "0",
                    *_TTYD_OPTIONS,
                    _BUFFER_OPTION,
                    str(values["srv_buf_size"]),
                    *self.command,
                ],
                stdin=subprocess.DEVNULL,
                stdout=sys.stderr,
                stderr=write_fd,
                env=environment,
                start_new_session=True,
            )
        finally:
            os.close(write_fd)

    # Waits for ttyd's version and port, stopping it when that fails.
    def __enter__(self) -> Self:
        try:
            _, found = self.line_wait(_VERSION_PATTERN, "ttyd's version", 0)
            self.version = found.group(1)
            _, found = self.line_wait(_LISTENING_PATTERN, "ttyd to listen", 0)
            self.port = int(found.group(1))
        except BaseException:
            self.process_stop()
            raise
        return self

    # Stops ttyd whatever ended the block, a slow exit failing a clean run.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        stopped = self.process_stop()
        if not stopped and exception is None:
            raise CheckFailed(
                f"{self.version} still ran {_STOP_SECONDS:g} s after SIGTERM"
                " and was killed"
            )

    # Sends ttyd a signal, after which the end of its log is no failure.
    def signal_send(self, number: int) -> None:
        self.killed = True
        os.kill(self.process.pid, number)

    # Copies whole log lines to stderr and keeps them.
    def lines_take(self, data: bytes) -> None:
        *complete, self.partial = (self.partial + data).split(b"\n")
        for line in complete:
            text = line.decode()
            self.lines.append(text)
            sys.stderr.write(f"{text}\n")
        sys.stderr.flush()

    # Reads ttyd's log, failing at its end unless ttyd was killed.
    def log_read(self) -> None:
        data = os.read(self.fd, _READ_BYTES)
        if not data:
            if not self.killed:
                raise CheckFailed(
                    f"{self.version} exited with {self.process.wait()}"
                )
            self.log_ended = True
            return
        self.lines_take(data)

    # Returns the first log line from `start` on that matches, and its index.
    def line_wait(
        self, pattern: re.Pattern[str], what: str, start: int
    ) -> tuple[int, re.Match[str]]:
        index = start
        while True:
            while index < len(self.lines):
                found = pattern.search(self.lines[index])
                if found is not None:
                    return index, found
                index += 1
            readable, _, _ = select.select(
                [self.fd], [], [], self.log.timer.seconds_left(what)
            )
            if readable:
                self.log_read()

    # Returns how ttyd logged the end of the program of that pid, and the code.
    def end_wait(self, pid: int, what: str) -> tuple[str, int]:
        start = 0
        while True:
            index, found = self.line_wait(_ENDED_PATTERN, what, start)
            if int(found.group(3)) == pid:
                return found.group(1), int(found.group(2))
            start = index + 1

    # Stops ttyd, then reads the rest of its log. False when it needed SIGKILL.
    def process_stop(self) -> bool:
        stopped = True
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(_STOP_SECONDS)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
                stopped = False
        while data := os.read(self.fd, _READ_BYTES):
            self.lines_take(data)
        os.close(self.fd)
        if self.partial:
            sys.stderr.write(f"{self.partial.decode()}\n")
            sys.stderr.flush()
        return stopped


# A WebSocket on ttyd: its protocol, and the program's output raw or in lines.
class WireClient:
    # Takes the socket after the upgrade and handles any frames already read.
    def __init__(
        self,
        ttyd: TtydServer,
        sock: socket.socket,
        rest: bytes,
        values: dict[str, Any],
        raw: bool,
    ) -> None:
        import jslb

        self.ttyd = ttyd
        self.sock = sock
        self.unread = bytearray(rest)
        self.fragments: bytearray | None = None
        self.unsent: collections.deque[bytes] = collections.deque()
        self.unsent_offset = 0
        self.close_sent = False
        self.close_code: int | None = None
        self.close_reason = b""
        self.end_expected = False
        self.ended = False
        self.reset = False
        self.ttyd_messages = 0
        self.pings = 0
        self.title = ""
        self.preferences: dict[str, Any] = {}
        self.raw = raw
        self.output = bytearray()
        self.chunk_bytes: int = values["chunk_bytes"]
        self.decoder = jslb.LineDecoder(
            values["line_max"],
            values["blob_max"],
            values["blob_max"],
            blob_refuse,
        )
        self.lines: collections.deque[LineObject] = collections.deque()
        self.full = False
        self.id_last = 0
        self.pid = 0
        self.seq: dict[str, int] = {}
        self.frames_handle()

    # Returns the next request id of this connection, from 1.
    def id_next(self) -> int:
        self.id_last += 1
        return self.id_last

    # Queues one WebSocket frame, masked as a client's must be.
    def frame_send(self, opcode: int, payload: bytes) -> None:
        head = bytearray([0x80 | opcode])
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
        self.unsent.append(bytes(head) + mask + masked)

    # Queues bytes for the program as ttyd input messages of `chunk_bytes`.
    def input_send(self, data: bytes) -> None:
        for start in range(0, len(data), self.chunk_bytes):
            piece = data[start : start + self.chunk_bytes]
            self.frame_send(_OPCODE_BINARY, b"0" + piece)

    # Queues a close frame with the normal code, after which the end is due.
    def close_send(self) -> None:
        self.close_sent = True
        self.end_expected = True
        self.frame_send(_OPCODE_CLOSE, _CLOSE_NORMAL.to_bytes(2, "big"))

    # Sends as much of the first queued frame as the socket takes.
    def unsent_send(self) -> None:
        frame = self.unsent[0]
        sent = self.sock.send(memoryview(frame)[self.unsent_offset :])
        self.unsent_offset += sent
        if self.unsent_offset == len(frame):
            self.unsent.popleft()
            self.unsent_offset = 0

    # Reads from ttyd, failing on an end of the connection that is not due.
    def socket_read(self) -> None:
        version = self.ttyd.version
        try:
            data = self.sock.recv(_READ_BYTES)
        except ConnectionResetError as error:
            if not self.end_expected:
                raise CheckFailed(f"{version} reset the connection") from error
            self.reset = True
            self.ended = True
            return
        if not data:
            if self.close_code is None and not self.end_expected:
                raise CheckFailed(
                    f"{version} ended the connection with no close frame"
                )
            self.ended = True
            return
        self.unread += data
        self.frames_handle()

    # Handles each whole frame read so far, then drops their bytes.
    def frames_handle(self) -> None:
        unread = self.unread
        start = 0
        while len(unread) - start >= 2:
            first, second = unread[start], unread[start + 1]
            if second & 0x80:
                raise CheckFailed(f"{self.ttyd.version} sent a masked frame")
            length = second & 0x7F
            head = 2
            if length == 126:
                head = 4
            elif length == 127:
                head = 10
            if len(unread) - start < head:
                break
            if head > 2:
                size = unread[start + 2 : start + head]
                length = int.from_bytes(size, "big")
            end = start + head + length
            if len(unread) < end:
                break
            payload = bytes(unread[start + head : end])
            start = end
            self.frame_take(first, payload)
        del unread[:start]

    # Handles one frame: a ping answered, a close, or a piece of a message.
    def frame_take(self, first: int, payload: bytes) -> None:
        opcode = first & 0x0F
        if opcode == _OPCODE_PING:
            self.pings += 1
            self.frame_send(_OPCODE_PONG, payload)
        elif opcode == _OPCODE_CLOSE:
            self.close_take(payload)
        elif opcode == _OPCODE_BINARY and self.fragments is None:
            self.fragments = bytearray(payload)
        elif opcode == _OPCODE_CONTINUATION and self.fragments is not None:
            self.fragments += payload
        else:
            raise CheckFailed(
                f"{self.ttyd.version} sent a frame of opcode {opcode} out of"
                " turn"
            )
        if opcode in (_OPCODE_BINARY, _OPCODE_CONTINUATION) and first & 0x80:
            message = bytes(cast(bytearray, self.fragments))
            self.fragments = None
            self.message_take(message)

    # Keeps ttyd's close code and reason, failing on a close that is not due.
    def close_take(self, payload: bytes) -> None:
        version = self.ttyd.version
        if len(payload) < 2:
            raise CheckFailed(f"{version} closed with no code")
        self.close_code = int.from_bytes(payload[:2], "big")
        self.close_reason = payload[2:]
        if not self.end_expected:
            raise CheckFailed(
                f"{version} closed the connection with {self.close_code},"
                f" reason {self.close_reason!r}"
            )

    # Handles one ttyd message: the title, the preferences, then output.
    def message_take(self, message: bytes) -> None:
        version = self.ttyd.version
        self.ttyd_messages += 1
        kind = message[:1]
        due = b"0"
        if self.ttyd_messages <= 2:
            due = str(self.ttyd_messages).encode()
        if kind != due:
            raise CheckFailed(
                f"{version}'s message {self.ttyd_messages} is of type"
                f" {kind!r}, not {due!r}: {message[:_SHOWN_BYTES]!r}"
            )
        if kind == b"1":
            self.title = message[1:].decode()
        elif kind == b"2":
            self.preferences = preferences_parse(version, message[1:])
        else:
            self.output_take(message[1:])

    # Keeps the program's output: raw bytes, or its lines, failing on a fault.
    def output_take(self, data: bytes) -> None:
        import jslb

        if self.raw:
            self.output += data
            return
        try:
            self.lines.extend(self.decoder.bytes_feed(data))
            self.decoder.bytes_feed(b"")
        except jslb.WireError as error:
            raise CheckFailed(
                f"the program's output through {self.ttyd.version} is not"
                f" JSLB: {error}"
            ) from error


# A forwarded operation of the replay: its request's parts, and the reply due.
class ReplayStep(NamedTuple):
    line_type: str
    key: str | None
    blobs: list[bytes]
    payload: dict[str, Any]
    due: dict[str, Any]


# The forwarded operations the test builds, each with the `since` it carries.
class ReplaySequence:
    # Starts with no step, and no database the replay made.
    def __init__(self) -> None:
        self.steps: list[ReplayStep] = []
        self.seq: dict[str, int] = {}

    # Adds a step that modifies a database: its `since`, and the `seq` after.
    def step_count(
        self,
        db: str,
        line_type: str,
        key: str | None,
        blobs: list[bytes],
        payload: dict[str, Any],
        due: dict[str, Any],
    ) -> None:
        since = self.seq[db]
        self.seq[db] = since + 1
        sent: dict[str, Any] = {**payload, "since": since}
        replied: dict[str, Any] = {**due, "seq": since + 1}
        self.steps.append(ReplayStep(line_type, key, blobs, sent, replied))

    # Creates a database, whose `seq` is 0 before it exists and after.
    def database_create(self, db: str) -> None:
        payload: dict[str, Any] = {"db": db, "since": 0}
        self.steps.append(ReplayStep("db.create", None, [], payload, {}))
        self.seq[db] = 0

    # Drops a database, its `since` the `seq` it has.
    def database_drop(self, db: str) -> None:
        payload: dict[str, Any] = {"db": db, "since": self.seq.pop(db)}
        self.steps.append(ReplayStep("db.drop", None, [], payload, {}))

    # Puts a value under a key of a database.
    def value_put(self, db: str, key: str, data: bytes) -> None:
        due: dict[str, Any] = {"sha256": sha256_text(data)}
        self.step_count(db, "kv.put", f"/{db}/{key}", [data], {}, due)

    # Deletes the value under a key of a database.
    def value_delete(self, db: str, key: str) -> None:
        self.step_count(db, "kv.delete", f"/{db}/{key}", [], {}, {})

    # Writes the first version of a document, whose ref the reply gives.
    def document_put(
        self, db: str, name: str, body: dict[int | str, Any], ref: str
    ) -> None:
        payload: dict[str, Any] = {"db": db, "id": name, "body": body}
        self.step_count(db, "doc.put", None, [], payload, {"ref": ref})

    # Appends a turn to a scene of a database, `n` the number it is given.
    def turn_append(
        self, db: str, scene: str, role: str, text: str, n: int
    ) -> None:
        content = {"role": role, "content": text}
        payload: dict[str, Any] = {
            "scene": scene,
            "role": role,
            "content": content,
        }
        self.step_count(db, "turn.append", None, [], payload, {"n": n})

    # Replaces turns 1 to `through` of a scene by one summary turn.
    def turns_compact(
        self, db: str, scene: str, through: int, summary: str
    ) -> None:
        payload: dict[str, Any] = {
            "scene": scene,
            "through": through,
            "summary": summary,
        }
        self.step_count(db, "turn.compact", None, [], payload, {})

    # Runs statements that modify a database, with the results due.
    def statements_run(
        self,
        db: str,
        statements: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> None:
        payload: dict[str, Any] = {"db": db, "statements": statements}
        due: dict[str, Any] = {"results": results}
        self.step_count(db, "sql.run", None, [], payload, due)


# Refuses a blob the client would stream, as it keeps each message in memory.
def blob_refuse(header: LineObject) -> NoReturn:
    raise CheckFailed(
        f"the client's decoder was asked to stream the blob {header}"
    )


# Returns ttyd's preferences, which must be a JSON object.
def preferences_parse(version: str, data: bytes) -> dict[str, Any]:
    try:
        value: object = json.loads(data)
    except json.JSONDecodeError as error:
        raise CheckFailed(
            f"{version}'s preferences are not JSON: {error}: {data!r}"
        ) from error
    if type(value) is not dict:
        raise CheckFailed(
            f"{version}'s preferences are not an object: {data!r}"
        )
    return cast(dict[str, Any], value)


# Returns the `SHA-256` of the bytes as 64 lowercase hex digits.
def sha256_text(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Returns the text as a terminal shows it: `UTF-8`, each LF as CR LF.
def terminal_text(text: str) -> bytes:
    return text.encode().replace(b"\n", b"\r\n")


# Says how the connection ended: a close frame, a reset, or neither.
def connection_end(client: WireClient) -> str:
    if client.reset:
        return "the TCP connection was reset"
    if client.close_code is None:
        return (
            "the TCP connection ended with no close frame, which a browser"
            " reports as 1006"
        )
    return (
        f"a close frame of code {client.close_code}, reason"
        f" {client.close_reason!r}, came and the TCP connection ended"
    )


# Sends what the clients queued and reads ttyd until `done` holds.
def clients_wait(
    clients: list[WireClient], done: Callable[[], bool], what: str
) -> None:
    ttyd = clients[0].ttyd
    while not done() or any(
        client.unsent for client in clients if not client.ended
    ):
        readers: list[socket.socket | int] = [
            client.sock for client in clients if not client.ended
        ]
        writers = [
            client.sock
            for client in clients
            if client.unsent and not client.ended
        ]
        if not ttyd.log_ended:
            readers.append(ttyd.fd)
        left = ttyd.log.timer.seconds_left(f"{what} through {ttyd.version}")
        readable, writable, _ = select.select(readers, writers, [], left)
        if ttyd.fd in readable:
            ttyd.log_read()
        for client in clients:
            if client.sock in writable:
                client.unsent_send()
            if client.sock in readable:
                client.socket_read()


# Sends what the client queued and reads ttyd until `done` holds.
def client_wait(
    client: WireClient, done: Callable[[], bool], what: str
) -> None:
    clients_wait([client], done, what)


# Returns ttyd's status and body for a GET of the path, within the rung.
def http_get(ttyd: TtydServer, path: str) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        ttyd.port,
        timeout=ttyd.log.timer.seconds_left(f"GET {path}"),
    )
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.read()
    except TimeoutError as error:
        raise CheckFailed(
            f"GET {path} through {ttyd.version} outlasted the rung's timer"
        ) from error
    finally:
        connection.close()


# Sends ttyd's first message, with its token, which starts the program.
def start_send(client: WireClient) -> None:
    status, body = http_get(client.ttyd, "/token")
    if status != _HTTP_OK:
        raise CheckFailed(f"GET /token answered {status}")
    token = json.loads(body)["token"]
    first = {"AuthToken": token, "columns": _COLUMNS, "rows": _ROWS}
    client.frame_send(_OPCODE_BINARY, json.dumps(first).encode())


# Opens a WebSocket on `/ws` with the query arguments and starts the program.
def websocket_open(
    ttyd: TtydServer, args: tuple[str, ...], values: dict[str, Any], raw: bool
) -> WireClient:
    timer = ttyd.log.timer
    key = base64.b64encode(os.urandom(16)).decode()
    host = f"127.0.0.1:{ttyd.port}"
    query = "&".join(f"arg={arg}" for arg in args)
    path = f"/ws?{query}" if args else "/ws"
    sock = socket.create_connection(
        ("127.0.0.1", ttyd.port), timer.seconds_left(f"ttyd to take {path}")
    )
    request = [
        f"GET {path} HTTP/1.1",
        f"Host: {host}",
        f"Origin: http://{host}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Version: 13",
        "Sec-WebSocket-Protocol: tty",
    ]
    sock.sendall(("\r\n".join(request) + "\r\n\r\n").encode())
    sock.setblocking(False)
    data = bytearray()
    while b"\r\n\r\n" not in data:
        readable, _, _ = select.select(
            [sock], [], [], timer.seconds_left(f"ttyd's answer to {path}")
        )
        if readable:
            chunk = sock.recv(_READ_BYTES)
            if not chunk:
                raise CheckFailed(
                    f"{ttyd.version} closed {path} unanswered after"
                    f" {bytes(data)!r}"
                )
            data += chunk
    head, _, rest = bytes(data).partition(b"\r\n\r\n")
    status, *header_lines = head.decode("latin-1").split("\r\n")
    answered: dict[str, str] = {}
    for header_line in header_lines:
        name, _, value = header_line.partition(":")
        answered[name.strip().lower()] = value.strip()
    digest = hashlib.sha1((key + _WEBSOCKET_GUID).encode()).digest()
    accept = base64.b64encode(digest).decode()
    if (
        not status.startswith("HTTP/1.1 101 ")
        or answered.get("sec-websocket-accept") != accept
        or answered.get("sec-websocket-protocol") != "tty"
    ):
        raise CheckFailed(f"{ttyd.version} answered {path} with {head!r}")
    client = WireClient(ttyd, sock, rest, values, raw)
    start_send(client)
    return client


# Closes the connection with the normal code and checks ttyd's answer.
def session_close(client: WireClient) -> None:
    client.close_send()
    client_wait(
        client,
        lambda: client.close_code is not None or client.ended,
        "ttyd's close frame",
    )
    client.sock.close()
    if client.close_code != _CLOSE_NORMAL:
        raise CheckFailed(
            f"{client.ttyd.version} answered close {_CLOSE_NORMAL}:"
            f" {connection_end(client)}"
        )


# The line as its debug rendering shows it.
def line_text(line: LineObject) -> str:
    import jslb

    return jslb.line_render(cast(jslb.Object, line))


# The bytes of each blob of a line, held in memory, in order.
def blobs_of(line: LineObject) -> list[bytes]:
    import jslb

    return [
        jslb.field_get(cast(jslb.Object, header), "data")
        for header in jslb.headers_of(cast(jslb.Object, line))[1:]
    ]


# The bytes a line and its blobs take on the wire.
def message_bytes(line: LineObject) -> int:
    import jslb

    pieces = jslb.line_encode(cast(jslb.Object, line))
    return sum(len(cast(bytes, piece)) for piece in pieces)


# The text and CR of an echo request with no payload and blobs of the sizes.
def echo_text(full: bool, request_id: int, sizes: list[int]) -> bytes:
    import jslb

    header = jslb.header_make(_ECHO_TYPE, id=request_id, full=full)
    blobs: list[jslb.Object] = []
    for size in sizes:
        blob = jslb.Object()
        blob["s"] = size
        blobs.append(blob)
    line = jslb.line_make(header, blobs)
    numbers = range(1, len(sizes) + 1)
    tags = "".join(_BLOB_TAG.format(number) for number in numbers)
    text = jslb.line_render(line).removesuffix(tags)
    return text.encode("utf-8") + _LINE_END


# Builds a request of the connection with the next id, its blobs and payload.
def request_make(
    client: WireClient,
    full: bool,
    line_type: str,
    blobs: list[bytes],
    key: str | None,
    payload: dict[str, Any],
) -> LineObject:
    import jslb

    header = jslb.header_make(
        line_type, id=client.id_next(), key=key, full=full
    )
    return jslb.line_make(
        header, [jslb.blob_make(data) for data in blobs], **payload
    )


# Builds a notification, a line with no id, in the connection's names.
def notice_make(
    client: WireClient, line_type: str, payload: dict[str, Any]
) -> LineObject:
    import jslb

    header = jslb.header_make(line_type, full=client.full)
    return jslb.line_make(header, [], **payload)


# Queues a line and its blobs as the program's input.
def line_send(client: WireClient, line: LineObject) -> None:
    import jslb

    pieces = jslb.line_encode(cast(jslb.Object, line))
    client.input_send(b"".join(cast(bytes, piece) for piece in pieces))


# Returns the next line the program wrote, failing if the connection ends.
def line_next(client: WireClient, what: str) -> LineObject:
    client_wait(client, lambda: bool(client.lines) or client.ended, what)
    if not client.lines:
        raise CheckFailed(
            f"{connection_end(client)} before {what} came, through"
            f" {client.ttyd.version}"
        )
    return client.lines.popleft()


# Returns the program's last line, then waits for ttyd to end the connection.
def line_last(client: WireClient, what: str) -> LineObject:
    client.end_expected = True
    client_wait(client, lambda: bool(client.lines) or client.ended, what)
    if not client.lines:
        raise CheckFailed(
            f"{connection_end(client)} before {what}, the program's last"
            f" line, came: a lone loss through {client.ttyd.version}, a ttyd"
            " fault, reported and not retried"
        )
    line = client.lines.popleft()
    client_wait(client, lambda: client.ended, f"the end after {what}")
    if client.lines:
        raise CheckFailed(
            f"the program wrote {line_text(client.lines[0])} after {what}"
        )
    client.sock.close()
    return line


# Returns the reply to the request, failing on an error or any other line.
def reply_take(
    client: WireClient, request: LineObject, what: str
) -> LineObject:
    import jslb

    line = line_next(client, what)
    asked: Any = request[0]
    header: Any = line[0]
    due = (jslb.field_get(asked, "type"), jslb.field_get(asked, "id"))
    came = (jslb.field_get(header, "type"), jslb.field_get(header, "reply"))
    if came != due:
        raise CheckFailed(f"{what}: the server wrote {line_text(line)}")
    return line


# Sends the request and returns its reply.
def exchange_run(
    client: WireClient, request: LineObject, what: str
) -> LineObject:
    line_send(client, request)
    return reply_take(client, request, what)


# Fails unless the line is an `error` line with the message, answering `reply`.
def error_check(
    line: LineObject, reply: int | None, message: str, what: str
) -> None:
    import jslb

    header: Any = line[0]
    payload = jslb.payload_of(cast(jslb.Object, line))
    if (
        jslb.field_get(header, "type") != "error"
        or jslb.field_get(header, "reply") != reply
        or list(payload) != ["message", "stack"]
        or payload["message"] != message
    ):
        raise CheckFailed(
            f"{what}: the server wrote {line_text(line)} where an error line"
            f" with the message {message!r} and r {reply} was due"
        )


# Fails unless the reply holds exactly the payload and no blob.
def payload_check(reply: LineObject, due: dict[str, Any], what: str) -> None:
    import jslb

    line = cast(jslb.Object, reply)
    if jslb.payload_of(line) != due or len(jslb.headers_of(line)) != 1:
        shown = json.dumps(due, ensure_ascii=False)
        raise CheckFailed(
            f"{what}: the server wrote {line_text(reply)} where the payload"
            f" {shown} and no blob were due"
        )


# Fails unless the reply is the echo of the request: its payload and blobs.
def echo_check(request: LineObject, reply: LineObject, what: str) -> None:
    import jslb

    asked = cast(jslb.Object, request)
    header: Any = asked[0]
    sent = blobs_of(asked)
    expected = jslb.line_make(
        jslb.header_make(
            _ECHO_TYPE,
            reply=jslb.field_get(header, "id"),
            full="type" in header,
        ),
        [jslb.blob_make(data) for data in sent],
        **jslb.payload_of(asked),
    )
    if line_text(reply) != line_text(expected):
        raise CheckFailed(
            f"{what}: the server wrote {line_text(reply)} where"
            f" {line_text(expected)} was due"
        )
    for number, (came, went) in enumerate(zip(blobs_of(reply), sent), 1):
        if came != went:
            raise CheckFailed(
                f"{what}: blob {number} came back {len(came)} bytes, sha256"
                f" {sha256_text(came)}, where {len(went)} bytes, sha256"
                f" {sha256_text(went)}, went"
            )


# Fails unless the file holds exactly the bytes.
def file_check(path: str, data: bytes) -> None:
    with open(path, "rb") as file:
        found = file.read()
    if found != data:
        raise CheckFailed(
            f"{path} holds {len(found)} bytes, sha256 {sha256_text(found)},"
            f" where {len(data)} bytes, sha256 {sha256_text(data)}, were put"
        )


# The bytes of the echo main loop file in the checkout.
def echo_source() -> bytes:
    with open(_ECHO_PATH, "rb") as file:
        return file.read()


# Returns the parent's pid, the second field after the name in brackets.
def process_parent(pid: int) -> int:
    with open(f"/proc/{pid}/stat", "rb") as file:
        stat = file.read()
    return int(stat[stat.rindex(b")") + 2 :].split()[1])


# Fails unless the pid is ttyd's child running its command and the arguments.
def program_check(ttyd: TtydServer, pid: int, args: tuple[str, ...]) -> None:
    with open(f"/proc/{pid}/cmdline", "rb") as file:
        cmdline = file.read().split(b"\0")[:-1]
    due = [word.encode() for word in (*ttyd.command, *args)]
    if cmdline != due:
        raise CheckFailed(f"hello's pid {pid} runs {cmdline}, not {due}")
    parent = process_parent(pid)
    if parent != ttyd.process.pid:
        raise CheckFailed(
            f"hello's pid {pid} is the child of {parent}, not of ttyd's"
            f" {ttyd.process.pid}"
        )


# Reads a process's resident size and its peak, in KiB, from its status file.
def memory_read(pid: int) -> MemoryUse:
    fields: dict[str, int] = {}
    with open(f"/proc/{pid}/status", encoding="utf-8") as file:
        for row in file:
            name, _, value = row.partition(":")
            if name in ("VmRSS", "VmHWM"):
                fields[name] = int(value.split()[0])
    return MemoryUse(fields["VmRSS"], fields["VmHWM"])


# Reads `hello`, checks it came from ttyd's child, answers it, keeps its facts.
def hello_take(
    client: WireClient,
    values: dict[str, Any],
    args: tuple[str, ...],
    what: str,
) -> None:
    import jslb

    ttyd = client.ttyd
    line = line_next(client, what)
    header: Any = line[0]
    payload = jslb.payload_of(cast(jslb.Object, line))
    path = ttyd.command[1]
    with open(path, "rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    due: dict[str, Any] = {
        "bootstrap": path,
        "sha256": digest,
        "root": ttyd.root,
        "settings": values,
        "provider_key": _PROVIDER_KEY,
    }
    full = "type" in header
    form = "full" if values["debug"] else "short"
    if (
        jslb.field_get(header, "type") != "hello"
        or jslb.field_get(header, "id") != _HELLO_ID
        or len(header) != 2
        or full != values["debug"]
        or list(payload) != _HELLO_FIELDS
        or any(payload[name] != value for name, value in due.items())
    ):
        raise CheckFailed(
            f"{what}: the program wrote {line_text(line)} where hello with id"
            f" {_HELLO_ID} in {form} names was due from {path}, sha256"
            f" {digest}, with the root {ttyd.root}, its settings and the"
            f" provider key {_PROVIDER_KEY}"
        )
    title = f"{' '.join(ttyd.command)} ({socket.gethostname()})"
    if client.title != title:
        raise CheckFailed(
            f"{ttyd.version}'s title is {client.title!r}, not {title!r}"
        )
    pid = cast(int, payload["pid"])
    program_check(ttyd, pid, args)
    client.pid = pid
    client.seq = cast(dict[str, int], payload["seq"])
    client.full = full
    answer = jslb.header_make("hello", reply=_HELLO_ID, full=full)
    line_send(client, jslb.line_make(answer, []))


# Fails unless ttyd logged that the program of that pid exited with code 1.
def exit_check(ttyd: TtydServer, pid: int, what: str) -> None:
    how, number = ttyd.end_wait(pid, what)
    if (how, number) != (_EXITED_WORDS, _PROGRAM_FAILED):
        raise CheckFailed(
            f"{ttyd.version} logged that the process of pid {pid} {how}"
            f" {number}, where it exited with code {_PROGRAM_FAILED}"
        )


# Fails unless the next end ttyd logs from `mark` on is an exit with code 1.
def exit_after(ttyd: TtydServer, mark: int, what: str) -> int:
    _, found = ttyd.line_wait(_ENDED_PATTERN, what, mark)
    if found.group(1, 2) != (_EXITED_WORDS, str(_PROGRAM_FAILED)):
        raise CheckFailed(f"{ttyd.version} logged: {found.string}")
    return int(found.group(3))


# Fails unless the raw output from the mark on is the expected bytes.
def transcript_check(
    client: WireClient, mark: int, expected: bytes, what: str
) -> None:
    shown = bytes(client.output[mark:])
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
        f"{what} through {client.ttyd.version} is {len(shown)} bytes where"
        f" {len(expected)} were due, unequal from byte {at}:"
        f" {shown[start:end]!r} where {expected[start:end]!r} was due; a"
        " loss is a ttyd fault, reported and not retried"
    )


# Opens the echo main loop's connection and checks `hello`, with a summary.
def rung_hello(
    ttyd: TtydServer, values: dict[str, Any]
) -> tuple[WireClient, str]:
    opened_at = time.monotonic()
    client = websocket_open(ttyd, _ECHO_ARGS, values, False)
    hello_take(client, values, _ECHO_ARGS, "hello")
    seconds = time.monotonic() - opened_at
    if client.seq:
        raise CheckFailed(
            f"hello's seq is {client.seq}, where the echo main loop, which"
            " opens no database, gives none"
        )
    form = "full" if client.full else "short"
    running = " ".join([*ttyd.command, *_ECHO_ARGS])
    return client, (
        f"ttyd's title {client.title!r} and preferences"
        f" {json.dumps(client.preferences)}; hello with id {_HELLO_ID} in"
        f" {form} names from pid {client.pid}, ttyd's child running"
        f" {running}, with bootstrap.py's path and sha256, the root, the"
        " root's settings, no seq and the provider key of ttyd's"
        f" environment, {seconds:.3f} s after the WebSocket opened; answered"
        " with an empty reply"
    )


# Echoes a payload, then a payload with a small blob and an empty one.
def rung_echo(client: WireClient) -> str:
    started = time.monotonic()
    what = "the echo of a payload"
    plain = request_make(
        client, client.full, _ECHO_TYPE, [], None, _ECHO_PAYLOAD
    )
    echo_check(plain, exchange_run(client, plain, what), what)
    what = "the echo of two blobs"
    pair = [_SMALL_BYTES, b""]
    blobs = request_make(
        client, client.full, _ECHO_TYPE, pair, None, _ECHO_PAYLOAD
    )
    echo_check(blobs, exchange_run(client, blobs, what), what)
    seconds = time.monotonic() - started
    return (
        "a payload of text in 2, 3 and 4 byte characters, a negative number"
        " and a nested list came back equal, its r the request's i; then the"
        f" same with a blob of the {len(_SMALL_BYTES)} control bytes below"
        f" space and an empty blob, equal byte for byte; {seconds:.3f} s for"
        " both"
    )


# Echoes 1 MiB of every byte value, which the server streams through a file.
def rung_control(client: WireClient, values: dict[str, Any]) -> str:
    what = "the 1 MiB echo"
    request = request_make(
        client, client.full, _ECHO_TYPE, [_CONTROL_BYTES], None, {}
    )
    before = client.ttyd_messages
    started = time.monotonic()
    echo_check(request, exchange_run(client, request, what), what)
    seconds = time.monotonic() - started
    return (
        f"one blob of {len(_CONTROL_BYTES)} bytes, every byte value"
        f" {len(_CONTROL_BYTES) // 256} times, CR, LF, 0x03, 0x04, 0x13 and"
        " bytes invalid in UTF-8 among them, over overflow_bytes"
        f" {values['overflow_bytes']} so the server streamed it through a"
        " cache file, came back equal, sha256"
        f" {sha256_text(_CONTROL_BYTES)[:12]}, in"
        f" {client.ttyd_messages - before} ttyd messages, {seconds:.3f} s"
    )


# Echoes a request whose one blob is exactly `blob_max` bytes, short names.
def rung_fit(client: WireClient, values: dict[str, Any]) -> str:
    what = "the echo of a blob of blob_max bytes"
    blob_max: int = values["blob_max"]
    request = request_make(
        client, False, _ECHO_TYPE, [os.urandom(blob_max)], None, {}
    )
    sent = message_bytes(request)
    started = time.monotonic()
    reply = exchange_run(client, request, what)
    seconds = time.monotonic() - started
    echo_check(request, reply, what)
    return (
        f"a request in short names with one blob of blob_max {blob_max}"
        f" random bytes, {sent} bytes with its line, came back equal in a"
        f" reply of {message_bytes(reply)} bytes, {seconds:.3f} s"
    )


# Echoes 128 MiB as one message, measuring ttyd's resident size.
def rung_large(client: WireClient, values: dict[str, Any]) -> str:
    what = "the large echo"
    ttyd = client.ttyd
    before = memory_read(ttyd.process.pid)
    request = request_make(
        client, False, _ECHO_TYPE, [os.urandom(_LARGE_BYTES)], None, {}
    )
    started = time.monotonic()
    reply = exchange_run(client, request, what)
    seconds = time.monotonic() - started
    echo_check(request, reply, what)
    after = memory_read(ttyd.process.pid)
    rate = _LARGE_BYTES / _MIB / seconds
    return (
        f"one request in short names with a blob of {_LARGE_BYTES} random"
        f" bytes, within blob_max {values['blob_max']}, came back equal;"
        f" {seconds:.2f} s, {rate:.1f} MiB/s each way; ttyd's resident size"
        f" {before.resident} KiB before and {after.resident} KiB after, its"
        f" peak {after.peak} KiB"
    )


# Opens a second engine connection, which the lock refuses, then echoes.
def rung_second(client: WireClient, values: dict[str, Any]) -> str:
    from i18n import i18n

    ttyd = client.ttyd
    mark = len(ttyd.lines)
    other = websocket_open(ttyd, _ECHO_ARGS, values, False)
    message = i18n("bootstrap.lock_held", os.path.join(ttyd.root, _LOCK_NAME))
    what = "the second connection's error line"
    error_check(line_last(other, what), None, message, what)
    pid = exit_after(ttyd, mark, "ttyd's log of the second program's end")
    if pid == client.pid:
        raise CheckFailed(f"{ttyd.version} logged the end of pid {pid}")
    what = "the first connection's echo"
    echo = request_make(
        client, client.full, _ECHO_TYPE, [], None, _ECHO_PAYLOAD
    )
    echo_check(echo, exchange_run(client, echo, what), what)
    return (
        "a second WebSocket on the same root got ttyd's title"
        f" {other.title!r}, then no hello but the error {message!r} with no"
        f" r, and its program, pid {pid}, exited with code {_PROGRAM_FAILED}"
        f" as ttyd logged; {connection_end(other)}; the first connection, pid"
        f" {client.pid}, still echoed"
    )


# Sends a line announcing blobs one byte over `blob_max`, refused at its CR.
def rung_over(client: WireClient, values: dict[str, Any]) -> str:
    from i18n import i18n

    blob_max: int = values["blob_max"]
    half = blob_max // 2
    sizes = [half, blob_max - half + 1]
    text = echo_text(False, client.id_next(), sizes)
    client.input_send(text)
    message = i18n("jslb.blobs_over", blob_max + 1, blob_max)
    what = "the error line of the blobs over blob_max"
    error_check(line_last(client, what), None, message, what)
    exit_check(client.ttyd, client.pid, "ttyd's log of the program's end")
    return (
        f"a line of {len(text)} bytes announcing blobs of {sizes[0]} and"
        f" {sizes[1]} bytes, {blob_max + 1} in all, sent without the blobs:"
        f" the server wrote the error {message!r} with no r at the line's CR,"
        f" before any blob byte, and exited with code {_PROGRAM_FAILED} as"
        f" ttyd logged; {connection_end(client)}"
    )


# The last line regression: on the console a subshell prints and exits.
def rung_lines(ttyd: TtydServer, values: dict[str, Any]) -> str:
    client = websocket_open(ttyd, _CONSOLE_ARGS, values, True)
    client_wait(
        client,
        lambda: client.output.endswith(_PROMPT) or client.ended,
        "dash's prompt",
    )
    if client.output != _PROMPT:
        raise CheckFailed(
            f"the console showed {bytes(client.output)!r} through"
            f" {ttyd.version} where dash's prompt {_PROMPT!r} was due"
        )
    typed = _LINES_COMMAND + "\n"
    numbers = "".join(f"{number}\n" for number in range(1, _LINES_COUNT + 1))
    expected = terminal_text(typed + numbers) + _PROMPT
    mark = len(client.output)
    before = client.ttyd_messages
    started = time.monotonic()
    client.input_send(typed.encode())
    client_wait(
        client,
        lambda: (
            client.ended
            or (
                len(client.output) - mark >= len(expected)
                and client.output.endswith(_PROMPT)
            )
        ),
        "the lines and the prompt after them",
    )
    seconds = time.monotonic() - started
    transcript_check(client, mark, expected, "the subshell's lines")
    messages = client.ttyd_messages - before
    session_close(client)
    return (
        f"on the console role, dash's prompt, then {typed!r} echoed and its"
        f" subshell's {_LINES_COUNT} lines in order, the last of them just"
        " before the subshell exited, then the prompt:"
        f" {len(expected)} bytes equal to this client's in {messages} ttyd"
        f" messages, {seconds:.2f} s from the command to the prompt; close"
        f" {_CLOSE_NORMAL} answered with {_CLOSE_NORMAL}"
    )


# Kills ttyd under an engine connection and checks what ends and how.
def rung_killed(ttyd: TtydServer, values: dict[str, Any]) -> str:
    client = websocket_open(ttyd, _ECHO_ARGS, values, False)
    hello_take(client, values, _ECHO_ARGS, "hello")
    descriptor = os.pidfd_open(client.pid)
    try:
        client.end_expected = True
        killed_at = time.monotonic()
        ttyd.signal_send(signal.SIGKILL)
        client_wait(
            client,
            lambda: client.ended and ttyd.log_ended,
            "the end of the connection and of ttyd's log",
        )
        ended_seconds = time.monotonic() - killed_at
        status = ttyd.process.wait()
        if status != -signal.SIGKILL:
            raise CheckFailed(
                f"{ttyd.version} exited with {status} on SIGKILL"
            )
        readable: list[Any] = []
        while not readable:
            left = ttyd.log.timer.seconds_left(f"pid {client.pid} to end")
            readable, _, _ = select.select([descriptor], [], [], left)
        gone_seconds = time.monotonic() - killed_at
    finally:
        os.close(descriptor)
    client.sock.close()
    return (
        f"SIGKILL to {ttyd.version} with the echo main loop running as pid"
        f" {client.pid}: {ended_seconds:.4f} s after the kill"
        f" {connection_end(client)} and ttyd's log ended; ttyd exited with"
        f" {status}; pid {client.pid} was gone {gone_seconds:.3f} s after the"
        " kill"
    )


# The response to `tools/list`: each server tool of the API file, no permit.
def list_response() -> dict[str, Any]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    tools = [
        {
            "name": entry["name"],
            "description": entry["description"],
            "inputSchema": entry["inputSchema"],
        }
        for entry in data["server"]["result"]["tools"]
    ]
    return {"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}}


# Opens a stock connection, opens an MCP session on the `mcp` line, calls.
def rung_mcp(
    ttyd: TtydServer, values: dict[str, Any]
) -> tuple[WireClient, str]:
    import jslb

    client = websocket_open(ttyd, _STOCK_ARGS, values, False)
    hello_take(client, values, _STOCK_ARGS, "hello")
    what = "the reply to initialize"
    request = request_make(
        client, client.full, "mcp", [], None, _INITIALIZE_MESSAGE
    )
    reply = exchange_run(client, request, what)
    payload_check(reply, _INITIALIZE_RESPONSE, what)
    line_send(client, notice_make(client, "mcp", _INITIALIZED_MESSAGE))
    what = "the reply to tools/list"
    request = request_make(client, client.full, "mcp", [], None, _LIST_MESSAGE)
    reply = exchange_run(client, request, what)
    payload_check(reply, list_response(), what)
    source = echo_source()
    digest = sha256_text(source)
    arguments = {"name": _TOOL_NAME, "text": source.decode("utf-8")}
    message = {
        "jsonrpc": "2.0",
        "id": _CALL_ID,
        "method": "tools/call",
        "params": {"name": "source_put", "arguments": arguments},
    }
    what = "the reply to tools/call"
    request = request_make(client, client.full, "mcp", [], None, message)
    reply = exchange_run(client, request, what)
    result_text = json.dumps({"sha256": digest}, separators=(",", ":"))
    response: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": _CALL_ID,
        "result": {
            "content": [{"type": "text", "text": result_text}],
            "isError": False,
        },
    }
    if jslb.payload_of(cast(jslb.Object, reply)) != response:
        raise CheckFailed(
            f"{what}: the server wrote {line_text(reply)} where"
            f" {json.dumps(response)} was due"
        )
    path = os.path.join(ttyd.root, _MAIN_LOOP_DIRECTORY, _TOOL_NAME)
    file_check(path, source)
    return client, (
        f"hello from pid {client.pid}; initialize, notifications/initialized"
        " with no reply and tools/list sent on the mcp line, each reply the"
        " response the protocol and API/mcp/tools.json give; tools/call of"
        f" source_put, unasked, wrote {_TOOL_NAME} of {len(source)} bytes"
        f" equal to the file and answered its sha256 {digest[:12]}"
    )


# Puts 1 MiB under a ref, streamed through the cache, and gets it back.
def rung_kv(client: WireClient) -> str:
    import jslb

    since = client.seq[_FILES_DB]
    digest = sha256_text(_CONTROL_BYTES)
    put = request_make(
        client,
        client.full,
        "kv.put",
        [_CONTROL_BYTES],
        _VALUE_REF,
        {"since": since},
    )
    reply = exchange_run(client, put, "the reply to kv.put")
    payload_check(reply, {"sha256": digest, "seq": since + 1}, "kv.put")
    client.seq[_FILES_DB] = since + 1
    get = request_make(client, client.full, "kv.get", [], _VALUE_REF, {})
    reply = exchange_run(client, get, "the reply to kv.get")
    due = {"size": len(_CONTROL_BYTES), "sha256": digest}
    blobs = blobs_of(reply)
    if jslb.payload_of(cast(jslb.Object, reply)) != due or blobs != [
        _CONTROL_BYTES
    ]:
        raise CheckFailed(
            f"kv.get: the server wrote {line_text(reply)} with blobs of"
            f" {[len(blob) for blob in blobs]} bytes where {json.dumps(due)}"
            " and the bytes put were due"
        )
    return (
        f"kv.put of {len(_CONTROL_BYTES)} bytes, every byte value, under"
        f" {_VALUE_REF} with since {since}: sha256 {digest[:12]} and seq"
        f" {since + 1}; kv.get gave the size, the sha256 and the bytes back,"
        " byte for byte"
    )


# Puts a document and reads the ref of its head.
def rung_doc(client: WireClient) -> str:
    since = client.seq[_METAVERSE_DB]
    ref = f"/{_METAVERSE_DB}/{_DOCUMENT_ID}/{_DOCUMENT_VERSION}"
    document = {
        "db": _METAVERSE_DB,
        "id": _DOCUMENT_ID,
        "body": _DOCUMENT_BODY,
        "since": since,
    }
    put = request_make(client, client.full, "doc.put", [], None, document)
    reply = exchange_run(client, put, "the reply to doc.put")
    payload_check(reply, {"ref": ref, "seq": since + 1}, "doc.put")
    client.seq[_METAVERSE_DB] = since + 1
    names = {"db": _METAVERSE_DB, "id": _DOCUMENT_ID}
    head = request_make(client, client.full, "doc.head", [], None, names)
    reply = exchange_run(client, head, "the reply to doc.head")
    payload_check(reply, {"ref": ref}, "doc.head")
    return (
        f"doc.put of {_DOCUMENT_ID} in {_METAVERSE_DB} with since {since}:"
        f" ref {ref} and seq {since + 1}; doc.head gave the same ref"
    )


# Puts lines of a page thread and reads the last of them back, oldest first.
def rung_verbose(client: WireClient) -> str:
    import jslb

    at = time.time_ns() // _NANOSECONDS_PER_MILLISECOND
    lines = [
        {"at": at, "text": f"{_WIDE_TEXT} {number}"}
        for number in range(_PUT_COUNT)
    ]
    put = {"thread": _PAGE_THREAD, "lines": lines}
    line_send(client, notice_make(client, "verbose.put", put))
    asked = {"thread": _PAGE_THREAD, "count": _TAIL_COUNT}
    tail = request_make(client, client.full, "verbose.tail", [], None, asked)
    reply = exchange_run(client, tail, "the reply to verbose.tail")
    payload_check(reply, {"lines": lines[-_TAIL_COUNT:]}, "verbose.tail")
    asked = {"thread": _SERVER_THREAD, "count": _TAIL_COUNT}
    tail = request_make(client, client.full, "verbose.tail", [], None, asked)
    reply = exchange_run(client, tail, "the server's verbose.tail")
    payload = jslb.payload_of(cast(jslb.Object, reply))
    if list(payload) != ["lines"]:
        raise CheckFailed(
            f"the server's verbose.tail: the server wrote {line_text(reply)}"
        )
    server_lines: list[Any] = payload["lines"]
    return (
        f"verbose.put of {len(lines)} lines on thread {_PAGE_THREAD}, a"
        f" notification with no reply, then verbose.tail of {_TAIL_COUNT}"
        f" gave its last {_TAIL_COUNT}, oldest first, equal to what was put;"
        f" verbose.tail of thread {_SERVER_THREAD} answered"
        f" {len(server_lines)} lines"
    )


# Sends a type no handler serves: one error line, then exit 1.
def rung_unknown(client: WireClient) -> str:
    from i18n import i18n

    request = request_make(client, client.full, _UNKNOWN_TYPE, [], None, {})
    line_send(client, request)
    message = i18n("dispatch.handler_unknown", _UNKNOWN_TYPE, _LINE_VERSION)
    what = "the error line of the unknown type"
    error_check(line_last(client, what), client.id_last, message, what)
    exit_check(client.ttyd, client.pid, "ttyd's log of the program's end")
    return (
        f"{_UNKNOWN_TYPE} with i {client.id_last}: the error {message!r}"
        f" with r {client.id_last}, the program's last line, then pid"
        f" {client.pid} exited with code {_PROGRAM_FAILED} as ttyd logged;"
        f" {connection_end(client)}"
    )


# A statement as `sql.run` carries it: its text and its bound parameters.
def statement_make(sql: str, params: list[Any]) -> dict[str, Any]:
    return {"sql": sql, "params": params}


# The result of one statement as the reply to `sql.run` gives it.
def result_make(
    columns: list[str], rows: list[list[Any]], changes: int
) -> dict[str, Any]:
    return {"columns": columns, "rows": rows, "changes": changes}


# Builds the replay: new databases written by each forwarded operation.
def replay_build(large: bytes) -> ReplaySequence:
    sequence = ReplaySequence()
    db = _REPLAY_DB
    sequence.database_create(db)
    sequence.statements_run(
        db, [statement_make(_PAIR_DDL, [])], [result_make([], [], 0)]
    )
    values: list[Any] = [value for row in _PAIR_ROWS for value in row]
    sequence.statements_run(
        db,
        [statement_make(_PAIR_INSERT, values)],
        [result_make([], [], len(_PAIR_ROWS))],
    )
    sequence.value_put(db, _SMALL_KEY, _SMALL_BYTES)
    sequence.value_put(db, _LARGE_KEY, large)
    sequence.value_delete(db, _SMALL_KEY)
    sequence.document_put(db, _SCENE_ID, _SCENE_BODY, _SCENE_REF)
    for n, (role, text) in enumerate(_TURNS, 1):
        sequence.turn_append(db, _SCENE_REF, role, text, n)
    sequence.turns_compact(db, _SCENE_REF, len(_TURNS), _SUMMARY_TEXT)
    updated = [_PAIR_VALUE, _PAIR_ROWS[1][0]]
    sequence.statements_run(
        db,
        [statement_make(_PAIR_UPDATE, updated)],
        [result_make([], [], 1)],
    )
    sequence.database_create(_DROPPED_DB)
    sequence.value_put(_DROPPED_DB, _DROPPED_KEY, _SMALL_BYTES)
    sequence.database_drop(_DROPPED_DB)
    return sequence


# Reads the replay back on a new program: its value, keys, head and rows.
def replay_read(client: WireClient, large: bytes, seq: int) -> None:
    import jslb

    digest = sha256_text(large)
    ref = f"/{_REPLAY_DB}/{_LARGE_KEY}"
    get = request_make(client, client.full, "kv.get", [], ref, {})
    reply = exchange_run(client, get, "the reply to kv.get")
    due: dict[str, Any] = {"size": len(large), "sha256": digest}
    blobs = blobs_of(reply)
    if jslb.payload_of(cast(jslb.Object, reply)) != due or blobs != [large]:
        raise CheckFailed(
            f"kv.get: the server wrote {line_text(reply)} with blobs of"
            f" {[len(blob) for blob in blobs]} bytes where {json.dumps(due)}"
            " and the bytes the replay put were due"
        )
    asked: dict[str, Any] = {"db": _REPLAY_DB, "prefix": _BLOB_PREFIX}
    listed = request_make(client, client.full, "kv.list", [], None, asked)
    reply = exchange_run(client, listed, "the reply to kv.list")
    row = {"k": _LARGE_KEY, "size": len(large), "sha256": digest}
    payload_check(reply, {"keys": [row]}, "kv.list")
    names: dict[str, Any] = {"db": _REPLAY_DB, "id": _SCENE_ID}
    head = request_make(client, client.full, "doc.head", [], None, names)
    reply = exchange_run(client, head, "the reply to doc.head")
    payload_check(reply, {"ref": _SCENE_REF}, "doc.head")
    statements = [
        statement_make(_PAIR_SELECT, []),
        statement_make(_TURN_SELECT, [_SUMMARY_TEXT, _SCENE_REF]),
    ]
    first, second = _PAIR_ROWS
    pairs: list[list[Any]] = [list(first), [second[0], _PAIR_VALUE]]
    turns: list[list[Any]] = [list(row) for row in _TURN_ROWS]
    results = [
        result_make(list(_PAIR_COLUMNS), pairs, 0),
        result_make(list(_TURN_COLUMNS), turns, 0),
    ]
    read: dict[str, Any] = {
        "db": _REPLAY_DB,
        "statements": statements,
        "since": seq,
    }
    run = request_make(client, client.full, "sql.run", [], None, read)
    reply = exchange_run(client, run, "the reply to sql.run")
    payload_check(reply, {"results": results, "seq": seq}, "sql.run")


# Replays the sequence the test builds, then reads it back on a new program.
def rung_replay(ttyd: TtydServer, values: dict[str, Any]) -> str:
    from i18n import i18n

    large = os.urandom(values["overflow_bytes"] + 1)
    sequence = replay_build(large)
    first = websocket_open(ttyd, _STOCK_ARGS, values, False)
    hello_take(first, values, _STOCK_ARGS, "hello")
    started = time.monotonic()
    for number, step in enumerate(sequence.steps, 1):
        what = f"the reply to operation {number}, {step.line_type}"
        request = request_make(
            first,
            first.full,
            step.line_type,
            step.blobs,
            step.key,
            step.payload,
        )
        payload_check(exchange_run(first, request, what), step.due, what)
    seconds = time.monotonic() - started
    session_close(first)
    ttyd.end_wait(first.pid, "ttyd's log of the first program's end")
    second = websocket_open(ttyd, _STOCK_ARGS, values, False)
    hello_take(second, values, _STOCK_ARGS, "hello after the replay")
    seq_due = {**first.seq, **sequence.seq}
    if second.seq != seq_due:
        raise CheckFailed(
            f"hello after the replay gave seq {second.seq}, where {seq_due}"
            " was due"
        )
    seq = sequence.seq[_REPLAY_DB]
    replay_read(second, large, seq)
    stale = seq - 1
    ref = f"/{_REPLAY_DB}/{_SMALL_KEY}"
    put = request_make(
        second, second.full, "kv.put", [_SMALL_BYTES], ref, {"since": stale}
    )
    line_send(second, put)
    message = i18n("substrate.since_stale", "kv.put", stale, seq, _REPLAY_DB)
    what = "the error line of the stale since"
    error_check(line_last(second, what), second.id_last, message, what)
    exit_check(ttyd, second.pid, "ttyd's log of the second program's end")
    types = dict.fromkeys(step.line_type for step in sequence.steps)
    kinds = ", ".join(types)
    return (
        f"{len(sequence.steps)} forwarded operations the test built, {kinds},"
        f" each with the since of its database, replayed on pid {first.pid}"
        f" in {seconds:.3f} s, each reply the one due; after a reconnect,"
        f" hello from pid {second.pid} gave {_REPLAY_DB} seq {seq} and no"
        f" {_DROPPED_DB}; kv.get, kv.list, doc.head and a sql.run read gave"
        " back what the replay put, deleted, appended and compacted; a kv.put"
        f" with the stale since {stale} got the error {message!r} and pid"
        f" {second.pid} exited with code {_PROGRAM_FAILED} as ttyd logged"
    )


# Puts the echo main loop with `source.put`, then `system.restart` serves it.
def rung_restart(ttyd: TtydServer, values: dict[str, Any]) -> str:
    client = websocket_open(ttyd, _STOCK_ARGS, values, False)
    hello_take(client, values, _STOCK_ARGS, "hello")
    first_pid = client.pid
    source = echo_source()
    named = {"name": _ECHO_NAME}
    put = request_make(
        client, client.full, "source.put", [source], None, named
    )
    reply = exchange_run(client, put, "the reply to source.put")
    payload_check(reply, {"sha256": sha256_text(source)}, "source.put")
    path = os.path.join(ttyd.root, _MAIN_LOOP_DIRECTORY, _ECHO_NAME)
    file_check(path, source)
    chosen = {"main_loop": _ECHO_NAME}
    restart = request_make(
        client, client.full, "system.restart", [], None, chosen
    )
    restart_id = client.id_last
    started = time.monotonic()
    line_send(client, restart)
    what = "a second hello, where no reply to system.restart is due"
    hello_take(client, values, _ECHO_ARGS, what)
    seconds = time.monotonic() - started
    if client.pid != first_pid or client.seq:
        raise CheckFailed(
            f"the second hello came from pid {client.pid} with seq"
            f" {client.seq}, where the pid {first_pid} the restart keeps and"
            " the echo main loop's empty seq were due"
        )
    what = "the echo of the second main loop"
    echo = request_make(
        client, client.full, _ECHO_TYPE, [], None, _ECHO_PAYLOAD
    )
    echo_check(echo, exchange_run(client, echo, what), what)
    session_close(client)
    return (
        f"on the stock main loop of pid {first_pid}, source.put of"
        f" {len(source)} bytes as {_ECHO_NAME} answered its sha256, equal to"
        f" the file's; system.restart with i {restart_id} got no reply, and"
        f" {seconds:.3f} s after it a second hello came from the same pid,"
        f" now running {_ECHO_NAME}, which then echoed; close {_CLOSE_NORMAL}"
        f" answered with {_CLOSE_NORMAL}"
    )


# With debug false: `source.put`, a restart and a main loop file refused.
def rung_refused(ttyd: TtydServer, values: dict[str, Any]) -> str:
    from i18n import i18n

    source = echo_source()
    first = websocket_open(ttyd, _STOCK_ARGS, values, False)
    hello_take(first, values, _STOCK_ARGS, "hello")
    named = {"name": _ECHO_NAME}
    put = request_make(first, first.full, "source.put", [source], None, named)
    line_send(first, put)
    put_message = i18n("engine_system.debug_off", "source.put")
    what = "the error line of source.put"
    error_check(line_last(first, what), first.id_last, put_message, what)
    exit_check(ttyd, first.pid, "ttyd's log of the first program's end")
    path = os.path.join(ttyd.root, _MAIN_LOOP_DIRECTORY, _ECHO_NAME)
    if os.path.lexists(path):
        raise CheckFailed(f"{path} exists after source.put was refused")
    second = websocket_open(ttyd, _STOCK_ARGS, values, False)
    hello_take(second, values, _STOCK_ARGS, "hello")
    chosen = {"main_loop": _ECHO_NAME}
    restart = request_make(
        second, second.full, "system.restart", [], None, chosen
    )
    line_send(second, restart)
    restart_message = i18n("engine_system.debug_off", "system.restart")
    what = "the error line of system.restart"
    error_check(line_last(second, what), second.id_last, restart_message, what)
    exit_check(ttyd, second.pid, "ttyd's log of the second program's end")
    mark = len(ttyd.lines)
    third = websocket_open(ttyd, _ECHO_ARGS, values, False)
    loop_message = i18n("bootstrap.main_loop_refused", _ECHO_NAME)
    what = "the error line of the main loop option"
    error_check(line_last(third, what), None, loop_message, what)
    pid = exit_after(ttyd, mark, "ttyd's log of the third program's end")
    return (
        "on a root whose setting debug is false, hello in short names from"
        f" pid {first.pid}, then source.put refused with {put_message!r}"
        f" and r {first.id_last}, nothing written; on a new connection"
        f" system.restart refused with {restart_message!r}; a connection"
        f" with --main-loop {_ECHO_NAME} got no hello but {loop_message!r};"
        f" each program, the last pid {pid}, exited with code"
        f" {_PROGRAM_FAILED} as ttyd logged"
    )


# Makes a root as the start script does, its setting debug as given.
def root_make(work: str, name: str, debug: bool) -> tuple[str, dict[str, Any]]:
    root = os.path.join(work, name)
    python_path = os.path.join(root, "python")
    os.makedirs(python_path)
    for module in _RUNTIME_MODULES:
        file_name = module + ".py"
        shutil.copyfile(
            os.path.join(_PYTHON_PATH, file_name),
            os.path.join(python_path, file_name),
        )
    shutil.copytree(_SEED_PATH, os.path.join(python_path, "seed"))
    strings_path = os.path.join(root, "i18n")
    os.makedirs(strings_path)
    shutil.copyfile(_STRINGS_PATH, os.path.join(strings_path, "en-US.json"))
    with open(_SETTINGS_PATH, encoding="utf-8") as file:
        values: dict[str, Any] = json.load(file)
    values["debug"] = debug
    text = json.dumps(values, ensure_ascii=False, indent=2) + "\n"
    with open(
        os.path.join(root, "settings.json"), "w", encoding="utf-8"
    ) as file:
        file.write(text)
    return root, values


# The rungs on a root whose `--main-loop` serves the echo main loop file.
def stage_echo(log: RungLog, work: str) -> None:
    if not log.book.root_enter("echo", "smoke-test"):
        return
    root, values = root_make(work, "echo", True)
    directory = os.path.join(root, _MAIN_LOOP_DIRECTORY)
    os.makedirs(directory)
    shutil.copyfile(_ECHO_PATH, os.path.join(directory, _ECHO_NAME))
    log.rung_start("ttyd")
    with TtydServer(root, values, log) as ttyd:
        log.rung_open("hello", "smoke-test")
        client, summary = rung_hello(ttyd, values)
        log.rung_print(summary, "smoke-test")
        log.rung_run("echo", "smoke-test", lambda: rung_echo(client))
        log.rung_run(
            "echo 1 MiB with control bytes",
            "smoke-test",
            lambda: rung_control(client, values),
        )
        log.rung_run(
            "echo blob_max", "normal-test", lambda: rung_fit(client, values)
        )
        log.rung_run(
            "echo 128 MiB", "normal-test", lambda: rung_large(client, values)
        )
        log.rung_run(
            "second connection refused",
            "smoke-test",
            lambda: rung_second(client, values),
        )
        log.rung_run(
            "blob_max plus one refused",
            "smoke-test",
            lambda: rung_over(client, values),
        )
        log.rung_run(
            "last line", "smoke-test", lambda: rung_lines(ttyd, values)
        )
        log.rung_run(
            "ttyd killed", "smoke-test", lambda: rung_killed(ttyd, values)
        )
    log.book.root_leave()


# The rungs on a root that serves the stock main loop in debug mode.
def stage_stock(log: RungLog, work: str) -> None:
    if not log.book.root_enter("stock", "smoke-test"):
        return
    root, values = root_make(work, "stock", True)
    log.rung_start("ttyd")
    with TtydServer(root, values, log) as ttyd:
        log.rung_open("mcp line", "smoke-test")
        client, summary = rung_mcp(ttyd, values)
        log.rung_print(summary, "smoke-test")
        log.rung_run(
            "kv.put and kv.get", "smoke-test", lambda: rung_kv(client)
        )
        log.rung_run(
            "doc.put and doc.head", "smoke-test", lambda: rung_doc(client)
        )
        log.rung_run(
            "verbose.tail", "smoke-test", lambda: rung_verbose(client)
        )
        log.rung_run(
            "unknown type", "smoke-test", lambda: rung_unknown(client)
        )
        log.rung_run(
            "operation sequence replayed",
            "smoke-test",
            lambda: rung_replay(ttyd, values),
        )
        log.rung_run(
            "system.restart", "smoke-test", lambda: rung_restart(ttyd, values)
        )
    log.book.root_leave()


# The rung on a root whose setting debug is false.
def stage_release(log: RungLog, work: str) -> None:
    if not log.book.root_enter("release", "smoke-test"):
        return
    root, values = root_make(work, "release", False)
    log.rung_start("ttyd")
    with TtydServer(root, values, log) as ttyd:
        log.rung_run(
            "system.restart refused without debug",
            "smoke-test",
            lambda: rung_refused(ttyd, values),
        )
    log.book.root_leave()


# Exits with 128 plus the signal's number, so the blocks stop ttyd.
def signal_exit(number: int, frame: types.FrameType | None) -> None:
    sys.exit(_SIGNAL_BASE + number)


# Runs the rungs of the chosen category in order and returns the exit code.
def main(arguments: list[str]) -> int:
    import category

    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description="Run the wire test: the server in roots under build/,"
        " through the ttyd the install script builds, from a standard"
        " library WebSocket client.",
    )
    category.options_add(parser)
    chosen: str = parser.parse_args(arguments).category
    for number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(number, signal_exit)
    log = RungLog(chosen)
    try:
        if not os.path.isfile(_TTYD_PATH):
            raise CheckFailed(
                f"{_TTYD_PATH} is missing: {_INSTALL_SCRIPT} builds it"
            )
        with tempfile.TemporaryDirectory(
            prefix=_WORK_PREFIX, dir=_BUILD_PATH
        ) as work:
            stage_echo(log, work)
            stage_stock(log, work)
            stage_release(log, work)
    except CheckFailed as failure:
        print(f"error: {log.rung}: {failure}", file=sys.stderr)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        return _EXIT_INTERRUPTED
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
