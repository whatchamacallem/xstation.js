# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handler of `sql.run` on a store double: the type, version and
# handler the registration records, the handler called as the dispatcher
# calls it on lines of the gold, the store's `sql_run` it makes with the
# line's database and statements, each a `SqlStatement` of its text and
# parameters, a parameter with quotes and text beyond ASCII bound whole, a
# line in full names, a line with `i` the handler leaves unanswered, and
# malformed statements. Running, rolling back and the databases the store
# refuses are the store's own, `test_substrate.py`'s.

import engine_sql, harness, re, unittest, unittest.mock
from collections.abc import Callable
from typing import Any

# The dotted name of the store that the tests patch.
_STORE_TARGET = "engine_sql._STATE.store"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_sql"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# Text with quotes, a statement separator and characters beyond ASCII.
_QUOTED_TEXT = "it's 'quoted'; DROP TABLE t; --" + chr(0x4E2D) + chr(0x1F600)


# A copy of a value of this module's gold, its number keys made `int`.
def _gold_value(name: str) -> Any:
    return _keys_number(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A copy of a JSON value with each number key an `int`, at every depth.
def _keys_number(value: Any) -> Any:
    if isinstance(value, dict):
        made: dict[int | str, Any] = {}
        for key, item in value.items():
            number = _NUMBER_KEY.fullmatch(key) is not None
            made[int(key) if number else key] = _keys_number(item)
        return made
    if isinstance(value, list):
        return [_keys_number(item) for item in value]
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


# A store double: records each call, answers what the test queued for it.
class StoreDouble:
    # Starts with no call recorded and no answer queued.
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answers: dict[str, list[Any]] = {}

    # Records a call and returns its next queued answer, which must exist.
    def call_answer(self, name: str, *args: Any) -> Any:
        self.calls.append((name, *args))
        if not self.answers.get(name):
            raise AssertionError(f"the store double has no answer: {name}")
        return self.answers[name].pop(0)

    # `Store.sql_run`, as `engine_sql` calls it.
    def sql_run(self, db: str, statements: list[Any]) -> Any:
        return self.call_answer("sql_run", db, statements)


# Gives each test an empty state, a registration recorder, a store double.
class IsolatedCase(unittest.TestCase):
    # Patches the state and `dispatch.handler_register` through `engine_sql`.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        state = unittest.mock.patch(_STORE_TARGET, None)
        register = unittest.mock.patch.object(
            engine_sql.dispatch, "handler_register", self.handler_record
        )
        for patcher in (state, register):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.store = StoreDouble()

    # Records one registration in place of the dispatcher's table.
    def handler_record(
        self, name: str, version: int, fn: Callable[..., Any]
    ) -> None:
        self.handlers.append((name, version, fn))

    # Registers the handlers on the store double, returns the one of `name`.
    def handler_get(self, name: str) -> Callable[..., Any]:
        store: Any = self.store
        engine_sql.handlers_register(store)
        (fn,) = [fn for kind, _, fn in self.handlers if kind == name]
        return fn

    # Calls the handler on a gold line, checks its one `sql_run`, returns it.
    def run_check(self, name: str) -> list[Any]:
        run = self.handler_get("sql.run")
        line = _gold_value(f"lines.{name}")
        statements = line["statements"]
        self.store.answers["sql_run"] = [[([], [], 0)] * len(statements)]
        self.assertIsNone(_handler_call(run, line))
        parsed = [(item["sql"], item["params"]) for item in statements]
        self.assertEqual(self.store.calls, [("sql_run", line["db"], parsed)])
        made: list[Any] = self.store.calls[0][2]
        return made

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)

    # Calls `fn` and checks it raises the type with text matching.
    def raise_match(
        self, kind: type[Exception], pattern: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaisesRegex(kind, pattern):
            fn()


# Tests the handler of `sql.run`.
class TestRun(IsolatedCase):
    # The universe database's statements go to the store in order.
    def test_universe_statements(self) -> None:
        self.run_check("run")

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.run_check("run_full")

    # A run with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.run_check("run_request")

    # Text with quotes and beyond ASCII stays a parameter, whole.
    def test_parameters_bound(self) -> None:
        made = self.run_check("run_quoted")
        self.assertEqual(made[1].params, [_QUOTED_TEXT])


# Tests what the handler of `sql.run` refuses.
class TestRefused(IsolatedCase):
    # A statement with a key missing or a key too many raises.
    def test_statement_malformed(self) -> None:
        run = self.handler_get("sql.run")
        line = _gold_value("lines.run_paramless")
        pattern = "missing 1 required positional argument: 'params'"
        self.raise_match(TypeError, pattern, lambda: _handler_call(run, line))
        extra = _gold_value("lines.run_extra")
        pattern = "unexpected keyword argument 'extra'"
        self.raise_match(TypeError, pattern, lambda: _handler_call(run, extra))
        self.assertEqual(self.store.calls, [])


# Tests the registration.
class TestRegister(IsolatedCase):
    # The handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        store: Any = self.store
        engine_sql.handlers_register(store)
        expected = [("sql.run", 0, engine_sql.sql_run)]
        self.assertEqual(self.handlers, expected)

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.run")
        message = _text_get("engine_sql_not_registered")
        self.raise_check(
            RuntimeError,
            message,
            lambda: _handler_call(engine_sql.sql_run, line),
        )
        self.assertEqual(self.store.calls, [])
