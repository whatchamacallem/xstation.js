# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the console role in debug mode, which runs the console's shell, dash
# in its bubblewrap sandbox: each run of `bootstrap_run` is a forked child
# whose controlling tty, stdin, stdout and stderr are a new pty of
# `pty.openpty`, as ttyd runs it, with its environment set in the child, and
# the test types a command line to the shell on the other side of the pty
# once its first prompt has come. The test reads only what the shell prints
# on the pty, from its first prompt on, and finds a command's output between
# two markers that `printf` escapes make, so that no echo of the input holds
# them. Dash starts in the sandbox's /tmp with only the variables the
# console keeps, at the shell's verbose level of the settings, its code
# given back; SIGTERM sent from outside to the sandbox the console role
# forked, found by its parent pid in /proc, gives 128 plus the signal; and a
# heredoc of binary bytes typed to `cat` comes back as the pty's output
# processing changes it, so that a connection that is not binary fails. The
# logged argv, the prompt, the start directory, the codes of the terminated
# sandbox, the heredoc's payload and output, and the expected texts are the
# gold's. The scratch directories go under build/.

import base64, bootstrap, contextlib, errno, harness, json, os, pty, signal
import sqlite3, sys, tempfile, termios, traceback, unittest
from typing import NamedTuple

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_bootstrap_dash"

# The most bytes a read of the pty takes at once.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The test's own copy of the console's shell, as the log names it.
_DASH_ARGV: list[str] = harness.gold_get(f"{_GOLD_ID}.argv")

# The test's own copy of the shell's verbose form.
_DASH_VERBOSE: list[str] = harness.gold_get(f"{_GOLD_ID}.argv_verbose")

# The prompt dash writes when it waits for a command.
_PROMPT: bytes = harness.gold_get(f"{_GOLD_ID}.prompt").encode("utf-8")

# The directory dash starts in, the sandbox's own.
_START_DIRECTORY: str = harness.gold_get(f"{_GOLD_ID}.start_directory")

# The heredoc's lines: every byte value dash keeps, and bad UTF 8 sequences.
_PAYLOAD = base64.b64decode(harness.gold_get(f"{_GOLD_ID}.binary.payload.d"))

# What the pty prints of the payload, after its output processing.
_OUTPUT = base64.b64decode(harness.gold_get(f"{_GOLD_ID}.binary.output.d"))

# The bytes the pty's line discipline acts on, each typed after `_LNEXT`.
_ACTED: list[int] = harness.gold_get(f"{_GOLD_ID}.binary.acted")

# The line discipline's literal next, which makes the byte after it plain.
_LNEXT = b"\x16"

# The heredoc's delimiter, quoted on the command line so that nothing expands.
_HEREDOC_END = "END"

# The marker the output of a command starts after.
_MARK_START = b"<<B>>"

# The marker the output of a command ends before.
_MARK_END = b"<<E>>"

# The environment variable that once held the provider key, a setting.
_PROVIDER_VARIABLE: str = harness.setting_get("provider.variable")

# The environment of a console run: the variables it keeps and two it drops.
_CONSOLE_ENVIRONMENT = {
    "HOME": "/home/test",
    "PATH": "/usr/bin:/bin",
    "TERM": "xterm-256color",
    _PROVIDER_VARIABLE: "the provider key of the test",
    "OTHER": "dropped",
}

# Variables the shell prints: those kept, `LANG`, never set, the two dropped.
_FOUND_VARIABLES = (
    "HOME",
    "PATH",
    "TERM",
    "LANG",
    "OTHER",
    _PROVIDER_VARIABLE,
)

# The text the shell prints for a variable its environment lacks.
_UNSET_TEXT = "unset"

# What the shell prints for each variable.
_FOUND_VALUES = [
    "/home/test",
    "/usr/bin:/bin",
    "xterm-256color",
    _UNSET_TEXT,
    _UNSET_TEXT,
    _UNSET_TEXT,
]

# The code the shell exits with after printing what it found.
_FOUND_CODE = 3

# The command line that ends the shell with code 0.
_EXIT_COMMAND = b"exit 0\n"

# The command line by which the shell ends itself with SIGKILL.
_KILL_COMMAND = b"kill -KILL $$\n"

# The code a shell gives a program a signal ended: this plus the signal.
_SIGNAL_BASE = 128

# The console role's code once SIGTERM from outside ended its sandbox.
_TERMINATED_CODE: int = harness.gold_get(f"{_GOLD_ID}.terminated.code")

# The code `verbose.exec` logs for that sandbox, minus the signal.
_TERMINATED_EXEC: int = harness.gold_get(f"{_GOLD_ID}.terminated.exec_code")

# The verbose level that logs the shell's start and exit, not verbose.
_LOGGED_LEVEL = 1

# The directory of the processes, each under its pid.
_PROC_PATH = "/proc"

# The file of a process that holds its parent's pid.
_STATUS_NAME = "status"

