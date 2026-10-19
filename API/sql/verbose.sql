-- The server's _verbose database, not replicated. Lines from the server
-- itself and, in debug mode, from the page's verbose.put. at is
-- milliseconds since the epoch; thread is ui, ai or server.
CREATE TABLE line (
    seq    INTEGER PRIMARY KEY,
    at     INTEGER NOT NULL,
    thread TEXT    NOT NULL,
    level  INTEGER NOT NULL,
    text   TEXT    NOT NULL
) STRICT;
