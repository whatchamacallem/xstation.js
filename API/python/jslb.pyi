from collections.abc import Callable, Iterator
from typing import Any

# A decoded JSON object: a dict whose keys are attributes too, at every
# level, so `line.scene.title` and `fn(line, **payload_of(line))` work.
class Object(dict[str, Any]):
    def __getattr__(self, name: str) -> Any: ...

# A framing or header fault. The port that fed the decoder closes on it.
class WireError(Exception): ...

# Builds the line header `"0"`. `full` selects full names, the debug form.
# A field at its default is left out.
def header_make(
    type: str,
    *,
    version: int = 0,
    id: int | None = None,
    reply: int | None = None,
    key: str | None = None,
    full: bool = False,
) -> Object: ...

# Builds a blob header with `d` set and `s` measured. `data` is the bytes,
# or the path of a file holding them. Other fields are the handler's.
def blob_make(
    data: bytes | str, key: str | None = None, **fields: object
) -> Object: ...

# Builds a line from its header, blob headers and payload, numbering the
# blob headers `"1"` on and setting `b`.
def line_make(header: Object, blobs: list[Object], **payload: Any) -> Object: ...

# Resolves a short or full field name on a header and its default.
def field_get(header: Object, name: str) -> Any: ...

# The blob headers of a line, in order.
def blobs_of(line: Object) -> list[Object]: ...

# The payload: the keys of the line that aren't decimal integer strings.
def payload_of(line: Object) -> dict[str, Any]: ...

# Yields the JSON bytes ending in CR, then each blob's `d` as it is, bytes
# or a file path, for the writer to send in order. Copies no blob bytes.
def line_encode(line: Object) -> Iterator[bytes | str]: ...

class LineDecoder:
    # `sink_make(header)` returns the path a blob over `overflow_bytes`
    # streams to as it arrives; its `d` is then that path.
    def __init__(
        self,
        line_max: int,
        blob_max: int,
        overflow_bytes: int,
        sink_make: Callable[[Object], str],
    ) -> None: ...
    # Returns the complete lines the bytes finish, zero or more. Raises
    # WireError at the first fault; the decoder is then unusable.
    def feed(self, data: bytes) -> list[Object]: ...
