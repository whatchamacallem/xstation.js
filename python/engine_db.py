# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the `db.create`, `db.drop` and `db.snapshot` lines, over the
# substrate's databases. A create and a drop are forwarded operations that
# carry `since` and go through `operation_apply`. A snapshot replies with the
# bytes of the database file as blob 1.

import dispatch, hashlib, jslb, substrate
from i18n import i18n


# The state the registration sets, which is empty until then.
class _State:
    # Starts with no store.
    def __init__(self) -> None:
        self.store: substrate.Store | None = None


# The one state of the module.
_STATE = _State()


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


# Replies with the `sha256` and `seq` of a database and its file as blob 1.
def db_snapshot(line: jslb.Object, *, db: str) -> jslb.Object:
    data, seq = _store_get().db_snapshot(db)
    return dispatch.reply_make(
        line,
        [jslb.blob_make(data)],
        sha256=hashlib.sha256(data).hexdigest(),
        seq=seq,
    )


# Registers the handlers, with the store whose databases they create and drop.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("db.create", 0, db_create)
    dispatch.handler_register("db.drop", 0, db_drop)
    dispatch.handler_register("db.snapshot", 0, db_snapshot)
