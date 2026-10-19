# the hyperposition-engine plan

This file is the whole plan; nothing outside this checkout is needed to
read it. Section 0 orients a reader who has seen nothing else. Sections
1 to 9 are the design. Section 10 holds what was asked for and is not
built, each with its design beside it. Section 11 holds what was decided
against. Assumptions the maintainer never confirmed are marked
"Unconfirmed" where they apply.

## 0 Orientation

### 0.1 The product

- The hyperposition-engine is a web page, served by ttyd from a Python
  back end, in which an AI guides a person through experiences. An
  experience is presented as large still images made by generative AI
  from a database of facts that describes it: a stack for "vibe coding"
  an experience and interacting with it.
- The page is bare bones HTML, CSS and JavaScript, written in
  TypeScript (2.5). The back end is ttyd, Python and dash.
- `xsjs` is the ttyd based back end administration tool suite, the
  Windows scripts at the top level of the checkout. The engine is one
  application of it, and the name stays.
- The engine is a template and a development environment. The AI writes
  each experience's scripts and database schema (5.6, 6.6); the engine
  supplies the substrate: databases, the wire, the task manager, the MCP
  tools and the provider protocol.
- ttyd is a stepping stone. It serves the page; its own terminal
  protocol, the one it serves to xterm.js, is recycled as the debug
  console; every other byte on the wire is JSLB (3).
- TypeScript in the browser and Python on the server is a permanent
  division. Shell appears only in the admin scripts and in the debug
  console. The Python server may one day be replaced by a hardened C,
  C++ or Rust component (10.2).

### 0.2 The experience

- The player starts at a blank black page with one subtitled remark,
  "How can I help you?". What the player answers goes to the AI, which
  talks to an MCP server in the browser on a worker thread and guides
  the player through experiences as requested.
- That starting point is the hyperposition, run by a very bored British
  female AI psychoanalyst, the analyst. Its scene holds nothing but
  wisps of fog and a few inexplicable bright lights, and it is the one
  scene the player cannot modify. The analyst tries to determine the
  right universe to send the player to, has admin control over the
  metaverse and performs requests as non judgementally and efficiently
  as possible. When the engine loads with no scene selected it loads the
  hyperposition (6.6).
- multiverse: a catalogue of separate experiences; the database
  `metaverse` (6.2) is that bookshelf, and both words are used.
  universe: a specific experience design. world: the current experience
  state, the global state of one experience. region: everything in your
  area; regions are disjoint entities. scene: a location; scenes follow
  the entities that move with the player through a local environment.
  Each scene is a new conversation with a new establishing shot. An
  experience is a series of scenes, with media files and a collection
  of entity databases. Compaction of a conversation is possible and
  crossfades stream in (10.7).
- The loop: the player initiates interaction and time always stops; a
  JavaScript handler optionally updates the page or notifies the AI; the
  AI interacts with the databases directly or through JavaScript, over
  MCP; then it updates the page, possibly with a new picture or scene,
  the render step; the player sees the updated page (5.3).
- By default time stops when the player stops, and gameplay is 2.5D and
  slow moving: the design of Myst, with basic RPG elements added, is the
  template. Multiplayer, turn based strategy games must work too (10.1),
  which may need the back end in C++ (10.2); proving the back end's
  algorithms and operation comes first.

### 0.3 How to work

- The maintainer owns the project and decides correctness and
  requirements. Architecture, correct wire formats, correct
  communication patterns and correct SQL design come first; delivery of
  working code second. An incomplete code base with correct APIs is
  worth more than a demo rewritten later.
- Modules are designed before they are implemented, with a professional
  separation of responsibilities, then built bottom up in the stages of
  8.7, everything bare bones and surveyed before the next stage begins.
- The work is test driven: design a module here and in API/, write its
  tests, write it, fix it, stack the next module on it with calls going
  one way, down (1.1). Drafts and prototypes are not goals.
- Nothing is added without its request (1.5), and every deferred
  capability is written with its full design (10), so that no example
  code ossifies into architecture and no reasoned out design is lost.
- Where this plan, a rule or an assumption marked Unconfirmed seems
  wrong, stop and ask; the maintainer requires explanations before plans
  change. Never decide silently, and never carry out something
  unrequested instead. An agent that meets an Unconfirmed assumption
  decides nothing: it uses the assumption and asks before building
  anything that would be reworked if the assumption is wrong.
