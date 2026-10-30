#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The platform services around the main loop, the command ttyd runs:
#
#     python3 python/bootstrap.py --root ROOT [console] [--main-loop NAME]
#
# With no role it is the engine: it puts its pty in raw mode, takes the
# engine.lock file of the root, reads the settings and opens the root's log,
# loads the main loop file and has it prepare the root, then writes the
# first line, tap.start with the fixed id 101, which carries the settings
# and, in debug mode, the root's test_settings.json as test_settings, read
# by jslb.json_decode, in full names in debug mode. It reads the Empty reply
# to 101 a byte at a time, then runs the main loop, whose own requests take
# their ids from dispatch.id_next, from 102. It reads no provider key and no
# provider file: no program but the test suites runs. --main-loop is served
# only to the engine role with the setting debug true, and neither option
# may be given twice. With the role console, when the setting debug is true,
# it opens the root's log and runs the console's shell, dash in the
# bubblewrap sandbox of the argv below, with a scrubbed environment through
# verbose.exec at the setting verbose_level, the shell's level, and it exits
# 1 otherwise. The sandbox binds / read only, gives dash empty /tmp, /home,
# /mnt and /root, unshares every namespace, gives it a session of its own,
# ends it with the console role and starts it in its own /tmp, so dash never
# sees the root and nothing it writes outlives it. Any exception writes one
# error line, its cascade under cause, in full names since it may come
# before the settings, and exits 1; once the log is open the exception's
# message is logged before its error line is written. In debug mode the log
# traces tap.start. The modules beside this file are imported inside the
# functions that use them, after their bytecode has been sent to build/.

import argparse, fcntl, importlib.machinery, importlib.util, json, os, sys
import termios, traceback, tty, types
from collections.abc import Callable, Iterator
from typing import Any, NamedTuple, NoReturn, cast

# The directory that holds this file and the modules it imports.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The stock main loop file, beside this file.
_MAIN_LOOP_STOCK = os.path.join(_PYTHON_PATH, "main_loop.py")

# The directory in the root that holds the files `--main-loop` names.
_MAIN_LOOP_DIRECTORY = "main_loop"

# The extension every main loop file name ends with.
_MAIN_LOOP_EXTENSION = ".py"

# The module name a main loop file is loaded under.
_MAIN_LOOP_MODULE = "main_loop"

# The functions a main loop file must define.
_LOOP_FUNCTIONS = ("loop_prepare", "loop_run")

# The option that names the root, given exactly once.
_ROOT_OPTION = "--root"

# The option that names a main loop file in the root, given at most once.
_LOOP_OPTION = "--main-loop"

# The file in the root that holds the settings.
_SETTINGS_NAME = "settings.json"

# The file in the root that holds the test settings, read in debug mode.
_TESTS_NAME = "test_settings.json"

# The file in the root whose lock one engine at a time holds.
_LOCK_NAME = "engine.lock"

# The permissions the lock file is created with: read and write by its owner.
_LOCK_MODE = 0o600

# The role that runs the console, the only role there is.
_CONSOLE_ROLE = "console"

# The console's shell: dash in the bubblewrap sandbox the maintainer gave.
_DASH_ARGV = (
    "bwrap",
    "--ro-bind",
    "/",
    "/",
    "--dev",
    "/dev",
    "--proc",
    "/proc",
    "--tmpfs",
    "/tmp",
    "--tmpfs",
    "/home",
    "--tmpfs",
    "/mnt",
    "--tmpfs",
    "/root",
    "--unshare-all",
    "--new-session",
    "--die-with-parent",
    "--chdir",
    "/tmp",
    "/bin/dash",
)

# Its verbose form, with dash's option that prints its input as it reads it.
_DASH_VERBOSE = (*_DASH_ARGV, "-v")

# The environment variables the console keeps when they are set.
_CONSOLE_VARIABLES = ("HOME", "LANG", "PATH", "TERM")

# The descriptor the engine reads its lines from, its pty.
_READ_FD = 0

# The descriptor the engine writes its lines to, the same pty.
_WRITE_FD = 1

# The type of the engine's first request and of its reply.
_FIRST_TYPE = "tap.start"

# The fixed id of the first line, before those of `dispatch.id_next`.
_FIRST_ID = 101

# The number of header fields of the reply to the first line: type, reply.
_REPLY_FIELDS = 2

# The type of the line that reports an exception.
_ERROR_TYPE = "error"

# The exit code of a run that failed or was refused.
_EXIT_FAILURE = 1

# A shell's exit code for a program a signal ended is this plus the signal.
_SIGNAL_BASE = 128

# Bytecode of the modules the functions below import goes in `build/pycache`.
sys.pycache_prefix = os.path.join(
    os.path.dirname(_PYTHON_PATH), "build", "pycache"
)


# The root, the role and the main loop file name of a run.
class _RunArguments(NamedTuple):
    root: str
    role: str | None
    main_loop: str | None


