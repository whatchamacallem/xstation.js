# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handler of `turn.append`, the browser's commit, which the server
# applies to its own store as a plain message and never answers. The server
# keeps every turn: it never compacts, and no compaction crosses the wire.
# The message is stored as canonical JSON.

import dispatch, jslb, json, substrate
from internationalization import i18n


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
        raise RuntimeError(i18n("engine_turn.not_registered"))
    return _STATE.store


# The canonical JSON text of a message: no white space, raw `UTF-8` text.
def _content_encode(content: dict[str, object]) -> str:
    return json.dumps(content, ensure_ascii=False, separators=(",", ":"))


# `turn.append`: appends the turn after the scene's last on this side.
def turn_append(
    line: jslb.Object,
    *,
    scene: str,
    role: str,
    content: dict[str, object],
) -> None:
    _store_get().turn_append(scene, role, _content_encode(content))


# Registers the handler on the store given.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("turn.append", 0, turn_append)
