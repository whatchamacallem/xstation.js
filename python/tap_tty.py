# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The page's end of the engine tty, with no browser and no ttyd. EngineTty
# runs python3 python/bootstrap.py --root ROOT, with any arguments after, on
# a new pty of the standard library's pty module, the pty its controlling
# tty and its stdin, stdout and stderr, as ttyd runs it. It plays the page
# on the other side: it reads the JSLB lines the engine writes by the
# decoder of jslb.py, writes the lines or bytes it is given, and hangs up by
# closing its side, as ttyd's close does, which ends the engine with SIGHUP,
# and returns the engine's exit code. suites_relay runs Python test suites
# over the tty: it makes a debug root from the checkout's settings and gold
# with the TAP suite server, tap_loop.py, in its main_loop directory, runs
# the engine there with --main-loop tap_loop.py, answers tap.start, sends
# one tap.run and hands the text of each tap.line of the language python
# the server pushes to its writer as it comes. It returns the exit code and
# the stderr text the reply carries, after hanging up. Anything else the
# engine writes fails the relay, naming it. Its texts are plain English, as
# the infrastructure for testing's are.

import errno, harness, jslb, json, os, pty, shutil, signal, sys, traceback
import types
from collections.abc import Callable
from typing import Any, NoReturn, Self

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The program the engine runs, beside this file.
_BOOTSTRAP_PATH = os.path.join(_PYTHON_PATH, "bootstrap.py")

# The option of `bootstrap.py` that names the root.
_ROOT_OPTION = "--root"

# The option of `bootstrap.py` that names a main loop file in the root.
_LOOP_OPTION = "--main-loop"

# The directory of a root that holds the main loop files.
_LOOP_DIRECTORY = "main_loop"

# The TAP suite server's main loop file, beside this file.
_LOOP_NAME = "tap_loop.py"

# The settings file of a root.
_SETTINGS_NAME = "settings.json"

# The test settings file of a root, which a debug root needs.
_TESTS_NAME = "test_settings.json"

# The type of the engine's first line and of the page's reply to it.
_FIRST_TYPE = "tap.start"

# The fixed id of the engine's first line.
_FIRST_ID = 101

# The type of the request that runs the suites.
_RUN_TYPE = "tap.run"

# The id of the page's `tap.run`, the first a port counts after 101.
_RUN_ID = 102

# The type of the push that carries each line of the stream.
_LINE_TYPE = "tap.line"

# The language of the Python stream.
_LANGUAGE = "python"

# The exit code of a forked child that could not exec the engine.
_EXEC_FAILED = 127


# In the forked child: execs the engine, or prints why not and exits 127.
def _engine_exec(argv: list[str]) -> NoReturn:
    try:
        os.execv(argv[0], argv)
    except BaseException:
        traceback.print_exc()
    os._exit(_EXEC_FAILED)


# `bootstrap.py` run whole on a new pty, and the page's end of its lines.
class EngineTty:
    # Runs the engine on the root, reading lines by the settings' limits.
    def __init__(
        self,
        root: str,
        arguments: list[str],
        values: dict[str, Any],
        sink_make: Callable[[jslb.Object], str],
    ) -> None:
        self._decoder = jslb.LineDecoder(
            values["line_max"],
            values["blob_max"],
            values["overflow_bytes"],
            sink_make,
        )
        self._read_bytes: int = values["chunk_bytes"]
        self._lines: list[jslb.Object] = []
        argv = [sys.executable, _BOOTSTRAP_PATH, _ROOT_OPTION, root]
        argv += arguments
        pid, descriptor = pty.fork()
        if pid == 0:
            _engine_exec(argv)
        self.pid = pid
        self._descriptor: int | None = descriptor

    # Returns the engine run, to be hung up when the block ends.
    def __enter__(self) -> Self:
        return self

    # Hangs up unless that was done already.
    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: types.TracebackType | None,
    ) -> None:
        if self._descriptor is not None:
            self.hangup()

    # Returns this side of the pty, raising once it is hung up.
    def _descriptor_get(self) -> int:
        if self._descriptor is None:
            raise RuntimeError(f"the engine {self.pid} is hung up")
        return self._descriptor

    # Reads what the engine wrote, empty once every writer is gone.
    def _bytes_read(self) -> bytes:
        try:
            return os.read(self._descriptor_get(), self._read_bytes)
        except OSError as error:
            # Linux reads EIO from a pty whose other side no process holds.
            if error.errno != errno.EIO:
                raise
            return b""

    # The next line the engine wrote. Raises `EOFError` at the end of them.
    def line_read(self) -> jslb.Object:
        while not self._lines:
            data = self._bytes_read()
            if not data:
                if not self._decoder.idle():
                    raise EOFError(f"the engine {self.pid} ended in a line")
                raise EOFError(f"the engine {self.pid} wrote no more lines")
            for piece in (data, b""):
                self._lines += self._decoder.bytes_feed(piece)
        return self._lines.pop(0)

    # Writes all the bytes to the engine as they are.
    def bytes_write(self, data: bytes) -> None:
        view = memoryview(data)
        while view:
            written = os.write(self._descriptor_get(), view)
            view = view[written:]

    # Writes a line, a blob held as a file copied a read at a time.
    def line_write(self, line: jslb.Object) -> None:
        for piece in jslb.line_encode(line):
            if isinstance(piece, bytes):
                self.bytes_write(piece)
                continue
            with open(piece, "rb") as file:
                while data := file.read(self._read_bytes):
                    self.bytes_write(data)

    # Closes this side, the hangup, and returns the engine's exit code.
    def hangup(self) -> int:
        os.close(self._descriptor_get())
        self._descriptor = None
        _, status = os.waitpid(self.pid, 0)
        return os.waitstatus_to_exitcode(status)


