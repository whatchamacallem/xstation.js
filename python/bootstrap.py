#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The platform services around the main loop, the command ttyd runs.
# API/python/bootstrap.pyi holds its roles. Its error line goes in full names,
# since it may come before the settings, and once the log is open the
# exception's message, then in debug mode that line's rendering, is logged
# before that line is written. The modules beside this file are imported inside
# the functions that use them, after their bytecode has been sent to build/.

import argparse, fcntl, importlib.machinery, importlib.util, os, signal, sys
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

# The file in the root whose lock one engine at a time holds.
_LOCK_NAME = "engine.lock"

# The permissions the lock file is created with: read and write by its owner.
_LOCK_MODE = 0o600

# The role that runs the console, the only role there is.
_CONSOLE_ROLE = "console"

# The Python before dash that gives it the pty as its controlling terminal.
_TERMINAL_STEP = "; ".join(
    (
        "import fcntl, os, signal, sys, termios",
        "os.setsid()",
        "fcntl.ioctl(0, termios.TIOCSCTTY, 0)",
        "signal.signal(signal.SIGPIPE, signal.SIG_DFL)",
        "signal.signal(signal.SIGXFSZ, signal.SIG_DFL)",
        'entries = open("/proc/self/environ", "rb").read().split(b"\\0")[:-1]',
        'given = dict(entry.split(b"=", 1) for entry in entries)',
        "os.execve(sys.argv[1], sys.argv[1:], given)",
    )
)

# The console's shell: dash, after the step, in the maintainer's sandbox.
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
    "python3",
    "-I",
    "-c",
    _TERMINAL_STEP,
    "/bin/dash",
)

# Its verbose form, with dash's option that prints its input as it reads it.
_DASH_VERBOSE = (*_DASH_ARGV, "-v")

# The shell's verbose level when the parameter verbose is false.
_LEVEL_PLAIN = 1

# The shell's verbose level when the parameter verbose is true.
_LEVEL_VERBOSE = 2

# The directory a console's root must be under, an empty tmpfs to dash.
_CONSOLE_HOME = "/home/"

# The environment variables the console keeps when they are set.
_CONSOLE_VARIABLES = ("HOME", "LANG", "PATH", "TERM")

# The descriptor of the console role's pty, which it gives up before bwrap.
_CONSOLE_FD = 0

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


# Reads the root's parameters and sets the switches from them.
def _parameters_apply(root: str) -> None:
    import switches

    switches.switches_apply(switches.parameters_load(root))


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
def _first_write(loaded: dict[str, Any], full: bool) -> None:
    import jslb, switches, verbose
    from internationalization import i18n

    header = jslb.header_make(_FIRST_TYPE, id=_FIRST_ID, full=full)
    payload: dict[str, Any] = {
        "settings": loaded,
        "switches": switches.switches_get(),
    }
    line = jslb.line_make(header, [], **payload)
    if switches.debug:
        verbose.log(i18n("bootstrap.start_submit", jslb.line_render(line)))
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


# Opens the root's log, then runs `serve`, logging and writing any failure.
def _logged_run(
    root: str, loaded: dict[str, Any], serve: Callable[[], int]
) -> int:
    import verbose
    from internationalization import i18n

    verbose.log_open(root, loaded["verbose_ring"], loaded["blob_max"])
    try:
        return serve()
    except Exception as error:
        verbose.log(i18n("bootstrap.run_failed", str(error)))
        _error_write(error, True)
        return _EXIT_FAILURE


# Serves the engine: the main loop's prepare, `tap.start`, its reply, the loop.
def _engine_serve(
    root: str, main_loop: str | None, loaded: dict[str, Any]
) -> int:
    import switches

    debug = switches.debug
    module = _loop_load(_loop_path(root, main_loop, debug))
    module.loop_prepare(root)
    _first_write(loaded, debug)
    _reply_read(loaded)
    module.loop_run(_READ_FD, _WRITE_FD, root)
    return 0


# Runs the engine: raw mode, the lock, the settings, then with the log open.
def _engine_run(root: str, main_loop: str | None) -> int:
    tty.setraw(_READ_FD, termios.TCSANOW)
    _lock_take(root)
    loaded = _settings_read(root)
    _parameters_apply(root)
    return _logged_run(
        root, loaded, lambda: _engine_serve(root, main_loop, loaded)
    )


# Gives up the pty as the controlling terminal, its group's SIGHUP ignored.
def _terminal_release() -> None:
    handler = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    fcntl.ioctl(_CONSOLE_FD, termios.TIOCNOTTY)
    signal.signal(signal.SIGHUP, handler)


# Gives up the pty and runs the sandboxed dash at the level, its code back.
def _dash_run(level: int) -> int:
    import verbose

    kept = {
        name: os.environ[name]
        for name in _CONSOLE_VARIABLES
        if name in os.environ
    }
    os.environ.clear()
    os.environ.update(kept)
    _terminal_release()
    code = verbose.exec(level, list(_DASH_ARGV), list(_DASH_VERBOSE))
    return code if code >= 0 else _SIGNAL_BASE - code


# Refuses a console's root that is not under `/home/`, links resolved.
def _home_check(root: str) -> None:
    from internationalization import i18n

    if not os.path.realpath(root).startswith(_CONSOLE_HOME):
        raise PermissionError(
            i18n("bootstrap.root_outside", root, _CONSOLE_HOME)
        )


# Runs the sandboxed dash with a scrubbed environment, in debug mode only.
def _console_run(root: str, loaded: dict[str, Any]) -> int:
    import switches

    if not switches.debug:
        return _EXIT_FAILURE
    level = _LEVEL_VERBOSE if switches.verbose else _LEVEL_PLAIN
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


# Writes the one `error` line, full names, no `r`, traced when the log is open.
def _error_write(error: Exception, log_open: bool) -> None:
    import jslb, switches, verbose
    from internationalization import i18n

    header = jslb.header_make(_ERROR_TYPE, full=True)
    line = jslb.line_make(header, [], **_cause_make(error))
    if log_open and switches.debug:
        verbose.log(i18n("bootstrap.line_error", jslb.line_render(line)))
    data = _text_bytes(jslb.line_encode(line))
    # A hangup from here on cannot end the run, which exits 1 itself.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    _bytes_write(data)


# Runs the role the arguments name and returns the exit code.
def bootstrap_run(argv: list[str]) -> int:
    try:
        arguments = _arguments_parse(argv)
    except Exception as error:
        # A refused command line may be the engine's, raw before it writes.
        tty.setraw(_READ_FD, termios.TCSANOW)
        _error_write(error, False)
        return _EXIT_FAILURE
    try:
        if arguments.role == _CONSOLE_ROLE:
            _home_check(arguments.root)
            loaded = _settings_read(arguments.root)
            _parameters_apply(arguments.root)
            return _console_run(arguments.root, loaded)
        return _engine_run(arguments.root, arguments.main_loop)
    except Exception as error:
        _error_write(error, False)
        return _EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(bootstrap_run(sys.argv[1:]))
