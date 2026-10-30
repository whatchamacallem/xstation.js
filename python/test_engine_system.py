# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the handlers of `settings.put`, `source.put` and `system.restart`
# and the two tools of the same names, each in a forked child: the handlers
# registered with the real dispatcher on a scratch root in `build/`, and the
# tools on a real MCP server and called through it, so the root, the debug
# setting and the handlers never reach another test. Each handler is called
# as the dispatcher calls it on lines of the gold, a blob's `d` the bytes or
# the path of a file the decoder would have streamed. The settings file is
# rewritten whole, a main loop file is written from bytes or moved from the
# streamed file, and its name is refused unless plain. The refusals of the
# restart run in a child that a restart would replace, so its ending shows
# the process kept; the exec itself runs only in a whole program. Debug mode
# gates all of them. The settings check holds the types of every table, the
# PowerShell constants' among them. The tools are those of the API file, and
# a tool's exception is the one the server keeps. The registration is read
# from the dispatcher, which refuses a second one of each type. Each child
# writes how its work ended to a file, or to stderr when that write fails,
# then kills itself.

import engine_system, functools, harness, hashlib, json, os, re, signal, sys
import tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any, cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_engine_system"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# The text of a main loop file.
_SOURCE_TEXT = "print('main loop')\n"

# The `JSON-RPC` code of arguments that a tool cannot use.
_CODE_PARAMS = -32602

# The name and the version of the server the tools are registered on.
_SERVER_NAME = "xsjs-server"
_SERVER_VERSION = "0"

# The request that lists the tools of a server.
_LIST_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
}

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

# The types the handlers are registered under, each with its gold text's case.
_HANDLER_TYPES = (
    ("settings.put", "settings"),
    ("source.put", "source"),
    ("system.restart", "restart"),
)

# The file in the scratch directory that a child writes how it ended to.
_ENDING_NAME = "ending.json"


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


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


