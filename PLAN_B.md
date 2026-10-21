# PLAN_B: what the hyperposition-engine job carries forward

## 0 Scope and authority

0.1 Written on 2026-10-19 by the coordinator session whose log is
`tmp/tasks_19_2016.md` (task 1.13), at the user's request. Sources: the
maintainer's two messages of that day, kept verbatim in section 1, and the
review document `tmp/PLANNING_UPDATE.md`. That review's one-off
instructions to the earlier coordinator are not carried: the log
corrections, the order of work and the per-task work orders. Only what stays
true after the job is carried.

0.1.1 Updated on 2026-10-20 by agent Q of the coordinated job whose log is
`tmp/tasks_20_1601.md` (tasks 1.20.6 to 1.20.10), from the maintainer's
message kept as 1.3. Sections 2.13 to 2.17, 5.22 to 5.26, 7.12, the 1.20
entries of 9 and the questions from 10.4.11 on are that update; earlier
text that it changes says so where it stands.

0.1.2 Updated on 2026-10-21 by agent Q2 of the same job (tasks 1.22 and
1.23), from the maintainer's messages kept as 1.4 and 1.5. Sections 2.18
to 2.20, the 1.4 and 1.5 entries of 9, 10.3.2 and the questions from
10.4.33 on are that update; earlier text that it changes says so where it
stands.

0.1.3 Updated on 2026-10-21 by agent Q3 of the same job (tasks 1.24.2 to
1.24.9), from the maintainer's message kept as 1.6. Section 2.21, the 1.6
entries of 9, 10.3.3 and the questions from 10.4.44 on are that update;
earlier text that it changes says so where it stands (2.14, 2.19.6, 3.8, 9,
10.4.21 and 10.4.22).

0.1.4 Updated on 2026-10-21 by agent Q4 of the same job (task 1.25), from
the maintainer's message kept as 1.7. Section 2.22, the 1.7 entries of 9,
10.3.4 and the questions from 10.4.50 on are that update; earlier text that
it changes says so where it stands (2.18.3, 2.18.4).

0.2 Readers: the maintainer, and every later session or agent that writes
code for `hyperposition-plan.md`.

0.3 Order of authority: the maintainer's words in section 1, then this
file's section 2, then `hyperposition-plan.md`, then `API/`.
Agents do not edit the plan or `API/`; section 7 lists the edits
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

1.3 Received at 22:58 on 2026-10-20 (log `tmp/tasks_20_1601.md`, 1.20),
after that job's postmortem; its "before testing" list is that log's 4.8,
and the class B items it names are that log's 4.6:

```text
please perform "before testing" above 1 2 3 5... all A are fine. assume all class B are approved, except update plan for these: 1.18.5  the max blob size needs to be the same as the max db size. whatever chrome supports for 1 large db is the max for browser storage (and caching to server as an image/restoring admin operations) needs to be the max blob window and every window a blow goes through needs to be the same size and a single settings.json entry.  1.18.10 (remove the powershell scripts from the whitelist.txt so they are not scanned. 1.18.16 for now only have verbose levels for shell scripts. the server and runtime only have a debug flag. 1.18.18.1 just use an event counter and compact when it reaches a reasonable threshold.
```

The message that log records as 1.21 is an instruction to that job's
coordinator and is not carried (0.1).

1.4 Received at 10:59 on 2026-10-21 (log `tmp/tasks_20_1601.md`, 1.22),
while that job's agent B5 ran. "The above B class calls" are the class B
items the coordinator's messages had named since 1.21 (that log's 1.22.1):

```text
i aprove the above B  class calls. define 2 categories of test "smoke-test", "normal-test". have test_all.sh run by default whatever important test suites fit in 2 minutes by labelling those smoke-tests and running only them when asked to run the smoke-test suites. then have the option to run smoke-test and those labelled normal-test during normal testing. schedule this now
```

1.5 Received at 11:09 on 2026-10-21 (log 1.23), while agent Q2 wrote this
update. One file name is elided as `[the project rules file]`, because no
file but that one names it (10.4.43); the log's 1.23 holds the literal
text:

```text
have @powershell/test_powershell.ps1 call python/test_all.py inside WSL. instead of test_all.sh call it "test_posix.sh " and have test_posix.sh call python/test_all.py. then test_powershell.ps1 and test_posix.sh  are the two offical test targets for the wole project. one runs on windows and later one will run in docker. update [the project rules file] and the doc and shcedule this new request
```

1.6 Received at 11:30 on 2026-10-21 (log 1.24), while agent Q2 wrote its
update. Its first request is 2.19.5 (log 1.24.1); the rest is 2.21:

```text
make test_powershell.ps1 stop on failure.  add the powershell reformatting back and add the BOM to the allow list and whatever is needed. remove it from all scanning except the comment scanner and the utf-8 allow list. make the table of file extension to scanner type be data driven. except powershell, just the the ps scripts handle formatting on thier own by reading the whitelist on thier own. the are different OS so there has to be a split.
```

1.7 Received at 11:58 on 2026-10-21 (log 1.25), while agent Q3 wrote its
update. One file name is elided as `[the project rules file]`, as in 1.5,
because no file but that one names it (10.4.43); the log's 1.25 holds the
literal text. The request is 2.22:

```text
i want "--normal-test" that worked great.  rename test_test_all to test_test and just test the stuff that is infrastructre for testing, not the test driver in there. update [the project rules file] and the docs to explain the destinction.
```

## 2 The maintainer's decisions

Each item states the decision, then how it is built. A detail marked
READING is the coordinator's reading of the words; section 10 asks about it.

### 2.1 Sizes

Superseded by 2.13, from the maintainer's 1.3 (log task 1.20.7). The text
below is kept as history of the design it replaces; its sizes, 10 MiB per
blob and per message and 100 MiB per queue, are class C (9.2).

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

2.5.3 Since 1.3 only the shell has verbose levels; the server and the
runtime have only `debug`. 2.15 says what remains of 2.5.1 and 2.5.2: the
levels of `verbose.exec` stay, for the shell alone.

### 2.6 Timers

2.6.1 Every timer has a sane default value. It is a named constant whose one
line comment says it is a default chosen by its writer.

2.6.2 The 120 s lengths already written stay as defaults. Every new timer
gets its writer's sane value, listed in the handoff.

2.6.3 The provider request uses `provider.timeout_seconds` (plan 4.1), and
`console_run` its `timeout_seconds` argument (plan 5.5).

### 2.7 System initialization

2.7.1 The maintainer, verbatim: "System initialization does not have to
abide by the rules for how the system it is used unless it is reasonably
convinent for it to do so." The rule is in the project rules.

2.7.2 The worker's initialization (`sqlite3InitModule`,
`installOpfsSAHPoolVfs` and its capacity, the OPFS directory, file handles
and `createSyncAccessHandle` for the cache slots) uses promises directly,
in one module that the synchronization audit of plan 8.6 exempts by name.
No platform port is built in `queue.ts`. Once initialization has handed the
objects over, the system runs under plan 1.3 as before.

### 2.8 No refusal between the AI API and the databases

2.8.1 The maintainer, verbatim: "i injected an article into your context
about how things that were never a requirement become requirements
incorrectly and then the user is refused when he tries to lifer the
requirement. this is a violation of the API agreemend between the AI API
and the databases. If the databases get trashed that is OK and part of the
AI API development process, where recovery will be included later." The
rule is in the project rules. It extends 2.3.

2.8.2 `source_put` and `system_restart` are not permit tools: the AI calls
them without asking, over the line and over stdio. The stdio refusal of a
permit tool has no case left on the server and is removed. The plan's
permit set, Unconfirmed in plan 5.5, becomes `console_run` alone, which
gates the host's shell, not a database (plan 4.6).

2.8.3 Proposed edits for the maintainer: in `API/mcp/tools.json` delete
the `"_meta": {"xsjs": {"permit": true}}` of `source_put` and
`system_restart`; plan 5.5 reads "`source_put {name}`, debug, and
`system_restart {main_loop}`, debug" and "the permit set is
`console_run`"; plan 8.6 names the initialization module beside the four.

### 2.10 Provider information

2.10.1 The maintainer, verbatim: "provider info will be provided later, for
now we depend on the test driver. just have a file that needs to be filled
out with the info and is not used during testing."

2.10.2 Default for the maintainer to confirm: `provider.json` beside
`settings.json` holds `base_url`, `chat_model` and `image_model`, empty
strings to be filled out. These three keys leave `settings.json`, the
settings checks and the `Settings` interface; `provider.scripted` (true)
and `provider.timeout_seconds` stay. When `provider.scripted` is false the
server reads `provider.json`, an empty value is an error, and `hello`
carries `provider_info {base_url, chat_model, image_model}` beside
`provider_key` (D8 unchanged). When it is true the file is never read and
`hello` carries no `provider_info`. Testing is scripted, but for the one
rung of the real HTTP timeout inside a turn (log task 1.18.23.3): it
writes its own `provider.json` into its own root, sets `provider.scripted`
false there and points `base_url` at a local stub. The maintainer approved
that departure from "not used during testing" (2.17).

### 2.11 Invisibility

2.11.1 Project rule: unintentional invisibility is always a bug, not a style
issue. `#debug` (the console and the overlays) under the fixed `#image`
(record 3.79 of `tmp/tasks_19_2016.md`) is such a bug.

### 2.12 Formatter

2.12.1 The maintainer, verbatim: "add a formatter for .ts, .js, and .html.
using the tools we have." `prettier` 3.9.8 is installed and formats all
three; `python/reformat.py` runs it for those extensions.

### 2.13 Sizes: one blob window

From 1.3 (log task 1.20.7). It supersedes 2.1.

2.13.1 Decision: the largest blob equals the largest database. What Chrome
supports for one large database is the limit for browser storage and for
the administration operations that cache a database on the server as an
image and restore it. That size is the blob window, every window a blob
goes through has that size, and it is one `settings.json` entry.

2.13.2 The entry is `blob_max`. It keeps its name: the maintainer's words
are "max blob size" and "max blob window", `blob_max` already names the
largest blob in both decoders and both settings checks, and keeping it
leaves one setting where three were. It replaces `message_max` and
`queue_max`, which leave `settings.json`, the settings checks of both
languages, `Settings` and every fixture that writes a whole settings
object. Question 10.4.11.

2.13.3 READING, what a window counts: blob bytes, the `s` of each blob it
holds or passes, never line bytes, which `line_max` bounds line by line.
- A message: the sum of its blobs' `s` is at most `blob_max`, so a blob is
  at most `blob_max`; checked when its line ends, before any blob byte is
  buffered.
- A queue: the sum of the `s` of the blobs of the lines it holds is at most
  `blob_max`. A queue no longer counts line bytes.
- A line is at most `line_max`, as before.

Why: a blob of `blob_max`, the largest database, must pass every window
with its line, and a window that counted the line would pass a blob of
`blob_max` minus that line only. A `kv.get` reply carries the blob its
`kv.put` carried under a longer line, so it fits whenever the put did.
Rejected: every window counts line and blob bytes, as `message_max` and
`queue_max` did, at `blob_max`; the largest database is then `blob_max`
minus its `db.snapshot` reply line, and log item 4.6.3.2 stays open. What
is lost: no queue bounds the bytes of lines without blobs; the
maintainer's 100 MiB queue bound that did is class C. Question 10.4.12.

