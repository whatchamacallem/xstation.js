#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The POSIX start of the engine, which stands alone from the Windows scripts.
# API/python/xsjs_serve.pyi holds the contract. Both stop signals are blocked
# from before ttyd starts, so that no stop comes while nothing watches for it,
# and ttyd's own start unblocks them, since it takes a signal mask from this
# process and a ttyd with them blocked would never stop. That start also has
# the kernel send ttyd SIGTERM when the thread that started it dies, as ttyd's
# session of its own ties its life to nothing else. A thread copies ttyd's log
# to stderr, so that a demo test that waits for no signal still shows it. The
# modules beside this file are imported inside the functions that use them,
# after their bytecode has been sent to build/.

import argparse, ctypes, os, re, shutil, signal, subprocess, sys, threading
from typing import Any, IO, cast

# The public names of this module, as its stub declares them.
__all__ = [
    "TtydServer",
    "page_ready",
    "root_default",
    "root_make",
    "serve_run",
    "ttyd_arguments",
]

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The checkout's top directory, which holds the settings.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# Where the page is built.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# The settings of the checkout.
_SETTINGS_PATH = os.path.join(_CHECKOUT_PATH, "settings.json")

# The strings, which a root holds in a directory of this name.
_ROOT_STRINGS = "i18n"
_STRINGS_PATH = os.path.join(_CHECKOUT_PATH, _ROOT_STRINGS, "en-US.json")

# The directory of a root that holds its modules and seed.
_ROOT_PYTHON = "python"

# The seed of `python`, which a root holds beside its modules.
_SEED_NAME = "seed"

# The name of the serve program's root, under the start script's folder.
_ROOT_NAME = "root"

# The root's log and the files SQLite keeps beside it, which each run removes.
_VERBOSE_NAMES = (
    "_verbose.sqlite",
    "_verbose.sqlite-wal",
    "_verbose.sqlite-shm",
)

# The engine page's template, in `html/`.
_PAGE_TEMPLATE = "engine"

# The program a ttyd build directory holds.
_TTYD_NAME = "ttyd"

# The program that runs the server's bootstrap, the command ttyd runs.
_PYTHON_PROGRAM = "python3"

# ttyd's log line of the port it listens on, whole, so that no digit is missed.
_PORT_PATTERN = re.compile(rb" N:  Listening on port: (\d+)\n")

# The signals that stop the program.
_STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)

# The wait between two looks at ttyd, a default chosen by its writer.
_POLL_SECONDS = 0.1

# The seconds ttyd has to stop after SIGTERM, a default chosen by its writer.
_STOP_SECONDS = 5

# The most bytes a read of ttyd's log takes at once.
_READ_BYTES = 65536

# The descriptor ttyd's log is copied to.
_STDERR_FD = 2

# A shell's exit code for a program a signal ended is this plus the signal.
_SIGNAL_BASE = 128

# The C library's `prctl`, found here, as a forked child should load nothing.
_PRCTL = ctypes.CDLL(None).prctl

# The option of `prctl` that names the signal of a parent's death, by Linux.
_PR_SET_PDEATHSIG = 1

