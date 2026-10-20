# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the `kv.get`, `kv.put`, `kv.delete` and `kv.list` lines,
# over the substrate's rows of values. The ref a line names is its header key
# and a value travels as blob 1. A put and a delete are forwarded operations
# that carry `since` and go through `operation_apply`.

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
        raise RuntimeError(i18n("engine_kv.not_registered"))
    return _STATE.store


# Returns the ref in the header key of a line, raising when it has none.
def _ref_get(line: jslb.Object) -> str:
    ref: str | None = jslb.field_get(line[0], "key")
    if ref is None:
        name: str = jslb.field_get(line[0], "type")
        raise ValueError(i18n("engine_kv.key_missing", name))
    return ref


# Returns the data of blob 1, raising when the line carries no blob.
def _blob_get(line: jslb.Object) -> bytes | str:
    if 1 not in line:
        name: str = jslb.field_get(line[0], "type")
        raise ValueError(i18n("engine_kv.blob_missing", name))
    data: bytes | str = jslb.field_get(line[1], "data")
    return data


# Applies the put, then reads the hash of the stored value as hex.
def _put_apply(
    store: substrate.Store, ref: str, data: bytes | str, since: int
) -> tuple[int, str]:
    seq = store.operation_apply("kv.put", since, k=ref, data=data)
    return seq, store.kv_get(ref).sha256.hex()


# Replies with the `size` and `sha256` of the value and the value as blob 1.
def kv_get(line: jslb.Object) -> jslb.Object:
    store = _store_get()
    value = store.kv_get(_ref_get(line))
    blob = jslb.blob_make(value.data)
    return dispatch.reply_make(
        line, [blob], size=value.size, sha256=value.sha256.hex()
    )


# Puts blob 1 under the ref as a forwarded operation. Replies `sha256`, `seq`.
def kv_put(line: jslb.Object, *, since: int) -> jslb.Object:
    store = _store_get()
    ref = _ref_get(line)
    data = _blob_get(line)
    seq, sha256 = store.transaction_run(
        lambda: _put_apply(store, ref, data, since)
    )
    return dispatch.reply_make(line, sha256=sha256, seq=seq)


# Deletes the ref as a forwarded operation. Replies with `seq`.
def kv_delete(line: jslb.Object, *, since: int) -> jslb.Object:
    store = _store_get()
    seq = store.operation_apply("kv.delete", since, k=_ref_get(line))
    return dispatch.reply_make(line, seq=seq)


# Replies with the `keys` of a database that start with the prefix.
def kv_list(line: jslb.Object, *, db: str, prefix: str) -> jslb.Object:
    rows = _store_get().kv_list(db, prefix)
    keys = [
        {"k": row.key, "size": row.size, "sha256": row.sha256.hex()}
        for row in rows
    ]
    return dispatch.reply_make(line, keys=keys)


# Registers the handlers, with the store whose rows they read and write.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("kv.get", 0, kv_get)
    dispatch.handler_register("kv.put", 0, kv_put)
    dispatch.handler_register("kv.delete", 0, kv_delete)
    dispatch.handler_register("kv.list", 0, kv_list)
