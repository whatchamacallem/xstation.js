# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `settings.put`, `source.put` and `system.restart` through the
# dispatcher and the two tools of the same names on an MCP server: the
# settings file rewritten whole, a main loop file written from a blob in
# memory or one streamed to the cache, its name refused unless plain, and the
# arguments of the restart up to the call of `os.execv`, which is patched.
# Debug mode gates all of them. The scratch directories go under `build/`.

import dispatch, engine_system, hashlib, io, jslb, json, mcp, os, sys, tempfile
import unittest, unittest.mock
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The settings file of the checkout, which holds a valid settings object.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The dotted name of the handler table that the tests patch.
_HANDLERS_TARGET = "dispatch._HANDLERS"

# The dotted name of the root that the tests patch.
_ROOT_TARGET = "engine_system._STATE.root"

# The dotted name of the debug setting that the tests patch.
_DEBUG_TARGET = "engine_system._STATE.debug"

# The dotted name of the call that replaces the process image.
_EXEC_TARGET = "os.execv"

# The dotted name of the arguments the process was started with.
_ARGV_TARGET = "sys.orig_argv"

# The dotted name of the standard output.
_STDOUT_TARGET = "sys.stdout"

# The dotted name of the standard error.
_STDERR_TARGET = "sys.stderr"

# The arguments of a process that was started with no main loop option.
_PROGRAM_ARGV = ["python3", "-X", "dev", "/r/bootstrap.py", "--root", "/r"]

# The text of a main loop file.
_SOURCE_TEXT = "print('main loop')\n"

# The `JSON-RPC` code of arguments that a tool cannot use.
_CODE_PARAMS = -32602

# The `JSON-RPC` code of an exception that a tool raised.
_CODE_INTERNAL = -32603

# Names that are not plain file names that end in `.py`.
_NAMES_INVALID = ("", "b", "b.txt", ".b.py", ".py", "d/b.py", "../b.py")


# Builds a line: the type, an optional id, the blobs and the payload.
def _line_make(
    name: str,
    request_id: int | None = None,
    blobs: list[jslb.Object] | None = None,
    **payload: Any,
) -> jslb.Object:
    header = jslb.header_make(name, id=request_id)
    return jslb.line_make(header, [] if blobs is None else blobs, **payload)


