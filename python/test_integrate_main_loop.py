# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the main loop serving every engine it registers, each line type but
# `system.restart`, which execs, in forked children over pipes, with roots in
# `build/`. Each child opens the root's log first, through
# `main_loop.verbose`, as `bootstrap.py` does, then prepares the root and
# serves the pipes. The page's commits are pushes applied and answered by
# nothing, read back from the root's database files; a `tap.line` of the
# TypeScript stream is appended to its file; the server's MCP server
# answers `initialize`, and `tools/list` with the tools of
# API/mcp/tools.json; `verbose.tail` gives the server's ring and the page's
# lines; and `settings.put` and `source.put` write the root's files in debug
# mode and are refused with debug false. The lines fed to the loop are the
# gold's, each its JSON text, a CR and its blobs' bytes, and the lines it
# writes are read back the same way and checked against the gold.

import contextlib, copy, functools, harness, hashlib, json, main_loop, os, re
import signal, sqlite3, tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_main_loop"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# A size chosen by its writer, small: a blob over it streams to the cache.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# A size chosen by its writer: the most the loop reads, so lines split.
_CHUNK_BYTES: int = harness.gold_get(f"{_GOLD_ID}.chunk_bytes")

# A size chosen by its writer: the most the test reads from the pipe.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# A ring size chosen by its writer, other than the checkout's.
_RING: int = harness.gold_get(f"{_GOLD_ID}.ring")

# The query of the hash and the value of one key.
_VALUE_QUERY = "SELECT sha256, data FROM _kv WHERE key = ?"

# The query of the heads of the documents.
_HEADS_QUERY = "SELECT id, version FROM _head ORDER BY id"

# The query of the turns of a database.
_TURNS_QUERY = "SELECT scene, n, role, content FROM _turn ORDER BY n"

# What a child says when `loop_prepare` returned None and its work ended.
_ENDING_PREPARED = repr(None)

# How a child ends when the loop exits 1.
_ENDING_FAILED = "exit 1"

# The database the push test makes.
_CASTLE_DB = "castle"

# The database the push test makes and drops.
_DROPPED_DB = "dropped"

# The source the `source.put` line carries.
_SOURCE = b"pass\n"

# The TAP file of the TypeScript stream in a root.
_TAP_FILE = os.path.join("tap", "typescript.tap")


