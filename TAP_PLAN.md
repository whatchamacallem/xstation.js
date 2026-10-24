# TAP plan

No code was written by the maintainer.

The plan of the bring up of the server and the page as a TAP run of test
suites, and of the protocol, limits, errors and tests it stands on. It is
the plan that `API/` follows: a stub changes only with this plan. It was
written top down, before any code of it. It stops before the testing phase:
it says what wave 2 of the session builds, in packages 1.46.1 to 1.46.7,
what wave 3 migrates, in 1.47, and how the bring up will be run later.
Nothing is run now. The item numbers, as 1.20, are those of the session's
log.

An unconfirmed assumption is written where it arises, as "Unconfirmed:".

## 1 The bring up over TAP

1.20 and 1.51. The `hello` line, its example program and everything that
existed for them are removed: `hello`, `boot.hello`, the start chain from
the hello to the first render, the engine page and the test engine page.
No example program runs anywhere. The one page there is is the test page,
and what the server and the page do when they come up is run test suites,
one TAP stream per thread. The real programs are built toward one test
suite at a time.

The engine page and the test engine page go with the hello because each
runs a program other than the test suites: the engine page the program by
`boot.boot_run`, the test engine page the same program under hooks for the
browser test's rungs. 1.20 asks for no such program: "i don't want to see
an example program running, i want to see tests suites everywhere and no
other programs. the real programs are to be built towards, one test suite
at at time, no shortcuts"; and 1.26 leaves "directly bringing up the app as
a final product as a separate testing strategy" for after the reasonable
limits of automated testing are reached. The wave 1 edits of the two
templates go with them: the `prettier-ignore` line of 1.3 above the hook of
`html/test_engine.html`, and the comment 1.41 shortened in both.

### 1.1 The sequence

1. ttyd runs `python3 <root>/python/bootstrap.py --root <root>` for each
   connection of tty 1, as the start script and the test drivers start it.
2. bootstrap puts its pty in raw mode, takes `<root>/engine.lock`, reads
   `<root>/settings.json`, opens the root's log, and has the main loop file
   prepare the root: open every database, create the fixed ones that are
   missing, seed the scripted provider's script when `_files` lacks it and
   the metaverse when it lacks the `universe` table.
3. bootstrap writes the first line, `tap.start`, a request with the fixed
   id 101. Its payload is `settings`, the settings as read, and in debug
   mode `test_settings`, `<root>/test_settings.json` read by
   `jslb.json_decode`. It is built in full names in debug mode, short names
   otherwise, as the server's settings say.
4. The page loads; its main thread makes the AI worker from the texts of
   the worker scripts and posts it the channel's end and the page's address.
5. The worker fetches ttyd's token, opens `/ws` with the subprotocol `tty`
   and sends the first message, `{"AuthToken": token}` only. Its decoder
   reads the first line under fixed bounds, `first_line_max` 10 MiB and no
   blob, since the settings do not exist yet.
6. At `tap.start` the worker readies sqlite3.wasm and the test pool, cleared
   at start, as the globals `test_sqlite3` and `test_pool`, and the test
   cache, its files cleared at start, as the wire's sink, so that a blob
   over `overflow_bytes` streams to a file, then `worker_ai.tap_start`: it
   sets its settings and, when present, the gold
   record in `harness`, builds its queue with the ports to the UI thread and
   the server, in debug mode wrapped in the `WireTap`, registers its fault
   reporting, sends `settings.set` with the same two values to the UI
   thread, and answers `tap.start` with an Empty reply, `r` 101.
7. bootstrap reads that reply a byte at a time and runs the main loop.
8. In debug mode the worker runs its suites, the modules of section 3.4, as
   one TAP stream, each line a `tap.line` push to the server the moment it
   is made. The server appends each to `<root>/tap/typescript.tap`,
   unbuffered. When the stream ends the worker sends `ui.tests` to the UI
   thread, which runs its suites the same way, its `tap.line` pushes going
   through the worker to the server.
9. Outside debug mode no gold record is sent, since 1.34 sends the test
   settings in debug mode only and the suites read them, so no suite runs,
   and nothing else does: there is no program yet.

Every later request of the server takes its id from `dispatch.id_next`,
which starts at 102 in both languages (1.9). The server sends none while
only the test suites run, so its main loop still refuses any reply.

`settings.put` in debug mode still rewrites the root's settings, for the
next connection. `system.restart` still makes the server exec itself; the
new process writes a new `tap.start`, which the page refuses with
`wire.start_twice`: only a reload of the page takes a new first line.

### 1.2 What is removed

From the boot and the pages: the `hello` line and `lines.Hello`,
`boot.hello` and `lines.BootHello`, `page.hello_shown`, the engine page
`html/engine.html` and the test engine page `html/test_engine.html`,
`ts/test_hook.ts`, `boot.boot_run`, `boot.page_main`,
`boot.worker_ai_main`, the boot's engine platform and pool, `page.page_main`,
`page.test_engine` and the page's engine start, `worker_ai.worker_start`,
`StartChain`, `chain_register`, `WorkerStart`, `ChainParts`, `StartStore`,
the start's fetch of snapshots, its MCP handshakes and its first render. From
the server: the hello's `bootstrap`, `sha256`, `pid`, `root` and `seq`
fields, the reading of the provider key and of `provider.json` at the
start. `page_build.py` builds one page, from `html/test.html` with the test
bundle, under the name it is given; the start script serves it as
`hyperposition-engine.html`.

The modules of the program are not removed: the agent, the tools, the
store, the scripted provider, the media port, the console view, the
overlays, the DOM port and the page's handlers stay, with their unit
suites, as what the suites build toward. The seed of a new metaverse stays
with the main loop. Only their assembly into a running program goes.

### 1.3 Deferred: the provider key and the provider information

The provider key and the provider information are not sent at bring up,
since no program but the test suites runs. Once a real program runs, the
design is this. Right after the Empty reply to `tap.start`, the server sends
`provider.set`, a request whose id comes from `dispatch.id_next`, wire lane,
SERVER to AI, no blob, reply Empty. Its payload is `provider_key`, the value
of the environment variable that the setting `provider.variable` names,
`XSJS_PROVIDER_KEY`, which the start script passes into WSL, and, when the
setting `provider.scripted` is false, `provider_info`: the root's
`provider.json` read by `jslb.json_decode`, exactly the keys `base_url`,
`chat_model` and `image_model`, each a non empty string. A missing variable
or file fails the server loud before the line is written, with the texts the
bootstrap has today. The worker keeps the key by `provider.key_set`, in its
memory only, and gives the information to the agent and the tools; the UI
thread never receives either. `provider.set` is a secret line: the worker's
`WireTap`, the server's trace and the queue's debug log write it as its
header and the sizes of its payload only, the form of a line too large for
its verbose entry (section 7), from one constant list of secret line types,
`provider.set` alone, in each language. This is why the old `hello` could
not be shown on tty 1's overlay without leaking the key: no line that holds
a secret is ever rendered.

### 1.4 Deferred: the real program's start and the planned recovery

1.17. The plan intentionally causes a database resync whenever the user
closes the browser window and opens it again, and recovers gracefully. Once
a real program runs, the design is this. The page's store opens its pool
with `clearOnInit` true, so nothing of an earlier window survives in the
browser. After `tap.start` and `provider.set`, the server sends every
database it holds but `_verbose`, each by `engine_db.restore_lines`: the
`db.restore` line with the database file as blob 1 and the count `files`,
then one `db.file` line per cache file it holds for that database (section
6.4). The worker restores each with `Store.db_restore(db, data, files)`. The
reopened window so gets the server's databases back, missing what the
browser committed and the server never received, as a lost line or a
closed window loses it. Then the agent's MCP clients start, `initialize`
and `tools/list` to both servers, and the AI running the MCP reads the
restored state through its tools and restores the experience to coherence:
it re-renders the scene the world's `scene` row names, writes again what a
lost line lost, and puts back what a lost cache file held. No code checks or
repairs the databases across the wire. The engine page's elements, the
media port, the console view, the overlays and the permit dialog come back
as the page of that program, each built after its suite.

1.26 asks to come back to the bring up order once the reasonable limits of
automated testing are reached; the likely outcome is bringing up the app
directly, as a final product, as a separate testing strategy. That is not
designed here.

## 2 Test settings and the gold record

1.34. `test_settings.json`, beside `settings.json`, holds every test suite
setting and is the gold record of expected test results. A test may use a
value derived from either file; a value derivable from `settings.json` is
not copied into `test_settings.json`.

### 2.1 The file

Top level keys are the settings of the test infrastructure and of the
PowerShell tests; a test module's own values live under its language and
its module name, so two agents never write the same object.

```text
smoke_seconds     the deadline of a smoke-test run, 120; read by category.py
module_seconds    the timer of one Python test module, 120; read by test_all.py
long_task_ms      the long task target of the browser test, 5, moved here
                  from settings.json
powershell        test_user, lint_module, lint_preset, lint_extensions,
                  lint_line_length: the constants of test_powershell.ps1 and
                  test_lint.ps1
python            { "<test module>": { ... } }, filled in wave 3
typescript        { "run": "unit", "<test module>": { ... } }; `run` picks
                  the TypeScript run: "unit", the unit suites of section 3.4,
                  or "wire", the wire rungs of section 4
```

