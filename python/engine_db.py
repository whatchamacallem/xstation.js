# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the `db.create`, `db.drop`, `db.snapshot` and `db.chunk`
# lines, over the substrate's databases. A create and a drop are forwarded
# operations that carry `since` and go through `operation_apply`: a create's
# `since` is 0, the `seq` a database has before it exists and keeps when
# created, a drop's is the database's `seq`. A snapshot keeps the bytes of
# the database file and replies with their head, and each chunk replies with
# the piece the reader asks for as blob 1, so that every reply fits
# `message_max` however large the database.

import dispatch, jslb, substrate
from i18n import i18n


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


# Creates a database as a forwarded operation. The reply is empty.
def db_create(line: jslb.Object, *, db: str, since: int) -> jslb.Object:
    _store_get().operation_apply("db.create", since, db=db)
    return dispatch.reply_make(line)


# Drops a database as a forwarded operation. The reply is empty.
def db_drop(line: jslb.Object, *, db: str, since: int) -> jslb.Object:
    _store_get().operation_apply("db.drop", since, db=db)
    return dispatch.reply_make(line)


# Keeps a snapshot and replies its number, `size`, `sha256` and `seq`.
def db_snapshot(line: jslb.Object, *, db: str) -> jslb.Object:
    head = _store_get().snapshot_keep(db)
    return dispatch.reply_make(
        line,
        snapshot=head.snapshot,
        size=head.size,
        sha256=head.sha256.hex(),
        seq=head.seq,
    )


# Replies with `size` bytes of a kept snapshot from `offset` as blob 1.
def db_chunk(
    line: jslb.Object, *, snapshot: int, offset: int, size: int
) -> jslb.Object:
    data = _store_get().snapshot_read(snapshot, offset, size)
    return dispatch.reply_make(line, [jslb.blob_make(data)])


# Registers the handlers, with the store whose databases they serve.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("db.create", 0, db_create)
    dispatch.handler_register("db.drop", 0, db_drop)
    dispatch.handler_register("db.snapshot", 0, db_snapshot)
    dispatch.handler_register("db.chunk", 0, db_chunk)
