# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Line coverage of modules by their own unit suites, counted with the LINE
# events of `sys.monitoring` in the process that counts. It imports the
# standard library only, and its texts are plain English. The lines that
# count are those that hold code: the lines of `co_lines()` over every code
# object of a file, found through `co_consts`, leaving out the
# `__annotate__` code of deferred annotations, which runs only when the
# annotations are read. A line of module or class body code counts whenever
# it ran; a line of a function counts only while a suite of its file runs.
# The callback returns `DISABLE`, so that a location fires once and the run
# stays fast, and a suite's start turns every location on again. A forked
# child, which may end by SIGKILL, marks each line of the suite's files it
# runs in anonymous memory shared with the counting process, which counts
# the marks at the suite's end. A line a forked child runs of any other
# file, or that a program started by the process runs, is not counted. A
# statement whose first line ends with `# pragma: no cover` is exempt, with
# the block that line opens, as coverage.py does. Files are compared by
# their real paths.

import ast, collections, inspect, mmap, os, sys, types
from collections.abc import Iterable

# The mark that exempts a statement and the block its first line opens.
_EXEMPT_MARK = "# pragma: no cover"

# The name of the code that evaluates deferred annotations when read.
_ANNOTATE_NAME = "__annotate__"

# The tool ids a count may take, in turn: of the ids 0 to 5, the coverage
# tool's and those after it, leaving the debugger's.
_TOOL_IDS = range(sys.monitoring.COVERAGE_ID, 6)

# The name a count's tool id carries.
_TOOL_NAME = "line_coverage"

# The statements whose first line opens a block, their `body`.
_BLOCK_STATEMENTS = (
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.ClassDef,
    ast.For,
    ast.FunctionDef,
    ast.If,
    ast.Try,
    ast.TryStar,
    ast.While,
    ast.With,
)


# The lines run since it started, on a `sys.monitoring` tool id of its own.
class LineCount:
    # Starts counting, on the first free tool id from `COVERAGE_ID` up.
    def __init__(self) -> None:
        free = [id for id in _TOOL_IDS if sys.monitoring.get_tool(id) is None]
        if not free:
            raise RuntimeError("internal error")  # pragma: no cover
        self._tool = free[0]
        # The process that counts, which its forked children are not.
        self._pid = os.getpid()
        # The real path of each file name a code object gives.
        self._paths: dict[str, str] = {}
        # The real paths of the files whose function lines count now, each
        # with a byte for each line number, which a forked child sets.
        self._suite: dict[str, mmap.mmap] = {}
        # The lines counted as run, by the real path of their file.
        self._run: collections.defaultdict[str, set[int]] = (
            collections.defaultdict(set)
        )
        sys.monitoring.use_tool_id(self._tool, _TOOL_NAME)
        sys.monitoring.register_callback(
            self._tool, sys.monitoring.events.LINE, self._line_note
        )
        sys.monitoring.set_events(self._tool, sys.monitoring.events.LINE)

    # From now, the function lines of these files count, until `suite_leave`.
    def suite_enter(self, paths: Iterable[str]) -> None:
        self._suite = {
            real: mmap.mmap(-1, len(_source_read(real).split("\n")) + 1)
            for real in {os.path.realpath(path) for path in paths}
        }
        # A function line turned off outside a suite fires again in this one.
        sys.monitoring.restart_events()

    # Counts the lines the suite's forked children marked; from now, the
    # function lines of no file count.
    def suite_leave(self) -> None:
        for path, marks in self._suite.items():
            lines = range(len(marks))
            self._run[path].update(line for line in lines if marks[line])
            marks.close()
        self._suite = {}

    # Raises at the first line that holds code, not exempt, never counted.
    def lines_check(self, path: str) -> None:
        source = _source_read(path)
        held = _lines_held(compile(source, path, "exec"))
        exempt = _lines_exempt(source)
        unrun = held - exempt - self._run[os.path.realpath(path)]
        if unrun:
            raise RuntimeError(
                f"line {min(unrun)} of {path} was never counted as run"
            )

    # Stops counting and frees the tool id. What was counted stays.
    def count_stop(self) -> None:
        sys.monitoring.set_events(self._tool, sys.monitoring.events.NO_EVENTS)
        sys.monitoring.register_callback(
            self._tool, sys.monitoring.events.LINE, None
        )
        sys.monitoring.free_tool_id(self._tool)

    # The LINE callback: counts the line if it counts now, and turns it off.
    def _line_note(self, code: types.CodeType, line: int) -> object:
        name = code.co_filename
        if name not in self._paths:
            self._paths[name] = os.path.realpath(name)
        path = self._paths[name]
        if path in self._suite and os.getpid() != self._pid:
            # A forked child marks the line for the counting process to read.
            self._suite[path][line] = 1
        # Function code is optimized; module and class body code is not.
        elif path in self._suite or not code.co_flags & inspect.CO_OPTIMIZED:
            self._run[path].add(line)
        return sys.monitoring.DISABLE


# The text of a Python file, as it is compiled.
def _source_read(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


# The lines that hold code: those of every code object but annotation code.
def _lines_held(module: types.CodeType) -> set[int]:
    held: set[int] = set()
    codes = [module]
    while codes:
        code = codes.pop()
        if code.co_name == _ANNOTATE_NAME:
            continue
        # None, or the 0 of the module's first instruction, is no line.
        held.update(line for _, _, line in code.co_lines() if line)
        codes.extend(
            const
            for const in code.co_consts
            if isinstance(const, types.CodeType)
        )
    return held


# The exempt lines: from the first line of each statement that ends with the
# mark to the end of the block that line opens, or else of the statement.
def _lines_exempt(source: str) -> set[int]:
    lines = source.split("\n")
    exempt: set[int] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.stmt):
            continue
        if not lines[node.lineno - 1].rstrip().endswith(_EXEMPT_MARK):
            continue
        if isinstance(node, _BLOCK_STATEMENTS):
            end = node.body[-1].end_lineno
        else:
            end = node.end_lineno
        if end is None:
            raise RuntimeError("internal error")  # pragma: no cover
        exempt.update(range(node.lineno, end + 1))
    return exempt
