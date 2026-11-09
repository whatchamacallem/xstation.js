# Reads an audit document for a person: one line per entry with its line number
# in the document, then a summary of what the run did. With --check it stops at
# the first unexpected failure and exits 1. It is for a run that is not expected
# to fail. Standard library only.

from typing import Any, NamedTuple

# One entry: where its heading is, its start, time, label, body and line.
class ReadEntry(NamedTuple):
    number: int
    start: int
    at: int
    label: str
    body: str
    line: dict[str, Any] | None

# A failure the check found, naming the line of the document that shows it.
class AuditFailed(Exception): ...

# The type of a line entry, or an empty string for a note or a dump.
def type_of(entry: ReadEntry) -> str: ...

# The entries of a document's text in order, a line of no form refused.
def entries_parse(text: str) -> list[ReadEntry]: ...

# The document's text, read whole under a shared lock of the file.
def document_read(path: str) -> str: ...

# The messages of a chat request, none for any other line.
def messages_of(entry: ReadEntry) -> list[dict[str, Any]]: ...

# The digest: per entry its line, time from the first, gap, lane and detail.
def digest_lines(entries: list[ReadEntry]) -> list[str]: ...

# The copies of the first request's system prompt in each chat request.
def prompt_copies(entries: list[ReadEntry]) -> list[int]: ...

# The summary of what the run did, each line one measurement of the record.
def summary_lines(entries: list[ReadEntry]) -> list[str]: ...

# The requests of the record with no reply, by start, sender, receiver and id.
def requests_open(entries: list[ReadEntry]) -> list[str]: ...

# Raises at the first unexpected failure of the record, naming its line.
def failure_check(entries: list[ReadEntry]) -> None: ...

# Prints the digest and summary, checks when asked, returns the exit code.
def main(arguments: list[str]) -> int: ...
