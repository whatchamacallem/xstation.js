# Reads an audit document for a person: one line per entry with its line number
# in the document, then a summary of what the run did: the model calls, the
# chains they started, the copies of the system prompt sent and written, the
# share of the input tokens served from cache by each reply's `usage`, and the
# bytes of the conversation's three lanes as sent and as written, both laid out
# as the document lays out a line. With --check it stops at the first
# unexpected failure and exits 1. It is for a run that is not expected to fail.
# It reads a line whole, through `audit.ShownLog`. A model call is a request
# whose url ends in `/responses` and whose body holds `input`, a model reply an
# answer whose body holds `output`, and the system prompt the content of the
# first model call's first item. `--check` also fails at a chained call whose
# input holds a system message or anything but the new items, which are the
# outputs answering the calls of the reply it chains from, in order, or else
# one user message; at a chain's first call that does not hold the prompt once,
# as its first item; when the written bodies of the three lanes hold the prompt
# more than once; and when an item of the model's output, by its id, is written
# in two bodies of those lanes.

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

# The digest: per entry its line, time from the first, gap, lane and detail.
def digest_lines(entries: list[ReadEntry]) -> list[str]: ...

# The copies of the first model call's system prompt in each model call.
def prompt_copies(entries: list[ReadEntry]) -> list[int]: ...

# The copies of that prompt in the bodies the three lanes wrote.
def prompt_recorded(entries: list[ReadEntry]) -> int: ...

# The summary of what the run did, each line one measurement of the record.
def summary_lines(entries: list[ReadEntry]) -> list[str]: ...

# The requests of the record with no reply, by start, sender, receiver and id.
def requests_open(entries: list[ReadEntry]) -> list[str]: ...

# Raises at the first unexpected failure of the record, naming its line.
def failure_check(entries: list[ReadEntry]) -> None: ...

# Prints the digest and summary, checks when asked, returns the exit code.
def main(arguments: list[str]) -> int: ...
