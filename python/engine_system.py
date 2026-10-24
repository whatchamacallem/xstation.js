# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the `settings.put`, `source.put` and `system.restart` lines
# and the two tools of the server's MCP server that do the same for an
# external agent. All of them need debug mode. A write goes to a temporary file
# beside its target, which is then renamed over it.

import dispatch, functools, hashlib, jslb, json, mcp, os, settings, sys
from internationalization import i18n
from typing import Any, NoReturn

# The file in the root that holds the settings.
_SETTINGS_NAME = "settings.json"

# The directory in the root that holds the main loop files.
_MAIN_LOOP_DIRECTORY = "main_loop"

# The extension every main loop file name ends with.
_MAIN_LOOP_EXTENSION = ".py"

# The suffix of the temporary file a write goes to before the rename.
_TEMP_SUFFIX = ".tmp"

# The process option that names the main loop file.
_MAIN_LOOP_OPTION = "--main-loop"

# The prefix of a long option, which alone ends the options.
_LONG_PREFIX = "--"

# The mark that joins a long option and its value in one word.
_VALUE_MARK = "="

# The `JSON-RPC` code of arguments that a tool cannot use.
_CODE_PARAMS_INVALID = -32602

# The name of the tool that writes a main loop file.
_SOURCE_TOOL = "source_put"

# The name of the tool that restarts the process.
_RESTART_TOOL = "system_restart"

# The description of the tool that writes a main loop file.
_SOURCE_DESCRIPTION = (
    "Write a main loop file into the server's main_loop directory for"
    " system_restart to serve. Debug mode."
)

# The description of the tool that restarts the process.
_RESTART_DESCRIPTION = (
    "Restart the server process in place, keeping its pid, serving the"
    " named main loop file. Debug mode."
)

# The input schema of the tool that writes a main loop file.
_SOURCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "text": {"type": "string"}},
    "required": ["name", "text"],
}

# The input schema of the tool that restarts the process.
_RESTART_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"main_loop": {"type": "string"}},
    "required": ["main_loop"],
}


# The state the registration sets, which is empty until then.
class _SystemState:
    # Starts with no root and no debug setting.
    def __init__(self) -> None:
        self.root: str | None = None
        self.debug: bool | None = None


# The one state of the module.
_STATE = _SystemState()


# Returns the root and the debug setting, raising before the registration.
def _registered_get() -> tuple[str, bool]:
    if _STATE.root is None or _STATE.debug is None:
        raise RuntimeError(i18n("engine_system.not_registered"))
    return _STATE.root, _STATE.debug


# Raises unless debug mode is on, naming the line or tool that needs it.
def _debug_check(debug: bool, name: str) -> None:
    if not debug:
        raise RuntimeError(i18n("engine_system.debug_off", name))


# Writes the bytes to a temporary file beside the path and renames it over.
def _file_write(path: str, data: bytes) -> None:
    temp = path + _TEMP_SUFFIX
    with open(temp, "wb") as file:
        file.write(data)
    os.replace(temp, path)


# Checks the settings and rewrites the settings file in the root.
def _settings_write(root: str, value: dict[str, Any]) -> None:
    settings.settings_check(value)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    _file_write(os.path.join(root, _SETTINGS_NAME), text.encode("utf-8"))


# Returns the path of a main loop file, raising unless the name is plain.
def _loop_path(root: str, name: str) -> str:
    if (
        os.path.basename(name) != name
        or name.startswith(".")
        or not name.endswith(_MAIN_LOOP_EXTENSION)
    ):
        raise ValueError(i18n("engine_system.name_invalid", name))
    return os.path.join(root, _MAIN_LOOP_DIRECTORY, name)


