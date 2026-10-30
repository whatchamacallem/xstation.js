# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the runner of the stdio transport, `stdio_serve`, which reads the
# root's settings and serves the tools of `engine_system` on a real
# `mcp.Server`, in forked children whose stdin is a pipe and stdout a file, on
# roots in build/ that hold the checkout's settings with `debug` set: a
# session answered against the tools of API/mcp/tools.json, `source_put`
# writing a main loop file into the root in debug mode, and refused with
# debug false, its exception raised once its answer is out. Each child
# writes how it ended to a file, then kills itself. The texts are the gold's.

import harness, hashlib, json, mcp_stdio, os, signal, sys, tempfile, traceback
import unittest
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_mcp_stdio"

# The file in its scratch directory a child writes how it ended to.
_ENDING_NAME = "ending.txt"

# The child's stdout, a file: its `sys.stdout` keeps the parent's seekability.
_OUTPUT_NAME = "output.txt"

# The permissions of the stdout file.
_OUTPUT_MODE = 0o600

# A client's `initialize` request, which opens a session.
_INITIALIZE_LINE = (
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":'
    '{"protocolVersion":"2025-06-18","capabilities":{},'
    '"clientInfo":{"name":"xsjs-test","version":"1"}}}'
)

# The response to it: the pinned revision, `tools`, the server's identity.
_INITIALIZE_REPLY = (
    '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",'
    '"capabilities":{"tools":{}},'
    '"serverInfo":{"name":"xsjs-server","version":"0"}}}'
)

# The notification that follows a client's `initialize`.
_INITIALIZED_LINE = '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# A client's `tools/list` request, after the notification.
_LIST_LINE = '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

# The id of the call of `source_put`.
_CALL_ID = 3

# The main loop file the call writes.
_SOURCE_NAME = "stdio_put.py"

# The text the call writes as that file.
_SOURCE_TEXT = "# written over stdio\n"


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The response to `tools/list`: the server tools of the API file, no permit.
def _list_reply() -> dict[str, Any]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    tools = [
        {
            "name": entry["name"],
            "description": entry["description"],
            "inputSchema": entry["inputSchema"],
        }
        for entry in data["server"]["result"]["tools"]
    ]
    return {"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}}


# The call of `source_put` that writes the main loop file, as a line.
def _call_line() -> str:
    arguments = {"name": _SOURCE_NAME, "text": _SOURCE_TEXT}
    params = {"name": "source_put", "arguments": arguments}
    call = {
        "jsonrpc": "2.0",
        "id": _CALL_ID,
        "method": "tools/call",
        "params": params,
    }
    return json.dumps(call, separators=(",", ":"))


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(work: Callable[[], str], path: str) -> None:
    try:
        try:
            ending = work()
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a root in `build/`.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the root in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)

    # Writes the checkout's settings, with `debug` as given, as the root's.
    def settings_write(self, debug: bool) -> None:
        values = harness.settings_copy()
        values["debug"] = debug
        path = os.path.join(self.root, "settings.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(values, file)

    # Serves the text on the root in a child, returns its ending and replies.
    def stdio_run(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        input_read, input_write = os.pipe()
        output_path = os.path.join(self.scratch, _OUTPUT_NAME)
        root = self.root

        # Serves the root with the pipe as stdin and the file as stdout.
        def pipes_serve() -> str:
            os.close(input_write)
            os.dup2(input_read, 0)
            os.close(input_read)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            output = os.open(output_path, flags, _OUTPUT_MODE)
            os.dup2(output, 1)
            os.close(output)
            return repr(mcp_stdio.stdio_serve(["--root", root]))

        path = os.path.join(self.scratch, _ENDING_NAME)
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child_end(pipes_serve, path)
        os.close(input_read)
        with open(input_write, "wb") as writer:
            writer.write(text.encode("utf-8"))
        _, status = os.waitpid(pid, 0)
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(output_path, encoding="utf-8") as file:
            output = file.read()
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        replies = [json.loads(line) for line in output.splitlines()]
        return ending, replies


# Tests the runner on a root, with the tools of `engine_system`.
class TestServe(ScratchCase):
    # Each line is answered, tools of the API file, and end of input exits 0.
    def test_session_served(self) -> None:
        self.settings_write(True)
        lines = [_INITIALIZE_LINE, _INITIALIZED_LINE, _LIST_LINE]
        text = "".join(line + "\n" for line in lines)
        ending, replies = self.stdio_run(text)
        self.assertEqual(ending, repr(0))
        expected = [json.loads(_INITIALIZE_REPLY), _list_reply()]
        self.assertEqual(replies, expected)

    # Debug on: `source_put` writes the loop file, answering with its digest.
    def test_source_written(self) -> None:
        self.settings_write(True)
        ending, replies = self.stdio_run(_call_line() + "\n")
        self.assertEqual(ending, repr(0))
        source = _SOURCE_TEXT.encode("utf-8")
        digest = {"sha256": hashlib.sha256(source).hexdigest()}
        text = json.dumps(digest, separators=(",", ":"))
        content = [{"type": "text", "text": text}]
        result = {"content": content, "isError": False}
        expected = {"jsonrpc": "2.0", "id": _CALL_ID, "result": result}
        self.assertEqual(replies, [expected])
        path = os.path.join(self.root, "main_loop", _SOURCE_NAME)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), source)

    # Debug off: an error answer, a raise ends the run before line 2, no file.
    def test_debug_refused(self) -> None:
        self.settings_write(False)
        text = _call_line() + "\n" + _INITIALIZE_LINE + "\n"
        ending, replies = self.stdio_run(text)
        message = _text_get("engine_system_debug_off_tool")
        (reply,) = replies
        self.assertEqual(reply["id"], _CALL_ID)
        self.assertIs(reply["result"]["isError"], True)
        (content,) = reply["result"]["content"]
        self.assertEqual(json.loads(content["text"])["message"], message)
        last = ending.rstrip("\n").rsplit("\n", 1)[-1]
        self.assertEqual(last, f"RuntimeError: {message}")
        directory = os.path.join(self.root, "main_loop")
        self.assertFalse(os.path.exists(directory))
