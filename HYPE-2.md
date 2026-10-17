# HYPE-2: the hyperposition-engine plan, second pass

This replaces HYPE.md. It applies the thirty answers of 2026-10-17 in
HYPE-QUESTIONS.md and reassesses the whole design with them in mind. Where
this document and HYPE.md differ, this one stands. Open decisions are
numbered in HYPE-QUESTIONS-2.md and referenced here as Q1, Q2 and so on.
The external APIs are in API/ and the synthetic transcripts in DATA/.
Nothing is implemented.

## 1 Method

### 1.1 APIs before code

- The maintainer would rather have an incomplete code base with correct
  APIs than a demo that is rewritten later. Every protocol this engine
  speaks is emulated as the real protocol from the first line of code:
  MCP is JSON-RPC 2.0 with `initialize`, `tools/list` and `tools/call`;
  the AI provider is spoken to in the generic chat completion shape; TAP
  is the TAP that tappy's consumer accepts. No table "in the shape of" a
  protocol stands in for the protocol.
- The order of work is: design the module in this document and in API/,
  write its test module, write the module, fix it, then stack the next
  module on it with calls going one way, down. No module calls up or
  sideways into a module that calls it.
- Documents iterate until the APIs are right. Implementation churn is not
  a planning goal; a stage that would need an API rewritten later is not
  started.

### 1.2 Fail fast

- This is a fail fast code base. No error is swallowed, defaulted or
  retried. Every failure stops with a message that names what to fix and
  a call stack. Fixing bugs is worth more than stability for now.
- On the server, a failed handler writes one `error` line and exits 1.
  In the page, the first failure in any thread shows its detail,
  disables the controls, closes the connection and offers Reconnect. The
  server's state is reconciled from its next `hello` (4.4).

### 1.3 One synchronization tool

- The task queue is the only synchronization tool. A task body is
  synchronous; a step that must await is a second task. A database is
  touched only inside a task on its owner thread. There are no locks,
  no shared memory, no `Atomics`.

### 1.4 What the second pass changed

Fresh eyes on HYPE.md, with the answers applied, changed these things.

1.4.1 Three threads, not two workers plus a main thread doing DOM only:
UI downloads media and paints; AI owns every database and proxies them,
talks to the provider, hosts MCP; WASM runs sqlite3.wasm and the OPFS
cache. That is a design goal until a hard need for more arises.

1.4.2 One tty. The engine connection carries the console as JSLB blobs
from a dash that the server forks under a pty. No `--url-arg` role, no
second WebSocket, no console log-in. The console can be opened and closed
at any time by the user or, with permission, by the AI (Q27).

1.4.3 No browser `settings` or `preferences` databases. settings.json
is read by the server and injected unmodified into the page in `hello`.
Preferences are a document in the `metaverse` database.

1.4.4 Databases are per region: `metaverse`, one per universe, one per
region. Scenes are documents inside a region, not files.

1.4.5 JSON Pointers are gone. A Document-Ref is a global key,
`<db>/<kind>/<name>/<version>`, that names its database and version.
Documents are immutable once written; history is the set of versions.

1.4.6 The ECS schema is the AI's. The engine seeds only its own tables
(`meta`, `kv`, `kv_gone`, `doc`, `doc_head`, `turn`, `log`); the AI is
the database administrator and runs DDL.

1.4.7 The blob type registry is gone. A blob is opaque bytes to JSLB;
the line's handler reads its blob headers.

1.4.8 Big blobs stream to the cache file as they arrive. The decoder
never holds more than `overflow_bytes` of one blob in memory.

1.4.9 The forked modules, `put`, `ls` and the dash-like command loop of
bootstrap.py go. Python forks nothing but the console's dash. `restart`
stays as the one exec, of Python itself (Q32).

1.4.10 TypeScript. Every script in the page is compiled by tsc from
`ts/` into one bundle that page_build.py inlines. Node runs tsc at build
time only and nothing else, ever (Q1).

1.4.11 The provider is generic: the chat completion protocol that xAI,
OpenAI and Anthropic's compatibility endpoint all serve, plus the image
generation endpoint. A scripted provider answers integer inputs so the
whole engine is tested with no AI running.

1.4.12 unittest is the test API in both languages, through tappy, with
one TAP plan per language and one subtest block per module, checked by
tappy's consumer on the server.

1.4.13 Operations shrink to the first beachhead: the engine serving
from the maintainer's own WSL user account through the existing Windows
scripts. Docker, systemd, sandboxes and the `.sh` scripts are doors kept
open, not work.

## 2 Architecture

### 2.1 Processes, threads and connections

```text
browser tab
  UI    main thread  page.ts: DOM, input, media_db, console view, faults
  AI    worker       owner of every database; wire; MCP; agent; proxies
  WASM  worker       sqlite3.wasm on OPFS; the cache directory
            |
            |  JSLB over ttyd's WebSocket, pty in raw mode, one per tab
            v
ttyd, one per machine, one program per WebSocket
  python3 bootstrap.py --root ~/.cache/xsjs [--debug]
     |                                    \
     | SQLite files under the root         \ dash under a pty, debug only
     v
  metaverse.sqlite  files.sqlite  <universe>.sqlite  <universe>/<region>.sqlite
```

- One Python process per connection. No threads, no asyncio: a `select`
  loop on the pty and, when open, the console's pty.