# Dispatches a line that must be answered and returns the reply.
def _reply_get(line: jslb.Object) -> jslb.Object:
    reply = dispatch.line_dispatch(line)
    if reply is None:
        raise AssertionError("the line was not answered")
    return reply


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# Reads the settings file of the checkout as an object.
def _settings_read() -> dict[str, Any]:
    with open(_SETTINGS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data


# Reads the tool entries of the server side of the API file.
def _entries_read() -> list[dict[str, Any]]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data["server"]["result"]["tools"]


# Writes a main loop file in the root, with its directory.
def _main_loop_write(root: str, name: str) -> str:
    path = os.path.join(root, "main_loop", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(_SOURCE_TEXT)
    return path


# Builds a `tools/call` request for a tool.
def _call_make(name: str, arguments: dict[str, Any]) -> mcp.Message:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


# Sends a message to the server and returns the response it must give.
def _response_get(server: mcp.Server, message: mcp.Message) -> mcp.Message:
    response = server.message_handle(message)
    if response is None:
        raise AssertionError("the message was not answered")
    return response


# Stands for the end of the process, which a successful exec causes.
class ExecCalled(BaseException):
    pass


# A text stream that counts its flushes.
class FlushCounter(io.StringIO):
    # Starts with no flushes.
    def __init__(self) -> None:
        super().__init__()
        self.flushes = 0

    # Counts the flush, then does it.
    def flush(self) -> None:
        self.flushes += 1
        super().flush()


# Gives each test an empty handler table, no registration and a scratch root.
class IsolatedCase(unittest.TestCase):
    # Patches the table and the state, makes a scratch root in `build/`.
    def setUp(self) -> None:
        table = unittest.mock.patch.dict(_HANDLERS_TARGET, {}, clear=True)
        root_state = unittest.mock.patch(_ROOT_TARGET, None)
        debug_state = unittest.mock.patch(_DEBUG_TARGET, None)
        for patcher in (table, root_state, debug_state):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name
        self.settings_path = os.path.join(self.root, "settings.json")
        self.loop_path = os.path.join(self.root, "main_loop")
        self.file_path = os.path.join(self.loop_path, "a.py")


# Tests the handler of `settings.put`.
class TestSettings(IsolatedCase):
    # The file is the settings object written whole, and no file is left over.
    def test_settings_written(self) -> None:
        engine_system.handlers_register(self.root, True)
        line = _line_make("settings.put", 3, settings=_settings_read())
        reply = _reply_get(line)
        self.assertEqual(reply[0]["r"], 3)
        self.assertEqual(jslb.payload_of(reply), {})
        written = _file_read(self.settings_path)
        self.assertEqual(written, _file_read(_SETTINGS_PATH))
        self.assertEqual(os.listdir(self.root), ["settings.json"])

    # A changed value is in the file, and the file replaces the old one.
    def test_settings_replaced(self) -> None:
        engine_system.handlers_register(self.root, True)
        with open(self.settings_path, "w", encoding="utf-8") as file:
            file.write("old\n")
        changed = _settings_read()
        changed["debug"] = False
        changed["provider"]["chat_model"] = "other"
        _reply_get(_line_make("settings.put", 1, settings=changed))
        with open(self.settings_path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written, changed)
        self.assertEqual(list(written), list(changed))
        self.assertEqual(os.listdir(self.root), ["settings.json"])

    # Settings that fail the check raise and the old file stays as it was.
    def test_settings_invalid(self) -> None:
        engine_system.handlers_register(self.root, True)
        with open(self.settings_path, "w", encoding="utf-8") as file:
            file.write("old\n")
        missing = _settings_read()
        del missing["line_max"]
        extra = _settings_read()
        extra["other"] = 1
        wrong = _settings_read()
        wrong["provider"]["timeout_seconds"] = "120"
        for bad in (missing, extra, wrong):
            with self.subTest(bad=bad):
                line = _line_make("settings.put", 1, settings=bad)
                with self.assertRaises(ValueError):
                    dispatch.line_dispatch(line)
                self.assertEqual(_file_read(self.settings_path), b"old\n")
                self.assertEqual(os.listdir(self.root), ["settings.json"])

    # With debug mode off the handler raises and writes nothing.
    def test_settings_gated(self) -> None:
        engine_system.handlers_register(self.root, False)
        line = _line_make("settings.put", 1, settings=_settings_read())
        with self.assertRaises(RuntimeError):
            dispatch.line_dispatch(line)
        self.assertEqual(os.listdir(self.root), [])


# Tests the handler of `source.put`.
class TestSource(IsolatedCase):
    # A blob in memory is written as the file, and the reply is its `sha256`.
    def test_bytes_written(self) -> None:
        engine_system.handlers_register(self.root, True)
        data = _SOURCE_TEXT.encode("utf-8")
        blob = jslb.blob_make(data)
        reply = _reply_get(_line_make("source.put", 4, [blob], name="a.py"))
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual(reply[0]["r"], 4)
        self.assertEqual(jslb.payload_of(reply), {"sha256": digest})
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), data)

    # A blob streamed to the cache is moved into place with the hash it has.
    def test_blob_streamed(self) -> None:
        engine_system.handlers_register(self.root, True)
        cache = os.path.join(self.root, "cache")
        os.makedirs(cache)
        source = os.path.join(cache, "blob")
        data = _SOURCE_TEXT.encode("utf-8")
        with open(source, "wb") as file:
            file.write(data)
        digest = hashlib.sha256(data).hexdigest()
        blob = jslb.blob_make(source, sha256=digest)
        reply = _reply_get(_line_make("source.put", 4, [blob], name="a.py"))
        self.assertEqual(jslb.payload_of(reply), {"sha256": digest})
        self.assertFalse(os.path.exists(source))
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), data)

    # A second write under the same name replaces the file.
    def test_file_replaced(self) -> None:
        engine_system.handlers_register(self.root, True)
        _main_loop_write(self.root, "a.py")
        blob = jslb.blob_make(b"new\n")
        _reply_get(_line_make("source.put", 1, [blob], name="a.py"))
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), b"new\n")

    # A name that is not plain raises and nothing is written.
    def test_name_invalid(self) -> None:
        engine_system.handlers_register(self.root, True)
        for name in _NAMES_INVALID:
            with self.subTest(name=name):
                blob = jslb.blob_make(b"x")
                line = _line_make("source.put", 1, [blob], name=name)
                with self.assertRaises(ValueError):
                    dispatch.line_dispatch(line)
                self.assertEqual(os.listdir(self.root), [])

    # A streamed blob under a name that is not plain stays in the cache.
    def test_streamed_refused(self) -> None:
        engine_system.handlers_register(self.root, True)
        source = os.path.join(self.root, "blob")
        with open(source, "wb") as file:
            file.write(b"x")
        blob = jslb.blob_make(source, sha256=hashlib.sha256(b"x").hexdigest())
        line = _line_make("source.put", 1, [blob], name="../a.py")
        with self.assertRaises(ValueError):
            dispatch.line_dispatch(line)
        self.assertEqual(os.listdir(self.root), ["blob"])

    # A line with no blob raises.
    def test_blob_missing(self) -> None:
        engine_system.handlers_register(self.root, True)
        line = _line_make("source.put", 1, name="a.py")
        with self.assertRaises(KeyError):
            dispatch.line_dispatch(line)
        self.assertEqual(os.listdir(self.root), [])

    # With debug mode off the handler raises and writes nothing.
    def test_source_gated(self) -> None:
        engine_system.handlers_register(self.root, False)
        blob = jslb.blob_make(b"x")
        line = _line_make("source.put", 1, [blob], name="a.py")
        with self.assertRaises(RuntimeError):
            dispatch.line_dispatch(line)
        self.assertEqual(os.listdir(self.root), [])


