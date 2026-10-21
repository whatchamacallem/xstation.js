# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `db.create`, `db.drop`, `db.snapshot` and `db.chunk` through the
# dispatcher on a real store under `build/`: databases made and dropped by
# forwarded lines, a new database at `seq` 0, a stale `since`, the head of a
# kept snapshot, its pieces as blob 1 in memory and streamed to the cache, a
# database over `message_max` read in pieces whose replies each fit, a
# snapshot restored into a second store, and a recorded sequence of creates
# and drops replayed to a second store.

import dispatch, engine_db, hashlib, jslb, os, sqlite3, substrate, tempfile
import unittest, unittest.mock, uuid
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
_STORE_TARGET = "engine_db._STATE.store"

# The `overflow_bytes` of the settings, 128 KiB.
_OVERFLOW_BYTES = 131072

# The `line_max` of the settings, 1 MiB.
_LINE_MAX = 1048576

# The `blob_max` of the settings, 10 MiB.
_BLOB_MAX = 10485760

# The `message_max` of the settings, 10 MiB.
_MESSAGE_MAX = 10485760

# The largest piece a reader asks for, so that its reply fits `message_max`.
_PIECE_MAX = _MESSAGE_MAX - _LINE_MAX

# The bytes of each row of the database over `message_max`, 1 MiB.
_ROW_BYTES = 1048576

# The rows of that database, 11 MiB together.
_ROW_COUNT = 11

# The database the tests create, snapshot and drop.
_DATABASE = "castle"

# Text beyond ASCII, built from its code points.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)

# A text row large enough to put the database file over `overflow_bytes`.
_BIG_TEXT = "x" * 200000

# A value over `overflow_bytes`, which the store keeps in the cache.
_VALUE_OVER = bytes(range(256)) * 800

# The magic bytes that start every SQLite database file.
_FILE_MAGIC = b"SQLite format 3\x00"

# Creates of the metaverse, a universe, its world and region, then a drop.
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

    return jslb.LineDecoder(
        _LINE_MAX, _BLOB_MAX, _MESSAGE_MAX, _OVERFLOW_BYTES, sink_make
    )


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


# Tests the handler of `db.create`.
class TestCreate(IsolatedCase):
    # A create makes the database file at `seq` 0 and replies with nothing.
    def test_database_created(self) -> None:
        engine_db.handlers_register(self.store)
        line = _line_make("db.create", 3, db=_DATABASE, since=0)
        reply = _reply_get(line)
        self.assertEqual(reply[0], {"t": "db.create", "r": 3})
        self.assertEqual(jslb.payload_of(reply), {})
        self.assertEqual(self.store.db_list(), [_DATABASE])
        self.assertEqual(self.store.seq_get(_DATABASE), 0)
        path = os.path.join(self.root, "castle.sqlite")
        self.assertTrue(os.path.isfile(path))

    # A stale `since` raises the desync and nothing is created.
    def test_since_stale(self) -> None:
        engine_db.handlers_register(self.store)
        line = _line_make("db.create", 1, db=_DATABASE, since=1)
        message = i18n("substrate.since_stale", "db.create", 1, 0, _DATABASE)
        self.dispatch_check(RuntimeError, message, line)
        self.assertEqual(self.store.db_list(), [])
        self.assertEqual(os.listdir(self.root), ["cache"])

    # A database that exists raises, and so does a name that is not valid.
    def test_create_refused(self) -> None:
        engine_db.handlers_register(self.store)
        self.store.db_create(_DATABASE)
        line = _line_make("db.create", 1, db=_DATABASE, since=0)
        with self.assertRaises(FileExistsError) as caught:
            dispatch.line_dispatch(line)
        path = os.path.join(self.root, "castle.sqlite")
        self.assertEqual(caught.exception.filename, path)
        self.assertEqual(self.store.seq_get(_DATABASE), 0)
        for name in ("", "a-b", "9a", "a/b"):
            with self.subTest(name=name):
                line = _line_make("db.create", 1, db=name, since=0)
                message = i18n("substrate.name_bad", name)
                self.dispatch_check(ValueError, message, line)
        self.assertEqual(self.store.db_list(), [_DATABASE])
        self.assertEqual(_files_find(self.root), ["castle.sqlite"])


