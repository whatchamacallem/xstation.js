#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Writes the JSLB vectors that the Python and the TypeScript decoders read
# into build/vectors, an intermediate made anew by test_all.py and by the test
# page's build before their tests read it, the files an earlier run left
# removed first. NAME.jslb holds a stream of messages that jslb.py
# encodes or bytes made by hand, which the encoder would write otherwise or
# refuse. NAME.json beside it holds the limits its decoder is built with, the
# messages that decoder returns, every key a string and each blob's d in
# lowercase hex, and their rendered form. A success sidecar says whether
# jslb.py encodes the messages back to the same bytes; an error sidecar names
# the slug of the fault that follows its messages. The number vectors are
# error vectors of the decoders' number rules: an integer token just past
# 2^53 either way, integers of 310 and of 4301 digits and a token whose
# double overflows either way, each refused at read. sha256.json beside them
# holds the digest vectors that check the hand written SHA-256 of the
# TypeScript at the edges of its padding: a JSON object whose keys sha256_55,
# sha256_56 and sha256_64 each name an object of an input of that many bytes,
# data, and its SHA-256 digest, sha256, both in lowercase hex.
# test_digests.json beside it holds the digests the TypeScript test modules
# compare with, a JSON object of each module's entries by name, each an
# input, data, and its digest, sha256, in the same form. The command line
# writes them all into build/vectors:
#
#     python3 python/vectors_make.py

import argparse, hashlib, json, os, sys
from typing import Any, NamedTuple

# The checkout's `python` directory.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# Where the command line writes the vectors and their sidecars.
_VECTORS_PATH = os.path.join(os.path.dirname(_PYTHON_PATH), "build", "vectors")

# The longest line a vector's decoder reads with its CR, its writer's choice.
_LINE_MAX = 8192

# A message's most blob bytes, its writer's choice, small so splits run fast.
_BLOB_MAX = 8192

# The largest blob a vector's decoder keeps in memory, its writer's choice.
_OVERFLOW_BYTES = 1024

# The limits a decoder reads every vector with, written into each sidecar.
_LIMITS = {
    "line_max": _LINE_MAX,
    "blob_max": _BLOB_MAX,
    "overflow_bytes": _OVERFLOW_BYTES,
}

# The sizes of the digest inputs, at the edges of the hash's padding.
_DIGEST_SIZES = (55, 56, 64)

# The file of the digest vectors, beside the JSLB vectors.
_DIGESTS_NAME = "sha256.json"

# The file of the TypeScript test modules' digests, beside the JSLB vectors.
_TEST_DIGESTS_NAME = "test_digests.json"

# The 16 by 16 PNG image that two TypeScript test modules keep, 88 bytes.
_ARRIVAL_IMAGE = (
    b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52"
    b"\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91\x68"
    b"\x36\x00\x00\x00\x1f\x49\x44\x41\x54\x78\xda\x63\xf8\x8f\x04\x18"
    b"\x90\x00\x2e\x71\x86\x41\xa8\x61\x90\x3b\x8f\x28\x0d\xa3\xf1\x30"
    b"\x28\x34\x00\x00\xd9\x57\x7e\x90\xcd\x82\x3c\xb3\x00\x00\x00\x00"
    b"\x49\x45\x4e\x44\xae\x42\x60\x82"
)

