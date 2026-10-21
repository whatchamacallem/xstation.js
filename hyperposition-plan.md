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
  ruff, shfmt, prettier for `.ts`, `.js` and `.html`, and a comment
  lexer; `python/reformat.py`, `python/reformat_whitelist.txt` and
  `python/pyproject.toml` support it. A new source file is added to the
  whitelist when it is created. The whitelist covers the `API/` stubs.
- `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_stop.ps1`,
  `xsjs_status.ps1` and `powershell/` are the Windows administration
  scripts. ttyd listens on 127.0.0.1:5769 inside WSL and a `netsh` port
  proxy forwards 5768 to it. They change as 7.5 says.
- `API/` holds the external API of every module, written from this
  plan before any code. Nothing in it runs, and it follows the plan.
- Nothing of the design in sections 1 to 9 is implemented. `ts/`,
  `html/`, `i18n/`, `third_party/`, the substrate and the page do not
  exist.
- Toolchain in the maintainer's WSL account, Ubuntu 26.04: Python 3.14.4
  with SQLite 3.46.1, so `Connection.serialize` and `os.unshare` exist;
  Node 22.22.1 and npm with no `tsc`, which stage 0 needs and the
  maintainer must be asked to install; ruff, pyright, shfmt, prettier
  3.9.8 and mdformat; docker, unused; Windows Chrome or Edge for the
  browser tests. `json.dumps` with `allow_nan=False` refuses NaN and
  writes integers past 2^53 unchanged, so the encoder checks them
  itself (3.6).
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
- MB means MiB, KB KiB and GB GiB, always.

### 0.6 Using this plan

- Sections 1 to 9 are the design; 10 the capabilities asked for and not
  built, each with its design; 11 what was decided against.
- Build in the stage order of 8.7. A stage starts only when the previous
  stage's exit criterion holds.
- API/ follows this plan: a change here changes it in the same pass.
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
- System initialization need not abide by the rules for how the system
  is used unless it is reasonably convenient. The AI worker's
  initialization, `sqlite3InitModule`, `installOpfsSAHPoolVfs` and its
  capacity, the OPFS directory, its file handles and
  `createSyncAccessHandle` for the cache files, uses promises directly
  in one module, `boot.ts`, which the audit of 8.6 exempts by name; no
  port turns them into lines. Once it has handed the objects over, the
  system runs under the rule above.
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
  trace a script with `script_debug` and optimize.
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
  `debug` is true, runs `/bin/dash` through `verbose.exec` at the setting
  `verbose_level`, `[dash, "-v"]` its level 2 form, with a scrubbed
  environment and the root as working directory, and exits with its code.
  The shell is the one thing with verbose levels; the server and the page
  have only `debug` (2.4, 10.19); when `debug` is false it
  exits 1 and ttyd closes the connection. Its pty stays cooked, so it
  echoes. The page's console module speaks ttyd's own client protocol
  to it, which is ttyd's dash and xterm.js recycled. The user opens it
  with ctrl-0 or the AI opens it with permission. No log-in beyond
  ttyd's own.
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
- `debug` is also the only verbose switch of the server and of the page,
  which have no verbose level (10.19): the task manager's trace (4.2),
  the server's trace of each line it dispatches and replies to, and the
  forwarding of `verbose.put` happen in debug mode only. A failure is
  logged always. Verbose levels belong to the shell alone (2.3).
  Unconfirmed: the server's trace holds each line's header JSON only;
  rework is the whole line in the form of 3.11.
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
- `html/test_engine.html` is the engine page built with the test
  bundle's `test_hook.ts`, through which a browser rung submits tasks
  from the UI's live queue (`page.test_engine`, `boot.test_engine`);
  `page_build(name, test, template)` chooses the template. The
  production page carries no test code.
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
- In debug mode the same rendering of the wire traffic and the page's
  `console.*` output goes to the server as `verbose.put`, so `_verbose`
  holds the page's view; `debug` alone gates it (2.4). The overlay of
  tty 1 does not show the `verbose.put` lines it forwards, which would
  feed it to itself. A 128 MiB upload renders as one line, a turn as
  many.
- The console view and the overlays show above the scene's image.
  Unintentional invisibility is always a bug, not a style issue. Two
  states are accepted by the maintainer: with both shown, the overlay
  below the console scrolls the console's top rows out, and the subtitle
  band lies over the bottom strip of the image.

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
- A line over `line_max` refused before its bytes are buffered. A
  message whose blobs' `s` sum over `blob_max` refused when the line
  ends, before any blob byte is buffered (3.8).
- The decoder raises on the first error and the port that fed it
  closes. No resynchronization on a byte stream.

### 3.8 Streaming blobs

- A blob of `s` at most `overflow_bytes` is collected in memory. A
  larger blob is written to a new file in the cache directory as it
  arrives, hashed on the way, and `d` is that path; the handler moves or
  links it. Memory per message is bounded by `line_max` plus `blob_max`.
- `blob_max` is the one window every blob goes through, the size of the
  largest database (6.10), and one `settings.json` entry. A window counts
  blob bytes, the `s` of each blob it holds or passes, never line bytes,
  which `line_max` bounds line by line: a message's blobs, and the blobs
  of the lines any JSLB queue holds, sum to at most `blob_max`, and a
  line that would pass it is a fault. The task manager's queues, the
  wire's frame queue and the AI worker's replication queue are bounded
  so, and `wire.ts` refuses to post a line over `line_max` or a message
  whose blobs sum over `blob_max`. The server holds no queue: it
  dispatches one line at a time. Unconfirmed: a window counts blob bytes
  only, so that a blob of `blob_max` passes every window with its line
  and a `kv.get` reply fits whenever its `kv.put` did; rework is counting
  line bytes too, the largest blob then `blob_max` minus its line.
- Unconfirmed: `blob_max` is 2147483391, the largest allocation SQLite's
  `sqlite3_serialize` makes by default, which every whole database image
  passes through and which no browser limit can raise; Chrome's own
  limits, the origin's quota, the largest `Uint8Array` and the wasm heap
  of the worker's export, are measured in stage 6 (8.7.7), and a lower
  one is the maintainer's to set. The research, its sources and the
  options are in `PLAN_B.md` 2.13.
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
  resident size during a 128 MiB upload, one message within `blob_max`,
  is measured in stage 2; only if the measurement demands it is a credit
  line added (10.11) or ttyd patched to bound the queue (2.7).
- `chunk_bytes` and `srv_buf_size` stay 1 MiB and are not set to
  `blob_max`: they are the pieces a blob is cut into, not windows that
  hold one, and each is allocated whole, by every `os.read` of the
  server and, read from the libwebsockets sources, by each service
  thread of ttyd. The maintainer approved this on 2026-10-21
  (`PLAN_B.md` 2.20).
- ttyd may end a connection without delivering a program's last output,
  and Linux ttyd closes with no close frame, code 1006, when the program
  exits. The page treats a close with no `error` line as the fault
  "connection closed with code N and no error line"; the wire test times
  each rung and reports a lone loss with the ttyd version, never
  retrying it.

### 3.11 Debug rendering

