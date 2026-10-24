# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handlers of `db.create` and `db.drop`, and `restore_lines`, on a
# store double: the type, version and handler each registration records,
# each handler called as the dispatcher calls it on lines of the gold and
# the store call it makes, lines in full names, a line with `i` the handler
# leaves unanswered, and the `db.restore` and `db.file` lines of the image
# the double's `db_snapshot` gives, in both name forms, against the gold,
# one past the old 10 MiB window among them. Making, dropping, snapshotting
# and restoring a database are the store's own, `test_substrate.py`'s.

import engine_db, harness, os, re, tempfile, unittest, unittest.mock
from collections.abc import Callable
from typing import Any, NamedTuple

# The checkout's build directory, where each test makes its scratch roots.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The dotted name of the store that the tests patch.
_STORE_TARGET = "engine_db._STATE.store"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_db"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The database the tests snapshot.
_DATABASE = "castle"

# The bytes the store double gives as the database file, a pattern.
_DATA_BYTES = bytes(range(256))

# A value over `overflow_bytes`, as the store keeps in a cache file.
_VALUE_OVER = bytes(range(256)) * (
    harness.setting_get("overflow_bytes") // 256 + 1
)


# The `DbImage` shape `Store.db_snapshot` returns: the file and cache files.
class DatabaseImage(NamedTuple):
    data: bytes
    files: list[str]


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


# A store double: records each call, answers what the test queued for it.
class StoreDouble:
    # Starts with no call recorded and no answer queued.
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answers: dict[str, list[Any]] = {}

    # Records a call and returns its next queued answer, which must exist.
    def call_answer(self, name: str, *args: Any) -> Any:
        self.calls.append((name, *args))
        if not self.answers.get(name):
            raise AssertionError(f"the store double has no answer: {name}")
        return self.answers[name].pop(0)

    # `Store.db_create`, as `engine_db` calls it.
    def db_create(self, name: str) -> Any:
        return self.call_answer("db_create", name)

    # `Store.db_drop`, as `engine_db` calls it.
    def db_drop(self, name: str) -> Any:
        return self.call_answer("db_drop", name)

    # `Store.db_snapshot`, as `engine_db` calls it.
    def db_snapshot(self, db: str) -> Any:
        return self.call_answer("db_snapshot", db)


# Gives each test an empty state, a registration recorder, a store double.
class IsolatedCase(unittest.TestCase):
    # Patches the state and `dispatch.handler_register` through `engine_db`.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        state = unittest.mock.patch(_STORE_TARGET, None)
        register = unittest.mock.patch.object(
            engine_db.dispatch, "handler_register", self.handler_record
        )
        for patcher in (state, register):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.store = StoreDouble()

    # Records one registration in place of the dispatcher's table.
    def handler_record(
        self, name: str, version: int, fn: Callable[..., Any]
    ) -> None:
        self.handlers.append((name, version, fn))

    # Registers the handlers on the store double.
    def double_register(self) -> None:
        store: Any = self.store
        engine_db.handlers_register(store)

    # Registers the handlers on the store double, returns the one of `name`.
    def handler_get(self, name: str) -> Callable[..., Any]:
        self.double_register()
        (fn,) = [fn for kind, _, fn in self.handlers if kind == name]
        return fn

    # Calls the handler of `kind` on a gold line, checks its one store call.
    def push_check(self, kind: str, method: str, name: str) -> None:
        fn = self.handler_get(kind)
        line = _gold_value(f"lines.{name}")
        self.store.answers[method] = [None]
        self.assertIsNone(_handler_call(fn, line))
        self.assertEqual(self.store.calls, [(method, line["db"])])

    # Writes bytes to a new file in a scratch root under `build/`.
    def file_write(self, data: bytes) -> str:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        root = self.enterContext(tempfile.TemporaryDirectory(dir=_BUILD_PATH))
        path = os.path.join(root, "blob")
        with open(path, "xb") as file:
            file.write(data)
        return path

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `db.create`.
class TestCreate(IsolatedCase):
    # A create asks the store to create the line's database.
    def test_database_created(self) -> None:
        self.push_check("db.create", "db_create", "create")

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.push_check("db.create", "db_create", "create_full")

    # A create with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.push_check("db.create", "db_create", "create_request")


# Tests the handler of `db.drop`.
class TestDrop(IsolatedCase):
    # A drop asks the store to drop the line's database.
    def test_database_dropped(self) -> None:
        self.push_check("db.drop", "db_drop", "drop")

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.push_check("db.drop", "db_drop", "drop_full")

    # A drop with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.push_check("db.drop", "db_drop", "drop_request")


# Tests the lines of a whole database that `restore_lines` yields.
class TestRestoreLines(IsolatedCase):
    # Writes two values over `overflow_bytes`, the double's cache files.
    def files_write(self) -> list[str]:
        values = (_VALUE_OVER, bytes(reversed(_VALUE_OVER)))
        return [self.file_write(value) for value in values]

    # Two cache files: the database file's line, then one line for each file.
    def test_lines_made(self) -> None:
        self.double_register()
        files = self.files_write()
        image = DatabaseImage(_DATA_BYTES, files)
        self.store.answers["db_snapshot"] = [image, image]
        for full, suffix in ((False, ""), (True, "_full")):
            with self.subTest(full=full):
                lines = list(engine_db.restore_lines(_DATABASE, full))
                expected = [_blob_line(f"restore{suffix}", _DATA_BYTES)]
                for path in files:
                    expected.append(_blob_line(f"file{suffix}", path))
                self.assertEqual(lines, expected)
        snapshot = ("db_snapshot", _DATABASE)
        self.assertEqual(self.store.calls, [snapshot, snapshot])

    # No cache file: the database file's line alone, `files` 0.
    def test_lines_empty(self) -> None:
        self.double_register()
        self.store.answers["db_snapshot"] = [DatabaseImage(_DATA_BYTES, [])]
        lines = list(engine_db.restore_lines(_DATABASE, False))
        self.assertEqual(lines, [_blob_line("restore_empty", _DATA_BYTES)])
        self.assertEqual(self.store.calls, [("db_snapshot", _DATABASE)])

    # A database past the old 10 MiB window goes whole as blob 1.
    def test_lines_large(self) -> None:
        self.double_register()
        window: int = harness.gold_get(f"{_GOLD_ID}.old_window")
        data = bytes(window + 1)
        files = self.files_write()
        self.store.answers["db_snapshot"] = [DatabaseImage(data, files)]
        lines = list(engine_db.restore_lines(_DATABASE, False))
        expected = [_blob_line("restore", data)]
        for path in files:
            expected.append(_blob_line("file", path))
        self.assertEqual(lines, expected)
        self.assertGreater(lines[0][1]["s"], window)


# Tests the registration.
class TestRegister(IsolatedCase):
    # Each handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        self.double_register()
        expected = [
            ("db.create", 0, engine_db.db_create),
            ("db.drop", 0, engine_db.db_drop),
        ]
        self.assertEqual(self.handlers, expected)

    # Before the registration each handler and `restore_lines` raise.
    def test_called_early(self) -> None:
        create = _gold_value("lines.create")
        drop = _gold_value("lines.drop")
        message = _text_get("engine_db_not_registered")
        calls: list[Callable[[], object]] = [
            lambda: _handler_call(engine_db.db_create, create),
            lambda: _handler_call(engine_db.db_drop, drop),
            lambda: next(engine_db.restore_lines(_DATABASE, False)),
        ]
        for call in calls:
            self.raise_check(RuntimeError, message, call)
        self.assertEqual(self.store.calls, [])
