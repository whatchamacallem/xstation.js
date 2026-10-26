# The page's end of the engine tty, with no browser and no ttyd. `EngineTty`
# runs `python3 python/bootstrap.py --root ROOT`, with any arguments after,
# on a new pty of the standard library's `pty` module, the pty its
# controlling tty and its stdin, stdout and stderr, as ttyd runs it, and
# plays the page: it reads the engine's JSLB lines, writes lines or bytes,
# and hangs up by closing its side, which ends the engine with SIGHUP.
# `suites_relay` runs Python test suites over the tty on the TAP suite
# server, `tap_loop.py`, in a debug root it makes from the checkout's
# settings and gold: it answers `tap.start`, sends one `tap.run`, and hands
# the text of each `tap.line` of the language python to its writer as it
# comes. Its texts are plain English.

import jslb, types
from collections.abc import Callable
from typing import Any, Self

# `bootstrap.py` run whole on a new pty, and the page's end of its lines.
class EngineTty:
    pid: int
    # Runs the engine on the root, reading lines by the settings' limits.
    def __init__(
        self,
        root: str,
        arguments: list[str],
        values: dict[str, Any],
        sink_make: Callable[[jslb.Object], str],
    ) -> None: ...
    # Returns the engine run, to be hung up when the block ends.
    def __enter__(self) -> Self: ...
    # Hangs up unless that was done already.
    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: types.TracebackType | None,
    ) -> None: ...
    # The next line the engine wrote. Raises `EOFError` at the end of them.
    def line_read(self) -> jslb.Object: ...
    # Writes all the bytes to the engine as they are.
    def bytes_write(self, data: bytes) -> None: ...
    # Writes a line, a blob held as a file copied a read at a time.
    def line_write(self, line: jslb.Object) -> None: ...
    # Closes this side, the hangup, and returns the engine's exit code.
    def hangup(self) -> int: ...

# Makes `root`, runs the suites over the tty, each line of them to `write`.
def suites_relay(
    root: str,
    category: str,
    failfast: bool,
    modules: list[str],
    write: Callable[[str], None],
) -> tuple[int, str]: ...
