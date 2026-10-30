# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handler of `doc.put` on a real store on a scratch root in
# `build/`. Each test runs in a forked child that registers the handler in
# the real dispatcher and kills itself when done, so that no registration
# reaches another test, and the parent checks how the child said it ended.
# The handler is called as the dispatcher calls it on lines of the gold,
# their bodies' header keys integers as the decoder reads them, a line in
# full names and a line with `i` the handler leaves unanswered among them,
# and the document is read back from the store at the head it moved. The
# dispatcher refuses a second registration of the type at version 0.
# Versions, heads and the bodies and targets the store refuses are the
# store's own, `test_substrate.py`'s.

import dispatch, engine_doc, harness, os, re, signal, substrate, sys, tempfile
import traceback, unittest
from collections.abc import Callable
from typing import Any, cast

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_doc"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The size over which the store keeps a value in a cache file.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# The ref of the scene's first version, which a put writes.
_SCENE_REF = "/castle_gatehouse/scene/arrival/1"

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


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    payload = {
        key: value for key, value in line.items() if isinstance(key, str)
    }
    return fn(line, **payload)


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

    # In the child: a store on the root, the handler registered on it.
    def store_register(self) -> substrate.Store:
        store = substrate.Store(self.root, _OVERFLOW_BYTES)
        engine_doc.handlers_register(store)
        return store

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `doc.put`.
class TestPut(ScratchCase):
    # In the child: the handler on a gold line, then the document at its head.
    def put_check(self, name: str) -> None:
        line = _gold_value(f"lines.{name}")
        store = self.store_register()
        store.db_create(line["db"])
        self.assertIsNone(_handler_call(engine_doc.doc_put, line))
        self.assertEqual(store.doc_head(line["db"], line["id"]), _SCENE_REF)
        self.assertEqual(store.doc_get(_SCENE_REF), line["body"])

    # The scene goes to the store with its database, id and body.
    def test_document_put(self) -> None:
        self.child_run(lambda: self.put_check("put"))

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.put_check("put_full"))

    # A put with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.child_run(lambda: self.put_check("put_request"))


# Tests the registration.
class TestRegister(ScratchCase):
    # In the child: the dispatcher refuses the type at version 0 again.
    def registered_check(self) -> None:
        self.store_register()
        message = _text_get("dispatch_handler_twice_put")
        self.raise_check(
            ValueError,
            message,
            lambda: dispatch.handler_register(
                "doc.put", 0, engine_doc.doc_put
            ),
        )

    # The handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        self.child_run(self.registered_check)

    # In the child: before the registration the handler raises.
    def early_check(self) -> None:
        line = _gold_value("lines.put")
        message = _text_get("engine_doc_not_registered")
        self.raise_check(
            RuntimeError,
            message,
            lambda: _handler_call(engine_doc.doc_put, line),
        )

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        self.child_run(self.early_check)
