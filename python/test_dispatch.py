# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests registration, dispatch by type and version on lines of the gold, the
# reply rules for requests and notifications, a `Failure`'s reply, the reply
# and error lines it builds, each compared whole with a gold line in its name
# form, the cascades against those built here from the raised exceptions by
# the rule of `cause`, and the ids from 102.

import dispatch, harness, re, traceback, unittest, unittest.mock
from typing import Any

# The dotted name of the handler table that the tests patch.
_HANDLERS_TARGET = "dispatch._HANDLERS"

# The dotted name of the id counters that the tests patch.
_IDS_TARGET = "dispatch._IDS"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_dispatch"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# Ids a request must not carry, each with the case of its gold text.
_IDS_REFUSED = (
    (0, "zero"),
    (-1, "negative"),
    (True, "bool"),
    (1.0, "float"),
    ("1", "text"),
    ([1], "list"),
)

# Versions a line must not carry, each with the case of its gold text.
_VERSIONS_REFUSED = (
    (True, "bool"),
    (1.0, "float"),
    ("1", "text"),
    ([1], "list"),
    (None, "null"),
)


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


# A blob header of `data`, its size and `d` both known only at run time.
def _blob_of(data: bytes) -> dict[int | str, Any]:
    return {"s": len(data), "d": data}


# The stack of one exception alone, as the rule of `cause` writes it.
def _stack_of(error: BaseException) -> str:
    lines = traceback.format_exception(error, chain=False)
    return "".join(lines).removesuffix("\n")


# One entry of a cascade: the exception's own message and stack.
def _entry_of(error: BaseException) -> dict[str, Any]:
    return {"message": str(error), "stack": _stack_of(error)}


# The exception that the attribute `name` of a raised exception holds.
def _link_get(error: BaseException, name: str) -> BaseException:
    link: object = getattr(error, name)
    if not isinstance(link, BaseException):
        raise AssertionError(f"the exception raised has no {name}")
    return link


# A gold error line with the cascade as its payload.
def _error_expected(name: str, cascade: dict[str, Any]) -> Any:
    line = _gold_value(f"lines.{name}")
    line.update(cascade)
    return line


# Makes a handler double that returns `reply`.
def _handler_make(reply: Any = None) -> unittest.mock.Mock:
    return unittest.mock.Mock(return_value=reply)


# Raises a `ValueError` and returns it, so that it carries a traceback.
def _error_raise() -> ValueError:
    try:
        raise ValueError("boom")
    except ValueError as error:
        return error


# Raises "outer" from "middle", raised while "boom" was handled.
def _chain_raise() -> RuntimeError:
    try:
        try:
            try:
                raise ValueError("boom")
            except ValueError:
                raise LookupError("middle")
        except LookupError as middle:
            raise RuntimeError("outer") from middle
    except RuntimeError as error:
        return error


# Raises "outer" from an unraised "other" while "boom" was handled.
def _cause_over_context() -> RuntimeError:
    try:
        try:
            raise ValueError("boom")
        except ValueError:
            raise RuntimeError("outer") from LookupError("other")
    except RuntimeError as error:
        return error


# Raises "outer" with `from None` while "boom" was handled, and returns it.
def _context_suppressed() -> RuntimeError:
    try:
        try:
            raise ValueError("boom")
        except ValueError:
            raise RuntimeError("outer") from None
    except RuntimeError as error:
        return error


# The cascade of `_chain_raise`: outer, middle by `from`, boom by context.
def _chain_cascade(error: BaseException) -> dict[str, Any]:
    middle = _link_get(error, "__cause__")
    first = _link_get(middle, "__context__")
    inner = _entry_of(middle) | {"cause": _entry_of(first)}
    return _entry_of(error) | {"cause": inner}


