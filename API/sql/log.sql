-- The server's log database, not replicated. Lines from the server
-- itself and, in debug mode, from the page's log.put.
CREATE TABLE log (
    seq    INTEGER PRIMARY KEY,
    at     INTEGER NOT NULL,
    thread TEXT    NOT NULL,
    level  INTEGER NOT NULL,
    text   TEXT    NOT NULL
) STRICT;
