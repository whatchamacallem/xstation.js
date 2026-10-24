# The handler of `turn.append`, the browser's commit, which the server
# applies to its own store as a plain message and never answers. The server
# keeps every turn: it never compacts, and no compaction crosses the wire.

import jslb, substrate

# `turn.append`: appends the turn after the scene's last on this side.
def turn_append(
    line: jslb.Object,
    *,
    scene: str,
    role: str,
    content: dict[str, object],
) -> None: ...

# Registers the handler on the store given.
def handlers_register(store: substrate.Store) -> None: ...
