# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the `doc.put` and `doc.head` lines, over the substrate's
# documents. A put is a forwarded operation that carries `since` and goes
# through `operation_apply`: it writes the next version and moves the head.
# The body arrives decoded, its header keys integers.

import dispatch, jslb, substrate
from i18n import i18n
from typing import Any


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
        raise RuntimeError(i18n("engine_doc.not_registered"))
    return _STATE.store


# Applies the put, then reads the ref of the version it wrote.
def _document_apply(
    store: substrate.Store,
    db: str,
    id: str,
    body: dict[int | str, Any],
    since: int,
) -> tuple[int, str]:
    seq = store.operation_apply("doc.put", since, db=db, id=id, body=body)
    return seq, store.doc_head(db, id)


# Writes the next version of a document as a forwarded operation.
def doc_put(
    line: jslb.Object,
    *,
    db: str,
    id: str,
    body: dict[int | str, Any],
    since: int,
) -> jslb.Object:
    store = _store_get()
    seq, ref = store.transaction_run(
        lambda: _document_apply(store, db, id, body, since)
    )
    return dispatch.reply_make(line, ref=ref, seq=seq)


# Replies with the `ref` of the current version of a document.
def doc_head(line: jslb.Object, *, db: str, id: str) -> jslb.Object:
    ref = _store_get().doc_head(db, id)
    return dispatch.reply_make(line, ref=ref)


# Registers the handlers, with the store whose documents they read and write.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("doc.put", 0, doc_put)
    dispatch.handler_register("doc.head", 0, doc_head)
