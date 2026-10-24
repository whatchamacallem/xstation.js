# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The server substrate, the single door to SQLite: one connection for each
# database file under a root, the substrate's tables in each, rows of values
# with overflow to the cache directory `<root>/cache`, which holds the values
# over `overflow_bytes` by their digest, documents, turns, SQL and snapshots.
# It applies the browser's committed operations as plain messages, through
# the same methods as any caller, and keeps more history than the browser:
# it never compacts turns. Nothing here numbers, orders or checks a change
# against another store.
#
# A value whose row names a cache file this side does not hold is lost: its
# row stays, `kv_list` lists it, `kv_put` replaces it, and `kv_get` raises
# `substrate.file_lost`. `db_restore` tolerates such rows, and `db_snapshot`
# lists only the cache files it holds, so a database moves as one blob with
# the cache files that exist and works but for the lost values.
#
# The schema's triggers raise the name of a string of the strings table, as
# `agent.content_ambiguous`: a statement that fails with such a message
# raises that string, the `sqlite3` error as its `__cause__`.

import hashlib, json, os, re, sqlite3, tempfile, urllib.parse
from collections.abc import Callable, Iterable
from internationalization import i18n
from typing import Any, NamedTuple, cast

# The substrate's tables, one statement each, created on first use.
_SCHEMA_STATEMENTS = (
    """CREATE TABLE _meta (
    name  TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID, STRICT""",
    """CREATE TABLE _kv (
    key    TEXT    PRIMARY KEY,
    size   INTEGER NOT NULL,
    sha256 BLOB    NOT NULL,
    data   BLOB
) WITHOUT ROWID, STRICT""",
    """CREATE TABLE _head (
    id      TEXT    PRIMARY KEY,
    version INTEGER NOT NULL
) WITHOUT ROWID, STRICT""",
    """CREATE TABLE _turn (
    scene   TEXT    NOT NULL,
    n       INTEGER NOT NULL,
    role    TEXT    NOT NULL,
    content TEXT    NOT NULL CHECK (json_valid(content)),
    PRIMARY KEY (scene, n)
) WITHOUT ROWID, STRICT""",
)

# The names of the substrate's tables.
_SCHEMA_TABLES = frozenset({"_meta", "_kv", "_head", "_turn"})

# The version of the substrate's tables, the `schema` row of `_meta`.
_SCHEMA_VERSION = "1"

# The file extension of a database under the root.
_DB_EXTENSION = ".sqlite"

# The permissions of a new database file, those SQLite gives one it makes.
_DB_MODE = 0o644

# The suffix of the file a restore writes beside the database's own file.
_RESTORE_SUFFIX = "-restore"

# The query that opens an existing database file to read and write.
_QUERY_WRITE = "mode=rw"

# The query that opens a database file to read once: read only, immutable.
_QUERY_READ = "mode=ro&immutable=1"

# The directory under the root that holds the values over `overflow_bytes`.
_CACHE_DIRECTORY = "cache"

# A locked database's wait: 5000 ms, a default chosen by its writer.
_BUSY_TIMEOUT_MS = 5000

# A database name, a C identifier.
_C_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# An external ref: a slash, a database name, a slash and a nonempty key.
_EXTERNAL_REF = re.compile(r"/([A-Za-z_][A-Za-z0-9_]*)/(.+)", re.DOTALL)

# A reference string of a document: an external ref with no white space.
_REFERENCE_STRING = re.compile(r"/[A-Za-z_][A-Za-z0-9_]*/\S+")

# An integer literal: decimal digits with no sign and no leading zero.
_INTEGER_LITERAL = re.compile(r"0|[1-9][0-9]*")

# Decimal digits, which no payload key of a document may be.
_DIGITS = re.compile(r"[0-9]+")

# The names of the strings the schema's triggers raise.
_TRIGGER_NAMES = ("agent.content_ambiguous",)


# A `_kv` row without its data.
class KvRow(NamedTuple):
    key: str
    size: int
    sha256: bytes


# The value of a key: bytes, or the cache file's path over `overflow_bytes`.
class KvValue(NamedTuple):
    data: bytes | str
    size: int
    sha256: bytes


