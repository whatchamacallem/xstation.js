# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handlers of `verbose.put` and `verbose.tail` in forked children,
# each on the real log of a scratch root in `build/`, opened through
# `engine_verbose.verbose` as `bootstrap.py` opens it, and registered with
# the real dispatcher, so the debug setting, the handlers and the log never
# reach another test. Each handler is called as the dispatcher calls it on
# lines of the gold: the page lines a put writes under their thread, read
# back from `_verbose`; the tail of the server from its ring, the lines it
# logged with the times the log measured, and of a page thread from the
# database, each with the count given; the gate of debug mode on
# `verbose.put` alone; and the lines a put refuses, its batch unwritten. The
# registration is read from the dispatcher, which refuses a second one of
# each type. Each child writes how its work ended to a file, or to stderr
# when that write fails, then kills itself.

import contextlib, engine_verbose, functools, harness, json, os, re, signal
import sqlite3, sys, tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_verbose"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The lines the ring of a child's log holds, as the checkout sets it.
_RING: int = harness.setting_get("verbose_ring")

# The file of the root's log.
_LOG_FILE = "_verbose.sqlite"

# The query of the time, thread and text of each line of the log, in order.
_ROWS_QUERY = "SELECT at, thread, text FROM line ORDER BY seq"

# The thread whose lines the server's own ring holds.
_SERVER_THREAD = "server"

# The texts the server logs in a child before the tails are asked for.
_SERVER_TEXTS: list[str] = harness.gold_get(f"{_GOLD_ID}.server_texts")

# The gold puts whose page lines the database holds for the tails.
_PAGE_PUTS = ("put_ui", "put_ai")

# The file in the scratch directory that a child writes how it ended to.
_ENDING_NAME = "ending.json"


