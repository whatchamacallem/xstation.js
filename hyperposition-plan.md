# the hyperposition-engine plan

This file is the whole plan; nothing outside this checkout is needed to
read it. Section 0 orients a reader who has seen nothing else. Sections
1 to 9 are the design. Section 10 holds what was asked for and is not
built, each with its design beside it. Section 11 holds what was decided
against. Section 12 is the record of every decision of the planning
process, each question with the maintainer's literal answer. Section 13
grades the requests the audit found unsatisfied or changed without
confirmation against this plan. Section 14 lists the points the
maintainer never confirmed. Section 15 is the maintainer's original
statement of requirements.

## 0 Orientation

This file is the whole plan. A reader who has seen nothing else starts
here: 0.1 and 0.2 say what is being built, 0.3 how the maintainer wants
it built, 0.4 what the checkout holds, 0.5 the terms and 0.6 how to use
the rest.

### 0.1 The product

- The hyperposition-engine is a web page, served by ttyd from a Python
  back end, in which an AI guides a person through experiences. An
  experience is presented as large still images made by generative AI
  from a database of facts that describes it. The product is a stack for
  "vibe coding" an experience and interacting with it.
- The page is bare bones HTML, CSS and JavaScript, written in
  TypeScript (2.5). The back end is ttyd, Python and dash.
- `xsjs` is the name of the ttyd based back end administration tool
  suite, the Windows scripts at the top level of the checkout. The
  engine is one application of it, and the name stays.
- The engine is a template and a development environment. The AI writes
  each experience's scripts and database schema (5.6, 6.6); the engine
  supplies the substrate: databases, the wire, the task manager, the MCP
  tools and the provider protocol.
- ttyd is a stepping stone. It first serves the page. Its normal
  terminal protocol, the one it serves to xterm.js, is recycled as the
  debug console; every other byte on the wire is JSLB (3).
- JavaScript, written as TypeScript, in the browser and Python on the
  server is a permanent division. Shell appears only in the admin
  scripts and in the debug console. The Python server may one day be
  replaced by a hardened C, C++ or Rust component (10.2).

### 0.2 The experience

- The player starts at a blank black page with one subtitled remark,
  "How can I help you?". What the player answers goes to the AI, which
  talks to an MCP server in the browser on a worker thread and guides
  the player through different experiences as requested.
- That starting point is the hyperposition, run by a very bored British
  female AI psychoanalyst, the analyst. Its scene holds nothing but
  wisps of fog and a few inexplicable bright lights, the engine bears
  its name, and it is the one scene the player cannot modify. The
  analyst tries to determine the right universe to send the player to.
  It has admin control over the metaverse and is expected to perform
  requests as non judgementally and efficiently as possible. When the
  engine loads with no scene selected it loads the hyperposition (6.6).
- multiverse: a catalogue of separate experiences. The database
  `metaverse` (6.2) is that bookshelf, and the maintainer uses both
  words.
- universe: a specific experience design.
- world: the current experience state, the global state of one
  experience.
- region: everything in your area. Regions are disjoint entities.
- scene: a location. Scenes follow the entities that move with the
  player from location to location through a local environment. Each
  scene is a new conversation with a new establishing shot. An
  experience is a series of scenes, with media files and a collection of
  entity databases. Compaction of a conversation is possible and
  crossfades stream in (10.7).
- The loop: the player initiates interaction and time always stops; a
  JavaScript handler optionally updates the page or notifies the AI; the
  AI interacts with the databases directly or through JavaScript, over
  MCP; then it updates the page, possibly with a new picture or scene,
  which is the render step; the player is presented with the updated
  page (5.3).
- By default time stops when the player stops, and gameplay is 2.5D and
  slow moving. The design of the game Myst, with basic RPG elements
  added, is the template. Multiplayer, turn based strategy games must
  work too (10.1). That may need a rewrite of the back end in C++
  (10.2), but proving the back end's algorithms and operation matters
  more now than thinking about multiplayer and C++.
- The service provides self designed generative AI experiences, and
  players are guided into experiences within their multiverse.

### 0.3 The maintainer's priorities

- The maintainer owns the project and decides correctness and
  requirements. Their primary concern is architecture, correct wire
  formats, correct communication patterns, correct SQL design and
  elegant use for this application (12.1.1).
- Modules are designed before they are implemented, with a professional
  separation of responsibilities, and then built in an incremental plan
  where everything is kept bare bones and can be surveyed, so the
  foundations are visible before the next stage of construction begins
  (12.1.1, 8.7).
- In the maintainer's words: "having ideal architecture is what is
  golden about this project, and delivery of working code is second"
  (12.4.2.4); "I would rather have an incomplete code base with correct
  APIs than have a demo that has to be rewritten after the ship already
  left port. Implementation churn is unacceptable as a planning goal."
  (12.2.2.3); "stop designing things and start building the apis i need
  from bottom up" (12.4.2.5).
- The work is bottom up and test driven: design a module, write its
  tests, fix it, then stack the next module on it with calls going one
  way, down (1.1). Drafts and prototypes are not goals; architecture and
  unit tests come before integration tests, "slowly leading to the top
  of the mountain" (12.1.7).
- Two failure modes are to be avoided (12.1.8). One is example code that
  no need of the design motivates, which later sessions read as a
  decision and preserve. The other is example code with the wrong API,
  which leaves the maintainer without any knowledge of the good API the
  planner reasoned out before curtailing its effort. The remedies are in
  this plan: nothing is added without its request (1.5), and every
  deferred capability is written with its full design (10).
- The maintainer will "require explanations before plans change"
  (12.3.27.1). Where this plan, a literal answer or a rule seems wrong,
  or an assumption of 14 is in doubt, stop and ask. Never decide
  silently, and never carry out something unrequested instead.
- The project rules apply to every agent in full. The ones this plan
  leans on: fail fast with no fallbacks (1.2); nothing unmotivated
  (1.5); two English names for each function and class (7.1); packages
  are requested from the maintainer and never installed unasked; the
  maintainer reviews every commit, so agents neither commit nor stage.

### 0.4 The checkout when this plan was written, 2026-10-18

Current state, not design (1.5): this plan chooses what is reused.

- `python/bootstrap.py` and `python/bootstrap.html` are the previous
  design's dash like command processor and its page, run by ttyd on a
  pty in canonical mode. The new bootstrap.py replaces them (7.2); their
  `put`, `ls`, forked modules and command loop are ripped out (11).
- `python/test_wire.py` is the wire test: Linux ttyd on `--port 0`, its
  port and version read from its log, running a copy of bootstrap.py
  made under `build/`, in about one second. It is the harness of the
  stage 2 rungs (8.7.3).
- `python/xsjs_screenshot.py` and `python/xsjs_screenshot_wsl.py` drive
  headless Windows Chrome or Edge over DevTools through a C# relay run
  by `powershell.exe`, because WSL's NAT cannot reach Windows'
  127.0.0.1. That relay is the implementation of `devtools.py` (8.2).
- `python/test_posix.py` formats and checks the whitelisted files with
  ruff, shfmt and a comment lexer; `python/reformat.py`,
  `python/reformat_whitelist.txt` and `python/pyproject.toml` support
  it. A new source file is added to the whitelist when it is created.
- `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_stop.ps1`,
  `xsjs_status.ps1` and `powershell/` are the Windows administration
  scripts. ttyd listens on 127.0.0.1:5769 inside WSL and a `netsh` port
  proxy forwards 5768 to it. They change in one function (7.5).
- `API/` holds the external API of every module and `DATA/` synthetic
  transcripts of the standard communication, both written from this
  plan before any code. Nothing in them runs, and they follow the plan.
- Nothing of the design in sections 1 to 9 is implemented. `ts/`,
  `html/`, `i18n/`, `third_party/`, `python/tap/`, the substrate and the
  page do not exist.
- Toolchain observed on 2026-10-18 in the maintainer's WSL account,
  Ubuntu 26.04: Python 3.14.4 with SQLite 3.46.1; Node 22.22.1 and npm
  with no `tsc`, which stage 0 needs and the maintainer must be asked to
  install; ruff, pyright, shfmt and mdformat; docker, unused; Windows
  Chrome or Edge for the browser tests.
- ttyd: the apt package, 1.7.7-4build1 at `/usr/bin/ttyd`, offers
  `--url-arg` but not `--srv-buf-size`. A build from source at
  `../ttyd/build/ttyd`, 1.7.7-2922cb8, offers both. 3.10 and 7.5 need
  `--srv-buf-size`; see 14.19.
- Facts established on 2026-10-17 and relied on: CPython accepts decimal
  string keys in `**kwargs`; `json.loads` with `object_hook` nests;
  `json.dumps` with `allow_nan=False` refuses NaN and writes integers
  past 2^53 unchanged; `Connection.serialize`, `os.unshare` and
  `tty.setraw` exist. In ttyd 1.7.7's source the pty read pauses until
  each 64 KiB buffer is written to the socket, client input goes to
  libuv's write queue with no bound, PAUSE does nothing because the
  pause flag is set once at process start, and the only buffer option
  is `--srv-buf-size`, libwebsockets' `pt_serv_buf_size`, default 4096,
  which both protocols use as the receive chunk size (3.10).

### 0.5 Terms

- JSLB: JS-Line-Blobs, the wire format of 3. A line is one JSON object
  ending in CR, followed by blobs of bytes.
- ttyd: a server that runs a program on a pty for each WebSocket and
  serves a terminal page. dash: the POSIX shell, used only as the debug
  console. tty 0 is the console, tty 1 the engine (2.3).
- xterm.js: the terminal emulator in the browser that shows the console.
- bootstrap.py: the platform services around the main loop: arguments
  and role, the lock, raw mode, `hello`, loading the main loop,
  restart, the console. main_loop.py: the select loop and the stock
  dispatcher (7.2).
- `hello`: the server's first request on the engine tty, carrying
  settings, `seq` per database and the provider key (4.4).
- Task manager: the per thread queue that dispatches one line at a time
  to synchronous handlers, which return a reply, nothing or a sleep
  (4.2). Port: anything that posts and receives lines (4.1).
- Substrate: the single door to SQLite on both sides, with the KV
  accessor, documents, turns and replication (6).
- KV row, Key-Value-Ref, Document-Ref, head: 6.3 and 6.4. `seq`: a
  database's counter of modifying operations (6.3, 6.8).
- OPFS and the SAH pool VFS: the browser's private file system and the
  sqlite3.wasm storage that runs on it in a worker (6.1).
- MCP: the Model Context Protocol, JSON-RPC 2.0 with tools (5.4).
- ECS: Entity Component System, the record structure the AI uses for
  scene data.
- Analyst, hyperposition, metaverse: 0.2. Debug mode: the setting
  `debug` (2.4).
- Door: a capability the design keeps open without building it. Section
  10 holds each with its design.
- Permit tool: a tool that runs only after the player accepts it (4.6).
- TAP: the Test Anything Protocol (8.1).
- A, B, C, D: the audit's grades of a request: unsatisfied or modified
  without cause, with cause but without confirmation, confirmed
  withdrawn or modified, satisfied (12.4, 13).

### 0.6 Using this plan

- Sections 1 to 9 are the design; 10 the capabilities asked for and not
  built, each with its design; 11 what was decided against; 12 the
  record of every question and the maintainer's literal answer; 13 the
  grades of the audit's findings; 14 the points never confirmed; 15 the
  original statement of requirements.
- Build in the stage order of 8.7. A stage starts only when the previous
  stage's exit criterion holds.
- The maintainer's literal words outrank every digest, this plan's own
  prose included. When they disagree, report the discrepancy and ask.
- The entries of 12 are in the order given. Where two disagree the later
  one governs, and an entry carries a "Later:" line when it was changed.
  "Applied in:" names the sections of this plan that carry an entry.
- Square brackets inside a literal block of 12 mark the only edits: the
  name of a document that no longer exists, replaced by what it was.
  Trailing white space is dropped. Spelling is the maintainer's.

## 1 Method

### 1.1 APIs before code

- An incomplete code base with correct APIs is worth more than a demo
  rewritten later. Every protocol is emulated as the real protocol from
  the first line: MCP is JSON-RPC 2.0; the provider is spoken to in the
  chat completion shape; TAP is TAP.
- Order of work: design the module here and in API/, write its test
  module, write the module, fix it, stack the next module on it with
  calls going one way, down. No module calls up or sideways.
- Documents iterate until the APIs are right. A stage that would need an
  API rewritten later is not started. "Stop designing things and start
  building the APIs I need from the bottom up": nothing here is a
  prototype or a draft; each stage is the final module behind its API.
- Nothing is added until it is required. A capability a request names
  but no stage needs yet is written in section 10 with its design.

### 1.2 Fail fast

- No error is swallowed, defaulted or retried (rules). A failed server
  handler writes one `error` line and exits 1. In the page,
  `error_overlay` replaces the screen with the message and the call
  stack in a `<pre>` and stops the app. Recovery is a full page reload,
  the tested path; resync is reloading the client, which is normal for
  games.

### 1.3 One synchronization tool

- The task manager is the only synchronization tool. A handler is
  synchronous. A handler that must wait returns a sleep to the task
  manager, which wakes it with the replies as a new task. No promise,
  lock, shared buffer or `Atomics` exists outside the task manager and
  the ports it owns; the audit in 8.6 enforces it.
- In synchronous mode, a debug setting, a queue runs every task it holds
  to completion before it reads the next input from any port, so a run
  is deterministic.

### 1.4 Encode and decode before use

- JSLB's encoder and decoder are proven, in both languages, against the
  vectors of 8.3, before the format carries anything. Stage 1 is that
  proof and nothing else.

### 1.5 Nothing unmotivated

- Nothing concrete exists ahead of the prose that describes it. A
  module, line type, table, tool or setting appears here only with its
  request; the entries of 12 give each request in the maintainer's words
  and name the sections that carry it. Existing code in the checkout is
  current state, not design: the bootstrapper, its page and the wire
  test are reused only where this plan chooses them (rules). The
  DevTools relay of the screenshot tool is chosen by this plan as the
  implementation of `devtools.py`.

### 1.6 Summary of decisions

Each point is a decision that 12 shows being made. The phrases "not
three" and "not one" mark answers that replaced earlier ones (12.2.3.2,
12.2.6.1, 12.3.6.1, 12.3.27.1).

1.6.1 Two threads, not three: UI and AI. sqlite3.wasm and OPFS run in
the AI worker, which owns every database.

1.6.2 Two ttys, not one: the engine tty is Python speaking JSLB in raw
mode; the console tty is ttyd's own dash under xterm.js, optional and
debug only.

1.6.3 The task manager wakes sleeping tasks; handlers never hold a
promise. Forwarding is a decoded object passed unchanged from the
receiving port to the sending port. A synchronous mode drains the queue
before each input.

1.6.4 `verbose` is the one logging namespace; the `log` namespace is
gone. `verbose.call` is where the one external program, the console's
dash, is started.

1.6.5 A Key-Value-Ref is `/$db/$key` or `$key`; a Document-Ref is a
Key-Value-Ref whose key ends in `/$version`. A document is a KV row; the
head of each id is a substrate table. Every JSON object with headers
keeps them at integer keys, discovered by probing from `0`.

1.6.6 The substrate's tables are prefixed, hidden from the AI, and
created on first use in every database. The scripts are the database
administrator; the seeded bootstrap script is the plan for it.

1.6.7 Replication forwards every modifying substrate operation to the
server as it commits; at start the browser's copy is replaced when it
differs; desync reloads; the forwarded operations double as an early
test driver.

1.6.8 Engine databases carry a leading underscore: `_settings`,
`_files`, `_preferences`, `_verbose`. The metaverse's universe table is
the one fixed experience schema.

1.6.9 The page loads `error_overlay`, `utility`, `ui_strings` and
`settings` first, in that order. Settings arrive in `hello` unmodified
and `settings.ts` is hand written, deep frozen outside debug mode;
nothing is generated from settings.json. Debug mode is a setting.

1.6.10 The AI edits, runs and debugs its scripts live in the browser
over MCP; they are KV rows, cached and backed up by replication.

1.6.11 Tests are unittest in both languages with the project's own
`tap.producer` and `tap.consumer`; each browser test line travels to the
server as its own JSLB line.

1.6.12 The provider key comes from the environment, never a file in the
checkout. Images come back as `b64_json` test patterns in the tests.

1.6.13 bootstrap.py can receive a new main loop from the page and serve
it after restart, in debug mode only.

1.6.14 Debug overlays: ctrl-0 toggles the console's xterm.js; ctrl-1 to
ctrl-n show the JSON part of recent JSLB on tty n with blobs as `<blob
"n"=K>` tags.

1.6.15 Timers exist where a wait can fail: the provider request, the
console command, every test rung. The agent sets no game timers.

1.6.16 No version floors or checks. Node runs tsc at build time only.

## 2 Architecture

### 2.1 Processes, threads and ttys

```text
browser tab
  UI  main thread   error_overlay, utility, ui_strings, settings, page:
                    DOM, input, media_db, console view (xterm.js),
                    overlays, permission
  AI  worker        every database (sqlite3.wasm on OPFS); wire; task
                    manager; agent; MCP; scripts; provider over HTTPS
       |                 |
       | tty 1: JSLB     | tty 0: ttyd's own protocol, debug only
       v                 v
ttyd --url-arg, one per machine, one program per WebSocket
  python3 bootstrap.py --root ~/.cache/xsjs           (tty 1, raw mode)
  python3 bootstrap.py --root ~/.cache/xsjs console   (tty 0: dash)
     |
     v  SQLite files under the root
  _settings _files _preferences _verbose metaverse <universe> <world> ...
```

- One Python process per engine connection, no threads, no asyncio: a
  `select` loop on the pty (bootstrap.py runs main_loop.py).
- The front end is TypeScript, the back end Python; the division is
  permanent. SH appears in admin scripts and in the console tty only.
  Neither SH nor Python is exposed to a socket except through the JSLB
  dispatcher's single door, the part of the security architecture
  enforced now; the console tty is the one exception, optional and debug
  only.
- Further ttys are Python, never dash. ttys are numbered: 0 is the
  console, 1 the engine, 2 and up are reserved (10.1).

### 2.2 The two threads

- UI: builds the DOM once, routes the player's text and clicks to the AI
  worker as tasks, paints what `render` names, keeps `media_db`, a
  JavaScript map from media key to decoded image under a byte budget,
  hosts the console view and the overlays, shows permission requests,
  and runs `error_overlay`. It owns no SQLite and never sees a wire.
- AI: owns both WebSockets, the task manager's owner table, sqlite3.wasm
  with the OPFS SAH pool VFS, every database and the cache directory. It
  runs the agent (5.3), the MCP server and client (5.4), the AI's
  scripts (5.6) and replication (6.8). A long query stalls the agent,
  which is accepted: the provider's latency is larger, and the AI can
  raise the verbose level and optimize.
- A third thread, if a hard need arises, reuses `queue.ts` and
  `substrate.ts` unchanged with a new owner table entry.

### 2.3 The ttys

- ttyd runs with `--url-arg`. Its command is `python3 bootstrap.py
  --root <root>`; a connection to `/ws?arg=console` appends `console`.
