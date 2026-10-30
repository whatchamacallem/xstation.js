#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The wire test, a TAP run: the producer is JavaScript in the page,
# ts/test_wire_rungs.ts, which runs the rungs on the page's own wire, and
# this file is the consumer. It builds the one page with page_build.py,
# makes three roots under build/ as the start script makes the server root,
# echo, stock and restart, each with its settings.json and its
# test_settings.json, whose typescript.run is "wire" and whose
# typescript.test_wire_rungs names the rungs the root runs and their gold.
# That gold is the rungs' fixed parameters, python.test_wire.rungs of the
# checkout's test_settings.json, with the parts known at run time added: the
# root, its rungs, the digest of the tool's text, and the text and digest of
# the restart's main loop file. The texts this file finds in the server's
# log, its timers and its sizes are python.test_wire too. Each root gets
# its own ttyd as python/ttyd_build.py builds it, given its
# options as the start script gives them and the built page as --index,
# running `python3 <root>/python/bootstrap.py --root <root>`, with
# --main-loop echo_loop.py on the echo root, and its own load of the page in
# chrome-headless-shell through devtools.LinuxPipe. The page meets ttyd's
# protocol as ts/wire.ts annotates it: the token from /token, /ws and
# /ws?arg=console with the subprotocol tty, a first message of JSON text,
# then '0' input, and from ttyd '0' output, '1' the title and '2' the
# preferences. That ttyd 1.7.7 accepts a first message without a size is
# from memory, owed to testing. The server appends each line of the page's
# stream to <root>/tap/typescript.tap; this file reads it as it grows,
# through tap_consumer.py, a line at a time under the timer of the rung it
# waits for, prints one line per point with its label and seconds, and
# stops at the first not ok, bail out or line that does not fit, naming it.
# Around the streams it makes the checks only this process can make: ttyd's
# resident size after the large rung and its end when killed after the echo
# stream; the stock server's database files, its log and its exit after the
# unknown rung; and on the restart root a stream that ended passing, then
# the server's exit and its pid kept by the exec, its log of the reply it
# did not expect to its second first line, which names the page's refusal
# or, by a race of the design, a verbose.put push of the page's log in
# flight across the exec, and the page's fault screen holding its refusal,
# where it always shows. Each root and rung is labelled smoke-test or
# normal-test: a smoke-test run, the default, leaves the normal-test rungs
# out of the gold, and a mislabel fails the run. It exits 0, or 1 at the
# first failed check, naming its rung. ttyd's log and the page's console are
# copied to stderr. ttyd, the browser and tsc through page_build.py are the
# programs it starts:
#
#     python3 python/test_wire.py [--smoke-test | --normal-test]

import argparse, contextlib, hashlib, json, os, pathlib, re, select, shutil
import signal, sqlite3, subprocess, sys, tempfile, time, types
from collections.abc import Callable
from typing import Any, NamedTuple, Protocol, Self, cast

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The checkout, which holds the `python` directory.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# The build directory: each run's roots, and the bytecode of what is imported.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# The id of this driver's gold in `test_settings.json`.
_GOLD_ID = "python.test_wire"

# The module that builds ttyd, which a missing ttyd names.
_BUILD_SCRIPT = os.path.join("python", "ttyd_build.py")

# The start of the name of the directory each run makes its roots in.
_WORK_PREFIX = "test_wire-"

# The template the page is built from, that of the ttyd test page.
_PAGE_TEMPLATE = "test"

# The name the page is built under, apart from the browser test's page.
_PAGE_NAME = "test_wire"

# The page `page_build.py` writes under that name, which each root copies.
_PAGE_PATH = os.path.join(_BUILD_PATH, f"{_PAGE_NAME}.html")

# The strings file, which the start script copies into the root.
_STRINGS_PATH = os.path.join(_CHECKOUT_PATH, "i18n", "en-US.json")

# The seed directory, which the start script copies into the root.
_SEED_PATH = os.path.join(_PYTHON_PATH, "seed")

# The directory of a root that holds the main loop files.
_MAIN_LOOP_DIRECTORY = "main_loop"

# The main loop file that serves `echo` on the echo root.
_ECHO_NAME = "echo_loop.py"