# Parses the arguments, refusing a repeated option and a console main loop.
def _arguments_parse(argv: list[str]) -> _RunArguments:
    from internationalization import i18n

    parser = argparse.ArgumentParser(
        description="The platform services around the main loop: with no"
        " role the engine on its pty, with the role console the debug"
        " console.",
        exit_on_error=False,
    )
    parser.add_argument(
        _ROOT_OPTION,
        action="append",
        required=True,
        help="the server's root directory",
    )
    parser.add_argument(
        _LOOP_OPTION,
        action="append",
        default=[],
        help="a main loop file in the root's main_loop directory, run in"
        " place of the stock main_loop.py in debug mode",
    )
    parser.add_argument(
        "role",
        nargs="?",
        choices=[_CONSOLE_ROLE],
        help="console runs dash in its sandbox in debug mode",
    )
    parsed = parser.parse_args(argv)
    roots: list[str] = parsed.root
    loops: list[str] = parsed.main_loop
    for option, values in ((_ROOT_OPTION, roots), (_LOOP_OPTION, loops)):
        if len(values) > 1:
            raise ValueError(i18n("bootstrap.option_repeated", option))
    role: str | None = parsed.role
    main_loop = loops[0] if loops else None
    if main_loop is not None and role == _CONSOLE_ROLE:
        raise PermissionError(i18n("bootstrap.main_loop_refused", main_loop))
    return _RunArguments(roots[0], role, main_loop)


# Reads and checks the settings file of the root.
def _settings_read(root: str) -> dict[str, Any]:
    import settings

    return settings.settings_load(os.path.join(root, _SETTINGS_NAME))


# Takes the engine lock of the root until exit or `exec`, which closes it.
def _lock_take(root: str) -> None:
    from internationalization import i18n

    path = os.path.join(root, _LOCK_NAME)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, _LOCK_MODE)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        os.close(descriptor)
        raise RuntimeError(i18n("bootstrap.lock_held", path)) from error


# Reads the test settings of the root by the decoders, refusing a non object.
def _tests_read(root: str) -> dict[str, Any]:
    import jslb
    from internationalization import i18n

    path = os.path.join(root, _TESTS_NAME)
    with open(path, encoding="utf-8") as file:
        data: object = jslb.json_decode(file.read())
    if not isinstance(data, dict):
        raise ValueError(i18n("bootstrap.tests_not_object", path))
    return cast(dict[str, Any], data)


# Returns the main loop file: the stock one, or in debug mode a named one.
def _loop_path(root: str, name: str | None, debug: bool) -> str:
    from internationalization import i18n

    if name is None:
        return _MAIN_LOOP_STOCK
    if not debug:
        raise PermissionError(i18n("bootstrap.main_loop_refused", name))
    if (
        os.path.basename(name) != name
        or name.startswith(".")
        or not name.endswith(_MAIN_LOOP_EXTENSION)
    ):
        raise ValueError(i18n("bootstrap.main_loop_name", name))
    return os.path.join(root, _MAIN_LOOP_DIRECTORY, name)


# Runs a main loop file from its source, never its bytecode, and checks it.
def _loop_load(path: str) -> types.ModuleType:
    from internationalization import i18n

    loader = importlib.machinery.SourceFileLoader(_MAIN_LOOP_MODULE, path)
    spec = importlib.util.spec_from_loader(_MAIN_LOOP_MODULE, loader)
    module = importlib.util.module_from_spec(
        cast(importlib.machinery.ModuleSpec, spec)
    )
    sys.modules[_MAIN_LOOP_MODULE] = module
    source = loader.get_data(path)
    exec(compile(source, path, "exec"), vars(module))
    for name in _LOOP_FUNCTIONS:
        if not callable(vars(module).get(name)):
            raise AttributeError(i18n("bootstrap.loop_missing", path, name))
    return module


# Returns the JSON text bytes, the one piece the encoder yields with no blob.
def _text_bytes(pieces: Iterator[bytes | str]) -> bytes:
    (piece,) = pieces
    return cast(bytes, piece)


# Writes all the bytes to the engine's output, with no buffer between.
def _bytes_write(data: bytes) -> None:
    view = memoryview(data)
    while len(view) > 0:
        written = os.write(_WRITE_FD, view)
        view = view[written:]


# Traces `tap.start` in debug mode, then writes it in `full` names.
def _first_write(
    loaded: dict[str, Any], tests: dict[str, Any] | None, full: bool
) -> None:
    import jslb, verbose
    from internationalization import i18n

    header = jslb.header_make(_FIRST_TYPE, id=_FIRST_ID, full=full)
    payload: dict[str, Any] = {"settings": loaded}
    if tests is not None:
        payload["test_settings"] = tests
    line = jslb.line_make(header, [], **payload)
    if loaded["debug"]:
        text = json.dumps(line[0], ensure_ascii=False, separators=(",", ":"))
        verbose.log(i18n("bootstrap.start_submit", text))
    _bytes_write(_text_bytes(jslb.line_encode(line)))


