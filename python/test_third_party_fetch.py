# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of third_party_fetch: `file_fetch` against file URLs and a scratch
# directory under build/, and the table of pinned files, which holds the
# two archives the page reads as the gold names them and the ttyd archive
# the setting powershell.ttyd_archive names.

import harness, hashlib, os, pathlib, re, tempfile, third_party_fetch
import unittest.mock
from typing import cast

# The id of the gold's list of the archives `page_build` reads.
_ARCHIVES_ID = "python.test_third_party_fetch.archives_read"

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The setting that names the ttyd archive the install script unpacks.
_ARCHIVE_SETTING = "powershell.ttyd_archive"

# The directory of the pinned files, which starts the archive's setting.
_THIRD_PARTY_PREFIX = "third_party/"

# A pinned name: words joined by hyphens, a hyphen, the version, the extension.
_NAME_PATTERN = re.compile(
    r"[a-z]+(?:-[a-z]+)*-([0-9]+(?:\.[0-9]+)*)(\.tar\.gz|\.tgz|\.zip)"
)


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
    def pins_get(self) -> tuple[tuple[str, str, str], ...]:
        pins: tuple[tuple[str, str, str], ...] = getattr(
            third_party_fetch, "_PINS"
        )
        return pins

    # The two archives `page_build` reads, by the gold, are names of the table.
    def test_archives_pinned(self) -> None:
        names = [name for name, _url, _sha256 in self.pins_get()]
        archives: list[str] = harness.gold_get(_ARCHIVES_ID)
        self.assertEqual(len(archives), 2)
        for archive in archives:
            self.assertIn(archive, names)

    # The ttyd archive that `xsjs_install.ps1` unpacks is a name of the table.
    def test_install_pinned(self) -> None:
        path: str = harness.setting_get(_ARCHIVE_SETTING)
        self.assertTrue(path.startswith(_THIRD_PARTY_PREFIX), path)
        names = [name for name, _url, _sha256 in self.pins_get()]
        self.assertIn(path.removeprefix(_THIRD_PARTY_PREFIX), names)

    # No two pins share a name, as each name is a file in `third_party/`.
    def test_pin_names(self) -> None:
        names = [name for name, _url, _sha256 in self.pins_get()]
        self.assertEqual(len(names), len(set(names)))

    # The version in each name occurs in its URL, which ends in its extension.
    def test_pin_versions(self) -> None:
        for name, url, _sha256 in self.pins_get():
            found = _NAME_PATTERN.fullmatch(name)
            self.assertIsNotNone(found, name)
            version, extension = cast(re.Match[str], found).group(1, 2)
            self.assertIn(version, url)
            self.assertTrue(url.endswith(extension), url)
