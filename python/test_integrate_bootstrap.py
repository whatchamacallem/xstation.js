# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the platform services with the stock main_loop.py serving every
# engine, in process: each run of `bootstrap_run` is a forked child whose
# controlling tty, stdin, stdout and stderr are a new pty of `pty.openpty`,
# as ttyd runs it, on a debug root in build/ whose settings are the
# checkout's and whose parameters are the run's with debug true, and the
# test plays the page on the other side of the pty. Bootstrap's records of
# `tap.start` and its reply and the main loop's records of a line share the
# one audit that `audit.tail` reads; a failure of the main loop writes its
# one error line, recorded once, with nothing from bootstrap after it; and
# the page's error line, recorded as it is read, ends the TypeScript stream
# and the run, unanswered. No run opens the log. Each child writes how its
# run ended to a file, then kills itself. The lines and texts are the gold's.

import audit, bootstrap, errno, functools, harness, json, os, pty, signal
import subprocess, switches, sys, tempfile, traceback, unittest
from typing import Any, NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_integrate_bootstrap"

# The most bytes a read of the pty takes at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The reply to `tap.start` in full names.
_REPLY_FULL = b'{"0":{"type":"tap.start","reply":101}}\r'

# The file in the root that holds the log, which no debug run opens.
_LOG_NAME = "_verbose.sqlite"

# The file in the root that holds the audit.
_AUDIT_NAME = "_audit.txt"

# The TAP file of the TypeScript stream in a root.
_TAP_FILE = os.path.join("tap", "typescript.tap")

# The file in its scratch directory a child writes how its run ended to.
_ENDING_NAME = "ending.txt"

# How a child ends when the main loop exits 1.
_ENDING_FAILED = "exit 1"

# The exit code of a child that killed itself once its run ended.
_KILLED = -signal.SIGKILL

# The exit code of a child the hangup ended.
_HUNG_UP = -signal.SIGHUP

# The test driver, which this suite runs as a program.
_DRIVER_PATH = os.path.join(_ROOT_PATH, "python", "test_all.py")

# A suite whose forked children the hangup must end.
_HANGUP_SUITE = "test_bootstrap"


# A scratch directory and its root.
class ScratchRoot(NamedTuple):
    scratch: str
    root: str


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
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


# The audit's entry of a line the run wrote, as the pty gave it.
def _sent_entry(line: dict[str, Any]) -> tuple[str, str]:
    body = json.dumps(line, ensure_ascii=False, indent=2)
    return (_text_get("audit_sent"), body)


# The audit's entry of a line the run read, its bytes as the test wrote them.
def _received_entry(given: bytes) -> tuple[str, str]:
    text, _, _ = given.partition(b"\r")
    body = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    return (_text_get("audit_received"), body)


# The label and body of each entry of the root's audit, with no log beside.
def _audit_read(case: unittest.TestCase, root: str) -> list[tuple[str, str]]:
    case.assertFalse(os.path.exists(os.path.join(root, _LOG_NAME)))
    entries = audit.entries_read(root)
    case.assertEqual({entry.start for entry in entries}, {1})
    return [(entry.label, entry.body) for entry in entries]


# Makes a debug scratch root: the checkout's settings, the run's parameters.
def _root_make(case: unittest.TestCase) -> ScratchRoot:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
    case.addCleanup(scratch.cleanup)
    root = os.path.join(scratch.name, "root")
    os.mkdir(root)
    loaded = harness.settings_copy()
    with open(os.path.join(root, "settings.json"), "w") as file:
        json.dump(loaded, file)
    switches.parameters_write(root, {**switches.switches_get(), "debug": True})
    return ScratchRoot(scratch.name, root)