# Each TypeScript test's inputs by name: bytes by hand, then a pattern's size.
_TEST_DIGESTS: dict[str, dict[str, tuple[bytes, int]]] = {
    "test_jslb": {
        "blob_half": (b"", 32768),
        "blob_largest": (b"", 65536),
        "empty": (b"", 0),
        "stream_long": (b"", 3072),
        "stream_over": (b"", 1025),
    },
    "test_media": {
        "abc": (b"abc", 0),
    },
    "test_substrate": {
        "absent": (b"absent", 0),
        "arrival_image": (_ARRIVAL_IMAGE, 0),
        "arrival_ref": (b"/castle_gatehouse/scene/arrival/1", 0),
        "castle_world": (b"castle_world", 0),
        "hello_wide": (b"hello \xe4\xb8\xad\xe6\x96\x87\xf0\x9f\x98\x80", 0),
        "map": (b"", 204800),
        "pattern_0": (b"", 0),
        "pattern_1": (b"", 1),
        "pattern_10": (b"", 10),
        "pattern_100": (b"", 100),
        "pattern_1000": (b"", 1000),
        "pattern_119": (b"", 119),
        "pattern_120": (b"", 120),
        "pattern_127": (b"", 127),
        "pattern_128": (b"", 128),
        "pattern_4": (b"", 4),
        "pattern_55": (b"", 55),
        "pattern_56": (b"", 56),
        "pattern_57": (b"", 57),
        "pattern_63": (b"", 63),
        "pattern_64": (b"", 64),
        "pattern_65": (b"", 65),
        "step_script": (
            b"// Advances the tide by args.hours in the region table"
            b" of the world.\n"
            b'const results = engine.store.sql_run("castle_world", [\n'
            b'  {sql: "UPDATE region SET tide = tide + ? WHERE name = ?",\n'
            b'    params: [args.hours, "castle_gatehouse"]},\n'
            b"]);\n"
            b'engine.log(1, "tide advanced by " + args.hours);\n'
            b"return {changes: results[0].changes};\n",
            0,
        ),
        "value_exact": (b"", 131072),
        "value_other": (b"\xff", 131072),
        "value_over": (b"", 131073),
    },
    "test_tools_browser": {
        "arrival_image": (_ARRIVAL_IMAGE, 0),
        "arrival_ref": (b"/castle_gatehouse/scene/arrival/1", 0),
        "byte_ff": (b"\xff", 0),
        "castle_world": (b"castle_world", 0),
        "document_lost": (b"a document whose cache file is lost", 0),
        "hyperposition_ref": (b"/metaverse/hyperposition/1", 0),
        "metaverse": (b"metaverse", 0),
        "note_a": (b"note/a", 0),
        "note_b": (b"note/b", 0),
        "script_stop": (b'throw new Error("stop");\n', 0),
        "step_script": (
            b"// Advances the tide by args.hours in the region table"
            b" of the world.\n"
            b'const results = engine.store.sql_run("castle_world", [\n'
            b'  {sql: "UPDATE region SET tide = tide + ? WHERE name = ?",\n'
            b'    params: [args.hours, "castle_gatehouse"]},\n'
            b"]);\n"
            b'engine.log("tide advanced by " + args.hours);\n'
            b"return {changes: results[0].changes};\n",
            0,
        ),
        "text_wide": (b"\xe4\xb8\xad\xe6\x96\x87\xf0\x9f\x98\x80 text", 0),
        "value_cached": (b"a value the cache holds", 0),
        "value_lost": (b"a value whose cache file is lost", 0),
    },
}

# Bytecode of `jslb` and of what it imports goes in `build`.
sys.pycache_prefix = os.path.join(
    os.path.dirname(_PYTHON_PATH), "build", "pycache"
)


# One message as encoded: the line's bytes ending in CR, then each blob's.
class _EncodedMessage(NamedTuple):
    line: bytes
    blobs: list[bytes]


# One error vector: the slug of its fault, the messages before it, its bytes.
class _ErrorVector(NamedTuple):
    name: str
    slug: str
    before: list[_EncodedMessage]
    fault: bytes


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
        vectors.append((name, [jslb.line_make(header, [blob], number=5)]))
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
    # Doubles past `2**53`, which both languages write as the same text.
    doubles = echo_make(
        [], large=1e300, low=-2.5e21, top=1.7976931348623157e308
    )
    vectors.append(("payload_doubles", [doubles]))
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
    # Two blobs whose sizes come to `blob_max`.
    half = _BLOB_MAX // 2
    at_max = echo_make([_pattern_make(half), _pattern_make(_BLOB_MAX - half)])
    vectors.append(("blobs_at_max", [at_max]))
    return [
        (name, [_pieces_split(list(jslb.line_encode(line))) for line in lines])
        for name, lines in vectors
    ]


