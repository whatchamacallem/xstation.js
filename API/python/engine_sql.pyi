import jslb

# `sql.run`: a forwarded commit of statements. Reply with `results`, `seq`.
def sql_run(
    line: jslb.Object,
    *,
    db: str,
    statements: list[dict[str, object]],
    since: int,
) -> jslb.Object: ...
