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
# engine.lock file of the root, loads the main loop file, has it prepare the
# databases, writes hello, reads and checks the reply and runs the loop.
# --main-loop is served only to the engine role with the setting debug true,
# and neither option may be given twice. With the role console it runs dash in
# the root with a scrubbed environment when the setting debug is true, and
# exits 1 otherwise. Any exception writes one error line, which jslb encodes,
# and exits 1. The modules beside this file are imported inside the functions
# that use them, after their bytecode has been sent to build/.

import argparse, fcntl, hashlib, importlib.machinery, importlib.util, os, sys
import termios, traceback, tty, types
from collections.abc import Iterator
from typing import Any, NamedTuple, NoReturn, cast

# The directory that holds this file and the modules it imports.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# This file, whose path and `sha256` the `hello` line carries.
_BOOTSTRAP_PATH = os.path.abspath(__file__)

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

# The shell the console role runs.
_DASH_PATH = "/bin/dash"

# The option of dash that prints its input as it reads it, its verbose form.
_DASH_VERBOSE = "-v"

# The environment variables the console keeps when they are set.
_CONSOLE_VARIABLES = ("HOME", "LANG", "PATH", "TERM")

# The environment variable that holds the provider key.
_PROVIDER_VARIABLE = "XSJS_PROVIDER_KEY"

# The descriptor the engine reads its lines from, its pty.
_READ_FD = 0

# The descriptor the engine writes its lines to, the same pty.
_WRITE_FD = 1

# The type of the engine's first request and of its reply.
_HELLO_TYPE = "hello"

# The id of `hello`, the first request on the engine tty.
_HELLO_ID = 1

# The number of header fields of the reply to `hello`: its type and reply.
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
    from i18n import i18n

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
        help="console runs dash in the root in debug mode",
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
    from i18n import i18n

    path = os.path.join(root, _LOCK_NAME)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, _LOCK_MODE)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        os.close(descriptor)
        raise RuntimeError(i18n("bootstrap.lock_held", path)) from error


# Returns the provider key, which only a provider that is not scripted needs.
def _provider_get(scripted: bool) -> str:
    from i18n import i18n

    key = os.environ.get(_PROVIDER_VARIABLE, "")
    if key == "" and not scripted:
        raise LookupError(i18n("bootstrap.provider_unset", _PROVIDER_VARIABLE))
    return key


# Returns the main loop file: the stock one, or in debug mode a named one.
def _loop_path(root: str, name: str | None, debug: bool) -> str:
    from i18n import i18n

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
    from i18n import i18n

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


# Encodes `hello`, the engine's first request, in the names `full` selects.
def _hello_encode(
    root: str,
    loaded: dict[str, Any],
    seq: dict[str, int],
    provider_key: str,
    full: bool,
) -> bytes:
    import jslb

    with open(_BOOTSTRAP_PATH, "rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    header = jslb.header_make(_HELLO_TYPE, id=_HELLO_ID, full=full)
    line = jslb.line_make(
        header,
        [],
        bootstrap=_BOOTSTRAP_PATH,
        sha256=digest,
        pid=os.getpid(),
        root=root,
        settings=loaded,
        seq=seq,
        provider_key=provider_key,
    )
    return _text_bytes(jslb.line_encode(line))


# Writes all the bytes to the engine's output, with no buffer between.
def _bytes_write(data: bytes) -> None:
    view = memoryview(data)
    while len(view) > 0:
        written = os.write(_WRITE_FD, view)
        view = view[written:]


# Reads the reply to `hello` a byte at a time, so no byte after it is taken.
def _reply_read(loaded: dict[str, Any]) -> None:
    import jslb
    from i18n import i18n

    # Refuses a blob large enough to stream, as the reply carries none.
    def sink_refuse(header: jslb.Object) -> NoReturn:
        size = jslb.field_get(header, "size")
        raise jslb.WireError(i18n("bootstrap.reply_blob", size))

    decoder = jslb.LineDecoder(
        loaded["line_max"],
        loaded["blob_max"],
        loaded["message_max"],
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
        or jslb.field_get(header, "type") != _HELLO_TYPE
        or type(reply) is not int
        or reply != _HELLO_ID
        or len(jslb.payload_of(line)) > 0
    ):
        rendered = jslb.line_render(line)
        raise jslb.WireError(
            i18n("bootstrap.reply_unexpected", rendered, _HELLO_ID)
        )


# Runs the engine: raw mode, the lock, `hello` and its reply, then the loop.
def _engine_run(root: str, main_loop: str | None) -> int:
    tty.setraw(_READ_FD, termios.TCSANOW)
    _lock_take(root)
    loaded = _settings_read(root)
    debug: bool = loaded["debug"]
    provider_key = _provider_get(loaded["provider"]["scripted"])
    module = _loop_load(_loop_path(root, main_loop, debug))
    seq: dict[str, int] = module.loop_prepare(root)
    _bytes_write(_hello_encode(root, loaded, seq, provider_key, debug))
    _reply_read(loaded)
    module.loop_run(_READ_FD, _WRITE_FD, root)
    return 0


# Runs dash in the root with a scrubbed environment, in debug mode only.
def _console_run(root: str, debug: bool) -> int:
    if not debug:
        return _EXIT_FAILURE
    import verbose

    kept = {
        name: os.environ[name]
        for name in _CONSOLE_VARIABLES
        if name in os.environ
    }
    os.environ.clear()
    os.environ.update(kept)
    os.chdir(root)
    code = verbose.exec(0, [_DASH_PATH], [_DASH_PATH, _DASH_VERBOSE])
    return code if code >= 0 else _SIGNAL_BASE - code


# Writes the one `error` line for an exception: `message` and `stack`, no `r`.
def _error_write(error: Exception) -> None:
    import jslb

    stack = "".join(traceback.format_exception(error)).removesuffix("\n")
    header = jslb.header_make(_ERROR_TYPE)
    line = jslb.line_make(header, [], message=str(error), stack=stack)
    _bytes_write(_text_bytes(jslb.line_encode(line)))


# Runs the role the arguments name and returns the exit code.
def bootstrap_run(argv: list[str]) -> int:
    try:
        arguments = _arguments_parse(argv)
        if arguments.role == _CONSOLE_ROLE:
            debug: bool = _settings_read(arguments.root)["debug"]
            return _console_run(arguments.root, debug)
        return _engine_run(arguments.root, arguments.main_loop)
    except Exception as error:
        _error_write(error)
        return _EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(bootstrap_run(sys.argv[1:]))
