# The handler of `doc.put`, the browser's commit, which the server applies
# to its own store as a plain message and never answers: the server writes
# its own next version, whatever version the browser's was.

from typing import Any

import jslb, substrate

# `doc.put`: writes the next version of the document and moves its head.
def doc_put(
    line: jslb.Object, *, db: str, id: str, body: dict[int | str, Any]
) -> None: ...

# Registers the handler on the store given.
def handlers_register(store: substrate.Store) -> None: ...
