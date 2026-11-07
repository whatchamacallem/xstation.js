# The handlers of the `verbose.put` and `verbose.tail` lines. A `verbose.tail`
# reply holds the newest lines that fit one reply below `line_max`, oldest
# first, so that its `count` is a maximum: every line of `_verbose` may be a
# full rendering, and a reply past `line_max` would fail at the page's decoder.

import jslb

# `verbose.put`: the page's lines into `_verbose`, debug mode only.
def verbose_put(
    line: jslb.Object, *, thread: str, lines: list[dict[str, object]]
) -> None: ...

# `verbose.tail`: reply with at most `count` lines of a thread, oldest first.
def verbose_tail(
    line: jslb.Object, *, thread: str, count: int
) -> jslb.Object: ...

# Registers both handlers: `debug` gates `verbose.put`, `line_max` the tail.
def handlers_register(debug: bool, line_max: int) -> None: ...
