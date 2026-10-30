# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `tap.line` and `error_take` in forked children, each registered on
# a scratch root in `build/` with the real dispatcher, so the root and the
# handler never reach another test. The handler is called as the dispatcher
# calls it on lines of the gold: the TAP lines of a browser test run
# appended to the TypeScript file line for line, the directory made when it
# is absent, each line on disk the moment it is handled, a language other
# than typescript refused, python among them, and a write that the limit of
# the file size cuts short refused, which only an unbuffered write shows.
# Then `error_take`, on the root's real log: the browser's cascade logged in
# its order, outermost first, read back from `_verbose` against the gold's
# texts, and the bail out line appended to the TypeScript stream with the
# line breaks of its message replaced, read back from the file. The
# registration is read from the dispatcher, which refuses a second one of
# the type. Each child writes how its work ended to a file, or to stderr
# when that write fails, then kills itself.

import contextlib, engine_tap, functools, harness, json, os, re, resource
import signal, sqlite3, sys, tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_tap"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

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

# TypeScript file size before a write cut short, chosen above any log write.
_FILL_BYTES: int = harness.gold_get(f"{_GOLD_ID}.fill_bytes")

# The bytes a write cut short writes: the limit is this far past the fill.
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

# The lines the ring of a child's log holds, as the checkout sets it.
_RING: int = harness.setting_get("verbose_ring")

# The file of the root's log.
_LOG_FILE = "_verbose.sqlite"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"

# The file in the scratch directory that a child writes how it ended to.
_ENDING_NAME = "ending.json"


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


# Makes the root's TypeScript file `_FILL_BYTES` long and returns its path.
def _fill_make(root: str) -> str:
    path = _tap_path(root, _LANGUAGE)
    os.makedirs(os.path.dirname(path))
    with open(path, "xb") as file:
        file.truncate(_FILL_BYTES)
    return path


# The thread and text of each line of the root's log, in order.
def _log_read(root: str) -> list[tuple[str, str]]:
    path = os.path.join(root, _LOG_FILE)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        rows: list[tuple[str, str]] = connection.execute(_LOG_QUERY).fetchall()
    return rows


# The work of a child: registers on the root, then handles each text's line.
def _lines_handle(root: str, texts: tuple[str, ...]) -> list[Any]:
    engine_tap.handlers_register(root)
    return [
        _handler_call(engine_tap.tap_line, _tap_line(text)) for text in texts
    ]


# The work of a child: handles each text's line, reading the file after each.
def _lines_watch(root: str, texts: tuple[str, ...]) -> list[str]:
    engine_tap.handlers_register(root)
    path = _tap_path(root, _LANGUAGE)
    seen: list[str] = []
    for text in texts:
        _handler_call(engine_tap.tap_line, _tap_line(text))
        seen.append(_file_read(path).decode("utf-8"))
    return seen


# The work of a child: registers, then handles a line of the language.
def _language_handle(root: str, language: str) -> Any:
    engine_tap.handlers_register(root)
    line = _tap_line("x")
    line["language"] = language
    return _handler_call(engine_tap.tap_line, line)


# In a child: opens the log, registers, handles the texts, takes the failure.
def _failure_take(
    root: str,
    texts: tuple[str, ...],
    message: str,
    cause: dict[str, object] | None,
) -> None:
    engine_tap.verbose.log_open(root, _RING)
    engine_tap.handlers_register(root)
    for text in texts:
        _handler_call(engine_tap.tap_line, _tap_line(text))
    engine_tap.error_take(message, _STACK, cause)


# The work of a child: opens the log, then takes a failure before registering.
def _failure_early(root: str) -> None:
    engine_tap.verbose.log_open(root, _RING)
    engine_tap.error_take("boom", _STACK, None)


# The work of a child: registers, then registers the handler's type again.
def _register_twice(root: str) -> None:
    engine_tap.handlers_register(root)
    engine_tap.dispatch.handler_register("tap.line", 0, engine_tap.tap_line)


