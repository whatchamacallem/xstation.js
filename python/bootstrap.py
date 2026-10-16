# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# This comment intentionally blank. No documentation goes here.
import contextlib, hashlib, io, os, platform, re, runpy, shlex, signal, sys
import types
from collections.abc import Callable
from typing import NamedTuple, NoReturn, TextIO

_BOOTSTRAP_PATH = os.path.abspath(__file__)

# A module's name is an identifier, so its file stays in the directory.
_MODULE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# What shows that the session waits for a command, as dash's `PS1` does.
_PROMPT = b"$ "

# The most taken from a descriptor in one read.
_READ_SIZE = 1 << 16

# The signals handled here, held back while a child forks.
_SIGNALS = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM}


# A module to run and its arguments, as a forked child carries them out.
class Module(NamedTuple):
    path: str
    args: list[str]


# Unwinds a forked child out of the session, to run its module.
class ModuleStart(BaseException):
    def __init__(self, module: Module) -> None:
        super().__init__(module.path)
        self.module = module


# A command that can't be carried out, reported to the terminal.
class CommandError(Exception):
    pass


# Abandons the input being read, as a `^C` does in dash.
class InputAbandoned(Exception):
    pass


class Session:
    # Sets the signal handlers.
    def __init__(self, modules: str) -> None:
        self.modules = modules
        # The running module's pid, None while none runs.
        self.child: int | None = None
        # Set while input is read, so that a `^C` abandons it.
        self.reading = False
        # Set by a `^C` between reads, so that the next read is abandoned.
        self.interrupted = False
        self.builtins: dict[str, Callable[[list[str]], None]] = {
            "ls": self.ls,
            "put": self.put,
            "restart": self.restart,
        }
        signal.signal(signal.SIGINT, self.signal_interrupt)
        for signal_number in (signal.SIGHUP, signal.SIGTERM):
            signal.signal(signal_number, self.signal_end)

    # Writes the first line, with this file's digest so an update shows.
    def banner_write(self) -> None:
        with open(_BOOTSTRAP_PATH, "rb") as own_file:
            digest = hashlib.sha256(own_file.read()).hexdigest()
        line_write(
            1,
            f"bootstrap {_BOOTSTRAP_PATH} sha256 {digest} pid {os.getpid()}"
            f" python {platform.python_version()} modules {self.modules}",
        )

    # Splits the line into words with the quoting of `sh`, then runs them.
    def command_run(self, line: bytes) -> None:
        try:
            text = line.decode()
        except UnicodeDecodeError as error:
            raise CommandError(f"not UTF-8: {error}") from error
        try:
            words = shlex.split(text)
        except ValueError as error:
            raise CommandError(f"{text}: {error}") from error
        if not words:
            return
        name, *args = words
        builtin = self.builtins.get(name)
        if builtin is None:
            self.module_start(name, args)
        else:
            builtin(args)

    # Returns the next line without its newline, or None at the end of input.
    def line_read(self) -> bytes | None:
        line = bytearray()
        try:
            self.read_start()
            # A byte at a time, so what follows the line is left for a module.
            while not line.endswith(b"\n"):
                byte = os.read(0, 1)
                if not byte:
                    return bytes(line) if line else None
                line += byte
        finally:
            self.reading = False
        return bytes(line[:-1])

    # Lists the directory's files with their sizes and digests.
    def ls(self, args: list[str]) -> None:
        if args:
            raise CommandError("usage: ls")
        with os.scandir(self.modules) as iterator:
            for entry in sorted(iterator, key=lambda entry: entry.name):
                if not entry.is_file(follow_symlinks=False):
                    continue
                with open(entry.path, "rb") as entry_file:
                    data = entry_file.read()
                digest = hashlib.sha256(data).hexdigest()
                line_write(1, f"{len(data)} {digest} {entry.name}")

    # Returns the module's path, failing on a name that isn't an identifier.
    def module_path(self, name: str) -> str:
        if not _MODULE_NAME.fullmatch(name):
            raise CommandError(f"{name}: not a module name")
        return os.path.join(self.modules, f"{name}.py")

    # Runs the module in a forked child and waits, reporting an exit not 0.
    def module_start(self, name: str, args: list[str]) -> None:
        path = self.module_path(name)
        if not os.path.isfile(path):
            raise CommandError(f"{name}: not found")
        signal.pthread_sigmask(signal.SIG_BLOCK, _SIGNALS)
        pid = os.fork()
        if pid == 0:
            for signal_number in (signal.SIGHUP, signal.SIGTERM):
                signal.signal(signal_number, signal.SIG_DFL)
            # A `^C` raises KeyboardInterrupt, as under `python3`.
            signal.signal(signal.SIGINT, signal.default_int_handler)
            # A session of its own, so a `^C` or a kill reaches all it starts.
            os.setsid()
            signal.pthread_sigmask(signal.SIG_UNBLOCK, _SIGNALS)
            raise ModuleStart(Module(path, args))
        self.child = pid
        signal.pthread_sigmask(signal.SIG_UNBLOCK, _SIGNALS)
        _, status = os.waitpid(pid, 0)
        self.child = None
        # What the module left running ends with it.
        group_kill(pid, signal.SIGKILL)
        code = os.waitstatus_to_exitcode(status)
        if code:
            line_write(2, f"{name}: exit {code}")

    # Saves what follows, up to the end of input, as the module's file.
    def put(self, args: list[str]) -> None:
        if len(args) != 1:
            raise CommandError("usage: put NAME")
        path = self.module_path(args[0])
        data = self.text_read()
        with open(path, "wb") as module_file:
            module_file.write(data)
        name = os.path.basename(path)
        digest = hashlib.sha256(data).hexdigest()
        line_write(1, f"saved {name} {len(data)} bytes sha256 {digest}")

    # Starts a read, abandoning it at once if a `^C` came since the last one.
    def read_start(self) -> None:
        self.reading = True
        if self.interrupted:
            raise InputAbandoned

    # Execs this file again with the command line ttyd gave, keeping the pid.
    def restart(self, args: list[str]) -> NoReturn:
        if args:
            raise CommandError("usage: restart")
        os.execv(sys.executable, sys.orig_argv)

    # Prompts for commands and runs them until the end of input.
    def run(self) -> NoReturn:
        self.banner_write()
        while True:
            all_write(1, _PROMPT)
            try:
                line = self.line_read()
                if line is None:
                    sys.exit(0)
                self.command_run(line)
            except InputAbandoned:
                self.interrupted = False
                all_write(1, b"\n")
            except CommandError as error:
                line_write(2, str(error))

    # Kills the child's group, then dies of the signal so ttyd sees how.
    def signal_end(
        self, signal_number: int, frame: types.FrameType | None
    ) -> None:
        if self.child is not None:
            group_kill(self.child, signal.SIGKILL)
        signal.signal(signal_number, signal.SIG_DFL)
        signal.raise_signal(signal_number)

    # Passes a `^C` on to the running module's group, or abandons the input.
    def signal_interrupt(
        self, signal_number: int, frame: types.FrameType | None
    ) -> None:
        if self.child is not None:
            group_kill(self.child, signal_number)
        elif self.reading:
            raise InputAbandoned
        else:
            self.interrupted = True

    # Returns what is read up to the end of input.
    def text_read(self) -> bytes:
        data = bytearray()
        try:
            self.read_start()
            while chunk := os.read(0, _READ_SIZE):
                data += chunk
        finally:
            self.reading = False
        return bytes(data)


