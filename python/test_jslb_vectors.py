# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of jslb on the vectors that vectors_make.py writes into build/vectors
# before any test here reads them, each read whole, by single bytes and split
# at every offset with its sidecar's limits: each success vector, and the
# bytes it encodes to, decode to its sidecar, the canonical ones encoding to
# the same bytes, and each error vector gives its lines, then its fault, its
# text compared with the gold record of test_jslb.

import jslb, json, os, test_jslb, vectors_make
from collections.abc import Iterator
from typing import Any

# The checkout's build directory, which holds the vectors.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The vectors and their sidecars, as `vectors_make.py` writes them.
_VECTORS_PATH = os.path.join(_BUILD_PATH, "vectors")


# Writes the vectors anew before any test here reads them.
def setUpModule() -> None:
    vectors_make.vectors_write(_VECTORS_PATH)


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


# Reads each vector `vectors_make.py` wrote, whole, by bytes and split.
class TestVectors(test_jslb.ScratchCase):
    # Returns a new decoder with a sidecar's limits, streaming into the sink.
    def sidecar_decoder(self, sidecar: dict[str, Any]) -> jslb.LineDecoder:
        limits: dict[str, int] = sidecar["limits"]
        return jslb.LineDecoder(
            limits["line_max"],
            limits["blob_max"],
            limits["overflow_bytes"],
            self.sink.path_make,
        )

    # Returns each error vector's slug and its message under the limits.
    def errors_expected(
        self, limits: dict[str, int]
    ) -> dict[str, tuple[str, str]]:
        blob_max = limits["blob_max"]
        over = (
            "blobs_over",
            test_jslb.text_get(
                "jslb_blobs_over_vector", blob_max + 1, blob_max
            ),
        )
        start = self.decode_reason(bytes.fromhex("c080"))
        continuation = self.decode_reason(bytes.fromhex("eda080"))
        header = ("no_header_zero", test_jslb.text_get("jslb_no_header_zero"))
        size = ("bad_size", test_jslb.text_get("jslb_bad_size"))
        forms = ("both_name_forms", test_jslb.text_get("jslb_both_name_forms"))
        typed = ("no_type", test_jslb.text_get("jslb_no_type"))
        return {
            "error_after_line": header,
            "error_bad_size_boolean": size,
            "error_bad_size_fraction": size,
            "error_bad_size_missing": size,
            "error_bad_size_negative": size,
            "error_bad_size_string": size,
            "error_blob_data": (
                "blob_data_field",
                test_jslb.text_get("jslb_blob_data_field"),
            ),
            "error_blob_gap": (
                "blob_gap",
                test_jslb.text_get("jslb_blob_gap_middle"),
            ),
            "error_blob_gap_first": (
                "blob_gap",
                test_jslb.text_get("jslb_blob_gap_first"),
            ),
            "error_blob_over_max": over,
            "error_blobs_mismatch": (
                "blobs_mismatch",
                test_jslb.text_get("jslb_blobs_mismatch_two"),
            ),
            "error_blobs_mismatch_boolean": (
                "blobs_mismatch",
                test_jslb.text_get("jslb_blobs_mismatch_true"),
            ),
            "error_blobs_mismatch_extra": (
                "blobs_mismatch",
                test_jslb.text_get("jslb_blobs_mismatch_zero"),
            ),
            "error_blobs_over": over,
            "error_both_name_forms": forms,
            "error_both_name_forms_blob": forms,
            "error_header_not_object": (
                "header_not_object",
                test_jslb.text_get("jslb_header_not_object_line"),
            ),
            "error_header_not_object_blob": (
                "header_not_object",
                test_jslb.text_get("jslb_header_not_object_blob"),
            ),
            "error_infinity": (
                "line_not_json",
                test_jslb.text_get("jslb_line_not_json_infinity"),
            ),
            "error_integer_above": (
                "integer_refused",
                test_jslb.text_get("jslb_integer_refused_above"),
            ),
            "error_integer_below": (
                "integer_refused",
                test_jslb.text_get("jslb_integer_refused_below"),
            ),
            "error_integer_digits_310": (
                "integer_refused",
                test_jslb.text_get(
                    "jslb_integer_refused_long", "1" + "0" * 309
                ),
            ),
            "error_integer_digits_4301": (
                "integer_refused",
                test_jslb.text_get(
                    "jslb_integer_refused_long", "1" + "0" * 4300
                ),
            ),
            "error_line_over_max": (
                "line_over_max",
                test_jslb.text_get(
                    "jslb_line_over_max_vector", limits["line_max"]
                ),
            ),
            "error_nan": (
                "line_not_json",
                test_jslb.text_get("jslb_line_not_json_nan"),
            ),
            "error_no_header_zero": header,
            "error_no_type": typed,
            "error_no_type_string": typed,
            "error_not_object": (
                "line_not_object",
                test_jslb.text_get("jslb_line_not_object"),
            ),
            "error_number_overflow": (
                "number_overflow",
                test_jslb.text_get("jslb_number_overflow_positive"),
            ),
            "error_number_overflow_negative": (
                "number_overflow",
                test_jslb.text_get("jslb_number_overflow_negative"),
            ),
            "error_payload_digit_key": (
                "payload_digit_key",
                test_jslb.text_get("jslb_payload_digit_key_01"),
            ),
            "error_unknown_line_field": (
                "unknown_line_field",
                test_jslb.text_get("jslb_unknown_line_field_x"),
            ),
            "error_utf8_overlong": (
                "line_not_utf8",
                test_jslb.text_get("jslb_line_not_utf8", start),
            ),
            "error_utf8_surrogate": (
                "line_not_utf8",
                test_jslb.text_get("jslb_line_not_utf8", continuation),
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
                test_jslb.pieces_join(jslb.line_encode(_line_sent(line)))
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
