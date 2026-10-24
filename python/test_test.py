# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of the infrastructure for testing. The harness: a value of either
# file by a top or nested id, the refusal of an unknown id, each file read
# once, and the deep copies of both whole files, on files of the test's own
# in place of the checkout's. Category: the options --smoke-test and
# --normal-test on a parser, which suites a run of each category runs, the
# seconds a run may take, the gold's smoke_seconds, the alarm of a suite,
# its own seconds or the deadline of a smoke-test run, whichever comes
# first, own seconds winning a tie, or a refusal once the deadline has
# passed, and the checks LabelBook makes of the labels of the roots and
# rungs a runner reaches, each refusal compared with its message. No real
# alarm is armed, since the runner's alarm of this module is running.

import argparse, category, contextlib, harness, io, json, os, tempfile
import unittest, unittest.mock
from typing import Any

# The label and category of the important suites that fit in 2 minutes.
_SMOKE_TEST = "smoke-test"

# The label and category of every other suite.
_NORMAL_TEST = "normal-test"

# The refusal of the category `all`, which is neither of the two.
_ALL_REFUSED = "the category 'all' is neither smoke-test nor normal-test"

# The dotted names of the harness's paths and state that the tests patch.
_SETTINGS_TARGET = "harness._SETTINGS_PATH"
_TESTS_TARGET = "harness._TESTS_PATH"
_STATE_TARGET = "harness._STATE"

# The settings file of the harness tests, a nested object among its values.
_SETTINGS: dict[str, Any] = {"debug": True, "provider": {"scripted": True}}

# The gold file of the harness tests, `smoke_seconds` read by `category`.
_GOLD: dict[str, Any] = {
    "smoke_seconds": 7,
    "python": {"test_test": {"limits": [1, 2]}},
}


# Returns a parser with the two options and no abbreviations, as runners make.
def parser_make() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    category.options_add(parser)
    return parser


# Writes `value` as the JSON text of the file at `path`.
def json_write(path: str, value: object) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(value, file)


# Gives each test its own two files and a harness that has read neither.
class HarnessCase(unittest.TestCase):
    # Writes the two files and points the harness at them until the test ends.
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.settings_path = os.path.join(folder.name, "settings.json")
        self.tests_path = os.path.join(folder.name, "test_settings.json")
        json_write(self.settings_path, _SETTINGS)
        json_write(self.tests_path, _GOLD)
        patchers = (
            unittest.mock.patch(_SETTINGS_TARGET, self.settings_path),
            unittest.mock.patch(_TESTS_TARGET, self.tests_path),
            unittest.mock.patch.dict(_STATE_TARGET, {}, clear=True),
        )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)


# The values of both files by id, the refusals, the one read and the copies.
class TestHarness(HarnessCase):
    # A top level id names its value in either file.
    def test_top_id(self) -> None:
        self.assertIs(harness.setting_get("debug"), True)
        self.assertEqual(harness.gold_get("smoke_seconds"), 7)

    # A nested id names the value of its keys joined by `.`.
    def test_nested_id(self) -> None:
        self.assertIs(harness.setting_get("provider.scripted"), True)
        self.assertEqual(harness.gold_get("python.test_test.limits"), [1, 2])

    # An id one of whose keys is missing raises, naming the file and the id.
    def test_id_unknown(self) -> None:
        with self.assertRaises(KeyError) as caught:
            harness.setting_get("provider.variable")
        expected = "settings.json has no value with id 'provider.variable'"
        self.assertEqual(caught.exception.args, (expected,))
        with self.assertRaises(KeyError) as caught:
            harness.gold_get("python.test_jslb")
        expected = "test_settings.json has no value with id 'python.test_jslb'"
        self.assertEqual(caught.exception.args, (expected,))

    # An id that goes on past a value that is not an object raises.
    def test_id_past_value(self) -> None:
        with self.assertRaises(KeyError) as caught:
            harness.setting_get("debug.on")
        expected = "settings.json has no value with id 'debug.on'"
        self.assertEqual(caught.exception.args, (expected,))

    # Each file is read once: a change after the first call is not seen.
    def test_read_once(self) -> None:
        self.assertIs(harness.setting_get("debug"), True)
        self.assertEqual(harness.gold_get("smoke_seconds"), 7)
        json_write(self.settings_path, {"debug": False})
        json_write(self.tests_path, {"smoke_seconds": 8})
        self.assertIs(harness.setting_get("debug"), True)
        self.assertEqual(harness.gold_get("smoke_seconds"), 7)

    # A copy holds the whole file, and changing it changes no later read.
    def test_copies_whole(self) -> None:
        settings = harness.settings_copy()
        gold = harness.gold_copy()
        self.assertEqual(settings, _SETTINGS)
        self.assertEqual(gold, _GOLD)
        settings["provider"]["scripted"] = False
        gold["python"]["test_test"]["limits"].append(3)
        self.assertIs(harness.setting_get("provider.scripted"), True)
        self.assertEqual(harness.gold_get("python.test_test.limits"), [1, 2])
        self.assertEqual(harness.settings_copy(), _SETTINGS)
        self.assertEqual(harness.gold_copy(), _GOLD)


