# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of jslb: the builders, field access, the encoder and its refusals,
# the debug rendering, the decoder, its limits, its number rules, its deferred
# fault and every hard error, each refusal compared with its text in the gold
# record, json_decode, blobs streamed into a sink in a scratch directory under
# build/, a file whose close fails after a fault, and the vectors
# vectors_make.py writes, each read whole, by single bytes and split at every
# offset. The decoders' limits here and the sizes chosen are gold values.

import errno, harness, hashlib, jslb, json, math, os, tempfile, unittest
import unittest.mock
from collections.abc import Callable, Iterable, Iterator
from typing import Any, NoReturn

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The vectors and their sidecars, as `vectors_make.py` writes them.
_VECTORS_PATH = os.path.join(_BUILD_PATH, "vectors")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_jslb"

# The longest line the decoders here read with its CR, its writer's choice.
_LINE_MAX: int = harness.gold_get(f"{_GOLD_ID}.line_max")

# The most bytes one message's blobs come to here, its writer's choice.
_BLOB_MAX: int = harness.gold_get(f"{_GOLD_ID}.blob_max")

# The largest blob the decoders here keep in memory, its writer's choice.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# The digits of a key past the 4300 an `int` reads, its writer's choice.
_LONG_DIGITS: int = harness.gold_get(f"{_GOLD_ID}.long_digits")

# The integers just past `2**53` either way, as their tokens.
_INTEGERS_PAST = ("9007199254740993", "-9007199254740993")

# The texts that refuse each of `_INTEGERS_PAST`, in order.
_PAST_TEXTS = ("jslb_integer_refused_above", "jslb_integer_refused_below")

# Integer tokens of 17, 310 and 4301 digits, each past `2**53`.
_INTEGERS_LONG = ("1" * 17, "1" + "0" * 309, "1" + "0" * 4300)

# Number tokens whose float overflows to an infinity.
_OVERFLOWS = ("1e400", "-1e400", "1.5e400")

# The texts that refuse each of `_OVERFLOWS`, in order.
_OVERFLOW_TEXTS = (
    "jslb_number_overflow_positive",
    "jslb_number_overflow_negative",
    "jslb_number_overflow_fraction",
)

# Number tokens with an exponent, within the doubles.
_DOUBLES = ("1e+300", "9.007199254740994e+15")

# Arrays nested deeper than the JSON parser recurses, its writer's choice.
_DEEP_NESTING: int = harness.gold_get(f"{_GOLD_ID}.deep_nesting")

# A line with no blobs, which a decoder that failed refuses all the same.
_ECHO_LINE = b'{"0":{"t":"echo"}}\r'


# A text of this module's gold, each `{n}` replaced by the n-th value given.
def _text_get(name: str, *values: object) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    for index, value in enumerate(values):
        text = text.replace("{" + str(index) + "}", str(value))
    return text


# Hands out new paths in a scratch directory and keeps the headers given.
class _ScratchSink:
    # Keeps the directory, with no path handed out yet.
    def __init__(self, directory: str) -> None:
        self.directory = directory
        self.headers: list[jslb.Object] = []

    # Returns a new path for the blob of the header.
    def path_make(self, header: jslb.Object) -> str:
        self.headers.append(header)
        return os.path.join(self.directory, f"blob_{len(self.headers)}")


# A file whose every write fails as on a full disk, and which records a close.
class _FailingFile:
    # Holds the error each write raises, with the file not closed yet.
    def __init__(self) -> None:
        self.error = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        self.closed = False

    # Raises the error, as a write to a full disk does.
    def write(self, data: bytes) -> NoReturn:
        raise self.error

    # Records that the file was closed.
    def close(self) -> None:
        self.closed = True


# A file whose every write fails as on a full disk, and whose close fails.
class _BrokenFile:
    # Holds the error each write raises and the error the close raises.
    def __init__(self) -> None:
        self.error = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        self.close_error = OSError(errno.EIO, os.strerror(errno.EIO))

    # Raises the error, as a write to a full disk does.
    def write(self, data: bytes) -> NoReturn:
        raise self.error

    # Raises the close's error, as a close that cannot flush does.
    def close(self) -> NoReturn:
        raise self.close_error


# A test case that compares raised messages and asks the stdlib for reasons.
class _MessageCase(unittest.TestCase):
    # Asserts the call raises the kind of error carrying exactly the message.
    def raised_assert(
        self,
        kind: type[BaseException],
        message: str,
        call: Callable[[], object],
    ) -> None:
        with self.assertRaises(kind) as caught:
            call()
        self.assertEqual(caught.exception.args, (message,))

    # Returns the reason the stdlib JSON parser gives for refusing the text.
    def parse_reason(self, text: str) -> str:
        with self.assertRaises(json.JSONDecodeError) as caught:
            json.loads(text)
        return caught.exception.msg

    # Returns the reason the stdlib gives for refusing the bytes as `UTF-8`.
    def decode_reason(self, data: bytes) -> str:
        with self.assertRaises(UnicodeDecodeError) as caught:
            data.decode("utf-8")
        return caught.exception.reason


# A test case with a scratch directory under `build` and a sink in it.
class _ScratchCase(_MessageCase):
    # Makes the scratch directory, removed when the test ends.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.sink = _ScratchSink(self.scratch)

    # Returns a new decoder with the limits here, streaming into the sink.
    def decoder_make(self) -> jslb.LineDecoder:
        return jslb.LineDecoder(
            _LINE_MAX,
            _BLOB_MAX,
            _OVERFLOW_BYTES,
            self.sink.path_make,
        )

    # Returns a new decoder with a sidecar's limits, streaming into the sink.
    def sidecar_decoder(self, sidecar: dict[str, Any]) -> jslb.LineDecoder:
        limits: dict[str, int] = sidecar["limits"]
        return jslb.LineDecoder(
            limits["line_max"],
            limits["blob_max"],
            limits["overflow_bytes"],
            self.sink.path_make,
        )

    # Feeds the pieces to the decoder and returns every line they finish.
    def pieces_decode(
        self, decoder: jslb.LineDecoder, pieces: Iterable[bytes]
    ) -> list[jslb.Object]:
        lines: list[jslb.Object] = []
        for piece in pieces:
            lines += decoder.bytes_feed(piece)
        return lines


# Returns the bytes the encoder's pieces stand for, reading each file path.
def _pieces_join(pieces: Iterable[bytes | str]) -> bytes:
    parts: list[bytes] = []
    for piece in pieces:
        if isinstance(piece, str):
            with open(piece, "rb") as file:
                parts.append(file.read())
        else:
            parts.append(piece)
    return b"".join(parts)


# Returns an `echo` message, its line padded to `length` bytes, then blobs.
def _message_padded(length: int, blobs: list[bytes]) -> bytes:
    made = [jslb.blob_make(data) for data in blobs]
    header = jslb.header_make("echo")
    short = len(next(jslb.line_encode(jslb.line_make(header, made, pad=""))))
    line = jslb.line_make(header, made, pad="a" * (length - short))
    return _pieces_join(jslb.line_encode(line))


