# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the audit's handlers in forked children, each on a scratch root in
# `build/` with the real dispatcher and a real audit, so that a registration
# never reaches another test. The lines go through `dispatch.line_dispatch`,
# as the main loop sends them: a record whose blob is bytes and one whose blob
# is a file the sink finished, which goes once read, laid out as the gold's
# body; a note; a record with no blob refused; the tail's newest entries and
# its fit, a reply one byte below `line_max` holding two entries and one at
# `line_max` holding one; both dumps, the browser's from the blob and the
# server's from a real store; and the handlers unregistered outside debug
# mode and refused before the registration. The texts are the gold's.

import audit, dispatch, engine_audit, harness, jslb, json, os, signal
import substrate, sys, tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_engine_audit"

# The settings the handlers and the store are sized by.
_BLOB_MAX: int = harness.setting_get("blob_max")
_LINE_MAX: int = harness.setting_get("line_max")
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# The file in the scratch directory that a child writes how it ended to.
_ENDING_NAME = "ending.json"

# The id of the tail's request, a value chosen by its writer.
_TAIL_ID = 7

# The time of every record and note, in milliseconds since the epoch.
_AT = 1793990940123


# A value of this module's gold.
def _gold(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# Lines of the gold joined as one text.
def _joined(name: str) -> str:
    return "\n".join(_gold(name))


# A line in full names of the type, its blobs and payload.
def _line(
    type: str, blobs: list[jslb.Object], id: int | None = None, **payload: Any
) -> jslb.Object:
    header = jslb.header_make(type, id=id, full=True)
    return jslb.line_make(header, blobs, **payload)


# The record of the gold's line, its JSON text as the blob given.
def _record(blob: jslb.Object) -> jslb.Object:
    return _line("audit.line", [blob], sender="ui", receiver="ai", at=_AT)


# A note of thread `ai` at the fixed time.
def _note(text: str) -> jslb.Object:
    return _line("audit.note", [], thread="ai", at=_AT, text=text)


# The tail's request of the count.
def _tail(count: int) -> jslb.Object:
    return _line("audit.tail", [], id=_TAIL_ID, count=count)


# The bytes of the tail's reply that carries the text.
def _reply_bytes(text: str) -> int:
    reply = dispatch.reply_make(_tail(0), text=text)
    return sum(len(piece) for piece in jslb.line_encode(reply))


# The entries of the root's audit as label and body.
def _entries(root: str) -> list[list[str]]:
    return [[entry.label, entry.body] for entry in audit.entries_read(root)]


# In a child: opens the root's audit and registers on a store of the root.
def _ready(root: str, line_max: int = _LINE_MAX) -> substrate.Store:
    audit.audit_open(root, _BLOB_MAX, "engine")
    store = substrate.Store(root, _OVERFLOW_BYTES, _BLOB_MAX)
    engine_audit.handlers_register(True, line_max, store)
    return store


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
        with open(path, "w", encoding="utf-8") as file:
            file.write(json.dumps(ending))
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

    # Runs the work in a child and checks the type and text it raised.
    def child_raised(
        self, work: Callable[[], object], kind: str, text: str
    ) -> None:
        ending = self.child_run(work)
        self.assertNotIn("returned", ending)
        self.assertEqual(ending["raised"], [kind, text])


# Tests the records and notes a page thread sends.
class TestRecord(ScratchCase):
    # A blob of bytes is laid out as the gold's body under its label.
    def test_record_bytes(self) -> None:
        text = json.dumps(_gold("record_line"))

        def work() -> Any:
            _ready(self.root)
            blob = jslb.blob_make(text.encode("utf-8"))
            dispatch.line_dispatch(_record(blob))
            return _entries(self.root)

        self.assertEqual(
            self.child_value(work), [["ui to ai", _joined("record_body")]]
        )

    # A blob the sink finished is read from its file, which then goes.
    def test_record_file(self) -> None:
        path = os.path.join(self.scratch, "blob")
        with open(path, "w", encoding="utf-8") as file:
            file.write(json.dumps(_gold("record_line")))

        def work() -> Any:
            _ready(self.root)
            dispatch.line_dispatch(_record(jslb.blob_make(path)))
            return _entries(self.root)

        self.assertEqual(
            self.child_value(work), [["ui to ai", _joined("record_body")]]
        )
        self.assertFalse(os.path.exists(path))

    # A note's text is indented under its label.
    def test_note(self) -> None:
        def work() -> Any:
            _ready(self.root)
            dispatch.line_dispatch(_note(_gold("note_text")))
            return _entries(self.root)

        body = "  " + _gold("note_text")
        self.assertEqual(self.child_value(work), [["note of ai", body]])

    # A record with no blob is refused, and the audit holds nothing.
    def test_blob_missing(self) -> None:
        def work() -> Any:
            _ready(self.root)
            payload = {"sender": "ui", "receiver": "ai", "at": _AT}
            dispatch.line_dispatch(_line("audit.line", [], **payload))

        text = _gold("texts.blob_missing")
        self.child_raised(work, "ValueError", text)
        self.assertEqual(_entries(self.root), [])


# Tests the end of the audit sent back in one reply below `line_max`.
class TestTail(ScratchCase):
    # The texts of the gold's notes as the document holds them.
    def texts(self) -> list[str]:
        notes: list[str] = _gold("tail_notes")
        return [audit.note_text("ai", _AT, note) for note in notes]

    # In a child on a root of its own: three notes, then the tail asked.
    def tail_text(self, count: int, line_max: int) -> Any:
        root = tempfile.mkdtemp(dir=self.scratch)

        def work() -> Any:
            _ready(root, line_max)
            for note in _gold("tail_notes"):
                dispatch.line_dispatch(_note(note))
            reply = dispatch.line_dispatch(_tail(count))
            return [jslb.field_get(reply[0], "reply"), reply["text"]]

        return self.child_value(work)

    # The newest entries, at most the count, oldest first.
    def test_newest(self) -> None:
        texts = self.texts()
        self.assertEqual(
            self.tail_text(2, _LINE_MAX), [_TAIL_ID, "".join(texts[1:])]
        )
        self.assertEqual(
            self.tail_text(9, _LINE_MAX), [_TAIL_ID, "".join(texts)]
        )

    # A reply one byte past the entries' fits them, one at `line_max` does not.
    def test_fit(self) -> None:
        texts = self.texts()
        size = _reply_bytes("".join(texts[1:]))
        self.assertEqual(
            self.tail_text(3, size + 1), [_TAIL_ID, "".join(texts[1:])]
        )
        self.assertEqual(self.tail_text(3, size), [_TAIL_ID, texts[2]])


# Tests the dumps of both sides' databases.
class TestDump(ScratchCase):
    # The browser's views from the blob, then the server's own store's.
    def test_dumps(self) -> None:
        views = json.dumps(_gold("views"))

        def work() -> Any:
            store = _ready(self.root)
            store.db_create("alpha")
            store.kv_put("/alpha/note", b"hi")
            blob = jslb.blob_make(views.encode("utf-8"))
            dispatch.line_dispatch(_line("db.dump", [blob]))
            return _entries(self.root)

        self.assertEqual(
            self.child_value(work),
            [
                ["databases of the browser", _joined("browser_body")],
                ["databases of the server", _joined("server_body")],
            ],
        )


# Tests the registration of the handlers.
class TestRegister(ScratchCase):
    # Outside debug mode nothing is registered.
    def test_debug_off(self) -> None:
        def work() -> Any:
            audit.audit_open(self.root, _BLOB_MAX, "engine")
            store = substrate.Store(self.root, _OVERFLOW_BYTES, _BLOB_MAX)
            engine_audit.handlers_register(False, _LINE_MAX, store)
            dispatch.line_dispatch(_note("x"))

        text = _gold("texts.handler_unknown")
        self.child_raised(work, "LookupError", text)

    # Before the registration the tail and the dumps are refused, unwritten.
    def test_not_registered(self) -> None:
        def work() -> Any:
            audit.audit_open(self.root, _BLOB_MAX, "engine")
            refused: list[str] = []
            blob = jslb.blob_make(b"[]")
            for call in (
                lambda: engine_audit.audit_tail(_tail(1), count=1),
                lambda: engine_audit.db_dump(_line("db.dump", [blob])),
            ):
                try:
                    call()
                except RuntimeError as error:
                    refused.append(str(error))
            return [refused, _entries(self.root)]

        text = _gold("texts.not_registered")
        self.assertEqual(self.child_value(work), [[text, text], []])