- A line is rendered for a human as its JSON text followed by one `<blob
  "n"=K>` tag per blob, K the header key from 1. The overlays (2.6) and
  `verbose.put` of wire traffic use this form.

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
- The queue handles sleeping tasks and an empty queue. In debug mode it
  logs every submit, dispatch, sleep, wake and reply through `verbose`,
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
  `provider_key`, and `provider_info` when `provider.scripted` is false
  (6.9). The worker posts `settings.set` to the UI, answers
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
- The permit set is `console_run` alone, which gates the host's shell,
  not a database. Nothing between the AI API and the databases asks
  permission or refuses: the AI calls `source_put` and `system_restart`
  without asking, over the line and over stdio.
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
  (5.3). The provider request waits `provider.timeout_seconds` and the
  console command `console_run`'s `timeout_seconds` argument; every
  other timer is a named constant holding a sane default, its one line
  comment saying its writer chose it.

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
  worker's memory only. The provider's address and model names are in
  `provider.json` (6.9), filled out by the maintainer later; until then
  the engine depends on the scripted provider below.
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
  `ai.model_reply`: for each tool call of the reply submits an MCP
  `tools/call`, storing nothing yet; a tool that must wait (an image, a
  permit, the console) sleeps in turn; when every tool result is in,
  `ai.tool_reply` stores the reply that called the tools together with
  their results in one transaction and submits the next provider
  request, so no stored call lacks its result and a failed tool call
  leaves no unanswered turn; a reply with no tool calls is stored and
  ends the turn with the reply to the original `ai.say`. In debug mode
  the queue log is the transcript of the turn (4.2).
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
  AI is the database administrator. SQL rules are not a security
  boundary: no table or database refuses a write.
- `db_create {db}`, `db_drop {db}`: the AI adds and removes databases.
  The AI may create a database outside the universe, world and region
  ones; no tool limit refuses it, and nothing limits their number.
- `db_stats {}`, `db_compact {db}`, `db_unload {db}`, `db_load {db}`:
  the database administration of 6.10.
- `kv_get {ref}`, `kv_put {ref, text}`, `kv_delete {ref}`, `kv_list {db,
  prefix}`: the KV accessor on Key-Value-Refs.
- `doc_get {ref}`, `doc_put {db, id, body}`, `doc_head {db, id}`.
- `script_run {name, args}`, `script_debug {name, args}` (5.6). A script
  is edited with `kv_put` on `/_files/script/<name>.js`.
- `image_make {prompt, key}`, `render {image, subtitle}`.
- `console_run {text, timeout_seconds}`, permit, debug.
- `verbose_tail {thread, count}`. The page has no verbose level to set
  (2.4); the `verbose_level` tool is deferred with the levels (10.19).

Server, in Python:

- `source_put {name}`, debug, and `system_restart {main_loop}`, debug.

API/mcp/tools.json is the list as `tools/list` returns it. The permit
set is `console_run` (4.6).

### 5.6 Scripts: the AI's JavaScript and the database administration

- The AI's scripts are KV values in `_files` under `script/<name>.js`,
  on both sides by replication, which is the immediate backup to both
  databases. They are editable over MCP.
- `script_run {name, args}` runs the text in the AI worker as a task:
  `new Function("engine", "args", text)` with `engine` the frozen object
  of the substrate, `verbose` and `i18n` APIs. It returns the value, or
  the exception with its stack, and the verbose lines the run emitted;
  `engine.log(text)` takes no level. `script_debug {name, args}` is the
  same run with its trace on, which traces every substrate call the
  script makes through the single door.
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
_settings     settings.json loaded, key to JSON text       fixed
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
  holds the settings file as the server loaded it; `_preferences` and
  `_files` have the engine's schema. A fixed schema is not enforced and
  no table or database refuses a write: SQL rules are not a security
  boundary. Unconfirmed: `_preferences` exists with its schema and
  nothing writes it yet, as Always Allow lasts the tab (4.6).
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
  scene's Document-Ref, each one provider message.
  `turn_compact(scene, through, summary)` in the substrate replaces turns
  1 to `through` with one summary row, role `system`, at `n` 1.
- Compaction is automatic, by an event counter, a heuristic baked into
  the wrapper, not an AI script. The events are the turns appended to a
  scene's conversation, of any role; the counter is the number of the
  scene's `_turn` rows, counted when read, so it survives whatever the
  turn store survives and resets when a compaction replaces the turns it
  covers with one. When the browser's `Store.turn_append` appends a turn
  of role `user` to a scene that already holds `turn_compact_turns`
  turns or more (6.9), it first compacts that scene's turns 1 to its
  last in the same transaction, forwarded as its own `turn.compact`
  before the `turn.append`; the server applies both and never compacts
  by itself. A `user` turn starts a player's turn, when no tool call
  waits for its result (5.3). The summary is by truncation: one `i18n`
  text naming the turns compacted and the count that reached the
  threshold; the databases hold the state. The AI may still compact by
  hand with `turn_compact`. Unconfirmed: the events, the counter, the
  moment, the summary and the threshold of 64 are readings and a
  default chosen by the planner; rework is this item, `substrate.ts`'s
  `turn_append` and the setting. The estimate design this replaces is
  in 10.20.

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
- The forwarded operations are a test driver: a sequence of them that
  the test builds, replayed into `test_wire.py`, drives the server
  substrate before the page exists, and replayed into the browser drives
  the page without a provider.
- Direction: during play the browser writes and the server backs up;
  nothing is pushed from the server while a tab is open (one way). The
  server is the source of truth.
- Start: `hello` carries `seq` per database. Where the browser's `seq`
  differs, its file is invalidated and replaced by the server's:
  `db.snapshot` yields `Connection.serialize` bytes as one blob, at most
  `blob_max` (3.8), with their `sha256`, which the browser checks before
  it restores, and `db.restore` writes a temp file and renames it. Only
  the databases the browser holds are replaced; the others stay unloaded
  until `db_load` (6.10).
- Desync: a refused push, or a reply whose `seq` is not the browser's,
  is a fault; the page reloads and the reload replaces the file. That
  path is unit tested in stage 6, early. Content divergence with equal
  `seq` is a door (10.9).
- `_verbose` is server only. `_settings` is written by the server from
  the file and never by the browser, which nothing enforces.

### 6.9 Settings

- `settings.json` holds constants only, each with a sane default:
  `debug`, `queue_synchronous`, `verbose_level`, `verbose_ring`,
  `line_max`, `blob_max`, `overflow_bytes`, `chunk_bytes`,
  `srv_buf_size`, `media_db_bytes`, `files_browser_bytes`,
  `db_soft_bytes`, `turn_compact_turns`, `long_task_ms`, and `provider`
  with `scripted` and `timeout_seconds`. Never a password or a key. A
  constant no module reads is not there.
- `blob_max` is the one window of every blob (3.8); `verbose_level` is the
  shell's level, read by the console role alone (2.3); `verbose_ring` the
  size of each thread's ring; `turn_compact_turns`, 64, the count of a
  scene's turns at which it is compacted (6.6). `message_max`,
  `queue_max`, `verbose_forward` and `turn_compact_tokens` are gone.
- The server loads it into `_settings` at start, so the AI can query it,
  and sends it in `hello` (2.4). `settings.put` in debug mode rewrites
  the file; the server rereads it at the next `hello`.
- `provider.json` beside `settings.json` holds the provider's
  `base_url`, `chat_model` and `image_model`, empty strings until the
  maintainer fills them out, and is not used during testing but by one
  rung. When `provider.scripted` is false the server reads it, an empty
  value is an error, and `hello` carries it as `provider_info` beside
  `provider_key`; when it is true, as in every test but that one, the
  file is never read and `hello` carries no `provider_info`. The rung of
  the real HTTP timeout inside a turn writes its own `provider.json` into
  its own root, sets `provider.scripted` false there and points
  `base_url` at a local stub; the maintainer accepted that. Unconfirmed: the file's
  name, place and keys; rework is the server's reading of it and
  `hello`.

### 6.10 Database administration

- The AI is the database administrator of the set of databases it
  operates on, and keeps the browser's working set in OPFS small enough
  for fast MCP operations. The server keeps every database as the source
  of truth (6.7, 6.8), so the browser's set shrinks without losing
  anything. Nothing limits the number of databases.
