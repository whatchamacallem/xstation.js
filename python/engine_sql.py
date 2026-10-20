# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handler of the `sql.run` line, a forwarded commit of statements. It
# carries `since`, so it checks that against the `seq` of the database itself,
# as `operation_apply` does, because the reply needs the results of the
# statements and `operation_apply` returns only the `seq`.

import dispatch, jslb, substrate
from i18n import i18n
from typing import Any, cast


# The store the registration sets, which is empty until then.
class _StoreState:
    # Starts with no store.
    def __init__(self) -> None:
        self.store: substrate.Store | None = None


# The one state of the module.
_STATE = _StoreState()


# Returns the store, raising before the handler is registered.
def _store_get() -> substrate.Store:
    if _STATE.store is None:
        raise RuntimeError(i18n("engine_sql.not_registered"))
    return _STATE.store


# Checks `since`, runs the statements, then reads their results and the `seq`.
def _statements_apply(
    store: substrate.Store,
    db: str,
    statements: list[substrate.SqlStatement],
    since: int,
) -> tuple[list[dict[str, Any]], int]:
    seq = store.seq_get(db)
    if since != seq:
        raise RuntimeError(
            i18n("substrate.since_stale", "sql.run", since, seq, db)
        )
    results: list[dict[str, Any]] = [
        {
            "columns": result.columns,
            "rows": result.rows,
            "changes": result.changes,
        }
        for result in store.sql_run(db, statements)
    ]
    return results, store.seq_get(db)


# Runs the statements as a forwarded commit. Replies with `results`, `seq`.
def sql_run(
    line: jslb.Object,
    *,
    db: str,
    statements: list[dict[str, object]],
    since: int,
) -> jslb.Object:
    store = _store_get()
    parsed = [
        substrate.SqlStatement(**cast(dict[str, Any], statement))
        for statement in statements
    ]
    results, seq = store.transaction_run(
        lambda: _statements_apply(store, db, parsed, since)
    )
    return dispatch.reply_make(line, results=results, seq=seq)


# Registers the handler, with the store whose databases it runs statements in.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("sql.run", 0, sql_run)
