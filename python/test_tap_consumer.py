# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP consumer: the kind it reads from each line, the stats of
# streams as the producers write them, passing, failing, bailed out and with
# expected failures, a bail out wherever it stands counting one failure
# unless it follows a failed point, the stream reader fed line by line, then
# streams with one fault each.

import tap_consumer, unittest
from collections.abc import Sequence

# A failfast stream, which bails out at its first failure.
_FAILFAST_LINES = (
    "TAP version 14",
    "    1..4",
    "    ok 1 - test_alpha_passes",
    "    not ok 2 - test_bravo_fails",
    "    # Traceback (most recent call last):",
    "    # AssertionError: 1 != 2",
    "Bail out! failfast",
)

# A stream whose block failed, without failfast.
_FAILING_LINES = (
    "TAP version 14",
    "    1..4",
    "    ok 1 - test_alpha_passes",
    "    not ok 2 - test_bravo_fails",
    "    # Traceback (most recent call last):",
    "    # AssertionError: 1 != 2",
    "    not ok 3 - test_charlie_raises",
    "    # Traceback (most recent call last):",
    "    # RuntimeError: fixture error",
    "    ok 4 - test_delta_skips # SKIP fixture skip",
    "not ok 1 - fixture",
    "1..1",
)

# A stream a failed `tearDownClass` ended, with a point beyond the plan.
_FIXTURE_LINES = (
    "TAP version 14",
    "    1..1",
    "    ok 1 - test_values_equal",
    "    not ok 2 - tearDownClass (module.ClosingFixture)",
    "    # RuntimeError: fixture error",
    "Bail out! failfast",
)

# Two passing blocks, the second empty, which the fault tests change.
_PASSING_LINES = (
    "TAP version 14",
    "    1..2",
    "    ok 1 - test_values_equal",
    "    ok 2 - test_skip_self # SKIP fixture skip",
    "ok 1 - test_first",
    "    1..0",
    "ok 2 - test_second",
    "1..2",
)

# The bail out the server appends when the browser fails.
_BROWSER_BAIL = "Bail out! The browser failed: boom"

# The counts of `passed`, `failed` and `skipped` after each passing line.
_PASSING_COUNTS = [
    (0, 0, 0),
    (0, 0, 0),
    (1, 0, 0),
    (1, 0, 1),
    (1, 0, 1),
    (1, 0, 1),
    (1, 0, 1),
    (1, 0, 1),
]

# A block with an expected failure, which passes, and an unexpected success.
_TODO_LINES = (
    "TAP version 14",
    "    1..2",
    "    not ok 1 - test_values_differ # TODO expected failure",
    "    # AssertionError: 1 != 2",
    "    not ok 2 - test_values_equal",
    "    # unexpected success",
    "not ok 1 - fixture",
    "1..1",
)


# The stats of the lines as a document, each line ended by a newline.
def stats_read(lines: Sequence[str]) -> tap_consumer.TapStats:
    return tap_consumer.document_stats("".join(line + "\n" for line in lines))


# The lines with the one at `index` replaced.
def line_replace(lines: Sequence[str], index: int, line: str) -> list[str]:
    changed = list(lines)
    changed[index] = line
    return changed


# The lines with `line` put in before the one at `index`.
def line_insert(lines: Sequence[str], index: int, line: str) -> list[str]:
    changed = list(lines)
    changed.insert(index, line)
    return changed


