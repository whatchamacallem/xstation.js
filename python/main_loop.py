# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The server's main loop, which `bootstrap.py` loads and a main loop file can
# replace in debug mode. `loop_prepare` runs before `hello`: it loads the
# settings into `_settings`, opens the log and every database under the root,
# creating the fixed ones that are missing, seeds the metaverse while its `seq`
# is 0, and returns the `seq` of each database. `loop_run` registers the stock
# handlers and runs the select loop on the engine tty: it decodes each line,
# refuses any reply, dispatches every other line and writes each reply. A
# failure writes one `error` line and exits 1.

import dispatch, engine_db, engine_doc, engine_kv, engine_mcp, engine_sql
import engine_system, engine_tap, engine_turn, engine_verbose, functools, jslb
import json, mcp, os, re, select, settings, substrate, uuid, verbose
from i18n import i18n
from typing import Any, NamedTuple, NoReturn, cast

# The settings file in the root.
_SETTINGS_NAME = "settings.json"

# The extension of a database file under the root.
_DB_EXTENSION = ".sqlite"

# The directory in the root that holds the blobs over `overflow_bytes`.
_CACHE_DIRECTORY = "cache"

# The database that holds the settings, one row per setting.
_SETTINGS_DB = "_settings"

# The database that holds the user's preferences.
_PREFERENCES_DB = "_preferences"

# The database that holds media, scripts and blobs by key.
_FILES_DB = "_files"

# The database that holds the `universe` table and the hyperposition.
_METAVERSE_DB = "metaverse"

# The fixed databases, opened first and created when their file is missing.
_DATABASES = (_SETTINGS_DB, _PREFERENCES_DB, _FILES_DB, _METAVERSE_DB)

# The log's own database, which `verbose` opens and the store never does.
_VERBOSE_DB = "_verbose"

# A database name, a C identifier.
_C_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# The directory beside this file that holds the seed of a new metaverse.
_SEED_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "seed"
)

# The extension of the file of a seed document.
_SEED_EXTENSION = ".json"

# The id of the hyperposition document, the scene a new metaverse starts in.
_HYPERPOSITION_ID = "hyperposition"

# The id of the analyst's prompt document.
_PROMPT_ID = "prompt"

# The seed file of the bootstrap script.
_SCRIPT_NAME = "bootstrap.js"

# The key of the bootstrap script in `_files`.
_SCRIPT_KEY = "script/bootstrap.js"

# The key in the metaverse of the player in use.
_PLAYER_KEY = "player"

# The player a new metaverse starts with.
_PLAYER_NAME = "player"

# The key in the metaverse of the database that holds the current world.
_WORLD_KEY = "world"

# The key in the current world of the current scene's `Document-Ref`.
_SCENE_KEY = "scene"

# The DDL of the metaverse's `universe` table, as the API's SQL file holds it.
_UNIVERSE_DDL = """CREATE TABLE universe (
    name   TEXT PRIMARY KEY,
    title  TEXT NOT NULL,
    player TEXT NOT NULL,
    world  TEXT NOT NULL
) WITHOUT ROWID, STRICT"""

# A top level key of a seed document that names a header: canonical digits.
_HEADER_KEY = re.compile(r"0|[1-9][0-9]*")

# The name the server's MCP server gives in its `serverInfo`.
_SERVER_NAME = "xsjs-server"

# The version the server's MCP server gives in its `serverInfo`.
_SERVER_VERSION = "0"

# The exit code of a failure.
_EXIT_FAILED = 1


# What `loop_prepare` opened for the root: its settings and its store.
class _PreparedRoot(NamedTuple):
    values: dict[str, Any]
    store: substrate.Store


# The seed of a new metaverse: its two documents and the bootstrap script.
class _SeedFiles(NamedTuple):
    hyperposition: dict[int | str, Any]
    prompt: dict[int | str, Any]
    script: bytes


# The state of the module, which is empty until `loop_prepare` runs.
class _LoopState:
    # Starts with nothing prepared.
    def __init__(self) -> None:
        self.prepared: _PreparedRoot | None = None