2.13.4 The value, researched on 2026-10-20. Each is a documented limit,
none a measurement:
- SQLite: a database file is at most 4294967294 pages, about 17.5 TB at
  4096 byte pages (https://sqlite.org/limits.html). The OPFS SAH pool VFS
  states no file size limit of its own
  (https://sqlite.org/wasm/doc/trunk/persistence.md).
- `sqlite3_serialize`, behind the server's `Connection.serialize` of
  `db.snapshot` (plan 6.8) and the worker's `sqlite3_js_db_export`,
  allocates the whole image with one `sqlite3_malloc64` of page count
  times page size
  (https://raw.githubusercontent.com/sqlite/sqlite/version-3.46.1/src/memdb.c),
  which refuses any request over `SQLITE_MAX_ALLOCATION_SIZE`, 2147483391
  by default
  (https://raw.githubusercontent.com/sqlite/sqlite/version-3.46.1/src/malloc.c,
  https://sqlite.org/compile.html). The system library and the pinned
  `sqlite-wasm-3460100` are both 3.46.1; the wasm build sets no other
  value (`ext/wasm/GNUmakefile` of 3.46.1). Whether Ubuntu's build sets
  another shows in `PRAGMA compile_options`; not checked.
- sqlite3.wasm's heap: the 3.46.1 build grows its memory and sets no
  `MAXIMUM_MEMORY`, so emscripten's default applies, 2147483648 bytes in
  the settings of emscripten 3.1.55
  (https://raw.githubusercontent.com/emscripten-core/emscripten/3.1.55/src/settings.js;
  the emscripten that built the pinned file is not recorded here);
  Chrome allows 4 GiB of wasm32 memory since M83
  (https://v8.dev/blog/4gb-wasm-memory). The heap also holds everything
  else SQLite holds, so the largest image the worker can export through it
  is below 2 GiB by an amount only a measurement gives.
- V8: an `ArrayBuffer`, so a `Uint8Array`, is at most
  `kMaxSafeBufferSizeForSandbox`, 32 GiB minus 1, with the V8 sandbox
  (https://raw.githubusercontent.com/v8/v8/main/include/v8-array-buffer.h,
  https://raw.githubusercontent.com/v8/v8/main/include/v8-internal.h),
  which 64-bit Chrome on Android, ChromeOS, Linux, macOS and Windows
  enables by default (https://v8.dev/blog/sandbox); 2^53 minus 1 without
  it. An allocation may fail below that for lack of memory; only a
  measurement says where. A restore reads the whole image into one
  `Uint8Array` before `importDb`, which writes it without the wasm heap.
- Chrome's storage: an origin may use up to 60% of the disk, about 5% in
  incognito (https://web.dev/articles/storage-for-the-web). The number is
  the machine's, read with `navigator.storage.estimate()`, a measurement.
  A restore holds at its peak the streamed cache file, the temporary file
  of its check and the database file: three times the database in OPFS.

Every whole database image, out of the server for `db_load` and the start
replacement and out of the worker for the UI's `db.snapshot`, goes through
`sqlite3_serialize`. So no database over 2147483391 bytes can be imaged in
this stack whatever Chrome allows; the largest at 4096 byte pages is 524287
pages, 2147479552 bytes.

2.13.5 `blob_max` is 2147483391 until the measurement of 2.13.9: the
smallest documented limit on the path, SQLite's, which Chrome cannot raise.
Unconfirmed: it is documented, not measured. Chrome's own limits, the quota,
the allocation and the worker's heap, are measured in the testing phase;
where one is lower the rung fails naming it and the maintainer sets the
entry. Nothing lowers the value at run time. Question 10.4.13.

2.13.6 READING of "caching to server as an image/restoring admin
operations": `db_unload` is the caching. The browser drops its copy, and
the server's copy, which replication keeps current (plan 6.8), is the image
kept. `db_load` and the start replacement are the restoring: one
`db.snapshot` blob from the server. No line sends a browser database to the
server whole, and none is added. Rejected: `db_unload` first sends the
browser's file to the server as one blob, on a new line the server compares
with or keeps beside its copy. Question 10.4.14.

2.13.7 The windows a blob goes through, as the code has them on 2026-10-20,
and what each becomes:
- The Python decoder, `jslb.LineDecoder`, built by `main_loop.loop_run`,
  `bootstrap._reply_read` and `echo_loop.py`: `blob_max` and `message_max`
  become one check, the blobs of a message at most `blob_max`. Its
  signature becomes `LineDecoder(line_max, blob_max, overflow_bytes,
  sink_make)`, as `API/python/jslb.pyi` has it.
- The TypeScript decoder: the same, `new LineDecoder(line_max, blob_max,
  overflow_bytes, sink)`.
- `wire.ts`'s post limit: `message_max` goes; it refuses a line over
  `line_max` or a message whose blobs sum over `blob_max`.
- `wire.ts`'s `FrameQueue`: `queue_max` becomes `blob_max`, blob bytes
  held.
- `queue.ts`'s `TaskQueue`: the same; before `settings_set` it bounds
  nothing, as now. On the UI's path it is the first window: a UI put of
  `blob_max` + 1 is refused there with `queue.queue_over` before `wire.ts`
  sees it (approved by 1.4, 2.20).
- The worker's replication queue, `worker_ai.ForwardQueue`: the same.
- The hello's decoder in `wire.ts` keeps no blob (`hello_blob_max` 0) and
  drops `hello_message_max`. READING: its line bound `hello_line_max` stays
  10485760, D24's constant (4.20), whose source, the maintainer's 10 MiB,
  is superseded. Question 10.4.18. The server's reply decoder reads the
  settings it sends.
- The server holds no queue and dispatches one line at a time; its window
  is its decoder. A `db.snapshot` reply holds the image in memory, at most
  what `sqlite3_serialize` allocates.
- `kv.put` and `kv.get`: a value passes the sender's post limit and the
  server's decoder going in, the page's decoder and the queues coming out,
  all at `blob_max`.
- `db.snapshot`, `db_load` and the start replacement: one reply, one blob,
  at most `blob_max` (2.13.8). `db_unload` moves no blob (2.13.6).
- The UI's `db.snapshot` and `kv.get` on the AI store, over the ui-ai
  lane: the same queues; the image is exported through the worker's heap
  (2.13.10).

READING: thresholds and budgets are not windows and keep their settings. A
window holds or passes a blob; these decide something else:
- `line_max` bounds a line, never a blob;
- `overflow_bytes` decides whether a blob is held in memory or streamed to
  a cache file; a blob up to `blob_max` passes on one side of it or the
  other;
- `db_soft_bytes` is a soft limit on the total of the databases and
  refuses nothing (2.2.2);
- `files_browser_bytes` and `media_db_bytes` are eviction budgets (plan
  6.7).

Rejected: setting them to `blob_max`, which would hold every blob in
memory, let one line fill a window, or end eviction. Question 10.4.15.

Class C since 1.4, approved as built (2.20); class B before it. Two
settings that cannot sensibly have the size:
- `chunk_bytes`: the size of each `os.read` of the server and of each piece
  `wire.ts` sends before it waits on `bufferedAmount`. `os.read` allocates
  its whole size up front, and a piece of `blob_max` would read a whole
  cache file into memory and hand ttyd one WebSocket message that it
  collects whole before writing it to the pty.
- `srv_buf_size`: libwebsockets' `pt_serv_buf_size`, the receive chunk of
  both protocols, a buffer each service thread holds at its full size.
  Unconfirmed: read from the libwebsockets sources, not measured
  (https://libwebsockets.org/lws-api-doc-main/html/structlws__context__creation__info.html).

They are the pieces a blob is cut into, not windows that hold one; both
stay 1 MiB. Options: a) as written; b) both `blob_max`, with the costs
above; c) a size the maintainer names. Question 10.4.15, answered by 1.4:
a).

2.13.8 `db.snapshot` returns to one blob, as plan 6.8 says: the reply
carries `sha256` and `seq` and the database file as blob 1, as
`API/ts/lines.d.ts` already has it. The `db.chunk` pieces of log record
3.12.2 are removed from the design with every name that served only them
(5.23); that design is kept in plan 10.21. The receiver checks the blob's
SHA-256 against `sha256` before it restores, as the pieces did.
- Log item 4.6.3.1, restated. Each `db_load` sends one `db.snapshot` and
  sleeps; the server answers one at a time, and each reply's blob streams
  to a cache file as it arrives. A reply counts its `s` in the AI's
  `TaskQueue` from the decoding of its line to the run of its wake, so two
  replies whose blobs sum over `blob_max`, held at once, fault with
  `queue.queue_over`. Class C since 1.4, which approved a) (2.20); class B
  before it. Options: a) as written, a loud fault; b) the
  `db_load` tool runs one load at a time, a later call waiting in the AI
  worker until the earlier is restored, so one image is held at most; c) a
  blob streamed to a cache file counts nothing in the queues, its bytes
  being in OPFS, so the queues bound memory and the quota bounds OPFS.
  Question 10.4.17.
- Log item 4.6.3.2, resolved by 2.13.3: only blob bytes count, and a
  `kv.get` reply carries the blob its `kv.put` carried.

2.13.9 The measurement, a browser rung of the testing phase,
`rung_blob_max`, stage 6, on a root of its own with the shipped
`blob_max`:
- the server's fixture makes a database of the most 4096 byte pages whose
  file is at most `blob_max`, 2147479552 bytes, and the page loads it with
  `db_load`: one `db.snapshot` reply, one blob, its digest checked, its
  `seq` opened;
- before the load, the origin's `quota` and `usage` from
  `navigator.storage.estimate()`, read through DevTools, reported, and
  checked to hold the three copies of 2.13.4;
- the UI's `db.snapshot` of that database, the export through the
  worker's heap, compared by SHA-256 with the server's file;
- the time of each, reported.

The rung fails, naming the path and the numbers, where any of them cannot
carry the database; the maintainer then sets `blob_max` or picks an option
of 2.13.10.

2.13.10 Class C since 1.4, which approved a) (2.20); class B before it:
the worker's own export, `Store.db_snapshot` through
`sqlite3_js_db_export`, serves the UI's `db.snapshot` and holds the whole
image in sqlite3.wasm's heap, at most 2147483648 bytes with all else SQLite
holds there, so it cannot export a database of `blob_max`. Options: a) as
built, its limit measured by 2.13.9; b) export with the pool's
`exportFile`, which reads the file between transactions into JavaScript
memory, bounded by V8 and not the heap; c) sqlite3.wasm rebuilt with a
`MAXIMUM_MEMORY` of 4 GiB, a change to a third party build. Question
10.4.16.

2.13.11 READING: a database that grows past `blob_max` in the browser is
not refused, because nothing is added between the AI API and the
databases (2.8). Its image is refused loud where it meets a window, by
`sqlite3_serialize` or by a decoder. Rejected: `PRAGMA max_page_count`
bounding each database at `blob_max`, a refusal only the maintainer can
ask for. Question 10.4.19.

2.13.12 The plan proofs 2.1.8 changed change again:
- the `kv.put`, `kv.get` and round trip of the largest message that fits
  `message_max` become a blob of `blob_max` with its line, and a message
  whose blobs sum to one byte more refused when its line ends;
- the 128 MiB upload and echo, which 2.1.8 split into messages that each
  fit, are one message each, as 128 MiB is within `blob_max`;
- the refusals of one byte more, approved by 1.4 as built (2.20): on the
  page's own port by `wire.ts` at its post with `wire.blobs_over`; from
  the UI first by the AI worker's task queue with `queue.queue_over`; and
  of a `kv.get` reply by the page's decoder with `jslb.blobs_over`, the
  value of `blob_max` + 1 bytes written on the server behind the page's
  back with `substrate.Store.kv_put` and a file path, since no port can
  carry it.

Each rung reads `blob_max` from its root's settings, so with the shipped
value each such rung moves 2 GiB. READING: the proofs stay at the window's
edge, where 2.1.8 put them, and do not return to the plan's earlier 16 MiB.
Question 10.4.20.

2.13.13 The maintainer's earlier sizes of 1.1 and 2.1, 10 MiB per blob and
per message and 100 MiB per queue, are class C, superseded by 1.3.

### 2.14 The reformat whitelist

From 1.3 (log task 1.20.8).

Replaced in part by 1.6 (log 1.24.9, 2.21): 2.14.1, 2.14.2, 2.14.3 but its
last item, 2.14.4 but the file kept with `test_others_refused`, and 2.14.5.
The text below is kept as history, and whole in plan 10.25.

2.14.1 Decision: the PowerShell scripts leave
`python/reformat_whitelist.txt` and `python/test_posix.py` does not scan
them. The lines `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1`,
`xsjs_stop.ps1`, `powershell/*.ps1` and `powershell/en-US/*.psd1` go. "Not
scanned" covers every check of `test_posix.py`: the character check, the
formatting, and the comment check, which also reads every PowerShell file
`_POWERSHELL_GLOBS` finds, whitelisted or not; that scan goes too.

2.14.2 READING: `powershell/en-US/*.psd1`, a PowerShell data file and not a
script, goes with the scripts. Only they read it, its byte order mark is
the PowerShell rule's, and keeping it scanned would keep the handling the
decision removes. Rejected: it stays whitelisted, with the byte order mark
handling and the PowerShell comment lexer kept for it. Question 10.4.21.

2.14.3 `test_posix.py`'s PowerShell handling. Removed, because it served
only the PowerShell files:
- `_BOM_EXTENSIONS` and the `utf-8-sig` choice of `non_ascii_check`, which
  reads every file as `utf-8` again;
- the `utf-8-sig` of `comments_check`, back to `utf-8`;
- `_POWERSHELL_GLOBS`, `powershell_paths()` and its use in `main`;
- the `.ps1`, `.psm1` and `.psd1` case of `comments_find`,
  `powershell_scan`, `powershell_double_scan` and
  `_POWERSHELL_TOKEN_BREAK`;
- the PowerShell sentences of the header comment and of `main`'s
  description.

Kept, because whitelisted files use it:
- `non_ascii_check`, which refuses U+FEFF like any character outside
  `_NON_ASCII_ALLOWED`, anywhere in any whitelisted file;
- `token_find`'s `utf-8-sig`, which reads only `ts/*.ts` and was not made
  for PowerShell.

2.14.4 `python/test_test_posix.py`, made for log task 1.18.10: the tests of
a mark accepted at the start of a `.ps1` or `.psd1` file go
(`test_powershell_marked`, `test_powershell_plain`, `test_mark_inside`,
`test_column_after`). `test_others_refused` stays with `a.py` and `a.ts`
and without `a.psm1`: it proves that a whitelisted file starting with a
byte order mark is refused, which every whitelisted file still relies on.
The file stays, so log task 1.20.4 still tracks it; its header and class
comments say what is left. READING: question 10.4.22.

2.14.5 An exception to 3.8 and to the project rules' whitelist rule: a new
PowerShell file is not added to the whitelist. The project rules are the
maintainer's to edit.

### 2.15 Verbose levels for the shell only

From 1.3 (log task 1.20.9).

2.15.1 Decision, for now: only the shell scripts have verbose levels; the
server and the runtime, the TypeScript of both threads, have only `debug`.
The server and runtime level design is kept in full in plan 10.19,
deferred by the maintainer.

2.15.2 READING of "shell scripts": the shell the engine starts through
`verbose.exec`, the console's `/bin/dash` on tty 0 (plan 2.3), and what
runs in it, typed at the console or sent by `console_run`; and the `.sh`
admin scripts of the door plan 10.3 when they are built. The Windows admin
scripts are PowerShell and have no verbose levels; none is added.
Rejected: the PowerShell admin scripts as the shell scripts, which would
add levels where the request removes them; `archive.sh` and `clean.sh`,
which plan 7.5 puts outside the project. Question 10.4.23.

2.15.3 READINGS, the settings (question 10.4.24):
- `verbose_level` stays under its name, read only by the console role as
  the level `verbose.exec` runs dash at. The name fits and one reader is
  left. Rejected: renamed `shell_level`; removed, dash run at a fixed
  level; the level carried in the console's `--url-arg`.
- `verbose_ring` stays: a ring size, not a level, which the overlays and
  `verbose_tail` need. Rejected: removed with the levels.
- `verbose_forward` goes: it is a second runtime flag, and the runtime has
  only `debug`. `verbose.put` is forwarded whenever `debug` is true.
  Rejected: kept beside `debug`.

2.15.4 `verbose.exec(level, argv, argv_verbose)` keeps its levels, which
are the shell's. 0 runs `argv` passed through; 1 runs `argv` passed through
and writes its start and exit to the server's log; 2 runs `argv_verbose`
raw and writes the same two lines. Its level comes from `verbose_level`.
The console's verbose form stays `[dash, "-v"]` (2.5.2). READING: level 1
passing the console's output through, log item 4.6.9.1, is kept as built,
because a captured level 1 gives dash no input. Rejected: level 1 captures
the output and formats it as Markdown progress. Question 10.4.25.

2.15.5 The server, with only `debug`:
- `verbose.level_set` goes; `verbose.log(text)` takes no level and writes
  every line it is given to `_verbose` and the ring.
- A failure is logged always: `bootstrap.run_failed`,
  `main_loop.serve_failed`.
- The trace of log task 1.18.16, `bootstrap.hello_submit`,
  `main_loop.line_dispatch` and `main_loop.line_reply`, is written when
  `debug` is true and never otherwise. READING: it keeps logging header
  JSON only, log item 4.6.9.2 as built. Rejected: the whole line in the
  form of plan 3.11; no trace. Question 10.4.26.
- `exec`'s start and exit lines are written at shell levels 1 and 2.
- `_verbose`'s `line.level` and `LogLine.level` go: no level is left to
  record, and a column of values no level gave would be fake data.

2.15.6 READINGS, the runtime with only `debug` (question 10.4.27):
- `verbose.level_set` goes from both threads; `verbose.log(text)` takes no
  level and writes to the thread's ring and its sink.
- The task manager's trace of every submit, dispatch, sleep, wake and
  reply, plan 4.2's level 2 lines, is written when `debug` is true.
- `verbose.put` is forwarded when `debug` is true.
- The overlays, debug only already, show the rendered wire traffic as
  before; the fix of log task 1.18.3, `WireTap` not rendering `verbose.put`
  into the overlay, stays.
- `lines.VerboseLine` loses `level`.
- The browser tool `verbose_level` goes; `verbose_tail` stays.
- A script's `engine.log(text)` takes no level, and its run keeps every
  line it wrote. The 322 byte step script of `ts/test_substrate.ts`, a
  measured SHA-256 vector that is never run, keeps its text
  `engine.log(1, ...)` (approved by 1.4, 2.20).
- `script_debug` is `script_run` with its trace on, every substrate call
  traced first: `script.script_run(store, name, args, trace)` takes a
  boolean where it took a level.

Rejected: the runtime logs nothing outside debug mode at all, the script
lines of a run included; `verbose_level` kept as a tool that switches
`debug`.

2.15.7 What log tasks 1.18.3 and 1.18.16 become:
- 1.18.3: in debug mode, where forwarding is now always on, the overlay
  does not feed itself. The fix stands; its rung runs on a root with
  `debug` true and no level.
