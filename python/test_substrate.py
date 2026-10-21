# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of the server substrate on scratch roots under build/: the tables on
# first use, both ref forms, documents and heads, overflow to the cache, a
# kill between a cache file and its row, snapshots and the pieces of a kept
# one, turns, SQL, the rules of `seq` and a recorded sequence of forwarded
# operations replayed.

import base64, hashlib, jslb, json, math, os, signal, sqlite3, substrate
import tempfile, unittest, unittest.mock
from collections.abc import Callable
from i18n import i18n
from typing import Any, NoReturn, cast

# The checkout's build directory, where each test makes its scratch roots.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The `overflow_bytes` of the settings, 128 KiB.
_OVERFLOW_BYTES = 131072

# The hyperposition scene, whose conversation the turn tests append to.
_SCENE = "/metaverse/hyperposition/1"

# Text beyond ASCII for keys and values, built from its code points.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)

# A value of exactly `overflow_bytes`, which stays in its row.
_VALUE_EXACT = bytes(range(256)) * (_OVERFLOW_BYTES // 256)

# A value one byte over `overflow_bytes`, which goes to the cache.
_VALUE_OVER = _VALUE_EXACT + bytes(1)

# A map of 204800 bytes, over `overflow_bytes`.
_MAP_BYTES = bytes(range(256)) * 800

# The bytes of a piece that the tests ask of a kept snapshot.
_PIECE_BYTES = 4096

# The real `os.replace`, which the patched one of the forked child calls.
_OS_REPLACE = os.replace

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

# A document with integer keys below the top level, out of order.
_NESTED_BODY: dict[int | str, Any] = {
    0: {"t": "nest"},
    1: "/_files/fog.png",
    "inner": {
        "b": 1,
        2: _WIDE_TEXT,
        "a": [{"z": None, 0: 0.5}],
        1: {"$ref": 1},
    },
    "count": -3,
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

# The world table of the castle universe database.
_WORLD_SQL = (
    "CREATE TABLE world (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT"
)

# The region table of the castle world database.
_REGION_SQL = (
    "CREATE TABLE region"
    " (name TEXT PRIMARY KEY, tide INTEGER NOT NULL DEFAULT 0) STRICT"
)

# Each database the replay starts from: its `seq` and its tables.
_HELLO_DATABASES: dict[str, tuple[int, list[str]]] = {
    "_files": (1, []),
    "metaverse": (5, [_UNIVERSE_SQL]),
}

# The arguments of the first tool call, the bootstrap script run.
_SCRIPT_ARGUMENTS = (
    '{"name":"bootstrap","args":{"universe":"castle","title":"The castle",'
    '"world":"castle_world","region":"castle_gatehouse"}}'
)

# The prompt of the image of the arrival scene.
_IMAGE_PROMPT = (
    "A rain dark castle gatehouse at dusk seen from the far side of a moat,"
    " one lantern lit, painted, wide still frame, no people"
)

# The arguments of the second tool call, the image made.
_IMAGE_ARGUMENTS = (
    '{"prompt":"' + _IMAGE_PROMPT + '","key":"/_files/gatehouse/arrival.png"}'
)

# The arguments of the third tool call, the arrival scene put.
_DOCUMENT_ARGUMENTS = (
    '{"db":"castle_gatehouse","id":"scene/arrival","body":'
    + _ARRIVAL_TEXT
    + "}"
)

# The arguments of the fourth tool call, the current scene of the world.
_SCENE_ARGUMENTS = (
    '{"ref":"/castle_world/scene","text":"/castle_gatehouse/scene/arrival/1"}'
)

# The arguments of the fifth tool call, the arrival scene rendered.
_RENDER_ARGUMENTS = (
    '{"image":"/_files/gatehouse/arrival.png","subtitle":"'
    + _ARRIVAL_SUBTITLE
    + '"}'
)

# A small PNG image as a provider answers it, its `b64_json`.
_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAH0lEQVR42mP4jwQYkAAuc"
    "YZBqGGQO48oDaPxMCg0AADZV36QzYI8swAAAABJRU5ErkJggg=="
)

# The bytes of that image, which the replay puts in `_files`.
_IMAGE_BYTES = base64.b64decode(_IMAGE_BASE64)

# A script that advances the tide in the region table of the world.
_STEP_SCRIPT = (
    "// Advances the tide by args.hours in the region table of the world.\n"
    'const results = engine.store.sql_run("castle_world", [\n'
    '  {sql: "UPDATE region SET tide = tide + ? WHERE name = ?",\n'
    '    params: [args.hours, "castle_gatehouse"]},\n'
    "]);\n"
    'engine.log(1, "tide advanced by " + args.hours);\n'
    "return {changes: results[0].changes};\n"
)

# The user's first message.
_MESSAGE_USER: dict[str, Any] = {"role": "user", "content": "1"}

# The assistant's message with the first tool call, the bootstrap script.
_MESSAGE_SCRIPT: dict[str, Any] = {
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

# The assistant's message with the second tool call, the image.
_MESSAGE_IMAGE: dict[str, Any] = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "call_2",
            "type": "function",
            "function": {
                "name": "browser.image_make",
                "arguments": _IMAGE_ARGUMENTS,
            },
        }
    ],
}

