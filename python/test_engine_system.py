# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handlers of `settings.put`, `source.put` and `system.restart`
# and the two tools of the same names: the type, version and handler each
# registration records, each handler called as the dispatcher calls it on
# lines of the gold, a blob's `d` the bytes or the path of a file the decoder
# would have streamed, and the tools as a server double records them, each
# called on the arguments the test chooses. The settings file is rewritten
# whole, a main loop file is written from bytes or moved from the streamed
# file, its name is refused unless plain, and the arguments of the restart
# are checked up to the call of `os.execv`, which is patched. Debug mode
# gates all of them. The settings check holds the types of every table, the
# PowerShell constants' among them. A tool's exception reaches its caller;
# the `isError` answer the MCP server makes of it is `test_mcp.py`'s. The
# scratch directories go under `build/`.

import engine_system, harness, hashlib, json, os, re, sys, tempfile
import unittest, unittest.mock
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The settings file of the checkout, whose bytes the written file matches.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The dotted name of the root that the tests patch.
_ROOT_TARGET = "engine_system._STATE.root"

# The dotted name of the debug setting that the tests patch.
_DEBUG_TARGET = "engine_system._STATE.debug"

# The dotted name of the call that replaces the process image.
_EXEC_TARGET = "os.execv"

# The dotted name of the arguments the process was started with.
_ARGV_TARGET = "sys.orig_argv"

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_system"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The process option that names the main loop file.
_MAIN_LOOP_OPTION = "--main-loop"

# The arguments of a process that was started with no main loop option.
_PROGRAM_ARGV = ["python3", "-X", "dev", "/r/bootstrap.py", "--root", "/r"]

# The text of a main loop file.
_SOURCE_TEXT = "print('main loop')\n"

# The `JSON-RPC` code of arguments that a tool cannot use.
_CODE_PARAMS = -32602

# Names that are not plain file names that end in `.py`, and their texts.
_NAMES_INVALID = (
    ("", "engine_system_name_invalid_empty"),
    ("b", "engine_system_name_invalid_b"),
    ("b.txt", "engine_system_name_invalid_txt"),
    (".b.py", "engine_system_name_invalid_hidden"),
    (".py", "engine_system_name_invalid_bare"),
    ("d/b.py", "engine_system_name_invalid_nested"),
    ("../b.py", "engine_system_name_invalid_parent"),
)

# Forms of the option and its value that argparse reads as `--main-loop`.
_OPTION_FORMS: tuple[list[str], ...] = (
    ["--main-loop=a.py"],
    ["--main", "a.py"],
    ["--m=a.py"],
    ["--main-loo", "a.py"],
)


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


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


# A line of the gold with one payload key set to the value the test gives.
def _line_set(name: str, key: str, value: Any) -> dict[int | str, Any]:
    line: dict[int | str, Any] = _gold_value(f"lines.{name}")
    line[key] = value
    return line


# A line of the gold with blob 1's size and `d` set, as the decoder gives it.
def _blob_line(name: str, data: bytes | str) -> dict[int | str, Any]:
    line: dict[int | str, Any] = _gold_value(f"lines.{name}")
    size = len(data) if isinstance(data, bytes) else os.path.getsize(data)
    line[1]["size" if "type" in line[0] else "s"] = size
    line[1]["d"] = data
    return line


# A line of the gold whose blob 1 the decoder streamed to `path`, digest set.
def _streamed_line(name: str, path: str, data: bytes) -> dict[int | str, Any]:
    with open(path, "xb") as file:
        file.write(data)
    line = _blob_line(name, path)
    line[1]["sha256"] = hashlib.sha256(data).hexdigest()
    return line


# Calls a handler as `dispatch.line_dispatch` does, the payload as keywords.
def _handler_call(fn: Callable[..., Any], line: dict[int | str, Any]) -> Any:
    payload = {
        key: value for key, value in line.items() if isinstance(key, str)
    }
    return fn(line, **payload)


# Reads the tool entries of the server side of the API file.
def _entries_read() -> list[dict[str, Any]]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data["server"]["result"]["tools"]