The shipped file holds the values that move now. Wave 3 adds each test
module's gold under `python.<module>` and `typescript.<module>`.

### 2.2 Sent to the browser

In debug mode the server reads `<root>/test_settings.json` and sends it as
`test_settings` in `tap.start`, right after `settings`, and the worker sends
both to the UI thread in `settings.set`. Every root gets a copy: the start
script lists it in `powershell.root_files`, and the test drivers copy it,
or write their own, into each root they make. The first line, settings and
test settings together, must stay under `first_line_max`, 10 MiB.

### 2.3 The harness

A test module imports, or in TypeScript references, only its own module
and the harness. The harness is a new module in each language that reads
the two files and depends on no other module of the project, so it sits
below every module in the testing order and its texts are plain English.

- Python, `python/harness.py`: `setting_get(id)` and `gold_get(id)`, ids of
  keys joined by `.`, reading `settings.json` and `test_settings.json` at
  the checkout's top once, at the first call, with the standard library's
  `json`; `KeyError` on an unknown id. `settings_copy()` and `gold_copy()`
  return `copy.deepcopy` of the whole object of `settings.json` and of
  `test_settings.json`, read as `setting_get` and `gold_get` read them, for
  a test that writes a root's `settings.json` with some values changed and
  a driver that writes a root's `test_settings.json` from the checkout's.
  The Python harness of a test module is the standard library's `unittest`
  and this module. Its tests are in
  `python/test_test.py`, which tests the infrastructure for testing.
- TypeScript, `ts/harness.ts`, in the test bundle only:
  `values_set(settings, gold)` once per thread by the bring up,
  `setting_get(id)` and `gold_get(id)`, throwing before `values_set` and on
  an unknown id. The TypeScript harness of a test module is `unittest` and
  this module. Its tests are `ts/test_harness.ts`.

Unconfirmed: the Python harness reads its two files with the standard
library's `json`, not `jslb.json_decode`, because the harness must import no
module of the project; the test settings are the maintainer's own file, not
data passing through the system.

### 2.4 The migration

Wave 3, 1.47, moves every test module of both languages to this rule, one
agent per language, by the handoffs `tmp/handoff_23_0919/1.47.1.md`, the
Python tests, and `tmp/handoff_23_0919/1.47.2.md`, the TypeScript tests,
which list each module's changes. The rules:

1. A test module imports, or in TypeScript calls at run time, only its own
   module and the harness of its language; type only references to `lines`
   and the other declarations stay. `i18n` is not the harness in either
   language, nor is its Python module `internationalization`. The test
   drivers, `test_all.py`, `test_wire.py`,
   `test_browser.py` and `test_posix.py`, import the infrastructure they
   run on: `category`, `harness`, `tap_consumer`, `tap_producer`,
   `devtools`, `page_build` and `vectors_make`. `test_all.py` also imports
   the drivers it runs, and `test_posix.py` `reformat`, the formatter whose
   checks it runs. The TypeScript drivers, `ts/test_all.ts` and
   `ts/test_wire_rungs.ts`, reference `unittest`, `tap_producer`, `harness`
   and the modules they run through.
2. A value a test derived through another module becomes a gold entry under
   `python.<test module>` or `typescript.<test module>`, an `i18n` text
   under its `texts` and a line under its `lines`, when it can be written
   exactly by hand, as an `i18n` text with its arguments in place, an
   argument known only at run time left its placeholder for the test to
   fill, a size or a literal, or a vector that `vectors_make.py` writes
   when it cannot, as a digest; never a value written by guess. A value
   derivable from `settings.json` is read with `setting_get` and derived,
   not copied. When neither is possible the import stays, and the agent's
   report lists it as not migrated, with the seam that would migrate it, a
   parameter of the module's API, written as its signature.
3. A collaborator object a module's API takes is a double written in the
   test module, not the real module; platform objects and the test page's
   globals `test_sqlite3`, `test_pool` and `test_vectors` stay. In Python a
   module that the module under test imports stays real, and one of its
   calls is replaced only by patching that attribute through the module
   under test's own name for the module, or through `sys.modules` for a
   module imported inside a function, never by a string target that names
   the other module; TypeScript's namespaces are frozen, so there only a
   parameter takes a double.
4. The test suites' own constants, as the timeouts and sizes their writers
   chose, move into the gold.
5. The first line must stay under `first_line_max`, so a large value is a
   vector or is made by the test, never gold; and since the file passes
   through the JSLB decoders, the gold holds no number they refuse.
6. `test_tap_producer` and `test_tap_consumer` in Python and
   `test_tap_producer` and `test_unittest` in TypeScript run before the
   harness is tested, so they read no gold.

## 3 The testing order

1.26. Testing starts with the Python unit suites, building up until the
TypeScript suites can be run in the browser and reported back over TAP to
the Python process that runs the Python suites. It proceeds in testing
dependency order, one module at a time, Python or TypeScript, starting with
the Python TAP producer and consumer, each next module the next one of the
module dependency DAG that can be tested. The bring up is itself the first
integration test of the TypeScript side.

### 3.1 The DAG, from the imports

Python, derived from each module's imports after this plan, the modules a
test driver alone uses included:

```text
tap_producer, tap_consumer, harness, internationalization, reformat,
third_party_fetch, devtools                 none
category                                    harness
jslb, verbose, substrate, stall_loop        internationalization
settings                                    internationalization, jslb
vectors_make                                jslb
dispatch                                    internationalization, jslb
page_build                                  vectors_make
engine_tap                                  dispatch, internationalization,
                                            jslb, verbose
engine_verbose                              dispatch, internationalization,
                                            jslb, verbose
engine_kv, engine_doc, engine_db,
engine_turn, engine_sql                     dispatch, internationalization,
                                            jslb, substrate
mcp                                         internationalization, dispatch
engine_mcp                                  dispatch, internationalization,
                                            jslb, mcp
engine_system                               dispatch, internationalization,
                                            jslb, mcp, settings
echo_loop                                   dispatch, engine_tap,
                                            internationalization, jslb,
                                            settings
main_loop                                   dispatch, engine_*,
                                            internationalization, jslb, mcp,
                                            settings, substrate, verbose
bootstrap                                   internationalization, jslb,
                                            settings, verbose, and the main
                                            loop file it loads
mcp_stdio                                   engine_system,
                                            internationalization, jslb, mcp,
                                            settings
```

TypeScript, derived from the namespaces each module calls at run time,
type only references left out, as those of `tap_producer` to `unittest`:

```text
harness, unittest, tap_producer, ui_strings,
error_overlay                                  none
i18n                                           ui_strings
utility                                        i18n
settings                                       utility, i18n
verbose                                        utility, settings, i18n
jslb                                           utility, i18n
dispatch                                       utility, settings, i18n,
                                               jslb
queue                                        utility, settings, i18n,
                                               verbose, jslb, dispatch
http, media                                    utility, i18n, jslb, queue
wire                                           utility, settings, i18n,
                                               jslb, queue, dispatch
provider                                       utility, settings, i18n, jslb
mcp                                            utility, settings, i18n,
                                               jslb, dispatch, queue
substrate                                      utility, settings, i18n,
                                               jslb, dispatch
script                                         utility, i18n, verbose,
                                               substrate
provider_script                                utility, i18n, jslb, queue,
                                               provider
tools_browser                                  utility, settings, i18n,
                                               jslb, dispatch, queue,
                                               substrate, provider, script
agent                                          utility, settings, i18n,
                                               dispatch, queue, substrate,
                                               provider
console_view                                   utility, settings, i18n,
                                               jslb, dispatch, queue
overlay                                        i18n
page                                           error_overlay, utility,
                                               settings, i18n, verbose, jslb,
                                               dispatch, queue, harness
worker_ai                                      error_overlay, utility,
                                               settings, i18n, verbose,
                                               jslb, dispatch, queue, wire,
                                               harness
boot                                           error_overlay, utility,
                                               settings, queue, wire,
                                               substrate, page, worker_ai
test_wire_rungs                                tap_producer, harness,
                                               utility, settings, jslb,
                                               dispatch, queue, wire, mcp
test_all, the page's entry                     unittest, tap_producer,
                                               harness, settings, jslb,
                                               queue, boot, test_wire_rungs
```

### 3.2 Findings

These are recorded, not fixed.

1. Neither language has an import cycle. Moving `names_full()` from
   `worker_ai` into `settings` (section 9.3) keeps it so: called from
   `wire`, `provider` and `tools_browser`, which `worker_ai` depends on, it
   would have made a cycle.
2. A cycle in the testing order: the tests of `jslb` read the vectors that
   `vectors_make` writes as `test_jslb` loads, and `vectors_make` imports
   `jslb`. So `jslb` is tested on vectors written by an untested `jslb`.
   The order below keeps `test_jslb` first; the vectors' own checks in
   `test_vectors_make` come right after it.
3. Modules call back into modules that depend on them, at run time, through
   functions they are given: `verbose.sink_set` (the queue's verbose batch),
   `settings.sender_register` (the page and the worker),
   `error_overlay.stop_register` and `report_register` (the page and the
   worker), `jslb.LineDecoder`'s sink (the store's cache files), every port's
   `line_receive` (the queue), `wire.WirePort.wire_open` and
   `close_receive` (the boot and the worker), `dispatch.handler_register`
   (every handler), `mcp.Server.tool_register` and `wake_register` (the
   tools), and in Python `mcp.Client`'s reply functions and
   `mcp_stdio.stdio_run`'s register. None is an import, so none breaks the
   order, and a test passes a double in their place. This plan removes two
   others: `substrate.Store.forward_set` and `wire.WirePort.cache_attach`.
   1.26's "modules are not allowed to call back into each other" is read as
   no cycle of the modules' own references: a ban of every function given
   at run time would ban the dispatch of a line to its handler, on which the
   queue stands, while the consequence the item names, that the modules
   "can be loaded and tested incrementally, 1 at a time", holds with a
   double in each place.

