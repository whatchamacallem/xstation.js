# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the dispatcher joined to the codec of `jslb`: the bytes of each line
# are read by the real decoder, with the limits of the checkout's settings,
# and dispatched by type and version to a handler of the test, which keeps
# the line and the payload it is called with. The reply or the error line
# that `dispatch` builds is written by the real encoder and read back by a
# new decoder, to be compared whole with the line expected, in the name form
# of the line it answers. Each test registers handlers, so it runs in a
# forked child, which writes how it ended on a pipe and kills itself, so the
# handlers it leaves never reach another test. The expected texts are the
# gold's.

import dispatch, functools, harness, jslb, os, signal, sys, traceback, unittest
from collections.abc import Callable
from typing import Any, NoReturn, TypeAlias, cast

# How a child ends when its test passed: any other ending is a traceback.
_ENDING_PASSED = "passed"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_dispatch"

# A request in short names, with a payload.
_GET_REQUEST = b'{"0":{"t":"kv.get","i":7},"ref":"/a/b"}\r'

# The reply to it as the peer reads it.
_GET_REPLY = {0: {"t": "kv.get", "r": 7}, "found": True}

# A request in full names, at version 1.
_PUT_REQUEST = b'{"0":{"type":"kv.put","version":1,"id":8},"n":2}\r'

# The reply to it as the peer reads it.
_PUT_REPLY = {0: {"type": "kv.put", "reply": 8}, "stored": True}

# A request with two blobs, their bytes after its line.
_ECHO_REQUEST = (
    b'{"0":{"t":"echo","i":3,"b":2},"1":{"s":3},"2":{"s":2},"n":4}\rabcde'
)

# The reply to it as the peer reads it, the bytes of each blob sent back.
_ECHO_REPLY = {
    0: {"t": "echo", "r": 3, "b": 2},
    1: {"s": 3, "d": b"abc"},
    2: {"s": 2, "d": b"de"},
    "n": 4,
}

# A notification, which has no id.
_PUT_NOTIFICATION = b'{"0":{"t":"verbose.put"},"text":"x"}\r'

# A request whose id the decoder reads as a float.
_ID_FLOAT = b'{"0":{"t":"kv.get","i":7.0}}\r'

# The calls a handler of the test keeps: each line and its payload.
HandlerCalls: TypeAlias = list[tuple[jslb.Object, dict[str, Any]]]


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# Refuses a blob over the checkout's `overflow_bytes`, which no line here has.
def _sink_refuse(header: jslb.Object) -> NoReturn:
    raise RuntimeError("internal error")


# Reads the lines of the bytes with a new decoder of the checkout's limits.
def _lines_read(data: bytes) -> list[jslb.Object]:
    decoder = jslb.LineDecoder(
        harness.setting_get("line_max"),
        harness.setting_get("blob_max"),
        harness.setting_get("overflow_bytes"),
        _sink_refuse,
    )
    lines = decoder.bytes_feed(data)
    if not decoder.idle():
        raise AssertionError(f"the bytes end inside a line: {data!r}")
    return lines


# Reads the one line of the bytes.
def _line_read(data: bytes) -> jslb.Object:
    (line,) = _lines_read(data)
    return line


# The bytes the encoder writes for a line whose blobs are in memory.
def _line_bytes(line: jslb.Object) -> bytes:
    data = bytearray()
    for piece in jslb.line_encode(line):
        if not isinstance(piece, bytes):
            raise AssertionError(f"the blob of {piece} is not in memory")
        data += piece
    return bytes(data)


# A line as the peer reads it: written by the encoder, then read back.
def _wire_pass(line: jslb.Object) -> jslb.Object:
    return _line_read(_line_bytes(line))


# The reply a dispatch returned, which must be a line.
def _reply_of(result: jslb.Object | dispatch.Failure | None) -> jslb.Object:
    if not isinstance(result, jslb.Object):
        raise AssertionError(f"{result!r} is no reply line")
    return result


# The stack of one exception alone, as the rule of `cause` writes it.
def _stack_of(error: BaseException) -> str:
    lines = traceback.format_exception(error, chain=False)
    return "".join(lines).removesuffix("\n")


# One entry of a cascade: the exception's own message and stack.
def _entry_of(error: BaseException) -> dict[str, Any]:
    return {"message": str(error), "stack": _stack_of(error)}


# Raises "outer" from "boom" and returns both, each with its traceback.
def _chain_raise() -> tuple[RuntimeError, ValueError]:
    try:
        raise ValueError("boom")
    except ValueError as first:
        try:
            raise RuntimeError("outer") from first
        except RuntimeError as error:
            return error, first


# A handler of the test: keeps the line and the payload, and replies with
# the fields given and a blob of the bytes of each blob the line carried.
def _handler_reply(
    calls: HandlerCalls,
    fields: dict[str, Any],
    line: jslb.Object,
    /,
    **payload: Any,
) -> jslb.Object:
    calls.append((line, payload))
    blobs = [
        jslb.blob_make(jslb.field_get(cast(jslb.Object, header), "data"))
        for header in jslb.headers_of(line)[1:]
    ]
    return dispatch.reply_make(line, blobs, **fields)


# A handler of the test: keeps the line and the payload, returns nothing.
def _handler_keep(
    calls: HandlerCalls, line: jslb.Object, /, **payload: Any
) -> None:
    calls.append((line, payload))


