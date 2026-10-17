# HYPE: the hyperposition-engine plan

This fleshes out hyperposition-plan.md into a plan that can be built in
order. Each section states what is settled, what is proposed, and where a
decision is needed. Open decisions are numbered in HYPE-QUESTIONS.md and
referenced here as Q1, Q2 and so on. Nothing here is implemented yet.

The order of work is fixed by section 7: design a module, write its tests,
fix it, then stack the next module on it with calls going one way, down.

## 1 Method

1.1 The build order is the dependency order. A module is designed in this
document, then its test module is written, then the module, then its bugs
are fixed, and only then does the next module start. No module calls up or
sideways into a module that calls it.

1.2 Every stage leaves something that can be surveyed by a person: a TAP
transcript, a screenshot of a page, or a status line. A stage is not done
until its survey artifact exists and matches what section 7 says it shows.

1.3 Barebones means: the fewest moving parts that prove the foundation.
No feature is added to a stage because a later stage will need it.

1.4 The project rules apply throughout: no fallbacks, first failure only,
no fake data, no decoration, two English names per identifier, 79 columns,
Python standard library only at run time, and SH only in admin scripts.

## 2 Architecture

### 2.1 Processes and connections

```text
browser tab
  main thread   page.js: DOM, input, images, subtitles, console view
  worker "db"   wire.js to the server; settings, preferences, files
  worker "ai"   world and scene databases; tool table; model loop
        |
        | JSLB over ttyd's WebSocket ('0' frames), pty in raw mode
        v
ttyd, one per machine, spawns one program per WebSocket
  python3 bootstrap.py <modules> engine [--debug]   JSLB server
  python3 bootstrap.py <modules> console            execs dash
  python3 bootstrap.py <modules> version            one line, exit 0
        |
        v
SQLite files under ~/.cache/xsjs/: files, catalog, worlds, scenes
```

- One Python process per connection. No threads, no asyncio: a select
  loop on the pty, synchronous handlers, SQLite in WAL for sharing.
- The page opens one engine connection. The console, when debug mode is
  on, is a second connection to the same ttyd (Q6).
- ttyd's `--url-arg` carries the role: `/ws?arg=console`. bootstrap.py
  accepts only `engine`, `console` and `version`; anything else exits 2.
- The front end is JS, the back end is PY. That division is permanent.
- Multiplayer is one tty per player later; nothing here forecloses it.

### 2.2 One currency: the JSLB object

- Every message, task and reply, on every thread and on the wire, is one
  JSLB object (section 3). Threads pass it by structured clone with the
  blob buffers transferred; the wire passes it as bytes.
- A port is anything with `line_post(line)` and `line_receive(fn)`. Three
  ports exist: local (same thread, direct call), thread (MessagePort) and
  wire (ttyd WebSocket). Code that submits a task never knows which.
- A handler is a function looked up by the line's type. The same registry
  shape exists in PY and JS, so a handler can move between threads and
  machines without changing its callers.

### 2.3 Ownership

- Each database has exactly one owner thread. Access happens only inside
  a task running on that thread. The owner table is static (section 5.2,
  Q19).
- The main thread owns no database. SQLite's persistent VFS for browsers
  (OPFS) exists only in workers, and the 200 Hz goal forbids synchronous
  I/O on the main thread (Q3, Q30).
- Worker "db" owns the wire to the server and the three KV databases:
  settings, preferences and files. Media and scripts arrive over the wire
  and land in files without crossing another thread.
- Worker "ai" owns the world database and the scene databases, runs the
  tool table and the model loop, and asks worker "db" for media by key.

### 2.4 Debug mode

- Debug mode is an argument of the ttyd command, set by the start script,
  never a setting: `bootstrap.py <modules> engine --debug` (Q16).
- The hello line carries `debug`. With it on: the console role is served,
  settings accept writes, files may be put into the modules directory,
  and `system.restart` is accepted. With it off those lines are errors.
- Headers use full names in debug mode, short names otherwise (3.4).

### 2.5 The page and its scripts

- ttyd serves exactly one static file. `GET /other.js` is 404 today and
  stays so. Everything the page needs is inside that file or arrives
  over JSLB as blobs (Q4).
- First draft: `page_build.py` inlines the scripts, the workers' scripts
  and sqlite3.wasm (base64) into `build/hyperposition-engine.html`, in
  dependency order. Start copies it beside bootstrap.py as the index.
- Later: the loader fetches scripts from the server's files database by
  key and runs them from blob URLs, which is what makes the JS editable
  over MCP and backed up to both files databases.
- Scripts are classic scripts, one frozen namespace object each, loaded
  with `importScripts` in workers and script elements on the main
  thread. No bundler, no ES modules, no import maps.

### 2.6 What stays

- The canonical-mode bootstrapper behaviours are kept where they still
  serve: `restart` keeps its pid by exec of `sys.orig_argv`; modules fork
  with `setsid` and run through `runpy`; `put` and `ls` become handlers
  (Q10).
- `test_wire.py` keeps its rungs, including the last-line regression for
  a program that exits right after printing. The `version` role is that
  program under JSLB. A lone loss there is reported with ttyd's version.
- No sleeps in bootstrap.py. No reload of the page as a retry.
- The Windows scripts change in one function: the ttyd options gain `-a`
  and the index file name.

## 3 JSLB wire format

### 3.1 Framing

```text
message := line blob*
line    := json-object CR
```

