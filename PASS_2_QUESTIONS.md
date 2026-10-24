# Second pass questions

These are the problems the first rework (`FIRST_REWORK.md`, items 1.1 to
1.41) unearthed and left unresolved, as 32 multiple choice questions numbered
2.1 to 2.32. They are grouped by class and ranked by importance within each
class.

- Class A: "this just needs to be done without your input, i'm happy to
  assume choice A". Choice A is applied, marked `--` as the selected options
  are in `FIRST_REWORK.md`.
- Class B: "this would cause a lot of rework and input is required to be
  sure." Nothing is applied.
- Class C: "this doesn't have long term consequences or input seems unlikely
  to change the outcome." Nothing is applied.

Importance runs from 1 (low) to 5 (high): how much breaks, or how much gets
built on the wrong thing, if the question stays open or is answered wrong.
Nothing was run, built, tested or formatted in this pass, so every applied
change is unverified until the testing phase.

## Summary

The first rework's 22 agents left their unresolved work in the records under
the gitignored `tmp/handoff_23_0919/`: deferred designs, class B decisions,
requests between packages, findings outside the items and points owed to
testing. Seven agents read those records and the first rework's postmortem,
checked each problem against the code as it stands, dropped the ones already
resolved and made the class A changes. The 32 questions were chosen from
their drafts. `TAP_PLAN.md`, whose section 12.2 listed 107 class B points, is
deleted from the working tree and was not read back from git (2.12).

What the first rework left unresolved, by kind:

- Deferred designs whose only record was gitignored or deleted:
  - the MCP server continuing after a tool's exception, lost with the plan
    (2.12);
  - the program's assembly on the AI thread, `provider.set` and the resync,
    which survive only in fragments (2.16);
  - the dispatch order (2.19);
  - the contract of `restore_lines` (2.21);
  - the designs that would close 1.23 (2.28);
  - `certificate_key` (2.32).

  Each design that survives is now written in full in its question.
- Failure policies that no rule settles:
  - a push the server's store refuses (2.13);
  - a push over `line_max` after its commit (2.14);
  - a fault before the worker can report (2.17);
  - the dispatcher's order (2.19);
  - the MCP server's invalid messages (2.24);
  - non-finite numbers from scripts (2.25).
- What removing the program under 1.20 left behind: 2.16, 2.18, 2.20, 2.21,
  2.27.
- Items left partial: 1.23 (2.28) and 1.34 (2.23).
- Rules and selected options that pull apart: 2.15, 2.22, 2.26, 2.29, 2.31.
- Code, tests, stubs, the line catalogue and docs out of step with each
  other, fixed as class A: 2.1 to 2.11.

Found but not made questions, for the record:

- The two JSLB decoders report different faults in two cases, though both
  refuse both inputs:
  - a digit key of more than 4300 digits: Python reports
    `jslb.line_not_json`, while TypeScript reports `jslb.blob_gap` or keeps
    the key as a string;
  - a bad number before a syntax fault.
- TypeScript `dispatch.error_make` has no caller outside its tests.
  TypeScript `dispatch.id_next` (1.9) has no caller at all:
  `TaskQueue.task_submit` numbers its requests from 1 with its own counter.
  Nothing collides, since each side matches replies only to its own
  requests.
- `mcp_stdio.stdio_run` types `register` as `Callable[[Any], None]`, where
  its stub has `Callable[[mcp.Server], None]`, because `mcp` is imported
  only after `sys.pycache_prefix` is set.
- `API/sql/*.sql` are missed by `python/reformat_whitelist.txt`, and
  `python/reformat_table.json` has no `.sql` row, so no check reads them.
- `substrate._hashes_named` opens every unopened `<root>/*.sqlite`
  read-write, `_verbose.sqlite` included, though `API/sql/verbose.sql` says
  the store never opens it. It writes nothing there.
- `Store.db_open` sets WAL mode before `schema_apply` checks the tables, so
  a file it refuses is left in WAL mode.
- Since the move to the gold record, no Python test restores a database
  larger than the old 10 MiB window.
- `python/seed/prompt.json` says `engine.store` "has the same operations as
  the database tools", but it has four more.
- `agent.prompt_build` finds a prompt by running `sql_run` on the store's
  own `_head` table.
- Several headers state shipped values that go stale when a setting
  changes: those of `xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1` and
  `powershell/test_powershell.ps1`, and `README.md`. `xsjs_start.ps1`'s
  header still says it serves the engine.
- `API/ts/worker_ai.d.ts` says `settings_register` relays the UI's
  `settings.put`, but `tap_start` also notifies the worker's own.
- The PowerShell scripts write their `.md` logs beside themselves, kept out
  of git by `.gitignore`, while a rule says to point tools at `build/`.
- `gold_value` in `ts/test_wire_rungs.ts` hands out the frozen gold without
  copying it. Nothing writes to it, and a write would throw, so nothing was
  changed.
- The first postmortem said `ts/test_all.ts`'s header is stale. That was
  wrong: `tap_start` does notify itself `worker.tests` in debug mode.

Owed to the testing phase, not questions:

- the trigger message texts of sqlite3.wasm and of Python's `sqlite3`;
- a 2 GiB echo, and a `kv.put` near `blob_max`, in the worker and OPFS;
- what dash writes after `exit`, ttyd's close code, and whether ttyd 1.7.7
  takes a first message without a size;
- `/proc/<pid>/task/<pid>/children` on the WSL kernel;
- `wsl --list`'s exit codes, and PowerShell 5.1's private scope;
- sqlite3's glue under the worker's `"use strict"`;
- the `faults` root, which runs both TAP streams nine times, and the timing
  of `rung_worker_hang`;
- the test page growing about 1.9 MB with `test_digests.json`, and the
  182478 byte gold riding in every debug root's first line.

Problems in how the first rework itself ran, which cannot be resolved now:

- Its agents broke the hard limits six times by starting `python3` with no
  input or with `--version`, and three times by reading files with
  `git show HEAD:`.
- Two agents deleted unused `i18n` keys before the coordinator's sweep.
- None of these breaches ran or wrote anything of the project.

No agent of this pass reported a breach.

Files changed in this pass, unstaged:

- Stubs and docs: `API/README.md`, `API/python/engine_verbose.pyi`,
  `API/python/mcp.pyi`, `API/python/settings.pyi`, `API/sql/metaverse.sql`,
  `API/ts/error_overlay.d.ts`, `API/ts/http.d.ts`, `API/ts/i18n.d.ts`,
  `API/ts/lines.d.ts`, `API/ts/media.d.ts`, `API/ts/page.d.ts`,
  `API/ts/settings.d.ts`, `API/ts/substrate.d.ts`, `API/ts/verbose.d.ts`,
  `API/ts/wire.d.ts`, `README.md`.
- Strings and gold: `i18n/en-US.json`, `test_settings.json`.
- Python: `python/dispatch.py`, `python/main_loop.py`, `python/reformat.py`,
  `python/reformat_table.json`, `python/substrate.py`,
  `python/test_dispatch.py`, `python/test_engine_kv.py`,
  `python/test_engine_system.py`, `python/test_main_loop.py`,
  `python/test_posix.py`, `python/test_reformat.py`,
  `python/test_substrate.py`.