# Returns a decoded line as a sidecar holds it, each blob's `d` in hex.
def _line_plain(line: jslb.Object) -> dict[int | str, Any]:
    plain: dict[int | str, Any] = dict(line)
    for number in range(1, jslb.field_get(line[0], "blobs") + 1):
        header: dict[int | str, Any] = dict(line[number])
        data = header["d"]
        if isinstance(data, str):
            with open(data, "rb") as file:
                data = file.read()
        header["d"] = data.hex()
        plain[number] = header
    return plain


# Returns a decoded line without the `sha256` added to each streamed blob.
def _line_sent(line: jslb.Object) -> jslb.Object:
    sent = jslb.Object(line)
    for number in range(1, jslb.field_get(line[0], "blobs") + 1):
        header: dict[int | str, Any] = line[number]
        if isinstance(header["d"], str):
            sent[number] = jslb.Object(
                (name, value)
                for name, value in header.items()
                if name != "sha256"
            )
    return sent


# Yields the ways to feed bytes: whole, by single bytes, split at each offset.
def _feeds_make(data: bytes) -> Iterator[list[bytes]]:
    yield [data]
    yield [data[index : index + 1] for index in range(len(data))]
    for index in range(len(data) + 1):
        yield [data[:index], data[index:]]


# Returns a vector's bytes and its sidecar.
def _vector_read(name: str) -> tuple[bytes, dict[str, Any]]:
    with open(os.path.join(_VECTORS_PATH, name + ".jslb"), "rb") as file:
        data = file.read()
    path = os.path.join(_VECTORS_PATH, name + ".json")
    with open(path, encoding="utf-8") as file:
        sidecar: dict[str, Any] = json.load(file)
    return data, sidecar


# Returns the names of the vectors whose sidecar holds an error, or not.
def _vector_names(error: bool) -> list[str]:
    names = sorted(
        name.removesuffix(".jslb")
        for name in os.listdir(_VECTORS_PATH)
        if name.endswith(".jslb")
    )
    return [
        name for name in names if ("error" in _vector_read(name)[1]) == error
    ]


# Tests the attribute access of a decoded object.
class TestObject(_MessageCase):
    # A string key reads as an attribute.
    def test_attribute_read(self) -> None:
        line = jslb.Object()
        line["d"] = b"blob"
        self.assertEqual(line.d, b"blob")

    # A missing key is a missing attribute, so `hasattr` is false.
    def test_attribute_missing(self) -> None:
        line = jslb.Object()
        self.assertFalse(hasattr(line, "d"))
        message = _text_get("jslb_attribute_missing")
        self.raised_assert(AttributeError, message, lambda: line.d)

    # A key named like a dict method reads only with `[]`, as the method wins.
    def test_attribute_shadowed(self) -> None:
        names = (
            "keys",
            "items",
            "values",
            "get",
            "copy",
            "update",
            "pop",
            "clear",
        )
        line = jslb.Object((name, index) for index, name in enumerate(names))
        for index, name in enumerate(names):
            self.assertEqual(line[name], index)
            self.assertTrue(callable(getattr(line, name)))


# Tests `header_make`, `blob_make` and `line_make`.
class TestBuild(_ScratchCase):
    # A header holds only its type when every field is at its default.
    def test_header_defaults(self) -> None:
        header = jslb.header_make("echo", version=0)
        self.assertEqual(list(header.items()), [("t", "echo")])
        header = jslb.header_make("echo", full=True)
        self.assertEqual(list(header.items()), [("type", "echo")])

    # Every field is set, in order, with short names.
    def test_header_short(self) -> None:
        header = jslb.header_make("kv.put", version=1, id=2, reply=3, key="a")
        self.assertEqual(
            list(header.items()),
            [("t", "kv.put"), ("v", 1), ("i", 2), ("r", 3), ("k", "a")],
        )

    # Every field is set, in order, with full names.
    def test_header_full(self) -> None:
        header = jslb.header_make(
            "kv.put", version=1, id=2, reply=3, key="a", full=True
        )
        self.assertEqual(
            list(header.items()),
            [
                ("type", "kv.put"),
                ("version", 1),
                ("id", 2),
                ("reply", 3),
                ("key", "a"),
            ],
        )

    # A blob of bytes is measured and keeps the same bytes object as `d`.
    def test_blob_bytes(self) -> None:
        data = b"\r\n\x03"
        blob = jslb.blob_make(data, "a/b", mime="text/plain")
        self.assertEqual(list(blob.keys()), ["s", "k", "mime", "d"])
        self.assertEqual(blob["s"], 3)
        self.assertIs(blob["d"], data)

    # A blob given as a file path measures the file and keeps the path.
    def test_blob_path(self) -> None:
        path = os.path.join(self.scratch, "file")
        with open(path, "wb") as file:
            file.write(b"12345")
        blob = jslb.blob_make(path)
        self.assertEqual(list(blob.items()), [("s", 5), ("d", path)])

    # A field that `blob_make` sets cannot be given as a handler field.
    def test_blob_reserved(self) -> None:
        for name in ("s", "k", "d", "size"):
            message = _text_get(f"jslb_blob_field_reserved_{name}")
            self.raised_assert(
                ValueError, message, lambda: jslb.blob_make(b"", **{name: "x"})
            )

    # Blob headers are numbered from 1 and counted in a copy of the header.
    def test_line_numbering(self) -> None:
        header = jslb.header_make("echo", id=1)
        first = jslb.blob_make(b"one")
        second = jslb.blob_make(b"two", "k")
        line = jslb.line_make(header, [first, second], text="x")
        self.assertEqual(list(line.keys()), [0, 1, 2, "text"])
        self.assertEqual(
            list(line[0].items()), [("t", "echo"), ("i", 1), ("b", 2)]
        )
        self.assertEqual(list(header.items()), [("t", "echo"), ("i", 1)])
        self.assertEqual(line[1], first)
        self.assertEqual(line[2], second)

    # A line with no blobs leaves the count out.
    def test_line_empty(self) -> None:
        line = jslb.line_make(jslb.header_make("echo"), [])
        self.assertEqual(line, {0: {"t": "echo"}})

    # A full header gives the blob headers full names for size and key.
    def test_line_full(self) -> None:
        header = jslb.header_make("echo", full=True)
        blob = jslb.blob_make(b"ab", "k", n=1)
        line = jslb.line_make(header, [blob])
        self.assertEqual(
            list(line[0].items()), [("type", "echo"), ("blobs", 1)]
        )
        self.assertEqual(
            list(line[1].items()),
            [("size", 2), ("key", "k"), ("n", 1), ("d", b"ab")],
        )

    # A header that already counts blobs is refused.
    def test_line_counted(self) -> None:
        header = jslb.header_make("echo")
        header["b"] = 1
        blobs = [jslb.blob_make(b"x")]
        message = _text_get("jslb_blobs_preset")
        self.raised_assert(
            ValueError, message, lambda: jslb.line_make(header, blobs)
        )


