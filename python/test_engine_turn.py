# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handler of `turn.append` on a real store on a scratch root in
# `build/`. Each test runs in a forked child that registers the handler in
# the real dispatcher and kills itself when done, so that no registration
# reaches another test, and the parent checks how the child said it ended.
# The handler is called as the dispatcher calls it on lines of the gold, and
# the scene's turns are read back from the store: the role and the message
# as canonical JSON, a message with null and a list whole, text beyond ASCII
# as raw characters, a line in full names, and a line with `i` the handler
# leaves unanswered. The dispatcher refuses a second registration of the
# type at version 0. The numbering of turns and the scenes the store refuses
# are the store's own, `test_substrate.py`'s.

import dispatch, engine_turn, harness, json, os, re, signal, substrate, sys
import tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any, cast

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_turn"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The database of the scene of the gold's lines.
_SCENE_DB = "metaverse"

# The size over which the store keeps a value in a cache file.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# Text beyond ASCII, built from its code points, as the gold's wide turn.
_WIDE_TEXT = chr(0x4E2D) + chr(0x6587) + chr(0x1F600)

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


# The canonical JSON text of a value, as the handler stores a message.
def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


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

    # In the child: a store on the root with the scene's database, the handler.
    def store_register(self) -> substrate.Store:
        store = substrate.Store(self.root, _OVERFLOW_BYTES)
        store.db_create(_SCENE_DB)
        engine_turn.handlers_register(store)
        return store

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)


# Tests the handler of `turn.append`.
class TestAppend(ScratchCase):
    # In the child: the handler on gold lines in order, then the scene's turns.
    def append_check(self, *names: str) -> list[substrate.TurnRow]:
        store = self.store_register()
        lines = [_gold_value(f"lines.{name}") for name in names]
        for line in lines:
            self.assertIsNone(_handler_call(engine_turn.turn_append, line))
        expected = [
            substrate.TurnRow(
                line["scene"], n, line["role"], _json_text(line["content"])
            )
            for n, line in enumerate(lines, 1)
        ]
        turns = store.turn_list(lines[0]["scene"])
        self.assertEqual(turns, expected)
        return turns

    # The player's first message goes to the store as canonical JSON.
    def test_turn_appended(self) -> None:
        self.child_run(lambda: self.append_check("append_user"))

    # A message with null and a list goes whole, each turn in order.
    def test_messages_whole(self) -> None:
        names = ("append_user", "append_call", "append_answer")
        self.child_run(lambda: self.append_check(*names))

    # In the child: the wide text is in the stored message as it is.
    def wide_check(self) -> None:
        (turn,) = self.append_check("append_wide")
        self.assertIn(_WIDE_TEXT, turn.content)

    # Text beyond ASCII is passed as raw characters, not as escapes.
    def test_text_wide(self) -> None:
        self.child_run(self.wide_check)

    # A line in full names is applied as one in short names.
    def test_full_names(self) -> None:
        self.child_run(lambda: self.append_check("append_full"))

    # An append with `i` is applied and answered with nothing, as a push is.
    def test_request_none(self) -> None:
        self.child_run(lambda: self.append_check("append_request"))


# Tests the registration.
class TestRegister(ScratchCase):
    # In the child: the dispatcher refuses the type at version 0 again.
    def registered_check(self) -> None:
        self.store_register()
        message = _text_get("dispatch_handler_twice_append")
        self.raise_check(
            ValueError,
            message,
            lambda: dispatch.handler_register(
                "turn.append", 0, engine_turn.turn_append
            ),
        )

    # The handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        self.child_run(self.registered_check)

    # In the child: before the registration the handler raises.
    def early_check(self) -> None:
        line = _gold_value("lines.append_user")
        message = _text_get("engine_turn_not_registered")
        self.raise_check(
            RuntimeError,
            message,
            lambda: _handler_call(engine_turn.turn_append, line),
        )

    # Called before the registration the handler raises.
    def test_called_early(self) -> None:
        self.child_run(self.early_check)
