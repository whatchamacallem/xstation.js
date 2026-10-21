# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# JSLB, the wire format: a line is one JSON object ending in CR, its headers
# at the integer keys 0, 1, ... and its payload at the other keys, followed by
# the bytes of each blob the line header counts. The builders, field access,
# the encoder, the debug rendering, and the decoder, which streams a blob over
# overflow_bytes into the file its sink names, hashing it on the way.

import hashlib, io, json, math, os, re
from collections.abc import Callable, Iterable, Iterator
from typing import Any, NoReturn, cast
from i18n import i18n

# The short line header field names and their full forms.
_LINE_NAMES = {
    "t": "type",
    "v": "version",
    "i": "id",
    "r": "reply",
    "k": "key",
    "b": "blobs",
}

# The full line header field names.
_LINE_FULL = frozenset(_LINE_NAMES.values())

# The short blob header field names the wire carries and their full forms.
_BLOB_NAMES = {"s": "size", "k": "key"}

# The full blob header field names the wire carries and their short forms.
_BLOB_SHORT = {full: short for short, full in _BLOB_NAMES.items()}

# The blob header names `blob_make` sets itself, which no field may take.
_BLOB_RESERVED = frozenset(("s", "k", "d", "size"))

# Every short field name `field_get` resolves and its full form.
_FIELD_NAMES = {**_LINE_NAMES, **_BLOB_NAMES, "d": "data"}

# The short form of every name `field_get` resolves.
_FIELD_SHORT = {
    **{short: short for short in _FIELD_NAMES},
    **{full: short for short, full in _FIELD_NAMES.items()},
}

# The defaults of the fields that have one, by short name.
_FIELD_DEFAULTS = {"v": 0, "b": 0}

# The fields a header of their kind must hold, by short name.
_FIELD_REQUIRED = frozenset(("t", "s"))

# The largest magnitude of an `int` the encoder writes and the decoder reads.
_INTEGER_LIMIT = 2**53

# A key of the decimal digits of a non negative integer, no leading zero.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# A key of decimal digits, which a payload key must not be.
_DIGIT_KEY = re.compile(r"[0-9]+")


# A decoded JSON object, headers at integer keys, string keys attributes too.
class Object(dict[int | str, Any]):
    # Reads a string key. A key named like a dict method, `keys`, needs `[]`.
    def __getattr__(self, name: str) -> Any:
        if name not in self:
            raise AttributeError(i18n("jslb.attribute_missing", name))
        return self[name]


# A framing or header fault. The port that fed the decoder closes on it.
class WireError(Exception):
    pass


# Builds the header `0`. `full` selects full names. Defaults are left out.
def header_make(
    type: str,
    *,
    version: int = 0,
    id: int | None = None,
    reply: int | None = None,
    key: str | None = None,
    full: bool = False,
) -> Object:
    fields: list[tuple[str, object]] = [("t", type)]
    if version != 0:
        fields.append(("v", version))
    if id is not None:
        fields.append(("i", id))
    if reply is not None:
        fields.append(("r", reply))
    if key is not None:
        fields.append(("k", key))
    header = Object()
    for name, value in fields:
        header[_LINE_NAMES[name] if full else name] = value
    return header


# Builds a blob header with `d` set and `s` measured: bytes or a file path.
def blob_make(
    data: bytes | str, key: str | None = None, **fields: object
) -> Object:
    size = len(data) if isinstance(data, bytes) else os.path.getsize(data)
    header = Object()
    header["s"] = size
    if key is not None:
        header["k"] = key
    for name, value in fields.items():
        if name in _BLOB_RESERVED:
            raise ValueError(i18n("jslb.blob_field_reserved", name))
        header[name] = value
    header["d"] = data
    return header


# Builds a line from its header, blob headers and payload, numbering them.
def line_make(header: Object, blobs: list[Object], **payload: Any) -> Object:
    full = "type" in header
    if "b" in header or "blobs" in header:
        raise ValueError(i18n("jslb.blobs_preset"))
    first = Object(header)
    if blobs:
        first["blobs" if full else "b"] = len(blobs)
    line = Object()
    line[0] = first
    for number, blob in enumerate(blobs, 1):
        line[number] = _blob_named(blob, full)
    for name, value in payload.items():
        line[name] = value
    return line


