# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests test_posix.py with its project callees, category.py and reformat.py,
# whose suites have passed: its formatter step in each category, given
# PowerShell files, which the Linux rows of reformat_table.json leave to
# Windows, so that no formatter starts. The step runs in a forked child
# whose stdout and stderr go to a scratch file under build/, so that nothing
# it prints reaches the stream. A smoke-test run prints its advisory and
# checks, and a normal-test run prints nothing and formats.

import functools, harness, os, signal, sys, tempfile, test_posix, traceback
import unittest
from collections.abc import Callable

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_test_posix"

# The advisory a `smoke-test` run prints before it checks.
_ADVISORY: str = harness.gold_get(f"{_GOLD_ID}.check_advisory")

# The category that only checks the formatting.
_SMOKE_TEST = "smoke-test"

# The category that does the reformatting.
_NORMAL_TEST = "normal-test"

# The PowerShell files the step is given, which no Linux row formats.
_WINDOWS_NAMES = ["a.ps1", "a.psd1"]

# How the work of a child ended when it returned.
_ENDING_RETURNED = "returned"


# Returns the text of the file.
def text_read(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


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


# The formatter step of each category, on the real category and reformat.
class TestFormatterStep(ChildCase):
    # Runs the step of the category on empty PowerShell files in a child.
    def step_run(self, chosen: str) -> tuple[str, str]:
        paths = [self.file_write(name, "") for name in _WINDOWS_NAMES]
        work = functools.partial(test_posix.formatter_run, paths, chosen)
        return self.child_run(work)

    # A `smoke-test` run prints the advisory, then checks with no command.
    def test_smoke_checked(self) -> None:
        ending, output = self.step_run(_SMOKE_TEST)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, _ADVISORY + "\n")

    # A `normal-test` run formats with no command and prints nothing.
    def test_normal_formatted(self) -> None:
        ending, output = self.step_run(_NORMAL_TEST)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, "")
