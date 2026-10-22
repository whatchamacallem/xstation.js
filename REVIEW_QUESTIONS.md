# Review questions

The questions left open by the review recorded in `REVIEW_RESULTS.md`
(HEAD `867f11e`), ordered by how much the answer affects the correctness of
the resulting program and how likely it is to improve it. Section 1 blocks
every test run, section 2 is the program's behaviour, section 3 is the
tests' ability to catch faults, sections 4 to 6 are interfaces, records and
rules, and section 7 closes the rest in one answer.

Each question names the built option where there is one, gives a
recommendation, and lists its sources: report items as `<task> <item>`
(reports under `tmp/review/report/`), "postmortem" and "annex" items of
`REVIEW_RESULTS.md`, and sections of `REVIEW_EXECUTION.md`. Write a letter
after "Answer:", several where the question says "choose any", or a
sentence for another choice.

## 1 Blocking: every test run stops or cannot start

### 1.1 The banner of `xsjs_install.ps1` stops every `test_posix.py` run

The figlet banner of `xsjs_install.ps1` uses U+2588 and U+2591 to U+2593,
which the non-ASCII check of `python/test_posix.py` refuses, so every run,
smoke included, stops at `xsjs_install.ps1:41:19` before any later check.

a) As built: nothing more is allowed and every run stops there.

b) The four characters join `_NON_ASCII_ALLOWED` for every file.

c) The four are allowed in the PowerShell rows only, by a sixth key of the
formatter table.

d) The maintainer redraws the banner in ASCII.

e) The script builds the banner at run time from `[char]0x2588` and the
others.

Recommended: c), which unblocks every run and keeps every other file to
ASCII.

Sources: 1.2 10.10, 1.10 10.3, 1.11 10.4; annex 1.7.1; REVIEW_EXECUTION.md
4.8.4.39, 11.2.5.3.

Answer:

### 1.2 The stub comments under `API/` stop `test_posix.py` next

Once 1.1 is answered, `comments_check` stops at the maintainer's stubs: a
`;` in a comment of `API/python/tap_consumer.pyi`, then 86 comments in 24 of
the 25 `API/ts/*.d.ts` that run over one line or hold a `;`. The check
allows a one line comment holding, outside code spans, only letters,
digits, space and `.,"'?:!()/`. Several stub texts the review proposed
elsewhere (question 5.2) would fail the same check, and prettier rewrites
`API/ts/*.d.ts` whenever it runs.

a) The agent rewrites the 87 comments, each to one line within 79 columns,
a namespace's description moving to a header comment above
`declare namespace`, each `;` reworded; the maintainer reviews the diff in
git.

b) The maintainer rewrites them.

c) `comments_check` skips `API/`.

d) `comments_check` allows several lines and `;` in `.d.ts` and `.pyi`
files only.

Recommended: a), so the stubs meet the rule every other file meets and the
wording stays the maintainer's to approve.

Sources: 1.2 4.1 to 4.3, 9.1, 9.2; postmortem 2.1.1 to 2.1.3; annex 3.1.3,
3.1.6, 3.1.19; REVIEW_EXECUTION.md 4.9.6.4, 11.2.5.11.

Answer:

### 1.3 `test_template_hooked` fails since the formatter split the hook

prettier split the one line
`<script data-worker>test_hook.engine_run();</script>` of
`html/test_engine.html` over three lines. `test_template_hooked` in
`python/test_page_build.py` counts the one line form, so it fails, and a
smoke run stops there when nothing earlier fails.

a) A `<!-- prettier-ignore -->` line above the hook.

b) The test matches the hook whatever its white space.

c) The split reverted by hand, which the next format run undoes.

Recommended: b), which survives every format run with no formatter
directive in the template.

Sources: 1.18 10.1, 1.20 10.1, 1.41 10.1; annex 1.8.9; REVIEW_EXECUTION.md
4.7.12, 11.10.5.1.

Answer:

### 1.4 Executable bits

`test_posix.sh`, one of the two official test targets, and
`python/third_party_fetch.py`, which the install runs by its command line,
are mode 100644.

a) `chmod +x` both; git shows the mode changes unstaged for review.

b) `test_posix.sh` only.

c) Neither; both are run through their interpreter.

Recommended: a).

Sources: 1.10 10.1, 1.11 11.1; annex 1.10.26, 2.4.4; REVIEW_EXECUTION.md
11.2.5.1.

Answer:

### 1.5 When the tests run

Nothing in the review ran. The 189 fixes and 7 partial fixes across 86
files have never been compiled or run, and 90 values are owed to testing:
tsc and pyright strict, every changed suite, every browser rung,
sqlite3.wasm's error texts, ttyd's and Chrome's behaviour. The seven
changed PowerShell files are owed to `powershell/test_lint.ps1`, which runs
on Windows only.

