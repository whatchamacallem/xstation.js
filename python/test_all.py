#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The one runner of every test suite, by category. A smoke-test run runs the
# suites labelled smoke-test, the important ones that fit in 2 minutes; a
# normal-test run runs the suites of both labels. Each suite's label is
# written beside it, and category.py holds the labels, the options and their
# checks. It runs the Python test suites and the TypeScript blocks in the
# order below, each one block of one TAP stream that goes to stdout a line
# at a time, each line read by the TAP consumer as it is written: it raises
# at the first line that does not fit, naming the block it is in or follows,
# and stops after the first block in which the consumer counts a failure. It
# raises unless the stream then ended, with its parent plan or a bail out,
# and exits 1 unless the consumer counted exactly the failing points
# --failures expects, none by default, a bail out counting as one unless it
# follows a failing point. When the stream passes so it runs, in this
# process and given the category, the checks of test_posix.py, the wire test
# and the browser test, and ends at the first that fails, with its exit
# code. Every suite and block has a timer, the gold record's module_seconds.
# Before the first block, in this process and outside every timer, the run
# has third_party_fetch.py fetch each pinned third party file that is not in
# place with its pinned digest, then has ttyd_build.py build ttyd where
# settings.json says, from the pinned archive and the project's patches,
# unless it was built from them, its programs' output in a log there, and a
# failed fetch or build fails the run there.
#
# The suites run in strict dependency order, in eight phases that only the
# order of the lists shows. Three are of Python: the unit suites,
# test_<module>.py, by layer; then the pair test of the TAP producer and
# consumer, test_tap_pair.py, and the integration suites,
# test_integrate_<module>.py, by the layer of their module; then the stdio
# suites, which start bootstrap.py or mcp_stdio.py as a program and talk to
# it over its stdio, by layer. Two are of group A, the TypeScript blocks run
# in Node: the unit blocks, test_<module>.ts, by layer; then the pair test
# of the TypeScript TAP producer and the Python consumer, test_tap_pair_ts.py,
# and the integration blocks, test_integrate_<module>.ts, by the layer of
# their block. Two are of group B, the TypeScript blocks run in headless
# Chrome: the unit blocks, then the integration blocks, each by layer as in A.
# One is of group C, the TypeScript blocks behind ttyd: its integration blocks,
# by layer as in A. A module calls into another when it imports it, at the top
# or in a function, loads its file, runs it as a program, or has it run inside
# the block of its suite, as this file has the TAP producer and consumer in
# every block; a call of a function it was handed is no call into the module
# that handed it over. A suite runs only after the suites of
# every module that its module or its own code calls into, directly or
# transitively, have passed. Layer 0 holds the suites of the TAP producer
# and consumer, whose only callees are the two of them, so the blocks of the
# unit phase are trusted to the two before the pair test proves that they
# agree, as group A's unit blocks are trusted to the TypeScript producer and
# the Python consumer before theirs. Each next layer holds the suites whose
# callees' suites all sit in earlier layers, alphabetical within it, and
# test_test is the one suite of harness.py, category.py and line_coverage.py.
# Two modules that call into each other are a bug. The later suites, listed
# apart with the programs they wait on, which are not yet approved, are in
# no phase: --module refuses them, and no category runs them.
#
# A TypeScript block is named by its file in ts, as test_jslb.ts, and runs
# in a realm of its own, a node process. Before the first block the run
# builds the Node bundle, build/ts/node.js, with page_build.node_build, and a
# build that fails fails the run. Each realm runs node build/ts/node.js
# BLOCK, with --failfast when the run's first failing test ends the stream.
# It is sent tap.start, with the id 101, the settings and the gold record,
# built as the engine's start builds it, and answers with an Empty reply.
# The text of each tap.line it pushes then goes to the relay of the TAP
# producer, which writes the block's indented lines to the stream and its
# parent line, under the block's timer. The realm must exit 0, and is killed
# when its block ends. Any failure of a block fails the run, the realm's
# stderr in its cause. The local HTTP server of local_http.py, the scripted
# far end of a block's fetches, starts from the gold's script before the
# first block that needs it, and stops when the stream ends, before the
# checks after it.
#
# A block of group B runs in a page load of its own in the one browser of the
# run, chrome-headless-shell on its DevTools pipe. Before the first B block,
# outside every block timer, the run builds the headless page,
# build/headless.html, with page_build.page_build, starts the browser, and
# adds the binding realm_line, which stands on every later load; a build or
# a start that fails fails the run. The page comes from the local HTTP
# server, from the server of the block's script if it has one, so that its
# fetches are of the page's own origin, and from that of the gold's
# typescript.test_headless.server if not. Under the block's timer the block
# loads the page, then calls test_headless.realm_start(BLOCK, FAILFAST,
# LINE) by Runtime.evaluate, LINE the base64 of tap.start; every DevTools
# wait of the block ends at the timer's end alone, so that the gold's
# seconds are the block's one limit. Each call of
# realm_line carries the base64 of one of the realm's lines: the Empty reply
# first, then each tap.line, whose text goes to the relay as in A. A worker
# block also sends verbose.put pushes, whose entries go to the block's log
# with the page's console messages, and the settings.set its worker sends
# toward the UI thread, which no UI thread takes there. Any other line, as an
# error or a fault, fails the block. The realm's stream ends at its last
# line, its parent plan or a bail out, and the block then loads about:blank,
# which ends the page and its worker, before the relay ends. Any failure of
# a block fails the run, the block's log in its cause. The browser stops when
# the stream ends, before the servers, so that it holds none of their
# connections.
#
# A block of group C runs as a block of B does, on the headless page that a
# ttyd of its own serves as its index, so that the block's ports to tty 0
# and tty 1 reach that ttyd and the server it runs. Before the block,
# outside its timer and inside the deadline, the run makes the block's
# root in build/ as the start script makes the server's: the modules of
# powershell.runtime_modules and the seed in its python/, i18n/en-US.json,
# settings.json with debug true, the gold record as test_settings.json,
# and in its main_loop/ the main loop file of python/ that the gold's
# typescript.BLOCK.root names under main_loop, if it names one. It starts
# the ttyd that ttyd_build.py built, in a session of its own, with the
# start script's options, --port 0, --interface the bind address,
# --writable, --check-origin, --terminal-type, --url-arg and
# --srv-buf-size, and --index build/headless.html, to run python3
# ROOT/python/bootstrap.py --root ROOT, with --main-loop and the file's
# name when the gold names one. ttyd writes its log to a file of its own,
# from which the run reads its version and its port, and a ttyd that
# ends first fails the run, its log in the cause. The block loads
# http://ADDRESS:PORT/. After the block's about:blank, outside its timer
# and inside the deadline, the run stops ttyd's process group by SIGTERM,
# kills it when it still runs after the gold's
# typescript.test_headless.stop_seconds, copies ttyd's log to the block's
# log, removes the root, then fails the run if ttyd was killed or had
# ended before its stop; the block's relay ends after. A root made for a
# block that did not run stops before the browser, its log to stderr.
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
#         [--stream] [--module NAME]... [--failures N] [--tty] [--coverage]
#
# --smoke-test is the default. In a smoke-test run, or with --failfast, the
# first failing test ends the stream. --stream ends the run once the stream
# is checked, before the checks after it, and writes nothing to stdout but
# the stream. --module runs only the suites and blocks it names, once each,
# in the order above, each one the category runs; it alone runs a suite or a
# block that fails by design, listed apart, so that a run can check that
# failures are counted, and counted right, by --failures. --tty runs the
# stream on the engine tty instead of in this process: through tap_tty.py,
# bootstrap.py on a new pty serves the TAP suite server, tap_loop.py, on a
# debug root in build/, which runs this file with --stream on the same
# suites and blocks and the same --failures, and pushes each line of its
# stream, and each line relayed is written to stdout and read by the
# consumer as it comes. The server's run writes its stderr, its timings
# among it, to this stderr when it ends, and its exit code must be the
# stream's verdict. --coverage counts with line_coverage.py the lines run
# from before any other project module loads, and after the passing block of
# the last suite of the run that counts for a module, it fails at that
# module's first line never counted as run. A unit suite counts for the
# module of its name, or for those listed for it, and an integration or
# stdio suite, or a TypeScript block, for none. It counts in this process,
# so it refuses --tty.

