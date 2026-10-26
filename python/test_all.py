#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The one runner of every test suite, by category. A smoke-test run runs the
# suites labelled smoke-test, the important ones that fit in 2 minutes; a
# normal-test run runs the suites of both labels. Each suite's label is
# written beside it, and category.py holds the labels, the options and their
# checks. It runs the Python test modules in the testing order of the module
# DAG, TAP_PLAN.md section 3.3: the tests of the TAP producer and consumer
# first, then those of the infrastructure for testing, the harness and
# category, then each next module the DAG allows. Each is one block of one
# TAP stream that goes to stdout a line at a time; then it checks that
# stream with the TAP consumer and exits 1 unless it is well formed and
# holds no failing point, a bail out counting as one. When the stream is
# clean it runs, in this process and given the category, the checks of
# test_posix.py, the wire test and the browser test, and ends at the first
# that fails, with its exit code. Every module has a timer, the gold
# record's module_seconds. The JSLB vectors are written anew into
# build/vectors as test_jslb loads, inside its block.
#
# After each module it writes "<module>: <label>, <s> s" to stderr, so that
# stdout stays the TAP stream. After the checks of test_posix.py it prints
# "test_posix.py: smoke-test, <s> s", and a passing run ends with "the
# <category> run took <s> s". A smoke-test run has the gold record's
# smoke_seconds in all from its start: each alarm ends at that deadline at
# the latest, a deadline passed before a suite starts raises at once, and
# passing it fails naming the suite it stopped. A normal-test run has no
# limit of its own. Standard library only:
#
#     python3 python/test_all.py [--smoke-test | --normal-test] [--failfast]
#         [--stream] [--module NAME]... [--tty]
#
# --smoke-test is the default. In a smoke-test run, or with --failfast, the
# first failing test ends the stream. --stream ends the run once the stream
# is checked, before the checks after it, and writes nothing to stdout but
# the stream. --module runs only the suites it names, once each, in the
# order above, each one the category runs. --tty runs the stream on the
# engine tty instead of in this process: through tap_tty.py, bootstrap.py
# on a new pty serves the TAP suite server, tap_loop.py, on a debug root in
# build/, which runs this file with --stream on the same suites and pushes
# each line of its stream, and each line relayed is written to stdout as it
# comes. The server's run writes its stderr, its timings among it, to this
# stderr when it ends, and its exit code must be the stream's verdict.

import argparse, functools, importlib, os, signal, sys, tempfile, time, types
import unittest

# The python directory of the checkout, which holds this script.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The build directory of the checkout, for bytecode and scratch files.
_BUILD_PATH = os.path.join(os.path.dirname(_PYTHON_PATH), "build")

# The test modules and their labels, in the order of `TAP_PLAN.md` 3.3.
_MODULES: list[tuple[str, str]] = [
    ("test_tap_producer", "smoke-test"),
    ("test_tap_consumer", "smoke-test"),
    ("test_test", "smoke-test"),
    ("test_internationalization", "smoke-test"),
    ("test_jslb", "smoke-test"),
    ("test_vectors_make", "smoke-test"),
    ("test_settings", "smoke-test"),
    ("test_verbose", "smoke-test"),
    ("test_substrate", "smoke-test"),
    ("test_dispatch", "smoke-test"),
    ("test_mcp", "smoke-test"),
    ("test_stall_loop", "smoke-test"),
    ("test_engine_tap", "smoke-test"),
    ("test_engine_verbose", "smoke-test"),
    ("test_engine_kv", "smoke-test"),
    ("test_engine_doc", "smoke-test"),
    ("test_engine_db", "smoke-test"),
    ("test_engine_turn", "smoke-test"),
    ("test_engine_sql", "smoke-test"),
    ("test_engine_mcp", "smoke-test"),
    ("test_engine_system", "smoke-test"),
    ("test_echo_loop", "smoke-test"),
    ("test_main_loop", "smoke-test"),
    ("test_bootstrap", "smoke-test"),
    ("test_mcp_stdio", "smoke-test"),
    ("test_third_party_fetch", "smoke-test"),
    ("test_page_build", "smoke-test"),
    ("test_devtools", "smoke-test"),
    ("test_reformat", "smoke-test"),
    ("test_test_posix", "smoke-test"),
    ("test_tap_tty", "smoke-test"),
]

# The one test module that reads the vectors, which are written as it loads.
_VECTORS_READER = "test_jslb"

# Where the vectors are written, an intermediate under `build`.
_VECTORS_PATH = os.path.join(_BUILD_PATH, "vectors")

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


# Writes the vectors if the module reads them, then imports it, returns tests.
def suite_load(loader: unittest.TestLoader, name: str) -> unittest.TestSuite:
    if name == _VECTORS_READER:
        import vectors_make

        vectors_make.vectors_write(_VECTORS_PATH)
    return loader.loadTestsFromModule(importlib.import_module(name))


# Arms a repeating alarm that raises the plan's message, or none for no plan.
def timer_start(plan: tuple[float, str] | None) -> None:
    if plan is None:
        return
    seconds, message = plan

    # Raises the failure of the suite that ran out of time.
    def alarm_raise(signal_number: int, frame: types.FrameType | None) -> None:
        raise RuntimeError(message)

    signal.signal(signal.SIGALRM, alarm_raise)
    signal.setitimer(signal.ITIMER_REAL, seconds, seconds)


