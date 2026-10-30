# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests engine_system with its real callees in forked children, each on a
# scratch root in `build/`: lines of the gold written as wire bytes, read by
# the real jslb decoder, which streams a blob over the gold's
# `overflow_bytes` into the root's cache, and served by the real
# dispatcher, each reply encoded by the real jslb encoder and read back from
# its JSON text. The settings the decoder read, checked by the real
# settings check and written whole; a main loop file from a blob in memory
# and from a blob the decoder streamed, moved out of the cache; the gate of
# debug mode, which leaves a streamed blob in the cache; and a restart to a
# file that does not exist refused, in a child that a restart would
# replace, so its ending shows the process kept. Each child writes how its
# work ended to a file, or to stderr when that write fails, then kills
# itself.

import engine_system, functools, harness, hashlib, json, os, signal, sys
import tempfile, traceback, unittest, uuid
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_engine_system"

# The limits of the decoder, as the checkout sets them.
_LINE_MAX: int = harness.setting_get("line_max")
_BLOB_MAX: int = harness.setting_get("blob_max")

# A size chosen by its writer, small: a blob over it streams to the cache.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# A main loop file whose blob stays in memory, within `_OVERFLOW_BYTES`.
_MEMORY_SOURCE = b"pass\n"

# A main loop file whose blob streams, over `_OVERFLOW_BYTES`.
_STREAMED_SOURCE = _MEMORY_SOURCE * _OVERFLOW_BYTES

# The directory of the root that the decoder streams blobs into.
_CACHE_NAME = "cache"

# The directory of the root that holds the main loop files.
_LOOP_NAME = "main_loop"

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


# The bytes of the gold `settings.put` carrying the settings.
def _settings_bytes(value: dict[str, Any]) -> bytes:
    return _line_bytes({**_gold_raw("lines.settings_put"), "settings": value})


# The bytes of the gold `source.put`, its blob the data given.
def _source_bytes(data: bytes) -> bytes:
    line = {**_gold_raw("lines.source_put"), "1": {"s": len(data)}}
    return _line_bytes(line) + data


# The reply the gold gives `source.put` for the data.
def _source_reply(data: bytes) -> dict[str, Any]:
    digest = hashlib.sha256(data).hexdigest()
    return {**_gold_raw("lines.source_reply"), "sha256": digest}


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# Names a new file in the root's cache for a blob the decoder streams.
def _sink_make(root: str, header: engine_system.jslb.Object) -> str:
    return os.path.join(root, _CACHE_NAME, uuid.uuid4().hex)


# The JSON text of a reply as the real encoder writes it, read back.
def _reply_read(reply: object) -> object:
    if not isinstance(reply, engine_system.jslb.Object):
        raise AssertionError(f"the result is not a reply: {reply!r}")
    (piece,) = engine_system.jslb.line_encode(reply)
    if not isinstance(piece, bytes):
        raise AssertionError(f"the reply's text is not bytes: {piece!r}")
    return json.loads(piece)


# In a child: registers, serves lines streaming to the cache, returns replies.
def _lines_serve(root: str, debug: bool, data: bytes) -> list[object]:
    engine_system.handlers_register(root, debug)
    decoder = engine_system.jslb.LineDecoder(
        _LINE_MAX,
        _BLOB_MAX,
        _OVERFLOW_BYTES,
        functools.partial(_sink_make, root),
    )
    replies: list[object] = []
    for line in decoder.bytes_feed(data):
        result = engine_system.dispatch.line_dispatch(line)
        replies.append(None if result is None else _reply_read(result))
    return replies


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


# Gives each test a scratch root, cache empty, in `build/`, work in children.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory, the root in it and the root's cache.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        self.cache = os.path.join(self.root, _CACHE_NAME)
        os.makedirs(self.cache)
        self.loop_path = os.path.join(self.root, _LOOP_NAME)

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


# Tests the lines of the system served through the dispatcher.
class TestServe(ScratchCase):
    # The settings the decoder read are written whole, the reply read back.
    def test_settings_served(self) -> None:
        value = harness.settings_copy()
        data = _settings_bytes(value)
        work = functools.partial(_lines_serve, self.root, True, data)
        expected = [_gold_raw("lines.settings_reply")]
        self.assertEqual(self.child_value(work), expected)
        path = os.path.join(self.root, "settings.json")
        with open(path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written, value)
        self.assertEqual(list(written), list(value))
        names = sorted(os.listdir(self.root))
        self.assertEqual(names, [_CACHE_NAME, "settings.json"])

    # A blob in memory is written as the main loop file.
    def test_source_memory(self) -> None:
        data = _source_bytes(_MEMORY_SOURCE)
        work = functools.partial(_lines_serve, self.root, True, data)
        expected = [_source_reply(_MEMORY_SOURCE)]
        self.assertEqual(self.child_value(work), expected)
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        path = os.path.join(self.loop_path, "a.py")
        self.assertEqual(_file_read(path), _MEMORY_SOURCE)
        self.assertEqual(os.listdir(self.cache), [])

    # A blob the decoder streamed is moved out of the cache into place.
    def test_source_streamed(self) -> None:
        data = _source_bytes(_STREAMED_SOURCE)
        work = functools.partial(_lines_serve, self.root, True, data)
        expected = [_source_reply(_STREAMED_SOURCE)]
        self.assertEqual(self.child_value(work), expected)
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        path = os.path.join(self.loop_path, "a.py")
        self.assertEqual(_file_read(path), _STREAMED_SOURCE)
        self.assertEqual(os.listdir(self.cache), [])

    # Debug off: each write refused, and a streamed blob stays in the cache.
    def test_debug_off(self) -> None:
        data = _settings_bytes(harness.settings_copy())
        self.child_raise(
            functools.partial(_lines_serve, self.root, False, data),
            RuntimeError,
            _text_get("engine_system_debug_off_settings"),
        )
        data = _source_bytes(_STREAMED_SOURCE)
        self.child_raise(
            functools.partial(_lines_serve, self.root, False, data),
            RuntimeError,
            _text_get("engine_system_debug_off_source"),
        )
        self.assertEqual(os.listdir(self.root), [_CACHE_NAME])
        (name,) = os.listdir(self.cache)
        path = os.path.join(self.cache, name)
        self.assertEqual(_file_read(path), _STREAMED_SOURCE)

    # A restart to a missing file is refused, in a child it would replace.
    def test_restart_refused(self) -> None:
        line = _gold_raw("lines.restart")
        path = os.path.join(self.loop_path, line["main_loop"])
        missing = _text_get("engine_system_main_loop_missing")
        self.child_raise(
            functools.partial(
                _lines_serve, self.root, True, _line_bytes(line)
            ),
            FileNotFoundError,
            missing.replace("{0}", path),
        )