import argparse, base64, contextlib, functools, importlib, json, os, re
import shutil, signal, subprocess, sys, tempfile, time, types, unittest
from collections.abc import Callable
from typing import Any, IO, NoReturn, TYPE_CHECKING, cast

# Only type checks import these here, and `main` imports `line_coverage` first.
if TYPE_CHECKING:
    import devtools, jslb, line_coverage, local_http, tap_consumer
    import tap_producer

# The python directory of the checkout, which holds this script.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The top directory of the checkout, which holds the settings and the gold.
_ROOT_PATH = os.path.dirname(_PYTHON_PATH)

# The build directory of the checkout, for bytecode and scratch files.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The settings that `tap.start` carries to a realm.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# The gold record that `tap.start` carries to a realm as its test settings.
_TESTS_PATH = os.path.join(_ROOT_PATH, "test_settings.json")

# The suites and their labels, in the three Python phases of the order above.
_MODULES: list[tuple[str, str]] = [
    ("test_tap_consumer", "smoke-test"),
    ("test_tap_producer", "smoke-test"),
    ("test_internationalization", "smoke-test"),
    ("test_reformat", "smoke-test"),
    ("test_test", "smoke-test"),
    ("test_third_party_fetch", "smoke-test"),
    ("test_devtools", "smoke-test"),
    ("test_jslb", "smoke-test"),
    ("test_local_http", "smoke-test"),
    ("test_stall_loop", "smoke-test"),
    ("test_substrate", "smoke-test"),
    ("test_test_posix", "smoke-test"),
    ("test_verbose", "smoke-test"),
    ("test_devtools_chrome", "smoke-test"),
    ("test_dispatch", "smoke-test"),
    ("test_settings", "smoke-test"),
    ("test_vectors_make", "smoke-test"),
    ("test_engine_db", "smoke-test"),
    ("test_engine_doc", "smoke-test"),
    ("test_engine_kv", "smoke-test"),
    ("test_engine_sql", "smoke-test"),
    ("test_engine_tap", "smoke-test"),
    ("test_engine_turn", "smoke-test"),
    ("test_engine_verbose", "smoke-test"),
    ("test_jslb_vectors", "smoke-test"),
    ("test_mcp", "smoke-test"),
    ("test_page_build", "smoke-test"),
    ("test_page_build_node", "smoke-test"),
    ("test_page_build_tsc", "smoke-test"),
    ("test_tap_loop", "smoke-test"),
    ("test_ttyd_build", "smoke-test"),
    ("test_echo_loop", "smoke-test"),
    ("test_engine_mcp", "smoke-test"),
    ("test_engine_system", "smoke-test"),
    ("test_main_loop", "smoke-test"),
    ("test_mcp_stdio", "smoke-test"),
    ("test_bootstrap", "smoke-test"),
    ("test_bootstrap_dash", "smoke-test"),
    ("test_tap_pair", "smoke-test"),
    ("test_integrate_test_posix", "smoke-test"),
    ("test_integrate_dispatch", "smoke-test"),
    ("test_integrate_settings", "smoke-test"),
    ("test_integrate_vectors_make", "smoke-test"),
    ("test_integrate_engine_db", "smoke-test"),
    ("test_integrate_engine_doc", "smoke-test"),
    ("test_integrate_engine_kv", "smoke-test"),
    ("test_integrate_engine_sql", "smoke-test"),
    ("test_integrate_engine_tap", "smoke-test"),
    ("test_integrate_engine_turn", "smoke-test"),
    ("test_integrate_engine_verbose", "smoke-test"),
    ("test_integrate_mcp", "smoke-test"),
    ("test_integrate_page_build", "smoke-test"),
    ("test_integrate_tap_loop", "smoke-test"),
    ("test_integrate_echo_loop", "smoke-test"),
    ("test_integrate_engine_mcp", "smoke-test"),
    ("test_integrate_engine_system", "smoke-test"),
    ("test_integrate_main_loop", "smoke-test"),
    ("test_integrate_mcp_stdio", "smoke-test"),
    ("test_integrate_bootstrap", "smoke-test"),
    ("test_mcp_stdio_process", "smoke-test"),
    ("test_tap_tty", "smoke-test"),
]

