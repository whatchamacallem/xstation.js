# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of test_posix's check of the characters beyond ASCII and of its
# PowerShell comment lexer, on files in a scratch directory under build/ and
# on text: a UTF-8 byte order mark is refused at the start of a file read as
# utf-8 and passed there in one read as utf-8-sig, and PowerShell comments
# are found past its strings and here strings, each refusal compared with its
# message.

import os, tempfile, test_posix, unittest

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The `UTF-8` byte order mark.
_BOM = bytes.fromhex("efbbbf")

# The name the lexer tests give their text.
_TEXT_PATH = "a.ps1"


# Returns the comments the PowerShell lexer finds in the text.
def comments_list(text: str) -> list[test_posix.Comment]:
    return test_posix.comments_find(_TEXT_PATH, text, "powershell")


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


# The byte order mark at the start, refused in `utf-8`, passed in `utf-8-sig`.
class TestByteOrder(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A Python or TypeScript file read as `utf-8` is refused at the mark.
    def test_others_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            for name in ("a.py", "a.ts"):
                path = file_write(scratch, name, _BOM + b"# a\n")
                with self.assertRaises(RuntimeError) as caught:
                    test_posix.non_ascii_check(path, "utf-8")
                expected = refusal_text(path, 1, 1, chr(0xFEFF))
                self.assertEqual(caught.exception.args, (expected,), name)

    # A PowerShell file read as `utf-8-sig` passes the mark at its start.
    def test_powershell_marked(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            for name in ("a.ps1", "a.psd1"):
                path = file_write(scratch, name, _BOM + b"# a\n")
                test_posix.non_ascii_check(path, "utf-8-sig")

    # A PowerShell file without the mark passes too.
    def test_powershell_plain(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "a.ps1", b"# a\n")
            test_posix.non_ascii_check(path, "utf-8-sig")

    # A mark after the start is refused at its line and column.
    def test_mark_inside(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "a.ps1", b"# a\n" + _BOM + b"# b\n")
            with self.assertRaises(RuntimeError) as caught:
                test_posix.non_ascii_check(path, "utf-8-sig")
            expected = refusal_text(path, 2, 1, chr(0xFEFF))
            self.assertEqual(caught.exception.args, (expected,))

    # A refused character's column is counted after the mark.
    def test_column_after(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            data = _BOM + b"# " + chr(0x2588).encode() + b"\n"
            path = file_write(scratch, "a.ps1", data)
            with self.assertRaises(RuntimeError) as caught:
                test_posix.non_ascii_check(path, "utf-8-sig")
            expected = refusal_text(path, 1, 3, chr(0x2588))
            self.assertEqual(caught.exception.args, (expected,))


# The PowerShell comment lexer on text: what it finds, skips and refuses.
class TestPowershellLexer(unittest.TestCase):
    # A `#` after a space or at the start of a line begins a line comment.
    def test_line_comment(self) -> None:
        self.assertEqual(
            comments_list("$a = 1 # one\n# two\n"),
            [
                test_posix.Comment(7, 12, 1, 0),
                test_posix.Comment(13, 18, 1, 0),
            ],
        )

    # A `<#` comment runs to its `#>`.
    def test_block_comment(self) -> None:
        self.assertEqual(
            comments_list("<# a #>\nb\n"), [test_posix.Comment(0, 7, 2, 2)]
        )

    # Single and double quoted strings hide a `#`, past their escapes.
    def test_strings_skipped(self) -> None:
        text = "'#' \"#\" 'it''s # x' \"a`\" # b\"\n"
        self.assertEqual(comments_list(text), [])

    # A comment inside the `$( )` of a double quoted string is found.
    def test_subexpression_comment(self) -> None:
        self.assertEqual(
            comments_list('"$(1 # c\n)"\n'), [test_posix.Comment(5, 8, 1, 0)]
        )

    # Here strings hide a `#` to their closing line, an empty one too.
    def test_here_skipped(self) -> None:
        text = "@'\n# x\n'@\n@\"\n# y\n\"@\n@'\n'@\n"
        self.assertEqual(comments_list(text), [])

    # A `#` inside a word or after a backtick begins no comment.
    def test_word_hash(self) -> None:
        self.assertEqual(comments_list("Write-Output a#b `#c\n"), [])

    # Each unterminated string, subexpression and comment is refused.
    def test_unterminated_refused(self) -> None:
        needle = "\n'@"
        for text, expected in (
            ("'a\n", "a.ps1:1: unterminated string"),
            ('"a\n', "a.ps1:1: unterminated string"),
            ('"$(1\n', "a.ps1:2: unterminated"),
            ("<# a\n", "a.ps1:1: no '#>' ends this"),
            ("@'\na\n", f"a.ps1:1: no {needle!r} ends this"),
        ):
            with self.assertRaises(RuntimeError) as caught:
                comments_list(text)
            self.assertEqual(caught.exception.args, (expected,), text)


# The comment check of a PowerShell file, read as `utf-8-sig`.
class TestPowershellCheck(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A `<# #>` comment below the header is refused.
    def test_block_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            data = _BOM + b"# h\n\n<# b #>\n"
            path = file_write(scratch, "a.ps1", data)
            with self.assertRaises(RuntimeError) as caught:
                test_posix.comments_check(path, "utf-8-sig", "powershell")
            expected = (
                f"{path}:3: <# #> comment below the top of the file. Use #."
            )
            self.assertEqual(caught.exception.args, (expected,))

    # A header of two lines is found past the mark.
    def test_marked_header(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            data = _BOM + b"# h\n# i\n\n# b\n"
            path = file_write(scratch, "a.ps1", data)
            test_posix.comments_check(path, "utf-8-sig", "powershell")

    # A `<# #>` comment is allowed as the header.
    def test_header_block(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "a.ps1", b"<# h\nh #>\n\n# b\n")
            test_posix.comments_check(path, "utf-8-sig", "powershell")


# The lexer names that `comments_find` knows.
class TestLexerName(unittest.TestCase):
    # A name that no lexer has is refused.
    def test_name_refused(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            test_posix.comments_find("a.x", "", "cobol")
        expected = "a.x: no comment lexer named 'cobol'"
        self.assertEqual(caught.exception.args, (expected,))