# Writes a main loop file in the root, with its directory.
def _loop_write(root: str, name: str) -> str:
    path = os.path.join(root, "main_loop", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(_SOURCE_TEXT)
    return path


# Stands for the end of the process image, which a successful exec causes.
class ImageReplaced(BaseException):
    pass


# A dict subclass of the shape of `jslb.Object`, as the decoder makes one.
class DecodedObject(dict[int | str, Any]):
    pass


# A server double: records each call, answers what the test queued for it.
class ServerDouble:
    # Starts with no call recorded and no answer queued.
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answers: dict[str, list[Any]] = {}

    # Records a call and returns its next queued answer, which must exist.
    def call_answer(self, name: str, *args: Any) -> Any:
        self.calls.append((name, *args))
        if not self.answers.get(name):
            raise AssertionError(f"the server double has no answer: {name}")
        return self.answers[name].pop(0)

    # `Server.tool_register`, as `engine_system` calls it.
    def tool_register(self, tool: Any, fn: Callable[..., Any]) -> Any:
        return self.call_answer("tool_register", tool, fn)


# Gives each test an empty state, a registration recorder, a scratch root.
class IsolatedCase(unittest.TestCase):
    # Patches the state and the registration, makes a scratch root.
    def setUp(self) -> None:
        self.handlers: list[tuple[str, int, Callable[..., Any]]] = []
        root_state = unittest.mock.patch(_ROOT_TARGET, None)
        debug_state = unittest.mock.patch(_DEBUG_TARGET, None)
        register = unittest.mock.patch.object(
            engine_system.dispatch, "handler_register", self.handler_record
        )
        for patcher in (root_state, debug_state, register):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name
        self.settings_path = os.path.join(self.root, "settings.json")
        self.loop_path = os.path.join(self.root, "main_loop")
        self.file_path = os.path.join(self.loop_path, "a.py")

    # Records one registration in place of the dispatcher's table.
    def handler_record(
        self, name: str, version: int, fn: Callable[..., Any]
    ) -> None:
        self.handlers.append((name, version, fn))

    # Registers the handlers for the debug setting, returns the one of `name`.
    def handler_get(self, name: str, debug: bool) -> Callable[..., Any]:
        engine_system.handlers_register(self.root, debug)
        (fn,) = [fn for kind, _, fn in self.handlers if kind == name]
        return fn

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)

    # Calls a handler on a line and checks the type and the text it raises.
    def handler_check(
        self,
        kind: type[Exception],
        message: str,
        fn: Callable[..., Any],
        line: dict[int | str, Any],
    ) -> None:
        self.raise_check(kind, message, lambda: _handler_call(fn, line))