# Tests the kind of each line the parser reads.
class TestParser(unittest.TestCase):
    # The version line names its version.
    def test_version_line(self) -> None:
        parser = tap_consumer.Parser()
        line = parser.parse_line("TAP version 14")
        self.assertEqual(line, tap_consumer.Version(14))

    # A plan line has its depth and the number of points it plans.
    def test_plan_line(self) -> None:
        parser = tap_consumer.Parser()
        lines = [parser.parse_line("1..3"), parser.parse_line("    1..0")]
        expected = [tap_consumer.Plan(0, 3), tap_consumer.Plan(1, 0)]
        self.assertEqual(lines, expected)

    # A point has its depth, grade, number, description and directive.
    def test_result_line(self) -> None:
        parser = tap_consumer.Parser()
        texts = [
            "ok 2 - test_a",
            "not ok 1 - b",
            "    ok 3 - c # SKIP",
            "ok 1 -  # SKIP",
        ]
        expected = [
            tap_consumer.Result(0, True, 2, "test_a", ""),
            tap_consumer.Result(0, False, 1, "b", ""),
            tap_consumer.Result(1, True, 3, "c", "SKIP"),
            tap_consumer.Result(0, True, 1, "", "SKIP"),
        ]
        lines = [parser.parse_line(text) for text in texts]
        self.assertEqual(lines, expected)

    # A directive skips or marks a point to do, with its text after it.
    def test_result_directive(self) -> None:
        parser = tap_consumer.Parser()
        texts = [
            "    ok 4 - test_d # SKIP why # not",
            "    not ok 1 - test_e # TODO expected",
            "    ok 1 - test_f",
        ]
        expected = [
            tap_consumer.Result(1, True, 4, "test_d", "SKIP why # not"),
            tap_consumer.Result(1, False, 1, "test_e", "TODO expected"),
            tap_consumer.Result(1, True, 1, "test_f", ""),
        ]
        lines = [parser.parse_line(text) for text in texts]
        self.assertEqual(lines, expected)
        grades = [(line.skip, line.todo) for line in expected]
        wanted = [(True, False), (False, True), (False, False)]
        self.assertEqual(grades, wanted)

    # A diagnostic line keeps its text, a blank one too.
    def test_diagnostic_line(self) -> None:
        parser = tap_consumer.Parser()
        cases = (
            ("    # AssertionError: 1 != 2", (1, "AssertionError: 1 != 2")),
            ("    #     at frame", (1, "    at frame")),
            ("    # ", (1, "")),
            ("# note", (0, "note")),
        )
        for text, (depth, words) in cases:
            line = parser.parse_line(text)
            self.assertEqual(line, tap_consumer.Diagnostic(depth, words))

    # A bail out line has its reason, empty when it gives none.
    def test_bail_line(self) -> None:
        parser = tap_consumer.Parser()
        lines = [parser.parse_line("Bail out! failfast")]
        lines.append(parser.parse_line("Bail out!"))
        expected = [tap_consumer.Bail(0, "failfast")]
        expected.append(tap_consumer.Bail(0, ""))
        self.assertEqual(lines, expected)

    # A line of no kind the producers write is unknown, with its text.
    def test_unknown_line(self) -> None:
        parser = tap_consumer.Parser()
        texts = (
            "",
            "ok",
            "ok 1 test_a",
            "ok x - test_a",
            "  ok 1 - test_a",
            "        ok 1 - test_a",
            "ok 1 - a # b",
            "ok 1 - a # TODOS",
            "1..",
            "1..x",
            "TAP version x",
            "Bail out",
            "    #note",
        )
        for text in texts:
            line = parser.parse_line(text)
            self.assertEqual(line, tap_consumer.Unknown(text))

    # The text splits at newlines only, a last line with none counts too.
    def test_text_lines(self) -> None:
        parser = tap_consumer.Parser()
        lines = list(parser.parse_text("1..1\nok 1 - a\r\nBail out!"))
        expected = [
            tap_consumer.Plan(0, 1),
            tap_consumer.Result(0, True, 1, "a\r", ""),
            tap_consumer.Bail(0, ""),
        ]
        self.assertEqual(lines, expected)
        self.assertEqual(list(parser.parse_text("")), [])
        line = list(parser.parse_text("1..0\n"))
        self.assertEqual(line, [tap_consumer.Plan(0, 0)])