a) After section 1, the agent runs `test_posix.sh` smoke and fixes each
first failure in turn, then the normal run the same way; the PowerShell
lint stays the maintainer's.

b) As a), smoke only.

c) The maintainer runs the tests and reports the first failure.

d) Every question below is answered and built first, then the tests run.

Recommended: a), so failures that no answer below changes are found before
more code is built on them.

Sources: postmortem 7, 8; annex section 2.

Answer:

## 2 Behaviour of the program

### 2.1 In debug mode a large legal wire line stops the AI worker

In debug mode `ts/worker_ai.ts` writes the rendering of every wire line into
a verbose entry bounded by `line_max` (1 MiB in the shipped
`settings.json`, which also ships `debug` true). A legal line well under
`line_max` can render past it and stop the worker with `queue.entry_over`.
The design asks for the rendering and says nothing past the bound.

a) As built: the worker faults.

b) The rendering is cut to fit the entry and ends with the count of bytes
cut.

c) A line whose rendering would not fit is logged as its header and the
sizes of its payload and blobs only.

d) Renderings get their own bound, a new setting.

Recommended: b), which keeps debug mode running and states exactly what was
cut.

Sources: 1.39 10.1; postmortem 4.3; annex 1.10.24; REVIEW_EXECUTION.md
11.20.3.21.

Answer:

### 2.2 `console_run` faults when the console is not open

When tty 0 is not open, the AI's `console_run` tool in
`ts/tools_browser.ts` faults with `wire.socket_missing`, where the design
has the AI open the console with the user's permission. The proposed fix is
a new line `console.show`, AI to UI, answered once tty 0 is open: stub rows
in `API/ts/lines.d.ts`, `open_is()` in `API/ts/console_view.d.ts`, code in
`ts/tools_browser.ts`, `ts/page.ts` and `ts/console_view.ts`, and a new
string `page.console_busy`.

a) As built: the tool faults.

b) `console.show` shows the console view as ctrl-0 does and replies once
tty 0 is open.

c) `console.show` opens tty 0 with the view hidden, which the design lists
as an open research goal.

d) The tool throws its own error telling the AI the user has to open the
console.

Recommended: b), whose design and code are written out in the proposal.

Sources: 1.27 4.2, 9.1; postmortem 2.2.5; annex 3.1.9.4, 3.1.15.1, 3.5.9 to
3.5.11.

Answer:

### 2.3 `VACUUM` can make the browser's copy differ from the server's

`Store.db_compact` in `ts/substrate.ts` runs `VACUUM` in the browser's copy
only. SQLite may renumber the rowids of a table without an INTEGER PRIMARY
KEY, so the two copies can hold different rowids at the same `seq`, which
the desync check cannot see.

a) Accepted and documented.

b) `VACUUM` forwarded so the server runs it too; the two renumberings are
still not guaranteed equal.

c) `db_compact` throws for a database holding any table without an INTEGER
PRIMARY KEY.

d) Measure in the testing phase whether this sqlite3.wasm build renumbers,
then decide.

Recommended: c), which fails loud instead of letting the copies drift.

Sources: 1.24 4.9, 10.1; 1.37 7.1; postmortem 2.2.4; annex 1.10.20, 2.6.5;
REVIEW_EXECUTION.md 11.16.6.9.

Answer:

### 2.4 A tool's exception

A tool's exception becomes a JSON-RPC -32603 response with the stack in
`data`, and the server keeps running (`python/mcp.py`, `ts/mcp.ts`). In
TypeScript, a tool that submits a request and then throws faults the queue
with `queue.wait_missing`, and its own message is lost. The project's fail
loud rule stands against the server running on; MCP specifies an `isError`
result for tool errors.

a) As built, the TypeScript message still lost.

b) The process ends, as a failed handler does, with the tool's own message
in both languages.

c) An `isError` result carrying the tool's message and stack, the server
running on, in both languages.

d) As built, except that the TypeScript tool's own message is the one
reported.

Recommended: c), so the AI sees its tool's error and nothing is swallowed.

Sources: 1.2 10.2, 1.3 10.1, 1.4 10.4, 1.13 10.2, 1.15 10.3; annex 1.10.2;
REVIEW_EXECUTION.md 11.5.5.2, 12.4.4.4.

Answer:

### 2.5 `hello`'s fixed id

`python/bootstrap.py` sends `hello` with the fixed id 1 (`_HELLO_ID`),
while the seam record says bootstrap takes each request's id from
`dispatch.id_next`. A later server request taking `id_next` starts at 1 too
and collides with `hello`'s id. Request 1.13_1 to use `id_next` was declined
because it breaks bootstrap's decided import set.

a) As built.

b) bootstrap imports `dispatch` and uses `id_next`, the import set record
amended.

c) `dispatch.id_next` starts at 2 in both languages, leaving 1 to `hello`.

