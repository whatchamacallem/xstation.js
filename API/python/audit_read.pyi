# Reads an audit document for a person: a listing of one line per entry with
# its line number in the document, then a summary of what the run did: the
# model calls, the chains they started, the copies of the system prompt sent
# and written, the share of the input tokens served from cache by each reply's
# `usage`, and the bytes of the conversation's three lanes as sent and as
# written. With --check it stops at the first unexpected failure and exits 1,
# for a run not expected to fail. It reads a line whole, through
# `audit.ShownLog`. A model call is a request whose url ends in `/responses`
# and whose body holds `input`, a model reply an answer whose body holds
# `output`, and the system prompt the content of the first model call's first
# item. `--check` also fails at a chained call that sends other than the new
# items, a chain's first call not holding the prompt once as its first item,
# the lanes writing the prompt twice and an output item written twice.
# `--guide NAME` adds the guide check, that every message is the one the walk
# of python/guides/NAME expects, and `--digest FILE` writes the audit digest,
# the run told as the player's and the model's conversation with its tools,
# SQL and lines between threads, by the rules of declawed.md's audit_read.
#
#     python3 python/audit_read.py PATH [--check] [--guide NAME]
#         [--digest FILE]

from typing import Any, NamedTuple

# One entry: its place, start, time, label, body, whole line, items kept.
class ReadEntry(NamedTuple):
    number: int
    start: int
    at: int
    label: str
    body: str
    line: dict[str, Any] | None
    kept: int

# A failure the check found, naming the line of the document that shows it.
class AuditFailed(Exception): ...

# The type of a line entry, or an empty string for a note or a dump.
def type_of(entry: ReadEntry) -> str: ...

# The entries of a document's text in order, a line of no form refused.
def entries_parse(text: str) -> list[ReadEntry]: ...

# The document's text, read whole under a shared lock of the file.
def document_read(path: str) -> str: ...

# The input items of a model call as sent, none for any other line.
def input_of(entry: ReadEntry) -> list[dict[str, Any]]: ...

# The listing: per entry its line, time from the first, gap, lane and detail.
def listing_lines(entries: list[ReadEntry]) -> list[str]: ...

# The copies of the first model call's system prompt in each model call.
def prompt_copies(entries: list[ReadEntry]) -> list[int]: ...

# The copies of that prompt in the bodies the three lanes wrote.
def prompt_recorded(entries: list[ReadEntry]) -> int: ...

# The summary of what the run did, each line one measurement of the record.
def summary_lines(entries: list[ReadEntry]) -> list[str]: ...

# The audit digest: shown entries told whole, hidden ones counted, a summary.
def digest_lines(entries: list[ReadEntry]) -> list[str]: ...

# The requests of the record with no reply, by start, sender, receiver and id.
def requests_open(entries: list[ReadEntry]) -> list[str]: ...

# Raises at the first unexpected failure of the record, naming its line.
def failure_check(entries: list[ReadEntry]) -> None: ...

# Raises at the first message a guide's walk does not expect, naming its line.
def guide_check(
    entries: list[ReadEntry], table: dict[str, Any], gold: dict[str, Any]
) -> None: ...

# Prints the listing and summary, checks and writes the digest when asked.
def main(arguments: list[str]) -> int: ...