- `json-object` is one JSON object in UTF-8 with no whitespace outside
  strings. JSON allows CR as whitespace, so the encoder emits none, and
  JSON forbids a raw CR inside a string, so the first CR ends the line.
- CR alone, byte 0x0D, ends the line. LF is an ordinary byte (Q8).
- The blobs follow the CR at once, in header order, each exactly `size`
  bytes, with no separator before, between or after them.
- A reader therefore needs two states: collecting bytes to a CR, then
  collecting known byte counts. It never scans blob contents.

### 3.2 Line header, key `"0"`

- `t` `type`: string, required. The handler name: lowercase words joined
  by `_`, namespaces by `.`, as `kv.put`, `scene.enter`, `error`.
- `v` `version`: integer, default 0. The version of that type's payload.
- `i` `id`: integer from 1, optional. Present when a reply is expected.
  Each sender numbers its own lines per port.
- `r` `reply`: integer, optional. The peer's `id` this line answers (Q9).
- `k` `key`: string, optional. The KV key the line is about.
- `b` `blobs`: integer, default 0. The number of blob headers.

### 3.3 Blob headers, keys `"1"` to `"b"`

- `s` `size`: integer, required. Bytes of the blob.
- `t` `type`: string, default `utf-8`. A content type from the registry:
  `utf-8`, `json`, `png`, `jpeg`, `webp`, `sqlite`, `js`, `wasm`, `html`,
  `css` (Q9).
- `v` `version`: integer, default 0.
- `k` `key`: string, default `""`. Where the blob is stored on arrival.
- `d` `data`: never serialized. In memory, the owned byte array.

### 3.4 Names

- A line uses either short names or full names in all its headers. Both
  forms in one line is a hard error. Full names are the debug mode form.
- The payload lives in the keys of the line that are not decimal integer
  strings. Decimal integer keys are reserved for headers.
- The decoder returns headers as sent, plus `d` or `data` on each blob.
  Omitted fields stay omitted; `field_get(header, "type")` resolves a
  short or full name and the default. Nothing is added or renamed.

### 3.5 Values

- Numbers are IEEE doubles. Integers must lie within plus or minus 2^53.
  The Python encoder refuses larger ints, NaN and infinities. Sizes and
  ids are non-negative integers.
- Strings are Unicode; the line is UTF-8 with the strict decoder on both
  sides. An invalid byte sequence is a hard error.
- Duplicate keys take the last value in both languages, as `JSON.parse`
  and `json.loads` do. Encoders never produce them.

### 3.6 Hard errors

- No `"0"`, no `t`, or `b` not matching the headers present: error.
- A gap in `"1"` to `"b"`, a non-integer or negative `s`, a payload key
  that is a decimal integer string, an unknown header field: error.
- A line over `line_max` bytes, 1 MiB, or a blob over `blob_max`, 1 GiB:
  error before the bytes are buffered. Large things go in blobs; huge
  things go in the file cache.
- The decoder raises on the first error and the port that fed it closes.
  There is no resynchronization on a byte stream.

### 3.7 In-memory form and round trip

- In memory a line is the parsed JSON object with `d` attached to each
  blob header: a plain object in JS, a `jslb.Object` in Python, which is
  a dict with attribute access made by `json.loads(object_hook=...)` at
  every level, so `line.scene.x` and `handler(**line)` both work.
- `line_decode(line_encode(x))` equals `x` as values, with each blob byte
  for byte identical. `line_encode` never copies blob bytes: it yields the
  JSON bytes, then each `d` as is, for a writer to send in order.
- Byte identity of the JSON text across languages is not promised; tests
  compare parsed values and blob bytes.

### 3.8 Example

```text
{"0":{"t":"scene.put","i":7,"k":"/quest/forest03","b":2},
 "1":{"t":"png","k":"/quest/forest03/backpack.png","s":8732763},
 "2":{"t":"png","k":"/quest/forest03/companion.png","s":64021},
 "title":"Forest clearing","entities":3}<CR><8732763 bytes><64021 bytes>
```

The line above is shown wrapped; on the wire it is one line.

### 3.9 Encoder and decoder API, both languages

- `header_make(type, **fields)` builds a line header in the form the
  debug flag selects. `blob_make(data, type, key)` builds a blob header
  with `d` set and `s` measured.
- `line_encode(line)` returns the sequence of byte chunks to write.
- `LineDecoder.feed(bytes)` returns the complete lines the bytes finish,
  zero or more, allocating each blob's buffer once from its header.
- `field_get(header, name)` as in 3.4. `blobs_of(line)` lists the blob
  headers in order.
- Nothing in `jslb` does I/O, knows ttyd, or knows a database.

### 3.10 Transport

- ttyd frames: client to server `'0' + bytes`, server to client the same,
  with `'1'` title and `'2'` preferences first. The wire module strips and
  adds the `'0'`; JSLB never sees it. Frames split anywhere.
