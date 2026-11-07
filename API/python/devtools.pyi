# Headless Chrome driven over the DevTools protocol by one client, the
# Browser, on the `Transport` it is given: LinuxPipe, to chrome-headless-shell
# on its descriptors 3 and 4, or `devtools_windows.WindowsRelay`, to Chrome or
# Edge on Windows. The relay's helpers that a running suite tests stay here,
# and the relay itself is the module devtools_windows.py. The switch
# `switches.anthropic` has LinuxPipe start Playwright's headless shell of
# Anthropic's cloud container in place of chrome-headless-shell's path.

from collections.abc import Callable
from typing import Any, Protocol, Self

import types

# The page's loads as loader and event name pairs, as DevTools reported them.
class PageEvents:
    lifecycle: set[tuple[str, str]]

# DevTools messages as WebSocket text frames on a byte channel.
class SocketChannel: ...

# DevTools messages each ended by a NUL byte, on the Linux browser's pipes.
class PipeChannel: ...

# Either channel of whole DevTools messages.
AnyChannel = SocketChannel | PipeChannel

# Speaks the DevTools protocol over a channel of whole messages.
class ProtocolClient:
    # Returns the result of a DevTools method, on the page once attached.
    def method_call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...
    # Returns the result of a method on the session, the browser's when empty.
    def session_call(
        self,
        session_id: str,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    # Passes events on until the condition holds, failing when the wait ends.
    def events_pump(self, what: str, done: Callable[[], bool]) -> None: ...
    # Ends every later wait at `end`, a `time.monotonic()` value, if sooner.
    def deadline_set(self, end: float) -> None: ...
    # Ends every later wait at `end` alone, in place of the wait's own limit.
    def limit_set(self, end: float) -> None: ...

# What a Browser runs on, which starts the browser and stops it.
class Transport(Protocol):
    # Whether a refused navigation is sent again.
    refused_retried: bool
    # Starts the browser and returns the channel to its DevTools.
    def transport_open(self, width_px: int, height_px: int) -> AnyChannel: ...
    # Stops the browser and removes what it left.
    def transport_close(self) -> None: ...

# `/usr/local/bin/chrome-headless-shell` on Linux, with DevTools on fds 3, 4.
class LinuxPipe:
    # A refusal on this machine's own 127.0.0.1 is final, as nothing forwards.
    refused_retried: bool
    # Starts nothing yet: the start makes its profile and caches in `build/`.
    def __init__(self) -> None: ...
    # Starts the browser on a new profile in `build/`, DevTools on its pipes.
    def transport_open(self, width_px: int, height_px: int) -> PipeChannel: ...
    # Stops the browser, closes this side's pipe ends and removes the profile.
    def transport_close(self) -> None: ...

# Headless Chrome over DevTools, on the transport it is given.
class Browser:
    events: PageEvents
    # Keeps the window size and the transport, starting nothing yet.
    def __init__(
        self,
        width_px: int,
        height_px: int,
        transport: Transport,
    ) -> None: ...
    # Starts the browser and its page, cleaning up if that fails.
    def __enter__(self) -> Self: ...
    # Stops the browser, removes its profile, fails on an exit no call saw.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None: ...
    # Opens the URL and waits for its load, sent again if refused on the relay.
    def page_open(self, url: str) -> None: ...
    # Evaluates JavaScript on the page and returns its JSON value.
    def script_evaluate(self, text: str) -> object: ...
    # Calls `fn` with each payload the page calls `name` with, on every load.
    def binding_add(self, name: str, fn: Callable[[str], None]) -> None: ...
    # Calls `fn` with each console message from now on.
    def console_follow(self, fn: Callable[[str], None]) -> None: ...
    def screenshot_save(self, path: str) -> None: ...
    def page_close(self) -> None: ...
    # Returns the DevTools client, failing if the browser isn't started.
    def client_get(self) -> ProtocolClient: ...
    # Starts a trace of the categories on the page, its events sent as events.
    def trace_start(self, categories: list[str]) -> None: ...
    # Ends the trace and returns its events once DevTools has sent them all.
    def trace_end(self) -> list[dict[str, Any]]: ...
    # Pauses the page's worker of that name in its debugger, waiting for it.
    def worker_pause(self, name: str) -> None: ...

# Returns the trace categories that hold what `blocking_find` looks for.
def blocking_categories() -> list[str]: ...

# Returns the trace's synchronous loads on the main thread of a renderer.
def blocking_find(events: list[dict[str, Any]]) -> list[dict[str, Any]]: ...

# Returns the Linux browser's path, Anthropic's by its switch.
def chrome_path() -> str: ...
