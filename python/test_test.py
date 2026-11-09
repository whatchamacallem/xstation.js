# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of the infrastructure for testing: the harness on the checkout's own
# settings.json and every suite's gold file, each also read with `json` as the
# oracle; category, with no real alarm armed, since the runner's alarm of this
# module is running; and line coverage on sample modules written to a scratch
# directory in build/ and run with `runpy`, their functions called in this
# process or in a forked child ended by SIGKILL.

import argparse, category, contextlib, harness, io, json, line_coverage, os
import runpy, signal, tempfile, unittest
from typing import Any, cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The settings file the harness reads, at the checkout's top.
_SETTINGS_NAME = "settings.json"

# The directory of each language's suites, which holds their gold files.
_LANGUAGE_DIRECTORIES = {
    "python": "python",
    "typescript": "ts",
    "powershell": "powershell",
}

# The start and the end of a suite's gold file name, around the suite.
_GOLD_PREFIX = "test_setting_"
_GOLD_SUFFIX = ".json"

# The id of this module's gold, its file `python/test_setting_test_test.json`.
_GOLD_ID = "python.test_test"

# This module's gold file, as the harness's refusals name it.
_GOLD_FILE = "python/test_setting_test_test.json"

# The driver's gold file, which holds the run's `smoke_seconds`.
_DRIVER_FILE = "python/test_setting_test_all.json"

# The list this module's gold holds under `limits`.
_LIMITS = [1, 2]

# The label and category of the important suites that fit in 3 minutes.
_SMOKE_TEST = "smoke-test"

# The label and category of every other suite.
_TEST_ALL = "test-all"

# The category of both labels and what is disabled.
_TEST_DISABLED = "test-disabled"

# The refusal of the category `all`, which is none of the three.
_ALL_REFUSED = (
    "the category 'all' is none of smoke-test, test-all and test-disabled"
)

# The mark that exempts a statement and the block its first line opens.
_MARK = "# pragma: no cover"

# Sample module: import, constant, class with method, function of two branches.
_SHAPES = """\
import os

_NAME = os.path.basename("shapes.py")


class Square:
    sides = 4

    def area(self, side):
        return side * side


def parity(number):
    if number % 2:
        return "odd"
    return "even"
"""

# The first function line of `_SHAPES`, the body of `Square.area`.
_AREA_LINE = 10

# The line of `_SHAPES` that only an even number runs.
_EVEN_LINE = 16

# Sample exempt in the marked `if` block, never run, and `raise`, not `else`.
_EXEMPT = """\
def sign(value):
    if value < 0:  {mark}
        raise RuntimeError("internal error")
    else:
        return 1


def fail():
    raise RuntimeError(  {mark}
        "internal error"
    )
""".format(mark=_MARK)

# The line of `_EXEMPT` in the `else` of the marked `if`.
_ELSE_LINE = 5

# A sample module with a signature over lines that hold only annotations.
_ANNOTATED = """\
def scale(
    value: int,
    factor: int,
) -> int:
    return value * factor
"""


# Returns a parser with the options and no abbreviations, as runners make.
def parser_make() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    category.options_add(parser)
    return parser