# Reads the reply to `tap.start` a byte at a time, taking no byte after it.
def _reply_read(loaded: dict[str, Any]) -> None:
    import jslb
    from internationalization import i18n

    # Refuses a blob large enough to stream, as the reply carries none.
    def sink_refuse(header: jslb.Object) -> NoReturn:
        size = jslb.field_get(header, "size")
        raise jslb.WireError(i18n("bootstrap.reply_blob", size))

    decoder = jslb.LineDecoder(
        loaded["line_max"],
        loaded["blob_max"],
        loaded["overflow_bytes"],
        sink_refuse,
    )
    lines: list[jslb.Object] = []
    while not lines:
        data = os.read(_READ_FD, 1)
        if not data:
            raise EOFError(i18n("bootstrap.reply_closed"))
        lines = decoder.bytes_feed(data)
        # Feeding nothing raises at once a fault the decoder held back.
        decoder.bytes_feed(b"")
    (line,) = lines
    header: jslb.Object = line[0]
    reply = jslb.field_get(header, "reply")
    if (
        len(header) != _REPLY_FIELDS
        or jslb.field_get(header, "type") != _FIRST_TYPE
        or type(reply) is not int
        or reply != _FIRST_ID
        or len(jslb.payload_of(line)) > 0
    ):
        rendered = jslb.line_render(line)
        raise jslb.WireError(
            i18n("bootstrap.reply_unexpected", rendered, _FIRST_ID)
        )


# Opens the root's log, then runs `serve`, always logging a failure.
def _logged_run(
    root: str, loaded: dict[str, Any], serve: Callable[[], int]
) -> int:
    import verbose
    from internationalization import i18n

    verbose.log_open(root, loaded["verbose_ring"])
    try:
        return serve()
    except Exception as error:
        verbose.log(i18n("bootstrap.run_failed", str(error)))
        raise


# Serves the engine: the main loop's prepare, `tap.start`, its reply, the loop.
def _engine_serve(
    root: str, main_loop: str | None, loaded: dict[str, Any]
) -> int:
    debug: bool = loaded["debug"]
    module = _loop_load(_loop_path(root, main_loop, debug))
    module.loop_prepare(root)
    tests = _tests_read(root) if debug else None
    _first_write(loaded, tests, debug)
    _reply_read(loaded)
    module.loop_run(_READ_FD, _WRITE_FD, root)
    return 0


# Runs the engine: raw mode, the lock, the settings, then with the log open.
def _engine_run(root: str, main_loop: str | None) -> int:
    tty.setraw(_READ_FD, termios.TCSANOW)
    _lock_take(root)
    loaded = _settings_read(root)
    return _logged_run(
        root, loaded, lambda: _engine_serve(root, main_loop, loaded)
    )


# Runs the sandboxed dash through `verbose.exec` at the level, its code back.
def _dash_run(level: int) -> int:
    import verbose

    kept = {
        name: os.environ[name]
        for name in _CONSOLE_VARIABLES
        if name in os.environ
    }
    os.environ.clear()
    os.environ.update(kept)
    code = verbose.exec(level, list(_DASH_ARGV), list(_DASH_VERBOSE))
    return code if code >= 0 else _SIGNAL_BASE - code


# Runs the sandboxed dash with a scrubbed environment, in debug mode only.
def _console_run(root: str, loaded: dict[str, Any]) -> int:
    if not loaded["debug"]:
        return _EXIT_FAILURE
    level: int = loaded["verbose_level"]
    return _logged_run(root, loaded, lambda: _dash_run(level))


# The cascade of an exception, by the rule of `dispatch.cause_make`.
def _cause_make(error: BaseException) -> dict[str, Any]:
    lines = traceback.format_exception(error, chain=False)
    cascade: dict[str, Any] = {
        "message": str(error),
        "stack": "".join(lines).removesuffix("\n"),
    }
    inner = error.__cause__
    if inner is None and not error.__suppress_context__:
        inner = error.__context__
    if inner is not None:
        cascade["cause"] = _cause_make(inner)
    return cascade


# Writes the one `error` line for an exception, in full names, with no `r`.
def _error_write(error: Exception) -> None:
    import jslb

    header = jslb.header_make(_ERROR_TYPE, full=True)
    line = jslb.line_make(header, [], **_cause_make(error))
    _bytes_write(_text_bytes(jslb.line_encode(line)))


# Runs the role the arguments name and returns the exit code.
def bootstrap_run(argv: list[str]) -> int:
    try:
        arguments = _arguments_parse(argv)
    except Exception as error:
        # A refused command line may be the engine's, raw before it writes.
        tty.setraw(_READ_FD, termios.TCSANOW)
        _error_write(error)
        return _EXIT_FAILURE
    try:
        if arguments.role == _CONSOLE_ROLE:
            loaded = _settings_read(arguments.root)
            return _console_run(arguments.root, loaded)
        return _engine_run(arguments.root, arguments.main_loop)
    except Exception as error:
        _error_write(error)
        return _EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(bootstrap_run(sys.argv[1:]))