- The AI worker owns the WebSocket. The UI thread never sees the wire.
  The WASM worker never sees anything but tasks from the AI worker.
- The front end is TypeScript, the back end is Python. SH appears only
  in admin scripts. Python launches no command line utility: the one
  child it forks is dash for the console, in debug mode, on request.

### 2.2 The three threads

- UI: builds the DOM once, routes the player's text and clicks to the AI
  worker, paints the image and subtitle a `render` task names, keeps
  `media_db`, a JavaScript map from media key to decoded image with a
  byte budget, downloads media from URLs the AI names, hosts the console
  view, and shows faults. It owns no SQLite and decodes no blob.
- AI: owns the wire, the task queue's owner table, and every database.
  It is the single intermediary: a task from the UI that touches data is
  a task on the AI worker. It runs the agent loop (5.3), the MCP server
  with the engine's tools and the MCP client the agent uses (5.4), and
  the replication scheduler (6.7). It touches no DOM.
- WASM: runs sqlite3.wasm with the OPFS SAH pool VFS and owns the OPFS
  cache directory. It executes `db.*`, `sql.*`, `kv.*`, `doc.*` and
  `sync.*` tasks from the AI worker, each as one transaction, and does
  nothing else. It exists so that a long query never stalls the AI
  worker's event loop, which must keep answering the UI and the wire
  (Q6).
- Ownership on paper: every database's owner is AI; WASM is AI's
  executor. "One task per database at a time" holds because the AI
  worker submits database tasks one after another.
- A fourth thread, if ever needed, is made by reusing `queue.ts` and
  `substrate.ts` as they are, with a new entry in the owner table.

### 2.3 Debug mode

- Debug mode is a flag of the ttyd command, `--debug`, set by the start
  script, never a setting. `hello` reports it (Q26).
- With it on: `console.*` is served, `settings.put`, `source.put` and
  `system.restart` are accepted, `sql.run` on server databases is
  accepted, and `log.put` from the page is stored. With it off those
  lines are errors.
- Headers use full names in debug mode, short names otherwise.

### 2.4 The page and its build

- ttyd serves exactly one static file, `build/hyperposition-engine.html`.
  Changing it needs a rebuild and a reload. Nothing is fetched at run
  time but media URLs the provider returns.
- `ts/` holds every script. tsc compiles them with `module` none and
  `outFile` into `build/js/engine.js`, one classic script in reference
  order. Each file defines one frozen object named after the module.
- `page_build.py` merges `html/engine.html` and `html/engine.css`, the
  bundle, sqlite3.wasm as base64, and xterm.js, into the one file. The
  workers are made from a Blob URL of the same bundle; each thread's
  entry is chosen by `self.name`, which `new Worker(url, {name})` sets.
  The output's SHA-256 is printed and is the page's version in `hello`.
- `html/test.html` is built the same way with the test modules added.
- Canonical TypeScript error handling: `strict` on, every thrown value
  an `Error` with `cause` when wrapped, `self.onerror` and
  `unhandledrejection` reported as faults, no empty catch. `log.ts`
  captures `console.*` into a ring and forwards it to the server over
  `log.put` when debug mode is on (Q30).
- The console view is xterm.js in the UI thread in a hidden container.
  ESC shows and hides it when the console is enabled, which it is for
  now (Q15). Research goal: whether xterm.js can be fed while detached from
  the DOM and attached on demand with its scrollback, colours and
  features intact; the headless package is the fallback for feeding.

## 3 JSLB wire format

### 3.1 Framing

```text
message := line blob*
line    := json-object CR
```

- `json-object` is one JSON object in UTF-8 with no whitespace outside
  strings. The encoder emits no CR, and JSON forbids a raw CR inside a
  string, so the first CR, byte 0x0D, ends the line.
- LF is an ordinary byte with no meaning, like every byte other than CR
  outside a string. Nothing translates it, in either direction.
- The blobs follow the CR at once, in header order, each exactly `s`
  bytes, with nothing before, between or after them.
- A reader has two states: bytes to a CR, then known byte counts. It
  never scans blob contents.

### 3.2 Line header, key `"0"`

- `t` `type`: string, required. The handler name: lowercase words joined
  by `_`, namespaces by `.`, as `kv.put`, `doc.get`, `error`.
- `v` `version`: integer, default 0. The version of that type's payload.
- `i` `id`: integer from 1. Present when a reply is expected. Each
  sender numbers its own lines per port.
- `r` `reply`: integer. The peer's `i` this line answers.
- `k` `key`: string. The key the line is about, when it is about one.
- `b` `blobs`: integer, default 0. The number of blob headers.

### 3.3 Blob headers, keys `"1"` to `"b"`

- `s` `size`: integer, required. Bytes of the blob.
- `k` `key`: string. Where the handler stores the blob, when it does.
- `d` `data`: never serialized. In memory, the bytes, or for a streamed
  blob the path of the file holding them (3.7).
- Any other field is the handler's. JSLB carries it and ignores it.
  There is no blob type registry: a blob is opaque bytes to JSLB and to
  the dispatcher, and the handler interprets its headers.

### 3.4 Names and defaults

- A line uses short names or full names in all its headers. Both forms
  in one line is a hard error. Full names are the debug mode form.
- A field at its default is not written: `v` 0 and `b` 0 never appear.
  A version shows up only once a type's payload has changed.