# The object of a file under the checkout's top, read with `json`.
def file_load(name: str) -> dict[str, Any]:
    with open(os.path.join(_ROOT_PATH, name), encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data


# Every suite's gold file read with `json`, `{language: {suite: gold}}`.
def gold_load() -> dict[str, Any]:
    gold: dict[str, Any] = {}
    for language, directory in _LANGUAGE_DIRECTORIES.items():
        suites: dict[str, Any] = {}
        for name in sorted(os.listdir(os.path.join(_ROOT_PATH, directory))):
            if name.startswith(_GOLD_PREFIX) and name.endswith(_GOLD_SUFFIX):
                suite = name[len(_GOLD_PREFIX) : -len(_GOLD_SUFFIX)]
                suites[suite] = file_load(os.path.join(directory, name))
        gold[language] = suites
    return gold


# The keys of the object whose values are objects in turn.
def keys_nested(data: dict[str, Any]) -> list[str]:
    return [key for key, value in data.items() if isinstance(value, dict)]


# Calls each function of a run `_SHAPES`, both branches of `parity`.
def shapes_call(shapes: dict[str, Any]) -> None:
    shapes["Square"]().area(2)
    shapes["parity"](1)
    shapes["parity"](2)


# The values by id, the refusals, the one read, and the copies.
class TestHarness(unittest.TestCase):
    # Reads the settings and every gold file with `json`, the oracle.
    def setUp(self) -> None:
        self.settings = file_load(_SETTINGS_NAME)
        self.gold = gold_load()

    # A top level id names its value: a setting, a language's whole gold.
    def test_top_id(self) -> None:
        for key, value in self.settings.items():
            self.assertEqual(harness.setting_get(key), value, key)
        for key, value in self.gold.items():
            self.assertEqual(harness.gold_get(key), value, key)

    # A language and a suite name that suite's whole gold file.
    def test_suite_id(self) -> None:
        for language, suites in self.gold.items():
            for suite, value in suites.items():
                id = f"{language}.{suite}"
                self.assertEqual(harness.gold_get(id), value, id)

    # A nested id names the value of its keys joined by `.`.
    def test_nested_id(self) -> None:
        for key in keys_nested(self.settings):
            inner = cast(dict[str, Any], self.settings[key])
            for name, value in inner.items():
                id = f"{key}.{name}"
                self.assertEqual(harness.setting_get(id), value, id)
        self.assertEqual(harness.gold_get(f"{_GOLD_ID}.limits"), _LIMITS)

    # An id one of whose keys is missing raises, naming the file and the id.
    def test_id_unknown(self) -> None:
        id = f"{_GOLD_ID}.no_such"
        with self.assertRaises(KeyError) as caught:
            harness.setting_get(id)
        expected = (
            "settings.json has no value with id 'python.test_test.no_such'"
        )
        self.assertEqual(caught.exception.args, (expected,))
        with self.assertRaises(KeyError) as caught:
            harness.gold_get(id)
        expected = (
            f"{_GOLD_FILE} has no value with id 'python.test_test.no_such'"
        )
        self.assertEqual(caught.exception.args, (expected,))

    # An id of a suite with no gold file raises, naming the file it sought.
    def test_suite_unknown(self) -> None:
        with self.assertRaises(KeyError) as caught:
            harness.gold_get("python.no_such.limits")
        expected = (
            "python/test_setting_no_such.json has no value with id"
            " 'python.no_such.limits'"
        )
        self.assertEqual(caught.exception.args, (expected,))

    # An id of no language raises, naming the gold.
    def test_language_unknown(self) -> None:
        with self.assertRaises(KeyError) as caught:
            harness.gold_get("no_such.test_test")
        expected = "the gold has no value with id 'no_such.test_test'"
        self.assertEqual(caught.exception.args, (expected,))

    # An id that goes on past a value that is not an object raises.
    def test_id_past_value(self) -> None:
        nested = keys_nested(self.settings)
        flat = [key for key in self.settings if key not in nested]
        id = f"{flat[0]}.on"
        with self.assertRaises(KeyError) as caught:
            harness.setting_get(id)
        expected = f"settings.json has no value with id {id!r}"
        self.assertEqual(caught.exception.args, (expected,))
        with self.assertRaises(KeyError) as caught:
            harness.gold_get(f"{_GOLD_ID}.limits.0")
        expected = (
            f"{_GOLD_FILE} has no value with id 'python.test_test.limits.0'"
        )
        self.assertEqual(caught.exception.args, (expected,))

    # Files are read once: two gets of an id are the object of the first read.
    def test_read_once(self) -> None:
        for key in keys_nested(self.settings):
            self.assertIs(harness.setting_get(key), harness.setting_get(key))
        self.assertIs(harness.gold_get(_GOLD_ID), harness.gold_get(_GOLD_ID))

    # A copy holds the whole file, and changing it changes no later read.
    def test_copies_whole(self) -> None:
        settings = harness.settings_copy()
        gold = harness.gold_copy()
        self.assertEqual(settings, self.settings)
        self.assertEqual(gold, self.gold)
        nested = keys_nested(settings)
        for key in nested:
            settings[key].clear()
        gold["python"]["test_test"]["limits"].append(3)
        for key in nested:
            expected = self.settings[key]
            self.assertEqual(harness.setting_get(key), expected, key)
        self.assertEqual(harness.gold_get(f"{_GOLD_ID}.limits"), _LIMITS)
        self.assertEqual(harness.settings_copy(), self.settings)
        self.assertEqual(harness.gold_copy(), self.gold)


# The options of a category, `smoke-test` when none is given.
class TestOptions(unittest.TestCase):
    # No option gives `smoke-test`.
    def test_default_smoke(self) -> None:
        parsed = parser_make().parse_args([])
        self.assertEqual(parsed.category, _SMOKE_TEST)

    # The option `--test-all` gives `test-all`.
    def test_normal_given(self) -> None:
        parsed = parser_make().parse_args(["--test-all"])
        self.assertEqual(parsed.category, _TEST_ALL)

    # The option `--test-disabled` gives `test-disabled`.
    def test_disabled_given(self) -> None:
        parsed = parser_make().parse_args(["--test-disabled"])
        self.assertEqual(parsed.category, _TEST_DISABLED)

    # Two options give the higher in either order, so that none contradicts.
    def test_options_raised(self) -> None:
        for words in (
            ["--test-all", "--test-disabled"],
            ["--test-disabled", "--test-all"],
        ):
            parsed = parser_make().parse_args(words)
            self.assertEqual(parsed.category, _TEST_DISABLED, words)

    # The default's name is no option: `--smoke-test` exits with the code 2.
    def test_smoke_refused(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                parser_make().parse_args(["--smoke-test"])
        self.assertEqual(caught.exception.code, 2)

    # An option of neither name, though the start of one, exits with code 2.
    def test_other_refused(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                parser_make().parse_args(["--normal"])
        self.assertEqual(caught.exception.code, 2)


# The words of a category's option for a command line.
class TestOptionWords(unittest.TestCase):
    # A `smoke-test` run has no option word.
    def test_smoke_none(self) -> None:
        self.assertEqual(category.option_words(_SMOKE_TEST), [])

    # A `test-all` run has its one option.
    def test_normal_option(self) -> None:
        self.assertEqual(category.option_words(_TEST_ALL), ["--test-all"])

    # A `test-disabled` run has its one option.
    def test_disabled_option(self) -> None:
        words = category.option_words(_TEST_DISABLED)
        self.assertEqual(words, ["--test-disabled"])

    # The words parse back to their category.
    def test_words_parsed(self) -> None:
        for chosen in (_SMOKE_TEST, _TEST_ALL, _TEST_DISABLED):
            words = category.option_words(chosen)
            parsed = parser_make().parse_args(words)
            self.assertEqual(parsed.category, chosen, chosen)

    # A category other than the three raises.
    def test_category_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            category.option_words("all")
        self.assertEqual(caught.exception.args, (_ALL_REFUSED,))


# Which suites a run of each category runs, and the strings it refuses.
class TestSelection(unittest.TestCase):
    # A `smoke-test` suite runs in a run of any category.
    def test_smoke_runs(self) -> None:
        for chosen in (_SMOKE_TEST, _TEST_ALL, _TEST_DISABLED):
            self.assertTrue(category.suite_runs(_SMOKE_TEST, chosen), chosen)

    # A `test-all` suite runs in a run of the two higher categories.
    def test_normal_runs(self) -> None:
        self.assertTrue(category.suite_runs(_TEST_ALL, _TEST_ALL))
        self.assertTrue(category.suite_runs(_TEST_ALL, _TEST_DISABLED))
        self.assertFalse(category.suite_runs(_TEST_ALL, _SMOKE_TEST))

    # The category `test-disabled` is no label.
    def test_disabled_label(self) -> None:
        with self.assertRaises(ValueError) as caught:
            category.suite_runs(_TEST_DISABLED, _TEST_DISABLED)
        expected = (
            "the label 'test-disabled' is neither smoke-test nor test-all"
        )
        self.assertEqual(caught.exception.args, (expected,))

    # A label other than the two raises.
    def test_label_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            category.suite_runs("smoke", _SMOKE_TEST)
        expected = "the label 'smoke' is neither smoke-test nor test-all"
        self.assertEqual(caught.exception.args, (expected,))

    # A category other than the three raises.
    def test_category_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            category.suite_runs(_SMOKE_TEST, "all")
        self.assertEqual(caught.exception.args, (_ALL_REFUSED,))


# What is disabled: which category takes it, and the setting of a run.
class TestDisabled(unittest.TestCase):
    # `test-disabled` alone takes what is disabled.
    def test_runs_chosen(self) -> None:
        self.assertTrue(category.disabled_runs(_TEST_DISABLED))
        self.assertFalse(category.disabled_runs(_TEST_ALL))
        self.assertFalse(category.disabled_runs(_SMOKE_TEST))

    # A category other than the three raises.
    def test_category_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            category.disabled_runs("all")
        self.assertEqual(caught.exception.args, (_ALL_REFUSED,))

    # A run's setting holds until the next, which turns it off again.
    def test_setting_kept(self) -> None:
        held = category.disabled_taken()
        self.addCleanup(
            category.disabled_set, _TEST_DISABLED if held else _SMOKE_TEST
        )
        category.disabled_set(_TEST_DISABLED)
        self.assertTrue(category.disabled_taken())
        category.disabled_set(_TEST_ALL)
        self.assertFalse(category.disabled_taken())


# The seconds a run of each category may take.
class TestLimit(unittest.TestCase):
    # A `smoke-test` run has the gold's `smoke_seconds`, as a float.
    def test_smoke_limit(self) -> None:
        limit = category.limit_seconds(_SMOKE_TEST)
        expected = float(file_load(_DRIVER_FILE)["smoke_seconds"])
        self.assertEqual(limit, expected)
        self.assertIs(type(limit), float)

    # A `test-all` or `test-disabled` run has no limit of its own.
    def test_normal_unlimited(self) -> None:
        self.assertIsNone(category.limit_seconds(_TEST_ALL))
        self.assertIsNone(category.limit_seconds(_TEST_DISABLED))

    # A category other than the three raises.
    def test_category_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            category.limit_seconds("all")
        self.assertEqual(caught.exception.args, (_ALL_REFUSED,))


# The alarm of a suite: its own seconds or the run's deadline, the sooner.
class TestAlarm(unittest.TestCase):
    # No seconds of its own and no run limit arm no alarm.
    def test_no_alarm(self) -> None:
        plan = category.alarm_plan("test_wire.py", None, None, 5.0)
        self.assertIsNone(plan)

    # With no run limit, a module's own seconds arm its alarm.
    def test_own_alarm(self) -> None:
        plan = category.alarm_plan("module m", 120.0, None, 500.0)
        self.assertEqual(plan, (120.0, "module m ran longer than 120 s"))

    # A deadline sooner than the module's own seconds arms the alarm.
    def test_deadline_sooner(self) -> None:
        plan = category.alarm_plan("module m", 120.0, 120.0, 100.0)
        expected = (20.0, "the smoke-test run passed its 120 s in module m")
        self.assertEqual(plan, expected)

    # Own seconds sooner than the deadline arm the alarm.
    def test_own_sooner(self) -> None:
        plan = category.alarm_plan("module m", 30.0, 120.0, 0.0)
        self.assertEqual(plan, (30.0, "module m ran longer than 30 s"))

    # A tie between the two goes to the module's own alarm.
    def test_tie_own(self) -> None:
        plan = category.alarm_plan("module m", 20.0, 120.0, 100.0)
        self.assertEqual(plan, (20.0, "module m ran longer than 20 s"))

    # A part with no alarm of its own gets the seconds left in the run.
    def test_part_deadline(self) -> None:
        plan = category.alarm_plan("test_browser.py", None, 120.0, 90.5)
        expected = (
            29.5,
            "the smoke-test run passed its 120 s in test_browser.py",
        )
        self.assertEqual(plan, expected)

    # A deadline already passed before the suite starts raises at once.
    def test_deadline_passed(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            category.alarm_plan("test_wire.py", None, 120.0, 120.0)
        expected = "the smoke-test run used its 120 s before test_wire.py"
        self.assertEqual(caught.exception.args, (expected,))


# The labels of the roots and rungs, checked as a runner reaches them.
class TestLabelBook(unittest.TestCase):
    # A `smoke-test` run leaves a `test-all` root out.
    def test_root_skipped(self) -> None:
        book = category.LabelBook(_SMOKE_TEST)
        self.assertFalse(book.root_enter("r", _TEST_ALL))

    # A `smoke-test` run of a `smoke-test` root runs its `smoke-test` rungs.
    def test_rungs_chosen(self) -> None:
        book = category.LabelBook(_SMOKE_TEST)
        self.assertTrue(book.root_enter("r", _SMOKE_TEST))
        self.assertTrue(book.rung_enter("a", _SMOKE_TEST))
        self.assertFalse(book.rung_enter("b", _TEST_ALL))
        book.root_leave()

    # A `test-all` run runs a `test-all` root and its rungs.
    def test_normal_all(self) -> None:
        book = category.LabelBook(_TEST_ALL)
        self.assertTrue(book.root_enter("r", _TEST_ALL))
        self.assertTrue(book.rung_enter("b", _TEST_ALL))
        book.root_leave()

    # A `smoke-test` rung in a `test-all` root raises.
    def test_smoke_hidden(self) -> None:
        book = category.LabelBook(_TEST_ALL)
        self.assertTrue(book.root_enter("r", _TEST_ALL))
        with self.assertRaises(RuntimeError) as caught:
            book.rung_enter("x", _SMOKE_TEST)
        expected = (
            "the rung 'x' is labelled smoke-test in the root 'r', labelled"
            " test-all, which a smoke-test run never starts"
        )
        self.assertEqual(caught.exception.args, (expected,))

    # A `smoke-test` root left with no `smoke-test` rung raises in either run.
    def test_root_empty(self) -> None:
        expected = (
            "the root 'r' is labelled smoke-test and holds no rung labelled"
            " smoke-test"
        )
        for chosen in (_SMOKE_TEST, _TEST_ALL):
            book = category.LabelBook(chosen)
            self.assertTrue(book.root_enter("r", _SMOKE_TEST), chosen)
            book.rung_enter("b", _TEST_ALL)
            with self.assertRaises(RuntimeError) as caught:
                book.root_leave()
            self.assertEqual(caught.exception.args, (expected,), chosen)

    # A rung outside any root runs as its label says and raises nothing.
    def test_outside_root(self) -> None:
        smoke = category.LabelBook(_SMOKE_TEST)
        self.assertFalse(smoke.rung_enter("s", _TEST_ALL))
        normal = category.LabelBook(_TEST_ALL)
        self.assertTrue(normal.rung_enter("s", _TEST_ALL))

    # A root entered while another root runs raises.
    def test_root_nested(self) -> None:
        book = category.LabelBook(_TEST_ALL)
        self.assertTrue(book.root_enter("r", _TEST_ALL))
        with self.assertRaises(RuntimeError) as caught:
            book.root_enter("q", _TEST_ALL)
        expected = "the root 'q' is entered inside the root 'r'"
        self.assertEqual(caught.exception.args, (expected,))

    # Leaving when no root runs, as after a root left out, raises.
    def test_leave_outside(self) -> None:
        book = category.LabelBook(_SMOKE_TEST)
        self.assertFalse(book.root_enter("r", _TEST_ALL))
        with self.assertRaises(RuntimeError) as caught:
            book.root_leave()
        expected = "no root that runs is left to leave"
        self.assertEqual(caught.exception.args, (expected,))


# The lines a count finds never run, in sample modules really run.
class TestLineCount(unittest.TestCase):
    # Makes the scratch directory of the samples in `build/`.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name

    # Writes a sample module in the scratch directory and returns its path.
    def sample_write(self, name: str, text: str) -> str:
        path = os.path.join(self.scratch, name)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path

    # Starts a count that stops when the test ends.
    def count_start(self) -> line_coverage.LineCount:
        count = line_coverage.LineCount()
        self.addCleanup(count.count_stop)
        return count

    # Checks that the count's check of the file raises naming the line.
    def unrun_check(
        self, count: line_coverage.LineCount, path: str, line: int
    ) -> None:
        with self.assertRaises(RuntimeError) as caught:
            count.lines_check(path)
        expected = f"line {line} of {path} was never counted as run"
        self.assertEqual(caught.exception.args, (expected,))

    # Calls each `_SHAPES` function in a forked child, always ended by SIGKILL.
    def child_call(self, shapes: dict[str, Any]) -> None:
        pid = os.fork()
        if pid == 0:
            try:
                shapes_call(shapes)
            finally:
                os.kill(os.getpid(), signal.SIGKILL)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)

    # Lines run at import count outside a suite, lines of functions in one.
    def test_all_counted(self) -> None:
        path = self.sample_write("shapes.py", _SHAPES)
        count = self.count_start()
        shapes = runpy.run_path(path)
        count.suite_enter([path])
        shapes_call(shapes)
        count.suite_leave()
        count.lines_check(path)

    # A branch never taken holds the first line never run.
    def test_branch_unrun(self) -> None:
        path = self.sample_write("shapes.py", _SHAPES)
        count = self.count_start()
        shapes = runpy.run_path(path)
        count.suite_enter([path])
        shapes["Square"]().area(2)
        shapes["parity"](1)
        count.suite_leave()
        self.unrun_check(count, path, _EVEN_LINE)

    # Function lines count only in a suite, though a run outside disabled them.
    def test_suite_only(self) -> None:
        path = self.sample_write("shapes.py", _SHAPES)
        count = self.count_start()
        shapes = runpy.run_path(path)
        shapes_call(shapes)
        self.unrun_check(count, path, _AREA_LINE)
        count.suite_enter([path])
        shapes_call(shapes)
        count.suite_leave()
        count.lines_check(path)

    # A file never run has its first line never run.
    def test_file_unrun(self) -> None:
        path = self.sample_write("shapes.py", _SHAPES)
        count = self.count_start()
        self.unrun_check(count, path, 1)

    # A suite counts the function lines of its own files only.
    def test_other_file(self) -> None:
        first = self.sample_write("first.py", _SHAPES)
        second = self.sample_write("second.py", _SHAPES)
        count = self.count_start()
        samples = [runpy.run_path(first), runpy.run_path(second)]
        count.suite_enter([first])
        for shapes in samples:
            shapes_call(shapes)
        count.suite_leave()
        count.lines_check(first)
        self.unrun_check(count, second, _AREA_LINE)

    # The marked `if` and `raise` are exempt with their blocks, the `else` not.
    def test_exempt(self) -> None:
        path = self.sample_write("exempt.py", _EXEMPT)
        count = self.count_start()
        exempt = runpy.run_path(path)
        self.unrun_check(count, path, _ELSE_LINE)
        count.suite_enter([path])
        exempt["sign"](1)
        count.suite_leave()
        count.lines_check(path)

    # The lines of a signature that hold only annotations do not count.
    def test_annotations(self) -> None:
        path = self.sample_write("annotated.py", _ANNOTATED)
        count = self.count_start()
        annotated = runpy.run_path(path)
        count.suite_enter([path])
        self.assertEqual(annotated["scale"](2, 3), 6)
        count.suite_leave()
        count.lines_check(path)

    # A file run and named through a symbolic link counts as its real path.
    def test_real_path(self) -> None:
        path = self.sample_write("shapes.py", _SHAPES)
        link = os.path.join(self.scratch, "link.py")
        os.symlink(path, link)
        count = self.count_start()
        shapes = runpy.run_path(link)
        count.suite_enter([link])
        shapes_call(shapes)
        count.suite_leave()
        count.lines_check(path)

    # A count stopped counts nothing more, and keeps what it counted.
    def test_stopped(self) -> None:
        first = self.sample_write("first.py", _SHAPES)
        second = self.sample_write("second.py", _SHAPES)
        count = line_coverage.LineCount()
        runpy.run_path(first)
        count.count_stop()
        runpy.run_path(second)
        self.unrun_check(count, first, _AREA_LINE)
        self.unrun_check(count, second, 1)

    # Two counts at once count apart, each only in its own suites.
    def test_two_counts(self) -> None:
        path = self.sample_write("shapes.py", _SHAPES)
        first = self.count_start()
        second = self.count_start()
        shapes = runpy.run_path(path)
        first.suite_enter([path])
        shapes_call(shapes)
        first.suite_leave()
        first.lines_check(path)
        self.unrun_check(second, path, _AREA_LINE)

    # Function lines a fork runs count in suites only, though SIGKILL ends it.
    def test_forked_child(self) -> None:
        path = self.sample_write("shapes.py", _SHAPES)
        count = self.count_start()
        shapes = runpy.run_path(path)
        self.child_call(shapes)
        self.unrun_check(count, path, _AREA_LINE)
        count.suite_enter([path])
        self.child_call(shapes)
        count.suite_leave()
        count.lines_check(path)
