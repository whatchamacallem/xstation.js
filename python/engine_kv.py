# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of `kv.put` and `kv.delete`, the browser's commits, which the
# server applies to its own store as plain messages and never answers. The
# ref is the line header's `k`, and a value travels as blob 1.

import dispatch, jslb, substrate
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


# `kv.put`: one blob in, the value, bytes or the cache path it streamed to.
def kv_put(line: jslb.Object) -> None:
    _store_get().kv_put(_ref_get(line), _blob_get(line))


# `kv.delete`: deletes the row, a missing one included.
def kv_delete(line: jslb.Object) -> None:
    _store_get().kv_delete(_ref_get(line))


# Registers the handlers on the store given.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("kv.put", 0, kv_put)
    dispatch.handler_register("kv.delete", 0, kv_delete)
