-- The server's _verbose database, which the store never opens and never
-- sends, written outside debug mode alone, by the server itself. at is
-- milliseconds since the epoch; thread is server; seq is the order the lines
-- were written in.
CREATE TABLE line (
    seq    INTEGER PRIMARY KEY,
    at     INTEGER NOT NULL,
    thread TEXT    NOT NULL,
    text   TEXT    NOT NULL
) STRICT;