### 3.3 The order of the Python run

`python/test_all.py` runs, in this order, each as one block of one TAP
stream on stdout: test_tap_producer, test_tap_consumer, test_test (the
harness and category), test_internationalization, test_jslb,
test_vectors_make, test_settings, test_verbose, test_substrate,
test_dispatch, test_mcp, test_stall_loop, test_engine_tap,
test_engine_verbose, test_engine_kv, test_engine_doc, test_engine_db,
test_engine_turn, test_engine_sql, test_engine_mcp, test_engine_system,
test_echo_loop, test_main_loop, test_bootstrap, test_mcp_stdio,
test_third_party_fetch, test_page_build, test_devtools, test_reformat,
test_test_posix. Then the checks of
`test_posix.py`, then the wire test, `test_wire.py` (section 4), the first
TypeScript run and the bring up's own integration test, then the browser
test, `test_browser.py`, whose `suites` root runs the TypeScript unit
suites of section 3.4 over TAP and checks the TypeScript stream with the
TAP consumer.

### 3.4 The order of the TypeScript run

`typescript.run` "unit" runs one stream per thread, the worker's first, as
the DAG asks, since the UI only modules depend on modules the worker tests:

- The worker: test_tap_producer, test_unittest, test_harness,
  test_error_overlay, test_ui_strings, test_i18n, test_utility,
  test_settings, test_verbose, test_jslb, test_dispatch, test_queue,
  test_http, test_wire, test_provider, test_mcp, test_substrate,
  test_script, test_provider_script, test_tools_browser, test_agent,
  test_worker_ai.
- Then the UI thread, at `ui.tests`: test_tap_producer, test_unittest,
  test_error_overlay, test_media, test_console_view, test_overlay,
  test_page, test_boot.

`error_overlay` runs on both threads, and `worker_ai` registers its report
function, so its tests run in both streams, each stream the cases of its
own thread: the report function in the worker's, the screen and the stop
function in the UI thread's. `boot` depends on `page` and on `worker_ai`,
so its tests run after both, last in the UI thread's stream.

Each stream stops after the first module that fails. The UI thread also
shows its own stream, the failed lines marked, in `#tap_output`.

## 4 The wire test as TAP

1.27. The wire test is a TAP run: the producer is a JavaScript module that
runs in the page, `ts/test_wire_rungs.ts`, and the consumer is Python,
`python/test_wire.py` with `python/tap_consumer.py`. The Python WebSocket
client of the wire test, which spoke ttyd's protocol as the page does but
not quite, is removed: the page's own wire is what is tested.

### 4.1 The producer

`ts/test_wire_rungs.ts` runs when `typescript.run` is "wire", on the
worker, instead of the unit suites of both threads: the UI thread runs
nothing in a wire run. TypeScript's `unittest` is synchronous
and a rung waits on the network, so the rungs are not `unittest` tests: each
rung is a task chain on the worker's queue, which submits its request to the
server, sleeps on the reply, and in its wake checks the reply against the
gold and writes its point by a `tap_producer.Tracker`. The stream has the
shape the consumer checks: the version line, one block, `test_wire_rungs`,
with its plan and one point per rung, then the parent point and the parent
plan `1..1`. The first rung that fails writes its `not ok` point with the
reason as diagnostics, then `Bail out!`: the first failure ends the stream.
Each rung's parameters, sizes and expected payloads come from
`typescript.test_wire_rungs` in the root's test settings.

### 4.2 The consumer

`python/test_wire.py` makes its roots as the start script does, writes each
root's `test_settings.json` with `typescript.run` "wire" and the rungs'
gold, starts the ttyd that `xsjs_install.ps1` builds, with
`--srv-buf-size` from the setting `srv_buf_size` and the command
`bootstrap.py --root <root>`, adding `--main-loop echo_loop.py` for the
echo root, then headless Chrome or Edge through `python/devtools.py`, and
opens the page. It reads `<root>/tap/typescript.tap` line by line as it
grows, through `tap_consumer.Parser.parse_line` and
`tap_consumer.StreamReader`, prints one line per rung point, and stops at
the first `not ok` or bail out, exiting 1 with the rung's name. The checks
only the Python process can make, ttyd's resident size, its exit, the
server's database files and log, it makes around the stream.

### 4.3 The rungs

Each root has its own ttyd and its own load of the page, and its gold,
`typescript.test_wire_rungs`, names the rungs it runs, in order, and their
parameters, by this schema, which the consumer writes and the producer
reads by exactly these names; handoffs 1.46.2 and 1.46.5 follow it:

```text
root            "echo", "stock" or "restart"
rungs           the rung names this run runs, in order: for echo "first",
                "echo", "control", then in a normal-test run "fit",
                "large"; for stock "first", "mcp", "commits", "verbose",
                "console", "lines", "unknown"; for restart "first",
                "restart". A
                smoke-test run leaves out the rungs labelled normal-test.
echo_payload    the payload object of the echo rung's `echo` line
control_bytes   1048576, the bytes of the control rung's one blob, byte
                i being i % 256
large_bytes     134217728, the bytes of the large rung's blob
mcp_call        {"name": "source_put", "arguments": {"name":
                "wire_tool.py", "text": <any text>}}
mcp_sha256      the SHA-256 hex of that text's UTF-8 bytes
commits         the push lines of the commits rung, in order, each
                {"type": t, "key": k, "text": x, "payload": p}, `key` the
                header's `k` when present, `text` the UTF-8 bytes of blob 1
                when present, `payload` the payload, absent when empty:
                db.create wire_commits; kv.put /wire_commits/kept "kept
                value"; kv.put /wire_commits/gone "gone value"; kv.delete
                /wire_commits/gone; doc.put {db wire_commits, id note, body
                {"0": {"t": "note"}, "text": "a note"}}; turn.append {scene
                /wire_commits/note/1, role user, content {"role": "user",
                "content": "a turn"}}; sql.run {db wire_commits, statements
                CREATE TABLE t (x INTEGER) STRICT, then INSERT INTO t
                VALUES (?) with [7]}; db.create wire_dropped; db.drop
                wire_dropped
verbose_count   10
console_size    {"columns": 80, "rows": 24}
console_prompt  "$ ", dash's prompt, which the console and lines rungs
                wait for before they type
console_typed   "exit\n", what the console rung types as one '0' message
console_last    "exit\r\n", what the console output ends with at the
                close, the terminal's echo of what was typed
lines_count     100000, the numbers the lines rung's subshell prints
lines_command   ( i=1; while [ "$i" -le 100000 ]; do echo "$i";
                i=$((i + 1)); done ), one line, the count `lines_count`
                written in
unknown_type    "wire.unknown"
restart_name    "echo_loop.py"
restart_text    the text of `python/echo_loop.py`
restart_sha256  the SHA-256 hex of that text's UTF-8 bytes
```

A rung that ends the session writes its point and closes the stream first.

On the echo root, whose server is `echo_loop.py`, which echoes `echo`
lines, appends `tap.line` as `engine_tap` does, and gives an `error` line
to `engine_tap.error_take`:

1. first: the first line was `tap.start` with `i` 101 and the test
   settings of this root.
2. echo: an `echo` line comes back equal.
3. control: an echo of one blob of `control_bytes` holding every byte
   value in turn, CR, LF, ^C, ^D, ^S and bytes invalid in UTF-8 among
   them, over `overflow_bytes`, so that both sides stream it through a
   cache file. A text of 1 MiB cannot be sent: its JSON is over
   `line_max`, and JSON escapes its control characters.
4. fit: a blob of exactly `blob_max` echoed. normal-test. Unconfirmed: that
   a `Uint8Array` of `blob_max` bytes, 2 GiB, fits in the worker, owed to
   testing.
5. large: 128 MiB as one blob echoed; then Python reads ttyd's resident
   size. normal-test.

After the stream Python kills ttyd and checks its end, as the killed rung
did.

On the stock root:

1. first, as above.
2. mcp: `initialize`, `notifications/initialized` and a `tools/call` of
   `source_put` over `mcp` lines, its result against the digest Python
   wrote into the gold.
3. commits: the push lines the gold lists, one of each commit type; after
   the stream Python opens the root's database files with `sqlite3`, read
   only, and checks the server applied each.
4. verbose: `verbose.tail` of the server's lines.
5. console: tty 0 by a `ConsolePort` the rung drives itself, its first
   message with `columns` and `rows`, `console_typed` typed once the
   output ends with `console_prompt`, and at the close the output since
   the typing ending with `console_last`, the last line read before the
   close.
6. lines, the last line regression of the console role: tty 0 by a new
   `ConsolePort`; at dash's prompt, `console_prompt`, `lines_command` is
   typed, a subshell
   that prints 1 to `lines_count`, one per line, and exits at once; the
   output must be the command's echo, every number in order, the last just
   before the subshell exited, then the prompt. smoke-test, as before.
