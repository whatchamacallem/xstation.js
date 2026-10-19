# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of the server substrate on scratch roots under build/: the tables on
# first use, both ref forms, documents and heads, overflow to the cache, a
# kill between a cache file and its row, snapshots, turns, guarded SQL, the
# rules of `seq` and a recorded sequence of forwarded operations replayed.

import hashlib, json, os, signal, sqlite3, substrate, tempfile, traceback
import unittest
from typing import Any

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

# A map over `overflow_bytes`, as large as the one of the sync transcript.
_MAP_BYTES = bytes(range(256)) * 800

# The real `os.replace`, which the patched one of the forked child calls.
_OS_REPLACE = os.replace

# The subtitle of the arrival scene of the turn transcript.
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

# The stored text of the arrival scene, as the turn transcript sends it.
_ARRIVAL_TEXT = (
    '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png","subtitle":"'
    + _ARRIVAL_SUBTITLE
    + '","image":{"$ref":1}}'
)

# The universe table, as the metaverse SQL file creates it.
_UNIVERSE_SQL = (
    "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL,"
    " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT"
)

# The world table of the castle universe, from the turn transcript.
_WORLD_SQL = (
    "CREATE TABLE world (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT"
)

# The region table of the castle world, from the turn transcript.
_REGION_SQL = (
    "CREATE TABLE region"
    " (name TEXT PRIMARY KEY, tide INTEGER NOT NULL DEFAULT 0) STRICT"
)

# The arguments of the first tool call of the turn transcript.
_SCRIPT_ARGUMENTS = (
    '{"name":"bootstrap","args":{"universe":"castle","title":"The castle",'
    '"world":"castle_world","region":"castle_gatehouse"}}'
)

# The forwarded operations of the turn and sync transcripts, in order.
_RECORDED: list[tuple[str, dict[str, Any]]] = [
    ("db.create", {"db": "metaverse"}),
    (
        "sql.run",
        {
            "db": "metaverse",
            "statements": [{"sql": _UNIVERSE_SQL, "params": []}],
        },
    ),
    (
        "turn.append",
        {
            "scene": _SCENE,
            "role": "user",
            "content": {"role": "user", "content": "1"},
        },
    ),
    (
        "turn.append",
        {
            "scene": _SCENE,
            "role": "assistant",
            "content": {
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
            },
        },
    ),
    ("db.create", {"db": "castle"}),
    (
        "sql.run",
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
    ),
    ("db.create", {"db": "castle_world"}),
    (
        "sql.run",
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
    ),
    ("db.create", {"db": "castle_gatehouse"}),
    (
        "sql.run",
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
    ),
    ("kv.put", {"k": "/metaverse/world", "data": b"castle_world"}),
    ("db.create", {"db": "_files"}),
    ("kv.put", {"k": "/_files/maps/castle.bin", "data": _MAP_BYTES}),
    (
        "doc.put",
        {
            "db": "castle_gatehouse",
            "id": "scene/arrival",
            "body": _ARRIVAL_BODY,
        },
    ),
    (
        "kv.put",
        {
            "k": "/castle_world/scene",
            "data": b"/castle_gatehouse/scene/arrival/1",
        },
    ),
    (
        "sql.run",
        {
            "db": "castle",
            "statements": [
                {
                    "sql": "UPDATE world SET title = ? WHERE name = ?",
                    "params": ["The castle at dusk", "castle_world"],
                }
            ],
        },
    ),
    (
        "turn.compact",
        {"scene": _SCENE, "through": 1, "summary": "The player answered 1."},
    ),
    ("kv.delete", {"k": "/metaverse/world"}),
    ("db.drop", {"db": "castle_gatehouse"}),
]


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


# The canonical JSON text of a value, as the substrate stores it.
def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# The path of the cache file of a value under a root.
def _cache_file(root: str, value: bytes) -> str:
    return os.path.join(root, "cache", hashlib.sha256(value).hexdigest())


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
    database = substrate.ref_split(ref).db
    if database is None:
        raise ValueError(f"{ref} is not an external ref")
    return database


