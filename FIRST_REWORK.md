# First round learnings

## What to fix

These are the things that came up after the first round of implementation.

Each one will have to be fixed using the option selected under the problem
description. the selection option will be preceded by `--`. Do not research
the history of this document or the tasks leading up to it. instead just act
on it as follows:

you are the agent coordinator, execute the following fixes. no testing is
allowed between agent handoffs. use a file renaming scheme where task ids are
appended to filenames for the duration of an edit. don't run, build or test
anything ever, just be the best coordinator and then stop so i can review
changes. im afk, cant talk, but we will go over the unstaged changes after
before we test. please enact everything entirely as requested now. then stop
before the testing phase of the plan.


### 1.1 The banner of `xsjs_install.ps1` stops every `test_posix.py` run

The figlet banner of `xsjs_install.ps1` uses U+2588 and U+2591 to U+2593,
which the non-ASCII check of `python/test_posix.py` refuses, so every run,
smoke included, stops at `xsjs_install.ps1:41:19` before any later check.

-- The four characters join `_NON_ASCII_ALLOWED` for every file.

### 1.2 The stub comments under `API/` stop `test_posix.py` next

Once 1.1 is answered, `comments_check` stops at the maintainer's stubs: a
`;` in a comment of `API/python/tap_consumer.pyi`, then 86 comments in 24 of
the 25 `API/ts/*.d.ts` that run over one line or hold a `;`. The check
allows a one line comment holding, outside code spans, only letters,
digits, space and `.,"'?:!()/`. Several stub texts the review proposed
elsewhere (question 5.2) would fail the same check, and prettier rewrites
`API/ts/*.d.ts` whenever it runs.

-- The agent rewrites the 87 comments, each to one line within 79 columns,
a namespace's description moving to a header comment above
`declare namespace`, each `;` reworded; the maintainer reviews the diff in
git. These were not written by the maintainer, update declawed and all docs
to say no code was written by the maintainer.

### 1.3 `test_template_hooked` fails since the formatter split the hook

prettier split the one line
`<script data-worker>test_hook.engine_run();</script>` of
`html/test_engine.html` over three lines. `test_template_hooked` in
`python/test_page_build.py` counts the one line form, so it fails, and a
smoke run stops there when nothing earlier fails.

-- A `<!-- prettier-ignore -->` line above the hook. Add a declawed.md rule
  saving explicit formatting escapes like that are legal when there is no
  normal solution.

### 1.4 Executable bits

`test_posix.sh`, one of the two official test targets, and
`python/third_party_fetch.py`, which the install runs by its command line,
are mode 100644.

-- `chmod +x` both; git shows the mode changes unstaged for review.

## 2 Behaviour of the program

### 2.1 In debug mode a large legal wire line stops the AI worker

In debug mode `ts/worker_ai.ts` writes the rendering of every wire line into
a verbose entry bounded by `line_max` (1 MiB in the shipped
`settings.json`, which also ships `debug` true). A legal line well under
`line_max` can render past it and stop the worker with `queue.entry_over`.
The design asks for the rendering and says nothing past the bound.

-- A line whose rendering would not fit is logged as its header and the
sizes of its payload and blobs only. Change all limits to allow the max size
DB so be backed up as a single blob.

### 2.2 `console_run` faults when the console is not open

When tty 0 is not open, the AI's `console_run` tool in
`ts/tools_browser.ts` faults with `wire.socket_missing`, where the design
has the AI open the console with the user's permission. The proposed fix is
a new line `console.show`, AI to UI, answered once tty 0 is open: stub rows
in `API/ts/lines.d.ts`, `open_is()` in `API/ts/console_view.d.ts`, code in
`ts/tools_browser.ts`, `ts/page.ts` and `ts/console_view.ts`, and a new
string `page.console_busy`.

-- `console.show` shows the console view as ctrl-0 does and replies once
tty 0 is open.

### 2.3 `VACUUM` can make the browser's copy differ from the server's

-- remove explicit incremental database synchronization. entire DBs may be
  synced by passing them as blobs. otherwise the sync process is expected to
  be lossy. the server may have more history than the browser. the server may
  not have received everything in an orderly manner due to a connection loss.

  remove any normal database replication using database replication specific
  techniques. it should be possible to replace the database with a different
  kind of backing store and not change the protocol. update the docs, code and
  declawed.md to say that.