7. unknown: its point and the end of the stream are written, then a push
   of an unknown line type is sent; Python checks that the server logged
   `dispatch.handler_unknown` and exited 1.

On the restart root, stock too:

1. first, as above.
2. restart: `source.put` of the echo main loop, its digest checked, then
   its point and the end of the stream written, as for every rung that
   ends the session, then `system.restart`. The new process's
   `tap.start` makes the page fail with `wire.start_twice`, which the
   worker reports as an `error` line; the new bootstrap reads it where it
   waits for the reply to its first line, fails with
   `bootstrap.reply_unexpected` naming it, and exits 1, so no
   `Bail out!` is written. The `error` line that bootstrap's failure
   writes, as every one does, the page no longer takes, its wire having
   faulted. Python takes as the expected end a stream that ended passing,
   then the server's log holding the text of `wire.start_twice`, its exit
   1, and the pid after the exec equal to the pid before it.

Removed: the rung of a line announcing blobs over `blob_max`, which the
page's frame queue refuses before it is sent, so only the server's decoder
tests can reach it; the rung of a second connection, which the page's wire
cannot observe without faulting, so `test_bootstrap.py`'s test of the held
lock covers it; the rungs of forwarded operations, `kv.get` and `doc.head`
round trips, whose server handlers this plan removes; the release stage,
whose root sends no gold, so the page runs nothing, the release refusals
staying covered by the unit tests of `engine_system` and `bootstrap`.

### 4.4 ttyd's protocol where the wire meets ttyd

The annotations go into `ts/wire.ts`, `ts/test_wire_rungs.ts` and the
stubs: the token from `/token`; `/ws` and `/ws?arg=console` with the
subprotocol `tty`; the first message, JSON text, on tty 1 only
`{"AuthToken": token}`, on tty 0 also `columns` and `rows`; client
messages '0', input, and '1', a resize, which the page never sends; server
messages '0' output, '1' the title and '2' the preferences; the command run
once the first message is in, and the socket ended when the command exits.
That ttyd 1.7.7 accepts a first message without a size is from memory, owed
to testing.

## 5 Errors

### 5.1 Cascades

1.14. A cascading failure is one object: an `error` line, a `fault` line and
an MCP error each hold the latest failure's `message` and `stack`, and under
`cause` the failure it arose from, nested, the first failure innermost.
The key is always the full word `cause`. TypeScript serializes an Error's
`cause` chain by `dispatch.cause_make`, a `cause` that is not an Error
written as its text with an empty stack. Python serializes `__cause__`, or
else `__context__` unless `__suppress_context__` is set, each entry's
`stack` the traceback of that exception alone,
`traceback.format_exception(error, chain=False)`. A fault met while a fault
is handled, as a `sink_close` that throws inside the decoder's
`#stream_shut`, is thrown with the first fault put under its innermost
`cause` by `utility.cause_append`, so both are reported. An `error` line
that reaches a queue stops it with `queue.error_line`, and the line's own
cascade is rebuilt under that error's `cause`, so a received cascade is
kept whole.

### 5.2 Tool errors

1.8. A tool's exception becomes a `tools/call` result with `isError` true,
whose one text content is the JSON text of the cascade, in both languages.
A protocol error, an unknown method or tool or bad params, is a JSON-RPC
error whose `data` is the cascade. Either way the request is answered first
and then the server fails, by the project's fail loud rule: the TypeScript
server's `line_handle` returns a `dispatch.Failure`, which the queue answers
and then throws; the Python `engine_mcp` returns a `dispatch.Failure`,
which the main loop writes and then raises; `mcp_stdio` writes the answer
and raises. A test driver reads `isError`, or the JSON-RPC error, to tell
an exception from the expected response. MCP is a testing protocol for now:
no AI is a requirement of the tests yet.

The TypeScript tool that submits a request and then throws: its throw
becomes the `isError` answer and a `dispatch.Failure`; the queue posts the
answer, finds the request the handler does not sleep on, and fails with
`queue.wait_missing` whose `cause` is the tool's own error, so its message
is kept and both are reported.

### 5.3 The browser's failure, when the test protocol runs from the server

1.8. The server gets the browser's exception gracefully and logs it before
the connection closes gracefully, and the TAP results are written out.

1. A fault of the AI worker reaches `error_overlay`'s report function: the
   worker sends an `error` line, the cascade by `dispatch.cause_make`, by
   `WirePort.wire_end`, which posts the line, then waits under the wire's
   drain timer for the server to end the socket, then posts the `fault`
   line to the page. The page shows it and terminates the worker.
2. A fault of the UI thread shows the fault screen, then the stop function
   posts it to the worker as a `fault` line with its cascade, which the
   worker sends on as an `error` line the same way, then closes itself.
3. The server's main loop gives an `error` line without `r` to
   `engine_tap.error_take`, which logs its message, stack and every cause,
   and appends `Bail out! <message>` to `<root>/tap/typescript.tap`, so the
   stream ends where it stands and reads as failed. The loop then exits 1
   and writes nothing back, and ttyd closes the socket as the command ends:
   the close that `wire_end` waits for.

So the server closes the connection, by its exit, once it has logged the
failure, in the order 1.8 gives, and the page never closes the socket on a
failure. ttyd 1.7.7 kills the command with its signal, SIGHUP unless set
otherwise, when the client closes first (`LWS_CALLBACK_CLOSED` in its
`src/protocol.c`), which could end the server before it has read and
logged the `error` line, and lose the diagnostics that 1.23 puts first.
Unconfirmed: that kill was read in the source of a ttyd checkout 24
commits past 1.7.7, not measured on the pinned release. Should the drain
timer expire before the close, its `wire.wait_expired` is
a fault met while a fault is reported: it is put outermost, the first fault
under its `cause`, as section 5.1 says, and the page receives that cascade.

A `Bail out!` line at depth 0 ends a stream wherever it stands, and counts
as one failure unless it follows a failed point, in `tap_consumer.py`.

### 5.4 Deferred: the MCP continuing after an exception

The ability of the MCP to continue after an exception will be enabled
later. The design is this. A new setting, `mcp_continue`, a bool, false
until the maintainer enables it. When true, an exception in a request
answers it exactly as above, and then the server goes on: `failure_take`
still returns the exception, which the transport logs with `verbose.log`,
its cascade whole, instead of failing; TypeScript's `line_handle` returns
the reply line, not a `dispatch.Failure`; `engine_mcp` returns the reply;
`mcp_stdio` writes it and reads the next line. A request that a failed
tool submitted and does not sleep on is abandoned: the queue keeps its id in
a set of abandoned ids instead of failing with `queue.wait_missing`, and
its reply, when it comes, is dropped with a verbose line naming it and its
blob bytes released. A tool's effects before its throw stay, but those of a
transaction it ran, which the throw rolled back. The AI reads `isError` and
decides what to do. The tests: a tool that throws after it submitted, then
a second call that succeeds on the same server; the late reply of the
abandoned request dropped and logged; a protocol error followed by a good
request. With `mcp_continue` false, everything stays as section 5.2 says.

## 6 The store protocol

1.7, 1.17, 1.19, 1.28 and 1.52. The databases are filesystem accelerators
that an AI talks to easily, not replicas. Normal database replication is an
anti-pattern for this product.

### 6.1 Lossy messages

Each modifying operation the browser's store commits, `db.create`,
`db.drop`, `kv.put`, `kv.delete`, `doc.put`, `turn.append` and a `sql.run`
that changed rows or the schema, goes to the server once its transaction has
committed, as one push line of the same type: no `i`, no reply. The store
gives it to `tasks.line_notify(line, "server")`; a `kv.put` carries its
value's bytes as blob 1, read out of the cache file when the value is one,
so no cache file is held for a line in flight. An operation that changes
nothing, or a rolled back transaction, sends nothing. The server applies
each line to its own store through the same methods as any caller. There is
no `seq`, no `since`, no ordering, no check of either side against the
other, no queue of lines in flight and no reply. A line lost to a
connection loss stays lost; a closed window loses what it had not sent. The
server may hold more history than the browser, and may not have received
everything in order. A line whose application fails on the server, as a
`db.create` of a database it already has, fails the server loud. The
TypeScript code is not responsible for database integrity across the wire.

### 6.2 Each store does its own maintenance

The browser's store compacts a scene's turns before it appends a `user`
turn at the threshold `turn_compact_turns`, for itself alone: nothing of the
compaction crosses the wire, and the `turn.append` it sends after is a
plain message. The server keeps every turn and never compacts. Neither store
relies on the other to hold what it dropped: the browser's tier of the cache
files of `_files`, the database of the scripts and images, which freed them
by a budget and fetched them back from the server by `kv.get`, is removed
with `files_browser_bytes`; the `_files` database stays.

### 6.3 Nothing exposes the backing store beyond routine SQL

