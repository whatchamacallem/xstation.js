# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handler of `sql.run`, the browser's commit of statements that changed
# its database, which the server runs on its own store in one transaction as
# a plain message and never answers.

import dispatch, jslb, substrate
from internationalization import i18n
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


# `sql.run`: runs the statements in order in one transaction.
def sql_run(
    line: jslb.Object,
    *,
    db: str,
    statements: list[dict[str, object]],
) -> None:
    store = _store_get()
    parsed = [
        substrate.SqlStatement(**cast(dict[str, Any], statement))
        for statement in statements
    ]
    store.sql_run(db, parsed)


# Registers the handler on the store given.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("sql.run", 0, sql_run)
