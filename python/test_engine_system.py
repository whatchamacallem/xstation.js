# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests `settings.put`, `source.put` and `system.restart` through the
# dispatcher and the two tools of the same names on an MCP server. Each line
# is encoded and decoded as the wire carries it, so a nested object arrives as
# the decoder makes it. The settings file is rewritten whole, a main loop file
# is written from a blob in memory or from one the decoder streamed to the
# cache, its name is refused unless plain, and the arguments of the restart
# are checked up to the call of `os.execv`, which is patched. Debug mode gates
# all of them. The scratch directories go under `build/`.

import dispatch, engine_system, hashlib, jslb, json, mcp, os, sys, tempfile
import unittest, unittest.mock
from collections.abc import Callable
from i18n import i18n
from typing import Any, cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The settings file of the checkout, which holds a valid settings object.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The longest line the test decoder takes, the size of the setting.
_LINE_MAX = 1048576

# The most bytes the blobs of a message come to, the size of the setting.
_BLOB_MAX = 2147483391

# The size above which the test decoder streams a blob, from the setting.
_OVERFLOW_BYTES = 131072

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

# The process option that names the main loop file.
_MAIN_LOOP_OPTION = "--main-loop"

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

# Forms of the option and its value that argparse reads as `--main-loop`.
_OPTION_FORMS: tuple[list[str], ...] = (
    ["--main-loop=a.py"],
    ["--main", "a.py"],
    ["--m=a.py"],
    ["--main-loo", "a.py"],
)

# No overflow bytes, so the decoder streams every blob, its writer's choice.
_OVERFLOW_NONE = 0