# Resolves a short or full field name on a header, and its default.
def field_get(header: Object, name: str) -> Any:
    if name not in _FIELD_SHORT:
        raise ValueError(i18n("jslb.field_unknown", name))
    short = _FIELD_SHORT[name]
    full = _FIELD_NAMES[short]
    if short in header and full in header:
        raise WireError(i18n("jslb.both_name_forms"))
    if short in header:
        return header[short]
    if full in header:
        return header[full]
    if short in _FIELD_REQUIRED:
        raise KeyError(i18n("jslb.field_missing", name))
    return _FIELD_DEFAULTS.get(short)


# The headers of an object, `0` on, found by probing the integer keys.
def headers_of(line: Object) -> list[Object | str]:
    headers: list[Object | str] = []
    while len(headers) in line:
        headers.append(line[len(headers)])
    return headers


# The payload: the keys of the object that aren't integers.
def payload_of(line: Object) -> dict[str, Any]:
    return {key: value for key, value in line.items() if isinstance(key, str)}


# Returns the JSON bytes ending in CR, then each blob's `d` as it is.
def line_encode(line: Object) -> Iterator[bytes | str]:
    sizes = _line_check(line, False)
    text = _line_text(line, len(sizes)) + "\r"
    pieces: list[bytes | str] = [text.encode("utf-8")]
    for number, size in enumerate(sizes, 1):
        data: object = line[number].get("d")
        if isinstance(data, bytes):
            length = len(data)
        elif isinstance(data, str):
            length = os.path.getsize(data)
        else:
            raise ValueError(i18n("jslb.blob_data_missing", number))
        if length != size:
            raise ValueError(
                i18n("jslb.blob_size_differs", number, size, length)
            )
        pieces.append(data)
    return iter(pieces)


# The JSON text of a line followed by one `<blob "n"=K>` tag per blob.
def line_render(line: Object) -> str:
    count = len(_line_check(line, False))
    tags = "".join(f'<blob "n"={number}>' for number in range(1, count + 1))
    return _line_text(line, count) + tags


# Copies a blob header with its size and key named in the line's form.
def _blob_named(blob: Object, full: bool) -> Object:
    renames = _BLOB_NAMES if full else _BLOB_SHORT
    named = Object()
    for name, value in blob.items():
        if isinstance(name, str):
            named[renames.get(name, name)] = value
        else:
            named[name] = value
    return named


# Returns the header at the key, which must be a JSON object.
def _header_at(
    line: dict[int | str, Any], number: int
) -> dict[int | str, Any]:
    header: object = line[number]
    if not isinstance(header, dict):
        raise WireError(i18n("jslb.header_not_object", number))
    return cast(dict[int | str, Any], header)


# Returns whether a header uses full names, `None` when it uses neither.
def _form_get(
    header: dict[int | str, Any], names: dict[str, str]
) -> bool | None:
    short = any(name in header for name in names)
    full = any(name in header for name in names.values())
    if short and full:
        raise WireError(i18n("jslb.both_name_forms"))
    if short or full:
        return full
    return None


# Checks a line's headers and payload keys and returns each blob's size.
def _line_check(line: dict[int | str, Any], wire: bool) -> list[int]:
    if 0 not in line:
        raise WireError(i18n("jslb.no_header_zero"))
    header = _header_at(line, 0)
    for name in header:
        if name not in _LINE_NAMES and name not in _LINE_FULL:
            raise WireError(i18n("jslb.unknown_line_field", name))
    full = _form_get(header, _LINE_NAMES)
    if not isinstance(header.get("type" if full else "t"), str):
        raise WireError(i18n("jslb.no_type"))
    probed = 0
    while probed + 1 in line:
        probed += 1
    for key in line:
        if type(key) is int and key > probed:
            raise WireError(i18n("jslb.blob_gap", probed + 1, key))
    count = _integer_read(header, "blobs" if full else "b", wire, 0)
    if type(count) is not int or count != probed:
        raise WireError(i18n("jslb.blobs_mismatch", count, probed))
    sizes: list[int] = []
    for number in range(1, probed + 1):
        blob = _header_at(line, number)
        if "data" in blob or (wire and "d" in blob):
            raise WireError(i18n("jslb.blob_data_field", number))
        if _form_get(blob, _BLOB_NAMES) not in (None, full):
            raise WireError(i18n("jslb.both_name_forms"))
        size = _integer_read(blob, "size" if full else "s", wire, None)
        if type(size) is not int or size < 0:
            raise WireError(i18n("jslb.bad_size", number))
        sizes.append(size)
    for key in line:
        if isinstance(key, str) and _DIGIT_KEY.fullmatch(key):
            raise WireError(i18n("jslb.payload_digit_key", key))
    return sizes


