# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests engine_verbose with its real callees in forked children, each on the
# real log of a scratch root in `build/`: lines of the gold written as wire
# bytes, read by the real jslb decoder and served by the real dispatcher,
# each reply encoded by the real jslb encoder and read back from its JSON
# text. The page lines each put writes, and a tail of each page thread that
# gives them back; the server's tail from its ring against `_verbose`; the
# values the decoder makes of a bad line's fields, each refused with the
# gold's text and its batch unwritten; the gate of debug mode; and
# `verbose.put` a push and `verbose.tail` a request, the dispatcher refusing
# each sent the other way. Each child writes how its work ended to a file,
# or to stderr when that write fails, then kills itself.

import contextlib, engine_verbose, functools, harness, json, os, signal
import sqlite3, sys, tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any, NoReturn

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_engine_verbose"

# The limits of the decoder, as the checkout sets them.
_LINE_MAX: int = harness.setting_get("line_max")
_BLOB_MAX: int = harness.setting_get("blob_max")
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# The lines the ring of a child's log holds, as the checkout sets it.
_RING: int = harness.setting_get("verbose_ring")

# The file of the root's log.
_LOG_FILE = "_verbose.sqlite"

# The query of the time, thread and text of each line of the log, in order.
_ROWS_QUERY = "SELECT at, thread, text FROM line ORDER BY seq"

# The thread whose lines the server's own ring holds.
_SERVER_THREAD = "server"

# The texts the server logs in a child before its lines are served.
_SERVER_TEXTS: list[str] = harness.gold_get(f"{_GOLD_ID}.server_texts")

# The file in the scratch directory that a child writes how it ended to.
_ENDING_NAME = "ending.json"