- 1.18.16: the console runs `verbose.exec` at the level `verbose_level`
  sets, level 2 passing dash's output through raw; the server writes its
  failures always and its trace in debug mode.

### 2.16 Compaction by an event counter

From 1.3 (log task 1.20.10).

2.16.1 Decision: compaction counts events and runs by itself when the count
reaches a threshold. The design it replaces, the estimate system message,
bytes counted as tokens and the AI deciding, is kept in plan 10.20, marked
replaced.

2.16.2 READING, the events counted: each turn appended to a scene's
conversation, one `_turn` row and one provider message, whatever its role:
the player's message, each assistant reply with or without tool calls,
each tool result, and the summary turn of a compaction. Rejected: the
player's turns, `ai.say` and `ai.click`, which grow a conversation by very
different amounts; provider requests. Question 10.4.28.

2.16.3 READING, where the counter lives: it is the number of the scene's
`_turn` rows, counted when read, so the turn store itself keeps it. It
survives exactly what the turn store survives, reloads, replication,
`db_unload` and `db_load`, the start replacement, and it cannot disagree
with the turns. Nothing new is stored. Rejected: a counter row per scene
in `_meta`, incremented by `turn_append` and reset by `turn_compact`, a
schema change; a KV row; a count in the agent's memory, which a reload
loses. Question 10.4.29.

2.16.4 It resets when a compaction replaces the turns it covers with one
summary turn: the count falls to that turn plus any after it. A new scene
starts at 0, each scene being its own conversation.

2.16.5 READING, where and when it runs: in the browser's substrate,
inside the wrapper, where plan 6.6 and 11 put compaction. When
`Store.turn_append` appends a turn of role `user` to a scene that already
holds `turn_compact_turns` turns or more, it first compacts that scene's
turns 1 to its last, in the same transaction. The compaction is forwarded
as its own `turn.compact` before the `turn.append`, so the server applies
the same two operations; the server's substrate never compacts by itself.
A `user` turn starts a player's turn, when the conversation is whole and
no tool call waits for its result (log item 4.6.2). Rejected: the agent
compacts at the end of each turn in `agent.ts`, where plan 11 decided
against compaction. Question 10.4.30.

2.16.6 READING, what the summary holds: compaction is by truncation,
because plan 10.14 leaves a summary written by the provider a door. The
summary turn, role `system` as `turn_compact` writes it, holds one `i18n`
text, `substrate.turns_compacted`, naming the turns compacted and the
count that reached the threshold and saying their text is no longer in the
conversation; the databases hold the state. Rejected: the last assistant
reply's text as the summary; the latest player turn kept whole and the
turns before it compacted; a summary written by the provider (plan 10.14).
Question 10.4.31.

2.16.7 The threshold is the `settings.json` entry `turn_compact_turns`,
replacing `turn_compact_tokens`: the plan's tunable constants are settings
(plan 6.9), which the server loads into `_settings` where the AI reads
them, and a test root sets a small value of its own to reach compaction in
a short run, which a named constant would not allow. Its default, 64, is a
sane value chosen by its writer, agent Q (2.6), Unconfirmed. Question
10.4.32. The browser's `Store` takes it as a constructor argument after
`overflow_bytes`.

2.16.8 The AI keeps `engine.store.turn_compact(scene, through, summary)` to
compact by hand. The analyst's seed prompt loses the estimate message and
says that compaction is automatic at `turn_compact_turns`.

### 2.17 The approved class B items

From 1.3 (log task 1.20.6).

2.17.1 Every class B item of log 4.6 is approved but 4.6.3, 4.6.6, 4.6.9
and 4.6.11, which 2.13 to 2.16 replace. The approved items are
requirements as built; 9.2 lists them as class C. Text that stated the
opposite now states the built behaviour: here 2.10.2, 6.3, 6.13 and
10.4.7; in the plan 2.5, 2.6, 5.3, 6.9, 8.3, 8.4 and 8.7.7; and
`API/ts/agent.d.ts` through 7.12.

### 2.18 Test categories

From 1.4 and 1.5 (log tasks 1.22.2 to 1.22.8, and 1.23).

2.18.1 Decision: two categories of test suite, under the maintainer's
names: `smoke-test`, the important suites that fit in 2 minutes in all,
and `normal-test`, the others. A label is one of those two strings. A
`smoke-test` run runs the suites labelled `smoke-test`; a `normal-test`
run, the maintainer's "normal testing", runs the suites of both labels.

2.18.2 READING, what a suite is: the smallest unit a runner starts, times
and names on its own, and can leave out without changing what the units
after it see.
- `python/test_all.py`: each module of `_MODULES`, one TAP block under its
  own alarm; its label stands beside its name in that table.
- `python/test_wire.py` and `python/test_browser.py`: each rung, run by
  `RungLog.rung_run` under its own timer and printed on its own line; its
  label is an argument of that call.
- `python/test_posix.py`: one suite, its checks being steps of one pass
  with no name or timer of their own; its label stands beside its call in
  `test_all.py`.
- The page's TypeScript modules: the browser rung "stage 0: typescript
  suites" runs them as one TAP stream per thread, and no runner can leave
  one module out unless the page reads the category, so they carry that
  rung's label.

A stage of `test_wire.py` (echo, stock, release) and a root of
`test_browser.py` carry a label too: `smoke-test` when they hold a
`smoke-test` rung, else `normal-test`. A `smoke-test` run starts no ttyd
and no page for a root it runs nothing on. The opening rungs of the wire
stages, "hello" and "mcp line", hand the later rungs their connection and
carry their stage's label. Setup is not a suite: a page build, a root's
ttyd, the browser and the stub server, the vectors. It runs when a suite
that needs it runs, and a page is built when the first root that serves it
starts.

Rejected:
- each runner whole as the grain, which leaves the browser and wire tests
  out of the smoke run whole;
- the root or stage as the grain, which loses the probe root's quick rungs
  to its 2 GiB and 120 s rungs unless roots are split;
- the stages of plan 8.7, which mix labels inside stages 5 and 6;
- each TypeScript module, which needs the category on the page (plan
  10.24).

Question 10.4.33.

2.18.3 Rules of a label:
- every suite carries one, written beside it; there is no default label;
- a `smoke-test` suite needs nothing that a `normal-test` suite does: a
  suite that a `smoke-test` suite needs is `smoke-test` itself;
- a root or stage labelled `smoke-test` holds a `smoke-test` rung, and one
  labelled `normal-test` holds none. `category.LabelBook` checks both as
  the runner reaches them and raises, so a mislabel fails loud in the
  first run that reaches it; a `normal-test` run reaches every one;
- a label other than the two strings raises.

The labels, the options and those checks are one new module,
`python/category.py`, which the three runners read, with its stub
`API/python/category.pyi` (text in `tmp/handoff_20_Q2.md`) and its tests
`python/test_category.py`. The plan chooses the reuse: the three runners
must read the same two options and apply the same rule. Since 1.7 the
module also holds `alarm_plan`, and its tests are in `python/test_test.py`,
which `python/test_category.py` joined (2.22.3, 2.22.4).

2.18.4 The labels. Each is Unconfirmed until the testing phase measures it,
because nothing may be run now (log 1.22.8); class B.

Smoke-test, each with its reason:
- S1, a unit suite: every module of `test_all.py`'s `_MODULES`, the new
  `test_category` and `test_test_all` among them (since 1.7, `test_test` in
  place of both, 2.22.5); the page's TypeScript suites, the browser rung
  "stage 0: typescript suites", and "stage 0: typescript suites in order",
  which reads the documents the first one wrote.
- S2, the rules' audit: `test_posix.py`, with the character and comment
  checks, the synchronization audit of plan 8.6, the formatters and
  `ruff check`.
- S3, the server through ttyd, moving at most 1 MiB and waiting out no
  timer: every rung of the wire test but "echo blob_max" and "echo 128
  MiB".
- S4, one real start of the engine page: the browser root "fresh", whose
  one rung "stage 8: fresh root" proves the page load, `hello`, the seeded
  Script and a first render with no fault (log task 1.18.1).

So the browser test's `smoke-test` roots are "suites" and "fresh", and
every stage of the wire test is `smoke-test`.

Normal-test, each with its reason:
- N1, moves or allocates a blob of `blob_max`, 2147483391 bytes: the wire
  test's "echo blob_max"; in the browser test "stage 5: blob_max round
  trip", "stage 5: blob_max plus one refused" and "stage 5: decoder fault"
  (root probe), "stage 5: wire drain timer" (root echo, 255 lines of 8
  MiB), "stage 5: largest UI put" (root upload) and "stage 6: largest
  database within blob_max measured", `rung_blob_max` (root largest).
- N2, waits out a 120 s timer of `wire.ts` by design, the whole limit of
  a `smoke-test` run: "stage 5: wire token timer" and "stage 5: wire open
  timer" (probe), "stage 5: wire hello timer" (stalled), "stage 5: wire
  drain timer" (echo).
- N3, moves 128 MiB or more: the wire test's "echo 128 MiB", which also
  measures ttyd's resident size for plan 3.10 and 10.11; "stage 5: echo
  128 MiB from the page" (echo); "stage 5: 128 MiB upload from the UI"
  (upload).
- N4, needs what a `normal-test` rung or root leaves: root "second", which
  compares with the run root "first" recorded; the rest of root "upload",
  which reads the trace and the long task observer that the largest put
  starts.
- N5, a long scripted session: root "stress", eight rounds under a 600 s
  timer; root "main", about forty rungs on one page, each needing the state
  of those before it, so it runs whole or not at all.
- N6, every other browser rung: a real platform path of a module whose
  unit suite runs in the smoke run, its time not measured. They are the
  rest of root "suites" ("stage 6: kill between file and row", and "stage
  0: worker hang keeps the UI's TAP lines", which runs the page's suites a
  second time), every rung of the roots faults, probe (but for N1 and N2),
  credential, release, first, locked, level, tool, crash, timeout,
  compact, bulk, replay and evict, and the rung "stage 5: stub reachable"
  outside any root, which only the `normal-test` roots probe, timeout and
  compact need.

Every rung of a `normal-test` root is `normal-test`. READING of "important
test suites that fit in 2 minutes": with no measurement, the smoke run is
the unit suites of both languages, the rules' audit, the wire test without
its large echoes, and one start of the engine page. A browser rung joins it
when a measurement shows room. Rejected: the unit suites and
`test_posix.py` alone; more browser roots (release, locked, tool, or main
whole) before any measurement. Question 10.4.34.

2.18.5 `test_posix.py` rewrites the whitelisted files with the formatters
as it checks them (`reformat.reformat`), so every `smoke-test` run formats
the tree. Kept as built. Question 10.4.37.

2.18.6 The 2 minutes, measured and enforced:
- Each suite's elapsed seconds, read with `time.monotonic` around it, are
  printed with its label. `test_all.py` writes `<module>: <label>, <s> s`
  to stderr after each module, so stdout stays the TAP stream, and
  `test_posix.py: smoke-test, <s> s` after the checks. The wire and
  browser tests end each rung's line with `(<label>, <s> s)`. A page
  build's line ends with its seconds. A passing run ends with `the
  <category> run took <s> s`.
- In a `smoke-test` run, `test_all.py`'s whole run has 120 s, the
  maintainer's 2 minutes, from its start. Each module's alarm is the
  sooner of its own 120 s and that deadline. `test_posix.py`,
  `test_wire.py` and `test_browser.py` run under an alarm at the deadline.
  A deadline already passed before a suite starts raises at once. The
  alarm raises naming the suite it stopped, so the run fails loud the
  moment it passes 120 s, with the lines measured so far printed above.
- A `normal-test` run has no limit of its own; every suite keeps its
  timer.

The maintainer confirms the fit from a `normal-test` run, whose lines give
every `smoke-test` suite's seconds, and from a `smoke-test` run that
passes. The limit is `test_all.py`'s; the lint and lifecycle steps of
`test_powershell.ps1` are outside it. Rejected:
- the limit checked once at the end, after every `smoke-test` suite ran,
  which reports late;
- the seconds reported with no limit;
- the limit in `test_posix.sh` under coreutils `timeout`, which would not
  reach `test_powershell.ps1` (plan 10.23).

Question 10.4.35.

2.18.7 READING, the runners' options: `test_all.py`, `test_wire.py` and
`test_browser.py` each take `--smoke-test` or `--normal-test`, at most one,
with `smoke-test` the default, through `category.options_add`. Each still
runs alone, and every test command of the project defaults to the smoke
run. Their `main` takes its argument list, so that `test_all.py` passes the
option to the two it runs in its own process. `test_all.py` keeps
`--failfast`. Rejected: a runner run alone runs every suite; the runners
require an option. Question 10.4.36.

2.18.8 Not built:
- a suite left out is not printed, nor written to TAP as `# SKIP`; a
  `smoke-test` run lists only what it ran;
- no `i18n` names: the runners and `category.py` write their messages
  with f-strings, as the TAP modules and `devtools.py` do;
- no test runs `test_posix.sh` or `test_powershell.ps1`; the testing phase
  proves them by running them, since a Python test that runs bash needs
  the maintainer's approval (question 10.4.42).

Each design is written out in plan 10.23.

### 2.19 The two official test targets

From 1.5 (log 1.23).

2.19.1 Decision: `powershell/test_powershell.ps1`, which runs on Windows,
and `test_posix.sh`, at the top level, are the two official test targets of
the whole project. Both call `python/test_all.py`, the first inside WSL.
`test_posix.sh` is the script 1.4 named `test_all.sh` (log 1.23.2). It will
later run in Docker; that design is in plan 10.22 and is not built (log
1.23.8).

2.19.2 `python/test_all.py` is the one runner of every suite, so that both
targets run the same suites: the TAP modules first, then the other Python
modules, then, when the stream is clean, `test_posix.py`'s checks,
`test_wire.py` and `test_browser.py`, each given the category. It stops at
the first failure with its exit code. The category is read in one place,
`test_all.py`'s options (2.18.7); each target checks its one argument and
passes it on. Rejected: each target calls `test_posix.py` and
`test_browser.py` itself, three runners per target to keep in step.

2.19.3 `test_posix.sh [--smoke-test | --normal-test]`, a bash script in the
style of `clean.sh`. No argument or `--smoke-test` passes `--smoke-test`;
`--normal-test` passes `--normal-test`. Any other argument, or more than
one, writes its usage to stderr and exits 2. It changes to its own
directory and runs `exec python3 python/test_all.py <option>`, so its exit
code is the runner's. It is listed in `python/reformat_whitelist.txt` by
name. READING: the target takes the maintainer's options and no others;
`--failfast` stays a developer's option of `test_all.py`. Rejected: every
argument passed through to `test_all.py`; a `--help` as `clean.sh` has.
Question 10.4.36.

2.19.4 `powershell\test_powershell.ps1 [--smoke-test | --normal-test]`:
- It reads `$args`, as `xsjs_stop.ps1` does, checks them before the
  administrator check and the lint step, and throws `test_usage` on
  anything else.
