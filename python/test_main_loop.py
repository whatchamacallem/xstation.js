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
# server's own `error` line, in the name form of the parameter `debug`,
# which each serving child sets from the root's parameters as `bootstrap.py`
# does. A handler's `dispatch.Stream`, registered through `dispatch` by the
# child, writes its pushes, then its reply, each traced in full or by its
# sizes. The analyst's seeded table is walked against the gold and the tools.

import contextlib, copy, dispatch, functools, harness, hashlib, jslb, json
import main_loop, os, re, runpy, shutil, signal, sqlite3, switches, tempfile
import traceback, unittest
from collections.abc import Callable, Iterator
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The seed files that the main loop reads for a new metaverse.
_SEED_PATH = os.path.join(_ROOT_PATH, "python", "seed")

# The main loop's file, which a root's link names beside a seed of its own.
_MODULE_PATH = os.path.join(_ROOT_PATH, "python", "main_loop.py")

# The tool list, which names the browser's tools the analyst's table calls.
_TOOLS_PATH = os.path.join(_ROOT_PATH, "API", "mcp", "tools.json")

# The prefix of a browser tool's name in a tool call.
_BROWSER_PREFIX = "browser."

# The id of this module's gold, in its own `test_setting_` file.
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

# The database the reopening test makes.
_CASTLE_DB = "castle"

# The database of the server's log, under the root.
_LOG_DB = "_verbose"

# The query of the thread and text of each line of the log, in order.
_LOG_QUERY = "SELECT thread, text FROM line ORDER BY seq"

# The thread the server's own lines are stored under in the log.
_SERVER_THREAD = "server"

# The thread of the gold's `verbose.put`, whose entry the log stores under it.
_PAGE_THREAD = "ui"

# The type of the request that a stream answers.
_STREAM_TYPE = "test.stream"

# The type of the request whose stream fails between its pushes.
_FAULT_TYPE = "test.fault"

# The type of a push of those streams.
_PUSH_TYPE = "test.push"

# The texts of a stream's pushes, each its blob's bytes too.
_PUSH_TEXTS: list[str] = harness.gold_get(f"{_GOLD_ID}.push_texts")

# A `line_max` chosen by its writer: no entry of a stream fits under it.
_LINE_SMALL: int = harness.gold_get(f"{_GOLD_ID}.line_small")

# A clock reading in milliseconds, as wide as every reading of this century.
_AT_SAMPLE: int = harness.gold_get(f"{_GOLD_ID}.at_sample")


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


# Reads a seed file of the checkout.
def _seed_read(name: str) -> bytes:
    with open(os.path.join(_SEED_PATH, name), "rb") as file:
        return file.read()


# The names of the browser's tools in the tool list, each with its prefix.
def _tools_browser() -> set[str]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        tools: list[dict[str, Any]] = json.load(file)["browser"]["result"][
            "tools"
        ]
    return {_BROWSER_PREFIX + tool["name"] for tool in tools}


# Every reply of the table: each node's by input, then its `after_tools`.
def _replies_all(script: dict[str, Any]) -> list[dict[str, Any]]:
    replies: list[dict[str, Any]] = []
    for node in script["nodes"].values():
        replies.extend(node["replies"].values())
        if "after_tools" in node:
            replies.append(node["after_tools"])
    return replies


# A tool call of the table as the gold has it, its arguments decoded.
def _call_read(call: dict[str, Any]) -> dict[str, Any]:
    function = call["function"]
    arguments = json.loads(function["arguments"])
    return {"arguments": arguments, "name": function["name"]}


# Every tool call of the table, as the gold has them.
def _calls_all(script: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _call_read(call)
        for reply in _replies_all(script)
        if "tool_calls" in reply
        for call in reply["tool_calls"]
    ]


# Walks an input as the scripted provider does: its rounds, its last reply.
def _input_walk(
    script: dict[str, Any], node: str, text: str
) -> tuple[list[list[dict[str, Any]]], dict[str, Any]]:
    reply = script["nodes"][node]["replies"][text]
    rounds: list[list[dict[str, Any]]] = []
    while "tool_calls" in reply:
        rounds.append([_call_read(call) for call in reply["tool_calls"]])
        reply = script["nodes"][reply["next"]]["after_tools"]
    return rounds, reply


