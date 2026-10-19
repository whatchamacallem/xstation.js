-- The substrate's tables, created on first use in every database it
-- opens. The prefix keeps them apart from the scripts' tables; a write
-- to one of them through sql_run is refused.

-- _meta holds seq, incremented in the same transaction as every
-- modifying operation, and schema.
CREATE TABLE _meta (
    name  TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID, STRICT;

-- The KV accessor. A document is the row its Document-Ref names, the key
-- $id/$version. data is NULL when the value is in the cache by sha256.
CREATE TABLE _kv (
    key    TEXT    PRIMARY KEY,
    size   INTEGER NOT NULL,
    sha256 BLOB    NOT NULL,
    data   BLOB
) WITHOUT ROWID, STRICT;

-- The current version of each document id.
CREATE TABLE _head (
    id      TEXT    PRIMARY KEY,
    version INTEGER NOT NULL
) WITHOUT ROWID, STRICT;

-- The conversation of each scene, by the scene's Document-Ref. n counts
-- within the scene; content is one provider message as JSON. Compaction
-- deletes turns 1 to N and inserts one summary row at n 1.
CREATE TABLE _turn (
    scene   TEXT    NOT NULL,
    n       INTEGER NOT NULL,
    role    TEXT    NOT NULL,
    content TEXT    NOT NULL CHECK (json_valid(content)),
    PRIMARY KEY (scene, n)
) WITHOUT ROWID, STRICT;
