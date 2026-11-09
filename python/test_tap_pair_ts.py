# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP producer of TypeScript and the TAP consumer of Python as a
# pair: the consumer validates each stream the TypeScript producer writes, and
# counts it as the TypeScript unittest's own result counts the same tests. node
# runs the pair block once, on real pipes. The oracle is the
# unittest.TestResult of each block that ran, its counts carried in the run's
# `tap.pair` push: a failure, an error and an unexpected success each fail one
# test, a skip skips one, and every other test run passed, an expected failure
# among them, since no fixture has two outcomes in one test. A bail out counts
# for nothing, since the producer writes one only after a failed point, where
# the consumer counts none.

import harness, jslb, os, page_build, shutil, subprocess, switches
import tap_consumer, time, unittest
from typing import Any, NamedTuple, NoReturn, cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The build directory, where the Node bundle is built.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The block the realm runs, which writes the pair runs.
_BLOCK = "test_tap_pair"

# The type of the first line.
_FIRST_TYPE = "tap.start"

# The fixed id of the first line.
_FIRST_ID = 101

# The type of each line of the realm's own stream.
_LINE_TYPE = "tap.line"

# The language each line of the realm's own stream names.
_LANGUAGE = "typescript"

# The type of the push that carries one run of the fixtures.
_PAIR_TYPE = "tap.pair"

# What starts the parent point's duration line, before its value.
_DURATION_PREFIX = "  duration_ms: "

# Half the last digit a duration is written with, which rounding may add.
_HALF_DIGIT = 0.05

# The milliseconds in a second.
_MILLISECONDS = 1000


# The oracle of one block of a run: its verdict and its unittest counts.
class PairBlock(NamedTuple):
    module: str
    passed: bool
    cases: int
    tests_run: int
    failures: int
    errors: int
    skipped: int
    expected_failures: int
    unexpected_successes: int


# One run of the fixtures: its name, its failfast, its lines, its blocks.
class PairRun(NamedTuple):
    run: str
    failfast: bool
    lines: list[str]
    blocks: list[PairBlock]


# Refuses a blob that streams, as the realm sends none that large.
def sink_refuse(header: jslb.Object) -> NoReturn:
    raise AssertionError(f"a blob came that streams: {header}")


# The bytes of the first line, as `bootstrap.py` writes it in debug mode.
def start_bytes() -> bytes:
    header = jslb.header_make(_FIRST_TYPE, id=_FIRST_ID, full=True)
    line = jslb.line_make(
        header,
        [],
        settings=harness.settings_copy(),
        switches={**switches.switches_get(), "debug": True},
    )
    (piece,) = jslb.line_encode(line)
    return cast(bytes, piece)


# Runs node on the bundle and the pair block, the first line on stdin.
def realm_run(path: str) -> subprocess.CompletedProcess[bytes]:
    node_path = shutil.which("node")
    if node_path is None:
        raise FileNotFoundError("node is not on PATH")
    return subprocess.run(
        [node_path, path, _BLOCK],
        input=start_bytes(),
        capture_output=True,
        check=False,
    )


# Reads a run from its push's payload, which holds exactly the run's fields.
def run_read(payload: dict[str, Any]) -> PairRun:
    blocks = [
        PairBlock(**cast(dict[str, Any], block)) for block in payload["blocks"]
    ]
    fields: dict[str, Any] = {**payload, "blocks": blocks}
    return PairRun(**fields)


# The stats the oracle gives a run: its blocks' unittest counts, by test.
def oracle_stats(blocks: list[PairBlock]) -> tap_consumer.TapStats:
    plan = passed = failed = skipped = 0
    for block in blocks:
        failing = block.failures + block.errors + block.unexpected_successes
        plan += block.cases
        passed += block.tests_run - failing - block.skipped
        failed += failing
        skipped += block.skipped
    return tap_consumer.TapStats(plan, passed, failed, skipped, True)


# The whole text of a stream of lines, each ending in a newline.
def stream_text(lines: list[str]) -> str:
    return "".join(text + "\n" for text in lines)