# A `_turn` row: `n` counts within the scene, `content` is one message.
class TurnRow(NamedTuple):
    scene: str
    n: int
    role: str
    content: str


# One SQL statement with its bound parameters, never string built.
class SqlStatement(NamedTuple):
    sql: str
    params: list[Any]


# The result of one statement: column names, rows, rows changed.
class SqlResult(NamedTuple):
    columns: list[str]
    rows: list[list[Any]]
    changes: int


# A ref split: the database (None when internal), the key, the version.
class RefParts(NamedTuple):
    db: str | None
    key: str
    version: int | None


# A database as one blob: its file's bytes and the paths of its cache files.
class DbImage(NamedTuple):
    data: bytes
    files: list[str]


# Raises unless the name is a C identifier, as a database name must be.
def _name_check(name: str) -> None:
    if _C_IDENTIFIER.fullmatch(name) is None:
        raise ValueError(i18n("substrate.name_bad", name))


# The version a key ends in, when its last segment is an integer literal.
def _version_find(key: str) -> int | None:
    head, slash, tail = key.rpartition("/")
    if slash and head and _INTEGER_LITERAL.fullmatch(tail):
        return int(tail)
    return None


# The database of a scene, whose ref must be an external `Document-Ref`.
def _scene_database(scene: str) -> str:
    parts = ref_split(scene)
    if parts.db is None or parts.version is None:
        raise ValueError(i18n("substrate.scene_bad", scene))
    return parts.db


# A JSON value ready to write: at every level integer keys first, keys checked.
def _json_ordered(value: object) -> object:
    if isinstance(value, dict):
        source = cast(dict[object, object], value)
        numbers: list[int] = []
        names: list[str] = []
        for key in source:
            if type(key) is int and key >= 0:
                numbers.append(key)
            elif type(key) is str and not _INTEGER_LITERAL.fullmatch(key):
                names.append(key)
            else:
                raise ValueError(i18n("substrate.key_refused", repr(key)))
        return {
            key: _json_ordered(source[key])
            for key in [*sorted(numbers), *names]
        }
    if isinstance(value, (list, tuple)):
        items = cast(Iterable[object], value)
        return [_json_ordered(item) for item in items]
    return value


# The canonical JSON text of a value, the text the wire's encoder writes.
def _json_canonical(value: object) -> str:
    return json.dumps(
        _json_ordered(value), ensure_ascii=False, separators=(",", ":")
    )


# A JSON object from parsed pairs, its integer literal keys made integers.
def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[int | str, Any]:
    return {
        (int(key) if _INTEGER_LITERAL.fullmatch(key) else key): item
        for key, item in pairs
    }


# A stored document: JSON text whose integer literal keys are its headers.
def _document_parse(data: bytes) -> dict[int | str, Any]:
    loaded: dict[int | str, Any] = json.loads(
        data.decode("utf-8"), object_pairs_hook=_pairs_object
    )
    return loaded


# The bytes of a value: as held, or read from its cache file.
def _value_read(data: bytes | str) -> bytes:
    if isinstance(data, bytes):
        return data
    with open(data, "rb") as file:
        return file.read()


# The `sha256` digest of a file's bytes.
def _file_hash(path: str) -> bytes:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").digest()


# A copy of header `0`: the type `t` and, when not 0, the version `v`.
def _header_copy(document: dict[int | str, Any]) -> dict[str, Any]:
    if 0 not in document:
        raise ValueError(i18n("substrate.header_missing"))
    header = document[0]
    if not isinstance(header, dict):
        raise ValueError(i18n("substrate.header_bad", header))
    fields = cast(dict[str, Any], header)
    typed = isinstance(fields.get("t"), str)
    versioned = "v" not in fields or (
        type(fields["v"]) is int and fields["v"] != 0
    )
    if not (typed and versioned and fields.keys() <= {"t", "v"}):
        raise ValueError(i18n("substrate.header_bad", header))
    return dict(fields)


# Raises on a payload key of decimal digits, which would read as a header.
def _key_check(key: str) -> None:
    if _DIGITS.fullmatch(key):
        raise ValueError(i18n("substrate.key_digits", key))


