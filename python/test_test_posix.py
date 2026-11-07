# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of test_posix's check of the characters beyond ASCII and of its
# PowerShell comment lexer, on files in a scratch directory under build/ and
# on text: a UTF-8 byte order mark is refused at the start of a file read as
# utf-8 and passed there in one read as utf-8-sig, the full block and the
# three shades of the install banner pass in either codec, and PowerShell
# comments are found past its strings and here strings, each refusal
# compared with its message. An HTML comment that is the formatter escape
# prettier-ignore passes the comment check, one with more words is refused.
# A header passes at the limit on its lines and is refused past it, as is a
# comment of two lines below it. The JavaScript, shell, HTML and CSS lexers are
# compared by the words of the comments they find and by their refusals. A
# synchronization token outside the exempt modules is refused with its message
# too, the audit's own check and its list of paths take what each test gives
# them, and bytes that are not UTF-8 are refused. No test reaches the formatter
# step or main, which call into api_match, category, page_build and reformat.

import os, tempfile, test_posix, unittest

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The `UTF-8` byte order mark.
_BOM = bytes.fromhex("efbbbf")

# The full block and the three shades of the install banner, allowed in all.
_BANNER_CHARACTERS = "".join(map(chr, (0x2588, 0x2591, 0x2592, 0x2593)))

# A block character beside them, which no file may hold.
_BLOCK_REFUSED = chr(0x2594)

# The lines a header may run to.
_HEADER_LIMIT = 20

# The name the lexer tests give their text.
_TEXT_PATH = "a.ps1"

# The name the tests of the other lexers give their text.
_LEXER_PATH = "a"


# Returns the comments the PowerShell lexer finds in the text.
def comments_list(text: str) -> list[test_posix.Comment]:
    return test_posix.comments_find(_TEXT_PATH, text, "powershell")


# Returns the words of each comment the named lexer finds in the text.
def comment_words(text: str, lexer: str) -> list[str]:
    return [
        text[comment.start + comment.opener : comment.end - comment.closer]
        for comment in test_posix.comments_find(_LEXER_PATH, text, lexer)
    ]


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
            data = _BOM + b"# " + _BLOCK_REFUSED.encode() + b"\n"
            path = file_write(scratch, "a.ps1", data)
            with self.assertRaises(RuntimeError) as caught:
                test_posix.non_ascii_check(path, "utf-8-sig")
            expected = refusal_text(path, 1, 3, _BLOCK_REFUSED)
            self.assertEqual(caught.exception.args, (expected,))


