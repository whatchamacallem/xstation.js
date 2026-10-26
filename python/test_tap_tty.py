# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests bootstrap.py run whole on a pty as ttyd runs it, unpatched, through
# tap_tty's EngineTty, with roots in build/ whose settings are the
# checkout's and whose test settings are the checkout's gold. On the stock
# main loop: the first line in either name form and its payload, the empty
# reply, pushes and a request served over the tty, the hangup that ends the
# engine with SIGHUP, a second engine refused by the lock, a wrong reply to
# tap.start refused, the page's error line ending the TypeScript stream,
# and a request no handler serves. On the echo main loop, a blob over
# overflow_bytes both ways. On the TAP suite server, tap_loop.py: a suite
# of this checkout relayed by suites_relay as a passing stream, its timings
# carried in the reply, and a suite the driver does not know refused by its
# exit code and its stderr, with no stream. The lines sent and expected,
# the texts and the suites run are this module's gold.

import harness, jslb, json, os, shutil, signal, tap_consumer, tap_tty
import tempfile, unittest
from typing import Any, NoReturn

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The checkout's `python` directory, which holds the main loop files.
_PYTHON_PATH = os.path.join(_ROOT_PATH, "python")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_tap_tty"

# A size chosen by its writer, small: a blob over it streams to the cache.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# A blob that streams both ways, over `_OVERFLOW_BYTES`.
_STREAMED_BYTES = bytes(
    index % 256 for index in range(_OVERFLOW_BYTES * 2 + 1)
)

# The directory of a root that holds the main loop files.
_LOOP_DIRECTORY = "main_loop"

# The echo main loop file.
_ECHO_NAME = "echo_loop.py"

# The TAP suite server's main loop file.
_SUITE_NAME = "tap_loop.py"

# The lock file of a root.
_LOCK_NAME = "engine.lock"

# The TAP file of the TypeScript stream in a root.
_TAP_FILE = os.path.join("tap", "typescript.tap")

# The fixed databases the stock main loop's prepare creates in a new root.
_FIXED_DBS = ("_settings", "_preferences", "_files", "metaverse")

# The exit code of a hangup, minus the number of the signal that ended it.
_HUNG_UP = -signal.SIGHUP

# The exit code of a failure.
_EXIT_FAILED = 1

# The exit code `argparse` gives a command line it refuses.
_EXIT_USAGE = 2