# Replaces each reference string in a body value by `{"$ref": n}`.
def _refs_take(value: Any, refs: dict[str, int]) -> Any:
    if isinstance(value, str):
        if _REFERENCE_STRING.fullmatch(value) is None:
            return value
        if value not in refs:
            refs[value] = len(refs) + 1
        return {"$ref": refs[value]}
    if isinstance(value, dict):
        fields = cast(dict[str, Any], value)
        if fields.keys() == {"$ref"}:
            raise ValueError(i18n("substrate.ref_shape", fields))
        return {key: _refs_take(item, refs) for key, item in fields.items()}
    if isinstance(value, list):
        return [_refs_take(item, refs) for item in cast(list[Any], value)]
    return value


# Replaces each `{"$ref": n}` in a body value by the string of header n.
def _refs_restore(value: Any, refs: list[str]) -> Any:
    if isinstance(value, dict):
        fields = cast(dict[str, Any], value)
        if fields.keys() == {"$ref"}:
            index = fields["$ref"]
            if type(index) is not int or not 1 <= index <= len(refs):
                raise ValueError(i18n("substrate.ref_index", index))
            return refs[index - 1]
        return {key: _refs_restore(item, refs) for key, item in fields.items()}
    if isinstance(value, list):
        return [_refs_restore(item, refs) for item in cast(list[Any], value)]
    return value


# The URI that opens a database file with the query's mode.
def _uri_make(path: str, query: str) -> str:
    return "file:" + urllib.parse.quote(path) + "?" + query


# Sets the pragmas of a new connection and checks the journal mode took.
def _pragmas_set(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
    if mode != "wal":
        raise RuntimeError(i18n("substrate.journal_mode", mode))
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")


# The cache hashes the rows of a database name, none when it lacks `_kv`.
def _hashes_read(connection: sqlite3.Connection) -> set[str]:
    found = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = '_kv'"
    ).fetchone()
    if found is None:
        return set()
    rows = connection.execute("SELECT sha256 FROM _kv WHERE data IS NULL")
    return {row[0].hex() for row in rows}


# The substrate's tables that a database holds.
def _tables_found(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_schema WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows} & _SCHEMA_TABLES


# Raises unless the tables found are all of the substrate's, at its version.
def _schema_check(connection: sqlite3.Connection, found: set[str]) -> None:
    if found != _SCHEMA_TABLES:
        raise RuntimeError(i18n("substrate.schema_partial", sorted(found)))
    row = connection.execute(
        "SELECT value FROM _meta WHERE name = 'schema'"
    ).fetchone()
    if row != (_SCHEMA_VERSION,):
        raise RuntimeError(
            i18n("substrate.schema_version", row, _SCHEMA_VERSION)
        )


# Raises unless a database file holds the substrate's tables, writing nothing.
def _schema_verify(path: str) -> None:
    connection = sqlite3.connect(
        _uri_make(path, _QUERY_READ), uri=True, isolation_level=None
    )
    try:
        _schema_check(connection, _tables_found(connection))
    finally:
        connection.close()


# Creates the substrate's `_` tables in a database that lacks them.
def schema_apply(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        found = _tables_found(connection)
        if found:
            _schema_check(connection, found)
        else:
            for statement in _SCHEMA_STATEMENTS:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO _meta (name, value) VALUES ('schema', ?)",
                (_SCHEMA_VERSION,),
            )
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


# Splits a `Key-Value-Ref` or `Document-Ref`. A bad ref raises.
def ref_split(ref: str) -> RefParts:
    if not ref.startswith("/"):
        if not ref:
            raise ValueError(i18n("substrate.ref_bad", ref))
        return RefParts(None, ref, _version_find(ref))
    match = _EXTERNAL_REF.fullmatch(ref)
    if match is None:
        raise ValueError(i18n("substrate.ref_bad", ref))
    return RefParts(match[1], match[2], _version_find(match[2]))