# Tests `field_get`, `headers_of` and `payload_of`.
class TestFields(_MessageCase):
    # Either name form finds each field of a short header.
    def test_field_short(self) -> None:
        header = jslb.header_make("echo", version=2, id=3, reply=4, key="k")
        header["b"] = 1
        expected = (
            ("t", "type", "echo"),
            ("v", "version", 2),
            ("i", "id", 3),
            ("r", "reply", 4),
            ("k", "key", "k"),
            ("b", "blobs", 1),
        )
        for short, full, value in expected:
            self.assertEqual(jslb.field_get(header, short), value)
            self.assertEqual(jslb.field_get(header, full), value)

    # Either name form finds each field of full headers, blob headers too.
    def test_field_full(self) -> None:
        header = jslb.header_make("echo", version=2, full=True)
        self.assertEqual(jslb.field_get(header, "t"), "echo")
        self.assertEqual(jslb.field_get(header, "version"), 2)
        blob = jslb.line_make(header, [jslb.blob_make(b"ab", "k")])[1]
        self.assertEqual(jslb.field_get(blob, "s"), 2)
        self.assertEqual(jslb.field_get(blob, "key"), "k")
        self.assertEqual(jslb.field_get(blob, "data"), b"ab")

    # An absent field gives its default, or `None` when it has none.
    def test_field_defaults(self) -> None:
        header = jslb.header_make("echo")
        self.assertEqual(jslb.field_get(header, "version"), 0)
        self.assertEqual(jslb.field_get(header, "b"), 0)
        for name in ("i", "reply", "k"):
            self.assertIsNone(jslb.field_get(header, name))
        blob = jslb.Object()
        blob["s"] = 0
        self.assertIsNone(jslb.field_get(blob, "d"))

    # An absent required field raises, as does a name that is no field.
    def test_field_refused(self) -> None:
        for name in ("type", "s"):
            message = _text_get(f"jslb_field_missing_{name}")
            self.raised_assert(
                KeyError, message, lambda: jslb.field_get(jslb.Object(), name)
            )
        header = jslb.header_make("echo")
        message = _text_get("jslb_field_unknown")
        self.raised_assert(
            ValueError, message, lambda: jslb.field_get(header, "sha256")
        )

    # A header holding both forms of a field raises.
    def test_field_forms(self) -> None:
        header = jslb.header_make("echo")
        header["type"] = "echo"
        message = _text_get("jslb_both_name_forms")
        self.raised_assert(
            jslb.WireError, message, lambda: jslb.field_get(header, "t")
        )

    # Probing stops at the first missing integer key, strings included.
    def test_headers_probing(self) -> None:
        document = jslb.Object()
        document[0] = jslb.header_make("scene")
        document[1] = "/metaverse/castle/1"
        document[2] = "/metaverse/hall/3"
        document[4] = "/metaverse/after/gap"
        document["body"] = {"text": "x"}
        self.assertEqual(
            jslb.headers_of(document),
            [{"t": "scene"}, "/metaverse/castle/1", "/metaverse/hall/3"],
        )
        self.assertEqual(jslb.headers_of(jslb.Object()), [])

    # The payload is every string key, in order.
    def test_payload_keys(self) -> None:
        blob = jslb.blob_make(b"x")
        line = jslb.line_make(jslb.header_make("echo"), [blob], b=1, a=2)
        self.assertEqual(
            list(jslb.payload_of(line).items()), [("b", 1), ("a", 2)]
        )


# Tests `line_encode` and its refusals.
class TestEncode(_ScratchCase):
    # A line with no blobs is its JSON text with no spaces and a CR.
    def test_encode_empty(self) -> None:
        header = jslb.header_make("echo")
        line = jslb.line_make(header, [], a=[1, {"b": None}])
        self.assertEqual(
            list(jslb.line_encode(line)),
            [b'{"0":{"t":"echo"},"a":[1,{"b":null}]}\r'],
        )

    # Integer keys come first in ascending order, in nested objects too.
    def test_encode_order(self) -> None:
        line = jslb.Object()
        line["z"] = {"y": 1, 1: "one", 0: "zero"}
        line[1] = jslb.blob_make(b"x")
        line[0] = {"t": "echo", "b": 1}
        self.assertEqual(
            next(jslb.line_encode(line)),
            b'{"0":{"t":"echo","b":1},"1":{"s":1},'
            b'"z":{"0":"zero","1":"one","y":1}}\r',
        )

    # Each blob's `d` follows the JSON as the same bytes object or path.
    def test_encode_blobs(self) -> None:
        data = b"\r\x03\x04"
        path = os.path.join(self.scratch, "file")
        with open(path, "wb") as file:
            file.write(b"file bytes")
        blobs = [jslb.blob_make(data), jslb.blob_make(path, "k")]
        line = jslb.line_make(jslb.header_make("echo"), blobs)
        pieces = list(jslb.line_encode(line))
        self.assertEqual(len(pieces), 3)
        self.assertEqual(
            pieces[0],
            b'{"0":{"t":"echo","b":2},"1":{"s":3},"2":{"s":10,"k":"k"}}\r',
        )
        self.assertIs(pieces[1], data)
        self.assertEqual(pieces[2], path)

    # Text is raw `UTF-8`, escaped as JSON does, with no CR but the last.
    def test_encode_text(self) -> None:
        raw = chr(0xE9) + chr(0x4E2D) + chr(0x1F600) + chr(0x7F)
        header = jslb.header_make("echo")
        line = jslb.line_make(header, [], text=raw + "\r\n\x00")
        encoded = _pieces_join(jslb.line_encode(line))
        expected = '{"0":{"t":"echo"},"text":"' + raw + '\\r\\n\\u0000"}\r'
        self.assertEqual(encoded, expected.encode("utf-8"))
        self.assertEqual(encoded.count(b"\r"), 1)

    # Integers within `2**53` either way are written, larger ones refused.
    def test_integer_limits(self) -> None:
        header = jslb.header_make("echo")
        line = jslb.line_make(header, [], high=2**53, low=-(2**53))
        self.assertEqual(
            _pieces_join(jslb.line_encode(line)),
            b'{"0":{"t":"echo"},"high":9007199254740992,'
            b'"low":-9007199254740992}\r',
        )
        cases = (
            (2**53 + 1, "jslb_integer_refused_above"),
            (-(2**53) - 1, "jslb_integer_refused_below"),
            ([2**60], "jslb_integer_refused_power"),
            ({"a": 2**60}, "jslb_integer_refused_power"),
        )
        for value, name in cases:
            message = _text_get(name)
            line = jslb.line_make(header, [], value=value)
            self.raised_assert(
                ValueError, message, lambda: jslb.line_encode(line)
            )

    # Doubles past `2**53` either way are written as Python writes a float.
    def test_double_range(self) -> None:
        header = jslb.header_make("echo")
        line = jslb.line_make(
            header, [], tenth=1e16, low=-1e300, top=1.7976931348623157e308
        )
        self.assertEqual(
            _pieces_join(jslb.line_encode(line)),
            b'{"0":{"t":"echo"},"tenth":1e+16,"low":-1e+300,'
            b'"top":1.7976931348623157e+308}\r',
        )

    # `NaN` and the infinities are refused.
    def test_float_refused(self) -> None:
        header = jslb.header_make("echo")
        cases = (
            (math.nan, "jslb_number_refused_nan"),
            (math.inf, "jslb_number_refused_infinity"),
            (-math.inf, "jslb_number_refused_infinity_negative"),
            ([math.nan], "jslb_number_refused_nan"),
        )
        for value, name in cases:
            message = _text_get(name)
            line = jslb.line_make(header, [], value=value)
            self.raised_assert(
                ValueError, message, lambda: jslb.line_encode(line)
            )

    # A key that would decode as another key or type is refused.
    def test_key_refused(self) -> None:
        header = jslb.header_make("echo")
        cases = (
            ({"5": 1}, "jslb_key_refused_digits"),
            ({-1: 1}, "jslb_key_refused_negative"),
            ({True: 1}, "jslb_key_refused_bool"),
            ({1.5: 1}, "jslb_key_refused_float"),
        )
        for value, name in cases:
            message = _text_get(name)
            line = jslb.line_make(header, [], value=value)
            self.raised_assert(
                ValueError, message, lambda: jslb.line_encode(line)
            )
        for name in ("5", "01"):
            message = _text_get(f"jslb_payload_digit_key_{name}")
            line = jslb.line_make(header, [], **{name: 1})
            self.raised_assert(
                jslb.WireError, message, lambda: jslb.line_encode(line)
            )
        line = jslb.line_make(header, [], value={"01": 1})
        self.assertEqual(
            next(jslb.line_encode(line)),
            b'{"0":{"t":"echo"},"value":{"01":1}}\r',
        )

    # A blob whose `d` is missing or of another size is refused.
    def test_size_differs(self) -> None:
        header = jslb.header_make("echo")
        blob = jslb.blob_make(b"abc")
        blob["s"] = 4
        line = jslb.line_make(header, [blob])
        message = _text_get("jslb_blob_size_differs")
        self.raised_assert(ValueError, message, lambda: jslb.line_encode(line))
        blob = jslb.blob_make(b"abc")
        del blob["d"]
        line = jslb.line_make(header, [blob])
        message = _text_get("jslb_blob_data_missing")
        self.raised_assert(ValueError, message, lambda: jslb.line_encode(line))

    # The encoder refuses a line that the decoder would refuse.
    def test_encode_checked(self) -> None:
        message = _text_get("jslb_no_header_zero")
        self.raised_assert(
            jslb.WireError, message, lambda: jslb.line_encode(jslb.Object())
        )
        line = jslb.line_make(jslb.header_make("echo"), [jslb.blob_make(b"x")])
        line[0]["b"] = 2
        message = _text_get("jslb_blobs_mismatch_two")
        self.raised_assert(
            jslb.WireError, message, lambda: jslb.line_encode(line)
        )
        line = jslb.line_make(jslb.header_make("echo"), [])
        line[0]["x"] = 1
        message = _text_get("jslb_unknown_line_field_x")
        self.raised_assert(
            jslb.WireError, message, lambda: jslb.line_encode(line)
        )


