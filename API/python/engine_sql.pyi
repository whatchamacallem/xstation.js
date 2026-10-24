# The handler of `sql.run`, the browser's commit of statements that changed
# its database, which the server runs on its own store in one transaction as
# a plain message and never answers.

import jslb, substrate

# `sql.run`: runs the statements in order in one transaction.
def sql_run(
    line: jslb.Object,
    *,
    db: str,
    statements: list[dict[str, object]],
) -> None: ...

# Registers the handler on the store given.
def handlers_register(store: substrate.Store) -> None: ...
