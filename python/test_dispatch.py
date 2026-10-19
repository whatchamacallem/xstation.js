# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests registration, dispatch by type and version, the reply rules for
# requests and notifications, and the reply, error and id lines it builds.

import dispatch, jslb, unittest, unittest.mock
from typing import Any

# The dotted name of the handler table that the tests patch.
_HANDLERS_TARGET = "dispatch._HANDLERS"

# The dotted name of the id counters that the tests patch.
_IDS_TARGET = "dispatch._IDS"

# The names a short name reply or error header must not carry.
_SHORT_ABSENT = ("i", "k", "v", "type", "id", "key", "version", "reply")

# The names a full name reply or error header must not carry.
_FULL_ABSENT = ("t", "i", "k", "v", "r", "id", "key", "version")

# The first line of the stack of a raised error.
_STACK_HEAD = "Traceback (most recent call last):"

# The last line of the stack of the error that the tests raise.
_STACK_TAIL = "ValueError: boom"


# Builds a line with no blobs: the type, the header fields and the payload.
def _line_make(
    name: str,
    *,
    version: int = 0,
    request_id: int | None = None,
    key: str | None = None,
    full: bool = False,
    **payload: Any,
) -> jslb.Object:
    header = jslb.header_make(
        name,
        version=version,
        id=request_id,
        key=key,
        full=full,
    )
    return jslb.line_make(header, [], **payload)


# Makes a handler double that returns `reply`.
def _handler_make(reply: jslb.Object | None = None) -> unittest.mock.Mock:
    return unittest.mock.Mock(return_value=reply)


# Raises a `ValueError` and returns it, so that it carries a traceback.
def _error_raise() -> ValueError:
    try:
        raise ValueError("boom")
    except ValueError as error:
        return error


# Gives each test an empty handler table and empty id counters.
class IsolatedCase(unittest.TestCase):
    # Patches the handler table and the id counters until the test ends.
    def setUp(self) -> None:
        for target in (_HANDLERS_TARGET, _IDS_TARGET):
            patcher = unittest.mock.patch.dict(target, {}, clear=True)
            patcher.start()
            self.addCleanup(patcher.stop)


# Tests the registration of handlers.
class TestRegistration(IsolatedCase):
    # A second registration of a pair raises and the first one stays.
    def test_twice_raises(self) -> None:
        first = _handler_make()
        dispatch.handler_register("kv.get", 0, first)
        with self.assertRaises(ValueError):
            dispatch.handler_register("kv.get", 0, _handler_make())
        dispatch.line_dispatch(_line_make("kv.get"))
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
        line = _line_make("kv.put", version=1, text="x", n=2)
        self.assertIsNone(dispatch.line_dispatch(line))
        other_version.assert_called_once_with(line, text="x", n=2)
        first.assert_not_called()
        other_type.assert_not_called()

    # The handler gets the line and the payload only, blobs stay in the line.
    def test_payload_only(self) -> None:
        handler = _handler_make()
        dispatch.handler_register("kv.put", 0, handler)
        header = jslb.header_make("kv.put")
        blob = jslb.blob_make(b"abc")
        line = jslb.line_make(header, [blob], n=1)
        dispatch.line_dispatch(line)
        handler.assert_called_once_with(line, n=1)
        self.assertEqual(line[1]["d"], b"abc")

    # A type or a version that nothing registered raises.
    def test_pair_unknown(self) -> None:
        dispatch.handler_register("kv.get", 0, _handler_make())
        with self.assertRaises(LookupError):
            dispatch.line_dispatch(_line_make("kv.put"))
        with self.assertRaises(LookupError):
            dispatch.line_dispatch(_line_make("kv.get", version=1))

    # An exception from a handler propagates unchanged.
    def test_handler_raises(self) -> None:
        error = KeyError("missing")
        handler = unittest.mock.Mock(side_effect=error)
        dispatch.handler_register("kv.get", 0, handler)
        with self.assertRaises(KeyError) as context:
            dispatch.line_dispatch(_line_make("kv.get", request_id=7))
        self.assertIs(context.exception, error)

    # A request gets the reply its handler returned, with `r` set to its `i`.
    def test_request_reply(self) -> None:
        request = _line_make("kv.get", request_id=7)
        reply = dispatch.reply_make(request, n=1)
        dispatch.handler_register("kv.get", 0, _handler_make(reply))
        self.assertIs(dispatch.line_dispatch(request), reply)
        self.assertEqual(reply[0]["r"], 7)

    # A reply without `r` gets it, spelled in the name form of its header.
    def test_reply_unset(self) -> None:
        short = _line_make("kv.get")
        full = _line_make("kv.put", full=True)
        dispatch.handler_register("kv.get", 0, _handler_make(short))
        dispatch.handler_register("kv.put", 0, _handler_make(full))
        dispatch.line_dispatch(_line_make("kv.get", request_id=7))
        dispatch.line_dispatch(_line_make("kv.put", request_id=8))
        self.assertEqual(short[0]["r"], 7)
        self.assertNotIn("reply", short[0])
        self.assertEqual(full[0]["reply"], 8)
        self.assertNotIn("r", full[0])

    # A request whose handler returns nothing raises.
    def test_request_none(self) -> None:
        dispatch.handler_register("kv.get", 0, _handler_make())
        with self.assertRaises(ValueError):
            dispatch.line_dispatch(_line_make("kv.get", request_id=7))

    # A notification whose handler returns nothing returns nothing.
    def test_notification_none(self) -> None:
        dispatch.handler_register("verbose.put", 0, _handler_make())
        line = _line_make("verbose.put", text="x")
        self.assertIsNone(dispatch.line_dispatch(line))

    # A notification whose handler returns a reply raises.
    def test_notification_reply(self) -> None:
        reply = _line_make("verbose.put")
        dispatch.handler_register("verbose.put", 0, _handler_make(reply))
        with self.assertRaises(ValueError):
            dispatch.line_dispatch(_line_make("verbose.put"))