# Returns a header field or `absent`, an integral float on the wire made `int`.
def _integer_read(
    header: dict[int | str, Any], name: str, wire: bool, absent: object
) -> Any:
    value: object = header.get(name, absent)
    if wire and type(value) is float and value.is_integer():
        value = int(value)
        header[name] = value
    return value


# Returns the JSON text the encoder writes for a line with `count` blobs.
def _line_text(line: dict[int | str, Any], count: int) -> str:
    sent = dict(line)
    for number in range(1, count + 1):
        header = _header_at(line, number)
        sent[number] = {
            name: value for name, value in header.items() if name != "d"
        }
    return json.dumps(
        _json_ready(sent),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    )


# Returns a value for `json.dumps`, integer keys first, numbers checked.
def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        source = cast(dict[object, object], value)
        numbers: list[int] = []
        names: list[str] = []
        for key in source:
            if type(key) is int and key >= 0:
                numbers.append(key)
            elif type(key) is str and not _NUMBER_KEY.fullmatch(key):
                names.append(key)
            else:
                raise ValueError(i18n("jslb.key_refused", repr(key)))
        ready: dict[int | str, object] = {}
        for key in [*sorted(numbers), *names]:
            ready[key] = _json_ready(source[key])
        return ready
    if isinstance(value, (list, tuple)):
        items = cast(Iterable[object], value)
        return [_json_ready(item) for item in items]
    if type(value) is int and abs(value) > _INTEGER_LIMIT:
        raise ValueError(i18n("jslb.integer_refused", value))
    if type(value) is float and not math.isfinite(value):
        raise ValueError(i18n("jslb.number_refused", value))
    return value


# Builds an `Object` from parsed pairs, decimal digit keys made integers.
def _object_make(pairs: list[tuple[str, Any]]) -> Object:
    made = Object()
    for key, value in pairs:
        made[int(key) if _NUMBER_KEY.fullmatch(key) else key] = value
    return made


# Refuses the `NaN` and `Infinity` constants, which are not JSON.
def _constant_refuse(name: str) -> NoReturn:
    raise WireError(i18n("jslb.line_not_json", name))


# Reads a JSON integer as an `int` within `2**53` either way, else a double.
def _integer_parse(text: str) -> int | float:
    number = int(text)
    if abs(number) > _INTEGER_LIMIT:
        return float(text)
    return number


# Parses line bytes as strict `UTF-8` JSON into an `Object`.
def _line_decode(text: bytes) -> Object:
    try:
        string = text.decode("utf-8")
    except UnicodeDecodeError as error:
        raise WireError(i18n("jslb.line_not_utf8", error.reason)) from error
    try:
        value: object = json.loads(
            string,
            object_pairs_hook=_object_make,
            parse_constant=_constant_refuse,
            parse_int=_integer_parse,
        )
    except json.JSONDecodeError as error:
        raise WireError(i18n("jslb.line_not_json", error.msg)) from error
    except (RecursionError, ValueError) as error:
        raise WireError(i18n("jslb.line_not_json", str(error))) from error
    if not isinstance(value, Object):
        raise WireError(i18n("jslb.line_not_object"))
    return value


