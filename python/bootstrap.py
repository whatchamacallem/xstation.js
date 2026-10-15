# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# This comment intentionally blank. No documentation goes here.
import base64, contextlib, hashlib, io, json, os, platform, re, runpy
import selectors, signal, sys, time, tty, types
from typing import Any, NamedTuple, NoReturn, TextIO

_BOOTSTRAP_PATH = os.path.abspath(__file__)

# The fields of each type of message from the page, besides type.
_INPUT_FIELDS: dict[str, dict[str, type[Any]]] = {
    "eof": {},
    "in": {"data": str},
    "kill": {},
    "list": {},
    "put": {"name": str, "text": str},
    "restart": {},
    "run": {"name": str, "args": list},
}

# A module's name is an identifier and `.py`, so it stays in the directory.
_MODULE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.py")

# The most taken from a descriptor in one read.
_READ_SIZE = 1 << 16

# The signals handled here, held back while a child forks.
_SIGNALS = {signal.SIGCHLD, signal.SIGHUP, signal.SIGTERM}


# A module to run and its arguments, as a forked child carries them out.
class Module(NamedTuple):
    path: str
    args: list[str]


# Unwinds a forked child out of the session, to run its module.
class ModuleStart(BaseException):
    def __init__(self, module: Module) -> None:
        super().__init__(module.path)
        self.module = module


# A module running in a forked child.
class Child:
    def __init__(self, name: str, pid: int, stdin: int) -> None:
        self.name = name
        self.pid = pid
        # None once the page sent eof.
        self.stdin: int | None = stdin
        # The output streams not yet at EOF.
        self.streams_open = 2
        # None until the child is reaped.
        self.code: int | None = None


