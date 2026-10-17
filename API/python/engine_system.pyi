from typing import Any

from jslb import Object

# Handlers of the connection-level lines on the wire.

# The server's first line, its own request with `i` 1. Returns the line
# to write; `hello_reply` takes the client's answer.
def hello_make(root: str, debug: bool) -> Object: ...
def hello_reply(line: Object, *, sha256: str, tab: str, seq: dict[str, int]) -> None: ...

# `tap.report`: parses the TAP text with tappy's consumer; reply with
# `ok` and the `pass`, `fail` and `skip` counts. A stream the parser
# rejects raises.
def tap_report(line: Object, *, language: str, text: str) -> Object: ...

# `settings.put`, debug mode: checks and rewrites `settings.json` in the
# root; reply empty; takes effect at the next `hello`.
def settings_put(line: Object, *, settings: dict[str, Any]) -> Object: ...

# `source.put`, debug mode: one blob written as `<name>` into the Python
# package in the root; reply with `sha256`.
def source_put(line: Object, *, name: str) -> Object: ...

# `system.restart`, debug mode: execs `sys.orig_argv`, keeping the pid.
# The new process writes a new `hello`. Never returns.
def system_restart(line: Object) -> None: ...