# Moves a document's reference strings into its headers `1` on.
def doc_encode(normal: dict[int | str, Any]) -> dict[int | str, Any]:
    header = _header_copy(normal)
    refs: dict[str, int] = {}
    body: dict[int | str, Any] = {}
    for key, value in normal.items():
        if isinstance(key, int):
            if key != 0:
                raise ValueError(i18n("substrate.header_normal", key))
        else:
            _key_check(key)
            body[key] = _refs_take(value, refs)
    encoded: dict[int | str, Any] = {0: header}
    for text, index in refs.items():
        encoded[index] = text
    encoded.update(body)
    return encoded


# Puts the headers' reference strings back where `{"$ref": n}` names them.
def doc_decode(encoded: dict[int | str, Any]) -> dict[int | str, Any]:
    header = _header_copy(encoded)
    refs: list[str] = []
    while len(refs) + 1 in encoded:
        text = encoded[len(refs) + 1]
        if not isinstance(text, str) or not _REFERENCE_STRING.fullmatch(text):
            raise ValueError(i18n("substrate.header_ref", len(refs) + 1))
        refs.append(text)
    normal: dict[int | str, Any] = {0: header}
    for key, value in encoded.items():
        if isinstance(key, int):
            if not 0 <= key <= len(refs):
                raise ValueError(i18n("substrate.header_gap", key))
        else:
            _key_check(key)
            normal[key] = _refs_restore(value, refs)
    return normal


