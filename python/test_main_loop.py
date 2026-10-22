# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the main loop in forked children over pipes, with roots in `build/`.
# Each child opens the root's log first, as `bootstrap.py` does.

import contextlib, functools, hashlib, jslb, json, main_loop, os, signal
import sqlite3, tempfile, traceback, unittest, verbose
from collections.abc import Callable
from i18n import i18n
from typing import Any, NoReturn

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The settings file of the checkout, which holds a valid settings object.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# The seed files that the main loop reads for a new metaverse.
_SEED_PATH = os.path.join(_ROOT_PATH, "python", "seed")

# The API file that holds the tools as `tools/list` returns them.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The `initialize` request the AI worker's MCP client sends the server.
_INITIALIZE_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "hyperposition-engine", "version": "0"},
    },
}

# The notification the client sends once the `initialize` reply is in.
_INITIALIZED_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
}

# The `tools/list` request the client sends after the notification.
_LIST_MESSAGE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
}

# The response to `initialize`: the pinned revision, `tools`, the server.
_INITIALIZE_RESPONSE: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "protocolVersion": "2025-06-18",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "xsjs-server", "version": "0"},
    },
}

# A size chosen by its writer, small: a blob over it streams to the cache.
_OVERFLOW_BYTES = 4096

# A size chosen by its writer: the most the loop reads, so lines split.
_CHUNK_BYTES = 1000

# A size chosen by its writer: a blob that streams, over `_OVERFLOW_BYTES`.
_STREAMED_BYTES = _OVERFLOW_BYTES * 2 + 1

# A size chosen by its writer: the most the test reads from the pipe.
_READ_BYTES = 65536

# The `seq` of a new database, which its creation leaves as it was.
_SEQ_CREATED = 0

# The `seq` of `_files` on a new root: the provider's script, then bootstrap's.
_FILES_SEQ = 2

# The key of the scripted provider's script in `_files`.
_PROVIDER_KEY = "provider/script.json"

# The `seq` of `_preferences` on a new root, which nothing writes.
_PREFERENCES_SEQ = 0

# The `seq` of `metaverse` on a new root: its table, two documents, three rows.
_METAVERSE_SEQ = 1 + 2 + 3

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

# The query of every key and value of a database.
_ROWS_QUERY = "SELECT key, data FROM _kv"

# The query of every key, size and hash of a database.
_HASHES_QUERY = "SELECT key, size, sha256 FROM _kv"

# The query of the hash and the value of one key.
_VALUE_QUERY = "SELECT sha256, data FROM _kv WHERE key = ?"

# The query of the heads of the documents.
_HEADS_QUERY = "SELECT id, version FROM _head ORDER BY id"

# The query of the columns of the `universe` table.
_COLUMNS_QUERY = "SELECT name FROM pragma_table_info('universe')"

# The query of the rows of the `universe` table.
_UNIVERSE_QUERY = "SELECT * FROM universe"

# How a child ends when a loop it never prepared returns instead of raising.
_ENDING_RETURNED = "returned"

# How a child ends when the loop exits 1.
_ENDING_FAILED = "exit 1"

# The name of a cache file: the `sha256` of its bytes in hex.
_HASH_NAME = r"^[0-9a-f]{64}$"

# A line whose header has no type, which the decoder refuses.
_BAD_LINE = b'{"0":{"i":3}}\r'

# The database the reopening test and the document test make.
_CASTLE_DB = "castle"

# The id of the document the document test puts.
_NOTE_ID = "note"

# The document the document test puts: its header and a text.
_NOTE_BODY: dict[int | str, Any] = {0: {"t": "note"}, "text": "A note."}

# The version the first put of a document writes.
_NOTE_VERSION = 1

# The main loop file that the refused `source.put` would write.
_SOURCE_NAME = "loop_test.py"

# The database of the server's log, under the root.
_LOG_DB = "_verbose"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"


# Reads the settings file of the checkout as an object.
def _settings_read() -> dict[str, Any]:
    with open(_SETTINGS_PATH, encoding="utf-8") as file:
        data: dict[str, Any] = json.load(file)
    return data


# The response to `tools/list`: each server tool of the API file, no permit.
def _list_response() -> dict[str, Any]:
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


