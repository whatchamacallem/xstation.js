# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# A main loop file with no database and no seq, the echo root of the wire
# test and of the browser test. bootstrap.py runs it from the root's
# main_loop directory when --main-loop names it in debug mode, or when
# system.restart names it after source.put stored it there, and writes the
# first line, `tap.start`. loop_prepare reads the settings for the decoder's
# limits and makes the cache directory. loop_run decodes each line and
# refuses any reply. The browser's `error` line, its failure, goes to
# `engine_tap.error_take`, then the loop exits 1 with nothing written back:
# the browser waits for the server to end, which ttyd's close of the socket
# gives it. A `tap.line` is appended through `engine_tap`; the page's
# `verbose.put` and `verbose.tail` are served through `engine_verbose`, as
# the stock main loop serves them, since the page sends its threads' lines
# in debug mode; and an `echo` is answered with the payload of its request
# and the bytes of each of its blobs, a blob over overflow_bytes going
# through a file in the root's cache directory both ways. A failure of its
# own writes one error line and exits 1, as the stock main loop does.

import dispatch, engine_tap, engine_verbose, functools, jslb, os, select
import settings, uuid
from internationalization import i18n
from typing import Any, NoReturn, cast

# The settings file in the root.
_SETTINGS_NAME = "settings.json"

# The directory in the root that holds the blobs over `overflow_bytes`.
_CACHE_DIRECTORY = "cache"

# The one line type this main loop serves.
_ECHO_TYPE = "echo"

# The version of the `echo` line.
_ECHO_VERSION = 0

# The type of the line that carries the browser's failure.
_ERROR_TYPE = "error"

# The exit code of a failure.
_EXIT_FAILED = 1


# The state of the module: the settings `loop_prepare` read, none before.
class _EchoState:
    # Starts with no settings read.
    def __init__(self) -> None:
        self.values: dict[str, Any] | None = None


# The one state of the module.
_STATE = _EchoState()


# Reads the settings and makes the cache directory. Opens no database.
def loop_prepare(root: str) -> None:
    _STATE.values = settings.settings_load(os.path.join(root, _SETTINGS_NAME))
    os.makedirs(os.path.join(root, _CACHE_DIRECTORY), exist_ok=True)


# Replies with the payload of the request and the bytes of each of its blobs.
def echo_reply(line: jslb.Object, **payload: Any) -> jslb.Object:
    blobs = [
        jslb.blob_make(jslb.field_get(cast(jslb.Object, header), "data"))
        for header in jslb.headers_of(line)[1:]
    ]
    return dispatch.reply_make(line, blobs, **payload)


# Names a new file in the cache for a blob the decoder streams.
def _sink_make(cache: str, header: jslb.Object) -> str:
    return os.path.join(cache, uuid.uuid4().hex)


# Writes all the bytes to the descriptor, looping on partial writes.
def _bytes_write(data: bytes, write_fd: int) -> None:
    view = memoryview(data)
    while view:
        written = os.write(write_fd, view)
        view = view[written:]


# Writes a line's pieces in order: bytes as they are, a file copied in chunks.
def _line_write(line: jslb.Object, write_fd: int, chunk: int) -> None:
    for piece in jslb.line_encode(line):
        if isinstance(piece, bytes):
            _bytes_write(piece, write_fd)
        else:
            with open(piece, "rb") as file:
                while data := file.read(chunk):
                    _bytes_write(data, write_fd)


# Writes the one `error` line of a failure, full names if `full`, exits 1.
def _failure_exit(
    line: jslb.Object | None,
    error: Exception,
    write_fd: int,
    chunk: int,
    full: bool,
) -> NoReturn:
    _line_write(dispatch.error_make(line, error, full), write_fd, chunk)
    raise SystemExit(_EXIT_FAILED) from error


# Serves the lines one read finished, then feeds nothing to raise a fault.
def _bytes_serve(
    decoder: jslb.LineDecoder,
    data: bytes,
    write_fd: int,
    chunk: int,
    full: bool,
) -> None:
    line: jslb.Object | None = None
    try:
        if not data and not decoder.idle():
            raise jslb.WireError(i18n("echo_loop.input_partial"))
        for piece in (data, b""):
            for line in decoder.bytes_feed(piece):
                if jslb.field_get(line[0], "reply") is not None:
                    rendered = jslb.line_render(line)
                    raise LookupError(
                        i18n("echo_loop.reply_unknown", rendered)
                    )
                if jslb.field_get(line[0], "type") == _ERROR_TYPE:
                    # The browser failed: logged, the TAP file ended, exit 1.
                    payload = jslb.payload_of(line)
                    engine_tap.error_take(
                        payload["message"],
                        payload["stack"],
                        payload.get("cause"),
                    )
                    raise SystemExit(_EXIT_FAILED)
                reply = dispatch.line_dispatch(line)
                if reply is not None:
                    _line_write(cast(jslb.Object, reply), write_fd, chunk)
            line = None
    except Exception as error:
        _failure_exit(line, error, write_fd, chunk, full)


# The select loop: reads the pty, decodes, writes the echo of each request.
def loop_run(read_fd: int, write_fd: int, root: str) -> None:
    values = cast(dict[str, Any], _STATE.values)
    dispatch.handler_register(_ECHO_TYPE, _ECHO_VERSION, echo_reply)
    engine_tap.handlers_register(root)
    engine_verbose.handlers_register(values["debug"])
    decoder = jslb.LineDecoder(
        values["line_max"],
        values["blob_max"],
        values["overflow_bytes"],
        functools.partial(_sink_make, os.path.join(root, _CACHE_DIRECTORY)),
    )
    chunk: int = values["chunk_bytes"]
    full: bool = values["debug"]
    while True:
        select.select([read_fd], [], [])
        data = os.read(read_fd, chunk)
        _bytes_serve(decoder, data, write_fd, chunk, full)
        if not data:
            return
