# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests test_posix.py with its project callees, category.py, page_build.py,
# reformat.py and switches.py, whose suites have passed: its formatter step in
# each category, so that no formatter starts, and its switch of the cloud
# environment. Each runs in a forked child whose stdout and stderr go to a
# scratch file under build/, so that nothing it prints reaches the stream. A
# smoke-test run, given a Python file that ruff would change, prints nothing
# and leaves the file as it is; a test-all run, given PowerShell files, which
# the Linux rows of reformat_table.json leave to Windows, prints nothing and
# formats. With no program on PATH, which neither a linter nor tsc could start
# from, main returns and prints nothing when given --anthropic, and when
# test_all.py has turned the switch on before calling it. Under the switch
# test_all.py leaves the suites that start formatters out of a test-all run,
# and --module refuses them, while without it the run takes them. Every suite
# of a test-all run counts under --coverage for modules that exist, the
# store's limit suite for the store. A disabled suite runs when --module names
# it or at the disabled level, and each level's option only raises a run.

import argparse, contextlib, functools, io, os, signal, switches, sys, tempfile
import test_all, test_posix, traceback, unittest
from collections.abc import Callable

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The category that runs no formatter.
_SMOKE_TEST = "smoke-test"

# The category that does the reformatting.
_TEST_ALL = "test-all"

# The category that also takes what is disabled.
_TEST_DISABLED = "test-disabled"

# The PowerShell files the step is given, which no Linux row formats.
_WINDOWS_NAMES = ["a.ps1", "a.psd1"]

# Python that ruff would change, which a `smoke-test` run leaves as it is.
_PYTHON_RAW = "x=1\n"

# How the work of a child ended when it returned.
_ENDING_RETURNED = "returned"

# The suites that start formatters, as a run lists them.
_FORMATTER_SUITES = ["test_reformat_formatters", "test_test_posix_formatters"]

# How a child ended that a refusal of its parser stopped.
_ENDING_REFUSED = "SystemExit: 2\n"

# The suite of the store's limit, which no module is named after.
_LIMIT_SUITE = "test_substrate_limit"

# The store module, which that suite counts for.
_STORE_PATH = os.path.join(_ROOT_PATH, "python", "substrate.py")

# A suite the test driver has disabled, which starts a Chrome for each test.
_DISABLED_SUITE = "test_devtools_chrome"

# The module that suite counts for.
_DISABLED_PATH = os.path.join(_ROOT_PATH, "python", "devtools.py")

# The options of the stream, each of which raises a run to the normal level.
_STREAM_OPTIONS = [
    ["--stream"],
    ["--module", "test_jslb"],
    ["--failfast"],
    ["--failures", "1"],
    ["--tty"],
    ["--coverage"],
]

# The options of each level above end to end, and the category each gives.
_LEVELS = [
    (["--test-normal"], _SMOKE_TEST),
    (["--test-all"], _TEST_ALL),
    (["--test-disabled"], _TEST_DISABLED),
    (["--test-normal", "--test-all"], _TEST_ALL),
    (["--test-all", "--test-normal"], _TEST_ALL),
    (["--test-normal", "--test-disabled"], _TEST_DISABLED),
    (["--test-disabled", "--test-all"], _TEST_DISABLED),
]

# The option a run's level once was, which the driver no longer knows.
_REMOVED_OPTION = "--end-to-end"


# Returns the text of the file.
def text_read(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


# Has the test driver choose the named suite of a `test-all` run.
def module_choose(name: str) -> None:
    test_all.modules_chosen(argparse.ArgumentParser(), [name], _TEST_ALL)


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
    # Runs the step of the category on the files in a child.
    def step_run(self, chosen: str, paths: list[str]) -> tuple[str, str]:
        work = functools.partial(test_posix.formatter_run, paths, chosen)
        return self.child_run(work)

    # A `smoke-test` run prints nothing and leaves the files alone.
    def test_smoke_untouched(self) -> None:
        path = self.file_write("b.py", _PYTHON_RAW)
        ending, output = self.step_run(_SMOKE_TEST, [path])
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, "")
        self.assertEqual(text_read(path), _PYTHON_RAW)

    # A `test-all` run formats with no command and prints nothing.
    def test_normal_formatted(self) -> None:
        paths = [self.file_write(name, "") for name in _WINDOWS_NAMES]
        ending, output = self.step_run(_TEST_ALL, paths)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, "")


# The switch of the cloud environment, which skips every check.
class TestAnthropicSwitch(ChildCase):
    # Runs main in a child that finds no program, so no linter or tsc starts.
    def main_run(self, arguments: list[str]) -> tuple[str, str]:
        def work() -> None:
            os.environ["PATH"] = self.scratch
            test_posix.main(arguments)

        return self.child_run(work)

    # Given to `test_posix.py`, the switch has it return, printing nothing.
    def test_option_skipped(self) -> None:
        ending, output = self.main_run(["--anthropic"])
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, "")

    # Set by the test driver before its call, the switch does the same.
    def test_driver_skipped(self) -> None:
        def work() -> None:
            parser = argparse.ArgumentParser()
            switches.options_add(parser)
            switches.switches_set(parser.parse_args(["--anthropic"]))
            os.environ["PATH"] = self.scratch
            test_posix.main([])

        ending, output = self.child_run(work)
        self.assertEqual(ending, _ENDING_RETURNED)
        self.assertEqual(output, "")


