# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `db.create`, `db.drop` and `db.snapshot` through the dispatcher on a
# real store under `build/`: databases made and dropped by forwarded lines, a
# stale `since`, the file of a snapshot as blob 1 in memory and streamed to
# the cache, a snapshot restored into a second store, and a recorded sequence
# of creates and drops replayed to a second store.

import dispatch, engine_db, hashlib, jslb, os, sqlite3, substrate, tempfile
import unittest, unittest.mock, uuid
from typing import Any

# The checkout's build directory, where each test makes its scratch roots.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The dotted name of the handler table that the tests patch.
_HANDLERS_TARGET = "dispatch._HANDLERS"

# The dotted name of the store that the tests patch.
_STORE_TARGET = "engine_db._STATE.store"

# The `overflow_bytes` of the settings, 128 KiB.
_OVERFLOW_BYTES = 131072

# The `line_max` of the settings, 1 MiB.
_LINE_MAX = 1048576

# The `blob_max` of the settings, 1 GiB.
_BLOB_MAX = 1073741824

# The database the tests create, snapshot and drop.
_DATABASE = "castle"

# Text beyond ASCII, built from its code points.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)

# A text row large enough to put the database file over `overflow_bytes`.
_BIG_TEXT = "x" * 200000

# The magic bytes that start every SQLite database file.
_FILE_MAGIC = b"SQLite format 3\x00"

