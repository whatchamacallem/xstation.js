# Line coverage of modules by their own unit suites, counted with the LINE
# events of `sys.monitoring` in the process that counts, standard library
# only, its texts plain English. The lines that count are those that hold
# code: the lines of `co_lines()` over every code object of a file, found
# through `co_consts`, leaving out the `__annotate__` code of deferred
# annotations, which runs only when the annotations are read. A line of
# module or class body code counts whenever it ran; a line of a function
# counts only while a suite of its file runs. A location turns itself off
# at its first event, and a suite's start turns every location on again. A
# forked child, which may end by SIGKILL, marks each line of the suite's
# files it runs in memory it shares with the counting process, which takes
# the marks as counted at the suite's end. A line a forked child runs of any
# other file, or that a program started by the process runs, is not
# counted. A statement whose first line ends with `# pragma: no cover` is
# exempt, with the block that line opens, as coverage.py does; the mark is
# put only on a line that raises "internal error". Files are compared by
# their real paths.

from collections.abc import Iterable

# The lines run since it started, on a `sys.monitoring` tool id of its own.
class LineCount:
    # Starts counting, on the first free tool id from `COVERAGE_ID` up.
    def __init__(self) -> None: ...
    # From now, the function lines of these files count, until `suite_leave`.
    def suite_enter(self, paths: Iterable[str]) -> None: ...
    # Counts what forked children marked, then stops counting function lines.
    def suite_leave(self) -> None: ...
    # Raises at the first line that holds code, not exempt, never counted.
    def lines_check(self, path: str) -> None: ...
    # Stops counting and frees the tool id. What was counted stays.
    def count_stop(self) -> None: ...
