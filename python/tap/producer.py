# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# A unittest runner that writes TAP version 14 one line at a time: one
# indented subtest block per module with its plan last, a parent line for
# each module, then the parent plan. With failfast the first failure ends
# the stream with a bail out line.

import types, unittest
from collections.abc import Callable

# The line that ends a failfast stream after its first failure.
_BAIL_LINE = "Bail out! failfast"

# What starts each traceback line written under a failed test point.
_DIAGNOSTIC_PREFIX = "    # "

# The characters a module name may not hold.
_NAME_FORBIDDEN = "#\n\r"

# The characters a skip reason may not hold.
_REASON_FORBIDDEN = "\n\r"

# What starts the line that opens a module's block, before its name.
_SUBTEST_PREFIX = "    # Subtest: "

# The first line of every stream.
_VERSION_LINE = "TAP version 14"


# Raises when the text holds a character that would break its TAP line.
def _text_check(text: str, forbidden: str) -> None:
    for character in forbidden:
        if character in text:
            raise ValueError(f"TAP text {text!r} holds {character!r}")


# Writes one test point per test as its outcome arrives, then any traceback.
class _TapResult(unittest.TestResult):
    # `write` takes each line, and `failfast` stops at the first failure.
    def __init__(self, write: Callable[[str], None], failfast: bool) -> None:
        super().__init__()
        self.failfast = failfast
        self._write = write
        self._current: unittest.TestCase | None = None

    # Marks the test as the one whose outcome comes next.
    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._current = test

    # Raises when the test ended with no outcome a test point can show.
    def stopTest(self, test: unittest.TestCase) -> None:
        super().stopTest(test)
        if self._current is not None:
            raise RuntimeError(f"{test.id()} ended with no TAP outcome")

    # Writes `ok` for a test that passed.
    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self._point_write(test, "ok", "")

    # Writes `ok` with a `SKIP` directive and the reason, if any.
    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        _text_check(reason, _REASON_FORBIDDEN)
        super().addSkip(test, reason)
        directive = f" # SKIP {reason}" if reason else " # SKIP"
        self._point_write(test, "ok", directive)

    # Writes `not ok` and the traceback of a failed assertion.
    def addFailure(
        self,
        test: unittest.TestCase,
        err: (
            tuple[type[BaseException], BaseException, types.TracebackType]
            | tuple[None, None, None]
        ),
    ) -> None:
        super().addFailure(test, err)
        self._failure_write(test, self.failures[-1][1])

    # Writes `not ok` and the traceback of an error that is not an assertion.
    def addError(
        self,
        test: unittest.TestCase,
        err: (
            tuple[type[BaseException], BaseException, types.TracebackType]
            | tuple[None, None, None]
        ),
    ) -> None:
        super().addError(test, err)
        self._failure_write(test, self.errors[-1][1])

    # Writes the running test's point, raising unless it is its first outcome.
    def _point_write(
        self, test: unittest.TestCase, word: str, directive: str
    ) -> None:
        if test is not self._current:
            raise RuntimeError(f"{test.id()} has no running test point")
        self._current = None
        name = type(test).__name__ + "." + test.id().rsplit(".", 1)[1]
        self._write(f"    {word} {self.testsRun} - {name}{directive}")

    # Writes `not ok` and the traceback, then ends a failfast stream.
    def _failure_write(self, test: unittest.TestCase, text: str) -> None:
        self._point_write(test, "not ok", "")
        for line in text.removesuffix("\n").split("\n"):
            self._write(_DIAGNOSTIC_PREFIX + line)
        if self.failfast:
            self._write(_BAIL_LINE)


# Writes TAP for a unittest run: one plan, one indented block per module.
class TapRunner:
    # `write` gets each TAP line as it is produced, with no buffering.
    def __init__(self, write: Callable[[str], None], failfast: bool) -> None:
        self._write = write
        self._failfast = failfast
        self._modules = 0
        self._passed = True
        self._bailed = False
        self._ended = False
        write(_VERSION_LINE)

    # Runs one module's suite as a subtest block named `module`.
    def module_run(self, module: str, suite: unittest.TestSuite) -> bool:
        if self._bailed or self._ended:
            raise RuntimeError(f"the TAP stream ended before {module!r}")
        _text_check(module, _NAME_FORBIDDEN)
        self._write(_SUBTEST_PREFIX + module)
        result = _TapResult(self._write, self._failfast)
        suite.run(result)
        if result.shouldStop:
            self._bailed = True
            self._passed = False
            return False
        self._modules += 1
        self._write(f"    1..{result.testsRun}")
        passed = result.wasSuccessful()
        word = "ok" if passed else "not ok"
        self._write(f"{word} {self._modules} - {module}")
        self._passed = self._passed and passed
        return passed

    # Writes the parent plan. Returns whether every module passed.
    def run_end(self) -> bool:
        if self._ended:
            raise RuntimeError("the TAP stream has ended already")
        self._ended = True
        if not self._bailed:
            self._write(f"1..{self._modules}")
        return self._passed