- The project rules apply to every agent in full. The ones this plan
  leans on: fail fast with no fallbacks (1.2); nothing unmotivated
  (1.5); two English names for each function and class (7.1); packages
  are requested from the maintainer and never installed unasked; the
  maintainer reviews every commit, so agents neither commit nor stage.

### 0.4 The checkout, as of 2026-10-19

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
  The tool clones and builds `../ttyd` when missing; 2.7 replaces that
  build.
- `python/test_posix.py` formats and checks the whitelisted files with
  ruff, shfmt and a comment lexer; `python/reformat.py`,
  `python/reformat_whitelist.txt` and `python/pyproject.toml` support
  it. A new source file is added to the whitelist when it is created.
  The whitelist covers `API/python/**/*.pyi` and `DATA/*.py`.
- `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_stop.ps1`,
  `xsjs_status.ps1` and `powershell/` are the Windows administration
  scripts. ttyd listens on 127.0.0.1:5769 inside WSL and a `netsh` port
  proxy forwards 5768 to it. They change as 7.5 says.
- `API/` holds the external API of every module and `DATA/` synthetic
  transcripts of the standard communication, both written from this
  plan before any code. Nothing in them runs, and they follow the plan;
  `DATA/transcripts_make.py` regenerates the transcripts.
- Nothing of the design in sections 1 to 9 is implemented. `ts/`,
  `html/`, `i18n/`, `third_party/`, `python/tap/`, the substrate and the
  page do not exist.
- Toolchain in the maintainer's WSL account, Ubuntu 26.04: Python 3.14.4
  with SQLite 3.46.1, so `Connection.serialize` and `os.unshare` exist;
  Node 22.22.1 and npm with no `tsc`, which stage 0 needs and the
  maintainer must be asked to install; ruff, pyright, shfmt and
  mdformat; docker, unused; Windows Chrome or Edge for the browser
  tests. `json.dumps` with `allow_nan=False` refuses NaN and writes
  integers past 2^53 unchanged, so the encoder checks them itself (3.6).
- ttyd: the latest release is 1.7.7 of 2024-03-30. The apt package,
  1.7.7-4build1 at `/usr/bin/ttyd`, and the release offer `--url-arg`
  and not `--srv-buf-size`; upstream commit db77fde of 2025-01-31 adds
  it. `../ttyd` at 1.7.7-24-g2922cb8, built at `../ttyd/build/ttyd`,
  offers both. 2.7 builds the release with that commit as a patch.
- In ttyd 1.7.7's source the pty read pauses until each 64 KiB buffer
  is written to the socket, client input goes to libuv's write queue
  with no bound, PAUSE does nothing because the pause flag is set once
  at process start, and the only buffer option is `--srv-buf-size`,
  libwebsockets' `pt_serv_buf_size`, default 4096, the receive chunk
  size of both protocols (3.10). On program exit Linux ttyd sends all
  the output but ends the connection with no close frame, which the
  browser reports as 1006 (3.10).

### 0.5 Terms

- JSLB: JS-Line-Blobs, the wire format of 3. A line is one JSON object
  ending in CR, followed by blobs of bytes.
- tty 0 is the console, ttyd's own dash under xterm.js; tty 1 is the
  engine, Python speaking JSLB (2.3).
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
- Analyst, hyperposition, metaverse: 0.2. Debug mode: the setting
  `debug` (2.4).
- Door: a capability the design keeps open without building it. Section
  10 holds each with its design.
- Permit tool: a tool that runs only after the player accepts it (4.6).

### 0.6 Using this plan

- Sections 1 to 9 are the design; 10 the capabilities asked for and not
  built, each with its design; 11 what was decided against.
- Build in the stage order of 8.7. A stage starts only when the previous
  stage's exit criterion holds.
- API/ and DATA/ follow this plan: a change here changes them in the
  same pass.
- The record of the planning process, every question and the
  maintainer's literal answer, was removed from this file on 2026-10-19.
  Every decision it produced is carried below. Do not reconstruct it
  from older documents or from history.

## 1 Method

### 1.1 APIs before code

- Every protocol is emulated as the real protocol from the first line:
  MCP is JSON-RPC 2.0; the provider is spoken to in the chat completion
  shape; TAP is TAP.
