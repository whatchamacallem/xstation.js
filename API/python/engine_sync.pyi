from typing import Any

from jslb import Object

# Handlers of the `sync.*` and `db.*` lines on the wire.

# `sync.pull`: reply with `seq` and the `kv`, `gone`, `doc`, `head` and
# `turn` rows above `since`, without `kv` data.
def sync_pull(line: Object, *, db: str, since: int) -> Object: ...

# `sync.push`: rows from the browser with one blob per hash in `blobs`,
# in that order; reply with `seq`.
def sync_push(
    line: Object,
    *,
    db: str,
    seq: int,
    kv: list[dict[str, Any]],
    gone: list[dict[str, Any]],
    doc: list[dict[str, Any]],
    head: list[dict[str, Any]],
    turn: list[dict[str, Any]],
    blobs: list[str],
) -> Object: ...

# `db.open`: reply with `seq`.
def db_open(line: Object, *, db: str, kind: str) -> Object: ...

# `db.list`: reply with `dbs`, each `db` and `seq`.
def db_list(line: Object) -> Object: ...

# `db.snapshot`: reply with `sha256`, `seq` and the file as one blob.
def db_snapshot(line: Object, *, db: str) -> Object: ...

# `db.restore`: one blob in; reply with `sha256` and `seq`.
def db_restore(line: Object, *, db: str) -> Object: ...

# `sql.run` on a server database, debug mode only: reply with `results`.
def sql_run(line: Object, *, db: str, statements: list[dict[str, Any]]) -> Object: ...
