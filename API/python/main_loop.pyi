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
# close the page waits for, since the page never closes on a failure. A
# `dispatch.Failure` writes its reply, then fails with its error, whose
# `error` line has no `r`, as its request is answered. A failure logs its
# message, writes one `error` line with its cascade, in the name form of the
# line it answers, else of the setting `debug`, and exits 1.

# Prepares the root once, before the first line.
def loop_prepare(root: str) -> None: ...

# The select loop: reads the pty, decodes, dispatches, writes each reply.
def loop_run(read_fd: int, write_fd: int, root: str) -> None: ...