# Tests the handler of `system.restart` up to the call that replaces the image.
class TestRestart(IsolatedCase):
    # The call gets the interpreter and the arguments with the option last.
    def test_exec_argv(self) -> None:
        engine_system.handlers_register(self.root, True)
        _main_loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        with (
            unittest.mock.patch(_EXEC_TARGET, side_effect=ExecCalled) as execv,
            unittest.mock.patch(_ARGV_TARGET, _PROGRAM_ARGV),
            self.assertRaises(ExecCalled),
        ):
            dispatch.line_dispatch(line)
        expected = _PROGRAM_ARGV + ["--main-loop", "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # An option the process already had is removed with its value.
    def test_option_replaced(self) -> None:
        engine_system.handlers_register(self.root, True)
        _main_loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        argv = _PROGRAM_ARGV + ["--main-loop", "a.py", "--other"]
        with (
            unittest.mock.patch(_EXEC_TARGET, side_effect=ExecCalled) as execv,
            unittest.mock.patch(_ARGV_TARGET, argv),
            self.assertRaises(ExecCalled),
        ):
            dispatch.line_dispatch(line)
        expected = _PROGRAM_ARGV + ["--other", "--main-loop", "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # An option with no value raises and the process is not replaced.
    def test_option_unfinished(self) -> None:
        engine_system.handlers_register(self.root, True)
        _main_loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        with (
            unittest.mock.patch(_EXEC_TARGET, side_effect=ExecCalled) as execv,
            unittest.mock.patch(_ARGV_TARGET, _PROGRAM_ARGV + ["--main-loop"]),
            self.assertRaises(ValueError),
        ):
            dispatch.line_dispatch(line)
        execv.assert_not_called()

    # Both streams are flushed before the call.
    def test_flushed(self) -> None:
        engine_system.handlers_register(self.root, True)
        _main_loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        out = FlushCounter()
        err = FlushCounter()
        with (
            unittest.mock.patch(_EXEC_TARGET, side_effect=ExecCalled),
            unittest.mock.patch(_ARGV_TARGET, _PROGRAM_ARGV),
            unittest.mock.patch(_STDOUT_TARGET, out),
            unittest.mock.patch(_STDERR_TARGET, err),
            self.assertRaises(ExecCalled),
        ):
            dispatch.line_dispatch(line)
        self.assertEqual((out.flushes, err.flushes), (1, 1))

    # A file that does not exist raises and the process is not replaced.
    def test_file_missing(self) -> None:
        engine_system.handlers_register(self.root, True)
        os.makedirs(self.loop_path)
        os.makedirs(os.path.join(self.loop_path, "b.py"))
        for name in ("a.py", "b.py"):
            with self.subTest(name=name):
                line = _line_make("system.restart", main_loop=name)
                with (
                    unittest.mock.patch(_EXEC_TARGET) as execv,
                    self.assertRaises(FileNotFoundError),
                ):
                    dispatch.line_dispatch(line)
                execv.assert_not_called()

    # A name that is not plain raises, even where a file of it exists.
    def test_name_invalid(self) -> None:
        engine_system.handlers_register(self.root, True)
        _main_loop_write(self.root, "b.py")
        _main_loop_write(self.root, os.path.join("d", "b.py"))
        outside = os.path.join(self.root, "b.py")
        with open(outside, "w", encoding="utf-8") as file:
            file.write(_SOURCE_TEXT)
        for name in _NAMES_INVALID:
            with self.subTest(name=name):
                line = _line_make("system.restart", main_loop=name)
                with (
                    unittest.mock.patch(_EXEC_TARGET) as execv,
                    self.assertRaises(ValueError),
                ):
                    dispatch.line_dispatch(line)
                execv.assert_not_called()

    # With debug mode off the handler raises and the process is not replaced.
    def test_restart_gated(self) -> None:
        engine_system.handlers_register(self.root, False)
        _main_loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        with (
            unittest.mock.patch(_EXEC_TARGET) as execv,
            self.assertRaises(RuntimeError),
        ):
            dispatch.line_dispatch(line)
        execv.assert_not_called()


# Tests the two tools on an MCP server.
class TestTools(IsolatedCase):
    # Makes an MCP server with the tools, for the debug setting.
    def server_make(self, debug: bool) -> mcp.Server:
        server = mcp.Server("xsjs-server", "0")
        engine_system.tools_register(server, self.root, debug)
        return server

    # The list is the server side of the API file, key for key.
    def test_tools_listed(self) -> None:
        server = self.server_make(True)
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        listed = _response_get(server, request)["result"]["tools"]
        self.assertEqual(json.dumps(listed), json.dumps(_entries_read()))

    # A second registration on one server raises.
    def test_tools_twice(self) -> None:
        server = self.server_make(True)
        with self.assertRaises(ValueError):
            engine_system.tools_register(server, self.root, True)

    # The source tool writes the text as the file and answers its `sha256`.
    def test_source_tool(self) -> None:
        server = self.server_make(True)
        call = _call_make("source_put", {"name": "a.py", "text": _SOURCE_TEXT})
        result = _response_get(server, call)["result"]
        digest = hashlib.sha256(_SOURCE_TEXT.encode("utf-8")).hexdigest()
        self.assertFalse(result["isError"])
        (block,) = result["content"]
        self.assertEqual(block["type"], "text")
        self.assertEqual(json.loads(block["text"]), {"sha256": digest})
        written = _file_read(self.file_path)
        self.assertEqual(written, _SOURCE_TEXT.encode("utf-8"))

    # With debug mode off the source tool raises and writes nothing.
    def test_source_gated(self) -> None:
        server = self.server_make(False)
        call = _call_make("source_put", {"name": "a.py", "text": _SOURCE_TEXT})
        response = _response_get(server, call)
        self.assertEqual(response["error"]["code"], _CODE_INTERNAL)
        self.assertEqual(os.listdir(self.root), [])

    # Arguments that are missing or not text are refused with their code.
    def test_source_arguments(self) -> None:
        server = self.server_make(True)
        bad: list[dict[str, Any]] = [
            {"name": "a.py"},
            {"text": "x"},
            {"name": 5, "text": "x"},
            {"name": "a.py", "text": None},
        ]
        for arguments in bad:
            with self.subTest(arguments=arguments):
                response = _response_get(
                    server, _call_make("source_put", arguments)
                )
                self.assertEqual(response["error"]["code"], _CODE_PARAMS)
        self.assertEqual(os.listdir(self.root), [])

    # A name that is not plain raises as any exception of a tool does.
    def test_source_name(self) -> None:
        server = self.server_make(True)
        call = _call_make("source_put", {"name": "../a.py", "text": "x"})
        response = _response_get(server, call)
        self.assertEqual(response["error"]["code"], _CODE_INTERNAL)
        self.assertEqual(os.listdir(self.root), [])

    # The restart tool replaces the process image as the handler does.
    def test_restart_tool(self) -> None:
        server = self.server_make(True)
        _main_loop_write(self.root, "b.py")
        call = _call_make("system_restart", {"main_loop": "b.py"})
        with (
            unittest.mock.patch(_EXEC_TARGET, side_effect=ExecCalled) as execv,
            unittest.mock.patch(_ARGV_TARGET, _PROGRAM_ARGV),
            self.assertRaises(ExecCalled),
        ):
            server.message_handle(call)
        expected = _PROGRAM_ARGV + ["--main-loop", "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # With debug mode off the restart tool raises and nothing is replaced.
    def test_restart_gated(self) -> None:
        server = self.server_make(False)
        _main_loop_write(self.root, "b.py")
        call = _call_make("system_restart", {"main_loop": "b.py"})
        with unittest.mock.patch(_EXEC_TARGET) as execv:
            response = _response_get(server, call)
        self.assertEqual(response["error"]["code"], _CODE_INTERNAL)
        execv.assert_not_called()

    # A missing file or a missing argument is an error and nothing is replaced.
    def test_restart_refused(self) -> None:
        server = self.server_make(True)
        cases: tuple[tuple[dict[str, Any], int], ...] = (
            ({"main_loop": "b.py"}, _CODE_INTERNAL),
            ({}, _CODE_PARAMS),
            ({"main_loop": 5}, _CODE_PARAMS),
        )
        for arguments, code in cases:
            with self.subTest(arguments=arguments):
                call = _call_make("system_restart", arguments)
                with unittest.mock.patch(_EXEC_TARGET) as execv:
                    response = _response_get(server, call)
                self.assertEqual(response["error"]["code"], code)
                execv.assert_not_called()


# Tests the registration.
class TestRegister(IsolatedCase):
    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_system.handlers_register(self.root, True)
        with self.assertRaises(ValueError):
            engine_system.handlers_register(self.root, True)

    # Called before the registration each handler raises.
    def test_unregistered(self) -> None:
        line = _line_make("settings.put")
        with self.assertRaises(RuntimeError):
            engine_system.settings_put(line, settings={})
        with self.assertRaises(RuntimeError):
            engine_system.source_put(line, name="a.py")
        with self.assertRaises(RuntimeError):
            engine_system.system_restart(line, main_loop="b.py")