- TypeScript: `ts/dispatch.ts`, `ts/jslb.ts`, `ts/test_dispatch.ts`,
  `ts/test_wire_rungs.ts`.
- PowerShell: `xsjs_install.ps1`.

## Class A: done, choice A assumed

### 2.1 `test_settings_written` compares bytes the writer cannot produce

Class A. Importance 3: a smoke run ends at its first failure. It would stop
at `python/test_engine_system.py`, the 21st of 30 modules, before the wire
and browser tests.

`test_settings_written` had `settings.put` write `harness.settings_copy()`
into a scratch root, then compared the bytes with the checkout's
`settings.json`. They cannot match:

- `engine_system._settings_write` writes
  `json.dumps(value, ensure_ascii=False, indent=2) + "\n"`, with one list
  item per line.
- The checkout holds `powershell.root_files` on one line.
- No formatter owns `settings.json`.

Why the maintainer: only to confirm. The other fixes tie a hand-edited file
to the layout of `json.dumps`, which no rule asks for.

-- A. Compare the parsed file and its top-level key order with
`harness.settings_copy()`, as `test_settings_replaced` beside it does. The
unused `_SETTINGS_PATH` goes. Applied in `python/test_engine_system.py`.

B. Rewrite `settings.json` in `json.dumps(indent=2)` form and keep the byte
compare.

C. Compare the bytes with
`json.dumps(harness.settings_copy(), ensure_ascii=False, indent=2) + "\n"`,
which repeats the writer's code.

### 2.2 Two comments below a header hold a `;`, which the comment check refuses

Class A. Importance 3: `comments_check` in `python/test_posix.py` stops at
the first one, so every lint run, smoke included, would fail there.

Below a file's header, the check allows only letters, digits, white space
and `.,"'?:!()/` outside code spans. Two comments broke it:

- `Store._row_write` in `python/substrate.py`: "Writes a row, its cache file
  first; a row of the same digest stays."
- `TestPut.test_value_stored` in `python/test_engine_kv.py`: "The image goes
  to the store under the header's key; nothing answers."

Both files are whitelisted. The first rework scanned only the stubs.

Why the maintainer: only to confirm. The files break the check as it
stands.

-- A. Each `;` becomes a full stop. Applied in both files.

B. Leave them for the testing phase to find.

### 2.3 The TypeScript number scan may overflow V8's backtrack stack on a long string

Class A. Importance 3: a JSON text holding a string of several MiB could be
refused with a `RangeError` that names no real fault. Examples are a
provider's reply carrying a base64 image, or a large first line.

`numbers_check` in `ts/jslb.ts` skips each JSON string with
`(?:[^"\\]|\\.)*`. That alternation repeats once per character, and V8 keeps
one backtrack entry for each repeat. The unrolled form
`"[^"\\]*(?:\\.[^"\\]*)*"` matches exactly the same strings and keeps an
entry only per escape. The first rework deferred this to a measurement.

Why the maintainer: only to confirm. The two patterns match the same tokens,
so no measurement can make the new one wrong.

-- A. `constants.number_token` becomes
`/"[^"\\]*(?:\\.[^"\\]*)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g`, and nothing
else changes. Applied in `ts/jslb.ts`.

B. Keep the old pattern until a test with a long string has run.

### 2.4 The stubs leave out names their modules export

Class A. Importance 3: the stubs under `API/` are the API the maintainer
reviews. Only `API/ts/lines.d.ts` is compiled, so nothing else catches a
stub that is out of step with its code.

The gaps were found in eleven stubs:

- `API/ts/page.d.ts`: `HandlerRegister`, `ImageSource`, `ConsoleControl`,
  `OverlayControl`, `PageParts`, `owners_make`, `settings_take`,
  `fault_read`, `handlers_register`.
- `API/ts/wire.d.ts`: `FrameQueue` and `ConsoleReader`, plus the members
  `WirePort.first_receive`, `message_take` and `close_take` and
  `ConsolePort.message_take` and `close_take`.
- `API/ts/error_overlay.d.ts`: `FaultScreen`.
- `API/ts/settings.d.ts`: `Sender`, `ValueStore`.
- `API/ts/media.d.ts`: `ImageCache`, `MediaExchange`.
- `API/ts/http.d.ts`: `FetchArguments`, `HttpAnswer`, `HttpExchange`. Its
  header also named a reply type `http.response`, which does not exist: the
  reply is of type `http.request`, with payload `lines.HttpResponse`.
- `API/ts/verbose.d.ts`: `LineRing`.
- `API/ts/i18n.d.ts`: `i18n_format`.
- `API/ts/substrate.d.ts`: `SlotHandle`, `ExecOptions`, `SqliteStatement`,
  `SqliteDatabase`, `SqliteModule` and `SqlitePool`, which `ts/boot.ts`
  uses. `CacheFiles`, `slot_add` and the `Store` constructor were typed
  `unknown`.
- `API/python/settings.pyi`: its list of types left out the nested object
  that a table checks.
- `API/python/engine_verbose.pyi`: said `verbose.tail` answers only from the
  server's ring; it also answers for the threads `ui` and `ai`.
- `API/python/mcp.pyi`: `RpcError` lacked its constructor
  `(code, message, data=None)`.

Most of these names are reached only by their module's own suite, which is
how 1.34 leaves each module to be tested.

Why the maintainer: whether a name that only its own suite reaches belongs
in the stub decides what every later stub holds. 1.32 accepted built
additions of this kind to the `queue`, `unittest` and `tap_producer` stubs.

-- A. Each stub declares every name its module exports, as the code
declares it, with a one line comment each, and the wrong sentences are
corrected. Applied in all eleven stubs; no code changed.

B. A stub declares only what other modules use, and `API/README.md` gains "A
name only the module's own suite reaches is exported but not declared." Only
the wrong sentences are fixed.

C. Nothing is exported for its own suite alone: those names become private,
and the suites test through the declared surface.

### 2.5 A pushed line's failure drops the tool's exception

Class A. Importance 2: the run's first failure would be missing from the
server's `error` line and log, though the server still stops.

When the handler of a line with no `i` returns a `Failure`,
`dispatch.line_dispatch` raised `dispatch.notification_replied` without the
`Failure`'s own error, in both languages. `engine_mcp.mcp_message` returns a
`Failure` whenever a tool in a JSON-RPC request threw, even when the `mcp`
line itself carried no `i`. So the tool's exception was never written.

Why the maintainer: only to confirm. The rules settle it: never swallow an
error, and describe a cascade as nested `cause` entries with the first
failure innermost.

-- A. `notification_replied` is raised with the `Failure`'s error as its
cause: `raise ... from` in Python, `utility.cause_append` in TypeScript.
Applied in `python/dispatch.py` and `ts/dispatch.ts`. Their tests
`test_failure_notification` and `test_notification_failure` now check the
cause.

B. The server writes such a failure as its own `error` line, and raises
`notification_replied` only for a plain reply.

