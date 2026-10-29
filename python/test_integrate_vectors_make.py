# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests vectors_make with its real callee, jslb: vectors_write into a scratch
# directory under build/, then each sidecar's messages made lines again, each
# blob's d its bytes. Every vector's lines render with jslb as its sidecar
# says, and the jslb encoder writes a success vector's bytes for its lines,
# without the sha256 a decoder adds to a streamed blob, exactly when its
# sidecar calls it canonical, as the vector made by hand is not.

import jslb, json, os, tempfile, unittest, vectors_make
from typing import Any

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)


# Returns each vector's name, its bytes and its sidecar, as written.
def _vectors_read(directory: str) -> list[tuple[str, bytes, dict[str, Any]]]:
    names = sorted(
        name.removesuffix(".jslb")
        for name in os.listdir(directory)
        if name.endswith(".jslb")
    )
    vectors: list[tuple[str, bytes, dict[str, Any]]] = []
    for name in names:
        with open(os.path.join(directory, name + ".jslb"), "rb") as file:
            data = file.read()
        path = os.path.join(directory, name + ".json")
        with open(path, encoding="utf-8") as file:
            sidecar: dict[str, Any] = json.load(file)
        vectors.append((name, data, sidecar))
    return vectors


# Returns a sidecar's message as a line, each blob's `d` its bytes.
def _message_line(message: dict[str, Any]) -> jslb.Object:
    line: jslb.Object = jslb.json_decode(json.dumps(message))
    for number in range(1, jslb.field_get(line[0], "blobs") + 1):
        header: jslb.Object = line[number]
        header["d"] = bytes.fromhex(header["d"])
    return line


# Returns a line as it was sent, without the `sha256` a decoder adds to each
# blob over `overflow_bytes`.
def _line_sent(line: jslb.Object, overflow_bytes: int) -> jslb.Object:
    sent = jslb.Object(line)
    for number in range(1, jslb.field_get(line[0], "blobs") + 1):
        header: jslb.Object = line[number]
        if len(header["d"]) > overflow_bytes:
            sent[number] = jslb.Object(
                (name, value)
                for name, value in header.items()
                if name != "sha256"
            )
    return sent


# Returns the bytes the encoder writes for a line whose blobs hold bytes.
def _line_bytes(line: jslb.Object) -> bytes:
    data = bytearray()
    for piece in jslb.line_encode(line):
        if not isinstance(piece, bytes):
            raise TypeError("internal error")
        data += piece
    return bytes(data)


# The vectors `vectors_write` makes through jslb, checked against jslb.
class TestVectors(unittest.TestCase):
    # Writes the vectors into a scratch directory, removed when the test ends.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        vectors_make.vectors_write(scratch)
        self.vectors = _vectors_read(scratch)

    # Each vector's messages render with jslb as its sidecar's renders.
    def test_renders_same(self) -> None:
        self.assertTrue(self.vectors)
        for name, _, sidecar in self.vectors:
            lines = [_message_line(message) for message in sidecar["messages"]]
            renders = [jslb.line_render(line) for line in lines]
            self.assertEqual(renders, sidecar["render"], name)

    # A success vector is the jslb encoding of its sidecar's messages exactly
    # when its sidecar calls it canonical, success vectors of both kinds.
    def test_encoded_same(self) -> None:
        successes = [
            (name, data, sidecar)
            for name, data, sidecar in self.vectors
            if "error" not in sidecar
        ]
        kinds = {sidecar["canonical"] for _, _, sidecar in successes}
        self.assertEqual(kinds, {False, True})
        for name, data, sidecar in successes:
            limit: int = sidecar["limits"]["overflow_bytes"]
            lines = [_message_line(message) for message in sidecar["messages"]]
            encoded = b"".join(
                _line_bytes(_line_sent(line, limit)) for line in lines
            )
            self.assertEqual(encoded == data, sidecar["canonical"], name)