Removed from the tools of `ts/tools_browser.ts`: `db_stats`, which measured
pages, free bytes, cache bytes and `seq`; `db_compact`, VACUUM; `db_unload`
and `db_load`, the unloading of the browser's copy and the loading of the
server's snapshot as a tool; the `seq` of the results of `sql_run`,
`kv_put` and `kv_delete`; the fetch back of a value the browser no longer
held. Removed from the agent: the measurement of the databases after each
turn against `db_soft_bytes`, which went to the provider, and the setting.
Removed from the seed's prompt, `python/seed/prompt.json`: its sentences on
`db_soft_bytes`, `db_stats`, `db_compact`, `db_unload`, `db_load`, `seq`
and the databases the browser has loaded or must keep loaded, and the
exceptions of `engine.store` for `db_stats` and `db_load`, so that the
prompt names only the tools that stay. Removed from the wire: `kv.get`,
`kv.list`, `doc.head` and `db.snapshot` as server requests, and
`turn.compact`, `SeqReply`, `since`, `seq` and `hello.seq`. Removed from
the stores: `operation_apply`, `forward_set`, `forward_done`, `seq_get`,
`start_open`, `db_stats`, `db_compact`, `db_unload`, `db_load`, `kv_held`,
`cache_fill`, `cache_evict`, the `_meta` row `seq`, every desync check,
and the worker's replication queue, `ForwardQueue`, `ServerHold` and the
`replicate.*` lines. Kept, as routine:
`sql_run`, `db_create`, `db_drop`, the `kv_*` and `doc_*` tools, whose
results name values, never storage.

The AI's scripts reach the store as `engine.store`, which holds the
routine methods only, bound to the store and frozen: `sql_run`, `db_list`,
`db_create`, `db_drop`, `kv_get`, `kv_put`, `kv_delete`, `kv_list`,
`doc_get`, `doc_put`, `doc_head`, `turn_append`, `turn_list`,
`turn_compact` and `transaction_run`, the traced form of `script_debug`
wrapping the same object. Removed from the scripts' `engine.store`:
`db_open`, `db_close`, `kv_check`, `db_snapshot`, `db_restore`, `sink` and
`handlers_register`, the store's own machinery. 1.28 requires it, so the
rule that nothing refuses the AI access to the databases unless the
maintainer requires it holds, and every database stays readable and
writable whole through the routine methods.

### 6.4 Whole databases as blobs

1.16. A database moves only whole, as blobs. `db.restore`, SERVER to AI,
carries the database file as blob 1 and `files`, the count of cache files
that follow; then come `files` lines of `db.file`, each with one cache file
as blob 1. The sender writes them in order:
`engine_db.restore_lines(db, full)`, `full` the server's `debug` setting,
yields them from `Store.db_snapshot(db)`, whose `files` are the cache files
the rows name and the sender holds, a lost one left out. The receiver keeps
the `db.restore` until its `files` lines are in, then calls
`Store.db_restore(db, data, files)`, which replaces the database file and
places each file in its cache under the digest of its own bytes. A second
`db.restore` while one waits, or a `db.file` with none waiting, fails loud.
Python's `db_restore(db, data, files)` is the twin of the browser's.

Each message is at most `line_max` plus `blob_max` bytes, `blob_max` being
the largest database, so a cache file, a value over `overflow_bytes` or the
blob of a `db.file`, is at most `blob_max` too.

The tolerance of lost cache files: a row that names a cache file its store
does not hold stays; `kv_list` lists it, `kv_put` replaces it, `kv_check`
counts nothing for it, and `kv_get` fails loud with `substrate.file_lost`,
naming the ref and the digest. A restored database without some of its
cache files works but for those values. The test, in both languages: a store
with a database holding two values over `overflow_bytes` and one under it;
its snapshot with one of the two cache files dropped; a second store,
under its own root, restores it; the value whose file came reads its bytes,
the small one reads its bytes, the lost one raises `substrate.file_lost`,
`kv_list` lists all three with their sizes and digests, `kv_put` over the
lost ref succeeds and reads back, and `kv_check` returns 0. And on the
sending side: a snapshot of a database one of whose cache files was deleted
lists only the files that exist, without raising.

### 6.5 Another backing store

The protocol names operations, never the storage: refs, documents, turns,
SQL statements as text, and whole databases as opaque blobs. Replacing the
database with another kind of backing store changes no line type and no
payload. Unconfirmed: SQL is the AI's routine query language, so another
backing store must accept the same SQL statements, and both stores must use
the same kind for a `db.restore` blob to be read; the protocol does not
change either way.

## 7 Limits

1.5. No setting was a hard bound of a database's size, but `blob_max`, the
bound of the blob bytes of one message, which the tests already called the
largest database. `blob_max`, 2147483391 bytes, is the largest database,
named so in the settings' stubs, and every limit is set so that a database
of that size is backed up as a single blob:

- A message's blobs come to at most `blob_max`: a database file is the one
  blob of its `db.restore`.
- A cache file is at most `blob_max`: a value over `overflow_bytes` is the
  one blob of its `kv.put`, and a `db.file`'s blob is one cache file.
- The queue of each thread and the wire's frame queue bound the blob bytes
  they hold by `blob_max`, and a held line counts only the blobs it holds in
  memory, `queue.line_bytes`: a blob streamed to a cache file, over
  `overflow_bytes`, counts nothing. So a database of `blob_max` and its
  cache files pass through one after another. Before, every blob counted,
  so a `db.restore` and a `db.file` in the queue together could pass the
  bound.
- `line_max`, 1 MiB, bounds the JSON text of a line, which a database line
  never comes near, and a verbose entry: a `verbose.put` holding one entry
  stays below it.
- A wire line whose rendering would not fit its verbose entry, by
  `queue.entry_fits`, is logged by the worker's `WireTap` as its header and
  the sizes of its payload and blobs only: `> <header 0> with a payload of
  P bytes and blobs of [s1, s2] bytes`. A rendering that fits is logged as
  before. A legal line so never stops the worker with `queue.entry_over`.
- `first_line_max`, 10 MiB, in `ts/wire.ts`, bounds the first line, read
  before the settings exist.
- `chunk_bytes` and `srv_buf_size` stay 1 MiB: they cut a message into
  frames and reads, and bound nothing whole.
- `overflow_bytes`, 128 KiB, is the size past which a value or a blob
  streams to a cache file, and `media_db_bytes`, 256 MiB, the budget of the
  UI thread's decoded images in memory. Neither bounds a database, and both
  stay.

The value of `blob_max` is kept. Unconfirmed: that the browser can hold a
`kv.put` of a value near `blob_max` in memory, as section 6.1 reads it out
of its cache file, and restore a `db.restore` of a database near
`blob_max` into its pool; that is owed to testing.

## 8 Bad numbers

1.13, 1.18 and 1.53. The JSLB decoders of both languages are the single
door for bad numbers, and no other layer checks a number. At read a decoder
refuses an integer token, digits with no fraction and no exponent, beyond
2^53 either way, with `jslb.integer_refused`; TypeScript compares the
token's text by `BigInt`, Python refuses a token of more than 16 digits
before `int` reads it, which also covers the 310 to 4300 digit integers,
and compares a shorter one after.
It refuses a number token whose double overflows to an infinity, as
`1e400`, with the new `jslb.number_overflow`. Both raise `WireError`. A
token with a fraction or an exponent within the doubles reads as its double.
TypeScript finds the tokens by scanning the text `JSON.parse` accepted,
strings skipped, for number tokens. `jslb.json_decode` applies the same rules
to JSON read from anywhere but a line: `mcp_stdio`'s input lines, the
settings files the server reads and the seed documents of its main loop,
the provider's HTTP replies and their tool call arguments, and ttyd's
token answer and preferences. The provider script's JSON in `_files` is
read the same way once the deferred program reads it again: while only the
test suites run no module reads it, `worker_ai`'s `script_read` going with
the start. A text that is not JSON it refuses with `jslb.text_not_json`,
which names no line. The encoders keep their refusal of NaN, the
infinities and, in Python, integers beyond 2^53, inside the same layer.

The number checks outside the JSLB layer that wave 2 removes:

1. `ts/utility.ts`: the replacer of `json_text` and `utility.number_refused`.
2. `ts/substrate.ts`: `json_canonical`'s `substrate.number_refused` and
   `substrate.integer_range`, and `constants.integer_limit`.
3. `python/substrate.py`: `_json_ordered`'s `substrate.integer_range` and
   `substrate.number_refused`, `_INTEGER_LIMIT`, and `allow_nan=False` in
   `_json_canonical`.
4. `python/engine_turn.py`: `allow_nan=False` in its canonical JSON.
5. `python/main_loop.py`: `allow_nan=False` in `_json_text`.
6. `python/mcp_stdio.py`: `allow_nan=False` in `_text_make`.
7. `python/vectors_make.py`: `allow_nan=False` in the sidecar it writes.
8. `ts/media.ts`, `ts/http.ts` and `ts/wire.ts`: the `Number.isFinite` part
   of the checks of a budget and of timeouts; their ranges stay.
9. `ts/provider_script.ts`: `Number.isSafeInteger` of the image count,
   which becomes `Number.isInteger`.

Checks that a count is a whole number from 0 up, a header's sizes inside
the JSLB layer, an MCP id's type and the like are checks of a value's
domain, not of a bad number, and stay. Unconfirmed: that reading of "bad
number" is the maintainer's.

A document version past 2^53 is the AI's problem over the MCP: nothing
checks a version, and a version the store cannot hold exactly is for the AI
to notice and resolve.

## 9 The smaller items

### 9.1 console.show