# A line of this module's gold.
def _line_get(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.lines.{name}")


# A text of this module's gold, each `{n}` replaced by the value at `n`.
def _text_get(name: str, *values: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    for number, value in enumerate(values):
        text = text.replace(f"{{{number}}}", value)
    return text


# The bytes of a gold line on the wire: its compact JSON text and a CR.
def _line_bytes(name: str) -> bytes:
    text = json.dumps(
        _line_get(name), ensure_ascii=False, separators=(",", ":")
    )
    return text.encode("utf-8") + b"\r"


# A line read back as JSON values, its integer keys strings, as the gold.
def _plain(line: jslb.Object) -> Any:
    return json.loads(json.dumps(line, ensure_ascii=False))


# Refuses a blob, as only the echo test takes one.
def _sink_refuse(header: jslb.Object) -> NoReturn:
    raise AssertionError(f"a blob came that streams: {header}")


# Writes a value as the JSON text of a file of the root.
def _json_write(root: str, name: str, value: object) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with open(os.path.join(root, name), "w", encoding="utf-8") as file:
        file.write(text)


# A root under `build/` and its scratch directory, with one main loop file.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory the root goes in.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.root = os.path.join(self.scratch, "root")

    # Makes the root with the settings, the gold and the main loop file.
    def root_make(self, debug: bool, loop: str | None) -> dict[str, Any]:
        values = harness.settings_copy()
        values["debug"] = debug
        os.makedirs(self.root)
        _json_write(self.root, "settings.json", values)
        _json_write(self.root, "test_settings.json", harness.gold_copy())
        if loop is not None:
            directory = os.path.join(self.root, _LOOP_DIRECTORY)
            os.makedirs(directory)
            shutil.copyfile(
                os.path.join(_PYTHON_PATH, loop), os.path.join(directory, loop)
            )
        return values

    # Runs the engine on the root, with the main loop file named if any.
    def engine_run(
        self, values: dict[str, Any], loop: str | None
    ) -> tap_tty.EngineTty:
        arguments = [] if loop is None else ["--main-loop", loop]
        engine = tap_tty.EngineTty(self.root, arguments, values, _sink_refuse)
        return self.enterContext(engine)

    # Reads the first line, checks it is the gold's, and answers it.
    def start_answer(self, engine: tap_tty.EngineTty, full: bool) -> Any:
        first = _plain(engine.line_read())
        form = "full" if full else "short"
        self.assertEqual(first["0"], _line_get(f"first_{form}")["0"])
        engine.bytes_write(_line_bytes(f"reply_{form}"))
        return first

    # Reads one line and checks it ends the engine with the error's text.
    def error_check(
        self, engine: tap_tty.EngineTty, header: dict[str, Any], text: str
    ) -> None:
        line = _plain(engine.line_read())
        self.assertEqual(line["0"], header)
        self.assertEqual(line["message"], text)
        with self.assertRaises(EOFError):
            engine.line_read()
        self.assertEqual(engine.hangup(), _EXIT_FAILED)

    # The text of the root's TypeScript TAP file.
    def tap_read(self) -> str:
        with open(
            os.path.join(self.root, _TAP_FILE), encoding="utf-8"
        ) as file:
            return file.read()


# Tests the stock main loop on the tty: the start, the lines, the hangup.
class TestStock(ScratchCase):
    # In debug mode the first line has full names and carries the gold.
    def test_start_full(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        first = self.start_answer(engine, True)
        self.assertEqual(first["settings"], values)
        self.assertEqual(first["test_settings"], harness.gold_copy())
        engine.bytes_write(_line_bytes("tail_ui"))
        reply = _plain(engine.line_read())
        self.assertEqual(reply, {**_line_get("tail_ui_reply"), "lines": []})
        self.assertEqual(engine.hangup(), _HUNG_UP)
        for name in _FIXED_DBS:
            path = os.path.join(self.root, name + ".sqlite")
            self.assertTrue(os.path.isfile(path), path)

    # Outside debug mode the first line has short names and no gold.
    def test_start_short(self) -> None:
        values = self.root_make(False, None)
        engine = self.engine_run(values, None)
        first = self.start_answer(engine, False)
        self.assertEqual(first, {"0": first["0"], "settings": values})
        engine.bytes_write(_line_bytes("tail_short"))
        reply = _plain(engine.line_read())
        self.assertEqual(reply, _line_get("tail_short_reply"))
        self.assertEqual(engine.hangup(), _HUNG_UP)

    # Pushes are applied in order and a request after them sees them.
    def test_lines_served(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        for name in ("verbose_put", "tap_line", "tail_ui"):
            engine.bytes_write(_line_bytes(name))
        reply = _plain(engine.line_read())
        self.assertEqual(reply, _line_get("tail_ui_reply"))
        self.assertEqual(self.tap_read(), _line_get("tap_line")["text"] + "\n")
        self.assertEqual(engine.hangup(), _HUNG_UP)

    # A second engine on the root is refused while the first holds the lock.
    def test_lock_held(self) -> None:
        values = self.root_make(True, None)
        first = self.engine_run(values, None)
        self.start_answer(first, True)
        first.bytes_write(_line_bytes("tail_ui"))
        first.line_read()
        second = self.engine_run(values, None)
        path = os.path.join(self.root, _LOCK_NAME)
        text = _text_get("bootstrap_lock_held", path)
        self.error_check(second, _line_get("error")["0"], text)
        self.assertEqual(first.hangup(), _HUNG_UP)

    # A reply to the first line that is not the empty reply is refused.
    def test_reply_refused(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        first = _plain(engine.line_read())
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        engine.bytes_write(_line_bytes("reply_wrong"))
        text = _text_get("bootstrap_reply_unexpected")
        self.error_check(engine, _line_get("error")["0"], text)

    # The page's error line ends its TAP stream and the engine, unanswered.
    def test_page_failed(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        engine.bytes_write(_line_bytes("browser_error"))
        with self.assertRaises(EOFError):
            engine.line_read()
        self.assertEqual(engine.hangup(), _EXIT_FAILED)
        self.assertEqual(self.tap_read(), _text_get("bail_out") + "\n")

    # A request of no handler is answered by an error line, then exit 1.
    def test_request_unknown(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        engine.bytes_write(_line_bytes("unknown_request"))
        header = _line_get("error_reply")["0"]
        text = _text_get("dispatch_handler_unknown")
        self.error_check(engine, header, text)


# Tests the echo main loop on the tty: a blob that streams both ways.
class TestEcho(ScratchCase):
    # The reply carries the payload and the blob, each streamed to a file.
    def test_blob_streamed(self) -> None:
        values = self.root_make(True, _ECHO_NAME)
        values["overflow_bytes"] = _OVERFLOW_BYTES
        _json_write(self.root, "settings.json", values)
        sink = os.path.join(self.scratch, "sink")

        # Names the one file the blob of the reply streams to.
        def sink_make(header: jslb.Object) -> str:
            return sink

        arguments = ["--main-loop", _ECHO_NAME]
        engine = self.enterContext(
            tap_tty.EngineTty(self.root, arguments, values, sink_make)
        )
        self.start_answer(engine, True)
        request = _line_get("echo")
        header = jslb.header_make("echo", id=request["0"]["id"], full=True)
        blob = jslb.blob_make(_STREAMED_BYTES)
        engine.line_write(jslb.line_make(header, [blob], text=request["text"]))
        reply = engine.line_read()
        self.assertEqual(jslb.field_get(reply[0], "reply"), request["0"]["id"])
        self.assertEqual(jslb.payload_of(reply), {"text": request["text"]})
        self.assertEqual(jslb.field_get(reply[1], "data"), sink)
        with open(sink, "rb") as file:
            self.assertEqual(file.read(), _STREAMED_BYTES)
        self.assertEqual(engine.hangup(), _HUNG_UP)


# Tests the TAP suite server on the tty: a stream relayed, a suite refused.
class TestSuites(ScratchCase):
    # The gold's suites run on the server, their stream passing and whole.
    def test_suites_relayed(self) -> None:
        suites: list[str] = harness.gold_get(f"{_GOLD_ID}.suites")
        lines: list[str] = []
        code, errors = tap_tty.suites_relay(
            self.root, "smoke-test", False, suites, lines.append
        )
        self.assertEqual(code, 0)
        text = "".join(line + "\n" for line in lines)
        stats = tap_consumer.document_stats(text)
        self.assertTrue(stats.well_formed)
        self.assertEqual(stats.failed, 0)
        self.assertGreater(stats.passed, 0)
        parents = [
            f"ok {number} - {name}" for number, name in enumerate(suites, 1)
        ]
        self.assertEqual(
            [line for line in lines if line.startswith("ok ")], parents
        )
        self.assertTrue(errors.startswith(_text_get("timing")), errors)

    # A suite the driver does not know is refused with no stream.
    def test_suite_refused(self) -> None:
        values = self.root_make(True, _SUITE_NAME)
        engine = self.engine_run(values, _SUITE_NAME)
        self.start_answer(engine, True)
        engine.bytes_write(_line_bytes("run_refused"))
        reply = _plain(engine.line_read())
        self.assertEqual(reply["0"], _line_get("run_reply")["0"])
        self.assertEqual(reply["code"], _EXIT_USAGE)
        self.assertIn(_text_get("module_refused"), reply["stderr"])
        self.assertEqual(engine.hangup(), _HUNG_UP)