- Order of work: design the module here and in API/, write its test
  module, write the module, fix it, stack the next module on it with
  calls going one way, down. No module calls up or sideways.
- A stage that would need an API rewritten later is not started.
  Nothing here is a prototype or a draft; each stage is the final module
  behind its API.
- Nothing is added until it is required. A capability a request names
  but no stage needs yet is written in section 10 with its design.

### 1.2 Fail fast

- No error is swallowed, defaulted or retried. A failed server handler
  writes one `error` line and exits 1. In the page, `error_overlay`
  replaces the screen with the message and the call stack in a `<pre>`
  and stops the app. Recovery is a full page reload, the tested path;
  resync is reloading the client.

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
  request. Existing code in the checkout is current state, not design:
  the bootstrapper, its page and the wire test are reused only where
  this plan chooses them. The DevTools relay of the screenshot tool is
  chosen by this plan as the implementation of `devtools.py`.

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
  console, 1 the engine, 2 and up are reserved for players (10.1).
  Unconfirmed: the role in `--url-arg` names them, `console`, nothing
  for the engine, `player2` onward.

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
- Unconfirmed: ttyd runs one command and the role rides `--url-arg`; the
  AI worker owns the console socket and relays it to the UI (4.7), so
  the AI worker is the only owner of sockets. Rework if ttyd should run
  two commands or the UI should own the socket: the start script,
  bootstrap.py's role handling and the console lane.
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
  Research goal, open: whether xterm.js can be fed while hidden and keep
  its state; the headless package is the alternative for feeding, chosen
  once by the research result. That is a design alternative, not a
  runtime fallback.
- ctrl-n, n from 1, toggles the overlay of tty n: a `<pre>` holding the
  rendered form (3.11) of the last `verbose_ring` lines in both
  directions, newest last. These overlays are read only and have no
  console features.
- In debug mode with `verbose_forward` on, the same rendering of the
  wire traffic and the page's `console.*` output goes to the server as
  `verbose.put`, so `_verbose` holds the page's view. Unconfirmed:
  verbose level 2 and `verbose_forward` gate it; a 128 MiB upload
  renders as one line, a turn as many.

### 2.7 ttyd

- The engine works with the latest source release of ttyd, built from
  source: 1.7.7, the tag of 2024-03-30, as of 2026-10-19. A later
  release moves the pin. No other ttyd is supported: not the apt
  package, not a build of ttyd's main branch, not Windows `ttyd.exe`.
  The runtime is ttyd in WSL, started by the Windows scripts (7.5, 9).
- `third_party_fetch.py` fetches the release's source archive, pinned by
  version and SHA-256 like the other third party code, into
  `third_party/`. The install script unpacks it, applies the patches and
  builds it with cmake under `build/ttyd/`, in WSL, installing nothing.
  The build dependencies are the ones ttyd's README names; they are
  present in the maintainer's WSL, as `../ttyd/build/ttyd` shows, and
  are requested from the maintainer on any other machine. Start copies
  `build/ttyd/ttyd` to the root (9).
- Where the design needs a behaviour that no option, setting or
  documented configuration of the release provides, ttyd is patched. A
  patch is a unified diff `third_party/ttyd/<nn>_<name>.patch`,
  committed, applied in name order to the unpacked source before the
  build. Each is recorded here with what it changes and why, and
  backports the upstream commit where one exists rather than writing
  new code.
- Patch 01, `01_srv_buf_size.patch`: upstream commit db77fde of
  2025-01-31, `src/server.c` and the two man pages, adds
  `--srv-buf-size`, which 3.10 relies on and the release lacks.
- No other patch exists. The next candidate is flow control: should the
  stage 2 measurement show ttyd's write queue growing without bound
  during the 128 MiB upload, a patch bounding it is the alternative to
  the credit line of 10.11, and the measurement decides. The missing
  close frame on program exit (0.4) needs none: the page treats a close
  with no `error` line as a fault (3.10).
- `test_wire.py` and `test_browser.py` run `build/ttyd/ttyd` (8.2). The
  screenshot tool's clone and build of `../ttyd` is retired with it.

## 3 JSLB wire format

### 3.1 Framing

```text
message := line blob*
line    := json-object CR
```

- `json-object` is one JSON object in UTF-8 with no whitespace outside
  strings. The encoder emits no CR, so the first CR, byte 0x0D, ends
  the line.