# The request that calls a tool on the arguments.
def _call_message(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


# What a server kept of a tool's exception: type, text, an `RpcError`'s code.
def _failure_read(failure: BaseException | None) -> object:
    if failure is None:
        return None
    read: list[object] = [type(failure).__name__, str(failure)]
    if isinstance(failure, engine_system.mcp.RpcError):
        read.append(failure.code)
    return read


# A new server with the tools registered for the root and the debug setting.
def _tools_server(root: str, debug: bool) -> engine_system.mcp.Server:
    server = engine_system.mcp.Server(_SERVER_NAME, _SERVER_VERSION)
    engine_system.tools_register(server, root, debug)
    return server


# The work of a child: registers the handlers, then calls one on the line.
def _handler_run(
    root: str, debug: bool, fn: Callable[..., Any], line: dict[int | str, Any]
) -> Any:
    engine_system.handlers_register(root, debug)
    return _handler_call(fn, line)


# The work of a child: lists the tools of a new server, returns the response.
def _tools_list(root: str, debug: bool) -> object:
    return _tools_server(root, debug).message_handle(_LIST_MESSAGE)


# In a child: calls a new server's tool, returns the response, kept exception.
def _tool_run(
    root: str, debug: bool, name: str, arguments: dict[str, Any]
) -> list[object]:
    server = _tools_server(root, debug)
    response = server.message_handle(_call_message(name, arguments))
    return [response, _failure_read(server.failure_take())]


# The work of a child: registers the handlers, then a handler's type again.
def _register_twice(root: str, name: str) -> None:
    engine_system.handlers_register(root, True)
    engine_system.dispatch.handler_register(
        name, 0, engine_system.settings_put
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
        self.settings_path = os.path.join(self.root, "settings.json")
        self.loop_path = os.path.join(self.root, "main_loop")
        self.file_path = os.path.join(self.loop_path, "a.py")

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

    # Registers in a child, calls a handler on a line, returns its reply.
    def handler_value(
        self, fn: Callable[..., Any], debug: bool, line: dict[int | str, Any]
    ) -> Any:
        work = functools.partial(_handler_run, self.root, debug, fn, line)
        return self.child_value(work)

    # Registers in a child, calls a handler on a line, checks what it raised.
    def handler_raise(
        self,
        fn: Callable[..., Any],
        debug: bool,
        line: dict[int | str, Any],
        kind: type[BaseException],
        message: str,
    ) -> None:
        work = functools.partial(_handler_run, self.root, debug, fn, line)
        self.child_raise(work, kind, message)

    # Calls a tool in a child and checks it failed, its exception as read.
    def tool_failed(
        self,
        debug: bool,
        name: str,
        arguments: dict[str, Any],
        failure: list[object],
    ) -> None:
        work = functools.partial(_tool_run, self.root, debug, name, arguments)
        response, kept = self.child_value(work)
        self.assertIs(response["result"]["isError"], True)
        self.assertEqual(kept, failure)


# Tests the handler of `settings.put`.
class TestSettings(ScratchCase):
    # The file is the settings object written whole, and no file is left over.
    def test_settings_written(self) -> None:
        value = harness.settings_copy()
        line = _line_set("settings_put", "settings", value)
        reply = self.handler_value(engine_system.settings_put, True, line)
        self.assertEqual(reply, _gold_raw("lines.settings_reply"))
        with open(self.settings_path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written, value)
        self.assertEqual(list(written), list(value))
        self.assertEqual(os.listdir(self.root), ["settings.json"])

    # A changed value is in the file, and the file replaces the old one.
    def test_settings_replaced(self) -> None:
        with open(self.settings_path, "w", encoding="utf-8") as file:
            file.write("old\n")
        changed = harness.settings_copy()
        changed["debug"] = False
        changed["provider"]["scripted"] = False
        line = _line_set("settings_put", "settings", changed)
        self.handler_value(engine_system.settings_put, True, line)
        with open(self.settings_path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written, changed)
        self.assertEqual(list(written), list(changed))
        self.assertEqual(os.listdir(self.root), ["settings.json"])

    # A nested provider of the type the decoder makes is kept.
    def test_provider_object(self) -> None:
        changed = harness.settings_copy()
        provider = engine_system.jslb.Object(changed["provider"])
        provider["timeout_seconds"] = 60
        changed["provider"] = provider
        line = _line_set("settings_put", "settings", changed)
        self.handler_value(engine_system.settings_put, True, line)
        with open(self.settings_path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written["provider"], provider)

    # Settings that fail the check raise and the old file stays as it was.
    def test_settings_invalid(self) -> None:
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
                self.handler_raise(
                    engine_system.settings_put,
                    True,
                    line,
                    ValueError,
                    _text_get(name),
                )
                self.assertEqual(_file_read(self.settings_path), b"old\n")
                self.assertEqual(os.listdir(self.root), ["settings.json"])

    # With debug mode off the handler raises and writes nothing.
    def test_settings_gated(self) -> None:
        line = _line_set("settings_put", "settings", harness.settings_copy())
        self.handler_raise(
            engine_system.settings_put,
            False,
            line,
            RuntimeError,
            _text_get("engine_system_debug_off_settings"),
        )
        self.assertEqual(os.listdir(self.root), [])


# Tests the handler of `source.put`.
class TestSource(ScratchCase):
    # A blob in memory is written as the file, and the reply is its `sha256`.
    def test_bytes_written(self) -> None:
        data = _SOURCE_TEXT.encode("utf-8")
        line = _blob_line("source_put", data)
        reply = self.handler_value(engine_system.source_put, True, line)
        digest = hashlib.sha256(data).hexdigest()
        expected = {**_gold_raw("lines.source_reply"), "sha256": digest}
        self.assertEqual(reply, expected)
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), data)

    # A blob the decoder streamed to the cache is moved into place.
    def test_blob_streamed(self) -> None:
        cache = os.path.join(self.root, "cache")
        os.makedirs(cache)
        source = os.path.join(cache, "blob")
        data = _SOURCE_TEXT.encode("utf-8")
        line = _streamed_line("source_put", source, data)
        reply = self.handler_value(engine_system.source_put, True, line)
        digest = hashlib.sha256(data).hexdigest()
        expected = {**_gold_raw("lines.source_reply"), "sha256": digest}
        self.assertEqual(reply, expected)
        self.assertFalse(os.path.exists(source))
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), data)

    # A second write under the same name replaces the file.
    def test_file_replaced(self) -> None:
        _loop_write(self.root, "a.py")
        line = _blob_line("source_put", b"new\n")
        self.handler_value(engine_system.source_put, True, line)
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), b"new\n")

    # A name that is not plain raises and nothing is written.
    def test_name_invalid(self) -> None:
        for name, text in _NAMES_INVALID:
            with self.subTest(name=name):
                line = _blob_line("source_put", b"x")
                line["name"] = name
                self.handler_raise(
                    engine_system.source_put,
                    True,
                    line,
                    ValueError,
                    _text_get(text),
                )
                self.assertEqual(os.listdir(self.root), [])

    # A streamed blob under a name that is not plain stays in the cache.
    def test_streamed_refused(self) -> None:
        source = os.path.join(self.root, "blob")
        line = _streamed_line("source_put", source, b"x")
        line["name"] = "../a.py"
        self.handler_raise(
            engine_system.source_put,
            True,
            line,
            ValueError,
            _text_get("engine_system_name_invalid_parent_a"),
        )
        self.assertEqual(os.listdir(self.root), ["blob"])

    # A line with no blob raises and nothing is written.
    def test_blob_missing(self) -> None:
        self.handler_raise(
            engine_system.source_put,
            True,
            _gold_value("lines.source_blobless"),
            ValueError,
            _text_get("engine_system_blob_missing"),
        )
        self.assertEqual(os.listdir(self.root), [])

    # With debug mode off the handler raises and writes nothing.
    def test_source_gated(self) -> None:
        self.handler_raise(
            engine_system.source_put,
            False,
            _blob_line("source_put", b"x"),
            RuntimeError,
            _text_get("engine_system_debug_off_source"),
        )
        self.assertEqual(os.listdir(self.root), [])