# Tests the handler of `settings.put`.
class TestSettings(IsolatedCase):
    # The file is the settings object written whole, and no file is left over.
    def test_settings_written(self) -> None:
        put = self.handler_get("settings.put", True)
        line = _line_set("settings_put", "settings", harness.settings_copy())
        reply = _handler_call(put, line)
        self.assertEqual(reply, _gold_value("lines.settings_reply"))
        written = _file_read(self.settings_path)
        self.assertEqual(written, _file_read(_SETTINGS_PATH))
        self.assertEqual(os.listdir(self.root), ["settings.json"])

    # A changed value is in the file, and the file replaces the old one.
    def test_settings_replaced(self) -> None:
        put = self.handler_get("settings.put", True)
        with open(self.settings_path, "w", encoding="utf-8") as file:
            file.write("old\n")
        changed = harness.settings_copy()
        changed["debug"] = False
        changed["provider"]["scripted"] = False
        _handler_call(put, _line_set("settings_put", "settings", changed))
        with open(self.settings_path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written, changed)
        self.assertEqual(list(written), list(changed))
        self.assertEqual(os.listdir(self.root), ["settings.json"])

    # A nested provider of a dict subclass, as the decoder makes it, is kept.
    def test_provider_object(self) -> None:
        put = self.handler_get("settings.put", True)
        changed = harness.settings_copy()
        provider = DecodedObject(changed["provider"])
        provider["timeout_seconds"] = 60
        changed["provider"] = provider
        _handler_call(put, _line_set("settings_put", "settings", changed))
        with open(self.settings_path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written["provider"], provider)

    # Settings that fail the check raise and the old file stays as it was.
    def test_settings_invalid(self) -> None:
        put = self.handler_get("settings.put", True)
        with open(self.settings_path, "w", encoding="utf-8") as file:
            file.write("old\n")
        missing = harness.settings_copy()
        del missing["line_max"]
        extra = harness.settings_copy()
        extra["other"] = 1
        wrong = harness.settings_copy()
        wrong["provider"]["timeout_seconds"] = "120"
        variable = harness.settings_copy()
        variable["provider"]["variable"] = 1
        listed = harness.settings_copy()
        listed["powershell"]["root_files"] = ["settings.json", 1]
        table = harness.settings_copy()
        table["powershell"]["build_tools"] = {"cmake": None}
        dropped = harness.settings_copy()
        del dropped["powershell"]["linux_port"]
        cases: list[tuple[dict[str, Any], str]] = [
            (missing, "settings_key_missing_line_max"),
            (extra, "settings_key_extra"),
            (wrong, "settings_type_wrong_timeout"),
            (variable, "settings_type_wrong_variable"),
            (listed, "settings_type_wrong_root_files"),
            (table, "settings_type_wrong_build_tools"),
            (dropped, "settings_key_missing_linux_port"),
        ]
        for bad, name in cases:
            with self.subTest(name=name):
                line = _line_set("settings_put", "settings", bad)
                message = _text_get(name)
                self.handler_check(ValueError, message, put, line)
                self.assertEqual(_file_read(self.settings_path), b"old\n")
                self.assertEqual(os.listdir(self.root), ["settings.json"])

    # With debug mode off the handler raises and writes nothing.
    def test_settings_gated(self) -> None:
        put = self.handler_get("settings.put", False)
        line = _line_set("settings_put", "settings", harness.settings_copy())
        message = _text_get("engine_system_debug_off_settings")
        self.handler_check(RuntimeError, message, put, line)
        self.assertEqual(os.listdir(self.root), [])


# Tests the handler of `source.put`.
class TestSource(IsolatedCase):
    # A blob in memory is written as the file, and the reply is its `sha256`.
    def test_bytes_written(self) -> None:
        put = self.handler_get("source.put", True)
        data = _SOURCE_TEXT.encode("utf-8")
        reply = _handler_call(put, _blob_line("source_put", data))
        expected = _gold_value("lines.source_reply")
        expected["sha256"] = hashlib.sha256(data).hexdigest()
        self.assertEqual(reply, expected)
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), data)

    # A blob the decoder streamed to the cache is moved into place.
    def test_blob_streamed(self) -> None:
        put = self.handler_get("source.put", True)
        cache = os.path.join(self.root, "cache")
        os.makedirs(cache)
        source = os.path.join(cache, "blob")
        data = _SOURCE_TEXT.encode("utf-8")
        line = _streamed_line("source_put", source, data)
        reply = _handler_call(put, line)
        expected = _gold_value("lines.source_reply")
        expected["sha256"] = hashlib.sha256(data).hexdigest()
        self.assertEqual(reply, expected)
        self.assertFalse(os.path.exists(source))
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), data)

    # A second write under the same name replaces the file.
    def test_file_replaced(self) -> None:
        put = self.handler_get("source.put", True)
        _loop_write(self.root, "a.py")
        _handler_call(put, _blob_line("source_put", b"new\n"))
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), b"new\n")

    # A name that is not plain raises and nothing is written.
    def test_name_invalid(self) -> None:
        put = self.handler_get("source.put", True)
        for name, text in _NAMES_INVALID:
            with self.subTest(name=name):
                line = _blob_line("source_put", b"x")
                line["name"] = name
                message = _text_get(text)
                self.handler_check(ValueError, message, put, line)
                self.assertEqual(os.listdir(self.root), [])

    # A streamed blob under a name that is not plain stays in the cache.
    def test_streamed_refused(self) -> None:
        put = self.handler_get("source.put", True)
        source = os.path.join(self.root, "blob")
        line = _streamed_line("source_put", source, b"x")
        line["name"] = "../a.py"
        message = _text_get("engine_system_name_invalid_parent_a")
        self.handler_check(ValueError, message, put, line)
        self.assertEqual(os.listdir(self.root), ["blob"])

    # A line with no blob raises and nothing is written.
    def test_blob_missing(self) -> None:
        put = self.handler_get("source.put", True)
        line = _gold_value("lines.source_blobless")
        message = _text_get("engine_system_blob_missing")
        self.handler_check(ValueError, message, put, line)
        self.assertEqual(os.listdir(self.root), [])

    # With debug mode off the handler raises and writes nothing.
    def test_source_gated(self) -> None:
        put = self.handler_get("source.put", False)
        line = _blob_line("source_put", b"x")
        message = _text_get("engine_system_debug_off_source")
        self.handler_check(RuntimeError, message, put, line)
        self.assertEqual(os.listdir(self.root), [])


