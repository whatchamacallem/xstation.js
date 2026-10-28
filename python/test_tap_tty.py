# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests bootstrap.py run whole on a pty as ttyd runs it, unpatched, through
# tap_tty's EngineTty, with roots in build/ whose settings are the
# checkout's and whose test settings are the checkout's gold. On the stock
# main loop: the first line in either name form and its payload, the empty
# reply, a wrong reply to tap.start refused, each line type the stock main
# loop registers sent once with its reply and the databases checked, the
# restart that system.restart starts going on over the same tty after
# settings.put and source.put, the page's error line ending the TypeScript
# stream with its cascade logged, a handler's Failure answered before the
# server's error line, a request no handler serves, the hangup that ends
# the engine with SIGHUP with a reply unread, and mcp_stdio.py served on the
# same root while the engine runs. On stall_loop.py, the hangup that ends an
# engine that never writes its first line. On the TAP suite server,
# tap_loop.py: a suite of this checkout relayed by suites_relay as a passing
# stream, its timings carried in the reply; failing_suite.py, which fails by
# design, relayed whole with its failures expected exactly, run again with
# one failure fewer and one more expected, each failing the run, and relayed
# by a failfast run, its stream ended by a bail out; and a suite the driver
# does not know refused by its exit code and its stderr, with no stream. The
# lines sent and expected, the texts, the suites run and the failing suite's
# counts are this module's gold.

import contextlib, copy, harness, hashlib, jslb, json, os, shutil, signal
import sqlite3, subprocess, sys, tap_consumer, tap_tty, tempfile, time
import unittest
from typing import Any, NoReturn

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The checkout's `python` directory, which holds the main loop files.
_PYTHON_PATH = os.path.join(_ROOT_PATH, "python")

# The MCP server on stdio, run beside the engine.
_STDIO_PATH = os.path.join(_PYTHON_PATH, "mcp_stdio.py")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_tap_tty"

# The most seconds a child of a test, or a wait on the engine, may take.
_CHILD_SECONDS: int = harness.gold_get(f"{_GOLD_ID}.child_seconds")

# The seconds between two looks at the root while a test waits on it.
_POLL_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.poll_seconds")

# The directory of a root that holds the main loop files.
_LOOP_DIRECTORY = "main_loop"

# The echo main loop file, which the restart test sends and restarts into.
_ECHO_NAME = "echo_loop.py"

# The main loop file whose prepare never returns.
_STALL_NAME = "stall_loop.py"

# The TAP suite server's main loop file.
_SUITE_NAME = "tap_loop.py"

# The TAP file of the TypeScript stream in a root.
_TAP_FILE = os.path.join("tap", "typescript.tap")

# The fixed databases the stock main loop's prepare creates in a new root.
_FIXED_DBS = ("_settings", "_preferences", "_files", "metaverse")

# The database the line types test creates, writes and drops.
_CASTLE_DB = "castle"

# The database of the scripts' files, which the provider's script is in.
_FILES_DB = "_files"

# The key of the provider's script in `_files`, which the prepare seeds.
_PROVIDER_KEY = "provider/script.json"

# The key of the value the line types test puts in the castle.
_KEPT_KEY = "kept"

# The root's log, a database of its own.
_LOG_DB = "_verbose"

# The query of the hash and the value of one key.
_VALUE_QUERY = "SELECT sha256, data FROM _kv WHERE key = ?"

# The query of one key, a row when the key is there.
_KEY_QUERY = "SELECT key FROM _kv WHERE key = ?"

# The query of the heads of the documents.
_HEADS_QUERY = "SELECT id, version FROM _head ORDER BY id"

# The query of the turns of a database.
_TURNS_QUERY = "SELECT scene, n, role, content FROM _turn ORDER BY n"

# The query of the table the `sql.run` line makes.
_TABLE_QUERY = "SELECT x FROM t"

# The query of the lines of the log.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The query that finds the log's table, a row once the engine opened it.
_LOG_FIND = "SELECT name FROM sqlite_schema WHERE type = 'table'"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"

# The exit code of a hangup, minus the number of the signal that ended it.
_HUNG_UP = -signal.SIGHUP

# The exit code of a failure.
_EXIT_FAILED = 1