- Measurement is by heuristics, never by a quota call:
  `navigator.storage.estimate()` is asynchronous and would break the one
  synchronization tool (1.3). A database's size is `page_count` times
  `page_size`, plus the `size` of its `_kv` rows whose value is in the
  cache (`data` NULL); its reclaimable space is `freelist_count` times
  `page_size`; the total is the sum over the databases open in the AI
  worker. `db_soft_bytes`, 1 GiB, is a soft limit and refuses nothing.
- Four browser tools, each one substrate operation behind one MCP tool:
  `db_stats {}`, read only, returns for each open database `name`,
  `bytes`, `free_bytes`, `cache_bytes` and `seq`, then `total_bytes`,
  `soft_bytes` and `over`. `db_compact {db}` runs `VACUUM` on the
  browser's copy and returns the bytes before and after; content and
  `seq` are unchanged, so it is not a modifying operation and nothing is
  forwarded. `db_unload {db}` closes the browser's copy and deletes its
  OPFS file and the cache files only it references; the server's copy
  stays, nothing is forwarded, and a later operation on that database is
  an error naming `db_load`. `db_load {db}` fetches the server's copy
  with `db.snapshot`, one blob, and opens it as the start replacement
  does (6.8).
- The largest database is `blob_max` (3.8), what Chrome supports for one
  database in this stack, and the limit of browser storage and of the
  caching and restoring above. Unconfirmed: `db_unload` is the caching,
  the server's replicated copy being the image kept, and `db_load` the
  restoring; no line sends a browser database to the server whole;
  rework is a line that does. A database that grows past `blob_max` is
  not refused (5.5); its image fails loud at a window.
- After each turn the agent compares `total_bytes` with
  `db_soft_bytes`. When over, it adds one system message holding the
  `db_stats` result to the next provider request, and the AI decides
  what to unload, compact, drop or `turn_compact`. There is no timer,
  because time stops. Nothing is evicted automatically but the `_files`
  browser tier (6.7).
- The server side is unchanged: the server evicts nothing (6.7).
- Unconfirmed: the request for "the db admin design/MVC" is read as the
  minimal code of this design, not a model, view and controller split
  (5.1); rework is that split.

## 7 Modules

### 7.1 Naming

- Functions and classes carry two English names; modules and test
  modules are the exception; the maintainer's own identifiers override
  the rule, as `verbose.log` and `verbose.exec` do.
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
- `tap_producer.py`: a `unittest` runner writing TAP with one plan per
  run and one indented subtest block per module. `tap_consumer.py`:
  takes a document, returns stats: plan, pass, fail, skip, and whether
  the stream is well formed.
- Both are written for the engine, following tappy's API and
  implementing only what the engine needs: the producer's
  `TAPTestRunner`, a `unittest.TextTestRunner` with the setters the
  engine needs, such as `set_stream`, and `Tracker` with `add_ok`,
  `add_not_ok`, `add_skip`, `set_plan` and `generate_tap_reports`; the
  consumer's `Parser` with `parse_text` and `parse_line`, yielding the
  line kinds `Result`, `Plan`, `Diagnostic`, `Bail`, `Version` and
  `Unknown`. tappy is not downloaded; compatibility with it is tested
  later. Unconfirmed: the names are recalled from tappy's documentation;
  rework is the names once checked against tappy. Unconfirmed: the
  request's "tap-producer/tap_producer tap-consumer/tap_consumer" is
  read as these module names, a hyphen being no legal module name;
  rework if directories `tap-producer/` and `tap-consumer/` are meant.
- Their own tests, `test_tap_producer.py` and `test_tap_consumer.py`,
  run before every other test. A test can declare that a suite must
  fail in a stated way, and passes when the suite fails exactly that
  way. The producer is exercised so on every way a run can fail: a
  failing assertion and an exception raised in a test; a failing
  `subTest`; errors in `setUp`, in `tearDown`, and in `tearDown` after a
  failure; errors in `setUpClass`, `tearDownClass` and `setUpModule`;
  `expectedFailure` and an unexpected success; a skip; failfast ending
  the run with `Bail out!`; a module that does not load.
- `jslb.py`: `Object`, `header_make`, `blob_make`, `line_make`,
  `field_get`, `headers_of`, `payload_of`, `line_encode`,
  `LineDecoder` with `bytes_feed`, `line_render` (3.11), `WireError`.
  Headers are the `int` keys of the decoded `dict` (3.2).
- `verbose.py`: `log(text)`, `history_get(count)`, and `exec(level,
  argv, argv_verbose)`, the one place an external program is started,
  whose levels are the shell's and the only verbose levels the server
  has (2.3, 2.4): level 0 runs `argv` with its output passed through,
  level 1 runs `argv` with its output passed through and its start and
  exit logged, level 2 runs `argv_verbose`, the caller's command line
  carrying that program's own verbose flags, raw, its output passed
  through and the same two lines logged. Lines go to `_verbose` and the
  ring, with no level. Unconfirmed: level 2 takes a whole
  `argv_verbose` from the caller; rework if the flags are inserted after
  `argv[0]` or appended. Unconfirmed: level 1 passes the output through,
  as a captured level 1 gives dash no input; rework is Markdown
  formatted progress.
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
  `test_browser.py`, `test_posix.py` with the audit of 8.6, and
  `category.py`, the test categories, the runners' options and each
  suite's alarm (8.2).

### 7.3 TypeScript, bottom up

Each is `ts/<name>.ts` with `ts/test_<name>.ts`. API/ts holds the
declarations.