- The payload is the set of keys that are not decimal integer strings.
  Decimal integer keys are reserved for headers.
- The decoder returns headers as sent, plus `d` on each blob. Omitted
  fields stay omitted; `field_get(header, "type")` resolves a short or
  full name and the default.

### 3.5 Values

- Numbers are IEEE doubles. Integers lie within plus or minus 2^53. The
  Python encoder refuses larger ints, NaN and infinities.
- Strings are Unicode; the line is UTF-8 with the strict decoder on both
  sides. An invalid byte sequence is a hard error.
- Duplicate keys take the last value in both languages. Encoders never
  produce them.

### 3.6 Hard errors

- No `"0"`, no `t`, or `b` not matching the headers present. A gap in
  `"1"` to `"b"`, a non-integer or negative `s`, a payload key that is a
  decimal integer string, both name forms in one line, an unknown field
  in the line header.
- A line over `line_max` or a blob over `blob_max`, both from settings,
  refused before the bytes are buffered.
- The decoder raises on the first error and the port that fed it closes.
  There is no resynchronization on a byte stream.

### 3.7 Streaming blobs

- A blob of `s` at most `overflow_bytes` is collected in memory and `d`
  is its bytes. A larger blob is written to a new file in the cache
  directory as its bytes arrive, hashed on the way, and `d` is that
  file's path; the handler moves or links it. Memory per connection is
  therefore bounded by `line_max` plus `overflow_bytes`, whatever the
  upload.
- The encoder yields the JSON bytes, then each `d` as is, bytes or file,
  for the writer to send in order. It never copies blob bytes.

### 3.8 Request, reply, push

- A line with `i` gets exactly one line with `r` equal to it, from the
  peer, on the same port. The reply's `t` is the request's `t`, or
  `error`. A line without `i` is a notification; nothing answers it.
- Ids restart at 1 per port per process lifetime. A reply with an
  unknown `r` is a hard error.
- Either side may send a notification between tasks: the server pushes
  `log.line`, `console.output`, `console.exit` and `kv.changed`.
- One port is one FIFO each way. A handler runs to completion before the
  next line on that port is read.

### 3.9 Transport

- ttyd frames: client to server `'0' + bytes`, server to client the
  same, with `'1'` title and `'2'` preferences first. `wire.ts` strips
  and adds the `'0'`; JSLB never sees it. Frames split anywhere.
- The server puts its pty in raw mode with `tty.setraw` before writing
  anything. Raw mode ends the 4095 byte line, the echo, every control
  character and `IUTF8`. The client sends nothing until `hello` arrives.
- ttyd's 5 s ping is answered by the browser's network stack, so a busy
  worker does not drop the connection.

### 3.10 Flow control, researched

- Output, pty to client: ttyd stops reading the pty after each 64 KiB
  libuv read and resumes only once that buffer is written to the
  socket. One buffer is in flight at a time; no option is needed.
- Input, client to pty: ttyd collects each whole WebSocket message, then
  hands it to libuv's write queue for the pty, which has no bound. The
  only ttyd option in this path is `--srv-buf-size`, libwebsockets'
  per-thread service buffer, default 4096, which is also the receive
  chunk size for both of ttyd's protocols because their `rx_buffer_size`
  is 0. Nothing in ttyd caps memory on upload.
- Decision: ttyd runs with `--srv-buf-size 1048576`; `chunk_bytes` is
  1 MiB, so one WebSocket message is one receive callback; `wire.ts`
  waits for `bufferedAmount` under one chunk before the next; the server
  reads the pty as fast as it arrives and streams big blobs to the cache
  file, so libuv's queue stays short because the consumer is never the
  bottleneck. ttyd's resident size during a 128 MiB upload is measured
  in stage 2 and a credit line is added to the API only if it demands
  one (Q9).
- ttyd's PAUSE command does nothing: `paused` is set at process start
  and never cleared, so `pty_pause` returns early.

## 4 Communication patterns

### 4.1 Lanes

Every message anywhere is one JSLB object. The lanes are:

```text
wire     AI worker  <->  server          bytes over ttyd
ui-ai    UI thread  <->  AI worker       structured clone, buffers moved
ai-wasm  AI worker  <->  WASM worker     structured clone, buffers moved
mcp      agent      <->  MCP server      JSON-RPC objects, local port
http     agent      <->  provider        HTTPS, the generic protocol
```

A port is anything with `line_post(line)` and `line_receive(fn)`:
local (same thread), thread (`MessagePort`) and wire. Code that submits
a task never knows which.

### 4.2 Connection lifecycle

- Open: the UI thread creates the WASM and AI workers from the bundle.
  The AI worker fetches `/token`, opens `/ws` with subprotocol `tty`,
  sends ttyd's first JSON message, skips the title and preferences, and
  waits for `hello`.
- `hello` is the server's request with `i` 1: `bootstrap`, `sha256`,
  `pid`, `python`, `sqlite`, `root`, `debug`, `settings`, `seq` per
  server database, `console` state. The AI worker answers with the
  page's `sha256`, `tab` id and `seq` per browser database, then posts
  `boot.hello` to the UI so the status shows.
- Then, in order, as tasks: `db.open` on WASM for `metaverse` and
  `files`; `sync.pull` from the server for each; `doc.head` of
  `world`; `doc.get` of its current scene; `kv.get` for media the scene
  names that the browser lacks; `render` to the UI. 7.4.9 shows it.