# The assistant's message with the three tool calls of the arrival scene.
_MESSAGE_SCENE: dict[str, Any] = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "call_3",
            "type": "function",
            "function": {
                "name": "browser.doc_put",
                "arguments": _DOCUMENT_ARGUMENTS,
            },
        },
        {
            "id": "call_4",
            "type": "function",
            "function": {
                "name": "browser.kv_put",
                "arguments": _SCENE_ARGUMENTS,
            },
        },
        {
            "id": "call_5",
            "type": "function",
            "function": {
                "name": "browser.render",
                "arguments": _RENDER_ARGUMENTS,
            },
        },
    ],
}

# The assistant's last message, the subtitle of the arrival scene.
_MESSAGE_FINAL: dict[str, Any] = {
    "role": "assistant",
    "content": _ARRIVAL_SUBTITLE,
}

# The forwarded operations to replay: each type, `since`, fields and `seq`.
_RECORDED: list[tuple[str, int, dict[str, Any], int]] = [
    (
        "turn.append",
        5,
        {"scene": _SCENE, "role": "user", "content": _MESSAGE_USER},
        6,
    ),
    (
        "turn.append",
        6,
        {"scene": _SCENE, "role": "assistant", "content": _MESSAGE_SCRIPT},
        7,
    ),
    ("db.create", 0, {"db": "castle"}, 0),
    (
        "sql.run",
        0,
        {
            "db": "castle",
            "statements": [
                {"sql": _WORLD_SQL, "params": []},
                {
                    "sql": "INSERT INTO world VALUES (?, ?)",
                    "params": ["castle_world", "The castle"],
                },
            ],
        },
        1,
    ),
    ("db.create", 0, {"db": "castle_world"}, 0),
    (
        "sql.run",
        0,
        {
            "db": "castle_world",
            "statements": [
                {"sql": _REGION_SQL, "params": []},
                {
                    "sql": "INSERT INTO region (name) VALUES (?)",
                    "params": ["castle_gatehouse"],
                },
            ],
        },
        1,
    ),
    ("db.create", 0, {"db": "castle_gatehouse"}, 0),
    (
        "sql.run",
        7,
        {
            "db": "metaverse",
            "statements": [
                {
                    "sql": "INSERT INTO universe VALUES (?, ?, ?, ?)",
                    "params": [
                        "castle",
                        "The castle",
                        "player",
                        "castle_world",
                    ],
                }
            ],
        },
        8,
    ),
    ("kv.put", 8, {"k": "/metaverse/world", "data": b"castle_world"}, 9),
    (
        "turn.append",
        9,
        {"scene": _SCENE, "role": "assistant", "content": _MESSAGE_IMAGE},
        10,
    ),
    (
        "kv.put",
        1,
        {"k": "/_files/gatehouse/arrival.png", "data": _IMAGE_BYTES},
        2,
    ),
    (
        "turn.append",
        10,
        {"scene": _SCENE, "role": "assistant", "content": _MESSAGE_SCENE},
        11,
    ),
    (
        "doc.put",
        0,
        {
            "db": "castle_gatehouse",
            "id": "scene/arrival",
            "body": _ARRIVAL_BODY,
        },
        1,
    ),
    (
        "kv.put",
        1,
        {
            "k": "/castle_world/scene",
            "data": b"/castle_gatehouse/scene/arrival/1",
        },
        2,
    ),
    (
        "turn.append",
        11,
        {"scene": _SCENE, "role": "assistant", "content": _MESSAGE_FINAL},
        12,
    ),
    (
        "sql.run",
        1,
        {
            "db": "castle",
            "statements": [
                {
                    "sql": "UPDATE world SET title = ? WHERE name = ?",
                    "params": ["The castle at dusk", "castle_world"],
                }
            ],
        },
        2,
    ),
    ("kv.put", 2, {"k": "/_files/maps/castle.bin", "data": _MAP_BYTES}, 3),
]

# A put that finds the server's `seq` one ahead.
_DESYNC: tuple[str, int, dict[str, Any], int] = (
    "kv.put",
    3,
    {"k": "/_files/script/step_tide.js", "data": _STEP_SCRIPT.encode()},
    4,
)

# The English text of the desync message for that put.
_DESYNC_MESSAGE = "kv.put: since 3 is not seq 4 of _files"


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


# The statements of a forwarded `sql.run`, each `sql` and `params`.
def _statements_parse(
    statements: list[dict[str, Any]],
) -> list[substrate.SqlStatement]:
    return [substrate.SqlStatement(**statement) for statement in statements]


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


# Makes the databases the replay starts from, each at its `seq`.
def _hello_make(root: str) -> None:
    for name, (seq, tables) in _HELLO_DATABASES.items():
        statements = [_statement_make(sql) for sql in tables]
        statements.append(
            _statement_make(
                "UPDATE _meta SET value = ? WHERE name = 'seq'", str(seq)
            )
        )
        _file_make(os.path.join(root, name + ".sqlite"), True, statements)


# Writes a row of `alpha`, then makes the call in the same transaction.
def _busy_call(store: substrate.Store, call: Callable[[], object]) -> None:
    store.kv_put("/alpha/busy", b"busy")
    call()


# The canonical JSON text of a value, as the substrate stores it.
def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# The path of the cache file of a value under a root.
def _cache_file(root: str, value: bytes) -> str:
    return os.path.join(root, "cache", hashlib.sha256(value).hexdigest())


# Reads a kept snapshot whole in pieces of `_PIECE_BYTES`, the last shorter.
def _pieces_read(
    store: substrate.Store, head: substrate.SnapshotHead
) -> bytes:
    data = b""
    while len(data) < head.size:
        size = min(_PIECE_BYTES, head.size - len(data))
        data += store.snapshot_read(head.snapshot, len(data), size)
    return data


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
        with open(os.path.join(directory, name), "rb") as file:
            contents.append((name, file.read()))
    return contents


