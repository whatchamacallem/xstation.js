# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of vectors_make: what vectors_write puts in a scratch directory under
# build/, each vector beside its sidecar, success and error vectors both, the
# directory made when it is missing, a file an earlier run left removed, the
# two vectors at the edge of blob_max, the six number vectors, the digest
# vectors, inputs of 55, 56 and 64 bytes each beside its SHA-256 digest, and
# the TypeScript test modules' digests, filed under the names of the blocks
# that read them, each input in lowercase hex beside its SHA-256 digest.

import hashlib, json, os, tempfile, unittest, vectors_make
from typing import Any

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The file of the digest vectors, which the TypeScript check reads by name.
_DIGESTS_NAME = "sha256.json"

# The digest vectors by name, and the size of each one's input.
_DIGEST_INPUTS = {"sha256_55": 55, "sha256_56": 56, "sha256_64": 64}

# The file of the TypeScript test modules' digests, read by name.
_TEST_DIGESTS_NAME = "test_digests.json"

# The TypeScript blocks that read those digests, each under its own name.
_DIGEST_BLOCKS = (
    "test_jslb_decode",
    "test_media",
    "test_substrate_store",
    "test_tools_browser",
)

# The number vectors by name, each with the slug of its fault and its token.
_NUMBER_VECTORS = {
    "error_number_overflow": ("number_overflow", "1e400"),
    "error_number_overflow_negative": ("number_overflow", "-1e400"),
    "error_integer_above": ("integer_refused", "9007199254740993"),
    "error_integer_below": ("integer_refused", "-9007199254740993"),
    "error_integer_digits_310": ("integer_refused", "1" + "0" * 309),
    "error_integer_digits_4301": ("integer_refused", "1" + "0" * 4300),
}


# Returns the names in the directory that end in the suffix, without it.
def names_ending(directory: str, suffix: str) -> list[str]:
    return sorted(
        name.removesuffix(suffix)
        for name in os.listdir(directory)
        if name.endswith(suffix)
    )


# The vectors and sidecars that `vectors_write` puts in a directory.
class TestVectorsWrite(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # Vectors pair with sidecars, both kinds, the two digest files the others.
    def test_sidecars_paired(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            vectors_make.vectors_write(scratch)
            vectors = names_ending(scratch, ".jslb")
            sidecars = names_ending(scratch, ".json")
            sidecars.remove(_DIGESTS_NAME.removesuffix(".json"))
            sidecars.remove(_TEST_DIGESTS_NAME.removesuffix(".json"))
            count = len(os.listdir(scratch))
            errors: set[bool] = set()
            for name in sidecars:
                path = os.path.join(scratch, name + ".json")
                with open(path, encoding="utf-8") as file:
                    errors.add("error" in json.load(file))
        self.assertEqual(vectors, sidecars)
        self.assertEqual(count, 2 * len(vectors) + 2)
        self.assertEqual(errors, {False, True})

    # Each input has its size and its digest, both in lowercase hex.
    def test_digests_written(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            vectors_make.vectors_write(scratch)
            path = os.path.join(scratch, _DIGESTS_NAME)
            with open(path, encoding="utf-8") as file:
                digests: dict[str, dict[str, str]] = json.load(file)
        self.assertEqual(list(digests), list(_DIGEST_INPUTS))
        for name, size in _DIGEST_INPUTS.items():
            vector = digests[name]
            self.assertEqual(sorted(vector), ["data", "sha256"], name)
            data = bytes.fromhex(vector["data"])
            self.assertEqual(len(data), size, name)
            self.assertEqual(vector["data"], data.hex(), name)
            self.assertEqual(
                vector["sha256"], hashlib.sha256(data).hexdigest(), name
            )

    # Each block has entries, an input in lowercase hex beside its digest.
    def test_modules_written(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            vectors_make.vectors_write(scratch)
            path = os.path.join(scratch, _TEST_DIGESTS_NAME)
            with open(path, encoding="utf-8") as file:
                digests: dict[str, dict[str, dict[str, str]]] = json.load(file)
        self.assertEqual(sorted(digests), list(_DIGEST_BLOCKS))
        for module, entries in digests.items():
            self.assertTrue(entries, module)
            for name, entry in entries.items():
                self.assertEqual(sorted(entry), ["data", "sha256"], name)
                data = bytes.fromhex(entry["data"])
                self.assertEqual(entry["data"], data.hex(), name)
                digest = hashlib.sha256(data).hexdigest()
                self.assertEqual(entry["sha256"], digest, name)
                self.assertEqual(len(entry["sha256"]), 64, name)

    # Each number vector is the line of its token alone, within `line_max`.
    def test_numbers_written(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            vectors_make.vectors_write(scratch)
            for name, (slug, token) in _NUMBER_VECTORS.items():
                with open(os.path.join(scratch, name + ".jslb"), "rb") as file:
                    data = file.read()
                path = os.path.join(scratch, name + ".json")
                with open(path, encoding="utf-8") as file:
                    sidecar: dict[str, Any] = json.load(file)
                line = b'{"0":{"t":"echo"},"n":%s}\r' % token.encode()
                self.assertEqual(data, line, name)
                self.assertEqual(sidecar["error"], slug, name)
                self.assertEqual(sidecar["messages"], [], name)
                line_max: int = sidecar["limits"]["line_max"]
                self.assertLessEqual(len(data), line_max, name)

    # A directory that does not exist yet is made and filled.
    def test_directory_made(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            directory = os.path.join(scratch, "vectors")
            vectors_make.vectors_write(directory)
            self.assertTrue(names_ending(directory, ".jslb"))

    # A file that an earlier run left in the directory is removed.
    def test_stale_removed(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            stale = os.path.join(scratch, "stale_vector.jslb")
            with open(stale, "wb") as file:
                file.write(b'{"t":"echo"}\r')
            vectors_make.vectors_write(scratch)
            self.assertFalse(os.path.exists(stale))

    # Blobs of `blob_max` in all make a success vector, one byte more a fault.
    def test_window_edge(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            vectors_make.vectors_write(scratch)
            path = os.path.join(scratch, "blobs_at_max.json")
            with open(path, encoding="utf-8") as file:
                sidecar: dict[str, Any] = json.load(file)
            path = os.path.join(scratch, "error_blobs_over.jslb")
            with open(path, "rb") as file:
                over: dict[str, Any] = json.loads(file.read().split(b"\r")[0])
        limits: dict[str, int] = sidecar["limits"]
        self.assertEqual(
            sorted(limits), ["blob_max", "line_max", "overflow_bytes"]
        )
        (message,) = sidecar["messages"]
        at_max = message["1"]["s"] + message["2"]["s"]
        self.assertEqual(at_max, limits["blob_max"])
        self.assertEqual(over["1"]["s"] + over["2"]["s"], at_max + 1)