# Writes all the bytes to the descriptor.
def all_write(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        view = view[os.write(descriptor, view) :]


# Sends the signal to the group, which is gone once all of it has exited.
def group_kill(pid: int, signal_number: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pid, signal_number)


# Writes the text and a newline to the descriptor, as `UTF-8`.
def line_write(descriptor: int, text: str) -> None:
    all_write(descriptor, f"{text}\n".encode())


# Runs the module in the forked child as `python3 -u` would run it.
def module_run(module: Module, modules: str) -> None:
    os.chdir(modules)
    os.environ["XSJS_BOOTSTRAP"] = _BOOTSTRAP_PATH
    os.environ["XSJS_MODULES"] = modules
    sys.stdout = stream_unbuffered(1, sys.stdout)
    sys.stderr = stream_unbuffered(2, sys.stderr)
    sys.argv = [module.path, *module.args]
    sys.path[0] = os.path.dirname(module.path)
    runpy.run_path(module.path, run_name="__main__")


# Runs the session until the end of input, returning only in a forked child.
def session_run(modules: str) -> Module:
    os.makedirs(modules, exist_ok=True)
    session = Session(modules)
    try:
        session.run()
    except ModuleStart as start:
        return start.module


# Returns a stream on the descriptor that writes at once, as under `-u`.
def stream_unbuffered(descriptor: int, replaced: TextIO) -> TextIO:
    return io.TextIOWrapper(
        io.FileIO(descriptor, "w", closefd=False),
        encoding=replaced.encoding,
        errors=replaced.errors,
        write_through=True,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <modules directory>", file=sys.stderr)
        sys.exit(2)
    modules_path = os.path.abspath(sys.argv[1])
    module_run(session_run(modules_path), modules_path)
