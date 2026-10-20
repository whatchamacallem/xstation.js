from collections.abc import Iterator
from typing import NamedTuple

# A line as tappy's parser returns it; `category` names its kind.
class Line:
    @property
    def category(self) -> str: ...

# A test point, category "test".
class Result(Line):
    @property
    def ok(self) -> bool: ...
    @property
    def number(self) -> int | None: ...
    @property
    def description(self) -> str: ...
    @property
    def skip(self) -> bool: ...
    @property
    def todo(self) -> bool: ...

# A plan line, category "plan".
class Plan(Line):
    @property
    def expected_tests(self) -> int: ...
    @property
    def skip(self) -> bool: ...

# A diagnostic line, category "diagnostic".
class Diagnostic(Line):
    @property
    def text(self) -> str: ...

# A bail out line, category "bail".
class Bail(Line):
    @property
    def reason(self) -> str: ...

# The version line, category "version".
class Version(Line):
    @property
    def version(self) -> int: ...

# Any other line, category "unknown".
class Unknown(Line): ...

# tappy's `Parser`, its names recalled from tappy's documentation.
class Parser:
    # Yields the kind of each line of the text, in order.
    def parse_text(self, text: str) -> Iterator[Line]: ...
    # Returns the kind of one line.
    def parse_line(self, text: str) -> Line: ...

# What a stream held: its plan, the counts, and whether it was well formed.
class TapStats(NamedTuple):
    plan: int
    ok: int
    not_ok: int
    skip: int
    well_formed: bool

# Takes a whole TAP document and returns its stats. Subtest blocks count.
def document_stats(text: str) -> TapStats: ...
