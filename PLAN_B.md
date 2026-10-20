# PLAN_B: what the hyperposition-engine job carries forward

## 0 Scope and authority

0.1 Written on 2026-10-19 by the coordinator session whose log is
`tmp/tasks_19_2016.md` (task 1.13), at the user's request. Sources: the
maintainer's two messages of that day, kept verbatim in section 1, and the
review document `tmp/PLANNING_UPDATE.md`. That review's one-off
instructions to the earlier coordinator are not carried: the log
corrections, the order of work and the per-task work orders. Only what stays
true after the job is carried.

0.2 Readers: the maintainer, and every later session or agent that writes
code for `hyperposition-plan.md`.

0.3 Order of authority: the maintainer's words in section 1, then this
file's section 2, then `hyperposition-plan.md`, then `API/`, then `DATA/`.
Agents do not edit the plan, `API/` or `DATA/`; section 7 lists the edits
the maintainer is asked to make so those files agree with this one.

0.4 Section 4 holds defaults the maintainer has not confirmed. They are used
as written until answered, and listed again in section 10.

0.5 Units: MB means MiB, KB KiB, GB GiB, always.

## 1 The maintainer's messages, verbatim

1.1 Received at 20:51:

```text
please incorperate this feed back from the maintainer """have max 10MB per blob. max 10MB combined total blobs+json. max 100MB for any JSLB queue. soft limit of1GB for all the DBs using heuristics. don't worry about too many DBs. the AI API needs a plan to live within the browsers cache size for fast MCP operations. it needs db admin commands to know when and how to compact the set of DBs it is operating. this would be a nice problem to have. remove db table protection rules like the protextion on _ or _settings. the sql rules are not a sufficient security boundry so they are not being set up as such. remove all protections from any db that are being added. just use the real TAP api and forget the test code. please don't forget verbose level 2. rename the verbose fn that runs commands "exec" """ and this feedback from a reviewer """
3.2 Invented values. These are the 120-second timeouts in the Python test runner and in the browser connection code (nobody specified a length), plus the guessed log times.

3.3 The formatter's file list was not updated. New TypeScript, test-output, seed-script and HTML files were never added, although new source files must be added when they are created.

3.4 The code can't be loaded. The combined strings file i18n/en-US.json was never assembled, so every engine module fails as soon as it is imported.

3.5 Fallbacks and "just in case" code, against the no-fallbacks rule:

the main loop prepares the root directory itself if the preparation step was skipped
closing a log that isn't open is quietly accepted
an unreachable return 0
output flushes that have nothing to flush
a duplicate directory creation
type-check branches that can never run
a second, hand-written JSON encoder in bootstrap's error path
two error messages for conditions that can't happen
3.6 Names that don't follow the two-English-words rule: _State in nine modules, Loopback and Recorder each have one word, and json_media_is has three.

3.7 A silent substitution. The new connection test needs an echo handler that nobody was assigned to write. Meanwhile the test runner still runs the old design's connection test in place of the new one.
"""
```

1.2 Received after 20:59 and before 21:11 (not measured):

```text
write PLAN_B.md with all the updates from the last two message from the maintiner and the PLANNING_UPDATE.md that need to be rememeberd going forward. keep these last two messages verbatum. """    i want a tap JS and PY producer custom written and a PY consuper custom written following the tappy apis but just implement the code you need in local tap-producer/tap_producer tap-consumer/tap_consumer modules and have tests for them and start by running those tests before running the rest. have a way to test expected failure, so you can say you expect a suite to fail a certain way and consider that success. then the tap producers cant be exercised to handle failure correctly in all the ways they have to. MB is MiB always. add the db admin design/MVC. don't download tappy, it can be tested later. use sane timer defaults."""
```

## 2 The maintainer's decisions

Each item states the decision, then how it is built. A detail marked
READING is the coordinator's reading of the words; section 10 asks about it.

### 2.1 Sizes

2.1.1 A blob is at most 10 MiB: the setting `blob_max` is 10485760.

2.1.2 A line and its blobs together are at most 10 MiB. A new setting,
`message_max` 10485760, covers the line's bytes including its CR plus the
`s` of every blob.

2.1.3 Any JSLB queue holds at most 100 MiB. A new setting, `queue_max`
104857600, covers the bytes held; a held line counts its JSON text in UTF-8
plus its blob sizes.