# Tests the stats of whole streams as the producers write them.
class TestStats(unittest.TestCase):
    # Passing blocks, one of them empty, are well formed.
    def test_passing_stream(self) -> None:
        stats = stats_read(_PASSING_LINES)
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 1, True))

    # A failing block counts its failures and is well formed.
    def test_failing_stream(self) -> None:
        stats = stats_read(_FAILING_LINES)
        self.assertEqual(stats, tap_consumer.TapStats(4, 1, 2, 1, True))

    # A failfast stream is well formed with the plan of the block it cut.
    def test_failfast_stream(self) -> None:
        stats = stats_read(_FAILFAST_LINES)
        self.assertEqual(stats, tap_consumer.TapStats(4, 1, 1, 0, True))

    # A fixture's failure may add a point beyond the plan before the bail.
    def test_fixture_stream(self) -> None:
        stats = stats_read(_FIXTURE_LINES)
        self.assertEqual(stats, tap_consumer.TapStats(1, 1, 1, 0, True))

    # An expected failure passes and an unexpected success fails.
    def test_todo_stream(self) -> None:
        stats = stats_read(_TODO_LINES)
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 1, 0, True))

    # A bail out alone, before any version line, ends a stream of one failure.
    def test_bail_alone(self) -> None:
        stats = stats_read((_BROWSER_BAIL,))
        self.assertEqual(stats, tap_consumer.TapStats(0, 0, 1, 0, True))

    # A bail out right after the version line counts one failure.
    def test_bail_versioned(self) -> None:
        stats = stats_read((_PASSING_LINES[0], _BROWSER_BAIL))
        self.assertEqual(stats, tap_consumer.TapStats(0, 0, 1, 0, True))

    # A bail out between blocks ends the stream and counts one failure.
    def test_bail_between(self) -> None:
        stats = stats_read(line_insert(_PASSING_LINES, 5, _BROWSER_BAIL))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 1, 1, True))

    # A bail out after a passing point ends the stream with one failure.
    def test_bail_passed(self) -> None:
        stats = stats_read(line_insert(_PASSING_LINES, 3, _BROWSER_BAIL))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 1, 0, True))

    # A bail out before the first point of a block counts one failure.
    def test_bail_planned(self) -> None:
        stats = stats_read(line_insert(_PASSING_LINES, 2, _BROWSER_BAIL))
        self.assertEqual(stats, tap_consumer.TapStats(2, 0, 1, 0, True))

    # A bail out after an expected failure counts one failure.
    def test_bail_todo(self) -> None:
        stats = stats_read(line_insert(_TODO_LINES, 4, _BROWSER_BAIL))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 1, 0, True))


# Tests the stream reader fed one line at a time, as the wire test feeds it.
class TestStreamReader(unittest.TestCase):
    # Each line fits, the counts grow as the points come, and the plan ends it.
    def test_lines_read(self) -> None:
        parser = tap_consumer.Parser()
        reader = tap_consumer.StreamReader()
        counts: list[tuple[int, int, int]] = []
        for text in _PASSING_LINES:
            self.assertFalse(reader.stream_ended(), text)
            self.assertTrue(reader.line_read(parser.parse_line(text)), text)
            counts.append((reader.passed, reader.failed, reader.skipped))
        self.assertTrue(reader.stream_ended())
        self.assertEqual(reader.plan, 2)
        self.assertEqual(counts, _PASSING_COUNTS)

    # A bail out ends the stream, and a line after it does not fit.
    def test_bail_ended(self) -> None:
        parser = tap_consumer.Parser()
        reader = tap_consumer.StreamReader()
        for text in _PASSING_LINES[:3] + (_BROWSER_BAIL,):
            self.assertTrue(reader.line_read(parser.parse_line(text)), text)
        self.assertTrue(reader.stream_ended())
        counts = (reader.plan, reader.passed, reader.failed)
        self.assertEqual(counts, (2, 1, 1))
        later = parser.parse_line(_PASSING_LINES[3])
        self.assertFalse(reader.line_read(later))

    # A line that does not fit where it stands is refused and counts nothing.
    def test_line_refused(self) -> None:
        parser = tap_consumer.Parser()
        reader = tap_consumer.StreamReader()
        self.assertFalse(reader.line_read(parser.parse_line("    1..2")))
        self.assertFalse(reader.stream_ended())
        counts = (reader.plan, reader.passed, reader.failed)
        self.assertEqual(counts, (0, 0, 0))