# Tests `line_render`, the debug form.
class TestRender(unittest.TestCase):
    # The JSON text is followed by one tag per blob, numbered from 1.
    def test_render_blobs(self) -> None:
        blobs = [jslb.blob_make(b"\r"), jslb.blob_make(b"ab", "k")]
        line = jslb.line_make(jslb.header_make("echo", id=1), blobs, n=1)
        self.assertEqual(
            jslb.line_render(line),
            '{"0":{"t":"echo","i":1,"b":2},"1":{"s":1},"2":{"s":2,"k":"k"},'
            '"n":1}<blob "n"=1><blob "n"=2>',
        )

    # A line with no blobs renders as its JSON text alone.
    def test_render_plain(self) -> None:
        line = jslb.line_make(jslb.header_make("echo", full=True), [])
        self.assertEqual(jslb.line_render(line), '{"0":{"type":"echo"}}')


# Tests `LineDecoder` on lines, blobs in memory, its limits and every fault.
class TestDecode(_ScratchCase):
    # Asserts the bytes raise the message and leave the decoder unusable.
    def refused_assert(self, data: bytes, message: str) -> None:
        decoder = self.decoder_make()
        self.raised_assert(
            jslb.WireError, message, lambda: decoder.bytes_feed(data)
        )
        failed = _text_get("jslb_decoder_failed")
        self.raised_assert(
            jslb.WireError, failed, lambda: decoder.bytes_feed(_ECHO_LINE)
        )

    # A line decodes to an `Object` with integer keys, nested objects too.
    def test_decode_line(self) -> None:
        lines = self.pieces_decode(
            self.decoder_make(),
            [b'{"0":{"t":"echo","i":1},"x":[{"2":3,"02":4}]}\r'],
        )
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertIsInstance(line, jslb.Object)
        self.assertIsInstance(line[0], jslb.Object)
        self.assertEqual(list(line.keys()), [0, "x"])
        self.assertEqual(list(line[0].items()), [("t", "echo"), ("i", 1)])
        self.assertIsInstance(line.x[0], jslb.Object)
        self.assertEqual(list(line.x[0].items()), [(2, 3), ("02", 4)])

    # Blobs follow the CR, each `d` set to its bytes, empty ones too.
    def test_decode_blobs(self) -> None:
        lines = self.pieces_decode(
            self.decoder_make(),
            [
                b'{"0":{"t":"echo","b":3},"1":{"s":2},"2":{"s":0},'
                b'"3":{"s":0,"k":"z"}}\r\r\n'
            ],
        )
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line[1].d, b"\r\n")
        self.assertNotIn("sha256", line[1])
        self.assertEqual(line[2].d, b"")
        self.assertEqual(
            list(line[3].items()), [("s", 0), ("k", "z"), ("d", b"")]
        )

    # Returns the `n` of the one line the decoder reads from the bytes.
    def number_read(self, data: bytes) -> Any:
        lines = self.pieces_decode(self.decoder_make(), [data])
        self.assertEqual(len(lines), 1)
        return lines[0]["n"]

    # Asserts a line of the token refuses it, with a decoder that fits it.
    def token_refused(self, token: str, message: str) -> None:
        data = b'{"0":{"t":"echo"},"n":%s}\r' % token.encode()
        decoder = jslb.LineDecoder(
            2 * len(data), _BLOB_MAX, _OVERFLOW_BYTES, self.sink.path_make
        )
        self.raised_assert(
            jslb.WireError, message, lambda: decoder.bytes_feed(data)
        )

    # `2**53` either way reads as an `int`, one past either is refused.
    def test_integer_edges(self) -> None:
        for value in (2**53, -(2**53)):
            data = b'{"0":{"t":"echo"},"n":%d}\r' % value
            number = self.number_read(data)
            self.assertIs(type(number), int)
            self.assertEqual(number, value)
        for token, name in zip(_INTEGERS_PAST, _PAST_TEXTS):
            self.token_refused(token, _text_get(name))

    # A size past `2**53` is a refused integer before it is a bad size.
    def test_size_integer(self) -> None:
        token = _INTEGERS_PAST[0]
        data = b'{"0":{"t":"echo","b":1},"1":{"s":%s}}\r' % token.encode()
        self.refused_assert(data, _text_get("jslb_integer_refused_above"))

    # Integers of 17, 310 and 4301 digits are refused before `int` reads them.
    def test_integer_digits(self) -> None:
        for token in _INTEGERS_LONG:
            message = _text_get("jslb_integer_refused_long", token)
            self.token_refused(token, message)

    # A token whose float overflows to an infinity is refused.
    def test_number_overflow(self) -> None:
        for token, name in zip(_OVERFLOWS, _OVERFLOW_TEXTS):
            self.token_refused(token, _text_get(name))

    # A token with an exponent within the doubles reads as its float.
    def test_double_read(self) -> None:
        for token in _DOUBLES:
            data = b'{"0":{"t":"echo"},"n":%s}\r' % token.encode()
            number = self.number_read(data)
            self.assertIs(type(number), float)
            self.assertEqual(number, float(token))

    # Digits in a key or a string are no number, however many they are.
    def test_digits_text(self) -> None:
        digits = b"1" * 20
        data = b'{"0":{"t":"echo"},"n":{"%s":"\\"%s"}}\r' % (digits, digits)
        number = self.number_read(data)
        self.assertEqual(number, {int(digits): '"' + digits.decode()})

    # The first refused token in the text is the one reported.
    def test_number_first(self) -> None:
        past = _INTEGERS_PAST[0]
        message = _text_get("jslb_number_overflow_positive")
        self.token_refused(f"[1e400,{past}]", message)
        message = _text_get("jslb_integer_refused_above")
        self.token_refused(f"[{past},1e400]", message)

    # A line whose blobs are all empty is complete at its CR.
    def test_blob_empty(self) -> None:
        decoder = self.decoder_make()
        lines = decoder.bytes_feed(b'{"0":{"t":"echo","b":1},"1":{"s":0}}\r')
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0][1].d, b"")

    # Lines come back when their last byte arrives, several in one call.
    def test_decode_pieces(self) -> None:
        decoder = self.decoder_make()
        self.assertEqual(
            decoder.bytes_feed(b'{"0":{"t":"a","b":1},"1":{"s":3}}\rxy'), []
        )
        lines = decoder.bytes_feed(b'z{"0":{"t":"b"}}\r{"0":{"t":"c"}}\r{"0"')
        self.assertEqual([line[0]["t"] for line in lines], ["a", "b", "c"])
        self.assertEqual(lines[0][1].d, b"xyz")
        self.assertEqual(decoder.bytes_feed(b""), [])
        lines = decoder.bytes_feed(b':{"t":"d"}}\r')
        self.assertEqual([line[0]["t"] for line in lines], ["d"])

    # An integral float count or size is read as an `int`, in either form.
    def test_integral_floats(self) -> None:
        lines = self.pieces_decode(
            self.decoder_make(),
            [
                b'{"0":{"t":"echo","b":1.0},"1":{"s":2.0}}\rxy',
                b'{"0":{"type":"echo","blobs":1e0},"1":{"size":1.0}}\rz',
            ],
        )
        self.assertEqual(len(lines), 2)
        for line, count, size, data in (
            (lines[0], "b", "s", b"xy"),
            (lines[1], "blobs", "size", b"z"),
        ):
            self.assertIs(type(line[0][count]), int)
            self.assertEqual(line[0][count], 1)
            self.assertIs(type(line[1][size]), int)
            self.assertEqual(line[1][size], len(data))
            self.assertEqual(line[1].d, data)

    # Lines before a fault are returned and the next call raises the fault.
    def test_fault_deferred(self) -> None:
        decoder = self.decoder_make()
        data = _ECHO_LINE + b'{"t":"echo"}\r' + _ECHO_LINE
        self.assertEqual(decoder.bytes_feed(data), [{0: {"t": "echo"}}])
        self.assertFalse(decoder.idle())
        fault = _text_get("jslb_no_header_zero")
        self.raised_assert(
            jslb.WireError, fault, lambda: decoder.bytes_feed(b"")
        )
        failed = _text_get("jslb_decoder_failed")
        self.raised_assert(
            jslb.WireError, failed, lambda: decoder.bytes_feed(b"")
        )

    # The decoder is idle between messages only, and never after a fault.
    def test_idle_states(self) -> None:
        decoder = self.decoder_make()
        self.assertTrue(decoder.idle())
        self.assertEqual(decoder.bytes_feed(b'{"0":{"t":"echo","b":1}'), [])
        self.assertFalse(decoder.idle())
        self.assertEqual(decoder.bytes_feed(b',"1":{"s":2}}\rx'), [])
        self.assertFalse(decoder.idle())
        self.assertEqual(len(decoder.bytes_feed(b"y")), 1)
        self.assertTrue(decoder.idle())
        message = _text_get("jslb_line_not_json", self.parse_reason(""))
        self.raised_assert(
            jslb.WireError, message, lambda: decoder.bytes_feed(b"\r")
        )
        self.assertFalse(decoder.idle())

    # A line of `line_max` bytes with its CR is read, one byte more is not.
    def test_line_max(self) -> None:
        prefix = b'{"0":{"t":"echo"},"pad":"'
        suffix = b'"}\r'
        pad = b"a" * (_LINE_MAX - len(prefix) - len(suffix))
        lines = self.pieces_decode(
            self.decoder_make(), [prefix + pad + suffix]
        )
        self.assertEqual(len(lines), 1)
        message = _text_get("jslb_line_over_max")
        self.refused_assert(prefix + pad + b"a" + suffix, message)

    # A line is refused once it passes `line_max`, before its CR arrives.
    def test_line_early(self) -> None:
        decoder = self.decoder_make()
        self.assertEqual(decoder.bytes_feed(b"{" * (_LINE_MAX - 1)), [])
        message = _text_get("jslb_line_over_max")
        self.raised_assert(
            jslb.WireError, message, lambda: decoder.bytes_feed(b"{")
        )

    # A blob of `blob_max` bytes is read, one more refused before buffering.
    def test_blob_max(self) -> None:
        line = b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r'
        over = line % (_BLOB_MAX + 1) + bytes(_BLOB_MAX + 1)
        message = _text_get("jslb_blobs_over")
        self.refused_assert(over, message)
        self.assertEqual(self.sink.headers, [])
        self.assertEqual(os.listdir(self.scratch), [])
        lines = self.pieces_decode(
            self.decoder_make(), [line % _BLOB_MAX, bytes(_BLOB_MAX)]
        )
        self.assertEqual(len(lines), 1)

    # Blobs of `blob_max` in all pass with a longest line, one byte more not.
    def test_blobs_summed(self) -> None:
        first = bytes(_BLOB_MAX // 2)
        rest = _BLOB_MAX - len(first)
        over = _message_padded(_LINE_MAX, [first, bytes(rest + 1)])
        message = _text_get("jslb_blobs_over")
        self.refused_assert(over, message)
        self.assertEqual(self.sink.headers, [])
        self.assertEqual(os.listdir(self.scratch), [])
        data = _message_padded(_LINE_MAX, [first, bytes(rest)])
        self.assertEqual(len(data), _LINE_MAX + _BLOB_MAX)
        lines = self.pieces_decode(self.decoder_make(), [data])
        self.assertEqual(len(lines), 1)

    # A line without header 0 is refused.
    def test_header_missing(self) -> None:
        message = _text_get("jslb_no_header_zero")
        self.refused_assert(b'{"t":"echo"}\r', message)
        self.refused_assert(b'{"1":{"s":0}}\r', message)

    # A header that is not a JSON object is refused.
    def test_header_object(self) -> None:
        self.refused_assert(
            b'{"0":"echo"}\r', _text_get("jslb_header_not_object_line")
        )
        self.refused_assert(
            b'{"0":{"t":"echo","b":1},"1":[]}\r',
            _text_get("jslb_header_not_object_blob"),
        )

    # A line header without a type string is refused.
    def test_type_missing(self) -> None:
        message = _text_get("jslb_no_type")
        self.refused_assert(b'{"0":{"i":1}}\r', message)
        self.refused_assert(b'{"0":{"t":null}}\r', message)
        self.refused_assert(b'{"0":{"t":1}}\r', message)
        self.refused_assert(b'{"0":{}}\r', message)

    # A blob count that differs from the blob headers is refused.
    def test_count_mismatch(self) -> None:
        cases = (
            (b'{"0":{"t":"echo","b":2},"1":{"s":0}}\r', "two"),
            (b'{"0":{"t":"echo"},"1":{"s":0}}\r', "zero"),
            (b'{"0":{"t":"echo","b":true},"1":{"s":0}}\r', "true"),
            (b'{"0":{"t":"echo","b":1.5},"1":{"s":0}}\r', "fraction"),
            (b'{"0":{"t":"echo","b":-1}}\r', "negative"),
        )
        for data, case in cases:
            message = _text_get(f"jslb_blobs_mismatch_{case}")
            self.refused_assert(data, message)

    # A gap in the blob headers is refused.
    def test_header_gap(self) -> None:
        self.refused_assert(
            b'{"0":{"t":"echo","b":2},"1":{"s":0},"3":{"s":0}}\r',
            _text_get("jslb_blob_gap_middle"),
        )
        self.refused_assert(
            b'{"0":{"t":"echo","b":1},"2":{"s":0}}\r',
            _text_get("jslb_blob_gap_first"),
        )

    # A size that is not a non negative integer is refused.
    def test_size_invalid(self) -> None:
        message = _text_get("jslb_bad_size")
        for size in (b"-1", b"1.5", b'"1"', b"true", b"null"):
            self.refused_assert(
                b'{"0":{"t":"echo","b":1},"1":{"s":%s}}\r' % size, message
            )
        self.refused_assert(
            b'{"0":{"t":"echo","b":1},"1":{"k":"a"}}\r', message
        )

    # A payload key of decimal digits is refused.
    def test_payload_digits(self) -> None:
        for name in ("01", "00"):
            message = _text_get(f"jslb_payload_digit_key_{name}")
            data = b'{"0":{"t":"echo"},"%s":1}\r' % name.encode()
            self.refused_assert(data, message)

    # Short and full names in one line are refused, across headers too.
    def test_forms_mixed(self) -> None:
        message = _text_get("jslb_both_name_forms")
        self.refused_assert(b'{"0":{"t":"echo","version":1}}\r', message)
        self.refused_assert(b'{"0":{"t":"echo","type":"echo"}}\r', message)
        self.refused_assert(
            b'{"0":{"type":"echo","blobs":1},"1":{"s":0}}\r', message
        )
        self.refused_assert(
            b'{"0":{"t":"echo","b":1},"1":{"s":0,"key":"a"}}\r', message
        )

    # An unknown field in the line header is refused.
    def test_line_field(self) -> None:
        for name in ("x", "s"):
            message = _text_get(f"jslb_unknown_line_field_{name}")
            data = b'{"0":{"t":"echo","%s":1}}\r' % name.encode()
            self.refused_assert(data, message)

    # A blob header that carries `d` or `data` on the wire is refused.
    def test_data_sent(self) -> None:
        message = _text_get("jslb_blob_data_field")
        self.refused_assert(
            b'{"0":{"t":"echo","b":1},"1":{"s":0,"d":""}}\r', message
        )
        self.refused_assert(
            b'{"0":{"type":"echo","blobs":1},"1":{"size":0,"data":""}}\r',
            message,
        )

    # A line that is not strict `UTF-8` or not a JSON object is refused.
    def test_text_invalid(self) -> None:
        for text in ("ff", "eda080", "c080"):
            data = bytes.fromhex(text)
            reason = self.decode_reason(data)
            message = _text_get("jslb_line_not_utf8", reason)
            self.refused_assert(b'{"0":{"t":"' + data + b'"}}\r', message)
        for text in ("{", ""):
            reason = self.parse_reason(text)
            message = _text_get("jslb_line_not_json", reason)
            self.refused_assert(text.encode() + b"\r", message)
        message = _text_get("jslb_line_not_object")
        self.refused_assert(b'[{"0":{"t":"echo"}}]\r', message)

    # A leading byte order mark is refused as not JSON.
    def test_mark_refused(self) -> None:
        marked = b"\xef\xbb\xbf" + _ECHO_LINE
        reason = self.parse_reason(marked[:-1].decode("utf-8"))
        self.refused_assert(marked, _text_get("jslb_line_not_json", reason))

    # The `NaN` and `Infinity` constants are refused as not JSON.
    def test_constant_refused(self) -> None:
        cases = (
            ("NaN", "jslb_line_not_json_nan"),
            ("Infinity", "jslb_line_not_json_infinity"),
            ("-Infinity", "jslb_line_not_json_infinity_negative"),
        )
        for constant, name in cases:
            message = _text_get(name)
            data = b'{"0":{"t":"echo"},"n":%s}\r' % constant.encode()
            self.refused_assert(data, message)

    # A key too long for an `int` is refused as not JSON.
    def test_key_long(self) -> None:
        digits = b"1" * _LONG_DIGITS
        data = b'{"0":{"t":"echo"},"n":{"' + digits + b'":1}}\r'
        decoder = jslb.LineDecoder(
            2 * len(data),
            _BLOB_MAX,
            _OVERFLOW_BYTES,
            self.sink.path_make,
        )
        with self.assertRaises(jslb.WireError) as caught:
            decoder.bytes_feed(data)
        cause = caught.exception.__cause__
        self.assertIs(type(cause), ValueError)
        message = _text_get("jslb_line_not_json", str(cause))
        self.assertEqual(caught.exception.args, (message,))

    # Arrays nested past the parser's depth are refused as not JSON.
    def test_nesting_deep(self) -> None:
        data = b'{"0":{"t":"echo"},"n":' + b"[" * _DEEP_NESTING + b"}\r"
        decoder = jslb.LineDecoder(
            2 * len(data), _BLOB_MAX, _OVERFLOW_BYTES, self.sink.path_make
        )
        with self.assertRaises(jslb.WireError) as caught:
            decoder.bytes_feed(data)
        cause = caught.exception.__cause__
        self.assertIs(type(cause), RecursionError)
        message = _text_get("jslb_line_not_json", str(cause))
        self.assertEqual(caught.exception.args, (message,))


# Tests blobs over `overflow_bytes`, streamed into the sink's files.
class TestStream(_ScratchCase):
    # A blob one byte over goes to the sink's file, hashed, `d` its path.
    def test_stream_sink(self) -> None:
        data = bytes(index % 256 for index in range(_OVERFLOW_BYTES + 1))
        line = b'{"0":{"t":"echo","b":2},"1":{"s":%d,"k":"big"},"2":{"s":1}}\r'
        lines = self.pieces_decode(
            self.decoder_make(), [line % len(data), data, b"x"]
        )
        self.assertEqual(len(lines), 1)
        blob = lines[0][1]
        self.assertIs(self.sink.headers[0], blob)
        self.assertEqual(list(blob.keys()), ["s", "k", "d", "sha256"])
        self.assertEqual(blob.d, os.path.join(self.scratch, "blob_1"))
        self.assertEqual(blob.sha256, hashlib.sha256(data).hexdigest())
        with open(blob.d, "rb") as file:
            self.assertEqual(file.read(), data)
        self.assertEqual(lines[0][2].d, b"x")

    # A blob of exactly `overflow_bytes` stays in memory, with no file.
    def test_stream_exact(self) -> None:
        data = bytes(index % 256 for index in range(_OVERFLOW_BYTES))
        line = b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % len(data)
        lines = self.pieces_decode(self.decoder_make(), [line + data])
        self.assertEqual(lines[0][1].d, data)
        self.assertNotIn("sha256", lines[0][1])
        self.assertEqual(os.listdir(self.scratch), [])

    # A streamed blob fed one byte at a time gives the same file and hash.
    def test_stream_bytes(self) -> None:
        data = bytes(index % 251 for index in range(3 * _OVERFLOW_BYTES))
        line = b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % len(data)
        stream = line + data
        lines = self.pieces_decode(
            self.decoder_make(),
            (stream[index : index + 1] for index in range(len(stream))),
        )
        self.assertEqual(len(lines), 1)
        with open(lines[0][1].d, "rb") as file:
            self.assertEqual(file.read(), data)
        self.assertEqual(lines[0][1].sha256, hashlib.sha256(data).hexdigest())

    # A sink path that already exists is refused and left as it was.
    def test_stream_existing(self) -> None:
        path = os.path.join(self.scratch, "taken")
        with open(path, "wb") as file:
            file.write(b"kept")
        decoder = jslb.LineDecoder(
            _LINE_MAX,
            _BLOB_MAX,
            _OVERFLOW_BYTES,
            lambda header: path,
        )
        size = _OVERFLOW_BYTES + 1
        with self.assertRaises(FileExistsError) as caught:
            decoder.bytes_feed(
                b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % size
            )
        self.assertEqual(caught.exception.filename, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), b"kept")

    # A streamed blob's file is closed when a write fails, at once or later.
    def test_stream_closed(self) -> None:
        size = _OVERFLOW_BYTES + 1
        data = b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\rx' % size
        failing = _FailingFile()
        decoder = self.decoder_make()
        with unittest.mock.patch(
            "jslb.open", create=True, return_value=failing
        ):
            with self.assertRaises(OSError) as caught:
                decoder.bytes_feed(data)
        self.assertIs(caught.exception, failing.error)
        self.assertTrue(failing.closed)
        failing = _FailingFile()
        decoder = self.decoder_make()
        with unittest.mock.patch(
            "jslb.open", create=True, return_value=failing
        ):
            lines = decoder.bytes_feed(_ECHO_LINE + data)
        self.assertEqual(lines, [{0: {"t": "echo"}}])
        self.assertTrue(failing.closed)
        with self.assertRaises(OSError) as caught:
            decoder.bytes_feed(b"")
        self.assertIs(caught.exception, failing.error)

    # A close that fails after a write failed raises, the write's error kept.
    def test_close_failure(self) -> None:
        size = _OVERFLOW_BYTES + 1
        data = b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\rx' % size
        broken = _BrokenFile()
        decoder = self.decoder_make()
        with unittest.mock.patch.object(
            jslb, "open", create=True, return_value=broken
        ):
            with self.assertRaises(OSError) as caught:
                decoder.bytes_feed(data)
        self.assertIs(caught.exception, broken.close_error)
        self.assertIs(caught.exception.__context__, broken.error)
        broken = _BrokenFile()
        decoder = self.decoder_make()
        with unittest.mock.patch.object(
            jslb, "open", create=True, return_value=broken
        ):
            lines = decoder.bytes_feed(_ECHO_LINE + data)
        self.assertEqual(lines, [{0: {"t": "echo"}}])
        with self.assertRaises(OSError) as caught:
            decoder.bytes_feed(b"")
        self.assertIs(caught.exception, broken.close_error)
        self.assertIs(caught.exception.__context__, broken.error)

    # A sent `sha256` is replaced on a streamed blob and kept on one in memory.
    def test_hash_sent(self) -> None:
        sent = b"0" * 64
        data = bytes(_OVERFLOW_BYTES + 1)
        head = b'{"0":{"t":"echo","b":2},"1":{"s":%d,"sha256":"%s"},'
        tail = b'"2":{"s":1,"sha256":"%s"}}\r'
        line = head % (len(data), sent) + tail % sent
        lines = self.pieces_decode(self.decoder_make(), [line + data + b"x"])
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            list(lines[0][1].items()),
            [
                ("s", len(data)),
                ("sha256", hashlib.sha256(data).hexdigest()),
                ("d", os.path.join(self.scratch, "blob_1")),
            ],
        )
        self.assertEqual(
            list(lines[0][2].items()),
            [("s", 1), ("sha256", sent.decode()), ("d", b"x")],
        )


