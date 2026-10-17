from typing import NamedTuple

# One pinned file: its URL, its SHA-256 as hex, where it lands.
class Pinned(NamedTuple):
    url: str
    sha256: str
    path: str

# Fetches with urllib what `third_party/SOURCES.json` pins and is missing,
# verifies every file's hash, and raises on a mismatch. Never updates.
def fetch_all(sources: str) -> list[Pinned]: ...
