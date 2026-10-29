# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `engine_db` with its callees: its handlers registered in the real
# dispatcher on a real store on a scratch root in `build/`. Each test runs in
# a forked child that kills itself when done, so that no registration
# reaches another test, and the parent checks how the child said it ended.
# Lines of the gold go as wire bytes through the real JSLB decoder to
# `dispatch.line_dispatch`, and their effects are read from the store: the
# pushes in both name forms are applied and answered by nothing, and a
# request is applied, then refused, its `error` line encoded by the real
# JSLB encoder and read back. The `db.restore` and `db.file` lines of a
# database are encoded, read back as the gold's in both name forms, and
# restored into a second root, which gives back every value.

import copy, dispatch, engine_db, harness, jslb, json, os, signal, substrate
import sys, tempfile, traceback, unittest, uuid
from collections.abc import Callable
from typing import Any

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_engine_db"

# The database the gold's lines name.
_DATABASE = "castle"

# The most bytes of a line the decoder reads, the checkout's setting.
_LINE_MAX: int = harness.setting_get("line_max")

# The most blob bytes of a line the decoder reads, the checkout's setting.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The size over which the decoder streams a blob and the store caches it.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# A value over `overflow_bytes`, which the store keeps in a cache file.
_VALUE_OVER = bytes(range(256)) * (_OVERFLOW_BYTES // 256 + 1)

# The values of the database by their refs: two in cache files, one in a row.
_VALUES = {
    "/castle/first": _VALUE_OVER,
    "/castle/second": bytes(reversed(_VALUE_OVER)),
    "/castle/third": b"a value held in its row",
}

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


# A gold line as the decoder reads it, blob 1's size set and no data.
def _sized_line(name: str, size: int) -> jslb.Object:
    text = json.dumps(harness.gold_get(f"{_GOLD_ID}.lines.{name}"))
    line: jslb.Object = jslb.json_decode(text)
    line[1]["size" if "type" in line[0] else "s"] = size
    return line


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


# Takes the data off blob 1 of a decoded line: its bytes, or its file's.
def _data_take(line: jslb.Object) -> bytes:
    blob: jslb.Object = line[1]
    data: bytes | str = blob.pop("d")
    if isinstance(data, bytes):
        return data
    # The decoder sets the digest of a blob it streamed to a file.
    del blob["sha256"]
    return _file_read(data)


# The bytes of a value the store holds: as held, or read from its file.
def _value_bytes(data: bytes | str) -> bytes:
    if isinstance(data, bytes):
        return data
    return _file_read(data)


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

    # In the child: a store on the root, the handlers in the dispatcher.
    def store_register(self) -> substrate.Store:
        store = substrate.Store(self.root, _OVERFLOW_BYTES)
        engine_db.handlers_register(store)
        return store

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
    # In the child: a create, then a drop, in each name form, the store after.
    def pushes_check(self) -> None:
        store = self.store_register()
        for suffix in ("", "_full"):
            self.push_serve(f"create{suffix}")
            self.assertEqual(store.db_list(), [_DATABASE])
            self.push_serve(f"drop{suffix}")
            self.assertEqual(store.db_list(), [])

    # Each push in both name forms is applied and answered by nothing.
    def test_pushes_applied(self) -> None:
        self.child_run(self.pushes_check)

    # In the child: the request makes the database, then is refused.
    def request_check(self) -> None:
        store = self.store_register()
        self.request_refuse("create_request")
        self.assertEqual(store.db_list(), [_DATABASE])

    # A create with `i` is applied, then refused for want of a reply.
    def test_request_refused(self) -> None:
        self.child_run(self.request_check)


# Tests the lines of a whole database, encoded, read back and restored.
class TestRestore(ScratchCase):
    # In the child: the database's lines in a name form, read back as gold's.
    def lines_carry(self, full: bool) -> list[bytes]:
        store = self.store_register()
        store.db_create(_DATABASE)
        for ref, value in _VALUES.items():
            store.kv_put(ref, value)
        lines = engine_db.restore_lines(_DATABASE, full)
        sent = self.lines_decode(b"".join(_line_wire(line) for line in lines))
        blobs = [_data_take(line) for line in sent]
        suffix = "_full" if full else ""
        expected = [_sized_line(f"restore{suffix}", len(blobs[0]))]
        for blob in blobs[1:]:
            expected.append(_sized_line(f"file{suffix}", len(blob)))
        self.assertEqual(sent, expected)
        return blobs

    # In the child: a second root restored from the lines holds the values.
    def restore_check(self) -> None:
        data, *files = self.lines_carry(False)
        cached: list[bytes | str] = [*files]
        copied = os.path.join(self.scratch, "copy")
        restored = substrate.Store(copied, _OVERFLOW_BYTES)
        restored.db_restore(_DATABASE, data, cached)
        for ref, value in _VALUES.items():
            self.assertEqual(_value_bytes(restored.kv_get(ref).data), value)

    # The lines carry the whole database: a restore from them gives it back.
    def test_lines_restored(self) -> None:
        self.child_run(self.restore_check)

    # The lines in full names read back as the gold's, one per cache file.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.lines_carry(True))
