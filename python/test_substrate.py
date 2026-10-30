# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of the server substrate on scratch roots under build/: the tables on
# first use, both ref forms, documents and heads, a document's stored text
# against the body of a doc.put line of the gold, overflow to the cache at
# the setting overflow_bytes, a lost cache file, a kill between a cache file
# and its row, snapshots and restores with their cache files, some lost,
# turns, SQL, a trigger's refusal, and transactions over several databases.
# Each text a refusal is checked against is the gold's.

import harness, hashlib, json, os, resource, signal, sqlite3, substrate
import tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any, NoReturn, cast

# The checkout's build directory, where each test makes its scratch roots.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_substrate"

# The `overflow_bytes` of the settings.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# The hyperposition scene, whose conversation the turn tests append to.
_SCENE = "/metaverse/hyperposition/1"

# Text beyond ASCII for keys and values, built from its code points.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)

# A value of exactly `overflow_bytes`, which stays in its row.
_VALUE_EXACT = bytes(index % 256 for index in range(_OVERFLOW_BYTES))

# A value one byte over `overflow_bytes`, which goes to the cache.
_VALUE_OVER = _VALUE_EXACT + bytes(1)

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

# The stored text of the arrival scene, its canonical JSON.
_ARRIVAL_TEXT = (
    '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png","subtitle":"'
    + _ARRIVAL_SUBTITLE
    + '","image":{"$ref":1}}'
)

# A document, integer keys below the top level out of order, names sorted.
_NESTED_BODY: dict[int | str, Any] = {
    0: {"t": "nest"},
    1: "/_files/fog.png",
    "count": -3,
    "inner": {
        "a": [{"z": None, 0: 0.5}],
        2: _WIDE_TEXT,
        "b": 1,
        1: {"$ref": 1},
    },
}

# The `_meta` table alone, as the substrate's SQL file creates it.
_META_SQL = (
    "CREATE TABLE _meta (name TEXT PRIMARY KEY, value TEXT NOT NULL)"
    " WITHOUT ROWID, STRICT"
)

# The universe table, as the metaverse SQL file creates it.
_UNIVERSE_SQL = (
    "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL,"
    " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT"
)

# The universe table's trigger on insert, as the metaverse SQL file has it.
_UNIVERSE_TRIGGER = (
    "CREATE TRIGGER universe_world_insert BEFORE INSERT ON universe"
    " WHEN EXISTS (SELECT 1 FROM universe"
    " WHERE world = NEW.world AND name <> NEW.name)"
    " BEGIN SELECT RAISE(ABORT, 'agent.content_ambiguous'); END"
)

# The insert of one row of the universe table.
_UNIVERSE_INSERT = "INSERT INTO universe VALUES (?, ?, ?, ?)"

# The world table of the castle universe database.
_WORLD_SQL = (
    "CREATE TABLE world (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT"
)


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# Makes a scratch root under build/, removed when the test ends.
def _root_make(case: unittest.TestCase) -> str:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    return case.enterContext(tempfile.TemporaryDirectory(dir=_BUILD_PATH))


# Makes a store on a root whose databases close when the test ends.
def _store_make(case: unittest.TestCase, root: str) -> substrate.Store:
    store = substrate.Store(root, _OVERFLOW_BYTES)
    case.addCleanup(_store_close, store)
    return store


# Closes every database a store has open.
def _store_close(store: substrate.Store) -> None:
    for name in store.db_list():
        store.db_close(name)


# Makes a call that must raise the type with exactly the message.
def _error_check(
    case: unittest.TestCase,
    kind: type[BaseException],
    message: str,
    call: Callable[[], object],
) -> None:
    with case.assertRaises(kind) as caught:
        call()
    case.assertEqual(str(caught.exception), message)


# One statement with its parameters.
def _statement_make(sql: str, *params: Any) -> substrate.SqlStatement:
    return substrate.SqlStatement(sql, list(params))


# The rows one statement returns.
def _rows_query(
    store: substrate.Store, db: str, sql: str, *params: Any
) -> list[list[Any]]:
    return store.sql_run(db, [_statement_make(sql, *params)])[0].rows


# The names of the tables of a database, in order.
def _tables_list(store: substrate.Store, db: str) -> list[str]:
    rows = _rows_query(
        store,
        db,
        "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name",
    )
    return [row[0] for row in rows]


# Makes a database file on a plain connection and runs the statements in it.
def _file_make(
    path: str, schema: bool, statements: list[substrate.SqlStatement]
) -> None:
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        if schema:
            substrate.schema_apply(connection)
        for statement in statements:
            connection.execute(statement.sql, statement.params)
    finally:
        connection.close()


# The names of the tables of a database file, read on a plain connection.
def _names_read(path: str) -> list[str]:
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name"
        ).fetchall()
    finally:
        connection.close()
    return [row[0] for row in rows]


# Writes a row of `alpha`, then makes the call in the same transaction.
def _busy_call(store: substrate.Store, call: Callable[[], object]) -> None:
    store.kv_put("/alpha/busy", b"busy")
    call()


# The canonical JSON text of a value, as the substrate stores it.
def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# The bytes a reader is fed for a line of the gold with no blob.
def _line_bytes(line: dict[str, Any]) -> bytes:
    return _json_text(line).encode("utf-8") + b"\r"


# The path of the cache file of a value under a root.
def _cache_file(root: str, value: bytes) -> str:
    return os.path.join(root, "cache", hashlib.sha256(value).hexdigest())