# Group A's unit phase, the TypeScript blocks that run in Node, by layer.
_A_UNIT: list[tuple[str, str]] = [
    ("test_tap_producer.ts", "smoke-test"),
    ("test_unittest.ts", "smoke-test"),
    ("test_harness.ts", "smoke-test"),
    ("test_ui_strings.ts", "smoke-test"),
    ("test_i18n.ts", "smoke-test"),
    ("test_utility.ts", "smoke-test"),
    ("test_jslb.ts", "smoke-test"),
    ("test_settings.ts", "smoke-test"),
    ("test_dispatch.ts", "smoke-test"),
    ("test_http.ts", "smoke-test"),
    ("test_media.ts", "smoke-test"),
    ("test_provider.ts", "smoke-test"),
    ("test_provider_key.ts", "smoke-test"),
    ("test_provider_key_unset.ts", "smoke-test"),
    ("test_provider_script.ts", "smoke-test"),
    ("test_verbose.ts", "smoke-test"),
    ("test_wire.ts", "smoke-test"),
    ("test_queue.ts", "smoke-test"),
    ("test_substrate.ts", "smoke-test"),
    ("test_line_case.ts", "smoke-test"),
    ("test_mcp.ts", "smoke-test"),
    ("test_wire_port.ts", "smoke-test"),
]

# Group A's integration phase, its pair test first, which is a Python suite.
_A_INTEGRATION: list[tuple[str, str]] = [
    ("test_tap_pair_ts", "smoke-test"),
    ("test_integrate_queue.ts", "smoke-test"),
    ("test_integrate_http.ts", "smoke-test"),
    ("test_integrate_mcp.ts", "smoke-test"),
    ("test_integrate_provider_script.ts", "smoke-test"),
]

# Group B's unit phase, the TypeScript blocks of headless Chrome, by layer.
_B_UNIT: list[tuple[str, str]] = [
    ("test_error_overlay.ts", "smoke-test"),
    ("test_error_overlay_worker.ts", "smoke-test"),
    ("test_overlay.ts", "smoke-test"),
    ("test_substrate_store.ts", "smoke-test"),
    ("test_jslb_decode.ts", "smoke-test"),
    ("test_console_view.ts", "smoke-test"),
    ("test_media_cache.ts", "smoke-test"),
    ("test_script.ts", "smoke-test"),
    ("test_worker_ai.ts", "smoke-test"),
    ("test_page.ts", "smoke-test"),
    ("test_tools_browser.ts", "smoke-test"),
    ("test_agent.ts", "smoke-test"),
    ("test_boot.ts", "smoke-test"),
]

# Group B's integration phase, by the layer of each block.
_B_INTEGRATION: list[tuple[str, str]] = [
    ("test_integrate_substrate.ts", "smoke-test"),
    ("test_integrate_media.ts", "smoke-test"),
    ("test_integrate_worker_ai.ts", "smoke-test"),
    ("test_integrate_console_view.ts", "smoke-test"),
    ("test_substrate_crash.ts", "smoke-test"),
    ("test_integrate_page.ts", "smoke-test"),
    ("test_integrate_tools_browser.ts", "smoke-test"),
    ("test_agent_faults.ts", "smoke-test"),
    ("test_integrate_agent.ts", "smoke-test"),
]

# Group C's integration phase, the blocks whose page ttyd serves, by layer.
_C_INTEGRATION: list[tuple[str, str]] = [
    ("test_worker_ai_console.ts", "smoke-test"),
    ("test_wire_end.ts", "smoke-test"),
    ("test_tools_browser_console.ts", "smoke-test"),
    ("test_integrate_wire.ts", "smoke-test"),
]

# Every suite and block of a run, in the phases of the order above.
_PHASES = (
    _MODULES
    + _A_UNIT
    + _A_INTEGRATION
    + _B_UNIT
    + _B_INTEGRATION
    + _C_INTEGRATION
)

# The suites and blocks that fail by design, which only `--module` runs.
_FAILING: list[tuple[str, str]] = [
    ("failing_suite", "smoke-test"),
    ("failing_block.ts", "smoke-test"),
]

# The end of a TypeScript block's name, its file in `ts`. It counts for none.
_TS_SUFFIX = ".ts"

# The TypeScript blocks that a node realm runs, those of group A.
_NODE_BLOCKS = frozenset(
    name
    for name, _ in _A_UNIT + _A_INTEGRATION + _FAILING
    if name.endswith(_TS_SUFFIX)
)

# The TypeScript blocks that a page load runs, those of groups B and C.
_CHROME_BLOCKS = frozenset(
    name for name, _ in _B_UNIT + _B_INTEGRATION + _C_INTEGRATION
)

# The TypeScript blocks whose page ttyd serves, each on a root of its own.
_TTYD_BLOCKS = frozenset(name for name, _ in _C_INTEGRATION)

# The gold id of the script of the local HTTP server, by each block it serves.
_SERVED: dict[str, str] = {
    "test_integrate_http.ts": "typescript.test_integrate_http.server",
    "test_integrate_media.ts": "typescript.test_integrate_media.server",
    "test_integrate_page.ts": "typescript.test_integrate_page.server",
}

# The gold id of the headless realm's own: its window, its page's server.
_HEADLESS_ID = "typescript.test_headless"

# The template of the headless page, and its name in `build`.
_PAGE_NAME = "headless"

# The headless page's path on the local HTTP server, which serves `build`.
_PAGE_PATH = f"/build/{_PAGE_NAME}.html"

# The headless page in `build`, which ttyd serves a block of C as its index.
_INDEX_PATH = os.path.join(_BUILD_PATH, f"{_PAGE_NAME}.html")

# The gold id of the seconds ttyd has to stop after SIGTERM.
_STOP_ID = f"{_HEADLESS_ID}.stop_seconds"

# The key of a block's gold under which its root's gold is.
_ROOT_KEY = "root"