- `error_overlay.ts`, `utility.ts`, `ui_strings.ts`, `settings.ts`,
  `i18n.ts`, `tap_producer.ts` (the producer, with the Python
  producer's names in the namespace `tap_producer`, exercised on the
  same ways to fail but `subTest` and the class and module fixtures its
  harness lacks), `unittest.ts` (`TestCase`,
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
PY  i18n  tap_producer  tap_consumer
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

TS  error_overlay  utility  ui_strings  settings  i18n  tap_producer  unittest
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

- The PowerShell files, `xsjs_*.ps1`, `powershell/*.ps1` and
  `powershell/en-US/*.psd1`, are in `python/reformat_whitelist.txt`, by
  the maintainer's decision of 2026-10-21 (`PLAN_B.md` 2.21). Windows
  formats them: `powershell/test_lint.ps1` reads the whitelist itself,
  matches its lines by the rule `reformat.py` uses, and formats and
  analyses the whitelisted `.ps1` and `.psd1` files, stopping at the first
  fault. Linux formats the rest with `reformat.py`. In `test_posix.py` they
  pass only the character check, with a UTF-8 byte order mark allowed at
  their start, and the comment check, with a PowerShell comment lexer that
  refuses `<# #>` below the header. `python/reformat_table.json` maps each
  extension to its comment lexer, codec, formatter, linter and system; the
  PowerShell rows' system is `windows`, so `reformat.py` formats none of
  them. Unconfirmed: the mark allowed by the codec of those rows
  (`PLAN_B.md` 10.4.44); the banner of `xsjs_install.ps1` stops
  `test_posix.py` until the maintainer chooses (10.4.45).
- The Windows scripts change in two places. The install script builds
  ttyd from the pinned source release with its patches (2.7) in place of
  installing the apt package. The function that starts ttyd runs the
  built binary with `--url-arg`, `--srv-buf-size 1048576`, the index
  file name and the root argument, and passes `XSJS_PROVIDER_KEY` from
  the user's environment into ttyd's; nothing about debug, which is a
  setting.
- `archive.sh` and `clean.sh` are not part of the project.
- `test_posix.sh` at the top and `powershell/test_powershell.ps1` are the
  project's two official test targets (8.2). `test_posix.sh` has no
  verbose levels (`PLAN_B.md` 2.15.2, 10.4.41).
- `.sh` parallels, a Dockerfile and `--container` are doors (10.3), and
  so is `test_posix.sh` run in Docker (10.22).

## 8 Testing

### 8.1 The runner and the stream

- unittest in both languages with identical output text. One TAP plan
  per language per run; each module's suite is one subtest block
  indented four spaces with its own plan, then a parent `ok N -
  <module>` line.
- Every stream is checked by `tap_consumer` on the server: `test_all.py`
  parses its own output; the page sends each TAP line as its own
  `tap.line` as it is produced, and further debug lines ad hoc, and the
  server appends each to `<root>/tap/<language>.tap` unbuffered, so a
  hang leaves the lines before it on disk. The consumer follows tappy's
  `Parser` and returns the stats of 7.2. Unconfirmed: `tap.line
  {language, text}` carries the TAP text, and the consumer returns plan,
  pass, fail, skip and whether the stream is well formed; rework if a
  structured result is wanted: the consumer and the test page.
- `failfast`: the first `not ok` stops the stream with the traceback as
  diagnostics. Side effects between tests are banned; name order is
  fine.
- `test.html` shows the stream with every failed line highlighted whole.
  That colour was requested; it is not decoration. Unconfirmed.

### 8.2 Runners

- Two categories of test suite, the maintainer's (`PLAN_B.md` 2.18):
  `smoke-test`, the important suites that fit in 2 minutes in all, and
  `normal-test`, the others. A `smoke-test` run runs the first; a
  `normal-test` run runs both. A suite is the smallest unit a runner
  starts, times and names on its own: a module of `test_all.py`, a rung
  of `test_wire.py` or `test_browser.py`. `test_posix.py` is one suite,
  and the page's TypeScript modules carry the label of the rung that runs
  them. Each label is written beside its suite. A wire stage or a browser
  root is `smoke-test` when it holds a `smoke-test` rung, and a
  `smoke-test` run starts no other. A `smoke-test` suite needs nothing
  that a `normal-test` suite does. `category.py` holds the two labels, the
  options, the alarm of each suite within a run's limit and the checks of
  these rules. Unconfirmed: each label and the fit in 2 minutes, until the
  testing phase measures them; rework is the labels of `PLAN_B.md` 2.18.4.
- The test driver and the infrastructure for testing (`PLAN_B.md` 2.22).
  `python/test_all.py` is the test driver: it chooses, orders, times and
  runs the test suites. The infrastructure for testing is the code the
  drivers and tests are built from, such as the test categories and their
  deadline: `category.py`, and the TAP modules, whose own tests run first.
  `python/test_test.py` tests the infrastructure for testing, every part
  of `category.py`, and not the test driver; no test module tests the
  driver. Unconfirmed: `alarm_plan` lives in `category.py`, and
  `test_test.py` holds every test of it; rework is `PLAN_B.md` 10.4.52 and
  10.4.53 (10.26).
- The project's two official test targets, which both call
  `python/test_all.py`:
  - `./test_posix.sh [--smoke-test | --normal-test]`, bash at the top. No
    option or `--smoke-test` runs the `smoke-test` suites, and
    `--normal-test` runs both labels; any other argument writes its usage
    and exits 2. It runs `python3 python/test_all.py` with the one option
    from its own directory and exits with its code. It will later run in
    Docker (10.22).
  - `.\powershell\test_powershell.ps1 [--smoke-test | --normal-test]`, on
    Windows as admin. It checks the option first, runs `test_lint.ps1`,
    then the lifecycle, with `wsl --cd <checkout> -e python3
    python/test_all.py <option>` as the step after the status check that
    follows `xsjs_install.ps1`, before the first start. It stops on
    failure, by the maintainer's decision of 2026-10-21: the first failed
    step ends the run with exit code 1, and the later steps, the last
    `xsjs_stop.ps1` among them, do not run, so the lifecycle's state at
    the failure is left as it is (`PLAN_B.md` 2.19.5).
  - `test_posix.sh` and `python/test_posix.py`, the checker of the
    whitelisted files, share a stem; both names are the maintainer's.
- `python3 python/test_all.py [--smoke-test | --normal-test]
  [--failfast]`, `--smoke-test` by default, each option by its full name
  only (the maintainer's decision of 2026-10-21: `--normal` is refused),
  the test driver and the one runner of every suite: the tests of
  `tap_producer` and `tap_consumer` first, then the
  Python suites of the category in dependency order, then, when the
  stream is clean, `test_posix.py`'s checks, `test_wire.py` and
  `test_browser.py`, each given the category, stopping at the first
  failure with its exit code. Each suite's label and measured seconds are
  printed. A `smoke-test` run has 120 s in all: every alarm ends at that
  deadline at the latest, and passing it fails loud naming the suite it
  stopped.
- `python3 python/test_wire.py [--smoke-test | --normal-test]`, the rungs
  of 8.7.3 and 8.7.5 of the category.
- `python3 python/test_browser.py [--smoke-test | --normal-test]`: builds
  `test.html` and the engine pages, each when the first root that serves
  it starts, serves them through ttyd, runs the TypeScript suites in
  headless Chrome, the `tap_producer` tests first in the page's
  `test_all.ts`, reads the `tap.line` stream from the file of 8.1, checks
  it with the consumer, saves a PNG. The one JavaScript runner is a browser. `devtools.py` is
  `page_open(url)`, `script_evaluate(text)`, `console_follow(fn)`,
  `screenshot_save(path)`, `page_close()` over the DevTools protocol,
  implemented by the relay now inside `xsjs_screenshot.py`, split out.
- `test_wire.py` and `test_browser.py` run the ttyd the install script
  built (2.7) and fail naming the install script when it is missing.
- `python3 python/test_posix.py` keeps its role for every whitelisted
  file and gains the audit of 8.6. It checks the PowerShell files'
  characters and comments only, and formats and lints none of them (7.5).
- Every rung and every browser test has a timer; a timer expiring is a
  failure that names the rung.

### 8.3 Cross-language vectors

- `build/vectors/*.jslb`, written by `vectors_make.py` with `jslb.py`
  before the vector tests read them: by `test_all.py` before `test_jslb`,
  and by `page_build.py` for the test page. Empty payloads, every header
  field, both name forms, zero to three blobs, blob bytes holding CR,
  LF, 0x03, 0x04, 0x13 and invalid UTF-8, each hard error, and the
  rendered form of 3.11. Both decoders read every vector, compare to the
  `*.json` sidecar, re-encode, and read the result whole, by single
  bytes, and split at every offset.

### 8.4 The UI thread stress test

- A long task observer on the UI thread during a `kv.put` and a
  `kv.get` each of a blob of `blob_max`, a 128 MiB upload, one message
  within `blob_max`, and a scripted turn with an image requires no task
  over `long_task_ms`, 5 ms, a soft target reported as a measurement,
  and no synchronous network load on the main thread, a hard failure
  found by tracing. The UI's puts go through the test engine page
  (2.5). Only synchronous network loads are detected, not the
  synchronous calls behind `document.cookie` or `localStorage`, which
  the maintainer accepted.

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
  reply line, and `boot.ts`, the one initialization module (1.3).

### 8.7 Stages

Each stage names what is built, what its tests prove, what a person
surveys, and the exit criterion. A stage starts only when the previous
one's exit criterion holds. An exit criterion is met by a `--normal-test`
run (8.2), which runs every rung.

8.7.1 Stage 0, the harness: ttyd built from the pinned release with its
patches (2.7), which `test_browser.py` serves through;
`third_party_fetch.py`, `tap_producer.py`, `tap_consumer.py`, `i18n`,
`test_all.py`, `category.py`, `test_posix.sh`, `tap_producer.ts`, `unittest.ts`, `devtools.py`,
`test_browser.py`, `page_build.py` for the test page, tsc in the build,
`error_overlay.ts`, `utility.ts`, `ui_strings.ts`, `settings.ts`. The
TAP modules' own tests run first in each runner. Proves one passing,
one failing, one raising and one skipped method yield identical TAP in
both languages as one subtest block, accepted by the consumer; every
way a run can fail, each an expected failure of a suite (7.2);
`failfast`; `i18n` raises in both; a thrown error in the test page ends
in the `<pre>` screen; `settings_get` of an unknown id throws and the
frozen object refuses a write. Survey: the TAP text; the PNG. Exit:
both runners exit 0 on the real suites, whose expected failures prove
each way a run fails.

8.7.2 Stage 1, JSLB: `jslb.py`, `jslb.ts`, the vectors, streaming over
`overflow_bytes`, header probing, rendering. Exit: both suites pass;
each reads all the vectors of the other.

8.7.3 Stage 2, the raw wire: `bootstrap.py` with raw mode, the lock and
`hello`, an `echo` handler; `test_wire.py` rungs `hello`, `echo`, `echo
1 MiB with control bytes`, `echo 128 MiB` as one message within
`blob_max`, with ttyd's resident size printed, an echo of a blob of
`blob_max` and a message whose blobs sum to one byte more refused at its
CR, `second connection refused`, `ttyd killed`, and
the last line regression of the rules' Project Direction 1.1, the old
test that keys on the last line of a process that exits right after
printing it, kept as it is: a lone loss there is a ttyd fault, reported
with the ttyd version and not retried. Each rung runs under a timer.
Exit: all rungs pass twice.

8.7.4 Stage 3, the server substrate: `substrate.py`, `settings.py`,
`verbose.py`. Proves the tables created on first use in a new database,
KV on both ref forms, documents, heads, the document round trip of 6.4,
`seq` across reopen, overflow at exactly `overflow_bytes`, snapshot and
restore, a `SIGKILL` between file and row, `kv_check`,
`operation_apply` of a sequence the test builds, `turn_compact`. Exit:
passes under `python3 -X dev`.

8.7.5 Stage 4, dispatch and the main loop: `dispatch.py`, `engine_*`,
`main_loop.py`, `mcp.py`, `mcp_stdio.py`, the main loop download and
restart. Proves through `test_wire.py` and a stdio MCP client written
in the test: `kv.put` and `kv.get` byte identical, `doc.put` and
`doc.head`, `verbose.tail`, `tools/list` and `tools/call` over stdio
and over the `mcp` line, an unknown type giving `error` then exit 1,
`system.restart` serving a second main loop after `source.put` in debug
mode and the same refused without it, an operation sequence the test
builds replayed over the wire (6.8). Exit: rungs pass; pyright clean.

8.7.6 Stage 5, the page reaches the server: `dispatch.ts`, `queue.ts`
with sleep, wake and synchronous mode, `wire.ts`, `http.ts` against a
local stub, `verbose.ts`, `overlay.ts`, `worker_ai.ts` without
databases, `page.ts` showing `hello`. Proves the hello relay, a round
trip of a blob of `blob_max` equal by SHA-256 and a message whose blobs
sum to one byte more refused by `wire.ts` at its post, a UI put of one
byte more refused first by the AI worker's task queue with
`queue.queue_over`, a `kv.get` reply of one byte more refused by the
page's decoder, its value written on the server behind the page's back
since no port carries it (both approved, `PLAN_B.md` 2.20), a
`verbose.put` forwarded from
the UI through the AI worker to the server unchanged, a sleeping task
woken by two replies in either order, the same run identical twice in
synchronous mode, the stress test of 8.4, a fault ending in the `<pre>`
screen and Reload, a close without an `error` line reported as such.
Survey: a PNG with ctrl-1 open. Exit: `test_browser.py` exits 0.

8.7.7 Stage 6, the browser substrate and replication: `substrate.ts` in
the AI worker, the forwarded operations both sides. Proves the stage 3
suite ported, but for what has no meaning on the SAH pool, which has no
WAL: a WAL file left by a kill, `test_wal_left`, is not ported. Proves a
second load finding the rows, overflow files in OPFS, the string to
string table replicated from the UI and from the AI (6.8), the start
replacement of a differing file, the desync reload, and an operation
sequence the test builds, `test_wire.replay_build`'s, replayed into the
page from the UI's queue, the browser's copy then compared with the
server's. Measures the largest database (3.8): a database of the most
4096 byte pages within `blob_max` loaded with `db_load` as one
`db.snapshot` blob, the origin's quota and usage read before it, and the
UI's `db.snapshot` of it compared with the server's file; the rung fails
naming the path and the numbers where one cannot carry it. Exit:
identical counts to the Python suite; the reload test passes.

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
  package, `main_loop/`, the page, `settings.json`, `provider.json`,
  `ttyd.log`, `engine.lock`, `tap/`, the databases and `cache/`. Start
  copies the built ttyd (2.7), the package, the page, the settings,
  `provider.json` beside them, and the seeds there. The provider key is
  `XSJS_PROVIDER_KEY` in the environment of the ttyd process.
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

10.14 Compaction beyond the turn counter.

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

10.19 Verbose levels in the server and the runtime (deferred by the
maintainer on 2026-10-20, "for now only have verbose levels for shell
scripts. the server and runtime only have a debug flag").

- Levels 0, 1 and 2 in the server and in both page threads: 0 only what
  must be said, 1 progress, 2 everything, every task queue event and
  every substrate call included. A line above the level is not written.
- Python: `verbose.level_set(level)` and `verbose.log(level, text)`;
  `_verbose`'s `line` table has a `level INTEGER NOT NULL` column and
  `LogLine` a `level`; `lines_put` checks each page line's level.
- TypeScript: `verbose.level_set(level)` per thread and
  `verbose.log(level, text)`; the ring of `verbose_ring` keeps the lines
  at or under the level; the sink batches them into `verbose.put` when
  `debug` and `verbose_forward` are both on; `lines.VerboseLine` has a
  `level`.
- Settings: `verbose_level` sets the server's level, both threads' and
  the console shell's at start; `verbose_forward` gates the forwarding
  beside `debug`.
- The server at level 2 logs `bootstrap.hello_submit`,
  `main_loop.line_dispatch` and `main_loop.line_reply`, each line's
  header JSON; a failure at level 0. The task manager at level 2 logs
  every submit, dispatch, sleep, wake and reply.
- Tools: `verbose_level {level}` sets the AI worker's level, 0, 1 or 2;
  `script_debug` is `script_run` at level 2, which traces every
  substrate call; a script's `engine.log(level, text)`, the run keeping
  the lines at or under its level; `script.script_run(store, name, args,
  level)`.
- Overlays: verbose level 2 and `verbose_forward` gate the forwarding of
  the page's view, an Unconfirmed reading.
- `verbose.dump(level, name, value)` of 10.17 has a level only with this
  design.
- Rework when it returns: the settings, both verbose modules, the
  queue's and the server's trace, the two tools, `script.ts` and the
  `level` column.

10.20 Compaction by a token estimate sent to the AI (replaced by the
maintainer on 2026-10-20, "just use an event counter and compact when it
reaches a reasonable threshold"). The design built before:

- After each turn the agent estimated the scene's conversation by the
  UTF-8 bytes of the JSON of its turns, taken as never fewer than their
  tokens: bytes counted as tokens, Unconfirmed.
- When the estimate was over the setting `turn_compact_tokens`, 65536,
  the next provider request carried one more system message, after the
  `db_stats` one when both were due, holding only a JSON object of
  `scene`, the scene's Document-Ref, `last`, its last turn's `n`,
  `tokens`, the estimate, and `turn_compact_tokens`.
- The AI decided whether and how far to compact, calling
  `engine.store.turn_compact(scene, through, summary)` from a script
  with a summary it wrote. `agent.ts`'s `TurnLoop.estimate_check` built
  it, and the analyst's seed prompt described it.
- The plan's text before that: `turn_compact(scene)` in the substrate
  replaced turns 1 to N with one summary row when the estimate exceeded
  `turn_compact_tokens`, a heuristic baked into the wrapper.
- Replaced by the event counter of 6.6.

10.21 Snapshots in pieces (replaced by the maintainer on 2026-10-20, "the
max blob size needs to be the same as the max db size"). Built for a
database over the 10 MiB that `message_max` then allowed per message:

- `db.snapshot {db}` replied with a head, `snapshot`, `size`, `sha256`
  and `seq`, and no blob; the server kept the image under the number
  `snapshot`.
- `db.chunk {snapshot, offset, size}` replied with `size` bytes from
  `offset` as blob 1, each piece at most `message_max` minus `line_max`;
  the piece that reached the end let the kept image go.
- The browser's `SnapshotFetch(db, message_max, line_max, full)` asked
  for the head, then each piece in order, assembled the bytes and
  checked their SHA-256 against the head before the restore; the
  TypeScript store kept and served snapshots to the UI the same way,
  with `Store.snapshot_keep`, `Store.snapshot_read` and
  `Store.blob_take`.
- Known defects then: parallel `db_load` calls could each hold a piece
  and reach `queue_max`, and a `kv.get` reply near the largest `kv.put`
  still exceeded `message_max`.
- The sizes it worked under, 10 MiB per blob and per message and 100 MiB
  per queue, are kept in `PLAN_B.md` 2.1.
- Replaced by one blob within `blob_max` (3.8, 6.8).

10.22 `test_posix.sh` in Docker (deferred by the maintainer on 2026-10-21,
"later one will run in docker").

- An image built from the Ubuntu release of the maintainer's WSL (0.4),
  holding from apt: `python3`, `openssl`, and the build tools and headers
  that `xsjs_install.ps1` checks for ttyd (`cmake`, `build-essential`,
  `patch`, `libuv1-dev`, `libjson-c-dev`, `zlib1g-dev`,
  `libwebsockets-dev`, `libssl-dev`). It also holds the tools
  `test_all.py` needs: `tsc` (Node at build time only, 11), `ruff`,
  `shfmt`, `prettier` 3.9.8, `mdformat`, and a Linux Chrome or Chromium
  for `test_browser.py`.
- ttyd is built in the image from the pinned release and its patches
  (2.7), by the build steps of `xsjs_install.ps1` written as its `.sh`
  parallel (10.3).
- `devtools.Browser` starts the container's Chrome directly. The C# relay
  through `powershell.exe` (0.4) serves WSL's NAT only and has no place
  in a container.
- The container runs as a user, not root (10.3), with the checkout bind
  mounted for reading and writing, so `build/` and the kept roots land in
  it. Its command is `./test_posix.sh [--smoke-test | --normal-test]`, and
  its exit code is the run's.
- A `--normal-test` run needs the disk and memory of the edge rungs
  (`PLAN_B.md` 2.13): about 2 GiB per edge root and up to 6 GiB of OPFS.
  Chrome needs a larger `/dev/shm` than Docker's default.
- What starts it, a `docker run` by hand, an option of `test_posix.sh`
  or the `--container` of 10.3, is decided when it is built.
- Rework when it is built: the image file, the ttyd build script,
  `devtools.py`'s start of Chrome, and 8.2.

10.23 Test category designs not built (2026-10-21, `PLAN_B.md` 2.18 and
2.19). Each option a) of `PLAN_B.md` 10.4.33 to 10.4.43 is built; the
others are kept here whole.

- The grain of a label (10.4.33):
  - the runner whole: `test_all.py`'s modules, `test_wire.py`,
    `test_browser.py` and `test_posix.py` each one suite. The browser
    and wire tests then leave the smoke run whole.
  - the root or stage: one label per `session_run` root and per wire
    stage, and no rung labels. The probe root then goes to `normal-test`
    whole for its 2 GiB rungs and 120 s timers, unless it is split into
    a root of its quick rungs and a root of the rest. Each half then
    starts a fresh page, and the moved rungs lose what the earlier rungs
    of the root left them.
  - the stages of 8.7: a label per stage number, read from the prefix of
    the rung names. Stages 5 and 6 mix labels.
- Where the labels are written (10.4.33):
  - one table, a JSON file beside `test_all.py` mapping each module,
    root and rung name to its label, read by every runner. The label
    then stands away from its suite and each name is written twice.
  - held by `test_posix.sh`, which passes the names to run to each
    runner as `--only` arguments.
- The limit (10.4.35):
  - checked once at the end of a `smoke-test` run, failing after every
    `smoke-test` suite ran when the total passed 120 s: the full
    measurements are printed, but the failure is reported late.
  - the seconds reported with no limit, for the maintainer to read.
  - the limit in the target: `test_posix.sh` measures with bash's
    `SECONDS` and runs each runner under coreutils `timeout` with the
    seconds left, turning exit code 124 into a message and exit 1.
    `test_powershell.ps1` would need the same again in PowerShell.
- Defaults and arguments (10.4.36):
  - a runner run alone runs every suite, and the targets pass
    `--smoke-test` by default;
  - the runners require an option;
  - the targets pass every argument through to `test_all.py`,
    `--failfast` included;
  - a `--help` on `test_posix.sh` that prints its usage to stdout and
    exits 0, as `clean.sh` does.
- Suites left out, reported: a TAP point `ok N - <module> # SKIP
  normal-test` for a module left out, through `Tracker.add_skip`, and a
  line per rung left out, so that a `smoke-test` run lists what it did
  not run.
- Messages through `i18n`: names such as `category.label_unknown` in
  `i18n/en-US.json`, where the TAP modules and `devtools.py` use
  f-strings.
- Tests of the targets (10.4.42): a Python test copies `test_posix.sh`
  beside stub runners into a scratch directory and runs it with bash, each
  stub recording its arguments and its exit code. Python running a
  command line utility needs the maintainer's approval. Or a shell test
  script of its own.
- `test_powershell.ps1` (10.4.38 to 10.4.40):
  - the first failure followed by a cleanup stop (replaced by the
    maintainer on 2026-10-21, "make test_powershell.ps1 stop on failure";
    built in this plan before that). At the first failed step after the
    lint step, the script wrote a section `test_cleanup`, "Stopping what
    the lifecycle started", and ran `xsjs_stop.ps1` once more in its own
    PowerShell as a cleanup, not a test, its exit code shown and logged as
    a step's. Then it threw `test_failed_step`, naming the failed step and
    the log, and exited 1. Its reason: to release the task, port proxy,
    firewall rule and password the lifecycle opened, as the Python
    runners' `with` blocks stop ttyd on a failure.
  - the carry-on and the tally kept, an exception to the rule (rejected
    by the maintainer the same day): every lifecycle step ran, the failed
    numbers were collected, and `test_failed_steps` named them at the end,
    so that the last stop still cleaned up.
  - `test_all.py` run before the lint step, or after the whole
    lifecycle;
  - the checkout copied into the Linux file system, for example under
    `~/.cache`, and the tests run there, with `build/` off `/mnt/c`.
- `test_posix.py` in the smoke run (10.4.37): a check that rewrites
  nothing, `ruff format --check`, `prettier --check` and `shfmt --diff`,
  failing on the files a formatter would change; or `test_posix.py`
  labelled `normal-test`.
- Verbose levels for `test_posix.sh` (10.4.41): the shell's level from
  `verbose_level` or an option, its start and exit written at levels 1
  and 2 as `verbose.exec` writes them.

10.24 Labels per TypeScript module (deferred: no TypeScript module is
`normal-test`, `PLAN_B.md` 2.18.2).

- `ts/test_all.ts`'s tables `first_modules`, `page_modules` and
  `worker_modules` become entries of a name, a label and a reader.
  `stream_run` leaves out a module whose label the category does not run,
  through a `ts/category.ts` with the rule of `category.py`.
- The category reaches the page in the test page's address:
  `test_browser.py` opens the suites root's page with `?category=` and the
  category, `boot.test_page` reads it from `location.search`, and the UI
  thread sends it to the AI worker in the payload of `worker.tests`.
- The browser rung "stage 0: typescript suites" then runs in both
  categories, and each TypeScript module's label stands beside it.
- Rework when it is built: `ts/test_all.ts`, `ts/boot.ts`, a
  `ts/category.ts` and its tests, the suites rung and its `API/ts/` stub.

10.25 The PowerShell files and the one table (2026-10-21, `PLAN_B.md`
2.21). Each option a) of `PLAN_B.md` 10.4.44 to 10.4.49 is built; the
others, and the design 1.6 replaced, are kept here whole.

- The PowerShell files outside the whitelist (replaced by the maintainer on
  2026-10-21, "add the powershell reformatting back ... remove it from all
  scanning except the comment scanner and the utf-8 allow list"; built by
  log task 1.20.8). `PLAN_B.md` 2.14 as written for 1.3:
  - 2.14.1 Decision: the PowerShell scripts leave
    `python/reformat_whitelist.txt` and `python/test_posix.py` does not
    scan them. The lines `xsjs_install.ps1`, `xsjs_start.ps1`,
    `xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/*.ps1` and
    `powershell/en-US/*.psd1` go. "Not scanned" covers every check of
    `test_posix.py`: the character check, the formatting, and the comment
    check, which also reads every PowerShell file `_POWERSHELL_GLOBS`
    finds, whitelisted or not; that scan goes too.
  - 2.14.2 READING: `powershell/en-US/*.psd1`, a PowerShell data file and
    not a script, goes with the scripts. Only they read it, its byte order
    mark is the PowerShell rule's, and keeping it scanned would keep the
    handling the decision removes. Rejected: it stays whitelisted, with the
    byte order mark handling and the PowerShell comment lexer kept for it.
    Question 10.4.21.
  - 2.14.3 `test_posix.py`'s PowerShell handling. Removed, because it
    served only the PowerShell files: `_BOM_EXTENSIONS` and the
    `utf-8-sig` choice of `non_ascii_check`, which reads every file as
    `utf-8` again; the `utf-8-sig` of `comments_check`, back to `utf-8`;
    `_POWERSHELL_GLOBS`, `powershell_paths()` and its use in `main`; the
    `.ps1`, `.psm1` and `.psd1` case of `comments_find`,
    `powershell_scan`, `powershell_double_scan` and
    `_POWERSHELL_TOKEN_BREAK`; the PowerShell sentences of the header
    comment and of `main`'s description. Kept, because whitelisted files
    use it: `non_ascii_check`, which refuses U+FEFF like any character
    outside `_NON_ASCII_ALLOWED`, anywhere in any whitelisted file;
    `token_find`'s `utf-8-sig`, which reads only `ts/*.ts` and was not
    made for PowerShell.
  - 2.14.4 `python/test_test_posix.py`, made for log task 1.18.10: the
    tests of a mark accepted at the start of a `.ps1` or `.psd1` file go
    (`test_powershell_marked`, `test_powershell_plain`,
    `test_mark_inside`, `test_column_after`). `test_others_refused` stays
    with `a.py` and `a.ts` and without `a.psm1`: it proves that a
    whitelisted file starting with a byte order mark is refused, which
    every whitelisted file still relies on. The file stays, so log task
    1.20.4 still tracks it; its header and class comments say what is
    left. READING: question 10.4.22.
  - 2.14.5 An exception to 3.8 and to the project rules' whitelist rule: a
    new PowerShell file is not added to the whitelist. The project rules
    are the maintainer's to edit.
  - Built with it, beyond that text (`tmp/handoff_20_L.md` G1): the
    `<# #>` check of `comments_check` and the header clause "not be a
    <# #> comment" were removed, since no lexer was left to find such a
    comment. 1.6 brings both back.
- Where the byte order mark is allowed (10.4.44):
  - b) U+FEFF added to `_NON_ASCII_ALLOWED` as
    `"\N{ZERO WIDTH NO-BREAK SPACE}"`: allowed anywhere in every
    whitelisted file, every row's codec `utf-8`; `test_others_refused`
    becomes a test that the mark passes, and a Python file starting with it
    fails in `tokenize` inside `comments_check`.
  - c) at the start of any whitelisted file: every row's codec
    `utf-8-sig`, or the `encoding` key dropped and both checks reading
    every file as `utf-8-sig`; `test_others_refused` reverses.
  - d) required at the start of a PowerShell file, the design of log task
    1.18.10 (`tmp/handovers_20_1601.md`, 1.18.10.2): `non_ascii_check`
    raises `<path>: no UTF-8 byte order mark` when a file of a PowerShell
    row does not start with EF BB BF, through a sixth row key such as
    `mark` (`required` or `refused`). It fails today on `xsjs_status.ps1`,
    `xsjs_stop.ps1` and `powershell/test_lint.ps1` (`PLAN_B.md` 6.4).