# A value of this module's gold as JSON holds it, which is not to be changed.
def _gold_raw(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The bytes of a line on the wire: its JSON text and the CR that ends it.
def _line_bytes(line: dict[str, Any]) -> bytes:
    text = json.dumps(line, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8") + b"\r"


# The bytes of a gold line.
def _gold_bytes(name: str) -> bytes:
    return _line_bytes(_gold_raw(f"lines.{name}"))


# The rows a gold put writes in the log, in order.
def _put_rows(name: str) -> list[tuple[int, str, str]]:
    put = _gold_raw(f"lines.{name}")
    return [
        (entry["at"], put["thread"], entry["text"]) for entry in put["lines"]
    ]


# Refuses a blob that streams: no line of these tests carries one.
def _sink_refuse(header: engine_verbose.jslb.Object) -> NoReturn:
    raise AssertionError(f"a blob came that streams: {header}")


# The lines of the bytes, read by the real decoder with the checkout's limits.
def _lines_decode(data: bytes) -> list[engine_verbose.jslb.Object]:
    decoder = engine_verbose.jslb.LineDecoder(
        _LINE_MAX, _BLOB_MAX, _OVERFLOW_BYTES, _sink_refuse
    )
    return decoder.bytes_feed(data)


# The JSON text of a reply as the real encoder writes it, read back.
def _reply_read(reply: object) -> object:
    if not isinstance(reply, engine_verbose.jslb.Object):
        raise AssertionError(f"the result is not a reply: {reply!r}")
    (piece,) = engine_verbose.jslb.line_encode(reply)
    if not isinstance(piece, bytes):
        raise AssertionError(f"the reply's text is not bytes: {piece!r}")
    return json.loads(piece)


# The time, thread and text of each line of the root's log, in order.
def _rows_read(root: str) -> list[tuple[int, str, str]]:
    path = os.path.join(root, _LOG_FILE)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        rows: list[tuple[int, str, str]] = connection.execute(
            _ROWS_QUERY
        ).fetchall()
    return rows


# The rows of the page threads in the root's log, in order.
def _page_rows(root: str) -> list[tuple[int, str, str]]:
    return [row for row in _rows_read(root) if row[1] != _SERVER_THREAD]


# In a child: opens the log, registers, logs texts, returns each line's reply.
def _lines_serve(root: str, debug: bool, data: bytes) -> list[object]:
    engine_verbose.verbose.log_open(root, _RING)
    engine_verbose.handlers_register(debug)
    for text in _SERVER_TEXTS:
        engine_verbose.verbose.log(text)
    replies: list[object] = []
    for line in _lines_decode(data):
        result = engine_verbose.dispatch.line_dispatch(line)
        replies.append(None if result is None else _reply_read(result))
    return replies


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(work: Callable[[], object], path: str) -> None:
    try:
        try:
            ending: dict[str, object] = {"returned": work()}
        except BaseException as error:
            ending = {
                "raised": [type(error).__name__, str(error)],
                "trace": traceback.format_exc(),
            }
        text = json.dumps(ending)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
    except BaseException:
        # The parent finds no ending, so the failure goes to stderr.
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a scratch root in `build/` and runs its work in children.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the empty root in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)

    # Runs the work in a forked child and returns how it ended.
    def child_run(self, work: Callable[[], object]) -> dict[str, Any]:
        path = os.path.join(self.scratch, _ENDING_NAME)
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child_end(work, path)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending: dict[str, Any] = json.load(file)
        os.remove(path)
        return ending

    # Runs the work in a child and returns what it returned.
    def child_value(self, work: Callable[[], object]) -> Any:
        ending = self.child_run(work)
        if "raised" in ending:
            self.fail(ending["trace"])
        return ending["returned"]

    # Runs the work in a child and checks the type and the text it raised.
    def child_raise(
        self,
        work: Callable[[], object],
        kind: type[BaseException],
        message: str,
    ) -> None:
        ending = self.child_run(work)
        if "returned" in ending:
            self.fail(f"nothing was raised: {ending['returned']!r}")
        expected = [kind.__name__, message]
        self.assertEqual(ending["raised"], expected, ending["trace"])


# Tests the `verbose.put` and `verbose.tail` lines served by the dispatcher.
class TestServe(ScratchCase):
    # Each put is written, and a tail of each page thread replies with it.
    def test_threads_served(self) -> None:
        names = ("put_ui", "put_ai", "tail_ui", "tail_ai")
        data = b"".join(_gold_bytes(name) for name in names)
        work = functools.partial(_lines_serve, self.root, True, data)
        expected = [
            None,
            None,
            _gold_raw("lines.tail_ui_reply"),
            _gold_raw("lines.tail_ai_reply"),
        ]
        self.assertEqual(self.child_value(work), expected)
        rows = _put_rows("put_ui") + _put_rows("put_ai")
        self.assertEqual(_page_rows(self.root), rows)

    # The server's tail is the last lines it logged, as the log stored them.
    def test_server_served(self) -> None:
        data = _gold_bytes("tail_server")
        work = functools.partial(_lines_serve, self.root, True, data)
        (reply,) = self.child_value(work)
        count: int = _gold_raw("lines.tail_server")["count"]
        logged = [
            {"at": at, "text": text}
            for at, thread, text in _rows_read(self.root)
            if thread == _SERVER_THREAD
        ]
        lines = logged[len(logged) - count :]
        expected = {**_gold_raw("lines.tail_server_reply"), "lines": lines}
        self.assertEqual(reply, expected)
        texts = [line["text"] for line in lines]
        self.assertEqual(texts, _SERVER_TEXTS[len(_SERVER_TEXTS) - count :])

    # A field read as a bool, float or number is refused, its batch unwritten.
    def test_fields_refused(self) -> None:
        for case, line in _gold_raw("lines.put_invalid").items():
            with self.subTest(case=case):
                data = _line_bytes(line)
                self.child_raise(
                    functools.partial(_lines_serve, self.root, True, data),
                    ValueError,
                    _text_get(f"engine_verbose_line_invalid_{case}"),
                )
                self.assertEqual(_page_rows(self.root), [])

    # With debug mode off a put is refused, and nothing is written.
    def test_debug_off(self) -> None:
        data = _gold_bytes("put_ui")
        self.child_raise(
            functools.partial(_lines_serve, self.root, False, data),
            RuntimeError,
            _text_get("engine_verbose_debug_off"),
        )
        self.assertEqual(_page_rows(self.root), [])

    # Put requests, written, are refused unanswered, tail pushes for replying.
    def test_kinds_refused(self) -> None:
        data = _gold_bytes("put_request")
        self.child_raise(
            functools.partial(_lines_serve, self.root, True, data),
            ValueError,
            _text_get("dispatch_request_unanswered"),
        )
        self.assertEqual(_page_rows(self.root), _put_rows("put_request"))
        data = _gold_bytes("tail_pushed")
        self.child_raise(
            functools.partial(_lines_serve, self.root, True, data),
            ValueError,
            _text_get("dispatch_notification_replied"),
        )
