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

# Creates the substrate's `_` tables in a database that lacks them.
def schema_apply(connection: sqlite3.Connection) -> None: ...

# Splits a `Key-Value-Ref` or `Document-Ref`. A bad ref raises.
def ref_split(ref: str) -> RefParts: ...

# Moves a document's reference strings into its headers `"1"` on.
def doc_encode(normal: dict[str, Any]) -> dict[str, Any]: ...

# Puts the headers' reference strings back where `{"$ref": n}` names them.
def doc_decode(encoded: dict[str, Any]) -> dict[str, Any]: ...

# One owner's databases under one root. Methods run inside `transaction_run`.
class Store:
    def __init__(self, root: str, overflow_bytes: int) -> None: ...
    # Opens `<root>/<name>.sqlite`, applying the schema. Returns its `seq`.
    def db_open(self, name: str) -> int: ...
    def db_close(self, name: str) -> None: ...
    # The open database names.
    def db_list(self) -> list[str]: ...
    # Creates and opens a new database. Raises when the file exists.
    def db_create(self, name: str) -> None: ...
    # Closes and deletes a database and its cache files.
    def db_drop(self, name: str) -> None: ...
    # The value a ref names. `db` is the database an internal ref is inside.
    def kv_get(self, ref: str, db: str | None = None) -> KvValue: ...
    # Writes the value, over `overflow_bytes` to the cache. Returns row, `seq`.
    def kv_put(
        self, ref: str, data: bytes | str, db: str | None = None
    ) -> tuple[KvRow, int]: ...
    # Deletes the row and its cache file when no other row shares the hash.
    def kv_delete(self, ref: str, db: str | None = None) -> int: ...
    def kv_list(self, db: str, prefix: str) -> list[KvRow]: ...
    # Removes cache files no row names. Returns their count.
    def kv_check(self, db: str) -> int: ...
    # The document a `Document-Ref` names, in its encoded form.
    def doc_get(self, ref: str, db: str | None = None) -> dict[str, Any]: ...
    # Writes version head plus one and moves the head. Returns ref and `seq`.
    def doc_put(
        self, db: str, id: str, body: dict[str, Any]
    ) -> tuple[str, int]: ...
    # The current `Document-Ref` of an id. Raises on an unknown id.
    def doc_head(self, db: str, id: str) -> str: ...
    # Appends a turn to the scene's conversation. Returns its `n` and `seq`.
    def turn_append(
        self, scene: str, role: str, content: str
    ) -> tuple[int, int]: ...
    # The scene's turns in order.
    def turn_list(self, scene: str) -> list[TurnRow]: ...
    # Replaces turns 1 to `through` with one summary turn at `n` 1.
    def turn_compact(self, scene: str, through: int, summary: str) -> int: ...
    # Runs the statements in order. Writing `_` tables or `_settings` raises.
    def sql_run(
        self, db: str, statements: list[SqlStatement]
    ) -> list[SqlResult]: ...
    # `Connection.serialize` bytes, and the database's `seq`.
    def db_snapshot(self, db: str) -> tuple[bytes, int]: ...
    # Replaces the database file by a temp file and a rename. Returns `seq`.
    def db_restore(self, db: str, data: bytes | str) -> int: ...
    # Applies one forwarded operation when `since` is the database's `seq`.
    def operation_apply(
        self, type: str, since: int, **payload: Any
    ) -> int: ...
    # Runs `fn` inside `BEGIN IMMEDIATE`: commit on return, rollback on raise.
    def transaction_run(self, fn: Callable[[], Any]) -> Any: ...
