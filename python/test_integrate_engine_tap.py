# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests engine_tap with its real callees in forked children, each on a
# scratch root in `build/`: lines of the gold written as wire bytes, read by
# the real jslb decoder and served by the real dispatcher on the handler
# that `handlers_register` gave it. The TAP lines of a run appended in
# order; the type served at version 0 alone; a language refused through the
# dispatcher, nothing written; a `tap.line` sent as a request appended, then
# refused by the dispatcher for the reply it never gets; and the browser's
# `error` line read by the decoder, its cascade of decoded objects handed to
# `error_take` as the main loop hands it, logged in the root's real log and
# read back from `_verbose`, and the bail out line ending the TypeScript
# file. Each child writes how its work ended to a file, or to stderr when
# that write fails, then kills itself.

import contextlib, engine_tap, functools, harness, json, os, signal, sqlite3
import sys, tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any, NoReturn

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_engine_tap"

# The limits of the decoder, as the checkout sets them.
_LINE_MAX: int = harness.setting_get("line_max")
_BLOB_MAX: int = harness.setting_get("blob_max")
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# The lines the ring of a child's log holds, as the checkout sets it.
_RING: int = harness.setting_get("verbose_ring")

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

# The file of the root's log.
_LOG_FILE = "_verbose.sqlite"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"

# The file in the scratch directory that a child writes how it ended to.
_ENDING_NAME = "ending.json"


# A value of this module's gold as JSON holds it, which is not to be changed.
def _gold_raw(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The bytes of a line on the wire: its JSON text and the CR that ends it.
def _line_bytes(line: dict[str, Any]) -> bytes:
    text = json.dumps(line, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8") + b"\r"


# The bytes of a gold line.
def _gold_bytes(name: str) -> bytes:
    return _line_bytes(_gold_raw(f"lines.{name}"))


# The bytes of the gold `tap.line` of the TypeScript stream, with the text.
def _tap_bytes(text: str) -> bytes:
    return _line_bytes({**_gold_raw("lines.tap_line"), "text": text})


# Refuses a blob that streams: no line of these tests carries one.
def _sink_refuse(header: engine_tap.jslb.Object) -> NoReturn:
    raise AssertionError(f"a blob came that streams: {header}")


# The lines of the bytes, read by the real decoder with the checkout's limits.
def _lines_decode(data: bytes) -> list[engine_tap.jslb.Object]:
    decoder = engine_tap.jslb.LineDecoder(
        _LINE_MAX, _BLOB_MAX, _OVERFLOW_BYTES, _sink_refuse
    )
    return decoder.bytes_feed(data)


# Returns the path of the TypeScript TAP file in a root.
def _tap_path(root: str) -> str:
    return os.path.join(root, "tap", "typescript.tap")


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# The thread and text of each line of the root's log, in order.
def _log_read(root: str) -> list[tuple[str, str]]:
    path = os.path.join(root, _LOG_FILE)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        rows: list[tuple[str, str]] = connection.execute(_LOG_QUERY).fetchall()
    return rows


# The work of a child: registers on the root, then serves the bytes' lines.
def _lines_serve(root: str, data: bytes) -> list[object]:
    engine_tap.handlers_register(root)
    return [
        engine_tap.dispatch.line_dispatch(line) for line in _lines_decode(data)
    ]


# The work of a child: opens the root's log, registers, reads the browser's
# `error` line from the bytes and hands its cascade to `error_take`.
def _failure_serve(root: str, data: bytes) -> None:
    engine_tap.verbose.log_open(root, _RING)
    engine_tap.handlers_register(root)
    (line,) = _lines_decode(data)
    payload = engine_tap.jslb.payload_of(line)
    engine_tap.error_take(
        payload["message"], payload["stack"], payload["cause"]
    )


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


# Tests the `tap.line` lines served through the dispatcher.
class TestServe(ScratchCase):
    # A run's lines, pushed, are appended to the file in order, unanswered.
    def test_lines_served(self) -> None:
        data = b"".join(_tap_bytes(text) for text in _RUN_LINES)
        work = functools.partial(_lines_serve, self.root, data)
        self.assertEqual(self.child_value(work), [None] * len(_RUN_LINES))
        expected = "".join(text + "\n" for text in _RUN_LINES)
        path = _tap_path(self.root)
        self.assertEqual(_file_read(path), expected.encode("utf-8"))
        self.assertEqual(os.listdir(os.path.dirname(path)), ["typescript.tap"])

    # The type is served at version 0 alone: version 1 has no handler.
    def test_version_unknown(self) -> None:
        self.child_raise(
            functools.partial(
                _lines_serve, self.root, _gold_bytes("tap_version")
            ),
            LookupError,
            _text_get("dispatch_handler_unknown"),
        )
        self.assertEqual(os.listdir(self.root), [])

    # A language other than typescript is refused, and nothing is written.
    def test_language_refused(self) -> None:
        self.child_raise(
            functools.partial(
                _lines_serve, self.root, _gold_bytes("tap_python")
            ),
            ValueError,
            _text_get("engine_tap_language_unknown"),
        )
        self.assertEqual(os.listdir(self.root), [])

    # A `tap.line` sent as a request is appended, then the dispatcher
    # refuses it for the reply the handler never gives.
    def test_request_refused(self) -> None:
        self.child_raise(
            functools.partial(
                _lines_serve, self.root, _gold_bytes("tap_request")
            ),
            ValueError,
            _text_get("dispatch_request_unanswered"),
        )
        text = _gold_raw("lines.tap_request")["text"]
        path = _tap_path(self.root)
        self.assertEqual(_file_read(path), (text + "\n").encode("utf-8"))


# Tests the browser's `error` line read by the decoder and taken.
class TestFailure(ScratchCase):
    # The decoded cascade is logged outermost first, then the bail out ends
    # the TypeScript file.
    def test_failure_taken(self) -> None:
        work = functools.partial(
            _failure_serve, self.root, _gold_bytes("browser_error")
        )
        self.assertIsNone(self.child_value(work))
        error = _gold_raw("lines.browser_error")
        texts = [
            _text_get("engine_tap_browser_failed"),
            error["stack"],
            _text_get("engine_tap_browser_cause_first"),
            error["cause"]["stack"],
            _text_get("engine_tap_browser_cause_second"),
            error["cause"]["cause"]["stack"],
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)
        bail = _text_get("bail_out") + "\n"
        path = _tap_path(self.root)
        self.assertEqual(_file_read(path), bail.encode("utf-8"))
