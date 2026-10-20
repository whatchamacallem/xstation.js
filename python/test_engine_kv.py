# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `kv.get`, `kv.put`, `kv.delete` and `kv.list` through the dispatcher
# on a real store under `build/`: values byte for byte, a blob streamed to the
# cache by the decoder, the replies as the wire carries them, the sizes,
# hashes and `seq` numbers of known values, a stale `since`, and a recorded
# sequence of forwarded operations replayed to a second store. A new database
# starts at `seq` 0.

import base64, dispatch, engine_kv, hashlib, jslb, os, sqlite3, substrate
import tempfile, unittest, unittest.mock, uuid
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
_STORE_TARGET = "engine_kv._STATE.store"

# The `overflow_bytes` of the settings, 128 KiB.
_OVERFLOW_BYTES = 131072

# The `line_max` of the settings, 1 MiB.
_LINE_MAX = 1048576

# The `blob_max` of the settings, 10 MiB.
_BLOB_MAX = 10485760

# The `message_max` of the settings, 10 MiB.
_MESSAGE_MAX = 10485760

# The database the tests keep their values in.
_DATABASE = "_files"

# Every byte value once, the control bytes of a terminal included.
_VALUE_BYTES = bytes(range(256))

# A value over `overflow_bytes`, which the store keeps in the cache.
_VALUE_OVER = bytes(range(256)) * 513

# The value of a world key: the name of a world database.
_WORLD_VALUE = b"castle_world"

# The `sha256` of the value of the world key, in hex.
_WORLD_SHA256 = (
    "6d0be246127ef7993924a9ce127c6fa6c093dca368163093ab31c80273336ecd"
)

# A small PNG image, as base64 text.
_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAH0lEQVR42mP4"
    "jwQYkAAucYZBqGGQO48oDaPxMCg0AADZV36QzYI8swAAAABJRU5ErkJggg=="
)

# The bytes of the image.
_IMAGE_BYTES = base64.b64decode(_IMAGE_BASE64)

# The `sha256` of the image, in hex.
_IMAGE_SHA256 = (
    "90b3a753ed6b58ea1033aadd244b2b253bd45e9adb25962a52621120768bb8f0"
)

# The ref the image is put under.
_IMAGE_KEY = "/_files/gatehouse/arrival.png"

# A map over `overflow_bytes`.
_MAP_BYTES = bytes(range(256)) * 800

# The `sha256` of the map, in hex.
_MAP_SHA256 = (
    "8c6627e25bfbdef2bba5abc03123ea8e9b60d892f7f180a8b9b5079fb3233c54"
)

# The ref the map is put under.
_MAP_KEY = "/_files/maps/castle.bin"

# A stand in for the script the server seeds into `_files`.
_SCRIPT_ONE = b"engine.say('How can I help you?');"

# A later text of the seeded script, written over it.
_SCRIPT_TWO = b"engine.say('Mind the moat.');"

# The key of the seeded script.
_SCRIPT_KEY = "/_files/script/bootstrap.js"

# A stand in for the script of the put that a desync refuses.
_TIDE_SCRIPT = b"engine.log(1, 'tide advanced by 1');"

# The ref of that script.
_TIDE_KEY = "/_files/script/step_tide.js"

# The English text of the desync message for that put.
_DESYNC_MESSAGE = "kv.put: since 3 is not seq 4 of _files"

# The puts on `_files` replayed: the seed, the image, the map, two rewrites.
_RECORDED: list[tuple[str, bytes]] = [
    (_SCRIPT_KEY, _SCRIPT_ONE),
    (_IMAGE_KEY, _IMAGE_BYTES),
    (_MAP_KEY, _MAP_BYTES),
    (_SCRIPT_KEY, _SCRIPT_ONE),
    (_SCRIPT_KEY, _SCRIPT_TWO),
]


# Builds a request line: the type, the id, the header key, blobs and payload.
def _line_make(
    name: str,
    request_id: int,
    key: str | None = None,
    blobs: list[jslb.Object] | None = None,
    **payload: Any,
) -> jslb.Object:
    header = jslb.header_make(name, id=request_id, key=key)
    return jslb.line_make(header, [] if blobs is None else blobs, **payload)


# Dispatches a line that must be answered and returns the reply.
def _reply_get(line: jslb.Object) -> jslb.Object:
    reply = dispatch.line_dispatch(line)
    if reply is None:
        raise AssertionError("the line was not answered")
    return reply


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# The bytes of a line on the wire: the encoder's pieces, files read in.
def _wire_bytes(line: jslb.Object) -> bytes:
    wire = b""
    for piece in jslb.line_encode(line):
        if isinstance(piece, bytes):
            wire += piece
        else:
            wire += _file_read(piece)
    return wire


