# Reads an audit document for a person or an AI debugging the code: the audit
# digest, every entry told as the run's conversation with its tools, SQL and
# lines between threads, a text shown before named by its line, then a
# summary: the model calls, the chains they started, the copies of the system
# prompt sent, the share of the input tokens served from cache by each reply's
# `usage`, the tools called and the commits. With --check it stops at the
# first unexpected failure and exits 1, for a run not expected to fail. It
# reads a line whole, through `audit.ShownLog`. A model call is a request whose
# url ends in `/responses` and whose body holds `input`, a model reply an
# answer whose body holds `output`, and the system prompt the content of the
# first model call's first item. `--check` also fails at a chained call that
# sends other than the new items, a chain's first call not holding the prompt
# once as its first item, the lanes writing the prompt twice and an output
# item written twice. `--guide NAME` adds the guide check, that every message
# is the one the walk of python/guides/NAME expects. databases_check replays
# the record's commits on a copy of a root's databases and compares them with
# the server's, and database_lines tells databases as text, by the rules of
# declawed.md's audit_read.
#
#     python3 python/audit_read.py PATH [--check] [--guide NAME]

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

# The copies of the first model call's system prompt the three lanes wrote.
def prompt_recorded(entries: list[ReadEntry]) -> int: ...

# The audit digest: every entry told, a text shown before named, a summary.
def digest_lines(entries: list[ReadEntry]) -> list[str]: ...

# The requests of the record with no reply, by start, sender, receiver and id.
def requests_open(entries: list[ReadEntry]) -> list[str]: ...

# Raises at the first unexpected failure of the record, naming its line.
def failure_check(entries: list[ReadEntry]) -> None: ...

# Raises at the first message a guide's walk does not expect, naming its line.
def guide_check(
    entries: list[ReadEntry], table: dict[str, Any], gold: dict[str, Any]
) -> None: ...

# Raises where `end` differs from `start` with the record's commits replayed.
def databases_check(
    entries: list[ReadEntry], start: str, end: str, scratch: str
) -> None: ...

# The databases of a directory as text, each object's SQL and rows.
def database_lines(root: str) -> list[str]: ...

# Prints the digest and, when asked, checks and prints the verdict.
def main(arguments: list[str]) -> int: ...
