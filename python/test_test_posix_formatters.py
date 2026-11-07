# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the formatter step of test_posix.py with the real formatters of
# reformat_table.json, ruff among them, and the whole program. Each runs in a
# forked child whose stdout and stderr go to a scratch file under build/, so
# that no formatter writes to the stream. A test-all run formats a Python file
# with ruff and prints nothing. Run as a program with no option, test_posix.py
# checks the checkout's whitelisted files, lints them with ruff and compiles
# the API text with tsc, formatting nothing and printing nothing, which is why
# that test is in this suite, one the cloud environment leaves out. Given
# --anthropic with no program on PATH, which neither a linter nor tsc could
# start from, it returns and prints nothing.

import functools, os, runpy, signal, sys, tempfile, test_posix, traceback
import unittest
from collections.abc import Callable

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The category that does the reformatting.
_TEST_ALL = "test-all"

# Python that ruff changes.
_PYTHON_RAW = "x=1\n"

# That Python as ruff formats it.
_PYTHON_FORMATTED = "x = 1\n"

# How the work of a child ended when it returned.
_ENDING_RETURNED = "returned"

# The module's file, as a command line starts it.
_PROGRAM_PATH = os.path.join(_ROOT_PATH, "python", "test_posix.py")


# Returns the text of the file.
def text_read(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


# In the forked child: runs the module's file as a program of the arguments.
def program_run(arguments: list[str]) -> None:
    sys.argv = [_PROGRAM_PATH, *arguments]
    runpy.run_path(_PROGRAM_PATH, run_name="__main__")


# In the forked child: runs the work, output to a file, writes its ending.
def child_end(
    work: Callable[[], None], output_path: str, ending_path: str
) -> None:
    try:
        try:
            with open(output_path, "xb") as output:
                os.dup2(output.fileno(), 1)
                os.dup2(output.fileno(), 2)
            work()
            ending = _ENDING_RETURNED
        except BaseException:
            ending = traceback.format_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        with open(ending_path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a scratch directory, and runs its work in forked children.
class ChildCase(unittest.TestCase):
    # Makes the scratch directory.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )

    # Writes the text to the named file of the scratch directory.
    def file_write(self, name: str, text: str) -> str:
        path = os.path.join(self.scratch, name)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path

    # Runs the work in a forked child, returns how it ended and its output.
    def child_run(self, work: Callable[[], None]) -> tuple[str, str]:
        output_path = os.path.join(self.scratch, "output.txt")
        ending_path = os.path.join(self.scratch, "ending.txt")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            child_end(work, output_path, ending_path)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        ending = text_read(ending_path)
        output = text_read(output_path)
        os.remove(ending_path)
        os.remove(output_path)
        return ending, output


# The formatter step of each category, on the real formatters.
class TestFormatterStep(ChildCase):
    # Runs the step of the category on the file in a child.
    def step_run(self, chosen: str, path: str) -> tuple[str, str]:
        work = functools.partial(test_posix.formatter_run, [path], chosen)
        return self.child_run(work)

    # A `test-all` run formats the file and prints nothing.
    def test_normal_formatted(self) -> None:
        path = self.file_write("b.py", _PYTHON_RAW)
        ending, output = self.step_run(_TEST_ALL, path)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, "")
        self.assertEqual(text_read(path), _PYTHON_FORMATTED)


# The whole program, as a command line starts it.
class TestProgramRun(ChildCase):
    # With no option it checks, lints and compiles the API, printing nothing.
    def test_files_checked(self) -> None:
        ending, output = self.child_run(functools.partial(program_run, []))
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, "")

    # With no program to start, the switch of the cloud environment returns.
    def test_switch_skipped(self) -> None:
        def work() -> None:
            os.environ["PATH"] = self.scratch
            program_run(["--anthropic"])

        ending, output = self.child_run(work)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, "")
