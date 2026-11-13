# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Headless Chrome driven over the DevTools protocol by one client, the Browser,
# on the `Transport` it is given: LinuxPipe here, or the WindowsRelay of
# devtools_windows.py, whose helpers that a running suite tests stay here.
#
# LinuxPipe drives Chrome for Testing, as admin.md installs it, headless by
# --remote-debugging-pipe, with XDG_CACHE_HOME set to the profile, where
# fontconfig caches fonts, and with no back/forward cache, which would keep a
# page navigated away from alive, and the OPFS files its workers hold. It opens
# about:blank, not the new tab page, and leads a process group of its own,
# whose end the profile's removal waits for, as Chrome's network service writes
# there after a killed browser. The browser's exit closes its pipe, and the
# call or wait under way raises one ConnectionError whose cause is the exit
# code; an exit with an error code that no call saw fails the Browser's end.
# With the switch `switches.anthropic`, LinuxPipe starts the headless shell of
# Anthropic's cloud container, Playwright's, in its place.

import base64, fcntl, functools, glob, hashlib, json, math, os, select, shutil
import signal, subprocess, switches, tempfile, time, types
from collections.abc import Callable
from typing import Any, IO, NamedTuple, NoReturn, Protocol, Self

# The public names of this module, as its stub declares them.
__all__ = [
    "AnyChannel",
    "Browser",
    "LinuxPipe",
    "PageEvents",
    "PipeChannel",
    "ProtocolClient",
    "SocketChannel",
    "Transport",
    "WaitTimer",
    "blocking_categories",
    "blocking_find",
    "chrome_path",
]

# The Linux browser of Anthropic's cloud container, Playwright's, one match.
_ANTHROPIC_CHROME_PATTERN = (
    "/opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux64"
    "/chrome-headless-shell"
)

# The trace categories of the synchronous loads and of the thread names.
_BLOCKING_CATEGORIES = ("loading", "__metadata")

# The trace events of a synchronous load, as Chrome's versions name them.
_BLOCKING_EVENT_NAMES = frozenset(
    (
        "URLLoader::loadSynchronously",
        "WebURLLoader::loadSynchronously",
        "WebURLLoaderImpl::loadSynchronously",
    )
)

# The build directory of the checkout, where a Linux browser's profile goes.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The Linux browser, the one the test driver may start, one match.
_CHROME_PATTERN = os.path.expanduser(
    "~/.local/share/chrome-for-testing/chrome/linux-*/chrome-linux64/chrome"
)

# The Linux browser's name, as its errors give it.
_CHROME_NAME = "chrome"

# The descriptor the Linux browser reads DevTools from, as the pipe flag sets.
_COMMAND_DESCRIPTOR = 3

# The lowest descriptor a browser's end of a pipe is copied to before start.
_DESCRIPTOR_FLOOR = 5

# The file the browser writes its DevTools port and path to, in the profile.
_DEVTOOLS_PORT_FILE_NAME = "DevToolsActivePort"

# How often the browser's group is polled, as its helpers end within 30 ms.
_GROUP_POLL_SECONDS = 0.01

# What ends each DevTools message on the Linux browser's pipes.
_PIPE_END = b"\0"

# The bytes a read of a pipe asks for, 64 KiB, a default chosen by its writer.
_PIPE_READ_BYTES = 65536

# How often a polling wait looks again, a default chosen by its writer.
_POLL_SECONDS = 0.1

# The start of the name of the profile folder each run makes.
_PROFILE_PREFIX = "xsjs_devtools-"

# The navigation error while WSL has not yet forwarded a new listener.
_REFUSED_ERROR_TEXT = "net::ERR_CONNECTION_REFUSED"

