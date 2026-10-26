# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the platform services without a pty: the arguments, the engine lock,
# the first line, `tap.start` with the fixed id 101, its settings and, in
# debug mode only, its test settings, and no provider field, the reply, the
# choice and loading of the main loop file, the console role, the error
# line in full names with its cascade, and the calls bootstrap makes on the
# server's log. Each run has descriptors 0 and 1 set to files, raw mode
# patched to record its calls, and `verbose`, which bootstrap imports inside
# its functions, replaced through `sys.modules` by a double that records
# each call; the test main loop files write their calls to files in the
# root. The expected texts and headers are the gold's. The scratch
# directories go under build/.

import bootstrap, fcntl, harness, json, os, signal, sys, tempfile, unittest
import unittest.mock
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The module under test.
_BOOTSTRAP_PATH = os.path.abspath(bootstrap.__file__)

# The stock main loop file, beside the module under test.
_STOCK_PATH = os.path.join(os.path.dirname(_BOOTSTRAP_PATH), "main_loop.py")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_bootstrap"

# The most bytes a probe or a test main loop reads at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The fixed id of `tap.start`, the first request on the engine tty.
_FIRST_ID = 101

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

# What the console keeps of that environment, which does not set `LANG`.
_CONSOLE_KEPT = {
    "HOME": "/home/test",
    "PATH": "/usr/bin:/bin",
    "TERM": "xterm-256color",
}

# The keys of `tap.start` outside debug mode, in written order.
_FIRST_KEYS = ["0", "settings"]

# The keys of `tap.start` in debug mode, the test settings last.
_FIRST_KEYS_DEBUG = ["0", "settings", "test_settings"]

# The file in the root that holds the test settings.
_TESTS_NAME = "test_settings.json"

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
    "\n"
    "\n"
    "def loop_run(read_fd, write_fd, root):\n"
    f"    rest = os.read(read_fd, {_READ_BYTES}).decode('utf-8')\n"
    f"    with open(os.path.join(root, {_RUN_NAME!r}), 'w') as file:\n"
    "        json.dump([read_fd, write_fd, root, rest], file)\n"
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

# Bytes after the reply, which the main loop must find unread.
_AFTER_REPLY = b"the bytes after the reply"

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


# A scratch directory and its root, with the settings and the test settings.
class ScratchRoot(NamedTuple):
    scratch: str
    root: str
    settings: dict[str, Any]
    tests: dict[str, Any]


# What a run returned and wrote, and each raw mode call with the output size.
class RunRecord(NamedTuple):
    code: int
    output: bytes
    raw_calls: list[tuple[int, int]]


# A double of `verbose`: records each call, answers what the test queued.
class VerboseDouble:
    # Starts with the answers queued for each function, by its name.
    def __init__(self, **answers: list[Any]) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.places: list[tuple[dict[str, str], str]] = []
        self.answers = answers

    # Records a call, returns its next queued answer or raises a queued error.
    def call_answer(self, name: str, *args: Any) -> Any:
        self.calls.append((name, *args))
        if not self.answers.get(name):
            raise AssertionError(f"the verbose double has no answer: {name}")
        answer = self.answers[name].pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    # `verbose.log_open`, as bootstrap calls it.
    def log_open(self, root: str, ring: int) -> Any:
        return self.call_answer("log_open", root, ring)

    # `verbose.log`, as bootstrap calls it.
    def log(self, text: str) -> Any:
        return self.call_answer("log", text)

    # `verbose.exec`, keeping the environment and directory it was called in.
    def exec(
        self, level: int, argv: list[str], argv_verbose: list[str]
    ) -> Any:
        self.places.append((dict(os.environ), os.getcwd()))
        return self.call_answer("exec", level, argv, argv_verbose)


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


# A verbose double for a run that opens the log and logs `count` lines.
def _logged(count: int) -> VerboseDouble:
    return VerboseDouble(log_open=[None], log=[None] * count)


# The call that opens the root's log at the ring of its settings.
def _open_call(made: ScratchRoot) -> tuple[Any, ...]:
    return ("log_open", made.root, made.settings["verbose_ring"])


# The log call of the trace of `tap.start`, in debug mode.
def _trace_call() -> tuple[Any, ...]:
    return ("log", _text_get("bootstrap_start_submit"))


# The log call of a failure with the message.
def _failure_call(message: str) -> tuple[Any, ...]:
    return ("log", _text_get("bootstrap_run_failed", message))


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