- After the lifecycle step that checks the status after
  `xsjs_install.ps1`, a step runs `wsl.exe --cd <checkout> -e python3
  python/test_all.py <option>`, its output and errors shown and logged as
  every step's are. `wsl --cd` takes the checkout's Windows path, `C:\src`
  as README.md supports, and starts in WSL's view of it, `/mnt/c/src`,
  as `xsjs_install.ps1` runs its builds there.
- Why there: it needs the ttyd that the install step builds, and nothing
  runs at that point, the first stop having removed the task, the port
  proxy and the firewall rule, so a failure leaves nothing open; and it
  fails before the start steps open ports.

Rejected: before the lint step, which tests the ttyd of an earlier
install; after the whole lifecycle; a copy of the checkout in the Linux
file system, which keeps the roots' SQLite files and locks off `/mnt/c`.
Questions 10.4.39 and 10.4.40.

2.19.5 Decision of the maintainer on 2026-10-21 (log 1.24.1, the answer to
10.4.38), class C: `test_powershell.ps1` stops on failure. The first failed
step ends the run: it throws `test_failed_step`, naming the step and the
log, and exits 1. The later steps, the last `xsjs_stop.ps1` among them, do
not run, so the state the lifecycle had at the failure is left as it is.
The tally goes. Before 1.24 the script carried on after a failed lifecycle
step and tallied the failed steps, so that its last stop still cleaned up
(log 1.23.10). Rejected by the maintainer: the reading this plan built
before 1.24, the first failure followed by `xsjs_stop.ps1` run once more as
a cleanup under a section `test_cleanup`, a carry on branch the request
does not name. Also rejected: the tally kept, as an exception to the rule.
Both are kept in plan 10.23.

2.19.6 `powershell/` is not in the whitelist (2.14). The edits to
`test_powershell.ps1` and `powershell/en-US/i18n.psd1` are neither
formatted by `reformat.py` nor scanned by `test_posix.py`; `test_lint.ps1`
formats and analyses them when `test_powershell.ps1` runs. Log 1.24.2
returns the PowerShell files to the whitelist; agent Q3's plan for log
1.24.2 to 1.24.9 says what follows from that. Since 1.6 (2.21),
`powershell/` is in the whitelist again: `test_posix.py` checks the
characters and comments of these files in WSL, and `test_lint.ps1` formats
and analyses them on Windows, reading the whitelist itself.

2.19.7 Found (log 1.23.9): `python/test_posix.py`, the checker of the
whitelisted files, and `test_posix.sh`, the target, share a stem. Both
names are the maintainer's.

2.19.8 The "shell scripts" of 2.15.2 stay as read. 1.4 and 1.5 bear on
that reading; question 10.4.41 holds the evidence.

### 2.20 The class B items approved by 1.4

From 1.4 (log task 1.22.1).

2.20.1 Approved as built, now class C (9.2):
- V's B1 (log 3.41.4): the 322 byte step script of `ts/test_substrate.ts`,
  a measured SHA-256 vector that is never run, keeps the text
  `engine.log(1, ...)` (2.15.6).
- K's B1 to B3 (log 3.42.2), which are Q's: `chunk_bytes` and
  `srv_buf_size` stay 1 MiB (2.13.7, 10.4.15 a)); nothing gates
  `db_load`, so `db_load` calls whose images, held at once, pass
  `blob_max` fault with `queue.queue_over` (2.13.8, 10.4.17 a)); the
  worker's export for the UI's `db.snapshot` stays `sqlite3_js_db_export`
  through the wasm heap (2.13.10, 10.4.16 a)).
- B4-1 (log 3.44.3): a UI put of `blob_max` + 1 is refused first by the AI
  worker's task queue with `queue.queue_over`, not by `wire.ts` with
  `wire.blobs_over`.
- B4-2 (log 3.44.4): `rung_decoder` writes the value of `blob_max` + 1
  bytes on the server behind the page's back, with `substrate.Store.kv_put`
  and a file path, before the page's `kv.get`, since no port can carry it.

Text that stated the opposite now states the built behaviour: here 2.13.7,
2.13.8, 2.13.10, 2.13.12, 2.15.6, 9.3, 10.3.1 and 10.4.15 to 10.4.17; in
the plan 3.10 and 8.7.6.

2.20.2 Not approved by 1.4, and still open (log 1.22.1): V's G1, a verbose
line written before `settings_set` throws, which was shown as a question
and not as class B; Q's B4, the value of `blob_max`; E's B1, the
`turn.append` applier; log 1.21.2, the formatter run; the reading of
2.15.2.

### 2.21 The PowerShell files back, and one table

From 1.6 (log tasks 1.24.2 to 1.24.9). Its first request, that
`test_powershell.ps1` stop on failure, is 2.19.5 (log 1.24.1).

2.21.1 Decision: the PowerShell files return to
`python/reformat_whitelist.txt` and are formatted again, on Windows, by
`powershell/test_lint.ps1`, which reads the whitelist itself; Linux formats
the other whitelisted files with `python/reformat.py`. In
`python/test_posix.py` they pass only two checks: the character check,
`non_ascii_check`, with a UTF-8 byte order mark allowed at their start, and
the comment check, `comments_check`, through a PowerShell comment lexer
written anew. Every other scan and every formatter in `python/` skips them.
What handles each extension, its formatter and its scanners, is one table
of data, `python/reformat_table.json`. READING of "whatever is needed" (log
1.24.4, 1.24.8): every change these need, the lexer and its tests among
them.

2.21.2 The whitelist (log 1.24.2). The six lines that 1.20.8 removed come
back after `clean.sh`, the top level names first: `xsjs_install.ps1`,
`xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/*.ps1`,
`powershell/en-US/*.psd1`. Each matches a file today: the four scripts at
the top; `test_lint.ps1`, `test_powershell.ps1` and `xsjs_util.ps1` in
`powershell/`; `i18n.psd1` in `powershell/en-US/`. The data file returns
with the scripts, as 10.4.21 b) described. 3.8 and the project rules'
whitelist rule hold for a new PowerShell file again; the exception of
2.14.5 goes.

2.21.3 The byte order mark (log 1.24.3). Where: in the codec, at the start
of a file only. Each row of the table names the codec that both checks
decode its files with. The `.ps1` and `.psd1` rows name `utf-8-sig`, which
drops one mark at the very start of a file and keeps any other U+FEFF,
which `non_ascii_check` then refuses at its line and column, the column
counted after the dropped mark. Every other row names `utf-8`, so a mark at
the start of a Python, TypeScript or other file is refused as before. For
which files: the whitelisted `.ps1` and `.psd1` files. Today five of them
start with a mark (`xsjs_install.ps1`, `xsjs_start.ps1`,
`powershell/test_powershell.ps1`, `powershell/xsjs_util.ps1`,
`powershell/en-US/i18n.psd1`, counted with `grep -c`) and three do not
(`xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/test_lint.ps1`, 6.4); both
kinds pass. `_NON_ASCII_ALLOWED` is unchanged. READING of "add the BOM to
the allow list": the mark is allowed through the codec of the rows of the
files that carry it, not by adding U+FEFF to `_NON_ASCII_ALLOWED`, where it
would be allowed anywhere in every whitelisted file, an invisible character
inside a line (project rule: unintentional invisibility is a bug), and a
Python file starting with it would fail in Python's tokenizer instead of in
the character check. Class B, question 10.4.44.

2.21.4 Found: log item 4.6.6 returns with the files. Lines 41 to 53 of
`xsjs_install.ps1`, its banner, hold U+2588, U+2591, U+2592 and U+2593,
which are outside `_NON_ASCII_ALLOWED`. `non_ascii_check` refuses the first
at `xsjs_install.ps1:41:19`, and since `main` checks the characters of
every file before any comment, `test_posix.py` stops there in every run,
its comment checks, audit, formatters and linter not reached. 1.6 names the
mark alone, and the maintainer answered the options of log item 4.6.6 with
1.3's removal, which 1.6 reverses; so nothing more is allowed until the
maintainer chooses. Class B: "whatever is needed" is not met for this
file. Question 10.4.45.

2.21.5 The table (log 1.24.6).
- Where: a data file, `python/reformat_table.json`, read by
  `reformat.table_read()`. `test_posix.py`'s `main` reaches it through
  `reformat`, which it already imports there, and passes each file's row to
  the checks. Why a data file: the request says data driven; a Python
  constant comes before the classes of its file, so a constant table could
  not hold `FileType` rows; and a shared module would make `reformat.py`,
  run as a script, set its bytecode prefix before importing it. The file is
  JSON, so it is not whitelisted (3.8). READING; question 10.4.46.
- Shape: one JSON object. Each key is an extension as `os.path.splitext`
  gives it, `.ts` for `a.d.ts`, its case kept. Each value is an object of
  exactly five keys, read into `reformat.FileType(comments, encoding,
  formatter, linter, system)`, a `NamedTuple`, so a missing or an extra key
  fails loud with Python's `TypeError`:
  - `comments`: the name of `test_posix.py`'s comment lexer, `none`,
    `python`, `shell`, `html`, `javascript` or `powershell`.
    `comments_find` dispatches on the name and raises for a name it does
    not know; no extension appears in its code.
  - `encoding`: the codec of `non_ascii_check` and `comments_check`.
  - `formatter`: the command `reformat.py` runs from the top directory with
    the row's files appended; empty in a `windows` row.
  - `linter`: the command `test_posix.py` runs from the top directory,
    after the formatters, with the row's files appended; empty when the row
    has none.
  - `system`: `linux` or `windows`, the system that formats and lints the
    row's files: `linux` by `reformat.py` and `test_posix.py`, `windows` by
    `powershell/test_lint.ps1`.
- Every row, as comments, encoding, formatter, linter, system:
  - `.html`: `html`, `utf-8`, prettier, none, `linux`;
  - `.js` and `.ts`: `javascript`, `utf-8`, prettier, none, `linux`;
  - `.md`: `none`, `utf-8`, `mdformat --check`, none, `linux`;
  - `.ps1` and `.psd1`: `powershell`, `utf-8-sig`, none, none, `windows`;
  - `.py` and `.pyi`: `python`, `utf-8`, `ruff format --config
    python/pyproject.toml --cache-dir build/ruff_cache`, `ruff check` with
    the same two options, `linux`;
  - `.sh`: `shell`, `utf-8`, `shfmt --list --write`, none, `linux`.

  Prettier is `prettier --write --no-config --print-width 79`. The
  commands are today's; the ruff paths are now relative to the top
  directory, from which both scripts run them.
- A whitelisted file whose extension has no row:
  `reformat.type_find(table, path)` raises `RuntimeError` `<path>: no row
  for '<extension>' in <table path>`. `reformat.reformat` finds every
  file's row before it runs a formatter, and `test_posix.py`'s `main` every
  file's row before its first check, so each fails at the first such file
  in path order, having done nothing. A file with no extension has the
  extension `''`, which has no row.
- "Formatted on Windows": a PowerShell row's `system` is `windows`.
  `reformat.reformat` runs a row's formatter only when the row's `system`
  is its `_SYSTEM`, `linux`, so the PowerShell rows are skipped by their
  data; no extension, and no PowerShell, is named in its code.
  `test_posix.py` runs a row's linter when it is not empty, and a `windows`
  row's is empty.
- What it replaces: the `match` on extensions of `comments_find`, the
  `endswith((".py", ".pyi"))` of `main` for `ruff check`, `reformat.py`'s
  `_FORMATTERS`, `_RUFF_FORMAT`, `_PRETTIER_FORMAT`, `_RUFF_CONFIG_PATH`
  and `_RUFF_CACHE_PATH`, and `test_posix.py`'s `_RUFF_CONFIG_PATH` and
  `_RUFF_CACHE_PATH`. A formatter or linter runs once per row, so `.py` and
  `.pyi` files are linted in two calls where `ruff check` had one.
- Not in the table: the synchronization audit of plan 8.6, which chooses
  `ts/*.ts` by its own glob and not from the whitelist, and `token_find`'s
  `utf-8-sig`, which reads only those files (2.14.3).

2.21.6 The PowerShell comment lexer (log 1.24.5, 1.24.8), written anew
from this text, its tests first in `python/test_test_posix.py` (2.21.10);
the code 1.20.8 removed is not recovered.
- `powershell_scan(path, text, i, closer, comments) -> int`, the shape of
  `shell_scan`: from the offset it adds each comment and returns the offset
  past the end of the text, or past the first unmatched `)` when `closer`
  is true; a `closer` scan that reaches the end fails as `<path>:<line>:
  unterminated`.
- A backtick escapes the next character, a line feed included, outside and
  inside double quoted strings.
- `'...'`: a single quoted string, in which `''` is one quote and nothing
  else escapes, read whole by `_POWERSHELL_SINGLE`, `'(?:[^']|'')*'`; with
  no closing quote it fails as `<path>:<line>: unterminated string`.
- `"..."`: `powershell_double_scan(path, text, i, comments) -> int`, the
  shape of `shell_double_scan`: a backtick or `""` skips two characters,
  and `$(` reads code to its `)` with `powershell_scan` and `closer` true,
  so a comment inside it is found; with no closing quote it fails as an
  unterminated string.
- Here strings: `@'` or `@"`, then only spaces or tabs to the end of the
  line (`_POWERSHELL_HERE`), read whole to the first line that starts with
  that quote and `@`, through `end_find` from the opening line's line feed,
  so an empty here string closes too; with no such line it fails as
  `end_find` does. A `$( )` inside `@" "@` is not read as code (plan
  10.25).
- `<#` starts a block comment to the next `#>`, `Comment(start, end, 2,
  2)`, wherever it stands outside a string; with no `#>` it fails as
  `end_find` does.
- `#` starts a line comment to the line feed, `Comment(start, end, 1, 0)`,
  at the start of the text or after a character of
  `_POWERSHELL_TOKEN_BREAK`: a space, a tab, a line feed or one of
  `;|&(){},`. After any other character it is part of a word, as in
  `a#b`.
- `(` and `)` count the depth that `closer` needs.
- The `<# #>` check of `comments_check` comes back as `tmp/handoff_20_L.md`
  G1 gives it: after `first_line` is computed, each comment of the group
  that starts with `<#` raises `<path>:<line>: <# #> comment below the top
  of the file. Use #.`, so a `<# #>` comment is allowed only as the header.
  The header comment of `test_posix.py` says so again.

2.21.7 `powershell/test_lint.ps1` (log 1.24.7). It reads
`python/reformat_whitelist.txt` itself, matches its lines by the rule of
2.21.8, and keeps the matched files whose extension, as
`[IO.Path]::GetExtension` gives it and compared case sensitively, is in its
own list `$extensions_`, `.ps1` and `.psd1`, the extensions of the table's
`windows` rows. It formats and analyses exactly those, in the order of
2.21.8: first the CRLF check of each, then `Invoke-Formatter` on each, then
`Invoke-ScriptAnalyzer -Path <file>` on each with the settings of
`_test_lint_get_lint_settings`. Its recursive `Get-ChildItem` and the
recursive `Invoke-ScriptAnalyzer` of the top directory go, and with them
`$globs_` and the `.psm1` it named, which no file uses and the table has no
row for. READING of "on their own": the script reads the whitelist and not
the table, so its two extensions are written in it beside the table's two
rows; question 10.4.47. Its messages are literal strings, as the file's are
and as tools write them; no `i18n.psd1` name is added.