# Returns each vector made by hand whose messages `jslb.py` encodes otherwise.
def _loose_vectors() -> list[tuple[str, list[_EncodedMessage]]]:
    line = b'{"0":{"t":"echo","b":1.0},"1":{"s":1.0}}\r'
    return [("integral_floats", [_EncodedMessage(line, [b"x"])])]


# Returns each error vector: its fault's slug, the messages before it, bytes.
def _error_vectors() -> list[_ErrorVector]:
    prefix = b'{"0":{"t":"echo"},"pad":"'
    suffix = b'"}\r'
    pad = b"a" * (_LINE_MAX + 1 - len(prefix) - len(suffix))
    # Two blobs whose sizes come to one byte past `blob_max`.
    half = _BLOB_MAX // 2
    over = b'{"0":{"t":"echo","b":2},"1":{"s":%d},"2":{"s":%d}}\r' % (
        half,
        _BLOB_MAX - half + 1,
    )
    # An `echo` line whose payload `n` is the number token given.
    number = b'{"0":{"t":"echo"},"n":%s}\r'
    faults = [
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
            "error_blobs_mismatch_boolean",
            "blobs_mismatch",
            b'{"0":{"t":"echo","b":true},"1":{"s":1}}\rx',
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
            "blobs_over",
            b'{"0":{"t":"echo","b":1},"1":{"s":%d}}\r' % (_BLOB_MAX + 1),
        ),
        ("error_blobs_over", "blobs_over", over),
        (
            "error_utf8_overlong",
            "line_not_utf8",
            b'{"0":{"t":"' + bytes.fromhex("c080") + b'"}}\r',
        ),
        (
            "error_utf8_surrogate",
            "line_not_utf8",
            b'{"0":{"t":"' + bytes.fromhex("eda080") + b'"}}\r',
        ),
        ("error_not_object", "line_not_object", b'[{"0":{"t":"echo"}}]\r'),
        ("error_header_not_object", "header_not_object", b'{"0":"echo"}\r'),
        (
            "error_header_not_object_blob",
            "header_not_object",
            b'{"0":{"t":"echo","b":1},"1":[]}\r',
        ),
        (
            "error_blob_data",
            "blob_data_field",
            b'{"0":{"t":"echo","b":1},"1":{"s":1,"d":"x"}}\rx',
        ),
        ("error_nan", "line_not_json", b'{"0":{"t":"echo"},"n":NaN}\r'),
        (
            "error_infinity",
            "line_not_json",
            b'{"0":{"t":"echo"},"n":Infinity}\r',
        ),
        ("error_number_overflow", "number_overflow", number % b"1e400"),
        (
            "error_number_overflow_negative",
            "number_overflow",
            number % b"-1e400",
        ),
        (
            "error_integer_above",
            "integer_refused",
            number % b"9007199254740993",
        ),
        (
            "error_integer_below",
            "integer_refused",
            number % b"-9007199254740993",
        ),
        (
            "error_integer_digits_310",
            "integer_refused",
            number % (b"1" + b"0" * 309),
        ),
        (
            "error_integer_digits_4301",
            "integer_refused",
            number % (b"1" + b"0" * 4300),
        ),
    ]
    vectors = [
        _ErrorVector(name, slug, [], data) for name, slug, data in faults
    ]
    before = _EncodedMessage(
        b'{"0":{"t":"echo","b":1},"1":{"s":1},"text":"before"}\r', [b"\r"]
    )
    vectors.append(
        _ErrorVector(
            "error_after_line", "no_header_zero", [before], b'{"t":"echo"}\r'
        )
    )
    return vectors


