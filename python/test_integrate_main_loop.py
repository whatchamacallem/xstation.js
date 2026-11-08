# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the main loop serving every engine it registers, each line type but
# `system.restart`, which execs, in forked children over pipes, with roots in
# `build/`. Each child opens the root's audit in debug mode, as `bootstrap.py`
# does, then prepares the root and serves the pipes. The page's commits are
# pushes applied and answered by nothing, read back from the root's database
# files; a `tap.line` of the TypeScript stream is appended to
# its file; the server's MCP server answers `initialize`, and `tools/list`
# with the tools of API/mcp/tools.json; `audit.tail` gives the audit's newest
# entries; `settings.put` and `source.put` write the root's files in debug
# mode and are refused with the parameter debug false, which each child sets
# from the root's parameters as `bootstrap.py` does; and `db.sync` streams
# every database whole, each line recorded in the audit with no blob's bytes.
# The lines fed to the loop are the gold's, each its JSON text, a CR and its
# blobs' bytes, and the lines it writes are read back the same way and
# checked against the gold.

import contextlib, copy, functools, harness, hashlib, json, main_loop, os, re
import signal, sqlite3, switches, tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The seed files that the main loop reads for a new metaverse.
_SEED_PATH = os.path.join(_ROOT_PATH, "python", "seed")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_integrate_main_loop"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# A size chosen by its writer, small: a blob over it streams to the cache.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# A size chosen by its writer: the most the loop reads, so lines split.
_CHUNK_BYTES: int = harness.gold_get(f"{_GOLD_ID}.chunk_bytes")

# A size chosen by its writer: the most the test reads from the pipe.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# A count of the audit's entries chosen by its writer, not the checkout's.
_ENTRIES: int = harness.gold_get(f"{_GOLD_ID}.entries")

# The seeded image: its file, its key in the metaverse and its ref.
_SEED_IMAGE: dict[str, Any] = harness.gold_get(f"{_GOLD_ID}.image")

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

# The seeded database that holds the image and the scene.
_METAVERSE_DB = "metaverse"

# The source the `source.put` line carries.
_SOURCE = b"pass\n"

# The value the sync tests keep in a row of the castle.
_KEPT_VALUE = b"kept value"

# The value the sync tests keep in a cache file, over `_OVERFLOW_BYTES`.
_BIG_VALUE = bytes(index % 256 for index in range(_OVERFLOW_BYTES * 2 + 1))

# The start of the names of the log's files, which no root holds.
_LOG_PREFIX = "_verbose"

# The file of the audit in the root.
_AUDIT_FILE = "_audit.txt"

# The directory of the TAP files in the root.
_TAP_DIRECTORY = "tap"

# The role the children open the audit for, as `bootstrap.py` names it.
_ENGINE_ROLE = "engine"

# The start of the label of a note, whose body is its text indented.
_NOTE_PREFIX: str = harness.gold_get(f"{_GOLD_ID}.texts.note_prefix")


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


# The bytes of the pushes that fill the castle, then of `db.sync`.
def _sync_bytes() -> bytes:
    lines = [
        _line_bytes("create_castle"),
        _line_bytes("put_kept", _KEPT_VALUE),
        _line_bytes("put_big", _BIG_VALUE),
        _line_bytes("sync"),
    ]
    return b"".join(lines)


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


# Opens the root's audit in debug mode, as `bootstrap.py` does.
def _record_open(root: str) -> None:
    if switches.debug:
        path = os.path.join(root, "settings.json")
        with open(path, encoding="utf-8") as file:
            values: dict[str, Any] = json.load(file)
        main_loop.audit.audit_open(root, values["blob_max"], _ENGINE_ROLE)


# Each entry of the root's audit: its label, its JSON or note, then the rest.
def _audit_read(root: str) -> list[tuple[str, Any, str]]:
    read: list[tuple[str, Any, str]] = []
    for entry in main_loop.audit.entries_read(root):
        if entry.label.startswith(_NOTE_PREFIX):
            read.append((entry.label, entry.body, ""))
        else:
            value, end = json.JSONDecoder().raw_decode(entry.body)
            read.append((entry.label, value, entry.body[end:]))
    return read


# The entry of a line under the label of the gold: its JSON, no blob's bytes.
def _line_entry(label: str, line: dict[str, Any]) -> tuple[str, Any, str]:
    value = dict(line)
    count = 0
    while str(count + 1) in value:
        count += 1
        blob: dict[str, Any] = value[str(count)]
        value[str(count)] = {
            name: field for name, field in blob.items() if name != "d"
        }
    rest = ""
    if count:
        rest = "\n" + _text_get("blobs_omitted").format(count)
    return _text_get(label), value, rest


