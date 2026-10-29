# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `engine_turn` with its callees: its handler registered in the real
# dispatcher on a real store on a scratch root in `build/`. Each test runs in
# a forked child that kills itself when done, so that no registration
# reaches another test, and the parent checks how the child said it ended.
# Lines of the gold go as wire bytes through the real JSLB decoder to
# `dispatch.line_dispatch`, and the scene's turns are read back from the
# store: messages with null and a list in order, text beyond ASCII as raw
# characters, a line in full names, and a request applied, then refused, its
# `error` line encoded by the real JSLB encoder and read back.

import copy, dispatch, engine_turn, harness, jslb, json, os, signal, substrate
import sys, tempfile, traceback, unittest, uuid
from collections.abc import Callable
from typing import Any

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_engine_turn"

# The database of the scene of the gold's lines.
_SCENE_DB = "metaverse"

# The most bytes of a line the decoder reads, the checkout's setting.
_LINE_MAX: int = harness.setting_get("line_max")

# The most blob bytes of a line the decoder reads, the checkout's setting.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The size over which the decoder streams a blob and the store caches it.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# Text beyond ASCII, built from its code points, as the gold's wide turn.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)

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


# The canonical JSON text of a value, as the handler stores a message.
def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# The turns that gold lines append to their scene in order, from `n` 1.
def _turns_expected(names: list[str]) -> list[substrate.TurnRow]:
    turns: list[substrate.TurnRow] = []
    for n, name in enumerate(names, 1):
        line: dict[str, Any] = _gold_copy(f"lines.{name}")
        text = _json_text(line["content"])
        turns.append(substrate.TurnRow(line["scene"], n, line["role"], text))
    return turns


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

    # In the child: a store on the root with the scene's database, the handler.
    def store_register(self) -> substrate.Store:
        store = substrate.Store(self.root, _OVERFLOW_BYTES)
        store.db_create(_SCENE_DB)
        engine_turn.handlers_register(store)
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
    # In the child: gold lines served in order, then the scene's turns.
    def turns_check(self, *names: str) -> list[substrate.TurnRow]:
        store = self.store_register()
        for name in names:
            self.push_serve(name)
        expected = _turns_expected(list(names))
        turns = store.turn_list(expected[0].scene)
        self.assertEqual(turns, expected)
        return turns

    # The player's message, a call with null and a list, then its answer.
    def test_turns_served(self) -> None:
        names = ("append_user", "append_call", "append_answer")
        self.child_run(lambda: self.turns_check(*names))

    # In the child: the wide text is in the stored message as it is.
    def wide_check(self) -> None:
        (turn,) = self.turns_check("append_wide")
        self.assertIn(_WIDE_TEXT, turn.content)

    # Text beyond ASCII crosses the wire and is stored as raw characters.
    def test_text_wide(self) -> None:
        self.child_run(self.wide_check)

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.turns_check("append_full"))

    # In the child: the request appends its turn, then is refused.
    def request_check(self) -> None:
        store = self.store_register()
        self.request_refuse("append_request")
        expected = _turns_expected(["append_request"])
        self.assertEqual(store.turn_list(expected[0].scene), expected)

    # An append with `i` is applied, then refused for want of a reply.
    def test_request_refused(self) -> None:
        self.child_run(self.request_check)