# Cancels the alarm of a suite that finished in time.
def timer_stop() -> None:
    signal.setitimer(signal.ITIMER_REAL, 0)


# The suites the run takes: the category's, only those named if any are.
def modules_chosen(
    parser: argparse.ArgumentParser, named: list[str], chosen: str
) -> list[tuple[str, str]]:
    import category

    labels = dict(_MODULES)
    for name in named:
        if named.count(name) > 1:
            parser.error(f"--module {name} is given more than once")
        if not category.suite_runs(labels[name], chosen):
            parser.error(f"--module {name} is not a suite of a {chosen} run")
    return [
        (name, label)
        for name, label in _MODULES
        if category.suite_runs(label, chosen) and (not named or name in named)
    ]


# Runs the suites in this process, one block each, timing each one.
def stream_run(
    stream: StreamWriter,
    modules: list[tuple[str, str]],
    failfast: bool,
    limit: float | None,
    started: float,
) -> None:
    import category, harness, tap_producer

    module_seconds = float(harness.gold_get("module_seconds"))
    runner = tap_producer.TAPTestRunner(failfast or limit is not None)
    runner.set_stream(stream.line_write)
    loader = unittest.TestLoader()
    for name, label in modules:
        begun = time.monotonic()
        what = f"module {name}"
        timer_start(
            category.alarm_plan(what, module_seconds, limit, begun - started)
        )
        load = functools.partial(suite_load, loader, name)
        passed = runner.module_run(name, load)
        timer_stop()
        seconds = time.monotonic() - begun
        sys.stderr.write(f"{name}: {label}, {seconds:.3f} s\n")
        sys.stderr.flush()
        if not passed:
            break
    runner.run_end()


# Runs the suites on the TAP suite server over a pty, relaying its stream.
def stream_relay(
    stream: StreamWriter,
    modules: list[tuple[str, str]],
    chosen: str,
    failfast: bool,
    limit: float | None,
    started: float,
) -> int:
    import category, tap_tty

    what = "the stream over the tty"
    elapsed = time.monotonic() - started
    timer_start(category.alarm_plan(what, None, limit, elapsed))
    names = [name for name, _ in modules]
    os.makedirs(_BUILD_PATH, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="test_all-", dir=_BUILD_PATH
    ) as work:
        root = os.path.join(work, "root")
        code, errors = tap_tty.suites_relay(
            root, chosen, failfast, names, stream.line_write
        )
    timer_stop()
    sys.stderr.write(errors)
    sys.stderr.flush()
    return code


# Runs the modules of the category, checks the stream, then runs the rest.
def main(arguments: list[str]) -> int:
    import category, tap_consumer

    parser = argparse.ArgumentParser(
        description="Run the suites of a category: the Python test modules"
        " in the testing order, the tests of the TAP modules first, as one"
        " TAP stream on stdout, check the stream, then run the checks of"
        " test_posix.py, the wire test and the browser test.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="end the stream at the first failing test",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="end the run once the stream is checked, writing nothing else"
        " to stdout",
    )
    parser.add_argument(
        "--module",
        action="append",
        default=[],
        choices=[name for name, _ in _MODULES],
        help="run only this suite; given once for each suite to run",
    )
    parser.add_argument(
        "--tty",
        action="store_true",
        help="run the stream on a pty through bootstrap.py and the TAP suite"
        " server, tap_loop.py, writing each line it relays",
    )
    category.options_add(parser)
    parsed = parser.parse_args(arguments)
    failfast: bool = parsed.failfast
    chosen: str = parsed.category
    modules = modules_chosen(parser, parsed.module, chosen)
    started = time.monotonic()
    limit = category.limit_seconds(chosen)
    stream = StreamWriter()
    code: int | None = None
    if parsed.tty:
        code = stream_relay(stream, modules, chosen, failfast, limit, started)
    else:
        stream_run(stream, modules, failfast, limit, started)
    stats = tap_consumer.document_stats(stream.document_get())
    if not stats.well_formed:
        raise RuntimeError("the TAP stream is not well formed")
    verdict = 1 if stats.failed else 0
    if code is not None and code != verdict:
        raise RuntimeError(
            f"test_all.py on the tty exited with {code}, though its stream"
            f" holds {stats.failed} failures"
        )
    if verdict or parsed.stream:
        return verdict
    posix_label = "smoke-test"
    if category.suite_runs(posix_label, chosen):
        import test_posix

        begun = time.monotonic()
        timer_start(
            category.alarm_plan("test_posix.py", None, limit, begun - started)
        )
        test_posix.main([f"--{chosen}"])
        timer_stop()
        seconds = time.monotonic() - begun
        print(f"test_posix.py: {posix_label}, {seconds:.3f} s", flush=True)
    import test_wire

    elapsed = time.monotonic() - started
    timer_start(category.alarm_plan("test_wire.py", None, limit, elapsed))
    code = test_wire.main([f"--{chosen}"])
    timer_stop()
    if code:
        return code
    import test_browser

    elapsed = time.monotonic() - started
    timer_start(category.alarm_plan("test_browser.py", None, limit, elapsed))
    code = test_browser.main([f"--{chosen}"])
    timer_stop()
    if code:
        return code
    elapsed = time.monotonic() - started
    print(f"the {chosen} run took {elapsed:.3f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
