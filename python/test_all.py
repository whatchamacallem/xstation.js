#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Runs the Python test modules in dependency order, each as one subtest block
# of one TAP stream that goes to stdout a line at a time, then checks that
# stream with the TAP consumer and exits 1 unless it is well formed and holds
# no `not ok` point. It stops at the first module that fails, and every
# module has a timer. When the stream is clean it runs the wire test in this
# process and exits with its code. Standard library only:
#
#     python3 python/test_all.py
#     python3 python/test_all.py --failfast
#     python3 python/test_all.py --nested
#
# With --failfast the first failing test ends the stream. With --nested it
# runs only the nested fixture of the TAP producer test, which has a passing,
# a failing, a raising and a skipped method, so it exits 1.

import argparse, os, signal, sys, types, unittest

# The python directory of the checkout, which holds this script.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The build directory of the checkout, for bytecode and scratch files.
_BUILD_PATH = os.path.join(os.path.dirname(_PYTHON_PATH), "build")

# How many seconds one module may run before it fails.
_MODULE_SECONDS = 120

# The module names in dependency order, which are also the block names.
_MODULES = [
    "i18n",
    "tap.consumer",
    "tap.producer",
    "jslb",
    "verbose",
    "settings",
    "substrate",
    "dispatch",
    "mcp",
    "engine_kv",
    "engine_doc",
    "engine_db",
    "engine_turn",
    "engine_sql",
    "engine_verbose",
    "engine_tap",
    "engine_mcp",
    "engine_system",
    "main_loop",
    "bootstrap",
    "mcp_stdio",
    "third_party_fetch",
    "devtools",
    "page_build",
]

# The name of the block that the nested fixture runs as.
_NESTED_BLOCK = "fixture"

# The dotted name the loader finds the nested fixture class by.
_NESTED_NAME = "tap.test_producer.TestProducer.NestedFixture"

# The tests and the modules they test are imported from python/.
sys.path.insert(0, _PYTHON_PATH)

# Bytecode of the modules imported from there goes in `build/pycache`.
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


# Returns the tests the loader finds by `name`, raising on any load error.
def suite_load(loader: unittest.TestLoader, name: str) -> unittest.TestSuite:
    suite = loader.loadTestsFromName(name)
    if loader.errors:
        raise RuntimeError(f"cannot load {name}:\n{loader.errors[0]}")
    return suite


# Returns the name of the test module of `module`.
def test_module(module: str) -> str:
    package, _, leaf = module.rpartition(".")
    return f"{package}.test_{leaf}" if package else f"test_{leaf}"


# Arms the alarm so that `module` fails if it runs longer than allowed.
def timer_start(module: str) -> None:
    # Raises the failure of the module that ran out of time.
    def alarm_raise(signal_number: int, frame: types.FrameType | None) -> None:
        raise RuntimeError(
            f"module {module} ran longer than {_MODULE_SECONDS} s"
        )

    signal.signal(signal.SIGALRM, alarm_raise)
    signal.alarm(_MODULE_SECONDS)


# Cancels the alarm of a module that finished in time.
def timer_stop() -> None:
    signal.alarm(0)


# Runs the modules, checks the stream, then runs the wire test.
def main() -> int:
    import tap.consumer, tap.producer

    parser = argparse.ArgumentParser(
        description="Run the Python test modules in dependency order as one"
        " TAP stream on stdout, check the stream, then run the wire test."
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="end the stream at the first failing test",
    )
    parser.add_argument(
        "--nested",
        action="store_true",
        help="run only the nested fixture of the producer test, which fails",
    )
    arguments = parser.parse_args()
    failfast: bool = arguments.failfast
    nested: bool = arguments.nested
    modules = (
        [(_NESTED_BLOCK, _NESTED_NAME)]
        if nested
        else [(module, test_module(module)) for module in _MODULES]
    )
    stream = StreamWriter()
    runner = tap.producer.TapRunner(stream.line_write, failfast)
    loader = unittest.TestLoader()
    for block, name in modules:
        timer_start(block)
        passed = runner.module_run(block, suite_load(loader, name))
        timer_stop()
        if not passed:
            break
    runner.run_end()
    stats = tap.consumer.document_stats(stream.document_get())
    if not stats.well_formed:
        raise RuntimeError("the TAP stream is not well formed")
    if stats.not_ok:
        return 1
    if nested:
        return 0
    import test_wire

    # The wire test parses `sys.argv` itself, so it is given no options.
    del sys.argv[1:]
    return test_wire.main()


if __name__ == "__main__":
    sys.exit(main())
