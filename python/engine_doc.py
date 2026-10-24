# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handler of `doc.put`, the browser's commit, which the server applies
# to its own store as a plain message and never answers: the server writes
# its own next version, whatever version the browser's was. The body arrives
# decoded, its header keys integers.

import dispatch, jslb, substrate
from internationalization import i18n
from typing import Any


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
        raise RuntimeError(i18n("engine_doc.not_registered"))
    return _STATE.store


# `doc.put`: writes the next version of the document and moves its head.
def doc_put(
    line: jslb.Object, *, db: str, id: str, body: dict[int | str, Any]
) -> None:
    _store_get().doc_put(db, id, body)


# Registers the handler on the store given.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("doc.put", 0, doc_put)
