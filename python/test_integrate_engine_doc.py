# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `engine_doc` with its callees: its handler registered in the real
# dispatcher on a real store on a scratch root in `build/`. Each test runs in
# a forked child that kills itself when done, so that no registration
# reaches another test, and the parent checks how the child said it ended.
# Lines of the gold go as wire bytes through the real JSLB decoder to
# `dispatch.line_dispatch`, and the documents are read back from the store:
# a put in each name form writes the next version of the body as the decoder
# read it, and a request is applied, then refused, its `error` line encoded
# by the real JSLB encoder and read back.

import copy, dispatch, engine_doc, harness, jslb, json, os, signal, substrate
import sys, tempfile, traceback, unittest, uuid
from collections.abc import Callable
from typing import Any

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_engine_doc"

# The database the gold's lines name.
_DATABASE = "castle_gatehouse"

# The refs of the scene's first two versions, which the puts write in turn.
_SCENE_REFS = (
    "/castle_gatehouse/scene/arrival/1",
    "/castle_gatehouse/scene/arrival/2",
)

# The most bytes of a line the decoder reads, the checkout's setting.
_LINE_MAX: int = harness.setting_get("line_max")

# The most blob bytes of a line the decoder reads, the checkout's setting.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The size over which the decoder streams a blob and the store caches it.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

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
        engine_doc.handlers_register(store)
        return store

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
    # In the child: a put in each name form, each read back at its version.
    def puts_check(self) -> None:
        store = self.store_register()
        for name, ref in zip(("put", "put_full"), _SCENE_REFS):
            (line,) = self.lines_decode(_line_bytes(name))
            self.assertIsNone(dispatch.line_dispatch(line))
            self.assertEqual(store.doc_head(_DATABASE, line["id"]), ref)
            self.assertEqual(store.doc_get(ref), line["body"])

    # Each put writes the next version of the body, answered by nothing.
    def test_puts_applied(self) -> None:
        self.child_run(self.puts_check)

    # In the child: the request writes the first version, then is refused.
    def request_check(self) -> None:
        store = self.store_register()
        self.request_refuse("put_request")
        document: str = _gold_copy("lines.put_request")["id"]
        self.assertEqual(store.doc_head(_DATABASE, document), _SCENE_REFS[0])

    # A put with `i` is applied, then refused for want of a reply.
    def test_request_refused(self) -> None:
        self.child_run(self.request_check)
