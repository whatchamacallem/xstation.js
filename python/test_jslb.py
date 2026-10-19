# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of jslb: the builders, field access, the encoder and its refusals,
# the debug rendering, the decoder and every hard error, blobs streamed into
# a sink in a scratch directory under build/, and the vectors vectors_make.py
# writes, each read whole, by single bytes and split at every offset.

import hashlib, jslb, json, math, os, tempfile, unittest
from collections.abc import Iterable, Iterator
from typing import Any

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The vectors and their sidecars, as `vectors_make.py` writes them.
_VECTORS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vectors"
)

# The longest line the decoders here read, its CR included.
_LINE_MAX = 4096

# The largest blob the decoders here read.
_BLOB_MAX = 65536

# The largest blob the decoders here keep in memory.
_OVERFLOW_BYTES = 1024

# A line with no blobs, which a decoder that failed refuses all the same.
_ECHO_LINE = b'{"0":{"t":"echo"}}\r'


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


# A test case with a scratch directory under `build` and a sink in it.
class _ScratchCase(unittest.TestCase):
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
            _LINE_MAX, _BLOB_MAX, _OVERFLOW_BYTES, self.sink.path_make
        )

    # Feeds the pieces to a new decoder and returns every line they finish.
    def pieces_decode(self, pieces: Iterable[bytes]) -> list[jslb.Object]:
        decoder = self.decoder_make()
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
        if jslb.field_get(line[number], "size") > _OVERFLOW_BYTES:
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
class TestObject(unittest.TestCase):
    # A string key reads as an attribute.
    def test_attribute_read(self) -> None:
        line = jslb.Object()
        line["d"] = b"blob"
        self.assertEqual(line.d, b"blob")

    # A missing key is a missing attribute, so `hasattr` is false.
    def test_attribute_missing(self) -> None:
        line = jslb.Object()
        self.assertFalse(hasattr(line, "d"))
        with self.assertRaises(AttributeError):
            getattr(line, "d")


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
        for name in ("s", "d", "size"):
            with self.assertRaises(ValueError):
                jslb.blob_make(b"", **{name: 1})

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
        with self.assertRaises(ValueError):
            jslb.line_make(header, [jslb.blob_make(b"x")])


# Tests `field_get`, `headers_of` and `payload_of`.
class TestFields(unittest.TestCase):
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
        with self.assertRaises(KeyError):
            jslb.field_get(jslb.Object(), "type")
        with self.assertRaises(KeyError):
            jslb.field_get(jslb.Object(), "s")
        with self.assertRaises(ValueError):
            jslb.field_get(jslb.header_make("echo"), "sha256")

    # A header holding both forms of a field raises.
    def test_field_forms(self) -> None:
        header = jslb.header_make("echo")
        header["type"] = "echo"
        with self.assertRaises(jslb.WireError):
            jslb.field_get(header, "t")

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
        for value in (2**53 + 1, -(2**53) - 1, [2**60], {"a": 2**60}):
            with self.assertRaises(ValueError):
                jslb.line_encode(jslb.line_make(header, [], value=value))

    # `NaN` and the infinities are refused.
    def test_float_refused(self) -> None:
        header = jslb.header_make("echo")
        for value in (math.nan, math.inf, -math.inf, [math.nan]):
            with self.assertRaises(ValueError):
                jslb.line_encode(jslb.line_make(header, [], value=value))

    # A key that would decode as another key or type is refused.
    def test_key_refused(self) -> None:
        header = jslb.header_make("echo")
        for value in ({"5": 1}, {-1: 1}, {True: 1}, {1.5: 1}):
            with self.assertRaises(ValueError):
                jslb.line_encode(jslb.line_make(header, [], value=value))
        for name in ("5", "01"):
            with self.assertRaises(jslb.WireError):
                jslb.line_encode(jslb.line_make(header, [], **{name: 1}))
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
        with self.assertRaises(ValueError):
            jslb.line_encode(jslb.line_make(header, [blob]))
        blob = jslb.blob_make(b"abc")
        del blob["d"]
        with self.assertRaises(ValueError):
            jslb.line_encode(jslb.line_make(header, [blob]))

    # The encoder refuses a line that the decoder would refuse.
    def test_encode_checked(self) -> None:
        with self.assertRaises(jslb.WireError):
            jslb.line_encode(jslb.Object())
        line = jslb.line_make(jslb.header_make("echo"), [jslb.blob_make(b"x")])
        line[0]["b"] = 2
        with self.assertRaises(jslb.WireError):
            jslb.line_encode(line)
        line = jslb.line_make(jslb.header_make("echo"), [])
        line[0]["x"] = 1
        with self.assertRaises(jslb.WireError):
            jslb.line_encode(line)


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