2.1.4 `line_max` stays 1048576. `overflow_bytes` stays 131072: a blob larger
than that still streams to the cache.

2.1.5 Both decoders take `message_max` after `blob_max`:
- Python: `LineDecoder(line_max, blob_max, message_max, overflow_bytes,
  sink_make)`.
- TypeScript: `new LineDecoder(line_max, blob_max, message_max,
  overflow_bytes, sink)`.

When a line ends, a message whose line length plus blob sizes exceeds
`message_max` is refused before any blob byte is buffered. The refusal is
`WireError` with the name `jslb.message_over`.

2.1.6 Where each limit is enforced:
- `wire.ts` refuses to post a message over `message_max`.
- `TaskQueue` throws `queue.queue_over` when holding a line would exceed
  `queue_max`.
- The `FrameQueue` of `wire.ts` throws `wire.queue_over` on the same
  condition.
- So does the replication queue of the worker.
- The Python server holds no queue; it dispatches one line at a time.

2.1.7 Plan 3.8's self-contradictory memory bound is settled by 2.1.2: the
memory per message is bounded by `message_max`.

2.1.8 Plan proofs whose sizes exceed the limits change:
- The 16 MiB `kv.put`, `kv.get` and round trip use the largest message that
  fits, `message_max`, which holds a blob of `message_max` minus its line's
  length. A message one byte larger must be refused.
- The 128 MiB measurement of ttyd's resident size sends 128 MiB as messages
  that each fit, one after another, never holding more than `queue_max`.

### 2.2 The database soft limit and the administration commands

The maintainer asked to build this design ("add the db admin design/MVC").
READING: "MVC" is read as the minimal code that implements the design, not
a model, view and controller split; plan 5.1 says the design is not MVC.

2.2.1 Goal: the AI worker keeps a working set of databases in OPFS small
enough for fast MCP operations. The server keeps every database as the
source of truth (plan 6.7), so the browser's set can shrink without losing
anything.

2.2.2 Measurement is by heuristics, never by a quota call:
`navigator.storage.estimate()` is asynchronous and would break the one
synchronization tool.
- A database's size is `page_count` times `page_size`, plus the `size` of its
  `_kv` rows whose value is in the cache (`data` NULL).
- Its reclaimable space is `freelist_count` times `page_size`.
- The total is the sum over the databases open in the AI worker.
- A new setting, `db_soft_bytes` 1073741824, is the soft limit. A soft limit
  refuses nothing.

2.2.3 Four browser tools, each one substrate operation behind one MCP tool:
- `db_stats {}`, read only. For each open database it returns `name`,
  `bytes`, `free_bytes`, `cache_bytes` and `seq`, then `total_bytes`,
  `soft_bytes` and `over`.
- `db_compact {db}` runs `VACUUM` on the browser's copy and returns the bytes
  before and after. It is not a modifying operation: the content and `seq`
  are unchanged, and nothing is forwarded.
- `db_unload {db}` closes the browser's copy and deletes its OPFS file and
  the cache files that only it references. The server copy stays and nothing
  is forwarded. A later operation on that database is an error naming
  `db_load`.
- `db_load {db}` fetches the server's copy with the existing `db.snapshot`
  line and opens it, the same way the start replacement of plan 6.8 does.

2.2.4 After each turn the agent compares `total_bytes` with `db_soft_bytes`.
When over, it adds one system message holding the `db_stats` result to the
next provider request. The AI, as database administrator, decides what to
unload, compact, drop or `turn_compact`. There is no timer, because time
stops. Nothing is evicted automatically except the existing `_files` browser
tier (`files_browser_bytes`, plan 6.7).

2.2.5 At start, the browser replaces a differing file only for the databases
it holds. The others stay unloaded until `db_load`.