1.6. `console.show`, ui-ai, AI to UI, no blob, reply Empty: the UI thread
shows the console view as ctrl 0 does and answers once tty 0 is open, at
once when `open_is()`, else through `open_request()`, its wake
`ui.console_shown` running `open_done` and replying. `console_run` asks the
permit, then submits `console.show` and sleeps on `tools.show_reply`, then
types the command. `page.console_busy` is thrown when the view is opening
or closing, neither idle nor open, so it can be neither answered nor asked
for tty 0; its text names both phases, since the view has no member that
tells them apart.

### 9.2 The xterm options and the resize path

1.30. `resize_send`, the terminal's `onResize` listener and their tests go,
and the rung that checked `stty size` after a refit. The first message of
tty 0 carries the size the view fits at its show; a later fit changes only
the terminal on the page, which is debug only. The options
`{cols, rows, disableStdin}` were checked against xterm 5.5.0's typings:
`cols` and `rows` are in `ITerminalInitOnlyOptions`, `disableStdin` in
`ITerminalOptions`, the constructor takes both, and `options.disableStdin`
can be set at run time. The typings are not in the tree; they were found in
`node_modules/@xterm/xterm` of a ttyd source checkout beside it, package
version 5.5.0.

### 9.3 Name forms

1.31. `settings.names_full()` is the one choice: true until the settings
are set, then the setting `debug`. Code that runs before the settings exist
uses the full names: the error overlay's `fault` line always. The five
places of 1.31 follow it: the nine line types of `ts/tools_browser.ts`,
`http.request` in `post_make` of `ts/provider.ts`, `ConsolePort` of
`ts/wire.ts`, which no longer reads `debug` itself, `ui.input` and
`ui.control_key` of the DOM port, and the worker's `fault` line. Three more
were found: `ts/console_view.ts`, which always built full names, the wake
lines of `ts/queue.ts`, always short, and the `error` line that
`dispatch.error_make` builds when it answers no line, always short.

### 9.4 Ambiguous content

1.12. `agent.content_ambiguous` is thrown before ambiguous content is
added: two triggers of `universe`, in API/sql/metaverse.sql, refuse an
insert or an update that would make a second row name a world, by
`RAISE(ABORT, 'agent.content_ambiguous')`. Each store throws, for a failed
statement whose SQLite message ends with the name of a string it lists,
that string, the SQLite error as its cause. So the refusal holds in both
stores, for the AI's SQL tool, its scripts, the UI's tasks and the server's
application of the browser's commits. `agent.universe_ambiguous` and its
check at the next turn go. Content like it is refused the same way: a
trigger raising the name of its string. Built by 1.46.4 and 1.46.1, the
throws, and 1.46.2, the DDL the server seeds. Unconfirmed: that the message
of sqlite3.wasm's error ends with the trigger's text, owed to testing.

### 9.5 Small stub additions

1.32. `utility.HashStream`, the one `SHA-256`, which `sha256_hex` and the
store's cache use, the copy in `ts/substrate.ts` removed. `queue.line_bytes`
exported, the copy in `ts/worker_ai.ts` removed with the replication queue.
`provider.key_clear()` for the tests. The built additions of `queue.d.ts`,
`unittest.d.ts` and `tap_producer.d.ts`, written as the code has them. And
`self.name` is "" on the main thread.

### 9.6 The PowerShell constants

1.39. Every constant of the PowerShell scripts is a setting. Those of the
install, start, status and stop scripts and of `xsjs_util.ps1` are under
`powershell` in `settings.json`, with `provider.variable` for the provider
key's variable; the ttyd `--srv-buf-size` reads `srv_buf_size`. Those of
`test_powershell.ps1` and `test_lint.ps1` are test suite settings, under
`powershell` in `test_settings.json`. What stays in the scripts: syntax,
that is cmdlet parameters, the names of the commands run and their flags,
the apt packages named for the command they install, registry paths,
Windows' own paths and environment variables, encodings, colours, formats,
patterns, the task's and the firewall rule's attributes and the log's
markup; the banner; what is read before the settings, the dot-sourced
`xsjs_util.ps1`, the strings file and the names of the two settings files;
the checkout's layout that other modules fix, such as `python/`,
`i18n/en-US.json` and `build/`, and the layout inside `ttyd_build`; the
addresses that define the localhost and HTTPS modes and the certificate's
localhost names; the lifecycle table of `test_powershell.ps1`; and the
install of PSScriptAnalyzer that 1.38 keeps as built. Only
`test_powershell.ps1` and `test_lint.ps1` read `test_settings.json`.

## 10 What wave 2 builds

The handoffs in `tmp/handoff_23_0919/` hold each package's exact changes.

- 1.46.1, the Python store: the lossy store, `db_snapshot` and `db_restore`
  with files, `substrate.file_lost`, the trigger names, the push handlers,
  `restore_lines`.
- 1.46.2, the Python bring up: `tap.start` with id 101 and the test
  settings, `dispatch.id_next` from 102, the main loop's handling of the
  browser's `error`, `engine_tap.error_take`, the settings types, the
  harness with `settings_copy` and `gold_copy`, `page_build` of one page,
  the TAP consumer's stream reader and
  bail out rule, the order of `test_all.py`, the wire test as the consumer.
- 1.46.3, the Python MCP and browser test: `isError` and `failure_take`,
  `engine_mcp` and `mcp_stdio` failing after the answer, the echo loop's
  `tap.line` and `error`, the browser test's rungs reduced to the bring up
  page.
- 1.46.4, the TypeScript store and worker: the lossy store and its pushes,
  the removed tools, `console.show` in `console_run`, the worker's bring
  up, the `WireTap` rule.
- 1.46.5, the TypeScript UI and wire: the removed pages and entries, the
  first line, `wire_end`, the fault paths, `console.show` on the page,
  `open_is`, `resize_send` gone, `names_full()` in `settings`, the agent's
  removals, the TypeScript run order, the wire rungs producer.
- 1.46.6, TypeScript core and JSLB in both languages: the decoders' number
  rules and `json_decode`, cascades, `dispatch.Failure`, the queue's bound
  and `entry_fits`, `utility.HashStream`, the harness, the MCP server's
  failures.
- 1.46.7, PowerShell: the settings reader and every constant read from the
  settings files.

## 11 How the bring up will be run later

Nothing runs now. Later, after the maintainer's review of the unstaged
changes:

1. `python3 python/page_build.py hyperposition-engine` builds the page.
2. `./test_posix.sh` runs `python3 python/test_all.py --smoke-test`, or
   `--normal-test`: the Python suites in the order of section 3.3, the
   checks of `test_posix.py`, the wire test and the browser test. On
   Windows, `powershell/test_powershell.ps1` runs the same inside WSL.
3. By hand: `.\xsjs_start.ps1`, then `http://localhost:5768/`; the page runs
   the TypeScript suites and shows the UI thread's stream in `#tap_output`,
   and the server writes both threads' streams, one after the other, to
   `~/.cache/xsjs/tap/typescript.tap`.

## 12 Requirements

Every requirement of the items this plan answers, by class: A unsatisfied
or modified without cause, B unsatisfied or modified with cause but without
confirmation, C confirmed withdrawn or modified, D satisfied without
modification or withdrawal. No requirement is class A or C.

### 12.1 Class D

1. 1.5: a line whose rendering would not fit its verbose entry is logged as
   its header and the sizes of its payload and blobs only.
2. 1.6: `console.show` shows the console view as ctrl 0 does and replies
   once tty 0 is open; `open_is()`; `page.console_busy` exists.
3. 1.7: explicit incremental synchronization removed; entire databases sync
   as blobs; the sync is lossy; the server may have more history and an
   unordered one; replication specific techniques removed.
4. 1.8: tool errors are `isError` results with message and stack in both
   languages; the server does not continue after one; the driver tells an
   exception from an expected response; the later continuation is designed
   beside its deferral.
5. 1.9: `dispatch.id_next` starts at 102 in both languages, 101 left to
   the first line.
6. 1.13: both decoders refuse an overflowing token at read, with a new
   `jslb.` name; the decoders are the single door.
7. 1.14: cascades are nested `cause` entries in one JSLB object, always the
   full key `cause`; the docs say so.
8. 1.16: `db_restore(db, data, files)`; the cache files in JSLB lines after
   the database's line; the message and overflow file sizes from the
   largest database; lost cache files tolerated and the test of it written.
9. 1.17: `seq` and its checks replaced by the lossy scheme; the TypeScript
   code is not responsible for integrity across the wire.
10. 1.18: a document version past 2^53 is the AI's problem over the MCP.
11. 1.19: no compaction relationship between two databases.
12. 1.20: the hello example ripped out; TAP over the wire planned; test
   suites everywhere.
13. 1.26: the testing order from the TAP producer and consumer up the DAG;
   TAP runs the server's and the app's bring up; the later bring up
   question left for later.
14. 1.27: ttyd protocol annotations; the remark about the first message
   kept word for word.
15. 1.28: each store does its own maintenance; exposure of the store beyond
   routine SQL removed, the seed's prompt included; a message based
   protocol.
16. 1.30: `resize_send` and its tests deleted; the xterm options checked
   against the 5.5.0 typings.
17. 1.31: code before the settings uses long names; the five places follow
   `names_full()`.
18. 1.32: every listed stub addition.
19. 1.34: the gold record; values derived from either file allowed; no
   `settings.json` derivative copied.
20. 1.39: `--srv-buf-size` reads `srv_buf_size`; PowerShell reads the
   settings file, written in handoff 1.46.7.

### 12.2 Class B

