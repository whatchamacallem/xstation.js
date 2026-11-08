# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The server's main loop, which `bootstrap.py` loads and a main loop file can
# replace in debug mode. `loop_prepare` runs before the first line,
# `tap.start`, and `loop_run` after it. Any reply is refused, since the server
# awaits none.
#
# An `error` line of the browser goes to `engine_tap.error_take`, after which
# the loop exits 1 and writes nothing: its exit ends the connection, the close
# the page waits for, since the page never closes on a failure. A
# `dispatch.Failure` writes its reply, then fails with its error, whose `error`
# line has no `r`, as its request is answered. A `dispatch.Stream` writes its
# pushes in order, then its reply. A failure writes one `error` line with its
# cascade, in the name form of the line it answers, else of the parameter
# `debug`, and exits 1, its message logged first outside debug mode. In debug
# mode the audit records each line read before it is dispatched, and each
# push, reply and `error` before it is written, the audit's own lines never.

import audit, dispatch, engine_audit, engine_db, engine_doc, engine_kv
import engine_mcp, engine_sql, engine_system, engine_tap, engine_turn
import functools, jslb, json, mcp, os, re, select, settings, substrate
import switches, uuid, verbose
from internationalization import i18n
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

# The seed file of the hyperposition's image.
_IMAGE_NAME = "hyperposition.bmp"

# The key in the metaverse of the hyperposition's image, which the scene names.
_IMAGE_KEY = "image/hyperposition"

# The seed file of the bootstrap script.
_SCRIPT_NAME = "bootstrap.js"

# The key of the bootstrap script in `_files`.
_SCRIPT_KEY = "script/bootstrap.js"

# The seed file of the scripted provider's script.
_PROVIDER_SCRIPT_NAME = "provider_script.json"

# The key of the scripted provider's script in `_files`.
_PROVIDER_SCRIPT_KEY = "provider/script.json"

# The key in the metaverse of the player in use.
_PLAYER_KEY = "player"

# The player a new metaverse starts with.
_PLAYER_NAME = "player"

# The key in the metaverse of the database that holds the current world.
_WORLD_KEY = "world"

# The key in the current world of the current scene's `Document-Ref`.
_SCENE_KEY = "scene"

# The `universe` table and its two triggers, as API/sql/metaverse.sql has them.
_METAVERSE_DDL = (
    """CREATE TABLE universe (
    name   TEXT PRIMARY KEY,
    title  TEXT NOT NULL,
    player TEXT NOT NULL,
    world  TEXT NOT NULL
) WITHOUT ROWID, STRICT""",
    """CREATE TRIGGER universe_world_insert BEFORE INSERT ON universe
WHEN EXISTS (
    SELECT 1 FROM universe WHERE world = NEW.world AND name <> NEW.name
)
BEGIN
    SELECT RAISE(ABORT, 'agent.content_ambiguous');
END""",
    """CREATE TRIGGER universe_world_update BEFORE UPDATE OF world ON universe
WHEN EXISTS (
    SELECT 1 FROM universe WHERE world = NEW.world AND name <> OLD.name
)
BEGIN
    SELECT RAISE(ABORT, 'agent.content_ambiguous');
END""",
)

# The query that finds the `universe` table, a row when the seed has run.
_UNIVERSE_FIND = (
    "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'universe'"
)

# The line type of the browser's failure.
_ERROR_TYPE = "error"

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


# The seed of a new metaverse: two documents, the bootstrap script, the image.
class _SeedFiles(NamedTuple):
    hyperposition: dict[int | str, Any]
    prompt: dict[int | str, Any]
    script: bytes
    image: bytes


# Where the loop writes, its chunk, and whether the audit records its lines.
class _LoopOutput(NamedTuple):
    write_fd: int
    chunk: int
    debug: bool


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
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# Reads a seed document by the decoders, its digit keys integer header keys.
def _document_read(name: str) -> dict[int | str, Any]:
    path = os.path.join(_SEED_DIRECTORY, name)
    with open(path, encoding="utf-8") as file:
        data: object = jslb.json_decode(file.read())
    if not isinstance(data, dict):
        raise ValueError(i18n("main_loop.seed_invalid", path))
    return cast(dict[int | str, Any], data)


# Reads the seed of a new metaverse, raising when a file of it is absent.
def _seed_read() -> _SeedFiles:
    with open(os.path.join(_SEED_DIRECTORY, _SCRIPT_NAME), "rb") as file:
        script = file.read()
    with open(os.path.join(_SEED_DIRECTORY, _IMAGE_NAME), "rb") as file:
        image = file.read()
    return _SeedFiles(
        _document_read(_HYPERPOSITION_ID + _SEED_EXTENSION),
        _document_read(_PROMPT_ID + _SEED_EXTENSION),
        script,
        image,
    )


# Writes one `_settings` row per setting, its value as JSON text.
def _settings_write(store: substrate.Store, values: dict[str, Any]) -> None:
    for key, value in values.items():
        store.kv_put(key, _json_text(value).encode("utf-8"), _SETTINGS_DB)


# Creates `universe` and triggers, writes the image, two documents, three rows.
def _metaverse_write(store: substrate.Store, seed: _SeedFiles) -> None:
    statements = [substrate.SqlStatement(sql, []) for sql in _METAVERSE_DDL]
    store.sql_run(_METAVERSE_DB, statements)
    store.kv_put(_IMAGE_KEY, seed.image, _METAVERSE_DB)
    scene = store.doc_put(_METAVERSE_DB, _HYPERPOSITION_ID, seed.hyperposition)
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


