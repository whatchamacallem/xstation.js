-- Applied to every database by db_open. meta holds name, schema and seq.
CREATE TABLE meta (
    name  TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID, STRICT;

-- Values by key. data is NULL when the value is in the cache by sha256.
-- seq is meta's seq, incremented in the same transaction as the write.
CREATE TABLE kv (
    key    TEXT    PRIMARY KEY,
    size   INTEGER NOT NULL,
    sha256 BLOB    NOT NULL,
    data   BLOB,
    seq    INTEGER NOT NULL UNIQUE
) WITHOUT ROWID, STRICT;

-- Deletions, for replication. A put of a gone key removes its row.
CREATE TABLE kv_gone (
    key TEXT    PRIMARY KEY,
    seq INTEGER NOT NULL UNIQUE
) WITHOUT ROWID, STRICT;

-- Immutable document versions. A Document-Ref is path || '/' || version.
CREATE TABLE doc (
    path    TEXT    NOT NULL,
    version INTEGER NOT NULL,
    body    TEXT    NOT NULL CHECK (json_valid(body)),
    seq     INTEGER NOT NULL UNIQUE,
    PRIMARY KEY (path, version)
) WITHOUT ROWID, STRICT;

-- The current version of each path.
CREATE TABLE doc_head (
    path    TEXT    PRIMARY KEY,
    version INTEGER NOT NULL
) WITHOUT ROWID, STRICT;
