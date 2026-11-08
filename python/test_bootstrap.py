# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the platform services in process: each run of `bootstrap_run` is a
# forked child on a new pty, as ttyd runs it, and the test plays the page on
# the other side of the pty. The test main loop files, named by `--main-loop`
# in debug mode, write their calls to files in the root; with no `--main-loop`
# the stock main_loop.py answers a request. Each child writes how its run ended
# to a file, then kills itself, so that the lock, the log, the audit and the
# loaded main loop never reach another test. In debug mode a run's record is
# the root's audit, read back by `audit.entries_read`, and outside debug mode
# the root's log, `_verbose.sqlite`.

import audit, bootstrap, contextlib, errno, fcntl, harness, json, os, pty
import resource, runpy, select, signal, sqlite3, switches, sys, tempfile
import termios, time, traceback, unittest
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The file ttyd starts as a program, with the arguments after its name.
_BOOTSTRAP_PATH = os.path.join(_ROOT_PATH, "python", "bootstrap.py")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_bootstrap"

# The most bytes a read of the pty, a probe or a test main loop takes at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The bytes of a role refused, so that its error line outgrows the pty.
_HANGUP_BYTES: int = harness.gold_get(f"{_GOLD_ID}.hangup_bytes")

# The seconds a run may take to block in the write of its error line.
_BLOCKED_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.blocked_seconds")

# The seconds between two looks at whether the run is blocked.
_POLL_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.poll_seconds")

# The seconds a run waits for a held lock, private to `bootstrap.py`.
_LOCK_WAIT_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.lock_wait_seconds")

# The seconds a test keeps the lock from a waiting run, well within that wait.
_LOCK_HELD_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.lock_held_seconds")

# The state `/proc/PID/stat` gives a process that sleeps, as in a write.
_SLEEPING_STATE = "S"

# The variables of the three switches, by the name of each.
_SWITCH_VARIABLES = {
    "anthropic": "XSJS_ANTHROPIC",
    "debug": "XSJS_DEBUG",
    "verbose": "XSJS_VERBOSE",
}

# The environment variable that once held the provider key, a setting.
_PROVIDER_VARIABLE: str = harness.setting_get("provider.variable")

# A provider key in the environment, which no run reads.
_PROVIDER_KEY = "the provider key of the test"

# The environment of an engine run, which holds a key it never reads.
_ENGINE_ENVIRONMENT = {_PROVIDER_VARIABLE: _PROVIDER_KEY}

# The environment of a console run: the variables it keeps and two it drops.
_CONSOLE_ENVIRONMENT = {
    "HOME": "/home/test",
    "PATH": "/usr/bin:/bin",
    "TERM": "xterm-256color",
    _PROVIDER_VARIABLE: _PROVIDER_KEY,
    "OTHER": "dropped",
}

# A console root that is not under `/home/`, which the console refuses.
_OUTSIDE_ROOT = "/usr"

# The keys of `tap.start` in either mode, in written order.
_FIRST_KEYS = ["0", "settings", "switches"]

# The file in the root that holds the log.
_LOG_NAME = "_verbose.sqlite"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"

# The file in the root that holds the audit.
_AUDIT_NAME = "_audit.txt"

# The header fields that count a line's blobs, short and full.
_BLOB_FIELDS = ("b", "blobs")

# The file name the test main loops are written under in the root.
_LOOP_NAME = "test_loop.py"

# The file the test main loop's `loop_prepare` writes its argument to.
_PREPARE_NAME = "prepare.json"

# The file the test main loop's `loop_run` writes its arguments and input to.
_RUN_NAME = "run.json"

# The file in its scratch directory a child writes how its run ended to.
_ENDING_NAME = "ending.txt"

# Bytes after the reply, which the main loop must find unread.
_AFTER_REPLY = b"the bytes after the reply"

# A main loop filing calls in the root, `loop_run` once `_AFTER_REPLY` is read.
_LOOP_TEXT = (
    "import json, os\n"
    "\n"
    "\n"
    "def loop_prepare(root):\n"
    f"    with open(os.path.join(root, {_PREPARE_NAME!r}), 'w') as file:\n"
    "        json.dump([root], file)\n"
    "\n"
    "\n"
    "def loop_run(read_fd, write_fd, root):\n"
    "    rest = b''\n"
    f"    while len(rest) < {len(_AFTER_REPLY)}:\n"
    f"        rest += os.read(read_fd, {_READ_BYTES})\n"
    "    text = rest.decode('utf-8')\n"
    f"    with open(os.path.join(root, {_RUN_NAME!r}), 'w') as file:\n"
    "        json.dump([read_fd, write_fd, root, text], file)\n"
)

# A main loop filing the switches and their variables at its prepare.
_LOOP_SWITCHES = (
    "import json, os, switches\n"
    "\n"
    "\n"
    "def loop_prepare(root):\n"
    f"    names = {_SWITCH_VARIABLES!r}\n"
    "    variables = {name: os.environ.get(variable)"
    " for name, variable in names.items()}\n"
    f"    with open(os.path.join(root, {_PREPARE_NAME!r}), 'w') as file:\n"
    "        json.dump([switches.switches_get(), variables], file)\n"
    "\n"
    "\n"
    "def loop_run(read_fd, write_fd, root):\n"
    "    pass\n"
)