# In the forked child: `login_tty`, a stock loop run, ending to file, a kill.
def _child_main(slave: int, root: str, path: str) -> None:
    try:
        try:
            os.login_tty(slave)
            ending = repr(bootstrap.bootstrap_run(["--root", root]))
        except SystemExit as error:
            ending = f"exit {error.code}"
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# `bootstrap_run` in a forked child on a new pty, and the page's end of it.
class EngineChild:
    # Forks the child that serves the root on the pty.
    def __init__(self, case: unittest.TestCase, made: ScratchRoot) -> None:
        self.ending_path = os.path.join(made.scratch, _ENDING_NAME)
        master, slave = pty.openpty()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(master)
            _child_main(slave, made.root, self.ending_path)
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

    # Reads the output to its end and returns how the run ended, and the rest.
    def run_end(self) -> tuple[str, bytes]:
        rest = self.buffer
        while data := self.bytes_read():
            rest += data
        self.buffer = b""
        _, status = os.waitpid(self.pid, 0)
        self.reaped = True
        code = os.waitstatus_to_exitcode(status)
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


# Tests bootstrap with the stock main loop and its engines.
class TestStock(unittest.TestCase):
    # Starts the engine on a new debug root and answers `tap.start`, returned.
    def engine_start(self) -> tuple[ScratchRoot, EngineChild, dict[str, Any]]:
        made = _root_make(self)
        child = EngineChild(self, made)
        first = child.line_read()
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        child.bytes_write(_REPLY_FULL)
        return made, child, first

    # `audit.tail` reads bootstrap's records, then the main loop's, unrecorded.
    def test_tail_shared(self) -> None:
        made, child, first = self.engine_start()
        child.bytes_write(_line_bytes("ping"))
        pinged = child.line_read()
        self.assertEqual(pinged, _line_get("ping_reply"))
        child.bytes_write(_line_bytes("tail"))
        reply = child.line_read()
        self.assertEqual(reply["0"], _line_get("tail_reply")["0"])
        path = os.path.join(made.root, _AUDIT_NAME)
        with open(path, encoding="utf-8") as file:
            _, _, entries = file.read().partition("\n\n")
        self.assertEqual(reply["text"], entries)
        expected = [
            _sent_entry(first),
            _received_entry(_REPLY_FULL),
            _received_entry(_line_bytes("ping")),
            _sent_entry(pinged),
        ]
        self.assertEqual(_audit_read(self, made.root), expected)
        self.assertEqual(child.hangup(), _HUNG_UP)

    # A loop failure records one error line, and bootstrap adds nothing.
    def test_failure_once(self) -> None:
        made, child, first = self.engine_start()
        child.bytes_write(_line_bytes("unknown_request"))
        error = child.line_read()
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        self.assertEqual(error["0"], _line_get("error_reply")["0"])
        message = _text_get("dispatch_handler_unknown")
        self.assertEqual(error["message"], message)
        expected = [
            _sent_entry(first),
            _received_entry(_REPLY_FULL),
            _received_entry(_line_bytes("unknown_request")),
            _sent_entry(error),
        ]
        self.assertEqual(_audit_read(self, made.root), expected)

    # A page error, recorded as read, ends the TAP file and run unanswered.
    def test_page_failed(self) -> None:
        made, child, first = self.engine_start()
        child.bytes_write(_line_bytes("browser_error"))
        self.assertEqual(child.run_end(), (_ENDING_FAILED, b""))
        error = _line_get("browser_error")
        path = os.path.join(made.root, _TAP_FILE)
        with open(path, encoding="utf-8") as file:
            self.assertEqual(file.read(), f"Bail out! {error['message']}\n")
        expected = [
            _sent_entry(first),
            _received_entry(_REPLY_FULL),
            _received_entry(_line_bytes("browser_error")),
        ]
        self.assertEqual(_audit_read(self, made.root), expected)


# The driver's children end by the hangup, however the driver was started.
class TestDriverHangup(unittest.TestCase):
    # A driver started with the hangup ignored still passes the suite.
    def test_hangup_restored(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                _DRIVER_PATH,
                "--stream",
                "--module",
                _HANGUP_SUITE,
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            preexec_fn=functools.partial(
                signal.signal, signal.SIGHUP, signal.SIG_IGN
            ),
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