# The one state of the module.
_STATE = _LoopState()


# The file of a database under the root.
def _database_path(root: str, name: str) -> str:
    return os.path.join(root, name + _DB_EXTENSION)


# The other databases under the root, the scripts' ones, by name.
def _databases_found(root: str) -> list[str]:
    names: list[str] = []
    for file_name in sorted(os.listdir(root)):
        name, extension = os.path.splitext(file_name)
        if (
            extension == _DB_EXTENSION
            and _C_IDENTIFIER.fullmatch(name) is not None
            and name not in _DATABASES
            and name != _VERBOSE_DB
        ):
            names.append(name)
    return names


# The JSON text of a value as the wire and the substrate write it.
def _json_text(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


# Reads a seed document, its top level digit keys made integer header keys.
def _document_read(name: str) -> dict[int | str, Any]:
    path = os.path.join(_SEED_DIRECTORY, name)
    with open(path, encoding="utf-8") as file:
        data: object = json.load(file)
    fields = cast(dict[str, Any], data)
    if not isinstance(data, dict):
        raise ValueError(i18n("main_loop.seed_invalid", path))
    return {
        (int(key) if _HEADER_KEY.fullmatch(key) else key): value
        for key, value in fields.items()
    }


# Reads the seed of a new metaverse, raising when a file of it is absent.
def _seed_read() -> _SeedFiles:
    with open(os.path.join(_SEED_DIRECTORY, _SCRIPT_NAME), "rb") as file:
        script = file.read()
    return _SeedFiles(
        _document_read(_HYPERPOSITION_ID + _SEED_EXTENSION),
        _document_read(_PROMPT_ID + _SEED_EXTENSION),
        script,
    )


# Writes one `_settings` row per setting, its value as JSON text.
def _settings_write(store: substrate.Store, values: dict[str, Any]) -> None:
    for key, value in values.items():
        store.kv_put(key, _json_text(value).encode("utf-8"), _SETTINGS_DB)


# Creates the `universe` table and writes the two documents and three rows.
def _metaverse_write(store: substrate.Store, seed: _SeedFiles) -> None:
    store.sql_run(_METAVERSE_DB, [substrate.SqlStatement(_UNIVERSE_DDL, [])])
    scene, _ = store.doc_put(
        _METAVERSE_DB, _HYPERPOSITION_ID, seed.hyperposition
    )
    store.doc_put(_METAVERSE_DB, _PROMPT_ID, seed.prompt)
    rows = (
        (_PLAYER_KEY, _PLAYER_NAME),
        (_WORLD_KEY, _METAVERSE_DB),
        (_SCENE_KEY, scene),
    )
    for key, text in rows:
        store.kv_put(key, text.encode("utf-8"), _METAVERSE_DB)


# Writes the script row, a no op when unchanged, then the metaverse at once.
def _metaverse_seed(store: substrate.Store, seed: _SeedFiles) -> None:
    store.kv_put(_SCRIPT_KEY, seed.script, _FILES_DB)
    store.transaction_run(lambda: _metaverse_write(store, seed))


# Loads the settings, opens the log and every database, seeding what is new.
def _prepare_run(root: str) -> _PreparedRoot:
    values = settings.settings_load(os.path.join(root, _SETTINGS_NAME))
    verbose.log_open(root, values["verbose_ring"])
    verbose.level_set(values["verbose_level"])
    store = substrate.Store(root, values["overflow_bytes"])
    for name in _DATABASES:
        if os.path.exists(_database_path(root, name)):
            store.db_open(name)
        else:
            store.db_create(name)
    for name in _databases_found(root):
        store.db_open(name)
    _settings_write(store, values)
    if store.seq_get(_METAVERSE_DB) == 0:
        _metaverse_seed(store, _seed_read())
    return _PreparedRoot(values, store)


# Prepares the root once, before `hello`, and returns each database's `seq`.
def loop_prepare(root: str) -> dict[str, int]:
    prepared = _prepare_run(root)
    _STATE.prepared = prepared
    store = prepared.store
    return {name: store.seq_get(name) for name in store.db_list()}


# Registers every stock handler, and the server's MCP server with its tools.
def _handlers_register(store: substrate.Store, root: str, debug: bool) -> None:
    engine_kv.handlers_register(store)
    engine_doc.handlers_register(store)
    engine_db.handlers_register(store)
    engine_turn.handlers_register(store)
    engine_sql.handlers_register(store)
    engine_verbose.handlers_register(debug)
    engine_tap.handlers_register(root)
    engine_system.handlers_register(root, debug)
    server = mcp.Server(_SERVER_NAME, _SERVER_VERSION)
    engine_system.tools_register(server, root, debug)
    engine_mcp.handlers_register(server)


# Names a new file in the cache for a blob the decoder streams.
def _sink_make(cache: str, header: jslb.Object) -> str:
    return os.path.join(cache, uuid.uuid4().hex)


# Writes all the bytes to the descriptor, looping on partial writes.
def _bytes_write(data: bytes, write_fd: int) -> None:
    view = memoryview(data)
    while view:
        written = os.write(write_fd, view)
        view = view[written:]


# Copies a file to the descriptor a chunk at a time.
def _file_copy(path: str, write_fd: int, chunk: int) -> None:
    with open(path, "rb") as file:
        while data := file.read(chunk):
            _bytes_write(data, write_fd)


# Writes a line's pieces in order: bytes as they are, a file path copied.
def _line_write(line: jslb.Object, write_fd: int, chunk: int) -> None:
    for piece in jslb.line_encode(line):
        if isinstance(piece, bytes):
            _bytes_write(piece, write_fd)
        else:
            _file_copy(piece, write_fd, chunk)


# Writes the one `error` line of a failure and exits 1.
def _failure_exit(
    line: jslb.Object | None, error: Exception, write_fd: int, chunk: int
) -> NoReturn:
    _line_write(dispatch.error_make(line, error), write_fd, chunk)
    raise SystemExit(_EXIT_FAILED) from error


# Refuses a reply, as the server has no request open, and dispatches the rest.
def _line_serve(line: jslb.Object, write_fd: int, chunk: int) -> None:
    # A first server request must take its ids after the 1 that `hello` used.
    if jslb.field_get(line[0], "reply") is not None:
        raise LookupError(
            i18n("main_loop.reply_unknown", jslb.line_render(line))
        )
    reply = dispatch.line_dispatch(line)
    if reply is not None:
        _line_write(reply, write_fd, chunk)


# Serves the lines one read finished, then feeds no bytes to raise a fault.
def _bytes_serve(
    decoder: jslb.LineDecoder, data: bytes, write_fd: int, chunk: int
) -> None:
    line: jslb.Object | None = None
    try:
        if not data and not decoder.idle():
            raise jslb.WireError(i18n("main_loop.input_partial"))
        for piece in (data, b""):
            for line in decoder.bytes_feed(piece):
                _line_serve(line, write_fd, chunk)
            line = None
    except Exception as error:
        _failure_exit(line, error, write_fd, chunk)


# The select loop: reads the pty, decodes, dispatches, writes each reply.
def loop_run(read_fd: int, write_fd: int, root: str) -> None:
    prepared = _STATE.prepared
    if prepared is None:
        raise RuntimeError(i18n("main_loop.not_prepared"))
    values = prepared.values
    _handlers_register(prepared.store, root, values["debug"])
    decoder = jslb.LineDecoder(
        values["line_max"],
        values["blob_max"],
        values["message_max"],
        values["overflow_bytes"],
        functools.partial(_sink_make, os.path.join(root, _CACHE_DIRECTORY)),
    )
    chunk: int = values["chunk_bytes"]
    while True:
        select.select([read_fd], [], [])
        data = os.read(read_fd, chunk)
        _bytes_serve(decoder, data, write_fd, chunk)
        if not data:
            return