# Tests the handler of `system.restart` up to the call that replaces the image.
class TestRestart(IsolatedCase):
    # The call gets the interpreter and the arguments with the option last.
    def test_exec_argv(self) -> None:
        restart = self.handler_get("system.restart", True)
        _loop_write(self.root, "b.py")
        line = _gold_value("lines.restart")
        with (
            unittest.mock.patch(
                _EXEC_TARGET, side_effect=ImageReplaced
            ) as execv,
            unittest.mock.patch(_ARGV_TARGET, _PROGRAM_ARGV),
            self.assertRaises(ImageReplaced),
        ):
            _handler_call(restart, line)
        expected = _PROGRAM_ARGV + [_MAIN_LOOP_OPTION, "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # An option the process already had is removed with its value.
    def test_option_replaced(self) -> None:
        restart = self.handler_get("system.restart", True)
        _loop_write(self.root, "b.py")
        line = _gold_value("lines.restart")
        argv = _PROGRAM_ARGV + [_MAIN_LOOP_OPTION, "a.py", "--other"]
        with (
            unittest.mock.patch(
                _EXEC_TARGET, side_effect=ImageReplaced
            ) as execv,
            unittest.mock.patch(_ARGV_TARGET, argv),
            self.assertRaises(ImageReplaced),
        ):
            _handler_call(restart, line)
        expected = _PROGRAM_ARGV + ["--other", _MAIN_LOOP_OPTION, "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # Each form of the option that argparse takes is removed with its value.
    def test_option_forms(self) -> None:
        restart = self.handler_get("system.restart", True)
        _loop_write(self.root, "b.py")
        line = _gold_value("lines.restart")
        expected = _PROGRAM_ARGV + ["--other", _MAIN_LOOP_OPTION, "b.py"]
        for form in _OPTION_FORMS:
            with self.subTest(form=form):
                argv = _PROGRAM_ARGV + form + ["--other"]
                with (
                    unittest.mock.patch(
                        _EXEC_TARGET, side_effect=ImageReplaced
                    ) as execv,
                    unittest.mock.patch(_ARGV_TARGET, argv),
                    self.assertRaises(ImageReplaced),
                ):
                    _handler_call(restart, line)
                execv.assert_called_once_with(sys.executable, expected)

    # A word that only looks like the option is kept.
    def test_option_kept(self) -> None:
        restart = self.handler_get("system.restart", True)
        _loop_write(self.root, "b.py")
        line = _gold_value("lines.restart")
        argv = _PROGRAM_ARGV + ["--mainloop", "--main-loops=a.py"]
        with (
            unittest.mock.patch(
                _EXEC_TARGET, side_effect=ImageReplaced
            ) as execv,
            unittest.mock.patch(_ARGV_TARGET, argv),
            self.assertRaises(ImageReplaced),
        ):
            _handler_call(restart, line)
        expected = argv + [_MAIN_LOOP_OPTION, "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # A file that does not exist raises and the process is not replaced.
    def test_file_missing(self) -> None:
        restart = self.handler_get("system.restart", True)
        os.makedirs(self.loop_path)
        os.makedirs(os.path.join(self.loop_path, "b.py"))
        for name in ("a.py", "b.py"):
            with self.subTest(name=name):
                line = _line_set("restart", "main_loop", name)
                path = os.path.join(self.loop_path, name)
                missing = _text_get("engine_system_main_loop_missing")
                message = missing.replace("{0}", path)
                with unittest.mock.patch(_EXEC_TARGET) as execv:
                    self.handler_check(
                        FileNotFoundError, message, restart, line
                    )
                execv.assert_not_called()

    # A name that is not plain raises, even where a file of it exists.
    def test_name_invalid(self) -> None:
        restart = self.handler_get("system.restart", True)
        _loop_write(self.root, "b.py")
        _loop_write(self.root, os.path.join("d", "b.py"))
        outside = os.path.join(self.root, "b.py")
        with open(outside, "w", encoding="utf-8") as file:
            file.write(_SOURCE_TEXT)
        for name, text in _NAMES_INVALID:
            with self.subTest(name=name):
                line = _line_set("restart", "main_loop", name)
                message = _text_get(text)
                with unittest.mock.patch(_EXEC_TARGET) as execv:
                    self.handler_check(ValueError, message, restart, line)
                execv.assert_not_called()

    # With debug mode off the handler raises and the process is not replaced.
    def test_restart_gated(self) -> None:
        restart = self.handler_get("system.restart", False)
        _loop_write(self.root, "b.py")
        line = _gold_value("lines.restart")
        message = _text_get("engine_system_debug_off_restart")
        with unittest.mock.patch(_EXEC_TARGET) as execv:
            self.handler_check(RuntimeError, message, restart, line)
        execv.assert_not_called()


# Tests the two tools as a server double records them.
class TestTools(IsolatedCase):
    # Registers the tools on a server double, returns each tool and its fn.
    def tools_record(
        self, debug: bool
    ) -> list[tuple[Any, Callable[..., Any]]]:
        server = ServerDouble()
        server.answers["tool_register"] = [None, None]
        double: Any = server
        engine_system.tools_register(double, self.root, debug)
        return [(tool, fn) for _, tool, fn in server.calls]

    # The function of the tool named, registered for the debug setting.
    def tool_get(self, name: str, debug: bool) -> Callable[..., Any]:
        recorded = self.tools_record(debug)
        (fn,) = [fn for tool, fn in recorded if tool[0] == name]
        return fn

    # Calls `fn` and checks it raises an `RpcError` of the params code.
    def params_check(self, message: str, fn: Callable[[], object]) -> None:
        with self.assertRaises(Exception) as caught:
            fn()
        error: Any = caught.exception
        self.assertEqual(type(error).__name__, "RpcError")
        self.assertEqual(str(error), message)
        self.assertEqual(error.code, _CODE_PARAMS)

    # The tools are the server side of the API file, key for key.
    def test_tools_listed(self) -> None:
        tools = [tool for tool, _ in self.tools_record(True)]
        expected = [
            [
                entry["name"],
                entry["description"],
                entry["inputSchema"],
                "_meta" in entry,
            ]
            for entry in _entries_read()
        ]
        self.assertEqual(json.dumps(tools), json.dumps(expected))

    # Neither tool is registered with a permit, so no client asks for one.
    def test_permit_absent(self) -> None:
        tools = [tool for tool, _ in self.tools_record(True)]
        self.assertEqual(
            [(tool[0], tool[3]) for tool in tools],
            [("source_put", False), ("system_restart", False)],
        )

    # The source tool writes the text as the file and answers its `sha256`.
    def test_source_tool(self) -> None:
        source = self.tool_get("source_put", True)
        content, is_error = source({"name": "a.py", "text": _SOURCE_TEXT})
        digest = hashlib.sha256(_SOURCE_TEXT.encode("utf-8")).hexdigest()
        self.assertIs(is_error, False)
        (block,) = content
        self.assertEqual(block["type"], "text")
        self.assertEqual(json.loads(block["text"]), {"sha256": digest})
        written = _file_read(self.file_path)
        self.assertEqual(written, _SOURCE_TEXT.encode("utf-8"))

    # With debug mode off the source tool raises and writes nothing.
    def test_source_gated(self) -> None:
        source = self.tool_get("source_put", False)
        arguments = {"name": "a.py", "text": _SOURCE_TEXT}
        message = _text_get("engine_system_debug_off_source_tool")
        self.raise_check(RuntimeError, message, lambda: source(arguments))
        self.assertEqual(os.listdir(self.root), [])

    # Arguments that are missing or not text are refused with their code.
    def test_source_arguments(self) -> None:
        source = self.tool_get("source_put", True)
        text_invalid = "engine_system_argument_invalid_text"
        name_invalid = "engine_system_argument_invalid_name"
        bad: list[tuple[dict[str, Any], str]] = [
            ({"name": "a.py"}, text_invalid),
            ({"text": "x"}, name_invalid),
            ({"name": 5, "text": "x"}, name_invalid),
            ({"name": "a.py", "text": None}, text_invalid),
        ]
        for arguments, text in bad:
            with self.subTest(arguments=arguments):
                message = _text_get(text)
                self.params_check(message, lambda: source(arguments))
        self.assertEqual(os.listdir(self.root), [])

    # A name that is not plain raises as any exception of a tool does.
    def test_source_name(self) -> None:
        source = self.tool_get("source_put", True)
        arguments = {"name": "../a.py", "text": "x"}
        message = _text_get("engine_system_name_invalid_parent_a")
        self.raise_check(ValueError, message, lambda: source(arguments))
        self.assertEqual(os.listdir(self.root), [])

    # The restart tool replaces the process image as the handler does.
    def test_restart_tool(self) -> None:
        restart = self.tool_get("system_restart", True)
        _loop_write(self.root, "b.py")
        with (
            unittest.mock.patch(
                _EXEC_TARGET, side_effect=ImageReplaced
            ) as execv,
            unittest.mock.patch(_ARGV_TARGET, _PROGRAM_ARGV),
            self.assertRaises(ImageReplaced),
        ):
            restart({"main_loop": "b.py"})
        expected = _PROGRAM_ARGV + [_MAIN_LOOP_OPTION, "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # With debug mode off the restart tool raises and nothing is replaced.
    def test_restart_gated(self) -> None:
        restart = self.tool_get("system_restart", False)
        _loop_write(self.root, "b.py")
        message = _text_get("engine_system_debug_off_restart_tool")
        with unittest.mock.patch(_EXEC_TARGET) as execv:
            self.raise_check(
                RuntimeError, message, lambda: restart({"main_loop": "b.py"})
            )
        execv.assert_not_called()

    # A missing file or a missing argument raises and nothing is replaced.
    def test_restart_refused(self) -> None:
        restart = self.tool_get("system_restart", True)
        path = os.path.join(self.loop_path, "b.py")
        missing = _text_get("engine_system_main_loop_missing")
        with unittest.mock.patch(_EXEC_TARGET) as execv:
            self.raise_check(
                FileNotFoundError,
                missing.replace("{0}", path),
                lambda: restart({"main_loop": "b.py"}),
            )
        execv.assert_not_called()
        invalid = _text_get("engine_system_argument_invalid_main_loop")
        refused: tuple[dict[str, Any], ...] = ({}, {"main_loop": 5})
        for arguments in refused:
            with self.subTest(arguments=arguments):
                with unittest.mock.patch(_EXEC_TARGET) as execv:
                    self.params_check(invalid, lambda: restart(arguments))
                execv.assert_not_called()


# Tests the registration.
class TestRegister(IsolatedCase):
    # Each handler is registered once, under its type at version 0.
    def test_handlers_registered(self) -> None:
        engine_system.handlers_register(self.root, True)
        expected = [
            ("settings.put", 0, engine_system.settings_put),
            ("source.put", 0, engine_system.source_put),
            ("system.restart", 0, engine_system.system_restart),
        ]
        self.assertEqual(self.handlers, expected)

    # Called before the registration each handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.settings_put")
        message = _text_get("engine_system_not_registered")
        uses: list[Callable[[], object]] = [
            lambda: engine_system.settings_put(line, settings={}),
            lambda: engine_system.source_put(line, name="a.py"),
            lambda: engine_system.system_restart(line, main_loop="b.py"),
        ]
        for use in uses:
            self.raise_check(RuntimeError, message, use)
