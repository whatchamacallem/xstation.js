from jslb import Object

# Handlers of the `kv.*` lines on the wire. The key is the line header's
# `k`; `db` is the payload. See API/ts/lines.d.ts for the shapes.

# `kv.get`: reply with `size` and `sha256`, and the value as one blob.
def kv_get(line: Object, *, db: str) -> Object: ...

# `kv.put`: one blob in; reply with `sha256` and `seq`.
def kv_put(line: Object, *, db: str) -> Object: ...

# `kv.delete`: reply with `seq`.
def kv_delete(line: Object, *, db: str) -> Object: ...

# `kv.list`: reply with `keys`, each `k`, `size`, `sha256`, `seq`.
def kv_list(line: Object, *, db: str, prefix: str) -> Object: ...
