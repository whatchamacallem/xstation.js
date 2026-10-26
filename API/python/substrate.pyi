# The server's store: one connection for each database file under a root,
# the substrate's tables in each, and the cache directory `<root>/cache`,
# which holds the values over `overflow_bytes` by their digest. It applies
# the browser's committed operations as plain messages, through the same
# methods as any caller, and keeps more history than the browser: it never
# compacts turns. Nothing here numbers, orders or checks a change against
# another store.
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

import sqlite3
from collections.abc import Callable
from typing import Any, NamedTuple

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

# Creates the substrate's `_` tables in a database that lacks them.
def schema_apply(connection: sqlite3.Connection) -> None: ...

# Splits a `Key-Value-Ref` or `Document-Ref`. A bad ref raises.
def ref_split(ref: str) -> RefParts: ...

# Moves a document's reference strings into its headers `1` on.
def doc_encode(normal: dict[int | str, Any]) -> dict[int | str, Any]: ...

# Puts the headers' reference strings back where `{"$ref": n}` names them.
def doc_decode(encoded: dict[int | str, Any]) -> dict[int | str, Any]: ...

# One owner's databases under one root. Methods run inside `transaction_run`.
class Store:
    def __init__(self, root: str, overflow_bytes: int) -> None: ...
    # Opens `<root>/<name>.sqlite`, applying the schema.
    def db_open(self, name: str) -> None: ...
    def db_close(self, name: str) -> None: ...
    # The open database names.
    def db_list(self) -> list[str]: ...
    # Creates and opens a new database. Raises when the file exists.
    def db_create(self, name: str) -> None: ...
    # Closes and deletes a database and its cache files.
    def db_drop(self, name: str) -> None: ...
    # The value a ref names. `db` is the database an internal ref is inside.
    def kv_get(self, ref: str, db: str | None = None) -> KvValue: ...
    # Writes the value, over `overflow_bytes` to the cache. Returns the row.
    def kv_put(
        self, ref: str, data: bytes | str, db: str | None = None
    ) -> KvRow: ...
    # Deletes the row and its cache file when no other row shares the hash.
    def kv_delete(self, ref: str, db: str | None = None) -> None: ...
    def kv_list(self, db: str, prefix: str) -> list[KvRow]: ...
    # Removes cache files no row names. Returns their count.
    def kv_check(self, db: str) -> int: ...
    # The document a `Document-Ref` names, in its encoded form.
    def doc_get(
        self, ref: str, db: str | None = None
    ) -> dict[int | str, Any]: ...
    # Writes version head plus one and moves the head. Returns the ref.
    def doc_put(self, db: str, id: str, body: dict[int | str, Any]) -> str: ...
    # The current `Document-Ref` of an id. Raises on an unknown id.
    def doc_head(self, db: str, id: str) -> str: ...
    # Appends a turn to the scene's conversation. Returns its `n`.
    def turn_append(self, scene: str, role: str, content: str) -> int: ...
    # The scene's turns in order.
    def turn_list(self, scene: str) -> list[TurnRow]: ...
    # Runs the statements in order.
    def sql_run(
        self, db: str, statements: list[SqlStatement]
    ) -> list[SqlResult]: ...
    # The `Connection.serialize` bytes, and the held cache files its rows name.
    def db_snapshot(self, db: str) -> DbImage: ...
    # Replaces the file by a temp file and a rename, caches files by digest.
    def db_restore(
        self, db: str, data: bytes | str, files: list[bytes | str]
    ) -> None: ...
    # Runs `fn` inside `BEGIN IMMEDIATE`: commit on return, rollback on raise.
    def transaction_run(self, fn: Callable[[], Any]) -> Any: ...