# The `seq` of each database on a new root with these settings.
def _seqs_new(values: dict[str, Any]) -> dict[str, int]:
    return {
        "_settings": len(values),
        "_files": _FILES_SEQ,
        "_preferences": _PREFERENCES_SEQ,
        "metaverse": _METAVERSE_SEQ,
    }


# A request of the type with the id and the payload, with no key or blob.
def _request_make(name: str, request_id: int, **payload: Any) -> jslb.Object:
    return jslb.line_make(jslb.header_make(name, id=request_id), [], **payload)


# A `kv.put` of the value under the ref, `since` the database's `seq`.
def _put_make(
    request_id: int, ref: str, value: bytes, since: int
) -> jslb.Object:
    header = jslb.header_make("kv.put", id=request_id, key=ref)
    return jslb.line_make(header, [jslb.blob_make(value)], since=since)


# A `kv.get` of the ref.
def _get_make(request_id: int, ref: str) -> jslb.Object:
    header = jslb.header_make("kv.get", id=request_id, key=ref)
    return jslb.line_make(header, [])


# Encodes lines whose blobs are all in memory.
def _lines_encode(lines: list[jslb.Object]) -> bytes:
    data = bytearray()
    for line in lines:
        for piece in jslb.line_encode(line):
            if not isinstance(piece, bytes):
                raise AssertionError("a blob is a file, not bytes")
            data += piece
    return bytes(data)


# The sink of a decoder that must stream nothing.
def _sink_refuse(header: jslb.Object) -> NoReturn:
    raise AssertionError("the output streamed a blob")


# Decodes bytes of whole lines whose blobs all stay in memory.
def _lines_decode(data: bytes) -> list[jslb.Object]:
    size = len(data)
    decoder = jslb.LineDecoder(size + 1, size, size, _sink_refuse)
    return decoder.bytes_feed(data)


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


# Opens the root's log with the ring of its settings.
def _log_open(root: str) -> None:
    path = os.path.join(root, "settings.json")
    with open(path, encoding="utf-8") as file:
        values: dict[str, Any] = json.load(file)
    verbose.log_open(root, values["verbose_ring"])


