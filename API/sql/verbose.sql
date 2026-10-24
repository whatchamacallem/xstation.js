-- The server's _verbose database, which the store never opens and never
-- sends. Lines from the server itself and, in debug mode, from the page's
-- verbose.put. at is milliseconds since the epoch; thread is ui, ai or
-- server; seq is the order the lines were written in.
CREATE TABLE line (
    seq    INTEGER PRIMARY KEY,
    at     INTEGER NOT NULL,
    thread TEXT    NOT NULL,
    text   TEXT    NOT NULL
) STRICT;