Recommended: c), which removes the collision and keeps bootstrap's import
set.

Sources: 1.13 4.3, 10.6; 1.16 10.4; postmortem 2.3.18; annex 1.10.11;
REVIEW_EXECUTION.md 11.5.7.1, 11.8.3.10, 11.8.3.14, 12.3.2.3.

Answer:

### 2.6 Canonical JSON of turns without the 2^53 check

`python/engine_turn.py` builds canonical JSON with
`json.dumps(..., ensure_ascii=False, separators=(",", ":"), allow_nan=False)`,
without the substrate's check that integers stay within 2^53, which the
TypeScript store enforces with `substrate.integer_range`. A turn holding a
larger integer is stored by the server where the browser would refuse it.

a) As built.

b) An API addition `substrate.json_canonical(value)`, which `engine_turn`
uses, so one function builds canonical JSON.

c) `engine_turn` checks the range itself before `json.dumps`.

Recommended: b).

Sources: 1.4 10.3, 1.14 10.4, 1.15 10.1; annex 1.10.5; REVIEW_EXECUTION.md
4.7.5.

Answer:

### 2.7 `wsl --list` exit codes are never read

`xsjs_util_get_distribution` in `powershell/xsjs_util.ps1` ignores the exit
codes of `wsl --list --verbose` and `wsl --list --running --quiet`, so a
failing `wsl` reads as "no distribution" or "none running". Telling them
apart needs WSL's real exit codes, a measurement on Windows.

a) As built.

b) The maintainer runs both commands with no distribution and with none
running and reports the exit codes; the agent then checks them.

c) Any nonzero exit is a hard error now, revisited if a normal state turns
out to exit nonzero.

Recommended: c), which ends the silent misreading at once and measures the
codes at the first run.

Sources: 1.11 4.13; postmortem 2.2.3; annex 2.5.3.

Answer:

### 2.8 Two `universe` rows for one world

Two `universe` rows can name the same current world; `ts/agent.ts` then
throws `agent.universe_ambiguous` at the next turn, away from the write
that caused it.

a) As built.

b) `universe.world` UNIQUE, so the second row's insert fails where it is
made.

Recommended: b).

Sources: 1.16 10.2, 1.26 10.1; annex 1.10.14; REVIEW_EXECUTION.md 4.7.4,
11.8.5.2, 11.18.5.1.

Answer:

### 2.9 A number that overflows a double

Both `jslb` decoders read a number token that overflows a double, such as
`1e400` (in Python also an integer of 310 to 4300 digits), as an infinity,
which both encoders then refuse to write (`jslb.number_refused`). The bad
value enters silently and fails later, elsewhere.

a) As built.

b) Both decoders refuse such a token at read, with `jslb.number_refused`
or a new `jslb.` name.

Recommended: b).

Sources: 1.12 10.6; annex 1.10.10.

Answer:

### 2.10 A throwing `sink_close` hides the first failure

In `bytes_feed` of `ts/jslb.ts`, a `sink_close` that throws inside
`#stream_shut`, called from the `catch`, replaces the original fault,
against the first failure rule. Python keeps the fault as `__context__`.

a) Wrap with `cause` under a new `jslb.` name, so both errors are reported.

b) A stub addition `sink_abort`, called instead of `sink_close` after a
failure.

c) As built, the sink side already dropping a blob closed after a failure.

Recommended: a).

Sources: 1.12 10.3; annex 1.9.6; REVIEW_EXECUTION.md 11.4.4.3, 11.4.6.6.

Answer:

### 2.11 `_cache_prune` skips `FileNotFoundError`

`_cache_prune` in `python/substrate.py` skips `FileNotFoundError` when it
removes a cache file, as an earlier coordinator prescribed; a later review
called it a swallowed error.

a) The skip stays.

b) The error is raised.

Recommended: b); no record names a path that removes cache files behind the
prune.

Sources: 1.2 10.1, 1.14 10.1; annex 1.10.1; REVIEW_EXECUTION.md 11.6.5.1,
12.2.4.1.

Answer:

### 2.12 `db_restore` brings no cache files

`Store.db_restore` in `python/substrate.py` replaces the database file and
opens it, but a restored image can name cache files the server lacks; a
value whose file is absent then fails at its read. No server line calls
`db_restore` yet.

a) As built.

b) `db_restore` raises `substrate.cache_unknown` with the first absent
hash, before the live database closes; no signature change.

c) `db_restore(db, data, files)` brings the files, an edit of
`API/python/substrate.pyi`.

Recommended: b).

Sources: 1.14 4.5, 10.3; postmortem 2.4.2; annex 1.9.7.

Answer:

### 2.13 `seq` read before the write lock

`python/engine_sql.py` and `python/engine_turn.py` read a database's `seq`
before the write lock, which is taken lazily at the first write. This is
sound only while the server is the one process writing each database.