# Writes the input of a run to a file, returns its path and the output's.
def _files_make(made: ScratchRoot, given: bytes) -> tuple[str, str]:
    in_path = os.path.join(made.scratch, "in.bin")
    out_path = os.path.join(made.scratch, "out.bin")
    with open(in_path, "wb") as file:
        file.write(given)
    return in_path, out_path


# Runs `bootstrap_run`, descriptors 0 and 1 in files, `logged` as `verbose`.
def _run_captured(
    made: ScratchRoot,
    argv: list[str],
    given: bytes,
    environment: dict[str, str],
    logged: VerboseDouble,
) -> RunRecord:
    in_path, out_path = _files_make(made, given)
    raw_calls: list[tuple[int, int]] = []

    # Records the descriptor of a raw mode call and the output size before it.
    def raw_record(descriptor: int, when: int) -> None:
        raw_calls.append((descriptor, os.fstat(1).st_size))

    scrubbed = unittest.mock.patch.dict(os.environ, environment, clear=True)
    raw = unittest.mock.patch("tty.setraw", side_effect=raw_record)
    modules = unittest.mock.patch.dict(sys.modules, {"verbose": logged})
    sys.stdout.flush()
    saved_in = os.dup(0)
    saved_out = os.dup(1)
    try:
        with open(in_path, "rb") as source, open(out_path, "wb") as sink:
            os.dup2(source.fileno(), 0)
            os.dup2(sink.fileno(), 1)
            try:
                with scrubbed, raw, modules:
                    code = bootstrap.bootstrap_run(argv)
            finally:
                os.dup2(saved_in, 0)
                os.dup2(saved_out, 1)
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


# Checks raw mode was set once, on descriptor 0, before any output.
def _raw_check(case: unittest.TestCase, record: RunRecord) -> None:
    case.assertEqual(record.raw_calls, [(0, 0)])


# Checks the run opened the root's log and logged one line, the failure.
def _failure_logged(
    case: unittest.TestCase,
    made: ScratchRoot,
    logged: VerboseDouble,
    message: str,
) -> None:
    expected = [_open_call(made), _failure_call(message)]
    case.assertEqual(logged.calls, expected)


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
    found = os.read(found_read, _READ_BYTES)
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
    ready = os.read(ready_read, _READ_BYTES)
    os.close(ready_read)
    if ready != b"held":
        os.close(release_write)
        os.waitpid(pid, 0)
        raise RuntimeError("the child could not take the engine lock")
    return pid, release_write


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
            logged = VerboseDouble()
            record = _run_captured(
                made, argv, b"", _ENGINE_ENVIRONMENT, logged
            )
            self.assertEqual(record.code, 1)
            _raw_check(self, record)
            (line,) = _lines_parse(record.output)
            _raised_check(self, line, "argparse.ArgumentError")
            self.assertEqual(logged.calls, [])

    # A repeated `--root` or `--main-loop` is refused after raw mode.
    def test_option_repeated(self) -> None:
        made = _root_make(self, True)
        root = ["--root", made.root]
        loop = ["--main-loop", _LOOP_NAME]
        for argv, case in (
            (root + root, "root"),
            (root + loop + loop, "loop"),
        ):
            record = _run_captured(
                made, argv, b"", _ENGINE_ENVIRONMENT, VerboseDouble()
            )
            self.assertEqual(record.code, 1)
            _raw_check(self, record)
            (line,) = _lines_parse(record.output)
            self.assertEqual(
                _error_check(self, line),
                _text_get(f"bootstrap_option_repeated_{case}"),
            )