# The key of a root's gold that names a main loop file of `python`.
_LOOP_KEY = "main_loop"

# A root's directories: its modules and seed, its strings, its main loop.
_ROOT_PYTHON = "python"
_ROOT_STRINGS = "i18n"
_ROOT_LOOPS = "main_loop"

# The seed of `python`, which a root holds beside its modules.
_SEED_NAME = "seed"

# The strings, which a root holds where the checkout does.
_STRINGS_PATH = os.path.join(_ROOT_PATH, _ROOT_STRINGS, "en-US.json")

# The program that runs the server's bootstrap, the command ttyd runs.
_PYTHON_PROGRAM = "python3"

# ttyd's first log line, with its version and that of libwebsockets.
_VERSION_PATTERN = re.compile(
    r" N: (ttyd \S+ \(libwebsockets \S+\))$", re.MULTILINE
)

# ttyd's log line of the port it listens on.
_PORT_PATTERN = re.compile(r" N:  Listening on port: (\d+)$", re.MULTILINE)

# The wait between two reads of ttyd's log for its port, its writer's.
_POLL_SECONDS = 0.01

# What ttyd's log lines are written after in a block's log.
_TTYD_SOURCE = "ttyd"

# The binding through which the headless realm sends each of its lines.
_BINDING_NAME = "realm_line"

# The page whose load ends a realm, its page and its worker.
_BLANK_URL = "about:blank"

# The push that carries a worker block's verbose entries.
_VERBOSE_TYPE = "verbose.put"

# The push a worker block sends toward the UI thread, which none takes there.
_NOTICE_TYPE = "settings.set"

# What the page's console messages are written after in a block's log.
_CONSOLE_SOURCE = "console"

# The program that runs a realm.
_NODE_PROGRAM = "node"

# The option that ends a realm's stream at its first failing test.
_FAILFAST_OPTION = "--failfast"

# The type of the first line a realm takes, `tap.start`.
_FIRST_TYPE = "tap.start"

# The fixed id of `tap.start`.
_FIRST_ID = 101

# The fields of the header of the Empty reply to `tap.start`.
_REPLY_FIELDS = 2

# The type of the push that carries each line of a realm's TAP stream.
_LINE_TYPE = "tap.line"

# The language of a realm's TAP lines.
_LANGUAGE = "typescript"

# The most bytes read from a realm's stdout at once.
_READ_BYTES = 65536

# The later suites, each with what it waits on, which no run takes.
_LATER: list[tuple[str, str]] = [
    (
        "test_devtools_powershell",
        "offline since 2026-10-30, kept, run by nothing, and to be brought"
        " back later; then powershell.exe, and Chrome or Edge",
    ),
    ("test_reformat_formatters", "ruff, shfmt and prettier"),
    ("test_test_posix_formatters", "ruff"),
]

# A suite's `--coverage` modules past its namesake, none for stdio, pair tests.
_COUNTED: dict[str, tuple[str, ...]] = {
    "failing_suite": (),
    "test_bootstrap_dash": ("bootstrap",),
    "test_devtools_chrome": ("devtools",),
    "test_devtools_powershell": ("devtools",),
    "test_jslb_vectors": ("jslb",),
    "test_mcp_stdio_process": (),
    "test_page_build_node": ("page_build",),
    "test_page_build_tsc": ("page_build",),
    "test_reformat_formatters": ("reformat",),
    "test_tap_pair": (),
    "test_tap_pair_ts": (),
    "test_tap_tty": (),
    "test_test": ("harness", "category"),
    "test_test_posix_formatters": ("test_posix",),
}

# The start of the name of each integration suite, which counts for none.
_INTEGRATE_PREFIX = "test_integrate_"

# The start of the name of each unit suite, before its module's name.
_TEST_PREFIX = "test_"

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# Reads each TAP line with the TAP consumer, then writes it to stdout at once.
class StreamWriter:
    # Starts before the stream of the suites named, in the order they run.
    def __init__(self, names: list[str]) -> None:
        import tap_consumer

        self.reader = tap_consumer.StreamReader()
        self._parser = tap_consumer.Parser()
        self._names = names
        self._blocks = 0
        self._place = "before the first block"

    # Prints the line, flushed, raising first unless it fits, naming its block.
    def line_write(self, text: str) -> None:
        import tap_consumer

        line = self._parser.parse_line(text)
        if not self.reader.line_read(line):
            raise RuntimeError(
                f"the TAP line {text!r} {self._place} does not fit the stream"
            )
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
        # A block's plan line opens it, and its parent line closes it.
        if isinstance(line, tap_consumer.Plan) and line.depth == 1:
            self._place = f"in the block of {self._names[self._blocks]}"
        elif isinstance(line, tap_consumer.Result) and line.depth == 0:
            self._place = f"after the block of {self._names[self._blocks]}"
            self._blocks += 1


# Imports the module and returns its tests.
def suite_load(loader: unittest.TestLoader, name: str) -> unittest.TestSuite:
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

    listed = _PHASES + _FAILING if named else _PHASES
    labels = dict(listed)
    for name in named:
        if named.count(name) > 1:
            parser.error(f"--module {name} is given more than once")
        if not category.suite_runs(labels[name], chosen):
            parser.error(f"--module {name} is not a suite of a {chosen} run")
    return [
        (name, label)
        for name, label in listed
        if category.suite_runs(label, chosen) and (not named or name in named)
    ]


# The paths of the modules whose lines a suite counts for under `--coverage`.
def paths_counted(name: str) -> list[str]:
    if name in _COUNTED:
        modules = _COUNTED[name]
    elif name.startswith(_INTEGRATE_PREFIX) or name.endswith(_TS_SUFFIX):
        modules = ()
    else:
        modules = (name.removeprefix(_TEST_PREFIX),)
    return [os.path.join(_PYTHON_PATH, module + ".py") for module in modules]


# After suite `index` passes, checks its modules no later suite counts for.
def coverage_check(
    count: line_coverage.LineCount,
    modules: list[tuple[str, str]],
    index: int,
) -> None:
    later = {
        path
        for name, _ in modules[index + 1 :]
        for path in paths_counted(name)
    }
    for path in paths_counted(modules[index][0]):
        if path not in later:
            count.lines_check(path)


