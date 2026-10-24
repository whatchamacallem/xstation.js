# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handlers of `kv.put` and `kv.delete` on a store double: the
# type, version and handler each registration records, each handler called
# as the dispatcher calls it on lines of the gold, the calls it makes on the
# store, values byte for byte or as the path a streamed blob took, lines in
# full names, a line with `i` the handler leaves unanswered, and lines that
# lack a key or a blob. The store's own effects are `test_substrate.py`'s.

import base64, engine_kv, harness, hashlib, os, re, tempfile, unittest
import unittest.mock
from collections.abc import Callable
from typing import Any

# The checkout's build directory, where each test makes its scratch roots.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The dotted name of the store that the tests patch.
_STORE_TARGET = "engine_kv._STATE.store"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_kv"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# Every byte value once, the control bytes of a terminal included.
_VALUE_BYTES = bytes(range(256))

# A value over `overflow_bytes`, which the decoder streams to a file.
_VALUE_OVER = bytes(range(256)) * (
    harness.setting_get("overflow_bytes") // 256 + 1
)

# A small PNG image, as base64 text.
_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAH0lEQVR42mP4"
    "jwQYkAAucYZBqGGQO48oDaPxMCg0AADZV36QzYI8swAAAABJRU5ErkJggg=="
)

# The bytes of the image.
_IMAGE_BYTES = base64.b64decode(_IMAGE_BASE64)


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


# The `KvRow` shape `Store.kv_put` returns for a value, as a plain tuple.
def _row_of(ref: str, value: bytes) -> tuple[str, int, bytes]:
    return (ref, len(value), hashlib.sha256(value).digest())


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

    # `Store.kv_put`, as `engine_kv` calls it.
    def kv_put(self, ref: str, data: bytes | str) -> Any:
        return self.call_answer("kv_put", ref, data)

    # `Store.kv_delete`, as `engine_kv` calls it.
    def kv_delete(self, ref: str) -> Any:
        return self.call_answer("kv_delete", ref)


# Gives each test an empty state, a registration recorder, a store double.
class IsolatedCase(unittest.TestCase):
    # Patches the state and `dispatch.handler_register` through `engine_kv`.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        state = unittest.mock.patch(_STORE_TARGET, None)
        register = unittest.mock.patch.object(
            engine_kv.dispatch, "handler_register", self.handler_record
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

    # Registers the handlers on the store double, returns the one of `name`.
    def handler_get(self, name: str) -> Callable[..., Any]:
        store: Any = self.store
        engine_kv.handlers_register(store)
        (fn,) = [fn for kind, _, fn in self.handlers if kind == name]
        return fn

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


# Tests the handler of `kv.put`.
class TestPut(IsolatedCase):
    # The image goes to the store under the header's key. Nothing answers.
    def test_value_stored(self) -> None:
        put = self.handler_get("kv.put")
        line = _blob_line("put_image", _IMAGE_BYTES)
        key = line[0]["k"]
        self.store.answers["kv_put"] = [_row_of(key, _IMAGE_BYTES)]
        self.assertIsNone(_handler_call(put, line))
        self.assertEqual(self.store.calls, [("kv_put", key, _IMAGE_BYTES)])

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        put = self.handler_get("kv.put")
        line = _blob_line("put_full", b"one")
        key = line[0]["key"]
        self.store.answers["kv_put"] = [_row_of(key, b"one")]
        self.assertIsNone(_handler_call(put, line))
        self.assertEqual(self.store.calls, [("kv_put", key, b"one")])

    # Every byte value and an empty value go to the store as given.
    def test_bytes_identical(self) -> None:
        put = self.handler_get("kv.put")
        values = (_VALUE_BYTES, b"")
        key = _gold_value("lines.put")[0]["k"]
        self.store.answers["kv_put"] = [_row_of(key, v) for v in values]
        for value in values:
            self.assertIsNone(_handler_call(put, _blob_line("put", value)))
        expected = [("kv_put", key, value) for value in values]
        self.assertEqual(self.store.calls, expected)

    # A value the decoder streamed goes to the store as the path it took.
    def test_streamed_put(self) -> None:
        put = self.handler_get("kv.put")
        path = self.file_write(_VALUE_OVER)
        line = _blob_line("put", path)
        key = line[0]["k"]
        self.store.answers["kv_put"] = [_row_of(key, _VALUE_OVER)]
        self.assertIsNone(_handler_call(put, line))
        self.assertEqual(self.store.calls, [("kv_put", key, path)])

    # A put with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        put = self.handler_get("kv.put")
        line = _blob_line("put_request", b"one")
        key = line[0]["k"]
        self.store.answers["kv_put"] = [_row_of(key, b"one")]
        self.assertIsNone(_handler_call(put, line))
        self.assertEqual(self.store.calls, [("kv_put", key, b"one")])

    # A line with no blob raises, and so does a line with no key.
    def test_line_incomplete(self) -> None:
        put = self.handler_get("kv.put")
        line = _gold_value("lines.put_blobless")
        message = _text_get("engine_kv_blob_missing")
        self.raise_check(ValueError, message, lambda: _handler_call(put, line))
        keyless = _blob_line("put_keyless", b"one")
        message = _text_get("engine_kv_key_missing_put")
        self.raise_check(
            ValueError, message, lambda: _handler_call(put, keyless)
        )
        self.assertEqual(self.store.calls, [])


# Tests the handler of `kv.delete`.
class TestDelete(IsolatedCase):
    # A delete asks the store to delete the header's key.
    def test_key_deleted(self) -> None:
        delete = self.handler_get("kv.delete")
        line = _gold_value("lines.delete")
        self.store.answers["kv_delete"] = [None]
        self.assertIsNone(_handler_call(delete, line))
        self.assertEqual(self.store.calls, [("kv_delete", line[0]["k"])])

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        delete = self.handler_get("kv.delete")
        line = _gold_value("lines.delete_full")
        self.store.answers["kv_delete"] = [None]
        self.assertIsNone(_handler_call(delete, line))
        self.assertEqual(self.store.calls, [("kv_delete", line[0]["key"])])

    # A delete with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        delete = self.handler_get("kv.delete")
        line = _gold_value("lines.delete_request")
        self.store.answers["kv_delete"] = [None]
        self.assertIsNone(_handler_call(delete, line))
        self.assertEqual(self.store.calls, [("kv_delete", line[0]["k"])])

    # A line with no key raises.
    def test_key_missing(self) -> None:
        delete = self.handler_get("kv.delete")
        line = _gold_value("lines.delete_keyless")
        message = _text_get("engine_kv_key_missing_delete")
        self.raise_check(
            ValueError, message, lambda: _handler_call(delete, line)
        )
        self.assertEqual(self.store.calls, [])


# Tests the registration.
class TestRegister(IsolatedCase):
    # Each handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        store: Any = self.store
        engine_kv.handlers_register(store)
        expected = [
            ("kv.put", 0, engine_kv.kv_put),
            ("kv.delete", 0, engine_kv.kv_delete),
        ]
        self.assertEqual(self.handlers, expected)

    # Called before the registration each handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.put_blobless")
        message = _text_get("engine_kv_not_registered")
        calls: list[Callable[[], object]] = [
            lambda: engine_kv.kv_put(line),
            lambda: engine_kv.kv_delete(line),
        ]
        for call in calls:
            self.raise_check(RuntimeError, message, call)
