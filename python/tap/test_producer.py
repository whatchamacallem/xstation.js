# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP producer on a fixture of one passing, one failing, one
# raising and one skipped test, nested in the test class so that no loader
# collects it. The TypeScript producer test expects the same text.

import tap.producer, unittest

# What starts each traceback line written under a failed test point.
_DIAGNOSTIC_PREFIX = "    # "

# The stream of an empty suite.
_EMPTY_LINES = [
    "TAP version 14",
    "    # Subtest: empty",
    "    1..0",
    "ok 1 - empty",
    "1..1",
]

# The fixture's failfast stream without its traceback lines.
_FAILFAST_LINES = [
    "TAP version 14",
    "    # Subtest: fixture",
    "    ok 1 - NestedFixture.test_alpha_passes",
    "    not ok 2 - NestedFixture.test_bravo_fails",
    "Bail out! failfast",
]

# The fixture's stream without its traceback lines.
_FIXTURE_LINES = [
    "TAP version 14",
    "    # Subtest: fixture",
    "    ok 1 - NestedFixture.test_alpha_passes",
    "    not ok 2 - NestedFixture.test_bravo_fails",
    "    not ok 3 - NestedFixture.test_charlie_raises",
    "    ok 4 - NestedFixture.test_delta_skips # SKIP fixture skip",
    "    1..4",
    "not ok 1 - fixture",
    "1..1",
]

# What starts the line that opens a module's block.
_SUBTEST_PREFIX = "    # Subtest: "


# The lines without the traceback lines under each failed test point.
def tracebacks_drop(lines: list[str]) -> list[str]:
    return [
        line
        for line in lines
        if not line.startswith(_DIAGNOSTIC_PREFIX)
        or line.startswith(_SUBTEST_PREFIX)
    ]


# Whether a traceback line follows every failed test point.
def tracebacks_follow(lines: list[str]) -> bool:
    return all(
        not line.startswith("    not ok ")
        or lines[index + 1].startswith(_DIAGNOSTIC_PREFIX)
        for index, line in enumerate(lines)
    )


# Tests `TapRunner` on the nested fixture and on an empty suite.
class TestProducer(unittest.TestCase):
    # A pass, a failure, an error and a skip, in name order.
    class NestedFixture(unittest.TestCase):
        # Passes.
        def test_alpha_passes(self) -> None:
            self.assertTrue(True)

        # Fails an assertion.
        def test_bravo_fails(self) -> None:
            self.assertEqual(1, 2)

        # Raises an error that is not an assertion.
        def test_charlie_raises(self) -> None:
            raise RuntimeError("fixture error")

        # Skips itself.
        def test_delta_skips(self) -> None:
            self.skipTest("fixture skip")

    # The fixture's tests, loaded in name order.
    def fixture_suite(self) -> unittest.TestSuite:
        loader = unittest.TestLoader()
        return loader.loadTestsFromTestCase(self.NestedFixture)

    # The fixture's stream is the expected text, traceback lines aside.
    def test_fixture_stream(self) -> None:
        lines: list[str] = []
        runner = tap.producer.TapRunner(lines.append, False)
        self.assertFalse(runner.module_run("fixture", self.fixture_suite()))
        self.assertFalse(runner.run_end())
        self.assertEqual(tracebacks_drop(lines), _FIXTURE_LINES)
        self.assertTrue(tracebacks_follow(lines))

    # With failfast the stream ends at the first failure, and says so.
    def test_failfast_stream(self) -> None:
        lines: list[str] = []
        runner = tap.producer.TapRunner(lines.append, True)
        self.assertFalse(runner.module_run("fixture", self.fixture_suite()))
        self.assertFalse(runner.run_end())
        self.assertEqual(tracebacks_drop(lines), _FAILFAST_LINES)
        self.assertTrue(tracebacks_follow(lines))
        with self.assertRaises(RuntimeError):
            runner.module_run("fixture", unittest.TestSuite())

    # An empty suite passes, and the stream ends once.
    def test_empty_suite(self) -> None:
        lines: list[str] = []
        runner = tap.producer.TapRunner(lines.append, False)
        self.assertTrue(runner.module_run("empty", unittest.TestSuite()))
        self.assertTrue(runner.run_end())
        self.assertEqual(lines, _EMPTY_LINES)
        with self.assertRaises(RuntimeError):
            runner.run_end()

    # A module name that would break its line is refused before any write.
    def test_name_check(self) -> None:
        lines: list[str] = []
        runner = tap.producer.TapRunner(lines.append, False)
        with self.assertRaises(ValueError):
            runner.module_run("a # b", unittest.TestSuite())
        with self.assertRaises(ValueError):
            runner.module_run("a\nb", unittest.TestSuite())
        self.assertEqual(lines, ["TAP version 14"])
