# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of third_party_fetch: `file_fetch` against file URLs and a scratch
# directory under build/, and the table of pinned files.

import hashlib, os, pathlib, tempfile, third_party_fetch, unittest.mock
from typing import Any

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The extension of the archive that each pinned name and URL must end in.
_EXTENSIONS = {
    "sqlite-wasm-3460100.zip": ".zip",
    "ttyd-1.7.7.tar.gz": ".tar.gz",
    "xterm-5.5.0.tgz": ".tgz",
}


# Tests of `file_fetch` with a source file and a target directory in scratch.
class TestFetch(unittest.TestCase):
    # Makes the scratch directory and points the module's directory into it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.source_path = os.path.join(scratch, "source")
        self.target_path = os.path.join(scratch, "third_party")
        self.enterContext(
            unittest.mock.patch.object(
                third_party_fetch, "_THIRD_PARTY_PATH", self.target_path
            )
        )

    # Writes the bytes to the source file and returns its file URL.
    def source_write(self, data: bytes) -> str:
        with open(self.source_path, "wb") as file:
            file.write(data)
        return pathlib.Path(self.source_path).as_uri()

    # Writes the bytes to a file in a new target directory, returns its path.
    def target_write(self, name: str, data: bytes) -> str:
        os.makedirs(self.target_path)
        path = os.path.join(self.target_path, name)
        with open(path, "wb") as file:
            file.write(data)
        return path

    # An existing file with another digest is replaced by the fetched bytes.
    def test_existing_replaced(self) -> None:
        data = b"new bytes"
        path = self.target_write("old.bin", b"old bytes")
        url = self.source_write(data)
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(url, digest, "old.bin")
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # An existing file with the right digest is returned without a fetch.
    def test_existing_reused(self) -> None:
        data = b"kept bytes"
        path = self.target_write("kept.bin", data)
        missing = pathlib.Path(self.source_path).as_uri()
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(missing, digest, "kept.bin")
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # A good digest makes the directory, writes the bytes, returns the path.
    def test_good_digest(self) -> None:
        data = b"good bytes"
        url = self.source_write(data)
        digest = hashlib.sha256(data).hexdigest()
        self.assertFalse(os.path.exists(self.target_path))
        path = third_party_fetch.file_fetch(url, digest, "good.bin")
        self.assertEqual(path, os.path.join(self.target_path, "good.bin"))
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # A digest that is not 64 lowercase hex characters raises naming the pin.
    def test_malformed_digest(self) -> None:
        data = b"bytes"
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
                third_party_fetch.file_fetch(url, digest, "bad.bin")
            self.assertIn("bad.bin", str(context.exception))
        self.assertFalse(
            os.path.exists(os.path.join(self.target_path, "bad.bin"))
        )

    # A wrong digest raises naming both digests and leaves no file.
    def test_wrong_digest(self) -> None:
        actual = hashlib.sha256(b"actual bytes").hexdigest()
        wanted = hashlib.sha256(b"wanted bytes").hexdigest()
        url = self.source_write(b"actual bytes")
        with self.assertRaises(ValueError) as context:
            third_party_fetch.file_fetch(url, wanted, "wrong.bin")
        self.assertIn(actual, str(context.exception))
        self.assertIn(wanted, str(context.exception))
        self.assertFalse(
            os.path.exists(os.path.join(self.target_path, "wrong.bin"))
        )


# Tests of the table of pinned files.
class TestPins(unittest.TestCase):
    # Returns the module's private table, which is read by name.
    def pins_get(self) -> tuple[Any, ...]:
        pins: tuple[Any, ...] = getattr(third_party_fetch, "_PINS")
        return pins

    # Every pin's name and URL end in the extension of its archive.
    def test_pin_extensions(self) -> None:
        for pin in self.pins_get():
            extension = _EXTENSIONS[pin.name]
            self.assertTrue(pin.name.endswith(extension), pin.name)
            self.assertTrue(pin.url.endswith(extension), pin.url)

    # The table has the three names that other modules read, once each.
    def test_pin_names(self) -> None:
        names = sorted(pin.name for pin in self.pins_get())
        self.assertEqual(names, sorted(_EXTENSIONS))