# A copy of a value of this module's gold, which the test may change.
def _gold_copy(name: str) -> Any:
    return copy.deepcopy(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The bytes of a line on the wire: its JSON text, a CR, then each blob.
def _wire_bytes(line: dict[str, Any], *blobs: bytes) -> bytes:
    size_name = "size" if "type" in line["0"] else "s"
    for number, blob in enumerate(blobs, 1):
        line[str(number)][size_name] = len(blob)
    text = json.dumps(line, ensure_ascii=False, separators=(",", ":"))
    return b"".join([text.encode("utf-8"), b"\r", *blobs])


# The bytes of a gold line on the wire.
def _line_bytes(name: str, *blobs: bytes) -> bytes:
    return _wire_bytes(_gold_copy(f"lines.{name}"), *blobs)


# Reads whole lines: each JSON text up to its CR, then its blobs' bytes.
def _lines_read(data: bytes) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    offset = 0
    while offset < len(data):
        end = data.index(b"\r", offset)
        line: dict[str, Any] = json.loads(data[offset:end])
        offset = end + 1
        size_name = "size" if "type" in line["0"] else "s"
        number = 1
        while str(number) in line:
            blob = line[str(number)]
            size: int = blob[size_name]
            if offset + size > len(data):
                raise AssertionError("the output ends inside a blob")
            blob["d"] = data[offset : offset + size]
            offset += size
            number += 1
        lines.append(line)
    return lines


# The payload of a line read back: the keys that are no header's number.
def _payload_of(line: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in line.items()
        if _NUMBER_KEY.fullmatch(key) is None
    }


# The result of `tools/list`: each server tool of the API file, no permit.
def _list_result() -> dict[str, Any]:
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
    return {"tools": tools}


# The JSON text of a value, as the server stores one.
def _json_bytes(value: object) -> bytes:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8")


# Runs a query on a database file under the root and returns its rows.
def _rows_read(root: str, db: str, sql: str, *params: object) -> list[Any]:
    path = os.path.join(root, db + ".sqlite")
    with contextlib.closing(sqlite3.connect(path)) as connection:
        return connection.execute(sql, params).fetchall()


# The value of a key of a database under the root, from the cache when NULL.
def _value_read(root: str, db: str, key: str) -> bytes:
    [(sha256, data)] = _rows_read(root, db, _VALUE_QUERY, key)
    if data is not None:
        return data
    with open(os.path.join(root, "cache", sha256.hex()), "rb") as file:
        return file.read()


# Reads a pipe to its end and closes it.
def _pipe_drain(fd: int) -> bytes:
    data = bytearray()
    while chunk := os.read(fd, _READ_BYTES):
        data += chunk
    os.close(fd)
    return bytes(data)


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(
    work: Callable[[int, int], str], read_fd: int, write_fd: int, path: str
) -> None:
    try:
        try:
            ending = work(read_fd, write_fd)
        except SystemExit as error:
            ending = f"exit {error.code}"
        except BaseException:
            ending = traceback.format_exc()
        with open(path, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Opens the root's log with the ring of its settings, through `main_loop`.
def _log_open(root: str) -> None:
    path = os.path.join(root, "settings.json")
    with open(path, encoding="utf-8") as file:
        values: dict[str, Any] = json.load(file)
    main_loop.verbose.log_open(root, values["verbose_ring"])


# The work of a child that prepares the root and serves the pipes to the end.
def _loop_serve(root: str, read_fd: int, write_fd: int) -> str:
    _log_open(root)
    prepared = repr(main_loop.loop_prepare(root))
    main_loop.loop_run(read_fd, write_fd, root)
    return prepared


# Gives each test a root in `build/` whose settings stream small blobs.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the root, and writes its settings.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)
        self.debug_write(harness.setting_get("debug"))
        self.work = functools.partial(_loop_serve, self.root)

    # Writes the checkout's settings with `debug` and the gold's sizes.
    def debug_write(self, debug: bool) -> None:
        values = harness.settings_copy()
        values["debug"] = debug
        values["overflow_bytes"] = _OVERFLOW_BYTES
        values["chunk_bytes"] = _CHUNK_BYTES
        path = os.path.join(self.root, "settings.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(values, file)
        self.values = values

    # Runs the loop in a child fed the data, returns its ending and output.
    def child_run(self, data: bytes) -> tuple[str, bytes]:
        input_read, input_write = os.pipe()
        os.set_blocking(input_write, False)
        self.assertEqual(os.write(input_write, data), len(data))
        os.close(input_write)
        output_read, output_write = os.pipe()
        path = os.path.join(self.scratch, "ending.txt")
        pid = os.fork()
        if pid == 0:
            os.close(output_read)
            _child_end(self.work, input_read, output_write, path)
        os.close(input_read)
        os.close(output_write)
        output = _pipe_drain(output_read)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(path)
        return ending, output

    # Runs the loop on data it serves to the end, and returns its output.
    def served_read(self, data: bytes) -> list[dict[str, Any]]:
        ending, output = self.child_run(data)
        if ending != _ENDING_PREPARED:
            self.fail(ending)
        return _lines_read(output)

    # Checks that a line read back has the header of a gold line.
    def header_check(self, line: dict[str, Any], name: str) -> None:
        self.assertEqual(line["0"], _gold_copy(f"lines.{name}")["0"])


# The main loop serving each engine's lines.
class TestEngines(ScratchCase):
    # Every kind of commit is applied as a push and answered by nothing.
    def test_pushes_applied(self) -> None:
        pushes = [
            _line_bytes("create_castle"),
            _line_bytes("put_kept", b"kept value"),
            _line_bytes("put_gone", b"gone value"),
            _line_bytes("delete_gone"),
            _line_bytes("doc_note"),
            _line_bytes("turn_note"),
            _line_bytes("sql_castle"),
            _line_bytes("create_dropped"),
            _line_bytes("drop_dropped"),
        ]
        self.assertEqual(self.served_read(b"".join(pushes)), [])
        kept = _value_read(self.root, _CASTLE_DB, "kept")
        self.assertEqual(kept, b"kept value")
        gone = _rows_read(self.root, _CASTLE_DB, _VALUE_QUERY, "gone")
        self.assertEqual(gone, [])
        note = _gold_copy("lines.doc_note")
        heads = _rows_read(self.root, _CASTLE_DB, _HEADS_QUERY)
        self.assertEqual(heads, [(note["id"], 1)])
        turn = _gold_copy("lines.turn_note")
        turns = _rows_read(self.root, _CASTLE_DB, _TURNS_QUERY)
        content = _json_bytes(turn["content"]).decode()
        expected = [(turn["scene"], 1, turn["role"], content)]
        self.assertEqual(turns, expected)
        table = _rows_read(self.root, _CASTLE_DB, "SELECT x FROM t")
        self.assertEqual(table, [(7,)])
        dropped = os.path.join(self.root, _DROPPED_DB + ".sqlite")
        self.assertFalse(os.path.exists(dropped))

    # A `tap.line` of the TypeScript stream is appended to its file, no answer.
    def test_tap_line(self) -> None:
        self.assertEqual(self.served_read(_line_bytes("tap_line")), [])
        text: str = _gold_copy("lines.tap_line")["text"]
        path = os.path.join(self.root, _TAP_FILE)
        with open(path, encoding="utf-8") as file:
            self.assertEqual(file.read(), text + "\n")

    # The server's MCP server answers `initialize` and `tools/list` only.
    def test_mcp_tools(self) -> None:
        lines = [
            _line_bytes("initialize"),
            _line_bytes("initialized"),
            _line_bytes("tools_list"),
        ]
        replies = self.served_read(b"".join(lines))
        self.assertEqual(len(replies), 2)
        first, second = replies
        self.assertEqual(first, _gold_copy("lines.initialize_reply"))
        expected = _gold_copy("lines.tools_list_reply")
        expected["result"] = _list_result()
        self.assertEqual(second, expected)

    # `verbose.tail` gives the server's ring, its own trace, and the page's.
    def test_verbose_tail(self) -> None:
        self.debug_write(True)
        lines = [
            _line_bytes("tail_server"),
            _line_bytes("verbose_put"),
            _line_bytes("tail_ui"),
        ]
        replies = self.served_read(b"".join(lines))
        self.assertEqual(len(replies), 2)
        server, page = replies
        self.header_check(server, "tail_server_reply")
        texts = [entry["text"] for entry in server["lines"]]
        self.assertEqual(texts, [_text_get("main_loop_line_dispatch_tail")])
        self.assertEqual(page, _gold_copy("lines.tail_ui_reply"))

    # In debug mode `source.put` writes a main loop file and `settings.put`
    # rewrites the settings, each answered.
    def test_debug_served(self) -> None:
        self.debug_write(True)
        changed = {**self.values, "verbose_ring": _RING}
        put = _gold_copy("lines.settings_put")
        put["settings"] = changed
        data = _line_bytes("source_put", _SOURCE) + _wire_bytes(put)
        replies = self.served_read(data)
        self.assertEqual(len(replies), 2)
        source, settings = replies
        digest = hashlib.sha256(_SOURCE).hexdigest()
        expected = {**_gold_copy("lines.source_reply"), "sha256": digest}
        self.assertEqual(source, expected)
        self.assertEqual(settings, _gold_copy("lines.settings_reply"))
        name: str = _gold_copy("lines.source_put")["name"]
        path = os.path.join(self.root, "main_loop", name)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), _SOURCE)
        path = os.path.join(self.root, "settings.json")
        with open(path, encoding="utf-8") as file:
            self.assertEqual(json.load(file), changed)

    # With `debug` false, `source.put` gets an `error` line and writes nothing.
    def test_debug_off(self) -> None:
        self.debug_write(False)
        data = _line_bytes("source_put", _SOURCE)
        ending, output = self.child_run(data)
        self.assertEqual(ending, _ENDING_FAILED)
        (error,) = _lines_read(output)
        self.header_check(error, "error_reply")
        self.assertEqual(sorted(_payload_of(error)), ["message", "stack"])
        message = _text_get("engine_system_debug_off_line")
        self.assertEqual(error["message"], message)
        self.assertTrue(error["stack"].endswith(": " + message))
        directory = os.path.join(self.root, "main_loop")
        self.assertFalse(os.path.exists(directory))