- Close: the AI worker closes the WebSocket with 1000. ttyd sends SIGHUP
  and the server exits; the console's dash, if open, gets SIGHUP from
  its pty. There is no `quit` line.
- There is no `cancel`. A runaway is ended by closing the connection.

### 4.3 Tasks across threads

- `task_submit(line)` returns a promise of the reply. The queue reads the
  owner table by the line's type prefix and posts to that owner's port,
  or runs the handler at once when the owner is this thread.
- Blob buffers are transferred. After `task_submit` the caller's `d` is
  detached.
- Each thread runs one task at a time. Bodies are synchronous (1.3). On
  the AI thread a handler may return a promise, since every database
  access inside it is a task of its own; on WASM every handler is
  synchronous (Q7). Forwarding, a route list each hop pops, is not in
  the first draft.

### 4.4 Errors, disconnect and reconnect

- Server: a handler that raises produces one `error` line with `r` when
  the request had `i`, carrying `message` and `stack`, written and
  flushed before the process exits 1. The write is the realistic effort
  to get the message out before the connection ends.
- Page: a fault in any thread posts `fault` to the UI, which shows the
  message and stack, disables the controls, tells the AI worker to close
  the wire, and shows Reconnect. Reconnect opens a new WebSocket in the
  same page; nothing reloads the page (Q12).
- Reconciliation: the new `hello` carries the server's `seq` per
  database and whether a console is open (it never is, the process is
  new). The AI worker compares with its own `seq`, pulls or pushes the
  difference (6.7), and resumes. Nothing in flight is retried: a task
  that had no reply is reported to the player as failed.

### 4.5 The console inside the tty

- `console.open` in debug mode forks dash under a new pty with a scrubbed
  environment, the root as working directory, and `TERM` xterm-256color;
  the reply carries its pid. Output arrives as `console.output` with one
  blob; input is `console.input` with one blob; `console.signal` sends a
  signal to its group; `console.close` ends it; `console.exit` is pushed
  with the code. The dash pty stays cooked, so it echoes.
- The user opens the console from the page. The AI opens or uses it only
  through the `console_run` tool after the permission flow (4.6).
- Sandboxing is a door: a container, namespaces or limits may be put
  around dash later without changing any line type.

### 4.6 Permission

- A tool marked `permit` in the tool list is not run until the UI shows
  the request with Accept, Deny and Always Allow below it. Accept runs
  it once; Deny makes the tool call return an error to the model; Always
  Allow records the tool name in the `preferences` document, which
  replicates (Q16).
- The flow is two tasks: `permit.ask` from AI to UI returns at once with
  the request shown; `permit.answer` from UI to AI carries the choice and
  resumes the tool call.

## 5 The AI

### 5.1 Not MVC

The model of this system is the set of databases, intermediated by one
thread. Threads that talk directly to each other and keep their own
private storage, the UI's `media_db` for one, are part of the design,
not an exception to it. A new thread that needs databases of its own
reuses the task system and the substrate unchanged.

### 5.2 The generic provider protocol

- The provider is any HTTPS service speaking the chat completion
  protocol: `POST {base_url}/chat/completions` with `model`, `messages`
  of `system`, `user`, `assistant` and `tool` roles, `tools` as function
  schemas, and `tool_choice`; answering `choices[0].message` with
  `content` and `tool_calls`, each `id`, `function.name` and
  `function.arguments` as a JSON string, and `finish_reason`. Images:
  `POST {base_url}/images/generations` with `model`, `prompt`, `n` and
  `response_format`, answering `data[]` with `url` or `b64_json`. xAI
  serves both; Anthropic serves the first through its compatibility
  endpoint and no images (Q4).
- `provider.ts` is the one door: `chat_complete(request)` and
  `image_generate(request)`, each one HTTPS request from the AI worker
  with the key in the `Authorization` header. `base_url`, the model
  names and the timeouts are settings. The key is not a setting: the
  server reads `secrets.json` from its root and passes the key in
  `hello`, where it lives only in the AI worker's memory (Q5, Q25).
- `provider_script.ts` implements the same interface with no network: a
  script is a table of nodes; the user's latest message is a single
  integer that selects the node's reply, which may carry tool calls; a
  tool result advances to the node the reply names. This is how every
  automated test and every transcript in DATA/ drives the engine.

### 5.3 The agent loop

- One turn: the player's `ai.say` or `ai.click` becomes a `turn` row and
  a user message; the agent calls `chat_complete` with the tool list
  from the MCP client; each `tool_call` is one MCP `tools/call`; its
  result is a `tool` message; the loop repeats until a reply has no tool
  calls; the final content is the subtitle; the agent submits `render`.
- The system prompt is the `prompt` document of the current scene's
  universe, with the hyperposition's analyst prompt as the first one.
- Time stops: nothing runs without a player task. The agent sets no
  timers.
- Turn storage: `turn(scene, n, role, content, seq)` in the metaverse
  database, keyed by the scene's Document-Ref and replicated by the row
  log. Compaction replaces turns 1 to N with one summary turn in one
  transaction (Q19).

### 5.4 MCP

- `mcp.ts` and `mcp.py` implement JSON-RPC 2.0 and the MCP methods
  `initialize`, `notifications/initialized`, `ping`, `tools/list` and
  `tools/call`, protocol revision `2025-06-18`, with `tools` the only
  capability advertised at first (Q8). Both are transport-agnostic:
  `message_handle(object)` returns the response object or nothing.
