# The handlers of `db.create` and `db.drop`, the browser's commits, which the
# server applies to its own store as plain messages and never answers. And
# the lines of a whole database: `restore_lines` yields `db.restore` with the
# database file as blob 1 and `files` set, then one `db.file` per cache file
# the server holds for it, each with that file as blob 1, for the main loop
# to write in order. A cache file the server lost is not among them.
#
# `db.sync`, the browser's one pull, answers with a `dispatch.Stream`: the
# `restore_lines` of every database the store holds, in name order, each built
# from its snapshot as the main loop reaches it, then the reply `DbSyncReply`,
# whose `databases` names them in that order. The pushes take the name form of
# the parameter `debug`, since a push answers nothing, and the reply that of
# the request.

from collections.abc import Iterator

import dispatch, jslb, substrate

# `db.create`: creates and opens the database.
def db_create(line: jslb.Object, *, db: str) -> None: ...

# `db.drop`: closes and deletes the database and its cache files.
def db_drop(line: jslb.Object, *, db: str) -> None: ...

# The `db.restore` line of a database, then its `db.file` lines.
def restore_lines(db: str, full: bool) -> Iterator[jslb.Object]: ...

# `db.sync`: the lines of every database, then the reply naming them.
def db_sync(line: jslb.Object) -> dispatch.Stream: ...

# Registers the handlers on the store given.
def handlers_register(store: substrate.Store) -> None: ...
