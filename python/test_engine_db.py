# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handlers of `db.create`, `db.drop` and `db.sync`, and
# `restore_lines`, on a real store on a scratch root in `build/`. Each test
# runs in a forked child that registers the handlers in the real dispatcher
# and kills itself when done, so that no registration reaches another test,
# and the parent checks how the child said it ended. Each handler is called
# as the dispatcher calls it on lines of the gold, lines in full names and a
# line with `i` the handler leaves unanswered among them, and its effect is
# read from the store. The `db.restore` and `db.file` lines are checked in
# both name forms against the gold and the store's own snapshot, one filled
# to its limit, `blob_max`, among them. The `Stream` of `db.sync` holds those
# lines in the gold's order, in every pairing of the two name forms, each
# database built as it is reached, a lost cache file left out and the log's
# file never named. The dispatcher refuses a second registration of each type
# at version 0. Making, dropping, snapshotting and restoring a database are
# the store's own, `test_substrate.py`'s.

import dispatch, engine_db, harness, jslb, os, re, signal, sqlite3, substrate
import switches, sys, tempfile, traceback, unittest, verbose
from collections.abc import Callable
from typing import Any, cast

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_engine_db"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The database the tests make, drop and snapshot.
_DATABASE = "castle"

# The file extension of a database under the root.
_DB_EXTENSION = ".sqlite"

# The size over which the store keeps a value in a cache file.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# The largest database file the store lets grow, the checkout's setting.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The lines of the log's ring, the checkout's setting.
_RING: int = harness.setting_get("verbose_ring")

# The databases of a sync, made out of name order.
_SYNC_MADE = ("keep", "castle", "_files")

# The last of those by name, which a stream reaches after the first.
_LATE_DATABASE = "keep"

# A ref in that database and a value written there while a stream runs.
_LATE_REF = "/keep/late"
_LATE_VALUE = b"a value written once the stream began"

# A value over `overflow_bytes`, as the store keeps in a cache file.
_VALUE_OVER = bytes(range(256)) * (_OVERFLOW_BYTES // 256 + 1)

# Two values over `overflow_bytes` by their refs, the database's cache files.
_VALUES_OVER = {
    "/castle/first": _VALUE_OVER,
    "/castle/second": bytes(reversed(_VALUE_OVER)),
}

# The statements that pad a database: a table, then a row of zero bytes.
_PADDING_SQL = (
    "CREATE TABLE padding (data BLOB NOT NULL) STRICT",
    "INSERT INTO padding VALUES (zeroblob(?))",
)

# How a child ends when its work returned.
_ENDING_PASSED = "passed"


# A copy of a value of this module's gold, its number keys made `int`.
def _gold_value(name: str) -> Any:
    return _keys_number(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A copy of a JSON value with each number key an `int`, at every depth.
def _keys_number(value: Any) -> Any:
    if isinstance(value, dict):
        made: dict[int | str, Any] = {}
        for key, item in cast(dict[str, Any], value).items():
            number = _NUMBER_KEY.fullmatch(key) is not None
            made[int(key) if number else key] = _keys_number(item)
        return made
    if isinstance(value, list):
        return [_keys_number(item) for item in cast(list[Any], value)]
    return value


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# A line of the gold with blob 1's size and `d` set, as the decoder gives it.
def _blob_line(name: str, data: bytes | str) -> dict[int | str, Any]:
    line: dict[int | str, Any] = _gold_value(f"lines.{name}")
    size = len(data) if isinstance(data, bytes) else os.path.getsize(data)
    line[1]["size" if "type" in line[0] else "s"] = size
    line[1]["d"] = data
    return line


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    payload = {
        key: value for key, value in line.items() if isinstance(key, str)
    }
    return fn(line, **payload)


# The type and database of each line, as the gold's `sync_order` lists them.
def _lines_order(lines: list[jslb.Object]) -> list[list[str]]:
    return [[jslb.field_get(line[0], "type"), line["db"]] for line in lines]


# The bytes of a file.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(work: Callable[[], object], path: str) -> None:
    try:
        try:
            work()
            ending = _ENDING_PASSED
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a scratch root in `build/` and a forked child to run in.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the root in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)

    # Runs the work in a forked child and fails with what the child raised.
    def child_run(self, work: Callable[[], object]) -> None:
        path = os.path.join(self.scratch, "ending.txt")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child_end(work, path)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(path)
        if ending != _ENDING_PASSED:
            self.fail(ending)

    # In the child: a store on the root, the handlers registered on it.
    def store_register(self) -> substrate.Store:
        store = substrate.Store(self.root, _OVERFLOW_BYTES, _BLOB_MAX)
        engine_db.handlers_register(store)
        return store

    # The file of a database under the root.
    def database_path(self, name: str) -> str:
        return os.path.join(self.root, name + _DB_EXTENSION)

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `db.create`.
class TestCreate(ScratchCase):
    # In the child: the handler on a gold line makes and opens its database.
    def create_check(self, name: str) -> None:
        line = _gold_value(f"lines.{name}")
        store = self.store_register()
        self.assertIsNone(_handler_call(engine_db.db_create, line))
        self.assertEqual(store.db_list(), [line["db"]])
        self.assertTrue(os.path.isfile(self.database_path(line["db"])))

    # A create makes the line's database in the store and opens it.
    def test_database_created(self) -> None:
        self.child_run(lambda: self.create_check("create"))

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.create_check("create_full"))

    # A create with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.child_run(lambda: self.create_check("create_request"))