2.21.8 The matching rule, one for both systems, built in
`reformat.paths_match(root_path, patterns)` and in `test_lint.ps1`'s
`_test_lint_get_paths`:
- The whitelist is read as UTF-8 and split into lines (`str.splitlines`,
  `[IO.File]::ReadAllLines`, which agree on a file of LF lines).
- A line is a path from the top directory, its parts joined by `/`, that
  fully matches ``(?:[^*?\[\]`/]+/)*[^\[\]`/]+``. Only its last part may
  hold `*`, any run of characters or none, and `?`, one character; no line
  holds `[`, `]` or a backtick, so Python's `fnmatch` and PowerShell's
  `-clike` read the same pattern. Any other line, an empty one among them,
  fails loud: `whitelist line '<line>' is not a path with * or ? in its last
  part only`.
- The part before the last `/` names a directory under the top, found by
  the file system; a line without `/` names the top. The names in that
  directory are listed (`os.listdir`, `Get-ChildItem -Force`), and a name
  matches when the last part matches it case sensitively
  (`fnmatch.fnmatchcase`, `-clike`) and, unless the last part starts with
  `.`, the name does not start with `.`, as in Python's `glob`.
- A line that matches no name, its directory missing among the causes,
  fails loud: `whitelist line '<line>' matches nothing under <top>`. A match
  that is not a file fails loud: `whitelist line '<line>' matches '<path>',
  which is not a file`, its path from the top joined by `/`.
- The files of every line, each once, are sorted by their paths from the
  top in ordinal order (`sorted`; a `SortedSet[string]` with
  `[StringComparer]::Ordinal`), so a first failure is the same file on both
  systems.
- The first line that fails stops the reading.

So whenever both systems accept the whitelist, they list the same files in
the same order. One difference stays: a directory part whose case differs
from the disk's fails on a case sensitive Linux file system and may pass on
Windows. `reformat.whitelist_paths()` keeps its name and calls
`paths_match` with the top directory and the whitelist's lines; `glob` is
no longer used. READING: the rule is enforced on both systems, so neither
accepts a line the other would list differently; question 10.4.48.

2.21.9 First failure in `test_lint.ps1` (project rule, "first failure
only"): the CRLF check prints the first file's fault and exits 1, where it
printed every file's; `Invoke-ScriptAnalyzer` runs file by file, and the
first file with results prints them and exits 1, where one run over the top
printed every file's. READING; question 10.4.49.

2.21.10 Tests first, then the code:
- `python/test_reformat.py`, new, a unit suite: the table's rows and shape,
  `type_find` on a row and on a missing one, `paths_match` on a scratch
  tree under `build/` (wildcards, the hidden rule, a literal line, a file
  matched twice, no match, a missing directory, a directory matched, case,
  each refused line form), and `whitelist_paths()` holding the eight
  PowerShell files of 2.21.2. It is listed in `test_all.py`'s `_MODULES`
  before `test_test_posix`, labelled `smoke-test` (2.18.4, S1).
- `python/test_test_posix.py`: the four tests 2.14.4 removed come back
  under their names, written for the codec: a mark passed at the start of a
  file read as `utf-8-sig`, a file without one passed, a mark after the
  start refused, and a refused character's column counted after the mark,
  with U+2588 of the banner. `test_others_refused` stays for a file read as
  `utf-8`. New: the PowerShell lexer's comments (a line, a block, one inside
  `$( )`), the strings and here strings it reads past, `#` inside a word
  and after a backtick, each unterminated form refused with its message;
  `comments_check` refusing `<# #>` below the header and reading a two line
  header past the mark; `comments_find` refusing a lexer name it does not
  know.
- No test runs `test_lint.ps1`; it is proved on Windows in the testing
  phase (log 2.22.4), as the two targets are (2.18.8).

2.21.11 The split by system, and what each official target runs (2.19,
unchanged by this part). Windows formats and analyses the PowerShell
files; Linux checks every whitelisted file and formats and lints the rest.
- `powershell/test_powershell.ps1`, on Windows: its lint step runs
  `test_lint.ps1`, which formats and analyses the whitelisted PowerShell
  files; its WSL step runs `python/test_all.py`, whose `test_posix.py`
  checks the characters and comments of every whitelisted file, the
  PowerShell ones included, audits `ts/*.ts`, formats the files of the
  `linux` rows and lints the Python ones.
- `test_posix.sh`, on Linux and later in Docker (plan 10.22): the same
  `python/test_all.py`; the PowerShell files are checked there and never
  formatted.
- `python/reformat.py` run alone formats the files of the `linux` rows, as
  the formatter run of log order 2.17 does.

2.21.12 Names and rules. New Python names, two words each:
`reformat.FileType`, `reformat.table_read`, `reformat.type_find`,
`reformat.paths_match`, `test_posix.powershell_scan` and
`test_posix.powershell_double_scan`, the last in the shape of
`shell_double_scan`. Constants at the top: `_SYSTEM`, `_TABLE_PATH` and
`_WHITELIST_LINE` in `reformat.py`; `_POWERSHELL_HERE`,
`_POWERSHELL_SINGLE` and `_POWERSHELL_TOKEN_BREAK` in `test_posix.py`.
Changed signatures: `non_ascii_check(path, encoding)`,
`comments_check(path, encoding, lexer)`, `comments_find(path, text,
lexer)`; `test_posix.main(arguments)` is Q2's (2.19). The PowerShell names
keep the file's style: `_test_lint_get_paths`, `$extensions_`,
`$whitelist_path_`, `$whitelist_line_`. No `API/` stub: `reformat.py` and
`test_posix.py` have none, as no tool has; the text one would hold is in
plan 10.25. No `i18n` name: the tools write f-strings and literal strings.
No setting and no timer.

2.21.13 Replaced (log 1.24.9): 2.14.1, 2.14.2, 2.14.3 but its last item,
2.14.4 but the file kept with `test_others_refused`, and 2.14.5. 2.14 is
kept where it stands with a note, and its text is kept whole in plan 10.25,
with every design this part considered and does not build.

### 2.22 The test driver and the infrastructure for testing

From 1.7 (log tasks 1.25.1 to 1.25.5).

2.22.1 Decision: the distinction, as the project rules state it since 1.7
(log 3.55). `python/test_all.py` is the test driver: it chooses, orders,
times and runs the test suites. The infrastructure for testing is the code
the drivers and tests are built from, such as the test categories and their
deadline. `python/test_test.py` tests the infrastructure for testing, not
the test driver. In this checkout:
- The test driver is `python/test_all.py`, the one runner of every suite
  (2.19.2), which both official targets call (2.19.1). Its table
  `_MODULES`, its order, its timers `timer_start` and `timer_stop`, its
  options and its `main` are the driver's, and no test module tests them.
  `test_wire.py` and `test_browser.py` run their rungs, and the driver runs
  them as its suites (2.18.2).
- The infrastructure for testing is `python/category.py`, which the driver
  and both of those runners are built from: the two labels, the options
  `--smoke-test` and `--normal-test`, the 120 s of a `smoke-test` run
  (`limit_seconds`), the alarm of each suite within it (`alarm_plan`,
  2.22.3) and `LabelBook`. The TAP modules `tap_producer` and
  `tap_consumer`, which the driver and the tests are built from too, are
  infrastructure as well.
- `python/test_test.py` holds the tests of `category.py` (2.22.4). The TAP
  modules keep their own test modules, which 1.2 asked for and which the
  driver runs first (2.4).

READING of "the stuff that is infrastructure for testing": the code the
driver, the runners and the tests are built from, which is not itself a
suite. `python/test_posix.py` is a suite, the rules' audit (2.18.4, S2),
tested by `python/test_test_posix.py`; neither changes. Question 10.4.53.

Found: the plans use "test driver" in two other senses, which this part
leaves as they stand: the maintainer's words in 2.10.1, about the provider
that testing depends on, and plan 6.8, where the forwarded operations
replayed into a test drive the server or the page.

2.22.2 The option (log 1.25.1). The maintainer's answer on 2026-10-21 to
T2a's class B item T2a-B1 (log 3.54.3), class C: option a), as built. The
options are `--smoke-test` and `--normal-test` by their full names:
`test_all.py`'s parser, and the parser the tests of `category.py` build,
refuse an abbreviation such as `--normal` with exit code 2 (`argparse`'s
`allow_abbrev=False`), and so `--fail` no longer means `--failfast`.
Rejected by the maintainer: b) abbreviations kept, the test's input changed
to one that is no prefix; c) `options_add` turning abbreviations off in
every runner's parser. Found: `test_wire.py` and `test_browser.py`, each
run alone, keep `argparse`'s default and take `--normal` for
`--normal-test`; `test_all.py` passes them the full name, and answer a)
leaves them as built. Question 10.4.50, answered.

2.22.3 `alarm_plan` moves from the driver into `python/category.py` (log
1.25.3). It is the deadline of a suite and of a `smoke-test` run: the
sooner of the suite's own seconds and the time left of the run's limit, the
suite's own seconds winning a tie, a refusal once that time is spent, and
no alarm with neither. That is infrastructure for testing, and
`category.py` already holds the limit, its 120 s and `limit_seconds`.
Built:
- `category.alarm_plan(what: str, seconds: float | None, limit: float |
  None, elapsed: float) -> tuple[float, str] | None`, its behaviour and its
  three message texts unchanged, the word `smoke-test` in them written with
  the module's `_SMOKE_TEST`. It stands after `limit_seconds`, and the
  module's header names it.
- `API/python/category.pyi` gains it, with the one line comment it has in
  the code: "The alarm of a suite, the sooner of its own seconds and the
  run's deadline."
- `test_all.py` loses it and calls `category.alarm_plan`; its `main`
  already imports `category`. `timer_start` and `timer_stop`, which arm
  and cancel `SIGALRM` for a plan, stay in the driver: they are how it runs
  a suite.

The plan chooses the reuse: a run's limit and the alarms made from it are
one deadline, kept in one module. Rejected:
- a new module of the infrastructure, such as `python/deadline.py` with its
  stub, which parts the alarms from the limit they are made from;
- `timer_start` and `timer_stop` moved too, which brings `signal` into the
  module that all three runners import, though only the driver arms an
  alarm;
- a module named `test`: `python/test.py` would shadow the standard
  library's `test` package for every script run from `python/`.

Question 10.4.52.

2.22.4 `python/test_test.py` (log 1.25.2, 1.25.3).
`python/test_test_all.py` is renamed `python/test_test.py`, which tests
only the infrastructure for testing:
- `TestModules` goes. It tested the driver's table `_MODULES`: each label
  accepted by `category.suite_runs`, the TAP modules' tests first, no name
  twice, `test_category` and `test_test_all` listed. With it go
  `modules_get`, `_MODULES_NAME` and `_CATEGORIES`. Nothing tests the table
  now; a label other than the two still raises in `suite_runs` when the
  driver reaches it. Its design is kept whole in plan 10.26.
- `TestAlarm` stays, its seven tests unchanged but for calling
  `category.alarm_plan`. The file imports `category` and not `test_all`.
- `python/test_category.py` joins it: `TestOptions`, `TestSelection`,
  `TestLimit` and `TestLabelBook` move in unchanged, with the constants and
  `parser_make` they use, and `python/test_category.py` goes. The imports
  are `import argparse, category, contextlib, io, unittest`.

Why joined: with `alarm_plan` in `category.py`, a `test_category.py` kept
beside `test_test.py` would part the tests of one module between two files
by nothing but the name the maintainer gave. `python/test_test.py` is the
test module of the infrastructure for testing as a whole, a name that no
module can match, `test` being the standard library's. Rejected:
`python/test_category.py` kept, and `python/test_test.py` holding
`TestAlarm` alone. Question 10.4.53.

2.22.5 The driver's table (log 1.25.4). The maintainer's answer on
2026-10-21 to T2a's class B item T2a-B2 (log 3.54.4), class C: c), no test
of the driver. `_MODULES` lists `("test_test", "smoke-test")`, last, in
place of `("test_category", "smoke-test")` and `("test_test_all",
"smoke-test")`, so the driver lists no test of itself; `test_test` tests
the infrastructure. The line `("test_reformat", "smoke-test")` of 2.21.10
stays. Rejected by the maintainer: a) the driver's table listing its own
test module, built until 1.7; b) that module run outside the table.
Question 10.4.51, answered.

2.22.6 The texts of 2.18.3 and 2.18.4 that name `python/test_category.py`,
`test_category` or `test_test_all` stay where they stand and say what 1.7
changed. The project rules hold the distinction (log 3.55), and plan 8.2
explains it.

2.22.7 Not built, each written out in plan 10.26: a test of the driver; the
checks of `TestModules` made by the driver itself before its first module,
which nothing asks for; the other options of 10.4.50 to 10.4.53.

2.22.8 Names and rules. No new name: `alarm_plan` keeps its two words, and
the moved test classes and methods keep theirs. `python/test_test.py`
matches the whitelist's `python/*.py`, so no line is added. No setting,
timer or `i18n` name. `category.py` names no test module, and `test_all.py`
lists `test_test`, which is not a test of itself.

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
created. `.md`, `.json` and `.css` files are not added. PowerShell files
are added again since 1.6 (2.21.2); from 1.3 to 1.6 they were not (2.14).

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

4.11 D12: TAP line grammar:
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
decoded with a line of at most 10 MiB and no blobs. The 10 MiB came from
the maintainer's sizes of 2.1, superseded by 2.13; it stays as this
default's constant (2.13.7, question 10.4.18).

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

5.12 `LineDecoder.idle()`. The `message_max` parameter of 2.1.5 is withdrawn
by 2.13.

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
`<root>/i18n/`; plan 9 shows `bootstrap.py` at the root.

5.19 The setting `db_soft_bytes`; the tools `db_stats`, `db_compact`,
`db_unload` and `db_load`. The settings `message_max` and `queue_max` are
withdrawn by 2.13.

5.20 The modules `tap_producer` and `tap_consumer` in place of plan 7.2's
`tap/producer.py` and `tap/consumer.py` and plan 7.3's `tap.ts`.

5.21 `i18n` names beyond the work orders: `bootstrap.option_repeated`,
`bootstrap.main_loop_refused`, `main_loop.input_partial`, and the
`console_view.*` phase names.

5.22 The API additions of agents D, U2 and B0 of log `tmp/tasks_20_1601.md`
(records 3.12, 3.13 and 3.16; their texts are in `tmp/api_texts_20_2258.md`)
are accepted by the maintainer's 1.3 (log task 1.20.2), except those that
2.13 removes. 5.23 to 5.26 say which; 7.12 applies them.

5.23 Dropped, agent D's `db.chunk` design: it existed only to carry a
snapshot in pieces under `message_max`, and 2.13 makes the blob window the
largest database, so `db.snapshot` is one blob again (plan 6.8). Each name
below served only the pieces:
- the line type `db.chunk` and its payload `DbChunk {snapshot, offset,
  size}`;
- the head reply of `db.snapshot`, `DbSnapshotReply {snapshot, size,
  sha256, seq}` with no blob, and the server keeping the bytes under a
  number;