a) The single process model is recorded as a requirement; the code stays.

b) The paths that write take the write lock before reading `seq`.

Recommended: a) if the single process model is the design, b) otherwise.

Sources: 1.14 10.4, 1.15 10.2; annex 1.10.6; REVIEW_EXECUTION.md 4.7.6,
11.7.5.2.

Answer:

### 2.14 Document versions past 2^53

`RefParts.version` in `API/ts/substrate.d.ts` is a JavaScript number, so
`version_find` rounds a version past 2^53, and `doc_head` can name a
version `doc_put` did not write if sqlite3.wasm returns a Number. `doc_put`
already counts exactly past 2^53.

a) `version` a `bigint` in both twins.

b) `version` stays a number, documented as rounded past 2^53.

c) `doc_put` refuses a version past 2^53 with `substrate.integer_range`, as
the TypeScript store already refuses larger doubles.

Recommended: c), one integer rule for the whole store; no real document
reaches 2^53 versions.

Sources: 1.4 4.2, 1.24 4.7, 10.2; 1.37 6.1; postmortem 2.2.1, 3.7; annex
1.9.5, 2.6.3, 3.1.12.1.

Answer:

### 2.15 Compaction

Built, not confirmed: compaction runs in the browser's substrate before a
`user` turn is appended at the threshold (setting `turn_compact_turns`,
64), forwarded as `turn.compact` before `turn.append`; the server never
compacts by itself, and a forwarded `turn.append` never compacts, so one
line cannot compact twice.

a) Confirmed as built.

b) Compaction moves to `ts/agent.ts`, at the end of each turn.

c) As a), with another threshold or a named constant in place of the
setting (state which).

Recommended: a).

Sources: 1.4 10.1, 1.8 10.2, 1.13 10.3, 1.15 10.4, 1.24 10.3; annex 1.5.2
to 1.5.4; REVIEW_EXECUTION.md 4.8.4.27, 11.7.5.4, 11.16.4.24.

Answer:

### 2.16 `hello` on tty 1's debug overlay

The overlay should show every wire line both ways, but `hello` carries
`provider_key`, which must stay in the worker's memory. A fix that showed
the whole `hello` leaked the key to the screen and the logs and was
reverted; `hello` is now not shown.

a) As built: `hello` not shown.

b) `hello` shown, rendered from a copy without `provider_key`, with a test
that the overlay holds no key.

Recommended: b), which meets both requirements.

Sources: 1.28 4.3, 10.6; 1.39 10.2; postmortem 2.2.6, 4.2; annex 1.10.23.

Answer:

## 3 The tests' ability to catch faults

### 3.1 `test_posix.py` rewrites source files on every smoke run

`python/test_posix.py` runs the formatter over every whitelisted file in
each smoke run, so a test run changes source files, and an unformatted file
is rewritten instead of reported.

a) As built.

b) It checks only (`ruff format --check`, `prettier --check`,
`shfmt --diff`) and rewrites nothing.

c) The rewrite moves to `normal-test`.

Recommended: b).

Sources: annex 1.8.12; REVIEW_EXECUTION.md 11.2.5.4.

Answer:

### 3.2 No test of SHA-256's padding boundary

`ts/substrate.ts` carries its own streamed SHA-256 (`HashStream`), and no
vector tests the 55 and 56 byte padding boundary, where hand written
SHA-256 code most often breaks.

a) As built.

b) `python/vectors_make.py` adds digests of 55, 56 and 64 byte inputs,
checked by both languages.

Recommended: b).

Sources: 1.12 10.5, 1.21 10.2; annex 1.10.9; REVIEW_EXECUTION.md 4.7.15,
11.13.5.2.

Answer:

### 3.3 Latent faults in the test harness (choose any)

a) `_child_end` in `python/test_echo_loop.py`: if the forked child's `open`
of its ending file fails, the child goes on to run the rest of the suite,
since that `open` stands outside the `try` before its `SIGKILL`; move it
inside, as `python/test_stall_loop.py` does with `finally`.

b) `python/test_browser.py`: the stub server's error reaches the main
thread by `SIGUSR1` at any point, so after a failure it can land in
cleanup, such as the `finally` resuming a stopped ttyd; block `SIGUSR1`
during cleanup so it lands after.

c) `xsjs_util_get_command_text` in `powershell/xsjs_util.ps1` logs the
wrong value if a command uses one of its own local names (`$command_`,
`$value_` and four others); no current call does; expand the command in a
scope that holds none of its locals.

d) None.

Recommended: a), b) and c).

Sources: 1.31, 1.34 10.2, 1.35 remarks; postmortem 4.3; annex 1.10.25,
2.1.23.

Answer:

### 3.4 Requests the stub server does not serve

Since 1.19's fix, any error in the stub server's handlers ends the browser
run. If headless Chrome asks the stub for a path it does not serve, such as
`/favicon.ico` when a rung opens `/text`, or resets a held socket, the run
ends though the page is correct.

