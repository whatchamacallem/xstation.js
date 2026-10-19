#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Writes the JSLB vectors that the Python and the TypeScript decoders read
# into python/vectors. NAME.jslb holds a stream of messages that jslb.py
# encodes or, for an error vector, bytes made by hand that the encoder would
# refuse. NAME.json beside it is what a decoder with the limits below returns:
# the messages, every key a string and each blob's d in lowercase hex, and
# their rendered form, or the slug of the fault:
#
#     python3 python/vectors_make.py

import argparse, hashlib, json, os, sys
from typing import Any, NamedTuple

# The checkout's `python` directory.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# Where the vectors and their sidecars go.
_VECTORS_PATH = os.path.join(_PYTHON_PATH, "vectors")

# The longest line a vector's decoder reads, its CR included.
_LINE_MAX = 4096

# The largest blob a vector's decoder reads.
_BLOB_MAX = 65536

# The largest blob a vector's decoder keeps in memory.
_OVERFLOW_BYTES = 1024

# Bytecode of `jslb` and of what it imports goes in `build`.
sys.pycache_prefix = os.path.join(
    os.path.dirname(_PYTHON_PATH), "build", "pycache"
)


# One message as encoded: the line's bytes ending in CR, then each blob's.
class _EncodedMessage(NamedTuple):
    line: bytes
    blobs: list[bytes]


# Returns `count` bytes that run through every byte value in turn.
def _pattern_make(count: int) -> bytes:
    return bytes(index % 256 for index in range(count))


# Splits what `jslb.line_encode` returns into the line and the blob bytes.
def _pieces_split(pieces: list[bytes | str]) -> _EncodedMessage:
    found: list[bytes] = []
    for piece in pieces:
        if not isinstance(piece, bytes):
            raise TypeError(f"a vector blob is the file {piece}, not bytes")
        found.append(piece)
    return _EncodedMessage(found[0], found[1:])


# Returns each success vector's name and its messages, encoded by `jslb`.
def _success_vectors() -> list[tuple[str, list[_EncodedMessage]]]:
    # Imported here so its bytecode goes under the prefix set above.
    import jslb

    # Makes an `echo` line carrying the blobs, each given as bytes.
    def echo_make(blobs: list[bytes], **payload: Any) -> jslb.Object:
        made = [jslb.blob_make(data) for data in blobs]
        return jslb.line_make(jslb.header_make("echo"), made, **payload)

    controls = b"\r\n\x03\x04\x13"
    invalid = bytes.fromhex("fffec080eda080f888808080e4b8")
    vectors: list[tuple[str, list[jslb.Object]]] = [
        ("empty_short", [echo_make([])]),
        (
            "empty_full",
            [jslb.line_make(jslb.header_make("echo", full=True), [])],
        ),
    ]
    for full, name in ((False, "fields_short"), (True, "fields_full")):
        header = jslb.header_make(
            "kv.put",
            version=2,
            id=3,
            reply=4,
            key="/metaverse/castle",
            full=full,
        )
        blob = jslb.blob_make(
            b"castle", "maps/castle.bin", mime="application/octet-stream"
        )
        vectors.append((name, [jslb.line_make(header, [blob], since=5)]))
    blobs = [b"one", b"two", b"three"]
    for count in range(4):
        header = jslb.header_make("echo", id=count + 1)
        made = [jslb.blob_make(data) for data in blobs[:count]]
        line = jslb.line_make(header, made, count=count)
        vectors.append((f"blobs_{count}", [line]))
    vectors += [
        ("blob_empty", [echo_make([b"", b"x", b""])]),
        ("blob_controls", [echo_make([controls, b"\r", b"\n"])]),
        ("blob_invalid_utf8", [echo_make([invalid], text="bytes")]),
        (
            "blob_overflow_exact",
            [echo_make([_pattern_make(_OVERFLOW_BYTES)])],
        ),
        (
            "blob_streamed",
            [
                echo_make(
                    [
                        _pattern_make(_OVERFLOW_BYTES + 1),
                        controls,
                        _pattern_make(2 * _OVERFLOW_BYTES),
                    ]
                )
            ],
        ),
    ]
    several = [
        jslb.line_make(jslb.header_make("echo", id=1), []),
        jslb.line_make(
            jslb.header_make("echo", reply=1),
            [jslb.blob_make(b"\r\r"), jslb.blob_make(b"")],
            text="two",
        ),
        jslb.line_make(
            jslb.header_make("echo", id=2, full=True),
            [jslb.blob_make(controls, "k")],
        ),
    ]
    vectors.append(("messages_several", several))
    text = "".join(chr(code) for code in (0xE9, 0x4E2D, 0x1F600, 0x2028))
    unicode = jslb.line_make(
        jslb.header_make("echo", key=chr(0x4E2D)),
        [],
        text=text,
        **{chr(0xE9): chr(0x1F600)},
    )
    vectors.append(("payload_unicode", [unicode]))
    escapes = "".join(chr(code) for code in range(0x20)) + '"\\/' + chr(0x7F)
    vectors.append(("payload_escapes", [echo_make([], text=escapes)]))
    values = echo_make(
        [],
        high=2**53,
        low=-(2**53),
        zero=0,
        negative=-1,
        flags=[True, False, None],
        nested=[1, [2, {}], {"a": []}],
        empty="",
    )
    vectors.append(("payload_values", [values]))
    document = {
        0: {"t": "scene", "v": 1},
        1: "/metaverse/castle/1",
        "text": "a scene",
    }
    put = jslb.line_make(
        jslb.header_make("doc.put", id=1),
        [],
        db="metaverse",
        id="castle",
        body=document,
    )
    vectors.append(("payload_document", [put]))
    length = len(next(jslb.line_encode(echo_make([], pad=""))))
    padded = echo_make([], pad="a" * (_LINE_MAX - length))
    vectors.append(("line_at_max", [padded]))
    return [
        (name, [_pieces_split(list(jslb.line_encode(line))) for line in lines])
        for name, lines in vectors
    ]


