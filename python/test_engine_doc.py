# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `doc.put` and `doc.head` through the dispatcher on a real store under
# `build/`: a scene put and its head read back, versions that never change,
# bodies read off the wire with integer header keys, a stale `since`, bodies
# the store refuses, and a recorded sequence replayed to a second store. A new
# database starts at `seq` 0.

import dispatch, engine_doc, jslb, os, sqlite3, substrate, tempfile, unittest
import unittest.mock
from collections.abc import Callable
from i18n import i18n
from typing import Any

# The checkout's build directory, where each test makes its scratch roots.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The dotted name of the handler table that the tests patch.
_HANDLERS_TARGET = "dispatch._HANDLERS"

# The dotted name of the store that the tests patch.
_STORE_TARGET = "engine_doc._STATE.store"

# The `overflow_bytes` of the settings, 128 KiB.
_OVERFLOW_BYTES = 131072

# The `line_max` of the settings, 1 MiB.
_LINE_MAX = 1048576

# The `blob_max` of the settings, the largest database.
_BLOB_MAX = 2147483391

# The database the tests put their documents in.
_DATABASE = "castle_gatehouse"

# The id of the arrival scene of the castle gatehouse.
_SCENE_ID = "scene/arrival"

# The ref of the first version of the scene: its database, id and 1.
_SCENE_REF = "/castle_gatehouse/scene/arrival/1"

# Text beyond ASCII, built from its code points.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)

# The subtitle of the arrival scene.
_ARRIVAL_SUBTITLE = (
    "Mind the moat. The gatehouse keeper has been expecting someone,"
    " though not necessarily you."
)

# The arrival scene of the castle gatehouse in its stored form.
_ARRIVAL_BODY: dict[int | str, Any] = {
    0: {"t": "scene"},
    1: "/_files/gatehouse/arrival.png",
    "subtitle": _ARRIVAL_SUBTITLE,
    "image": {"$ref": 1},
}

# The same scene with another subtitle, a later version of the document.
_ARRIVAL_BODY_TWO: dict[int | str, Any] = {
    0: {"t": "scene"},
    1: "/_files/gatehouse/arrival.png",
    "subtitle": "The keeper is not in.",
    "image": {"$ref": 1},
}

# The stored text of the arrival scene, its canonical JSON.
_ARRIVAL_TEXT = (
    '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png","subtitle":"'
    + _ARRIVAL_SUBTITLE
    + '","image":{"$ref":1}}'
)

# A document with no reference strings, the shape of a prompt.
_PROMPT_BODY: dict[int | str, Any] = {
    0: {"t": "prompt"},
    "text": "You are the analyst.",
}

# The puts to replay, each an id and a body.
_RECORDED: list[tuple[str, dict[int | str, Any]]] = [
    (_SCENE_ID, _ARRIVAL_BODY),
    ("prompt", _PROMPT_BODY),
    (_SCENE_ID, _ARRIVAL_BODY_TWO),
    (_SCENE_ID, _ARRIVAL_BODY),
]


# Builds a request line: the type, the id and the payload.
def _line_make(name: str, request_id: int, **payload: Any) -> jslb.Object:
    header = jslb.header_make(name, id=request_id)
    return jslb.line_make(header, [], **payload)


# Dispatches a line that must be answered and returns the reply.
def _reply_get(line: jslb.Object) -> jslb.Object:
    reply = dispatch.line_dispatch(line)
    if reply is None:
        raise AssertionError("the line was not answered")
    return reply


# Refuses a streamed blob, which no line of these tests carries.
def _sink_refuse(header: jslb.Object) -> str:
    raise AssertionError("a blob was streamed")


# The bytes of a line on the wire, which these tests give no blobs.
def _wire_bytes(line: jslb.Object) -> bytes:
    wire = b""
    for piece in jslb.line_encode(line):
        if not isinstance(piece, bytes):
            raise AssertionError("a blob was streamed")
        wire += piece
    return wire


# Decodes the one line the bytes hold.
def _line_decode(wire: bytes) -> jslb.Object:
    decoder = jslb.LineDecoder(
        _LINE_MAX, _BLOB_MAX, _OVERFLOW_BYTES, _sink_refuse
    )
    (line,) = decoder.bytes_feed(wire)
    return line


# Builds a `doc.put` line as the server reads it off the wire.
def _put_line(
    db: str, name: str, body: dict[int | str, Any], since: int
) -> jslb.Object:
    line = _line_make("doc.put", 1, db=db, id=name, body=body, since=since)
    return _line_decode(_wire_bytes(line))


# Closes every database a store has open.
def _store_close(store: substrate.Store) -> None:
    for name in store.db_list():
        store.db_close(name)


# Every statement of the dump of a database file: its schema and its rows.
def _database_dump(path: str) -> list[str]:
    connection = sqlite3.connect(path)
    try:
        return list(connection.iterdump())
    finally:
        connection.close()