# The database a recorded operation modifies.
def _target_database(fields: dict[str, Any]) -> str:
    if "db" in fields:
        return fields["db"]
    ref = fields["k"] if "k" in fields else fields["scene"]
    return cast(str, substrate.ref_split(ref).db)


# Makes on a store the direct call a modifier made for a recorded operation.
def _modifier_call(
    store: substrate.Store, kind: str, fields: dict[str, Any]
) -> None:
    calls: dict[str, Callable[[], object]] = {
        "kv.put": lambda: store.kv_put(fields["k"], fields["data"]),
        "doc.put": lambda: store.doc_put(
            fields["db"], fields["id"], fields["body"]
        ),
        "db.create": lambda: store.db_create(fields["db"]),
        "turn.append": lambda: store.turn_append(
            fields["scene"], fields["role"], _json_text(fields["content"])
        ),
        "sql.run": lambda: store.sql_run(
            fields["db"], _statements_parse(fields["statements"])
        ),
    }
    calls[kind]()


# Renames as `os.replace` does, then kills the process before the row.
def _replace_kill(source: str, target: str) -> None:
    _OS_REPLACE(source, target)
    os.kill(os.getpid(), signal.SIGKILL)


# In the forked child: puts a value and is killed as its cache file lands.
def _child_put(root: str, value: bytes) -> NoReturn:
    try:
        store = substrate.Store(root, _OVERFLOW_BYTES)
        store.db_open("alpha")
        setattr(os, "replace", _replace_kill)
        store.kv_put("/alpha/big", value)
    finally:
        os._exit(1)