# `C#` reading `$port_`, a thread each way, as PowerShell's CopyToAsync hangs.
_RELAY_SCRIPT = r"""
$ProgressPreference = 'SilentlyContinue'
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Net.Sockets;
using System.Threading;

public static class XsjsDevToolsRelay {
    // The bytes each read copies, 64 KiB, a default chosen by its writer.
    const int CopyBytes = 65536;

    public static void RelayRun(int port) {
        var client = new TcpClient("127.0.0.1", port);
        client.NoDelay = true;
        var network = client.GetStream();
        var input = Console.OpenStandardInput();
        var output = Console.OpenStandardOutput();
        var upload = new Thread(() => {
            StreamCopy(input, network);
            client.Client.Shutdown(SocketShutdown.Send);
        });
        upload.IsBackground = true;
        upload.Start();
        StreamCopy(network, output);
    }

    static void StreamCopy(Stream from, Stream to) {
        var buffer = new byte[CopyBytes];
        int count;
        while ((count = from.Read(buffer, 0, buffer.Length)) > 0) {
            to.Write(buffer, 0, count);
            to.Flush();
        }
    }
}
'@
[XsjsDevToolsRelay]::RelayRun($port_)
"""

# The descriptor the Linux browser writes DevTools to, as the pipe flag sets.
_REPLY_DESCRIPTOR = 4

# Seconds for one answer, event or page load, a default chosen by its writer.
_REPLY_WAIT_SECONDS = 60

# Seconds to retry a refused navigation, a default chosen by its writer.
_SERVER_WAIT_SECONDS = 60

# Seconds for a stopped process to be gone, a default chosen by its writer.
_STOP_WAIT_SECONDS = 5

# The name Chrome gives a renderer's main thread, where the page's UI runs.
_UI_THREAD_NAME = "CrRendererMain"

# What RFC 6455 appends to the key before it is hashed into the accept value.
_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# The opcode of a frame that closes the connection.
_WEBSOCKET_OPCODE_CLOSE = 0x8

# The opcode of a frame that continues a fragmented message.
_WEBSOCKET_OPCODE_CONTINUATION = 0x0

# The opcode of a ping, which a pong answers.
_WEBSOCKET_OPCODE_PING = 0x9

# The opcode of a pong.
_WEBSOCKET_OPCODE_PONG = 0xA

# The opcode of a text frame, which carries every DevTools message.
_WEBSOCKET_OPCODE_TEXT = 0x1


# Where the browser serves DevTools on Windows' 127.0.0.1.
class EndpointAddress(NamedTuple):
    port: int
    path: str


# One WebSocket frame as read: whether it ends its message, its opcode, data.
class SocketFrame(NamedTuple):
    final: bool
    opcode: int
    payload: bytes


# A named wait with a time limit, which fails loud once the limit has passed.
class WaitTimer:
    # Starts the wait, `what` being the thing waited for.
    def __init__(self, what: str, seconds: float) -> None:
        self.what = what
        self.seconds = seconds
        self.end = time.monotonic() + seconds
        self.deadline_cut = False

    # Ends the wait at the deadline instead, when the deadline comes first.
    def deadline_apply(self, deadline: float) -> None:
        if deadline < self.end:
            self.end = deadline
            self.deadline_cut = True

    # Returns the seconds left, or raises `TimeoutError` naming the wait.
    def seconds_left(self) -> float:
        left = self.end - time.monotonic()
        if left > 0:
            return left
        if self.deadline_cut:
            raise TimeoutError(
                f"gave up at the deadline waiting for {self.what}"
            )
        raise TimeoutError(
            f"gave up after {self.seconds:g} s waiting for {self.what}"
        )


# Keeps page loads, trace events, workers and pauses, passes console and calls.
class PageEvents:
    # Starts with no followers, no bindings and nothing seen.
    def __init__(self) -> None:
        self.followers: list[Callable[[str], None]] = []
        self.bindings: dict[str, Callable[[str], None]] = {}
        self.lifecycle: set[tuple[str, str]] = set()
        self.trace: list[dict[str, Any]] = []
        self.trace_done = False
        self.trace_lost = False
        self.workers: dict[str, str] = {}
        self.paused: set[str] = set()

    # Records a load, trace, worker or pause, or passes console text or a call.
    def message_handle(self, message: dict[str, Any]) -> None:
        method = message["method"]
        if method == "Page.lifecycleEvent":
            params = message["params"]
            self.lifecycle.add((params["loaderId"], params["name"]))
        elif method == "Runtime.consoleAPICalled":
            text = console_text(message["params"]["args"])
            for follower in self.followers:
                follower(text)
        elif method == "Runtime.bindingCalled":
            params = message["params"]
            self.bindings[params["name"]](params["payload"])
        elif method == "Tracing.dataCollected":
            self.trace += message["params"]["value"]
        elif method == "Tracing.tracingComplete":
            self.trace_done = True
            self.trace_lost = message["params"]["dataLossOccurred"]
        elif method == "Target.attachedToTarget":
            params = message["params"]
            target = params["targetInfo"]
            if target["type"] == "worker":
                self.workers[target["title"]] = params["sessionId"]
        elif method == "Target.detachedFromTarget":
            gone = message["params"]["sessionId"]
            self.workers = {
                title: session
                for title, session in self.workers.items()
                if session != gone
            }
            self.paused.discard(gone)
        elif method == "Debugger.paused":
            self.paused.add(message["sessionId"])

    # Returns the trace's events, failing if DevTools lost any of them.
    def trace_take(self) -> list[dict[str, Any]]:
        if self.trace_lost:
            raise RuntimeError(
                "the trace lost events, so it can't show everything that ran"
            )
        return self.trace


