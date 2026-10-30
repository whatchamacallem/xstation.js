# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP producer and consumer as a pair: the consumer validates each
# stream the producer writes, and counts it as unittest's own result counts
# the same tests. Each kind of outcome of a test, of a class or module
# fixture and of a module's load runs with and without failfast, alone and
# as a block between passing blocks, which run until one fails, as the
# driver runs them. Every line parses to a known kind, the stream reader
# takes each and the stream ends, the document is well formed with the
# oracle's counts, and the consumer fails the stream exactly when the runner
# does. The oracle grades what unittest records of each test: a test that
# fails, errs or passes unexpectedly is one failure however many of its
# subtests failed, an expected failure is a pass, a skip is a skip, and each
# failed fixture is one failure. It counts no bail out, since the producer
# writes one only after a failed point, where the consumer counts none. The
# fixtures are nested in the test class so that no loader collects them.
# The failing `setUpModule` runs in a forked child, which registers its
# module and then kills itself, so that the module reaches no other test.

import functools, importlib, os, signal, sys, tap_consumer, tap_producer
import traceback, types, unittest
from collections.abc import Callable, Sequence
from typing import NamedTuple

# A module name that no file provides, for a load that fails.
_ABSENT_MODULE = "tap_pair_absent"

# The ending a child writes when its work raised nothing.
_ENDING_PASSED = "passed"

# The module the `setUpModule` fixture claims, registered only in its child.
_FIXTURE_MODULE = "tap_pair_fixture"


# Raises, as the `setUpModule` of the fixture's module.
def module_fail() -> None:
    raise RuntimeError("fixture error")


# Imports the module no file provides, as the driver loads a suite's module.
def absent_load() -> unittest.TestSuite:
    module = importlib.import_module(_ABSENT_MODULE)
    return unittest.TestLoader().loadTestsFromModule(module)


# unittest's own load of the module no file provides: one test, which errs.
def absent_oracle() -> unittest.TestSuite:
    return unittest.TestLoader().loadTestsFromName(_ABSENT_MODULE)


# In the forked child: runs the work, writes how it ended, kills itself.
def child_end(work: Callable[[], None], write_fd: int) -> None:
    try:
        try:
            work()
            ending = _ENDING_PASSED
        except BaseException:
            ending = traceback.format_exc()
        try:
            with os.fdopen(write_fd, "w", encoding="utf-8") as file:
                file.write(ending)
        except BaseException:
            # The parent finds no ending, so the failure and it go to stderr.
            sys.stderr.write(
                f"{traceback.format_exc()}the ending not written: {ending}\n"
            )
            sys.stderr.flush()
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# A block of a stream: its name, the load the runner takes, the oracle's load.
class FixtureBlock(NamedTuple):
    name: str
    load: Callable[[], unittest.TestSuite]
    oracle: Callable[[], unittest.TestSuite]


# The block of a fixture class, whose tests both loads take in name order.
def class_block(fixture: type[unittest.TestCase]) -> FixtureBlock:
    loader = unittest.TestLoader()
    load = functools.partial(loader.loadTestsFromTestCase, fixture)
    return FixtureBlock(fixture.__name__, load, load)


# The oracle: unittest's own result of a block, graded test by test.
class OutcomeResult(unittest.TestResult):
    # `failfast` stops the run at the first failure, as the runner's does.
    def __init__(self, failfast: bool) -> None:
        super().__init__()
        self.failfast = failfast
        self.pass_count = 0
        self.fail_count = 0
        self.skip_count = 0
        self._fail_mark = 0
        self._skip_mark = 0

    # The outcomes unittest recorded that fail a test or a fixture.
    def failing_count(self) -> int:
        return (
            len(self.failures)
            + len(self.errors)
            + len(self.unexpectedSuccesses)
        )

    # Counts each failing outcome since the last grade as a fixture's failure.
    def fixtures_grade(self) -> None:
        failing = self.failing_count()
        self.fail_count += failing - self._fail_mark
        self._fail_mark = failing

    # Grades the fixtures that ran before the test, then starts it.
    def startTest(self, test: unittest.TestCase) -> None:
        self.fixtures_grade()
        super().startTest(test)

    # Stops the test and grades it by the outcomes recorded while it ran.
    def stopTest(self, test: unittest.TestCase) -> None:
        super().stopTest(test)
        failing = self.failing_count()
        if failing > self._fail_mark:
            self.fail_count += 1
        elif len(self.skipped) > self._skip_mark:
            self.skip_count += 1
        else:
            self.pass_count += 1
        self._fail_mark = failing
        self._skip_mark = len(self.skipped)


# The stats the oracle gives the blocks: unittest's runs of the same tests.
def oracle_stats(
    blocks: Sequence[FixtureBlock], failfast: bool
) -> tap_consumer.TapStats:
    plan = passed = failed = skipped = 0
    for block in blocks:
        suite = block.oracle()
        plan += suite.countTestCases()
        result = OutcomeResult(failfast)
        suite.run(result)
        result.fixtures_grade()
        passed += result.pass_count
        failed += result.fail_count
        skipped += result.skip_count
    return tap_consumer.TapStats(plan, passed, failed, skipped, True)