# Runs the work, files capped past the fill, `SIGXFSZ` ignored, then uncaps.
def _limited_run(work: Callable[[], object]) -> object:
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    limit = _FILL_BYTES + _SHORT_BYTES
    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, hard))
    try:
        return work()
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, (soft, hard))


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(work: Callable[[], object], path: str) -> None:
    try:
        try:
            ending: dict[str, object] = {"returned": work()}
        except BaseException as error:
            ending = {
                "raised": [type(error).__name__, str(error)],
                "trace": traceback.format_exc(),
            }
        text = json.dumps(ending)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
    except BaseException:
        # The parent finds no ending, so the failure goes to stderr.
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a scratch root in `build/` and runs its work in children.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the empty root in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)

    # Runs the work in a forked child and returns how it ended.
    def child_run(self, work: Callable[[], object]) -> dict[str, Any]:
        path = os.path.join(self.scratch, _ENDING_NAME)
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child_end(work, path)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending: dict[str, Any] = json.load(file)
        os.remove(path)
        return ending

    # Runs the work in a child and returns what it returned.
    def child_value(self, work: Callable[[], object]) -> Any:
        ending = self.child_run(work)
        if "raised" in ending:
            self.fail(ending["trace"])
        return ending["returned"]

    # Runs the work in a child and checks the type and the text it raised.
    def child_raise(
        self,
        work: Callable[[], object],
        kind: type[BaseException],
        message: str,
    ) -> None:
        ending = self.child_run(work)
        if "returned" in ending:
            self.fail(f"nothing was raised: {ending['returned']!r}")
        expected = [kind.__name__, message]
        self.assertEqual(ending["raised"], expected, ending["trace"])


# Tests the lines appended to the file.
class TestAppend(ScratchCase):
    # A run's lines replay into one file, line for line, and no other.
    def test_run_replay(self) -> None:
        work = functools.partial(_lines_handle, self.root, _RUN_LINES)
        self.assertEqual(self.child_value(work), [None] * len(_RUN_LINES))
        expected = "".join(text + "\n" for text in _RUN_LINES)
        path = _tap_path(self.root, _LANGUAGE)
        self.assertEqual(_file_read(path), expected.encode("utf-8"))
        self.assertEqual(os.listdir(os.path.dirname(path)), ["typescript.tap"])

    # Each line is in the file as soon as it is handled.
    def test_lines_visible(self) -> None:
        texts = ("TAP version 14", "1..1", "ok 1 - test_a")
        work = functools.partial(_lines_watch, self.root, texts)
        expected = [
            "".join(text + "\n" for text in texts[:count])
            for count in range(1, len(texts) + 1)
        ]
        self.assertEqual(self.child_value(work), expected)

    # The directory is made when it is absent.
    def test_directory_made(self) -> None:
        directory = os.path.join(self.root, "tap")
        self.assertFalse(os.path.exists(directory))
        self.child_value(functools.partial(_lines_handle, self.root, ("x",)))
        self.assertTrue(os.path.isdir(directory))

    # A file that exists is appended to and keeps its lines.
    def test_file_appended(self) -> None:
        path = _tap_path(self.root, _LANGUAGE)
        os.makedirs(os.path.dirname(path))
        with open(path, "wb") as file:
            file.write(b"old\n")
        self.child_value(functools.partial(_lines_handle, self.root, ("new",)))
        self.assertEqual(_file_read(path), b"old\nnew\n")

    # The text is written as `UTF-8` with the newline after it, and no other.
    def test_text_encoded(self) -> None:
        texts = (_WIDE_TEXT, "", "a\nb")
        self.child_value(functools.partial(_lines_handle, self.root, texts))
        expected = _WIDE_TEXT.encode("utf-8") + b"\n\na\nb\n"
        path = _tap_path(self.root, _LANGUAGE)
        self.assertEqual(_file_read(path), expected)

    # The line is one unbuffered write, so a write cut short raises.
    def test_write_short(self) -> None:
        path = _fill_make(self.root)
        message = _text_get("engine_tap_write_short_line")
        message = message.replace("{2}", path)
        work = functools.partial(_lines_handle, self.root, ("ok",))
        limited = functools.partial(_limited_run, work)
        self.child_raise(limited, OSError, message)
        self.assertEqual(_file_read(path)[_FILL_BYTES:], b"o")