# A program started by `os.posix_spawn`, its exit read from a pidfd.
class SpawnedProcess:
    # Keeps the program's name and process id, and opens its pidfd.
    def __init__(self, name: str, pid: int) -> None:
        self.name = name
        self.pid = pid
        self.exit_fd = os.pidfd_open(pid)
        self.exit_code: int | None = None

    # Returns the exit code once the program exits, failing when timed out.
    def exit_wait(self, timer: WaitTimer) -> int:
        while self.exit_code is None:
            ready = select.select([self.exit_fd], [], [], timer.seconds_left())
            if ready[0]:
                status = os.waitpid(self.pid, 0)[1]
                os.close(self.exit_fd)
                self.exit_code = os.waitstatus_to_exitcode(status)
        return self.exit_code


# DevTools messages as WebSocket text frames on a byte channel.
class SocketChannel:
    # Keeps the channel's reader and writer.
    def __init__(
        self,
        reader: Callable[[WaitTimer, int], bytes],
        writer: Callable[[bytes], None],
    ) -> None:
        self.reader = reader
        self.writer = writer

    # Sends one WebSocket frame, masked as a client's must be.
    def frame_send(self, opcode: int, payload: bytes) -> None:
        self.writer(frame_encode(opcode, payload, os.urandom(4)))

    # Sends the WebSocket upgrade and checks that DevTools accepted the key.
    def handshake_open(self, host: str, path: str, timer: WaitTimer) -> None:
        key = base64.b64encode(os.urandom(16)).decode()
        self.writer(handshake_request(host, path, key))
        head = head_read(functools.partial(self.reader, timer))
        handshake_check(key, head)

    # Returns the next message, joining fragments and answering pings.
    def message_receive(self, timer: WaitTimer) -> bytes:
        return message_read(
            functools.partial(self.reader, timer), self.frame_send
        )

    # Sends one message as a text frame.
    def message_send(self, data: bytes) -> None:
        self.frame_send(_WEBSOCKET_OPCODE_TEXT, data)


# DevTools messages each ended by a NUL byte, on the Linux browser's pipes.
class PipeChannel:
    # Keeps the browser and the ends of its pipes this side holds.
    def __init__(
        self, process: SpawnedProcess, command_fd: int, reply_fd: int
    ) -> None:
        self.process = process
        self.command_fd = command_fd
        self.reply_fd = reply_fd
        self.pending = bytearray()

    # Raises that the browser closed its pipe, the cause its exit code.
    def closed_raise(self) -> NoReturn:
        name = self.process.name
        timer = WaitTimer(
            f"{name} to exit, its pipe closed", _STOP_WAIT_SECONDS
        )
        code = self.process.exit_wait(timer)
        raise ConnectionError(
            f"{name} closed its DevTools pipe"
        ) from RuntimeError(f"{name} exited with {code}")

    # Returns the next message, without its NUL, failing when the timer ends.
    def message_receive(self, timer: WaitTimer) -> bytes:
        end = self.pending.find(_PIPE_END)
        while end < 0:
            chunk = pipe_read(self.reply_fd, timer, _PIPE_READ_BYTES)
            if not chunk:
                self.closed_raise()
            found = chunk.find(_PIPE_END)
            if found >= 0:
                end = len(self.pending) + found
            self.pending += chunk
        message = bytes(self.pending[:end])
        del self.pending[: end + 1]
        return message

    # Sends one message and its NUL, all of it, as a write may take part.
    def message_send(self, data: bytes) -> None:
        left = memoryview(data + _PIPE_END)
        while left:
            try:
                written = os.write(self.command_fd, left)
            except BrokenPipeError:
                self.closed_raise()
            left = left[written:]


