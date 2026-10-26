# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handlers of `verbose.put` and `verbose.tail` on a double of the
# calls they make on `verbose`, patched through `engine_verbose.verbose`:
# the registration's types, versions and handlers, each handler called as
# the dispatcher calls it on lines of the gold, the page lines a put hands
# to `lines_put` under their thread, the tail of the server from
# `history_get` and of a page thread from `tail_get` replied with the count
# given, the gate of debug mode on `verbose.put` alone, and the lines a put
# refuses. Writing, reading and refusing are `test_verbose.py`'s.

import engine_verbose, harness, re, unittest, unittest.mock
from collections.abc import Callable
from typing import Any, NamedTuple

# The dotted name of the debug setting that the tests patch.
_DEBUG_TARGET = "engine_verbose._STATE.debug"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_verbose"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The calls of `verbose` that `engine_verbose` makes, which the double takes.
_VERBOSE_CALLS = ("lines_put", "history_get", "tail_get")


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


# The `verbose.LogLine` shape the double answers, as a test's own tuple.
class LogEntry(NamedTuple):
    at: int
    text: str


# The entries of the `lines` of a line or a reply, as `LogEntry` tuples.
def _entries_of(line: dict[int | str, Any]) -> list[LogEntry]:
    return [LogEntry(entry["at"], entry["text"]) for entry in line["lines"]]


# A double of `verbose`: records each call, answers what the test queued.
class VerboseDouble:
    # Starts with no call recorded and no answer queued.
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answers: dict[str, list[Any]] = {}

    # Records a call and returns its next queued answer, which must exist.
    def call_answer(self, name: str, *args: Any) -> Any:
        self.calls.append((name, *args))
        if not self.answers.get(name):
            raise AssertionError(f"the verbose double has no answer: {name}")
        return self.answers[name].pop(0)

    # `verbose.lines_put`, as `engine_verbose` calls it.
    def lines_put(self, thread: str, lines: list[Any]) -> Any:
        return self.call_answer("lines_put", thread, lines)

    # `verbose.history_get`, as `engine_verbose` calls it.
    def history_get(self, count: int) -> Any:
        return self.call_answer("history_get", count)

    # `verbose.tail_get`, as `engine_verbose` calls it.
    def tail_get(self, thread: str, count: int) -> Any:
        return self.call_answer("tail_get", thread, count)


# Gives each test an empty state, a registration recorder, a verbose double.
class IsolatedCase(unittest.TestCase):
    # Patches the state, `handler_register` and `verbose` by `engine_verbose`.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        self.verbose = VerboseDouble()
        record = self.handler_record
        patchers: list[Any] = [
            unittest.mock.patch(_DEBUG_TARGET, None),
            unittest.mock.patch.object(
                engine_verbose.dispatch, "handler_register", record
            ),
        ]
        for name in _VERBOSE_CALLS:
            double = getattr(self.verbose, name)
            target = engine_verbose.verbose
            patchers.append(unittest.mock.patch.object(target, name, double))
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    # Records one registration in place of the dispatcher's table.
    def handler_record(
        self, name: str, version: int, fn: Callable[..., Any]
    ) -> None:
        self.handlers.append((name, version, fn))

    # Registers the handlers with the debug setting, returns the one of `name`.
    def handler_get(self, name: str, debug: bool) -> Callable[..., Any]:
        engine_verbose.handlers_register(debug)
        (fn,) = [fn for kind, _, fn in self.handlers if kind == name]
        return fn

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `verbose.put`.
class TestPut(IsolatedCase):
    # Page lines go to `lines_put` under their thread, in order.
    def test_lines_stored(self) -> None:
        put = self.handler_get("verbose.put", True)
        ui = _gold_value("lines.put_ui")
        ai = _gold_value("lines.put_ai")
        self.verbose.answers["lines_put"] = [None, None]
        self.assertIsNone(_handler_call(put, ui))
        self.assertIsNone(_handler_call(put, ai))
        expected = [
            ("lines_put", "ui", _entries_of(ui)),
            ("lines_put", "ai", _entries_of(ai)),
        ]
        self.assertEqual(self.verbose.calls, expected)

    # With debug mode off the handler raises and nothing is written.
    def test_debug_off(self) -> None:
        put = self.handler_get("verbose.put", False)
        line = _gold_value("lines.put_ui")
        message = _text_get("engine_verbose_debug_off")
        self.raise_check(
            RuntimeError, message, lambda: _handler_call(put, line)
        )
        self.assertEqual(self.verbose.calls, [])

    # A bad field raises and the batch that holds the line is not written.
    def test_line_invalid(self) -> None:
        put = self.handler_get("verbose.put", True)
        for case, line in _gold_value("lines.put_invalid").items():
            with self.subTest(case=case):
                message = _text_get(f"engine_verbose_line_invalid_{case}")
                with self.assertRaises(ValueError) as caught:
                    _handler_call(put, line)
                self.assertEqual(str(caught.exception), message)
                self.assertEqual(self.verbose.calls, [])

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.put_ui")
        self.raise_check(
            RuntimeError,
            _text_get("engine_verbose_not_registered"),
            lambda: _handler_call(engine_verbose.verbose_put, line),
        )