- tty 1, the engine: bootstrap.py with no role puts its pty in raw mode
  and speaks JSLB. The AI worker opens it at page load. A second engine
  connection on the same root is refused: bootstrap.py takes
  `<root>/engine.lock` with `flock`, and when it cannot, writes `error`
  and exits 1.
- tty 0, the console: bootstrap.py with role `console`, when the setting
  `debug` is true, runs `/bin/dash` through `verbose.call` with a
  scrubbed environment and the root as working directory, and exits with
  its code; when `debug` is false it exits 1 and ttyd closes the
  connection. Its pty stays cooked, so it echoes. The page's console
  module speaks ttyd's own client protocol to it, which is ttyd's dash
  and xterm.js recycled. The user opens it with ctrl-0 or the AI opens
  it with permission. No log-in beyond ttyd's own.
- Sandboxing the dash is a door (10.4).

### 2.4 The first four scripts, settings and debug mode

- The page's bundle begins, in this order, with `error_overlay`,
  `utility`, `ui_strings` and `settings`, then `i18n` and the rest in
  reference order.
- `error_overlay.ts` has one job: it catches `error` and
  `unhandledrejection` on the window, resource load failures in the
  capture phase, and `fault` lines from the AI worker, and replaces the
  screen by `document.write` with a `<pre>` holding the message and the
  call stack, then closes the wire and terminates the worker. It depends
  on nothing.
- `utility.ts` holds the non essential error handling, `error_wrap
  (message, cause)` and `fail_now(message)`, and the single door
  routines the modules below share: `sha256_hex`, `utf8_encode`,
  `utf8_decode`, `base64_decode`, `json_text` and `time_now`.
- `ui_strings.ts` is the strings table. `page_build.py` substitutes the
  text of `i18n/en-US.json` into it unmodified, the one build step the
  one file rule requires, so both languages read the same file.
- `settings.ts` is hand written: `settings_set(value)` once, from
  `hello`, then `settings_get(id)` by id. Outside debug mode the object
  is deep frozen; in debug mode `settings_put(id, value)` changes the
  live value and sends `settings.put`, which rewrites the file in the
  root for the next `hello`. Nothing is built from settings.json.
- `settings.json` at the checkout's top level holds every constant with
  a sane default; 6.9 lists them. Start copies it to the root; the
  server loads it into `_settings` and sends it in `hello` unmodified.
- Debug mode is the setting `debug`, false in a release. The server
  gates `console`, `settings.put`, `source.put`, `system.restart` and
  `verbose.put` on it; the page gates the overlays and `settings_put`.
- Headers use full names in debug mode, short names otherwise.

### 2.5 The page and its build

- ttyd serves one static file, `build/hyperposition-engine.html`.
  Changing it needs a rebuild and a reload. Nothing is fetched at run
  time but media URLs, when the provider returns one (5.7).
- `ts/` holds every script. tsc compiles them with `module` none and
  `outFile` into one classic script in reference order; each file
  defines one frozen object named after its module. Node runs tsc at
  build time and nothing else, ever.
- `page_build.py` merges `html/engine.html` and `html/engine.css`, the
  bundle, sqlite3.wasm as base64 and xterm.js into the one file; the AI
  worker is a Blob URL of the same bundle with its entry chosen by
  `self.name`. The output's SHA-256 is printed.
- `html/test.html` is built the same way with the test modules added.
- Canonical TypeScript error handling: `strict` on, every thrown value
  an `Error` with `cause` when wrapped, no empty catch.
- The AI's scripts are not in the bundle: they are KV values the AI
  edits live (5.6). tsc precompiles only the modules the AI does not
  edit.

### 2.6 Debug overlays

- ctrl-0 toggles the console view: one xterm.js instance in a hidden
  container, shown with its scrollback, colours and features intact.
  Research goal, kept: whether xterm.js can be fed while hidden and keep
  its state; the headless package is the alternative for feeding, chosen
  once by the research result.
- ctrl-n, n from 1, toggles the overlay of tty n: a `<pre>` holding the
  rendered form (3.11) of the last `verbose_ring` lines in both
  directions, newest last. These overlays are read only and have no
  console features.
- In debug mode with `verbose_forward` on, the same rendering of the
  wire traffic and the page's `console.*` output goes to the server as
  `verbose.put`, so `_verbose` holds the page's view.

## 3 JSLB wire format

### 3.1 Framing

```text
message := line blob*
line    := json-object CR
```

- `json-object` is one JSON object in UTF-8 with no whitespace outside
  strings. The encoder emits no CR and JSON forbids a raw CR inside a
  string, so the first CR, byte 0x0D, ends the line.
- LF is an ordinary byte with no meaning, as every byte other than CR
  outside a string.
- The blobs follow the CR at once, in header order, each exactly `s`
  bytes, nothing between.
- A reader has two states: bytes to a CR, then known byte counts.

### 3.2 Headers at integer keys

- Every JSON object that carries headers, a JSLB line or a document,
  keeps them at the decimal integer keys `0`, `1`, ... and its
  payload at every other key. `0` is the object's own header. The
  headers are discovered by probing the integers from 0 until one is
  missing, so a reference to a header is an integer.
- In a line, `1` to `"b"` are blob headers. In a document, `1` on
  are reference strings (6.4).

### 3.3 Line header, key `0`

- `t` `type`: string, required. The handler name: lowercase words joined
  by `_`, namespaces by `.`.
- `v` `version`: integer, default 0.
- `i` `id`: integer from 1, present when a reply is expected.
- `r` `reply`: integer, the peer's `i` this line answers.
- `k` `key`: string, the key the line is about, when it is about one.
- `b` `blobs`: integer, default 0. It equals the probe count of 3.2; a
  difference is a hard error.

### 3.4 Blob headers, keys `1` to `"b"`

- `s` `size`: integer, required. `k` `key`: where the handler stores
  the blob, when it does. `d` `data`: never serialized; in memory the
  bytes, or for a streamed blob the path of its cache file (3.8).
- Any other field is the handler's. There is no blob type registry: a
  blob is opaque bytes to JSLB and to the dispatcher.

### 3.5 Names and defaults

- Short names or full names in all headers of a line; both in one line
  is a hard error. Full names are the debug mode form.
- A field at its default is not written.
- The decoder returns headers as sent plus `d`; `field_get(header,
  "type")` resolves short or full name and the default.

### 3.6 Values

- Numbers are IEEE doubles; integers lie within plus or minus 2^53;
  the Python encoder refuses larger ints, NaN and infinities.
- Strings are Unicode; the line is UTF-8 under the strict decoder on
  both sides. Duplicate keys take the last value; encoders never produce
  them.

### 3.7 Hard errors

- No `0`, no `t`, `b` not matching the headers present, a gap in
  `1` to `"b"`, a non-integer or negative `s`, a payload key that is a
  decimal integer string, both name forms, an unknown field in the line
  header.
- A line over `line_max` or a blob over `blob_max`, refused before the
  bytes are buffered.
- The decoder raises on the first error and the port that fed it
  closes. No resynchronization on a byte stream.

### 3.8 Streaming blobs

- A blob of `s` at most `overflow_bytes` is collected in memory. A
  larger blob is written to a new file in the cache directory as it
  arrives, hashed on the way, and `d` is that path; the handler moves or
  links it. Memory per connection is bounded by `line_max` plus
  `overflow_bytes`.
- The encoder yields the JSON bytes, then each `d` as is, bytes or
  file. It never copies blob bytes.

### 3.9 Request, reply, push

- A line with `i` gets exactly one line with `r` equal to it, from the
  peer, on the same port; its `t` is the request's `t` or `error`. A
  line without `i` is a notification.
- Ids restart at 1 per port per process lifetime. An unknown `r` is a
  hard error.
- One port is one FIFO each way. A handler runs to completion before
  the next line on that port is dispatched (4.2).

### 3.10 Transport and flow control

- ttyd frames: `'0' + bytes` each way, `'1'` title and `'2'`
  preferences first. `wire.ts` strips and adds the `'0'`.
- The server puts its pty in raw mode with `tty.setraw` before writing
  anything. The client sends nothing until `hello` arrives.
- ttyd's 5 s ping is answered by the browser's network stack.
- ttyd stops reading the pty after each 64 KiB read until it is written
  to the socket; client to pty input goes to libuv's unbounded write
  queue; the one option is `--srv-buf-size`, the receive chunk size.
  Decision: ttyd runs with `--srv-buf-size 1048576`; `chunk_bytes` is 1
  MiB; `wire.ts` waits for `bufferedAmount` under one chunk before the
  next; the server streams big blobs to the cache file so libuv's queue
  stays short. ttyd's resident size during a 128 MiB upload is measured
  in stage 2; a credit line is added only if the measurement demands it
  (10.11).
- ttyd may end a connection without delivering a program's last output
  (Project Direction 1.1). The page treats a close with no `error` line
  as the fault "connection closed with code N and no error line"; the
  wire test times each rung and reports a lone loss with the ttyd
  version, never retrying it.

### 3.11 Debug rendering

- A line is rendered for a human as its JSON text followed by one `<blob
  "n"=K>` tag per blob, K the header key from 1. The overlays (2.6),
  `verbose.put` of wire traffic and the transcripts in DATA/ use this
  form.

## 4 Communication patterns

### 4.1 Lanes and ports

```text
wire     AI worker  <->  server        bytes over tty 1
console  AI worker  <->  ttyd's dash   ttyd's protocol over tty 0
ui-ai    UI thread  <->  AI worker     structured clone, buffers moved
mcp      agent      <->  MCP server    JSON-RPC objects, local port
http     agent      <->  provider      HTTPS, one request per line
```

- Every message on every lane is one JSLB object, except the console
  tty's own protocol. A port is anything with `line_post(line)` and
  `line_receive(fn)`: local, thread (`MessagePort`), wire, and http,
  which turns `http.request` into a `fetch` with a timer of
  `timeout_seconds` and posts the response, or the timeout, as the reply
  line. The console lane carries ttyd's protocol bytes wrapped as
  `console.output` and `console.input` lines on the ui-ai lane, so that
  the AI worker is the only owner of sockets.
- Code that submits a task never knows which port carries it.

### 4.2 The task manager

- `TaskQueue` per thread. It dispatches one line at a time; a handler
  runs to completion. The owner table maps a type prefix to the thread
  that handles it; a line whose owner is another thread is posted to
  that thread's port unchanged (4.3).
- A handler returns one of three things: a reply line, when the task had
  `i`; nothing, for a notification; or a sleep. A sleep names the ids of
  the requests the handler submitted and the type of the task to wake
  with: `task_sleep(state, wait_ids, then_type)`. When every reply in
  `wait_ids` has arrived the queue enqueues a line of `then_type` whose
  payload is `state` and the replies. A task can therefore re-enqueue
  itself in a different form at a different destination any number of
  times.
- Locking: every database is on the AI thread and one task runs at a
  time, so a running task holds every database. A sleeping task holds
  nothing: `transaction_run` is the only way to touch a database and it
  cannot span a return, so the handler has committed before it sleeps.
  That is the task manager's locking scheme.
- Synchronous mode, the setting `queue_synchronous`, debug only: before
  the queue reads the next line from any port it runs every task it
  holds, including woken tasks and tasks it posted to itself, to
  completion; a sleep that waits on another thread is the only thing
  that lets an input through. Runs are then deterministic.
- The queue handles sleeping tasks and an empty queue. It logs every
  submit, dispatch, sleep, wake and reply through `verbose` at level 2,
  and no other information is needed to reconstruct the thread's
  timeline.
- Blob buffers are transferred, never copied; after submit the caller's
  `d` is detached (owned data array).

### 4.3 Forwarding

- A line arriving on one port whose owner is not this thread is passed
  as the decoded object, unchanged, to the port of its owner, which
  encodes it again. The owner table on the AI thread maps `verbose.` to
  `server`, so a `verbose.put` from the UI reaches the server through
  the AI worker with nothing added; the embedded forwarding instruction
  is the type itself. Replication (6.8) is this mechanism: a modifying
  operation committed in the browser is the same line forwarded to the
  server. Explicit route headers are a door (10.10).

### 4.4 Connection lifecycle

- Open: `error_overlay`, `utility`, `ui_strings`, `settings`, then
  `page.ts` creates the AI worker from the bundle. The worker fetches
  `/token`, opens `/ws` with subprotocol `tty`, sends ttyd's first
  message, skips title and preferences, waits for `hello`.
- `hello` is the server's request with `i` 1: `bootstrap`, `sha256`,
  `pid`, `root`, `settings`, `seq` per server database and
  `provider_key`. The worker posts `settings.set` to the UI, answers
  with an empty reply, then posts `boot.hello`.
- Then, as tasks: for each engine database and the metaverse, compare
  `seq` and replace the browser's file from the server where they
  differ (6.8); read `/metaverse/world`, then `/$world/scene`; fetch
  the referenced media the browser lacks; `render`.
- Close: the worker closes the WebSocket with 1000; ttyd sends SIGHUP
  and the server exits. There is no `quit` and no `cancel`; a runaway is
  ended by closing.

### 4.5 Errors and recovery

- Server: a handler that raises produces one `error` line with `r` when
  the request had `i`, `message` and `stack`, written and flushed before
  exit 1; the realistic effort to get the message out.
- Page: any fault reaches `error_overlay`, which shows it and stops the
  app (2.4). The screen offers Reload. Reload is `location.reload()`;
  the new page replicates from the server, which is the source of truth.
  Nothing in flight is retried.
- A close without an `error` line, a desync (6.8) and a timer expiring
  (1.6.15) are faults like any other and end in Reload.
- Project Direction 1.3 of the rules, written for the old bootstrapper's
  page, reads "never retry by reloading the page". The new design
  reloads by decision; the sentence is the maintainer's.

### 4.6 Permission

- A tool marked `permit` is not run until the UI shows the request with
  Accept, Deny and Always Allow below it. Accept runs it once; Deny
  returns an error to the model; Always Allow lasts the tab and is not
  stored.
- The tool submits `permit.ask` to the UI and sleeps. The UI's handler
  shows the buttons, submits `dom.choice` to the DOM port of `page.ts`,
  which answers when a button is clicked, and sleeps; its wake replies
  to `permit.ask` with the choice, which wakes the tool. A DOM listener
  is an event, not a promise, so `page.ts` needs no exception in 8.6.

### 4.7 The console lane

- `console.open` from the UI makes the AI worker open tty 0 and relay:
  output arrives as `console.output` with one blob, input goes as
  `console.input` with one blob, both the raw bytes of ttyd's protocol
  including its first JSON message; `console.close` closes the socket;
  `console.exit` is pushed when ttyd closes it. The server side is ttyd
  and dash; no Python line type exists for the console.
- The AI reaches it only through the `console_run` tool after the
  permission flow. `console_run` posts the text and a newline as
  `console.input` to the console port, submits `console.read` to it and
  sleeps; the port answers with the output once the prompt returns or
  `timeout_seconds` expires, a timer.
- The player's text and clicks are notifications a DOM listener posts
  to the UI's queue as `ui.input`; the handler submits `ai.say` or
  `ai.click` to the AI worker and sleeps with `ui.turn_end`, which
  enables the input again.

## 5 The AI

### 5.1 Not MVC

- The model of this system is the set of databases on one thread.
  Threads that talk directly and keep private storage, `media_db` for
  one, are part of the design. The phrase "the AI needs MVC" is read as
  the tool layer of 5.5 and the stubs of 8.5.

### 5.2 The generic provider protocol

- The chat completion protocol: `POST {base_url}/chat/completions` with
  `model`, `messages`, `tools`, `tool_choice`; `choices[0].message` with
  `content`, `tool_calls` and `finish_reason`. Images: `POST
  {base_url}/images/generations` with `response_format` `b64_json`. xAI
  is the first and only provider tested; the same shape for others is a
  door.
- `provider.ts` is the one door: `chat_request(messages, tools)` and
  `image_request(prompt)` each build one `http.request` line with the
  key in `Authorization`; the caller submits it and sleeps. The key is
  read by the server from the environment variable `XSJS_PROVIDER_KEY`
  and sent in `hello`; it lives in the AI worker's memory only.
- `provider_script.ts` answers the same lines with no network: a script
  is a table of nodes; the player's message is one integer that selects
  the node's reply, which may carry tool calls; a tool result advances
  to the node the reply names. Image requests return a low resolution
  PNG test pattern with hard pixel edges drawn by the stub. Every
  automated test drives the engine this way; no AI runs in tests.

### 5.3 The agent loop

- One turn is a chain of tasks. `ai.say {text}` or `ai.click {x, y}`
  from the UI: the handler appends the turn (6.6), builds the provider
  request, submits it and sleeps with `ai.model_reply`.
  `ai.model_reply`: stores the assistant turn; for each tool call
  submits an MCP `tools/call`; a tool that must wait (an image, a
  permit, the console) sleeps in turn; when every tool result is in,
  the next provider request is submitted; a reply with no tool calls
  ends the turn with the reply to the original `ai.say`. The queue log
  is the transcript of the turn (4.2).
- The system prompt is the analyst's prompt document in the metaverse,
  then the current universe's prompt document when the scripts have made
  one.
- Time stops: nothing runs without a player task; the agent sets no game
  timers.

### 5.4 MCP

- `mcp.ts` and `mcp.py` implement JSON-RPC 2.0 and the MCP methods
  `initialize`, `notifications/initialized`, `ping`, `tools/list` and
  `tools/call`, revision `2025-06-18` pinned as a constant, any further
  part of it emulated when a tool needs it. Both are transport agnostic:
  `message_handle(object)` returns the response or nothing.
- Transports: a local port in the AI worker; the JSLB line `mcp` whose
  payload is the JSON-RPC message; `mcp_stdio.py`, newline delimited on
  stdin and stdout, so an external agent drives a server directly.
- The client sees browser tools and server tools in one flat list
  under `browser.` and `server.` prefixes.

### 5.5 Tools

Browser, in the AI worker; each names its request:

- `sql_run {db, statements}`: the single door to SQL; DDL allowed, the
  AI is the database administrator. The substrate's own tables and
  `_settings` refuse writes.
- `db_create {db}`, `db_drop {db}`: the AI adds and removes databases.
- `kv_get {ref}`, `kv_put {ref, text}`, `kv_delete {ref}`, `kv_list {db,
  prefix}`: the KV accessor on Key-Value-Refs.
- `doc_get {ref}`, `doc_put {db, id, body}`, `doc_head {db, id}`.
- `script_run {name, args}`, `script_debug {name, args}` (5.6). A script
  is edited with `kv_put` on `/_files/script/<name>.js`.
- `image_make {prompt, key}`, `render {image, subtitle}`.
- `console_run {text, timeout_seconds}`, permit, debug.
- `verbose_level {level}`, `verbose_tail {thread, count}`.

Server, in Python:

- `source_put {name}`, permit, debug, and `system_restart {main_loop}`,
  permit, debug.

API/mcp/tools.json is the list as `tools/list` returns it.

### 5.6 Scripts: the AI's JavaScript and the database administration

- The AI's scripts are KV values in `_files` under `script/<name>.js`,
  on both sides by replication, which is the immediate backup to both
  databases. They are editable over MCP.