a) As built.

b) The stub answers `/favicon.ico` with 404 and records it in the rung log;
any other unserved path still ends the run.

c) The stub answers every unserved path with 404, recorded in the rung log.

d) Decide after the first browser run shows whether Chrome asks.

Recommended: b).

Sources: 1.19 11.1, 1.35 11; annex 2.4.10.

Answer:

### 3.5 A rung timer cannot fire inside a DevTools call

A rung's timer in `python/test_browser.py` cannot interrupt a DevTools
wait, so a rung can overrun by one DevTools wait, 60 s, against the smoke
run's 120 s. The proposed fix adds `ProtocolClient.deadline_set(end)` to
`API/python/devtools.pyi`, every later wait ending at the deadline when it
comes first.

a) Add `deadline_set` with its code and the rungs' calls.

b) As built.

Recommended: a).

Sources: 1.19 4.4, 9.3; postmortem 3.5; annex 1.9.8, 3.1.5.2, 3.5.5.

Answer:

### 3.6 The wire open timer rung tests the stub, not ttyd

`rung_opening` ("wire open timer") points the port at the stub server, not
ttyd, so it does not prove the port's open timer against the real server.
Two ways were recorded. The `Fetch.enable` form was written (pause the
port's token fetch, stop ttyd with `SIGSTOP`, answer with ttyd's token,
wait for the open timer) and backed out only because its public field
`PageEvents.requests_paused` in `python/devtools.py` had no stub line.

a) The `Fetch.enable` form, with `requests_paused` added to
`API/python/devtools.pyi` and recorded in REVIEW_EXECUTION.md 4.5.

b) ttyd's `--max-clients 1`.

c) As built, on the stub.

Recommended: a), whose code and test were already written once.

Sources: 1.6 4.5; 1.18 9.2, 10.6, 10.7; 1.34; postmortem 3.4, 4.1; annex
1.6.9, 1.6.10, 3.1.5.1, 3.4.4, 3.5.4; REVIEW_EXECUTION.md 12.5.5.4.10.

Answer:

### 3.7 The wire test's first message

1.23 made the page's tty 1 first message carry only the token, dropping an
80 by 24 size copied from the old page. The client of `python/test_wire.py`
still sends `columns` and `rows`, so the wire test no longer opens tty 1 the
way the page does. That ttyd 1.7.7 accepts a first message without a size
is from memory, owed to testing.

a) `python/test_wire.py` sends only the token, as the page does.

b) Both send a size, 1.23's change reverted.

c) As built, the two differing.

Recommended: a), the first wire and browser runs proving that ttyd accepts
it.

Sources: 1.23 4.3, 1.36 10.4; annex 1.6.12, 2.4.12.

Answer:

### 3.8 The provider of root "compact"

`rung_compact_auto` writes its own `provider.json` at a local stub, a
second rung using that file where the maintainer approved one (the HTTP
timeout rung), while the plan asks it to check the second chat request
after compaction.

a) As built: the maintainer extends the approval to this rung, and
REVIEW_EXECUTION.md 2.10.1, 11.5.3.26 and 12.5.2.7.3.3 are amended.

b) A scripted root that checks the server's turns and the `turn.*` order
and drops the check of the second chat request, which a unit test of
`prompt_build` in `ts/test_agent.ts` proves instead.

Recommended: a), which checks end to end what compaction changes, against a
local stub only.

Sources: 1.7 4.4, 10.2; postmortem 2.3.17; annex 1.5.1, 3.4.1, 3.4.20,
3.4.40.

Answer:

### 3.9 First failure in test runs

A smoke run ends at its first failure, but a `normal-test` run without
`--failfast` records every failing test of a module before it stops, and
the browser runs may set failfast false; the project rule asks for the
first failure only.

a) As built.

b) Only the 120 s deadline ends a smoke run at once; other failures run the
module out.

c) Every run ends at its first failure.

Recommended: c), the project rule.

Sources: 1.2 10.9, 1.5 10.5, 1.9 10.1; annex 1.10.30; REVIEW_EXECUTION.md
11.1.5.9, 12.2.4.7.

Answer:

### 3.10 The xterm options and the resize path

The xterm `Terminal` options `{cols, rows, disableStdin}` in
`ts/console_view.ts` were written from memory of the 5.x API, never checked
against the pinned 5.5.0 typings. The resize path was recorded unreachable
without a fit addon, but `ConsoleView.rows_fit` now reaches `resize_send`
through `terminal.resize` and its `onResize`.

a) Pin `@xterm/addon-fit` and fit with it.

b) Delete `resize_send` and its tests.

c) As built, with the options checked against the 5.5.0 typings now.

Recommended: c).