### 2.6 The `universe` update trigger refuses a rename that keeps its world

Class A. Importance 2: a legal write is refused loudly as
`agent.content_ambiguous`. Nothing is corrupted.

`universe_world_update` fires `BEFORE UPDATE OF world`. It refused when
another row names the new world, excluding the updated row by `NEW.name`.
In a BEFORE trigger the table still holds the old row. So with row `a`
holding world `w`, `UPDATE universe SET name = 'd', world = 'w' WHERE name =
'a'` found row `a` itself and was refused. The insert trigger is right to
use `NEW.name`.

Why the maintainer: only to confirm. 1.12's selected option refuses only
ambiguous content.

-- A. The update trigger excludes the row by `OLD.name`, in
`API/sql/metaverse.sql` and in its copy `_METAVERSE_DDL` in
`python/main_loop.py`. `test_world_ambiguous` in `python/test_main_loop.py`
also renames `a` to `d`, keeping `w`, and expects it to pass. Applied.

B. Leave it: a script writes the rename and the world in two statements.

### 2.7 The line catalogue is out of step with the code

Class A. Importance 2: `API/ts/lines.d.ts` is the wire API later sessions
build from. The dispatch design of 2.19, built from the old table, would
refuse every MCP request.

- The table called `mcp` a push on the `wire` and `mcp` lanes. In the code,
  an `mcp` line is a request when its JSON-RPC message is a request:
  `queue.task_submit` gives it an `i`, `ts/mcp.ts` reads the answer by `r`,
  and `engine_mcp.mcp_message` answers through `dispatch.reply_make`. Only a
  JSON-RPC notification rides as a push.
- The table listed `settings.put` on `wire` only, though the UI thread
  notifies it to the worker and the worker's `tap_start` notifies it to
  itself. It also lacked the worker's wakes `worker.console_opened` and
  `worker.settings_put`.

Why the maintainer: only to confirm. The other choices change code in both
languages, or the table's scope, to fit a table.

-- A. The catalogue follows the code. Both `mcp` rows read "request or
push", and a header sentence says when each applies. Four rows are added:
`settings.put` on `ui-ai` and on `ai`, and `worker.console_opened` and
`worker.settings_put` as wakes. Applied in `API/ts/lines.d.ts`.

B. The code follows the catalogue: every `mcp` line becomes a push, its
JSON-RPC response a push of its own matched by the JSON-RPC id. This changes
`ts/mcp.ts`, its use of `ts/queue.ts`, `python/engine_mcp.py` and their
tests.

C. As A for `mcp`, but the table lists only lines that cross a thread, so
the `ai` row and the two wakes are not added.

### 2.8 The `first` wire rung compared the gold with itself

Class A. Importance 2: a check that cannot fail reports a pass that measured
nothing.

`#first_run` in `ts/test_wire_rungs.ts` compared the gold in `tap.start`'s
`test_settings` with `harness.gold_get(...)`. The harness is filled from
that same line, so the two texts are always equal. The rung's other checks
do measure the line: full names, type `tap.start`, `i` 101, no `r`, no
blobs, and payload keys exactly `settings` and `test_settings`.

Why the maintainer: the handoff asked for the comparison. A real comparison
needs the Python driver to take part.

-- A. The comparison goes, and the other checks stay. Applied in
`ts/test_wire_rungs.ts`.

B. Make it real: the rung writes the SHA-256 of the gold's JSON text as its
diagnostic, and `python/test_wire.py` compares it with the digest of the
text it wrote. This holds only while both languages write that JSON byte for
byte alike.

C. Keep it.

### 2.9 Two store behaviours lost their tests in the move to the gold record

Class A. Importance 2: a store that numbered turns across scenes, or
versions across ids, would pass every test.

The Python test migration to `test_settings.json` (1.34) removed two tests,
saying `python/test_substrate.py` covers them:

- `test_scenes_apart`: turns are numbered within each scene.
- `test_ids_apart`: versions are counted within each id.

It did not cover them. `test_turns_append` appends to one scene only, and
`test_document_heads` puts only one id, twice.

Why the maintainer: only to confirm. The record says the coverage moved, and
it did not.

-- A. Applied in `python/test_substrate.py`:

- `test_turns_append` appends one turn to `/metaverse/elsewhere/1` and gets
  `n` 1 there, with the first scene unchanged.
- `test_document_heads` puts `scene/moat` between the two `scene/arrival`
  puts and gets version 1 for it. The arrival's second put still gets
  version 2.

B. Leave the coverage to the testing phase.

### 2.10 `wsl --install -d` never reads its exit code

Class A. Importance 2: a failed install of the distribution was reported as
"not ready, restart Windows", with its exit code lost.

`_xsjs_install_step_check_linux` in `xsjs_install.ps1` runs
`wsl --install -d <distribution>` directly, because the install is
interactive, and never read `$LASTEXITCODE`. The `wsl -e true` that follows
caught a failure only as `distribution_not_ready`.

Why the maintainer: only to confirm. 1.11's selected option for the two
`wsl --list` calls, "Any nonzero exit is a hard error now, revisited if a
normal state turns out to exit nonzero", decides the same case here.

-- A. Right after the install, a nonzero `$LASTEXITCODE` throws `exit_code`
with the command and the code, as `xsjs_util_get_wsl` does. No new string.
Applied in `xsjs_install.ps1`.

B. As A, with a new string `distribution_install_failed`, "Installing {0}
failed (exit code {1}).".

C. Leave it.

### 2.11 Texts that misstate the project

Class A. Importance 1: readers are misled, but nothing runs differently.

- `README.md` said the install puts ttyd in Linux with apt.
  `xsjs_install.ps1` actually builds it from the pinned source release and
  its patches.
- `API/README.md`'s table "Lanes, as `lines.d.ts` names them" listed five of
  the eight lanes, leaving out `dom`, `ui` and `ai`.
- The `.md` row of `python/reformat_table.json` (`mdformat --check`, lexer
  `none`) has matched no file since 1.40 removed both `.md` lines from the
  whitelist. It was kept only because it existed. Its traces are
  `case "none"` in `python/test_posix.py`, `".md"` in
  `python/test_reformat.py`, and a sentence in `python/reformat.py`'s
  header.
- `engine_doc.not_registered` and `engine_turn.not_registered` said
  "handlers" for modules that register one handler each.

Why the maintainer: only to confirm. The rule against unrequested
documentation does not cover text that exists and is wrong, and the rules
forbid keeping code because it exists.

-- A. All corrected and applied:

- `README.md` gets "Ensures Python 3 and OpenSSL are installed in Linux with
  apt." and "Builds ttyd in Linux from its pinned source release and
  patches, after checking for the tools and headers the build needs."
- `API/README.md` gains rows for `dom`, `ui` and `ai`.
- The `.md` row and its three traces go.
- The two texts read "The doc handler was called before it was registered."
  and "The turn handler was called before it was registered.", in
  `i18n/en-US.json` and in the gold.

B. As A, but the lane table of `API/README.md` goes, `lines.d.ts` being the
catalogue.