- `script_run {name, args}` runs the text in the AI worker as a task:
  `new Function("engine", "args", text)` with `engine` the frozen object
  of the substrate, `verbose` and `i18n` APIs. It returns the value, or
  the exception with its stack, and the verbose lines the run emitted.
  `script_debug {name, args}` is the same run at verbose level 2, which
  traces every substrate call the script makes through the single door.
  A simulation step is such a script run by a tool call or a turn.
  Nothing is sent to the server for compilation.
- The scripts are the database administrator. The server seeds one,
  `script/bootstrap.js`, the plan for the administration: it creates a
  universe database and its `world` table, a world database and its
  `region` table, region databases, writes the `universe` row and the
  Key-Value-Refs of 6.6, and enters a scene. The AI edits it like any
  script. The engine seeds nothing in a universe, world or region
  database.

### 5.7 Images

- `image_make` submits an image request and sleeps. The reply's
  `b64_json` is decoded in the AI worker, written to `_files` under the
  key, which replicates it to the server at once, and posted to the UI
  as `media.store` with the buffer transferred, into `media_db`. A URL
  answer is handed to the UI as `media.fetch`, which downloads it and
  replies with the bytes. Server side fetching is a required door
  (10.5).

## 6 Data

### 6.1 Engines and connections

- Server: Python's `sqlite3` on the system library. Browser:
  sqlite3.wasm pinned by version and SHA-256 with the OPFS SAH pool VFS
  in the AI worker. No version floors and no version checks.
- One connection per database. Server pragmas: `foreign_keys=ON`,
  `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`.
- A database name is a C identifier. Its file is `<name>.sqlite` under
  the root.

### 6.2 Databases

```text
name          holds                                       schema
_settings     settings.json loaded, key to JSON text       immutable
_preferences  the user's preferences, key to JSON text     fixed
_files        media, scripts and blobs by key              fixed
_verbose      the server's verbose lines (server only)     fixed
metaverse     the universe table; the hyperposition        universe fixed
<universe>    the experience's tables                      the scripts'
<world>       the world's tables, one experience state     the scripts'
<region>      the region's entities and scenes             the scripts'
```

- The three browser databases, settings, preferences and files, are
  these, on the AI thread, named with a leading underscore. `_settings`
  is immutable; `_preferences` and `_files` have an immutable schema.
- The substrate's tables (6.3) are created on first use in every
  database the substrate opens, so a Key-Value-Ref resolves in any
  database and a blob is stored in a given database. They are the
  substrate's, prefixed `_`, and the AI never needs to see them.
- The metaverse adds the `universe` table, the one fixed experience
  schema. Every other table is the scripts'.

### 6.3 The substrate's tables

```sql
CREATE TABLE _meta (
    name  TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID, STRICT;

CREATE TABLE _kv (
    key    TEXT    PRIMARY KEY,
    size   INTEGER NOT NULL,
    sha256 BLOB    NOT NULL,
    data   BLOB
) WITHOUT ROWID, STRICT;

CREATE TABLE _head (
    id      TEXT    PRIMARY KEY,
    version INTEGER NOT NULL
) WITHOUT ROWID, STRICT;

CREATE TABLE _turn (
    scene   TEXT    NOT NULL,
    n       INTEGER NOT NULL,
    role    TEXT    NOT NULL,
    content TEXT    NOT NULL CHECK (json_valid(content)),
    PRIMARY KEY (scene, n)
) WITHOUT ROWID, STRICT;
```

- `_meta` holds `seq`, incremented in the same transaction as every
  modifying operation, and `schema`. `_kv` is the KV accessor; `sha256`
  names the overflow file, detects an unchanged write and lets
  replication skip bytes the other side has; `data` is NULL when the
  value is in the cache (6.5). No type column: what a value is, is the
  key owner's business. `_head` is the current version of each document
  id (6.4). `_turn` is the turn table.
- There is no per row `seq` and no tombstone table: replication is by
  forwarded operations, not by row log (6.8).

### 6.4 Key-Value-Refs, Document-Refs and documents

- A Key-Value-Ref names a KV row: `/$db/$key` is an external reference,
  `$key` an internal one, inside the database at hand. `$db` is a C
  identifier; `$key` is any non-empty UTF-8 text, which may contain `/`.
  Scripts keep settings that are not documents in such rows, as
  `/metaverse/world`.
- A Document-Ref is a Key-Value-Ref whose key is `$id/$version`:
  `/$db/$id/$version` external, `$id/$version` internal. `$id` is any
  non-empty UTF-8 text, which may contain `/`; `$version` is an integer
  literal, the last segment. Nothing else about the shape of `$id` is
  fixed.
- A document is the KV row named by its Document-Ref, holding JSON.
  `doc_put(db, id, body)` writes version `_head` plus one and moves the
  head in the same transaction; `doc_head(db, id)` reads `_head`;
  `doc_get(ref)` is `kv_get` with a JSON decode. A written version never
  changes; history is the set of versions. This is the design with the
  best performance: one table for documents, blobs and settings, so one
  overflow path and one replication path, and a head lookup by primary
  key instead of a prefix scan whose string order would misorder
  versions.
- A document's headers follow 3.2: `0` is the document header, `t` the
  document type and `v` its format version, defaults omitted; `1` on
  are reference strings, Key-Value-Refs and Document-Refs, iterable by
  probing; `{"$ref": n}` anywhere in the body names header n.
  `doc_encode(normal)` moves every reference string into the headers and
  leaves `{"$ref": n}` behind, sharing equal strings;
  `doc_decode(encoded)` puts them back. The round trip is identical. The
  engine prefetches from the headers without knowing the schema;
  `kv_get` of a reference the browser lacks asks the server with
  `kv.get` and stores the answer first.
- The engine's one document contract is the scene: type `scene`, with
  `subtitle` text and, when there is one, `image` a reference to a
  media row. The hyperposition is `/metaverse/hyperposition/1`.

### 6.5 Overflow to the cache

- A KV value over `overflow_bytes`, 128 KiB, lives in
  `<root>/cache/<sha256 hex>` with `data` NULL; the browser's cache is
  an OPFS directory in the AI worker. File first, then the row; a crash
  between leaves an unreferenced file that `kv_check` removes. The
  streaming decoder's file is renamed into place, no second copy.

### 6.6 The metaverse, players, worlds, scenes and turns

- `metaverse.universe(name TEXT PRIMARY KEY, title TEXT NOT NULL, player
  TEXT NOT NULL, world TEXT NOT NULL)` is the one fixed table: which
  player is in which universe and which of its worlds. Several players
  in several universes at once; by default there is one player.
- The engine reads two Key-Value-Refs: `/metaverse/player`, the player
  in use, and `/metaverse/world`, the database holding the current
  world; then the Document-Ref in `/$world/scene` is the scene it
  renders (the world holds the pointer to the current scene). The seed
  sets `player` to `player`, `world` to `metaverse` and
  `/metaverse/scene` to `/metaverse/hyperposition/1`.
- The bootstrap script (5.6) makes the rest: a universe database with a
  `world` table, a world database with a `region` table, region
  databases, each name a C identifier; defaults `current_universe` for
  simulations in the present day and `world`. The schema of those tables
  is mutable and the seed goes no further.
- Regions are disjoint entities; a scene is a location inside one. The
  hyperposition creates a new scene document for each conversation.
- Turns are `_turn` rows in the database of the scene, keyed by the
  scene's Document-Ref, each one provider message. `turn_compact(scene)`
  in the substrate replaces turns 1 to N with one summary row when the
  estimate exceeds `turn_compact_tokens`; a heuristic baked into the
  wrapper, not an AI script.

### 6.7 Media tiers

```text
tier              where       keeps                        evicts
media_db          UI thread   decoded images in use        by budget
_files (browser)  AI worker   the current scene's refs     on leave
_files (server)   server      everything ever stored       never, v0
```

- Sparingly in the browser, aggressively on the server. Budgets are
  settings.

### 6.8 Replication

- Always over JSLB, as it happens, from the modifier to the server. The
  unit is the substrate operation: `kv_put`, `kv_delete`, `doc_put`,
  `turn_append`, `turn_compact`, `db_create`, `db_drop` and every
  modifying `sql_run` commit in the browser is forwarded as the same
  line (`kv.put` with its blob, `sql.run`, ...) to the server right
  after the transaction commits, in order, one in flight per database.
  Each carries `since`, the browser's `seq` before the operation; the
  server refuses it with `error` when `since` is not its own `seq`, runs
  the same operation otherwise, and replies with its new `seq`. The
  copies are deterministic as long as the statements are.
- This is inside the substrate, not ad hoc: `substrate.ts` emits the
  lines after commit and `substrate.py` applies them. The first unit
  test replicates a string to string table, created and filled through
  `sql_run`, by modifications submitted as tasks from the UI thread and
  from the AI thread, and compares the server's copy.
- The forwarded operations are a test driver: a recorded sequence of
  them replayed into `test_wire.py` drives the server substrate before
  the page exists, and replayed into the browser drives the page without
  a provider.
- Direction: during play the browser writes and the server backs up;
  nothing is pushed from the server while a tab is open (one way). The
  server is the source of truth.
- Start: `hello` carries `seq` per database. Where the browser's `seq`
  differs, its file is invalidated and replaced by the server's:
  `db.snapshot` yields `Connection.serialize` bytes as one blob and
  `db.restore` writes a temp file and renames it.
- Desync: a refused push, or a reply whose `seq` is not the browser's,
  is a fault; the page reloads and the reload replaces the file. That
  path is unit tested in stage 6, early. Content divergence with equal
  `seq` is a door (10.9).
- `_verbose` is server only. `_settings` is written by the server from
  the file and never by the browser.

### 6.9 Settings

- `settings.json` holds constants only, each with a sane default:
  `debug`, `queue_synchronous`, `verbose_level`, `verbose_ring`,
  `verbose_forward`, `line_max`, `blob_max`, `overflow_bytes`,
  `chunk_bytes`, `srv_buf_size`, `media_db_bytes`,
  `files_browser_bytes`, `turn_compact_tokens`, `long_task_ms`, and
  `provider` with `scripted`, `base_url`, `chat_model`, `image_model`
  and `timeout_seconds`. Never a password or a key. A constant no module
  reads is not there.
- The server loads it into `_settings` at start, so the AI can query it,
  and sends it in `hello` (2.4). `settings.put` in debug mode rewrites
  the file; the server rereads it at the next `hello`.

## 7 Modules

### 7.1 Naming

- Functions and classes carry two English names; modules and test
  modules are the exception; the maintainer's own identifiers override
  the rule, as `verbose.log` does (rules).
- Constants are `_UPPER_NAME` at the top of each Python file; TypeScript
  has one frozen `constants` object per module.
- `i18n("name", ...args)` in both languages; `from i18n import i18n` is
  the one `from` exception; strings live in `i18n/en-US.json`, read by
  Python and substituted into `ui_strings.ts` by the build, checked for
  the same names by stage 0; PowerShell keeps its `i18n.psd1`.

### 7.2 Python, bottom up

Each has `test_<module>.py` beside it holding `unittest.TestCase`
classes. API/python holds the stubs.

- `i18n.py`: raises on a missing name or a placeholder count that
  differs from the argument count.
- `tap/producer.py`: a `unittest` runner writing TAP with one plan per
  run and one indented subtest block per module. `tap/consumer.py`:
  takes a document, returns stats: plan, pass, fail, skip, and whether
  the stream is well formed.
- `jslb.py`: `Object`, `header_make`, `blob_make`, `line_make`,
  `field_get`, `headers_of`, `payload_of`, `line_encode`,
  `LineDecoder` with `bytes_feed`, `line_render` (3.11), `WireError`.
- `verbose.py`: `level_set`, `log(level, text)`, `history_get(count)`,
  `call(level, argv)`, the one place an external program is started, at
  level 0 quietly with output passed through, at level 1 with Markdown
  formatted progress, at level 2 raw with verbose flags passed on. Lines
  go to `_verbose` and the ring.
- `settings.py`: `settings_load(path)`, `settings_check(settings)`.
- `substrate.py`: `Store` with `db_open`, `db_close`, `db_list`,
  `db_create`, `db_drop`, `ref_split`, `kv_get`, `kv_put`, `kv_delete`,
  `kv_list`, `kv_check`, `doc_get`, `doc_put`, `doc_head`, `doc_encode`,
  `doc_decode`, `turn_append`, `turn_list`, `turn_compact`, `sql_run`,
  `db_snapshot`, `db_restore`, `operation_apply`, `transaction_run`;
  `schema_apply(connection)`.
- `dispatch.py`: `handler_register`, `line_dispatch`, `reply_make`,
  `error_make`, `id_next`; calls `fn(line, **payload)`.
- `mcp.py`: `Server` with `tool_register`, `message_handle`; `Client`
  with `initialize_send`, `tools_list`, `tool_call`.
- `mcp_stdio.py`: the stdio transport around `mcp.Server`.
- `engine_kv.py`, `engine_doc.py`, `engine_db.py`, `engine_turn.py`,
  `engine_sql.py`, `engine_verbose.py`, `engine_tap.py`,
  `engine_mcp.py`, `engine_system.py`: the handlers of
  API/ts/lines.d.ts, one module per namespace.
- `main_loop.py`: `loop_run(read_fd, write_fd, root)`, the select loop
  and the stock dispatcher; replaceable.
- `bootstrap.py`: the platform services: arguments and role, the lock,
  raw mode, `hello`, choosing and loading the main loop file, restart,
  the console. Immutable outside debug mode.
- `page_build.py`, `third_party_fetch.py` (urllib and SHA-256 into
  `third_party/`), `devtools.py` (8.2), `test_all.py`, `test_wire.py`,
  `test_browser.py`, `test_posix.py` with the audit of 8.6.

### 7.3 TypeScript, bottom up

Each is `ts/<name>.ts` with `ts/test_<name>.ts`. API/ts holds the
declarations.