# Tests the engine lock of the root.
class TestLock(unittest.TestCase):
    # After a run the lock is still held, so a child's attempt is refused.
    def test_lock_kept(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        record = _run_captured(
            made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT, _logged(1)
        )
        self.assertEqual(record.code, 0)
        self.assertEqual(_lock_tried(made.root), b"refused")

    # A held lock is one error line after raw mode, its cause the refusal.
    def test_lock_refused(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = ["--root", made.root]
        logged = VerboseDouble()
        pid, release = _lock_hold(made.root)
        try:
            record = _run_captured(
                made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT, logged
            )
        finally:
            os.close(release)
            os.waitpid(pid, 0)
        self.assertEqual(record.code, 1)
        _raw_check(self, record)
        (line,) = _lines_parse(record.output)
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
        self.assertEqual(logged.calls, [])
        self.assertEqual(_lock_tried(made.root), b"taken")

    # The lock closes at `exec`, so the probe the main loop becomes takes it.
    def test_lock_released(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_EXEC)
        argv = _engine_argv(made.root)
        code, output = _child_run(made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT)
        self.assertEqual(code, 0)
        first, taken = output.split(b"\r")
        header = json.loads(first)["0"]
        self.assertEqual(header, _line_get("first_full")["0"])
        self.assertEqual(taken, b"taken")


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
        logged = _logged(1)
        record = _run_captured(
            made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT, logged
        )
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        self.assertEqual(_raised_check(self, line, kind), expected)
        self.assertEqual(_marker_read(made.root, _PREPARE_NAME), [made.root])
        self.assertFalse(os.path.exists(os.path.join(made.root, _RUN_NAME)))
        _failure_logged(self, made, logged, expected)

    # Outside debug mode `tap.start` is short, its test settings left unread.
    def test_first_short(self) -> None:
        made = _root_make(self, False)
        os.remove(os.path.join(made.root, _TESTS_NAME))
        path = _loop_write(made.root, _LOOP_TEXT)
        given = _REPLY_SHORT + _AFTER_REPLY
        argv = ["--root", made.root]
        stock = unittest.mock.patch.object(bootstrap, "_MAIN_LOOP_STOCK", path)
        with stock:
            record = _run_captured(
                made, argv, given, _ENGINE_ENVIRONMENT, _logged(0)
            )
        self.assertEqual(record.code, 0)
        _raw_check(self, record)
        (first,) = _lines_parse(record.output)
        self.assertEqual(first["0"], _line_get("first_short")["0"])
        self.first_check(made, first, False)

    # In debug mode `tap.start` has full names and the test settings.
    def test_first_full(self) -> None:
        made = _root_make(self, True)
        _loop_write(made.root, _LOOP_TEXT)
        given = _REPLY_FULL + _AFTER_REPLY
        argv = _engine_argv(made.root)
        record = _run_captured(
            made, argv, given, _ENGINE_ENVIRONMENT, _logged(1)
        )
        self.assertEqual(record.code, 0)
        _raw_check(self, record)
        (first,) = _lines_parse(record.output)
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
        given = _REPLY_FULL + _AFTER_REPLY
        argv = _engine_argv(made.root)
        record = _run_captured(made, argv, given, {}, _logged(1))
        self.assertEqual(record.code, 0)
        (first,) = _lines_parse(record.output)
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
    # Runs with the input and checks `tap.start`, the error line, no loop run.
    def refusal_check(
        self, made: ScratchRoot, given: bytes, expected: str
    ) -> None:
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        logged = _logged(2)
        record = _run_captured(made, argv, given, _ENGINE_ENVIRONMENT, logged)
        self.assertEqual(record.code, 1)
        first, line = _lines_parse(record.output)
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        self.assertEqual(_error_check(self, line), expected)
        self.assertFalse(os.path.exists(os.path.join(made.root, _RUN_NAME)))
        self.assertEqual(
            logged.calls,
            [_open_call(made), _trace_call(), _failure_call(expected)],
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
            given = reply + _AFTER_REPLY
            argv = _engine_argv(made.root)
            record = _run_captured(
                made, argv, given, _ENGINE_ENVIRONMENT, _logged(1)
            )
            self.assertEqual(record.code, 0)
            (first,) = _lines_parse(record.output)
            self.assertEqual(first["0"], _line_get("first_full")["0"])
            self.assertEqual(
                _marker_read(made.root, _RUN_NAME),
                [0, 1, made.root, _AFTER_REPLY.decode("utf-8")],
            )

    # Input that ends before the reply is refused.
    def test_reply_closed(self) -> None:
        expected = _text_get("bootstrap_reply_closed")
        self.refusal_check(_root_make(self, True), b"", expected)

    # A reply with a blob over `overflow_bytes` is refused before its bytes.
    def test_reply_streamed(self) -> None:
        made = _root_make(self, True)
        size: int = made.settings["overflow_bytes"] + 1
        header = {"t": "tap.start", "r": _FIRST_ID, "b": 1}
        reply = {"0": header, "1": {"s": size}}
        given = json.dumps(reply, separators=(",", ":")).encode() + b"\r"
        expected = _text_get("bootstrap_reply_blob", str(size))
        self.refusal_check(made, given, expected)


# Tests the choice and the loading of the main loop file.
class TestMainLoop(unittest.TestCase):
    # A name that is not a plain file name ending in `.py` is refused.
    def test_name_refused(self) -> None:
        for name, case in _NAMES_REFUSED:
            made = _root_make(self, True)
            _loop_write(made.root, _LOOP_TEXT)
            argv = ["--root", made.root, "--main-loop", name]
            record = _run_captured(
                made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT, _logged(1)
            )
            self.assertEqual(record.code, 1)
            (line,) = _lines_parse(record.output)
            self.assertEqual(
                _error_check(self, line),
                _text_get(f"bootstrap_main_loop_name_{case}"),
            )
            prepared = os.path.join(made.root, _PREPARE_NAME)
            self.assertFalse(os.path.exists(prepared))

    # A file that lacks `loop_run` is refused before `tap.start`.
    def test_function_missing(self) -> None:
        made = _root_make(self, True)
        path = _loop_write(made.root, _LOOP_PARTIAL)
        argv = _engine_argv(made.root)
        record = _run_captured(
            made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT, _logged(1)
        )
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        self.assertEqual(
            _error_check(self, line),
            _text_get("bootstrap_loop_missing", path),
        )

    # A named file that does not exist is refused before `tap.start`.
    def test_file_missing(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, "main_loop", _LOOP_NAME)
        argv = _engine_argv(made.root)
        record = _run_captured(
            made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT, _logged(1)
        )
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertIn(path, message)

    # Outside debug mode `--main-loop` is refused before the file is loaded.
    def test_debug_gate(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        record = _run_captured(
            made, argv, _REPLY_SHORT, _ENGINE_ENVIRONMENT, _logged(1)
        )
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        self.assertEqual(
            _error_check(self, line), _text_get("bootstrap_main_loop_refused")
        )
        prepared = os.path.join(made.root, _PREPARE_NAME)
        self.assertFalse(os.path.exists(prepared))

    # With no `--main-loop` the stock file runs until it imports `substrate`.
    def test_stock_path(self) -> None:
        made = _root_make(self, False)
        argv = ["--root", made.root]
        logged = _logged(1)
        halted = unittest.mock.patch.dict(sys.modules, {"substrate": None})
        with halted:
            record = _run_captured(
                made, argv, b"", _ENGINE_ENVIRONMENT, logged
            )
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        message = _raised_check(self, line, "ModuleNotFoundError")
        self.assertIn("substrate", message)
        self.assertIn(f'File "{_STOCK_PATH}"', line["stack"])
        names = sorted(os.listdir(made.root))
        self.assertEqual(names, ["engine.lock", "settings.json", _TESTS_NAME])
        _failure_logged(self, made, logged, message)


# Tests the console role, which runs dash in debug mode only.
class TestConsole(unittest.TestCase):
    # Outside debug mode nothing runs, nothing is written and the code is 1.
    def test_console_refused(self) -> None:
        made = _root_make(self, False)
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        argv = ["--root", made.root, "console"]
        logged = VerboseDouble()
        record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT, logged)
        self.assertEqual(logged.calls, [])
        self.assertEqual(record, RunRecord(1, b"", []))
        self.assertEqual(os.getcwd(), before)

    # In debug mode dash runs in the root with only the kept variables.
    def test_console_scrubbed(self) -> None:
        made = _root_make(self, True)
        self.addCleanup(os.chdir, os.getcwd())
        argv = ["--root", made.root, "console"]
        logged = VerboseDouble(log_open=[None], exec=[3])
        record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT, logged)
        self.assertEqual(record, RunRecord(3, b"", []))
        level: int = made.settings["verbose_level"]
        called = ("exec", level, ["/bin/dash"], ["/bin/dash", "-v"])
        self.assertEqual(logged.calls, [_open_call(made), called])
        ((environment, directory),) = logged.places
        self.assertEqual(environment, _CONSOLE_KEPT)
        self.assertTrue(os.path.samefile(directory, made.root))

    # Dash runs at the verbose level of the settings, and its verbose form.
    def test_console_level(self) -> None:
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        for level in range(3):
            made = _level_write(_root_make(self, True), level)
            argv = ["--root", made.root, "console"]
            logged = VerboseDouble(log_open=[None], exec=[0])
            record = _run_captured(
                made, argv, b"", _CONSOLE_ENVIRONMENT, logged
            )
            os.chdir(before)
            self.assertEqual(record, RunRecord(0, b"", []))
            called = ("exec", level, ["/bin/dash"], ["/bin/dash", "-v"])
            self.assertEqual(logged.calls, [_open_call(made), called])

    # A dash that cannot start is logged, then is one error line and exit 1.
    def test_console_failed(self) -> None:
        made = _root_make(self, True)
        self.addCleanup(os.chdir, os.getcwd())
        argv = ["--root", made.root, "console"]
        missing = FileNotFoundError(2, "No such file or directory", "dash")
        logged = VerboseDouble(log_open=[None], exec=[missing], log=[None])
        record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT, logged)
        self.assertEqual(record.code, 1)
        self.assertEqual(record.raw_calls, [])
        (line,) = _lines_parse(record.output)
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertEqual(message, str(missing))
        level: int = made.settings["verbose_level"]
        called = ("exec", level, ["/bin/dash"], ["/bin/dash", "-v"])
        expected = [_open_call(made), called, _failure_call(message)]
        self.assertEqual(logged.calls, expected)

    # A dash a signal ended gives the shell's code, 128 plus the signal.
    def test_console_signal(self) -> None:
        made = _root_make(self, True)
        self.addCleanup(os.chdir, os.getcwd())
        argv = ["--root", made.root, "console"]
        logged = VerboseDouble(log_open=[None], exec=[-signal.SIGKILL])
        record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT, logged)
        self.assertEqual(record, RunRecord(128 + signal.SIGKILL, b"", []))

    # The console role with `--main-loop` is refused, raw, before dash runs.
    def test_console_loop(self) -> None:
        made = _root_make(self, True)
        argv = ["--root", made.root, "console", "--main-loop", _LOOP_NAME]
        logged = VerboseDouble()
        record = _run_captured(made, argv, b"", _CONSOLE_ENVIRONMENT, logged)
        self.assertEqual(logged.calls, [])
        self.assertEqual(record.code, 1)
        _raw_check(self, record)
        (line,) = _lines_parse(record.output)
        self.assertEqual(
            _error_check(self, line), _text_get("bootstrap_main_loop_refused")
        )


