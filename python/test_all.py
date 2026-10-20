#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Runs the tests of the TAP producer and consumer first, then the other Python
# test modules in dependency order, each as one block of one TAP stream that
# goes to stdout a line at a time, then checks that stream with the TAP
# consumer and exits 1 unless it is well formed and holds no failing point. It
# stops at the first module that fails, and every module has a timer. When the
# stream is clean it runs the wire test in this process, then, when that exits
# 0, the browser test, and exits with the code of the last one run. Standard
# library only:
#
#     python3 python/test_all.py
#     python3 python/test_all.py --failfast
#
# With --failfast the first failing test ends the stream.

import argparse, functools, importlib, os, signal, sys, types, unittest

# The python directory of the checkout, which holds this script.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The build directory of the checkout, for bytecode and scratch files.
_BUILD_PATH = os.path.join(os.path.dirname(_PYTHON_PATH), "build")

# A default chosen by its writer: the seconds a module runs before it fails.
_MODULE_SECONDS = 120.0

# The test modules, the TAP ones first, then in dependency order.
_MODULES = [
    "test_tap_producer",
    "test_tap_consumer",
    "test_i18n",
    "test_jslb",
    "test_verbose",
    "test_settings",
    "test_substrate",
    "test_dispatch",
    "test_mcp",
    "test_engine_kv",
    "test_engine_doc",
    "test_engine_db",
    "test_engine_turn",
    "test_engine_sql",
    "test_engine_verbose",
    "test_engine_tap",
    "test_engine_mcp",
    "test_engine_system",
    "test_main_loop",
    "test_bootstrap",
    "test_mcp_stdio",
    "test_third_party_fetch",
    "test_devtools",
    "test_page_build",
]

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# Writes each TAP line to stdout at once and keeps the lines for checking.
class StreamWriter:
    # Starts with no lines.
    def __init__(self) -> None:
        self._lines: list[str] = []

    # Returns the lines written so far as one document.
    def document_get(self) -> str:
        return "".join(line + "\n" for line in self._lines)

    # Writes the line and a newline to stdout, flushed, and keeps the line.
    def line_write(self, text: str) -> None:
        self._lines.append(text)
        sys.stdout.write(text + "\n")
        sys.stdout.flush()


# Imports the test module and returns its tests.
def suite_load(loader: unittest.TestLoader, name: str) -> unittest.TestSuite:
    return loader.loadTestsFromModule(importlib.import_module(name))


# Arms a repeating alarm so that `module` fails if it runs longer than allowed.
def timer_start(module: str) -> None:
    # Raises the failure of the module that ran out of time.
    def alarm_raise(signal_number: int, frame: types.FrameType | None) -> None:
        raise RuntimeError(
            f"module {module} ran longer than {_MODULE_SECONDS} s"
        )

    signal.signal(signal.SIGALRM, alarm_raise)
    signal.setitimer(signal.ITIMER_REAL, _MODULE_SECONDS, _MODULE_SECONDS)


# Cancels the alarm of a module that finished in time.
def timer_stop() -> None:
    signal.setitimer(signal.ITIMER_REAL, 0)


# Runs the modules, checks the stream, then the wire and browser tests.
def main() -> int:
    import tap_consumer, tap_producer

    parser = argparse.ArgumentParser(
        description="Run the tests of the TAP modules, then the other Python"
        " test modules in dependency order, as one TAP stream on stdout,"
        " check the stream, then run the wire test and the browser test."
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="end the stream at the first failing test",
    )
    arguments = parser.parse_args()
    failfast: bool = arguments.failfast
    stream = StreamWriter()
    runner = tap_producer.TAPTestRunner(failfast)
    runner.set_stream(stream.line_write)
    loader = unittest.TestLoader()
    for name in _MODULES:
        timer_start(name)
        load = functools.partial(suite_load, loader, name)
        passed = runner.module_run(name, load)
        timer_stop()
        if not passed:
            break
    runner.run_end()
    stats = tap_consumer.document_stats(stream.document_get())
    if not stats.well_formed:
        raise RuntimeError("the TAP stream is not well formed")
    if stats.failed:
        return 1
    import test_wire

    # The wire test parses `sys.argv` itself, so it is given no options.
    del sys.argv[1:]
    code = test_wire.main()
    if code != 0:
        return code
    # The browser test parses `sys.argv` itself, so it too gets no options.
    del sys.argv[1:]
    import test_browser

    return test_browser.main()


if __name__ == "__main__":
    sys.exit(main())
