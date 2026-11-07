# The server's main loop, which `bootstrap.py` loads and a main loop file can
# replace in debug mode. `loop_prepare` runs before the first line: it loads
# the settings, opens every database under the root, creating missing fixed
# ones, seeds the scripted provider's script when `_files` lacks it, and seeds
# the metaverse when it lacks the `universe` table: the DDL and triggers of
# API/sql/metaverse.sql, the row of the image `seed/hyperposition.bmp`, then
# the documents. `loop_run` registers the stock handlers and runs the select
# loop on the pty: it decodes and serves each line, refusing any reply, as the
# server awaits none. A browser `error` line goes to `engine_tap.error_take`,
# then the loop exits 1 and writes nothing: its exit ends the connection, the
# close the page waits for. A `dispatch.Failure` writes its reply, then fails
# with its error, whose `error` line has no `r`, as its request is answered.
# A `dispatch.Stream` writes its pushes in order, then its reply. A failure
# logs its message, writes one `error` line with its cascade, in the name form
# of the line it answers, else of the parameter `debug`, and exits 1. In debug
# mode `jslb.line_render` logs each line dispatched, push, reply and `error`,
# never its blob bytes, as `main_loop.line_dispatch`, `line_push`, `line_reply`
# and `line_error`. An entry past one `verbose.put` of thread `server` below
# `line_max` is logged by their `_sized` strings: its header, payload size and
# blob sizes, as a `verbose.put` dispatched is.

# Prepares the root once, before the first line.
def loop_prepare(root: str) -> None: ...

# The select loop: reads the pty, decodes, dispatches, writes each answer.
def loop_run(read_fd: int, write_fd: int, root: str) -> None: ...