Sources: 1.5 10.3, 1.29 10.3, 1.30 10.1; annex 1.10.27, 2.3.24;
REVIEW_EXECUTION.md 4.7.8, 11.22.5.1.

Answer:

## 4 Debug mode name form

### 4.1 Lines built in short names in debug mode

The rule (D27) is that in debug mode every line uses full names, the
worker's `names_full()` deciding. Five places build short names in debug
mode: the nine line types of `ts/tools_browser.ts`; `http.request` in
`post_make` of `ts/provider.ts`; `ConsolePort` in `ts/wire.ts`, which reads
`debug` itself as a second reader; `ui.input` and `ui.control_key` of
`DomPort` in `ts/page.ts`; and the worker's `fault` line in
`ts/error_overlay.ts`, which depends on nothing and can run before the
settings exist. Every fix needs a stub change.

a) Pass the form down: `tools_register(..., settings_get, full)`, `full?`
on `chat_request` and the image request, `ConsolePort(base_url, full)`,
`DomPort(container, full)`, with the proposed stub edits and code; the
`fault` line recorded as the one exception.

b) As a), but `ConsolePort` keeps reading `debug` itself.

c) The rule narrowed to the lines the worker builds itself, the five
recorded as exceptions.

d) As built, left open.

Recommended: a).

Sources: 1.3 4.1 to 4.5, 9.6 to 9.8; 1.23 4.5, 9.1, 10.1; 1.27 4.3, 9.2;
1.29 4.3, 9.1; postmortem 2.3.7 to 2.3.10, 2.3.23; annex 1.4.1, 1.4.2,
3.1.10, 3.1.11.1, 3.1.14, 3.1.16, 3.4.5, 3.4.35, 3.4.39, 3.5.1, 3.5.2,
3.5.6, 3.5.13.

Answer:

## 5 Public interfaces and records

### 5.1 Small stub additions (choose any)

a) `HashStream` exported from `API/ts/utility.d.ts`, removing the SHA-256
copied into `ts/substrate.ts`.

b) `queue.line_bytes` exported from `API/ts/queue.d.ts`, removing the byte
measure copied into `ts/worker_ai.ts`.

c) `provider.key_clear()`, for the tests only, so that `key_get` with no
key set is tested (`provider.key_missing`).

d) The built additions to `API/ts/queue.d.ts` accepted: `owner?` on
`task_submit` and `line_notify`, `sink_attach`, the class `VerboseBatch`.

e) The built additions to `API/ts/unittest.d.ts` and
`API/ts/tap_producer.d.ts` accepted.

f) `API/ts/boot.d.ts` says `self.name` is `""` on the main thread, as the
code tests, not undefined.

g) None.

Recommended: a) to f).

Sources: 1.20 10.4; 1.22 9.1; 1.24 4.5, 9.1; 1.25 4.6, 9.1; 1.28 4.11, 9.1,
10.3; annex 1.9.2, 1.9.4, 3.1.8.3, 3.1.8.4, 3.1.11.2, 3.1.13, 3.1.17,
3.5.7, 3.5.8, 3.5.12.

Answer:

### 5.2 Corrections to the records that need no choice

In the stubs: `reply_make`'s `blobs` defaulting to `None`, `main` declared
in `API/python/third_party_fetch.pyi`, the handler comment of
`API/ts/dispatch.d.ts`, the constructor and `OwnerTable` comments of
`API/ts/queue.d.ts`, and the `mcp` rows, the `HttpResponse` comment and
four lane rows of `API/ts/lines.d.ts`. In `API/README.md`, the removed
planning document's name. In REVIEW_EXECUTION.md, about thirty statements
the code proved wrong, such as three PowerShell files lacking a byte order
mark (all eight have one), eight patch hunks (seven), test counts,
`ServerHold` and `worker.snapshot_reply`. Several proposed stub texts would
fail `comments_check`, and the text proposed for 11.4.6.4 contradicts its
own reason (both languages now pin their behaviour for a 5000 digit
number).

a) The agent applies them all, rewording to pass `comments_check` and
reconciling 11.4.6.4; the maintainer reviews the diff in git.

b) As a), for the stubs and `API/README.md` only; REVIEW_EXECUTION.md stays
as written, a closed record.

c) The maintainer applies them.

d) None.

Recommended: a), so later sessions do not build on statements the code has
shown wrong.

Sources: postmortem 2.3.1 to 2.3.6, 2.3.11 to 2.3.15, 2.3.19, 2.3.20,
2.4.1, 6.2, 6.4; annex 3.1.1 to 3.1.3, 3.1.7, 3.1.8.1, 3.1.8.2, 3.1.9.1 to
3.1.9.3, 3.1.19, 3.2, and 3.4 but for the items tied to questions 3.6, 3.8
and 4.1.

Answer:

### 5.3 `source_put`'s arguments

The plan named the server tool `source_put {name}`; `API/mcp/tools.json`
and `python/engine_system.py` take `{name, text}`.