### 2.4 A tool's exception

A tool's exception becomes a JSON-RPC -32603 response with the stack in
`data`, and the server keeps running (`python/mcp.py`, `ts/mcp.ts`). In
TypeScript, a tool that submits a request and then throws faults the queue
with `queue.wait_missing`, and its own message is lost. The project's fail
loud rule stands against the server running on; MCP specifies an `isError`
result for tool errors.

The ability for the AI MCP to continue after an exception will be enabled
later. The test driver driving the MCP protocol should be able to see and
confirm whether it got an exception or expected response. Remember MCP is
still a testing protocol and an actual AI has not been put in as a requirement
for testing yet.

If the test protocol is running from the server side then the server needs to
get the exception message back from the browser gracefully and log it before
closing the connection gracefully and writing out TAP-protocol results.

### 2.5 `hello`'s fixed id

`python/bootstrap.py` sends `hello` with the fixed id 1 (`_HELLO_ID`),
while the seam record says bootstrap takes each request's id from
`dispatch.id_next`. A later server request taking `id_next` starts at 1 too
and collides with `hello`'s id. Request 1.13_1 to use `id_next` was declined
because it breaks bootstrap's decided import set.

-- `dispatch.id_next` starts at 102 in both languages, leaving 101 to `hello`.

### 2.6 Canonical JSON of turns without the 2^53 check

`python/engine_turn.py` builds canonical JSON with
`json.dumps(..., ensure_ascii=False, separators=(",", ":"), allow_nan=False)`,
without the substrate's check that integers stay within 2^53, which the
TypeScript store enforces with `substrate.integer_range`. A turn holding a
larger integer is stored by the server where the browser would refuse it.

-- Ignore.

Answer:

### 2.7 `wsl --list` exit codes are never read

`xsjs_util_get_distribution` in `powershell/xsjs_util.ps1` ignores the exit
codes of `wsl --list --verbose` and `wsl --list --running --quiet`, so a
failing `wsl` reads as "no distribution" or "none running". Telling them
apart needs WSL's real exit codes, a measurement on Windows.

-- Any nonzero exit is a hard error now, revisited if a normal state turns
out to exit nonzero.

### 2.8 Two `universe` rows for one world

Two `universe` rows can name the same current world; `ts/agent.ts` then
throws `agent.universe_ambiguous` at the next turn, away from the write
that caused it.

-- Throw `agent.content_ambiguous` wherever ambiguous content like this
  would have been added, before it is added.

### 2.9 A number that overflows a double

Both `jslb` decoders read a number token that overflows a double, such as
`1e400` (in Python also an integer of 310 to 4300 digits), as an infinity,
which both encoders then refuse to write (`jslb.number_refused`). The bad
value enters silently and fails later, elsewhere.

-- Both decoders refuse such a token at read, with `jslb.number_refused`
or a new `jslb.` name. this is to be the single door "bad number" enforcement
layer. bad data gets identified passing through JSLB layers. update declawed.md
to explain that exclusive sanitization layer system.

### 2.10 A throwing `sink_close` hides the first failure

In `bytes_feed` of `ts/jslb.ts`, a `sink_close` that throws inside
`#stream_shut`, called from the `catch`, replaces the original fault,
against the first failure rule. Python keeps the fault as `__context__`.

-- Wrap with `cause` under a nested JS object so it is all serialized in one 
  JSLB. so both errors are reported. update docs to say chaining nested "cause"
  entries is the correct way to describe cascading failure. always use the full
  "cause" tile and not "c". only the headers have single letter names.

### 2.11 `_cache_prune` skips `FileNotFoundError`

`_cache_prune` in `python/substrate.py` skips `FileNotFoundError` when it
removes a cache file, as an earlier coordinator prescribed; a later review
called it a swallowed error.

-- The skip stays.

### 2.12 `db_restore` brings no cache files

-- `db_restore(db, data, files)` brings the files, an edit of
`API/python/substrate.pyi`.

the file cache is part of the DB and should be sent in subsequent JSLB
messages after the DB. The max message size is based on the max DB size. That
means the max overflow file size is the same as the max DB size too.

the system has to be able to tolerate the loss of cached files when replicating
a database and that tolerance also has to be tested.

### 2.13 `seq` read before the write lock