# Refuses a blob, as a realm sends none.
def sink_refuse(header: jslb.Object) -> NoReturn:
    import jslb

    size = jslb.field_get(header, "size")
    raise RuntimeError(f"a realm sent a blob of {size} bytes")


# Builds `tap.start` as the engine's start builds it, and returns its settings.
def start_encode() -> tuple[bytes, dict[str, Any]]:
    import jslb, settings

    loaded = settings.settings_load(_SETTINGS_PATH)
    with open(_TESTS_PATH, encoding="utf-8") as file:
        tests: object = jslb.json_decode(file.read())
    header = jslb.header_make(_FIRST_TYPE, id=_FIRST_ID, full=loaded["debug"])
    line = jslb.line_make(header, [], settings=loaded, test_settings=tests)
    # The JSON text bytes, the one piece the encoder yields with no blob.
    (piece,) = jslb.line_encode(line)
    return cast(bytes, piece), loaded


# Raises unless the line is the Empty reply to `tap.start`.
def reply_check(line: jslb.Object) -> None:
    import jslb

    header: jslb.Object = line[0]
    reply = jslb.field_get(header, "reply")
    if (
        len(header) != _REPLY_FIELDS
        or jslb.field_get(header, "type") != _FIRST_TYPE
        or type(reply) is not int
        or reply != _FIRST_ID
        or len(jslb.payload_of(line)) > 0
    ):
        raise RuntimeError(
            f"the realm wrote {jslb.line_render(line)}, not the Empty reply"
            f" to {_FIRST_ID}"
        )


# Feeds the text of a `tap.line` to the relay, refusing any other line.
def line_relay(runner: tap_producer.TAPTestRunner, line: jslb.Object) -> str:
    import jslb

    header: jslb.Object = line[0]
    payload = jslb.payload_of(line)
    if (
        jslb.field_get(header, "type") != _LINE_TYPE
        or jslb.field_get(header, "id") is not None
        or jslb.field_get(header, "reply") is not None
        or payload.get("language") != _LANGUAGE
    ):
        raise RuntimeError(
            f"the realm wrote {jslb.line_render(line)}, not a"
            f" {_LINE_TYPE} of {_LANGUAGE}"
        )
    text: str = payload["text"]
    runner.relay_feed(text)
    return text


# The local HTTP servers of the run, by the gold id of each one's script.
class ServerPool:
    # Holds no server yet.
    def __init__(self) -> None:
        self._servers: dict[str, local_http.LocalServer] = {}

    # Starts the server of the gold's script, unless it is serving already.
    def server_need(self, script: str) -> None:
        import harness, local_http

        if script not in self._servers:
            self._servers[script] = local_http.LocalServer(
                harness.gold_get(script), _BUILD_PATH
            )

    # Stops each server started, once the stream has ended.
    def servers_stop(self) -> None:
        for server in self._servers.values():
            server.server_stop()


# Runs each TypeScript block of group A in a node realm of its own.
class RealmRunner:
    # Holds no bundle or `tap.start` yet: each is made at first need.
    def __init__(
        self,
        runner: tap_producer.TAPTestRunner,
        reader: tap_consumer.StreamReader,
        servers: ServerPool,
    ) -> None:
        self._runner = runner
        self._reader = reader
        self._servers = servers
        self._bundle: str | None = None
        self._start = b""
        self._settings: dict[str, Any] = {}

    # Builds the bundle and `tap.start` once, and starts the block's server.
    def block_prepare(
        self, name: str, limit: float | None, started: float
    ) -> None:
        import category, page_build

        if self._bundle is None:
            what = "the Node bundle"
            elapsed = time.monotonic() - started
            timer_start(category.alarm_plan(what, None, limit, elapsed))
            self._bundle = page_build.node_build(_BUILD_PATH)
            timer_stop()
            self._start, self._settings = start_encode()
        if name in _SERVED:
            self._servers.server_need(_SERVED[name])

    # Runs the block in a realm, relaying its stream, the realm killed after.
    def block_run(self, name: str) -> None:
        block = name.removesuffix(_TS_SUFFIX)
        command = [_NODE_PROGRAM, cast(str, self._bundle), block]
        if self._runner.failfast:
            command.append(_FAILFAST_OPTION)
        self._runner.block_relay(block, self._reader)
        with (
            tempfile.TemporaryFile(dir=_BUILD_PATH) as errors,
            subprocess.Popen(
                command,
                bufsize=0,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
            ) as realm,
        ):
            try:
                self.realm_serve(realm)
            except Exception as error:
                realm.kill()
                realm.wait()
                errors.seek(0)
                cause = RuntimeError(
                    "the realm's stderr:\n" + errors.read().decode("utf-8")
                )
                cause.__cause__ = error
                raise RuntimeError(
                    f"the realm of {name} failed: {error}"
                ) from cause
            finally:
                realm.kill()

    # Writes `tap.start`, relays the realm's stream, then checks its exit.
    def realm_serve(self, realm: subprocess.Popen[bytes]) -> None:
        import jslb

        stdin = cast(IO[bytes], realm.stdin)
        view = memoryview(self._start)
        while view:
            view = view[stdin.write(view) :]
        stdin.close()
        loaded = self._settings
        decoder = jslb.LineDecoder(
            loaded["line_max"],
            loaded["blob_max"],
            loaded["overflow_bytes"],
            sink_refuse,
        )
        output = cast(IO[bytes], realm.stdout).fileno()
        replied = False
        while data := os.read(output, _READ_BYTES):
            # Feeding nothing raises at once a fault the decoder held back.
            for piece in (data, b""):
                for line in decoder.bytes_feed(piece):
                    if replied:
                        line_relay(self._runner, line)
                    else:
                        reply_check(line)
                        replied = True
        if not decoder.idle():
            raise EOFError("the realm's stdout ended in a line")
        code = realm.wait()
        if code != 0:
            raise RuntimeError(f"the realm exited with {code}")
        self._runner.relay_end()