# Tests `json_decode`, the decoder's number rules on any JSON text.
class TestJsonDecode(_MessageCase):
    # Any JSON value is returned, objects as `Object`s with `int` digit keys.
    def test_values(self) -> None:
        self.assertEqual(
            jslb.json_decode('[1,"a",{"b":null}]'), [1, "a", {"b": None}]
        )
        self.assertEqual(jslb.json_decode("12"), 12)
        value = jslb.json_decode('{"0":{"t":"echo"},"x":{"02":1,"2":3}}')
        self.assertIsInstance(value, jslb.Object)
        self.assertEqual(list(value.keys()), [0, "x"])
        self.assertIsInstance(value[0], jslb.Object)
        self.assertEqual(list(value.x.items()), [("02", 1), (2, 3)])

    # The tokens a line reads, read here the same.
    def test_numbers_read(self) -> None:
        for value in (2**53, -(2**53)):
            number = jslb.json_decode(str(value))
            self.assertIs(type(number), int)
            self.assertEqual(number, value)
        for token in _DOUBLES:
            number = jslb.json_decode(token)
            self.assertIs(type(number), float)
            self.assertEqual(number, float(token))
        digits = "1" * 20
        value = jslb.json_decode(f'{{"{digits}":"{digits}"}}')
        self.assertEqual(value, {int(digits): digits})

    # The tokens a line refuses, refused here the same.
    def test_numbers_refused(self) -> None:
        cases = [
            (token, _text_get(name))
            for token, name in zip(_INTEGERS_PAST, _PAST_TEXTS)
        ]
        cases += [
            (token, _text_get("jslb_integer_refused_long", token))
            for token in _INTEGERS_LONG
        ]
        cases += [
            (token, _text_get(name))
            for token, name in zip(_OVERFLOWS, _OVERFLOW_TEXTS)
        ]
        for token, message in cases:
            self.raised_assert(
                jslb.WireError, message, lambda: jslb.json_decode(token)
            )

    # A text that is not JSON is refused, the parser's error its cause.
    def test_not_json(self) -> None:
        for text in ("{", "", "[1,]"):
            reason = self.parse_reason(text)
            message = _text_get("jslb_text_not_json", reason)
            with self.assertRaises(jslb.WireError) as caught:
                jslb.json_decode(text)
            self.assertEqual(caught.exception.args, (message,))
            cause = caught.exception.__cause__
            self.assertIs(type(cause), json.JSONDecodeError)

    # The `NaN` and `Infinity` constants are refused as not JSON.
    def test_constant_refused(self) -> None:
        cases = (
            ("NaN", "jslb_text_not_json_nan"),
            ("Infinity", "jslb_text_not_json_infinity"),
            ("-Infinity", "jslb_text_not_json_infinity_negative"),
        )
        for constant, name in cases:
            message = _text_get(name)
            self.raised_assert(
                jslb.WireError, message, lambda: jslb.json_decode(constant)
            )