- TypeScript `substrate.SnapshotFetch` with `db`, `head_line()`,
  `head_take(reply)`, `piece_take(data)`, `seq_sent()` and `bytes_get()`,
  and `substrate.SnapshotHead`;
- TypeScript `Store.snapshot_keep(db)`, `Store.snapshot_read(snapshot,
  offset, size)` and `Store.blob_take(data)`;
- TypeScript `worker_ai.StartStore.blob_take` and
  `worker_ai.ChainParts.settings_get`, which read `message_max` and
  `line_max` for the pieces;
- Python `substrate.SnapshotHead`, `Store.snapshot_keep`,
  `Store.snapshot_read` and `engine_db.db_chunk`;
- the strings of the pieces, `substrate.piece_none`,
  `substrate.piece_size`, `substrate.snapshot_range` and
  `substrate.snapshot_unknown`. `substrate.snapshot_digest` stays, as the
  one blob's digest is checked (2.13.8), and so do
  `substrate.cache_unknown` and `substrate.fill_desync` of log task
  1.18.6.

5.24 Accepted, agent D's TypeScript `Store` methods of log tasks 1.18.6 and
1.18.18.2:
- `kv_held(ref, db?)`: whether this side holds a value's bytes, in its row
  or a file;
- `cache_fill(ref, data, db?)`: puts back the cache file of a value from
  bytes or a cache handle whose digest is the row's;
- `cache_evict(db, keep, budget)`: frees a database's cached files by key,
  but those the kept refs and other databases name, until they fit the
  budget; returns the count freed.

5.25 Accepted, agent U2's additions of log tasks 1.18.23.4 and 1.18.23.5:
`page.test_engine(run: (tasks: queue.TaskQueue) => void): void`,
`boot.test_engine` with the same signature, the test bundle only module
`test_hook` with `engine_run(): void`, and `page_build.page_build(name:
str, test: bool, template: str) -> str`. `page` has no stub and
`API/ts/boot.d.ts` leaves test only functions out, as it does
`test_page`; only `API/python/page_build.pyi` changes.

5.26 Accepted, agent B0's additions to `devtools.py` of log tasks 1.18.23.4
and 1.18.11.1: `ProtocolClient.session_call(session_id, method, params)`,
`Browser.trace_start(categories)`, `Browser.trace_end()`,
`Browser.worker_pause(name)`, `blocking_categories()`,
`blocking_find(events)`, and the `PageEvents` fields `trace`,
`trace_done`, `trace_lost`, `workers` and `paused`. Its replacement text of
`API/python/devtools.pyi` is applied as written; that text declares
`PageEvents.lifecycle` only, so the five fields stay out of the stub.

## 6 Open questions found while writing the code

6.3 Answered by log task 1.18.23.2 of `tmp/tasks_20_1601.md`: `exit_done`
returns the console view to idle and ctrl-0 on an idle view sends
`console.open` again, so the console reopens without a page load; its rung
runs open, exit, open (log item 4.6.16, approved, 2.17).

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

6.11 argparse still accepts `-h`, so a client `--url-arg -h` prints help to
the pty and exits 0.

6.12 The xterm `Terminal` constructor options were written from memory and
not checked against the pinned 5.5.0 typings. The resize path is
unreachable without a fit addon.

6.13 Answered by log item 4.6.1 of `tmp/tasks_20_1601.md`, approved (2.17):
the server seeds the `_files` row `provider/script.json` from
`python/seed/provider_script.json` when it is missing, and the scripted
provider reads its Script from `/_files/provider/script.json`. The seeded
Script has one node and no replies, so input on a root without a test
driver faults.

6.14 The Lookup Accelerator of the project rules was removed by the
maintainer's commit 168ac16. Updating it (old task 1.9.3) is held.

## 7 Edits proposed for the maintainer's files

7.1 Plan, sizes:
- 3.7: "`blob_max`, 10 MiB, and `message_max`, 10 MiB, a line and its
  blobs together". Applied by task 1.16.10.
- 3.8: "Memory per connection is bounded by `message_max`". Applied by
  task 1.16.10 as "Memory per message", the words of 2.1.7, with the
  `queue_max` bound of 2.1.3 and 2.1.6 beside it.
- 6.9: add `message_max`, `queue_max` and `db_soft_bytes`. Applied by
  task 1.16.10.
- 8.4, 8.7.3 and 8.7.6: the sizes of 2.1.8. Applied by task 1.16.10,
  with 3.10 and the 128 MiB rendering of 2.6.

7.2 Plan, protections:
- 5.5: delete "The substrate's own tables and `_settings` refuse writes."
  Applied by task 1.16.10, replaced by "SQL rules are not a security
  boundary: no table or database refuses a write."
- 6.2: delete "`_settings` is immutable" as an enforced rule. Applied by
  task 1.16.10.
- 8.7.4: delete "a write to a `_` table or to `_settings` refused".
  Applied by task 1.16.10.
- 11: delete the `sql_run` guarding item. Applied by task 1.16.10 as a
  rewrite, not a deletion: the item now records that both the `EXPLAIN`
  guard and the refusal by name are decided against, so neither returns.

7.3 Plan 2.3 and 7.2: `verbose.exec(level, argv, argv_verbose)`. Applied
by task 1.16.10, with the reading of 2.5.2 marked Unconfirmed.

7.4 Plan 7.2, 7.3, 8.1 and 8.7.1: the TAP modules of 2.4. Applied by
task 1.16.10, with 0.4, 7.4 and 8.2, and the readings of 2.4.2 and 2.4.3
marked Unconfirmed.

7.5 Plan 3.9: ids per thread queue (D2). Not applied by task 1.16.10: D2
is a default of section 4, not a decision of the maintainer.

7.6 Plan 6.8: `since` on `db.create` and `db.drop`, and a new database at
`seq` 0 (D1). Not applied by task 1.16.10: D1 is a default of section 4.

7.7 Plan 9: the root layout of 5.18. Not applied by task 1.16.10: 5.18 is
a departure awaiting acceptance.

7.8 Plan 10: a section with the design of 2.2. Applied by task 1.16.10 as
plan 6.10, not in plan 10: plan 10 holds what is not built, and 2.2 is
built.

7.9 `API/`:
- `python/verbose.pyi`: `exec`. Applied by task 1.16.10, with
  `python/bootstrap.pyi`'s comment.
- `python/jslb.pyi` and `ts/jslb.d.ts`: `message_max`, `idle()`, `size`.
  Not applied by task 1.16.10: 5.12 and 5.15 await acceptance.
- `python/main_loop.pyi`: `loop_prepare`. Not applied by task 1.16.10:
  5.1 awaits acceptance.
- `python/substrate.pyi`: `seq_get`. Not applied by task 1.16.10: 5.4
  awaits acceptance. Its `sql_run` refusal comment is removed (2.3).
- `python/engine_db.pyi`: `since`. Not applied by task 1.16.10: D1.
- `ts/lines.d.ts`:
  - `DbName` gets `since`;
  - `ConsoleOpenReply { token: string; }`;
  - `replicate.*` and `ui.console_reply`;
  - the `http.request` reply comment.

  Not applied by task 1.16.10: D1, D23, 5.17, 5.14 and a rule of the
  review, none a decision of the maintainer. `Hello` gains
  `provider_info` and `ProviderInfo` (2.10).
- `settings.json`: the sizes and new keys of 2.1 and 2.2. Applied by
  task 1.16.10, with the three provider keys removed (2.10), and the
  same in `ts/settings.d.ts`.
- `mcp/tools.json`: `sql_run`'s description without the refusal, and the
  four tools of 2.2.3. The description applied by task 1.16.10; the four
  tools not: 5.19 lists them for acceptance and 2.2.3 states their names
  and arguments, not their descriptions and schemas.
- `ts/tap.d.ts` and `ts/unittest.d.ts`: 2.4. `ts/tap.d.ts` applied by
  task 1.16.10 as `ts/tap_producer.d.ts`, with `python/tap/producer.pyi`
  and `python/tap/consumer.pyi` moved to `python/tap_producer.pyi` and
  `python/tap_consumer.pyi`; `ts/unittest.d.ts` not: its run methods are
  5.10, awaiting acceptance.
- `ts/boot.d.ts`: "`self.name` is empty on the main thread". Not applied
  by task 1.16.10: a finding of the code, not a decision.
- `ts/utility.d.ts`: `json_text` is `JSON.stringify` with number checks.
  Not applied by task 1.16.10: D26.
- `ts/media.d.ts` and `ts/console_view.d.ts`: 5.13 and 5.14. Not
  applied by task 1.16.10: awaiting acceptance.

7.11 Applied by task 1.16.10 beyond 7.1 to 7.9:
- the edits of 2.8.3: `API/mcp/tools.json` without the `_meta` of
  `source_put` and `system_restart`, plan 4.6 and 5.5 with the permit
  set `console_run`, plan 1.3 and 8.6 naming `boot.ts` (2.7);
- plan 5.5's Unconfirmed tool limits on `db_create` replaced by the
  decision that no tool limit refuses it (2.2.6, 2.8);
- the plan's "recorded" operation sequences made sequences the test
  builds;
- the provider file in the plan (5.2, 6.9, 9), `API/settings.json`,
  `API/ts/settings.d.ts`, `API/ts/lines.d.ts`, and the `info` parameter
  in `API/ts/agent.d.ts` and `API/ts/tools_browser.d.ts` (2.10);
- the timers in plan 4.7 (2.6), invisibility in plan 2.6 (2.11), the
  formatter in plan 0.4 (2.12), MB as MiB in plan 0.5;
- `API/sql/substrate.sql`'s refusal sentence removed (2.3);
- the whitelist line `API/python/tap/*.pyi` removed.

7.12 Edits for 1.20, applied by agent A2. Each names its file, what goes,
what comes and the decision behind it. Nothing outside the list changes.
A stub's drift from the code that no decision here covers is left as it
is.

7.12.1 `API/settings.json` (2.13.2, 2.13.5, 2.15.3, 2.16.7):
- `blob_max` becomes 2147483391;
- `message_max` and `queue_max` go;
- `verbose_forward` goes;
- `"turn_compact_tokens": 65536` becomes `"turn_compact_turns": 64` in
  the same place;
- the key order is then `debug`, `queue_synchronous`, `verbose_level`,
  `verbose_ring`, `line_max`, `blob_max`, `overflow_bytes`, `chunk_bytes`,
  `srv_buf_size`, `media_db_bytes`, `files_browser_bytes`,
  `db_soft_bytes`, `turn_compact_turns`, `long_task_ms`, `provider`, every
  other value unchanged.

7.12.2 `API/ts/settings.d.ts`, interface `Settings`, the same keys:
`verbose_forward: boolean;`, `message_max: number;` and `queue_max:
number;` go; `turn_compact_tokens: number;` becomes `turn_compact_turns:
number;`.

7.12.3 `API/python/jslb.pyi`: `LineDecoder.__init__(self, line_max: int,
blob_max: int, overflow_bytes: int, sink_make: Callable[[Object], str])`
already has the signature of 2.13.7 and stays. Above `class LineDecoder:`
comes this one line. `idle()` stays out (5.12 awaits acceptance).

```text
# WireError: a line over `line_max`, or blobs over `blob_max` in all.
```

7.12.4 `API/ts/jslb.d.ts`: the constructor `(line_max, blob_max,
overflow_bytes, sink)` stays. Above `class LineDecoder {` comes this one
line, indented two spaces:

```text
// WireError: a line over `line_max`, or blobs over `blob_max` in all.
```

7.12.5 `API/ts/lines.d.ts`:
- `db.snapshot` stays as it is: the table row `DbSnapshotReply + 1`,
  `DbSnapshotReply { sha256: Sha256; seq: number; }` and its comment.
  Agent D's text for `db.snapshot` and `db.chunk` is not applied (5.23);
  no `db.chunk` row and no `DbChunk`.
- `VerboseLine` loses `level: number;` and is `{ at: number; text:
  string; }` (2.15.6).

7.12.6 `API/ts/agent.d.ts`, the comment above `handlers_register` (log
item 4.6.2, 2.17), indented two spaces; the signature stays:

```text
// The turn as a chain of tasks on the AI thread. `ai.say` and
// `ai.click` append the player's turn, submit the provider request and
// sleep with `ai.model_reply`. `ai.model_reply` submits each tool call
// of a reply and sleeps with `ai.tool_reply`, storing nothing yet;
// `ai.tool_reply` stores that reply and its tool results together in
// one transaction and submits the next provider request. A reply with
// no tool calls is stored and ends the turn with `TurnEnd`. No stored
// call lacks its result. In debug mode the queue log is the transcript
// of the turn.
```

7.12.7 `API/ts/substrate.d.ts`, class `Store`:
- the constructor gains `compact_turns: number` after `overflow_bytes`:
  `constructor(sqlite3: unknown, root: string, overflow_bytes: number,
  compact_turns: number);` (2.16.7);
- above `turn_append(` comes this one line (2.16.5):

  ```text
  // A `user` turn on a scene of `compact_turns` turns first compacts them.
  ```

- after `db_restore(...)` come agent D's three methods (5.24), each with
  its one line comment:
  - `// Whether this side holds a value's bytes, in its row or a file.`
    then `kv_held(ref: lines.KvRef, db?: string): boolean;`
  - `// Puts back a value's cache file from bytes with the row's digest.`
    then `cache_fill(ref: lines.KvRef, data: Uint8Array | string, db?:
    string): void;`
  - `// Frees a database's unkept cache files to the budget; their count.`
    then `cache_evict(db: string, keep: readonly string[], budget:
    number): number;`
- nothing of `SnapshotFetch`, `SnapshotHead`, `snapshot_keep`,
  `snapshot_read` or `blob_take` (5.23).

7.12.8 `API/python/substrate.pyi` and `API/python/engine_db.pyi`: nothing
of agent D's NEEDS 3 and 4 (5.23). `engine_db.pyi`'s `db_snapshot`
comment already says one blob.

7.12.9 `API/python/page_build.pyi`, replaced whole by agent U2's text
(5.25), section 2.2 of `tmp/api_texts_20_2258.md`:

```text
# Builds `build/<name>.html` from `html/<template>`. Returns its hash.
def page_build(name: str, test: bool, template: str) -> str: ...
```

7.12.10 `API/python/devtools.pyi`, replaced whole by agent B0's text, the
Python block of section 3.2 of `tmp/api_texts_20_2258.md`, from `from
collections.abc import Callable` to the line of `blocking_find`, as
written (5.26).

7.12.11 `API/python/verbose.pyi`, replaced whole (2.15.4, 2.15.5):

```text
from typing import NamedTuple

# One line: milliseconds since the epoch and its text.
class LogLine(NamedTuple):
    at: int
    text: str

# Writes one line to `_verbose`, unbuffered, and to the ring of `verbose_ring`.
def log(text: str) -> None: ...

# The last `count` lines of the ring, oldest first.
def history_get(count: int) -> list[LogLine]: ...

# The shell's runner: `argv` at level 0 or 1, `argv_verbose` raw at 2.
def exec(level: int, argv: list[str], argv_verbose: list[str]) -> int: ...
```

7.12.12 `API/ts/verbose.d.ts`, replaced whole (2.15.6):

