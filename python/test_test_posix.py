# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of test_posix's check of the characters beyond ASCII, on files in a
# scratch directory under build/: a UTF-8 byte order mark is accepted at the
# start of a .ps1 or .psd1 file and refused anywhere else, each refusal
# compared with its message.

import os, tempfile, test_posix, unittest

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The `UTF-8` byte order mark.
_BOM = bytes.fromhex("efbbbf")


# Writes the bytes to the named file of the directory and returns its path.
def file_write(directory: str, name: str, data: bytes) -> str:
    path = os.path.join(directory, name)
    with open(path, "wb") as file:
        file.write(data)
    return path


# The message of a character the check refuses at a line and a column.
def refusal_text(path: str, line: int, column: int, character: str) -> str:
    return (
        f"{path}:{line}:{column}: U+{ord(character):04X} {character!r}"
        " isn't in _NON_ASCII_ALLOWED"
    )


# The byte order mark, accepted only at the start of a PowerShell file.
class TestByteOrder(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A PowerShell script and data file may start with the mark.
    def test_powershell_marked(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            for name in ("a.ps1", "a.psd1"):
                path = file_write(scratch, name, _BOM + b"# a\n")
                test_posix.non_ascii_check(path)

    # A PowerShell file without the mark passes as before.
    def test_powershell_plain(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "a.ps1", b"# a\n")
            test_posix.non_ascii_check(path)

    # The mark past the start of a PowerShell file is refused where it is.
    def test_mark_inside(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "a.ps1", _BOM + b"# a\n" + _BOM)
            with self.assertRaises(RuntimeError) as caught:
                test_posix.non_ascii_check(path)
        expected = refusal_text(path, 2, 1, chr(0xFEFF))
        self.assertEqual(caught.exception.args, (expected,))

    # A file of any other kind that starts with the mark is refused.
    def test_others_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            for name in ("a.py", "a.ts", "a.psm1"):
                path = file_write(scratch, name, _BOM + b"# a\n")
                with self.assertRaises(RuntimeError) as caught:
                    test_posix.non_ascii_check(path)
                expected = refusal_text(path, 1, 1, chr(0xFEFF))
                self.assertEqual(caught.exception.args, (expected,), name)

    # Columns of the first line count from past the mark.
    def test_column_after(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            block = chr(0x2588)
            text = "# " + block + "\n"
            path = file_write(scratch, "a.ps1", _BOM + text.encode("utf-8"))
            with self.assertRaises(RuntimeError) as caught:
                test_posix.non_ascii_check(path)
        expected = refusal_text(path, 1, 3, block)
        self.assertEqual(caught.exception.args, (expected,))