# The thread and text of each line of the root's log, in order.
def _log_read(root: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = _rows_read(root, _LOG_DB, _LOG_QUERY)
    return rows


# The trace texts of a line dispatched and of its reply, if any, in order.
def _trace_texts(request: jslb.Object, reply: jslb.Object | None) -> list[str]:
    texts = [i18n("main_loop.line_dispatch", _json_bytes(request[0]).decode())]
    if reply is not None:
        texts.append(
            i18n("main_loop.line_reply", _json_bytes(reply[0]).decode())
        )
    return texts


# The work of a child that prepares the root and says the `seq` it returned.
def _prepare_once(root: str, read_fd: int, write_fd: int) -> str:
    _log_open(root)
    return json.dumps(main_loop.loop_prepare(root))


# The work of a child that prepares the root and serves the pipes to the end.
def _loop_serve(root: str, read_fd: int, write_fd: int) -> str:
    _log_open(root)
    answers = main_loop.loop_prepare(root)
    main_loop.loop_run(read_fd, write_fd, root)
    return json.dumps(answers)


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
        values = _settings_read()
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

    # Decodes output that must be whole lines, which encode back to it.
    def lines_read(self, output: bytes) -> list[jslb.Object]:
        lines = _lines_decode(output)
        self.assertEqual(_lines_encode(lines), output)
        return lines

    # Reads the `seq` that a child which prepared the root said, or fails.
    def answers_read(self, ending: str) -> dict[str, int]:
        if not ending.startswith("{"):
            self.fail(ending)
        answers: dict[str, int] = json.loads(ending)
        return answers


# `loop_prepare`: the databases made, seeded and counted, in each process.
class TestPrepare(ScratchCase):
    # Prepares the root in a child and returns the `seq` it said.
    def prepare_read(self) -> dict[str, int]:
        work = functools.partial(_prepare_once, self.root)
        ending, output = self.child_run(work, b"")
        self.assertEqual(output, b"")
        return self.answers_read(ending)

    # An empty root gets the databases, their `seq`, the settings and the seed.
    def test_root_empty(self) -> None:
        values = self.settings_write()
        self.assertEqual(self.prepare_read(), _seqs_new(values))
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
        self.assertEqual(sorted(files), expected)
        heads = _rows_read(self.root, "metaverse", _HEADS_QUERY)
        self.assertEqual(heads, _SEED_HEADS)
        for name in _SEED_IDS:
            document = _value_read(self.root, "metaverse", name + "/1")
            seed = _seed_read(name + ".json")
            self.assertEqual(json.loads(document), json.loads(seed))
        seeded = {
            key: _value_read(self.root, "metaverse", key)
            for key in _METAVERSE_ROWS
        }
        self.assertEqual(seeded, _METAVERSE_ROWS)
        columns = _rows_read(self.root, "metaverse", _COLUMNS_QUERY)
        self.assertEqual(columns, _UNIVERSE_COLUMNS)
        universes = _rows_read(self.root, "metaverse", _UNIVERSE_QUERY)
        self.assertEqual(universes, [])

    # A new process on the prepared root answers the same and seeds nothing.
    def test_prepare_again(self) -> None:
        self.settings_write()
        first = self.prepare_read()
        self.assertEqual(self.prepare_read(), first)
        heads = _rows_read(self.root, "metaverse", _HEADS_QUERY)
        self.assertEqual(heads, _SEED_HEADS)

    # A changed setting rewrites its row, one more `seq` in `_settings` only.
    def test_setting_changed(self) -> None:
        values = self.settings_write()
        before = self.prepare_read()
        ring = values["verbose_ring"] + 1
        self.settings_write(verbose_ring=ring)
        changed = {**before, "_settings": before["_settings"] + 1}
        self.assertEqual(self.prepare_read(), changed)
        stored = _value_read(self.root, "_settings", "verbose_ring")
        self.assertEqual(stored, _json_bytes(ring))

    # A metaverse file left at `seq` 0, as a kill leaves it, is seeded anew.
    def test_metaverse_empty(self) -> None:
        values = self.settings_write()
        with open(os.path.join(self.root, "metaverse.sqlite"), "xb"):
            pass
        self.assertEqual(self.prepare_read(), _seqs_new(values))
        heads = _rows_read(self.root, "metaverse", _HEADS_QUERY)
        self.assertEqual(heads, _SEED_HEADS)
        columns = _rows_read(self.root, "metaverse", _COLUMNS_QUERY)
        self.assertEqual(columns, _UNIVERSE_COLUMNS)

    # A provider script in `_files` is kept, and a missing one seeded again.
    def test_provider_kept(self) -> None:
        self.settings_write()
        first = self.prepare_read()
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
        self.assertEqual(self.prepare_read(), first)
        kept = _value_read(self.root, "_files", _PROVIDER_KEY)
        self.assertEqual(kept, own)
        with contextlib.closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute(
                    "DELETE FROM _kv WHERE key = ?", (_PROVIDER_KEY,)
                )
        again = {**first, "_files": first["_files"] + 1}
        self.assertEqual(self.prepare_read(), again)
        seeded = _value_read(self.root, "_files", _PROVIDER_KEY)
        self.assertEqual(seeded, _seed_read("provider_script.json"))


# `loop_run` over pipes: the replies, a streamed blob, failures and the end.
class TestLoop(ScratchCase):
    # Writes settings that stream small blobs and split reads, and the work.
    def setUp(self) -> None:
        super().setUp()
        self.values = self.settings_write(
            overflow_bytes=_OVERFLOW_BYTES, chunk_bytes=_CHUNK_BYTES
        )
        self.work = functools.partial(_loop_serve, self.root)

    # Checks that a line is the reply of the type to the id, or to none.
    def reply_check(
        self, line: jslb.Object, name: str, request_id: int | None
    ) -> None:
        self.assertEqual(jslb.field_get(line[0], "type"), name)
        self.assertEqual(jslb.field_get(line[0], "reply"), request_id)

    # Checks an `error` line: the id it answers and its message.
    def error_check(
        self, line: jslb.Object, request_id: int | None, message: str
    ) -> None:
        self.reply_check(line, "error", request_id)
        self.assertEqual(line["message"], message)

    # Runs the loop on lines it serves, returns the `seq` it said and output.
    def served_read(
        self, lines: list[jslb.Object]
    ) -> tuple[dict[str, int], list[jslb.Object]]:
        ending, output = self.child_run(self.work, _lines_encode(lines))
        return self.answers_read(ending), self.lines_read(output)

    # Runs the loop on data that fails, and returns its lines, the error last.
    def failure_read(self, data: bytes) -> list[jslb.Object]:
        ending, output = self.child_run(self.work, data)
        self.assertEqual(ending, _ENDING_FAILED)
        return self.lines_read(output)

    # A value put and then got comes back byte for byte, with its hash.
    def test_put_get(self) -> None:
        value = bytes(range(256))
        ref = "/_files/test/value"
        lines = [_put_make(1, ref, value, _FILES_SEQ), _get_make(2, ref)]
        _, replies = self.served_read(lines)
        self.assertEqual(len(replies), 2)
        put, got = replies
        digest = hashlib.sha256(value).hexdigest()
        self.reply_check(put, "kv.put", 1)
        self.assertEqual(put["sha256"], digest)
        self.assertEqual(put["seq"], _FILES_SEQ + 1)
        self.reply_check(got, "kv.get", 2)
        self.assertEqual(got[1]["d"], value)
        self.assertEqual(got["size"], len(value))
        self.assertEqual(got["sha256"], digest)

    # A blob over `overflow_bytes` streams to the cache and comes back whole.
    def test_blob_streamed(self) -> None:
        value = bytes(index % 256 for index in range(_STREAMED_BYTES))
        ref = "/_files/test/streamed"
        lines = [_put_make(1, ref, value, _FILES_SEQ), _get_make(2, ref)]
        _, replies = self.served_read(lines)
        self.assertEqual(len(replies), 2)
        put, got = replies
        digest = hashlib.sha256(value).hexdigest()
        self.reply_check(put, "kv.put", 1)
        self.assertEqual(put["sha256"], digest)
        self.reply_check(got, "kv.get", 2)
        self.assertEqual(got[1]["d"], value)
        names = os.listdir(os.path.join(self.root, "cache"))
        self.assertIn(digest, names)
        for name in names:
            self.assertRegex(name, _HASH_NAME)

    # A database a script made in one process is open in the next one.
    def test_databases_reopened(self) -> None:
        ref = f"/{_CASTLE_DB}/title"
        value = b"The castle"
        create = _request_make(
            "db.create", 1, db=_CASTLE_DB, since=_SEQ_CREATED
        )
        lines = [create, _put_make(2, ref, value, _SEQ_CREATED)]
        _, replies = self.served_read(lines)
        self.assertEqual(len(replies), 2)
        created, put = replies
        self.reply_check(created, "db.create", 1)
        self.assertEqual(jslb.payload_of(created), {})
        self.reply_check(put, "kv.put", 2)
        self.assertEqual(put["seq"], _SEQ_CREATED + 1)
        answers, replies = self.served_read([_get_make(1, ref)])
        expected = {**_seqs_new(self.values), _CASTLE_DB: _SEQ_CREATED + 1}
        self.assertEqual(answers, expected)
        self.assertEqual(len(replies), 1)
        self.reply_check(replies[0], "kv.get", 1)
        self.assertEqual(replies[0][1]["d"], value)

    # An unknown type gets one `error` line with its id, and nothing after.
    def test_type_unknown(self) -> None:
        unknown = _request_make("no.such", 1)
        later = _get_make(2, "/metaverse/world")
        replies = self.failure_read(_lines_encode([unknown, later]))
        self.assertEqual(len(replies), 1)
        message = i18n("dispatch.handler_unknown", "no.such", 0)
        self.error_check(replies[0], 1, message)

    # Outside debug mode a failure's message is logged, its `error` line sent.
    def test_failure_logged(self) -> None:
        self.settings_write(
            debug=False,
            overflow_bytes=_OVERFLOW_BYTES,
            chunk_bytes=_CHUNK_BYTES,
        )
        unknown = _request_make("no.such", 1)
        replies = self.failure_read(_lines_encode([unknown]))
        message = i18n("dispatch.handler_unknown", "no.such", 0)
        self.error_check(replies[0], 1, message)
        text = i18n("main_loop.serve_failed", message)
        self.assertEqual(_log_read(self.root), [(_SERVER_THREAD, text)])

    # In debug mode a failure is logged after the trace of its line.
    def test_failure_traced(self) -> None:
        self.settings_write(
            debug=True,
            overflow_bytes=_OVERFLOW_BYTES,
            chunk_bytes=_CHUNK_BYTES,
        )
        unknown = _request_make("no.such", 1)
        replies = self.failure_read(_lines_encode([unknown]))
        message = i18n("dispatch.handler_unknown", "no.such", 0)
        self.error_check(replies[0], 1, message)
        texts = [
            *_trace_texts(unknown, None),
            i18n("main_loop.serve_failed", message),
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # A fault of the input with no line is logged the same way.
    def test_fault_logged(self) -> None:
        replies = self.failure_read(_BAD_LINE)
        message = i18n("jslb.no_type")
        self.error_check(replies[0], None, message)
        text = i18n("main_loop.serve_failed", message)
        self.assertEqual(_log_read(self.root), [(_SERVER_THREAD, text)])

    # In debug mode the log traces each line and reply, at the shell's level 0.
    def test_trace_logged(self) -> None:
        self.settings_write(
            debug=True,
            overflow_bytes=_OVERFLOW_BYTES,
            chunk_bytes=_CHUNK_BYTES,
            verbose_level=0,
        )
        request = _get_make(1, "/metaverse/world")
        _, replies = self.served_read([request])
        self.assertEqual(len(replies), 1)
        texts = _trace_texts(request, replies[0])
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # Outside debug mode nothing is traced, whatever the shell's level.
    def test_trace_quiet(self) -> None:
        self.settings_write(
            debug=False,
            overflow_bytes=_OVERFLOW_BYTES,
            chunk_bytes=_CHUNK_BYTES,
            verbose_level=2,
        )
        _, replies = self.served_read([_get_make(1, "/metaverse/world")])
        self.assertEqual(len(replies), 1)
        self.assertEqual(_log_read(self.root), [])

    # A reply, to `hello` or to any other id, gets an `error` line with no id.
    def test_reply_unknown(self) -> None:
        strays = [
            jslb.line_make(jslb.header_make("hello", reply=1), []),
            jslb.line_make(jslb.header_make("kv.get", reply=1), []),
            jslb.line_make(jslb.header_make("hello", reply=2), []),
        ]
        for stray in strays:
            replies = self.failure_read(_lines_encode([stray]))
            self.assertEqual(len(replies), 1)
            message = i18n("main_loop.reply_unknown", jslb.line_render(stray))
            self.error_check(replies[0], None, message)

    # Bytes that are no line get an `error` line with no id.
    def test_line_bad(self) -> None:
        replies = self.failure_read(_BAD_LINE)
        self.assertEqual(len(replies), 1)
        self.error_check(replies[0], None, i18n("jslb.no_type"))

    # A line before a fault in the same read is served, then the fault ends it.
    def test_fault_after(self) -> None:
        data = _lines_encode([_get_make(1, "/metaverse/world")]) + _BAD_LINE
        replies = self.failure_read(data)
        self.assertEqual(len(replies), 2)
        got, error = replies
        self.reply_check(got, "kv.get", 1)
        self.assertEqual(got[1]["d"], _METAVERSE_ROWS["world"])
        self.error_check(error, None, i18n("jslb.no_type"))

    # The end of the input between messages returns with nothing written.
    def test_end_returns(self) -> None:
        answers, replies = self.served_read([])
        self.assertEqual(answers, _seqs_new(self.values))
        self.assertEqual(replies, [])

    # The end of the input inside a line or inside a blob is an `error` line.
    def test_end_partial(self) -> None:
        line = _lines_encode([_get_make(1, "/metaverse/world")])
        put = _put_make(1, "/_files/test/cut", bytes(10), _FILES_SEQ)
        blob = _lines_encode([put])
        message = i18n("main_loop.input_partial")
        for data in (line[:-1], blob[:-1]):
            replies = self.failure_read(data)
            self.assertEqual(len(replies), 1)
            self.error_check(replies[0], None, message)

    # `loop_run` raises when `loop_prepare` has not run in the process.
    def test_run_unprepared(self) -> None:
        work = functools.partial(_loop_unprepared, self.root)
        ending, output = self.child_run(work, b"")
        self.assertEqual(output, b"")
        last = ending.rstrip("\n").rsplit("\n", 1)[-1]
        message = i18n("main_loop.not_prepared")
        self.assertEqual(last, f"RuntimeError: {message}")

    # The server's MCP server answers `initialize` and `tools/list` only.
    def test_mcp_tools(self) -> None:
        notice = jslb.line_make(
            jslb.header_make("mcp"), [], **_INITIALIZED_MESSAGE
        )
        lines = [
            _request_make("mcp", 1, **_INITIALIZE_MESSAGE),
            notice,
            _request_make("mcp", 2, **_LIST_MESSAGE),
        ]
        _, replies = self.served_read(lines)
        self.assertEqual(len(replies), 2)
        first, second = replies
        self.reply_check(first, "mcp", 1)
        self.assertEqual(jslb.payload_of(first), _INITIALIZE_RESPONSE)
        self.reply_check(second, "mcp", 2)
        self.assertEqual(jslb.payload_of(second), _list_response())

    # `doc.put` replies the first version's ref and `seq`, `doc.head` the ref.
    def test_doc_head(self) -> None:
        create = _request_make(
            "db.create", 1, db=_CASTLE_DB, since=_SEQ_CREATED
        )
        put = _request_make(
            "doc.put",
            2,
            db=_CASTLE_DB,
            id=_NOTE_ID,
            body=_NOTE_BODY,
            since=_SEQ_CREATED,
        )
        head = _request_make("doc.head", 3, db=_CASTLE_DB, id=_NOTE_ID)
        _, replies = self.served_read([create, put, head])
        self.assertEqual(len(replies), 3)
        created, written, current = replies
        ref = f"/{_CASTLE_DB}/{_NOTE_ID}/{_NOTE_VERSION}"
        self.reply_check(created, "db.create", 1)
        self.reply_check(written, "doc.put", 2)
        self.assertEqual(
            jslb.payload_of(written), {"ref": ref, "seq": _SEQ_CREATED + 1}
        )
        self.reply_check(current, "doc.head", 3)
        self.assertEqual(jslb.payload_of(current), {"ref": ref})

    # `verbose.tail` gives the server's ring, its own trace, and the page's.
    def test_verbose_tail(self) -> None:
        self.settings_write(
            debug=True,
            overflow_bytes=_OVERFLOW_BYTES,
            chunk_bytes=_CHUNK_BYTES,
        )
        entries = [{"at": 1, "text": "first"}, {"at": 2, "text": "second"}]
        put = jslb.line_make(
            jslb.header_make("verbose.put"), [], thread="ui", lines=entries
        )
        tail = _request_make("verbose.tail", 1, thread="server", count=10)
        lines = [
            tail,
            put,
            _request_make("verbose.tail", 2, thread="ui", count=10),
        ]
        _, replies = self.served_read(lines)
        self.assertEqual(len(replies), 2)
        server, page = replies
        self.reply_check(server, "verbose.tail", 1)
        texts = [entry["text"] for entry in server["lines"]]
        self.assertEqual(texts, _trace_texts(tail, None))
        self.reply_check(page, "verbose.tail", 2)
        self.assertEqual(jslb.payload_of(page), {"lines": entries})

    # With `debug` false, `source.put` gets an `error` line and writes nothing.
    def test_debug_off(self) -> None:
        self.settings_write(
            debug=False,
            overflow_bytes=_OVERFLOW_BYTES,
            chunk_bytes=_CHUNK_BYTES,
        )
        header = jslb.header_make("source.put", id=1)
        blobs = [jslb.blob_make(b"pass\n")]
        source = jslb.line_make(header, blobs, name=_SOURCE_NAME)
        replies = self.failure_read(_lines_encode([source]))
        self.assertEqual(len(replies), 1)
        message = i18n("engine_system.debug_off", "source.put")
        self.error_check(replies[0], 1, message)
        directory = os.path.join(self.root, "main_loop")
        self.assertFalse(os.path.exists(directory))
