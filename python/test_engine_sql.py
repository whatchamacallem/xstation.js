# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `sql.run` through the dispatcher on a real store under `build/`: the
# statements, results and `seq` numbers the turn and sync transcripts
# recorded, a read that leaves `seq`, a stale `since` that runs nothing, a
# failed commit rolled back whole, malformed statements, bound parameters,
# and the transcripts' statements replayed to a second store, compared by
# dump and `seq` at every step. A new database starts at `seq` 0.

import dispatch, engine_sql, jslb, os, sqlite3, substrate, tempfile, unittest
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
_STORE_TARGET = "engine_sql._STATE.store"

# The `overflow_bytes` of the settings, 128 KiB.
_OVERFLOW_BYTES = 131072

# The `line_max` of the settings, 1 MiB.
_LINE_MAX = 1048576

# The `blob_max` of the settings, 10 MiB.
_BLOB_MAX = 10485760

# The `message_max` of the settings, 10 MiB.
_MESSAGE_MAX = 10485760

# The universe database that the turn transcript creates.
_UNIVERSE = "castle"

# The world database that the turn transcript creates.
_WORLD = "castle_world"

# The database of the universe table.
_METAVERSE = "metaverse"

# The `seq` of `metaverse` when the turn transcript inserts the universe.
_METAVERSE_SINCE = 7

# The universe table, the one fixed schema of `metaverse`.
_UNIVERSE_DDL = (
    "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL,"
    " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT"
)

# The world table that the bootstrap script makes in the universe database.
_WORLD_DDL = (
    "CREATE TABLE world (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT"
)

# The region table that the bootstrap script makes in the world database.
_REGION_DDL = (
    "CREATE TABLE region (name TEXT PRIMARY KEY, tide INTEGER NOT NULL"
    " DEFAULT 0) STRICT"
)

# The statements the turn transcript commits in the universe database.
_UNIVERSE_STATEMENTS: list[dict[str, Any]] = [
    {"sql": _WORLD_DDL, "params": []},
    {
        "sql": "INSERT INTO world VALUES (?, ?)",
        "params": ["castle_world", "The castle"],
    },
]

# The statements the turn transcript commits in the world database.
_WORLD_STATEMENTS: list[dict[str, Any]] = [
    {"sql": _REGION_DDL, "params": []},
    {
        "sql": "INSERT INTO region (name) VALUES (?)",
        "params": ["castle_gatehouse"],
    },
]

# The statement the turn transcript commits in `metaverse`.
_METAVERSE_STATEMENTS: list[dict[str, Any]] = [
    {
        "sql": "INSERT INTO universe VALUES (?, ?, ?, ?)",
        "params": ["castle", "The castle", "player", "castle_world"],
    },
]

# The statement the sync transcript commits in the universe database.
_UPDATE_STATEMENTS: list[dict[str, Any]] = [
    {
        "sql": "UPDATE world SET title = ? WHERE name = ?",
        "params": ["The castle at dusk", "castle_world"],
    },
]

# A read of the world table, which changes nothing.
_SELECT_STATEMENTS: list[dict[str, Any]] = [
    {"sql": "SELECT name, title FROM world", "params": []},
]

# The result of a statement that has no columns and changes no row.
_NO_CHANGE: dict[str, Any] = {"columns": [], "rows": [], "changes": 0}

# The result of a statement that has no columns and changes one row.
_ONE_CHANGE: dict[str, Any] = {"columns": [], "rows": [], "changes": 1}

# Text with quotes, a statement separator and characters beyond ASCII.
_QUOTED_TEXT = "it's 'quoted'; DROP TABLE t; --" + chr(0x4E2D) + chr(0x1F600)


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
        _LINE_MAX, _BLOB_MAX, _MESSAGE_MAX, _OVERFLOW_BYTES, _sink_refuse
    )
    (line,) = decoder.bytes_feed(wire)
    return line


# Builds a `sql.run` line as the server reads it off the wire.
def _run_line(
    db: str, statements: list[dict[str, Any]], since: int
) -> jslb.Object:
    line = _line_make("sql.run", 1, db=db, statements=statements, since=since)
    return _line_decode(_wire_bytes(line))


# One SQL statement with its parameters.
def _statement_make(sql: str, *params: Any) -> substrate.SqlStatement:
    return substrate.SqlStatement(sql, list(params))


# Closes every database a store has open.
def _store_close(store: substrate.Store) -> None:
    for name in store.db_list():
        store.db_close(name)


# Every statement of the dump of a database file, read beside its store.
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
        self.store.db_create(_UNIVERSE)

    # Makes a scratch root under `build/`, removed when the test ends.
    def root_make(self) -> str:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        return self.enterContext(tempfile.TemporaryDirectory(dir=_BUILD_PATH))

    # Makes a store on a root, closing its databases when the test ends.
    def store_make(self, root: str) -> substrate.Store:
        store = substrate.Store(root, _OVERFLOW_BYTES)
        self.addCleanup(_store_close, store)
        return store

    # Says whether the universe database has a table of the name.
    def table_exists(self, name: str) -> bool:
        statement = _statement_make(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = ?",
            name,
        )
        return bool(self.store.sql_run(_UNIVERSE, [statement])[0].rows)

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

    # Dispatches a line and checks it raises the type with text matching.
    def dispatch_match(
        self, kind: type[Exception], pattern: str, line: jslb.Object
    ) -> None:
        with self.assertRaisesRegex(kind, pattern):
            dispatch.line_dispatch(line)