# Tests `LineDecoder` on lines and blobs in memory and on every hard error.
class TestDecode(_ScratchCase):
    # Asserts the bytes raise `WireError` and leave the decoder unusable.
    def refused_assert(self, data: bytes) -> None:
        decoder = self.decoder_make()
        with self.assertRaises(jslb.WireError):
            decoder.bytes_feed(data)
        with self.assertRaises(jslb.WireError):
            decoder.bytes_feed(_ECHO_LINE)

    # A line decodes to an `Object` with integer keys, nested objects too.
    def test_decode_line(self) -> None:
        lines = self.pieces_decode(
            [b'{"0":{"t":"echo","i":1},"x":[{"2":3,"02":4}]}\r']
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
            [
                b'{"0":{"t":"echo","b":3},"1":{"s":2},"2":{"s":0},'
                b'"3":{"s":0,"k":"z"}}\r\r\n'
            ]
        )
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line[1].d, b"\r\n")
        self.assertNotIn("sha256", line[1])
        self.assertEqual(line[2].d, b"")
        self.assertEqual(
            list(line[3].items()), [("s", 0), ("k", "z"), ("d", b"")]
        )

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

    # A line of `line_max` bytes with its CR is read, one byte more is not.
    def test_line_max(self) -> None:
        prefix = b'{"0":{"t":"echo"},"pad":"'
        suffix = b'"}\r'
        pad = b"a" * (_LINE_MAX - len(prefix) - len(suffix))
        self.assertEqual(len(self.pieces_decode([prefix + pad + suffix])), 1)
        self.refused_assert(prefix + pad + b"a" + suffix)

    # A line is refused once it passes `line_max`, before its CR arrives.
    def test_line_early(self) -> None:
        decoder = self.decoder_make()
        self.assertEqual(decoder.bytes_feed(b"{" * (_LINE_MAX - 1)), [])
        with self.assertRaises(jslb.WireError):
            decoder.bytes_feed(b"{")

    # A blob of `blob_max` bytes is read, one more is refused at the CR.
    def test_blob_max(self) -> None:
        line = b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % _BLOB_MAX
        lines = self.pieces_decode([line, bytes(_BLOB_MAX)])
        self.assertEqual(len(lines), 1)
        self.refused_assert(
            b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % (_BLOB_MAX + 1)
        )

    # A line without header 0 is refused.
    def test_header_missing(self) -> None:
        self.refused_assert(b'{"t":"echo"}\r')
        self.refused_assert(b'{"1":{"s":0}}\r')

    # A header that is not a JSON object is refused.
    def test_header_object(self) -> None:
        self.refused_assert(b'{"0":"echo"}\r')
        self.refused_assert(b'{"0":{"t":"echo","b":1},"1":[]}\r')

    # A line header without a type string is refused.
    def test_type_missing(self) -> None:
        self.refused_assert(b'{"0":{"i":1}}\r')
        self.refused_assert(b'{"0":{"t":null}}\r')
        self.refused_assert(b'{"0":{"t":1}}\r')
        self.refused_assert(b'{"0":{}}\r')

    # A blob count that differs from the blob headers is refused.
    def test_count_mismatch(self) -> None:
        self.refused_assert(b'{"0":{"t":"echo","b":2},"1":{"s":0}}\r')
        self.refused_assert(b'{"0":{"t":"echo"},"1":{"s":0}}\r')
        self.refused_assert(b'{"0":{"t":"echo","b":true},"1":{"s":0}}\r')
        self.refused_assert(b'{"0":{"t":"echo","b":-1}}\r')

    # A gap in the blob headers is refused.
    def test_header_gap(self) -> None:
        self.refused_assert(
            b'{"0":{"t":"echo","b":2},"1":{"s":0},"3":{"s":0}}\r'
        )
        self.refused_assert(b'{"0":{"t":"echo","b":1},"2":{"s":0}}\r')

    # A size that is not a non negative integer is refused.
    def test_size_invalid(self) -> None:
        for size in (b"-1", b"1.5", b'"1"', b"true", b"null"):
            self.refused_assert(
                b'{"0":{"t":"echo","b":1},"1":{"s":%s}}\r' % size
            )
        self.refused_assert(b'{"0":{"t":"echo","b":1},"1":{"k":"a"}}\r')

    # A payload key of decimal digits is refused.
    def test_payload_digits(self) -> None:
        self.refused_assert(b'{"0":{"t":"echo"},"01":1}\r')
        self.refused_assert(b'{"0":{"t":"echo"},"00":1}\r')

    # Short and full names in one line are refused, across headers too.
    def test_forms_mixed(self) -> None:
        self.refused_assert(b'{"0":{"t":"echo","version":1}}\r')
        self.refused_assert(b'{"0":{"t":"echo","type":"echo"}}\r')
        self.refused_assert(b'{"0":{"type":"echo","blobs":1},"1":{"s":0}}\r')
        self.refused_assert(
            b'{"0":{"t":"echo","b":1},"1":{"s":0,"key":"a"}}\r'
        )

    # An unknown field in the line header is refused.
    def test_line_field(self) -> None:
        self.refused_assert(b'{"0":{"t":"echo","x":1}}\r')
        self.refused_assert(b'{"0":{"t":"echo","s":1}}\r')

    # A blob header that carries `d` or `data` on the wire is refused.
    def test_data_sent(self) -> None:
        self.refused_assert(b'{"0":{"t":"echo","b":1},"1":{"s":0,"d":""}}\r')
        self.refused_assert(
            b'{"0":{"type":"echo","blobs":1},"1":{"size":0,"data":""}}\r'
        )

    # A line that is not strict `UTF-8` or not a JSON object is refused.
    def test_text_invalid(self) -> None:
        self.refused_assert(b'{"0":{"t":"\xff"}}\r')
        self.refused_assert(b'{"0":{"t":"\xed\xa0\x80"}}\r')
        self.refused_assert(b'{"0":{"t":"\xc0\x80"}}\r')
        self.refused_assert(b"{\r")
        self.refused_assert(b'[{"0":{"t":"echo"}}]\r')
        self.refused_assert(b"\r")

    # The `NaN` and `Infinity` constants are refused.
    def test_constant_refused(self) -> None:
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            self.refused_assert(b'{"0":{"t":"echo"},"n":%s}\r' % constant)


