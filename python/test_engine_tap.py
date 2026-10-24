# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `tap.line`, its handler recorded at registration and called as the
# dispatcher calls it on lines of the gold: the TAP lines of a browser test
# run appended to the TypeScript file line for line, the directory made when
# it is absent, each line on disk the moment it is handled, and a language
# other than typescript refused, python among them. Then `error_take`: the
# browser's cascade logged in its order, outermost first, as the calls on a
# recorder of `verbose.log` show against the gold's texts, and the bail out
# line appended to the TypeScript stream with the line breaks of its message
# replaced, read back from the file. The scratch directories go under
# `build/`.

import engine_tap, harness, os, re, tempfile, unittest, unittest.mock
from collections.abc import Callable
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

# The dotted name of the root that the tests patch.
_ROOT_TARGET = "engine_tap._STATE.root"

# The dotted name of the `open` that the handler calls, which a test patches.
_OPEN_TARGET = "engine_tap.open"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_tap"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The one language whose stream crosses the wire.
_LANGUAGE = "typescript"

# Languages the handler refuses, each with the case of its gold text.
_LANGUAGES_REFUSED = (
    ("python", "python"),
    ("rust", "rust"),
    ("", "empty"),
    ("TypeScript", "capital"),
    ("../typescript", "path"),
)

# The bytes a write cut short reports, a count its writer chose.
_SHORT_BYTES = 1

# Text with a character of two bytes and one of three bytes in `UTF-8`.
_WIDE_TEXT = "ok 1 - caf" + chr(0xE9) + " " + chr(0x4E2D)

# A cascade of the browser below its latest failure: two causes, nested.
_CAUSE: dict[str, object] = {
    "message": "inner",
    "stack": "Error: inner\n    at b",
    "cause": {"message": "first", "stack": "Error: first\n    at c"},
}

# The latest failure's message, with each kind of line break in it.
_MESSAGE = "boom\nnext\r\nlast"

# The latest failure's stack.
_STACK = "Error: boom\n    at a"

# The bail out line of `_MESSAGE`, each line break a space.
_BAIL_LINE = "Bail out! boom next  last"