# The bytes of a value as a store holds it: its row's or its cache file's.
def _value_bytes(value: substrate.KvValue) -> bytes:
    if isinstance(value.data, bytes):
        return value.data
    with open(value.data, "rb") as file:
        return file.read()


# Makes `alpha` with two values over `overflow_bytes` and one under, by ref.
def _alpha_fill(store: substrate.Store) -> dict[str, bytes]:
    values = {
        "/alpha/one": _VALUE_OVER,
        "/alpha/small": b"small",
        "/alpha/two": bytes(reversed(_VALUE_OVER)),
    }
    store.db_create("alpha")
    for ref, value in values.items():
        store.kv_put(ref, value)
    return values


# Every statement of the dump of a database file: its schema and its rows.
def _database_dump(path: str) -> list[str]:
    connection = sqlite3.connect(path)
    try:
        return list(connection.iterdump())
    finally:
        connection.close()


# Forked child: puts over `overflow_bytes`, file whole, killed writing the row.
def _child_put(root: str) -> NoReturn:
    try:
        store = substrate.Store(root, _OVERFLOW_BYTES)
        store.db_open("alpha")
        # Its row ends the write ahead log past the size of that cache file.
        store.kv_put("/alpha/fill", _VALUE_EXACT)
        core = resource.getrlimit(resource.RLIMIT_CORE)[1]
        resource.setrlimit(resource.RLIMIT_CORE, (0, core))
        size = resource.getrlimit(resource.RLIMIT_FSIZE)[1]
        resource.setrlimit(resource.RLIMIT_FSIZE, (len(_VALUE_OVER), size))
        # The default action of SIGXFSZ, which Python ignores, kills.
        signal.signal(signal.SIGXFSZ, signal.SIG_DFL)
        store.kv_put("/alpha/big", _VALUE_OVER)
    finally:
        os._exit(1)


# A create one descriptor short, returning the error and databases left open.
def _create_limited(root: str, write_fd: int) -> str:
    store = substrate.Store(root, _OVERFLOW_BYTES)
    free = os.dup(write_fd)
    os.close(free)
    files = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    resource.setrlimit(resource.RLIMIT_NOFILE, (free + 1, files))
    try:
        store.db_create("alpha")
    except sqlite3.OperationalError as error:
        return f"{error} {store.db_list()}"
    return f"created {store.db_list()}"


# In the forked child: the limited create, how it ended written to the pipe.
def _child_create(root: str, write_fd: int) -> NoReturn:
    try:
        try:
            ending = _create_limited(root, write_fd)
        except BaseException:
            ending = traceback.format_exc()
        os.write(write_fd, ending.encode("utf-8"))
    finally:
        os._exit(0)