# A tool call with only the arguments the gold pins, as the texts are free.
def _call_trim(
    call: dict[str, Any], pinned: dict[str, Any]
) -> dict[str, Any]:
    arguments = call["arguments"]
    kept = {key: arguments[key] for key in pinned["arguments"]}
    return {"arguments": kept, "name": call["name"]}


# The rounds of a walk with only the arguments the gold's rounds pin.
def _rounds_trim(
    rounds: list[list[dict[str, Any]]], gold: list[list[dict[str, Any]]]
) -> list[list[dict[str, Any]]]:
    return [
        [_call_trim(*pair) for pair in zip(calls, pinned, strict=True)]
        for calls, pinned in zip(rounds, gold, strict=True)
    ]


# The JSON text of a value, as the server stores a setting.
def _json_bytes(value: object) -> bytes:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8")


# The bytes of one `verbose.put` of the server holding an entry of the text.
def _put_bytes(text: str) -> int:
    put = {
        "0": {"type": "verbose.put"},
        "thread": _SERVER_THREAD,
        "lines": [{"at": _AT_SAMPLE, "text": text}],
    }
    return len(_json_bytes(put))


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
    main_loop.verbose.log_open(
        root, values["verbose_ring"], values["blob_max"]
    )


# The thread and text of each line of the root's log, in order.
def _log_read(root: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = _rows_read(root, _LOG_DB, _LOG_QUERY)
    return rows


# The thread and text of the trace of an `error` line, as the loop wrote it.
def _error_row(line: dict[str, Any]) -> tuple[str, str]:
    text = _json_bytes(line).decode("utf-8")
    return (_SERVER_THREAD, _text_get("main_loop_line_error").format(text))


# The work of a child that prepares the root and says what the prepare gave.
def _prepare_once(root: str, read_fd: int, write_fd: int) -> str:
    _log_open(root)
    return repr(main_loop.loop_prepare(root))


# The work of a child that prepares the root by the module run from a link.
def _prepare_linked(root: str, link: str, read_fd: int, write_fd: int) -> str:
    _log_open(root)
    return repr(runpy.run_path(link)["loop_prepare"](root))


# The work of a child that prepares the root and serves the pipes to the end.
def _loop_serve(root: str, read_fd: int, write_fd: int) -> str:
    switches.switches_apply(switches.parameters_load(root))
    _log_open(root)
    prepared = repr(main_loop.loop_prepare(root))
    main_loop.loop_run(read_fd, write_fd, root)
    return prepared


# The work of a child that runs the loop on a root it never prepared.
def _loop_unprepared(root: str, read_fd: int, write_fd: int) -> str:
    main_loop.loop_run(read_fd, write_fd, root)
    return _ENDING_RETURNED


# Builds a push of a stream in the name form of the parameter `debug`.
def _push_make(text: str, blobs: list[jslb.Object]) -> jslb.Object:
    header = jslb.header_make(_PUSH_TYPE, full=switches.debug)
    return jslb.line_make(header, blobs, text=text)


# The pushes of a stream, each logged as the loop reaches it.
def _pushes_make() -> Iterator[jslb.Object]:
    for text in _PUSH_TEXTS:
        main_loop.verbose.log(text)
        yield _push_make(text, [jslb.blob_make(text.encode("utf-8"))])


# The pushes of a stream that fails: one, then a raise in place of the next.
def _pushes_fail() -> Iterator[jslb.Object]:
    yield _push_make(_PUSH_TEXTS[0], [])
    raise ValueError(_text_get("stream_fault"))


# The handler of `_STREAM_TYPE`: its pushes, then a reply of the line's text.
def _stream_handle(line: jslb.Object, *, text: str) -> dispatch.Stream:
    reply = dispatch.reply_make(line, text=text)
    return dispatch.Stream(_pushes_make(), reply)


# The handler of `_FAULT_TYPE`, whose reply the loop never reaches.
def _fault_handle(line: jslb.Object) -> dispatch.Stream:
    return dispatch.Stream(_pushes_fail(), dispatch.reply_make(line))


# The work of a child that serves the pipes with both handlers registered.
def _stream_serve(root: str, read_fd: int, write_fd: int) -> str:
    dispatch.handler_register(_STREAM_TYPE, 0, _stream_handle)
    dispatch.handler_register(_FAULT_TYPE, 0, _fault_handle)
    return _loop_serve(root, read_fd, write_fd)


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

    # Insert and update refuse a second row naming a world, a rename passes.
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
            with connection:
                connection.execute(
                    "UPDATE universe SET name = 'd', world = 'w'"
                    " WHERE name = 'a'"
                )
        universes = _rows_read(self.root, "metaverse", _UNIVERSE_QUERY)
        expected = [("c", "C", "player", "x"), ("d", "A", "player", "w")]
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

    # A seed document that is no JSON object is refused, naming its file.
    def test_seed_invalid(self) -> None:
        self.settings_write()
        directory = os.path.join(self.root, "python")
        seed = os.path.join(directory, "seed")
        shutil.copytree(_SEED_PATH, seed)
        path = os.path.join(seed, "hyperposition.json")
        with open(path, "w", encoding="utf-8") as file:
            file.write("[]")
        # The module reads the seed beside its file, so this link gives it one.
        link = os.path.join(directory, "main_loop.py")
        os.symlink(_MODULE_PATH, link)
        work = functools.partial(_prepare_linked, self.root, link)
        ending, output = self.child_run(work, b"")
        self.assertEqual(output, b"")
        last = ending.rstrip("\n").rsplit("\n", 1)[-1]
        message = _text_get("main_loop_seed_invalid").format(path)
        self.assertEqual(last, f"ValueError: {message}")


# The analyst's table in the seed, whose texts only the demo's golds pin.
class TestAnalyst(unittest.TestCase):
    # Reads the table of the seed and the gold's account of it.
    def setUp(self) -> None:
        self.script: dict[str, Any] = json.loads(
            _seed_read("provider_script.json")
        )
        self.gold: dict[str, Any] = _gold_copy("analyst")

    # Every `next` names a node of the table.
    def test_next_known(self) -> None:
        for reply in _replies_all(self.script):
            self.assertIn(reply["next"], self.script["nodes"])

    # Every tool call names a browser tool of the tool list, with its prefix.
    def test_tools_listed(self) -> None:
        tools = _tools_browser()
        for call in _calls_all(self.script):
            self.assertIn(call["name"], tools)

    # Every tool call's arguments are the text of a JSON object.
    def test_arguments_object(self) -> None:
        for call in _calls_all(self.script):
            self.assertIsInstance(call["arguments"], dict, call["name"])

    # A reply that calls tools has no text, and any other reply has text.
    def test_content_text(self) -> None:
        for reply in _replies_all(self.script):
            if "tool_calls" in reply:
                self.assertIsNone(reply["content"])
            else:
                self.assertIsInstance(reply["content"], str)

    # The table starts in its start node, and only input nodes hold inputs.
    def test_inputs_held(self) -> None:
        self.assertEqual(self.script["start"], self.gold["start_node"])
        inputs = sorted(self.gold["inputs"])
        for name, node in self.script["nodes"].items():
            held = inputs if name in self.gold["input_nodes"] else []
            self.assertEqual(sorted(node["replies"]), held, name)

    # Each input of each input node makes the gold's calls and ends in `menu`.
    def test_inputs_lead(self) -> None:
        for name in self.gold["input_nodes"]:
            for text, rounds in self.gold["inputs"].items():
                walked, last = _input_walk(self.script, name, text)
                trimmed = _rounds_trim(walked, rounds)
                self.assertEqual(trimmed, rounds, f"{name} {text}")
                end = self.gold["end_node"]
                self.assertEqual(last["next"], end, f"{name} {text}")


# `loop_run` over pipes: the pushes, the replies, failures and the end.
class TestLoop(ScratchCase):
    # Writes settings that stream small blobs and split reads, and the work.
    def setUp(self) -> None:
        super().setUp()
        self.values = self.settings_write(
            overflow_bytes=_OVERFLOW_BYTES, chunk_bytes=_CHUNK_BYTES
        )
        self.debug_write(True)
        self.work = functools.partial(_loop_serve, self.root)

    # Writes the root's parameters, the run's with `debug` and `verbose` set.
    def parameters_set(self, debug: bool, verbose: bool) -> None:
        parameters = {**switches.switches_get(), "debug": debug}
        switches.parameters_write(
            self.root, {**parameters, "verbose": verbose}
        )
        self.debug_mode = debug

    # Writes the root's parameters, the run's with `debug` set.
    def debug_write(self, debug: bool) -> None:
        self.parameters_set(debug, switches.verbose)

    # The gold line of an `error` that answers no line, in the debug form.
    def error_name(self) -> str:
        return "error_full" if self.debug_mode else "error"

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

    # Has the loop serve the two streams, under the `line_max` given.
    def stream_limit(self, line_max: int) -> None:
        self.settings_write(
            overflow_bytes=_OVERFLOW_BYTES,
            chunk_bytes=_CHUNK_BYTES,
            line_max=line_max,
        )
        self.work = functools.partial(_stream_serve, self.root)

    # Checks a sync's pushes: each database's restore, then its file lines.
    def restores_check(
        self, pushes: list[dict[str, Any]], type_name: str
    ) -> None:
        left = list(pushes)
        names: list[str] = _gold_copy("lines.sync_reply")["databases"]
        for name in names:
            restore = left.pop(0)
            self.assertEqual(restore["0"][type_name], "db.restore", name)
            self.assertEqual(restore["db"], name)
            for _ in range(restore["files"]):
                file = left.pop(0)
                self.assertEqual(file["0"][type_name], "db.file", name)
                self.assertEqual(file["db"], name)
        self.assertEqual(left, [])

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

    # A line's blob that is a cache file is copied to the output, whole.
    def test_file_copied(self) -> None:
        value = bytes(index % 256 for index in range(_STREAMED_BYTES))
        put = _line_bytes("put_streamed", value)
        lines = self.served_read(put + _line_bytes("sync"))
        self.assertIn(value, [line["1"]["d"] for line in lines if "1" in line])

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
        expected.append(_error_row(replies[0]))
        self.assertEqual(_log_read(self.root), expected)

    # A fault of the input with no line is logged the same way.
    def test_fault_logged(self) -> None:
        replies = self.failure_read(_BAD_LINE)
        message = _text_get("jslb_no_type")
        self.error_check(replies[0], self.error_name(), message)
        text = _text_get("main_loop_serve_failed_type")
        expected = [(_SERVER_THREAD, text), _error_row(replies[0])]
        self.assertEqual(_log_read(self.root), expected)

    # An `error` whose entry does not fit is traced as its header and sizes.
    def test_failure_sized(self) -> None:
        self.parameters_set(True, False)
        self.stream_limit(_LINE_SMALL)
        error = self.failure_read(_line_bytes("fault_request"))[-1]
        size = len(_json_bytes(_payload_of(error)))
        sized = _text_get("main_loop_line_error_sized")
        text = sized.replace("{0}", str(size))
        self.assertEqual(_log_read(self.root)[-1], (_SERVER_THREAD, text))

    # A `verbose.put` is traced by its sizes, as its entries go to the rows.
    def test_put_sized(self) -> None:
        self.parameters_set(True, False)
        self.assertEqual(self.served_read(_line_bytes("verbose_put")), [])
        expected = [
            (_SERVER_THREAD, _text_get("main_loop_line_dispatch_put_sized")),
            (_PAGE_THREAD, _text_get("verbose_put_entry")),
        ]
        self.assertEqual(_log_read(self.root), expected)

    # An `error` line that answers no line is in full names in debug mode.
    def test_fault_names(self) -> None:
        for debug, name in ((True, "error_full"), (False, "error")):
            with self.subTest(debug=debug):
                self.debug_write(debug)
                (error,) = self.failure_read(_BAD_LINE)
                self.header_check(error, name)

    # In debug mode the log traces each line and reply, at the shell's level 1.
    def test_trace_logged(self) -> None:
        self.parameters_set(True, False)
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
        self.parameters_set(False, True)
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

    # A `Stream` writes its pushes in order, then its reply, nothing traced.
    def test_stream_written(self) -> None:
        self.debug_write(False)
        self.stream_limit(self.values["line_max"])
        lines = self.served_read(_line_bytes("stream_request"))
        self.assertEqual(len(lines), 3)
        first, second, reply = lines
        self.assertEqual(first["1"].pop("d"), b"first")
        self.assertEqual(first, _gold_copy("lines.stream_push_first"))
        self.assertEqual(second["1"].pop("d"), b"second")
        self.assertEqual(second, _gold_copy("lines.stream_push_second"))
        self.assertEqual(reply, _gold_copy("lines.stream_reply"))
        expected = [(_SERVER_THREAD, text) for text in _PUSH_TEXTS]
        self.assertEqual(_log_read(self.root), expected)

    # In debug mode each line is traced in full as the loop reaches it.
    def test_stream_traced(self) -> None:
        self.parameters_set(True, False)
        self.stream_limit(self.values["line_max"])
        lines = self.served_read(_line_bytes("stream_request"))
        self.assertEqual(len(lines), 3)
        first, second = _PUSH_TEXTS
        texts = [
            _text_get("main_loop_line_dispatch_stream"),
            first,
            _text_get("main_loop_line_push_first"),
            second,
            _text_get("main_loop_line_push_second"),
            _text_get("main_loop_line_reply_stream"),
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # A fault between pushes answers the request with an `error`, no reply.
    def test_stream_fault(self) -> None:
        self.debug_write(False)
        self.stream_limit(self.values["line_max"])
        lines = self.failure_read(_line_bytes("fault_request"))
        self.assertEqual(len(lines), 2)
        push, error = lines
        self.assertEqual(push, _gold_copy("lines.fault_push"))
        self.error_check(error, "error_reply", _text_get("stream_fault"))
        text = _text_get("main_loop_serve_failed_stream")
        self.assertEqual(_log_read(self.root), [(_SERVER_THREAD, text)])

    # Each line past the limit is traced as its header and sizes.
    def test_trace_sized(self) -> None:
        self.parameters_set(True, False)
        self.stream_limit(_LINE_SMALL)
        lines = self.served_read(_line_bytes("stream_blob", b"bytes"))
        self.assertEqual(len(lines), 3)
        first, second = _PUSH_TEXTS
        texts = [
            _text_get("main_loop_line_dispatch_sized"),
            first,
            _text_get("main_loop_line_push_first_sized"),
            second,
            _text_get("main_loop_line_push_second_sized"),
            _text_get("main_loop_line_reply_sized"),
        ]
        expected = [(_SERVER_THREAD, text) for text in texts]
        self.assertEqual(_log_read(self.root), expected)

    # An entry whose `verbose.put` stays below `line_max` is rendered.
    def test_entry_fits(self) -> None:
        text = _text_get("main_loop_line_dispatch_stream")
        self.stream_limit(_put_bytes(text) + 1)
        self.served_read(_line_bytes("stream_request"))
        self.assertEqual(_log_read(self.root)[0], (_SERVER_THREAD, text))

    # An entry whose `verbose.put` reaches `line_max` is logged by its sizes.
    def test_entry_over(self) -> None:
        text = _text_get("main_loop_line_dispatch_stream")
        self.stream_limit(_put_bytes(text))
        self.served_read(_line_bytes("stream_request"))
        sized = _text_get("main_loop_line_dispatch_stream_sized")
        self.assertEqual(_log_read(self.root)[0], (_SERVER_THREAD, sized))

    # `db.sync` restores each database in name order, then names them.
    def test_sync_served(self) -> None:
        for debug, type_name in ((True, "type"), (False, "t")):
            with self.subTest(debug=debug):
                self.debug_write(debug)
                lines = self.served_read(_line_bytes("sync"))
                self.assertEqual(lines[-1], _gold_copy("lines.sync_reply"))
                self.restores_check(lines[:-1], type_name)
