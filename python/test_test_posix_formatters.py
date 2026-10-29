# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the formatter step of test_posix.py with the real formatters of
# reformat_table.json, a later suite that waits on ruff. The step runs in a
# forked child whose stdout and stderr go to a scratch file under build/, so
# that neither the advisory nor a formatter writes to the stream. A
# smoke-test run prints its advisory first and only checks, ruff's checker
# refusing a Python file it would change and leaving it as it is, and a
# normal-test run prints no advisory and formats the file.

import functools, harness, json, os, signal, subprocess, sys, tempfile
import test_posix, traceback, unittest
from collections.abc import Callable

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The gold of the advisory, which the integration suite of the step holds.
_ADVISORY_ID = "python.test_integrate_test_posix.check_advisory"

# The advisory a `smoke-test` run prints before it checks.
_ADVISORY: str = harness.gold_get(_ADVISORY_ID)

# The category that only checks the formatting.
_SMOKE_TEST = "smoke-test"

# The category that does the reformatting.
_NORMAL_TEST = "normal-test"

# The options of each ruff command of the table, its configuration and cache.
_RUFF_OPTIONS = [
    "--config",
    "python/pyproject.toml",
    "--cache-dir",
    "build/ruff_cache",
]

# The Python row's checker, before its files.
_PYTHON_CHECKER = ["ruff", "format", "--check", *_RUFF_OPTIONS]

# Python that ruff changes.
_PYTHON_RAW = "x=1\n"

# That Python as ruff formats it.
_PYTHON_FORMATTED = "x = 1\n"

# How the work of a child ended when it returned.
_ENDING_RETURNED = "returned"

# The start of how the work of a child ended when a command it ran failed.
_ENDING_FAILED = "failed: "


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
        except subprocess.CalledProcessError as error:
            ending = _ENDING_FAILED + json.dumps(error.cmd)
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

    # A `smoke-test` run prints the advisory, then only checks the files.
    def test_smoke_checked(self) -> None:
        path = self.file_write("b.py", _PYTHON_RAW)
        ending, output = self.step_run(_SMOKE_TEST, path)
        failed = _ENDING_FAILED + json.dumps([*_PYTHON_CHECKER, path])
        self.assertEqual(ending, failed)
        self.assertTrue(output.startswith(_ADVISORY + "\n"), output)
        self.assertEqual(text_read(path), _PYTHON_RAW)

    # A `normal-test` run formats the files and prints no advisory.
    def test_normal_formatted(self) -> None:
        path = self.file_write("b.py", _PYTHON_RAW)
        ending, output = self.step_run(_NORMAL_TEST, path)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertNotIn(_ADVISORY, output)
        self.assertEqual(text_read(path), _PYTHON_FORMATTED)
