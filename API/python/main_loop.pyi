# The server's main loop, which `bootstrap.py` loads and a main loop file can
# replace in debug mode. `loop_prepare` runs before the first line: it loads
# the settings, opens every database under the root, creating the fixed ones
# that are missing, seeds the scripted provider's script when `_files` lacks
# it, and seeds the metaverse when it lacks the `universe` table, with the
# DDL and the triggers of API/sql/metaverse.sql. `loop_run` registers the
# stock handlers and runs the select loop on the pty: it decodes each line,
# refuses any reply, since the server awaits none, and serves the rest. An
# `error` line of the browser goes to `engine_tap.error_take`, after which
# the loop exits 1 and writes nothing: its exit ends the connection, the
# close the page waits for. A `dispatch.Failure` writes its reply, then fails
# with its error, whose `error` line has no `r`, as its request is answered.
# A `dispatch.Stream` writes its pushes in order, then its reply. A failure
# logs its message, writes one `error` line with its cascade, in the name form
# of the line it answers, else of the parameter `debug`, and exits 1. In debug
# mode each line dispatched, push, reply and `error` is logged by
# `jslb.line_render`, never its blob bytes, as `main_loop.line_dispatch`,
# `line_push`, `line_reply` and `line_error`. An entry past one `verbose.put`
# of thread `server` below `line_max` is logged by their `_sized` strings:
# its header, payload size and blob sizes, as a `verbose.put` dispatched is.

# Prepares the root once, before the first line.
def loop_prepare(root: str) -> None: ...

# The select loop: reads the pty, decodes, dispatches, writes each answer.
def loop_run(read_fd: int, write_fd: int, root: str) -> None: ...