# Bytecode of the modules the functions below import goes in `build/pycache`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# ttyd serving a root, on `port` or, for 0, the port its log then names.
class TtydServer:
    # Starts ttyd and returns once its log names the port it listens on.
    def __init__(self, values: dict[str, Any], root: str, port: int) -> None:
        from internationalization import i18n

        arguments = ttyd_arguments(values, root, port)
        if not os.path.isfile(arguments[0]):
            raise FileNotFoundError(
                i18n("xsjs_serve.ttyd_missing", arguments[0])
            )
        self._root = root
        self._process = subprocess.Popen(
            arguments,
            bufsize=0,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=exec_prepare,
        )
        self.pid = self._process.pid
        self._log = cast(IO[bytes], self._process.stdout)
        self.port = self.port_read()
        self._copier = threading.Thread(target=self.log_copy, daemon=True)
        self._copier.start()

    # Copies the log to stderr up to the port's line. Returns the port.
    def port_read(self) -> int:
        from internationalization import i18n

        seen = b""
        while (found := _PORT_PATTERN.search(seen)) is None:
            data = self._log.read(_READ_BYTES)
            if not data:
                self._log.close()
                code = self._process.wait()
                raise RuntimeError(
                    i18n("xsjs_serve.ttyd_ended", code, self._root)
                )
            os.write(_STDERR_FD, data)
            seen += data
        return int(found.group(1))

    # Copies the rest of the log to stderr, leaving the signals to the waiter.
    def log_copy(self) -> None:
        signal.pthread_sigmask(signal.SIG_BLOCK, _STOP_SIGNALS)
        with self._log:
            while data := self._log.read(_READ_BYTES):
                os.write(_STDERR_FD, data)

    # The page's address on this ttyd, `http://localhost:PORT/`.
    def address_get(self) -> str:
        return f"http://localhost:{self.port}/"

    # Returns at SIGINT, SIGTERM or ttyd's end, both left blocked for the stop.
    def signal_wait(self) -> None:
        signal.pthread_sigmask(signal.SIG_BLOCK, _STOP_SIGNALS)
        while self._process.poll() is None:
            if signal.sigtimedwait(_STOP_SIGNALS, _POLL_SECONDS) is not None:
                return

    # Stops ttyd's group by SIGTERM, by SIGKILL past a wait. Returns its code.
    def server_stop(self) -> int:
        from internationalization import i18n

        code = self._process.poll()
        if code is not None:
            self._copier.join()
            raise RuntimeError(i18n("xsjs_serve.ttyd_ended", code, self._root))
        os.killpg(self.pid, signal.SIGTERM)
        try:
            code = self._process.wait(_STOP_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(self.pid, signal.SIGKILL)
            code = self._process.wait()
        self._copier.join()
        return code if code >= 0 else _SIGNAL_BASE - code


# In ttyd's child: unblocks the stop signals and ties ttyd to this thread.
def exec_prepare() -> None:
    signal.pthread_sigmask(signal.SIG_UNBLOCK, _STOP_SIGNALS)
    # `prctl` fails only on a bad signal number, which a constant cannot be.
    _PRCTL(_PR_SET_PDEATHSIG, ctypes.c_ulong(signal.SIGTERM))


# The serve program's root, `root` under `powershell.linux_folder` of home.
def root_default(values: dict[str, Any]) -> str:
    folder: str = values["powershell"]["linux_folder"]
    return os.path.join(os.path.expanduser("~"), folder, _ROOT_NAME)


# Builds the engine page from `html/engine.html`. Returns its path in `build/`.
def page_ready(values: dict[str, Any]) -> str:
    import page_build

    page_name: str = values["powershell"]["engine_page"]
    page_build.page_build(_PAGE_TEMPLATE, os.path.splitext(page_name)[0])
    return os.path.join(_BUILD_PATH, page_name)


# Makes the root from the built page: its log goes, or with `fresh` all of it.
def root_make(
    values: dict[str, Any],
    page: str,
    root: str,
    parameters: dict[str, bool],
    fresh: bool,
) -> None:
    import switches

    powershell: dict[str, Any] = values["powershell"]
    if fresh and os.path.exists(root):
        shutil.rmtree(root)
    for name in _VERBOSE_NAMES:
        path = os.path.join(root, name)
        if os.path.exists(path):
            os.remove(path)
    python_path = os.path.join(root, _ROOT_PYTHON)
    strings_path = os.path.join(root, _ROOT_STRINGS)
    # The copies of earlier runs go, so the root holds this checkout's only.
    for path in (python_path, strings_path):
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)
    for module in powershell["runtime_modules"]:
        shutil.copy(os.path.join(_PYTHON_PATH, f"{module}.py"), python_path)
    shutil.copytree(
        os.path.join(_PYTHON_PATH, _SEED_NAME),
        os.path.join(python_path, _SEED_NAME),
    )
    shutil.copy(_STRINGS_PATH, strings_path)
    for name in powershell["root_files"]:
        shutil.copy(os.path.join(_CHECKOUT_PATH, name), root)
    shutil.copyfile(page, os.path.join(root, powershell["engine_page"]))
    switches.parameters_write(root, parameters)


# ttyd's command line: the start script's options, the root's `bootstrap.py`.
def ttyd_arguments(values: dict[str, Any], root: str, port: int) -> list[str]:
    powershell: dict[str, Any] = values["powershell"]
    return [
        os.path.join(_CHECKOUT_PATH, powershell["ttyd_build"], _TTYD_NAME),
        "--port",
        str(port),
        "--interface",
        powershell["bind_address"],
        "--writable",
        "--check-origin",
        "--terminal-type",
        powershell["terminal_type"],
        "--index",
        os.path.join(root, powershell["engine_page"]),
        "--url-arg",
        f"--srv-buf-size={values['srv_buf_size']}",
        _PYTHON_PROGRAM,
        os.path.join(root, _ROOT_PYTHON, powershell["bootstrap_script"]),
        "--root",
        root,
    ]


# Serves by the arguments after the program's name. Returns the exit code.
def serve_run(argv: list[str]) -> int:
    import settings, switches

    values = settings.settings_load(_SETTINGS_PATH)
    parser = argparse.ArgumentParser(
        description="Build the engine page, make a root and serve it through"
        " the built ttyd, printing the address, until SIGINT or SIGTERM.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=values["powershell"]["linux_port"],
        help="the port ttyd listens on, 0 for one it picks (default"
        " %(default)s)",
    )
    parser.add_argument(
        "--root",
        default=root_default(values),
        help="the root to make and serve, kept between runs (default"
        " %(default)s)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="remove the root first, with its databases",
    )
    switches.options_add(parser)
    parsed = parser.parse_args(argv)
    switches.switches_set(parsed)
    root = os.path.abspath(parsed.root)
    page = page_ready(values)
    root_make(values, page, root, switches.switches_get(), parsed.fresh)
    signal.pthread_sigmask(signal.SIG_BLOCK, _STOP_SIGNALS)
    server = TtydServer(values, root, parsed.port)
    try:
        print(server.address_get(), flush=True)
        server.signal_wait()
    finally:
        code = server.server_stop()
    return code


if __name__ == "__main__":
    sys.exit(serve_run(sys.argv[1:]))
