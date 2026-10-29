# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the platform services in process: each run of `bootstrap_run` is a
# forked child whose controlling tty, stdin, stdout and stderr are a new pty
# of `pty.openpty`, as ttyd runs it, with its environment set in the child,
# and the test plays the page on the other side of the pty. It tests the
# arguments, the engine lock, the raw mode of the pty, the first line,
# `tap.start` with the fixed id 101, its settings and, in debug mode only,
# its test settings, and no provider field, the reply, the choice and
# loading of the main loop file, the console role where it runs no shell,
# the error line in full names with its cascade, and the lines bootstrap
# writes to the root's log. The test main loop files, named by `--main-loop`
# in debug mode, write their calls to files in the root; with no
# `--main-loop` the stock main_loop.py answers a request. Each child writes
# how its run ended to a file, then kills itself, so that the lock, the log
# and the loaded main loop never reach another test. The expected texts and
# lines are the gold's. The scratch directories go under build/.

import bootstrap, contextlib, errno, fcntl, harness, json, os, pty, resource
import signal, sqlite3, sys, tempfile, termios, traceback, unittest
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_bootstrap"

# The most bytes a read of the pty, a probe or a test main loop takes at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

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

# The keys of `tap.start` outside debug mode, in written order.
_FIRST_KEYS = ["0", "settings"]

# The keys of `tap.start` in debug mode, the test settings last.
_FIRST_KEYS_DEBUG = ["0", "settings", "test_settings"]

# The file in the root that holds the test settings.
_TESTS_NAME = "test_settings.json"

# The file in the root that holds the log.
_LOG_NAME = "_verbose.sqlite"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"

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

# A main loop that writes its calls to files in the root, its `loop_run`
# once it has read the bytes after the reply.
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


# A scratch directory and its root, with the settings and the test settings.
class ScratchRoot(NamedTuple):
    scratch: str
    root: str
    settings: dict[str, Any]
    tests: dict[str, Any]


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


# The log line of the trace of `tap.start`, in debug mode.
def _trace_line() -> tuple[str, str]:
    return (_SERVER_THREAD, _text_get("bootstrap_start_submit"))


# The log line of a failure with the message.
def _failure_line(message: str) -> tuple[str, str]:
    return (_SERVER_THREAD, _text_get("bootstrap_run_failed", message))


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


# Writes the text as the test settings file of the root.
def _tests_write(root: str, text: str) -> None:
    with open(os.path.join(root, _TESTS_NAME), "w", encoding="utf-8") as file:
        file.write(text)


