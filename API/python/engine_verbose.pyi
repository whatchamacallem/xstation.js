import jslb

# `verbose.put`: the page's lines into `_verbose`, debug mode only.
def verbose_put(
    line: jslb.Object, *, thread: str, lines: list[dict[str, object]]
) -> None: ...

# `verbose.tail`: reply with the last `count` lines of the server's ring.
def verbose_tail(
    line: jslb.Object, *, thread: str, count: int
) -> jslb.Object: ...

# Registers both handlers, with debug mode as the gate of `verbose.put`.
def handlers_register(debug: bool) -> None: ...
