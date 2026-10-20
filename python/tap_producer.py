# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The Python TAP producer, shaped after tappy's: a `Tracker` writes the lines
# of one level of a TAP version 14 stream the moment each is added,
# `TAPTestResult` turns the outcomes of unittest into one point per test, and
# `TAPTestRunner` writes one stream: the version line, then per module a block
# indented four spaces with its plan first, its points and their diagnostics,
# then a parent line, and the parent plan last. A run that has to stop, by
# failfast or by a class or module fixture that failed, ends with a bail out
# line in place of the parent line and the parent plan.

import re, traceback, types, unittest
from collections.abc import Callable
from typing import NamedTuple, TypeAlias, cast

# The line that ends a stream that stopped, by failfast or a failed fixture.
_BAIL_LINE = "Bail out! failfast"

# What starts each line of a module's block.
_BLOCK_INDENT = "    "

# The directive of a test that failed the way it was expected to.
_EXPECTED_DIRECTIVE = "TODO expected failure"

# A line break, which no text written on one TAP line may hold.
_LINE_BREAK = re.compile(r"[\r\n]")

# The diagnostic of a test that passed though it was expected to fail.
_SURPRISE_TEXT = "unexpected success"

# The first line of every stream.
_VERSION_LINE = "TAP version 14"

# What unittest reports an error with, as `sys.exc_info` returns it.
_ErrorInfo: TypeAlias = (
    tuple[type[BaseException], BaseException, types.TracebackType]
    | tuple[None, None, None]
)


# Raises unless the description and the directive each fit on one TAP line.
def _line_check(
    description: str, directive: str, diagnostics: str | None
) -> None:
    if "#" in description or _LINE_BREAK.search(description + directive):
        raise ValueError(
            f"the TAP point {description!r} # {directive!r} does not fit on"
            f" one line, its diagnostics: {diagnostics!r}"
        )


# The directive of a skipped test, with its reason when it has one.
def _skip_directive(reason: str) -> str:
    return f"SKIP {reason}" if reason else "SKIP"


# One outcome of a test: its word, its directive and its diagnostic text.
class _PointPart(NamedTuple):
    word: str
    directive: str
    diagnostics: str


# Writes the lines of one level of a stream the moment each is added.
class Tracker:
    # `write` takes each line, without its newline.
    def __init__(self, write: Callable[[str], None]) -> None:
        self._write = write
        self._count = 0

    # Writes the plan at once, before the points, as tappy does when streaming.
    def set_plan(self, total: int) -> None:
        self._write(f"1..{total}")

    # Writes a passing point. `class_name` is tappy's and is not written.
    def add_ok(
        self,
        class_name: str,
        description: str,
        directive: str = "",
        diagnostics: str | None = None,
    ) -> None:
        self._point_add("ok", description, directive, diagnostics)

    # Writes a failing point. `class_name` is tappy's and is not written.
    def add_not_ok(
        self,
        class_name: str,
        description: str,
        directive: str = "",
        diagnostics: str | None = None,
    ) -> None:
        self._point_add("not ok", description, directive, diagnostics)

    # Writes a passing point with a `SKIP` directive and the reason.
    def add_skip(self, class_name: str, description: str, reason: str) -> None:
        self._point_add("ok", description, _skip_directive(reason), None)

    # Writes the plan of the points added, for a level whose plan comes last.
    def generate_tap_reports(self) -> None:
        self._write(f"1..{self._count}")

    # Writes the next numbered point, then a diagnostic line per text line.
    def _point_add(
        self,
        word: str,
        description: str,
        directive: str,
        diagnostics: str | None,
    ) -> None:
        _line_check(description, directive, diagnostics)
        self._count += 1
        suffix = f" # {directive}" if directive else ""
        self._write(f"{word} {self._count} - {description}{suffix}")
        if diagnostics is not None:
            for line in diagnostics.removesuffix("\n").split("\n"):
                self._write("# " + line)


