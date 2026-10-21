# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of vectors_make: what vectors_write puts in a scratch directory under
# build/, each vector beside its sidecar, success and error vectors both, the
# directory made when it is missing, and a file an earlier run left removed.

import json, os, tempfile, unittest, vectors_make

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)


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

    # Each vector has its sidecar, nothing else is written, and both kinds are.
    def test_sidecars_paired(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            vectors_make.vectors_write(scratch)
            vectors = names_ending(scratch, ".jslb")
            sidecars = names_ending(scratch, ".json")
            count = len(os.listdir(scratch))
            errors: set[bool] = set()
            for name in sidecars:
                path = os.path.join(scratch, name + ".json")
                with open(path, encoding="utf-8") as file:
                    errors.add("error" in json.load(file))
        self.assertEqual(vectors, sidecars)
        self.assertEqual(count, 2 * len(vectors))
        self.assertEqual(errors, {False, True})

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