# Returns each error vector's name, the slug of its fault and its bytes.
def _error_vectors() -> list[tuple[str, str, bytes]]:
    prefix = b'{"0":{"t":"echo"},"pad":"'
    suffix = b'"}\r'
    pad = b"a" * (_LINE_MAX + 1 - len(prefix) - len(suffix))
    return [
        ("error_no_header_zero", "no_header_zero", b'{"t":"echo"}\r'),
        ("error_no_type", "no_type", b'{"0":{"i":1}}\r'),
        ("error_no_type_string", "no_type", b'{"0":{"t":1}}\r'),
        (
            "error_blobs_mismatch",
            "blobs_mismatch",
            b'{"0":{"t":"echo","b":2},"1":{"s":1}}\rx',
        ),
        (
            "error_blobs_mismatch_extra",
            "blobs_mismatch",
            b'{"0":{"t":"echo"},"1":{"s":1}}\rx',
        ),
        (
            "error_blob_gap",
            "blob_gap",
            b'{"0":{"t":"echo","b":2},"1":{"s":1},"3":{"s":1}}\rxy',
        ),
        (
            "error_blob_gap_first",
            "blob_gap",
            b'{"0":{"t":"echo","b":1},"2":{"s":1}}\rx',
        ),
        (
            "error_bad_size_missing",
            "bad_size",
            b'{"0":{"t":"echo","b":1},"1":{"k":"x"}}\r',
        ),
        (
            "error_bad_size_negative",
            "bad_size",
            b'{"0":{"t":"echo","b":1},"1":{"s":-1}}\r',
        ),
        (
            "error_bad_size_string",
            "bad_size",
            b'{"0":{"t":"echo","b":1},"1":{"s":"1"}}\rx',
        ),
        (
            "error_bad_size_fraction",
            "bad_size",
            b'{"0":{"t":"echo","b":1},"1":{"s":1.5}}\rxx',
        ),
        (
            "error_bad_size_boolean",
            "bad_size",
            b'{"0":{"t":"echo","b":1},"1":{"s":true}}\rx',
        ),
        (
            "error_payload_digit_key",
            "payload_digit_key",
            b'{"0":{"t":"echo"},"01":1}\r',
        ),
        (
            "error_both_name_forms",
            "both_name_forms",
            b'{"0":{"t":"echo","version":1}}\r',
        ),
        (
            "error_both_name_forms_blob",
            "both_name_forms",
            b'{"0":{"type":"echo","blobs":1},"1":{"s":1}}\rx',
        ),
        (
            "error_unknown_line_field",
            "unknown_line_field",
            b'{"0":{"t":"echo","x":1}}\r',
        ),
        ("error_line_over_max", "line_over_max", prefix + pad + suffix),
        (
            "error_blob_over_max",
            "blob_over_max",
            b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % (_BLOB_MAX + 1),
        ),
    ]


# What a decoder returns for a message: `d` in hex, `sha256` when streamed.
def _message_expected(message: _EncodedMessage) -> dict[str, Any]:
    expected: dict[str, Any] = json.loads(message.line[:-1].decode("utf-8"))
    for number, data in enumerate(message.blobs, 1):
        header: dict[str, Any] = expected[str(number)]
        header["d"] = data.hex()
        if len(data) > _OVERFLOW_BYTES:
            header["sha256"] = hashlib.sha256(data).hexdigest()
    return expected


# Returns the rendered form: the JSON text without `d`, then a tag per blob.
def _message_render(expected: dict[str, Any], count: int) -> str:
    sent = dict(expected)
    for number in range(1, count + 1):
        header: dict[str, Any] = expected[str(number)]
        sent[str(number)] = {
            name: value for name, value in header.items() if name != "d"
        }
    text = json.dumps(sent, ensure_ascii=False, separators=(",", ":"))
    tags = "".join(f'<blob "n"={number}>' for number in range(1, count + 1))
    return text + tags


# Writes a vector's bytes and its sidecar into the vectors directory.
def _vector_write(name: str, data: bytes, sidecar: dict[str, Any]) -> None:
    with open(os.path.join(_VECTORS_PATH, name + ".jslb"), "wb") as file:
        file.write(data)
    path = os.path.join(_VECTORS_PATH, name + ".json")
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(sidecar, allow_nan=False, indent=2) + "\n")


# Writes every vector and its sidecar.
def main() -> None:
    argparse.ArgumentParser(
        description="Write the JSLB vectors and their sidecars into"
        " python/vectors/."
    ).parse_args()
    os.makedirs(_VECTORS_PATH, exist_ok=True)
    for name, messages in _success_vectors():
        expected = [_message_expected(message) for message in messages]
        render = [
            _message_render(item, len(message.blobs))
            for item, message in zip(expected, messages, strict=True)
        ]
        data = b"".join(
            message.line + b"".join(message.blobs) for message in messages
        )
        _vector_write(name, data, {"messages": expected, "render": render})
    for name, slug, data in _error_vectors():
        _vector_write(name, data, {"error": slug})


if __name__ == "__main__":
    main()
