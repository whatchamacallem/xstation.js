# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handler of the `mcp` line on a server double: the registration's
# type, version and handler, the handler called as the dispatcher calls it
# on lines of the gold, the members of each message handed to the server as
# they came, its response the payload of the reply and nothing replied when
# it gives none, a reply without `r` to a request that came as a push, and
# after an exception a result named `Failure` holding the reply and the
# exception. What the MCP server answers is `test_mcp.py`'s.

import engine_mcp, harness, re, unittest, unittest.mock
from collections.abc import Callable
from typing import Any

# The dotted name of the MCP server that the tests patch.
_SERVER_TARGET = "engine_mcp._STATE.server"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_mcp"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")


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


# The payload of a line: its string keys, in the order they came.
def _payload_of(line: dict[int | str, Any]) -> dict[str, Any]:
    return {key: value for key, value in line.items() if isinstance(key, str)}


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    return fn(line, **_payload_of(line))


# A server double: records each call, answers what the test queued for it.
class ServerDouble:
    # Starts with no call recorded and no answer queued.
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answers: dict[str, list[Any]] = {}

    # Records a call and returns its next queued answer, which must exist.
    def call_answer(self, name: str, *args: Any) -> Any:
        self.calls.append((name, *args))
        if not self.answers.get(name):
            raise AssertionError(f"the server double has no answer: {name}")
        return self.answers[name].pop(0)

    # `Server.message_handle`, as `engine_mcp` calls it.
    def message_handle(self, message: dict[str, Any]) -> Any:
        return self.call_answer("message_handle", message)

    # `Server.failure_take`, as `engine_mcp` calls it.
    def failure_take(self) -> Any:
        return self.call_answer("failure_take")


# Gives each test an empty state, a registration recorder, a server double.
class IsolatedCase(unittest.TestCase):
    # Patches the state and `dispatch.handler_register` through `engine_mcp`.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        state = unittest.mock.patch(_SERVER_TARGET, None)
        register = unittest.mock.patch.object(
            engine_mcp.dispatch, "handler_register", self.handler_record
        )
        for patcher in (state, register):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.server = ServerDouble()

    # Records one registration in place of the dispatcher's table.
    def handler_record(
        self, name: str, version: int, fn: Callable[..., Any]
    ) -> None:
        self.handlers.append((name, version, fn))

    # Registers the handler on the server double and returns it.
    def handler_get(self) -> Callable[..., Any]:
        server: Any = self.server
        engine_mcp.handlers_register(server)
        (fn,) = [fn for kind, _, fn in self.handlers if kind == "mcp"]
        return fn

    # Queues the server's answers to one message: a response and a failure.
    def answers_queue(self, response: Any, failure: Any) -> None:
        self.server.answers.setdefault("message_handle", []).append(response)
        self.server.answers.setdefault("failure_take", []).append(failure)

    # Checks a result is a `Failure` of the reply and the error, by its name.
    def failure_check(
        self, result: Any, reply: dict[int | str, Any], error: BaseException
    ) -> None:
        self.assertEqual(type(result).__name__, "Failure")
        self.assertEqual(result.reply, reply)
        self.assertIs(result.error, error)

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the exchange that opens a session, on the server double.
class TestExchange(IsolatedCase):
    # Opening a session replies to `initialize` and `tools/list` only.
    def test_session_opened(self) -> None:
        handler = self.handler_get()
        names = ("initialize", "initialized", "list")
        lines = [_gold_value(f"lines.{name}") for name in names]
        expected = [
            _gold_value("lines.initialize_reply"),
            None,
            _gold_value("lines.list_reply"),
        ]
        for reply in expected:
            response = None if reply is None else _payload_of(reply)
            self.answers_queue(response, None)
        replies = [_handler_call(handler, line) for line in lines]
        self.assertEqual(replies, expected)
        messages = [call[1] for call in self.server.calls[::2]]
        self.assertEqual(messages, [_payload_of(line) for line in lines])

    # A request pushed with no wire id gets a reply without `r`.
    def test_request_pushed(self) -> None:
        handler = self.handler_get()
        reply = _gold_value("lines.ping_pushed_reply")
        self.answers_queue(_payload_of(reply), None)
        line = _gold_value("lines.ping_pushed")
        self.assertEqual(_handler_call(handler, line), reply)

    # An error response is the reply of a `Failure` holding the exception.
    def test_error_response(self) -> None:
        handler = self.handler_get()
        error = RuntimeError("kept")
        reply = _gold_value("lines.unknown_reply")
        self.answers_queue(_payload_of(reply), error)
        result = _handler_call(handler, _gold_value("lines.unknown"))
        self.failure_check(result, reply, error)

    # A tool's exception is the `isError` reply of a `Failure` holding it.
    def test_tool_raises(self) -> None:
        handler = self.handler_get()
        error = ValueError("boom")
        reply = _gold_value("lines.call_reply")
        self.answers_queue(_payload_of(reply), error)
        result = _handler_call(handler, _gold_value("lines.call"))
        self.failure_check(result, reply, error)


# Tests how the message reaches the server and the response comes back.
class TestPass(IsolatedCase):
    # The server gets the members of the message as they came, in order.
    def test_members_passed(self) -> None:
        handler = self.handler_get()
        for line in _gold_value("lines.passed"):
            with self.subTest(line=line):
                self.server.calls.clear()
                self.answers_queue(None, None)
                self.assertIsNone(_handler_call(handler, line))
                message = _payload_of(line)
                passed = self.server.calls[0][1]
                self.assertEqual(
                    self.server.calls,
                    [("message_handle", message), ("failure_take",)],
                )
                self.assertEqual(list(passed), list(message))

    # The response is the payload of the reply, and the wire id is separate.
    def test_response_replied(self) -> None:
        handler = self.handler_get()
        reply = _gold_value("lines.ping_reply")
        self.answers_queue(_payload_of(reply), None)
        line = _gold_value("lines.ping")
        self.assertEqual(_handler_call(handler, line), reply)

    # No response means nothing to reply.
    def test_response_none(self) -> None:
        handler = self.handler_get()
        self.answers_queue(None, None)
        self.assertIsNone(_handler_call(handler, _gold_value("lines.ping")))

    # A failure kept with no response raises: a `Failure` needs a reply.
    def test_failure_unanswered(self) -> None:
        handler = self.handler_get()
        error = RuntimeError("kept")
        self.answers_queue(None, error)
        line = _gold_value("lines.initialized")
        with self.assertRaises(RuntimeError) as caught:
            _handler_call(handler, line)
        self.assertIs(caught.exception, error)

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.initialized")
        self.raise_check(
            RuntimeError,
            _text_get("engine_mcp_not_registered"),
            lambda: _handler_call(engine_mcp.mcp_message, line),
        )

    # The handler is registered once, under `mcp` at version 0.
    def test_handlers_registered(self) -> None:
        server: Any = self.server
        engine_mcp.handlers_register(server)
        self.assertEqual(self.handlers, [("mcp", 0, engine_mcp.mcp_message)])