Each was satisfied by the reading closest to the words, as explained, and
waits for the maintainer's confirmation. Only points 25 and 107 need a
choice of the maintainer, a multiple choice question written in each, to
satisfy all requirements together. Points 35 on are the class B decisions
of the review of step 2.3 and of the integration of step 2.11, one point
each, naming the progress file under `tmp/handoff_23_0919/` that gives its
reason.

1. 1.5, the largest database: no setting was a hard bound of a database's
   size, so `blob_max`, the bound of one message's blobs and already called
   the largest database by the tests, was named the largest database rather
   than adding a setting of the same value.
2. 1.5, the limits: the queues count only the blob bytes held in memory, so
   a database and its cache files streamed one after another never pass the
   bound; no value changed.
3. 1.6, `page.console_busy`: its purpose was chosen as the refusal of a
   `console.show` that finds the view opening or closing.
4. 1.7 and 1.28, another backing store: SQL text stays in the protocol as
   the AI's routine queries, so another store must accept the same SQL.
5. 1.7 and 1.28, the `_files` tier: the browser's eviction of cache files
   by budget and their fetch back from the server relied on the server
   holding them and checked the bytes against the browser's rows, a
   relationship between two databases; it is removed with
   `files_browser_bytes`, and `db_soft_bytes` with the measurement that
   read it.
6. 1.7, the server's read requests: `kv.get`, `kv.list`, `doc.head` and
   `db.snapshot` lose their server handlers, since their only callers were
   the removed tier, start chain and `db_load`.
7. 1.8, the server side: the browser's failure reaches the server as an
   `error` line, the UI's through the worker; the server logs it, ends the
   TAP file with `Bail out!` and exits 1 without an answer, which closes the
   connection; the page waits for that close and never closes first, since
   ttyd kills the server when the client closes, as section 5.3 says.
8. 1.8, protocol errors: an exception of any request, a protocol error
   included, answers and then stops the server.
9. 1.8, the tool that submits and throws: the queue fails with
   `queue.wait_missing` whose `cause` is the tool's error, the latest
   failure outermost, as JavaScript's and Python's chains order them.
10. 1.12: the refusal is two triggers of `universe` raising the string's
   name, which each store throws as that string, rather than a check in the
   agent, which no write passes through.
11. 1.13 and 1.53, the integer range: the decoders refuse integer tokens
   beyond 2^53; a token with a fraction or an exponent is a double both
   languages hold alike and passes, which the TypeScript store refused
   before and the Python one did not.
12. 1.13, `jslb.json_decode`: JSON read from outside a line passes the same
   door, so the single door holds for stdio, files and HTTP.
13. 1.18 and 1.53: the encoders' refusals of NaN and the infinities stay,
   inside the JSLB layer; the domain checks of counts and timeouts stay.
14. 1.17, the planned recovery: designed in full, deferred to the real
   program, since no program runs at bring up.
15. 1.20 and 1.51, no example program: the engine page, the test engine
   page and the program's assembly are removed, by 1.20's "no other
   programs" and 1.26's later app bring up, as section 1 says; the
   program's modules and the metaverse seed kept; outside debug mode the
   page runs nothing, since 1.34 sends the gold in debug mode only. With
   the test engine page goes wave 1's answer to 1.3, its `prettier-ignore`
   line, and with both templates the comment 1.41 shortened in them.
16. 1.20 and 1.51, the provider: designed in full as `provider.set`,
   deferred.
17. 1.26, calling back: no import cycle exists; the run time callbacks are
   listed as findings, not changed, read as section 3.2 says; the
   TypeScript worker's suites now run before the UI thread's, as the DAG
   asks, `error_overlay`'s tests in both streams and `boot`'s last.
18. 1.27, the producer: the rungs are task chains writing TAP with a
   `Tracker`, since `unittest` is synchronous; the rungs a page cannot
   observe moved to Python checks or were removed, as section 4.3 says, and
   the session ending rungs got their own roots; the console role's last
   line regression, which the page can observe, stays as the rung "lines".
19. 1.30, the remaining issue: a refit after tty 0 opened no longer reaches
   the pty, accepted as debug only.
20. 1.31, beyond the five places: `console_view.ts` and the queue's wake
   lines follow `names_full()` too, which moved into `settings` so that no
   cycle forms.
21. 1.32, `queue.line_bytes`: it counts the blobs held in memory, the bound
   of section 7.
22. 1.34, what moves now: the infrastructure's deadlines, `long_task_ms`
   and the PowerShell tests' constants; every test module's values move in
   wave 3.
23. 1.34, the test settings in `tap.start`: one line, `test_settings` the
   field right after `settings`.
24. 1.34, the harness: a new module in each language, and in Python too a
   test module imports no `i18n`, its texts coming from the gold record,
   as 1.34 lists `i18n` among the TypeScript imports to remove.
25. 1.39, the PowerShell constants: the test scripts' constants went into
   `test_settings.json`, by 1.34's rule for test suite settings, and the
   selection of what is a constant is section 9.6's. The project's rule
   "PowerShell constants go in `settings.json`." disagrees, and only the
   maintainer changes it. The question: (a) the plan stands, and the rule
   gains, for example, "PowerShell constants go in `settings.json`, those
   of the PowerShell tests in `test_settings.json`."; or (b) the five keys
   of `powershell` in `test_settings.json` move under `powershell` in
   `settings.json`, and the two test scripts read them there.
26. 1.2 and 1.55, all docs: `README.md`, `API/README.md` and this plan say
   no code was written by the maintainer, as the project rules do; "all docs"
   read as the documents checked in that describe the project.
27. 1.7, 1.17 and 1.52, the lossy messages: each commit of the browser's
   store goes to the server as a push of the same type, never answered,
   nothing ordering or checking it, and a line the server cannot apply
   fails the server loud; read as the lossy sync 1.7 allows beside whole
   blobs, not as the explicit incremental synchronization it removes.
28. 1.28, the app working when the databases are removed: the protocol
   names operations, never storage (section 6.5), a lost cache file is
   tolerated (section 6.4), and a browser whose databases are removed gets
   them back from the server by the recovery of section 1.4, designed in
   full and deferred to the real program; at bring up the test pool is
   cleared at every start and nothing relies on an earlier window.
29. 1.8, `wire_end` on a socket already closed calls back at once, so the
   fault still reaches the page when the server ended first.
30. 1.8, the TAP consumer: a `Bail out!` at depth 0 ends a stream wherever
   it stands and counts one failure unless it follows a failed point.
31. 1.14 and 1.31, bootstrap's `error` line: in full names always, its
   cascade serialized by its own copy of the rule, since bootstrap may not
   import `dispatch` and may write before the settings exist.
32. 1.34 and 1.13, the Python harness: it reads its two files with the
   standard library's `json`, not `jslb.json_decode`, since it imports no
   module of the project, as section 2.3 says.
33. 1.17, the `_meta` row `seq`: no longer written, the schema version
   staying 1, an older file's `seq` row left unread.
34. 1.28, the scripts' store: `engine.store` holds the routine methods only,
   as section 6.3 lists them, by 1.28's "Exposing the existence of the DB
   beyond routine SQL queries is an API violation", the maintainer's own
   requirement, which the rule against refusing the AI access to the
   databases defers to; every database stays readable and writable whole.
35. 1.20 and 1.27, `lines.d.ts` (2.3.1, B 7): `TapLine.language` and
   `Fault.thread` narrowed to the values a producer exists for.
36. 1.20, `README.md` (2.3.1, B 8): the start script's bullet names what
   the plan's start script copies.
37. 1.34, `test_settings.json` (2.3.1, B 9): its keys sorted, by the wave
   3 rule.
38. 1.17, `seq` in other tests (2.3.2, B 1): a test that asserts `seq`
   along the way stays, the assertion replaced by what it stood for.
39. 1.16, `test_chunk_unknown` (2.3.2, B 2): it goes with the
   `db.snapshot` tests, as it tests the removed snapshot's form.
40. 1.5 and 1.16, `test_lines_restored` (2.3.2, B 3): it replaces
   `test_blob_streamed` and `test_past_window`, so both items keep a
   Python test.
41. 1.31, Python's `dispatch.error_make(line, error, full)` (2.3.3, B 1):
   the caller passes its `debug`, Python having no `names_full()`.
42. 1.26, `API/python/tap_consumer.pyi` (2.3.3, B 2): it follows the code,
   `category` and `Plan.skip` dropped, `depth` added.
43. 1.8, a `Failure`'s `error` line (2.3.3, B 3): it has no `r`, its
   request being answered and the failure the server's own.
44. 1.8, `engine_tap.error_take` (2.3.3, B 5): the message's text and the
   stack are two log calls per entry.
45. 1.27 and 1.39, `python/test_wire.py` (2.3.3, B 6): it reads the
   runtime modules, bind address and terminal type from the settings,
   drops the provider's environment and names its page `test_wire`.
46. 1.20, `_provider_seed` (2.3.3, B 7): kept and named in
   `main_loop.pyi`, as section 1.2 keeps the program's modules and seed.
47. 1.7, a push that carries `i` (2.3.3, section 3 point 1): left as it
   is, `dispatch.line_dispatch` refusing it only after its handler applied
   it, the failure still loud and first. The deferred design:
   `handler_register(type, version, fn, push: bool)`, the flag from the
   reply column of `API/ts/lines.d.ts`; `line_dispatch` refuses before the
   call a push with `i`, `dispatch.push_identified` "The push line of type
   {0} version {1} carries the id {2}.", and a request without `i`,
   `dispatch.request_unidentified` "The request line of type {0} version
   {1} carries no id."; `notification_replied` and `request_unanswered`
   stay for a handler that returns against its flag; every
   `handlers_register` passes the flag; the same in `ts/dispatch.ts`.