- LF is an ordinary byte with no meaning, as every byte other than CR
  outside a string.
- The blobs follow the CR at once, in header order, each exactly `s`
  bytes, nothing between.
- A reader has two states: bytes to a CR, then known byte counts.

### 3.2 Headers at integer keys

- Every JSON object that carries headers, a JSLB line or a document,
  keeps them at the integer keys 0, 1, ... and its payload at every
  other key. 0 is the object's own header. The headers are discovered
  by probing the integers from 0 until one is missing, so a reference
  to a header is an integer, `line[0]`, `line[1]`, never a string of
  digits.
- JSON writes every key as a string, so the encoder writes an integer
  key as its decimal digits and the decoder turns a key that is the
  decimal digits of a non negative integer, with no sign and no leading
  zero, back into an integer. In Python the decoded object is a `dict`
  with `int` keys for the headers and `str` keys for the payload; in
  JavaScript `line[0]` is the property `"0"`, and `headers_of` probes by
  number.
- In a line, 1 to `b` are blob headers. In a document, 1 on are
  reference strings (6.4).

### 3.3 Line header, key 0

- `t` `type`: string, required. The handler name: lowercase words joined
  by `_`, namespaces by `.`.
- `v` `version`: integer, default 0.
- `i` `id`: integer from 1, present when a reply is expected.
- `r` `reply`: integer, the peer's `i` this line answers.
- `k` `key`: string, the key the line is about, when it is about one.
- `b` `blobs`: integer, default 0. It equals the probe count of 3.2; a
  difference is a hard error.

default values should not be stored, but be implicit by omission.

### 3.4 Blob headers, keys 1 to b

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

- No 0, no `t`, `b` not matching the headers present, a gap in 1 to
  `b`, a non-integer or negative `s`, a payload key that is decimal
  digits, both name forms, an unknown field in the line header.
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
  queue; the one option is `--srv-buf-size`, the receive chunk size,
  patched into the release (2.7). Decision: ttyd runs with
  `--srv-buf-size 1048576`; `chunk_bytes` is 1 MiB; `wire.ts` waits for
  `bufferedAmount` under one chunk before the next; the server streams
  big blobs to the cache file so libuv's queue stays short. ttyd's
  resident size during a 128 MiB upload is measured in stage 2; only if
  the measurement demands it is a credit line added (10.11) or ttyd
  patched to bound the queue (2.7).
- ttyd may end a connection without delivering a program's last output,
  and Linux ttyd closes with no close frame, code 1006, when the program
  exits. The page treats a close with no `error` line as the fault
  "connection closed with code N and no error line"; the wire test times
  each rung and reports a lone loss with the ttyd version, never
  retrying it.

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
  are faults like any other and end in Reload.
- The rules' Project Direction 1.3, written for the old bootstrapper's
  page, says never retry by reloading the page. This design reloads, by
  the maintainer's decision (11).

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
  and dash; no Python line type exists for the console. The owner of
  the socket is Unconfirmed (2.3).
- The AI reaches it only through the `console_run` tool after the
  permission flow. `console_run` posts the text and a newline as
  `console.input` to the console port, submits `console.read` to it and
  sleeps; the port answers with the output once the prompt returns or
  `timeout_seconds` expires, a timer.
- The player's text and clicks are notifications a DOM listener posts
  to the UI's queue as `ui.input`; the handler submits `ai.say` or
  `ai.click` to the AI worker and sleeps with `ui.turn_end`, which
  enables the input again.
- Timers exist wherever a wait can fail: the provider request (4.1), the
  console command, every test rung (8.2). The agent sets no game timers
  (5.3).

## 5 The AI

### 5.1 The model

- The model of this system is the set of databases on one thread; the
  design is not MVC. Threads that talk directly and keep private
  storage, `media_db` for one, are part of the design. The AI reaches
  the model through the tool layer of 5.5, and the tests drive that
  layer through the stubs of 8.5.

### 5.2 The generic provider protocol

- The chat completion protocol: `POST {base_url}/chat/completions` with
  `model`, `messages`, `tools`, `tool_choice`; `choices[0].message` with
  `content`, `tool_calls` and `finish_reason`. Images: `POST
  {base_url}/images/generations` with `response_format` `b64_json`. xAI
  is the first and only provider tested; the same shape for others is a
  door (10.6).