- The engine role puts its pty in raw mode with `tty.setraw` before it
  writes anything. Raw mode ends the 4095 byte line, the echo, CR to LF
  translation, LF to CR LF on output, `^C`, `^D`, `^S`, `^Q`, `^\` and
  `IUTF8`. The client sends nothing until the hello line arrives.
- The console role leaves the pty cooked. xterm.js drives it as today.
- ttyd's 5 s ping is answered by the browser's network stack, not by JS,
  so a busy worker does not drop the connection.

### 3.11 Limits and measurements

- `line_max` 1 MiB, `blob_max` 1 GiB, `chunk_bytes` 64 KiB per WebSocket
  message on upload. All are constants with two-word names in one place.
- Upload backpressure: the JS writer waits for `bufferedAmount` to fall
  under one chunk before the next. ttyd queues pty writes in memory; its
  resident size during a 128 MiB upload is a stage 2 measurement. A credit
  window is added only if that measurement demands it (Q23).

## 4 Communication patterns

### 4.1 Request and reply

- A line with `i` gets exactly one line with `r` equal to it, from the
  peer, on the same port. The reply's `t` is the request's `t`, or `error`.
- A line without `i` is a notification. Nothing answers it.
- Ids restart at 1 per port per process lifetime and never repeat within
  one. A reply with an unknown `r` is a hard error.

### 4.2 Push

- Either side may send a notification at any time between its tasks:
  the server pushes `log.line` to a client that sent `log.follow`, and
  `files.changed` when its files database gains a key.
- Push never carries a blob the receiver did not ask for; it carries the
  key, and the receiver asks with `files.get` when it wants the bytes.

### 4.3 Ordering

- One port is one FIFO in each direction. The server is single-threaded,
  so replies leave in request order. Across ports no order is promised.
- A task's handler runs to completion before the next line on that port
  is read. There is no interleaving to reason about.

### 4.4 Errors

- A handler that raises produces one `error` line with `r`, carrying
  `message` and `stack` as text, written before anything else.
- Proposed policy for the server: after writing the error line it exits 1.
  The connection ends, the page shows the stack, nothing retries. That is
  first failure only with a call stack; a connection is cheap (Q7).
- In the page: the first failure in any thread disables the controls and
  shows the detail, as bootstrap.html does now. No partial operation.

### 4.5 Connection lifecycle

- Engine: ttyd spawns the program, it sets raw mode, writes `hello` with
  `i` 1 and payload `bootstrap`, `sha256`, `pid`, `python`, `sqlite`,
  `modules`, `role`, `debug`, `settings` (Q27). The client replies to the
  hello and may then send. `version` writes the same line and exits 0.
- End: the client closes the WebSocket with 1000. ttyd sends SIGHUP; the
  server's handler exits at once. SQLite's journal makes a transaction in
  flight vanish whole. There is no `quit` line in the first draft.
- There is no `cancel`. Raw mode removed `^C`; a runaway is ended by
  closing the connection, which kills the process group (Q8).

### 4.6 Tasks across threads

- `task_submit(line)` returns a promise of the reply. The queue reads
  the owner table by the line's type prefix and posts to that owner's
  port, or runs the handler at once when the owner is this thread.
- Blob buffers are transferred, not copied. After `task_submit` the
  caller's `d` is detached; the draft's word "owned" means this.
- Each thread runs one task at a time, which is what "max 1 task per DB"
  means once every database has one owner thread. Task bodies are
  synchronous; a step that must await is a second task (Q20).
- Forwarding, a route list in a header that each hop pops, is not in the
  first draft. A task that needs two owners is two tasks from the caller.

### 4.7 Console channel

- The console is a second ttyd connection in text mode under xterm.js
  headless, which renders dash's output to a text grid the page shows.
  Input is sent by the page and not echoed into the view.
- The AI reaches the console only through a tool call that the page must
  confirm. Without debug mode the role is refused by the server.

### 4.8 Versioning

- `v` on the line header is per type. A handler is registered for one
  version; a line with another version is an error, not a translation.
- A breaking change to the framing itself is a new blob type registry
  entry and a new hello payload field, never a silent change.

## 5 SQL design

### 5.1 Engines

- Server: Python's `sqlite3` on the system library, 3.46 in WSL today.
  Floor 3.38 for `STRICT`, `WITHOUT ROWID` and the JSON functions (Q28).
- Browser: sqlite3.wasm from sqlite.org, pinned by version and SHA-256,
  with the OPFS pool VFS, which needs a worker and no cross-origin
  isolation headers that ttyd could not send.
- One connection per database per owner. Pragmas per connection:
  `foreign_keys=ON`; server adds `journal_mode=WAL`,
  `synchronous=NORMAL`, `busy_timeout=5000`. The browser VFS has no WAL
  and keeps the default rollback journal.

### 5.2 Databases and owners

```text
name          owner      shape    replicated
settings      db worker  kv       seeded from the server at start
preferences   db worker  kv       to the server
files         db worker  kv+blob  both ways, by content hash
world         ai worker  kv+log   to the server
scene/<id>    ai worker  ecs      to the server
server files  server     kv+blob  master for scripts and media
catalog       server     table    not replicated
```

- A database name is `[a-z][a-z0-9_/]*`; its file is `<name>.sqlite`
  under the owner's root. Scenes are one file each so that a scene is a
  conversation that can be attached, detached, compacted and replaced.
- The region is the set of scene databases attached to the world
  connection at once, at most eight, with `ATTACH` by scene id.

### 5.3 The KV table

```sql
CREATE TABLE meta (
    name  TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID, STRICT;

CREATE TABLE kv (
    key    TEXT    PRIMARY KEY,
    type   TEXT    NOT NULL,
    size   INTEGER NOT NULL,
    sha256 BLOB    NOT NULL,
    data   BLOB,
    seq    INTEGER NOT NULL UNIQUE
) WITHOUT ROWID, STRICT;

CREATE TABLE kv_gone (
    key TEXT    PRIMARY KEY,
    seq INTEGER NOT NULL UNIQUE
) WITHOUT ROWID, STRICT;
```

- `type` is the JSLB blob type of the value. settings and preferences
  hold `json`, where the text `null` is a value per RFC 8259.
- `sha256` is the content hash. The `ls` builtin already reports it; it
  names the overflow file, detects an unchanged write, and lets
  replication skip bytes the other side has.
- `seq` comes from `meta` row `seq`, incremented in the same transaction
  as the write. `kv_gone` records deletions for replication; a put of a
  gone key removes its tombstone.
- `data` is NULL when the value went to the file cache (5.4).
- `meta` also holds `schema`, the DDL version, and `name`.

### 5.4 Overflow to the file cache

- Values over `overflow_bytes` are written to `<root>/cache/<sha256 hex>`
  and `data` is NULL. Below it they stay in the row. The draft gives
  128 KiB in two places and 128 MiB in one; SQLite's own measurements put
  the crossover near 100 KiB, so 128 KiB is proposed (Q12).
- A read returns the bytes from the row or the file; a delete removes the
  file when no other key shares the hash. The browser's cache is an OPFS
  directory; the server's is a directory under its root.
- Write order is file first, then the row in a transaction. A crash
  between the two leaves an unreferenced file, which `kv_check` removes.

### 5.5 Keys

- Every key is a JSON Pointer, RFC 6901: `/quest/forest03/backpack.png`.
  The experience is one logical document; a pointer into it names a
  scene, an entity, a file. `world` holds `/scene`, the pointer to the
  player's current scene (Q14).
- The same pointer names the same thing on both sides, so replication is
  a key-by-key comparison with no mapping table.

### 5.6 Scene schema

```sql
CREATE TABLE entity (
    id   INTEGER PRIMARY KEY,
    name TEXT UNIQUE
) STRICT;

CREATE TABLE component (
    entity INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    kind   TEXT    NOT NULL,
    data   TEXT    NOT NULL CHECK (json_valid(data)),
    PRIMARY KEY (entity, kind)
) WITHOUT ROWID, STRICT;

CREATE TABLE media (
    entity INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    role   TEXT    NOT NULL,
    key    TEXT    NOT NULL,
    PRIMARY KEY (entity, role)
) WITHOUT ROWID, STRICT;

CREATE TABLE turn (
    seq     INTEGER PRIMARY KEY,
    role    TEXT    NOT NULL,
    content TEXT    NOT NULL CHECK (json_valid(content))
) STRICT;
```

- Entities are rows; components are JSON documents by kind, so the AI
  can invent kinds without DDL. Facts about the scene are components.
  Indexes on `json_extract` are added when a query is measured slow.
- `media.key` points into files. Files is another database, so there is
  no foreign key; `scene_check` verifies the keys exist.
- `turn` is the scene's conversation. Compaction replaces a prefix of
  turns with one summary turn in one transaction (Q17, Q18).

### 5.7 World and catalog

- `world` is a KV database plus `visited(scene TEXT PRIMARY KEY,
  at INTEGER NOT NULL)`. Its `/scene` value is the current pointer;
  the hyperposition is `/hyperposition`, the one scene no task may write.
- `catalog` on the server: `universe(name TEXT PRIMARY KEY, title TEXT
  NOT NULL, seed TEXT NOT NULL)`, where `seed` is the key of the sqlite
  blob in files that a new world copies. The multiverse is this table.
- Layout under the server root: `files.sqlite`, `catalog.sqlite`,
  `worlds/<player>/world.sqlite`, `worlds/<player>/scenes/<id>.sqlite`
  (Q15).

### 5.8 Transactions

- A task is a transaction. The owner opens `BEGIN IMMEDIATE` before the
  handler and commits after it; a raise rolls back and becomes the error
  line. No handler issues `BEGIN` or `COMMIT`.
- The AI's `sql.run` tool runs inside the same rule: one statement list,
  one transaction, parameters bound, never string-built.

### 5.9 Replication

- First draft: whole-database snapshots. `db_snapshot` uses
  `Connection.serialize` in Python and the wasm export in the browser;
  the bytes travel as one blob of type `sqlite` with the database name as
  key. The receiver writes a temp file and renames it. Both sides report
  the snapshot's SHA-256 and the test compares them.
- Second draft: row log. `sync.pull {since}` returns `kv` rows and
  `kv_gone` rows with `seq` above `since`; files blobs are sent only when
  the receiver lacks that `sha256`. Snapshots remain for first copy.
- The browser is the writer of its player's world and scenes while it is
  connected; the server is their backup. The server is the master of
  scripts and seeds. Conflicts are therefore absent by construction in
  the single-tab case; a second tab is a question (Q13).

## 6 Modules

### 6.1 Naming

- Functions and classes carry two English names: `line_encode`,
  `kv_put`, `task_submit`, `LineDecoder`, `TaskQueue`. Modules and test
  modules are the exception: `jslb`, `tap`, `i18n`, `test_jslb`.
- Test methods are `test_` and at least two names, as their names are
  their documentation: `test_roundtrip_empty_line`,
  `test_blob_split_inside_character`.
- Constants are `_UPPER_NAME` at the top of each Python file; JS has one
  frozen `constants` object per module.

### 6.2 Python modules, bottom up

Each entry gives the responsibility, what it imports from this project,
and its public names. Every module has `test_<module>.py` beside it
holding its `unittest.TestCase` classes, run through tappy (6.2.2).

6.2.1 `i18n.py`, no project imports.

- `_TEXTS`: the dictionary of strings, `{0}` placeholders as PowerShell.
- `text_format(name, *args)`: raises on a missing name or a placeholder
  count that differs from the argument count (Q29).

6.2.2 `python/tap/`, tappy's producer modules copied as they are.

- tappy 3.x, BSD licensed, from its sdist pinned by version and SHA-256:
  `__init__.py`, `tracker.py`, `runner.py`, `line.py`, `formatter.py`,
  `directive.py`, `rules.py`, `main.py`, `__main__.py` and its license.
  The consumer files `parser.py`, `loader.py` and `adapter.py` are left
  out: nothing parses TAP yet.
- `TAPTestRunner` is `unittest.TextTestRunner` writing TAP. Instance
  methods `set_stream(True)` and `set_header(False)`; class methods
  `set_outdir(path)`, `set_combined(True)` for one `testresults.tap`,
  and `set_format(text)` with `{method_name}` and `{short_description}`.
- Default output: one `<TestCase>.tap` per class, starting
  `# TAP results for <TestCase>`, one `ok` or `not ok` line per test
  method, and the plan `1..N` last, N being the methods run. The plan
  is not settable.
- `Tracker` is the core: `add_ok`, `add_not_ok`, `add_skip`, `set_plan`,
  `generate_tap_reports`. It is the API the JS clone mirrors.
- The copy keeps tappy's style: `python/*.py` in the whitelist does not
  descend into `python/tap/`, and pyright excludes it (Q5).

6.2.3 `jslb.py`, imports i18n.

- `Object`, `header_make`, `blob_make`, `field_get`, `blobs_of`,
  `line_encode`, `LineDecoder`, `WireError`. Section 3 is its spec.

6.2.4 `verbose.py`, imports i18n.

- `level_set(level)`; `command_run(args)`: level 0 runs the command with
  its output passing through; level 1 wraps the output in Markdown blocks
  in the log; level 2 passes verbose flags to the command and logs raw.
- `log_write(text)`, `log_tail(count)`: the ring of the last N level 1
  lines, so the front end can ask for them. Writes are unbuffered.

6.2.5 `substrate.py`, imports i18n.

- `Store`: `db_open(name, root)`, `db_close()`, `kv_get(key)`,
  `kv_put(key, type, data)`, `kv_delete(key)`, `kv_list(prefix)`,
  `kv_check()`, `sql_run(statements, params)`, `db_snapshot()`,
  `db_restore(data)`, `transaction_run(fn)`. Sections 5.3 to 5.8.
- `schema_apply(connection, kind)`: creates `kv`, `ecs` or `catalog`
  tables and records `schema` in `meta`.

6.2.6 `dispatch.py`, imports jslb, i18n.

- `handler_register(type, version, fn)`, `line_dispatch(line) -> line`,
  `reply_make(line, **payload)`, `error_make(line, error)`,
  `id_next()`. Calls `fn(line, **payload)` with payload the non-integer
  keys (Q1).

6.2.7 `engine_kv.py`, `engine_db.py`, `engine_log.py`,
`engine_system.py`; import dispatch, substrate, verbose.

- `kv.get`, `kv.put`, `kv.delete`, `kv.list`; `db.snapshot`,
  `db.restore`, `db.list`; `log.follow`, `log.tail`; `hello`,
  `system.restart`, `files.put` into the modules directory in debug mode.
  These are the former `put` and `ls` builtins and `restart`.

6.2.8 `main_loop.py`, imports jslb, dispatch, the engine modules.

- `loop_run(read_fd, write_fd, root, debug)`: select on the read fd,
  feed the decoder, dispatch each line inside a transaction, write the
  reply chunks, push pending log lines between tasks, exit on SIGHUP and
  SIGTERM. Nothing else.

6.2.9 `bootstrap.py`, imports main_loop.

- Argument whitelist: modules directory, role, `--debug`. Role `engine`:
  raw mode, hello, `loop_run`. Role `console`: scrub the environment,
  change directory, apply limits, exec dash (Q11). Role `version`: hello
  and exit 0. The restart exec and the fork of modules stay here.

6.2.10 `page_build.py`, imports nothing from the project.

- Writes `build/hyperposition-engine.html` from `html/loader.html` and
  the manifest order of `js/`, inlining sqlite3.wasm as base64. The
  output's SHA-256 is printed, so a start can show what it serves.

6.2.11 `test_all.py`, imports tap.

- Loads the `test_<module>.py` modules in the order of this section into
  one `unittest.TestSuite`, runs it with `TAPTestRunner` streaming and
  `failfast`, so the stream stops at the first failing test, and prints
  `fail pass` last from the result. Exits 1 on any failure. Within one
  class unittest runs methods in name order.

6.2.12 `test_browser.py`, imports the DevTools driver of
`xsjs_screenshot.py` split into `devtools.py`.

- Serves `build/test.html` through Linux ttyd as the screenshot tool
  does, opens it in headless Chrome, waits for `window.tap`, prints its
  TAP, saves the page as a PNG, exits with its fail count clamped to 1.

### 6.3 JavaScript modules, bottom up

Each is `js/<name>.js`, a classic script that defines one frozen object
named after the module, and has `js/test_<name>.js` holding its
`TestCase` classes, run through the tappy clone (6.3.2). Workers load
them with `importScripts`.

6.3.1 `i18n.js`: `text_format(name, ...args)`, throws as in Python.

6.3.2 `tap.js`: a clone of tappy's producers and the subset of unittest
they need.

- `Tracker` with `add_ok`, `add_not_ok`, `add_skip`, `set_plan` and
  `generate_tap_reports`, writing the same text as the Python original.
- `TAPTestRunner` with `set_stream`, `set_outdir`, `set_combined`,
  `set_format`, `set_header` and `run(suite)` with `failfast`.
- `TestCase` with `setUp`, `tearDown`, `test_` methods in definition
  order, each awaited when it returns a promise, and `assertEqual`,
  `assertTrue`, `assertRaises`, `skipTest`, `fail`. `TestSuite` and
  `TestLoader.loadTestsFromModule`.
- A page has no directory: the stream is a `pre`, and `set_outdir` keeps
  the `.tap` texts in a map the page lists by class name (Q5).
- `report_html(text)` colours every `not ok` line and its diagnostic
  lines red, whole line, and nothing else.

6.3.3 `jslb.js`: the same names as `jslb.py`; `LineDecoder.feed` takes a
`Uint8Array`; blob buffers are `ArrayBuffer`s made once at header time.

6.3.4 `dispatch.js`: the same names as `dispatch.py`; a handler is
`fn(line)` and destructures its payload.

6.3.5 `queue.js`: `TaskQueue` with `task_submit(line)`, `owner_table`,
`LocalPort`, `ThreadPort` over a `MessagePort` with transfer lists, and
`pending` replies by id. Section 4.6.

6.3.6 `wire.js`: `WirePort`: fetch `/token`, open `/ws` with `['tty']`,
send ttyd's first JSON message, skip title and preferences, strip and add
the `'0'`, feed `LineDecoder`, wait for `bufferedAmount` on upload.

6.3.7 `substrate.js`: `Store` with the API of `substrate.py` over
sqlite3.wasm and the OPFS pool VFS; overflow files in an OPFS directory.

6.3.8 `console.js`: a ttyd text connection, xterm.js headless as the
terminal state machine, `grid_read()` returning the visible lines, and
`line_send(text)`. Stdin is not shown; the grid is.

6.3.9 `tools.js`: the tool table the model may call: `tools_list()` and
`tool_call(name, input)`, each tool a name, a description and a JSON
schema in the shape MCP's `tools/list` returns, so a bridge to a real
MCP transport is a transport, not a rewrite (Q2).

6.3.10 `model.js`: the single door to the model: `turn_run(turns, tools)
-> Promise<turn>`. A scripted model, driven by a table of inputs to
outputs, serves the tests; the real one is selected by a setting.

6.3.11 `worker_db.js`: entry of worker "db": `WirePort`, three `Store`s,
handlers `settings.*`, `preferences.*`, `files.*`, `sync.*`.

6.3.12 `worker_ai.js`: entry of worker "ai": world and scene `Store`s,
handlers `world.*`, `scene.*`, `ai.say`; owns `tools` and `model`.

6.3.13 `page.js`: the main thread: builds the DOM once, routes input to
`ai.say`, shows the image and subtitle a `render` task carries, hosts the
console view in debug mode. No database, no decoding of blobs.

6.3.14 `html/loader.html`: the markup and the inline boot: creates the
workers from the inlined scripts, waits for the hello relayed by worker
"db", then starts `page`. `html/test.html` runs the suites and shows
`report_html`.

### 6.4 Admin scripts

- `xsjs_install.sh`, `xsjs_start.sh`, `xsjs_stop.sh`, `xsjs_status.sh`
  at the top level mirror the `.ps1` scripts: same arguments, same first
  status line, a log `<script>.sh.md` beside each. POSIX sh (Q26).
- `posix/test_posix_lifecycle.sh` mirrors `test_powershell.ps1` inside
  a container built from `posix/Dockerfile` on `ubuntu:24.04`, running
  install, start, `test_wire.py`, stop (Q24).
- Start on Linux records a pid file under `~/.cache/xsjs/` and starts
  ttyd with `setsid`; stop signals the pid it recorded. Start at boot on
  Linux is a question (Q25).

### 6.5 Third-party files

- `third_party/sqlite-wasm/`, `third_party/xterm-headless/` and
  `third_party/tappy/`, each with a `SOURCE.md` naming the version, URL
  and SHA-256, fetched by `third_party_fetch.py` with `urllib` and
  verified, never by a package manager (Q4). `python/tap/` is the copy
  of tappy's producer files from there.

### 6.6 Dependency graph

```text
PY  i18n  tap (unittest)
      |
    jslb   verbose   substrate
       \      |       /
        dispatch  ---+
            |
    engine_kv  engine_db  engine_log  engine_system
            |
        main_loop
            |
        bootstrap

JS  i18n  tap
      |
    jslb         substrate(sqlite3.wasm)    console(xterm headless)
      |              |                          |
    dispatch         |                          |
      |              |                          |
    queue ------ wire                           |
      |      \       |                          |
    tools  model     |                          |
      \     |        |                          |
    worker_ai   worker_db                    page
                     \                         /
                      loader.html (page_build.py)
```

No arrow points up. A test module imports only its module and `tap`.

## 7 Testing

### 7.1 The runner

- tappy's producer API in both languages, as the maintainer asked on
  2026-10-17. This replaces the bespoke function-list runner of the
  draft, and with it the rule that a falsy return fails a test: a test
  is a `test_` method and its assertions decide (Q5).
- One TAP line per test method, not per assertion. The plan is the
  number of methods run and is not settable.
- A failure writes `not ok N - description` and tappy's diagnostic lines
  with the traceback. `failfast` stops the run there: first failure only.
- The driver prints `fail pass` after the stream, from the result.
- The HTML report colours the whole failed line and its diagnostic
  lines. Nothing else on the page is styled.

### 7.2 Runners

- `python3 python/test_all.py`: all Python suites in dependency order in
  one stream, then `python3 python/test_wire.py` for the wire rungs.
  Standard library only; Linux ttyd from `../ttyd` as today.
- `python3 python/test_browser.py`: builds `test.html`, serves it, runs
  the JS suites in headless Chrome, prints their TAP and saves a PNG.
  sqlite3.wasm and OPFS exist only in a browser, so there is one JS
  runner and it is a browser (Q22).
- `python3 python/test_posix.py` keeps its role: encoding, comments,
  formatting, lint, for every whitelisted file including the new ones.

### 7.3 Cross-language vectors

- `python/vectors/*.jslb`: byte files written by `jslb.py` covering
  empty payloads, every header field, short and full names, zero to
  three blobs, blob bytes that contain CR, LF, 0x03, 0x04, 0x13 and
  invalid UTF-8, and each hard error of 3.6.
- Both decoders read every vector and compare to the JSON sidecar
  `*.json` holding the expected object and the blobs' SHA-256. Both
  encoders re-encode and both decoders read the result.
- Every vector is also fed one byte at a time and in two pieces split
  at every offset, with identical results.

### 7.4 Stages

Each stage names what is built, what its tests prove, what a person
surveys, and the exit criterion. A stage starts only after the previous
one's exit criterion holds.

7.4.1 Stage 0, the harness.

- Builds: `third_party_fetch.py` and the tappy copy in `python/tap/`,
  `i18n.py`, `test_all.py`, `i18n.js`, `tap.js`, `devtools.py` split
  out of the screenshot tool, `test_browser.py`, `html/test.html`,
  `page_build.py` for the test page only.
- Proves: a nested `TestCase` with one passing method, one failing by
  assertion, one raising and one skipped yields the text tappy writes,
  `1..4` and the counts; the JS clone yields the same text for the same
  class, compared line by line outside the tracebacks; `set_outdir` on
  the Python side writes `<TestCase>.tap` with the header; `failfast`
  stops after the first `not ok`; `text_format` raises on a missing name
  and on a count mismatch in both languages.
- Survey: the TAP text in the terminal; the PNG of `test.html`.
- Exit: both runners exit 0 on the real suites and 1 on the nested
  failing class they test with.

7.4.2 Stage 1, JSLB.

- Builds: `jslb.py`, `jslb.js`, the vectors of 7.3.
- Proves: section 3 line by line; every hard error raises; no copy of
  blob bytes on encode, measured by identity of the yielded buffers.
- Survey: the TAP text; the vector directory listing with sizes.
- Exit: both suites pass; both read all vectors of the other.

7.4.3 Stage 2, the raw wire.

- Builds: `bootstrap.py` roles, raw mode, hello, an `echo` handler that
  returns its line and blobs; `test_wire.py` rungs `hello`, `echo`,
  `echo blob 1 MiB with control bytes`, `echo 128 MiB`, `version`,
  `two engines`, `ttyd killed`.
- Proves: raw mode passes 0x03, 0x04, 0x0D, 0x13 and 4096 byte lines
  untouched both ways; the `version` line arrives whole; a lone loss is
  reported with ttyd's version; ttyd's resident size during the 128 MiB
  echo is printed.
- Survey: one line per rung with the measured bytes, seconds and ttyd
  memory.
- Exit: all rungs pass twice in a row.

7.4.4 Stage 3, the server substrate.

- Builds: `substrate.py` with the KV schema.
- Proves: put, get, delete, list, tombstones, `seq` monotonic across
  reopen, overflow at exactly `overflow_bytes`, same hash shares one
  cache file, snapshot and restore equal by SHA-256, a `SIGKILL` between
  file write and row leaves a consistent database and `kv_check` removes
  the orphan.
- Survey: the TAP text; the cache directory listing after the suite.
- Exit: suite passes under `python3 -X dev`.

7.4.5 Stage 4, dispatch and the main loop.

- Builds: `dispatch.py`, `engine_*.py`, `main_loop.py`, `verbose.py`.
- Proves, through `test_wire.py` as the client: `kv.put` of a blob and
  `kv.get` returning identical bytes, `kv.list`, `db.snapshot`,
  `log.follow` pushing a line written by a handler, an unknown type
  producing an `error` line with a stack and then the exit the policy
  of 4.4 prescribes, `system.restart` keeping the pid and reporting the
  new SHA-256 after `files.put` changed bootstrap.py in debug mode, and
  the same `files.put` refused without debug mode.
- Survey: the rung lines; `ttyd.log` showing the exit codes.
- Exit: all rungs pass; `pyright --project python` clean.

7.4.6 Stage 5, the page reaches the server.

- Builds: `dispatch.js`, `queue.js`, `wire.js`, `worker_db.js` without
  databases, `loader.html`, `page.js` showing only the hello.
- Proves: `test.html` in Chrome runs the JS suites for jslb, dispatch and
  queue; the loader's hello relay shows `pid`, `sha256` and `debug`; a
  `kv.put` of 16 MiB from the page and a `kv.get` compare equal by
  SHA-256 computed in the worker; a long task observer on the main
  thread reports no task over 5 ms during the transfer (Q30).
- Survey: a PNG of the page with the hello and the measured numbers.
- Exit: `test_browser.py` exits 0; the PNG shows no `failure` line.

7.4.7 Stage 6, the browser substrate.

- Builds: `substrate.js`, sqlite3.wasm inlined, the OPFS cache.
- Proves: the stage 3 suite, ported, passes in the worker; a second
  page load on the same origin finds the rows; overflow files appear in
  the OPFS directory listing the test prints.
- Survey: the PNG of `test.html` with the suite's lines.
- Exit: identical `fail pass` counts to the Python suite's.

7.4.8 Stage 7, two workers.

- Builds: `worker_ai.js` with world and one scene database on the ECS
  schema; owner table; `page.js` showing an image from files.
- Proves: a task from the main thread to "ai" that reads a scene row
  and asks "db" for a media key by a second task; buffers transferred,
  measured by `byteLength` 0 on the sender; one task at a time per
  worker shown by an interleaving test; the region attaches and
  detaches scene files.
- Survey: a PNG of the page showing the image and its key.
- Exit: `test_browser.py` exits 0 with the stage's suites.

7.4.9 Stage 8, replication.

- Builds: `sync.*` handlers both sides, snapshot first.
- Proves: a world written in the browser appears on the server with the
  same SHA-256; a seed from the catalog becomes a browser world; then
  the row log sends only rows above `since` and no blob whose hash the
  receiver has, counted on the wire.
- Survey: the rung lines with byte counts for full and incremental sync.
- Exit: both directions pass with the counts the test predicts from its
  own writes.

7.4.10 Stage 9, the console.

- Builds: role `console`, `console.js`, xterm.js headless, the debug
  view in `page.js`.
- Proves: `echo` round trip through the grid; `^C` ends `sleep 600`;
  the sandbox facts the role prints, uid, cwd and environment names,
  match what bootstrap.py set; without debug mode the role exits 2.
- Survey: a PNG with the console grid visible.
- Exit: the rung and the browser test pass.

7.4.11 Stage 10, the hyperposition.

- Builds: `tools.js`, `model.js` with the scripted model, `ai.say`, the
  render task, the hyperposition scene seeded with its prompt
  components, the black page with "How can I help you?".
- Proves: a typed sentence becomes a `turn` row, a scripted tool call
  that puts a PNG the test made into files, a render that shows it, and
  the subtitle text from the model; the hyperposition scene refuses
  writes; time does not advance without input, shown by the absence of
  timers in a trace.
- Survey: a PNG of the page after the exchange.
- Exit: the scripted run passes; the real model is behind a setting and
  outside the automated tests.

7.4.12 Stage 11, operations.

- Builds: the `.sh` scripts, the Dockerfile, the lifecycle test; the
  one-function change to the Windows scripts.
- Proves: install, start, `test_wire.py`, stop in the container exit 0;
  `test_powershell.ps1` still passes on Windows.
- Survey: the container's log; `xsjs_status.ps1` output.
- Exit: both lifecycle tests pass.

## 8 The experience layer

8.1 The algorithm of the draft maps to lines as follows.

- Player acts: `page` submits `ai.say {text}` or `ai.click {x, y}` to
  "ai". Time stops because nothing runs without such a task.
- "ai" appends a `turn`, calls `model.turn_run` with the tool table.
- Tools: `sql.run {db, statements, params}` on the region;
  `kv.get` and `kv.put`; `scene.enter {pointer}`; `image.make {prompt}`
  which stores the result in files and returns its key (Q21);
  `console.run {text}` in debug mode after the page confirms.
- "ai" submits `render {image_key, subtitle}` to the main thread, which
  asks "db" for the bytes and paints.
- The reply to `ai.say` carries the turn's end.

8.2 The hyperposition is `/hyperposition`: black, fog and lights as
media later, the subtitle "How can I help you?" first. Its prompt is a
component of kind `prompt` on the analyst entity; the analyst's remit,
to find the right universe and act on requests without judgement, is
data in that row, not code.

8.3 Scenes are conversations. Entering a scene starts a new `turn` log
with an establishing shot; compaction summarizes; the next scene's files
are fetched while the crossfade runs in the page.

## 9 Operations

9.1 Server root: `~/.cache/xsjs/` keeps bootstrap.py, the page, the
modules directory, and gains `files.sqlite`, `catalog.sqlite`, `worlds/`
and `cache/`. Start copies the Python package and the built page there.

9.2 Windows: `xsjs_util_get_ttyd_options` gains `-a` and names the built
page; the status script's command line match stays exact.

9.3 Linux and the container: the `.sh` scripts of 6.4. The container
runs as a user, not root, so that ttyd and the sandbox facts match WSL.

9.4 Certificate, boot and checkout decisions of the project direction
stand unchanged: LAN address as a SAN at the next generation, one reboot
test by the maintainer, `C:\src` for Windows users.
