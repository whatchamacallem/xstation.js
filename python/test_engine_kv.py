# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handlers of `kv.put` and `kv.delete` on a real store on a
# scratch root in `build/`. Each test runs in a forked child that registers
# the handlers in the real dispatcher and kills itself when done, so that no
# registration reaches another test, and the parent checks how the child
# said it ended. Each handler is called as the dispatcher calls it on lines
# of the gold, and the store's rows are read back: values byte for byte or
# as the path a streamed blob took, lines in full names, a line with `i` the
# handler leaves unanswered, and lines that lack a key or a blob, which
# change no row. The dispatcher refuses a second registration of each type
# at version 0. The store's own effects are `test_substrate.py`'s.

import base64, dispatch, engine_kv, harness, os, re, signal, substrate, sys
import tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any, cast

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_kv"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The database of the refs of the gold's lines.
_FILES_DB = "_files"

# The size over which the store keeps a value in a cache file.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# Every byte value once, the control bytes of a terminal included.
_VALUE_BYTES = bytes(range(256))

# A value over `overflow_bytes`, which the decoder streams to a file.
_VALUE_OVER = bytes(range(256)) * (_OVERFLOW_BYTES // 256 + 1)

# A small PNG image, as base64 text.
_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAH0lEQVR42mP4"
    "jwQYkAAucYZBqGGQO48oDaPxMCg0AADZV36QzYI8swAAAABJRU5ErkJggg=="
)

# The bytes of the image.
_IMAGE_BYTES = base64.b64decode(_IMAGE_BASE64)

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


# The ref in the header of a line of the gold, in either name form.
def _ref_of(line: dict[int | str, Any]) -> str:
    ref: str = line[0]["key" if "type" in line[0] else "k"]
    return ref


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    payload = {
        key: value for key, value in line.items() if isinstance(key, str)
    }
    return fn(line, **payload)


# The bytes of a value the store holds: as held, or read from its file.
def _value_bytes(data: bytes | str) -> bytes:
    if isinstance(data, bytes):
        return data
    with open(data, "rb") as file:
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

    # In the child: a store on the root with `_files`, the handlers on it.
    def store_register(self) -> substrate.Store:
        store = substrate.Store(self.root, _OVERFLOW_BYTES)
        store.db_create(_FILES_DB)
        engine_kv.handlers_register(store)
        return store

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `kv.put`.
class TestPut(ScratchCase):
    # In the child: the handler on a gold line, then the value under its ref.
    def put_check(self, name: str, data: bytes | str, value: bytes) -> None:
        store = self.store_register()
        line = _blob_line(name, data)
        self.assertIsNone(_handler_call(engine_kv.kv_put, line))
        self.assertEqual(_value_bytes(store.kv_get(_ref_of(line)).data), value)

    # The image goes to the store under the header's key. Nothing answers.
    def test_value_stored(self) -> None:
        self.child_run(
            lambda: self.put_check("put_image", _IMAGE_BYTES, _IMAGE_BYTES)
        )

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.put_check("put_full", b"one", b"one"))

    # Every byte value goes to the store as given.
    def test_bytes_identical(self) -> None:
        self.child_run(
            lambda: self.put_check("put", _VALUE_BYTES, _VALUE_BYTES)
        )

    # An empty value goes to the store as given.
    def test_value_empty(self) -> None:
        self.child_run(lambda: self.put_check("put", b"", b""))

    # A value the decoder streamed goes to the store as the path it took.
    def test_streamed_put(self) -> None:
        path = os.path.join(self.scratch, "blob")
        with open(path, "xb") as file:
            file.write(_VALUE_OVER)
        self.child_run(lambda: self.put_check("put", path, _VALUE_OVER))

    # A put with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.child_run(lambda: self.put_check("put_request", b"one", b"one"))

    # In the child: a line with no blob or no key raises, and no row is made.
    def incomplete_check(self) -> None:
        store = self.store_register()
        line = _gold_value("lines.put_blobless")
        message = _text_get("engine_kv_blob_missing")
        self.raise_check(
            ValueError, message, lambda: _handler_call(engine_kv.kv_put, line)
        )
        keyless = _blob_line("put_keyless", b"one")
        message = _text_get("engine_kv_key_missing_put")
        self.raise_check(
            ValueError,
            message,
            lambda: _handler_call(engine_kv.kv_put, keyless),
        )
        self.assertEqual(store.kv_list(_FILES_DB, ""), [])

    # A line with no blob raises, and so does a line with no key.
    def test_line_incomplete(self) -> None:
        self.child_run(self.incomplete_check)


# Tests the handler of `kv.delete`.
class TestDelete(ScratchCase):
    # In the child: a row the store made, then the handler on a gold line.
    def delete_check(self, name: str) -> None:
        store = self.store_register()
        line = _gold_value(f"lines.{name}")
        store.kv_put(_ref_of(line), b"one")
        self.assertIsNone(_handler_call(engine_kv.kv_delete, line))
        self.assertEqual(store.kv_list(_FILES_DB, ""), [])

    # A delete removes the row of the header's key.
    def test_key_deleted(self) -> None:
        self.child_run(lambda: self.delete_check("delete"))

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.delete_check("delete_full"))

    # A delete with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.child_run(lambda: self.delete_check("delete_request"))

    # In the child: a line with no key raises, and the row stays.
    def missing_check(self) -> None:
        store = self.store_register()
        ref = _ref_of(_gold_value("lines.delete"))
        store.kv_put(ref, b"one")
        line = _gold_value("lines.delete_keyless")
        message = _text_get("engine_kv_key_missing_delete")
        self.raise_check(
            ValueError,
            message,
            lambda: _handler_call(engine_kv.kv_delete, line),
        )
        self.assertEqual(store.kv_get(ref).data, b"one")

    # A line with no key raises.
    def test_key_missing(self) -> None:
        self.child_run(self.missing_check)


# Tests the registration.
class TestRegister(ScratchCase):
    # In the child: the dispatcher refuses each type at version 0 again.
    def registered_check(self) -> None:
        self.store_register()
        handlers = [
            ("kv.put", engine_kv.kv_put, "put"),
            ("kv.delete", engine_kv.kv_delete, "delete"),
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

    # In the child: before the registration each handler raises.
    def early_check(self) -> None:
        line = _gold_value("lines.put_blobless")
        message = _text_get("engine_kv_not_registered")
        calls: list[Callable[[], object]] = [
            lambda: engine_kv.kv_put(line),
            lambda: engine_kv.kv_delete(line),
        ]
        for call in calls:
            self.raise_check(RuntimeError, message, call)

    # Called before the registration each handler raises.
    def test_called_early(self) -> None:
        self.child_run(self.early_check)