# Child: the root's parameters set, as `bootstrap.py` sets them, then serves.
def _loop_serve(root: str, read_fd: int, write_fd: int) -> str:
    switches.switches_apply(switches.parameters_load(root))
    _record_open(root)
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
        self.debug_write(True)
        self.work = functools.partial(_loop_serve, self.root)

    # Writes the checkout's settings with the gold's sizes, `debug` set.
    def debug_write(self, debug: bool) -> None:
        values = harness.settings_copy()
        values["overflow_bytes"] = _OVERFLOW_BYTES
        values["chunk_bytes"] = _CHUNK_BYTES
        path = os.path.join(self.root, "settings.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(values, file)
        self.values = values
        parameters = {**switches.switches_get(), "debug": debug}
        switches.parameters_write(self.root, parameters)

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

    # Checks that the root holds nothing that records a run.
    def records_absent(self) -> None:
        names = os.listdir(self.root)
        self.assertNotIn(_AUDIT_FILE, names)
        self.assertNotIn(_TAP_DIRECTORY, names)
        logs = [name for name in names if name.startswith(_LOG_PREFIX)]
        self.assertEqual(logs, [])

    # Runs the loop on data it serves to the end, and returns its output.
    def served_read(self, data: bytes) -> list[dict[str, Any]]:
        ending, output = self.child_run(data)
        if ending != _ENDING_PREPARED:
            self.fail(ending)
        return _lines_read(output)

    # Checks that a line read back has the header of a gold line.
    def header_check(self, line: dict[str, Any], name: str) -> None:
        self.assertEqual(line["0"], _gold_copy(f"lines.{name}")["0"])

    # Checks a sync's pushes by type, and gives each database its blobs.
    def restores_read(
        self, pushes: list[dict[str, Any]]
    ) -> dict[str, tuple[bytes, list[bytes]]]:
        restores: dict[str, tuple[bytes, list[bytes]]] = {}
        left = iter(pushes)
        for restore in left:
            self.assertEqual(restore["0"]["type"], "db.restore")
            files: list[bytes] = []
            for _ in range(restore["files"]):
                file = next(left)
                self.assertEqual(file["0"]["type"], "db.file")
                self.assertEqual(file["db"], restore["db"])
                files.append(file["1"]["d"])
            restores[restore["db"]] = (restore["1"]["d"], files)
        return restores


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
        path = os.path.join(self.root, _TAP_DIRECTORY, "typescript.tap")
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

    # `audit.tail` gives the audit's newest entries, a line read among them.
    def test_audit_tail(self) -> None:
        note = _gold_copy("lines.audit_note")
        lines = [
            _line_bytes("create_castle"),
            _line_bytes("audit_note"),
            _line_bytes("tail_one"),
            _line_bytes("tail_all"),
        ]
        replies = self.served_read(b"".join(lines))
        self.assertEqual(len(replies), 2)
        one, every = replies
        noted = main_loop.audit.note_text(
            note["thread"], note["at"], note["text"]
        )
        expected = {**_gold_copy("lines.tail_one_reply"), "text": noted}
        self.assertEqual(one, expected)
        self.header_check(every, "tail_all_reply")
        path = os.path.join(self.root, _AUDIT_FILE)
        with open(path, encoding="utf-8") as file:
            document = file.read()
        # The entries follow the document's one start heading and its blank.
        self.assertEqual(every["text"], document.split("\n\n", 1)[1])
        labels = [entry[0] for entry in _audit_read(self.root)]
        read = _text_get("label_read")
        self.assertEqual(labels, [read, _NOTE_PREFIX + note["thread"]])

    # Debug on: `source.put` writes a loop, `settings.put` settings, answered.
    def test_debug_served(self) -> None:
        self.debug_write(True)
        changed = {**self.values, "audit_entries": _ENTRIES}
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
        self.records_absent()

    # With `debug` false, a whole session leaves no record in the root.
    def test_session_unrecorded(self) -> None:
        self.debug_write(False)
        pushes = _line_bytes("create_castle") + _line_bytes("initialize")
        replies = self.served_read(pushes)
        self.assertEqual(replies, [_gold_copy("lines.initialize_reply")])
        self.records_absent()

    # `db.sync` sends every database whole, each with its cache files after it.
    def test_sync_whole(self) -> None:
        lines = self.served_read(_sync_bytes())
        expected = _gold_copy("lines.sync_reply")
        self.assertEqual(lines[-1], expected)
        restores = self.restores_read(lines[:-1])
        self.assertEqual(list(restores), expected["databases"])
        image, files = restores[_CASTLE_DB]
        self.assertEqual(files, [_BIG_VALUE])
        path = os.path.join(self.scratch, _CASTLE_DB + ".sqlite")
        with open(path, "wb") as file:
            file.write(image)
        kept = _value_read(self.scratch, _CASTLE_DB, "kept")
        self.assertEqual(kept, _KEPT_VALUE)

    # `db.sync` carries the seeded image's row and the scene that names it.
    def test_sync_image(self) -> None:
        lines = self.served_read(_sync_bytes())
        data, _ = self.restores_read(lines[:-1])[_METAVERSE_DB]
        path = os.path.join(self.scratch, _METAVERSE_DB + ".sqlite")
        with open(path, "wb") as file:
            file.write(data)
        image = _value_read(self.scratch, _METAVERSE_DB, _SEED_IMAGE["key"])
        with open(os.path.join(_SEED_PATH, _SEED_IMAGE["file"]), "rb") as file:
            self.assertEqual(image, file.read())
        document = _value_read(self.scratch, _METAVERSE_DB, "hyperposition/1")
        scene: dict[str, Any] = json.loads(document)
        self.assertEqual(scene["1"], _SEED_IMAGE["ref"])
        self.assertEqual(scene["image"], {"$ref": 1})

    # A sync's lines are recorded in order, in full, with no blob's bytes.
    def test_sync_recorded(self) -> None:
        create = _gold_copy("lines.create_castle")
        kept = _gold_copy("lines.put_kept")
        big = _gold_copy("lines.put_big")
        sync = _gold_copy("lines.sync")
        data = [
            _wire_bytes(create),
            _wire_bytes(kept, _KEPT_VALUE),
            _wire_bytes(big, _BIG_VALUE),
            _wire_bytes(sync),
        ]
        lines = self.served_read(b"".join(data))
        # The sink that streams the blob adds its digest to its header.
        big["1"]["sha256"] = hashlib.sha256(_BIG_VALUE).hexdigest()
        read = [create, kept, big, sync]
        expected = [_line_entry("label_read", line) for line in read]
        expected += [_line_entry("label_written", line) for line in lines]
        self.assertEqual(_audit_read(self.root), expected)