# The exit code `argparse` gives a command line it refuses.
_EXIT_USAGE = 2


# A value of this module's gold.
def _gold_value(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# A copy of a line of this module's gold, free to change.
def _line_get(name: str) -> Any:
    return copy.deepcopy(_gold_value(f"lines.{name}"))


# A text of this module's gold, each `{n}` replaced by the value at `n`.
def _text_get(name: str, *values: str) -> str:
    text: str = _gold_value(f"texts.{name}")
    for number, value in enumerate(values):
        text = text.replace(f"{{{number}}}", value)
    return text


# The compact JSON text of a value, as the wire and the substrate write it.
def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# The bytes of a gold line on the wire: its JSON text, a CR, its blobs.
def _line_bytes(name: str, *blobs: bytes) -> bytes:
    line: dict[str, Any] = _line_get(name)
    for number, blob in enumerate(blobs, 1):
        line[str(number)]["size"] = len(blob)
    return b"".join([_json_text(line).encode("utf-8"), b"\r", *blobs])


# The stats of the lines of a stream relayed.
def _stats_read(lines: list[str]) -> tap_consumer.TapStats:
    return tap_consumer.document_stats("".join(line + "\n" for line in lines))


# A line read back as JSON values, its integer keys strings, as the gold.
def _plain(line: jslb.Object) -> Any:
    return json.loads(json.dumps(line, ensure_ascii=False))


# Refuses a blob that streams, as no line here carries one that large.
def _sink_refuse(header: jslb.Object) -> NoReturn:
    raise AssertionError(f"a blob came that streams: {header}")


# Writes a value as the JSON text of a file of the root.
def _json_write(root: str, name: str, value: object) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with open(os.path.join(root, name), "w", encoding="utf-8") as file:
        file.write(text)


# Reads the bytes of a file.
def _bytes_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# Runs a query on a database file under the root and returns its rows.
def _rows_read(root: str, db: str, sql: str, *params: object) -> list[Any]:
    path = os.path.join(root, db + ".sqlite")
    with contextlib.closing(sqlite3.connect(path)) as connection:
        return connection.execute(sql, params).fetchall()


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

    # The lines of the root's log, each its thread and its text.
    def log_read(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = _rows_read(
            self.root, _LOG_DB, _LOG_QUERY
        )
        return rows

    # Waits until the engine has opened the root's log, past its raw mode.
    def log_wait(self) -> None:
        path = os.path.join(self.root, _LOG_DB + ".sqlite")
        deadline = time.monotonic() + _CHILD_SECONDS
        while not (
            os.path.exists(path) and _rows_read(self.root, _LOG_DB, _LOG_FIND)
        ):
            if time.monotonic() > deadline:
                raise AssertionError(f"no log in {_CHILD_SECONDS} s: {path}")
            time.sleep(_POLL_SECONDS)


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

    # A reply to the first line that is not the empty reply is refused.
    def test_reply_refused(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        first = _plain(engine.line_read())
        self.assertEqual(first["0"], _line_get("first_full")["0"])
        engine.bytes_write(_line_bytes("reply_wrong"))
        text = _text_get("bootstrap_reply_unexpected")
        self.error_check(engine, _line_get("error")["0"], text)

    # Each line type but the debug ones, once, each push seen by the next.
    def test_lines_served(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        kept: str = _gold_value("kept_value")
        pushes = [
            _line_bytes("create_castle"),
            _line_bytes("put_kept", kept.encode("utf-8")),
            _line_bytes("delete_provider"),
            _line_bytes("doc_note"),
            _line_bytes("turn_note"),
            _line_bytes("sql_castle"),
            _line_bytes("verbose_put"),
            _line_bytes("tap_line"),
            _line_bytes("tail_ui"),
        ]
        engine.bytes_write(b"".join(pushes))
        reply = _plain(engine.line_read())
        self.assertEqual(reply, _line_get("tail_ui_reply"))
        rows = _rows_read(self.root, _CASTLE_DB, _VALUE_QUERY, _KEPT_KEY)
        self.assertEqual([data for _, data in rows], [kept.encode("utf-8")])
        rows = _rows_read(self.root, _FILES_DB, _KEY_QUERY, _PROVIDER_KEY)
        self.assertEqual(rows, [])
        note = _line_get("doc_note")
        heads = _rows_read(self.root, _CASTLE_DB, _HEADS_QUERY)
        self.assertEqual(heads, [(note["id"], 1)])
        turn = _line_get("turn_note")
        turns = _rows_read(self.root, _CASTLE_DB, _TURNS_QUERY)
        content = _json_text(turn["content"])
        self.assertEqual(turns, [(turn["scene"], 1, turn["role"], content)])
        table = _rows_read(self.root, _CASTLE_DB, _TABLE_QUERY)
        self.assertEqual(table, [(7,)])
        self.assertEqual(self.tap_read(), _line_get("tap_line")["text"] + "\n")
        engine.bytes_write(
            _line_bytes("drop_castle") + _line_bytes("initialize")
        )
        reply = _plain(engine.line_read())
        self.assertEqual(reply, _line_get("initialize_reply"))
        castle = os.path.join(self.root, _CASTLE_DB + ".sqlite")
        self.assertFalse(os.path.exists(castle))
        self.assertEqual(engine.hangup(), _HUNG_UP)

    # The debug lines put the settings and a main loop file, then restart.
    def test_restart_served(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        changed = {**values, "verbose_ring": _gold_value("ring")}
        header = jslb.header_make("settings.put", id=102, full=True)
        engine.line_write(jslb.line_make(header, [], settings=changed))
        reply = _plain(engine.line_read())
        self.assertEqual(reply, _line_get("settings_reply"))
        with open(
            os.path.join(self.root, "settings.json"), encoding="utf-8"
        ) as file:
            self.assertEqual(json.load(file), changed)
        source = _bytes_read(os.path.join(_PYTHON_PATH, _ECHO_NAME))
        engine.bytes_write(_line_bytes("source_put", source))
        reply = _plain(engine.line_read())
        digest = hashlib.sha256(source).hexdigest()
        self.assertEqual(
            reply, {**_line_get("source_reply"), "sha256": digest}
        )
        path = os.path.join(self.root, _LOOP_DIRECTORY, _ECHO_NAME)
        self.assertEqual(_bytes_read(path), source)
        engine.bytes_write(_line_bytes("restart"))
        first = self.start_answer(engine, True)
        self.assertEqual(first["settings"], changed)
        self.assertEqual(first["test_settings"], harness.gold_copy())
        engine.bytes_write(_line_bytes("echo"))
        reply = _plain(engine.line_read())
        self.assertEqual(reply, _line_get("echo_reply"))
        self.assertEqual(engine.hangup(), _HUNG_UP)

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
        error = _line_get("browser_error")
        texts = [
            _text_get("engine_tap_browser_failed"),
            error["stack"],
            _text_get("engine_tap_browser_cause"),
            error["cause"]["stack"],
        ]
        # The cascade is logged last, after the trace of the first line.
        cascade = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(self.log_read()[-len(cascade) :], cascade)

    # A handler's `Failure` writes its reply, then the server's error line.
    def test_failure_answered(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        engine.bytes_write(_line_bytes("call_name_invalid"))
        reply = _plain(engine.line_read())
        self.assertEqual(reply["0"], _line_get("call_reply")["0"])
        self.assertIs(reply["result"]["isError"], True)
        text = _text_get("name_invalid")
        self.error_check(engine, _line_get("error")["0"], text)

    # A request of no handler is answered by an error line, then exit 1.
    def test_request_unknown(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        engine.bytes_write(_line_bytes("unknown_request"))
        header = _line_get("error_reply")["0"]
        text = _text_get("dispatch_handler_unknown")
        self.error_check(engine, header, text)

    # A hangup with a reply unread ends the engine by SIGHUP, no failure.
    def test_hangup_unread(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        engine.bytes_write(_line_bytes("tail_ui"))
        self.assertEqual(engine.hangup(), _HUNG_UP)
        prefix = _text_get("failed_prefix")
        for thread, text in self.log_read():
            self.assertFalse(text.startswith(prefix), (thread, text))

    # `mcp_stdio.py` serves the same root while the engine runs on it.
    def test_stdio_beside(self) -> None:
        values = self.root_make(True, None)
        engine = self.engine_run(values, None)
        self.start_answer(engine, True)
        names = ("stdio_initialize", "stdio_initialized", "stdio_call")
        sent = "".join(_json_text(_line_get(name)) + "\n" for name in names)
        process = subprocess.run(
            [sys.executable, _STDIO_PATH, "--root", self.root],
            input=sent.encode("utf-8"),
            capture_output=True,
            timeout=_CHILD_SECONDS,
        )
        self.assertEqual((process.returncode, process.stderr), (0, b""))
        opened, called = [
            json.loads(text) for text in process.stdout.splitlines()
        ]
        self.assertEqual(opened, _line_get("stdio_initialize_reply"))
        arguments = _line_get("stdio_call")["params"]["arguments"]
        source = arguments["text"].encode("utf-8")
        digest = _json_text({"sha256": hashlib.sha256(source).hexdigest()})
        content = [{"type": "text", "text": digest}]
        result = {"content": content, "isError": False}
        self.assertEqual(
            called, {**_line_get("stdio_call_reply"), "result": result}
        )
        path = os.path.join(self.root, _LOOP_DIRECTORY, arguments["name"])
        self.assertEqual(_bytes_read(path), source)
        engine.bytes_write(_line_bytes("tail_ui"))
        reply = _plain(engine.line_read())
        self.assertEqual(reply, {**_line_get("tail_ui_reply"), "lines": []})
        self.assertEqual(engine.hangup(), _HUNG_UP)


# Tests the stall main loop on the tty: the hangup of a silent engine.
class TestStall(ScratchCase):
    # The engine that never writes its first line ends by SIGHUP, unlogged.
    def test_stall_hangup(self) -> None:
        values = self.root_make(True, _STALL_NAME)
        engine = self.engine_run(values, _STALL_NAME)
        self.log_wait()
        self.assertEqual(engine.hangup(), _HUNG_UP)
        self.assertEqual(self.log_read(), [])


# Tests the TAP suite server on the tty: a stream relayed, a suite refused.
class TestSuites(ScratchCase):
    # The gold's suites run on the server, their stream passing and whole.
    def test_suites_relayed(self) -> None:
        suites: list[str] = _gold_value("suites")
        lines: list[str] = []
        code, errors = tap_tty.suites_relay(
            self.root, "smoke-test", False, 0, suites, lines.append
        )
        self.assertEqual(code, 0)
        stats = _stats_read(lines)
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

    # Relays the failing suite on a root of its own, expecting `failures`.
    def failing_relay(
        self, name: str, category: str, failures: int
    ) -> tuple[int, list[str]]:
        lines: list[str] = []
        root = os.path.join(self.scratch, name)
        suites = [_gold_value("failing.suite")]
        code, _ = tap_tty.suites_relay(
            root, category, False, failures, suites, lines.append
        )
        return code, lines

    # The failing suite relayed whole holds its failures, exactly expected.
    def test_failures_relayed(self) -> None:
        failures: int = _gold_value("failing.failures")
        code, lines = self.failing_relay("root", "normal-test", failures)
        self.assertEqual(code, 0)
        stats = tap_consumer.TapStats(*_gold_value("failing.stats"))
        self.assertEqual(_stats_read(lines), stats)
        suite: str = _gold_value("failing.suite")
        self.assertEqual(lines[-2:], [f"not ok 1 - {suite}", "1..1"])

    # Expecting one failure fewer or one more than the stream holds fails.
    def test_failures_miscounted(self) -> None:
        failures: int = _gold_value("failing.failures")
        for name, expected in (
            ("fewer", failures - 1),
            ("more", failures + 1),
        ):
            code, lines = self.failing_relay(name, "normal-test", expected)
            self.assertEqual(code, _EXIT_FAILED, name)
            self.assertEqual(_stats_read(lines).failed, failures, name)

    # A `smoke-test` run is failfast: its first failure bails out, one failure.
    def test_bail_relayed(self) -> None:
        code, lines = self.failing_relay("root", "smoke-test", 1)
        self.assertEqual(code, 0)
        stats = _stats_read(lines)
        self.assertEqual((stats.failed, stats.well_formed), (1, True))
        self.assertEqual(lines[-1], _text_get("bail_failfast"))

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