# Tests the reply line a handler builds.
class TestReply(IsolatedCase):
    # A short name reply has `t` and `r` and nothing else of the request.
    def test_short_names(self) -> None:
        request = _line_make(
            "kv.get", version=1, request_id=7, key="/a/b", n=1
        )
        reply = dispatch.reply_make(request, found=True, size=3)
        self.assertEqual(reply[0]["t"], "kv.get")
        self.assertEqual(reply[0]["r"], 7)
        for name in _SHORT_ABSENT:
            self.assertNotIn(name, reply[0])
        self.assertNotIn(1, reply)
        self.assertEqual(jslb.payload_of(reply), {"found": True, "size": 3})

    # A full name reply has `type` and `reply` and nothing else of the request.
    def test_full_names(self) -> None:
        request = _line_make(
            "kv.get", version=1, request_id=7, key="/a/b", full=True, n=1
        )
        reply = dispatch.reply_make(request, found=True, size=3)
        self.assertEqual(reply[0]["type"], "kv.get")
        self.assertEqual(reply[0]["reply"], 7)
        for name in _FULL_ABSENT:
            self.assertNotIn(name, reply[0])
        self.assertNotIn(1, reply)
        self.assertEqual(jslb.payload_of(reply), {"found": True, "size": 3})

    # Blobs are numbered from 1 and counted, and stay apart from the payload.
    def test_blobs_numbered(self) -> None:
        request = _line_make("db.snapshot", request_id=3)
        first = jslb.blob_make(b"abc")
        second = jslb.blob_make(b"de")
        reply = dispatch.reply_make(request, blobs=[first, second], seq=4)
        self.assertEqual(jslb.field_get(reply[0], "blobs"), 2)
        self.assertEqual(reply[1], first)
        self.assertEqual(reply[2], second)
        self.assertNotIn(3, reply)
        self.assertEqual(jslb.payload_of(reply), {"seq": 4})


# Tests the error line.
class TestError(IsolatedCase):
    # The error line of a request has `r`, the message and the stack.
    def test_request_error(self) -> None:
        request = _line_make("kv.get", request_id=5)
        error_line = dispatch.error_make(request, _error_raise())
        self.assertEqual(error_line[0]["t"], "error")
        self.assertEqual(error_line[0]["r"], 5)
        for name in _SHORT_ABSENT:
            self.assertNotIn(name, error_line[0])
        payload = jslb.payload_of(error_line)
        self.assertEqual(sorted(payload), ["message", "stack"])
        self.assertEqual(payload["message"], "boom")
        self.assertTrue(payload["stack"].startswith(_STACK_HEAD + "\n"))
        self.assertTrue(payload["stack"].endswith(_STACK_TAIL))

    # The error line of a full name request uses full names.
    def test_full_error(self) -> None:
        request = _line_make("kv.get", request_id=5, full=True)
        error_line = dispatch.error_make(request, _error_raise())
        self.assertEqual(error_line[0]["type"], "error")
        self.assertEqual(error_line[0]["reply"], 5)
        for name in _FULL_ABSENT:
            self.assertNotIn(name, error_line[0])

    # The error line of a notification has no `r`.
    def test_notification_error(self) -> None:
        notification = _line_make("verbose.put")
        error_line = dispatch.error_make(notification, _error_raise())
        self.assertEqual(error_line[0]["t"], "error")
        self.assertNotIn("r", error_line[0])
        self.assertNotIn("reply", error_line[0])
        self.assertEqual(jslb.payload_of(error_line)["message"], "boom")

    # The error line of no line has no `r`, in short names.
    def test_no_line(self) -> None:
        error_line = dispatch.error_make(None, _error_raise())
        self.assertEqual(error_line[0]["t"], "error")
        self.assertNotIn("r", error_line[0])
        self.assertNotIn("type", error_line[0])


# Tests the ids of the ports.
class TestIdNext(IsolatedCase):
    # The ids of a port count up from 1.
    def test_ids_count(self) -> None:
        ids = [dispatch.id_next("wire") for _ in range(3)]
        self.assertEqual(ids, [1, 2, 3])

    # Each port counts on its own.
    def test_ports_separate(self) -> None:
        self.assertEqual(dispatch.id_next("wire"), 1)
        self.assertEqual(dispatch.id_next("ui"), 1)
        self.assertEqual(dispatch.id_next("wire"), 2)
        self.assertEqual(dispatch.id_next("ui"), 2)
