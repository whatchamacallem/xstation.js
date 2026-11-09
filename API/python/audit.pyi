# The audit document of a root, `_audit.txt`, debug mode only: every JSLB line
# of the demo, each exchange once, in the order the server learned of it, laid
# out for a person. The engine role and the console role open it for
# appending, each writing its start heading, `engine` or `console`, with the
# date, the time and the process id; each entry is one write under an
# exclusive lock of the file, its size checked first, so two processes never
# interleave, and an entry that would carry the file past `blob_max` raises
# `audit.full`, having written nothing. A heading starts at the left margin
# with `====` or `----`, and no line of a body does. A line's body is its JSON
# text laid out by `json.dumps` with an indent of 2, then `[blobs omitted: N]`
# when its header counts blobs; the audit's own lines, every type under
# `audit.`, are never recorded. A wire line the server reads is `ai to server`
# and one it writes `server to ai`, written before the line. An entry read
# back holds the start it follows from 1, its time as printed, its label, as
# `ui to ai`, `note of ai` or `databases of the browser`, and its body. A
# tail's entries are measured as the JSON string of the reply that carries
# them, and one that does not fit ends the tail, older ones too. What a model
# request, its reply or a commit repeats of what the document shows is written
# as a count: `line_thin` leaves it out, `line_whole` puts it back.

import jslb
from typing import Any, NamedTuple

# One entry read back: its start, its time, its label, its body.
class AuditEntry(NamedTuple):
    start: int
    time: str
    label: str
    body: str

# What the document shows: each conversation's items, the tools, the output.
class ShownLog:
    # The items by the conversation's ref, `prompt_cache_key` or `scene`.
    items: dict[str, list[Any]]
    # The conversation last shown, whose items a new one is compared with.
    last: str
    tools: list[Any]
    # The output of the last model reply.
    output: list[Any]
    def __init__(self) -> None: ...
    def line_thin(
        self, label: str, kind: str, line: dict[Any, Any]
    ) -> dict[Any, Any]: ...
    def line_whole(
        self, label: str, kind: str, line: dict[Any, Any]
    ) -> dict[Any, Any]: ...

# Opens the root's document for appending, held to `blob_max`, start heading.
def audit_open(root: str, blob_max: int, role: str) -> None: ...

# Closes the document and returns the module to its state before the open.
def audit_close() -> None: ...

# A line entry of a wire line the server read, but the audit's own lines.
def line_received(line: jslb.Object) -> None: ...

# A line entry of a wire line the server writes, written before the line.
def line_sent(line: jslb.Object) -> None: ...

# A line entry of a page thread's record of the line's JSON text.
def record_put(sender: str, receiver: str, at: int, text: str) -> None: ...

# A note of a thread: its time and text.
def note_put(thread: str, at: int, text: str) -> None: ...

# A dump entry of one side's views, in name order, under its title.
def dump_put(title: str, views: list[dict[str, Any]]) -> None: ...

# The laid out text of a record, as the document holds it, for a block log.
def record_text(sender: str, receiver: str, at: int, text: str) -> str: ...

# The laid out text of a note, as the document holds it, for a block log.
def note_text(thread: str, at: int, text: str) -> str: ...

# The newest whole entries, at most `count`, that fit below `limit` bytes.
def tail_read(count: int, limit: int) -> str: ...

# The entries of a root's document in order, the demo test's check.
def entries_read(root: str) -> list[AuditEntry]: ...
