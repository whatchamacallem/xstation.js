# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `tap.line` through the dispatcher: the TAP lines of a browser test
# run appended to its file line for line, the two languages kept apart, the
# directory made when it is absent, each line on disk the moment it is
# handled, and a language other than python or typescript refused. The
# scratch directories go under `build/`.

import dispatch, engine_tap, jslb, os, tempfile, unittest, unittest.mock
from collections.abc import Callable
from i18n import i18n
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The TAP lines of a run of two modules, in the shape the runner writes.
_RUN_LINES = (
    "TAP version 14",
    "1..2",
    "    1..2",
    "    ok 1 - test_one",
    "    ok 2 - test_two",
    "ok 1 - test_first",
    "    1..1",
    "    ok 1 - test_one",
    "ok 2 - test_second",
)

# The dotted name of the handler table that the tests patch.
_HANDLERS_TARGET = "dispatch._HANDLERS"

# The dotted name of the root that the tests patch.
_ROOT_TARGET = "engine_tap._STATE.root"

# The dotted name of the `open` that the handler calls, which a test patches.
_OPEN_TARGET = "engine_tap.open"

# The bytes a write cut short reports, a count its writer chose.
_SHORT_BYTES = 1

# Text with a character of two bytes and one of three bytes in `UTF-8`.
_WIDE_TEXT = "ok 1 - caf" + chr(0xE9) + " " + chr(0x4E2D)


# Builds a line with no blobs: the type and the payload.
def _line_make(name: str, **payload: Any) -> jslb.Object:
    return jslb.line_make(jslb.header_make(name), [], **payload)


# Returns the path of the TAP file of a language in a root.
def _tap_path(root: str, language: str) -> str:
    return os.path.join(root, "tap", language + ".tap")


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# Gives each test an empty handler table, no registration and a scratch root.
class IsolatedCase(unittest.TestCase):
    # Patches the table and the state, makes a scratch root in `build/`.
    def setUp(self) -> None:
        table = unittest.mock.patch.dict(_HANDLERS_TARGET, {}, clear=True)
        state = unittest.mock.patch(_ROOT_TARGET, None)
        for patcher in (table, state):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the lines appended to the files.
class TestAppend(IsolatedCase):
    # A run's lines replay into one file, line for line, and no other.
    def test_run_replay(self) -> None:
        engine_tap.handlers_register(self.root)
        for text in _RUN_LINES:
            line = _line_make("tap.line", language="typescript", text=text)
            self.assertIsNone(dispatch.line_dispatch(line))
        expected = "".join(text + "\n" for text in _RUN_LINES)
        path = _tap_path(self.root, "typescript")
        self.assertEqual(_file_read(path), expected.encode("utf-8"))
        self.assertEqual(os.listdir(os.path.dirname(path)), ["typescript.tap"])

    # Each line is in the file as soon as it is handled.
    def test_lines_visible(self) -> None:
        engine_tap.handlers_register(self.root)
        path = _tap_path(self.root, "python")
        expected = b""
        for text in ("TAP version 14", "1..1", "ok 1 - test_a"):
            line = _line_make("tap.line", language="python", text=text)
            dispatch.line_dispatch(line)
            expected += text.encode("utf-8") + b"\n"
            self.assertEqual(_file_read(path), expected)

    # The two languages go to two files.
    def test_languages_apart(self) -> None:
        engine_tap.handlers_register(self.root)
        for language in ("python", "typescript", "python"):
            line = _line_make("tap.line", language=language, text=language)
            dispatch.line_dispatch(line)
        python = _tap_path(self.root, "python")
        typescript = _tap_path(self.root, "typescript")
        self.assertEqual(_file_read(python), b"python\npython\n")
        self.assertEqual(_file_read(typescript), b"typescript\n")

    # The directory is made when it is absent.
    def test_directory_made(self) -> None:
        engine_tap.handlers_register(self.root)
        directory = os.path.join(self.root, "tap")
        self.assertFalse(os.path.exists(directory))
        line = _line_make("tap.line", language="python", text="x")
        dispatch.line_dispatch(line)
        self.assertTrue(os.path.isdir(directory))

    # A file that exists is appended to and keeps its lines.
    def test_file_appended(self) -> None:
        engine_tap.handlers_register(self.root)
        path = _tap_path(self.root, "python")
        os.makedirs(os.path.dirname(path))
        with open(path, "wb") as file:
            file.write(b"old\n")
        line = _line_make("tap.line", language="python", text="new")
        dispatch.line_dispatch(line)
        self.assertEqual(_file_read(path), b"old\nnew\n")

    # The text is written as `UTF-8` with the newline after it, and no other.
    def test_text_encoded(self) -> None:
        engine_tap.handlers_register(self.root)
        for text in (_WIDE_TEXT, "", "a\nb"):
            line = _line_make("tap.line", language="python", text=text)
            dispatch.line_dispatch(line)
        expected = _WIDE_TEXT.encode("utf-8") + b"\n\na\nb\n"
        path = _tap_path(self.root, "python")
        self.assertEqual(_file_read(path), expected)

    # The file is opened unbuffered, and a write cut short raises.
    def test_write_short(self) -> None:
        engine_tap.handlers_register(self.root)
        opened = unittest.mock.mock_open()
        opened.return_value.write.return_value = _SHORT_BYTES
        line = _line_make("tap.line", language="python", text="ok")
        data = b"ok\n"
        path = _tap_path(self.root, "python")
        message = i18n("engine_tap.write_short", _SHORT_BYTES, len(data), path)
        with unittest.mock.patch(_OPEN_TARGET, opened, create=True):
            self.raise_check(
                OSError, message, lambda: dispatch.line_dispatch(line)
            )
        opened.assert_called_once_with(path, "ab", buffering=0)
        opened.return_value.write.assert_called_once_with(data)


# Tests what the handler refuses.
class TestRefuse(IsolatedCase):
    # A language other than python or typescript raises and writes nothing.
    def test_language_unknown(self) -> None:
        engine_tap.handlers_register(self.root)
        for language in ("rust", "", "Python", "../python"):
            with self.subTest(language=language):
                line = _line_make("tap.line", language=language, text="x")
                self.raise_check(
                    ValueError,
                    i18n("engine_tap.language_unknown", language),
                    lambda: dispatch.line_dispatch(line),
                )
                self.assertEqual(os.listdir(self.root), [])

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _line_make("tap.line")
        self.raise_check(
            RuntimeError,
            i18n("engine_tap.not_registered"),
            lambda: engine_tap.tap_line(line, language="python", text="x"),
        )

    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_tap.handlers_register(self.root)
        self.raise_check(
            ValueError,
            i18n("dispatch.handler_twice", "tap.line", 0),
            lambda: engine_tap.handlers_register(self.root),
        )