# The lane of one block's realm in a page: its lines, its log, where it stands.
class PageLane:
    # Starts before the Empty reply, the realm's log written to `log` at once.
    def __init__(
        self,
        runner: tap_producer.TAPTestRunner,
        loaded: dict[str, Any],
        log: IO[bytes],
    ) -> None:
        import jslb, tap_consumer

        self._runner = runner
        self._log = log
        self._decoder = jslb.LineDecoder(
            loaded["line_max"],
            loaded["blob_max"],
            loaded["overflow_bytes"],
            sink_refuse,
        )
        self._parser = tap_consumer.Parser()
        self._replied = False
        self.ended = False
        self.calls = 0

    # Writes one text of the realm's log, after what it came from.
    def log_write(self, source: str, text: str) -> None:
        self._log.write(f"{source}: {text}\n".encode("utf-8"))

    # Takes one call of the binding, the base64 of the realm's bytes.
    def text_take(self, text: str) -> None:
        data = base64.b64decode(text, validate=True)
        # Feeding nothing raises at once a fault the decoder held back.
        for piece in (data, b""):
            for line in self._decoder.bytes_feed(piece):
                self.line_take(line)
        self.calls += 1

    # Logs a verbose entry, relays a TAP line, and refuses any other line.
    def line_take(self, line: jslb.Object) -> None:
        import jslb, tap_consumer

        kind = jslb.field_get(line[0], "type")
        # The notice of the settings is the UI thread's, which no block runs.
        if kind == _NOTICE_TYPE:
            return
        if kind == _VERBOSE_TYPE:
            payload = jslb.payload_of(line)
            for entry in payload["lines"]:
                self.log_write(payload["thread"], entry["text"])
        elif not self._replied:
            reply_check(line)
            self._replied = True
        elif self.ended:
            raise RuntimeError(
                f"the realm wrote {jslb.line_render(line)} after its stream"
                " ended"
            )
        else:
            parsed = self._parser.parse_line(line_relay(self._runner, line))
            self.ended = (
                isinstance(parsed, (tap_consumer.Plan, tap_consumer.Bail))
                and parsed.depth == 0
            )

    # Raises unless the realm's lines ended between two lines.
    def end_check(self) -> None:
        if not self._decoder.idle():
            raise EOFError("the realm's lines ended in a line")


# One block's root in `build`, as the start script makes one, and its ttyd.
class RootServer:
    # Makes the root, starts ttyd on it, and reads ttyd's version and port.
    def __init__(self, name: str, ttyd: str, loaded: dict[str, Any]) -> None:
        import harness

        block = name.removesuffix(_TS_SUFFIX)
        gold_id = f"{_LANGUAGE}.{block}.{_ROOT_KEY}"
        gold: dict[str, Any] = harness.gold_get(gold_id)
        self._stop_seconds = float(harness.gold_get(_STOP_ID))
        powershell: dict[str, Any] = loaded["powershell"]
        self.version = ttyd
        self._host: str = powershell["bind_address"]
        self._port = 0
        self._process: subprocess.Popen[bytes] | None = None
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self._log = tempfile.TemporaryFile(dir=_BUILD_PATH, buffering=0)
        self.root = tempfile.mkdtemp(prefix=f"root-{block}-", dir=_BUILD_PATH)
        try:
            command = self.root_make(gold, loaded)
            self._process = subprocess.Popen(
                [
                    ttyd,
                    "--port",
                    "0",
                    "--interface",
                    self._host,
                    "--writable",
                    "--check-origin",
                    "--terminal-type",
                    powershell["terminal_type"],
                    "--url-arg",
                    f"--srv-buf-size={loaded['srv_buf_size']}",
                    "--index",
                    _INDEX_PATH,
                    *command,
                ],
                stdin=subprocess.DEVNULL,
                stdout=self._log,
                stderr=self._log,
                start_new_session=True,
            )
            self.version, self._port = self.start_read(self._process)
        except BaseException:
            self.server_stop(stderr_write)
            raise

    # Writes the root's files, and returns the command ttyd runs on it.
    def root_make(
        self, gold: dict[str, Any], loaded: dict[str, Any]
    ) -> list[str]:
        powershell: dict[str, Any] = loaded["powershell"]
        python_path = os.path.join(self.root, _ROOT_PYTHON)
        os.makedirs(python_path)
        for module in powershell["runtime_modules"]:
            file_name = f"{module}.py"
            shutil.copyfile(
                os.path.join(_PYTHON_PATH, file_name),
                os.path.join(python_path, file_name),
            )
        shutil.copytree(
            os.path.join(_PYTHON_PATH, _SEED_NAME),
            os.path.join(python_path, _SEED_NAME),
        )
        strings_path = os.path.join(self.root, _ROOT_STRINGS)
        os.makedirs(strings_path)
        shutil.copyfile(
            _STRINGS_PATH,
            os.path.join(strings_path, os.path.basename(_STRINGS_PATH)),
        )
        settings_path = os.path.basename(_SETTINGS_PATH)
        with open(
            os.path.join(self.root, settings_path), "w", encoding="utf-8"
        ) as file:
            values = {**loaded, "debug": True}
            file.write(json.dumps(values, ensure_ascii=False, indent=2) + "\n")
        shutil.copyfile(
            _TESTS_PATH, os.path.join(self.root, os.path.basename(_TESTS_PATH))
        )
        bootstrap = os.path.join(python_path, powershell["bootstrap_script"])
        command = [_PYTHON_PROGRAM, bootstrap, "--root", self.root]
        if _LOOP_KEY in gold:
            loop: str = gold[_LOOP_KEY]
            loops_path = os.path.join(self.root, _ROOT_LOOPS)
            os.makedirs(loops_path)
            shutil.copyfile(
                os.path.join(_PYTHON_PATH, loop),
                os.path.join(loops_path, loop),
            )
            command += ["--main-loop", loop]
        return command

    # The text of ttyd's log so far, read with no move of its offset.
    def log_text(self) -> str:
        descriptor = self._log.fileno()
        size = os.fstat(descriptor).st_size
        return os.pread(descriptor, size, 0).decode("utf-8")

    # Reads ttyd's version and port from its log, failing if it ends first.
    def start_read(self, process: subprocess.Popen[bytes]) -> tuple[str, int]:
        while True:
            code = process.poll()
            text = self.log_text()
            version = _VERSION_PATTERN.search(text)
            port = _PORT_PATTERN.search(text)
            if version is not None and port is not None:
                return version.group(1), int(port.group(1))
            if code is not None:
                raise RuntimeError(
                    f"{self.version} exited with {code} before it listened"
                ) from RuntimeError(f"ttyd's log:\n{text}")
            time.sleep(_POLL_SECONDS)

    # The page's address on this ttyd.
    def url_get(self) -> str:
        return f"http://{self._host}:{self._port}/"

    # Stops ttyd's group, writes its log, removes the root, returns a failure.
    def server_stop(self, write: Callable[[str, str], None]) -> str | None:
        process = self._process
        failure: str | None = None
        try:
            if process is not None:
                code = process.poll()
                if code is not None:
                    failure = (
                        f"{self.version} exited with {code} before its stop"
                    )
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                    seconds = self._stop_seconds
                    try:
                        process.wait(seconds)
                    except subprocess.TimeoutExpired:
                        failure = (
                            f"{self.version} still ran {seconds:g} s after"
                            " SIGTERM and was killed"
                        )
        finally:
            try:
                # A stop cut short, as by an alarm, kills the group too.
                if process is not None and process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                for text in self.log_text().splitlines():
                    write(_TTYD_SOURCE, text)
                if failure is not None:
                    write(_TTYD_SOURCE, failure)
            finally:
                self._log.close()
                shutil.rmtree(self.root)
        return failure