# Tests the handler of `db.drop`.
class TestDrop(ScratchCase):
    # In the child: the handler on a gold line drops a database the store made.
    def drop_check(self, name: str) -> None:
        line = _gold_value(f"lines.{name}")
        store = self.store_register()
        store.db_create(line["db"])
        self.assertIsNone(_handler_call(engine_db.db_drop, line))
        self.assertEqual(store.db_list(), [])
        self.assertFalse(os.path.exists(self.database_path(line["db"])))

    # A drop closes the line's database and deletes its file.
    def test_database_dropped(self) -> None:
        self.child_run(lambda: self.drop_check("drop"))

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.drop_check("drop_full"))

    # A drop with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.child_run(lambda: self.drop_check("drop_request"))


# Tests the lines of a whole database that `restore_lines` yields.
class TestRestoreLines(ScratchCase):
    # In the child: makes the database with the two values over the limit.
    def values_write(self, store: substrate.Store) -> None:
        store.db_create(_DATABASE)
        for ref, value in _VALUES_OVER.items():
            store.kv_put(ref, value)

    # In the child: the lines of the store's own snapshot, as the gold's.
    def lines_expected(
        self, store: substrate.Store, restore_name: str, file_name: str
    ) -> list[dict[int | str, Any]]:
        image = store.db_snapshot(_DATABASE)
        expected = [_blob_line(restore_name, image.data)]
        expected += [_blob_line(file_name, path) for path in image.files]
        return expected

    # In the child: both name forms of the lines, the cache files the values.
    def made_check(self) -> None:
        store = self.store_register()
        self.values_write(store)
        for full, suffix in ((False, ""), (True, "_full")):
            lines = list(engine_db.restore_lines(_DATABASE, full))
            expected = self.lines_expected(
                store, f"restore{suffix}", f"file{suffix}"
            )
            self.assertEqual(lines, expected)
            files = sorted(_file_read(line[1]["d"]) for line in lines[1:])
            self.assertEqual(files, sorted(_VALUES_OVER.values()))

    # Two cache files: the database file's line, then one line for each file.
    def test_lines_made(self) -> None:
        self.child_run(self.made_check)

    # In the child: a database with no cache file, its file's line alone.
    def empty_check(self) -> None:
        store = self.store_register()
        store.db_create(_DATABASE)
        lines = list(engine_db.restore_lines(_DATABASE, False))
        image = store.db_snapshot(_DATABASE)
        self.assertEqual(image.files, [])
        self.assertEqual(lines, [_blob_line("restore_empty", image.data)])

    # No cache file: the database file's line alone, `files` 0.
    def test_lines_empty(self) -> None:
        self.child_run(self.empty_check)

    # In the child: the database padded until full, its files too.
    def large_check(self) -> None:
        store = self.store_register()
        self.values_write(store)
        create, insert = _PADDING_SQL
        store.sql_run(_DATABASE, [substrate.SqlStatement(create, [])])
        padding = [substrate.SqlStatement(insert, [_OVERFLOW_BYTES])]
        with self.assertRaises(sqlite3.OperationalError) as caught:
            for _ in range(_BLOB_MAX // _OVERFLOW_BYTES + 1):
                store.sql_run(_DATABASE, padding)
        code = caught.exception.sqlite_errorcode
        self.assertEqual(code, sqlite3.SQLITE_FULL)
        lines = list(engine_db.restore_lines(_DATABASE, False))
        self.assertEqual(lines, self.lines_expected(store, "restore", "file"))
        self.assertGreater(lines[0][1]["s"], _BLOB_MAX - 2 * _OVERFLOW_BYTES)
        self.assertLessEqual(lines[0][1]["s"], _BLOB_MAX)

    # A database filled to `blob_max` goes whole as blob 1.
    def test_lines_large(self) -> None:
        self.child_run(self.large_check)


# Tests the handler of `db.sync`.
class TestSync(ScratchCase):
    # In the child: makes the databases out of name order, the values in one.
    def databases_write(self, store: substrate.Store) -> None:
        for name in _SYNC_MADE:
            store.db_create(name)
        for ref, value in _VALUES_OVER.items():
            store.kv_put(ref, value)

    # In the child: the handler's answer to a gold line, `debug` set first.
    def stream_get(self, name: str, debug: bool) -> dispatch.Stream:
        switches.switches_apply({**switches.switches_get(), "debug": debug})
        line = _gold_value(f"lines.{name}")
        stream: dispatch.Stream = _handler_call(engine_db.db_sync, line)
        self.assertIsInstance(stream, dispatch.Stream)
        return stream

    # In the child: each database's lines in the gold's order, then the reply.
    def stream_check(self, suffix: str, debug: bool) -> None:
        store = self.store_register()
        self.databases_write(store)
        stream = self.stream_get(f"sync{suffix}", debug)
        reply = _gold_value(f"lines.sync_reply{suffix}")
        self.assertEqual(stream.reply, reply)
        pushes = list(stream.pushes)
        self.assertEqual(_lines_order(pushes), _gold_value("sync_order"))
        expected: list[jslb.Object] = []
        for name in reply["databases"]:
            expected += engine_db.restore_lines(name, debug)
        self.assertEqual(pushes, expected)

    # With debug off and a request in short names every line is in short names.
    def test_short_names(self) -> None:
        self.child_run(lambda: self.stream_check("", False))

    # With debug on and a request in full names every line is in full names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.stream_check("_full", True))

    # Debug on: the pushes are in full names, the reply in the request's.
    def test_pushes_full(self) -> None:
        self.child_run(lambda: self.stream_check("", True))

    # Debug off: the pushes are in short names, the reply in the request's.
    def test_pushes_short(self) -> None:
        self.child_run(lambda: self.stream_check("_full", False))

    # In the child: with no database the reply goes alone.
    def empty_check(self) -> None:
        self.store_register()
        stream = self.stream_get("sync", False)
        self.assertEqual(list(stream.pushes), [])
        self.assertEqual(stream.reply, _gold_value("lines.sync_reply_empty"))

    # A store with no database sends no push, and the reply names none.
    def test_no_database(self) -> None:
        self.child_run(self.empty_check)

    # In the child: a value written after the first line is in a later line.
    def reached_check(self) -> None:
        store = self.store_register()
        self.databases_write(store)
        pushes = iter(self.stream_get("sync", False).pushes)
        next(pushes)
        store.kv_put(_LATE_REF, _LATE_VALUE)
        image = store.db_snapshot(_LATE_DATABASE)
        self.assertEqual(list(pushes)[-1][1]["d"], image.data)

    # Each database's snapshot is taken as the stream reaches it, not before.
    def test_built_when_reached(self) -> None:
        self.child_run(self.reached_check)

    # In the child: one cache file removed, the other's line alone goes.
    def lost_check(self) -> None:
        store = self.store_register()
        self.databases_write(store)
        lost, held = store.db_snapshot(_DATABASE).files
        os.remove(lost)
        stream = self.stream_get("sync", False)
        pushes = list(stream.pushes)
        restore, *files = [line for line in pushes if line["db"] == _DATABASE]
        self.assertEqual(restore["files"], 1)
        self.assertEqual([line[1]["d"] for line in files], [held])
        self.assertEqual(stream.reply, _gold_value("lines.sync_reply"))

    # A cache file the server lost is left out, and the sync goes on.
    def test_file_lost(self) -> None:
        self.child_run(self.lost_check)

    # In the child: the log's file refuses the store and goes unnamed.
    def log_check(self) -> None:
        store = self.store_register()
        verbose.log_open(self.root, _RING, _BLOB_MAX)
        line = _gold_value("lines.create_log")
        self.assertTrue(os.path.isfile(self.database_path(line["db"])))
        with self.assertRaises(FileExistsError):
            _handler_call(engine_db.db_create, line)
        self.databases_write(store)
        stream = self.stream_get("sync", False)
        self.assertEqual(stream.reply, _gold_value("lines.sync_reply"))
        pushes = list(stream.pushes)
        self.assertEqual(_lines_order(pushes), _gold_value("sync_order"))

    # The log's `_verbose` is never held by the store, so no line names it.
    def test_log_unnamed(self) -> None:
        self.child_run(self.log_check)


# Tests the registration.
class TestRegister(ScratchCase):
    # In the child: the dispatcher refuses each type at version 0 again.
    def registered_check(self) -> None:
        self.store_register()
        handlers = [
            ("db.create", engine_db.db_create, "create"),
            ("db.drop", engine_db.db_drop, "drop"),
            ("db.sync", engine_db.db_sync, "sync"),
        ]
        for kind, fn, name in handlers:
            message = _text_get(f"dispatch_handler_twice_{name}")
            self.raise_check(
                ValueError,
                message,
                lambda: dispatch.handler_register(kind, 0, fn),
            )

    # Each handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        self.child_run(self.registered_check)

    # In the child: before the registration each handler and the lines raise.
    def early_check(self) -> None:
        create = _gold_value("lines.create")
        drop = _gold_value("lines.drop")
        sync = _gold_value("lines.sync")
        message = _text_get("engine_db_not_registered")
        calls: list[Callable[[], object]] = [
            lambda: _handler_call(engine_db.db_create, create),
            lambda: _handler_call(engine_db.db_drop, drop),
            lambda: _handler_call(engine_db.db_sync, sync),
            lambda: next(engine_db.restore_lines(_DATABASE, False)),
        ]
        for call in calls:
            self.raise_check(RuntimeError, message, call)

    # Before the registration each handler and `restore_lines` raise.
    def test_called_early(self) -> None:
        self.child_run(self.early_check)