# Reads lines and their blobs from a byte stream fed in pieces of any size.
class LineDecoder:
    # `sink_make(header)` returns the path a blob over `overflow_bytes` takes.
    def __init__(
        self,
        line_max: int,
        blob_max: int,
        message_max: int,
        overflow_bytes: int,
        sink_make: Callable[[Object], str],
    ) -> None:
        self._line_max = line_max
        self._blob_max = blob_max
        self._message_max = message_max
        self._overflow_bytes = overflow_bytes
        self._sink_make = sink_make
        self._failed = False
        self._fault: Exception | None = None
        self._text = bytearray()
        self._line: Object | None = None
        self._sizes: list[int] = []
        self._number = 0
        self._left = 0
        self._memory = bytearray()
        self._file: io.BufferedWriter | None = None
        self._path = ""
        self._hash = hashlib.sha256()

    # Returns the lines finished. A fault after them raises on the next call.
    def bytes_feed(self, data: bytes) -> list[Object]:
        fault = self._fault
        if fault is not None:
            self._fault = None
            raise fault
        if self._failed:
            raise WireError(i18n("jslb.decoder_failed"))
        self._failed = True
        lines: list[Object] = []
        try:
            self._bytes_read(data, lines)
            self._failed = False
        except Exception as error:
            if not lines:
                raise
            self._fault = error
        finally:
            if self._failed:
                self._file_shut()
        return lines

    # Returns whether the decoder stands between messages and has not failed.
    def idle(self) -> bool:
        return not self._failed and self._line is None and not self._text

    # Reads the bytes, adding each line they finish to `lines`.
    def _bytes_read(self, data: bytes, lines: list[Object]) -> None:
        offset = 0
        while True:
            line = self._line
            if line is None:
                end = data.find(b"\r", offset)
                if end < 0:
                    self._length_check(len(data) - offset)
                    self._text += data[offset:]
                    return
                self._length_check(end - offset)
                self._text += data[offset:end]
                offset = end + 1
                line = self._line_parse()
                if not self._sizes:
                    lines.append(line)
                    continue
                self._line = line
                self._blob_start(line, 1)
                continue
            count = min(self._left, len(data) - offset)
            self._blob_write(data[offset : offset + count])
            offset += count
            if self._left > 0:
                return
            self._blob_finish(line)
            if self._number < len(self._sizes):
                self._blob_start(line, self._number + 1)
                continue
            lines.append(line)
            self._line = None

    # Closes the file of a streamed blob when one is open, keeping its bytes.
    def _file_shut(self) -> None:
        file = self._file
        if file is not None:
            self._file = None
            file.close()

    # Refuses a line once its bytes and its CR would pass `line_max`.
    def _length_check(self, more: int) -> None:
        if len(self._text) + more + 1 > self._line_max:
            raise WireError(i18n("jslb.line_over_max", self._line_max))

    # Parses and checks the line read, refusing a blob or a message too large.
    def _line_parse(self) -> Object:
        length = len(self._text) + 1
        line = _line_decode(bytes(self._text))
        self._text.clear()
        sizes = _line_check(line, True)
        for number, size in enumerate(sizes, 1):
            if size > self._blob_max:
                raise WireError(
                    i18n("jslb.blob_over_max", number, size, self._blob_max)
                )
        total = length + sum(sizes)
        # Memory per message is bounded here by `message_max`, a settled limit.
        if total > self._message_max:
            raise WireError(
                i18n("jslb.message_over", total, self._message_max)
            )
        self._sizes = sizes
        return line

    # Starts blob `number` of the line, in memory or in a new sink file.
    def _blob_start(self, line: Object, number: int) -> None:
        self._number = number
        self._left = self._sizes[number - 1]
        if self._left > self._overflow_bytes:
            self._path = self._sink_make(line[number])
            self._file = open(self._path, "xb")
            self._hash = hashlib.sha256()
        else:
            self._memory = bytearray()

    # Adds bytes to the blob being read, hashing those that go to a file.
    def _blob_write(self, chunk: bytes) -> None:
        if self._file is None:
            self._memory += chunk
        else:
            self._file.write(chunk)
            self._hash.update(chunk)
        self._left -= len(chunk)

    # Sets `d` on the finished blob, and for a file `sha256`, over any sent.
    def _blob_finish(self, line: Object) -> None:
        header = line[self._number]
        if self._file is None:
            header["d"] = bytes(self._memory)
            self._memory = bytearray()
            return
        self._file.close()
        self._file = None
        header["d"] = self._path
        header["sha256"] = self._hash.hexdigest()