# Seeds the scripted provider's script in `_files` when its row is missing.
def _provider_seed(store: substrate.Store) -> None:
    rows = store.kv_list(_FILES_DB, _PROVIDER_SCRIPT_KEY)
    if any(row.key == _PROVIDER_SCRIPT_KEY for row in rows):
        return
    path = os.path.join(_SEED_DIRECTORY, _PROVIDER_SCRIPT_NAME)
    with open(path, "rb") as file:
        store.kv_put(_PROVIDER_SCRIPT_KEY, file.read(), _FILES_DB)


# Loads the settings and opens every database, seeding what is new.
def _prepare_run(root: str) -> _PreparedRoot:
    values = settings.settings_load(os.path.join(root, _SETTINGS_NAME))
    store = substrate.Store(root, values["overflow_bytes"], values["blob_max"])
    for name in _DATABASES:
        if os.path.exists(_database_path(root, name)):
            store.db_open(name)
        else:
            store.db_create(name)
    for name in _databases_found(root):
        store.db_open(name)
    _settings_write(store, values)
    _provider_seed(store)
    find = [substrate.SqlStatement(_UNIVERSE_FIND, [])]
    (found,) = store.sql_run(_METAVERSE_DB, find)
    if not found.rows:
        _metaverse_seed(store, _seed_read())
    return _PreparedRoot(values, store)


# Prepares the root once, before the first line.
def loop_prepare(root: str) -> None:
    _STATE.prepared = _prepare_run(root)


# Registers every stock handler, and the server's MCP server with its tools.
def _handlers_register(
    store: substrate.Store, root: str, debug: bool, line_max: int
) -> None:
    engine_kv.handlers_register(store)
    engine_doc.handlers_register(store)
    engine_db.handlers_register(store)
    engine_turn.handlers_register(store)
    engine_sql.handlers_register(store)
    engine_audit.handlers_register(debug, line_max, store)
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
def _line_write(line: jslb.Object, output: _LoopOutput) -> None:
    for piece in jslb.line_encode(line):
        if isinstance(piece, bytes):
            _bytes_write(piece, output.write_fd)
        else:
            _file_copy(piece, output.write_fd, output.chunk)


# Writes a push, a reply or an `error` line, recorded first in debug mode.
def _answer_write(answer: jslb.Object, output: _LoopOutput) -> None:
    if output.debug:
        audit.line_sent(answer)
    _line_write(answer, output)


# Writes the `error` line of a failure and exits 1, logged outside debug mode.
def _failure_exit(
    line: jslb.Object | None, error: BaseException, output: _LoopOutput
) -> NoReturn:
    if not output.debug:
        verbose.log(i18n("main_loop.serve_failed", str(error)))
    _answer_write(dispatch.error_make(line, error, output.debug), output)
    raise SystemExit(_EXIT_FAILED) from error


# Refuses a reply, dispatches the rest, and records each line in debug mode.
def _line_serve(line: jslb.Object, output: _LoopOutput) -> None:
    if output.debug:
        audit.line_received(line)
    # The server awaits no reply, as the one to `tap.start` was bootstrap's.
    if jslb.field_get(line[0], "reply") is not None:
        raise LookupError(
            i18n("main_loop.reply_unknown", jslb.line_render(line))
        )
    if jslb.field_get(line[0], "type") == _ERROR_TYPE:
        # The browser's failure: its stream bailed out, no answer.
        payload = jslb.payload_of(line)
        cause = payload["cause"] if "cause" in payload else None
        engine_tap.error_take(payload["message"], payload["stack"], cause)
        raise SystemExit(_EXIT_FAILED)
    result = dispatch.line_dispatch(line)
    if isinstance(result, dispatch.Failure):
        _answer_write(result.reply, output)
        # The request is answered, so the failure is the server's own.
        _failure_exit(None, result.error, output)
    if isinstance(result, dispatch.Stream):
        for push in result.pushes:
            _answer_write(push, output)
        _answer_write(result.reply, output)
    elif result is not None:
        _answer_write(result, output)


# Serves the lines one read finished, then feeds no bytes to raise a fault.
def _bytes_serve(
    decoder: jslb.LineDecoder, data: bytes, output: _LoopOutput
) -> None:
    line: jslb.Object | None = None
    try:
        if not data and not decoder.idle():
            raise jslb.WireError(i18n("main_loop.input_partial"))
        for piece in (data, b""):
            for line in decoder.bytes_feed(piece):
                _line_serve(line, output)
            line = None
    except Exception as error:
        _failure_exit(line, error, output)


# The select loop: reads the pty, decodes, dispatches, writes each answer.
def loop_run(read_fd: int, write_fd: int, root: str) -> None:
    prepared = _STATE.prepared
    if prepared is None:
        raise RuntimeError(i18n("main_loop.not_prepared"))
    values = prepared.values
    output = _LoopOutput(write_fd, values["chunk_bytes"], switches.debug)
    _handlers_register(prepared.store, root, output.debug, values["line_max"])
    decoder = jslb.LineDecoder(
        values["line_max"],
        values["blob_max"],
        values["overflow_bytes"],
        functools.partial(_sink_make, os.path.join(root, _CACHE_DIRECTORY)),
    )
    while True:
        select.select([read_fd], [], [])
        data = os.read(read_fd, output.chunk)
        _bytes_serve(decoder, data, output)
        if not data:
            return