# That file in the checkout, beside this one.
_ECHO_PATH = os.path.join(_PYTHON_PATH, _ECHO_NAME)

# The option of `bootstrap.py` that names a main loop file of the root.
_LOOP_OPTION = "--main-loop"

# The arguments that run the echo main loop file on the echo root.
_ECHO_ARGS = (_LOOP_OPTION, _ECHO_NAME)

# The arguments of the stock main loop: none.
_STOCK_ARGS: tuple[str, ...] = ()

# The label of the important rungs that fit in 2 minutes.
_SMOKE_TEST = "smoke-test"

# The label of every other rung.
_NORMAL_TEST = "normal-test"

# The echo root's rungs and their labels, in the order they run.
_ECHO_RUNGS = (
    ("first", _SMOKE_TEST),
    ("echo", _SMOKE_TEST),
    ("control", _SMOKE_TEST),
    ("fit", _NORMAL_TEST),
    ("large", _NORMAL_TEST),
)

# The stock root's rungs and their labels, in the order they run.
_STOCK_RUNGS = (
    ("first", _SMOKE_TEST),
    ("mcp", _SMOKE_TEST),
    ("commits", _SMOKE_TEST),
    ("verbose", _SMOKE_TEST),
    ("console", _SMOKE_TEST),
    ("lines", _SMOKE_TEST),
    ("unknown", _SMOKE_TEST),
)

# The restart root's rungs and their labels, in the order they run.
_RESTART_RUNGS = (("first", _SMOKE_TEST), ("restart", _SMOKE_TEST))

# The run of the TypeScript side that runs the wire rungs.
_TYPESCRIPT_RUN = "wire"

# The name `argparse` shows, as `sys.argv` may be empty.
_PROGRAM_NAME = "test_wire.py"

# The option, patched into the release, that sets ttyd's receive chunk size.
_BUFFER_OPTION = "--srv-buf-size"

# The file under a root that the server appends the TypeScript stream to.
_TAP_PATH = os.path.join("tap", "typescript.tap")

# The server's log under a root, and the query of its texts in order.
_LOG_NAME = "_verbose.sqlite"
_LOG_QUERY = "SELECT text FROM line ORDER BY seq"

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

# The text of the page's fault screen, its message and stack, or null.
_FAULT_SCRIPT = (
    "(() => { const pre = document.querySelector("
    '"body > pre:not(#tap_output)"); return pre === null ? null :'
    " pre.textContent; })()"
)

# The type of the page's refusal of the restarted server's first line.
_REFUSAL_TYPE = "error"

# The type of a push of the page's log, which may be in flight at the exec.
_PUSH_TYPE = "verbose.put"

# The code a failed program exits with.
_PROGRAM_FAILED = 1

# The exit code of a run with a failed check.
_EXIT_FAILED = 1

# The exit code of a run that `^C` ended.
_EXIT_INTERRUPTED = 130

# A shell's exit code for a signal is this plus the signal's number.
_SIGNAL_BASE = 128

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# A check that failed, with the measurement that failed it.
class CheckFailed(Exception):
    pass


# A process's resident size and its peak, in KiB.
class MemoryUse(NamedTuple):
    resident: int
    peak: int


# The DevTools client of the page, whose waits a rung's timer bounds.
class DriverClient(Protocol):
    # Ends every later DevTools wait at `end` when that comes first.
    def deadline_set(self, end: float) -> None: ...


# The browser of `devtools.py` as this file uses it.
class BrowserDriver(Protocol):
    # Navigates to the URL and returns once it loads.
    def page_open(self, url: str) -> None: ...

    # Calls `fn` with the text of each console message from now on.
    def console_follow(self, fn: Callable[[str], None]) -> None: ...

    # Evaluates JavaScript on the page and returns its JSON value.
    def script_evaluate(self, text: str) -> object: ...

    # Returns the DevTools client of the page.
    def client_get(self) -> DriverClient: ...


# The stream reader of `tap_consumer.py` as this file uses it.
class StreamReading(Protocol):
    plan: int
    passed: int
    failed: int
    skipped: int

    # Takes the next line. Returns whether it fits where it stands.
    def line_read(self, line: Any) -> bool: ...

    # Whether the stream ended, by its parent plan or a bail out line.
    def stream_ended(self) -> bool: ...