- `provider.ts` is the one door: `chat_request(messages, tools)` and
  `image_request(prompt)` each build one `http.request` line with the
  key in `Authorization`; the caller submits it and sleeps. The key is
  read by the server from the environment variable `XSJS_PROVIDER_KEY`,
  a name that is Unconfirmed, and sent in `hello`; it lives in the AI
  worker's memory only.
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
  Unconfirmed: the AI may create a database outside the universe, world
  and region ones; rework is tool limits.
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

API/mcp/tools.json is the list as `tools/list` returns it. Unconfirmed:
the permit set is `console_run`, `source_put` and `system_restart`;
rework is the tool metadata and the stub conversations.

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
  Nothing is sent to the server for compilation. Unconfirmed: run and
  debug are a run and a traced run; rework if stepping or breakpoints
  are meant: a script interpreter or DevTools in the loop.
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
  (10.5). Unconfirmed: `media.fetch` stays beside `b64_json`; if the
  first version is `b64_json` only, one line type and one UI handler
  fewer.

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
  `_preferences` exists with its schema and nothing writes it yet, as
  Always Allow lasts the tab (4.6). Unconfirmed.
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
  changes; history is the set of versions. One table holds documents,
  blobs and settings, so there is one overflow path and one replication
  path, and the head is a primary key lookup.
- A document's headers follow 3.2: 0 is the document header, `t` the
  document type and `v` its format version, defaults omitted; 1 on are
  reference strings, Key-Value-Refs and Document-Refs, iterable by
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
  Unconfirmed: the player in use is the Key-Value-Ref
  `/metaverse/player` and a universe row is `(name, title, player,
  world)`; rework if a player table is wanted: a second fixed schema.
- The engine reads two Key-Value-Refs: `/metaverse/player`, the player
  in use, and `/metaverse/world`, the database holding the current
  world; then the Document-Ref in `/$world/scene` is the scene it
  renders (the world holds the pointer to the current scene). The seed
  sets `player` to `player`, `world` to `metaverse` and
  `/metaverse/scene` to `/metaverse/hyperposition/1`.
- The server seeds the hyperposition document, the analyst's prompt
  document, the three keys above and `script/bootstrap.js` when it
  creates the metaverse. Unconfirmed: the seed texts are repository
  files `python/seed/<id>.json`, each a document in its encoded form
  (6.4), and the script beside them.
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
  from the AI thread, and compares the server's copy. Unconfirmed: the
  UI thread, which holds no SQLite, submits its modifications as tasks
  to the AI worker's database, which forwards them; rework if the UI
  must hold a table of its own: a UI side substrate.
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
  reads is not there. `grok-4` and `grok-2-image` in API/settings.json
  are placeholders: the maintainer named xAI and no model.
- The server loads it into `_settings` at start, so the AI can query it,
  and sends it in `hello` (2.4). `settings.put` in debug mode rewrites
  the file; the server rereads it at the next `hello`.

## 7 Modules

### 7.1 Naming

- Functions and classes carry two English names; modules and test
  modules are the exception; the maintainer's own identifiers override
  the rule, as `verbose.log` does.
- Constants are `_UPPER_NAME` at the top of each Python file; TypeScript
  has one frozen `constants` object per module.
- `i18n("name", ...args)` in both languages; `from i18n import i18n` is
  the one `from` exception, decided by the maintainer and not yet in the
  rules file, which is the maintainer's to edit: report the gap, don't
  edit the rules. Strings live in `i18n/en-US.json`, read by Python and
  substituted into `ui_strings.ts` by the build, checked for the same
  names by stage 0; PowerShell keeps its `i18n.psd1`.

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
  Headers are the `int` keys of the decoded `dict` (3.2).
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
  `error_make`, `id_next`; calls `fn(line, **payload)`, so a handler
  reads its first blob as `line[1].d`.
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
  the console. Immutable outside debug mode. In debug mode `source.put`
  stores a main loop file as `<root>/main_loop/<name>` and
  `system.restart` restarts the process with the named file as its main
  loop, so the AI can recover the server when only bootstrap.py is
  intact, sending several main loops and examining the output of each.
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