# Tests the handler of `sql.run` with the transcripts' statements.
class TestRecorded(IsolatedCase):
    # The universe database's commit: two results and `seq` 1 from 0.
    def test_universe_statements(self) -> None:
        engine_sql.handlers_register(self.store)
        reply = _reply_get(_run_line(_UNIVERSE, _UNIVERSE_STATEMENTS, 0))
        payload = {"results": [_NO_CHANGE, _ONE_CHANGE], "seq": 1}
        self.assertEqual(reply[0], {"t": "sql.run", "r": 1})
        self.assertEqual(jslb.payload_of(reply), payload)
        decoded = _line_decode(_wire_bytes(reply))
        self.assertEqual(jslb.payload_of(decoded), payload)
        self.assertEqual(self.store.seq_get(_UNIVERSE), 1)

    # The world database's commit: two results and `seq` 1 from 0.
    def test_world_statements(self) -> None:
        engine_sql.handlers_register(self.store)
        self.store.db_create(_WORLD)
        reply = _reply_get(_run_line(_WORLD, _WORLD_STATEMENTS, 0))
        payload = {"results": [_NO_CHANGE, _ONE_CHANGE], "seq": 1}
        self.assertEqual(jslb.payload_of(reply), payload)
        self.assertEqual(self.store.seq_get(_WORLD), 1)

    # The universe row of `metaverse`: one result and `seq` 8 from 7.
    def test_metaverse_statement(self) -> None:
        engine_sql.handlers_register(self.store)
        self.store.db_create(_METAVERSE)
        self.store.sql_run(_METAVERSE, [_statement_make(_UNIVERSE_DDL)])
        for number in range(2, _METAVERSE_SINCE + 1):
            key = f"/metaverse/before/{number}"
            self.store.kv_put(key, str(number).encode("ascii"))
        self.assertEqual(self.store.seq_get(_METAVERSE), _METAVERSE_SINCE)
        line = _run_line(_METAVERSE, _METAVERSE_STATEMENTS, _METAVERSE_SINCE)
        reply = _reply_get(line)
        payload = {"results": [_ONE_CHANGE], "seq": 8}
        self.assertEqual(jslb.payload_of(reply), payload)

    # The sync transcript's update after the universe commit: `seq` 2 from 1.
    def test_update_statement(self) -> None:
        engine_sql.handlers_register(self.store)
        _reply_get(_run_line(_UNIVERSE, _UNIVERSE_STATEMENTS, 0))
        reply = _reply_get(_run_line(_UNIVERSE, _UPDATE_STATEMENTS, 1))
        payload = {"results": [_ONE_CHANGE], "seq": 2}
        self.assertEqual(jslb.payload_of(reply), payload)
        self.assertEqual(self.store.seq_get(_UNIVERSE), 2)

    # A read replies its columns and rows and leaves the `seq` as it was.
    def test_select_unchanged(self) -> None:
        engine_sql.handlers_register(self.store)
        _reply_get(_run_line(_UNIVERSE, _UNIVERSE_STATEMENTS, 0))
        _reply_get(_run_line(_UNIVERSE, _UPDATE_STATEMENTS, 1))
        reply = _reply_get(_run_line(_UNIVERSE, _SELECT_STATEMENTS, 2))
        result = {
            "columns": ["name", "title"],
            "rows": [["castle_world", "The castle at dusk"]],
            "changes": 0,
        }
        self.assertEqual(
            jslb.payload_of(reply), {"results": [result], "seq": 2}
        )
        self.assertEqual(self.store.seq_get(_UNIVERSE), 2)