# Gives each test an empty handler table and empty id counters.
class IsolatedCase(unittest.TestCase):
    # Patches the handler table and the id counters until the test ends.
    def setUp(self) -> None:
        for target in (_HANDLERS_TARGET, _IDS_TARGET):
            patcher = unittest.mock.patch.dict(target, {}, clear=True)
            patcher.start()
            self.addCleanup(patcher.stop)

    # Dispatches a line and checks the type and the text of what it raises.
    def dispatch_check(
        self, kind: type[Exception], message: str, line: Any
    ) -> None:
        with self.assertRaises(kind) as caught:
            dispatch.line_dispatch(line)
        self.assertEqual(str(caught.exception), message)


# Tests the registration of handlers.
class TestRegistration(IsolatedCase):
    # A second registration of a pair raises and the first one stays.
    def test_twice_raises(self) -> None:
        first = _handler_make()
        dispatch.handler_register("kv.get", 0, first)
        with self.assertRaises(ValueError) as context:
            dispatch.handler_register("kv.get", 0, _handler_make())
        self.assertEqual(
            str(context.exception), _text_get("dispatch_handler_twice")
        )
        dispatch.line_dispatch(_gold_value("lines.get"))
        first.assert_called_once()

    # The same type at another version, and another type, register.
    def test_pairs_differ(self) -> None:
        dispatch.handler_register("kv.get", 0, _handler_make())
        dispatch.handler_register("kv.get", 1, _handler_make())
        dispatch.handler_register("kv.put", 0, _handler_make())


