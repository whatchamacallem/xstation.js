# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# A test module that fails by design, which test_all.py lists apart from the
# suites so that only --module runs it: a run of it with --failures checks
# that failing tests are reported, and that the count is right. Each test
# ends one way a test can end: one passes, one fails an assertion, one
# raises an error, one has two failed subtests, one is skipped, one fails as
# it is expected to and one passes though it is expected to fail. Without
# failfast its block holds 4 failing points; with failfast its stream ends
# at the first with a bail out.

import unittest


# Tests that end each way a test can end, 4 of them failing.
class TestOutcomes(unittest.TestCase):
    # Passes.
    def test_passed(self) -> None:
        self.assertEqual(1, 1)

    # Fails an assertion.
    def test_failed(self) -> None:
        self.assertEqual(1, 2)

    # Raises an error that is no assertion.
    def test_errored(self) -> None:
        raise RuntimeError("an error by design")

    # Fails two subtests and passes one, which counts as one failure.
    def test_subtests_failed(self) -> None:
        for number in (1, 2, 3):
            with self.subTest(number=number):
                self.assertEqual(number, 2)

    # Is skipped.
    @unittest.skip("skipped by design")
    def test_skipped(self) -> None:
        raise AssertionError("a skipped test ran")

    # Fails as it is expected to, which counts as no failure.
    @unittest.expectedFailure
    def test_expected_failed(self) -> None:
        self.assertEqual(1, 2)

    # Passes though it is expected to fail, which counts as a failure.
    @unittest.expectedFailure
    def test_unexpected_passed(self) -> None:
        self.assertEqual(1, 1)
