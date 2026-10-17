from jslb import Object

# Handlers of the `console.*` lines on the wire, debug mode only. Output
# is pushed as `console.output` with one blob, and `console.exit` with
# the code, from the main loop's select on the console's fd.

# `console.open`: forks dash; reply with `pid`. A second open while one
# runs raises.
def console_open(line: Object, *, columns: int, rows: int) -> Object: ...

# `console.input`: one blob written to the pty; no reply.
def console_input(line: Object) -> None: ...

# `console.signal`: sends the signal to the group; no reply.
def console_signal(line: Object, *, signal: int) -> None: ...

# `console.close`: ends dash; reply with `code`.
def console_close(line: Object) -> Object: ...