# Makes a decoder whose streamed blobs go to new files in the root's cache.
def _decoder_make(root: str) -> jslb.LineDecoder:
    cache = os.path.join(root, "cache")

    # Returns a new path in the cache for a streamed blob.
    def sink_make(header: jslb.Object) -> str:
        return os.path.join(cache, "sink" + uuid.uuid4().hex)

    return jslb.LineDecoder(
        _LINE_MAX, _BLOB_MAX, _MESSAGE_MAX, _OVERFLOW_BYTES, sink_make
    )


# Decodes the one line the bytes hold, streaming a big blob to the cache.
def _line_decode(root: str, wire: bytes) -> jslb.Object:
    (line,) = _decoder_make(root).bytes_feed(wire)
    return line


# Builds a `kv.put` line as the server reads it off the wire.
def _put_line(root: str, key: str, value: bytes, since: int) -> jslb.Object:
    line = _line_make("kv.put", 1, key, [jslb.blob_make(value)], since=since)
    return _line_decode(root, _wire_bytes(line))


# The bytes of a blob, read from its file when it was streamed.
def _blob_read(line: jslb.Object, number: int) -> bytes:
    data: bytes | str = line[number]["d"]
    return _file_read(data) if isinstance(data, str) else data


# The row that `kv.list` replies for a key holding a value.
def _row_make(key: str, value: bytes) -> dict[str, Any]:
    digest = hashlib.sha256(value).hexdigest()
    return {"k": key, "size": len(value), "sha256": digest}


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


# The name and the bytes of every file in a directory, by name.
def _files_read(directory: str) -> list[tuple[str, bytes]]:
    contents: list[tuple[str, bytes]] = []
    for name in sorted(os.listdir(directory)):
        contents.append((name, _file_read(os.path.join(directory, name))))
    return contents


# Gives each test an empty handler table, no registration and a real store.
class IsolatedCase(unittest.TestCase):
    # Patches the table and the state, makes a store with `_files` in it.
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


