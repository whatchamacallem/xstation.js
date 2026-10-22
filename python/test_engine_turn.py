# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `turn.append` and `turn.compact` through the dispatcher on a real
# store under `build/`: turns numbered within their scene, the `n` and `seq`
# of the first turn after the seed of `metaverse`, messages read off the
# wire and stored as canonical JSON, compaction into a summary turn, a stale
# `since`, what the store refuses, and a recorded sequence replayed to a
# second store. A new database starts at `seq` 0.

import dispatch, engine_turn, jslb, json, os, sqlite3, substrate, tempfile
import unittest, unittest.mock
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
_STORE_TARGET = "engine_turn._STATE.store"

# The `overflow_bytes` of the settings, 128 KiB.
_OVERFLOW_BYTES = 131072

# The `line_max` of the settings, 1 MiB.
_LINE_MAX = 1048576

# The `blob_max` of the settings, the largest database.
_BLOB_MAX = 2147483391

# The database the tests keep their turns in.
_DATABASE = "metaverse"

# The hyperposition scene, whose conversation the tests append to.
_SCENE = "/metaverse/hyperposition/1"

# Another scene of the same database, with a conversation of its own.
_OTHER_SCENE = "/metaverse/castle/arrival/1"

# The hyperposition document the server seeds, in its stored form.
_HYPERPOSITION_BODY: dict[int | str, Any] = {
    0: {"t": "scene"},
    "subtitle": "How can I help you?",
}

# A stand in for the analyst's prompt document the server seeds.
_PROMPT_BODY: dict[int | str, Any] = {
    0: {"t": "prompt"},
    "text": "You are the analyst.",
}

# The keys the server seeds into `metaverse`, and their values.
_SEED_KEYS: list[tuple[str, bytes]] = [
    ("/metaverse/player", b"player"),
    ("/metaverse/world", b"metaverse"),
    ("/metaverse/scene", b"/metaverse/hyperposition/1"),
]

# The `seq` of `metaverse` after its seed, the first `since` of the turns.
_SEED_SEQ = 5

# Text beyond ASCII, built from its code points.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)

# The summary text that the tests compact turns into.
_SUMMARY = "The player answered 1."

# The arguments of a `script_run` call that builds a universe, as JSON text.
_SCRIPT_ARGUMENTS = (
    '{"name":"bootstrap","args":{"universe":"castle","title":"The castle",'
    '"world":"castle_world","region":"castle_gatehouse"}}'
)

# The player's first message.
_USER_TURN: dict[str, Any] = {"role": "user", "content": "1"}

# The assistant's turn that calls `script_run`, whose content is null.
_CALL_TURN: dict[str, Any] = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "browser.script_run",
                "arguments": _SCRIPT_ARGUMENTS,
            },
        }
    ],
}

# The assistant's answer to the player.
_ANSWER_TURN: dict[str, Any] = {
    "role": "assistant",
    "content": "Mind the moat.",
}

# The player's next message, which follows the compaction.
_NEXT_TURN: dict[str, Any] = {"role": "user", "content": "2"}

# The turns that the tests append in order, each a role and a message.
_TURNS: list[tuple[str, dict[str, Any]]] = [
    ("user", _USER_TURN),
    ("assistant", _CALL_TURN),
    ("assistant", _ANSWER_TURN),
]