# The start of the line of that file which holds the parent's pid.
_PPID_FIELD = b"PPid:"

# The file in the root that holds the log.
_LOG_NAME = "_verbose.sqlite"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"

# The file in its scratch directory a child writes how its run ended to.
_ENDING_NAME = "ending.txt"

# The exit code of a child that killed itself once its run ended.
_KILLED = -signal.SIGKILL


# A scratch directory and its root.
class ScratchRoot(NamedTuple):
    scratch: str
    root: str


# A text of this module's gold, each `{n}` replaced by the value at `n`.
def _text_get(name: str, *values: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    for number, value in enumerate(values):
        text = text.replace(f"{{{number}}}", value)
    return text


# The `printf` escapes of the bytes, which print them and never hold them.
def _escapes_make(data: bytes) -> str:
    return "".join(f"\\{value:03o}" for value in data)


# The command line printing a marker, the command's output, a marker, `then`.
def _marked_line(command: str, then: str) -> bytes:
    start = _escapes_make(_MARK_START)
    end = _escapes_make(_MARK_END)
    text = f"printf '{start}'; {command}; printf '{end}'; {then}\n"
    return text.encode("utf-8")


# The command line that prints the variables and the directory, then exits.
def _found_command() -> bytes:
    words = [f'"${{{name}-{_UNSET_TEXT}}}"' for name in _FOUND_VARIABLES]
    printed = f"printf '%s\\n' {' '.join(words)}; pwd -P"
    return _marked_line(printed, f"exit {_FOUND_CODE}")


# The heredoc to `cat` of the payload as typed, then the shell's exit.
def _heredoc_typed(payload: bytes) -> bytes:
    typed = bytearray(_marked_line(f"cat <<'{_HEREDOC_END}'", "exit 0"))
    for value in payload:
        if value in _ACTED:
            typed += _LNEXT
        typed.append(value)
    typed += f"{_HEREDOC_END}\n".encode("utf-8")
    return bytes(typed)


# The log lines of the shell's run and of its exit with the code.
def _exec_lines(argv: list[str], code: int) -> list[tuple[str, str]]:
    command = " ".join(argv)
    return [
        (_SERVER_THREAD, _text_get("verbose_exec_run", command)),
        (_SERVER_THREAD, _text_get("verbose_exec_exit", command, str(code))),
    ]


# The thread and text of each line of the root's log, which must be open.
def _log_read(root: str) -> list[tuple[str, str]]:
    path = os.path.join(root, _LOG_NAME)
    if not os.path.isfile(path):
        raise AssertionError(f"the log was never opened: {path}")
    with contextlib.closing(sqlite3.connect(path)) as connection:
        cursor = connection.execute(_LOG_QUERY)
        rows: list[tuple[str, str]] = cursor.fetchall()
    return rows


# Makes a debug scratch root with the checkout's settings at the level.
def _root_make(case: unittest.TestCase, level: int) -> ScratchRoot:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
    case.addCleanup(scratch.cleanup)
    root = os.path.join(scratch.name, "root")
    os.mkdir(root)
    loaded = harness.settings_copy()
    loaded["debug"] = True
    loaded["verbose_level"] = level
    path = os.path.join(root, "settings.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(loaded, file)
    return ScratchRoot(scratch.name, root)


# In the forked child: `login_tty`, environment, run, ending to file, a kill.
def _child_main(
    slave: int, argv: list[str], environment: dict[str, str], path: str
) -> None:
    try:
        try:
            os.login_tty(slave)
            os.environ.clear()
            os.environ.update(environment)
            ending = repr(bootstrap.bootstrap_run(argv))
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# `bootstrap_run` in a forked child on a new pty, and the typist's end of it.
class ConsoleChild:
    # Forks the child that runs the console role of the root on the pty.
    def __init__(self, case: unittest.TestCase, made: ScratchRoot) -> None:
        self.ending_path = os.path.join(made.scratch, _ENDING_NAME)
        argv = ["--root", made.root, "console"]
        master, slave = pty.openpty()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(master)
            _child_main(slave, argv, _CONSOLE_ENVIRONMENT, self.ending_path)
        os.close(slave)
        self.pid = pid
        self.master = master
        self.reaped = False
        self.printed = bytearray()
        self.prompted = 0
        case.addCleanup(self.cleanup)

    # Reads and keeps what the child wrote, empty once no process holds it.
    def bytes_read(self) -> bytes:
        try:
            data = os.read(self.master, _READ_BYTES)
        except OSError as error:
            # Linux reads EIO from a pty whose other side no process holds.
            if error.errno != errno.EIO:
                raise
            return b""
        self.printed += data
        return data

    # Writes all the bytes to the child, as typed.
    def bytes_write(self, data: bytes) -> None:
        view = memoryview(data)
        while view:
            written = os.write(self.master, view)
            view = view[written:]

    # Reads up to the shell's first prompt, where every comparison starts.
    def prompt_wait(self) -> None:
        while _PROMPT not in self.printed:
            if not self.bytes_read():
                raise AssertionError(f"no prompt: {bytes(self.printed)!r}")
        self.prompted = self.printed.index(_PROMPT)

    # The pid of the one process the console role forked, its sandbox.
    def sandbox_find(self) -> int:
        found: list[int] = []
        for name in os.listdir(_PROC_PATH):
            if not name.isdigit():
                continue
            path = os.path.join(_PROC_PATH, name, _STATUS_NAME)
            try:
                with open(path, "rb") as file:
                    lines = file.read().splitlines()
            except (FileNotFoundError, ProcessLookupError):
                # A process may end between the listing and the read.
                continue
            for line in lines:
                if line.startswith(_PPID_FIELD):
                    if int(line[len(_PPID_FIELD) :]) == self.pid:
                        found.append(int(name))
        if len(found) != 1:
            raise AssertionError(f"the children of {self.pid}: {found}")
        return found[0]

    # The bytes printed between the markers, from the first prompt on.
    def marked_get(self) -> bytes:
        shown = bytes(self.printed[self.prompted :])
        start = shown.find(_MARK_START)
        end = shown.find(_MARK_END, start + len(_MARK_START))
        if start < 0 or end < 0:
            raise AssertionError(f"no markers: {shown!r}")
        return shown[start + len(_MARK_START) : end]

    # Whether the pty is raw: no line editing, no echo, no output processing.
    def raw_get(self) -> bool:
        attributes = termios.tcgetattr(self.master)
        oflag: int = attributes[1]
        lflag: int = attributes[3]
        edited = lflag & (termios.ICANON | termios.ECHO)
        return not edited and not oflag & termios.OPOST

    # Reads the shell's echo and output to the end, then returns how it ended.
    def run_end(self) -> str:
        while self.bytes_read():
            pass
        _, status = os.waitpid(self.pid, 0)
        self.reaped = True
        code = os.waitstatus_to_exitcode(status)
        if code != _KILLED:
            raise AssertionError(f"the child {self.pid} exited with {code}")
        with open(self.ending_path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(self.ending_path)
        return ending

    # Kills and reaps a child a failed test left, and closes this side.
    def cleanup(self) -> None:
        if not self.reaped:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
            self.reaped = True
        os.close(self.master)


# Tests the console role, which runs the sandboxed dash in debug mode.
class TestConsole(unittest.TestCase):
    # Dash starts in its own /tmp with only the kept variables, its code back.
    def test_console_scrubbed(self) -> None:
        made = _root_make(self, harness.setting_get("verbose_level"))
        child = ConsoleChild(self, made)
        child.prompt_wait()
        child.bytes_write(_found_command())
        self.assertEqual(child.run_end(), repr(_FOUND_CODE))
        self.assertFalse(child.raw_get())
        lines = child.marked_get().decode("utf-8").splitlines()
        self.assertEqual(lines, [*_FOUND_VALUES, _START_DIRECTORY])

    # Dash runs at the verbose level of the settings, and its verbose form.
    def test_console_level(self) -> None:
        logged: list[list[tuple[str, str]]] = [
            [],
            _exec_lines(_DASH_ARGV, 0),
            _exec_lines(_DASH_VERBOSE, 0),
        ]
        for level, expected in enumerate(logged):
            made = _root_make(self, level)
            child = ConsoleChild(self, made)
            child.prompt_wait()
            child.bytes_write(_EXIT_COMMAND)
            self.assertEqual(child.run_end(), repr(0))
            self.assertEqual(_log_read(made.root), expected)

    # A dash a signal ended gives its sandbox's code, 128 plus the signal.
    def test_console_signal(self) -> None:
        made = _root_make(self, harness.setting_get("verbose_level"))
        child = ConsoleChild(self, made)
        child.prompt_wait()
        child.bytes_write(_KILL_COMMAND)
        code = _SIGNAL_BASE + signal.SIGKILL
        self.assertEqual(child.run_end(), repr(code))

    # SIGTERM from outside to the sandbox gives 128 plus it, and is logged.
    def test_console_terminated(self) -> None:
        made = _root_make(self, _LOGGED_LEVEL)
        child = ConsoleChild(self, made)
        child.prompt_wait()
        os.kill(child.sandbox_find(), signal.SIGTERM)
        self.assertEqual(child.run_end(), repr(_TERMINATED_CODE))
        expected = _exec_lines(_DASH_ARGV, _TERMINATED_EXEC)
        self.assertEqual(_log_read(made.root), expected)

    # A heredoc of binary bytes to `cat` comes back as the pty prints them.
    def test_console_binary(self) -> None:
        made = _root_make(self, harness.setting_get("verbose_level"))
        child = ConsoleChild(self, made)
        child.prompt_wait()
        child.bytes_write(_heredoc_typed(_PAYLOAD))
        self.assertEqual(child.run_end(), repr(0))
        self.assertEqual(child.marked_get(), _OUTPUT)
