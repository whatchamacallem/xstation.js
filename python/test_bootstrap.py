# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the platform services without a pty: the arguments, the engine lock,
# the hello line, the provider file and the reply, the choice and loading of
# the main loop file, the console role, the error line and the server's log.
# Each run has descriptors 0 and 1 set to files and raw mode patched to record
# its calls, and the test main loop files write their calls to files in the
# root. A run that opens the log has it closed when it returns. The scratch
# directories go under build/.

import bootstrap, contextlib, fcntl, hashlib, json, os, signal, sqlite3, sys
import tempfile, unittest, unittest.mock, verbose
from typing import Any, NamedTuple
from i18n import i18n

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The checkout's settings, which each test root copies with `debug` set.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# The module under test, whose path and `sha256` the `hello` line carries.
_BOOTSTRAP_PATH = os.path.abspath(bootstrap.__file__)

# The stock main loop file, beside the module under test.
_STOCK_PATH = os.path.join(os.path.dirname(_BOOTSTRAP_PATH), "main_loop.py")

# The id of `hello`, the first request on the engine tty.
_HELLO_ID = 1

# The environment variable that holds the provider key.
_PROVIDER_VARIABLE = "XSJS_PROVIDER_KEY"

# The provider key in the environment of an engine run.
_PROVIDER_KEY = "the provider key of the test"

# The environment of an engine run, which holds the key and nothing else.
_ENGINE_ENVIRONMENT = {_PROVIDER_VARIABLE: _PROVIDER_KEY}

# The file in the root that a provider that is not scripted reads.
_PROVIDER_NAME = "provider.json"

# The provider file of a root whose provider is not scripted, filled out.
_PROVIDER_INFO = {
    "base_url": "the base url of the test",
    "chat_model": "the chat model of the test",
    "image_model": "the image model of the test",
}

# Values the provider file may not hold: empty text and values not text.
_INFO_EMPTY: tuple[object, ...] = ("", None, 0, [])

# The provider fields of `hello` with the key set and the provider file read.
_FIELDS_FILLED: dict[str, Any] = {
    "provider_key": _PROVIDER_KEY,
    "provider_info": _PROVIDER_INFO,
}

# The provider fields of `hello` with the key set and the provider scripted.
_FIELDS_SCRIPTED: dict[str, Any] = {"provider_key": _PROVIDER_KEY}

# The environment of a console run: the variables it keeps and two it drops.
_CONSOLE_ENVIRONMENT = {
    "HOME": "/home/test",
    "PATH": "/usr/bin:/bin",
    "TERM": "xterm-256color",
    _PROVIDER_VARIABLE: _PROVIDER_KEY,
    "OTHER": "dropped",
}

# What the console keeps of that environment, which does not set `LANG`.
_CONSOLE_KEPT = {
    "HOME": "/home/test",
    "PATH": "/usr/bin:/bin",
    "TERM": "xterm-256color",
}

# The keys of the `hello` line before its provider fields, in written order.
_HELLO_KEYS = [
    "0",
    "bootstrap",
    "sha256",
    "pid",
    "root",
    "settings",
    "seq",
]

# The `seq` map the test main loop returns.
_LOOP_SEQ = {"_settings": 15, "_files": 1, "_preferences": 0, "metaverse": 5}

# The file name the test main loops are written under in the root.
_LOOP_NAME = "test_loop.py"

# The file the test main loop's `loop_prepare` writes its argument to.
_PREPARE_NAME = "prepare.json"

# The file the test main loop's `loop_run` writes its arguments and input to.
_RUN_NAME = "run.json"

# A main loop that writes its calls to files in the root.
_LOOP_TEXT = (
    "import json, os\n"
    "\n"
    "\n"
    "def loop_prepare(root):\n"
    f"    with open(os.path.join(root, {_PREPARE_NAME!r}), 'w') as file:\n"
    "        json.dump([root], file)\n"
    f"    return {_LOOP_SEQ!r}\n"
    "\n"
    "\n"
    "def loop_run(read_fd, write_fd, root):\n"
    "    rest = os.read(read_fd, 64).decode('utf-8')\n"
    f"    with open(os.path.join(root, {_RUN_NAME!r}), 'w') as file:\n"
    "        json.dump([read_fd, write_fd, root, rest], file)\n"
)

