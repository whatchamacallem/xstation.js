# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The TAP suite server, a main loop file that runs the Python test suites on
# the engine tty and reports them over it, in place of the stock main loop.
# bootstrap.py runs it from the root's main_loop directory when --main-loop
# names it in debug mode, and writes the first line, `tap.start`, and reads
# its reply as for any main loop. loop_prepare reads the settings for the
# decoder's limits and the name form. loop_run decodes each line, refuses
# any reply and serves the one type `tap.run`: its handler runs the driver,
# test_all.py, as `python3 test_all.py --stream`, with the category, with
# --failfast when asked, and with --module for each suite named, its input
# empty. Each line of the driver's stdout, a line of its TAP stream, is
# pushed the moment it ends as a `tap.line` of the language python, in the
# name form of the setting `debug`; what it writes to stderr is kept, and
# when it exits the reply carries its exit code and that text. Its stdout
# ending inside a line is a fault. A line of no other type has a handler, a
# blob is refused, and a failure writes one `error` line and exits 1, as the
# stock main loop does. The hangup that ends the connection ends the loop,
# and a driver still running with it, as both are in the tty's foreground
# group.

import dispatch, functools, jslb, os, select, settings, subprocess, sys
import test_all
from internationalization import i18n
from typing import Any, NoReturn, cast

# The settings file in the root.
_SETTINGS_NAME = "settings.json"

# The one line type this main loop serves.
_RUN_TYPE = "tap.run"

# The version of the `tap.run` line.
_RUN_VERSION = 0

# The type of the push that carries each line of the stream.
_LINE_TYPE = "tap.line"

# The language of the stream the driver writes.
_LANGUAGE = "python"

# The driver's option that runs the stream alone.
_STREAM_OPTION = "--stream"

# The driver's option that ends the stream at the first failure.
_FAILFAST_OPTION = "--failfast"

# The driver's option that names one suite to run.
_MODULE_OPTION = "--module"

# The byte that ends each line of the driver's stdout.
_NEWLINE = b"\n"

# A size chosen by its writer: the most read from one of the driver's pipes.
_PIPE_BYTES = 65536

# The exit code of a failure.
_EXIT_FAILED = 1


# The state of the module: the settings `loop_prepare` read, none before.
class _SuiteState:
    # Starts with no settings read.
    def __init__(self) -> None:
        self.values: dict[str, Any] | None = None


# The one state of the module.
_STATE = _SuiteState()


# Reads the settings. Opens no database.
def loop_prepare(root: str) -> None:
    _STATE.values = settings.settings_load(os.path.join(root, _SETTINGS_NAME))


# Refuses a blob large enough to stream, as no line here carries one.
def _sink_refuse(header: jslb.Object) -> NoReturn:
    size = jslb.field_get(header, "size")
    raise jslb.WireError(i18n("tap_loop.blob_refused", size))


# Writes all the bytes to the descriptor, looping on partial writes.
def _bytes_write(data: bytes, write_fd: int) -> None:
    view = memoryview(data)
    while view:
        written = os.write(write_fd, view)
        view = view[written:]


# Writes a line that carries no blob, its JSON text the one piece.
def _line_write(line: jslb.Object, write_fd: int) -> None:
    (piece,) = jslb.line_encode(line)
    _bytes_write(cast(bytes, piece), write_fd)


# Pushes one line of the stream as a `tap.line` of the language python.
def _push_write(text: str, write_fd: int, full: bool) -> None:
    header = jslb.header_make(_LINE_TYPE, full=full)
    line = jslb.line_make(header, [], language=_LANGUAGE, text=text)
    _line_write(line, write_fd)


# The driver's command line: the stream alone, of the suites named.
def _command_make(
    category: str, failfast: bool, modules: list[str]
) -> list[str]:
    command = [sys.executable, test_all.__file__, _STREAM_OPTION]
    command.append("--" + category)
    if failfast:
        command.append(_FAILFAST_OPTION)
    for name in modules:
        command += [_MODULE_OPTION, name]
    return command


# `tap.run`: runs the driver, pushing each line of its stdout as it ends.
def suites_run(
    write_fd: int,
    full: bool,
    line: jslb.Object,
    *,
    category: str,
    failfast: bool,
    modules: list[str],
) -> jslb.Object:
    command = _command_make(category, failfast, modules)
    pending = b""
    errors = b""
    with subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as child:
        output = cast(Any, child.stdout).fileno()
        error = cast(Any, child.stderr).fileno()
        open_fds = [output, error]
        while open_fds:
            readable, _, _ = select.select(open_fds, [], [])
            for descriptor in readable:
                data = os.read(descriptor, _PIPE_BYTES)
                if not data:
                    open_fds.remove(descriptor)
                elif descriptor == error:
                    errors += data
                else:
                    *texts, pending = (pending + data).split(_NEWLINE)
                    for text in texts:
                        _push_write(text.decode("utf-8"), write_fd, full)
        code = child.wait()
    if pending:
        raise ValueError(i18n("tap_loop.output_partial", pending))
    return dispatch.reply_make(line, code=code, stderr=errors.decode("utf-8"))


# Writes the one `error` line of a failure, full names if `full`, exits 1.
def _failure_exit(
    line: jslb.Object | None, error: Exception, write_fd: int, full: bool
) -> NoReturn:
    _line_write(dispatch.error_make(line, error, full), write_fd)
    raise SystemExit(_EXIT_FAILED) from error


# Serves the lines one read finished, then feeds nothing to raise a fault.
def _bytes_serve(
    decoder: jslb.LineDecoder, data: bytes, write_fd: int, full: bool
) -> None:
    line: jslb.Object | None = None
    try:
        if not data and not decoder.idle():
            raise jslb.WireError(i18n("tap_loop.input_partial"))
        for piece in (data, b""):
            for line in decoder.bytes_feed(piece):
                if jslb.field_get(line[0], "reply") is not None:
                    rendered = jslb.line_render(line)
                    raise LookupError(i18n("tap_loop.reply_unknown", rendered))
                reply = dispatch.line_dispatch(line)
                if reply is not None:
                    _line_write(cast(jslb.Object, reply), write_fd)
            line = None
    except Exception as error:
        _failure_exit(line, error, write_fd, full)


# The select loop: reads the pty, decodes, runs each `tap.run` in turn.
def loop_run(read_fd: int, write_fd: int, root: str) -> None:
    values = cast(dict[str, Any], _STATE.values)
    full: bool = values["debug"]
    run = functools.partial(suites_run, write_fd, full)
    dispatch.handler_register(_RUN_TYPE, _RUN_VERSION, run)
    decoder = jslb.LineDecoder(
        values["line_max"],
        values["blob_max"],
        values["overflow_bytes"],
        _sink_refuse,
    )
    chunk: int = values["chunk_bytes"]
    while True:
        select.select([read_fd], [], [])
        data = os.read(read_fd, chunk)
        _bytes_serve(decoder, data, write_fd, full)
        if not data:
            return