- The Windows scripts change in two places. The install script builds
  ttyd from the pinned source release with its patches (2.7) in place of
  installing the apt package. The function that starts ttyd runs the
  built binary with `--url-arg`, `--srv-buf-size 1048576`, the index
  file name and the root argument, and passes `XSJS_PROVIDER_KEY` from
  the user's environment into ttyd's; nothing about debug, which is a
  setting.
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
  hang leaves the lines before it on disk. Unconfirmed: `tap.line
  {language, text}` carries the TAP text, and the consumer returns plan,
  pass, fail, skip and whether the stream is well formed; rework if a
  structured result is wanted: the consumer and the test page.
- `failfast`: the first `not ok` stops the stream with the traceback as
  diagnostics. Side effects between tests are banned; name order is
  fine.
- `test.html` shows the stream with every failed line highlighted whole.
  That colour was requested; it is not decoration. Unconfirmed.

### 8.2 Runners

- `python3 python/test_all.py`: the Python suites in dependency order,
  then `test_wire.py`.
- `python3 python/test_browser.py`: builds `test.html`, serves it
  through ttyd, runs the TypeScript suites in headless Chrome, reads the
  `tap.line` stream from the file of 8.1, checks it with the consumer,
  saves a PNG. The one JavaScript runner is a browser. `devtools.py` is
  `page_open(url)`, `script_evaluate(text)`, `console_follow(fn)`,
  `screenshot_save(path)`, `page_close()` over the DevTools protocol,
  implemented by the relay now inside `xsjs_screenshot.py`, split out.
- `test_wire.py` and `test_browser.py` run the ttyd the install script
  built (2.7) and fail naming the install script when it is missing.
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

8.7.1 Stage 0, the harness: ttyd built from the pinned release with its
patches (2.7), which `test_browser.py` serves through;
`third_party_fetch.py`, `tap/`, `i18n`, `test_all.py`, `tap.ts`,
`unittest.ts`, `devtools.py`, `test_browser.py`, `page_build.py` for the
test page, tsc in the build, `error_overlay.ts`, `utility.ts`,
`ui_strings.ts`, `settings.ts`. Proves one passing, one failing, one
raising and one skipped method yield identical TAP in both languages as
one subtest block, accepted by the consumer; `failfast`; `i18n` raises
in both; a thrown error in the test page ends in the `<pre>` screen;
`settings_get` of an unknown id throws and the frozen object refuses a
write. Survey: the TAP text; the PNG. Exit: both runners exit 0 on the
real suites and 1 on the nested class.

8.7.2 Stage 1, JSLB: `jslb.py`, `jslb.ts`, the vectors, streaming over
`overflow_bytes`, header probing, rendering. Exit: both suites pass;
each reads all the vectors of the other.

8.7.3 Stage 2, the raw wire: `bootstrap.py` with raw mode, the lock and
`hello`, an `echo` handler; `test_wire.py` rungs `hello`, `echo`, `echo
1 MiB with control bytes`, `echo 128 MiB` with ttyd's resident size
printed, `second connection refused`, `ttyd killed`, and the last line
regression of the rules' Project Direction 1.1, the old test that keys
on the last line of a process that exits right after printing it, kept
as it is: a lone loss there is a ttyd fault, reported with the ttyd
version and not retried. Each rung runs under a timer. Exit: all rungs
pass twice.

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

8.7.10 Stage 9, the beachhead: the changes to the Windows scripts (7.5);
the engine serving from the maintainer's WSL account; the maintainer's
test plan run by hand. Exit: the maintainer's sign-off.

## 9 Operations

- First beachhead: the engine runs from the maintainer's own user
  account on WSL, started by the Windows scripts, nothing as root, no
  service manager, no container.
- Server root `~/.cache/xsjs/`: `ttyd`, `bootstrap.py`, the Python
  package, `main_loop/`, the page, `settings.json`, `ttyd.log`,
  `engine.lock`, `tap/`, the databases and `cache/`. Start copies the
  built ttyd (2.7), the package, the page, the settings and the seeds
  there. The provider key is `XSJS_PROVIDER_KEY` in the environment of
  the ttyd process.
- Certificate, boot and checkout decisions of the rules' Project
  Direction stand unchanged.
- An audit of the key in `hello` and of the dispatcher's single door
  follows the beachhead (10.12).

## 10 Things that should be possible, but not implemented.

Each item is a request from the planning process that this plan does not
build. The design that was reasoned out is written beside it so that
nothing is lost.

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
  it. A ttyd patch bounding its write queue (2.7) is the other route;
  the measurement decides between them.

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
maintainer, or is a proposal that no request motivates. Each gives what
was proposed and what replaced it. Nothing here returns without a
request.