# A main loop file that defines `loop_prepare` and not `loop_run`.
_LOOP_PARTIAL = "def loop_prepare(root):\n    return {}\n"

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
    "    return {}\n"
    "\n"
    "\n"
    "def loop_run(read_fd, write_fd, root):\n"
    "    path = os.path.join(root, 'engine.lock')\n"
    f"    probe = {_PROBE_TEXT!r}\n"
    "    os.execv(sys.executable, [sys.executable, '-c', probe, path])\n"
)

# The reply to `hello` in short names.
_REPLY_SHORT = b'{"0":{"t":"hello","r":1}}\r'

# The reply to `hello` in short names, its header fields in the other order.
_REPLY_REORDERED = b'{"0":{"r":1,"t":"hello"}}\r'

# The reply to `hello` in full names.
_REPLY_FULL = b'{"0":{"type":"hello","reply":1}}\r'

# Bytes after the reply, which the main loop must find unread.
_AFTER_REPLY = b"the bytes after the reply"

# Replies that are not the empty reply to `hello`, each with its rendering.
_REPLIES_WRONG = [
    (b'{"0":{"t":"hello","r":2}}\r', '{"0":{"t":"hello","r":2}}'),
    (b'{"0":{"t":"hello","r":true}}\r', '{"0":{"t":"hello","r":true}}'),
    (b'{"0":{"t":"hello","r":1,"b":0}}\r', '{"0":{"t":"hello","r":1,"b":0}}'),
    (b'{"0":{"t":"hello","i":1,"r":1}}\r', '{"0":{"t":"hello","i":1,"r":1}}'),
    (
        b'{"0":{"t":"hello","r":1},"extra":1}\r',
        '{"0":{"t":"hello","r":1},"extra":1}',
    ),
    (
        b'{"0":{"t":"error","r":1},"message":"m","stack":"s"}\r',
        '{"0":{"t":"error","r":1},"message":"m","stack":"s"}',
    ),
    (
        b'{"0":{"t":"hello","r":1,"b":1},"1":{"s":3}}\rabc',
        '{"0":{"t":"hello","r":1,"b":1},"1":{"s":3}}<blob "n"=1>',
    ),
]

# A reply that is not JSON.
_REPLY_GARBLED = b"not a line\r"

# The reason the JSON parser of Python gives for that reply.
_GARBLED_REASON = "Expecting value"

# The file in the root that holds the server's log.
_LOG_NAME = "_verbose.sqlite"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"


# A scratch directory and the root made in it, with the settings it holds.
class ScratchRoot(NamedTuple):
    scratch: str
    root: str
    settings: dict[str, Any]


# What a run returned and wrote, and each raw mode call with the output size.
class RunRecord(NamedTuple):
    code: int
    output: bytes
    raw_calls: list[tuple[int, int]]


# Writes the text as the provider file of the root.
def _info_write(root: str, text: str) -> None:
    path = os.path.join(root, _PROVIDER_NAME)
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