# A copy of a value of this module's gold, its number keys made `int`.
def _gold_value(name: str) -> Any:
    return _keys_number(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A copy of a JSON value with each number key an `int`, at every depth.
def _keys_number(value: Any) -> Any:
    if isinstance(value, dict):
        made: dict[int | str, Any] = {}
        for key, item in value.items():
            number = _NUMBER_KEY.fullmatch(key) is not None
            made[int(key) if number else key] = _keys_number(item)
        return made
    if isinstance(value, list):
        return [_keys_number(item) for item in value]
    return value


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The gold `tap.line` of the TypeScript stream, with the text it carries.
def _tap_line(text: str) -> Any:
    line = _gold_value("lines.tap_line")
    line["text"] = text
    return line


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    payload = {
        key: value for key, value in line.items() if isinstance(key, str)
    }
    return fn(line, **payload)


# Returns the path of the TAP file of a language in a root.
def _tap_path(root: str, language: str) -> str:
    return os.path.join(root, "tap", language + ".tap")


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# Gives each test an empty state, a registration recorder and a scratch root.
class IsolatedCase(unittest.TestCase):
    # Patches the state and `dispatch.handler_register` through `engine_tap`.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        state = unittest.mock.patch(_ROOT_TARGET, None)
        register = unittest.mock.patch.object(
            engine_tap.dispatch, "handler_register", self.handler_record
        )
        for patcher in (state, register):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name

    # Records one registration in place of the dispatcher's table.
    def handler_record(
        self, name: str, version: int, fn: Callable[..., Any]
    ) -> None:
        self.handlers.append((name, version, fn))

    # Registers the handler on the scratch root, returns the one of `name`.
    def handler_get(self, name: str) -> Callable[..., Any]:
        engine_tap.handlers_register(self.root)
        (fn,) = [fn for kind, _, fn in self.handlers if kind == name]
        return fn

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the lines appended to the file.
class TestAppend(IsolatedCase):
    # A run's lines replay into one file, line for line, and no other.
    def test_run_replay(self) -> None:
        handler = self.handler_get("tap.line")
        for text in _RUN_LINES:
            self.assertIsNone(_handler_call(handler, _tap_line(text)))
        expected = "".join(text + "\n" for text in _RUN_LINES)
        path = _tap_path(self.root, _LANGUAGE)
        self.assertEqual(_file_read(path), expected.encode("utf-8"))
        self.assertEqual(os.listdir(os.path.dirname(path)), ["typescript.tap"])

    # Each line is in the file as soon as it is handled.
    def test_lines_visible(self) -> None:
        handler = self.handler_get("tap.line")
        path = _tap_path(self.root, _LANGUAGE)
        expected = b""
        for text in ("TAP version 14", "1..1", "ok 1 - test_a"):
            _handler_call(handler, _tap_line(text))
            expected += text.encode("utf-8") + b"\n"
            self.assertEqual(_file_read(path), expected)

    # The directory is made when it is absent.
    def test_directory_made(self) -> None:
        handler = self.handler_get("tap.line")
        directory = os.path.join(self.root, "tap")
        self.assertFalse(os.path.exists(directory))
        _handler_call(handler, _tap_line("x"))
        self.assertTrue(os.path.isdir(directory))

    # A file that exists is appended to and keeps its lines.
    def test_file_appended(self) -> None:
        handler = self.handler_get("tap.line")
        path = _tap_path(self.root, _LANGUAGE)
        os.makedirs(os.path.dirname(path))
        with open(path, "wb") as file:
            file.write(b"old\n")
        _handler_call(handler, _tap_line("new"))
        self.assertEqual(_file_read(path), b"old\nnew\n")

    # The text is written as `UTF-8` with the newline after it, and no other.
    def test_text_encoded(self) -> None:
        handler = self.handler_get("tap.line")
        for text in (_WIDE_TEXT, "", "a\nb"):
            _handler_call(handler, _tap_line(text))
        expected = _WIDE_TEXT.encode("utf-8") + b"\n\na\nb\n"
        path = _tap_path(self.root, _LANGUAGE)
        self.assertEqual(_file_read(path), expected)

    # The file is opened unbuffered, and a write cut short raises.
    def test_write_short(self) -> None:
        handler = self.handler_get("tap.line")
        opened = unittest.mock.mock_open()
        opened.return_value.write.return_value = _SHORT_BYTES
        line = _tap_line("ok")
        path = _tap_path(self.root, _LANGUAGE)
        message = _text_get("engine_tap_write_short_line")
        message = message.replace("{2}", path)
        with unittest.mock.patch(_OPEN_TARGET, opened, create=True):
            self.raise_check(
                OSError, message, lambda: _handler_call(handler, line)
            )
        opened.assert_called_once_with(path, "ab", buffering=0)
        opened.return_value.write.assert_called_once_with(b"ok\n")


# Tests the browser's failure taken by the server.
class TestErrorTake(IsolatedCase):
    # Records `verbose.log` through `engine_tap` until the test ends.
    def log_patch(self) -> list[str]:
        logged: list[str] = []
        patcher = unittest.mock.patch.object(
            engine_tap.verbose, "log", logged.append
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return logged

    # The message, the stack, then each cause outermost first, one call each.
    def test_cascade_logged(self) -> None:
        engine_tap.handlers_register(self.root)
        logged = self.log_patch()
        engine_tap.error_take(_MESSAGE, _STACK, _CAUSE)
        expected = [
            _text_get("engine_tap_browser_failed_breaks"),
            _STACK,
            _text_get("engine_tap_browser_cause_inner"),
            "Error: inner\n    at b",
            _text_get("engine_tap_browser_cause_first"),
            "Error: first\n    at c",
        ]
        self.assertEqual(logged, expected)

    # With no cause only the message and the stack are logged.
    def test_cause_absent(self) -> None:
        engine_tap.handlers_register(self.root)
        logged = self.log_patch()
        engine_tap.error_take("boom", _STACK, None)
        expected = [_text_get("engine_tap_browser_failed_boom"), _STACK]
        self.assertEqual(logged, expected)

    # The bail out ends the stream's file, its message on one line.
    def test_bail_appended(self) -> None:
        handler = self.handler_get("tap.line")
        self.log_patch()
        for text in _RUN_LINES[:4]:
            _handler_call(handler, _tap_line(text))
        engine_tap.error_take(_MESSAGE, _STACK, _CAUSE)
        lines = _RUN_LINES[:4] + (_BAIL_LINE,)
        expected = "".join(text + "\n" for text in lines)
        path = _tap_path(self.root, _LANGUAGE)
        self.assertEqual(_file_read(path), expected.encode("utf-8"))

    # Before any line of the stream, the bail out makes the file alone.
    def test_bail_first(self) -> None:
        engine_tap.handlers_register(self.root)
        self.log_patch()
        engine_tap.error_take("boom", _STACK, None)
        path = _tap_path(self.root, _LANGUAGE)
        self.assertEqual(_file_read(path), b"Bail out! boom\n")
        self.assertEqual(os.listdir(os.path.dirname(path)), ["typescript.tap"])

    # The bail out is written unbuffered, and a write cut short raises.
    def test_bail_short(self) -> None:
        engine_tap.handlers_register(self.root)
        self.log_patch()
        opened = unittest.mock.mock_open()
        opened.return_value.write.return_value = _SHORT_BYTES
        path = _tap_path(self.root, _LANGUAGE)
        message = _text_get("engine_tap_write_short_bail")
        message = message.replace("{2}", path)
        with unittest.mock.patch(_OPEN_TARGET, opened, create=True):
            self.raise_check(
                OSError,
                message,
                lambda: engine_tap.error_take("boom", _STACK, None),
            )
        opened.assert_called_once_with(path, "ab", buffering=0)
        opened.return_value.write.assert_called_once_with(b"Bail out! boom\n")

    # Called before the registration it logs the failure, then raises.
    def test_take_early(self) -> None:
        logged = self.log_patch()
        self.raise_check(
            RuntimeError,
            _text_get("engine_tap_not_registered"),
            lambda: engine_tap.error_take("boom", _STACK, None),
        )
        expected = [_text_get("engine_tap_browser_failed_boom"), _STACK]
        self.assertEqual(logged, expected)


# Tests the registration and what the handler refuses.
class TestRefuse(IsolatedCase):
    # A language other than typescript raises and writes nothing.
    def test_language_unknown(self) -> None:
        handler = self.handler_get("tap.line")
        for language, case in _LANGUAGES_REFUSED:
            with self.subTest(language=language):
                line = _tap_line("x")
                line["language"] = language
                self.raise_check(
                    ValueError,
                    _text_get(f"engine_tap_language_unknown_{case}"),
                    lambda: _handler_call(handler, line),
                )
                self.assertEqual(os.listdir(self.root), [])

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _tap_line("x")
        self.raise_check(
            RuntimeError,
            _text_get("engine_tap_not_registered"),
            lambda: _handler_call(engine_tap.tap_line, line),
        )

    # The handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        engine_tap.handlers_register(self.root)
        expected = [("tap.line", 0, engine_tap.tap_line)]
        self.assertEqual(self.handlers, expected)