# Databases: the tables on first use, names, creating, opening, dropping.
class TestDatabases(unittest.TestCase):
    # A new database gets the substrate's tables and the `schema` row 1 alone.
    def test_tables_created(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        self.assertEqual(
            _tables_list(store, "alpha"), ["_head", "_kv", "_meta", "_turn"]
        )
        rows = _rows_query(
            store, "alpha", "SELECT name, value FROM _meta ORDER BY name"
        )
        self.assertEqual(rows, [["schema", "1"]])
        self.assertEqual(store.db_list(), ["alpha"])

    # A database file made elsewhere gets the tables when first opened.
    def test_tables_foreign(self) -> None:
        root = _root_make(self)
        connection = sqlite3.connect(os.path.join(root, "beta.sqlite"))
        try:
            connection.execute("CREATE TABLE note (text TEXT)")
            connection.execute("INSERT INTO note VALUES (?)", (_WIDE_TEXT,))
            connection.commit()
        finally:
            connection.close()
        store = _store_make(self, root)
        store.db_open("beta")
        self.assertEqual(
            _tables_list(store, "beta"),
            ["_head", "_kv", "_meta", "_turn", "note"],
        )
        self.assertEqual(
            _rows_query(store, "beta", "SELECT text FROM note"), [[_WIDE_TEXT]]
        )

    # A name that is not a C identifier raises and makes no file.
    def test_names_bad(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        names = {
            "empty": "",
            "digit": "1abc",
            "dash": "a-b",
            "space": "a b",
            "dot": "a.b",
            "slash": "a/b",
            "accent": "caf" + chr(0xE9),
        }
        for case, name in names.items():
            message = _text_get(f"substrate_name_bad_{case}")
            _error_check(
                self, ValueError, message, lambda: store.db_create(name)
            )
            _error_check(
                self, ValueError, message, lambda: store.db_open(name)
            )
        self.assertEqual(os.listdir(root), ["cache"])
        self.assertEqual(store.db_list(), [])

    # A second create, a second open, a missing file and a close all raise.
    def test_create_twice(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        with self.assertRaises(FileExistsError) as caught:
            store.db_create("alpha")
        path = os.path.join(root, "alpha.sqlite")
        self.assertEqual(caught.exception.filename, path)
        message = _text_get("substrate_db_open")
        _error_check(
            self, RuntimeError, message, lambda: store.db_open("alpha")
        )
        _error_check(
            self,
            sqlite3.OperationalError,
            "unable to open database file",
            lambda: store.db_open("gamma"),
        )
        self.assertFalse(os.path.exists(os.path.join(root, "gamma.sqlite")))
        message = _text_get("substrate_db_closed_close")
        _error_check(
            self, LookupError, message, lambda: store.db_close("gamma")
        )
        self.assertEqual(store.db_list(), ["alpha"])

    # A create whose open fails removes its file, so a later create succeeds.
    def test_create_failed(self) -> None:
        root = _root_make(self)
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            _child_create(root, write_fd)
        os.close(write_fd)
        with os.fdopen(read_fd, "rb") as pipe:
            ending = pipe.read().decode("utf-8")
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        self.assertEqual(ending, "unable to open database file []")
        self.assertEqual(os.listdir(root), ["cache"])
        store = _store_make(self, root)
        store.db_create("alpha")
        self.assertEqual(store.db_list(), ["alpha"])

    # A file with only some of the substrate's tables raises, its tables kept.
    def test_schema_partial(self) -> None:
        root = _root_make(self)
        path = os.path.join(root, "beta.sqlite")
        _file_make(path, False, [_statement_make(_META_SQL)])
        store = _store_make(self, root)
        message = _text_get("substrate_schema_partial_meta")
        _error_check(
            self, RuntimeError, message, lambda: store.db_open("beta")
        )
        self.assertEqual(store.db_list(), [])
        self.assertEqual(_names_read(path), ["_meta"])

    # A file whose `schema` row is not the substrate's version raises.
    def test_schema_version(self) -> None:
        root = _root_make(self)
        _file_make(
            os.path.join(root, "beta.sqlite"),
            True,
            [
                _statement_make(
                    "UPDATE _meta SET value = ? WHERE name = 'schema'", "2"
                )
            ],
        )
        store = _store_make(self, root)
        message = _text_get("substrate_schema_version")
        _error_check(
            self, RuntimeError, message, lambda: store.db_open("beta")
        )
        self.assertEqual(store.db_list(), [])

    # Closing, dropping or restoring a database a transaction wrote raises.
    def test_database_busy(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        data = store.db_snapshot("alpha").data
        listed = sorted(os.listdir(root))
        message = _text_get("substrate_db_busy")
        calls: list[Callable[[], object]] = [
            lambda: store.db_close("alpha"),
            lambda: store.db_drop("alpha"),
            lambda: store.db_restore("alpha", data, []),
        ]
        for call in calls:
            _error_check(
                self,
                RuntimeError,
                message,
                lambda: store.transaction_run(lambda: _busy_call(store, call)),
            )
            self.assertEqual(store.db_list(), ["alpha"])
            self.assertEqual(store.kv_list("alpha", ""), [])
            self.assertEqual(sorted(os.listdir(root)), listed)

    # A write ahead log another connection keeps beside a dropped file raises.
    def test_wal_left(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        path = os.path.join(root, "alpha.sqlite")
        reader = sqlite3.connect(path, isolation_level=None)
        self.addCleanup(reader.close)
        reader.execute("BEGIN")
        reader.execute("SELECT value FROM _meta").fetchall()
        message = _text_get("substrate_wal_left")
        _error_check(
            self, RuntimeError, message, lambda: store.db_drop("alpha")
        )
        self.assertEqual(store.db_list(), [])
        self.assertTrue(os.path.isfile(path))
        reader.execute("COMMIT")
        reader.close()
        store.db_open("alpha")

    # Dropping removes the file and the cache files no other database names.
    def test_drop_files(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.db_create("beta")
        alone = bytes(reversed(_VALUE_OVER))
        store.kv_put("/alpha/shared", _VALUE_OVER)
        store.kv_put("/alpha/alone", alone)
        store.kv_put("/beta/shared", _VALUE_OVER)
        store.db_drop("alpha")
        self.assertFalse(os.path.exists(os.path.join(root, "alpha.sqlite")))
        self.assertFalse(os.path.exists(_cache_file(root, alone)))
        shared = _cache_file(root, _VALUE_OVER)
        self.assertTrue(os.path.isfile(shared))
        self.assertEqual(store.db_list(), ["beta"])
        self.assertEqual(store.kv_get("/beta/shared").data, shared)
        store.db_drop("beta")
        self.assertEqual(os.listdir(os.path.join(root, "cache")), [])
        self.assertEqual(os.listdir(root), ["cache"])


# `Key-Value-Ref` and `Document-Ref` splitting, and the refs that are bad.
class TestRefs(unittest.TestCase):
    # Each form splits into its database, its key and its version.
    def test_split_forms(self) -> None:
        cases = [
            (_SCENE, substrate.RefParts("metaverse", "hyperposition/1", 1)),
            (
                "/metaverse/world",
                substrate.RefParts("metaverse", "world", None),
            ),
            (
                "script/bootstrap.js",
                substrate.RefParts(None, "script/bootstrap.js", None),
            ),
            (
                "scene/arrival/12",
                substrate.RefParts(None, "scene/arrival/12", 12),
            ),
            ("/_files/a//b/", substrate.RefParts("_files", "a//b/", None)),
            ("maps/01", substrate.RefParts(None, "maps/01", None)),
            ("7", substrate.RefParts(None, "7", None)),
            (
                "/x/" + _WIDE_TEXT + "/0",
                substrate.RefParts("x", _WIDE_TEXT + "/0", 0),
            ),
        ]
        for ref, parts in cases:
            self.assertEqual(substrate.ref_split(ref), parts, ref)

    # An empty ref, a missing key and a bad database name raise.
    def test_refs_bad(self) -> None:
        refs = {
            "empty": "",
            "slash": "/",
            "database_empty": "//key",
            "key_missing": "/metaverse",
            "key_empty": "/metaverse/",
            "digit": "/1db/key",
            "dash": "/d-b/key",
            "accent": "/caf" + chr(0xE9) + "/key",
        }
        for case, ref in refs.items():
            message = _text_get(f"substrate_ref_bad_{case}")
            _error_check(
                self, ValueError, message, lambda: substrate.ref_split(ref)
            )

    # An internal ref needs a database and an external ref takes none.
    def test_ref_database(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        message = _text_get("substrate_ref_internal")
        _error_check(
            self, ValueError, message, lambda: store.kv_put("world", b"x")
        )
        message = _text_get("substrate_ref_both")
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.kv_put("/alpha/world", b"x", "alpha"),
        )
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.kv_get("/alpha/world", "alpha"),
        )
        message = _text_get("substrate_db_closed_put")
        _error_check(
            self,
            LookupError,
            message,
            lambda: store.kv_put("/beta/world", b"x"),
        )
        message = _text_get("substrate_document_ref_value")
        _error_check(
            self, ValueError, message, lambda: store.doc_get("/alpha/world")
        )
        self.assertEqual(store.kv_list("alpha", ""), [])


# Values: both ref forms, the overflow limit, shared cache files, streams.
class TestValues(unittest.TestCase):
    # A value put by one ref form is read by the other, listed, deleted twice.
    def test_refs_both(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        key = "greeting/" + _WIDE_TEXT
        value = ("hello " + _WIDE_TEXT).encode("utf-8")
        digest = hashlib.sha256(value).digest()
        row = store.kv_put("/alpha/" + key, value)
        self.assertEqual(row, substrate.KvRow(key, len(value), digest))
        self.assertEqual(
            store.kv_get(key, "alpha"),
            substrate.KvValue(value, len(value), digest),
        )
        world = hashlib.sha256(b"world").digest()
        self.assertEqual(
            store.kv_put("place/a/b", b"world", "alpha"),
            substrate.KvRow("place/a/b", 5, world),
        )
        self.assertEqual(store.kv_get("/alpha/place/a/b").data, b"world")
        self.assertEqual(store.kv_list("alpha", "greeting/"), [row])
        keys = [listed.key for listed in store.kv_list("alpha", "")]
        self.assertEqual(keys, [key, "place/a/b"])
        self.assertIsNone(store.kv_delete(key, "alpha"))
        message = _text_get("substrate_key_missing_deleted")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/" + key)
        )
        self.assertIsNone(store.kv_delete(key, "alpha"))
        keys = [listed.key for listed in store.kv_list("alpha", "")]
        self.assertEqual(keys, ["place/a/b"])

    # A value of exactly `overflow_bytes` stays in its row, one byte more not.
    def test_overflow_boundary(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.kv_put("/alpha/exact", _VALUE_EXACT)
        exact = store.kv_get("/alpha/exact")
        self.assertEqual(exact.data, _VALUE_EXACT)
        self.assertEqual(exact.size, _OVERFLOW_BYTES)
        self.assertEqual(os.listdir(os.path.join(root, "cache")), [])
        store.kv_put("/alpha/over", _VALUE_OVER)
        path = _cache_file(root, _VALUE_OVER)
        digest = hashlib.sha256(_VALUE_OVER).digest()
        self.assertEqual(
            store.kv_get("/alpha/over"),
            substrate.KvValue(path, _OVERFLOW_BYTES + 1, digest),
        )
        with open(path, "rb") as file:
            self.assertEqual(file.read(), _VALUE_OVER)
        self.assertEqual(
            os.listdir(os.path.join(root, "cache")), [os.path.basename(path)]
        )

    # A cache file stays while any row of any database names its hash.
    def test_cache_shared(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.db_create("beta")
        path = _cache_file(root, _VALUE_OVER)
        store.kv_put("/alpha/one", _VALUE_OVER)
        store.kv_put("/alpha/two", _VALUE_OVER)
        store.kv_put("/beta/three", _VALUE_OVER)
        store.kv_delete("/alpha/one")
        self.assertTrue(os.path.isfile(path))
        store.kv_put("/alpha/two", b"small")
        self.assertTrue(os.path.isfile(path))
        store.db_close("beta")
        store.kv_put("/alpha/two", _VALUE_OVER)
        store.kv_delete("/alpha/two")
        self.assertTrue(os.path.isfile(path))
        store.db_open("beta")
        store.kv_delete("/beta/three")
        self.assertFalse(os.path.exists(path))
        self.assertEqual(store.kv_check("alpha"), 0)

    # A file the stream decoder wrote over `overflow_bytes` moves into place.
    def test_file_moved(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        sink = os.path.join(root, "cache", "sink")
        with open(sink, "wb") as file:
            file.write(_VALUE_OVER)
        row = store.kv_put("/alpha/streamed", sink)
        self.assertFalse(os.path.exists(sink))
        digest = hashlib.sha256(_VALUE_OVER).digest()
        self.assertEqual(
            row, substrate.KvRow("streamed", _OVERFLOW_BYTES + 1, digest)
        )
        self.assertEqual(
            store.kv_get("/alpha/streamed").data,
            _cache_file(root, _VALUE_OVER),
        )
        small = os.path.join(root, "cache", "small")
        with open(small, "wb") as file:
            file.write(_VALUE_EXACT)
        message = (
            _text_get("substrate_file_small")
            .replace("{0}", small)
            .replace("{1}", str(_OVERFLOW_BYTES))
            .replace("{2}", str(_OVERFLOW_BYTES))
        )
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.kv_put("/alpha/small", small),
        )
        self.assertEqual(store.kv_list("alpha", ""), [row])
        self.assertEqual(store.kv_check("alpha"), 1)
        self.assertFalse(os.path.exists(small))

    # A row whose cache file is gone stays listed and put over, its get raises.
    def test_file_lost(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        row = store.kv_put("/alpha/big", _VALUE_OVER)
        os.remove(_cache_file(root, _VALUE_OVER))
        message = _text_get("substrate_file_lost_removed").replace(
            "{1}", row.sha256.hex()
        )
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/big")
        )
        self.assertEqual(store.kv_list("alpha", ""), [row])
        store.kv_put("/alpha/big", b"small")
        self.assertEqual(store.kv_get("/alpha/big").data, b"small")


# Documents: versions and heads, the encoded round trip, bad documents.
class TestDocuments(unittest.TestCase):
    # Each put writes its id's next version and moves its head, versions stay.
    def test_document_heads(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("castle_gatehouse")
        first = store.doc_put(
            "castle_gatehouse", "scene/arrival", _ARRIVAL_BODY
        )
        self.assertEqual(first, "/castle_gatehouse/scene/arrival/1")
        self.assertEqual(
            store.doc_head("castle_gatehouse", "scene/arrival"), first
        )
        self.assertEqual(
            store.kv_get(first).data, _ARRIVAL_TEXT.encode("utf-8")
        )
        moat = store.doc_put("castle_gatehouse", "scene/moat", _ARRIVAL_BODY)
        self.assertEqual(moat, "/castle_gatehouse/scene/moat/1")
        changed = dict(_ARRIVAL_BODY)
        changed["subtitle"] = "The keeper waves."
        second = store.doc_put("castle_gatehouse", "scene/arrival", changed)
        self.assertEqual(second, "/castle_gatehouse/scene/arrival/2")
        self.assertEqual(
            store.doc_head("castle_gatehouse", "scene/arrival"), second
        )
        self.assertEqual(
            store.doc_head("castle_gatehouse", "scene/moat"), moat
        )
        self.assertEqual(store.doc_get(first), _ARRIVAL_BODY)
        self.assertEqual(
            _json_text(store.doc_get(first)), _json_text(_ARRIVAL_BODY)
        )
        self.assertEqual(
            _json_text(store.doc_get("scene/arrival/2", "castle_gatehouse")),
            _json_text(changed),
        )
        message = _text_get("substrate_id_missing_absent")
        _error_check(
            self,
            LookupError,
            message,
            lambda: store.doc_head("castle_gatehouse", "scene/absent"),
        )
        message = _text_get("substrate_key_missing_version")
        _error_check(
            self,
            LookupError,
            message,
            lambda: store.doc_get("/castle_gatehouse/scene/arrival/3"),
        )
        message = _text_get("substrate_document_ref_head")
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_get("/castle_gatehouse/scene/arrival"),
        )

    # Encoding moves refs into shared headers and decoding restores the text.
    def test_round_trip(self) -> None:
        normal: dict[int | str, Any] = {
            0: {"t": "scene", "v": 2},
            "subtitle": "Fog " + _WIDE_TEXT,
            "image": "/_files/fog.png",
            "links": [
                "/metaverse/world",
                {"to": "/_files/fog.png", "note": "/not a ref"},
            ],
            "local": "world",
            "slash": "/",
            "count": 3,
            "ratio": 0.5,
            "shown": True,
            "none": None,
        }
        expected: dict[int | str, Any] = {
            0: {"t": "scene", "v": 2},
            1: "/_files/fog.png",
            2: "/metaverse/world",
            "subtitle": "Fog " + _WIDE_TEXT,
            "image": {"$ref": 1},
            "links": [{"$ref": 2}, {"to": {"$ref": 1}, "note": "/not a ref"}],
            "local": "world",
            "slash": "/",
            "count": 3,
            "ratio": 0.5,
            "shown": True,
            "none": None,
        }
        encoded = substrate.doc_encode(normal)
        self.assertEqual(encoded, expected)
        self.assertEqual(_json_text(encoded), _json_text(expected))
        decoded = substrate.doc_decode(encoded)
        self.assertEqual(decoded, normal)
        self.assertEqual(_json_text(decoded), _json_text(normal))
        store = _store_make(self, _root_make(self))
        store.db_create("metaverse")
        ref = store.doc_put("metaverse", "fog", encoded)
        self.assertEqual(ref, "/metaverse/fog/1")
        stored = store.doc_get(ref)
        self.assertEqual(_json_text(stored), _json_text(expected))
        self.assertEqual(
            _json_text(substrate.doc_decode(stored)), _json_text(normal)
        )

    # Documents that would not round trip, or are malformed, raise.
    def test_documents_bad(self) -> None:
        normals: list[tuple[dict[int | str, Any], str]] = [
            ({"subtitle": "x"}, _text_get("substrate_header_missing")),
            (
                {0: {"t": "scene", "v": 0}},
                _text_get("substrate_header_bad_version"),
            ),
            ({0: {"v": 2}}, _text_get("substrate_header_bad_typeless")),
            (
                {0: {"t": "scene", "x": 1}},
                _text_get("substrate_header_bad_field"),
            ),
            ({0: "scene"}, _text_get("substrate_header_bad_text")),
            (
                {0: {"t": "scene"}, 1: "/a/b"},
                _text_get("substrate_header_normal"),
            ),
            (
                {0: {"t": "scene"}, "12": "x"},
                _text_get("substrate_key_digits_encode"),
            ),
            (
                {0: {"t": "scene"}, "x": {"$ref": 1}},
                _text_get("substrate_ref_shape"),
            ),
        ]
        for normal, message in normals:
            _error_check(
                self, ValueError, message, lambda: substrate.doc_encode(normal)
            )
        encodeds: list[tuple[dict[int | str, Any], str]] = [
            (
                {0: {"t": "scene"}, 1: "/a/b", "x": {"$ref": 2}},
                _text_get("substrate_ref_index_two"),
            ),
            (
                {0: {"t": "scene"}, 2: "/a/b", "x": {"$ref": 2}},
                _text_get("substrate_header_gap"),
            ),
            (
                {0: {"t": "scene"}, 1: 5, "x": {"$ref": 1}},
                _text_get("substrate_header_ref"),
            ),
            (
                {0: {"t": "scene"}, 1: "world", "x": {"$ref": 1}},
                _text_get("substrate_header_ref"),
            ),
            (
                {0: {"t": "scene"}, 1: "/a/b", "x": {"$ref": True}},
                _text_get("substrate_ref_index_true"),
            ),
            (
                {0: {"t": "scene"}, "07": "x"},
                _text_get("substrate_key_digits_decode"),
            ),
        ]
        for encoded, message in encodeds:
            _error_check(
                self,
                ValueError,
                message,
                lambda: substrate.doc_decode(encoded),
            )
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        message = _text_get("substrate_id_empty")
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_put("alpha", "", {0: {"t": "note"}}),
        )
        message = _text_get("substrate_header_gap")
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_put(
                "alpha", "gap", {0: {"t": "note"}, 2: "/a/b"}
            ),
        )
        self.assertEqual(store.kv_list("alpha", ""), [])

    # A string whose key part holds white space stays text in the body.
    def test_spaces_kept(self) -> None:
        lines = ["/me/ waves and leaves", "/me/waves and\nleaves", "/me/a b"]
        normal: dict[int | str, Any] = {
            0: {"t": "scene"},
            "subtitle": "/me waves/ and leaves",
            "lines": lines,
            "image": "/me/waves",
        }
        expected: dict[int | str, Any] = {
            0: {"t": "scene"},
            1: "/me/waves",
            "subtitle": "/me waves/ and leaves",
            "lines": lines,
            "image": {"$ref": 1},
        }
        self.assertEqual(substrate.doc_encode(normal), expected)
        self.assertEqual(substrate.doc_decode(expected), normal)
        message = _text_get("substrate_header_ref")
        for text in ["/me waves/ and leaves", *lines]:
            _error_check(
                self,
                ValueError,
                message,
                lambda: substrate.doc_decode({0: {"t": "scene"}, 1: text}),
            )

    # A put whose next version is already a row raises and moves no head.
    def test_version_exists(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        store.kv_put("/alpha/note/1", b"{}")
        message = _text_get("substrate_version_exists")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.doc_put("alpha", "note", {0: {"t": "note"}}),
        )
        message = _text_get("substrate_id_missing_note")
        _error_check(
            self, LookupError, message, lambda: store.doc_head("alpha", "note")
        )
        self.assertEqual(store.kv_get("/alpha/note/1").data, b"{}")

    # A nested document is stored as the body's text in its doc.put line.
    def test_nested_text(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        ref = store.doc_put("alpha", "nest", _NESTED_BODY)
        stored = cast(bytes, store.kv_get(ref).data)
        line = harness.gold_get(f"{_GOLD_ID}.lines.doc_put")
        self.assertEqual(
            _line_bytes(line),
            b'{"0":{"t":"doc.put"},"body":'
            + stored
            + b',"db":"alpha","id":"nest"}\r',
        )
        self.assertEqual(store.doc_get(ref), _NESTED_BODY)
        digits: dict[int | str, Any] = {0: {"t": "note"}, "x": {"12": 1}}
        message = _text_get("substrate_key_refused")
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_put("alpha", "digits", digits),
        )
        keys = [row.key for row in store.kv_list("alpha", "")]
        self.assertEqual(keys, ["nest/1"])


# Turns: appended in order and listed.
class TestTurns(unittest.TestCase):
    # Turns number from 1 in their scene, a bad scene or content raises.
    def test_turns_append(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("metaverse")
        user = '{"role":"user","content":"1"}'
        answer = _json_text({"role": "assistant", "content": _WIDE_TEXT})
        self.assertEqual(store.turn_append(_SCENE, "user", user), 1)
        self.assertEqual(store.turn_append(_SCENE, "assistant", answer), 2)
        self.assertEqual(
            store.turn_list(_SCENE),
            [
                substrate.TurnRow(_SCENE, 1, "user", user),
                substrate.TurnRow(_SCENE, 2, "assistant", answer),
            ],
        )
        elsewhere = "/metaverse/elsewhere/1"
        self.assertEqual(store.turn_list(elsewhere), [])
        self.assertEqual(store.turn_append(elsewhere, "user", user), 1)
        self.assertEqual(
            store.turn_list(elsewhere),
            [substrate.TurnRow(elsewhere, 1, "user", user)],
        )
        scenes = {"internal": "hyperposition/1", "value": "/metaverse/world"}
        for case, scene in scenes.items():
            message = _text_get(f"substrate_scene_bad_{case}")
            _error_check(
                self,
                ValueError,
                message,
                lambda: store.turn_append(scene, "user", user),
            )
        _error_check(
            self,
            sqlite3.IntegrityError,
            "CHECK constraint failed: json_valid(content)",
            lambda: store.turn_append(_SCENE, "user", "not json"),
        )
        self.assertEqual([row.n for row in store.turn_list(_SCENE)], [1, 2])


# SQL: the results of statements, the changes they make, a trigger's refusal.
class TestSql(unittest.TestCase):
    # Statements return columns, rows and changes, a read changing none.
    def test_sql_results(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("castle")
        results = store.sql_run(
            "castle",
            [
                _statement_make(_WORLD_SQL),
                _statement_make(
                    "INSERT INTO world VALUES (?, ?)",
                    "castle_world",
                    "The castle",
                ),
            ],
        )
        self.assertEqual(
            results,
            [substrate.SqlResult([], [], 0), substrate.SqlResult([], [], 1)],
        )
        selected = store.sql_run(
            "castle", [_statement_make("SELECT name, title FROM world")]
        )
        self.assertEqual(
            selected,
            [
                substrate.SqlResult(
                    ["name", "title"], [["castle_world", "The castle"]], 0
                )
            ],
        )

    # A trigger raising a string's name raises that string, adding no row.
    def test_trigger_name(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("metaverse")
        store.sql_run(
            "metaverse",
            [
                _statement_make(_UNIVERSE_SQL),
                _statement_make(_UNIVERSE_TRIGGER),
                _statement_make(
                    _UNIVERSE_INSERT,
                    "castle",
                    "The castle",
                    "player",
                    "castle_world",
                ),
            ],
        )
        second = _statement_make(
            _UNIVERSE_INSERT, "tower", "The tower", "player", "castle_world"
        )
        with self.assertRaises(ValueError) as caught:
            store.sql_run("metaverse", [second])
        message = _text_get("agent_content_ambiguous")
        self.assertEqual(str(caught.exception), message)
        cause = caught.exception.__cause__
        self.assertIsInstance(cause, sqlite3.IntegrityError)
        rows = _rows_query(store, "metaverse", "SELECT name FROM universe")
        self.assertEqual(rows, [["castle"]])


# Transactions: writes in several databases commit or roll back together.
class TestTransactions(unittest.TestCase):
    # Writes in one `transaction_run` commit together or roll back together.
    def test_transaction_whole(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        store.db_create("beta")

        # Puts three values in two databases.
        def puts_three() -> None:
            store.kv_put("/alpha/a", b"1")
            store.kv_put("/beta/b", b"2")
            store.kv_put("/alpha/c", b"3")

        store.transaction_run(puts_three)
        keys = [row.key for row in store.kv_list("alpha", "")]
        self.assertEqual(keys, ["a", "c"])
        keys = [row.key for row in store.kv_list("beta", "")]
        self.assertEqual(keys, ["b"])

        # Puts a value to the cache, deletes another, then raises.
        def puts_raise() -> None:
            store.kv_put("/alpha/d", _VALUE_OVER)
            store.kv_delete("/alpha/a")
            raise RuntimeError("rolled back")

        _error_check(
            self,
            RuntimeError,
            "rolled back",
            lambda: store.transaction_run(puts_raise),
        )
        self.assertEqual(store.kv_get("/alpha/a").data, b"1")
        message = _text_get("substrate_key_missing_rolled")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/d")
        )
        self.assertEqual(store.kv_check("alpha"), 1)

    # A failure after one of two databases was written rolls both back.
    def test_transaction_split(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        store.db_create("beta")

        # Puts a value in one database, then writes and fails in the other.
        def writes_split() -> None:
            store.kv_put("/alpha/a", b"1")
            store.sql_run(
                "beta",
                [
                    _statement_make("CREATE TABLE note (x TEXT)"),
                    _statement_make("INSERT INTO absent VALUES (1)"),
                ],
            )

        _error_check(
            self,
            sqlite3.OperationalError,
            "no such table: absent",
            lambda: store.transaction_run(writes_split),
        )
        message = _text_get("substrate_key_missing_split")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/a")
        )
        self.assertEqual(
            _tables_list(store, "beta"), ["_head", "_kv", "_meta", "_turn"]
        )


# Snapshots with the held cache files, restored from bytes or files.
class TestSnapshot(unittest.TestCase):
    # Restores `alpha` on a second root with the first of its two cache files.
    def files_lost_check(self, streamed: bool) -> None:
        first_root = _root_make(self)
        first = _store_make(self, first_root)
        values = _alpha_fill(first)
        image = first.db_snapshot("alpha")
        big = [values["/alpha/one"], values["/alpha/two"]]
        expected = sorted(_cache_file(first_root, value) for value in big)
        self.assertEqual(image.files, expected)
        refs = {
            hashlib.sha256(value).hexdigest(): ref
            for ref, value in values.items()
        }
        came = refs[os.path.basename(image.files[0])]
        lost = refs[os.path.basename(image.files[1])]
        with open(image.files[0], "rb") as file:
            sent = file.read()
        root = _root_make(self)
        second = _store_make(self, root)
        if streamed:
            sink = os.path.join(root, "cache", "sink")
            with open(sink, "wb") as file:
                file.write(sent)
            second.db_restore("alpha", image.data, [sink])
            self.assertFalse(os.path.exists(sink))
        else:
            second.db_restore("alpha", image.data, [sent])
        self.assertEqual(_value_bytes(second.kv_get(came)), values[came])
        small = second.kv_get("/alpha/small").data
        self.assertEqual(small, values["/alpha/small"])
        lost_hex = os.path.basename(image.files[1])
        message = (
            _text_get("substrate_file_lost_restored")
            .replace("{0}", lost)
            .replace("{1}", lost_hex)
        )
        _error_check(self, LookupError, message, lambda: second.kv_get(lost))
        rows = [
            substrate.KvRow(
                ref.removeprefix("/alpha/"),
                len(value),
                hashlib.sha256(value).digest(),
            )
            for ref, value in values.items()
        ]
        self.assertEqual(second.kv_list("alpha", ""), rows)
        second.kv_put(lost, b"again")
        self.assertEqual(second.kv_get(lost).data, b"again")
        self.assertEqual(second.kv_check("alpha"), 0)

    # A restore brings back the rows of the snapshot.
    def test_snapshot_restore(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.kv_put("/alpha/a", b"one")
        store.sql_run(
            "alpha",
            [
                _statement_make("CREATE TABLE t (x TEXT)"),
                _statement_make("INSERT INTO t VALUES (?)", _WIDE_TEXT),
            ],
        )
        image = store.db_snapshot("alpha")
        data = image.data
        self.assertEqual(data[:16], b"SQLite format 3\x00")
        self.assertEqual(image.files, [])
        path = os.path.join(root, "alpha.sqlite")
        dump = _database_dump(path)
        store.kv_put("/alpha/a", b"two")
        store.kv_put("/alpha/b", b"three")
        store.sql_run("alpha", [_statement_make("DELETE FROM t")])
        self.assertIsNone(store.db_restore("alpha", data, []))
        self.assertEqual(store.kv_get("/alpha/a").data, b"one")
        message = _text_get("substrate_key_missing_restored")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/b")
        )
        self.assertEqual(_database_dump(path), dump)
        other = _root_make(self)
        second = _store_make(self, other)
        sink = os.path.join(other, "cache", "sink")
        with open(sink, "wb") as file:
            file.write(data)
        second.db_restore("alpha", sink, [])
        self.assertFalse(os.path.exists(sink))
        self.assertEqual(
            _database_dump(os.path.join(other, "alpha.sqlite")), dump
        )

    # A file without the substrate's tables raises and the old one stays open.
    def test_restore_foreign(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.kv_put("/alpha/a", b"one")
        listed = sorted(os.listdir(root))
        memory = sqlite3.connect(":memory:")
        self.addCleanup(memory.close)
        memory.execute("CREATE TABLE note (x TEXT)")
        data = memory.serialize()
        message = _text_get("substrate_schema_partial_none")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.db_restore("alpha", data, []),
        )
        self.assertEqual(store.db_list(), ["alpha"])
        self.assertEqual(store.kv_get("/alpha/a").data, b"one")
        self.assertEqual(sorted(os.listdir(root)), listed)

    # Two snapshots of one database taken apart hold their own bytes.
    def test_snapshots_apart(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        first = store.db_snapshot("alpha")
        store.kv_put("/alpha/a", b"one")
        second = store.db_snapshot("alpha")
        self.assertNotEqual(first.data, second.data)

    # A cached value stays held through a snapshot and its restore.
    def test_value_held(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.kv_put("/alpha/big", _VALUE_OVER)
        path = _cache_file(root, _VALUE_OVER)
        image = store.db_snapshot("alpha")
        self.assertEqual(image.files, [path])
        store.db_restore("alpha", image.data, [])
        digest = hashlib.sha256(_VALUE_OVER).digest()
        self.assertEqual(
            store.kv_get("/alpha/big"),
            substrate.KvValue(path, len(_VALUE_OVER), digest),
        )
        with open(path, "rb") as file:
            self.assertEqual(file.read(), _VALUE_OVER)

    # A restore with one of its two cache files streamed loses one value.
    def test_restore_files_lost(self) -> None:
        self.files_lost_check(True)

    # The same restore with the cache file given as its bytes.
    def test_restore_bytes(self) -> None:
        self.files_lost_check(False)

    # A snapshot leaves out a deleted cache file, without raising.
    def test_snapshot_missing_file(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        values = _alpha_fill(store)
        os.remove(_cache_file(root, values["/alpha/one"]))
        image = store.db_snapshot("alpha")
        kept = _cache_file(root, values["/alpha/two"])
        self.assertEqual(image.files, [kept])


# A kill between a cache file and its row.
class TestCrash(unittest.TestCase):
    # The killed put leaves a file and no row, and `kv_check` removes it.
    def test_kill_between(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.db_close("alpha")
        pid = os.fork()
        if pid == 0:
            _child_put(root)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGXFSZ)
        path = _cache_file(root, _VALUE_OVER)
        self.assertTrue(os.path.isfile(path))
        store.db_open("alpha")
        message = _text_get("substrate_key_missing_killed")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/big")
        )
        self.assertEqual(store.kv_check("alpha"), 1)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(store.kv_check("alpha"), 0)