# Tests the handler of `db.drop`.
class TestDrop(IsolatedCase):
    # A drop closes and deletes the database and its cache files.
    def test_database_dropped(self) -> None:
        engine_db.handlers_register(self.store)
        self.store.db_create(_DATABASE)
        self.store.kv_put("/castle/maps/castle.bin", _VALUE_OVER)
        cache = os.path.join(self.root, "cache")
        self.assertEqual(len(os.listdir(cache)), 1)
        line = _line_make("db.drop", 4, db=_DATABASE, since=1)
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
        self.store.kv_put("/castle/a", b"one")
        line = _line_make("db.drop", 1, db=_DATABASE, since=0)
        message = i18n("substrate.since_stale", "db.drop", 0, 1, _DATABASE)
        self.dispatch_check(RuntimeError, message, line)
        self.assertEqual(self.store.db_list(), [_DATABASE])
        self.assertEqual(_files_find(self.root), ["castle.sqlite"])

    # A database that is not open raises.
    def test_drop_unknown(self) -> None:
        engine_db.handlers_register(self.store)
        line = _line_make("db.drop", 1, db=_DATABASE, since=0)
        message = i18n("substrate.db_closed", _DATABASE)
        self.dispatch_check(LookupError, message, line)


# Tests the handlers of `db.snapshot` and `db.chunk`.
class TestSnapshot(IsolatedCase):
    # Makes the database with a table and one row of the text: `seq` 1.
    def database_fill(self, text: str) -> None:
        self.store.db_create(_DATABASE)
        statements = [
            _statement_make("CREATE TABLE t (x TEXT) STRICT"),
            _statement_make("INSERT INTO t VALUES (?)", text),
        ]
        self.store.sql_run(_DATABASE, statements)

    # Makes the database with rows of zero bytes past `message_max`: `seq` 1.
    def database_over(self) -> None:
        self.store.db_create(_DATABASE)
        statements = [
            _statement_make("CREATE TABLE b (x BLOB) STRICT"),
            _statement_make(
                "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL"
                " SELECT i + 1 FROM n WHERE i < ?)"
                " INSERT INTO b SELECT zeroblob(?) FROM n",
                _ROW_COUNT,
                _ROW_BYTES,
            ),
        ]
        self.store.sql_run(_DATABASE, statements)

    # Restores the snapshot into a second store and reads back the row.
    def row_restored(self, data: bytes) -> list[list[Any]]:
        second = self.store_make(self.root_make())
        self.assertEqual(second.db_restore(_DATABASE, data), 1)
        statement = _statement_make("SELECT x FROM t")
        return second.sql_run(_DATABASE, [statement])[0].rows

    # The head holds the number, size, hash and `seq` of the kept snapshot.
    def test_head_replied(self) -> None:
        engine_db.handlers_register(self.store)
        self.database_fill(_WIDE_TEXT)
        data, _ = self.store.db_snapshot(_DATABASE)
        reply = _reply_get(_line_make("db.snapshot", 9, db=_DATABASE))
        self.assertEqual(reply[0], {"t": "db.snapshot", "r": 9})
        payload = {
            "snapshot": 1,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "seq": 1,
        }
        self.assertEqual(jslb.payload_of(reply), payload)
        self.assertEqual(data[:16], _FILE_MAGIC)
        piece = _line_make(
            "db.chunk", 10, snapshot=1, offset=0, size=len(data)
        )
        self.assertEqual(_reply_get(piece)[1]["d"], data)
        self.assertEqual(self.row_restored(data), [[_WIDE_TEXT]])

    # A piece is blob 1, streamed over `overflow_bytes`, and the last one goes.
    def test_pieces_replied(self) -> None:
        engine_db.handlers_register(self.store)
        self.database_fill(_BIG_TEXT)
        data, _ = self.store.db_snapshot(_DATABASE)
        head = _reply_get(_line_make("db.snapshot", 1, db=_DATABASE))
        line = _line_make("db.chunk", 2, snapshot=1, offset=0, size=len(data))
        reply = _reply_get(line)
        self.assertEqual(reply[0], {"t": "db.chunk", "r": 2, "b": 1})
        self.assertEqual(reply[1], {"s": len(data), "d": data})
        self.assertEqual(jslb.payload_of(reply), {})
        self.assertGreater(len(data), _OVERFLOW_BYTES)
        decoded = _line_decode(self.root, _wire_bytes(reply))
        self.assertEqual(decoded[1]["sha256"], head["sha256"])
        self.assertEqual(_blob_read(decoded, 1), data)
        self.assertEqual(self.row_restored(data), [[_BIG_TEXT]])
        message = i18n("substrate.snapshot_unknown", 1)
        self.dispatch_check(LookupError, message, line)

    # A database over `message_max` comes in pieces whose replies each fit.
    def test_over_message(self) -> None:
        engine_db.handlers_register(self.store)
        self.database_over()
        head = _reply_get(_line_make("db.snapshot", 1, db=_DATABASE))
        size: int = head["size"]
        self.assertGreater(size, _MESSAGE_MAX)
        data = b""
        while len(data) < size:
            line = _line_make(
                "db.chunk",
                2,
                snapshot=head["snapshot"],
                offset=len(data),
                size=min(_PIECE_MAX, size - len(data)),
            )
            wire = _wire_bytes(_reply_get(line))
            self.assertLessEqual(len(wire), _MESSAGE_MAX)
            data += _blob_read(_line_decode(self.root, wire), 1)
        self.assertEqual(hashlib.sha256(data).hexdigest(), head["sha256"])
        second = self.store_make(self.root_make())
        self.assertEqual(second.db_restore(_DATABASE, data), 1)
        statement = _statement_make("SELECT count(*), sum(length(x)) FROM b")
        rows = second.sql_run(_DATABASE, [statement])[0].rows
        self.assertEqual(rows, [[_ROW_COUNT, _ROW_COUNT * _ROW_BYTES]])

    # A piece of no kept snapshot, or one outside it, raises.
    def test_chunk_refused(self) -> None:
        engine_db.handlers_register(self.store)
        self.store.db_create(_DATABASE)
        line = _line_make("db.chunk", 1, snapshot=1, offset=0, size=1)
        message = i18n("substrate.snapshot_unknown", 1)
        self.dispatch_check(LookupError, message, line)
        head = _reply_get(_line_make("db.snapshot", 2, db=_DATABASE))
        size: int = head["size"]
        line = _line_make("db.chunk", 3, snapshot=1, offset=size, size=1)
        message = i18n("substrate.snapshot_range", 1, size, 1, size)
        self.dispatch_check(ValueError, message, line)

    # The `seq` of the reply is the `seq` of the database at that moment.
    def test_seq_replied(self) -> None:
        engine_db.handlers_register(self.store)
        self.store.db_create(_DATABASE)
        line = _line_make("db.snapshot", 1, db=_DATABASE)
        self.assertEqual(_reply_get(line)["seq"], 0)
        self.store.kv_put("/castle/a", b"one")
        line = _line_make("db.snapshot", 2, db=_DATABASE)
        self.assertEqual(_reply_get(line)["seq"], 1)

    # A database that is not open raises.
    def test_snapshot_unknown(self) -> None:
        engine_db.handlers_register(self.store)
        line = _line_make("db.snapshot", 1, db=_DATABASE)
        message = i18n("substrate.db_closed", _DATABASE)
        self.dispatch_check(LookupError, message, line)


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
            self.assertEqual(second.seq_get(name), 0)
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
        message = i18n("dispatch.handler_twice", "db.create", 0)
        self.raise_check(
            ValueError,
            message,
            lambda: engine_db.handlers_register(self.store),
        )

    # Called before the registration each handler raises.
    def test_unregistered(self) -> None:
        line = _line_make("db.create", 1)
        message = i18n("engine_db.not_registered")
        calls: list[Callable[[], object]] = [
            lambda: engine_db.db_create(line, db=_DATABASE, since=0),
            lambda: engine_db.db_drop(line, db=_DATABASE, since=0),
            lambda: engine_db.db_snapshot(line, db=_DATABASE),
            lambda: engine_db.db_chunk(line, snapshot=1, offset=0, size=1),
        ]
        for call in calls:
            self.raise_check(RuntimeError, message, call)