- The banner characters (10.4.45, log item 4.6.6, the options of
  `tmp/handovers_20_1601.md` for log task 1.18.10):
  - b) `"\N{FULL BLOCK}"`, `"\N{LIGHT SHADE}"`, `"\N{MEDIUM SHADE}"` and
    `"\N{DARK SHADE}"` added to `_NON_ASCII_ALLOWED`, for every file.
  - c) a sixth row key, `allowed`, a list of the characters beyond
    `_NON_ASCII_ALLOWED` that the row's files may hold: the four in the
    PowerShell rows, empty in the others, passed to `non_ascii_check` as a
    third argument and joined to the set there.
  - d) the maintainer redraws the banner in ASCII.
  - e) `xsjs_install.ps1` builds the banner at run time: its here string
    holds ASCII stand-ins, one per character, replaced with
    `[string][char]0x2588`, `0x2591`, `0x2592` and `0x2593`.
- Where the table lives (10.4.46):
  - b) a constant `_FILE_TYPES` in `reformat.py`: its rows are literal
    tuples or dicts, since a constant comes before the classes of its file,
    so the rows lose their field names or their types; `test_posix.py`
    reaches it through a public function of `reformat`.
  - c) a shared module `python/file_types.py` holding `FileType`, the
    table and `type_find`, with its tests and an `API/python` stub;
    `reformat.py` and `test_posix.py` import it after setting
    `sys.pycache_prefix`, which `reformat.py` does not do today.
  - A refusal of a repeated key: `json.load` with an `object_pairs_hook`
    that raises when an extension appears twice. Not built: Python keeps
    the last of two equal keys silently.