# A handler of the test that raises the error given.
def _handler_raise(
    error: BaseException, line: jslb.Object, /, **payload: Any
) -> NoReturn:
    raise error


# In the forked child: runs the check, writes how it ended, kills itself.
def _child_end(check: Callable[[], None], write_fd: int) -> None:
    try:
        try:
            check()
            ending = _ENDING_PASSED
        except BaseException:
            ending = traceback.format_exc()
        try:
            with open(write_fd, "w", encoding="utf-8") as file:
                file.write(ending)
        except BaseException:
            # The parent reads no ending, so the failure and it go to stderr.
            sys.stderr.write(
                f"{traceback.format_exc()}the ending not written: {ending}\n"
            )
            sys.stderr.flush()
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Runs each check that registers a handler in a forked child.
class ChildCase(unittest.TestCase):
    # Runs the check in a forked child, failing with its traceback, if any.
    def child_check(self, check: Callable[[], None]) -> None:
        read_fd, write_fd = os.pipe()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            _child_end(check, write_fd)
        os.close(write_fd)
        with open(read_fd, encoding="utf-8") as file:
            ending = file.read()
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        if ending != _ENDING_PASSED:
            self.fail(ending)


# Makes a test of a `ChildCase` run whole in a forked child, by `child_check`.
def _child_run(test: Callable[[Any], None]) -> Callable[[Any], None]:
    # Runs the test on its case in a forked child.
    @functools.wraps(test)
    def forked_run(case: ChildCase) -> None:
        case.child_check(functools.partial(test, case))

    return forked_run


# Lines off the wire dispatched, and the replies and error lines written.
class TestWire(ChildCase):
    # A request in short names gets its reply in short names, with `r`.
    @_child_run
    def test_request_short(self) -> None:
        calls: HandlerCalls = []
        handler = functools.partial(_handler_reply, calls, {"found": True})
        dispatch.handler_register("kv.get", 0, handler)
        line = _line_read(_GET_REQUEST)
        reply = _reply_of(dispatch.line_dispatch(line))
        self.assertEqual(calls, [(line, {"ref": "/a/b"})])
        self.assertEqual(_wire_pass(reply), _GET_REPLY)

    # A request in full names at a version gets its reply in full names.
    @_child_run
    def test_request_full(self) -> None:
        calls: HandlerCalls = []
        stale: HandlerCalls = []
        handler = functools.partial(_handler_reply, calls, {"stored": True})
        other = functools.partial(_handler_keep, stale)
        dispatch.handler_register("kv.put", 0, other)
        dispatch.handler_register("kv.put", 1, handler)
        line = _line_read(_PUT_REQUEST)
        reply = _reply_of(dispatch.line_dispatch(line))
        self.assertEqual(calls, [(line, {"n": 2})])
        self.assertEqual(stale, [])
        self.assertEqual(_wire_pass(reply), _PUT_REPLY)

    # The blobs the decoder read reach the handler in the line, apart from
    # the payload, and the blobs of its reply follow the reply's line.
    @_child_run
    def test_blobs_echoed(self) -> None:
        calls: HandlerCalls = []
        handler = functools.partial(_handler_reply, calls, {"n": 4})
        dispatch.handler_register("echo", 0, handler)
        line = _line_read(_ECHO_REQUEST)
        reply = _reply_of(dispatch.line_dispatch(line))
        self.assertEqual(calls, [(line, {"n": 4})])
        self.assertEqual(line[1]["d"], b"abc")
        self.assertEqual(line[2]["d"], b"de")
        self.assertEqual(_wire_pass(reply), _ECHO_REPLY)

    # A notification reaches its handler and gets no reply.
    @_child_run
    def test_notification_none(self) -> None:
        calls: HandlerCalls = []
        handler = functools.partial(_handler_keep, calls)
        dispatch.handler_register("verbose.put", 0, handler)
        line = _line_read(_PUT_NOTIFICATION)
        self.assertIsNone(dispatch.line_dispatch(line))
        self.assertEqual(calls, [(line, {"text": "x"})])

    # A handler's raise passes through, and the error line written for it
    # carries the cascade in the name form of the line, with its `r`.
    @_child_run
    def test_error_carried(self) -> None:
        error, first = _chain_raise()
        handler = functools.partial(_handler_raise, error)
        dispatch.handler_register("kv.get", 0, handler)
        line = _line_read(_GET_REQUEST)
        with self.assertRaises(RuntimeError) as caught:
            dispatch.line_dispatch(line)
        self.assertIs(caught.exception, error)
        written = _wire_pass(dispatch.error_make(line, error, True))
        expected = {
            0: {"t": "error", "r": 7},
            **_entry_of(error),
            "cause": _entry_of(first),
        }
        self.assertEqual(written, expected)

    # An id the decoder reads as a float is refused before any call.
    @_child_run
    def test_id_float(self) -> None:
        calls: HandlerCalls = []
        handler = functools.partial(_handler_keep, calls)
        dispatch.handler_register("kv.get", 0, handler)
        line = _line_read(_ID_FLOAT)
        with self.assertRaises(ValueError) as caught:
            dispatch.line_dispatch(line)
        expected = _text_get("dispatch_id_refused_float")
        self.assertEqual(str(caught.exception), expected)
        self.assertEqual(calls, [])