- Transports: local port inside the AI worker; the JSLB line `mcp`
  whose payload is the JSON-RPC message, so the server's tools reach the
  agent over the wire; and `mcp_stdio.py`, newline-delimited JSON-RPC on
  stdin and stdout, so an external agent can drive a server directly.
- The AI worker's MCP client connects to two servers, the browser's and
  the Python one, and lists their tools under `browser.` and `server.`
  prefixes. The provider sees one flat tool list.
- Tools, browser: `sql_run`, `universe_create`, `region_create`,
  `doc_get`, `doc_put`, `doc_head`, `kv_list`, `scene_enter`,
  `image_make`, `render`. Server:
  `console_run` (permit), `log_tail`, `source_put` (permit, debug),
  `system_restart` (permit, debug). API/mcp/tools.json is the list as
  `tools/list` returns it.

### 5.5 Images

- `image_make` calls `image_generate`, which answers with a URL or
  base64. The AI worker submits `media.fetch {url, key}` to the UI,
  which downloads the bytes, decodes them into `media_db`, and replies
  with size and SHA-256 (Q17). The AI worker then asks the UI for the
  bytes with `media.bytes` only when it decides to back them up (6.6).
- A base64 answer is decoded in the AI worker and posted to the UI with
  the buffer transferred; the rest is the same.

### 5.6 Simulation steps

- A simulation step is a JavaScript function the AI writes and stores
  in `files` under `<universe>/<region>/step/<name>.js`. The agent runs
  it in the AI worker with `new Function` against the store proxy when
  a tool or a turn asks for it. Nothing compiles at run time; the
  draft's server-side TypeScript compiler is dropped (Q23).

## 6 Data

### 6.1 Engines and connections

- Server: Python's `sqlite3` on the system library, floor 3.38 for
  `STRICT`, `WITHOUT ROWID` and the JSON functions (Q31). Browser:
  sqlite3.wasm pinned by version and SHA-256, the OPFS SAH pool VFS, in
  the WASM worker only.
- One connection per database per owner. Server pragmas:
  `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`,
  `busy_timeout=5000`. The browser VFS keeps the rollback journal.
- A database name is `[a-z][a-z0-9_]*(/[a-z][a-z0-9_]*)*`; its file is
  `<name>.sqlite` under the owner's root, with `/` as directories.

### 6.2 Databases

```text
name                    holds                                 schema
metaverse               universes, world, preferences, turns  engine
files                   media and scripts by key              engine
<universe>              the experience: rules, prompts, media  AI
<universe>/<region>     the region's entities and scenes      AI
```

- `metaverse` and `files` exist on both sides with the engine's schema
  (API/sql). The server also holds `log`, not replicated.
- A universe database and its region databases are created by the AI as
  the database administrator: typed tables for each kind of component,
  indexes on what it queries, views, no JSON columns by default. The
  engine imposes only engine.sql in each (6.4), so that Document-Refs
  work everywhere, and `sql_run` refuses a statement that names those
  tables (Q22).
- The region is one database, attached to the universe's connection
  as `region` when the player is in it, so one transaction spans both
  (Q21). Division into regions means disjoint entities; scenes within a
  region share entities that follow the player from location to
  location.
- Universes are documents, `metaverse/universe/<name>`: the title, the
  regions and the seed scene. The hyperposition's scene, the analyst's
  prompt, the world and the preferences are seeded by the server when
  it creates a new `metaverse` (Q20).
- The world is the `world` document in `metaverse`: the universe, the
  region and the current scene's Document-Ref.

### 6.3 The KV table

```sql
CREATE TABLE meta (
    name  TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID, STRICT;

CREATE TABLE kv (
    key    TEXT    PRIMARY KEY,
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

- `sha256` is the content hash: it names the overflow file, detects an
  unchanged write, and lets replication skip bytes the other side has.
- `seq` comes from `meta` row `seq`, incremented in the same transaction
  as the write. `kv_gone` records deletions; a put of a gone key removes
  its tombstone. `data` is NULL when the value is in the cache (6.5).
- There is no type column. What a value is, is the business of the key's
  owner.

### 6.4 Documents and Document-Refs

```sql
CREATE TABLE doc (
    path    TEXT    NOT NULL,
    version INTEGER NOT NULL,
    body    TEXT    NOT NULL CHECK (json_valid(body)),
    seq     INTEGER NOT NULL UNIQUE,
    PRIMARY KEY (path, version)
) WITHOUT ROWID, STRICT;