- How `test_lint.ps1` chooses its files (10.4.47):
  - b) it also reads `python/reformat_table.json` with `ConvertFrom-Json`,
    which Windows PowerShell 5.1 returns as an object whose properties are
    the extensions, takes the names of the properties whose `system` is
    `windows` as `$extensions_`, and throws on a whitelisted file whose
    extension has no row, as `reformat.type_find` does. One source then
    names the PowerShell extensions for both systems.
  - c) it formats every whitelisted file whose extension is not of a
    `linux` row; it too needs the table.
- The matching rule (10.4.48):
  - b) `reformat.py` keeps `glob.glob(pattern, root_dir=...)`, which also
    accepts wildcards in directories, `[...]` sets and a directory as a
    match; `test_lint.ps1` alone refuses those lines, so the two systems
    can disagree until a Windows run fails.
  - c) every whitelist line names one file, with no wildcard, and both
    scripts test that each exists.
- First failure in `test_lint.ps1` (10.4.49), b): the loop collects the
  CRLF fault of every file, prints them all and exits 1; one
  `Invoke-ScriptAnalyzer` over the whole file list prints every result.
- The PowerShell lexer's limits, not built: a `$( )` inside `@" "@` read
  as code, scanning the body as a double quoted string whose end is a line
  that starts with `"@`; `#` after a word read as a comment where
  PowerShell's expression mode would; PowerShell's own parser,
  `[System.Management.Automation.Language.Parser]::ParseFile` in
  `test_lint.ps1`, giving every comment token exactly, which would move the
  comment check to Windows against 1.6's "except the comment scanner".
