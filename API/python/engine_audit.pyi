# The handlers of the audit, registered in debug mode alone. A record's blob,
# the JSON text of the line it records, is read whole from memory or from the
# file the main loop's sink finished, which then goes. An `audit.tail` reply
# holds the newest whole entries of the document that fit one reply below
# `line_max`, oldest first, so its `count` is a maximum. An `audit.dump` writes
# the browser's views from its blob 1 as `databases of the browser`, then the
# views of every database of the server's store in name order as `databases
# of the server`, each by `audit.dump_put`.

import jslb, substrate

# `audit.line`: a page thread's record into the document.
def audit_line(
    line: jslb.Object, *, sender: str, receiver: str, at: int
) -> None: ...

# `audit.note`: a page thread's note into the document.
def audit_note(
    line: jslb.Object, *, thread: str, at: int, text: str
) -> None: ...

# `audit.tail`: the document's newest entries that fit one reply.
def audit_tail(line: jslb.Object, *, count: int) -> jslb.Object: ...

# `audit.dump`: the browser's views from blob 1, then the server's own.
def audit_dump(line: jslb.Object) -> None: ...

# Registers the four when `debug` is true, `line_max` bounding the tail.
def handlers_register(
    debug: bool, line_max: int, store: substrate.Store
) -> None: ...