C. Leave them all.

## Class B: input required

### 2.12 `TAP_PLAN.md` is deleted, and six files and several deferred designs still depend on it

Class B. Importance 5: the API and the test order were written from that
plan, and which document governs now decides every later change under
`API/`.

The maintainer deleted `TAP_PLAN.md` from the working tree, unstaged. It was
not read back from git.

Six tracked files still cite it:

- `API/README.md`, three times: "The external API of every module
  TAP_PLAN.md names", "A file changes only when TAP_PLAN.md changes with
  it", and one more.
- `API/python/mcp.pyi` and `python/mcp.py`: section 5.4.
- `python/test_all.py`, twice: section 3.3, the run order.
- `python/test_wire.py`: section 4.3, the schema of the wire rungs' gold.
- `ts/provider.ts`: section 1.3, where `provider.set` is deferred.

`python/test_browser.py` also says "the plan" four times and labels its
rungs "stage 0" to "stage 8".

What became of the designs the plan held:

- The MCP server continuing after a tool's exception (5.4, deferred by 1.8)
  is recorded nowhere else.
- The program's assembly on the AI thread, `provider.set` and the resync
  (1.3 and 1.4) survive only in fragments (2.16).
- The dispatch order (12.2 point 47) survives in full in
  `tmp/handoff_23_0919/2.3.3_progress.md` and in 2.19 here.
- The run order and the gold schema survive only as code: `_MODULES` in
  `python/test_all.py` and `gold_make` in `python/test_wire.py`.

The plan's section 12.2 listed the first rework's 107 class B points. This
test was drawn instead from the records under the gitignored
`tmp/handoff_23_0919/`, which are now the only record of the other deferred
designs.

Why the maintainer: the deletion is the maintainer's act, and its intent is
not recorded. The rules ask that a deferred design be written in full beside
its deferral, and that nothing concrete exist ahead of the prose that
describes it. Both now point at a file that only git holds.

A. Keep it deleted. Once this test is answered, a new plan is written from
the answers, the code and the records, including the designs carried by this
test, and the citations are repointed to it in the same change. Until then
they stay. The design of 5.4 is redone when 1.8's "enabled later" comes.