# Tests the error line, which `jslb` encodes in full names.
class TestError(unittest.TestCase):
    # A missing settings file is one error line after raw mode, and exit 1.
    def test_error_shape(self) -> None:
        made = _root_make(self, True)
        path = os.path.join(made.root, "settings.json")
        os.remove(path)
        argv = _engine_argv(made.root)
        logged = VerboseDouble()
        record = _run_captured(
            made, argv, _REPLY_FULL, _ENGINE_ENVIRONMENT, logged
        )
        self.assertEqual(record.code, 1)
        _raw_check(self, record)
        (line,) = _lines_parse(record.output)
        message = _raised_check(self, line, "FileNotFoundError")
        self.assertIn(path, message)
        self.assertEqual(list(line), ["0", "message", "stack"])
        self.assertEqual(logged.calls, [])

    # Outside debug mode the error line is still in full names.
    def test_error_full(self) -> None:
        made = _root_make(self, False)
        _loop_write(made.root, _LOOP_TEXT)
        argv = _engine_argv(made.root)
        record = _run_captured(
            made, argv, _REPLY_SHORT, _ENGINE_ENVIRONMENT, _logged(1)
        )
        self.assertEqual(record.code, 1)
        (line,) = _lines_parse(record.output)
        self.assertEqual(line["0"], _line_get("error")["0"])


