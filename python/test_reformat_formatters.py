# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests reformat's check and formatting with the real formatters of
# reformat_table.json, a later suite that waits on ruff, shfmt and prettier.
# Each check or formatting runs in a forked child whose stdout and stderr go
# to a scratch file under build/, so that no formatter writes to the stream.
# A file its formatter would change is refused by its row's checker and left
# as it is, and a formatting rewrites the files of the Python and shell rows,
# which their checkers then pass. Prettier skips the files .gitignore lists,
# build/ among them, so the TypeScript row's checker runs on a formatted file
# of the checkout, which it passes as it is.

import functools, json, os, reformat, signal, subprocess, sys, tempfile
import traceback, unittest
from collections.abc import Callable

# The checkout's top directory, where the formatters run.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The options of each ruff command of the table, its configuration and cache.
_RUFF_OPTIONS = [
    "--config",
    "python/pyproject.toml",
    "--cache-dir",
    "build/ruff_cache",
]

# The Python row's checker, before its files.
_PYTHON_CHECKER = ["ruff", "format", "--check", *_RUFF_OPTIONS]

# The shell row's checker, before its files.
_SHELL_CHECKER = ["shfmt", "--diff"]

# Python that ruff changes.
_PYTHON_RAW = "x=1\n"

# That Python as ruff formats it.
_PYTHON_FORMATTED = "x = 1\n"

# Shell that shfmt changes.
_SHELL_RAW = "echo  a\n"

# That shell as shfmt formats it.
_SHELL_FORMATTED = "echo a\n"

# A formatted TypeScript file of the checkout, outside the gitignored build/.
_TYPESCRIPT_PATH = os.path.join(_ROOT_PATH, "ts", "utility.ts")

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


# The check of each Linux row, which rewrites nothing.
class TestCheck(ChildCase):
    # A check starts each Linux row's checker on its files, rewriting none.
    def test_check_commands(self) -> None:
        for name, text, checker in (
            ("b.py", _PYTHON_RAW, _PYTHON_CHECKER),
            ("b.sh", _SHELL_RAW, _SHELL_CHECKER),
        ):
            path = self.file_write(name, text)
            work = functools.partial(reformat.format_check, [path])
            ending, _ = self.child_run(work)
            failed = _ENDING_FAILED + json.dumps([*checker, path])
            self.assertEqual(ending, failed, name)
            self.assertEqual(text_read(path), text, name)

    # The TypeScript row's checker passes a formatted file as it is.
    def test_check_formatted(self) -> None:
        before = text_read(_TYPESCRIPT_PATH)
        work = functools.partial(reformat.format_check, [_TYPESCRIPT_PATH])
        ending, _ = self.child_run(work)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(text_read(_TYPESCRIPT_PATH), before)


# The formatting of each Linux row, whose checker then passes its files.
class TestFormat(ChildCase):
    # A formatting starts each Linux row's formatter on its files.
    def test_format_commands(self) -> None:
        python_path = self.file_write("b.py", _PYTHON_RAW)
        shell_path = self.file_write("b.sh", _SHELL_RAW)
        paths = [python_path, shell_path]
        ending, _ = self.child_run(functools.partial(reformat.reformat, paths))
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(text_read(python_path), _PYTHON_FORMATTED)
        self.assertEqual(text_read(shell_path), _SHELL_FORMATTED)
        work = functools.partial(reformat.format_check, paths)
        ending, _ = self.child_run(work)
        self.assertEqual(ending, _ENDING_RETURNED)