# Tests blobs over `overflow_bytes`, streamed into the sink's files.
class TestStream(_ScratchCase):
    # A blob one byte over goes to the sink's file, hashed, `d` its path.
    def test_stream_sink(self) -> None:
        data = bytes(index % 256 for index in range(_OVERFLOW_BYTES + 1))
        line = b'{"0":{"t":"echo","b":2},"1":{"s":%d,"k":"big"},"2":{"s":1}}\r'
        lines = self.pieces_decode([line % len(data), data, b"x"])
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
        lines = self.pieces_decode([line + data])
        self.assertEqual(lines[0][1].d, data)
        self.assertNotIn("sha256", lines[0][1])
        self.assertEqual(os.listdir(self.scratch), [])

    # A streamed blob fed one byte at a time gives the same file and hash.
    def test_stream_bytes(self) -> None:
        data = bytes(index % 251 for index in range(3 * _OVERFLOW_BYTES))
        line = b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % len(data)
        stream = line + data
        lines = self.pieces_decode(
            stream[index : index + 1] for index in range(len(stream))
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
            _LINE_MAX, _BLOB_MAX, _OVERFLOW_BYTES, lambda header: path
        )
        size = _OVERFLOW_BYTES + 1
        with self.assertRaises(FileExistsError):
            decoder.bytes_feed(
                b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % size
            )
        with open(path, "rb") as file:
            self.assertEqual(file.read(), b"kept")


# Reads each vector `vectors_make.py` wrote, whole, by bytes and split.
class TestVectors(_ScratchCase):
    # Each success vector decodes to its sidecar and encodes to its bytes.
    def test_vectors_success(self) -> None:
        names = _vector_names(False)
        self.assertTrue(names, f"no success vectors in {_VECTORS_PATH}")
        for name in names:
            data, sidecar = _vector_read(name)
            messages = json.dumps(sidecar["messages"])
            for pieces in _feeds_make(data):
                lines = self.pieces_decode(pieces)
                plain = json.dumps([_line_plain(line) for line in lines])
                self.assertEqual(plain, messages, name)
                renders = [jslb.line_render(line) for line in lines]
                self.assertEqual(renders, sidecar["render"], name)
            encoded = b"".join(
                _pieces_join(jslb.line_encode(_line_sent(line)))
                for line in self.pieces_decode([data])
            )
            self.assertEqual(encoded, data, name)

    # Each error vector raises `WireError` however it is fed.
    def test_vectors_error(self) -> None:
        names = _vector_names(True)
        self.assertTrue(names, f"no error vectors in {_VECTORS_PATH}")
        for name in names:
            data, _ = _vector_read(name)
            for pieces in _feeds_make(data):
                with self.assertRaises(jslb.WireError, msg=name):
                    self.pieces_decode(pieces)
