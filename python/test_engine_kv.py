# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `kv.get`, `kv.put`, `kv.delete` and `kv.list` through the dispatcher
# on a real store under `build/`: values byte for byte, a blob streamed to the
# cache by the decoder, the replies as the wire carries them, a stale `since`
# and a recorded sequence of forwarded operations replayed to a second store.

import dispatch, engine_kv, hashlib, jslb, os, sqlite3, substrate, tempfile
import unittest, unittest.mock, uuid
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

# The `blob_max` of the settings, 1 GiB.
_BLOB_MAX = 1073741824

# The database the tests keep their values in.
_DATABASE = "_files"

# Every byte value once, the control bytes of a terminal included.
_VALUE_BYTES = bytes(range(256))

# A value over `overflow_bytes`, which the store keeps in the cache.
_VALUE_OVER = bytes(range(256)) * 513

# A map as large as the one of the sync transcript, over `overflow_bytes`.
_MAP_BYTES = bytes(range(256)) * 800

# The text of the script that the recorded sequence writes first.
_SCRIPT_ONE = b"engine.say('How can I help you?');"

# The text of the script that the recorded sequence writes over it.
_SCRIPT_TWO = b"engine.say('Mind the moat.');"

# The key of the script of the recorded sequence.
_SCRIPT_KEY = "/_files/script/bootstrap.js"

# The key of the map of the recorded sequence.
_MAP_KEY = "/_files/maps/castle.bin"

