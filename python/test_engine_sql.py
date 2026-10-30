# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handler of `sql.run` on a real store on a scratch root in
# `build/`. Each test runs in a forked child that registers the handler in
# the real dispatcher and kills itself when done, so that no registration
# reaches another test, and the parent checks how the child said it ended.
# The handler is called as the dispatcher calls it on lines of the gold, and
# the rows the line's statements made are queried back from its database: a
# parameter with quotes and text beyond ASCII bound whole, a line in full
# names, a line with `i` the handler leaves unanswered, and malformed
# statements. The dispatcher refuses a second registration of the type at
# version 0. Running, rolling back and the databases the store refuses are
# the store's own, `test_substrate.py`'s.

import dispatch, engine_sql, harness, os, re, signal, substrate, sys, tempfile
import traceback, unittest
from collections.abc import Callable
from typing import Any, cast

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_sql"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The size over which the store keeps a value in a cache file.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# Text with quotes, a statement separator and characters beyond ASCII.
_QUOTED_TEXT = "it's 'quoted'; DROP TABLE t; --" + chr(0x4E2D) + chr(0x1F600)

# The query of the rows the gold's universe statements insert.
_WORLD_QUERY = "SELECT name, title FROM world"

# The query of the row the gold's quoted statements insert.
_QUOTED_QUERY = "SELECT x FROM t"

# How a child ends when its work returned.
_ENDING_PASSED = "passed"


# A copy of a value of this module's gold, its number keys made `int`.
def _gold_value(name: str) -> Any:
    return _keys_number(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A copy of a JSON value with each number key an `int`, at every depth.
def _keys_number(value: Any) -> Any:
    if isinstance(value, dict):
        made: dict[int | str, Any] = {}
        for key, item in cast(dict[str, Any], value).items():
            number = _NUMBER_KEY.fullmatch(key) is not None
            made[int(key) if number else key] = _keys_number(item)
        return made
    if isinstance(value, list):
        return [_keys_number(item) for item in cast(list[Any], value)]
    return value


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    payload = {
        key: value for key, value in line.items() if isinstance(key, str)
    }
    return fn(line, **payload)


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(work: Callable[[], object], path: str) -> None:
    try:
        try:
            work()
            ending = _ENDING_PASSED
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a scratch root in `build/` and a forked child to run in.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the root in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)

    # Runs the work in a forked child and fails with what the child raised.
    def child_run(self, work: Callable[[], object]) -> None:
        path = os.path.join(self.scratch, "ending.txt")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child_end(work, path)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(path)
        if ending != _ENDING_PASSED:
            self.fail(ending)

    # In the child: a store on the root, the handler registered on it.
    def store_register(self) -> substrate.Store:
        store = substrate.Store(self.root, _OVERFLOW_BYTES)
        engine_sql.handlers_register(store)
        return store

    # Calls `fn` and checks it raises the type with text matching.
    def raise_match(
        self, kind: type[Exception], pattern: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaisesRegex(kind, pattern):
            fn()

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `sql.run`.
class TestRun(ScratchCase):
    # In the child: the handler on a gold line, then the row it inserted.
    def run_check(self, name: str, query: str) -> list[list[Any]]:
        line = _gold_value(f"lines.{name}")
        store = self.store_register()
        store.db_create(line["db"])
        self.assertIsNone(_handler_call(engine_sql.sql_run, line))
        select = [substrate.SqlStatement(query, [])]
        (result,) = store.sql_run(line["db"], select)
        self.assertEqual(result.rows, [line["statements"][-1]["params"]])
        return result.rows

    # The universe database's statements run in order: its table, its row.
    def test_universe_statements(self) -> None:
        self.child_run(lambda: self.run_check("run", _WORLD_QUERY))

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.run_check("run_full", _WORLD_QUERY))

    # A run with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.child_run(lambda: self.run_check("run_request", _WORLD_QUERY))

    # In the child: the quoted text comes back from its table whole.
    def quoted_check(self) -> None:
        rows = self.run_check("run_quoted", _QUOTED_QUERY)
        self.assertEqual(rows, [[_QUOTED_TEXT]])

    # Text with quotes and beyond ASCII stays a parameter, whole.
    def test_parameters_bound(self) -> None:
        self.child_run(self.quoted_check)


# Tests what the handler of `sql.run` refuses.
class TestRefused(ScratchCase):
    # In the child: a statement with a key missing or a key too many raises.
    def malformed_check(self) -> None:
        store = self.store_register()
        line = _gold_value("lines.run_paramless")
        store.db_create(line["db"])
        pattern = "missing 1 required positional argument: 'params'"
        self.raise_match(
            TypeError,
            pattern,
            lambda: _handler_call(engine_sql.sql_run, line),
        )
        extra = _gold_value("lines.run_extra")
        pattern = "unexpected keyword argument 'extra'"
        self.raise_match(
            TypeError,
            pattern,
            lambda: _handler_call(engine_sql.sql_run, extra),
        )

    # A statement with a key missing or a key too many raises.
    def test_statement_malformed(self) -> None:
        self.child_run(self.malformed_check)


# Tests the registration.
class TestRegister(ScratchCase):
    # In the child: the dispatcher refuses the type at version 0 again.
    def registered_check(self) -> None:
        self.store_register()
        message = _text_get("dispatch_handler_twice_run")
        self.raise_check(
            ValueError,
            message,
            lambda: dispatch.handler_register(
                "sql.run", 0, engine_sql.sql_run
            ),
        )

    # The handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        self.child_run(self.registered_check)

    # In the child: before the registration the handler raises.
    def early_check(self) -> None:
        line = _gold_value("lines.run")
        message = _text_get("engine_sql_not_registered")
        self.raise_check(
            RuntimeError,
            message,
            lambda: _handler_call(engine_sql.sql_run, line),
        )

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        self.child_run(self.early_check)
