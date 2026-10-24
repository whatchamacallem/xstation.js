# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the main loop in forked children over pipes, with roots in `build/`.
# Each child opens the root's log first, through `main_loop.verbose`, as
# `bootstrap.py` does. The prepare returns None, and its effects are read
# from the root's database files: the settings rows, the seeds, the
# `universe` table and its two triggers. The lines fed to the loop are the
# gold's, each its JSON text, a CR and its blobs' bytes; the lines it writes
# are read back the same way and checked against the gold, and the texts of
# its traces and refusals are the gold's, renderings written out. The
# browser's commits are pushes the loop applies and answers with nothing.
# The browser's `error` line is taken by `engine_tap` and the loop exits 1
# writing nothing, and a handler's `Failure` writes its reply, then the
# server's own `error` line, in the name form of the setting `debug`.

import contextlib, copy, functools, harness, hashlib, json, main_loop, os, re
import signal, sqlite3, tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The seed files that the main loop reads for a new metaverse.
_SEED_PATH = os.path.join(_ROOT_PATH, "python", "seed")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_main_loop"

# A key of the decimal digits of a non negative integer, as JSLB reads it.
_NUMBER_KEY = re.compile(r"0|[1-9][0-9]*")

# A size chosen by its writer, small: a blob over it streams to the cache.
_OVERFLOW_BYTES: int = harness.gold_get(f"{_GOLD_ID}.overflow_bytes")

# A size chosen by its writer: the most the loop reads, so lines split.
_CHUNK_BYTES: int = harness.gold_get(f"{_GOLD_ID}.chunk_bytes")

# A size chosen by its writer: a blob that streams, over `_OVERFLOW_BYTES`.
_STREAMED_BYTES = _OVERFLOW_BYTES * 2 + 1

# A size chosen by its writer: the most the test reads from the pipe.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The key of the scripted provider's script in `_files`.
_PROVIDER_KEY = "provider/script.json"

# The fixed databases the prepare opens, creating the missing ones.
_FIXED_DBS = ("_settings", "_preferences", "_files", "metaverse")

# The rows the seed writes in the metaverse beside the two documents.
_METAVERSE_ROWS = {
    "player": b"player",
    "world": b"metaverse",
    "scene": b"/metaverse/hyperposition/1",
}

# The ids of the seeded documents, each the name of its seed file.
_SEED_IDS = ("hyperposition", "prompt")

# The heads of the two seeded documents.
_SEED_HEADS = [("hyperposition", 1), ("prompt", 1)]

# The columns of the metaverse's `universe` table.
_UNIVERSE_COLUMNS = [("name",), ("title",), ("player",), ("world",)]

# The triggers of the `universe` table, as API/sql/metaverse.sql names them.
_UNIVERSE_TRIGGERS = [("universe_world_insert",), ("universe_world_update",)]

# The string the triggers raise for a second row naming a world.
_AMBIGUOUS = "agent.content_ambiguous"

# The query of every key and value of a database.
_ROWS_QUERY = "SELECT key, data FROM _kv"

# The query of every key, size and hash of a database, in key order.
_HASHES_QUERY = "SELECT key, size, sha256 FROM _kv ORDER BY key"

# The query of the hash and the value of one key.
_VALUE_QUERY = "SELECT sha256, data FROM _kv WHERE key = ?"

# The query of the heads of the documents.
_HEADS_QUERY = "SELECT id, version FROM _head ORDER BY id"

# The query of the columns of the `universe` table.
_COLUMNS_QUERY = "SELECT name FROM pragma_table_info('universe')"

# The query of the rows of the `universe` table.
_UNIVERSE_QUERY = "SELECT * FROM universe"

# The query of the names of the triggers of a database.
_TRIGGERS_QUERY = (
    "SELECT name FROM sqlite_schema WHERE type = 'trigger' ORDER BY name"
)

# The query of the turns of a database.
_TURNS_QUERY = "SELECT scene, n, role, content FROM _turn ORDER BY n"

# What a child says when `loop_prepare` returned None and its work ended.
_ENDING_PREPARED = repr(None)

# How a child ends when a loop it never prepared returns instead of raising.
_ENDING_RETURNED = "returned"

# How a child ends when the loop exits 1.
_ENDING_FAILED = "exit 1"

