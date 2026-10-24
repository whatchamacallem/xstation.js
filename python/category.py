# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The two categories of test suite that the runners share: smoke-test, the
# important suites that fit in 2 minutes in all, and normal-test, the others.
# It holds the options --smoke-test and --normal-test that choose the category
# of a run, smoke-test when neither is given; whether a suite of a label runs
# in a run of a category, a smoke-test suite in both and a normal-test suite
# in a normal-test run only; the seconds a run may take, the gold record's
# smoke_seconds for a smoke-test run; the alarm of a suite, its own seconds
# or the run's deadline, whichever comes first; and LabelBook, which checks
# as a runner reaches them that a root labelled smoke-test holds a rung
# labelled smoke-test and that a root labelled normal-test holds none. A
# label or category other than the two strings raises.

import argparse, harness

# The label of the important suites that fit in 2 minutes, and its category.
_SMOKE_TEST = "smoke-test"

# The label of every other suite, and the category that runs both labels.
_NORMAL_TEST = "normal-test"

# The two labels, which are also the two categories.
_LABELS = (_SMOKE_TEST, _NORMAL_TEST)


# Adds `--smoke-test` or `--normal-test` as `category`, `smoke-test` if none.
def options_add(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f"--{_SMOKE_TEST}",
        action="store_const",
        const=_SMOKE_TEST,
        dest="category",
        help="run the suites labelled smoke-test, the default",
    )
    group.add_argument(
        f"--{_NORMAL_TEST}",
        action="store_const",
        const=_NORMAL_TEST,
        dest="category",
        help="run the suites of both labels",
    )
    parser.set_defaults(category=_SMOKE_TEST)


# Whether a label's suite runs in a category's run. Other strings raise.
def suite_runs(label: str, category: str) -> bool:
    if label not in _LABELS:
        raise ValueError(
            f"the label {label!r} is neither {_SMOKE_TEST} nor {_NORMAL_TEST}"
        )
    _category_check(category)
    return label == _SMOKE_TEST or category == _NORMAL_TEST


# A run's seconds: the gold `smoke_seconds` for `smoke-test`, else None.
def limit_seconds(category: str) -> float | None:
    _category_check(category)
    if category != _SMOKE_TEST:
        return None
    return float(harness.gold_get("smoke_seconds"))


# The alarm of a suite, the sooner of its own seconds and the run's deadline.
def alarm_plan(
    what: str, seconds: float | None, limit: float | None, elapsed: float
) -> tuple[float, str] | None:
    own: tuple[float, str] | None = None
    if seconds is not None:
        own = (seconds, f"{what} ran longer than {seconds:g} s")
    if limit is None:
        return own
    if elapsed >= limit:
        raise RuntimeError(
            f"the {_SMOKE_TEST} run used its {limit:g} s before {what}"
        )
    left = limit - elapsed
    if own is not None and own[0] <= left:
        return own
    return (left, f"the {_SMOKE_TEST} run passed its {limit:g} s in {what}")


# The labels of the roots and rungs a runner reaches, checked as it goes.
class LabelBook:
    # Starts outside any root, for a run of the category.
    def __init__(self, category: str) -> None:
        _category_check(category)
        self._category = category
        self._root: str | None = None
        self._label: str | None = None
        self._reached = False

    # Whether the root runs. A root that runs is left by `root_leave`.
    def root_enter(self, root: str, label: str) -> bool:
        runs = suite_runs(label, self._category)
        if self._root is not None:
            raise RuntimeError(
                f"the root {root!r} is entered inside the root {self._root!r}"
            )
        if runs:
            self._root = root
            self._label = label
            self._reached = False
        return runs

    # Whether it runs, raising for a `smoke-test` rung in a `normal-test` root.
    def rung_enter(self, rung: str, label: str) -> bool:
        runs = suite_runs(label, self._category)
        if label == _SMOKE_TEST:
            if self._label == _NORMAL_TEST:
                raise RuntimeError(
                    f"the rung {rung!r} is labelled {_SMOKE_TEST} in the root"
                    f" {self._root!r}, labelled {_NORMAL_TEST}, which a"
                    f" {_SMOKE_TEST} run never starts"
                )
            self._reached = True
        return runs

    # Raises when a `smoke-test` root reached no `smoke-test` rung.
    def root_leave(self) -> None:
        if self._root is None:
            raise RuntimeError("no root that runs is left to leave")
        if self._label == _SMOKE_TEST and not self._reached:
            raise RuntimeError(
                f"the root {self._root!r} is labelled {_SMOKE_TEST} and holds"
                f" no rung labelled {_SMOKE_TEST}"
            )
        self._root = None
        self._label = None


# Raises unless the category is one of the two.
def _category_check(category: str) -> None:
    if category not in _LABELS:
        raise ValueError(
            f"the category {category!r} is neither {_SMOKE_TEST} nor"
            f" {_NORMAL_TEST}"
        )
