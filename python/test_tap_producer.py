# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP producer: its tracker, its runner, and every way a run can
# fail. Each failure is an expected failure: the test states the stream the
# suite must write, its diagnostics by the lines they must hold, and passes
# only when the suite fails exactly that way. The fixtures are nested in the
# test class so that no loader collects them.

import importlib, sys, tap_producer, types, unittest
from collections.abc import Callable, Sequence
from typing import cast

# A module name that no file provides, for a load that fails.
_ABSENT_MODULE = "tap_fixture_absent"

# The diagnostic line of the assertion the fixtures fail.
_ASSERTION_LINE = "    # AssertionError: 1 != 2"

# The line that ends a stream that stopped.
_BAIL_LINE = "Bail out! failfast"

# The block name of every fixture run.
_BLOCK_NAME = "fixture"

# What starts each diagnostic line of a block.
_DIAGNOSTIC_PREFIX = "    # "

# The diagnostic line of the error the fixtures raise.
_ERROR_LINE = "    # RuntimeError: fixture error"

# The module name the module fixture claims, registered only by its test.
_FIXTURE_MODULE = "tap_fixture_module"

# The parent line of a fixture block that failed.
_PARENT_FAILED = "not ok 1 - fixture"

# The parent line of a fixture block that passed.
_PARENT_PASSED = "ok 1 - fixture"

# The parent plan of a stream of one block.
_PARENT_PLAN = "1..1"

# The first diagnostic line of a traceback.
_TRACEBACK_LINE = "    # Traceback (most recent call last):"

# The first line of every stream.
_VERSION_LINE = "TAP version 14"


# Raises, as the module fixture's `setUpModule`.
def module_fail() -> None:
    raise RuntimeError("fixture error")


# The name unittest gives a fixture class in the point of its fixture error.
def fixture_name(fixture: type[unittest.TestCase]) -> str:
    return f"{fixture.__module__}.{fixture.__qualname__}"


# The load of a fixture class's tests, in name order.
def class_load(
    fixture: type[unittest.TestCase],
) -> Callable[[], unittest.TestSuite]:
    return lambda: unittest.TestLoader().loadTestsFromTestCase(fixture)


# The load of a module that no file provides.
def absent_load() -> unittest.TestSuite:
    module = importlib.import_module(_ABSENT_MODULE)
    return unittest.TestLoader().loadTestsFromModule(module)


# The runs of consecutive diagnostic lines of a stream, in order.
def runs_find(lines: Sequence[str]) -> list[list[str]]:
    runs: list[list[str]] = []
    inside = False
    for line in lines:
        diagnostic = line.startswith(_DIAGNOSTIC_PREFIX)
        if diagnostic and inside:
            runs[-1].append(line)
        elif diagnostic:
            runs.append([line])
        inside = diagnostic
    return runs


# The stream with each diagnostic run cut to the lines its expected run states.
def stream_reduce(actual: Sequence[str], expected: Sequence[str]) -> list[str]:
    stated = runs_find(expected)
    if len(runs_find(actual)) != len(stated):
        return list(actual)
    runs = iter(stated)
    wanted: list[str] = []
    reduced: list[str] = []
    inside = False
    for line in actual:
        diagnostic = line.startswith(_DIAGNOSTIC_PREFIX)
        if diagnostic and not inside:
            wanted = next(runs)
        if not diagnostic:
            reduced.append(line)
        elif wanted and wanted[0] == line:
            reduced.append(wanted.pop(0))
        inside = diagnostic
    return reduced


# Runs the load as block `fixture`, failing the case unless it writes expected.
def stream_expect(
    case: unittest.TestCase,
    load: Callable[[], unittest.TestSuite],
    failfast: bool,
    expected: Sequence[str],
) -> None:
    lines: list[str] = []
    runner = tap_producer.TAPTestRunner(failfast)
    runner.set_stream(lines.append)
    passed = runner.module_run(_BLOCK_NAME, load)
    ended = runner.run_end()
    case.assertEqual(stream_reduce(lines, expected), list(expected))
    case.assertEqual([passed, ended], [_PARENT_PASSED in expected] * 2)