# Tests what the handler of `sql.run` refuses.
class TestRefused(IsolatedCase):
    # A stale `since` raises the desync and runs nothing.
    def test_since_stale(self) -> None:
        engine_sql.handlers_register(self.store)
        line = _run_line(_UNIVERSE, _UNIVERSE_STATEMENTS, 1)
        message = i18n("substrate.since_stale", "sql.run", 1, 0, _UNIVERSE)
        self.dispatch_check(RuntimeError, message, line)
        self.assertFalse(self.table_exists("world"))
        self.assertEqual(self.store.seq_get(_UNIVERSE), 0)

    # A failing second statement rolls the first one back.
    def test_statement_failed(self) -> None:
        engine_sql.handlers_register(self.store)
        statements: list[dict[str, Any]] = [
            {"sql": "CREATE TABLE t (x TEXT) STRICT", "params": []},
            {"sql": "INSERT INTO missing VALUES (1)", "params": []},
        ]
        line = _run_line(_UNIVERSE, statements, 0)
        pattern = "no such table: missing"
        self.dispatch_match(sqlite3.OperationalError, pattern, line)
        self.assertFalse(self.table_exists("t"))
        self.assertEqual(self.store.seq_get(_UNIVERSE), 0)

    # A statement with a key missing or a key too many raises.
    def test_statement_malformed(self) -> None:
        engine_sql.handlers_register(self.store)
        line = _run_line(_UNIVERSE, [{"sql": "SELECT 1"}], 0)
        pattern = "missing 1 required positional argument: 'params'"
        self.dispatch_match(TypeError, pattern, line)
        statements: list[dict[str, Any]] = [
            {"sql": "SELECT 1", "params": [], "extra": 1},
        ]
        line = _run_line(_UNIVERSE, statements, 0)
        pattern = "unexpected keyword argument 'extra'"
        self.dispatch_match(TypeError, pattern, line)
        self.assertEqual(self.store.seq_get(_UNIVERSE), 0)

    # A database that is not open raises.
    def test_database_unknown(self) -> None:
        engine_sql.handlers_register(self.store)
        line = _run_line("none", _SELECT_STATEMENTS, 0)
        message = i18n("substrate.db_closed", "none")
        self.dispatch_check(LookupError, message, line)


# Tests the handler of `sql.run` on edge cases of its input.
class TestEdges(IsolatedCase):
    # No statements reply no results and leave the `seq`.
    def test_statements_empty(self) -> None:
        engine_sql.handlers_register(self.store)
        reply = _reply_get(_run_line(_UNIVERSE, [], 0))
        self.assertEqual(jslb.payload_of(reply), {"results": [], "seq": 0})

    # Text with quotes and beyond ASCII is bound, stored and read back whole.
    def test_parameters_bound(self) -> None:
        engine_sql.handlers_register(self.store)
        statements: list[dict[str, Any]] = [
            {"sql": "CREATE TABLE t (x TEXT) STRICT", "params": []},
            {"sql": "INSERT INTO t VALUES (?)", "params": [_QUOTED_TEXT]},
            {"sql": "SELECT x FROM t", "params": []},
        ]
        reply = _reply_get(_run_line(_UNIVERSE, statements, 0))
        read = {"columns": ["x"], "rows": [[_QUOTED_TEXT]], "changes": 0}
        payload = {"results": [_NO_CHANGE, _ONE_CHANGE, read], "seq": 1}
        self.assertEqual(jslb.payload_of(reply), payload)
        decoded = _line_decode(_wire_bytes(reply))
        self.assertEqual(jslb.payload_of(decoded), payload)
        self.assertTrue(self.table_exists("t"))


# Tests the transcripts' statements replayed on a second store.
class TestReplay(IsolatedCase):
    # Runs statements on the first store, forwards them, compares the two.
    def operation_forward(
        self,
        second_root: str,
        db: str,
        statements: list[dict[str, Any]],
    ) -> int:
        since = self.store.seq_get(db)
        parsed = [substrate.SqlStatement(**item) for item in statements]
        results = [
            {
                "columns": result.columns,
                "rows": result.rows,
                "changes": result.changes,
            }
            for result in self.store.sql_run(db, parsed)
        ]
        reply = jslb.payload_of(_reply_get(_run_line(db, statements, since)))
        self.assertEqual(reply["results"], results, db)
        self.assertEqual(reply["seq"], self.store.seq_get(db), db)
        name = db + ".sqlite"
        self.assertEqual(
            _database_dump(os.path.join(self.root, name)),
            _database_dump(os.path.join(second_root, name)),
            db,
        )
        return reply["seq"]

    # The second store follows the first, dump for dump and `seq` for `seq`.
    def test_recorded_replay(self) -> None:
        second_root = self.root_make()
        second = self.store_make(second_root)
        engine_sql.handlers_register(second)
        self.store.db_create(_WORLD)
        second.db_create(_UNIVERSE)
        second.db_create(_WORLD)
        steps = [
            (_UNIVERSE, _UNIVERSE_STATEMENTS),
            (_WORLD, _WORLD_STATEMENTS),
            (_UNIVERSE, _UPDATE_STATEMENTS),
        ]
        seqs = [
            self.operation_forward(second_root, db, statements)
            for db, statements in steps
        ]
        self.assertEqual(seqs, [1, 1, 2])
        self.assertEqual(second.seq_get(_UNIVERSE), 2)
        self.assertEqual(second.seq_get(_WORLD), 1)


# Tests the registration.
class TestRegister(IsolatedCase):
    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_sql.handlers_register(self.store)
        message = i18n("dispatch.handler_twice", "sql.run", 0)
        self.raise_check(
            ValueError,
            message,
            lambda: engine_sql.handlers_register(self.store),
        )

    # Called before the registration the handler raises.
    def test_unregistered(self) -> None:
        line = _line_make("sql.run", 1)
        message = i18n("engine_sql.not_registered")
        self.raise_check(
            RuntimeError,
            message,
            lambda: engine_sql.sql_run(
                line, db=_UNIVERSE, statements=[], since=0
            ),
        )