48. 1.8, a tool's exception (2.3.4, B 1): every one, an `RpcError` it
   raises included, is an `isError` result.
49. 1.8 and 1.20, `rung_thrown` (2.3.4, B 3): it carries the fault
   report's checks, and `rung_page_thrown` is merged into it.
50. 1.8, the fault rungs (2.3.4, B 4): each waits for both TAP streams of
   a new load before it faults, so that the fault reaches the server.
51. 1.20, `rung_gating` (2.3.4, B 5): it becomes "release runs nothing",
   the one page with `debug` false.
52. 1.20 and 1.27, the browser rungs the wire test runs (2.3.4, B 6):
   removed, not kept twice.
53. 1.20, the moved browser rungs (2.3.4, B 7): to the `suites`, `probe`
   and `faults` roots of the one page, a rung moved when the one page loads
   the module it tests and removed otherwise.
54. 1.20, `rung_worker_hang` (2.3.4, B 8): it stays, its documents' roles
   swapped by the new order.
55. 1.26, `rung_suites_order` (2.3.4, B 9): it checks the two lists of
   section 3.4 in full, as constants of the driver.
56. 1.8, the echo loop's `error` path (2.3.4, B 10): it stays whatever the
   restart rung's end, as section 5.3 holds for every server.
57. 1.8, 1.20 and 1.27, Python stub additions (2.3.4, B 11):
   `engine_verbose.handlers_register`, `devtools.Browser`'s constructor
   and context manager and `mcp_stdio.stdio_run`, the code's own.
58. 1.8, `mcp_stdio.pyi`'s `register` (2.3.4, B 12): typed
   `Callable[[mcp.Server], None]`, the code keeping wave 1's `Any`.
59. 1.8 and 1.34, `test_echo_loop.py` (2.3.4, B 13): it checks the
   browser's `error` line by a patch of `echo_loop.engine_tap.error_take`.
60. 1.6 and 1.20, the worker's register functions (2.3.5, B 2):
   `settings_register`, `console_register` and `note_make` stay exported.
61. 1.8, `tap_start`'s fault pieces (2.3.5, B 3): exported for their unit
   tests, `tap_start` itself tested by the bring up.
62. 1.31, the worker's relayed copies (2.3.5, B 4): `console.open` and
   `settings.put` take `settings.names_full()`, not the UI line's form.
63. 1.7 and 1.52, `db.create` and `db.drop` (2.3.5, B 6): pushed at once,
   a file operation being committed when done.
64. 1.16, a stray `db.file` (2.3.5, B 7): one of another database than the
   waiting restore is refused with `substrate.file_unexpected`.
65. 1.6, `page.console_busy` (2.3.6, B 1): it names no phase, since 1.6
   lists `open_is()` as the view's one addition.
66. 1.27, `boot.TestStart` (2.3.6, B 2): passed to `run`, giving the wire
   rungs the first line and the page's address.
67. 1.8, the main thread's faults (2.3.6, B 3): each one the overlay
   catches, a resource load failure included, runs the stop function.
68. 1.27, the control rung (2.3.6, B 4): one blob of every byte value, the
   closest working form of "every control character" within `line_max`.
69. 1.27, the restart rung (2.3.6, B 5): it ends the stream before
   `system.restart`, by section 4.3's rule for a rung ending the session.
70. 1.27, the console and lines rungs (2.3.6, B 6): they drive their own
   `ConsolePort` outside the queue, bounded by Python's rung timer.
71. 1.27, a failed rung (2.3.6, B 7): reported in the stream, `not ok` then
   `Bail out!`, not thrown, so the server writes no second `Bail out!`.
72. 1.20, the compiler options (2.3.6, B 8): `ts/tsconfig.json` keeps the
   shared ones and `ts/tsconfig.test.json` extends it.
73. 1.8 and 1.14, the fault screen (2.3.6, B 9): it shows each cause after
   the stack.
74. 1.13 and 1.53, `NaN` and `Infinity` (2.3.6, B 10): their cases in
   `test_http.ts` and `test_script.ts` change to what the code then does.
75. 1.7 and 1.52, `jslb.blob_make` (2.3.7, B 1): bytes only, its cache
   handle form gone with the forwarding.
76. 1.31, TypeScript's `dispatch.error_make` without a line (2.3.7, B 2):
   it takes `settings.names_full()`, so `dispatch` depends on `settings`.
77. 1.14, the Python twin (2.3.7, B 3): built in `python/jslb.py` too,
   though 1.14 names only `ts/jslb.ts`.
78. 1.13, `jslb.text_not_json` (2.3.7, B 4): the new key of
   `json_decode`, which reads no line.
79. 1.14, a received `error` line (2.3.7, B 5): its cascade rebuilt under
   the queue's error by a function private to `ts/queue.ts`.
80. 1.13, a text both malformed and holding a bad number (2.3.7, B 6):
   TypeScript names it not JSON and Python the number, both refusing it.
   The deferred design that makes them agree: Python's hooks record the
   first bad token and return a placeholder, and `json.loads` returning
   raises it.
81. 1.13, the vectors' `_LINE_MAX` (2.3.7, B 7): raised to 8192 rather
   than limits per vector.
82. 1.7, two vectors' `since=5` (2.3.7, B 8): it becomes `number=5`.
83. 1.22, `python/test_vectors_make.py` (2.3.7, B 9): taken into 1.46.6
   with `python/vectors_make.py`.
84. 1.18, the TypeScript encoder (2.3.7, B 10): it still writes a number
   between 2^53 and 1e21 as digits, which both decoders refuse at read.
85. 1.8, a message that is not a JSON-RPC 2.0 request (2.3.7, B 11, and
   2.3.4, B 2): answered -32600 with no exception, in both languages.
86. 1.13, the integer at the bound (2.3.7, B 12): 9007199254740992 stays
   the one success vector, none added.
87. 1.39, what stays in the PowerShell scripts (2.3.8, B 1): section 9.6's
   list, "PS constants" read as named values, not syntax.
88. 1.34 and 1.39, `test_settings.json` in PowerShell (2.3.8, B 3): read
   by the two test scripts only, not by `xsjs_util.ps1`.
89. 1.13 and 1.39, the PowerShell settings reader (2.3.8, B 4): it refuses
   an unknown id and checks no type and no number.
90. 1.23, `xsjs_util_get_command_text` (2.3.8, B 5): fixed by private
   locals and `$args[0]`.
91. 1.39, the PowerShell strings (2.3.8, B 6): `ubuntu_not_working`
   renamed `distribution_not_ready`, a repeated setting an argument.
92. 1.34, the drivers' imports (2.3.9, B 1): `test_all.py` imports the
   drivers it runs and `test_posix.py` `reformat`, section 2.4 rule 1.
93. 1.34, the Python seam (2.3.9, B 2): an attribute patched through the
   module under test's name, or `sys.modules`, section 2.4 rule 3.
94. 1.34, a handler module's test (2.3.9, B 3): it checks the None return
   in place of `dispatch.request_unanswered`, dispatch's own rule.
95. 1.34, the engine tests (2.3.9, B 4): they take a store double and check
   the handler's calls, the store's effects being `test_substrate.py`'s.
96. 1.34, `i18n` texts in the gold (2.3.9, B 5): literal arguments
   substituted, a run time one left its placeholder.
97. 1.34, the vectors in wave 3 (2.3.9, B 6): `python/vectors_make.py` and
   `python/test_vectors_make.py` are 1.47.2's alone.
98. 1.34, `page_build`'s archive names (2.3.9, B 7): one gold entry, checked
   from `test_third_party_fetch.py` and `test_page_build.py`.
99. 1.34, the wire rungs' fixed values (2.3.9, B 8): in
   `python.test_wire.rungs`, copied into each root's
   `typescript.test_wire_rungs`.
100. 1.34, a test suite setting (2.3.9, B 9): a constant that tunes how the
   suite runs, not data it checks with.
101. 1.34, the gold's layout (2.3.9, B 10): `texts`, `lines` and named
   values per module, no name holding `.`.
102. 1.34, the TypeScript digests (2.3.9, B 11): from the vector
   `test_digests.json`, input and digest in one record.
103. 1.34, the TypeScript drivers (2.3.9, B 12): they keep their references
   to the modules they run through.
104. 1.34, `test_vectors` (2.3.9, B 13): it stays a test page global beside
   `test_sqlite3` and `test_pool`.
105. 1.26, the DAG row of `test_wire_rungs` (2.11, B 1): it keeps `queue`
   as handoff 1.46.5's producer declares it.
106. 1.27, the restart rung (2.11, B 2): section 4.3 says the page does not
   take the `error` line the failing bootstrap writes.
107. 1.20 and 1.41, `python/bootstrap.html` (2.3.3, section 7 point 1): it
   stays unchanged, a page of its own that `python/xsjs_screenshot.py`
   drives outside the TAP run, by 1.41's "`python/bootstrap.html` stays".
   The question: (a) both stay, 1.41 governing; or (b) both go, by 1.20's
   "no other programs".