# Writes the bytes as a main loop file and returns their `sha256` in hex.
def _bytes_install(root: str, name: str, data: bytes) -> str:
    path = _loop_path(root, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _file_write(path, data)
    return hashlib.sha256(data).hexdigest()


# Moves a file that was streamed to the cache into place as a main loop file.
def _file_install(root: str, name: str, source: str) -> None:
    path = _loop_path(root, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    os.replace(source, path)


# Says whether a word gives the main loop option, as argparse abbreviates it.
def _option_match(word: str) -> bool:
    name = word.partition(_VALUE_MARK)[0]
    longer = len(name) > len(_LONG_PREFIX)
    return longer and _MAIN_LOOP_OPTION.startswith(name)


# Returns the process arguments with the main loop option set to the file.
def _argv_make(argv: list[str], main_loop: str) -> list[str]:
    kept: list[str] = []
    skipping = False
    for word in argv:
        if skipping:
            skipping = False
        elif _option_match(word):
            skipping = _VALUE_MARK not in word
        else:
            kept.append(word)
    return [*kept, _MAIN_LOOP_OPTION, main_loop]


# Replaces the process image to serve the main loop file, which must exist.
def _restart_run(root: str, main_loop: str) -> NoReturn:
    path = _loop_path(root, main_loop)
    if not os.path.isfile(path):
        raise FileNotFoundError(i18n("engine_system.main_loop_missing", path))
    os.execv(sys.executable, _argv_make(sys.orig_argv, main_loop))


# Reads the text argument of a tool call, raising unless it is there.
def _argument_get(tool: str, arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str):
        raise mcp.RpcError(
            _CODE_PARAMS_INVALID,
            i18n("engine_system.argument_invalid", tool, key),
        )
    return value


# Runs the tool that writes the text as a main loop file.
def _source_tool(
    root: str, debug: bool, arguments: dict[str, Any]
) -> mcp.ToolResult:
    _debug_check(debug, _SOURCE_TOOL)
    name = _argument_get(_SOURCE_TOOL, arguments, "name")
    text = _argument_get(_SOURCE_TOOL, arguments, "text")
    digest = _bytes_install(root, name, text.encode("utf-8"))
    result = json.dumps({"sha256": digest}, separators=(",", ":"))
    return mcp.ToolResult([{"type": "text", "text": result}], False)


# Runs the tool that restarts the process to serve a main loop file.
def _restart_tool(
    root: str, debug: bool, arguments: dict[str, Any]
) -> mcp.ToolResult:
    _debug_check(debug, _RESTART_TOOL)
    _restart_run(root, _argument_get(_RESTART_TOOL, arguments, "main_loop"))


# Rewrites `settings.json` in the root, in debug mode only.
def settings_put(
    line: jslb.Object, *, settings: dict[str, object]
) -> jslb.Object:
    root, debug = _registered_get()
    _debug_check(debug, "settings.put")
    _settings_write(root, settings)
    return dispatch.reply_make(line)


# Writes blob 1 as a main loop file and replies with its `sha256`.
def source_put(line: jslb.Object, *, name: str) -> jslb.Object:
    root, debug = _registered_get()
    _debug_check(debug, "source.put")
    if 1 not in line:
        raise ValueError(i18n("engine_system.blob_missing"))
    blob: jslb.Object = line[1]
    data: bytes | str = jslb.field_get(blob, "data")
    if isinstance(data, str):
        digest: str = blob["sha256"]
        _file_install(root, name, data)
    else:
        digest = _bytes_install(root, name, data)
    return dispatch.reply_make(line, sha256=digest)


# Replaces the process image to serve the main loop file, in debug mode only.
def system_restart(line: jslb.Object, *, main_loop: str) -> None:
    root, debug = _registered_get()
    _debug_check(debug, "system.restart")
    _restart_run(root, main_loop)


# Registers the two tools of the server on the MCP server.
def tools_register(server: mcp.Server, root: str, debug: bool) -> None:
    server.tool_register(
        mcp.Tool(_SOURCE_TOOL, _SOURCE_DESCRIPTION, _SOURCE_SCHEMA, False),
        functools.partial(_source_tool, root, debug),
    )
    server.tool_register(
        mcp.Tool(_RESTART_TOOL, _RESTART_DESCRIPTION, _RESTART_SCHEMA, False),
        functools.partial(_restart_tool, root, debug),
    )


# Registers the three handlers, with the root and the debug gate they need.
def handlers_register(root: str, debug: bool) -> None:
    _STATE.root = root
    _STATE.debug = debug
    dispatch.handler_register("settings.put", 0, settings_put)
    dispatch.handler_register("source.put", 0, source_put)
    dispatch.handler_register("system.restart", 0, system_restart)