CREATE TABLE doc_head (
    path    TEXT    PRIMARY KEY,
    version INTEGER NOT NULL
) WITHOUT ROWID, STRICT;
```

- A Document-Ref is `<db>/<kind>/<name>/<version>`:
  `castle/gatehouse/scene/arrival/54`. A path is the ref without its
  version: always a database name, a kind and a name, so the database
  is the leading one or two segments with no lookup. Each segment is
  `[a-z0-9_]+` and the version a positive integer (Q3). `doc_put(path,
  body)` writes version `head + 1` and moves the head. A written
  version never changes. `doc_get(ref)` returns that version;
  `doc_head(path)` returns the current ref.
- Pushing a new scene is `doc_put` of the scene and `doc_put` of
  `world` pointing at the new ref. Replication carries both rows; the
  old versions stay as history.
- A document names the documents and media it needs in a top-level
  `refs` array of Document-Refs and media keys, so the engine can
  prefetch without knowing the schema (Q10). `doc_get` of a ref the local
  database lacks asks the server with `doc.get` over the wire, stores
  the answer, then returns it. The same for `kv.get` of media.
- This is the no-SQL layer: the AI writes JSON documents where a
  document fits, typed tables where a table fits, and the engine
  replicates both the same way, by `seq`.

### 6.5 Overflow to the cache

- A KV value over `overflow_bytes`, 128 KiB, lives in
  `<root>/cache/<sha256 hex>` with `data` NULL. Below it, in the row.
  The browser's cache is an OPFS directory owned by the WASM worker.
- Write order: file first, then the row. A crash between the two leaves
  an unreferenced file that `kv_check` removes. A delete removes the
  file when no other key shares the hash.
- The streaming decoder (3.7) already wrote the file; `kv_put` of a
  streamed blob renames it into place by hash, no second copy.

### 6.6 Media tiers

```text
tier              where            keeps                        evicts
media_db          UI thread        decoded images in use        by budget
files (browser)   WASM worker      refs of the current region   on leave
files (server)    server           everything ever stored       never, v0
```

- The provider's image goes to the UI first (5.5). The AI worker backs
  it up to the server at once with `kv.put` on `files`, streaming the
  bytes it asked the UI for, and to the browser's `files` only when the
  current scene's `refs` name it. Budgets are settings (Q18).

### 6.7 Replication

- Continuous while efficient: after every committed task that changed
  `seq` in a replicated database, the AI worker schedules one `sync.push`
  carrying the rows above the server's last known `seq`, coalesced so at
  most one push per database is in flight. The server pushes `kv.changed`
  notifications and the browser pulls.
- `sync.pull {db, since}` returns `kv`, `kv_gone`, `doc`, `doc_head` and
  `turn` rows above `since` without blob data; blobs are fetched by
  `kv.get` when the receiver lacks that `sha256`. `sync.push` is the
  same rows with blobs attached for hashes the receiver said it lacks.
- First copy of a database is a snapshot: `db.snapshot` yields
  `Connection.serialize` bytes as one blob; `db.restore` writes a temp
  file and renames it. Both report SHA-256.
- The AI's own tables in universe and region databases have no row log
  in v0: a database that changed during a turn is pushed whole by
  `db.snapshot` and `db.restore` after the turn. A change log kept by
  triggers the engine installs on every table DDL creates is the second
  draft (Q2).
- The browser writes its world and the player's documents; the server
  is their backup and the master of scripts and universes. Two tabs on
  one world is refused by the second tab (Q11).
- Schema correctness of what the AI writes is a non-goal of the engine.
  The smoke test is that an arbitrary generated script runs SQL
  transactions through the tool and the rows replicate.

### 6.8 Settings

- `settings.json` at the checkout's top level, copied to the root by
  start, is read and validated by `settings.py` and sent in `hello`
  unmodified (Q24). The page reads it through `settings.ts`. No
  filtering.
- It holds constants only: ports, `line_max`, `blob_max`,
  `overflow_bytes`, `chunk_bytes`, media budgets, provider `base_url`
  and model names, MCP revision, console enabled. Never a password or a
  key. API/settings.json is the v0 proposal.
- `settings.put` in debug mode rewrites the file in the root and takes
  effect at the next `hello`.

## 7 Modules

### 7.1 Naming

- Functions and classes carry two English names: `line_encode`,
  `kv_put`, `task_submit`, `LineDecoder`, `TaskQueue`. Modules and test
  modules are the exception: `jslb`, `tap`, `i18n`, `test_jslb`.
- Test methods are `test_` and at least two names.
- Constants are `_UPPER_NAME` at the top of each Python file; TypeScript
  has one frozen `constants` object per module.
- `i18n` is a function in both languages, `i18n("name", ...args)`; the
  `from` ban has one exception, `from i18n import i18n`. Strings live in
  `i18n/en-US.json`, read by both languages and checked for the same
  names by stage 0 (Q29).

### 7.2 Python, bottom up

Each has `test_<module>.py` beside it holding `unittest.TestCase`
classes. API/python holds the stubs.

- `i18n.py`: `i18n(name, *args)`; raises on a missing name or a
  placeholder count that differs from the argument count.
- `tap/`: tappy's sdist copied as it is, producers and consumer, pinned
  by version and SHA-256, with its license. The consumer checks every
  TAP stream (8.1). The copy's style is its own (Q28).
- `jslb.py`: `Object`, `header_make`, `blob_make`, `field_get`,
  `blobs_of`, `line_encode`, `LineDecoder`, `WireError`. Section 3.
- `verbose.py`: `level_set`, `log_write`, `log_tail`, `log_follow`.
  Levels 0, 1 and 2 as the draft gave them, for the logs the engine
  writes itself; the subprocess wrapper is gone with the PY to SH ban.
- `settings.py`: `settings_load(path)`, `settings_check(settings)`.
- `substrate.py`: `Store` with `db_open`, `db_close`, `db_list`,
  `db_attach`, `db_detach`, `kv_get`, `kv_put`, `kv_delete`, `kv_list`,
  `kv_check`, `doc_get`, `doc_put`, `doc_head`, `ref_split`,
  `turn_append`, `turn_list`, `turn_compact`, `sql_run`, `db_snapshot`,
  `db_restore`, `sync_pull`, `sync_apply`, `transaction_run`;
  `schema_apply(connection, kind)`.
- `dispatch.py`: `handler_register`, `line_dispatch`, `reply_make`,
  `error_make`, `id_next`. Calls `fn(line, **payload)`.
- `mcp.py`: `Server` with `tool_register`, `message_handle`; `Client`
  with `initialize_send`, `tools_list`, `tool_call`; JSON-RPC helpers.
- `mcp_stdio.py`: the stdio transport around `mcp.Server`.
- `console.py`: `Console` with `console_open`, `console_write`,
  `console_read`, `console_signal`, `console_close`, `fd`.
- `engine_kv.py`, `engine_doc.py`, `engine_sync.py`, `engine_log.py`,
  `engine_console.py`, `engine_mcp.py`, `engine_system.py`: the
  handlers of API/ts/lines.d.ts, one module per namespace.
- `main_loop.py`: `loop_run(read_fd, write_fd, root, debug)`.
- `bootstrap.py`: arguments, raw mode, `hello`, `loop_run`, restart.
- `page_build.py`: the one file from templates, bundle and wasm.
- `third_party_fetch.py`: urllib fetch and SHA-256 check into
  `third_party/`.
- `test_all.py`, `test_wire.py` rewritten for JSLB, `test_browser.py`,
  `devtools.py` split from the screenshot tool, `test_posix.py` as it is.

### 7.3 TypeScript, bottom up

Each is `ts/<name>.ts` with `ts/test_<name>.ts`. API/ts holds the
declarations.

- `i18n.ts`, `tap.ts` (tappy's `Tracker` and `TAPTestRunner`),
  `unittest.ts` (`TestCase`, `TestSuite`, `TestLoader`, the asserts
  used), `jslb.ts`, `dispatch.ts`, `queue.ts`, `wire.ts`, `log.ts`,
  `settings.ts`.
- `substrate.ts`: `Store` over sqlite3.wasm, the same API as Python,
  runs in the WASM worker. `store_proxy.ts`: the same API returning
  promises, runs in the AI worker, each method one task.
- `mcp.ts`, `provider.ts`, `provider_script.ts`, `agent.ts`,
  `tools_browser.ts` (the tools of 5.4 registered into `mcp.Server`).
- `media.ts` (`media_db`), `console_view.ts` (xterm.js), `page.ts`,
  `worker_ai.ts`, `worker_wasm.ts`, `boot.ts` (entry by `self.name`).

### 7.4 Dependency graph

```text
PY  i18n   tap
      |
    jslb  verbose  settings  substrate  mcp  console
       \     |        |         |        |     |
        dispatch -----+---------+--------+-----+
            |
    engine_kv engine_doc engine_sync engine_log engine_console
    engine_mcp engine_system
            |
        main_loop
            |
        bootstrap          mcp_stdio