# Databases: the tables on first use, names, creating, opening, dropping.
class TestDatabases(unittest.TestCase):
    # A new database gets the substrate's tables, `seq` 0 and `schema` 1.
    def test_tables_created(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        self.assertEqual(
            _tables_list(store, "alpha"), ["_head", "_kv", "_meta", "_turn"]
        )
        rows = _rows_query(
            store, "alpha", "SELECT name, value FROM _meta ORDER BY name"
        )
        self.assertEqual(rows, [["schema", "1"], ["seq", "0"]])
        self.assertEqual(store.db_list(), ["alpha"])
        self.assertEqual(store.seq_get("alpha"), 0)

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
        self.assertEqual(store.db_open("beta"), 0)
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
        names = ["", "1abc", "a-b", "a b", "a.b", "a/b", "caf" + chr(0xE9)]
        for name in names:
            message = i18n("substrate.name_bad", name)
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
        message = i18n("substrate.db_open", "alpha")
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
        message = i18n("substrate.db_closed", "gamma")
        _error_check(
            self, LookupError, message, lambda: store.db_close("gamma")
        )
        self.assertEqual(store.seq_get("alpha"), 0)

    # A create whose open fails removes its file, so a later create succeeds.
    def test_create_failed(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        failure = RuntimeError("schema failure made by the test")
        with unittest.mock.patch.object(
            substrate, "schema_apply", side_effect=failure
        ):
            with self.assertRaises(RuntimeError) as caught:
                store.db_create("alpha")
        self.assertIs(caught.exception, failure)
        self.assertEqual(os.listdir(root), ["cache"])
        self.assertEqual(store.db_list(), [])
        store.db_create("alpha")
        self.assertEqual(store.seq_get("alpha"), 0)

    # A file with only some of the substrate's tables raises, its tables kept.
    def test_schema_partial(self) -> None:
        root = _root_make(self)
        path = os.path.join(root, "beta.sqlite")
        _file_make(path, False, [_statement_make(_META_SQL)])
        store = _store_make(self, root)
        message = i18n("substrate.schema_partial", ["_meta"])
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
        message = i18n("substrate.schema_version", ("2",), "1")
        _error_check(
            self, RuntimeError, message, lambda: store.db_open("beta")
        )
        self.assertEqual(store.db_list(), [])

    # Closing, dropping or restoring a database a transaction wrote raises.
    def test_database_busy(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        data = store.db_snapshot("alpha")[0]
        listed = sorted(os.listdir(root))
        message = i18n("substrate.db_busy", "alpha")
        calls: list[Callable[[], object]] = [
            lambda: store.db_close("alpha"),
            lambda: store.db_drop("alpha"),
            lambda: store.db_restore("alpha", data),
        ]
        for call in calls:
            _error_check(
                self,
                RuntimeError,
                message,
                lambda: store.transaction_run(lambda: _busy_call(store, call)),
            )
            self.assertEqual(store.db_list(), ["alpha"])
            self.assertEqual(store.seq_get("alpha"), 0)
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
        message = i18n("substrate.wal_left", "alpha")
        _error_check(
            self, RuntimeError, message, lambda: store.db_drop("alpha")
        )
        self.assertEqual(store.db_list(), [])
        self.assertTrue(os.path.isfile(path))
        reader.execute("COMMIT")
        reader.close()
        self.assertEqual(store.db_open("alpha"), 0)

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
        refs = [
            "",
            "/",
            "//key",
            "/metaverse",
            "/metaverse/",
            "/1db/key",
            "/d-b/key",
            "/caf" + chr(0xE9) + "/key",
        ]
        for ref in refs:
            message = i18n("substrate.ref_bad", ref)
            _error_check(
                self, ValueError, message, lambda: substrate.ref_split(ref)
            )

    # An internal ref needs a database and an external ref takes none.
    def test_ref_database(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        message = i18n("substrate.ref_internal", "world")
        _error_check(
            self, ValueError, message, lambda: store.kv_put("world", b"x")
        )
        message = i18n("substrate.ref_both", "/alpha/world", "alpha")
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
        message = i18n("substrate.db_closed", "beta")
        _error_check(
            self,
            LookupError,
            message,
            lambda: store.kv_put("/beta/world", b"x"),
        )
        message = i18n("substrate.document_ref", "/alpha/world")
        _error_check(
            self, ValueError, message, lambda: store.doc_get("/alpha/world")
        )
        self.assertEqual(store.seq_get("alpha"), 0)


# Values: both ref forms, the overflow limit, shared cache files, streams.
class TestValues(unittest.TestCase):
    # A value put by one ref form is read by the other, listed and deleted.
    def test_refs_both(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        key = "greeting/" + _WIDE_TEXT
        value = ("hello " + _WIDE_TEXT).encode("utf-8")
        digest = hashlib.sha256(value).digest()
        row, seq = store.kv_put("/alpha/" + key, value)
        self.assertEqual(row, substrate.KvRow(key, len(value), digest))
        self.assertEqual(seq, 1)
        self.assertEqual(
            store.kv_get(key, "alpha"),
            substrate.KvValue(value, len(value), digest),
        )
        self.assertEqual(store.kv_put("place/a/b", b"world", "alpha")[1], 2)
        self.assertEqual(store.kv_get("/alpha/place/a/b").data, b"world")
        self.assertEqual(store.kv_list("alpha", "greeting/"), [row])
        keys = [listed.key for listed in store.kv_list("alpha", "")]
        self.assertEqual(keys, [key, "place/a/b"])
        self.assertEqual(store.kv_delete(key, "alpha"), 3)
        message = i18n("substrate.key_missing", key, "alpha")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/" + key)
        )

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
        row, seq = store.kv_put("/alpha/streamed", sink)
        self.assertFalse(os.path.exists(sink))
        digest = hashlib.sha256(_VALUE_OVER).digest()
        self.assertEqual(
            row, substrate.KvRow("streamed", _OVERFLOW_BYTES + 1, digest)
        )
        self.assertEqual(seq, 1)
        self.assertEqual(
            store.kv_get("/alpha/streamed").data,
            _cache_file(root, _VALUE_OVER),
        )
        small = os.path.join(root, "cache", "small")
        with open(small, "wb") as file:
            file.write(_VALUE_EXACT)
        message = i18n(
            "substrate.file_small", small, _OVERFLOW_BYTES, _OVERFLOW_BYTES
        )
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.kv_put("/alpha/small", small),
        )
        self.assertEqual(store.seq_get("alpha"), 1)
        self.assertEqual(store.kv_check("alpha"), 1)
        self.assertFalse(os.path.exists(small))


# Documents: versions and heads, the encoded round trip, bad documents.
class TestDocuments(unittest.TestCase):
    # Each put writes the next version and moves the head, versions stay.
    def test_document_heads(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("castle_gatehouse")
        first = store.doc_put(
            "castle_gatehouse", "scene/arrival", _ARRIVAL_BODY
        )
        self.assertEqual(first, ("/castle_gatehouse/scene/arrival/1", 1))
        self.assertEqual(
            store.doc_head("castle_gatehouse", "scene/arrival"), first[0]
        )
        self.assertEqual(
            store.kv_get(first[0]).data, _ARRIVAL_TEXT.encode("utf-8")
        )
        changed = dict(_ARRIVAL_BODY)
        changed["subtitle"] = "The keeper waves."
        second = store.doc_put("castle_gatehouse", "scene/arrival", changed)
        self.assertEqual(second, ("/castle_gatehouse/scene/arrival/2", 2))
        self.assertEqual(
            store.doc_head("castle_gatehouse", "scene/arrival"), second[0]
        )
        self.assertEqual(store.doc_get(first[0]), _ARRIVAL_BODY)
        self.assertEqual(
            _json_text(store.doc_get(first[0])), _json_text(_ARRIVAL_BODY)
        )
        self.assertEqual(
            _json_text(store.doc_get("scene/arrival/2", "castle_gatehouse")),
            _json_text(changed),
        )
        message = i18n(
            "substrate.id_missing", "scene/absent", "castle_gatehouse"
        )
        _error_check(
            self,
            LookupError,
            message,
            lambda: store.doc_head("castle_gatehouse", "scene/absent"),
        )
        message = i18n(
            "substrate.key_missing", "scene/arrival/3", "castle_gatehouse"
        )
        _error_check(
            self,
            LookupError,
            message,
            lambda: store.doc_get("/castle_gatehouse/scene/arrival/3"),
        )
        message = i18n(
            "substrate.document_ref", "/castle_gatehouse/scene/arrival"
        )
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
        ref, seq = store.doc_put("metaverse", "fog", encoded)
        self.assertEqual((ref, seq), ("/metaverse/fog/1", 1))
        stored = store.doc_get(ref)
        self.assertEqual(_json_text(stored), _json_text(expected))
        self.assertEqual(
            _json_text(substrate.doc_decode(stored)), _json_text(normal)
        )

    # Documents that would not round trip, or are malformed, raise.
    def test_documents_bad(self) -> None:
        normals: list[tuple[dict[int | str, Any], str]] = [
            ({"subtitle": "x"}, i18n("substrate.header_missing")),
            (
                {0: {"t": "scene", "v": 0}},
                i18n("substrate.header_bad", {"t": "scene", "v": 0}),
            ),
            ({0: {"v": 2}}, i18n("substrate.header_bad", {"v": 2})),
            (
                {0: {"t": "scene", "x": 1}},
                i18n("substrate.header_bad", {"t": "scene", "x": 1}),
            ),
            ({0: "scene"}, i18n("substrate.header_bad", "scene")),
            (
                {0: {"t": "scene"}, 1: "/a/b"},
                i18n("substrate.header_normal", 1),
            ),
            (
                {0: {"t": "scene"}, "12": "x"},
                i18n("substrate.key_digits", "12"),
            ),
            (
                {0: {"t": "scene"}, "x": {"$ref": 1}},
                i18n("substrate.ref_shape", {"$ref": 1}),
            ),
        ]
        for normal, message in normals:
            _error_check(
                self, ValueError, message, lambda: substrate.doc_encode(normal)
            )
        encodeds: list[tuple[dict[int | str, Any], str]] = [
            (
                {0: {"t": "scene"}, 1: "/a/b", "x": {"$ref": 2}},
                i18n("substrate.ref_index", 2),
            ),
            (
                {0: {"t": "scene"}, 2: "/a/b", "x": {"$ref": 2}},
                i18n("substrate.header_gap", 2),
            ),
            (
                {0: {"t": "scene"}, 1: 5, "x": {"$ref": 1}},
                i18n("substrate.header_ref", 1),
            ),
            (
                {0: {"t": "scene"}, 1: "world", "x": {"$ref": 1}},
                i18n("substrate.header_ref", 1),
            ),
            (
                {0: {"t": "scene"}, 1: "/a/b", "x": {"$ref": True}},
                i18n("substrate.ref_index", True),
            ),
            (
                {0: {"t": "scene"}, "07": "x"},
                i18n("substrate.key_digits", "07"),
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
        message = i18n("substrate.integer_range", 2**53 + 1)
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_put(
                "alpha", "big", {0: {"t": "n"}, "n": 2**53 + 1}
            ),
        )
        message = i18n("substrate.id_empty")
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_put("alpha", "", {0: {"t": "note"}}),
        )
        message = i18n("substrate.header_gap", 2)
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_put(
                "alpha", "gap", {0: {"t": "note"}, 2: "/a/b"}
            ),
        )
        self.assertEqual(store.seq_get("alpha"), 0)

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
        message = i18n("substrate.header_ref", 1)
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
        message = i18n("substrate.version_exists", "note/1", "alpha")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.doc_put("alpha", "note", {0: {"t": "note"}}),
        )
        message = i18n("substrate.id_missing", "note", "alpha")
        _error_check(
            self, LookupError, message, lambda: store.doc_head("alpha", "note")
        )
        self.assertEqual(store.seq_get("alpha"), 1)

    # A nested document is stored as the text the wire's encoder writes.
    def test_nested_text(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        ref = store.doc_put("alpha", "nest", _NESTED_BODY)[0]
        stored = cast(bytes, store.kv_get(ref).data)
        line = jslb.line_make(
            jslb.header_make("doc.put"),
            [],
            db="alpha",
            id="nest",
            body=_NESTED_BODY,
        )
        self.assertEqual(
            list(jslb.line_encode(line)),
            [
                b'{"0":{"t":"doc.put"},"db":"alpha","id":"nest","body":'
                + stored
                + b"}\r"
            ],
        )
        self.assertEqual(store.doc_get(ref), _NESTED_BODY)
        digits: dict[int | str, Any] = {0: {"t": "note"}, "x": {"12": 1}}
        message = i18n("substrate.key_refused", repr("12"))
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_put("alpha", "digits", digits),
        )
        infinite: dict[int | str, Any] = {0: {"t": "note"}, "x": [math.inf]}
        message = i18n("substrate.number_refused", math.inf)
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.doc_put("alpha", "infinite", infinite),
        )
        self.assertEqual(store.seq_get("alpha"), 1)


# Turns: appended in order, listed, and compacted into one summary.
class TestTurns(unittest.TestCase):
    # Turns number from 1 in their scene, a bad scene or content raises.
    def test_turns_append(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("metaverse")
        user = '{"role":"user","content":"1"}'
        answer = _json_text({"role": "assistant", "content": _WIDE_TEXT})
        self.assertEqual(store.turn_append(_SCENE, "user", user), (1, 1))
        self.assertEqual(
            store.turn_append(_SCENE, "assistant", answer), (2, 2)
        )
        self.assertEqual(
            store.turn_list(_SCENE),
            [
                substrate.TurnRow(_SCENE, 1, "user", user),
                substrate.TurnRow(_SCENE, 2, "assistant", answer),
            ],
        )
        self.assertEqual(store.turn_list("/metaverse/elsewhere/1"), [])
        for scene in ("hyperposition/1", "/metaverse/world"):
            message = i18n("substrate.scene_bad", scene)
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
        self.assertEqual(store.seq_get("metaverse"), 2)

    # Compaction replaces turns 1 to `through` by one summary turn at 1.
    def test_turns_compact(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("metaverse")
        for text in ("1", "2", "3", "4"):
            message = _json_text({"role": "user", "content": text})
            store.turn_append(_SCENE, "user", message)
        self.assertEqual(store.turn_compact(_SCENE, 3, "Asked thrice."), 5)
        summary = '{"role":"system","content":"Asked thrice."}'
        fourth = '{"role":"user","content":"4"}'
        self.assertEqual(
            store.turn_list(_SCENE),
            [
                substrate.TurnRow(_SCENE, 1, "system", summary),
                substrate.TurnRow(_SCENE, 4, "user", fourth),
            ],
        )
        self.assertEqual(store.turn_append(_SCENE, "user", fourth), (5, 6))
        message = i18n("substrate.through_bad", 0)
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.turn_compact(_SCENE, 0, "None."),
        )
        message = i18n("substrate.turns_none", "/metaverse/elsewhere/1", 2)
        _error_check(
            self,
            LookupError,
            message,
            lambda: store.turn_compact("/metaverse/elsewhere/1", 2, "None."),
        )
        self.assertEqual(store.seq_get("metaverse"), 6)


# SQL: the results of statements and the changes they count.
class TestSql(unittest.TestCase):
    # Statements return columns, rows and changes, and only writes count.
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
        self.assertEqual(store.seq_get("castle"), 1)
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
        self.assertEqual(store.seq_get("castle"), 1)


# The rules of `seq`: what counts, what does not, and transactions.
class TestSeq(unittest.TestCase):
    # Changes count once each, no change and a failure count nothing.
    def test_seq_rules(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        self.assertEqual(store.kv_put("/alpha/a", b"one")[1], 1)
        self.assertEqual(store.kv_put("/alpha/a", b"one")[1], 1)
        self.assertEqual(store.kv_put("/alpha/a", b"two")[1], 2)
        self.assertEqual(store.kv_delete("/alpha/absent"), 2)
        self.assertEqual(store.kv_delete("/alpha/a"), 3)
        store.sql_run("alpha", [_statement_make("SELECT 1")])
        self.assertEqual(store.seq_get("alpha"), 3)
        store.sql_run("alpha", [_statement_make("CREATE TABLE t (x TEXT)")])
        self.assertEqual(store.seq_get("alpha"), 4)
        store.sql_run(
            "alpha", [_statement_make("INSERT INTO t VALUES (?)", "a")]
        )
        self.assertEqual(store.seq_get("alpha"), 5)
        store.sql_run(
            "alpha",
            [_statement_make("UPDATE t SET x = ? WHERE x = ?", "b", "absent")],
        )
        self.assertEqual(store.seq_get("alpha"), 5)
        _error_check(
            self,
            sqlite3.OperationalError,
            "no such table: absent",
            lambda: store.sql_run(
                "alpha",
                [
                    _statement_make("INSERT INTO t VALUES (?)", "b"),
                    _statement_make("INSERT INTO absent VALUES (1)"),
                ],
            ),
        )
        self.assertEqual(store.seq_get("alpha"), 5)
        rows = _rows_query(store, "alpha", "SELECT x FROM t")
        self.assertEqual(rows, [["a"]])

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
        self.assertEqual(store.seq_get("alpha"), 2)
        self.assertEqual(store.seq_get("beta"), 1)

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
        self.assertEqual(store.seq_get("alpha"), 2)
        self.assertEqual(store.kv_get("/alpha/a").data, b"1")
        message = i18n("substrate.key_missing", "d", "alpha")
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
        self.assertEqual(store.seq_get("alpha"), 0)
        self.assertEqual(store.seq_get("beta"), 0)
        message = i18n("substrate.key_missing", "a", "alpha")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/a")
        )
        self.assertEqual(
            _tables_list(store, "beta"), ["_head", "_kv", "_meta", "_turn"]
        )

    # `seq` survives closing, reopening and a new store on the same root.
    def test_seq_reopen(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.kv_put("/alpha/a", b"one")
        store.doc_put("alpha", "note", {0: {"t": "note"}, "text": _WIDE_TEXT})
        store.turn_append(
            "/alpha/scene/1", "user", '{"role":"user","content":"hi"}'
        )
        self.assertEqual(store.seq_get("alpha"), 3)
        store.db_close("alpha")
        self.assertEqual(store.db_list(), [])
        self.assertEqual(store.db_open("alpha"), 3)
        _store_close(store)
        again = _store_make(self, root)
        self.assertEqual(again.db_open("alpha"), 3)
        self.assertEqual(again.kv_get("/alpha/a").data, b"one")


# Snapshots: serialized bytes with `seq`, restored from bytes or a file.
class TestSnapshot(unittest.TestCase):
    # A restore brings back the rows and the `seq` of the snapshot.
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
        data, seq = store.db_snapshot("alpha")
        self.assertEqual(data[:16], b"SQLite format 3\x00")
        self.assertEqual(seq, 2)
        path = os.path.join(root, "alpha.sqlite")
        dump = _database_dump(path)
        store.kv_put("/alpha/a", b"two")
        store.kv_put("/alpha/b", b"three")
        store.sql_run("alpha", [_statement_make("DELETE FROM t")])
        self.assertEqual(store.seq_get("alpha"), 5)
        self.assertEqual(store.db_restore("alpha", data), 2)
        self.assertEqual(store.seq_get("alpha"), 2)
        self.assertEqual(store.kv_get("/alpha/a").data, b"one")
        message = i18n("substrate.key_missing", "b", "alpha")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/b")
        )
        self.assertEqual(_database_dump(path), dump)
        other = _root_make(self)
        second = _store_make(self, other)
        sink = os.path.join(other, "cache", "sink")
        with open(sink, "wb") as file:
            file.write(data)
        self.assertEqual(second.db_restore("alpha", sink), 2)
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
        message = i18n("substrate.schema_partial", [])
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.db_restore("alpha", data),
        )
        self.assertEqual(store.db_list(), ["alpha"])
        self.assertEqual(store.kv_get("/alpha/a").data, b"one")
        self.assertEqual(store.seq_get("alpha"), 1)
        self.assertEqual(sorted(os.listdir(root)), listed)

    # A kept snapshot reads back in pieces as its serialized bytes, then goes.
    def test_pieces_kept(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        store.kv_put("/alpha/exact", _VALUE_EXACT)
        data, seq = store.db_snapshot("alpha")
        head = store.snapshot_keep("alpha")
        digest = hashlib.sha256(data).digest()
        self.assertEqual(
            head, substrate.SnapshotHead(1, len(data), digest, seq)
        )
        self.assertEqual(seq, 1)
        self.assertGreater(head.size, 2 * _PIECE_BYTES)
        self.assertEqual(_pieces_read(store, head), data)
        message = i18n("substrate.snapshot_unknown", 1)
        _error_check(
            self, LookupError, message, lambda: store.snapshot_read(1, 0, 1)
        )

    # A piece outside the snapshot or of no bytes raises, and the rest reads.
    def test_pieces_bad(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        head = store.snapshot_keep("alpha")
        size = head.size
        cases = [(-1, 1), (0, 0), (0, size + 1), (size, 1), (size - 1, 2)]
        for offset, length in cases:
            message = i18n("substrate.snapshot_range", 1, offset, length, size)
            _error_check(
                self,
                ValueError,
                message,
                lambda: store.snapshot_read(1, offset, length),
            )
        message = i18n("substrate.snapshot_unknown", 2)
        _error_check(
            self, LookupError, message, lambda: store.snapshot_read(2, 0, 1)
        )
        data, _ = store.db_snapshot("alpha")
        self.assertEqual(_pieces_read(store, head), data)

    # Two kept snapshots of one database read apart, each its own bytes.
    def test_snapshots_apart(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        first_data, _ = store.db_snapshot("alpha")
        first = store.snapshot_keep("alpha")
        store.kv_put("/alpha/a", b"one")
        second_data, _ = store.db_snapshot("alpha")
        second = store.snapshot_keep("alpha")
        self.assertEqual((first.snapshot, first.seq), (1, 0))
        self.assertEqual((second.snapshot, second.seq), (2, 1))
        self.assertNotEqual(first.sha256, second.sha256)
        self.assertEqual(_pieces_read(store, first), first_data)
        self.assertEqual(_pieces_read(store, second), second_data)

    # A cached value stays held through the pieces of a snapshot and a restore.
    def test_value_held(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.kv_put("/alpha/big", _VALUE_OVER)
        head = store.snapshot_keep("alpha")
        data = _pieces_read(store, head)
        self.assertEqual(store.db_restore("alpha", data), head.seq)
        path = _cache_file(root, _VALUE_OVER)
        digest = hashlib.sha256(_VALUE_OVER).digest()
        self.assertEqual(
            store.kv_get("/alpha/big"),
            substrate.KvValue(path, len(_VALUE_OVER), digest),
        )
        with open(path, "rb") as file:
            self.assertEqual(file.read(), _VALUE_OVER)


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
            _child_put(root, _VALUE_OVER)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        path = _cache_file(root, _VALUE_OVER)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(store.db_open("alpha"), 0)
        message = i18n("substrate.key_missing", "big", "alpha")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/big")
        )
        self.assertEqual(store.kv_check("alpha"), 1)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(store.kv_check("alpha"), 0)


# Replication: the recorded sequences replayed, a stale `since`, bad lines.
class TestReplay(unittest.TestCase):
    # The recorded operations give the recorded `seq`, and the copies agree.
    def test_recorded_replay(self) -> None:
        first_root = _root_make(self)
        second_root = _root_make(self)
        _hello_make(first_root)
        _hello_make(second_root)
        first = _store_make(self, first_root)
        second = _store_make(self, second_root)
        for name, (seq, _) in _HELLO_DATABASES.items():
            self.assertEqual(first.db_open(name), seq)
            self.assertEqual(second.db_open(name), seq)
        sink = os.path.join(second_root, "cache", "sink")
        for kind, since, fields, seq in _RECORDED:
            _modifier_call(first, kind, fields)
            self.assertEqual(first.seq_get(_target_database(fields)), seq)
            replayed = dict(fields)
            if kind == "kv.put" and len(fields["data"]) > _OVERFLOW_BYTES:
                with open(sink, "wb") as file:
                    file.write(fields["data"])
                replayed["data"] = sink
            applied = second.operation_apply(kind, since, **replayed)
            self.assertEqual(applied, seq, kind)
        names = first.db_list()
        self.assertEqual(
            names,
            [
                "_files",
                "castle",
                "castle_gatehouse",
                "castle_world",
                "metaverse",
            ],
        )
        self.assertEqual(second.db_list(), names)
        _store_close(first)
        _store_close(second)
        for name in names:
            self.assertEqual(
                _database_dump(os.path.join(first_root, name + ".sqlite")),
                _database_dump(os.path.join(second_root, name + ".sqlite")),
                name,
            )
        self.assertEqual(
            _files_read(os.path.join(first_root, "cache")),
            _files_read(os.path.join(second_root, "cache")),
        )
        self.assertEqual(
            sorted(os.listdir(first_root)), sorted(os.listdir(second_root))
        )
        kind, since, fields, seq = _DESYNC
        self.assertEqual(second.db_open("_files"), since)
        second.kv_put(fields["k"], fields["data"])
        _error_check(
            self,
            RuntimeError,
            _DESYNC_MESSAGE,
            lambda: second.operation_apply(kind, since, **fields),
        )
        self.assertEqual(second.seq_get("_files"), seq)

    # A `since` that is not the `seq` raises the desync and changes nothing.
    def test_since_stale(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        message = i18n("substrate.since_stale", "kv.put", 1, 0, "alpha")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.operation_apply(
                "kv.put", 1, k="/alpha/a", data=b"x"
            ),
        )
        message = i18n("substrate.since_stale", "db.create", 1, 0, "beta")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.operation_apply("db.create", 1, db="beta"),
        )
        self.assertFalse(os.path.exists(os.path.join(root, "beta.sqlite")))
        message = i18n("substrate.since_stale", "db.drop", 1, 0, "alpha")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.operation_apply("db.drop", 1, db="alpha"),
        )
        self.assertEqual(store.db_list(), ["alpha"])
        self.assertEqual(store.seq_get("alpha"), 0)
        message = i18n("substrate.key_missing", "a", "alpha")
        _error_check(
            self, LookupError, message, lambda: store.kv_get("/alpha/a")
        )
        self.assertEqual(
            store.operation_apply("kv.put", 0, k="/alpha/a", data=b"x"), 1
        )
        self.assertEqual(store.operation_apply("db.drop", 1, db="alpha"), 0)
        self.assertEqual(store.db_list(), [])

    # A stale `doc.put` raises and writes no version.
    def test_stale_document(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        body: dict[int | str, Any] = {0: {"t": "note"}}
        message = i18n("substrate.since_stale", "doc.put", 1, 0, "alpha")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.operation_apply(
                "doc.put", 1, db="alpha", id="note", body=body
            ),
        )
        message = i18n("substrate.id_missing", "note", "alpha")
        _error_check(
            self, LookupError, message, lambda: store.doc_head("alpha", "note")
        )
        self.assertEqual(store.seq_get("alpha"), 0)

    # A stale `turn.append` raises and appends no turn.
    def test_stale_turn(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        scene = "/alpha/scene/1"
        message = i18n("substrate.since_stale", "turn.append", 1, 0, "alpha")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.operation_apply(
                "turn.append",
                1,
                scene=scene,
                role="user",
                content=_MESSAGE_USER,
            ),
        )
        self.assertEqual(store.turn_list(scene), [])
        self.assertEqual(store.seq_get("alpha"), 0)

    # A stale `sql.run` raises and runs no statement.
    def test_stale_sql(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        statements: list[dict[str, Any]] = [
            {"sql": "CREATE TABLE note (x TEXT)", "params": []}
        ]
        message = i18n("substrate.since_stale", "sql.run", 1, 0, "alpha")
        _error_check(
            self,
            RuntimeError,
            message,
            lambda: store.operation_apply(
                "sql.run", 1, db="alpha", statements=statements
            ),
        )
        self.assertEqual(
            _tables_list(store, "alpha"), ["_head", "_kv", "_meta", "_turn"]
        )
        self.assertEqual(store.seq_get("alpha"), 0)

    # A delete, a compaction and a drop, which the replay lacks, apply.
    def test_operations_unrecorded(self) -> None:
        store = _store_make(self, _root_make(self))
        scene = "/alpha/scene/1"
        summary = '{"role":"system","content":"Answered 1."}'
        self.assertEqual(store.operation_apply("db.create", 0, db="alpha"), 0)
        self.assertEqual(
            store.operation_apply("kv.put", 0, k="/alpha/a", data=b"one"), 1
        )
        self.assertEqual(
            store.operation_apply("kv.delete", 1, k="/alpha/a"), 2
        )
        self.assertEqual(
            store.operation_apply(
                "turn.append",
                2,
                scene=scene,
                role="user",
                content=_MESSAGE_USER,
            ),
            3,
        )
        self.assertEqual(
            store.operation_apply(
                "turn.compact",
                3,
                scene=scene,
                through=1,
                summary="Answered 1.",
            ),
            4,
        )
        self.assertEqual(
            store.turn_list(scene),
            [substrate.TurnRow(scene, 1, "system", summary)],
        )
        self.assertEqual(store.operation_apply("db.drop", 4, db="alpha"), 0)
        self.assertEqual(store.db_list(), [])

    # An unknown type, wrong keywords or an internal ref raise.
    def test_operation_bad(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        message = i18n("substrate.operation_type", "kv.get")
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.operation_apply("kv.get", 0, k="/alpha/a"),
        )
        with self.assertRaisesRegex(TypeError, "'data'"):
            store.operation_apply("kv.put", 0, k="/alpha/a")
        with self.assertRaisesRegex(TypeError, "'db'"):
            store.operation_apply("kv.delete", 0, k="/alpha/a", db="alpha")
        message = i18n("substrate.ref_internal", "a")
        _error_check(
            self,
            ValueError,
            message,
            lambda: store.operation_apply("kv.delete", 0, k="a"),
        )
        with self.assertRaisesRegex(TypeError, "'params'"):
            store.operation_apply(
                "sql.run", 0, db="alpha", statements=[{"sql": "SELECT 1"}]
            )
        self.assertEqual(store.seq_get("alpha"), 0)