# Gives each test an empty handler table, no registration and a real store.
class IsolatedCase(unittest.TestCase):
    # Patches the table and the state, makes a store with a database in it.
    def setUp(self) -> None:
        table = unittest.mock.patch.dict(_HANDLERS_TARGET, {}, clear=True)
        state = unittest.mock.patch(_STORE_TARGET, None)
        for patcher in (table, state):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.root = self.root_make()
        self.store = self.store_make(self.root)
        self.store.db_create(_DATABASE)

    # Makes a scratch root under `build/`, removed when the test ends.
    def root_make(self) -> str:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        return self.enterContext(tempfile.TemporaryDirectory(dir=_BUILD_PATH))

    # Makes a store on a root, closing its databases when the test ends.
    def store_make(self, root: str) -> substrate.Store:
        store = substrate.Store(root, _OVERFLOW_BYTES)
        self.addCleanup(_store_close, store)
        return store

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)

    # Dispatches a line and checks the type and the text of what it raises.
    def dispatch_check(
        self, kind: type[Exception], message: str, line: jslb.Object
    ) -> None:
        self.raise_check(kind, message, lambda: dispatch.line_dispatch(line))

    # Checks that the scene has no head, as nothing was put under its id.
    def head_absent(self) -> None:
        message = i18n("substrate.id_missing", _SCENE_ID, _DATABASE)
        self.raise_check(
            LookupError,
            message,
            lambda: self.store.doc_head(_DATABASE, _SCENE_ID),
        )


# Tests the handler of `doc.put`.
class TestPut(IsolatedCase):
    # The first put writes version 1, its ref and `seq` 1.
    def test_version_written(self) -> None:
        engine_doc.handlers_register(self.store)
        line = _put_line(_DATABASE, _SCENE_ID, _ARRIVAL_BODY, 0)
        reply = _reply_get(line)
        self.assertEqual(reply[0], {"t": "doc.put", "r": 1})
        self.assertEqual(jslb.payload_of(reply), {"ref": _SCENE_REF, "seq": 1})
        self.assertEqual(self.store.doc_get(_SCENE_REF), _ARRIVAL_BODY)
        stored = self.store.kv_get(_SCENE_REF).data
        self.assertEqual(stored, _ARRIVAL_TEXT.encode("utf-8"))
        self.assertEqual(self.store.seq_get(_DATABASE), 1)

    # A version once written never changes, and the head follows the puts.
    def test_versions_kept(self) -> None:
        engine_doc.handlers_register(self.store)
        bodies = (_ARRIVAL_BODY, _ARRIVAL_BODY, _ARRIVAL_BODY_TWO)
        for index, body in enumerate(bodies):
            line = _put_line(_DATABASE, _SCENE_ID, body, index)
            reply = _reply_get(line)
            ref = f"/castle_gatehouse/scene/arrival/{index + 1}"
            payload = {"ref": ref, "seq": index + 1}
            self.assertEqual(jslb.payload_of(reply), payload)
            head = {"db": _DATABASE, "id": _SCENE_ID}
            request = _line_make("doc.head", 2, **head)
            self.assertEqual(_reply_get(request)["ref"], ref)
        first = self.store.doc_get("/castle_gatehouse/scene/arrival/1")
        third = self.store.doc_get("/castle_gatehouse/scene/arrival/3")
        self.assertEqual(first, _ARRIVAL_BODY)
        self.assertEqual(third, _ARRIVAL_BODY_TWO)

    # Two ids keep two heads.
    def test_ids_apart(self) -> None:
        engine_doc.handlers_register(self.store)
        _reply_get(_put_line(_DATABASE, _SCENE_ID, _ARRIVAL_BODY, 0))
        _reply_get(_put_line(_DATABASE, "prompt", _PROMPT_BODY, 1))
        _reply_get(_put_line(_DATABASE, "prompt", _PROMPT_BODY, 2))
        self.assertEqual(self.store.doc_head(_DATABASE, _SCENE_ID), _SCENE_REF)
        self.assertEqual(
            self.store.doc_head(_DATABASE, "prompt"),
            "/castle_gatehouse/prompt/2",
        )

    # Text beyond ASCII is stored as the `UTF-8` bytes the wire carried.
    def test_text_wide(self) -> None:
        engine_doc.handlers_register(self.store)
        body: dict[int | str, Any] = {0: {"t": "prompt"}, "text": _WIDE_TEXT}
        reply = _reply_get(_put_line(_DATABASE, "wide", body, 0))
        stored = self.store.kv_get(reply["ref"]).data
        self.assertIn(_WIDE_TEXT.encode("utf-8"), stored)
        self.assertEqual(self.store.doc_get(reply["ref"]), body)

    # A stale `since` raises the desync and nothing is written.
    def test_since_stale(self) -> None:
        engine_doc.handlers_register(self.store)
        line = _put_line(_DATABASE, _SCENE_ID, _ARRIVAL_BODY, 1)
        message = i18n("substrate.since_stale", "doc.put", 1, 0, _DATABASE)
        self.dispatch_check(RuntimeError, message, line)
        self.head_absent()
        self.assertEqual(self.store.seq_get(_DATABASE), 0)

    # A body the store refuses raises and nothing is written.
    def test_body_invalid(self) -> None:
        engine_doc.handlers_register(self.store)
        cases: list[tuple[dict[int | str, Any], str]] = [
            ({"subtitle": "x"}, i18n("substrate.header_missing")),
            (
                {0: {"t": "scene"}, "image": {"$ref": 1}},
                i18n("substrate.ref_index", 1),
            ),
            (
                {0: {"t": "scene", "x": 1}},
                i18n("substrate.header_bad", {"t": "scene", "x": 1}),
            ),
            (
                {0: {"t": "scene", "v": 0}},
                i18n("substrate.header_bad", {"t": "scene", "v": 0}),
            ),
            ({0: {"v": 2}}, i18n("substrate.header_bad", {"v": 2})),
        ]
        for body, message in cases:
            with self.subTest(body=body):
                line = _put_line(_DATABASE, _SCENE_ID, body, 0)
                self.dispatch_check(ValueError, message, line)
        self.head_absent()
        self.assertEqual(self.store.seq_get(_DATABASE), 0)

    # An empty id raises, and so does a database that is not open.
    def test_target_invalid(self) -> None:
        engine_doc.handlers_register(self.store)
        line = _put_line(_DATABASE, "", _PROMPT_BODY, 0)
        message = i18n("substrate.id_empty")
        self.dispatch_check(ValueError, message, line)
        line = _put_line("none", "prompt", _PROMPT_BODY, 0)
        message = i18n("substrate.db_closed", "none")
        self.dispatch_check(LookupError, message, line)
        self.assertEqual(self.store.seq_get(_DATABASE), 0)