# Makes a scratch root: the settings, and unless scripted the provider file.
def _root_make(
    case: unittest.TestCase, debug: bool, scripted: bool = True
) -> ScratchRoot:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
    case.addCleanup(scratch.cleanup)
    root = os.path.join(scratch.name, "root")
    os.mkdir(root)
    with open(_SETTINGS_PATH, encoding="utf-8") as file:
        loaded: dict[str, Any] = json.load(file)
    loaded["debug"] = debug
    loaded["provider"]["scripted"] = scripted
    path = os.path.join(root, "settings.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(loaded, file)
    if not scripted:
        _info_write(root, json.dumps(_PROVIDER_INFO))
    return ScratchRoot(scratch.name, root, loaded)


# Rewrites the settings of a scratch root with the shell's verbose level set.
def _level_write(made: ScratchRoot, level: int) -> ScratchRoot:
    loaded = {**made.settings, "verbose_level": level}
    path = os.path.join(made.root, "settings.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(loaded, file)
    return ScratchRoot(made.scratch, made.root, loaded)


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


# Writes the input of a run to a file, returns its path and the output's.
def _files_make(made: ScratchRoot, given: bytes) -> tuple[str, str]:
    in_path = os.path.join(made.scratch, "in.bin")
    out_path = os.path.join(made.scratch, "out.bin")
    with open(in_path, "wb") as file:
        file.write(given)
    return in_path, out_path


# Runs `bootstrap_run` with descriptors 0 and 1 in files and the environment.
def _run_captured(
    made: ScratchRoot,
    argv: list[str],
    given: bytes,
    environment: dict[str, str],
) -> RunRecord:
    in_path, out_path = _files_make(made, given)
    raw_calls: list[tuple[int, int]] = []
    opened: list[str] = []
    log_open = verbose.log_open

    # Records the descriptor of a raw mode call and the output size before it.
    def raw_record(descriptor: int, when: int) -> None:
        raw_calls.append((descriptor, os.fstat(1).st_size))

    # Opens the log the run asks for and notes it, so the run's end closes it.
    def open_record(root: str, ring: int) -> None:
        log_open(root, ring)
        opened.append(root)

    scrubbed = unittest.mock.patch.dict(os.environ, environment, clear=True)
    raw = unittest.mock.patch("tty.setraw", side_effect=raw_record)
    logged = unittest.mock.patch("verbose.log_open", side_effect=open_record)
    modules = unittest.mock.patch.dict(sys.modules)
    sys.stdout.flush()
    saved_in = os.dup(0)
    saved_out = os.dup(1)
    try:
        with open(in_path, "rb") as source, open(out_path, "wb") as sink:
            os.dup2(source.fileno(), 0)
            os.dup2(sink.fileno(), 1)
            try:
                with scrubbed, raw, logged, modules:
                    code = bootstrap.bootstrap_run(argv)
            finally:
                os.dup2(saved_in, 0)
                os.dup2(saved_out, 1)
                if opened:
                    verbose.log_close()
    finally:
        os.close(saved_in)
        os.close(saved_out)
    with open(out_path, "rb") as file:
        output = file.read()
    return RunRecord(code, output, raw_calls)


# Runs `bootstrap_run` in a child, which its main loop may replace by `exec`.
def _child_run(
    made: ScratchRoot,
    argv: list[str],
    given: bytes,
    environment: dict[str, str],
) -> tuple[int, bytes]:
    in_path, out_path = _files_make(made, given)
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        try:
            source = os.open(in_path, os.O_RDONLY)
            sink = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            os.dup2(source, 0)
            os.dup2(sink, 1)
            os.environ.clear()
            os.environ.update(environment)
            with unittest.mock.patch("tty.setraw"):
                bootstrap.bootstrap_run(argv)
        finally:
            os.kill(os.getpid(), signal.SIGKILL)
    _, status = os.waitpid(pid, 0)
    with open(out_path, "rb") as file:
        output = file.read()
    return os.waitstatus_to_exitcode(status), output


# Splits the output into its lines, each ending in CR, and parses each one.
def _lines_parse(output: bytes) -> list[dict[str, Any]]:
    texts = output.split(b"\r")
    if texts.pop() != b"":
        raise ValueError(f"the output does not end in CR: {output!r}")
    return [json.loads(text) for text in texts]


# Reads the JSON file a function of the test main loop wrote in the root.
def _marker_read(root: str, name: str) -> Any:
    with open(os.path.join(root, name), encoding="utf-8") as file:
        return json.load(file)


# Checks a line is an `error` line with no `r`, and returns its message.
def _error_check(case: unittest.TestCase, line: dict[str, Any]) -> str:
    case.assertEqual(list(line), ["0", "message", "stack"])
    case.assertEqual(line["0"], {"t": "error"})
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


# Checks raw mode was set once, on descriptor 0, before any output.
def _raw_check(case: unittest.TestCase, record: RunRecord) -> None:
    case.assertEqual(record.raw_calls, [(0, 0)])


# Reads the thread and text of each line of the root's log, in order.
def _log_read(root: str) -> list[tuple[str, str]]:
    path = os.path.join(root, _LOG_NAME)
    if not os.path.exists(path):
        raise AssertionError(f"the root has no log: {path}")
    with contextlib.closing(sqlite3.connect(path)) as connection:
        rows: list[tuple[str, str]] = connection.execute(
            _LOG_QUERY
        ).fetchall()
    return rows


# The log line of the trace of a `hello` the run wrote, as it was parsed.
def _hello_trace(hello: dict[str, Any]) -> tuple[str, str]:
    header = json.dumps(hello["0"], separators=(",", ":"))
    return _SERVER_THREAD, i18n("bootstrap.hello_submit", header)


# The log line of a failure with the message.
def _failure_line(message: str) -> tuple[str, str]:
    return _SERVER_THREAD, i18n("bootstrap.run_failed", message)


# Checks the root's log holds one line, the failure's message.
def _failure_logged(
    case: unittest.TestCase, root: str, message: str
) -> None:
    case.assertEqual(_log_read(root), [_failure_line(message)])


# Checks a run that failed before it could open the root's log made none.
def _log_absent(case: unittest.TestCase, root: str) -> None:
    case.assertFalse(os.path.exists(os.path.join(root, _LOG_NAME)))


# Returns what a child process found when it tried the root's engine lock.
def _lock_tried(root: str) -> bytes:
    found_read, found_write = os.pipe()
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
    found = os.read(found_read, 64)
    os.close(found_read)
    os.waitpid(pid, 0)
    return found


# Holds the root's engine lock in a child until the returned descriptor closes.
def _lock_hold(root: str) -> tuple[int, int]:
    ready_read, ready_write = os.pipe()
    release_read, release_write = os.pipe()
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
    ready = os.read(ready_read, 64)
    os.close(ready_read)
    if ready != b"held":
        os.close(release_write)
        os.waitpid(pid, 0)
        raise RuntimeError("the child could not take the engine lock")
    return pid, release_write


# Tests the arguments, which are refused with an error line before raw mode.
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
            record = _run_captured(made, argv, b"", _ENGINE_ENVIRONMENT)
            self.assertEqual(record.code, 1)
            self.assertEqual(record.raw_calls, [])
            (line,) = _lines_parse(record.output)
            _raised_check(self, line, "argparse.ArgumentError")
        _log_absent(self, made.root)

    # A repeated `--root` or `--main-loop` is refused before raw mode.
    def test_option_repeated(self) -> None:
        made = _root_make(self, True)
        root = ["--root", made.root]
        loop = ["--main-loop", _LOOP_NAME]
        for argv, option in (
            (root + root, "--root"),
            (root + loop + loop, "--main-loop"),
        ):
            record = _run_captured(made, argv, b"", _ENGINE_ENVIRONMENT)
            self.assertEqual(record.code, 1)
            self.assertEqual(record.raw_calls, [])
            (line,) = _lines_parse(record.output)
            self.assertEqual(
                _error_check(self, line),
                i18n("bootstrap.option_repeated", option),
            )


# Tests the engine lock of the root.
class TestLock(unittest.TestCase):
    # After a run the lock is still held, so a child's attempt is refused.
    def test_lock_kept(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 0)
        self.assertEqual(_lock_tried(made.root), b"refused")

    # A lock another process holds is one error line after raw mode, exit 1.
    def test_lock_refused(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        pid, release = _lock_hold(made.root)
        try:
            record = _run_captured(
                made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT
            )
        finally:
            os.close(release)
            os.waitpid(pid, 0)
        self.assertEqual(record.code, 1)
        _raw_check(self, record)
        (line,) = _lines_parse(record.output)
        path = os.path.join(made.root, "engine.lock")
        self.assertEqual(
            _error_check(self, line), i18n("bootstrap.lock_held", path)
        )
        prepared = os.path.join(made.root, _PREPARE_NAME)
        self.assertFalse(os.path.exists(prepared))
        _log_absent(self, made.root)
        self.assertEqual(_lock_tried(made.root), b"taken")

    # The lock closes at `exec`, so the probe the main loop becomes takes it.
    def test_lock_released(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_EXEC)
        argv = _engine_argv(made.root)
        code, output = _child_run(made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT)
        self.assertEqual(code, 0)
        hello, taken = output.split(b"\r")
        header = json.loads(hello)["0"]
        self.assertEqual(header, {"type": "hello", "id": _HELLO_ID})
        self.assertEqual(taken, b"taken")


# Tests the `hello` line, its provider fields and the main loop calls.
class TestHello(unittest.TestCase):
    # Checks `hello`, its provider fields last, and the test main loop's calls.
    def hello_check(
        self,
        made: ScratchRoot,
        hello: dict[str, Any],
        provider: dict[str, Any],
    ) -> None:
        self.assertEqual(list(hello), _HELLO_KEYS + list(provider))
        self.assertEqual(hello["bootstrap"], _BOOTSTRAP_PATH)
        with open(_BOOTSTRAP_PATH, "rb") as file:
            digest = hashlib.sha256(file.read()).hexdigest()
        self.assertEqual(hello["sha256"], digest)
        self.assertEqual(hello["pid"], os.getpid())
        self.assertEqual(hello["root"], made.root)
        self.assertEqual(hello["settings"], made.settings)
        self.assertEqual(list(hello["settings"]), list(made.settings))
        self.assertEqual(hello["seq"], _LOOP_SEQ)
        self.assertEqual({name: hello[name] for name in provider}, provider)
        self.assertEqual(_marker_read(made.root, _PREPARE_NAME), [made.root])
        self.assertEqual(
            _marker_read(made.root, _RUN_NAME),
            [0, 1, made.root, _AFTER_REPLY.decode("utf-8")],
        )

    # Runs a provider that is not scripted and checks its key is refused.
    def provider_refused(self, environment: dict[str, str]) -> None:
        made = _root_make(self, True, scripted=False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, _REPLY_FULL, environment)
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        message = i18n("bootstrap.provider_unset", _PROVIDER_VARIABLE)
        self.assertEqual(_error_check(self, line), message)
        prepared = os.path.join(made.root, _PREPARE_NAME)
        self.assertFalse(os.path.exists(prepared))
        _failure_logged(self, made.root, message)

    # Runs a provider that is not scripted and checks its file is refused.
    def info_refused(
        self, made: ScratchRoot, kind: str, expected: str
    ) -> None:
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        self.assertEqual(_raised_check(self, line, kind), expected)
        prepared = os.path.join(made.root, _PREPARE_NAME)
        self.assertFalse(os.path.exists(prepared))
        _failure_logged(self, made.root, expected)

    # Outside debug mode `hello` has short names, with the test's stock file.
    def test_hello_short(self) -> None:
        made = _root_make(self, False, scripted=False)
        path = _loop_write(made.root, _LOOP_TEXT)
        given = _REPLY_SHORT + _AFTER_REPLY
        argv = ["--root", made.root]
        stock = unittest.mock.patch.object(bootstrap, "_MAIN_LOOP_STOCK", path)
        with stock:
            record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 0)
        _raw_check(self, record)
        (hello,) = _lines_parse(record.output)
        self.assertEqual(hello["0"], {"t": "hello", "i": _HELLO_ID})
        self.hello_check(made, hello, _FIELDS_FILLED)

    # In debug mode `hello` has full names.
    def test_hello_full(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        given = _REPLY_FULL + _AFTER_REPLY
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 0)
        _raw_check(self, record)
        (hello,) = _lines_parse(record.output)
        self.assertEqual(hello["0"], {"type": "hello", "id": _HELLO_ID})
        self.hello_check(made, hello, _FIELDS_SCRIPTED)

    # A scripted provider with no key variable sends the empty key.
    def test_provider_scripted(self) -> None:
        made = _root_make(self, True, scripted=True)
        _loop_write(made.root, _LOOP_TEXT)
        given = _REPLY_FULL + _AFTER_REPLY
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, given, {})
        self.assertEqual(record.code, 0)
        (hello,) = _lines_parse(record.output)
        self.hello_check(made, hello, {"provider_key": ""})

    # An empty key is refused when the provider is not scripted.
    def test_provider_empty(self) -> None:
        self.provider_refused({_PROVIDER_VARIABLE: ""})

    # No key variable is refused when the provider is not scripted.
    def test_provider_unset(self) -> None:
        self.provider_refused({})

    # A provider that is not scripted sends the file's values beside the key.
    def test_info_sent(self) -> None:
        made = _root_make(self, True, scripted=False)
        _loop_write(made.root, _LOOP_TEXT)
        given = _REPLY_FULL + _AFTER_REPLY
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 0)
        _raw_check(self, record)
        (hello,) = _lines_parse(record.output)
        self.assertEqual(hello["0"], {"type": "hello", "id": _HELLO_ID})
        self.hello_check(made, hello, _FIELDS_FILLED)

    # A scripted provider never reads the provider file, here not JSON.
    def test_info_unread(self) -> None:
        made = _root_make(self, True)
        _info_write(made.root, "not JSON")
        _loop_write(made.root, _LOOP_TEXT)
        given = _REPLY_FULL + _AFTER_REPLY
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 0)
        (hello,) = _lines_parse(record.output)
        self.hello_check(made, hello, _FIELDS_SCRIPTED)

    # A provider that is not scripted and has no provider file is refused.
    def test_info_missing(self) -> None:
        made = _root_make(self, True, scripted=False)
        path = os.path.join(made.root, _PROVIDER_NAME)
        os.remove(path)
        expected = i18n("bootstrap.provider_missing", path)
        self.info_refused(made, "FileNotFoundError", expected)

    # A file that is not an object with exactly the three keys is refused.
    def test_info_keys(self) -> None:
        missing = dict(_PROVIDER_INFO)
        del missing["image_model"]
        extra = {**_PROVIDER_INFO, "other": "the other value of the test"}
        keys = ", ".join(_PROVIDER_INFO)
        for text in (json.dumps(missing), json.dumps(extra), "[]", '"text"'):
            made = _root_make(self, True, scripted=False)
            _info_write(made.root, text)
            path = os.path.join(made.root, _PROVIDER_NAME)
            expected = i18n("bootstrap.provider_keys", path, keys)
            self.info_refused(made, "ValueError", expected)

    # A value that is empty or not text is refused, naming its key.
    def test_info_empty(self) -> None:
        for key in _PROVIDER_INFO:
            for value in _INFO_EMPTY:
                made = _root_make(self, True, scripted=False)
                info: dict[str, object] = {**_PROVIDER_INFO, key: value}
                _info_write(made.root, json.dumps(info))
                path = os.path.join(made.root, _PROVIDER_NAME)
                expected = i18n("bootstrap.provider_empty", path, key)
                self.info_refused(made, "ValueError", expected)