# Makes a scratch root: the checkout's settings and test settings, `debug` set.
def _root_make(case: unittest.TestCase, debug: bool) -> ScratchRoot:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
    case.addCleanup(scratch.cleanup)
    root = os.path.join(scratch.name, "root")
    os.mkdir(root)
    loaded = harness.settings_copy()
    loaded["debug"] = debug
    path = os.path.join(root, "settings.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(loaded, file)
    tests = harness.gold_copy()
    _tests_write(root, json.dumps(tests))
    return ScratchRoot(scratch.name, root, loaded, tests)


# Rewrites the settings of a scratch root with the shell's verbose level set.
def _level_write(made: ScratchRoot, level: int) -> ScratchRoot:
    loaded = {**made.settings, "verbose_level": level}
    path = os.path.join(made.root, "settings.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(loaded, file)
    return ScratchRoot(made.scratch, made.root, loaded, made.tests)


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


# Holds the root's engine lock in a child until the returned descriptor closes.
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


# In the forked child: the pty as its tty and its 0, 1 and 2, the
# environment, the run, how it ended written to the file, then a kill.
def _child_main(
    slave: int,
    argv: list[str],
    environment: dict[str, str],
    path: str,
    spawn_refused: bool,
) -> None:
    try:
        try:
            os.login_tty(slave)
            os.environ.clear()
            os.environ.update(environment)
            if spawn_refused:
                # The user may own no more processes, so none can start.
                resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
            ending = repr(bootstrap.bootstrap_run(argv))
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
    ) -> None:
        self.ending_path = os.path.join(made.scratch, _ENDING_NAME)
        master, slave = pty.openpty()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(master)
            _child_main(
                slave, argv, environment, self.ending_path, spawn_refused
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
            _log_absent(self, made.root)

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

    # A held lock is one error line after raw mode, its cause the refusal.
    def test_lock_refused(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = ["--root", made.root]
        pid, release = _lock_hold(made.root)
        try:
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            line = child.line_read()
            ending = child.run_end()
        finally:
            os.close(release)
            os.waitpid(pid, 0)
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
        _log_absent(self, made.root)
        self.assertEqual(_lock_tried(made.root), b"taken")

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


# Tests the first line, its settings and test settings, and the loop calls.
class TestFirst(unittest.TestCase):
    # Checks `tap.start`'s payload, no provider field, and the loop's calls.
    def first_check(
        self, made: ScratchRoot, first: dict[str, Any], debug: bool
    ) -> None:
        keys = _FIRST_KEYS_DEBUG if debug else _FIRST_KEYS
        self.assertEqual(list(first), keys)
        self.assertEqual(first["settings"], made.settings)
        self.assertEqual(list(first["settings"]), list(made.settings))
        if debug:
            self.assertEqual(first["test_settings"], made.tests)
        self.assertEqual(_marker_read(made.root, _PREPARE_NAME), [made.root])
        self.assertEqual(
            _marker_read(made.root, _RUN_NAME),
            [0, 1, made.root, _AFTER_REPLY.decode("utf-8")],
        )

    # Runs a debug root whose test settings are refused, after the prepare.
    def refused_check(
        self, made: ScratchRoot, kind: str, expected: str
    ) -> None:
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertEqual(_raised_check(self, line, kind), expected)
        self.assertEqual(_marker_read(made.root, _PREPARE_NAME), [made.root])
        self.assertFalse(os.path.exists(os.path.join(made.root, _RUN_NAME)))
        self.assertEqual(_log_read(made.root), [_failure_line(expected)])

    # Outside debug mode `tap.start` is short, its test settings left unread,
    # and the stock main loop answers the request after the reply.
    def test_first_short(self) -> None:
        made = _root_make(self, False)
        os.remove(os.path.join(made.root, _TESTS_NAME))
        argv = ["--root", made.root]
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        first = child.line_read()
        self.assertTrue(child.raw_get())
        self.assertEqual(first["0"], _line_get("first_short")["0"])
        self.assertEqual(list(first), _FIRST_KEYS)
        self.assertEqual(first["settings"], made.settings)
        self.assertEqual(list(first["settings"]), list(made.settings))
        child.bytes_write(_REPLY_SHORT + _line_bytes("tail_short"))
        self.assertEqual(child.line_read(), _line_get("tail_short_reply"))
        self.assertEqual(child.hangup(), _HUNG_UP)

    # In debug mode `tap.start` has full names and the test settings.
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
        self.first_check(made, first, True)

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
        self.first_check(made, first, True)

    # In debug mode a missing test settings file raises as `open` does.
    def test_tests_missing(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, _TESTS_NAME)
        os.remove(path)
        expected = str(FileNotFoundError(2, "No such file or directory", path))
        self.refused_check(made, "FileNotFoundError", expected)

    # A test settings file that is not an object is refused, naming it.
    def test_tests_object(self) -> None:
        for text in ("[]", '"text"', "null", "1"):
            made = _root_make(self, True)
            _tests_write(made.root, text)
            path = os.path.join(made.root, _TESTS_NAME)
            expected = _text_get("bootstrap_tests_not_object", path)
            self.refused_check(made, "ValueError", expected)

    # A test settings file that is not JSON is refused by the decoders.
    def test_tests_garbled(self) -> None:
        made = _root_make(self, True)
        _tests_write(made.root, _GARBLED_TEXT)
        expected = _text_get("jslb_text_not_json")
        self.refused_check(made, "jslb.WireError", expected)


# Tests the reply to `tap.start`, which must be the empty reply in either form.
class TestReply(unittest.TestCase):
    # Writes the reply, checks `tap.start`, the error line, no loop run.
    def refusal_check(
        self, made: ScratchRoot, given: bytes, expected: str
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
            _log_read(made.root), [_trace_line(), _failure_line(expected)]
        )

    # Each reply that is not the empty reply is refused, showing what came.
    def test_reply_wrong(self) -> None:
        for given, case in _REPLIES_WRONG:
            expected = _text_get(f"bootstrap_reply_unexpected_{case}")
            self.refusal_check(_root_make(self, True), given, expected)

    # A reply that is not JSON is refused by the decoder.
    def test_reply_garbled(self) -> None:
        expected = _text_get("jslb_line_not_json")
        given = _GARBLED_TEXT.encode("utf-8") + b"\r"
        self.refusal_check(_root_make(self, True), given, expected)

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
        self.refusal_check(made, given, expected)


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
        _log_absent(self, made.root)

    # A dash that cannot start, as the user may own no more processes, is
    # logged, then is one error line and exit 1, the pty never raw.
    def test_console_failed(self) -> None:
        made = _level_write(_root_make(self, True), 0)
        argv = ["--root", made.root, "console"]
        child = EngineChild(
            self, made, argv, _CONSOLE_ENVIRONMENT, spawn_refused=True
        )
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertFalse(child.raw_get())
        message = _raised_check(self, line, "BlockingIOError")
        self.assertTrue(message.startswith(_SPAWN_REFUSED), message)
        self.assertEqual(_log_read(made.root), [_failure_line(message)])

    # The console role with `--main-loop` is refused, raw, before dash runs.
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
        _log_absent(self, made.root)


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
        _log_absent(self, made.root)

    # Outside debug mode the error line is still in full names.
    def test_error_full(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
        line = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertEqual(line["0"], _line_get("error")["0"])


# Tests the lines the engine role writes to the root's log.
class TestLog(unittest.TestCase):
    # In debug mode the log traces `tap.start`, whatever the shell's level.
    def test_first_traced(self) -> None:
        for level in range(3):
            made = _level_write(_root_make(self, True), level)
            _loop_write(made.root, _LOOP_TEXT)
            argv = _engine_argv(made.root)
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            child.line_read()
            child.bytes_write(_REPLY_FULL + _AFTER_REPLY)
            self.assertEqual(child.run_end(), (_ENDING_SERVED, b""))
            self.assertEqual(_log_read(made.root), [_trace_line()])

    # Outside debug mode a run that does not fail logs nothing, at any level.
    def test_first_quiet(self) -> None:
        for level in range(3):
            made = _level_write(_root_make(self, False), level)
            argv = ["--root", made.root]
            child = EngineChild(self, made, argv, _ENGINE_ENVIRONMENT)
            child.line_read()
            child.bytes_write(_REPLY_SHORT + _line_bytes("tail_short"))
            self.assertEqual(child.line_read(), _line_get("tail_short_reply"))
            self.assertEqual(child.hangup(), _HUNG_UP)
            self.assertEqual(_log_read(made.root), [])
