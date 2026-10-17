import sqlite3
from collections.abc import Callable
from typing import Any, NamedTuple, TypeVar

T = TypeVar("T")

# A `kv` row without its data; `data` is fetched by `kv_get`.
class KvRow(NamedTuple):
    key: str
    size: int
    sha256: bytes
    seq: int

# A `kv_gone` tombstone.
class GoneRow(NamedTuple):
    key: str
    seq: int

# A `doc` row. A path is `<db>/<kind>/<name>`; a Document-Ref is the path
# and `/<version>`, so the ref names its database with no lookup.
class DocRow(NamedTuple):
    path: str
    version: int
    body: str
    seq: int

# A `doc_head` row.
class HeadRow(NamedTuple):
    path: str
    version: int

# A `turn` row of metaverse: `n` within the scene, `seq` in the database.
class TurnRow(NamedTuple):
    scene: str
    n: int
    role: str
    content: str
    seq: int

# What `sync_pull` returns and `sync_apply` takes: rows above a `seq`.
class SyncRows(NamedTuple):
    seq: int
    kv: list[KvRow]
    gone: list[GoneRow]
    doc: list[DocRow]
    head: list[HeadRow]
    turn: list[TurnRow]

# One SQL statement with its bound parameters, never string built.
class SqlStatement(NamedTuple):
    sql: str
    params: list[Any]

# The result of one statement: column names, rows, rows changed.
class SqlResult(NamedTuple):
    columns: list[str]
    rows: list[list[Any]]
    changes: int

# The value of a key: its bytes, or the cache file's path when over
# `overflow_bytes`, with its size and hash.
class KvValue(NamedTuple):
    data: bytes | str
    size: int
    sha256: bytes

# Creates the engine tables of `kind` (`engine`, `metaverse`, `log`) and
# records `schema` in `meta`. Applied by `db_open` to a new database.
def schema_apply(connection: sqlite3.Connection, kind: str) -> None: ...

# One owner's databases under one root. Every method runs inside the
# transaction `transaction_run` opens; none issues BEGIN or COMMIT.
class Store:
    def __init__(self, root: str, overflow_bytes: int) -> None: ...
    # Opens `<root>/<name>.sqlite`, creating it with `schema_apply`.
    # Returns its `seq`.
    def db_open(self, name: str, kind: str) -> int: ...
    def db_close(self, name: str) -> None: ...
    # The open database names.
    def db_list(self) -> list[str]: ...
    # Attaches a region database to a universe connection as `region`.
    def db_attach(self, universe: str, region: str) -> None: ...
    def db_detach(self, universe: str) -> None: ...
    def kv_get(self, db: str, key: str) -> KvValue: ...
    # Writes the value; over `overflow_bytes` it goes to the cache. A path
    # from the streaming decoder is renamed into the cache, not copied.
    # Returns the row's `sha256` and `seq`.
    def kv_put(self, db: str, key: str, data: bytes | str) -> KvRow: ...
    # Returns the tombstone's `seq`.
    def kv_delete(self, db: str, key: str) -> int: ...
    def kv_list(self, db: str, prefix: str) -> list[KvRow]: ...
    # Removes cache files no row names. Returns their count.
    def kv_check(self, db: str) -> int: ...
    # The body of a ref. Raises on an unknown ref or an unopened database.
    def doc_get(self, ref: str) -> str: ...
    # Writes `head + 1` and moves the head. Returns the new ref and `seq`.
    def doc_put(self, path: str, body: str) -> tuple[str, int]: ...
    # The current ref of a path. Raises on an unknown path.
    def doc_head(self, path: str) -> str: ...
    # Splits a ref or path: database, kind, name, and version or None.
    def ref_split(self, ref: str) -> tuple[str, str, str, int | None]: ...
    # Appends a turn to the scene's conversation. Returns its `n`.
    def turn_append(self, scene: str, role: str, content: str) -> int: ...
    # The scene's turns in order.
    def turn_list(self, scene: str) -> list[TurnRow]: ...
    # Replaces turns 1 to `through` with one summary turn at `n` 1.
    def turn_compact(self, scene: str, through: int, summary: str) -> None: ...
    # Runs the statements in order in the current transaction.
    def sql_run(self, db: str, statements: list[SqlStatement]) -> list[SqlResult]: ...
    # `Connection.serialize` bytes, and the database's `seq`.
    def db_snapshot(self, db: str) -> tuple[bytes, int]: ...
    # Replaces the database file by a temp file and a rename.
    def db_restore(self, db: str, data: bytes | str) -> int: ...
    # Rows above `since`, without `kv` data.
    def sync_pull(self, db: str, since: int) -> SyncRows: ...
    # Applies rows from the peer, keeping their `seq`; `blobs` maps a
    # `sha256` to the bytes or path for rows whose data the store lacks.
    def sync_apply(self, db: str, rows: SyncRows, blobs: dict[bytes, bytes | str]) -> int: ...
    # Runs `fn` inside `BEGIN IMMEDIATE` on every open database, commits
    # on return, rolls back on raise and re-raises.
    def transaction_run(self, fn: Callable[[], T]) -> T: ...