a) `{name, text}`, the record corrected.

b) `{name}`, the code changed.

Recommended: a).

Sources: 1.1 10.4; annex 1.9.1; REVIEW_EXECUTION.md 12.1.5.2.

Answer:

## 6 Rules, with little or no change in behaviour

### 6.1 Do name prefixes count among the two words?

The two word rule is settled for `test_` methods only, where the prefix
does not count (`test_unregistered` became `test_called_early`). Rungs: 137
names in `python/test_browser.py` and `python/test_wire.py`, 108 with one
word after `rung_`, 29 with two (`rung_level_two`, `rung_drain_poll`,
`rung_compact_auto`, `rung_blob_max` and others). Test classes: most Python
classes are `Test` and one word, nine are `Test` and two (`TestByteOrder`,
`TestIdNext` and others); most TypeScript classes are `Test` and two
(`TestValueStore`), a few `Test` and one (`TestDigest`, `TestOverlay` and
others).

a) No prefix counts, as for `test_`: the 108 rungs, the Python `Test` and
one classes and the few TypeScript ones are renamed.

b) `rung_` and `Test` count, `test_` staying as settled: the 29 rungs, the
nine Python `Test` and two classes and most TypeScript classes are renamed.

c) Rung functions and test classes are exempt from the two word rule.

d) Separate answers for `rung_` and `Test` (write them).

Recommended: a), one reading for every prefix.

Sources: 1.2 10.5, 10.6; 1.7 10.1; 1.17 10.3; 1.21 10.4; 1.26 10.3; annex
1.1.1, 1.1.2; REVIEW_EXECUTION.md 12.2.2.5, 12.2.4.5.

Answer:

### 6.2 `non_ascii_check` and `Comment` in `python/test_posix.py`

The plan expects the names `non_ascii_check` (three words) and `Comment`
(one word), against the two word rule.

a) They stand as the plan's exceptions.

b) They are renamed to two words, such as `ascii_check` and
`CommentSpan`.

Recommended: b).

Sources: 1.2 10.7, 1.10 10.6; annex 1.1.3; REVIEW_EXECUTION.md 11.2.3.3,
11.2.3.4.

Answer:

### 6.3 `from i18n import i18n`

The project rules ban `from` imports but for `collections.abc` and
`typing`, while `API/python/i18n.pyi` calls `from i18n import i18n` "the
one `from` import allowed", and the Python tree uses it throughout.

a) The maintainer adds the exception to the project rules.

b) The code changes to `import i18n` and `i18n.i18n(...)` everywhere.

Recommended: a).

Sources: 1.1 10.2, 1.2 10.4, 1.9 10.2, 1.12 10.4, 1.13 10.4, 1.16 10.5,
1.17 10.4; annex 1.2.1.

Answer:

### 6.4 What a test module may import

The rule is that a test module imports only its module and the harness.
As built, tests also import the modules their module's API is built on:
`ts/test_substrate.ts` imports `jslb`, `utility` and `i18n`;
`python/test_dispatch.py`, `python/test_settings.py` and every
`python/test_engine_*.py` import `jslb` or `dispatch`;
`python/test_mcp_stdio.py` imports `mcp`; `python/test_substrate.py`
imports `jslb`; `ts/test_agent.ts` and `ts/test_script.ts` use real
`substrate`, `queue`, `provider` and other modules, not doubles; and the
rungs of `python/test_browser.py` import siblings inside their functions.

a) The rule admits the modules below the tested one, as built everywhere.

b) The strict rule: plain literals and doubles in place of every such
import.

c) The rule names the admitted modules (`jslb`, `utility`, `i18n`,
`dispatch`, `mcp`).

Recommended: a).

Sources: 1.8 10.1, 1.13 10.5, 1.14 10.2, 1.26 10.2, 1.5 10.4; annex 1.2.2
to 1.2.6.

Answer:

### 6.5 A comment for every class field?

Uncommented fields stand in `ts/mcp.ts`, `ts/provider_script.ts` and
`ts/tools_browser.ts`; task 1.24 read "one comment line per construct" as
one per field, task 1.27 as none required.

a) Every field gets its own one line comment.

b) None is required; the rule limits a comment to one line, as
`comments_check` enforces.

Recommended: b), since the project rules ban documentation added only
because some is missing.

Sources: 1.25 10.1, 1.27 10.1; 1.37 7.1; annex 1.3.1.

Answer:

### 6.6 Platform errors with no `i18n` text

Tests of a platform `TypeError`, such as a write to a frozen object, check
only the error's type, since the message is the engine's, not an `i18n`
text.

a) The type only, as built.

b) The type and the engine's message text.

Recommended: a).

Sources: 1.21 10.3, 1.36 10.2; annex 1.10.19.

Answer:

### 6.7 Intermediates written outside `build/`

