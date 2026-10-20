# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the `turn.append` and `turn.compact` lines, over the
# substrate's turns. Both are forwarded operations that carry `since`. An
# append checks `since` against the `seq` of the scene's database itself, as
# `operation_apply` does, and stores the message as canonical JSON, because
# its reply needs the `n` the store gives the turn and `operation_apply`
# returns only the `seq`. A compaction goes through `operation_apply`.

import dispatch, jslb, json, substrate
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
        raise RuntimeError(i18n("engine_turn.not_registered"))
    return _STATE.store


# The database of a scene, an external `Document-Ref`.
def _scene_database(scene: str) -> str:
    parts = substrate.ref_split(scene)
    if parts.db is None or parts.version is None:
        raise ValueError(i18n("substrate.scene_bad", scene))
    return parts.db


# The canonical JSON text of a message: no white space, raw `UTF-8` text.
def _content_encode(content: dict[str, object]) -> str:
    return json.dumps(
        content, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


# Checks `since` against the `seq` of the scene's database, then appends.
def _turn_apply(
    store: substrate.Store, scene: str, role: str, text: str, since: int
) -> tuple[int, int]:
    db = _scene_database(scene)
    seq = store.seq_get(db)
    if since != seq:
        raise RuntimeError(
            i18n("substrate.since_stale", "turn.append", since, seq, db)
        )
    return store.turn_append(scene, role, text)


# Appends a turn to a scene as a forwarded operation. Replies `n`, `seq`.
def turn_append(
    line: jslb.Object,
    *,
    scene: str,
    role: str,
    content: dict[str, object],
    since: int,
) -> jslb.Object:
    store = _store_get()
    text = _content_encode(content)
    n, seq = store.transaction_run(
        lambda: _turn_apply(store, scene, role, text, since)
    )
    return dispatch.reply_make(line, n=n, seq=seq)


# Replaces turns 1 to `through` by a summary as a forwarded operation.
def turn_compact(
    line: jslb.Object, *, scene: str, through: int, summary: str, since: int
) -> jslb.Object:
    seq = _store_get().operation_apply(
        "turn.compact", since, scene=scene, through=through, summary=summary
    )
    return dispatch.reply_make(line, seq=seq)


# Registers the handlers, with the store whose turns they append and compact.
def handlers_register(store: substrate.Store) -> None:
    _STATE.store = store
    dispatch.handler_register("turn.append", 0, turn_append)
    dispatch.handler_register("turn.compact", 0, turn_compact)