# Reads a file with a handle of its own.
def _file_read(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()


# Stands for the sink of a decoder whose blobs all stay in memory.
def _sink_refuse(header: jslb.Object) -> str:
    raise AssertionError("a blob was streamed")


# Encodes the line and decodes it as the server does, with the sink given.
def _wire_pass(
    line: jslb.Object,
    overflow_bytes: int,
    sink_make: Callable[[jslb.Object], str],
) -> jslb.Object:
    data = b"".join(cast(bytes, piece) for piece in jslb.line_encode(line))
    decoder = jslb.LineDecoder(_LINE_MAX, _BLOB_MAX, overflow_bytes, sink_make)
    (decoded,) = decoder.bytes_feed(data)
    return decoded


# Builds a line, then passes it through the wire with its blobs in memory.
def _line_make(
    name: str,
    request_id: int | None = None,
    blobs: tuple[jslb.Object, ...] = (),
    **payload: Any,
) -> jslb.Object:
    header = jslb.header_make(name, id=request_id)
    line = jslb.line_make(header, list(blobs), **payload)
    return _wire_pass(line, _OVERFLOW_BYTES, _sink_refuse)


# Builds a `source.put` line whose blob the decoder streams to the path.
def _streamed_make(name: str, data: bytes, path: str) -> jslb.Object:
    header = jslb.header_make("source.put", id=4)
    line = jslb.line_make(header, [jslb.blob_make(data)], name=name)
    return _wire_pass(line, _OVERFLOW_NONE, lambda blob: path)


# Dispatches a line that must be answered and returns the reply.
def _reply_get(line: jslb.Object) -> jslb.Object:
    reply = dispatch.line_dispatch(line)
    if reply is None:
        raise AssertionError("the line was not answered")
    return reply


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
def _loop_write(root: str, name: str) -> str:
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


# Stands for the end of the process image, which a successful exec causes.
class ImageReplaced(BaseException):
    pass


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

    # Calls `fn` and checks the type and the text of what it raises.
    def raise_check(
        self, kind: type[Exception], message: str, fn: Callable[[], object]
    ) -> None:
        with self.assertRaises(kind) as caught:
            fn()
        self.assertEqual(str(caught.exception), message)

    # Dispatches a line and checks the type and the text of what it raises.
    def dispatch_check(
        self, kind: type[Exception], message: str, line: jslb.Object
    ) -> None:
        self.raise_check(kind, message, lambda: dispatch.line_dispatch(line))


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
        changed["provider"]["scripted"] = False
        _reply_get(_line_make("settings.put", 1, settings=changed))
        with open(self.settings_path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written, changed)
        self.assertEqual(list(written), list(changed))
        self.assertEqual(os.listdir(self.root), ["settings.json"])

    # The nested provider comes from the decoder as an `Object` and is kept.
    def test_provider_object(self) -> None:
        engine_system.handlers_register(self.root, True)
        changed = _settings_read()
        changed["provider"]["timeout_seconds"] = 60
        line = _line_make("settings.put", 2, settings=changed)
        self.assertIs(type(line["settings"]["provider"]), jslb.Object)
        _reply_get(line)
        with open(self.settings_path, encoding="utf-8") as file:
            written: dict[str, Any] = json.load(file)
        self.assertEqual(written["provider"], changed["provider"])

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
        cases: list[tuple[dict[str, Any], str]] = [
            (missing, i18n("settings.key_missing", "line_max")),
            (extra, i18n("settings.key_extra", "other")),
            (
                wrong,
                i18n(
                    "settings.type_wrong",
                    "provider.timeout_seconds",
                    "int",
                    "str",
                ),
            ),
        ]
        for bad, message in cases:
            with self.subTest(message=message):
                line = _line_make("settings.put", 1, settings=bad)
                self.dispatch_check(ValueError, message, line)
                self.assertEqual(_file_read(self.settings_path), b"old\n")
                self.assertEqual(os.listdir(self.root), ["settings.json"])

    # With debug mode off the handler raises and writes nothing.
    def test_settings_gated(self) -> None:
        engine_system.handlers_register(self.root, False)
        line = _line_make("settings.put", 1, settings=_settings_read())
        message = i18n("engine_system.debug_off", "settings.put")
        self.dispatch_check(RuntimeError, message, line)
        self.assertEqual(os.listdir(self.root), [])


# Tests the handler of `source.put`.
class TestSource(IsolatedCase):
    # A blob in memory is written as the file, and the reply is its `sha256`.
    def test_bytes_written(self) -> None:
        engine_system.handlers_register(self.root, True)
        data = _SOURCE_TEXT.encode("utf-8")
        blob = jslb.blob_make(data)
        reply = _reply_get(_line_make("source.put", 4, (blob,), name="a.py"))
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual(reply[0]["r"], 4)
        self.assertEqual(jslb.payload_of(reply), {"sha256": digest})
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), data)

    # A blob the decoder streamed to the cache is moved into place.
    def test_blob_streamed(self) -> None:
        engine_system.handlers_register(self.root, True)
        cache = os.path.join(self.root, "cache")
        os.makedirs(cache)
        source = os.path.join(cache, "blob")
        data = _SOURCE_TEXT.encode("utf-8")
        line = _streamed_make("a.py", data, source)
        self.assertEqual(line[1]["d"], source)
        reply = _reply_get(line)
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual(jslb.payload_of(reply), {"sha256": digest})
        self.assertFalse(os.path.exists(source))
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), data)

    # A second write under the same name replaces the file.
    def test_file_replaced(self) -> None:
        engine_system.handlers_register(self.root, True)
        _loop_write(self.root, "a.py")
        blob = jslb.blob_make(b"new\n")
        _reply_get(_line_make("source.put", 1, (blob,), name="a.py"))
        self.assertEqual(os.listdir(self.loop_path), ["a.py"])
        self.assertEqual(_file_read(self.file_path), b"new\n")

    # A name that is not plain raises and nothing is written.
    def test_name_invalid(self) -> None:
        engine_system.handlers_register(self.root, True)
        for name in _NAMES_INVALID:
            with self.subTest(name=name):
                blob = jslb.blob_make(b"x")
                line = _line_make("source.put", 1, (blob,), name=name)
                message = i18n("engine_system.name_invalid", name)
                self.dispatch_check(ValueError, message, line)
                self.assertEqual(os.listdir(self.root), [])

    # A streamed blob under a name that is not plain stays in the cache.
    def test_streamed_refused(self) -> None:
        engine_system.handlers_register(self.root, True)
        source = os.path.join(self.root, "blob")
        line = _streamed_make("../a.py", b"x", source)
        message = i18n("engine_system.name_invalid", "../a.py")
        self.dispatch_check(ValueError, message, line)
        self.assertEqual(os.listdir(self.root), ["blob"])

    # A line with no blob raises and nothing is written.
    def test_blob_missing(self) -> None:
        engine_system.handlers_register(self.root, True)
        line = _line_make("source.put", 1, name="a.py")
        message = i18n("engine_system.blob_missing")
        self.dispatch_check(ValueError, message, line)
        self.assertEqual(os.listdir(self.root), [])

    # With debug mode off the handler raises and writes nothing.
    def test_source_gated(self) -> None:
        engine_system.handlers_register(self.root, False)
        blob = jslb.blob_make(b"x")
        line = _line_make("source.put", 1, (blob,), name="a.py")
        message = i18n("engine_system.debug_off", "source.put")
        self.dispatch_check(RuntimeError, message, line)
        self.assertEqual(os.listdir(self.root), [])