# The pair on every run of the realm's fixtures, from one run of node.
class TestPair(unittest.TestCase):
    # How node ended, and every line it wrote, the reply first.
    completed: subprocess.CompletedProcess[bytes]
    found: list[jslb.Object]
    idle: bool
    # The seconds node ran, which bound the durations it wrote.
    seconds: float

    # Builds the bundle in `build`, reusing a newer compile, then runs node.
    @classmethod
    def setUpClass(cls) -> None:
        path = page_build.node_build(_BUILD_PATH)
        started = time.perf_counter()
        cls.completed = realm_run(path)
        cls.seconds = time.perf_counter() - started
        decoder = jslb.LineDecoder(
            harness.setting_get("line_max"),
            harness.setting_get("blob_max"),
            harness.setting_get("overflow_bytes"),
            sink_refuse,
        )
        cls.found = decoder.bytes_feed(cls.completed.stdout)
        cls.idle = decoder.idle()

    # The payloads of the pushes after the reply whose header is of the type.
    def payloads_of(self, line_type: str) -> list[dict[str, Any]]:
        header = jslb.header_make(line_type, full=True)
        return [
            jslb.payload_of(push)
            for push in self.found[1:]
            if push[0] == header
        ]

    # The runs the realm sent, in order.
    def runs_sent(self) -> list[PairRun]:
        return [run_read(payload) for payload in self.payloads_of(_PAIR_TYPE)]

    # The realm answered, sent only its stream and its runs, and exited 0.
    def test_answer_given(self) -> None:
        self.assertEqual(self.completed.stderr, b"")
        self.assertEqual(self.completed.returncode, 0)
        self.assertTrue(self.idle)
        answer = jslb.header_make(_FIRST_TYPE, reply=_FIRST_ID, full=True)
        self.assertEqual(self.found[0], jslb.line_make(answer, []))
        streamed = self.payloads_of(_LINE_TYPE)
        for payload in streamed:
            self.assertEqual(payload["language"], _LANGUAGE)
        sent = len(streamed) + len(self.payloads_of(_PAIR_TYPE))
        self.assertEqual(len(self.found), 1 + sent)

    # The realm's own block passes, with one point per run, named by it.
    def test_points_named(self) -> None:
        texts = [payload["text"] for payload in self.payloads_of(_LINE_TYPE)]
        text = stream_text(texts)
        stats = tap_consumer.document_stats(text)
        self.assertTrue(stats.well_formed)
        self.assertEqual(stats.failed, 0)
        ending = [f"ok 1 - {_BLOCK}", "  ---", "  ...", "1..1"]
        self.assertEqual(texts[-5:-3] + texts[-2:], ending)
        limit = self.seconds * _MILLISECONDS + _HALF_DIGIT
        duration = texts[-3].removeprefix(_DURATION_PREFIX)
        self.assertLessEqual(float(duration), limit)
        points = [
            line.description
            for line in tap_consumer.Parser().parse_text(text)
            if isinstance(line, tap_consumer.Result) and line.depth == 1
        ]
        names = [run.run for run in self.runs_sent()]
        self.assertTrue(names)
        self.assertEqual(points, names)

    # Every line of every run parses to a kind the consumer knows.
    def test_lines_parsed(self) -> None:
        parser = tap_consumer.Parser()
        for run in self.runs_sent():
            for text in run.lines:
                line = parser.parse_line(text)
                where = f"{run.run}, line {text!r}"
                self.assertNotIsInstance(line, tap_consumer.Unknown, where)

    # The stream reader takes every line of each run, and the stream ends.
    def test_stream_read(self) -> None:
        parser = tap_consumer.Parser()
        for run in self.runs_sent():
            reader = tap_consumer.StreamReader()
            for text in run.lines:
                where = f"{run.run}, line {text!r}"
                self.assertTrue(
                    reader.line_read(parser.parse_line(text)), where
                )
            self.assertTrue(reader.stream_ended(), run.run)

    # Each run's document is well formed, with the counts of the oracle.
    def test_stats_counted(self) -> None:
        for run in self.runs_sent():
            stats = tap_consumer.document_stats(stream_text(run.lines))
            self.assertEqual(stats, oracle_stats(run.blocks), run.run)

    # The consumer fails a run exactly when the runner's `module_run` does.
    def test_verdict_equal(self) -> None:
        for run in self.runs_sent():
            stats = tap_consumer.document_stats(stream_text(run.lines))
            verdict = all(block.passed for block in run.blocks)
            self.assertEqual(stats.failed == 0, verdict, run.run)