# Tests the tracker: numbered points, directives, diagnostics and plans.
class TestTracker(unittest.TestCase):
    # Points are numbered in order and the plan that comes last counts them.
    def test_points_numbered(self) -> None:
        lines: list[str] = []
        tracker = tap_producer.Tracker(lines.append)
        tracker.add_ok("Case", "test_one")
        tracker.add_not_ok("Case", "test_two", diagnostics="first\nsecond\n")
        tracker.add_skip("Case", "test_three", "why")
        tracker.add_skip("Case", "test_four", "")
        tracker.add_not_ok("Case", "test_five", "TODO later")
        tracker.generate_tap_reports()
        expected = [
            "ok 1 - test_one",
            "not ok 2 - test_two",
            "# first",
            "# second",
            "ok 3 - test_three # SKIP why",
            "ok 4 - test_four # SKIP",
            "not ok 5 - test_five # TODO later",
            "1..5",
        ]
        self.assertEqual(lines, expected)

    # A plan set first is written at once, before the points.
    def test_plan_first(self) -> None:
        lines: list[str] = []
        tracker = tap_producer.Tracker(lines.append)
        tracker.set_plan(2)
        tracker.add_ok("Case", "test_one", "", "note")
        tracker.add_ok("Case", "test_two")
        expected = ["1..2", "ok 1 - test_one", "# note", "ok 2 - test_two"]
        self.assertEqual(lines, expected)

    # A blank line of diagnostic text is still a diagnostic line.
    def test_diagnostics_blank(self) -> None:
        lines: list[str] = []
        tracker = tap_producer.Tracker(lines.append)
        tracker.add_not_ok("Case", "test_one", diagnostics="a\n\nb")
        self.assertEqual(lines, ["not ok 1 - test_one", "# a", "# ", "# b"])

    # Text that would break its line is refused with its diagnostics.
    def test_line_refused(self) -> None:
        lines: list[str] = []
        tracker = tap_producer.Tracker(lines.append)
        refused = (
            ("a # b", "", "trace"),
            ("a\nb", "", None),
            ("test_one", "SKIP a\rb", None),
        )
        for description, directive, diagnostics in refused:
            with self.assertRaises(ValueError) as caught:
                tracker.add_ok("Case", description, directive, diagnostics)
            message = (
                f"the TAP point {description!r} # {directive!r} does not fit"
                f" on one line, its diagnostics: {diagnostics!r}"
            )
            self.assertEqual(str(caught.exception), message)
        self.assertEqual(lines, [])


