# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `verbose.put` and `verbose.tail` through the dispatcher: the lines of
# the page threads stored under their thread and kept out of the ring, the
# lines of the server's ring replied with the count and the thread, the gate
# of debug mode on `verbose.put` alone, and the registration. The scratch
# directories go under `build/`.

import contextlib, dispatch, engine_verbose, jslb, os, sqlite3, tempfile
import unittest, unittest.mock, verbose
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The file in the root that holds the lines.
_FILE_NAME = "_verbose.sqlite"

# The lines the ring of a test holds at most.
_RING_LINES = 10

# A count of lines greater than any ring a test makes.
_HISTORY_ALL = 100

# Reads every row of the table, in the order they were written.
_SELECT_ROWS = "SELECT seq, at, thread, level, text FROM line ORDER BY seq"

# The dotted name of the handler table that the tests patch.
_HANDLERS_TARGET = "dispatch._HANDLERS"

# The dotted name of the debug setting that the tests patch.
_DEBUG_TARGET = "engine_verbose._STATE.debug"

# Two lines of a page thread.
_PAGE_LINES: list[dict[str, object]] = [
    {"at": 10, "level": 1, "text": "a"},
    {"at": 20, "level": 2, "text": "b"},
]

# Lines the handler refuses: a field missing, extra, mistyped or out of range.
_LINES_INVALID: list[dict[str, object]] = [
    {"at": 1, "level": 1},
    {"at": 1, "level": 1, "text": "x", "n": 2},
    {"at": "1", "level": 1, "text": "x"},
    {"at": 1.5, "level": 1, "text": "x"},
    {"at": True, "level": 1, "text": "x"},
    {"at": 1, "level": "1", "text": "x"},
    {"at": 1, "level": 1, "text": 5},
    {"at": 1, "level": 3, "text": "x"},
]


# Builds a line with no blobs: the type, an optional id and the payload.
def _line_make(
    name: str, request_id: int | None = None, **payload: Any
) -> jslb.Object:
    header = jslb.header_make(name, id=request_id)
    return jslb.line_make(header, [], **payload)


# Dispatches a line that must be answered and returns the reply.
def _reply_get(line: jslb.Object) -> jslb.Object:
    reply = dispatch.line_dispatch(line)
    if reply is None:
        raise AssertionError("the line was not answered")
    return reply


# Reads every row of the table with a connection of its own.
def _rows_read(path: str) -> list[Any]:
    database = os.path.join(path, _FILE_NAME)
    with contextlib.closing(sqlite3.connect(database)) as connection:
        return connection.execute(_SELECT_ROWS).fetchall()


# Gives each test an empty handler table, no registration and an open log.
class IsolatedCase(unittest.TestCase):
    # Patches the table and the state, opens the log in a scratch directory.
    def setUp(self) -> None:
        table = unittest.mock.patch.dict(_HANDLERS_TARGET, {}, clear=True)
        state = unittest.mock.patch(_DEBUG_TARGET, None)
        for patcher in (table, state):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.path = scratch.name
        verbose.log_open(self.path, _RING_LINES)
        self.addCleanup(verbose.log_close)
        verbose.level_set(2)


# Tests the handler of `verbose.put`.
class TestPut(IsolatedCase):
    # Page lines are stored under their thread, whatever the level.
    def test_lines_stored(self) -> None:
        engine_verbose.handlers_register(True)
        ui = _line_make("verbose.put", thread="ui", lines=_PAGE_LINES)
        ai = _line_make(
            "verbose.put",
            thread="ai",
            lines=[{"at": 30, "level": 0, "text": "c"}],
        )
        self.assertIsNone(dispatch.line_dispatch(ui))
        self.assertIsNone(dispatch.line_dispatch(ai))
        self.assertEqual(
            _rows_read(self.path),
            [
                (1, 10, "ui", 1, "a"),
                (2, 20, "ui", 2, "b"),
                (3, 30, "ai", 0, "c"),
            ],
        )

    # Page lines are not in the ring of the server.
    def test_ring_unchanged(self) -> None:
        engine_verbose.handlers_register(True)
        line = _line_make("verbose.put", thread="ui", lines=_PAGE_LINES)
        dispatch.line_dispatch(line)
        self.assertEqual(verbose.history_get(_HISTORY_ALL), [])

    # With debug mode off the handler raises and nothing is written.
    def test_debug_off(self) -> None:
        engine_verbose.handlers_register(False)
        line = _line_make("verbose.put", thread="ui", lines=_PAGE_LINES)
        with self.assertRaises(RuntimeError):
            dispatch.line_dispatch(line)
        self.assertEqual(_rows_read(self.path), [])

    # A bad field raises and the batch that holds the line is not written.
    def test_line_invalid(self) -> None:
        engine_verbose.handlers_register(True)
        for bad in _LINES_INVALID:
            with self.subTest(bad=bad):
                line = _line_make(
                    "verbose.put", thread="ui", lines=_PAGE_LINES + [bad]
                )
                with self.assertRaises(ValueError):
                    dispatch.line_dispatch(line)
                self.assertEqual(_rows_read(self.path), [])

    # A thread other than ui or ai raises and nothing is written.
    def test_thread_unknown(self) -> None:
        engine_verbose.handlers_register(True)
        for thread in ("server", "console", ""):
            with self.subTest(thread=thread):
                line = _line_make(
                    "verbose.put", thread=thread, lines=_PAGE_LINES
                )
                with self.assertRaises(ValueError):
                    dispatch.line_dispatch(line)
                self.assertEqual(_rows_read(self.path), [])

    # Called before the registration the handler raises.
    def test_unregistered(self) -> None:
        line = _line_make("verbose.put")
        with self.assertRaises(RuntimeError):
            engine_verbose.verbose_put(line, thread="ui", lines=[])