# The recorded operations on `_files`: a key, and its value or `None`.
_RECORDED: list[tuple[str, bytes | None]] = [
    (_SCRIPT_KEY, _SCRIPT_ONE),
    (_MAP_KEY, _MAP_BYTES),
    (_SCRIPT_KEY, _SCRIPT_ONE),
    (_SCRIPT_KEY, _SCRIPT_TWO),
    (_MAP_KEY, None),
    (_MAP_KEY, None),
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

    return jslb.LineDecoder(_LINE_MAX, _BLOB_MAX, _OVERFLOW_BYTES, sink_make)


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


# Tests the handler of `kv.get`.
class TestGet(IsolatedCase):
    # A value in its row is replied with its size, hash and bytes as blob 1.
    def test_value_replied(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put("/_files/a", b"castle_world")
        reply = _reply_get(_line_make("kv.get", 4, "/_files/a"))
        digest = hashlib.sha256(b"castle_world").hexdigest()
        payload = {"size": 12, "sha256": digest}
        self.assertEqual(reply[0], {"t": "kv.get", "r": 4, "b": 1})
        self.assertEqual(reply[1], {"s": 12, "d": b"castle_world"})
        self.assertEqual(jslb.payload_of(reply), payload)

    # A value in the cache is replied as the path of its file, which encodes.
    def test_path_replied(self) -> None:
        engine_kv.handlers_register(self.store)
        self.store.kv_put("/_files/big", _VALUE_OVER)
        reply = _reply_get(_line_make("kv.get", 1, "/_files/big"))
        digest = hashlib.sha256(_VALUE_OVER).hexdigest()
        path = os.path.join(self.root, "cache", digest)
        payload = {"size": len(_VALUE_OVER), "sha256": digest}
        self.assertEqual(reply[1], {"s": len(_VALUE_OVER), "d": path})
        self.assertEqual(jslb.payload_of(reply), payload)
        decoded = _line_decode(self.root, _wire_bytes(reply))
        self.assertEqual(decoded[1]["sha256"], digest)
        self.assertEqual(_blob_read(decoded, 1), _VALUE_OVER)
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
        with self.assertRaises(LookupError):
            dispatch.line_dispatch(_line_make("kv.get", 1, "/_files/none"))
        with self.assertRaises(ValueError):
            dispatch.line_dispatch(_line_make("kv.get", 1))

    # An internal ref or an empty key raises, and so does a closed database.
    def test_ref_invalid(self) -> None:
        engine_kv.handlers_register(self.store)
        for key in ("a", "", "/_files/"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    dispatch.line_dispatch(_line_make("kv.get", 1, key))
        with self.assertRaises(LookupError):
            dispatch.line_dispatch(_line_make("kv.get", 1, "/none/a"))


# Tests the handler of `kv.put`.
class TestPut(IsolatedCase):
    # A put stores blob 1 under the key and replies with its hash and `seq`.
    def test_value_stored(self) -> None:
        engine_kv.handlers_register(self.store)
        reply = _reply_get(_put_line(self.root, "/_files/a", b"one", 1))
        digest = hashlib.sha256(b"one").hexdigest()
        self.assertEqual(reply[0], {"t": "kv.put", "r": 1})
        self.assertEqual(jslb.payload_of(reply), {"sha256": digest, "seq": 2})
        self.assertEqual(self.store.kv_get("/_files/a").data, b"one")
        self.assertEqual(self.store.seq_get(_DATABASE), 2)

    # A line in full names is answered in full names.
    def test_full_names(self) -> None:
        engine_kv.handlers_register(self.store)
        header = jslb.header_make("kv.put", id=1, key="/_files/a", full=True)
        line = jslb.line_make(header, [jslb.blob_make(b"one")], since=1)
        reply = _reply_get(line)
        self.assertEqual(reply[0], {"type": "kv.put", "reply": 1})
        self.assertEqual(reply["seq"], 2)
        self.assertEqual(self.store.kv_get("/_files/a").data, b"one")

    # Every byte value, an empty value and a cached value return as put.
    def test_bytes_identical(self) -> None:
        engine_kv.handlers_register(self.store)
        values = (_VALUE_BYTES, b"", _VALUE_OVER)
        for index, value in enumerate(values):
            key = f"/_files/value{index}"
            put = _reply_get(_put_line(self.root, key, value, index + 1))
            digest = hashlib.sha256(value).hexdigest()
            payload = {"sha256": digest, "seq": index + 2}
            self.assertEqual(jslb.payload_of(put), payload)
            reply = _reply_get(_line_make("kv.get", 2, key))
            self.assertEqual(reply["size"], len(value))
            self.assertEqual(reply["sha256"], digest)
            self.assertEqual(_blob_read(reply, 1), value)
            decoded = _line_decode(self.root, _wire_bytes(reply))
            self.assertEqual(_blob_read(decoded, 1), value)
            self.assertEqual(jslb.payload_of(decoded), jslb.payload_of(reply))

    # A blob over `overflow_bytes` arrives as a file that is moved into place.
    def test_streamed_put(self) -> None:
        engine_kv.handlers_register(self.store)
        line = _put_line(self.root, _MAP_KEY, _MAP_BYTES, 1)
        path = line[1]["d"]
        digest = hashlib.sha256(_MAP_BYTES).hexdigest()
        self.assertIsInstance(path, str)
        self.assertEqual(line[1]["sha256"], digest)
        reply = _reply_get(line)
        self.assertEqual(jslb.payload_of(reply), {"sha256": digest, "seq": 2})
        cache = os.path.join(self.root, "cache")
        self.assertFalse(os.path.exists(path))
        self.assertEqual(os.listdir(cache), [digest])
        self.assertEqual(
            self.store.kv_get(_MAP_KEY).data, os.path.join(cache, digest)
        )
        self.assertEqual(_file_read(os.path.join(cache, digest)), _MAP_BYTES)

    # An identical write is not a change, so the `seq` stays.
    def test_put_unchanged(self) -> None:
        engine_kv.handlers_register(self.store)
        seqs: list[int] = []
        for value, since in ((b"one", 1), (b"one", 2), (b"two", 2)):
            line = _put_line(self.root, "/_files/a", value, since)
            seqs.append(_reply_get(line)["seq"])
        self.assertEqual(seqs, [2, 2, 3])

    # A stale `since` raises the desync and nothing is written.
    def test_since_stale(self) -> None:
        engine_kv.handlers_register(self.store)
        line = _put_line(self.root, "/_files/a", b"one", 5)
        with self.assertRaises(RuntimeError) as caught:
            dispatch.line_dispatch(line)
        message = "kv.put: since 5 is not seq 1 of _files"
        self.assertEqual(str(caught.exception), message)
        with self.assertRaises(LookupError):
            self.store.kv_get("/_files/a")
        self.assertEqual(self.store.seq_get(_DATABASE), 1)

    # The transcript's desync: another writer moved `seq` ahead of `since`.
    def test_writer_ahead(self) -> None:
        engine_kv.handlers_register(self.store)
        _reply_get(_put_line(self.root, _MAP_KEY, _MAP_BYTES, 1))
        _reply_get(_put_line(self.root, "/_files/a", b"one", 2))
        self.store.kv_put("/_files/b", b"two")
        line = _put_line(self.root, "/_files/script/step_tide.js", b"tide", 3)
        with self.assertRaises(RuntimeError) as caught:
            dispatch.line_dispatch(line)
        message = "kv.put: since 3 is not seq 4 of _files"
        self.assertEqual(str(caught.exception), message)
        with self.assertRaises(LookupError):
            self.store.kv_get("/_files/script/step_tide.js")

    # A line with no blob raises, and so does a line with no key.
    def test_line_incomplete(self) -> None:
        engine_kv.handlers_register(self.store)
        with self.assertRaises(KeyError):
            line = _line_make("kv.put", 1, "/_files/a", since=1)
            dispatch.line_dispatch(line)
        with self.assertRaises(ValueError):
            blob = jslb.blob_make(b"one")
            line = _line_make("kv.put", 1, None, [blob], since=1)
            dispatch.line_dispatch(line)
        self.assertEqual(self.store.seq_get(_DATABASE), 1)


# Tests the handler of `kv.delete`.
class TestDelete(IsolatedCase):
    # A delete removes the key and replies with the new `seq`.
    def test_key_deleted(self) -> None:
        engine_kv.handlers_register(self.store)
        _reply_get(_put_line(self.root, "/_files/a", b"one", 1))
        reply = _reply_get(_line_make("kv.delete", 2, "/_files/a", since=2))
        self.assertEqual(reply[0], {"t": "kv.delete", "r": 2})
        self.assertEqual(jslb.payload_of(reply), {"seq": 3})
        with self.assertRaises(LookupError):
            self.store.kv_get("/_files/a")

    # A key that is not there changes nothing, so the `seq` stays.
    def test_key_absent(self) -> None:
        engine_kv.handlers_register(self.store)
        line = _line_make("kv.delete", 1, "/_files/none", since=1)
        self.assertEqual(jslb.payload_of(_reply_get(line)), {"seq": 1})

    # A value in the cache is removed together with its file.
    def test_cache_removed(self) -> None:
        engine_kv.handlers_register(self.store)
        _reply_get(_put_line(self.root, _MAP_KEY, _MAP_BYTES, 1))
        cache = os.path.join(self.root, "cache")
        self.assertEqual(len(os.listdir(cache)), 1)
        _reply_get(_line_make("kv.delete", 2, _MAP_KEY, since=2))
        self.assertEqual(os.listdir(cache), [])

    # A stale `since` raises the desync and the key stays.
    def test_since_stale(self) -> None:
        engine_kv.handlers_register(self.store)
        _reply_get(_put_line(self.root, "/_files/a", b"one", 1))
        line = _line_make("kv.delete", 2, "/_files/a", since=1)
        with self.assertRaises(RuntimeError) as caught:
            dispatch.line_dispatch(line)
        message = "kv.delete: since 1 is not seq 2 of _files"
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(self.store.kv_get("/_files/a").data, b"one")

    # A line with no key raises.
    def test_key_missing(self) -> None:
        engine_kv.handlers_register(self.store)
        with self.assertRaises(ValueError):
            dispatch.line_dispatch(_line_make("kv.delete", 1, since=1))


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
        with self.assertRaises(LookupError):
            dispatch.line_dispatch(line)


# Tests a recorded sequence of forwarded operations on a second store.
class TestReplay(IsolatedCase):
    # The server's store ends as the modifier's store did, `seq` for `seq`.
    def test_recorded_replay(self) -> None:
        second_root = self.root_make()
        second = self.store_make(second_root)
        second.db_create(_DATABASE)
        engine_kv.handlers_register(second)
        seqs: list[int] = []
        for key, value in _RECORDED:
            since = self.store.seq_get(_DATABASE)
            if value is None:
                self.store.kv_delete(key)
                line = _line_make("kv.delete", 1, key, since=since)
            else:
                self.store.kv_put(key, value)
                line = _put_line(second_root, key, value, since)
            reply = _reply_get(line)
            self.assertEqual(reply["seq"], self.store.seq_get(_DATABASE), key)
            seqs.append(reply["seq"])
        self.assertEqual(seqs, [2, 3, 3, 4, 5, 5])
        self.assertEqual(second.kv_get(_SCRIPT_KEY).data, _SCRIPT_TWO)
        _store_close(self.store)
        _store_close(second)
        name = _DATABASE + ".sqlite"
        self.assertEqual(
            _database_dump(os.path.join(self.root, name)),
            _database_dump(os.path.join(second_root, name)),
        )
        self.assertEqual(
            _files_read(os.path.join(self.root, "cache")),
            _files_read(os.path.join(second_root, "cache")),
        )


# Tests the registration.
class TestRegister(IsolatedCase):
    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_kv.handlers_register(self.store)
        with self.assertRaises(ValueError):
            engine_kv.handlers_register(self.store)

    # Called before the registration each handler raises.
    def test_unregistered(self) -> None:
        line = _line_make("kv.get", 1, "/_files/a")
        with self.assertRaises(RuntimeError):
            engine_kv.kv_get(line)
        with self.assertRaises(RuntimeError):
            engine_kv.kv_put(line, since=1)
        with self.assertRaises(RuntimeError):
            engine_kv.kv_delete(line, since=1)
        with self.assertRaises(RuntimeError):
            engine_kv.kv_list(line, db="_files", prefix="")