TS  i18n  tap  unittest  settings  log
      |
    jslb     substrate(sqlite3.wasm)   provider  provider_script
      |          |                        |
    dispatch     |                      agent --- mcp --- tools_browser
      |          |                        |
    queue --- wire --- store_proxy -------+
      |          |                        |
    media  console_view                   |
      \       |                           |
      page  worker_ai  worker_wasm  <-----+
            \    |    /
              boot  ->  page_build.py
```

No arrow points up. A test module imports only its module and `tap`.

### 7.5 Admin scripts and scripts ignored

- The Windows scripts change in one function: the ttyd options gain
  `--srv-buf-size 1048576`, the index file name, and `--debug` passed
  through when the start script is given it.
- `archive.sh` and `clean.sh` are not part of the project and are
  ignored.
- `.sh` parallels of the Windows scripts, a Dockerfile and a container
  test under `--container` are doors kept open, not work.

## 8 Testing

### 8.1 The runner and the stream

- unittest in both languages. Python runs tappy's `TAPTestRunner`; the
  TypeScript clone implements only the unittest and tappy surface the
  tests use, with identical output text.
- One TAP plan per language per run. Each module's suite is one subtest
  block, indented four spaces with its own plan, followed by a parent
  level `ok N - <module>` line. The parent plan is the number of modules.
- Every stream is checked by tappy's consumer on the server:
  `test_all.py` parses its own output after writing it; the page sends
  its stream as `tap.report` (Q14) and the server parses it and replies
  with the counts. A stream the consumer rejects fails the run (Q13).
- `failfast`: the stream stops at the first `not ok`, with the
  traceback as diagnostic lines. The driver prints `fail pass` last.
  Side effects between tests are banned; name order is fine.

### 8.2 Runners

- `python3 python/test_all.py`: the Python suites in dependency order,
  then `test_wire.py` for the wire rungs.
- `python3 python/test_browser.py`: builds `test.html`, serves it
  through Linux ttyd, runs the TypeScript suites in headless Chrome,
  receives `tap.report`, saves a PNG. There is no other JavaScript
  runner; Node is not one.
- `python3 python/test_posix.py` keeps its role for every whitelisted
  file.

### 8.3 Cross-language vectors

- `python/vectors/*.jslb`: byte files from `jslb.py` covering empty
  payloads, every header field, both name forms, zero to three blobs,
  blob bytes holding CR, LF, 0x03, 0x04, 0x13 and invalid UTF-8, and each
  hard error. Both decoders read every vector, compare to the `*.json`
  sidecar, re-encode, and read the result, whole, by single bytes and
  split at every offset.

### 8.4 The UI thread stress test

- A long task observer on the UI thread during a 16 MiB `kv.put` and
  `kv.get`, during a 128 MiB upload, and during a scripted turn with an
  image, requires no task over 5 ms, a soft target reported as a
  measurement, and no synchronous I/O call on the main thread at all,
  which is a hard failure found by tracing.

### 8.5 Stages

Each stage names what is built, what its tests prove, what a person
surveys, and the exit criterion. A stage starts only after the previous
one's exit criterion holds.

8.5.1 Stage 0, the harness: `third_party_fetch.py`, `tap/`, `i18n`,
`test_all.py`, `tap.ts`, `unittest.ts`, `devtools.py`,
`test_browser.py`, `page_build.py` for the test page, tsc in the build.
Proves the nested class of one passing, one failing, one raising and one
skipped method yields tappy's text in both languages, as one subtest
block under one plan, accepted by the consumer; `failfast`; `i18n`
raises in both. Survey: the TAP text; the PNG. Exit: both runners exit 0
on the real suites and 1 on the nested class.

8.5.2 Stage 1, JSLB: `jslb.py`, `jslb.ts`, the vectors, streaming to a
file over `overflow_bytes`. Exit: both suites pass; each reads all the
vectors of the other.

8.5.3 Stage 2, the raw wire: `bootstrap.py` with raw mode and `hello`,
an `echo` handler; `test_wire.py` rungs `hello`, `echo`, `echo 1 MiB
with control bytes`, `echo 128 MiB` with ttyd's resident size printed,
`ttyd killed`, and the last line regression of RESEARCH 1 kept as it is.
Exit: all rungs pass twice.

8.5.4 Stage 3, the server substrate: `substrate.py`, `settings.py`.
Proves KV, documents, heads, tombstones, `seq` across reopen, overflow
at exactly `overflow_bytes`, snapshot and restore, a `SIGKILL` between
file and row, `kv_check`. Exit: passes under `python3 -X dev`.

8.5.5 Stage 4, dispatch and the main loop: `dispatch.py`, `engine_*`,
`main_loop.py`, `verbose.py`, `mcp.py`, `mcp_stdio.py`. Proves, through
`test_wire.py` and a stdio MCP client written in the test: `kv.put` and
`kv.get` byte identical, `doc.put` and `doc.head`, `sync.pull`,
`log.follow`, `tools/list` and `tools/call` over stdio and over the
`mcp` line, an unknown type giving `error` then exit 1, `system.restart`
keeping the pid after `source.put` in debug mode, and the same refused
without it. Exit: rungs pass; pyright clean.

8.5.6 Stage 5, the page reaches the server: `dispatch.ts`, `queue.ts`,
`wire.ts`, `log.ts`, `worker_ai.ts` without databases, `page.ts` showing
`hello`. Proves the hello relay, a 16 MiB round trip equal by SHA-256,
the stress test of 8.4, a fault showing and Reconnect working. Survey: a
PNG. Exit: `test_browser.py` exits 0.

8.5.7 Stage 6, the browser substrate: `substrate.ts`, `worker_wasm.ts`,
`store_proxy.ts`. Proves the stage 3 suite ported, a second load finding
the rows, overflow files in OPFS, one database task at a time. Exit:
identical counts to the Python suite.

8.5.8 Stage 7, replication: `sync.*` both sides. Proves snapshot first
copy, then rows only above `seq` and no blob the receiver has, counted
on the wire. Exit: both directions pass with predicted counts.

8.5.9 Stage 8, the console: `console.py`, `engine_console.py`,
`console_view.ts`, the permission flow. Proves `echo` through dash and
back into xterm.js, `^C` ending `sleep 600`, ESC showing and hiding the
view, Deny returning an error to the caller. Survey: a PNG with the
console visible. Exit: the rung and the browser test pass.

8.5.10 Stage 9, the hyperposition: `mcp.ts`, `provider.ts`,
`provider_script.ts`, `agent.ts`, `tools_browser.ts`, `media.ts`, the
hyperposition scene and prompt. Proves a scripted conversation of
integer inputs: a turn row, a tool call creating a typed table by DDL,
an image fetched into `media_db`, a render with the subtitle, a backup
to the server's `files`, time not advancing without input. Survey: a
PNG after the exchange. Exit: the scripted run passes; the real provider
is behind a setting and outside the automated tests.

8.5.11 Stage 10, the beachhead: the one-function change to the Windows
scripts; the engine serving from the maintainer's WSL account; the
maintainer's test plan run by hand. Exit: the maintainer's sign-off.

## 9 Operations

- First beachhead: the engine runs from the maintainer's own user
  account on WSL, started by the existing Windows scripts, nothing as
  root, no service manager, no container. That is the first goal.
- Server root `~/.cache/xsjs/`: `bootstrap.py` and the Python package,
  the page, `settings.json`, `secrets.json`, `ttyd.log`, the databases
  and `cache/`. Start copies the package, the page and the settings
  there.
- Doors kept open, not implemented: Docker under `--container`, a
  systemd user unit, a sandbox for dash, the `.sh` scripts, test
  environments on other OS flavours.
- Certificate, boot and checkout decisions of the project direction
  stand unchanged.