# The parser of `tap_consumer.py` as this file uses it.
class LineParsing(Protocol):
    # Returns the kind of one line.
    def parse_line(self, text: str) -> Any: ...


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
    # Starts on the build, before any rung, checking the category's labels.
    def __init__(self, chosen: str) -> None:
        import category

        self.book = category.LabelBook(chosen)
        self.rung = "build"
        self.timer = RungTimer(self.rung, float(gold_value("rung_seconds")))
        self.started = time.monotonic()
        self.client: DriverClient | None = None

    # Has each rung's timer from now on bound the client's DevTools waits.
    def client_bind(self, client: DriverClient) -> None:
        self.client = client
        client.deadline_set(self.timer.end)

    # Names the step that runs now and starts its timer and its seconds.
    def rung_start(self, rung: str) -> None:
        self.rung = rung
        self.timer = RungTimer(rung, float(gold_value("rung_seconds")))
        self.started = time.monotonic()
        if self.client is not None:
            self.client.deadline_set(self.timer.end)

    # Starts a rung of the gold, which runs since the gold names it.
    def rung_enter(self, rung: str, label: str) -> None:
        if not self.book.rung_enter(rung, label):
            raise CheckFailed(
                f"the rung {rung} does not run in this run, but the gold"
                " names it"
            )
        self.rung_start(rung)

    # Prints the summary of the rung that ran, its label and its seconds.
    def rung_print(self, summary: str, label: str) -> None:
        seconds = time.monotonic() - self.started
        print(f"{self.rung}: {summary} ({label}, {seconds:.3f} s)", flush=True)

    # Prints the summary of a step that is no rung, and its seconds.
    def step_print(self, summary: str) -> None:
        seconds = time.monotonic() - self.started
        print(f"{self.rung}: {summary} ({seconds:.3f} s)", flush=True)