- JSON Pointers: replaced by Document-Refs.
- A fixed Document-Ref depth `<db>/<kind>/<name>/<version>` and separate
  `doc` and `doc_head` tables: a document is a KV row with `_head`, and
  `$id` is free.
- A `refs` array required in every document, or `{"$ref": n}` naming a
  top level `refs` table: the integer keyed headers probed from 0.
- One database per scene, eight attached: one per region, then the
  universe, world and region databases and tables the bootstrap script
  makes.
- SQLite in the browser's local storage: OPFS in a worker.
- Settings, preferences and files databases on the main thread, or
  removed in favour of `hello` and a metaverse document: on the AI
  thread, as `_settings`, `_preferences`, `_files`.
- Three threads with the substrate on a WASM worker and the AI worker as
  owner on paper: two.
- A handler on the AI thread returning a promise: the task manager
  sleeps and wakes.
- `handler(**line)` with the headers as keyword arguments: the
  dispatcher calls `handler(line, **payload)`.
- A line type defaulting to `utf-8`, string versions, a blob type
  registry: type required, integer versions, defaults omitted, no
  registry.
- `text_format` as the i18n function name: `i18n` with a `from`
  exception.
- Node banned entirely: allowed for tsc at build time.
- `.sh` parallels, a Docker lifecycle test, serving from an Ubuntu
  container, a systemd unit, version floors: doors (10.3), not work.
- Debug mode as a flag of the ttyd command: a setting.
- All of the page's JavaScript editable by the AI: the modules the AI
  does not edit are precompiled; the AI edits its own scripts.
- A server side TypeScript compiler for the AI's scripts: nothing is
  sent for compilation.
- The AI's scripts run with `new Function` and no MCP edit, run or debug
  tools: MCP edits, runs and debugs them.
- Reconnect in the same page without reloading: a full reload is the
  tested path, by decision, although the rules' Project Direction 1.3,
  written for the old bootstrapper's page, says never retry by
  reloading the page.
- `put`, `ls`, the forked modules and the command loop of the existing
  bootstrap.py: ripped out.
- One tty with dash forked by Python and relayed as JSLB blobs, with a
  Python `console.py` and `engine_console.py` for it: two ttys, the
  console optional and ttyd's own.
- The `log` namespace, `engine_log.py`, `log.sql`, `log.*` lines,
  `log_tail`, `log.ts`, `log_ring`: `verbose`.
- The verbose module without its external call wrapper: the wrapper is
  the one place external calls go through.
- The AI's tables replicated by whole snapshot after a turn with a
  trigger written change log as the improvement; a row log with per row
  `seq`, `kv_gone` tombstones, `sync.pull` and `sync.push`; `kv.changed`
  pushed by the server while a tab is open, and the browser pulling:
  every operation forwarded as it happens, one way during play, and
  differing files replaced at start.
- Two tasks from the caller in place of forwarding: forwarding is
  required.
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
- A console log-in and a player account: none; ownership of the server
  is the account.
- `settings.ts` generated from settings.json at build time, and a
  `settings_sha256` in `hello` refusing a page built from another file:
  settings arrive in `hello` and the module is hand written.
- `python`, `sqlite` and `debug` fields in `hello`, `tab` and the page's
  hash in its reply: no version checks, debug is in the settings,
  nothing reads the rest.
- `port_windows`, `port_wsl`, `console_enabled`, `console_columns`,
  `console_rows`, `mcp_protocol_version` and `log_ring` as settings: no
  module reads them; the console is debug mode, xterm.js sends its own
  size, the revision is a constant.
- `script_put`, `script_get`, `script_list` tools: a script is a KV row
  the `kv_*` tools edit.
- `universe_create`, `world_create`, `region_create`, `player_switch`
  and `scene_enter` as engine tools: the scripts are the database
  administrator and the seeded bootstrap script does these.
- `verbose.dump`, `verbose.follow`, `verbose.line` and a server side
  `verbose.level`: deferred to 10.16 and 10.17.
- Turns as documents, or as the version history of one document: the
  turn table.
- The apt package of ttyd, and `../ttyd` built by the screenshot tool:
  the latest source release built with the project's patches (2.7).