- `error_overlay.ts`, `utility.ts`, `ui_strings.ts`, `settings.ts`,
  `i18n.ts`, `tap.ts` (the producer), `unittest.ts` (`TestCase`,
  `TestSuite`, `TestLoader`, the asserts used; output identical to
  Python's), `verbose.ts`, `jslb.ts`, `dispatch.ts`, `queue.ts`,
  `wire.ts`, `http.ts`.
- `substrate.ts`: `Store` over sqlite3.wasm, the same API as Python plus
  the emitting side of replication (6.8).
- `mcp.ts`, `provider.ts`, `provider_script.ts`, `agent.ts`,
  `tools_browser.ts`, `script.ts` (5.6).
- `media.ts`, `console_view.ts` (xterm.js and ttyd's client protocol),
  `overlay.ts` (2.6), `page.ts` with the DOM port, `worker_ai.ts`,
  `boot.ts`.

### 7.4 Dependency graph

```text
PY  i18n  tap/producer  tap/consumer
      |
    jslb  verbose  settings  substrate  mcp
       \     |        |         |        |
        dispatch -----+---------+--------+
            |
    engine_kv engine_doc engine_db engine_turn engine_sql
    engine_verbose engine_tap engine_mcp engine_system
            |
        main_loop
            |
        bootstrap          mcp_stdio

TS  error_overlay  utility  ui_strings  settings  i18n  tap  unittest
      |
    verbose  jslb   substrate(sqlite3.wasm)   provider  provider_script
      |       |          |                        |
    dispatch  |          |          agent --- mcp --- tools_browser
      |       |          |            |                   |
    queue --- wire --- http ----------+               script
      |
    media  console_view  overlay
      \       |            /
       page         worker_ai
            \        /
              boot  ->  page_build.py
```

No arrow points up. A test module imports only its module and the test
harness.

### 7.5 Admin scripts

- The Windows scripts change in one function: the ttyd options gain
  `--url-arg`, `--srv-buf-size 1048576`, the index file name, and the
  root argument; nothing about debug, which is a setting. The start
  script passes `XSJS_PROVIDER_KEY` from the user's environment into
  ttyd's.
- `archive.sh` and `clean.sh` are not part of the project.
- `.sh` parallels, a Dockerfile and `--container` are doors (10.3).

## 8 Testing

### 8.1 The runner and the stream

- unittest in both languages with identical output text. One TAP plan
  per language per run; each module's suite is one subtest block
  indented four spaces with its own plan, then a parent `ok N -
  <module>` line.
- Every stream is checked by `tap.consumer` on the server: `test_all.py`
  parses its own output; the page sends each TAP line as its own
  `tap.line` as it is produced, and further debug lines ad hoc, and the
  server appends each to `<root>/tap/<language>.tap` unbuffered, so a
  hang leaves the lines before it on disk.
- `failfast`: the first `not ok` stops the stream with the traceback as
  diagnostics. Side effects between tests are banned; name order is
  fine.
- `test.html` shows the stream with every failed line highlighted whole.

### 8.2 Runners

- `python3 python/test_all.py`: the Python suites in dependency order,
  then `test_wire.py`.
- `python3 python/test_browser.py`: builds `test.html`, serves it
  through Linux ttyd, runs the TypeScript suites in headless Chrome,
  reads the `tap.line` stream from the file of 8.1, checks it with the
  consumer, saves a PNG. The one JavaScript runner is a browser.
  `devtools.py` is `page_open(url)`, `script_evaluate(text)`,
  `console_follow(fn)`, `screenshot_save(path)`, `page_close()` over the
  DevTools protocol, implemented by the relay now inside
  `xsjs_screenshot.py`, split out.
- `python3 python/test_posix.py` keeps its role for every whitelisted
  file and gains the audit of 8.6.
- Every rung and every browser test has a timer; a timer expiring is a
  failure that names the rung.

### 8.3 Cross-language vectors

- `python/vectors/*.jslb` from `jslb.py`: empty payloads, every header
  field, both name forms, zero to three blobs, blob bytes holding CR,
  LF, 0x03, 0x04, 0x13 and invalid UTF-8, each hard error, and the
  rendered form of 3.11. Both decoders read every vector, compare to the
  `*.json` sidecar, re-encode, and read the result whole, by single
  bytes, and split at every offset.

### 8.4 The UI thread stress test

- A long task observer on the UI thread during a 16 MiB `kv.put` and
  `kv.get`, a 128 MiB upload and a scripted turn with an image requires
  no task over `long_task_ms`, 5 ms, a soft target reported as a
  measurement, and no synchronous I/O on the main thread, a hard failure
  found by tracing.

### 8.5 Stubs

- The integration tests drive every operation of 6.6 through the integer
  based scripted provider and the seeded bootstrap script: a universe, a
  world and a region created, a typed table created by DDL, a scene
  written and entered, an image made, a render, a turn stored,
  compaction, a script put, run and debugged, the baseline the AI will
  be asked for.

### 8.6 The synchronization audit

- `test_posix.py` fails on `await`, `.then(`, `new Promise`, `Atomics`
  or `SharedArrayBuffer` in any `ts/*.ts` other than `queue.ts`,
  `wire.ts`, `http.ts` and `media.ts`, the four modules that turn an
  event of the platform, a socket, a response, an image decoded, into a
  reply line.

### 8.7 Stages

Each stage names what is built, what its tests prove, what a person
surveys, and the exit criterion. A stage starts only when the previous
one's exit criterion holds.

8.7.1 Stage 0, the harness: `third_party_fetch.py`, `tap/`, `i18n`,
`test_all.py`, `tap.ts`, `unittest.ts`, `devtools.py`,
`test_browser.py`, `page_build.py` for the test page, tsc in the build,
`error_overlay.ts`, `utility.ts`, `ui_strings.ts`, `settings.ts`.
Proves one passing, one failing, one raising and one skipped method
yield identical TAP in both languages as one subtest block, accepted by
the consumer; `failfast`; `i18n` raises in both; a thrown error in the
test page ends in the `<pre>` screen; `settings_get` of an unknown id
throws and the frozen object refuses a write. Survey: the TAP text; the
PNG. Exit: both runners exit 0 on the real suites and 1 on the nested
class.

8.7.2 Stage 1, JSLB: `jslb.py`, `jslb.ts`, the vectors, streaming over
`overflow_bytes`, header probing, rendering. Exit: both suites pass;
each reads all the vectors of the other.

8.7.3 Stage 2, the raw wire: `bootstrap.py` with raw mode, the lock and
`hello`, an `echo` handler; `test_wire.py` rungs `hello`, `echo`, `echo
1 MiB with control bytes`, `echo 128 MiB` with ttyd's resident size
printed, `second connection refused`, `ttyd killed`, and the last line
regression of Project Direction 1.1 (the old test that keys on the last
line of a process that exits right after printing it; a lone loss there
is a ttyd fault, reported with the ttyd version and not retried) kept as
it is, each rung under a timer. Exit: all rungs pass twice.

8.7.4 Stage 3, the server substrate: `substrate.py`, `settings.py`,
`verbose.py`. Proves the tables created on first use in a new database,
KV on both ref forms, documents, heads, the document round trip of 6.4,
`seq` across reopen, overflow at exactly `overflow_bytes`, snapshot and
restore, a `SIGKILL` between file and row, `kv_check`,
`operation_apply` of a recorded sequence, `turn_compact`, a write to a
`_` table or to `_settings` refused. Exit: passes under `python3 -X
dev`.

8.7.5 Stage 4, dispatch and the main loop: `dispatch.py`, `engine_*`,
`main_loop.py`, `mcp.py`, `mcp_stdio.py`, the main loop download and
restart. Proves through `test_wire.py` and a stdio MCP client written
in the test: `kv.put` and `kv.get` byte identical, `doc.put` and
`doc.head`, `verbose.tail`, `tools/list` and `tools/call` over stdio
and over the `mcp` line, an unknown type giving `error` then exit 1,
`system.restart` serving a second main loop after `source.put` in debug
mode and the same refused without it, a recorded operation sequence
replayed over the wire (6.8). Exit: rungs pass; pyright clean.

8.7.6 Stage 5, the page reaches the server: `dispatch.ts`, `queue.ts`
with sleep, wake and synchronous mode, `wire.ts`, `http.ts` against a
local stub, `verbose.ts`, `overlay.ts`, `worker_ai.ts` without
databases, `page.ts` showing `hello`. Proves the hello relay, a 16 MiB
round trip equal by SHA-256, a `verbose.put` forwarded from the UI
through the AI worker to the server unchanged, a sleeping task woken by
two replies in either order, the same run identical twice in
synchronous mode, the stress test of 8.4, a fault ending in the `<pre>`
screen and Reload, a close without an `error` line reported as such.
Survey: a PNG with ctrl-1 open. Exit: `test_browser.py` exits 0.

8.7.7 Stage 6, the browser substrate and replication: `substrate.ts` in
the AI worker, the forwarded operations both sides. Proves the stage 3
suite ported, a second load finding the rows, overflow files in OPFS,
the string to string table replicated from the UI and from the AI (6.8),
the start replacement of a differing file, the desync reload, a recorded
sequence replayed into the page. Exit: identical counts to the Python
suite; the reload test passes.

8.7.8 Stage 7, the console tty: `console_view.ts`, the console lane,
the permission flow, bootstrap.py's `console` role. Proves `echo`
through dash into xterm.js, `^C` ending `sleep 600`, ctrl-0 showing and
hiding the view, the role refused outside debug mode, `console_run`
returning the output and timing out on `sleep 600`, Deny returning an
error to the caller. Survey: a PNG with the console visible. Exit: the
browser test passes.

8.7.9 Stage 8, the hyperposition: `mcp.ts`, `provider.ts`,
`provider_script.ts`, `agent.ts`, `tools_browser.ts`, `script.ts`,
`media.ts`, the seeds, `script/bootstrap.js`. Proves the stubs of 8.5
end to end with time not advancing without input. Survey: a PNG after
the exchange. Exit: the scripted run passes; the real provider is
behind a setting and outside the automated tests.

8.7.10 Stage 9, the beachhead: the one-function change to the Windows
scripts; the engine serving from the maintainer's WSL account; the
maintainer's test plan run by hand. Exit: the maintainer's sign-off.

## 9 Operations

- First beachhead: the engine runs from the maintainer's own user
  account on WSL, started by the existing Windows scripts, nothing as
  root, no service manager, no container.
- Server root `~/.cache/xsjs/`: `bootstrap.py`, the Python package,
  `main_loop/`, the page, `settings.json`, `ttyd.log`, `engine.lock`,
  `tap/`, the databases and `cache/`. Start copies the package, the
  page, the settings and the seeds there. The provider key is
  `XSJS_PROVIDER_KEY` in the environment of the ttyd process.
- Certificate, boot and checkout decisions of the Project Direction
  stand unchanged.
- An audit of the key in `hello` and of the dispatcher's single door
  follows the beachhead (10.12).

## 10 Things that should be possible, but not implemented.

Each item is a request from the planning process that this plan does not
build. The design that was reasoned out is written beside it so that
nothing is lost (rules: Requirements-Data-Loss).

10.1 Multiplayer.

- One tty per additional player, numbered 2 and up; ttys carry the
  player number in `--url-arg` and bootstrap.py takes it as a role.
- One bootstrap.py process per player on the same universe files in
  WAL; the server is the arbiter, as every browser forwards to it.
- Turn based strategy: a turn order table in the world, designed by the
  scripts; the server refuses a forwarded operation from a player whose
  turn it is not, an `error` the page shows.
- The overlays ctrl-2 and up exist for these ttys already (2.6).
- This may need the back end in C++; 10.2.

10.2 A hardened server.

- The JSLB dispatcher's single door is the interface a C, C++ or Rust
  component implements; the ttyd command line and `hello` are the seam.
  The Python main loop stays downloadable until then.

10.3 Containers, `.sh` scripts and other OS flavours.

- `xsjs_install.sh`, `xsjs_start.sh`, `xsjs_stop.sh`, `xsjs_status.sh`
  at the top level with the same names and logs `<script>.sh.md`.
- A lifecycle test in a Docker container inside WSL under
  `--container`, running as a user, not root.
- A systemd user unit for start at boot on Linux.
- Version floors and checks return when the other OS flavours arrive.

10.4 A sandboxed dash.

- Without root: environment scrub, working directory, resource limits,
  `os.unshare` for user and network namespaces; or a container. Any
  failure to apply one is a hard error. No line type changes.

10.5 Server side image fetching (a required door).

- `image.fetch {url, key}` to the server, which downloads the bytes
  with `urllib`, stores them in `_files` and replies with size and
  SHA-256; the browser then `kv.get`s them. Needed when a provider's
  image host refuses a browser origin. The server then needs the
  sleeping task of 10.13.

10.6 Providers other than xAI.

- The same chat completion and image shapes with another `base_url`
  and model names; Anthropic's compatibility endpoint serves chat and
  no images.

10.7 Crossfade prefetch.

- When `/$world/scene` changes, the next scene's headers (6.4) are read
  and its media fetched before `render`, while the UI cross fades from
  the old image.

10.8 Switching the player in the page.

- The data model holds several players (6.6). The bootstrap script
  switches `/metaverse/player`; a control in the page that offers it to
  the user is not built.

10.9 Content divergence detection.

- Equal `seq` with different contents, from a non deterministic
  statement: a per database checksum computed by the wrapper, the
  SHA-256 of every row in primary key order, compared at `hello` and
  after each forwarded operation; a mismatch is a desync.

10.10 Explicit forwarding routes.

- A route list header each hop pops, for a line that must visit several
  threads with markup added at each, such as a diagnostics request. The
  owner table covers the cases this plan needs (4.3).

10.11 A credit line for uploads.

- `wire.credit {bytes}` from the server granting what it will accept,
  added only if the stage 2 measurement of ttyd's resident size demands
  it.

10.12 The security audit.

- The key in `hello`, the single door, the console tty, the permit set.

10.13 A sleeping task on the server (symmetry with 4.2).

- `dispatch.py` gains `task_sleep` and `main_loop.py` a wake table when
  the server first needs to wait on something, as 10.5 would.

10.14 Compaction beyond an estimate.

- A summary turn written by the provider rather than by truncation,
  and heuristics on scene changes, inside the wrapper.

10.15 Line types versioned by handler.

- A handler registered per version; a line of another version is an
  error, not a translation; a breaking framing change is a new `hello`
  field. Nothing needs a second version yet.

10.16 Verbose follow.

- `verbose.follow` from the page registers for the server's lines;
  `verbose.line` is pushed for each line written from then on;
  `follow_add(fn)` in `verbose.py` is the hook. The front end asks with
  `verbose.tail` until this is required.

10.17 Telemetry and dumps.

- `verbose.dump(level, name, value)` writes a KV row
  `/_verbose/dump/<name>` holding the JSON of `value` when the level
  allows, so a thread's state can be inspected after the fact; a
  `verbose_dump` tool for the AI. Not required by any stage.

10.18 Server side `sql_run` in debug mode.

- The `sql.run` line on the wire against a server database, debug only,
  for the AI recovering the server. The AI's console reaches `sqlite3`
  meanwhile. Not required by any stage.

## 11 Things that are not being done without permission.

Each item was proposed during planning and decided against by the
maintainer, or is a proposal that no request motivates and that this
plan drops. Each item gives what was proposed and what replaced it or
why it was dropped, and the record (12) holds the maintainer's words.
Nothing here returns without a request.

- JSON Pointers: replaced by Document-Refs.
- A fixed Document-Ref depth `<db>/<kind>/<name>/<version>` and separate
  `doc` and `doc_head` tables: rejected as over fitting an example and
  re-inventing a table; a document is a KV row with `_head` for
  performance.
- A `refs` array required in every document: replaced by the integer
  keyed headers probed from `0`.
- One database per scene, eight attached: replaced by one per region,
  then by the universe, world and region databases and tables the
  bootstrap script makes.
- SQLite in the browser's local storage: OPFS in a worker.
- Settings, preferences and files databases on the main thread: on the
  AI thread, as `_settings`, `_preferences`, `_files`. Their removal in
  favour of `hello` and a metaverse document: rejected.
- Three threads with the substrate on a WASM worker and the AI worker as
  owner on paper: merged into two.
- A handler on the AI thread returning a promise: rejected; the task
  manager sleeps and wakes.
- `handler(**line)` with the headers as keyword arguments: the
  dispatcher calls `handler(line, **payload)`.
- A line type defaulting to `utf-8`, string versions, a blob type
  registry: type required, integer versions, defaults omitted, no
  registry.
- `text_format` as the i18n function name: `i18n` with a `from`
  exception.
- Node banned entirely: allowed for tsc at build time.
- `.sh` parallels, a Docker lifecycle test, serving from an Ubuntu
  container, a systemd unit, version floors: doors, not work.
- Debug mode as a flag of the ttyd command: a setting.
- All of the page's JavaScript editable by the AI: the modules the AI
  does not edit are precompiled; the AI edits its own scripts.
- A server side TypeScript compiler for the AI's scripts: dropped;
  nothing is sent for compilation.
- The AI's steps run with `new Function` and no MCP edit, run or debug
  tools: rejected; MCP edits, runs and debugs them.
- Reconnect in the same page without reloading (the rules' Project
  Direction 1.3, written for the old bootstrapper's test, says never
  retry by reloading the page): a full reload is the tested path.
- `put`, `ls`, the forked modules and the command loop of bootstrap.py
  (the existing code): ripped out; not recycled unless the design needs
  it.
- One tty with dash forked by Python and relayed as JSLB blobs:
  rejected; two ttys, the console optional.
- The `log` namespace, `engine_log.py`, `log.sql`, `log.*` lines,
  `log_tail`, `log.ts`, `log_ring`: rejected for `verbose`.
- The verbose module without its external call wrapper "with the PY to
  SH ban": rejected; the wrapper is the one place external calls go
  through.
- The AI's tables replicated by whole snapshot after a turn, with a
  trigger written change log planned as the improvement: rejected; every
  operation forwarded as it happens.
- A row log with per row `seq`, `kv_gone` tombstones, `sync.pull` and
  `sync.push`: dropped with forwarded operations.
- `kv.changed` pushed by the server while a tab is open, and the browser
  pulling: dropped; replication is one way during play and the start
  replaces differing files.
- Always Allow stored in the preferences document: tab only.
- The provider key in `secrets.json` in the root: the environment.
- The UI fetching the provider's image URL as the first form: `b64_json`
  first.
- The whole TAP stream sent at the end as `tap.report`: each line as its
  own `tap.line`.
- A read only second tab: single tab.
- Compaction decided by the agent from a token estimate in `agent.ts`:
  inside the wrapper.
- `sql_run` guarding the engine's tables by parsing statements with
  `EXPLAIN`: the substrate's tables are prefixed and refuse writes by
  name.
- Forwarding left out of the first version of the design ("not in the
  first draft"), with two tasks from the caller instead: rejected;
  forwarding is required.
- Multiplayer dropped without mention: harvested into 10.1.
- A console log-in and a player account: none; ownership of the server
  is the account.
- 128 MiB, written once as the overflow threshold: 128 KiB.
- Python `console.py` and `engine_console.py` forking dash under a pty:
  dropped with the one tty design; the console is ttyd's.
- A section designing a fourth thread: reduced to the one sentence in
  2.2.
- A `report_html` declaration in API/ts/tap.d.ts that no sentence of the
  design stated: the highlighted report is stated in 8.1 and the
  declaration follows it.
- Suggesting additions to the reformat whitelist: banned by the rules
  (do not suggest additions to the whitelist); new source files are
  added when created.
- `settings.ts` generated from settings.json at build time, and a
  `settings_sha256` in `hello` refusing a page built from another file:
  dropped; settings arrive in `hello` and the module is hand written.
- `python`, `sqlite` and `debug` fields in `hello`, `tab` and the page's
  hash in its reply: dropped; no version checks, debug is in the
  settings, nothing reads the rest.
- `port_windows`, `port_wsl`, `console_enabled`, `console_columns`,
  `console_rows`, `mcp_protocol_version` and `log_ring` as settings:
  dropped; no module reads them, the console is debug mode, xterm.js
  sends its own size, the revision is a constant.
- `script_put`, `script_get`, `script_list` tools: dropped; a script is
  a KV row the existing `kv_*` tools edit.
- `universe_create`, `world_create`, `region_create`, `player_switch`
  and `scene_enter` as engine tools in the substrate: dropped; the
  scripts are the database administrator and the seeded bootstrap script
  does these.
- `verbose.dump`, `verbose.follow`, `verbose.line` and a server side
  `verbose.level`: deferred to 10.16 and 10.17.
- Turns as documents, or as the version history of one document: the
  turn table.
- `{"$ref": n}` naming a top level `refs` table: the references are the
  headers `1` on, probed.

## 12 Decision record

The planning process in order, in the maintainer's own words. Four
passes produced it: a first design document and thirty questions about
it (12.2); a second design document, API/, DATA/ and thirty two
questions (12.3); an audit of every request with the maintainer's
answers to its findings (12.4); and a third design document, which is
this file's first form, with thirty two more questions of which twelve
were answered (12.5). 12.1 holds the briefs and the maintainer's
statements about process. Those documents no longer exist; what matters
in them is here.

Each entry has an identifier, the question condensed, the maintainer's
answer literal in a text block, a Later line where a later entry changed
it, and an Applied in line naming the sections of this plan that carry
it. The condensed questions are the AI's words; the text blocks are the
maintainer's.

12.1 The maintainer's briefs and process feedback.

The requests that started each pass, and the maintainer's statements
about how the AI should work, literal and in the order given. They
govern how this plan is used (0.3).

12.1.1 2026-10-17: the first brief, which commissioned the first design
document and its questions.

```text
I just committed [the original plan, section 15] which is a rough draft of a system
architecture  i want to build and a bit of product direction to guide the
project. this doc represents a plan for the futre direction of the codebase
you are running in.  my primary concern is architecture, correct wire
formats, correct communication patters, correct SQL design and elegant use
for this application. i need modules designed before they are implemented,
and done so with a professional seperation of responsibilities. then i need
an intremental test plan where everything is kept barebones, and can be
surveyed as such, so the foundations are viasibile before the next stage of
contruction begins. read the plan doc. look at [the old test plan] as a dump
of obsolete information that still encodes likely relavant information about
how to stay out of the cracks. focus on documenting detailed things in your
plan with 79 char bullet points about my A class concerns. write [the first design document] with
[the original plan, section 15] fleshed out into as much of a plan as you can. then
write [the first question file] with questions you have for me that need to be
resolved in decreasing order of severity. stop at 30 for now. think hard,
take all the time you like.
```

12.1.2 While the first design document was written, about the registry
of formats (FORMATS.md).

```text
don't read formats
```

12.1.3 The same pass.

```text
please don't look in my git history, stay on target
```

12.1.4 The same pass: the test API, later replaced by the project's own
TAP modules (12.3.13.1).

```text
this is what i want the test api for PY and JS to look like. you can just copy the "tappy" PY module into this project and make a JS clone.  https://tappy.readthedocs.io/en/latest/producers.html
```

12.1.5 2026-10-17: the second brief, which commissioned the second
design document, API/, DATA/ and the second question file.

```text
read the modifications to  [the first question file]  in the last commit. write
[the second design document] incorperating this feedback and after reassesing the entiere design
with this feedback in mind and with a feeash set of eyes.  Then create a dir
called API/ and start writing just the external APIs for the modules required
in the different languages. Then create synthetic communication logs (with
blobs replaced with """<1 blob>""" e.g. """{ blah:1}<2 blobs>"""). Put the
synthetic transcripts of standard communication in DATA/ so i can think about
it. feel free to write a script to generate the transcripts, but it should be
generally real. showing the boot sequence would be cool. then write your top
32 A list questions remaining to [the second question file]  and stop.
```

12.1.6 After the second pass: an instruction to edit the rules' reformat
whitelist rule as the answer to 12.2.5.4 asked.

```text
3.6 update it.
```

12.1.7 2026-10-18: after the second design document was found to have
dropped forwarding with the words "is not in the first draft" (see
12.4.1.3).

```text
so i asked for JSLB forwarding and got back a response from you just now
including the statement 'forwarding "is not in the first draft"'.  explain
the process that led to this outcome? do you have instructiions in your
system prompt or were there other instructions? can you confirm I wat i
wanted to do bottom up test driven development and so building "drafts"
and "prototypes" were a non goal and architecture and unit tests before
integration tests slowly leading to the top of the mountain was the goal.
please advise me on how to instruct a futre agent to adress this rationale
```

12.1.8 2026-10-18: the two failure modes, which the rules now name
Accidental-Requirements and Requirements-Data-Loss.

```text
I understand now, thank you.  there are two failure modes. the first
failure mode is writing example code that is unmotivated by a need in the
current design and then having that arbitrary example ossify. this may
already be happeneing with the xsjs code being available to this planning
session. the second failure mode is making example code that has the wrong
API and then leaving the user without even any knowlege of what was the
good API that the AI planner hypotosized about before curtailing its
efforst. please explain this in your own words
```

12.1.9 2026-10-18: the instruction that produced the third design
document, whose sections 10 and 11 became sections 10 and 11 here, and
whose decision record became section 12.

```text
well that went wrong. i responded to [the audit] in [the audit answers], read it for
confirmation. sorry about the frustrated remarks, i really thought my
second round responses could be addressed without writing an intermediate
planning document.  write [the third design document] with an updated version of [the second design document]. read
the task_* docs and add sections to [the third design document] entitled "## Things that should
be possible, but not implemented." and "## Things that are not being done
without permission." and add all requests for futre capability to the
former. then add all requests that ended up being decided against to "##
Things that are not being done ...". I want a complete scrape of the whole
planning process I went thtough so that every descision is in this one
document and i don't have to keep asking you ro re-read all the
engineering logs. keep it point form where possible. when you are done
write [the third question file] with up to 32 A list questions, ranked by potential rework,
if you have them.
```

12.1.10 2026-10-18: after the rules gained the section on
Accidental-Requirements, Requirements-Data-Loss and
Requirements-Refusal.

```text
This was been added to [the rules file]. """ [the section "Accidental-
```

12.2 Round 1: the first design document, answered 2026-10-17.

The first design document was written from the original plan (15) and
ended with thirty questions in decreasing order of severity. Each entry
below is one question, condensed, and the maintainer's literal answer.

12.2.1 The shape of a JSLB line and how a handler receives it.

12.2.1.1 Is a JSLB line a JSON object whose keys `0`, `1` and so on are
the headers and whose other keys are the payload, rather than a JSON
array with the payload at a position that depends on the blob count?

```text
== yes. (ignore alternatives in my responses unless mentioned.)
```

Applied in: 3.1, 3.2.

12.2.1.2 How does a handler receive a line: `handler(line, **payload)`,
payload being the non integer keys, so a handler reads `line["1"]["d"]`
for its first blob; or the headers moved under one named key so that
`handler(**line)` alone suffices?

```text
== yes to the former.
```

Applied in: 7.2, 11.

12.2.2 Where the model runs and who holds its key.

12.2.2.1 Does the model loop run in the browser's AI worker, calling the
model's HTTP API with a key held in the browser, or on the Python
server, which then needs an HTTP client in its select loop and a key in
its state directory?

```text
== This is not Model View Controller. Instead the model is broken into
  DBs which are intermediated by a single thread. However and composition
  of threads intercommunicating directly and using their own private DB
  storage is a critical architectural component. If another thread with
  a few more DBs is needed that should entail reusing existing code
  (e.g. the task system)
```

Applied in: 2.2, 5.1, 11.

12.2.2.2 Which provider and model?

```text
== Use a generic AI protocol so service can be rented from SpaceX's AI
  division. Anthropic doesn't generate images. Plan to test the AI operating
  over that protocol using automated test driven development where no
  actual AI is required. Testing for this project should not involve
  running an AI at first. Logging a synthesized AI conversation using
  the generic AI MVC protocol to emit chat messages, respond to single
  integer inputs (to simulate conversation).
```

Applied in: 5.2.

12.2.2.3 Is MCP meant literally, JSON-RPC `tools/list` and `tools/call`
over a transport, or is a tool table in MCP's shape enough until an
external client needs to connect?

```text
== No I expect the correct expected protocols to be emulated before building
  anything that would use them. The APIs are more valuable than a demo. Any
  part of the design that skimps on API so that integration testing can
  be done in the wrong order needs to be entirely re-written.
  I would rather have an incomplete code base with correct APIs than have a
  demo that has to be rewritten after the ship already left port.
  Implementation churn is unacceptable as a planning goal. Fix that and plan
 to iterate on docs until we have APIs before code.
```

Applied in: 1.1, 5.4.

12.2.3 SQLite in the browser cannot live on the main thread.

12.2.3.1 sqlite3.wasm persists through OPFS, which exists only in
workers, and `localStorage` holds about 5 MiB of strings, so every
browser database belongs in a worker and the main thread has none. Does
"browser's local storage" mean OPFS, or was `localStorage` meant for
settings and preferences only?

```text
== The main thread needs media and it will have to cache that in a
"media_db" JS/DOM object(s) that is not OPFS.
```

Applied in: 2.2, 11.

12.2.3.2 Media would then live in a database worker and the main thread
would paint from transferred buffers. Is that acceptable in place of a
files database on the UI thread?

```text
== No. All the DBs go on the AI thread. I was explicit about the AI
  worker thread (the one talking to the AI API) being in the same
  thread as the DBs it uses. For now we have 3 threads:
    - UI: downloads media
    - AI: utilizes and proxies DBs
    - WASM: sqlite wasm

Add to the docs this is a design goal until a hard need for more arises.
```

Later: The all databases on the AI thread part stands; the three threads
design goal was changed to two by 12.3.6.1 and 12.4.2.3.
Applied in: 1.6.1, 2.2, 6.2, 11.

12.2.4 One static file, and where third-party code comes from.

12.2.4.1 ttyd serves one file. Inline every script and sqlite3.wasm into
it at build time, fetch scripts from the files database over JSLB later,
or serve static files from a Python server?

```text
== Yes, however, add this as an additional goal. TypeScript (via tsc) should
  be used to create any JS file that is served as part of
  hyperposition-engine.html. And that page should contain all the source
  code required without dynamic requests for TS compilation.
  Changing hyperposition-engine.html (aside from using debug tools) will
  require a reload and a potential recompile.

  Yes have `page_build.py` merge html and css templates. use canonical
  TS error handling and logging. the v0 hyperposition-engine.html
  needs a way to show a view with the TS console. And optionally logging
  TS/JS spew to the server (using JSLB+DB sync) is important.
```

Applied in: 2.4, 2.5, 2.6, 11.

12.2.4.2 sqlite3.wasm, xterm.js headless and tappy would be fetched by a
standard library script with pinned versions and SHA-256 into
`third_party/` and committed. Is committing them acceptable, and is
xterm.js headless the "minimal adaptation" meant?

```text
== xterm.js needs to run off screen and so that may make sense. add
 this as a research goal. there needs to be a clean standard way to
 show the DOM described by xterm.js however it is integrated, because
 the user may want to put it on screen looking thw way it normally
 does and see the history with color and all the features. and then
 close it again. it is expected to be a debug console in the normal
 sense. Pressing the ESC key should show and re-hide it when enabled.
 enable it for now.
```

Later: The ESC key was changed to ctrl-0 by 12.3.15.1.
Applied in: 2.6.

12.2.5 Consequences of tappy as the test API.

12.2.5.1 tappy's `TAPTestRunner` is `unittest.TextTestRunner`, so tests
become `unittest.TestCase` classes and the original plan's rules "no
existing test facility" and "a falsy return fails" lapse. Confirm.

```text
== Confirm. Sorry, midstream change of plans. "unittest" is back on the
  table and a JS version of PY's "unittest" with just the API surface
  actually used is desired too. then both languages have test that
  look similar and output that is identical.

  Add that all test runs are to be checked by the tappy TAP consumer
  package. Then may need to be sent from the browser to the server for this.
  That would fit an automated testing story that is required.
```

Later: The unittest and JS clone part stands; the tappy copy was
replaced by the project's own TAP modules by 12.3.13.1.
Applied in: 8.1.

12.2.5.2 unittest runs methods in name order. Is that fine, or must the
JS clone also sort by name so both read the same?

```text
== this is fine. sideffects are banned.
```

Applied in: 8.1.

12.2.5.3 In a page there is no output directory for TAP files. Keep the
`.tap` texts in a map listed by class name and stream to a `pre`?

```text
== there should only be one TAP "test plan" for each language.

so a single producer process emits multiple suites in one stream
suites are handled by subtests: indented TAP blocks (4 spaces) each
with their own plan, followed by a parent-level ok line
```

Applied in: 7.2, 8.1.

12.2.5.4 The tappy copy keeps tappy's style and `from` imports, outside
the formatting rules (`python/*.py` does not descend into `python/tap/`
and pyright would exclude it). Is a subdirectory outside the formatting
rules acceptable, or should the copy be restyled to the project's rules?

```text
== Update [the rules file] not to ignore the whitelist and not ask to add new
  files.
```

Applied in: the project rules, not this plan.

12.2.6 One tty or two.

12.2.6.1 Run the console as a second ttyd connection, the role in
`?arg=console` through ttyd's `--url-arg`, or as one connection with
dash under a pty that Python forks and relays in JSLB blobs? Which
first, and is the single tty form the target?

```text
== 2. all of these questions seem to be asking me to restate myself.
```

Later: The "2" was read wrongly by the second design; corrected by
12.3.27.1 and 12.4.2.1.
Applied in: 1.6.2.

12.2.7 What the server does after a handler fails.

12.2.7.1 When a handler fails, write one `error` line with the stack,
exit 1 and let the connection end (one process per connection makes that
cheap), or answer the error and keep serving?

```text
== All errors should result in the web app disconnecting and asking to
  reconnect. Any realistic effort should be made to ensure it gets
  a message to display before losing the connection. Server status can
  be reconcilled when the app tries to reconnect.
```

Applied in: 1.2, 4.5.

12.2.7.2 The same for a worker in the page: the first failure disables
the controls and shows the detail. Agreed?

```text
== Yes, add to the docs this is a fail fast codebase that never swallows any
  error and focuses on stopping with a correct error message that can be
  fixed. Fixing bugs is more valuable than stability for now.
```

Applied in: 1.2.

12.2.8 Raw mode and the CR terminator.

12.2.8.1 The engine role puts the pty in raw mode so blobs pass. That
removes `^C`, `^D`, the 4095 byte line and the echo on that connection;
a runaway is ended by closing the socket. Agreed?

```text
== yes
```

Applied in: 2.3, 3.10, 4.4.

12.2.8.2 CR alone ends a line. In raw mode CR and LF are both plain
bytes, so the choice is convention. Keep CR, as Enter in a terminal
sends CR?

```text
Just write it POSIX style. Do not treat LF differently than any other char.
```

Applied in: 3.1.

12.2.9 Header fields and their defaults.

12.2.9.1 Replies need an id to match: `i`/`id` on requests and
`r`/`reply` on answers. Agreed, and are those the names?

```text
== OK, but document along with the rest of the design doc for JSLB.
```

Applied in: 3.3, 3.9, 11.

12.2.9.2 The original plan gave the line header's type the default
`utf-8`, which is a content type, while dispatch keys on type. Make the
line type required with no default, keep `utf-8` as the blob type
default, and make versions integers defaulting to 0?

```text
== Yes, and do not print values that are at their defaults. So version
 numbers only show up in JSLB when a chunks version has actually changed.
```

Applied in: 3.3, 3.5, 10.15, 11.

12.2.9.3 A blob type registry was proposed: `utf-8`, `json`, `png`,
`jpeg`, `webp`, `sqlite`, `js`, `wasm`, `html`, `css`, short names, not
MIME. Where is the registry kept?

```text
== There is no blob type registry. blobs are opaque binary objects
  to the JSLB handlers. the JSLB's handler is responsible for interpreting
  the blob headers independently.
```

Applied in: 3.4, 11.

12.2.10 The fate of put, ls, restart and forked modules.

12.2.10.1 `put` and `ls` of the existing bootstrap.py would become
`files.put` and `kv.list`, `restart` would become `system.restart`, and
the fork of modules would stay without a caller. Do forked modules
survive as a way to run a long job off the select loop, or do they go?

```text
== do not recycle this codebase unless it is needed for the new design. rip
  out PY->SH as much as possible.
```

Later: "Rip out" was clarified by 12.3.32.1.
Applied in: 1.5, 11.

12.2.11 What "reasonably sandboxed" means for dash.

12.2.11.1 What does "reasonably sandboxed" mean for dash? Without root,
Python can scrub the environment, change directory, set resource limits
and call `os.unshare` for user and network namespaces. Which are
required, and is a failure to apply one a hard error or a reason not to
serve the console?

```text
== It may simply mean a docker container. this is not a request to
  implement anything. it is a request to keep a door open.
```

Applied in: 10.4.

12.2.11.2 Is the AI's console access gated by the page confirming each
command?

```text
== Present "Accept" "Deny" "Always Allow" buttons below the request.
```

Applied in: 2.3, 4.6, 10.4.

12.2.12 The overflow threshold.

12.2.12.1 The original plan says 128 KiB twice and 128 MiB once as the
overflow threshold. Which?

```text
== 128 KiB
```

Applied in: 3.8, 6.5, 11.

12.2.13 Replication and conflicts.

12.2.13.1 Replication starts with whole database snapshots, then a row
log by `seq`. The browser writes its player's world and scenes, the
server backs them up, the server masters scripts and seeds. What happens
with two tabs on one world, and what cadence is "as reasonable"?

```text
== reasonable means continuously, while remaining efficient.
  there has to be a JSON Pointer scheme but i didn't fully define it.
  the AI API is responsible for writing scripts that talk to the DBs
  about the schema of the players metaverse. This can be smoke tested
  to show an arbitrary AI generated script could execute SQL transactions
  but schema correctness is explicitly a non-goal and the responsibility
  of the AI API.
```

Applied in: 5.6, 6.8.

12.2.14 The JSON Pointers section.

12.2.14.1 The original plan's JSON Pointers section ends mid-sentence at
"When the play". What was the rest, and what is the document's root?
(Assumed: every KV key is a JSON Pointer into one logical document and
`world` holds `/scene`.)

```text
== Sorry. I need to be able to push new versions of a json doc into the KV
  and have other docs reference the version. I called that a JSON Pointer
  but rename that a "Document-Ref". Adding each json docs "version"/"v"
  string to the end of the KV key (e.g. forest/trees03/scene/53) would
  work for a "Document-Ref". Then by adding forest/trees03/scene/54 and
  setting that as the player's current scene, the update could be pushed
  out and replicated while keeping history. then if the paths in the new
  scene point to things not yet cached locally in the DB then the thread
  knows to ask an external source for the document. This is how the server
  reconstructs the web apps document trail. it is like no-sql.
```

Later: The Document-Ref grammar was fixed by 12.3.3.1 and the
Key-Value-Ref defined by 12.5.3.1.
Applied in: 5.5, 6.4, 11.

12.2.15 Identity.

12.2.15.1 "Once logged in" today means ttyd's Basic authentication. Is
there a player identity beyond that, and how does a connection map to a
per player directory?

```text
== No there is no player account. Ownership of the server is the only
  "account."
  Change the plans: don't require a console log in. If the web app needs
  auth anyway then just allow that to be the only tty. However, the AI
  and the user need to be able to enable and log it in at any time.
```

Applied in: 2.3, 11.

12.2.16 Debug mode.

12.2.16.1 Debug mode is a flag in the ttyd command written by the start
script, reported in `hello`, gating the console, settings writes, module
puts and restart. Is that the definition?

```text
== yes, cool.
```

Later: Debug mode became a setting by 12.3.26.1.
Applied in: 11.

12.2.17 Scenes as files and the region.

12.2.17.1 One SQLite file per scene, attached to the world connection as
the region, at most eight attached; compaction replaces a prefix of
turns with one summary turn; crossfade means fetching the next scene's
files before entering it. Does that match the terminology?

```text
No, that sounds too fine grained. An experience may create a new scene every
few minutes. e.g. by walking through a castle. Use 1 DB per region for now.
That means a DB for "metaverse", one for the specific experience, and a
third for the region within that. Division into regions should involve
disjoint entities. Whereas scenes normally involve entities following from
location to location while the player moves through a local environment.
```

Later: Refined by 12.3.19.1 and 12.3.21.1 into the metaverse, universe,
world and region databases.
Applied in: 6.6, 11.

12.2.18 The ECS schema and the AI's rights.

12.2.18.1 The schema gives entities, JSON components by kind, media by
role and a turn log, so the AI invents kinds without DDL. May the AI run
DDL at all through `sql.run`, or only statements against these tables?

```text
== Allow DDL: the agent can add indexes on JSON paths it queries often, create
  views, or promote a mature kind to a real typed table. This is a cornerstone
  part of the design. The AI API is expected to create multiple tables for
  managing all the various formats of Entity Component System data, without
  resorting to json.
  The AI API is expected to act like a professional database admin and set up
  the database for the experience as if it were working at a big company.
  Then the "simulation steps" JS for the experience can use fast SQL queries
```

Applied in: 5.5.

12.2.19 The thread model of the first draft.

12.2.19.1 The original plan says "the first draft does have to have a
web worker", which may be missing a "not". OPFS forces at least one
worker. Is two right, or one?

```text
== this was a mistake, omit. 3 threads are needed.
```

Later: Three threads were merged into two by 12.3.6.1 and 12.4.2.3.
Applied in: no section; the sentence is omitted.

12.2.20 Synchronous task bodies.

12.2.20.1 A task body is synchronous and anything that must await is
split into a second task, which makes "one task per database" true
without locks. Agreed?

```text
== yes. the task queue is the only sync tool. add that to the docs.
```

Applied in: 1.3.

12.2.21 Images.

12.2.21.1 Who makes the pictures, the same model or an image provider,
and from which thread? Formats PNG and WebP; a size budget per image?

```text
== the AI API provider makes the images and sends them to the web apps
  UI thread. They will be backed up sparingly to the web workers DBs and
  more aggressively cached by the server.
```

Applied in: 5.5, 5.7, 6.7.

12.2.22 The JavaScript test runner.

12.2.22.1 Run the JS test suites in headless Chrome through the existing
DevTools driver, because sqlite3.wasm and OPFS need a browser; Node is
installed but unused by the project. One runner, in the browser only?

```text
Yes. Node is banned as a bad dependency. This all needs a browser to test.
```

Later: Node was allowed for tsc at build time by 12.3.1.1.
Applied in: 8.2, 11.

12.2.23 Flow control for big uploads.

12.2.23.1 ttyd queues pty writes in memory with no window. Measure
ttyd's resident size during a 128 MiB echo and add a credit window only
if the measurement demands it?

```text
== No. research config required and how to set it. A 1MiB buffer is a fine
  default if that fixes nonsense.
```

Applied in: 3.10.

12.2.24 Docker.

12.2.24.1 `docker` is installed in the maintainer's WSL. May the
lifecycle test use it, with `ubuntu:24.04` as the base, the container
running as a user, not root?

```text
== That is optional and happens when --container is passed to the test
  script. Document this as a door to keep open but not implement.
too soon.
```

Applied in: 10.3, 11.

12.2.25 Start at boot on Linux.

12.2.25.1 The Windows side uses a sign-in task; Linux and a container
have no sign-in. Is a systemd user unit wanted for `xsjs_start.sh`, or
nothing?

```text
== too soon. first i need it working out of my user account, with an
  awareness of work after that. make "working out of my user account"
  on WSL the "first beach head." it is the first gaol, doc.
```

Applied in: 9, 10.3, 11.

12.2.26 Shell dialect and logs.

12.2.26.1 `archive.sh` is POSIX sh and `clean.sh` is bash. Make the four
admin scripts POSIX sh for dash, with logs `<script>.sh.md` beside them
like the PowerShell logs?

```text
== document those two scripts are not part of the project and are to be
 ignored.
```

Applied in: 7.5.

12.2.27 Settings.

12.2.27.1 `hello` carries the settings. Seed them from a top level
`settings.json` read by the server at start, and may only debug mode
write them back?

```text
== yes have a settings.json that is used by the PY back end for config and then
  injected into the JS web app unmodified. do no filtering, just put the
  settings into the web app.
  passwords and auth do not go in settings. settings are just a way for
  engineers to keep all the constant values in one place.
```

Applied in: 1.6.9, 2.4, 4.4, 6.9.

12.2.28 Version floors.

12.2.28.1 WSL has Python 3.14 and SQLite 3.46; `ubuntu:24.04` has Python
3.12 and SQLite 3.45. The design needs `Connection.serialize` (3.11),
`os.unshare` (3.12) and `STRICT` (SQLite 3.37). Floors of Python 3.12
and SQLite 3.38?

```text
== don't run docker. i will create test environments later to test and fix
  running on 20 different OS flavors.
```

Later: Version floors and checks were dropped by 12.3.31.1.
Applied in: 10.3, 11.

12.2.29 The i18n call.

12.2.29.1 The original plan writes `i18n("internal_error", code)`. A
Python module is not callable and `from` imports are banned, so name the
function `text_format` in both languages, with `{0}` placeholders shared
with the PowerShell strings?

```text
add an exception to the docs allowing "from" with i18n so i18n("xx") can
be used after importing it from i18n.
```

Applied in: 7.1, 11.

12.2.30 Measuring the 200 Hz goal.

12.2.30.1 Measure the 200 Hz goal on the UI thread with a long task
observer during a 16 MiB transfer, requiring no task over 5 ms. Is that
the acceptance measurement, and 5 ms the budget?

```text
5ms is a soft target. Yes, this is a required test. I/O stalls hitting
the main thread are fatal and a stress test is needed.
```

Applied in: 8.4.

12.3 Round 2: the second design document, answered 2026-10-18.

The second design document applied the first round's answers, added API/
and DATA/, and ended with thirty two questions. Each entry is one
question, condensed, and the maintainer's literal answer.

12.3.1 tsc needs Node.

12.3.1.1 tsc is a Node program and Node is banned as a dependency. Is
build time Node allowed, and may Python run it (the rules require
approval for Python running command line utilities)? The alternative is
compiling TypeScript inside headless Chrome through the DevTools driver.

```text
== Make the use of Node for tsc an exception. Sorry.
```

Applied in: 1.6.16, 2.5, 11.

12.3.2 Replicating the AI's own tables.

12.3.2.1 The row log replicates the engine's tables only. The typed
tables the AI creates have no `seq`. Is a whole snapshot after any turn
that changed such a database acceptable for the first version, with
triggers writing a change log as the second?

```text
== No. Replication is always over JSLB. For now forward all modifications
  as they happen from the modifier to the server via other threads as needed.
  the first unit tests just need to replicate a string->string DB table
  from the AI worker and the UI. This is required to be part of the
  substrate module and not handled ad hoc. update docs.
```

Later: Operation forwarding was confirmed by 12.5.5.1.
Applied in: 1.6.7, 6.8, 11.

12.3.3 The Document-Ref grammar.

12.3.3.1 The Document-Ref was drafted as `<db>/<kind>/<name>/<version>`,
so the database is always the leading one or two segments and no lookup
is needed; the example `forest/trees03/scene/53` became
`forest/trees03/scene/clearing/53`. Is the fixed depth acceptable?

```text
== Update docs, the plan over fits an example,  The document schema is:

    `/$db/$id/$version` - external DB reference.
    `$id/$version` - internal DB reference.

  $db - a valid C identifier
  $id - any non-null utf-8 sequence
  $version - an integer literal

  The default setup is described below.
```

Later: Extended by 12.5.3.1, which defines the Key-Value-Ref.
Applied in: 1.6.5, 5.5, 6.4, 11.

12.3.4 The generic provider protocol.

12.3.4.1 The provider protocol is the chat completion protocol with
function tools and the image generation endpoint, as xAI serves both at
one base URL. The model names in the API stub are placeholders. Is xAI
the first provider, and which chat and image models?

```text
== The first test is all xAI nobody else. Using the same APIs as OpenAI would
  be cool but is not required.
```

Applied in: 5.2, 10.6.

12.3.5 The provider key and browser-origin calls.

12.3.5.1 The AI worker calls the provider directly, so the key must
reach the browser: read it from `secrets.json` in the root and send it
in `hello`, to live only in the AI worker's memory. Is that acceptable,
and has the provider's CORS behaviour been checked?

```text
== No, that is a public GitHub repo. Just get it from the ENV like normal
  for testing.
```

Applied in: 1.6.12, 4.4, 5.2, 7.5, 9, 11.

12.3.6 What runs on the WASM thread.

12.3.6.1 Put the whole substrate on the WASM thread with the AI thread
holding a proxy whose every method is one task, or keep that logic on
the AI thread and make WASM a bare SQL executor, at the cost of many
more round trips per operation?

```text
== if the AI thread and the wasm thread can be merged than just do that.
  otherwise, add all the TS to WASM that helps.
```

Applied in: 1.6.1, 11.

12.3.7 Promises in AI thread handlers.

12.3.7.1 A handler on the AI thread, `ai.say` for one, spans many
awaits. May an AI thread handler return a promise, or must the agent be
written as a chain of separate tasks?

```text
== All AI MCP and WASM should be written in TS and running on the WASM thread
   instead. Only dispatch one
   JSLB in a thread at a time. The task manager provides the DB locking scheme.
   A second JSLB can be enqueued by the handler for a first JSLB. this
   second handler needs to be able to sleep on some number of resource requests.
   in this manner tasks/JSLB lines can re-enqueue in different forms and at
   different destinations.

I should be able to form a transaction diagram of the movement of data in the
thread by logging tasks/JSLB lines submitted to the task queue and events
initiated by the task queue. No other
information should be required to understand the timeline of events in the
thread.

The queue handles having sleeping tasks and being empty as needed. all of
this is required in the plan.
```

Applied in: 1.3, 1.6.3, 4.2, 11.

12.3.8 MCP revision and the stdio transport.

12.3.8.1 Pin MCP revision `2025-06-18` with the `tools` capability only,
and build the stdio transport in stage 4 so an external agent can drive
a server. Is that revision right, and is stdio in scope for stage 4?

```text
== Yes, pin it and emulate any part of it.
```

Applied in: 5.4.

12.3.9 Flow control, the research result.

12.3.9.1 ttyd bounds the pty to client direction by itself and nothing
bounds the client to pty direction but libuv's write queue. Run ttyd
with `--srv-buf-size 1048576`, use 1 MiB chunks, wait on
`bufferedAmount`, stream big blobs to the cache file, and measure ttyd's
resident size in stage 2, adding a credit line only if the measurement
demands it. Is that the configuration?

```text
== ok
```

Applied in: 3.10, 10.11.

12.3.10 How a document declares its refs.

12.3.10.1 Require a top level `refs` array in every document so the
engine prefetches without knowing the schema (the engine refuses a
document without it), or resolve refs only on demand, which gives no
cross fade prefetch?

```text
== use the integer indices for the reference table. this means e.g.
{
  { 0:"/blah/.x../2",
  { 1:"/blah/.fs../1"},
  { "absn":"/blah/.ssx../2"},
  { "$ref":0}
}

This can be resolved into:
{
  { "absn":"/blah/.ssx../2"},
  { "$ref":"/blah/.x../2"}
}

with the referenced strings moved into the references to them. they
may or may not be shared. this should provide a clean round trip from
"normal" to "encoded" and back.
```

Later: Refined by 12.5.12.1, the integer keyed headers.
Applied in: 6.4, 11.

12.3.11 Two tabs on one world.

12.3.11.1 The OPFS SAH pool allows one opener per file and the server
runs one process per connection on the same files in WAL. Refuse the
second tab with a message, or is a read only second tab wanted?

```text
== no single tab only please.
```

Applied in: 2.3, 11.

12.3.12 Recovering from a worker fault.

12.3.12.1 A fault in the AI or WASM worker leaves it in an unknown
state. Should Reconnect also terminate and recreate both workers, or is
a page reload by the user the right recovery?

```text
== Full reload after failure is the tested path.
```

Later: Resolved against the rules' Project Direction 1.3 by 12.5.1.1.
Applied in: 1.2, 4.5, 11.

12.3.13 tappy's consumer and TAP 14 subtests.

12.3.13.1 tappy parses TAP 13, so indented subtest lines may come back
as unknown lines rather than results. Extend the copy to subtests, or
count only the parent level lines?

```text
== write custom PY `tap.consumer` and `tap.producer` modules. write
  `tap.producer` for JS and TY. keep the consumer a simple thing that
  takes a document and returns some stats.
```

Applied in: 1.6.11, 7.2.

12.3.14 When the browser sends its TAP.

12.3.14.1 Send the whole TAP stream as one `tap.report` at the end (a
test that hangs then leaves nothing on the server), or each line as
`tap.line`?

```text
== individual test case results as JSLB messages from the webb app to the
   server. further JSLB debug messages may be added ad hoc.
```

Applied in: 1.6.11, 8.1, 11.

12.3.15 ESC and xterm.js.

12.3.15.1 ESC is a key the shell uses, so ESC cannot both hide the
console and reach dash while the terminal has focus. Which key shows and
hides the console, or is the conflict acceptable?

```text
== use ctrl-0 to toggle the debug console. use ctrl-1..ctrl-n to show debug tty
   io for other tty. the non-0 tty do not need to be interactive or have any
   console features. add that to the console plan.
```

Applied in: 1.6.14, 2.6.

12.3.16 The scope of Always Allow.

12.3.16.1 Record Always Allow in the preferences document, which
replicates and so outlives the tab, or let it last the tab only?

```text
== Tab only.
```

Applied in: 4.6, 11.

12.3.17 How image bytes reach the UI.

12.3.17.1 Have the UI fetch the provider's image URL (provider URLs are
temporary and the image host may not allow a browser origin), or ask for
`b64_json`, which puts the bytes in the AI worker's response? Which is
the first form?

```text
== The integration tests should use inline `b64_json` of low resolution
   `.png` test patterns drawn with hard pixel edges.
   Do not design server side fetching, but have it as a required open door.
```

Applied in: 1.6.12, 5.2, 5.7, 10.5, 11.

12.3.18 Media budgets.

12.3.18.1 Media budgets proposed: 256 MiB for `media_db`, the current
scene's refs only for the browser's files database, everything for the
server. Are those the numbers, or is this too soon?

```text
== Putting constants, with sane defaults, in settings.js for normal
   configuration of the services
   required is expected for all this, make that a general request.
```

Applied in: 2.4, 6.7, 6.9.

12.3.19 Compaction of turns.

12.3.19.1 Turns live in the metaverse by scene ref. Who decides to
compact: the agent by a token estimate against a setting, or the model
through a `turns_compact` tool?

```text
== The players current universe DB lives in the metaverse DB.
    - "metaverse" is like a bookshelf of experiences
    - multiple players can be tracked in multiple universes at the same time
    - the user may switch players. by default there is only one.
  Then the players current world DB to use is stored in the current universe DB
    - "world" is global state for an experience. these are standard games terms
  This is all required, update the plan.
   The default guidance and set up for the AI API shouldn't go past this. the
   AI API is expected to design scripts using the sqlite wrapper as a single
   door. DB admin, like
   this should be baked into the TS/PY sqlite wrapper and not left exposed to
   some AI slop script. Using heuristics is fine.
```

Applied in: 5.5, 6.6, 10.8, 10.14, 11.

12.3.20 Seeding the metaverse.

12.3.20.1 The server seeds the hyperposition's documents, the analyst
prompt and the world from the Python package when it creates a new
`metaverse`, and keeps the universe catalogue as documents under
`metaverse/universe/<name>`. Is the server the seeder, and are the seed
texts repository files?

```text
== yes.
  The AI API is given a bootstrap.js file to start with that knows
  how to replicate DB modification to and from the server. In an ideal world
  the server DB could simply be replicated deterministically using the existing
  DB wrapper replication code.
  it is OK if there is DSYNC. communication is only one way. on startup the
  page replicates from the server, and browser DB cache files should actually
  be invalidated if they are different than the server version and re-uploaded.
  that way the server is the ultimate source of truth. if the web app wrecks
  itself (and it may) in theory the server should be able to repair the
  saved DBs, and restore the web app to a stable state when it restarted.
  Make the reload on DB DSYNC a requirement of the prototype. That needs to be
  unit tested early. It needs to work for iteration time.
```

Applied in: 1.2, 1.6.7, 4.5, 5.6, 6.6, 6.8, 8.7.7, 10.9, 11.

12.3.21 Attaching the region.

12.3.21.1 Attach the current region to the universe connection as
`region`, one region at a time (ATTACH on the SAH pool VFS to be
verified). Is one region enough, or must several be attached, as the
earlier design's eight scenes were?

```text
== This layer of code is tutorial code for an AI API and it is expected
  to be edited by it. Have a table of universes in the metaverse. this
  is the only fixed schema. have a table of worlds (with a mutable schema) in
  any universe. have a table of regions (with a mutable schema) in any world.
  don't break down the DBs further in the seed config. allow the AI API to
  design new DB schema and add/remove DB using it as required to implement the
  experience. use a C identifier for all of the above so they are legal
  DB names. metaverse is "metaverse". the default universe might be
  "current_universe" for simulations based on scientific data and happening
  in the present day. Otherwise the name would correspond to the kind of
  fantasy requested, or simply designate a requested partition of realities.
  The world can be called "world" by default. Further details would have to
  be filled in by the AI API when the analyst has chosen a destination.

  the integration tests have to perform these operations using an integer
  based communication protocol that stubs out the AI API. that is how testing
  has to go. in deployment, this could just be part of an AI prompt it is too
  soon to write. the requirement to add to the docs from this response is
  that the AI needs MVC to implement the above and the tests need stubs
  that use the MVC to smoke test the baseline expected usage that will be
  asked of the AI API as well.
```

Applied in: 1.6.8, 5.1, 5.2, 5.5, 5.6, 6.1, 6.2, 6.6, 8.5, 11.

12.3.22 Protecting the engine's tables.

12.3.22.1 The AI runs DDL in universe and region databases that also
hold the engine's `meta`, `kv`, `doc` and `doc_head`. Have `sql_run`
refuse a statement that names those tables, by parsing the statement's
table names with SQLite's own `EXPLAIN`, or is the AI trusted?

```text
== engine tables:
  add one leading underscore to "engine" DB names:
    - the "_settings" DB is immutable
    - the "_files" and "_preferences" DB have immutable schema
```

Applied in: 1.6.8, 2.4, 5.5, 6.2, 6.9, 11.

12.3.23 Simulation steps.

12.3.23.1 The original plan had a server side TypeScript compiler for
the AI's scripts. The second design stored the AI's simulation steps as
JavaScript in the files database and ran them in the AI worker with `new
Function`, so nothing compiles at run time. Is JavaScript from the AI
acceptable?

```text
== No, this is wrong and has to be clearly updated. The AI API's scripts
  are not sent to the server for recompilation. Instead the AI uses its
  MCP interface to edit the JS live in the browser. And once done, it
  gets cached and backed up. TS is used to precompile the modules that
  the AI is not expected to edit. The AI is expected to have MCP controls
  to run and debug the .js it is editing using MCP so that it can diagnose
  stepping problems in a simulation. it is not required to write a simulator
  but it needs to be tested using the TAP test protocol using the integer
  based stub AI conversations.
```

Applied in: 1.6.10, 2.5, 5.5, 5.6, 8.5, 11.

12.3.24 When settings take effect.

12.3.24.1 Settings travel in `hello`, so a `settings.put` in debug mode
takes effect at the next connection, not at once. Acceptable?

```text
== settings should be served via the settings.js module which will have an
   id based lookup mechanism. and be deep frozen when not loaded in debug
   mode (as is normal in development.) it should load after "error_handler.js"
   which has no other job than to catch exceptions, resource load failures and
   other errors and replace the screen using document.write to present
   any error with a callstack in a big `<pre>` block and top the app.
```

Later: Refined by 12.5.8.1.
Applied in: 1.2, 1.6.9, 2.4, 6.9.

12.3.25 Secrets in hello.

12.3.25.1 The provider key rides the same connection as everything else:
plain HTTP on localhost, or HTTPS with Basic authentication on the LAN,
with no other gate. Confirm.

```text
== confirm. audit to follow.
```

Applied in: 4.4, 5.2, 9, 10.12.

12.3.26 The debug flag on Windows.

12.3.26.1 Pass `--debug` through `xsjs_start.ps1 --debug` into the ttyd
command, and have the status script report it. Is that the argument?

```text
== no, debug is a settings.js thing. it gets disabled for releases.
```

Applied in: 1.6.9, 2.4, 7.5, 11.

12.3.27 One tty.

12.3.27.1 The first round answered the one tty or two question with "2",
read as the second alternative: one connection, dash under a pty the
server forks, relayed as JSLB blobs, and the original plan's sentence
about two ttys retired. Confirm.

```text
== no, i have always explicitly asked for the opposite of this, and require
   explanations before plans change. in recent responses i have indicated that
   the dash tty should be entirely optional. (and it should for any sane
   security architecture going forward). Being able to launch PY directly
   is important because one day that process may become a C/C++/Rust webserver
   component with a hardened and optimized implementation. Dash is just for
   development in debug mode by me and the AI API.
```

Applied in: 1.6.2, 2.1, 10.2, 11.

12.3.28 The whitelist rule.

12.3.28.1 The first round asked for a change to the project rules about
the reformat whitelist. The rules are the maintainer's, so they were not
edited. What is the wording?

```text
== Add "Do not suggest additions to the whitelist." please.
```

Applied in: the project rules, not this plan.

12.3.29 One strings file.

12.3.29.1 Keep every Python and TypeScript string in `i18n/en-US.json`,
read by both, and leave PowerShell's `i18n.psd1` as it is. Confirm.

```text
== yes.
```

Applied in: 2.4, 7.1.

12.3.30 Log forwarding.

12.3.30.1 Forward the page's console output to the server as `log.put`
only in debug mode, into the server's `log` database, with a ring of
`log_ring` lines in each thread. Confirm the policy.

```text
== There is no log_* DB/namespace, there is only the verbose_* DB/namespace.
   `verbose.log()` would be a good name, and then the log operation
   would be gated by the verbosity level. i explained the verbose module
   in detail, that is what i want for logging, telemetry, dumps. put that
   in the docs.
```

Applied in: 1.6.4, 7.2, 10.17, 11.

12.3.31 Version floors.

12.3.31.1 With no container, the only runtime is WSL's Python 3.14 and
SQLite 3.46. Keep the floors Python 3.12 and SQLite 3.38 as
documentation only, or drop them until the other OS flavours arrive?

```text
== drop them until the other OS flavours arrive. remove version checks they
   would be too brittle at this stage od dev.
```

Applied in: 1.6.16, 6.1, 10.3, 11.

12.3.32 restart and source.put.

12.3.32.1 `system.restart` execs Python itself and `source.put` writes
the package it execs, both debug mode only, as the one way the AI can
rewrite the server from the page. Does "rip out" cover them?

```text
At this point the request to "rip out" out something could have been any
of 10 i might have made so far. a request to "rip out" is a request to avoid
ossification of example code.

as i type this, i want bootstrap.py to be able to download a new main loop
PY file from the web app and serve it after a restart. in this manner, the AI
API can try to recover the server when only the bootstrap.py file is intact.
It can send over multiple main loop files and examine the outputs as needed.
the main loop is responsible for handling JSLB and there is a stock JSLB
dispatcher provided as described in the plan. bootstrap.py should be immutable
when not in debug. That means the player may have to reload a few times, but
the AI should be able to recover/clean up/admin the box without needing someone
to log in over Dash and clean up for it. This should all be fairly bare bones,
and the AI API should normally have no business mucking with the PY files served
from the back end. this is dev MCP only. the main goal is having only one
AI in a single conversation in the browser able to debug and work globally
without asking the user to copy and paste or auth.
```

Applied in: 1.6.13, 5.5, 7.2, 10.2, 10.18.

12.4 The audit, 2026-10-18.

An audit of every request of the maintainer across the planning rounds
graded each as A (unsatisfied or modified without cause), B (unsatisfied
or modified with cause but without confirmation), C (confirmed withdrawn
or modified) or D (satisfied). The maintainer answered the A and B
findings. Each entry is one finding, condensed, and the maintainer's
literal answer; section 13 grades the same findings against this plan.

12.4.1 A: unsatisfied or modified without cause.

12.4.1.1 Verbose module as the logging module. The original plan
specifies a `verbose` module with levels 0 to 2 and an internal log
history. The second design kept `verbose.py` but put the logging that
reaches the page and the database under a `log` namespace:
`engine_log.py`, `log.sql`, `log.put`, `log.line`, `log.follow`, the
`log_tail` tool, `log.ts` and a `log_ring` setting. No reason was given
and no question asked. The second round (12.3.30.1) rejected it.

```text
= enact this new api please.
```

Applied in: 1.6.4, 11.

12.4.1.2 A view of the page's own console output. The second design
captured `console.*` into a ring and forwarded it to the server in debug
mode; the only in page view was the xterm.js view of dash. No view of
the page's own console output was specified, and the omission was not
stated. The second round (12.3.15.1) treated "the debug console"
(ctrl-0) and the tty views (ctrl-1 to ctrl-n) as different things; the
phrase is ambiguous and the reading taken was never confirmed.

```text
== I only need one xterm.js instance for the root console. I also want simple
   debug pages displaying the json part of all recent JSLB I/O in some
   giant `<pre>` block with the modules dummied out with a `<module "n"=3>`
   debug tag. (this is new syntax again.)
```

Applied in: 1.6.14, 2.6, 3.11.

12.4.1.3 Task forwarding. The original plan says "JSLB can be sent to
the first thread with embedded forwarding instructions". The first and
second designs said forwarding "is not in the first draft" and offered
two tasks from the caller instead, with no reason and no question. The
second round (12.3.7.1) restated the need: a handler enqueues a second
JSLB in a different form at a different destination.

```text
== encode/decode needs to be proven before the format is used for anything.
   at that point forwarding is accomplished by passing a decoded object from
   an incoming decoder-recipient, changing nothing and passing off to the
   encoder-recipient. this is how logging gets from the UI to the AI to the
   server, seeing as it looks like the AI thread will have the non-dash tty.
```

Applied in: 1.4, 1.6.3, 4.3, 8.7.2, 11.

12.4.1.4 Multiplayer, one tty per additional player. The first design
kept it as something nothing forecloses; the second dropped every
mention. Minor, but it bears on the tty count.

```text
== this is exactly the kind of thing i need harvested into [the third design document]
```

Applied in: 10.1, 11.

12.4.1.5 Two English names per identifier. The API stubs declared
`main(argv)` in bootstrap.pyi and mcp_stdio.pyi, `LineDecoder.feed` in
jslb.pyi and the handler `mcp` in engine_mcp.pyi with one name each,
without stating an exception.

```text
== update [the rules file] the "two names" rule is overridden any time the
  maintainer specifies a different identifier.
```

Applied in: 7.1.

12.4.2 B: unsatisfied or modified with cause, without confirmation.

12.4.2.1 Two ttys, the dash console an optional second connection. The
original plan says "At first only 2 tty should be required"; the first
round answered "2" (12.2.6.1) and "don't require a console log in"
(12.2.15.1). The second design relayed dash inside the engine tty as
JSLB blobs, reading "2" as the question's second alternative, and
rewrote the whole document, the API and the transcripts around it.
Confirmation was asked in 12.3.27.1, which rejected it.

```text
== ignore previous instructions due to being confusing. having xtrem.js
   available os a debug overlay for the dash console is a requirement. this
   requirement is being put in now to enforce architectural design.
   having debug overlays for the other ttys used by the page that show the
   JSLB with `<blob "n"=2>` style.
```

Applied in: 1.6.2, 1.6.14, 2.6, 3.11, 11.

12.4.2.2 Verbose wraps subprocess. The original plan has `verbose` wrap
subprocess. The second design dropped the wrapper "with the PY to SH
ban", citing the answer to 12.2.10.1. Never asked. The second round
(12.3.30.1) re-asserted the module as described in the original plan.

```text
== you are chasing implementation details i never was aware of. i had no
   idea SH was required by PY, because I assumed PY could just make a sys-call
   without running a shell. And that the "verbose" module was just the kind
   of place to do loud or quiet external system calls. seeing as how
   "subprocess" was already taken.
   The only part of my security architecture I would like to be able to enforce
   right now is "not exposing SH or PY directly to a socket except through
   the JSLB dispatcher single door. That will have to be hardened and so
   it doesn't make sense for random sh fragments to be creeping in there.
   I am trying to avoid the nightmare that comes from having data structures
   shared between PY and SH and don't think SH scales so all data structures go
   in PY. Now, if you still need to call SH from PY because there is no other
   sane route under ubuntu than do so. That is the real goal, update the docs
   to explain.
```

Applied in: 1.6.4, 2.1, 2.3, 7.2, 9, 10.12, 11.

12.4.2.3 All databases on the AI thread. The second design put every
database on the WASM worker with the AI worker as "owner on paper" and a
proxy whose every method was one task, because a long query would stall
the AI worker's event loop. Asked in 12.3.6.1, which answered: merge the
AI and WASM threads if possible, otherwise move the AI, MCP and WASM
code to the WASM thread.

```text
== it sounds like i repeated my self twice and was ignored. yes, this is a
  change of plans. having an AI event loop stall due to the DB would be a
  great problem to have. the AI stalls are so much larger the DB stalls
  should get lost in the noise. the AI API should be able to enable verbose
  and optimize the stalls, and or ask for architectural assistance.
```

Applied in: 1.6.1, 2.2, 5.5, 11.

12.4.2.4 Task bodies synchronous, the queue the only synchronization
tool. The first round answered yes (12.2.20.1). The second design let an
AI thread handler return a promise because `ai.say` spans many awaits.
Asked in 12.3.7.1, which rejected it: one JSLB dispatched at a time,
re-enqueue, sleeping tasks, a timeline reconstructible from the queue's
log alone.

```text
== I will become hysterical if you design one single synchronization
  mechanism (use a single promise) outside my task manager. if a task
  needs to wait on a promise it has to do so under the purview of the
  task manager. exceptions to this rule will be audited for and will result
  in architecture churn, which is the worst.
  I know uptight architecture isn't fun, but having ideal architecture is what
  is golden about this project, and delivery of working code is second the
  second step after that. No code has been written, don't sell me short before
  we start.
```

Applied in: 1.3, 1.6.3, 4.2, 8.6, 11.

12.4.2.5 Document-Ref as the version appended to the KV key. The first
round described the example `forest/trees03/scene/53` (12.2.14.1). The
second design made separate `doc` and `doc_head` tables, fixed the depth
at `<db>/<kind>/<name>/<version>` and rewrote the example with five
segments, because the database is then found without a lookup. Asked in
12.3.3.1, which rejected it as over fitting an example and gave
`/$db/$id/$version` and `$id/$version`.

```text
== im getting PTSD from seeing that example again after saying it was wrong.
   Please use  `/$db/$id/$version` and `$id/$version` as described. Where
   $id may contain arbitrary path components.
   this is violation of the most basic part of the doc API design. if you
   hardcode path segments then you have re-invented a F'ing table and
   reimplemented it on top of a table.
   This is a development environment, a template, stop designing things and
   start building the apis i need from bottom up.
```

Applied in: 1.1, 1.6.5, 6.4, 11.

12.4.2.6 Replication of the AI's own tables. The second design
replicated the engine's tables by row log and pushed the AI's own tables
whole by snapshot after a turn, because those tables have no `seq`.
Asked in 12.3.2.1, which rejected it: always over JSLB, modifications
forwarded as they happen, a string to string table replicated by the
substrate as the first unit test.

No answer in the maintainer's reply to the audit; decided by 12.3.2.1.

Applied in: 6.8.

12.5 Later answers, 2026-10-18.

The audit's answers produced the third design document, which is this
file's first form, and a third file of thirty two questions. The
maintainer answered twelve of them in one message, quoted here in
pieces, each piece after its question. The message opens with an
instruction to the AI, quoted first. The twenty questions with no answer
are in section 14.

12.5.0 The opening of the message.

```text
Add these to the last All [the third design document], then update the APIs and DATA,
regenerate the test data anything that needs to be made new and current.
From [the third question file]:
```

12.5.1 Reload on failure against Project Direction 1.3.

12.5.1.1 The second round (12.3.12.1, 12.3.20.1) made a full page reload
the tested recovery path and the reload on desync a requirement. The
rules' Project Direction 1.3 says never retry by reloading the page,
written for the old bootstrapper's test. Does the new design, which
reloads, stand?

```text
#1 yes new design, resync is reloading client. that is normal
for games.
```

Applied in: 1.2, 4.5, 11.

12.5.2 Documents as KV rows.

12.5.2.1 Store a document as the KV row keyed `$id/$version` in database
`$db`, with `doc_put`, `doc_head` and `doc_get` as sugar over `kv_*` and
no document table; `doc_head` would be a prefix scan for the highest
version. Or a document table?

```text
#2 whatever has best perf.
```

Applied in: 1.6.5, 6.4, 11.

12.5.3 What "the only fixed schema" covers.

12.5.3.1 The second round (12.3.21.1) made the metaverse's universe
table the only fixed schema. The plan also puts the substrate's own KV
tables in every database the substrate opens, treating them as the
substrate and not as experience schema, so that Document-Refs resolve
anywhere and blobs can be stored in a named database, and seeds `world`
and `region` tables of mutable schema in each universe. Is that
acceptable? The alternative is KV tables only in the engine databases,
which would change Document-Refs into AI databases, the reference
prefetch and the media tiers.

```text
#3 yes. also define Key-Value-Ref
which is just a Document-Ref without a version. so that scripts can
create new settings that are not full blown documents. The built in
tables are a part of the substrate module the AI should never need to
see. some prefix or suffix to prevent collsiioons with engine tables is
required. so it is fine for the tables to be automatically created on
use in each DB. rememeber the scripts re the DB admin, the plan for DB
admin here is a bootstrap.
```

Applied in: 1.6.5, 1.6.6, 5.5, 5.6, 6.2, 6.4, 11.

12.5.4 The sleep API of the task manager.

12.5.4.1 A handler returns `task_sleep(state, wait_ids, then_type)`; the
queue enqueues `then_type` with `state` and the replies once every
awaited reply has arrived; one transaction per dispatch, so a sleeping
task holds no database. HTTP is a port that answers `http.request`
lines. Is that the shape?

```text
#4 a debug flag that forces the local threads
JSLB queue to be fully empty (run to completion) before reading inputs
would cause it to be more deterministic. call that the task queues
"syncronous" mode.
```

Applied in: 1.3, 1.6.3, 4.2.

12.5.5 Replication as forwarded operations.

12.5.5.1 Forward each committed `kv_put`, `kv_delete` and modifying
`sql_run` to the server as the same line, one way during play, with no
server push to an open tab, and replace a differing file at start; or
row level replication of the AI's tables, or a server push?

```text
#5: operation forwarding is required, it may be used
as a test driver early on.
```

Applied in: 1.6.7, 6.8, 11.

12.5.8 The settings pipeline.

12.5.8.1 Build `settings.ts` from settings.json at build time, deep
frozen outside debug mode, and load the same file into `_settings` on
the server, so `debug` is one key read by both; a `settings.put` then
takes effect on the server at the next `hello` and in the page at the
next build. Or must the page receive settings in `hello` instead?

```text
#8 don't build `settings.json` from
`settings.ts` unless required. add non-essential error handling to
utility.ts, along with misc single door routines. load the ui strings
after that too. """

<script src="../scripts/error_overlay.js"></script>
    <script src="../scripts/utility.js"></script>
    <script src="../scripts/ui_strings.js"></script>
    <script src="../scripts/settings.js"></script>

"""
```

Applied in: 1.6.9, 2.4, 11.

12.5.9 The representation of turns.

12.5.9.1 Make each turn a document `turn/<scene ref>/<n>`, or make a
scene's conversation the version history of one document `turn/<scene
ref>`, turn n being version n, which fits "each scene is a new
conversation" and costs `kv_delete` of versions on compaction?

```text
#9 the hyper position can create a new scene for each conversation,
and use the turn table as described. however, it is up to the AI API to
write scripts that populated the universe DB, world DB, region DBs.
```

Applied in: 1.6.6, 5.6, 6.2, 6.3, 6.6, 11.

12.5.12 The reference table in a document.

12.5.12.1 Top level integer keys hold reference strings, `{"$ref": n}`
anywhere in the body names one, equal strings share an entry, and the
round trip is identical. Not stated: whether `$ref` is the key name,
whether a reference may appear inside a nested document's own table, and
whether media keys and Document-Refs share the table.

```text
#12
all header objects in json formats need to have integer keys. so a
reference to a header is an integer. the headers have standard formats
and can be discovered by probling the integers linearly starting at 0. 0
should be the file header. [1]... would be the blobs, or external
references that need to be iterable in a standard way, that can just be
a simple array of strings merged with an object with non-integer keys.
```

Applied in: 1.6.5, 3.2, 6.4, 11.

12.5.13 The DevTools driver.

12.5.13.1 `devtools.py` is specified by its API. The relay inside
`xsjs_screenshot.py` exists. Is the existing relay the implementation of
that API, or is `devtools.py` written fresh to it? (The first design
chose the relay because it existed, which the rules now name as the
wrong reason.)

```text
#13 keep it then.
```

Applied in: 1.5, 8.2.

12.5.14 The debug tag and the overlay.

12.5.14.1 The maintainer wrote `<module "n"=3>` once and `<blob "n"=2>`
once. The plan takes `<blob "n"=K>` with K the blob header index. The
overlay shows the last lines of a tty in both directions. Does DATA/
adopt the tag in place of `<N blobs>`, and does the ui-ai lane get an
overlay too?

```text
#14 sorry use ``<blob "n"=2>`
```

Applied in: 1.6.14, 2.6, 3.11.

12.5.15 The last line regression test.

12.5.15.1 The rules' Project Direction 1.1 keeps the test that keys on
the last line of a process exiting right after printing it. Under JSLB
in raw mode the server never exits right after output except on `error`.
Does the rung become "the `error` line before exit 1 arrives whole"?

```text
#15 this was a whole
fiasco that ended with you doing busy work to sync before a disconnect.
you are still going to have to set timers and be aware of the failure
modes and test around them.
```

Applied in: 1.6.15, 3.10, 4.7, 5.3, 8.2.

12.5.16 The verbose API.

12.5.16.1 The plan named `verbose.log`, `dump`, `history_get`,
`follow_add` and `call`, the database `_verbose`, and the lines
`verbose.put`, `verbose.line`, `verbose.follow`, `verbose.tail` and
`verbose.level`. The second round (12.3.30.1) named only
`verbose.log()`. Are these names right?

```text
#16 don't add things until the are required.
```

Applied in: 1.1, 6.9, 10.16, 10.17, 10.18, 11.

## 13 A and B class requirements

Each item is an A or B class finding of the audit of the planning
process (12.4), with the maintainer's answer where there is one and
whether this plan satisfies the original request. "Satisfied" means the
request as the maintainer stated it, or restated it in an answer, is
what sections 1 to 9 build.

13.1 A, unsatisfied or modified without cause.

- The verbose module renamed to a `log` namespace. Answer: enact the
  verbose API. Satisfied: `verbose` is the one namespace (1.6.4, 7.2),
  trimmed to what stages need, the rest in 10.16 and 10.17. Record:
  12.4.1.1.
- A view of the TS console in v0. Answer: one xterm.js for the console,
  `<pre>` pages for JSLB. Satisfied: 2.6. Record: 12.4.1.2.
- Task forwarding dropped. Answer: forwarding is the decoded object
  passed unchanged. Satisfied: 4.3, and replication uses it (6.8).
  Record: 12.4.1.3.
- Multiplayer dropped. Answer: harvest it. Satisfied as a recorded
  design: 10.1, with the tty numbering of 2.1 reserved for it. Record:
  12.4.1.4.
- One name identifiers in the API stubs. Answer: the rule is overridden
  by the maintainer's identifiers. Satisfied: the rule is in the rules
  file with that override; the stubs use two names except where an
  answer names the identifier. Record: 12.4.1.5.

13.2 B, unsatisfied or modified with cause, without confirmation.

- One tty instead of two. Answer: two ttys, the console optional.
  Satisfied: 2.1, 2.3. Record: 12.4.2.1.
- Verbose without its subprocess wrapper. Answer: `verbose` is where
  external calls go. Satisfied: `verbose.call` runs the console's dash
  (2.3, 7.2). Record: 12.4.2.2.
- Databases on a WASM worker with a proxy. Answer: all databases on the
  AI thread. Satisfied: 2.2. Record: 12.4.2.3.
- Promises in AI handlers. Answer: the task manager only. Satisfied:
  4.2, 8.6. Record: 12.4.2.4.
- A fixed Document-Ref depth and document tables. Answer: the grammar as
  given, `$id` free. Satisfied: 6.4, with the performance choice.
  Record: 12.4.2.5.
- Snapshot replication of the AI's tables. Answer: forwarded operations.
  Satisfied: 6.8. Record: 12.4.2.6.
- The settings and preferences databases removed. Answer: `_settings`,
  `_files`, `_preferences`. Satisfied: 6.2. Record: 12.3.22.1.
- Scripts run by `new Function` with no MCP edit, run or debug tools.
  Answer: MCP edits, runs and debugs. Satisfied: 5.6, with `kv_put` as
  the edit and `script_run` and `script_debug` as the controls. Record:
  12.3.23.1.
- The new source files not whitelisted. Answer: the rule. Satisfied: the
  globs are in the whitelist and the stubs pass the check; the rewrite
  of API/ and DATA/ to this plan is done in the same pass. Record:
  12.3.28.1.
- The `from` exception for i18n not in the rules file. No answer. Not
  satisfied in the rules file, which is the maintainer's; 7.1 records
  the exception.
- The tappy consumer left out. A later answer superseded it with the
  project's own modules. Satisfied: 7.2, 8.1. Record: 12.3.13.1.

## 14 Points the maintainer never confirmed

The third question file asked thirty two questions, ranked by the rework
a different answer would cause. Twelve were answered (12.5). Twenty were
not. For each, the design kept its assumption, trimmed by the answer
"don't add things until they are required" (12.5.16.1). An agent that
meets one of these decides nothing: it uses the assumption, and asks the
maintainer before building anything that would be reworked if the
assumption is wrong.

14.1 The console tty mechanism. Assumption: ttyd runs with `--url-arg`;
a connection with `?arg=console` runs `bootstrap.py ... console`, which
in debug mode runs dash through `verbose.call` and otherwise exits 1;
the AI worker owns that socket and relays it to the UI's xterm.js (2.3,
4.7). Rework if ttyd should run two commands, or the UI should own the
socket: the start script, bootstrap.py's role handling and the console
lane.

14.2 Script run and debug. Assumption: `script_run` runs a script with
`new Function` in the AI worker against the substrate's frozen API and
returns the value or the exception and the verbose lines, and
`script_debug` is the same run traced at verbose level 2 (5.6). The
answer in 12.3.23.1 asks for run and debug controls and says no more.
Rework if stepping or breakpoints are meant: a script interpreter or
DevTools in the loop.

14.3 The UI's part in the first replication test. 12.3.2.1 asks for a
string to string table replicated from the AI worker and the UI, and the
UI has no SQLite (12.2.3.1). Assumption: the UI thread submits the
modifications as tasks, forwarded to the AI worker's database and then
to the server (6.8, 8.7.7). Rework if the UI must hold a table of its
own: a UI side substrate.

14.4 The permit set. Assumption: `console_run`, `source_put` and
`system_restart` are the permit tools (5.5). Rework: tool metadata and
the stub conversations.

14.5 The provider key variable. Assumption: `XSJS_PROVIDER_KEY` in the
environment of the ttyd process, passed by the Windows start script from
the user's environment (5.2, 7.5, 9). The name is a choice.

14.6 Image URLs. Assumption: `media.fetch` stays beside `b64_json` for a
provider that answers a URL (5.7). Rework if the first version is
`b64_json` only: one line type and one UI handler fewer.

14.7 The seeds. The server seeds the hyperposition document, the
analyst's prompt document and the keys `/metaverse/player`,
`/metaverse/world` and `/metaverse/scene` when it creates the metaverse
(6.6). The plan does not say where the seed texts live or in what form.
Assumption: repository files `python/seed/<id>.json`, each a document in
its encoded form (6.4).

14.8 Preferences in the first version. `_preferences` exists by
12.3.22.1 and Always Allow lasts the tab by 12.3.16.1, so nothing writes
it. Assumption: the database exists, empty, with its schema (6.2).

14.9 The current player. Assumption: the player in use is the
Key-Value-Ref `/metaverse/player`, and a universe row is `(name, title,
player, world)` (6.6). Rework if a player table is wanted: a second
fixed schema.

14.10 The meaning of "MVC". 12.2.2.1 says the design is not MVC, and
12.3.21.1 says the AI "needs MVC to implement the above and the tests
need stubs that use the MVC". Assumption: the second is read as the tool
layer of 5.5 and the stubs of 8.5 (5.1). Naming only.

14.11 The TAP line. Assumption: each case is sent as `tap.line
{language, text}` carrying the TAP text, and the consumer returns plan,
pass, fail, skip and whether the stream is well formed (8.1). Rework:
the consumer and the test page, if a structured result is wanted.

14.12 The highlighted report. The original plan asks for colour on HTML
output with the whole failed line highlighted, and 8.1 keeps it in
`test.html`. The rules ban unrequested style. Assumption: it stays
requested.

14.13 Model names. 12.3.4.1 names xAI and no models. `API/settings.json`
holds `grok-4` and `grok-2-image` as placeholders (5.2, 6.9).

14.14 Database creation tools. Assumption: `db_create` and `db_drop`
are tools (5.5) and the AI may create a database outside the universe,
world and region ones. Rework: tool limits.

14.15 Wire traffic in the server's verbose. In debug mode the rendered
wire traffic is forwarded to `_verbose` (2.6). A 128 MiB upload renders
as one line, but a turn is many. Assumption: verbose level 2 and the
setting `verbose_forward` gate it.

14.16 The console lane's owner. Assumption: every console keystroke goes
from the UI to the AI worker to tty 0 and back, so the AI worker is the
only owner of sockets (4.7). Rework if the UI thread may own tty 0: one
socket moves and `console_run` relays the other way.

14.17 The xterm.js alternative. 2.6 keeps "the headless package is the
alternative for feeding, chosen once by the research result". The rules
ban fallbacks in code. Assumption: this is a design alternative chosen
once by a research result, not a runtime fallback, and the word is read
that way.

14.18 Reserved tty numbers. Assumption: tty 0 is the console, 1 the
engine, and 2 and up are reserved for players (2.1, 10.1); the role in
`--url-arg` names them: `console`, none for the engine, `player2`
onward.

14.19 A ttyd with `--srv-buf-size`. Not in the third question file;
found while writing 0.4. 3.10 and 7.5 start ttyd with `--srv-buf-size
1048576`, and `xsjs_install.ps1` installs ttyd in WSL with apt. The apt
package, 1.7.7-4build1, has no such option, so ttyd would refuse to
start. Only the build from source at `../ttyd/build/ttyd` offers it. No
decision is recorded. Ask the maintainer whether the install script
builds ttyd, whether the option is dropped, or something else.

Two of the twenty need no assumption. The question of two threads is
settled by 12.4.2.3 and 12.3.6.1. The question of a `settings_sha256` in
`hello` refusing a page built from other settings is moot: 12.5.8.1 and
12.5.16.1 dropped it (11).

## 15 The maintainer's original statement of requirements

The text below is the first document the maintainer wrote for this
project, committed on 2026-10-17 and quoted without change except for
trailing white space. Every later decision in section 12 refines or
replaces parts of it; sections 1 to 11 say which. Its unfinished JSON
Pointers section was replaced by Document-Refs (12.2.14.1).

````text
# hyperposition-engine

A cloud stack for "vibe coding" an experience and interacting with it.
The experience is presented as large still images in a web browser made using generative AI from a database of facts describing an experience.

The experiences are in-browser using bare bones .html, .css and .js
content. The back end is ttyd+py+dash server-based stack for "vibe coding" an experience and interacting with it. administration scripts
are expected to support serving it from an ubuntu container on any platform.

The ttyd project is being used as a stepping stone. First ttyd is made
to serve the hyperposition-engine.html page. Then the normal ttyd+dash
protocol ttyd serves to xterm.js is recycled as the "console" module
in hyperposition-engine.js. The console module allows dash commands to be run with binary I/O captured via the ttyd protocol in binary mode.

xterm.js is minimally adapted so hyperposition-engine.html can run it offscreen with the page showing the console I/O. with stdin hidden, stdout shown. the dash process providing the console must be
reasonably sandboxed. All further ttys allocated would communicate with back end pure PY using a new wire format called JSLB defined below.

Once logged in, the hyperposition-engine.html uses the JSLB format everywhere. (Except the console.) A collection of sqlite databases are used for substrate. The "web-worker-ai" web worker allows an AI to use MCP to control the experience.

The experience starts with a blank black web page and a single subtitled remark "How can I help you?" The user's responses are then used fed to an AI (talking to an MCP server in the browser on a worker thread) to guide the user as requested through different experiences. This starting point is called the hyperposition and is controlled by a very bored British female AI psychoanalyst.

## Console

The AI has MCP access to the Dash shell. This allows it to do management work on the back end. e.g. checking the logs of the python server after a crash. The user should be able to interact with
the admin console as well as the AI in debug mode. the AI may be
sandboxed in a web worker and have to ask permission to talk to
the admin console.

## Wire Format JS-Line-Blobs, JSLB

The standard wire communication protocol is binary mode json lines ending in CR alone, with interleaved blobs. Integer indices into a line contain headers. Either the first char of a name or the full name are acceptable. Full names are used in debug mode.

Index 0 is the Line-Header.
    "t"/"type"    - Type used for breaking changes (="utf-8")
    "v"/"version" - Version used for breaking changes (=0)
    "k"/"key"     - * Optional. Key in a KV store
    "b"/"blobs"   - Number of blobs (=0)


Indices 1+ are Blob-Headers. They add "s"/"size" to the Line-Header.
    "v"/"version" - Version used for breaking changes (="0")
    "t"/"type"    - Type used for breaking changes (="utf-8")
    "k"/"key"     - Key in a KV store (="")
    "s"/"size"    - Data size in bytes (*required)
    "d"/"data"    - * Never serialized. An owned data array.

```txt
{ // ...
  "0":{"v":"1","t":"tile","k":"quest/forest03.json"}
  "1":{"t":"png","k":"quest/backpack.png","8732763"}
  "2":{"t":"png","k":"quest/companion.png","8732764" } // ...
  }<blob-1><blob-2><blob-3>
```

After reading the json line the recipient is responsible for reading the blobs as described by the blob headers, putting them into byte array storage, and fixing up the "d"/"data" reference in the blob headers to point to the allocated array.

This format requires a single door encode/decode function for each
language. The encode functions take a json object to be written as
a single line. They remove the "d"/"data" field from the blob headers
and append them as blobs after the line with no other control bytes
interleaved. Then, the decoding functions are required to restore
identical json with binary identical blobs from the data which was
stored as described above. this requires a json representation to
load into that supports binary arrays. e.g. JS.

this format is designed for 2-way non-blocking communication, unlike
the console and its use of dash. messages are sent to the network
as they are composed. large files may be transferred simply by sending
them with a header instructing the other side to store them in
a given DB. responses must be matched by id.

the "syscall" dispatch mechanism PY uses in its main loop requires
looking up a "line handler" by "t"/"type". then the line handler
is invoked with the json object's keys passed as `**kwargs`. the
`**kwargs` can be passed around and used as a collection, and the tool to convert a JS object to `**kwargs` could be used on sub-parts
of the JSLB object to pass that part to another subroutine. In this
manner a suite of testable functions that take `**kwargs` can
be assembled into a test suite without going via json and having
to debug all that. if there was a python version of json that could
just be passed as `**kwargs` at any point in the object hierarchy
and looked like python when you used it, that would be ideal.

On the JS side, the same type based plugin line-dispatch syscall
mechanism is required. As an example, this allows logging to be
registered for and sent from the server to a diagnostic page.

## sqlite

Chosen as a dynamic AI command language for scene data, typically
using Entity Component System or ECS structured records.

- utf-8 line driven
- has KV wrapper with 128KiB blowout to fs cache

https://sqlite.org/wasm/doc/trunk/demo-123.md

## JSLB task queue module

Each JS thread needs a JSLB queue. JSLB tasks arrive in the unencoded JSLB JS format. They may or may not have been encoded and decoded by transmission between threads.

Access to a DB is only allowed by executing a task. Specifically, when the task queue has already dispatched the task to the thread owning that DB (and perhaps others used at the same time). Large amounts of processing, touching more than one DB, may be requested in a single task (the UI thread still needs to be 200Hz when possible) without requiring subtasks to redispatch to other databases. The task dispatch mechanism is intended to be large grained, for things like
"""the user clicked at X, Y""" instead of """set /forest1/sdf/4/"""

When multiple threads are required to perform a task, JSLB can be sent to the first thread with embedded forwarding instructions to have that JSLB marked up and sent along to additional threads. For example, the JSLB may have an optional diagnostics request embedded in a certain message type.

- DBs are assigned to threads, by default "worker-ai".
  - Thread I/O is JSLB ending in CR with interleaved blobs.
- The files DB is a KY store on the main thread.
- Scripts may be kept in any DB.
for now, the AI thread will have
- max 1 task per DB at a time.

the API for a tasks should abstract whether it is performed in the same thread or in another worker. as long as the thread is the correct owner for the DB is should be allowed. the first draft does have to have a web worker.

## Algorithm

1. The player initiates interaction. Time always stops.
2. A JS handler optionally updates the page or notifies the AI.

  User ---> JS ---> html
  User ---> JS ---> AI

3. The AI interacts with the database directly or via JS.

  AI <--> MCP <----------> SQL # { utf-8 sql, .ts, .bin }
  AI <--> MCP <--> JS <--> SQL # experience step
  AI ---> MCP ---> TS compiler # server-side TypeScript

4. Then it updates the html, possibly with a new picture or scene.

  AI ---> MCP ---> JS ---> html # render step

5. The player is presented with an updated page.

## Terminology

- each scene is a new "conversation" with a new establishing shot.
- each scene has a database which references the files.
- compaction is possible. crossfades stream in.

- an experience is made out of a series of scenes.
- it has media files and a collection of entity databases.

- the experience terminology is as follows.
  - multiverse: a catalog of separate experiences.
  - universe: a specific experience design.
  - world: the current experience state.
  - region: everything in your area.
  - scene: a location.

## Experience Design

- by default, time stops when the player stops
- by default gameplay is 2.5D
- service provides self designed generative AI experiences
- players are guided into experiences within their multiverse

When the hyperposition-engine loads with no scene selected, then
it loads a scene known as the "hyperposition." It contains nothing
but wisps of fog and a few inexplicable bright lights. The engine
bears this scene's namesake. It is the one scene that the player
is unable to modify. In this scene the player meets the AI analyst
who tries to determine the right universe to send the player to.
The analyst has admin control over the metaverse and expected to
perform requests as non-judgementally and efficiently as possible.

The design of the Myst Game, with basic rpg elements added is
a good template for slow moving 2.5D. Multiplayer, turn-based
strategy games need to work too. Multiplayer may require a
rewrite of the backend in C++ and for now it is more important
to design and prove the back end's algorithms and operation
than it is to slow down and think about multiplayer and C++ just
yet.

## System architecture

The front end is JS and the back end is PY. That division
is permanent.

And SH should not be used outside of admin
scripts for installing/uninstalling/starting/stopping the
service. There should be a POSIX parallel to the powershell
at the top level in xsjs and I should be able to test the
lifecycle using scripts with the same names as the top level
.ps but with .sh endings. The test for this needs to be
automated to run in a docker container inside WSL. keep the xsjs
name for now on the back end. Because the hyperposition-engine
is just one application of the xsjs back end administration
ttyd based tool suite.


The new html app being written to serve on the front end is
called the hyperposition-engine because it is designed to do
this one job, instead of being designed to serve custom webpages
in general.

Meanwhile, all the JS is editable by AI over MCP and will be
backed up immediately to a front end and backend DB. The
SH and PY should be effectively immutable to the web app. The
web app does have admin console access via ttyd+dash but that
is only intended for debugging and may be disabled. in debug mode
the AI can do things like rewrite the bootstrap.py and reboot
the server while running within the web page. It has to be centralized so the debugging AI has access to all data in one conversation.

Further ttys requested should be served by python and not dash.
There should be no dependency on the Unix command line. Instead
the PY scripts need to use the PY system modules to do everything
in PY. Add these modules:
  - verbose : wraps subprocess with a verbose level and different
    flags and handling depending on the verbose level. level 0 calls
    commands with no good news wanted and allows the output to go
    to stderr/stdout as is. level 1 adds basic .md formatting
    to the logs generated by these called. level 2 is just everything
    raw again with verbose flags passed to subcommands. also keep all
    the logging routines here and an internal log history of
    N lines generated at level 1 so the front end could ask for it.
  - substrate : this module is a single door to sqlite module/dbs.
    adds a file cache layer for blobs over 128MiB. Add a KV accessor
    so the DB can be accessed as such.
  - bootstrap.py is just the platform specific services required to
    run the main_loop.py. They implement the prescribed json lines
    protocol above, the client and server waiting on each end of the
    pipe.

At first only 2 tty should be required by the web app. The html client
may even drop down to using only 1 tty. Multiplayer would require
multiple tty from ttyd, 1 per additional player.

## JSON Pointers

When the play

## Individually testable modules.

A critical part of this planning process is identifying the modules required in each language before starting. No two modules should call into each other cyclically as this violates the principles of starting with "unit testing" and incremental "integration testing" and I want both.

I want JS and PY test suite for everything possible, building up from the smallest modules to the largest. Both languages must implement the
output expected of the Test Anything Protocol when testing. Do not use existing test facilities for any language. Make a bespoke solution
that registers one function call per test and calls each one in
the order they were registered. Each module should have a test sub
module with a standardized entry point that returns the test suite for that module as an array of function calls. Only the name of the function, as queried from the interpreter, is used to document a test.
If a test throws an exception or returns "falsy" then the test failed.
Provide a wrapper that formats error messages for humans.

For now don't bother parsing the Test Anything Protocol, and instead
return (num_fail, num_pass) along with it for now. It is intended for
AI and human reading form now. Add color to any HTML output so readers
can see failed lines. highlight the entire line.

# Code quality

this is test driven development. first we design a module, then we
write tests for it, and then we fix all the bugs. after that we
move on to the next module. and we build our way up by stacking
modules with one way call patterns going down.

that way when we have all out modules assembled, testing as we go, we know the final assembly will work. this process has to be made clear in all action plans to write code.

all function call and class identifiers should contain two english names. modules (and their test sub modules) are the only exception.

both PY and JS require i18n support. when reading normal code i should see `i18n("internal_error", code)` or whatever and the i18n should
just be a dictionary of strings. If the UI string happens to be undefined then throw a message about the missing string and don't worry about the rest, that can be debugged in a subsequent step.

The remaining parameters should be formatted into the string if it
has formatting specifiers. Again, just throwing over improper usage
is fine as long as the callstack is correct it can all be unravelled
from there.

## HTML App

The JS app stores sqlite dbs in the browsers local storage
and then syncs them to the webserver. This design is intended to
allow the AI to run at full speed within the browser and then have
continuous backups to the server (as reasonable.)

This means the JS side has to implement an identical "substrate"
module to the PY side. It has the same API except it has more
work to do. In addition to managing a list of DBs, KV store
abstraction, and having a 128KiB filesystem overflow like the
server it has to do replication. the current players state
(the world) should contain a JSON Pointer to the players
current scene. More on that later.

The players current scene description is going to be in a DB on the AI
worker thread's side. The AI worker provides immediate access to
the DBs
required to implement the experience. this is moved off the UI
thread so the the UI doesn't stall in the DB and the AI doesn't
have to talk across 2 threads for normal DB access. (just 1.)
(media remains in the UI threads "files" DB and is referenced by BV
path from the AI thread.)

Media is expected to be loaded by the UI thread and written into
its "files" DB. The AI worker loads media by sending URLs.

Meanwhile, on the web app side, the main JS thread owns 3 databases.
The settings and preferences DBs map strings to json strings.
For example, per RFC 8259 """null""" is a valid way to say null that
way.

This means the 3 DB are:
  - settings : App wide constants, mutable when debug mode is enabled.
  - preferences : User configurable settings.
  - files KV: media cache, system scripts, blobs
````