# Each digest vector by name: an input at an edge of the padding, its digest.
def _digest_vectors() -> dict[str, dict[str, str]]:
    vectors: dict[str, dict[str, str]] = {}
    for size in _DIGEST_SIZES:
        data = _pattern_make(size)
        vectors[f"sha256_{size}"] = {
            "data": data.hex(),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return vectors


# Each TypeScript test module's entries by name: an input, its digest.
def _test_digests() -> dict[str, dict[str, dict[str, str]]]:
    vectors: dict[str, dict[str, dict[str, str]]] = {}
    for module, inputs in _TEST_DIGESTS.items():
        entries: dict[str, dict[str, str]] = {}
        for name, (written, size) in inputs.items():
            data = written + _pattern_make(size)
            entries[name] = {
                "data": data.hex(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        vectors[module] = entries
    return vectors


# Writes a file of digest vectors into the directory, keys sorted.
def _digests_write(directory: str, name: str, vectors: dict[str, Any]) -> None:
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(vectors, indent=2, sort_keys=True) + "\n")


# What a decoder returns for a message: `d` in hex, `sha256` when streamed.
def _message_expected(message: _EncodedMessage) -> dict[str, Any]:
    expected: dict[str, Any] = json.loads(message.line[:-1].decode("utf-8"))
    _integral_set(expected["0"], ("b", "blobs"))
    for number, data in enumerate(message.blobs, 1):
        header: dict[str, Any] = expected[str(number)]
        _integral_set(header, ("s", "size"))
        header["d"] = data.hex()
        if len(data) > _OVERFLOW_BYTES:
            header["sha256"] = hashlib.sha256(data).hexdigest()
    return expected


# Makes each named field that holds an integral float an `int`, as decoders do.
def _integral_set(header: dict[str, Any], names: tuple[str, str]) -> None:
    for name in names:
        value: object = header.get(name)
        if type(value) is float and value.is_integer():
            header[name] = int(value)


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


# The messages a decoder returns and their renders, as a sidecar holds them.
def _messages_expected(messages: list[_EncodedMessage]) -> dict[str, Any]:
    expected = [_message_expected(message) for message in messages]
    render = [
        _message_render(item, len(message.blobs))
        for item, message in zip(expected, messages, strict=True)
    ]
    return {"messages": expected, "render": render}


# The bytes of the messages, each line followed by its blobs.
def _messages_join(messages: list[_EncodedMessage]) -> bytes:
    return b"".join(
        message.line + b"".join(message.blobs) for message in messages
    )


# Writes a vector's bytes and its sidecar into the directory.
def _vector_write(
    directory: str, name: str, data: bytes, sidecar: dict[str, Any]
) -> None:
    with open(os.path.join(directory, name + ".jslb"), "wb") as file:
        file.write(data)
    path = os.path.join(directory, name + ".json")
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(sidecar, indent=2) + "\n")


# Writes the vectors, sidecars and digest vectors to the emptied directory.
def vectors_write(directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    for stale in os.listdir(directory):
        os.remove(os.path.join(directory, stale))
    made = ((True, _success_vectors()), (False, _loose_vectors()))
    for canonical, vectors in made:
        for name, messages in vectors:
            sidecar: dict[str, Any] = {
                **_messages_expected(messages),
                "canonical": canonical,
                "limits": _LIMITS,
            }
            _vector_write(directory, name, _messages_join(messages), sidecar)
    for vector in _error_vectors():
        sidecar = {
            "error": vector.slug,
            **_messages_expected(vector.before),
            "limits": _LIMITS,
        }
        data = _messages_join(vector.before) + vector.fault
        _vector_write(directory, vector.name, data, sidecar)
    _digests_write(directory, _DIGESTS_NAME, _digest_vectors())
    _digests_write(directory, _TEST_DIGESTS_NAME, _test_digests())


# Writes each vector, its sidecar and the digest vectors into `build/vectors`.
def main() -> None:
    argparse.ArgumentParser(
        description="Write the JSLB vectors, their sidecars and the SHA-256"
        " digest vectors into build/vectors/, removing what an earlier run"
        " left there."
    ).parse_args()
    vectors_write(_VECTORS_PATH)


if __name__ == "__main__":
    main()