`python/engine_sql.py` and `python/engine_turn.py` read a database's `seq`
before the write lock, which is taken lazily at the first write. This is
sound only while the server is the one process writing each database.

This all goes away and gets replaced with a lazy any lossy replication scheme I
keep describing. This is a failure of the requirements gathering process
because I have been explicitly trying to explain this is not a normal usage
pattern for a database that i am implementing and that normal database
replication patterns are an anti-pattern for this product. they are just being
used as filesystem accelerators that an AI talks to easily.

the plan calls for intentionally causing data base resynchronisation whenever
the user calls the browser window and then recovering gracefully.

when the user reopens the window they get DBs back from the server that are
missing content that was not synced. and then the AI running the MCP has to
restore the state of the experience back to being coherent.

The TS code is not responsible for maintaining database integrity across a wire
and the maintainer has consistently stated a design that does not have this
requirement. You have a document in your context about how non-requirements
become impossible to remove, and this is looking like one of those case studies.

### 2.14 Document versions past 2^53

- Do nothing about bad numbers except at the jslb decode layer. This is a
  problem for the AI using the MCP. Get with the design around that.

### 2.15 Compaction

Built, not confirmed: compaction runs in the browser's substrate before a
`user` turn is appended at the threshold (setting `turn_compact_turns`,
64), forwarded as `turn.compact` before `turn.append`; the server never
compacts by itself, and a forwarded `turn.append` never compacts, so one
line cannot compact twice.

-- This kind of relationship is prohibited between two DBs. See previous response
as to why this is solving a problem i don't have.

### 2.16 `hello` on tty 1's debug overlay

The overlay should show every wire line both ways, but `hello` carries
`provider_key`, which must stay in the worker's memory. A fix that showed
the whole `hello` leaked the key to the screen and the logs and was
reverted; `hello` is now not shown.

-- This is specification based on legacy code again. The first steps for this
  project involve using the TAP consumer/producer protocol to orchestrate
  top level debugging activity.

  rip out the existing "hello world" nonsense, i never asked for it, that was
  some example code written by an ai an now i keep having to explain how to fix
  something i never asked for while being ignored on what i want.

  replace it with a plan to use the TAP protocol over the wire. i don't want
  to see an example program running, i want to see tests suites everywhere
  and no other programs. the real programs are to be built towards, one
  test suite at at time, no shortcuts.

## 3 The tests' ability to catch faults

### 3.1 `test_posix.py` rewrites source files on every smoke run

`python/test_posix.py` runs the formatter over every whitelisted file in
each smoke run, so a test run changes source files, and an unformatted file
is rewritten instead of reported.

-- when doing quick checks only run  (`ruff format --check`, `prettier
  --check`, `shfmt --diff`) and rewrite nothing. have an advisory saying to
  wait until `normal-test` and just use that to do the reformatting.
-- Then in  `normal-test` mode do the reformatting.

### 3.2 No test of SHA-256's padding boundary

`ts/substrate.ts` carries its own streamed SHA-256 (`HashStream`), and no
vector tests the 55 and 56 byte padding boundary, where hand written
SHA-256 code most often breaks.

-- `python/vectors_make.py` adds digests of 55, 56 and 64 byte inputs,
checked by both languages.

### 3.3 Latent faults in the test harness (choose any)

-- `_child_end` in `python/test_echo_loop.py`: if the forked child's `open`
of its ending file fails, the child goes on to run the rest of the suite,
since that `open` stands outside the `try` before its `SIGKILL`; move it
inside, as `python/test_stall_loop.py` does with `finally`.

-- `python/test_browser.py`: the stub server's error reaches the main
thread by `SIGUSR1` at any point, so after a failure it can land in
cleanup, such as the `finally` resuming a stopped ttyd; block `SIGUSR1`
during cleanup so it lands after.

-- `xsjs_util_get_command_text` in `powershell/xsjs_util.ps1` logs the
wrong value if a command uses one of its own local names (`$command_`,
`$value_` and four others); no current call does; expand the command in a
scope that holds none of its locals.

Make a best effort to report these with relevant data, to screen, or logs.
If jslb logging is not possible then it is not a hard requirement. recovering
all diagnostics from a TAP run before shutdown is the top priority.

### 3.4 Requests the stub server does not serve

