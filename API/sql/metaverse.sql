-- Added to metaverse after engine.sql. The world, the preferences and the
-- universe catalogue are documents: paths metaverse/world/main,
-- metaverse/preferences/main and metaverse/universe/<name> in doc.

-- The conversation of each scene, by the scene's Document-Ref. n counts
-- within the scene; seq is meta's seq, for replication. content is one
-- provider message as JSON. Compaction deletes turns 1 to N and inserts
-- one summary row at n 1.
CREATE TABLE turn (
    scene   TEXT    NOT NULL,
    n       INTEGER NOT NULL,
    role    TEXT    NOT NULL,
    content TEXT    NOT NULL CHECK (json_valid(content)),
    seq     INTEGER NOT NULL UNIQUE,
    PRIMARY KEY (scene, n)
) WITHOUT ROWID, STRICT;