# Tests the call of the handler a line names and the reply rules.
class TestDispatch(IsolatedCase):
    # Only the handler of the line's type and version is called.
    def test_handler_called(self) -> None:
        first = _handler_make()
        other_version = _handler_make()
        other_type = _handler_make()
        dispatch.handler_register("kv.put", 0, first)
        dispatch.handler_register("kv.put", 1, other_version)
        dispatch.handler_register("kv.get", 0, other_type)
        line = _gold_value("lines.put_v1")
        self.assertIsNone(dispatch.line_dispatch(line))
        other_version.assert_called_once_with(
            line, n=line["n"], text=line["text"]
        )
        first.assert_not_called()
        other_type.assert_not_called()

    # The handler gets the line and the payload only, blobs stay in the line.
    def test_payload_only(self) -> None:
        handler = _handler_make()
        dispatch.handler_register("kv.put", 0, handler)
        line = _gold_value("lines.put_blob")
        line[1].update(_blob_of(b"abc"))
        dispatch.line_dispatch(line)
        handler.assert_called_once_with(line, n=line["n"])
        self.assertEqual(line[1]["d"], b"abc")

    # A type or a version that nothing registered raises.
    def test_pair_unknown(self) -> None:
        dispatch.handler_register("kv.get", 0, _handler_make())
        self.dispatch_check(
            LookupError,
            _text_get("dispatch_handler_unknown_put"),
            _gold_value("lines.put"),
        )
        self.dispatch_check(
            LookupError,
            _text_get("dispatch_handler_unknown_get"),
            _gold_value("lines.get_v1"),
        )

    # An id that is not an integer of at least 1 raises before any call.
    def test_id_refused(self) -> None:
        handler = _handler_make()
        dispatch.handler_register("kv.get", 0, handler)
        for value, case in _IDS_REFUSED:
            with self.subTest(value=value):
                line = _gold_value("lines.get")
                line[0]["i"] = value
                message = _text_get(f"dispatch_id_refused_{case}")
                self.dispatch_check(ValueError, message, line)
        handler.assert_not_called()

    # A version that is not an integer raises before any call.
    def test_version_refused(self) -> None:
        first = _handler_make()
        second = _handler_make()
        dispatch.handler_register("kv.get", 0, first)
        dispatch.handler_register("kv.get", 1, second)
        for value, case in _VERSIONS_REFUSED:
            with self.subTest(value=value):
                line = _gold_value("lines.get")
                line[0]["v"] = value
                message = _text_get(f"dispatch_version_refused_{case}")
                self.dispatch_check(ValueError, message, line)
        first.assert_not_called()
        second.assert_not_called()

    # An exception from a handler propagates unchanged.
    def test_handler_raises(self) -> None:
        error = KeyError("missing")
        handler = unittest.mock.Mock(side_effect=error)
        dispatch.handler_register("kv.get", 0, handler)
        with self.assertRaises(KeyError) as context:
            dispatch.line_dispatch(_gold_value("lines.get_request"))
        self.assertIs(context.exception, error)

    # A request gets the reply its handler returned, with `r` set to its `i`.
    def test_request_reply(self) -> None:
        request = _gold_value("lines.get_request")
        reply = dispatch.reply_make(request, n=1)
        dispatch.handler_register("kv.get", 0, _handler_make(reply))
        self.assertIs(dispatch.line_dispatch(request), reply)
        self.assertEqual(reply, _gold_value("lines.get_reply"))

    # A reply without `r` gets it, spelled in the name form of its header.
    def test_reply_unset(self) -> None:
        short = _gold_value("lines.get")
        full = _gold_value("lines.put_full")
        dispatch.handler_register("kv.get", 0, _handler_make(short))
        dispatch.handler_register("kv.put", 0, _handler_make(full))
        dispatch.line_dispatch(_gold_value("lines.get_request"))
        dispatch.line_dispatch(_gold_value("lines.put_request"))
        self.assertEqual(short, _gold_value("lines.get_answered"))
        self.assertEqual(full, _gold_value("lines.put_full_answered"))

    # A request whose handler returns nothing raises.
    def test_request_none(self) -> None:
        dispatch.handler_register("kv.get", 0, _handler_make())
        self.dispatch_check(
            ValueError,
            _text_get("dispatch_request_unanswered"),
            _gold_value("lines.get_request"),
        )

    # A notification whose handler returns nothing returns nothing.
    def test_notification_none(self) -> None:
        dispatch.handler_register("verbose.put", 0, _handler_make())
        line = _gold_value("lines.verbose_put_text")
        self.assertIsNone(dispatch.line_dispatch(line))

    # A notification whose handler returns a reply raises.
    def test_notification_reply(self) -> None:
        reply = _gold_value("lines.verbose_put")
        dispatch.handler_register("verbose.put", 0, _handler_make(reply))
        self.dispatch_check(
            ValueError,
            _text_get("dispatch_notification_replied_verbose"),
            _gold_value("lines.verbose_put"),
        )

    # A request's `Failure` is returned, its reply given `r` as a reply is.
    def test_failure_request(self) -> None:
        request = _gold_value("lines.mcp_request")
        error = _error_raise()
        failure = dispatch.Failure(dispatch.reply_make(request), error)
        dispatch.handler_register("mcp", 0, _handler_make(failure))
        self.assertIs(dispatch.line_dispatch(request), failure)
        self.assertEqual(failure.reply, _gold_value("lines.mcp_reply"))
        self.assertIs(failure.error, error)

    # A notification's `Failure` raises, as a reply to a notification does.
    def test_failure_notification(self) -> None:
        reply = _gold_value("lines.mcp")
        failure = dispatch.Failure(reply, _error_raise())
        dispatch.handler_register("mcp", 0, _handler_make(failure))
        self.dispatch_check(
            ValueError,
            _text_get("dispatch_notification_replied_mcp"),
            _gold_value("lines.mcp"),
        )
        self.assertEqual(reply, _gold_value("lines.mcp"))


