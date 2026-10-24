# The handlers of `db.create` and `db.drop`, the browser's commits, which the
# server applies to its own store as plain messages and never answers. And
# the lines of a whole database: `restore_lines` yields `db.restore` with the
# database file as blob 1 and `files` set, then one `db.file` per cache file
# the server holds for it, each with that file as blob 1, for the main loop
# to write in order. A cache file the server lost is not among them.

from collections.abc import Iterator

import jslb, substrate

# `db.create`: creates and opens the database.
def db_create(line: jslb.Object, *, db: str) -> None: ...

# `db.drop`: closes and deletes the database and its cache files.
def db_drop(line: jslb.Object, *, db: str) -> None: ...

# The `db.restore` line of a database, then its `db.file` lines.
def restore_lines(db: str, full: bool) -> Iterator[jslb.Object]: ...

# Registers the handlers on the store given.
def handlers_register(store: substrate.Store) -> None: ...
