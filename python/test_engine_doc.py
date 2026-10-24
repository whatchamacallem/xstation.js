# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handler of `doc.put` on a store double: the type, version and
# handler the registration records, the handler called as the dispatcher
# calls it on lines of the gold, their bodies' header keys integers as the
# decoder reads them, the store's `doc_put` it makes with the line's
# database, id and body, a line in full names, and a line with `i` the
# handler leaves unanswered. Versions, heads and the bodies and targets the
# store refuses are the store's own, `test_substrate.py`'s.

import engine_doc, harness, re, unittest, unittest.mock
from collections.abc import Callable
from typing import Any

# The dotted name of the store that the tests patch.
_STORE_TARGET = "engine_doc._STATE.store"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_doc"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The ref the store double answers for a put, the scene's first version.
_SCENE_REF = "/castle_gatehouse/scene/arrival/1"


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

    # `Store.doc_put`, as `engine_doc` calls it.
    def doc_put(self, db: str, id: str, body: dict[int | str, Any]) -> Any:
        return self.call_answer("doc_put", db, id, body)


# Gives each test an empty state, a registration recorder, a store double.
class IsolatedCase(unittest.TestCase):
    # Patches the state and `dispatch.handler_register` through `engine_doc`.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        state = unittest.mock.patch(_STORE_TARGET, None)
        register = unittest.mock.patch.object(
            engine_doc.dispatch, "handler_register", self.handler_record
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
        engine_doc.handlers_register(store)
        (fn,) = [fn for kind, _, fn in self.handlers if kind == name]
        return fn

    # Calls the handler on a line of the gold, checks the one `doc_put`.
    def put_check(self, name: str) -> None:
        put = self.handler_get("doc.put")
        line = _gold_value(f"lines.{name}")
        self.store.answers["doc_put"] = [_SCENE_REF]
        self.assertIsNone(_handler_call(put, line))
        expected = [("doc_put", line["db"], line["id"], line["body"])]
        self.assertEqual(self.store.calls, expected)

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `doc.put`.
class TestPut(IsolatedCase):
    # The scene goes to the store with its database, id and body.
    def test_document_put(self) -> None:
        self.put_check("put")

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.put_check("put_full")

    # A put with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.put_check("put_request")


# Tests the registration.
class TestRegister(IsolatedCase):
    # The handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        store: Any = self.store
        engine_doc.handlers_register(store)
        expected = [("doc.put", 0, engine_doc.doc_put)]
        self.assertEqual(self.handlers, expected)

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.put")
        message = _text_get("engine_doc_not_registered")
        self.raise_check(
            RuntimeError,
            message,
            lambda: _handler_call(engine_doc.doc_put, line),
        )
        self.assertEqual(self.store.calls, [])
