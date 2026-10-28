# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The Python TAP consumer, shaped after tappy's: a `Parser` reads TAP version
# 14 text line by line into tappy's line kinds, each with its depth, zero for
# the stream and one for a block indented four spaces. A `StreamReader`
# checks a stream against the one the producers write, a line at a time as
# it arrives, as the wire test reads the TypeScript stream the server
# writes, and counts its points; `document_stats` reads a whole document so
# and returns its stats: the points its blocks plan, how many passed, failed
# and were skipped, and whether it is well formed. Reading stops at the
# first fault: the counts are those of the lines before it. A `Bail out!`
# line at depth 0 ends a stream wherever it stands, before the version line
# too, since the server appends one when the browser fails: it counts as one
# failure unless it follows a failed point, as the producer's own does, and
# reading stops there, every line after it ignored, as TAP 14 asks a harness
# to stop at a bail out.

import io, re
from collections.abc import Iterator
from typing import NamedTuple, TypeAlias

# A bail out line: its indent and its reason.
_BAIL_PATTERN = re.compile(r"( {4})?Bail out!(?: (.*))?")

# A diagnostic line: its indent and its text after the hash and the space.
_DIAGNOSTIC_PATTERN = re.compile(r"( {4})?# (.*)")

# How many spaces indent a block one level.
_INDENT_WIDTH = 4

# A plan line: its indent and the number of points it plans.
_PLAN_PATTERN = re.compile(r"( {4})?1\.\.([0-9]+)")

# A test point: its indent, `not`, number, description and directive.
_RESULT_PATTERN = re.compile(
    r"( {4})?(not )?ok ([0-9]+) - ([^#]*?)(?: # ((?:SKIP|TODO)(?: .*)?))?"
)

# The version the producers write.
_TAP_VERSION = 14

# The version line: the version it names.
_VERSION_PATTERN = re.compile(r"TAP version ([0-9]+)")


# A test point: depth, whether it passed, number, description, directive.
class Result(NamedTuple):
    depth: int
    ok: bool
    number: int
    description: str
    directive: str

    # Whether the directive skips the test.
    @property
    def skip(self) -> bool:
        return self.directive.startswith("SKIP")

    # Whether the directive marks the test as still to do.
    @property
    def todo(self) -> bool:
        return self.directive.startswith("TODO")


# A plan line: its depth and the number of points it plans.
class Plan(NamedTuple):
    depth: int
    expected_tests: int


# A diagnostic line: its depth and its text.
class Diagnostic(NamedTuple):
    depth: int
    text: str


# A bail out line: its depth and its reason, empty when it gives none.
class Bail(NamedTuple):
    depth: int
    reason: str


# The version line: the version it names.
class Version(NamedTuple):
    version: int


# Any other line: its text.
class Unknown(NamedTuple):
    text: str


# Any line kind the parser returns.
Line: TypeAlias = Result | Plan | Diagnostic | Bail | Version | Unknown


# What a document held: its planned points, its counts, and whether it fits.
class TapStats(NamedTuple):
    plan: int
    passed: int
    failed: int
    skipped: int
    well_formed: bool


# Reads TAP text into line kinds, as tappy's parser does, with their depths.
class Parser:
    # Yields the kind of each line of the text, a last one with no newline too.
    def parse_text(self, text: str) -> Iterator[Line]:
        for line in io.StringIO(text, newline="\n"):
            yield self.parse_line(line.removesuffix("\n"))

    # Returns the kind of one line, given without its newline.
    def parse_line(self, text: str) -> Line:
        if found := _VERSION_PATTERN.fullmatch(text):
            return Version(int(found[1]))
        if found := _PLAN_PATTERN.fullmatch(text):
            indent, total = found.groups("")
            return Plan(len(indent) // _INDENT_WIDTH, int(total))
        if found := _RESULT_PATTERN.fullmatch(text):
            indent, negation, number, description, directive = found.groups("")
            return Result(
                len(indent) // _INDENT_WIDTH,
                not negation,
                int(number),
                description,
                directive,
            )
        if found := _DIAGNOSTIC_PATTERN.fullmatch(text):
            indent, line = found.groups("")
            return Diagnostic(len(indent) // _INDENT_WIDTH, line)
        if found := _BAIL_PATTERN.fullmatch(text):
            indent, reason = found.groups("")
            return Bail(len(indent) // _INDENT_WIDTH, reason)
        return Unknown(text)


# Checks a stream line by line against the producers' grammar and counts it.
class StreamReader:
    # Starts before the version line, with every count at zero.
    def __init__(self) -> None:
        self.plan = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self._state = "version"
        self._parents = 0
        self._planned = 0
        self._points = 0
        self._block_failed = False
        self._last_failed = False

    # Whether the stream ended, with its parent plan or a bail out line.
    def stream_ended(self) -> bool:
        return self._state in ("ended", "bailed")

    # Takes the next line and returns whether it fits where it stands.
    def line_read(self, line: Line) -> bool:
        match self._state, line:
            case "version", Version(version=found) if found == _TAP_VERSION:
                self._state = "between"
            case "between", Plan(depth=1, expected_tests=total):
                self._block_open(total)
            case "between", Plan(depth=0, expected_tests=total):
                return self._stream_close(total)
            case "block", Result(depth=1) as point:
                return self._point_count(point)
            case "block", Diagnostic(depth=1) if self._points:
                pass
            case "block", Result(depth=0) as parent:
                return self._parent_read(parent)
            case "version" | "between" | "block", Bail(depth=0):
                self._bail_read()
            case "bailed", _:
                # Reading stopped at the bail out, so the line is ignored.
                pass
            case _:
                return False
        return True

    # Ends the stream, one failure more unless the last point read failed.
    def _bail_read(self) -> None:
        if not (self._state == "block" and self._last_failed):
            self.failed += 1
        self._state = "bailed"

    # Opens a block with the number of points its plan line names.
    def _block_open(self, total: int) -> None:
        self.plan += total
        self._planned = total
        self._points = 0
        self._block_failed = False
        self._last_failed = False
        self._state = "block"

    # Ends the stream when the parent plan counts the blocks closed so far.
    def _stream_close(self, total: int) -> bool:
        if total != self._parents:
            return False
        self._state = "ended"
        return True

    # Counts the next point of the block, refusing a failed one with a skip.
    def _point_count(self, point: Result) -> bool:
        if point.number != self._points + 1 or (point.skip and not point.ok):
            return False
        self._points += 1
        self._last_failed = not point.ok and not point.todo
        self._block_failed = self._block_failed or self._last_failed
        if self._last_failed:
            self.failed += 1
        elif point.skip:
            self.skipped += 1
        else:
            self.passed += 1
        return True

    # Closes the block with a parent line of the next number, graded by it.
    def _parent_read(self, parent: Result) -> bool:
        if (
            parent.number != self._parents + 1
            or parent.ok == self._block_failed
            or parent.directive
            or self._points != self._planned
        ):
            return False
        self._parents += 1
        self._state = "between"
        return True


# Takes a whole document and returns its stats. Its last line needs a newline.
def document_stats(text: str) -> TapStats:
    reader = StreamReader()
    fits = all(reader.line_read(line) for line in Parser().parse_text(text))
    well_formed = fits and reader.stream_ended() and text.endswith("\n")
    return TapStats(
        reader.plan, reader.passed, reader.failed, reader.skipped, well_formed
    )
