# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the MCP server and client joined to `dispatch`, which writes the
# cascade of an exception: a tool's exception raised from another, or while
# another was handled, answers with an `isError` result whose text is the
# cascade with the first exception nested under `cause`, as the server
# answers it and as a client, joined to the server by a send function of
# the test, passes it on. The cascade expected is built here from the
# exceptions by the rule of `cause`.

import functools, json, mcp, traceback, unittest
from typing import Any, NoReturn

# The schema of a tool that takes nothing.
_EMPTY_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

# The tool that raises.
_FAILING_TOOL = mcp.Tool("fail", "Fails.", _EMPTY_SCHEMA, False)


# The `stack` of one entry of a cascade: the traceback without its chain.
def _stack_of(error: BaseException) -> str:
    lines = traceback.format_exception(error, chain=False)
    return "".join(lines).removesuffix("\n")


# One entry of a cascade: the exception's own message and stack.
def _entry_of(error: BaseException) -> dict[str, Any]:
    return {"message": str(error), "stack": _stack_of(error)}


# The text of an `isError` result: the cascade as compact JSON, as sent.
def _cascade_text(cascade: dict[str, Any]) -> str:
    return json.dumps(cascade, ensure_ascii=False, separators=(",", ":"))


# Raises "outer" while "inner" is handled and returns both.
def _context_raise() -> tuple[ValueError, RuntimeError]:
    try:
        raise RuntimeError("inner")
    except RuntimeError as inner:
        try:
            raise ValueError("outer")
        except ValueError as error:
            return error, inner


# Raises the error given, as a tool function that fails does.
def _tool_raise(error: Exception, arguments: dict[str, Any]) -> NoReturn:
    raise error


# Joins a client to a server: each message the client sends is handled by
# the server, and each response goes back to the client.
class ClientLink:
    # Makes a client whose send is a call of the server.
    def __init__(self, server: mcp.Server) -> None:
        self.server = server
        self.client = mcp.Client("xsjs-client", "2", self.message_carry)

    # Gives the message to the server and its response back to the client.
    def message_carry(self, message: mcp.Message) -> None:
        response = self.server.message_handle(message)
        if response is not None:
            self.client.message_handle(response)


# Tests the cascades of a tool's exceptions, through the server and a client.
class TestCascade(unittest.TestCase):
    # Makes the server.
    def setUp(self) -> None:
        self.server = mcp.Server("xsjs-test", "1")

    # Registers a tool that raises the error given when it is called.
    def failing_register(self, error: Exception) -> None:
        self.server.tool_register(
            _FAILING_TOOL, functools.partial(_tool_raise, error)
        )

    # Calls the failing tool and returns the `isError` result it answers.
    def failing_call(self, request_id: int) -> dict[str, Any]:
        params = {"name": _FAILING_TOOL.name, "arguments": {}}
        request: mcp.Message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": params,
        }
        response = self.server.message_handle(request)
        if response is None:
            raise AssertionError(f"no response to {request}")
        self.assertNotIn("error", response)
        self.assertEqual(response["id"], request_id)
        result: dict[str, Any] = response["result"]
        self.assertEqual(result["isError"], True)
        self.assertEqual(len(result["content"]), 1)
        self.assertEqual(result["content"][0]["type"], "text")
        return result

    # Takes the failure the last request kept, then checks none is left.
    def failure_get(self) -> BaseException:
        failure = self.server.failure_take()
        if failure is None:
            raise AssertionError("no failure kept")
        self.assertIsNone(self.server.failure_take())
        return failure

    # The exception a tool raised from another holds it under `cause`.
    def test_cause_kept(self) -> None:
        inner = RuntimeError("inner")
        try:
            raise ValueError("outer") from inner
        except ValueError as raised:
            error = raised
        self.failing_register(error)
        result = self.failing_call(9)
        cascade = {
            "message": "outer",
            "stack": _stack_of(error),
            "cause": {"message": "inner", "stack": _stack_of(inner)},
        }
        self.assertEqual(result["content"][0]["text"], _cascade_text(cascade))
        self.assertIs(self.failure_get(), error)

    # The exception a tool raised while another was handled holds it too.
    def test_context_kept(self) -> None:
        error, inner = _context_raise()
        self.failing_register(error)
        result = self.failing_call(10)
        cascade = _entry_of(error) | {"cause": _entry_of(inner)}
        self.assertEqual(result["content"][0]["text"], _cascade_text(cascade))
        self.assertIs(self.failure_get(), error)

    # A client joined to the server passes on the result with the cascade.
    def test_client_cascade(self) -> None:
        error, inner = _context_raise()
        self.failing_register(error)
        results: list[mcp.ToolResult] = []
        link = ClientLink(self.server)
        link.client.tool_call(_FAILING_TOOL.name, {}, results.append)
        cascade = _entry_of(error) | {"cause": _entry_of(inner)}
        content = [{"type": "text", "text": _cascade_text(cascade)}]
        self.assertEqual(results, [mcp.ToolResult(content, True)])
        self.assertIs(self.failure_get(), error)
