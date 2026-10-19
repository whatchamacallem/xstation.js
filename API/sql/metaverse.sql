-- Seeded in metaverse by the server, the one fixed experience table:
-- which player is in which universe and which of its worlds. The
-- bootstrap script writes it. The player in use is the KV row player,
-- the database of the current world the KV row world, and the current
-- scene the Document-Ref in that database's KV row scene.
CREATE TABLE universe (
    name   TEXT PRIMARY KEY,
    title  TEXT NOT NULL,
    player TEXT NOT NULL,
    world  TEXT NOT NULL
) WITHOUT ROWID, STRICT;