# Tests the handler of `verbose.tail`.
class TestTail(IsolatedCase):
    # The reply holds the last lines of the ring with all three fields.
    def test_tail_lines(self) -> None:
        engine_verbose.handlers_register(True)
        for text in ("a", "b", "c"):
            verbose.log(1, text)
        reply = _reply_get(
            _line_make("verbose.tail", 7, thread="server", count=2)
        )
        self.assertEqual(reply[0]["r"], 7)
        expected = [
            {"at": entry.at, "level": entry.level, "text": entry.text}
            for entry in verbose.history_get(2)
        ]
        self.assertEqual(jslb.payload_of(reply), {"lines": expected})
        self.assertEqual([entry["text"] for entry in expected], ["b", "c"])
        self.assertEqual([entry["level"] for entry in expected], [1, 1])

    # The count limits the reply, oldest first, and a large one gives all.
    def test_tail_counts(self) -> None:
        engine_verbose.handlers_register(True)
        for text in ("a", "b", "c"):
            verbose.log(1, text)
        expected: dict[int, list[str]] = {
            0: [],
            1: ["c"],
            3: ["a", "b", "c"],
            _HISTORY_ALL: ["a", "b", "c"],
        }
        for count, texts in expected.items():
            with self.subTest(count=count):
                reply = _reply_get(
                    _line_make("verbose.tail", 1, thread="server", count=count)
                )
                lines = jslb.payload_of(reply)["lines"]
                self.assertEqual([entry["text"] for entry in lines], texts)

    # The lines of the page threads are not in the reply.
    def test_tail_page(self) -> None:
        engine_verbose.handlers_register(True)
        page = _line_make("verbose.put", thread="ui", lines=_PAGE_LINES)
        dispatch.line_dispatch(page)
        verbose.log(1, "s")
        reply = _reply_get(
            _line_make("verbose.tail", 1, thread="server", count=_HISTORY_ALL)
        )
        lines = jslb.payload_of(reply)["lines"]
        self.assertEqual([entry["text"] for entry in lines], ["s"])

    # The server holds the ring of its own thread only, so the others raise.
    def test_tail_thread(self) -> None:
        engine_verbose.handlers_register(True)
        for thread in ("ui", "ai", "console", "", "SERVER"):
            with self.subTest(thread=thread):
                line = _line_make("verbose.tail", 1, thread=thread, count=1)
                with self.assertRaises(ValueError):
                    dispatch.line_dispatch(line)

    # A negative count raises.
    def test_tail_negative(self) -> None:
        engine_verbose.handlers_register(True)
        line = _line_make("verbose.tail", 1, thread="server", count=-1)
        with self.assertRaises(ValueError):
            dispatch.line_dispatch(line)

    # Debug mode does not gate the tail.
    def test_tail_ungated(self) -> None:
        engine_verbose.handlers_register(False)
        verbose.log(1, "a")
        reply = _reply_get(
            _line_make("verbose.tail", 1, thread="server", count=1)
        )
        lines = jslb.payload_of(reply)["lines"]
        self.assertEqual([entry["text"] for entry in lines], ["a"])

    # A tail of a log that is not open raises.
    def test_tail_unopened(self) -> None:
        engine_verbose.handlers_register(True)
        verbose.log_close()
        line = _line_make("verbose.tail", 1, thread="server", count=1)
        with self.assertRaises(RuntimeError):
            dispatch.line_dispatch(line)


# Tests the registration.
class TestRegister(IsolatedCase):
    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_verbose.handlers_register(True)
        with self.assertRaises(ValueError):
            engine_verbose.handlers_register(True)