# Tests `system.restart` refusals in children whose endings show none replaced.
class TestRestart(ScratchCase):
    # A file that does not exist raises.
    def test_file_missing(self) -> None:
        os.makedirs(self.loop_path)
        os.makedirs(os.path.join(self.loop_path, "b.py"))
        missing = _text_get("engine_system_main_loop_missing")
        for name in ("a.py", "b.py"):
            with self.subTest(name=name):
                path = os.path.join(self.loop_path, name)
                self.handler_raise(
                    engine_system.system_restart,
                    True,
                    _line_set("restart", "main_loop", name),
                    FileNotFoundError,
                    missing.replace("{0}", path),
                )

    # A name that is not plain raises, even where a file of it exists.
    def test_name_invalid(self) -> None:
        _loop_write(self.root, "b.py")
        _loop_write(self.root, os.path.join("d", "b.py"))
        outside = os.path.join(self.root, "b.py")
        with open(outside, "w", encoding="utf-8") as file:
            file.write(_SOURCE_TEXT)
        for name, text in _NAMES_INVALID:
            with self.subTest(name=name):
                self.handler_raise(
                    engine_system.system_restart,
                    True,
                    _line_set("restart", "main_loop", name),
                    ValueError,
                    _text_get(text),
                )

    # With debug mode off the handler raises.
    def test_restart_gated(self) -> None:
        _loop_write(self.root, "b.py")
        self.handler_raise(
            engine_system.system_restart,
            False,
            _gold_value("lines.restart"),
            RuntimeError,
            _text_get("engine_system_debug_off_restart"),
        )