```text
declare namespace verbose {
  // Writes one line to the ring of `verbose_ring` lines and hands it to
  // the sink.
  function log(text: string): void;

  // The last `count` lines of the ring, oldest first.
  function history_get(count: number): lines.VerboseLine[];

  // The one consumer of new lines: the thread's queue, which batches
  // them into `verbose.put` when `debug` is on.
  function sink_set(fn: (line: lines.VerboseLine) => void): void;
}
```

7.12.13 `API/sql/verbose.sql`: the line `level  INTEGER NOT NULL,` goes
(2.15.5).

7.12.14 `API/ts/queue.d.ts`: in the comment above `class TaskQueue`, "Every
submit, dispatch, sleep, wake and reply is a verbose line at level 2."
becomes "In debug mode every submit, dispatch, sleep, wake and reply is a
verbose line." (2.15.6).

7.12.15 `API/ts/script.d.ts`, replaced whole (2.15.6):

```text
declare namespace script {
  // What a run returned: the value or the exception with its stack, and
  // the verbose lines the run wrote.
  interface ScriptResult {
    value?: unknown;
    error?: string;
    stack?: string;
    lines: lines.VerboseLine[];
  }

  // The frozen object a script receives as `engine`: the store's
  // methods, `verbose.log` and `i18n`.
  interface Engine {
    store: substrate.Store;
    log(text: string): void;
    i18n(name: string, ...args: unknown[]): string;
  }

  // Runs `/_files/script/<name>.js` with `new Function("engine", "args",
  // text)` inside the calling task; with `trace`, as `script_debug` runs
  // it, each substrate call is traced first.
  function script_run(
    store: substrate.Store,
    name: string,
    args: unknown,
    trace: boolean
  ): ScriptResult;
}
```

7.12.16 `API/mcp/tools.json` (2.15.6): the `verbose_level` tool object goes;
`script_debug`'s description becomes "Run the script as script_run does,
tracing every substrate call it makes first.".

7.12.17 `API/ts/tools_browser.d.ts`: `verbose_level` leaves the tool list of
the comment (2.15.6).

7.12.18 `API/python/bootstrap.pyi`, replaced whole (2.15.3):

```text
# `python3 bootstrap.py --root <root> [console]`. Returns the exit code.
# The engine role takes the lock, sets raw mode, writes `hello` and runs the
# main loop file. The console role runs dash through `verbose.exec` at the
# setting `verbose_level` in debug mode and exits 1 otherwise. Immutable
# outside debug mode.
def bootstrap_run(argv: list[str]) -> int: ...
```

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
- the messages of section 1, 1.3 among them (log `tmp/tasks_20_1601.md`,
  1.20);
- the project rules as they bear on the job.

9.1 D, satisfied without modification:
- the job is run as a coordinator with many agents;
- nothing is run, built or tested between handoffs or at all;
- files are locked by renaming for each edit, and no lock remains between
  waves;
- nothing is staged or committed by an agent;
- authorship is ascribed to no non-person;
- the lost agents are recorded and their tasks resumed;
- this file keeps the maintainer's messages of section 1 verbatim.

For 1.3:
- one `settings.json` entry, `blob_max`, is the window of every blob, and
  `db.snapshot` is one blob again (2.13);
- the PowerShell files leave the whitelist and are not scanned (2.14.1),
  reversed by 1.6 (2.21);
- verbose levels belong to the shell only; the server and the runtime
  have `debug` alone (2.15.1);
- compaction counts events and runs at a threshold (2.16.1);
- the class B items approved are recorded and the text that contradicted
  them changed (2.17).

For 1.4 and 1.5:
- two categories of test suite under the maintainer's names (2.18.1);
- `test_posix.sh` is the script's name and it calls `python/test_all.py`;
  `test_powershell.ps1` calls `python/test_all.py` inside WSL; the two are
  the project's official test targets (2.19.1);
- the categories reach `python/test_all.py` from both targets (2.19.2);
- the approved class B items are recorded and the text that contradicted
  them changed (2.20);
- 1.4 is kept verbatim in section 1.

For 1.6:
- the PowerShell reformatting comes back: the six whitelist lines return,
  and `test_lint.ps1` formats the whitelisted PowerShell files (2.21.2,
  2.21.7);
- the PowerShell files pass only the comment check and the character check
  of `test_posix.py`; every other scan and every formatter in `python/`
  skips them (2.21.1, 2.21.5, 2.21.6);
- the table of extension to formatter and scanners is data,
  `python/reformat_table.json` (2.21.5);
- the PowerShell scripts read the whitelist themselves; Windows formats the
  PowerShell files and Linux the rest (2.21.7, 2.21.11);
- 1.6 is kept verbatim in section 1.

For 1.7:
- `--normal-test` stays as built (2.22.2);
- `python/test_test_all.py` is renamed `python/test_test.py` (2.22.4);
- `python/test_test.py` tests the infrastructure for testing and not the
  test driver: `TestModules` goes, and `alarm_plan` moves into
  `python/category.py` so that `TestAlarm` stays (2.22.3, 2.22.4);
- the project rules and the two plans explain the distinction between the
  test driver and the infrastructure for testing (2.22.1, plan 8.2).

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

For 1.3, the items of log `tmp/tasks_20_1601.md`:
- 4.5, class A, accepted as recorded ("all A are fine");
- the sizes of 1.1 and 2.1, 10 MiB per blob and per message and 100 MiB
  per queue, superseded by `blob_max` (2.13.13);
- agent D's `db.chunk` pieces, removed (2.13.8, 5.23);
- the PowerShell files in the whitelist and scanned, withdrawn (2.14);
  restored by 1.6, scanned for their comments and characters only (2.21);
- verbose levels in the server and the runtime, deferred "for now" (2.15,
  plan 10.19);
- the compaction estimate sent to the AI, bytes counted as tokens and the
  AI deciding, replaced by the counter (2.16, plan 10.20);
- 4.6.1, approved: the Script stays at `/_files/provider/script.json`,
  seeded with no replies, so input on a root without a test driver faults;
- 4.6.2, approved: a tool call turn is stored with its results after the
  tools run (plan 5.3 and `API/ts/agent.d.ts` changed);
- 4.6.4, approved: Python stores doubles above 2^53, which the TypeScript
  store refuses with `substrate.integer_range`;
- 4.6.5, approved: the vectors go to `build/vectors`, not
  `python/vectors/` (plan 8.3 changed);
- 4.6.7, approved: a crash before the log opens, from the arguments, raw
  mode, the engine lock or the settings, reaches only the terminal;
- 4.6.8.1, approved: with both shown, the overlay below the console
  scrolls the console's top rows out (plan 2.6 changed);
- 4.6.8.2, approved: the subtitle band lies over the bottom strip of the
  fixed image (plan 2.6 changed);
- 4.6.10, approved: the page replay compares the browser's copy with the
  server's, not through `test_wire`'s private reader (plan 8.7.7
  changed);
- 4.6.12, approved: seven files under `tmp/` still mention `DATA/`, and
  `constants.recorded_png` is probably the deleted DATA PNG;
- 4.6.13.1, approved: the stress test runs `_STRESS_ROUNDS`, 8 rounds, a
  count chosen by its writer;
- 4.6.13.2, approved: the echo rungs keep the 251 byte period pattern, not
  non repetitive data;
- 4.6.14, approved: `ConsoleView.close_request` exists and no UI action
  calls it;
- 4.6.15.1, approved: the drain rungs stall ttyd with SIGSTOP;
- 4.6.15.2, approved: the drain timer rung posts a burst sized from the
  queue bound, 11 lines under `queue_max`; the bound is now `blob_max`;
- 4.6.15.3, approved: the drain poll rung sleeps 5 s, then checks the poll
  once;
- 4.6.16, approved: `rung_console_reopen` runs open, exit, open (6.3
  changed);
- 4.6.17, approved: `rung_http_timeout` writes its own `provider.json`
  (2.10.2 and plan 6.9 changed);
- 4.6.18.1, approved: a test engine page outside the production bundle
  (plan 2.5 changed);
- 4.6.18.2, approved: the largest put is measured in the start state it is
  used in;
- 4.6.18.3, approved: `rung_ui_upload` expected `worker_ai.queue_over`
  after about 11 of its 15 puts; under 2.13 its 135 MiB fits `blob_max`,
  so its expectation changes;
- 4.6.18.4, approved: only synchronous network loads are detected, under
  three candidate Chrome event names (plan 8.4 changed);
- 4.6.19, approved: `test_wal_left` cannot apply to the SAH pool, which has
  no WAL, and nothing is built for it (plan 8.7.7 changed).

For 1.4 and 1.5 (2.20):
- V's B1, approved: the step script of `ts/test_substrate.ts` keeps
  `engine.log(1, ...)`;
- K's and Q's B1, approved: `chunk_bytes` and `srv_buf_size` stay 1 MiB;
- K's and Q's B2, approved: `db_load` calls whose images, held at once,
  pass `blob_max` fault with `queue.queue_over`;
- K's and Q's B3, approved: the worker's export stays
  `sqlite3_js_db_export` through the wasm heap;
- B4-1, approved: a UI put of `blob_max` + 1 is refused first with
  `queue.queue_over` (plan 8.7.6 changed);
- B4-2, approved: `rung_decoder` writes the over-size value on the server
  (plan 8.7.6 changed);
- the name `test_all.sh` of 1.4, replaced by `test_posix.sh` in 1.5;
- 10.4.38, answered by the maintainer on 2026-10-21 (log 1.24.1):
  `test_powershell.ps1` stops at its first failed step and runs no later
  step, the last stop included; the cleanup stop this plan built before
  and the tally are rejected (2.19.5);
- `test_posix.sh` in Docker, later by the maintainer's words: designed in
  plan 10.22 and not built.

For 1.6:
- the PowerShell files outside the whitelist and unscanned (2.14, from
  1.3), reversed; the replaced text is kept whole in plan 10.25.

For 1.7:
- T2a-B1 (log 3.54.3), answered by the maintainer on 2026-10-21 (log
  1.25.1): a), the options by their full names, abbreviations refused by
  `test_all.py` and the parser of the tests (2.22.2, 10.4.50);
- T2a-B2 (log 3.54.4), answered by the maintainer on 2026-10-21 (log
  1.25.4): c), the driver lists `test_test`, which tests the
  infrastructure, and no test of itself (2.22.5, 10.4.51);
- `TestModules`, the tests of the driver's table, removed by 1.7; its
  design is kept whole in plan 10.26.

9.3 B, unsatisfied or modified with cause and not yet confirmed:
- the defaults of section 4;
- the API additions and departures of section 5;
- the READINGS of 2.2 ("MVC"), 2.4.2 (module names), 2.4.3 (tappy names
  from memory) and 2.5.2 (`argv_verbose`);
- 1.9.3, held;
- the open questions of section 6.

For 1.3:
- the value of `blob_max`, documented and not measured, Unconfirmed until
  the rung of 2.13.9 (2.13.5);
- the READINGS of 2.13.2 (the name), 2.13.3 (a window counts blob bytes),
  2.13.6 (the caching operation), 2.13.7 (thresholds keep their settings;
  the hello's line bound), 2.13.11 (no refusal past `blob_max`), 2.13.12
  (proofs at the window's edge), 2.14.2 (the data files), 2.14.4 (what is
  left of `test_test_posix.py`), 2.15.2 to 2.15.6 (the shell scripts, the
  settings, level 1, the server's trace, the runtime), 2.16.2 to 2.16.7
  (the events, the counter, where it runs, the summary, the threshold);
- class B until 1.4, class C since (9.2, 2.20): `chunk_bytes` and
  `srv_buf_size` cannot be the window (2.13.7); parallel `db_load` calls
  fault past `blob_max` (2.13.8, log item 4.6.3.1); the worker's export
  through its heap cannot carry `blob_max` (2.13.10).

For 1.4 and 1.5:
- every label and the fit in 2 minutes, Unconfirmed until the testing
  phase measures them (2.18.4, log 1.22.8);
- the READINGS of 2.18.2 (the grain of a label), 2.18.4 (the smoke set),
  2.18.6 (the limit fails loud), 2.18.7 and 2.19.3 (options and
  defaults), 2.19.4 (where and how the WSL step runs), 2.18.5 (the
  formatters in the smoke run) and 2.18.8 (no test of the targets);
- 1.5 kept in section 1 with the project rules file's name elided
  (10.4.43).

For 1.6:
- the byte order mark allowed by the codec of the PowerShell rows, at the
  start of a file only, not added to `_NON_ASCII_ALLOWED` (2.21.3,
  10.4.44);
- the banner of `xsjs_install.ps1`: "whatever is needed" is not met for
  it, and `test_posix.py` stops there until the maintainer chooses (2.21.4,
  10.4.45);
- the READINGS of 2.21.1 ("whatever is needed"), 2.21.5 (the data file),
  2.21.7 ("on their own": the whitelist and not the table), 2.21.8 (the
  rule enforced on both systems) and 2.21.9 (first failure in
  `test_lint.ps1`).

For 1.7:
- the READINGS of 2.22.1 (what the infrastructure for testing is, the TAP
  modules keeping their own tests), 2.22.3 (`alarm_plan` in `category.py`)
  and 2.22.4 (`python/test_category.py` joined into `python/test_test.py`);
- 1.7 kept in section 1 with the project rules file's name elided
  (10.4.43).

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

10.3.1 For 1.3: this plan satisfies every request of 1.3 as written, with
the readings of 9.3 built now and reworked if an answer differs. Three
class B items cannot be satisfied as worded without the maintainer, each
with its question: `chunk_bytes` and `srv_buf_size` as windows (10.4.15),
parallel `db_load` calls (10.4.17), and the worker's export (10.4.16).
The value of `blob_max` waits on the measurement of 2.13.9 (10.4.13). No
class A item of 1.3 was found. In 10.4.11 to 10.4.32 "(built)" marks the
plan's choice, which the agents of log order 2.14 build. 1.4 approved the
three class B items as built (2.20).

10.3.2 For 1.4 and 1.5: this plan satisfies 1.4 and 1.5 as written, with
the readings of 9.3 built now and reworked if an answer differs. One
request cannot be satisfied as worded without a measurement: that the
smoke-test suites fit in 2 minutes (log 1.22.8), which nothing may measure
before the testing phase; the run reports each suite's seconds and fails
loud past 120 s, so the testing phase confirms or corrects the labels.
`test_powershell.ps1` stops at its first failed step by the maintainer's
answer to 10.4.38 (log 1.24.1, 2.19.5). No class A item of 1.4 or 1.5 was
found. In 10.4.33 to 10.4.43 "(built)" marks the plan's choice, which
agent T2 of log order 2.20.2 builds.

10.3.3 For 1.6: this plan satisfies 1.6 as written, with the readings of
9.3 built now and reworked if an answer differs, but for two class B
items. The byte order mark is allowed through the codec of the rows of the
files that carry it, at their start only, and not added to
`_NON_ASCII_ALLOWED` (10.4.44). The banner of `xsjs_install.ps1` stops
`test_posix.py`, which "whatever is needed" would cover, until the
maintainer chooses among the options log item 4.6.6 offered (10.4.45). No
class A item of 1.6 was found. In 10.4.44 to 10.4.49 "(built)" marks the
plan's choice, which agent T3 of log order 2.22.3 builds; 10.4.21 and
10.4.22 are affected.

10.3.4 For 1.7: this plan satisfies 1.7 as written, with the readings of
9.3 built now and reworked if an answer differs. Two class B items of the
log, T2a-B1 and T2a-B2, are answered by 1.7 and are class C (9.2, 10.4.50,
10.4.51). No class A item of 1.7 was found. In 10.4.52 and 10.4.53
"(built)" marks the plan's choice, which agent Q4 of log order 2.24.2
builds.

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
- a) D12, plan first with bare names (built);
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

10.4.7 The console after `console.exit`:
- a) closed until the next page load;
- b) reopenable from ctrl-0 (built by log task 1.18.23.2 of
  `tmp/tasks_20_1601.md`, the maintainer's request; 6.3).

10.4.9 The Lookup Accelerator:
- a) stays removed (held);
- b) the maintainer writes it;
- c) an agent writes it.

10.4.10 Section 4's defaults:
- a) accept all;
- b) name the ones to change.

10.4.11 The one size entry (2.13.2):
- a) `blob_max`, kept (built);
- b) a new name, such as `window_bytes` or `db_max`.

10.4.12 What a window counts (2.13.3):
- a) blob bytes only; lines bounded by `line_max` (built);
- b) line and blob bytes, so the largest blob is `blob_max` minus its
  line and a `kv.get` reply can exceed the `kv.put` that stored it.

10.4.13 The value of `blob_max` (2.13.5):
- a) 2147483391, SQLite's documented allocation bound, until the rung of
  2.13.9 measures Chrome (built);
- b) the measured value, whatever it is, once measured;
- c) a value the maintainer names.

10.4.14 "caching to server as an image/restoring admin operations"
(2.13.6):
- a) `db_unload` drops the browser's copy and the server's replicated copy
  is the image; `db_load` restores it (built);
- b) `db_unload` first sends the browser's file to the server as one
  blob, on a new line.

10.4.15 Settings that are not windows (2.13.7):
- a) `line_max`, `overflow_bytes`, `db_soft_bytes`, `files_browser_bytes`,
  `media_db_bytes`, `chunk_bytes` and `srv_buf_size` keep their own
  values (built);
- b) as a), but `chunk_bytes` and `srv_buf_size` become `blob_max`, each
  then allocated or collected whole at that size;
- c) the maintainer names others that become `blob_max`.

Answered by 1.4: a) (2.20).

10.4.16 The worker's export for the UI's `db.snapshot` (2.13.10):
- a) `sqlite3_js_db_export` through the wasm heap, its limit measured
  (built);
- b) the pool's `exportFile`, bounded by V8 and not the heap;
- c) sqlite3.wasm rebuilt with a `MAXIMUM_MEMORY` of 4 GiB.

Answered by 1.4: a) (2.20).

10.4.17 Several `db_load` calls at once (2.13.8, log item 4.6.3.1):
- a) a loud `queue.queue_over` when their images held at once pass
  `blob_max` (built);
- b) `db_load` runs one load at a time, later calls waiting;
- c) a blob streamed to a cache file counts nothing in the queues.

Answered by 1.4: a) (2.20).

10.4.18 The hello's line bound before the settings are known (2.13.7):
- a) 10485760, D24's constant (built);
- b) 1048576, the `line_max` of `settings.json`, as a constant;
- c) the value of `blob_max`, as a constant.

10.4.19 A database grown past `blob_max` in the browser (2.13.11):
- a) nothing refuses it; its image fails loud at a window (built);
- b) `PRAGMA max_page_count` bounds every database at `blob_max`.

10.4.20 The size of the plan's large proofs (2.13.12):
- a) a blob of `blob_max`, one byte more refused; 128 MiB as one message
  (built);
- b) the plan's earlier 16 MiB and 128 MiB, with the edge proved only by
  the decoders' unit tests;
- c) the edge proofs on roots whose settings set a smaller `blob_max`,
  and the shipped value proved by the rung of 2.13.9 alone.

10.4.21 `powershell/en-US/*.psd1` (2.14.2):
- a) leaves the whitelist with the scripts (built);
- b) stays whitelisted and scanned, with the byte order mark handling and
  the PowerShell lexer kept for it.

Affected by 1.6 (2.21.2): the data file returns to the whitelist with the
scripts, with the byte order mark handling and a PowerShell lexer, as b)
describes; a) was built until 1.6.

10.4.22 `python/test_test_posix.py` (2.14.4):
- a) kept with `test_others_refused` for `.py` and `.ts` (built);
- b) deleted whole, with its line in `python/test_all.py`.

Affected by 1.6 (2.21.10): a) stands, and the file gains the PowerShell
tests again, written anew.

10.4.23 The "shell scripts" that keep verbose levels (2.15.2):
- a) the console's dash through `verbose.exec`, and the `.sh` door
  scripts when built (built);
- b) the PowerShell admin scripts, which would gain levels;
- c) another set the maintainer names.

1.4 and 1.5 bear on this reading; their evidence is in 10.4.41.

10.4.24 The settings `verbose_level`, `verbose_ring` and `verbose_forward`
(2.15.3):
- a) `verbose_level` kept for the console alone, `verbose_ring` kept,
  `verbose_forward` removed (built);
- b) `verbose_level` renamed, such as `shell_level`;
- c) `verbose_forward` kept as a flag beside `debug`;
- d) `verbose_level` removed and dash run at a fixed level.

10.4.25 Shell level 1 (2.15.4, log item 4.6.9.1):
- a) the output passed through, start and exit logged (built);
- b) the output captured and formatted as Markdown progress.

10.4.26 The server's trace in debug mode (2.15.5, log item 4.6.9.2):
- a) header JSON only (built);
- b) the whole line in the form of plan 3.11;
- c) no trace.

10.4.27 The runtime with only `debug` (2.15.6):
- a) lines without levels, the queue's trace and the forwarding in debug
  mode, the `verbose_level` tool removed, `script_debug` a traced run
  (built);
- b) as a), with the `verbose_level` tool kept to switch `debug`;
- c) the runtime keeps no verbose lines outside debug mode at all.

10.4.28 The events compaction counts (2.16.2):
- a) every turn appended to the scene, of any role (built);
- b) the player's turns, `ai.say` and `ai.click`;
- c) provider requests.

10.4.29 Where the counter is kept (2.16.3):
- a) the count of the scene's `_turn` rows, counted when read (built);
- b) a counter row per scene in `_meta`;
- c) a KV row per scene.

10.4.30 Where and when compaction runs (2.16.5):
- a) in the browser's substrate, before a `user` turn is appended to a
  scene at the threshold (built);
- b) in `agent.ts`, at the end of each turn.

10.4.31 What compaction keeps (2.16.6):
- a) every turn compacted, the summary a fixed `i18n` text naming them
  (built);
- b) the last assistant reply's text as the summary;
- c) the latest player turn kept whole, the turns before it compacted;
- d) a summary written by the provider (plan 10.14).

10.4.32 The compaction threshold (2.16.7):
- a) the setting `turn_compact_turns`, 64 (built);
- b) the same setting with another default;
- c) a named constant.

10.4.33 The grain of a test suite's label (2.18.2):
- a) a module of `test_all.py`, a rung of the wire and browser tests with
  its stage or root labelled too, `test_posix.py` whole, and the
  TypeScript modules under the rung that runs them (built);
- b) each runner whole;
- c) each root or stage, the roots split so that each holds one label;
- d) as a), with each TypeScript module labelled too (plan 10.24).

10.4.34 The smoke-test suites (2.18.4):
- a) the unit suites of both languages, `test_posix.py`, the wire test
  without its 2 GiB and 128 MiB echoes, and the browser roots "suites"
  (its first two rungs) and "fresh" (built);
- b) the unit suites and `test_posix.py` only;
- c) as a), with more browser roots that the maintainer names once the
  testing phase has measured them.

10.4.35 The 2 minutes (2.18.6):
- a) a smoke-test run fails loud the moment it passes 120 s, with each
  suite's seconds printed (built);
- b) it fails at its end, when its total passed 120 s;
- c) there is no limit; the seconds are printed for the maintainer.

10.4.36 Options and defaults (2.18.7, 2.19.3):
- a) each target takes `--smoke-test` or `--normal-test` and passes it
  on; every runner defaults to `--smoke-test` (built);
- b) as a), but a runner run alone runs every suite;
- c) the targets pass every argument through to `test_all.py`,
  `--failfast` included.

10.4.37 `test_posix.py` rewrites the whitelisted files in every smoke-test
run (2.18.5):
- a) as built;
- b) it checks the formatting and rewrites nothing;
- c) it becomes `normal-test`.

10.4.38 `test_powershell.ps1` after a failed step (2.19.5, log 1.23.10):
- a) it stops at the first failed step, runs `xsjs_stop.ps1` as a cleanup
  and exits 1 naming the step (built until 1.24, rejected);
- b) it carries on and tallies the failed steps, as the maintainer wrote
  it, an exception to "first failure only";
- c) it stops at the first failed step with no cleanup (built).

Answered by the maintainer on 2026-10-21 (log 1.24.1), class C: c), "make
test_powershell.ps1 stop on failure".

10.4.39 When `test_powershell.ps1` runs `test_all.py` (2.19.4):
- a) after the status check that follows `xsjs_install.ps1`, before the
  first start (built);
- b) after the whole lifecycle;
- c) before the lint step.

10.4.40 Where `test_all.py` runs from Windows (2.19.4):
- a) in place: `wsl --cd` of the Windows checkout, `/mnt/c/src`, with its
  roots under `build/` there (built);
- b) a copy of the checkout in the Linux file system, run there.

10.4.41 The "shell scripts" of 1.3 (2.15.2, 10.4.23), with the evidence of
1.4 and 1.5. 1.4 asked for a real `.sh` file, and 1.5 named it
`test_posix.sh` and made it one of the project's two official test
targets. The project now holds a `.sh` script of its own beside
`archive.sh` and `clean.sh`, which plan 7.5 puts outside the project, so
the reason 2.15.2 gave for leaving `.sh` files out does not hold for this
one. `test_posix.sh` is built with no verbose level:
- a) unchanged: the console's dash and the `.sh` door scripts;
  `test_posix.sh` has no levels (built);
- b) `test_posix.sh` takes the shell's verbose level, from `verbose_level`
  or an option, and at levels 1 and 2 writes its start and its exit as
  `verbose.exec` does;
- c) every `.sh` file of the project: `test_posix.sh`, `archive.sh` and
  `clean.sh`.

10.4.42 Tests of the two targets (2.18.8):
- a) none; the testing phase proves them by running them (built);
- b) a Python test that runs `test_posix.sh` with bash on a copy beside
  stub runners, with the maintainer's approval for Python running bash;
- c) a shell test script.

10.4.43 The project rules file that 1.5 names (section 1):
- a) its name elided from the copy of 1.5, the log holding the literal
  text (built);
- b) the copy verbatim, the name included;
- c) 1.5 left out of section 1, with a pointer to the log.

10.4.44 Where the UTF-8 byte order mark is allowed (2.21.3):
- a) at the start of a file of a `.ps1` or `.psd1` row only, by the row's
  codec `utf-8-sig`; anywhere else, and in every other file, U+FEFF is
  refused (built);
- b) U+FEFF added to `_NON_ASCII_ALLOWED`, allowed anywhere in every
  whitelisted file, as the words read; `test_others_refused` then reverses;
- c) at the start of any whitelisted file, every file read as
  `utf-8-sig`;
- d) as a), and required at the start of every PowerShell file, as the
  PowerShell rule asks (6.4); `xsjs_status.ps1`, `xsjs_stop.ps1` and
  `test_lint.ps1` then fail until they gain one.

10.4.45 The banner characters of `xsjs_install.ps1` (2.21.4, log item
4.6.6):
- a) nothing more is allowed; `test_posix.py` stops at
  `xsjs_install.ps1:41:19` until this is answered (built);
- b) U+2588, U+2591, U+2592 and U+2593 join `_NON_ASCII_ALLOWED`, for
  every file;
- c) the four are allowed in the PowerShell rows only, by a sixth key of
  the table;
- d) the maintainer redraws the banner in ASCII;
- e) the script builds the banner from `[char]0x2588` and the others at run
  time.

10.4.46 Where the table lives (2.21.5):
- a) `python/reformat_table.json`, read by `reformat.table_read`, which
  `test_posix.py` calls (built);
- b) a constant in `reformat.py`, its rows plain tuples;
- c) a shared module, `python/file_types.py`, imported by both scripts.

10.4.47 How `test_lint.ps1` chooses the PowerShell files (2.21.7):
- a) the whitelisted files whose extension is in its own list, `.ps1` and
  `.psd1`, kept equal to the table's `windows` rows by hand (built);
- b) it reads `python/reformat_table.json` too and takes the extensions of
  its `windows` rows, failing loud on a whitelisted file of no row as
  Linux does;
- c) every whitelisted file whose extension is not of a `linux` row, which
  also needs the table.

10.4.48 The whitelist's matching rule (2.21.8):
- a) one rule, enforced by both scripts: wildcards in the last part only,
  no brackets or backticks, case sensitive names, Python's rule for names
  starting with `.`, a match that is not a file refused (built);
- b) `reformat.py` keeps `glob.glob`; `test_lint.ps1` alone refuses the
  lines it cannot match the same way;
- c) the whitelist names files only, without wildcards.

10.4.49 First failure in `test_lint.ps1` (2.21.9):
- a) the CRLF check and PSScriptAnalyzer stop at the first file with a
  fault (built);
- b) every file's CRLF faults and every file's analyzer results printed
  before the exit, as before 1.6.

10.4.50 Abbreviated options (2.22.2, log 3.54.3, T2a-B1):
- a) the full names only: `test_all.py` and the parser of the tests refuse
  `--normal` and `--fail` (built);
- b) abbreviations kept, and the test's input changed to one that is no
  prefix;
- c) `options_add` turns abbreviations off for all three runners.

Answered by the maintainer on 2026-10-21 (log 1.25.1), class C: a), "i want
"--normal-test" that worked great."

10.4.51 The driver listing its own test module (2.22.5, log 3.54.4,
T2a-B2):
- a) `test_all.py`'s table lists `test_test_all` (built until 1.7);
- b) that module run outside the table;
- c) no test of `test_all.py` (built).

Answered by the maintainer on 2026-10-21 (log 1.25.4), class C: c), "just
test the stuff that is infrastructre for testing, not the test driver";
the table lists `test_test`, and `alarm_plan` moved into the infrastructure
so that its tests stay.

10.4.52 Where `alarm_plan` lives (2.22.3):
- a) `python/category.py`, beside the 120 s and `limit_seconds` (built);
- b) a new module of the infrastructure, such as `python/deadline.py`, with
  its stub;
- c) as a), with `timer_start` and `timer_stop` moved into `category.py`
  too.

10.4.53 The test modules of the infrastructure for testing (2.22.1,
2.22.4):
- a) `python/test_test.py` holds every test of `category.py`, and
  `python/test_category.py` is joined into it (built);
- b) `python/test_category.py` kept, and `python/test_test.py` holding
  `TestAlarm` alone;
- c) as a), with the tests of `tap_producer` and `tap_consumer` joined too,
  `test_test` then run first.
