from collections.abc import Callable, Iterator
from typing import Any

# A decoded JSON object, headers at integer keys, string keys attributes too.
class Object(dict[int | str, Any]):
    def __getattr__(self, name: str) -> Any: ...

# A framing or header fault. The port that fed the decoder closes on it.
class WireError(Exception): ...

# Builds the header `0`. `full` selects full names. Defaults are left out.
def header_make(
    type: str,
    *,
    version: int = 0,
    id: int | None = None,
    reply: int | None = None,
    key: str | None = None,
    full: bool = False,
) -> Object: ...

# Builds a blob header with `d` set and `s` measured: bytes or a file path.
def blob_make(
    data: bytes | str, key: str | None = None, **fields: object
) -> Object: ...

# Builds a line from its header, blob headers and payload, numbering them.
def line_make(
    header: Object, blobs: list[Object], **payload: Any
) -> Object: ...

# Resolves a short or full field name on a header, and its default.
def field_get(header: Object, name: str) -> Any: ...

# The headers of an object, `0` on, found by probing the integer keys.
def headers_of(line: Object) -> list[Object | str]: ...

# The payload: the keys of the object that aren't integers.
def payload_of(line: Object) -> dict[str, Any]: ...

# Yields the JSON bytes ending in CR, then each blob's `d` as it is.
def line_encode(line: Object) -> Iterator[bytes | str]: ...

# The JSON text of a line followed by one `<blob "n"=K>` tag per blob.
def line_render(line: Object) -> str: ...

# WireError: a line over `line_max`, or blobs over `blob_max` in all.
class LineDecoder:
    # `sink_make(header)` returns the path a blob over `overflow_bytes` takes.
    def __init__(
        self,
        line_max: int,
        blob_max: int,
        overflow_bytes: int,
        sink_make: Callable[[Object], str],
    ) -> None: ...
    # Returns the complete lines the bytes finish. Raises WireError on a fault.
    def bytes_feed(self, data: bytes) -> list[Object]: ...