# The operations to replay, each a type and a payload.
_RECORDED: list[tuple[str, dict[str, Any]]] = [
    ("turn.append", {"scene": _SCENE, "role": "user", "content": _USER_TURN}),
    (
        "turn.append",
        {"scene": _SCENE, "role": "assistant", "content": _CALL_TURN},
    ),
    (
        "turn.append",
        {"scene": _SCENE, "role": "assistant", "content": _ANSWER_TURN},
    ),
    (
        "turn.compact",
        {"scene": _SCENE, "through": 2, "summary": _SUMMARY},
    ),
    ("turn.append", {"scene": _SCENE, "role": "user", "content": _NEXT_TURN}),
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


# Builds a forwarded line as the server reads it off the wire.
def _forward_line(
    kind: str, payload: dict[str, Any], since: int
) -> jslb.Object:
    line = _line_make(kind, 1, since=since, **payload)
    return _line_decode(_wire_bytes(line))


# Builds a forwarded `turn.append` line of a turn of the hyperposition.
def _append_line(
    role: str, content: dict[str, Any], since: int
) -> jslb.Object:
    payload = {"scene": _SCENE, "role": role, "content": content}
    return _forward_line("turn.append", payload, since)


# Builds a forwarded `turn.append` of the first message, `since` 0, to a scene.
def _scene_line(scene: str) -> jslb.Object:
    payload = {"scene": scene, "role": "user", "content": _USER_TURN}
    return _forward_line("turn.append", payload, 0)


# The canonical JSON text of a value, as the substrate stores it.
def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# The row a turn is stored as, with its content in canonical JSON.
def _row_make(n: int, role: str, content: dict[str, Any]) -> substrate.TurnRow:
    return substrate.TurnRow(_SCENE, n, role, _json_text(content))


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

    # Writes the seed of a new `metaverse` straight to a store, five changes.
    def seed_write(self, store: substrate.Store) -> None:
        store.doc_put(_DATABASE, "hyperposition", _HYPERPOSITION_BODY)
        store.doc_put(_DATABASE, "prompt", _PROMPT_BODY)
        for key, value in _SEED_KEYS:
            store.kv_put(key, value)
        self.assertEqual(store.seq_get(_DATABASE), _SEED_SEQ)

    # Appends the turns through the handler from `seq` 0, ending at `seq` 3.
    def turns_append(self) -> None:
        for index, (role, content) in enumerate(_TURNS):
            _reply_get(_append_line(role, content, index))

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


# Tests the handler of `turn.append`.
class TestAppend(IsolatedCase):
    # The first turn after the seed gets `n` 1 and the next `seq`, 6.
    def test_turn_appended(self) -> None:
        engine_turn.handlers_register(self.store)
        self.seed_write(self.store)
        reply = _reply_get(_append_line("user", _USER_TURN, _SEED_SEQ))
        self.assertEqual(reply[0], {"t": "turn.append", "r": 1})
        self.assertEqual(jslb.payload_of(reply), {"n": 1, "seq": 6})
        rows = self.store.turn_list(_SCENE)
        self.assertEqual(rows, [_row_make(1, "user", _USER_TURN)])
        self.assertEqual(self.store.seq_get(_DATABASE), 6)

    # Turns count up, and a message with null and a list is stored whole.
    def test_turns_numbered(self) -> None:
        engine_turn.handlers_register(self.store)
        self.seed_write(self.store)
        replies = [
            jslb.payload_of(_reply_get(_append_line(role, content, since)))
            for since, (role, content) in enumerate(_TURNS, _SEED_SEQ)
        ]
        expected = [
            {"n": 1, "seq": 6},
            {"n": 2, "seq": 7},
            {"n": 3, "seq": 8},
        ]
        self.assertEqual(replies, expected)
        rows = self.store.turn_list(_SCENE)
        made = [
            _row_make(index, role, content)
            for index, (role, content) in enumerate(_TURNS, 1)
        ]
        self.assertEqual(rows, made)
        self.assertEqual(json.loads(rows[1].content), _CALL_TURN)

    # Each scene counts its own turns.
    def test_scenes_apart(self) -> None:
        engine_turn.handlers_register(self.store)
        scenes = (_SCENE, _OTHER_SCENE, _SCENE, _OTHER_SCENE, _OTHER_SCENE)
        counts: list[int] = []
        for index, scene in enumerate(scenes):
            payload = {"scene": scene, "role": "user", "content": _USER_TURN}
            line = _forward_line("turn.append", payload, index)
            counts.append(_reply_get(line)["n"])
        self.assertEqual(counts, [1, 1, 2, 2, 3])

    # Text beyond ASCII is stored as raw characters, not as escapes.
    def test_text_wide(self) -> None:
        engine_turn.handlers_register(self.store)
        content = {"role": "user", "content": _WIDE_TEXT}
        _reply_get(_append_line("user", content, 0))
        stored = self.store.turn_list(_SCENE)[0].content
        self.assertEqual(stored, _json_text(content))
        self.assertIn(_WIDE_TEXT, stored)

    # A stale `since` raises the desync and no turn is added.
    def test_since_stale(self) -> None:
        engine_turn.handlers_register(self.store)
        self.seed_write(self.store)
        line = _append_line("user", _USER_TURN, 4)
        message = i18n("substrate.since_stale", "turn.append", 4, 5, _DATABASE)
        self.dispatch_check(RuntimeError, message, line)
        self.assertEqual(self.store.turn_list(_SCENE), [])
        self.assertEqual(self.store.seq_get(_DATABASE), _SEED_SEQ)

    # A scene not an external document ref raises, as does a closed database.
    def test_scene_invalid(self) -> None:
        engine_turn.handlers_register(self.store)
        for scene in ("hyperposition/1", "/metaverse/hyperposition"):
            with self.subTest(scene=scene):
                line = _scene_line(scene)
                message = i18n("substrate.scene_bad", scene)
                self.dispatch_check(ValueError, message, line)
        line = _scene_line("/none/scene/1")
        message = i18n("substrate.db_closed", "none")
        self.dispatch_check(LookupError, message, line)
        self.assertEqual(self.store.seq_get(_DATABASE), 0)


# Tests the handler of `turn.compact`.
class TestCompact(IsolatedCase):
    # Turns 1 to `through` become one summary turn at `n` 1.
    def test_turns_compacted(self) -> None:
        engine_turn.handlers_register(self.store)
        self.turns_append()
        payload = {"scene": _SCENE, "through": 2, "summary": _SUMMARY}
        reply = _reply_get(_forward_line("turn.compact", payload, 3))
        self.assertEqual(reply[0], {"t": "turn.compact", "r": 1})
        self.assertEqual(jslb.payload_of(reply), {"seq": 4})
        summary = {"role": "system", "content": _SUMMARY}
        self.assertEqual(
            self.store.turn_list(_SCENE),
            [
                _row_make(1, "system", summary),
                _row_make(3, "assistant", _ANSWER_TURN),
            ],
        )

    # The turn after a compaction is numbered after the last that is left.
    def test_append_after(self) -> None:
        engine_turn.handlers_register(self.store)
        self.turns_append()
        payload = {"scene": _SCENE, "through": 2, "summary": _SUMMARY}
        _reply_get(_forward_line("turn.compact", payload, 3))
        reply = _reply_get(_append_line("user", _NEXT_TURN, 4))
        self.assertEqual(jslb.payload_of(reply), {"n": 4, "seq": 5})

    # A stale `since` raises the desync and the turns stay.
    def test_since_stale(self) -> None:
        engine_turn.handlers_register(self.store)
        self.turns_append()
        payload = {"scene": _SCENE, "through": 2, "summary": _SUMMARY}
        line = _forward_line("turn.compact", payload, 1)
        kind = "turn.compact"
        message = i18n("substrate.since_stale", kind, 1, 3, _DATABASE)
        self.dispatch_check(RuntimeError, message, line)
        self.assertEqual(len(self.store.turn_list(_SCENE)), 3)
        self.assertEqual(self.store.seq_get(_DATABASE), 3)

    # A `through` below 1 raises, and so does a scene with no turn to replace.
    def test_compact_refused(self) -> None:
        engine_turn.handlers_register(self.store)
        payload = {"scene": _SCENE, "through": 0, "summary": _SUMMARY}
        line = _forward_line("turn.compact", payload, 0)
        message = i18n("substrate.through_bad", 0)
        self.dispatch_check(ValueError, message, line)
        payload = {"scene": _SCENE, "through": 1, "summary": _SUMMARY}
        line = _forward_line("turn.compact", payload, 0)
        message = i18n("substrate.turns_none", _SCENE, 1)
        self.dispatch_check(LookupError, message, line)
        self.assertEqual(self.store.turn_list(_SCENE), [])
        self.assertEqual(self.store.seq_get(_DATABASE), 0)


# Tests a recorded sequence of forwarded operations on a second store.
class TestReplay(IsolatedCase):
    # Runs one operation on the first store, forwards it, returns the reply.
    def operation_forward(
        self, kind: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        since = self.store.seq_get(_DATABASE)
        scene: str = payload["scene"]
        if kind == "turn.append":
            text = _json_text(payload["content"])
            n, seq = self.store.turn_append(scene, payload["role"], text)
            expected: dict[str, Any] = {"n": n, "seq": seq}
        else:
            seq = self.store.turn_compact(
                scene, payload["through"], payload["summary"]
            )
            expected = {"seq": seq}
        line = _forward_line(kind, payload, since)
        reply = jslb.payload_of(_reply_get(line))
        self.assertEqual(reply, expected, kind)
        return reply

    # The second store ends as the first did, `seq` for `seq`.
    def test_recorded_replay(self) -> None:
        second_root = self.root_make()
        second = self.store_make(second_root)
        second.db_create(_DATABASE)
        self.seed_write(self.store)
        self.seed_write(second)
        engine_turn.handlers_register(second)
        replies = [
            self.operation_forward(kind, payload)
            for kind, payload in _RECORDED
        ]
        expected = [
            {"n": 1, "seq": 6},
            {"n": 2, "seq": 7},
            {"n": 3, "seq": 8},
            {"seq": 9},
            {"n": 4, "seq": 10},
        ]
        self.assertEqual(replies, expected)
        rows = second.turn_list(_SCENE)
        self.assertEqual(rows, self.store.turn_list(_SCENE))
        self.assertEqual([row.n for row in rows], [1, 3, 4])
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
        engine_turn.handlers_register(self.store)
        message = i18n("dispatch.handler_twice", "turn.append", 0)
        self.raise_check(
            ValueError,
            message,
            lambda: engine_turn.handlers_register(self.store),
        )

    # Called before the registration each handler raises.
    def test_called_early(self) -> None:
        line = _line_make("turn.append", 1)
        content: dict[str, object] = {}
        message = i18n("engine_turn.not_registered")
        calls: list[Callable[[], object]] = [
            lambda: engine_turn.turn_append(
                line, scene=_SCENE, role="user", content=content, since=0
            ),
            lambda: engine_turn.turn_compact(
                line, scene=_SCENE, through=1, summary="x", since=0
            ),
        ]
        for call in calls:
            self.raise_check(RuntimeError, message, call)