- A stub `API/python/reformat.pyi`, not written, as no tool has one:

  ```python
  from typing import NamedTuple

  # What handles the whitelisted files of one extension.
  class FileType(NamedTuple):
      comments: str
      encoding: str
      formatter: list[str]
      linter: list[str]
      system: str

  # Returns the table's rows by extension.
  def table_read() -> dict[str, FileType]: ...

  # Returns the row of the file's extension, failing when it has none.
  def type_find(table: dict[str, FileType], path: str) -> FileType: ...

  # Returns the files the whitelist lines match under the root, sorted.
  def paths_match(root_path: str, patterns: list[str]) -> list[str]: ...

  # Returns the files the whitelist's lines match from the top, sorted.
  def whitelist_paths() -> list[str]: ...

  # Runs each formatter of this system once over its files.
  def reformat(paths: list[str]) -> None: ...
  ```

- The synchronization audit through the table, not built: an `audit` row
  key choosing the files `token_find` reads. The audit chooses `ts/*.ts` by
  its own glob, and the whitelist also lists `API/ts/*.ts`.
- Rework when one is chosen: `python/reformat_table.json`,
  `python/reformat.py`, `python/test_posix.py`, their tests and
  `powershell/test_lint.ps1`.

10.26 The tests of the driver and of the infrastructure for testing
(2026-10-21, `PLAN_B.md` 2.22). Each option a) of `PLAN_B.md` 10.4.52 and
10.4.53 is built; the others, the options of the two answered questions
10.4.50 and 10.4.51, and the design 1.7 replaced, are kept here whole.

