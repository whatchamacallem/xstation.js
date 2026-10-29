# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `engine_sql` with its callees: its handler registered in the real
# dispatcher on a real store on a scratch root in `build/`. Each test runs in
# a forked child that kills itself when done, so that no registration
# reaches another test, and the parent checks how the child said it ended.
# Lines of the gold go as wire bytes through the real JSLB decoder to
# `dispatch.line_dispatch`, and the rows their statements made are queried
# back from the store: the universe's statements in each name form, a
# parameter with quotes and text beyond ASCII whole across the wire, and a
# request applied, then refused, its `error` line encoded by the real JSLB
# encoder and read back.

import copy, dispatch, engine_sql, harness, jslb, json, os, signal, substrate
import sys, tempfile, traceback, unittest, uuid
from collections.abc import Callable
from typing import Any

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_engine_sql"

# The database the gold's lines name.
_DATABASE = "castle"

# The most bytes of a line the decoder reads, the checkout's setting.
_LINE_MAX: int = harness.setting_get("line_max")

# The most blob bytes of a line the decoder reads, the checkout's setting.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The size over which the decoder streams a blob and the store caches it.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# Text with quotes, a statement separator and characters beyond ASCII.
_QUOTED_TEXT = "it's 'quoted'; DROP TABLE t; --" + chr(0x4E2D) + chr(0x1F600)

# The query of the rows the gold's universe statements insert.
_WORLD_QUERY = "SELECT name, title FROM world"

# The query of the row the gold's quoted statements insert.
_QUOTED_QUERY = "SELECT x FROM t"

# How a child ends when its work returned.
_ENDING_PASSED = "passed"


# A copy of a value of this module's gold, which the test may change.
def _gold_copy(name: str) -> Any:
    return copy.deepcopy(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The bytes of a gold line on the wire: its JSON text, a CR, then each blob.
def _line_bytes(name: str, *blobs: bytes) -> bytes:
    line: dict[str, Any] = _gold_copy(f"lines.{name}")
    size_name = "size" if "type" in line["0"] else "s"
    for number, blob in enumerate(blobs, 1):
        line[str(number)][size_name] = len(blob)
    text = json.dumps(line, ensure_ascii=False, separators=(",", ":"))
    return b"".join([text.encode("utf-8"), b"\r", *blobs])


# The row the last statement of a gold line inserts: its parameters.
def _row_inserted(name: str) -> list[Any]:
    row: list[Any] = _gold_copy(f"lines.{name}")["statements"][-1]["params"]
    return row


# The bytes of a file.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# The bytes the encoder writes for a line, a blob held in a file read from it.
def _line_wire(line: jslb.Object) -> bytes:
    pieces = [
        piece if isinstance(piece, bytes) else _file_read(piece)
        for piece in jslb.line_encode(line)
    ]
    return b"".join(pieces)


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(work: Callable[[], object], path: str) -> None:
    try:
        try:
            work()
            ending = _ENDING_PASSED
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a scratch root in `build/` and a forked child to run in.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the root in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)

    # Runs the work in a forked child and fails with what the child raised.
    def child_run(self, work: Callable[[], object]) -> None:
        path = os.path.join(self.scratch, "ending.txt")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child_end(work, path)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(path)
        if ending != _ENDING_PASSED:
            self.fail(ending)

    # Names a new file in the scratch directory for a blob the decoder streams.
    def sink_make(self, header: jslb.Object) -> str:
        return os.path.join(self.scratch, uuid.uuid4().hex)

    # Decodes whole lines from bytes, raising a fault found after the last.
    def lines_decode(self, data: bytes) -> list[jslb.Object]:
        decoder = jslb.LineDecoder(
            _LINE_MAX, _BLOB_MAX, _OVERFLOW_BYTES, self.sink_make
        )
        lines = decoder.bytes_feed(data)
        self.assertEqual(decoder.bytes_feed(b""), [])
        self.assertTrue(decoder.idle())
        return lines

    # In the child: a store on the root with the database, the handler in it.
    def store_register(self) -> substrate.Store:
        store = substrate.Store(self.root, _OVERFLOW_BYTES)
        store.db_create(_DATABASE)
        engine_sql.handlers_register(store)
        return store

    # In the child: the rows of a query on the database.
    def rows_get(self, store: substrate.Store, query: str) -> list[list[Any]]:
        select = [substrate.SqlStatement(query, [])]
        (result,) = store.sql_run(_DATABASE, select)
        return result.rows

    # In the child: serves a gold line through the dispatcher, unanswered.
    def push_serve(self, name: str) -> None:
        (line,) = self.lines_decode(_line_bytes(name))
        self.assertIsNone(dispatch.line_dispatch(line))

    # In the child: a gold request refused, its `error` line read back.
    def request_refuse(self, name: str) -> None:
        (line,) = self.lines_decode(_line_bytes(name))
        message = _text_get("dispatch_request_unanswered")
        with self.assertRaises(ValueError) as caught:
            dispatch.line_dispatch(line)
        self.assertEqual(str(caught.exception), message)
        error = dispatch.error_make(line, caught.exception, False)
        (sent,) = self.lines_decode(_line_wire(error))
        self.assertEqual(sent[0], _gold_copy("lines.error_request")["0"])
        self.assertEqual(sent["message"], message)


# Tests the lines of the gold served through the dispatcher.
class TestServed(ScratchCase):
    # In the child: the universe's statements, then the quoted ones.
    def runs_check(self) -> None:
        store = self.store_register()
        self.push_serve("run")
        world = self.rows_get(store, _WORLD_QUERY)
        self.assertEqual(world, [_row_inserted("run")])
        self.push_serve("run_quoted")
        quoted = self.rows_get(store, _QUOTED_QUERY)
        self.assertEqual(quoted, [[_QUOTED_TEXT]])

    # Each run makes its table and row, the quoted text whole, unanswered.
    def test_runs_applied(self) -> None:
        self.child_run(self.runs_check)

    # In the child: the universe's statements in full names.
    def full_check(self) -> None:
        store = self.store_register()
        self.push_serve("run_full")
        world = self.rows_get(store, _WORLD_QUERY)
        self.assertEqual(world, [_row_inserted("run_full")])

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(self.full_check)

    # In the child: the request runs its statements, then is refused.
    def request_check(self) -> None:
        store = self.store_register()
        self.request_refuse("run_request")
        world = self.rows_get(store, _WORLD_QUERY)
        self.assertEqual(world, [_row_inserted("run_request")])

    # A run with `i` is applied, then refused for want of a reply.
    def test_request_refused(self) -> None:
        self.child_run(self.request_check)
