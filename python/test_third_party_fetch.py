# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of third_party_fetch: `file_fetch` against file URLs of a scratch
# directory under build/, into the real third_party/ in a library directory
# no pin uses, which git ignores as it ignores the pins. Each file a test
# puts there is removed when the test ends, and the directory with it. Then
# `pins_fetch` on the pins already in place, the gold's paths and digests.

import harness, hashlib, os, pathlib, tempfile, third_party_fetch, unittest

# The checkout's top directory.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The directory the fetched files go to.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")

# The library directory of every name a test fetches, which no pin uses.
_LIBRARY_NAME = "test_third_party_fetch"

# The gold's pins, each its path in `third_party/` and its sha256, in order.
_PINS_ID = "python.test_third_party_fetch.pins"


# Returns the name in the scratch library of the file name.
def name_make(file_name: str) -> str:
    return _LIBRARY_NAME + "/" + file_name


# Tests of `file_fetch` with a source file in scratch and the real target.
class TestFetch(unittest.TestCase):
    # Makes the scratch directory that holds the source file.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.source_path = os.path.join(scratch, "source")
        self.library_path = os.path.join(_THIRD_PARTY_PATH, _LIBRARY_NAME)
        self.assertFalse(os.path.exists(self.library_path), self.library_path)

    # Writes the bytes to the source file and returns its file URL.
    def source_write(self, data: bytes) -> str:
        with open(self.source_path, "wb") as file:
            file.write(data)
        return pathlib.Path(self.source_path).as_uri()

    # Removes the file and the scratch library when the test ends.
    def removal_add(self, path: str) -> None:
        self.addCleanup(os.rmdir, self.library_path)
        self.addCleanup(os.remove, path)

    # Writes the bytes to a new file of the scratch library, removed after.
    def target_write(self, name: str, data: bytes) -> str:
        path = os.path.join(_THIRD_PARTY_PATH, name)
        os.mkdir(self.library_path)
        with open(path, "wb") as file:
            file.write(data)
        self.removal_add(path)
        return path

    # An existing file with another digest is replaced by the fetched bytes.
    def test_existing_replaced(self) -> None:
        data = b"new bytes"
        name = name_make("old.bin")
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
        name = name_make("kept.bin")
        path = self.target_write(name, data)
        missing = pathlib.Path(self.source_path).as_uri()
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(missing, digest, name)
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # A good digest makes the library, writes the bytes and returns the path.
    def test_good_digest(self) -> None:
        data = b"good bytes"
        name = name_make("good.bin")
        path = os.path.join(_THIRD_PARTY_PATH, name)
        url = self.source_write(data)
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(url, digest, name)
        self.removal_add(path)
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # A digest that is not 64 lowercase hex characters raises naming the pin.
    def test_malformed_digest(self) -> None:
        data = b"bytes"
        name = name_make("bad.bin")
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
        self.assertFalse(os.path.exists(self.library_path))

    # A wrong digest raises naming both digests and leaves no file.
    def test_wrong_digest(self) -> None:
        name = name_make("wrong.bin")
        actual = hashlib.sha256(b"actual bytes").hexdigest()
        wanted = hashlib.sha256(b"wanted bytes").hexdigest()
        url = self.source_write(b"actual bytes")
        with self.assertRaises(ValueError) as context:
            third_party_fetch.file_fetch(url, wanted, name)
        self.assertIn(actual, str(context.exception))
        self.assertIn(wanted, str(context.exception))
        self.assertFalse(os.path.exists(self.library_path))


# Tests of `pins_fetch` on the pins, which the run fetched before its blocks.
class TestPins(unittest.TestCase):
    # Each pin is at its path with its digest, and a second fetch keeps it.
    def test_pins_placed(self) -> None:
        pins: list[list[str]] = harness.gold_get(_PINS_ID)
        paths = [os.path.join(_THIRD_PARTY_PATH, name) for name, _ in pins]
        self.assertEqual(third_party_fetch.pins_fetch(), paths)
        for path, (_, digest) in zip(paths, pins):
            with open(path, "rb") as file:
                actual = hashlib.file_digest(file, "sha256").hexdigest()
            self.assertEqual(actual, digest, path)
        stats = [os.stat(path) for path in paths]
        self.assertEqual(third_party_fetch.pins_fetch(), paths)
        for path, stat in zip(paths, stats):
            again = os.stat(path)
            self.assertEqual(
                (again.st_ino, again.st_mtime_ns),
                (stat.st_ino, stat.st_mtime_ns),
                path,
            )