B. Restore it as committed, with `git checkout -- TAP_PLAN.md` (the
maintainer's command), and answer its 12.2 points beside this test.

C. Keep it deleted and remove the citations now. Each design a citation
stands for is written into the header of its module's stub, and
`API/README.md`'s rule reads "A file changes only by the maintainer's
request."

D. Keep it deleted and only remove the citations. The designs stay in git
history and `tmp/`.

### 2.13 A push the server's store cannot apply ends the server

Class B. Importance 4: it decides what a lost line does to every later
connection. The push handlers, the main loop's failure path and the
browser's reconnect are all built on it.

Each push handler (`kv.put`, `kv.delete`, `doc.put`, `db.create`,
`db.drop`, `turn.append`, `sql.run`) applies the browser's commit through
`substrate.Store`. Any raise ends the server with one `error` line and exit
1. 1.7 says the server "may not have received everything in an orderly
manner due to a connection loss", and a push that depends on a lost line
raises:

- a push into a database whose `db.create` was lost: `substrate.db_closed`;
- a `db.create` whose `db.drop` was lost: `FileExistsError`;
- an `sql.run` on a table whose `CREATE` was lost: `no such table`.

The browser keeps its databases and sends the same kind of push on the next
connection, so that server ends too. This repeats until the deferred resync
of 1.17, where a reopened window gets the server's databases back, brings
the two stores together.

Why the maintainer: 1.7 calls the sync lossy, while the rules forbid
swallowing an error or giving a default. Nothing says what the server does
with a push its store refuses.

A. As built: a refused push is a hard error, logged, and the server ends.
The resync of 1.17, when built, runs at the start of each connection, before
the server reads any push.

B. A refused push counts as one more lost line, for push types only:
`main_loop._line_serve` logs the failure and its cascade with `verbose.log`
and reads on. The rules gain that exception on the maintainer's word.

C. The server answers a refused push with an `error` line carrying the
cascade and keeps serving, and the browser's AI repairs the damage over the
MCP. This needs a new row in `API/ts/lines.d.ts`.

D. The handlers apply what they can: `db.create` of an existing database
opens it, and a push into a missing database creates it first. Every other
refusal stays a hard error.

### 2.14 A push longer than `line_max` fails after the browser has committed

Class B. Importance 4: a legal store operation fails after its commit and
loses the pushes after it. The commit lines are built on payloads that
cannot carry the data.

The browser's store puts the data in the payload for three pushes, so the
line grows with the data:

- `doc.put`: `{db, id, body}`;
- `turn.append`: `{scene, role, content}`;
- `sql.run`: `{db, statements}`.

Only `kv.put` carries its bytes as blob 1, bounded by `blob_max`.
`transaction_run` hands the pending pushes to `line_notify` after the
commit. `FrameQueue.line_add` in `ts/wire.ts` then refuses a line over
`line_max` (1048576 bytes) as `wire.line_over`, and the server's decoder
would refuse it too.

So an operation like either of these throws to its caller though the
browser committed it, and the later pushes of its transaction are never
sent:

- a document over 1 MiB of canonical JSON;
- one `sql_run` with many statements or a large parameter.

Why the maintainer: whether `line_max` bounds a store operation is a reading
of 1.16's "The max message size is based on the max DB size", which no
record settles. The fix changes either the wire catalogue and the server's
handlers, or adds a refusal to the store.

A. Each push carries its data as blob 1, as `kv.put` does:

- `doc.put` carries the canonical text, with payload `{db, id}`;
- `turn.append` carries the content's canonical text, with `{scene, role}`;
- `sql.run` carries the JSON text of `statements`, with `{db}`.

The server's handlers read blob 1, bounded by `blob_max`. The files are
`ts/substrate.ts`, `python/engine_doc.py`, `python/engine_turn.py`,
`python/engine_sql.py` and `API/ts/lines.d.ts`.

B. Before its transaction starts, the store refuses an operation whose push
line would pass `line_max`, as a new `substrate.push_over`. Nothing commits
that cannot be sent.

C. As built.

### 2.15 The AI's scripts get 15 of the store's methods

Class B. Importance 4: every script the AI writes is built on this surface.

`script.script_run` gives a script `engine.store`, a frozen object holding
15 methods of `substrate.Store`: `sql_run`, `db_list`, `db_create`,
`db_drop`, the `kv_*` and `doc_*` methods, `turn_append`, `turn_list`,
`turn_compact` and `transaction_run`.

Seven are withheld: `db_open`, `db_close`, `kv_check`, `db_snapshot`,
`db_restore`, `sink` and `handlers_register`. `ts/test_script.ts` checks
that `engine.store.db_snapshot` is absent.

Every row stays readable and writable, since `sql_run` refuses no statement:
DDL, `VACUUM` and `PRAGMA` all pass. But no script and no MCP tool can take
or restore a whole database as a blob.

Why the maintainer: the rule "Nothing refuses the AI API access to the
databases unless the maintainer requires it" and 1.28's "Exposing the
existence of the DB beyond routine SQL queries is an API violation" pull
apart here. Only the maintainer can say whether 1.28 is that requirement.

A. Keep the 15. 1.28 is the requirement the rule allows for, and what is
withheld is the store's machinery and the SQLite image, which 1.7 keeps out
of the protocol.

B. Scripts get the whole `substrate.Store` again. `ScriptStore`,
`store_methods` and `store_routine` go from `ts/script.ts` and
`API/ts/script.d.ts`, the two tests of the restriction go, and the
`engine.store` sentence of `python/seed/prompt.json` is rewritten.

C. The 15 plus `db_snapshot` and `db_restore`, so whole databases move as
opaque blobs, as 1.7 allows. The other five stay withheld.

### 2.16 The deferred program on the AI thread has lost its plan

Class B. Importance 4: the program's pieces are built and tested but wired
nowhere. The parts of its design that decide the resync, or that could leak
the provider key, are recorded nowhere.

Under 1.20 the bring-up runs only the test suites, so the AI thread's
program is not assembled. Its pieces are:

- the console port and the provider port;
- the store on the boot's pool and cache, with its handlers;
- the MCP server, with `tools_browser.tools_register`;
- the two MCP clients and the agent;
- the `WireTap` note.

So these run nowhere: `console_register`, `note_make`, `tools_register`, the
owner table's routes for `kv.`, `doc.`, `db.`, `turn.`, `sql.`, `ai.`,
`tools.` and `console.`, and the store's `db.restore` and `db.file`
handlers.

The fullest record is `tmp/handoff_23_0919/1.46.4.md` section 3 point 2. No
record says:

- what `provider.set` is: its lane, payload and reply, and when it is sent;
- how the key stays off tty 1's overlay, which `WireTap` feeds in debug
  mode (the leak that started 1.20);
- what starts a resync, which databases it covers, and in what order.

Why the maintainer: the rule that a deferred design is written in full
beside its deferral pulls against the deletion of the plan that held it. The
key's path is a design that a wrong guess could turn back into 1.20's leak.

A. Record the assembly as the records give it, in the header of
`API/ts/worker_ai.d.ts`, naming the key's line and the start of a resync as
not yet designed. No code changes.

B. As A, and design the key's part now. `provider.set` is a SERVER -> AI
push with payload `lines.ProviderInfo` and the key as blob 1.
`jslb.line_render` shows a blob only as a tag, so neither `WireTap`'s note
nor the overlay shows the key, and `provider.key_set` keeps it.

C. Leave the design in the gitignored records only, and design the assembly
afresh with the program's first suite, by 1.20's "one test suite at a time".

### 2.17 A fault before `worker_ai.tap_start` never reaches the server

Class B. Importance 3: the diagnostics that 1.23 calls the top priority are
lost in a plausible failure, such as an OPFS handle that another Chrome page
still holds.

When `tap.start` arrives, the worker first awaits three steps: sqlite3.wasm's
init, the OPFS pool (`installOpfsSAHPoolVfs`), and the test cache's
`createSyncAccessHandle` calls. Only then does `worker_ai.tap_start` set the
settings and register the report function.

A rejection in that chain, or a throw in `tap_start` before its
`error_overlay.report_register`, finds no report function:

- `error_overlay` posts the `fault` line to the page only.
- No `error` line goes to the server.
- The server waits for its reply until its own timer ends the run, with no
  message.

The wire could not carry an `error` line then anyway, since
`WirePort.parts_live` reads the settings that `tap_start` sets.

Why the maintainer: the fix reorders a bring-up that two packages' stubs
describe. The smaller fix changes when `tap.start` is answered, which the
Python drivers see.

A. `ts/boot.ts` reads `tap.start`'s settings, calls `settings.settings_set`
and registers the report function as soon as the first line arrives.
`worker_ai.tap_start` does neither any more. This changes `ts/worker_ai.ts`,
`API/ts/worker_ai.d.ts` and `API/ts/boot.d.ts`. The reply still means ready,
and a fault during the platform's start reaches the bootstrap waiting for
that reply, which fails with `bootstrap.reply_unexpected`.

B. Only `boot` changes: `tap_start` runs at `tap.start` and answers it
before the test platform exists, and the platform opens inside the
`worker.tests` task. A server line with a blob over `overflow_bytes`,
arriving before the cache has its slots, would then fail.

C. As built: such a fault shows on the page only, and the Python driver's
timer ends the run.

### 2.18 The provider key and file still reach every root, unread

Class B. Importance 3: an AI provider's secret rides into a process that
never reads it.

By the first rework's reading of 1.20, the bring-up sends no provider key or
information, and `python/bootstrap.py` reads neither. Yet:

- `xsjs_start.ps1` still adds `provider.variable` (`XSJS_PROVIDER_KEY`) to
  `WSLENV`, so the key reaches the environment of ttyd and the server.
- `powershell.root_files` copies `provider.json` into every root.
- `main_loop._provider_seed` seeds `python/seed/provider_script.json`.
- `python/settings.py` checks a `provider` object that no product code
  reads.

Outside their own tests, nothing reads the seeded script, `provider.json` or
`ts/provider_script.ts`.

Why the maintainer: what the deferred program keeps (2.16) is a design
choice, and the reading of 1.20 that removed the provider from the bring-up
is unconfirmed.

A. Stop only the key and the file. The `WSLENV` forward goes from
`xsjs_start.ps1`, and `provider.json` leaves `powershell.root_files` in
`settings.json`, `API/settings.json` and the samples of
`python/test_settings.py` and `ts/test_settings.ts`. The `provider`
settings, the seed and the TypeScript provider modules stay for the deferred
program.

B. Remove the whole residue: A, plus the `provider` settings object (in both
settings files, `_PROVIDER_TYPES` in `python/settings.py`, and
`ts/settings.ts`), `_provider_seed`, `python/seed/provider_script.json` and
the `XSJS_PROVIDER_KEY` environments of `python/test_bootstrap.py`. The
TypeScript provider modules follow 2.16.

C. Keep all of it until the deferred program returns.

### 2.19 A malformed line runs its handler before the dispatcher refuses it

Class B. Importance 3: while this is open, a malformed push changes the
server's store before the loud failure. Building the fix later changes every
engine's registration in both languages.

`line_dispatch` in `python/dispatch.py` and `ts/dispatch.ts` calls the
handler first, and only then compares the line's `i` with what the handler
returned:

- A push such as `kv.put` that wrongly carries `i` is applied to the store,
  then fails with `dispatch.request_unanswered`, a text that blames the
  handler.
- A request type sent without `i` runs, then fails with
  `notification_replied`.

A registration does not say whether its type's lines carry `i`, so the
dispatcher cannot refuse earlier, and `mcp` lines are both (2.7). The design
in choice A was deferred in the first rework and is otherwise only in
`tmp/handoff_23_0919/2.3.3_progress.md`.

Why the maintainer: no item asks for this order, and the store is a lossy
accelerator whose server exits on the fault anyway. The fix is a new
registration shape across every engine of both languages.

A. Refuse before the call:

- `handler_register(type, version, fn, kind)` in both languages and their
  stubs, where `kind` is `"push"`, `"request"` or `"either"` (for `mcp`),
  taken from the catalogue's reply column.
- Before the handler runs, `line_dispatch` raises `dispatch.push_identified`
  "The push line of type {0} version {1} carries the id {2}." or
  `dispatch.request_unidentified` "The request line of type {0} version {1}
  carries no id."
- `notification_replied` and `request_unanswered` stay, for a handler that
  returns against its kind.
- Every `handlers_register` and `mcp.Server.wake_register` pass the kind.
- TypeScript's wakes keep their own `r` check.

B. As A, but the kinds are one table by type inside each dispatcher, copied
from the catalogue, and `handler_register` keeps its signature.

C. As built. The headers of both dispatch stubs say the form is checked
after the handler runs.

### 2.20 `python/bootstrap.html` and `python/xsjs_screenshot.py` drive a bootstrap that is gone

Class B. Importance 3: two kept files present a retired command loop as
working code, the kind of prior art a later session would build on.

`python/xsjs_screenshot.py` starts ttyd on
`python3 python/bootstrap.py <modules directory>`. It expects a first line
`bootstrap <path> sha256 <hex> pid <n> python <version> modules <path>`, and
types `put update` and `dir` into `python/bootstrap.html`.

The current `bootstrap.py` requires `--root`, writes the JSLB line
`tap.start`, and has no banner, `put` or `dir`. So the tool would fail at
its first check.

The tool also clones ttyd's default branch with `git clone` and builds it
with cmake, where the install builds the pinned 1.7.7 release with its
patches. Nothing runs either file, nor `python/xsjs_screenshot_wsl.py`,
which goes with them. Screenshots of the current page come from
`PageSession.shot_save` in `python/test_browser.py`.

Why the maintainer: 1.41's selected option says "`python/bootstrap.html`
stays", and 1.20's says "no other programs". The first may mean the file
stays, or only that its long lines stay unedited.

A. Delete `python/bootstrap.html`, `python/xsjs_screenshot.py` and
`python/xsjs_screenshot_wsl.py` with `rm`, together with the whitelist line
`python/*.html`, which would then match no file. Screenshots stay with
`test_browser.py`.

B. Keep all three, unchanged and unrun.

C. Keep all three, each header gaining one line saying it drives the retired
line processor bootstrap and nothing runs it.

D. Rewrite `xsjs_screenshot.py` for the current bring-up (`html/test.html`
on a root made as `test_wire.py` makes one, ttyd from
`powershell.ttyd_build`) and delete `bootstrap.html`.

### 2.21 `engine_db.restore_lines` has no caller, and its caller's design went with the plan

Class B. Importance 3: the resync of 1.17 would be built on this function,
and on a contract that only a gitignored record holds.

`restore_lines(db, full)` in `python/engine_db.py` yields a `db.restore`
line with the database file as blob 1, then one `db.file` line per cache
file. It is the server's half of 1.16 ("sent in subsequent JSLB messages
after the DB") and of 1.17. Its caller was the resync in section 1.4 of the
deleted plan (2.16).

The `db.file` lines name live paths under `<root>/cache`. A `kv.put`,
`kv.delete` or `db.drop` handled between the first and last line can prune a
named file, and writing that line then fails with `FileNotFoundError`. The
contract that prevents this, that the caller writes every line before it
reads the wire again, is only in `tmp/handoff_23_0919/1.46.1_progress.md`.

Why the maintainer: keeping, hardening or removing the function each builds
the deferred resync a different way, and the plan that held the caller was
deleted.

A. Keep it and write its contract beside it, as one comment line in
`API/python/engine_db.pyi` and `python/engine_db.py`: "The caller writes
every line before it reads the wire again, so no handler prunes a file a
line names."

B. Keep it and make it safe on its own. At its first `next` it hard links
each listed cache file to a name of its own under `<root>/cache`, and the
`db.file` lines name the links. The caller removes each link once its line
is written, and `kv_check` leaves those names alone.

C. Remove `restore_lines`, its stub entry and `TestRestoreLines` until the
resync is designed again. `Store.db_snapshot` stays.

D. Keep it as built, with its contract only in the record.

### 2.22 A script cannot read a value over `overflow_bytes`

Class B. Importance 3: the AI's scripts can write a large value they cannot
read, and the cache's file names reach the AI.

`ScriptStore.kv_get` in `ts/script.ts` is `substrate.Store.kv_get` bound to
the store. For a value over `overflow_bytes` (131072 bytes), it returns
`data` as the cache handle, the hex name of its file.

A script has no way to read a handle. `sink` and `CacheFiles.cache_read` are
not in `ScriptStore` (2.15), and `sql_run` sees `data` as NULL. The seeded
prompt says "a string in place of bytes is a cache handle, never text", but
gives no way to read one. The MCP tools `kv_get` and `doc_get`, and
`Store.doc_get`, read the cache themselves.

Why the maintainer: whether a handle may reach a script at all is a reading
of 1.28's "Exposing the existence of the DB beyond routine SQL queries is an
API violation". One choice changes the store's contract in both languages.

A. `store_routine` binds a `kv_get` that reads a cached value whole, as
`value_text` does, so `data` is always bytes. The prompt drops the handle
sentence, and the store is unchanged.

B. `substrate.Store.kv_get` always returns bytes, in both languages, and the
handle form leaves `KvValue`. `text_read`, `value_text` and the `kv.get`
handler stop reading the cache.

C. `ScriptStore` gains `cache_read(handle, offset, length)` on the store's
cache, and the prompt says how a script reads a handle.

D. As built.

### 2.23 1.34 left seven references to other modules in the TypeScript tests

Class B. Importance 3: closing it changes the public API of four modules and
their callers. Accepting it writes an exception into 1.34's rule that a test
module references only its own module and the harness.

The TypeScript tests moved to the gold record `test_settings.json`, leaving
these run time references:

- `ts/test_queue.ts` uses `dispatch.handler_register`, since
  `queue.TaskQueue` runs every handler through `dispatch`'s table, and
  `verbose.history_get`, since the queue traces into the thread's ring.
- `ts/test_mcp.ts` uses `dispatch.line_dispatch`, since
  `mcp.Server.wake_register` puts each wake in that table.
- `ts/test_tools_browser.ts` and `ts/test_agent.ts` use `provider.key_set`,
  since both modules read `provider.key_get()`. Nothing clears the key, so
  every later suite of the worker's stream runs with it set.
- `ts/test_boot.ts` checks `boot.test_page === page.test_page`, which no
  double can stand in for.
- `ts/test_substrate.ts`'s `kill_put` keeps the constant 131072, since the
  kill rung of `python/test_browser.py` calls it in a raw worker that has no
  harness values.

Separately, `harness.setting_get` and `gold_get` throw before `values_set`.
But every suite runs after the bring-up has set the values, so no test
reaches that throw.

Why the maintainer: finishing 1.34 to the letter adds parameters that no
item named to `queue`, `mcp`, `tools_browser` and `agent`, and a class to
`harness`. It would also do so before `provider.set`'s design (2.16) says
where the key lives.

A. Finish both:

- `TaskQueue`'s constructor takes `dispatch_run` and `sink_attach` takes
  `log`; `ts/page.ts` and `ts/worker_ai.ts` pass `dispatch.line_dispatch`
  and `verbose.log`.
- `mcp.Server`'s constructor takes `register`.
- `tools_browser.tools_register` and `agent.handlers_register` take
  `key_get: () => string`.
- `kill_put(store, size)` takes the size, and the kill rung passes
  `options.overflow + 1`.
- The boot identity check goes.
- `harness` exports a class `ValueKeeper` (`values_set`, `setting_get`,
  `gold_get`), and the module's three functions call one instance of it.
  `ts/test_harness.ts` tests the throw on an instance of its own.

B. The changes of A without `ValueKeeper`, so the throw stays untested.

C. Neither:

- The headers of `API/ts/unittest.d.ts` and `API/ts/harness.d.ts` gain "A
  test may also call the namespace that keeps state its module reaches with
  no parameter: the handler table of `dispatch`, the thread's verbose ring
  and the provider key."
- `AgentCase` gains a `tearDown` that calls `provider.key_clear()`.
- The boot check and the `kill_put` constant stay.

### 2.24 The MCP server answers an invalid message and drops an unknown notification, and runs on

Class B. Importance 2: a misspelt notification passes unseen, against "Never
swallow an error".

Under 1.8, an exception during a request is recorded as a failure, so the
server answers and stops. Two cases record no failure, the same in
`ts/mcp.ts` and `python/mcp.py` (`Server.message_handle`):

- A message that is not a JSON-RPC 2.0 request gets the answer -32600, and
  the server keeps running.
- A message without `id` returns nothing whatever its method, so an unknown
  notification is treated like `notifications/initialized`.

Why the maintainer: 1.8 has the server stop after an exception, and the
first rework judged an invalid message not to be one. Which client mistakes
stop the test protocol is the protocol owner's choice, in both servers.

A. Both stop the server. The -32600 answer records a failure, so
`line_handle` returns a `dispatch.Failure`. A notification other than
`notifications/initialized` throws a new `mcp.notification_unknown` "The
notification {0} is not served.", with no answer. Both stubs say so.

B. Only the unknown notification stops the server, as in A. The -32600
answer stays as built.

C. Both as built. The stub headers add that a notification of any method is
accepted without a check.

### 2.25 A non-finite number from a script is stored as `null` or fails unnamed

Class B. Importance 2: rarely, a script's bad value silently changes data on
both sides, or fails with a platform message.

A script's `doc_put` body or `turn_append` content can hold `Infinity`,
`-Infinity` or `NaN`, values that no JSLB decoder has seen:

- `json_canonical` in `ts/substrate.ts` writes an infinity through
  `utility.json_text`, whose `JSON.stringify` gives `null`. So the document,
  its push and the server's copy hold `null`.
- NaN fails in `number_canonical` as a platform `TypeError`.
- A `sql_run` parameter is bound locally, and its push then fails at the
  encoder's `jslb.number_refused`, after the commit.

The server's values arrive only through its decoder, so only the browser
meets this.

Why the maintainer: the rule that the JSLB decoders are the single door for
bad numbers leaves a value that never passes a decoder unchecked. That
conflicts with the rule that nothing gives a default.

A. `ts/jslb.ts` exports the encoder's refusal as `jslb.number_check(value)`,
which its `json_write` uses. `number_canonical` calls it first, so a stored
document or turn refuses a non-finite number as `jslb.number_refused` inside
the JSLB layer. `sql_run` stays as it is.

B. `number_canonical` refuses a non-finite number itself, as a new
`substrate.number_refused`, and the rule names values from scripts as the
one exception to the single door.

C. As built.

### 2.26 The PowerShell tests' five constants are read from `test_settings.json`

Class B. Importance 2: nothing breaks either way, but the answer either
rewords a project rule or moves keys through three packages.

The two PowerShell test scripts read five keys from `test_settings.json`, by
1.34's "have all test suite settings moved into that object":

- `powershell/test_powershell.ps1` reads `powershell.test_user`.
- `powershell/test_lint.ps1` reads `lint_module`, `lint_preset`,
  `lint_extensions` and `lint_line_length`.

The rule that 1.39 produced says "PowerShell constants go in
`settings.json`."

Separately, `lint_extensions` (`[".ps1", ".psd1"]`) repeats the two
`windows` rows of `python/reformat_table.json`, so a PowerShell extension
added to the table would be missed by the lint. `settings_check` in
`python/settings.py` refuses a missing or extra `powershell` key, so any key
that moves must reach `_POWERSHELL_TYPES` in the same change.

Why the maintainer: two of the maintainer's texts, 1.34 and 1.39 with its
rule, name different files for the same keys, and only the maintainer words
the project rules.

A. The rule stands:

- `lint_extensions` goes, and `test_lint.ps1` takes the name of every
  `windows` row from `python/reformat_table.json`.
- The other four move into the `powershell` object of `settings.json` and
  `API/settings.json`, read by `xsjs_util_get_setting`.
- `test_settings.json` loses its `powershell` object.
- The four keys are added to `_POWERSHELL_TYPES`, the `powershell` type of
  `ts/settings.ts` and `API/ts/settings.d.ts`, and the samples of both
  settings tests.

B. As A, but `lint_extensions` also moves into `settings.json` and keeps its
copy of the table.

C. As built, and the rule gains "those of the PowerShell tests in
`test_settings.json`".

D. As C, but `lint_extensions` goes as in A.

## Class C: little long term consequence

### 2.27 Nothing removes cache files that no row names

Class C. Importance 3: the cache grows by every orphan file, in the
browser's persistent OPFS cache once the resync is built. A sweep at the
wrong time would delete a blob being streamed.

`kv_check(db)` in both stores removes every cache file that no row of any
database under the root names, but only tests call it. Orphans come from:

- a kill between a cache file and its row;
- a rolled-back put;
- a `db_restore` that replaced a database: it does not prune the files only
  the replaced copy named, while `db_drop` does;
- a streamed blob refused as `substrate.file_small` or `substrate.db_closed`;
- the stream files of a killed server.

The decoder streams a blob to `<root>/cache/<uuid>` (`main_loop._sink_make`),
so a sweep between two reads of one blob would delete it.

Why the maintainer: 1.28 gives each store its own maintenance but names no
time for it, and when it runs decides what it may delete.

A. Each store runs `kv_check` once at its start, before the first line is
read, when no stream file can be in use: in `main_loop._prepare_run` after
the databases open, and in the browser's store when it opens. `db_restore`
also prunes the names only the replaced copy held, the twin of `db_drop`.

B. `db_restore` ends with `kv_check`'s sweep over every database, in both
languages, and nothing else changes.

C. Leave `kv_check` without a caller until a maintenance design exists. The
deferred program's design gains a sweep at its start and after each resync.

D. Remove `kv_check` from both stores, their stubs and their tests until
then.

### 2.28 1.23's two harness faults are closed only in part

Class C. Importance 2: 1.23 calls recovering all diagnostics from a TAP run
before shutdown the top priority, and both gaps lose some in rare cases.

The `SIGUSR1` gap:

- When a stub handler thread of `python/test_browser.py` fails,
  `StubServer.failure_send` signals the main thread, whose handler raises
  `CheckFailed` wherever it is.
- 1.23's selected fix wraps nine cleanups in `failure_held()`, which blocks
  the signal. But Python runs a signal handler between any two bytecodes, so
  the signal can land after a `finally` or `__exit__` starts and before the
  block.
- If it lands at the top of `TtydServer.process_stop`, it skips the
  `SIGTERM` and `SIGKILL` of ttyd's process group. ttyd and its server then
  outlive the run, and the last log lines are never read.
- If it lands in a drain rung's `finally`, it skips the `SIGCONT` to ttyd.
- No placement of the block closes the gap while the failure is raised from
  a signal handler.

The `_child_end` gap: in `python/test_echo_loop.py`, the forked child writes
how its work ended to `<scratch>/ending.txt`, then kills itself. When that
write fails, the child's traceback goes to stderr, and the test's TAP point
shows only the parent's `FileNotFoundError`.

Why the maintainer: the selected options named only blocking the signal and
moving the `open`, which is what was built. Closing the gaps replaces the
signal and the file, and both designs were only in gitignored records.

A. Close both:

- The stub sends no signal. `failure_send` keeps the first failure under
  its condition, and a new `StubServer.failure_check()` raises
  `CheckFailed` once.
- `RungTimer.seconds_left`, `PageSession.probe_wait` and
  `TtydServer.log_wait` call `failure_check` on each stub of the run before
  they sleep or select. A failure during a DevTools wait is raised when
  that wait ends, at the latest at the rung's deadline.
- `failure_raise`, `handler_kept`, the `SIGUSR1` handler, `failure_held()`
  and `HeldExit` go.
- The echo child's ending travels through a third pipe, which `child_run`
  opens beside the other two. `_child_end` writes the ending or the
  traceback to it with a loop of `os.write`.
- The parent drains that pipe and the output pipe together with `select`,
  and returns the report as the test's assertion text. `ending.txt` goes.

B. Close only the `SIGUSR1` gap, as in A.

C. Keep both as built, with the designs recorded here.

### 2.29 The failure texts of `python/devtools.py` and the drivers are plain English, outside `i18n`

Class C. Importance 2: every new check in a driver or in `devtools.py` adds
a text that a later answer would have to move.

- `python/devtools.py` writes its 24 raises in plain English. It is
  "Standard library only", so it imports no `internationalization`.
- `python/test_browser.py` raises 83 `CheckFailed` texts and
  `python/test_wire.py` 18, all in plain English.
- The texts the drivers expect from the page and the server, by contrast,
  are the gold's copies of `i18n` texts.

The rules expect `from internationalization import i18n` "in most modules",
and allow "internal error" for an error nobody expects.

Why the maintainer: no rule says whether the test drivers and `devtools.py`
are among "most modules". One guess leaves texts that cannot be translated.
The other makes `devtools.py` depend on a project module, and on its copy in
every root.

A. Keep plain English in `devtools.py` and in the drivers' own failure
texts. The rules gain, beside the `i18n` import rule: "the test drivers and
`python/devtools.py` write their own failure texts in plain English".

B. `devtools.py`'s 24 texts become `devtools.*` keys in `i18n/en-US.json`,
read through `from internationalization import i18n`, and its header loses
"Standard library only". The drivers stay in plain English.

C. As B, and every `CheckFailed` text of `test_browser.py` and
`test_wire.py` also becomes a `test_browser.*` or `test_wire.*` key.

### 2.30 `bind_address` is both where ttyd binds in Linux and where the Windows port proxy connects

Class C. Importance 2: the shipped `127.0.0.1` works. Another value can
leave the proxy connecting where nothing listens, which shows only when a
browser connects.

`powershell.bind_address` is used in three places:

- ttyd's `-i` in Linux;
- the port proxy's `connectaddress` on Windows;
- the address `xsjs_util_remove_proxy` matches.

The first two meet only through `wslrelay`. A value such as `0.0.0.0` would
make the proxy connect to `0.0.0.0` on Windows, and
`_xsjs_start_step_start_task` checks only that the relay and the proxy
listen.

Why the maintainer: whether this is one address or two is a design choice
that no item makes. A second setting that nobody asked for would be an
Accidental-Requirement if the address never changes.

A. As built: one loopback setting, with its comments explaining why.

B. A new `powershell.proxy_address`, "127.0.0.1", for `connectaddress` and
the removal match. It goes through `_POWERSHELL_TYPES`, `ts/settings.ts`,
`API/ts/settings.d.ts`, both settings files and the samples of the settings
tests.

C. The proxy connects to a literal `127.0.0.1`, a mode address like the
listen addresses, and `bind_address` stays ttyd's alone.

### 2.31 `i18n` is renamed in Python only

Class C. Importance 1: names only; nothing runs differently.

1.33's selected option renamed the Python module `i18n` to
`internationalization`, keeping the function `i18n()`. The rules now give
`from internationalization import i18n` as the expected import.

Four TypeScript names keep the old name: `ts/i18n.ts` with its global
functions `i18n` and `i18n_format`, its stub `API/ts/i18n.d.ts`, the suite
`ts/test_i18n.ts`, and the strings directory `i18n/`. The scope was the
coordinator's choice, since the item's text is about the Python `from`
import.

Why the maintainer: "rename the module" does not say which language.

A. Python only, as built.

B. TypeScript too: `ts/internationalization.ts` keeping its global `i18n()`,
`API/ts/internationalization.d.ts`, `ts/test_internationalization.ts`, and
every module list, page and whitelist line that names them.

C. As B, and the directory `i18n/` becomes `internationalization/`.

### 2.32 `rsa:2048` stays a literal in `xsjs_start.ps1` while `certificate_days` is a setting

Class C. Importance 1: the key changes only when the maintainer wants
another one.

`_xsjs_start_step_make_certificate` runs `openssl req -x509 -newkey
rsa:2048`, with `-days` from `powershell.certificate_days`. The PowerShell
handoff counted "a size" as a constant and an `openssl` flag as syntax that
stays. Its builder read `rsa:2048` as a flag's value and kept it. The other
reading was written only in a gitignored record.

Why the maintainer: 1.39's "move remaining PS constants there" does not say
whether a flag's value is a constant. Either reading keeps the script
working.

A. A new setting `certificate_key`, "rsa:2048":

- after `certificate_days` in `settings.json` and `API/settings.json`;
- typed in `API/ts/settings.d.ts`, `ts/settings.ts` and
  `_POWERSHELL_TYPES`, and added to the samples of the settings tests;
- read into `$certificate_key_` in `powershell/xsjs_util.ps1`, and passed as
  `'-newkey', $certificate_key_` in `xsjs_start.ps1`.

B. As built.
