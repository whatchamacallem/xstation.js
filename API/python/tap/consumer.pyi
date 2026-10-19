from typing import NamedTuple

# What a stream held: its plan, the counts, and whether it was well formed.
class TapStats(NamedTuple):
    plan: int
    ok: int
    not_ok: int
    skip: int
    well_formed: bool

# Takes a whole TAP document and returns its stats. Subtest blocks count.
def document_stats(text: str) -> TapStats: ...