# The name of a cache file: the `sha256` of its bytes in hex.
_HASH_NAME = r"^[0-9a-f]{64}$"

# A line whose header has no type, which the decoder refuses.
_BAD_LINE = b'{"0":{"i":3}}\r'

# The database the reopening test and the push test make.
_CASTLE_DB = "castle"

# The database the push test makes and drops.
_DROPPED_DB = "dropped"

# The database of the server's log, under the root.
_LOG_DB = "_verbose"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"


# A copy of a value of this module's gold, which the test may change.
def _gold_copy(name: str) -> Any:
    return copy.deepcopy(harness.gold_get(f"{_GOLD_ID}.{name}"))


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# The bytes of a gold line on the wire: its JSON text, a CR, then each blob.
def _line_bytes(name: str, *blobs: bytes) -> bytes:
    line: dict[str, Any] = _gold_copy(f"lines.{name}")
    size_name = "size" if "type" in line["0"] else "s"
    for number, blob in enumerate(blobs, 1):
        line[str(number)][size_name] = len(blob)
    text = json.dumps(line, ensure_ascii=False, separators=(",", ":"))
    return b"".join([text.encode("utf-8"), b"\r", *blobs])


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


# Reads a seed file of the checkout.
def _seed_read(name: str) -> bytes:
    with open(os.path.join(_SEED_PATH, name), "rb") as file:
        return file.read()


# The JSON text of a value, as the server stores a setting.
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


# The key, size and hash of every row of each fixed database of the root.
def _rows_snapshot(root: str) -> dict[str, list[Any]]:
    return {db: _rows_read(root, db, _HASHES_QUERY) for db in _FIXED_DBS}


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
        ending = work(read_fd, write_fd)
    except SystemExit as error:
        ending = f"exit {error.code}"
    except BaseException:
        ending = traceback.format_exc()
    with open(path, "w", encoding="utf-8") as file:
        file.write(ending)
    os.kill(os.getpid(), signal.SIGKILL)


# Opens the root's log with the ring of its settings, through `main_loop`.
def _log_open(root: str) -> None:
    path = os.path.join(root, "settings.json")
    with open(path, encoding="utf-8") as file:
        values: dict[str, Any] = json.load(file)
    main_loop.verbose.log_open(root, values["verbose_ring"])