# Tests streams with one fault each: reading stops at the fault.
class TestFaults(unittest.TestCase):
    # A block plan that differs from its points is a fault at the parent.
    def test_plan_mismatch(self) -> None:
        stats = stats_read(line_replace(_PASSING_LINES, 1, "    1..3"))
        self.assertEqual(stats, tap_consumer.TapStats(3, 1, 0, 1, False))

    # A point out of sequence is a fault.
    def test_number_gap(self) -> None:
        line = "    ok 3 - test_skip_self # SKIP fixture skip"
        stats = stats_read(line_replace(_PASSING_LINES, 3, line))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 0, False))

    # A diagnostic line before the first point of a block is a fault.
    def test_diagnostic_early(self) -> None:
        stats = stats_read(line_insert(_PASSING_LINES, 2, "    # note"))
        self.assertEqual(stats, tap_consumer.TapStats(2, 0, 0, 0, False))

    # A diagnostic line between blocks is a fault.
    def test_diagnostic_outside(self) -> None:
        stats = stats_read(line_insert(_PASSING_LINES, 5, "# note"))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 1, False))

    # A bail out indented into a block is a fault.
    def test_bail_indented(self) -> None:
        line = "    Bail out! failfast"
        stats = stats_read(line_insert(_PASSING_LINES, 3, line))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 0, False))

    # A failed point that claims a skip is a fault.
    def test_skip_failed(self) -> None:
        line = "    not ok 1 - test_values_equal # SKIP why"
        stats = stats_read(line_replace(_PASSING_LINES, 2, line))
        self.assertEqual(stats, tap_consumer.TapStats(2, 0, 0, 0, False))

    # A parent line that disagrees with its block is a fault.
    def test_parent_mismatch(self) -> None:
        for parent in ("not ok 1 - test_first", "ok 2 - test_first"):
            stats = stats_read(line_replace(_PASSING_LINES, 4, parent))
            self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 1, False))

    # A parent plan that differs from the blocks is a fault.
    def test_parent_plan(self) -> None:
        stats = stats_read(line_replace(_PASSING_LINES, 7, "1..3"))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 1, False))

    # A stream cut before its parent plan is not well formed.
    def test_plan_missing(self) -> None:
        stats = stats_read(_PASSING_LINES[:-1])
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 1, False))

    # A stream with its plan line present but its last newline cut is a fault.
    def test_newline_missing(self) -> None:
        text = "".join(line + "\n" for line in _PASSING_LINES)
        whole = tap_consumer.document_stats(text)
        cut = tap_consumer.document_stats(text.removesuffix("\n"))
        self.assertEqual(whole, tap_consumer.TapStats(2, 1, 0, 1, True))
        self.assertEqual(cut, tap_consumer.TapStats(2, 1, 0, 1, False))

    # A line after the parent plan is a fault.
    def test_line_trailing(self) -> None:
        stats = stats_read(_PASSING_LINES + ("ok 3 - test_third",))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 1, False))

    # A line after a bail out is a fault.
    def test_line_bailed(self) -> None:
        stats = stats_read(_FAILFAST_LINES + ("1..1",))
        self.assertEqual(stats, tap_consumer.TapStats(4, 1, 1, 0, False))

    # A version other than 14 is a fault, and so is an empty text.
    def test_version_wrong(self) -> None:
        stats = stats_read(line_replace(_PASSING_LINES, 0, "TAP version 13"))
        self.assertEqual(stats, tap_consumer.TapStats(0, 0, 0, 0, False))
        empty = tap_consumer.document_stats("")
        self.assertEqual(empty, tap_consumer.TapStats(0, 0, 0, 0, False))

    # A line of no known kind inside a block is a fault.
    def test_line_unknown(self) -> None:
        stats = stats_read(line_insert(_PASSING_LINES, 3, "    hello"))
        self.assertEqual(stats, tap_consumer.TapStats(2, 1, 0, 0, False))