# Tests the calls the engine role makes on the server's log.
class TestLog(unittest.TestCase):
    # In debug mode the log traces `tap.start`, whatever the shell's level.
    def test_first_traced(self) -> None:
        for level in range(3):
            made = _level_write(_root_make(self, True), level)
            _loop_write(made.root, _LOOP_TEXT)
            given = _REPLY_FULL + _AFTER_REPLY
            argv = _engine_argv(made.root)
            logged = _logged(1)
            record = _run_captured(
                made, argv, given, _ENGINE_ENVIRONMENT, logged
            )
            self.assertEqual(record.code, 0)
            self.assertEqual(logged.calls, [_open_call(made), _trace_call()])

    # Outside debug mode a run that does not fail logs nothing, at any level.
    def test_first_quiet(self) -> None:
        for level in range(3):
            made = _level_write(_root_make(self, False), level)
            path = _loop_write(made.root, _LOOP_TEXT)
            given = _REPLY_SHORT + _AFTER_REPLY
            argv = ["--root", made.root]
            logged = _logged(0)
            stock = unittest.mock.patch.object(
                bootstrap, "_MAIN_LOOP_STOCK", path
            )
            with stock:
                record = _run_captured(
                    made, argv, given, _ENGINE_ENVIRONMENT, logged
                )
            self.assertEqual(record.code, 0)
            self.assertEqual(logged.calls, [_open_call(made)])