# Tests the runner: the stream of modules that pass and fail, and its ends.
class TestRunner(unittest.TestCase):
    # Blocks plan first, parents follow, and the parent plan comes last.
    def test_modules_pass(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(False)
        runner.set_stream(lines.append)
        load = class_load(TestFailures.PassingFixture)
        self.assertTrue(runner.module_run("first", load))
        self.assertTrue(runner.module_run("second", unittest.TestSuite))
        self.assertTrue(runner.run_end())
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    ok 1 - test_values_equal",
            "ok 1 - first",
            "    1..0",
            "ok 2 - second",
            "1..2",
        ]
        self.assertEqual(lines, expected)

    # Without failfast a failed module is graded and the stream goes on.
    def test_module_fails(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(False)
        runner.set_stream(lines.append)
        load = class_load(TestFailures.AssertionFixture)
        self.assertFalse(runner.module_run("first", load))
        self.assertTrue(runner.module_run("second", unittest.TestSuite))
        self.assertFalse(runner.run_end())
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_values_differ",
            _ASSERTION_LINE,
            "not ok 1 - first",
            "    1..0",
            "ok 2 - second",
            "1..2",
        ]
        self.assertEqual(stream_reduce(lines, expected), expected)

    # A stream that bailed out takes no other module and writes no plan.
    def test_bail_ends(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(True)
        runner.set_stream(lines.append)
        load = class_load(TestFailures.AssertionFixture)
        self.assertFalse(runner.module_run("first", load))
        with self.assertRaises(RuntimeError) as caught:
            runner.module_run("second", unittest.TestSuite)
        message = "the TAP stream ended before 'second'"
        self.assertEqual(str(caught.exception), message)
        self.assertFalse(runner.run_end())
        self.assertEqual(lines[-1], _BAIL_LINE)

    # The stream ends once, and takes no module after its end.
    def test_end_twice(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(False)
        runner.set_stream(lines.append)
        self.assertTrue(runner.run_end())
        with self.assertRaises(RuntimeError) as caught:
            runner.run_end()
        message = "the TAP stream has ended already"
        self.assertEqual(str(caught.exception), message)
        with self.assertRaises(RuntimeError) as caught:
            runner.module_run("late", unittest.TestSuite)
        message = "the TAP stream ended before 'late'"
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(lines, [_VERSION_LINE, "1..0"])

    # The stream is set once, and a block before it is refused.
    def test_stream_once(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(False)
        with self.assertRaises(RuntimeError) as caught:
            runner.module_run("early", unittest.TestSuite)
        message = "set_stream was not called before '    1..0'"
        self.assertEqual(str(caught.exception), message)
        runner.set_stream(lines.append)
        with self.assertRaises(RuntimeError) as caught:
            runner.set_stream(lines.append)
        message = "the TAP stream is set already"
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(lines, [_VERSION_LINE])

    # A module name that would break its lines is refused before any block.
    def test_name_refused(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(False)
        runner.set_stream(lines.append)
        with self.assertRaises(ValueError) as caught:
            runner.module_run("a # b", unittest.TestSuite)
        message = (
            "the TAP point 'a # b' # '' does not fit on one line, its"
            " diagnostics: None"
        )
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(lines, [_VERSION_LINE])


# Tests each way a run can fail, each stated as the stream it must write.
class TestFailures(unittest.TestCase):
    # Passes.
    class PassingFixture(unittest.TestCase):
        # Passes an assertion.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Fails an assertion.
    class AssertionFixture(unittest.TestCase):
        # Fails `1 != 2`.
        def test_values_differ(self) -> None:
            self.assertEqual(1, 2)

    # Raises an error in its test.
    class ErrorFixture(unittest.TestCase):
        # Raises an error that is not an assertion's.
        def test_error_raised(self) -> None:
            raise RuntimeError("fixture error")

    # Passes one subtest and fails the next.
    class SubtestFixture(unittest.TestCase):
        # The case 2 fails `1 != 2`.
        def test_cases_differ(self) -> None:
            for case in (1, 2):
                with self.subTest(case=case):
                    self.assertEqual(1, case)

    # Raises in `setUp`.
    class SetupFixture(unittest.TestCase):
        # Raises before the test.
        def setUp(self) -> None:
            raise RuntimeError("fixture error")

        # Never runs.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Raises in `tearDown` after a test that passed.
    class TeardownFixture(unittest.TestCase):
        # Raises after the test.
        def tearDown(self) -> None:
            raise RuntimeError("fixture error")

        # Passes an assertion.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Fails its test, then raises in `tearDown`: two outcomes of one test.
    class DoubleFixture(unittest.TestCase):
        # Raises after the test.
        def tearDown(self) -> None:
            raise RuntimeError("fixture error")

        # Fails `1 != 2`.
        def test_values_differ(self) -> None:
            self.assertEqual(1, 2)

    # Raises in `setUpClass`.
    class ClassFixture(unittest.TestCase):
        # Raises before the class's tests.
        @classmethod
        def setUpClass(cls) -> None:
            raise RuntimeError("fixture error")

        # Never runs.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Raises in `tearDownClass` after a test that passed.
    class ClosingFixture(unittest.TestCase):
        # Raises after the class's tests.
        @classmethod
        def tearDownClass(cls) -> None:
            raise RuntimeError("fixture error")

        # Passes an assertion.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Belongs to a module whose `setUpModule` raises.
    class ModuleFixture(unittest.TestCase):
        # The module the suite looks `setUpModule` up in.
        __module__ = _FIXTURE_MODULE

        # Never runs.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Expects its assertion to fail, and it does.
    class ExpectedFixture(unittest.TestCase):
        # Fails `1 != 2` as expected.
        @unittest.expectedFailure
        def test_values_differ(self) -> None:
            self.assertEqual(1, 2)

    # Expects its assertion to fail, and it passes.
    class SurpriseFixture(unittest.TestCase):
        # Passes though it is expected to fail.
        @unittest.expectedFailure
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Skips its test.
    class SkipFixture(unittest.TestCase):
        # Skips itself with a reason.
        def test_skip_self(self) -> None:
            self.skipTest("fixture skip")

    # A pass, a failure, an error and a skip, in name order.
    class MixedFixture(unittest.TestCase):
        # Passes.
        def test_alpha_passes(self) -> None:
            self.assertEqual(1, 1)

        # Fails `1 != 2`.
        def test_bravo_fails(self) -> None:
            self.assertEqual(1, 2)

        # Raises an error that is not an assertion's.
        def test_charlie_raises(self) -> None:
            raise RuntimeError("fixture error")

        # Skips itself.
        def test_delta_skips(self) -> None:
            self.skipTest("fixture skip")

    # Skips in `setUpClass`, an outcome with no running test.
    class SkippedFixture(unittest.TestCase):
        # Skips the class before its tests.
        @classmethod
        def setUpClass(cls) -> None:
            raise unittest.SkipTest("fixture skip")

        # Never runs.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Starts its test and stops it with no outcome.
    class SilentFixture(unittest.TestCase):
        # Reports a start and a stop and nothing between.
        def run(
            self, result: unittest.TestResult | None = None
        ) -> unittest.TestResult | None:
            started = cast(unittest.TestResult, result)
            started.startTest(self)
            started.stopTest(self)
            return started

        # Never runs.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # A failed assertion is a failing point with the assertion's text.
    def test_assertion_fails(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_values_differ",
            _TRACEBACK_LINE,
            _ASSERTION_LINE,
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.AssertionFixture), False, expected)

    # An error in a test is a failing point with the error's text.
    def test_error_raised(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_error_raised",
            _TRACEBACK_LINE,
            _ERROR_LINE,
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.ErrorFixture), False, expected)

    # A failed subtest fails its test's one point, naming the subtest.
    def test_subtest_fails(self) -> None:
        name = self.SubtestFixture("test_cases_differ").id()
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_cases_differ",
            f"{_DIAGNOSTIC_PREFIX}{name} (case=2)",
            _TRACEBACK_LINE,
            _ASSERTION_LINE,
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.SubtestFixture), False, expected)

    # With failfast a failed subtest ends the stream.
    def test_subtest_failfast(self) -> None:
        name = self.SubtestFixture("test_cases_differ").id()
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_cases_differ",
            f"{_DIAGNOSTIC_PREFIX}{name} (case=2)",
            _ASSERTION_LINE,
            _BAIL_LINE,
        ]
        stream_expect(self, class_load(self.SubtestFixture), True, expected)

    # An error in `setUp` fails the test's point.
    def test_setup_raises(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_values_equal",
            _TRACEBACK_LINE,
            _ERROR_LINE,
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.SetupFixture), False, expected)

    # An error in `tearDown` fails the point of a test that passed.
    def test_teardown_raises(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_values_equal",
            _TRACEBACK_LINE,
            _ERROR_LINE,
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.TeardownFixture), False, expected)

    # A second outcome of one test adds its diagnostics to the same point.
    def test_outcomes_two(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_values_differ",
            _TRACEBACK_LINE,
            _ASSERTION_LINE,
            _TRACEBACK_LINE,
            _ERROR_LINE,
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.DoubleFixture), False, expected)

    # An error in `setUpClass` is a point of its own and ends the stream.
    def test_class_setup(self) -> None:
        name = fixture_name(self.ClassFixture)
        expected = [
            _VERSION_LINE,
            "    1..1",
            f"    not ok 1 - setUpClass ({name})",
            _TRACEBACK_LINE,
            _ERROR_LINE,
            _BAIL_LINE,
        ]
        stream_expect(self, class_load(self.ClassFixture), False, expected)

    # An error in `tearDownClass` is a point after the tests and ends it.
    def test_class_teardown(self) -> None:
        name = fixture_name(self.ClosingFixture)
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    ok 1 - test_values_equal",
            f"    not ok 2 - tearDownClass ({name})",
            _TRACEBACK_LINE,
            _ERROR_LINE,
            _BAIL_LINE,
        ]
        stream_expect(self, class_load(self.ClosingFixture), False, expected)

    # An error in `setUpModule` is a point of its own and ends the stream.
    def test_module_setup(self) -> None:
        module = types.ModuleType(_FIXTURE_MODULE)
        setattr(module, "setUpModule", module_fail)
        sys.modules[_FIXTURE_MODULE] = module
        self.addCleanup(sys.modules.pop, _FIXTURE_MODULE)
        expected = [
            _VERSION_LINE,
            "    1..1",
            f"    not ok 1 - setUpModule ({_FIXTURE_MODULE})",
            _TRACEBACK_LINE,
            _ERROR_LINE,
            _BAIL_LINE,
        ]
        stream_expect(self, class_load(self.ModuleFixture), False, expected)

    # An expected failure is a `TODO` point that does not fail the block.
    def test_failure_expected(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_values_differ # TODO expected failure",
            _TRACEBACK_LINE,
            _ASSERTION_LINE,
            _PARENT_PASSED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.ExpectedFixture), False, expected)

    # An unexpected success fails its point and says so.
    def test_success_unexpected(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_values_equal",
            "    # unexpected success",
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.SurpriseFixture), False, expected)

    # A skip is a passing point with its reason.
    def test_skip_reason(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    ok 1 - test_skip_self # SKIP fixture skip",
            _PARENT_PASSED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.SkipFixture), False, expected)

    # Without failfast every test runs and the failures fail the block.
    def test_mixed_outcomes(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..4",
            "    ok 1 - test_alpha_passes",
            "    not ok 2 - test_bravo_fails",
            _TRACEBACK_LINE,
            _ASSERTION_LINE,
            "    not ok 3 - test_charlie_raises",
            _TRACEBACK_LINE,
            _ERROR_LINE,
            "    ok 4 - test_delta_skips # SKIP fixture skip",
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, class_load(self.MixedFixture), False, expected)

    # With failfast the first failure ends the stream with a bail out line.
    def test_failfast_bails(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..4",
            "    ok 1 - test_alpha_passes",
            "    not ok 2 - test_bravo_fails",
            _TRACEBACK_LINE,
            _ASSERTION_LINE,
            _BAIL_LINE,
        ]
        stream_expect(self, class_load(self.MixedFixture), True, expected)

    # A module that does not load is one failing point with its traceback.
    def test_load_fails(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - fixture",
            _TRACEBACK_LINE,
            f"    # ModuleNotFoundError: No module named '{_ABSENT_MODULE}'",
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        stream_expect(self, absent_load, False, expected)

    # With failfast a module that does not load ends the stream.
    def test_load_failfast(self) -> None:
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - fixture",
            f"    # ModuleNotFoundError: No module named '{_ABSENT_MODULE}'",
            _BAIL_LINE,
        ]
        stream_expect(self, absent_load, True, expected)

    # A skip outside a running test raises with its reason.
    def test_fixture_skip(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(False)
        runner.set_stream(lines.append)
        load = class_load(self.SkippedFixture)
        with self.assertRaises(RuntimeError) as caught:
            runner.module_run(_BLOCK_NAME, load)
        name = fixture_name(self.SkippedFixture)
        message = (
            f"setUpClass ({name}) has an outcome outside a running test:"
            " _PointPart(word='ok', directive='SKIP fixture skip',"
            " diagnostics='')"
        )
        self.assertEqual(str(caught.exception), message)

    # A test that ends with no outcome raises when its point is due.
    def test_outcome_missing(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(False)
        runner.set_stream(lines.append)
        load = class_load(self.SilentFixture)
        with self.assertRaises(RuntimeError) as caught:
            runner.module_run(_BLOCK_NAME, load)
        name = self.SilentFixture("test_values_equal").id()
        message = f"{name} ended with no TAP outcome"
        self.assertEqual(str(caught.exception), message)


# Tests the expected failure check: stated lines match, others do not.
class TestExpectation(unittest.TestCase):
    # Diagnostic lines not stated are dropped, stated ones kept in order.
    def test_stated_lines(self) -> None:
        actual = ["    not ok 1 - a", "    # x", "    # y", "    # z", "1..1"]
        expected = ["    not ok 1 - a", "    # x", "    # z", "1..1"]
        self.assertEqual(stream_reduce(actual, expected), expected)

    # A stated line the run lacks leaves the streams different.
    def test_line_missing(self) -> None:
        actual = ["    not ok 1 - a", "    # x", "1..1"]
        expected = ["    not ok 1 - a", "    # y", "1..1"]
        reduced = ["    not ok 1 - a", "1..1"]
        self.assertEqual(stream_reduce(actual, expected), reduced)

    # A run of diagnostics the expectation does not state is kept whole.
    def test_run_unstated(self) -> None:
        actual = ["    not ok 1 - a", "    # x", "    ok 2 - b", "    # y"]
        expected = ["    not ok 1 - a", "    # x", "    ok 2 - b"]
        self.assertEqual(stream_reduce(actual, expected), actual)

    # A suite that fails another way does not match the stated failure.
    def test_failure_other(self) -> None:
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(False)
        runner.set_stream(lines.append)
        runner.module_run(_BLOCK_NAME, class_load(TestFailures.ErrorFixture))
        runner.run_end()
        expected = [
            _VERSION_LINE,
            "    1..1",
            "    not ok 1 - test_error_raised",
            _ASSERTION_LINE,
            _PARENT_FAILED,
            _PARENT_PLAN,
        ]
        self.assertNotEqual(stream_reduce(lines, expected), expected)