prettier writes Node's compile cache to the system's temporary directory,
and `python/mcp_stdio.py` sets no `sys.pycache_prefix`, though
intermediates go in `build/`.

a) Both pointed at `build/`: `NODE_COMPILE_CACHE` under `build/` for
prettier, `sys.pycache_prefix` in `python/mcp_stdio.py`.

b) Node's compile cache disabled (`NODE_DISABLE_COMPILE_CACHE=1`), and
`sys.pycache_prefix` as a).

c) As built.

Recommended: a).

Sources: 1.2 10.3, 1.10 10.4, 1.13 10.1, 1.41 10.3; annex 1.8.11, 1.10.3;
REVIEW_EXECUTION.md 11.2.5.11, 11.5.5.1.

Answer:

### 6.8 `powershell/test_lint.ps1` installs PSScriptAnalyzer

When PSScriptAnalyzer is missing, `powershell/test_lint.ps1` installs it
with `Install-PackageProvider` and `Install-Module`, beside the rule to ask
before any package manager is used.

a) As built; only the maintainer runs it.

b) It fails loud naming the missing module, and the maintainer installs it
once.

Recommended: b).

Sources: 1.10 10.7; annex 1.7.3.

Answer:

### 6.9 ttyd's `--srv-buf-size` in the start script

`powershell/xsjs_util.ps1` passes ttyd `--srv-buf-size 1048576` as a
literal, while the setting `srv_buf_size`, also 1 MiB, governs only the
test runners' ttyd; the start script reads no setting by its record.

a) As built, a literal.

b) Read from the `settings.json` the start copies.

Recommended: a), the decline already confirmed.

Sources: 1.1 4.4, 1.11 10.1, 1.31; annex 1.7.4.

Answer:

### 6.10 `.md` lines in the formatter whitelist

`LICENSE.md` and `README.md` stand in `python/reformat_whitelist.txt`,
checked by `mdformat --check` only, against the rule that `.md` files are
never added.

a) Both lines removed.

b) Both kept.

Recommended: a), the project rule.

Sources: 1.1 10.3, 1.10 10.5, 1.41 3.3; annex 1.8.2; REVIEW_EXECUTION.md
11.2.5.14.

Answer:

### 6.11 Lines over 79 columns the formatter cannot wrap

The comment "The AI worker runs the text of each `data-worker` script, in
order." is 80 columns in each of the three `html/*.html` templates after
the formatter's re-indent; "A snapshot streamed to the cache opens from its
handle, sink digest kept." is 80 columns in `ts/test_tools_browser.ts`;
five string literals of `python/test_browser.py` and three lines of
`python/bootstrap.html` (81, 82 and 86 columns, held by D22) run over.

a) The comments and strings are reworded shorter by hand;
`python/bootstrap.html` stays.

b) Accepted as they are.

Recommended: a).

Sources: 1.2 10.8, 1.18 10.2, 1.27 10.2, 1.41 10.2; annex 1.8.5 to 1.8.8.

Answer:

## 7 Everything else

### 7.1 Built options with no alternative proposed

Each of these stands as built, with no alternative proposed or none
preferred by any report: the setting name `verbose_level`; the page names,
categories and root "level" shared by the debug and console rungs of
`python/test_browser.py`; the label grain and the smoke suites; the value
of `blob_max` and the size of the large proofs; a window counting blob
bytes only; two TAP documents per browser run; the fixed SAH pool and cache
capacities; `probe.fault` not finding the TAP `<pre>`; `probe.wire_pending`
reading `WirePort`'s private fields; the sleep loop of `devtools.page_open`;
the TAP module layout and grammar; the two minute limit, the options and
defaults, the place of `alarm_plan` and the infrastructure's test modules;
where the formatter table lives, how `test_lint.ps1` picks its files, the
matching rule and `test_lint.ps1` stopping at the first faulty file; which
shell scripts keep verbose levels; no tests of the two official targets;
the location of `ttyd.log`; where the install's WSL step runs and which
checkout it uses; a verbose line before `settings_set` throwing
`settings.not_set`; shell level 1 through the console; the form of the
debug trace; only the console reading `verbose_level`; `-h` printing help
to the pty and exiting 0; the defaults as a whole; `python/page_build.py`
writing f-strings as a tool without `i18n`; `python/pyproject.toml`,
`html/engine.css` and `API/sql/*.sql` outside the whitelist as built.

a) All accepted as decided.

b) All accepted but those named in the answer.

c) Left open.

Recommended: a).

Sources: annex 1.1.4, 1.1.5, 1.6.1 to 1.6.8, 1.6.11, 1.7.5 to 1.7.7,
1.8.1, 1.8.3, 1.8.4, 1.8.12, 1.10.4, 1.10.8, 1.10.12, 1.10.13, 1.10.15 to
1.10.18, 1.10.28, 1.10.29.

Answer:
