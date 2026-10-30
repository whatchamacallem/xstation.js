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
#
# The suites run in strict dependency order, in five phases that only the
# order of the lists shows. Three are of Python: the unit suites,
# test_<module>.py, by layer; then the pair test of the TAP producer and
# consumer, test_tap_pair.py, and the integration suites,
# test_integrate_<module>.py, by the layer of their module; then the stdio
# suites, which start bootstrap.py or mcp_stdio.py as a program and talk to
# it over its stdio, by layer. Two are of group A, the TypeScript blocks run
# in Node: the unit blocks, test_<module>.ts, by layer; then the pair test
# of the TypeScript TAP producer and the Python consumer, test_tap_pair_ts.py,
# and the integration blocks, test_integrate_<module>.ts, by the layer of
# their block. A module calls into another when it imports it, at the top
# or in a function, loads its file, runs it as a program, or has it run
# inside the block of its suite, as this file has the TAP producer and
# consumer in every block; a call of a function it was handed is no call
# into the module that handed it over. A suite runs only after the suites of
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

import argparse, functools, importlib, os, signal, subprocess, sys, tempfile
import time, types, unittest
from typing import Any, IO, NoReturn, TYPE_CHECKING, cast

# Only type checks import these here, and `main` imports `line_coverage` first.
if TYPE_CHECKING:
    import jslb, line_coverage, local_http, tap_consumer, tap_producer

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
    ("test_tap_loop", "smoke-test"),
    ("test_echo_loop", "smoke-test"),
    ("test_engine_mcp", "smoke-test"),
    ("test_engine_system", "smoke-test"),
    ("test_main_loop", "smoke-test"),
    ("test_mcp_stdio", "smoke-test"),
    ("test_bootstrap", "smoke-test"),
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

# Every suite and block of a run, in the phases of the order above.
_PHASES = _MODULES + _A_UNIT + _A_INTEGRATION

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

# The gold id of the script of the local HTTP server, by each block it serves.
_SERVED: dict[str, str] = {
    "test_integrate_http.ts": "typescript.test_integrate_http.server",
}

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
    ("test_bootstrap_dash", "dash"),
    ("test_devtools_powershell", "powershell.exe, and Chrome or Edge"),
    ("test_page_build_tsc", "the archives of third_party_fetch.py"),
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


# Runs each TypeScript block of group A in a node realm of its own.
class RealmRunner:
    # Holds no bundle, `tap.start` or server yet: each is made at first need.
    def __init__(
        self,
        runner: tap_producer.TAPTestRunner,
        reader: tap_consumer.StreamReader,
    ) -> None:
        self._runner = runner
        self._reader = reader
        self._bundle: str | None = None
        self._start = b""
        self._settings: dict[str, Any] = {}
        self._servers: dict[str, local_http.LocalServer] = {}

    # Builds the bundle and `tap.start` once, and starts the block's server.
    def block_prepare(
        self, name: str, limit: float | None, started: float
    ) -> None:
        import category, harness, local_http, page_build

        if self._bundle is None:
            what = "the Node bundle"
            elapsed = time.monotonic() - started
            timer_start(category.alarm_plan(what, None, limit, elapsed))
            self._bundle = page_build.node_build(_BUILD_PATH)
            timer_stop()
            self._start, self._settings = start_encode()
        script = _SERVED.get(name)
        if script is not None and script not in self._servers:
            self._servers[script] = local_http.LocalServer(
                harness.gold_get(script), _BUILD_PATH
            )

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
                        self.line_relay(line)
                    else:
                        reply_check(line)
                        replied = True
        if not decoder.idle():
            raise EOFError("the realm's stdout ended in a line")
        code = realm.wait()
        if code != 0:
            raise RuntimeError(f"the realm exited with {code}")
        self._runner.relay_end()

    # Feeds the text of a `tap.line` to the relay, refusing any other line.
    def line_relay(self, line: jslb.Object) -> None:
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
        self._runner.relay_feed(payload["text"])

    # Stops each server started, once the stream has ended.
    def servers_stop(self) -> None:
        for server in self._servers.values():
            server.server_stop()


# Runs the suites and blocks here, one timed block each, to the first failing.
def stream_run(
    stream: StreamWriter,
    modules: list[tuple[str, str]],
    failfast: bool,
    limit: float | None,
    started: float,
    count: line_coverage.LineCount | None,
) -> None:
    import category, harness, tap_producer

    module_seconds = float(harness.gold_get("module_seconds"))
    runner = tap_producer.TAPTestRunner(failfast or limit is not None)
    runner.set_stream(stream.line_write)
    loader = unittest.TestLoader()
    realms = RealmRunner(runner, stream.reader)
    try:
        for index, (name, label) in enumerate(modules):
            failed = stream.reader.failed
            realm = name in _NODE_BLOCKS
            if realm:
                realms.block_prepare(name, limit, started)
            begun = time.monotonic()
            what = f"block {name}" if realm else f"module {name}"
            timer_start(
                category.alarm_plan(
                    what, module_seconds, limit, begun - started
                )
            )
            if count is not None:
                count.suite_enter(paths_counted(name))
            if realm:
                realms.block_run(name)
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
        realms.servers_stop()


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
    started = time.monotonic()
    limit = category.limit_seconds(chosen)
    stream = StreamWriter([name for name, _ in modules])
    code: int | None = None
    if parsed.tty:
        code = stream_relay(
            stream, modules, chosen, failfast, failures, limit, started
        )
    else:
        stream_run(stream, modules, failfast, limit, started, count)
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