# Tests the two tools, registered on a real server and called through it.
class TestTools(ScratchCase):
    # The tools listed are the server side of the API file, key for key.
    def test_tools_listed(self) -> None:
        work = functools.partial(_tools_list, self.root, True)
        tools = self.child_value(work)["result"]["tools"]
        self.assertEqual(json.dumps(tools), json.dumps(_entries_read()))

    # Neither tool is registered with a permit, so no client asks for one.
    def test_permit_absent(self) -> None:
        work = functools.partial(_tools_list, self.root, True)
        tools = self.child_value(work)["result"]["tools"]
        self.assertEqual(
            [(tool["name"], "_meta" in tool) for tool in tools],
            [("source_put", False), ("system_restart", False)],
        )

    # The source tool writes the text as the file and answers its `sha256`.
    def test_source_tool(self) -> None:
        arguments = {"name": "a.py", "text": _SOURCE_TEXT}
        work = functools.partial(
            _tool_run, self.root, True, "source_put", arguments
        )
        response, failure = self.child_value(work)
        self.assertIsNone(failure)
        result = response["result"]
        self.assertIs(result["isError"], False)
        (block,) = result["content"]
        self.assertEqual(block["type"], "text")
        digest = hashlib.sha256(_SOURCE_TEXT.encode("utf-8")).hexdigest()
        self.assertEqual(json.loads(block["text"]), {"sha256": digest})
        written = _file_read(self.file_path)
        self.assertEqual(written, _SOURCE_TEXT.encode("utf-8"))

    # With debug mode off the source tool raises and writes nothing.
    def test_source_gated(self) -> None:
        arguments = {"name": "a.py", "text": _SOURCE_TEXT}
        message = _text_get("engine_system_debug_off_source_tool")
        failure: list[object] = [RuntimeError.__name__, message]
        self.tool_failed(False, "source_put", arguments, failure)
        self.assertEqual(os.listdir(self.root), [])

    # Arguments that are missing or not text are refused with their code.
    def test_source_arguments(self) -> None:
        text_invalid = "engine_system_argument_invalid_text"
        name_invalid = "engine_system_argument_invalid_name"
        bad: list[tuple[dict[str, Any], str]] = [
            ({"name": "a.py"}, text_invalid),
            ({"text": "x"}, name_invalid),
            ({"name": 5, "text": "x"}, name_invalid),
            ({"name": "a.py", "text": None}, text_invalid),
        ]
        kind = engine_system.mcp.RpcError.__name__
        for arguments, text in bad:
            with self.subTest(arguments=arguments):
                failure: list[object] = [kind, _text_get(text), _CODE_PARAMS]
                self.tool_failed(True, "source_put", arguments, failure)
        self.assertEqual(os.listdir(self.root), [])

    # A name that is not plain raises as any exception of a tool does.
    def test_source_name(self) -> None:
        arguments = {"name": "../a.py", "text": "x"}
        message = _text_get("engine_system_name_invalid_parent_a")
        failure: list[object] = [ValueError.__name__, message]
        self.tool_failed(True, "source_put", arguments, failure)
        self.assertEqual(os.listdir(self.root), [])

    # With debug mode off the restart tool raises, in a child it would replace.
    def test_restart_gated(self) -> None:
        _loop_write(self.root, "b.py")
        message = _text_get("engine_system_debug_off_restart_tool")
        failure: list[object] = [RuntimeError.__name__, message]
        arguments = {"main_loop": "b.py"}
        self.tool_failed(False, "system_restart", arguments, failure)

    # A missing file or a missing argument raises, in a child it would replace.
    def test_restart_refused(self) -> None:
        path = os.path.join(self.loop_path, "b.py")
        missing = _text_get("engine_system_main_loop_missing")
        failure: list[object] = [
            FileNotFoundError.__name__,
            missing.replace("{0}", path),
        ]
        arguments: dict[str, Any] = {"main_loop": "b.py"}
        self.tool_failed(True, "system_restart", arguments, failure)
        invalid = _text_get("engine_system_argument_invalid_main_loop")
        kind = engine_system.mcp.RpcError.__name__
        refused: tuple[dict[str, Any], ...] = ({}, {"main_loop": 5})
        for arguments in refused:
            with self.subTest(arguments=arguments):
                failure = [kind, invalid, _CODE_PARAMS]
                self.tool_failed(True, "system_restart", arguments, failure)


# Tests the registration.
class TestRegister(ScratchCase):
    # Each handler is registered under its type at version 0, a repeat refused.
    def test_handlers_registered(self) -> None:
        for name, case in _HANDLER_TYPES:
            with self.subTest(name=name):
                self.child_raise(
                    functools.partial(_register_twice, self.root, name),
                    ValueError,
                    _text_get(f"dispatch_handler_twice_{case}"),
                )

    # Called before the registration each handler raises.
    def test_called_early(self) -> None:
        line = _gold_value("lines.settings_put")
        message = _text_get("engine_system_not_registered")
        uses: list[Callable[[], object]] = [
            functools.partial(engine_system.settings_put, line, settings={}),
            functools.partial(engine_system.source_put, line, name="a.py"),
            functools.partial(
                engine_system.system_restart, line, main_loop="b.py"
            ),
        ]
        for use in uses:
            self.child_raise(use, RuntimeError, message)