# Tests the browser's failure taken by the server.
class TestErrorTake(ScratchCase):
    # The message, the stack, then each cause outermost first, one line each.
    def test_cascade_logged(self) -> None:
        work = functools.partial(
            _failure_take, self.root, (), _MESSAGE, _CAUSE
        )
        self.assertIsNone(self.child_value(work))
        texts = [
            _text_get("engine_tap_browser_failed_breaks"),
            _STACK,
            _text_get("engine_tap_browser_cause_inner"),
            "Error: inner\n    at b",
            _text_get("engine_tap_browser_cause_first"),
            "Error: first\n    at c",
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # With no cause only the message and the stack are logged.
    def test_cause_absent(self) -> None:
        work = functools.partial(_failure_take, self.root, (), "boom", None)
        self.child_value(work)
        texts = [_text_get("engine_tap_browser_failed_boom"), _STACK]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # The bail out ends the stream's file, its message on one line.
    def test_bail_appended(self) -> None:
        texts = _RUN_LINES[:4]
        work = functools.partial(
            _failure_take, self.root, texts, _MESSAGE, _CAUSE
        )
        self.child_value(work)
        expected = "".join(text + "\n" for text in texts + (_BAIL_LINE,))
        path = _tap_path(self.root, _LANGUAGE)
        self.assertEqual(_file_read(path), expected.encode("utf-8"))

    # Before any line of the stream, the bail out makes the file alone.
    def test_bail_first(self) -> None:
        work = functools.partial(_failure_take, self.root, (), "boom", None)
        self.child_value(work)
        path = _tap_path(self.root, _LANGUAGE)
        self.assertEqual(_file_read(path), b"Bail out! boom\n")
        self.assertEqual(os.listdir(os.path.dirname(path)), ["typescript.tap"])

    # The bail out is one unbuffered write, so a write cut short raises.
    def test_bail_short(self) -> None:
        path = _fill_make(self.root)
        message = _text_get("engine_tap_write_short_bail")
        message = message.replace("{2}", path)
        work = functools.partial(_failure_take, self.root, (), "boom", None)
        limited = functools.partial(_limited_run, work)
        self.child_raise(limited, OSError, message)
        self.assertEqual(_file_read(path)[_FILL_BYTES:], b"B")
        texts = [_text_get("engine_tap_browser_failed_boom"), _STACK]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # Called before the registration it logs the failure, then raises.
    def test_take_early(self) -> None:
        self.child_raise(
            functools.partial(_failure_early, self.root),
            RuntimeError,
            _text_get("engine_tap_not_registered"),
        )
        texts = [_text_get("engine_tap_browser_failed_boom"), _STACK]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)


# Tests the registration and what the handler refuses.
class TestRefuse(ScratchCase):
    # A language other than typescript raises and writes nothing.
    def test_language_unknown(self) -> None:
        for language, case in _LANGUAGES_REFUSED:
            with self.subTest(language=language):
                self.child_raise(
                    functools.partial(_language_handle, self.root, language),
                    ValueError,
                    _text_get(f"engine_tap_language_unknown_{case}"),
                )
                self.assertEqual(os.listdir(self.root), [])

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        self.child_raise(
            functools.partial(
                _handler_call, engine_tap.tap_line, _tap_line("x")
            ),
            RuntimeError,
            _text_get("engine_tap_not_registered"),
        )

    # The handler is registered under its type at version 0, a repeat refused.
    def test_handlers_registered(self) -> None:
        self.child_raise(
            functools.partial(_register_twice, self.root),
            ValueError,
            _text_get("dispatch_handler_twice"),
        )