# Tests the reply to `hello`, which must be the empty reply in either form.
class TestReply(unittest.TestCase):
    # Runs with the input and checks `hello`, the error line and no loop run.
    def refusal_check(
        self, made: ScratchRoot, given: bytes, expected: str
    ) -> None:
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 1)
        hello, line = _lines_parse(record.output)
        self.assertEqual(hello["0"], {"type": "hello", "id": _HELLO_ID})
        self.assertEqual(_error_check(self, line), expected)
        self.assertFalse(os.path.exists(os.path.join(made.root, _RUN_NAME)))
        self.assertEqual(
            _log_read(made.root),
            [_hello_trace(hello), _failure_line(expected)],
        )

    # Each reply that is not the empty reply is refused, showing what came.
    def test_reply_wrong(self) -> None:
        for given, rendering in _REPLIES_WRONG:
            expected = i18n("bootstrap.reply_unexpected", rendering, _HELLO_ID)
            self.refusal_check(_root_make(self, True), given, expected)

    # A reply that is not JSON is refused by the decoder.
    def test_reply_garbled(self) -> None:
        expected = i18n("jslb.line_not_json", _GARBLED_REASON)
        self.refusal_check(_root_make(self, True), _REPLY_GARBLED, expected)

    # Short replies, in either field order, to a full `hello` are accepted.
    def test_reply_accepted(self) -> None:
        for reply in (_REPLY_SHORT, _REPLY_REORDERED):
            made = _root_make(self, True)
            _loop_write(made.root, _LOOP_TEXT)
            given = reply + _AFTER_REPLY
            argv = _engine_argv(made.root)
            record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT)
            self.assertEqual(record.code, 0)
            (hello,) = _lines_parse(record.output)
            self.assertEqual(hello["0"], {"type": "hello", "id": _HELLO_ID})
            self.assertEqual(
                _marker_read(made.root, _RUN_NAME),
                [0, 1, made.root, _AFTER_REPLY.decode("utf-8")],
            )

    # Input that ends before the reply is refused.
    def test_reply_closed(self) -> None:
        expected = i18n("bootstrap.reply_closed")
        self.refusal_check(_root_make(self, True), b"", expected)

    # A reply with a blob over `overflow_bytes` is refused before its bytes.
    def test_reply_streamed(self) -> None:
        made = _root_make(self, True)
        size: int = made.settings["overflow_bytes"] + 1
        reply = {"0": {"t": "hello", "r": 1, "b": 1}, "1": {"s": size}}
        given = json.dumps(reply, separators=(",", ":")).encode() + b"\r"
        self.refusal_check(made, given, i18n("bootstrap.reply_blob", size))


