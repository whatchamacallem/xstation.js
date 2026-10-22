# REVIEW_EXECUTION: the code review, dispatched

## 1 Scope and authority

1.1 Written on 2026-10-21 at the maintainer's request (17.1). This file is
the plan by which a coordinator session, the administrator agent, dispatches
the whole code review of this checkout: the code the planning documents
called for against the code that is there. A coordinator carries it out with
its agents; the session that wrote this file only wrote it.

1.2 This file stands alone. The planning documents, the engineering logs
and the earlier plan of this review, from which it was made, have been
removed. Everything of them the review needs is restated here: the system
as designed (section 2), the rules for all code (section 3), the decisions
in force (section 4), and for each area what its agent expects to find
(sections 11 and 12).

1.3 The review finds and fixes three kinds of thing (5.3):

1.3.1 U, an undocumented deviation: the code differs from what this file
leads a reader to expect, and nothing records the difference.

1.3.2 M, a mistake: code that is simply incorrect, a test that cannot pass,
a seam whose two sides disagree, a breach of the project rules.

1.3.3 S, a shortcut: a short term substitute put where the expected design
was within reach with more work.

1.4 The review does not revisit judgement calls. Every decision, reading,
assumption, default, approval and chosen option of the planning agents, the
coordinators and the maintainer stands. Every assumption the AI made is
accepted for the purpose of this review (5.1). Section 4 and the Decided
parts of sections 11 and 12 hold them.

1.5 What the review has, and nothing else:

1.5.1 the project rules, which are the maintainer's and reach every agent
in its context; no agent opens the file that holds them;

1.5.2 this file;

1.5.3 the tree it reviews: the code and its comments; the stubs under
`API/` (the public names and signatures of each module, the catalogue of
line types `API/ts/lines.d.ts`, the DDL under `API/sql/`,
`API/mcp/tools.json`, `API/settings.json`); `i18n/en-US.json`;
`settings.json` and `provider.json`.

1.5.4 No agent looks for the removed documents, in the tree, in git's
history or anywhere else. What this file says of them is what is known.
`API/README.md` still names one of them; the census lists that for the
maintainer (12.1).

1.6 Order of authority: the project rules; then the maintainer's words
(4.1) and answers (4.8), the latest first; then the rest of this file; then
the stubs under `API/`. Within this file an area's Expected and Decided
parts are the more specific and win over the general picture of section 2.
Where a stub and this file disagree and no decided item settles it, the
point is a finding (12.1).

1.7 Baseline. When this file was begun HEAD was `7258e51`, and when it was
finished `1545189`. The coordinator records HEAD and `git status --short`
again before the first launch (9.1.2); the commit it records is the
baseline, which every later mention of "the baseline" means and every
prompt carries (15.3). Every change of the review is made against the
baseline and left unstaged for the maintainer, but for the formatter's
staging (14.2).

1.8 Citations inside this file are bare section numbers, such as "(5.3)".
Tasks are named by id, such as "task 1.19"; a finding outside its report is
named `<task id> 4.<n>` (10.3.4).

1.9 Readers: the coordinator, every agent of the review, the maintainer.

## 2 The system in brief

2.1 The map every review agent reads before its own entry: the system as
designed now, the maintainer's decisions and the later records applied, no
history. An item marked Unconfirmed is an assumption the maintainer has not
confirmed; it is accepted for the review. A default is named "D<n>" with
what it says (all in 4.4). A door is a capability kept open and not built
(designs in 4.2; what was decided against in 4.3). Sections 11 and
12 hold each area's detail.

2.2 The product and its terms.

2.2.1 The hyperposition-engine is a web page, served by ttyd from a Python
back end, in which an AI guides a person through experiences shown as large
still images made by generative AI from a database of facts; a template
and development environment where the AI writes each experience's scripts
and schema over the engine's substrate. The page is TypeScript, the back
end ttyd, Python and dash, a permanent division; shell appears only in the
admin scripts and the debug console. `xsjs`, the Windows administration
suite's name, stays. ttyd is a stepping stone: every byte on the wire but
its console protocol is JSLB.

2.2.2 The player starts at a blank black page with one subtitled remark,
"How can I help you?"; the answer goes to the AI, which talks to an MCP
server in the browser's worker. The start is the hyperposition, run by the
analyst, "a very bored British female AI psychoanalyst" with admin control
over the metaverse: fog and a few bright lights, the one scene the player
cannot modify, loaded when no scene is selected. Multiverse: the catalogue
of experiences, the database `metaverse`; universe: one experience design;
world: its global state; region: a disjoint area; scene: a location, each a
new conversation. The player acts and time stops; nothing runs without a
player task and the agent sets no game timers.

2.2.3 Terms. tty 0 is the console, ttyd's own dash under xterm.js; tty 1
the engine, Python speaking JSLB. `hello`: the server's first request on
tty 1. Task manager: the per thread queue of synchronous handlers. Port:
anything that posts and receives lines. Substrate: the single door to
SQLite on both sides. `seq`: a database's count of modifying operations.
Permit tool: one run only after the player accepts. MB means MiB, KB KiB
and GB GiB, always.

2.3 Processes, threads and ttys.

2.3.1 One ttyd per machine runs with `--url-arg`, one program per
WebSocket: `python3 bootstrap.py --root <root>`, the root `~/.cache/xsjs`;
`/ws?arg=console` appends `console`. Each engine connection is one Python
process, no threads, no asyncio: a `select` loop on the pty, `bootstrap.py`
running `main_loop.py`. Neither shell nor Python meets a socket but through
the JSLB dispatcher's single door, but for the console, debug only.

2.3.2 tty 1: no role, raw mode, JSLB, opened by the AI worker at page load;
a second engine connection on a root is refused, `bootstrap.py` failing to
`flock` `<root>/engine.lock`, writing `error` and exiting 1. tty 0: role
`console`; with `debug` true it runs `/bin/dash` through `verbose.exec` at
`verbose_level`, `[dash, "-v"]` its level 2 form, with a scrubbed
environment, the root as working directory and a cooked pty, exiting with
dash's code; with `debug` false it exits 1. ctrl-0 opens it, or the AI
through `console_run`; no log-in beyond ttyd's; sandboxing it is a door.
ttys 2 on are Python, reserved for players. Unconfirmed: the role in
`--url-arg` names the tty, `console`, nothing for the engine, `player2`
onward; ttyd runs one command; the AI worker owns the console socket and
relays it to the UI.

2.3.3 The UI thread builds the DOM once, routes input to the AI worker as
tasks, paints what `render` names, keeps `media_db` (media key to decoded
image, under a budget), hosts the console view and overlays, shows
permission requests and runs `error_overlay`; it owns no SQLite and no
wire. The AI worker owns both WebSockets, the owner table, sqlite3.wasm on
the OPFS SAH pool VFS, every database and the cache, and runs the agent,
MCP, the scripts and replication; a long query stalling the agent is
accepted. A third thread would reuse `queue.ts` and `substrate.ts`.

2.4 ttyd: only the latest source release, 1.7.7, built from source, in
WSL; a later release moves the pin. `python/third_party_fetch.py` fetches
it into `third_party/`, pinned by version and SHA-256 like sqlite3.wasm and
xterm.js; the install script applies the patches in name order and builds
under `build/ttyd/`, installing nothing; start copies the binary to the
root. A patch, `third_party/ttyd/<nn>_<name>.patch`, is made only where no
option serves, backporting upstream; the one, `01_srv_buf_size.patch`
(upstream db77fde), adds `--srv-buf-size`. On exit Linux ttyd closes with
no close frame (1006), possibly dropping the last output; a patch bounding
its unbounded input queue is the alternative to a credit line.

2.5 The first four scripts, settings and debug mode.

2.5.1 The bundle begins `error_overlay`, `utility`, `ui_strings`,
`settings`, then `i18n` and the rest in reference order. `error_overlay.ts`
depends on nothing: on `error`, `unhandledrejection`, resource load
failures and `fault` lines it writes a `<pre>` of the message and stack
over the screen by `document.write`, closes the wire and ends the worker.
`utility.ts` holds `error_wrap`, `fail_now` and the single door routines
(D26: its messages go through `i18n`; `base64_decode` is strict).
`ui_strings.ts` is the table the build fills from `i18n/en-US.json`.

2.5.2 `settings.json` (2.10.9) is copied to the root, loaded into
`_settings` and sent in `hello` unmodified. `settings.ts`, hand written:
`settings_set(value)` once, then `settings_get(id)`; deep frozen outside
debug mode, where `settings_put(id, value)` sends `settings.put`, which
rewrites the root's file for the next `hello`. Debug mode is `debug`,
false in a release: the server gates `console`, `settings.put`,
`source.put`, `system.restart` and `verbose.put` on it, the page the
overlays and `settings_put`; it is the only verbose switch of the server
and the page (2.13). Headers use full names in debug mode, else short (D27:
one `names_full()` in the worker chooses).

2.6 The page. ttyd serves one static file,
`build/hyperposition-engine.html`; nothing is fetched at run time but media
URLs. tsc (D16: TypeScript 5.x) compiles `ts/` with `module` none and
`outFile` into one classic script in reference order, each file one frozen
object named after its module; Node runs only tsc, at build time.
`python/page_build.py` merges `html/engine.html`, `html/engine.css`, the
bundle, sqlite3.wasm as base64 and xterm.js, and prints the SHA-256; the
worker is a Blob URL of the bundle, its entry chosen by `self.name`.
`html/test.html` adds the tests; `html/test_engine.html` adds the test
bundle's `test_hook.ts`, through which a rung submits tasks from the UI's
live queue (`page.test_engine`, `boot.test_engine`); `page_build(name, test,
template)` chooses; the production page holds no test code.

2.6.1 Overlays: ctrl-0 toggles the console view, one hidden xterm.js
(feeding it hidden is an open research goal). ctrl-n, n from 1, toggles tty
n's read only `<pre>` of its last `verbose_ring` rendered lines; in debug
mode that rendering and `console.*` go to the server as `verbose.put`,
which tty 1's overlay does not show. Both show above the image;
unintentional invisibility is a bug. Accepted by the maintainer: the
overlay below the console scrolls its top rows out; the subtitle band lies
over the image's bottom strip.

2.7 JSLB.

2.7.1 `message := line blob*`, `line := json-object CR`: UTF-8 JSON with no
white space outside strings and no CR, so the first CR ends the line; LF
means nothing. Blobs follow at once in header order, each exactly `s`
bytes. Headers sit at the integer keys 0, 1, ..., found by probing from 0
until one is missing, the payload at every other key; the decoder turns a
key of decimal digits, no sign or leading zero, into an integer (Python:
`int` keys; JavaScript: `line[0]`, `headers_of` probing by number). In a
line 1 to `b` are blob headers; in a document 1 on are reference strings.

2.7.2 Line header `t` `type` (required), `v` `version`, `i` `id`, `r`
`reply`, `k` `key`, `b` `blobs`; blob header `s` `size` (required), `k`,
and `d`, never serialized, the bytes or a streamed blob's cache file; other
blob fields are the handler's. One name form per line, full in debug mode;
defaults are not written; integers within plus or minus 2^53. Hard errors,
raised at the first and closing the port, with no resynchronization: no 0
or `t`, `b` unlike the headers, a gap in 1 to `b`, a bad `s`, a digit
payload key, both name forms, an unknown field in the line header, a line
over `line_max` (before buffering), blobs over `blob_max` in sum (when the
line ends). D7: Python accepts an integral
float `b` or `s`. D4: lines before a fault are returned and the fault
raised at the next feed, a streamed file closed on any exception, and end
of input when `LineDecoder.idle()` is false a hard error. D5: no
`WireError` slug. A blob over `overflow_bytes` streams to a cache file,
hashed on the way; the encoder never copies blob bytes. D3: TypeScript
`blob_make(data, key?, fields?, size?)` needs `size` for a cache handle.
The decoders take `(line_max, blob_max, overflow_bytes, sink_make)` in
Python and `(line_max, blob_max, overflow_bytes, sink)` in TypeScript.

2.7.3 One blob window, the maintainer's decision: the largest blob is the
largest database Chrome supports here, every window a blob passes has that
size, and it is one setting, `blob_max`. Unconfirmed: a window counts blob
`s`, never line bytes. The windows: a message's blobs, each task queue, the
wire's `FrameQueue`, the worker's replication queue, `wire.ts`'s post and
each decoder; the server holds no queue. Unconfirmed: `blob_max` is
2147483391, `sqlite3_serialize`'s documented largest allocation;
`rung_blob_max` measures Chrome, and a lower limit is the maintainer's to
set. `line_max`, `overflow_bytes`, `db_soft_bytes` and the media budgets
are not windows; `chunk_bytes` and `srv_buf_size` stay 1 MiB (approved).
Refusals: `jslb.blobs_over` (decoder), `wire.blobs_over` (post),
`queue.queue_over` (queue, the UI path's first window). D24: wire limits
are built after `settings_set`; `hello` is decoded with one line of at most
10 MiB and no blobs.

2.7.4 A line with `i` gets exactly one line with `r` equal to it, on the
same port, its `t` the request's or `error`; an unknown `r` is a hard
error. D2: ids are one counter per thread queue. ttyd frames are `'0' +
bytes`, `'1'` and `'2'` first. The server is raw before it writes; ttyd
runs with `--srv-buf-size 1048576`; `wire.ts` waits for `bufferedAmount`
under one `chunk_bytes`. A close with no `error` line is the fault
"connection closed with code N and no error line"; the wire test reports a
lone loss with the ttyd version, never retrying. Rendering: the JSON text,
then `<blob "n"=K>` per blob, K its key.

2.8 Lanes and the task manager.

2.8.1 Lanes: wire (worker and server, tty 1), console (worker and ttyd's
dash, tty 0), ui-ai (structured clone, buffers moved), mcp (agent and MCP
server, local), http (agent and provider). All carry JSLB but the console
tty. A port has `line_post(line)` and `line_receive(fn)`: local, thread,
wire, and http, which runs `http.request` as a `fetch` under a
`timeout_seconds` timer and posts the response or the timeout as the reply,
`t` `http.request`. A submitter never knows the port. `API/ts/lines.d.ts`
catalogues every line type with lane, direction, blobs and reply.

2.8.2 One `TaskQueue` per thread dispatches one line at a time. Its owner
table maps a type prefix to a thread; a line owned elsewhere passes to that
thread's port unchanged: forwarding. The AI table maps `verbose.` to
`server`, so the type is the instruction; replication is this mechanism.
`task_submit(line, owner?)` and `line_notify(line, owner?)` take an explicit
owner, an API addition that stands for the review and awaits the
maintainer's acceptance (4.5.5); route headers are a door. A handler
returns a reply built with `dispatch.reply_make(request, payload, blobs)`,
nothing, or `task_sleep(state, wait_ids, then_type)` naming every request
it submitted; when all replies are in, a wake of `then_type`, with no `i`,
carries `state` and the replies. An arriving `error` line is a fault. One
task runs at a time on the AI thread, which holds every database;
`transaction_run`, the only way in, cannot span a return, so a sleeper holds
nothing. `queue_synchronous`, debug only, runs every held task before
reading any port, so runs repeat exactly. In debug mode the queue logs every
submit, dispatch, sleep, wake and reply. Blob buffers move, never copy.

2.9 Lifecycle, errors, permission, the console.

2.9.1 Open: `page.ts` creates the worker, which fetches `/token`, opens
`/ws` (subprotocol `tty`) and waits for `hello` (`i` 1: `bootstrap`,
`sha256`, `pid`, `root`, `settings`, `seq` per database, `provider_key`,
and `provider_info` when `provider.scripted` is false). `bootstrap.py` owns
`hello`: `loop_prepare(root)` once before it, then `loop_run(read_fd,
write_fd, root)`. The worker posts `settings.set`, answers, posts
`boot.hello`, replaces each database whose `seq` differs, and renders the
scene of `/$world/scene`. D9: a second `hello`, after `system.restart`, is
a fault. Close: code 1000, ttyd's SIGHUP, the server exits.

2.9.2 A raising server handler writes one `error` line (`r`, `message`,
`stack`), flushed before exit 1. In the page any fault reaches
`error_overlay`, whose Reload, `location.reload()`, is recovery by the
maintainer's decision; the page replicates from the server, the source of
truth, and retries nothing. A close without `error`, a desync and an
expired timer are faults. A crash before the server's log opens reaches
only the terminal (approved). D21: no failure stack in `_verbose`.

2.9.3 A `permit` tool runs after the UI's Accept; Deny returns an error;
Always Allow lasts the tab. The permit set is `console_run` alone, gating
the host's shell; nothing between the AI API and the databases asks or
refuses, and `source_put` and `system_restart` run unasked, on the line and
over stdio. The tool sleeps on `permit.ask`, the UI on `dom.choice` to the
DOM port, answered by a click, an event, not a promise.

2.9.4 `console.open` makes the worker open tty 0 (D23: the reply carries
`token`); `console.output` and `console.input` carry one blob of ttyd's raw
bytes; `console.close` closes; `console.exit` is pushed when ttyd closes,
and ctrl-0 then reopens it. No Python line type serves the console.
`console_run` posts text and a newline, submits `console.read` and sleeps
until the prompt or `timeout_seconds`. Player input: `ui.input` from a DOM
listener; the UI submits `ai.say` or `ai.click` and sleeps with
`ui.turn_end`. Timers stand wherever a wait can fail: the provider request
(`provider.timeout_seconds`), `console_run`, every rung; others are named
constants (3.12).

2.10 The AI and the data.

2.10.1 The model is the set of databases on one thread, not MVC. The
provider is spoken to in the chat completion shape (`/chat/completions`,
`/images/generations` with `b64_json`), xAI only; `provider.ts`, the one
door, builds one `http.request` line, key in `Authorization`. The key,
`XSJS_PROVIDER_KEY` (Unconfirmed name; D8: needed only when
`provider.scripted` is false), comes in `hello` and stays in worker memory.
`provider.json` holds `base_url`, `chat_model`, `image_model`, empty until
the maintainer fills them, read only when `provider.scripted` is false
(Unconfirmed: its name, place, keys). D28: dotted tool names go unmapped.
`provider_script.ts` answers offline from a Script, a table of nodes the
player's integer messages and the tool results walk; no AI runs in tests.
The Script is `/_files/provider/script.json`, seeded with one node and no
replies, so input without a test driver faults (approved); only the HTTP
timeout rung uses a `provider.json`, its own, at a local stub (approved).

2.10.2 A turn is a chain of tasks: `ai.say {text}` or `ai.click {x, y}`
appends the turn and sleeps on the provider request with `ai.model_reply`,
which submits a `tools/call` per tool call, storing nothing; when all are
in, `ai.tool_reply` stores the calling reply with its results in one
transaction and asks again. A reply without tool calls is stored and
answers `ai.say` (D17: its text is the `subtitle`). The system prompt is the
analyst's document, then the universe's (D17: document `prompt` in the
database of the `universe` row whose `world` is `/metaverse/world`).

2.10.3 MCP: `mcp.ts` and `mcp.py`, JSON-RPC 2.0, `initialize`,
`notifications/initialized`, `ping`, `tools/list`, `tools/call`, revision
`2025-06-18` a constant; `message_handle(object)` returns the response or
nothing; transports a local port, the line `mcp`, and `mcp_stdio.py`
(newline delimited). One tool list, prefixes `browser.` and `server.`,
`API/mcp/tools.json` its text. Browser tools: `sql_run` (the single door to
SQL, DDL allowed), `db_*`, `kv_*`, `doc_*`, `script_run`, `script_debug`,
`image_make`, `render`, `console_run` (permit, debug), `verbose_tail`;
server tools `source_put` and `system_restart`, both debug.

2.10.4 Scripts are KV values `script/<name>.js` in `_files`, replicated,
edited with `kv_put`. `script_run` runs one as a task, `new
Function("engine", "args", text)`, `engine` the frozen substrate, `verbose`
and `i18n` APIs, returning the value or the exception, and its log lines;
`script_debug` traces each substrate call (Unconfirmed: a traced run). The
seeded `script/bootstrap.js` makes the universe, world and region databases
with their `world` and `region` tables, the `universe` row and the refs of
2.10.7, and enters a scene. `image_make` writes the decoded `b64_json` to
`_files` and posts `media.store` to the UI; a URL goes as `media.fetch`
(Unconfirmed).

2.10.5 Python's `sqlite3` on the system library; pinned sqlite3.wasm on
the OPFS SAH pool VFS; no version floors or checks; one connection per
database, WAL on the server; names are C identifiers. Databases:
`_settings` (written by the server only, unenforced), `_preferences`
(Unconfirmed: unwritten), `_files`, `_verbose` (server only), `metaverse`,
and the scripts' universe, world and region databases. No schema is
enforced, and nothing refuses a write to any table or database.

2.10.6 The substrate's tables (`API/sql/substrate.sql`), made on first use
in every database: `_meta` (`seq`, bumped with every modifying operation,
and `schema`); `_kv(key, size, sha256, data)`, `data` NULL when cached,
`sha256` naming the file and spotting unchanged writes; `_head(id,
version)`; `_turn(scene, n, role, content)`. No per row `seq`, no
tombstones. D1: a new database is at `seq` 0; `db.create` carries `since`
0, `db.drop` its `seq`, and their reply `seq` check is skipped. A value
over `overflow_bytes`, 128 KiB, lives in `<root>/cache/<sha256 hex>` (OPFS
in the browser), file before row; `kv_check` removes an orphan file.

2.10.7 A Key-Value-Ref is `/$db/$key`, or `$key` within a database; `$key`
is any non empty UTF-8 text, `/` and white space allowed (D18: only a
document's reference strings exclude white space from their key). A
Document-Ref's key is `$id/$version`, the version an integer and the last
segment. A document is that row, JSON: `doc_put` writes head plus one and
moves `_head` in one transaction; versions never change; its headers follow
2.7.1, 1 on being reference strings that `{"$ref": n}` names, and
`doc_encode` and `doc_decode` round trip exactly; a `kv_get` the browser
cannot answer asks the server with `kv.get` first. The one engine contract
is the scene: type `scene`, `subtitle`, an optional `image` ref; the
hyperposition is `/metaverse/hyperposition/1`. `metaverse.universe(name,
title, player, world)` is the one fixed experience table; the engine reads
`/metaverse/player`, `/metaverse/world` and the scene ref in
`/$world/scene` (Unconfirmed: that row shape and the player ref). The
server seeds the hyperposition, the analyst's prompt, those refs and
`script/bootstrap.js` (Unconfirmed: from `python/seed/<id>.json`).

2.10.8 Turns are `_turn` rows in the scene's database, keyed by its
Document-Ref, one provider message each; `turn_compact(scene, through,
summary)` puts one `system` row at 1 in place of 1 to `through`; the AI may
call it. Compaction by an event counter is the maintainer's decision; the
planners' readings, Unconfirmed: the count is the scene's `_turn` rows;
when the browser's `Store.turn_append` adds a `user` turn to a scene of
`turn_compact_turns` (64) or more, it first compacts 1 to the last in the
same transaction, forwarded as `turn.compact` before `turn.append`; the
server never compacts itself; the summary is `substrate.turns_compacted`.

2.10.9 Settings, constants only, sane defaults, no key or password, none
without a reader: `debug`, `queue_synchronous`, `verbose_level`,
`verbose_ring`, `line_max`, `blob_max`, `overflow_bytes`, `chunk_bytes`,
`srv_buf_size`, `media_db_bytes`, `files_browser_bytes`, `db_soft_bytes`,
`turn_compact_turns`, `long_task_ms`, `provider` (`scripted`,
`timeout_seconds`); `message_max`, `queue_max`, `verbose_forward` and
`turn_compact_tokens` are gone. Media tiers: `media_db` evicts by budget,
the browser's `_files` on leaving a scene, the server's never.

2.10.10 Replication: each modifying operation committed in the browser
(`kv_put`, `kv_delete`, `doc_put`, `turn_append`, `turn_compact`,
`db_create`, `db_drop`, modifying `sql_run`) is forwarded as the same line,
in order, one in flight per database, with `since`, the prior `seq`; the
server refuses with `error` a `since` unlike its `seq`, else applies it
(`operation_apply`) and replies with its `seq`. `Store.forward_set(fn)`
emits; the page sends as tasks of the internal types `replicate.next` and
`replicate.done`, a departure that stands for the review and awaits the
maintainer's acceptance (4.5.17). Unconfirmed: the UI's writes are
tasks on the worker's databases. The server is the truth: at start a
differing database is replaced by one `db.snapshot` blob, digest checked;
others stay unloaded. A refused push or a mismatched `seq` is a desync.

2.10.11 Database administration, by heuristics (`page_count`,
`freelist_count`, cached `_kv` sizes), never a quota call; `db_soft_bytes`,
1 GiB, refuses nothing. `db_stats` reports each open database and the
total; `db_compact` vacuums the browser's copy; `db_unload` drops it and its
own cache files; `db_load` restores it from one `db.snapshot` (Unconfirmed:
unload caches, load restores, no line sends a database whole). A database
past `blob_max` is not refused; its image fails at a window. A turn ending
over `db_soft_bytes` adds one system message with `db_stats` to the next
request. Unconfirmed: "the db admin design/MVC" means this minimal code.

2.11 Modules, bottom up. Each Python module has `python/test_<module>.py`,
each TypeScript module `ts/test_<name>.ts`; stubs in `API/` exist for all
but the runners, `test_posix.py`, `reformat.py`, `vectors_make.py`, the
test main loops, `page.ts` and `worker_ai.ts`. Python, in its dependency order:
- `i18n.py`: `i18n(name, *args)`, raising on a missing name or count.
- `tap_producer.py`: `TAPTestRunner` and `Tracker`, the TAP stream.
- `tap_consumer.py`: `Parser`, a stream's plan, pass, fail and skip.
- `jslb.py`: the codec, `LineDecoder` with `bytes_feed` and `idle()`.
- `verbose.py`: `log`, `history_get`, `exec`, `log_open`, `tail_get`.
- `settings.py`: `settings_load(path)`, `settings_check(settings)`.
- `substrate.py`: `Store`, every substrate operation; `schema_apply`.
- `mcp.py`: `Server` and `Client`, JSON-RPC 2.0 and the MCP methods.
- `dispatch.py`: `line_dispatch` calls `fn(line, **payload)`; `reply_make`.
- `engine_kv.py`, `engine_doc.py`, `engine_db.py`, `engine_turn.py`,
  `engine_sql.py`, `engine_verbose.py`, `engine_tap.py`, `engine_mcp.py`,
  `engine_system.py`: a namespace's handlers, `handlers_register(...)`.
- `main_loop.py`: `loop_prepare`, `loop_run`, the select loop; replaceable.
- `bootstrap.py`: role, lock, raw mode, `hello`, main loop, the console.
- `mcp_stdio.py`, beside `bootstrap.py`: `stdio_run`, MCP over stdio.
- `echo_loop.py`, `stall_loop.py`: test main loops no plan names.
- Tools: `page_build`, `third_party_fetch`, `devtools`, `vectors_make`,
  `category`, `test_all`, `test_wire`, `test_browser`, `test_posix`,
  `reformat`; and `python/seed/`, the four seed files.

2.11.1 `bootstrap.py` is immutable outside debug mode; in it `source.put`
stores `<root>/main_loop/<name>` and `system.restart` restarts on it, so
the AI can recover the server. D10: `--main-loop` is refused outside debug
mode and with the console role; a repeated option is an error. TypeScript:
- `error_overlay.ts`, `utility.ts`, `ui_strings.ts`, `settings.ts`: 2.5.
- `i18n.ts`: `i18n(name, ...args)`, Python's placeholder rule.
- `tap_producer.ts`: the Python producer's names in `tap_producer`.
- `unittest.ts`: `TestCase`, `TestSuite`, `TestLoader`, Python's output.
- `verbose.ts`: `log(text)`, `LineRing`, the thread's ring and sink.
- `jslb.ts`: the codec, twin of `jslb.py`.
- `dispatch.ts`: `handler_register`, `line_dispatch`, `reply_make`,
  `task_sleep`.
- `queue.ts`: `TaskQueue`, the ports, owner table, sleeps and wakes.
- `wire.ts`: `WirePort` (tty 1), `ConsolePort` (tty 0), `FrameQueue`.
- `http.ts`: `HttpPort`, a `fetch` under a timer.
- `substrate.ts`: `Store` on sqlite3.wasm, emitting the forwarded lines.
- `mcp.ts`: the JSON-RPC 2.0 server and client.
- `provider.ts`: `chat_request`, `image_request`, the key.
- `provider_script.ts`: the scripted provider.
- `agent.ts`: the turn's tasks.
- `tools_browser.ts`: the browser tools.
- `script.ts`: `script_run` of the AI's scripts.
- `media.ts`: `MediaPort`, `media_db`, `media.store`, `media.fetch`.
- `console_view.ts`: xterm.js and ttyd's client protocol.
- `overlay.ts`: the tty overlays.
- `page.ts`: the UI thread and the DOM port.
- `worker_ai.ts`: the AI worker and its replication queue.
- `boot.ts`: the entry by `self.name`, and initialization.
- `test_all.ts`, `test_hook.ts`: the page's runner and the test hook.

2.11.2 No arrow points up; a test module imports only its module and the
harness; `ts/tsconfig.json` and `ts/tsconfig.test.json` list the files.
TypeScript:

```text
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

2.11.3 Admin scripts: the four `xsjs_*.ps1` and `powershell/`
(`xsjs_util.ps1`, `test_lint.ps1`, `test_powershell.ps1`,
`en-US/i18n.psd1`); ttyd listens on 127.0.0.1:5769 in WSL, `netsh`
forwarding 5768. Start runs the built ttyd with `--url-arg`,
`--srv-buf-size 1048576`, the index file and the root, passing
`XSJS_PROVIDER_KEY`; nothing about debug. D31: the Windows ttyd report step
stays. `test_lint.ps1` formats and analyses the PowerShell files on
Windows; Linux checks only their characters and comments (Unconfirmed: a
UTF-8 byte order mark allowed at the start by the codec of their rows); the
banner of `xsjs_install.ps1` stops `test_posix.py` until the maintainer
answers (4.8.4.39). D22: the previous design's files and
lines it lists stay untouched until the maintainer decides. `archive.sh`
and `clean.sh` are not the project's.

2.12 Testing.

2.12.1 unittest in both languages, identical text; one TAP plan per
language per run, each module a block indented four spaces, then `ok N -
<module>` (D12: block plan first, no `# Subtest`, bare method names, a
failfast block ending `Bail out! failfast`). `tap_consumer` checks every
stream; the page sends each line as `tap.line {language, text}`, appended
unbuffered to `<root>/tap/<language>.tap` (Unconfirmed). The TAP modules
are custom after tappy's API, tappy not downloaded (Unconfirmed: the names,
recalled, and the module names read from "tap-producer/tap_producer
tap-consumer/tap_consumer"); their tests run first, and prove every way a
run can fail as a suite expected to fail that way.

2.12.2 Categories, the maintainer's: `smoke-test`, the important suites
fitting 2 minutes in all, and `normal-test`; a normal run runs both. A
suite is a `_MODULES` module, a wire or browser rung, or `test_posix.py`;
the page's TypeScript suites carry their rung's label. Every label stands
beside its suite; a smoke suite needs no normal one; a stage or root is
smoke when it holds a smoke rung, and a smoke run starts no other;
`category.LabelBook` raises on a breach.
Unconfirmed: the labels and the fit. Smoke: the unit modules, the two
"stage 0: typescript suites" rungs, `test_posix.py`, every wire rung but
"echo blob_max" and "echo 128 MiB", and the browser root "fresh".

2.12.3 The test driver, `python/test_all.py`, chooses, orders, times and
runs the suites: `[--smoke-test | --normal-test] [--failfast]`, smoke by
default, full names only; TAP tests first, Python suites in dependency
order, then, if clean, `test_posix.py`, `test_wire.py`, `test_browser.py`
through their `main`; it stops at the first failure with its code and
prints `<module>: <label>, <s> s` and `the <category> run took <s> s`. A
smoke run has 120 s, every alarm ending by it, overrun failing loud naming
the suite, any failure ending the run; a normal run has no limit and stops
early only with `--failfast`. The infrastructure for testing, what the
drivers and tests are built from, is `category.py` (labels, `options_add`,
`limit_seconds`, `alarm_plan`, `LabelBook`) and the TAP modules;
`python/test_test.py` holds every test of `category.py`, the TAP modules
keep their own test modules, run first, and nothing tests the driver.

2.12.4 Targets, the maintainer's: `./test_posix.sh [--smoke-test |
--normal-test]`, exit 2 on anything else, `exec python3 python/test_all.py
<option>` (Docker later, a door); `powershell\test_powershell.ps1`, same
options, admin on Windows: option check, `test_lint.ps1`, the lifecycle,
`wsl.exe --cd <checkout> -e python3 python/test_all.py <option>` after the
status check that follows `xsjs_install.ps1`; by the maintainer's decision
the first failed step throws `test_failed_step`, exits 1 and runs nothing
later. `--failfast` does not pass through. No test runs the targets or
`test_lint.ps1`.

2.12.5 `test_wire.py` drives Linux ttyd on roots under `build/`;
`test_browser.py` serves the pages through ttyd to headless Windows Chrome
or Edge, checks the `tap.line` file and saves a PNG; run alone, both keep
`argparse`'s abbreviations. `devtools.py` is the C# DevTools relay run by
`powershell.exe` (D15: `page_open` waits, bounded, on
`net::ERR_CONNECTION_REFUSED`). `test_posix.py` checks each whitelisted
file by its row of `reformat_table.json`, audits `ts/*.ts`, runs the
formatters, which rewrite files each run, and `ruff check`. Every rung has
a timer whose expiry fails naming it.

2.12.6 Vectors: `build/vectors/*.jslb` and `*.json` sidecars from
`vectors_make.py`, read by both decoders whole, by bytes and split at every
offset; `python/vectors/` is left empty for the maintainer. Stress: no UI
task over `long_task_ms`, 5 ms (soft, measured), and no synchronous network
load (hard; only those are detected, accepted). Stubs: every operation of
the metaverse through the scripted provider and the seeded bootstrap
script. Audit: `await`, `.then(`, `new
Promise`, `Atomics` and `SharedArrayBuffer` fail in `ts/*.ts` but
`queue.ts`, `wire.ts`, `http.ts`, `media.ts` and `boot.ts` (D29: not
`async`).

2.12.7 Stages, their order set aside by the maintainer: all written, none
run; an exit is a `--normal-test` run.
- 0 harness: ttyd, fetch, TAP, i18n, driver, page build, first four.
- 1 JSLB: both codecs and the vectors, each reading the other's.
- 2 raw wire: raw mode, lock, `hello`, echo to `blob_max`; twice.
- 3 server substrate: refs, documents, `seq`, overflow, snapshot, kill.
- 4 dispatch and main loop: handlers, MCP, restart, a replayed sequence.
- 5 page to server: lanes, queue, `blob_max` refusals, stress, Reload.
- 6 browser substrate: stage 3 ported, replication, `rung_blob_max`.
- 7 console: `console_view.ts`, the lane, permission, `console_run`.
- 8 hyperposition: the AI side and seeds, end to end, no time passing.
- 9 beachhead: the Windows scripts, the maintainer's hand test, sign-off.

2.13 Verbose levels. For now only the shell has levels, by the maintainer's
decision; the server and the runtime have only `debug`, their level design
a door. Unconfirmed: the shell is the console's dash and what runs in it,
and future `.sh` admin scripts; PowerShell and `test_posix.sh` have none.
`verbose.exec(level, argv, argv_verbose)`, the one place an external
program starts: 0 runs `argv` passed through; 1 also logs start and exit;
2 runs `argv_verbose`, carrying the program's own flags, raw (Unconfirmed:
a whole `argv_verbose`; level 1 passing output through). `verbose.log(text)`
has no level on either side; the server logs failures always and its trace
of each line, header JSON only (Unconfirmed), in debug mode only; the
runtime's queue trace and `verbose.put` forwarding are debug only too. D13:
`verbose.tail_get(thread, count)` serves `ui` and `ai`.

2.14 Operations. The beachhead runs from the maintainer's own WSL account,
started by the Windows scripts; nothing as root, no service manager, no
container. The root `~/.cache/xsjs/` holds `ttyd`, the Python package,
`main_loop/`, the page, `settings.json`, `provider.json`, `ttyd.log`,
`engine.lock`, `tap/`, the databases and `cache/`, copied there by start
with the seeds; as built, a departure that stands for the review and awaits
the maintainer's acceptance (4.5.18), the package is `<root>/python/` with
`<root>/i18n/`; that start writes `ttyd.log` under `%LOCALAPPDATA%` is open
(4.7). WSL has Python 3.14.4 with SQLite 3.46.1 and Node 22.22.1 without
`tsc`, which is asked of the maintainer.

## 3 Rules for all code

3.1 These rules bind every fix and every line of code the review writes,
beside the project rules, which every agent has in its context and which
this section does not restate. They came out of the planning and the
earlier reviews and stay in force. Section 5 says how a decision of section
4 that breaks one of them is treated; section 6 holds the review's own
rules for making a fix.

3.2 Method.

3.2.1 APIs before code. Every protocol is emulated as the real protocol
from its first line: MCP is JSON-RPC 2.0, the provider is spoken to in the
chat completion shape, TAP is TAP. The order of work is: design the module
and its stub under `API/`, write its test module, write the module, fix it,
then stack the next module on it, with calls going one way, down. No module
calls up or sideways; no arrow of the dependency graph points up; a test
module imports only its module and the test harness. Nothing is a prototype
or a draft: each module is the final module behind its API, and work that
would need an API rewritten later is not started.

3.2.2 The stages. The design builds bottom up in stages, each started when
the previous one's exit criterion holds. The maintainer set that order
aside for this checkout by asking for all the code first and a stop before
the testing phase: every stage is written and none is run yet; the testing
phase proves them (section 7 says what this review runs).

3.2.3 Nothing unmotivated. Nothing concrete exists ahead of the prose that
describes it: a module, line type, table, tool or setting appears only with
its request. A capability a request names that nothing needs yet is a
design kept in 4.2, not code. Existing code is current state, not
design, and is reused only where the design chooses it; that some code
exists is never the reason.

3.2.4 Fail fast. No error is swallowed, defaulted or retried. A failed
server handler writes one `error` line and exits 1. In the page,
`error_overlay` replaces the screen with the message and the call stack in
a `<pre>` and stops the app; recovery is a full page reload, the tested
path, and resync is reloading the client. TypeScript error handling is
canonical: `strict` is on, every thrown value is an `Error`, with `cause`
when it wraps another, and no `catch` is empty.

3.2.5 One synchronization tool. The task manager is the only one. A
handler is synchronous; a handler that must wait returns a sleep to the
task manager, which wakes it with the replies as a new task. No promise,
lock, shared buffer or `Atomics` exists outside the task manager and the
ports it owns. The synchronization audit of `python/test_posix.py` enforces
it over `ts/*.ts`, refusing `await`, `.then(`, `new Promise`, `Atomics` and
`SharedArrayBuffer` outside `queue.ts`, `wire.ts`, `http.ts` and
`media.ts`, the four modules that turn an event of the platform (a socket,
a response, a decoded image) into a reply line, and `boot.ts`. D29: `async`
is not among the audited tokens.

3.2.6 System initialization need not abide by the rules for how the system
is used unless that is reasonably convenient. The AI worker's
initialization (`sqlite3InitModule`, `installOpfsSAHPoolVfs` and its
capacity, the OPFS directory, its file handles and `createSyncAccessHandle`
for the cache files) uses promises directly in one module, `boot.ts`,
which the audit exempts by name; no port turns them into lines, and no
platform port is built in `queue.ts`. Once it has handed the objects over,
the system runs under 3.2.5.

3.2.7 Encode and decode before use: JSLB's encoder and decoder are proven,
in both languages, against the vectors before the format carries anything;
stage 1 is that proof and nothing else.

3.2.8 An agent that meets an assumption marked Unconfirmed uses it and
decides nothing; for this review every such assumption is accepted.

3.3 TypeScript handlers:
- A handler returns a finished reply line built with
  `dispatch.reply_make(request, payload, blobs)`, a `Sleep`, or nothing.
- A wake line carries no `i`. A wake handler that owes a reply builds it
  from the original request line kept in its `state`.
- Every request a handler run submits is named in that run's sleep.
- `task_submit(line, owner?)` and `line_notify(line, owner?)` take an
  explicit owner.
- Replies on the http lane have `t` `http.request`.
- An arriving `error` line is a fault.
- Ids are one counter per queue, and no TypeScript module calls
  `dispatch.id_next`.

3.4 Bytes. `Store.kv_put(ref, data)` takes bytes, `Uint8Array` or `bytes`.
A string is a cache file path in Python and a cache handle in TypeScript,
never text. Text is encoded with `TextEncoder` and read back with
`TextDecoder`.

3.5 Tests:
- A test that expects an error compares the message with the `i18n(name,
  args)` text, never only a base class (D5: `WireError` has no slug).
- A fixture reads `document` and other thread bound globals in `setUp`,
  never at construction.
- No test enshrines the implementation's number where a recorded number
  exists.
- Side effects between tests are banned: no test leaves state another test
  sees; name order is fine.
- Each module has its test module beside it: `python/test_<module>.py`
  holding `unittest.TestCase` classes, `ts/test_<name>.ts` in TypeScript.
- A count a test sets, such as a small compaction threshold, is a named
  constant whose comment says its writer chose it, never a bare literal; an
  earlier audit applied this against the project rules' ban on fake data.
- D25: exports made only for tests stay.

3.6 Style:
- Every class and function identifier has two English words, private ones
  too; the exceptions are module names and the names of 3.11.
- One comment line per construct, never two consecutive comment lines.
- No `isinstance` or `is None` branch whose only purpose is to narrow a
  type; `cast` is used instead.
- `i18n` is always called with a literal name at the call site.

3.7 `bootstrap.py` owns the whole `hello` exchange; the main loop never sees
it. `bootstrap` calls `loop_prepare(root)` once, before `hello`, then
`loop_run(read_fd, write_fd, root)`; every replacement main loop defines
`loop_prepare`.

3.8 Errors:
- A module with no handler for a case makes no branch for it.
- A JSON parse failure of any kind in a decoder is a `WireError`.
- A decoder fault is raised once, and the port closes.
- Lines completed before a fault are returned, and the fault is raised by
  the next feed.

3.9 Strings. Every message of an engine module goes through `i18n`, in
both languages: `i18n("name", ...args)`, which raises on a missing name or
on a placeholder count that differs from the argument count. Strings live
in `i18n/en-US.json`, a tracked source file, read by Python and substituted
into `ui_strings.ts` by the build, so both languages read the same names.
Each task writes its strings in a fragment of its own, and the fragments
are merged into `i18n/en-US.json`; section 10 says where this review's
fragments go and section 14 who merges them. D26: `utility`'s messages go
through `i18n`. The tools do not use `i18n`: the runners, `category.py`,
the TAP modules, `devtools.py`, `reformat.py` and `test_posix.py` write
f-strings and literal strings. PowerShell keeps its strings in
`powershell/en-US/i18n.psd1`; `powershell/test_lint.ps1` writes literal
strings, as tools do.

3.10 The whitelist. Each new source file goes in
`python/reformat_whitelist.txt` when it is created. `.md`, `.json` and
`.css` files are not added. PowerShell files are added like any other
source file, as the maintainer returned them to the whitelist.

3.11 Naming. Functions and classes carry two English names; modules and
test modules are the exception, and the maintainer's own identifiers
override the rule. These names stand though they break it, each given by
the maintainer, by the plans or by a stub: `verbose.exec` and `verbose.log`
(the maintainer's); `i18n`; each runner's `main`; `reformat.reformat`;
`LineDecoder.idle()`; `rung_blob_max`; `test_test`; and every name a stub
under `API/` declares, such as `Store`, `Server`, `Client`, `Object`,
`Browser`, `Overlay` and tappy's `Tracker`, `Parser`, `Line`, `Result`,
`Plan`, `Diagnostic`, `Bail`, `Version` and `Unknown`. PowerShell code
keeps its files' own naming style, as `_test_lint_get_paths` and
`$extensions_` do.

3.12 Constants and timers.

3.12.1 Python constants are `_UPPER_NAME` at the top of each file, after
the imports. TypeScript has one frozen `constants` object per module, and
each TypeScript file defines one frozen object named after its module.

3.12.2 Timers exist wherever a wait can fail: the provider request, the
console command, every test rung, whose expiry is a failure naming the
rung. The provider request waits `provider.timeout_seconds` and the
console command `console_run`'s `timeout_seconds` argument. Every other
timer is a named constant holding a sane default, its one line comment
saying it is a default chosen by its writer; the 120 s lengths written
before stay as defaults. The agent sets no game timers: time stops.

3.12.3 The design's tunable constants are entries of `settings.json`, each
with a sane default, never a password or a key; a constant no module reads
is not there.

3.13 Imports. Each Python file imports its modules on the fewest lines that
stay within 79 columns, `import a, b, c` in alphabetical order. `from` is
used only for `collections.abc` and `typing`, each on one line with its
names in alphabetical order, and for `from i18n import i18n`, the one
further exception, which the maintainer decided and the project rules do
not yet hold; that gap is the maintainer's to close, so it is reported and
the rules are not edited.

3.14 No refusals. SQL rules are not a security boundary, so nothing is
built as one: no substrate, engine handler or tool refuses a write to any
table or database, no fixed schema is enforced, and nothing between the AI
API and the databases asks permission or refuses; the one permit tool is
`console_run`, which gates the host's shell. A database that grows past
`blob_max` is not refused; its image fails loud where it meets a window.
Nothing checks versions and nothing sets a version floor.

3.15 Units and PowerShell. MB means MiB, KB KiB and GB GiB, always, in code,
comments and messages. Three PowerShell files, `xsjs_stop.ps1`,
`xsjs_status.ps1` and `powershell/test_lint.ps1`, have no UTF-8 byte order
mark, which the PowerShell rule of the earlier job's agent instructions
requires, not the project rules; that is open (4.7.1), and D22, the hold
on parts of the previous design, holds the first two.

3.16 Formatting belongs to the formatter run of section 14; section 6 says
what an agent writes by hand. An earlier coordinator read the refill
of a comment paragraph that an edit had left with a one word line, at 79
columns with the same words in the same order, as the repair of the edit's
damage, not as polish.

## 4 The register of decisions in force

4.0 This section holds, for the whole job, what is decided, deliberately
left, still open or left undone; the Decided, Open and Candidates parts of
sections 11 and 12 hold the same for each area. Each item is accepted
(5.1), open (5.2) or a candidate (5.1.2, 5.3.2) as its part says.

4.0.1 In the quotes of 4.1 the name of the project rules file is replaced
by "[the project rules file]", as the project rules forbid that name
outside itself; nothing else in a quote is changed.

4.1 The maintainer's words, verbatim. Each message of the maintainer that
the earlier jobs kept is copied below in a text block, exactly as typed,
typing errors included. Three marks differ from the typed text, the same
everywhere. A message line longer than this page allows is broken at a
single space, and its continuation is indented by two spaces; the break and
the indent stand for that one space. The project rules file's name, wherever
a message names it, is written `[the project rules file]`, because no file
but the project rules may name it. One ellipsis character is written as
three dots, because this file is ASCII. Beside these three, the spaces that
ended two typed lines are not kept. A message that names a document that
no longer exists is followed by a line saying so. The messages from 4.1.1
to 4.1.7 are those the earlier job's plan kept as its first authority, in
its order; the messages from 4.1.8 to 4.1.21 are the others the records
kept, in time order, each introduced by the date and time its session
began; 4.1.22 holds the short messages that stopped, resumed and steered
the agents of the two coordinated sessions.

4.1.1 Received on 2026-10-19 at 20:51.

```text
please incorperate this feed back from the maintainer """have max 10MB per
  blob. max 10MB combined total blobs+json. max 100MB for any JSLB queue. soft
  limit of1GB for all the DBs using heuristics. don't worry about too many
  DBs. the AI API needs a plan to live within the browsers cache size for fast
  MCP operations. it needs db admin commands to know when and how to compact
  the set of DBs it is operating. this would be a nice problem to have. remove
  db table protection rules like the protextion on _ or _settings. the sql
  rules are not a sufficient security boundry so they are not being set up as
  such. remove all protections from any db that are being added. just use the
  real TAP api and forget the test code. please don't forget verbose level 2.
  rename the verbose fn that runs commands "exec" """ and this feedback from a
  reviewer """
3.2 Invented values. These are the 120-second timeouts in the Python test
  runner and in the browser connection code (nobody specified a length), plus
  the guessed log times.

3.3 The formatter's file list was not updated. New TypeScript, test-output,
  seed-script and HTML files were never added, although new source files must
  be added when they are created.

3.4 The code can't be loaded. The combined strings file i18n/en-US.json was
  never assembled, so every engine module fails as soon as it is imported.

3.5 Fallbacks and "just in case" code, against the no-fallbacks rule:

the main loop prepares the root directory itself if the preparation step was
  skipped
closing a log that isn't open is quietly accepted
an unreachable return 0
output flushes that have nothing to flush
a duplicate directory creation
type-check branches that can never run
a second, hand-written JSON encoder in bootstrap's error path
two error messages for conditions that can't happen
3.6 Names that don't follow the two-English-words rule: _State in nine
  modules, Loopback and Recorder each have one word, and json_media_is has
  three.

3.7 A silent substitution. The new connection test needs an echo handler that
  nobody was assigned to write. Meanwhile the test runner still runs the old
  design's connection test in place of the new one.
"""
```

4.1.2 Received on 2026-10-19 after 20:59 and before 21:11, a time not
measured; the session's record gives 21:01.

```text
write PLAN_B.md with all the updates from the last two message from the
  maintiner and the PLANNING_UPDATE.md that need to be rememeberd going
  forward. keep these last two messages verbatum. """    i want a tap JS and
  PY producer custom written and a PY consuper custom written following the
  tappy apis but just implement the code you need in local
  tap-producer/tap_producer tap-consumer/tap_consumer modules and have tests
  for them and start by running those tests before running the rest. have a
  way to test expected failure, so you can say you expect a suite to fail a
  certain way and consider that success. then the tap producers cant be
  exercised to handle failure correctly in all the ways they have to. MB is
  MiB always. add the db admin design/MVC. don't download tappy, it can be
  tested later. use sane timer defaults."""
```

The two documents this message names no longer exist; the first is the plan
it asked for.

4.1.3 Received on 2026-10-20 at 22:58, after the postmortem of that day's
coordinated job. Its "before testing" list was that postmortem's list of
what the maintainer does before testing, numbered 1 to 5 in the
conversation: 1, fix the git index of `python/devtools.py`, which tracked an
agent's lock name; 2, apply the `API/` texts of three agents; 3, run the
formatters, twice if a run is not stable; 4, decide the class B items and
the other findings; 5, track five new files. The four numbers the message
names are tasks of that job, in order: a database over 10 MiB can be sent
to the browser as a snapshot, loaded and restored; `python/test_posix.py`
reads the whitelisted PowerShell files past their byte order mark; verbose
level 2; the `turn_compact_tokens` estimate.

```text
please perform "before testing" above 1 2 3 5... all A are fine. assume all
  class B are approved, except update plan for these: 1.18.5  the max blob
  size needs to be the same as the max db size. whatever chrome supports for 1
  large db is the max for browser storage (and caching to server as an
  image/restoring admin operations) needs to be the max blob window and every
  window a blow goes through needs to be the same size and a single
  settings.json entry.  1.18.10 (remove the powershell scripts from the
  whitelist.txt so they are not scanned. 1.18.16 for now only have verbose
  levels for shell scripts. the server and runtime only have a debug flag.
  1.18.18.1 just use an event counter and compact when it reaches a
  reasonable threshold.
```

4.1.4 Received on 2026-10-21 at 10:59. "The above B class calls" are the
class B items the coordinator's messages had named since its first turn on
the order of 4.1.18 (4.8.3). The script it names, `test_all.sh`, was renamed
`test_posix.sh` by 4.1.5.

```text
i aprove the above B  class calls. define 2 categories of test "smoke-test",
  "normal-test". have test_all.sh run by default whatever important test
  suites fit in 2 minutes by labelling those smoke-tests and running only them
  when asked to run the smoke-test suites. then have the option to run
  smoke-test and those labelled normal-test during normal testing. schedule
  this now
```

4.1.5 Received on 2026-10-21 at 11:09. One file name is elided as
`[the project rules file]`; the typed text named the project rules file.

```text
have @powershell/test_powershell.ps1 call python/test_all.py inside WSL.
  instead of test_all.sh call it "test_posix.sh " and have test_posix.sh call
  python/test_all.py. then test_powershell.ps1 and test_posix.sh  are the two
  offical test targets for the wole project. one runs on windows and later one
  will run in docker. update [the project rules file] and the doc and
  shcedule this new request
```

The planning documents this message calls "the doc" no longer exist.

4.1.6 Received on 2026-10-21 at 11:30.

```text
make test_powershell.ps1 stop on failure.  add the powershell reformatting
  back and add the BOM to the allow list and whatever is needed. remove it
  from all scanning except the comment scanner and the utf-8 allow list. make
  the table of file extension to scanner type be data driven. except
  powershell, just the the ps scripts handle formatting on thier own by
  reading the whitelist on thier own. the are different OS so there has to be
  a split.
```

4.1.7 Received on 2026-10-21 at 11:58. One file name is elided as in 4.1.5.

```text
i want "--normal-test" that worked great.  rename test_test_all to test_test
  and just test the stuff that is infrastructre for testing, not the test
  driver in there. update [the project rules file] and the docs to explain the
  destinction.
```

The planning documents this message calls "the docs" no longer exist.

4.1.8 2026-10-19 14:13, the request that began the first coordinated job.

```text
read @hyperposition-plan.md  ... you are the agent coordinator, execute the
  code writing part of the plan using lots of agents. no testing is allowed
  between agent
handoffs. use a file renaming scheme where task ids are appended to filenames
for the duration of an edit. don't run,
build or test anything ever, just be the best coordinator and then stop so i
  can review
changes. im afk, cant talk, but we will go over the unstaged changes after
  before
we test. please enact everything entirely as requested now. then stop before
  the testing
phase of the plan. that means apis, unit tests and integration tests written
  but not executed. everything. once the code is there a code review process
  will start, but we are just going to write the code now.   please enact that
  doc, thank you.
```

The document this message names no longer exists.

4.1.9 2026-10-19 18:27, the request of a review session; "the last commit"
was the first job's commit.

```text
do a code review of the last commit (which is all the changes in progress)
  for the coordinator agent overseeing the changes in progress and write
  tmp/PLANNING_UPDATE.md to instruct it to correct any shortcomings
```

The document this message names no longer exists.

4.1.10 2026-10-19 20:16, the request that resumed the job after that review.

```text
read tmp/PLANNING_UPDATE.md and @hyperposition-plan.md. work was intteruped
  in progress and is now being resumed after a review.

you are the agent coordinator, execute the plan. no testing is allowed
  between agent
handoffs. use a file renaming scheme where task ids are appended to filenames
for the duration of an edit. don't run,
build or test anything ever, just be the best coordinator and then stop so i
  can review
changes. im afk, cant talk, but we will go over the unstaged changes after
  before
we test. please enact everything entirely as requested now. then stop before
  the testing
phase of the plan
```

The two documents this message names no longer exist.

4.1.11 2026-10-19 20:18, the request of an explanation session beside the
job.

```text
i got this feedback about PLANNING_UPDATE.md """
Unresolved after this document

Decisions D6 (plan 3.8 memory bound contradicts itself), D22 (previous-design
  files) and D19's fixed schemas (_files/_preferences) are on HOLD for you.
Class B items, i.e. modified with cause but unconfirmed by you: the writers'
  TAP grammar, which departs from DATA/06 (the document defaults to following
  DATA/06); the coordinator's API additions and plan departures (explicit
  queue owner route, replication as page tasks, root layout); and verbose
  level 2 "flags passed on", which is unimplemented.
Class A items are in the document's section 6.4.
""" please explain without refs ti external sources
```

The document this message names, the `DATA/` directory and the plan it
cites no longer exist.

4.1.12 From the session of 2026-10-19 20:16, received on 2026-10-20 after
09:04, when the coordinator had stopped at the maintainer's "stop all".

```text
just explain the 3 questions tersely """ (async setup, the permission-marked
  tools, the wire.ts timers) are still waiting on you.""" here in chat and
  stop.
```

4.1.13 From the session of 2026-10-19 20:16, received after 4.1.12 and
before 09:32 on 2026-10-20. The file name is elided twice. Its answers are
in 4.8.1.3.

```text
please continue, here are your responses. 1: System initialization does not
  have to abide by the rules for how the system it is used unless it is
  reasonably convinent for it to do so. update [the project rules file] with
  that one. 2: i injected an article into your context about how things that
  were never a requirement become requirements incorrectly and then the user
  is refused when he tries to lifer the requirement. this is a violation of
  the API agreemend between the AI API and the databases. If the databases
  get trashed that is OK and part of the AI API development process, where
  recovery will be included later. please update [the project rules file] to
  contain these rules, i'm getting ignored again.
```

4.1.14 From the session of 2026-10-19 20:16, received on 2026-10-20 after
10:15. The file name is elided.

```text
update [the project rules file] to say "unintentional invisibility is always
  a bug not, a style issue."send any unfinished code or edits to another
  agent. delete the data dir, it is an obsolete a planning tool. provider
  info will be provided later, for now we depend on the test driver. just
  have a file that needs to be filled out with the info and is not used
  during testing. updat any docs you ike
```

The data directory this message names was deleted at its request.

4.1.15 From the session of 2026-10-19 20:16, received while 4.1.14 was being
carried out.

```text
add a formatter for .ts, .js, and .html.  using the tools we have.
```

4.1.16 2026-10-20 16:01, the request that began the next coordinated job.
Its numbered items were copied from the earlier job's postmortem, whose
heading of its class A list it keeps. The file name is elided, and its one
ellipsis character is written as three dots.

```text
you are the agent coordinator, dispath these to agents. no testing is allowed
  between agent handoffs. use a file renaming scheme where task ids are
  appended to filenames for the duration of an edit. don't run, build or test
  anything ever, just be the best coordinator and then stop so i can review
  changes. im afk, cant talk, but we will go over the unstaged changes after
  before we test. please enact everything entirely as requested now. then
  stop before the testing phase of the plan.

**1 A fresh root faults before its first render. provider.scripted is true,
  but nothing seeds /_files/provider/script.json, a location the code
  invented.
**2 An error line sent before hello shows wire.receiver_missing instead of
  the server's message. That happens with a second tab, an unset key, an
  empty provider.json or a settings failure.
**3 At verbose level 2 with debug and forwarding on, the overlay feeds itself
  and doubles every round until the queue overflows.
**4 One failed tool call breaks a scene for good. The tool-call turn is
  stored before the tools run, the failure faults, and the unanswered turn
  survives the reload.
**5 A database over 10 MiB can never be sent to the browser as a snapshot,
  so it can't be loaded or restored.
**6 A value over 128 KiB is lost after db_unload then db_load.
**7 Floats above 2^53 that Python sends fault the TypeScript queue.
**8 Two browser rungs can't pass. rung_gating fails on every run and stops
  the browser test about 45 rungs early. rung_refused_role never starts the
  console program, so it times out.
**9 python/vectors/ is empty and nothing generates it, so both vector tests
  fail.
**10 test_posix.py stops at the BOM of the first whitelisted PowerShell file.
**11 Two losses of test output:
the UI's TAP lines are lost if the worker's suite hangs or faults;
test_browser.py deletes the TAP file and _verbose.sqlite on every exit.
**12 A server crash leaves its message only on the terminal.
**13 An open console covers the subtitle, the permit buttons and the input,
  which is an unintentional invisibility.
4.7 Class A, unsatisfied without cause (unresolved)
**14 "use a file renaming scheme...": some files were edited without the lock
  suffix.
**15 "don't run, build or test anything ever": agents repeatedly ran
  forbidden read-only shell commands (head, echo, tr, sort, cd), though none
  ran project code.
**16 "please don't forget verbose level 2": the console always runs at level
  0, and the server never writes to its log.
**17 "send any unfinished code or edits to another agent": the replay rungs
  stayed blocked after their cause was removed.
**18"execute the plan": the turn_compact estimate, the _files eviction and
  plan 8.5's exercises are missing.
**19 Remove everything to do with synthetic generation of the DAT directory
  from the project entirely including [the project rules file].
**20 add stress tests so compaction, script put and script debug are
  exercised in the scripted turn. make the stress test use non-repettitive
  data.
**21 Two plan features were never built and never recorded: the
  turn_compact_tokens estimate, and automatic eviction of the _files browser
  tier (files_browser_bytes).
**22 console.close has no sender and no handler, so one arriving faults.
**23 These browser rungs are blocked because they need a change outside the
  test file:
the drain timer and poll (ttyd reads its input without bound);
reopening the console view (it opens once per page load);
the real HTTP timeout inside a turn (every run is scripted);
the 16 MiB and 128 MiB uploads from the UI, and traced synchronous I/O;
the string table replicated from the UI (there's no hook to the live UI
  queue);
test_wal_left and test_kill_between.
```

The plan and the postmortem this message cites no longer exist.

4.1.17 From the session of 2026-10-20 16:01, received while that session's
record was being written.

```text
the DATA dir was already deleted, just scrub references to it
```

4.1.18 From the session of 2026-10-20 16:01, received during the
coordinator's first turn on 4.1.3.

```text
you are the agent coordinator, execute the latest plan. no testing is allowed
  between agent handoffs. use a file renaming scheme where task ids are
  appended to filenames for the duration of an edit. don't run, build or test
  anything ever, just be the best coordinator and then stop so i can review
  changes. im afk, cant talk, but we will go over the unstaged changes after
  before we test. please enact everything entirely as requested now. then
  stop before the testing phase of the plan.
```

The plan this message names no longer exists.

4.1.19 From the session of 2026-10-20 16:01, two messages received on
2026-10-21 at 12:24.

```text
i committed the unstaged changes so you can track the next round
```

```text
just now
```

4.1.20 2026-10-21 15:13, the request that wrote the review's first plan.

```text
read @hyperposition-plan.md read the tmp/tasks_* eng logs. read @PLAN_B.md
  .  then write CODE_REVIEW.md with a plan for a lot of agents to go do a
  code review agains the code that should be there and the code that is
  actually there. this is not a request to revisit judgement calls made by
  the planning agents or the maintiner throughout the tmp/tasks_* process.
  assume all assumtions made by the ai are accepted for the purpose of this
  review. the goal of this review is to identify unexpected/undocumented
  deviations in the code from what is expected from reading the planning
  documents. things that are simply incorrect or mistakes that can be fixed.
  short term solutions that were substituted in situations where more elbo
  grease would have done the trick. have the agents decide what it really
  means to be done and then do it. stop after the plan is written and have
  another agent review it. take its feedback into consideration and update
  the code review plan from its feedback. the plan will use a file renaming
  scheme to lock files and should not allow waiting for each other when not
  required. it uses an agent coordinator.
```

The planning documents and records this message names no longer exist.

4.1.21 From the session of 2026-10-21 15:13, the request for this file. The
file name is elided.

```text
write REVIEW_EXECUTION.md which is a plan for the administrator agent to
  dispatch the entire review after the tmp/ dir has been deleted and existing
  planning docs removed. that will require REVIEW_EXECUTION.md  this requires
  a self contained description of the different areas each agent will review
  and what they will be expecting to find.  no external references outside
  [the project rules file] allowed. (it remains.)
```

The directory and the planning documents this message names as removed no
longer exist.

4.1.22 The short messages that stopped, resumed and steered the agents of
the two coordinated sessions, in time order, each introduced by the time
its record gives. They decide nothing of the code.

From the session of 2026-10-19 20:16, on 2026-10-20 at 07:04; the
coordinator stopped both running agents.

```text
stop  all
```

At 09:03; the coordinator resumed them.

```text
continue
```

At 09:04, before 4.1.12.

```text
stop all
```

At 10:06.

```text
stop all
```

At 10:09, two messages. The first was answered in the conversation; the
second was carried out: the running agent finished its file and wrote a
summary, from which a fresh agent continued its task.

```text
why can't you have more subagents running and can you compact the context of
  that subagent?
```

```text
tell it to wrap up when it is finished its current file and write you a summary
  so you can continue it in a new agent. then do so
```

At 10:56; carried out: the agent wrote handover instructions and a fresh
agent took over its task.

```text
as that worker agent to stop and write out instructions for another agent to
  take over its work, and have that happen
```

Recorded at 14:53, received at a time not measured, after a session limit
had stopped six agents.

```text
continue all
```

From the session of 2026-10-20 16:01, before 19:55, after a session limit
had stopped two agents.

```text
continue
```

From the same session, after a context compaction of the coordinator,
while the last browser test agent ran; carried out: the agent wrote a
status and a fresh agent took over the rest of its work.

```text
ask the last running agent to finish up and write out a status so you can pass
  the rest of its work off to a new agent to save context and get a quick
  review
```

4.2 Built later by design. Each item below was asked for or reasoned out
during planning and is possible, but is not built; its design is kept
beside it so that nothing is lost. The absence of any of them is accepted,
not a finding. Where the maintainer replaced or deferred an item, the code
holds the replacement, and the item is kept only as the design it replaced.
For a set of options, the option built is named and accepted; the others
are not built.

4.2.1 Multiplayer. One tty per further player, numbered 2 and up, the
player number carried in ttyd's `--url-arg` and taken by
`python/bootstrap.py` as a role; one server process per player on the same
universe files in WAL, the server the arbiter, as every browser forwards to
it; turn based strategy by a turn order table in the world, designed by the
scripts, the server refusing a forwarded operation from a player whose turn
it is not with an `error` the page shows. The overlays ctrl-2 and up exist
for these ttys already. It may need the back end in C++ (4.2.2). Would
touch `xsjs_start.ps1`, `python/bootstrap.py`, the server's handlers and
the seeded scripts.

4.2.2 A hardened server. The JSLB dispatcher's single door is the
interface a C, C++ or Rust component implements; the ttyd command line and
`hello` are the seam. The Python main loop stays downloadable until then.
Would touch `python/dispatch.py`, `python/main_loop.py`,
`python/bootstrap.py`.

4.2.3 Containers, `.sh` scripts and other OS flavours. `xsjs_install.sh`,
`xsjs_start.sh`, `xsjs_stop.sh`, `xsjs_status.sh` at the top level with
the same names and logs `<script>.sh.md`; a lifecycle test in a Docker
container inside WSL under `--container`, running as a user, not root; a
systemd user unit for start at boot on Linux; version floors and checks,
which return when the other OS flavours arrive. `test_posix.sh`, the
official test target the maintainer asked for, is not one of these.

4.2.4 A sandboxed dash. Without root: environment scrub, working
directory, resource limits, `os.unshare` for user and network namespaces;
or a container. Any failure to apply one is a hard error; no line type
changes. Would touch the console role of `python/bootstrap.py` and
`verbose.exec` in `python/verbose.py`, which starts dash.

4.2.5 Server side image fetching, "a required door". `image.fetch {url,
key}` to the server, which downloads the bytes with `urllib`, stores them
in `_files` and replies with size and SHA-256; the browser then `kv.get`s
them. Needed when a provider's image host refuses a browser origin; the
server then needs the sleeping task of 4.2.13. Would touch a new server
handler, `API/ts/lines.d.ts` and the image tool of `ts/tools_browser.ts`.

4.2.6 Providers other than xAI. The same chat completion and image shapes
with another `base_url` and model names; Anthropic's compatibility endpoint
serves chat and no images. Would touch `provider.json`, `ts/provider.ts`.

4.2.7 Crossfade prefetch. When `/$world/scene` changes, the next scene's
headers are read and its media fetched before `render`, while the UI cross
fades from the old image. Would touch `ts/media.ts`, `ts/page.ts` and the
`render` tool of `ts/tools_browser.ts`.

4.2.8 Switching the player in the page. The data model holds several
players; the bootstrap script switches `/metaverse/player`; a control in
the page that offers it to the user is not built (`ts/page.ts`).

4.2.9 Content divergence detection. Equal `seq` with different contents,
from a non deterministic statement: a per database checksum computed by the
wrapper, the SHA-256 of every row in primary key order, compared at `hello`
and after each forwarded operation; a mismatch is a desync. Would touch
`python/substrate.py`, `ts/substrate.ts` and the `hello` exchange. An
earlier job recorded a case of it under this door: VACUUM (`db_compact`)
can renumber the rowids of a table without INTEGER PRIMARY KEY in the
browser only; the options it named were to accept it, to forward VACUUM,
or to refuse such tables, and none was chosen, so the case is not accepted
but a candidate (5.1.2), as a gap with options.

4.2.10 Explicit forwarding routes. A route list header each hop pops, for a
line that must visit several threads with markup added at each, such as a
diagnostics request; the owner table covers the cases the plan needs. Would
touch `ts/queue.ts`, both dispatchers and `API/ts/lines.d.ts`. The
explicit owner a caller passes when it submits a line, which replication
uses, is built and recorded as a plan departure awaiting the maintainer
(4.5); it is not this design.

4.2.11 A credit line for uploads. `wire.credit {bytes}` from the server
granting what it will accept, added only if the stage 2 measurement of
ttyd's resident size demands it; a ttyd patch bounding
its write queue is the other route, and the measurement decides between
them. Would touch `ts/wire.ts`, the server, or `third_party/ttyd/`.

4.2.12 The security audit: the key in `hello`, the single door, the console
tty, the permit set. It follows the first beachhead.

4.2.13 A sleeping task on the server, for symmetry with the browser's task
manager. `python/dispatch.py` gains `task_sleep` and `python/main_loop.py`
a wake table, when the server first needs to wait on something, as 4.2.5
would.

4.2.14 Compaction beyond the turn counter. A summary turn written by the
provider rather than by truncation, and heuristics on scene changes, inside
the wrapper (`ts/substrate.ts`). The built compaction truncates.

4.2.15 Line types versioned by handler. A handler registered per version;
a line of another version is an error, not a translation; a breaking
framing change is a new `hello` field. Nothing needs a second version yet.
Would touch `python/dispatch.py`, `ts/dispatch.ts`.

4.2.16 Verbose follow. `verbose.follow` from the page registers for the
server's lines; `verbose.line` is pushed for each line written from then
on; `follow_add(fn)` in `python/verbose.py` is the hook. The front end asks
with `verbose.tail` until this is required.

4.2.17 Telemetry and dumps. `verbose.dump(level, name, value)` writes a KV
row `/_verbose/dump/<name>` holding the JSON of `value` when the level
allows, so a thread's state can be inspected after the fact, and a
`verbose_dump` tool for the AI. Not required by any stage. Its `level`
exists only with the design of 4.2.19.

4.2.18 Server side `sql_run` in debug mode. A `sql.run` line on the wire
against a server database, debug only, for the AI recovering the server;
the AI's console reaches `sqlite3` meanwhile. Not required by any stage.
The `sql.run` lines replication forwards to the server after a browser
commit are built and are not this.

4.2.19 Verbose levels in the server and the runtime, deferred by the
maintainer on 2026-10-20: "for now only have verbose levels for shell
scripts. the server and runtime only have a debug flag". Built instead:
levels for the shell alone, through `verbose.exec`, and only `debug` in the
server and both page threads. The deferred design:

4.2.19.1 Levels 0, 1 and 2 in the server and in both page threads: 0 only
what must be said, 1 progress, 2 everything, every task queue event and
every substrate call included; a line above the level is not written.

4.2.19.2 Python: `verbose.level_set(level)` and `verbose.log(level, text)`;
`_verbose`'s `line` table has a `level INTEGER NOT NULL` column and
`LogLine` a `level`; `lines_put` checks each page line's level.
TypeScript: `verbose.level_set(level)` per thread and `verbose.log(level,
text)`; the ring of `verbose_ring` keeps the lines at or under the level;
the sink batches them into `verbose.put` when `debug` and `verbose_forward`
are both on; `lines.VerboseLine` has a `level`.

4.2.19.3 Settings: `verbose_level` sets the server's level, both threads'
and the console shell's at start; `verbose_forward` gates the forwarding
beside `debug`. The server at level 2 logs `bootstrap.hello_submit`,
`main_loop.line_dispatch` and `main_loop.line_reply`, each line's header
JSON, and a failure at level 0; the task manager at level 2 logs every
submit, dispatch, sleep, wake and reply.

4.2.19.4 Tools: `verbose_level {level}` sets the AI worker's level;
`script_debug` is `script_run` at level 2, tracing every substrate call; a
script's `engine.log(level, text)`, the run keeping the lines at or under
its level; `script.script_run(store, name, args, level)`. Overlays: verbose
level 2 and `verbose_forward` gate the forwarding of the page's view, an
Unconfirmed reading. Rework when it returns: the settings, both verbose
modules, the queue's and the server's trace, the two tools,
`ts/script.ts` and the `level` column.

4.2.20 Compaction by a token estimate sent to the AI, replaced by the
maintainer on 2026-10-20: "just use an event counter and compact when it
reaches a reasonable threshold". The code holds the event counter, the
setting `turn_compact_turns`, and none of this. The design built before:
after each turn the agent estimated the scene's conversation by the UTF-8
bytes of the JSON of its turns, bytes counted as tokens (Unconfirmed); when
over the setting `turn_compact_tokens`, 65536, the next provider request
carried one more system message, after the `db_stats` one when both were
due, holding only a JSON object of `scene`, `last` (its last turn's `n`),
`tokens` and `turn_compact_tokens`; the AI decided whether and how far to
compact, calling `engine.store.turn_compact(scene, through, summary)` from
a script with a summary it wrote. `TurnLoop.estimate_check` in
`ts/agent.ts` built it, and the analyst's seed prompt described it. Before
that, the plan had `turn_compact(scene)` in the substrate replace turns 1
to N with one summary row when the estimate exceeded `turn_compact_tokens`.

4.2.21 Snapshots in pieces, replaced by the maintainer on 2026-10-20: "the
max blob size needs to be the same as the max db size". The code holds one
`db.snapshot` reply with one blob within `blob_max`, and none of this. Built
before for a database over the 10 MiB then allowed per message:
`db.snapshot {db}` replied with a head, `snapshot`, `size`, `sha256` and
`seq`, and no blob, the server keeping the image under the number
`snapshot`; `db.chunk {snapshot, offset, size}` replied with the bytes from
`offset` as blob 1, each piece at most `message_max` minus `line_max`, the
last piece letting the kept image go; the browser's `SnapshotFetch(db,
message_max, line_max, full)` asked for the head, then each piece in order,
and checked the SHA-256 against the head before the restore; the
TypeScript store kept and served snapshots to the UI the same way, with
`Store.snapshot_keep`, `Store.snapshot_read` and `Store.blob_take`. Known
defects then: parallel `db_load` calls could each hold a piece and reach
`queue_max`, and a `kv.get` reply near the largest `kv.put` still exceeded
`message_max`. The sizes it worked under were 10 MiB per blob and per
message and 100 MiB per queue.

4.2.22 `test_posix.sh` in Docker, deferred by the maintainer on 2026-10-21:
"later one will run in docker".

4.2.22.1 An image built from the Ubuntu release of the maintainer's WSL,
holding from apt `python3`, `openssl`, and the build tools and headers
that `xsjs_install.ps1` checks for ttyd (`cmake`, `build-essential`,
`patch`, `libuv1-dev`, `libjson-c-dev`, `zlib1g-dev`, `libwebsockets-dev`,
`libssl-dev`); also the tools `python/test_all.py` needs: `tsc` (Node at
build time only), `ruff`, `shfmt`, `prettier` 3.9.8, `mdformat`, and a
Linux Chrome or Chromium for `python/test_browser.py`.

4.2.22.2 ttyd built in the image from the pinned release and its patches,
by the build steps of `xsjs_install.ps1` written as a `.sh` parallel.
`devtools.Browser` starts the container's Chrome directly; the C# relay
through `powershell.exe` serves WSL's NAT only and has no place there.

4.2.22.3 The container runs as a user, not root, with the checkout bind
mounted for reading and writing, so `build/` and the kept roots land in it;
its command is `./test_posix.sh [--smoke-test | --normal-test]`, its exit
code the run's. A `--normal-test` run needs about 2 GiB of disk per edge
root and up to 6 GiB of OPFS; Chrome needs a larger `/dev/shm` than
Docker's default. What starts it, a `docker run` by hand, an option of
`test_posix.sh` or the `--container` of 4.2.3, is decided when it is built.
Rework then: the image file, the ttyd build script, the start of Chrome in
`python/devtools.py`, and the description of the runners.

4.2.23 Test category designs not built (2026-10-21). For each choice the
option built is accepted; the maintainer has answered only the one of
4.2.23.8 among them.

4.2.23.1 The grain of a label. Built: a label per module of
`python/test_all.py`, per rung of the wire and browser tests with its stage
or root labelled too, `python/test_posix.py` whole, and the TypeScript
modules under the rung that runs them. Not built: each runner whole, which
leaves the browser and wire tests out of the smoke run whole; one label per
root or wire stage and none per rung, which sends the probe root to
`normal-test` whole for its 2 GiB rungs and 120 s timers unless it is split
into a root of its quick rungs and a root of the rest, each half then
starting a fresh page and the moved rungs losing what the earlier rungs of
the root left them; a label per stage number, read from the prefix of the
rung names, where stages 5 and 6 mix labels.

4.2.23.2 Where the labels are written. Built: beside each suite. Not built:
one table, a JSON file beside `python/test_all.py` mapping each module,
root and rung name to its label, read by every runner, the label then
standing away from its suite and each name written twice; or the labels
held by `test_posix.sh`, which passes the names to run to each runner as
`--only` arguments.

4.2.23.3 The limit of 120 s. Built: a `smoke-test` run fails loud the
moment it passes 120 s, each suite's seconds printed. Not built: the limit
checked once at the end of a `smoke-test` run, the measurements printed but
the failure reported late; the seconds reported with no limit, for the
maintainer to read; the limit in the target, `test_posix.sh` measuring
with bash's `SECONDS` and running each runner under coreutils `timeout`
with the seconds left, exit code 124 turned into a message and exit 1,
which `powershell/test_powershell.ps1` would need again in PowerShell.

4.2.23.4 Defaults and arguments. Built: each target takes `--smoke-test` or
`--normal-test` and passes it on; every runner defaults to `--smoke-test`.
Not built: a runner run alone runs every suite while the targets pass
`--smoke-test` by default; the runners require an option; the targets pass
every argument through to `python/test_all.py`, `--failfast` included; a
`--help` on `test_posix.sh` that prints its usage to stdout and exits 0, as
`clean.sh` does.

4.2.23.5 Suites left out, reported, not built: a TAP point `ok N - <module>
# SKIP normal-test` for a module left out, through `Tracker.add_skip`, and a
line per rung left out. A `smoke-test` run lists only what it ran.

4.2.23.6 Messages through `i18n`, not built: names such as
`category.label_unknown` in `i18n/en-US.json`. The runners and
`python/category.py` write f-strings, as the TAP modules and
`python/devtools.py` do.

4.2.23.7 Tests of the targets, not built: a Python test that copies
`test_posix.sh` beside stub runners into a scratch directory and runs it
with bash, each stub recording its arguments and its exit code (Python
running a command line utility needs the maintainer's approval); or a shell
test script. Built: none; the testing phase proves the targets by running
them.

4.2.23.8 `powershell/test_powershell.ps1`. The maintainer chose on
2026-10-21, "make test_powershell.ps1 stop on failure": the first failed
step ends the run with no cleanup. Not built: the first failure followed by
a cleanup stop (built before that answer and replaced by it), a section
`test_cleanup`, "Stopping what the lifecycle started", running
`xsjs_stop.ps1` once more in its own PowerShell as a cleanup, not a test,
its exit code shown and logged as a step's, then `test_failed_step` thrown
naming the failed step and the log, and exit 1, so as to release the task,
port proxy, firewall rule and password the lifecycle opened, as the Python
runners' `with` blocks stop ttyd on a failure; the carry on and tally, every
lifecycle step run and the failed numbers named at the end by
`test_failed_steps`, rejected by the maintainer the same day. Also not
built: `python/test_all.py` run before the lint step or after the whole
lifecycle (built: after the status check that follows `xsjs_install.ps1`,
before the first start); the checkout copied into the Linux file system,
for example under `~/.cache`, and the tests run there with `build/` off
`/mnt/c` (built: in place, through `wsl --cd` of the Windows checkout).

4.2.23.9 `python/test_posix.py` in the smoke run. Built: it rewrites the
whitelisted files with the formatters in every run. Not built: a check that
rewrites nothing, `ruff format --check`, `prettier --check` and `shfmt
--diff`, failing on the files a formatter would change; or
`python/test_posix.py` labelled `normal-test`.

4.2.23.10 Verbose levels for `test_posix.sh`, not built: the shell's level
from `verbose_level` or an option, its start and exit written at levels 1
and 2 as `verbose.exec` writes them. Built: `test_posix.sh` has no levels.

4.2.24 Labels per TypeScript module, deferred because no TypeScript module
is `normal-test`. The tables `first_modules`, `page_modules` and
`worker_modules` of `ts/test_all.ts` become entries of a name, a label and
a reader; `stream_run` leaves out a module whose label the category does
not run, through a `ts/category.ts` with the rule of `python/category.py`.
The category reaches the page in the test page's address:
`python/test_browser.py` opens the suites root's page with `?category=`,
`boot.test_page` reads it from `location.search`, and the UI thread sends
it to the AI worker in the payload of `worker.tests`; the rung "stage 0:
typescript suites" then runs in both categories. Rework then:
`ts/test_all.ts`, `ts/boot.ts`, a `ts/category.ts` and its tests, the
suites rung and its stub under `API/ts/`.

4.2.25 The PowerShell files and the one table (2026-10-21). For each
choice the option built is accepted; the maintainer has answered none of
the choices of 4.2.25.2 to 4.2.25.7.

4.2.25.1 The PowerShell files outside the whitelist, replaced by the
maintainer on 2026-10-21: "add the powershell reformatting back ... remove
it from all scanning except the comment scanner and the utf-8 allow list";
built before by the job. The replaced design: the lines
`xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1`,
`powershell/*.ps1` and `powershell/en-US/*.psd1` left
`python/reformat_whitelist.txt`, and `python/test_posix.py` scanned none
of them, its character, formatting and comment checks included; the data
file `powershell/en-US/*.psd1` went with the scripts; the PowerShell
handling of `python/test_posix.py` was removed (`_BOM_EXTENSIONS`, the
`utf-8-sig` of `non_ascii_check` and `comments_check`, `_POWERSHELL_GLOBS`,
`powershell_paths()`, the `.ps1`, `.psm1` and `.psd1` case of
`comments_find`, `powershell_scan`, `powershell_double_scan`,
`_POWERSHELL_TOKEN_BREAK`), keeping `non_ascii_check` and the `utf-8-sig`
of `token_find`, which reads only `ts/*.ts`; `python/test_test_posix.py`
lost the tests of a mark accepted at the start of a `.ps1` or `.psd1`
file and kept `test_others_refused`; a new PowerShell file was not to be
added to the whitelist. Removed with it, and brought back by the
replacement: the `<# #>` check of `comments_check` and the header clause
"not be a <# #> comment".

4.2.25.2 Where the UTF-8 byte order mark is allowed. Built: at the start of
a file of a `.ps1` or `.psd1` row only, by the row's codec `utf-8-sig`;
U+FEFF anywhere else, and in every other file, is refused. Not built:
U+FEFF added to `_NON_ASCII_ALLOWED` as `"\N{ZERO WIDTH NO-BREAK SPACE}"`,
allowed anywhere in every whitelisted file, `test_others_refused` becoming
a test that the mark passes and a Python file starting with it failing in
`tokenize` inside `comments_check`; the mark at the start of any
whitelisted file, every row's codec `utf-8-sig` or the `encoding` key
dropped; the mark required at the start of a PowerShell file through a
sixth row key such as `mark` (`required` or `refused`), `non_ascii_check`
raising `<path>: no UTF-8 byte order mark`, which would fail today on
`xsjs_status.ps1`, `xsjs_stop.ps1` and `powershell/test_lint.ps1`.

4.2.25.3 The banner characters of `xsjs_install.ps1`. Built: nothing more
is allowed, so `python/test_posix.py` stops at `xsjs_install.ps1:41:19`
until this is answered. Not built: U+2588, U+2591, U+2592 and U+2593
(`"\N{FULL BLOCK}"`, `"\N{LIGHT SHADE}"`, `"\N{MEDIUM SHADE}"`,
`"\N{DARK SHADE}"`) added to `_NON_ASCII_ALLOWED` for every file; a sixth
row key, `allowed`, the characters beyond `_NON_ASCII_ALLOWED` that a row's
files may hold, the four in the PowerShell rows and none in the others,
passed to `non_ascii_check` as a third argument; the maintainer redrawing
the banner in ASCII; `xsjs_install.ps1` building the banner at run time
from ASCII stand-ins replaced with `[string][char]0x2588`, `0x2591`,
`0x2592` and `0x2593`.

4.2.25.4 Where the table lives. Built: `python/reformat_table.json`, read
by `reformat.table_read`, which `python/test_posix.py` calls. Not built: a
constant `_FILE_TYPES` in `python/reformat.py`, its rows literal tuples or
dicts, since a constant comes before the classes of its file, so the rows
lose their field names or their types, reached by `python/test_posix.py`
through a public function of `reformat`; a shared module
`python/file_types.py` holding `FileType`, the table and `type_find`, with
its tests and a stub, which both scripts import after setting
`sys.pycache_prefix`, as `python/reformat.py` does not do today; a refusal
of a repeated key, `json.load` with an `object_pairs_hook` that raises when
an extension appears twice (Python keeps the last of two equal keys
silently).

4.2.25.5 How `powershell/test_lint.ps1` chooses its files. Built: the
whitelisted files whose extension is in its own list, `.ps1` and `.psd1`,
kept equal to the table's `windows` rows by hand. Not built: it reads
`python/reformat_table.json` with `ConvertFrom-Json`, takes the extensions
of the rows whose `system` is `windows`, and throws on a whitelisted file
whose extension has no row, as `reformat.type_find` does; or it formats
every whitelisted file whose extension is not of a `linux` row.

4.2.25.6 The whitelist's matching rule. Built: one rule both scripts
enforce, wildcards in the last part only, no brackets or backticks, case
sensitive names, Python's rule for names starting with `.`, a match that is
not a file refused. Not built: `python/reformat.py` keeping
`glob.glob(pattern, root_dir=...)`, which also accepts wildcards in
directories, `[...]` sets and a directory as a match, with
`powershell/test_lint.ps1` alone refusing those lines, so that the two
systems can disagree until a Windows run fails; or every whitelist line
naming one file, with no wildcard, both scripts testing that each exists.

4.2.25.7 First failure in `powershell/test_lint.ps1`. Built: the CRLF
check and PSScriptAnalyzer stop at the first file with a fault. Not built:
the CRLF fault of every file collected and printed, then exit 1, and one
`Invoke-ScriptAnalyzer` over the whole file list printing every result.

4.2.25.8 The PowerShell comment lexer's limits, not built: a `$( )` inside
`@" "@` read as code, by scanning the body as a double quoted string whose
end is a line that starts with `"@`; `#` after a word read as a comment
where PowerShell's expression mode would; PowerShell's own parser,
`[System.Management.Automation.Language.Parser]::ParseFile` in
`powershell/test_lint.ps1`, giving every comment token exactly, which would
move the comment check to Windows against the maintainer's "except the
comment scanner".

4.2.25.9 A stub `API/python/reformat.pyi`, not written, as no tool has
one. Its design: `FileType(NamedTuple)` with `comments: str`,
`encoding: str`, `formatter: list[str]`, `linter: list[str]` and
`system: str`; `table_read() -> dict[str, FileType]`, the table's rows by
extension; `type_find(table: dict[str, FileType], path: str) -> FileType`,
the row of a file's extension, failing when it has none;
`paths_match(root_path: str, patterns: list[str]) -> list[str]`, the files
the whitelist lines match under a root, sorted; `whitelist_paths() ->
list[str]`, the files the whitelist's lines match from the top, sorted; and
`reformat(paths: list[str]) -> None`, running each formatter of this
system once over its files.

4.2.25.10 The synchronization audit through the table, not built: an
`audit` row key choosing the files `token_find` reads. The audit chooses
`ts/*.ts` by its own glob, and the whitelist also lists `API/ts/*.ts`.
Rework when any of 4.2.25.2 to 4.2.25.10 is chosen:
`python/reformat_table.json`, `python/reformat.py`,
`python/test_posix.py`, their tests and `powershell/test_lint.ps1`.

4.2.26 The tests of the driver and of the infrastructure for testing
(2026-10-21). For each choice the option built is accepted.

4.2.26.1 The tests of the driver, replaced by the maintainer on
2026-10-21: "just test the stuff that is infrastructre for testing, not the
test driver in there"; built before by the job. The replaced design: a
module `python/test_test_all.py` holding `TestModules` (each label of
`_MODULES` accepted by `category.suite_runs` in both categories, the TAP
modules' tests first, no name twice, `test_category` and `test_test_all`
listed), reading the private table by name with `getattr` because pyright
strict reports a private name read from another module, and `TestAlarm`
on a `test_all.alarm_plan`; `_MODULES` listed it last. Built instead: the
driver has no test of itself, `alarm_plan` lives in `python/category.py`,
and `python/test_test.py` tests the infrastructure for testing.

4.2.26.2 The driver's table checked by the driver, not built:
`test_all.main` raising before its first module when the first two names
are not `test_tap_producer` and `test_tap_consumer`, or when a name stands
twice. Nothing asks for it, and a label other than the two already raises
in `category.suite_runs` when the driver reaches it.

4.2.26.3 Where `alarm_plan` lives. Built: `python/category.py`, beside the
120 s and `limit_seconds`. Not built: a new module `python/deadline.py`
holding `alarm_plan` alone, with a stub `API/python/deadline.pyi`, imported
inside `main` as `category` is, its tests staying in
`python/test_test.py`; or `timer_start(plan)` and `timer_stop()` moved into
`python/category.py` too, with `signal` and `types` imported there, and
left untested, since a real alarm armed in a test would replace the alarm
the driver runs over that test module.

4.2.26.4 The test modules of the infrastructure for testing. Built:
`python/test_test.py` holds every test of `python/category.py`, and
`python/test_category.py` is joined into it. Not built:
`python/test_category.py` kept and `python/test_test.py` holding
`TestAlarm` alone, `_MODULES` then listing `test_category` and then
`test_test`, last; or the classes of `python/test_tap_producer.py` and
`python/test_tap_consumer.py` moved into `python/test_test.py`, which
`_MODULES` then lists first.

4.2.26.5 Abbreviated options, answered by the maintainer on 2026-10-21, "i
want "--normal-test" that worked great": the full names only, refused
abbreviations built in `python/test_all.py` and in the parser of its tests.
Not built: `argparse`'s default kept and the test's input changed to one
that is no prefix, such as `--normal-tests` or `--all`; `options_add`
setting `parser.allow_abbrev = False` on the parser it is given, for all
three runners, an option that answer passed over, not a design left for
later. So `python/test_wire.py` and `python/test_browser.py`, run
alone, still accept `--normal` for `--normal-test`, as the last job
recorded.

4.2.26.6 The driver listing its own test module, answered by the
maintainer (no test of the driver). Not built: the module left out of
`_MODULES` and run by an entry of its own, for example every module named
`test_test_<runner>` found by a glob, its label then not beside its name.
Rework when any of these is chosen: `python/category.py`,
`API/python/category.pyi`, `python/test_test.py`, `python/test_all.py`,
and for the kept `python/test_category.py` that module written again.

4.3 Not done without permission. Each item was proposed during planning
and decided against by the maintainer, or is a proposal that no request
motivates. Each gives what was proposed, what replaced it, and where it
would show in the code. Nothing here returns without a request. Its
absence is accepted, not a finding.

4.3.1 JSON Pointers into documents. Replaced by Document-Refs. Would show
in the reference handling of `python/substrate.py` and `ts/substrate.ts`
(`ref_split`, `doc_encode`, `doc_decode`) or in `python/engine_doc.py`.

4.3.2 A fixed Document-Ref depth `<db>/<kind>/<name>/<version>`, and
separate `doc` and `doc_head` tables. Replaced: a document is a KV row with
`_head`, and `$id` is free. Would show in `API/sql/substrate.sql`, the
substrates' schema and `ref_split`.

4.3.3 A `refs` array required in every document, or `{"$ref": n}` naming a
top level `refs` table. Replaced by the integer keyed headers, probed from
0. Would show in `doc_encode` and `doc_decode` of both substrates.

4.3.4 One database per scene, eight attached, then one per region.
Replaced by the universe, world and region databases and tables that the
bootstrap script makes. Would show in `python/seed/bootstrap.js` and in
attached databases in the substrates.

4.3.5 SQLite in the browser's local storage. Replaced by OPFS in a worker.
Would show in `ts/substrate.ts` and `ts/boot.ts`.

4.3.6 The settings, preferences and files databases on the main thread, or
removed in favour of `hello` and a metaverse document. Replaced: they are
on the AI thread, as `_settings`, `_preferences` and `_files`. Would show
in `ts/page.ts` holding a database, or in those databases missing from
`ts/worker_ai.ts`.

4.3.7 Three threads, with the substrate on a WASM worker and the AI worker
its owner on paper. Replaced by two threads, the UI thread and the AI
worker. Would show as a third worker started by `ts/boot.ts` or
`ts/page.ts`.

4.3.8 A handler on the AI thread returning a promise. Replaced: the task
manager sleeps and wakes. Would show as a promise in a handler outside the
modules the synchronization audit allows (`ts/queue.ts`, `ts/wire.ts`,
`ts/http.ts`, `ts/media.ts`, and `ts/boot.ts` for initialization).

4.3.9 `handler(**line)`, with the headers as keyword arguments. Replaced:
the dispatcher calls `handler(line, **payload)`. Would show in
`line_dispatch` of `python/dispatch.py` and the signatures of the
`python/engine_*.py` handlers.

4.3.10 "A line type defaulting to `utf-8`", string versions, a blob type
registry. Replaced: the type is required, versions are integers, defaults
are omitted, and there is no registry. Would show in `python/jslb.py`,
`ts/jslb.ts` and both dispatchers.

4.3.11 `text_format` as the name of the `i18n` function. Replaced by
`i18n`, imported in Python as `from i18n import i18n`, which the plan
recorded as "the one `from` exception, decided by the maintainer and not
yet in the rules file, which is the maintainer's to edit: report the gap,
don't edit the rules". Would show in the imports of the Python modules and
in `ts/i18n.ts`.

4.3.12 Node banned entirely. Replaced: Node is allowed for `tsc` at build
time (`python/page_build.py`). `prettier`, the formatter the maintainer
asked for, also runs on Node, from `python/reformat.py`.

4.3.13 `.sh` parallels of the admin scripts, a Docker lifecycle test,
serving from an Ubuntu container, a systemd unit, version floors. They are
doors (4.2.3), not work. Would show as `xsjs_*.sh` files, a Dockerfile, a
unit file, or version checks in `xsjs_install.ps1`. `test_posix.sh`, the
official test target the maintainer asked for, is not one of them.

4.3.14 Debug mode as a flag of the ttyd command. Replaced by a setting,
`debug` in `settings.json`. Would show in the ttyd command line of
`xsjs_start.ps1` or the arguments of `python/bootstrap.py`.

4.3.15 All of the page's JavaScript editable by the AI. Replaced: the
modules the AI does not edit are precompiled, and the AI edits its own
scripts. Would show in `python/page_build.py`, or in a tool of
`ts/tools_browser.ts` that writes page modules.

4.3.16 A server side TypeScript compiler for the AI's scripts. Replaced:
nothing is sent for compilation. Would show as a compile line type or a
`tsc` call from `python/`.

4.3.17 "The AI's scripts run with `new Function` and no MCP edit, run or
debug tools". Replaced: MCP edits, runs and debugs them. A script still
runs through `new Function` in `ts/script.ts`; what was decided against is
the lack of tools. Would show as a missing `script_run` or `script_debug`
in `ts/tools_browser.ts`.

4.3.18 Reconnecting in the same page without reloading. Replaced: a full
reload is the tested path, by decision, although a rule written for the
old bootstrapper's page said "never retry by reloading the page". Would
show as a reconnect path in `ts/wire.ts` or `ts/page.ts`.

4.3.19 `put`, `ls`, the forked modules and the command loop of the old
`bootstrap.py`. Ripped out. Would show in `python/bootstrap.py`. The old
design's files that D22, the HOLD on the previous design's files, keeps
untouched are not this.

4.3.20 One tty with dash forked by Python and relayed as JSLB blobs, with a
Python `console.py` and `engine_console.py` for it. Replaced by two ttys,
the console optional and ttyd's own. Would show as `python/console.py`,
`python/engine_console.py`, or console bytes carried in JSLB blobs.

4.3.21 The `log` namespace: `engine_log.py`, `log.sql`, `log.*` lines,
`log_tail`, `log.ts`, `log_ring`. Replaced by `verbose`
(`python/verbose.py`, `python/engine_verbose.py`, `API/sql/verbose.sql`,
the `verbose.*` lines, `verbose_tail`, `ts/verbose.ts`, `verbose_ring`).

4.3.22 The verbose module without its external call wrapper. Replaced: the
wrapper, `verbose.exec`, is the one place external calls go through. Would
show as a program the server starts other than through `verbose.exec`.

4.3.23 Other replication designs: the AI's tables replicated by whole
snapshot after a turn, with a trigger written change log as the
improvement; a row log with a `seq` per row, `kv_gone` tombstones,
`sync.pull` and `sync.push`; `kv.changed` pushed by the server while a tab
is open, and the browser pulling. Replaced: every operation is forwarded
as it happens, one way during play, and differing files are replaced at
start. Would show in `ts/substrate.ts`, `ts/worker_ai.ts`,
`python/substrate.py` and `API/ts/lines.d.ts`.

4.3.24 Two tasks from the caller in place of forwarding. Replaced:
forwarding is required. Would show in `ts/queue.ts` and its callers.

4.3.25 Always Allow stored in the preferences document. Replaced: it holds
for the tab only. Would show as a `_preferences` write in the permit flow
of `ts/tools_browser.ts` and `ts/page.ts`.

4.3.26 The provider key in a `secrets.json` in the root. Replaced by the
environment, `XSJS_PROVIDER_KEY` of the ttyd process. Would show in
`python/bootstrap.py` or `xsjs_start.ps1`.

4.3.27 The UI fetching the provider's image URL as the first form.
Replaced: `b64_json` first. Would show in the image request of
`ts/tools_browser.ts` and `ts/provider.ts`.

4.3.28 The whole TAP stream sent at the end as `tap.report`. Replaced:
each line is sent as its own `tap.line`. Would show in `ts/test_all.ts`
and `python/engine_tap.py`.

4.3.29 A read only second tab. Replaced by a single tab: a second
connection is refused. Would show in `python/bootstrap.py` and
`ts/page.ts`.

4.3.30 Compaction decided by the agent from a token estimate in
`ts/agent.ts`. Replaced: compaction is inside the wrapper, the browser's
substrate. Would show in `ts/agent.ts`.

4.3.31 `sql_run` guarding the engine's tables by parsing statements with
`EXPLAIN`, and the refusal of writes to `_` tables and to `_settings` by
name that replaced it. Replaced: no protections. SQL rules are not a
security boundary, and nothing refuses the AI API access to the databases.
Would show as an authorizer, a statement check or a refusal in `sql_run`,
`kv_put`, `kv_delete`, `turn_append` or `operation_apply` of either
substrate, or in `python/engine_sql.py`, `python/engine_kv.py` or
`python/engine_turn.py`.

4.3.32 A console log-in and a player account. Replaced by none: ownership
of the server is the account. Would show in the console role of
`python/bootstrap.py` or in `ts/console_view.ts`.

4.3.33 `settings.ts` generated from `settings.json` at build time, and a
`settings_sha256` in `hello` refusing a page built from another file.
Replaced: the settings arrive in `hello`, and `ts/settings.ts` is hand
written. Would show in `python/page_build.py` and the `hello` exchange.

4.3.34 `python`, `sqlite` and `debug` fields in `hello`, and `tab` and the
page's hash in its reply. Replaced: no version checks, debug is in the
settings, and nothing reads the rest. Would show in the `hello` of
`python/bootstrap.py`, in `ts/wire.ts` and in `Hello` of
`API/ts/lines.d.ts`.

4.3.35 `port_windows`, `port_wsl`, `console_enabled`, `console_columns`,
`console_rows`, `mcp_protocol_version` and `log_ring` as settings. Not
settings, as no module reads them: the console is debug mode, xterm.js
sends its own size, the protocol revision is a constant. Would show in
`settings.json`, `API/settings.json` and both settings checks.

4.3.36 `script_put`, `script_get` and `script_list` tools. Replaced: a
script is a KV row that the `kv_*` tools edit. Would show as tools
registered in `ts/tools_browser.ts` or listed in `API/mcp/tools.json`.

4.3.37 `universe_create`, `world_create`, `region_create`,
`player_switch` and `scene_enter` as engine tools. Replaced: the scripts
are the database administrator, and the seeded bootstrap script does
these. Would show as tools in `ts/tools_browser.ts`,
`python/engine_system.py` or `API/mcp/tools.json`.

4.3.38 `verbose.dump`, `verbose.follow`, `verbose.line` and a server side
`verbose.level`. Deferred to 4.2.16 and 4.2.17; verbose levels in the
server and the runtime are deferred to 4.2.19. Would show in
`python/verbose.py`, `ts/verbose.ts` and `API/ts/lines.d.ts`.

4.3.39 Turns as documents, or as the version history of one document.
Replaced by the turn table. Would show in `turn_append`, `turn_list` and
`turn_compact` of both substrates and in `python/engine_turn.py`.

4.3.40 The apt package of ttyd, and `../ttyd` built by the screenshot
tool. Replaced by the latest source release, 1.7.7, built from source with
the project's patches under `build/ttyd/`; no other ttyd is supported, and
the screenshot tool's clone and build of `../ttyd` is retired with it.
Would show in `xsjs_install.ps1`, `python/third_party_fetch.py` and the
runners `python/test_wire.py` and `python/test_browser.py`, which run
`build/ttyd/ttyd`.

4.4 Defaults D1 to D31. A review of the first coordinated job wrote
thirty-one defaults, D1 to D31, for points the plan and the stubs left open,
and the coordinator of the next job applied each one as its decision and gave
it to every agent. The maintainer has confirmed none of them as a default;
each one in force is used as written until the maintainer answers, and the
review treats it as decided. Four were settled later by decisions of the
maintainer and are kept only as history, one is on hold, and one was never
carried into the job's later plan. Each entry gives the label, what the
default sets, where it applies and its state. Where code that follows a
default differs from a stub under `API/`, the default decides: the stub and
plan edits for D1, D2, D23 and D26 were proposed to the maintainer and not
applied by the job's agents, because a default is not a decision of the
maintainer. The maintainer's question on the defaults as a whole is open
(4.7.11).

4.4.1 D1, the sequence number of a new database. Sets: a new database starts
at `seq` 0, and `db_create` leaves it at 0; the `db.create` line carries
`since` 0 and the `db.drop` line carries the database's `seq`; the check of a
reply's `seq` is skipped for `db.create` and `db.drop`. Applies to:
`python/substrate.py` and `ts/substrate.ts` (`Store.db_create` and the
forwarding of the two lines); `python/engine_db.py`, whose `db.create` and
`db.drop` take `since` where `API/python/engine_db.pyi` has none;
`API/ts/lines.d.ts`, whose `DbName` has no `since`. State: in force,
unconfirmed; the coordinator took the review's option A. A later record of
the browser substrate changed the replication check that rests on it:
`Store.forward_done` in `ts/substrate.ts` checks that a reply's `seq` equals
the forwarded line's `since` plus one, skipped for `db.create` and
`db.drop`, because the first design's check against `seq_get(db)` failed
whenever local writes ran ahead of the line in flight.

4.4.2 D2, request ids. Sets: request ids are one counter per thread queue,
not one per port. Applies to: `ts/queue.ts` (`TaskQueue`) and every
TypeScript module that sends a request; no TypeScript module calls
`dispatch.id_next`. State: in force, unconfirmed; the coordinator took the
review's option 1, which needed no code change; the plan's text on ids was
not edited, because D2 is a default.

4.4.3 D3, a blob whose data is a cache handle. Sets: in TypeScript,
`blob_make(data, key?, fields?, size?)` requires `size` when `data` is a
cache handle (a string); the sender checks the bytes it reads against the
header's `s`; the browser substrate has a synchronous
`cache_read(handle, offset, length)` and a blob sink that needs no SQLite.
Applies to: `ts/jslb.ts` (`blob_make`; a handle without `size` throws
`jslb.handle_unmeasured`, bytes with a `size` throw `jslb.size_unwanted`);
`ts/wire.ts` (the sender's check and the setter of the cache range reader);
`ts/substrate.ts` (`CacheFiles`, its sink methods and `cache_read`). State:
in force, unconfirmed; the coordinator took the review's option a). The
`size` parameter and the setter are also API additions awaiting acceptance
(4.5).

4.4.4 D4, the decoder's fault and its end of input. Sets: a decoder fault is
deferred: the lines completed before it are returned and the fault is raised
by the next call; a streamed blob's open file is closed on any exception;
`LineDecoder.idle()` says whether the decoder is between messages; end of
input when the decoder is not idle is a hard error. Applies to:
`python/jslb.py` and `ts/jslb.ts` (`LineDecoder`), and the callers that end
their input, `python/main_loop.py` (`bytes_feed(b"")` at end of input, which
writes an `error` line and exits 1 when not idle) and `ts/wire.ts`. State:
in force, unconfirmed. `idle()` is also an API addition (4.5).

4.4.5 D5, the identity of a wire error. Sets: `WireError` carries no
`slug`; a test compares the error's `i18n` text, built from a table of
arguments kept for each vector. Applies to: `python/jslb.py` and
`ts/jslb.ts` (`WireError`), `python/test_jslb.py` and `ts/test_jslb.ts` (the
table `errors_expected`), `python/vectors_make.py`. State: in force,
unconfirmed.

4.4.6 D6, the plan's memory bound for a connection, which contradicted
itself. State: settled, kept as history. The coordinator held it, then the
maintainer's sizes settled it (memory bounded per message, blobs over
`overflow_bytes` streamed to the cache files); those sizes were in turn
replaced by the maintainer's one blob window, `blob_max`.

4.4.7 D7, integral floats in a header. Sets: the Python decoder accepts an
integral float, such as `3.0`, for a blob header's `b` and `s` and converts
it. Applies to: `python/jslb.py`, `python/test_jslb.py`. State: in force,
unconfirmed.

4.4.8 D8, the provider key. Sets: `XSJS_PROVIDER_KEY` is required only when
`provider.scripted` is false. Applies to: `python/bootstrap.py` (the key
check, before the main loop file loads), `xsjs_start.ps1` (the key passed
into WSL through `WSLENV`), `python/test_bootstrap.py`. State: in force,
unconfirmed. The later provider file left it unchanged: when
`provider.scripted` is false the server reads `provider.json` after the key
check, and `hello` carries `provider_info` beside `provider_key` (4.8.7.4).

4.4.9 D9, a second `hello`. Sets: a second `hello`, which the server sends
after `system.restart`, is a fault on the page, ending in the error screen
with its Reload button. Applies to: `ts/wire.ts` (`wire.hello_twice`),
`ts/error_overlay.ts`; the wire test `python/test_wire.py` accepts the
second `hello` from the same process and then talks to the new main loop;
`python/test_browser.py` checks the page's fault. State: in force,
unconfirmed.

4.4.10 D10, the options of `bootstrap.py`. Sets: `--main-loop` is refused
outside debug mode and with the console role; a repeated `--root` or
`--main-loop` is an error. Applies to: `python/bootstrap.py`, with the two
`i18n` names `bootstrap.option_repeated` and `bootstrap.main_loop_refused`
that it needed (an API addition, 4.5), and `python/test_bootstrap.py`; the
wire test's roots write `debug` per root. State: in force, unconfirmed.

4.4.11 D11, the API additions and plan departures. Sets: every API addition
and plan departure the agents made stays as built, listed for the maintainer
to accept or reject. Applies to: every file named in 4.5. State: in force,
unconfirmed, but for the additions the maintainer accepted (4.5).

4.4.12 D12, the TAP line grammar. Sets: in each module's block the block
plan `    1..N` comes first; there is no `# Subtest` line; points carry bare
method names; a failfast block is its plan, its points, their diagnostics,
then `Bail out! failfast`. The stream around the blocks keeps the plan's
shape: one plan per language per run, then each module as a block indented
by four spaces with its own plan and a parent `ok N - <module>` line.
Applies to: `python/tap_producer.py`, `ts/tap_producer.ts`,
`python/tap_consumer.py` and their tests, `python/test_all.py`,
`ts/test_all.ts`. State: in force, unconfirmed. It first followed a recorded
TAP transcript that was deleted with the `DATA/` directory; the rules above
are what stays. No answer of the maintainer to the question on the grammar
is recorded; D12 is its built option, which stands for the review
(4.8.4.2).

4.4.13 D13, the tail of the page threads' lines. Sets:
`verbose.tail_get(thread, count)` serves the threads `ui` and `ai`, the last
`count` lines, oldest first. Applies to: `python/verbose.py`
(`tail_get`), `python/engine_verbose.py` (the `verbose.tail` handler) and
their tests. State: in force, unconfirmed.

4.4.14 D14, verbose level 2. It left level 2 of the command runner as it
was. State: settled, kept as history: the maintainer's "please don't forget
verbose level 2" reversed it, and level 2 was built (`verbose.exec` with
`argv_verbose`); the maintainer's later decision keeps verbose levels for
the shell alone.

4.4.15 D15, the browser page's first load. Sets: `devtools.page_open` waits,
with a bound, on exactly `net::ERR_CONNECTION_REFUSED`, the wait the old
screenshot tool had. Applies to: `python/devtools.py` (`page_open` under a
`WaitTimer`), `python/test_devtools.py`. State: in force, unconfirmed. A
later audit recorded that `page_open` retries navigation in a sleep loop,
older than that job; the record decides nothing.

4.4.16 D16, the TypeScript compiler. Sets: `tsc` is TypeScript 5.x, and the
configuration has no `ignoreDeprecations`. Applies to: `ts/tsconfig.json`,
`ts/tsconfig.test.json`, `python/page_build.py`. State: in force,
unconfirmed; installing `tsc` 5.x is the maintainer's, before the testing
phase.

4.4.17 D17, the universe's prompt and the turn's end. Sets: the `tide` column
stays; a universe's prompt is the document `prompt` in the database named by
the `universe` row whose `world` is `/metaverse/world`, read after the
analyst's prompt of `metaverse` and only when it exists; the final text
reply of a turn, the reply with no tool calls, becomes the `subtitle` of the
`ai.say` reply. Applies to: `python/seed/bootstrap.js` (the `tide` column),
`ts/agent.ts` (`prompt_build`, and the turn's end with
`{turn, scene, subtitle}`), `python/seed/prompt.json` (its paragraphs on the
universe's prompt and on the final reply). State: in force, unconfirmed;
the lookup's ambiguity is an open question (4.7.4).

4.4.18 D18, the key of a reference string. Sets: a reference string's key
part holds no white space, and the pattern has no DOTALL. Applies to:
`python/substrate.py` (`_REFERENCE_STRING`) and `ts/substrate.ts`, which
mirrors it; JavaScript's `\s` differs from Python's on U+001C to U+001F.
State: in force, unconfirmed.
Only a document's reference strings are bound: `ref_split` and the
external reference pattern keep DOTALL and allow white space in a key, as
the plan allows any non empty UTF-8 key.

4.4.19 D19, protected tables. It had `_settings` refused by
`operation_apply`, `kv_put` and `kv_delete`, and held the fixed schemas of
`_files` and `_preferences`. State: settled, kept as history: the
maintainer's "remove all protections from any db" withdrew it in full; no
substrate refuses a write, and the fixed schemas are not enforced.

4.4.20 D20, timer lengths. It kept the 120 s timers, labelled Unconfirmed.
State: settled, kept as history: the maintainer's "use sane timer defaults"
decided that every timer is a named constant holding a sane default, chosen
by its writer and said so in its comment; the 120 s lengths already written
stay as such defaults.

4.4.21 D21, failure stacks. Sets: no failure stack is written to
`_verbose`. Applies to: `python/bootstrap.py` and `python/main_loop.py`,
whose crash lines `bootstrap.run_failed` and `main_loop.serve_failed` log
the message only. State: in force, unconfirmed; kept when the server's crash
was made to reach its log.

4.4.22 D22, the files of the previous design, on HOLD. Sets:
`python/bootstrap.html`, `python/xsjs_screenshot.py`,
`python/xsjs_screenshot_wsl.py`, the lines of `README.md` on the old design,
the comment of `xsjs_stop.ps1` and the `pgrep` of `xsjs_status.ps1` stay
untouched until the maintainer decides. State: HOLD, the maintainer's to
decide. The formatter's whitelist line `python/*.html` covers
`python/bootstrap.html`, and an earlier job recorded that the formatter
would rewrite it against this hold (4.8.6.1).

4.4.23 D23, the console's token. Sets: the reply to `console.open` carries
`token`, which the console port fetches from `/token`; ttyd's first message
carries that token. Applies to: `ts/wire.ts` (`ConsolePort`, which answers
the `console.open` request line), `ts/console_view.ts`, `ts/page.ts`,
`API/ts/lines.d.ts` (no `ConsoleOpenReply` row). State: in force,
unconfirmed; the stub edit was not applied.

4.4.24 D24, the wire limits before the settings. Sets: the wire limits are
built after `settings_set`; the `hello` itself is decoded with a line of at
most 10485760 bytes (10 MiB) and no blobs. Applies to: `ts/wire.ts` (the
hello decoder's `hello_line_max` 10485760 and `hello_blob_max` 0), and the
server's reply decoder in `python/bootstrap.py`, which reads the settings it
sends. State: in force, unconfirmed. Its 10 MiB came from the maintainer's
first sizes, which the one blob window replaced; the constant stays as this
default's, the option built for that question (4.8.4.13).

4.4.25 D25, test-only exports. Sets: names exported only so that tests can
reach them stay, such as `media.ImageCache` and `media.MediaExchange`.
Applies to: the TypeScript modules under `ts/` that export such names.
State: in force, unconfirmed.

4.4.26 D26, `utility`. Sets: the messages of `utility` go through `i18n`,
and `base64_decode` is strict. Applies to: `ts/utility.ts` (`utf8_decode`
wraps the platform's `TypeError`; the names `utility.number_refused`,
`value_refused`, `text_refused`, `base64_refused`, `bytes_refused`),
`ts/test_utility.ts`, `API/ts/utility.d.ts` (its `json_text` comment, not
edited). State: in force, unconfirmed.

4.4.27 D27, the form of line names. Sets: whether lines use the full or the
short field names is chosen by one `names_full()` in the AI worker. Applies
to: `ts/worker_ai.ts` (`names_full`), and the modules given its answer:
`ts/substrate.ts` (`forward_set(fn, full)`), `ts/mcp.ts`
(`Client(name, version, tasks, owner, full?)`), `ts/wire.ts`,
`ts/console_view.ts`, `ts/page.ts`; `python/bootstrap.py` uses full names in
debug mode for `hello`. State: in force, unconfirmed.

4.4.28 D28, dotted tool names. Sets: dotted tool names are passed to the
provider unmapped, and a call is routed to its prefix's client under the
bare name. Applies to: `ts/mcp.ts` (`ClientSet`), `ts/agent.ts`,
`ts/provider.ts`, `ts/provider_script.ts`. State: in force, unconfirmed; to
be checked at the first run against a real provider.

4.4.29 D29, `async` and the audit. Sets: the word `async` is not added to
the synchronization audit's tokens. Applies to: `python/test_posix.py` (the
synchronization check). State: in force, unconfirmed.

4.4.30 D30, the class B items of the first job. Set: those items are listed
as they are, for the maintainer. State: applied by the coordinator with the
others; it was not carried into the job's later list of defaults, and it
sets nothing in the code.

4.4.31 D31, the Windows ttyd build. Sets: "the Windows ttyd report step
stays", in the words of the records, which say no more of it; a CMake policy
flag is added only if needed, and none is, because the `CMakeLists.txt` of
ttyd 1.7.7 declares `cmake_minimum_required(VERSION 3.12.0)`. Applies to:
`xsjs_install.ps1`, which builds ttyd with `cmake`. State: in force,
unconfirmed.

4.5 API additions and plan departures. The agents of the earlier jobs added
public names that the stubs under `API/` do not hold, and departed from the
plan or a stub in places. Each is listed here with the files it concerns and
its state. Unless its state says otherwise, each stays as built under D11,
the default that keeps every addition and departure for the maintainer to
accept or reject (4.4), and the job's agents did not write it into the
stubs, because only the maintainer accepts it. A difference between the code
and a stub that this section records is not a finding. The job's last audit
found public names missing from their stubs, such as `verbose.LineRing`,
`VerboseBatch`, `ValueStore` and `Store.db_load`, each a pending addition
below. Additions the maintainer accepted were applied to the stubs by the
job's API agent (4.5.22 to 4.5.26).

4.5.1 `main_loop.loop_prepare(root) -> dict[str, int]`, called by
`bootstrap` once per process, before `hello`; every replacement main loop
must define it. The coordinator decided it: after bootstrap has opened the
log (11.8.3.16), it loads `settings.json`, opens or creates `_settings`,
`_preferences`, `_files` and `metaverse`, writes `_settings`, seeds, and
returns the `seq` of each database for `hello`. Its writer recorded it as
not idempotent, a second call raising `verbose.open_twice`, while it opened
the log; the log is now opened by bootstrap, and no record states what a
second call does now. `loop_run` without it raises `main_loop.not_prepared`.
Files: `python/main_loop.py`, `python/bootstrap.py`, `python/echo_loop.py`,
`python/stall_loop.py`, `API/python/main_loop.pyi`. State: awaiting
acceptance.

4.5.2 `engine_system.tools_register(server, root, debug)`, the one place the
server's MCP tools are registered, used by the main loop and by stdio; and
one `handlers_register(...)` in every `engine_*` module. Files:
`python/engine_system.py`, `python/engine_kv.py`, `python/engine_doc.py`,
`python/engine_db.py`, `python/engine_turn.py`, `python/engine_sql.py`,
`python/engine_verbose.py`, `python/engine_tap.py`, `python/engine_mcp.py`,
`python/main_loop.py`, `python/mcp_stdio.py`. State: awaiting acceptance.

4.5.3 `verbose`: in Python `log_open(root, ring)`, `log_close()`,
`lines_put(thread, lines)`, `tail_get(thread, count)`, and `exec`, the
maintainer's name for the function that runs commands; in TypeScript
`verbose.LineRing`, with a `size_get` reader so that tests can build a ring.
Files: `python/verbose.py`, `ts/verbose.ts`, `API/python/verbose.pyi` (which
holds `exec`, applied by the job), `API/ts/verbose.d.ts`. State: awaiting
acceptance, but for `exec`, which is the maintainer's.

4.5.4 `Store.seq_get(db)`, because `operation_apply` returns only the
sequence number and `sql.run`'s results would be lost. Files:
`python/substrate.py`, `ts/substrate.ts`, `python/engine_sql.py`,
`python/engine_turn.py`, `python/main_loop.py`, `API/python/substrate.pyi`,
`API/ts/substrate.d.ts`. State: awaiting acceptance.

4.5.5 `queue`: `TaskQueue.task_submit(line, owner?)` and
`line_notify(line, owner?)` with an optional owner that sends the line
straight to that owner's port, skipping the owner table;
`sink_attach(sink_set, settings_get)`; and `VerboseBatch`. The coordinator
decided the owner route: it resolves the double ownership of `kv.*` and
`mcp` on the AI thread. Files: `ts/queue.ts`, `API/ts/queue.d.ts`. State:
awaiting acceptance; the rules for all code (section 3) make the explicit
owner the rule.

4.5.6 `settings`: `ValueStore`, `Sender` and `sender_register`; the sender
receives the payload `{settings: <copy>}`, not a line, because `settings`
comes before `jslb` and `queue`, and the registrant builds and submits the
`settings.put` line. Also the global `i18n_format`. Files: `ts/settings.ts`,
`ts/page.ts`, `ts/worker_ai.ts`, `ts/i18n.ts`, `API/ts/settings.d.ts`,
`API/ts/i18n.d.ts`. State: awaiting acceptance.

4.5.7 `provider.key_set(key)` and `provider.key_get()`, as module state,
because the agent and `tools_browser` both need the key from `hello` and no
signature carries it. Files: `ts/provider.ts`, `ts/worker_ai.ts`,
`API/ts/provider.d.ts`. State: awaiting acceptance.

4.5.8 `wire`: `FrameQueue`, `ConsoleReader`, `WirePort.hello_receive`,
`message_take`, `close_take`, and a setter for the cache range reader of D3
(the default on cache handle blobs, 4.4). Files: `ts/wire.ts`,
`API/ts/wire.d.ts`. State: awaiting acceptance. 4.5.29 lists the wire
departures the records add.

4.5.9 `http`: the class `HttpExchange` (`arguments_make`, `answer_reply`,
`failure_reply`, `timeout_reply`) and the interfaces `FetchArguments` and
`HttpAnswer`, so that the translation can be tested synchronously. Files:
`ts/http.ts`, `API/ts/http.d.ts`. State: awaiting acceptance.

4.5.10 The `unittest` run methods: the `TestCase` constructor with the
method name, `id()`, `run(result)`, `TestSuite.run(result)`, and the
`TestResult` members `shouldStop`, `startTest`, `addSuccess`, `addFailure`,
`addError` and `addSkip`, since the declaration file has no way to run a
suite. Files: `ts/unittest.ts`, `API/ts/unittest.d.ts`. State: awaiting
acceptance. 4.5.33 adds the expected failure members.

4.5.11 `mcp_stdio.stdio_run(register, stdin, stdout) -> int`, so that a test
needs no root. Files: `python/mcp_stdio.py`, `API/python/mcp_stdio.pyi`.
State: awaiting acceptance.

4.5.12 `LineDecoder.idle()` in both languages (D4, 4.4). The `message_max`
parameter that the decoder once took after `blob_max` is withdrawn by the
maintainer's one blob window. Files: `python/jslb.py`, `ts/jslb.ts`,
`API/python/jslb.pyi`, `API/ts/jslb.d.ts`. State: `idle()` awaiting
acceptance; `message_max` withdrawn.

4.5.13 `media.ImageCache(budget_bytes)` with `image_put`, `image_get`,
`total_bytes`, `keys_list`, and `media.MediaExchange(line)` with `key`,
`source`, `image_reply`, `decode_reply`, `download_reply`,
`timeout_reply`; test-only exports under D25. Files: `ts/media.ts`,
`API/ts/media.d.ts`. State: awaiting acceptance.

4.5.14 `ConsoleView.open_request()` (returns a `dispatch.Sleep`, throws
`console_view.open_phase` unless idle), `open_done(wake)`, `exit_done()`
(throws `console_view.exit_phase` unless open), and the wake type
`ui.console_reply` with state `null`, which is in neither `lines.d.ts` nor
the stub. Files: `ts/console_view.ts`, `ts/page.ts`,
`API/ts/console_view.d.ts`, `API/ts/lines.d.ts`. State: awaiting
acceptance. 4.5.30 adds the later console additions.

4.5.15 `jslb.blob_make` with `size` (D3, 4.4). Files: `ts/jslb.ts`,
`API/ts/jslb.d.ts`. State: awaiting acceptance.

4.5.16 Public helper names in `python/devtools.py` (such as
`EndpointAddress`, `SocketFrame`, `WaitTimer`, `PageEvents`,
`ProtocolClient`, `frame_encode`, `message_read`, `relay_script`,
`command_run`, `path_wsl`), public because pyright strict refuses private
access from the tests; the public helpers of `python/page_build.py`, with
`__all__ = ["page_build"]`; `page_build.main()`, the command line
`python3 python/page_build.py <name> [--test]`; `test_all.suites_run()`, the
test page's entry. Files: `python/devtools.py`, `python/page_build.py`,
`ts/test_all.ts`, `API/python/devtools.pyi`, `API/python/page_build.pyi`.
State: awaiting acceptance.

4.5.17 Replication, decided by the coordinator: the internal line types
`replicate.next` and `replicate.done`, which are not in `lines.d.ts`;
replication done as page tasks over `Store.forward_set(fn)`, where the plan
puts it inside the substrate: the forward function appends the line to a
FIFO per database and notifies a local `replicate.next` task, whose handler
submits the oldest line of a database with none in flight to the server and
sleeps on `replicate.done`, so that lines go after the commit, in order, one
in flight per database, through the task manager; and the explicit owner
route of 4.5.5, which the plan lists as not built. Files: `ts/worker_ai.ts`
(`ForwardQueue`), `ts/substrate.ts`, `ts/queue.ts`, `API/ts/lines.d.ts`,
`API/ts/substrate.d.ts`. State: awaiting acceptance. The reply check is the
one of D1 (4.4).

4.5.18 The server root layout: `<root>/python/bootstrap.py` and
`<root>/i18n/`, mirroring the checkout's runtime files, where the plan shows
`bootstrap.py` at the root. Files: `xsjs_install.ps1`, `xsjs_start.ps1`
(the runtime modules copied, `python/seed` copied), `python/bootstrap.py`,
`python/test_wire.py` and `python/test_browser.py` (roots built as the start
script builds them). State: awaiting acceptance; the plan's text was not
edited.

4.5.19 The setting `db_soft_bytes`, and the tools `db_stats`, `db_compact`,
`db_unload` and `db_load`, of the database administration design the
maintainer asked to have built. The settings `message_max` and `queue_max`
that once stood beside it are withdrawn by the one blob window. Files:
`settings.json`, `python/settings.py`, `ts/settings.ts`, `ts/substrate.ts`,
`ts/tools_browser.ts`, `ts/agent.ts`, `API/ts/settings.d.ts`,
`API/mcp/tools.json` (the four tools are not in it). State: awaiting
acceptance; `message_max` and `queue_max` withdrawn.

4.5.20 The modules `tap_producer` and `tap_consumer`, in place of the plan's
`tap/producer.py`, `tap/consumer.py` and `tap.ts`. Files:
`python/tap_producer.py`, `python/tap_consumer.py`, `ts/tap_producer.ts`,
`API/python/tap_producer.pyi`, `API/python/tap_consumer.pyi`,
`API/ts/tap_producer.d.ts`. State: the stubs were moved to these names by
the job; the module names are a reading of the maintainer's words whose
question stays open with them built (4.8.4.1).

4.5.21 `i18n` names beyond what was ordered: `bootstrap.option_repeated`,
`bootstrap.main_loop_refused` (D10, 4.4), `main_loop.input_partial`, raised
as `jslb.WireError` for end of input inside a message, and the
`console_view.*` phase names. Files: `python/bootstrap.py`,
`python/main_loop.py`, `ts/console_view.ts`, `i18n/en-US.json`. State:
awaiting acceptance.

4.5.22 The API additions of the earlier job's agents of databases, of the UI
test page and of the browser tracing were accepted by the maintainer's
message of 2026-10-20 at 22:58 (4.1), which asked for their `API/` texts to
be applied, except those the blob window removes; 4.5.23 to 4.5.26 say
which. State: accepted; the stub texts were applied.

4.5.23 Dropped: the `db.chunk` design, which existed only to carry a
snapshot in pieces under `message_max`; the blob window makes the largest
database one blob, so `db.snapshot` is one blob again. Gone with it: the
line type `db.chunk` and its payload `DbChunk {snapshot, offset, size}`; the
head reply of `db.snapshot`, `DbSnapshotReply {snapshot, size, sha256, seq}`
with no blob, and the server keeping the bytes under a number; TypeScript
`substrate.SnapshotFetch` and `substrate.SnapshotHead`; TypeScript
`Store.snapshot_keep(db)`, `Store.snapshot_read(snapshot, offset, size)` and
`Store.blob_take(data)`; TypeScript `worker_ai.StartStore.blob_take` and
`worker_ai.ChainParts.settings_get`; Python `substrate.SnapshotHead`,
`Store.snapshot_keep`, `Store.snapshot_read` and `engine_db.db_chunk`; the
strings `substrate.piece_none`, `substrate.piece_size`,
`substrate.snapshot_range` and `substrate.snapshot_unknown`. Kept:
`substrate.snapshot_digest`, since the one blob's digest is checked, and
`substrate.cache_unknown` and `substrate.fill_desync`. Files:
`ts/substrate.ts`, `ts/worker_ai.ts`, `python/substrate.py`,
`python/engine_db.py`, `i18n/en-US.json`, `API/ts/lines.d.ts`. State: a
decision of the maintainer; no `db.chunk` name is in `API/`.

4.5.24 Accepted, three TypeScript `Store` methods: `kv_held(ref, db?)`,
whether this side holds a value's bytes, in its row or a file;
`cache_fill(ref, data, db?)`, which puts back the cache file of a value from
bytes or a cache handle whose digest is the row's; `cache_evict(db, keep,
budget)`, which frees a database's cached files by key, but those the kept
refs and other databases name, until they fit the budget, and returns the
count freed. Files: `ts/substrate.ts`, `ts/tools_browser.ts`,
`API/ts/substrate.d.ts`. State: accepted, in the stub.

4.5.25 Accepted, the test engine page: `page.test_engine(run: (tasks:
queue.TaskQueue) => void): void`, `boot.test_engine` with the same
signature, the module `test_hook` with `engine_run(): void`, in the test
bundle only, and `page_build.page_build(name: str, test: bool, template:
str) -> str`. `page` has no stub, and `API/ts/boot.d.ts` leaves test-only
functions out as it does `test_page`, so only `API/python/page_build.pyi`
changed. Files: `ts/page.ts`, `ts/boot.ts`, `ts/test_hook.ts`,
`html/test_engine.html`, `python/page_build.py`,
`API/python/page_build.pyi`. State: accepted, in the stub.

4.5.26 Accepted, additions to `python/devtools.py`:
`ProtocolClient.session_call(session_id, method, params)`,
`Browser.trace_start(categories)`, `Browser.trace_end()`,
`Browser.worker_pause(name)`, `blocking_categories()`,
`blocking_find(events)`, and the `PageEvents` fields `trace`, `trace_done`,
`trace_lost`, `workers` and `paused`. Its replacement text of
`API/python/devtools.pyi` was applied as written; that text declares
`PageEvents.lifecycle` only, so the five fields stay out of the stub, and it
has no `Browser.__init__`, `__enter__` or `__exit__`. `__all__` of
`python/devtools.py` is `["Browser", "blocking_categories",
"blocking_find"]`. Files: `python/devtools.py`, `python/test_browser.py`,
`API/python/devtools.pyi`. State: accepted, in the stub.

4.5.27 The records name these further additions and departures, which the
list above does not hold. Each stays as built under D11 unless its state
says otherwise.

4.5.28 `error_overlay.FaultScreen` with `stop_register`, `overlay_show` and
a private first-fault flag; the module functions pass through to one page
instance, so that a test does not flag the test page for good (rejected: a
module flag, a flag in the document). Files: `ts/error_overlay.ts`,
`API/ts/error_overlay.d.ts`. State: awaiting acceptance.

4.5.29 Departures from `API/ts/wire.d.ts`: the constructors
`WirePort(base_url, sink, settings_get)` and
`ConsolePort(base_url, settings_get)`; `ConsolePort.console_open(fn)`
removed, `console.open` being a request line the port answers (rejected:
keeping `console_open` with an adapter in the page). Additions:
`WirePort.cache_attach`, `ConsolePort.message_take`,
`ConsolePort.close_take`, and `FrameQueue` with `line_add` in place of
`pieces_add`; its constructor once took `chunk_bytes`, `message_max` and
`queue_max`, the last two since withdrawn by the blob window. Later
`WirePort.line_take` throws the new string `wire.error_first`, with the
server's message and stack, for an `error` line before `hello`, and the port
then shuts. Files: `ts/wire.ts`, `ts/boot.ts`,
`API/ts/wire.d.ts`, `API/ts/lines.d.ts` (the proposed row `console.open`
with `ConsoleOpenReply`). State: awaiting acceptance.

4.5.30 Console additions of the later job: `ConsoleView.open_wanted`,
`close_request` and `close_done`; `page.ConsoleControl` gains two members;
`worker_ai.console_register` gains `close`; the wake type
`ui.console_closed`, not in `lines.d.ts`; the view's phase "closed" removed
and "closing" new; the strings `console_view.close_phase` and
`console_view.closed_phase`. `console.close` has a sender and a handler, and
no UI action calls the sender, an approved item (4.8.2). Files:
`ts/console_view.ts`, `ts/page.ts`, `ts/worker_ai.ts`, `i18n/en-US.json`,
`API/ts/console_view.d.ts`, `API/ts/lines.d.ts`. State: awaiting
acceptance.

4.5.31 Departures from `API/ts/substrate.d.ts`: the constructor
`(sqlite3, pool, cache, root, overflow_bytes, compact_turns)`, six
arguments where the stub has four, `pool` and `cache` added (rejected: one
bundle object), `forward_set(fn, full)` for the name form of D27 (4.4), and
`handlers_register(register)`. Additions: `seq_get(db)` (4.5.4),
`forward_done(line, reply)`, `db_stats(soft_bytes): StoreStats` (`{databases:
[{name, bytes, free_bytes, cache_bytes, seq}], total_bytes, soft_bytes,
over}`, `over` meaning `total_bytes > soft_bytes`), `db_compact(db):
{before, after}`, `db_unload(db)`, `db_load(db, data): number`,
`start_open(server_seq): string[]`, and the class `CacheFiles(slots)` with
`slot_add`, `slots_free`, the sink methods and `cache_read`. The job's last
audit recorded that `forward_set` takes one argument in the stub and two in
the code; this entry is the record of that departure. Files:
`ts/substrate.ts`, `ts/worker_ai.ts`, `ts/boot.ts`, `ts/tools_browser.ts`,
`ts/script.ts`, `API/ts/substrate.d.ts`. State: awaiting acceptance.

4.5.32 Python stub departures of the engine modules: `doc_put`'s body typed
`dict[int | str, Any]`, and `since` on `db_create` and `db_drop` (D1, 4.4).
Files: `python/engine_doc.py`, `python/engine_db.py`,
`API/python/engine_doc.pyi`, `API/python/engine_db.pyi`. State: awaiting
acceptance.

4.5.33 `unittest.expectedFailure(method)`, with `addExpectedFailure` and
`addUnexpectedSuccess` on the result, and the `AssertionError` name set on
the prototype; the expected failure mechanism the maintainer asked for.
Files: `ts/unittest.ts`, `API/ts/unittest.d.ts`. State: awaiting
acceptance.

4.5.34 The Python TAP producer's `module_run(module, load)` and `run_end()`,
because tappy has no named nested blocks (rejected: `set_module(name)`, a
separate call for a module that does not load); the TypeScript producer has
the same names. `set_stream` is per instance and takes a line callback, not
tappy's class method. Files: `python/tap_producer.py`,
`ts/tap_producer.ts`, `API/python/tap_producer.pyi`,
`API/ts/tap_producer.d.ts`. State: awaiting acceptance; the departures from
tappy's names are part of a class B item (4.8.6.1).

4.5.35 `ts/mcp.ts`: the departures `Client(name, version, tasks, owner,
full?)`, for the name form of D27, and `constants` holding the protocol's
field and method names and codes; the additions `WakeFn`,
`Server.wake_register(then_type, fn)`, `Server.line_handle(line)`,
`Client.initialized_send(reply)`, `Client.tools_read(reply)`,
`Client.tools_cached()` and `ClientSet.result_of(reply)`. Files:
`ts/mcp.ts`, `ts/worker_ai.ts`, `ts/agent.ts`, `API/ts/mcp.d.ts`. State:
awaiting acceptance.

4.5.36 `ts/tools_browser.ts`: the departure `tools_register(server, store,
tasks, provider_owner, info, settings_get)`, its model parameter since
replaced by `info` (4.5.37), and the addition of the four database tools
of 4.5.19 with proposed descriptions and schemas for `API/mcp/tools.json`.
The tools register 20 tools: the sixteen browser tools of `tools.json`,
then `db_stats`, `db_compact`, `db_unload` and `db_load`; a seventeenth,
`verbose_level`, went with the shell only verbose levels
(4.6.11.16, 4.8.4.22).
Files: `ts/tools_browser.ts`, `API/ts/tools_browser.d.ts`,
`API/mcp/tools.json`. State: awaiting acceptance. When the provider file
came, the job's documentation agent wrote `info` in place of the model
parameter into `API/ts/tools_browser.d.ts` and `API/ts/agent.d.ts`,
following the provider file (4.8.7.4), and applied none of the agents' other
departures.

4.5.37 `ts/agent.ts`: the departure `agent.handlers_register(store, clients,
tasks, provider_owner, chat_model, settings_get, register)`, its model
parameter since replaced by `info` as in 4.5.36. Files: `ts/agent.ts`,
`API/ts/agent.d.ts`. State: awaiting acceptance.

4.5.38 `worker_ai.info_read`, which reads the provider information that
`hello` carries; the information is passed as an argument (rejected:
`provider.info_set` module state). Files: `ts/worker_ai.ts`,
`API/ts/lines.d.ts` (`ProviderInfo` and `Hello.provider_info`, applied by
the job). State: awaiting acceptance.

4.5.39 Other public names the records list as added and checked present,
with no stub entry: `test_wire.replay_build`, public for the page's replay;
the strings `bootstrap.hello_submit`, `main_loop.line_dispatch` and
`main_loop.line_reply` of the server's trace, header JSON only; the test
helpers `kill_pool`, `kill_hold`, `kill_put` and `kill_check` of
`ts/test_substrate.ts`; the module `python/category.py`, with its stub
`API/python/category.pyi`, written by the job; `reformat.table_read`, which
reads `python/reformat_table.json`, with no stub, because
`API/python/reformat.pyi` is a design kept in the plan and not built. Files:
`python/test_wire.py`, `python/bootstrap.py`, `python/main_loop.py`,
`i18n/en-US.json`, `ts/test_substrate.ts`,
`python/category.py`, `python/reformat.py`. State: awaiting acceptance,
but `category.py`, whose stub the job wrote from the plan.

4.5.40 Named by the records as API additions and not built, so not in the
code: `WireError.slug` (D5 chose against it); `substrate.json_canonical`,
`substrate.scene_database`, `Store.doc_has`, `Store.db_create(name,
statements)`, `sink_abort`, `limit_attach`, `WirePort.settings_take()` and
`browser.turn_compact`, each an alternative a record rejected or left; a
`verbose_flags` parameter, replaced by `argv_verbose`; and the platform port
in `ts/queue.ts` for the worker's asynchronous setup, with its internal line
types, which a coordinator decision ordered and the maintainer's rule on
system initialization withdrew before it was built (4.8.1.3).

4.6 Edits proposed for the maintainer's files. The earlier jobs ranked the
maintainer's words first, then their own record of the maintainer's
decisions, then the plan, then the stubs under `API/`; their agents did
not edit the plan or the stubs on their own account, and the edits needed
to make those files agree were listed for the maintainer. Two tasks then
applied those that carry a decision of the maintainer: the documentation
task of 2026-10-20, at the maintainer's request, and later that day an
agent of the next job, which applied the stub texts the maintainer asked
for. Each edit below says whether it was applied. The plan is no longer in
the tree; an edit of the plan is kept for what it says of the design.
Where a stub and the code differ as an edit not applied here records, the
difference is accepted and listed, not a finding.

4.6.1 The plan's sizes. All applied by the documentation task, and since
replaced in the plan by the one blob window, under which a message's blobs
sum to at most `blob_max`, memory per message is bounded by `line_max`
plus `blob_max`, and `message_max` and `queue_max` are gone:

4.6.1.1 the hard errors: "`blob_max`, 10 MiB, and `message_max`, 10 MiB,
a line and its blobs together";

4.6.1.2 streaming blobs: "Memory per connection is bounded by
`message_max`", applied as "Memory per message", the words of the decision
on sizes that settled the plan's contradictory memory bound, with the
`queue_max` bound beside it;

4.6.1.3 the settings: `message_max`, `queue_max` and `db_soft_bytes`
added; `db_soft_bytes` stays;

4.6.1.4 the UI thread stress test and the proofs of stages 2 and 5: the
16 MiB `kv.put`, `kv.get` and round trip as the largest message that fits
`message_max`, a message one byte larger refused, and the 128 MiB
measurement of ttyd's resident size as messages that each fit; applied
with the plan's transport and flow control and the 128 MiB rendering of
the debug overlays. The proofs now move a blob of `blob_max`.

4.6.2 The plan's protections, all applied by the documentation task:

4.6.2.1 the tools: "The substrate's own tables and `_settings` refuse
writes." deleted and replaced by "SQL rules are not a security boundary:
no table or database refuses a write.";

4.6.2.2 the databases: "`_settings` is immutable" deleted as an enforced
rule;

4.6.2.3 the proof of stage 3, the substrate: "a write to a `_` table or
to `_settings` refused" deleted;

4.6.2.4 the list of things not done without permission: the item on
`sql_run` guarding rewritten rather than deleted, so that it records both
the `EXPLAIN` guard and the refusal by name as decided against (4.3.31).

4.6.3 The plan's architecture and Python modules:
`verbose.exec(level, argv, argv_verbose)`. Applied, with the reading that
level 2 runs the caller's whole `argv_verbose` marked Unconfirmed.

4.6.4 The plan's Python and TypeScript module lists, its test stream and
the proof of stage 0: the TAP modules `tap_producer` and `tap_consumer`,
custom written after tappy's names, their own tests run before every other
test.
Applied, with the checkout's description, the dependency graph and the
runners, and the readings of the module names and of tappy's names,
recalled from memory, marked Unconfirmed.

4.6.5 The plan's request ids: one counter per thread queue, not per port
(D2). Not applied: D2 is a default, not a decision of the maintainer.

4.6.6 The plan's replication: `since` on `db.create` and `db.drop`, and a
new database at `seq` 0 (D1: `db_create` leaves it 0, `db.create` carries
`since` 0, `db.drop` the database's `seq`, and the reply `seq` check is
skipped for both). Not applied: D1 is a default.

4.6.7 The plan's operations: the server root layout
`<root>/python/bootstrap.py` and `<root>/i18n/`, where the plan shows
`bootstrap.py` at the root. Not applied: a departure awaiting the
maintainer's acceptance (4.5).

4.6.8 The plan: a section holding the database administration design, the
soft limit `db_soft_bytes` measured by heuristics and the four tools
`db_stats`, `db_compact`, `db_unload` and `db_load`. Applied as a section
on database administration in the plan's data chapter, not among the
things not built, because it is built.

4.6.9 `API/` and its settings, file by file:

4.6.9.1 `API/python/verbose.pyi`: `exec`. Applied, with the comment of
`API/python/bootstrap.pyi`. Both stubs were later replaced whole
(4.6.11.11, 4.6.11.18).

4.6.9.2 `API/python/jslb.pyi` and `API/ts/jslb.d.ts`: the decoder's
`message_max`, `LineDecoder.idle()`, and `blob_make` with `size`. Not
applied: `idle()` and `size` await acceptance as API additions;
`message_max` was later withdrawn by the one blob window (4.6.11.3,
4.6.11.4).

4.6.9.3 `API/python/main_loop.pyi`: `loop_prepare(root) -> dict[str,
int]`, called once per process before `hello`, which every replacement
main loop must define. Not applied: awaits acceptance.

4.6.9.4 `API/python/substrate.pyi`: `Store.seq_get(db)`. Not applied:
awaits acceptance. The stub's comment that `sql_run` refuses writes was
removed (applied).

4.6.9.5 `API/python/engine_db.pyi`: `since`. Not applied: D1, the default
of 4.6.6 on `since` and a new database's `seq`.

4.6.9.6 `API/ts/lines.d.ts`: `DbName` gains `since` (D1, as in 4.6.6);
`ConsoleOpenReply { token: string; }` (D23: the `console.open` reply
carries `token`, fetched from `/token`); rows for `replicate.*` and
`ui.console_reply`, replication's internal line types and the console
view's wake type, both awaiting acceptance; and the comment of the
`http.request` reply, from a rule of an earlier review. Not applied: none
is a decision of the maintainer. Applied: `Hello` gains `provider_info`,
and the interface `ProviderInfo` is added, under the provider file, the
coordinator's default on the maintainer's provider answer, which the
maintainer has not confirmed (4.8.7.4).

4.6.9.7 `API/settings.json`: the sizes and the new keys `message_max`,
`queue_max` and `db_soft_bytes`. Applied, with `base_url`,
`chat_model` and `image_model` removed by the provider file decision, and
the same in `API/ts/settings.d.ts`. Changed again later (4.6.11.1,
4.6.11.2).

4.6.9.8 `API/mcp/tools.json`: `sql_run`'s description without its refusal
sentence, applied; the four database tools, not applied, because they
await acceptance and the decision gave their names and arguments, not their
descriptions and schemas.

4.6.9.9 `API/ts/tap.d.ts` and `API/ts/unittest.d.ts`: the TAP modules.
`tap.d.ts` applied as `API/ts/tap_producer.d.ts`, with
`API/python/tap/producer.pyi` and `consumer.pyi` moved to
`API/python/tap_producer.pyi` and `API/python/tap_consumer.pyi`.
`unittest.d.ts` not applied: its run methods (the `TestCase` constructor
with the method name, `id()`, `run(result)`, `TestSuite.run(result)` and
the `TestResult` members) await acceptance.

4.6.9.10 `API/ts/boot.d.ts`: "`self.name` is empty on the main thread".
Not applied: a finding about the code, not a decision.

4.6.9.11 `API/ts/utility.d.ts`: `json_text` is `JSON.stringify` with
number checks. Not applied: it rests on D26, `utility`'s messages through
`i18n` and a strict `base64_decode`, a default.

4.6.9.12 `API/ts/media.d.ts` and `API/ts/console_view.d.ts`:
`media.ImageCache` and `media.MediaExchange`; `ConsoleView.open_request()`,
`open_done(wake)`, `exit_done()` and the wake type `ui.console_reply`. Not
applied: they await acceptance.

4.6.10 Applied by the documentation task beyond that list:

4.6.10.1 `API/mcp/tools.json` without the permit mark `"_meta": {"xsjs":
{"permit": true}}` of `source_put` and `system_restart`; the plan's permit
set `console_run` alone; the plan naming `boot.ts`, the one
initialization module, beside the four modules the synchronization audit
allows;

4.6.10.2 the plan's Unconfirmed tool limits on `db_create` replaced by the
decision that no tool limit refuses it;

4.6.10.3 the plan's recorded operation sequences made sequences the test
builds;

4.6.10.4 the provider file in the plan, `API/settings.json`,
`API/ts/settings.d.ts` and `API/ts/lines.d.ts`, and the `info` parameter
in `API/ts/agent.d.ts` and `API/ts/tools_browser.d.ts` in place of the
model parameter;

4.6.10.5 in the plan, the timer rule (each timer a named constant whose
comment says it is a default chosen by its writer), the invisibility of
`#debug` under the fixed `#image` as a bug, the formatter, and MB read as
MiB;

4.6.10.6 the refusal sentence of `API/sql/substrate.sql` removed;

4.6.10.7 the whitelist line `API/python/tap/*.pyi` removed.

4.6.11 The stub edits for the one blob window, the shell only verbose
levels and the event counter, with the stub texts of three agents the
maintainer accepted (4.5). All eighteen applied by one agent of the next
job on 2026-10-20; 4.6.11.8 needed no change; a later read only audit
confirmed every one. Nothing outside the list changed: a stub's drift from
the code that none of them covers was left as it was.

4.6.11.1 `API/settings.json`: `blob_max` becomes 2147483391; `message_max`,
`queue_max` and `verbose_forward` go; `"turn_compact_tokens": 65536`
becomes `"turn_compact_turns": 64` in the same place; the key order is
`debug`, `queue_synchronous`, `verbose_level`, `verbose_ring`, `line_max`,
`blob_max`, `overflow_bytes`, `chunk_bytes`, `srv_buf_size`,
`media_db_bytes`, `files_browser_bytes`, `db_soft_bytes`,
`turn_compact_turns`, `long_task_ms`, `provider`, every other value
unchanged.

4.6.11.2 `API/ts/settings.d.ts`, interface `Settings`, the same keys:
`verbose_forward`, `message_max` and `queue_max` go;
`turn_compact_tokens: number;` becomes `turn_compact_turns: number;`.

4.6.11.3 `API/python/jslb.pyi`: `LineDecoder.__init__(self, line_max:
int, blob_max: int, overflow_bytes: int, sink_make: Callable[[Object],
str])` already had the one window's signature and stays; above `class
LineDecoder:` comes the one line "# WireError: a line over `line_max`, or
blobs over `blob_max` in all."; `idle()` stays out, awaiting acceptance.

4.6.11.4 `API/ts/jslb.d.ts`: the constructor `(line_max, blob_max,
overflow_bytes, sink)` stays; the same comment line, with `//` and
indented two spaces, comes above `class LineDecoder {`.

4.6.11.5 `API/ts/lines.d.ts`: `db.snapshot` stays as it was, its row
`DbSnapshotReply + 1` and `DbSnapshotReply { sha256: Sha256; seq: number;
}` with its comment, one reply and one blob; no `db.chunk` row and no
`DbChunk`; `VerboseLine` loses `level` and is `{ at: number; text: string;
}`.

4.6.11.6 `API/ts/agent.d.ts`: a comment above `handlers_register`, whose
signature stays, describing the turn as a chain of tasks on the AI thread:
`ai.say` and `ai.click` append the player's turn, submit the provider
request and sleep with `ai.model_reply`; `ai.model_reply` submits each
tool call of a reply and sleeps with `ai.tool_reply`, storing nothing yet;
`ai.tool_reply` stores that reply and its tool results together in one
transaction and submits the next provider request; a reply with no tool
calls is stored and ends the turn with `TurnEnd`; no stored call lacks its
result; in debug mode the queue log is the transcript of the turn.

4.6.11.7 `API/ts/substrate.d.ts`, class `Store`: the constructor gains
`compact_turns: number` after `overflow_bytes`, as `constructor(sqlite3:
unknown, root: string, overflow_bytes: number, compact_turns: number);`;
above `turn_append(` comes "// A `user` turn on a scene of
`compact_turns` turns first compacts them."; after `db_restore(...)` come
three methods, each with a one line comment: `kv_held(ref: lines.KvRef,
db?: string): boolean`, whether this side holds a value's bytes, in its
row or a file; `cache_fill(ref: lines.KvRef, data: Uint8Array | string,
db?: string): void`, which puts back a value's cache file from bytes with
the row's digest; `cache_evict(db: string, keep: readonly string[],
budget: number): number`, which frees a database's unkept cache files to
the budget and returns their count. Nothing of `SnapshotFetch`,
`SnapshotHead`, `snapshot_keep`, `snapshot_read` or `blob_take`.

4.6.11.8 `API/python/substrate.pyi` and `API/python/engine_db.pyi`: none
of the snapshot piece names; the `db_snapshot` comment of `engine_db.pyi`
already says one blob.

4.6.11.9 `API/python/page_build.pyi`, replaced whole by two lines: the
comment "# Builds `build/<name>.html` from `html/<template>`. Returns its
hash." and `def page_build(name: str, test: bool, template: str) -> str:
...`.

4.6.11.10 `API/python/devtools.pyi`, replaced whole by the text of the
agent that added tracing and the worker pause to `python/devtools.py`, as
written: it declares `ProtocolClient.session_call(session_id, method,
params)`, `Browser.trace_start(categories)`, `Browser.trace_end()`,
`Browser.worker_pause(name)`, `blocking_categories()` and
`blocking_find(events)`, and of `PageEvents` only `lifecycle`, so its
fields `trace`, `trace_done`, `trace_lost`, `workers` and `paused` stay out
of the stub. That text has no `Browser.__init__`, `__enter__` or
`__exit__`; this was recorded and not acted on.

4.6.11.11 `API/python/verbose.pyi`, replaced whole: `LogLine`, a
NamedTuple of `at: int` and `text: str`, one line in milliseconds since
the epoch and its text; `log(text: str) -> None`, writing one line to
`_verbose`, unbuffered, and to the ring of `verbose_ring`;
`history_get(count: int) -> list[LogLine]`, the last `count` lines of the
ring, oldest first; `exec(level: int, argv: list[str], argv_verbose:
list[str]) -> int`, the shell's runner, `argv` at level 0 or 1 and
`argv_verbose` raw at 2.

4.6.11.12 `API/ts/verbose.d.ts`, replaced whole: namespace `verbose` with
`log(text: string): void`, writing one line to the ring of `verbose_ring`
lines and handing it to the sink; `history_get(count: number):
lines.VerboseLine[]`, the last `count` lines, oldest first; and
`sink_set(fn: (line: lines.VerboseLine) => void): void`, the one consumer
of new lines, the thread's queue, which batches them into `verbose.put`
when `debug` is on.

4.6.11.13 `API/sql/verbose.sql`: the line `level  INTEGER NOT NULL,` goes.

4.6.11.14 `API/ts/queue.d.ts`: in the comment above `class TaskQueue`,
"Every submit, dispatch, sleep, wake and reply is a verbose line at level
2." becomes "In debug mode every submit, dispatch, sleep, wake and reply
is a verbose line.". Left as found: a comment in that stub citing "debug
mode of 4.2", a section number of the plan.

4.6.11.15 `API/ts/script.d.ts`, replaced whole: namespace `script` with
`ScriptResult`, the value or the exception with its stack, and the verbose
lines the run wrote (`value?: unknown; error?: string; stack?: string;
lines: lines.VerboseLine[];`); `Engine`, the frozen object a script
receives as `engine`, of `store: substrate.Store`, `log(text: string):
void` and `i18n(name: string, ...args: unknown[]): string`; and
`script_run(store, name, args, trace: boolean): ScriptResult`, which runs
`/_files/script/<name>.js` with `new Function("engine", "args", text)`
inside the calling task, and with `trace`, as `script_debug` runs it,
traces each substrate call first.

4.6.11.16 `API/mcp/tools.json`: the `verbose_level` tool object goes;
`script_debug`'s description becomes "Run the script as script_run does,
tracing every substrate call it makes first.".

4.6.11.17 `API/ts/tools_browser.d.ts`: `verbose_level` leaves the tool list
of the comment.

4.6.11.18 `API/python/bootstrap.pyi`, replaced whole: one function,
`bootstrap_run(argv: list[str]) -> int`, its comment saying `python3
bootstrap.py --root <root> [console]` returns the exit code; the engine
role takes the lock, sets raw mode, writes `hello` and runs the main loop
file; the console role runs dash through `verbose.exec` at the setting
`verbose_level` in debug mode and exits 1 otherwise; it is immutable
outside debug mode.

4.6.12 Outside this list: `API/python/category.pyi` was written by the
last job with the test categories and later gained `alarm_plan`, from the
decisions on test categories and on the infrastructure for testing; an
audit found it equal to `python/category.py`. The formatter run of
2026-10-21 reformatted the whitelisted stubs under `API/` with the rest of
the tree; its report names changes of layout and quoting with the same
values.

4.7 Open questions. Each item below is a point an earlier job left to the
maintainer, with its options where the records give them; none of the
options is built and no later record answers it. The review chooses none: an
agent that meets one lists it and changes nothing for it. Each item names the
files it touches, so that the agent of each area knows it when it meets it.
The questions an earlier job answered, and those still open with one of
their options built, are in 4.8.4; the built option of an open one stands
for the review, and the question stays the maintainer's, the banner
of 4.8.4.39 first, since it stops every run.

4.7.1 The UTF-8 byte order mark of three PowerShell files. `xsjs_stop.ps1`,
`xsjs_status.ps1` and `powershell/test_lint.ps1` have no byte order mark,
which the PowerShell rule of the earlier job's agent instructions requires
(every PowerShell file starts with one; the project rules hold no such
rule), and they hold the copyright sign, so PSScriptAnalyzer's
`PSUseBOMForUnicodeEncodedFile` may report them on Windows. D22, the hold
on the previous design's files (4.4), holds the first two. Options: none
recorded for the three files themselves; the one unbuilt option of the
byte order mark question (4.8.4.38) would require the mark at the start of
every PowerShell file, so that the three fail until they gain one. Files:
`xsjs_stop.ps1`, `xsjs_status.ps1`, `powershell/test_lint.ps1`,
`python/test_posix.py`.

4.7.2 `ttyd.log`. The plan puts `ttyd.log` in the server root; the start
script writes it under `%LOCALAPPDATA%`. A design that meets the plan was
recorded and not built: ttyd started as
`sh -c 'exec "$0" "$@" 2>>"<root>/ttyd.log"'`. Options: the script as it is,
or the recorded design. Files: `xsjs_start.ps1`.

4.7.3 `python/mcp_stdio.py` sets no `sys.pycache_prefix`: its sibling
imports are needed at module level, and setting the prefix first would trip
ruff's E402; run as a script it writes `__pycache__` beside the sources
unless `PYTHONPYCACHEPREFIX` is set. Options: `# noqa: E402`; "imports
inside `stdio_serve` with the subclass", a subclass since removed with the
stdio refusal (4.8.1.3); a launcher; documenting `PYTHONPYCACHEPREFIX`. Files:
`python/mcp_stdio.py`.

4.7.4 The `universe` table does not make `world` unique, so the lookup of a
universe's prompt (D17, 4.4) can be ambiguous: two rows with one world match
twice, and in the hyperposition no row matches. `agent.prompt_build` reads
the universe's prompt only when exactly one `universe` row has the current
world. Options: `world` made UNIQUE; a hard error in `agent.prompt_build`.
Files: `API/sql/metaverse.sql`, `ts/agent.ts`, `python/seed/bootstrap.js`,
`python/seed/prompt.json`.

4.7.5 `engine_turn` builds canonical JSON with `json.dumps(...,
ensure_ascii=False, separators=(",", ":"), allow_nan=False)`, which lacks
the substrate's private check that integers stay within 2^53. The
alternatives the record named: an API addition
`substrate.json_canonical(value)`; keeping `operation_apply` and the O(N)
`turn_list`; `MAX(n)` through `sql_run`, a layering breach. A later record
adds that the browser's `json_canonical` runs only on data made in the
browser. That the TypeScript store refuses doubles above 2^53 with
`substrate.integer_range`, where Python stores them, so that an AI script
storing 1e16 faults, was approved by the maintainer with the other class B
items of that job (4.8.2, 11.16.4.15), and is not part of this question.
Files: `python/engine_turn.py`, `python/substrate.py`.

4.7.6 `engine_sql` and `engine_turn` read `seq` before the write lock, which
is taken lazily. This is sound only under the single process model. No
options are recorded. Files: `python/engine_sql.py`,
`python/engine_turn.py`.

4.7.7 argparse still accepts `-h`, so a client's `--url-arg -h` prints help
to the pty and exits 0. No options are recorded. Files:
`python/bootstrap.py`.

4.7.8 The xterm `Terminal` constructor options `{cols, rows, disableStdin}`
were written from memory of the 5.x API and not checked against the
pinned 5.5.0 typings, and the resize path is unreachable without a fit
addon.
Options for the resize path: pin `@xterm/addon-fit`, or delete `resize_send`
and its tests. Files: `ts/console_view.ts`, `ts/test_console_view.ts`.

4.7.9 The Lookup Accelerator of the project rules, which the maintainer's
commit 168ac16 removed ("remove accel to prevent contamination"); the
earlier job's task to update it is held, because the project rules forbid
editing them without request. Options: a) it stays removed, as now; b) the
maintainer writes it; c) an agent writes it. Files: the project rules, which
no agent edits.

4.7.10 The agents' read-only commands outside their allowlist. In every
session of the earlier jobs agents ran `cd`, `head`, `awk`, `sed`, `echo`,
`tr`, `sort` and shell loops, read only, after their instructions named them
as forbidden; none ran project code. Options: a) accept them as logged; b)
the maintainer restricts the agents' Bash permission to `mv`, `mkdir -p`,
`ls`, `grep`, `wc` and `test`; c) treat each as a defect that reopens the
task. Files: none in the tree.

4.7.11 The defaults D1 to D31 (4.4). Options: a) accept all; b) name the
ones to change. Files: those named in 4.4.

4.7.12 The formatter split the hooked line of the test engine page. prettier
split the one line of `html/test_engine.html` that holds the
`<script data-worker>` element calling `test_hook.engine_run();` over three
lines, and `test_template_hooked` of `python/test_page_build.py` counts that
one line, so it fails; a smoke-test run, which ends at its first failure,
stops there first when nothing earlier fails. Options: a) a
`<!-- prettier-ignore -->` line above it; b) the test matches the hook
whatever its white space; c) the change reverted by hand, which the next
format run undoes. Files: `html/test_engine.html`,
`python/test_page_build.py`, `python/reformat.py`.

4.7.13 A verbose line written before the settings. The ring of
`ts/verbose.ts` reads the `verbose_ring` setting from the first line, so a
line written before `settings_set` throws. The question the earlier job put
to the maintainer: is such a line ever wanted? It was shown as an open
question, not as a class B item, and the maintainer's approval of that day
left it open. Its options a) to d) were in a document that no longer exists.
Files: `ts/verbose.ts`, `ts/settings.ts`.

4.7.14 The other findings of the postmortem of 2026-10-20 at 21:43, which
it asked the maintainer to decide before testing and which the answer of
22:58 left undecided (4.8.1.7): the files the whitelist misses
(`html/engine.css`, `python/seed/provider_script.json`, older JSON, SQL,
TOML and tsconfig files) and the comment lexers they would need;
`LICENSE.md` and `README.md` in the whitelist; `from i18n import i18n`
(3.13); the provider's Script kept at or under `overflow_bytes`, as the
worker reads it as text with no fetch on a miss; the sleep loop of
`devtools.page_open` (D15, 4.4); and in `python/test_browser.py` the
constants after their classes, the sibling imports inside functions, the
page names read the wrong way round, the older probe names of one word,
and `probe.fault` finding the TAP `<pre>` of the test page. Where the
project rules or this file's expected design settle one (the place of
constants, the two word names, the fetch on a miss of 2.10.7), the review
follows them as for any finding; the others it lists and does not change.
The whitelist's misses rest on recorded exclusions (12.1.2.13) and its
`.md` lines are the maintainer's own, so both are open by 5.3.5
(11.2.5.14). No options are recorded. Files:
`python/reformat_whitelist.txt`, `python/test_posix.py`,
`python/seed/provider_script.json`, `ts/worker_ai.ts`,
`python/devtools.py`, `python/test_browser.py`.

4.7.15 The 55 byte SHA-256 padding boundary is untested, since no digest
may be recalled from memory. Options: a) the maintainer copies the entry
`Len = 440` of the NIST CAVP file `SHA256ShortMsg.rsp` into a test
`test_padding_boundary`; b) `python/vectors_make.py` emits a `hashlib`
digest of a 55 byte message for the test to read. Files: `ts/utility.ts`,
`ts/test_utility.ts`, `python/vectors_make.py`.

4.8 The maintainer's answers and approved items. This section holds what the
maintainer decided in answer to the earlier jobs, the class B items the
maintainer approved, the questions of the earlier job's plan, answered or
still open with one option built, that job's requirement classes, the other
class B items of the records, and the coordinators' decisions that concern
the whole job rather than one area. Every item here is decided for the
review, and the form it gives the code is not a finding, but for a class A
item of 4.8.5.3 that no answer accepted, which is a candidate (5.1.2). A
class B item is a requirement modified with cause and not confirmed by the
maintainer; it stands as built until the maintainer answers. A class C
item is one the maintainer confirmed withdrawn or modified. A built option
stands for the review; the maintainer may still choose another, and the
other options are listed so that a later answer can be placed.

4.8.1 The maintainer's answers, in time order. The messages are quoted whole
in 4.1.

4.8.1.1 2026-10-19 at 20:51 (4.1.1), the maintainer's feedback and a
reviewer's, which the coordinator decided on that evening, the decisions
then reworked by the later answers:
- sizes: the first sizes, at most 10 MiB per blob, 10 MiB for a line and
  its blobs together and 100 MiB held by any JSLB queue, were built and are
  replaced by the one blob window of 4.8.1.7;
- the soft limit: 1 GiB for all the databases together, measured by
  heuristics, the setting `db_soft_bytes` 1073741824, which refuses
  nothing; the number of databases is not limited;
- the database administration commands, so that the AI learns when and how
  to compact the set of databases it operates: designed that evening and
  built by the next answer;
- protections removed: no substrate refuses any write; the authorizer
  refusals of `_` tables and of `_settings` in `python/substrate.py` are
  deleted, `ts/substrate.ts` gets none, and the default D19 (4.4) is
  withdrawn in full, with the fixed schemas of `_files` and `_preferences`
  not enforced; the tests proving a refusal are deleted, the names
  `engine_kv.settings_refused` and `engine_turn.settings_refused` go, and
  `python/seed/prompt.json` loses its sentence on refused writes; the
  plan's "`_settings` is written by the server and never by the browser"
  stays as a description of behaviour, with no enforcement;
- "just use the real TAP api": read with the next answer as code following
  tappy's APIs;
- verbose level 2 is built, and the function that runs commands is
  `verbose.exec(level, argv, argv_verbose) -> int`, the maintainer's name:
  level 2 runs `argv_verbose`, the caller's command line with that
  program's own verbose flags; `verbose.call_run` and `verbose.call_exit`
  became `verbose.exec_run` and `verbose.exec_exit`; the console passes
  `["/bin/dash", "-v"]` as `argv_verbose`; ruff runs its default rules
  only, so the name `exec` raises no lint rule;
- the reviewer's items: no invented timer value (4.8.1.2), every new source
  file in the reformat whitelist, `i18n/en-US.json` assembled from the
  fragments, the fallbacks and "just in case" code removed, the one and
  three word names renamed, an `echo` main loop written and the old
  design's wire test replaced.

4.8.1.2 2026-10-19 at about 21:01 (4.1.2), answering the four questions the
coordinator had put that evening (the unit of "MB", whether to build the
administration design now, the reading of the TAP request, the timer
lengths):
- MB is MiB, always; KB is KiB and GB GiB;
- the database administration design is built with its code; "MVC" was read
  as the design's minimal code, a question still open with it built (4.8.4);
- TAP is custom code following tappy's APIs, implementing only what the
  engine needs: a Python producer, a TypeScript producer and a Python
  consumer, in modules named `tap_producer` and `tap_consumer`, with tests
  of their own that run before every other test, first in
  `python/test_all.py` and first in `ts/test_all.ts`;
- a test can declare that a suite must fail in a stated way, and passes when
  it fails exactly so, so that the producers are exercised on every way a
  run can fail; this replaced the nested fixture run of
  `python/test_all.py --nested`;
- tappy is not downloaded; compatibility with it is tested later;
- every timer is a named constant holding a sane default, whose one line
  comment says it is a default chosen by its writer; the 120 s lengths
  already written stay as such defaults; the provider request uses
  `provider.timeout_seconds` and `console_run` its `timeout_seconds`
  argument.
These superseded the coordinator's decisions of that evening on the unit,
on designing the administration commands without building them, on holding
TAP, and on timers that raise until the maintainer sets a value.

4.8.1.3 2026-10-20 (4.1.12, 4.1.13), the answers to the "3 questions":
- async setup: system initialization need not abide by the rules for how
  the system is used unless it is reasonably convenient; the worker's
  initialization (`sqlite3InitModule`, `installOpfsSAHPoolVfs` and its
  capacity, the OPFS directory, the file handles and
  `createSyncAccessHandle` for the cache slots) uses promises directly in
  one module that the synchronization audit exempts by name; no platform
  port is built in `ts/queue.ts`, which withdrew the coordinator's decision
  to build one; once initialization has handed the objects over, the system
  runs under the one synchronization tool as before;
- the permission-marked tools: a refusal between the AI API and the
  databases that was never a requirement violates the API agreement between
  them, and trashed databases are part of developing the AI API; so
  `source_put` and `system_restart` are not permit tools, the AI calls them
  without asking over the line and over stdio, the stdio refusal of a
  permit tool is removed, and the permit set is `console_run` alone, which
  gates the host's shell, not a database;
- both rules went into the project rules;
- the third question, the `wire.ts` timers, has no recorded answer; the
  waits of `ts/wire.ts` (`token_seconds`, `open_seconds`, `hello_seconds`,
  `drain_seconds`) are each 120 s, "a default kept from the earlier code",
  under the timer answer of 4.8.1.2.

4.8.1.4 2026-10-20 (4.1.14):
- unintentional invisibility is always a bug, not a style issue, a rule of
  the project rules; the console and overlays of `#debug` under the fixed
  `#image` were such a bug;
- unfinished code or edits go to another agent;
- the `DATA/` directory, an obsolete planning tool, is deleted;
- provider information comes later; for now the system depends on the test
  driver, and a file to be filled out holds the information and is not
  used during testing: the coordinator's `provider.json` (4.8.7.4).

4.8.1.5 2026-10-20 (4.1.15): a formatter for `.ts`, `.js` and `.html` with
the tools at hand: `python/reformat.py` runs `prettier` 3.9.8, the one
installed tool that covers all three.

4.8.1.6 2026-10-20 at 16:01 (4.1.16, 4.1.17): the maintainer listed the
earlier postmortem's defects and class A items as requests, with new ones:
stress tests with non repetitive data, the two features never built (the
`turn_compact_tokens` estimate and the eviction of the `_files` browser
tier), a sender and a handler for `console.close`, and the blocked browser
rungs. Every request was built or recorded as class B; the class B items
were approved later (4.8.2). "the DATA dir was already deleted, just scrub
references to it" was read as: every reference to `DATA/` is removed from
the project, the job's records excepted, since they are only added to. The
review's planners read every point of a record that only disagreed with
`DATA/` as closed by its deletion.

4.8.1.7 2026-10-20 at 22:58 (4.1.3):
- "before testing" 1, 2, 3 and 5 were done: the git index of
  `python/devtools.py` fixed and five new files tracked, both by the
  maintainer's own commit `a5d08eb`; the `API/` texts of the agents of
  databases, the UI test page and the browser tracing applied (4.5); the
  formatter run twice, the second run changing nothing;
- "before testing" 4, the maintainer deciding the class B items and the
  other findings of that postmortem, was not among the steps performed:
  "assume all class B are approved" decided the class B items, and the
  other findings have no answer (4.7.14);
- "all A are fine": the class A items of that postmortem are accepted as
  recorded: the coordinator's read-only `&&` chains and pipe; agents that
  grepped names another agent held locked; an agent that held two locks at
  once; a command count given as "about 47";
- "assume all class B are approved": every class B item of that postmortem
  is approved as built (4.8.2), but four whose design was replaced:
  - the blob window: the largest blob equals the largest database; what
    Chrome supports for one large database is the limit for browser
    storage and for the administration operations that cache a database on
    the server as an image and restore it; that size is the blob window,
    every window a blob goes through has that size, and it is one
    `settings.json` entry, `blob_max`, which replaces `message_max` and
    `queue_max`; `db.snapshot` is one blob again;
  - the PowerShell scripts left the reformat whitelist so that they were
    not scanned, reversed by 4.8.1.11;
  - for now only the shell scripts have verbose levels; the server and the
    runtime have only the `debug` flag;
  - compaction uses an event counter and runs when it reaches a reasonable
    threshold, in place of an estimate sent to the AI.

4.8.1.8 2026-10-20, during the coordinator's first turn on the message of
22:58 (4.1.18), the order to execute the latest plan. The coordinator's
readings: "the latest plan" is the plan as updated by those four decisions,
written first and then built by agents, because nothing concrete may exist
ahead of the prose that describes it (rejected: updating the plans only);
the formatter run is the one run allowed beside "don't run, build or test
anything ever", because the maintainer named it (rejected: run nothing),
recorded as class B; the git index changes asked for, and the staging before
the formatter, are the project rules' one exception.

4.8.1.9 2026-10-21 at 10:59 (4.1.4):
- "i aprove the above B class calls" approved the class B items of 4.8.3,
  read as those the coordinator's messages had named since its first turn
  on the order of 4.8.1.8 (rejected: the last message's two items alone;
  every class B item of the run, some never shown to the maintainer);
- two categories of test suite, `smoke-test` and `normal-test`: by default
  the runner runs the important suites that fit in 2 minutes, labelled
  `smoke-test`, and only them when asked for the smoke-test suites; an
  option runs the smoke-test suites and those labelled `normal-test`;
- "schedule this now" was read as planned and built in that run, before
  the audit, the formatter run and the stop (rejected: written into the
  plan only);
- the script the message names was built as a new top level shell script,
  the one entry point that runs the suites by category, since the
  maintainer's identifier overrides; the next message renamed it;
- "fit in 2 minutes" is a measurement that nothing could make before the
  testing phase, so every label is assigned by the plan and Unconfirmed
  until the testing phase measures it, recorded as class B.

4.8.1.10 2026-10-21 at 11:09 (4.1.5):
- `powershell/test_powershell.ps1` calls `python/test_all.py` inside WSL;
- the script of 4.8.1.9 is `test_posix.sh`, and it calls
  `python/test_all.py`;
- `powershell/test_powershell.ps1` and `test_posix.sh` are the two official
  test targets of the whole project: the first runs on Windows, the second
  will later run in Docker; the Docker run was designed and not built;
- both targets call `python/test_all.py`, so the categories reach it from
  both;
- the project rules were updated, the maintainer's own bullet of that
  morning renamed and the targets' bullet added; "the doc" was read as the
  two planning documents (rejected: `README.md`, which lists only the user
  facing scripts);
- `python/test_posix.py`, the checker of the whitelisted files, and
  `test_posix.sh` share a stem; both names are the maintainer's.

4.8.1.11 2026-10-21 at 11:30 (4.1.6):
- `powershell/test_powershell.ps1` stops on failure: the first failed step
  ends the run with a failing exit code and no later step runs, the last
  stop among them, so the lifecycle's state at the failure is left as it
  is; this answered the plan's question on it (4.8.4.30) and rejected the
  cleanup stop and the tally;
- the PowerShell reformatting comes back: the six whitelist lines
  `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1`,
  `powershell/*.ps1` and `powershell/en-US/*.psd1` return;
- the byte order mark joins the allow list (4.8.4.38), with "whatever is
  needed", which the earlier job recorded as not met for the banner of
  4.8.4.39; the PowerShell files pass only the comment check and the
  character check of
  `python/test_posix.py`, which needs a PowerShell comment lexer again,
  written anew from the plan with its tests first, not recovered from git
  (rejected: restoring the removed functions from the last commit);
- the table of file extension to formatter and scanners is data, read by
  the code (rejected: the comment lexers alone);
- except PowerShell: the PowerShell scripts format the PowerShell files on
  Windows, reading the whitelist on their own; Linux formats the rest, and
  the Python table has no PowerShell formatter.

4.8.1.12 2026-10-21 at 11:58 (4.1.7):
- the option is `--normal-test`, as built; options are taken by their full
  names and abbreviations such as `--normal` are refused (rejected: an
  abbreviation beside the full name); class C;
- `python/test_test_all.py` is renamed `python/test_test.py`, which tests
  only the infrastructure for testing, not the test driver: `TestModules`,
  the tests of the driver's own table `_MODULES`, goes; `alarm_plan`, the
  deadline of a suite and of a smoke-test run, is infrastructure and moves
  out of the driver, so `TestAlarm` stays and no longer imports the driver
  (rejected: `TestAlarm` removed, which loses the only proof of the 120 s
  deadline; `alarm_plan` left in the driver and tested there);
- `python/test_all.py` lists `test_test` and no test of itself; class C;
- the project rules and the two plans explain the distinction between the
  infrastructure for testing and the test driver.

4.8.1.13 2026-10-21 at 12:24 (4.1.19): the maintainer committed the unstaged
changes as `a5d08eb`; the commit is the maintainer's and the run committed
nothing. "so you can track the next round" was read as: the next round, the
audit's follow up edits and the formatter run, is left as changes against
`a5d08eb` for the maintainer's review, the follow up's whitelisted files
staged before the formatter so that its changes stay unstaged and apart
(rejected: a commit by the run).

4.8.1.14 2026-10-21 at 15:13 (4.1.20, 4.1.21): the review's mandate, which
section 1 carries: judgement calls of the planning agents and the
maintainer are not revisited, every assumption the AI made is accepted for
the review, and this file references nothing outside itself but the project
rules.

4.8.2 The class B items approved on 2026-10-20 at 22:58. They are
requirements as built, class C since; the plan text that said the opposite
was changed to state the built behaviour, and so was `API/ts/agent.d.ts`.
- The scripted provider's Script stays at `/_files/provider/script.json`;
  the server seeds that `_files` row from `python/seed/provider_script.json`
  when it is missing; the seeded Script has one node and no replies, so
  input on a root without a test driver faults.
- A tool call turn is stored with its results, after the tools run, unlike
  the plan's first design and the first `API/ts/agent.d.ts`.
- Python stores doubles above 2^53, which the TypeScript store refuses with
  `substrate.integer_range`.
- The test vectors go to `build/vectors`, not `python/vectors/`; the empty
  `python/vectors/` is left for the maintainer.
- A crash before the server's log opens, from the arguments, raw mode, the
  engine lock or the settings, reaches only the terminal.
- With both shown, the overlay below the console scrolls the console's top
  rows out; the subtitle band lies over the bottom strip of the fixed
  image.
- The page replay compares the browser's copy of a database with the
  server's, not through `test_wire`'s private reader.
- Seven files under the job's record directory still mention `DATA/`, and
  `constants.recorded_png` is probably the deleted `DATA/` PNG.
- The stress test runs `_STRESS_ROUNDS`, 8 rounds, a count chosen by its
  writer; the echo rungs keep the 251 byte period pattern, not non
  repetitive data.
- `ConsoleView.close_request` exists and no UI action calls it.
- The drain rungs stall ttyd with SIGSTOP; the drain timer rung posts a
  burst sized from the queue bound, 11 lines then, the bound now
  `blob_max`; the drain poll rung sleeps 5 s, then checks the poll once.
- `rung_console_reopen` runs open, exit, open: `exit_done` returns the
  console view to idle, and ctrl-0 on an idle view sends `console.open`
  again, so the console reopens without a page load.
- `rung_http_timeout` writes its own `provider.json` into its own root,
  sets `provider.scripted` false there and points `base_url` at a local
  stub, a departure from "not used during testing".
- A test engine page outside the production bundle, the coordinator's
  design: the rung submits UI `kv.put` and `sql.run` to the AI store
  through it (4.5.25).
- The largest put is measured in the start state it is used in.
- `rung_ui_upload` expected `worker_ai.queue_over` after about 11 of its 15
  puts; under the blob window its 135 MiB fits `blob_max`, so its
  expectation changes.
- Only synchronous network loads are detected, under three candidate Chrome
  event names.
- `test_wal_left` cannot apply to the SAH pool, which has no WAL, and
  nothing is built for it.

4.8.3 The class B items approved on 2026-10-21 at 10:59, class C since; the
plan text that said the opposite was changed:
- the step script of `ts/test_substrate.ts`, a measured SHA-256 vector that
  is never run, keeps the text `engine.log(1, ...)`;
- `chunk_bytes` and `srv_buf_size` stay 1 MiB and are not windows (the
  answer to 4.8.4.10);
- nothing gates `db_load`, so `db_load` calls whose images, held at once,
  pass `blob_max` fault with `queue.queue_over` (4.8.4.12);
- the worker's export for the UI's `db.snapshot` stays
  `sqlite3_js_db_export`, through the wasm heap (4.8.4.11);
- a UI put of `blob_max` + 1 is refused first by the AI worker's task queue
  with `queue.queue_over`, not by `wire.ts` with `wire.blobs_over`;
- `rung_decoder` writes the value of `blob_max` + 1 bytes on the server,
  behind the page's back, with `substrate.Store.kv_put` and a file path,
  before the page's `kv.get`, since no port can carry it.
Not approved by that message, and still class B: the value of `blob_max`
(4.8.4.8); a forwarded `turn.append` that never compacts (4.8.6.2); the
formatter run read as the one run (4.8.1.8); the reading of the "shell
scripts" (4.8.4.18). The verbose line before the settings stays an open
question (4.7.13).

4.8.4 The plan's questions, each answered or with an option built. Each
gives the question, the option in force, and the others. An item marked
Answered, or one that names the maintainer's answer or request, is closed.
Every other item stays open for the maintainer, the banner of 4.8.4.39
first, since it stops every run: its built option stands for the review,
which keeps it (5.1), answers none of them and files nothing against them;
its other options are not rejected but open; and an agent whose area holds
the question lists it among the open questions met (10.3.10) and changes
nothing.

4.8.4.1 The TAP module layout. Built: `python/tap_producer.py`,
`python/tap_consumer.py`, `ts/tap_producer.ts`, read from "tap-producer/
tap_producer tap-consumer/tap_consumer" because a hyphen is not legal in a
Python module or a TypeScript namespace name; `ts/unittest.ts` stays the
TestCase harness. Others: directories `tap-producer/` and `tap-consumer/`;
another layout.

4.8.4.2 The TAP line grammar. Built: D12, the plan line first with bare
names (4.4). Others: tappy's default output, with a `# TAP results for`
header and the plan last; the earlier writers' `# Subtest` grammar.

4.8.4.3 "MVC" in "the db admin design/MVC". Built: the minimal code of the
design. Others: a model, view and controller split; something else.

4.8.4.4 The form of verbose level 2. Built: a full `argv_verbose`. Others:
flags inserted after `argv[0]`, wrong for a wrapper such as
`python3 script.py`; flags appended, wrong where options come before
operands.

4.8.4.5 The console after `console.exit`. Built, at the maintainer's
request: reopenable from ctrl-0 (4.8.2). Other: closed until the next page
load.

4.8.4.6 The one size entry. Built: `blob_max`, kept. Other: a new name, such
as `window_bytes` or `db_max`.

4.8.4.7 What a window counts. Built: blob bytes only, the `s` of each blob a
message or a queue holds; a line is bounded by `line_max`. Other: line and
blob bytes, so that the largest blob is `blob_max` minus its line and a
`kv.get` reply can exceed the `kv.put` that stored it.

4.8.4.8 The value of `blob_max`. Built: 2147483391, SQLite's documented
allocation bound, until the rung `rung_blob_max` measures Chrome; class B,
not a measurement, and not approved. Others: the measured value once
measured; a value the maintainer names.

4.8.4.9 "caching to server as an image/restoring admin operations". Built:
`db_unload` drops the browser's copy, the server's replicated copy is the
image, and `db_load` restores it. Other: `db_unload` first sends the
browser's file to the server as one blob, on a new line.

4.8.4.10 The settings that are not windows. Answered on 2026-10-21 at 10:59:
`line_max`, `overflow_bytes`, `db_soft_bytes`, `files_browser_bytes`,
`media_db_bytes`, `chunk_bytes` and `srv_buf_size` keep their own values.
Others: `chunk_bytes` and `srv_buf_size` become `blob_max`; others the
maintainer names.

4.8.4.11 The worker's export for the UI's `db.snapshot`. Answered on
2026-10-21 at 10:59: `sqlite3_js_db_export` through the wasm heap, its limit
measured. Others: the pool's `exportFile`, bounded by V8 and not the heap;
sqlite3.wasm rebuilt with a `MAXIMUM_MEMORY` of 4 GiB.

4.8.4.12 Several `db_load` calls at once. Answered on 2026-10-21 at 10:59: a
loud `queue.queue_over` when their images held at once pass `blob_max`.
Others: one load at a time, later calls waiting; a blob streamed to a cache
file counting nothing in the queues.

4.8.4.13 The `hello`'s line bound before the settings are known. Built:
10485760, the constant of D24 (4.4). Others: 1048576, the `line_max` of
`settings.json`, as a constant; the value of `blob_max`, as a constant.

4.8.4.14 A database grown past `blob_max` in the browser. Built: nothing
refuses it, and its image fails loud at a window. Other:
`PRAGMA max_page_count` bounds every database at `blob_max`.

4.8.4.15 The size of the plan's large proofs. Built: a blob of `blob_max`,
one byte more refused; 128 MiB as one message. Others: the earlier 16 MiB
and 128 MiB, with the edge proved only by the decoders' unit tests; the
edge proved on roots whose settings set a smaller `blob_max`, and the
shipped value by `rung_blob_max` alone.

4.8.4.16 `powershell/en-US/*.psd1`. Built until 2026-10-21 at 11:30: it left
the whitelist with the scripts. Since then: it is back in the whitelist with
the scripts, with the byte order mark handling and a PowerShell lexer, which
the other option described.

4.8.4.17 `python/test_test_posix.py`. Built: kept, with
`test_others_refused` for `.py` and `.ts`; since 2026-10-21 at 11:30 it also
holds the PowerShell tests again, written anew. Other: deleted whole, with
its line in `python/test_all.py`.

4.8.4.18 The "shell scripts" that keep verbose levels. Built: the console's
dash through `verbose.exec`, and the `.sh` door scripts when they are built;
`test_posix.sh` has no verbose level. Others: the PowerShell admin scripts,
which would gain levels; `test_posix.sh` taking the shell's level, from
`verbose_level` or an option, and writing its start and exit at levels 1
and 2 as `verbose.exec` does; every `.sh` file of the project; another set
the maintainer names. Class B, not approved; the earlier job noted that the
reason given for leaving `.sh` files out, that `archive.sh` and `clean.sh`
lie outside the project, does not hold for `test_posix.sh`.

4.8.4.19 The settings `verbose_level`, `verbose_ring` and `verbose_forward`.
Built: `verbose_level` kept for the console alone, `verbose_ring` kept,
`verbose_forward` removed. Others: `verbose_level` renamed, such as
`shell_level`; `verbose_forward` kept as a flag beside `debug`;
`verbose_level` removed and dash run at a fixed level.

4.8.4.20 Shell level 1. Built: the output passed through, the start and the
exit logged, since a captured level 1 gives dash no input. Other: the output
captured and formatted as Markdown progress.

4.8.4.21 The server's trace in debug mode. Built: header JSON only, the
strings `bootstrap.hello_submit`, `main_loop.line_dispatch` and
`main_loop.line_reply`. Others: the whole line in the plan's form; no trace.

4.8.4.22 The runtime with only `debug`. Built: lines without levels, the
queue's trace and the forwarding in debug mode only, the `verbose_level`
tool removed, `script_debug` a traced run; failures are always logged.
Others: the same with the `verbose_level` tool kept to switch `debug`; no
verbose lines outside debug mode at all.

4.8.4.23 The events compaction counts. Built: every turn appended to the
scene, of any role. Others: the player's turns, `ai.say` and `ai.click`;
provider requests.

4.8.4.24 Where the counter is kept. Built: the count of the scene's `_turn`
rows, counted when read. Others: a counter row per scene in `_meta`; a KV
row per scene.

4.8.4.25 Where and when compaction runs. Built: in the browser's substrate,
before a `user` turn is appended to a scene at the threshold, compacting in
the same transaction and forwarding `turn.compact` before `turn.append`.
Other: in `agent.ts`, at the end of each turn.

4.8.4.26 What compaction keeps. Built: every turn compacted, the summary a
fixed `i18n` text naming them. Others: the last assistant reply's text as
the summary; the latest player turn kept whole; a summary written by the
provider.

4.8.4.27 The compaction threshold. Built: the setting `turn_compact_turns`,
64. Others: the same setting with another default; a named constant.

4.8.4.28 The grain of a test suite's label. Built: a module of
`python/test_all.py`, a rung of the wire and browser tests with its stage or
root labelled too, `python/test_posix.py` whole, and the TypeScript modules
under the rung that runs them. Others: each runner whole; each root or
stage, the roots split so that each holds one label; as built, with each
TypeScript module labelled too, designed and not built.

4.8.4.29 The smoke-test suites. Built: the unit suites of both languages,
`python/test_posix.py`, the wire test without its 2 GiB and 128 MiB echoes,
and the browser roots "suites" (its first two rungs) and "fresh". Others:
the unit suites and `python/test_posix.py` only; more browser roots that the
maintainer names once the testing phase has measured them.

4.8.4.30 `powershell/test_powershell.ps1` after a failed step. Answered on
2026-10-21 at 11:30, class C: it stops at the first failed step with no
cleanup. Rejected: it stops, runs `xsjs_stop.ps1` as a cleanup and exits 1
naming the step, built until then; it carries on and tallies the failed
steps, as the maintainer first wrote it.

4.8.4.31 The 2 minutes. Built: a smoke-test run fails loud the moment it
passes 120 s, with each suite's seconds printed. Others: it fails at its
end, when its total passed 120 s; there is no limit and the seconds are
printed for the maintainer.

4.8.4.32 Options and defaults. Built: each target takes `--smoke-test` or
`--normal-test` and passes it on, and every runner defaults to
`--smoke-test`; `--failfast` does not pass through the targets. Others: a
runner run alone runs every suite; the targets pass every argument through
to `python/test_all.py`, `--failfast` included.

4.8.4.33 `python/test_posix.py` rewrites the whitelisted files in every
smoke-test run. Built: as it is. Others: it checks the formatting and
rewrites nothing; it becomes `normal-test`.

4.8.4.34 When `powershell/test_powershell.ps1` runs `python/test_all.py`.
Built: after the status check that follows `xsjs_install.ps1`, before the
first start. Others: after the whole lifecycle; before the lint step.

4.8.4.35 Where `python/test_all.py` runs from Windows. Built: in place,
`wsl --cd` of the Windows checkout, `/mnt/c/src`, with its roots under
`build/` there. Other: a copy of the checkout in the Linux file system.

4.8.4.36 Tests of the two targets. Built: none; the testing phase proves
them by running them. Others: a Python test that runs `test_posix.sh` with
bash on a copy beside stub runners, with the maintainer's approval for
Python running bash; a shell test script.

4.8.4.37 The project rules file's name in the maintainer's messages of 11:09
and 11:58. Built: the name elided from the copies (4.1). Others: the copy
verbatim, the name included; the message left out.

4.8.4.38 Where the UTF-8 byte order mark is allowed. Built: at the start of
a file of a `.ps1` or `.psd1` row only, by the row's codec `utf-8-sig`;
anywhere else, and in every other file, U+FEFF is refused; it is not added
to `_NON_ASCII_ALLOWED`. Others: U+FEFF added to `_NON_ASCII_ALLOWED`,
allowed anywhere in every whitelisted file, as the words read, which
reverses `test_others_refused`; allowed at the start of any whitelisted
file, every file read as `utf-8-sig`; as built, and required at the start of
every PowerShell file, so that `xsjs_status.ps1`, `xsjs_stop.ps1` and
`powershell/test_lint.ps1` fail until they gain one (4.7.1).

4.8.4.39 The banner characters of `xsjs_install.ps1`, U+2588 and U+2591 to
U+2593 of its figlet banner, the maintainer's content. Built: nothing more
is allowed, so `python/test_posix.py` stops at `xsjs_install.ps1:41:19` on
every run, the smoke-test run included, until the maintainer answers; the
earlier job asked for this answer first, since it stops every run, and
recorded that "whatever is needed" is not met for the banner. Others: the
four join `_NON_ASCII_ALLOWED`, for every file; the four are allowed in the
PowerShell rows only, by a sixth key of the table; the maintainer redraws
the banner in ASCII; the script builds the banner from `[char]0x2588` and
the others at run time.

4.8.4.40 Where the table of extensions lives. Built:
`python/reformat_table.json`, read by `reformat.table_read`, which
`python/test_posix.py` calls; it maps each extension to its comment lexer,
encoding, formatter, linter and system, and it is data, not whitelisted, as
`settings.json` is not. Others: a constant in `python/reformat.py`, its rows
plain tuples; a shared module `python/file_types.py`.

4.8.4.41 How `powershell/test_lint.ps1` chooses the PowerShell files. Built:
the whitelisted files whose extension is in its own list, `.ps1` and
`.psd1`, kept equal to the table's `windows` rows by hand. Others: it reads
`python/reformat_table.json` too and takes the extensions of its `windows`
rows, failing loud on a whitelisted file of no row as Linux does; every
whitelisted file whose extension is not of a `linux` row.

4.8.4.42 The whitelist's matching rule. Built: one rule, enforced by both
scripts: wildcards in the last part only, no brackets or backticks, case
sensitive names, Python's rule for names starting with `.`, and a match that
is not a file refused. Others: `python/reformat.py` keeps `glob.glob` and
`powershell/test_lint.ps1` alone refuses the lines it cannot match the same
way; the whitelist names files only, without wildcards.

4.8.4.43 First failure in `powershell/test_lint.ps1`. Built: the CRLF check
and PSScriptAnalyzer stop at the first file with a fault. Other: every
file's CRLF faults and analyzer results printed before the exit.

4.8.4.44 Abbreviated options. Answered on 2026-10-21 at 11:58, class C: the
full names only; `python/test_all.py` and the parser of the tests refuse
`--normal` and `--fail`. Others: abbreviations kept, with the test's input
changed to one that is no prefix; `options_add` turning abbreviations off
for all three runners, so that `python/test_wire.py` and
`python/test_browser.py` run alone refuse `--normal` too, designed, not
built, and passed over by that answer.

4.8.4.45 The driver listing its own test module. Answered on 2026-10-21 at
11:58, class C: no test of `python/test_all.py`; its table lists
`test_test`, which tests the infrastructure. Others: the table lists
`test_test_all`, built until then; that module run outside the table.

4.8.4.46 Where `alarm_plan` lives. Built: `python/category.py`, beside the
120 s and `limit_seconds`. Others: a new module of the infrastructure, such
as `python/deadline.py`, with its stub; as built, with `timer_start` and
`timer_stop` moved into `python/category.py` too.

4.8.4.47 The test modules of the infrastructure for testing. Built:
`python/test_test.py` holds every test of `python/category.py`, and
`python/test_category.py` is joined into it; the TAP modules keep their own
tests. Others: `python/test_category.py` kept, with `python/test_test.py`
holding `TestAlarm` alone; as built, with the tests of `tap_producer` and
`tap_consumer` joined too and `test_test` then run first.

4.8.4.48 A smoke-test run ends at its first failure. Built, by the
coordinator's choice: any failure ends a `smoke-test` run, the deadline's
among them. Others: only the deadline ends it at once, other failures
running the module out as a `normal-test` run does; every run ends at its
first failure, as the first failure rule asks.

4.8.5 The earlier job's requirement classes.

4.8.5.1 Class C, confirmed withdrawn or modified by the maintainer: the
plan's stage order, set aside by "write everything first and stop before
testing"; the database protections, D19 and the PRAGMA allow list,
withdrawn; downloading tappy, withdrawn; the bespoke TAP runner, replaced by
the custom modules shaped on tappy; the invented timer values, replaced by
sane defaults; "MB" fixed as MiB; the database administration design, built
rather than left as a door; D6 and D14 settled (4.4); the class A items of
the first later round, accepted; the sizes of 10 MiB per blob and per
message and 100 MiB per queue, superseded by `blob_max`; the `db.chunk`
pieces, removed (4.5.23); the PowerShell files out of the whitelist and
unscanned, withdrawn and then reversed, scanned for their comments and
characters only; verbose levels in the server and the runtime, deferred
"for now"; the compaction estimate sent to the AI, with bytes counted as
tokens and the AI deciding, replaced by the counter; the approved items
of 4.8.2 and 4.8.3; the name `test_all.sh`, replaced by `test_posix.sh`; the
answers of 4.8.4.30, 4.8.4.44 and 4.8.4.45; `test_posix.sh` in Docker,
later by the maintainer's words, designed and not built; `TestModules`,
removed, its design kept in the plan.

4.8.5.2 Class B, modified with cause and not confirmed, each with its state:
- the defaults D1 to D31: in force as written (4.4), the question on them
  open (4.7.11);
- the API additions and departures: stay as built (4.5);
- the reading of "MVC" (4.8.4.3), of the TAP module names (4.8.4.1) and of
  verbose level 2 (4.8.4.4): built;
- tappy's names, followed as recalled from tappy's documentation and to be
  checked against tappy when it is tested: the producer's `TAPTestRunner`,
  a `unittest.TextTestRunner` with the setters the engine needs such as
  `set_stream`, and `Tracker` with `add_ok`, `add_not_ok`, `add_skip`,
  `set_plan` and `generate_tap_reports`; the consumer's `Parser` with
  `parse_text` and `parse_line`, yielding the line kinds `Result`, `Plan`,
  `Diagnostic`, `Bail`, `Version` and `Unknown`; and the stats the plan asks
  of the consumer: plan, pass, fail, skip, and whether the stream is well
  formed. The TypeScript producer uses the same names inside the namespace
  `tap_producer`. The code departs from these names where 4.5.34 says;
- the update of the Lookup Accelerator: held (4.7.9);
- the questions found while writing the code: open (4.7.1 to 4.7.8);
- the value of `blob_max`: documented, not measured, Unconfirmed until
  `rung_blob_max` (4.8.4.8);
- the readings behind the questions of 4.8.4.6 to 4.8.4.27 (the window, the
  verbose levels, compaction), of 4.8.4.28 to 4.8.4.37 (the labels, the
  options, the targets) and of 4.8.4.38 to 4.8.4.47 (the PowerShell files,
  the table, the infrastructure for testing): built, and reworked if an
  answer differs;
- every label and the fit in 2 minutes: Unconfirmed until the testing
  phase measures them; the run reports each suite's seconds and fails loud
  past 120 s;
- the copies of two messages with the project rules file's name elided
  (4.8.4.37);
- the byte order mark through the codec (4.8.4.38) and the banner
  (4.8.4.39), both unanswered.

4.8.5.3 Class A, unsatisfied or modified without cause, each with its
state:
- agents ran read-only commands their instructions forbid, `cd`, `head`,
  `awk`, `sed`, `echo`, `tr`, `sort` and shell loops, in every session:
  the coordinator could forbid and record them but not remove the shell
  from an agent; the question is open (4.7.10);
- the job's record was once edited, not appended: it cannot be undone, it is
  recorded, and the records have been only appended since;
- the review's class A items: the reformat whitelist, the strings file, the
  remaining fallbacks (`log_close` on a closed log, the unreachable
  `return 0`, the flushes before `execv`), the names `Loopback`, `Recorder`
  and `json_media_is`, the `echo` handler and the old wire test still run.
  Each went to a later step of the job, and the records show those steps
  done: the whitelist brought up to date, `i18n/en-US.json` merged,
  `log_close` on a closed log raising `verbose.not_open`, the flushes
  before `os.execv` and their test removed, the three names renamed,
  `python/echo_loop.py` written and `python/test_wire.py` rewritten. The
  unreachable `return 0` went with the order for `python/test_all.py`,
  which has been rewritten since, and no record says it was removed. The
  level 0 flushes of `verbose.exec` were kept as ordered, a class B item
  (4.8.6.1).
- the earlier postmortem's class A items, which the maintainer then listed
  as requests (4.8.1.6): the edits made without a lock suffix, the
  forbidden commands, verbose level 2, the replay rungs left blocked, and
  the plan's parts not executed (the `turn_compact` estimate, the `_files`
  eviction, the exercises of the scripted turn); each was built or recorded
  as class B in the next round, and the class A items of that round were
  accepted by "all A are fine".

4.8.6 The other class B items of the records, which the plan did not carry
as such; each stands as built until the maintainer answers.

4.8.6.1 From the end of the job of 2026-10-19 to 20, each with its state:
- a reply could exceed the per message size and snapshots over 10 MiB
  could not be sent: superseded by the blob window;
- the browser's pool of 16 spare databases and its 256 cache slots are fixed
  at initialization, because promises are confined to initialization;
  options recorded: a platform port for run time growth, larger constants;
  unconfirmed, the fixed `CacheFiles` slots and pool stand;
- level 2 logged its output instead of passing it through raw: superseded,
  `exec` passes output through at every level and level 2 runs
  `argv_verbose`;
- the byte order mark conflict and `API/sql/*.sql` out of the whitelist:
  the mark is handled by the codec (4.8.4.38); the whitelist still misses
  older JSON, SQL, TOML and tsconfig files, `html/engine.css` and
  `python/seed/provider_script.json`, and `test_posix.comments_find` has no
  lexer for `.css`, `.json`, `.sql` or `.toml`; unconfirmed;
- the level 0 flushes of `verbose.exec`, kept because their order asked for
  them: unconfirmed;
- the TAP modules: the module name reading (4.8.4.1), the code's departures
  from tappy's names in the stubs, two TAP documents in `typescript.tap`,
  a constant failfast: unconfirmed;
- the "MVC" reading (4.8.4.3), and the plan contradicting itself on who
  compacts turns: superseded by the counter, which compacts by itself in
  the substrate (4.8.4.25);
- `provider.json`, a coordinator default (4.8.7.4), with scripted requests
  carrying `model: ""` from an empty provider information: unconfirmed;
- the formatter: prettier would rewrite `python/bootstrap.html`, held by
  D22 (4.4), and the maintainer's `API/ts/*.d.ts`, both matched by
  whitelist lines; Node's compile cache lands in the system's temporary
  directory, outside the tree; prettier reports every unparsable file and
  exits 2 at the end, not at the first failure; unconfirmed; the record of
  the formatter run of 2026-10-21 lists "three lines of
  `python/bootstrap.html`" among the lines over 79 columns after it;
- the rule text of the system initialization answer gained an example the
  maintainer did not write, "such as the one synchronization tool and its
  audit"; it stands in the project rules: unconfirmed;
- `#debug` and `#subtitle` gained `background: black` in
  `html/engine.css`, a colour motivated only by the invisibility rule:
  unconfirmed;
- every default and every API addition awaiting acceptance: 4.4 and 4.5.

4.8.6.2 From the job's last round, 2026-10-21, unresolved, each unconfirmed:
- the formatter run read as the one run allowed (4.8.1.8);
- the "shell scripts" read as the console's dash (4.8.4.18);
- `blob_max` 2147483391, SQLite's documented bound, not a measurement
  (4.8.4.8);
- a forwarded `turn.append` applied by `operation_apply` goes through the
  private `#turn_add` and never compacts, so one forwarded line cannot
  compact twice; in `ts/substrate.ts`;
- the "level" root of `python/test_browser.py` is
  `{"debug": True, "verbose_level": 2}`, one root for the debug rungs and
  the console rungs, not two;
- "the above B class calls" read as the items of 4.8.3 (4.8.1.9);
- every label, and the browser smoke set of two roots, chosen without a
  measurement (4.8.4.29);
- the project rules file's name elided in the copies (4.8.4.37);
- the two targets take only `--smoke-test` and `--normal-test` (4.8.4.32);
- the byte order mark through the codec (4.8.4.38);
- the banner of `xsjs_install.ps1` not handled (4.8.4.39);
- the infrastructure for testing read as `python/category.py` and the TAP
  modules, `alarm_plan` moved into `python/category.py`, and
  `python/test_category.py` joined into `python/test_test.py` (4.8.4.46,
  4.8.4.47);
- a smoke-test run ends at its first failure of any kind (4.8.4.48);
- the old name `powershell_double_scan` left inside a replaced design kept
  in the plans, which no longer exist;
- the logged readings of 4.8.1.9 to 4.8.1.13: scheduling means planned and
  built in that run; `test_all.sh` a new script, then renamed; "the doc"
  and "the docs" are the two plans, not `README.md`; one table for
  formatters and scanners; the PowerShell lexer written anew; `alarm_plan`
  is infrastructure; the next round left as changes against `a5d08eb`.

4.8.7 The coordinators' decisions and other deciding records that concern
the whole job.

4.8.7.1 The first job's standing decisions, carried to the maintainer: the
server root mirrors the checkout's runtime subset (4.5.18); `i18n` covers
the engine modules' messages, not the tools; the JSLB key order, the
`sha256` field of a streamed blob and canonical JSON; the
`handlers_register` signatures of the engine modules (4.5.2); the seed file
names; the TypeScript compile order and the page build tokens; vector files
generated by `python/vectors_make.py`, written to `build/vectors` since
(4.8.2). Their details were in the agents' instructions, a document that no
longer exists. Two contracts of those instructions were replaced by the
review that followed: the seeding rule of
`metaverse`, now seeded in one transaction when its `seq` is 0, after the
`_files` script row; and the `sha256` field of a streamed blob's header,
now overwritten in place, key order `s, sha256, d`.

4.8.7.2 The owner route and the replication design, decided by the
coordinator: 4.5.5 and 4.5.17.

4.8.7.3 Long lines are left to the reformatting tool, not wrapped by hand,
under the project rule to use the reformatting tools instead of formatting
by hand; the coordinator withdrew an order to wrap 75 lines of
`python/test_browser.py` by hand when that rule arrived.

4.8.7.4 `provider.json`, a coordinator decision on the maintainer's
provider answer (4.8.1.4), a default the maintainer has not confirmed: a
file beside `settings.json` holds `base_url`, `chat_model` and
`image_model` as empty strings to be filled out; these three keys left
`settings.json`, both settings checks and the `Settings` interface, while
`provider.scripted` (true) and `provider.timeout_seconds` stay; when
`provider.scripted` is false the server reads `provider.json`, an empty
value is an error, and `hello` carries `provider_info {base_url,
chat_model, image_model}` beside `provider_key` (D8, 4.4); when it is true
the file is never read and `hello` carries no `provider_info`. Reason:
every test reads `settings.json`, so the information could not stay there
and be "not used during testing". The maintainer approved the one rung that
writes its own `provider.json` (4.8.2).

4.8.7.5 The Lookup Accelerator task is held (4.7.9): the project rules
forbid editing them without request, and the maintainer had removed the
section.

4.8.7.6 The test engine page, outside the production bundle, through which
a rung submits UI puts to the AI store: a coordinator decision, approved
(4.8.2, 4.5.25).

4.8.7.7 The coordinator of 2026-10-19 to 20 departed from its own order of
work four times, each with its reason: the browser substrate began before
the step before it ended, as every input it mirrors had landed; the wire
test was written beside the page modules, as it reads none of their files;
the whitelist was brought up to date before the strings were merged, as
its patterns cover files still to come; and the strings were merged while
the browser test was still being written, a late fragment to get a follow
up merge. It also gave the console port's side of D23 (4.4) to the task of
`ts/wire.ts`. None of these sets anything in the code.

4.9 Work the earlier job left. The job that first wrote down the
maintainer's decisions, on 2026-10-19, ended that record with its
remaining work, in order: steps 3 to 6 of its plan of work, then the
maintainer's test run. Each item below gives that work and what the later
records show of it: done, partly done with what remains, or not done. No
job ran the project's tests, builds or type checks, so "done" means
written and recorded as complete, never verified; the one run was the
formatter's (4.9.6). The gaps, readings and defects each task recorded in
its own files are its area's (section 11); they are named here only where a
later record settles them.

4.9.1 Step 3, the seams, at most six agents at a time.

4.9.1.1 The Python substrate, `python/substrate.py` and its tests: D1 (a
new database starts at `seq` 0, `db_create` leaves it 0, `db.create`
carries `since` 0 and `db.drop` the database's `seq`); an earlier review's
prescribed changes, without its PRAGMA and `_settings` items; no
authorizer refusals. Done: `db_create` leaves `seq` 0; both authorizers and
their constants deleted with the tests of their refusals; a restore written
to a temporary file and checked through a read only connection before the
live database closes; nested canonical JSON with the decoder's key rules;
the fork child ending every path in `os._exit(1)`. The stub comments it
proposed to remove went from `API/python/substrate.pyi` and
`API/sql/substrate.sql` (4.6).

4.9.1.2 `python/jslb.py`: D4 (the deferred fault, a streamed blob's file
closed on any exception, `LineDecoder.idle()`, end of input when not idle a
hard error), D5 (no `WireError.slug`; tests compare `i18n` text from a
table of arguments for each vector), D7 (the decoder accepts an integral
float for `b` and `s`), and the maintainer's first sizes. Done. The sizes
were replaced by the one blob window: the decoder is `LineDecoder(line_max,
blob_max, overflow_bytes, sink_make)`, and `jslb.message_over` is gone. The
vectors it asked the maintainer to generate are now written by
`python/test_all.py` to `build/vectors` before the decoder tests, and by
`python/page_build.py` for the test page; the empty `python/vectors/` is
left for the maintainer.

4.9.1.3 `python/verbose.py` with `exec` and level 2, D13
(`verbose.tail_get(thread, count)` serves `ui` and `ai`), the four engine
modules `python/engine_verbose.py`, `python/engine_tap.py`,
`python/engine_mcp.py` and `python/engine_system.py`, and
`python/test_i18n.py`. Done. Level 2 was then found unreachable, the
console always run at level 0 and the server never logging; the next job
made the console run `verbose.exec` at `verbose_level`, level 2 passing
dash's output through raw, and the server log. By the maintainer's later
decision only the shell has levels: the server logs its failures always
and its trace only in debug mode, and has no level of its own.

4.9.1.4 `python/dispatch.py`, `python/mcp.py`, `python/mcp_stdio.py` and
the one word test class names. Done: `Loopback` became `DirectLink` and
`Recorder` `CallRecorder`. Left: four test names of three words holding a
protocol name, `test_tools_list_shape`, `test_tools_list_permit`,
`test_call_rpc_error` and `test_call_rpc_bare`; and `python/mcp_stdio.py`
setting no `sys.pycache_prefix`, a question for the maintainer with the
options `# noqa: E402` or a launcher.

4.9.1.5 `ts/queue.ts`: `queue_max`. Done, then replaced by the one blob
window: the task queue bounds the blob bytes of the lines it holds at
`blob_max`, throwing `queue.queue_over`, and before `settings_set` it
bounds nothing.

4.9.1.6 A follow up on Python files already landed: `exec` and the message
limit in `python/bootstrap.py`; the message limit in `python/main_loop.py`;
the protections removed from `python/engine_kv.py`,
`python/engine_turn.py`, their tests and `python/test_engine_sql.py`; the
refusal sentence removed from `python/seed/prompt.json`. Done, with a
second follow up for the decoders of `python/test_engine_doc.py` and
`python/test_engine_db.py`. The message limit went with the one blob
window. Kept by that agent, as a statement about the scene and not a
database refusal: the prompt's words that the hyperposition "is the one
scene the player cannot modify".

4.9.1.7 Settings in both languages: `settings.json`, `python/settings.py`,
`ts/settings.ts` and their tests. Done. Since then the provider's
`base_url`, `chat_model` and `image_model` moved to `provider.json`;
`message_max`, `queue_max` and `verbose_forward` went; and
`turn_compact_tokens` became `turn_compact_turns`.

4.9.1.8 `error_overlay`, `utility` and `http` in TypeScript. Done: only the
first fault shown, through a page instance `error_overlay.FaultScreen`;
the `utility` messages through `i18n` and a strict `base64_decode` (D26,
those two as a default); `json_media_is` renamed `media_json`.

4.9.1.9 The Python tools `python/third_party_fetch.py`,
`python/devtools.py`, `python/page_build.py` and `python/test_posix.py`.
Done. Left for the maintainer: the three `sha256` pins of
`python/third_party_fetch.py`, empty by design so that the tool raises
until the maintainer fills them (accepted for the review), and `chmod +x
python/third_party_fetch.py`; no later record shows either done.

4.9.1.10 `ts/jslb.ts`, the twin of the Python decoder. Done, with D3
(`blob_make(data, key?, fields?, size?)`, `size` required for a cache
handle). The one blob window later took out its message limit. Its stub
additions, `idle()` and `size`, are not applied (4.6.9.2).

4.9.1.11 `ts/wire.ts`: D23 (the `console.open` reply carries `token`,
fetched from `/token`), D24 (the wire limits are built after
`settings_set`, and `hello` is decoded with a line of at most 10 MiB and
no blobs), and the sizes. Done. Its four waits are 120 s each, "a default
kept from the earlier code", after the coordinator corrected an order of
its own that had them replaced. Since: an `error` line before `hello`
shows the server's message, `wire.error_first`; the post limit is a line
over `line_max` or blobs over `blob_max`.

4.9.1.12 The TAP modules with `python/test_all.py` and the two tsconfig
lists. Done: `python/tap_producer.py`, `python/tap_consumer.py`,
`ts/tap_producer.ts` and their tests, run before every other test; the old
`python/tap/` modules, `ts/tap.ts` and `ts/test_tap.ts` removed.
`python/test_all.py` was later rewritten for the two test categories and
the infrastructure for testing.

4.9.2 Step 4.

4.9.2.1 `ts/substrate.ts`, with the database administration measurement.
Done but for one point, blocked by the rule that only the task manager
synchronizes: the worker's initialization calls return promises. The
maintainer settled it: initialization uses promises directly in one
module the audit exempts, `ts/boot.ts`, and no platform port is built.
Three tests of the Python substrate were recorded as not portable to the
browser and given to the browser test: `test_kill_between`, since written
as the browser rung `rung_kill_between` through real workers;
`test_wal_left`, which cannot apply to the SAH pool, which has no WAL, so
nothing was built, approved by the maintainer; `test_create_failed`, for
which no later record names a rung.

4.9.2.2 `ts/mcp.ts`. Done. Its open question, whether `source_put` and
`system_restart`, marked as permit tools, may run unasked, was closed by
the maintainer: they are not permit tools, and only `console_run` asks the
player.

4.9.2.3 `ts/script.ts` and `ts/tools_browser.ts`, with the four database
tools. Done, 21 tools. Left then: the general `kv.get` fetch of a missing
ref; since built for the `kv_get` and `doc_get` tools, which fetch a value
not held and refill the cache after its SHA-256 check, while a script
reading a value not held throws `substrate.cache_unknown`. The four tools
are not in `API/mcp/tools.json` (4.6.9.8). Since: the `verbose_level` tool
went, and `script_run` takes `trace` where it took a level.

4.9.2.4 `ts/agent.ts`, with the system message when the databases pass the
soft limit. Done. Since: a reply with tool calls is stored with its
results after the tools run, approved by the maintainer; a token estimate
was built and then replaced by the event counter in the browser's
substrate (4.2.20).

4.9.3 Step 5.

4.9.3.1 `ts/page.ts`, `ts/worker_ai.ts` and `ts/boot.ts`. Done by its own
check, and partly met by its own account: the cache slots (256) and the
SQLite pool's capacity are fixed at initialization, with no growth at run
time, because only initialization may use promises. The earlier job left
that to the maintainer, with the options a platform port for growth at run
time or larger constants; no later record answers it, and it is accepted
for the review. Also left then, and settled since: `console.close` with
no sender and no handler (the AI handles it; `ConsoleView.close_request`
exists, and no UI action calls it, approved); `#debug` covered by the
fixed `#image` (fixed); the scripted provider's Script at
`/_files/provider/script.json` (seeded from
`python/seed/provider_script.json`, approved).

4.9.3.2 `ts/test_all.ts`. Done. `typescript.tap` holds two TAP documents,
one per thread, against the plan's one TAP plan per language per run; the
earlier job left that to the maintainer as a change with cause, no later
record answers it, and it is accepted for the review. Since: the UI's
suites run first, then the worker's, so every UI line is on the wire
before the worker's suites start.

4.9.3.3 `python/test_browser.py`. Done, with rungs left blocked; the next
job, at the maintainer's request, gave each the change it needed: the
drain timer and poll, written by stalling ttyd with SIGSTOP; reopening the
console view, built, the view returning to idle on exit and ctrl-0 opening
it again; the real HTTP timeout inside a turn, written on a root that
writes its own `provider.json`, approved; the 16 MiB and 128 MiB uploads
from the UI and traced synchronous I/O, through a test engine page outside
the production bundle (a coordinator's default, approved) and DevTools
tracing; the string table replicated from the UI, through the same page;
`test_wal_left` and `test_kill_between` (4.9.2.1). The page's operation
sequence replay, and the compaction, script put and script debug of the
scripted turn, with a stress root of eight rounds, were written too. Its
lines over 79 columns were left to the formatter, which does not shorten
string lines.

4.9.3.4 `python/test_wire.py` with the echo main loop. Done:
`python/echo_loop.py` and the rungs of stages 2 and 4. Left then: the
replay of an operation sequence over the wire, blocked while it rested on
the deleted recorded data; since written as a rung of fourteen operations
the test builds, read back after a reconnect and ending in a
`substrate.since_stale` refusal. Its finding that a reply can be longer
than its request, so that a request of the largest size gets a reply over
the limit, is resolved by the one blob window, which counts blob bytes
only.

4.9.4 Step 6.

4.9.4.1 The whitelist, `python/reformat_whitelist.txt`. Done. Since: the
PowerShell files left it and came back by the maintainer's later decisions,
with `python/reformat_table.json`. Recorded on 2026-10-20 and not changed:
the whitelist missed `html/engine.css`, `python/seed/provider_script.json`
and older JSON, SQL, TOML and tsconfig files, and it lists `LICENSE.md`
and `README.md` against the rule that `.md` files are never added.

4.9.4.2 `i18n/en-US.json`. Done: merged from every fragment, one flat
object, keys sorted by code point, ASCII; later jobs kept it merged.

4.9.4.3 The read only reconciliation. Done by six reviewers: the Python
server; the TypeScript core; the TypeScript AI side; the page, worker and
boot; the contracts, stubs and tooling; the browser and wire runners.
Their findings were for the maintainer and not fixed then. The next job,
at the maintainer's request, took the thirteen listed as stopping the
system or its tests, and the class A items: a fresh root faulting before
its first render; an `error` line before `hello` shown as
`wire.receiver_missing`; the level 2 overlay feeding itself; a failed tool
call breaking a scene; a database over 10 MiB that could not be
snapshotted; a value over `overflow_bytes` lost after `db_unload` then
`db_load`; floats above 2^53 faulting the TypeScript queue; two browser
rungs that could not pass; the empty `python/vectors/`;
`python/test_posix.py` stopping at a byte order mark; lost test output; a
server crash leaving its message only on the terminal; an open console
covering the subtitle, the permit buttons and the input. Each was written
or recorded as a change with cause, and none verified. The reviewers'
other findings were not scheduled; each area's are its candidates
(section 11).

4.9.4.4 The update of the Lookup Accelerator of the project rules. Not
done, held: its update was asked for, while the maintainer had removed
that section and the project rules forbid editing them without request;
the two contradict. Options for the maintainer: it stays removed (held);
the maintainer writes it; an agent writes it.

4.9.5 The maintainer's test run, the TAP tests first. Not done: no record
shows a run, and every later job stopped before the testing phase, as the
maintainer asked.

4.9.6 What the last job left, by its account of 2026-10-21:

4.9.6.1 the testing phase, by the maintainer's order;

4.9.6.2 `chmod +x test_posix.sh`, committed with mode 100644, which no
agent may make;

4.9.6.3 the formatter, run twice and stable after one run, split the one
line `<script data-worker>test_hook.engine_run();</script>` of
`html/test_engine.html` over three lines, so `test_template_hooked` of
`python/test_page_build.py`, which counts that one line, fails. Options
for the maintainer: a `<!-- prettier-ignore -->` line above it; the test
matching the hook whatever its white space; the change reverted by hand,
which the next format run undoes. Not changed;

4.9.6.4 a smoke run stops at its first failure: at that test first, if
nothing earlier fails; then in `python/test_posix.py` at the banner of
`xsjs_install.ps1` (U+2588, U+2591 to U+2593) until the maintainer
answers 4.2.25.3; then at four comments holding `;` outside a code span,
three in `python/test_browser.py` (above `rung_early`, `ui_request` and
`rung_ui_put_largest`) and one in `python/stall_loop.py` (above
`loop_run`);

4.9.6.5 measurements owed to the testing phase: the value of `blob_max`
(`rung_blob_max`); every suite's seconds and the 120 s fit of the smoke
set; the SHA-256 of the 319 byte step script of `ts/test_script.ts` and
`ts/test_tools_browser.ts`, if a constant vector is wanted back; whether
sqlite-wasm keeps header bytes 18 and 19 of an imported WAL database;
about 2 GiB of disk per edge rung and up to 6 GiB of OPFS for
`rung_blob_max`;

4.9.6.6 the designs written and not built: those of 4.2, and one more,
the stub HTTP server of `python/test_browser.py` started only when a rung
needs it; a smoke run starts it though no smoke rung needs it, against the
rule that setup runs when a suite that needs it runs, so it is a candidate
(S) of the browser runner's area, not a design accepted;

4.9.6.7 the empty `python/vectors/`, left for the maintainer to delete.
The other findings it listed for the maintainer are its areas' candidates
(section 11).

## 5 What counts

5.1 Accepted, not a finding. An agent that meets one of these lists it with
what decides it (10.3.3) and changes nothing:

5.1.1 anything section 4.2 lists as built later by design, or section 4.3
as not done without permission;

5.1.2 every item of section 4 that its part presents as decided: the
maintainer's words of 4.1, the designs of 4.2 and 4.3, the defaults D1 to
D31 of 4.4, the additions and departures of 4.5, the answers and approved
items of 4.8; and every Decided item of sections 11 and 12, whichever
area's entry holds it. The questions of 4.7 are open (5.2). An item of
section 4 that presents something as left, missing, partly done or a
candidate, such as a class A item of 4.8.5.3 that no answer accepted, or
the work left of 4.9, is a candidate (5.3.2): checked against the code
and filed only if it still holds;

5.1.3 every value or behaviour that this file or a comment in the tree
marks Unconfirmed, recalled from memory, not measured or unverified;
checking those is the testing phase's;

5.1.4 the hold on the old design (D22, 4.4): `python/bootstrap.html`,
`python/xsjs_screenshot.py`, `python/xsjs_screenshot_wsl.py`, the
`README.md` lines on the old design, `xsjs_stop.ps1`'s comment and
`xsjs_status.ps1`'s `pgrep` stay as they are until the maintainer lifts it;

5.1.5 a comment or a stub in the tree that presents the code's form as
chosen, with a reason of design, by the test of 5.3.4: with the logs gone,
such a comment is the record the AI left of its own decision, and every AI
assumption is accepted (1.4).

5.2 Open, not decided by the review. A question this file leaves to the
maintainer, with options, stays open: those of 4.7, of the Open parts of
sections 11 and 12, and every question of the earlier plan that has a
built option and no answer of the maintainer, which 4.8.4 holds. Its
built option, if any, stands for the review, which keeps it (5.1) and
files nothing against it; its other options are not rejected but open; a
rejection made by a record of the maintainer stays a rejection. The agent
lists each open question it meets (10.3.10) and chooses nothing. A point
where a decided item breaks a project rule or a rule of section 3 is open
too (5.3.5).

5.3 Finding classes.

5.3.1 U: the code differs from what this file states (section 2, section
3, an Expected part, or a decided item), and the search of 5.5 finds no
record of the difference.

5.3.2 M: the code is wrong whatever the records say: it raises where it must
not, cannot pass, contradicts its own comment or stub, breaks a seam, or
breaks a project rule or a rule of section 3. A record that names a defect
and leaves it unfixed, outside a question with options, does not make it
accepted: the Candidates parts of sections 11 and 12 list such records by
area.

5.3.3 S: the code or a record shows a substitute taken for effort, time or
the earlier jobs' ban on running anything, and not chosen between designs.
Its marks are words such as "not built", "left", "stand in", "copied",
"duplicated", "kept from", "by hand", "no ... yet", or a gap that asks no
question. It is in scope only where the expected design is reachable under
sections 6 and 7.

5.3.4 Decision or candidate. A record, whether an item of this file or a
comment in the tree, decides when it presents the code's form as chosen:
"rejected:", "chose", "decided", "(built)", "as built", "approved", a class
B or C item of the earlier job, or a reason of design for the form. A record
that presents something as missing, untested, left, kept, not built,
unreachable or wrong is a candidate, even when it names the fix as an
"alternative".

5.3.5 Precedence: a decided item (5.1) wins. Where such an item breaks a
project rule or a rule of section 3, the point is open (10.3.10), not a
finding. Otherwise a point is M where a rule, a seam or a proof breaks, U
where no record exists, and S where a record shows a substitute.

5.4 Severity, fixed in this order:

5.4.1 1, blocking: the system, a runner or a test cannot work as this file
says: a test that can never pass, a check that stops every run, a seam that
throws, a name used at run time with no entry.

5.4.2 2, defect: wrong behaviour on some input or path.

5.4.3 3, rule: a project rule or a rule of section 3 broken with no change
of behaviour.

5.4.4 4, completeness: a proof, test, rung or part this file names is
missing.

5.5 The search before any finding, since a decided item outweighs even an
M (5.3.5):

5.5.1 the agent's own entry, all of it, and section 2's part on the module;

5.5.2 a `grep -n` of this file for the file stem, the symbol, the `i18n`
names and the line types involved, and a read of each hit, since section 4
or another area's entry may decide the point;

5.5.3 the comments at the place and the module's stub under `API/`;

5.5.4 then the finding, with what was searched and why none decides it; or
the item listed as accepted, with what decides it.

5.6 Out of scope: `archive.sh` and `clean.sh`, which are not part of the
project; the empty `python/vectors/`, left for the maintainer; every file
under `tmp/` but the review's own; values that need a run or a measurement,
which are owed to the testing phase (10.3.11); the project rules file and
its symlink.

## 6 Rules for fixes

6.1 A fix moves the code to what this file states, by the smallest change
that meets it. Nothing is added that no requirement motivates: no refactor,
no rename for taste, no new module or file that this file does not name, no
reuse chosen because some code exists. The project rules ban polish,
decorative comments, extra logging, colour, borders and redesign; a fix
makes none of them.

6.2 Public interfaces. A fix that would add, remove or change a public name
or signature that `API/` declares, or that would need a declaration there,
is not made: the API comes before the code, and `API/` is the maintainer's.
The agent writes the whole design instead, the stub text and every code
change it would bring, as a proposed edit (10.3.9), so that nothing
reasoned out is lost. Private names, test only exports (D25, 4.4) and the
internal line types already recorded (12.3) may change. Moving code to the
name or signature its stub already declares is a fix, not an interface
change; when code in another area relies on the code's present form, it is
a seam change (8.6.7).

6.3 The rules of section 3 bind every fix. Among them: handlers return
finished reply lines built with `reply_make`; `Store.kv_put` takes bytes; a
test that expects an error compares the `i18n` text; fixtures read thread
bound globals in `setUp`; two English words in every function and class
name, private ones included; one comment line per construct; `cast` in
place of a branch that only narrows a type; `i18n` called with a literal
name; `bootstrap.py` owns `hello`; every message of an engine module goes
through `i18n`. The earlier jobs' own working rules, on the commands an
agent could run, on staging and on fragments of strings that could only
add, are replaced for this review by sections 7, 10.6 and 14.2 (17.3.3).

6.4 Tests move with behaviour: a fix that changes what code does changes or
adds its unit test first, in the same area. No test leaves state that
another test sees.

6.5 Strings. A new, reworded or removed `i18n` name goes into the agent's
fragment (10.6), never into `i18n/en-US.json`. An agent writes only names
whose module prefix belongs to its own files; another module's name is a
request (8.6). A prefix used in both languages is written by the owner of
its Python module: `substrate.` by task 1.14; `mcp.`, `dispatch.`,
`settings.` and `verbose.` by task 1.13; `jslb.` by task 1.12. The TypeScript
owner sends that owner a request.

6.6 Names given by the maintainer, by the plans or by `API/` stay, though
they break the two word rule: `verbose.exec` and `verbose.log`, each
runner's `main`, `reformat.reformat`, `idle()`, `rung_blob_max`,
`test_test`.

6.7 Values. A timer or size is a named constant whose one line comment says
its writer chose it. A fix never puts in a value that a measurement should
give; such a value is owed to the testing phase.

6.8 Errors fail loud: no swallowed error, no default, no retry, no branch
for a case that cannot happen; the first failure only; nothing tallies
failures.

6.9 Python imports stand on the fewest lines, in alphabetical order; `from`
is used only for `collections.abc`, `typing` and `from i18n import i18n`;
constants are `_UPPER_NAME` at the top, after the imports. TypeScript has
one frozen `constants` object per module.

6.10 No agent edits: the project rules file and its symlink, `API/` and
`API/README.md`, `README.md`, `LICENSE.md`, the files and parts of the
hold (5.1.4), `archive.sh`, `clean.sh`, and this file; task 1.11 edits
`xsjs_status.ps1` and `xsjs_stop.ps1` outside their held parts (11.3.1).
Proposed edits to `API/`, `README.md` and this file go in the report
(10.3.9); a proposed edit of this file corrects a statement of sections 2
to 4, 11 or 12 that the code and its comments show wrong. The tracked
files `.gitignore`, `.gitattributes` and `.vscode/settings.json` are the
coordinator's (8.1).

6.11 Formatting belongs to the formatter run (14.2), by the project rules.
An agent does not reformat code beyond its own edit, and writes its own new
text within 79 columns. Existing comments and strings over 79 columns that
the formatter cannot wrap are listed as open (10.3.10), not wrapped by hand,
as the maintainer has left them.

6.12 A finding that cannot be fixed under sections 6 and 7 is recorded with
what blocks it and the design that would fix it.

## 7 What is run

7.1 Nothing of the project is run: no test, runner, build, `tsc`, type
checker, linter, ttyd, browser or script of the checkout, by any agent or by
the coordinator. The one run is the formatter of 14.2, because the project
rules make the formatting tools the only way to format. Why: the testing
phase is the maintainer's to start, every earlier job stopped before it,
`tsc` is not installed, and the runners need a built ttyd and Windows
Chrome. Verification is by reading. A verification run is designed in 16.1
and not built; the maintainer turns it on by asking for it when the review
is launched.

7.2 An agent may use: Read, Write and Edit; `ls`, `grep`, `wc`, `test`,
`cmp`, `diff`, and `find` outside `.git`; `git status` and `git diff`
against the baseline; `mv` and `mkdir -p` for locks and under
`tmp/review/`. Agents are launched as the general purpose type, which has
these tools.

7.3 An agent may not: change git's index or history, the formatter's
staging of 14.2 excepted; run `git log`, `git show` or read any past
commit; use a package manager or install anything; use the network; delete
a tracked file, which it proposes instead; write a source file by shell
redirection, `sed -i` or `tee`, since every edit goes through Edit or Write
on a lock name; read a session transcript, which lost an earlier job an
agent to a refusal; ask the user, since questions go in the report.

7.4 Each report counts its commands by name and names every departure from
7.2 and 7.3.

## 8 Locks, ownership and requests

8.1 Ownership. Every file an agent may edit has exactly one owner task,
listed in section 11; a new file belongs to the task that creates it; task
1.40 writes `i18n/en-US.json` and the summaries of 14.1, and task 1.41 lets
the formatter rewrite whitelisted files, the two tasks that write files they
do not own. Only the owner edits a file; anybody reads anything. A file no
entry lists is the coordinator's: requests for it go to
`tmp/review/inbox/coordinator/`, and in Phase 2 the coordinator gives each
one to a task by an `mv` of the request into that task's inbox, recorded in
its log.

8.2 The lock. The owner of `F` renames it `F.T<task id>` with `mv`, edits it
under that name, and renames it back. The rename is atomic: when it fails,
someone holds the file, and the agent does not wait (8.5). An agent holds at
most one source file's lock at a time, for one run of edits, and releases it
before it takes the next, so no reader meets a source lock for long; beside
it, it may hold the locks of its own report, its fragment and the requests
it has claimed. No agent ever waits on a lock, so no deadlock can arise.

8.3 A new file, the review's own under `tmp/review/` included, is written as
`F.T<task id>` and renamed `F` when complete. A report stays under its lock
name until the agent publishes it (10.2.8).

8.4 Reading never waits. A reader that does not find `F` reads `F.T*` as it
stands, knowing it may be mid edit. A `grep` hit on a lock name is a hit on
`F`. A glob or a name filter, such as `ts/*.ts`, `--include=*.py` or `find
-name`, does not match a lock name: a check that lists files by pattern
also lists each `F.T*` as `F`, and looks for a file missing under `F` as
`F.T*` before it files anything.

8.5 A lock held by another task on a file the agent owns is a stray lock:
the agent records it, names it in its reply, and goes on with other work. No
agent takes, edits or removes another task's lock.

8.6 Requests. An agent that needs a change in a file it does not own:

8.6.1 writes a request file `tmp/review/inbox/<owner>/<own>_<n>.md`, where
`<owner>` and `<own>` are task ids and `n` is one more than the highest `n`
of `<own>_<n>` under `tmp/review/inbox/*/` and `tmp/review/done/*/`, in the
form of 10.5, made under its lock name and renamed when complete;

8.6.2 sends it as soon as the finding is made, and does not wait: it records
the request as pending in its report and goes on;

8.6.3 sends one request per finding, or one per owner for a batch of hits of
one rule.

The owner, after its own fixes and again before it ends:

8.6.4 claims each request with `mv tmp/review/inbox/<owner>/<s>_<n>.md
tmp/review/inbox/<owner>/<s>_<n>.md.T<owner>`;

8.6.5 applies it, declines it with the item of this file or the rule that
decides the point, or forwards it to the right owner as a new request whose
`Forwarded from:` line names it;

8.6.6 appends its resolution line and, after `test ! -e
tmp/review/done/<owner>/<s>_<n>.md`, moves it with `mv
tmp/review/inbox/<owner>/<s>_<n>.md.T<owner>
tmp/review/done/<owner>/<s>_<n>.md`, its lock suffix dropped.

A request that arrives after its owner ended is worked in Phase 2 (9.3).

8.6.7 Seams. A change that two owners must make together starts on the
receiving side. The sender changes nothing on its own side and sends its
request with `Seam: pending`. The owner that applies it writes a request
back for the sender's side, `Seam: <s>_<n> applied`, which the sender works
in its pass or in Phase 2. A declined seam request leaves both sides as they
were. Nobody waits for the other side.

8.7 Shared files and their stewards:

8.7.1 `i18n/en-US.json`: only the closing agent writes it, from the
fragments (14.1).

8.7.2 `python/reformat_whitelist.txt` and `python/reformat_table.json`: task
1.10. A new source file reaches the whitelist by request when it is created.

8.7.3 `ts/tsconfig.json` and `ts/tsconfig.test.json`: task 1.18.

8.7.4 `python/test_all.py` and its `_MODULES`: task 1.9.

8.7.5 `ts/test_all.ts` and its module tables: task 1.20.

8.7.6 `settings.json` and `provider.json`: task 1.13.

8.7.7 `python/test_browser.py`: task 1.19; tasks 1.5 to 1.7 send requests.

8.7.8 `ts/test_substrate.ts`: task 1.24; task 1.8 sends requests.

8.8 Waits. An agent waits only for finished work it needs:

8.8.1 a verifier (section 13) is launched when the first area of its group
has ended with an empty inbox, and is resumed by SendMessage as each later
area of the group ends so;

8.8.2 the closing agent starts after every writer and verifier has ended;

8.8.3 the formatter starts after the closing agent;

8.8.4 the postmortem follows the formatter.

Nothing else waits on another agent: an owner starts without the reviewers
that write to it, a reviewer without the owners it writes to, and a
request's sender never waits for its answer. The pool of 9.2 limits how many
agents run at once; that is the coordinator's guard against HTTP 429, not a
wait of one agent on another (17.3.5).

8.9 Lost agents. An agent stopped by a limit, a refusal or the user is
logged at once with the locks it holds, which stay its task's. It is resumed
by SendMessage after the reset. No two agents run under one task id: the
coordinator replaces an agent only after its stop is confirmed, by its
notification or by TaskStop. The replacement, a fresh agent with the same
task id and prompt, first renames each of its task's locks back after
reading `git diff <baseline> -- F` and the predecessor's report, which may
stand at `tmp/review/report/<id>.md.T<id>`, and completes or reverts each
half made change; then it starts 10.2. No other task takes those locks.

## 9 Phases

9.1 Phase 0, the coordinator alone:

9.1.1 opens its log under the project rules, making `tmp/` with `mkdir -p`
since it was removed; task 1 is the user's literal text, the tasks of
sections 11 to 14 numbered as there. If the log already holds a task 1, the
review takes the next free task number k, and every task id 1.x of this file
becomes k.x in the prompts, the lock suffixes, the paths and the lock check
(15.2), and each prompt of 15.3 gives k;

9.1.2 records `git rev-parse --short HEAD` and `git status --short`; that
HEAD is the baseline (1.7). Expected: `?? REVIEW_EXECUTION.md` while this
file is untracked, and ` D` lines for top level `.md` files other than
this file, `README.md`, `LICENSE.md` and the project rules file and its
symlink, the removal of the planning documents, while it is uncommitted;
`tmp/` was never tracked, so its removal shows nothing. Any other change is
recorded, and the review does not start until the coordinator has logged
what it is;

9.1.3 makes `tmp/review/` with `report/`, `i18n/`, and an `inbox/<id>/` and
`done/<id>/` per task and for `coordinator`;

9.1.4 runs the lock check of 15.2, which prints nothing.

9.2 Phase 1, review and fix: tasks 1.1 to 1.30 in a rolling pool of at most
eight at once, a size the writer of this file chose (17.3.5); resumed agents
count against it. The order of launch is the largest work first, owners and
reviewers mixed: 1.19, 1.24, 1.15, 1.12, then 1.1 to 1.8, then the rest in
the order of their task ids. Requests that reach an owner after its pass are
worked in Phase 2. After an HTTP 429 the coordinator may lower the pool, and
logs it.

9.3 Phase 2, drain. When an agent has ended and its inbox holds requests,
the coordinator resumes it by SendMessage to work them (the text of 15.3.2),
or, when it cannot, launches a fresh agent under the same task id with the
Phase 2 prompt of 15.3.2. Task 1.19 may be drained by fresh agents run one
at a time, each taking the waiting requests, making its edits to
`python/test_browser.py` in one lock cycle and reading only the parts it
edits. This repeats until, with every Phase 1 agent ended, every inbox is
empty; at most three resumptions per task, the rest going to the
postmortem.

9.4 Phase 3, verification, tasks 1.31 to 1.39 (section 13), each launched
and resumed as 8.8.1 says. A REJECTED fix goes to its owner as a request and
is worked as in 9.3, once; the closing agent checks the result.

9.5 Phase 4, closing, task 1.40 (14.1).

9.6 Phase 5, formatting, task 1.41 (14.2).

9.7 Phase 6, the postmortem, by the coordinator (15.4).

## 10 The agent's work

10.1 Every agent reads sections 1 to 3 and 5 to 10 whole and its own entry
in sections 11 to 14. It reads section 4 and the other entries by the
search of 5.5, before every finding, as they are long. Its prompt names
its task id, its entry, the baseline and its phase (15.3); this file is its
brief. The project rules reach every agent in its context; no agent opens
the project rules file.

10.2 An owner works in this order:

10.2.1 reads its entry, the stubs of its modules, its files, and the code on
the other side of each seam, and searches this file for its files' stems and
its `i18n` prefix (5.5.2);

10.2.2 writes its definition of done (10.4) into its report before any edit;
the definition is the agent's own, and the coordinator does not shorten it;

10.2.3 checks the code against each item and files findings (10.3.4),
sending each request for another owner's file as soon as it is found (8.6);

10.2.4 fixes its own files in severity order, tests first, each file under
its lock;

10.2.5 writes its fragment (10.6);

10.2.6 works its inbox (8.6.4 to 8.6.7);

10.2.7 checks each item of its definition again and marks it met, or unmet
with the finding, request or reason that holds it open;

10.2.8 works its inbox once more; reads the resolutions of its own requests,
`tmp/review/done/*/<own>_*`, into item 6 of its report; publishes the
report; and replies to the coordinator in at most 15 lines: counts by class
and severity, files changed, requests sent, locks held (none), departures.

A read only reviewer does 10.2.1 to 10.2.3 and 10.2.8, with a definition of
done for its review, and writes nothing outside `tmp/review/`.

10.3 The report, `tmp/review/report/<task id>.md`, numbered by ISO 2145:

10.3.1 Scope: the files owned and the files read.

10.3.2 Definition of done.

10.3.3 Accepted, not changed: each item with what decides it.

10.3.4 Findings, each `4.<n> <class> <severity> <file> <symbol>`, named
`<task id> 4.<n>` outside the report, followed by Expected (the statement of
this file or the stub), Actual (the code, quoted), Searched (what 5.5 read,
and why none decides it), Action (fixed in its files; requested, with the
request; proposed in item 9; or not fixed, with the reason) and Checked (how
the fix was confirmed by reading).

10.3.5 Files changed, the files it created among them.

10.3.6 Requests sent, each with its state.

10.3.7 Requests received, each with its resolution.

10.3.8 The names of its fragment.

10.3.9 Proposed edits to `API/`, `README.md` and this file: the exact old
and new text and the reason.

10.3.10 Open questions met (5.2).

10.3.11 Owed to the testing phase.

10.3.12 The definition of done, item by item, met or unmet.

10.3.13 Commands and departures (7.4).

10.4 A definition of done holds at least:

10.4.1 the expected inventory of the area, each item with its source in
this file or the stub: the modules, public names and signatures, line types
handled and sent, settings read, `i18n` names, test classes, and the proofs
its entry gives the area;

10.4.2 the checks, each a statement a reader can confirm: conformance to
its entry and to sections 2 and 3; each seam; the project rules; the tests
(each proof has its test or rung, or a decided item says why not; error
tests compare `i18n` text; no test leaves state);

10.4.3 the accepted items found;

10.4.4 the exit: done when every check holds, or each that does not has a
finding whose action is a fix, a request, a proposed edit or a recorded
reason, which is one of: an open question (5.2), a public interface (6.2),
a run or a measurement (5.6, 7.1), a request pending with another owner, a
seam whose other side is pending (8.6.7). Time, effort and context are not
reasons: an agent short of context says so in its reply, and the
coordinator continues the task (9.3).

10.5 A request file:

```text
Request <from task id>_<n> to <owner task id>
File: <path>
Symbol: <name>
Finding: <class> <severity>, <one sentence>
Expected: <the statement of this file or the stub>
Change: <exact old and new text, or the change in words>
Seam: none, pending, or <s>_<n> applied (8.6.7)
Forwarded from: <s>_<n>, or none
```

The owner appends one line: `Resolution: applied`, `Resolution: declined,
<item or rule>`, or `Resolution: forwarded to <task id>`.

10.6 A fragment, `tmp/review/i18n/<task id>.json`, is one JSON object with
the keys `add` and `reword`, each an object of name to text, and `remove`, a
list of names. It can reword and remove as well as add, which the earlier
jobs' add only fragments could not (17.3.3).

## 11 Areas and their owners

11.0 Each entry gives its task's files, owned (edited) and read (the
seams), then what is expected, what is decided, what is open, and the
candidates: what the earlier jobs left, to be checked against the current
code and filed only if it still holds, its class fixed by 5.3. The
candidates are not the whole review; the definition of done is (10.4).
The table of 15.5 maps every task to its section and its verifier.
A Decided item that states the built option of a question with no answer
of the maintainer decides the code, and the question stays open as 5.2
says: the entry's Open part holds it, or points to the item of 4.8.4 that
holds it; where it does neither, the question is open all the same.

11.1 Task 1.9, the Python test infrastructure.

11.1.1 Owns: `python/tap_producer.py`, `python/tap_consumer.py`,
`python/test_tap_producer.py`, `python/test_tap_consumer.py`,
`python/category.py`, `python/test_test.py`, `python/test_all.py` (steward
of its table `_MODULES`), `python/i18n.py`, `python/test_i18n.py`.

11.1.2 Reads: the stubs `API/python/tap_producer.pyi`,
`API/python/tap_consumer.pyi`, `API/python/category.pyi` and
`API/python/i18n.pyi`; the twins `ts/tap_producer.ts` (task 1.20) and
`ts/i18n.ts` (task 1.21); the `main(arguments)` of `python/test_posix.py`,
`python/test_wire.py` and `python/test_browser.py`; `python/vectors_make.py`,
which the driver runs; the uses of `category` in `python/test_wire.py` and
`python/test_browser.py`; the TAP check of `python/test_browser.py`;
`i18n/en-US.json`.

11.1.3 Expected.

11.1.3.1 The maintainer asked for a Python TAP producer, a TypeScript TAP
producer and a Python TAP consumer, custom written, following tappy's API
and implementing only what the engine needs, with tests of their own that
run before every other test, and a way to declare that a suite must fail in
a stated way, the test passing when the suite fails exactly that way.
tappy is not downloaded; compatibility with it is tested later.

11.1.3.2 `python/tap_producer.py` is a `unittest` runner writing TAP, with
one plan per run and one indented subtest block per module:
`TAPTestRunner`, a `unittest.TextTestRunner` with the setters the engine
needs, such as `set_stream`; and `Tracker` with `add_ok`, `add_not_ok`,
`add_skip`, `set_plan` and `generate_tap_reports`. Its stub is
`API/python/tap_producer.pyi`; the code's recorded departures from it are in
11.1.4.3.

11.1.3.3 `python/tap_consumer.py` takes a document and returns its stats:
`Parser` with `parse_text` and `parse_line`, yielding the line kinds
`Result`, `Plan`, `Diagnostic`, `Bail`, `Version` and `Unknown`, and
`document_stats(text)`, which returns the plan, the passes, the failures,
the skips and whether the stream is well formed. Its stub is
`API/python/tap_consumer.pyi`.

11.1.3.4 The stream: one TAP plan per language per run; each module's suite
is one subtest block indented four spaces with its own plan, then a parent
`ok N - <module>` line. The line grammar is the default D12 (section 4.4):
the block plan `    1..N` comes first; no `# Subtest` line; bare method
names; a failfast block is plan, points, diagnostics, `Bail out! failfast`.
A block is named after its test module, such as `test_i18n`.

11.1.3.5 `failfast`: the first `not ok` stops the stream, with the
traceback as diagnostics. Side effects between tests are banned; name order
is fine.

11.1.3.6 The ways a run can fail, each exercised on the Python producer as
an expected failure of a suite: a failing assertion, and an exception raised
in a test; a failing `subTest`; errors in `setUp`, in `tearDown`, and in
`tearDown` after a failure (two outcomes of one test); errors in
`setUpClass`, `tearDownClass` and `setUpModule`; `expectedFailure` and an
unexpected success; a skip; failfast ending the run with `Bail out!`; a
module that does not load.

11.1.3.7 The expected failure mechanism, with tests of its own: the stated
non diagnostic lines must match exactly, and each stated diagnostic run
must hold the stated lines in order. The diagnostics are checked for
`AssertionError: 1 != 2` and `RuntimeError: fixture error`.

11.1.3.8 `python/i18n.py`, stub `API/python/i18n.pyi`: `i18n(name, *args)`
returns the text of `name` with the placeholders replaced by the arguments
in one pass. It raises `KeyError` for a missing name, and `ValueError`
unless the set of placeholder indices in the text equals `{0, ..., n-1}`
for n arguments. A placeholder matches `\{(0|[1-9][0-9]*)\}`, ASCII digits
only, so `{01}` is literal text; `ts/i18n.ts` uses the same rule.

11.1.3.9 The table `_STRINGS` is loaded once, at import, from
`<module dir>/../i18n/en-US.json`: a missing file raises
`FileNotFoundError`; a document that is not one object, or a value that is
not a string, raises `ValueError`. In the server root that file is
`<root>/i18n/en-US.json`, beside `<root>/python/`, the root layout, a
departure that stands for the review and awaits the maintainer's acceptance
(4.5.18).

11.1.3.10 `python/category.py`, stub `API/python/category.pyi`, is the
infrastructure for testing that the driver and both runners are built from:
the two labels `smoke-test` and `normal-test`; `options_add(parser)`, which
adds `--smoke-test` and `--normal-test`, at most one, `smoke-test` the
default; `suite_runs(label, category)`, a `smoke-test` run running the
suites labelled `smoke-test` and a `normal-test` run the suites of both
labels; `limit_seconds(category)`, 120 s for a `smoke-test` run, the
maintainer's 2 minutes, and none for a `normal-test` run; `alarm_plan`;
`LabelBook` with `root_enter`, `rung_enter` and `root_leave`.

11.1.3.11 `category.alarm_plan(what, seconds, limit, elapsed)` returns the
alarm of a suite: the sooner of the suite's own seconds and the time left
of the run's limit, the suite's own seconds winning a tie; a refusal once
that time is spent; no alarm when there is neither. It stands after
`limit_seconds`, the module's header names it, its three message texts
write the word `smoke-test` with the module's `_SMOKE_TEST`, and its stub
comment is "The alarm of a suite, the sooner of its own seconds and the
run's deadline."

11.1.3.12 The rules of a label: every suite carries one, written beside it,
and there is no default label; a `smoke-test` suite needs nothing that a
`normal-test` suite does; a root or stage labelled `smoke-test` holds a
`smoke-test` rung, and one labelled `normal-test` holds none, which
`LabelBook` checks as the runner reaches them, raising, so a mislabel fails
loud in the first run that reaches it; a label other than the two strings
raises.

11.1.3.13 `python/test_all.py` is the test driver: it chooses, orders,
times and runs the test suites, and it is the one runner of every suite,
which both official targets call. The infrastructure for testing is the
code the drivers and tests are built from: `category.py` and the TAP
modules.

11.1.3.14 The command is `python3 python/test_all.py [--smoke-test |
--normal-test] [--failfast]`, `--smoke-test` by default, each option by its
full name only: its parser refuses an abbreviation such as `--normal` with
exit code 2 (`argparse`'s `allow_abbrev=False`), so `--fail` does not mean
`--failfast`. Its `main` takes its argument list.

11.1.3.15 A run, in order: the tests of `tap_producer` and `tap_consumer`;
the other Python suites of the category in dependency order, the vectors
`build/vectors/*.jslb` written by `vectors_make.py` before `test_jslb`;
then, when the stream is clean, the checks of `test_posix.py`,
`test_wire.py` and `test_browser.py`, in its own process, through
`test_posix.main([])`, `test_wire.main([option])` and
`test_browser.main([option])`. It stops at the first failure with its exit
code.

11.1.3.16 `_MODULES` lists each Python unittest module once, its label
beside its name: `test_tap_producer` and `test_tap_consumer` first;
`("test_reformat", "smoke-test")` before `test_test_posix`; and
`("test_test", "smoke-test")` last. It names no `test_test_all` and no
`test_category`, and no test of the driver. Every module of the table is
labelled `smoke-test`, as a unit suite; `test_posix.py` is one suite,
labelled `smoke-test` beside its call in the driver.

11.1.3.17 The driver checks its own stream with `tap_consumer`, from the
copy it keeps of its output (`StreamWriter`): a stream that is not well
formed, or one holding a `not ok`, fails the run.

11.1.3.18 Each suite's elapsed seconds, read with `time.monotonic` around
it, are printed with its label: the driver writes `<module>: <label>, <s>
s` to stderr after each module, so stdout stays the TAP stream, and
`test_posix.py: smoke-test, <s> s` after the checks; a passing run ends
with `the <category> run took <s> s`.

11.1.3.19 The deadline: a `smoke-test` run has 120 s in all from its start.
Each module's alarm is the sooner of its own 120 s and that deadline;
`test_posix.py`, `test_wire.py` and `test_browser.py` run under an alarm at
the deadline; a deadline already passed when a suite starts raises at once;
the alarm raises naming the suite it stopped, so the run fails loud the
moment it passes 120 s, with the lines measured so far printed above.
`timer_start(plan)` and `timer_stop()` arm and cancel `SIGALRM` for a plan
and stay in the driver. No test module arms `SIGALRM`, which the driver's
alarm holds while the module runs.

11.1.3.20 A `smoke-test` run stops at its first failing test, so the
deadline's error ends it. A `normal-test` run has no limit of its own,
every suite keeps its timer, and it stops at its first failing test only
with `--failfast`.

11.1.3.21 Timers: the module timer `_MODULE_SECONDS`, 120.0, keeps the 120 s
already written as a default; the 120 s of a `smoke-test` run is the
maintainer's 2 minutes; every other timer is a named constant whose one
line comment says its writer chose it (section 3).

11.1.3.22 Messages: the TAP modules, `category.py` and the driver write
plain English or f-strings, not `i18n`, so the TAP tests load while
`i18n/en-US.json` is missing; the area owns no `i18n` prefix. Settings
read: none. Line types: none; the page's `tap.line` text is checked by
`test_browser.py` with this area's consumer.

11.1.3.23 Tests owed: `python/test_tap_producer.py` and
`python/test_tap_consumer.py`, run first, cover 11.1.3.6 and 11.1.3.7. One
passing, one failing, one raising and one skipped method yield identical
TAP in both languages as one subtest block, accepted by the consumer (with
tasks 1.20 and 1.4). failfast is proved. These are proofs of stage 0, whose
exit is both runners exiting 0 on the real suites, their expected failures
proving each way a run fails.

11.1.3.24 `python/test_i18n.py` proves that `i18n` raises on a missing name
and on a placeholder count that differs, with `TestLookup` and
`TestStrings` (`test_file_values`; `test_file_names`, which scans the non
test `python/*.py` and `ts/*.ts` for `i18n("name"` calls); its placeholder
test tells one substitution pass from two.

11.1.3.25 `python/test_test.py` tests every part of `category.py` and not
the driver: `TestOptions`, `TestSelection`, `TestLimit`, `TestLabelBook`,
and `TestAlarm`, whose seven tests call `category.alarm_plan`; it imports
`import argparse, category, contextlib, io, unittest`, and the parser its
tests build refuses `--normal` with exit code 2. No test module tests the
driver.

11.1.3.26 A test that expects an error compares its message, never only its
class; no test leaves state that another test sees.

11.1.4 Decided, not a finding.

11.1.4.1 D12, the TAP line grammar of 11.1.3.4, a default in force (section
4.4).

11.1.4.2 tappy's names, recalled from tappy's documentation and
Unconfirmed until checked against tappy; the module names `tap_producer`
and `tap_consumer`, read from the maintainer's "tap-producer/tap_producer
tap-consumer/tap_consumer", a hyphen being no legal module name (11.1.5.1).

11.1.4.3 The recorded departures of the TAP code from its stubs, the
writer's choices left for the maintainer: `set_stream(write)` per instance,
taking a line callback, where tappy's is a classmethod and the stub has
`set_stream(streaming: bool)`; `Tracker(write)`; `TAPTestRunner(failfast)`;
the API additions `module_run(module, load)` and `run_end()`, because
tappy has no named nested blocks (rejected: `set_module(name)`, a separate
load failure call); `TAPTestResult`, derived from `unittest.TestResult`
with no `stream`; the consumer's line kinds as `NamedTuple`s with a
`depth`, joined in a `Line` union, where the stub derives them from a
`Line` class; the `TapStats` fields `plan`,
`passed`, `failed`, `skipped`, `well_formed`, where the stub has `plan`,
`ok`, `not_ok`, `skip`, `well_formed`. The stubs keep their own forms, the
maintainer's API.

11.1.4.4 `run` overrides `TextTestRunner.run` and prints no summary, as its
writer recorded; stdout carries only the TAP stream.

11.1.4.5 A point is written once all of a test's outcomes are in, and the
"no outcome" check runs at that moment; it takes its word and directive
from the first failing outcome, the others written as further diagnostics,
so a skip then a `tearDown` error is `not ok` (rejected: writing at the
first outcome).

11.1.4.6 An expected failure is written `not ok N - <name> # TODO expected
failure` and counted as passed; an unexpected success is `not ok` with
`unexpected success`, where tappy writes `ok ... # TODO (unexpected
success)`.

11.1.4.7 A class or module fixture error is a numbered `not ok` point with
its traceback and ends the run with `Bail out! failfast` even without
failfast (rejected: `Bail out! fixture`).

11.1.4.8 `SkipTest` in `setUpClass` or `setUpModule` raises `RuntimeError`,
because D12, the TAP line grammar, has no form for it. A failing subtest's
diagnostics start with the subtest's id line, one point per test. A module
that does not load is a `1..1` block.

11.1.4.9 The consumer's details as built: no tappy `Directive`;
`parse_text` splits at the line feed without stripping; `plan` is the sum
of the block plans; a bailed block's count is not checked; `not ok ... #
SKIP` is refused.

11.1.4.10 `Tracker` accepts `class_name` and does not write it, D12 naming
points by bare method names; diagnostics are written raw; `add_skip` is
kept, though the result does not call it, as tappy's API names it. The
expected failure helpers (`stream_expect`, `stream_reduce`, `runs_find`)
live in the producer's test modules.

11.1.4.11 Unconfirmed, accepted: Python 3.14's traceback colouring only
with a `stream` attribute; the place of `addSubTest` in its list; a
consumer that returns stats only.

11.1.4.12 Full option names, refused abbreviations, in `test_all.py` and in
the parser of its tests only: the maintainer's answer of 2026-10-21, "i
want "--normal-test" that worked great" (section 4.8). `test_wire.py` and
`test_browser.py` run alone keep `argparse`'s default and take `--normal`
for `--normal-test`; the driver passes them the full name, and the answer
leaves them as built.

11.1.4.13 No test of the driver: the maintainer's answer of 2026-10-21,
"just test the stuff that is infrastructre for testing, not the test driver
in there" (section 4.8). `_MODULES` lists `test_test`, which tests the
infrastructure; nothing tests the table; a label other than the two still
raises in `suite_runs` when the driver reaches it.

11.1.4.14 `alarm_plan` in `category.py`, beside the limit it is made from,
and `timer_start` and `timer_stop` in the driver, which alone arms an
alarm: the planners chose it, rejecting a new module such as
`python/deadline.py` with its stub, the timers moved too, which brings
`signal` into the module all three runners import, and a module named
`test`, which would shadow the standard library's `test` package
(11.1.5.7).

11.1.4.15 `python/test_category.py` joined into `python/test_test.py`, so
the tests of one module are not parted between two files by a name alone
(rejected: `test_category.py` kept beside a `test_test.py` holding
`TestAlarm` alone); the reading that the infrastructure for testing is
`category.py` and the TAP modules, which keep their own test modules
(class B, 11.1.5.8).

11.1.4.16 A `smoke-test` run ends at its first failure of any kind,
`TAPTestRunner` being made with `failfast or limit is not None`: built by
the coordinator's choice, so that the deadline ends the run (11.1.5.9).

11.1.4.17 f-strings in the driver and `category.py`, as the TAP modules
write theirs; not built: `i18n` names for them, a suite left out printed or
written to TAP as `# SKIP` (a `smoke-test` run lists only what it ran), a
test that runs `test_posix.sh` or `test_powershell.ps1` (4.2).

11.1.4.18 Every label, and the fit of the smoke set in 2 minutes,
Unconfirmed until the testing phase measures them; class B. The grain of a
label as built: a module of `_MODULES`, and `test_posix.py` whole
(11.1.5.3).

11.1.4.19 `test_posix.main([])` takes an empty list: only the driver and
the two runners take the options, and `test_posix.py`'s label stands beside
its call in the driver.

11.1.4.20 `import category` and other sibling imports stand inside
functions, after `sys.pycache_prefix` is set, so that bytecode goes to
`build/` and not into `python/`.

11.1.4.21 A test reads another module's private name with `getattr`, or
patches it by string target, because pyright strict reports a private name
read from another module. `assertTrue(name in strings)` stands in place of
`assertIn`, so a failure does not print the whole table. `cast` before
`isinstance` in `i18n.py`, written to satisfy pyright strict, unverified.

11.1.4.22 The deliberate exceptions of the strings check: the patched `t.*`
names of `python/test_i18n.py`.

11.1.4.23 Not built, by design (4.2): the driver's table checked by
the driver before its first module; `TestModules`; the options of the
questions of 11.1.5 that are not built.

11.1.4.24 Owed, not a finding: every suite's measured seconds; tappy
compatibility; a pyright strict run.

11.1.4.25 `LabelBook` raises in two cases beyond the label rules of
11.1.3.12, each added by its writer with a test written first: a root
entered while another is open, and a root left when none is open.

11.1.5 Open, for the maintainer.

11.1.5.1 The TAP module layout: a) `python/tap_producer.py`,
`python/tap_consumer.py`, `ts/tap_producer.ts` (built); b) directories
`tap-producer/` and `tap-consumer/` holding the modules; c) another layout.

11.1.5.2 The TAP line grammar: a) D12, the block plan first with bare names
(built); b) tappy's default output, with a `# TAP results for` header and
the plan last; c) the earlier writers' `# Subtest` grammar.

11.1.5.3 The grain of a label: a) a module of `test_all.py`, a rung of the
wire and browser tests with its stage or root labelled too, `test_posix.py`
whole, and the TypeScript modules under the rung that runs them (built); b)
each runner whole; c) each root or stage, the roots split so that each
holds one label; d) as a), with each TypeScript module labelled too.

11.1.5.4 The smoke-test suites: a) the unit suites of both languages,
`test_posix.py`, the wire test without its 2 GiB and 128 MiB echoes, and
the browser roots "suites" (its first two rungs) and "fresh" (built); b)
the unit suites and
`test_posix.py` only; c) as a), with more browser roots that the maintainer
names once the testing phase has measured them.

11.1.5.5 The 2 minutes: a) a `smoke-test` run fails loud the moment it
passes 120 s, with each suite's seconds printed (built); b) it fails at its
end, when its total passed 120 s; c) no limit, the seconds printed for the
maintainer.

11.1.5.6 Options and defaults: a) each target takes `--smoke-test` or
`--normal-test` and passes it on, and every runner defaults to
`--smoke-test` (built); b) as a), but a runner run alone runs every suite;
c) the targets pass every argument through to `test_all.py`, `--failfast`
included.

11.1.5.7 Where `alarm_plan` lives: a) `python/category.py`, beside the
120 s and `limit_seconds` (built); b) a new module such as
`python/deadline.py`, with its stub; c) as a), with `timer_start` and
`timer_stop` moved into `category.py` too.

11.1.5.8 The test modules of the infrastructure for testing: a)
`python/test_test.py` holds every test of `category.py`, which
`python/test_category.py` joined (built); b) `python/test_category.py`
kept, and `python/test_test.py` holding `TestAlarm` alone; c) as a), with
the tests of `tap_producer` and `tap_consumer` joined too, `test_test` then
run first.

11.1.5.9 A smoke-test run ends at its first failure: a) any failure ends
it, the deadline's among them (built); b) only the deadline ends it at
once, other failures running the module out, as a `normal-test` run does;
c) every run ends at its first failure, as the first failure rule asks.
Found and not changed: without `--failfast`, a `normal-test` run records
every failing test of a module before it stops, against "first failure
only"; option c) is the change the records name.

11.1.6 Candidates.

11.1.6.1 `_STRINGS` stands after a function in `python/i18n.py`, against
the rule that constants stand at the top after the imports; recorded by its
writer and again by a later review.

11.1.6.2 The two `ValueError` paths of the strings loader, a document that
is not an object and a value that is not a string, have no test.

11.1.6.3 `del sys.argv[1:]` written twice in `python/test_all.py`, recorded
when the driver called the runners' `main()` with no arguments; check
whether it survived the change to `main(arguments)`.

11.1.6.4 Each way a run can fail of 11.1.3.6 has its expected failure test,
and the TAP modules' tests run first.

11.1.6.5 The stderr lines and the closing line of 11.1.3.18.

11.1.6.6 Recorded for the first version of the driver, with no later record
of a fix: what a test prints to stdout reaches the real stream but not the
copy the consumer checks (the writer expected test modules not to write to
stdout); the exit decision comes from the consumer's stats and `run_end`'s
value is ignored; a `not ok` prints nothing to stderr. Check each against
the driver as it is.

11.1.7 Seams.

11.1.7.1 The driver's calls `test_posix.main([])`, `test_wire.main([option])`
and `test_browser.main([option])`: a change of a runner's signature needs
task 1.10, 1.17 or 1.19, which receives first.

11.1.7.2 `category`'s public names, used by `python/test_wire.py` (task
1.17) and `python/test_browser.py` (task 1.19): a change needs both, and
each receives first.

11.1.7.3 The vectors written before `test_jslb`: a change of
`vectors_make.py`'s entry needs task 1.12, which receives first.

11.1.7.4 The TAP text of `ts/tap_producer.ts` (task 1.20) is the same as
the Python producer's for the same outcomes; a change of the text in one
language needs task 1.20, which receives first.

11.1.7.5 `tap_consumer.document_stats` is called by `python/test_browser.py`
(task 1.19) on `<root>/tap/typescript.tap`, which holds two documents, the
UI's then the worker's, each checked on its own; a change of the
consumer's interface needs task 1.19, which receives first.

11.1.7.6 The placeholder rule of `i18n.py` is the rule of `ts/i18n.ts`
(task 1.21); a change needs task 1.21, which receives first.

11.1.7.7 Both targets call the driver with one option: `test_posix.sh`
(task 1.10) and `powershell/test_powershell.ps1` (task 1.11); a change of
the driver's options needs both, and each receives first.

11.1.7.8 `i18n/en-US.json` is written only by task 1.40, from the
fragments (section 14); a name this area adds, rewords or removes goes in
its fragment (10.6).

11.2 Task 1.10, the rules tooling.

11.2.1 Owns: `python/test_posix.py`, `python/test_test_posix.py`,
`python/reformat.py`, `python/test_reformat.py`,
`python/reformat_table.json`, `python/reformat_whitelist.txt` (steward),
`python/pyproject.toml`, `test_posix.sh`, `powershell/test_lint.ps1`.

11.2.2 Reads: the extension of every whitelisted file; `ts/*.ts`, for the
synchronization audit; `powershell/test_powershell.ps1`, whose lint step
runs `test_lint.ps1`; `python/test_all.py`, which calls
`test_posix.main([])` and which `test_posix.sh` runs. No stub: neither
`reformat.py` nor `test_posix.py` has one, as no tool has; the stub a
`reformat.py` would have is a design not built (4.2).

11.2.3 Expected.

11.2.3.1 `python/test_posix.py` checks every whitelisted file and is one
suite, the rules' audit, labelled `smoke-test`. Its entry is
`main(arguments)`. It reads the table with `reformat.table_read()` and the
whitelist with `reformat.whitelist_paths()`, and finds every file's row
before its first check, so a file with no row fails before anything is
done.

11.2.3.2 Its steps, in this order: the character check of every file; the
comment check of every file; the synchronization audit; the formatters,
through `reformat.reformat`, which rewrite the files; then each row's
linter, when the row has one, once per row from the top directory with the
row's files appended, so `.py` and `.pyi` files are linted in two calls.

11.2.3.3 `non_ascii_check(path, encoding)` decodes a file with its row's
codec and refuses, at its line and column, any character outside
`_NON_ASCII_ALLOWED`, which the PowerShell work left unchanged. The `.ps1`
and `.psd1` rows name `utf-8-sig`, which drops one byte order mark at the
very start of a file and keeps any other U+FEFF, which is then refused, its
column counted after the dropped mark; every other row names `utf-8`, so a
mark at the start of a Python, TypeScript or other file is refused.

11.2.3.4 `comments_check(path, encoding, lexer)` and `comments_find(path,
text, lexer)`: the row's `comments` names the lexer, one of `none`,
`python`, `shell`, `html`, `javascript` and `powershell`; `comments_find`
dispatches on the name and raises for a name it does not know, and no
extension appears in its code. A comment of a group that starts with `<#`
below the header raises `<path>:<line>: <# #> comment below the top of the
file. Use #.`, so a `<# #>` comment is allowed only as the header, as the
header comment of `test_posix.py` says.

11.2.3.5 The PowerShell comment lexer, written anew from its design:
`powershell_scan(path, text, i, closer, comments) -> int`, in the shape of
`shell_scan`, adds each comment from the offset and returns the offset past
the end, or past the first unmatched `)` when `closer` is true; a `closer`
scan that reaches the end fails as `<path>:<line>: unterminated`.

11.2.3.6 Its tokens: a backtick escapes the next character, a line feed
included, inside and outside double quoted strings; `'...'` is read whole
by `_POWERSHELL_SINGLE`, `'(?:[^']|'')*'`, and with no closing quote fails
as `<path>:<line>: unterminated string`; `"..."` is read by
`powershell_quoted(path, text, i, comments) -> int`, where a backtick or
`""` skips two characters and `$(` reads code to its `)` with
`powershell_scan` and `closer` true, and an unclosed string fails as
unterminated; a here string, `@'` or `@"` then only spaces or tabs to the
end of the line (`_POWERSHELL_HERE`), is read whole to the first line that
starts with that quote and `@`, through `end_find`; `<#` starts a block
comment to the next `#>`, `Comment(start, end, 2, 2)`; `#` starts a line
comment to the line feed, `Comment(start, end, 1, 0)`, at the start of the
text or after a character of `_POWERSHELL_TOKEN_BREAK` (a space, a tab, a
line feed or one of `;|&(){},`), and after any other character is part of a
word, as in `a#b`; `(` and `)` count the depth that `closer` needs.

11.2.3.7 The synchronization audit fails on `await`, `.then(`, `new
Promise`, `Atomics` or `SharedArrayBuffer` in any `ts/*.ts` other than
`queue.ts`, `wire.ts`, `http.ts` and `media.ts`, the four modules that turn
an event of the platform (a socket, a response, an image decoded) into a
reply line, and `boot.ts`, the one initialization module.
`_SYNCHRONIZATION_MODULES` names those five. `typescript_paths` raises when
its glob matches nothing; `token_find` reads `ts/*.ts` as `utf-8-sig` and
blanks comments and string literals before it matches; `.then` with
generics is a hit. The self check `audit_probe` writes `_AUDIT_REFUSED`
(nine texts) and `_AUDIT_PASSED` (six) to `build/<temp>/probe.ts` before
the audit.

11.2.3.8 `python/reformat.py`: `FileType(comments, encoding, formatter,
linter, system)`, a `NamedTuple`; `table_read()` reads
`python/reformat_table.json` into rows by extension, a missing or an extra
key failing loud with Python's `TypeError`; `type_find(table, path)`
raises `RuntimeError` `<path>: no row for '<extension>' in <table path>`;
`paths_match(root_path, patterns)`; `whitelist_paths()`, which calls
`paths_match` with the top directory and the whitelist's lines;
`reformat(paths)`, which finds every file's row before it runs a
formatter, then runs each formatter once over its row's files from the top
directory, with `check=True`, only for the rows whose `system` is its
`_SYSTEM`, `linux`. Constants at the top: `_SYSTEM`, `_TABLE_PATH`,
`_WHITELIST_LINE`. No PowerShell name and no extension stand in its code.
Run alone, it formats the files of the `linux` rows.

11.2.3.9 `python/reformat_table.json` is one JSON object. Each key is an
extension as `os.path.splitext` gives it, `.ts` for `a.d.ts`, its case
kept; each value has exactly the keys `comments`, `encoding`, `formatter`,
`linter` and `system`. The rows, as comments, encoding, formatter, linter,
system: `.html` html, `utf-8`, prettier, none, `linux`; `.js` and `.ts`
javascript, `utf-8`, prettier, none, `linux`; `.md` none, `utf-8`,
`mdformat --check`, none, `linux`; `.ps1` and `.psd1` powershell,
`utf-8-sig`, none, none, `windows`; `.py` and `.pyi` python, `utf-8`,
`ruff format --config python/pyproject.toml --cache-dir build/ruff_cache`,
`ruff check` with the same two options, `linux`; `.sh` shell, `utf-8`,
`shfmt --list --write`, none, `linux`. Prettier is `prettier --write
--no-config --print-width 79`. A file with no extension has the extension
`''`, which has no row.

11.2.3.10 The matching rule, one for both systems, in `reformat.paths_match`
and in `test_lint.ps1`'s `_test_lint_get_paths`: the whitelist is read as
UTF-8 and split into lines; a line is a path from the top directory, its
parts joined by `/`, that fully matches ``(?:[^*?\[\]`/]+/)*[^\[\]`/]+``,
only its last part holding `*` (any run of characters or none) or `?` (one
character), and any other line, an empty one among them, fails as
`whitelist line '<line>' is not a path with * or ? in its last part only`.

11.2.3.11 The part before the last `/` names a directory under the top, a
line without `/` the top itself; the names in it are listed, and one
matches when the last part matches it case sensitively and, unless the last
part starts with `.`, the name does not start with `.`. A line that matches
no name fails as `whitelist line '<line>' matches nothing under <top>`; a
match that is not a file fails as `whitelist line '<line>' matches
'<path>', which is not a file`. The files of every line, each once, are
sorted by their paths in ordinal order, so a first failure is the same file
on both systems; the first line that fails stops the reading. `glob` is not
used.

11.2.3.12 `python/reformat_whitelist.txt` lists every source file by name
or by glob: top level files by name, files in subdirectories by glob. A new
source file is added when it is created; `.md`, `.json` and `.css` files
are not added. The six PowerShell lines `xsjs_install.ps1`,
`xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/*.ps1`
and `powershell/en-US/*.psd1` stand after `test_posix.sh`, which stands
after `clean.sh` by name. The whitelist covers the stubs, `API/python/*.pyi`
and `API/ts/*.ts`.

11.2.3.13 `python/pyproject.toml` configures ruff, which runs only its
default rules; ruff's cache is `build/ruff_cache`.

11.2.3.14 `test_posix.sh [--smoke-test | --normal-test]`, a bash script at
the top in the style of `clean.sh`, is one of the project's two official
test targets, and later runs in Docker (4.2). No argument or
`--smoke-test` passes `--smoke-test`; `--normal-test` passes
`--normal-test`; any other argument, or more than one, writes its usage to
stderr and exits 2. It changes to its own directory and runs `exec python3
python/test_all.py <option>`, so its exit code is the runner's. It has no
verbose levels.

11.2.3.15 `powershell/test_lint.ps1` reads `python/reformat_whitelist.txt`
itself (`[IO.File]::ReadAllLines`), matches its lines by the rule of
11.2.3.10 with `Get-ChildItem -Force`, `-clike` and a `SortedSet[string]`
with `[StringComparer]::Ordinal`, and keeps the files whose extension, as
`[IO.Path]::GetExtension` gives it and compared case sensitively, is in its
own list `$extensions_`, `.ps1` and `.psd1`. It runs, in this order, the
CRLF check of each file, `Invoke-Formatter` on each, then
`Invoke-ScriptAnalyzer -Path <file>` on each with the settings of
`_test_lint_get_lint_settings`; the first file with a fault prints it and
exits 1. It has no recursive `Get-ChildItem`, no `$globs_` and no `.psm1`.
Its messages are literal strings; no `i18n.psd1` name serves it.

11.2.3.16 The split by system: Windows formats and analyses the PowerShell
files, through `test_lint.ps1` in the lint step of `test_powershell.ps1`;
Linux checks every whitelisted file, the PowerShell ones for their
characters and comments only, and formats and lints the rest.

11.2.3.17 Messages: the tools write f-strings and literal strings; the area
owns no `i18n` prefix. No setting, no timer, no line type.

11.2.3.18 Tests owed, written before the code: `python/test_reformat.py`, a
unit suite labelled `smoke-test`, listed in `_MODULES` before
`test_test_posix`, tests the table's rows and shape, `type_find` on a row
and on a missing one, `paths_match` on a scratch tree under `build/`
(wildcards, the hidden rule, a literal line, a file matched twice, no
match, a missing directory, a directory matched, case, each refused line
form) and `whitelist_paths()` holding the eight PowerShell files.

11.2.3.19 `python/test_test_posix.py` tests a mark passed at the start of a
file read as `utf-8-sig` (`test_powershell_marked`), a file without one
(`test_powershell_plain`), a mark after the start refused
(`test_mark_inside`), a refused character's column counted after the mark,
with U+2588 (`test_column_after`), and, for a file read as `utf-8`, a mark
at its start refused (`test_others_refused`, with `a.py` and `a.ts`); the
PowerShell lexer's comments (a line, a block, one inside `$( )`), the
strings and here strings it reads past, `#` inside a word and after a
backtick, each unterminated form refused with its message;
`comments_check` refusing `<# #>` below the header and reading a two line
header past the mark; `comments_find` refusing a lexer name it does not
know.

11.2.3.20 The proof of the audit is that it fails on each token outside the
five modules; `audit_probe` checks it in every run.

11.2.4 Decided, not a finding.

11.2.4.1 The PowerShell files in the whitelist, formatted on Windows by
`test_lint.ps1` and checked by `test_posix.py` for characters and comments
only: the maintainer's request of 2026-10-21 ("add the powershell
reformatting back ... remove it from all scanning except the comment
scanner and the utf-8 allow list ... the ps scripts handle formatting on
thier own by reading the whitelist on thier own", section 4.1). A new
PowerShell file is added to the whitelist like any other.

11.2.4.2 The byte order mark allowed through the codec of the `.ps1` and
`.psd1` rows, at the start of a file only, and not added to
`_NON_ASCII_ALLOWED`, where it would pass anywhere in every file as an
invisible character and a Python file starting with it would fail in
Python's tokenizer: class B, built (11.2.5.2).

11.2.4.3 `test_posix.py` stopping at `xsjs_install.ps1:41:19`, the first
banner character (U+2588, U+2591, U+2592, U+2593), in every run, before its
comment checks, audit, formatters and linter: built until the maintainer
answers (11.2.5.3).

11.2.4.4 The table as a data file read by `reformat.table_read()`: the
request says data driven, a Python constant stands before the classes of
its file and so could not hold `FileType` rows, and a shared module would
make `reformat.py`, run as a script, set its bytecode prefix before
importing it (11.2.5.5). The file is JSON and so not whitelisted. A key
written twice in it is kept last by `json.load`, silently; its refusal is a
design not built (4.2).

11.2.4.5 `test_lint.ps1`'s own list of the two extensions, kept equal to
the table's `windows` rows by hand, as it reads the whitelist and not the
table (11.2.5.6). One matching rule enforced on both systems; one
difference stays, a directory part whose case differs from the disk's,
which fails on Linux and may pass on Windows (11.2.5.7). The first file
with a fault ends `test_lint.ps1` (11.2.5.8).

11.2.4.6 The formatters rewrite the whitelisted files in every run of
`test_posix.py`, the `smoke-test` run included: kept as built (11.2.5.4).

11.2.4.7 `audit_probe` lives in the runner, where its writer put it, the
recorded alternative being `python/test_test_posix.py`.

11.2.4.8 `.md`, `.json` and `.css` files stay outside the whitelist; the
comment check has no lexer for `.json` and `.css` and would raise on them.

11.2.4.9 `API/sql/*.sql` outside the whitelist, for want of a `.sql`
lexer: a class B item for the maintainer, who may want one (11.2.5.12).

11.2.4.10 The `.md` row runs `mdformat --check`, which rewrites nothing.

11.2.4.11 Tokens inside comments and string literals are not hits of the
audit, `token_find` blanking them. `async` is not audited, by the default
D29, `async` not added to the synchronization audit (section 4.4). The audit
chooses `ts/*.ts` by its own glob and not from the table, though the
whitelist also lists `API/ts/*.ts`; an `audit` row key is a design not
built (4.2).

11.2.4.12 The PowerShell names keep their files' style:
`_test_lint_get_paths`, `_test_lint_get_lint_settings`, `$extensions_`,
`$whitelist_path_`, `$whitelist_line_`. Each throw of `test_lint.ps1` is
built in `$message_` first, to keep within 79 columns. `test_lint.ps1` is
LF with no byte order mark (11.2.5.2, 11.3.5.2).

11.2.4.13 The lexer limits not built (4.2): a `$( )` inside `@"
"@` is not read as code; `#` after a word is not read as a comment where
PowerShell's expression mode would; PowerShell's own parser, which would
move the comment check to Windows.

11.2.4.14 The lexer and the `<# #>` check were written anew from their
design, not recovered from git; the `<# #>` check is word for word the
earlier design's text.

11.2.4.15 No test runs `test_lint.ps1` or `test_posix.sh`; the testing
phase proves them by running them (11.2.5.10).

11.2.4.16 `test_posix.sh` takes only the maintainer's two options:
`--failfast` stays a developer's option of `test_all.py`, and there is no
`--help` (class B). Its stem is shared with `python/test_posix.py`; both
names are the maintainer's.

11.2.4.17 Prettier writes `<!doctype html>` in lower case; the header check
ignores case. Seven comment texts that were over 79 columns or held a `;`
the comment check refuses were reworded with their meaning kept.

11.2.4.18 The formatter's changes to files no agent edits that the
whitelist covers: the maintainer's `API/ts/*.d.ts` stubs, and
`python/bootstrap.html`, which the default D22 holds untouched (the files
of the previous design, kept until the maintainer decides, section 4.4). A
class B item for the maintainer (11.2.5.11), not reverted by the review.

11.2.4.19 Owed, not a finding: `chmod +x test_posix.sh`, which only the
maintainer may do (11.2.5.1); the formatting and analysis of the
PowerShell files, on Windows; PSScriptAnalyzer's
`PSUseBOMForUnicodeEncodedFile` may report the files with no mark,
unverified.

11.2.5 Open, for the maintainer.

11.2.5.1 `test_posix.sh` is committed with mode 100644 while the target is
run as `./test_posix.sh`; the `chmod +x` is the maintainer's, "which no
agent may"; until then `bash test_posix.sh`. Listed; nothing is changed.

11.2.5.2 Where the UTF-8 byte order mark is allowed: a) at the start of a
file of a `.ps1` or `.psd1` row only, by the row's codec `utf-8-sig`, and
refused anywhere else and in every other file (built); b) U+FEFF added to
`_NON_ASCII_ALLOWED`, allowed anywhere in every whitelisted file, as the
words read, `test_others_refused` then reversing; c) at the start of any
whitelisted file, every file read as `utf-8-sig`; d) as a), and required at
the start of every PowerShell file, as the PowerShell rule of the earlier
job's agent instructions asks (the project rules hold no such rule), so that
`xsjs_status.ps1`, `xsjs_stop.ps1` and `test_lint.ps1` fail until they gain
one.

11.2.5.3 The banner characters of `xsjs_install.ps1`: a) nothing more is
allowed, and `test_posix.py` stops at `xsjs_install.ps1:41:19` (built); b)
U+2588, U+2591, U+2592 and U+2593 join `_NON_ASCII_ALLOWED`, for every
file; c) the four allowed in the PowerShell rows only, by a sixth key of
the table; d) the maintainer redraws the banner in ASCII; e) the script
builds the banner at run time from `[char]0x2588` and the others. The
records put this question first, since it stops every run.

11.2.5.4 `test_posix.py` rewrites the whitelisted files in every smoke-test
run: a) as built; b) it checks the formatting and rewrites nothing (`ruff
format --check`, `prettier --check`, `shfmt --diff`); c) it becomes
`normal-test`.

11.2.5.5 Where the table lives: a) `python/reformat_table.json`, read by
`reformat.table_read`, which `test_posix.py` calls (built); b) a constant
in `reformat.py`, its rows plain tuples; c) a shared module,
`python/file_types.py`, imported by both scripts.

11.2.5.6 How `test_lint.ps1` chooses its files: a) the whitelisted files
whose extension is in its own list, kept equal to the table's `windows`
rows by hand (built); b) it reads the table too and takes the extensions of
its `windows` rows, failing loud on a whitelisted file of no row, as Linux
does; c) every whitelisted file whose extension is not of a `linux` row,
which also needs the table.

11.2.5.7 The matching rule: a) one rule enforced by both scripts (built);
b) `reformat.py` keeps `glob.glob`, and `test_lint.ps1` alone refuses the
lines it cannot match the same way; c) the whitelist names files only,
without wildcards.

11.2.5.8 First failure in `test_lint.ps1`: a) the CRLF check and
PSScriptAnalyzer stop at the first file with a fault (built); b) every
file's faults and results printed before the exit.

11.2.5.9 The "shell scripts" that keep verbose levels: a) the console's
dash and the `.sh` door scripts, and `test_posix.sh` has none (built); b)
`test_posix.sh` takes the shell's level from `verbose_level` or an option
and writes its start and exit at levels 1 and 2 as `verbose.exec` does; c)
every `.sh` file of the project, `archive.sh` and `clean.sh` among them; d)
the PowerShell administration scripts, which would gain levels; e)
another set the maintainer names.

11.2.5.10 Tests of the two targets: a) none, the testing phase proving them
by running them (built); b) a Python test that runs `test_posix.sh` with
bash on a copy beside stub runners, with the maintainer's approval for
Python running bash; c) a shell test script.

11.2.5.11 The formatter's class B items: prettier rewrites
`python/bootstrap.html` and the maintainer's `API/ts/*.d.ts`; Node's
compile cache lands in the system's temporary directory, outside the tree,
against the rule that intermediates go in `build/` (the recorded
alternatives: `NODE_COMPILE_CACHE` under `build/`, or
`NODE_DISABLE_COMPILE_CACHE=1`); prettier reports every unparsable file
and exits 2 at the end, as ruff does, not at the first failure only.

11.2.5.12 `API/sql/*.sql` and a `.sql` lexer, which the maintainer may
want (11.2.4.9).

11.2.5.13 Comments and strings over 79 columns that the formatter cannot
wrap (prettier never wraps comments, and ruff will not shorten a string
line) are listed, not wrapped by hand (section 6).

11.2.5.14 The whitelist lines `LICENSE.md` and `README.md`, which the
maintainer wrote, stand against the project rule that `.md` files are
never added. A decided item that breaks a project rule is open (5.3.5),
and the maintainer, asked, has not answered (4.7.14). Listed, not changed.

11.2.6 Candidates.

11.2.6.1 The message of `synchronization_check` says "the four modules"
where `_SYNCHRONIZATION_MODULES` names five.

11.2.6.2 The audit matches its tokens literally on single spaces, so `new`
and `Promise` parted by two spaces, and `.then (`, escape it, and `x.await`
is a hit: S, not changed by the earlier job.

11.2.6.3 `_SYNCHRONIZATION_MODULES` is exactly `queue.ts`, `wire.ts`,
`http.ts`, `media.ts` and `boot.ts`.

11.2.6.4 A source file the whitelist misses is a discrepancy to fix; task
1.1 sends what it finds. A new row needs its lexer, and a new line must not
change which files the formatter rewrites beyond the file it adds. Recorded
misses: `python/pyproject.toml` and other TOML files, for which the comment
check has no lexer; the writer of the whitelist left out "configuration,
data, third party and `.md` files".

11.2.6.5 Older function names of three or more words in
`python/test_posix.py`, such as `shell_double_scan`, found and not changed.

11.2.6.6 `javascript_scan` may raise on a division directly after a
generic's `>`, recorded as loud, not silent, and not changed.

11.2.6.7 The guard comment of `python/reformat.py` named ruff and shfmt
only when prettier was added; check whether it survived the table.

11.2.6.8 No check measures the width of HTML lines. After the formatter
run six HTML lines were recorded over 79 columns, made by its re-indent: a
comment of 80 columns in each `html/*.html` template (11.10.5.2) and three
lines of `python/bootstrap.html`, which the default D22 holds.

11.2.6.9 The whitelist lines `archive.sh` and `clean.sh` name two scripts
that are not part of the project (5.6); an earlier review recorded them as
lines the whitelist should not have, and no record decided them. The
PowerShell lines and `test_posix.sh` stand after `clean.sh`.

11.2.6.10 Withdrawn: the whitelist lines `LICENSE.md` and `README.md` are
open (11.2.5.14).

11.2.7 Seams.

11.2.7.1 `test_posix.main(arguments)` is called by `python/test_all.py`
(task 1.9) as `main([])`; a change of its signature needs task 1.9, which
receives first.

11.2.7.2 The lint step of `powershell/test_powershell.ps1` (task 1.11) runs
`test_lint.ps1`; a change of how it is called needs task 1.11, which
receives first.

11.2.7.3 A new source file reaches the whitelist by a request to this task
from the task that creates it, and task 1.1's census sends the misses; this
task receives first.

11.2.7.4 `_SYNCHRONIZATION_MODULES` names `ts/queue.ts` (task 1.22),
`ts/wire.ts` and `ts/http.ts` (task 1.23), `ts/media.ts` (task 1.30) and
`ts/boot.ts` (task 1.28); a token moved in or out of them needs that owner,
which receives first.

11.2.7.5 Task 1.41 runs `python3 python/reformat.py` (section 14); a change
of what it formats is this task's, made before that run.

11.3 Task 1.11, the Windows administration scripts and third party code.

11.3.1 Owns: `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1` and
`xsjs_stop.ps1`, but for their parts that the default D22 holds untouched
(11.3.4.1);
`powershell/xsjs_util.ps1`, `powershell/test_powershell.ps1`,
`powershell/en-US/i18n.psd1`, `python/third_party_fetch.py`,
`python/test_third_party_fetch.py`, `third_party/ttyd/01_srv_buf_size.patch`.

11.3.2 Reads: `settings.json` and `provider.json` (task 1.13); the
arguments of `python/bootstrap.py` and the root it reads (task 1.16);
`powershell/test_lint.ps1` (task 1.10); the archive names of
`python/page_build.py` (task 1.18); `python/test_all.py` and its options
(task 1.9); `README.md`, the maintainer's; the stub
`API/python/third_party_fetch.pyi`.

11.3.3 Expected.

11.3.3.1 `xsjs` is the ttyd based back end administration suite, the
Windows scripts at the top of the checkout. The runtime is ttyd in WSL,
started by those scripts; the first beachhead runs from the maintainer's
own WSL account, nothing as root, no service manager, no container. ttyd
listens on 127.0.0.1:5769 inside WSL, and a `netsh` port proxy forwards
5768 to it.

11.3.3.2 The engine works with the latest source release of ttyd, built
from source: 1.7.7, the tag of 2024-03-30. No other ttyd is supported: not
the apt package, not a build of ttyd's main branch, not Windows
`ttyd.exe`. A later release moves the pin.

11.3.3.3 `xsjs_install.ps1` builds ttyd in place of installing the apt
package: it unpacks the release's source archive that
`third_party_fetch.py` fetched into `third_party/`, applies the patches
`third_party/ttyd/<nn>_<name>.patch` in name order, and builds with cmake
under `build/ttyd/`, in WSL, installing nothing. It checks for the build
tools and headers ttyd's README names (`cmake`, `build-essential`, `patch`,
`libuv1-dev`, `libjson-c-dev`, `zlib1g-dev`, `libwebsockets-dev`,
`libssl-dev`), which are present in the maintainer's WSL and are requested
from the maintainer on any other machine. The Windows ttyd report step
stays, and no CMake policy flag is passed, since the 1.7.7 `CMakeLists.txt`
declares CMake 3.12.0 (the default D31, section 4.4).

11.3.3.4 Patch 01, `01_srv_buf_size.patch`, is upstream commit db77fde of
2025-01-31, `src/server.c` and the two man pages (`man/ttyd.1`,
`man/ttyd.man.md`), eight hunks, which adds `--srv-buf-size`, which the
wire's flow control relies on and the release lacks. It is `git
format-patch -1 db77fde` of `../ttyd`, unedited. No other patch exists; a
patch backports the upstream commit where one exists rather than writing
new code.

11.3.3.5 `xsjs_start.ps1` copies into the server root `~/.cache/xsjs/` the
built `build/ttyd/ttyd`, the Python package (the runtime modules that
`$runtime_modules_` lists, and `python/seed`, copied), the page,
`settings.json`, and `provider.json` beside it; the root holds
`<root>/python/bootstrap.py` and `<root>/i18n/` (the root layout, a
departure that stands for the review and awaits the maintainer's
acceptance, 4.5.18). The function that starts ttyd runs the
built binary with `--url-arg`, `--srv-buf-size 1048576`, the index file
name and the root argument, and passes `XSJS_PROVIDER_KEY` from the user's
environment into ttyd's through `WSLENV`; nothing about debug, which is a
setting. The key is required only when `provider.scripted` is false (the
default D8, section 4.4).

11.3.3.6 `xsjs_stop.ps1` reads its arguments from `$args`. Its comment, and
the `pgrep` of `xsjs_status.ps1`, are held untouched (11.3.4.1).

11.3.3.7 `powershell/xsjs_util.ps1`: `xsjs_util_invoke_native` logs the
expanded command as a code span before its exit line.

11.3.3.8 `powershell/test_powershell.ps1 [--smoke-test | --normal-test]`,
on Windows as administrator, is one of the project's two official test
targets. It reads `$args`, as `xsjs_stop.ps1` does, and checks them first,
before the administrator check and the lint step, case sensitively
(`-cin`), as the Python side is; anything else throws `test_usage`. It
then runs `test_lint.ps1`, then the lifecycle.

11.3.3.9 The WSL step comes after the lifecycle step that checks the status
after `xsjs_install.ps1`, and before the first start: `wsl.exe --cd
<checkout> -e python3 python/test_all.py <option>`, its output and errors
shown and logged as every step's, untrimmed, so the TAP blocks keep their
indentation. `wsl --cd` takes the checkout's Windows path, `C:\src` as
`README.md` supports, and starts in WSL's view of it, `/mnt/c/src`. There
it needs the ttyd the install step built, nothing is running, the first
stop having removed the task, the port proxy and the firewall rule, and it
fails before the start steps open ports.

11.3.3.10 It stops on failure: the first failed step throws
`test_failed_step`, naming the step and the log, and exits 1; no later step
runs, the last `xsjs_stop.ps1` among them, so the lifecycle's state at the
failure is left as it is. There is no tally of failed steps and no cleanup
step. Its header states its preconditions: `settings.json`,
`i18n\en-US.json` and `build\hyperposition-engine.html`, made by
`third_party_fetch.py` and then `page_build.py hyperposition-engine` in WSL.

11.3.3.11 `powershell/en-US/i18n.psd1` holds the PowerShell strings, read
through `Import-LocalizedData`; PowerShell keeps its own strings file while
Python and TypeScript read `i18n/en-US.json`. Every name a script uses is in
it. `test_lint.ps1`'s messages are literal strings and use none of it.

11.3.3.12 The PowerShell files are whitelisted. Windows formats and
analyses them with `test_lint.ps1`; `test_posix.py` checks only their
characters, a byte order mark allowed at their start, and their comments,
a `<# #>` comment allowed only as the header (11.2). Five start with a mark
(`xsjs_install.ps1`, `xsjs_start.ps1`, `powershell/test_powershell.ps1`,
`powershell/xsjs_util.ps1`, `powershell/en-US/i18n.psd1`) and three do not
(`xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/test_lint.ps1`); both kinds
pass.

11.3.3.13 `python/third_party_fetch.py`, stub
`API/python/third_party_fetch.pyi`: `file_fetch(url, sha256, name)` checks
the digest's form first, 64 lower case hex characters, else `ValueError`
naming the pin; reuses an existing file with the right digest; downloads
with `urllib`, hashes in memory, raises on a mismatch, writes through a
temporary directory under `build/` and `os.replace`s into
`third_party/<name>`.

11.3.3.14 `_PINS` is a tuple of `(name, url, sha256)` triples among the
constants: `ttyd-1.7.7.tar.gz`, `sqlite-wasm-3460100.zip` and
`xterm-5.5.0.tgz`, each `sha256` the empty string, left for the maintainer,
so the tool raises until they are filled. `_NAME_PATTERN` checks the names.
The timer `_SOCKET_SECONDS`, 60.0, a default chosen by its writer, is passed
as `urlopen`'s `timeout`. tappy is not pinned.

11.3.3.15 Messages: the PowerShell names of `i18n.psd1`; the Python tool
writes no `i18n` names, `i18n` covering the engine modules' messages and
not the tools'. Settings: the scripts copy `settings.json` and
`provider.json` and read no setting; nothing about debug. Line types: none.

11.3.3.16 Tests: `python/test_third_party_fetch.py` holds
`test_pin_versions` and `test_archives_pinned`, which reads `page_build`'s
private archive names with `getattr`, as pyright strict reports a private
name read from another module; its downloads are `file://` URLs. No test
runs a PowerShell script; Windows proves them in the testing phase.

11.3.4 Decided, not a finding.

11.3.4.1 The default D22, HOLD: `python/bootstrap.html`,
`python/xsjs_screenshot.py`, `python/xsjs_screenshot_wsl.py`, the
`README.md` lines on the old design, `xsjs_stop.ps1`'s comment and
`xsjs_status.ps1`'s `pgrep` stay untouched until the maintainer decides
(section 4.4).

11.3.4.2 The byte order marks as they are: allowed at the start of a
PowerShell file, not required (11.2.5.2, 11.3.5.2).

11.3.4.3 The three empty `sha256` pins, left for the maintainer by design,
so that the tool raises until they are filled.

11.3.4.4 `XSJS_PROVIDER_KEY` carried through `WSLENV`, with D8, the key
required only when `provider.scripted` is false, unchanged.

11.3.4.5 The "exited N" line still shows variable names; rejected: a new
parameter of `xsjs_util_invoke_native`, or a script block built from quoted
text.

11.3.4.6 The first failed step ending the run with no cleanup: the
maintainer's answer of 2026-10-21, "make test_powershell.ps1 stop on
failure" (section 4.8). Rejected by the maintainer: the first failure
followed by `xsjs_stop.ps1` run once more as a cleanup under a section
`test_cleanup`, a carry on branch the request does not name; the tally of
failed steps kept as an exception to the rule. Both are designs not built
(4.2). The string `test_cleanup` is gone.

11.3.4.7 The WSL step after the status check that follows the install,
before the first start, and in place, `wsl --cd` of the Windows checkout
with its roots under `build/` there: the planners chose both (11.3.5.4,
11.3.5.5). Rejected: before the lint step, which tests the ttyd of an
earlier install; after the whole lifecycle; a copy of the checkout in the
Linux file system, which would keep the roots' SQLite files and locks off
`/mnt/c`.

11.3.4.8 The Windows ttyd report step, and no CMake policy flag (D31).

11.3.4.9 The root layout `<root>/python/bootstrap.py` and `<root>/i18n/`,
where the plan showed `bootstrap.py` at the root: a departure that stands
for the review and awaits the maintainer's acceptance (4.5.18).
`$runtime_modules_` lists the runtime modules and
`python/seed` is copied, not every non test file, as the earlier job's
instructions ordered.

11.3.4.10 The banner of `xsjs_install.ps1` keeps its non ASCII block
characters, the maintainer's content, as built; `test_posix.py` stops at
it (11.2.5.3). Its first writer rejected ASCII stand ins mapped at script
scope; the later question keeps a banner built at run time from
`[char]0x2588` and the others among its options, so the review chooses
none of them.

11.3.4.11 The header of `test_powershell.ps1` states the preconditions; a
first lifecycle step that builds the page was designed and rejected.

11.3.4.12 `_PinEntry` was removed (alternatives recorded: the class above
the constants, or a dict). The patch keeps a white space only upstream
hunk, the upstream blob ids in its `index` lines and the format-patch
signature, as the unedited backport. `main` of `third_party_fetch.py`
prints nothing, as its writer recorded.

11.3.4.13 Unconfirmed, accepted: one ttyd command, with the role on
`--url-arg`; the patch's applicability, checked by reading only, offsets 0;
the versions and URLs of the pins, and sqlite.org's acceptance of
`urllib`'s user agent; that the source unpacked under the checkout's work
tree may make `ttyd --version` report this checkout's commit;
PSScriptAnalyzer's `PSUseBOMForUnicodeEncodedFile` may report the three
files with no mark.

11.3.4.14 Owed, not a finding: the three `sha256` values, from `sha256sum`;
`chmod +x python/third_party_fetch.py`; one `patch -p1 --dry-run` on the
unpacked release; the ttyd build packages; a ttyd started by the previous
`xsjs_start.ps1`, stopped by hand once (`pgrep -a -x ttyd`, `kill`); the
formatting, analysis and run of every PowerShell file, on Windows.

11.3.4.15 The Windows administration scripts are PowerShell and have no
verbose levels, and none is added: the planners' reading of the
maintainer's "for now only have verbose levels for shell scripts", class
B, built; its question is 11.2.5.9.

11.3.5 Open, for the maintainer.

11.3.5.1 `ttyd.log`: the plan puts it in the server root, and the start
script writes it under `%LOCALAPPDATA%`. A design that meets the plan is
recorded and not built: ttyd started through `sh -c 'exec "$0" "$@"
2>>"<root>/ttyd.log"'`.

11.3.5.2 `xsjs_stop.ps1`, `xsjs_status.ps1` and `powershell/test_lint.ps1`
have no UTF-8 byte order mark, which the PowerShell rule of the earlier
job's agent instructions requires, not the project rules; D22,
which holds the previous design's parts untouched, holds the first two.
Option d) of 11.2.5.2 would require the mark.

11.3.5.3 The banner of `xsjs_install.ps1` (11.2.5.3).

11.3.5.4 When `test_powershell.ps1` runs `test_all.py`: a) after the status
check that follows `xsjs_install.ps1`, before the first start (built); b)
after the whole lifecycle; c) before the lint step.

11.3.5.5 Where `test_all.py` runs from Windows: a) in place, `wsl --cd` of
the Windows checkout, `/mnt/c/src`, with its roots under `build/` there
(built); b) a copy of the checkout in the Linux file system, run there.

11.3.5.6 Tests of the two targets (11.2.5.10).

11.3.6 Candidates.

11.3.6.1 `powershell/test_powershell.ps1` keeps an older `Remove-Item ...
-ErrorAction SilentlyContinue`, which swallows an error; found and not
changed.

11.3.6.2 The header's list of checkout files of
`powershell/test_powershell.ps1` lacks `provider.json`, which
`xsjs_start.ps1` copies.

11.3.6.3 Other command lines logged with their variables unexpanded,
outside the instructions of the time; the list of them is lost, so the
agent finds them.

11.3.6.4 Existing code that reads as a fallback: the `Import-LocalizedData`
retry with `-UICulture en-US`; a failed `wsl --update` that only warns; and
the 15 s `Start-Sleep` polls; each a finding unless a record decides it.

11.3.6.5 ttyd starts with `--srv-buf-size 1048576`, while the setting
`srv_buf_size`, 1 MiB, must have a reader, since a constant no module reads
is not in `settings.json`; it was recorded as read only by the test
runners. One of the two is the deviation.

11.3.6.6 The uniqueness of the pins' names has no test, `test_pin_names`
having been dropped.

11.3.6.7 The archive name `ttyd-1.7.7.tar.gz` in `xsjs_install.ps1` is not
checked against the pin.

11.3.6.8 `_SOCKET_SECONDS` bounds each connect and read, not the whole
download.

11.3.6.9 An existing file whose digest differs from its pin is replaced,
not refused.

11.3.6.10 The tests use `file://` URLs, so redirects, HTTP errors and
timeouts are not covered.

11.3.6.11 Files copied into the root by earlier runs are not removed.

11.3.7 Seams.

11.3.7.1 The WSL step runs `python/test_all.py` with one option; a change
of the driver's options needs task 1.9, which receives first.

11.3.7.2 The lint step runs `powershell/test_lint.ps1`; a change of its
call needs task 1.10, which receives first.

11.3.7.3 `xsjs_start.ps1` builds the root that `python/bootstrap.py` reads
(task 1.16): its arguments, `$runtime_modules_`, `python/seed`,
`settings.json` and `provider.json` (task 1.13); a change of either side
needs the other, and task 1.16 receives first.

11.3.7.4 `python/test_third_party_fetch.py` reads the archive names of
`python/page_build.py` (task 1.18); a change of them needs task 1.18,
which receives first.

11.3.7.5 `python/test_wire.py` (task 1.17) and `python/test_browser.py`
(task 1.19) run the ttyd the install script built and fail naming the
install script when it is missing; a change of the build's path needs both,
and each receives first.

11.4 Task 1.12, JSLB in both languages.

11.4.1 Owns: `python/jslb.py`, `python/test_jslb.py`,
`python/vectors_make.py`, `python/test_vectors_make.py`, `ts/jslb.ts`,
`ts/test_jslb.ts`; the `jslb.` names of `i18n`, for both languages.

11.4.2 Reads: `API/python/jslb.pyi`, `API/ts/jslb.d.ts`, and in
`API/ts/lines.d.ts` the interfaces `LineHeader`, `BlobHeader` and `Line`;
the code that builds a decoder and feeds it, `python/main_loop.py`
(`loop_run`), `python/bootstrap.py` (the decoder of the reply to `hello`)
and `python/echo_loop.py` (task 1.16), and `ts/wire.ts` (task 1.23); the
page's blob sink, `substrate.CacheFiles` in `ts/substrate.ts` (task 1.24);
the callers of the vector writer, `python/test_all.py` (task 1.9) and
`python/page_build.py` with `html/test.html` (task 1.18); the users of the
builders, `python/dispatch.py` (task 1.13) and `ts/dispatch.ts` and
`ts/queue.ts` (task 1.22); `i18n/en-US.json`.

11.4.3 Expected. This is the whole JSLB wire format and its two codecs.

11.4.3.1 JSLB is the one format of every message on every lane but the
console tty's own protocol. It is written twice, `python/jslb.py` and
`ts/jslb.ts`, twins that behave the same but for the differences of
11.4.4. `API/python/jslb.pyi` and `API/ts/jslb.d.ts` hold the signatures;
the code adds `LineDecoder.idle()` in both languages and, in TypeScript,
the `size` argument of `blob_make` (11.4.4.1). `jslb.py` imports `i18n`
only; nothing in the area calls up or sideways.

11.4.3.2 Framing. A message is one line followed by zero or more blobs; a
line is one JSON object followed by CR, the byte 0x0D. The object is
UTF-8 with no white space outside strings. The encoder emits no CR, so the
first CR ends the line. LF is an ordinary byte with no meaning, as is every
byte other than CR outside a string.

11.4.3.3 The blobs follow the CR at once, in header order, each exactly
its `s` bytes, with nothing between them. A reader has two states: bytes up
to a CR, then known byte counts.

11.4.3.4 Headers at integer keys. Every JSON object that carries headers,
a line or a document, keeps them at the integer keys 0, 1, ... and its
payload at every other key. Key 0 is the object's own header. The headers
are found by probing the integers from 0 until one is missing, so a
reference to a header is an integer, `line[0]`, `line[1]`, never a string
of digits.

11.4.3.5 JSON writes every key as a string. The encoder writes an integer
key as its decimal digits, and the decoder turns a key that is the decimal
digits of a non negative integer, with no sign and no leading zero
(`0|[1-9][0-9]*`), back into an integer, at every level of nesting, a
document inside a payload included. In Python the decoded object is a
`jslb.Object`, a `dict` with `int` keys for the headers and `str` keys for
the payload, whose keys are also its attributes; in TypeScript `line[0]` is
the property `"0"` and `headers_of` probes by number.

11.4.3.6 In a line the headers 1 to `b` are blob headers. In a document
the headers from 1 on are reference strings.

11.4.3.7 The line header, key 0, has six fields, each with a short and a
full name: `t` `type`, required, a string, the handler name, lowercase
words joined by `_` and namespaces joined by `.`; `v` `version`, an
integer, default 0; `i` `id`, an integer from 1, present when a reply is
expected; `r` `reply`, an integer, the peer's `i` that the line answers;
`k` `key`, a string, the key the line is about, when it is about one; `b`
`blobs`, an integer, default 0, which equals the number of blob headers
found by probing. A field at its default is not written: defaults are
implicit by omission.

11.4.3.8 A blob header, keys 1 to `b`, has `s` `size`, a required integer;
`k` `key`, where the handler stores the blob, when it does; and `d`
`data`, never serialized: in memory the bytes, or for a streamed blob the
path of its cache file in Python and its cache handle in TypeScript. Any
other field is the handler's. There is no blob type registry: a blob is
opaque bytes to JSLB and to the dispatcher.

11.4.3.9 Names. All the headers of a line use short names, or all use full
names; both forms in one line is a hard error. Full names are the debug
mode form. The decoder returns the headers as sent plus `d`;
`field_get(header, name)` resolves a short or a full name and its default.

11.4.3.10 Values. Numbers are IEEE doubles; integers lie within plus or
minus 2^53, the bound included, so 2^53 passes. The Python encoder refuses
larger integers, NaN and the infinities. Strings are Unicode, and the line
is UTF-8 under the strict decoder on both sides: Python refuses a leading
byte order mark, and TypeScript decodes with `TextDecoder` fatal and
`ignoreBOM: true`. Duplicate keys take the last value; the encoders never
write them.

11.4.3.11 Doubles beyond 2^53. The Python decoder reads an integer token
beyond plus or minus 2^53 as a double, and the TypeScript JSON writer,
`json_write` in `ts/jslb.ts`, refuses only NaN and the infinities, so a
double beyond 2^53 that Python sends passes both decoders and re-encodes.
The Python encoder still refuses such an `int`. The vector
`payload_doubles` holds the case.

11.4.3.12 The hard errors of the format: no header 0; no `t`; a `b` that
does not match the headers present; a gap in 1 to `b`; an `s` that is not
an integer or is negative; a payload key that is decimal digits, at the top
level of a line; both name forms; an unknown field in the line header; a
line over `line_max`, refused before its bytes are buffered, its CR
counted; a message whose blobs' `s` sum over `blob_max`, refused when its
line ends, before any blob byte is buffered.

11.4.3.13 The hard errors the twins add, each a `WireError`: header 0 or a
blob header that is not an object; `t` present but not a string, which
counts as no `t`; `b` not an integer, a boolean refused, which counts as a
count mismatch; `d` or `data` sent in a blob header; invalid UTF-8; invalid
JSON of any kind, a Python `ValueError` or `RecursionError` from the parser
being wrapped as `jslb.line_not_json`; a top level that is not an object;
the constants `NaN` and `Infinity`, which give `jslb.line_not_json`. Not
checked when decoding: the types of `v`, `i`, `r` and `k`, default values
written out, white space outside strings, integers beyond 2^53.

11.4.3.14 The order of the checks, the first fault winning: no header 0;
header 0 not an object; an unknown field; both name forms in header 0; the
type; the gap, which counts p consecutive headers from 1 and makes any
integer key above p `jslb.blob_gap`; the count, a `b` other than p being
`jslb.blobs_mismatch`; then each blob header (not an object, a data field,
its name form, its size); then the payload keys; then `blob_max`.

11.4.3.15 Faults. The decoder raises on the first fault, and the port that
fed it closes; there is no resynchronization on a byte stream. Lines
completed before a fault are returned, and the fault is raised by the next
feed; every feed after it raises `jslb.decoder_failed`. A streamed blob's
file is closed on any exception. `LineDecoder.idle()` says whether the
decoder stands between messages; end of input when it is not idle is a hard
error, which the caller raises. A caller delivers the lines a feed returns,
then feeds empty input, which raises a held fault.

11.4.3.16 Streaming blobs. A blob whose `s` is at most `overflow_bytes` is
collected in memory. A larger one is written as it arrives to a new file in
the cache directory, hashed on the way, and `d` is its path or handle; the
handler moves or links it. In Python the file is the path
`sink_make(header)` returns, opened with `"xb"`, and the decoder sets `d`
and then `sha256`. In TypeScript the decoder calls the `BlobSink` of the
stub (`sink_open`, `sink_append`, and `sink_close`, which returns the
SHA-256), does no hashing of its own and does not check what `sink_close`
returns. The decoder sets `sha256` on a streamed blob's header, replacing
any value the sender put there; an in memory blob keeps a `sha256` the
sender put. Memory per message is bounded by `line_max` plus `blob_max`.

11.4.3.17 The one blob window. `blob_max` is the one window every blob
goes through, the size of the largest database, and one `settings.json`
entry. A window counts blob bytes, the `s` of each blob it holds or passes,
never line bytes, which `line_max` bounds line by line: a message's blobs,
and the blobs of the lines any JSLB queue holds, sum to at most `blob_max`,
and a line that would pass it is a fault. In both decoders that is one
check when the line ends, the sum of the message's `s` against `blob_max`,
`jslb.blobs_over`, before any blob byte is buffered or any sink is called.
The constructors are `LineDecoder(line_max, blob_max, overflow_bytes,
sink_make)` in Python and `new LineDecoder(line_max, blob_max,
overflow_bytes, sink)` in TypeScript. `message_max`, `queue_max` and
`jslb.message_over` are withdrawn.

11.4.3.18 Thresholds are not windows: `line_max` bounds a line and never a
blob; `overflow_bytes` decides only whether a blob is held in memory or
streamed. The shipped values are `blob_max` 2147483391, `line_max` 1048576
and `overflow_bytes` 131072.

11.4.3.19 Encoding. `line_encode` yields the JSON bytes ending in CR, then
each `d` as it is, bytes, file path or handle; it never copies blob bytes.
Python returns an iterator over a list built at call time, TypeScript an
array. The encoder and the decoder share one structure check, so the
encoder refuses every line the decoder would refuse. At every level the
encoder writes the integer keys first, in ascending order, then the string
keys in insertion order; TypeScript sorts the canonical digit keys
numerically, by length and then by digits. Python refuses, with
`ValueError`, a nested string key that is canonical digits and any
negative, boolean or other key that is neither a string nor an integer.

11.4.3.20 Building. `header_make` builds header 0 with its defaults left
out, `full` choosing full names. `blob_make` builds a blob header with `d`
set and `s` measured, from bytes or, in Python, a file path; it always uses
short names and refuses the reserved field names
(`jslb.blob_field_reserved`). In TypeScript a cache handle cannot be
measured, so `blob_make(data, key?, fields?, size?)` takes `size` for a
handle (`jslb.handle_unmeasured` without it) and refuses one for bytes
(`jslb.size_unwanted`); the sender checks the bytes it reads against `s`.
`line_make` numbers the blob headers from 1 and sets `b`, refusing a `b`
already set (`jslb.blobs_preset`), writes no `b` for no blobs, and renames
`s` and `k` to `size` and `key` when header 0 is in full names; `d` keeps
its short name in both forms.

11.4.3.21 Reading. `field_get` refuses an unknown name and a missing `t`
or `s`, raises `WireError` on both name forms, returns `None` in Python and
`undefined` in TypeScript for an absent `i`, `r`, `k` or `d`, and 0 for an
absent `v`. `headers_of` returns the headers found by probing and
`payload_of` the keys that are not integers. `Object.__getattr__` raises
`AttributeError` with `jslb.attribute_missing` for a missing key.

11.4.3.22 Exceptions in Python: a structural fault raises `WireError`,
from the decoder, from the encoder and from `line_render`; a refused value
or argument raises `ValueError`: an integer beyond plus or minus 2^53, NaN,
an infinity, a bad key, a `d` missing or of the wrong size, a `b` set
before `line_make`, a reserved name in `blob_make`. `field_get` raises
`ValueError` for an unknown name and `KeyError` for a missing `t` or `s`.
In TypeScript the name of `WireError` is set on its prototype.

11.4.3.23 Rendering. `line_render` gives a line for a human as its JSON
text followed by one `<blob "n"=K>` tag per blob, K the header key from 1,
the same in both languages. The overlays and the `verbose.put` of wire
traffic use this form, and a 128 MiB upload renders as one line.

11.4.3.24 The vectors. `python/vectors_make.py` writes
`build/vectors/<name>.jslb` and its sidecar `<name>.json` with `jslb.py`
before the vector tests read them: `python/test_all.py` writes them before
`test_jslb`, and `python/page_build.py` writes them for the test page,
which holds them in the global `test_vectors` on both threads, keyed
`<name>.jslb` and `<name>.json`. The writer imports `jslb` inside a
function after setting `sys.pycache_prefix`. No stub under `API/` declares
it.

11.4.3.25 The vectors hold empty payloads, every header field, both name
forms, zero to three blobs, blob bytes holding CR, LF, 0x03, 0x04, 0x13
and invalid UTF-8, each hard error, and the rendered form. Later work added
a line of exactly `line_max` (`line_at_max`), integral floats, doubles
beyond 2^53, a fault after a complete line, and vectors for the added
faults: overlong and surrogate UTF-8, a line that is not an object, a
header that is not an object, data sent in a blob header, NaN and Infinity.

11.4.3.26 Each sidecar carries `limits`, the decoder settings of its
vector: `line_max` 4096, `blob_max` 8192, `overflow_bytes` 1024. The writer
of the sidecar format recorded the rest of it as "success sidecars
`canonical`, error sidecars `error`, `messages`, `render`", the blob bytes
as lowercase hex. The sidecars are built with the standard library's
`json.loads`, not with the decoder.

11.4.3.27 Both decoders read every vector, compare it with its sidecar,
re-encode it, and read the result whole, by single bytes, and split at
every offset; before re-encoding they drop the `sha256` the decoder put on
a streamed blob, TypeScript where `d` is a handle. An error vector is
checked by the `i18n` text of its fault, from a table of arguments per
vector in each test module (`errors_expected`), and that table names
exactly the error vectors written. Each test builds its decoder from the
sidecar's `limits`.

11.4.3.28 The tests and the proof. `python/test_jslb.py` tests every
function and every error, header probing, streaming, refusal before
buffering for `line_max` and for `blob_max`, and the vectors;
`ts/test_jslb.ts` mirrors it and adds tests for what JavaScript alone has;
`python/test_vectors_make.py` tests the writer. Every refusal is compared
with its `i18n` text. Stage 1 is this proof and nothing else, made in both
languages before the format carries anything; its exit is that both suites
pass and, in the plan's words, "each reads all the vectors of the other".

11.4.3.29 The `i18n` names of the area, prefix `jslb.`:
`attribute_missing`, `bad_size`, `blob_data_field`, `blob_data_missing`,
`blob_field_reserved`, `blob_gap`, `blob_size_differs`, `blobs_mismatch`,
`blobs_over`, `blobs_preset`, `both_name_forms`, `decoder_failed`,
`field_missing`, `field_unknown`, `handle_unmeasured`, `header_not_object`,
`integer_refused`, `key_refused`, `line_not_json`, `line_not_object`,
`line_not_utf8`, `line_over_max`, `no_header_zero`, `no_type`,
`number_refused`, `payload_digit_key`, `size_unwanted`, `text_refused`,
`unknown_line_field`, `value_refused`. `attribute_missing` and
`key_refused` are Python's alone; `handle_unmeasured`, `size_unwanted`,
`text_refused` and `value_refused` are TypeScript's.

11.4.4 Decided, not a finding.

11.4.4.1 `LineDecoder.idle()` and the TypeScript `blob_make` argument
`size` are in the code and not in the stubs. They are API additions waiting
for the maintainer (4.5), kept by D11, the default that the API additions
and plan departures stay. The stub edits applied for the one blob window
kept the stubs' four argument constructors, which already had that form,
put above `LineDecoder` the comment line "WireError: a line over
`line_max`, or blobs over `blob_max` in all." and left `idle()` out until
the addition is accepted (4.6.11.3, 4.6.11.4). `idle` keeps its one word
name, which the list of
additions gives it (3).

11.4.4.2 `WireError` carries no slug: D5, the default that the tests
compare `i18n` text from a table of arguments for each vector, rejected the
API addition `WireError.slug`.

11.4.4.3 The deferred fault of 11.4.3.15 is D4, the default that lines
before a fault are returned and the fault raised by the next feed, that a
streamed blob's file is closed on any exception, that `idle()` exists, and
that end of input when not idle is a hard error. As built, Python holds a
fault only when the call returned lines (the alternative, always holding
it, was not taken), holds any `Exception` and lets a `BaseException`
through, and closes the file in a `finally`; TypeScript throws the same
object again and closes the open blob with `sink_close`. A held fault can
be a sink's own error.

11.4.4.4 The TypeScript `size` argument is D3, the default that
`blob_make(data, key?, fields?, size?)` requires `size` for a cache handle
and that the sender checks the bytes it reads against `s`; it answered the
TypeScript writer's question, whose other options were a
`BlobSink.sink_size(handle)` with `blob_make` taking the sink, and a
string meaning text. `blob_make` does not check a handle's `size`;
`line_encode` refuses a bad one as `jslb.bad_size` and passes a string `d`
without measuring it.

11.4.4.5 D7, the default that the Python decoder accepts an integral float
for `b` and `s`, converting it. TypeScript accepts `1.0` and `1e0` there
too, because `JSON.parse` loses the lexical form.

11.4.4.6 `NaN` and `Infinity` give `jslb.line_not_json`, not
`jslb.number_refused`, since the parser refuses them first.

11.4.4.7 A window counts blob bytes only: the planners' reading of the
maintainer's one window, built; its question stays open (4.8.4.7). They
chose against counting line and blob bytes together, the other option,
open, because a blob of `blob_max`, the largest database, must pass
every window with its line, and a `kv.get` reply must fit wherever its
`kv.put` did. No window bounds the bytes of lines without blobs; the
maintainer's earlier 100 MiB queue bound is withdrawn by the maintainer's
later message.

11.4.4.8 `blob_max` 2147483391 is SQLite's documented allocation bound,
Unconfirmed, not a measurement; the measurement is owed to the testing
phase.

11.4.4.9 Doubles beyond 2^53 decode in both languages and pass the
TypeScript writer (11.4.3.11): a later job's fix for the floats Python
sends. The Python encoder's refusal of large integers stays.

11.4.4.10 The vectors go to `build/vectors`, not `python/vectors/`, which
the maintainer approved; the empty `python/vectors/` is left for the
maintainer and is out of scope. Their limits are far below the shipped
ones on purpose, so that splitting every vector at every offset stays fast.

11.4.4.11 The coordinator decided, for the first writers, the JSLB key
order, the streamed blob's `sha256` field, canonical JSON, the vector
sidecar format, and that `vectors_make.py` generates the vector files. The
comment on attribute access and the test `test_attribute_shadowed` were
ordered by the coordinator.

11.4.4.12 The twin contract that the planners set for the TypeScript
writer from the Python writer's gaps stands item by item. 11.4.4.13 to
11.4.4.27 restate it.

11.4.4.13 `line_max` counts the CR; the vectors `line_at_max` and
`error_line_over_max` fix it.

11.4.4.14 Canonical digit keys become integer keys at every level, while
the fault of a payload key of digits applies to the top level of a line
only. JavaScript orders only array index keys, those below 2^32 - 1, first,
so nested digit keys at or above 4294967295 order differently in the two
languages.

11.4.4.15 The encoder's key order and its refusals of keys, as 11.4.3.19
states them.

11.4.4.16 The exception types of 11.4.3.22.

11.4.4.17 The integer bound is inclusive; `MAX_SAFE_INTEGER`, the
alternative, was not taken.

11.4.4.18 The added faults and the points left unchecked of 11.4.3.13.

11.4.4.19 The order of the checks of 11.4.3.14.

11.4.4.20 A `sha256` the sender put on a streamed blob is overwritten. In
Python a blob header's keys come as read, then `d`, then `sha256`.

11.4.4.21 The `overflow_bytes` rule is per blob, so a line of several in
memory blobs can hold up to `b` times `overflow_bytes`.

11.4.4.22 `blob_make` always writes short names; `line_make` renames `s`
and `k` when header 0 is full; `d` is the in memory name in both forms;
`field_get` returns `None` for an absent `i`, `r`, `k` or `d`.

11.4.4.23 `line_encode` checks the line when it is called and returns an
iterator of a list.

11.4.4.24 The vector test drops the decoder's `sha256` from streamed blobs
before re-encoding.

11.4.4.25 The sidecars are built with the standard library's `json.loads`.

11.4.4.26 Not handled, as recorded: stale files in a vector directory; a
digit key of over 4300 digits, a Python `ValueError`; `bytearray` for `d`;
about 6,400 temporary files per run of the streamed vector split at every
offset, removed with the scratch directory.

11.4.4.27 TypeScript decodes with `TextDecoder` fatal and `ignoreBOM:
true`, while Python refuses a leading byte order mark; `t` must be a
string, and `b` and `s` integer numbers, never booleans.

11.4.4.28 The language differences the TypeScript writer recorded, each
accepted, follow in 11.4.4.29 to 11.4.4.45.

11.4.4.29 JavaScript draws no line between integer and string keys, so
Python's refusals of nested string digit keys and of negative, boolean or
float keys have no TypeScript equivalent. A decoded JavaScript object puts
array index keys first where Python keeps the order read; only the order in
memory differs, and the re-encoded bytes are identical. A `Map` based object
model was rejected.

11.4.4.30 TypeScript's `line_make` refuses a payload key of decimal digits
with `jslb.payload_digit_key` when the line is built, where Python refuses
it when the line is encoded, because in JavaScript such a key would
overwrite a header without a sound.

11.4.4.31 A text holding a lone surrogate is refused by TypeScript's
`line_encode` and `line_render` (`jslb.text_refused`), and by Python's
`line_encode` only.

11.4.4.32 TypeScript refuses, with `jslb.value_refused`, the values JSON
cannot carry: `undefined`, holes, functions, bigint, symbols, typed arrays,
`Map`, `Date` and objects that are not plain.

11.4.4.33 Float text differs from Python's for magnitudes below 1e-4 and
for integral floats; no vector hits it, and a Python style float formatter
was not built. The same record said TypeScript refused floats above 2^53;
11.4.3.11 replaced that.

11.4.4.34 The TypeScript decoder accepts `1.0` and `1e0` as integers for
`b` and `s`, and `JSON.parse` rounds integers beyond 2^53 silently; a
parser of its own, or source text access beyond ES2022, were the
alternatives not taken.

11.4.4.35 `field_get` returns `undefined` in TypeScript where Python
returns `None`.

11.4.4.36 The TypeScript decoder does no hashing and does not check what
`sink_close` returns; `sink_append` gets a view valid only during the
call, never an empty one; an error from the sink propagates and leaves the
decoder failed.

11.4.4.37 `__proto__` keys stay own data properties.

11.4.4.38 `test_vectors` is declared inside `namespace test_jslb`, to
avoid a clash.

11.4.4.39 The TypeScript test helper `raised_assert` checks the exact
class.

11.4.4.40 The TypeScript argument texts of `jslb.line_not_utf8` and
`jslb.line_not_json` differ from Python's, by design.

11.4.4.41 A number of 5000 digits decodes to `Infinity` or to a rounded
double in TypeScript, where Python refuses it. The difference is accepted;
that no test pins it is 11.4.6.4.

11.4.4.42 TypeScript's reserved blob field names also hold `key` and
`data`; Python's are `s`, `k`, `d` and `size`.

11.4.4.43 `test_error_name` relies on V8's stack format.

11.4.4.44 The TypeScript vector test's sent line strips `sha256` when `d`
is a handle.

11.4.4.45 TypeScript overwrites a sent `sha256` in place on a streamed
blob, its key order `s`, `sha256`, `d`, and keeps it on an in memory blob.

11.4.4.46 The plan decided against a line type defaulting to UTF-8, string
versions and a blob type registry (4.3): the type is required, versions are
integers, defaults are omitted, and there is no registry. Line types
versioned by handler are built later by design (4.2): nothing needs a
second version yet.

11.4.4.47 Every value the records mark Unconfirmed is accepted: among
them, that the C scanner of Python raises a plain `ValueError` over 4300
digits.

11.4.5 Open, for the maintainer.

11.4.5.1 The value of `blob_max`. Options: a) 2147483391, SQLite's
documented allocation bound, until the testing phase measures Chrome
(built); b) the measured value, once measured; c) a value the maintainer
names. The maintainer's approval of the window's other items left this one
open. The review keeps a), as built.

11.4.6 Candidates.

11.4.6.1 Every hard error of 11.4.3.12 and 11.4.3.13 has a vector, and
both decoders refuse it with its `i18n` text; the encoder refuses every
line the decoder would refuse. Files: `python/vectors_make.py`,
`python/jslb.py` and `ts/jslb.ts`, their shared structure checks.

11.4.6.2 The window of 11.4.3.17 is checked at the CR, before any blob
byte is buffered or any sink call, and `line_max` before the line's bytes
are buffered, in both languages: `LineDecoder.bytes_feed` and its private
helpers in `python/jslb.py` and `ts/jslb.ts`.

11.4.6.3 `line_render` gives the form of 11.4.3.23 identically in both
languages, as the vectors' rendered form fixes it.

11.4.6.4 A number of 5000 digits decodes in TypeScript where Python
refuses it (11.4.4.41), and no test pins either behaviour:
`python/test_jslb.py` and `ts/test_jslb.ts`.

11.4.6.5 The Python path that wraps a parser `RecursionError` as
`jslb.line_not_json` has no test (`python/test_jslb.py`).

11.4.6.6 When the TypeScript decoder closes a streamed blob on a failure,
it calls `sink_close` and discards the hash, so the partial bytes stay in
the sink; and a `sink_close` that throws during that cleanup replaces the
original error, losing the first failure. The writer recorded the
alternatives: an API addition `sink_abort`, a sink that drops a blob closed
after a failure, and wrapping with `cause`. A fix that needs the
`BlobSink` stub changed is a proposed edit (6), not an edit of the stub.

11.4.7 Seams.

11.4.7.1 The decoders' builders and feeders, `python/main_loop.py`,
`python/bootstrap.py` and `python/echo_loop.py` (task 1.16): each builds
`LineDecoder(line_max, blob_max, overflow_bytes, sink_make)`, delivers the
lines a feed returns and then feeds empty input; `bootstrap.py` feeds one
byte at a time and feeds empty input after each. End of input inside a
message is theirs to raise (`main_loop.input_partial` and
`echo_loop.input_partial`, raised as `jslb.WireError`). Task 1.16's side
receives a change of the decoder's signature or of its fault protocol
first.

11.4.7.2 `ts/wire.ts` (task 1.23): builds its decoder after
`settings_set`, the `hello` decoder with no blob and a line of at most
10485760 bytes, and refuses to post a line over `line_max` or a message
whose blobs sum over `blob_max` (`wire.blobs_over`). Task 1.23 receives
first.

11.4.7.3 `ts/substrate.ts` (task 1.24): `CacheFiles` is the `BlobSink`
and copies each appended view during the call; a cached value's blob
header is built with `blob_make` and the row's size. Task 1.24 receives
first.

11.4.7.4 `python/substrate.py` (task 1.14) builds canonical JSON with
`jslb`'s key rules and renames the decoder's streamed file into its cache.

11.4.7.5 `python/dispatch.py` (task 1.13), `ts/dispatch.ts` and
`ts/queue.ts` (task 1.22) rely on `field_get` returning `None` or
`undefined` for an absent `id` and `reply` and 0 for an absent version, on
`header_make` leaving defaults out and writing `type` and `reply` when
full, and on `line_make` writing no `b` for no blobs.

11.4.7.6 `python/test_all.py` (task 1.9) writes the vectors before
`test_jslb`; `python/page_build.py` (task 1.18) puts them into the test
page; `ts/test_all.ts` (task 1.20) runs `test_jslb` on the worker.

11.4.7.7 `python/test_browser.py` (task 1.19) expects `jslb.blobs_over`
from the page's decoder for a `kv.get` reply of `blob_max` plus one byte;
the engine tests of task 1.15 and `python/test_wire.py` (task 1.17) build
four argument decoders. A renamed `jslb.` name or a changed signature is a
request to each.

11.5 Task 1.13, the Python server core.

11.5.1 Owns: `python/dispatch.py`, `python/test_dispatch.py`,
`python/mcp.py`, `python/test_mcp.py`, `python/mcp_stdio.py`,
`python/test_mcp_stdio.py`, `python/settings.py`, `python/test_settings.py`,
`python/verbose.py`, `python/test_verbose.py`; steward of `settings.json`
and `provider.json`; the `i18n` prefixes `dispatch.`, `mcp.`, `mcp_stdio.`,
`settings.` and `verbose.`, for both languages.

11.5.2 Reads: `API/python/dispatch.pyi`, `mcp.pyi`, `mcp_stdio.pyi`,
`settings.pyi`, `verbose.pyi`; `API/settings.json`, `API/mcp/tools.json`,
`API/sql/verbose.sql`, `API/ts/lines.d.ts`; `python/jslb.py` (task 1.12);
the `engine_*` handlers, `engine_system.tools_register` among them (task
1.15); `python/main_loop.py` and `python/bootstrap.py` (task 1.16); the
twins `ts/dispatch.ts` (task 1.22), `ts/mcp.ts` (task 1.25),
`ts/settings.ts` and `ts/verbose.ts` (task 1.21); `xsjs_start.ps1` (task
1.11), which copies both files into the root.

11.5.3 Expected.

11.5.3.1 The area is the Python layer under the engine handlers: the
dispatcher, the MCP server and client and their stdio transport, the
settings file's loader and check, and the server's verbose log with its
one runner of external programs. In the dependency order `jslb`,
`verbose`, `settings` and `mcp` stand under `dispatch`, which stands under
the `engine_*` modules, `main_loop` and `bootstrap`; `mcp_stdio` stands
beside `bootstrap`. No module calls up or sideways.

11.5.3.2 `dispatch.py` has the names of its stub: `Handler`,
`handler_register`, `line_dispatch`, `reply_make`, `error_make`,
`id_next`.

11.5.3.3 `handler_register(type, version, fn)` registers one type and
version; a second registration of the same pair raises `ValueError`
`dispatch.handler_twice`.

11.5.3.4 `line_dispatch(line)` checks the header before the lookup: `v`
must be an `int` and not a `bool`, else `dispatch.version_refused`; `i`,
when present, an `int`, not a `bool`, of at least 1, else
`dispatch.id_refused`. It does not check `t`, which the decoder already
refuses when it is not a string. An unknown pair of type and version raises
`LookupError` `dispatch.handler_unknown`. It calls `fn(line,
**payload_of(line))`, so a handler reads its first blob as `line[1].d`.

11.5.3.5 A request whose handler returns `None` raises `ValueError`
`dispatch.request_unanswered`; a notification whose handler returns a reply
raises `ValueError` `dispatch.notification_replied`. On a reply,
`line_dispatch` sets `r`, spelled `reply` or `r` as the reply's own header
spells its names, and overwrites a wrong `r` without a sound; it checks
neither the reply's name form nor its `t`.

11.5.3.6 `reply_make(line, blobs, **payload)` builds a reply that carries
`t` and `r` only, no `v` and no `k`; `blobs` defaults to `None`. Handlers
return finished reply lines built with it.

11.5.3.7 `error_make(line, error)` builds the one `error` line for a
raise: `message` is `str(error)`, `stack` the formatted exception without
its final newline, chained causes included; `r` is set only when the
request had `i`; the line takes the request's name form, short names when
`line` is `None`.

11.5.3.8 `id_next(port)` counts per port from 1.

11.5.3.9 Fail fast: whoever calls `line_dispatch` catches what it raises,
writes `error_make(line, error)` and exits 1; a failed handler produces one
`error` line, with `r` when the request had `i`, written and flushed before
exit 1. Nothing is swallowed, defaulted or retried.

11.5.3.10 `mcp.py` has the names of its stub: `Message`, `Tool`,
`ToolResult`, `RpcError`, `Server` with `tool_register` and
`message_handle`, and `Client` with `message_handle`, `initialize_send`,
`tools_list` and `tool_call`. It implements JSON-RPC 2.0 and the MCP
methods `initialize`, `notifications/initialized`, `ping`, `tools/list`
and `tools/call`, revision `2025-06-18` pinned as a constant, capability
`tools` only, any further part of MCP emulated when a tool needs it. It is
transport agnostic: `message_handle(message)` returns the response, or
`None`.

11.5.3.11 The server returns `None` for any message without an `id`, a
notification; it lists tools in registration order, with `_meta` only for a
permit tool; a second tool of one name raises `mcp.tool_twice`. Errors are
`RpcError(code, message, data=None)` responses: -32600 for an invalid
message; -32601 for a request to a notification method, or to a method not
served; -32602 for an unknown tool name, `mcp.tool_unknown`, or for
`params` or `arguments` that are not objects; -32603 with `data.stack` for
a tool's exception. Arguments are not validated against `inputSchema`.
`initialize`
ignores the client's params and keeps no lifecycle state. Every
`tools/call` result carries `isError`.

11.5.3.12 The client allocates ids from 1 and registers the callback
before it sends. An error response makes `Client.message_handle` raise
`RpcError`; a reply id that is not an `int`, an error response with id null
among them, raises `mcp.reply_id_refused`; an id it does not await raises
`mcp.reply_unknown`; the callback is popped before an error is raised.

11.5.3.13 The server's MCP server is built as `mcp.Server("xsjs-server",
"0")`. `engine_system.tools_register(server, root, debug)` is the one place
its tools, `source_put` and `system_restart` of `API/mcp/tools.json`, are
registered, for the `mcp` line and for stdio alike. The `mcp` line's
payload is the JSON-RPC message itself.

11.5.3.14 `mcp_stdio.py` serves the server's tools as newline delimited
JSON-RPC on stdin and stdout, so that an external agent drives a server
directly. `stdio_serve(argv)` of its stub reads `--root`, takes `debug`
from `settings.settings_load`, builds the server and calls
`engine_system.tools_register(server, root, debug)`; the addition
`stdio_run(register, stdin, stdout) -> int` serves given streams, so a
test needs no root.

11.5.3.15 Stdio output is compact UTF-8, flushed per response. A blank
line, a line that is not JSON (`mcp_stdio.line_malformed`) and a line that
is not an object (`mcp_stdio.line_object`) raise `ValueError`, and the
process exits 1 by its traceback; input accepts `NaN`. Nothing over stdio
refuses a tool:
`source_put` and `system_restart` are not permit tools, and the AI calls
them without asking, over the line and over stdio.

11.5.3.16 `settings.py`: `settings_load(path)` reads UTF-8 JSON, requires
an object (`settings.not_object`), checks it and returns the dict as read;
`settings_check(settings)` raises `ValueError` through `i18n` on a missing
key (`settings.key_missing`), an extra key (`settings.key_extra`) or a
wrong type (`settings.type_wrong`), in that order, the top level before
`provider`. Types are compared by exact identity, so a `bool` is no `int`;
where a `dict` is wanted, `isinstance(..., dict)` lets a decoded
`jslb.Object` pass. There are no range checks: the plan names keys and
types only. `settings.put` checks its object with `settings_check` before
the file is rewritten.

11.5.3.17 `verbose.py` has `LogLine(at, text)`, `log(text)`,
`history_get(count)` and `exec(level, argv, argv_verbose)` of its stub,
and the additions `log_open(root, ring)`, `log_close()`, `lines_put(thread,
lines)` and `tail_get(thread, count)`. It imports only `i18n`.

11.5.3.18 It owns `<root>/_verbose.sqlite` and its one `line` table of
`API/sql/verbose.sql`, which has no `level` column and no substrate
tables; `_verbose` is the server's alone and is left out of `hello`'s
`seq`. `log_open(root, ring)` opens the file, creates the table only when
`sqlite_master` lacks it, sets only `journal_mode=WAL` and
`synchronous=NORMAL`, and starts an empty ring of `ring` lines, the setting
`verbose_ring`. A second `log_open` raises `verbose.open_twice`; `log`
before `log_open`, and `log_close` on a closed log, raise
`verbose.not_open`.

11.5.3.19 `log(text)` takes no level. It commits the row to `_verbose`
first, each row its own commit, then appends the line to the ring, all
before it returns, so that a hard exit loses nothing. `history_get(count)`
returns the ring's last `count` lines, oldest first; a negative count
raises `verbose.count_invalid`.

11.5.3.20 `lines_put(thread, lines)` writes the page's lines, thread `ui`
or `ai` (else `verbose.thread_unknown`), in one transaction, outside the
server's ring. `tail_get(thread, count)` reads them back, oldest first,
lines of earlier openings included, and refuses `server`, which
`history_get` serves.

11.5.3.21 `exec(level, argv, argv_verbose)` is the one place an external
program is started. Its levels are the shell's and the only verbose levels
the server has: level 0 runs `argv` with its output passed through; level
1 runs `argv` with its output passed through and writes its start
(`verbose.exec_run`) and its exit (`verbose.exec_exit`) to the log; level 2
runs `argv_verbose`, the caller's command line carrying that program's own
verbose flags, raw, its output passed through, and writes the same two
lines. A level outside 0 to 2 raises `verbose.level_invalid`; a death by a
signal returns a negative code. The console role runs dash through it at
the setting `verbose_level`, `[dash, "-v"]` being dash's level 2 form.

11.5.3.22 The server has only `debug`, no verbose level. A failure is
logged always, the message only and never its stack
(`bootstrap.run_failed`, `main_loop.serve_failed`); the trace of each line
the server dispatches and replies to (`bootstrap.hello_submit`,
`main_loop.line_dispatch`, `main_loop.line_reply`) is written when `debug`
is true and never otherwise, each line's header JSON only. The writers of
those lines are task 1.16's; `verbose.log` is this task's.

11.5.3.23 `settings.json` at the top level holds constants only, each with
a sane default, never a password or a key, with the keys of
`API/settings.json` in its order: `debug`, `queue_synchronous`,
`verbose_level`, `verbose_ring`, `line_max`, `blob_max`,
`overflow_bytes`, `chunk_bytes`, `srv_buf_size`, `media_db_bytes`,
`files_browser_bytes`, `db_soft_bytes`, `turn_compact_turns`,
`long_task_ms`, and `provider` holding `scripted` and `timeout_seconds`
only. A constant no module reads is not there. `message_max`, `queue_max`,
`verbose_forward`, `turn_compact_tokens` and the provider's three strings
are gone from it.

11.5.3.24 The values the decisions fix: `blob_max` 2147483391, the one
window of every blob; `chunk_bytes` and `srv_buf_size` 1048576, the pieces
a blob is cut into and not windows; `line_max` 1048576; `overflow_bytes`
131072; `db_soft_bytes` 1073741824, a soft limit that refuses nothing;
`turn_compact_turns` 64; `long_task_ms` 5; `provider.scripted` true and
`provider.timeout_seconds` 120. `verbose_level` is read by the console
role alone; `verbose_ring` is the size of each thread's ring.

11.5.3.25 Start copies `settings.json` into the root; the server loads it
into `_settings` and sends it in `hello` unmodified; `settings.put`, in
debug mode, rewrites the root's file, which the server reads again at the
next `hello`.

11.5.3.26 `provider.json`, beside it, holds `base_url`, `chat_model` and
`image_model`, empty strings until the maintainer fills them out. When
`provider.scripted` is false the server reads it, an empty value is an
error, and `hello` carries it as `provider_info` beside `provider_key`;
when true, as in every test but one, the file is never read and `hello`
carries no `provider_info`. The one rung of the real HTTP timeout inside a
turn writes its own `provider.json` into its own root, with
`provider.scripted` false there and `base_url` at a local stub, which the
maintainer accepted. Start copies the file into the root.

11.5.3.27 Every message of the area goes through `i18n` with a literal
name. The names: `dispatch.handler_twice`, `handler_unknown`, `id_refused`,
`notification_replied`, `request_unanswered`, `version_refused`, and the
TypeScript twin's `id_invalid`, `reply_headerless`, `stack_missing`,
`type_invalid`; `mcp.call_params`, `message_unexpected`, `method_unknown`,
`reply_id_refused`, `reply_unknown`, `request_invalid`, `tool_twice`,
`tool_unknown`, and the twin's `prefix_refused`, `prefix_unknown`,
`reply_error`, `reply_method`, `response_invalid`, `result_invalid`,
`tools_unread`, `version_refused`, `wake_unknown`;
`mcp_stdio.line_malformed`, `line_object`; `settings.key_extra`,
`key_missing`, `not_object`, `type_wrong`, and the twin's `already_set`,
`no_sender`, `not_set`, `put_denied`, `sender_twice`, `unknown_id`;
`verbose.count_invalid`, `exec_exit`, `exec_run`, `level_invalid`,
`not_open`, `open_twice`, `thread_unknown`, and the twin's `ring_invalid`,
`sink_twice`. The task writes these prefixes for both languages; the
TypeScript owners send it requests.

11.5.3.28 Tests. Every test that expects an error compares the `i18n`
text. `test_mcp_stdio.py` holds a class `TestProcess` that starts
`python/mcp_stdio.py --root <scratch>` with pipes and
`PYTHONPYCACHEPREFIX`, replays a session built from the pinned revision
and the server entries of `API/mcp/tools.json` and expects exit 0, then
sends a malformed line and expects exit 1 with a traceback naming
`mcp_stdio.line_malformed`, under the timer `_CHILD_SECONDS`;
`test_tools_run` calls `source_put` and `system_restart` over stdio.
`test_mcp.py` registers `console_run` from `API/mcp/tools.json`, so that
the permit `_meta` path keeps a case.

11.5.3.29 Proofs. Stage 3 builds `settings.py` and `verbose.py` with the
server substrate and passes under `python3 -X dev`. Stage 4 builds
`dispatch.py`, `mcp.py` and `mcp_stdio.py` with the handlers and the main
loop and proves, through the wire test and a stdio MCP client written in
the test, `tools/list` and `tools/call` over stdio and over the `mcp` line,
and an unknown type giving `error` and then exit 1; its exit is that the
rungs pass and pyright is clean.

11.5.4 Decided, not a finding.

11.5.4.1 No refusal on stdio: the maintainer's rule that nothing refuses
the AI API access to the databases made `source_put` and `system_restart`
plain tools, and the stdio permit refusal was removed with its name.

11.5.4.2 `system_restart` over stdio execs the stdio process with
`--main-loop`, which `mcp_stdio`'s argument parser refuses (exit 2, no
reply), and would restart the stdio process rather than the server under
ttyd; it is kept because it fails loud. The alternatives recorded were not
registering it on stdio, `mcp_stdio` accepting `--main-loop`, and a stdio
tool restarting the engine server found through the root.

11.5.4.3 Shell level 1 passes the output through and logs the start and
the exit, the planners' choice, built, because a captured level 1 gives
dash no input; the other option, capturing the output as Markdown
progress, is open (4.8.4.20). The server's debug trace holds header JSON
only, built; the other options, the whole rendered line and no trace, are
open (4.8.4.21).

11.5.4.4 No `level` column in `_verbose` and no `level` in `LogLine`: no
level is left to record, and a column of values no level gave would be
fake data.

11.5.4.5 D21, the default that no failure stack is written to `_verbose`.

11.5.4.6 D13, the default that `verbose.tail_get(thread, count)` serves
`ui` and `ai`; an empty list, which would be fake data, was rejected.

11.5.4.7 The settings check: exact type identity; `ValueError` for every
fault (a custom class, `KeyError` and `TypeError` rejected); the extra name
`settings.not_object`; the order of 11.5.3.16; no range checks; duplicate
keys not detected, integers past 2^53 not checked, a byte order mark
refused; an `Object` value at a scalar key named `Object` in
`settings.type_wrong`.

11.5.4.8 `exec` at level 0 flushes before it runs `argv`: the
coordinator's order, recorded as a class B item with its cause.

11.5.4.9 The dispatcher's recorded forms: `blobs` defaults to `None` (a
shared mutable list rejected); a wrong `r` is overwritten without a sound
(setting it only when absent, or raising when it differs, not taken);
replies carry no `v` and no `k`; the error line follows the request's name
form (always short, and full when `debug`, rejected); `message` is
`str(error)`, so a `KeyError` prints with quotes; the exception classes of
11.5.3.3 to 11.5.3.5; no check that a reply's form or `t` matches the
request's.

11.5.4.10 The header checks run before the lookup, where `ts/dispatch.ts`
looks up first, and their names are new, `dispatch.id_refused` and
`dispatch.version_refused`, rather than the TypeScript `dispatch.id_invalid`,
because the rules differ and one name holds one text. `error_make` copies
an invalid `i` into `r` (leaving `r` out, or raising, not taken).

11.5.4.11 `id_next` counts per port, as the plan has it for the server;
the page's ids are D2, the default that request ids are one counter per
thread queue.

11.5.4.12 MCP's recorded forms: the addition `stdio_run` (4.5); the
`RpcError` constructor; the codes of 11.5.3.11; arguments not checked
against `inputSchema`; no lifecycle state in `initialize`, so the client's
identities are not checked; `isError` always written; the client raising
`RpcError` on an error response.

11.5.4.13 The stdio test's choices: the scratch settings are a byte copy of
the checkout's `settings.json`; each `select` is bounded on its own (one
deadline per line not taken); the last stderr line is matched exactly
(`PYTHON_COLORS=0` not taken); `_CHILD_SECONDS` 30 is a default chosen by
its writer; the test doubles are named `DirectLink` and `CallRecorder`.

11.5.4.14 The verbose log's recorded forms: `log_open` takes the ring size
and opens the file (a `level` parameter, verbose reading the settings, a
lazy open and a `Log` class rejected); `log_close` exists so that tests
leave no open connection; `lines_put`'s lines stay out of the server ring;
`tail_get` refuses `server`; `exec` has no `cwd` and no `env`, so the
console role changes directory and scrubs the environment itself; only
two pragmas are set; `exec`, the maintainer's own name, shadows the builtin
inside the module only.

11.5.4.15 `verbose.exec` and `verbose.log` are the maintainer's names and
break the two word rule by right (3). `from i18n import i18n` is the one
allowed `from` import (3).

11.5.4.16 `provider.json` is the coordinator's default for the
maintainer's request for "a file that needs to be filled out with the info
and is not used during testing", its three keys taken out of
`settings.json`. Its root copy is made by start; the server checks it
beyond the order, exact keys and string values, under one name
`bootstrap.provider_keys` for missing, extra or not an object, and sends
`provider_info` as read.

11.5.4.17 The settings entries as decided, built: `blob_max` keeps its
name for the one window, its value Unconfirmed until measured;
`chunk_bytes` and `srv_buf_size` stay 1 MiB, the maintainer's answer;
`verbose_level` keeps its name, read by the console role alone (renaming it
`shell_level` and removing it are other options of its question, open,
4.8.4.19; carrying the level in the console's `--url-arg` rejected);
`verbose_ring` stays, a ring size and not a level; `verbose_forward` goes,
`verbose.put` being forwarded whenever `debug` is true; `turn_compact_turns`
replaces `turn_compact_tokens`, its 64 a sane value chosen by its writer,
Unconfirmed, its question open (4.8.4.27); the three provider keys moved to
`provider.json`.

11.5.4.18 The settings and verbose texts the tests expect from SQLite and
from the platform that were written from memory, such as the SQLite message
of `test_page_batch`, are Unconfirmed and accepted.

11.5.5 Open, for the maintainer.

11.5.5.1 `mcp_stdio.py` sets no `sys.pycache_prefix`, because its sibling
imports are needed at module level and setting the prefix before them
trips ruff's E402; run as a script it writes `__pycache__` beside
the sources unless `PYTHONPYCACHEPREFIX` is set. Options: `# noqa: E402`;
a launcher; the imports inside `stdio_serve`; documenting
`PYTHONPYCACHEPREFIX`.

11.5.5.2 A tool function's exception becomes a -32603 response with
`data.stack`, and the server keeps running; a tool called with `debug`
false raises and is answered so, and the server does not exit. The writer
chose this over an `isError` result as MCP specifies for tool errors, no
`data`, and ending the process; a later review reported it as breaking fail
fast. A record decides it and a project rule stands against it, so it is
open, not a finding. Options: a) as built; b) the process ends, as a failed
handler does; c) an `isError` result.

11.5.6 Candidates.

11.5.6.1 A negative `v` passes the dispatcher's type check and ends in
`dispatch.handler_unknown`: `line_dispatch` in `python/dispatch.py`.

11.5.6.2 Invalid JSON in `settings.json` or in `provider.json` raises
`json.JSONDecodeError` with no `i18n` message, untested, "if" the rule
that every message of an engine module goes through `i18n` reaches it:
`settings_load` here, the provider file's reader in `python/bootstrap.py`
(task 1.16).

11.5.6.3 Every key of `settings.json` is one of 11.5.3.23 and has a
reader; with task 1.1. A later review found `srv_buf_size` and
`long_task_ms` read only by test runners, and the ttyd command line fixes
`--srv-buf-size 1048576` while `srv_buf_size` must have a reader, so one of
the two is the deviation (with task 1.11).

11.5.6.4 `verbose.log` writes each line before it returns, so that a hard
exit loses nothing, and `exec` writes its start and exit at levels 1 and 2
only.

11.5.6.5 The path from `--root` through `settings.json` to
`tools_register` in `mcp_stdio.py` has no test; the writer named it an
integration rung.

11.5.6.6 Four test names of three words with a protocol name were left:
`test_tools_list_shape`, `test_tools_list_permit`, `test_call_rpc_error`,
`test_call_rpc_bare`.

11.5.6.7 Test modules that import more than their module and the
harness, against the plan's rule that a test module imports only its module
and the test harness: `test_dispatch.py` imports `jslb`; the MCP tests
import `mcp` beside their module and read `API/mcp/tools.json` by path.

11.5.6.8 An existing `line` table's schema is not verified, so a
`_verbose.sqlite` made before the `level` column went keeps it and fails
loud at its first insert; no migration is built.

11.5.7 Seams.

11.5.7.1 `python/main_loop.py`, `python/bootstrap.py` and
`python/echo_loop.py` (task 1.16) route a line carrying `r` before
`line_dispatch`, the reply to `hello` having type `hello`; call `id_next`
once per request sent; catch what `line_dispatch` raises, write
`error_make(line, error)` and exit 1; open the log with `log_open(root,
settings["verbose_ring"])` before the first `log`; run the console's dash
through `exec`. Task 1.16 receives first.

11.5.7.2 The handlers (task 1.15) reply with `reply_make`;
`engine_mcp` passes `jslb.payload_of(line)` to `message_handle`, replies
with the response as the payload and sends nothing on `None`;
`engine_system.tools_register` imports without side effects and without
`mcp_stdio`; `engine_system`'s `settings.put` calls `settings_check`;
`engine_verbose` calls `lines_put`, `tail_get` and `history_get`. Task
1.15 receives first.

11.5.7.3 The settings key set is one set in `settings.json`,
`API/settings.json`, the check of `settings.py`, the `Settings` interface
of `ts/settings.ts` (task 1.21) and `API/ts/settings.d.ts`; a change of a
key is a seam with task 1.21 and a proposed edit for the stubs (6).

11.5.7.4 Fixtures that copy the checkout's `settings.json`: the engine
tests (task 1.15), `python/test_wire.py` (task 1.17),
`python/test_browser.py` (task 1.19). `xsjs_start.ps1` (task 1.11) copies
`settings.json` and `provider.json` into the root.

11.5.7.5 The twins `ts/dispatch.ts` (task 1.22), `ts/mcp.ts` (task 1.25),
`ts/settings.ts` and `ts/verbose.ts` (task 1.21) share this task's
prefixes and texts; a change of a shared text goes to them first, and
their new names come here as requests.

11.6 Task 1.14, the Python substrate.

11.6.1 Owns: `python/substrate.py` and `python/test_substrate.py`. It also
writes every `substrate.` name of the strings file, for both languages: the
TypeScript owner, task 1.24, sends the `substrate.` names it needs to this
task as requests (6.5).

11.6.2 Reads: `API/python/substrate.pyi`, which holds the signatures;
`API/sql/substrate.sql`, `API/sql/metaverse.sql` and `API/sql/verbose.sql`;
`API/ts/lines.d.ts`, for the forwarded lines and their replies;
`ts/substrate.ts` and `API/ts/substrate.d.ts`, the twin (task 1.24); the
callers: the five store handlers `python/engine_kv.py`, `engine_doc.py`,
`engine_db.py`, `engine_turn.py` and `engine_sql.py` (task 1.15),
`python/main_loop.py` (task 1.16), and `python/test_browser.py` (task 1.19),
which writes one value on the server through `Store.kv_put`; `settings.json`
for `overflow_bytes`.

11.6.3 Expected.

11.6.3.1 Purpose: the single door to SQLite on the server, one owner's
databases under one root: the KV accessor, documents, turns, SQL, whole
database images, and the applying side of replication. The browser's
`substrate.ts` emits the forwarded lines after each commit and
`substrate.py` applies them; replication is inside the substrate, not ad
hoc.

11.6.3.2 Public names, as `API/python/substrate.pyi` declares them: the
tuples `KvRow`, `KvValue`, `TurnRow`, `SqlStatement`, `SqlResult` and
`RefParts`; the functions `schema_apply(connection)`, `ref_split(ref)`,
`doc_encode(normal)` and `doc_decode(encoded)`; and `Store(root,
overflow_bytes)` with `db_open`, `db_close`, `db_list`, `db_create`,
`db_drop`, `kv_get`, `kv_put`, `kv_delete`, `kv_list`, `kv_check`,
`doc_get`, `doc_put`, `doc_head`, `turn_append`, `turn_list`,
`turn_compact`, `sql_run`, `db_snapshot`, `db_restore`, `operation_apply`
and `transaction_run`. `Store.seq_get(db) -> int` is an API addition
(11.6.4.2).

11.6.3.3 Engine: Python's `sqlite3` on the system library, with no version
floor and no version check. One connection per database, opened with mode
`rw` and `isolation_level=None`, with the pragmas `foreign_keys=ON`,
`journal_mode=WAL`, `synchronous=NORMAL` and `busy_timeout=5000`; a journal
mode other than `wal` raises `substrate.journal_mode`.

11.6.3.4 A database name is a C identifier, and its file is
`<root>/<name>.sqlite`.

11.6.3.5 The databases of the server: `_settings` (`settings.json` as the
server loaded it, a key to its JSON text), `_preferences` and `_files` (the
engine's schema, which nothing enforces), `metaverse` (with `universe`, the
one fixed experience table), and the universe, world and region databases
the scripts make. `_verbose` is the verbose module's own file, holding only
its `line` table and no substrate table; the substrate does not create it.

11.6.3.6 Tables: `schema_apply` creates `_meta`, `_kv`, `_head` and `_turn`
with the DDL of `API/sql/substrate.sql`, on first use, in every database the
substrate opens, and writes the `_meta` rows `seq` "0" and `schema` "1". The
prefix `_` keeps them apart from the scripts' tables, and the AI never needs
to see them.

11.6.3.7 `_kv` has no type column: what a value is, is the key owner's
business. There is no per row `seq` and no tombstone table, because
replication is by forwarded operations, not by a row log.

11.6.3.8 No protection, by the maintainer's decision that SQL rules are not
a security boundary: no table or database refuses a write; there is no
authorizer; nothing refuses in `operation_apply`, `kv_put`, `kv_delete`,
`turn_append` or `sql_run`; the fixed schemas of `_files`, `_preferences`
and `metaverse` are not enforced. That `_settings` is written by the server
from the file and never by the browser describes behaviour; nothing
enforces it.

11.6.3.9 Key-Value-Refs: `/$db/$key` is external and `$key` internal, inside
the database at hand; `$db` is a C identifier; `$key` is any non-empty UTF-8
text and may contain `/`. `ref_split` returns `RefParts(db, key, version)`,
`db` None for an internal ref, and raises on a bad ref.

11.6.3.10 Document-Refs: a Key-Value-Ref whose key is `$id/$version`: `$id`
is any non-empty UTF-8 text and may contain `/`; `$version` is an integer
literal, the last segment. Nothing else about the shape of `$id` is fixed.

11.6.3.11 Documents: a document is the KV row its Document-Ref names,
holding JSON. `doc_put(db, id, body)` writes version head plus one and moves
`_head` in the same transaction, returning the ref and `seq`;
`doc_head(db, id)` reads `_head` and raises on an unknown id; `doc_get(ref)`
is `kv_get` with a JSON decode and returns the document in its encoded form.
A written version never changes; history is the set of versions; the head is
a primary key lookup.

11.6.3.12 A document's headers follow the JSLB rule of integer keys: 0 is the
document header, `t` its type and `v` its format version, defaults omitted;
1 on are reference strings, Key-Value-Refs and Document-Refs, found by
probing; `{"$ref": n}` anywhere in the body names header n. `doc_encode`
moves every reference string into the headers, sharing equal strings, and
leaves `{"$ref": n}` behind; `doc_decode` puts them back; the round trip is
identical.

11.6.3.13 The engine's one document contract is the scene: type `scene`,
with `subtitle` text and, when there is one, `image`, a reference to a media
row. The hyperposition is `/metaverse/hyperposition/1`.

11.6.3.14 One table, `_kv`, holds documents, blobs and settings, so there is
one overflow path and one replication path.

11.6.3.15 Values: `kv_put(ref, data, db)` takes bytes; a `str` is the path
of a cache file, never text (a rule of section 3); it returns the `KvRow`
and the new `seq`. `kv_get(ref, db)` returns `KvValue(data, size, sha256)`,
`data` the bytes or, over `overflow_bytes`, the cache file's path.
`kv_delete` deletes the row, and its cache file when no other row shares the
hash, and returns `seq`. `kv_list(db, prefix)` returns `KvRow`s. The `db`
argument names the database an internal ref is inside.

11.6.3.16 Overflow: a value over `overflow_bytes`, the setting of 128 KiB,
lives in `<root>/cache/<sha256 hex>` with `data` NULL; a value of exactly
`overflow_bytes` stays in the row. File first, then the row: a crash between
leaves an unreferenced file that `kv_check` removes. The streaming decoder's
file is renamed into place, with no second copy. `sha256` names the file,
detects an unchanged write and lets replication skip bytes the other side
has.

11.6.3.17 `kv_check(db)` removes the cache files no row names and returns
their count.

11.6.3.18 `seq`: `_meta.seq` counts a database's modifying operations and is
incremented in the same transaction as each one; `db_open` returns it, and it
survives a close and a reopen. A new database starts at 0 and `db_create`
leaves it 0 (11.6.4.1).

11.6.3.19 Each forwarded operation but `db.create` and `db.drop` advances the
server's `seq` by one: the browser checks the reply's `seq` as `since` plus
1, a check an earlier coordinator accepted in place of an equality with the
browser's own `seq`.

11.6.3.20 `db_open(name)` opens `<root>/<name>.sqlite`, applying the schema,
and returns its `seq`; `db_close(name)`; `db_list()` returns the open names;
`db_create(name)` creates and opens a new database and raises when the file
exists; `db_drop(name)` closes and deletes a database and its cache files.

11.6.3.21 Transactions: `transaction_run(fn)` runs `fn` inside `BEGIN
IMMEDIATE`, commits on return and rolls back on a raise; the `Store`'s
methods run inside it.

11.6.3.22 SQL: `sql_run(db, statements)` runs each `SqlStatement(sql,
params)` in order, one statement with its bound parameters, never built as a
string, and returns one `SqlResult(columns, rows, changes)` per statement.
DDL is allowed: the AI is the database administrator.

11.6.3.23 Turns: `_turn` rows live in the database of the scene, keyed by
the scene's Document-Ref, `n` counting within the scene, each `content` one
provider message as JSON (checked by `json_valid`). `turn_append(scene,
role, content)` returns `n` and `seq`; `turn_list(scene)` returns the
scene's turns in order; `turn_compact(scene, through, summary)` replaces
turns 1 to `through` with one summary row, role `system`, at `n` 1, and
returns `seq`.

11.6.3.24 The server's substrate never compacts by itself. The browser's
`Store.turn_append`, before it appends a turn of role `user` to a scene that
holds `turn_compact_turns` turns or more, compacts that scene's turns 1 to
its last in the same transaction and forwards the compaction as its own
`turn.compact` before the `turn.append`; the server applies the two lines as
they come.

11.6.3.25 The summary of an automatic compaction is one `i18n` text,
`substrate.turns_compacted`, naming the turns compacted and the count that
reached the threshold and saying their text is no longer in the
conversation. It is written in the browser; its name is this task's to
write.

11.6.3.26 Images: `db_snapshot(db)` returns the `Connection.serialize`
bytes and the database's `seq`. The `db.snapshot` reply carries them as one
blob, at most `blob_max`, with its SHA-256, which the browser checks before
it restores; the reply holds the whole image in memory, at most what
`sqlite3_serialize` allocates.

11.6.3.27 `db_restore(db, data)` replaces the database file by a temporary
file and a rename and returns `seq`; `data` is bytes or a cache file path.

11.6.3.28 Replication: the units are `kv_put`, `kv_delete`, `doc_put`,
`turn_append`, `turn_compact`, `db_create`, `db_drop` and every modifying
`sql_run` commit, each forwarded by the browser as the same line
(`kv.put` with its blob, `kv.delete`, `doc.put`, `turn.append`,
`turn.compact`, `db.create`, `db.drop`, `sql.run`) right after its commit,
in order, one in flight per database. Each carries `since`, the browser's
`seq` before the operation. The copies are deterministic as long as the
statements are.

11.6.3.29 `operation_apply(type, since, **payload)` applies one forwarded
operation when `since` is the database's `seq`: it runs the same operation
and returns the new `seq`. A `since` that is not the database's `seq` raises
with `substrate.since_stale`, "<type>: since <since> is not seq <seq> of
<db>", which reaches the browser as `error`; there the refusal is a desync
fault, and the reload replaces the file.

11.6.3.30 The keyword sets of `operation_apply`, as its writer recorded
them: `kv.put`, `k` (an external ref) and `data` (bytes, or the path of the
decoder's streamed file, which is renamed into the cache); `kv.delete`, `k`;
`doc.put`, `db`, `id` and `body` (the stored form, integer header keys);
`db.create`, `db`; `db.drop`, `db`; `turn.append`, `scene`, `role` and
`content` (the message object, stored as canonical JSON); `turn.compact`,
`scene`, `through` and `summary`; `sql.run`, `db` and `statements` (objects
with exactly `sql` and `params`). Wrong keywords raise `TypeError`; an
unknown type raises `ValueError`.

11.6.3.31 Direction: during play the browser writes and the server backs up;
nothing is pushed from the server while a tab is open; the server is the
source of truth. At start `hello` carries `seq` per database, and where the
browser's differs the browser replaces its file from the server's
`db.snapshot`.

11.6.3.32 Numbers: the substrate writes canonical JSON with `jslb`'s key
rules, applied recursively; an integer beyond plus or minus 2^53 raises, as
the plan's Python encoder refuses larger integers. `substrate.number_refused`
and `substrate.key_refused` name a number and a key that JSON cannot hold.

11.6.3.33 Errors: every message goes through `i18n` with a literal name,
under the prefix `substrate.`. The exception types, as the writer recorded
them: `ValueError` for bad input; `LookupError` for a missing key or id and
a database not open; `RuntimeError` for a desync and for state;
`FileExistsError` from `os.open`; SQLite's own errors pass through.

11.6.3.34 Tests: `python/test_substrate.py` holds `unittest.TestCase`
classes; a test that expects an error compares the message with the `i18n`
text; no test leaves state that another test sees; no test enshrines the
implementation's number where a recorded number exists.

11.6.3.35 The proofs of stage 3, each owed a test: the substrate's tables
created on first use in a new database; KV on both ref forms; documents;
heads; the document round trip; `seq` across a reopen; overflow at exactly
`overflow_bytes`; snapshot and restore; a `SIGKILL` between file and row;
`kv_check`; `operation_apply` of a sequence the test builds;
`turn_compact`. The stage's exit, the suite passing under `python3 -X dev`,
is owed to the testing phase (section 7).

11.6.3.36 The browser's stage 6 ports this suite, and its exit asks for
counts identical to the Python suite's, but for `test_wal_left`, which has
no meaning on the SAH pool and is not ported (approved by the maintainer).

11.6.4 Decided, not a finding.

11.6.4.1 `since` 0 on `db.create` and the database's `seq` on `db.drop`, and
`db_create` leaving `seq` 0, where neither the plan nor the stubs say so:
D1, a new database starts at `seq` 0 and `db_create` leaves it 0, `db.create`
carries `since` 0, `db.drop` carries the database's `seq`, and the reply
`seq` check is skipped for those two. The earlier job removed the counting
of `db_create` to build it. The stub edits were not applied because D1
awaits the maintainer.

11.6.4.2 `Store.seq_get(db)` exists though the stub lacks it: an API
addition the planners hold for the maintainer (section 4.5), because
`operation_apply` returns only `seq` and the `results` of `sql.run`'s reply
would otherwise be lost. Rejected by its writer: `operation_apply` returning
the reply payload, a last result attribute, reading `seq` through
`db_snapshot`.

11.6.4.3 One cache namespace under the root: a cache file is removed, by
`kv_delete`, an overwrite, `db_drop` or `kv_check`, only when no row with
NULL `data` in any database file under the root names it. Open databases are
read through their own connection, closed `<C identifier>.sqlite` files
through a temporary one, and files without `_kv`, such as
`_verbose.sqlite`, are skipped; removal waits for the outermost commit;
`kv_check`'s `db` is only checked as open; one process is assumed. Rejected
by its writer: a cache directory per database, scanning only the open
databases, a reference count table.

11.6.4.4 No `fsync` before the row's commit: "file then row" holds against
a process crash only (the writer's record).

11.6.4.5 `transaction_run` begins lazily: the outermost call owns the
transaction; each connection takes `BEGIN IMMEDIATE` at its first write or
snapshot; every touched connection commits in begin order, or all roll
back; there is no atomicity across databases and no savepoint, so a nested
failure that the caller catches and then commits leaves partial work.
Alternatives recorded and not taken: begin everywhere, savepoints, a failed
flag.

11.6.4.6 A `COMMIT`, `END` or `ROLLBACK` inside `sql_run` ends the
substrate's transaction early, and `transaction_run`'s `COMMIT` then raises.
The one alternative recorded, an authorizer denying only
`SQLITE_TRANSACTION` (which the record says "refuses no write"), is not
built: the review's planners accepted the form, because that authorizer
would refuse statements of the AI, which the project rules forbid between
the AI API and the databases.

11.6.4.7 D18, a reference string's key part holds no white space, as
scoped: only document reference strings exclude white space, their pattern
having no DOTALL; `ref_split` and the external ref pattern keep DOTALL and
allow white space in keys, because the plan allows any non-empty UTF-8 key.

11.6.4.8 A double above 2^53 is stored by the Python substrate, where the
TypeScript store refuses it with `substrate.integer_range`: approved by the
maintainer.

11.6.4.9 One blob per image, by the maintainer's decision that the largest
blob is the largest database: `substrate.SnapshotHead`,
`Store.snapshot_keep`, `Store.snapshot_read`, `engine_db.db_chunk` and the
strings `substrate.piece_none`, `substrate.piece_size`,
`substrate.snapshot_range` and `substrate.snapshot_unknown` are gone;
`substrate.snapshot_digest`, `substrate.cache_unknown` and
`substrate.fill_desync` stay. The design of snapshots in pieces is kept
among the designs not built (4.2).

11.6.4.10 No `PRAGMA max_page_count`: a database that grows past `blob_max`
is not refused, and its image fails loud where it meets a window (the
planners' reading, built, its question open, 4.8.4.14; a bound only the
maintainer can ask for).

11.6.4.11 The server substrate has no database administration measurement;
`db_stats`, `db_compact`, `db_unload` and `db_load` are the browser's. The
server side is unchanged, because the server evicts nothing.

11.6.4.12 The tests of a refusal are gone with the authorizers
(`test_writes_refused`, `test_settings_refused`), by the maintainer's
removal of every protection.

11.6.4.13 A `str` passed to `kv_put` is always a file path, must be over
`overflow_bytes`, and is hashed by reading the file (alternatives recorded:
a `str` as text, a `sha256` parameter).

11.6.4.14 The writer's rules on refs and databases: an internal ref needs
`db`, and an external ref given a `db` raises; a version literal is
`0|[1-9][0-9]*`; C identifiers do not exclude C keywords; `db_open` of a
missing file raises SQLite's `OperationalError`, as only `db_create` makes
files; a second open raises; a partial set of the substrate's tables, or a
`schema` other than "1", raises; `db_close`, `db_drop` and `db_restore` raise
inside a transaction; `db_drop` and `db_restore` raise
(`substrate.wal_left`) rather than delete when a `-wal` file is left;
`db_create` removes its file when `db_open` raises.

11.6.4.15 The writer's rules on documents: a reference string matches
`/<C identifier>/` followed by a non-empty key without white space, and
internal refs stay in the body; header numbers follow first occurrence,
depth first, in insertion order; `doc_encode` and `doc_decode` raise on
malformed headers or `$ref` indexes; `doc_decode` requires every header from
1 on to be a reference string; `doc_put` checks the body with `doc_decode`
and stores it as given, in the encoded form.

11.6.4.16 The writer's rules on turns: the summary row has role `system` and
the content `{"role":"system","content":<summary>}` (alternative recorded:
`assistant`); `through` below 1 raises `ValueError`; nothing deleted raises
`LookupError`; gaps in `n` are kept, and the next append is the largest `n`
plus 1.

11.6.4.17 `SqlResult.changes` is the statement's delta of `total_changes`,
so DDL gives 0 and trigger rows count.

11.6.4.18 `db_restore` writes `<db>.sqlite-restore` with
`O_CREAT|O_EXCL`, checks it through an immutable read only connection before
it closes the live database, and removes it on any raise: prescribed by an
order of the earlier coordinator. The fixed name's consequence after a kill
is a candidate (11.6.6.3).

11.6.4.19 The crash test forks a child that ends every path in
`os._exit(1)` and kills it between file and row; the suite has no timer.

11.6.4.20 The tests assume SQLite behaviours nobody measured, among them that
SQLite deletes `-wal` and `-shm` when the last connection closes:
Unconfirmed, owed to the testing phase.

11.6.4.21 The recorded differences of the TypeScript twin, accepted for the
twins (12.4): it checks a statement's parameter count when preparing
(`substrate.params_count`), catches several statements in one text after
running them (`substrate.statement_many`), and throws on empty SQL, which
Python accepts; numbers past 2^53 give `substrate.integer_range`;
`substrate.key_refused` has no JavaScript case; a top level key "12" is
`header_normal` there and `key_digits` here; its `kv_check` spares a live
sink file.

11.6.4.22 Built later by design (section 4.2), so absent here: content
divergence detection by a per database checksum; snapshots in pieces;
compaction beyond the turn counter; verbose levels in the server. Decided
against (section 4.3): a row log with per row `seq`, tombstones,
`sync.pull` and `sync.push`; turns as documents; separate `doc` and
`doc_head` tables with a fixed Document-Ref depth; `sql_run` guarding the
engine's tables.

11.6.5 Open, for the maintainer.

11.6.5.1 `_cache_prune` skips only `FileNotFoundError` when it removes cache
files. An order of the earlier coordinator prescribed the skip, and an
earlier reviewer recorded it as swallowing an error, against the project
rules' ban on fallbacks. By the precedence of section 5, a decision that
breaks a project rule is open: the skip as prescribed, or the error raised.
The review chooses neither.

11.6.6 Candidates.

11.6.6.1 `python/substrate.py`, the branch raising `substrate.transaction_none`
("A substrate write ran outside transaction_run."): an earlier reviewer
listed it among branches for cases that cannot happen. To check: whether any
write can run outside `transaction_run`; a branch for a case that cannot
happen breaks the ban on fallbacks.

11.6.6.2 `python/test_substrate.py`: `_DESYNC_MESSAGE`, the literal
"kv.put: since 3 is not seq 4 of _files", is compared as a literal where the
test rule asks for the `i18n` text of `substrate.since_stale`; and the
replay test's `seq` start state was kept from the deleted transcripts and
never verified, reached by writing `_meta.seq` directly because the
`universe` DDL counts. Expected: the message built with `i18n`, and a
sequence the test builds.

11.6.6.3 `Store.db_restore`: the fixed restore name with `O_EXCL` makes a
restore after a `SIGKILL` raise `FileExistsError` until the file is removed
by hand (alternatives recorded: a uuid name, `mkstemp`). The TypeScript twin
throws `substrate.restore_left` for a leftover file, its writer's record.

11.6.6.4 Each proof of stage 3 (11.6.3.35) has its test in
`python/test_substrate.py`; a proof with no test is severity 4.

11.6.6.5 `Store.db_restore` brings no cache files, so a restored image may
name cache files the server lacks; its writer recorded "the design for that
is open", and no later record gives one for the server.

11.6.7 Seams.

11.6.7.1 With task 1.15: the five store handlers call `operation_apply`,
`seq_get`, `transaction_run` and the `Store`'s methods and build their reply
fields from them. A change of what a method takes, returns or raises goes to
task 1.15 as a request with `Seam: pending`; task 1.15 receives first.

11.6.7.2 With task 1.16: `main_loop.loop_prepare` opens, writes `_settings`
and seeds through the `Store` inside `transaction_run`, and builds the
`hello` map from `db_open`, `db_list` and `seq_get`; task 1.16 receives
first.

11.6.7.3 With task 1.19: `python/test_browser.py` writes a value of
`blob_max` plus one bytes on the server through `substrate.Store.kv_put` with
a file path, approved by the maintainer; a change of that path goes to task
1.19 first.

11.6.7.4 With task 1.24, the twin: `ref_split`, `doc_encode`, `doc_decode`,
canonical JSON, `seq`, overflow at exactly `overflow_bytes`, `turn_compact`
and its summary, and `operation_apply` against each forwarded line behave
alike in both languages (task 1.4 reviews them, 12.4). A change on one side
goes to task 1.24 as a request; task 1.24 receives first.

11.6.7.5 With task 1.24 and task 1.8 (12.6): the browser's port of this
suite keeps identical counts, so a test added or removed here is sent to
task 1.24, the steward of `ts/test_substrate.ts`.

11.6.7.6 Strings: this task writes the `substrate.` names that task 1.24
requests. `substrate.since_stale` and `substrate.scene_bad` are also used by
`engine_sql` and `engine_turn` (task 1.15), so a rewording reaches them.

11.7 Task 1.15, the Python engine handlers.

11.7.1 Owns: `python/engine_kv.py`, `python/engine_doc.py`,
`python/engine_db.py`, `python/engine_turn.py`, `python/engine_sql.py`,
`python/engine_verbose.py`, `python/engine_tap.py`, `python/engine_mcp.py`,
`python/engine_system.py`; their nine tests `python/test_engine_kv.py`,
`test_engine_doc.py`, `test_engine_db.py`, `test_engine_turn.py`,
`test_engine_sql.py`, `test_engine_verbose.py`, `test_engine_tap.py`,
`test_engine_mcp.py` and `test_engine_system.py`; and the `i18n` prefixes
`engine_kv.`, `engine_doc.`, `engine_db.`, `engine_turn.`, `engine_sql.`,
`engine_verbose.`, `engine_tap.`, `engine_mcp.` and `engine_system.`.

11.7.2 Reads: `API/ts/lines.d.ts`, the wire rows; the nine stubs
`API/python/engine_*.pyi`; `API/python/dispatch.pyi`; `API/mcp/tools.json`,
the two server tools; `python/substrate.py` (task 1.14); `python/dispatch.py`,
`python/mcp.py`, `python/mcp_stdio.py`, `python/verbose.py` and
`python/settings.py` (task 1.13); `python/jslb.py` (task 1.12);
`python/main_loop.py`, which registers the handlers, and the options of
`python/bootstrap.py` (task 1.16); the forwarded lines of `ts/substrate.ts`
(task 1.24); `python/test_wire.py` (task 1.17), whose stage 4 rungs drive
these handlers.

11.7.3 Expected.

11.7.3.1 The handlers of `API/ts/lines.d.ts` on the server, one module per
namespace: `kv.*`, `doc.*`, `db.*`, `turn.*`, `sql.*`, `verbose.*`,
`tap.line`, `mcp`, and in `engine_system` `settings.put`, `source.put` and
`system.restart`. Each stub `API/python/engine_<namespace>.pyi` holds its
functions, the payload as keyword parameters.

11.7.3.2 The dispatcher calls `fn(line, **payload)`, so a handler reads its
first blob as `line[1].d`: the bytes, or for a blob over `overflow_bytes`
the path of its streamed file under `<root>/cache/`, which the handler moves
or links.

11.7.3.3 A handler of a request returns a finished reply line built with
`dispatch.reply_make(line, blobs, **payload)`; a handler of a notification
returns None.

11.7.3.4 Registration: every module has `handlers_register(...)`, an API
addition the planners hold for the maintainer (section 4.5), and
`engine_system` has `tools_register(server, root, debug)`, the one place the
server's MCP tools are registered, used by `main_loop` and by `mcp_stdio`.
The records name `handlers_register(store)` for the five store modules and
`handlers_register(server)` for `engine_mcp`.

11.7.3.5 Each module keeps what it was registered with in a private holder
class with a two word name, `_StoreState` in the five store modules,
`_VerboseState`, `_TapState`, `_McpState` and `_SystemState`, and one
`_STATE` instance.

11.7.3.6 A forwarded operation carries `since`. Its handler, inside one
`transaction_run`, refuses a `since` that is not the database's `seq` by
raising with `substrate.since_stale`, else runs the same substrate operation
and replies with the new `seq`. Nothing refuses a write to any table or
database.

11.7.3.7 `engine_kv`: the ref is the line header's `k`, and a line without
it raises `engine_kv.key_missing`. `kv.get` replies `size` and `sha256` with
the value as one blob; `kv.put` takes one blob, is forwarded with `since`
and replies `sha256` and `seq`, a missing blob raising
`engine_kv.blob_missing`; `kv.delete` is forwarded with `since` and replies
`seq`; `kv.list {db,
prefix}` replies `keys`, each `{k, size, sha256}`. A SHA-256 in a payload is
64 lowercase hex characters.

11.7.3.8 `engine_doc`: `doc.put {db, id, body, since}` is forwarded and
replies `ref` and `seq`; the body arrives with integer header keys, because
`jslb` turns nested digit keys into integers, and is stored in its encoded
form. `doc.head {db, id}` replies `ref`.

11.7.3.9 `engine_db`: `db.create {db, since}` and `db.drop {db, since}` are
forwarded and reply Empty; `db.snapshot {db}` replies `sha256` and `seq`
with the database file as one blob, at most `blob_max`. There is no
`db.chunk`.

11.7.3.10 `engine_turn`: `turn.append {scene, role, content, since}` is
forwarded and replies `n` and `seq`; `content` is the provider message
object, stored as canonical JSON in the database of the scene, and the scene
must be an external Document-Ref (`substrate.scene_bad`). `turn.compact
{scene, through, summary, since}` is forwarded and replies `seq`.

11.7.3.11 The server applies both forwarded `turn.compact` and
`turn.append`, and never compacts by itself: compaction at
`turn_compact_turns` runs in the browser, which forwards `turn.compact`
before the `turn.append` that caused it.

11.7.3.12 `engine_sql`: `sql.run {db, statements, since}` is a forwarded
commit of statements, each `{sql, params}`, and replies `results`, each
`{columns, rows, changes}`, and `seq`. Inside one `transaction_run` it checks
`since` against `Store.seq_get`, runs `Store.sql_run` and reads `seq_get`
again.

11.7.3.13 `engine_verbose`, `verbose.put {thread, lines}`: a push from the
page, debug mode only (`engine_verbose.debug_off` otherwise); `thread` is
`ui` or `ai`; each line is exactly `{at, text}` with exact types
(`engine_verbose.line_invalid` otherwise); the lines go to `_verbose`
through `verbose.lines_put`.

11.7.3.14 `engine_verbose`, `verbose.tail {thread, count}`: replies `lines`,
each `{at, text}`; for `server` the server's ring through
`verbose.history_get`, for `ui` and `ai` through `verbose.tail_get` (D13,
`verbose.tail_get(thread, count)` serves `ui` and `ai`). It is not gated on
`debug`.

11.7.3.15 `engine_tap`, `tap.line {language, text}`: a push; `language` is
`python` or `typescript` (`engine_tap.language_unknown` otherwise); the
handler appends `text` and a newline to `<root>/tap/<language>.tap`,
unbuffered, so a hang leaves the lines before it on disk.

11.7.3.16 `engine_mcp`, `mcp`: the payload is a JSON-RPC message for the
server's `mcp.Server`; `mcp_message` passes `jslb.payload_of(line)` to
`Server.message_handle`, replies with the returned object as the payload
through `reply_make`, and sends nothing on None.

11.7.3.17 `engine_system`, `settings.put {settings}`: debug mode only; it
checks the value as the settings check does, rewrites `<root>/settings.json`
(indent 2, a trailing newline, written by a rename) and replies Empty; the
server rereads the file at the next `hello`.

11.7.3.18 `engine_system`, `source.put {name}` with one blob: debug mode
only; it writes the blob as `<root>/main_loop/<name>`, `name` a plain file
name ending `.py` (`engine_system.name_invalid` otherwise), moves a streamed
file with `os.replace`, and replies `sha256`; no blob raises
`engine_system.blob_missing`.

11.7.3.19 `engine_system`, `system.restart {main_loop}`: a push, debug mode
only; it requires `<root>/main_loop/<main_loop>`
(`engine_system.main_loop_missing`), then execs Python itself with
`os.execv(sys.executable, ...)` on `sys.orig_argv`, every two token
`--main-loop <x>` removed and `--main-loop <main_loop>` appended, keeping its
pid; the new process writes a new `hello` (D9, a second `hello` after
`system.restart` is a fault ending in Reload on the page).

11.7.3.20 The debug gate: `settings.put`, `source.put`, `system.restart` and
`verbose.put` raise when the setting `debug` is false;
`engine_system.debug_off` names the operation.

11.7.3.21 The server tools, as `API/mcp/tools.json` lists them: `source_put
{name, text}` and `system_restart {main_loop}`, debug mode only, with no
permit mark, so the AI calls them without asking, over the line and over
stdio. A missing or non text argument raises `RpcError` -32602 with
`engine_system.argument_invalid`; `source_put`'s result is one text block
`{"sha256":"<hex>"}`.

11.7.3.22 Errors: every message goes through `i18n` with a literal name,
under the module's prefix. A handler's raise reaches `main_loop`, which
writes the one `error` line and exits 1; an unknown type gives `error`, then
exit 1.

11.7.3.23 Tests: each `test_engine_<namespace>.py` holds `unittest.TestCase`
classes; a test that expects an error compares the `i18n` text; no test
leaves state that another test sees.

11.7.3.24 The proofs of stage 4 that reach these handlers, carried by
`python/test_wire.py` (task 1.17) and a stdio MCP client written in a test
(task 1.13): `kv.put` and `kv.get` byte identical; `doc.put` and
`doc.head`; `verbose.tail`; `tools/list` and `tools/call` over stdio and
over the `mcp` line; an unknown type giving `error` then exit 1;
`system.restart` serving a second main loop after `source.put` in debug
mode, and the same refused without it; an operation sequence the test builds
replayed over the wire. The stage's exit adds pyright clean, owed to the
testing phase.

11.7.4 Decided, not a finding.

11.7.4.1 `db_create` and `db_drop` take `since`, which
`API/python/engine_db.pyi` and the `DbName` of `API/ts/lines.d.ts` lack: D1,
a new database starts at `seq` 0, `db.create` carries `since` 0 and
`db.drop` the database's `seq`. The stub edits were not applied because D1
awaits the maintainer.

11.7.4.2 `doc_put`'s `body` is `dict[int | str, Any]` where the stub has
`dict[str, object]`: a stub departure the earlier writer recorded for the
maintainer, as the body arrives with integer header keys.

11.7.4.3 The `_*State` holders, accepted by the review's planners: their two
word names answer the maintainer's reviewer, who found `_State` in nine
modules against the two word rule. Whether their `not_registered` checks can
be reached is a candidate (11.7.6.2).

11.7.4.4 `source_put` and `system_restart` carry no permit: by the
maintainer's rule that nothing between the AI API and the databases asks or
refuses; the stdio refusal of a permit tool is gone, and `test_permit_absent`
proves the mark absent.

11.7.4.5 `system_restart` called over stdio execs the stdio process with
`--main-loop`, which `mcp_stdio`'s parser refuses (exit 2, no reply): kept
so that it fails loud. Options recorded and not taken: not registering it
on stdio, `mcp_stdio` accepting `--main-loop`, a stdio tool restarting the
engine server found through the root.

11.7.4.6 No flush before `os.execv` and no `blob_invalid` branch in
`source.put`: both removed, answering the maintainer's reviewer on flushes
with nothing to flush and on branches that can never run.

11.7.4.7 `verbose.put`'s lines carry `at` and `text` only, and a line with a
`level` is refused: by the maintainer's decision the server and the runtime
have no verbose level. D21, no failure stack is written to `_verbose`.

11.7.4.8 The check of `settings.put` runs in a helper, because `settings` is
also the keyword's name; strict types refuse a `bool` where an `int` is
wanted.

11.7.4.9 `engine_tap` never truncates a `.tap` file: the owner of a run
removes it first (its writer's record).

11.7.4.10 `engine_turn` checks the scene through `substrate.ref_split` and
reuses `substrate.scene_bad` (alternative recorded: an API addition
`substrate.scene_database(scene)`), and calls `Store.turn_append` after it
checks `since` against `seq_get`, not through `operation_apply`.

11.7.4.11 The tests' `TypeError` patterns rely on CPython's `namedtuple`
messages, SQLite's raises are matched by their text, and per step dumps open
the WAL file with a second connection: the writer's records, accepted as
assumptions.

11.7.4.12 The test names that say "recorded", `_RECORDED`,
`test_recorded_replay` and `TestRecorded`, name each test's own sequence, as
the earlier job recorded when the transcripts were deleted. With the
protections, their tests went; the input validation tests stayed.

11.7.4.13 `test_engine_tap`'s `test_run_replay` runs a constant TAP run of
the plan's stream shape; `test_engine_mcp`'s `test_session_opened` builds
the expected replies from the pinned revision and the server entries of
`API/mcp/tools.json`, with ids the test chooses.

11.7.4.14 Built later by design (section 4.2), so absent here: a sleeping
task on the server; server side image fetching with `image.fetch`;
`verbose.follow`, `verbose.line` and `verbose.dump`; a debug `sql.run`
against a server database for recovering the server; line types versioned
by handler; verbose levels in the server. Decided against (section 4.3): a
Python `engine_console.py` and console line types; the `log` namespace and
`engine_log.py`; the tools `script_put`, `script_get`, `script_list`,
`universe_create`, `world_create`, `region_create`, `player_switch` and
`scene_enter`.

11.7.5 Open, for the maintainer.

11.7.5.1 `engine_turn` builds its canonical text with `json.dumps(...,
ensure_ascii=False, separators=(",", ":"), allow_nan=False)`, which lacks
the substrate's private check that integers stay within 2^53 (the plan notes
that `json.dumps` writes larger integers unchanged), and its text can differ
from the substrate's in key order. Options recorded: an API addition
`substrate.json_canonical(value)`, owned by task 1.14; keeping
`operation_apply` and the O(N) `turn_list`; `MAX(n)` through `sql_run`,
recorded as a layering breach.

11.7.5.2 `engine_sql` and `engine_turn` read `seq` before the lazily taken
write lock, which is sound only under the single process model. The
planners left it open; no option is recorded.

11.7.5.3 A tool's exception, the `debug` false raise among them, becomes a
JSON-RPC -32603 response and the server keeps running: a decision of the
earlier writer that an earlier reviewer reported as breaking fail fast. Task
1.13 lists it (11.5); this task changes nothing for it.

11.7.5.4 Where and when compaction runs, open with its built option,
which the review keeps (5.1): in the browser's substrate before a `user`
turn is appended at the threshold, forwarded as `turn.compact` before
`turn.append`, so that the server applies both and never compacts by
itself (11.7.3.11); other: in `agent.ts`, at the end of each turn. The
agent lists it and changes nothing.

11.7.6 Candidates.

11.7.6.1 Restart: `_argv_make` in `python/engine_system.py` removes only
the two token `--main-loop x` and appends its own, so a `--main-loop=x`, or
an abbreviation the parser accepts, stays, while D10 (a repeated `--root` or
`--main-loop` is an error, and `--main-loop` is refused outside debug mode
and with the console role) makes `bootstrap.py` refuse the repeat: a
restart from such a command line fails. The writer of `bootstrap.py`
expected `system.restart` to exec with each option once. Seam with task
1.16 (11.7.7.1).

11.7.6.2 `engine_system.option_unfinished`, raised for a trailing
`--main-loop` with no value, is kept although the parser refuses that at
start; and the nine `not_registered` checks raise for a handler called
before its registration. An earlier reviewer listed both among branches for
cases that cannot happen.

11.7.6.3 Both forwarded `turn.compact` and `turn.append` have their handler
and their test.

11.7.6.4 `python/test_engine_kv.py`: the `sha256` literals were kept from the
deleted transcripts and never verified, where `hashlib` can compute them in
the test (the alternative recorded): S.

11.7.6.5 `python/test_engine_system.py`: `_main_loop_write` has three words,
against the two word rule.

11.7.6.6 `engine_tap.tap_line` opens the file with `"ab"` and default
buffering for each line and then closes it, where the plan says the server
appends each line unbuffered; its writer recorded the change as one line,
`buffering=0` with a check of the count written.

11.7.6.7 `source.put` writes through a fixed temporary name `<target>.tmp`,
with no `fsync`, and a failed write leaves the temporary file (its writer's
record).

11.7.6.8 The plan named the tool `source_put {name}`, where
`API/mcp/tools.json` and the code take `{name, text}` (an earlier
reviewer's finding). Task 1.1 lists the difference for the maintainer
(12.1.5.2); this task changes nothing for it.

11.7.7 Seams.

11.7.7.1 With task 1.16, the restart: a fix in `_argv_make` alone is this
task's; when the parser of `bootstrap.py` must change, the request goes to
task 1.16, which receives first.

11.7.7.2 With task 1.14: the five store handlers rest on the `Store`'s
methods, `seq_get` and `transaction_run`; a change needed there goes to task
1.14, which receives first. `substrate.since_stale` and
`substrate.scene_bad` are task 1.14's names.

11.7.7.3 With task 1.16: `main_loop` calls every `handlers_register`, and
`engine_system.tools_register(server, root, debug)` before
`engine_mcp.handlers_register(server)`; a change of a registration
signature goes to task 1.16 first.

11.7.7.4 With task 1.13: `dispatch.reply_make`, `mcp.Server`, `RpcError`,
`verbose.lines_put`, `tail_get`, `history_get` and the settings check; and
`mcp_stdio` registers the two tools through `tools_register`. A change
needed there goes to task 1.13 first.

11.7.7.5 With task 1.17: the stage 4 rungs of `python/test_wire.py` compare
these replies; a change of a reply's shape goes to task 1.17 first.

11.7.7.6 With task 1.24: the forwarded lines and their `since` come from
`ts/substrate.ts`; a change of a forwarded payload is a change of the line
contract, which task 1.3 reviews (12.3), and goes to task 1.24 first.
`API/ts/lines.d.ts` calls `mcp` a push while both sides send requests and
`engine_mcp` replies: task 1.3's candidate, an edit proposed for the stub.

11.8 Task 1.16, the Python platform and the seeds.

11.8.1 Owns: `python/main_loop.py`, `python/test_main_loop.py`,
`python/bootstrap.py`, `python/test_bootstrap.py`, `python/echo_loop.py`,
`python/stall_loop.py`, `python/seed/hyperposition.json`,
`python/seed/prompt.json`, `python/seed/provider_script.json`,
`python/seed/bootstrap.js`, and the `i18n` prefixes `main_loop.`,
`bootstrap.` and `echo_loop.`.

11.8.2 Reads: `API/python/main_loop.pyi` and `API/python/bootstrap.pyi`;
`API/sql/metaverse.sql` and `API/sql/verbose.sql`; `API/ts/lines.d.ts`
(`hello`, `error`, `Hello`, `ProviderInfo`); `API/mcp/tools.json`, the tools
the prompt names; `settings.json` and `provider.json`;
`python/engine_system.py` (task 1.15); `python/verbose.py`,
`python/settings.py`, `python/dispatch.py` and `python/mcp.py` (task 1.13);
`python/jslb.py` (task 1.12); `python/substrate.py` (task 1.14);
`ts/worker_ai.ts` (task 1.28), the reader of `hello` and of the Script;
`ts/agent.ts` and `ts/script.ts` (task 1.26), the reader of the prompt
documents and the runner of `bootstrap.js`; `ts/provider_script.ts` (task
1.25); `python/test_wire.py` (task 1.17) and `python/test_browser.py` (task
1.19), which start `echo_loop.py` and `stall_loop.py` with `--main-loop`.

11.8.3 Expected.

11.8.3.1 `bootstrap.py` is the platform service around the main loop:
arguments and role, the engine lock, raw mode, `hello`, choosing and loading
the main loop file, restart, and the console. The plan calls it "Immutable
outside debug mode". The previous design's `put`, `ls`, forked modules and
command loop are gone.

11.8.3.2 Its one public name is `bootstrap_run(argv) -> int`
(`API/python/bootstrap.pyi`), which returns the exit code.

11.8.3.3 The command: ttyd runs `python3 bootstrap.py --root <root>` with
`--url-arg`; a connection to `/ws?arg=console` appends the role `console`;
no role is the engine, on tty 1. Player roles are a door (section 4.2).

11.8.3.4 Options: `--root <root>`; `--main-loop <name>`, a file in
`<root>/main_loop/` (a bad name raises `bootstrap.main_loop_name`), refused
outside debug mode and with the console role (`bootstrap.main_loop_refused`);
a repeated `--root` or `--main-loop` raises `bootstrap.option_repeated`.
These are D10, which is exactly these refusals.

11.8.3.5 Debug mode is the setting `debug` of the root's `settings.json`,
never a flag of the command.

11.8.3.6 The engine role takes `<root>/engine.lock` with `flock`; when it
cannot, it writes `error` (`bootstrap.lock_held`) and exits 1, so a second
engine connection on one root is refused.

11.8.3.7 The engine role puts its pty in raw mode with `tty.setraw`, on fd
0, before it writes anything, and then speaks JSLB.

11.8.3.8 The provider: D8, `XSJS_PROVIDER_KEY` is required only when
`provider.scripted` is false (`bootstrap.provider_unset`). When
`provider.scripted` is false, bootstrap reads `<root>/provider.json` and
refuses a missing file (`bootstrap.provider_missing`), a non object or keys
other than `base_url`, `chat_model` and `image_model`
(`bootstrap.provider_keys`), and an empty or non string value
(`bootstrap.provider_empty`); when it is true the file is never read. Both
checks run before the main loop file loads.

11.8.3.9 The order: `loop_prepare(root)` once, before `hello`; then `hello`
and its reply; then `loop_run(read_fd, write_fd, root)`. Bootstrap owns the
whole `hello` exchange, and the main loop never sees it.

11.8.3.10 `hello` is the server's request with `i` 1, carrying `bootstrap`,
`sha256`, `pid`, `root`, `settings` (the root's `settings.json`
unmodified), `seq` per server database (the map `loop_prepare` returns,
`_verbose` left out), `provider_key` always, and `provider_info {base_url,
chat_model, image_model}` last, only when `provider.scripted` is false. It
carries no `python`, `sqlite` or `debug` field and no settings digest.

11.8.3.11 The reply to `hello` is empty. Bootstrap reads it with a decoder
built from the settings it sends, `LineDecoder(line_max, blob_max,
overflow_bytes, sink_make)`, and checks it by its fields in either name
form: a reply with a blob raises `bootstrap.reply_blob`, the end of input
`bootstrap.reply_closed`, any other line `bootstrap.reply_unexpected` with
the line rendered and the hello's id.

11.8.3.12 Headers use full names in debug mode and short names otherwise.

11.8.3.13 The main loop file: the stock `python/main_loop.py` beside
`bootstrap.py`, or `<root>/main_loop/<name>` with `--main-loop` in debug
mode. It is loaded by `SourceFileLoader` with `cast`, registered as
`sys.modules["main_loop"]` and run by `compile` and `exec` of its source; a
file without `loop_prepare` or `loop_run` raises `bootstrap.loop_missing`.
Every replacement main loop defines both.

11.8.3.14 Bootstrap imports nothing of the engine but the main loop file and
the stable modules `jslb`, `settings`, `verbose` and `i18n` (a decision of
the earlier coordinator).

11.8.3.15 Exit codes at the seam with the main loop: a `SystemExit(1)` from
`loop_run` passes with no second `error` line; a raise from `loop_prepare`,
or an early raise from `loop_run`, gets bootstrap's `error` line and exit 1;
a normal return exits 0.

11.8.3.16 The log: bootstrap opens `_verbose` for both roles before running
them; on a crash it logs `bootstrap.run_failed` with the message, not the
stack (D21, no failure stack is written to `_verbose`), then writes the
`error` line and exits 1. When `debug` is true it logs
`bootstrap.hello_submit` with the hello's header JSON only, and never
otherwise.

11.8.3.17 The console role: when `debug` is true it runs `/bin/dash`
through `verbose.exec` at the setting `verbose_level`, `["/bin/dash", "-v"]`
its level 2 form, with a scrubbed environment and the root as working
directory, and exits with dash's code; when `debug` is false it exits 1 and
ttyd closes the connection. Its pty stays cooked, so it echoes.
`verbose_level` is read by the console role alone.

11.8.3.18 `verbose.exec`'s levels are the shell's: 0 runs `argv` with its
output passed through; 1 does the same and writes its start and exit to the
log; 2 runs `argv_verbose` raw and writes the same two lines.

11.8.3.19 No Python line type exists for the console: the server side of tty
0 is ttyd and dash.

11.8.3.20 Restart: after `system.restart` execs Python in the same pid with
the new `--main-loop`, bootstrap runs again and writes a second `hello`; the
engine lock is released at that exec.

11.8.3.21 The root: `<root>/python/bootstrap.py` and `<root>/i18n/`
(11.8.4.15), with `main_loop/`, `settings.json`, `provider.json`,
`engine.lock`, `tap/`, the databases and `cache/`; start copies the
package, the settings, `provider.json` and the seeds there.

11.8.3.22 `main_loop.py` is the select loop and the stock dispatcher, and is
replaceable: one Python process per engine connection, no threads, no
asyncio. The server holds no queue and dispatches one line at a time.

11.8.3.23 Its public names: `loop_run(read_fd, write_fd, root)`
(`API/python/main_loop.pyi`: reads the pty, decodes, dispatches, writes each
reply), and `loop_prepare(root) -> dict[str, int]`, an API addition
(11.8.4.1).

11.8.3.24 `loop_prepare` runs once per process, before `hello`, after
bootstrap has opened the log (11.8.3.16): it loads `settings.json`, opens or
creates `_settings`, `_preferences`, `_files` and `metaverse`, writes
`_settings` with one KV row per top level key holding its JSON text, reopens
every other `.sqlite` of the root whose name is a C identifier, `_verbose`
excepted, seeds (11.8.3.30 and 11.8.3.31), and returns the `seq` of each open
database, in `db_list()` order.

11.8.3.25 `loop_run` registers the handlers of every engine module, builds
`mcp.Server("xsjs-server", "0")`, calls `engine_system.tools_register(server,
root, debug)` before `engine_mcp.handlers_register(server)`, and decodes with
`LineDecoder(line_max, blob_max, overflow_bytes, sink_make)` from the
settings, its streamed blobs written as files under `<root>/cache/`, on the
root's file system, so that a handler can rename them into the cache.

11.8.3.26 It writes each reply line and its blobs to the pty. `chunk_bytes`,
1 MiB, is the size of each `os.read` the server makes; it is not `blob_max`,
because each read is allocated whole (approved by the maintainer).

11.8.3.27 A line with `r` raises `main_loop.reply_unknown`: an unknown `r`
is a hard error, and the one reply the server awaits, the one to `hello`, is
bootstrap's. With D4 (the lines completed before a fault are returned and
the fault is raised by the next feed; `LineDecoder.idle()`; end of input
when not idle is a hard error) the loop dispatches the lines of each read,
then feeds `b""`; end of input inside a message raises
`main_loop.input_partial` as a `jslb.WireError`.

11.8.3.28 A handler that raises produces one `error` line,
`dispatch.error_make(line, error)`, with `r` when the request had `i`, and
`message` and `stack`, written and flushed before exit 1;
`main_loop.serve_failed` is logged first, always, with the message only.

11.8.3.29 When `debug` is true the loop logs `main_loop.line_dispatch` and
`main_loop.line_reply` with each line's header JSON only, and never
otherwise.

11.8.3.30 Seeding the metaverse: while `metaverse` is at `seq` 0,
`loop_prepare` writes the `_files` row `script/bootstrap.js` from
`python/seed/bootstrap.js`, then seeds `metaverse` in one `transaction_run`:
the `universe` table of `API/sql/metaverse.sql`, the documents
`hyperposition` and `prompt` from `python/seed/<id>.json`, and the KV rows
`player` = `player`, `world` = `metaverse` and `scene` =
`/metaverse/hyperposition/1`. A seed file that is not a valid document
raises `main_loop.seed_invalid`.

11.8.3.31 The `_files` row `provider/script.json` is written from
`python/seed/provider_script.json` when the row is missing
(`main_loop._provider_seed`).

11.8.3.32 The engine reads `/metaverse/player`, the player in use, and
`/metaverse/world`, the database of the current world; the Document-Ref in
`/$world/scene` is the scene it renders. The plan marks the player row and
the `universe` row's shape `(name, title, player, world)` Unconfirmed.

11.8.3.33 The seeds are repository files `python/seed/<id>.json`, each a
document in its encoded form, with the script beside them (Unconfirmed in
the plan).

11.8.3.34 `python/seed/hyperposition.json` holds the hyperposition document:
type `scene` and the `subtitle` "How can I help you?", the player's starting
remark, with no `image`, so the page shows black; as written,
`{"0":{"t":"scene"},"subtitle":"How can I help you?"}`.

11.8.3.35 `python/seed/prompt.json` holds the analyst's prompt document, id
`prompt` in `metaverse`, type `prompt` with one `text` member: the system
prompt of every turn, before the current universe's own prompt document when
the scripts have made one.

11.8.3.36 The prompt's text, as the earlier writers recorded it: the
analyst's character and scene, its task and admin control; the vocabulary
and the `player`, `world` and `scene` rows; every tool of
`API/mcp/tools.json` by name with the `browser.` and `server.` prefixes; how
to show a scene; the bootstrap script with its arguments and return value.

11.8.3.37 The prompt also says: that a universe may have its own document
`prompt`, of type `prompt` with its text in `text`, in the database named by
the `universe` row whose `world` is `/metaverse/world`, and that it follows
this one when it exists; that the final reply with no tool calls ends the
turn and its text goes back to the page as the `subtitle` of the reply; that
a script is a function body run with `engine` and `args`, whose `return` is
the value of `script_run`; that `engine.store.kv_put` takes bytes
(`TextEncoder`), that `kv_get(ref).data` is bytes (`TextDecoder`), and that a
string in place of bytes is a cache handle.

11.8.3.38 The prompt also says: that `console_run`, `source_put` and
`system_restart` need debug mode and only `console_run` asks the player; the
database administration (the browser's copies and the server's databases,
`db_soft_bytes` refusing nothing, the one system message holding the
`db_stats` JSON, the AI deciding to unload, compact, drop or
`turn_compact`, the four `browser.` database tools, `turn_compact` reached
through a script as `engine.store.turn_compact`, and `metaverse` and the
current world's, universe's and scene's databases kept loaded); and that
compaction is automatic at `turn_compact_turns`.

11.8.3.39 The prompt does not say that any table refuses a write, holds no
compaction estimate message, and names no `verbose_level` tool: all three
are gone.

11.8.3.40 `python/seed/provider_script.json` holds the scripted provider's
Script, one node and no replies, which the page reads from
`/_files/provider/script.json`; input on a root without a test driver
therefore faults. The Script must stay at or under `overflow_bytes`, because
the worker reads it as text with no fetch on a miss: one of the findings of
4.7.14, which the fetch on a miss of 2.10.7 settles, so it stays the
candidate 11.20.6.2 of the worker's area.

11.8.3.41 `python/seed/bootstrap.js` is the plan for the administration,
seeded as `/_files/script/bootstrap.js` and edited by the AI like any
script: it creates a universe database and its `world` table, a world
database and its `region` table, a region database, writes the `universe`
row and `/metaverse/world`, and with its options writes `/metaverse/player`
and enters a scene. The defaults are `current_universe` for the universe and
`world` for the world, each name a C identifier. The engine seeds nothing in
a universe, world or region database, and the schema of those tables is the
scripts'.

11.8.3.42 The script, as its writer recorded it: synchronous; it returns
`{universe, world, region}`, with `scene` when it enters one; the option
`args.player` writes `/metaverse/player`; the option `args.scene {id,
subtitle, image?}` writes the scene document in the region database and
`/<world>/scene`; the order is the `universe` row, the scene document and
`/<world>/scene`, `/metaverse/player`, then `/metaverse/world` last; the
`universe` row's `player` is `args.player`, else the decoded text of
`/metaverse/player`; its `store.kv_put` calls pass `TextEncoder` bytes.

11.8.3.43 `python/echo_loop.py`, the test main loop of the wire test:
`loop_prepare` makes `<root>/cache` and returns `{}`; `loop_run` registers
`echo_reply` for the type `echo`, version 0, which answers with the payload
and the bytes of each blob; a fault writes one `error` line and exits 1; end
of input inside a message raises `echo_loop.input_partial`; its decoder is
`LineDecoder(line_max, blob_max, overflow_bytes, sink_make)`.

11.8.3.44 `python/stall_loop.py`: a fixture main loop whose `loop_prepare`
never returns, for the browser rung "stage 5: wire hello timer".

11.8.3.45 Tests: `python/test_main_loop.py` and `python/test_bootstrap.py`
hold `unittest.TestCase` classes; messages are compared with their `i18n`
text; no test leaves state that another test sees.

11.8.3.46 The proofs that reach this area, carried by other runners: stage
2's `hello`, `echo` and "second connection refused" (task 1.17); stage 4's
main loop download and restart, `system.restart` serving a second main loop
after `source.put` in debug mode and refused without it (task 1.17); stage
7's console role refused outside debug mode, `echo` through dash and `^C`
ending `sleep 600` (task 1.19); stage 8's seeds and `script/bootstrap.js`
end to end, and the root "fresh", whose rung "stage 8: fresh root" proves
the page load, `hello`, the seeded Script and a first render with no fault
(task 1.19).

11.8.4 Decided, not a finding.

11.8.4.1 `loop_prepare` before `hello`, an API addition the planners hold
for the maintainer (section 4.5): a decision of the earlier coordinator,
because `hello` carries `seq` and the browser's first forwarded operation
would desync if seeding came after it. Its writer recorded it as not
idempotent, a second call raising `verbose.open_twice`, while it opened the
log; the log is now opened by bootstrap (11.8.3.16), and no record states
what a second call does now.

11.8.4.2 `metaverse` is at `seq` 6 on a new root, because the `universe` DDL
counts beside the two documents and the three rows; the question it raised
went with the deleted transcripts.

11.8.4.3 The script row and the metaverse seed are written only while
`metaverse` is at `seq` 0, because writing the script at every start would
overwrite an edited one; so an existing install keeps its old prompt.

11.8.4.4 A crash before the log can open, from the arguments, raw mode, the
engine lock or the settings, reaches only the terminal: approved by the
maintainer.

11.8.4.5 The `error` line uses short names in debug mode too: prescribed by
an order of the earlier coordinator.

11.8.4.6 The Script at `/_files/provider/script.json`, seeded with one node
and no replies: approved by the maintainer; the location stays because the
worker's reader and the browser test use it.

11.8.4.7 The prompt's text is the maintainer's to review and stands, but
where it states something false of the code (11.8.6.5). Its sentence that
the hyperposition "is the one scene the player cannot modify" is the plan's
statement about the scene, not a database refusal. The universe prompt's
shape is chosen to match the analyst's seed, and the prompt does not claim
that the player sees the subtitle of the turn's end.

11.8.4.8 D10's placement: a repeat, and `--main-loop` with the console role,
are refused while parsing; the debug gate on `--main-loop` comes after raw
mode, the lock and the provider check; the errors are `PermissionError` and
`ValueError`. The parser is built with `exit_on_error=False`, and its
writer relied on that option's behaviour in Python 3.13 or later: an
assumption, accepted.

11.8.4.9 The names `bootstrap.option_repeated`, `bootstrap.main_loop_refused`
and `main_loop.input_partial`, beyond the earlier orders: listed by the
planners for the maintainer (section 4.5).

11.8.4.10 The reply header must hold exactly `type` and `reply`, so an
explicit `b` 0, `v` 0, `i` or `k` is refused (alternative recorded: check
through `field_get` only); a full name reply to a short `hello` is accepted.

11.8.4.11 With D4, bootstrap feeds `b""` after each one byte feed of the
reply, so a held fault is raised at once.

11.8.4.12 The engine lock is released at exec by Python's close on exec
default, with no explicit flag; `test_lock_released` proves it.

11.8.4.13 The trace of debug mode holds each line's header JSON only, the
planners' reading built (the whole line rendered, and no trace, the other
options, are open, 11.8.5.3); failures are logged always.

11.8.4.14 `provider.json` is checked beyond its order: exact keys, all
strings, one name `bootstrap.provider_keys` for a missing key, an extra one
or a non object; `provider_info` is sent as read.

11.8.4.15 The root layout `<root>/python/bootstrap.py` and `<root>/i18n/`,
where the plan shows `bootstrap.py` at the root: a departure the planners
list for the maintainer, kept by D11 (the API additions and plan departures
stay).

11.8.4.16 A `.sqlite` file of the root whose name is not a C identifier is
skipped by `loop_prepare` (alternative recorded: raise); the keys of
`hello`'s `seq` come in `db_list()` order; `_verbose` is the verbose
module's own file, made by `verbose.log_open`, never through the substrate,
and left out of `seq`.

11.8.4.17 `python/echo_loop.py` is the echo main loop the planners named for
the wire test, the plan's stage 2 echo handler: self contained on `jslb`,
`dispatch`, `settings` and `i18n`; its streamed cache files stay until the
root is deleted; its reply carries the payload and the blob bytes, with no
blob key or field.

11.8.4.18 The console passes its output through at level 1 too, as a
captured level 1 gives dash no input: the planners' reading, built, its
question open (11.8.5.3).

11.8.4.19 `bootstrap.js` takes the player and the scene as options: the plan
says the script enters a scene and switches players, and its writer
rejected the transcripts' script alone, always writing a default scene
(which needs invented subtitle text) and a Document-Ref argument (impossible
before the region database exists). It validates no argument, `title` and
`region` have no default, a failed run keeps the databases it made, and it
makes one region per run.

11.8.4.20 D17, the `tide` column stays, a universe's prompt is document
`prompt` in the database named by the `universe` row whose `world` is
`/metaverse/world`, and the final text reply becomes the `ai.say` reply's
`subtitle`: the script's region table keeps `tide`, and the prompt states
the other two.

11.8.4.21 The seed JSON files are pretty printed; `main_loop` reads the key
"0" as the integer header, and `doc_put` canonicalizes. They are outside the
reformat whitelist, as `.json` files are never added; `python/seed/*.js` is
in it.

11.8.4.22 `turn_compact` has no MCP tool, and the prompt sends it through a
script (alternative recorded: an API addition `browser.turn_compact`); the
AI keeps `engine.store.turn_compact` to compact by hand.

11.8.4.23 `from i18n import i18n` in these modules: the one `from` exception
the maintainer decided.

11.8.4.24 The test designs recorded: each in process run wraps
`sys.modules` in `patch.dict`; `test_hello_short` patches the private
`bootstrap._MAIN_LOOP_STOCK`; `test_stock_path` stops the stock loop with
`sys.modules["substrate"] = None`; platform errors are asserted by the
stack's last line; the garbled reply expects `jslb.line_not_json` with
CPython's JSON message; `test_mcp_tools` of `python/test_main_loop.py`
compares built responses, and `test_doc_head` reads its own `doc.put` in
`castle`.

11.8.4.25 `python/bootstrap.html` is the previous design's page, held by
D22 (the previous design's files stay untouched until the maintainer
decides); it is not this task's.

11.8.4.26 Built later by design (section 4.2): ttys and roles for further
players; a sandboxed dash; a sleeping task and a wake table on the server; a
hardened server behind the same command line and `hello`. Decided against
(section 4.3): one tty with dash forked by Python and relayed as blobs;
debug as a flag of the ttyd command; `python`, `sqlite` and `debug` fields
in `hello`; a settings digest in `hello`; the provider key in a file of the
root; the old `put`, `ls` and command loop.

11.8.5 Open, for the maintainer.

11.8.5.1 The parser still accepts `-h`, so a client `--url-arg -h` prints
help to the pty and exits 0; its writer recorded `add_help=False` as an
option, not applied.

11.8.5.2 The `universe` table does not make `world` unique, so the lookup
of a universe's prompt can be ambiguous. The alternatives recorded: a UNIQUE
`world`, in the maintainer's `API/sql/metaverse.sql`, which `main_loop`
applies; a hard error in `agent.prompt_build` (task 1.26).

11.8.5.3 Open with a built option, which the review keeps (5.1): the
console's level 1 passes dash's output through and logs start and exit
(other: the output captured and formatted as Markdown progress); the
server's debug trace holds each line's header JSON only, Unconfirmed
(others: the whole line in its rendered form; no trace); `verbose_level`
read by the console role alone, `verbose_ring` kept, `verbose_forward`
gone (others: `verbose_level` renamed, such as `shell_level`;
`verbose_forward` kept beside `debug`; dash run at a fixed level). The
agent lists them and changes nothing.

11.8.6 Candidates.

11.8.6.1 `python/stall_loop.py`: the comment above `loop_run` holds a `;`
outside a code span, which `comments_check` of `python/test_posix.py`
refuses: severity 1, as it stops `test_posix.py` once the banner question of
`xsjs_install.ps1` is answered.

11.8.6.2 `python/stall_loop.py`: the unreachable `loop_run` raises a plain
`RuntimeError`, not an `i18n` message.

11.8.6.3 `main_loop._line_serve`: a stale comment, recorded by an earlier
reviewer.

11.8.6.4 `main_loop.loop_run`: the branch raising `main_loop.not_prepared`
when `loop_prepare` did not run, listed by an earlier reviewer among
branches for cases that cannot happen. It replaced the fallback the
maintainer's reviewer reported, the main loop preparing the root itself
when the preparation step was skipped; a fix must not bring that back.

11.8.6.5 `python/seed/prompt.json`: "the same operations as the database
tools" for `engine.store` does not hold for `engine.store.db_stats()` and
`db_load`; and its sentences that `console_run`, `source_put` and
`system_restart` need debug mode are checked against the code, an earlier
reviewer having recorded that `console_run` neither checks debug nor opens
tty 0 (that tool is task 1.27's).

11.8.6.6 The restart seam of 11.7.6.1, on this side: `bootstrap.py` refuses
the repeated `--main-loop` that `system.restart` leaves when the command
line held `--main-loop=x` or an abbreviation.

11.8.6.7 An argument error writes its `error` line before raw mode, where
the plan has the engine's pty in raw mode before anything is written (an
earlier reviewer's finding). The record that places the D10 refusals while
parsing (11.8.4.8) does not speak of raw mode.

11.8.6.8 Invalid JSON in `provider.json` raises `json.JSONDecodeError` with
no `i18n` message, untested (its writer's record), as `settings_load` does
for `settings.json` (task 1.13's candidate, 11.5); the reader here is
`bootstrap._provider_read`.

11.8.6.9 `python/stall_loop.py` is a module no plan names (an earlier
reviewer recorded it as an Accidental-Requirement risk), and no record
decides it, where `echo_loop.py` is decided (11.8.4.17). Neither fixture
main loop has a `test_<module>.py`, which the plan asks beside each Python
module, and no record decides that either.

11.8.7 Seams.

11.8.7.1 With task 1.15, the restart: `engine_system._argv_make` builds the
command line that `bootstrap.py` parses. A fix in the parser is this task's;
a fix in `_argv_make` goes to task 1.15, which receives first.

11.8.7.2 With task 1.28, and task 1.3 (12.3) for the line contract:
`ts/worker_ai.ts` reads `hello` (`seq`, `settings`, `provider_key`,
`provider_info`) and answers it; a change of a `hello` field goes to task
1.28 first.

11.8.7.3 With tasks 1.25 and 1.28: the Script's location
`/_files/provider/script.json` and its content are read by
`ts/provider_script.ts` and by the worker; a change goes to them first.

11.8.7.4 With task 1.26: `agent.prompt_build` reads the `text` of the head
of `prompt` in `metaverse`, a document of type `prompt` with a string
`text`, and `script.script_run` runs `bootstrap.js`; a change of the
prompt's shape or of the script's arguments goes to task 1.26 first.

11.8.7.5 With task 1.14: seeding and `seq` go through the `Store`. With task
1.13: `verbose.log_open`, `log` and `exec`, `settings.settings_load`,
`dispatch.error_make` and `mcp.Server`. With task 1.12: `LineDecoder` and
`idle()`. A change needed on one of those sides goes to its task first.

11.8.7.6 With tasks 1.17 and 1.19: they start `echo_loop.py` and
`stall_loop.py` through `--main-loop` and assert `bootstrap.lock_held`,
`bootstrap.main_loop_refused` and `engine_system.debug_off`; a change of an
option or a message goes to them first.

11.8.7.7 With tasks 1.9 and 1.10: a new test module goes into `_MODULES` of
`python/test_all.py` by a request to task 1.9; `python/*.py` covers it in
the whitelist, which task 1.10 keeps.

11.9 Task 1.17, the wire test.

11.9.1 Owns: `python/test_wire.py`.

11.9.2 Reads: `python/bootstrap.py`, `python/main_loop.py`,
`python/echo_loop.py`, `python/jslb.py`, `python/dispatch.py`,
`python/mcp.py`, the `python/engine_*.py` handlers, `python/substrate.py`,
`python/category.py`, `python/test_all.py` (its caller), and the users of
`replay_build` in `python/test_browser.py`; the stubs
`API/python/bootstrap.pyi`, `main_loop.pyi`, `jslb.pyi`, `category.pyi`,
`dispatch.pyi`, `mcp.pyi`, `substrate.pyi` and the `engine_*.pyi` stubs,
`API/ts/lines.d.ts` (the line shapes) and `API/mcp/tools.json`, which the
"mcp line" rung reads; `settings.json`, `i18n/en-US.json` and
`python/seed/`, which it copies into each root.

11.9.3 Expected.

11.9.3.1 Purpose. The wire test proves the server through ttyd before the
page exists: the rungs of the plan's stage 2, the raw wire, and the wire
part of stage 4, dispatch and the main loop. Stage 2's exit criterion is
that all its rungs pass twice; stage 4's, that the rungs pass and pyright
is clean. An exit criterion is met by a `--normal-test` run, which runs
every rung.

11.9.3.2 Command: `python3 python/test_wire.py [--smoke-test |
--normal-test]`, at most one option, `smoke-test` by default, added by
`category.options_add`. The entry is `main(arguments)`, which takes its
argument list and returns the exit code; the `__main__` block passes
`sys.argv[1:]`. `python/test_all.py` calls it in its own process with the
full option name, as `test_wire.main([f"--{chosen}"])`, after the Python
suites and `test_posix.py`'s checks and before `test_browser.py`, once the
TAP stream is clean.

11.9.3.3 ttyd. The test runs `build/ttyd/ttyd`, the pinned 1.7.7 release
with its patch, which the install script builds, and fails naming
`xsjs_install.ps1` when it is missing. ttyd listens on port 0, its port and
version read from its log, and runs with `--srv-buf-size 1048576`, the
planners' decision for flow control.

11.9.3.4 Roots. One root per stage, under `build/` with the prefix
`test_wire-`, built as `xsjs_start.ps1` builds a root:
`<root>/python/bootstrap.py` with the runtime modules and the seeds,
`<root>/i18n/en-US.json`, and the checkout's `settings.json` with `debug`
written for the root. ttyd's environment holds
`XSJS_PROVIDER_KEY=test-wire-key`.

11.9.3.5 The client speaks ttyd's WebSocket itself, with the standard
library. ttyd's frames are `'0'` plus bytes each way, `'1'` the title and
`'2'` the preferences first; the server sets raw mode before it writes
anything, and the client sends nothing until `hello` arrives. It reads
lines with `jslb`'s decoder. Its request ids count from 1 per connection
and continue across `system.restart`.

11.9.3.6 Stages, in order, each labelled `smoke-test`: `echo`, whose root
runs `--main-loop echo_loop.py` in debug mode; `stock`, the stock main loop
in debug mode; `release`, a root with `debug` false. Each stage is checked
against the category before its root is made, so a stage with nothing to
run starts no ttyd.

11.9.3.7 The rungs of `echo`, each `smoke-test` unless marked, and what
each proves:

11.9.3.7.1 "hello", the opening rung: the lock is taken, raw mode set and
`hello` received. It hands the later rungs their connection and carries
its stage's label.

11.9.3.7.2 "echo": the echo handler answers the payload and the bytes of
each blob.

11.9.3.7.3 "echo 1 MiB with control bytes": 1 MiB of blob bytes holding
every byte value, echoed equal.

11.9.3.7.4 "echo blob_max", `normal-test`: one blob of `blob_max`, read
from the root's settings, echoed; with the shipped value it moves 2 GiB.

11.9.3.7.5 "echo 128 MiB", `normal-test`: 128 MiB as one message within
`blob_max`, with ttyd's resident size and its peak (`VmRSS`, `VmHWM`)
printed. That measurement decides whether a credit line, or a ttyd patch
bounding its write queue, is ever added.

11.9.3.7.6 "second connection refused": a second connection meets the
engine lock, `bootstrap.lock_held`.

11.9.3.7.7 "blob_max plus one refused": a message whose blobs sum to
`blob_max` + 1 is refused when its line ends, at its carriage return,
before any blob byte is buffered, with `jslb.blobs_over`.

11.9.3.7.8 "last line": the old regression that keys on the last line of a
process that exits right after printing it, kept as it is: 100000 lines on
the console role. A lone loss there is a ttyd fault, reported with the
ttyd version and never retried.

11.9.3.7.9 "ttyd killed", a rung the plan's stage 2 names.

11.9.3.8 The rungs of `stock` and `release`, each `smoke-test`:

11.9.3.8.1 "mcp line", the opening rung of `stock`: `initialize`, the
notification and `tools/list` over the `mcp` line, each reply compared
with a response the test builds from the pinned revision and the server
entries of `API/mcp/tools.json`, then `tools/call` of `source_put`, which
the AI calls without asking.

11.9.3.8.2 "kv.put and kv.get": the value read back byte identical, 1 MiB.

11.9.3.8.3 "doc.put and doc.head".

11.9.3.8.4 "verbose.tail": lines put with `at` and `text` only, read back.

11.9.3.8.5 "unknown type": an unknown line type gives an `error` line,
then exit 1 (`dispatch.handler_unknown`).

11.9.3.8.6 "operation sequence replayed": a sequence of 14 operations that
the test builds with `replay_build`, of the substrate's forwarded kinds
(`kv.put`, `kv.delete`, `doc.put`, `turn.append`, `turn.compact`,
`db.create`, `db.drop` and modifying `sql.run`), replayed over the wire,
read back after a reconnect, and ending in a `substrate.since_stale`
refusal.

11.9.3.8.7 "system.restart": `source.put` then `system.restart` in debug
mode serve a second main loop: a second `hello` from the same pid, then
the echo loop serves.

11.9.3.8.8 "system.restart refused without debug", the one rung of
`release`: `source.put` and `system.restart` refused with
`engine_system.debug_off`, and `--main-loop` with
`bootstrap.main_loop_refused`.

11.9.3.9 Lines and labels. Each rung runs through `RungLog.rung_run(rung,
label, check)` under its own timer and prints one line ending
`(<label>, <s> s)`, its seconds read with `time.monotonic` around it. A
rung the category leaves out is neither run nor printed. A mislabel raises
through `category.LabelBook` as the runner reaches it: a stage labelled
`smoke-test` holds a `smoke-test` rung, one labelled `normal-test` holds
none, and any label but the two strings raises. `RungLog.rung_open` starts
an opening rung and raises when its stage runs but it would not.

11.9.3.10 Timers. Every rung runs under a timer that names it:
`_RUNG_SECONDS` 120.0, the 120 s already written, kept as a default;
ttyd's stop waits `_STOP_SECONDS` 5.0. Each is a named constant whose one
line comment says its writer chose it. The test arms no `SIGALRM` of its
own: in a `smoke-test` run `test_all.py` runs it under an alarm at the
run's deadline.

11.9.3.11 Errors. The first failure ends the run, raised as `CheckFailed`
with the measurement that failed it. Nothing is retried. ttyd is stopped
with `SIGTERM`, then killed after `_STOP_SECONDS`, which is reported as a
failure only if none came earlier.

11.9.3.12 Messages. The test's own messages are f-strings, with no `i18n`
name. It calls `i18n` with a literal name only to build the text of an
engine error it expects: `bootstrap.lock_held`,
`bootstrap.main_loop_refused`, `dispatch.handler_unknown`,
`engine_system.debug_off`, `jslb.blobs_over`, `substrate.since_stale`.

11.9.3.13 Imports. The sibling modules are imported inside functions, after
`sys.pycache_prefix` is set to `build/pycache`, so that no bytecode lands
in `python/`; `import category` stands inside `RungLog.__init__` and
`main`.

11.9.3.14 Public names for the browser test: `replay_build(large) ->
ReplaySequence`, with `ReplayStep` and `ReplaySequence`. The plan's stage 6
replays "`test_wire.replay_build`'s" sequence into the page.

11.9.4 Decided, not a finding.

11.9.4.1 The last line regression runs on the console role, its writer's
choice; every rung where the server writes a line and exits reports a
missing last line as a lone loss with the ttyd version.

11.9.4.2 The 128 MiB echo is one message, and the edge rungs work at the
root's `blob_max`, so with the shipped value each moves 2 GiB: the
maintainer made one blob window, and the planners' reading, built, keeps
the proofs "at the window's edge".

11.9.4.3 The labels: three stages, all `smoke-test`; 17 rungs, 15
`smoke-test`, with "echo blob_max" and "echo 128 MiB" `normal-test`
because one moves a blob of `blob_max` and the other 128 MiB. The smoke
rungs move at most 1 MiB and wait out no timer. Every label is
Unconfirmed until the testing phase measures the fit in 2 minutes; class
B, accepted.

11.9.4.4 `replay_build` is public, and the browser test imports it; the
plan names it. A shared replay module was written out as the alternative
and not built.

11.9.4.5 ttyd is stopped with `SIGTERM`, then killed.

11.9.4.6 "kv.put and kv.get" moves 1 MiB, not `blob_max`: the plan's stage
4 names no size for it, and it is a smoke rung.

11.9.4.7 `tools/list` and `tools/call` over stdio are proved by
`python/test_mcp_stdio.py`, not by the wire test, its writer's choice.

11.9.4.8 The echo reply carries the payload and the bytes of each blob,
with no blob key or fields.

11.9.4.9 The test accepts the second `hello` after `system.restart`, which
the page treats as a fault (D9, a second `hello` after `system.restart` is
a fault ending in Reload).

11.9.4.10 `--main-loop` is refused on the root with `debug` false (D10,
`--main-loop` refused outside debug mode and with the console role).

11.9.4.11 "mcp line" compares payloads with responses the test builds, not
with recorded text, and its tool entries carry no `_meta`, as
`engine_system` registers them; `API/mcp/tools.json` was edited to drop
the `_meta` of `source_put` and `system_restart` once those two were no
longer permit tools.

11.9.4.12 Run alone, the test keeps `argparse`'s default and takes
`--normal` for `--normal-test`. The maintainer's answer refuses
abbreviations in `test_all.py` only, which passes the full name, and
leaves the runners as built; turning abbreviations off in every runner's
parser, through `options_add`, is the option that answer passed over.

11.9.4.13 A rung the category leaves out is not printed, nor written as a
skip, and the runners' messages are f-strings with no `i18n` names: the
reported skips and the `i18n` messages are designs not built (section
4.2).

11.9.4.14 `from i18n import i18n` inside functions: the one `from`
exception of the plan's naming rules, decided by the maintainer. The plan
records that it is not yet in the project rules and says to report that
gap, not to edit the rules.

11.9.4.15 `main` keeps one word, the name the planners gave each runner's
entry.

11.9.4.16 The root layout `<root>/python/bootstrap.py` and `<root>/i18n/`
is a plan departure that stands for the review and awaits the maintainer's
acceptance (4.5.18).

11.9.4.17 The imports inside functions after the bytecode prefix, and the
`LineObject` alias cast to `jslb.Object`, are their writer's choice.

11.9.4.18 `XSJS_PROVIDER_KEY=test-wire-key` in ttyd's environment is its
writer's choice.

11.9.4.19 Names holding "transcript", such as `transcript_check`, mean the
terminal output, as an earlier job recorded.

11.9.4.20 Owed to the testing phase, not findings: every label's fit in 2
minutes, ttyd's resident size during the 128 MiB echo, and the shipped
`blob_max`, which is documented and not measured.

11.9.5 Open, for the maintainer. Each has its built option, which the
review keeps (5.1); the agent lists the question and changes nothing.

11.9.5.1 The size of the large proofs: a) a blob of `blob_max`, one byte
more refused, 128 MiB as one message (built); b) the earlier 16 MiB and
128 MiB, the edge proved only by the decoders' unit tests; c) the edge
rungs on roots whose settings set a smaller `blob_max`, the shipped value
proved by `rung_blob_max` alone.

11.9.5.2 The grain of a label, the smoke-test suites and the options:
the questions of 11.1.5.3, 11.1.5.4 and 11.1.5.6, whose built options
make each wire rung a suite, every rung but "echo blob_max" and "echo 128
MiB" `smoke-test`, and `--smoke-test` the default of the runner run
alone.

11.9.6 Candidates.

11.9.6.1 `rung_fit`, the rung "echo blob_max", holds `blob_max` random
bytes twice in the test client, the request and the echo, because the
client has no streaming send and its decoder keeps every message in
memory: 4 GiB in one process. Expected: the blob is not held whole twice,
which the streaming send the record names as missing would give. S.

11.9.6.2 Each rung of 11.9.3.7 and 11.9.3.8 exists and proves what it
states, runs under a timer that names it, and a lone loss is reported
with the ttyd version and never retried.

11.9.7 Seams.

11.9.7.1 `replay_build`, `ReplayStep` and `ReplaySequence` are read by
`rung_page_replay` of `python/test_browser.py`: a change to their names or
shapes goes to task 1.19, which receives first.

11.9.7.2 `main(arguments)` is called by `python/test_all.py`: a change to
its signature goes to task 1.9, which receives first.

11.9.7.3 The echo reply and the root's cache directory are
`python/echo_loop.py`'s, task 1.16's.

11.9.7.4 The `i18n` names and reply shapes the rungs expect belong to
`bootstrap.py` and `main_loop.py` (task 1.16), the `engine_*` handlers
(task 1.15), `dispatch.py` and `mcp.py` (task 1.13), `jslb.py` (task 1.12)
and `substrate.py` (task 1.14). A change there that this file must follow
reaches task 1.17 as a request, and task 1.17 receives first.

11.9.7.5 `LabelBook` and `options_add` are `python/category.py`'s, task
1.9's.

11.10 Task 1.18, the page build and DevTools.

11.10.1 Owns: `python/page_build.py`, `python/test_page_build.py`,
`python/devtools.py`, `python/test_devtools.py`, `html/engine.html`,
`html/test.html`, `html/test_engine.html`, and, as their steward,
`ts/tsconfig.json` and `ts/tsconfig.test.json`.

11.10.2 Reads: `API/python/page_build.pyi` and `API/python/devtools.pyi`;
`ts/boot.ts`, `ts/test_hook.ts`, `ts/test_all.ts`, `ts/error_overlay.ts`,
`ts/page.ts` and `ts/ui_strings.ts` (its `I18N_TABLE_JSON`);
`html/engine.css`; `i18n/en-US.json`; `python/vectors_make.py`;
`python/third_party_fetch.py` and `python/test_third_party_fetch.py`,
which reads this module's archive names; the comments of `xsjs_start.ps1`
and `powershell/test_powershell.ps1` that name the build command; the users
of `devtools` and `page_build` in `python/test_browser.py`; and
`python/xsjs_screenshot.py` and `python/xsjs_screenshot_wsl.py`, held
(D22, the previous design's files left untouched until the maintainer
decides).

11.10.3 Expected.

11.10.3.1 The page is one static file that ttyd serves,
`build/hyperposition-engine.html`, built by `python3 python/page_build.py
hyperposition-engine`. Nothing is fetched at run time but media URLs.
Changing the page needs a rebuild and a reload.

11.10.3.2 `page_build(name, test, template) -> str` (stub
`API/python/page_build.pyi`) builds `build/<name>.html` from
`html/<template>`, and prints and returns the page's SHA-256; `test`
chooses the test bundle. `main()` is the command line `python3
python/page_build.py <name> [--test]`. `__all__` is `["page_build"]`, and
the helper names are public.

11.10.3.3 The bundle. `tsc --project` over `ts/tsconfig.json`, or
`ts/tsconfig.test.json` for a test page, compiles the `ts/` files it lists
with `module` none and `outFile` into one classic script in reference
order; each file defines one frozen object named after its module, and
`strict` is on. The bundle begins with `error_overlay`, `utility`,
`ui_strings` and `settings`, in that order, then `i18n` and the rest in
reference order. Node runs tsc at build time and nothing else. tsc is
TypeScript 5.x, with no `ignoreDeprecations` (D16, the TypeScript version
default).

11.10.3.4 The strings. The build substitutes `I18N_TABLE_JSON` in
`ui_strings` exactly once with the unmodified text of `i18n/en-US.json`,
the one build step the one file rule requires, so both languages read one
file. tsc keeps comments, so a comment naming the token would count
against the "exactly once".

11.10.3.5 The pieces: `jswasm/sqlite3.js` and `jswasm/sqlite3.wasm` from
`third_party/sqlite-wasm-3460100.zip`, and `package/lib/xterm.js` and
`package/css/xterm.css` from `third_party/xterm-5.5.0.tgz`, each member
found by its path suffix with exactly one match; `html/engine.css`; and
sqlite3.wasm as base64. Seven markers are filled: `XSJS_BUILD_BUNDLE`,
`XSJS_BUILD_ENGINE_CSS`, `XSJS_BUILD_XTERM_CSS`, `XSJS_BUILD_XTERM_JS`,
`XSJS_BUILD_SQLITE3_JS`, `XSJS_BUILD_SQLITE3_WASM` and
`XSJS_BUILD_TEST_VECTORS`. The build refuses a piece holding `</script`,
`</style`, `<!--` with `<script`, or NUL.

11.10.3.6 The vectors. For a test page the build writes
`build/vectors/*.jslb` anew with `vectors_make.py` and embeds them as
`test_vectors`.

11.10.3.7 The templates. The body of `html/engine.html`, in order: the
bundle (`data-worker`); `sqlite3_wasm_base64` in a `text/plain` script
(`data-worker`); sqlite3.js in a `text/plain` script (`data-worker`);
xterm.js (the UI only); `boot.boot_run();` (`data-worker`).
`html/test.html` puts `<pre id="tap_output">` and the `test_vectors`
script first and ends with `test_all.suites_run();`.
`html/test_engine.html` is the engine page built with the test bundle,
whose entry is `test_hook.engine_run();`; through it a browser rung
submits tasks from the UI's live queue (`page.test_engine`,
`boot.test_engine`). The entry call stands in the template because
`boot.ts` is in both bundles.

11.10.3.8 The worker. Its source is `"use strict";\n` plus the
`textContent` of every `script[data-worker]` in document order, one Blob of
type `text/javascript`, started as `new Worker(url, {name: "ai"})`; the
entry is chosen by `self.name`, which is `""` on the main thread. A one
line comment in `page_build.py` states this contract. Globals:
`sqlite3_wasm_base64` and `sqlite3InitModule` in the worker only,
`Terminal` on the UI thread only, `test_vectors` on a test page in both
threads. No module touches the DOM or `Terminal` at load.

11.10.3.9 The lists. The production page carries no test code:
`ts/tsconfig.json` lists no test module and not `ts/test_hook.ts`, which
is in the test bundle only. Both lists name the `ts/` files exactly as
they exist, in reference order, the first four scripts first. A `ts/` file
added, renamed or removed changes the lists, which only task 1.18 edits.

11.10.3.10 `error_overlay` has one job from the start of the page: it
catches `error` and `unhandledrejection` on the window, resource load
failures in the capture phase and `fault` lines from the AI worker, and
replaces the screen by `document.write` with a `<pre>` holding the message
and the call stack. A thrown error in the test page ends in that `<pre>`
screen, a proof of the plan's stage 0.

11.10.3.11 `python/test_page_build.py` tests the build without starting
tsc; its `test_template_hooked` counts the one line hook of
`html/test_engine.html`.

11.10.3.12 `devtools.py` is the DevTools relay of the old screenshot tool,
split out. It starts headless Windows Chrome or Edge and speaks the
DevTools protocol through a C# relay run by `powershell.exe` (the class
`XsjsDevToolsRelay`, the profile prefix `xsjs_devtools-`), because WSL's
NAT cannot reach Windows' 127.0.0.1. `Browser()` raises off WSL; there is
no fallback path to `powershell.exe`.

11.10.3.13 Public names (stub `API/python/devtools.pyi`): `Browser`, a
context manager made with `(width_px, height_px)`, with `events`,
`page_open(url)`, `script_evaluate(text)`, `console_follow(fn)`,
`screenshot_save(path)`, `page_close()`, `client_get()`,
`trace_start(categories)`, `trace_end()` and `worker_pause(name)`;
`ProtocolClient.method_call`, `session_call` and `events_pump`;
`PageEvents.lifecycle`; `blocking_categories()` and
`blocking_find(events)`. `__all__` is `["Browser", "blocking_categories",
"blocking_find"]`, under the comment "The public names of this module, as
its stub declares them."

11.10.3.14 Waits. Every wait has a named `WaitTimer` that raises
`TimeoutError`. The timers, each "a default chosen by its writer":
`_COMMAND_WAIT_SECONDS` 60, `_DEVTOOLS_WAIT_SECONDS` 60, `_POLL_SECONDS`
0.1, `_PROFILE_REMOVE_SECONDS` 10, `_REPLY_WAIT_SECONDS` 60,
`_SERVER_WAIT_SECONDS` 60, `_STOP_WAIT_SECONDS` 5.

11.10.3.15 `page_open(url)` navigates and waits for `Page.lifecycleEvent`
"load" with the `loaderId` that `Page.navigate` returned; a same document
navigation raises `KeyError`. It repeats the navigation, within a bound,
only while `errorText` is `net::ERR_CONNECTION_REFUSED` (D15, that bounded
wait, which the old tool had because WSL forwards a new listener about 1 s
late).

11.10.3.16 `script_evaluate(text)` sends `awaitPromise` and
`returnByValue`. A thrown exception raises with its description, an
unserializable result raises, and `undefined` returns `None`.

11.10.3.17 The console. `Runtime.enable` is sent at attach. Messages are
read only while another call or the load wait reads the socket, with no
reader thread. A caller calls `console_follow` before `page_open`, and
makes its server reachable from Windows first.

11.10.3.18 Shutdown, in order: kill through the stop script, which waits
on a timer, sleeping `_POLL_SECONDS`; end the relay; remove the profile,
retrying only on `EACCES`, `EBUSY`, `ENOTEMPTY` and `EPERM` within
`_PROFILE_REMOVE_SECONDS`, then raising `TimeoutError` with the last
`OSError` as its context. `page_close()` is `Target.closeTarget`.

11.10.3.19 Strictness. An unexpected reply id is a `RuntimeError`. The
DevTools port file must hold exactly two fields once it is not empty; one
with fewer is not ready. `wslpath` runs as a subprocess.

11.10.3.20 Tracing. `trace_start(categories)` starts a trace, and
`trace_end()` returns its events and raises when the trace lost events.
`blocking_categories()` returns `loading` and `__metadata`.
`blocking_find(events)` returns the synchronous network loads on any
`CrRendererMain` thread. Only synchronous network loads are detected, not
the synchronous calls behind `document.cookie` or `localStorage`, which
the maintainer accepted; the browser rung `rung_blocking_control` proves
the event names first.

11.10.3.21 `session_call` calls a method on a session, the browser's when
the id is empty. `worker_pause(name)` pauses the page's worker of that name
through `Target.setAutoAttach` and `Debugger.pause`, waiting for
`Debugger.paused`.

11.10.3.22 Messages. `devtools.py` names no `i18n` string; its messages
are f-strings, as its first writer built them. The planners' decision on
the test categories gave the runners and `category.py` f-strings, naming
the TAP modules and `devtools.py` as writing theirs so already. Nothing
decides it for `page_build.py`, and the sources record no `i18n` prefix
for it.

11.10.3.23 `python/test_devtools.py`: the first writer's about 45 tests
in 8 classes, on frames, masking, the accept key, the handshake,
reassembly, the relay script's text, address parsing, the timers and the
protocol client on canned bytes; then `TestBrowser`, 9 tests, added by a
later writer, and the tests of the tracing and `worker_pause` additions;
no test starts a process.

11.10.4 Decided, not a finding.

11.10.4.1 D15's bounded retry of the navigation, a sleep loop on exactly
`net::ERR_CONNECTION_REFUSED`. An earlier audit's note that `page_open`
"retries navigation in a sleep loop" is this default; the note stays open
(11.10.5.3).

11.10.4.2 Three candidate Chrome trace event names where one is right,
approved by the maintainer; the plan's "the page's UI thread" built as any
renderer main thread, class B, accepted.

11.10.4.3 `__all__` of three names, and every helper of `devtools.py`
public (`EndpointAddress`, `SocketFrame`, `WaitTimer`, `PageEvents`,
`ProtocolClient`, `frame_encode`, `frame_decode`, `message_read`,
`accept_key`, `handshake_request`, `handshake_check`, `head_read`,
`address_parse`, `relay_script`, `powershell_command`, `pipe_read`,
`bytes_exact`, `console_text`, `exception_text`, `command_run`, `path_wsl`,
`stream_write`), because pyright strict refuses private access from the
tests. The public helpers of both modules and `page_build.main()` are
accepted API additions (section 4.5).

11.10.4.4 The `PageEvents` fields `trace`, `trace_done`, `trace_lost`,
`workers` and `paused` stay out of the stub, whose text declares
`lifecycle` only and was applied as written; so was the text of
`API/python/page_build.pyi`.

11.10.4.5 `devtools.py` duplicates the relay, the DevTools client and the
browser lookup of `python/xsjs_screenshot.py` and
`python/xsjs_screenshot_wsl.py`, which are held (D22, left untouched until
the maintainer decides); retiring the old tool is the maintainer's
decision.

11.10.4.6 Not carried over from the old tool: focus emulation, `page_fit`,
`click` and `line_send`. The plan names five functions: `page_open`,
`script_evaluate`, `console_follow`, `screenshot_save` and `page_close`.

11.10.4.7 `screenshot_save` does not create directories; the caller does.
`page_close` ignores the result of `Target.closeTarget`.

11.10.4.8 The profile removal retry and its errno set, its writer's choice
under the coordinator's order; the drvfs errnos are unmeasured.

11.10.4.9 `cast` in place of an `assert` that only narrows a type.

11.10.4.10 Unconfirmed, accepted, owed to the first run: the RFC 6455
accept value `s3pPLMBiTxaQ9kYGzzhZRbK+xOo=` typed from memory; the fields
of `Page.lifecycleEvent`; `Target.closeTarget` returning `success`; the
argument shapes of `Runtime.consoleAPICalled`; the fields of
`exceptionDetails`; the trace event names.

11.10.4.11 The worker join contract is stated by a one line comment and is
not enforced in code: the second of two forms the coordinator offered.
Rejected by its writer: the worker text as one prebuilt element, fixed ids
per piece, one Blob URL per piece with `importScripts`, and the vectors
after the bundle.

11.10.4.12 The formatter's changes to the templates, reported by the
earlier job as suspect, not reverted, and listed for the maintainer to
review: every build marker on its own indented line, and a `;` after
`XSJS_BUILD_BUNDLE` and `XSJS_BUILD_XTERM_JS`, which the merge tolerates
by its writer's reading of the formatter, Unconfirmed, so the built page
holds each followed by `;`; `<!doctype html>` in lower case, which the
header check reads without case. They stay, and the agent lists them for
the maintainer's review (10.3.10).

11.10.4.13 The test engine page outside the production bundle, approved by
the maintainer: `page.test_engine(run)`, `boot.test_engine`, the test
bundle only module `test_hook` with `engine_run()`, and `page_build`'s
`template`. `page` has no stub, and `API/ts/boot.d.ts` leaves out the test
only functions.

11.10.4.14 The test page carries `engine.css`, so a failed TAP line is red
text, not a background; the highlight was requested and is Unconfirmed.

11.10.4.15 `page_build.main` keeps one word, as the accepted API addition
names it.

11.10.4.16 The two tsconfig files are not in the reformat whitelist:
`.json` files are not added to it.

11.10.4.17 tsc keeps its default `lib`, and the compile fails until every
listed file exists.

11.10.4.18 xterm.js ends with a `sourceMappingURL` comment, which DevTools
may request and ttyd answers with 404; recorded by the build's writer.

11.10.4.19 Unconfirmed, accepted: sqlite3.js 3.46.1 fetches sqlite3.wasm by
URL, which a Blob worker cannot resolve, so the worker supplies the bytes
from `sqlite3_wasm_base64`; sqlite3.js runs under strict mode; TypeScript 6
deprecating `outFile` and `module` none, recalled from memory.

11.10.4.20 `devtools.Browser` starting a container's Chrome directly
belongs to the Docker target of `test_posix.sh`, built later by design
(section 4.2).

11.10.5 Open, for the maintainer.

11.10.5.1 `test_template_hooked` of `python/test_page_build.py` fails: the
formatter split the one line `<script data-worker>test_hook.engine_run();
</script>` of `html/test_engine.html` over three lines, and the test counts
that one line. Options: a) a `<!-- prettier-ignore -->` line above it; b)
the test matches the hook whatever its white space; c) the change
reverted by hand, which the next format run undoes.

11.10.5.2 An 80 column HTML comment in each `html/*.html`, made by the
formatter's re-indent; prettier does not wrap comments. Listed, not
wrapped by hand.

11.10.5.3 The sleep loop of `devtools.page_open`, D15's bounded retry
(11.10.4.1): one of the findings of 4.7.14, which neither the project
rules nor this file's expected design settle. Listed, not changed.

11.10.6 Candidates.

11.10.6.1 The `from typing` names of `devtools.py` stand out of order
(`IO, Any, NamedTuple, Self, cast`); the project rules put them in
alphabetical order on one line.

11.10.6.2 `error_overlay.overlay_install()` runs only from the last
script, so a throw while the bundle or xterm.js loads leaves a blank page,
against 11.10.3.10. A seam: see 11.10.7.2.

11.10.6.3 The production bundle carries no test code: `ts/tsconfig.json`
lists no test module and not `ts/test_hook.ts`; both lists are in
reference order, the first four scripts first.

11.10.6.4 `page_build.py` runs `tsc` with no timeout, which its writer
recorded as a gap. Expected: the run bounded by a named timer.

11.10.6.5 When a navigation is refused until the bound ends, the timeout's
message does not repeat the error text, a gap its writer recorded.

11.10.6.6 A DevTools port path cut short but holding two fields is
accepted and fails at the handshake, a gap its writer recorded.

11.10.6.7 Console messages logged before `console_follow` are lost, and
`Runtime.exceptionThrown` is not delivered, as the first writer recorded;
the callers are expected to call `console_follow` before `page_open`.

11.10.7 Seams.

11.10.7.1 The templates' entry calls are `boot.boot_run` (`ts/boot.ts`,
task 1.28), `test_all.suites_run` and `test_hook.engine_run`
(`ts/test_all.ts` and `ts/test_hook.ts`, task 1.20).

11.10.7.2 11.10.6.2: `overlay_install` is defined in `ts/error_overlay.ts`
(task 1.21) and called from `ts/boot.ts` (task 1.28) and `ts/page.ts`
(task 1.29). Task 1.18 sends its request to the owner whose file the fix
changes, which receives first; the templates follow.

11.10.7.3 `I18N_TABLE_JSON` stands in `ts/ui_strings.ts` (task 1.21).

11.10.7.4 `python/test_browser.py` (task 1.19) mirrors `devtools.Browser`,
`ProtocolClient` and `PageEvents` in its `BrowserDriver`, `DriverClient`
and `LifecycleEvents`, and calls `page_build(name, test, template)` from
`page_ready`: a change to either goes to task 1.19, which receives first.

11.10.7.5 `python/test_third_party_fetch.py` (task 1.11) reads
`page_build`'s `_SQLITE_ARCHIVE` and `_XTERM_ARCHIVE` with `getattr`, and
the comments of `xsjs_start.ps1` and `powershell/test_powershell.ps1` name
the build command: a rename goes to task 1.11, which receives first.

11.10.7.6 The vectors are written by `python/vectors_make.py` (task 1.12).

11.10.7.7 The tsconfig lists follow every `ts/` file: the census (task
1.1) and each `ts/` owner send their changes to task 1.18.

11.11 Task 1.19, the browser test's harness.

11.11.1 Owns: `python/test_browser.py`, 8986 lines at the baseline, the
largest file, so it is launched first (section 9); task 1.19 is its
steward. In Phase 1 it reviews the harness: the imports, the constants,
`RunContext`, `RungLog`, the roots and `session_run`, `page_ready`, the
stub server, `_PROBE_KIT`, `BrowserDriver`, `tap_check`, the teardown, the
timers and the labels; and it works its inbox in its pass. The rungs are
reviewed by tasks 1.5 to 1.7 (12.5), whose requests task 1.19 works in its
pass or in Phase 2, where fresh agents under task 1.19 may run one at a
time, each taking the waiting requests, making its edits in one lock cycle
and reading only the parts it edits.

11.11.2 Reads: `python/devtools.py` and `API/python/devtools.pyi`;
`python/category.py` and `API/python/category.pyi`; `python/page_build.py`
and `API/python/page_build.pyi`; `python/tap_consumer.py` and its stub;
`python/test_wire.py` (`replay_build`); `python/substrate.py` and its stub;
`python/bootstrap.py`, `python/main_loop.py`, `python/echo_loop.py`,
`python/stall_loop.py` and `python/seed/`; `settings.json`,
`provider.json` and `i18n/en-US.json`; `ts/test_all.ts`, which writes the
TAP documents; and the `ts/` code each probe reaches.

11.11.3 Expected.

11.11.3.1 Command and entry: `python3 python/test_browser.py
[--smoke-test | --normal-test]`, at most one option, `smoke-test` by
default, added by `category.options_add`; the entry is `main(arguments)`,
the `__main__` block passing `sys.argv[1:]`. `python/test_all.py` calls
`test_browser.main([option])` in its own process after `test_wire.py`.

11.11.3.2 What it does: it builds `test.html` and the engine pages, each
when the first root that serves it starts, serves them through ttyd, runs
the TypeScript suites in headless Chrome with the `tap_producer` tests
first in the page's `test_all.ts`, reads the `tap.line` stream from the
file the server appends it to, checks it with the consumer, and saves
PNGs in `build/test_browser/`. The one JavaScript runner is a browser. It
runs `build/ttyd/ttyd` and fails naming `xsjs_install.ps1` when it is
missing. Its rungs carry the proofs of the plan's stages 0 and 4 to 8; the
exit criterion of stage 5 is that `test_browser.py` exits 0.

11.11.3.3 Setup is not a suite: a page build, a root's ttyd, the browser
and the stub server, the vectors. Each runs when a suite that needs it
runs, and a `smoke-test` run starts no ttyd and no page for a root it runs
nothing on. One browser and one stub server serve every root of the run.

11.11.3.4 `RunContext` carries what the roots of one run share: the one
browser, as a `BrowserDriver`, the `RungLog`, the work directory, the stub
server, the three pages and the set of pages built so far.

11.11.3.5 `BrowserDriver`, `DriverClient` and `LifecycleEvents` are
`Protocol` classes for the part of `devtools.Browser`, `ProtocolClient`
and `PageEvents` the test uses, `trace_start` and `trace_end` among them;
they agree with `API/python/devtools.pyi`, and pyright strict accepts
`devtools.Browser` as a `BrowserDriver`.

11.11.3.6 The roots. Each is built as `test_wire.py` builds a root, made
with `tempfile.mkdtemp` under `build/` with the prefix `test_browser-`,
and kept after the run with its path printed, so that the TAP file and
`_verbose.sqlite` survive every exit. ttyd serves the root's page with
`--index` and runs with `--srv-buf-size 1048576`. The provider Script and
the AI scripts are written into `_files` by a `substrate.Store` in the test
process before ttyd starts. The first writer removed the provider key from
ttyd's environment (D8: `XSJS_PROVIDER_KEY` is required only when
`provider.scripted` is false). The seeded Script, at
`/_files/provider/script.json`, has one node and no replies, so input on a
root without a test driver faults.

11.11.3.7 The roots and their labels: 23 roots, `suites` and `fresh`
`smoke-test`, the rest `normal-test`: `faults`, `probe`, `credential`,
`echo`, `stalled`, `release`, `first`, `second`, `main`, `locked`, `level`,
`tool`, `crash`, `timeout`, `compact`, `bulk`, `replay`, `evict`, `stress`,
`upload` and `largest`, which runs last. The rung "stage 5: stub
reachable" stands outside any root, `normal-test`, since only the
`normal-test` roots `probe`, `timeout` and `compact` need the stub. Of 126
rungs, 3 are `smoke-test`: "stage 0: typescript suites" and "stage 0:
typescript suites in order", which reads the documents the first wrote, in
`suites`, and "stage 8: fresh root" in `fresh`, which proves the page
load, `hello`, the seeded Script and a first render with no fault. Every
rung of a `normal-test` root is `normal-test`.

11.11.3.8 Why a rung is `normal-test`: it moves or allocates a blob of
`blob_max`; it waits out a 120 s timer of `wire.ts` by design, the whole
limit of a smoke run; it moves 128 MiB or more; it needs what a
`normal-test` rung or root leaves (`second` compares with what `first`
recorded; the rest of `upload` reads the trace and the long task observer
that the largest put starts); it is a long scripted session (`stress`,
eight rounds under a 600 s timer; `main`, about forty rungs on one page,
each needing the state of those before it, run whole or not at all); or
it is another real platform path of a module whose unit suite runs in the
smoke run.

11.11.3.9 `session_run` takes the root's label and checks it with the
run's `category.LabelBook` before it builds, makes or serves anything; a
root labelled `smoke-test` holds a `smoke-test` rung, one labelled
`normal-test` holds none, and a mislabel raises as the runner reaches it.

11.11.3.10 `page_ready` builds a page with `page_build(name, test,
template)` the first time a root serves it, and prints a line ending with
the build's seconds. The three pages: `test`, from `html/test.html`;
`test_engine`, the engine page from `html/engine.html`, built as
`build/test_engine.html`; and `test_engine_hook`, the test engine page from
`html/test_engine.html`. A smoke run builds only `test` and `test_engine`.

11.11.3.11 `RungLog`. `rung_run(rung, label, check)` runs a rung of the
category under its own timer and prints one line ending
`(<label>, <s> s)`, its seconds read with `time.monotonic`. A rung the
category leaves out is neither run nor printed. `import category` stands
inside `RungLog.__init__` and `main`.

11.11.3.12 Timers. Every rung and every browser test has a timer, and a
timer expiring is a failure that names the rung. Each timer is a named
constant whose one line comment says its writer chose it; the 120 s
lengths already written stay. The constants and their writers' values:
`_RUNG_SECONDS` 120.0, `_SUITES_SECONDS` 600.0, `_POLL_SECONDS` 0.1,
`_STOP_SECONDS` 5.0, `_HTTP_SECONDS` 2, `_MEDIA_SECONDS` 2,
`_CONSOLE_SECONDS` 30, `_SLEEP_SECONDS` 2, `_HOLD_SECONDS` 120.0,
`_QUIET_SECONDS` 5.0, `_ECHO_SECONDS` 600.0, `_WIRE_SECONDS` 120,
`_FRAMES_MS` 1000, `_PROVIDER_SECONDS` 1, `_STALL_SECONDS` 5.0,
`_DRAIN_SECONDS` 120, `_LARGEST_SECONDS` 600.0, `_UPLOAD_SECONDS` 600.0,
`_STRESS_SECONDS` 600.0, `_WINDOW_SECONDS` 600.0 (for `rung_round`,
`rung_over` and `rung_decoder`) and `_MEASURE_SECONDS` 3600.0 (for
`rung_blob_max`). In a `smoke-test` run `test_all.py` runs the test under
an alarm at the run's deadline.

11.11.3.13 Errors: the first failure ends the run, raised as
`CheckFailed` naming the rung; nothing tallies failures.

11.11.3.14 The stub server, `StubServer` with `StubHandler`, is the local
stub that `http.ts` is proved against, and serves the media downloads, the
provider that a root's own `provider.json` points `base_url` at for the
real HTTP timeout inside a turn, and the held `/token` and WebSocket
upgrade of the wire timer rungs and of "console closed before open".

11.11.3.15 The probe kit, `_PROBE_KIT`, is the JavaScript the harness
evaluates in a page through `script_evaluate` to read and drive the page's
modules, as functions under `probe`. Its function names carry two English
words, as `probe.words` became `probe.words_make` for that rule. The test
only exports of the page's modules that the probes read stay (D25, test
only exports stay).

11.11.3.16 `tap_check` and its helpers read `<root>/tap/typescript.tap`,
which the server appends unbuffered, one `tap.line` at a time, so a hang
leaves the lines before it on disk. The file holds two TAP documents, the
UI's then the worker's, each from `TAP version 14`. The check splits it
there, requires exactly two documents (`_TAP_DOCUMENTS`), each well formed
with no failure by `tap_consumer`, and stops at the first failure.

11.11.3.17 The teardown: each root's ttyd stopped, its stop bounded by
`_STOP_SECONDS`; the browser closed by `devtools.Browser`'s own shutdown;
the stub server shut; the roots kept.

11.11.3.18 Messages: the harness's own are f-strings, with no `i18n` name.
It imports `i18n` and calls `i18n.i18n(...)` with a literal name to build
the text of an engine error a rung expects.

11.11.3.19 Imports and constants: the sibling modules are imported inside
functions after `sys.pycache_prefix` is set to `build/pycache`; constants
are `_UPPER_NAME` at the top of the file, after the imports.

11.11.4 Decided, not a finding.

11.11.4.1 The roots and the ladder of rungs of each root, as built; an
earlier audit found every ladder rung and helper defined, every root
complete, and no clash of scripted inputs (16 for `bulk`, 17 for `evict`,
18 to 41 for `stress`).

11.11.4.2 The kept roots: the maintainer asked that no test output be
lost, and the roots are no longer deleted on exit.

11.11.4.3 `import category` inside `RungLog.__init__` and `main`,
because on the top import line it would run before `sys.pycache_prefix`
is set and write bytecode into `python/`.

11.11.4.4 The labels of 11.11.3.7. Each is Unconfirmed until the testing
phase measures the fit in 2 minutes, and the smoke set of two roots was
chosen without a measurement; class B, accepted.

11.11.4.5 The first writer's decisions: roots built as `test_wire` builds
them, the page served from the root with `--index`, the scripts written by
a `Store` before ttyd starts, the provider key removed from ttyd's
environment, one browser and one stub server for every root, the
screenshots in `build/test_browser/`, and the first failure only through
`CheckFailed`.

11.11.4.6 Three pages built with `page_build(name, test, template)`, and a
smoke run building only `test` and `test_engine`.

11.11.4.7 Two TAP documents in `tap/typescript.tap`, the UI's then the
worker's, as the page's harness writes them; so `tap_check` reads two.

11.11.4.8 The page replay imports `test_wire` and uses only its public
`replay_build`; a shared replay module was written out as the alternative
and not built.

11.11.4.9 Run alone, the test takes `--normal` for `--normal-test`, as
built; the maintainer's answer refuses abbreviations in `test_all.py`
only.

11.11.4.10 A rung the category leaves out is not printed nor written as a
skip, and the messages are f-strings: the reported skips and the `i18n`
messages are designs not built (section 4.2). `import i18n` with
`i18n.i18n(...)` is the form its first writer recorded.

11.11.4.11 `main` keeps one word, the name the planners gave each
runner's entry. `rung_blob_max` keeps its three words, the name the
planners gave the measurement rung; as a decision that breaks the two
names rule it is open (12.5.4.5), not a finding.

11.11.4.12 The root `level` is `{"debug": True, "verbose_level": 2}`,
one root for the debug rungs and the console rungs, not two: a class B
item not yet confirmed, built as option a) of 11.11.5.2; the synchronous
root is `{"queue_synchronous": True, "debug": True}`.

11.11.4.13 The test engine page outside the production bundle, approved by
the maintainer, through which a rung submits tasks from the UI's live
queue.

11.11.4.14 The drain poll rung's approved form: a sleep of 5 s, then one
check that the poll waits.

11.11.4.15 On the rungs, decided, for the requests task 1.19 works: the
drain rungs stall ttyd with `SIGSTOP`; the drain timer rung posts a burst
sized from the queue bound, now `blob_max`, 255 lines of 8 MiB at the
shipped value; `_STRESS_ROUNDS` is 8, a count chosen by its writer; the
echo rungs keep the 251 byte period pattern, not non repetitive data;
`rung_console_reopen` runs open, exit, open; `rung_http_timeout` writes
its own `provider.json`, sets `provider.scripted` false there and points
`base_url` at the local stub; the largest put is measured in the start
state it is used in; `rung_ui_upload`'s 135 MiB fits `blob_max`, so its
approved expectation of `worker_ai.queue_over` changes, and no later
record shows the change (12.5.5.4.9); only synchronous network
loads are detected, under three candidate event names; nothing is built
for `test_wal_left`; the page replay compares the browser's copy with the
server's; a UI put of `blob_max` + 1 is refused first by the AI worker's
task queue with `queue.queue_over`; `rung_decoder` writes the value of
`blob_max` + 1 bytes on the server with `substrate.Store.kv_put` and a
file path, since no port can carry it; each edge rung moves 2 GiB at the
shipped `blob_max`; the three races the first writer accepted. They are
listed here because task 1.19 applies the stage reviewers' requests.

11.11.4.16 Unconfirmed, accepted: the two browser behaviours
`rung_credential` rests on; the main root's start scene holds about 46
turns, counted from the ladder and not measured, so it never compacts.

11.11.5 Open, for the maintainer.

11.11.5.1 The lines over 79 columns that the formatter cannot wrap,
string literals among them: the earlier job counted about 60 long lines
before its one formatter run and left them to it; the count after the run
was not recorded, and an earlier review found that the formatter leaves
long string lines. Listed, not wrapped by hand.

11.11.5.2 The root of the debug rungs and the console rungs, a class B
item the maintainer has not confirmed: a) one root, `{"debug": True,
"verbose_level": 2}`, because the console rungs need the shell's level 2
on the same root and the key is in every root's settings (built); b) two
roots, `{"debug": True}` as first asked and another for the rungs that
need the shell's level 2; c) as the maintainer names.

11.11.5.3 The questions of the test categories that this file's labels
and options build stay open in 11.1.5, the built option of each being
this file's form: the grain of a label (11.1.5.3); the smoke-test
suites, whose built option makes `suites`, by its first two rungs, and
`fresh` this file's `smoke-test` roots (11.1.5.4); the 2 minutes
(11.1.5.5); options and defaults, whose option b) would make this file,
run alone, run every suite (11.1.5.6).

11.11.5.4 The about 70 other local imports of sibling modules after
`sys.pycache_prefix`, the pattern of `test_wire.py` and `test_all.py`:
listed by the earlier job for the maintainer to decide, and not answered
(4.7.14). Listed, not changed.

11.11.5.5 On the test page `probe.fault` always finds the TAP `<pre>`;
no rung on that page calls it today: one of the findings of 4.7.14, which
neither the project rules nor this file's expected design settle. Listed,
not changed.

11.11.5.6 The page names `_ENGINE_PAGE = "test_engine"`, built from
`html/engine.html`, and `_TEST_ENGINE_PAGE = "test_engine_hook"`, built
from `html/test_engine.html`, read the wrong way round, as an earlier
audit recorded: one of the findings of 4.7.14, which neither the project
rules nor this file's expected design settle. Listed, not changed.

11.11.6 Candidates. Each is checked by task 1.19 but where marked.

11.11.6.1 `_KEY_ENTER`, `_KEY_INTERRUPT`, `_EXTRAS_NONE` and `_EXTRAS_KEY`
stand after their classes `KeyStroke` and `ServerExtras`, not at the top
of the file: the constants rule. Older than the earlier job.

11.11.6.2 Names of one word in `_PROBE_KIT`: `probe.pattern`, `thrown`,
`hit`, `view`, `views`, `viewport`, `canvas`, `fault`, `outcome`, `rows`,
`focus`, `permit`, `history`, `widths`, `sink`, `summary` and `receiver`.
Expected: two English words. Checked by the stage reviewer (12.5): the
rung names of three words, `rung_test_engine_start`,
`rung_ui_put_largest`, `rung_level_two`, `rung_compact_auto` and
`rung_refused_role`; expected two English words.

11.11.6.3 Withdrawn: `probe.fault` finding the TAP `<pre>` on the test
page is open (11.11.5.5).

11.11.6.4 A smoke run starts the stub HTTP server, which no smoke rung
needs, against 11.11.3.3. S: the design, written and not built, starts the
stub server only when a rung needs it.

11.11.6.5 The rung timer cannot fire during a DevTools call, and only
`CheckFailed` names the rung, against 11.11.3.12: a timer expiring is a
failure that names the rung.

11.11.6.6 A mutable `Protocol` attribute makes `RunContext(browser, ...)`
a pyright strict error, against 11.11.3.5.

11.11.6.7 The stub server swallows a request for an unexpected path; it
fails loud by the no fallbacks rule.

11.11.6.8 `tap_check` tallies failures; the first failure only is
reported, and nothing tallies.

11.11.6.9 `tap_failures` zips two different line splits with
`strict=True`.

11.11.6.10 The roots take `debug` and `provider.scripted` from the
checkout's `settings.json`; the record names no other form.

11.11.6.11 The `SIGALRM` handler is left installed, and a port is released
before its reuse; the driver's alarm runs around this test in a smoke run.

11.11.6.12 The stub holds the token, open and closed before open requests
with no timeout, a gap its writer recorded, against 11.11.3.12.

11.11.6.13 Withdrawn: the page names read the wrong way round are open
(11.11.5.6).

11.11.6.14 `_WIRE_SECONDS` 120 and `_DRAIN_SECONDS` 120 copy the lengths
of `ts/wire.ts`, as their writers recorded; no class was given.

11.11.6.15 Checked by the stage reviewer (12.5): three comments hold a `;`
outside a code span, above `rung_early`, `ui_request` and
`rung_ui_put_largest`, which `test_posix.py`'s comment check refuses:
severity 1, as it stops `test_posix.py` once the question of the banner of
`xsjs_install.ps1` is answered.

11.11.6.16 Checked by the stage reviewer (12.5): `rung_order` is racy.

11.11.6.17 Checked by the stage reviewer (12.5): `rung_long` prints an
unmeasured 0.0 ms, against the rule of no fake data.

11.11.6.18 Checked by the stage reviewer (12.5): `rung_single` proves
nothing.

11.11.6.19 Checked by the stage reviewer (12.5): `rung_desync` clicks
Reload without the hit check.

11.11.6.20 `probe.wire_pending` of `_PROBE_KIT` reads the `WirePort`'s
private `socket` and `poll_id`, a gap its writer recorded with options a)
to d), whose text is lost. The approved form of the drain poll rung uses
it; the approval names the sleep and the one check, not the read. The
rung's side is the stage reviewer's (12.5.5.4.8); the probe is task
1.19's.

11.11.7 Seams.

11.11.7.1 `BrowserDriver`, `DriverClient` and `LifecycleEvents` mirror
`python/devtools.py`, and `page_ready` calls `page_build`: both task
1.18's. A change task 1.18 makes there reaches task 1.19 as a request,
and task 1.19 receives first.

11.11.7.2 `LabelBook`, `options_add` and `tap_consumer` are task 1.9's,
and `python/test_all.py` (task 1.9) calls `main([option])`.

11.11.7.3 `replay_build`, `ReplayStep` and `ReplaySequence` are task 1.17's.

11.11.7.4 The two TAP documents and their order come from `ts/test_all.ts`,
and `test_ui_tasks` from `ts/test_hook.ts`, both task 1.20's.

11.11.7.5 The probes read the `ts/` modules of tasks 1.20 to 1.30, among
them the private `socket` and `poll_id` of `WirePort` (`ts/wire.ts`, task
1.23) and the `kill_*` exports of `ts/test_substrate.ts` (task 1.24). A
probe change that needs a change there is a request to that owner, which
receives first.

11.11.7.6 `substrate.Store` (task 1.14) places the scripts and values;
`echo_loop.py`, `stall_loop.py`, `main_loop.py`, `bootstrap.py` and the
seeds (task 1.16) are the server the roots run.

11.11.7.7 The requests of tasks 1.5 to 1.7 on the rungs come to task
1.19, which applies them in this file.

11.12 Task 1.20, the TypeScript test harness.

11.12.1 Owns: `ts/unittest.ts`, `ts/test_unittest.ts`, `ts/tap_producer.ts`,
`ts/test_tap_producer.ts`, `ts/test_all.ts`, `ts/test_hook.ts`. The task is
the steward of the module tables of `ts/test_all.ts` (`first_modules`,
`page_modules`, `worker_modules`): the census of task 1.1 sends it every
test module the tables miss or hold twice.

11.12.2 Reads: `API/ts/unittest.d.ts`, `API/ts/tap_producer.d.ts`,
`API/ts/lines.d.ts` (`tap.line`); `python/tap_producer.py`, the twin, and
`python/tap_consumer.py`, which checks the stream; `ts/boot.ts`
(`boot.test_page`, `boot.test_worker`, `boot.test_engine`), `ts/page.ts`
(`page.test_engine`), `ts/worker_ai.ts` (`names_full`, `worker.tests`);
`ts/tsconfig.test.json`, whose order the tables follow; `html/test.html`,
`html/test_engine.html`; `python/engine_tap.py`, the server's `tap.line`
handler; the rungs "stage 0: typescript suites" and "stage 0: typescript
suites in order" of `python/test_browser.py`.

11.12.3 Expected.

11.12.3.1 Purpose: the TypeScript half of the test harness, run in the
browser, which is the one JavaScript runner. The maintainer asked for "a
tap JS and PY producer custom written and a PY consuper custom written
following the tappy apis but just implement the code you need", with tests
of their own run before the rest, and a way to declare that a suite must
fail in a stated way and count that as success (4.1). tappy is not
downloaded; compatibility with it is tested later.

11.12.3.2 `ts/unittest.ts` is the TestCase harness: `TestCase`,
`TestSuite`, `TestLoader`, `TestResult` and the asserts the tests use, with
Python's names, all synchronous, as `API/ts/unittest.d.ts` declares, plus
the run methods of 4.5 (the `TestCase` constructor taking the method name,
`id()`, `run(result)`, `TestSuite.run(result)`, and the `TestResult`
members `shouldStop`, `startTest`, `addSuccess`, `addFailure`, `addError`,
`addSkip`), and `unittest.expectedFailure(method)`, `addExpectedFailure`,
`addUnexpectedSuccess` and a public `unexpectedSuccesses` count, recorded
API additions.

11.12.3.3 Its output text is identical to Python's for the same outcomes:
failure texts copy Python's; `AssertionError` carries its name on the
prototype.

11.12.3.4 `ts/tap_producer.ts` is the producer, in the namespace
`tap_producer`, with the Python producer's names: `Tracker` (`add_ok`,
`add_not_ok`, `add_skip`, `set_plan`, `generate_tap_reports`),
`TAPTestRunner(failfast)` with `set_stream`, `run`, `module_run(module,
load)` and `run_end()`, `TAPTestResult`, and `report_html(text)`, as
`API/ts/tap_producer.d.ts` declares but for the recorded departures of
11.12.4.

11.12.3.5 The line grammar is D12, the TAP grammar default (4.4): each
module's block is indented four spaces and starts with its plan `    1..N`;
no `# Subtest` line; points carry the bare method name; a failfast block is
its plan, its points, the diagnostics and `Bail out! failfast`. After the
block comes the parent line `ok N - <module>` or `not ok N - <module>`.
Diagnostics are lines `    # ` holding the error's `stack`.

11.12.3.6 Each block's name is the test module's name, such as `test_i18n`.

11.12.3.7 A point is written once all of a test's outcomes are in; it takes
its word and directive from the first failing outcome and writes the others
as further diagnostics, as the Python producer does.

11.12.3.8 An expected failure is written `not ok N - <method> # TODO
expected failure` and counted as passed; an unexpected success is a `not
ok` point with `unexpected success`, as in Python.

11.12.3.9 The producer is exercised on every way a TypeScript run can fail,
each as an expected failure of a suite: a failing assertion and an
exception raised in a test; errors in `setUp`, in `tearDown`, and in
`tearDown` after a failure; `expectedFailure` and an unexpected success; a
skip; failfast ending the run with `Bail out!`; a module that does not
load. `subTest` and the class and module fixtures are left out because the
TypeScript harness has none.

11.12.3.10 The expected failure mechanism lives in the producer's test
module: `stream_expect`, `stream_reduce` and `runs_find`, with the
non diagnostic lines compared exactly and each diagnostic run required to
contain the stated lines in order, and tests of its own.

11.12.3.11 The stage 0 proof this task shares with task 1.9: one passing,
one failing, one raising and one skipped method give identical TAP in both
languages as one subtest block, which `tap_consumer` accepts. Task 1.4
checks the identity (12.4).

11.12.3.12 `report_html(text)` marks each `not ok` point with its
diagnostic lines, whole lines, and a parent `not ok` line alone; it escapes
`&`, `<` and `>` only and leaves the bail out line unmarked. The highlight
was requested and is not decoration; it is Unconfirmed in the plan.

11.12.3.13 `ts/test_all.ts` is a frozen namespace `test_all` whose one
export is `suites_run()`. On the UI thread (`self.name === ""`) it calls
`boot.test_page(page_run)`; in the worker, `boot.test_worker(worker_run)`.

11.12.3.14 Each thread makes one `TAPTestRunner`, whose `set_stream`
callback sends each line as it is produced as the notification `tap.line
{language: "typescript", text}` with `line_notify`, routed by the hook's
owner table: on the UI `tap.` goes to `ai`, in the worker to `server`. The
server appends each to `<root>/tap/typescript.tap` unbuffered, so a hang
leaves the lines before it on disk.

11.12.3.15 Each thread runs the blocks `test_tap_producer` and
`test_unittest` first, from `first_modules`, then its own table in the
order of `ts/tsconfig.test.json`, each module's reader called inside the
arrow passed to `module_run`; it stops at the first `false` and then calls
`run_end()`.

11.12.3.16 The UI suite runs first and then sends `worker.tests` to the
worker, so every UI line is on the wire before the worker's suite starts;
`typescript.tap` holds the UI's document, then the worker's, each from
`TAP version 14`.

11.12.3.17 The UI thread writes `tap_producer.report_html` of its own
stream into `#tap_output` of `html/test.html`.

11.12.3.18 `ts/test_hook.ts` is in the test bundle only. It exports
`engine_run(): void` and sets the global `test_ui_tasks` on the test engine
page, `html/test_engine.html`, whose worker script calls
`test_hook.engine_run();`. Through it a browser rung submits tasks from the
UI's live queue (`page.test_engine`, `boot.test_engine`). The production
page carries no test code.

11.12.3.19 Every test module of the bundle stands in exactly one table, so
that no TypeScript suite is left unrun; the tables carry no label of their
own: the TypeScript modules carry the label `smoke-test` of the rung
"stage 0: typescript suites" that runs them.

11.12.3.20 Test rules (3): a test that expects an error compares the
message with the `i18n` text, never only a base class; a fixture reads
`document` and other thread bound globals in `setUp`, never at
construction or bundle load; no test leaves state another test sees; no
suite registers a type that the hook or another suite on the same thread
registers.

11.12.3.21 Messages of `unittest` and `tap_producer` are plain English, not
`i18n`, so the TAP tests load while `i18n/en-US.json` is missing. The
module has no `i18n` prefix.

11.12.3.22 Two English words in every function and class name, one comment
line per construct, one frozen `constants` object per module (3).

11.12.4 Decided, not a finding.

11.12.4.1 `typescript.tap` holds two TAP documents, the UI's then the
worker's, each with its own plan, where the plan says one TAP plan per
language per run. The writer recorded it as needed: a third `language`
value would change `TapLine` and the server's languages, and numbering
continued across the two threads would need a fixed type; it was rejected.
The browser rung splits the file at `TAP version 14` and requires exactly
two well formed documents with no failure. The order UI then worker was
chosen so that a worker hang loses no UI line (the maintainer's request
that no test output be lost).

11.12.4.2 `failfast` is the constant `false` in `ts/test_all.ts`, recorded
by its writer and carried as a class B item; the rung's timer covers a
hang.

11.12.4.3 `test_tap_producer` and `test_unittest` run on both threads.

11.12.4.4 No per module timer in `ts/test_all.ts`: the timer of the rung
that runs the suites covers a hang.

11.12.4.5 Only the UI's stream is shown on the page.

11.12.4.6 `run_end()`'s result is not used.

11.12.4.7 `worker_ai.names_full()` chooses the name form of the `tap.line`
headers on both threads.

11.12.4.8 The test page registers no stop function: `boot.test_page` does
not call `stop_register`. The writer of the boot module listed it among the
decisions to keep; the earlier review named it again, and the decision
stands. The hook is task 1.28's.

11.12.4.9 `set_stream` takes a line callback per instance, not tappy's
class method; `Tracker` takes a write function; `TAPTestRunner` takes
`failfast`; `module_run(module, load)` and `run_end()` exist because tappy
has no named nested blocks; `run` prints no summary. These depart from the
stubs and from tappy and are recorded as the writer's choices for the
maintainer (4.5); tappy's `yaml_block` and directive objects are left out.

11.12.4.10 `API/ts/tap_producer.d.ts` declares `set_stream(streaming:
boolean)` and `API/ts/unittest.d.ts` lacks the run methods and the
expected failure names; the stubs were not edited because those additions
await the maintainer's acceptance.

11.12.4.11 `Tracker` accepts `class_name` without writing it, passes
diagnostics raw, and keeps `add_skip` though the result does not use it.

11.12.4.12 `report_html` does not mark `# TODO` points.

11.12.4.13 TypeScript `expectedFailure` marks methods in a `WeakSet` from a
class static block.

11.12.4.14 `SkipTest` keeps its class field `name`, so its stack header is
`Error:`; V8's stack header is Unconfirmed.

11.12.4.15 TypeScript diagnostics are `error.stack`, with no `cause` chain.

11.12.4.16 `assertEqual` compares arrays, `Uint8Array` and plain objects by
content; `assertTrue` uses JavaScript truthiness; `assertIn` takes text,
arrays and the own keys of plain objects; `assertRaises` is an
`instanceof` check, and the tests compare messages through their own
helpers.

11.12.4.17 The loader collects a class's own prototype methods named
`test_` in export order, where Python collects inherited names starting
`test`, sorted; the plan says name order is fine.

11.12.4.18 The test class's fixture is nested in it, in both languages.

11.12.4.19 Test files use `override setUp` and `override tearDown`, which
needs TypeScript 4.3 or later; D16 makes `tsc` TypeScript 5.x (4.4).

11.12.4.20 The tables become entries of a name, a label and a reader only
when per module TypeScript labels are built; that design is deferred (4.2)
and `smoke-test` holds for the whole rung. The maintainer's question on the
grain of a label is open with its built option in force (4.8.4.28): the
TypeScript modules stand under the rung that runs them.

11.12.4.21 The module layout `ts/tap_producer.ts` and the names recalled
from tappy's documentation are the built readings (the layout is the
built option of 4.8.4.1); tappy's names are Unconfirmed until tappy is
tested.

11.12.4.22 `tap.line {language, text}` carrying the TAP text, and the
consumer returning plan, pass, fail, skip and well formed, are Unconfirmed
readings of the plan, accepted.

11.12.4.23 `ts/test_hook.ts`, `page.test_engine` and `boot.test_engine` are
accepted API additions (4.5); `page` has no stub and `API/ts/boot.d.ts`
leaves the test only functions out.

11.12.4.24 The UI runs `test_i18n` and the worker runs `test_verbose`, each
the writer's choice of thread.

11.12.4.25 Unconfirmed and accepted, the testing phase's to check: that a
module's namespace object is assignable to the index signature of the
readers in the tables of `ts/test_all.ts`, and, in its writer's words,
"`bufferedAmount` inside a task".

11.12.5 Open, for the maintainer.

11.12.5.1 None recorded for these files. The formatter's split of the
hooked line of `html/test_engine.html`, which breaks
`test_template_hooked`, belongs to task 1.18 (4.7).

11.12.6 Candidates.

11.12.6.1 `ts/test_unittest.ts`: tests that assert only a base class, where
a test that expects an error must compare the `i18n` or literal message
text (3). A review of the earlier job named this file among five.

11.12.6.2 `self.name` is tested as `""` in `test_all.suites_run` and as
`"ai"` in `boot.boot_run`: two tests of one fact that disagree on which
value is checked. Check `ts/test_all.ts` against `ts/boot.ts`; a change
on the boot side is task 1.28's.

11.12.6.3 Output identical to Python's for the same outcomes: the same
four methods (passing, failing, raising, skipped) give the same TAP text
from `tap_producer.ts` as from `tap_producer.py`, but for the stack lines.
With task 1.4 (12.4).

11.12.6.4 Every way a TypeScript run can fail of 11.12.3.9 has its
expected failure test in `ts/test_tap_producer.ts`, and the producer's and
the harness's tests run first on each thread.

11.12.6.5 The tables of `ts/test_all.ts` against `ts/tsconfig.test.json`:
each test module in the bundle once, in bundle order, on the thread whose
globals it needs (`test_page` on the UI only).

11.12.6.6 Tests that leave registered handlers, ring lines or a scheduled
step in the thread's live state, so that a later block sees them. The
earlier review recorded this for the TypeScript core's tests without
naming the files; check this task's tests for it.

11.12.7 Seams.

11.12.7.1 Task 1.9 owns the Python producer and consumer: a change of the
TAP text is made in both producers, the Python side first, and checked by
task 1.4.

11.12.7.2 Task 1.28 owns `ts/boot.ts`: the hooks `test_page`,
`test_worker`, `test_engine`, their owner tables and the `self.name` test.
A change of a hook's signature is received by `ts/boot.ts` first.

11.12.7.3 Task 1.29 owns `ts/page.ts` (`page.test_engine`).

11.12.7.4 Task 1.18 owns `ts/tsconfig.test.json`, `ts/tsconfig.json`,
`html/test.html` and `html/test_engine.html`: a new test module enters the
bundle list there first, then the table here.

11.12.7.5 Task 1.19 owns `python/test_browser.py`, which splits
`typescript.tap` into two documents and checks their order; a change of
the document count or order is received there first.

11.12.7.6 Task 1.15 owns `python/engine_tap.py`, which accepts the
`language` values of `tap.line`.

11.13 Task 1.21, the first TypeScript modules.

11.13.1 Owns: `ts/error_overlay.ts`, `ts/utility.ts`, `ts/ui_strings.ts`,
`ts/settings.ts`, `ts/i18n.ts`, `ts/verbose.ts`, `ts/overlay.ts`, and their
seven tests `ts/test_error_overlay.ts`, `ts/test_utility.ts`,
`ts/test_ui_strings.ts`, `ts/test_settings.ts`, `ts/test_i18n.ts`,
`ts/test_verbose.ts`, `ts/test_overlay.ts`. The `i18n` prefixes `utility.`
and `overlay.` are this task's; `settings.` and `verbose.` are used in both
languages and are written by task 1.13 (6); `error_overlay`, `ui_strings`
and `i18n` have none.

11.13.2 Reads: `API/ts/error_overlay.d.ts`, `utility.d.ts`,
`ui_strings.d.ts`, `settings.d.ts`, `i18n.d.ts`, `verbose.d.ts`,
`overlay.d.ts`, and in `API/ts/lines.d.ts` the payloads `Fault`,
`SettingsSet`, `SettingsPut`, `VerboseLine`, `OverlayLine`; `ts/page.ts`,
`ts/worker_ai.ts`, `ts/boot.ts`, `ts/queue.ts` (`sink_attach`,
`VerboseBatch`); `python/settings.py`, `python/i18n.py`,
`python/verbose.py` (the twins); `python/page_build.py` (the substitution
of the strings table); `settings.json`, `i18n/en-US.json`;
`html/engine.css` (the overlay's `<pre>` elements).

11.13.3 Expected.

11.13.3.1 The first four scripts. The page's bundle begins, in this order,
with `error_overlay`, `utility`, `ui_strings` and `settings`, then `i18n`
and the rest in reference order. tsc compiles every `ts/` file with
`module` none and `outFile` into one classic script; each file defines one
frozen object named after its module.

11.13.3.2 The page opens in that order too: the four scripts, then
`page.ts` creates the AI worker, a Blob URL of the same bundle whose entry
is chosen by `self.name`.

11.13.3.3 `error_overlay.ts` has one job and depends on nothing. Its texts
are plain English constants, not `i18n`.

11.13.3.4 The fault screen. `overlay_install()` installs the handlers: on
the window, `error` and `unhandledrejection`, and resource load failures in
the capture phase. In the worker, detected by `typeof document ===
"undefined"`, the same two events post `{0: {t: "fault"}, thread: "ai",
message, stack}` to the UI with `self.postMessage` instead; `page.ts`
passes such a message to `overlay_show`.

11.13.3.5 `overlay_show(message, stack)` replaces the screen by
`document.write` with a `<pre>` holding the message and the call stack,
calls `document.close()` after the write, runs the stop function, which
closes the wire and terminates the worker, and offers Reload, which is
`location.reload()`.

11.13.3.6 Only the first fault is shown: a private first fault flag of
`error_overlay.FaultScreen`, to whose one page instance the module
functions pass through.

11.13.3.7 `stop_register(fn)` is called once, by `page.ts`; a second call
throws.

11.13.3.8 A resource failure's message is "Failed to load <tag> <src or
href>": it names `src`, else `href`, and throws when the element has
neither, as for `<object data>` and SVG `xlink:href`. The capture listener
ignores targets that are not an `Element`.

11.13.3.9 Every fault ends on this screen and in Reload, and nothing in
flight is retried: a thrown error, a rejection, a failed resource, a
`fault` from the worker, an arriving `error` line, a close with no `error`
line, a desync, a timer expiring. Recovery is the full page reload, the
tested path; the new page replicates from the server. A reconnect in the
same page was decided against by the maintainer.

11.13.3.10 `utility.ts` holds the non essential error handling,
`error_wrap(message, cause)` (an `Error` with `cause` set) and
`fail_now(message)`, and the single door routines the modules below share,
all synchronous: `sha256_hex`, `utf8_encode`, `utf8_decode`,
`base64_decode`, `json_text`, `time_now` (milliseconds since the epoch), as
`API/ts/utility.d.ts` declares.

11.13.3.11 `sha256_hex` is implemented in the file, not by
`crypto.subtle`, its constants computed at load from the primes.

11.13.3.12 `utf8_encode` throws `utility.text_refused` on a lone surrogate.

11.13.3.13 `utf8_decode` is strict (`fatal: true`, `ignoreBOM: true`) and
wraps the platform's `TypeError` as `utility.bytes_refused` with `cause`.

11.13.3.14 `base64_decode` is strict, D26 (4.4: `utility` messages go
through `i18n` and `base64_decode` is strict): the standard alphabet, full
padding, no white space and zero unused bits, else
`utility.base64_refused`.

11.13.3.15 `json_text` writes no white space outside strings and refuses
only NaN and the infinities (`utility.number_refused`) and a value JSON has
no text for (`utility.value_refused`). A double beyond 2^53 passes: the
maintainer asked that floats above 2^53 sent by Python not fault the
TypeScript queue, and the fix made `utility.number_check` and the JSLB
re-encoder refuse NaN and the infinities only.

11.13.3.16 Every `utility` message goes through `i18n`, called at call
time, as `utility` precedes `i18n` in the bundle.

11.13.3.17 `ui_strings.ts` is the strings table `ui_strings.table`, frozen:
`page_build.py` substitutes the text of `i18n/en-US.json` unmodified for
the token `I18N_TABLE_JSON`, the one build step the one file rule requires,
so both languages read the same file.

11.13.3.18 `settings.ts` is hand written; nothing is built from
`settings.json`. The `Settings` interface of `API/ts/settings.d.ts` holds
exactly `debug`, `queue_synchronous`, `verbose_level`, `verbose_ring`,
`line_max`, `blob_max`, `overflow_bytes`, `chunk_bytes`, `srv_buf_size`,
`media_db_bytes`, `files_browser_bytes`, `db_soft_bytes`,
`turn_compact_turns`, `long_task_ms` and `provider {scripted,
timeout_seconds}`.

11.13.3.19 `settings_set(value)` is called once per thread, from `hello`;
outside debug mode the object is deep frozen and refuses a write; a second
call throws `settings.already_set`.

11.13.3.20 `settings_get(id)` reads by id, nested keys joined by `.` as in
`provider.timeout_seconds`; it throws `settings.not_set` before
`settings_set` and `settings.unknown_id` on an unknown id.

11.13.3.21 `settings_put(id, value)` works in debug mode only, else
`settings.put_denied`; it changes the live value and sends `settings.put`,
which rewrites the file in the root for the next `hello`.

11.13.3.22 The sending goes through `settings.Sender` and
`sender_register(sender)`: the sender receives the payload `{settings:
<copy>}`, not a line, because `settings` comes before `jslb` and `queue`;
each thread that offers `settings_put` registers one sender once, which
builds the `settings.put` line and submits it. A second registration throws
`settings.sender_twice`; a put with no sender throws `settings.no_sender`
before changing anything.

11.13.3.23 `settings.ValueStore` (`value_set`, `value_get`, `value_put`,
`sender_register`) holds the state; the module functions delegate to one
private instance, so tests exercise once per thread state on their own
instances.

11.13.3.24 The checks of a settings object name a missing key
(`settings.key_missing`), an extra key (`settings.key_extra`) and a wrong
type (`settings.type_wrong`).

11.13.3.25 `i18n.ts` declares the global function `i18n(name, ...args)`,
whose module object is the function. It throws on a missing name,
inherited names refused, and when the placeholder count differs from the
argument count. The placeholders match `\{(0|[1-9][0-9]*)\}`, their index
set must equal 0 to n-1, and the text is replaced in one pass. The rule is
the same as `python/i18n.py`'s (task 1.4 checks it, 12.4).

11.13.3.26 The global `i18n_format(name, text, args)` lets a test supply
the text.

11.13.3.27 `i18n` is called with a literal name at every call site (3).

11.13.3.28 `verbose.ts` has no level: the runtime has only the `debug`
flag, by the maintainer's words "for now only have verbose levels for shell
scripts. the server and runtime only have a debug flag" (4.1). Its names
are those of `API/ts/verbose.d.ts`: `log(text)` writes one line to the
thread's ring of `verbose_ring` lines and hands it to the sink;
`history_get(count)` returns the last `count` lines, oldest first;
`sink_set(fn)` sets the one consumer, the thread's queue, which batches the
lines into `verbose.put` when `debug` is true. `verbose.LineRing`, with a
`size_get` reader, is the accepted addition that tests build rings with
(4.5).

11.13.3.29 A line is `lines.VerboseLine {at, text}`, with no `level`.

11.13.3.30 `sink_set` twice throws `verbose.sink_twice`; the sink gets only
the lines written after it is set; the ring takes the line before the sink
is called. `history_get` refuses a bad count with `verbose.count_invalid`;
a bad `verbose_ring` is `verbose.ring_invalid`.

11.13.3.31 `overlay.ts` holds the read only debug overlays of ttys 1 and
up on the UI thread, as `API/ts/overlay.d.ts` declares: `new
Overlay(container, ring)` creates, per tty, a hidden read only `<pre>` on
its first use; `line_add(tty, text)` keeps the last `ring` lines and sets
`textContent`, newest last; `overlay_toggle(tty)` flips `hidden`. It
installs no listener and no style and touches no `document` at load.

11.13.3.32 The overlay of a shown tty keeps its newest line in view
(`Overlay.end_show`).

11.13.3.33 The overlays are debug only, fed by `overlay.line {tty, text}`
lines that the worker renders as the line's JSON text followed by one
`<blob "n"=K>` tag per blob, K the header key from 1. ctrl-n toggles tty n
in `page.ts`. The tty 1 overlay does not show the `verbose.put` lines it
forwards.

11.13.3.34 Two states are accepted by the maintainer: with both shown, the
overlay below the console scrolls the console's top rows out, and the
subtitle band lies over the bottom strip of the image. Any other
unintentional invisibility is a bug.

11.13.3.35 Tests: the digests of the empty message, "abc", the 56 and 112
byte standard messages, one million letters a and a subarray view; UTF-8 of
1 to 4 bytes, a BOM and invalid sequences; base64; `json_text`;
`error_wrap`; `fail_now`; `time_now`; the frozen surface; the lone
surrogate; `overlay_show` with `document.write` and `document.close`
stubbed in `setUp`; `test_first_only`; `test_stop_twice`; the overlay's
synchronous tests on a detached `div`. Every expected error is compared
with its message text (3).

11.13.3.36 Owed to the browser rungs (12.5), not to TestCases: a thrown
error and a rejection reaching the `<pre>` screen; a failing script and
image reaching the capture handler, with `src`, `href` and neither; a Blob
worker posting `fault`; the stop function after the write; a Reload
click; a fault while the parser runs a script; the module `overlay_show`
showing the first fault only; ctrl-n handling with ctrl-0 staying the
console view; `overlay.line` reaching `line_add`; the debug gating; the
real CSS showing and hiding an overlay; the verbose singleton in the live
state, the queue installing its sink, and the `verbose.put` batching.

11.13.4 Decided, not a finding.

11.13.4.1 `error_overlay.FaultScreen` exists beside the three functions of
the stub, an accepted addition (4.5), so that a test does not flag the test
page for good; a module flag and a flag in the document were rejected.

11.13.4.2 The worker is detected by `typeof document === "undefined"`:
`WorkerGlobalScope` does not compile under the DOM library and `self.name`
was rejected.

11.13.4.3 `error_overlay`'s texts, the second `stop_register` message
among them, are literal English, as the module depends on nothing.

11.13.4.4 `<object data>` and SVG `xlink:href` throw the missing address
error; adding `data` was the alternative not taken.

11.13.4.5 The escape helper of `error_overlay` is not exported, as the stub
lists three names.

11.13.4.6 The overlay screen writes `document.close()` after the write.

11.13.4.7 The SHA-256 constants are computed from the primes, not
tabulated; check them first if a digest test fails.

11.13.4.8 The strict base64 pattern narrows its last character class to
characters whose unused bits are zero, so "Zh==" is refused; a re-encode
check was the alternative.

11.13.4.9 `json_text` drops properties whose value is `undefined` and
writes `-0` as `0`.

11.13.4.10 `API/ts/utility.d.ts` still says `json_text` throws on ints
beyond 2^53; the code refuses NaN and the infinities only, by the fix
asked for in the maintainer's request on floats above 2^53. The stub text
is the maintainer's to change (4.6).

11.13.4.11 The `settings.Sender` form: a sender of a line with a short or
cast full name header built inside `settings`, `settings_put` returning the
payload, and a replaceable sender were rejected.

11.13.4.12 `settings.ValueStore` exists so tests need neither a reset
hook nor the singleton; both were rejected.

11.13.4.13 The settings errors use `i18n` by call time reference, though
`i18n` comes later in the bundle.

11.13.4.14 Outside debug mode `settings_set` freezes the passed object in
place; a sender that throws leaves the live value already changed; there is
no value validation on the client; setting `debug` false in debug mode
ends later puts. The writer recorded these as its choices.

11.13.4.15 An object value at a scalar key names the type `Object` in
`settings.type_wrong`.

11.13.4.16 The class `TestLiveSettings` was dropped by the earlier job's
order; the tests compare thrown messages with `i18n` text through
`message_thrown`.

11.13.4.17 `provider` holds `scripted` and `timeout_seconds` only; the
provider's `base_url`, `chat_model` and `image_model` live in
`provider.json`, and `ts/test_settings.ts` expects those three ids to throw
`settings.unknown_id`.

11.13.4.18 `i18n_format` is a global, so a test can supply text; scanning
the real table, a table parameter and an unfrozen table were rejected.
`ts/test_i18n.ts` reads `ui_strings.table`.

11.13.4.19 `i18n` formats its arguments with `String(arg)`, which differs
from Python's `str` for booleans, `null` and floats, a difference its
writer recorded.

11.13.4.20 `ui_strings.table` freezes the substituted `I18N_TABLE_JSON`.

11.13.4.21 `verbose.ts` has no `level_set` and no level argument; the
`verbose_level` setting is the console shell's alone. The maintainer's
deferred design of runtime levels is not built (4.2).

11.13.4.22 The ring is an array trimmed with `splice`; the sink is not
given the ring's earlier lines when it is set (a replay at install was
rejected); there is no re-entrancy guard, so the queue's flush must not log
into its own batch.

11.13.4.23 The verbose singleton in the live state, the queue's sink and
the batching are proven by browser rungs, not by TestCases.

11.13.4.24 The `Overlay` constructor throws `overlay.ring_invalid` unless
`ring` is a whole number of 1 or more, an addition with one string.

11.13.4.25 `overlay_toggle` on a tty with no lines creates and shows an
empty `<pre>`; throwing, doing nothing and creating only in `line_add` were
rejected.

11.13.4.26 `textContent` is rewritten from all kept lines on every
`line_add`; one text node per line and a rewrite only while shown were the
recorded alternatives.

11.13.4.27 The `<pre>` elements are appended in the order of first use.

11.13.5 Open, for the maintainer.

11.13.5.1 A `verbose.log` line written before `settings_set` throws,
because the ring reads `verbose_ring` from the first line. The maintainer
did not approve it with the class B items, and it stands as the question
"a log line written before the settings are set throws; is such a line
ever wanted?". Its four options were written in a document that no longer
exists.

11.13.5.2 The 55 byte SHA-256 padding boundary is untested, since no digest
may be recalled from memory. Options: a) the maintainer copies the entry
`Len = 440` of the NIST CAVP file `SHA256ShortMsg.rsp` into a test
`test_padding_boundary`; b) `python/vectors_make.py` emits a `hashlib`
digest of a 55 byte message for the test to read.

11.13.6 Candidates.

11.13.6.1 Tests that assert only a base class, against the rule that a test
expecting an error compares its message (3): `ts/test_verbose.ts` (16 such
tests recorded), `ts/test_overlay.ts`, `ts/test_i18n.ts`.

11.13.6.2 `error_overlay`'s `thrown_stack` returns `""` where a value has no
stack, and `overlay_show` skips the stop function when none is registered;
the earlier review listed both among "defaults and unreachable branches".
Check each against the no fallbacks rule. The test page registers no stop
function by decision (11.12.4.8).

11.13.6.3 The worker's `error` listener does not cancel the event, so the
browser may also report the error and the page may show file, line and
column without a stack.

11.13.6.4 `settings_put` in debug mode changes only the UI's copy: the
relay sends `settings.put` from the UI to the AI worker, which submits it
to the server, and the AI's copy keeps the old value. The plan has
`settings_put` change the live value and send `settings.put`. Seam with
task 1.28.

11.13.6.5 Tests that leave ring lines or handlers in the thread's live
state, which a later test sees.

11.13.6.6 One word identifiers against the two word rule (3): the
interface `Leaf` in `ts/settings.ts` and the interface `Entry` in
`ts/overlay.ts`.

11.13.6.7 The module level settings functions are covered only through
`ValueStore`, by the writer's own record.

11.13.6.8 The fault screen does not show `cause` chains, a gap its writer
recorded; the plan names the message and the call stack.

11.13.6.9 `overlay.line_add` and `overlay_toggle` do not validate `tty`, a
gap its writer recorded.

11.13.7 Seams.

11.13.7.1 Task 1.29, `ts/page.ts` and `html/engine.css`: `stop_register`
exactly once; worker messages shaped `{0: {t: "fault"}, ...}` passed to
`overlay_show`; an `Overlay` on a live container with `verbose_ring`;
`overlay.line` decoded into `{tty, text}`; ctrl-n mapped to
`overlay_toggle(n)`; the UI's settings sender registered once.
`html/engine.css` must not set `display` on the overlay's `<pre>` elements,
since an author `display` overrides `[hidden]`.

11.13.7.2 Task 1.28, `ts/worker_ai.ts` and `ts/boot.ts`: the worker entry
calls `overlay_install()` first; `settings_set` from `hello`, then
`settings.set` to the UI; the worker's settings sender; the settings
relay of 11.13.6.4, whose fix touches the relay there; the UI to AI lane
is its own `MessageChannel`, because the worker's `error_overlay` posts
faults with `self.postMessage`.

11.13.7.3 Task 1.18: the order of the first four scripts in
`ts/tsconfig.json`, and the substitution of `I18N_TABLE_JSON` by
`python/page_build.py`. Its candidate that `overlay_install()` runs only
from the last script, so that a throw while the bundle or xterm.js loads
leaves a blank page, is shared with this task and task 1.28.

11.13.7.4 Task 1.13 writes every `settings.` and `verbose.` string; a new or
reworded name of those prefixes is a request to it. Task 1.4 compares
`settings`, `verbose` and `i18n` with their Python twins; task 1.9 owns
`python/i18n.py`.

11.13.7.5 Task 1.12, `ts/jslb.ts`: its re-encoder's number check changed
with `utility.number_check`; a change of one is made in the other.

11.13.7.6 Task 1.24, `ts/substrate.ts`: its candidate that the incremental
SHA-256 copies `utility`'s block function; a new public name in `utility`
is an interface change, proposed and not made (6).

11.13.7.7 Task 1.22, `ts/queue.ts`: `sink_attach(verbose.sink_set,
settings.settings_get)` and `VerboseBatch` call this task's names.

11.14 Task 1.22, the TypeScript dispatcher and task manager.

11.14.1 Owns: `ts/dispatch.ts`, `ts/test_dispatch.ts`, `ts/queue.ts`,
`ts/test_queue.ts`. The `i18n` prefix `queue.` is this task's;
`dispatch.` is used in both languages and is written by task 1.13 (6).

11.14.2 Reads: `API/ts/dispatch.d.ts`, `API/ts/queue.d.ts`,
`API/ts/lines.d.ts` (`Wake`, the lane table); `python/dispatch.py`, the
twin; `ts/jslb.ts` (`field_get`, `header_make`, `line_make`);
`ts/verbose.ts` and `ts/settings.ts`, which the queue's sink calls; the
ports `ts/wire.ts`, `ts/http.ts`, `ts/media.ts`; every caller of
`handler_register`, `task_submit` and `line_notify`: `ts/worker_ai.ts`,
`ts/boot.ts`, `ts/page.ts`, `ts/agent.ts`, `ts/script.ts`, `ts/mcp.ts`,
`ts/tools_browser.ts`, `ts/console_view.ts`, `ts/substrate.ts`,
`ts/test_all.ts`, `ts/test_hook.ts`; and
`_SYNCHRONIZATION_MODULES` of `python/test_posix.py`.

11.14.3 Expected. The task manager is the one synchronization tool, so its
design is restated whole: the dispatcher first, then the queue's owners,
its submit, sleep and wake, its steps and items, its windows, its blob
moves, its forwarding marks, its trace, and the audit.

11.14.3.1 The dispatcher's names are those of `API/ts/dispatch.d.ts`:
`Reply`, `Sleep`, `task_sleep(state, wait_ids, then_type)`, `Handler`,
`handler_register(type, version, fn)`, `line_dispatch(line)`,
`reply_make(line, payload, blobs?)`, `error_make(line, error)` and
`id_next(port)`. A handler is synchronous.

11.14.3.2 A handler returns one of three things: a finished reply line
built with `dispatch.reply_make(request, payload, blobs)` when the task had
`i`; nothing, for a notification; or a `Sleep` (3). A return of a payload
with no header throws `dispatch.reply_headerless`.

11.14.3.3 `handler_register` keys the registry on the exact pair of type
and version; a second registration of a pair throws
`dispatch.handler_twice`.

11.14.3.4 `line_dispatch` finds the handler by type and version, version
0 by default, and throws `dispatch.handler_unknown` on an unknown pair; a
type that is not text throws `dispatch.type_invalid`, an id that is not a
number `dispatch.id_invalid`.

11.14.3.5 A request whose handler returns nothing throws
`dispatch.request_unanswered`. A `Sleep` passes through. A reply line gets
`r` set to the request's `i`, in the reply header's own name form.

11.14.3.6 A line with no `i` may return nothing, a `Sleep`, or a reply that
already carries `r`: the wake of a task that owes a reply. Any other reply
to a notification throws `dispatch.notification_replied`.

11.14.3.7 A reply carries `t` and `r` and no `v` or `k`; its `t` is the
request's `t`. `error_make` builds the one `error` line of a throw, with
`message`, `stack`, and `r` when the request had `i`.

11.14.3.8 `stack` is the `Error`'s own `stack`, with no `cause` chain; an
`Error` with no stack throws `dispatch.stack_missing`.

11.14.3.9 `id_next(port)` stays in the stub, and no TypeScript module calls
it: ids are one counter per queue (3).

11.14.3.10 The dispatcher relies on `jslb`: `field_get` gives `undefined`
for an absent `id` and `reply` and 0 for an absent version; `header_make`
leaves out `undefined` fields and returns an unfrozen plain object;
`line_make` writes no `b` for no blobs.

11.14.3.11 The rule. The task manager is the only synchronization tool. A
handler that must wait returns a sleep to the task manager, which wakes it
with the replies as a new task. No promise, lock, shared buffer or
`Atomics` exists outside the task manager and the ports it owns.

11.14.3.12 The audit's five modules. `python/test_posix.py` fails on
`await`, `.then(`, `new Promise`, `Atomics` or `SharedArrayBuffer` in any
`ts/*.ts` other than `queue.ts`, `wire.ts`, `http.ts` and `media.ts`, the
four modules that turn an event of the platform (a socket, a response, an
image decoded) into a reply line, and `boot.ts`, the one initialization
module. D29: `async` is not added to the audit (4.4). A DOM listener is an
event, not a promise, so `page.ts` needs no exception.

11.14.3.13 System initialization need not abide by the rules of use, by the
maintainer's rule: the worker's `sqlite3InitModule`,
`installOpfsSAHPoolVfs` and its capacity, the OPFS directory, its file
handles and `createSyncAccessHandle` use promises directly in `boot.ts`; no
port turns them into lines, and no platform port is built in `queue.ts`.
Once initialization has handed the objects over, the rule of 11.14.3.11
holds.

11.14.3.14 A third thread, if a hard need arises, reuses `queue.ts`
unchanged with a new owner table entry.

11.14.3.15 Locking. Every database is on the AI thread and one task runs at
a time, so a running task holds every database. A sleeping task holds
nothing: `transaction_run` is the only way to touch a database and cannot
span a return, so the handler has committed before it sleeps.

11.14.3.16 Owners. One `TaskQueue` per thread: `new TaskQueue(thread,
owners, synchronous)`. A `ThreadName` is `"ui"`, `"ai"`, `"server"`,
`"http"`, `"media"`, `"console"` or `"dom"`: the two threads, the server,
and the ports that turn a platform event into a reply line.

11.14.3.17 A port is anything with `line_post(line, transfer)` and
`line_receive(fn)`, carrying lines one way each direction, in order.
`port_add(thread, port)` connects the port that reaches the named owner; a
second one throws `queue.port_twice`. A port's `line_receive` is called
once, and a port delivers each reply on the port that carried the request.

11.14.3.18 `LocalPort` is a loopback, and the queue adds one for its own
thread; its receiver errors are `queue.receiver_missing` and
`queue.receiver_twice`. `ThreadPort` wraps a `MessagePort` with the blob
buffers in the transfer list; its `onmessageerror` throws
`queue.message_error`, and a message that is not a line throws
`queue.message_invalid`.

11.14.3.19 The owner table maps a type prefix to its owner, and the longest
matching prefix wins; a type that no prefix matches throws
`queue.owner_missing`. Each thread's table also maps its own types to
itself.

11.14.3.20 `task_submit(line, owner?)` and `line_notify(line, owner?)` take
an explicit owner that sends the line straight to that owner's port,
skipping the table (3). A named owner without a connected port throws
`queue.port_missing`; the queue's own thread named as owner runs the line
here. Callers name the owner where a prefix has two (the `kv.` lines and
`mcp` on the AI thread): `mcp.Client`, the agent's provider owner, the
tools.

11.14.3.21 A line arriving on the thread's own loopback port is dispatched
on this thread with no table lookup. Wakes skip the table too.

11.14.3.22 Code that submits a task never knows which port carries it.

11.14.3.23 Submit, sleep and wake. `task_submit` submits a request and
returns its `i`; `line_notify` posts a notification that nothing answers. A
line given to either that already has an id or a reply throws
`queue.submit_marked` or `queue.notify_marked`; a header field that is not a
number throws `queue.field_invalid`, a type that is not text
`queue.type_invalid`.

11.14.3.24 Ids are one counter per `TaskQueue`, shared by all its ports,
from 1 for the life of the thread: D2, request ids are one counter per
thread queue and not per port (4.4). A reply must arrive on the port its
request went to.

11.14.3.25 `task_submit` outside a handler throws `queue.submit_outside`,
as no task could wait for the reply.

11.14.3.26 Every request a handler run submits is named in that run's
sleep, else `queue.wait_missing` when the handler returns. A sleep on an id
the run did not submit throws `queue.wait_unknown`; an id named twice,
`queue.wait_twice`.

11.14.3.27 When every reply in `wait_ids` has arrived, the queue enqueues
one wake line of `then_type` whose payload is `lines.Wake {state,
replies}`, the replies in the order they were submitted whatever order they
arrived in. A task can so re-enqueue itself in another form at another
destination any number of times.

11.14.3.28 A sleep on an empty `wait_ids` wakes at once, so a long job
splits itself with a sleep on `[]`.

11.14.3.29 A wake line carries no `i`. A wake handler that owes a reply
builds it from the original request line kept in its `state`. The queue
carries the request a task owes through its sleeps and wakes, checks a
returned reply against it (`queue.reply_unowed` when it answers no request
the task owes), and posts the finished reply line unchanged to that
request's port; a wake that returns nothing while a reply is owed throws
`queue.reply_missing`.

11.14.3.30 An unknown `r`, a known `r` arriving on another port among them,
is the hard error `queue.reply_unknown`.

11.14.3.31 An `error` line arriving from any port is the hard error
`queue.error_line`, with the remote message and stack: a provider failure
is a fault (3).

11.14.3.32 A `Sleep` is recognized by its shape (`state`, `wait_ids`,
`then_type`), and `task_sleep` validates nothing.

11.14.3.33 Steps and items. The queue dispatches one line at a time; a
handler runs to completion before the next line is dispatched. One port is
one FIFO each way.

11.14.3.34 Outside synchronous mode the queue keeps one queue of items in
arrival order and runs one held item per macrotask, scheduled by a
`MessageChannel` message to itself.

11.14.3.35 Synchronous mode is the setting `queue_synchronous`, debug only.
The queue then keeps two queues, its own items and wakes first, then one
input: before it reads the next line from any port it runs every task it
holds to completion, woken tasks and tasks it posted to itself included. A
sleep that waits on another thread is the only thing that lets an input
through, so a run is deterministic.

11.14.3.36 After the first fault every later step throws `queue.stopped`,
which carries the first fault's message and stack with `cause` set; every
later arrival throws it too, showing the root cause.

11.14.3.37 `depth()` is the number of tasks waiting, running and sleeping,
for the stress test and the synchronous mode check. The queue handles
sleeping tasks and an empty queue.

11.14.3.38 Windows. A `TaskQueue` is a window of `blob_max`: the sum of the
`s` of the blobs of the lines it holds is at most `blob_max`, and a line
that would pass it throws `queue.queue_over`, a fault. The window counts
blob bytes only, never line bytes, which `line_max` bounds line by line; a
cache handle counts its `s`.

11.14.3.39 A line is held from its arrival on any port until it is run or
forwarded; a reply is held until its wake runs; a wake's `state` and the
verbose batch are not counted.

11.14.3.40 `blob_max` is read through the `settings_get` given to
`sink_attach`, so before `sink_attach` the queue bounds nothing: the UI's
queue receives `settings.set` before it has settings.

11.14.3.41 On the UI's path the queue is the first window: a UI put of
`blob_max` + 1 is refused by the AI worker's task queue with
`queue.queue_over` before `wire.ts` sees it.

11.14.3.42 Blob moves. Blob buffers are transferred, never copied:
`task_submit` and `line_notify` move the buffer of every `Uint8Array` blob
with `structuredClone` and a transfer list, a shared buffer moved once (a
view moves its whole buffer), and post a shallow copy; after the call the
caller's `d` is detached. A buffer of shared memory throws
`queue.buffer_shared`.

11.14.3.43 Forwarding. A line arriving on one port whose owner is another
thread is passed with `line_forward` as the decoded object, unchanged, to
its owner's port, which encodes it again; the type is the forwarding
instruction. The owner table on the AI thread maps `verbose.` to `server`,
so a `verbose.put` from the UI reaches the server through the AI worker
with nothing added.

11.14.3.44 The forwarding marks. `line_forward` refuses a line with an id
or a reply with `queue.forward_marked`, because such a line is answered on
the port it came on; a line received from a port whose own thread the
table names as its owner throws `queue.forward_back`, since the two would
pass it back and forth; a line this thread handles itself throws
`queue.forward_local`.

11.14.3.45 A request for another owner is submitted, not forwarded:
replication, for one, submits each committed operation to `"server"` with
an explicit owner and sleeps on it (task 1.28's handlers).

11.14.3.46 The trace. In debug mode the queue logs every submit, notify,
forward, dispatch, sleep, wake and reply through `verbose`, with the
literal names `queue.submit`, `queue.notify`, `queue.forward`,
`queue.dispatch`, `queue.sleep`, `queue.wake`, `queue.reply` and
`queue.reply_received`, each text the line's header 0 as JSON with the from
and to thread, and no other information is needed to reconstruct the
thread's timeline. Outside debug mode it logs none of them.

11.14.3.47 The sink. `sink_attach(sink_set, settings_get)` installs the
thread's `VerboseBatch(thread, settings_get)` (`line_add`, `batch_send`) as
the `verbose` sink, on every queue after `settings_set`, which also turns
on the `blob_max` bound. The batch keeps a line only when `debug` is true,
read per line, leaves out lines logged while a batch is sent, and is sent
as `verbose.put` after every item in both modes, split into lines below
`line_max`; an entry too large alone throws `queue.entry_over` and nothing
is posted.

11.14.3.48 `sink_attach` refuses a thread other than `ui` and `ai`
(`queue.sink_thread`), a second attach (`queue.sink_twice`), and a thread
that owns `verbose.put` itself (`queue.sink_owner`).

11.14.3.49 Tests: `ts/test_dispatch.ts`, synchronous, with unique type and
port names; `ts/test_queue.ts`, synchronous, with a port double, among its
classes `TestOwnerGiven` (the table overridden, a reply from another port
an unknown `r`, an owner without a port throwing for a notification and a
submit, the queue's own thread as owner running here) and `TestQueueLimit`,
and the tests `test_step_waits`, `test_thread_receiver` and
`test_run_twice` with its history comparison. The settings fixture
`settings_make` holds every key of `Settings`, `verbose_level` 1 as in
every other fixture.

11.14.3.50 Owed to the browser rungs (12.5): the scheduling outside
synchronous mode; a `ThreadPort` across a real worker; a `verbose.put`
forwarded from the UI through the AI worker to the server unchanged; a
sleeping task woken by two replies in either order over real ports; the
same run identical twice in synchronous mode; the UI stress test, no task
over `long_task_ms` (5 ms, a soft target reported as a measurement) and no
synchronous network load on the main thread; `sink_attach` on the live
`verbose`; a handler's throw reaching `error_overlay`; the hello relay.

11.14.4 Decided, not a finding.

11.14.4.1 Ids per queue, not per port, where the plan says ids restart at 1
per port: D2, request ids are one counter per thread queue (4.4). The
plan's sentence was left because that default awaits the maintainer's
confirmation. Per port counters with `{port, id}` pairs, per
port wire ids with a local handle, an ambiguity error and
`dispatch.id_next` as the shared counter were the alternatives.

11.14.4.2 Handlers return finished reply lines because a payload cannot
carry blobs and a wake handler must answer the earlier request; wrapping a
payload in `line_dispatch` was rejected. `API/ts/dispatch.d.ts` still says
a handler returns "the reply without a header"; that stub text is the
maintainer's to change (4.6).

11.14.4.3 Python's rule that a notification's handler returning a reply
raises is relaxed for wakes: a reply that carries `r` is accepted without
`i`.

11.14.4.4 `dispatch.ts` looks the handler up before it checks the header,
where `python/dispatch.py` checks first; Python uses its own names
`dispatch.id_refused` and `dispatch.version_refused` beside the TypeScript
`dispatch.id_invalid`, because the rules differ and one name holds one
text. These are recorded twin differences.

11.14.4.5 As in Python, `line_dispatch` overwrites a wrong `r` silently,
writes no `v` or `k` on replies and checks neither the reply's name form
nor its `t`.

11.14.4.6 No `Dispatcher` class: the registry is module state and tests use
unique names; a class was the recorded rebuild option.

11.14.4.7 Setting `r` with `Object.assign` throws on a frozen header.

11.14.4.8 One held item per macrotask through a `MessageChannel`:
`setTimeout(0)` clamping, `queueMicrotask`, `scheduler.postTask` and time
slicing were rejected.

11.14.4.9 An arriving `error` line is a fault: delivering it as a reply in
the wake and dispatching it to an `error` handler were rejected.

11.14.4.10 `forward_marked`: forwarding a request would need id
translation, which is not built.

11.14.4.11 The explicit owner of `task_submit` and `line_notify` is the
earlier coordinator's decision, an addition that stands for the review and
awaits the maintainer's acceptance (4.5). It resolves
the double ownership of `kv.` lines and `mcp` on the AI thread, so the stub
comment of `OwnerTable` (`"kv."` to `"server"` on the AI thread) is not
the only route.

11.14.4.12 The loopback dispatch without a lookup: otherwise
`task_submit(line, "ai")` for a type the table sends to `server` would
come back through the loopback and be forwarded, a `forward_marked` throw.

11.14.4.13 `sink_attach` and `VerboseBatch` are additions that stand for
the review and await the maintainer's acceptance (4.5.5);
installing the sink in the constructor, sending on idle and sending per
line were rejected.

11.14.4.14 No bound before `sink_attach`: the planners' list of the windows
a blob goes through says the queue "before `settings_set` ... bounds
nothing, as now".

11.14.4.15 The window counts blob bytes only, the planners' reading, built
as option a) of the question on what a window counts (4.8.4.7): a blob of
`blob_max`, the largest database, must pass every window with its line.
The earlier measure of a held line, its JSON text plus its blob sizes, is
gone with `queue_max`.

11.14.4.16 `blob_max` and `line_max` are read on every call, so a debug
`settings_put` takes effect at once: an Unconfirmed reading, accepted.

11.14.4.17 A UI put of `blob_max` + 1 refused first with `queue.queue_over`,
not by `wire.ts` with `wire.blobs_over`: approved by the maintainer as
built (4.8).

11.14.4.18 Two `db_load` replies whose images, held at once, pass
`blob_max` fault with `queue.queue_over`: approved by the maintainer as
built (4.8).

11.14.4.19 A step scheduled before the first fault throws `queue.stopped`
again, so a fault may be reported twice.

11.14.4.20 The verbose batch is not sent on a fault.

11.14.4.21 The trace and the forwarding of `verbose.put` happen in debug
mode only, with no level, by the maintainer's words on verbose levels
(4.1); `verbose_forward` is gone. The runtime's deferred level design is
not built (4.2).

11.14.4.22 Wake headers use short names in every mode.

11.14.4.23 No platform port in `queue.ts`: the earlier coordinator's port
for the initialization promises was withdrawn when the maintainer gave the
rule on system initialization.

11.14.4.24 Replication runs as page tasks through the queue, with the
internal types `replicate.next` and `replicate.done`, which are not in
`API/ts/lines.d.ts`, and the explicit owner route, where the plan puts it
inside the substrate and lists explicit routes as a door: plan departures
that stand for the review and await the maintainer's acceptance (4.5).
Explicit route headers stay a door (4.2).

11.14.4.25 `API/ts/queue.d.ts` still cites a plan section ("the debug mode
of 4.2") in a comment; it is the maintainer's stub, left as found.

11.14.4.26 `API/ts/queue.d.ts` declares `task_submit(line)` and
`line_notify(line)` without the owner and nothing of `sink_attach` or
`VerboseBatch`; those additions await the maintainer (4.5).

11.14.4.27 `ThreadPort`'s `onmessageerror` throws.

11.14.4.28 The verbose batch's split measures a group's `verbose.put` as
the bytes of the empty `verbose.put`, plus each entry, plus the commas
between them; "below `line_max`" means "the line with its CR fits", its
writer's recorded measure.

11.14.5 Open, for the maintainer.

11.14.5.1 None recorded for these files.

11.14.6 Candidates.

11.14.6.1 `dispatch.line_dispatch` accepts the ids 0, -3 and 1.5 and a
string `v`, which `python/dispatch.py` refuses (`dispatch.id_refused`,
`dispatch.version_refused`). With task 1.4 (12.4); a new or changed
`dispatch.` string is a request to task 1.13.

11.14.6.2 `queue.step_empty`, a step with no task waiting, which the
earlier review listed among "defaults and unreachable branches". Check it
against the rule that no branch exists for a case that cannot happen.

11.14.6.3 The interface `Owed` in `ts/queue.ts` has one word, against the
two word rule (3).

11.14.6.4 Tests that register fresh types in the dispatcher's registry and
never unregister them, and that leave a scheduled step in the thread's live
state, so that a later test sees them (`ts/test_dispatch.ts`,
`ts/test_queue.ts`).

11.14.6.5 `test_run_twice` was recorded as proving nothing below verbose
level 2, since its history comparison needs the trace. With the levels
gone the trace exists only when `debug` is true: check that the test's
settings make the comparison compare a trace.

11.14.7 Seams.

11.14.7.1 Task 1.13 writes every `dispatch.` string and owns
`python/dispatch.py`; task 1.4 compares the twins. A fix of 11.14.6.1 that
needs a string sends the request to task 1.13 first.

11.14.7.2 Task 1.28, `ts/worker_ai.ts` and `ts/boot.ts`: the AI thread's
owner table and ports (`ui`, `server`, `console`, `http`, the provider
owner), `sink_attach` after `settings_set`, the replication handlers, and
the copy of WASM backed bytes before `task_submit`, which moves buffers.

11.14.7.3 Task 1.29, `ts/page.ts`: the UI's owner table, the DOM port
`dom`, `ui.input`, `dom.choice`.

11.14.7.4 Tasks 1.20, 1.24, 1.25, 1.26, 1.27, 1.28, 1.29 and 1.30 call
`handler_register`, `task_submit` or `line_notify`. A change of those
signatures is an interface change, proposed and not made (6); a change of
behaviour they rely on is received by the queue's callers first.

11.14.7.5 Task 1.23 owns `ts/wire.ts` and `ts/http.ts`, which implement
`queue.Port`.

11.14.7.6 Task 1.21 owns `verbose.sink_set` and `settings.settings_get`,
which `sink_attach` takes.

11.14.7.7 Task 1.10 owns `python/test_posix.py`, whose
`_SYNCHRONIZATION_MODULES` holds the five modules of 11.14.3.12.

11.14.7.8 Task 1.19's rungs reach the UI's live queue through
`test_ui_tasks.task_submit`, called only inside handlers.

11.15 Task 1.23, the TypeScript wire and http lanes.

11.15.1 Owns: `ts/wire.ts`, `ts/test_wire.ts`, `ts/http.ts`,
`ts/test_http.ts`. The `i18n` prefixes `wire.` and `http.` are this
task's.

11.15.2 Reads: `API/ts/wire.d.ts`, `API/ts/http.d.ts`, `API/ts/lines.d.ts`
(`Hello`, `ConsoleBytes`, `ConsoleRead`, `ConsoleReadReply`, `ConsoleExit`,
`HttpRequest`, `HttpResponse`, the rows of `console.*` and `http.request`);
`API/ts/queue.d.ts` (`Port`); `ts/jslb.ts` (`LineDecoder`, `idle()`,
`BlobSink`); `ts/queue.ts`; `ts/worker_ai.ts`, which builds both ports,
answers `hello` and relays the console; `ts/console_view.ts`, which sends
ttyd's first message on tty 0; `ts/substrate.ts` (`CacheFiles.cache_read`);
`ts/tools_browser.ts` (`console_run`); `ts/agent.ts` and
`ts/provider.ts`, which submit `http.request`; `python/bootstrap.py`'s
`hello`; the rungs of `python/test_browser.py` that probe the wire port.

11.15.3 Expected.

11.15.3.1 The lanes. `wire` joins the AI worker and the server, bytes over
tty 1; `console` joins the AI worker and ttyd's dash, ttyd's own protocol
over tty 0; `http` joins the agent and the provider over HTTPS, one request
per line. Every message on every lane is one JSLB object but the console
tty's own protocol. Both ports implement `queue.Port`.

11.15.3.2 Transport. ttyd frames each message as `'0'` plus bytes each way,
and sends `'1'` the title and `'2'` the preferences first. `WirePort`
strips and adds the `'0'` and keeps the title and the preferences. A
message of another kind throws `wire.kind_unknown`, an empty one
`wire.message_empty`, a text message where binary is due
`wire.message_text`.

11.15.3.3 The server puts its pty in raw mode with `tty.setraw` before it
writes anything, and the client sends nothing until `hello` arrives: a
`line_post` before `hello` throws `wire.post_early`.

11.15.3.4 ttyd's 5 s ping is answered by the browser's network stack.

11.15.3.5 Addresses are made by `new URL(path, base_url)`, `base_url` the
page's own address; `http:` becomes `ws:` and `https:` `wss:`, and any
other scheme throws `wire.scheme_unknown`.

11.15.3.6 Flow control, the plan's decision. ttyd stops reading the pty
after each 64 KiB read until it is written to the socket, and puts client
input on libuv's unbounded write queue. So ttyd runs with `--srv-buf-size
1048576`, patched into the 1.7.7 release; `chunk_bytes` is 1 MiB;
`wire.ts` waits for `bufferedAmount` under one chunk before it sends the
next; the server streams big blobs to a cache file so libuv's queue stays
short.

11.15.3.7 Output is framed as `'0'` frames of at most `chunk_bytes`,
counting the `'0'` byte, so a frame's payload is `chunk_bytes` - 1; a chunk
size below 2 throws `wire.chunk_invalid`. The JSON piece and each blob are
framed separately; an empty piece sends nothing; each send passes a fresh
`ArrayBuffer`.

11.15.3.8 `wire.FrameQueue` holds the frames to send. Its `line_add`
refuses before anything is queued: a line over `line_max` with
`wire.line_over`; a message whose blobs sum over `blob_max` with
`wire.blobs_over`; a line whose blob bytes, with those held, would pass
`blob_max` with `wire.queue_over`. The window counts blob bytes only and is
released frame by frame.

11.15.3.9 The drain polls `bufferedAmount` with `setTimeout` every
`poll_ms` (0) under the timer `drain_seconds`; its expiry throws
`wire.wait_expired` naming `wire.what_drain`.

11.15.3.10 A blob whose `d` is a cache handle is sent in ranges of at most
`chunk_bytes` - 1 read through the synchronous reader set by
`WirePort.cache_attach`: D3, `blob_make` takes `size` for a handle and the
sender checks the bytes it reads against `s` (4.4). A short range throws
`wire.handle_differs`; a handle with no reader attached,
`wire.handle_unsent`.

11.15.3.11 A credit line for uploads, or a ttyd patch bounding its write
queue, is added only if the measurement of ttyd's resident size during a
128 MiB upload demands it (4.2).

11.15.3.12 Connection lifecycle, open. The page loads the first four
scripts, then `page.ts` creates the AI worker, which builds
`WirePort(base_url, sink, settings_get)`; the port fetches `/token`, opens
`/ws` with the subprotocol `tty`, sends ttyd's first JSON message, skips
the title and the preferences and waits for `hello`. A token request that
fails names its status (`wire.token_status`) or its missing token
(`wire.token_invalid`); a second open throws `wire.open_twice`.

11.15.3.13 Each wait has a timer: `token_seconds`, `open_seconds`,
`hello_seconds` and `drain_seconds`, 120 s each. An expiry throws
`wire.wait_expired` naming what it waited for (`wire.what_token`,
`wire.what_open`, `wire.what_hello`, `wire.what_drain`) and does not close
the socket. A timer started twice throws `wire.timer_twice`.

11.15.3.14 `hello` is decoded under the hello phase constants of D24 (wire
limits are built after `settings_set`; the hello is decoded with a line of
at most 10 MiB and no blobs, 4.4): `hello_line_max` 10485760,
`hello_blob_max` 0, `hello_overflow_bytes` 0. The first decoded line goes
to the receiver set by `hello_receive(fn)`.

11.15.3.15 An `error` line before `hello` throws `wire.error_first` with
the server's message and stack, and the port shuts, so its close adds no
second fault; another line before `hello` throws `wire.hello_missing`.
Bytes after `hello` and before its reply throw `wire.hello_trailing`. A
second `hello` throws `wire.hello_twice`: D9, a second `hello` after
`system.restart` is a fault ending in Reload (4.4).

11.15.3.16 After `hello` the line decoder, `new LineDecoder(line_max,
blob_max, overflow_bytes, sink)`, and the `FrameQueue` are built at first
use from the injected settings reader.

11.15.3.17 `hello` is the server's request with `i` 1: `bootstrap`,
`sha256`, `pid`, `root`, `settings`, `seq` per server database,
`provider_key`, and `provider_info` when `provider.scripted` is false. The
worker posts `settings.set` to the UI, answers with an empty reply, then
posts `boot.hello`.

11.15.3.18 The decoder is driven as `ts/jslb.ts` requires: the port
delivers the lines a feed returns, then feeds an empty array, which throws
a held fault; any thrown value is a fault. A decoder fault is raised once
and the port closes; there is no resynchronization on a byte stream.

11.15.3.19 Any throw while the port takes a message closes the socket with
1000 and is thrown again; incoming messages are then dropped, and the close
function is not called.

11.15.3.20 Close. `close_receive(fn(code, had_error))` is called once when
the socket ends for any reason but `wire_close`. A close with no `error`
line is the fault "connection closed with code N and no error line"
(`wire.close_silent`), which the port throws itself; a close in the middle
of a message, the decoder not idle, is `wire.close_partial`.

11.15.3.21 Every close this side makes uses 1000. `wire_close()` closes
with 1000; before the socket exists it throws. The worker ends a session by
closing with 1000; ttyd sends SIGHUP and the server exits. There is no
`quit` and no `cancel`; a runaway is ended by closing.

11.15.3.22 Linux ttyd closes with no close frame, code 1006, when the
program exits, and may end a connection without delivering the program's
last output; the page treats such a close as the fault of 11.15.3.20, and
the wire test reports a lone loss with the ttyd version, never retrying it.

11.15.3.23 A close without an `error` line, a desync and a timer expiring
are faults like any other and end in Reload; nothing in flight is retried.

11.15.3.24 Header names are full in debug mode and short otherwise, the
form chosen by one `names_full()` in the worker: D27 (4.4).

11.15.3.25 The console port. `ConsolePort(base_url, settings_get)` is the
port to tty 0, `/ws?arg=console`, with no JSLB on the socket: ttyd's
protocol bytes travel wrapped as `console.output` and `console.input` lines
on the ui-ai lane, so the AI worker is the only owner of sockets.

11.15.3.26 `console.open` is a request posted to the port: it fetches
`/token`, opens the socket and replies `{token}` once it is open: D23, the
`console.open` reply carries `token`, fetched from `/token` (4.4). The
console view puts that token in ttyd's first message; the console port
sends no first message of its own.

11.15.3.27 Each message ttyd sends becomes one `console.output` line with
the bytes as blob 1. Each `console.input` line posted sends its one blob,
held in memory, as one message (`wire.input_blob`, `wire.input_bytes`).
Another type throws `wire.console_type`.

11.15.3.28 `console.read {until, timeout_seconds}` needs an id
(`wire.id_missing`), a text `until` (`wire.read_until`) and a
`timeout_seconds` from 0 (`wire.read_seconds`); a second read while one
waits throws `wire.read_twice`. The port answers `ConsoleReadReply {text,
timed_out}`: the output received after the read was posted, up to and
including the message that completes `until`, or, when the request's
`timeout_seconds` expires, a timer, the text so far with `timed_out` true.

11.15.3.29 Each read decodes with its own strict UTF-8 decoder; invalid
bytes throw `wire.output_invalid` with `cause`; output that arrives with no
read waiting is ignored.

11.15.3.30 `console.close` closes the socket. When ttyd closes it,
`close_take` stops the open timer, clears the socket and answers a waiting
read with `timed_out` true and the text so far; `close_receive(fn(code))`
is called once and the worker pushes `console.exit`. The port can open
again: open, close, exit, open. A socket that closes before it opens throws
`wire.open_closed` and the close receiver is not called.

11.15.3.31 The console is reached by the AI only through `console_run`
after the permission flow: it posts the text and a newline as
`console.input`, submits `console.read` and sleeps. The console role runs
only in debug mode.

11.15.3.32 The public names beyond the stub, accepted additions (4.5):
`WirePort.hello_receive`, `message_take`, `close_take` and `cache_attach`;
`ConsolePort.message_take` and `close_take`; `wire.FrameQueue`; and
`wire.ConsoleReader` with `message_take`, `read_start` and `read_expire`.

11.15.3.33 The HTTP port. `HttpPort(timeout_seconds)` answers each
`http.request {method, url, headers, json?, body?}` with one `fetch`, under
an `AbortController` and a `setTimeout` of `timeout_seconds`; any thread
may own one; the provider's port is built from `provider.timeout_seconds`.

11.15.3.34 `line_post` checks the line synchronously and throws on a type
other than `http.request` (`http.type_invalid`), a line with no id
(`http.id_missing`), a line with blobs (`http.blobs_refused`), a missing or
bad field (`http.field_invalid`) and a request before a receiver is set
(`http.receiver_missing`). `line_receive` twice throws
`http.receiver_twice`. The timeout must be finite, above 0 and at most
2^31 - 1 ms (`http.timeout_invalid`).

11.15.3.35 The reply is a line of `t` `http.request`, the request's own
type, with `r` equal to its `i` (3), carrying `status`, `headers`, and
`json` when the media type is `application/json`, else `text`.

11.15.3.36 An `error` line answers a non 2xx status, with the body's text
in the message (`http.status_failed`), a rejected fetch
(`http.fetch_failed`), the timer expiring (`http.timeout_expired`) and a
body that is not JSON under a JSON media type (`http.json_invalid`). After
the timeout no second line is sent.

11.15.3.37 `http.HttpExchange` (`arguments_make`, `answer_reply`,
`failure_reply`, `timeout_reply`), `FetchArguments` and `HttpAnswer` are
accepted additions (4.5), so the translation is tested synchronously.

11.15.3.38 Tests: synchronous, none starting a `fetch` or a socket; every
expected error compared with its message text (3).

11.15.3.39 Owed to the browser rungs (12.5): the hello relay; a round trip
of a blob of `blob_max` equal by SHA-256; a message whose blobs sum to one
byte more refused by `wire.ts` at its post; a close without an `error` line
reported as such; the token fetch and the open on both ports; the token
accepted by ttyd; open, close, exit, open; `wire.open_closed`; every timer;
the drain poll; a fault closing the port; cache sends through the
substrate's reader; the console echo, `^C`, `console_run` and its timeout;
and for `HttpPort` against a local stub server: the exact POST body and
headers, text and JSON responses, the statuses 400, 401 and 500, a closed
port, a stub that never answers or stalls the body, no second line after
the timeout, several requests out of order, a GET with a body, the CORS
preflight, the port inside the worker, a throwing receiver, and the real
HTTP timeout inside a turn.

11.15.4 Decided, not a finding.

11.15.4.1 The constructors `WirePort(base_url, sink, settings_get)` and
`ConsolePort(base_url, settings_get)`, where the stub has
`WirePort(base_url, chunk_bytes, decoder)` and `ConsolePort(base_url)`,
and the stub's `console_open` and `console_close` replaced by the request
lines `console.open` and `console.close`: recorded API departures (4.5);
keeping `console_open` with an adapter was the alternative.

11.15.4.2 The four waits of 120 s are defaults: the maintainer asked for
"sane timer defaults" (4.1), and the planners kept the 120 s lengths
already written. Each comment reads "a default kept from the earlier
code". An earlier coordinator's order to replace them was corrected. The
rungs that wait out one of them are `normal-test`.

11.15.4.3 A wait that expires throws and does not close the socket.

11.15.4.4 The drain poll uses `setTimeout` with 0 ms; a fixed interval and
`WebSocketStream` were the alternatives.

11.15.4.5 `line_post` before `hello` throws; a queue of early lines was the
alternative.

11.15.4.6 `wire.error_first` is the fix of the maintainer's request that an
`error` line sent before `hello` show the server's message, not
`wire.receiver_missing`.

11.15.4.7 A throw while taking a message closes and rethrows, and the
close function is not called afterwards; this narrows the stub's "any
reason other than `wire_close`".

11.15.4.8 The port throws the silent close fault itself, and every close
it makes uses 1000.

11.15.4.9 The token request uses `fetch` with no catch, so a rejection is
unhandled and reaches `error_overlay`; `XMLHttpRequest` was the
alternative.

11.15.4.10 `wire_close` before the socket exists throws.

11.15.4.11 The console read answers with the output received after the
read was posted, up to the message that completes `until`, as the plan's
"once the prompt returns" says; `API/ts/lines.d.ts` says "since the last
read", stub text that is the maintainer's to change (4.6).

11.15.4.12 A strict decoder per read, by the earlier job's prescription; a
UTF-8 character split across two reads faults the second.

11.15.4.13 `hello_line_max` is 10485760, the constant of D24 (the hello
decoded with a line of at most 10 MiB and no blobs), built as option
a) of the question on the hello's line bound (4.8.4.13); it came from the
maintainer's earlier 10 MiB, now superseded. `hello_blob_max` 0 lets a
blob header of size 0 pass (`wire.hello_blobs` was the alternative).
`hello_message_max` is gone with `message_max`.

11.15.4.14 The settings parts are read once, at first use after `hello`,
so a debug `settings_put` of them takes effect at the next `hello`;
`WirePort.settings_take()` and building from `hello.settings` were the
alternatives.

11.15.4.15 Bytes after `hello` and before its reply throw, relying on
`bootstrap.py` sending nothing between; decoding with the hello limits
until the reply was the alternative.

11.15.4.16 `wire.close_partial` has its own text.

11.15.4.17 A console socket closing before it opens throws
`wire.open_closed` without calling the close receiver.

11.15.4.18 `debug` is read through a cast; `wire.read_id` was merged into
`wire.id_missing`.

11.15.4.19 `chunk_bytes` and `srv_buf_size` stay 1 MiB and are not set to
`blob_max`: they are the pieces a blob is cut into, each allocated whole.
Approved by the maintainer (4.8).

11.15.4.20 A UI put of `blob_max` + 1 is refused first by the AI worker's
task queue, so `wire.blobs_over` refuses only on the page's own port; a
`kv.get` reply of `blob_max` + 1 is refused by the page's decoder, its
value written on the server behind the page's back. Both approved (4.8).

11.15.4.21 The drain rungs stall ttyd with `SIGSTOP`; wait lengths read
from settings were excluded by the timer rule. Approved (4.8).

11.15.4.22 The AI worker owns the console socket and the role rides
`--url-arg` as `console`: Unconfirmed readings of the plan, accepted.

11.15.4.23 `API/ts/lines.d.ts` still shows the `console.open` reply as
`Empty` and no `ConsoleOpenReply {token}`: the edit for D23, the
`console.open` reply carrying `token`, was not applied to the maintainer's
stub (4.6).

11.15.4.24 The console port sends no first message; the console view does.

11.15.4.25 The reply on the http lane has `t` `http.request`, where
`API/ts/http.d.ts` says `http.response`; the rule of section 3 decides, and
the stub text is the maintainer's to change (4.6).

11.15.4.26 `http.ts` builds its lines with `jslb` only;
`dispatch.reply_make` and `error_make` were rejected.

11.15.4.27 Only the media type `application/json` is JSON
(`application/problem+json` is text); a non 2xx message includes the body
text; a body that is not JSON under a JSON type is an `error` line.

11.15.4.28 An `error` line's stack is that of an `Error` made in `http.ts`;
the fetch failure's own stack is only its `cause`. The fetch defaults are
untouched.

11.15.4.29 Exporting nothing and four free functions were rejected for
`HttpExchange`; the old name `json_media_is` is `media_json`.

11.15.4.30 The provider address and model in `ts/test_http.ts`,
`https://api.x.ai/v1/chat/completions` and `grok-4`, are test input: the
placeholders the shipped settings held, as the plan then said, before the
provider file took the three provider keys out. No value is invented, and
`provider.json` stays empty.

11.15.5 Open, for the maintainer.

11.15.5.1 None recorded for these files.

11.15.6 Candidates.

11.15.6.1 `ConsolePort.names_full()` is a second reader of the name form,
against D27, one `names_full()` in the worker (4.4).

11.15.6.2 tty 1's first message to ttyd carries `columns: 80, rows: 24`,
carried from the old `python/bootstrap.html`: a reuse by availability,
where the plan alone chooses what of the old code is reused. The plan
lists `console_columns` and `console_rows` among the settings decided
against, as xterm.js sends its own size.

11.15.6.3 `http.ts`'s `.catch` after `.then` reports an error in building
the reply as `http.fetch_failed` and can leave a rejection unhandled; its
writer also recorded that a receiver that throws reaches the unhandled
rejection path.

11.15.6.4 `close_take` skipping an unset receiver, `wire.read_none`,
`wire.frames_none` and `http.stack_missing`, the last recorded by its
writer as unreachable in V8 and untested: listed by the earlier review
among "defaults and unreachable branches".

11.15.6.5 `ts/test_http.ts`: 13 tests recorded as asserting only a base
class, where a test that expects an error compares the message text (3).

11.15.6.6 The comment of `wire.constants.hello_line_max` was found calling
it "the maintainer's size", though the coordinator set it; it is the
constant of D24, the hello's 10 MiB line bound (11.15.4.13), and its one
line comment says who chose it.

11.15.6.7 A cache file longer than the blob's `s` is not detected, a gap
its writer recorded.

11.15.6.8 `API/ts/lines.d.ts` gives `HttpResponse` a blob 1 "when the
request asked for `binary`", which `HttpRequest` cannot ask for, and the
lane table gives it no blob; the code builds no such path, recorded as not
built, with its design: a `binary` field, an `arrayBuffer()` read and a
blob. The census (12.1) proposes the stub edit.

11.15.7 Seams.

11.15.7.1 Task 1.28, `ts/worker_ai.ts`: it builds both ports with
`settings.settings_get`, registers `close_receive`, answers `hello`,
calls `cache_attach` before any handle blob, owns `console.` lines and the
`console.open` handler, and holds the one `names_full()`. A fix of
11.15.6.1 changes the `ConsolePort` constructor, an interface change
proposed and not made (6); the worker receives such a change first.

11.15.7.2 Task 1.30, `ts/console_view.ts`: ttyd's first message on tty 0
with the token, and the console reopening.

11.15.7.3 Task 1.27, `ts/tools_browser.ts`: `console_run` and its
`console.read`. Tasks 1.25 and 1.26: the `http.request` lines and the
provider's `HttpPort`.

11.15.7.4 Task 1.24, `ts/substrate.ts`: `cache_read(handle, offset,
length)` returns exactly `length` bytes while the file has them, and a
`jslb.BlobSink` that needs no SQLite exists before `hello`.

11.15.7.5 Task 1.12, `ts/jslb.ts`: the decoder's arguments, `idle()` and
`blob_make`'s `size`.

11.15.7.6 Task 1.16, `python/bootstrap.py`: raw mode before any write,
`hello` as the first request, nothing sent between `hello` and its reply.

11.15.7.7 Task 1.19, `python/test_browser.py`: `probe.wire_pending` reads
the `WirePort`'s private `socket` and `poll_id`, and `_WIRE_SECONDS` and
`_DRAIN_SECONDS` copy the 120 s of `wire.ts`. A rename of those fields or
a change of those values is sent to task 1.19 before it lands.

11.15.7.8 Task 1.3, the line contract (12.3): the rows and comments of
`console.open`, `console.read` and `http.request` in `API/ts/lines.d.ts`.

11.16 Task 1.24, the TypeScript substrate.

11.16.1 Owns: `ts/substrate.ts` and `ts/test_substrate.ts`. Task 1.8 reads
`ts/test_substrate.ts` as a read only reviewer (12.6) and sends its requests
here.

11.16.2 Reads: `API/ts/substrate.d.ts`, `API/ts/lines.d.ts`,
`API/sql/substrate.sql`, `python/substrate.py` and
`API/python/substrate.pyi` (the twin), `ts/boot.ts` and `ts/worker_ai.ts`
(the pool, the cache files, the replication queue, the start),
`ts/tools_browser.ts` (the database tools, the fetch of a value not held,
`render`'s eviction), `ts/script.ts` (`engine.store`), `ts/agent.ts`
(`turn_append`), `ts/utility.ts`, `ts/jslb.ts` (`BlobSink`, `blob_make`),
`ts/queue.ts`, `ts/dispatch.ts`, `python/test_browser.py` (the rungs that
call the kill probes).

11.16.3 Expected.

11.16.3.1 Purpose. The single door to SQLite in the AI worker: the KV
accessor on Key-Value-Refs, documents and heads, turns and their
compaction, SQL, snapshots and restores, the database administration
operations, and the emitting side of replication. It has the API of
`python/substrate.py` plus that emitting side. Every database and the
cache are on the AI thread; a running task holds every database, a
sleeping one none.

11.16.3.2 Module form. One frozen `namespace substrate` exporting
`ref_split`, `doc_encode`, `doc_decode`, `CacheFiles`, `Store` and the
interfaces; one frozen `constants` object for the module's constants. No
`await`, `.then(`, `new Promise`, `Atomics`, `SharedArrayBuffer`, `async`
or timer: the synchronization audit exempts only `queue.ts`, `wire.ts`,
`http.ts`, `media.ts` and `boot.ts`.

11.16.3.3 Engine. sqlite3.wasm, pinned by version and SHA-256, on the OPFS
SAH pool VFS; no version floor and no version check. Initialization,
`sqlite3InitModule`, `installOpfsSAHPoolVfs` and its capacity, the OPFS
directory, its file handles and `createSyncAccessHandle` for the cache
files, uses promises in `ts/boot.ts` alone, by the maintainer's rule that
system initialization need not abide by the rules of use. `boot.ts` hands
the objects to the store, which is synchronous from then on. No platform
port in `queue.ts` turns those promises into lines.

11.16.3.4 Stub. `API/ts/substrate.d.ts` holds `KvValue`, `TurnRow`,
`RefParts`, `ref_split`, `doc_encode`, `doc_decode` and `Store` with
`db_open`, `db_close`, `db_list`, `db_create`, `db_drop`, `kv_get`,
`kv_put`, `kv_delete`, `kv_list`, `kv_check`, `doc_get`, `doc_put`,
`doc_head`, `turn_append`, `turn_list`, `turn_compact`, `sql_run`,
`db_snapshot`, `db_restore`, `kv_held`, `cache_fill`, `cache_evict`,
`operation_apply`, `transaction_run`, `forward_set`, `sink` and
`handlers_register`. The code's departures and additions are in 11.16.4.

11.16.3.5 Tables. The substrate's `_meta`, `_kv`, `_head` and `_turn` of
`API/sql/substrate.sql` are created on first use in every database the
store opens. `_meta` holds `seq`, incremented in the same transaction as
every modifying operation, and `schema`. `_kv.sha256` names the overflow
file, detects an unchanged write and lets replication skip bytes the other
side has; `data` is NULL when the value is in the cache. No type column,
no per row `seq`, no tombstone table.

11.16.3.6 Databases. One connection per database. A database name is a C
identifier and its file `<name>.sqlite`. Only `foreign_keys = ON` is set,
as the SAH pool has no WAL. A new database starts at `seq` 0 and
`db_create` leaves it 0 (D1, a new database at `seq` 0, `db.create`
carrying `since` 0 and `db.drop` its database's `seq`). Nothing limits the
number of databases.

11.16.3.7 No protections. No table or database refuses a write: no
authorizer, no refusal of `_` tables or of `_settings`, none in
`operation_apply`, `kv_put`, `kv_delete` or `turn_append`, and no
enforcement of the fixed schemas of `_files`, `_preferences` or
`metaverse`. The maintainer decided that SQL rules are not a security
boundary and that nothing refuses the AI API access to the databases.
`_settings` is written by the server from its file and never by the
browser, which nothing enforces.

11.16.3.8 Refs and documents. `ref_split` splits `/$db/$key` and `$key`;
a bad ref throws. A Document-Ref's key is `$id/$version`, the version an
integer literal and the last segment. `doc_put(db, id, body)` writes
version head plus one and moves `_head` in the same transaction;
`doc_head` reads `_head`; `doc_get` is `kv_get` with a JSON decode. A
written version never changes. `doc_encode` moves every reference string
into headers 1 on, sharing equal strings, and leaves `{"$ref": n}`;
`doc_decode` puts them back; the round trip is identical. A reference
string's key part holds no white space (D18), the excluded class being
exactly the code points of Python's `str.isspace`. Canonical JSON applies
`jslb`'s key rules at every nesting level, as the Python twin does.

11.16.3.9 KV. `kv_put(ref, data)` takes bytes; a string is a cache handle,
never text; callers encode text with `TextEncoder` (`utility.utf8_encode`)
and decode with `TextDecoder`. A value over `overflow_bytes` lives in a
cache file with `data` NULL; a value of exactly `overflow_bytes` stays in
the row. File first, then the row; a crash between leaves a file that
`kv_check` frees. The streaming decoder's file becomes the value's file
with no second copy. `kv_held(ref, db?)` says whether this side holds a
value's bytes, in its row or a file; `cache_fill(ref, data, db?)` puts the
cache file back from bytes or a handle whose digest is the row's;
`cache_evict(db, keep, budget)` frees a database's cache files by key, but
those the kept refs and other databases name, until they fit the budget,
and returns the count freed. A script reading a value not held throws
`substrate.cache_unknown`, naming the digest; the `kv_get` and `doc_get`
tools fetch it (11.19).

11.16.3.10 The cache files. `CacheFiles(slots)` is a fixed set of OPFS
files held open with sync access handles; each file's first 64 bytes hold
the stored SHA-256 in hex, or zeros when the file is free; a sink handle
`sink/<n>` lives in memory only; `substrate.cache_full` is thrown when no
file is free. It is the `jslb.BlobSink` of the wire's decoder: it needs no
SQLite, exists before `hello`, copies each appended view and hashes on the
way with an incremental SHA-256. `cache_read(handle, offset, length)`
reads synchronously, returning exactly `length` bytes while the file has
them; `slot_add` and `slots_free` serve the worker. A cached value's blob
header is built "`jslb.blob_make(sha256, undefined, {}, row size)`" (D3,
`blob_make` taking `size` for a cache handle, the sender checking the
bytes it reads against `s`).

11.16.3.11 Turns. Turns are `_turn` rows in the database of the scene,
keyed by the scene's Document-Ref, each one provider message.
`turn_compact(scene, through, summary)` replaces turns 1 to `through` with
one summary row, role `system`, at `n` 1. Compaction is automatic: when
`turn_append` appends a turn of role `user` to a scene that already holds
`compact_turns` turns or more, it first compacts that scene's turns 1 to
its last in the same transaction, forwarded as its own `turn.compact`
before the `turn.append`. The summary is the one `i18n` text
`substrate.turns_compacted`, naming the turns compacted and the count that
reached the threshold. The server applies both lines and never compacts by
itself. The AI may still compact by hand through `engine.store`.

11.16.3.12 SQL and transactions. `sql_run(db, statements)` takes
`{sql, params}` statements; DDL is allowed. `transaction_run(fn)` is the
only way to touch a database and cannot span a return, so a handler has
committed before it sleeps.

11.16.3.13 Forwarding. Every modifying operation committed in the
browser, `kv_put`, `kv_delete`, `doc_put`, `turn_append`, `turn_compact`,
`db_create`, `db_drop` and every modifying `sql_run`, is handed to the
function of `forward_set` as the same wire line, after the commit, in
order, with `since` the browser's `seq` before the operation. The lines and
their payloads: `kv.put {since}` with `k` the ref and blob 1, reply
`{sha256, seq}`; `kv.delete {since}`, reply `{seq}`; `doc.put {db, id,
body, since}`, reply `{ref, seq}`; `db.create {db}` and `db.drop {db}`
with `since`, reply Empty; `turn.append {scene, role, content, since}`,
reply `{n, seq}`; `turn.compact {scene, through, summary, since}`, reply
`{seq}`; `sql.run {db, statements, since}`, reply `{results, seq}`. The
server refuses a line whose `since` is not its own `seq`; a refused push
or a reply whose `seq` is not the browser's is a desync, a fault that ends
in Reload, and the reload replaces the file.

11.16.3.14 Acknowledgement. `forward_done(line, reply)` is called once per
forwarded line by the worker's `replicate.done` handler. It checks that
the reply's `seq` is `since + 1`, skipped for `db.create` and `db.drop`,
and releases what the line held. One line is in flight per database; the
queue that keeps that order is `ts/worker_ai.ts`'s (11.20).

11.16.3.15 Snapshot and restore. `db.snapshot` replies with `sha256` and
`seq` and the database file as one blob of at most `blob_max`; the
receiver checks the blob's SHA-256 against `sha256` before it restores.
`db_snapshot(db)` exports the browser's copy for the UI's `db.snapshot`
through `sqlite3_js_db_export`. `db_restore` and `db_load` import the
image as `<file>-restore`, check it read only, then import it over the
live copy; a leftover `-restore` file throws `substrate.restore_left`.

11.16.3.16 Start. `start_open(server_seq)` takes `hello`'s `seq` per
database, deletes held files the server lacks, unloads held files whose
`seq` differs and returns their names, which the worker then replaces with
`db.snapshot` and `db_restore`, and marks the names the browser lacks
unloaded. Only the databases the browser holds are replaced; the others
stay unloaded until `db_load`.

11.16.3.17 Database administration. Measurement by heuristics, never by a
quota call (`navigator.storage.estimate()` is asynchronous): a database's
size is `page_count` times `page_size` plus the `size` of its `_kv` rows
with `data` NULL; its reclaimable space is `freelist_count` times
`page_size`; the total sums the databases open in the AI worker.
`db_stats(soft_bytes)` returns `{databases: [{name, bytes, free_bytes,
cache_bytes, seq}], total_bytes, soft_bytes, over}`, `over` meaning
`total_bytes > soft_bytes`; a soft limit refuses nothing.
`db_compact(db)` runs `VACUUM` on the browser's copy and returns
`{before, after}`; content and `seq` are unchanged and nothing is
forwarded. `db_unload(db)` closes the browser's copy and deletes its OPFS
file and the cache files only it references; the server's copy stays,
nothing is forwarded, and a later operation on that database throws
`substrate.db_unloaded` naming `db_load`. `db_load(db, data)` opens the
server's copy as the start replacement does and returns its `seq`.

11.16.3.18 Handlers. `handlers_register` registers on the AI thread the
handlers of the UI's `kv.*`, `doc.*`, `db.*`, `turn.*` and `sql.*` lines,
which travel the ui-ai lane without `since`: `kv.get` (reply
`{size, sha256}` and blob 1), `kv.put`, `kv.delete`, `kv.list {db,
prefix}` (reply `{keys}`), `doc.put`, `doc.head {db, id}` (reply `{ref}`),
`db.create`, `db.drop`, `db.snapshot`, `turn.append`, `turn.compact` and
`sql.run`. Each returns a finished reply built with `dispatch.reply_make`.

11.16.3.19 Settings read. `overflow_bytes` and `turn_compact_turns` reach
the constructor from the worker; `db_soft_bytes` reaches `db_stats` and
`files_browser_bytes` reaches `cache_evict` from the tools.

11.16.3.20 Strings and errors. The prefix `substrate.` is shared with
`python/substrate.py`; task 1.14 writes it, and a new, reworded or removed
name goes to it as a request (6, 8). A fault is a thrown `Error` whose
message is the `i18n` text of a literal name; a wrapped error keeps
`cause`; no catch is empty.

11.16.3.21 Tests. `ts/test_substrate.ts` holds `unittest.ts` cases, runs
in the browser rung "stage 0: typescript suites" and carries its label;
it imports only its module and the harness and reads the globals
`test_sqlite3` and `test_pool` (at least 16 free slots) that the worker
sets at `hello`. Every expected error is compared with its `i18n` text, no
test leaves state another sees, and no test enshrines the code's number
where a recorded number exists.

11.16.3.22 Proofs of stage 6 owed here, in `ts/test_substrate.ts`:

11.16.3.22.1 the stage 3 suite of `python/test_substrate.py` ported class
by class, with identical counts but for what has no meaning on the SAH
pool: the tables created on first use in a new database, KV on both ref
forms, documents, heads, the document round trip, `seq` across reopen,
overflow at exactly `overflow_bytes`, snapshot and restore, a kill between
file and row, `kv_check`, `operation_apply` of a sequence the test builds,
`turn_compact`; `test_wal_left` is not ported;

11.16.3.22.2 the test only kill probes `kill_pool`, `kill_put`,
`kill_hold` and `kill_check`, which the rung between file and row runs in
real workers.

11.16.3.23 The rest of stage 6 is rungs of `python/test_browser.py` (task
1.19, checked by task 1.5): a second load finding the rows, overflow files
in OPFS, the string to string table, created and filled through `sql_run`,
replicated by modifications submitted as tasks from the UI and from the AI
and compared with the server's copy (the plan calls it "the first unit
test"), the start replacement of a differing file, the desync reload (the
plan: "unit tested in stage 6, early"), an operation sequence built by
`test_wire.replay_build` replayed into the page from the UI's queue with
the browser's copy compared with the server's, and `rung_blob_max`. The
exit: identical counts to the Python suite, and the reload test passes.

11.16.4 Decided, not a finding.

11.16.4.1 The constructor takes six arguments, `(sqlite3, pool, cache,
root, overflow_bytes, compact_turns)`, at every call site, where the stub
has four: an API departure an earlier job recorded, the pool and the cache
being handed over by `boot.ts`; `compact_turns` comes after
`overflow_bytes` by the maintainer's compaction decision.

11.16.4.2 `forward_set(fn, full)` takes the line name form, where the stub
has one argument: an API departure for D27, the one `names_full()` in the
worker that chooses the name form.

11.16.4.3 `handlers_register(register)` takes the dispatcher's register
function, where the stub takes none: an API departure.

11.16.4.4 Public names beyond the stub, API additions an earlier job
recorded and D11 (the API additions and departures stay) keeps (4.5):
`seq_get(db)`, `forward_done(line, reply)`, `db_stats(soft_bytes)`,
`db_compact(db)`, `db_unload(db)`, `db_load(db, data)`,
`start_open(server_seq)`, and the class `CacheFiles(slots)` with
`slot_add`, `slots_free`, the sink methods and `cache_read`.

11.16.4.5 The test only exports of `ts/test_substrate.ts`, the kill probes
among them: D25, test only exports stay.

11.16.4.6 The cache as the fixed slot files of 11.16.3.10, not a file per
value named by its digest: the writer rejected a file per value, whose
creation is asynchronous, a SQLite cache database and SAH pool files.

11.16.4.7 The number of cache slots (256) and the pool's capacity are
fixed at initialization, with no growth at run time: a recorded class B
item, because promises are confined to initialization; its options were a
platform port for growth or larger constants. An earlier review held it
against "don't worry about too many DBs"; the review leaves it.

11.16.4.8 `sink_close` of a short blob frees its file and returns the
digest of the bytes received without throwing; keeping it until
`kv_check`, or throwing, was rejected.

11.16.4.9 `kv_check` never removes a live sink file, departing from
Python's `test_file_moved`.

11.16.4.10 A forwarded line with a handle blob holds its file until
`forward_done`. Forwarded values are copies; `db.create` and `db.drop`
lines go at once and the others after the outermost commit; a rollback
discards the pending lines. With no forward function set, a modifying
operation throws `substrate.forward_unset` inside its transaction.

11.16.4.11 `forward_done` checks `since + 1`, keyed on the line object:
an earlier job's coordinator accepted it in place of an earlier check that
the reply's `seq` equals `seq_get(db)`, which fails whenever local writes
run ahead of the line in flight. That coordinator's platform port for the
asynchronous setup, decided beside it, was withdrawn by the maintainer's
initialization rule (11.16.3.3).

11.16.4.12 Replication runs as page tasks over `forward_set`, with the
internal line types `replicate.next` and `replicate.done` and the explicit
owner route, where the plan puts it inside the substrate: a departure
awaiting acceptance (4.5).

11.16.4.13 `DbName` in `API/ts/lines.d.ts` carries no `since`, while the
lines do (D1, `db.create` carrying `since` 0 and `db.drop` its `seq`):
the stub edit was not applied because D1 is a default.

11.16.4.14 SQL differences from Python: the parameter count is checked by
`prepare` (`substrate.params_count`); several statements in one text are
caught after running and rolled back (`substrate.statement_many`); empty
SQL throws where Python accepts it. Numbers past 2^53 give
`substrate.integer_range`; `substrate.key_refused` has no JavaScript
case; a top level key "12" is `substrate.header_normal` here and
`substrate.key_digits` in Python.

11.16.4.15 Doubles above 2^53 are refused by the store's canonical JSON
with `substrate.integer_range`, where Python stores them: a class B item
the maintainer approved with every class B item of that job ("assume all
class B are approved"), so the question once left as "the maintainer's
call" is closed (4.8).

11.16.4.16 Restore and load go through `<file>-restore` (11.16.3.15).

11.16.4.17 The start leaves every database the browser lacks unloaded
until `db_load`, and replaces only held differing files: the maintainer's
database administration design.

11.16.4.18 Withdrawn: the renumbering of rowids by `db_compact`'s `VACUUM`
in the browser only is a candidate (11.16.6.9).

11.16.4.19 `db_snapshot` exports through `sqlite3_js_db_export` and the
wasm heap, so it cannot export a database of `blob_max`: approved by the
maintainer as built, its limit measured by `rung_blob_max`.

11.16.4.20 Several `db_load` calls whose images, held at once, pass
`blob_max` fault with `queue.queue_over`: approved by the maintainer.

11.16.4.21 `db.snapshot` is one blob again, by the maintainer's "the max
blob size needs to be the same as the max db size". No `db.chunk`,
`SnapshotFetch`, `SnapshotHead`, `snapshot_keep`, `snapshot_read`,
`blob_take` or piece string remains; `substrate.snapshot_digest`,
`substrate.cache_unknown` and `substrate.fill_desync` stay.

11.16.4.22 The planners' readings, built: a database grown past
`blob_max` is not refused and its image fails loud at a window;
`db_unload` is the caching and the server's replicated copy the image
kept, and no line sends a browser database to the server whole; "the db
admin design/MVC" is the minimal code of the design, not a model, view and
controller split.

11.16.4.23 The compaction readings, built: every turn appended counts,
whatever its role; the counter is the number of the scene's `_turn` rows,
counted when read; compaction runs in `turn_append` before a `user` turn;
compaction is by truncation, the summary turn holding one fixed `i18n`
text naming the turns compacted (4.8.4.26); the threshold is the setting
`turn_compact_turns`, 64, a value its writer chose, Unconfirmed. No MCP
tool compacts: the AI calls `engine.store.turn_compact` from a script, and
a `browser.turn_compact` tool was not added.

11.16.4.24 A forwarded `turn.append` applied by `operation_apply` goes
through the private `#turn_add` and never compacts, so one forwarded line
cannot compact twice: a class B item, built; the maintainer has not
confirmed it, and it is listed among the points still unresolved
(4.8.6.2). The review changes nothing.

11.16.4.25 The 322 byte step script of `ts/test_substrate.ts`, a measured
SHA-256 vector that is never run, keeps the text `engine.log(1, ...)`:
approved by the maintainer.

11.16.4.26 `test_wal_left` is not ported, because the SAH pool has no
WAL: approved by the maintainer.

11.16.4.27 Unconfirmed sqlite3.wasm details recalled from memory, used as
written and owed to the testing phase: the `OpfsSAHPoolDb` flags,
`getFileNames` paths, `importDb` synchronous and overwriting, `unlink`,
`exec` options, `prepare`, `changes(true)`, `selectValue`,
`sqlite3_js_db_export`, the error class, synchronous sync access handle
calls, `VACUUM`'s slot. Also owed: whether sqlite-wasm keeps header bytes
18 and 19 of an imported WAL database.

11.16.4.28 A long query stalls the agent: accepted by the plan, the
provider's latency being larger.

11.16.4.29 Unconfirmed: `_preferences` exists with its schema and nothing
writes it yet, as Always Allow lasts the tab.

11.16.5 Open, for the maintainer. None is held by this area alone. The
confirmation of 11.16.4.24 and the value of `blob_max` are the
maintainer's (4.8.6.2, 4.8.4.8); the review builds on both as they stand.

11.16.6 Candidates.

11.16.6.1 `db_unload` and `db_load` in `ts/substrate.ts` refuse with
`substrate.forward_pending` while forwarded lines of the database are
unanswered: a refusal between the AI API and a database that no plan asks
for, against the project rule that nothing refuses the AI API access to
the databases (an earlier review called it Requirements-Refusal): M. The
fix removes the refusal; the owner records the design it chooses for an
unload or load with lines in flight, within the task manager as the one
synchronization tool, and where that design needs a public API change it
writes it as a proposed edit instead (6, 10). Seam: 11.16.7.1.

11.16.6.2 The incremental SHA-256 of `CacheFiles` copies `utility`'s block
function, where `utility` is the single door for `sha256_hex`: S. The fix
needs a public incremental name in `ts/utility.ts`, so it is written as a
proposed edit with the whole design (6, 10) and not made.

11.16.6.3 Module level constants outside `constants`, and fields without
their one line comment, where they stand in these two files (an earlier
review's finding on the TypeScript AI side).

11.16.6.4 `ts/test_substrate.ts` compares a literal message, not its
`i18n` text; task 1.8 checks the same (12.6).

11.16.6.5 `test_create_failed` of `python/test_substrate.py` was recorded
by its writer as not portable, with no record that decides it, where the
stage 6 proof excepts only `test_wal_left`.

11.16.6.6 Document versions past 2^53 "lose precision", recorded by the
writer as a gap and left.

11.16.6.7 The text of `substrate.integer_range` says integer where the
value refused is a double (an audit's remark); the text is task 1.14's.

11.16.6.8 `test_recorded_replay` and other identifiers that still say
"recorded" after the transcripts they were taken from were deleted, where
only their comments were changed.

11.16.6.9 `db_compact`'s `VACUUM` can renumber the rowids of tables
without an INTEGER PRIMARY KEY in the browser only. Its writer recorded
this as a gap and named options, to accept it, to forward `VACUUM` or to
refuse such tables, and pointed to content divergence detection with equal
`seq`, a door (4.2); none was chosen. No class was given.

11.16.7 Seams.

11.16.7.1 Removing the `forward_pending` refusal: `ts/substrate.ts` and its
tests change first; `ts/tools_browser.ts` (task 1.27) receives a request
where its tools or tests rely on the refusal, and `ts/worker_ai.ts` (task
1.28) where the chosen design touches the replication queue.

11.16.7.2 Any `substrate.` name added, reworded or removed: task 1.14
receives the request.

11.16.7.3 Moving the constructor or `forward_set` toward the stub's form
is a seam change with `ts/worker_ai.ts` and `ts/boot.ts` (task 1.28),
which receive the request before the change lands.

11.16.7.4 A change to the kill probes' names or shapes:
`python/test_browser.py` (task 1.19) receives the request before the
change lands.

11.17 Task 1.25, MCP and the providers in TypeScript.

11.17.1 Owns: `ts/mcp.ts`, `ts/test_mcp.ts`, `ts/provider.ts`,
`ts/test_provider.ts`, `ts/provider_script.ts`,
`ts/test_provider_script.ts`.

11.17.2 Reads: `API/ts/mcp.d.ts`, `API/ts/provider.d.ts`,
`API/ts/provider_script.d.ts`, `API/mcp/tools.json`, `API/ts/lines.d.ts`,
`python/mcp.py` and `API/python/mcp.pyi` (the twin), `python/mcp_stdio.py`,
`python/engine_mcp.py`, `ts/http.ts` (the HTTP port), `ts/queue.ts`,
`ts/agent.ts`, `ts/tools_browser.ts`, `ts/worker_ai.ts` (the registration,
the handshake, the Script read), `python/seed/provider_script.json`,
`provider.json`.

11.17.3 Expected.

11.17.3.1 MCP. `ts/mcp.ts` implements JSON-RPC 2.0 and the MCP methods
`initialize`, `notifications/initialized`, `ping`, `tools/list` and
`tools/call`, capability `tools` only, at the revision "2025-06-18"
pinned as a constant; a further part of MCP is emulated only when a tool
needs it. The stub is `API/ts/mcp.d.ts`: `Server(name, version)` with
`tool_register` and `message_handle`; `Client(name, version, tasks,
owner)` with `initialize_send`, `tools_list`, `tool_call` and `result_of`;
`ClientSet` with `client_add`, `tools_cached` and `tool_call`; the types
`Tool`, `Content`, `ToolResult` and `ToolFn`.

11.17.3.2 MCP transports. `message_handle(message)` returns the response,
nothing for a notification, or a sleep. In the browser the browser server
sits behind a local port of the AI worker, and the Python server behind
the JSLB line `mcp`, whose payload is the JSON-RPC message; stdio is
Python's (`python/mcp_stdio.py`).

11.17.3.3 MCP server. It answers with the shapes, codes and texts of
`python/mcp.py`: -32600, -32601, -32602, and -32603 with `data.stack`. A
tool's sleep keeps the original `mcp` line, and its wake builds the reply
with `dispatch.reply_make`.

11.17.3.4 MCP client. One JSON-RPC id counter per client; each message is
submitted as an `mcp` line to an explicit owner; `initialize_send` is
followed by `notifications/initialized` once its reply arrives.

11.17.3.5 `ClientSet` lists the browser's and the server's tools in one
flat list under the prefixes `browser.` and `server.`, and routes a call to
its prefix's client under the bare name. Dotted names go to the provider
unmapped (D28, dotted tool names passed unmapped, to be checked at the
first real provider run).

11.17.3.6 Permits. A tool's `_meta.xsjs.permit` survives `tools/list`.
The permit set is `console_run` alone; `server.source_put` and
`server.system_restart` carry no mark and are called without asking, over
the line and over stdio.

11.17.3.7 Wiring, done by the worker (11.20), not here: `new
mcp.Server("xsjs-browser", "0")` given to `tools_browser.tools_register`;
`dispatch.handler_register("mcp", 0, (line) => server.line_handle(line))`
once on the AI thread; clients `new mcp.Client("hyperposition-engine",
"0", tasks, "ai", names_full())` and the same with `"server"`; a
`ClientSet` adding `browser` then `server`; both handshakes as boot tasks
before the first `ai.say`; no owner table entry for `mcp`.

11.17.3.8 `API/ts/lines.d.ts` calls `mcp` a push while both sides send
requests on it; that proposed stub edit is task 1.3's (12.3).

11.17.3.9 The provider protocol, the chat completion shape: `POST
{base_url}/chat/completions` with `model`, `messages`, `tools` and
`tool_choice`, read from `choices[0].message` with `content`, `tool_calls`
and `finish_reason`; images: `POST {base_url}/images/generations` with
`response_format` `b64_json`. xAI is the first and only provider tested;
another provider of the same shapes is a door (4.2).

11.17.3.10 `ts/provider.ts` is the one door, stub `API/ts/provider.d.ts`:
`chat_request(base_url, key, request)` and `image_request(base_url, key,
request)` each build one `http.request` line, `{method, url, headers,
json}`, with the key in `Authorization`; the caller submits it to the
provider owner, the HTTP port or the scripted port, and sleeps on its id.
`chat_response(reply)` and `image_response(reply)` read the wake's reply
line and throw on a body not of the shape. `tools_convert(tools)` turns
MCP tools into function tools, keeping each tool's dotted name, text and
schema and dropping `_meta`.

11.17.3.11 Replies on the http lane have `t` `http.request`, the request's
own type; an arriving `error` line is a fault.

11.17.3.12 The key is read by the server from `XSJS_PROVIDER_KEY`, a name
Unconfirmed, sent in `hello` as `provider_key`, and kept in the AI
worker's memory only, through `provider.key_set(key)`, which replaces it,
and `provider.key_get()`. The key is required only when
`provider.scripted` is false (D8).

11.17.3.13 The address and model names are `provider.json`'s `base_url`,
`chat_model` and `image_model`, empty until the maintainer fills them;
they reach the worker as `hello.provider_info` only when
`provider.scripted` is false, and the agent and the tools take them as a
`lines.ProviderInfo` argument.

11.17.3.14 The provider request waits `provider.timeout_seconds`, the HTTP
port's timer; this area sets no timer.

11.17.3.15 The scripted provider, `ts/provider_script.ts`, stub
`API/ts/provider_script.d.ts`: `ScriptPort(script)` implements
`queue.Port` with `line_post(line, transfer)`, `line_receive(fn)` and
`node()`, and answers the provider's `http.request` lines inside
`line_post` with no network, routed by the URL suffix, `/chat/completions`
or `/images/generations`.

11.17.3.16 A `Script` is `{start, nodes}`; a node is `{replies,
after_tools?}`; a reply is `{content, tool_calls?, next}`. The latest user
message is one integer matching `^(?:0|-?[1-9][0-9]*)$` that selects the
node's reply; a tool result moves to the node the reply names.

11.17.3.17 Scripted faults throw out of `line_post` into the queue: results
not asked for, results pending, an unexpected role, a `tool_call_id` not
matched (`provider_script.*`).

11.17.3.18 An image request needs `b64_json` and is answered with `n`
copies of `image_pattern()`: a 16 by 16 checkerboard PNG with hard pixel
edges, built in code from stored deflate blocks, its CRC-32 and Adler-32
computed in code. Chat ids are `chatcmpl-synthetic-<n>`.

11.17.3.19 The worker reads the Script from `/_files/provider/script.json`,
which the server seeds from `python/seed/provider_script.json` when the
row is missing; the seeded Script has one node and no replies, so input on
a root without a test driver faults. Every automated test drives the
engine this way; no AI runs in tests.

11.17.3.20 One frozen `constants` object per module; `mcp.ts` exports its
own, which holds the protocol's field and method names and codes.

11.17.3.21 Strings: the prefix `mcp.` is shared with `python/mcp.py` and
written by task 1.13, which receives requests for it (6, 8); `provider.`
and `provider_script.` are this area's. Every fault is a thrown `Error`
with the `i18n` text of a literal name.

11.17.3.22 Tests: `ts/test_mcp.ts`, `ts/test_provider.ts` and
`ts/test_provider_script.ts`, in the browser rung "stage 0: typescript
suites" under its label; each imports only its module and the harness and
compares every expected error with its `i18n` text.

11.17.4 Decided, not a finding.

11.17.4.1 `Client(name, version, tasks, owner, full?)`: an API departure
for D27, the one `names_full()` in the worker that chooses the line name
form. The exported `constants`: an API departure.

11.17.4.2 API additions an earlier job recorded, kept by D11 (the API
additions and departures stay) (4.5): `WakeFn`,
`Server.wake_register(then_type, fn)`, `Server.line_handle(line)`,
`Client.initialized_send(reply)`, `Client.tools_read(reply)`,
`Client.tools_cached()`, `ClientSet.result_of(reply)`; and
`provider.key_set` and `provider.key_get` as module state, because the
agent and the tools both need the key from `hello` and no signature
carries it.

11.17.4.3 `wake_register` registers one dispatch handler per wake type
that wraps `{request, state}`; `ToolFn(args, request)`, one
`mcp.tool_wake` type and exposing the wrapper were rejected.

11.17.4.4 The worker registers the `mcp` line handler;
`Server.handlers_register()` was the alternative not built.

11.17.4.5 A throw becomes a -32603 error response, in `message_handle` and
in wakes; a tool that submits and then throws faults the queue with
`queue.wait_missing` and its own message is lost. Faulting directly and
converting only protocol errors were the alternatives.

11.17.4.6 `result_of` throws `mcp.reply_error` on an error response, as
Python's client does; `isError: true` for the model was the alternative.
A reply with tool calls is stored only with its results (11.18), so the
fault leaves no unanswered turn.

11.17.4.7 `isError` is copied only when the tool set it, where Python
always writes it; the client refuses another protocol revision with
`mcp.version_refused`, where Python's does not; the reply checks are
Python's.

11.17.4.8 The client sends the bare tool name in `params.name`; absent
`arguments` means `{}`; a prefix is new, not empty and without a dot, and a
name is split at its first dot; `tools_cached` throws `mcp.tools_unread`
before the handshake.

11.17.4.9 `mcp.reply_unknown`'s first argument is the line id in
TypeScript and the JSON-RPC id in Python, as its writer recorded it.

11.17.4.10 `source_put` and `system_restart` are not permit tools, by the
maintainer: a refusal between the AI API and the databases that was never
a requirement breaks the API agreement between them. `ts/test_mcp.ts`
keeps its stdio tool list without their marks, has no stdio refusal case,
and its `test_reply_error` and `test_calls_routed` use the -32602
`mcp.tool_unknown` refusal of an unregistered tool, built in the test.

11.17.4.11 `key_set` replaces the key; the body read has no `error`
branch; `Authorization` and `Content-Type` keep their case.

11.17.4.12 The stored block PNG: a level 9 deflate matching the old
transcripts was rejected and `CompressionStream`, a promise, is banned.
Its values come from the deleted transcripts' base64 and `pattern_make`,
the CRC polynomial built from its exponents and the Adler modulus
computed.

11.17.4.13 Node movement on tool results, the input pattern, the four
scripted faults, routing by URL suffix, faults thrown out of `line_post`,
replies built with `jslb` rather than `dispatch` (the port is not a
handler), images needing `b64_json` in `n` copies: the writer's recorded
forms.

11.17.4.14 A field once named `awaited` is `pending`, so that the audit's
token `await` does not match.

11.17.4.15 `constants.recorded_png` in `ts/test_provider.ts` and
`ts/test_provider_script.ts` stays as test data, probably the deleted
transcripts' PNG: approved by the maintainer.

11.17.4.16 A scripted request carries `model: ""` and the bare paths
`/chat/completions` and `/images/generations`, from the empty
`ProviderInfo` the worker builds when scripted: a class B item recorded so
that no value is invented.

11.17.4.17 The provider information is passed as an argument, not kept as
module state; a `provider.info_set` was the alternative.

11.17.4.18 The Script at `/_files/provider/script.json`, seeded with no
replies: approved by the maintainer.

11.17.4.19 Unconfirmed, used as written: `media.fetch` beside `b64_json`
(the scripted port answers `b64_json` only); the key's variable name.

11.17.4.20 The provider information in `ts/test_provider.ts` and
`ts/test_provider_script.ts`, `https://api.x.ai/v1`, `grok-4` and
`grok-2-image`, is test input only: the values the shipped settings held
before the provider file took them out, kept when the tests' comments were
reworded, so that no value is invented. `provider.json` stays empty.

11.17.5 Open, for the maintainer. None in this area.

11.17.6 Candidates.

11.17.6.1 No test keeps a tool's `_meta` through `tools/list` in
`ts/test_mcp.ts`, and `test_dotted_names` of `ts/test_provider.ts` no
longer shows `tools_convert` dropping it, since the permit marks of the two
server tools were removed: S. The alternatives recorded: register
`console_run` with its mark, as the Python tests do; the mark on a
`browser.console_run` double.

11.17.6.2 `provider.key_get` with no key set is untested, the tests
sharing one global scope.

11.17.6.3 Module level constants outside `constants`, and fields without
their one line comment, where they stand in these six files (an earlier
review's finding on the TypeScript AI side).

11.17.6.4 Test values kept from the deleted transcripts in
`ts/test_mcp.ts`: `stdio_restart` still equals a transcript line, kept
(alternatives: build it with `call_message`, copy a `source_put` call);
the -32602 replacement error is not a recorded value (alternatives:
compute it with `server_make()`, use Python's
`engine_system.argument_invalid` text).

11.17.6.5 `test_list_recorded` and other identifiers that still say
"recorded" after the transcripts were deleted, where only comments were
changed.

11.17.7 Seams.

11.17.7.1 Any `mcp.` name added, reworded or removed: task 1.13 receives
the request.

11.17.7.2 The constructors of `Server`, `Client` and `ClientSet` are
called by `ts/worker_ai.ts` (task 1.28); `chat_request`, `chat_response`
and `tools_convert` by `ts/agent.ts` (task 1.26); `image_request` and
`image_response` by `ts/tools_browser.ts` (task 1.27). A change to any of
them reaches the caller's owner as a request before it lands.

11.17.7.3 The Script read and its size are `ts/worker_ai.ts`'s (11.20).

11.18 Task 1.26, the agent loop and scripts.

11.18.1 Owns: `ts/agent.ts`, `ts/test_agent.ts`, `ts/script.ts`,
`ts/test_script.ts`.

11.18.2 Reads: `API/ts/agent.d.ts`, `API/ts/script.d.ts`,
`API/ts/lines.d.ts`, `API/mcp/tools.json`, `ts/substrate.ts`, `ts/mcp.ts`,
`ts/provider.ts`, `ts/provider_script.ts`, `ts/tools_browser.ts` (the
caller of `script_run`), `ts/worker_ai.ts` (the registration),
`ts/verbose.ts`, `ts/i18n.ts`, `python/seed/prompt.json`,
`python/seed/bootstrap.js`.

11.18.3 Expected.

11.18.3.1 The turn as a chain of tasks on the AI thread, as the comment of
`API/ts/agent.d.ts` gives it. `ai.say {text}` or `ai.click {x, y}` from
the UI: the handler reads the scene, appends the player's turn, role
`user`, with `Store.turn_append`, builds the chat request and submits it
to the provider owner, with the key from `provider.key_get()`, and sleeps
with `ai.model_reply`.

11.18.3.2 `ai.model_reply`: for each tool call of the reply it submits a
`tools/call` through `ClientSet.tool_call`, storing nothing yet, and
sleeps with `ai.tool_reply`; a tool that must wait (an image, a permit,
the console) sleeps in turn.

11.18.3.3 `ai.tool_reply`: when every tool result is in, it stores the
reply that called the tools together with their results, as `tool` turns,
in one transaction, and submits the next provider request. No stored call
lacks its result, and a failed tool call leaves no unanswered turn.

11.18.3.4 A reply with no tool calls is stored and ends the turn with the
reply to the original `ai.say` or `ai.click`, `TurnEnd {turn, scene,
subtitle}`, built with `dispatch.reply_make` from the request kept in the
wake's state; the final text reply is the `subtitle` (D17: the `tide`
column stays, a universe's prompt is its document `prompt`, and the final
text reply becomes the `subtitle` of the reply to `ai.say`).

11.18.3.5 Each turn row is one provider message in the scene's database,
keyed by the scene's Document-Ref, and the store forwards each as
`turn.append`.

11.18.3.6 The request's messages: the system prompt of `prompt_build`;
then, when due, one system message holding the `db_stats` result; then the
scene's turns. Its tools are the `ClientSet`'s, converted with
`provider.tools_convert`.

11.18.3.7 The soft limit: after each turn the agent compares `total_bytes`
of `db_stats` with `db_soft_bytes`; when over, the next provider request
carries that one system message, and the AI as database administrator
decides what to unload, compact, drop or `turn_compact`. No timer.

11.18.3.8 Compaction is the store's, in `Store.turn_append`, not the
agent's: `agent.ts` holds no estimate, no `turn_compact_tokens` and no
compaction call. The replaced estimate design is kept as a design not
built (4.2).

11.18.3.9 `prompt_build(store)`: the analyst's prompt document `prompt`
in `metaverse`, then, when the scripts have made one, the current
universe's document `prompt` in the database named by the `universe` row
whose `world` is `/metaverse/world`. The seeds' writer chose a prompt
document's shape: type `prompt` with its text in a string `text`.

11.18.3.10 Time stops: nothing runs without a player task, and the agent
sets no timer; the provider request waits the HTTP port's
`provider.timeout_seconds`. In debug mode the queue's log is the
transcript of the turn.

11.18.3.11 Stub `API/ts/agent.d.ts`: `handlers_register(store, clients,
tasks, provider_owner, info)` and `prompt_build(store)`. Line types
handled: `ai.say` and `ai.click`, replied with `TurnEnd`; the wakes
`ai.model_reply` and `ai.tool_reply`. Sent: `http.request` to the provider
owner and `mcp` lines through the clients. Settings: `db_soft_bytes`
through `settings_get`; the chat model from `info`. Strings: `agent.`.

11.18.3.12 Scripts. The AI's scripts are KV values in `_files` under
`script/<name>.js`, on both sides by replication, edited with `kv_put` on
`/_files/script/<name>.js` and so editable over MCP. They are not in the
bundle, and nothing is sent to the server for compilation.

11.18.3.13 `script.script_run(store, name, args, trace)`, stub
`API/ts/script.d.ts`: reads `/_files/script/<name>.js`, a cached value
through `cache_read`, runs it as `new Function("engine", "args", text)`
inside the calling task, with `engine` the frozen `{store, log, i18n}`,
and returns `{value, lines}` or `{error, stack, lines}`, `lines` every
verbose line the run wrote. `engine.log(text)` takes no level.

11.18.3.14 With `trace` true, as `script_debug` runs it, a Proxy writes
`script.trace_call` before each store call the script makes, the text
`substrate <method> <JSON of the arguments>`; only the calls the script
makes are traced.

11.18.3.15 The seeded `script/bootstrap.js` is the plan of the database
administration; the engine seeds nothing in a universe, world or region
database. Strings: `script.trace_call`.

11.18.3.16 Tests: `ts/test_agent.ts` drives whole scripted turns through
`ScriptPort`; `ts/test_script.ts` runs and traces scripts; both run in the
browser rung "stage 0: typescript suites" under its label, import only
their module and the harness and compare every expected error with its
`i18n` text. The stage 8 proofs, the stubs of the plan's integration run
end to end with time not advancing without input, are rungs of
`python/test_browser.py` (task 1.19, checked by task 1.7).

11.18.4 Decided, not a finding.

11.18.4.1 `handlers_register(store, clients, tasks, provider_owner, info,
settings_get, register)`: an API departure an earlier job recorded,
`settings_get` and `register` beyond the stub; `info` stands in place of
the chat model by the maintainer's provider file.

11.18.4.2 A tool call turn is stored with its results after the tools run:
approved by the maintainer; the stub's comment and the plan were changed
to it.

11.18.4.3 Tool results are stored as `tool` turns and forwarded as
`turn.append`, each tool call id being answered; the wake state is
`{request, scene, calls}`; `TurnEnd.turn` is the measured `n`, and
`TurnEnd.scene` is read again at the turn end; the user turn's `since` is
compared with the measured `seq`.

11.18.4.4 The over limit message is `utility.json_text(stats)` alone,
placed after the prompt messages and before the conversation, used once;
an `i18n` sentence, the last place and a stored turn were the
alternatives.

11.18.4.5 The universe prompt's presence is read by `SELECT version FROM
_head WHERE id = ?`, where a `Store.doc_has` addition was the alternative;
an unloaded universe database faults.

11.18.4.6 A click is told to the model as the text `agent.click_text`.

11.18.4.7 Text parts are joined with "\n"; an image part throws
`agent.content_unsupported`; `isError` is not inspected.

11.18.4.8 Tool arguments that are not an object throw
`agent.arguments_invalid`, where sending the error back to the model was
the alternative; `null` content with no tool calls throws
`agent.reply_empty`; only `choices[0]` is read.

11.18.4.9 The provider timeout is the HTTP port's, from
`provider.timeout_seconds`, by the maintainer's timer decision.

11.18.4.10 The tests use doubles for the modules they call, recorded by
their writer as doubles "for unlanded modules"; the plan has a test module
import only its module and the harness. `TestCompacted` holds its
thresholds as named constants, `compact_reached: 2` and
`compact_unreached: 3`, each "a count chosen by its writer".

11.18.4.11 `script_run` takes the boolean `trace` where it took a level:
the planners' reading, built, of the maintainer's "the server and runtime
only have a debug flag". `script.level_invalid` is gone with the levels;
script levels are a design not built (4.2).

11.18.4.12 A run line's `at` is a second clock reading; a thrown value
that is not an `Error` has no stack; a missing script throws; cached
values are read through
`(store.sink() as substrate.CacheFiles).cache_read`.

11.18.4.13 `test_step_recorded` compares the 319 byte step script's
digest with `utility.sha256_hex` of its bytes: a measured constant owed to
the testing phase, if wanted back.

11.18.4.14 No MCP tool compacts turns: the AI compacts by hand with
`engine.store.turn_compact` in a script.

11.18.4.15 Unconfirmed, used as written: run and debug are a run and a
traced run; stepping or breakpoints would need a script interpreter or
DevTools in the loop.

11.18.4.16 Decided against by the maintainer: `script_put`, `script_get`
and `script_list` tools (a script is a KV row the `kv_*` tools edit);
`universe_create`, `world_create`, `region_create`, `player_switch` and
`scene_enter` tools (the seeded bootstrap script does them); compaction
decided by the agent from a token estimate.

11.18.4.17 The non scripted provider information of `ts/test_agent.ts`,
`https://api.x.ai/v1`, `grok-4` and `grok-2-image`, is test input only:
the three values the shipped settings held before the provider file took
them out, recorded by its writer so that no value is invented.

11.18.5 Open, for the maintainer.

11.18.5.1 `agent.universe_ambiguous`: the `universe` table does not make
`world` unique, so two rows with the current world make the universe
prompt lookup ambiguous, and the agent throws. Options an earlier job
named: a UNIQUE `world`; a hard error in `prompt_build`. The code holds
the second, but the question was left open after the code was written,
so the hard error is not a decision (4.7.4). The review chooses none.

11.18.6 Candidates.

11.18.6.1 A script that returns NaN, Infinity, a BigInt or a cyclic object
throws out of its tool, and the trace throws on such arguments
(`script.script_run` and its Proxy), where a run returns the value, or the
exception with its stack, and its lines.

11.18.6.2 No remnant of the replaced estimate in `ts/agent.ts` or
`ts/test_agent.ts`: no `estimate_check`, no `turn_compact_tokens`, no
estimate system message.

11.18.6.3 `agent.prompt_invalid` makes every later turn throw on a prompt
document the schema allows but not of the seeds' shape, a rule of its
writer's own (an earlier review called it an Accidental-Requirement).

11.18.6.4 Module level constants outside `constants`, and fields without
their one line comment, where they stand in these four files (an earlier
review's finding on the TypeScript AI side).

11.18.6.5 `TestTurnRecorded`, `test_step_recorded` and other identifiers
that still say "recorded" after the transcripts were deleted, where only
comments were changed.

11.18.7 Seams.

11.18.7.1 Compaction and `turn_append` are `ts/substrate.ts`'s (task
1.24); `ClientSet` and `result_of` `ts/mcp.ts`'s, and `chat_request` and
`tools_convert` `ts/provider.ts`'s (task 1.25).

11.18.7.2 `script.script_run` is called by `ts/tools_browser.ts` (task
1.27) for `script_run` and `script_debug`; a change to its result reaches
task 1.27 as a request before it lands.

11.18.7.3 The analyst's seed prompt, `python/seed/prompt.json` (task
1.16), describes the over limit message and compaction; a change to
either reaches task 1.16 as a request.

11.18.7.4 The registration is `ts/worker_ai.ts`'s (task 1.28).

11.19 Task 1.27, the browser tools.

11.19.1 Owns: `ts/tools_browser.ts`, `ts/test_tools_browser.ts`.

11.19.2 Reads: `API/ts/tools_browser.d.ts`, `API/mcp/tools.json`,
`API/ts/lines.d.ts`, `ts/substrate.ts`, `ts/mcp.ts`, `ts/script.ts`,
`ts/provider.ts`, `ts/wire.ts` (the console port's `console.input` and
`console.read`), `ts/page.ts` (`permit.ask`, `render`), `ts/media.ts`
(`media.store`, `media.fetch`), `ts/worker_ai.ts` (the registration, the
ports, the console's opening), `python/engine_verbose.py` (`verbose.tail`),
`python/engine_kv.py` (`kv.get`), `python/engine_db.py` (`db.snapshot`).

11.19.3 Expected.

11.19.3.1 Purpose. The tool layer through which the AI reaches the model,
the set of databases on the AI thread: each tool is one substrate
operation, or one request and its wake, behind one MCP tool on the browser
server.

11.19.3.2 `tools_register(server, store, tasks, provider_owner, info,
settings_get)` registers, once on the AI thread after `settings_set` and
`provider.key_set`, the sixteen browser tools of `API/mcp/tools.json` with
their descriptions and input schemas as written there, then the four
database tools. The stub, `API/ts/tools_browser.d.ts`, lists the sixteen.

11.19.3.3 The tools, each with its arguments (required unless marked
optional) and its permit flag. Only `console_run` is a permit tool; none
of the others asks the player or refuses anything:

11.19.3.3.1 `sql_run {db, statements}`, `statements` an array of
`{sql, params}` with `params` an array: SQL statements in one transaction
on a database, the single door to SQL; DDL allowed, the AI's scripts being
the database administrator; no table or database refuses a write. No
permit.

11.19.3.3.2 `db_create {db}`: an empty database, its name a C identifier;
a database outside the universe, world and region ones is allowed, and no
tool limit refuses one. No permit.

11.19.3.3.3 `db_drop {db}`: deletes a database and everything in it. No
permit.

11.19.3.3.4 `kv_get {ref}`: the value a Key-Value-Ref names, as text. No
permit.

11.19.3.3.5 `kv_put {ref, text}`: writes text under a Key-Value-Ref,
encoded with `utility.utf8_encode` before `Store.kv_put`; a script is the
row `/_files/script/<name>.js`. No permit.

11.19.3.3.6 `kv_delete {ref}`: deletes the row. No permit.

11.19.3.3.7 `kv_list {db, prefix}`: the keys under a prefix with sizes and
hashes. No permit.

11.19.3.3.8 `doc_get {ref}`: a document by Document-Ref in its encoded
form, header 0, references at 1 on, `{"$ref": n}` in the body. No permit.

11.19.3.3.9 `doc_put {db, id, body}`, `body` an object: a new version and
its head moved; returns the new Document-Ref. No permit.

11.19.3.3.10 `doc_head {db, id}`: the current Document-Ref. No permit.

11.19.3.3.11 `script_run {name, args}`, `args` an object: runs
`/_files/script/<name>.js` as a task in the worker through
`script.script_run(store, name, args, false)`; returns its value or
exception and the verbose lines it wrote. No permit.

11.19.3.3.12 `script_debug {name, args}`: the same run with the trace on,
"tracing every substrate call it makes first". No permit.

11.19.3.3.13 `image_make {prompt, key}`: generates an image and keeps it
under `/_files/<key>`; returns the key, size and sha256. No permit.

11.19.3.3.14 `render {subtitle}`, with `image` optional: shows an image by
its Key-Value-Ref with a subtitle; no image means black. No permit.

11.19.3.3.15 `console_run {text, timeout_seconds}`, `timeout_seconds` a
number: one command line in the debug console's dash, its output until the
next prompt or the timeout. Permit: `_meta.xsjs.permit` true. A debug mode
tool.

11.19.3.3.16 `verbose_tail {thread, count}`, `count` an integer: the last
lines of a thread's verbose ring, `ui`, `ai` or `server`. No permit.

11.19.3.3.17 `db_stats {}`: read only; for each open database `name`,
`bytes`, `free_bytes`, `cache_bytes` and `seq`, then `total_bytes`,
`soft_bytes` and `over`, from `Store.db_stats` with the setting
`db_soft_bytes`. No permit.

11.19.3.3.18 `db_compact {db}`: `VACUUM` on the browser's copy, the bytes
before and after; not a modifying operation, nothing forwarded. No
permit.

11.19.3.3.19 `db_unload {db}`: closes the browser's copy and deletes its
OPFS file and the cache files only it references; the server's copy
stays and nothing is forwarded. No permit.

11.19.3.3.20 `db_load {db}`: fetches the server's copy with `db.snapshot`,
one blob, and opens it as the start replacement does. No permit.

11.19.3.4 The server's tools, `source_put {name, text}` and
`system_restart {main_loop}`, both debug mode tools and neither a permit
tool, are Python's; the agent sees them as `server.` tools.

11.19.3.5 Waiting. A tool that waits submits one request with an explicit
owner and sleeps on it, woken through `mcp.Server.wake_register` by a wake
type of its own, `tools.*_reply`. The requests: `http.request` of
`provider.image_request` with `info.image_model` to the provider owner
(`image_make`); `render {scene, subtitle, image?}` to the UI, replied
Empty; `permit.ask {permit, tool, input}` to the UI, replied
`{permit, choice}`; `console.read {until, timeout_seconds}` to the console
port, replied `{text, timed_out}`; `verbose.tail {thread, count}` to the
server, replied `{lines}`; `kv.get` to the server, replied
`{size, sha256}` and blob 1; `db.snapshot {db}` to the server, replied
`{sha256, seq}` and blob 1.

11.19.3.6 Images. The reply's `b64_json` is decoded in the worker,
written to `_files` under the key, which replicates it to the server at
once, and posted to the UI as `media.store {k}` with blob 1 and its buffer
transferred, into `media_db`. A URL answer goes to the UI as
`media.fetch {url, k}`, which downloads it and replies with the bytes
(Unconfirmed).

11.19.3.7 Render and eviction. When the scene changes, `render` calls
`Store.cache_evict`, keeping the scene's header refs and the rendered
image within `files_browser_bytes`: the eviction of the `_files` browser
tier, the only automatic eviction.

11.19.3.8 The permission flow. `console_run` submits `permit.ask` to the
UI and sleeps; the UI shows Accept, Deny and Always Allow; Accept runs the
tool once, Deny returns an error to the model, Always Allow lasts the tab
and is not stored. Then the tool posts the text and a newline as
`console.input` with one blob to the console port, submits `console.read`
and sleeps; the port answers with the output once the prompt returns or
`timeout_seconds` expires. The AI reaches tty 0 only through this tool;
the user opens the console with ctrl-0 "or the AI opens it with
permission", and `console_run` is a debug tool.

11.19.3.9 A value not held. `kv_get` and `doc_get` on a value this side
does not hold (`Store.kv_held`) submit `kv.get`, check the reply's
SHA-256, refill the cache with `Store.cache_fill`, then answer; so a value
over `overflow_bytes` survives `db_unload` then `db_load`.

11.19.3.10 `db_load`'s wake checks the reply's blob against its `sha256`
with a private `snapshot_data` (`substrate.snapshot_digest` on a
mismatch), opens it with `Store.db_load(db, data)`, and compares the `seq`
it returns with the reply's (`tools_browser.load_desync`). The blob, at
most `blob_max`, streams to a cache file as it arrives.

11.19.3.11 Results are `ToolResult {content: [{type: "text", text}],
isError?}`; a script that threw returns `isError: true`.

11.19.3.12 Line names: headers use full names in debug mode and short
names otherwise, the form chosen by the worker's one `names_full()`
(D27).

11.19.3.13 Settings read through `settings_get`: `db_soft_bytes`,
`files_browser_bytes`, and `debug` for the debug tool.

11.19.3.14 Strings: `tools_browser.load_desync` and
`tools_browser.permit_denied`; errors as thrown `Error`s with the `i18n`
text of a literal name.

11.19.3.15 Tests: `ts/test_tools_browser.ts`, in the browser rung "stage
0: typescript suites" under its label, with doubles for the modules it
calls; it imports only its module and the harness and compares every
expected error with its `i18n` text. The stage 7 proofs of the tool,
`console_run` returning the output and timing out on `sleep 600`, and
Deny returning an error to the caller, are rungs of
`python/test_browser.py` (task 1.19, checked by task 1.5).

11.19.4 Decided, not a finding.

11.19.4.1 `tools_register(server, store, tasks, provider_owner, info,
settings_get)`: an API departure an earlier job recorded, `settings_get`
beyond the stub; `info` stands in place of the image model by the
maintainer's provider file.

11.19.4.2 The four database tools are registered beside the sixteen of
`API/mcp/tools.json`, which does not list them: an API addition awaiting
acceptance (4.5), whose descriptions and schemas an earlier job proposed
for `API/mcp/tools.json`; D11 (the API additions and departures stay)
keeps them.

11.19.4.3 The wake states `{key}`, `{}`, `{text, timeout_seconds}` and
`{db}`, through `mcp.Server.wake_register`.

11.19.4.4 The permit flow lives in the tool, with permit numbers per
registration; Deny returns `isError` with `tools_browser.permit_denied`.

11.19.4.5 The console's output is normalized: CRLF to LF, the echo and the
`$ ` prompt cut.

11.19.4.6 `snapshot_data` is private here and in `ts/worker_ai.ts`, not
an API addition.

11.19.4.7 The image is keyed under `/_files/<key>`, as the plan and
`API/mcp/tools.json` say; the disagreement with the deleted transcripts
was closed by their deletion.

11.19.4.8 Arguments are read with casts and are not validated against
`inputSchema`, as their writer recorded; no plan asks for a validation
against the schema.

11.19.4.9 `verbose_tail` asks the server for every thread, `ui` and `ai`
too (D13, the server's `verbose.tail_get(thread, count)` serving `ui` and
`ai`).

11.19.4.10 `sql_run`'s description carries no refusal sentence, by the
maintainer's removal of every protection; `script_debug`'s description is
the maintainer's stub edit.

11.19.4.11 The `verbose_level` tool is gone: the runtime has only a debug
flag, by the maintainer. `verbose_dump` and levels are designs not built
(4.2).

11.19.4.12 Several `db_load` calls whose images, held at once, pass
`blob_max` fault with `queue.queue_over`: approved by the maintainer.

11.19.4.13 The fetch of a value not held and `render`'s eviction are the
fixes of an earlier job for a value lost after `db_unload` then `db_load`
and for the unbuilt `_files` eviction.

11.19.4.14 `test_put_recorded` compares the step script's digest with
`utility.sha256_hex` of its bytes: a measured constant owed to the testing
phase, if wanted back.

11.19.4.15 The test doubles are cast through `unknown`.

11.19.4.16 Unconfirmed, used as written: `media.fetch` beside `b64_json`;
the AI worker owns the console socket and relays it to the UI.

11.19.4.17 Decided against by the maintainer: `script_put`, `script_get`
and `script_list` tools; `universe_create`, `world_create`,
`region_create`, `player_switch` and `scene_enter` tools; `sql_run`
guarding the engine's tables.

11.19.4.18 The non scripted provider information of
`ts/test_tools_browser.ts`, `https://api.x.ai/v1`, `grok-4` and
`grok-2-image`, is test input only: the three values the shipped settings
held before the provider file took them out, recorded by its writer so
that no value is invented.

11.19.5 Open, for the maintainer. None in this area.

11.19.6 Candidates.

11.19.6.1 `console_run` neither checks `debug` nor opens tty 0, where the
plan makes it a debug tool and has the AI open the console with
permission. Seam: 11.19.7.2.

11.19.6.2 `ts/test_tools_browser.ts` keeps the withdrawn `sql_run` refusal
sentence in a private copy, `constants.refusal_sentence`, a sentence the
maintainer's removal of every protection took out of the description.

11.19.6.3 The lines this file builds, `verbose.tail` and `db.snapshot`
among them, are in short names always, as their writer recorded, where
headers use full names in debug mode.

11.19.6.4 The seam of 11.16.6.1: the `forward_pending` refusal of
`db_unload` and `db_load`.

11.19.6.5 Module level constants outside `constants`, and fields without
their one line comment, where they stand in these two files (an earlier
review's finding on the TypeScript AI side).

11.19.6.6 `test_put_recorded` and other identifiers that still say
"recorded" after the transcripts were deleted, where only comments were
changed.

11.19.7 Seams.

11.19.7.1 The `forward_pending` refusal: `ts/substrate.ts` (task 1.24)
changes first; this area receives a request where its tools or tests rely
on the refusal.

11.19.7.2 Opening tty 0 from `console_run` needs the worker's console
opening (`ts/worker_ai.ts`, task 1.28) and may touch the console view's
state (`ts/console_view.ts`, task 1.30); each receives a request before
the tool relies on it. The `debug` check needs nothing outside this file.

11.19.7.3 `permit.ask` and `render` are answered by `ts/page.ts` (task
1.29), `media.store` and `media.fetch` by `ts/media.ts` (task 1.30),
`console.read` by `ts/wire.ts` (task 1.23); a change to a payload reaches
that owner as a request before it lands.

11.19.7.4 The registration and the ports are `ts/worker_ai.ts`'s (task
1.28); `script.script_run` is task 1.26's.

11.20 Task 1.28, the AI worker and boot.

11.20.1 Owns: `ts/worker_ai.ts`, `ts/test_worker_ai.ts`, `ts/boot.ts`,
`ts/test_boot.ts`.

11.20.2 Reads: `API/ts/boot.d.ts` and `API/ts/lines.d.ts` (no stub
`API/ts/worker_ai.d.ts` exists); `ts/queue.ts`, `ts/wire.ts`, `ts/http.ts`,
`ts/substrate.ts`, `ts/mcp.ts`, `ts/agent.ts`, `ts/tools_browser.ts`,
`ts/provider.ts`, `ts/provider_script.ts`, `ts/settings.ts`,
`ts/verbose.ts`, `ts/error_overlay.ts`, `ts/overlay.ts`, `ts/page.ts`,
`ts/test_all.ts`, `ts/test_hook.ts`, `html/engine.html`; on the server
`python/bootstrap.py` (the `hello` and its reply) and `python/main_loop.py`
(the seed of the scripted provider's Script).

11.20.3 Expected.

11.20.3.1 The AI worker owns both WebSockets, the owner table of its task
manager, sqlite3.wasm with the OPFS SAH pool VFS, every database and the
cache directory. It runs the agent, the MCP server and clients, the AI's
scripts and replication. A long query stalls the agent, which the plan
accepts.

11.20.3.2 One bundle runs on both threads; the worker is a Blob URL of the
page's own bundle, its entry chosen by `self.name`. `boot.boot_run()` is the
last `data-worker` script of the page and runs the worker's entry when
`self.name` is `"ai"`, the page's otherwise. The worker's source is
`"use strict";\n` followed by the text of every `script[data-worker]` in
document order, one Blob of type `text/javascript`, started as
`new Worker(url, {name: "ai"})`; the globals `sqlite3_wasm_base64` and
`sqlite3InitModule` exist in the worker only. This contract was recorded by
the writer of the page build and is accepted (11.10).

11.20.3.3 `boot.ts` is the one initialization module, under the
maintainer's rule that system initialization need not abide by the rules
for how the system is used unless that is reasonably convenient:
`sqlite3InitModule`, `installOpfsSAHPoolVfs` and its capacity, the OPFS
directory, its file handles and `createSyncAccessHandle` for the cache files
use promises there directly, and no port turns them into lines. No platform
port is built in `ts/queue.ts` for them. Once `boot.ts` has handed its
objects over, the worker runs on the task manager alone.

11.20.3.4 The synchronization audit of `python/test_posix.py` refuses
`await`, `.then(`, `new Promise`, `Atomics` and `SharedArrayBuffer` in
every `ts/*.ts` but `queue.ts`, `wire.ts`, `http.ts`, `media.ts` and
`boot.ts`, so `ts/worker_ai.ts` and the two test modules of this area hold
none of them. D29, the default that `async` is not added to the audit,
stands.

11.20.3.5 The start, as its writer recorded it and kept as decided:
`boot.worker_ai_main` waits for the page's first message `{port,
base_url}`, the worker's end of the UI to AI channel and the page's http or
https address, because a Blob URL cannot be the base of `/token`; it makes
the server's `WirePort` with an empty `substrate.CacheFiles([])` as its sink
before `hello`; when `hello` arrives it initializes sqlite3.wasm with
`sqlite3InitModule({wasmBinary})` from the base64 text (decoded strictly,
D26, the default that `utility`'s messages go through `i18n` and
`base64_decode` is strict), installs the SAH pool named `xsjs-pool` in the
directory `.xsjs-pool` with the initial capacity `pool_capacity(n)`, two
files for each of the server's `n` databases plus 36, and opens the OPFS
directory `xsjs-cache` with its 256 files `"0"` to `"255"` for synchronous
access; then it calls `worker_ai.worker_start`.

11.20.3.6 `worker_ai.worker_start` runs ten steps in this order: the
thread's queue; the server port, wrapped in a `WireTap` in debug mode; the
console port; the provider key; the store and replication; the MCP server
and the browser tools; the MCP clients and the agent; the start chain; the
answer to `hello`; the internal task `worker.start`.

11.20.3.7 `hello` is the server's request with `i` 1 and the payload
`bootstrap`, `sha256`, `pid`, `root`, `settings`, `seq` per server database
and `provider_key`, with `provider_info` only when `provider.scripted` is
false. The worker calls `settings_set` with the settings, posts
`settings.set` to the UI, answers `hello` with an empty reply posted
directly on the wire, then posts `boot.hello` with `bootstrap`, `sha256`,
`pid` and `root` to the UI. The client sends nothing on the wire before
`hello` arrives. The wire limits are built after `settings_set` (D24, the
default that the `hello` itself is decoded with a line of at most 10 MiB
and no blobs).

11.20.3.8 The provider key of `hello` goes to `provider.key_set` and lives
in the worker's memory only. `worker_ai.info_read(hello, scripted)` returns
`hello.provider_info` when `provider.scripted` is false and the constant
`scripted_info`, three empty strings, when it is true. The provider owner
`"http"` is an `HttpPort` whose timer is `provider.timeout_seconds`, or the
scripted provider's `ScriptPort` when `provider.scripted` is true; the
worker reads that provider's Script from `/_files/provider/script.json`.

11.20.3.9 The worker's queue carries the ports `ui` (the channel's end from
the page), `server` (the `WirePort`), `console` (the `ConsolePort`) and the
provider owner. Its owner table maps the worker's own types to `ai` (`ai.`,
`worker.`, `replicate.`, `tools.`, `settings.put`, and the UI's `kv.`,
`doc.`, `db.`, `turn.` and `sql.` tasks on the store), `verbose.` to
`server`, so that a `verbose.put` from the UI reaches the server with
nothing added, and the console types as 11.22.3.11 says; it has no entry for
`mcp`, whose clients name their owner explicitly. In the test bundle `tap.`
is owned by `server`.

11.20.3.10 Every queue attaches the verbose sink with
`sink_attach(verbose.sink_set, settings.settings_get)` after
`settings_set`. In debug mode the queue writes every submit, dispatch,
sleep, wake and reply as a verbose line, and `verbose.put` is forwarded to
the server whenever `debug` is true. No thread has a verbose level: the
maintainer's "the server and runtime only have a debug flag".

11.20.3.11 The store is `new substrate.Store(sqlite3, pool, cache, root,
overflow_bytes, compact_turns)`, six arguments, built after `settings_set`
with `turn_compact_turns` as the sixth. The worker calls `forward_set(fn,
names_full())`, whose `fn` only queues; `handlers_register` for the UI's
store tasks; and `WirePort.cache_attach` with the cache's `cache_read`
before any blob held in a cache file is sent.

11.20.3.12 Replication, a coordinator's design of the first job built
here: `fn(line)` appends each forwarded line to a FIFO of its database and
notifies the local task `replicate.next`; its handler takes the oldest line
of a database with none in flight, submits it to `server` and sleeps with
`replicate.done`; that wake calls `Store.forward_done(line, reply)` once
per line and notifies `replicate.next` again while the FIFO holds more. So
every modifying operation reaches the server after its commit, in order,
one in flight per database, through the task manager.

11.20.3.13 `forward_done` checks that the reply's `seq` is the line's
`since` plus 1 and skips the check for `db.create` and `db.drop` (D1, the
default that a new database starts at `seq` 0, `db.create` carries `since`
0 and `db.drop` carries the database's `seq`). A mismatch is the desync of
the plan, a fault ending in Reload.

11.20.3.14 The worker's forward queue, `worker_ai.ForwardQueue`, holds at
most `blob_max` bytes of blobs, the sum of the `s` of the blobs of the
lines it holds; line bytes do not count. Holding a line past it throws
`worker_ai.queue_over`, a fault. Bytes that live in the WASM heap are
copied before `task_submit` moves the buffers of a line.

11.20.3.15 The start chain, as tasks: the store's `start_open(hello.seq)`
deletes the browser's files that the server lacks, unloads those whose
`seq` differs and returns their names, and marks the server's other
databases unloaded, so a differing file is replaced only for a database the
browser holds; for each returned name the worker sends one `db.snapshot` and
restores the file; then it loads, one at a time, `metaverse`, `_files`, the
current world's database, named by `/metaverse/world`, the matching
universes' databases, and the databases of the scene, the Document-Ref in
`/$world/scene`, and of its image; then it opens the provider port, runs
both MCP handshakes at once, posts the scene's image to the UI as
`media.store` and sends `render`. `metaverse` and the current world's and
universe's databases are loaded before the first turn.

11.20.3.16 The scene is the engine's one document contract: type `scene`,
with `subtitle` text and, when there is one, `image`, a reference to a
media row; a scene without them is the fault `worker_ai.scene_invalid`.

11.20.3.17 The checks of every start replacement and load: a `db.snapshot`
reply carries `sha256` and `seq` and the database file as blob 1, one blob
of at most `blob_max`. Before it restores, the worker checks the blob's
SHA-256 against `sha256` (`substrate.snapshot_digest`), and it compares
the `seq` of the file it opened with the `seq` the server sent, a
difference being the fault `worker_ai.snapshot_desync`. The store
restores through a temporary `<file>-restore` that it checks read only
before it imports it over the live copy. No line sends a browser database
to the server whole.

11.20.3.18 The snapshot pieces are gone with the maintainer's one blob
window: no `db.chunk`, no `StartStore.blob_take` and no
`ChainParts.settings_get`, which read `message_max` and `line_max` for the
pieces. `message_max` and `queue_max` are read nowhere.

11.20.3.19 MCP and the agent: `new mcp.Server("xsjs-browser", "0")` is
given once to `tools_browser.tools_register(server, store, tasks,
provider_owner, info, settings_get)` after `settings_set` and
`provider.key_set`, and the `mcp` line is routed to it by one
`dispatch.handler_register("mcp", 0, ...)` on the AI thread; the clients
are `new mcp.Client("hyperposition-engine", "0", tasks, "ai",
names_full())` and the same with `"server"`, joined in a `ClientSet` that
adds `"browser"` then `"server"`; the handshakes (both `initialize_send`,
sleep; `initialized_send` and both `tools_list`, sleep; `tools_read`) run as
start tasks before the first `ai.say`; `agent.handlers_register(store,
clients, tasks, "http", info, settings.settings_get,
dispatch.handler_register)` is called once after `settings_set` and
`provider.key_set`.

11.20.3.20 The settings relay: in debug mode each thread's settings sender
notifies `settings.put` to `ai`, and the worker submits `settings.put` to
the server as a request and sleeps with the internal wake
`worker.settings_put`, because the Python server refuses a reply to a
notification. In debug mode `settings_put(id, value)` changes the live
value and sends `settings.put`, which rewrites the settings file in the
root for the next `hello`; the server refuses `settings.put` outside debug
mode.

11.20.3.21 Debug mode: the server port is wrapped in a `WireTap` that posts
each line it passes, in both directions, rendered as its JSON text followed
by one `<blob "n"=K>` tag per blob, as `overlay.line {tty: 1, text}` to the
UI (`worker_ai.overlay_sent`, `worker_ai.overlay_received`). The overlay of
tty 1 holds the last `verbose_ring` lines in both directions, newest last;
it does not show the `verbose.put` lines the worker forwards, which would
feed it to itself. In debug mode the same rendering of the wire traffic and
the page's `console.*` output go to the server as `verbose.put`, so
`_verbose` holds the page's view; `debug` alone gates it. Line headers use
full names in debug mode and short names otherwise, chosen by the one
`worker_ai.names_full()` (D27, the default that the name form is chosen by
one `names_full()` in the worker).

11.20.3.22 Faults: any throw in the worker reaches `error_overlay`, whose
worker side posts `fault` to the UI with `self.postMessage`; an arriving
`error` line is a fault; an `error` line before `hello` shows the server's
message and stack (`wire.error_first`); a second `hello`, as after
`system.restart`, is a fault ending in Reload (D9, the default that a second
`hello` after `system.restart` is such a fault); a close with no `error`
line is the fault "connection closed with code N and no error line".
Nothing is retried; recovery is a full page reload.

11.20.3.23 The console relay, `worker_ai.console_register`: `console.open`
from the UI is submitted to the console port, which fetches `/token`, opens
tty 0 and replies with `{token}` (D23, the default that the `console.open`
reply carries `token`), and the worker answers the UI's `console.open`
with it after the internal wake `worker.console_opened`; `console.input`
goes to the console port; `console.output` and `console.exit` go to the
UI; `console.close` closes the console port and replies Empty.

11.20.3.24 The test bundle: `boot.test_worker(run)` sets the globals
`test_sqlite3` and `test_pool` at `hello`, on a test pool cleared at its
start, and runs the worker's suite inside the internal task `worker.tests`
with `tap.` owned by `server`. The UI's suite runs first and then sends
`worker.tests`, so every UI TAP line is on the wire before the worker's
suite starts and `typescript.tap` holds the UI's document, then the
worker's. `boot.test_engine` is `page.test_engine`; `ts/test_hook.ts`, in
the test bundle only, starts `boot.worker_ai_main` in the worker of the
test engine page.

11.20.3.25 Messages go through `i18n` with a literal name at the call
site; the prefix of this area is `worker_ai.`, and it formats the names of
the modules it stands in for, such as `substrate.snapshot_digest`. Every
thrown value is an `Error`, with `cause` when wrapped; no error is
swallowed, defaulted or retried.

11.20.3.26 Tests: `ts/test_worker_ai.ts` and `ts/test_boot.ts` run on the
worker thread of `ts/test_all.ts`. A test that expects an error compares
the message with the `i18n` text, never only a base class; no test
enshrines the implementation's number where a recorded number exists.

11.20.3.27 The plan's proofs of this area are browser rungs of
`python/test_browser.py` (11.11, 12.5): the hello relay; a UI put of
`blob_max` plus one refused first by the AI worker's task queue with
`queue.queue_over`; a `verbose.put` forwarded from the UI through the worker
to the server unchanged; a fault ending in the `<pre>` screen and Reload; a
close without an `error` line reported as such; the start replacement of a
differing file; the desync reload; the string to string table replicated
from the UI and from the AI; and those the first writer asked for: the
worker start and its promises, the hello step order, a second `hello`, a
fault on worker load, the overlay feed, the start with a scene image, pool
and cache exhaustion.

11.20.4 Decided, not a finding.

11.20.4.1 Promises in `boot.ts`, the exemption of `boot.ts` by name in the
audit, and no platform port: the maintainer's initialization rule (an
earlier coordinator's platform port design was withdrawn for it).

11.20.4.2 Initialization runs after `hello` and waits for the page's
`{port, base_url}`: the writer's decisions, kept.

11.20.4.3 The fixed capacities: the pool's `pool_capacity(n)`, 2 files per
database plus 36 spare (16 more databases and 4 temporary files, a default
chosen by its writer), and the 256 cache files are fixed at initialization,
with no `slot_add` when `slots_free()` runs low and no growth at run time,
because promises are confined to initialization. Recorded as class B for
the maintainer, with the options a platform port for run time growth or
larger constants; an earlier review read it as against the maintainer's
"don't worry about too many DBs" and the rule against refusals. The built
form stands and is not filed.

11.20.4.4 `boot_run` tests `self.name === "ai"`; on the main thread
`self.name` is `""`. `API/ts/boot.d.ts` says "undefined on the main
thread"; its correction to "empty on the main thread" was proposed to the
maintainer and not applied (section 4.6).

11.20.4.5 `API/ts/boot.d.ts` declares `page_main`, `DomPort` and
`worker_ai_main` inside `boot`; the code keeps the UI's code in namespace
`page` and the worker's in `worker_ai`, and `boot` re-exports
`page_main`, `DomPort`, `test_page` and `test_engine` and defines
`worker_ai_main` and `test_worker` itself, as recorded at first writing. No
stub of `page` or `worker_ai` exists, and `API/ts/boot.d.ts` leaves the
test only functions out (an accepted API addition).

11.20.4.6 The UI to AI lane is a `MessageChannel` apart from the worker's
own message channel, because the worker's `error_overlay` posts faults with
`self.postMessage`.

11.20.4.7 The ten steps of 11.20.3.6 and the start chain of 11.20.3.15,
loads of the scene's and the image's databases at start included, one
database at a time, with the two MCP handshakes at once: the writer's
decisions, kept.

11.20.4.8 The settings relay as a request to the server with the wake
`worker.settings_put`, for the reason in 11.20.3.20.

11.20.4.9 The internal line types, none of them in `API/ts/lines.d.ts`:
`replicate.next` and `replicate.done` (API additions that stand for the
review and await the maintainer's acceptance, whose stub edit is proposed
in section 4.6); the `worker.` types `start`,
`initialized`, `listed`, `fetched`, `stored`, `rendered`,
`console_opened`, `settings_put` and `tests`, recorded at first writing
with `worker.restored` and `worker.loaded`. The code names the start
chain's wake of a `db.snapshot` reply `worker.snapshot_reply`; no record
names it, and the snapshot design changed twice after the first writing
(pieces, then the maintainer's one blob).

11.20.4.10 The `WireTap` exists in debug mode only, and it does not render
`verbose.put` into the overlay: the fix of the overlay that fed itself,
kept by the maintainer's decision on verbose levels.

11.20.4.11 `worker_ai.info_read` (an API addition) and the constant
`scripted_info` of three empty strings, so a scripted request carries
`model: ""` and the bare paths: class B, no value invented.

11.20.4.12 The Script at `/_files/provider/script.json`, seeded by the
server from `python/seed/provider_script.json` when missing, with one node
and no replies, so input on a root with no test driver faults: approved by
the maintainer.

11.20.4.13 Replication as page tasks over `Store.forward_set(fn)`, with
the two `replicate.` types and the explicit owner route, where the plan
puts replication inside the substrate: a plan departure that stands for
the review and awaits the maintainer's acceptance.
`forward_done` checks `since` plus 1, accepted in place of the first
design's comparison with `seq_get(db)`, which failed whenever local writes
ran ahead of the line in flight.

11.20.4.14 No back pressure in the worker: a UI upload of 128 MiB waits
only for the UI to AI hop, so the forward queue may throw
`worker_ai.queue_over`; approved as built (the options were the test
pacing itself or back pressure in the AI).

11.20.4.15 Nothing gates `db_load`: loads whose images, held at once, pass
`blob_max` fault with `queue.queue_over` (approved by the maintainer).

11.20.4.16 The snapshot digest check `snapshot_data` is written privately
in `ts/worker_ai.ts` and again in `ts/tools_browser.ts`, not as an API
addition, as the writer of the one blob change recorded.

11.20.4.17 `worker.tests` is sent after the UI's suite, the fix of the UI
TAP lines lost when the worker's suite hung or faulted.

11.20.4.18 The test hooks of 11.20.3.24 and a test engine page outside the
production bundle, `ts/test_hook.ts` in the test bundle only: approved.
The production bundle's `boot.ts` re-exports `test_engine`, an accepted
API addition, and D25, the default that test only exports stay, holds.

11.20.4.19 Unconfirmed and accepted, the testing phase's to check: the
option `wasmBinary`, the pool's option names and capacity raising, the
shapes of the sync access handles, messages posted before the worker's
script runs, `terminate()` closing the sockets, and that the AI worker owns
the console socket and is the only owner of sockets (the plan names the
rework: the start script, bootstrap's role handling and the console lane).

11.20.4.20 D11, the default that the API additions and plan departures of
the earlier jobs stay, holds for this area's public names.

11.20.4.21 `worker_ai.names_full()` is read on both threads, by
`ts/test_all.ts` too: it is the one reader of D27, the default that the
line name form is chosen by one `names_full()` in the worker.

11.20.4.22 When `provider.scripted` is false, `worker_ai.info_read` takes
`hello.provider_info` by a cast and does not check that the `hello`
carries it: its writer recorded this with its reason, that the server
always sends `provider_info` when `provider.scripted` is false.

11.20.4.23 The non scripted provider information of
`ts/test_worker_ai.ts`, `https://api.x.ai/v1`, `grok-4` and
`grok-2-image`, is test input only: the three values the shipped settings
held before the provider file took them out, recorded by its writer so
that no value is invented.

11.20.5 Open, for the maintainer.

11.20.5.1 A verbose line written before `settings_set` throws, because
each thread's ring reads `verbose_ring` from its first line. Shown to the
maintainer as a question, "is such a line ever wanted?", and not answered;
its options are not in the tree. It belongs with `ts/verbose.ts` (11.13);
the start of this area is where such a line would be written.

11.20.6 Candidates.

11.20.6.1 The overlay of tty 1 never shows `hello` and its reply, where the
plan's overlay holds the rendered lines in both directions. Check
`WireTap` and the hello path through `WirePort.hello_receive`. Recorded by
the review of 2026-10-20; no class given.

11.20.6.2 `worker_ai.script_read` reads the provider's Script with
`value_text` and has no fetch on a miss, so a Script over `overflow_bytes`
faults the start with `substrate.cache_unknown`; the plan has `kv_get` of a
reference the browser lacks ask the server with `kv.get` and store the
answer first. Class S.

11.20.6.3 At first writing the record said "a cached boot image always
fetched with `kv.get`" and that the plan's general `kv.get` was "still not
built", where the plan's start fetches "the referenced media the browser
lacks". Check the start chain's image fetch; a later record built the
fetch on miss for the `kv_get` and `doc_get` tools only.

11.20.6.4 At first writing the record said the held line measure of the
queue was "duplicated" in the worker. Check `ForwardQueue`'s measure
against `ts/queue.ts`'s, now that both count only blob bytes; the mark is
one of class S.

11.20.6.5 The review of 2026-10-20 found large public surfaces in
`ts/worker_ai.ts` (and `ts/page.ts`) with no `API/` declaration. D25, the
default that test only exports stay, and the decided absence of a stub
(11.20.4.5) bear on it; the census of 12.1 checks the stubs.

11.20.6.6 The seams of 11.10's `error_overlay.overlay_install()` candidate
and 11.13's `settings_put` candidate, as 11.20.7 says.

11.20.6.7 The record of the provider information change listed among its
gaps that `provider.scripted` is read twice. Check the reads of
`provider.scripted` in `ts/worker_ai.ts` (`info_read` and the provider
owner); no class was given.

11.20.7 Seams. Each starts on the side that receives the request (8.6.7).

11.20.7.1 With tasks 1.18 (`html/engine.html`) and 1.21
(`ts/error_overlay.ts`): 11.10's candidate, that
`error_overlay.overlay_install()` runs only from the last script, so a throw
while the bundle or xterm.js loads leaves a blank page. Its calls are in
`boot.worker_ai_main` and `boot.test_worker` here and in `page.page_main`
and `page.test_page` (task 1.29). Task 1.18 holds the candidate and sends;
this area receives.

11.20.7.2 With task 1.21 (`ts/settings.ts`): 11.13's candidate, that
`settings_put` in debug mode changes only the UI's copy, where the plan
changes the live value and sends `settings.put`. Task 1.21 sends; this
area receives for the worker's side of the relay.

11.20.7.3 With task 1.20 (`ts/test_all.ts`): 11.12's candidate, that
`self.name` is tested as `""` there and as `"ai"` in `boot.boot_run`.
Whichever side changes receives first.

11.20.7.4 With task 1.24 (`ts/substrate.ts`): a fetch on a miss, for the
candidates 11.20.6.2 or 11.20.6.3, that needs a `Store` name beyond the
accepted `kv_held` and `cache_fill` is a change of a public API, proposed
(section 6); task 1.24 receives.

11.20.7.5 With task 1.23 (`ts/wire.ts`): a change to the hello path, for
the candidate 11.20.6.1, or to the console port's token or close; that
task receives.

11.20.7.6 With task 1.27 (`ts/tools_browser.ts`): 11.19's candidate, that
`console_run` neither checks `debug` nor opens tty 0, where the plan has
the AI open the console with permission; a fix that needs the worker's
console relay sends to this area, which receives.

11.20.7.7 With task 1.29 (`ts/page.ts`): the UI's handlers of the lines
the worker posts (`settings.set`, `boot.hello`, `media.store`, `render`,
`permit.ask`, `console.*`, `overlay.line`, `fault`); a change of a payload
is a seam, received first by the side that handles the line.

11.21 Task 1.29, the page.

11.21.1 Owns: `ts/page.ts`, `ts/test_page.ts`, `html/engine.css`.

11.21.2 Reads: `API/ts/boot.d.ts` (`page_main`, `DomPort`; `page` has no
stub of its own), `API/ts/lines.d.ts`, `API/ts/error_overlay.d.ts`,
`API/ts/media.d.ts`, `API/ts/console_view.d.ts`, `API/ts/overlay.d.ts`;
`ts/console_view.ts`, `ts/overlay.ts`, `ts/media.ts`, `ts/error_overlay.ts`,
`ts/settings.ts`, `ts/queue.ts`, `ts/worker_ai.ts`, `ts/boot.ts`,
`ts/tools_browser.ts` (the sender of `permit.ask`), `ts/test_hook.ts`,
`html/engine.html`, `html/test_engine.html`, `python/page_build.py`.

11.21.3 Expected.

11.21.3.1 The UI thread builds the DOM once, routes the player's text and
clicks to the AI worker as tasks, paints what `render` names, keeps
`media_db`, hosts the console view and the overlays, shows permission
requests and runs `error_overlay`. It owns no SQLite and never sees a wire.

11.21.3.2 The bundle begins with `error_overlay`, `utility`, `ui_strings`
and `settings`, then `i18n` and the rest in reference order; then
`page.ts` creates the AI worker from the bundle. `page.page_main` installs
`error_overlay` first, builds the DOM, creates the worker from the
bundle's Blob URL, owns the UI queue with its media port and its DOM port,
routes input, paints renders, hosts the console view and the overlays and
shows permission requests.

11.21.3.3 The worker is made by the contract of 11.20.3.2:
`"use strict";\n` and the text of every `script[data-worker]` in document
order, one Blob of type `text/javascript`, `new Worker(url, {name: "ai"})`.
The page's first message to the worker is `{port, base_url}`, the worker's
end of a `MessageChannel` and the page's http or https address. No module
touches the DOM or `Terminal` when the bundle loads; `Terminal` exists on
the UI thread only.

11.21.3.4 `error_overlay.stop_register` is called once, by `page.ts`, with
what stopping the app means: closing the wire and terminating the worker.
The UI holds no wire; that `terminate()` closes the worker's sockets is
Unconfirmed (11.21.4.12).

11.21.3.5 `page.ts` builds in `<body>`, in this order, `canvas#image`;
`div#debug`, the container of the console view and the overlays; and
`div#subtitle`, the band holding the subtitle's `<p>`, the permit area
`#permit` and a form with `input#input`.

11.21.3.6 `html/engine.css` lays the page out as one column: `body` is a
flex column, on a black page; `#image` is fixed over the viewport and
shows the whole image (`object-fit: contain`);
`#debug` stands at the top, positioned so that it paints after the fixed
`#image` by tree order, shrinks to the room left and scrolls inside its box
(`overflow: auto`), on black; `#subtitle` is an in flow band at the bottom,
on black. `engine.css` sets no `display` on a `<pre>` inside the overlay
container, because an author `display` overrides `[hidden]`.

11.21.3.7 The console view's rows are fitted to the space above the band,
and a shown overlay keeps its newest line in view (`Overlay.end_show`).

11.21.3.8 The console view and the overlays show above the scene's image.
Unintentional invisibility is always a bug, not a style issue (the project
rules). Two states are accepted by the maintainer: with the console and an
overlay both shown, the overlay below the console scrolls the console's
top rows out of view; and the subtitle band lies over the bottom strip of
the fixed image.

11.21.3.9 `DomPort(container)` finds the image, the input and the permit
area and listens to them. Its listeners are events, not promises, so
`page.ts` needs no exception in the synchronization audit: they post the
player's text and clicks as `ui.input` notifications (`{text}` or `{x, y}`)
and control keys as the internal `ui.control_key`. It answers `dom.choice
{permit, choices}` by showing one button per choice and replies
`{choice}` when one is clicked.

11.21.3.10 The `ui.input` handler submits `ai.say {text}` or `ai.click {x,
y}` to the AI worker and sleeps with `ui.turn_end`, which enables the
input again. The reply to `ai.say` or `ai.click` is `TurnEnd {turn, scene,
subtitle}`; its `subtitle` is the final text reply, which goes back to the
page as the subtitle (D17, the default whose third part is that the final
text reply becomes the `ai.say` reply's `subtitle`).

11.21.3.11 `render {scene, subtitle, image?}` paints the image `media`
holds under `image`, or black when `image` is absent, shows the subtitle
and replies Empty.

11.21.3.12 `media.store` and `media.fetch` from the AI are owned by `ui`:
version 0 handlers submit a copy without `i` with `task_submit(copy,
"media")` to the media port, sleep keeping the request in `state`, and the
wake `ui.media_reply` replies with `reply_make(original, payload, blobs)`,
carrying blob 1 for `media.fetch`. The media port is
`media.MediaPort(media_db_bytes, timeout_seconds)`; its download timer is
a named constant holding a sane default whose one line comment says its
writer chose it (11.21.6.1).

11.21.3.13 The permission flow: a tool marked `permit`, `console_run`
alone, submits `permit.ask {permit, tool, input}` to the UI and sleeps. The
UI's handler shows the request with Accept, Deny and Always Allow below it
(the choices `accept`, `deny` and `always`), submits `dom.choice` to the
DOM port of `page.ts` and sleeps with `ui.permit_reply`; its wake replies to
`permit.ask` with `{permit, choice}`, which wakes the tool. Accept runs the
tool once; Deny returns an error to the model; Always Allow lasts the tab
and is not stored, not in the preferences either. The tool keeps the flow
and its permit numbers (11.19). Nothing else between the AI API and the
databases asks permission.

11.21.3.14 The console view, from the page: ctrl-0 calls `view_toggle()`
and, on an idle view, also returns `open_request()`, whose wake
`ui.console_reply` calls `open_done`; `console.output` calls
`output_feed` with blob 1; `console.exit` calls `exit_done`; the wake
`ui.console_closed` calls `close_done`. The UI's owner table maps
`console.` to `ai` and `console.output` and `console.exit` to `ui`. The
page drives the view through `page.ConsoleControl`.

11.21.3.15 The overlays: the page gives `overlay.Overlay` a live container
and `verbose_ring`, decodes `overlay.line` into `{tty, text}` for
`line_add`, and maps ctrl-n, n from 1, to `overlay_toggle(n)`; ctrl-0 stays
the console view.

11.21.3.16 `settings.set` from the AI gives `settings_set(value)` its one
call; then the UI queue attaches its verbose sink. The page gates the
overlays and `settings_put` on `debug`, the only switch of the page, which
has no verbose level. The page reads `debug`, `queue_synchronous`,
`media_db_bytes` and `verbose_ring`.

11.21.3.17 `boot.hello {bootstrap, sha256, pid, root}` is shown by the
page. A `fault` line from the AI worker reaches `error_overlay`, which
replaces the screen with the message and the stack in a `<pre>`, stops the
app and offers Reload.

11.21.3.18 The production page carries no test code. `page.test_page(run)`
and `page.test_engine(run)` are accepted API additions in `page.ts`;
`ts/test_hook.ts` and `html/test_engine.html` are the test bundle's.

11.21.3.19 Messages go through `i18n` with a literal name; the prefix of
this area is `page.`. Every thrown value is an `Error`, with `cause` when
wrapped; nothing is swallowed.

11.21.3.20 Tests: `ts/test_page.ts` is a DOM suite that runs on the UI
thread only; its fixtures read `document` in `setUp`, never at
construction; a test that expects an error compares the message with the
`i18n` text.

11.21.3.21 The plan's proofs of this area are browser rungs of
`python/test_browser.py` (11.11, 12.5): the page showing `hello`; a fault
ending in the `<pre>` screen and Reload; ctrl-0 showing and hiding the
console view; Deny returning an error to the caller; the stress test of the
UI thread, its `long_task_ms` a soft target reported as a measurement and
a synchronous network load on the main thread a hard failure; a PNG with
ctrl-1 open and one with the console visible; the visibility rungs; and
those the first writer asked for: click and keys on the real page, the
overlay feed, the media decode path, the start with a scene image.

11.21.4 Decided, not a finding.

11.21.4.1 The column layout of 11.21.3.6, the fix of an open console that
covered the subtitle, the permit buttons and the input, made with no colour
change; `#debug` keeps painting after the fixed `#image` by tree order
(the alternatives recorded were `z-index: 1` and a fixed `#debug`).

11.21.4.2 The two invisible states of 11.21.3.8, approved by the
maintainer.

11.21.4.3 `#debug { background: black; }` and `#subtitle { background:
black; }`, colour motivated only by the invisibility rule (white overlay,
subtitle and permit text over a light image): class B, left for the
maintainer to accept or revert; built, and not filed. With it, the
recorded choices of `overflow: auto` over wrapping and of black on
`#debug` over black on `#debug pre` only.

11.21.4.4 Click coordinates in image pixels are floored, not clamped; an
empty text is sent as `ai.say ""`.

11.21.4.5 A message from the worker on its own channel that is not a
`fault` is a fault (`page.message_unknown`); the UI to AI lane is the
separate `MessageChannel` (11.20.4.6).

11.21.4.6 `page` has no stub; `boot` re-exports `page_main`, `DomPort`,
`test_page` and `test_engine` (11.20.4.5).

11.21.4.7 `page.test_page` registers no stop function and maps `tap.` to
`ai`; `page.test_engine` serves a test engine page outside the production
bundle, a coordinator's decision approved by the maintainer.

11.21.4.8 No UI action calls `ConsoleView.close_request` (approved: the
plan names none); ctrl-0 on an idle view sends `console.open` again, so the
console reopens without a page load (approved; the maintainer asked for
it).

11.21.4.9 The internal types `ui.control_key` and `ui.media_reply`, with
`ui.console_reply` and `ui.console_closed` of 11.22, none in
`API/ts/lines.d.ts`; `ui.turn_end` and `ui.permit_reply` are in it.

11.21.4.10 No label per TypeScript module: the page's modules carry the
label of the rung that runs them. The deferred design, `test_page` reading
a category from `location.search`, is not built.

11.21.4.11 The formatter's output stands: one object key of `ts/page.ts`
without quotes and strings requoted or merged, with the same values.

11.21.4.12 Unconfirmed and accepted, the testing phase's to check: the
capture phase receiving keys before xterm.js; `terminate()` closing the
sockets; messages posted before the worker's script runs; xterm 5.5.0's
`xterm.css`, recalled from memory, against which `engine.css` was written.

11.21.4.13 D25, the default that test only exports stay, and D11, the
default that the API additions stay, hold for this module's public names.

11.21.5 Open, for the maintainer: none is recorded for this area alone.
The console's question of 11.22.5 bears on what the page shows.

11.21.6 Candidates.

11.21.6.1 The image download timer: the page passes
`provider.timeout_seconds` to `MediaPort` as its download timeout, a reuse
by availability that the media module's writer recorded ("no setting names
it"). The plan's provider request waits `provider.timeout_seconds` and the
console command its own argument; "every other timer is a named constant
holding a sane default, its one line comment saying its writer chose it".
An earlier coordinator ordered this timer made a constant; the maintainer's
"use sane timer defaults" then set its form. The stub gives
`MediaPort(budget_bytes, timeout_seconds)`, so the constant can stand in
`ts/page.ts`.

11.21.6.2 The permission flow of 11.21.3.13: `dom.choice` submitted to the
DOM port and the wake `ui.permit_reply`, the three choices, and Always
Allow lasting the tab and stored nowhere. Check `ts/page.ts` with the tool
side of `ts/tools_browser.ts`.

11.21.6.3 Every state in which a part of the page is unintentionally
invisible, beyond the two of 11.21.3.8 (the project rules). States recorded
and fixed: `#debug` under the fixed `#image`; a tall `#debug` covering the
band; the console's last rows scrolled out of view inside `#debug`; a tall
overlay's newest lines out of view. Check each again, and the band, the
permit buttons and the input with the console and each overlay shown.

11.21.6.4 The large public surface of `ts/page.ts` with no `API/`
declaration, as 11.20.6.5 says.

11.21.6.5 The calls of `error_overlay.overlay_install()` in
`page.page_main` and `page.test_page`, for 11.10's candidate (11.21.7.3).

11.21.6.6 At first writing the record listed among its gaps that
`boot.hello` was "logged at level 1 only", where the stage 5 proof has
`page.ts` showing `hello` (11.21.3.17, 11.21.3.21); the runtime has since
lost its verbose levels (11.13.3.28). Check how `page.ts` shows the
`hello` it receives (`page.hello_shown`); no class was given.

11.21.7 Seams. Each starts on the side that receives the request (8.6.7).

11.21.7.1 With task 1.30 (`ts/media.ts`): the download timer of 11.21.6.1,
only if its owner moves the constant into `ts/media.ts`, which changes the
stub's constructor; task 1.30 receives.

11.21.7.2 With task 1.27 (`ts/tools_browser.ts`): the payload of
`permit.ask` and its answer; the side that handles the line receives first.

11.21.7.3 With tasks 1.18 (`html/engine.html`) and 1.21
(`ts/error_overlay.ts`): 11.10's `overlay_install` candidate; task 1.18
sends, this area receives for `page.page_main` and `page.test_page`.

11.21.7.4 With task 1.21 (`ts/overlay.ts`, `ts/settings.ts`): the overlay's
container, ring and newest line; 11.13's `settings_put` candidate, which
the page gates on `debug`.

11.21.7.5 With task 1.30 (`ts/console_view.ts`): `ConsoleControl` and the
console's wakes; the side that changes a member receives first.

11.21.7.6 With task 1.28 (`ts/worker_ai.ts`): the lines of 11.20.7.7.

11.21.7.7 With task 1.18 (`python/page_build.py`, `html/engine.html`): the
build merges `engine.css`, the bundle and xterm.js into the one page; the
template's markers are task 1.18's.

11.22 Task 1.30, media and the console view.

11.22.1 Owns: `ts/media.ts`, `ts/test_media.ts`, `ts/console_view.ts`,
`ts/test_console_view.ts`.

11.22.2 Reads: `API/ts/media.d.ts`, `API/ts/console_view.d.ts`,
`API/ts/lines.d.ts`; `ts/page.ts` (the caller of both modules),
`ts/queue.ts`, `ts/wire.ts` (the `ConsolePort` and its token),
`ts/worker_ai.ts` (the console relay and `media.store`),
`ts/tools_browser.ts` (`image_make`, `render`, `console_run`),
`ts/utility.ts`; xterm.js 5.5.0, pinned under `third_party/`.

11.22.3 Expected.

11.22.3.1 The media tiers, in the plan's words "Sparingly in the browser,
aggressively on the server. Budgets are settings.": `media_db` on the UI
thread keeps
the decoded images in use and evicts by its budget `media_db_bytes`;
`_files` in the AI worker keeps the current scene's references and evicts
on leaving the scene within `files_browser_bytes`; `_files` on the server
keeps everything ever stored and never evicts, in this version.

11.22.3.2 The browser tier `_files` is evicted by `Store.cache_evict(db,
keep, budget)`, which the `render` tool calls when the scene changes,
keeping the scene's header references and the rendered image within
`files_browser_bytes` (tasks 1.24 and 1.27). Nothing else evicts
automatically.

11.22.3.3 The image path: `image_make` submits an image request and
sleeps; the reply's `b64_json` is decoded in the AI worker, written to
`_files` under the key, which replicates it to the server at once, and
posted to the UI as `media.store` with the buffer transferred, into
`media_db`. A URL answer is handed to the UI as `media.fetch`, which
downloads it and replies with the bytes. `render` then names the image
the UI paints. Fetching on the server is a door, not built.

11.22.3.4 `media.ts` is the UI thread's media cache, `media_db`: a map
from a Key-Value-Ref to its decoded image within a byte budget. Nothing in
it touches SQLite. It is one of the four modules that turn an event of the
platform into a reply line (the image decoded, the download), so its
promises are allowed by the synchronization audit.

11.22.3.5 `media.MediaPort(budget_bytes, timeout_seconds)` implements
`queue.Port` (`API/ts/media.d.ts`): `line_post` answers `media.fetch {url,
k}` with `MediaReply {k, size, sha256}` and the bytes as blob 1 once they
are downloaded and decoded, and `media.store {k}`, whose blob 1 is the
image, with `MediaReply` once decoded; it answers `error` on a failure or
when the
download timer expires. `image_get(k)` returns the decoded image, or
`undefined` once evicted.

11.22.3.6 `media.ImageCache(budget_bytes)`, with `image_put`, `image_get`,
`total_bytes` and `keys_list`, and `media.MediaExchange(line)`, with `key`,
`source`, `image_reply`, `decode_reply`, `download_reply` and
`timeout_reply`, are accepted API additions, test only exports; the stub
does not carry them (section 4.6).

11.22.3.7 The download is a wait that can fail, so it has a timer; its
value comes from the caller (11.21.6.1).

11.22.3.8 `console_view.ts` holds xterm.js in a hidden container on the UI
thread and speaks ttyd's client protocol: the first JSON message with the
columns and the rows, `'0'` input, `'1'` resize. Each message it sends is
one `console.input` line; each `console.output` line's blob is fed to it.
ctrl-0 toggles the view, which keeps its scrollback, colours and features
while hidden.

11.22.3.9 `console_view.ConsoleView(container, tasks)` has `view_show`,
`view_hide`, `view_toggle` and `output_feed(data)`
(`API/ts/console_view.d.ts`), and the accepted additions
`open_request(): dispatch.Sleep`, which throws `console_view.open_phase`
unless the view is idle, `open_done(wake)`,
`exit_done()`, which throws `console_view.exit_phase` unless the view is
open, the wake type `ui.console_reply`, and `open_wanted`,
`close_request`, `close_done` with the wake type `ui.console_closed`. The
phases are idle, opening, open and closing.

11.22.3.10 `view_show` and `view_toggle` change visibility only; the
opening is driven through the UI's task queue. ttyd's first message carries
the `token` of the `console.open` reply (D23, the default that the
`console.open` reply carries `token`, fetched from `/token`), never a hard
coded one. The terminal takes no input until the first message is sent and
after `console.exit`. The module registers no handler; the page registers
its wakes. Every `task_submit` and `line_notify` names its owner `ai`.

11.22.3.11 The console lane: `console.open` from the UI makes the AI
worker open tty 0 and relay; output arrives as `console.output` with one
blob and input goes as `console.input` with one blob, both the raw bytes of
ttyd's protocol, its first JSON message included; `console.close` closes
the socket; `console.exit {code}` is pushed when ttyd closes it. On the AI
thread `console.` is owned by `ai`, `console.input` by the console port,
and `console.output` and `console.exit` by `ui`. The server side is ttyd
and dash; no Python line type exists for the console.

11.22.3.12 Tty 0 is the debug console: `bootstrap.py` with the role
`console` runs `/bin/dash` through `verbose.exec` at the setting
`verbose_level` when `debug` is true, with a cooked pty that echoes, and
exits 1 when `debug` is false. The user opens it with ctrl-0; the AI opens
it with permission, through `console_run` alone.

11.22.3.13 The columns are 120 and the rows are fitted to the space above
the subtitle band; a space with no room for one row is the error
`console_view.rows_unfit`. The plan sets no console size by settings,
because xterm.js sends its own size.

11.22.3.14 Messages go through `i18n` with a literal name; the prefixes of
this area are `media.` and `console_view.`. Every thrown value is an
`Error`, with `cause` when wrapped; no failure is defaulted.

11.22.3.15 Tests: `ts/test_media.ts` and `ts/test_console_view.ts` run on
the UI thread; a test that expects an error compares the message with the
`i18n` text; the console view's opening is tested through a real
`queue.TaskQueue`.

11.22.3.16 The plan's proofs of this area are browser rungs of
`python/test_browser.py` (11.11, 12.5): `echo` through dash into xterm.js;
`^C` ending `sleep 600`; ctrl-0 showing and hiding the view; the role
refused outside debug mode; `console_run` returning the output and timing
out on `sleep 600`; the console opened, exited and opened again; the rows
fitted and refitted; and the image made and rendered in the scripted turn.
The writers left these for rungs: a real PNG kept, the download as blob 1,
a network failure, a status outside 200 to 299, the timeout, undecodable
bytes, eviction closing a real `ImageBitmap`; keystrokes dropped while
input is off, feeding while hidden, a token accepted by a ttyd with a
credential.

11.22.4 Decided, not a finding.

11.22.4.1 An image counts width times height times 4 bytes (the
alternative recorded was its encoded length).

11.22.4.2 Eviction is oldest first by insertion: a lookup does not refresh
an image, the newest is always kept, a key stored again becomes the
newest, and an evicted image is closed (the alternatives recorded were
least recently used, refusing over budget, evicting before the insert).

11.22.4.3 `media.fetch` decodes before it replies, and an undecodable
download is an `error` reply; a status outside 200 to 299 is a failed
download, named in the cause.

11.22.4.4 Failures are `error` lines, so faults on the UI queue that end
in Reload (the alternative recorded was an error field in `MediaReply`, a
change of `API/ts/lines.d.ts`). A malformed request throws from
`line_post`. A `media.store` blob must be bytes; a cache handle throws.

11.22.4.5 The `media.fetch` reply carries the bytes as blob 1 and the
payload in the order `k`, `size`, `sha256`. Decoding is by
`createImageBitmap(new Blob([bytes.slice()]))`.

11.22.4.6 Unconfirmed and accepted: `media.fetch` stands beside
`b64_json` (the plan's rework would be one line type and one UI handler
fewer); the scripted provider answers `b64_json` only.

11.22.4.7 The wake `ui.console_reply` carries the state `null` (the
alternatives recorded were the name `ui.console_open` and the state
`{"open": id}`).

11.22.4.8 Until the first message is sent and after exit, xterm's
`disableStdin` is true, and text that reaches the view anyway is a hard
error,
`console_view.input_phase` (rejected: throwing on every early key,
buffering, dropping).

11.22.4.9 `exit_done` returns the view to idle and ctrl-0 on an idle view
sends `console.open` again, so the console reopens without a page load:
built at the maintainer's request and approved, with its rung opening,
exiting and opening.

11.22.4.10 `close_request` exists and no UI action calls it, as the plan
names none (approved).

11.22.4.11 The rows are fitted to the space above the band, because the
plan rejects fixed console size settings; the columns stay 120.

11.22.4.12 The console view's lines use full names always, the console
being debug only.

11.22.4.13 Unconfirmed and accepted: xterm.js fed while hidden keeps its
state (the plan calls this an open research goal, decided once by its
result, with the headless package as the design alternative, not a runtime
fallback); the AI worker owns the console socket.

11.22.4.14 The `console.open` reply carries `token` though
`API/ts/lines.d.ts` gives it Empty; the stub row `ConsoleOpenReply {token:
string}` was proposed to the maintainer and not applied (section 4.6). The
same holds for the additions of 11.22.3.6 and 11.22.3.9, missing from
their stubs, and for the `console_view.*` phase names.

11.22.4.15 D25, the default that test only exports stay, and D11, the
default that the API additions stay, hold for both modules.

11.22.5 Open, for the maintainer.

11.22.5.1 The xterm `Terminal` constructor options, `{cols, rows,
disableStdin}`, were written from memory of the 5.x API and not checked
against the pinned 5.5.0 typings, and the resize path was recorded as
unreachable without a fit addon. The options recorded for the resize path
were to pin `@xterm/addon-fit` or to delete `resize_send` and its tests; a
later record fitted the rows to the space above the band. The review
chooses none.

11.22.6 Candidates.

11.22.6.1 `media.ts` builds `stack: error.stack`, which the review of
2026-10-20 listed among defaults and unreachable branches.

11.22.6.2 `columns: 120` and `rows: 40` of `console_view.ts`'s constants
were recorded as invented and unmarked; they were first taken from a
recorded console transcript that is deleted, and the rows are now fitted at
run time (11.22.3.13). Each such constant's comment must say its writer
chose it.

11.22.6.3 At first writing the record said `output_feed` has no phase
check. Check it against the phases of 11.22.3.9.

11.22.6.4 The download timer of 11.21.6.1, if its fix comes here.

11.22.6.5 Its writer recorded that `ts/test_console_view.ts` registers the
wake handler of `ui.console_reply` once per bundle, and a later review
found TypeScript tests that leave registered handlers in the thread's live
state. Check the handlers this test registers against the test rules (3,
11.12.3.20): no test leaves state another test sees, and no suite
registers a type that another suite on the UI thread registers.

11.22.7 Seams. Each starts on the side that receives the request (8.6.7).

11.22.7.1 With task 1.29 (`ts/page.ts`): `page.ConsoleControl`, the
console's wakes, the media handlers and the construction of `MediaPort`
with its budget and timer; the side that changes a member receives first.

11.22.7.2 With task 1.23 (`ts/wire.ts`): the token of the `console.open`
reply and ttyd's first message; task 1.23 receives for its port.

11.22.7.3 With task 1.28 (`ts/worker_ai.ts`): the console relay and the
`media.store` the start chain posts.

11.22.7.4 With task 1.27 (`ts/tools_browser.ts`): `image_make`, `render`
and 11.19's `console_run` candidate.

11.22.7.5 With task 1.18 (`python/page_build.py`): xterm.js and its
`xterm.css`, merged into the one page from the pinned archive.

## 12 Read only reviewers

12.0 These tasks edit nothing outside `tmp/review/`. Each writes requests
to the owners of section 11 and a report as 10.3 says, its definition of
done covering its review. A Decided item that states the built option of a
question with no answer of the maintainer decides the code, and the
question stays open, as 11.0 says for section 11.

12.1 Task 1.1, the census.

12.1.1 Checks: read only, over the tree, by `grep`, `ls`, `find` and
reading; it edits nothing outside the review's own directory (section 8),
writes its requests to the owners and its report. Seven inventories: the
`i18n` calls and strings of both languages and of PowerShell; the settings
keys; the whitelist; the two tsconfig lists; the two tables of test
modules; the stubs of `API/python/` and `API/ts/` against their modules;
`API/mcp/tools.json` against the registered tools.

12.1.2 Expected.

12.1.2.1 Every call of `i18n` with a literal name in `python/` and `ts/`,
code and tests, has an entry in `i18n/en-US.json`. A call is
`i18n("name", ...)`, or `i18n.i18n("name", ...)` where the module is
imported whole, as in `python/test_browser.py`; a call written over several
lines counts as well. The name is always a literal at the call site.

12.1.2.2 An entry's placeholders match its call: the set of indices of the
placeholders `\{(0|[1-9][0-9]*)\}` in the text equals `{0, ..., n-1}` for
the n arguments after the name; only ASCII digits count, so `{01}` is
literal text. Both languages apply this one rule, substituting in one pass.

12.1.2.3 Every entry has a call outside the tests. Deliberate exceptions,
recorded: the patched `t.*` names of `python/test_i18n.py` and the missing
name probes of `ts/test_i18n.ts`. `i18n_format(name, text, args)` of
`ts/i18n.ts`, an accepted addition through which a test supplies its own
text, is not a call of `i18n`.

12.1.2.4 `i18n/en-US.json` is one flat JSON object of string values, ASCII,
its keys sorted by code point. Only task 1.40 writes it, from the fragments
(section 14); the census writes nothing into it. A name belongs to the
owner of its module prefix; a prefix used in both languages is written by
the owner of its Python module: `substrate.` by task 1.14; `mcp.`,
`dispatch.`, `settings.` and `verbose.` by task 1.13; `jslb.` by task 1.12
(6.5).

12.1.2.5 Which messages go through `i18n`: every message of an engine
module, and the messages of `utility` (the default D26, `utility` messages
through `i18n` and a strict `base64_decode`, section 4.4). By decision, not
through it: the TAP modules of both languages and `ts/unittest.ts`, plain
English, so the TAP tests load while the strings file is missing;
`error_overlay`, which depends on nothing; `category.py`, the driver's and
the runners' own messages, `devtools.py`, `reformat.py`, `test_posix.py`
and `third_party_fetch.py`, which write f-strings or plain English;
`powershell/test_lint.ps1`, literal strings. A runner that checks an
expected error still compares it with its `i18n` text.

12.1.2.6 PowerShell keeps its own strings file: every name a script uses
from `powershell/en-US/i18n.psd1` is defined there, and every name defined
there has a use.

12.1.2.7 `settings.json`, at the top of the checkout, holds constants only,
each with a sane default, never a password or a key: `debug`,
`queue_synchronous`, `verbose_level`, `verbose_ring`, `line_max`,
`blob_max`, `overflow_bytes`, `chunk_bytes`, `srv_buf_size`,
`media_db_bytes`, `files_browser_bytes`, `db_soft_bytes`,
`turn_compact_turns`, `long_task_ms`, and `provider` with `scripted` and
`timeout_seconds`. A constant no module reads is not there.

12.1.2.8 Keys that are not in `settings.json`, by decision: `message_max`,
`queue_max`, `verbose_forward` and `turn_compact_tokens`, gone with the
designs they served; `base_url`, `chat_model` and `image_model`, moved to
`provider.json`; `port_windows`, `port_wsl`, `console_enabled`,
`console_columns`, `console_rows`, `mcp_protocol_version` and `log_ring`,
which no module reads (the console is debug mode, xterm.js sends its own
size, the revision is a constant).

12.1.2.9 The key set of `settings.json` is the key set of
`API/settings.json`; of the key and type tables of `python/settings.py`
(`settings_check`) and of `ts/settings.ts`; of the `Settings` interface of
`API/ts/settings.d.ts`; and of every fixture that writes a whole settings
object: the Python tests that copy the checkout's `settings.json`, the
`Settings` literals of the TypeScript tests, and the roots that
`python/test_wire.py` and `python/test_browser.py` build. The Python check
refuses a missing key, an extra key and a wrong type, by exact type
identity, so a `bool` is not an `int`.

12.1.2.10 Each key has a reader. Recorded readers: `blob_max`, the one
window of every blob; `verbose_level`, read by the console role alone as
the shell's level; `verbose_ring`, the size of each thread's ring;
`turn_compact_turns`, 64, the count of a scene's turns at which it is
compacted; `files_browser_bytes`, by `Store.cache_evict`, which the
`render` tool calls when the scene changes; `db_soft_bytes`, 1 GiB, a soft
limit that refuses nothing; `provider.timeout_seconds`, by the provider
request; `debug`, the one switch of debug mode and of the server's and the
page's tracing.

12.1.2.11 `provider.json`, beside `settings.json`, holds exactly
`base_url`, `chat_model` and `image_model`, empty strings until the
maintainer fills them out. It is read only when `provider.scripted` is
false, an empty value then being an error. Its name, place and keys are
Unconfirmed.

12.1.2.12 Every source file outside `.git`, `third_party/` and the
directories git ignores (`build/`, and the one holding the engineering
records and the review's own files) is matched by a line of
`python/reformat_whitelist.txt`: top level files by name, files in
subdirectories by glob. A new source file is added when it is created.

12.1.2.13 The recorded exclusions, which are not misses: `.md`, `.json` and
`.css` files are never added, and the comment check has no lexer for
`.json` or `.css` and would raise on them, so `html/engine.css`,
`i18n/en-US.json`, `settings.json`, `provider.json`, `API/settings.json`,
`API/mcp/tools.json`, `python/reformat_table.json`, the JSON seeds of
`python/seed/`, both tsconfig files and the `.md` files stay out; the
lines `LICENSE.md` and `README.md` are the maintainer's, open (11.2.5.14);
`API/sql/*.sql` stays out for want of a `.sql` lexer, a class B item for
the maintainer. The whitelist's writer left out "configuration, data,
third party and `.md` files" (12.1.5.4). The PowerShell files are in, since
the maintainer's request of 2026-10-21, and a new one is added like any
other; the stubs are in, through `API/python/*.pyi` and `API/ts/*.ts`.

12.1.2.14 Each whitelist line follows the matching rule of 11.2.3.10 and
matches at least one name, every match a file; each whitelisted file's
extension has a row in `python/reformat_table.json`, whose comment lexer
`comments_find` knows. A miss is a request to task 1.10, which adds the
line, and for a new extension a row with its lexer.

12.1.2.15 `ts/` holds every script, each defining one frozen object named
after its module. `ts/tsconfig.json` lists every module of `ts/` that is
not a test module, in reference order, beginning with `error_overlay`,
`utility`, `ui_strings` and `settings`, then `i18n` and the rest; it lists
no `test_*.ts` and no `test_hook.ts`, as the production page carries no
test code. `ts/tsconfig.test.json` lists those modules and every test
module, `test_all.ts` and `test_hook.ts` among them, in reference order. No
list names a missing file, and every `ts/*.ts` is in the list it belongs
to. tsc compiles with `module` none and `outFile` into one classic script,
`strict` on, TypeScript 5.x with no `ignoreDeprecations` (the default D16,
section 4.4). Requests go to task 1.18.

12.1.2.16 `_MODULES` of `python/test_all.py` (11.1.3.16) lists every Python
unittest module `python/test_*.py` once, with its label, but for the
runners `test_posix.py`, `test_wire.py` and `test_browser.py`, which the
driver runs after the stream is clean; the TAP modules' tests first;
`test_reformat` before `test_test_posix`; `test_test` last; no
`test_test_all` and no `test_category`; no name twice. Requests go to task
1.9.

12.1.2.17 The tables `first_modules`, `page_modules` and `worker_modules`
of `ts/test_all.ts` list every `ts/test_*.ts` but `test_all.ts` and
`test_hook.ts`: `test_tap_producer` and `test_unittest` first, on both
threads; every other module in the table of the thread that runs it, the
writer's choice; the UI's suite runs first, then the worker's. Requests go
to task 1.20.

12.1.2.18 Each stub of `API/python/` and `API/ts/` against its module:
every public name and signature. A difference recorded as an accepted
addition or departure (section 4.5), as an edit proposed and not applied
(section 4.6), or in an area's Decided list, is accepted and listed. An
unrecorded difference is a U finding and a request to the owner, who moves
the code to the stub, as a seam change where other areas call it (8.6.7).
A stub edit is proposed instead (10.3.9) only where this file states the
code's form, or where the stub's form would break a recorded decision. No
agent edits `API/`, which is the maintainer's.

12.1.2.19 Modules with no stub, by record: `reformat.py` and
`test_posix.py`, as no tool has one; the drivers and runners; `page` and
`worker_ai`, whose public functions `API/ts/boot.d.ts` declares inside
`boot` (11.20.4.5, 11.21.4.6). `API/ts/boot.d.ts` leaves the test only
functions out, as it does `test_page`. Test only exports stay (the
default D25, section 4.4).

12.1.2.20 `API/mcp/tools.json` is the list as `tools/list` returns it,
checked against the tools that `ts/tools_browser.ts` and
`python/engine_system.py` register: each name, description, schema and
prefix. The client sees the browser tools and the server tools in one flat
list under the prefixes `browser.` and `server.`.

12.1.2.21 The browser tools: `sql_run {db, statements}`, whose description
holds no refusal, SQL rules being no security boundary; `db_create {db}`,
`db_drop {db}`; `db_stats {}`, `db_compact {db}`, `db_unload {db}`,
`db_load {db}`; `kv_get {ref}`, `kv_put {ref, text}`, `kv_delete {ref}`,
`kv_list {db, prefix}`; `doc_get {ref}`, `doc_put {db, id, body}`,
`doc_head {db, id}`; `script_run {name, args}`, `script_debug {name,
args}`; `image_make {prompt, key}`, `render {image, subtitle}`;
`console_run {text, timeout_seconds}`, a permit tool, debug; `verbose_tail
{thread, count}`. The server tools: `source_put` and `system_restart
{main_loop}`, debug. The permit set is `console_run` alone: neither
`source_put` nor `system_restart` carries a permit mark. Requests go to
task 1.27 and task 1.15.

12.1.3 Decided.

12.1.3.1 The four database tools `db_stats`, `db_compact`, `db_unload` and
`db_load` are absent from `API/mcp/tools.json`: the edit was not applied,
as the additions await acceptance and the plans state their names and
arguments, not their descriptions and schemas.

12.1.3.2 Public names missing from their stubs that are pending additions
(section 4.5), such as `verbose.LineRing`, `VerboseBatch`, `ValueStore` and
`Store.db_load`, are listed, not filed. The TAP code's departures from its
stubs (11.1.4.3) are recorded. The browser `Store`'s recorded departures
from `API/ts/substrate.d.ts` stand, among them `forward_set(fn, full)`,
whose second argument carries the name form of the default D27 (the line
name form chosen by one `names_full()` in the worker, section 4.4), though
a later audit found the stub's one argument and changed nothing.

12.1.3.3 Dotted tool names are passed to the provider unmapped (the default
D28, checked at the first real provider run, section 4.4).

12.1.3.4 `API/sql/*.sql` outside the whitelist, class B (11.2.4.9). The
whitelist lines `archive.sh` and `clean.sh` are a candidate of task 1.10
(11.2.6.9), and `LICENSE.md` and `README.md` are open (11.2.5.14): the
census lists them and requests nothing.

12.1.3.5 The order of the keys of `i18n/en-US.json` by code point, and the
`\n` escapes of `queue.error_line` and `queue.stopped`, kept as written:
Unconfirmed, accepted.

12.1.3.6 The empty `python/vectors/`, left for the maintainer, is outside
the census; the vectors are written to `build/vectors`.

12.1.4 Open.

12.1.4.1 `API/sql/*.sql` and a `.sql` lexer, which the maintainer may want
(11.2.5.12).

12.1.4.2 The gap the plan asked to be reported: `from i18n import i18n` is
the maintainer's decision and is not in the project rules, which only the
maintainer edits (12.2.4.4).

12.1.5 Candidates.

12.1.5.1 `API/README.md` names the plan file of the earlier job, which no
longer exists in the tree. `API/` is the maintainer's: the census lists it
as a proposed edit (10.3.9), not a request.

12.1.5.2 The plan named the server tool `source_put {name}`, while
`API/mcp/tools.json` and the code take `{name, text}`; an earlier review
recorded the difference, never scheduled. The census lists it with the
plan's words, for the maintainer.

12.1.5.3 Stub comments left as found: the handler comment of
`API/ts/dispatch.d.ts`, recorded as stale; a comment in `API/ts/queue.d.ts`
that cites "debug mode of 4.2", a section number of the plan, which no
longer exists. Each a proposed edit.

12.1.5.4 `python/pyproject.toml` and the other TOML files are outside the
whitelist, with no lexer for them; recorded for the maintainer and not
changed (11.2.6.4).

12.1.5.5 `srv_buf_size` and `long_task_ms` were recorded as read only by
the test runners; `xsjs_start.ps1` passes the size as a literal (11.3.6.5).

12.1.5.6 The roots of `python/test_browser.py` inherit `debug`,
`verbose_level` and `provider.scripted` from the checkout's
`settings.json` (task 1.19).

12.1.5.7 `ts/test_tools_browser.ts` keeps its own copy of the withdrawn
`sql_run` refusal sentence (task 1.27).

12.1.6 Requests go to: task 1.9 (`_MODULES`); task 1.10 (whitelist lines
and table rows); task 1.18 (the tsconfig lists); task 1.20 (the tables of
`ts/test_all.ts`); task 1.13 (`settings.json`, `provider.json`,
`python/settings.py`); task 1.21 (`ts/settings.ts`, `ts/i18n.ts`); for a
string or a stub, the owner of its module (sections 11.1 to 11.22); task
1.27 and task 1.15 (the tools); the coordinator for a file no entry lists.
Edits of `API/` and `README.md` are proposed for the maintainer. Task 1.40
checks the whitelist, tsconfig and test table items again on the changed
tree (section 14).

12.2 Task 1.2, the rules sweep.

12.2.1 Checks: by `grep` over the whitelisted files, read only, editing
nothing outside the review's own directory (section 8); one request per
owner per rule, with every hit listed. A hit in a file no agent edits (the
`API/` stubs, `README.md`, `LICENSE.md`, and the parts that the default D22
holds untouched, section 4.4) is listed as accepted or as a proposed edit
for the maintainer, not requested. `archive.sh` and `clean.sh` are outside
the review's scope (5.6). The rules are those of section 3 and the
project rules; the forms each is swept by follow.

12.2.2 Expected.

12.2.2.1 Errors fail loud: no error is swallowed, defaulted or retried; no
branch is written for a case that cannot happen, and a module with no
handler for a case makes no branch for it; the first failure only, and
nothing tallies failures. Swept forms: a Python `except` that passes,
returns a default or continues; a bare `except:`, or an `except Exception`
with no raise; an empty TypeScript `catch`; `??` and `||` giving a default
to a required value; PowerShell's `-ErrorAction SilentlyContinue`; `||
true` and `2>/dev/null` in shell.

12.2.2.2 Not swallowed, by the error rules of the decoders: a JSON parse
failure of any kind in a decoder is a `WireError`; a decoder fault is
raised once and the port closes; lines completed before a fault are
returned and the fault is raised by the next feed.

12.2.2.3 Values: every timer and size is a named constant. The provider
request waits `provider.timeout_seconds` and the console command
`console_run`'s `timeout_seconds` argument; every other timer is a named
constant holding a sane default, its one line comment saying its writer
chose it. No fake data: every value is a measurement, plain arithmetic on
one, or such a default, and no test enshrines the implementation's number
where a recorded number exists. Swept forms: a number used as a timer or a
size outside a named constant; a named timer whose comment does not say
that its writer chose it.

12.2.2.4 Names: every function and class identifier carries two English
words, private ones included; modules and test modules are the exception.
The names given by the maintainer, the plans or `API/` stay: `verbose.exec`
and `verbose.log`, each runner's `main`, `reformat.reformat`, `idle()`,
`rung_blob_max`, `test_test`, and every name a stub declares, such as
tappy's `Result`, `Plan` and `Bail`. A library's names that the code
implements are the library's, such as unittest's `setUp`, `startTest`,
`addSuccess` and `addSubTest`, since the plans build on unittest in both
languages, and the TypeScript harness's copies of them, an accepted
addition. Swept form: a name of one word, or of three or more.

12.2.2.5 Counting words: the records count a test method's words after the
`test_` prefix that unittest requires (the moved tests "keep theirs", two
words). For the `rung_` prefix they disagree: an audit counted "three
words after `rung_`", while a builder said that `rung_level_two` and
`rung_compact_auto` "keep three words". A name whose count depends on that
reading is listed as open, not filed.

12.2.2.6 Python imports stand as `import a, b, c` in alphabetical order, on
one line or on the fewest lines that stay within 79 columns. `from` is used
only for `collections.abc` and `typing`, each on one line with its names in
alphabetical order, and for `from i18n import i18n`, the maintainer's
decision, which the project rules do not yet carry. Constants are named
`_UPPER_NAME` and stand at the top of their file, after the imports. A
TypeScript module has one frozen `constants` object, and no constant
outside it.

12.2.2.7 Comments: one comment line per construct, never two consecutive
comment lines. A file's header comment at its top may run over several
lines, and in a PowerShell file it may be a `<# #>` block, the only place
such a block is allowed. `comments_check` refuses a `;` outside a code
span. Comments and strings over 79 columns that the formatter cannot wrap
are listed as open, not wrapped by hand (section 6).

12.2.2.8 No `isinstance` or `is None` branch whose only purpose is to
narrow a type: `cast` stands in its place. A check that refuses bad input
and raises is not such a branch. `i18n` is always called with a literal
name at the call site.

12.2.2.9 Synchronization: no `await`, `.then(`, `new Promise`, `Atomics` or
`SharedArrayBuffer`, with any white space within or around it, in a
`ts/*.ts` other than `queue.ts`, `wire.ts`, `http.ts`, `media.ts` and
`boot.ts`: the task manager is the only synchronization tool, and no
promise, lock, shared buffer or `Atomics` exists outside it and the ports
it owns, but for the initialization in `boot.ts`. A token inside a comment
or a string literal is not a hit, as the audit blanks both; a name that
holds a token is a hit, which is why `awaited` was renamed `pending`;
`async` is not swept (the default D29, `async` not added to the
synchronization audit, section 4.4). The sweep catches the spaced forms the
audit's literal match misses (11.2.6.2).

12.2.3 Decided.

12.2.3.1 A bounded retry by default: `devtools.page_open` waits, with a
bound, on exactly `net::ERR_CONNECTION_REFUSED`, the wait the old
screenshot tool had (the default D15, section 4.4); an earlier audit's
note on that sleep loop stays open (11.10.5.3).
`devtools.profile_remove` retries only EACCES, EBUSY, ENOTEMPTY and EPERM
under a bound, then raises `TimeoutError` with the last `OSError` as its
context, the errno set its writer's choice, unmeasured. `page_close`
ignores the result of `Target.closeTarget`, as the earlier job's
instructions had it.

12.2.3.2 Not swallowed: a class or module fixture error ending the run
with `Bail out! failfast` (11.1.4.7); the alarm raising an error that
unittest records as a `not ok` (11.1.3.19); a failure written always,
before the error line and exit 1 of the server.

12.2.3.3 Values kept: the 120 s lengths already written, as defaults;
`_STRESS_ROUNDS`, 8, a count chosen by its writer; the step script of
`ts/test_substrate.ts`, a measured SHA-256 vector that is never run, which
keeps the text `engine.log(1, ...)`; the hello's line bound of 10 MiB
before the settings are known (the default D24, section 4.4); `chunk_bytes`
and `srv_buf_size` at 1 MiB, approved by the maintainer.

12.2.3.4 Names kept: `page_build.main()` and `test_all.suites_run()`, public
names of an accepted addition; the PowerShell names in their files' style
(11.2.4.12).

12.2.3.5 Imports inside functions, after `sys.pycache_prefix` is set, so
bytecode goes to `build/` (11.1.4.20).

12.2.3.6 A hit that an area's Decided list (sections 11.1 to 11.22) or
section 4 holds is listed as accepted with it, not filed; one that an
area's Open list holds is listed as open.

12.2.4 Open.

12.2.4.1 `_cache_prune` of `python/substrate.py` skips only
`FileNotFoundError`, as the earlier job's instructions prescribed; a later
review called it a swallowed error. A decision that breaks a project rule
is open, not a finding (section 5).

12.2.4.2 `python/mcp.py` turns a tool's exception into a -32603 response
and keeps running: a recorded decision that a later review reports as
breaking fail fast; open on the same ground.

12.2.4.3 `python/mcp_stdio.py` sets no `sys.pycache_prefix`: a) `# noqa:
E402`; b) a launcher.

12.2.4.4 `from i18n import i18n` is "decided by the maintainer and not yet
in the rules file, which is the maintainer's to edit: report the gap, don't
edit the rules". The sweep reports the gap.

12.2.4.5 The count of words after `rung_` (12.2.2.5).

12.2.4.6 Lines over 79 columns that the formatter cannot wrap (12.2.2.7).

12.2.4.7 Without `--failfast`, a `normal-test` run records every failing
test of a module before it stops, against "first failure only"
(11.1.5.9).

12.2.5 Candidates, recorded hits, each checked against the code.

12.2.5.1 Errors: `Remove-Item ... -ErrorAction SilentlyContinue` in
`powershell/test_powershell.ps1`; the `Import-LocalizedData` retry and a
failed `wsl --update` that only warns, and the 15 s `Start-Sleep` polls,
each recorded as reading like a fallback (11.3.6.4); the stub server of
`python/test_browser.py` swallowing an unexpected path, and its
`tap_check` tallying failures; in TypeScript, `thrown_stack` returning "",
`overlay_show` skipping a missing stop function, `media.ts`'s `stack:
error.stack`, `close_take` skipping an unset receiver, and the unreachable
`queue.step_empty`, `wire.read_none` and `wire.frames_none`; in Python, the
branches for cases that cannot happen `option_unfinished`, `not_prepared`,
`transaction_none` and nine `not_registered` checks; `stall_loop`'s
unreachable `loop_run` raising a plain `RuntimeError`.

12.2.5.2 Values: the console view's `columns: 120`, a constant whose
comment must say its writer chose it (its rows are fitted to the space, as
decided); tty 1's `columns: 80, rows: 24`, carried from the old page; the
image download timer, which reuses `provider.timeout_seconds`;
`_WIRE_SECONDS` and `_DRAIN_SECONDS` of `python/test_browser.py`, 120 each,
copied from `ts/wire.ts`; `rung_long` printing an unmeasured 0.0 ms;
`hello_line_max` commented "the maintainer's size" where the coordinator
set it.

12.2.5.3 Names: older names of three words, such as `shell_double_scan`,
`rung_ui_put_largest`, `rung_test_engine_start` and `_main_loop_write`;
one word probe names of `python/test_browser.py` (`pattern`, `thrown`,
`hit`, `view`, `views`, `viewport`, `canvas`, `fault`, `outcome`, `rows`,
`focus`, `permit`, `history`, `widths`, `sink`, `summary`, `receiver`) and
the one and three word names of its probe kit and `rung_refused_role`; the
TypeScript names `Owed`, `Leaf`, `Entry`, `Payload` and `Options`.

12.2.5.4 Imports and constants: `_STRINGS` after a function in
`python/i18n.py`; `_KEY_ENTER`, `_KEY_INTERRUPT`, `_EXTRAS_NONE` and
`_EXTRAS_KEY` after their classes in `python/test_browser.py`; the `from
typing` names of `python/devtools.py` out of order; module level constants
outside `constants` on the TypeScript AI side; the order of the two `from`
lines, recorded as differing between files.

12.2.5.5 Comments: four comments that hold a `;` outside a code span,
three in `python/test_browser.py` (above `rung_early`, `ui_request` and
`rung_ui_put_largest`) and one in `python/stall_loop.py` (above
`loop_run`), severity 1, as each stops `test_posix.py` once the banner
question is answered; comment characters outside backticks in
`python/test_browser.py`; two line comments in `API/ts/unittest.d.ts` and
in the TAP stub, recorded and not edited, a proposed edit for the
maintainer.

12.2.5.6 Synchronization: the spaced forms and `x.await` of 11.2.6.2.

12.2.6 Requests go to the owner of each file (sections 11.1 to 11.22), one
per owner per rule, every hit listed; to the coordinator for a file no
entry lists. Edits of `API/` and `README.md` are proposed for the
maintainer.

12.3 Task 1.3, the line contract.

12.3.1 Checks. Read only: every row of `API/ts/lines.d.ts`, its type,
lane, direction, blob count, payload and reply, against the Python handler
and the TypeScript handlers registered for it and against every line built
with its `t`: field names and types, blob counts, `k`, reply shapes,
`since` and `seq`, and the name form in debug mode; the owner tables of the
task manager; the `hello` exchange on both sides; the `error` line; the
`mcp` line; the internal line types. The files: the stub; on the server
`python/engine_*.py`, `python/dispatch.py`, `python/mcp.py`,
`python/main_loop.py`, `python/bootstrap.py`, `python/echo_loop.py`; in
the page every `ts/*.ts` that registers a handler, submits, notifies,
forwards or builds a line: `queue.ts`, `dispatch.ts`, `wire.ts`,
`http.ts`, `substrate.ts`, `mcp.ts`, `provider.ts`, `provider_script.ts`,
`agent.ts`, `tools_browser.ts`, `script.ts`, `worker_ai.ts`, `boot.ts`,
`page.ts`, `media.ts`, `console_view.ts`, `overlay.ts`, `verbose.ts`,
`settings.ts`, `error_overlay.ts`, `test_all.ts`, `test_hook.ts`.

12.3.2 Expected. `API/ts/lines.d.ts` remains and holds the rows and their
payload interfaces; what follows is what the stub does not say.

12.3.2.1 The stub's own terms: "push" is a notification the receiver never
answers; "fwd" marks a modifying substrate operation the browser forwards
to the server after its commit, carrying `since`, the same types travelling
on the ui-ai lane without `since` as tasks the UI submits to the AI thread;
"wake" marks a line the task manager enqueues on its own thread when every
reply a sleeping task waited for has arrived.

12.3.2.2 Request, reply, push. A line with `i` gets exactly one line with
`r` equal to it, from the peer, on the same port; its `t` is the request's
`t` or `error`. A line without `i` is a notification. An unknown `r` is a
hard error, a known `r` arriving on another port included. One port is one
FIFO each way, and a handler runs to completion before the next line on
that port is dispatched.

12.3.2.3 Ids. On the server ids restart at 1 per port per process lifetime
(`dispatch.id_next`). In the page they are D2, the default that request ids
are one counter per thread queue, not per port, from 1 for the life of the
thread; no TypeScript module calls `dispatch.id_next`. A reply must arrive
on the port its request went to.

12.3.2.4 Replies. A handler returns a finished reply line built with
`dispatch.reply_make(request, payload, blobs)`, a sleep, or nothing. A
reply carries `t` and `r` and no `v` or `k`, its `r` in the reply header's
own name form; nothing checks that its form or `t` matches the request's.
A wake line carries no `i`; a wake handler that owes a reply builds it from
the original request kept in its state; every request a handler run submits
is named in that run's sleep. Python refuses a reply to a notification;
TypeScript accepts a reply that carries `r` from a wake handler, which has
no `i`. Replies on the http lane have `t` `http.request`.

12.3.2.5 The name form. Headers use full names in debug mode and short
names otherwise; in the page one `names_full()` in the worker chooses the
form (D27, the default that the line name form is chosen by one
`names_full()` in the worker), which `Store.forward_set(fn, full)` and
`mcp.Client(..., full?)` take. Python's `error_make` follows the request's
name form.

12.3.2.6 `since` and `seq`. Each forwarded modifying operation, `kv.put`,
`kv.delete`, `doc.put`, `db.create`, `db.drop`, `turn.append`,
`turn.compact` and every modifying `sql.run`, carries `since`, the
browser's `seq` before the operation, on the wire and not on the ui-ai
lane. The server refuses it with `error` when `since` is not its own
`seq`, runs the same operation otherwise, and replies with its new `seq`.
The browser checks that a reply's `seq` is `since` plus 1, the check
skipped for `db.create` and `db.drop`. By D1, the default that a new
database starts at `seq` 0, `db.create` carries `since` 0 and `db.drop` the
database's `seq`. A refused push, or a reply whose `seq` is not the
browser's, is a desync and a fault.

12.3.2.7 Blobs and `k`. The blob counts are the stub's. For `kv.get`,
`kv.put` and `kv.delete` the ref is header 0's `k`. `kv.put`'s value is
blob 1; `kv.get`'s reply is `{size, sha256}` with the value as blob 1;
`db.snapshot`'s reply is `{sha256, seq}` with the database file as blob 1,
one blob, whose SHA-256 the receiver checks against `sha256` before it
restores; `source.put`'s blob 1 is the file written as `main_loop/<name>`,
and the line is refused without it; `media.store`'s blob 1 is the image,
`media.fetch`'s reply carries the bytes as blob 1; `console.input` and
`console.output` carry one message of ttyd's own protocol as blob 1. Every
line is within `line_max` and every message's blobs within `blob_max`
(11.4).

12.3.2.8 Payload facts the records fix. `verbose.put` lines carry `at` and
`text` only, are forwarded whenever `debug` is true, are refused by the
server when `debug` is false (`engine_verbose.debug_off`), and leave the UI
in batches split into lines below `line_max`. `tap.line` is `{language,
text}`, `language` `python` or `typescript`, one line per TAP line,
appended on the server to `<root>/tap/<language>.tap`. `settings.put` is a
request from the AI thread to the server: each thread's sender notifies
`settings.put` to `ai`, which submits it, because Python refuses a reply to
a notification. `console.close` closes the console port and replies
Empty. The `db.chunk` line is withdrawn.

12.3.2.9 The owner tables. Each thread has one `TaskQueue(thread, owners,
synchronous)`. Its owner table maps a type prefix to the owner that handles
it, the longest prefix winning; the owners are the names of
`queue.ThreadName`: `ui`, `ai`, `server`, `http`, `media`, `console`,
`dom`. A line whose owner is another thread is posted to that owner's port
unchanged, as the decoded object, and that port encodes it again. Each
table maps the types of the stub's lane table to the owner its
"from -> to" column names, and the thread's own types to itself.

12.3.2.10 On the AI thread the table maps `verbose.` to `server`, so a
`verbose.put` from the UI reaches the server through the AI worker with
nothing added, the type itself being the forwarding instruction; and, in
the words of `API/ts/queue.d.ts`, "`"kv."` to `"server"` on the AI thread
for the forwarded form, and so on". On
the UI thread it maps `kv.`, `doc.`, `db.`, `turn.` and `sql.` to `ai`, and
`media.` to `ui`, whose handlers pass a copy without `i` to the `media`
port with an explicit owner and reply from the wake with
`reply_make(original, payload, blobs)`.

12.3.2.11 Because the UI's `kv.*` tasks run on the AI thread while the
AI's forwarded `kv.*` lines go to the server, and `mcp` has two owners on
the AI thread, `task_submit(line, owner?)` and `line_notify(line, owner?)`
take an explicit owner, which posts straight to that owner's port and skips
the table. There is no owner table entry for `mcp`; `mcp.Client`, the
agent's provider owner and the tools name their owner. A type matching no
prefix raises `queue.owner_missing`; wakes skip the table; a line arriving
on the thread's own loopback port is dispatched there without a lookup;
`line_forward` of a line carrying `i` or `r` raises `queue.forward_marked`.
The test hooks route `tap.` to `ai` on the UI thread and to `server` in the
worker.

12.3.2.12 The `hello` exchange, server side. `bootstrap.py` owns it whole;
the main loop never sees it. `bootstrap` calls `loop_prepare(root)` once,
before `hello`, so that seeding happens before the first `seq` is sent,
then `loop_run(read_fd, write_fd, root)`. The server puts its pty in raw
mode with `tty.setraw` before it writes anything. `hello` is the server's
request with `i` 1: `bootstrap`, `sha256`, `pid`, `root`, `settings` as
loaded, `seq` per server database in `db_list()` order with `_verbose`
left out, `provider_key` always, and `provider_info` last, only when
`provider.scripted` is false. The server reads the reply with the settings
it sent, checks it by its fields in either name form, refuses a reply header
holding anything but the type and the reply (an explicit `b`, `v`, `i` or
`k`), and accepts a full name reply to a short `hello`.

12.3.2.13 The `hello` exchange, page side. The client sends nothing until
`hello` arrives. The page decodes `hello` with no blob and a line of at
most 10485760 bytes, and builds its wire limits after `settings_set` (D24,
the default that the wire limits are built after `settings_set` and that
`hello` is decoded under that line bound with no blobs). The worker posts
`settings.set` to the UI, answers `hello` with an empty reply, then posts
`boot.hello`. Then, as tasks: for each engine database and the metaverse,
compare `seq` and replace the browser's file from the server where they
differ, only the databases the browser holds being replaced and the others
staying unloaded until `db_load`; read `/metaverse/world`, then
`/$world/scene`; fetch the media the browser lacks; `render`. An `error`
line before `hello` shows the server's
message and stack (`wire.error_first`), and the port then shuts. A second
`hello`, after `system.restart`, is a fault ending in Reload (D9, the
default that a second `hello` after `system.restart` is such a fault).

12.3.2.14 The `error` line, `ErrorLine {message, stack}`. On the server a
handler that raises produces one `error` line, with `r` when the request
had `i`, `message` and `stack` as text, written and flushed before exit 1;
`dispatch.error_make` builds it (11.5); `bootstrap.py` builds its own with
`jslb` alone, in short names, in debug mode too; end of input inside a
message writes `error` and exits 1. In the page an `error` line arriving on
any port is a fault, `queue.error_line` with the remote message and stack,
which ends in the `<pre>` screen and Reload; a close with no `error` line is
the fault "connection closed with code N and no error line". The page's own
faults travel as `fault` lines, `{thread, message, stack}`, on the ui-ai
lane; the worker's `error_overlay` posts them with `self.postMessage`, so
the UI to AI lane is a `MessageChannel` of its own.

12.3.2.15 The `mcp` line. Its payload is the JSON-RPC message itself,
`mcp.Message`. On the wire it runs between the AI worker's `mcp.Client`
and the server's `mcp.Server`, through `engine_mcp`, which passes
`jslb.payload_of(line)` to `message_handle`, replies with the response as
the payload and sends nothing on `None`; on the local lane it runs between
the agent and the browser's MCP server, whose tool that sleeps keeps the
original `mcp` line so that the wake builds the reply with `reply_make`.
The client sends each message as an `mcp` line's payload and reads the
response from the wake. The tools form one flat list under the prefixes
`browser.` and `server.`; dotted names pass to the provider unmapped (D28,
the default that dotted tool names go to the provider unmapped, to be
checked at the first real provider run). Stdio, `mcp_stdio.py`, is the
third transport.

12.3.2.16 Internal line types, in no row of the stub, recorded and so
accepted: `replicate.next` and `replicate.done`, replication run as page
tasks over `Store.forward_set(fn)`, a departure that stands for the review
and awaits the maintainer's acceptance (4.5.17); the wakes
`ui.console_reply`, whose
state is `null`, and `ui.console_closed`; and from the AI worker's start
chain and the page, as the record writes them, "`worker.start`,
`.restored`, `.loaded`, `.initialized`, `.listed`, `.fetched`, `.stored`,
`.rendered`, `.console_opened`, `.settings_put`, `.tests`,
`ui.media_reply`, `ui.control_key`", the suffixes being names under
`worker.`. The wakes `tools.*_reply`, a tool's own, are a row of the stub.
Any other type in no row and no record is a finding.

12.3.3 Decided, not a finding.

12.3.3.1 The `console.open` reply carries `token`, fetched from `/token`,
where the stub's row says Empty (D23, the default that the `console.open`
reply carries `token`); `DbName` has no `since` though `db.create` and
`db.drop` carry it (D1). Both are listed as stub edits not applied, since
neither is a decision of the maintainer.

12.3.3.2 `replicate.*` and `ui.console_reply` stay out of the stub: API
additions waiting for the maintainer (4.5), kept by D11, the default that
the additions and departures stay.

12.3.3.3 The stub's `HttpResponse` comment names `http.response`, while a
reply on the http lane has `t` `http.request`, the request's own type: a
rule of section 3, whose stub edit was not applied.

12.3.3.4 Applied to the stub already, so matching it is right: `Hello`
with `provider_info` and `ProviderInfo`; `VerboseLine` without `level`;
`db.snapshot` as one blob.

12.3.3.5 The explicit owner of 12.3.2.11 is the coordinator's decision,
which resolved the double ownership of `kv.*` and `mcp`.

12.3.3.6 An arriving `error` line is a fault; delivering it as a reply in
the wake, or dispatching it to an `error` handler, were the alternatives
not taken. `line_forward` refuses a line with `i` or `r`, since id
translation would be the design for request forwarding.

12.3.3.7 Wake headers use short names in every mode; the console view
writes full names always, the console being debug only; `bootstrap.py`'s
`error` line uses short names in debug mode too, as the coordinator
ordered; Python's `error_make` follows the request's name form, always
short and full when `debug` having been rejected; the form of `hello` in
debug mode is the full one, Unconfirmed.

12.3.3.8 The `settings.put` relay of 12.3.2.8 is built as recorded. The
`typescript.tap` file holds two TAP documents, the UI's then the worker's;
a third `language` value, which would change `TapLine`, was rejected.

12.3.3.9 `console.close` has a handler, and a sender,
`ConsoleView.close_request`, that no UI action calls: approved by the
maintainer. After `console.exit` the view returns to idle, and ctrl-0 sends
`console.open` again.

12.3.3.10 The UI holds no SQLite and submits its modifications as tasks
to the AI worker's database, which forwards them (Unconfirmed). `media.fetch`
stays beside `b64_json` (Unconfirmed). Explicit route headers, a sleeping
task on the server and line types versioned by handler are built later by
design (4.2).

12.3.3.11 The wire test accepts the second `hello` of `system.restart`,
which the page treats as a fault (12.3.2.13).

12.3.3.12 The `console.read` reply holds the output received after the
read was posted, up to and including the message that completes `until`,
where the stub's comment says the output received "since the last read":
its writer followed the plan, whose port answers with the output once the
prompt returns, and recorded the stub's comment as disagreeing. The stub's
comment is a proposed edit, not a finding.

12.3.4 Open, for the maintainer. None belongs to the line contract alone;
the question of 11.5.5.2, a tool's exception as a -32603 response, bears on
the `mcp` line's error responses in both languages.

12.3.5 Candidates.

12.3.5.1 The stub calls `mcp` a push while both sides send requests on it
with `i` and answer them with `r`. Where the code is right, the finding is
a proposed edit of the two `mcp` rows of `API/ts/lines.d.ts` (6).

12.3.5.2 `HttpResponse`'s comment promises `data` as blob 1 "when the
request asked for `binary`", but `HttpRequest` has no `binary` field and the
lane table says 0 blobs; it is not built. The writer recorded the design
should image downloads move to the http port: the field, an `arrayBuffer()`
read and a blob. Where the code is right, a proposed edit of the stub.

12.3.5.3 `db.snapshot` and `verbose.tail` lines, both built by
`ts/tools_browser.ts` (task 1.27), are in short names always, where
debug mode wants full names.

12.3.5.4 `ConsolePort.names_full()` is a second reader of the name form,
against D27's one `names_full()` in the worker (task 1.23).

12.3.5.5 `bootstrap.py`'s `error` line on an argument error is written
before raw mode, where the server writes nothing before it (task 1.16).

12.3.5.6 The comment of `hello_line_max` in `ts/wire.ts` calls it "the
maintainer's size", though the coordinator set it (task 1.23).

12.3.5.7 `API/ts/dispatch.d.ts` says a handler "returns the reply without
a header", against the rule that a handler returns a finished reply line;
where the code follows the rule, a proposed edit of that stub (task 1.22).

12.3.5.8 Each internal type the code holds that 12.3.2.16 does not name.

12.3.6 Requests go to: the server's handlers, task 1.15; `dispatch.py` and
`mcp.py`, task 1.13; `main_loop.py`, `bootstrap.py` and `echo_loop.py`,
task 1.16; `queue.ts` and `dispatch.ts`, task 1.22; `wire.ts` and
`http.ts`, task 1.23; `substrate.ts`, task 1.24; `mcp.ts`, `provider.ts`
and `provider_script.ts`, task 1.25; `agent.ts` and `script.ts`, task 1.26;
`tools_browser.ts`, task 1.27; `worker_ai.ts` and `boot.ts`, task 1.28;
`page.ts`, task 1.29; `media.ts` and `console_view.ts`, task 1.30;
`verbose.ts`, `settings.ts`, `overlay.ts` and `error_overlay.ts`, task
1.21; `test_all.ts` and `test_hook.ts`, task 1.20. A change of
`API/ts/lines.d.ts` is a proposed edit in the report, never an edit.

12.4 Task 1.4, the twins.

12.4.1 Checks. Read only: what 12.4.2 says behaves the same in Python and
in TypeScript, pair by pair, other than JSLB, which task 1.12 owns whole
(11.4). The pairs and their stubs: `python/substrate.py` and
`ts/substrate.ts` (`API/python/substrate.pyi`, `API/ts/substrate.d.ts`,
`API/sql/*.sql`); `python/dispatch.py` and `ts/dispatch.ts`;
`python/mcp.py` and `ts/mcp.ts`; `python/settings.py` and
`ts/settings.ts` (`API/settings.json`, `API/ts/settings.d.ts`);
`python/verbose.py` and `ts/verbose.ts`; `python/i18n.py` and `ts/i18n.ts`;
`python/tap_producer.py` and `ts/tap_producer.ts`; each with its test
module.

12.4.2 Expected, pair by pair.

12.4.2.1 The substrate. `ts/substrate.ts` is `Store` over sqlite3.wasm with
the same API as Python's, plus the emitting side of replication; the stage
6 suite is the stage 3 suite ported, with identical counts but for what
has no meaning on the SAH pool (task 1.8 checks that port).

12.4.2.2 `ref_split`: a Key-Value-Ref is `/$db/$key`, external, or
`$key`, internal; `$db` is a C identifier, `$key` any non empty text that
may contain `/`. A Document-Ref is a Key-Value-Ref whose key is
`$id/$version`, the version an integer literal, `0|[1-9][0-9]*`, and the
last segment. `ref_split` keeps white space in keys; only a document's
reference strings exclude it (D18, the default that a reference string's
key part holds no white space), and the TypeScript class of white space is
exactly the code points of Python's `str.isspace`.

12.4.2.3 `doc_encode` and `doc_decode`: header 0 is the document header,
`t` the document type and `v` its format version, defaults omitted;
headers 1 on are reference strings, each matching `/<C identifier>/<non
empty>` (internal refs stay in the body); `{"$ref": n}` in the body names
header n. `doc_encode` moves every reference string into the headers and
shares equal strings, numbering them by first occurrence, depth first, in
insertion order; `doc_decode` puts them back, requires every header from 1
on to be a reference string, and raises on a malformed header or `$ref`
index. The round trip is identical. `doc_put` checks the body with
`doc_decode` and stores it as given.

12.4.2.4 Canonical JSON follows `jslb`'s key rules at every level and
refuses integers beyond plus or minus 2^53, but for the difference of
12.4.3.3.

12.4.2.5 `seq`: `_meta` holds it, incremented in the same transaction as
every modifying operation; a new database starts at 0 and `db_create`
leaves it 0 (D1, the default that a new database starts at `seq` 0); it
survives a reopen; `seq_get(db)` reads it.

12.4.2.6 Overflow: a KV value over `overflow_bytes` lives in the cache under
its SHA-256 with `data` NULL; a value of exactly `overflow_bytes` stays in
the row; the file comes first, then the row. `Store.kv_put(ref, data)`
takes bytes; a string is a cache file path in Python and a cache handle in
TypeScript, never text.

12.4.2.7 `turn_compact(scene, through, summary)` replaces turns 1 to
`through` with one summary row of role `system` at `n` 1, its content
`{"role":"system","content":summary}`; `through` below 1 raises, a
compaction that deletes nothing raises, gaps in `n` are kept and the next
append is the highest `n` plus 1. The automatic compaction runs in the
browser's `Store.turn_append` alone: a `user` turn on a scene holding
`turn_compact_turns` turns or more first compacts turns 1 to the last in
the same transaction, forwarded as its own `turn.compact` before the
`turn.append`, its summary the one `i18n` text `substrate.turns_compacted`
naming the turns compacted and the count that reached the threshold. The
server applies both lines and never compacts by itself.

12.4.2.8 `operation_apply` applies each forwarded line by its type and
keywords: `kv.put` `k` and `data`; `kv.delete` `k`; `doc.put` `db`, `id`,
`body`; `db.create` `db`, `since` 0; `db.drop` `db`, `since` its `seq`;
`turn.append` `scene`, `role`, `content`; `turn.compact` `scene`,
`through`, `summary`; `sql.run` `db` and `statements`, each statement
exactly `sql` and `params`. A stale `since` is refused with the text
"<type>: since S is not seq Q of <db>". The two copies are deterministic as
long as the statements are.

12.4.2.9 The dispatchers. Both register a handler per type and version, a
second registration of a pair refused; both refuse an unknown pair; both
set `r` on a reply in the reply header's own name form, overwriting a
wrong `r`, and write no `v` or `k` on replies; neither checks a reply's
form or `t`; the registry key is the exact pair; both build the one `error`
line with `message`, `stack` and `r` when the request had `i`.

12.4.2.10 MCP. `mcp.ts` answers `initialize`, `ping`, `tools/list` and
`tools/call` with the shapes, codes and texts of `python/mcp.py`: -32600,
-32601, -32602, and -32603 with `data.stack`; revision `2025-06-18`
pinned as a constant in both; capability `tools` only. The reply checks of
the TypeScript client are Python's; absent `arguments` mean `{}`; both
clients raise on an error response (`mcp.reply_error` in TypeScript,
`RpcError` in Python). Six of TypeScript's `mcp.` names reuse Python's
texts word for word.

12.4.2.11 Settings. One key set and one shape: `settings.json`,
`API/settings.json`, the check of `settings.py` and the `Settings`
interface of `ts/settings.ts` and `API/ts/settings.d.ts` hold the same
keys, `provider` holding `scripted` and `timeout_seconds` only. Python
loads and checks the file (11.5); TypeScript's `settings_set(value)` stores
what `hello` carried once per thread, deep frozen unless `debug` is true, a
second call throwing; `settings_get(id)` reads by id, nested ids joined by
`.`, and throws before `settings_set` and on an unknown id
(`settings.unknown_id`); outside debug mode the frozen object refuses a
write; `settings_put(id, value)` in debug mode only changes the live value
and has the registered sender submit `settings.put`, which rewrites the
root's file for the next `hello`.

12.4.2.12 Verbose. In both languages `log(text)` takes no level and keeps
every line in a ring of `verbose_ring` lines, and `history_get(count)`
returns the ring's last `count` lines, oldest first. Python also writes
each line to `_verbose` before it returns (11.5). TypeScript hands each
line to the thread's one sink, `sink_set(fn)`, which is the thread's queue
batching the lines into `verbose.put` when `debug` is true; the ring takes
the line before the sink is called, the sink gets only lines written after
it is set, and a second `sink_set` throws `verbose.sink_twice`. A line is
`{at, text}`, milliseconds since the epoch and its text, in both. Neither
the server nor the page has a verbose level.

12.4.2.13 `i18n`. One file, `i18n/en-US.json`, which Python reads at
import and the build substitutes into `ui_strings.ts` unmodified; stage 0
checks that both read the same names. One placeholder rule: `{n}` with `n`
matching `0|[1-9][0-9]*`, ASCII only, so `{01}` is literal text; the set of
indices used must equal 0 to the argument count minus 1; one substitution
pass, which the Python test tells from two. A missing name raises in both,
a placeholder count unlike the arguments raises in both; TypeScript also
refuses inherited names.

12.4.2.14 The TAP producers. Identical TAP text for the same outcomes:
one passing, one failing, one raising and one skipped method yield the same
TAP in both languages as one subtest block. One plan per language per run;
each module's suite is one block indented four spaces with its own plan,
then a parent `ok N - <module>` line. The line grammar is D12, the default
that the block plan `    1..N` comes first, that no `# Subtest` line is
written, that method names are bare, and that a failfast block is plan,
points, diagnostics, `Bail out! failfast`. Both follow tappy's names, the
TypeScript ones inside the namespace `tap_producer`: `TAPTestRunner` with
`set_stream` and the failfast argument, and `Tracker` with `set_plan`,
`add_ok`, `add_not_ok`, `add_skip` and `generate_tap_reports`. An expected
failure is `not ok N - x # TODO expected failure`, counted as passed; an
unexpected success is `not ok` with `unexpected success`. Block names are
the test module names; TAP messages are plain English, not `i18n`.

12.4.3 Decided, not a finding: each accepted difference.

12.4.3.1 Substrate, SQL: TypeScript checks the parameter count with
`prepare` (`substrate.params_count`), catches several statements in one
text after running them and rolls back (`substrate.statement_many`), and
throws on empty SQL, which Python accepts.

12.4.3.2 Substrate, numbers and keys: a number past 2^53 gives
`substrate.integer_range` in TypeScript; `substrate.key_refused` has no
JavaScript case; a top level key "12" is `header_normal` in TypeScript and
`key_digits` in Python.

12.4.3.3 Substrate, doubles: Python stores doubles above 2^53, which the
TypeScript store refuses with `substrate.integer_range`, whose text says
integer; approved by the maintainer. Whether an AI script storing 1e16
should fault was once left as the maintainer's call, and that approval
decides it (4.8.2); the TypeScript `json_canonical` runs only on data made
in the browser, so it was left unchanged.

12.4.3.4 Substrate, the pool: the SAH pool has no WAL, so only
`foreign_keys = ON` is set in TypeScript, and the test of a WAL file left
by a kill is not ported; approved by the maintainer.

12.4.3.5 Substrate, documents: the header numbering of nested objects
with integer like keys may differ in TypeScript, as the contract the
coordinator carried to the TypeScript writer foresaw.

12.4.3.6 Substrate, the API: TypeScript's departures and additions,
`constructor(sqlite3, pool, cache, root, overflow_bytes, compact_turns)`,
`forward_set(fn, full)`, `handlers_register(register)`, `seq_get`,
`forward_done`, `db_stats`, `db_compact`, `db_unload`, `db_load`,
`start_open` and `CacheFiles`, stand as additions waiting for the
maintainer (4.5); `kv_held`, `cache_fill` and `cache_evict` were accepted
by the maintainer and are in the stub (4.5.24). The database
administration is the browser's; the server substrate has no measurement.
The browser's cache is a fixed set of files held open, where Python's is a
directory.

12.4.3.7 Dispatch: TypeScript's `stack` is `Error.stack`, with no `cause`
chain, where Python's includes chained causes; an `Error` without a stack
throws `dispatch.stack_missing`; TypeScript checks header kinds with
`dispatch.type_invalid` and `dispatch.id_invalid`. Python checks `v` and
`i` before the lookup with its own names, `dispatch.version_refused` and
`dispatch.id_refused`, where TypeScript looks up first, because the rules
differ and one name holds one text.

12.4.3.8 Dispatch, replies: a TypeScript handler returns a finished reply
line built with `reply_make`, and a payload only return throws
`dispatch.reply_headerless`; Python's rule that a notification's handler
returning a reply raises is relaxed in TypeScript for wakes, which carry no
`i`. TypeScript has `task_sleep` and `Sleep`; a sleeping task on the server
is built later by design (4.2).

12.4.3.9 Dispatch, ids: Python's `id_next(port)` counts per port;
TypeScript's ids are one counter per thread queue (D2, the default that
request ids are one counter per thread queue), and no TypeScript module
calls `dispatch.id_next`.

12.4.3.10 MCP: TypeScript copies `isError` only when the tool set it,
where Python always writes it; the TypeScript client refuses another
protocol revision with `mcp.version_refused`, where Python's does not.
TypeScript's additions for sleeping tools and the queue, `WakeFn`,
`Server.wake_register`, `Server.line_handle`, `Client.initialized_send`,
`Client.tools_read`, `Client.tools_cached`, `ClientSet.result_of`, and its
departures, `Client(name, version, tasks, owner, full?)` and a `constants`
object of the protocol's names and codes, stand (4.5). The servers are
named `xsjs-server` in Python and `xsjs-browser` in TypeScript.

12.4.3.11 Settings: TypeScript's additions `ValueStore`, `Sender`,
`sender_register` and the global `i18n_format` stand (4.5); the sender gets
the payload `{settings: <copy>}`, not a line, because `settings` comes
before `jslb` and `queue`, and the registrant builds and submits the line.
TypeScript does not validate values; a non debug `settings_set` freezes the
object passed in place; a sender that throws leaves the live value changed;
setting `debug` false in debug mode ends later puts.

12.4.3.12 Verbose: TypeScript's addition `verbose.LineRing` stands, and
Python's `log_open`, `log_close`, `lines_put` and `tail_get` (4.5). Only
Python has `exec`, the shell's runner, with the only levels left.

12.4.3.13 `i18n`: TypeScript reads `ui_strings.table`; Python raises
`KeyError` for a missing name and `ValueError` for a placeholder mismatch.

12.4.3.14 TAP: the TypeScript producer is exercised on the same ways a run
can fail but `subTest` and the class and module fixtures, which its harness
lacks; only Python ends a run on a fixture error with `Bail out! failfast`.
The Python additions `module_run(module, load)` and `run_end()`,
`set_stream` per instance taking a line callback, and `Tracker(write)`
stand; TypeScript adds `report_html`. tappy's names are recalled from its
documentation, Unconfirmed.

12.4.3.15 TAP, the stream: TypeScript writes two TAP documents to
`typescript.tap`, the UI's then the worker's, each with its own plan,
where Python writes one plan per run (11.12.4.1); both producers give the
same text for the same outcomes within a document.

12.4.4 Open, for the maintainer.

12.4.4.1 A forwarded `turn.append` applied by the TypeScript
`operation_apply` goes through the private `#turn_add` and never compacts,
so that one forwarded line cannot compact twice, against the order that
nothing else in the store changes; its writer's options are no longer on
record, and the maintainer has not approved it.

12.4.4.2 TypeScript's ring reads `verbose_ring` from the first line, so a
line written before `settings_set` throws, where Python's log refuses any
line before `log_open`; the question left to the maintainer is whether such
a line is ever wanted.

12.4.4.3 `engine_turn` builds canonical JSON with `json.dumps` and lacks
the substrate's check that integers stay within 2^53, so its text can
differ from the substrate's in key order and in integers past 2^53; open,
with the alternatives its writer named (4.7.5).

12.4.4.4 A tool's exception as a -32603 response, in both languages
(11.5.5.2). In TypeScript a tool that submits a request and then throws
faults the queue with `queue.wait_missing`, and its own message is lost;
faulting directly, or converting only protocol errors, were the
alternatives recorded.

12.4.5 Candidates.

12.4.5.1 `ts/dispatch.ts` accepts the ids 0, -3 and 1.5 and a string `v`,
which Python refuses.

12.4.5.2 TypeScript's `i18n` formats its arguments with `String(arg)`,
which the writer recorded "differs from Python `str` for booleans, `null`
and floats"; no record decides it.

12.4.5.3 `mcp.reply_unknown`'s `{0}` is the line id in TypeScript and the
JSON-RPC id in Python, under one text.

12.4.5.4 TypeScript's `kv_check` never removes a live sink file,
"departing from Python's `test_file_moved`"; no record decides it.

12.4.5.5 Document versions past 2^53 lose precision in TypeScript.

12.4.5.6 `ts/test_mcp.ts` has no case left where `tools/list` keeps a
tool's `_meta`, where `python/test_mcp.py` keeps one by registering
`console_run` with its mark.

12.4.5.7 The two TAP producers give the same text for the same outcomes,
as the stage 0 proof of 12.4.2.14 states (with task 1.20).

12.4.6 Requests go to: the substrate, tasks 1.14 and 1.24; the
dispatchers, tasks 1.13 and 1.22; MCP, tasks 1.13 and 1.25; settings and
verbose, tasks 1.13 and 1.21; `i18n`, tasks 1.9 and 1.21; the TAP
producers, tasks 1.9 and 1.20; `engine_turn`, task 1.15. A request goes to
the side that differs from the expected form, and to both when both
differ; a shared `i18n` text goes to the owner of the Python module (6.5).

12.5 Tasks 1.5 to 1.7, the rungs of `python/test_browser.py`.

12.5.1 Checks.

12.5.1.1 Scope: the rungs of `python/test_browser.py`, each run through
`RungLog.rung_run(name, label, function)`, divided by the stage that opens
the rung's name, whatever root runs it. Task 1.5 reviews the rungs named
"stage 0:", "stage 4:", "stage 6:" and "stage 7:"; task 1.6 the rungs named
"stage 5:"; task 1.7 the rungs named "stage 8:". Each task reads the rung
functions of its stages, the probe text they send to the page and the
helpers only they call. It edits nothing.

12.5.1.2 Each rung is checked against the proofs its stage owes (12.5.2),
the decisions in force (12.5.3, section 4) and the project rules: it drives
what it claims through the real path; it checks what it states; it fails
first and loud, under a timer that names it; it holds no fake data; it
carries its label.

12.5.1.3 The harness is task 1.19's (11.11) and is not reviewed here: the
imports and constants, `RunContext`, `RungLog`, the roots and
`session_run`, `page_ready`, the stub server, `_PROBE_KIT`,
`BrowserDriver`, `tap_check`, the teardown. A harness point met while
reading a rung is not reported by tasks 1.5 to 1.7; 12.5.5.1.4 lists the
harness points already recorded, so that none is reported twice.

12.5.1.4 Files read beside the rungs: `python/devtools.py`,
`python/category.py`, `python/test_wire.py` (its public `replay_build`),
`python/substrate.py`, `python/echo_loop.py`, `python/stall_loop.py`, the
`ts/` code each probe reaches, and the stubs under `API/` for them.

12.5.1.5 Parts. Each of 12.5.2 to 12.5.5 has seven parts: .1 every stage,
.2 stage 0, .3 stage 4, .4 stage 5, .5 stage 6, .6 stage 7, .7 stage 8.
Task 1.5 reads parts .1, .2, .3, .5 and .6; task 1.6 parts .1 and .4; task
1.7 parts .1 and .7. The proofs a stage owes are the plan's stage proofs,
restated in its part of 12.5.2. The first paragraph of each stage's part
of 12.5.2 lists the rungs as the file has them on 2026-10-21, by root, for
finding them; that list states no expectation.

12.5.2 Expected.

12.5.2.1 Every stage.

12.5.2.1.1 The runner. `python3 python/test_browser.py [--smoke-test |
--normal-test]` builds `html/test.html` and the engine pages, each when the
first root that serves it starts, serves them through ttyd, runs the
TypeScript suites in headless Chrome, the `tap_producer` tests first in the
page's `ts/test_all.ts`, reads the `tap.line` stream from
`<root>/tap/typescript.tap`, checks it with `tap_consumer`, and saves a
PNG. The one JavaScript runner is a browser. It runs `build/ttyd/ttyd`, the
ttyd the install script built, and fails naming the install script when it
is missing. `python/test_all.py` runs it as one of its suites, given the
category, after the Python suites, the checks of `python/test_posix.py` and
`python/test_wire.py`.

12.5.2.1.2 Timers. Every rung and every browser test has a timer; a timer
expiring is a failure that names the rung. Every timer is a named constant
holding a sane default, its one line comment saying that its writer chose
it. The 120 s lengths already written stay as defaults. The provider
request waits `provider.timeout_seconds`; `console_run` waits its
`timeout_seconds` argument.

12.5.2.1.3 First failure only. Any error is a hard error, reported at once;
nothing collects or tallies failures; nothing in flight is retried. A timer
expiring, a close without an `error` line and a desync are faults like any
other.

12.5.2.1.4 No fake data. Every value a rung prints or compares is a
measurement or plain arithmetic on one. A count, size or input that a rung
chooses is a named constant whose comment says its writer chose it.

12.5.2.1.5 The two categories, under the maintainer's names: `smoke-test`,
the important suites that fit in 2 minutes in all, and `normal-test`, the
others. A `smoke-test` run runs the suites labelled `smoke-test`; a
`normal-test` run runs both labels. In this file the suite is the rung:
each rung is run by `RungLog.rung_run` under its own timer and printed on
its own line, and its label is an argument of that call. Every rung carries
one label, written beside it; there is no default label; a label other than
the two strings raises.

12.5.2.1.6 Roots and setup. A root of `session_run` carries a label too:
`smoke-test` when it holds a `smoke-test` rung, else `normal-test`.
`category.LabelBook` checks both directions as the runner reaches them and
raises, so a mislabel fails loud in the first run that reaches it; a
`normal-test` run reaches every one. A `smoke-test` run starts no ttyd and
no page for a root it runs nothing on. A `smoke-test` suite needs nothing
that a `normal-test` suite does. Every rung of a `normal-test` root is
`normal-test`. Setup is not a suite: a page build, a root's ttyd, the
browser and the stub server. Setup runs when a suite that needs it runs,
and a page is built when the first root that serves it starts.

12.5.2.1.7 The labels and their reasons. Each label is Unconfirmed until
the testing phase measures it, because nothing could be run when they were
written (class B).

12.5.2.1.7.1 S1, a unit suite: the page's TypeScript suites, the rung
"stage 0: typescript suites", and "stage 0: typescript suites in order",
which reads the documents the first one wrote. The page's TypeScript
modules carry the label of "stage 0: typescript suites", since no runner
can leave one module out unless the page reads the category.

12.5.2.1.7.2 S4, one real start of the engine page: the root "fresh",
whose one rung "stage 8: fresh root" proves the page load, `hello`, the
seeded Script and a first render with no fault.

12.5.2.1.7.3 So the `smoke-test` roots of this file are "suites" and
"fresh", and its `smoke-test` rungs are those three; every other rung is
`normal-test`.

12.5.2.1.7.4 N1, moves or allocates a blob of `blob_max`, 2147483391
bytes: "stage 5: blob_max round trip", "stage 5: blob_max plus one refused"
and "stage 5: decoder fault" (root probe); "stage 5: wire drain timer"
(root echo, 255 lines of 8 MiB); "stage 5: largest UI put" (root upload);
"stage 6: largest database within blob_max measured", `rung_blob_max`
(root largest).

12.5.2.1.7.5 N2, waits out a 120 s timer of `wire.ts` by design, the whole
limit of a `smoke-test` run: "stage 5: wire token timer" and "stage 5: wire
open timer" (probe); "stage 5: wire hello timer" (stalled); "stage 5: wire
drain timer" (echo).

12.5.2.1.7.6 N3, moves 128 MiB or more: "stage 5: echo 128 MiB from the
page" (echo); "stage 5: 128 MiB upload from the UI" (upload).

12.5.2.1.7.7 N4, needs what a `normal-test` rung or root leaves: the root
"second", which compares with the run that the root "first" recorded; the
rest of the root "upload", which reads the trace and the long task observer
that the largest put starts.

12.5.2.1.7.8 N5, a long scripted session: the root "stress", eight rounds
under a 600 s timer; the root "main", about forty rungs on one page, each
needing the state of those before it, so it runs whole or not at all.

12.5.2.1.7.9 N6, every other browser rung, a real platform path of a
module whose unit suite runs in the smoke run, its time not measured: the
rest of the root "suites" ("stage 6: kill between file and row", and "stage
0: worker hang keeps the UI's TAP lines", which runs the page's suites a
second time); every rung of the roots faults, probe (but for N1 and N2),
credential, release, first, locked, level, tool, crash, timeout, compact,
bulk, replay and evict; and the rung "stage 5: stub reachable", outside any
root, which only the `normal-test` roots probe, timeout and compact need.

12.5.2.1.7.10 Counted when the labels were written: 23 roots, 2 of them
`smoke-test`; 126 rungs, 3 `smoke-test` and 123 `normal-test`, "stage 5:
stub reachable" among them; every rung that moves 2 GiB, every rung that
waits out a 120 s timer, and `rung_blob_max` are `normal-test`.

12.5.2.1.8 Printing and the deadline. Each suite's elapsed seconds are read
with `time.monotonic` around it. Each rung's line ends with `(<label>, <s>
s)`; a page build's line ends with its seconds; a passing run ends with
`the <category> run took <s> s`. A rung its category leaves out is neither
run nor printed. In a `smoke-test` run this file runs under an alarm at the
run's deadline, 120 s from the start of `python/test_all.py`, which raises
naming the suite it stopped.

12.5.2.1.9 A stage's exit criterion is met by a `--normal-test` run, which
runs every rung.

12.5.2.1.10 Sizes. `blob_max`, 2147483391, is the one window every blob
goes through, and it counts blob bytes only, never line bytes, which
`line_max` bounds line by line. Each rung that proves a window reads
`blob_max` from its root's settings, so with the shipped value each such
rung moves 2 GiB; the proofs stay at the window's edge. A `--normal-test`
run needs about 2 GiB of disk per edge root and up to 6 GiB of OPFS.

12.5.2.1.11 The page and the server under test. Debug mode is the setting
`debug`. The server gates `console`, `settings.put`, `source.put`,
`system.restart` and `verbose.put` on it; the page gates the overlays and
`settings_put`. Headers use full names in debug mode, short names
otherwise. Debug mode is also the only verbose switch of the server and of
the page: the task manager's trace, the server's trace and the forwarding
of `verbose.put` happen in debug mode only, and a failure is logged always.
Verbose levels belong to the shell alone.

12.5.2.1.12 The rules of section 3 and the project rules bind every rung
function, helper, constant and comment of the file: two English names per
function, constants at the top, the comment check of `test_posix.py`.

12.5.2.1.13 Names gone from the design, which no rung reads or formats:
the settings `message_max`, `queue_max`, `verbose_forward` and
`turn_compact_tokens`; the strings `wire.message_over` and
`jslb.message_over`; the snapshot pieces `db.chunk`, `SnapshotFetch` and
`SnapshotHead`; the rung `rung_level`, its input "6", `_ENDING_LEVEL`,
`_TOOL_LEVEL` and `_TRACE_LEVEL`. The level that stays, the console
shell's, is `_SHELL_LEVEL`, and the root "level" keeps its name.

12.5.2.2 Stage 0, the harness (task 1.5).

12.5.2.2.1 The rungs of the stage as the file has them, for finding them,
not as an expectation. Root "suites" (`smoke-test`, the test page): "stage
0: typescript suites" (`rung_suites`, `smoke-test`), "stage 0: typescript
suites in order" (`rung_suites_order`, `smoke-test`), "stage 0: worker hang
keeps the UI's TAP lines" (`rung_worker_hang`, `normal-test`). Root
"faults" (`normal-test`, the engine page), each `normal-test`: "stage 0:
thrown error" (`rung_thrown`), "stage 0: first fault only" (`rung_first`),
"stage 0: reload" (`rung_reload`), "stage 0: rejection"
(`rung_rejection`), one "stage 0: failing <name>" per resource kind and
"stage 0: failing with neither address" (`rung_resource`), "stage 0: worker
fault posted" (`rung_posted`), "stage 0: worker throws at load"
(`rung_load`), "stage 0: write versus append" (`rung_append`).

12.5.2.2.2 The plan's proofs of stage 0: one passing, one failing, one
raising and one skipped method yield identical TAP in both languages as one
subtest block, accepted by the consumer; every way a run can fail, each an
expected failure of a suite; `failfast`; `i18n` raises in both; a thrown
error in the test page ends in the `<pre>` screen; `settings_get` of an
unknown id throws and the frozen object refuses a write. The TAP modules'
own tests run first in each runner. Survey: the TAP text; the PNG. Exit:
both runners exit 0 on the real suites, whose expected failures prove each
way a run fails. The TypeScript side of these proofs is carried by "stage
0: typescript suites"; the Python side is `python/test_all.py`'s.

12.5.2.2.3 Every way a run can fail, as the TypeScript producer is
exercised: a failing assertion and an exception raised in a test; errors in
`setUp`, in `tearDown`, and in `tearDown` after a failure (two outcomes of
one test); `expectedFailure` and an unexpected success; a skip; failfast
ending the run with `Bail out!`; a module that does not load. A test can
declare that a suite must fail in a stated way, and it passes when the
suite fails exactly that way.

12.5.2.2.4 The stream. One TAP plan per language per run; each module's
suite is one subtest block indented four spaces with its own plan, then a
parent `ok N - <module>` line; the line grammar is D12 (the default that
puts the block plan `    1..N` first, writes no `# Subtest` line and bare
method names, and ends a failfast block with plan, points, diagnostics and
`Bail out! failfast`). The page sends each TAP line as its own `tap.line
{language, text}` as it is produced, and the server appends each to
`<root>/tap/typescript.tap` unbuffered, so a hang leaves the lines before
it on disk. `test.html` shows the stream with every failed line highlighted
whole, a colour that was requested (Unconfirmed).

12.5.2.2.5 "stage 0: typescript suites" reads `<root>/tap/typescript.tap`
whole and checks it with `tap_consumer`, failing unless the stream is well
formed and no test failed. The file holds two TAP documents (12.5.3.2.1),
so the rung splits the text at `TAP version 14` and requires exactly two
documents, each well formed with no failure. The UI's suite runs first,
then the UI sends `worker.tests` to the worker, so every UI TAP line is on
the wire before the worker's suite starts: the file's order is the UI's
document, then the worker's. "stage 0: typescript suites in order" reads
the documents the first rung wrote.

12.5.2.2.6 The maintainer asked that no test output be lost. The UI's TAP
lines are kept when the worker's suite hangs or faults: "stage 0: worker
hang keeps the UI's TAP lines" pauses the AI worker through
`devtools.Browser.worker_pause(name)` and proves that the UI's TAP document
stays whole. The run's roots are made with `tempfile.mkdtemp` and kept, the
path printed, so the TAP file and `_verbose.sqlite` survive every exit.

12.5.2.2.7 Proofs the writers of `error_overlay` and `utility` left to
browser rungs: a thrown error and a rejection reaching the `<pre>` screen;
a failing script and a failing image reaching the capture phase handler,
the message "Failed to load <tag> <src or href>" naming `src`, else `href`,
and a throw when neither exists, `<object data>` and SVG `xlink:href`
throwing that missing address error; `overlay_show` showing the first fault
only; a Blob worker posting `fault`; a Blob worker throwing at load; the
stop function after the write; a Reload click; and the write versus append
case: when a fault fires while the parser runs a script, `document.open`
is a no op and the write appends.

12.5.2.2.8 The page under test: `error_overlay.ts` catches `error` and
`unhandledrejection` on the window, resource load failures in the capture
phase, and `fault` lines from the AI worker, and replaces the screen by
`document.write` with a `<pre>` holding the message and the call stack,
then closes the wire and terminates the worker. The screen offers Reload,
which is `location.reload()`.

12.5.2.3 Stage 4, dispatch and the main loop (task 1.5).

12.5.2.3.1 The rungs of the stage as the file has them: root "level"
(`normal-test`, settings `{"debug": True, "verbose_level": 2}`): "stage 4:
server trace in debug mode" (`rung_server_trace`, `normal-test`); root
"crash" (`normal-test`, the test engine page): "stage 4: crash logged"
(`rung_crash_logged`, `normal-test`).

12.5.2.3.2 The plan's proofs of stage 4 are made through `test_wire.py` and
a stdio MCP client written in the test, task 1.17's (11.9), not by this
file: `kv.put` and `kv.get` byte identical, `doc.put` and `doc.head`,
`verbose.tail`, `tools/list` and `tools/call` over stdio and over the `mcp`
line, an unknown type giving `error` then exit 1, `system.restart` serving
a second main loop after `source.put` in debug mode and the same refused
without it, an operation sequence the test builds replayed over the wire.
Exit: rungs pass; pyright clean. The two rungs of this file prove the
server's log and trace, below.

12.5.2.3.3 "stage 4: crash logged" proves the maintainer's request that a
server crash write its message to the server's log, not only to the
terminal: `bootstrap.py` opens `_verbose` for both roles before running
them and logs `bootstrap.run_failed` on a crash; the main loop's failure
exit logs `main_loop.serve_failed`; both then write the `error` line and
exit 1. The message is logged, not the stack: D21, the default that no
failure stacks are written to `_verbose`. A failure is logged always.

12.5.2.3.4 "stage 4: server trace in debug mode" proves the server's trace:
`bootstrap.hello_submit`, `main_loop.line_dispatch` and
`main_loop.line_reply`, written when `debug` is true and never otherwise,
each holding the line's header JSON only. The rung checks debug mode, with
no runtime level: `_verbose` has no `level` column, the test's
`VerboseRow` is `seq`, `at`, `text`, `verbose.log` takes the text alone,
and the probe `log_mark` takes `(text)`.

12.5.2.4 Stage 5, the page reaches the server (task 1.6).

12.5.2.4.1 The rungs of the stage as the file has them, each
`normal-test`. Outside any root: "stage 5: stub reachable"
(`rung_reachable`). Root "probe" (the engine page): "input before render"
(`rung_idle`), "wire hello" (`rung_hello`), "blob_max round trip"
(`rung_round`), "blob_max plus one refused" (`rung_over`), "wire_close"
(`rung_close`), "error line then close" (`rung_error`), the http rungs
"http post" (`rung_post`), "http preflight" (`rung_preflight`), "http text
and json" (`rung_answers`), "http statuses" (`rung_statuses`), "http closed
port" (`rung_refused`), "http never answers" (`rung_never`), "http stalled
body" (`rung_stall`), "http one line per request" (`rung_single`), "http
out of order" (`rung_order`), "http get with a body" (`rung_body`), "http
port in a worker" (`rung_worker`), "http throwing receiver"
(`rung_receiver`), the queue rungs "queue scheduling" (`rung_schedule`),
"queue thread port" (`rung_thread`), "queue two replies" (`rung_pair`),
"queue handler throws" (`rung_handler`), and "decoder fault"
(`rung_decoder`), "close without error line" (`rung_silent`), "wire token
timer" (`rung_token`), "wire open timer" (`rung_opening`). Root "stalled"
(`--main-loop stall_loop.py`): "wire hello timer" (`rung_stalled`). Root
"echo" (`--main-loop echo_loop.py`): "echo 128 MiB from the page"
(`rung_large`), "wire drain poll" (`rung_drain_poll`), "wire drain timer"
(`rung_drain_timer`). Root "release" (`debug` false): "debug gating"
(`rung_gating`). Roots "first" and "second" (synchronous): "synchronous run
recorded" (`rung_recorded`), "synchronous run identical twice"
(`rung_twice`). Root "main": "hello relay" (`rung_relay`), "verbose ring"
(`rung_ring`), "verbose sink" (`rung_sink`), "overlay strings"
(`rung_strings`), "overlay keys" (`rung_keys`), "overlay lines"
(`rung_lines`), "verbose batching" (`rung_batch`), "overlay style"
(`rung_style`), "overlay survey" (`rung_survey`), "second hello"
(`rung_restart`). Root "locked": "error before hello"
(`rung_error_first`). Root "level": "debug mode without feedback"
(`rung_level_two`). Root "upload" (the test engine page): "test engine page
start" (`rung_test_engine_start`), "traced synchronous load found"
(`rung_blocking_control`), "largest UI put" (`rung_ui_put_largest`), "128
MiB upload from the UI" (`rung_ui_upload`), "no synchronous load on the UI
thread" (`rung_blocking_none`). Each name above begins "stage 5: ".

12.5.2.4.2 The plan's proofs of stage 5: the hello relay; a round trip of a
blob of `blob_max` equal by SHA-256; a message whose blobs sum to one byte
more refused by `wire.ts` at its post; a UI put of one byte more refused
first by the AI worker's task queue with `queue.queue_over`; a `kv.get`
reply of one byte more refused by the page's decoder, its value written on
the server behind the page's back since no port carries it; a `verbose.put`
forwarded from the UI through the AI worker to the server unchanged; a
sleeping task woken by two replies in either order; the same run identical
twice in synchronous mode; the stress test of the UI thread (12.5.2.4.4); a
fault ending in the `<pre>` screen and Reload; a close without an `error`
line reported as such. Survey: a PNG with ctrl-1 open. Exit:
`test_browser.py` exits 0.

12.5.2.4.3 The refusals, by name: on the page's own port by `wire.ts` at
its post with `wire.blobs_over`; from the UI first by the AI worker's task
queue with `queue.queue_over`; a `kv.get` reply by the page's decoder with
`jslb.blobs_over`, the value of `blob_max` + 1 bytes written on the server
with `substrate.Store.kv_put` and a file path before the page's `kv.get`. A
message's blobs are checked when its line ends, before any blob byte is
buffered. The 128 MiB upload and the 128 MiB echo are one message each,
128 MiB being within `blob_max`.

12.5.2.4.4 The UI thread stress test: a long task observer on the UI thread
during a `kv.put` and a `kv.get` each of a blob of `blob_max`, a 128 MiB
upload, one message within `blob_max`, and a scripted turn with an image
requires no task over `long_task_ms`, 5 ms, a soft target reported as a
measurement, and no synchronous network load on the main thread, a hard
failure found by tracing. The UI's puts go through the test engine page.
Only synchronous network loads are detected, not the synchronous calls
behind `document.cookie` or `localStorage`, which the maintainer accepted.
"traced synchronous load found" proves the trace event names on a load
made for it; "no synchronous load on the UI thread" then finds none. The
scripted turn and the long task report are stage 8's rungs on the same root
(12.5.2.7.6).

12.5.2.4.5 The test engine page: `html/test_engine.html` is the engine page
built with the test bundle's `ts/test_hook.ts`, through which a rung
submits tasks from the UI's live queue (`page.test_engine`,
`boot.test_engine`, `test_hook.engine_run()`, the global `test_ui_tasks`);
`page_build(name, test, template)` chooses the template; the production
page carries no test code. `test_ui_tasks.task_submit` is called only
inside handlers, so `queue.submit_outside` cannot happen.

12.5.2.4.6 The maintainer's requests this stage carries:

12.5.2.4.6.1 An `error` line arriving before `hello` shows the server's
message, not `wire.receiver_missing`: `WirePort.line_take` throws
`wire.error_first` with the server's message and stack, and the port then
shuts, so the close adds no second fault. Its causes: a second tab, an
unset key, an empty `provider.json`, a settings failure; "error before
hello" runs on the root "locked".

12.5.2.4.6.2 In debug mode, where forwarding is always on, the overlay does
not feed itself: `WireTap.line_post` does not render `verbose.put` into the
overlay of tty 1. "debug mode without feedback" proves it.

12.5.2.4.6.3 `rung_gating` can pass. It failed because the console view
always appended a hidden `div` to `#debug`, a cause in the test file, which
was repaired: the console is no longer hidden for the visibility rungs.

12.5.2.4.6.4 The drain timer and the drain poll are written, and so are the
uploads from the UI and the traced synchronous I/O.

12.5.2.4.7 Proofs the writers of the units left to browser rungs:

12.5.2.4.7.1 The http port, twelve rungs against a local stub server: the
exact POST body and headers, text and JSON responses, 400, 401 and 500
statuses, a closed port, a stub that never answers or stalls the body, no
second line after the timeout, several requests out of order, GET with a
body, the CORS preflight, the port inside the worker, a throwing receiver.

12.5.2.4.7.2 The task queue: non synchronous scheduling, `ThreadPort`
across a real worker, `verbose.put` from the UI through the worker to the
server unchanged, a sleeping task woken by two replies over real ports, the
same run identical twice in the real page, the stress test, `sink_attach`
on the live `verbose`, a handler throw reaching `error_overlay`, the hello
relay.

12.5.2.4.7.3 The wire port: the token fetch and the open on both ports, the
token accepted by ttyd, every timer, the drain poll, a fault closing the
port, cache sends through the substrate's reader, a message at the window
and one byte over through ttyd, the hello relay, close code 1006, the
decoder fault, `wire_close`.

12.5.2.4.7.4 The verbose module: the module singleton at the live state,
the queue installing the sink, `verbose.put` batching.

12.5.2.4.7.5 The overlays: ctrl-n key handling, ctrl-0 staying the console
view, `overlay.line` lines reaching `line_add`, debug gating, the PNG with
ctrl-1 open, the real CSS showing and hiding, the real strings table
holding `overlay.ring_invalid`.

12.5.2.4.7.6 The page: the worker's start and its promises, the hello step
order, a second hello, a fault on worker load, keys on the real page, the
overlay feed.

12.5.2.4.8 The connection. The worker fetches `/token`, opens `/ws` with
subprotocol `tty`, sends ttyd's first message, skips title and preferences
and waits for `hello`; it posts `settings.set` to the UI, answers with an
empty reply, then posts `boot.hello`. `wire.ts` waits 120 s for the token,
the open, the hello and the drain; a timer rung faults with
`wire.wait_expired` naming the wait (`wire.what_token`, `wire.what_open`).
The hello timer is reached with `python/stall_loop.py`, a fixture main loop
whose `loop_prepare` never returns. A close without an `error` line is the
fault "connection closed with code N and no error line"; Linux ttyd closes
with code 1006 and no close frame when the program exits.

12.5.2.4.9 The second hello: D9, the default that a second `hello` after
`system.restart` is a fault ending in Reload. "second hello" proves it on
the root "main".

12.5.2.4.10 Synchronous mode, the setting `queue_synchronous`, is debug
only: before the queue reads the next line from any port it runs every
task it holds to completion, so runs are deterministic. The synchronous
roots "first" and "second" have the settings `{"queue_synchronous": True,
"debug": True}`; "second" compares its run with the one "first" recorded.

12.5.2.4.11 The overlays: ctrl-n, n from 1, toggles the overlay of tty n, a
`<pre>` holding the rendered form of the last `verbose_ring` lines in both
directions, newest last, read only. A line is rendered as its JSON text
followed by one `<blob "n"=K>` tag per blob, K the header key from 1. In
debug mode the same rendering and the page's `console.*` output go to the
server as `verbose.put`. A 128 MiB upload renders as one line, a turn as
many.

12.5.2.5 Stage 6, the browser substrate and replication (task 1.5).

12.5.2.5.1 The rungs of the stage as the file has them, each
`normal-test`. Root "suites": "kill between file and row"
(`rung_kill_between`). Root "first" (synchronous): "second load"
(`rung_reopen`), "start replacement" (`rung_replace`), "desync reload"
(`rung_desync`). Root "main": "table from the AI" (`rung_pairs`),
"overflow through OPFS" (`rung_overflow`), "cache exhaustion"
(`rung_cache`), "pool exhaustion" (`rung_pool`). Root "bulk": "database
over the old window loaded as one blob" (`rung_bulk_start`), "db_unload and
db_load keep a cached value" (`rung_bulk_reload`). Root "replay" (the test
engine page, `debug` true): "operation sequence replayed into the page"
(`rung_page_replay`), "string table from the UI" (`rung_ui_strings`). Root
"evict": "_files eviction on leave" (`rung_files_evict`). Root "largest"
(the test engine page, run last): "largest database within blob_max
measured" (`rung_blob_max`). Each name above begins "stage 6: ".

12.5.2.5.2 The plan's proofs of stage 6: the stage 3 suite ported (task
1.8, 12.6), but for `test_wal_left`; a second load finding the rows;
overflow files in OPFS; the string to string table replicated from the UI
and from the AI; the start replacement of a differing file; the desync
reload; an operation sequence the test builds, `test_wire.replay_build`'s,
replayed into the page from the UI's queue, the browser's copy then
compared with the server's. It measures the largest database: a database of
the most 4096 byte pages within `blob_max` loaded with `db_load` as one
`db.snapshot` blob, the origin's quota and usage read before it, and the
UI's `db.snapshot` of it compared with the server's file; the rung fails
naming the path and the numbers where one cannot carry it. Exit: "identical
counts to the Python suite; the reload test passes."

12.5.2.5.3 Replication. Every modifying substrate operation committed in
the browser is forwarded as the same line to the server right after the
transaction commits, in order, one in flight per database, carrying
`since`, the browser's `seq` before the operation; the server refuses it
with `error` when `since` is not its own `seq`. The first unit test
replicates a string to string table, created and filled through `sql_run`,
by modifications submitted as tasks from the UI thread and from the AI
thread, and compares the server's copy; Unconfirmed: the UI thread, which
holds no SQLite, submits its modifications as tasks to the AI worker's
database, which forwards them. Start: where the `seq` that `hello` carries
for a database differs, the browser's file is replaced by the server's
`db.snapshot`, one blob of at most `blob_max` with its `sha256`, checked
before the restore; only the databases the browser holds are replaced, the
others stay unloaded until `db_load`. Desync: a refused push, or a reply
whose `seq` is not the browser's, is a fault; the page reloads and the
reload replaces the file.

12.5.2.5.4 `rung_blob_max`, the measurement, on a root of its own with the
shipped `blob_max`: the server's fixture makes a database of exactly 524287
pages of 4096 bytes, 2147479552 bytes, the most whose file is at most
`blob_max`, and the page loads it with `db_load`: one `db.snapshot` reply,
one blob, its digest checked, its `seq` opened. Before the load, the
origin's `quota` and `usage` from `navigator.storage.estimate()`, read
through DevTools, are reported and checked to hold three copies of the
database, since a restore holds at its peak the streamed cache file, the
temporary file of its check and the database file. The UI's `db.snapshot`
of it, the export through the worker's heap, is compared by SHA-256 with
the server's file. The time of each is reported. The rung fails, naming
the path and the numbers, where any of them cannot carry the database.

12.5.2.5.5 The maintainer's requests this stage carries:

12.5.2.5.5.1 A database over the old 10 MiB window is sent to the browser
as a snapshot, loaded and restored: `rung_bulk_start`, now one `db.snapshot`
blob.

12.5.2.5.5.2 A value over `overflow_bytes` survives `db_unload` then
`db_load`: `rung_bulk_reload`. The `kv_get` and `doc_get` tools fetch a
value not held with `kv.get` and refill the cache after its SHA-256 check.

12.5.2.5.5.3 The operation sequence replay of the page:
`rung_page_replay`.

12.5.2.5.5.4 Automatic eviction of the browser's `_files` tier:
`Store.cache_evict(db, keep, budget)`, called by the `render` tool when the
scene changes, keeps the scene's header refs and the rendered image within
`files_browser_bytes`: `rung_files_evict`.

12.5.2.5.5.5 The string table replicated from the UI, through the test
engine page: `rung_ui_strings`.

12.5.2.5.5.6 The kill between file and row, through real workers on the
test page: `rung_kill_between`. Its pause point is the test only code
`kill_pool`, `kill_put`, `kill_hold` and `kill_check` of
`ts/test_substrate.ts`, whose probes pass `options.compact`, the store's
sixth argument.

12.5.2.5.6 The snapshot rungs ("second load", "start replacement",
"database over the old window loaded as one blob", `rung_blob_max`) expect
one `db.snapshot` reply with one blob, carrying `sha256` and `seq`
(`SnapshotReply`, `snapshot_check`, `image_read`); every edge rung works at
`blob_max`.

12.5.2.5.7 Exhaustion. The pool and the cache slots are fixed at
initialization (256 cache slots; a pool of `2n + 36`) and refuse past
their limits; "cache exhaustion" and "pool exhaustion" prove those
refusals, and the pool rung also checks on the server's side the writes
the pool dropped.

12.5.2.6 Stage 7, the console tty (task 1.5).

12.5.2.6.1 The rungs of the stage as the file has them, each
`normal-test`. Root "probe": "console open, close, exit, open"
(`rung_cycle`), "console closed before open" (`rung_closing`). Root
"credential" (ttyd with `--credential`): "token with a credential"
(`rung_credential`). Root "release" (`debug` false): "console role refused"
(`rung_refused_role`). Root "level": "console at shell verbose level 2"
(`rung_console_verbose`), "console open, exit, open in the view"
(`rung_console_reopen`). Root "main": "keystrokes dropped before the first
message" (`rung_early`), "console open" (`rung_console`), "console echo"
(`rung_echo`), "console rows fitted" (`rung_console_rows`), "console rows
refitted" (`rung_console_refit`), "console run" (`rung_run`), "permit
deny" (`rung_deny`), "console run timeout" (`rung_timeout`), "console
interrupt" (`rung_interrupt`), "console fed while hidden" (`rung_hidden`),
"console exit" (`rung_exit`). Each name above begins "stage 7: ".

12.5.2.6.2 The plan's proofs of stage 7: `echo` through dash into
xterm.js, `^C` ending `sleep 600`, ctrl-0 showing and hiding the view, the
role refused outside debug mode, `console_run` returning the output and
timing out on `sleep 600`, Deny returning an error to the caller. Survey: a
PNG with the console visible. Exit: the browser test passes.

12.5.2.6.3 The console. tty 0 is `bootstrap.py` with the role `console`:
when `debug` is true it runs `/bin/dash` through `verbose.exec` at the
setting `verbose_level`, `[dash, "-v"]` its level 2 form, with a scrubbed
environment and the root as working directory, and exits with its code;
when `debug` is false it exits 1 and ttyd closes the connection. Its pty
stays cooked, so it echoes. Unconfirmed: the AI worker owns the console
socket and relays it to the UI. `console.open` from the UI makes the AI
worker open tty 0; output arrives as `console.output` with one blob, input
goes as `console.input` with one blob; `console.close` closes the socket;
`console.exit` is pushed when ttyd closes it. The `console.open` reply
carries `token`, fetched from `/token` (D23, that default).

12.5.2.6.4 `console_run` and permission. The AI reaches the console only
through `console_run`, after the permission flow: the tool posts the text
and a newline as `console.input`, submits `console.read` and sleeps; the
port answers with the output once the prompt returns or `timeout_seconds`
expires. The UI shows the request with Accept, Deny and Always Allow:
Accept runs it once; Deny returns an error to the model; Always Allow
lasts the tab and is not stored. The permit set is `console_run` alone.

12.5.2.6.5 Shell levels, the shell's alone: level 0 runs `argv` with its
output passed through; level 1 runs `argv` passed through and writes its
start and exit to the server's log; level 2 runs `argv_verbose` raw and
writes the same two lines. "console at shell verbose level 2" proves the
console at level 2, dash's output passed through raw.

12.5.2.6.6 The maintainer's requests this stage carries:

12.5.2.6.6.1 The console view reopens: `exit_done` returns the view to
idle, and ctrl-0 on an idle view sends `console.open` again, so the console
reopens without a page load; "console open, exit, open in the view".

12.5.2.6.6.2 `rung_refused_role` can pass: it never sent ttyd's first
message, a cause in the test file, which was repaired.

12.5.2.6.6.3 An open console does not cover the subtitle, the permit
buttons or the input: the console's rows are fitted to the space above the
subtitle band and its columns stay 120, with the new string
`console_view.rows_unfit`; "console rows fitted" and "console rows
refitted".

12.5.2.6.7 Proofs the console's writers left to browser rungs: dash's echo
into xterm, `^C` ending `sleep 600`, ctrl-0, keystrokes dropped while input
is disabled, feeding while hidden, a token accepted by a ttyd with a
credential; the token fetch and the open; open, close, exit, open;
`wire.open_closed` for a socket that closes before it opens, the close
receiver not called; `console_run` and its timeout; `console.exit`; the
role refused. Typing while opening: xterm's `disableStdin` is true until
the first message and after exit, and text that reaches the view anyway is
a hard error.

12.5.2.6.8 The plan's research goal: whether xterm.js can be fed while
hidden and keep its state; the headless package is the alternative for
feeding, chosen once by the research result. "console fed while hidden" is
that measurement.

12.5.2.7 Stage 8, the hyperposition (task 1.7).

12.5.2.7.1 The rungs of the stage as the file has them, each `normal-test`
but "stage 8: fresh root". Root "probe": the media rungs "media png kept"
(`rung_store`), "media download as blob 1" (`rung_fetch`), "media network
failure" (`rung_lost`), "media status" (`rung_missing`), "media timeout"
(`rung_late`), "media undecodable" (`rung_garbage`), "media eviction"
(`rung_evict`). Root "tool": "failed tool call" (`rung_tool_failed`). Root
"timeout" (`provider.scripted` false, a `provider.json` of its own pointed
at the stub, the key in ttyd's environment): "provider request timeout"
(`rung_http_timeout`). Root "compact" (`turn_compact_turns` 2, the same
provider arrangement): "compaction at the threshold"
(`rung_compact_auto`). Root "fresh" (`smoke-test`, `provider.scripted`
true): "fresh root" (`rung_fresh_root`, `smoke-test`). Root "stress"
(`turn_compact_turns` 8): "script put, debug and compaction"
(`rung_exercise`), "stress of script put, debug and compaction"
(`rung_stress`). Root "upload" (the test engine page): "traced scripted
turn" (`rung_traced_turn`), "long tasks of the UI's puts, upload and turn"
(`rung_long`). Root "main": "band uncovered by the debug views"
(`rung_band`), "scripted turn" (`rung_turn`), "time without input"
(`rung_still`), "image visible" (`rung_image`), "console visible"
(`rung_terminal`), "subtitle visible" (`rung_subtitle`), "input visible"
(`rung_input`), "overlay visible" (`rung_overlay`), "overlay newest line"
(`rung_overlay_newest`), "overlay wide" (`rung_wide`), "long tasks"
(`rung_long`), "start with a scene image" (`rung_scene`), "click on the
image" (`rung_click`). Each name above begins "stage 8: ".

12.5.2.7.2 The plan's proofs of stage 8: the stubs end to end with time
not advancing without input. The integration tests drive every operation
of the metaverse, its players, worlds, scenes and turns through the integer
based scripted provider and the seeded bootstrap script: a universe, a
world and a region created, a typed table created by DDL, a scene written
and entered, an image made, a render, a turn stored, compaction, a script
put, run and debugged, the baseline the AI will be asked for. Survey: a
PNG after the exchange. Exit: the scripted run passes; the real provider
is behind a setting and outside the automated tests.

12.5.2.7.3 The maintainer's requests this stage carries:

12.5.2.7.3.1 A fresh root renders without a fault while `provider.scripted`
is true. The server seeds the `_files` row `provider/script.json` from
`python/seed/provider_script.json` when it is missing, and the scripted
provider reads its Script from `/_files/provider/script.json`. "fresh
root" proves the page load, `hello`, the seeded Script and a first render
with no fault.

12.5.2.7.3.2 A failed tool call does not break a scene: no unanswered tool
call turn is stored or survives a reload. A reply with tool calls is
stored together with its tool results in one transaction after every
result is built. "failed tool call" proves it.

12.5.2.7.3.3 The real HTTP timeout inside a turn: "provider request
timeout" writes its own `provider.json` into its own root, sets
`provider.scripted` false there and points `base_url` at a local stub. The
plan says that `provider.json` "is not used during testing but by one
rung", this one, and that the maintainer accepted that; in every other
test `provider.scripted` is true and the file is never read.

12.5.2.7.3.4 The plan's exercises in the scripted turn (compaction, a
script put, a script debugged) and stress tests of the same with non
repetitive data: `rung_exercise` and `rung_stress` (rounds 2 to 8) on the
root "stress". Each round runs a script put, a script debug of a script
that reads seeded data and puts it back, and a compaction;
`compaction_check` checks each input; the script inputs of the roots do
not collide (16 on bulk, 17 on evict, 18 to 41 on stress).

12.5.2.7.3.5 Compaction by the event counter. When the browser's
`Store.turn_append` appends a turn of role `user` to a scene that already
holds `turn_compact_turns` turns or more, it first compacts that scene's
turns 1 to its last in the same transaction, forwarded as its own
`turn.compact` before the `turn.append`; the server applies both and never
compacts by itself. The summary turn, role `system`, holds one `i18n`
text, `substrate.turns_compacted`, naming the turns compacted and the count
that reached the threshold. A test root sets a small `turn_compact_turns`
of its own to reach compaction in a short run. `rung_compact_auto`, on the
root "compact" (`_COMPACT_TURNS` 2), checks the server's turns, the second
chat request and the order of the `turn.*` lines dispatched.

12.5.2.7.3.6 An open console covers neither the subtitle, nor the permit
buttons, nor the input: "band uncovered by the debug views", which
replaced the toggle rung. A shown overlay keeps its newest line in view
(`Overlay.end_show`): "overlay newest line".

12.5.2.7.4 Visibility. Unintentional invisibility is always a bug, not a
style issue. The console view and the overlays show above the scene's
image; eight visibility rungs were asked for that rule. Two states are
accepted by the maintainer (12.5.3.6.3, 12.5.3.7.9).

12.5.2.7.5 Proofs the writers of the units left to browser rungs: media, a
real PNG kept, a download as blob 1, a network failure, a status outside
200 to 299, a timeout, undecodable bytes, an eviction closing a real
`ImageBitmap`; the agent, the real `HttpPort` timeout and a real MCP round
trip in a turn; the page, a click on the real page, the media decode path,
the start with a scene image.

12.5.2.7.6 The long tasks of 12.5.2.4.4 include a scripted turn with an
image: "traced scripted turn" and "long tasks of the UI's puts, upload and
turn" on the root "upload", whose `long_task_ms` result is a soft target
reported as a measurement.

12.5.2.7.7 Time not advancing without input: the agent sets no game
timers; "time without input" waits `_QUIET_SECONDS`, 5 s, and finds the
state identical.

12.5.3 Decided, not a finding.

12.5.3.1 Every stage.

12.5.3.1.1 The plan's stage order was set aside by the maintainer's "write
everything first and stop before testing" (class C): the rungs of every
stage were written together, and none waited on an earlier stage's exit.

12.5.3.1.2 The roots and ladders as built, by the earlier writers' choice:
roots built as `test_wire.py` builds them, the page served from the root
with `--index`; one browser and one stub server for every root; the Script
and the AI's scripts written into `_files` by a `substrate.Store` in the
test process before ttyd starts; the provider key removed from ttyd's
environment, but on the roots that pass it; the engine page built as
`build/test_engine.html`; screenshots in `build/test_browser/`; first
failure only through `CheckFailed`; the run's roots kept.

12.5.3.1.3 Timers, each its writer's sane default, not changed by the
review: `_RUNG_SECONDS` 120.0, `_SUITES_SECONDS` 600.0, `_POLL_SECONDS`
0.1, `_STOP_SECONDS` 5.0, `_HTTP_SECONDS` 2, `_MEDIA_SECONDS` 2,
`_CONSOLE_SECONDS` 30, `_SLEEP_SECONDS` 2, `_HOLD_SECONDS` 120.0,
`_QUIET_SECONDS` 5.0, `_ECHO_SECONDS` 600.0, `_WIRE_SECONDS` 120,
`_DRAIN_SECONDS` 120, `_FRAMES_MS` 1000, `_PROVIDER_SECONDS` 1,
`_STALL_SECONDS` 5.0, `_LARGEST_SECONDS` 600.0, `_UPLOAD_SECONDS` 600.0,
`_STRESS_SECONDS` 600.0, `_WINDOW_SECONDS` 600 (for `rung_round`,
`rung_over` and `rung_decoder`) and `_MEASURE_SECONDS` 3600 (for
`rung_blob_max`).

12.5.3.1.4 Stalls are made by stopping ttyd with SIGSTOP.

12.5.3.1.5 The labels as built, each Unconfirmed; the maintainer confirms
the fit from a `normal-test` run, whose lines give every `smoke-test`
suite's seconds, and from a `smoke-test` run that passes. The grain, chosen
by the planners: a rung, with its root labelled too; the question stays
open (4.8.4.28). Its other options, open with it: each runner whole; the
root or stage as the grain, which loses the probe root's quick
rungs to its 2 GiB and 120 s rungs unless roots are split; the stages of
the plan, which mix labels inside stages 5 and 6; each TypeScript module,
which needs the category on the page (a design kept in 4.2). A
browser rung joins the smoke run when a measurement shows room; more roots
before any measurement were rejected.

12.5.3.1.6 Not built, by the planners' choice: a suite left out is neither
printed nor written to TAP as `# SKIP`; the runners and `category.py` write
their messages with f-strings, not `i18n` names; no test runs
`test_posix.sh` or `test_powershell.ps1`.

12.5.3.1.7 A `smoke-test` run ends at its first failure of any kind, the
deadline's among them (built); a `normal-test` run stops at its first
failing test only with `--failfast`.

12.5.3.1.8 Run alone, `python/test_browser.py` keeps `argparse`'s default
and takes `--normal` for `--normal-test`: the maintainer's answer that
refuses abbreviations covers `python/test_all.py` and its test parser, and
leaves this runner as built.

12.5.3.1.9 Withdrawn: the sibling imports inside functions, after
`sys.pycache_prefix` is set, are open (11.11.5.4, 4.7.14).

12.5.3.1.10 The proofs at the window's edge (built, a reading): a blob of
`blob_max` and one byte more refused; 128 MiB as one message. The question
stays open (4.8.4.15); its other options, open with it: the earlier 16
MiB and 128 MiB proofs with the edge proved only by the
decoders' unit tests; the edge proved on roots with a smaller `blob_max`.
`blob_max` is 2147483391, SQLite's documented allocation bound, not a
measurement, until `rung_blob_max` measures Chrome. The value itself is
open for the maintainer (11.4.5.1); the review keeps it as built.

12.5.3.1.11 The disk and memory the edge rungs need (about 2 GiB of disk
per edge rung, up to 6 GiB of OPFS for `rung_blob_max`) is a risk owed to
the testing phase.

12.5.3.1.12 The first writer of the file recorded "three accepted races"
and did not name them; the races later writers named are in 12.5.5.

12.5.3.1.13 `rung_level` was removed with no replacement, since the
browser tool `verbose_level` is gone; the unit test `test_level_gone`
proves the registration.

12.5.3.1.14 D15, the default that `devtools.page_open` waits, with a bound,
on exactly `net::ERR_CONNECTION_REFUSED`; D25, the default that test only
exports stay.

12.5.3.2 Stage 0.

12.5.3.2.1 `<root>/tap/typescript.tap` holds two TAP documents, each from
`TAP version 14`, departing from the plan's "one TAP plan per language per
run" (class B, unconfirmed). Alternatives named: a third `language` value,
which changes `TapLine` and the languages of `engine_tap`; numbering
continued across the two threads, refused because it needs a fixed type.
The order is the UI's document, then the worker's, so that the UI's lines
are written before the worker's suite can hang.

12.5.3.2.2 `ts/test_all.ts` runs with failfast a constant `false` (class
B), and has no timer per module: the rung's timer covers a hang.

12.5.3.2.3 `devtools.Browser.worker_pause(name)` pauses the worker through
`Target.setAutoAttach` and `Debugger.pause` and waits for
`Debugger.paused` (an accepted API addition, section 4.5).

12.5.3.2.4 The first fault flag lives in `error_overlay.FaultScreen`, the
module functions passing through to one page instance, so that a test does
not flag the test page for good (rejected: a module flag, a flag in the
document); an accepted API addition.

12.5.3.2.5 `<object data>` and SVG `xlink:href` throw the missing address
error, as built; the alternative named was to add `data`.

12.5.3.2.6 "stage 0: worker hang keeps the UI's TAP lines" runs the page's
suites a second time, and is `normal-test` (N6).

12.5.3.3 Stage 4.

12.5.3.3.1 The root "level" is `{"debug": True, "verbose_level": 2}`, one
root for the debug rungs and the console rungs, not two, because one of
the rungs asked for needs the shell's level 2 on the same root and the key
is in every root's settings (class B; options a) one root as built, b) two
roots, c) as the maintainer names).

12.5.3.3.2 The server's trace holds header JSON only (built; the question
stays open, 4.8.4.21, with its other options: the whole line in the
rendered form; no trace).

12.5.3.3.3 A crash before the log can open, from the arguments, raw mode,
the engine lock or the settings, reaches only the terminal (approved).

12.5.3.3.4 Verbose levels in the server and the runtime are deferred by
the maintainer (4.2); the stage 4 rungs check debug mode, with no
level.

12.5.3.4 Stage 5.

12.5.3.4.1 Approved by the maintainer: a UI put of `blob_max` + 1 is
refused first by the AI worker's task queue with `queue.queue_over`, not
by `wire.ts` with `wire.blobs_over` (options were a) as built, b)
`wire.blobs_over` with `queue.ts` no longer counting the UI's lines, c) a
string the maintainer names).

12.5.3.4.2 Approved by the maintainer: `rung_decoder` writes the value of
`blob_max` + 1 bytes on the server behind the page's back, with
`substrate.Store.kv_put` and a file path, before the page's `kv.get`, since
no port can carry it (options were a) as built, b) a test main loop file
that sends such a reply, c) a unit test only).

12.5.3.4.3 Approved: the drain rungs stall ttyd with SIGSTOP, because
settings driven wait lengths are excluded by the timer rule and a fixture
main loop cannot stall ttyd's reads without a ttyd input flow patch.

12.5.3.4.4 Approved: the drain timer rung posts a burst sized from the
queue bound, not one 8 MiB echo, which the socket buffers may absorb. The
bound is now `blob_max`, so the burst is 255 lines of 8 MiB at the shipped
value; 11 lines was recorded under the old bound.

12.5.3.4.5 Approved: the drain poll rung sleeps `_STALL_SECONDS`, 5 s,
then checks the poll once (the alternative recorded, a `probe.wire_polling`
waited on with `probe_wait`, is not built).

12.5.3.4.6 Approved: the echo rungs keep the `probe.pattern` bytes of
period 251, not non repetitive data.

12.5.3.4.7 Withdrawn: the use of the stub by the token, open and closed
before open rungs is a candidate (12.5.5.4.10).

12.5.3.4.8 The three wire timer rungs wait the full 120 s each, more than
6 minutes a run, by design (N2).

12.5.3.4.9 The test engine page outside the production bundle, the
coordinator's choice, approved by the maintainer.

12.5.3.4.10 Approved: the largest UI put is measured in the start state it
is used in, because a fresh start and a reload differ in the digits of the
forward ids.

12.5.3.4.11 Approved: `rung_ui_upload` expected `worker_ai.queue_over`
after about 11 of its 15 puts, the AI's forward queue holding the forwards
past the old queue bound (options were a) as built, b) the test paces
itself one row at a time, c) back pressure in the AI). Under the one window
its 135 MiB fits `blob_max`, "so its expectation changes".

12.5.3.4.12 Approved: only synchronous network loads are detected, under
three candidate Chrome event names, where one is right
(`_BLOCKING_EVENT_NAMES`); "the page's UI thread" is any renderer main
thread (`CrRendererMain`); the names are Unconfirmed and
`rung_blocking_control` proves them first.

12.5.3.4.13 D9, the default that a second `hello` after `system.restart` is
a fault ending in Reload; the wire test accepts the second `hello`, the
page treats it as a fault.

12.5.3.4.14 D10, the default that `--main-loop` is refused outside debug
mode and with the console role: the roots "echo" and "stalled" set `debug`
true.

12.5.3.4.15 `verbose_forward` is gone: `verbose.put` is forwarded whenever
`debug` is true, and the fix that keeps the overlay from feeding itself
stands.

12.5.3.4.16 The root "probe" stubs the Worker.

12.5.3.5 Stage 6.

12.5.3.5.1 Approved: `test_wal_left` cannot apply to the SAH pool, which
has no WAL, and nothing is built for it.

12.5.3.5.2 Approved: the page replay compares the browser's copy with the
server's files, not through `test_wire`'s private reader. It imports
`test_wire` and uses only its public `replay_build`; the alternative, a
shared `python/replay_sequence.py`, is not built.

12.5.3.5.3 `db.snapshot` is one blob again; the snapshot in pieces is a
replaced design kept in 4.2.

12.5.3.5.4 Approved: the worker's own export for the UI's `db.snapshot`
stays `sqlite3_js_db_export` through the wasm heap, its limit measured by
`rung_blob_max` (the options not chosen: the pool's `exportFile`;
sqlite3.wasm rebuilt with a `MAXIMUM_MEMORY` of 4 GiB). Approved:
`db_load` calls whose images, held at once, pass `blob_max` fault with
`queue.queue_over`. Approved: `chunk_bytes` and `srv_buf_size` stay 1 MiB.

12.5.3.5.5 A database grown past `blob_max` in the browser is not refused;
its image fails loud at a window (built; rejected: `PRAGMA max_page_count`).
`db_unload` drops the browser's copy and the server's replicated copy is
the image that `db_load` restores (built).

12.5.3.5.6 Owed to the testing phase: the export check fails if
sqlite-wasm rewrites header bytes 18 and 19 from WAL to rollback.

12.5.3.5.7 The pool and the cache slots are fixed at initialization,
because promises are confined to initialization (class B; options a
platform port for run time growth, larger constants).

12.5.3.5.8 The kill worker's text is wrapped in a function, so its names
cannot clash with the bundle's.

12.5.3.5.9 The eviction rung is `rung_files_evict`: a second top level
`rung_evict` shadowed the media eviction rung and was renamed, its body
unchanged.

12.5.3.6 Stage 7.

12.5.3.6.1 Approved: `rung_console_reopen` runs open, exit, open.

12.5.3.6.2 Approved: `ConsoleView.close_request` exists and no UI action
calls it.

12.5.3.6.3 Accepted by the maintainer: with both shown, the overlay below
the console scrolls the console's top rows out.

12.5.3.6.4 Withdrawn: "console closed before open" uses the stub, a
candidate (12.5.5.6.6).

12.5.3.6.5 `rung_credential` rests on two browser behaviours recorded as
unconfirmed; checking them is the testing phase's.

12.5.3.6.6 Shell level 1 passes the console's output through and logs its
start and exit, because a captured level 1 gives dash no input (built;
the question stays open, 4.8.4.20, with its other option: the output
captured and formatted as Markdown progress).

12.5.3.6.7 The console's rows are fitted to the space above the band and
its columns stay 120; the plan rejects console size settings, xterm.js
sending its own size.

12.5.3.6.8 Typing while the console opens is a hard error (rejected:
throwing on every early key, buffering, dropping); the keystrokes rung
stops ttyd with SIGSTOP.

12.5.3.6.9 The console output `console_run` returns is normalized: CRLF to
LF, the echo and the `$ ` prompt cut. Deny returns `isError` with
`tools_browser.permit_denied`.

12.5.3.6.10 The root "level" as 12.5.3.3.1.

12.5.3.7 Stage 8.

12.5.3.7.1 Approved: the Script stays at `/_files/provider/script.json`,
seeded with one node and no replies, so input on a root without a test
driver faults.

12.5.3.7.2 Approved: a tool call turn is stored with its results after the
tools run.

12.5.3.7.3 Approved: `rung_http_timeout` writes its own `provider.json`,
against the maintainer's "not used during testing".

12.5.3.7.4 D8, the default that `XSJS_PROVIDER_KEY` is required only when
`provider.scripted` is false: the roots that set it false pass the key.

12.5.3.7.5 Approved: the stress test runs `_STRESS_ROUNDS`, 8 rounds, a
count chosen by its writer.

12.5.3.7.6 Compaction, built as the planners read it (Unconfirmed): the
events are every turn appended, of any role; the counter is the count of
the scene's `_turn` rows, counted when read; it runs in the browser's
substrate before a `user` turn; the summary is by truncation; the
threshold `turn_compact_turns` defaults to 64. The estimate design it
replaced, and its rung, are gone (4.2).

12.5.3.7.7 The stress script's `out_ref` takes the `/_files/rung/stress/`
prefix, because a ref with no database throws `substrate.ref_internal`.
`rung_exercise` waits for the scripted turn on the server before counting;
`rung_stress` fails when no round compacted by itself; the compaction
script no longer sums tokens; `rung_overlay_newest` runs `_INPUT_PLAIN` in
place of the removed input "6"; `stress_make()` reads no setting.

12.5.3.7.8 Unconfirmed: the root "main"'s start scene holds about 46
turns, counted from the ladder and not measured, under the default 64, so
it never compacts.

12.5.3.7.9 Accepted by the maintainer: the subtitle band lies over the
bottom strip of the fixed image.

12.5.3.7.10 `rung_band` replaces the toggle rung, and an earlier decision
on the toggle rung was withdrawn. `#debug` and `#subtitle` carry
`background: black`, a colour motivated only by the invisibility rule
(class B).

12.5.3.7.11 The media module as its writer recorded it, some points with
alternatives named: an image counts width times height times 4 bytes;
eviction is oldest first by insertion, a lookup does not refresh, the
newest is always kept, evicted images are closed; `media.fetch` decodes
before replying and an undecodable download is an `error` reply; a status
outside 200 to 299 is a failed download, named in the cause; failures are
`error` lines, hence faults on the UI queue ending in Reload; `media.fetch`
replies with the bytes as blob 1.

12.5.3.7.12 D17, the default whose last part makes the final text reply the
`ai.say` reply's `subtitle`.

12.5.4 Open, for the maintainer.

12.5.4.1 Every stage: the lines of the file over 79 columns that the
formatter cannot wrap, string lines `ruff format` will not shorten, as
11.11.5.1 says; listed and not changed, task 1.19's.

12.5.4.2 Stage 0: none.

12.5.4.3 Stage 4: none.

12.5.4.4 Stage 5: none.

12.5.4.5 Stage 6: the name `rung_blob_max`. The planners named the
measurement rung so in the design of the one window, and its writer kept
"the plan's three word name against the two word rule". A decision in
force that breaks a project rule is open, not a finding; the records offer
no options.

12.5.4.6 Stage 7: the xterm `Terminal` constructor options were written
from memory and not checked against the pinned 5.5.0 typings, and the
resize path was recorded as unreachable without a fit addon; options when
recorded: pin `@xterm/addon-fit`, or delete `resize_send` and its tests.

12.5.4.7 Stage 8: none.

12.5.5 Candidates.

12.5.5.1 Every stage.

12.5.5.1.1 The comment above the helper `ui_request`, used by rungs of
stages 5 and 6, holds a `;` outside a code span, which `comments_check`
refuses; `python/test_posix.py` stops there once the banner question of
`xsjs_install.ps1` is answered: severity 1. Listed once, so that one
request reaches task 1.19.

12.5.5.1.2 The second writer of the file recorded that close codes are
printed, not asserted, without naming the rungs. The rungs that writer
added: "console open, close, exit, open", "wire token timer", "wire open
timer", "console closed before open", "token with a credential", "echo 128
MiB from the page", "wire hello timer", "keystrokes dropped before the
first message", "time without input", and the server side check of the
pool rung.

12.5.5.1.3 A reviewer recorded "comment characters outside backticks" in
the file without naming the comments.

12.5.5.1.4 Harness points, task 1.19's, not reported by tasks 1.5 to 1.7:
a rung timer cannot fire during a DevTools call, and only `CheckFailed`
names the rung; a mutable Protocol attribute fails pyright strict; the
stub swallows an unexpected path; `tap_check` tallies failures; the roots
inherit `debug` and `provider.scripted` from the checkout; `tap_failures`
zips two different splits with `strict=True`; the `SIGALRM` handler is
left installed and a port is released before its reuse; the stub holds
the token, open and closed before open requests with no timeout of its
own; `_WIRE_SECONDS` and `_DRAIN_SECONDS` copy the lengths of
`ts/wire.ts`; `_KEY_ENTER`,
`_KEY_INTERRUPT`, `_EXTRAS_NONE` and `_EXTRAS_KEY` stand after their
classes; the one word probe names `pattern`, `thrown`, `hit`, `view`,
`views`, `viewport`, `canvas`, `fault`, `outcome`, `rows`, `focus`,
`permit`, `history`, `widths`, `sink`, `summary` and `receiver`;
`probe.fault` finds the TAP `<pre>` on the test page; a smoke run starts
the stub HTTP server that no smoke rung needs (S, its lazy design
written); the page names `_ENGINE_PAGE = "test_engine"` and
`_TEST_ENGINE_PAGE = "test_engine_hook"` read the wrong way round.

12.5.5.2 Stage 0.

12.5.5.2.1 The proof "a thrown error in the test page ends in the `<pre>`
screen": the fault rungs run on the engine page; on the test page the
probe's fault finder always finds the TAP `<pre>` and no rung on that page
calls it. That the test page registers no stop function is decided
(11.12.4.8) and is not part of this candidate. Check that a rung makes the
proof on the test page, or that a record says otherwise. No class or
severity was given.

12.5.5.3 Stage 4: none recorded.

12.5.5.4 Stage 5.

12.5.5.4.1 The comment above `rung_ui_put_largest` holds a `;` outside a
code span, which `comments_check` refuses: severity 1, as 12.5.5.1.1.

12.5.5.4.2 Names of three words against the two names rule:
`rung_test_engine_start`, `rung_ui_put_largest` and `rung_level_two`, the
last kept by its writer and recorded as kept.

12.5.5.4.3 `rung_order` ("stage 5: http out of order") is racy.

12.5.5.4.4 `rung_single` ("stage 5: http one line per request") proves
nothing.

12.5.5.4.5 The stub's requests held with no timeout of their own ("wire
token timer", "wire open timer") are a harness point (12.5.5.1.4).

12.5.5.4.6 "echo 128 MiB from the page" runs the port on the page's
thread, recorded as a gap; the plan says the AI worker is the only owner
of sockets.

12.5.5.4.7 The copies `_WIRE_SECONDS` and `_DRAIN_SECONDS` are a harness
point (12.5.5.1.4).

12.5.5.4.8 `rung_drain_poll` checks that the poll waits through
`probe.wire_pending`, which reads the WirePort's private `socket` and
`poll_id`; its writer recorded this as a gap, with options a) to d)
whose text is lost. The approval of the rung's form (12.5.3.4.5) names
the sleep and the one check, not the read; the probe is task 1.19's
(11.11).

12.5.5.4.9 `rung_ui_upload`: the approved expectation of
`worker_ai.queue_over` was written under the old queue bound, and the
record of the approval says that under the one window "its expectation
changes"; no later record shows the change. Check what the rung now
expects.

12.5.5.4.10 The token, open and closed before open rungs use the stub
server, not ttyd: the stub holds `/token` or the upgrade. Its writer
recorded this as a gap and named as alternatives ttyd's `--max-clients 1`
and DevTools `Fetch.enable` with a stopped ttyd. No class or severity was
given.

12.5.5.5 Stage 6.

12.5.5.5.1 `rung_desync` ("stage 6: desync reload") clicks Reload without
the hit check.

12.5.5.5.2 The pool exhaustion rung's server side check relies on the
writes arriving in order.

12.5.5.6 Stage 7.

12.5.5.6.1 The comment above `rung_early` holds a `;` outside a code span,
which `comments_check` refuses: severity 1, as 12.5.5.1.1.

12.5.5.6.2 The keystrokes rung also stalls the engine's own connection,
and its typed text check races a late send.

12.5.5.6.3 "token with a credential" runs the port on the page's thread,
as 12.5.5.4.6.

12.5.5.6.4 The request of "console closed before open", held with no
timeout of its own, is a harness point (12.5.5.1.4).

12.5.5.6.5 A reviewer named `rung_refused_role` among the identifiers of
three words, against the two names rule.

12.5.5.6.6 "console closed before open" uses the stub, as 12.5.5.4.10.

12.5.5.7 Stage 8.

12.5.5.7.1 `rung_compact_auto` has three words, kept by its writer and
recorded as kept, against the two names rule.

12.5.5.7.2 `rung_long` prints an unmeasured 0.0 ms, against no fake data;
both "stage 8: long tasks" and "stage 8: long tasks of the UI's puts,
upload and turn" run it.

12.5.5.7.3 The baseline of "time without input" races the writes still in
transit.

12.5.5.7.4 "click on the image" is proven by the scripted provider's
`input_invalid` fault, recorded as a gap; check what the rung proves of
the click.

12.5.6 Requests go to task 1.19 (11.11), the owner of
`python/test_browser.py`, which works them in its pass or in Phase 2 by
fresh agents run one at a time. A fix outside the file goes to that file's
owner (section 11): `python/test_wire.py` to task 1.17 (11.9);
`python/devtools.py` and the pages to task 1.18 (11.10); `ts/test_all.ts`
to task 1.20 (11.12); `ts/test_substrate.ts` to task 1.24 (11.16). A
change that needs both sides is a seam, as section 8 says.

12.6 Task 1.8, `ts/test_substrate.ts`.

12.6.1 Checks.

12.6.1.1 Scope: `ts/test_substrate.ts`, the TypeScript port of the stage 3
suite, read class by class and test by test against
`python/test_substrate.py`. Read only; it edits nothing.

12.6.1.2 Files read beside it: `python/test_substrate.py`,
`ts/substrate.ts`, `API/ts/substrate.d.ts`, `python/substrate.py`,
`i18n/en-US.json`, `ts/test_all.ts` (whose worker suite runs it), and the
rung "stage 6: kill between file and row" of `python/test_browser.py`,
which drives its kill probes.

12.6.1.3 The steward of `ts/test_substrate.ts` and of `ts/substrate.ts` is
task 1.24 (11.16).

12.6.2 Expected.

12.6.2.1 The plan's stage 6 proves the stage 3 suite ported, "but for what
has no meaning on the SAH pool, which has no WAL: a WAL file left by a
kill, `test_wal_left`, is not ported." Its exit criterion: "identical
counts to the Python suite; the reload test passes."

12.6.2.2 The proofs of stage 3, each of which the port carries as a test:
the tables created on first use in a new database; KV on both ref forms;
documents; heads; the document round trip, `doc_encode(normal)` moving
every reference string into the headers and leaving `{"$ref": n}` behind,
equal strings shared, and `doc_decode(encoded)` putting them back, the
round trip identical; `seq` across a reopen; overflow at exactly
`overflow_bytes`, a value of exactly `overflow_bytes` staying in the row
and a larger one going to the cache, file first, then the row; snapshot
and restore; a `SIGKILL` between file and row, whose unreferenced file
`kv_check` removes; `kv_check`; `operation_apply` of a sequence the test
builds; `turn_compact`. The Python suite's own exit is that it passes
under `python3 -X dev`.

12.6.2.3 Class by class: each test class of `python/test_substrate.py`
has its counterpart in `ts/test_substrate.ts` holding its tests, but for
the tests that 12.6.3.1 names and the differences that 12.6.3.2 records;
each test not ported has a record. Classes of the TypeScript file beyond
the port test the TypeScript store's own accepted API: `CacheFiles`,
`seq_get`, `forward_set`, `forward_done`, `db_stats`, `db_compact`,
`db_unload`, `db_load`, `start_open`, the handlers of the UI's `kv.*`,
`doc.*`, `db.*`, `turn.*` and `sql.*` lines, `kv_held`, `cache_fill` and
`cache_evict`.

12.6.2.4 Counts recorded when the two files were written: the Python
suite, 40 tests in 10 classes; the TypeScript suite, 16 test classes and
63 methods. Later work changed both; neither count is current.

12.6.2.5 Messages: every expected error is compared with the `i18n` text
of its name and arguments, never with a literal. When the file was
written, all 50 thrown names were compared with their `i18n` text.

12.6.2.6 The kill probes: `kill_pool`, `kill_put`, `kill_hold` and
`kill_check` are test only code exported from `ts/test_substrate.ts`, the
pause point of the kill between file and row (D25, the default that test
only exports stay). They pass the store's sixth argument as
`options.compact`. `test_kill_between` of the file uses them, and the rung
"stage 6: kill between file and row" (root "suites", `normal-test`, N6)
runs them through real workers on the test page, the kill worker's text
wrapped in a function so that its names cannot clash with the bundle's.

12.6.2.7 No state left between tests: side effects between tests are
banned; name order is fine.

12.6.2.8 The suite runs in the worker's half of the page's TypeScript
suites, in `tsconfig.test.json` order, under the rung "stage 0: typescript
suites" (`smoke-test`, S1). The worker sets the globals `test_sqlite3` and
`test_pool`, with at least 16 free slots, at `hello`, before the test
bundle runs.

12.6.2.9 The `Store` takes six arguments, `turn_compact_turns` after
`overflow_bytes`, at every call site. A count the tests choose to reach
compaction is a named constant whose comment says its writer chose it, as
`compact_small: 3`.

12.6.2.10 `db.snapshot` replies with one blob carrying `sha256` and `seq`;
no `db.chunk`, `SnapshotFetch`, `SnapshotHead`, `snapshot_keep`,
`snapshot_read` or `blob_take` is left, nor the strings
`substrate.piece_none`, `substrate.piece_size`, `substrate.snapshot_range`
and `substrate.snapshot_unknown`; `substrate.snapshot_digest`,
`substrate.cache_unknown` and `substrate.fill_desync` stay.

12.6.2.11 Constants stand in the frozen `constants` object; no line of the
file is over 79 columns, and its header paragraph was refilled with its
words unchanged.

12.6.3 Decided, not a finding.

12.6.3.1 Tests of the Python suite with no TypeScript port, by record:

12.6.3.1.1 `test_wal_left`, approved by the maintainer: it cannot apply to
the SAH pool, which has no WAL (the browser's databases set only
`foreign_keys = ON`); nothing is built for it.

12.6.3.1.2 The names of the Python substrate that the TypeScript twin does
not use: `substrate.journal_mode` and `substrate.wal_left`, there being no
WAL; `substrate.key_refused`, which has no JavaScript case;
`substrate.transaction_none`, recorded as unused with no reason given (its
Python branch is a candidate of task 1.14, 11.6). The Python tests that
expect them have no port.

12.6.3.2 Accepted differences between the twins, which the port follows:

12.6.3.2.1 `kv_check` never removes a live sink file, departing from
Python's `test_file_moved`.

12.6.3.2.2 SQL: the parameter count is checked by `prepare`
(`substrate.params_count`); several statements are caught after running
(`substrate.statement_many`) and rolled back; empty SQL throws where
Python accepts it.

12.6.3.2.3 Numbers: past 2^53 they give `substrate.integer_range`; a top
level key "12" is `header_normal` in TypeScript but `key_digits` in
Python; Python stores doubles above 2^53, which the TypeScript store
refuses with `substrate.integer_range` (approved).

12.6.3.2.4 The reference string class excludes exactly Python's
`str.isspace` code points, tested, JavaScript's `\s` differing from
Python's on U+001C to U+001F; D18, the default that a reference string's
key part holds no white space.

12.6.3.2.5 `forward_done` checks that a reply's `seq` is `since + 1`,
skipped for `db.create` and `db.drop`: the coordinator's correction of an
earlier check against `seq_get(db)`, which failed whenever local writes ran
ahead of the line in flight.

12.6.3.2.6 D1, the default that a new database starts at `seq` 0 and
`db_create` leaves it 0, `db.create` carrying `since` 0 and `db.drop` the
database's `seq`, the reply's `seq` check skipped for both.

12.6.3.2.7 Forwarded values are copies; `db.create` and `db.drop` lines go
at once, the others after the outermost commit; a rollback discards the
pending lines and holds; with no forward function set, the store throws
`substrate.forward_unset` inside the transaction.

12.6.3.2.8 Restore and load import `<file>-restore`, check it read only,
then import it over the live copy; a leftover throws
`substrate.restore_left`.

12.6.3.2.9 Withdrawn: VACUUM renumbering the rowids of tables without
INTEGER PRIMARY KEY on the browser only is a candidate of task 1.24
(11.16.6.9).

12.6.3.2.10 A forwarded `turn.append` applied by `operation_apply` goes
through the private `#turn_add` and never compacts, so that one forwarded
line cannot compact twice (class B, built; options a) to c) were offered,
and the maintainer has not approved it).

12.6.3.2.11 The cache is a fixed set of OPFS files held open with sync
access handles, each file's first 64 bytes the stored SHA-256 in hex or
zeros when free, a sink handle `sink/<n>` in memory only, and
`substrate.cache_full` when no file is free (rejected: a file per value,
whose creation is asynchronous; a SQLite cache database; SAH pool files).
The slots and the pool are fixed at initialization (accepted).
`sink_close` of a short blob frees its file and returns the hash of the
bytes received, without throwing (alternatives named: keep it until
`kv_check`; throw).

12.6.3.2.12 The store's departures from `API/ts/substrate.d.ts`, accepted:
the constructor `(sqlite3, pool, cache, root, overflow_bytes,
turn_compact_turns)`, `forward_set(fn, full)` for the name form of D27
(the default that one `names_full()` in the worker chooses the line name
form), and `handlers_register(register)`.

12.6.3.3 The step script: the 322 byte step script of
`ts/test_substrate.ts`, a measured SHA-256 vector that is never run, keeps
its text `engine.log(1, ...)` (approved by the maintainer), though a
script's `engine.log(text)` now takes no level. The other copies of the
step script, 319 bytes without the level, in `ts/test_script.ts` and
`ts/test_tools_browser.ts`, compare their digest with `utility.sha256_hex`
of their own bytes; a measured constant for them is owed to the testing
phase, "if a constant vector is wanted back".

12.6.4 Open, for the maintainer.

12.6.4.1 None recorded for this file. `json_canonical` refusing doubles
above 2^53 with `substrate.integer_range`, where Python stores them, was
once left as "the maintainer's call"; the maintainer then approved it with
the other class B items of that job, so it is decided (12.6.3.2.3,
11.16.4.15).

12.6.5 Candidates.

12.6.5.1 `test_create_failed` of `python/test_substrate.py` was recorded,
with `test_wal_left` and `test_kill_between`, as "not portable", its proof
left to the browser test. No later record names a port or a rung for it,
and the plan exempts only `test_wal_left`. Check for a ported test, a
rung, or a record that decides it; no class or severity was given.

12.6.5.2 A reviewer recorded that `ts/test_substrate.ts` compares a
literal message, not its `i18n` text, without naming the test. Check every
comparison against 12.6.2.5.

12.6.5.3 Values kept from the deleted transcripts. When the file was
written its digests and sequences were recorded from transcripts that were
later deleted; then the comments citing them were reworded, the values
kept, the digests not recomputed, and identifiers still saying "recorded"
left (`test_recorded_replay` is in both files). The Python twin has the
same record for its `seq` start state and for `_DESYNC_MESSAGE` compared as
a literal (task 1.14's).

12.6.5.4 No state left between tests: a reviewer of the TypeScript core
recorded tests that leave handlers, ring lines and a scheduled step in the
thread's live state, naming no file; check this file against 12.6.2.7.

12.6.5.5 Module level constants outside `constants`, and fields without
their comment, were recorded for the TypeScript AI side without naming the
file; task 1.24 has the point for `ts/substrate.ts`; check this file
against the same rule.

12.6.6 Requests go to task 1.24 (11.16), the steward of
`ts/test_substrate.ts`.

12.6.6.1 Seam with task 1.24's own candidate: `db_unload` and `db_load`
refuse with `substrate.forward_pending` while forwarded lines of the
database are unanswered, a refusal between the AI API and a database that
no plan asks for. A test of this file that asserts that refusal moves with
its fix, in the same change, by task 1.24.

12.6.6.2 Seam with task 1.19 (11.11): the kill probes are called by the
rung "stage 6: kill between file and row"; a change of their names or
signatures is made on both sides, as section 8 says for seams.

## 13 Verifiers

13.1 Tasks 1.31 to 1.39 are fresh agents and edit nothing outside
`tmp/review/`. Each reads the reports of its areas, `git diff <baseline> --`
their files, and every file an area created (its report's item 5), which
`git diff` does not show while untracked, and for every fix and every
declined request states CONFIRMED or REJECTED with its reason. Like every
agent, a verifier takes the project rules from its context and does not
open the project rules file. It checks that:

13.1.1 the fix does what its finding says and meets the statement of this
file or the stub;

13.1.2 it reverses no accepted item (5.1) and decides no open question
(5.2);

13.1.3 it adds nothing unmotivated (6.1) and changes no public interface
(6.2);

13.1.4 it breaks no project rule and no rule of section 3, and its test
moved with it (6.4);

13.1.5 its strings are in a fragment, and each seam it changed changed on
both sides, or on neither (8.6.7);

13.1.6 a declined request cites an item or rule that does decide it;

13.1.7 the items its owner marked met in the definition of done hold, by
sample.

13.2 The groups:

13.2.1 task 1.31: tasks 1.9, 1.10, 1.11;

13.2.2 task 1.32: tasks 1.12, 1.13;

13.2.3 task 1.33: tasks 1.14, 1.15;

13.2.4 task 1.34: tasks 1.16, 1.17, 1.18;

13.2.5 task 1.35: task 1.19;

13.2.6 task 1.36: tasks 1.20, 1.21, 1.22, 1.23;

13.2.7 task 1.37: tasks 1.24, 1.27;

13.2.8 task 1.38: tasks 1.25, 1.26;

13.2.9 task 1.39: tasks 1.28, 1.29, 1.30.

The requests of tasks 1.1 to 1.8 are verified with the owners that applied
them.

## 14 Closing and formatting

14.1 Task 1.40, the closing agent, after every writer and verifier:

14.1.1 merges every fragment into `i18n/en-US.json`, one flat object, keys
sorted by code point, ASCII, as the file stands at the baseline. Identical
additions from two fragments merge once. A name given two different texts,
or written by a task that does not own it (6.5), is left as at the baseline
and becomes a request to its owner. A removed name that a call still uses is
kept and reported;

14.1.2 checks again every literal `i18n` call against the merged file, with
its placeholder count, and every entry for a call outside the tests; a
mismatch is a request to the owner;

14.1.3 checks again, on the changed tree, the census items of 12.1 on the
whitelist, the two `tsconfig` lists and the test module tables, for every
file the review created or renamed, a miss being a request;

14.1.4 checks each REJECTED fix's resolution, and every request resolved
"applied" after its area's verifier ended, as 13.1 says;

14.1.5 checks that every request with a `Seam:` line has both sides applied
or neither; a half applied seam is severity 1 in `summary.md` and in the
postmortem;

14.1.6 runs the lock check of 15.2. When 14.1.1 to 14.1.5 made requests, or
the check prints a lock name, the coordinator runs one more round of 9.3
and then this task again, before 14.2 starts;

14.1.7 writes `tmp/review/maintainer_edits.md` (every report's item 9),
`tmp/review/open.md` (items 10 and 11) and `tmp/review/summary.md`: counts
by class, severity and area; every finding not fixed, named `<task id>
4.<n>`, with one sentence and its reason.

14.2 Task 1.41, the formatter, after the closing agent, by the project
rules:

14.2.1 checks with `git status --short` that only the review's changes are
in the tree, beside what 9.1.2 recorded;

14.2.2 stages the whitelisted files the review changed, the one staging the
project rules allow, so the formatter's own changes stay apart;

14.2.3 runs `python3 python/reformat.py`, writes `git diff` to
`tmp/review/format_1.diff`, runs it again, writes `tmp/review/format_2.diff`,
and compares the two with `cmp`; a second run that changes anything means
the formatter is not stable, which the postmortem tells the user;

14.2.4 reads the formatter's changes; one it believes wrong may be reverted
and the edit made by hand, as the project rules allow, and is reported;

14.2.5 commits nothing and unstages nothing. The PowerShell files are
Windows's to format and are not formatted here; the ones the review changed
are owed to `powershell/test_lint.ps1` (15.4);

14.2.6 does not revert the formatter's changes to the files of 6.10 or 5.6
that the whitelist covers, such as the stubs under `API/` and
`python/bootstrap.html`, but lists them for the maintainer, as an earlier
job recorded that the formatter may rewrite them.

## 15 The coordinator

15.1 The coordinator writes only its log, the directories of 9.1.3 and the
`mv` of 8.1; it launches, checks and records, and edits no source and no
report. It reads the reports, not the agents' transcripts. It launches
every agent as the general purpose type, and loads SendMessage and TaskStop
with ToolSearch before it first needs them. A coordinator short of context
ends with its log current; a new coordinator session continues from the log
and `tmp/review/`.

15.2 After every agent ends it runs the lock check, `find . -path ./.git
-prune -o -path ./build -prune -o -name '*.T1.*' -print`, which may show
only running agents' locks; a lock of an ended agent is stray, and the
coordinator resumes that task to release it. It lists `tmp/review/inbox/*/`;
runs `git status --short`, which shows nothing staged before 14.2; and
records in its log, with the time from `date '+%d_%H%M'`, the agent's reply
in short and what the checks showed.

15.3 The prompts.

15.3.1 Phases 1, 3, 4 and 5; a verifier's entry is given as "13.1 and
13.2.<m>", the closing agent's as 14.1, the formatter's as 14.2:

```text
You are task <id> of the code review in /home/t/xstation.js. Read
REVIEW_EXECUTION.md sections 1 to 3 and 5 to 10 and your entry, section
<n>, and work as they say; read section 4 by the search of 5.5. Task ids
1.x of the file are <k>.x here. Baseline: <hash>. Phase: <1, 3, 4 or 5>.
Your lock suffix is .T<id>, your inbox tmp/review/inbox/<id>/, your report
tmp/review/report/<id>.md. Reply in at most 15 lines.
```

15.3.2 Phase 2, sent by SendMessage to the agent, or as the prompt of a
fresh agent under the same task id:

```text
Phase 2 of task <id>. Baseline: <hash>. Task ids 1.x of the file are <k>.x
here. Read your report (its lock name if it is not published), work every
request in tmp/review/inbox/<id>/ as REVIEW_EXECUTION.md 8.6.4 to 8.6.7
say, then update items 5 to 7 and 12 of the report, publish it, and reply
in at most 15 lines. A fresh agent reads REVIEW_EXECUTION.md sections 1 to
3 and 5 to 10 and its entry, section <n>, first.
```

15.4 The postmortem, in the log and in the conversation with the log's
link, only when every agent has ended and every task is ready for review:
every unfinished task and every lost agent; every finding not fixed, each
with one sentence; every half applied seam; the open questions met; the
proposed edits to `API/`, `README.md` and this file; the values owed to the
testing phase; the PowerShell files changed, owed to
`powershell/test_lint.ps1` on Windows; the formatter's stability and the
changes of 14.2.6; screenshots, none, since nothing runs (17.3.4); and the
A and B items of the requests the review served.

15.5 Tasks, sections and verifiers:

```text
task  section  verified by    task  section  verified by
1.1   12.1     -              1.22  11.14    1.36
1.2   12.2     -              1.23  11.15    1.36
1.3   12.3     -              1.24  11.16    1.37
1.4   12.4     -              1.25  11.17    1.38
1.5   12.5     -              1.26  11.18    1.38
1.6   12.5     -              1.27  11.19    1.37
1.7   12.5     -              1.28  11.20    1.39
1.8   12.6     -              1.29  11.21    1.39
1.9   11.1     1.31           1.30  11.22    1.39
1.10  11.2     1.31           1.31  13.2.1   -
1.11  11.3     1.31           1.32  13.2.2   -
1.12  11.4     1.32           1.33  13.2.3   -
1.13  11.5     1.32           1.34  13.2.4   -
1.14  11.6     1.33           1.35  13.2.5   -
1.15  11.7     1.33           1.36  13.2.6   -
1.16  11.8     1.34           1.37  13.2.7   -
1.17  11.9     1.34           1.38  13.2.8   -
1.18  11.10    1.34           1.39  13.2.9   -
1.19  11.11    1.35           1.40  14.1     -
1.20  11.12    1.36           1.41  14.2     -
1.21  11.13    1.36
```

A verifier's entry is 13.1 with its group of 13.2.

## 16 Designs not built

16.1 A verification run, for the maintainer to turn on. After Phase 3 and
before Phase 4, one agent runs, from the checkout's top, with
`PYTHONPYCACHEPREFIX=build/pycache`, each Python unit module of
`python/test_all.py`'s `_MODULES` that a review change touched, as
`python3 -X dev -m unittest <module>` from `python/`, under a timer of 600 s
each, a default chosen by the writer of this file; the first failure stops
it, and its output goes to `tmp/review/run.txt`. A failure becomes a request
to the owner and one more round of 9.3. Nothing TypeScript, no wire or
browser test and no `test_posix.py` run, as those need `tsc`, ttyd, Chrome,
or rewrite the tree. Not built because 7.1 holds until the maintainer lifts
it.

16.2 A register phase at review time, agents gathering every decision
before Phase 1 and every owner reading it. Not built: its sources are gone,
and the register was built into this file before they were removed (section
4 and the Decided parts of sections 11 and 12), so no agent waits for it.

16.3 One verifier per area, 22 agents. Not built: the groups of 13.2 cover
the same with fewer launches and the same rules.

16.4 Agents applying their proposed `API/` edits with the code. Not built:
`API/` is the maintainer's, and the API comes before the code.

## 17 The requirements of the requests

17.1 The request for this file, verbatim but for the name of the project
rules file, which the project rules forbid outside itself, of 2026-10-21:

```text
write REVIEW_EXECUTION.md which is a plan for the administrator agent to dispatch the entire review after the tmp/ dir has been deleted and existing planning docs removed. that will require REVIEW_EXECUTION.md  this requires a self contained description of the different areas each agent will review and what they will be expecting to find.  no external references outside [the project rules file] allowed. (it remains.)
```

The request for the review itself, of the same day, is quoted in 4.1.

17.2 D, satisfied without modification.

17.2.1 Of the request for this file: a plan for the administrator agent to
dispatch the entire review (sections 9 and 15, with the prompts of 15.3 and
the table of 15.5); it works after `tmp/` and the planning documents are
removed, since no step reads them and Phase 0 makes `tmp/` again (1.2, 1.5,
9.1); a self contained description of each area and of what its agent
expects to find (sections 2 to 4, and the Expected, Decided, Open and
Candidates parts of every entry of sections 11 and 12); the project rules,
the one reference the request allows, are called "the project rules"
without the name of the file that holds them, as the project rules forbid
that name outside itself; the references to the tree under review are the
B item of 17.3.6.

17.2.2 Of the request for the review: the review compares the code that
should be there with the code that is (5.3, 10.4); judgement calls are not
revisited and every AI assumption is accepted (1.4, 5.1, 5.3.4, 5.3.5);
undocumented deviations, mistakes and shortcuts are its three classes
(5.3); a lot of agents, 41 tasks (sections 11 to 14); files are locked by
renaming (8.2); no agent waits on another but for the finished work of 8.8;
an agent coordinator runs it (section 15); the earlier plan of the review
was reviewed by another agent and updated from its feedback before this file
was made from it, and this file was checked against those sources by four
reviewing agents before their removal and corrected from their findings.

17.3 B, modified with cause, not confirmed:

17.3.1 "have the agents decide what it really means to be done and then do
it": each agent decides its definition of done (10.4) and works to it, but
within three limits the rules impose: it runs nothing (7.1), it changes no
public interface and proposes such changes instead (6.2), and it decides no
question left to the maintainer (5.2).

17.3.2 "things that are simply incorrect or mistakes that can be fixed":
some broken things are questions the maintainer has not answered, such as
the hooked template test that the formatter broke (11.10), the mode of
`test_posix.sh` (11.2) and the long lines the formatter cannot wrap (6.11);
the review lists them and does not fix them, because fixing one chooses an
option or reverses a decision.

17.3.3 The earlier jobs' working rules are departed from: 7.2 adds the read
only commands `cmp`, `diff`, `find`, `git status` and `git diff` to their
`mv`, `mkdir -p`, `ls`, `grep`, `wc` and `test`, so that agents can check
their own changes; 14.2.2 stages files, which those rules forbade and the
project rules allow before a formatter run; 10.6 puts fragments under
`tmp/review/i18n/` with an `add`, `reword` and `remove` shape, where the
earlier fragments could only add.

17.3.4 The project rules ask for links to screenshots in every postmortem.
Nothing runs in this review (7.1), so none can be made, though tasks 1.29
and 1.30 may change what the page shows.

17.3.5 The pool of at most eight agents at once (9.2) is the writer's
choice, a guard against the HTTP 429 limits that stopped agents of earlier
jobs; while the pool is full, a ready agent waits for a slot.

17.3.6 "no external references outside [the project rules file]": this file
names the tree it reviews throughout, and the stubs under `API/` stay the
authority for public names and signatures (1.5.3, 1.6, 6.2) instead of being
restated here. They are taken as part of the code under review, which
remains, not as external references. `API/README.md` still names a removed
planning document (1.5.4).

17.3.7 "a self contained description": the register of section 4 and the
Decided parts of sections 11 and 12 were carried over by agents from the
plans and logs before their removal. A decision the transfer missed cannot
be found after the removal; an agent that meets its code will file it as a
finding, which revisits a judgement call against the request for the review
(1.4). Each finding's Searched part (10.3.4) shows the maintainer what was
searched, so such a finding can be declined when the diff is reviewed.

17.4 A, unsatisfied without cause: none.

17.5 Questions for the B items:

17.5.1 Running during the review:

17.5.1.1 a) nothing run but the formatter (built);

17.5.1.2 b) the verification run of 16.1 after Phase 3;

17.5.1.3 c) each owner runs its Python unit modules after its fixes.

17.5.2 Questions left to the maintainer that the review meets:

17.5.2.1 a) listed, not decided (built);

17.5.2.2 b) the review builds the option a record recommends, and marks it
for the maintainer;

17.5.2.3 c) the maintainer answers them before the review is launched.

17.5.3 Changes to public interfaces:

17.5.3.1 a) proposed with their whole design, not made (built);

17.5.3.2 b) made in the code and the stub together, each recorded as an
API addition (4.5).

17.5.4 The earlier working rules of 17.3.3:

17.5.4.1 a) the read only additions, the formatter's staging and the new
fragments, as written (built);

17.5.4.2 b) the six earlier commands only, the formatter run left to the
maintainer, and fragments that only add.

17.5.5 Screenshots:

17.5.5.1 a) none, since nothing runs (built);

17.5.5.2 b) the verification run of 16.1 extended to the browser test's
PNGs, which needs ttyd and Windows Chrome and the maintainer's leave to run
them.

17.5.6 The pool:

17.5.6.1 a) at most eight at once, lowered after a 429 (built);

17.5.6.2 b) no cap: every ready agent is launched at once;

17.5.6.3 c) a number the maintainer names.

17.5.7 The stubs under `API/`:

17.5.7.1 a) read as part of the tree, the authority on public names and
signatures (built);

17.5.7.2 b) this file restates every public name and signature, and the
stubs are read only as code under review.

17.5.8 Decisions the transfer missed (17.3.7):

17.5.8.1 a) the review runs from this file alone, and the maintainer
declines such findings when reviewing the diff (built);

17.5.8.2 b) the maintainer keeps the removed documents outside the tree for
the review's agents to search, which the request for this file excludes;

17.5.8.3 c) U findings are reported and not fixed in a first pass; the
maintainer marks each one, and a second pass fixes those marked.

17.6 C, modified by the maintainer's later request: the review's request
asked that the plans and the logs be read, and that deviations be found
against what reading the planning documents leads one to expect. The
request for this file removes those documents: they were read by the
agents that wrote the earlier plan of the review and this file from it,
and the review measures against this file (5.3.1), which carries what
they stated (17.3.7).