# A copy of a value of this module's gold, its number keys made `int`.
def _gold_value(name: str) -> Any:
    return _keys_number(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A value of this module's gold as JSON holds it, which is not to be changed.
def _gold_raw(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


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


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    payload = {
        key: value for key, value in line.items() if isinstance(key, str)
    }
    return fn(line, **payload)


# The time, thread and text of each line of the root's log, in order.
def _rows_read(root: str) -> list[tuple[int, str, str]]:
    path = os.path.join(root, _LOG_FILE)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        rows: list[tuple[int, str, str]] = connection.execute(
            _ROWS_QUERY
        ).fetchall()
    return rows


# The rows that the gold's page lines make in the log, in order.
def _page_rows() -> list[tuple[int, str, str]]:
    rows: list[tuple[int, str, str]] = []
    for name in _PAGE_PUTS:
        put = _gold_value(f"lines.{name}")
        for entry in put["lines"]:
            rows.append((entry["at"], put["thread"], entry["text"]))
    return rows


# The last `count` lines of the server in the rows, as a tail replies them.
def _server_lines(
    rows: list[tuple[int, str, str]], count: int
) -> list[dict[str, object]]:
    lines: list[dict[str, object]] = [
        {"at": at, "text": text}
        for at, thread, text in rows
        if thread == _SERVER_THREAD
    ]
    return lines[len(lines) - min(count, len(lines)) :]


# Opens the root's log through `engine_verbose`, then registers the handlers.
def _log_register(root: str, debug: bool) -> None:
    engine_verbose.verbose.log_open(root, _RING)
    engine_verbose.handlers_register(debug)


# The work of a child: registers, then calls the put handler on each line.
def _lines_put(root: str, debug: bool, lines: list[Any]) -> list[Any]:
    _log_register(root, debug)
    return [_handler_call(engine_verbose.verbose_put, line) for line in lines]


# In a child: registers, logs server and page lines, then tails each line.
def _tails_get(root: str, debug: bool, lines: list[Any]) -> list[Any]:
    _log_register(root, debug)
    for text in _SERVER_TEXTS:
        engine_verbose.verbose.log(text)
    for name in _PAGE_PUTS:
        put = _gold_value(f"lines.{name}")
        entries = [
            engine_verbose.verbose.LogLine(entry["at"], entry["text"])
            for entry in put["lines"]
        ]
        engine_verbose.verbose.lines_put(put["thread"], entries)
    return [_handler_call(engine_verbose.verbose_tail, line) for line in lines]


# The work of a child: registers, then registers a handler's type again.
def _register_twice(name: str) -> None:
    engine_verbose.handlers_register(True)
    engine_verbose.dispatch.handler_register(
        name, 0, engine_verbose.verbose_tail
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


# Tests the handler of `verbose.put`.
class TestPut(ScratchCase):
    # Page lines are written under their thread, in order.
    def test_lines_stored(self) -> None:
        lines = [_gold_value(f"lines.{name}") for name in _PAGE_PUTS]
        work = functools.partial(_lines_put, self.root, True, lines)
        self.assertEqual(self.child_value(work), [None, None])
        self.assertEqual(_rows_read(self.root), _page_rows())

    # With debug mode off the handler raises and nothing is written.
    def test_debug_off(self) -> None:
        lines = [_gold_value("lines.put_ui")]
        self.child_raise(
            functools.partial(_lines_put, self.root, False, lines),
            RuntimeError,
            _text_get("engine_verbose_debug_off"),
        )
        self.assertEqual(_rows_read(self.root), [])

    # A bad field raises and the batch that holds the line is not written.
    def test_line_invalid(self) -> None:
        for case, line in _gold_value("lines.put_invalid").items():
            with self.subTest(case=case):
                self.child_raise(
                    functools.partial(_lines_put, self.root, True, [line]),
                    ValueError,
                    _text_get(f"engine_verbose_line_invalid_{case}"),
                )
                self.assertEqual(_rows_read(self.root), [])

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.put_ui")
        self.child_raise(
            functools.partial(_handler_call, engine_verbose.verbose_put, line),
            RuntimeError,
            _text_get("engine_verbose_not_registered"),
        )


# Tests the handler of `verbose.tail`.
class TestTail(ScratchCase):
    # The server's tail is the last lines it logged, as the log stored them.
    def test_tail_lines(self) -> None:
        line = _gold_value("lines.tail_server")
        work = functools.partial(_tails_get, self.root, True, [line])
        (reply,) = self.child_value(work)
        lines = _server_lines(_rows_read(self.root), line["count"])
        expected = {**_gold_raw("lines.tail_server_reply"), "lines": lines}
        self.assertEqual(reply, expected)
        texts = [entry["text"] for entry in lines]
        self.assertEqual(texts, _SERVER_TEXTS[-line["count"] :])

    # The count reaches the ring as given, a large one included.
    def test_tail_counts(self) -> None:
        counts = (0, 1, 3, harness.gold_get(f"{_GOLD_ID}.history_all"))
        lines: list[Any] = []
        for count in counts:
            line = _gold_value("lines.tail_server")
            line["count"] = count
            lines.append(line)
        work = functools.partial(_tails_get, self.root, True, lines)
        replies = self.child_value(work)
        rows = _rows_read(self.root)
        for count, reply in zip(counts, replies, strict=True):
            with self.subTest(count=count):
                self.assertEqual(reply["lines"], _server_lines(rows, count))

    # A page thread's tail comes from the database with its thread and count.
    def test_page_threads(self) -> None:
        threads = ("ui", "ai")
        lines = [_gold_value(f"lines.tail_{thread}") for thread in threads]
        work = functools.partial(_tails_get, self.root, True, lines)
        expected = [
            _gold_raw(f"lines.tail_{thread}_reply") for thread in threads
        ]
        self.assertEqual(self.child_value(work), expected)

    # Debug mode does not gate the tail, of the server or of a page thread.
    def test_tail_ungated(self) -> None:
        line = _gold_value("lines.tail_server")
        lines = [line, _gold_value("lines.tail_ui")]
        work = functools.partial(_tails_get, self.root, False, lines)
        server, page = self.child_value(work)
        rows = _rows_read(self.root)
        self.assertEqual(server["lines"], _server_lines(rows, line["count"]))
        self.assertEqual(page, _gold_raw("lines.tail_ui_reply"))


# Tests the registration.
class TestRegister(ScratchCase):
    # Each handler is registered under its type at version 0, a repeat refused.
    def test_handlers_registered(self) -> None:
        for name, case in (("verbose.put", "put"), ("verbose.tail", "tail")):
            with self.subTest(name=name):
                self.child_raise(
                    functools.partial(_register_twice, name),
                    ValueError,
                    _text_get(f"dispatch_handler_twice_{case}"),
                )