# Makes on a store the direct call a modifier made for a recorded operation.
def _modifier_call(
    store: substrate.Store, kind: str, fields: dict[str, Any]
) -> None:
    if kind == "kv.put":
        store.kv_put(fields["k"], fields["data"])
    elif kind == "kv.delete":
        store.kv_delete(fields["k"])
    elif kind == "doc.put":
        store.doc_put(fields["db"], fields["id"], fields["body"])
    elif kind == "db.create":
        store.db_create(fields["db"])
    elif kind == "db.drop":
        store.db_drop(fields["db"])
    elif kind == "turn.append":
        text = _json_text(fields["content"])
        store.turn_append(fields["scene"], fields["role"], text)
    elif kind == "turn.compact":
        store.turn_compact(
            fields["scene"], fields["through"], fields["summary"]
        )
    elif kind == "sql.run":
        statements = [
            substrate.SqlStatement(statement["sql"], statement["params"])
            for statement in fields["statements"]
        ]
        store.sql_run(fields["db"], statements)
    else:
        raise ValueError(f"no direct call for {kind}")


# Renames as `os.replace` does, then kills the process before the row.
def _replace_kill(source: str, target: str) -> None:
    _OS_REPLACE(source, target)
    os.kill(os.getpid(), signal.SIGKILL)


# In the forked child: puts a value and is killed as its cache file lands.
def _child_put(root: str, value: bytes) -> None:
    try:
        store = substrate.Store(root, _OVERFLOW_BYTES)
        store.db_open("alpha")
        setattr(os, "replace", _replace_kill)
        store.kv_put("/alpha/big", value)
    except BaseException:
        traceback.print_exc()
    os.kill(os.getpid(), signal.SIGTERM)


