# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# A main loop file that opens no database and serves one line type, `echo`,
# whose reply carries the payload of its request and the bytes of each of its
# blobs. bootstrap.py runs it from the root's main_loop directory when
# --main-loop names it in debug mode, or when system.restart names it after
# source.put stored it there. loop_prepare reads the settings for the
# decoder's limits and returns no seq, as it opens no database; loop_run
# decodes each line, dispatches it and writes its reply, a blob over
# overflow_bytes going through a file in the root's cache directory both ways.
# A failure writes one error line and exits 1, as the stock main loop does.

import dispatch, functools, jslb, os, select, settings, uuid
from i18n import i18n
from typing import Any, NoReturn, cast

# The settings file in the root.
_SETTINGS_NAME = "settings.json"

# The directory in the root that holds the blobs over `overflow_bytes`.
_CACHE_DIRECTORY = "cache"

# The one line type this main loop serves.
_ECHO_TYPE = "echo"

# The version of the `echo` line.
_ECHO_VERSION = 0

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
def loop_prepare(root: str) -> dict[str, int]:
    _STATE.values = settings.settings_load(os.path.join(root, _SETTINGS_NAME))
    os.makedirs(os.path.join(root, _CACHE_DIRECTORY), exist_ok=True)
    return {}


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


# Writes the one `error` line of a failure and exits 1.
def _failure_exit(
    line: jslb.Object | None, error: Exception, write_fd: int, chunk: int
) -> NoReturn:
    _line_write(dispatch.error_make(line, error), write_fd, chunk)
    raise SystemExit(_EXIT_FAILED) from error


# Echoes the lines one read finished, then feeds nothing to raise a fault.
def _bytes_serve(
    decoder: jslb.LineDecoder, data: bytes, write_fd: int, chunk: int
) -> None:
    line: jslb.Object | None = None
    try:
        if not data and not decoder.idle():
            raise jslb.WireError(i18n("echo_loop.input_partial"))
        for piece in (data, b""):
            for line in decoder.bytes_feed(piece):
                reply = cast(jslb.Object, dispatch.line_dispatch(line))
                _line_write(reply, write_fd, chunk)
            line = None
    except Exception as error:
        _failure_exit(line, error, write_fd, chunk)


# The select loop: reads the pty, decodes, writes the echo of each request.
def loop_run(read_fd: int, write_fd: int, root: str) -> None:
    values = cast(dict[str, Any], _STATE.values)
    dispatch.handler_register(_ECHO_TYPE, _ECHO_VERSION, echo_reply)
    decoder = jslb.LineDecoder(
        values["line_max"],
        values["blob_max"],
        values["overflow_bytes"],
        functools.partial(_sink_make, os.path.join(root, _CACHE_DIRECTORY)),
    )
    chunk: int = values["chunk_bytes"]
    while True:
        select.select([read_fd], [], [])
        data = os.read(read_fd, chunk)
        _bytes_serve(decoder, data, write_fd, chunk)
        if not data:
            return