# Tests the choice and the loading of the main loop file.
class TestMainLoop(unittest.TestCase):
    # A name that is not a plain file name ending in `.py` is refused.
    def test_name_refused(self) -> None:
        for name in (
            "../test_loop.py",
            "main_loop/test_loop.py",
            ".test_loop.py",
            "test_loop.txt",
            "",
        ):
            made = _root_make(self, True)
            _loop_write(made.root, _LOOP_TEXT)
            argv = ["--root", made.root, "--main-loop", name]
            record = _run_captured(
                made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT
            )
            self.assertEqual(record.code, 1)
            (line,) = _lines_parse(record.output)
            self.assertEqual(
                _error_check(self, line),
                i18n("bootstrap.main_loop_name", name),
            )
            prepared = os.path.join(made.root, _PREPARE_NAME)
            self.assertFalse(os.path.exists(prepared))

    # A file that lacks `loop_run` is refused before `hello`.
    def test_function_missing(self) -> None:
        made = _root_make(self, True)
        path = _loop_write(made.root, _LOOP_PARTIAL)
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        self.assertEqual(
            _error_check(self, line),
            i18n("bootstrap.loop_missing", path, "loop_run"),
        )

    # A named file that does not exist is refused before `hello`.
    def test_file_missing(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, "main_loop", _LOOP_NAME)
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertIn(path, message)

    # Outside debug mode `--main-loop` is refused before the file is loaded.
    def test_debug_gate(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, _REPLY_SHORT, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        self.assertEqual(
            _error_check(self, line),
            i18n("bootstrap.main_loop_refused", _LOOP_NAME),
        )
        prepared = os.path.join(made.root, _PREPARE_NAME)
        self.assertFalse(os.path.exists(prepared))

    # With no `--main-loop` the stock file runs until it imports `substrate`.
    def test_stock_path(self) -> None:
        made = _root_make(self, False)
        argv = ["--root", made.root]
        halted = unittest.mock.patch.dict(sys.modules, {"substrate": None})
        with halted:
            record = _run_captured(made, argv, b"", _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        message = _raised_check(self, line, "ModuleNotFoundError")
        self.assertIn("substrate", message)
        self.assertIn(f'File "{_STOCK_PATH}"', line["stack"])
        names = sorted(os.listdir(made.root))
        self.assertEqual(names, [_LOG_NAME, "engine.lock", "settings.json"])
        _failure_logged(self, made.root, message)


# Tests the console role, which runs dash in debug mode only.
class TestConsole(unittest.TestCase):
    # Outside debug mode nothing runs, nothing is written and the code is 1.
    def test_console_refused(self) -> None:
        made = _root_make(self, False)
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        argv = ["--root", made.root, "console"]
        with unittest.mock.patch("verbose.exec") as executed:
            record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT)
        executed.assert_not_called()
        self.assertEqual(record, RunRecord(1, b"", []))
        self.assertEqual(os.getcwd(), before)
        _log_absent(self, made.root)

    # In debug mode dash runs in the root with only the kept variables.
    def test_console_scrubbed(self) -> None:
        made = _root_make(self, True)
        self.addCleanup(os.chdir, os.getcwd())
        seen: list[tuple[int, list[str], list[str], dict[str, str], str]] = []

        # Records the call and returns the code dash exits with.
        def exec_record(
            level: int, argv: list[str], argv_verbose: list[str]
        ) -> int:
            environment = dict(os.environ)
            seen.append((level, argv, argv_verbose, environment, os.getcwd()))
            return 3

        argv = ["--root", made.root, "console"]
        with unittest.mock.patch("verbose.exec", side_effect=exec_record):
            record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT)
        self.assertEqual(record, RunRecord(3, b"", []))
        ((level, called, called_verbose, environment, directory),) = seen
        expected: int = made.settings["verbose_level"]
        self.assertEqual(
            (level, called, called_verbose),
            (expected, ["/bin/dash"], ["/bin/dash", "-v"]),
        )
        self.assertEqual(environment, _CONSOLE_KEPT)
        self.assertTrue(os.path.samefile(directory, made.root))

    # Dash runs at the verbose level of the settings, and its verbose form.
    def test_console_level(self) -> None:
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        for level in range(3):
            made = _level_write(_root_make(self, True), level)
            argv = ["--root", made.root, "console"]
            with unittest.mock.patch("verbose.exec", return_value=0) as run:
                record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT)
            os.chdir(before)
            self.assertEqual(record, RunRecord(0, b"", []))
            run.assert_called_once_with(
                level, ["/bin/dash"], ["/bin/dash", "-v"]
            )
            self.assertEqual(_log_read(made.root), [])

    # A dash that cannot start is logged, then is one error line and exit 1.
    def test_console_failed(self) -> None:
        made = _root_make(self, True)
        self.addCleanup(os.chdir, os.getcwd())
        argv = ["--root", made.root, "console"]
        missing = FileNotFoundError(2, "No such file or directory", "dash")
        with unittest.mock.patch("verbose.exec", side_effect=missing):
            record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT)
        self.assertEqual(record.code, 1)
        self.assertEqual(record.raw_calls, [])
        (line,) = _lines_parse(record.output)
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertEqual(message, str(missing))
        _failure_logged(self, made.root, message)

    # A dash a signal ended gives the shell's code, 128 plus the signal.
    def test_console_signal(self) -> None:
        made = _root_make(self, True)
        self.addCleanup(os.chdir, os.getcwd())
        argv = ["--root", made.root, "console"]
        ended = -signal.SIGKILL
        with unittest.mock.patch("verbose.exec", return_value=ended):
            record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT)
        self.assertEqual(record, RunRecord(128 + signal.SIGKILL, b"", []))

    # The console role with `--main-loop` is refused before dash runs.
    def test_console_loop(self) -> None:
        made = _root_make(self, True)
        argv = ["--root", made.root, "console", "--main-loop", _LOOP_NAME]
        with unittest.mock.patch("verbose.exec") as executed:
            record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT)
        executed.assert_not_called()
        self.assertEqual(record.code, 1)
        self.assertEqual(record.raw_calls, [])
        (line,) = _lines_parse(record.output)
        self.assertEqual(
            _error_check(self, line),
            i18n("bootstrap.main_loop_refused", _LOOP_NAME),
        )


