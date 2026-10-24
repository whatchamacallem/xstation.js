# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handler of `turn.append` on a store double: the type, version
# and handler the registration records, the handler called as the
# dispatcher calls it on lines of the gold, the store's `turn_append` it
# makes with the scene, the role and the message as canonical JSON, a
# message with null and a list whole, text beyond ASCII as raw characters, a
# line in full names, and a line with `i` the handler leaves unanswered. The
# numbering of turns and the scenes the store refuses are the store's own,
# `test_substrate.py`'s.

import engine_turn, harness, json, re, unittest, unittest.mock
from collections.abc import Callable
from typing import Any

# The dotted name of the store that the tests patch.
_STORE_TARGET = "engine_turn._STATE.store"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_turn"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# Text beyond ASCII, built from its code points, as the gold's wide turn.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)


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


# The canonical JSON text of a value, as the handler stores a message.
def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


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

    # `Store.turn_append`, as `engine_turn` calls it.
    def turn_append(self, scene: str, role: str, content: str) -> Any:
        return self.call_answer("turn_append", scene, role, content)


# Gives each test an empty state, a registration recorder, a store double.
class IsolatedCase(unittest.TestCase):
    # Patches the state and `dispatch.handler_register` through `engine_turn`.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        state = unittest.mock.patch(_STORE_TARGET, None)
        register = unittest.mock.patch.object(
            engine_turn.dispatch, "handler_register", self.handler_record
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
        engine_turn.handlers_register(store)
        (fn,) = [fn for kind, _, fn in self.handlers if kind == name]
        return fn

    # Calls the handler on a gold line, checks its one `turn_append`.
    def append_check(self, name: str) -> str:
        append = self.handler_get("turn.append")
        line = _gold_value(f"lines.{name}")
        self.store.answers["turn_append"] = [1]
        self.assertIsNone(_handler_call(append, line))
        text = _json_text(line["content"])
        expected = [("turn_append", line["scene"], line["role"], text)]
        self.assertEqual(self.store.calls, expected)
        return text

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `turn.append`.
class TestAppend(IsolatedCase):
    # The player's first message goes to the store as canonical JSON.
    def test_turn_appended(self) -> None:
        self.append_check("append_user")

    # A message with null and a list goes whole, each turn in order.
    def test_messages_whole(self) -> None:
        append = self.handler_get("turn.append")
        names = ("append_user", "append_call", "append_answer")
        lines = [_gold_value(f"lines.{name}") for name in names]
        self.store.answers["turn_append"] = [1, 2, 3]
        for line in lines:
            self.assertIsNone(_handler_call(append, line))
        expected = [
            (
                "turn_append",
                line["scene"],
                line["role"],
                _json_text(line["content"]),
            )
            for line in lines
        ]
        self.assertEqual(self.store.calls, expected)

    # Text beyond ASCII is passed as raw characters, not as escapes.
    def test_text_wide(self) -> None:
        text = self.append_check("append_wide")
        self.assertIn(_WIDE_TEXT, text)

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.append_check("append_full")

    # An append with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.append_check("append_request")


# Tests the registration.
class TestRegister(IsolatedCase):
    # The handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        store: Any = self.store
        engine_turn.handlers_register(store)
        expected = [("turn.append", 0, engine_turn.turn_append)]
        self.assertEqual(self.handlers, expected)

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.append_user")
        message = _text_get("engine_turn_not_registered")
        self.raise_check(
            RuntimeError,
            message,
            lambda: _handler_call(engine_turn.turn_append, line),
        )
        self.assertEqual(self.store.calls, [])