# The thread and text of each line of the root's log, in order.
def _log_read(root: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = _rows_read(root, _LOG_DB, _LOG_QUERY)
    return rows


# The work of a child that prepares the root and says what the prepare gave.
def _prepare_once(root: str, read_fd: int, write_fd: int) -> str:
    _log_open(root)
    return repr(main_loop.loop_prepare(root))


# The work of a child that prepares the root and serves the pipes to the end.
def _loop_serve(root: str, read_fd: int, write_fd: int) -> str:
    _log_open(root)
    prepared = repr(main_loop.loop_prepare(root))
    main_loop.loop_run(read_fd, write_fd, root)
    return prepared


# The work of a child that runs the loop on a root it never prepared.
def _loop_unprepared(root: str, read_fd: int, write_fd: int) -> str:
    main_loop.loop_run(read_fd, write_fd, root)
    return _ENDING_RETURNED


# Gives each test a scratch directory in `build/` that holds an empty root.
class ScratchCase(unittest.TestCase):
    # Makes the scratch directory and the root in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)

    # Writes the checkout's settings, with the changes, as the root's.
    def settings_write(self, **changes: Any) -> dict[str, Any]:
        values = harness.settings_copy()
        values.update(changes)
        path = os.path.join(self.root, "settings.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(values, file)
        return values

    # Runs the work in a child fed the data, returns its ending and output.
    def child_run(
        self, work: Callable[[int, int], str], data: bytes
    ) -> tuple[str, bytes]:
        input_read, input_write = os.pipe()
        os.set_blocking(input_write, False)
        self.assertEqual(os.write(input_write, data), len(data))
        os.close(input_write)
        output_read, output_write = os.pipe()
        path = os.path.join(self.scratch, "ending.txt")
        pid = os.fork()
        if pid == 0:
            os.close(output_read)
            _child_end(work, input_read, output_write, path)
        os.close(input_read)
        os.close(output_write)
        output = _pipe_drain(output_read)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(path)
        return ending, output

    # Checks that a child's prepare returned None and its work ended.
    def prepared_check(self, ending: str) -> None:
        if ending != _ENDING_PREPARED:
            self.fail(ending)


# `loop_prepare`: the databases made and seeded, read from the root's files.
class TestPrepare(ScratchCase):
    # Prepares the root in a child, which writes nothing on the pipe.
    def prepare_run(self) -> None:
        work = functools.partial(_prepare_once, self.root)
        ending, output = self.child_run(work, b"")
        self.assertEqual(output, b"")
        self.prepared_check(ending)

    # Checks the seeded metaverse: heads, `universe` and its two triggers.
    def metaverse_check(self) -> None:
        heads = _rows_read(self.root, "metaverse", _HEADS_QUERY)
        self.assertEqual(heads, _SEED_HEADS)
        columns = _rows_read(self.root, "metaverse", _COLUMNS_QUERY)
        self.assertEqual(columns, _UNIVERSE_COLUMNS)
        triggers = _rows_read(self.root, "metaverse", _TRIGGERS_QUERY)
        self.assertEqual(triggers, _UNIVERSE_TRIGGERS)

    # An empty root gets the databases, the settings and the seed.
    def test_root_empty(self) -> None:
        values = self.settings_write()
        self.prepare_run()
        rows = _rows_read(self.root, "_settings", _ROWS_QUERY)
        stored = {row[0]: row[1] for row in rows}
        expected = {key: _json_bytes(value) for key, value in values.items()}
        self.assertEqual(stored, expected)
        preferences = _rows_read(self.root, "_preferences", _ROWS_QUERY)
        self.assertEqual(preferences, [])
        seeded_files = (
            (_PROVIDER_KEY, _seed_read("provider_script.json")),
            ("script/bootstrap.js", _seed_read("bootstrap.js")),
        )
        files = _rows_read(self.root, "_files", _HASHES_QUERY)
        expected = [
            (key, len(data), hashlib.sha256(data).digest())
            for key, data in seeded_files
        ]
        self.assertEqual(files, expected)
        self.metaverse_check()
        for name in _SEED_IDS:
            document = _value_read(self.root, "metaverse", name + "/1")
            seed = _seed_read(name + ".json")
            self.assertEqual(json.loads(document), json.loads(seed))
        seeded = {
            key: _value_read(self.root, "metaverse", key)
            for key in _METAVERSE_ROWS
        }
        self.assertEqual(seeded, _METAVERSE_ROWS)
        universes = _rows_read(self.root, "metaverse", _UNIVERSE_QUERY)
        self.assertEqual(universes, [])

    # The triggers refuse a second row naming a world, by insert or update.
    def test_world_ambiguous(self) -> None:
        self.settings_write()
        self.prepare_run()
        path = os.path.join(self.root, "metaverse.sqlite")
        statements = (
            "INSERT INTO universe VALUES ('b', 'B', 'player', 'w')",
            "UPDATE universe SET world = 'w' WHERE name = 'c'",
        )
        with contextlib.closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO universe VALUES"
                    " ('a', 'A', 'player', 'w'), ('c', 'C', 'player', 'x')"
                )
            for statement in statements:
                with self.assertRaises(sqlite3.IntegrityError) as caught:
                    with connection:
                        connection.execute(statement)
                self.assertEqual(str(caught.exception), _AMBIGUOUS)
        universes = _rows_read(self.root, "metaverse", _UNIVERSE_QUERY)
        expected = [("a", "A", "player", "w"), ("c", "C", "player", "x")]
        self.assertEqual(sorted(universes), expected)

    # A new process on the prepared root changes no row and seeds nothing.
    def test_prepare_again(self) -> None:
        self.settings_write()
        self.prepare_run()
        first = _rows_snapshot(self.root)
        self.prepare_run()
        self.assertEqual(_rows_snapshot(self.root), first)
        self.metaverse_check()

    # A changed setting rewrites its row, in `_settings` only.
    def test_setting_changed(self) -> None:
        values = self.settings_write()
        self.prepare_run()
        before = _rows_snapshot(self.root)
        ring = values["verbose_ring"] + 1
        self.settings_write(verbose_ring=ring)
        self.prepare_run()
        after = _rows_snapshot(self.root)
        stored = _value_read(self.root, "_settings", "verbose_ring")
        self.assertEqual(stored, _json_bytes(ring))
        for db in _FIXED_DBS:
            if db != "_settings":
                self.assertEqual(after[db], before[db], db)

    # A metaverse file without `universe`, as a kill leaves it, is seeded.
    def test_metaverse_empty(self) -> None:
        self.settings_write()
        with open(os.path.join(self.root, "metaverse.sqlite"), "xb"):
            pass
        self.prepare_run()
        self.metaverse_check()
        seeded = {
            key: _value_read(self.root, "metaverse", key)
            for key in _METAVERSE_ROWS
        }
        self.assertEqual(seeded, _METAVERSE_ROWS)

    # A provider script in `_files` is kept, and a missing one seeded again.
    def test_provider_kept(self) -> None:
        self.settings_write()
        self.prepare_run()
        path = os.path.join(self.root, "_files.sqlite")
        own = b'{"start":"own","nodes":{"own":{"replies":{}}}}'
        digest = hashlib.sha256(own).digest()
        with contextlib.closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE _kv SET size = ?, sha256 = ?, data = ?"
                    " WHERE key = ?",
                    (len(own), digest, own, _PROVIDER_KEY),
                )
        self.prepare_run()
        kept = _value_read(self.root, "_files", _PROVIDER_KEY)
        self.assertEqual(kept, own)
        with contextlib.closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute(
                    "DELETE FROM _kv WHERE key = ?", (_PROVIDER_KEY,)
                )
        self.prepare_run()
        seeded = _value_read(self.root, "_files", _PROVIDER_KEY)
        self.assertEqual(seeded, _seed_read("provider_script.json"))