- The tests of the driver (replaced by the maintainer on 2026-10-21, "just
  test the stuff that is infrastructre for testing, not the test driver in
  there"; built by log task 1.22.2). `python/test_test_all.py` held
  `TestModules` and `TestAlarm`. Its header read: "Tests of test_all: its
  table of modules, each with a label category.py accepts, the TAP modules
  first and no name twice; and alarm_plan, the alarm of a suite, its own
  seconds or the deadline of a smoke-test run, whichever comes first, own
  seconds winning a tie, or a refusal once the deadline has passed. No real
  alarm is armed, since the runner's alarm of this module is running." It
  imported `category, test_all, unittest`. `TestAlarm` called
  `test_all.alarm_plan`, which `test_all.py` defined between
  `StreamWriter` and `suite_load`. `_MODULES` listed the module last, as
  `("test_test_all", "smoke-test")`, after `("test_category",
  "smoke-test")` (`PLAN_B.md` 2.18.4). The table was read with `getattr`,
  as pyright strict reports a private name read from another module
  (`tmp/handoff_20_T2a.md` G18). The part that goes, as written:

  ```python
  # The name of the runner's table of modules, read by name as it is private.
  _MODULES_NAME = "_MODULES"

  # The two categories of run.
  _CATEGORIES = ("smoke-test", "normal-test")


  # Returns the runner's table of modules, each name with its label.
  def modules_get() -> list[tuple[str, str]]:
      modules: list[tuple[str, str]] = getattr(test_all, _MODULES_NAME)
      return modules


  # The table of the modules the runner runs, in order.
  class TestModules(unittest.TestCase):
      # Each label is one that a run of either category accepts.
      def test_labels_valid(self) -> None:
          for name, label in modules_get():
              for chosen in _CATEGORIES:
                  with self.subTest(module=name, category=chosen):
                      category.suite_runs(label, chosen)

      # The tests of the TAP producer and consumer come first.
      def test_tap_first(self) -> None:
          names = [name for name, _ in modules_get()[:2]]
          self.assertEqual(names, ["test_tap_producer", "test_tap_consumer"])

      # No module is listed twice.
      def test_names_unique(self) -> None:
          names = [name for name, _ in modules_get()]
          self.assertEqual(len(set(names)), len(names))

      # The tests of category.py and of the runner itself are listed.
      def test_new_listed(self) -> None:
          names = [name for name, _ in modules_get()]
          self.assertIn("test_category", names)
          self.assertIn("test_test_all", names)
  ```

- The driver's table checked by the driver, not built: `test_all.main`
  raising before its first module when the first two names are not
  `test_tap_producer` and `test_tap_consumer`, or when a name stands twice,
  which keeps the checks of `TestModules` without a test of the driver.
  Nothing asks for it, and a label other than the two already raises in
  `category.suite_runs` when the driver reaches it.
- Where `alarm_plan` lives (`PLAN_B.md` 10.4.52):
  - b) a new module of the infrastructure, `python/deadline.py`, holding
    `alarm_plan` alone, with a stub `API/python/deadline.pyi` of the same
    signature and comment, imported by `test_all.py` inside `main` as
    `category` is. Its tests stay in `python/test_test.py`, which then
    imports both. The limit, its 120 s and `limit_seconds` stay in
    `category.py`.
  - c) as a), with `timer_start(plan)` and `timer_stop()` moved into
    `category.py` beside the plan they arm, `signal` and `types` imported
    there. They stay untested: a real alarm armed in a test would replace
    the alarm the driver runs over that test module.
- The test modules of the infrastructure for testing (`PLAN_B.md`
  10.4.53):
  - b) `python/test_category.py` kept as T2a wrote it, the test module of
    `category.py` but for `alarm_plan`, and `python/test_test.py` holding
    `TestAlarm` alone, importing `category` and `unittest`. `_MODULES`
    then lists `("test_category", "smoke-test")` and then `("test_test",
    "smoke-test")`, last.
  - c) as a), with the classes of `python/test_tap_producer.py` and
    `python/test_tap_consumer.py` moved into `python/test_test.py`, which
    `_MODULES` then lists first, so that the TAP modules' tests still run
    before the rest, as 1.2 asks.
- Abbreviated options (`PLAN_B.md` 10.4.50, answered a)):
  - b) `argparse`'s default kept in `test_all.py` and in the tests' parser,
    the test's input changed to one that is no prefix, such as
    `--normal-tests` or `--all`;
  - c) `options_add` setting `parser.allow_abbrev = False` on the parser it
    is given, one place for all three runners, a change to the caller's
    parser.
- The driver listing its own test module (`PLAN_B.md` 10.4.51, answered
  c)): b) the module left out of `_MODULES` and run by an entry of its own,
  for example every module named `test_test_<runner>` found by a glob, its
  label then not beside its name.
- Rework when one is chosen: `python/category.py`,
  `API/python/category.pyi`, `python/test_test.py`, `python/test_all.py`,
  and for 10.4.53 b) a `python/test_category.py` written again from the
  classes now in `python/test_test.py`.

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
  `EXPLAIN`, and the refusal of writes to `_` tables and to `_settings`
  by name that replaced it: no protections. SQL rules are not a security
  boundary, and nothing refuses the AI API access to the databases.
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
  `verbose.level`: deferred to 10.16 and 10.17; verbose levels in the
  server and the runtime are deferred to 10.19.
- Turns as documents, or as the version history of one document: the
  turn table.
- The apt package of ttyd, and `../ttyd` built by the screenshot tool:
  the latest source release built with the project's patches (2.7).
