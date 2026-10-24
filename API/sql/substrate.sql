-- The substrate's tables, created on first use in every database it
-- opens. The prefix keeps them apart from the scripts' tables.

-- _meta holds schema, the version of these tables. Nothing counts the
-- changes of a database: the stores sync by plain messages and whole blobs.
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
-- within the scene; content is one provider message as JSON. The browser's
-- compaction deletes turns 1 to N and inserts one summary row at n 1; the
-- server never compacts.
CREATE TABLE _turn (
    scene   TEXT    NOT NULL,
    n       INTEGER NOT NULL,
    role    TEXT    NOT NULL,
    content TEXT    NOT NULL CHECK (json_valid(content)),
    PRIMARY KEY (scene, n)
) WITHOUT ROWID, STRICT;