# The characters beyond ASCII that every file may hold, in either codec.
class TestAllowed(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # The full block and the three shades of the banner pass in every file.
    def test_banner_passed(self) -> None:
        data = ("# " + _BANNER_CHARACTERS + "\n").encode()
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            for name, encoding in (("a.py", "utf-8"), ("a.ps1", "utf-8-sig")):
                path = file_write(scratch, name, data)
                test_posix.non_ascii_check(path, encoding)


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


# Compares the refusals of a comment lexer with their messages.
class LexerCase(unittest.TestCase):
    # Has the named lexer refuse each text with the message beside it.
    def refusals_check(
        self, lexer: str, cases: tuple[tuple[str, str], ...]
    ) -> None:
        for text, expected in cases:
            with self.assertRaises(RuntimeError) as caught:
                test_posix.comments_find(_LEXER_PATH, text, lexer)
            self.assertEqual(caught.exception.args, (expected,), text)


# The JavaScript comment lexer on text: what it finds, skips and refuses.
class TestJavascriptLexer(LexerCase):
    # A `//` comment runs to the end of its line or of the text.
    def test_line_comment(self) -> None:
        self.assertEqual(
            comment_words("// a\nb // c", "javascript"), [" a", " c"]
        )

    # A `/*` comment runs over its lines to its `*/`.
    def test_block_comment(self) -> None:
        self.assertEqual(
            comment_words("/* a\nb */\n", "javascript"), [" a\nb "]
        )

    # Quoted strings hide a comment marker, past their escapes.
    def test_strings_skipped(self) -> None:
        text = '"// a\\"" \'/* b\'\n'
        self.assertEqual(comment_words(text, "javascript"), [])

    # A regular expression hides a slash in its escapes and its class.
    def test_regex_skipped(self) -> None:
        text = "a = /\\/[/]b/gi // c\n"
        self.assertEqual(comment_words(text, "javascript"), [" c"])

    # A slash after a word is a division, and opens nothing.
    def test_division_passed(self) -> None:
        self.assertEqual(comment_words("a / b // c\n", "javascript"), [" c"])

    # A template hides comment markers, but not in its `${ }` spans.
    def test_template_spans(self) -> None:
        text = "`// a${b /* c */}\\` // d` // e\n"
        self.assertEqual(comment_words(text, "javascript"), [" c ", " e"])

    # A brace pair inside a `${ }` span does not end the span.
    def test_braces_nested(self) -> None:
        text = "`${ {} /* a */ }`\n{ // b\n}\n"
        self.assertEqual(comment_words(text, "javascript"), [" a ", " b"])

    # Each unterminated literal, comment and span is refused.
    def test_unterminated_refused(self) -> None:
        self.refusals_check(
            "javascript",
            (
                ("'a\n", "a:1: unterminated string"),
                ("= /a\n", "a:1: unterminated regular expression"),
                ("`a\n", "a:1: unterminated template literal"),
                ("/* a\n", "a:1: no '*/' ends this"),
                ("`${a\n", "a:2: no closing brace"),
            ),
        )


# The shell comment lexer on text: what it finds, skips and refuses.
class TestShellLexer(LexerCase):
    # A `#` that starts a word begins a comment, one inside a word does not.
    def test_line_comment(self) -> None:
        text = "# a\nb # c\nd#e\n"
        self.assertEqual(comment_words(text, "shell"), [" a", " c"])

    # Quoted text and an escape hide a `#`.
    def test_strings_skipped(self) -> None:
        text = "'# a' \"# b\" \\# c\n"
        self.assertEqual(comment_words(text, "shell"), [])

    # A double quoted string holds code in its `$( )` alone.
    def test_quoted_parts(self) -> None:
        text = '"a\\" `# b` $(c # d\n) # e" # f\n'
        self.assertEqual(comment_words(text, "shell"), [" d", " f"])

    # A paren pair inside a `$( )` does not end it.
    def test_parens_nested(self) -> None:
        text = '"$((a) # b\n)"\n'
        self.assertEqual(comment_words(text, "shell"), [" b"])

    # A here string opens no here document, so the next line is code.
    def test_here_string(self) -> None:
        text = "a <<< b\n# c\n"
        self.assertEqual(comment_words(text, "shell"), [" c"])

    # A here document hides a `#` to its closing line.
    def test_heredoc_skipped(self) -> None:
        text = "a <<B # c\n# d\nB\n# e\n"
        self.assertEqual(comment_words(text, "shell"), [" c", " e"])

    # With `-` and a quoted word, tabs may come before the closing word.
    def test_heredoc_stripped(self) -> None:
        text = "a <<-'B'\n# c\n\tB\n# d\n"
        self.assertEqual(comment_words(text, "shell"), [" d"])

    # Two here documents begun on a line close in order.
    def test_heredocs_ordered(self) -> None:
        text = "a <<B <<C\n# d\nB\n# e\nC\n# f\n"
        self.assertEqual(comment_words(text, "shell"), [" f"])

    # Each unterminated quote, substitution and here document is refused.
    def test_unterminated_refused(self) -> None:
        self.refusals_check(
            "shell",
            (
                ("'a\n", 'a:1: no "\'" ends this'),
                ('"a\n', "a:1: unterminated string"),
                ('"$(a\n', "a:2: unterminated"),
                ("a <<B\nc\n", "a:1: no line ends the here document 'B'"),
                ("a <<B", "a:1: unterminated"),
            ),
        )


# The HTML comment lexer on text, with its script and style elements.
class TestHtmlLexer(LexerCase):
    # The comments of a script element come in order with the page's own.
    def test_script_comments(self) -> None:
        text = "<!-- a -->\n<script>\n// b\n</script>\n<!-- c -->\n"
        self.assertEqual(comment_words(text, "html"), [" a ", " b", " c "])

    # The comments of a style element are found past its strings.
    def test_style_comments(self) -> None:
        text = "<style>\n/* a */ b { c: '/* d'; }\n</style>\n"
        self.assertEqual(comment_words(text, "html"), [" a "])

    # An element's tags are found in either case.
    def test_tag_case(self) -> None:
        text = "<SCRIPT>// a\n</SCRIPT>\n"
        self.assertEqual(comment_words(text, "html"), [" a"])

    # A script or style element with no end tag is refused at its start.
    def test_tag_unclosed(self) -> None:
        self.refusals_check(
            "html",
            (
                ("\n<script>\n", "a:2: no end tag"),
                ("<style>\n", "a:1: no end tag"),
            ),
        )


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


# A formatter escape below the header, passed whole by the comment check.
class TestEscapeCheck(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A `prettier-ignore` comment passes though it holds a `-`.
    def test_escape_passed(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            data = b"<!-- h -->\n<p></p>\n<!-- prettier-ignore -->\n<p></p>\n"
            path = file_write(scratch, "a.html", data)
            test_posix.comments_check(path, "utf-8", "html")

    # A comment holding more than the escape is refused at its `-`.
    def test_escape_extended(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            data = b"<!-- h -->\n<p></p>\n<!-- prettier-ignore a -->\n"
            path = file_write(scratch, "a.html", data)
            with self.assertRaises(RuntimeError) as caught:
                test_posix.comments_check(path, "utf-8", "html")
            expected = (
                f"{path}:3: comment holds '-' outside _ENGLISH_PUNCT and code"
                " spans"
            )
            self.assertEqual(caught.exception.args, (expected,))


# The limit on the lines of a header, whatever comments make it up.
class TestHeaderLimit(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A header of line comments at the limit passes.
    def test_limit_passed(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            data = b"# h\n" * _HEADER_LIMIT + b"\na = 1\n"
            path = file_write(scratch, "a.py", data)
            test_posix.comments_check(path, "utf-8", "python")

    # A header of line comments past the limit is refused at its first line.
    def test_limit_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            data = b"# h\n" * (_HEADER_LIMIT + 1) + b"\na = 1\n"
            path = file_write(scratch, "a.py", data)
            with self.assertRaises(RuntimeError) as caught:
                test_posix.comments_check(path, "utf-8", "python")
            expected = f"{path}:1: header runs to line 21, past its 20 lines"
            self.assertEqual(caught.exception.args, (expected,))

    # A block comment header is counted by the lines it spans.
    def test_block_counted(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            data = b"<!--\n" + b"h\n" * _HEADER_LIMIT + b"-->\n<p></p>\n"
            path = file_write(scratch, "a.html", data)
            with self.assertRaises(RuntimeError) as caught:
                test_posix.comments_check(path, "utf-8", "html")
            expected = f"{path}:1: header runs to line 22, past its 20 lines"
            self.assertEqual(caught.exception.args, (expected,))

    # A doctype line before a header is not one of its lines.
    def test_doctype_uncounted(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            lines = b"h\n" * (_HEADER_LIMIT - 2)
            data = b"<!DOCTYPE html>\n<!--\n" + lines + b"-->\n<p></p>\n"
            path = file_write(scratch, "a.html", data)
            test_posix.comments_check(path, "utf-8", "html")


# The lexer names that `comments_find` knows.
class TestLexerName(unittest.TestCase):
    # A name that no lexer has is refused.
    def test_name_refused(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            test_posix.comments_find("a.x", "", "cobol")
        expected = "a.x: no comment lexer named 'cobol'"
        self.assertEqual(caught.exception.args, (expected,))


# The refusal of a synchronization token outside the exempt modules.
class TestAuditMessage(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A token outside the exempt modules is refused at its line.
    def test_token_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "a.ts", b"\nawait x;\n")
            with self.assertRaises(RuntimeError) as caught:
                test_posix.synchronization_check(path)
            expected = f"{path}:2: await outside _SYNCHRONIZATION_MODULES"
            self.assertEqual(caught.exception.args, (expected,))

    # The same token in an exempt module passes.
    def test_module_exempt(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "queue.ts", b"\nawait x;\n")
            test_posix.synchronization_check(path)


# The audit's check of itself, on the probes each test gives it.
class TestAuditProbe(unittest.TestCase):
    # A token it refuses and a literal it passes leave it silent.
    def test_probes_passed(self) -> None:
        test_posix.audit_probe(("await x;\n",), ("const s = 'await';\n",))

    # A probe that holds no token is named as one the audit misses.
    def test_token_missed(self) -> None:
        code = "const a = 1;\n"
        with self.assertRaises(RuntimeError) as caught:
            test_posix.audit_probe((code,), ())
        expected = f"the audit misses the token in {code!r}"
        self.assertEqual(caught.exception.args, (expected,))

    # A probe that must pass but holds a token is named with that token.
    def test_token_found(self) -> None:
        code = "await x;\n"
        with self.assertRaises(RuntimeError) as caught:
            test_posix.audit_probe((), (code,))
        expected = f"the audit finds 'await' in {code!r}"
        self.assertEqual(caught.exception.args, (expected,))


# The TypeScript files the audit reads under a top directory.
class TestTypescriptPaths(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # The `.ts` files of `ts/` come sorted, and no other file comes.
    def test_paths_sorted(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            directory = os.path.join(scratch, "ts")
            os.mkdir(directory)
            second = file_write(directory, "b.ts", b"")
            first = file_write(directory, "a.ts", b"")
            file_write(directory, "c.js", b"")
            paths = test_posix.typescript_paths(scratch)
            self.assertEqual(paths, [first, second])

    # A top directory that holds no such file is refused.
    def test_paths_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            with self.assertRaises(RuntimeError) as caught:
                test_posix.typescript_paths(scratch)
            expected = f"ts/*.ts matches no file under {scratch}"
            self.assertEqual(caught.exception.args, (expected,))


# The one line limit on a comment below the header.
class TestCommentLines(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # Comments on adjacent lines below the header are refused as one comment.
    def test_lines_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "a.py", b"# h\n\n# b\n# c\n")
            with self.assertRaises(RuntimeError) as caught:
                test_posix.comments_check(path, "utf-8", "python")
            expected = (
                f"{path}:3: comment below the header runs to line 4. Make it"
                " one line."
            )
            self.assertEqual(caught.exception.args, (expected,))


# Bytes the codec cannot read, refused with the decoder's words.
class TestBadBytes(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A byte that is not `UTF-8` is refused, the decoder's error its cause.
    def test_bytes_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = file_write(scratch, "a.py", b"\xff\n")
            with self.assertRaises(RuntimeError) as caught:
                test_posix.non_ascii_check(path, "utf-8")
            expected = (
                f"{path}: not UTF-8: 'utf-8' codec can't decode byte 0xff in"
                " position 0: invalid start byte"
            )
            self.assertEqual(caught.exception.args, (expected,))
            cause = caught.exception.__cause__
            self.assertIsInstance(cause, UnicodeDecodeError)