# Runs each TypeScript block of groups B and C in a page load of its own.
class PageRunner:
    # Holds no page, browser or `tap.start` yet: each is made at first need.
    def __init__(
        self,
        runner: tap_producer.TAPTestRunner,
        reader: tap_consumer.StreamReader,
        servers: ServerPool,
        ttyd: str,
    ) -> None:
        self._runner = runner
        self._reader = reader
        self._servers = servers
        self._ttyd = ttyd
        self._stack = contextlib.ExitStack()
        self._browser: devtools.Browser | None = None
        self._line = ""
        self._settings: dict[str, Any] = {}
        self._lane: PageLane | None = None
        self._root: RootServer | None = None

    # Builds the page, `tap.start` and the browser once, then a server or root.
    def block_prepare(
        self, name: str, limit: float | None, started: float
    ) -> None:
        import category, devtools, harness, page_build

        if self._browser is None:
            what = "the headless page and the browser"
            elapsed = time.monotonic() - started
            timer_start(category.alarm_plan(what, None, limit, elapsed))
            page_build.page_build(_PAGE_NAME, _PAGE_NAME)
            start, self._settings = start_encode()
            self._line = base64.b64encode(start).decode("ascii")
            browser = self._stack.enter_context(
                devtools.Browser(
                    harness.gold_get(f"{_HEADLESS_ID}.window_width"),
                    harness.gold_get(f"{_HEADLESS_ID}.window_height"),
                    devtools.LinuxPipe(),
                )
            )
            browser.console_follow(self.console_take)
            browser.binding_add(_BINDING_NAME, self.binding_call)
            self._browser = browser
            timer_stop()
        if name in _TTYD_BLOCKS:
            what = f"the root and ttyd of {name}"
            elapsed = time.monotonic() - started
            timer_start(category.alarm_plan(what, None, limit, elapsed))
            self._root = RootServer(name, self._ttyd, self._settings)
            timer_stop()
        else:
            self._servers.server_need(page_script(name))

    # Runs the block in a fresh page load, relaying its stream, then ends it.
    def block_run(
        self, name: str, end: float, limit: float | None, started: float
    ) -> None:
        import harness

        block = name.removesuffix(_TS_SUFFIX)
        browser = cast("devtools.Browser", self._browser)
        root: RootServer | None = None
        if name in _TTYD_BLOCKS:
            root = cast(RootServer, self._root)
            self._root = None
            url = root.url_get()
        else:
            script = harness.gold_get(page_script(name))
            url = f"http://{script['host']}:{script['port']}{_PAGE_PATH}"
        call = (
            f"test_headless.realm_start({json.dumps(block)},"
            f" {json.dumps(self._runner.failfast)}, {json.dumps(self._line)})"
        )
        self._runner.block_relay(block, self._reader)
        with tempfile.TemporaryFile(dir=_BUILD_PATH, buffering=0) as log:
            lane = PageLane(self._runner, self._settings, log)
            self._lane = lane
            try:
                try:
                    client = browser.client_get()
                    # The end of the block's timer ends each of its waits.
                    client.limit_set(end)
                    browser.page_open(url)
                    browser.script_evaluate(call)
                    # A wait for each next line, the block's timer over all.
                    while not lane.ended:
                        calls = lane.calls
                        client.events_pump(
                            f"the next line of the realm of {name}",
                            lambda: lane.calls > calls,
                        )
                    browser.page_open(_BLANK_URL)
                    lane.end_check()
                except BaseException:
                    # The root of a failed block stops too, its failure kept.
                    if root is not None:
                        root.server_stop(lane.log_write)
                    raise
                if root is not None:
                    root_stop(name, root, lane, limit, started)
            except Exception as error:
                log.seek(0)
                cause = RuntimeError(
                    "the realm's log:\n" + log.read().decode("utf-8")
                )
                cause.__cause__ = error
                raise RuntimeError(
                    f"the realm of {name} failed: {error}"
                ) from cause
            finally:
                self._lane = None
        self._runner.relay_end()

    # Gives the payload of a call of the binding to the running block's lane.
    def binding_call(self, text: str) -> None:
        self.lane_get().text_take(text)

    # Writes a message of the page's console to the running block's log.
    def console_take(self, text: str) -> None:
        self.lane_get().log_write(_CONSOLE_SOURCE, text)

    # The lane of the block running, raising when none is.
    def lane_get(self) -> PageLane:
        if self._lane is None:
            raise RuntimeError(
                "the page spoke while no block of B or C was running"
            )
        return self._lane

    # Stops a root no block ran on, then the browser, once the stream ended.
    def browser_stop(self) -> None:
        root = self._root
        self._root = None
        try:
            if root is not None:
                root.server_stop(stderr_write)
        finally:
            self._stack.close()