# Databases: the tables on first use, names, creating, opening, dropping.
class TestDatabases(unittest.TestCase):
    # A new database gets the substrate's tables, `seq` 1 and `schema` 1.
    def test_tables_created(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        self.assertEqual(
            _tables_list(store, "alpha"), ["_head", "_kv", "_meta", "_turn"]
        )
        rows = _rows_query(
            store, "alpha", "SELECT name, value FROM _meta ORDER BY name"
        )
        self.assertEqual(rows, [["schema", "1"], ["seq", "1"]])
        self.assertEqual(store.db_list(), ["alpha"])
        self.assertEqual(store.seq_get("alpha"), 1)

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

    # A name that is not a C identifier is refused and makes no file.
    def test_names_bad(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        names = ["", "1abc", "a-b", "a b", "a.b", "a/b", "caf" + chr(0xE9)]
        for name in names:
            with self.assertRaises(ValueError, msg=name):
                store.db_create(name)
            with self.assertRaises(ValueError, msg=name):
                store.db_open(name)
        self.assertEqual(os.listdir(root), ["cache"])
        self.assertEqual(store.db_list(), [])

    # A second create, a second open, a missing file and a close all raise.
    def test_create_twice(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        with self.assertRaises(FileExistsError):
            store.db_create("alpha")
        with self.assertRaises(RuntimeError):
            store.db_open("alpha")
        with self.assertRaises(sqlite3.OperationalError):
            store.db_open("gamma")
        self.assertFalse(os.path.exists(os.path.join(root, "gamma.sqlite")))
        with self.assertRaises(LookupError):
            store.db_close("gamma")
        self.assertEqual(store.seq_get("alpha"), 1)

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
            with self.assertRaises(ValueError, msg=ref):
                substrate.ref_split(ref)

    # An internal ref needs a database and an external ref takes none.
    def test_ref_database(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        with self.assertRaises(ValueError):
            store.kv_put("world", b"x")
        with self.assertRaises(ValueError):
            store.kv_put("/alpha/world", b"x", "alpha")
        with self.assertRaises(LookupError):
            store.kv_put("/beta/world", b"x")
        with self.assertRaises(ValueError):
            store.doc_get("/alpha/world")
        self.assertEqual(store.seq_get("alpha"), 1)


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
        self.assertEqual(seq, 2)
        self.assertEqual(
            store.kv_get(key, "alpha"),
            substrate.KvValue(value, len(value), digest),
        )
        self.assertEqual(store.kv_put("place/a/b", b"world", "alpha")[1], 3)
        self.assertEqual(store.kv_get("/alpha/place/a/b").data, b"world")
        self.assertEqual(store.kv_list("alpha", "greeting/"), [row])
        keys = [listed.key for listed in store.kv_list("alpha", "")]
        self.assertEqual(keys, [key, "place/a/b"])
        self.assertEqual(store.kv_delete(key, "alpha"), 4)
        with self.assertRaises(LookupError):
            store.kv_get("/alpha/" + key)

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
        self.assertEqual(seq, 2)
        self.assertEqual(
            store.kv_get("/alpha/streamed").data,
            _cache_file(root, _VALUE_OVER),
        )
        small = os.path.join(root, "cache", "small")
        with open(small, "wb") as file:
            file.write(_VALUE_EXACT)
        with self.assertRaises(ValueError):
            store.kv_put("/alpha/small", small)
        self.assertEqual(store.seq_get("alpha"), 2)
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
        self.assertEqual(first, ("/castle_gatehouse/scene/arrival/1", 2))
        self.assertEqual(
            store.doc_head("castle_gatehouse", "scene/arrival"), first[0]
        )
        self.assertEqual(
            store.kv_get(first[0]).data, _ARRIVAL_TEXT.encode("utf-8")
        )
        changed = dict(_ARRIVAL_BODY)
        changed["subtitle"] = "The keeper waves."
        second = store.doc_put("castle_gatehouse", "scene/arrival", changed)
        self.assertEqual(second, ("/castle_gatehouse/scene/arrival/2", 3))
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
        with self.assertRaises(LookupError):
            store.doc_head("castle_gatehouse", "scene/absent")
        with self.assertRaises(LookupError):
            store.doc_get("/castle_gatehouse/scene/arrival/3")
        with self.assertRaises(ValueError):
            store.doc_get("/castle_gatehouse/scene/arrival")

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
        self.assertEqual((ref, seq), ("/metaverse/fog/1", 2))
        stored = store.doc_get(ref)
        self.assertEqual(_json_text(stored), _json_text(expected))
        self.assertEqual(
            _json_text(substrate.doc_decode(stored)), _json_text(normal)
        )

    # Documents that would not round trip, or are malformed, raise.
    def test_documents_bad(self) -> None:
        normals: list[dict[int | str, Any]] = [
            {"subtitle": "x"},
            {0: {"t": "scene", "v": 0}},
            {0: {"v": 2}},
            {0: {"t": "scene", "x": 1}},
            {0: "scene"},
            {0: {"t": "scene"}, 1: "/a/b"},
            {0: {"t": "scene"}, "12": "x"},
            {0: {"t": "scene"}, "x": {"$ref": 1}},
        ]
        for normal in normals:
            with self.assertRaises(ValueError, msg=repr(normal)):
                substrate.doc_encode(normal)
        encodeds: list[dict[int | str, Any]] = [
            {0: {"t": "scene"}, 1: "/a/b", "x": {"$ref": 2}},
            {0: {"t": "scene"}, 2: "/a/b", "x": {"$ref": 2}},
            {0: {"t": "scene"}, 1: 5, "x": {"$ref": 1}},
            {0: {"t": "scene"}, 1: "/a/b", "x": {"$ref": True}},
            {0: {"t": "scene"}, "07": "x"},
        ]
        for encoded in encodeds:
            with self.assertRaises(ValueError, msg=repr(encoded)):
                substrate.doc_decode(encoded)
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        with self.assertRaises(ValueError):
            store.doc_put("alpha", "big", {0: {"t": "n"}, "n": 2**53 + 1})
        with self.assertRaises(ValueError):
            store.doc_put("alpha", "", {0: {"t": "note"}})
        with self.assertRaises(ValueError):
            store.doc_put("alpha", "gap", {0: {"t": "note"}, 2: "/a/b"})
        self.assertEqual(store.seq_get("alpha"), 1)


# Turns: appended in order, listed, and compacted into one summary.
class TestTurns(unittest.TestCase):
    # Turns number from 1 in their scene, a bad scene or content raises.
    def test_turns_append(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("metaverse")
        user = '{"role":"user","content":"1"}'
        answer = _json_text({"role": "assistant", "content": _WIDE_TEXT})
        self.assertEqual(store.turn_append(_SCENE, "user", user), (1, 2))
        self.assertEqual(
            store.turn_append(_SCENE, "assistant", answer), (2, 3)
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
            with self.assertRaises(ValueError, msg=scene):
                store.turn_append(scene, "user", user)
        with self.assertRaises(sqlite3.IntegrityError):
            store.turn_append(_SCENE, "user", "not json")
        self.assertEqual(store.seq_get("metaverse"), 3)

    # Compaction replaces turns 1 to `through` by one summary turn at 1.
    def test_turns_compact(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("metaverse")
        for text in ("1", "2", "3", "4"):
            message = _json_text({"role": "user", "content": text})
            store.turn_append(_SCENE, "user", message)
        self.assertEqual(store.turn_compact(_SCENE, 3, "Asked thrice."), 6)
        summary = '{"role":"system","content":"Asked thrice."}'
        fourth = '{"role":"user","content":"4"}'
        self.assertEqual(
            store.turn_list(_SCENE),
            [
                substrate.TurnRow(_SCENE, 1, "system", summary),
                substrate.TurnRow(_SCENE, 4, "user", fourth),
            ],
        )
        self.assertEqual(store.turn_append(_SCENE, "user", fourth), (5, 7))
        with self.assertRaises(ValueError):
            store.turn_compact(_SCENE, 0, "None.")
        with self.assertRaises(LookupError):
            store.turn_compact("/metaverse/elsewhere/1", 2, "None.")
        self.assertEqual(store.seq_get("metaverse"), 7)


# Guarded SQL: results, and writes refused on `_` tables and `_settings`.
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
        self.assertEqual(store.seq_get("castle"), 2)
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
        self.assertEqual(store.seq_get("castle"), 2)

    # Writes to `_` tables, transactions and attaching raise, changing nothing.
    def test_writes_refused(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        store.kv_put("/alpha/key", b"value")
        other = os.path.join(root, "other.sqlite")
        refused = [
            _statement_make(
                "INSERT INTO _kv VALUES (?, ?, ?, ?)", "k", 1, bytes(32), b"v"
            ),
            _statement_make(
                "UPDATE _meta SET value = ? WHERE name = ?", "9", "seq"
            ),
            _statement_make("DELETE FROM _head"),
            _statement_make("DROP TABLE _turn"),
            _statement_make("ALTER TABLE _kv ADD COLUMN note TEXT"),
            _statement_make("CREATE INDEX kv_size ON _kv (size)"),
            _statement_make(
                "CREATE TRIGGER kv_spy AFTER INSERT ON _kv BEGIN SELECT 1; END"
            ),
            _statement_make("CREATE TABLE _mine (x TEXT)"),
            _statement_make("BEGIN"),
            _statement_make("COMMIT"),
            _statement_make("SAVEPOINT nested"),
            _statement_make("ATTACH DATABASE ? AS other", other),
        ]
        for statement in refused:
            with self.assertRaises(sqlite3.DatabaseError, msg=statement.sql):
                store.sql_run("alpha", [statement])
        self.assertEqual(store.seq_get("alpha"), 2)
        self.assertEqual(store.kv_get("/alpha/key").data, b"value")
        self.assertFalse(os.path.exists(other))
        self.assertEqual(
            _tables_list(store, "alpha"), ["_head", "_kv", "_meta", "_turn"]
        )
        store.sql_run("alpha", [_statement_make("CREATE TABLE mine (x TEXT)")])
        self.assertEqual(store.seq_get("alpha"), 3)

    # `_settings` is read by `sql_run` and written only by the substrate.
    def test_settings_refused(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("_settings")
        self.assertEqual(store.kv_put("/_settings/debug", b"true")[1], 2)
        self.assertEqual(
            _rows_query(store, "_settings", "SELECT key FROM _kv"), [["debug"]]
        )
        refused = [
            _statement_make("CREATE TABLE note (x TEXT)"),
            _statement_make(
                "INSERT INTO _kv VALUES (?, ?, ?, ?)", "k", 1, bytes(32), b"v"
            ),
            _statement_make("PRAGMA user_version = 7"),
        ]
        for statement in refused:
            with self.assertRaises(sqlite3.DatabaseError, msg=statement.sql):
                store.sql_run("_settings", [statement])
        self.assertEqual(store.seq_get("_settings"), 2)
        self.assertEqual(
            _tables_list(store, "_settings"),
            ["_head", "_kv", "_meta", "_turn"],
        )


# The rules of `seq`: what counts, what does not, and transactions.
class TestSeq(unittest.TestCase):
    # Changes count once each, no change and a failure count nothing.
    def test_seq_rules(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        self.assertEqual(store.kv_put("/alpha/a", b"one")[1], 2)
        self.assertEqual(store.kv_put("/alpha/a", b"one")[1], 2)
        self.assertEqual(store.kv_put("/alpha/a", b"two")[1], 3)
        self.assertEqual(store.kv_delete("/alpha/absent"), 3)
        self.assertEqual(store.kv_delete("/alpha/a"), 4)
        store.sql_run("alpha", [_statement_make("SELECT 1")])
        self.assertEqual(store.seq_get("alpha"), 4)
        store.sql_run("alpha", [_statement_make("CREATE TABLE t (x TEXT)")])
        self.assertEqual(store.seq_get("alpha"), 5)
        store.sql_run(
            "alpha", [_statement_make("INSERT INTO t VALUES (?)", "a")]
        )
        self.assertEqual(store.seq_get("alpha"), 6)
        store.sql_run(
            "alpha",
            [_statement_make("UPDATE t SET x = ? WHERE x = ?", "b", "absent")],
        )
        self.assertEqual(store.seq_get("alpha"), 6)
        with self.assertRaises(sqlite3.OperationalError):
            store.sql_run(
                "alpha",
                [
                    _statement_make("INSERT INTO t VALUES (?)", "b"),
                    _statement_make("INSERT INTO absent VALUES (1)"),
                ],
            )
        self.assertEqual(store.seq_get("alpha"), 6)
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
        self.assertEqual(store.seq_get("alpha"), 3)
        self.assertEqual(store.seq_get("beta"), 2)

        # Puts a value to the cache, deletes another, then raises.
        def puts_raise() -> None:
            store.kv_put("/alpha/d", _VALUE_OVER)
            store.kv_delete("/alpha/a")
            raise RuntimeError("rolled back")

        with self.assertRaises(RuntimeError):
            store.transaction_run(puts_raise)
        self.assertEqual(store.seq_get("alpha"), 3)
        self.assertEqual(store.kv_get("/alpha/a").data, b"1")
        with self.assertRaises(LookupError):
            store.kv_get("/alpha/d")
        self.assertEqual(store.kv_check("alpha"), 1)

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
        self.assertEqual(store.seq_get("alpha"), 4)
        store.db_close("alpha")
        self.assertEqual(store.db_list(), [])
        self.assertEqual(store.db_open("alpha"), 4)
        _store_close(store)
        again = _store_make(self, root)
        self.assertEqual(again.db_open("alpha"), 4)
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
        self.assertEqual(seq, 3)
        path = os.path.join(root, "alpha.sqlite")
        dump = _database_dump(path)
        store.kv_put("/alpha/a", b"two")
        store.kv_put("/alpha/b", b"three")
        store.sql_run("alpha", [_statement_make("DELETE FROM t")])
        self.assertEqual(store.seq_get("alpha"), 6)
        self.assertEqual(store.db_restore("alpha", data), 3)
        self.assertEqual(store.seq_get("alpha"), 3)
        self.assertEqual(store.kv_get("/alpha/a").data, b"one")
        with self.assertRaises(LookupError):
            store.kv_get("/alpha/b")
        self.assertEqual(_database_dump(path), dump)
        other = _root_make(self)
        second = _store_make(self, other)
        sink = os.path.join(other, "cache", "sink")
        with open(sink, "wb") as file:
            file.write(data)
        self.assertEqual(second.db_restore("alpha", sink), 3)
        self.assertFalse(os.path.exists(sink))
        self.assertEqual(
            _database_dump(os.path.join(other, "alpha.sqlite")), dump
        )


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
        self.assertEqual(store.db_open("alpha"), 1)
        with self.assertRaises(LookupError):
            store.kv_get("/alpha/big")
        self.assertEqual(store.kv_check("alpha"), 1)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(store.kv_check("alpha"), 0)


# Replication: a recorded sequence replayed, a stale `since`, bad operations.
class TestReplay(unittest.TestCase):
    # Replaying the recorded operations reproduces the modifier's store.
    def test_recorded_replay(self) -> None:
        first_root = _root_make(self)
        second_root = _root_make(self)
        first = _store_make(self, first_root)
        second = _store_make(self, second_root)
        sink = os.path.join(second_root, "cache", "sink")
        for kind, fields in _RECORDED:
            database = _target_database(fields)
            since = 0 if kind == "db.create" else first.seq_get(database)
            _modifier_call(first, kind, fields)
            seq = 0 if kind == "db.drop" else first.seq_get(database)
            replayed = dict(fields)
            if kind == "kv.put" and len(fields["data"]) > _OVERFLOW_BYTES:
                with open(sink, "wb") as file:
                    file.write(fields["data"])
                replayed["data"] = sink
            self.assertEqual(
                second.operation_apply(kind, since, **replayed), seq, kind
            )
        names = first.db_list()
        self.assertEqual(
            names, ["_files", "castle", "castle_world", "metaverse"]
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

    # A `since` that is not the `seq` raises the desync and changes nothing.
    def test_since_stale(self) -> None:
        root = _root_make(self)
        store = _store_make(self, root)
        store.db_create("alpha")
        with self.assertRaises(RuntimeError) as caught:
            store.operation_apply("kv.put", 0, k="/alpha/a", data=b"x")
        self.assertEqual(
            str(caught.exception), "kv.put: since 0 is not seq 1 of alpha"
        )
        with self.assertRaises(RuntimeError):
            store.operation_apply("db.create", 1, db="beta")
        self.assertFalse(os.path.exists(os.path.join(root, "beta.sqlite")))
        with self.assertRaises(RuntimeError):
            store.operation_apply("db.drop", 0, db="alpha")
        self.assertEqual(store.db_list(), ["alpha"])
        self.assertEqual(store.seq_get("alpha"), 1)
        with self.assertRaises(LookupError):
            store.kv_get("/alpha/a")
        self.assertEqual(
            store.operation_apply("kv.put", 1, k="/alpha/a", data=b"x"), 2
        )
        self.assertEqual(store.operation_apply("db.drop", 2, db="alpha"), 0)
        self.assertEqual(store.db_list(), [])

    # An unknown type, wrong keywords or an internal ref raise.
    def test_operation_bad(self) -> None:
        store = _store_make(self, _root_make(self))
        store.db_create("alpha")
        with self.assertRaises(ValueError):
            store.operation_apply("kv.get", 1, k="/alpha/a")
        with self.assertRaises(TypeError):
            store.operation_apply("kv.put", 1, k="/alpha/a")
        with self.assertRaises(TypeError):
            store.operation_apply("kv.delete", 1, k="/alpha/a", db="alpha")
        with self.assertRaises(ValueError):
            store.operation_apply("kv.delete", 1, k="a")
        with self.assertRaises(TypeError):
            store.operation_apply(
                "sql.run", 1, db="alpha", statements=[{"sql": "SELECT 1"}]
            )
        self.assertEqual(store.seq_get("alpha"), 1)
