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

-- A world belongs to one universe at most. A second row naming a world
-- would make the current universe ambiguous, so it is refused before it is
-- added, in every store and by every path a write takes. The message is the
-- name of the string the store throws in its place.
CREATE TRIGGER universe_world_insert BEFORE INSERT ON universe
WHEN EXISTS (
    SELECT 1 FROM universe WHERE world = NEW.world AND name <> NEW.name
)
BEGIN
    SELECT RAISE(ABORT, 'agent.content_ambiguous');
END;

CREATE TRIGGER universe_world_update BEFORE UPDATE OF world ON universe
WHEN EXISTS (
    SELECT 1 FROM universe WHERE world = NEW.world AND name <> OLD.name
)
BEGIN
    SELECT RAISE(ABORT, 'agent.content_ambiguous');
END;