# ttyd serving one root, in a session of its own, its log read from a pipe.
class TtydServer:
    # Starts ttyd on a port of its choosing, as the start script starts it.
    def __init__(
        self,
        root: str,
        values: dict[str, Any],
        args: tuple[str, ...],
        log: RungLog,
    ) -> None:
        self.root = root
        self.log = log
        self.host: str = values["powershell"]["bind_address"]
        self.command = [
            "python3",
            os.path.join(root, "python", "bootstrap.py"),
            "--root",
            root,
            *args,
        ]
        path = ttyd_path()
        self.version = path
        self.lines: list[str] = []
        self.partial = b""
        self.port = 0
        self.killed = False
        self.log_ended = False
        page = os.path.join(root, values["powershell"]["engine_page"])
        self.fd, write_fd = os.pipe()
        try:
            self.process = subprocess.Popen(
                [
                    path,
                    "--port",
                    "0",
                    "--interface",
                    self.host,
                    "--writable",
                    "--check-origin",
                    "--terminal-type",
                    values["powershell"]["terminal_type"],
                    "--index",
                    page,
                    "--url-arg",
                    _BUFFER_OPTION,
                    str(values["srv_buf_size"]),
                    *self.command,
                ],
                stdin=subprocess.DEVNULL,
                stdout=sys.stderr,
                stderr=write_fd,
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
            seconds = float(gold_value("stop_seconds"))
            raise CheckFailed(
                f"{self.version} still ran {seconds:g} s after SIGTERM and"
                " was killed"
            )

    # The page's address on this ttyd.
    def url_get(self) -> str:
        return f"http://{self.host}:{self.port}/"

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
        data = os.read(self.fd, gold_value("read_bytes"))
        if not data:
            if not self.killed:
                raise CheckFailed(
                    f"{self.version} exited with {self.process.wait()}"
                )
            self.log_ended = True
            return
        self.lines_take(data)

    # Reads what ttyd logged within the seconds, so its pipe never fills.
    def log_poll(self, seconds: float) -> None:
        readable, _, _ = select.select([self.fd], [], [], seconds)
        if readable:
            self.log_read()

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
            self.log_poll(self.log.timer.seconds_left(what))

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
                self.process.wait(float(gold_value("stop_seconds")))
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
                stopped = False
        while data := os.read(self.fd, gold_value("read_bytes")):
            self.lines_take(data)
        os.close(self.fd)
        if self.partial:
            sys.stderr.write(f"{self.partial.decode()}\n")
            sys.stderr.flush()
        return stopped


# The TypeScript stream a root's server writes, read as it grows.
class TapStream:
    # Starts before the file exists, nothing read.
    def __init__(
        self,
        ttyd: TtydServer,
        parser: LineParsing,
        reader: StreamReading,
    ) -> None:
        self.ttyd = ttyd
        self.path = os.path.join(ttyd.root, _TAP_PATH)
        self.parser = parser
        self.reader = reader
        self.offset = 0
        self.partial = b""
        self.ready: list[str] = []
        self.points = 0

    # Takes the bytes the file gained since the last read, in whole lines.
    def file_read(self) -> None:
        if not os.path.exists(self.path):
            return
        with open(self.path, "rb") as file:
            file.seek(self.offset)
            data = file.read()
        self.offset += len(data)
        *complete, self.partial = (self.partial + data).split(b"\n")
        self.ready.extend(line.decode("utf-8") for line in complete)

    # Returns the next whole line, waiting for it under the rung's timer.
    def line_next(self, what: str) -> str:
        while not self.ready:
            left = self.ttyd.log.timer.seconds_left(what)
            self.ttyd.log_poll(min(float(gold_value("poll_seconds")), left))
            self.file_read()
        return self.ready.pop(0)

    # Reads one line into the reader, failing at a misfit or a failure.
    def line_take(self, what: str) -> str:
        line = self.line_next(what)
        if not self.reader.line_read(self.parser.parse_line(line)):
            raise CheckFailed(
                f"{what}: the line {line!r} of {self.path} does not fit the"
                " stream where it stands"
            )
        if self.reader.failed:
            shown = [line]
            while not self.reader.stream_ended():
                shown.append(self.line_next(f"the end of {what}"))
                self.reader.line_read(self.parser.parse_line(shown[-1]))
            raise CheckFailed(f"{what}: the stream failed: {shown}")
        return line

    # Returns the line of the rung's point, the next one of the stream.
    def point_next(self, rung: str) -> str:
        what = f"the point of the rung {rung}"
        while True:
            if self.reader.stream_ended():
                raise CheckFailed(f"the stream ended before {what}")
            line = self.line_take(what)
            reader = self.reader
            points = reader.passed + reader.failed + reader.skipped
            if points > self.points:
                self.points = points
                return line

    # Reads the stream to its parent plan, every point of the rungs passed.
    def end_read(self, rungs: int) -> None:
        while not self.reader.stream_ended():
            self.line_take("the end of the stream")
        reader = self.reader
        if (reader.plan, reader.passed) != (rungs, rungs):
            raise CheckFailed(
                f"the stream planned {reader.plan} and passed {reader.passed}"
                f" points, where {rungs} rungs ran"
            )


# A value of this driver's gold, `python.test_wire` of the test settings.
def gold_value(name: str) -> Any:
    import harness

    return harness.gold_get(f"{_GOLD_ID}.{name}")


# The ttyd `ttyd_build.py` builds from the pinned release and its patches.
def ttyd_path() -> str:
    import harness

    build: str = harness.setting_get("powershell.ttyd_build")
    return os.path.join(_CHECKOUT_PATH, build, "ttyd")


# The payload of the gold's one commit of the type.
def commit_payload(kind: str) -> dict[str, Any]:
    commits: list[dict[str, Any]] = gold_value("rungs.commits")
    (payload,) = [
        commit["payload"] for commit in commits if commit["type"] == kind
    ]
    return payload


# The `SHA-256` hex of a text's `UTF-8` bytes.
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Copies a console message of the page to stderr.
def console_copy(text: str) -> None:
    sys.stderr.write(f"console: {text}\n")


# Returns the parent's pid, the second field after the name in brackets.
def process_parent(pid: int) -> int:
    with open(f"/proc/{pid}/stat", "rb") as file:
        stat = file.read()
    return int(stat[stat.rindex(b")") + 2 :].split()[1])


# Returns which command the pid runs, failing unless it is ttyd's child.
def program_check(
    ttyd: TtydServer, pid: int, commands: list[list[str]]
) -> int:
    with open(f"/proc/{pid}/cmdline", "rb") as file:
        cmdline = file.read().split(b"\0")[:-1]
    dues = [[word.encode() for word in command] for command in commands]
    if cmdline not in dues:
        raise CheckFailed(
            f"the server's pid {pid} runs {cmdline}, not one of {dues}"
        )
    parent = process_parent(pid)
    if parent != ttyd.process.pid:
        raise CheckFailed(
            f"the server's pid {pid} is the child of {parent}, not of ttyd's"
            f" {ttyd.process.pid}"
        )
    return dues.index(cmdline)


# The pid of the one program ttyd runs and which command: ttyd's, or an exec's.
def server_find(ttyd: TtydServer, execed: list[list[str]]) -> tuple[int, int]:
    pid = ttyd.process.pid
    # The kernel's list of the children of ttyd's main thread.
    with open(f"/proc/{pid}/task/{pid}/children", encoding="ascii") as file:
        children = [int(word) for word in file.read().split()]
    if len(children) != 1:
        raise CheckFailed(
            f"{ttyd.version} runs the programs {children}, where one was due"
        )
    found = program_check(ttyd, children[0], [ttyd.command, *execed])
    return children[0], found


# Reads a process's resident size and its peak, in KiB, from its status file.
def memory_read(pid: int) -> MemoryUse:
    fields: dict[str, int] = {}
    with open(f"/proc/{pid}/status", encoding="utf-8") as file:
        for row in file:
            name, _, value = row.partition(":")
            if name in ("VmRSS", "VmHWM"):
                fields[name] = int(value.split()[0])
    return MemoryUse(fields["VmRSS"], fields["VmHWM"])


# Fails unless ttyd logged that the program of that pid exited with code 1.
def exit_check(ttyd: TtydServer, pid: int, what: str) -> None:
    how, number = ttyd.end_wait(pid, what)
    if (how, number) != (_EXITED_WORDS, _PROGRAM_FAILED):
        raise CheckFailed(
            f"{ttyd.version} logged that the process of pid {pid} {how}"
            f" {number}, where it exited with code {_PROGRAM_FAILED}"
        )


# Opens a database file of the root read only.
def database_open(root: str, name: str) -> sqlite3.Connection:
    uri = pathlib.Path(root, name).as_uri()
    return sqlite3.connect(f"{uri}?mode=ro", uri=True)


# Returns the texts of the server's log, in order.
def log_texts(root: str) -> list[str]:
    with contextlib.closing(database_open(root, _LOG_NAME)) as connection:
        rows: list[tuple[str]] = connection.execute(_LOG_QUERY).fetchall()
    return [row[0] for row in rows]


# Returns the log text that holds every one of the parts, failing if none.
def log_find(root: str, parts: list[str], what: str) -> str:
    for text in log_texts(root):
        if all(part in text for part in parts):
            return text
    raise CheckFailed(f"{what}: no line of the server's log holds {parts}")


# Returns the line the server's log names in the text, which holds no blob.
def line_named(root: str, unexpected: str, what: str) -> dict[str, Any]:
    refused = unexpected.replace("{0}", "")
    text = log_find(root, [refused], what)
    rendered = text[text.index(refused) + len(refused) :]
    line, end = json.JSONDecoder().raw_decode(rendered)
    if end != len(rendered):
        raise CheckFailed(f"{what}: the line {rendered!r} holds blobs")
    named: dict[str, Any] = line
    return named


# Returns the page's fault screen once written, waiting under the rung's timer.
def fault_wait(browser: BrowserDriver, ttyd: TtydServer, what: str) -> str:
    while True:
        text = cast(str | None, browser.script_evaluate(_FAULT_SCRIPT))
        if text is not None:
            return text
        left = ttyd.log.timer.seconds_left(what)
        ttyd.log_poll(min(float(gold_value("poll_seconds")), left))


# Fails unless a query of the database gives the rows due.
def rows_check(
    connection: sqlite3.Connection, sql: str, due: list[tuple[Any, ...]]
) -> None:
    rows: list[tuple[Any, ...]] = connection.execute(sql).fetchall()
    if rows != due:
        raise CheckFailed(f"{sql} gave {rows}, where {due} was due")


# Fails unless the server applied each push of the commits rung.
def commits_check(root: str) -> str:
    database = commit_payload("sql.run")["db"]
    dropped_database = commit_payload("db.drop")["db"]
    turn = commit_payload("turn.append")
    name = f"{database}.sqlite"
    with contextlib.closing(database_open(root, name)) as connection:
        rows_check(
            connection,
            "SELECT key, data FROM _kv WHERE key IN ('kept', 'gone')",
            [("kept", b"kept value")],
        )
        rows_check(
            connection,
            "SELECT key FROM _kv WHERE key = 'note/1'",
            [("note/1",)],
        )
        rows_check(connection, "SELECT id, version FROM _head", [("note", 1)])
        sql = "SELECT scene, n, role, content FROM _turn"
        rows: list[tuple[str, int, str, str]] = connection.execute(
            sql
        ).fetchall()
        turns = [(*row[:3], json.loads(row[3])) for row in rows]
        due = (turn["scene"], 1, turn["role"], turn["content"])
        if turns != [due]:
            raise CheckFailed(f"{sql} gave {rows} in {name}")
        rows_check(connection, "SELECT x FROM t", [(7,)])
    dropped = os.path.join(root, f"{dropped_database}.sqlite")
    if os.path.lexists(dropped):
        raise CheckFailed(f"{dropped} exists after db.drop")
    return (
        f"{name} holds kept and not gone, the note at version 1 and its"
        f" head, the turn of {turn['scene']} at n 1 and the row 7 of t;"
        f" {dropped_database} was dropped"
    )


# Kills ttyd and checks its end and that of the program it ran.
def kill_check(ttyd: TtydServer, pid: int) -> str:
    descriptor = os.pidfd_open(pid)
    try:
        killed_at = time.monotonic()
        ttyd.signal_send(signal.SIGKILL)
        while not ttyd.log_ended:
            ttyd.log_poll(ttyd.log.timer.seconds_left("the end of ttyd's log"))
        ended_seconds = time.monotonic() - killed_at
        status = ttyd.process.wait()
        if status != -signal.SIGKILL:
            raise CheckFailed(
                f"{ttyd.version} exited with {status} on SIGKILL"
            )
        readable: list[Any] = []
        while not readable:
            left = ttyd.log.timer.seconds_left(f"pid {pid} to end")
            readable, _, _ = select.select([descriptor], [], [], left)
        gone_seconds = time.monotonic() - killed_at
    finally:
        os.close(descriptor)
    return (
        f"SIGKILL to {ttyd.version} with the echo main loop running as pid"
        f" {pid}: ttyd's log ended {ended_seconds:.4f} s after the kill;"
        f" ttyd exited with {status}; pid {pid} was gone {gone_seconds:.3f} s"
        " after the kill"
    )


# The gold of a root's wire rungs.
def gold_make(name: str, rungs: list[str]) -> dict[str, Any]:
    fixed: dict[str, Any] = gold_value("rungs")
    restart_path = os.path.join(_PYTHON_PATH, fixed["restart_name"])
    with open(restart_path, encoding="utf-8") as file:
        restart_text = file.read()
    tool_text: str = fixed["mcp_call"]["arguments"]["text"]
    return {
        "root": name,
        "rungs": rungs,
        **fixed,
        "mcp_sha256": sha256_text(tool_text),
        "restart_text": restart_text,
        "restart_sha256": sha256_text(restart_text),
    }


# Writes a value as the JSON text of a file of the root, as the start script.
def json_write(root: str, name: str, value: object) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with open(os.path.join(root, name), "w", encoding="utf-8") as file:
        file.write(text)


# Makes a root as the start script does, with the gold of its rungs.
def root_make(
    work: str, name: str, rungs: list[str]
) -> tuple[str, dict[str, Any]]:
    import harness

    root = os.path.join(work, name)
    python_path = os.path.join(root, "python")
    os.makedirs(python_path)
    values = harness.settings_copy()
    values["debug"] = True
    values["verbose_level"] = gold_value("root_level")
    for module in values["powershell"]["runtime_modules"]:
        file_name = module + ".py"
        shutil.copyfile(
            os.path.join(_PYTHON_PATH, file_name),
            os.path.join(python_path, file_name),
        )
    shutil.copytree(_SEED_PATH, os.path.join(python_path, "seed"))
    strings_path = os.path.join(root, "i18n")
    os.makedirs(strings_path)
    shutil.copyfile(_STRINGS_PATH, os.path.join(strings_path, "en-US.json"))
    json_write(root, "settings.json", values)
    tests = harness.gold_copy()
    tests["typescript"]["run"] = _TYPESCRIPT_RUN
    tests["typescript"]["test_wire_rungs"] = gold_make(name, rungs)
    json_write(root, "test_settings.json", tests)
    page = os.path.join(root, values["powershell"]["engine_page"])
    shutil.copyfile(_PAGE_PATH, page)
    return root, values


# The rungs of the category, by their labels.
def rungs_chosen(
    rungs: tuple[tuple[str, str], ...], chosen: str
) -> list[tuple[str, str]]:
    import category

    return [rung for rung in rungs if category.suite_runs(rung[1], chosen)]


# Opens the page on the root's ttyd and reads its stream, a rung per point.
def stream_run(
    log: RungLog,
    browser: BrowserDriver,
    ttyd: TtydServer,
    root: str,
    rungs: list[tuple[str, str]],
    execed: list[list[str]],
) -> int:
    import tap_consumer

    log.rung_start(f"{root}: page")
    browser.page_open(ttyd.url_get())
    stream = TapStream(
        ttyd, tap_consumer.Parser(), tap_consumer.StreamReader()
    )
    (first, first_label), *rest = rungs
    log.rung_enter(f"{root}: {first}", first_label)
    line = stream.point_next(first)
    # The page runs on past its first point, so a later rung may have execed.
    pid, found = server_find(ttyd, execed)
    running = (
        "its command"
        if found == 0
        else f"its command execed in place as {execed[found - 1]}"
    )
    log.rung_print(
        f"{line.strip()}; the server is pid {pid}, ttyd's child running"
        f" {running}",
        first_label,
    )
    for rung, label in rest:
        log.rung_enter(f"{root}: {rung}", label)
        summary = stream.point_next(rung).strip()
        if rung == "large":
            use = memory_read(ttyd.process.pid)
            summary += (
                f"; ttyd's resident size {use.resident} KiB, its peak"
                f" {use.peak} KiB"
            )
        log.rung_print(summary, label)
    log.rung_start(f"{root}: stream end")
    stream.end_read(len(rungs))
    log.step_print(f"the stream ended passing, {len(rungs)} points")
    return pid


# The echo root: its stream, then ttyd killed.
def root_echo(
    log: RungLog, browser: BrowserDriver, work: str, chosen: str
) -> None:
    if not log.book.root_enter("echo", _SMOKE_TEST):
        return
    rungs = rungs_chosen(_ECHO_RUNGS, chosen)
    root, values = root_make(work, "echo", [rung for rung, _ in rungs])
    directory = os.path.join(root, _MAIN_LOOP_DIRECTORY)
    os.makedirs(directory)
    shutil.copyfile(_ECHO_PATH, os.path.join(directory, _ECHO_NAME))
    log.rung_start("echo: ttyd")
    with TtydServer(root, values, _ECHO_ARGS, log) as ttyd:
        pid = stream_run(log, browser, ttyd, "echo", rungs, [])
        log.rung_start("echo: ttyd killed")
        log.step_print(kill_check(ttyd, pid))
    log.book.root_leave()


# The stock root: its stream, then the server's end, log and databases.
def root_stock(
    log: RungLog, browser: BrowserDriver, work: str, chosen: str
) -> None:
    if not log.book.root_enter("stock", _SMOKE_TEST):
        return
    rungs = rungs_chosen(_STOCK_RUNGS, chosen)
    root, values = root_make(work, "stock", [rung for rung, _ in rungs])
    log.rung_start("stock: ttyd")
    with TtydServer(root, values, _STOCK_ARGS, log) as ttyd:
        pid = stream_run(log, browser, ttyd, "stock", rungs, [])
        log.rung_start("stock: server end")
        exit_check(ttyd, pid, "ttyd's log of the server's end")
        message: str = gold_value("texts.dispatch_handler_unknown")
        log_find(root, [message], "the server's log of the unknown push")
        applied = commits_check(root)
        log.step_print(
            f"pid {pid} logged {message!r} and exited with code"
            f" {_PROGRAM_FAILED} as ttyd logged; {applied}"
        )
    log.book.root_leave()


# The restart root: a stream that ended passing, then the exec's refusal.
def root_restart(
    log: RungLog, browser: BrowserDriver, work: str, chosen: str
) -> None:
    if not log.book.root_enter("restart", _SMOKE_TEST):
        return
    rungs = rungs_chosen(_RESTART_RUNGS, chosen)
    root, values = root_make(work, "restart", [rung for rung, _ in rungs])
    log.rung_start("restart: ttyd")
    with TtydServer(root, values, _STOCK_ARGS, log) as ttyd:
        # The command `system.restart` execs the server into, in place.
        main_loop: str = gold_value("rungs.restart_name")
        restarted = [*ttyd.command, _LOOP_OPTION, main_loop]
        pid = stream_run(log, browser, ttyd, "restart", rungs, [restarted])
        log.rung_start("restart: server end")
        exit_check(ttyd, pid, "ttyd's log of the restarted server's end")
        unexpected: str = gold_value("texts.bootstrap_reply_unexpected")
        twice: str = gold_value("texts.wire_start_twice")
        what = "the server's log of the reply to its second first line"
        line = line_named(root, unexpected, what)
        kind = line["0"]["type"]
        refusal = kind == _REFUSAL_TYPE and line["message"] == twice
        # A push sent before the exec may reach the restarted server first.
        if not refusal and kind != _PUSH_TYPE:
            raise CheckFailed(
                f"{what}: it names {line}, neither the page's refusal nor a"
                f" {_PUSH_TYPE} push"
            )
        fault = fault_wait(browser, ttyd, "the page's fault screen")
        if fault.split("\n", 1)[0] != twice:
            raise CheckFailed(
                f"the page's fault screen shows {fault!r}, not {twice!r}"
            )
        named = "the page's refusal" if refusal else f"a {_PUSH_TYPE} push"
        log.step_print(
            f"the server execed in place as pid {pid}, then logged"
            f" {unexpected.replace('{0}', '')!r} naming {named} and exited"
            f" with code {_PROGRAM_FAILED} as ttyd logged; the page's fault"
            f" screen shows {twice!r}"
        )
    log.book.root_leave()


# Builds the page, then runs each root of the category in one browser.
def roots_run(log: RungLog, work: str, chosen: str) -> None:
    import devtools, page_build

    digest = page_build.page_build(_PAGE_TEMPLATE, _PAGE_NAME)
    log.step_print(f"built {_PAGE_PATH}, sha256 {digest}")
    width, height = gold_value("window_width"), gold_value("window_height")
    with devtools.Browser(width, height, devtools.LinuxPipe()) as browser:
        browser.console_follow(console_copy)
        log.client_bind(browser.client_get())
        root_echo(log, browser, work, chosen)
        root_stock(log, browser, work, chosen)
        root_restart(log, browser, work, chosen)


# Exits with 128 plus the signal's number, so the blocks stop ttyd.
def signal_exit(number: int, frame: types.FrameType | None) -> None:
    sys.exit(_SIGNAL_BASE + number)


# Runs the roots of the chosen category in order and returns the exit code.
def main(arguments: list[str]) -> int:
    import category

    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description="Run the wire test: the page's wire rungs on roots under"
        " build/, through the ttyd python/ttyd_build.py builds, in"
        " chrome-headless-shell, their TAP stream read from each root.",
    )
    category.options_add(parser)
    chosen: str = parser.parse_args(arguments).category
    for number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(number, signal_exit)
    log = RungLog(chosen)
    try:
        path = ttyd_path()
        if not os.path.isfile(path):
            raise CheckFailed(f"{path} is missing: {_BUILD_SCRIPT} builds it")
        with tempfile.TemporaryDirectory(
            prefix=_WORK_PREFIX, dir=_BUILD_PATH
        ) as work:
            roots_run(log, work, chosen)
    except CheckFailed as failure:
        print(f"error: {log.rung}: {failure}", file=sys.stderr)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        return _EXIT_INTERRUPTED
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