# Tests the handler of `system.restart` up to the call that replaces the image.
class TestRestart(IsolatedCase):
    # The call gets the interpreter and the arguments with the option last.
    def test_exec_argv(self) -> None:
        engine_system.handlers_register(self.root, True)
        _loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        with (
            unittest.mock.patch(
                _EXEC_TARGET, side_effect=ImageReplaced
            ) as execv,
            unittest.mock.patch(_ARGV_TARGET, _PROGRAM_ARGV),
            self.assertRaises(ImageReplaced),
        ):
            dispatch.line_dispatch(line)
        expected = _PROGRAM_ARGV + [_MAIN_LOOP_OPTION, "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # An option the process already had is removed with its value.
    def test_option_replaced(self) -> None:
        engine_system.handlers_register(self.root, True)
        _loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        argv = _PROGRAM_ARGV + [_MAIN_LOOP_OPTION, "a.py", "--other"]
        with (
            unittest.mock.patch(
                _EXEC_TARGET, side_effect=ImageReplaced
            ) as execv,
            unittest.mock.patch(_ARGV_TARGET, argv),
            self.assertRaises(ImageReplaced),
        ):
            dispatch.line_dispatch(line)
        expected = _PROGRAM_ARGV + ["--other", _MAIN_LOOP_OPTION, "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # Each form of the option that argparse takes is removed with its value.
    def test_option_forms(self) -> None:
        engine_system.handlers_register(self.root, True)
        _loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
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
                    dispatch.line_dispatch(line)
                execv.assert_called_once_with(sys.executable, expected)

    # A word that only looks like the option is kept.
    def test_option_kept(self) -> None:
        engine_system.handlers_register(self.root, True)
        _loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        argv = _PROGRAM_ARGV + ["--mainloop", "--main-loops=a.py"]
        with (
            unittest.mock.patch(
                _EXEC_TARGET, side_effect=ImageReplaced
            ) as execv,
            unittest.mock.patch(_ARGV_TARGET, argv),
            self.assertRaises(ImageReplaced),
        ):
            dispatch.line_dispatch(line)
        expected = argv + [_MAIN_LOOP_OPTION, "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # A file that does not exist raises and the process is not replaced.
    def test_file_missing(self) -> None:
        engine_system.handlers_register(self.root, True)
        os.makedirs(self.loop_path)
        os.makedirs(os.path.join(self.loop_path, "b.py"))
        for name in ("a.py", "b.py"):
            with self.subTest(name=name):
                line = _line_make("system.restart", main_loop=name)
                path = os.path.join(self.loop_path, name)
                message = i18n("engine_system.main_loop_missing", path)
                with unittest.mock.patch(_EXEC_TARGET) as execv:
                    self.dispatch_check(FileNotFoundError, message, line)
                execv.assert_not_called()

    # A name that is not plain raises, even where a file of it exists.
    def test_name_invalid(self) -> None:
        engine_system.handlers_register(self.root, True)
        _loop_write(self.root, "b.py")
        _loop_write(self.root, os.path.join("d", "b.py"))
        outside = os.path.join(self.root, "b.py")
        with open(outside, "w", encoding="utf-8") as file:
            file.write(_SOURCE_TEXT)
        for name in _NAMES_INVALID:
            with self.subTest(name=name):
                line = _line_make("system.restart", main_loop=name)
                message = i18n("engine_system.name_invalid", name)
                with unittest.mock.patch(_EXEC_TARGET) as execv:
                    self.dispatch_check(ValueError, message, line)
                execv.assert_not_called()

    # With debug mode off the handler raises and the process is not replaced.
    def test_restart_gated(self) -> None:
        engine_system.handlers_register(self.root, False)
        _loop_write(self.root, "b.py")
        line = _line_make("system.restart", main_loop="b.py")
        message = i18n("engine_system.debug_off", "system.restart")
        with unittest.mock.patch(_EXEC_TARGET) as execv:
            self.dispatch_check(RuntimeError, message, line)
        execv.assert_not_called()


# Tests the two tools on an MCP server.
class TestTools(IsolatedCase):
    # Makes an MCP server with the tools, for the debug setting.
    def server_make(self, debug: bool) -> mcp.Server:
        server = mcp.Server("xsjs-server", "0")
        engine_system.tools_register(server, self.root, debug)
        return server

    # Checks the code and the text of the error that a response carries.
    def error_check(
        self, response: mcp.Message, code: int, message: str
    ) -> None:
        self.assertEqual(response["error"]["code"], code)
        self.assertEqual(response["error"]["message"], message)

    # The list is the server side of the API file, key for key.
    def test_tools_listed(self) -> None:
        server = self.server_make(True)
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        listed = _response_get(server, request)["result"]["tools"]
        self.assertEqual(json.dumps(listed), json.dumps(_entries_read()))

    # Neither tool is listed with a permit mark, so no client asks for one.
    def test_permit_absent(self) -> None:
        server = self.server_make(True)
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        listed = _response_get(server, request)["result"]["tools"]
        self.assertEqual(
            [(tool["name"], "_meta" in tool) for tool in listed],
            [("source_put", False), ("system_restart", False)],
        )

    # A second registration on one server raises.
    def test_tools_twice(self) -> None:
        server = self.server_make(True)
        self.raise_check(
            ValueError,
            i18n("mcp.tool_twice", "source_put"),
            lambda: engine_system.tools_register(server, self.root, True),
        )

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
        message = i18n("engine_system.debug_off", "source_put")
        self.error_check(response, _CODE_INTERNAL, message)
        self.assertEqual(os.listdir(self.root), [])

    # Arguments that are missing or not text are refused with their code.
    def test_source_arguments(self) -> None:
        server = self.server_make(True)
        bad: list[tuple[dict[str, Any], str]] = [
            ({"name": "a.py"}, "text"),
            ({"text": "x"}, "name"),
            ({"name": 5, "text": "x"}, "name"),
            ({"name": "a.py", "text": None}, "text"),
        ]
        for arguments, key in bad:
            with self.subTest(arguments=arguments):
                response = _response_get(
                    server, _call_make("source_put", arguments)
                )
                message = i18n(
                    "engine_system.argument_invalid", "source_put", key
                )
                self.error_check(response, _CODE_PARAMS, message)
        self.assertEqual(os.listdir(self.root), [])

    # A name that is not plain raises as any exception of a tool does.
    def test_source_name(self) -> None:
        server = self.server_make(True)
        call = _call_make("source_put", {"name": "../a.py", "text": "x"})
        response = _response_get(server, call)
        message = i18n("engine_system.name_invalid", "../a.py")
        self.error_check(response, _CODE_INTERNAL, message)
        self.assertEqual(os.listdir(self.root), [])

    # The restart tool replaces the process image as the handler does.
    def test_restart_tool(self) -> None:
        server = self.server_make(True)
        _loop_write(self.root, "b.py")
        call = _call_make("system_restart", {"main_loop": "b.py"})
        with (
            unittest.mock.patch(
                _EXEC_TARGET, side_effect=ImageReplaced
            ) as execv,
            unittest.mock.patch(_ARGV_TARGET, _PROGRAM_ARGV),
            self.assertRaises(ImageReplaced),
        ):
            server.message_handle(call)
        expected = _PROGRAM_ARGV + [_MAIN_LOOP_OPTION, "b.py"]
        execv.assert_called_once_with(sys.executable, expected)

    # With debug mode off the restart tool raises and nothing is replaced.
    def test_restart_gated(self) -> None:
        server = self.server_make(False)
        _loop_write(self.root, "b.py")
        call = _call_make("system_restart", {"main_loop": "b.py"})
        with unittest.mock.patch(_EXEC_TARGET) as execv:
            response = _response_get(server, call)
        message = i18n("engine_system.debug_off", "system_restart")
        self.error_check(response, _CODE_INTERNAL, message)
        execv.assert_not_called()

    # A missing file or a missing argument is an error and nothing is replaced.
    def test_restart_refused(self) -> None:
        server = self.server_make(True)
        path = os.path.join(self.loop_path, "b.py")
        invalid = i18n(
            "engine_system.argument_invalid", "system_restart", "main_loop"
        )
        cases: tuple[tuple[dict[str, Any], int, str], ...] = (
            (
                {"main_loop": "b.py"},
                _CODE_INTERNAL,
                i18n("engine_system.main_loop_missing", path),
            ),
            ({}, _CODE_PARAMS, invalid),
            ({"main_loop": 5}, _CODE_PARAMS, invalid),
        )
        for arguments, code, message in cases:
            with self.subTest(arguments=arguments):
                call = _call_make("system_restart", arguments)
                with unittest.mock.patch(_EXEC_TARGET) as execv:
                    response = _response_get(server, call)
                self.error_check(response, code, message)
                execv.assert_not_called()


# Tests the registration.
class TestRegister(IsolatedCase):
    # A second registration raises, as the dispatcher refuses the pair.
    def test_register_twice(self) -> None:
        engine_system.handlers_register(self.root, True)
        self.raise_check(
            ValueError,
            i18n("dispatch.handler_twice", "settings.put", 0),
            lambda: engine_system.handlers_register(self.root, True),
        )

    # Called before the registration each handler raises.
    def test_called_early(self) -> None:
        line = _line_make("settings.put")
        message = i18n("engine_system.not_registered")
        uses: list[Callable[[], object]] = [
            lambda: engine_system.settings_put(line, settings={}),
            lambda: engine_system.source_put(line, name="a.py"),
            lambda: engine_system.system_restart(line, main_loop="b.py"),
        ]
        for use in uses:
            self.raise_check(RuntimeError, message, use)