# The recorded operations: a type and a database name, as the transcript has.
_RECORDED: list[tuple[str, str]] = [
    ("db.create", "metaverse"),
    ("db.create", "castle"),
    ("db.create", "castle_world"),
    ("db.create", "castle_gatehouse"),
    ("db.drop", "castle_gatehouse"),
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


# The bytes of a blob, read from its file when it was streamed.
def _blob_read(line: jslb.Object, number: int) -> bytes:
    data: bytes | str = line[number]["d"]
    return _file_read(data) if isinstance(data, str) else data


# The names of the database files in a root, in order.
def _files_find(root: str) -> list[str]:
    names = os.listdir(root)
    return sorted(name for name in names if name.endswith(".sqlite"))


# One SQL statement with its parameters.
def _statement_make(sql: str, *params: Any) -> substrate.SqlStatement:
    return substrate.SqlStatement(sql, list(params))


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
    # Patches the table and the state, makes a store with no database.
    def setUp(self) -> None:
        table = unittest.mock.patch.dict(_HANDLERS_TARGET, {}, clear=True)
        state = unittest.mock.patch(_STORE_TARGET, None)
        for patcher in (table, state):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.root = self.root_make()
        self.store = self.store_make(self.root)

    # Makes a scratch root under `build/`, removed when the test ends.
    def root_make(self) -> str:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        return self.enterContext(tempfile.TemporaryDirectory(dir=_BUILD_PATH))

    # Makes a store on a root, closing its databases when the test ends.
    def store_make(self, root: str) -> substrate.Store:
        store = substrate.Store(root, _OVERFLOW_BYTES)
        self.addCleanup(_store_close, store)
        return store


# Tests the handler of `db.create`.
class TestCreate(IsolatedCase):
    # A create makes the database file with `seq` 1 and replies with nothing.
    def test_database_created(self) -> None:
        engine_db.handlers_register(self.store)
        line = _line_make("db.create", 3, db=_DATABASE, since=0)
        reply = _reply_get(line)
        self.assertEqual(reply[0], {"t": "db.create", "r": 3})
        self.assertEqual(jslb.payload_of(reply), {})
        self.assertEqual(self.store.db_list(), [_DATABASE])
        self.assertEqual(self.store.seq_get(_DATABASE), 1)
        path = os.path.join(self.root, "castle.sqlite")
        self.assertTrue(os.path.isfile(path))

    # A stale `since` raises the desync and nothing is created.
    def test_since_stale(self) -> None:
        engine_db.handlers_register(self.store)
        line = _line_make("db.create", 1, db=_DATABASE, since=1)
        with self.assertRaises(RuntimeError) as caught:
            dispatch.line_dispatch(line)
        message = "db.create: since 1 is not seq 0 of castle"
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(self.store.db_list(), [])
        self.assertEqual(os.listdir(self.root), ["cache"])

    # A database that exists raises, and so does a name that is not valid.
    def test_create_refused(self) -> None:
        engine_db.handlers_register(self.store)
        self.store.db_create(_DATABASE)
        line = _line_make("db.create", 1, db=_DATABASE, since=0)
        with self.assertRaises(FileExistsError):
            dispatch.line_dispatch(line)
        self.assertEqual(self.store.seq_get(_DATABASE), 1)
        for name in ("", "a-b", "9a", "a/b"):
            with self.subTest(name=name):
                line = _line_make("db.create", 1, db=name, since=0)
                with self.assertRaises(ValueError):
                    dispatch.line_dispatch(line)
        self.assertEqual(self.store.db_list(), [_DATABASE])
        self.assertEqual(_files_find(self.root), ["castle.sqlite"])


# Tests the handler of `db.drop`.
class TestDrop(IsolatedCase):
    # A drop closes and deletes the database and its cache files.
    def test_database_dropped(self) -> None:
        engine_db.handlers_register(self.store)
        self.store.db_create(_DATABASE)
        self.store.kv_put("/castle/maps/castle.bin", bytes(range(256)) * 800)
        cache = os.path.join(self.root, "cache")
        self.assertEqual(len(os.listdir(cache)), 1)
        line = _line_make("db.drop", 4, db=_DATABASE, since=2)
        reply = _reply_get(line)
        self.assertEqual(reply[0], {"t": "db.drop", "r": 4})
        self.assertEqual(jslb.payload_of(reply), {})
        self.assertEqual(self.store.db_list(), [])
        self.assertEqual(_files_find(self.root), [])
        self.assertEqual(os.listdir(cache), [])

    # A stale `since` raises the desync and the database stays.
    def test_since_stale(self) -> None:
        engine_db.handlers_register(self.store)
        self.store.db_create(_DATABASE)
        line = _line_make("db.drop", 1, db=_DATABASE, since=0)
        with self.assertRaises(RuntimeError) as caught:
            dispatch.line_dispatch(line)
        message = "db.drop: since 0 is not seq 1 of castle"
        self.assertEqual(str(caught.exception), message)
        self.assertEqual(self.store.db_list(), [_DATABASE])
        self.assertEqual(_files_find(self.root), ["castle.sqlite"])

    # A database that is not open raises.
    def test_drop_unknown(self) -> None:
        engine_db.handlers_register(self.store)
        line = _line_make("db.drop", 1, db=_DATABASE, since=0)
        with self.assertRaises(LookupError):
            dispatch.line_dispatch(line)


# Tests the handler of `db.snapshot`.
class TestSnapshot(IsolatedCase):
    # Makes the database with a table and one row of the text.
    def database_fill(self, text: str) -> None:
        self.store.db_create(_DATABASE)
        statements = [
            _statement_make("CREATE TABLE t (x TEXT) STRICT"),
            _statement_make("INSERT INTO t VALUES (?)", text),
        ]
        self.store.sql_run(_DATABASE, statements)

    # Restores the snapshot into a second store and reads back the row.
    def row_restored(self, data: bytes) -> list[list[Any]]:
        second = self.store_make(self.root_make())
        self.assertEqual(second.db_restore(_DATABASE, data), 2)
        statement = _statement_make("SELECT x FROM t")
        return second.sql_run(_DATABASE, [statement])[0].rows

    # The reply holds the hash and `seq`, and the file of the database.
    def test_file_replied(self) -> None:
        engine_db.handlers_register(self.store)
        self.database_fill(_WIDE_TEXT)
        reply = _reply_get(_line_make("db.snapshot", 9, db=_DATABASE))
        data = reply[1]["d"]
        payload = {"sha256": hashlib.sha256(data).hexdigest(), "seq": 2}
        self.assertEqual(reply[0], {"t": "db.snapshot", "r": 9, "b": 1})
        self.assertEqual(reply[1], {"s": len(data), "d": data})
        self.assertEqual(jslb.payload_of(reply), payload)
        self.assertEqual(data[:16], _FILE_MAGIC)
        self.assertLessEqual(len(data), _OVERFLOW_BYTES)
        decoded = _line_decode(self.root, _wire_bytes(reply))
        self.assertEqual(_blob_read(decoded, 1), data)
        self.assertEqual(jslb.payload_of(decoded), payload)
        self.assertEqual(self.row_restored(data), [[_WIDE_TEXT]])

    # A file over `overflow_bytes` is streamed and its hash is the reply's.
    def test_file_streamed(self) -> None:
        engine_db.handlers_register(self.store)
        self.database_fill(_BIG_TEXT)
        reply = _reply_get(_line_make("db.snapshot", 1, db=_DATABASE))
        data = reply[1]["d"]
        digest = hashlib.sha256(data).hexdigest()
        self.assertGreater(len(data), _OVERFLOW_BYTES)
        self.assertEqual(reply["sha256"], digest)
        decoded = _line_decode(self.root, _wire_bytes(reply))
        self.assertEqual(decoded[1]["sha256"], digest)
        self.assertEqual(_blob_read(decoded, 1), data)
        self.assertEqual(self.row_restored(data), [[_BIG_TEXT]])

    # The `seq` of the reply is the `seq` of the database at that moment.
    def test_seq_replied(self) -> None:
        engine_db.handlers_register(self.store)
        self.store.db_create(_DATABASE)
        line = _line_make("db.snapshot", 1, db=_DATABASE)
        self.assertEqual(_reply_get(line)["seq"], 1)
        self.store.kv_put("/castle/a", b"one")
        line = _line_make("db.snapshot", 2, db=_DATABASE)
        self.assertEqual(_reply_get(line)["seq"], 2)

    # A database that is not open raises.
    def test_snapshot_unknown(self) -> None:
        engine_db.handlers_register(self.store)
        line = _line_make("db.snapshot", 1, db=_DATABASE)
        with self.assertRaises(LookupError):
            dispatch.line_dispatch(line)


# Tests a recorded sequence of forwarded operations on a second store.
class TestReplay(IsolatedCase):
    # The server's store ends as the modifier's store did, file for file.
    def test_recorded_replay(self) -> None:
        second_root = self.root_make()
        second = self.store_make(second_root)
        engine_db.handlers_register(second)
        for kind, name in _RECORDED:
            if kind == "db.create":
                since = 0
                self.store.db_create(name)
            else:
                since = self.store.seq_get(name)
                self.store.db_drop(name)
            line = _line_make(kind, 1, db=name, since=since)
            self.assertEqual(jslb.payload_of(_reply_get(line)), {}, name)
        names = ["castle", "castle_world", "metaverse"]
        self.assertEqual(self.store.db_list(), names)
        self.assertEqual(second.db_list(), names)
        for name in names:
            self.assertEqual(second.seq_get(name), 1)
        _store_close(self.store)
        _store_close(second)
        for name in names:
            file_name = name + ".sqlite"
            self.assertEqual(
                _database_dump(os.path.join(self.root, file_name)),
                _database_dump(os.path.join(second_root, file_name)),
                name,
            )
        self.assertEqual(
            sorted(os.listdir(self.root)), sorted(os.listdir(second_root))
        )


# Tests the registration.
class TestRegister(IsolatedCase):
    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_db.handlers_register(self.store)
        with self.assertRaises(ValueError):
            engine_db.handlers_register(self.store)

    # Called before the registration each handler raises.
    def test_unregistered(self) -> None:
        line = _line_make("db.create", 1)
        with self.assertRaises(RuntimeError):
            engine_db.db_create(line, db=_DATABASE, since=0)
        with self.assertRaises(RuntimeError):
            engine_db.db_drop(line, db=_DATABASE, since=1)
        with self.assertRaises(RuntimeError):
            engine_db.db_snapshot(line, db=_DATABASE)