# The suites the test driver takes, in a child with the switch set as given.
class TestDriverSuites(ChildCase):
    # Runs the work in a child, the switch of the cloud environment as given.
    def switch_run(
        self, anthropic: bool, work: Callable[[], None]
    ) -> tuple[str, str]:
        def switched() -> None:
            switches.switches_apply(
                {**switches.switches_get(), "anthropic": anthropic}
            )
            work()

        return self.child_run(switched)

    # Returns what a child prints of the suites of a `test-all` run.
    def suites_chosen(self, anthropic: bool) -> str:
        def work() -> None:
            parser = argparse.ArgumentParser()
            modules = test_all.modules_chosen(parser, [], _TEST_ALL)
            names = [name for name, _ in modules]
            print(*(name for name in _FORMATTER_SUITES if name in names))

        ending, output = self.switch_run(anthropic, work)
        self.assertEqual(ending, _ENDING_RETURNED)
        return output

    # Under the switch, a `test-all` run takes no suite of a formatter.
    def test_formatters_left(self) -> None:
        self.assertEqual(self.suites_chosen(True), "\n")

    # Without the switch, a `test-all` run takes them.
    def test_formatters_taken(self) -> None:
        expected = " ".join(_FORMATTER_SUITES) + "\n"
        self.assertEqual(self.suites_chosen(False), expected)

    # Under the switch, `--module` refuses each suite of a formatter.
    def test_module_refused(self) -> None:
        for name in _FORMATTER_SUITES:
            work = functools.partial(module_choose, name)
            ending, output = self.switch_run(True, work)
            self.assertTrue(ending.endswith(_ENDING_REFUSED), ending)
            expected = f"--module {name} is not a suite of this {_TEST_ALL}"
            self.assertIn(expected, output)


# The modules the test driver counts each suite for under `--coverage`.
class TestDriverCounted(unittest.TestCase):
    # The suite of the store's limit counts for the store module.
    def test_limit_counted(self) -> None:
        counted = test_all.paths_counted(_LIMIT_SUITE)
        self.assertEqual(counted, [_STORE_PATH])

    # Every suite of a `test-all` run counts for modules that exist.
    def test_modules_present(self) -> None:
        parser = argparse.ArgumentParser()
        for name, _ in test_all.modules_chosen(parser, [], _TEST_ALL):
            for path in test_all.paths_counted(name):
                self.assertTrue(os.path.isfile(path), path)


# The suites the test driver has disabled, which run only when named.
class TestDriverDisabled(unittest.TestCase):
    # No run takes a disabled suite, and its module is left unchecked.
    def test_disabled_left(self) -> None:
        parser = argparse.ArgumentParser()
        modules = test_all.modules_chosen(parser, [], _TEST_ALL)
        self.assertNotIn(_DISABLED_SUITE, [name for name, _ in modules])
        self.assertIn(_DISABLED_PATH, test_all.paths_unchecked(modules))

    # `--module` runs a disabled suite, and its module is then checked.
    def test_disabled_named(self) -> None:
        parser = argparse.ArgumentParser()
        named = [_DISABLED_SUITE]
        modules = test_all.modules_chosen(parser, named, _TEST_ALL)
        self.assertEqual([name for name, _ in modules], named)
        self.assertNotIn(_DISABLED_PATH, test_all.paths_unchecked(modules))

    # A `test-disabled` run takes each disabled suite, and checks its module.
    def test_disabled_level(self) -> None:
        parser = argparse.ArgumentParser()
        modules = test_all.modules_chosen(parser, [], _TEST_DISABLED)
        self.assertIn(_DISABLED_SUITE, [name for name, _ in modules])
        self.assertNotIn(_DISABLED_PATH, test_all.paths_unchecked(modules))


# The level of a run, which its options only raise.
class TestDriverLevels(unittest.TestCase):
    # With no option the run has no stream, and its rungs are of `smoke-test`.
    def test_default_end(self) -> None:
        parsed = test_all.parser_make().parse_args([])
        self.assertFalse(test_all.stream_wanted(parsed))
        self.assertEqual(parsed.category, _SMOKE_TEST)

    # Each level above end to end has a stream, the higher of two options won.
    def test_levels_raised(self) -> None:
        for words, chosen in _LEVELS:
            with self.subTest(words=words):
                parsed = test_all.parser_make().parse_args(words)
                self.assertTrue(test_all.stream_wanted(parsed))
                self.assertEqual(parsed.category, chosen)

    # An option of the stream raises the run to normal, not higher.
    def test_stream_raised(self) -> None:
        for words in _STREAM_OPTIONS:
            with self.subTest(words=words):
                parsed = test_all.parser_make().parse_args(words)
                self.assertTrue(test_all.stream_wanted(parsed))
                self.assertEqual(parsed.category, _SMOKE_TEST)

    # The option the default level took the place of is gone.
    def test_removed_refused(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                test_all.parser_make().parse_args([_REMOVED_OPTION])
        self.assertEqual(caught.exception.code, 2)
