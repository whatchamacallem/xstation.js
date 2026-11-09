# The handlers of `turn.append` and `turn.prompt`, the browser's commits, which
# the server applies to its own store as plain messages and never answers. The
# server keeps every turn: it never compacts, and no compaction crosses the
# wire.

import jslb, substrate

# `turn.append`: appends the turn after the scene's last on this side.
def turn_append(
    line: jslb.Object,
    *,
    scene: str,
    role: str,
    content: list[dict[str, object]],
) -> None: ...

# `turn.prompt`: stores the conversation's system prompt before its turn 1.
def turn_prompt(
    line: jslb.Object,
    *,
    scene: str,
    messages: list[dict[str, object]],
) -> None: ...

# Registers the handlers on the store given.
def handlers_register(store: substrate.Store) -> None: ...