# `loop_run` over pipes: the pushes, the replies, failures and the end.
class TestLoop(ScratchCase):
    # Writes settings that stream small blobs and split reads, and the work.
    def setUp(self) -> None:
        super().setUp()
        self.values = self.settings_write(
            overflow_bytes=_OVERFLOW_BYTES, chunk_bytes=_CHUNK_BYTES
        )
        self.work = functools.partial(_loop_serve, self.root)

    # Writes the settings of the test with `debug` as given.
    def debug_write(self, debug: bool, **changes: Any) -> None:
        self.values = self.settings_write(
            debug=debug,
            overflow_bytes=_OVERFLOW_BYTES,
            chunk_bytes=_CHUNK_BYTES,
            **changes,
        )

    # The gold line of an `error` that answers no line, in the debug form.
    def error_name(self) -> str:
        return "error_full" if self.values["debug"] else "error"

    # Checks that a line read back has the header of a gold line.
    def header_check(self, line: dict[str, Any], name: str) -> None:
        self.assertEqual(line["0"], _gold_copy(f"lines.{name}")["0"])

    # Checks an `error`: the gold's header, the message, its stack, no cause.
    def error_check(
        self, line: dict[str, Any], name: str, message: str
    ) -> None:
        self.header_check(line, name)
        self.assertEqual(sorted(_payload_of(line)), ["message", "stack"])
        self.assertEqual(line["message"], message)
        self.assertTrue(line["stack"].endswith(": " + message))

    # Runs the loop on data it serves to the end, and returns its output.
    def served_read(self, data: bytes) -> list[dict[str, Any]]:
        ending, output = self.child_run(self.work, data)
        self.prepared_check(ending)
        return _lines_read(output)

    # Runs the loop on data that fails, and returns its lines, the error last.
    def failure_read(self, data: bytes) -> list[dict[str, Any]]:
        ending, output = self.child_run(self.work, data)
        self.assertEqual(ending, _ENDING_FAILED)
        return _lines_read(output)

    # A value pushed is in the root's `_files`, byte for byte, unanswered.
    def test_put_get(self) -> None:
        value = bytes(range(256))
        replies = self.served_read(_line_bytes("put_value", value))
        self.assertEqual(replies, [])
        [(size, sha256)] = _rows_read(
            self.root,
            "_files",
            "SELECT size, sha256 FROM _kv WHERE key = ?",
            "test/value",
        )
        self.assertEqual(size, len(value))
        self.assertEqual(sha256, hashlib.sha256(value).digest())
        self.assertEqual(_value_read(self.root, "_files", "test/value"), value)

    # A blob over `overflow_bytes` streams to the cache, named by its digest.
    def test_blob_streamed(self) -> None:
        value = bytes(index % 256 for index in range(_STREAMED_BYTES))
        put = _line_bytes("put_streamed", value)
        self.assertEqual(self.served_read(put), [])
        digest = hashlib.sha256(value).hexdigest()
        names = os.listdir(os.path.join(self.root, "cache"))
        self.assertIn(digest, names)
        for name in names:
            self.assertRegex(name, _HASH_NAME)
        stored = _value_read(self.root, "_files", "test/streamed")
        self.assertEqual(stored, value)

    # A database a push made in one process is open in the next one.
    def test_databases_reopened(self) -> None:
        create = _line_bytes("create_castle")
        title = _line_bytes("put_title", b"The castle")
        self.assertEqual(self.served_read(create + title), [])
        gate = _line_bytes("put_gate", b"The gate")
        self.assertEqual(self.served_read(gate), [])
        rows = _rows_read(self.root, _CASTLE_DB, _ROWS_QUERY + " ORDER BY key")
        expected = [("gate", b"The gate"), ("title", b"The castle")]
        self.assertEqual(rows, expected)

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

    # An unknown type gets one `error` line with its id, and nothing after.
    def test_type_unknown(self) -> None:
        unknown = _line_bytes("unknown_request")
        later = _line_bytes("put_later", b"later")
        replies = self.failure_read(unknown + later)
        self.assertEqual(len(replies), 1)
        message = _text_get("dispatch_handler_unknown")
        self.error_check(replies[0], "error_reply", message)
        rows = _rows_read(self.root, "metaverse", _VALUE_QUERY, "later")
        self.assertEqual(rows, [])

    # Outside debug mode a failure's message is logged, its `error` line sent.
    def test_failure_logged(self) -> None:
        self.debug_write(False)
        replies = self.failure_read(_line_bytes("unknown_request"))
        message = _text_get("dispatch_handler_unknown")
        self.error_check(replies[0], "error_reply", message)
        text = _text_get("main_loop_serve_failed_unknown")
        self.assertEqual(_log_read(self.root), [(_SERVER_THREAD, text)])

    # In debug mode a failure is logged after the trace of its line.
    def test_failure_traced(self) -> None:
        self.debug_write(True)
        replies = self.failure_read(_line_bytes("unknown_request"))
        message = _text_get("dispatch_handler_unknown")
        self.error_check(replies[0], "error_reply", message)
        texts = [
            _text_get("main_loop_line_dispatch_unknown"),
            _text_get("main_loop_serve_failed_unknown"),
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # A fault of the input with no line is logged the same way.
    def test_fault_logged(self) -> None:
        replies = self.failure_read(_BAD_LINE)
        message = _text_get("jslb_no_type")
        self.error_check(replies[0], self.error_name(), message)
        text = _text_get("main_loop_serve_failed_type")
        self.assertEqual(_log_read(self.root), [(_SERVER_THREAD, text)])

    # An `error` line that answers no line is in full names in debug mode.
    def test_fault_names(self) -> None:
        for debug, name in ((True, "error_full"), (False, "error")):
            with self.subTest(debug=debug):
                self.debug_write(debug)
                (error,) = self.failure_read(_BAD_LINE)
                self.header_check(error, name)

    # In debug mode the log traces each line and reply, at the shell's level 0.
    def test_trace_logged(self) -> None:
        self.debug_write(True, verbose_level=0)
        replies = self.served_read(_line_bytes("initialize"))
        self.assertEqual(len(replies), 1)
        texts = [
            _text_get("main_loop_line_dispatch_mcp"),
            _text_get("main_loop_line_reply_mcp"),
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # Outside debug mode nothing is traced, whatever the shell's level.
    def test_trace_quiet(self) -> None:
        self.debug_write(False, verbose_level=2)
        replies = self.served_read(_line_bytes("initialize"))
        self.assertEqual(len(replies), 1)
        self.assertEqual(_log_read(self.root), [])

    # A reply, to `tap.start` or to any other id, gets an `error` line, no id.
    def test_reply_unknown(self) -> None:
        for reply in ("101", "102", "2"):
            replies = self.failure_read(_line_bytes(f"stray_{reply}"))
            self.assertEqual(len(replies), 1)
            message = _text_get(f"main_loop_reply_unknown_{reply}")
            self.error_check(replies[0], "error", message)

    # Bytes that are no line get an `error` line with no id.
    def test_line_bad(self) -> None:
        replies = self.failure_read(_BAD_LINE)
        self.assertEqual(len(replies), 1)
        message = _text_get("jslb_no_type")
        self.error_check(replies[0], self.error_name(), message)

    # A line before a fault in the same read is served, then the fault ends it.
    def test_fault_after(self) -> None:
        replies = self.failure_read(_line_bytes("initialize") + _BAD_LINE)
        self.assertEqual(len(replies), 2)
        answer, error = replies
        self.assertEqual(answer, _gold_copy("lines.initialize_reply"))
        message = _text_get("jslb_no_type")
        self.error_check(error, self.error_name(), message)

    # The end of the input between messages returns with nothing written.
    def test_end_returns(self) -> None:
        self.assertEqual(self.served_read(b""), [])

    # The end of the input inside a line or inside a blob is an `error` line.
    def test_end_partial(self) -> None:
        line = _line_bytes("initialize")
        blob = _line_bytes("put_cut", bytes(10))
        message = _text_get("main_loop_input_partial")
        for data in (line[:-1], blob[:-1]):
            replies = self.failure_read(data)
            self.assertEqual(len(replies), 1)
            self.error_check(replies[0], self.error_name(), message)

    # `loop_run` raises when `loop_prepare` has not run in the process.
    def test_run_unprepared(self) -> None:
        work = functools.partial(_loop_unprepared, self.root)
        ending, output = self.child_run(work, b"")
        self.assertEqual(output, b"")
        last = ending.rstrip("\n").rsplit("\n", 1)[-1]
        message = _text_get("main_loop_not_prepared")
        self.assertEqual(last, f"RuntimeError: {message}")

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

    # The browser's `error` is logged and bailed out, then exit 1, no answer.
    def test_browser_error(self) -> None:
        self.debug_write(False)
        error = _gold_copy("lines.browser_error")
        data = _line_bytes("browser_error") + _line_bytes("initialize")
        ending, output = self.child_run(self.work, data)
        self.assertEqual(ending, _ENDING_FAILED)
        self.assertEqual(output, b"")
        path = os.path.join(self.root, "tap", "typescript.tap")
        bail = "Bail out! " + error["message"] + "\n"
        with open(path, "rb") as file:
            self.assertEqual(file.read(), bail.encode("utf-8"))
        texts = [
            _text_get("engine_tap_browser_failed"),
            error["stack"],
            _text_get("engine_tap_browser_cause"),
            error["cause"]["stack"],
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # A `Failure` writes its reply, then the server's `error` line, no `r`.
    def test_failure_answered(self) -> None:
        self.debug_write(False)
        replies = self.failure_read(_line_bytes("call_debug_off"))
        self.assertEqual(len(replies), 2)
        answer, error = replies
        self.header_check(answer, "call_reply")
        self.assertIs(answer["result"]["isError"], True)
        message = _text_get("engine_system_debug_off_tool")
        self.error_check(error, "error", message)
        text = _text_get("main_loop_serve_failed_debug")
        self.assertEqual(_log_read(self.root), [(_SERVER_THREAD, text)])

    # In debug mode the server's `error` after a `Failure` is in full names.
    def test_failure_full(self) -> None:
        self.debug_write(True)
        replies = self.failure_read(_line_bytes("call_name_invalid"))
        self.assertEqual(len(replies), 2)
        answer, error = replies
        self.header_check(answer, "call_reply")
        self.assertIs(answer["result"]["isError"], True)
        message = _text_get("engine_system_name_invalid")
        self.error_check(error, "error_full", message)

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

    # With `debug` false, `source.put` gets an `error` line and writes nothing.
    def test_debug_off(self) -> None:
        self.debug_write(False)
        replies = self.failure_read(_line_bytes("source_put", b"pass\n"))
        self.assertEqual(len(replies), 1)
        message = _text_get("engine_system_debug_off_line")
        self.error_check(replies[0], "error_reply", message)
        directory = os.path.join(self.root, "main_loop")
        self.assertFalse(os.path.exists(directory))
