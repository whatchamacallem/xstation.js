# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Reads a TAP version 14 stream in the form the producer writes and returns
# the plan and counts of the test points inside its subtest blocks, and
# whether it is well formed. Reading stops at the first fault: the counts are
# those of the lines before it.

import re
from typing import NamedTuple

# The line that ends a failfast stream after its first failure.
_BAIL_LINE = "Bail out! failfast"

# What starts each traceback line, allowed only under a failed test point.
_DIAGNOSTIC_PREFIX = "    # "

# A test point in a block: its word, its number and any `SKIP` directive.
_POINT_LINE = re.compile(
    r"    (ok|not ok) ([0-9]+) - [^#]*?( # SKIP(?: .*)?)?"
)

# What starts the line that opens a module's block, before its name.
_SUBTEST_PREFIX = "    # Subtest: "

# The first line of every stream.
_VERSION_LINE = "TAP version 14"


# What a stream held: its plan, the counts, and whether it was well formed.
class TapStats(NamedTuple):
    plan: int
    ok: int
    not_ok: int
    skip: int
    well_formed: bool


# Reads a stream line by line, counting the test points inside its blocks.
class _StreamReader:
    # Starts with every count at zero.
    def __init__(self) -> None:
        self.plan = 0
        self.ok = 0
        self.not_ok = 0
        self.skip = 0

    # Returns whether the lines are a whole stream, counting until a fault.
    def lines_check(self, lines: list[str]) -> bool:
        state = "version"
        blocks = 0
        module = ""
        points = 0
        failed = False
        last_failed = False
        for line in lines:
            if state == "version" and line == _VERSION_LINE:
                state = "between"
            elif state == "between" and line == f"1..{blocks}":
                state = "planned"
            elif state == "between" and line.startswith(_SUBTEST_PREFIX):
                module = line.removeprefix(_SUBTEST_PREFIX)
                if "#" in module:
                    return False
                points = 0
                failed = False
                last_failed = False
                state = "block"
            elif state == "block" and line.startswith(_DIAGNOSTIC_PREFIX):
                if not last_failed:
                    return False
            elif state == "block" and line == f"    1..{points}":
                self.plan += points
                state = "parent"
            elif state == "block" and line == _BAIL_LINE and last_failed:
                state = "bailed"
            elif state == "block":
                point = _POINT_LINE.fullmatch(line)
                if point is None or point[2] != str(points + 1):
                    return False
                points += 1
                last_failed = point[1] == "not ok"
                if last_failed and point[3] is not None:
                    return False
                if last_failed:
                    failed = True
                    self.not_ok += 1
                elif point[3] is None:
                    self.ok += 1
                else:
                    self.skip += 1
            elif state == "parent":
                word = "not ok" if failed else "ok"
                if line != f"{word} {blocks + 1} - {module}":
                    return False
                blocks += 1
                state = "between"
            else:
                return False
        return state in ("planned", "bailed")


# Takes a whole TAP document and returns its stats. Subtest blocks count.
def document_stats(text: str) -> TapStats:
    lines = text.split("\n")
    rest = lines.pop()
    reader = _StreamReader()
    well_formed = reader.lines_check(lines) and rest == ""
    return TapStats(
        reader.plan, reader.ok, reader.not_ok, reader.skip, well_formed
    )