# A main loop file that defines `loop_prepare` and not `loop_run`.
_LOOP_PARTIAL = "def loop_prepare(root):\n    pass\n"

# A program that takes the lock of the file its argument names, then says so.
_PROBE_TEXT = (
    "import fcntl, os, sys\n"
    "descriptor = os.open(sys.argv[1], os.O_RDWR)\n"
    "fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
    "os.write(1, b'taken')\n"
)

# A main loop whose `loop_run` replaces its process by the probe.
_LOOP_EXEC = (
    "import os, sys\n"
    "\n"
    "\n"
    "def loop_prepare(root):\n"
    "    pass\n"
    "\n"
    "\n"
    "def loop_run(read_fd, write_fd, root):\n"
    "    path = os.path.join(root, 'engine.lock')\n"
    f"    probe = {_PROBE_TEXT!r}\n"
    "    os.execv(sys.executable, [sys.executable, '-c', probe, path])\n"
)

# A main loop whose `loop_prepare` ends the input, a pipe nothing writes to.
_LOOP_ENDED = (
    "import os\n"
    "\n"
    "\n"
    "def loop_prepare(root):\n"
    "    read_fd, write_fd = os.pipe()\n"
    "    os.close(write_fd)\n"
    "    os.dup2(read_fd, 0)\n"
    "\n"
    "\n"
    "def loop_run(read_fd, write_fd, root):\n"
    "    pass\n"
)

# The reply to `tap.start` in short names.
_REPLY_SHORT = b'{"0":{"t":"tap.start","r":101}}\r'

# The reply to `tap.start` in short names, its header fields reordered.
_REPLY_REORDERED = b'{"0":{"r":101,"t":"tap.start"}}\r'

# The reply to `tap.start` in full names.
_REPLY_FULL = b'{"0":{"type":"tap.start","reply":101}}\r'

# Replies that are not the empty reply to `tap.start`, with their cases.
_REPLIES_WRONG = [
    (b'{"0":{"t":"tap.start","r":1}}\r', "reply_one"),
    (b'{"0":{"t":"tap.start","r":true}}\r', "reply_true"),
    (b'{"0":{"t":"tap.start","r":101,"b":0}}\r', "blobs_zero"),
    (b'{"0":{"t":"tap.start","i":101,"r":101}}\r', "id_given"),
    (b'{"0":{"t":"tap.start","r":101},"extra":1}\r', "payload_extra"),
    (b'{"0":{"t":"hello","r":101}}\r', "hello"),
    (
        b'{"0":{"t":"error","r":101},"message":"m","stack":"s"}\r',
        "error_replied",
    ),
    (b'{"0":{"t":"error"},"message":"m","stack":"s"}\r', "error_pushed"),
    (
        b'{"0":{"t":"tap.start","r":101,"b":1},"1":{"s":3}}\rabc',
        "blob_carried",
    ),
]

# Main loop names that are not a plain file name ending in `.py`, by case.
_NAMES_REFUSED = [
    ("../test_loop.py", "parent"),
    ("main_loop/test_loop.py", "nested"),
    (".test_loop.py", "dotted"),
    ("test_loop.txt", "suffix"),
    ("", "empty"),
]

# A text that is not JSON, as a reply or as the test settings.
_GARBLED_TEXT = "not a line"

# The keys an error line may hold, its cascade's `cause` among them.
_ERROR_KEYS = {"0", "message", "stack", "cause"}

# How a child ends when `bootstrap_run` returns 0.
_ENDING_SERVED = repr(0)

# How a child ends when `bootstrap_run` returns 1.
_ENDING_FAILED = repr(1)

# The exit code of a child that killed itself once its run ended.
_KILLED = -signal.SIGKILL

# The exit code of a child the hangup ended.
_HUNG_UP = -signal.SIGHUP

# The start of the message of a process that the system refused to start.
_SPAWN_REFUSED = f"[Errno {errno.EAGAIN}] {os.strerror(errno.EAGAIN)}"


# A scratch directory and its root, its settings and its parameters.
class ScratchRoot(NamedTuple):
    scratch: str
    root: str
    settings: dict[str, Any]
    parameters: dict[str, bool]