# The pair on each kind of outcome, every fixture in four streams.
class TestPair(unittest.TestCase):
    # Passes.
    class PassFixture(unittest.TestCase):
        # Passes an assertion.
        def test_values_equal(self) -> None:
            self.assertEqual(1, 1)

    # Skips one test without a reason and one with a reason.
    class SkipFixture(unittest.TestCase):
        # Skips itself, giving no reason.
        def test_reason_absent(self) -> None:
            raise unittest.SkipTest("")

        # Skips itself with a reason.
        def test_reason_given(self) -> None:
            self.skipTest("fixture skip")

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

    # Fails one subtest and passes one, then fails two in its next test.
    class SubtestFixture(unittest.TestCase):
        # The case 1 passes and the case 2 fails `1 != 2`.
        def test_one_failed(self) -> None:
            for case in (1, 2):
                with self.subTest(case=case):
                    self.assertEqual(1, case)

        # The cases 2 and 3 both fail.
        def test_two_failed(self) -> None:
            for case in (2, 3):
                with self.subTest(case=case):
                    self.assertEqual(1, case)

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

    # Holds no test, as a module with no tests does.
    class EmptyFixture(unittest.TestCase):
        pass

    # Runs the blocks as one stream until one fails, then checks the pair.
    def stream_check(
        self, blocks: Sequence[FixtureBlock], failfast: bool
    ) -> None:
        names = [block.name for block in blocks]
        run = f"blocks {names}, failfast {failfast}"
        lines: list[str] = []
        runner = tap_producer.TAPTestRunner(failfast)
        runner.set_stream(lines.append)
        verdicts: list[bool] = []
        for block in blocks:
            verdicts.append(runner.module_run(block.name, block.load))
            if not verdicts[-1]:
                break
        runner.run_end()
        parser = tap_consumer.Parser()
        reader = tap_consumer.StreamReader()
        for text in lines:
            where = f"{run}, line {text!r}"
            line = parser.parse_line(text)
            self.assertNotIsInstance(line, tap_consumer.Unknown, where)
            self.assertTrue(reader.line_read(line), where)
        self.assertTrue(reader.stream_ended(), run)
        stats = tap_consumer.document_stats(
            "".join(text + "\n" for text in lines)
        )
        expected = oracle_stats(blocks[: len(verdicts)], failfast)
        self.assertEqual(stats, expected, run)
        self.assertEqual(stats.failed == 0, all(verdicts), run)

    # Checks the block with and without failfast, alone and between passes.
    def runs_check(self, block: FixtureBlock) -> None:
        passing = class_block(self.PassFixture)
        for failfast in (False, True):
            self.stream_check([block], failfast)
            self.stream_check([passing, block, passing], failfast)

    # Runs the work in a forked child and returns the ending it wrote.
    def child_run(self, work: Callable[[], None]) -> str:
        read_fd, write_fd = os.pipe()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            child_end(work, write_fd)
        os.close(write_fd)
        with os.fdopen(read_fd, encoding="utf-8") as file:
            ending = file.read()
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        return ending

    # In the child: registers the fixture's module, then checks its block.
    def module_check(self) -> None:
        module = types.ModuleType(_FIXTURE_MODULE)
        setattr(module, "setUpModule", module_fail)
        sys.modules[_FIXTURE_MODULE] = module
        self.runs_check(class_block(self.ModuleFixture))

    # A pass counts as passed.
    def test_pass_counted(self) -> None:
        self.runs_check(class_block(self.PassFixture))

    # A skip counts as skipped, without a reason and with one.
    def test_skips_counted(self) -> None:
        self.runs_check(class_block(self.SkipFixture))

    # A failed assertion counts as one failure.
    def test_assertion_fails(self) -> None:
        self.runs_check(class_block(self.AssertionFixture))

    # An error counts as one failure.
    def test_error_raised(self) -> None:
        self.runs_check(class_block(self.ErrorFixture))

    # A test counts as one failure however many of its subtests fail.
    def test_subtests_fail(self) -> None:
        self.runs_check(class_block(self.SubtestFixture))

    # An expected failure counts as passed, and its block passes.
    def test_failure_expected(self) -> None:
        self.runs_check(class_block(self.ExpectedFixture))

    # An unexpected success counts as one failure.
    def test_success_unexpected(self) -> None:
        self.runs_check(class_block(self.SurpriseFixture))

    # A failed `setUpClass` counts as the oracle measures it.
    def test_class_setup(self) -> None:
        self.runs_check(class_block(self.ClassFixture))

    # A failed `tearDownClass` counts as the oracle measures it.
    def test_class_teardown(self) -> None:
        self.runs_check(class_block(self.ClosingFixture))

    # A failed `setUpModule` counts as the oracle measures it, in a child.
    def test_module_setup(self) -> None:
        self.assertEqual(self.child_run(self.module_check), _ENDING_PASSED)

    # A module that fails to load counts as unittest's loader counts it.
    def test_load_fails(self) -> None:
        block = FixtureBlock(_ABSENT_MODULE, absent_load, absent_oracle)
        self.runs_check(block)

    # A module with no tests plans none and passes.
    def test_module_empty(self) -> None:
        self.runs_check(class_block(self.EmptyFixture))
