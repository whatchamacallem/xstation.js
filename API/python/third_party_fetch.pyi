# Fetches the pinned third party files with urllib, each to its path in
# `third_party/`, `<library>/<file>`, one directory per library, made when
# missing. The sha256 hex of each download is checked before the file is
# moved into place, and a file there with its pinned hex is left alone,
# with no fetch. The test driver fetches every pin before each run.

# Fetches the URL to the name's path in `third_party/`. Returns the path.
def file_fetch(url: str, sha256: str, name: str) -> str: ...

# Fetches each pinned file in pin order, to the first failure. Returns paths.
def pins_fetch() -> list[str]: ...