# Tests the handler of `kv.get`.
class TestGet(IsolatedCase):
    # A value in its row is replied with its size, hash and bytes as blob 1.
    def test_value_replied(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put("/_files/world", _WORLD_VALUE)
        reply = _reply_get(_line_make("kv.get", 4, "/_files/world"))
        payload = {"size": 12, "sha256": _WORLD_SHA256}
        self.assertEqual(reply[0], {"t": "kv.get", "r": 4, "b": 1})
        self.assertEqual(reply[1], {"s": 12, "d": _WORLD_VALUE})
        self.assertEqual(jslb.payload_of(reply), payload)

    # A value in the cache is replied as the path of its file, which encodes.
    def test_path_replied(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put(_MAP_KEY, _MAP_BYTES)
        reply = _reply_get(_line_make("kv.get", 1, _MAP_KEY))
        path = os.path.join(self.root, "cache", _MAP_SHA256)
        payload = {"size": 204800, "sha256": _MAP_SHA256}
        self.assertEqual(reply[1], {"s": 204800, "d": path})
        self.assertEqual(jslb.payload_of(reply), payload)
        decoded = _line_decode(self.root, _wire_bytes(reply))
        self.assertEqual(decoded[1]["sha256"], _MAP_SHA256)
        self.assertEqual(_blob_read(decoded, 1), _MAP_BYTES)
        self.assertEqual(jslb.payload_of(decoded), payload)

    # A line in full names is answered in full names.
    def test_full_names(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put("/_files/a", b"one")
        header = jslb.header_make("kv.get", id=2, key="/_files/a", full=True)
        reply = _reply_get(jslb.line_make(header, []))
        self.assertEqual(reply[0], {"type": "kv.get", "reply": 2, "blobs": 1})
        self.assertEqual(reply[1], {"size": 3, "d": b"one"})
        self.assertEqual(reply["size"], 3)

    # A key that is not there raises, and so does a line with no key.
    def test_key_missing(self) -> None:
        engine_kv.handlers_register(self.store)
        line = _line_make("kv.get", 1, "/_files/none")
        message = i18n("substrate.key_missing", "none", _DATABASE)
        self.dispatch_check(LookupError, message, line)
        message = i18n("engine_kv.key_missing", "kv.get")
        self.dispatch_check(ValueError, message, _line_make("kv.get", 1))

    # An internal ref or an empty key raises, and so does a closed database.
    def test_ref_invalid(self) -> None:
        engine_kv.handlers_register(self.store)
        cases = (
            ("a", i18n("substrate.ref_internal", "a")),
            ("", i18n("substrate.ref_bad", "")),
            ("/_files/", i18n("substrate.ref_bad", "/_files/")),
        )
        for key, message in cases:
            with self.subTest(key=key):
                line = _line_make("kv.get", 1, key)
                self.dispatch_check(ValueError, message, line)
        line = _line_make("kv.get", 1, "/none/a")
        message = i18n("substrate.db_closed", "none")
        self.dispatch_check(LookupError, message, line)


# Tests the handler of `kv.put`.
class TestPut(IsolatedCase):
    # The image put after the seed: its hash and `seq` 2.
    def test_value_stored(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put(_SCRIPT_KEY, _SCRIPT_ONE)
        reply = _reply_get(_put_line(self.root, _IMAGE_KEY, _IMAGE_BYTES, 1))
        payload = {"sha256": _IMAGE_SHA256, "seq": 2}
        self.assertEqual(reply[0], {"t": "kv.put", "r": 1})
        self.assertEqual(jslb.payload_of(reply), payload)
        self.assertEqual(self.store.kv_get(_IMAGE_KEY).data, _IMAGE_BYTES)
        self.assertEqual(self.store.kv_get(_IMAGE_KEY).size, 88)
        self.assertEqual(self.store.seq_get(_DATABASE), 2)

    # A line in full names is answered in full names.
    def test_full_names(self) -> None:
        engine_kv.handlers_register(self.store)
        header = jslb.header_make("kv.put", id=1, key="/_files/a", full=True)
        line = jslb.line_make(header, [jslb.blob_make(b"one")], since=0)
        reply = _reply_get(line)
        self.assertEqual(reply[0], {"type": "kv.put", "reply": 1})
        self.assertEqual(reply["seq"], 1)
        self.assertEqual(self.store.kv_get("/_files/a").data, b"one")

    # Every byte value, an empty value and a cached value return as put.
    def test_bytes_identical(self) -> None:
        engine_kv.handlers_register(self.store)
        values = (_VALUE_BYTES, b"", _VALUE_OVER)
        for index, value in enumerate(values):
            key = f"/_files/value{index}"
            put = _reply_get(_put_line(self.root, key, value, index))
            digest = hashlib.sha256(value).hexdigest()
            payload = {"sha256": digest, "seq": index + 1}
            self.assertEqual(jslb.payload_of(put), payload)
            reply = _reply_get(_line_make("kv.get", 2, key))
            self.assertEqual(reply["size"], len(value))
            self.assertEqual(reply["sha256"], digest)
            self.assertEqual(_blob_read(reply, 1), value)
            decoded = _line_decode(self.root, _wire_bytes(reply))
            self.assertEqual(_blob_read(decoded, 1), value)
            self.assertEqual(jslb.payload_of(decoded), jslb.payload_of(reply))

    # The map arrives streamed and is moved into place.
    def test_streamed_put(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put(_SCRIPT_KEY, _SCRIPT_ONE)
        self.store.kv_put(_IMAGE_KEY, _IMAGE_BYTES)
        line = _put_line(self.root, _MAP_KEY, _MAP_BYTES, 2)
        path = line[1]["d"]
        self.assertIsInstance(path, str)
        self.assertEqual(line[1]["sha256"], _MAP_SHA256)
        reply = _reply_get(line)
        payload = {"sha256": _MAP_SHA256, "seq": 3}
        self.assertEqual(jslb.payload_of(reply), payload)
        cache = os.path.join(self.root, "cache")
        stored = os.path.join(cache, _MAP_SHA256)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(os.listdir(cache), [_MAP_SHA256])
        self.assertEqual(self.store.kv_get(_MAP_KEY).data, stored)
        self.assertEqual(_file_read(stored), _MAP_BYTES)

    # An identical write is not a change, so the `seq` stays.
    def test_put_unchanged(self) -> None:
        engine_kv.handlers_register(self.store)
        seqs: list[int] = []
        for value, since in ((b"one", 0), (b"one", 1), (b"two", 1)):
            line = _put_line(self.root, "/_files/a", value, since)
            seqs.append(_reply_get(line)["seq"])
        self.assertEqual(seqs, [1, 1, 2])

    # A stale `since` raises the desync and nothing is written.
    def test_since_stale(self) -> None:
        engine_kv.handlers_register(self.store)
        line = _put_line(self.root, "/_files/a", b"one", 5)
        message = i18n("substrate.since_stale", "kv.put", 5, 0, _DATABASE)
        self.dispatch_check(RuntimeError, message, line)
        missing = i18n("substrate.key_missing", "a", _DATABASE)
        self.raise_check(
            LookupError, missing, lambda: self.store.kv_get("/_files/a")
        )
        self.assertEqual(self.store.seq_get(_DATABASE), 0)

    # A desync: another writer moved `seq` past `since`.
    def test_writer_ahead(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put(_SCRIPT_KEY, _SCRIPT_ONE)
        self.store.kv_put(_IMAGE_KEY, _IMAGE_BYTES)
        _reply_get(_put_line(self.root, _MAP_KEY, _MAP_BYTES, 2))
        self.store.kv_put(_SCRIPT_KEY, _SCRIPT_TWO)
        line = _put_line(self.root, _TIDE_KEY, _TIDE_SCRIPT, 3)
        message = i18n("substrate.since_stale", "kv.put", 3, 4, _DATABASE)
        self.assertEqual(message, _DESYNC_MESSAGE)
        self.dispatch_check(RuntimeError, _DESYNC_MESSAGE, line)
        key = "script/step_tide.js"
        missing = i18n("substrate.key_missing", key, _DATABASE)
        self.raise_check(
            LookupError, missing, lambda: self.store.kv_get(_TIDE_KEY)
        )
        self.assertEqual(self.store.seq_get(_DATABASE), 4)

    # A line with no blob raises, and so does a line with no key.
    def test_line_incomplete(self) -> None:
        engine_kv.handlers_register(self.store)
        line = _line_make("kv.put", 1, "/_files/a", since=0)
        message = i18n("engine_kv.blob_missing", "kv.put")
        self.dispatch_check(ValueError, message, line)
        blob = jslb.blob_make(b"one")
        line = _line_make("kv.put", 1, None, [blob], since=0)
        message = i18n("engine_kv.key_missing", "kv.put")
        self.dispatch_check(ValueError, message, line)
        self.assertEqual(self.store.seq_get(_DATABASE), 0)


# Tests the handler of `kv.delete`.
class TestDelete(IsolatedCase):
    # A delete removes the key and replies with the new `seq`.
    def test_key_deleted(self) -> None:
        engine_kv.handlers_register(self.store)
        _reply_get(_put_line(self.root, "/_files/a", b"one", 0))
        reply = _reply_get(_line_make("kv.delete", 2, "/_files/a", since=1))
        self.assertEqual(reply[0], {"t": "kv.delete", "r": 2})
        self.assertEqual(jslb.payload_of(reply), {"seq": 2})
        missing = i18n("substrate.key_missing", "a", _DATABASE)
        self.raise_check(
            LookupError, missing, lambda: self.store.kv_get("/_files/a")
        )

    # A key that is not there changes nothing, so the `seq` stays.
    def test_key_absent(self) -> None:
        engine_kv.handlers_register(self.store)
        line = _line_make("kv.delete", 1, "/_files/none", since=0)
        self.assertEqual(jslb.payload_of(_reply_get(line)), {"seq": 0})

    # A value in the cache is removed together with its file.
    def test_cache_removed(self) -> None:
        engine_kv.handlers_register(self.store)
        _reply_get(_put_line(self.root, _MAP_KEY, _MAP_BYTES, 0))
        cache = os.path.join(self.root, "cache")
        self.assertEqual(os.listdir(cache), [_MAP_SHA256])
        _reply_get(_line_make("kv.delete", 2, _MAP_KEY, since=1))
        self.assertEqual(os.listdir(cache), [])

    # A stale `since` raises the desync and the key stays.
    def test_since_stale(self) -> None:
        engine_kv.handlers_register(self.store)
        _reply_get(_put_line(self.root, "/_files/a", b"one", 0))
        line = _line_make("kv.delete", 2, "/_files/a", since=0)
        message = i18n("substrate.since_stale", "kv.delete", 0, 1, _DATABASE)
        self.dispatch_check(RuntimeError, message, line)
        self.assertEqual(self.store.kv_get("/_files/a").data, b"one")

    # A line with no key raises.
    def test_key_missing(self) -> None:
        engine_kv.handlers_register(self.store)
        message = i18n("engine_kv.key_missing", "kv.delete")
        line = _line_make("kv.delete", 1, since=0)
        self.dispatch_check(ValueError, message, line)


# Tests the handler of `kv.list`.
class TestList(IsolatedCase):
    # The keys with the prefix are replied in key order with size and hash.
    def test_keys_listed(self) -> None:
        engine_kv.handlers_register(self.store)
        values = {
            "script/b.js": b"b",
            "script/a.js": b"aa",
            "maps/c.bin": _VALUE_OVER,
        }
        for key, value in values.items():
            self.store.kv_put("/_files/" + key, value)
        line = _line_make("kv.list", 3, db="_files", prefix="script/")
        reply = _reply_get(line)
        expected = [
            _row_make("script/a.js", b"aa"),
            _row_make("script/b.js", b"b"),
        ]
        self.assertEqual(reply[0], {"t": "kv.list", "r": 3})
        self.assertEqual(jslb.payload_of(reply), {"keys": expected})
        decoded = _line_decode(self.root, _wire_bytes(reply))
        self.assertEqual(jslb.payload_of(decoded), {"keys": expected})

    # An empty prefix lists every key, and a prefix nothing has lists none.
    def test_prefix_edges(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put("/_files/maps/c.bin", _VALUE_OVER)
        self.store.kv_put("/_files/script/a.js", b"aa")
        line = _line_make("kv.list", 1, db="_files", prefix="")
        keys = _reply_get(line)["keys"]
        self.assertEqual(
            [row["k"] for row in keys], ["maps/c.bin", "script/a.js"]
        )
        line = _line_make("kv.list", 2, db="_files", prefix="none")
        self.assertEqual(_reply_get(line)["keys"], [])

    # A database that is not open raises.
    def test_database_closed(self) -> None:
        engine_kv.handlers_register(self.store)
        line = _line_make("kv.list", 1, db="none", prefix="")
        message = i18n("substrate.db_closed", "none")
        self.dispatch_check(LookupError, message, line)


# Tests a recorded sequence of forwarded operations on a second store.
class TestReplay(IsolatedCase):
    # Runs one operation on the first store, forwards it, returns the reply.
    def operation_forward(
        self, second_root: str, key: str, value: bytes | None
    ) -> dict[str, Any]:
        since = self.store.seq_get(_DATABASE)
        if value is None:
            self.store.kv_delete(key)
            line = _line_make("kv.delete", 1, key, since=since)
        else:
            self.store.kv_put(key, value)
            line = _put_line(second_root, key, value, since)
        payload = jslb.payload_of(_reply_get(line))
        self.assertEqual(payload["seq"], self.store.seq_get(_DATABASE), key)
        return payload

    # The second store ends as the first did, `seq` for `seq`, file for file.
    def test_recorded_replay(self) -> None:
        second_root = self.root_make()
        second = self.store_make(second_root)
        second.db_create(_DATABASE)
        engine_kv.handlers_register(second)
        replies = [
            self.operation_forward(second_root, key, value)
            for key, value in _RECORDED
        ]
        seqs = [reply["seq"] for reply in replies]
        self.assertEqual(seqs, [1, 2, 3, 3, 4])
        self.assertEqual(replies[1]["sha256"], _IMAGE_SHA256)
        self.assertEqual(replies[2]["sha256"], _MAP_SHA256)
        cache = os.path.join(self.root, "cache")
        second_cache = os.path.join(second_root, "cache")
        self.assertEqual(os.listdir(second_cache), [_MAP_SHA256])
        self.assertEqual(_files_read(cache), _files_read(second_cache))
        deletes = [
            self.operation_forward(second_root, _MAP_KEY, None)
            for _ in range(2)
        ]
        self.assertEqual(deletes, [{"seq": 5}, {"seq": 5}])
        self.assertEqual(os.listdir(second_cache), [])
        self.assertEqual(second.kv_get(_SCRIPT_KEY).data, _SCRIPT_TWO)
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
        engine_kv.handlers_register(self.store)
        message = i18n("dispatch.handler_twice", "kv.get", 0)
        self.raise_check(
            ValueError,
            message,
            lambda: engine_kv.handlers_register(self.store),
        )

    # Called before the registration each handler raises.
    def test_unregistered(self) -> None:
        line = _line_make("kv.get", 1, "/_files/a")
        message = i18n("engine_kv.not_registered")
        calls: list[Callable[[], object]] = [
            lambda: engine_kv.kv_get(line),
            lambda: engine_kv.kv_put(line, since=0),
            lambda: engine_kv.kv_delete(line, since=0),
            lambda: engine_kv.kv_list(line, db=_DATABASE, prefix=""),
        ]
        for call in calls:
            self.raise_check(RuntimeError, message, call)