# Tests the error line, which `jslb` encodes.
class TestError(unittest.TestCase):
    # A missing settings file is one error line after raw mode, and exit 1.
    def test_error_shape(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, "settings.json")
        os.remove(path)
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT)
        self.assertEqual(record.code, 1)
        _raw_check(self, record)
        (line,) = _lines_parse(record.output)
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertIn(path, message)
        _log_absent(self, made.root)


# Tests the lines the engine role writes to the server's log.
class TestLog(unittest.TestCase):
    # In debug mode the log traces `hello`, whatever the shell's level.
    def test_hello_traced(self) -> None:
        for level in range(3):
            made = _level_write(_root_make(self, True), level)
            _loop_write(made.root, _LOOP_TEXT)
            given = _REPLY_FULL + _AFTER_REPLY
            argv = _engine_argv(made.root)
            record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT)
            self.assertEqual(record.code, 0)
            (hello,) = _lines_parse(record.output)
            self.assertEqual(_log_read(made.root), [_hello_trace(hello)])

    # Outside debug mode a run that does not fail logs nothing, at any level.
    def test_hello_quiet(self) -> None:
        for level in range(3):
            made = _level_write(_root_make(self, False), level)
            path = _loop_write(made.root, _LOOP_TEXT)
            given = _REPLY_SHORT + _AFTER_REPLY
            argv = ["--root", made.root]
            stock = unittest.mock.patch.object(
                bootstrap, "_MAIN_LOOP_STOCK", path
            )
            with stock:
                record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT)
            self.assertEqual(record.code, 0)
            self.assertEqual(_log_read(made.root), [])