# Tests the reply line a handler builds.
class TestReply(IsolatedCase):
    # A short name reply has `t` and `r` and nothing else of the request.
    def test_short_names(self) -> None:
        request = _gold_value("lines.keyed")
        reply = dispatch.reply_make(request, found=True, size=3)
        self.assertEqual(reply, _gold_value("lines.keyed_reply"))

    # A full name reply has `type` and `reply` and nothing else of the request.
    def test_full_names(self) -> None:
        request = _gold_value("lines.keyed_full")
        reply = dispatch.reply_make(request, found=True, size=3)
        self.assertEqual(reply, _gold_value("lines.keyed_reply_full"))

    # Blobs are numbered from 1 and counted, and stay apart from the payload.
    def test_blobs_numbered(self) -> None:
        request = _gold_value("lines.echo_request")
        blobs: list[Any] = [_blob_of(b"abc"), _blob_of(b"de")]
        reply = dispatch.reply_make(request, blobs=blobs, n=4)
        expected = _gold_value("lines.echo_reply")
        expected[1].update(_blob_of(b"abc"))
        expected[2].update(_blob_of(b"de"))
        self.assertEqual(reply, expected)


# Tests the cascade of an exception.
class TestCause(IsolatedCase):
    # A chain by `from` and by context nests each cause, the first innermost.
    def test_chain(self) -> None:
        error = _chain_raise()
        self.assertEqual(dispatch.cause_make(error), _chain_cascade(error))

    # `__cause__` is taken before `__context__` when both are set.
    def test_cause_first(self) -> None:
        error = _cause_over_context()
        other = _link_get(error, "__cause__")
        expected = _entry_of(error) | {"cause": _entry_of(other)}
        self.assertEqual(dispatch.cause_make(error), expected)

    # `from None` suppresses the context, so the cascade ends at the raise.
    def test_context_suppressed(self) -> None:
        error = _context_suppressed()
        self.assertEqual(dispatch.cause_make(error), _entry_of(error))


# Tests the error line.
class TestError(IsolatedCase):
    # The error line of a request has `r` and the line's short names.
    def test_request_error(self) -> None:
        request = _gold_value("lines.get_request")
        error = _error_raise()
        error_line = dispatch.error_make(request, error, True)
        expected = _error_expected("error_reply", _entry_of(error))
        self.assertEqual(error_line, expected)

    # The error line of a full name request uses full names.
    def test_full_error(self) -> None:
        request = _gold_value("lines.get_request_full")
        error = _error_raise()
        error_line = dispatch.error_make(request, error, False)
        expected = _error_expected("error_reply_full", _entry_of(error))
        self.assertEqual(error_line, expected)

    # The error line of a notification has no `r`.
    def test_notification_error(self) -> None:
        notification = _gold_value("lines.verbose_put")
        error = _error_raise()
        error_line = dispatch.error_make(notification, error, False)
        expected = _error_expected("error", _entry_of(error))
        self.assertEqual(error_line, expected)

    # The error line of no line has no `r`, in short names when not `full`.
    def test_no_line(self) -> None:
        error = _error_raise()
        error_line = dispatch.error_make(None, error, False)
        expected = _error_expected("error", _entry_of(error))
        self.assertEqual(error_line, expected)

    # The error line of no line uses full names when `full`.
    def test_no_line_full(self) -> None:
        error = _error_raise()
        error_line = dispatch.error_make(None, error, True)
        expected = _error_expected("error_full", _entry_of(error))
        self.assertEqual(error_line, expected)

    # The payload is the cascade, under the full key `cause`.
    def test_cascade_carried(self) -> None:
        error = _chain_raise()
        error_line = dispatch.error_make(None, error, False)
        expected = _error_expected("error", _chain_cascade(error))
        self.assertEqual(error_line, expected)


# Tests the ids of the ports.
class TestIdNext(IsolatedCase):
    # The ids of a port count up from 102, as 101 is the first line's.
    def test_ids_count(self) -> None:
        ids = [dispatch.id_next("wire") for _ in range(3)]
        self.assertEqual(ids, [102, 103, 104])

    # Each port counts on its own.
    def test_ports_separate(self) -> None:
        self.assertEqual(dispatch.id_next("wire"), 102)
        self.assertEqual(dispatch.id_next("ui"), 102)
        self.assertEqual(dispatch.id_next("wire"), 103)
        self.assertEqual(dispatch.id_next("ui"), 103)
