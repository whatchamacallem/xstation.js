# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP consumer on the fixture's streams as the producers write
# them, on passing blocks, and on streams with one fault each.

import tap.consumer, unittest
from collections.abc import Sequence

# The fixture's failfast stream, which ends at its first failure.
_FAILFAST_LINES = (
    "TAP version 14",
    "    # Subtest: fixture",
    "    ok 1 - NestedFixture.test_alpha_passes",
    "    not ok 2 - NestedFixture.test_bravo_fails",
    "    # AssertionError: 1 != 2",
    "Bail out! failfast",
)

# The fixture's stream with traceback lines under its failed test points.
_FIXTURE_LINES = (
    "TAP version 14",
    "    # Subtest: fixture",
    "    ok 1 - NestedFixture.test_alpha_passes",
    "    not ok 2 - NestedFixture.test_bravo_fails",
    "    # Traceback (most recent call last):",
    "    # AssertionError: 1 != 2",
    "    not ok 3 - NestedFixture.test_charlie_raises",
    "    # Traceback (most recent call last):",
    "    # RuntimeError: fixture error",
    "    ok 4 - NestedFixture.test_delta_skips # SKIP fixture skip",
    "    1..4",
    "not ok 1 - fixture",
    "1..1",
)

# Two passing blocks, the second empty, which the fault tests change.
_PASSING_LINES = (
    "TAP version 14",
    "    # Subtest: first",
    "    ok 1 - Case.test_one",
    "    1..1",
    "ok 1 - first",
    "    # Subtest: second",
    "    1..0",
    "ok 2 - second",
    "1..2",
)


# The stats of the lines as a document, each line ended by a newline.
def stats_read(lines: Sequence[str]) -> tap.consumer.TapStats:
    return tap.consumer.document_stats("\n".join(lines) + "\n")


# Tests `document_stats` on whole streams and on faults.
class TestConsumer(unittest.TestCase):
    # The fixture's stream is well formed and counted by its test points.
    def test_fixture_stream(self) -> None:
        stats = stats_read(_FIXTURE_LINES)
        self.assertEqual(stats, tap.consumer.TapStats(4, 1, 2, 1, True))

    # A failfast stream is well formed with no plan for its last block.
    def test_failfast_stream(self) -> None:
        stats = stats_read(_FAILFAST_LINES)
        self.assertEqual(stats, tap.consumer.TapStats(0, 1, 1, 0, True))

    # Passing blocks, one of them empty, are well formed.
    def test_passing_stream(self) -> None:
        stats = stats_read(_PASSING_LINES)
        self.assertEqual(stats, tap.consumer.TapStats(1, 1, 0, 0, True))

    # A block plan that differs from its count of test points is a fault.
    def test_plan_mismatch(self) -> None:
        lines = list(_PASSING_LINES)
        lines[3] = "    1..2"
        stats = stats_read(lines)
        self.assertEqual(stats, tap.consumer.TapStats(0, 1, 0, 0, False))

    # A test point out of sequence is a fault.
    def test_number_gap(self) -> None:
        lines = list(_PASSING_LINES)
        lines[2] = "    ok 2 - Case.test_one"
        stats = stats_read(lines)
        self.assertEqual(stats, tap.consumer.TapStats(0, 0, 0, 0, False))

    # A traceback line under a passing test point is a fault.
    def test_stray_diagnostic(self) -> None:
        lines = list(_PASSING_LINES)
        lines.insert(3, "    # note")
        stats = stats_read(lines)
        self.assertEqual(stats, tap.consumer.TapStats(0, 1, 0, 0, False))

    # A bail out after a passing test point is a fault.
    def test_misplaced_bail(self) -> None:
        lines = list(_PASSING_LINES)
        lines.insert(3, "Bail out! failfast")
        stats = stats_read(lines)
        self.assertEqual(stats, tap.consumer.TapStats(0, 1, 0, 0, False))

    # A failed test point with a `SKIP` directive is a fault.
    def test_failed_skip(self) -> None:
        lines = list(_PASSING_LINES)
        lines[2] = "    not ok 1 - Case.test_one # SKIP why"
        stats = stats_read(lines)
        self.assertEqual(stats, tap.consumer.TapStats(0, 0, 0, 0, False))

    # A parent line that disagrees with its block is a fault.
    def test_parent_mismatch(self) -> None:
        for parent in ("not ok 1 - first", "ok 1 - other", "ok 2 - first"):
            lines = list(_PASSING_LINES)
            lines[4] = parent
            stats = stats_read(lines)
            self.assertEqual(stats, tap.consumer.TapStats(1, 1, 0, 0, False))

    # A stream cut before its plan is a fault.
    def test_missing_plan(self) -> None:
        stats = stats_read(_PASSING_LINES[:-1])
        self.assertEqual(stats, tap.consumer.TapStats(1, 1, 0, 0, False))

    # A last line with no newline is a fault.
    def test_missing_newline(self) -> None:
        stats = tap.consumer.document_stats("\n".join(_PASSING_LINES))
        self.assertEqual(stats, tap.consumer.TapStats(1, 1, 0, 0, False))

    # A line after the plan is a fault.
    def test_trailing_line(self) -> None:
        stats = stats_read(_PASSING_LINES + ("ok 3 - third",))
        self.assertEqual(stats, tap.consumer.TapStats(1, 1, 0, 0, False))

    # An empty text is not a stream.
    def test_empty_text(self) -> None:
        stats = tap.consumer.document_stats("")
        self.assertEqual(stats, tap.consumer.TapStats(0, 0, 0, 0, False))