# The two options, at most one, and `smoke-test` when neither is given.
class TestOptions(unittest.TestCase):
    # No option gives `smoke-test`.
    def test_default_smoke(self) -> None:
        parsed = parser_make().parse_args([])
        self.assertEqual(parsed.category, _SMOKE_TEST)

    # The option `--smoke-test` gives `smoke-test`.
    def test_smoke_given(self) -> None:
        parsed = parser_make().parse_args(["--smoke-test"])
        self.assertEqual(parsed.category, _SMOKE_TEST)

    # The option `--normal-test` gives `normal-test`.
    def test_normal_given(self) -> None:
        parsed = parser_make().parse_args(["--normal-test"])
        self.assertEqual(parsed.category, _NORMAL_TEST)

    # Both options together exit with the usage code 2.
    def test_both_refused(self) -> None:
        arguments = ["--smoke-test", "--normal-test"]
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                parser_make().parse_args(arguments)
        self.assertEqual(caught.exception.code, 2)

    # An option of neither name, though the start of one, exits with code 2.
    def test_other_refused(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                parser_make().parse_args(["--normal"])
        self.assertEqual(caught.exception.code, 2)


# Which suites a run of each category runs, and the strings it refuses.
class TestSelection(unittest.TestCase):
    # A `smoke-test` suite runs in a run of either category.
    def test_smoke_runs(self) -> None:
        for chosen in (_SMOKE_TEST, _NORMAL_TEST):
            self.assertTrue(category.suite_runs(_SMOKE_TEST, chosen), chosen)

    # A `normal-test` suite runs in a `normal-test` run only.
    def test_normal_runs(self) -> None:
        self.assertTrue(category.suite_runs(_NORMAL_TEST, _NORMAL_TEST))
        self.assertFalse(category.suite_runs(_NORMAL_TEST, _SMOKE_TEST))

    # A label other than the two raises.
    def test_label_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            category.suite_runs("smoke", _SMOKE_TEST)
        expected = "the label 'smoke' is neither smoke-test nor normal-test"
        self.assertEqual(caught.exception.args, (expected,))

    # A category other than the two raises.
    def test_category_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            category.suite_runs(_SMOKE_TEST, "all")
        self.assertEqual(caught.exception.args, (_ALL_REFUSED,))


# The seconds a run of each category may take.
class TestLimit(HarnessCase):
    # A `smoke-test` run has the gold's `smoke_seconds`, as a float.
    def test_smoke_limit(self) -> None:
        limit = category.limit_seconds(_SMOKE_TEST)
        self.assertEqual(limit, 7.0)
        self.assertIs(type(limit), float)

    # A `normal-test` run has no limit of its own.
    def test_normal_unlimited(self) -> None:
        self.assertIsNone(category.limit_seconds(_NORMAL_TEST))

    # A category other than the two raises.
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
    # A `smoke-test` run leaves a `normal-test` root out.
    def test_root_skipped(self) -> None:
        book = category.LabelBook(_SMOKE_TEST)
        self.assertFalse(book.root_enter("r", _NORMAL_TEST))

    # A `smoke-test` run of a `smoke-test` root runs its `smoke-test` rungs.
    def test_rungs_chosen(self) -> None:
        book = category.LabelBook(_SMOKE_TEST)
        self.assertTrue(book.root_enter("r", _SMOKE_TEST))
        self.assertTrue(book.rung_enter("a", _SMOKE_TEST))
        self.assertFalse(book.rung_enter("b", _NORMAL_TEST))
        book.root_leave()

    # A `normal-test` run runs a `normal-test` root and its rungs.
    def test_normal_all(self) -> None:
        book = category.LabelBook(_NORMAL_TEST)
        self.assertTrue(book.root_enter("r", _NORMAL_TEST))
        self.assertTrue(book.rung_enter("b", _NORMAL_TEST))
        book.root_leave()

    # A `smoke-test` rung in a `normal-test` root raises.
    def test_smoke_hidden(self) -> None:
        book = category.LabelBook(_NORMAL_TEST)
        self.assertTrue(book.root_enter("r", _NORMAL_TEST))
        with self.assertRaises(RuntimeError) as caught:
            book.rung_enter("x", _SMOKE_TEST)
        expected = (
            "the rung 'x' is labelled smoke-test in the root 'r', labelled"
            " normal-test, which a smoke-test run never starts"
        )
        self.assertEqual(caught.exception.args, (expected,))

    # A `smoke-test` root left with no `smoke-test` rung raises in either run.
    def test_root_empty(self) -> None:
        expected = (
            "the root 'r' is labelled smoke-test and holds no rung labelled"
            " smoke-test"
        )
        for chosen in (_SMOKE_TEST, _NORMAL_TEST):
            book = category.LabelBook(chosen)
            self.assertTrue(book.root_enter("r", _SMOKE_TEST), chosen)
            book.rung_enter("b", _NORMAL_TEST)
            with self.assertRaises(RuntimeError) as caught:
                book.root_leave()
            self.assertEqual(caught.exception.args, (expected,), chosen)

    # A rung outside any root runs as its label says and raises nothing.
    def test_outside_root(self) -> None:
        smoke = category.LabelBook(_SMOKE_TEST)
        self.assertFalse(smoke.rung_enter("s", _NORMAL_TEST))
        normal = category.LabelBook(_NORMAL_TEST)
        self.assertTrue(normal.rung_enter("s", _NORMAL_TEST))

    # A root entered while another root runs raises.
    def test_root_nested(self) -> None:
        book = category.LabelBook(_NORMAL_TEST)
        self.assertTrue(book.root_enter("r", _NORMAL_TEST))
        with self.assertRaises(RuntimeError) as caught:
            book.root_enter("q", _NORMAL_TEST)
        expected = "the root 'q' is entered inside the root 'r'"
        self.assertEqual(caught.exception.args, (expected,))

    # Leaving when no root runs, as after a root left out, raises.
    def test_leave_outside(self) -> None:
        book = category.LabelBook(_SMOKE_TEST)
        self.assertFalse(book.root_enter("r", _NORMAL_TEST))
        with self.assertRaises(RuntimeError) as caught:
            book.root_leave()
        expected = "no root that runs is left to leave"
        self.assertEqual(caught.exception.args, (expected,))
