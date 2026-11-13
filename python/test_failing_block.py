# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the test driver's count of a TypeScript realm's failing tests, on
# failing_block.ts, the block that fails by design, which only --module runs.
# Each test runs the real driver, test_all.py, as a program with --stream and
# --module of the block, its stdout the stream: a test-all run expects the
# failures the gold measured for the whole block, and a smoke-test run, which
# is failfast, expects the one failure before its bail out. Each run passes,
# exiting 0 with nothing on stderr, as its failures are those expected, and
# the TAP consumer reads its stream as well formed, with the gold's counts.

import harness, os, subprocess, sys, tap_consumer, unittest

# The checkout's python directory, which holds the driver.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The driver, run as a program.
_DRIVER_PATH = os.path.join(_PYTHON_PATH, "test_all.py")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_failing_block"

# The block that fails by design, named by its file in `ts`.
_BLOCK: str = harness.gold_get(f"{_GOLD_ID}.block")

# The counts of the whole block's stream, as measured.
_WHOLE_STATS = tap_consumer.TapStats(
    *harness.gold_get(f"{_GOLD_ID}.whole_stats")
)

# The counts of the failfast stream, which ends at the first failure.
_BAIL_STATS = tap_consumer.TapStats(
    *harness.gold_get(f"{_GOLD_ID}.bail_stats")
)

# The last line of the failfast stream.
_BAIL_LINE: str = harness.gold_get(f"{_GOLD_ID}.bail_line")

# The exit code of the driver when the failing tests are those expected.
_DRIVER_PASSED = 0


# Runs the driver on the block, returns its stream once it has passed.
def stream_read(
    case: unittest.TestCase, levels: list[str], failures: int
) -> str:
    command = [sys.executable, _DRIVER_PATH, "--stream", *levels]
    command += ["--module", _BLOCK, "--failures", str(failures)]
    done = subprocess.run(
        command, stdin=subprocess.DEVNULL, capture_output=True, text=True
    )
    case.assertEqual(done.returncode, _DRIVER_PASSED, done.stderr)
    case.assertEqual(done.stderr, "")
    return done.stdout


# The driver's verdict on the block's failures, whole and failfast.
class TestBlock(unittest.TestCase):
    # A `test-all` run expecting the block's failures passes, counts kept.
    def test_failures_counted(self) -> None:
        stream = stream_read(self, ["--test-all"], _WHOLE_STATS.failed)
        self.assertEqual(tap_consumer.document_stats(stream), _WHOLE_STATS)

    # A `smoke-test` run bails out at the first failure, which it expects.
    def test_bail_counted(self) -> None:
        stream = stream_read(self, [], _BAIL_STATS.failed)
        self.assertEqual(tap_consumer.document_stats(stream), _BAIL_STATS)
        self.assertEqual(stream.splitlines()[-1], _BAIL_LINE)