# Turns unittest's outcomes into one point per test, written once all are in.
class TAPTestResult(unittest.TestResult):
    # `tracker` writes the points of the block this result runs.
    def __init__(self, tracker: Tracker) -> None:
        super().__init__()
        self._tracker = tracker
        self._current: unittest.TestCase | None = None
        self._parts: list[_PointPart] = []

    # Writes the point of the test before, then marks this one as running.
    def startTest(self, test: unittest.TestCase) -> None:
        self.point_flush()
        super().startTest(test)
        self._current = test

    # Keeps a pass.
    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self._part_add(test, _PointPart("ok", "", ""))

    # Keeps a skip and its reason.
    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._part_add(test, _PointPart("ok", _skip_directive(reason), ""))

    # Keeps a failed assertion and its traceback.
    def addFailure(self, test: unittest.TestCase, err: _ErrorInfo) -> None:
        super().addFailure(test, err)
        self._failure_add(test, self.failures[-1][1])

    # Keeps an error and its traceback, of a test or of a fixture.
    def addError(self, test: unittest.TestCase, err: _ErrorInfo) -> None:
        super().addError(test, err)
        self._failure_add(test, self.errors[-1][1])

    # Keeps a failed subtest's name and traceback. A passed one adds nothing.
    def addSubTest(
        self,
        test: unittest.TestCase,
        subtest: unittest.TestCase,
        err: _ErrorInfo | None,
    ) -> None:
        super().addSubTest(test, subtest, err)
        if err is None:
            return
        failed = issubclass(
            cast(type[BaseException], err[0]), test.failureException
        )
        text = (self.failures if failed else self.errors)[-1][1]
        self._failure_add(test, subtest.id() + "\n" + text)

    # Keeps a failure the test was expected to have, with its traceback.
    def addExpectedFailure(
        self, test: unittest.TestCase, err: _ErrorInfo
    ) -> None:
        super().addExpectedFailure(test, err)
        text = self.expectedFailures[-1][1]
        self._part_add(test, _PointPart("not ok", _EXPECTED_DIRECTIVE, text))

    # Keeps the pass of a test that was expected to fail, which fails it.
    def addUnexpectedSuccess(self, test: unittest.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        self._part_add(test, _PointPart("not ok", "", _SURPRISE_TEXT))

    # Writes the point of the last test, raising when it had no outcome.
    def point_flush(self) -> None:
        test = self._current
        if test is None:
            return
        parts = self._parts
        self._current = None
        self._parts = []
        if not parts:
            raise RuntimeError(f"{test.id()} ended with no TAP outcome")
        failing = [part for part in parts if part.word == "not ok"]
        lead = next((part for part in failing if not part.directive), parts[0])
        lines: list[str] = []
        for part in parts:
            if part is not lead and part.directive:
                lines.append(part.directive)
            if part.diagnostics:
                lines.append(part.diagnostics)
        name = test.id().rsplit(".", 1)[1]
        diagnostics = "\n".join(lines) if lines else None
        if lead.word == "ok":
            self._tracker.add_ok(
                type(test).__name__, name, lead.directive, diagnostics
            )
        else:
            self._tracker.add_not_ok(
                type(test).__name__, name, lead.directive, diagnostics
            )

    # Keeps a failing part, or writes the point of a failed fixture and stops.
    def _failure_add(self, test: unittest.TestCase, text: str) -> None:
        if test is self._current:
            self._parts.append(_PointPart("not ok", "", text))
            return
        self.point_flush()
        self._tracker.add_not_ok(
            type(test).__name__, test.id(), diagnostics=text
        )
        self.stop()

    # Keeps a part of the running test, raising for an outcome of any other.
    def _part_add(self, test: unittest.TestCase, part: _PointPart) -> None:
        if test is not self._current:
            raise RuntimeError(
                f"{test.id()} has an outcome outside a running test: {part!r}"
            )
        self._parts.append(part)


# Writes TAP for a unittest run: one plan, one indented block per module.
class TAPTestRunner(unittest.TextTestRunner):
    # `failfast` ends the stream at the first failure, as unittest's does.
    def __init__(self, failfast: bool) -> None:
        super().__init__(failfast=failfast)
        self._write: Callable[[str], None] | None = None
        self._parent = Tracker(self._line_write)
        self._passed = True
        self._bailed = False
        self._ended = False

    # Sends each line to `write` the moment it is made, the version line first.
    def set_stream(self, write: Callable[[str], None]) -> None:
        if self._write is not None:
            raise RuntimeError("the TAP stream is set already")
        self._write = write
        write(_VERSION_LINE)

    # Runs the test as one block, its plan first, and returns its result.
    def run(
        self, test: unittest.TestSuite | unittest.TestCase
    ) -> TAPTestResult:
        block = Tracker(self._block_write)
        block.set_plan(test.countTestCases())
        result = TAPTestResult(block)
        result.failfast = self.failfast
        test.run(result)
        result.point_flush()
        return result

    # Loads and runs one module as a block, then closes the block.
    def module_run(
        self, module: str, load: Callable[[], unittest.TestSuite]
    ) -> bool:
        if self._bailed or self._ended:
            raise RuntimeError(f"the TAP stream ended before {module!r}")
        _line_check(module, "", None)
        try:
            suite = load()
        except Exception as error:
            block = Tracker(self._block_write)
            block.set_plan(1)
            text = "".join(traceback.format_exception(error))
            block.add_not_ok(module, module, diagnostics=text)
            return self._block_end(module, False, self.failfast)
        result = self.run(suite)
        return self._block_end(
            module, result.wasSuccessful(), result.shouldStop
        )

    # Writes the parent plan unless the stream bailed out. True if all passed.
    def run_end(self) -> bool:
        if self._ended:
            raise RuntimeError("the TAP stream has ended already")
        self._ended = True
        if not self._bailed:
            self._parent.generate_tap_reports()
        return self._passed

    # Bails out when the block stopped the run, else writes its parent line.
    def _block_end(self, module: str, passed: bool, stopped: bool) -> bool:
        if stopped:
            self._line_write(_BAIL_LINE)
            self._bailed = True
            self._passed = False
            return False
        if passed:
            self._parent.add_ok(module, module)
        else:
            self._parent.add_not_ok(module, module)
        self._passed = self._passed and passed
        return passed

    # Writes a line of a block, indented one level.
    def _block_write(self, text: str) -> None:
        self._line_write(_BLOCK_INDENT + text)

    # Writes a line of the stream, which `set_stream` must have set.
    def _line_write(self, text: str) -> None:
        write = self._write
        if write is None:
            raise RuntimeError(f"set_stream was not called before {text!r}")
        write(text)
