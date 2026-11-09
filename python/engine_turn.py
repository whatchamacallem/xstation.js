# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of `turn.append` and `turn.prompt`, the browser's commits, which
# the server applies to its own store as plain messages and never answers. The
# server keeps every turn: it never compacts, and no compaction crosses the
# wire. A turn's items are stored as compact JSON in the order they came, and
# each message of a prompt as an array of one item. That text equals the row
# the browser's store writes while no object in the items has an integer key,
# as the browser writes integer keys first, at every level, and keeps the rest
# in the order they came.

import dispatch, jslb, json, substrate
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
        raise RuntimeError(i18n("engine_turn.not_registered"))
    return _STATE.store


# The compact JSON text of a turn's items in their order: raw `UTF-8` text.
def _content_encode(content: list[dict[str, object]]) -> str:
    return json.dumps(content, ensure_ascii=False, separators=(",", ":"))


# `turn.append`: appends the turn after the scene's last on this side.
def turn_append(
    line: jslb.Object,
    *,
    scene: str,
    role: str,
    content: list[dict[str, object]],
) -> None:
    _store_get().turn_append(scene, role, _content_encode(content))


# `turn.prompt`: stores the conversation's system prompt before its turn 1.
def turn_prompt(
    line: jslb.Object,
    *,
    scene: str,
    messages: list[dict[str, object]],
) -> None:
    rows = [(str(item["role"]), _content_encode([item])) for item in messages]
    _store_get().turn_prompt(scene, rows)


# Registers the handlers on the store given.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("turn.append", 0, turn_append)
    dispatch.handler_register("turn.prompt", 0, turn_prompt)