# Stops a passing block's root outside its timer, inside the deadline.
def root_stop(
    name: str,
    root: RootServer,
    lane: PageLane,
    limit: float | None,
    started: float,
) -> None:
    import category

    timer_stop()
    failure: str | None = None
    try:
        what = f"the stop of the root of {name}"
        elapsed = time.monotonic() - started
        timer_start(category.alarm_plan(what, None, limit, elapsed))
    finally:
        failure = root.server_stop(lane.log_write)
    if failure is not None:
        raise RuntimeError(failure)


# Writes one text of a log to stderr, after what it came from.
def stderr_write(source: str, text: str) -> None:
    sys.stderr.write(f"{source}: {text}\n")
    sys.stderr.flush()


# The gold id of the script of the server of a B block's page.
def page_script(name: str) -> str:
    if name in _SERVED:
        return _SERVED[name]
    return f"{_HEADLESS_ID}.server"


# Runs the suites and blocks here, one timed block each, to the first failing.
def stream_run(
    stream: StreamWriter,
    modules: list[tuple[str, str]],
    failfast: bool,
    limit: float | None,
    started: float,
    count: line_coverage.LineCount | None,
    ttyd: str,
) -> None:
    import category, harness, tap_producer

    module_seconds = float(harness.gold_get("module_seconds"))
    runner = tap_producer.TAPTestRunner(failfast or limit is not None)
    runner.set_stream(stream.line_write)
    loader = unittest.TestLoader()
    servers = ServerPool()
    realms = RealmRunner(runner, stream.reader, servers)
    pages = PageRunner(runner, stream.reader, servers, ttyd)
    try:
        for index, (name, label) in enumerate(modules):
            failed = stream.reader.failed
            realm = name in _NODE_BLOCKS
            page = name in _CHROME_BLOCKS
            if realm:
                realms.block_prepare(name, limit, started)
            elif page:
                pages.block_prepare(name, limit, started)
            begun = time.monotonic()
            what = f"block {name}" if realm or page else f"module {name}"
            plan = category.alarm_plan(
                what, module_seconds, limit, begun - started
            )
            timer_start(plan)
            if count is not None:
                count.suite_enter(paths_counted(name))
            if realm:
                realms.block_run(name)
            elif page:
                # A block has seconds of its own, so its alarm has a plan.
                seconds, _ = cast(tuple[float, str], plan)
                pages.block_run(name, begun + seconds, limit, started)
            else:
                load = functools.partial(suite_load, loader, name)
                runner.module_run(name, load)
            if count is not None:
                count.suite_leave()
            timer_stop()
            seconds = time.monotonic() - begun
            sys.stderr.write(f"{name}: {label}, {seconds:.3f} s\n")
            sys.stderr.flush()
            # The consumer's count, not the producer's verdict, stops the run.
            if stream.reader.failed > failed:
                break
            if count is not None:
                coverage_check(count, modules, index)
        runner.run_end()
    finally:
        try:
            pages.browser_stop()
        finally:
            servers.servers_stop()


# Runs the suites on the TAP suite server over a pty, relaying its stream.
def stream_relay(
    stream: StreamWriter,
    modules: list[tuple[str, str]],
    chosen: str,
    failfast: bool,
    failures: int,
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
            root, chosen, failfast, failures, names, stream.line_write
        )
    timer_stop()
    sys.stderr.write(errors)
    sys.stderr.flush()
    return code


# Runs the modules of the category, checks the stream, then runs the rest.
def main(arguments: list[str]) -> int:
    import line_coverage

    # With `--coverage`, counting precedes project imports, so that they count.
    count = line_coverage.LineCount() if "--coverage" in arguments else None
    import category

    parser = argparse.ArgumentParser(
        description="Run the suites of a category: the Python test modules"
        " and the TypeScript blocks in the testing order, the tests of the TAP"
        " modules first, as one"
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
        choices=[name for name, _ in _PHASES + _FAILING],
        help="run only this suite, or this TypeScript block named by its file"
        " in ts; given once for each to run",
    )
    parser.add_argument(
        "--failures",
        type=int,
        default=0,
        help="the failing tests the run expects: it passes only when"
        " exactly this many fail",
    )
    parser.add_argument(
        "--tty",
        action="store_true",
        help="run the stream on a pty through bootstrap.py and the TAP suite"
        " server, tap_loop.py, writing each line it relays",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="count the lines run, and fail after a unit suite's block at the"
        " first line of its modules never counted as run",
    )
    category.options_add(parser)
    parsed = parser.parse_args(arguments)
    failfast: bool = parsed.failfast
    chosen: str = parsed.category
    failures: int = parsed.failures
    if failures < 0:
        parser.error(f"--failures {failures} is below 0")
    if count is not None and parsed.tty:
        parser.error(
            "--coverage counts the lines run in this process, and --tty runs"
            " the stream in another"
        )
    modules = modules_chosen(parser, parsed.module, chosen)
    import third_party_fetch, ttyd_build

    # Bring up: the pins and ttyd are in place before the first block's timer.
    third_party_fetch.pins_fetch()
    ttyd = ttyd_build.checkout_build()
    started = time.monotonic()
    limit = category.limit_seconds(chosen)
    stream = StreamWriter([name for name, _ in modules])
    code: int | None = None
    if parsed.tty:
        code = stream_relay(
            stream, modules, chosen, failfast, failures, limit, started
        )
    else:
        stream_run(stream, modules, failfast, limit, started, count, ttyd)
        if count is not None:
            count.count_stop()
    reader = stream.reader
    if not reader.stream_ended():
        raise RuntimeError(
            "the TAP stream did not end with its parent plan or a bail out"
        )
    verdict = 0 if reader.failed == failures else 1
    if code is not None and code != verdict:
        raise RuntimeError(
            f"test_all.py on the tty exited with {code}, though its stream"
            f" holds {reader.failed} failures of {failures} expected"
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
