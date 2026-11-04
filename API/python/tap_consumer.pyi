# The TAP consumer, tappy's names: a parser of TAP version 14 lines and a
# reader that checks a stream against the producers' grammar, one TAP
# stream of one parent plan and one indented block per test module. It reads
# a whole document, or a stream line by line as it arrives, as the wire test
# reads the TypeScript stream the server writes, stopping at its first
# failure. A `Bail out!` line at depth 0 ends a stream wherever it stands: it
# is well formed, and it counts as one failure unless it follows a failed
# point, as the producer's own bail out does. Reading stops there: every line
# after it is ignored, as TAP 14 asks a harness to stop at a bail out. The
# server writes one when the browser fails, which can be before the version
# line. Each line kind is a class named as tappy's category of it, and a
# line inside a stream carries its depth: 0 for the stream, 1 for a block
# indented four spaces. Every point, a block's or a parent's, is followed at
# once by its YAML block, indented two spaces more than the point, of the
# three lines `---`, `duration_ms: N` with N the milliseconds `[0-9]+.[0-9]`,
# and `...`, then by its diagnostic lines. The parser gives those three
# lines alone as YAML, any other text at that indent being unknown, and the
# reader takes them in order after each point: a hardcoded grammar, no YAML
# parser, so that any other attribute is refused.

from collections.abc import Iterator
from typing import NamedTuple, TypeAlias

# A test point, tappy's "test": its depth, number, description, directive.
class Result(NamedTuple):
    depth: int
    ok: bool
    number: int
    description: str
    directive: str
    # Whether the directive skips the test.
    @property
    def skip(self) -> bool: ...
    # Whether the directive marks the test as still to do.
    @property
    def todo(self) -> bool: ...

# A plan line, tappy's "plan": its depth and the number of points it plans.
class Plan(NamedTuple):
    depth: int
    expected_tests: int

# A diagnostic line, tappy's "diagnostic": its depth and its text.
class Diagnostic(NamedTuple):
    depth: int
    text: str

# A bail out line, tappy's "bail": its depth and its reason, empty for none.
class Bail(NamedTuple):
    depth: int
    reason: str

# The version line, tappy's "version": the version it names.
class Version(NamedTuple):
    version: int

# A line of a point's YAML block: its point's depth, its text after the indent.
class YamlLine(NamedTuple):
    depth: int
    text: str

# Any other line, tappy's "unknown": its text.
class Unknown(NamedTuple):
    text: str

# Any line kind the parser returns.
Line: TypeAlias = (
    Result | Plan | Diagnostic | Bail | Version | YamlLine | Unknown
)

# tappy's `Parser`, its names recalled from tappy's documentation.
class Parser:
    # Yields the kind of each line of the text, in order.
    def parse_text(self, text: str) -> Iterator[Line]: ...
    # Returns the kind of one line.
    def parse_line(self, text: str) -> Line: ...

# Checks a stream line by line and counts its points.
class StreamReader:
    plan: int
    passed: int
    failed: int
    skipped: int
    # Takes the next line. Returns whether it fits where it stands.
    def line_read(self, line: Line) -> bool: ...
    # Whether the stream ended, by its parent plan or a bail out line.
    def stream_ended(self) -> bool: ...

# What a document held: its plan, the counts, and whether it was well formed.
class TapStats(NamedTuple):
    plan: int
    passed: int
    failed: int
    skipped: int
    well_formed: bool

# Takes a whole document and returns its stats. Its last line needs a newline.
def document_stats(text: str) -> TapStats: ...
