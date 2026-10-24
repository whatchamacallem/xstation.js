# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of `db.create` and `db.drop`, the browser's commits, which the
# server applies to its own store as plain messages and never answers. And
# the lines of a whole database: `restore_lines` yields `db.restore` with the
# database file as blob 1 and `files` set, then one `db.file` per cache file
# the server holds for it, each with that file as blob 1, for the main loop
# to write in order. A cache file the server lost is not among them.

import dispatch, jslb, substrate
from collections.abc import Iterator
from internationalization import i18n


# The store the registration sets, which is empty until then.
class _StoreState:
    # Starts with no store.
    def __init__(self) -> None:
        self.store: substrate.Store | None = None


# The one state of the module.
_STATE = _StoreState()


# Returns the store, raising before the handlers are registered.
def _store_get() -> substrate.Store:
    if _STATE.store is None:
        raise RuntimeError(i18n("engine_db.not_registered"))
    return _STATE.store


# `db.create`: creates and opens the database.
def db_create(line: jslb.Object, *, db: str) -> None:
    _store_get().db_create(db)


# `db.drop`: closes and deletes the database and its cache files.
def db_drop(line: jslb.Object, *, db: str) -> None:
    _store_get().db_drop(db)


# The `db.restore` line of a database, then its `db.file` lines.
def restore_lines(db: str, full: bool) -> Iterator[jslb.Object]:
    image = _store_get().db_snapshot(db)
    yield jslb.line_make(
        jslb.header_make("db.restore", full=full),
        [jslb.blob_make(image.data)],
        db=db,
        files=len(image.files),
    )
    for path in image.files:
        yield jslb.line_make(
            jslb.header_make("db.file", full=full),
            [jslb.blob_make(path)],
            db=db,
        )


# Registers the handlers on the store given.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("db.create", 0, db_create)
    dispatch.handler_register("db.drop", 0, db_drop)