Since 1.19's fix, any error in the stub server's handlers ends the browser
run. If headless Chrome asks the stub for a path it does not serve, such as
`/favicon.ico` when a rung opens `/text`, or resets a held socket, the run
ends though the page is correct.

-- The stub answers `/favicon.ico` with 404 and records it in the rung log;
any other unserved path still ends the run.

### 3.5 A rung timer cannot fire inside a DevTools call

A rung's timer in `python/test_browser.py` cannot interrupt a DevTools
wait, so a rung can overrun by one DevTools wait, 60 s, against the smoke
run's 120 s. The proposed fix adds `ProtocolClient.deadline_set(end)` to
`API/python/devtools.pyi`, every later wait ending at the deadline when it
comes first.

-- Add `deadline_set` with its code and the rungs' calls.

### 3.6 The wire open timer rung tests the stub, not ttyd

`rung_opening` ("wire open timer") points the port at the stub server, not
ttyd, so it does not prove the port's open timer against the real server.
Two ways were recorded. The `Fetch.enable` form was written (pause the
port's token fetch, stop ttyd with `SIGSTOP`, answer with ttyd's token,
wait for the open timer) and backed out only because its public field
`PageEvents.requests_paused` in `python/devtools.py` had no stub line.

-- Ignore. Testing starts with running PY unit tests incrementally building up
  until JS unit tests can be run and reported back from the browser to the
  process running the PY testing process. progress proceeds in testing
  dependency order. modules are not allowed to call back into each other. that
  should mean they can be loaded and tested incrementally, 1 at a time, before
  loading and testing the next. select either one PY or JS module at a time
  starting with the PY TAP producer/consumer submodules. then pick the next
  module in the module dependency DAG that can be tested and move on to that
  one. just add support for using the TAP protocol to run server and app
  bring up. then once it has been woven into unit tests and integration tests
  show it can be run that way. 

  finally, once the reasonable limits of automated testing has been hit then
  then come back to this server bring up order question. what is most likely
  to happen at that time is directly bringing up the app as a final product
  as a separate testing strategy.

### 3.7 The wire test's first message

1.23 made the page's tty 1 first message carry only the token, dropping an
80 by 24 size copied from the old page. The client of `python/test_wire.py`
still sends `columns` and `rows`, so the wire test no longer opens tty 1 the
way the page does. That ttyd 1.7.7 accepts a first message without a size
is from memory, owed to testing.

-- Again make this the TAP protocol. JS producer module, PY consumer module.
  add ttyd protocol annotations as required. ensure that last remark is 
  preserved.

### 3.8 The provider of root "compact"

`rung_compact_auto` writes its own `provider.json` at a local stub, a
second rung using that file where the maintainer approved one (the HTTP
timeout rung), while the plan asks it to check the second chat request
after compaction.

this is another example of why we don't invent requirements. each instance of
the substrate module does its own maintenance. Exposing the existence of the
DB beyond routine SQL queries is an API violation.

I need a message based protocol because the DBs may be removed and i want the
app to still work.

this is an important requirement.

### 3.9 First failure in test runs

A smoke run ends at its first failure, but a `normal-test` run without
`--failfast` records every failing test of a module before it stops, and
the browser runs may set failfast false; the project rule asks for the
first failure only.

-- As built.


### 3.10 The xterm options and the resize path

The xterm `Terminal` options `{cols, rows, disableStdin}` in
`ts/console_view.ts` were written from memory of the 5.x API, never checked
against the pinned 5.5.0 typings. The resize path was recorded unreachable
without a fit addon, but `ConsoleView.rows_fit` now reaches `resize_send`
through `terminal.resize` and its `onResize`.

-- Delete `resize_send` and its tests, this is debug only. Expect to resolve
  any remaining issue.

## 4 Debug mode name form

### 4.1 Lines built in short names in debug mode

The rule (D27) is that in debug mode every line uses full names, the
worker's `names_full()` deciding. Five places build short names in debug
mode: the nine line types of `ts/tools_browser.ts`; `http.request` in
`post_make` of `ts/provider.ts`; `ConsolePort` in `ts/wire.ts`, which reads
`debug` itself as a second reader; `ui.input` and `ui.control_key` of
`DomPort` in `ts/page.ts`; and the worker's `fault` line in
`ts/error_overlay.ts`, which depends on nothing and can run before the
settings exist.

