# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of third_party_fetch: `file_fetch` against file URLs of a scratch
# directory under build/, into the real third_party/ under names no pin
# uses. Each file a test puts there is removed when the test ends.

import hashlib, os, pathlib, tempfile, third_party_fetch, unittest

# The checkout's top directory.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The directory the fetched files go to.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")

# The start of every name a test fetches, which no pinned name has.
_NAME_START = "test_third_party_fetch_"


# Tests of `file_fetch` with a source file in scratch and the real target.
class TestFetch(unittest.TestCase):
    # Makes the scratch directory that holds the source file.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.source_path = os.path.join(scratch, "source")

    # Writes the bytes to the source file and returns its file URL.
    def source_write(self, data: bytes) -> str:
        with open(self.source_path, "wb") as file:
            file.write(data)
        return pathlib.Path(self.source_path).as_uri()

    # The path of the name in `third_party/`, where no file may be yet.
    def target_find(self, name: str) -> str:
        path = os.path.join(_THIRD_PARTY_PATH, name)
        self.assertFalse(os.path.exists(path), path)
        return path

    # Writes the bytes to a new file in `third_party/`, removed at the end.
    def target_write(self, name: str, data: bytes) -> str:
        path = self.target_find(name)
        with open(path, "wb") as file:
            file.write(data)
        self.addCleanup(os.remove, path)
        return path

    # An existing file with another digest is replaced by the fetched bytes.
    def test_existing_replaced(self) -> None:
        data = b"new bytes"
        name = _NAME_START + "old.bin"
        path = self.target_write(name, b"old bytes")
        url = self.source_write(data)
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(url, digest, name)
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # An existing file with the right digest is returned without a fetch.
    def test_existing_reused(self) -> None:
        data = b"kept bytes"
        name = _NAME_START + "kept.bin"
        path = self.target_write(name, data)
        missing = pathlib.Path(self.source_path).as_uri()
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(missing, digest, name)
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # A good digest writes the bytes into place and returns the path.
    def test_good_digest(self) -> None:
        data = b"good bytes"
        name = _NAME_START + "good.bin"
        path = self.target_find(name)
        url = self.source_write(data)
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(url, digest, name)
        self.addCleanup(os.remove, path)
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # A digest that is not 64 lowercase hex characters raises naming the pin.
    def test_malformed_digest(self) -> None:
        data = b"bytes"
        name = _NAME_START + "bad.bin"
        path = self.target_find(name)
        url = self.source_write(data)
        good = hashlib.sha256(data).hexdigest()
        malformed = (
            "",
            good[:63],
            good + "0",
            good + "\n",
            "A" * 64,
            "g" * 64,
        )
        for digest in malformed:
            with self.assertRaises(ValueError, msg=repr(digest)) as context:
                third_party_fetch.file_fetch(url, digest, name)
            self.assertIn(name, str(context.exception))
        self.assertFalse(os.path.exists(path))

    # A wrong digest raises naming both digests and leaves no file.
    def test_wrong_digest(self) -> None:
        name = _NAME_START + "wrong.bin"
        path = self.target_find(name)
        actual = hashlib.sha256(b"actual bytes").hexdigest()
        wanted = hashlib.sha256(b"wanted bytes").hexdigest()
        url = self.source_write(b"actual bytes")
        with self.assertRaises(ValueError) as context:
            third_party_fetch.file_fetch(url, wanted, name)
        self.assertIn(actual, str(context.exception))
        self.assertIn(wanted, str(context.exception))
        self.assertFalse(os.path.exists(path))
