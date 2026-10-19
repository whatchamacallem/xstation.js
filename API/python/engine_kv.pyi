import jslb

# Handlers of the `kv.*` lines. The ref is the line header's `k`.

# `kv.get`: reply with `size` and `sha256`, and the value as one blob.
def kv_get(line: jslb.Object) -> jslb.Object: ...

# `kv.put`: one blob in, a forwarded operation. Reply with `sha256`, `seq`.
def kv_put(line: jslb.Object, *, since: int) -> jslb.Object: ...

# `kv.delete`: a forwarded operation. Reply with `seq`.
def kv_delete(line: jslb.Object, *, since: int) -> jslb.Object: ...

# `kv.list`: reply with `keys`, each `k`, `size`, `sha256`.
def kv_list(line: jslb.Object, *, db: str, prefix: str) -> jslb.Object: ...
