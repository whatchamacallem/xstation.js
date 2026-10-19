# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the `turn.append` and `turn.compact` lines, over the
# substrate's turns. Both are forwarded operations that carry `since` and go
# through `operation_apply`.

import dispatch, jslb, substrate
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
        raise RuntimeError(i18n("engine_turn.not_registered"))
    return _STATE.store


# Applies the append, then reads the `n` that the new turn was given.
def _turn_apply(
    store: substrate.Store,
    scene: str,
    role: str,
    content: dict[str, object],
    since: int,
) -> tuple[int, int]:
    seq = store.operation_apply(
        "turn.append", since, scene=scene, role=role, content=content
    )
    return store.turn_list(scene)[-1].n, seq


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
    n, seq = store.transaction_run(
        lambda: _turn_apply(store, scene, role, content, since)
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