class Session:
    # Watches the terminal and the wake up pipe, and sets the signal handlers.
    def __init__(self, modules: str) -> None:
        self.modules = modules
        self.child: Child | None = None
        # What the page wrote after its last newline.
        self.input_partial = bytearray()
        self.selector = selectors.DefaultSelector()
        self.selector.register(0, selectors.EVENT_READ, self.input_read)
        self.wake_reader, self.wake_writer = os.pipe()
        os.set_blocking(self.wake_writer, False)
        self.selector.register(
            self.wake_reader, selectors.EVENT_READ, self.wake_read
        )
        signal.set_wakeup_fd(self.wake_writer)
        signal.signal(signal.SIGCHLD, signal_wake)
        for signal_number in (signal.SIGHUP, signal.SIGTERM):
            signal.signal(signal_number, self.signal_end)

    # Sends the exit once the child is reaped and its streams have ended.
    def child_end(self) -> None:
        child = self.child
        # A wake up can come after the exit was sent.
        if child is None:
            return
        if child.code is None:
            pid, status = os.waitpid(child.pid, os.WNOHANG)
            if pid == 0:
                return
            child.code = os.waitstatus_to_exitcode(status)
        if child.streams_open:
            return
        self.child = None
        if child.stdin is not None:
            os.close(child.stdin)
        self.send({"type": "exit", "name": child.name, "code": child.code})
        self.modules_send()

    # Closes the child's stdin, so its next read of it gets EOF.
    def child_eof(self) -> None:
        os.close(self.child_stdin())
        self.child_running().stdin = None

    # Sends what the child wrote on the stream, or notes the stream's end.
    def child_read(self, descriptor: int, stream_name: str) -> None:
        chunk = os.read(descriptor, _READ_SIZE)
        if chunk:
            self.send(
                {
                    "type": "out",
                    "stream": stream_name,
                    "data": base64.b64encode(chunk).decode("ascii"),
                }
            )
            return
        self.selector.unregister(descriptor)
        os.close(descriptor)
        self.child_running().streams_open -= 1
        self.child_end()

    # Returns the running child, failing when there is none.
    def child_running(self) -> Child:
        if self.child is None:
            raise RuntimeError("no module is running")
        return self.child

    # Forks a child that runs the module with the arguments, on pipes.
    def child_start(self, name: str, args: list[Any]) -> None:
        if self.child is not None:
            raise RuntimeError(
                f"{self.child.name} is still running as pid {self.child.pid}"
            )
        if any(type(argument) is not str for argument in args):
            raise ValueError(f"run's args aren't all strings: {args!r}")
        path = self.module_path(name)
        stdin_reader, stdin_writer = os.pipe()
        stdout_reader, stdout_writer = os.pipe()
        stderr_reader, stderr_writer = os.pipe()
        signal.pthread_sigmask(signal.SIG_BLOCK, _SIGNALS)
        pid = os.fork()
        if pid == 0:
            os.dup2(stdin_reader, 0)
            os.dup2(stdout_writer, 1)
            os.dup2(stderr_writer, 2)
            for descriptor in (
                stdin_reader,
                stdin_writer,
                stdout_reader,
                stdout_writer,
                stderr_reader,
                stderr_writer,
                self.wake_reader,
                self.wake_writer,
            ):
                os.close(descriptor)
            self.selector.close()
            signal.set_wakeup_fd(-1)
            for signal_number in _SIGNALS:
                signal.signal(signal_number, signal.SIG_DFL)
            # A session of its own, so kill reaches all it starts.
            os.setsid()
            signal.pthread_sigmask(signal.SIG_UNBLOCK, _SIGNALS)
            raise ModuleStart(Module(path, args))
        for descriptor in (stdin_reader, stdout_writer, stderr_writer):
            os.close(descriptor)
        self.child = Child(name, pid, stdin_writer)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, _SIGNALS)
        for descriptor, stream_name in (
            (stdout_reader, "stdout"),
            (stderr_reader, "stderr"),
        ):
            self.selector.register(
                descriptor,
                selectors.EVENT_READ,
                lambda descriptor=descriptor, stream_name=stream_name: (
                    self.child_read(descriptor, stream_name)
                ),
            )
        self.send({"type": "started", "name": name, "pid": pid, "args": args})

    # Returns the running child's stdin, failing once the page sent eof.
    def child_stdin(self) -> int:
        child = self.child_running()
        if child.stdin is None:
            raise RuntimeError(f"{child.name}'s stdin is already closed")
        return child.stdin

    # Writes all the bytes to the child's stdin, waiting as the pipe fills.
    def child_write(self, data: bytes) -> None:
        stdin = self.child_stdin()
        view = memoryview(data)
        while view:
            view = view[os.write(stdin, view) :]

    # Sends the hello, with this file's digest so an update shows.
    def hello_send(self) -> None:
        with open(_BOOTSTRAP_PATH, "rb") as own_file:
            own = own_file.read()
        self.send(
            {
                "type": "hello",
                "pid": os.getpid(),
                "python": platform.python_version(),
                "bootstrap": _BOOTSTRAP_PATH,
                "sha256": hashlib.sha256(own).hexdigest(),
                "modules": self.modules,
                "started": time.time(),
            }
        )

    # Reads input and acts on whole lines in order.
    def input_read(self) -> None:
        chunk = os.read(0, _READ_SIZE)
        if not chunk:
            raise EOFError("the terminal closed")
        self.input_partial += chunk
        if b"\n" not in chunk:
            return
        *lines, self.input_partial = self.input_partial.split(b"\n")
        for line in lines:
            self.message_answer(line)

    # Handles descriptors until an error, then kills the child's group.
    def loop(self) -> NoReturn:
        try:
            while True:
                for key, _ in self.selector.select():
                    key.data()
        finally:
            if self.child is not None:
                group_kill(self.child.pid, signal.SIGKILL)

    # Acts on a page line, which must hold a known type's exact fields.
    def message_answer(self, line: bytearray) -> None:
        message: dict[str, Any] = json.loads(line)
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
        if kind == "eof":
            self.child_eof()
        elif kind == "in":
            self.child_write(base64.b64decode(message["data"], validate=True))
        elif kind == "kill":
            group_kill(self.child_running().pid, signal.SIGTERM)
        elif kind == "list":
            self.modules_send()
        elif kind == "put":
            self.module_put(message["name"], message["text"])
        elif kind == "restart":
            self.restart()
        else:
            self.child_start(message["name"], message["args"])

    # Returns the module's path in the directory, failing on any other name.
    def module_path(self, name: str) -> str:
        if not _MODULE_NAME.fullmatch(name):
            raise ValueError(f"not a module name: {name!r}")
        return os.path.join(self.modules, name)

    # Writes the module's text as `UTF-8` and sends its size and digest.
    def module_put(self, name: str, text: str) -> None:
        data = text.encode()
        with open(self.module_path(name), "wb") as module_file:
            module_file.write(data)
        self.send(
            {
                "type": "saved",
                "name": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
        self.modules_send()

    # Sends the directory's modules with their sizes and digests.
    def modules_send(self) -> None:
        self.send({"type": "modules", "entries": modules_list(self.modules)})

    # Execs this file again with the command line ttyd gave, keeping the pid.
    def restart(self) -> NoReturn:
        if self.child is not None:
            raise RuntimeError(
                f"{self.child.name} is still running as pid {self.child.pid}"
            )
        os.execv(sys.executable, sys.orig_argv)

    # Writes the messages' lines to the terminal in one write, all of it.
    def send(self, *messages: dict[str, Any]) -> None:
        data = memoryview(
            b"".join(
                json.dumps(message).encode("ascii") + b"\n"
                for message in messages
            )
        )
        while data:
            data = data[os.write(1, data) :]

    # Kills the child's group, then dies of the signal so ttyd sees how.
    def signal_end(
        self, signal_number: int, frame: types.FrameType | None
    ) -> None:
        if self.child is not None:
            group_kill(self.child.pid, signal.SIGKILL)
        signal.signal(signal_number, signal.SIG_DFL)
        signal.raise_signal(signal_number)

    # Drains the wake up pipe and sends the exit of a child that ended.
    def wake_read(self) -> None:
        os.read(self.wake_reader, _READ_SIZE)
        self.child_end()


# Sends the signal to the group, which is gone once all of it has exited.
def group_kill(pid: int, signal_number: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pid, signal_number)


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


# Returns the directory's files, sorted, with their sizes and digests.
def modules_list(modules: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with os.scandir(modules) as iterator:
        for entry in sorted(iterator, key=lambda entry: entry.name):
            if not entry.is_file(follow_symlinks=False):
                continue
            with open(entry.path, "rb") as entry_file:
                data = entry_file.read()
            entries.append(
                {
                    "name": entry.name,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    return entries


# Runs the session until a signal, returning only in a forked child.
def session_run(modules: str) -> Module:
    os.makedirs(modules, exist_ok=True)
    tty.setraw(0)
    session = Session(modules)
    session.hello_send()
    session.modules_send()
    try:
        session.loop()
    except ModuleStart as start:
        return start.module


# Lets SIGCHLD reach the wake up pipe, which the loop reads.
def signal_wake(signal_number: int, frame: types.FrameType | None) -> None:
    pass


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