# Either channel of whole DevTools messages.
AnyChannel = SocketChannel | PipeChannel


# Speaks the DevTools protocol over a channel of whole messages.
class ProtocolClient:
    # Keeps the channel and where events go.
    def __init__(
        self,
        channel: AnyChannel,
        event_fn: Callable[[dict[str, Any]], None],
        wait_seconds: float,
    ) -> None:
        self.channel = channel
        self.event_fn = event_fn
        self.wait_seconds = wait_seconds
        self.call_id = 0
        self.session_id = ""
        self.deadline: float | None = None

    # Ends every later wait at `end`, a `time.monotonic()` value, if sooner.
    def deadline_set(self, end: float) -> None:
        self.deadline = end

    # Ends every later wait at `end` alone, in place of the wait's own limit.
    def limit_set(self, end: float) -> None:
        self.wait_seconds = math.inf
        self.deadline = end

    # Passes events on until the condition holds, failing when the wait ends.
    def events_pump(self, what: str, done: Callable[[], bool]) -> None:
        timer = self.timer_start(what)
        while not done():
            message = self.message_next(timer)
            if "id" in message:
                raise RuntimeError(
                    f"DevTools answered call {message['id']} while no call"
                    " was waiting"
                )
            self.event_fn(message)

    # Returns the next DevTools message, decoded, failing when the timer ends.
    def message_next(self, timer: WaitTimer) -> dict[str, Any]:
        message: dict[str, Any] = json.loads(
            self.channel.message_receive(timer)
        )
        return message

    # Returns the result of a DevTools method, on the page once attached.
    def method_call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        browser = method.startswith(("Browser.", "Target."))
        return self.session_call(
            "" if browser else self.session_id, method, params
        )

    # Returns the result of a method on the session, the browser's when empty.
    def session_call(
        self,
        session_id: str,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.call_id += 1
        request: dict[str, Any] = {
            "id": self.call_id,
            "method": method,
            "params": params or {},
        }
        if session_id:
            request["sessionId"] = session_id
        self.channel.message_send(json.dumps(request).encode())
        timer = self.timer_start(f"the reply to {method}")
        while True:
            message = self.message_next(timer)
            if "id" not in message:
                self.event_fn(message)
                continue
            if message["id"] != self.call_id:
                raise RuntimeError(
                    f"DevTools answered call {message['id']} while call"
                    f" {self.call_id} was waiting"
                )
            if "error" in message:
                raise RuntimeError(f"{method}: {message['error']['message']}")
            result: dict[str, Any] = message["result"]
            return result

    # Returns the timer of a wait, ended at the deadline when that comes first.
    def timer_start(self, what: str) -> WaitTimer:
        timer = WaitTimer(what, self.wait_seconds)
        if self.deadline is not None:
            timer.deadline_apply(self.deadline)
        return timer


# What a Browser runs on. Each method sits on one line, which a count reaches.
class Transport(Protocol):
    # Whether a refused navigation is sent again.
    refused_retried: bool

    # Starts the browser and returns the channel to its DevTools.
    def transport_open(self, width_px: int, height_px: int) -> AnyChannel: ...

    # Stops the browser and removes what it left.
    def transport_close(self) -> None: ...


# Chrome on Linux, headless, with DevTools on its descriptors 3 and 4.
class LinuxPipe:
    # A refusal on this machine's own 127.0.0.1 is final, as nothing forwards.
    refused_retried = False

    # Starts nothing yet: the browser's start makes its profile and pipes.
    def __init__(self) -> None:
        self.profile_path = ""
        self.command_fd = -1
        self.reply_fd = -1
        self.process: SpawnedProcess | None = None

    # Ends the browser by closing its command pipe, failing on an unseen exit.
    def browser_stop(self) -> None:
        process = self.process
        if process is None:
            return
        # A code read before the stop was raised by the pipe that saw it.
        seen = process.exit_code is not None
        os.close(self.command_fd)
        self.command_fd = -1
        try:
            code = process.exit_wait(
                WaitTimer(f"{_CHROME_NAME} to exit", _STOP_WAIT_SECONDS)
            )
        except TimeoutError:
            os.kill(process.pid, signal.SIGKILL)
            process.exit_wait(
                WaitTimer(
                    f"{_CHROME_NAME} to exit once killed", _STOP_WAIT_SECONDS
                )
            )
            raise
        if code != 0 and not seen:
            raise RuntimeError(f"{_CHROME_NAME} exited with {code}")

    # Stops the browser, closes this side's pipe ends and removes the profile.
    def transport_close(self) -> None:
        try:
            self.browser_stop()
        finally:
            for fd in (self.command_fd, self.reply_fd):
                if fd >= 0:
                    os.close(fd)
            self.command_fd = -1
            self.reply_fd = -1
            if self.process is not None:
                group_wait(self.process.pid)
            if self.profile_path:
                shutil.rmtree(self.profile_path)

    # Starts the browser on a new profile in `build/`, DevTools on its pipes.
    def transport_open(self, width_px: int, height_px: int) -> PipeChannel:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.profile_path = tempfile.mkdtemp(
            prefix=_PROFILE_PREFIX, dir=_BUILD_PATH
        )
        command_read, self.command_fd = os.pipe()
        command_read = descriptor_raise(command_read)
        self.reply_fd, reply_write = os.pipe()
        reply_write = descriptor_raise(reply_write)
        path = chrome_path()
        try:
            pid = os.posix_spawn(
                path,
                [
                    path,
                    "--headless",
                    "--disable-features=BackForwardCache",
                    "--remote-debugging-pipe",
                    f"--user-data-dir={self.profile_path}",
                    f"--window-size={width_px},{height_px}",
                    "about:blank",
                ],
                {**os.environ, "XDG_CACHE_HOME": self.profile_path},
                file_actions=[
                    (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
                    (os.POSIX_SPAWN_OPEN, 1, os.devnull, os.O_WRONLY, 0),
                    (os.POSIX_SPAWN_OPEN, 2, os.devnull, os.O_WRONLY, 0),
                    (os.POSIX_SPAWN_DUP2, command_read, _COMMAND_DESCRIPTOR),
                    (os.POSIX_SPAWN_DUP2, reply_write, _REPLY_DESCRIPTOR),
                ],
                setpgroup=0,
            )
        finally:
            os.close(command_read)
            os.close(reply_write)
        self.process = SpawnedProcess(_CHROME_NAME, pid)
        return PipeChannel(self.process, self.command_fd, self.reply_fd)


# Headless Chrome over DevTools, on the transport it is given.
class Browser:
    # Keeps the window size and the transport, starting nothing yet.
    def __init__(
        self, width_px: int, height_px: int, transport: Transport
    ) -> None:
        self.width_px = width_px
        self.height_px = height_px
        self.transport = transport
        self.client: ProtocolClient | None = None
        self.events = PageEvents()
        self.target_id = ""

    # Starts the browser and its page, cleaning up if that fails.
    def __enter__(self) -> Self:
        try:
            channel = self.transport.transport_open(
                self.width_px, self.height_px
            )
            self.client = ProtocolClient(
                channel, self.events.message_handle, _REPLY_WAIT_SECONDS
            )
            self.target_attach()
        except BaseException:
            self.transport.transport_close()
            raise
        return self

    # Stops the browser and removes its profile, whatever ended the block.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        self.transport.transport_close()

    # Calls `fn` with each payload the page calls `name` with, on every load.
    def binding_add(self, name: str, fn: Callable[[str], None]) -> None:
        self.events.bindings[name] = fn
        self.client_get().method_call("Runtime.addBinding", {"name": name})

    # Returns the DevTools client, failing if the browser isn't started.
    def client_get(self) -> ProtocolClient:
        if self.client is None:
            raise RuntimeError("the browser isn't started: use a with block")
        return self.client

    # Calls `fn` with the text of each console message from now on.
    def console_follow(self, fn: Callable[[str], None]) -> None:
        self.events.followers.append(fn)

    # Closes the page, so no more calls to it work.
    def page_close(self) -> None:
        self.client_get().method_call(
            "Target.closeTarget", {"targetId": self.target_id}
        )

    # Opens the URL and waits for its load, sent again if refused on the relay.
    def page_open(self, url: str) -> None:
        client = self.client_get()
        timer = WaitTimer(
            f"{url} to accept connections after {_REFUSED_ERROR_TEXT}",
            _SERVER_WAIT_SECONDS,
        )
        navigated = client.method_call("Page.navigate", {"url": url})
        while (
            self.transport.refused_retried
            and navigated.get("errorText") == _REFUSED_ERROR_TEXT
        ):
            time.sleep(min(_POLL_SECONDS, timer.seconds_left()))
            navigated = client.method_call("Page.navigate", {"url": url})
        if "errorText" in navigated:
            raise RuntimeError(f"{url}: {navigated['errorText']}")
        loader_id = navigated["loaderId"]
        client.events_pump(
            f"{url} to load",
            lambda: (loader_id, "load") in self.events.lifecycle,
        )

    # Saves a PNG of the page to the path.
    def screenshot_save(self, path: str) -> None:
        image = self.client_get().method_call(
            "Page.captureScreenshot", {"format": "png"}
        )
        with open(path, "wb") as image_file:
            image_file.write(base64.b64decode(image["data"], validate=True))

    # Evaluates JavaScript on the page and returns its JSON value.
    def script_evaluate(self, text: str) -> object:
        result = self.client_get().method_call(
            "Runtime.evaluate",
            {
                "expression": text,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        if "exceptionDetails" in result:
            raise RuntimeError(
                f"the page threw {exception_text(result['exceptionDetails'])}"
            )
        value: dict[str, Any] = result["result"]
        if "unserializableValue" in value:
            raise RuntimeError(
                f"the page returned {value['unserializableValue']}, which"
                " JSON can't hold"
            )
        return value.get("value")

    # Attaches to the browser's page and sets up its events and viewport.
    def target_attach(self) -> None:
        client = self.client_get()
        targets = client.method_call("Target.getTargets")["targetInfos"]
        pages = [target for target in targets if target["type"] == "page"]
        if pages:
            self.target_id = pages[0]["targetId"]
        else:
            self.target_id = client.method_call(
                "Target.createTarget", {"url": "about:blank"}
            )["targetId"]
        client.session_id = client.method_call(
            "Target.attachToTarget",
            {"targetId": self.target_id, "flatten": True},
        )["sessionId"]
        client.method_call("Page.enable")
        client.method_call("Page.setLifecycleEventsEnabled", {"enabled": True})
        client.method_call("Runtime.enable")
        client.method_call(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": self.width_px,
                "height": self.height_px,
                "deviceScaleFactor": 1,
                "mobile": False,
            },
        )

    # Ends the trace and returns its events once DevTools has sent them all.
    def trace_end(self) -> list[dict[str, Any]]:
        client = self.client_get()
        client.method_call("Tracing.end")
        client.events_pump(
            "the trace to complete", lambda: self.events.trace_done
        )
        return self.events.trace_take()

    # Starts a trace of the categories on the page, its events sent as events.
    def trace_start(self, categories: list[str]) -> None:
        self.events.trace = []
        self.events.trace_done = False
        self.events.trace_lost = False
        self.client_get().method_call(
            "Tracing.start",
            {
                "transferMode": "ReportEvents",
                "traceConfig": {"includedCategories": categories},
            },
        )

    # Pauses the page's worker of that name in its debugger, waiting for it.
    def worker_pause(self, name: str) -> None:
        client = self.client_get()
        client.session_call(
            client.session_id,
            "Target.setAutoAttach",
            {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,
                "flatten": True,
            },
        )
        client.events_pump(
            f"the worker {name} to attach",
            lambda: name in self.events.workers,
        )
        session_id = self.events.workers[name]
        client.session_call(session_id, "Debugger.enable")
        client.session_call(session_id, "Debugger.pause")
        client.events_pump(
            f"the worker {name} to pause",
            lambda: session_id in self.events.paused,
        )


# Returns the accept value DevTools must answer the WebSocket key with.
def accept_key(key: str) -> str:
    digest = hashlib.sha1((key + _WEBSOCKET_GUID).encode()).digest()
    return base64.b64encode(digest).decode()


# Parses the port file's text, a port and a path, into an address.
def address_parse(text: str) -> EndpointAddress:
    fields = text.split()
    if len(fields) != 2:
        raise ValueError(
            f"{_DEVTOOLS_PORT_FILE_NAME} holds {text!r}, not a port and a path"
        )
    return EndpointAddress(int(fields[0]), fields[1])


# Returns the trace categories that hold what `blocking_find` looks for.
def blocking_categories() -> list[str]:
    return list(_BLOCKING_CATEGORIES)


# Returns the trace's synchronous loads on the main thread of a renderer.
def blocking_find(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    threads = {
        (event["pid"], event["tid"])
        for event in events
        if event["name"] == "thread_name"
        and event["args"]["name"] == _UI_THREAD_NAME
    }
    if not threads:
        raise RuntimeError(f"the trace names no {_UI_THREAD_NAME} thread")
    return [
        event
        for event in events
        if event["name"] in _BLOCKING_EVENT_NAMES
        and (event["pid"], event["tid"]) in threads
    ]


# Returns exactly count bytes from the reader, failing if it runs dry first.
def bytes_exact(read: Callable[[int], bytes], count: int) -> bytes:
    data = bytearray()
    while len(data) < count:
        chunk = read(count - len(data))
        if chunk == b"":
            raise ConnectionError("DevTools closed the connection")
        data += chunk
    return bytes(data)


# Returns the one browser the pattern matches, failing on any other count.
def chrome_match(pattern: str) -> str:
    paths = glob.glob(pattern)
    if len(paths) != 1:
        raise FileNotFoundError(
            f"{len(paths)} browsers match {pattern}, not 1"
        )
    return paths[0]


# Returns the Linux browser's path, Anthropic's by its switch.
def chrome_path() -> str:
    if switches.anthropic:
        return chrome_match(_ANTHROPIC_CHROME_PATTERN)
    return chrome_match(_CHROME_PATTERN)


# Runs a command to its end, for at most the seconds, returning its stdout.
def command_run(
    what: str, arguments: list[str], cwd: str | None, seconds: float
) -> str:
    try:
        completed = subprocess.run(
            arguments,
            check=False,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise TimeoutError(
            f"gave up after {seconds:g} s waiting for {what}"
        ) from error
    if completed.returncode != 0:
        raise RuntimeError(
            f"{what} exited with {completed.returncode}: "
            + completed.stderr.decode("utf-8", "replace").strip()
        )
    return completed.stdout.decode("utf-8")


# Returns a console message's text: each argument's value or description.
def console_text(args: list[dict[str, Any]]) -> str:
    texts: list[str] = []
    for arg in args:
        if "value" in arg:
            value = arg["value"]
            if isinstance(value, str):
                texts.append(value)
            else:
                texts.append(json.dumps(value, ensure_ascii=False))
        elif "unserializableValue" in arg:
            texts.append(arg["unserializableValue"])
        elif "description" in arg:
            texts.append(arg["description"])
        else:
            texts.append(arg["type"])
    return " ".join(texts)


# Moves the descriptor above 4, so that its copy onto 3 or 4 clobbers neither.
def descriptor_raise(fd: int) -> int:
    raised = fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, _DESCRIPTOR_FLOOR)
    os.close(fd)
    return raised


# Returns a thrown exception's text with its stack, from DevTools' details.
def exception_text(details: dict[str, Any]) -> str:
    thrown: dict[str, Any] = details.get("exception", {})
    # An Error's description is its message and its stack.
    if "description" in thrown:
        return thrown["description"]
    head: str = details["text"]
    if "value" in thrown:
        head += " " + json.dumps(thrown["value"], ensure_ascii=False)
    lines = [head]
    frames: list[dict[str, Any]] = details.get("stackTrace", {}).get(
        "callFrames", []
    )
    for frame in frames:
        name = frame["functionName"] or "<anonymous>"
        line = frame["lineNumber"] + 1
        column = frame["columnNumber"] + 1
        lines.append(f"    at {name} ({frame['url']}:{line}:{column})")
    return "\n".join(lines)


# Reads one frame: its flags, its opcode and its payload, unmasked if masked.
def frame_decode(read: Callable[[int], bytes]) -> SocketFrame:
    first, second = bytes_exact(read, 2)
    length = second & 0x7F
    if length == 126:
        length = int.from_bytes(bytes_exact(read, 2), "big")
    elif length == 127:
        length = int.from_bytes(bytes_exact(read, 8), "big")
    mask = bytes_exact(read, 4) if second & 0x80 else b""
    payload = bytes_exact(read, length)
    if mask:
        payload = bytes(
            byte ^ mask[index % 4] for index, byte in enumerate(payload)
        )
    return SocketFrame(bool(first & 0x80), first & 0x0F, payload)


# Returns one whole frame for the payload, masked with the 4 byte mask.
def frame_encode(opcode: int, payload: bytes, mask: bytes) -> bytes:
    head = bytearray([0x80 | opcode])
    if len(payload) < 126:
        head.append(0x80 | len(payload))
    elif len(payload) < 1 << 16:
        head.append(0x80 | 126)
        head += len(payload).to_bytes(2, "big")
    else:
        head.append(0x80 | 127)
        head += len(payload).to_bytes(8, "big")
    head += mask
    masked = bytes(
        byte ^ mask[index % 4] for index, byte in enumerate(payload)
    )
    return bytes(head) + masked


# Returns once no process of the group `pid` leads is left, zombies included.
def group_wait(pid: int) -> None:
    timer = WaitTimer(
        f"{_CHROME_NAME}'s processes to exit", _STOP_WAIT_SECONDS
    )
    while True:
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(min(_GROUP_POLL_SECONDS, timer.seconds_left()))


# Fails unless the head answers the upgrade with the accept value of the key.
def handshake_check(key: str, head: bytes) -> None:
    lines = head.decode("latin-1").strip().split("\r\n")
    status = lines[0]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()
    if not status.startswith("HTTP/1.1 101 "):
        raise ConnectionError(f"DevTools answered {status or 'nothing'}")
    if headers.get("sec-websocket-accept") != accept_key(key):
        raise ConnectionError("DevTools answered a WebSocket key wrongly")


# Returns the WebSocket upgrade request for the host, path and key.
def handshake_request(host: str, path: str, key: str) -> bytes:
    return (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    ).encode()


# Reads the answer's status line and headers, up to the blank line after them.
def head_read(read: Callable[[int], bytes]) -> bytes:
    head = bytearray()
    while not head.endswith(b"\r\n\r\n"):
        head += bytes_exact(read, 1)
    return bytes(head)


# Returns the next message, joining fragments and answering pings on the way.
def message_read(
    read: Callable[[int], bytes], send: Callable[[int, bytes], None]
) -> bytes:
    message = bytearray()
    started = False
    while True:
        frame = frame_decode(read)
        if frame.opcode == _WEBSOCKET_OPCODE_CLOSE:
            raise ConnectionError("DevTools closed the connection")
        if frame.opcode == _WEBSOCKET_OPCODE_PING:
            send(_WEBSOCKET_OPCODE_PONG, frame.payload)
            continue
        if frame.opcode == _WEBSOCKET_OPCODE_PONG:
            continue
        due = (
            _WEBSOCKET_OPCODE_CONTINUATION
            if started
            else _WEBSOCKET_OPCODE_TEXT
        )
        if frame.opcode != due:
            raise ConnectionError(
                f"DevTools sent WebSocket opcode {frame.opcode} where {due}"
                " was due"
            )
        message += frame.payload
        started = True
        if frame.final:
            return bytes(message)


# Reads up to count bytes from the descriptor, failing when the timer ends.
def pipe_read(fd: int, timer: WaitTimer, count: int) -> bytes:
    while True:
        ready = select.select([fd], [], [], timer.seconds_left())[0]
        if ready:
            return os.read(fd, count)


# Returns the arguments that run the script in PowerShell, base64 encoded.
def powershell_command(powershell: str, script: str) -> list[str]:
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    return [
        powershell,
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
        encoded,
    ]


# Returns the relay's script, set to connect to the DevTools port.
def relay_script(port: int) -> str:
    return f"$port_ = {port}\n" + _RELAY_SCRIPT


# Writes the bytes to the stream and flushes them through.
def stream_write(stream: IO[bytes], data: bytes) -> None:
    stream.write(data)
    stream.flush()