# Refuses a blob, as the TAP suite server sends none.
def _sink_refuse(header: jslb.Object) -> NoReturn:
    size = jslb.field_get(header, "size")
    raise RuntimeError(f"the TAP suite server sent a blob of {size} bytes")


# Writes a value as the JSON text of a file of the root.
def _json_write(root: str, name: str, value: object) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with open(os.path.join(root, name), "w", encoding="utf-8") as file:
        file.write(text)


# Makes a debug root that serves the TAP suite server and returns its settings.
def _root_make(root: str) -> dict[str, Any]:
    values = harness.settings_copy()
    values["debug"] = True
    directory = os.path.join(root, _LOOP_DIRECTORY)
    os.makedirs(directory)
    _json_write(root, _SETTINGS_NAME, values)
    _json_write(root, _TESTS_NAME, harness.gold_copy())
    shutil.copyfile(
        os.path.join(_PYTHON_PATH, _LOOP_NAME),
        os.path.join(directory, _LOOP_NAME),
    )
    return values


# Fails the relay on a line it does not expect, naming the line.
def _line_refuse(line: jslb.Object, expected: str) -> NoReturn:
    rendered = jslb.line_render(line)
    raise RuntimeError(
        f"the TAP suite server wrote {rendered}, not {expected}"
    )


# Runs the named suites of the category over the tty, each line to `write`.
def suites_relay(
    root: str,
    category: str,
    failfast: bool,
    modules: list[str],
    write: Callable[[str], None],
) -> tuple[int, str]:
    values = _root_make(root)
    arguments = [_LOOP_OPTION, _LOOP_NAME]
    with EngineTty(root, arguments, values, _sink_refuse) as engine:
        first = engine.line_read()
        header: jslb.Object = first[0]
        if (
            jslb.field_get(header, "type") != _FIRST_TYPE
            or jslb.field_get(header, "id") != _FIRST_ID
        ):
            _line_refuse(first, f"{_FIRST_TYPE} {_FIRST_ID}")
        reply = jslb.header_make(_FIRST_TYPE, reply=_FIRST_ID, full=True)
        engine.line_write(jslb.line_make(reply, []))
        request = jslb.header_make(_RUN_TYPE, id=_RUN_ID, full=True)
        engine.line_write(
            jslb.line_make(
                request,
                [],
                category=category,
                failfast=failfast,
                modules=modules,
            )
        )
        while True:
            line = engine.line_read()
            header = line[0]
            name = jslb.field_get(header, "type")
            payload = jslb.payload_of(line)
            if (
                name == _LINE_TYPE
                and jslb.field_get(header, "id") is None
                and jslb.field_get(header, "reply") is None
                and payload.get("language") == _LANGUAGE
            ):
                write(payload["text"])
            elif (
                name == _RUN_TYPE
                and jslb.field_get(header, "reply") == _RUN_ID
            ):
                break
            else:
                _line_refuse(line, f"{_LINE_TYPE} or the reply to {_RUN_ID}")
        code = engine.hangup()
    if code != -signal.SIGHUP:
        raise RuntimeError(f"the TAP suite server exited with {code}")
    return payload["code"], payload["stderr"]