# Tests the handler of `doc.head`.
class TestHead(IsolatedCase):
    # The head is the ref of the version the last put wrote.
    def test_head_replied(self) -> None:
        engine_doc.handlers_register(self.store)
        _reply_get(_put_line(_DATABASE, _SCENE_ID, _ARRIVAL_BODY, 0))
        line = _line_make("doc.head", 5, db=_DATABASE, id=_SCENE_ID)
        reply = _reply_get(line)
        payload = {"ref": _SCENE_REF}
        self.assertEqual(reply[0], {"t": "doc.head", "r": 5})
        self.assertEqual(jslb.payload_of(reply), payload)
        decoded = _line_decode(_wire_bytes(reply))
        self.assertEqual(jslb.payload_of(decoded), payload)

    # An id nothing was put under raises, and so does a database not open.
    def test_head_unknown(self) -> None:
        engine_doc.handlers_register(self.store)
        line = _line_make("doc.head", 1, db=_DATABASE, id="prompt")
        message = i18n("substrate.id_missing", "prompt", _DATABASE)
        self.dispatch_check(LookupError, message, line)
        line = _line_make("doc.head", 1, db="none", id="prompt")
        message = i18n("substrate.db_closed", "none")
        self.dispatch_check(LookupError, message, line)


# Tests a recorded sequence of forwarded operations on a second store.
class TestReplay(IsolatedCase):
    # The server's store ends as the modifier's store did, `seq` for `seq`.
    def test_recorded_replay(self) -> None:
        second_root = self.root_make()
        second = self.store_make(second_root)
        second.db_create(_DATABASE)
        engine_doc.handlers_register(second)
        refs: list[str] = []
        seqs: list[int] = []
        for name, body in _RECORDED:
            since = self.store.seq_get(_DATABASE)
            ref, seq = self.store.doc_put(_DATABASE, name, body)
            reply = _reply_get(_put_line(_DATABASE, name, body, since))
            self.assertEqual(reply["ref"], ref)
            self.assertEqual(reply["seq"], seq)
            refs.append(reply["ref"])
            seqs.append(reply["seq"])
        self.assertEqual(
            refs,
            [
                _SCENE_REF,
                "/castle_gatehouse/prompt/1",
                "/castle_gatehouse/scene/arrival/2",
                "/castle_gatehouse/scene/arrival/3",
            ],
        )
        self.assertEqual(seqs, [1, 2, 3, 4])
        _store_close(self.store)
        _store_close(second)
        name = _DATABASE + ".sqlite"
        self.assertEqual(
            _database_dump(os.path.join(self.root, name)),
            _database_dump(os.path.join(second_root, name)),
        )


# Tests the registration.
class TestRegister(IsolatedCase):
    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_doc.handlers_register(self.store)
        message = i18n("dispatch.handler_twice", "doc.put", 0)
        self.raise_check(
            ValueError,
            message,
            lambda: engine_doc.handlers_register(self.store),
        )

    # Called before the registration each handler raises.
    def test_unregistered(self) -> None:
        line = _line_make("doc.head", 1)
        body: dict[int | str, Any] = {}
        message = i18n("engine_doc.not_registered")
        calls: list[Callable[[], object]] = [
            lambda: engine_doc.doc_put(
                line, db=_DATABASE, id="p", body=body, since=0
            ),
            lambda: engine_doc.doc_head(line, db=_DATABASE, id="prompt"),
        ]
        for call in calls:
            self.raise_check(RuntimeError, message, call)