# Reads each vector `vectors_make.py` wrote, whole, by bytes and split.
class TestVectors(_ScratchCase):
    # Returns each error vector's slug and its message under the limits.
    def errors_expected(
        self, limits: dict[str, int]
    ) -> dict[str, tuple[str, str]]:
        blob_max = limits["blob_max"]
        over = (
            "blobs_over",
            _text_get("jslb_blobs_over_vector", blob_max + 1, blob_max),
        )
        start = self.decode_reason(bytes.fromhex("c080"))
        continuation = self.decode_reason(bytes.fromhex("eda080"))
        header = ("no_header_zero", _text_get("jslb_no_header_zero"))
        size = ("bad_size", _text_get("jslb_bad_size"))
        forms = ("both_name_forms", _text_get("jslb_both_name_forms"))
        typed = ("no_type", _text_get("jslb_no_type"))
        return {
            "error_after_line": header,
            "error_bad_size_boolean": size,
            "error_bad_size_fraction": size,
            "error_bad_size_missing": size,
            "error_bad_size_negative": size,
            "error_bad_size_string": size,
            "error_blob_data": (
                "blob_data_field",
                _text_get("jslb_blob_data_field"),
            ),
            "error_blob_gap": ("blob_gap", _text_get("jslb_blob_gap_middle")),
            "error_blob_gap_first": (
                "blob_gap",
                _text_get("jslb_blob_gap_first"),
            ),
            "error_blob_over_max": over,
            "error_blobs_mismatch": (
                "blobs_mismatch",
                _text_get("jslb_blobs_mismatch_two"),
            ),
            "error_blobs_mismatch_boolean": (
                "blobs_mismatch",
                _text_get("jslb_blobs_mismatch_true"),
            ),
            "error_blobs_mismatch_extra": (
                "blobs_mismatch",
                _text_get("jslb_blobs_mismatch_zero"),
            ),
            "error_blobs_over": over,
            "error_both_name_forms": forms,
            "error_both_name_forms_blob": forms,
            "error_header_not_object": (
                "header_not_object",
                _text_get("jslb_header_not_object_line"),
            ),
            "error_header_not_object_blob": (
                "header_not_object",
                _text_get("jslb_header_not_object_blob"),
            ),
            "error_infinity": (
                "line_not_json",
                _text_get("jslb_line_not_json_infinity"),
            ),
            "error_integer_above": (
                "integer_refused",
                _text_get("jslb_integer_refused_above"),
            ),
            "error_integer_below": (
                "integer_refused",
                _text_get("jslb_integer_refused_below"),
            ),
            "error_integer_digits_310": (
                "integer_refused",
                _text_get("jslb_integer_refused_long", "1" + "0" * 309),
            ),
            "error_integer_digits_4301": (
                "integer_refused",
                _text_get("jslb_integer_refused_long", "1" + "0" * 4300),
            ),
            "error_line_over_max": (
                "line_over_max",
                _text_get("jslb_line_over_max_vector", limits["line_max"]),
            ),
            "error_nan": (
                "line_not_json",
                _text_get("jslb_line_not_json_nan"),
            ),
            "error_no_header_zero": header,
            "error_no_type": typed,
            "error_no_type_string": typed,
            "error_not_object": (
                "line_not_object",
                _text_get("jslb_line_not_object"),
            ),
            "error_number_overflow": (
                "number_overflow",
                _text_get("jslb_number_overflow_positive"),
            ),
            "error_number_overflow_negative": (
                "number_overflow",
                _text_get("jslb_number_overflow_negative"),
            ),
            "error_payload_digit_key": (
                "payload_digit_key",
                _text_get("jslb_payload_digit_key_01"),
            ),
            "error_unknown_line_field": (
                "unknown_line_field",
                _text_get("jslb_unknown_line_field_x"),
            ),
            "error_utf8_overlong": (
                "line_not_utf8",
                _text_get("jslb_line_not_utf8", start),
            ),
            "error_utf8_surrogate": (
                "line_not_utf8",
                _text_get("jslb_line_not_utf8", continuation),
            ),
        }

    # Each success vector, and the bytes it encodes to, decode to its sidecar.
    def test_vectors_success(self) -> None:
        names = _vector_names(False)
        self.assertTrue(names, f"no success vectors in {_VECTORS_PATH}")
        for name in names:
            data, sidecar = _vector_read(name)
            messages = json.dumps(sidecar["messages"])
            decoded = self.pieces_decode(self.sidecar_decoder(sidecar), [data])
            encoded = b"".join(
                _pieces_join(jslb.line_encode(_line_sent(line)))
                for line in decoded
            )
            self.assertEqual(encoded == data, sidecar["canonical"], name)
            # Reads the vector, then the bytes encoded again when they differ.
            for source in dict.fromkeys((data, encoded)):
                for pieces in _feeds_make(source):
                    decoder = self.sidecar_decoder(sidecar)
                    lines = self.pieces_decode(decoder, pieces)
                    plain = json.dumps([_line_plain(line) for line in lines])
                    self.assertEqual(plain, messages, name)
                    renders = [jslb.line_render(line) for line in lines]
                    self.assertEqual(renders, sidecar["render"], name)

    # Each error vector gives its lines, then its fault, however it is fed.
    def test_vectors_error(self) -> None:
        names = _vector_names(True)
        self.assertTrue(names, f"no error vectors in {_VECTORS_PATH}")
        for name in names:
            data, sidecar = _vector_read(name)
            expected = self.errors_expected(sidecar["limits"])
            self.assertEqual(sorted(expected), names)
            slug, message = expected[name]
            self.assertEqual(sidecar["error"], slug, name)
            messages = json.dumps(sidecar["messages"])
            for pieces in _feeds_make(data):
                decoder = self.sidecar_decoder(sidecar)
                lines: list[jslb.Object] = []
                with self.assertRaises(jslb.WireError, msg=name) as caught:
                    for piece in pieces:
                        lines += decoder.bytes_feed(piece)
                    decoder.bytes_feed(b"")
                self.assertEqual(caught.exception.args, (message,), name)
                plain = json.dumps([_line_plain(line) for line in lines])
                self.assertEqual(plain, messages, name)
                renders = [jslb.line_render(line) for line in lines]
                self.assertEqual(renders, sidecar["render"], name)
