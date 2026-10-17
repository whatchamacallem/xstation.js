from typing import Any

from jslb import Object

# Handlers of the `doc.*` lines on the wire. A ref is
# `<db>/<kind>/<name>/<version>`; a path is the same without the version.

# `doc.get`: reply with `body`, the document as JSON.
def doc_get(line: Object, *, ref: str) -> Object: ...

# `doc.put`: reply with `ref` of the new version and `seq`.
def doc_put(line: Object, *, path: str, body: Any) -> Object: ...

# `doc.head`: reply with `ref`.
def doc_head(line: Object, *, path: str) -> Object: ...