# Tests the handler of `verbose.tail`.
class TestTail(IsolatedCase):
    # The server's tail comes from `history_get`, replied with two fields.
    def test_tail_lines(self) -> None:
        tail = self.handler_get("verbose.tail", True)
        line = _gold_value("lines.tail_server")
        reply = _gold_value("lines.tail_server_reply")
        self.verbose.answers["history_get"] = [_entries_of(reply)]
        self.assertEqual(_handler_call(tail, line), reply)
        self.assertEqual(self.verbose.calls, [("history_get", line["count"])])

    # The count goes to `history_get` as given, a large one included.
    def test_tail_counts(self) -> None:
        tail = self.handler_get("verbose.tail", True)
        counts = (0, 1, 3, harness.gold_get(f"{_GOLD_ID}.history_all"))
        self.verbose.answers["history_get"] = [[] for _ in counts]
        for count in counts:
            with self.subTest(count=count):
                line = _gold_value("lines.tail_server")
                line["count"] = count
                reply = _handler_call(tail, line)
                self.assertEqual(reply["lines"], [])
        expected = [("history_get", count) for count in counts]
        self.assertEqual(self.verbose.calls, expected)

    # A page thread's tail comes from `tail_get` with its thread and count.
    def test_page_threads(self) -> None:
        tail = self.handler_get("verbose.tail", True)
        for thread in ("ui", "ai"):
            with self.subTest(thread=thread):
                self.verbose.calls.clear()
                line = _gold_value(f"lines.tail_{thread}")
                reply = _gold_value(f"lines.tail_{thread}_reply")
                self.verbose.answers["tail_get"] = [_entries_of(reply)]
                self.assertEqual(_handler_call(tail, line), reply)
                expected = [("tail_get", thread, line["count"])]
                self.assertEqual(self.verbose.calls, expected)

    # Debug mode does not gate the tail, of the server or of a page thread.
    def test_tail_ungated(self) -> None:
        tail = self.handler_get("verbose.tail", False)
        server = _gold_value("lines.tail_server_reply")
        page = _gold_value("lines.tail_ui_reply")
        self.verbose.answers["history_get"] = [_entries_of(server)]
        self.verbose.answers["tail_get"] = [_entries_of(page)]
        line = _gold_value("lines.tail_server")
        self.assertEqual(_handler_call(tail, line), server)
        line = _gold_value("lines.tail_ui")
        self.assertEqual(_handler_call(tail, line), page)


# Tests the registration.
class TestRegister(IsolatedCase):
    # Each handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        engine_verbose.handlers_register(True)
        expected = [
            ("verbose.put", 0, engine_verbose.verbose_put),
            ("verbose.tail", 0, engine_verbose.verbose_tail),
        ]
        self.assertEqual(self.handlers, expected)