# One owner's databases under one root. Methods run inside `transaction_run`.
class Store:
    # Keeps the root and the overflow limit and makes the cache directory.
    def __init__(self, root: str, overflow_bytes: int) -> None:
        self._root = os.path.abspath(root)
        self._cache = os.path.join(self._root, _CACHE_DIRECTORY)
        self._overflow_bytes = overflow_bytes
        self._connections: dict[str, sqlite3.Connection] = {}
        self._joined: list[sqlite3.Connection] | None = None
        self._unlinks: set[str] = set()
        os.makedirs(self._cache, exist_ok=True)

    # Opens `<root>/<name>.sqlite`, applying the schema.
    def db_open(self, name: str) -> None:
        _name_check(name)
        if name in self._connections:
            raise RuntimeError(i18n("substrate.db_open", name))
        connection = sqlite3.connect(
            _uri_make(self._path_find(name), _QUERY_WRITE),
            uri=True,
            isolation_level=None,
        )
        try:
            _pragmas_set(connection)
            schema_apply(connection)
        except BaseException:
            connection.close()
            raise
        self._connections[name] = connection

    # Closes an open database, which must not be inside a transaction.
    def db_close(self, name: str) -> None:
        connection = self._connection_get(name)
        if connection.in_transaction:
            raise RuntimeError(i18n("substrate.db_busy", name))
        connection.close()
        del self._connections[name]

    # The open database names.
    def db_list(self) -> list[str]:
        return sorted(self._connections)

    # Creates and opens a new database. Raises when the file exists.
    def db_create(self, name: str) -> None:
        _name_check(name)
        path = self._path_find(name)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        os.close(os.open(path, flags, _DB_MODE))
        try:
            self.db_open(name)
        except BaseException:
            os.remove(path)
            raise

    # Closes and deletes a database and its cache files.
    def db_drop(self, name: str) -> None:
        hashes = _hashes_read(self._connection_get(name))
        self.db_close(name)
        self._wal_check(name)
        os.remove(self._path_find(name))
        self._cache_prune(hashes)

    # The value a ref names. `db` is the database an internal ref is inside.
    def kv_get(self, ref: str, db: str | None = None) -> KvValue:
        name, key = self._ref_resolve(ref, db)
        connection = self._connection_get(name)
        row = connection.execute(
            "SELECT size, sha256, data FROM _kv WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            raise LookupError(i18n("substrate.key_missing", key, name))
        size, sha256, data = row
        if data is None:
            path = self._cache_path(sha256)
            if not os.path.isfile(path):
                raise LookupError(
                    i18n("substrate.file_lost", ref, sha256.hex())
                )
            return KvValue(path, size, sha256)
        return KvValue(data, size, sha256)

    # Writes the value, over `overflow_bytes` to the cache. Returns the row.
    def kv_put(
        self, ref: str, data: bytes | str, db: str | None = None
    ) -> KvRow:
        name, key = self._ref_resolve(ref, db)
        connection = self._connection_get(name)
        return self.transaction_run(
            lambda: self._value_put(connection, key, data)
        )

    # Deletes the row and its cache file when no other row shares the hash.
    def kv_delete(self, ref: str, db: str | None = None) -> None:
        name, key = self._ref_resolve(ref, db)
        connection = self._connection_get(name)
        self.transaction_run(lambda: self._value_delete(connection, key))

    # The rows of a database whose keys start with the prefix, by key.
    def kv_list(self, db: str, prefix: str) -> list[KvRow]:
        connection = self._connection_get(db)
        rows = connection.execute(
            "SELECT key, size, sha256 FROM _kv"
            " WHERE substr(key, 1, length(?1)) = ?1 ORDER BY key",
            (prefix,),
        ).fetchall()
        return [KvRow(*row) for row in rows]

    # Removes cache files no row names. Returns their count.
    def kv_check(self, db: str) -> int:
        self._connection_get(db)
        named = self._hashes_named()
        removed = 0
        for file_name in sorted(os.listdir(self._cache)):
            if file_name not in named:
                os.remove(os.path.join(self._cache, file_name))
                removed += 1
        return removed

    # The document a `Document-Ref` names, in its encoded form.
    def doc_get(self, ref: str, db: str | None = None) -> dict[int | str, Any]:
        if ref_split(ref).version is None:
            raise ValueError(i18n("substrate.document_ref", ref))
        return _document_parse(_value_read(self.kv_get(ref, db).data))

    # Writes version head plus one and moves the head. Returns the ref.
    def doc_put(self, db: str, id: str, body: dict[int | str, Any]) -> str:
        if not id:
            raise ValueError(i18n("substrate.id_empty"))
        doc_decode(body)
        data = _json_canonical(body).encode("utf-8")
        connection = self._connection_get(db)
        return self.transaction_run(
            lambda: self._document_put(db, connection, id, data)
        )

    # The current `Document-Ref` of an id. Raises on an unknown id.
    def doc_head(self, db: str, id: str) -> str:
        connection = self._connection_get(db)
        row = connection.execute(
            "SELECT version FROM _head WHERE id = ?", (id,)
        ).fetchone()
        if row is None:
            raise LookupError(i18n("substrate.id_missing", id, db))
        return f"/{db}/{id}/{row[0]}"

    # Appends a turn to the scene's conversation. Returns its `n`.
    def turn_append(self, scene: str, role: str, content: str) -> int:
        connection = self._connection_get(_scene_database(scene))
        return self.transaction_run(
            lambda: self._turn_add(connection, scene, role, content)
        )

    # The scene's turns in order.
    def turn_list(self, scene: str) -> list[TurnRow]:
        connection = self._connection_get(_scene_database(scene))
        rows = connection.execute(
            "SELECT scene, n, role, content FROM _turn"
            " WHERE scene = ? ORDER BY n",
            (scene,),
        ).fetchall()
        return [TurnRow(*row) for row in rows]

    # Runs the statements in order.
    def sql_run(
        self, db: str, statements: list[SqlStatement]
    ) -> list[SqlResult]:
        connection = self._connection_get(db)
        return self.transaction_run(
            lambda: self._statements_run(connection, statements)
        )

    # The `Connection.serialize` bytes, and the held cache files its rows name.
    def db_snapshot(self, db: str) -> DbImage:
        connection = self._connection_get(db)
        return self.transaction_run(lambda: self._snapshot_take(connection))

    # Replaces the file by a temp file and a rename, caches files by digest.
    def db_restore(
        self, db: str, data: bytes | str, files: list[bytes | str]
    ) -> None:
        _name_check(db)
        if isinstance(data, str):
            self._file_replace(db, data)
        else:
            temporary = self._path_find(db) + _RESTORE_SUFFIX
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            descriptor = os.open(temporary, flags, _DB_MODE)
            try:
                with os.fdopen(descriptor, "wb") as file:
                    file.write(data)
                self._file_replace(db, temporary)
            except BaseException:
                os.remove(temporary)
                raise
        for entry in files:
            if isinstance(entry, str):
                sha256 = _file_hash(entry)
            else:
                sha256 = hashlib.sha256(entry).digest()
            self._cache_store(sha256, entry)
        self.db_open(db)

    # Runs `fn` inside `BEGIN IMMEDIATE`: commit on return, rollback on raise.
    def transaction_run(self, fn: Callable[[], Any]) -> Any:
        if self._joined is not None:
            return fn()
        joined: list[sqlite3.Connection] = []
        self._joined = joined
        self._unlinks = set()
        try:
            result = fn()
            for connection in joined:
                connection.execute("COMMIT")
        except BaseException:
            for connection in joined:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
            raise
        finally:
            self._joined = None
        self._cache_prune(self._unlinks)
        return result

    # The file of a database under the root.
    def _path_find(self, name: str) -> str:
        return os.path.join(self._root, name + _DB_EXTENSION)

    # The connection of an open database. A database not open raises.
    def _connection_get(self, name: str) -> sqlite3.Connection:
        if name not in self._connections:
            raise LookupError(i18n("substrate.db_closed", name))
        return self._connections[name]

    # Begins the running transaction on a connection at its first write.
    def _transaction_join(self, connection: sqlite3.Connection) -> None:
        joined = cast(list[sqlite3.Connection], self._joined)
        if connection not in joined:
            connection.execute("BEGIN IMMEDIATE")
            joined.append(connection)

    # The database and key of a ref, `db` naming an internal ref's database.
    def _ref_resolve(self, ref: str, db: str | None) -> tuple[str, str]:
        parts = ref_split(ref)
        if parts.db is None:
            if db is None:
                raise ValueError(i18n("substrate.ref_internal", ref))
            return db, parts.key
        if db is not None:
            raise ValueError(i18n("substrate.ref_both", ref, db))
        return parts.db, parts.key

    # Raises when a closed database still has a write ahead log beside it.
    def _wal_check(self, name: str) -> None:
        if os.path.exists(self._path_find(name) + "-wal"):
            raise RuntimeError(i18n("substrate.wal_left", name))

    # Checks a file's tables, then closes the database and renames it over.
    def _file_replace(self, db: str, source: str) -> None:
        _schema_verify(source)
        if db in self._connections:
            self.db_close(db)
        self._wal_check(db)
        os.replace(source, self._path_find(db))

    # The cache file of a hash.
    def _cache_path(self, sha256: bytes) -> str:
        return os.path.join(self._cache, sha256.hex())

    # Puts a cache file in place: renames a file, or writes bytes then renames.
    def _cache_store(self, sha256: bytes, data: bytes | str) -> None:
        path = self._cache_path(sha256)
        if isinstance(data, str):
            os.replace(data, path)
        else:
            descriptor, temporary = tempfile.mkstemp(dir=self._cache)
            with os.fdopen(descriptor, "wb") as file:
                file.write(data)
            os.replace(temporary, path)

    # The hashes the rows with `data` NULL name, in every database file.
    def _hashes_named(self) -> set[str]:
        named: set[str] = set()
        for file_name in sorted(os.listdir(self._root)):
            name, extension = os.path.splitext(file_name)
            if extension != _DB_EXTENSION or not _C_IDENTIFIER.fullmatch(name):
                continue
            if name in self._connections:
                named |= _hashes_read(self._connections[name])
                continue
            connection = sqlite3.connect(
                _uri_make(self._path_find(name), _QUERY_WRITE),
                uri=True,
                isolation_level=None,
            )
            try:
                named |= _hashes_read(connection)
            finally:
                connection.close()
        return named

    # Removes the cache files of the hashes no row of any database names.
    def _cache_prune(self, hashes: set[str]) -> None:
        if not hashes:
            return
        named = self._hashes_named()
        for name in sorted(hashes - named):
            # An absent file meets the removal, and a read of it still fails.
            try:
                os.remove(os.path.join(self._cache, name))
            except FileNotFoundError:
                pass

    # Writes a row, its cache file first. A row of the same digest stays.
    def _row_write(
        self, connection: sqlite3.Connection, key: str, data: bytes | str
    ) -> KvRow:
        if isinstance(data, str):
            size = os.path.getsize(data)
            sha256 = _file_hash(data)
            if size <= self._overflow_bytes:
                raise ValueError(
                    i18n(
                        "substrate.file_small",
                        data,
                        size,
                        self._overflow_bytes,
                    )
                )
        else:
            size = len(data)
            sha256 = hashlib.sha256(data).digest()
        cached = size > self._overflow_bytes
        if cached:
            self._cache_store(sha256, data)
        row = KvRow(key, size, sha256)
        old = connection.execute(
            "SELECT sha256, data IS NULL FROM _kv WHERE key = ?", (key,)
        ).fetchone()
        if old is not None and old[0] == sha256:
            return row
        connection.execute(
            "INSERT INTO _kv (key, size, sha256, data) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (key) DO UPDATE SET size = excluded.size,"
            " sha256 = excluded.sha256, data = excluded.data",
            (key, size, sha256, None if cached else data),
        )
        if old is not None and old[1]:
            self._unlinks.add(old[0].hex())
        return row

    # Writes a value inside the transaction.
    def _value_put(
        self, connection: sqlite3.Connection, key: str, data: bytes | str
    ) -> KvRow:
        self._transaction_join(connection)
        return self._row_write(connection, key, data)

    # Deletes a row inside the transaction, a missing row a no op.
    def _value_delete(self, connection: sqlite3.Connection, key: str) -> None:
        self._transaction_join(connection)
        old = connection.execute(
            "SELECT sha256, data IS NULL FROM _kv WHERE key = ?", (key,)
        ).fetchone()
        if old is None:
            return
        connection.execute("DELETE FROM _kv WHERE key = ?", (key,))
        if old[1]:
            self._unlinks.add(old[0].hex())

    # Writes the next version of a document and moves its head.
    def _document_put(
        self, db: str, connection: sqlite3.Connection, id: str, data: bytes
    ) -> str:
        self._transaction_join(connection)
        row = connection.execute(
            "SELECT version FROM _head WHERE id = ?", (id,)
        ).fetchone()
        version = 1 if row is None else row[0] + 1
        key = f"{id}/{version}"
        exists = connection.execute(
            "SELECT 1 FROM _kv WHERE key = ?", (key,)
        ).fetchone()
        if exists is not None:
            raise RuntimeError(i18n("substrate.version_exists", key, db))
        self._row_write(connection, key, data)
        connection.execute(
            "INSERT INTO _head (id, version) VALUES (?, ?)"
            " ON CONFLICT (id) DO UPDATE SET version = excluded.version",
            (id, version),
        )
        return f"/{db}/{key}"

    # Inserts a turn after the last of its scene inside the transaction.
    def _turn_add(
        self,
        connection: sqlite3.Connection,
        scene: str,
        role: str,
        content: str,
    ) -> int:
        self._transaction_join(connection)
        n = connection.execute(
            "SELECT COALESCE(MAX(n), 0) + 1 FROM _turn WHERE scene = ?",
            (scene,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO _turn (scene, n, role, content) VALUES (?, ?, ?, ?)",
            (scene, n, role, content),
        )
        return n

    # Runs the statements, a trigger's refusal raised as the string it names.
    def _statements_run(
        self, connection: sqlite3.Connection, statements: list[SqlStatement]
    ) -> list[SqlResult]:
        self._transaction_join(connection)
        results: list[SqlResult] = []
        for statement in statements:
            before = connection.total_changes
            try:
                cursor = connection.execute(statement.sql, statement.params)
            except sqlite3.DatabaseError as error:
                for name in _TRIGGER_NAMES:
                    if str(error).endswith(name):
                        raise ValueError(i18n(name)) from error
                raise
            rows = [list(row) for row in cursor.fetchall()]
            columns: list[str] = []
            if cursor.description is not None:
                columns = [column[0] for column in cursor.description]
            changed = connection.total_changes - before
            results.append(SqlResult(columns, rows, changed))
        return results

    # Serializes the database and lists its held cache files, in a transaction.
    def _snapshot_take(self, connection: sqlite3.Connection) -> DbImage:
        self._transaction_join(connection)
        paths = [
            os.path.join(self._cache, name)
            for name in sorted(_hashes_read(connection))
        ]
        files = [path for path in paths if os.path.isfile(path)]
        return DbImage(connection.serialize(), files)
