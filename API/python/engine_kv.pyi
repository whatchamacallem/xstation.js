# The handlers of `kv.put` and `kv.delete`, the browser's commits, which the
# server applies to its own store as plain messages and never answers. The
# ref is the line header's `k`.

import jslb, substrate

# `kv.put`: one blob in, the value, bytes or the cache path it streamed to.
def kv_put(line: jslb.Object) -> None: ...

# `kv.delete`: deletes the row, a missing one included.
def kv_delete(line: jslb.Object) -> None: ...

# Registers the handlers on the store given.
def handlers_register(store: substrate.Store) -> None: ...