# A text of this module's gold, each `{n}` replaced by the value at `n`.
def _text_get(name: str, *values: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    for number, value in enumerate(values):
        text = text.replace(f"{{{number}}}", value)
    return text


# A line of this module's gold, string keys as `json` reads the output.
def _line_get(name: str) -> dict[str, Any]:
    line: dict[str, Any] = harness.gold_get(f"{_GOLD_ID}.lines.{name}")
    return line


# The bytes of a gold line on the wire: its JSON text and a CR.
def _line_bytes(name: str) -> bytes:
    line = _line_get(name)
    text = json.dumps(line, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8") + b"\r"


# The log line of a failure with the message.
def _failure_line(message: str) -> tuple[str, str]:
    return (_SERVER_THREAD, _text_get("bootstrap_run_failed", message))


# The label and body of the audit's entry of a line, laid out by `json`.
def _record_entry(label: str, line: dict[str, Any]) -> tuple[str, str]:
    body = json.dumps(line, ensure_ascii=False, indent=2)
    blobs = 0
    for field in _BLOB_FIELDS:
        if field in line["0"]:
            blobs = line["0"][field]
    if blobs:
        body += "\n" + _text_get("audit_blobs_omitted", str(blobs))
    return (_text_get(label), body)


# The entry of a line the run wrote, as the pty gave it.
def _sent_entry(line: dict[str, Any]) -> tuple[str, str]:
    return _record_entry("audit_sent", line)


# The entry of a line the run read, its bytes as the test wrote them.
def _received_entry(given: bytes) -> tuple[str, str]:
    text, _, _ = given.partition(b"\r")
    return _record_entry("audit_received", json.loads(text))


# The entry of a note of console of the text, indented as the audit does.
def _console_entry(text: str) -> tuple[str, str]:
    return (_text_get("audit_console"), "  " + text)


# The label and body of each entry of the root's audit, after one start.
def _audit_read(case: unittest.TestCase, root: str) -> list[tuple[str, str]]:
    entries = audit.entries_read(root)
    case.assertEqual({entry.start for entry in entries}, {1})
    return [(entry.label, entry.body) for entry in entries]


# The thread and text of each line of the root's log, which must be open.
def _log_read(root: str) -> list[tuple[str, str]]:
    path = os.path.join(root, _LOG_NAME)
    if not os.path.isfile(path):
        raise AssertionError(f"the log was never opened: {path}")
    with contextlib.closing(sqlite3.connect(path)) as connection:
        cursor = connection.execute(_LOG_QUERY)
        rows: list[tuple[str, str]] = cursor.fetchall()
    return rows


# Checks the run never opened the root's log.
def _log_absent(case: unittest.TestCase, root: str) -> None:
    case.assertFalse(os.path.exists(os.path.join(root, _LOG_NAME)))


# Checks the run never opened the root's audit.
def _audit_absent(case: unittest.TestCase, root: str) -> None:
    case.assertFalse(os.path.exists(os.path.join(root, _AUDIT_NAME)))


# Checks the run opened neither the root's log nor its audit.
def _records_absent(case: unittest.TestCase, root: str) -> None:
    _log_absent(case, root)
    _audit_absent(case, root)


# Makes a scratch root: the checkout's settings, `debug` set.
def _root_make(case: unittest.TestCase, debug: bool) -> ScratchRoot:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
    case.addCleanup(scratch.cleanup)
    root = os.path.join(scratch.name, "root")
    os.mkdir(root)
    loaded = harness.settings_copy()
    path = os.path.join(root, "settings.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(loaded, file)
    parameters = {**switches.switches_get(), "debug": debug}
    switches.parameters_write(root, parameters)
    return ScratchRoot(scratch.name, root, loaded, parameters)


# Rewrites the parameters of a scratch root with the parameter `verbose` set.
def _verbose_write(made: ScratchRoot, verbose: bool) -> ScratchRoot:
    parameters = {**made.parameters, "verbose": verbose}
    switches.parameters_write(made.root, parameters)
    return made._replace(parameters=parameters)


# Writes a main loop file into the root's `main_loop` directory.
def _loop_write(root: str, text: str) -> str:
    directory = os.path.join(root, "main_loop")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, _LOOP_NAME)
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)
    return path


# The arguments of an engine run with the test main loop file.
def _engine_argv(root: str) -> list[str]:
    return ["--root", root, "--main-loop", _LOOP_NAME]


# Reads the JSON file a function of the test main loop wrote in the root.
def _marker_read(root: str, name: str) -> Any:
    with open(os.path.join(root, name), encoding="utf-8") as file:
        return json.load(file)


# Checks a line is an `error` line in full names, no `r`, returns its message.
def _error_check(case: unittest.TestCase, line: dict[str, Any]) -> str:
    case.assertEqual(list(line)[:3], ["0", "message", "stack"])
    case.assertLessEqual(set(line), _ERROR_KEYS)
    case.assertEqual(line["0"], _line_get("error")["0"])
    stack = line["stack"]
    case.assertIsInstance(stack, str)
    case.assertTrue(stack.startswith("Traceback (most recent call last):"))
    message = line["message"]
    case.assertIsInstance(message, str)
    return message


# Checks an error line reports an exception of the kind, returns its message.
def _raised_check(
    case: unittest.TestCase, line: dict[str, Any], kind: str
) -> str:
    message = _error_check(case, line)
    stack: str = line["stack"]
    case.assertTrue(stack.endswith(f"\n{kind}: {message}"))
    return message


# Returns what a child process found when it tried the root's engine lock.
def _lock_tried(root: str) -> bytes:
    found_read, found_write = os.pipe()
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(found_read)
            path = os.path.join(root, "engine.lock")
            descriptor = os.open(path, os.O_RDWR)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                os.write(found_write, b"taken")
            except BlockingIOError:
                os.write(found_write, b"refused")
        finally:
            os.kill(os.getpid(), signal.SIGKILL)
    os.close(found_write)
    found = os.read(found_read, _READ_BYTES)
    os.close(found_read)
    os.waitpid(pid, 0)
    return found


# Holds the root's engine lock in a child until `_lock_free` ends that child.
def _lock_hold(root: str) -> tuple[int, int]:
    ready_read, ready_write = os.pipe()
    release_read, release_write = os.pipe()
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(ready_read)
            os.close(release_write)
            path = os.path.join(root, "engine.lock")
            descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(ready_write, b"held")
            os.read(release_read, 1)
        finally:
            os.kill(os.getpid(), signal.SIGKILL)
    os.close(ready_write)
    os.close(release_read)
    ready = os.read(ready_read, _READ_BYTES)
    os.close(ready_read)
    if ready != b"held":
        os.close(release_write)
        os.waitpid(pid, 0)
        raise RuntimeError("the child could not take the engine lock")
    return pid, release_write


# Frees the lock by ending its holder, as a later fork keeps `release` open.
def _lock_free(pid: int, release: int) -> None:
    os.close(release)
    os.kill(pid, signal.SIGKILL)
    os.waitpid(pid, 0)


# Runs the file as ttyd starts it, and returns the code of its exit.
def _program_run(argv: list[str]) -> object:
    sys.argv = [_BOOTSTRAP_PATH, *argv]
    try:
        runpy.run_path(_BOOTSTRAP_PATH, run_name="__main__")
    except SystemExit as error:
        return error.code
    raise AssertionError(f"{_BOOTSTRAP_PATH} ended with no exit")


# In the forked child: `login_tty`, environment, run, ending to file, a kill.
def _child_main(
    slave: int,
    argv: list[str],
    environment: dict[str, str],
    path: str,
    spawn_refused: bool,
    program: bool,
) -> None:
    try:
        try:
            os.login_tty(slave)
            os.environ.clear()
            os.environ.update(environment)
            if spawn_refused:
                # The user may own no more processes, so none can start.
                resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
            run = _program_run if program else bootstrap.bootstrap_run
            ending = repr(run(argv))
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# `bootstrap_run` in a forked child on a new pty, and the page's end of it.
class EngineChild:
    # Forks the child that runs the arguments on the pty in the environment.
    def __init__(
        self,
        case: unittest.TestCase,
        made: ScratchRoot,
        argv: list[str],
        environment: dict[str, str],
        spawn_refused: bool = False,
        program: bool = False,
    ) -> None:
        self.ending_path = os.path.join(made.scratch, _ENDING_NAME)
        master, slave = pty.openpty()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(master)
            _child_main(
                slave,
                argv,
                environment,
                self.ending_path,
                spawn_refused,
                program,
            )
        os.close(slave)
        self.pid = pid
        self.master: int | None = master
        self.reaped = False
        self.buffer = b""
        case.addCleanup(self.cleanup)

    # This side of the pty, which must still be open.
    def master_get(self) -> int:
        if self.master is None:
            raise AssertionError(f"the pty of the child {self.pid} is closed")
        return self.master

    # Reads what the child wrote, empty once no process holds its side.
    def bytes_read(self) -> bytes:
        try:
            return os.read(self.master_get(), _READ_BYTES)
        except OSError as error:
            # Linux reads EIO from a pty whose other side no process holds.
            if error.errno != errno.EIO:
                raise
            return b""

    # The next line the child wrote, its text up to the CR as `json` reads it.
    def line_read(self) -> dict[str, Any]:
        while (end := self.buffer.find(b"\r")) < 0:
            data = self.bytes_read()
            if not data:
                raise AssertionError(f"the output ends in {self.buffer!r}")
            self.buffer += data
        line: dict[str, Any] = json.loads(self.buffer[:end])
        self.buffer = self.buffer[end + 1 :]
        return line

    # Writes all the bytes to the child.
    def bytes_write(self, data: bytes) -> None:
        view = memoryview(data)
        while view:
            written = os.write(self.master_get(), view)
            view = view[written:]

    # Whether the pty is raw: no line editing, no echo, no output processing.
    def raw_get(self) -> bool:
        attributes = termios.tcgetattr(self.master_get())
        oflag: int = attributes[1]
        lflag: int = attributes[3]
        edited = lflag & (termios.ICANON | termios.ECHO)
        return not edited and not oflag & termios.OPOST

    # Whether the child writes nothing for the seconds.
    def output_quiet(self, seconds: float) -> bool:
        return not select.select([self.master_get()], [], [], seconds)[0]

    # Reads the output to its end, then reaps the child: its code, the rest.
    def rest_read(self) -> tuple[int, bytes]:
        rest = self.buffer
        while data := self.bytes_read():
            rest += data
        self.buffer = b""
        _, status = os.waitpid(self.pid, 0)
        self.reaped = True
        return os.waitstatus_to_exitcode(status), rest

    # Reads the output to its end and returns how the run ended, and the rest.
    def run_end(self) -> tuple[str, bytes]:
        code, rest = self.rest_read()
        if code != _KILLED:
            raise AssertionError(f"the child {self.pid} exited with {code}")
        with open(self.ending_path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(self.ending_path)
        return ending, rest

    # Closes this side, the hangup, and returns the child's exit code.
    def hangup(self) -> int:
        os.close(self.master_get())
        self.master = None
        _, status = os.waitpid(self.pid, 0)
        self.reaped = True
        return os.waitstatus_to_exitcode(status)

    # Kills and reaps a child a failed test left, and closes this side.
    def cleanup(self) -> None:
        if not self.reaped:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
            self.reaped = True
        if self.master is not None:
            os.close(self.master)
            self.master = None


# Tests the arguments, which are refused with an error line after raw mode.
class TestArguments(unittest.TestCase):
    # No root, an unknown role, option or extra word is refused by `argparse`.
    def test_arguments_refused(self) -> None:
        made = _root_make(self, True)
        cases: list[list[str]] = [
            [],
            ["--root"],
            ["--root", made.root, "player2"],
            ["--root", made.root, "--other", "x"],
            ["--root", made.root, "console", "console"],
        ]
        for argv in cases:
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            line = child.line_read()
            self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
            self.assertTrue(child.raw_get())
            _raised_check(self, line, "argparse.ArgumentError")
            _records_absent(self, made.root)

    # A repeated `--root` or `--main-loop` is refused after raw mode.
    def test_option_repeated(self) -> None:
        made = _root_make(self, True)
        root = ["--root", made.root]
        loop = ["--main-loop", _LOOP_NAME]
        for argv, case in (
            (root + root, "root"),
            (root + loop + loop, "loop"),
        ):
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            line = child.line_read()
            self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
            self.assertTrue(child.raw_get())
            self.assertEqual(
                _error_check(self, line),
                _text_get(f"bootstrap_option_repeated_{case}"),
            )


# Tests the engine lock of the root.
class TestLock(unittest.TestCase):
    # While the main loop runs the lock is held, and the run's end frees it.
    def test_lock_kept(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        child.line_read()
        self.assertEqual(_lock_tried(made.root), b"refused")
        child.bytes_write(_REPLY_FULL + _AFTER_REPLY)
        self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
        self.assertEqual(_lock_tried(made.root), b"taken")

    # A lock held past the wait is one error line, its cause the last refusal.
    def test_lock_refused(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = ["--root", made.root]
        pid, release = _lock_hold(made.root)
        started = time.monotonic()
        try:
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            line = child.line_read()
            waited = time.monotonic() - started
            ending = child.run_end()
        finally:
            _lock_free(pid, release)
        self.assertGreaterEqual(waited, _LOCK_WAIT_SECONDS)
        self.assertEqual(ending, (_ENDING_FAILED, b""))
        self.assertTrue(child.raw_get())
        path = os.path.join(made.root, "engine.lock")
        self.assertEqual(
            _error_check(self, line), _text_get("bootstrap_lock_held", path)
        )
        cause = line["cause"]
        self.assertEqual(sorted(cause), ["message", "stack"])
        last = cause["stack"].rsplit("\n", 1)[-1]
        self.assertEqual(last, f"BlockingIOError: {cause['message']}")
        self.assertEqual(line["stack"].count("Traceback"), 1)
        prepared = os.path.join(made.root, _PREPARE_NAME)
        self.assertFalse(os.path.exists(prepared))
        _records_absent(self, made.root)
        self.assertEqual(_lock_tried(made.root), b"taken")

    # A lock freed within the wait is taken, and the first line then comes.
    def test_lock_waited(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        pid, release = _lock_hold(made.root)
        try:
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            quiet = child.output_quiet(_LOCK_HELD_SECONDS)
        finally:
            _lock_free(pid, release)
        self.assertTrue(quiet)
        first = child.line_read()
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        child.bytes_write(_REPLY_FULL + _AFTER_REPLY)
        self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
        self.assertEqual(_lock_tried(made.root), b"taken")

    # A hangup during the wait ends the run by SIGHUP, as elsewhere.
    def test_lock_hangup(self) -> None:
        made = _root_make(self, False)
        argv = ["--root", made.root]
        pid, release = _lock_hold(made.root)
        try:
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            quiet = child.output_quiet(_LOCK_HELD_SECONDS)
            code = child.hangup()
        finally:
            _lock_free(pid, release)
        self.assertTrue(quiet)
        self.assertEqual(code, _HUNG_UP)

    # The lock closes at `exec`, so the probe the main loop becomes takes it.
    def test_lock_released(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_EXEC)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        first = child.line_read()
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        child.bytes_write(_REPLY_FULL)
        self.assertEqual(child.rest_read(), (0, b"taken"))


# Tests the first line, its settings and switches, and the loop's calls.
class TestFirst(unittest.TestCase):
    # Checks `tap.start`'s payload, no gold or provider, and the loop's calls.
    def first_check(self, made: ScratchRoot, first: dict[str, Any]) -> None:
        self.assertEqual(list(first), _FIRST_KEYS)
        self.assertEqual(first["settings"], made.settings)
        self.assertEqual(list(first["settings"]), list(made.settings))
        self.assertEqual(first["switches"], made.parameters)
        self.assertEqual(_marker_read(made.root, _PREPARE_NAME), [made.root])
        self.assertEqual(
            _marker_read(made.root, _RUN_NAME),
            [0, 1, made.root, _AFTER_REPLY.decode("utf-8")],
        )

    # No debug: short `tap.start`, and the stock loop answers.
    def test_first_short(self) -> None:
        made = _root_make(self, False)
        argv = ["--root", made.root]
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        first = child.line_read()
        self.assertTrue(child.raw_get())
        self.assertEqual(first["0"], _line_get("first_short")["0"])
        self.assertEqual(list(first), _FIRST_KEYS)
        self.assertEqual(first["settings"], made.settings)
        self.assertEqual(list(first["settings"]), list(made.settings))
        self.assertEqual(first["switches"], made.parameters)
        child.bytes_write(_REPLY_SHORT + _line_bytes("ping_short"))
        self.assertEqual(child.line_read(), _line_get("ping_short_reply"))
        self.assertEqual(child.hangup(), _HUNG_UP)

    # In debug mode `tap.start` has full names and no gold.
    def test_first_full(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        first = child.line_read()
        self.assertTrue(child.raw_get())
        child.bytes_write(_REPLY_FULL + _AFTER_REPLY)
        self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        self.first_check(made, first)

    # No provider is read: not scripted, no key and a garbled provider file.
    def test_provider_unread(self) -> None:
        made = _root_make(self, True)
        made.settings["provider"]["scripted"] = False
        path = os.path.join(made.root, "settings.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(made.settings, file)
        with open(os.path.join(made.root, "provider.json"), "w") as file:
            file.write(_GARBLED_TEXT)
        _loop_write(made.root, _LOOP_TEXT)
        child = EngineChild(self, made, _engine_argv(made.root), {})
        first = child.line_read()
        child.bytes_write(_REPLY_FULL + _AFTER_REPLY)
        self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
        self.first_check(made, first)


# Tests the reply to `tap.start`, which must be the empty reply in either form.
class TestReply(unittest.TestCase):
    # Writes the reply, checks the error line, no loop run, and the audit.
    def refusal_check(
        self,
        made: ScratchRoot,
        given: bytes,
        expected: str,
        received: list[tuple[str, str]],
    ) -> None:
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        first = child.line_read()
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        child.bytes_write(given)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertEqual(_error_check(self, line), expected)
        self.assertFalse(os.path.exists(os.path.join(made.root, _RUN_NAME)))
        self.assertEqual(
            _audit_read(self, made.root),
            [_sent_entry(first), *received, _sent_entry(line)],
        )
        _log_absent(self, made.root)

    # Each reply that is not the empty reply is refused, recorded as it came.
    def test_reply_wrong(self) -> None:
        for given, case in _REPLIES_WRONG:
            expected = _text_get(f"bootstrap_reply_unexpected_{case}")
            received = [_received_entry(given)]
            made = _root_make(self, True)
            self.refusal_check(made, given, expected, received)

    # A reply that is not JSON is refused by the decoder, never recorded.
    def test_reply_garbled(self) -> None:
        expected = _text_get("jslb_line_not_json")
        given = _GARBLED_TEXT.encode("utf-8") + b"\r"
        self.refusal_check(_root_make(self, True), given, expected, [])

    # Short replies, in either field order, to a full `tap.start` are taken.
    def test_reply_accepted(self) -> None:
        for reply in (_REPLY_SHORT, _REPLY_REORDERED):
            made = _root_make(self, True)
            _loop_write(made.root, _LOOP_TEXT)
            argv = _engine_argv(made.root)
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            first = child.line_read()
            child.bytes_write(reply + _AFTER_REPLY)
            self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
            self.assertEqual(first["0"], _line_get("first_full")["0"])
            self.assertEqual(
                _marker_read(made.root, _RUN_NAME),
                [0, 1, made.root, _AFTER_REPLY.decode("utf-8")],
            )

    # A reply with a blob over `overflow_bytes` is refused before its bytes.
    def test_reply_streamed(self) -> None:
        made = _root_make(self, True)
        size: int = made.settings["overflow_bytes"] + 1
        header = {"t": "tap.start", "r": 101, "b": 1}
        reply = {"0": header, "1": {"s": size}}
        given = json.dumps(reply, separators=(",", ":")).encode() + b"\r"
        expected = _text_get("bootstrap_reply_blob", str(size))
        self.refusal_check(made, given, expected, [])

    # An input that ends before the reply is one error line, both recorded.
    def test_reply_closed(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_ENDED)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        first = child.line_read()
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        expected = _text_get("bootstrap_reply_closed")
        self.assertEqual(_raised_check(self, line, "EOFError"), expected)
        self.assertEqual(
            _audit_read(self, made.root),
            [_sent_entry(first), _sent_entry(line)],
        )
        _log_absent(self, made.root)


# Tests the choice and the loading of the main loop file.
class TestMainLoop(unittest.TestCase):
    # Runs the arguments, checks one error line ends it, returns its message.
    def refused_read(self, made: ScratchRoot, argv: list[str]) -> str:
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        return _error_check(self, line)

    # A name that is not a plain file name ending in `.py` is refused.
    def test_name_refused(self) -> None:
        for name, case in _NAMES_REFUSED:
            made = _root_make(self, True)
            _loop_write(made.root, _LOOP_TEXT)
            argv = ["--root", made.root, "--main-loop", name]
            self.assertEqual(
                self.refused_read(made, argv),
                _text_get(f"bootstrap_main_loop_name_{case}"),
            )
            prepared = os.path.join(made.root, _PREPARE_NAME)
            self.assertFalse(os.path.exists(prepared))

    # A file that lacks `loop_run` is refused before `tap.start`.
    def test_function_missing(self) -> None:
        made = _root_make(self, True)
        path = _loop_write(made.root, _LOOP_PARTIAL)
        self.assertEqual(
            self.refused_read(made, _engine_argv(made.root)),
            _text_get("bootstrap_loop_missing", path),
        )

    # A named file that does not exist is refused before `tap.start`.
    def test_file_missing(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, "main_loop", _LOOP_NAME)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertIn(path, message)

    # Outside debug mode `--main-loop` is refused before the file is loaded.
    def test_debug_gate(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        self.assertEqual(
            self.refused_read(made, _engine_argv(made.root)),
            _text_get("bootstrap_main_loop_refused"),
        )
        prepared = os.path.join(made.root, _PREPARE_NAME)
        self.assertFalse(os.path.exists(prepared))


# Tests the console role where it runs no shell.
class TestConsole(unittest.TestCase):
    # Outside debug mode nothing runs, nothing is written and the code is 1.
    def test_console_refused(self) -> None:
        made = _root_make(self, False)
        argv = ["--root", made.root, "console"]
        child = EngineChild(self, made, argv, _CONSOLE_ENVIRONMENT)
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertFalse(child.raw_get())
        _records_absent(self, made.root)

    # A sandbox denied a process is noted, one error line, exit 1, never raw.
    def test_console_failed(self) -> None:
        made = _verbose_write(_root_make(self, True), False)
        argv = ["--root", made.root, "console"]
        child = EngineChild(
            self, made, argv, _CONSOLE_ENVIRONMENT, spawn_refused=True
        )
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertFalse(child.raw_get())
        message = _raised_check(self, line, "BlockingIOError")
        self.assertTrue(message.startswith(_SPAWN_REFUSED), message)
        started = _console_entry(_text_get("verbose_exec_run"))
        failed = _console_entry(_text_get("bootstrap_run_failed", message))
        self.assertEqual(_audit_read(self, made.root), [started, failed])
        _log_absent(self, made.root)

    # A root outside `/home/`, which dash's sandbox hides, is refused first.
    def test_console_outside(self) -> None:
        made = _root_make(self, True)
        argv = ["--root", _OUTSIDE_ROOT, "console"]
        child = EngineChild(self, made, argv, _CONSOLE_ENVIRONMENT)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertFalse(child.raw_get())
        self.assertEqual(
            _error_check(self, line), _text_get("bootstrap_root_outside")
        )
        _records_absent(self, made.root)

    # The console role with `--main-loop` is refused, raw, before any shell.
    def test_console_loop(self) -> None:
        made = _root_make(self, True)
        argv = ["--root", made.root, "console", "--main-loop", _LOOP_NAME]
        child = EngineChild(self, made, argv, _CONSOLE_ENVIRONMENT)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertTrue(child.raw_get())
        self.assertEqual(
            _error_check(self, line), _text_get("bootstrap_main_loop_refused")
        )
        _records_absent(self, made.root)


# Tests the error line, which `jslb` encodes in full names.
class TestError(unittest.TestCase):
    # A missing settings file is one error line after raw mode, and exit 1.
    def test_error_shape(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, "settings.json")
        os.remove(path)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertTrue(child.raw_get())
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertIn(path, message)
        self.assertEqual(list(line), ["0", "message", "stack"])
        _records_absent(self, made.root)

    # Outside debug mode the error line is in full names, its message logged.
    def test_error_full(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertEqual(line["0"], _line_get("error")["0"])
        message = line["message"]
        self.assertEqual(_log_read(made.root), [_failure_line(message)])
        _audit_absent(self, made.root)


# Tests the root's parameters, which set the switches of the run.
class TestParameters(unittest.TestCase):
    # The parameters set the switches and their variables, not the parent's.
    def test_parameters_applied(self) -> None:
        made = _root_make(self, True)
        parameters = {
            "anthropic": not switches.anthropic,
            "debug": True,
            "verbose": not switches.verbose,
        }
        switches.parameters_write(made.root, parameters)
        made = made._replace(parameters=parameters)
        environment = {
            **_ENGINE_ENVIRONMENT,
            **{
                _SWITCH_VARIABLES[name]: "1"
                for name, on in parameters.items()
                if not on
            },
        }
        _loop_write(made.root, _LOOP_SWITCHES)
        child = EngineChild(self, made, _engine_argv(made.root), environment)
        first = child.line_read()
        child.bytes_write(_REPLY_FULL)
        self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
        self.assertEqual(first["switches"], parameters)
        variables = {
            name: "1" if on else None for name, on in parameters.items()
        }
        self.assertEqual(
            _marker_read(made.root, _PREPARE_NAME), [parameters, variables]
        )

    # A parameters file with a key that names no switch is refused, unlogged.
    def test_parameters_refused(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, "parameters.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump({**made.parameters, "verbose_level": 1}, file)
        child = EngineChild(self, made, _engine_argv(made.root), {})
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        expected = _text_get("switches_parameter_extra", path)
        self.assertEqual(_raised_check(self, line, "ValueError"), expected)
        _records_absent(self, made.root)

    # A root with no parameters file is refused, naming the file.
    def test_parameters_missing(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, "parameters.json")
        os.remove(path)
        child = EngineChild(self, made, ["--root", made.root, "console"], {})
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertIn(path, message)
        _records_absent(self, made.root)


# Returns the state `/proc/PID/stat` gives the process, after its name.
def _state_read(pid: int) -> str:
    with open(f"/proc/{pid}/stat", encoding="utf-8") as file:
        text = file.read()
    return text[text.rindex(")") + 2]


# Tests the hangup that comes while a run writes its error line.
class TestHangup(unittest.TestCase):
    # A hangup while the run is blocked in its error line's write ends nothing.
    def test_hangup_ignored(self) -> None:
        made = _root_make(self, True)
        role = "x" * _HANGUP_BYTES
        argv = ["--root", made.root, role]
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        child.buffer = child.bytes_read()
        deadline = time.monotonic() + _BLOCKED_SECONDS
        while _state_read(child.pid) != _SLEEPING_STATE:
            if time.monotonic() > deadline:
                raise AssertionError(
                    f"the run {child.pid} never blocked in its write"
                )
            time.sleep(_POLL_SECONDS)
        os.kill(child.pid, signal.SIGHUP)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        message = _raised_check(self, line, "argparse.ArgumentError")
        self.assertIn(repr(role), message)


# Tests the record the engine role keeps: the audit or the root's log.
class TestRecord(unittest.TestCase):
    # In debug mode the audit holds `tap.start` and its reply, and no log.
    def test_first_recorded(self) -> None:
        for verbose in (False, True):
            made = _verbose_write(_root_make(self, True), verbose)
            _loop_write(made.root, _LOOP_TEXT)
            argv = _engine_argv(made.root)
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            first = child.line_read()
            child.bytes_write(_REPLY_FULL + _AFTER_REPLY)
            self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
            self.assertEqual(
                _audit_read(self, made.root),
                [_sent_entry(first), _received_entry(_REPLY_FULL)],
            )
            _log_absent(self, made.root)

    # Outside debug mode a run that does not fail logs nothing, no audit.
    def test_first_quiet(self) -> None:
        for verbose in (False, True):
            made = _verbose_write(_root_make(self, False), verbose)
            argv = ["--root", made.root]
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            child.line_read()
            child.bytes_write(_REPLY_SHORT + _line_bytes("ping_short"))
            self.assertEqual(child.line_read(), _line_get("ping_short_reply"))
            self.assertEqual(child.hangup(), _HUNG_UP)
            self.assertEqual(_log_read(made.root), [])
            _audit_absent(self, made.root)


# Tests the file run as a program, which is how ttyd starts it.
class TestProgram(unittest.TestCase):
    # The words after the file's name reach the run, and exit 0 ends a serve.
    def test_program_served(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        child = EngineChild(
            self, made, argv, _ENGINE_ENVIRONMENT, program=True
        )
        first = child.line_read()
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        child.bytes_write(_REPLY_FULL + _AFTER_REPLY)
        self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
        self.assertEqual(
            _marker_read(made.root, _RUN_NAME),
            [0, 1, made.root, _AFTER_REPLY.decode("utf-8")],
        )

    # The code the run returns is the program's: a refused command line is 1.
    def test_program_failed(self) -> None:
        made = _root_make(self, True)
        child = EngineChild(self, made, [], _ENGINE_ENVIRONMENT, program=True)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        _raised_check(self, line, "argparse.ArgumentError")