-- Code running before the settings exist should use the long names. That is
  not an optimization issue, and it proves the dual label system as a bonus.

## 5 Public interfaces and records

### 5.1 Small stub additions 

-- `HashStream` exported from `API/ts/utility.d.ts`, removing the SHA-256
copied into `ts/substrate.ts`.

-- `queue.line_bytes` exported from `API/ts/queue.d.ts`, removing the byte
measure copied into `ts/worker_ai.ts`.

-- `provider.key_clear()`, for the tests only, so that `key_get` with no
key set is tested (`provider.key_missing`).

-- The built additions to `API/ts/queue.d.ts` accepted: `owner?` on
`task_submit` and `line_notify`, `sink_attach`, the class `VerboseBatch`.

-- The built additions to `API/ts/unittest.d.ts` and
`API/ts/tap_producer.d.ts` accepted.

-- `API/ts/boot.d.ts` says `self.name` is `""` on the main thread, as the
code tests, not undefined.

### 6.3 `from i18n import i18n`

The project rules ban `from` imports but for `collections.abc` and
`typing`, while `API/python/i18n.pyi` calls `from i18n import i18n` "the
one `from` import allowed", and the Python tree uses it throughout.

-- rename the module "internationalization" and keep the function name
   i18n(). update the docs to say `from internationalization import i18n`
   is the expected form and that this is an expected import in most places as
   well.

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

-- create a test_settings.json object alongside settings.json and have all
  test suite settings moved into that object. when debug mode is enabled have
  the test settings sent to the browser right after the regular settings.json
  so that settings.json.
  replace the data derived from imports that can be pre-calculated with entries
  in test_settings.json. test_settings.json is the new "gold" record of the
  expected test results. the tests may use values derived from either
  of test_settings.json and settings.json. it is not required to hard code
  settings.json derivatives into test_settings.json.

this will require changes in both languages and is a huge task. that is
authorized even if it takes a while.

### 6.5 A comment for every class field?

Update the docs to say comments are not required, the one line limit
is an allowance for sentences improving comprehension and optimizing code
lookup times.

### 6.6 Platform errors with no `i18n` text

Tests of a platform `TypeError`, such as a write to a frozen object, check
only the error's type, since the message is the engine's, not an `i18n`
text.

an "internal error" can be represented with the "internal error" string if
there is no reasonable expectation of the error being thrown. there is no
reason to provide a detailed UI string for something that is unlikely to
be meaningful and debugging will be required anyway. update the declawed.md
about that.

### 6.7 Intermediates written outside `build/`

prettier writes Node's compile cache to the system's temporary directory,
and `python/mcp_stdio.py` sets no `sys.pycache_prefix`, though
intermediates go in `build/`.

-- correct things to go to build if they are not going to /tmp.

### 6.8 `powershell/test_lint.ps1` installs PSScriptAnalyzer

When PSScriptAnalyzer is missing, `powershell/test_lint.ps1` installs it
with `Install-PackageProvider` and `Install-Module`, beside the rule to ask
before any package manager is used.

-- As built; only the maintainer runs it.

### 6.9 ttyd's `--srv-buf-size` in the start script

`powershell/xsjs_util.ps1` passes ttyd `--srv-buf-size 1048576` as a
literal, while the setting `srv_buf_size`, also 1 MiB, governs only the
test runners' ttyd; the start script reads no setting by its record.

-- Read from the `settings.json`. move remaining PS constants there.
  update docs that PS consts go there too.

### 6.10 `.md` lines in the formatter whitelist

`LICENSE.md` and `README.md` stand in `python/reformat_whitelist.txt`,
checked by `mdformat --check` only, against the rule that `.md` files are
never added.

-- Both lines removed.

### 6.11 Lines over 79 columns the formatter cannot wrap

The comment "The AI worker runs the text of each `data-worker` script, in
order." is 80 columns in each of the three `html/*.html` templates after
the formatter's re-indent; "A snapshot streamed to the cache opens from its
handle, sink digest kept." is 80 columns in `ts/test_tools_browser.ts`;
five string literals of `python/test_browser.py` and three lines of
`python/bootstrap.html` (81, 82 and 86 columns, held by D22) run over.

-- Ideally the comments and strings are reworded shorter by hand;
`python/bootstrap.html` stays. otherwise add escapes that tell the scanner
 to skip it,l if those exist, otherwise report failure.