2.2.6 Nothing limits the number of databases ("don't worry about too many
DBs").

2.2.7 Builders:
- the substrate side: `ts/substrate.ts` (task 1.6.1);
- the four tools: `ts/tools_browser.ts` (1.7.5);
- the over-limit message: `ts/agent.ts` (1.7.6);
- the setting: `settings.json` and the settings checks in both languages.

The server side is unchanged in v0, because the server evicts nothing (plan
6.7).

### 2.3 No protections

2.3.1 SQL rules are not a security boundary, so nothing is built as one. No
substrate, engine handler or tool refuses a write to any table or database:
- no authorizer refusal of `_` tables or of `_settings`;
- no refusal in `operation_apply`, `kv_put`, `kv_delete` or `turn_append`;
- no enforcement of the fixed schemas of `_files`, `_preferences` or
  `metaverse`.

2.3.2 Tests that prove a refusal are deleted, with their `i18n` names. The
analyst prompt no longer says such tables refuse writes.

2.3.3 Plan 6.8's "`_settings` is written by the server from the file and
never by the browser" stays as a description of what the code does, with no
enforcement.

### 2.4 TAP

2.4.1 Custom code, following tappy's APIs and implementing only what the
engine needs:
- a Python producer;
- a TypeScript producer;
- a Python consumer.

tappy is not downloaded. Compatibility with the real tappy is tested later.
The producer and consumer have tests of their own, and those tests run
before every other test: first in `python/test_all.py`, first in the page's
`ts/test_all.ts`.

2.4.2 READING: "tap-producer/tap_producer tap-consumer/tap_consumer" names
the modules `tap_producer` and `tap_consumer`, because a hyphen is not legal
in a Python module name or a TypeScript namespace name. The files:
- `python/tap_producer.py`, `python/tap_consumer.py`;
- `python/test_tap_producer.py`, `python/test_tap_consumer.py`;
- `ts/tap_producer.ts`, `ts/test_tap_producer.ts`.

They replace these, which are removed once the new files land:
- `python/tap/producer.py`, `python/tap/consumer.py` and their two tests;
- `ts/tap.ts` and `ts/test_tap.ts`.

`ts/unittest.ts` stays as the TestCase harness.

2.4.3 tappy's names that are followed, recalled from tappy's documentation
and to be checked against tappy when it is tested:
- producer: `TAPTestRunner`, a `unittest.TextTestRunner` with the setters
  the engine needs, such as `set_stream`; and `Tracker` with `add_ok`,
  `add_not_ok`, `add_skip`, `set_plan` and `generate_tap_reports`;
- consumer: `Parser` with `parse_text` and `parse_line`, yielding the line
  kinds `Result`, `Plan`, `Diagnostic`, `Bail`, `Version` and `Unknown`;
- also the stats plan 7.2 asks of the consumer: plan, pass, fail, skip, and
  whether the stream is well formed.

The TypeScript producer uses the same names inside the namespace
`tap_producer`.

2.4.4 Expected failure: a test can declare that a suite must fail in a
stated way, and the test passes when the suite fails exactly that way. The
producers must be exercised on every way a run can fail:
- Python:
  - a failing assertion, and an exception raised in a test;
  - a failing `subTest`;
  - errors in `setUp`, in `tearDown`, and in `tearDown` after a failure (two
    outcomes of one test);
  - errors in `setUpClass`, `tearDownClass` and `setUpModule`;
  - `expectedFailure` and an unexpected success;
  - a skip;
  - failfast ending the run with `Bail out!`;
  - a module that does not load.
- TypeScript: the same list minus `subTest` and the class and module
  fixtures, which its harness does not have.
- This replaces the nested fixture run of `python/test_all.py --nested`.

2.4.5 The plan's stream shape stays (plan 8.1): one plan per language per
run, then each module as a four-space-indented block with its own plan and a
parent `ok N - <module>` line. The line grammar is the default D12 of
section 4.

### 2.5 verbose

2.5.1 The function that runs commands is `verbose.exec`. The name is the
maintainer's own identifier, so it overrides the two-word rule. Its `i18n`
names are `verbose.exec_run` and `verbose.exec_exit`.

2.5.2 Level 2 is built. READING of "raw with verbose flags passed on":
`exec(level: int, argv: list[str], argv_verbose: list[str]) -> int`.
- Level 0 runs `argv` quietly, with its output passed through.
- Level 1 runs `argv` with Markdown-formatted progress.
- Level 2 runs `argv_verbose`, the caller's command line carrying that
  program's own verbose flags, and passes its output through raw.

The console's dash passes `[dash, "-v"]` as its verbose form.

### 2.6 Timers

2.6.1 Every timer has a sane default value. It is a named constant whose one
line comment says it is a default chosen by its writer.

2.6.2 The 120 s lengths already written stay as defaults. Every new timer
gets its writer's sane value, listed in the handoff.

2.6.3 The provider request uses `provider.timeout_seconds` (plan 4.1), and
`console_run` its `timeout_seconds` argument (plan 5.5).

## 3 Rules for all code

These came out of the review and stay in force.

3.1 TypeScript handlers:
- A handler returns a finished reply line built with
  `dispatch.reply_make(request, payload, blobs)`, a `Sleep`, or nothing.
- A wake line carries no `i`. A wake handler that owes a reply builds it from
  the original request line kept in its `state`.
- Every request a handler run submits is named in that run's sleep.
- `task_submit(line, owner?)` and `line_notify(line, owner?)` take an
  explicit owner.
- Replies on the http lane have `t` `http.request`.
- An arriving `error` line is a fault.
- Ids are one counter per queue, and no TypeScript module calls
  `dispatch.id_next`.

3.2 `Store.kv_put(ref, data)` takes bytes (`Uint8Array`, `bytes`). A string
is a cache file path in Python and a cache handle in TypeScript, never text.
Text is encoded with `TextEncoder` and read back with `TextDecoder`.

3.3 Tests:
- A test that expects an error compares the message with the
  `i18n(name, args)` text, never only a base class.
- A fixture reads `document` and other thread-bound globals in `setUp`,
  never at construction.
- No test enshrines the implementation's number where a recorded number
  exists.

3.4 Style:
- Every class and function identifier has two English words, private ones
  too; the maintainer's own identifiers are the exception.
- One comment line per construct, never two consecutive comment lines.
- No `isinstance` or `is None` branch whose only purpose is to narrow a type;
  use `cast` instead.
- `i18n` is always called with a literal name at the call site.

3.5 `bootstrap.py` owns the whole `hello` exchange; the main loop never sees
it. `bootstrap` calls `loop_prepare(root)` once, before `hello`, then
`loop_run(read_fd, write_fd, root)`.

3.6 Errors:
- A module with no handler for a case makes no branch for it.
- A JSON parse failure of any kind in a decoder is a `WireError`.
- A decoder fault is raised once, and the port closes.
- Lines completed before a fault are returned, and the fault is raised by
  the next feed.

3.7 Every message of an engine module goes through `i18n`. Each task's
strings go in a fragment `tmp/i18n/<task>.json`, and the fragments are
merged into `i18n/en-US.json`, a tracked source file.

3.8 Each new source file goes in `python/reformat_whitelist.txt` when it is
created. `.md`, `.json` and `.css` files are not added.

3.9 Working rules:
- Agents edit a file only under its lock name `F.T<task>` and rename it back
  when the edit ends.
- Agents run nothing; their commands are `mv`, `mkdir -p`, `ls`, `grep`,
  `wc` and `test`.
- Nothing is staged or committed except by the maintainer.

## 4 Defaults in force, not confirmed by the maintainer

From `tmp/PLANNING_UPDATE.md` section 3, with their state after section 2.

4.1 D1: a new database starts at `seq` 0, and `db_create` leaves it 0.
`db.create` carries `since` 0, and `db.drop` carries the database's `seq`.
The reply `seq` check is skipped for `db.create` and `db.drop`.

4.2 D2: request ids are one counter per thread queue, not per port.

4.3 D3: in TypeScript, `blob_make(data, key?, fields?, size?)` requires
`size` for a cache handle. The sender checks the bytes it reads against `s`.
Task 1.6.1 builds a synchronous `cache_read(handle, offset, length)` and a
sink that needs no SQLite.

4.4 D4: the deferred fault of 3.6, a streamed blob's file closed on any
exception, and `LineDecoder.idle()`. End of input when not idle is a hard
error.

4.5 D5: no `WireError.slug`. Tests compare `i18n` text from a table of
arguments for each vector.

4.6 D7: the Python decoder accepts an integral float for `b` and `s`.

4.7 D8: `XSJS_PROVIDER_KEY` is required only when `provider.scripted` is
false.

4.8 D9: a second `hello` after `system.restart` is a fault ending in Reload.

4.9 D10: `--main-loop` is refused outside debug mode and with the console
role. A repeated `--root` or `--main-loop` is an error.

4.10 D11: the API additions and plan departures of section 5 stay.

4.11 D12: TAP line grammar of `DATA/06_tap.txt`:
- the block plan `    1..N` comes first;
- no `# Subtest` line;
- bare method names;
- a failfast block is plan, points, diagnostics, `Bail out! failfast`.

4.12 D13: `verbose.tail_get(thread, count)` serves `ui` and `ai`.

4.13 D15: `devtools.page_open` waits, with a bound, on exactly
`net::ERR_CONNECTION_REFUSED`, the wait the old screenshot tool had.

4.14 D16: `tsc` is TypeScript 5.x. No `ignoreDeprecations`.

4.15 D17:
- the `tide` column stays;
- a universe's prompt is document `prompt` in the database named by the
  `universe` row whose `world` is `/metaverse/world`;
- the final text reply becomes the `ai.say` reply's `subtitle`.

4.16 D18: a reference string's key part holds no white space.

4.17 D21: no failure stacks are written to `_verbose`.

4.18 D22, HOLD: `python/bootstrap.html`, `python/xsjs_screenshot.py`,
`python/xsjs_screenshot_wsl.py`, the README lines on the old design,
`xsjs_stop.ps1`'s comment and `xsjs_status.ps1`'s `pgrep` stay untouched
until the maintainer decides.

4.19 D23: the `console.open` reply carries `token`, fetched from `/token`.

4.20 D24: wire limits are built after `settings_set`. The `hello` itself is
decoded with the maintainer's sizes: line and message at most 10 MiB, no
blobs.

4.21 D25: test-only exports stay.

4.22 D26: `utility` messages go through `i18n`, and `base64_decode` is
strict.

4.23 D27: the line name form is chosen by one `names_full()` in the worker.

4.24 D28: dotted tool names are passed to the provider unmapped; to be
checked at the first real provider run.

4.25 D29: `async` is not added to the synchronization audit.

4.26 D31: the Windows ttyd report step stays. The 1.7.7 `CMakeLists.txt`
declares CMake 3.12.0, so no policy flag is needed.

4.27 Settled by the maintainer and kept only as history:
- D6, by 2.1.7;
- D14, by 2.5;
- D19, by 2.3;
- D20, by 2.6.

## 5 API additions and plan departures, to accept or reject

5.1 `main_loop.loop_prepare(root) -> dict[str, int]`, called once per
process before `hello`. Every replacement main loop must define it.

5.2 `engine_system.tools_register(server, root, debug)`, and one
`handlers_register(...)` in every `engine_*` module.

5.3 `verbose`:
- Python: `log_open(root, ring)`, `log_close()`, `lines_put(thread,
  lines)`, `tail_get(thread, count)`, and `exec` (2.5).
- TypeScript: `verbose.LineRing`.

5.4 `Store.seq_get(db)`.

5.5 `queue`: `TaskQueue.task_submit(line, owner?)`, `line_notify(line,
owner?)`, `sink_attach(sink_set, settings_get)` and `VerboseBatch`.

5.6 `settings`: `ValueStore`, `Sender`, `sender_register`. Also the global
`i18n_format`.

5.7 `provider.key_set(key)` and `provider.key_get()`.

5.8 `wire`: `FrameQueue`, `ConsoleReader`, `WirePort.hello_receive`,
`message_take`, `close_take`, and a setter for the cache range reader (D3).

5.9 `http`: `HttpExchange`, `FetchArguments`, `HttpAnswer`.

5.10 The `unittest` run methods: the `TestCase` constructor with the method
name, `id()`, `run(result)`, `TestSuite.run(result)`, and the `TestResult`
members.

5.11 `mcp_stdio.stdio_run(register, stdin, stdout)`.

5.12 `LineDecoder.idle()`, and the `message_max` parameter (2.1.5).

5.13 `media.ImageCache` and `media.MediaExchange`.

5.14 `ConsoleView.open_request()`, `open_done(wake)`, `exit_done()`, and the
wake type `ui.console_reply`.

5.15 `jslb.blob_make` with `size` (D3).

5.16 Public helper names in `devtools.py` and `page_build.py`;
`page_build.main()` and `test_all.suites_run()`.

5.17 Replication:
- the internal line types `replicate.next` and `replicate.done`, which are
  not in `lines.d.ts`;
- replication done as page tasks over `Store.forward_set(fn)`, where plan 6.8
  says it is inside the substrate;
- the explicit owner route, which plan 10.10 lists as not built.

5.18 The server root layout `<root>/python/bootstrap.py` and
`<root>/i18n/`; plan 9 and `DATA/01` show `bootstrap.py` at the root.

5.19 The settings `message_max`, `queue_max` and `db_soft_bytes`; the tools
`db_stats`, `db_compact`, `db_unload` and `db_load`.

5.20 The modules `tap_producer` and `tap_consumer` in place of plan 7.2's
`tap/producer.py` and `tap/consumer.py` and plan 7.3's `tap.ts`.

5.21 `i18n` names beyond the work orders: `bootstrap.option_repeated`,
`bootstrap.main_loop_refused`, `main_loop.input_partial`, and the
`console_view.*` phase names.

## 6 Open questions found while writing the code

6.1 The `seq` of `metaverse` on a new root. `DATA/01` records 5: two
documents and three rows. The plan's rule also counts the `universe`
table's DDL, so the code gives 6, and the replay of the recorded sequences
desyncs on `metaverse`. Options:
- a) regenerate DATA with 6;
- b) an API addition that applies a fixed schema at `seq` 0;
- c) the `universe` DDL moves into the bootstrap script.

6.2 DATA files to regenerate with `DATA/transcripts_make.py`:
- 01: the name form with debug true; `seq`.
- 02:
  - ids per queue;
  - the prompt id `prompt`, not `prompt/analyst`;
  - `since` on `db.create`, and `seq`;
  - turn numbers: the generator counts `sql.run` and `kv.put` as turns;
  - the stored-block PNG (6.10).
- 04: the error text.
- 05: `since` and `seq`.
- 06: the TAP grammar, after 2.4.

6.3 The console opens once per page load in `console_view.ts`, while
`ConsolePort` is being made reopenable for open, close, exit, open.

6.4 `xsjs_stop.ps1`, `xsjs_status.ps1` and `powershell/test_lint.ps1` have
no UTF-8 BOM, which the PowerShell rule requires. D22 holds the first two.

6.5 Plan 9 puts `ttyd.log` in the server root. The start script writes it
under `%LOCALAPPDATA%`; a design that meets plan 9 is in log record 3.17.6.

6.6 `mcp_stdio.py` sets no `sys.pycache_prefix`. Options: `# noqa: E402`,
or a launcher.

6.7 The `universe` table does not make `world` unique, so the universe
prompt lookup can be ambiguous.

6.8 `engine_turn` builds canonical JSON with `json.dumps` and lacks the
substrate's private check that integers stay within 2^53.

6.9 `engine_sql` and `engine_turn` read `seq` before the lazily taken write
lock. This is sound only under the single process model.

6.10 The scripted provider's stored-block PNG is 852 bytes. `DATA/02`
records an 88 byte zlib level 9 PNG.

6.11 argparse still accepts `-h`, so a client `--url-arg -h` prints help to
the pty and exits 0.

6.12 The xterm `Terminal` constructor options were written from memory and
not checked against the pinned 5.5.0 typings. The resize path is
unreachable without a fit addon.

6.13 Who supplies the provider `Script` in the page is specified nowhere.

6.14 The Lookup Accelerator of the project rules was removed by the
maintainer's commit 168ac16. Updating it (old task 1.9.3) is held.

## 7 Edits proposed for the maintainer's files

7.1 Plan, sizes:
- 3.7: "`blob_max`, 10 MiB, and `message_max`, 10 MiB, a line and its
  blobs together".
- 3.8: "Memory per connection is bounded by `message_max`".
- 6.9: add `message_max`, `queue_max` and `db_soft_bytes`.
- 8.4, 8.7.3 and 8.7.6: the sizes of 2.1.8.

7.2 Plan, protections:
- 5.5: delete "The substrate's own tables and `_settings` refuse writes."
- 6.2: delete "`_settings` is immutable" as an enforced rule.
- 8.7.4: delete "a write to a `_` table or to `_settings` refused".
- 11: delete the `sql_run` guarding item.

7.3 Plan 2.3 and 7.2: `verbose.exec(level, argv, argv_verbose)`.

7.4 Plan 7.2, 7.3, 8.1 and 8.7.1: the TAP modules of 2.4.

7.5 Plan 3.9: ids per thread queue (D2).

7.6 Plan 6.8: `since` on `db.create` and `db.drop`, and a new database at
`seq` 0 (D1).

7.7 Plan 9: the root layout of 5.18.

7.8 Plan 10: a section with the design of 2.2.

7.9 `API/`:
- `python/verbose.pyi`: `exec`.
- `python/jslb.pyi` and `ts/jslb.d.ts`: `message_max`, `idle()`, `size`.
- `python/main_loop.pyi`: `loop_prepare`.
- `python/substrate.pyi`: `seq_get`.
- `python/engine_db.pyi`: `since`.
- `ts/lines.d.ts`:
  - `DbName` gets `since`;
  - `ConsoleOpenReply { token: string; }`;
  - `replicate.*` and `ui.console_reply`;
  - the `http.request` reply comment.
- `settings.json`: the sizes and new keys of 2.1 and 2.2.
- `mcp/tools.json`: `sql_run`'s description without the refusal, and the
  four tools of 2.2.3.
- `ts/tap.d.ts` and `ts/unittest.d.ts`: 2.4.
- `ts/boot.d.ts`: "`self.name` is empty on the main thread".
- `ts/utility.d.ts`: `json_text` is `JSON.stringify` with number checks.
- `ts/media.d.ts` and `ts/console_view.d.ts`: 5.13 and 5.14.

7.10 `DATA/`: the regenerations of 6.2.

## 8 Work remaining in this job, in order

8.1 Step 3, the seams, at most six agents at a time:
- 1.4.1 substrate: D1; the review's work order without its PRAGMA and
  `_settings` items; no authorizer refusals.
- 1.3.1 `jslb.py`: D4, D5, D7, 2.1.
- 1.3.3, 1.4.5 and 1.2.1: `verbose`, `exec` and level 2, D13, the four
  engine modules, `test_i18n.py`.
- 1.4.2 and 1.4.3: `dispatch.py`, `mcp.py`, `mcp_stdio.py`, the one-word
  test class names.
- 1.5.2 `queue.ts`: `queue_max`.
- A follow-up on landed Python files:
  - `bootstrap.py`: `exec`, `message_max`;
  - `main_loop.py`: `message_max`;
  - `engine_kv.py` and `engine_turn.py` and their tests, and
    `test_engine_sql.py`: protections removed;
  - `python/seed/prompt.json`: the refusal sentence removed.
- 1.3.5 and 1.2.4: settings in both languages.
- 1.2.3, 1.5.4 and 1.5.5: `error_overlay`, `utility`, `http`.
- 1.2.5 to 1.2.8: the Python tools.
- 1.3.2 `jslb.ts`.
- 1.5.3 `wire.ts`: D23, D24, 2.1.
- 1.2.2 with 1.2.9: the TAP modules of 2.4, `test_all.py`, the tsconfig
  lists.

8.2 Step 4:
- 1.6.1 `substrate.ts`, with 2.2's measurement;
- then 1.7.4 `mcp.ts`, 1.7.5 `script.ts` and `tools_browser.ts` with 2.2's
  tools, and 1.7.6 `agent.ts` with 2.2.4.

8.3 Step 5:
- 1.8.1 `page.ts`, `worker_ai.ts`, `boot.ts`;
- then 1.8.2 `test_all.ts`, 1.8.3 `test_browser.py` and 1.4.8 `test_wire.py`
  with the `echo` main loop.

8.4 Step 6:
- 1.9.2, the whitelist;
- 1.9.1, `i18n/en-US.json`;
- 1.9.4, a read-only reconciliation;
- 1.9.3 is held.

8.5 Then the maintainer's test run, TAP tests first (2.4.1).

## 9 Requirement classes

The requests weighed are:
- the user's request of the coordinated job (log `tmp/tasks_19_1413.md`,
  1.1);
- the resumption (`tmp/tasks_19_2016.md`, 1.11);
- the two messages of section 1;
- the project rules as they bear on the job.

9.1 D, satisfied without modification:
- the job is run as a coordinator with many agents;
- nothing is run, built or tested between handoffs or at all;
- files are locked by renaming for each edit, and no lock remains between
  waves;
- nothing is staged or committed by an agent;
- authorship is ascribed to no non-person;
- the lost agents are recorded and their tasks resumed;
- this file keeps the two messages verbatim.

9.2 C, confirmed withdrawn or modified by the maintainer:
- the plan's stage order, set aside by "write everything first and stop
  before testing";
- the database protections (D19 and the PRAGMA allow list), withdrawn;
- downloading tappy, withdrawn;
- the bespoke TAP runner, replaced by the custom tappy-shaped modules;
- the invented timer values, replaced by sane defaults (2.6);
- "MB" fixed as MiB;
- the database administration design, built rather than left as a door;
- D6 and D14, settled.

9.3 B, unsatisfied or modified with cause and not yet confirmed:
- the defaults of section 4;
- the API additions and departures of section 5;
- the READINGS of 2.2 ("MVC"), 2.4.2 (module names), 2.4.3 (tappy names
  from memory) and 2.5.2 (`argv_verbose`);
- 1.9.3, held;
- the open questions of section 6.

9.4 A, unsatisfied or modified without cause:
- 9.4.1 Agents ran read-only commands the brief forbids: `cd`, `head`,
  `awk`, `sed`, `echo`, `tr`, `sort`, shell loops. This happened in every
  session of the job, after the brief named them as forbidden.
- 9.4.2 The engineering log of the job was once edited, not appended
  (record 4.4 of `tmp/tasks_19_1413.md`).
- 9.4.3 The review's class A items not yet done:
  - the reformat whitelist (reviewer 3.3);
  - the strings file (3.4);
  - the remaining fallbacks (3.5): `log_close` on a closed log, the dead
    `return 0`, the flushes before `execv`; the provider's `error` branch,
    the main loop's own preparation, the duplicate directory creation, the
    narrowing branches and bootstrap's second JSON encoder are done;
  - the names `Loopback`, `Recorder` and `json_media_is` (3.6);
  - the `echo` handler and the old wire test still being run (3.7).

## 10 The A and B items, and whether this plan satisfies them

10.1 Satisfied by this plan:
- 9.4.3, by the steps of section 8: 3.3 by 1.9.2, 3.4 by 1.9.1, 3.5 by the
  step 3 orders, 3.6 by 1.4.3 and 1.5.4, 3.7 by 1.4.8;
- 9.4.2 cannot be undone. It is recorded, and the log has been append-only
  since.

10.2 Not satisfiable without the maintainer: 9.4.1, the forbidden commands.
The coordinator can forbid them and record each breach, but it cannot
remove the shell from an agent. Question 10.4.1.

10.3 The B items stay as written until answered. Section 2's readings are
built now and are reworked if the answer differs.

10.4 Questions (multiple choice):

10.4.1 Agents' read-only commands outside the allowlist:
- a) accept them as logged;
- b) the maintainer restricts the agents' Bash permission to `mv`,
  `mkdir -p`, `ls`, `grep`, `wc` and `test`;
- c) treat each as a defect that reopens the task.

10.4.2 The TAP module layout:
- a) `python/tap_producer.py`, `python/tap_consumer.py`,
  `ts/tap_producer.ts` (built);
- b) directories `tap-producer/` and `tap-consumer/` holding the modules;
- c) another layout.

10.4.3 The TAP line grammar:
- a) `DATA/06_tap.txt`, plan first with bare names (built);
- b) tappy's default output, with a `# TAP results for` header and the plan
  last;
- c) the earlier writers' `# Subtest` grammar.

10.4.4 "MVC" in "the db admin design/MVC":
- a) the minimal code of the design (built);
- b) a model, view and controller split;
- c) something else.

10.4.5 The verbose level 2 form:
- a) a full `argv_verbose` (built);
- b) flags inserted after `argv[0]`;
- c) flags appended.

10.4.6 The `metaverse` `seq` on a new root: a), b) or c) of 6.1.

10.4.7 The console after `console.exit`:
- a) closed until the next page load (built);
- b) reopenable from ctrl-0.

10.4.8 The scripted PNG:
- a) regenerate `DATA/02` from stored blocks;
- b) the runner ignores the PNG's size and digest;
- c) another way.

10.4.9 The Lookup Accelerator:
- a) stays removed (held);
- b) the maintainer writes it;
- c) an agent writes it.

10.4.10 Section 4's defaults:
- a) accept all;
- b) name the ones to change.
