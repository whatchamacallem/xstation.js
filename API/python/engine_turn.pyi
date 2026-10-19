import jslb

# `turn.append`: a forwarded operation. Reply with `n` and `seq`.
def turn_append(
    line: jslb.Object,
    *,
    scene: str,
    role: str,
    content: dict[str, object],
    since: int,
) -> jslb.Object: ...

# `turn.compact`: a forwarded operation. Reply with `seq`.
def turn_compact(
    line: jslb.Object, *, scene: str, through: int, summary: str, since: int
) -> jslb.Object: ...
