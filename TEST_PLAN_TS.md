# TEST_PLAN_TS

The execution plan for testing the TypeScript modules of `ts/` in strict
dependency order, with no mock test objects, in three groups: A, the blocks
the TypeScript toolchain runs in Node; B, the blocks run in headless Chrome
with no ttyd and no tty; C, what lies past the limit of B, where planning
stops. Most tests take the shape the maintainer set on 2026-10-28: a TAP
test producer sends JSLB lines straight to the module under test, compares
the JSLB lines that come back with expected lines, and reports to a TAP
consumer.

Tasks 5.2, 5.3, 5.4, 5.8, 5.9 and 5.10 were done on 2026-10-29, while the
agents of `PY_GOALPOSTS.md` ran its wave 3. On 2026-10-30 the maintainer
answered Questions T1 to T5, which did 5.1. Section 8 gives what is done
and what follows. "Question Tn" names a question of section 9; the T keeps
them apart from the numbers of `PY_GOALPOSTS.md`.

Section 1 lists what will be accomplished; section 2 reviews the TS tests
as they are; section 3 the decisions; section 4 the rules; section 5 group
A; section 6 group B; section 7 group C; section 8 the order; section 9 the
questions; section 10 what is left out; section 11 the requirements
analysis.

## 1 What will be accomplished, in order of importance

- Every TS test runs from the official targets: `python3
  python/test_all.py` runs each TS block as a block of its one TAP stream,
  every line read by the Python TAP consumer as it arrives (3.4, Question
  T2). Tasks 5.7 and 6.3.
- No TS suite uses a double or changes a module's state. 18 of the 27
  suites hold one today (2.6). Tasks 5.8 to 5.10 and 6.4 to 6.6.
- Group A first: 27 blocks run in Node 22 after tsc, a fresh process per
  block, before any browser starts (section 5).
- The TS pair test proves that the Python consumer validates what the TS
  producer writes, against `unittest`'s own counts (`PY_GOALPOSTS.md` 9.2).
  Task 5.5.
- Line cases: an integration suite is a table in the gold of the lines
  sent and the lines expected back, which `line_case` runs on the real
  module behind a real port (3.6). Tasks 5.3, 5.9, 5.10 and 6.7.
- Group B: every other block that needs no ttyd and no tty, in
  `chrome-headless-shell` on Linux, the page served from 127.0.0.1 and the
  realm lane carried over the DevTools protocol (section 6).
- Group C is listed and left: what needs ttyd, the server or a tty
  (section 7).

## 2 The TS tests on 2026-10-28

2.1 What there is. 31 files `ts/test_*.ts`: 27 `unittest` suites with 846
test methods by count of their `test_` methods; `test_all.ts`, the entry of
the test page on both threads; and `test_wire_rungs.ts`, the producer of the
wire test. `ts/unittest.ts` is a synchronous subset of Python's `unittest`,
and `ts/tap_producer.ts` writes the text of the Python producer. There is no
TS consumer.

2.2 How they run. tsc compiles every module and suite into one bundle by
`ts/tsconfig.test.json`. `python/page_build.py` puts the bundle into
`html/test.html` with the strings table in place of `I18N_TABLE_JSON`, the
JSLB vectors as the global `test_vectors`, SQLite's wasm and glue, and
xterm.js, as `build/test.html`. The page runs only behind ttyd:
`boot.test_worker` opens `wire.WirePort` to ttyd, the first line, `tap.start`,
comes from `bootstrap.py`, then sqlite3.wasm and the OPFS pool start and are
set as the globals `test_sqlite3` and `test_pool`, and `worker_ai.tap_start`
runs the AI worker's stream: `test_tap_producer`, `test_unittest`, then 20
suites. Its end sends `ui.tests`, at which the UI thread runs its stream: the
same two first suites, then 6. Each TAP line goes to the server as a
`tap.line` push, which the server appends to `tap/typescript.tap`.
`python/test_browser.py`'s suites rung opens the page in Chrome or Edge on
Windows, through the relay of `devtools.py` in `powershell.exe`, and checks
that file with the consumer, after the Python stream (`PY_GOALPOSTS.md`
2.13). The gold's `typescript.run` set to "wire" runs the wire rungs alone,
for `test_wire.py`.

2.3 What blocks a run on this machine. tsc is not on PATH; prettier 3.9.8 is
the only global npm package. `third_party/` holds ttyd only, without the
SQLite and xterm.js archives page_build reads. `test_wire.py` and
`test_browser.py` need ttyd, which `PY_GOALPOSTS.md` 2.10 does not approve.
Node 22.22.1 is at `/usr/bin/node`, and `chrome-headless-shell` at
`/usr/local/bin/chrome-headless-shell`, installed on 2026-10-23 and named by
no file of the tree. `devtools.py` drives only Windows Chrome or Edge.

2.4 The order. The two lists of `test_all.ts` agree with the graph of
runtime references between the modules. Type-only references, such as
`settings.Settings` in `harness`, are not calls. `worker_ai` and `page` call
`harness.values_set`: the bring up is a TAP run (`API/README.md`). The
layers by the rules of `PY_GOALPOSTS.md` 4.1, before any test block adds an
edge:

| Layer | Modules |
| --- | --- |
| 0 | `error_overlay`, `harness`, `tap_producer`, `ui_strings`, `unittest` |
| 1 | `i18n` |
| 2 | `overlay`, `utility` |
| 3 | `jslb`, `settings` |
| 4 | `dispatch`, `http`, `media`, `provider`, `provider_script`, `verbose`, `wire` |
| 5 | `console_view`, `mcp`, `queue`, `script`, `substrate` |
| 6 | `agent`, `page`, `tools_browser`, `worker_ai` |
| 7 | `boot` |

2.5 The producer is unchecked. No pair test reads the TS producer's lines
with the Python consumer. The consumer reads them only after a whole page
run, and `test_wire.py` reads the rung stream before the producer's own
suite has run (`PY_GOALPOSTS.md` 9.2).

2.6 Doubles. 18 of the 27 suites hold one, of the kinds of
`PY_GOALPOSTS.md` 3.2. A plain function a test hands through a public
parameter is not counted (4.3).

| Suite | Replaced | Kind |
| --- | --- | --- |
| `test_unittest` | `EventLog` for `TAPTestResult` | callee |
| `test_error_overlay` | `document.write` and `document.close` | system |
| `test_settings` | `settings_make`, a hand copy of `settings.json` | own data |
| `test_jslb` | `MemorySink`, which answers canned digests, `FullSink`, `FailingSink` and `BrokenSink`, for `substrate.CacheFiles` | callee, fault |
| `test_dispatch` | `Error.stack` by `Object.defineProperty` | system |
| `test_queue` | `PortDouble` for `ThreadPort` and the wire port; `RingDouble` for `verbose.LineRing` and the sink | system, callee |
| `test_http` | fetch causes made up in Chrome's text | fault |
| `test_wire` | `SocketDouble` written into the private `port["socket"]`; the private `message_event` called; `UnusedSink` | system, own data, callee, fault |
| `test_media` | `ImageDouble` for `ImageBitmap`; decode and fetch causes made up | system, fault |
| `test_provider` | `provider.key_clear`, an export for the tests only | own data |
| `test_mcp` | `QueueDouble` for `queue.TaskQueue`; `wake_make` in place of the queue's wake | callee, program |
| `test_substrate` | `MemorySlot` and `ShortSlot` for OPFS handles; `pool_stopped` and `kill_pool` around the real pool; a notifier for `TaskQueue`; `handlers_get`'s map for `dispatch`; the cache-file header, the `_meta` row, the restore suffix and the file names copied from the module | system, fault, callee, own data |
| `test_script` | `StoreDouble`, `CacheDouble` | callee, fault |
| `test_tools_browser` | `ServerDouble`, `StoreDouble`, `CacheDouble`, `TasksDouble`; wakes called directly | callee, program, fault |
| `test_agent` | `StoreDouble`, `ClientsDouble`, `ToolTable`, `TasksDouble`, a register closure; `turn_run` and `wake_next` emulate the queue | callee, program, fault |
| `test_worker_ai` | `PortDouble`, `TasksDouble`, `register_route`, `WireDouble` | callee |
| `test_console_view` | `FakeTerminal` set on `globalThis.Terminal`; `TasksDouble` | system, callee |
| `test_page` | `TasksDouble`, `ImageDouble`, `ViewDouble`, `OverlayDouble`, `HandlerBench` | callee |

`test_tap_producer`'s fixtures are its own test classes, as the pair test's
are in `PY_GOALPOSTS.md` 5.4; its `SilentFixture` overrides `TestCase.run`
and is checked by 4.6. No helper is shared between test files: each file
has its own copies of `gold_value`, `thrown_get` and the rest.

2.7 Unittest is synchronous. A real fetch, a MessagePort delivery, a timer,
`createImageBitmap` or an OPFS promise ends after the test that started it,
so no unit test reaches one; the suites test the code before and after each
with made-up answers. A real `TaskQueue` in synchronous mode, the setting
`queue_synchronous`, drains inside the call that feeds it, and a
`LocalPort` delivers on its own thread, so a unit test can drive a real
queue. The wire rungs are the one asynchronous TAP producer: a task chain
that writes points through `tap_producer.Tracker`.

2.8 The shape. The gold holds named JSLB lines, `typescript.test_<module>.lines`,
for 14 suites, each used by hand in an imperative test. Tests that send a
JSLB line or bytes into the module and compare what comes back:
`test_jslb`'s decoder classes, `test_mcp`'s server classes and
`test_provider_script`. Partly so: `test_dispatch`, `test_queue`,
`test_http`, `test_wire`, `test_media`, `test_provider`, `test_substrate`,
`test_tools_browser`, `test_agent`, `test_worker_ai`, `test_console_view`,
`test_page` and `test_error_overlay`. No gold pairs the lines sent with the
lines expected.

2.9 One realm holds every suite of a thread. The worker's 20 suites share
the dispatch table, which holds the bring up's registrations and every
test's under types never removed; the id counters; the settings store and
the verbose ring that `tap_start` set; the provider key that `test_agent`
and `test_tools_browser` set; `test_tools_browser`'s cached digests; and
the pool of capacity 32. Registering a type twice throws
`dispatch.handler_twice`, and `task_submit` outside a handler run throws
`queue.submit_outside`.

2.10 What a Node realm lacks. `error_overlay.ts` calls `overlay_install`,
which reads `self`, when the bundle loads. `ui_strings.ts` needs
`I18N_TABLE_JSON` replaced. `test_utility`, `test_jslb`, `test_media`,
`test_substrate` and `test_tools_browser` read `test_vectors`. `worker_ai`,
`page` and `boot` call `error_overlay`, so a bundle without it does not
compile. No other module reads a global at load. A MessageChannel with an
`onmessage` keeps Node's loop alive, as `test_queue`'s 40 queues do, so a
Node realm ends by exiting.

2.11 Rules the tests break. `harness.ts` says a test module references only
its own module, `unittest` and `harness`; `test_queue`, `test_tools_browser`,
`test_agent` and `test_boot` call others, and every integration suite will.
`test_browser.py`'s probe kit replaces `Worker` and patches `Blob`: system
doubles in group C (7.2).

## 3 The decisions

Each is class B until the maintainer confirms it (11.2), or rests on a
question of section 9, all answered on 2026-10-30, or was confirmed then
(11.3).

3.1 Three groups. A: every block that runs in Node 22 after tsc with no
double. B: every other block that runs in `chrome-headless-shell` with no
ttyd and no tty. C: the rest, listed in section 7, where planning stops. A
block runs once, in the first group that can run it. A suite whose classes
fall in different groups is split into blocks, one module each.

3.2 A realm per block. A realm is one JavaScript global: in A one `node`
process; in B a dedicated Worker for a worker-side block and a page load
for a UI-side block. Each block starts in a fresh realm, and no test resets
a module's state (the project rule, `PY_GOALPOSTS.md` 2.4). Within a block
each test registers types of its own. A test that needs fresher state than
its block gives moves to a block of its own, such as `test_provider_key.ts`,
and `test_provider_key_unset.ts`, whose one test reads the key unset, which
it read before only by running first. The ids a realm takes from
`dispatch.id_next` start at 102, so expected lines can hold them.

3.3 The realm lane. Every realm speaks JSLB with the driver on a new lane,
`realm`:

1. The driver sends `tap.start` with `i` 101, carrying `settings.json` and
   `test_settings.json`, built as `bootstrap.py` builds it, with
   `jslb.header_make`, `line_make` and `line_encode`.
2. The realm decodes it with `jslb.LineDecoder` over `new
   substrate.CacheFiles([])`, as `boot.ts` does; this is bring up, which
   the project rules exempt. It calls `settings.settings_set` and
   `harness.values_set`, answers Empty, runs its one block, sends each TAP
   line as a `tap.line` push, and ends.
3. In A the lane is the node process's stdin and stdout, and the block is
   named as node's argument, `node node.js BLOCK [--failfast]`. With
   `--failfast` the first failure ends the stream with a bail out, as the
   driver's own `--failfast` does. Node's writes to a pipe are synchronous
   on Linux, so a hard exit loses no line.
4. In B the lane rides DevTools: the driver's line is base64 of its bytes in
   a `Runtime.evaluate` call on the page's main thread, and the realm's
   lines go out as base64 through a binding of `Runtime.addBinding`. The
   main thread relays a worker block's lines over a real MessageChannel
   with a `queue.ThreadPort` at each end.

3.4 One stream (Question T2). Each TS block is a block of `test_all.py`'s one
stream. The realm's TS producer writes a document of one block. The driver
relays the block's indented lines into its own stream as they arrive,
unchanged, each through the gate of `PY_GOALPOSTS.md` 5.3, then writes the
parent line itself with its own number. That line is `ok` only when the
consumer counted no failure in the block and the realm's own parent line
was `ok`; when the two differ the run fails. A bail out from the realm ends
the stream. `python/tap_producer.py` gains `TAPTestRunner.block_relay`,
stub first. Four phases follow the three of `PY_GOALPOSTS.md` 2.1: A unit,
A integration with the TS pair test first, B unit, B integration, each by
layer and alphabetical within a layer. No line marks a phase.

3.5 Unit and integration suites. `test_<module>.ts` tests the module through
its API, on its real callees where it calls them. `test_integrate_<module>.ts`
is a block of line cases (3.6), one for each module that serves JSLB lines
through a port or a queue: `queue`, which also covers `dispatch`, whose
lines arrive only through a queue; `http`; `media`; `mcp`; `provider_script`;
`substrate`; `tools_browser`, through `mcp` lines; `agent`; `worker_ai`;
`console_view`; and `page`. `wire`'s is in group C. A module with no line
entry gets none, since its unit suite already runs on its real callees.
This departs from `PY_GOALPOSTS.md` 2.5, which gives an integration suite to
every module with a project callee (11.2 item 1). `i18n`, and `ui_strings`,
the table it reads, do not count as modules when labelling a unit suite,
as `internationalization` does not.

3.6 Line cases. A new module of the infrastructure for testing,
`ts/line_case.ts`, stub first in `API/ts/line_case.d.ts`, runs a block of
cases:

1. An integration suite exports one function that builds the module's
   real topology in its realm: a real `queue.TaskQueue` with the module's
   handlers registered through the module's own register function, and
   the module's ports. It returns the test's end of the lane the cases
   speak: a real `queue.ThreadPort` over a MessageChannel whose other end
   the queue owns. The one exception is `test_integrate_http`, which has no
   queue: the other end of its ThreadPort pair speaks to the real
   `http.HttpPort` itself, since an `error` line that reaches a queue stops
   it by design, so no failed fetch would come back as a line.
2. The gold `typescript.test_integrate_<module>.cases` lists the cases in
   order, each `{"name", "send", "expect", "seconds"}`. `send` and `expect`
   name lines of the suite's `lines`. A blob's bytes in a gold line are
   base64 under the blob header's key `d`. `line_case.block_run` takes the
   gold's key as an argument, `block_run(runner, name, id, build, done)`,
   since `test_line_case` runs several case tables from its own gold; the
   Node runner passes `typescript.<block>`.
3. `line_case` sends a case's lines through the test's end, collects every
   line that comes back, and adds one point when every expected line is in
   or the seconds are up. The point is `ok` when the lines equal the
   expected lines, in order: header and payload by value, each blob header
   but `d` by value, each blob by size and `utility.sha256_hex`, and an
   `error` line's `stack`, and each `stack` down its `cause` chain, by its
   first line only, the error's name and message, since the rest holds
   build paths and line numbers. Otherwise
   it is `not ok`, with a diagnostic naming the first difference, a line
   still missing or a line not expected.
4. A case never answers a request the module makes (3.9).

3.7 Asynchronous blocks. `tap_producer.TAPTestRunner` gains a block written
as its points arrive: `block_start(name, count)` writes the block's plan of
`count` points at once and returns the block's `Tracker`, and
`block_end(name)` writes its parent line, or with failfast after a failed
point the bail out line. The count is given at the start because every
producer writes a block's plan first, and the Python consumer refuses a
block plan that follows the block's points. `line_case` writes through it,
its count the number of cases, as does `test_line_case`, a block that
writes its own points. `unittest` stays synchronous: a test whose result
arrives after its call is a line case.

3.8 `unittest.TestResult`. `unittest` gains Python's `TestResult` class:
`testsRun`, `failures`, `errors`, `skipped`, `expectedFailures`,
`unexpectedSuccesses` and `shouldStop`, kept as Python keeps them, and
`TAPTestResult` extends it. It is the oracle of the TS pair test, as
Python's is in `PY_GOALPOSTS.md` 5.4, and the real result in place of
`test_unittest`'s `EventLog`.

3.9 The limit of B. The driver and `line_case` send requests and pushes
into the module under test, and read every line it sends out. Neither
answers a request the module makes. A path that waits on a reply from the
server, from ttyd, from the console on tty 0, or from a realm that is not
running is group C. A push the module sends toward the server, such as a
store's commit or a `tap.line`, is read and compared like a reply.

One far end is scripted, by the answer of 2026-10-30 that the far end of
a connection may answer with replies the test scripts (3.10, Question T5):
the driver's HTTP server answers the fetches of `http` and `media`. The
same answer would admit a scripted far end on the AI worker's server
lane, through the `queue.Port` that `worker_ai.tap_start` takes by 3.11
item 4: a ThreadPort pair whose far end is a synchronous queue with the
test's handlers answering `verbose.tail`, `settings.put`, `source.put`
and `echo`. That would move 7.1 items 3, 4 and 6 from C to B. It is not
planned here, and is written down so that the design is not lost.

3.10 HTTP (Question T5). `http.HttpPort` and `media.MediaPort` fetch from a
real HTTP server: an `http.server` of the standard library that the driver
starts on 127.0.0.1, answering each path with the status, headers, body
and delay the suite's gold names. The same server serves the page of B.

3.11 The headless bring up (Question T4).

1. A second template, `html/headless.html`, built by page_build.py as
   `build/headless.html`, carries the same bundle, vectors, SQLite and
   xterm.js. Its last script opens the realm lane: `ts/test_headless.ts`.
2. The driver's server serves the page on 127.0.0.1, since OPFS needs a
   secure origin that is not opaque.
3. `boot` gains `headless_worker(run)`: the worker's bring up with its first
   line from the realm lane in place of `wire.WirePort`, sqlite3, the pool
   and the test slots started as `tests_open` starts them (6.2).
4. `worker_ai.tap_start` takes its server lane as a `queue.Port` and an end
   function in place of a `wire.WirePort`, so a block can hand it a
   ThreadPort. `boot.test_worker` passes the WirePort's own.
5. The ttyd page, `html/test.html` with `test_all.ts`, stays for group C.

3.12 Programs (Question T1). A needs `node` and `tsc`; B also needs
`chrome-headless-shell`. The maintainer approved all three on 2026-10-30
for `test_all.py`'s TS phases (Question T1 B). tsc is TypeScript 5.2.2 from
the apt package `node-typescript`, `/usr/bin/tsc`, and no file of the tree
names any other tsc. `devtools.py` gains a transport for a Linux browser
over `--remote-debugging-pipe`, file descriptors 3 and 4, standard library
only, beside its Windows relay. The reason is that the project keeps one
DevTools client, `devtools.Browser`, and not that the module exists.

3.13 The builds. page_build.py builds the Node bundle `build/ts/node.js` from
a new `ts/tsconfig.node.json`, which lists the modules of A's blocks, A's
suites, `line_case` and `ts/test_node.ts`. It replaces the strings table and
defines `test_vectors` before the bundle, as the page has them, so there is
one replacement of the table for every bundle. It also builds
`build/headless.html`. `test_all.py` builds both at the start of the TS
phases.

## 4 The rules every task follows

4.1 The order. `PY_GOALPOSTS.md` 4.1 items 1 to 5, over the TS modules: M
calls into N when M's code references N's namespace when it runs, or N runs
inside M's test block. A type-only reference is not a call. The bootstrap
exception of its item 6 covers the TS unit blocks of A, which run before
the TS pair test proves the TS producer and the Python consumer agree.

4.2 Unit and integration: 3.5.

4.3 Callbacks. A plain function the test hands through a public parameter
is the test's own (`PY_GOALPOSTS.md` 2.11, Question 10 A): the writer of
`set_stream`, a receiver of `line_receive`, a handler for `dispatch`, a tool
for `mcp.Server`, a sender for `settings.sender_register`, a size reader, a
sink for `verbose.sink_set`, the stop and report functions of
`error_overlay`. It may record what it gets, or throw, and the test checks
it. A function never replaces one the module imports.

4.4 Objects (Question T3). An object written by a test that stands where the
module takes a project class or a platform object is a double, and is
replaced by the real one: a real `queue.TaskQueue`, `LocalPort` or
`ThreadPort`; `verbose.LineRing`; `substrate.Store`; `CacheFiles`, over real
OPFS handles when a blob streams to a file; `mcp.Server` and `ClientSet`;
the xterm.js `Terminal`; `document`; `ImageBitmap`. A test that cannot have
the real object in its group moves to a block of a later group. The far
end of a connection is not such an object: it may answer with replies the
test scripts, as the driver's server of 3.10 does (Question T5).

4.5 System. Nothing is assigned onto `globalThis` or `self`, no prototype is
patched, and no property of a platform object is redefined. A DOM event a
test needs is made with the DOM's own constructor and sent with
`dispatchEvent`.

4.6 Fault. A real fault, such as a fetch to a closed port, bytes that do not
decode as an image, a cache with no free slot, or a block's worker that the
driver terminates mid-transaction. Otherwise the test is removed and
recorded with the code path it reached (`PY_GOALPOSTS.md` 4.8). A cause made
up in a platform's text is fake data and goes.

4.7 Own data. No export for the tests only: `provider.key_clear` goes, and
`provider_script.ScriptPort.node()`, which only test assertions call, goes
with its stub; the tests still check every line the provider answers.
`queue.LocalPort(far?)`, which links two local ports both ways so that two
real queues on one thread are joined, is a general capability of the
queue, not an export for the tests, and stays. No private name is read or
written, such as `test_wire`'s `port["socket"]` and `message_event`. No
layout or name is copied from a module's constants, such as
`test_substrate`'s cache-file header, restore suffix and
`root/name.sqlite`. Values come from `settings.json` and the gold through
`harness`, or from the module's API.

4.8 Gold. A block's values and lines are under its own id
`typescript.<suite>` in `test_settings.json`. A line case names lines and
holds no JSON text.

4.9 Every task:

1. changes a stub in `API/ts/` or `API/python/` before the code it
   describes;
2. compiles with both `ts/tsconfig.test.json` and `ts/tsconfig.node.json`,
   strict;
3. runs `python3 python/reformat.py` twice and reports it if the second run
   changes anything; new files fall under the whitelist globs `ts/*.ts`,
   `API/ts/*.ts`, `html/*.html` and `python/*.py` already;
4. ends with a report naming each test moved and the block it went to, and
   each test removed with the code path it reached.

## 5 Group A: the Node run

5.0 The blocks of A, by the survey of 2026-10-28 with its corrections of
2026-10-30, with Question T3 answered A. `test_wire_port` runs in A, since
it passes 26 of 26 in Node on a real, empty `substrate.CacheFiles([])`,
measured: none of its blobs is large enough to stream to a file.

| Block | Layer | From | What goes |
| --- | --- | --- | --- |
| `test_tap_producer` | 0 | whole | `SilentFixture` by 4.6 |
| `test_unittest` | 0 | whole | `EventLog`, for `unittest.TestResult` (3.8) |
| `test_harness` | 0 | whole | none |
| `test_ui_strings` | 0 | whole | none |
| `test_i18n` | 1 | whole | none |
| `test_utility` | 2 | whole | none |
| `test_jslb` | 3 | `TestBuild`, `TestFields`, `TestEncode`, `TestRender`, `TestJsonDecode`, `TestSurface` | the two encode tests that decode with `MemorySink` go to `test_jslb_decode` (B) |
| `test_settings` | 3 | whole | `settings_make`, for `harness.setting_get` |
| `test_dispatch` | 4 | whole | the redefined `Error.stack`, for a thrown value with no stack, or removed |
| `test_http` | 4 | `TestRequestTranslate`, `TestRequestChecks`, `TestAnswerReply`, `TestPortChecks`, and `TestFailureReply`'s timeout tests | `TestFailureReply`'s made-up causes; real failures in `test_integrate_http` |
| `test_media` | 4 | `TestCacheBudget`, `TestRequestChecks`, `TestReplyLines`, `TestPortChecks`, and `TestFailureLines`' timeout tests | `TestFailureLines`' made-up causes; `TestCacheEviction` to `test_integrate_media` (B) |
| `test_provider` | 4 | all but `TestProviderKey` | none |
| `test_provider_key` | 4 | `TestProviderKey` but `test_key_unset` | `key_clear` |
| `test_provider_key_unset` | 4 | `TestProviderKey`'s `test_key_unset` alone | none; its own fresh realm gives the unset key |
| `test_provider_script` | 4 | whole | `ScriptPort.node()` and the assertions that call it (4.7) |
| `test_verbose` | 4 | whole | none |
| `test_wire` | 4 | `TestInputFrames`, `TestConsolePort`, `TestConsoleRead`, `TestStrictText`, `TestModuleSurface` | `TestWireMessages`, `TestSettingsPhase`, `TestCloseFault` to `test_wire_port`; `TestWireEnd` to C |
| `test_queue` | 5 | the synchronous tests | `PortDouble`, for a real `LocalPort` and a second real `TaskQueue`; `RingDouble`, for a real `verbose.LineRing` |
| `test_substrate` | 5 | the `ref_split`, `doc_encode` and `doc_decode` tests and `TestSurface`, in classes without `StoreCase` | the store and cache tests to `test_substrate_store` (B) |
| `test_mcp` | 6 | `TestSurface`, `TestServerMethods`, `TestServerErrors`, `TestServerWakes` on a real synchronous queue; `TestClientChecks` and `TestClientSet` | `QueueDouble` and `wake_make`; the other client classes to `test_integrate_mcp` |
| `test_line_case` | 6 | new | none |
| `test_wire_port` | 6 | `test_wire`'s `TestWireMessages`, `TestSettingsPhase`, `TestCloseFault` | `UnusedSink`, for a real, empty `substrate.CacheFiles([])` |
| `test_tap_pair_ts` | pair | new, first of A's integration phase | none |
| `test_integrate_queue` | 5 | new, and `test_queue`'s tests that wait on a `ThreadPort` | none |
| `test_integrate_http` | 4 | new: `http.request` lines through a real `HttpPort` to the server of 3.10 | none |
| `test_integrate_provider_script` | 4 | new: chat and image lines through a `ScriptPort` that a real queue owns as `http` | none |
| `test_integrate_mcp` | 6 | new, and `test_mcp`'s other client classes: `mcp` lines between a real `Client` and `Server` on real queues | none |

A layer here counts the edges a test block adds: `test_mcp` and
`test_line_case` use a real queue, so they follow `test_queue`;
`test_wire_port` uses a real `CacheFiles`, so it follows `test_substrate`;
`test_integrate_mcp` runs both `queue` and `mcp`. `TestClientChecks` and
`TestClientSet` stay unit tests, since they throw inside the client before
any line is sent, which no line case sees. Task 5.11 recomputes every
layer.

5.1 Programs (Question T1). Done on 2026-10-30.

1. The maintainer installed tsc from the apt package `node-typescript`, as
   answer B says: `/usr/bin/tsc`, TypeScript 5.2.2.
2. `tsc --version` answers, and the approvals of `node`, `tsc` and
   `chrome-headless-shell` are written into 3.12.

5.2 The wire API. Done on 2026-10-29.

1. Owns `API/ts/lines.d.ts` and the lane table of `API/README.md`. Needs
   nothing.
2. Adds the lane `realm`, DRIVER <-> REALM, JSLB over a node process's
   stdio or over DevTools: `tap.start` DRIVER -> REALM, answered Empty, `i`
   101; `tap.line` REALM -> DRIVER, a push; `tap.pair` REALM -> DRIVER, a
   push carrying one run of the pair fixtures: the run's name `run`, its
   `failfast`, its TAP lines, and for each block its `module`, whether
   `module_run` `passed`, its `cases` by `countTestCases`, and the counts
   of `unittest.TestResult`, which the Python pair test's checks need.
3. Done when the catalogue and the lane table hold them.

5.3 The infrastructure for testing, in TypeScript. Done on 2026-10-29; the
count at `block_start` (3.7) and the stack's first line (3.6 item 3)
follow in its files (8.2).

1. Owns `ts/unittest.ts`, `ts/tap_producer.ts`, the new `ts/line_case.ts`,
   their stubs in `API/ts/`, `ts/test_unittest.ts`, `ts/test_tap_producer.ts`
   and the new `ts/test_line_case.ts`. Needs 5.2.
2. `unittest.TestResult` by 3.8; `test_unittest` checks the outcomes of its
   fixtures through it, in place of `EventLog`. A check of the order of
   events that the real result does not keep becomes a fixture recording
   its own calls, or is removed by 4.6.
3. `TAPTestRunner.block_start` and `block_end` by 3.7, tested in
   `test_tap_producer` with a writer function (4.3).
4. `line_case` by 3.6, and `test_line_case` running it on `queue`'s real
   ports, with cases that pass and cases that fail by design, read as
   lines through the writer.
5. Done when both configs compile and the suites are written. They run in
   task 5.12.

5.4 The Node realm. Done on 2026-10-29.

1. Owns the new `ts/test_node.ts` and `ts/tsconfig.node.json`. Needs 5.2
   and 5.3.
2. `test_node.ts` follows 3.3 items 1 to 3. The first line must be
   `tap.start` with `i` 101; anything else exits 1 with the cascade on
   stderr. The block named by `process.argv[2]`, followed by `--failfast`
   or nothing, is an entry of the runner's block table, of one of three
   kinds: `module`, a `unittest` module run through
   `TAPTestRunner.module_run`; `topology`, a block of line cases whose
   topology `line_case.block_run` runs on the gold `typescript.<block>`;
   or `run`, a block that writes its own points as they arrive, as
   `test_line_case` does. The realm exits 0 after `run_end`, and 1 at any
   throw.
3. `process` is declared in the file with the members it uses: no
   `@types/node` and no package.
4. `tsconfig.node.json` lists the modules of A's blocks in the order of
   `tsconfig.test.json`, without `error_overlay`, `worker_ai`, `page`, `boot`
   and the modules only B's blocks need, then A's suites, `line_case` and
   `test_node.ts`.
5. Done when it compiles.

5.5 The TS pair test.

1. Owns the new `ts/test_tap_pair.ts`, the new `python/test_tap_pair_ts.py`
   and their gold. Needs 5.2 to 5.4, 5.7 and `PY_GOALPOSTS.md` 5.4.
2. `test_tap_pair.ts` runs the fixtures of `PY_GOALPOSTS.md` 5.4 item 3, in
   the outcomes TS `unittest` has, each with failfast and without, alone and
   as one of several blocks, through `TAPTestRunner` into a list, and sends
   one `tap.pair` per run.
3. `test_tap_pair_ts.py`, a Python suite labelled `smoke-test` and the first
   of A's integration phase, starts that realm and checks each run by
   `PY_GOALPOSTS.md` 5.4 items 4 and 5, with `unittest.TestResult`'s counts
   (3.8) as the oracle.
4. Done when it passes, and a deliberate break of the TS producer's failure
   line, then undone, makes it fail.

5.6 The builds (3.13, 3.11 item 1).

1. Owns the builds of the Node bundle and the headless page in
   `python/page_build.py`, its stub, `html/headless.html`, and their tests
   in `test_page_build_tsc.py`, the later suite of `PY_GOALPOSTS.md` 5.12.
   Needs `PY_GOALPOSTS.md` wave 3 and Question T1.
2. The Node bundle is built first. The headless page also needs 6.2, and
   the SQLite wasm and xterm.js archives that page_build.py puts in every
   page, which `python/third_party_fetch.py` has not fetched on this
   machine. Whether an agent may run it, or the maintainer runs it, is a
   question still open with the maintainer, so the headless page waits for
   that answer, and so does `test_page_build_tsc`, which now waits only on
   those archives, since tsc is approved.
3. Done when both build and their tests pass.
4. Status, 2026-10-30: the Node bundle is done. `page_build.node_build`
   builds `build/ts/node.js`, and its tests, which need only tsc and node,
   are the new suite `test_page_build_node.py`, a split suite of
   `page_build` in the unit phase, not `test_page_build_tsc.py`. The stub's
   header holds the design of the headless page: `page_build(template,
   name)`, `html/headless.html` with the markers of `html/test.html`.

5.7 The driver's TS phases (3.3, 3.4).

1. Owns the TS phases of `python/test_all.py` under the lock,
   `TAPTestRunner.block_relay` in `python/tap_producer.py` with its stub, and
   its tests in `python/test_tap_producer.py`. Needs `PY_GOALPOSTS.md` wave
   3, Questions T1 and T2, and 5.4 and 5.6. It is done as two tasks:
   5.7.1, the relay and the server, and 5.7.2, the driver's TS phases,
   items 2 to 5, after 5.7.1.
   1. 5.7.1 writes `TAPTestRunner.block_relay`, stub first, tested in
      `python/test_tap_producer.py`, and the server of 3.10 as a new
      module with its stub and unit suite. The server answers the paths of
      the gold `typescript.test_integrate_http.server` with their status,
      headers, body and delay, holds `closed_port` bound but not
      listening, and serves files of `build/` for the page of B, so that
      both uses have their API at once.
   2. 5.7.2 writes the TS phases of `python/test_all.py` under the lock.
2. The builds run at the start of the TS phases. Each TS block: start its
   realm, write `tap.start`, relay by 3.4 under the block's timer from the
   gold's `module_seconds`, and require exit code 0.
3. The TS blocks and their labels sit in lists beside `_MODULES`, one per
   phase. `--module NAME` runs a TS block too.
4. The server of 3.10 starts before the first block that needs it and stops
   when the run ends.
5. Done when one A block runs alone with `--module`, and a block that fails
   by design stops the stream with the right count under `--failures`.
6. Status, 2026-10-30: 5.7.1 is done. `TAPTestRunner.block_relay`,
   `relay_feed` and `relay_end` relay a realm's block; the server is the new
   module `local_http`, `LocalServer(script, files)`, whose first handler
   failure is raised in the main thread at once. `test_integrate_http`
   passes 11 of 11 against it. 5.7.2 is running.

5.8 Doubles out, layers 0 to 3: `tap_producer`, `unittest`, `harness`,
`ui_strings`, `i18n`, `utility`, `settings`, `jslb`. Done on 2026-10-29;
the digest vectors of item 2 follow (8.2).

1. Owns those suites, the new `ts/test_jslb_decode.ts`, and the modules for
   any fix their suites show, apart from 5.3's. Needs 5.3.
2. The changes of table 5.0. Under Question T3 answer A, `TestDecode`,
   `TestNumbers`, `TestStream`, `TestVectors` and the two encode tests move to
   `test_jslb_decode.ts`, a B block after `test_substrate_store`, on a real
   `CacheFiles` over real OPFS handles. `FullSink`'s fault becomes a cache
   with no free slot; the faults of `FailingSink` and `BrokenSink` are made
   real or removed by 4.6. `test_close_failure` stays: it closes a real
   OPFS file under a blob being streamed into it, and the next write fails
   with the browser's own error, a real fault. The digest vectors of
   `python/vectors_make.py` are filed under the blocks that read them,
   `test_jslb_decode` and `test_substrate_store`, and its entry `empty`,
   `FailingSink`'s canned digest, which nothing reads now, goes.
3. `harness.ts`'s header drops the rule that a test module references only
   its own module, `unittest` and `harness`; rule 4.1 replaces it.
4. Done when no block of the task holds a double or changes a module's
   state, and both configs compile.

5.9 Doubles out, then line cases: `verbose`, `dispatch`, `queue`, `mcp`.
Done on 2026-10-29.

1. Owns those suites, the new `test_integrate_queue.ts` and
   `test_integrate_mcp.ts`, and the modules for any fix. Needs 5.3.
2. The changes of table 5.0. `test_queue` and `test_mcp` build the far side
   of the `server` lane as a second real `TaskQueue` in synchronous mode,
   whose handlers are the test's functions (4.3), joined by a linked pair
   of `queue.LocalPort`s (4.7). The `ui` lane's far end is the test's own
   end of a linked pair, since a queue there would lose the line posted
   just before a fault.
3. Done as 5.8 item 4.

5.10 Doubles out, then line cases: `http`, `media`, `provider`,
`provider_script`, `wire`, and the A part of `substrate`. Done on
2026-10-29; `test_wire_port` and `test_provider_key_unset` into A and
`ScriptPort.node()` out follow (8.2).

1. Owns those suites, the new `test_provider_key.ts`,
   `test_provider_key_unset.ts`, `test_integrate_http.ts`,
   `test_integrate_provider_script.ts` and `test_wire_port.ts`, the A part
   of `test_substrate.ts`, and the modules for any fix. Needs 5.3.
   `test_integrate_http.ts` needs Question T5.
2. The changes of table 5.0. `provider.key_clear` goes with its stub, and
   `ScriptPort.node()` with its stub (4.7). `test_wire_port.ts` is an A
   block on a real, empty `CacheFiles([])`. `test_key_unset` moves from
   `test_provider_key.ts` to `test_provider_key_unset.ts`, alone, since it
   passes only when it runs first in its realm.
3. Done as 5.8 item 4.

5.11 The A order.

1. Owns the lists of A's blocks in `python/test_all.py` under the lock.
   Needs 5.7 to 5.10.
2. Recompute the layers by 4.1, over the tree as the tasks leave it,
   reading each module's runtime references and each block's uses.
3. A unit blocks by layer, alphabetical within; then `test_tap_pair_ts`;
   then A's integration blocks by layer.
4. Every block is labelled `smoke-test` unless the run's timings break the
   120 s of the gold's `smoke_seconds`; then the slowest become
   `normal-test`, by the project rule.
5. Status, 2026-10-30: done. The layers, from the graph the TypeScript
   compiler API resolves, type-only uses left out; no two modules call into
   each other. The TS producer runs in every block, so it is layer 0, and
   the Node runner's start-up is bring up, which counts for no block. An
   integration block also follows the integration blocks of the modules
   that run inside it.

   | Layer | Blocks |
   | --- | --- |
   | 0 | `test_tap_producer`, `test_unittest` |
   | 1 | `test_harness`, `test_ui_strings` |
   | 2 | `test_i18n` |
   | 3 | `test_utility` |
   | 4 | `test_jslb`, `test_settings` |
   | 5 | `test_dispatch`, `test_http`, `test_media`, `test_provider`, `test_provider_key`, `test_provider_key_unset`, `test_provider_script`, `test_verbose`, `test_wire` |
   | 6 | `test_queue`, `test_substrate` |
   | 7 | `test_line_case`, `test_mcp`, `test_wire_port` |
   | 8 | `test_integrate_queue` |
   | 9 | `test_integrate_http`, `test_integrate_mcp`, `test_integrate_provider_script` |

   Every block stays `smoke-test`.

5.12 Run and fix A.

1. One agent, serial. Needs 5.1 to 5.11.
2. Run `python3 python/test_all.py --stream`. At the first failing TS
   block, fix the module it tests or its suite, and run again until A is
   clean; then with `--normal-test`.
3. Done when the Python phases and A pass inside 120 s. A's time is
   recorded as a measurement.
4. Status, 2026-10-30: done with no fix. `--stream`, `--normal-test
   --stream` and `--tty --stream` each pass 85 of 85 blocks, 58 Python and
   27 of A, 1320 points, in about 29 s. A alone takes 9.54 s, 7.81 s of it
   inside the block timers and the rest building the Node bundle.

## 6 Group B: headless Chrome, no tty

6.0 The blocks of B, with Question T3 answered A and Question T4 answered A.

| Block | Side | From | What goes |
| --- | --- | --- | --- |
| `test_error_overlay` | UI | `TestOverlay`, `TestStop`, `TestSurface` | the replaced `document.write` and `close`, for the real ones in the block's own page load; the skips by thread |
| `test_error_overlay_worker` | worker | `TestReport` | the skips by thread |
| `test_overlay` | UI | whole | none |
| `test_console_view` | UI | whole | `FakeTerminal`, for the real xterm.js `Terminal`; `TasksDouble`, for a real queue |
| `test_page` | UI | whole | the five doubles, for a real queue, `Overlay`, `ConsoleView` and `MediaPort` image cache |
| `test_substrate_store` | worker | the store and cache classes of `test_substrate` | `MemorySlot` and `ShortSlot`, for real OPFS handles; the notifier, for a real queue; the pool wrappers and copied names, by 4.6 and 4.7 |
| `test_jslb_decode` | worker | 5.8 item 2 | none |
| `test_script` | worker | whole | `StoreDouble` and `CacheDouble`, for a real `Store` |
| `test_tools_browser` | worker | all but `TestConsole` and `test_tail_asked` | the four doubles, for a real `Server`, `Store`, `CacheFiles` and queue |
| `test_agent` | worker | whole | the five doubles, for a real `Store`, `ClientSet` and queue |
| `test_worker_ai` | worker | `TestOwnerTables`, `TestQueueMode`, `TestWireTap`, `TestSurface` | `PortDouble`, for a real `LocalPort`; `TasksDouble` |
| `test_boot` | UI | whole | none |
| `test_integrate_media` | UI | new, and `TestCacheEviction`: `media.store` and `media.fetch` lines, real decode, real fetch from the server of 3.10 | none |
| `test_integrate_substrate` | worker | new: the store lines of the ui-ai lane, their replies and their commit pushes | none |
| `test_integrate_tools_browser` | worker | new: `mcp` tool calls through a real `Server` on a real queue | none |
| `test_integrate_agent` | worker | new: `ai.say` and `ai.click`, the provider a `ScriptPort` | none |
| `test_integrate_console_view` | UI | new: `console.show`, `console.output` and `console.exit` | none |
| `test_integrate_page` | UI | new: the ai-ui lines `page.handlers_register` serves, the DOM read back | none |
| `test_integrate_worker_ai` | worker | new: `tap_start` in a fresh worker, `tap.start` answered, `settings.set` sent, store lines answered, commits pushed | none |

6.1 The Linux DevTools transport (3.12).

1. Owns the transport in `python/devtools.py`, its stub, and its tests in
   `test_devtools_chrome.py`, a later suite by `PY_GOALPOSTS.md` 4.6 until
   the browser is approved. Needs `PY_GOALPOSTS.md` wave 3 and Question T1.
2. Starts `chrome-headless-shell` with `--remote-debugging-pipe` and a
   profile of its own that goes when it does, and speaks DevTools on
   descriptors 3 and 4: `Runtime.evaluate`, `Runtime.addBinding` and its
   `Runtime.bindingCalled` events, `Page.navigate`, the console.
3. Done when its tests pass.
4. Status, 2026-10-30: done. `devtools.LinuxPipe` beside `WindowsRelay`;
   `test_devtools_chrome.py` runs in the unit phase, since the browser is
   approved, 14 tests on the real `chrome-headless-shell`.

6.2 The headless bring up (3.11, Question T4).

1. Owns `ts/test_headless.ts`, `boot`'s `headless_worker`, the server lane
   of `worker_ai.tap_start`, their stubs, and `test_boot` and
   `test_worker_ai` for the changed APIs. Needs 5.2, 5.3 and Question T4.
2. `test_headless.ts` opens the realm lane on the main thread (3.3 item 4).
   It runs a UI block in its own page load, and a worker block in a fresh
   Worker made from the texts of the `data-worker` scripts, relaying over a
   ThreadPort pair.
3. `boot.headless_worker` sets the global `test_slots` as
   `boot.tests_open` does: three OPFS files of a directory of their own,
   cleared at start, that no cache holds, which `test_jslb_decode` reads.
   Start-up is bring up, which the project rules exempt.
4. Done when both configs compile. `html/headless.html` is written with
   the headless build of 5.6.
5. Status, 2026-10-30: done, compiled only. The realm's entry is
   `test_headless.realm_start(BLOCK, FAILFAST, LINE)` by `Runtime.evaluate`,
   and its lines go out through the binding `realm_line`. `headless_worker`
   starts sqlite3, the pool and `test_slots`, and no test cache, since no
   headless line streams a blob into one.

6.3 The driver's B phases.

1. Owns the B phases of `python/test_all.py` under the lock. Needs 5.7,
   5.11, 6.1, 6.2 and 5.6, and so the answer on the SQLite wasm and
   xterm.js archives that 5.6 item 2 waits for.
2. One browser for the run. Each block: a page load from the server of
   3.10, then `tap.start` over DevTools, the relay of 3.4 under the block's
   timer, and the realm's end line.
3. Done as 5.7 item 5, for a B block.

6.4 Doubles out on the UI side: `error_overlay`, `overlay`, `console_view`,
`page`, `boot`.

1. Owns those suites, the new `test_error_overlay_worker.ts`,
   `test_integrate_console_view.ts` and `test_integrate_page.ts`, and the
   modules for any fix. Needs 6.2.
2. The changes of table 6.0. The fault screen is written into the block's
   own page by the real `document.write`.
3. Done as 5.8 item 4.

6.5 Doubles out on the worker side, the store: `substrate`, `jslb`'s B
block, `script`.

1. Owns `test_substrate_store.ts`, `test_script.ts`,
   `test_integrate_substrate.ts`, and the modules for any fix.
   `test_jslb_decode.ts` stays with 5.8. Needs 6.2.
2. The store builds from the realm's sqlite3 module and pool, which the
   bring up starts. The crash test terminates the block's worker
   mid-transaction from the driver, or is removed by 4.6.
3. Done as 5.8 item 4.

6.6 Doubles out on the worker side, the top: `tools_browser`, `agent`,
`worker_ai`, and `media`'s line cases.

1. Owns those suites, `test_integrate_tools_browser.ts`,
   `test_integrate_agent.ts`, `test_integrate_worker_ai.ts`,
   `test_integrate_media.ts`, and the modules for any fix. Needs 6.2, 6.5
   and Question T5.
2. The changes of table 6.0. The tests that go to C are recorded (7.1).
3. Done as 5.8 item 4.

6.7 The integration suites of B are written by 6.4 to 6.6, each by 3.6.

6.8 The B order and the run.

1. Owns the lists of B's blocks in `python/test_all.py`. Needs 6.3 to 6.6.
2. As 5.11 and 5.12 for B: by layer, alphabetical within, B unit then B
   integration.
3. Done when the Python phases, A and B pass inside 120 s, in both
   categories. Planning ends here (section 7).

## 7 Group C: the limit

7.1 What no headless realm without a tty can run, by 3.9:

1. `wire.WirePort.wire_open`, its socket send and drain, `wire_end` and
   `wire_close` on an open socket (`TestWireEnd`), and `ConsolePort`'s open
   and input: ttyd's WebSocket protocol on tty 1 and tty 0.
2. `test_wire_rungs.ts` and `python/test_wire.py`: every rung waits on the
   server through ttyd, and two drive dash on tty 0.
3. `test_worker_ai`'s `TestRelays`, which needs the console owner and the
   server's `settings.put` reply, and `TestFaults`, which needs an open
   WirePort.
4. `test_tools_browser`'s `TestConsole`, the console owner, and
   `test_tail_asked`, `verbose.tail` to the server.
5. `console_view`'s open path: `console.open` to the console owner.
6. Every request from the AI worker to the server that waits on a reply:
   `verbose.tail`, `tap.run`, the `settings.put` relay, `source.put`,
   `echo`; and `system.restart` with its new `tap.start`. `db.restore` and
   `db.file` from a real server store.
7. `python/test_browser.py`'s rungs, with its probe kit's doubles (2.11).
8. A realm with `debug` false: `tap.start` carries the gold in debug mode
   only (`API/README.md`), so no test can run there, and
   `test_tools_browser`'s `test_debug_off` is recorded, not run.

7.2 Planning stops here. `test_wire.py` and `test_browser.py` stay after
the stream, where `PY_GOALPOSTS.md` 2.13 puts them, and the ttyd page stays
as it is.

## 8 Order and sharing

8.1 Done. On 2026-10-29, while the agents of `PY_GOALPOSTS.md` ran its
wave 3, which passed the same day: 5.2, 5.3, 5.4, 5.8, 5.9 and 5.10,
compile-checked with a tsc borrowed from outside the tree, which no file
names. 23 of the 24 A blocks then in the Node runner's table passed in
Node, 469 tests, run outside the driver; `test_integrate_http` waits for
the server of 3.10. On 2026-10-30 the maintainer answered Questions T1 to
T5, which did 5.1.

8.2 What follows, in waves, each after the one before; the tasks of a wave
run in parallel, each on the files it owns:

1. Wave 1:
   1. The follow-ups of 2026-10-30 in the files of 5.3, 5.8 and 5.10: the
      count at `block_start` (3.7), the stack's first line (3.6 item 3),
      `test_wire_port` and `test_provider_key_unset` into A (5.0),
      `ScriptPort.node()` out (4.7), and the digest vectors (5.8 item 2).
   2. 5.6, the Node bundle; the headless page waits (5.6 item 2).
   3. 5.7.1, the relay and the server.
   4. 6.1 and 6.2, which run beside A's work since they own separate
      files; 6.2 compiles only, since nothing runs a page yet.
2. Wave 2: 5.7.2, and 5.5 written beside it; 5.5 is done once it passes in
   the run that 5.7.2 builds.
3. Wave 3: 5.11, then 5.12, one agent; `test_integrate_http` passes here.
4. Wave 4, once the maintainer answers whether an agent may run
   `python3 python/third_party_fetch.py` for the SQLite wasm and xterm.js
   archives (5.6 item 2): the archives, the headless page of 5.6 with
   `html/headless.html`, `test_page_build_tsc` taken out of the later
   suites (`PY_GOALPOSTS.md` 9.6), and 6.3.
5. Wave 5: 6.4, 6.5 and 6.6.
6. Wave 6: 6.8, then the whole runs and two runs of `python/reformat.py`
   over the whole tree.

8.3 No B block runs before A passes in 5.12, though 6.1 and 6.2 are
written beside A's tasks.

8.4 Every task works in the main tree, as `PY_GOALPOSTS.md` 7.1 says. A
task owns the files its section names, and a failure in a file another task
owns is reported to that task.

8.5 Shared files are edited only under a lock: the file renamed with the
task number appended, such as `ts/queue.ts.5.9`, for one edit, then renamed
back. A file found missing is waited for, never recreated. The shared files:

1. `python/test_all.py`: tasks 5.7.2, 5.11, 6.3 and 6.8, after the tasks
   of `PY_GOALPOSTS.md`.
2. `test_settings.json`: each block's gold under its own id, edited in
   place, never rewritten whole.
3. `i18n/en-US.json`: new texts under the module's own keys.
4. `ts/tsconfig.test.json` and `ts/tsconfig.node.json`: a task adds its own
   new files.
5. `API/README.md`: task 5.2's lane table, beside `PY_GOALPOSTS.md`'s
   edits.

## 9 Questions

Question T1: which programs may `test_all.py` start for the TS phases, and
how is tsc installed?

[ ] A. `node`, `tsc` and `chrome-headless-shell`; the maintainer installs
tsc with `npm install --global typescript` into `~/.npm-global`, beside
prettier. (Recommended: the one place global npm packages live now, and it
unblocks A and B.)

[x] B. `node`, `tsc` and `chrome-headless-shell`; tsc from the apt package
`node-typescript`, which the maintainer installs.

[ ] C. `node` and `tsc` only: group A runs, group B waits.

[ ] D. None yet: nothing of this plan runs.

Answered B by the maintainer on 2026-10-30: `node`, `tsc` and
`chrome-headless-shell` are approved, and tsc is installed from
`node-typescript` as `/usr/bin/tsc`, TypeScript 5.2.2 (3.12, 5.1).

Question T2: how does a TS block join the run of `test_all.py`?

[x] A. As a block of the one stream: the realm's block lines relayed
unchanged, the parent line written by the driver, and
`TAPTestRunner.block_relay` added to `python/tap_producer.py` (3.4).
(Recommended: one run and one stream, as `PY_GOALPOSTS.md` 2.1 decided for
Python, and a failure names the TS module.)

[ ] B. Each realm's document is checked apart by its own `StreamReader`
after the Python stream, with no change to a producer: one document per
block, 45 in all.

[ ] C. One realm for all of A and one page for B, one document each, with
no fresh realm per block, so that tests reset state or depend on order,
against 3.2.

Answered A on 2026-10-30: decided by the agent by `PY_GOALPOSTS.md` 2.1,
one run and one stream, and the maintainer accepted the decision.

Question T3: is an object a test writes to implement an interface the
module takes as a parameter, such as `jslb.BlobSink`, `queue.Port` or
`substrate.SlotHandle`, a double?

[x] A. Yes. It is replaced by the real implementation, and a test without
one moves to a later group. (Recommended: `PY_GOALPOSTS.md` 2.3 bans a
double of any kind, and 4.7 a hand-made reader.) The cost: `test_jslb`'s
decoder classes and two encode tests, 43 tests, and `test_wire`'s WirePort
classes, 26 tests, need `substrate.CacheFiles` and move to B.

[ ] B. Not when it does the real work and answers nothing canned: it keeps
the bytes it gets and hashes them with `utility.sha256_hex`. Those 69 tests
stay in A. `MemorySink`'s canned digests and `UnusedSink` go either way.

Answered A by the maintainer on 2026-10-30, with T5, as one answer:
nothing stands in for a project part or a platform object that a module
calls, and the far end of a connection may answer with replies the test
scripts. The WirePort classes, `test_wire_port`, stay in A all the same,
since they pass on a real, empty `CacheFiles` (5.0).

Question T4: may the product APIs change so that the AI worker's high level
integration runs without ttyd?

[x] A. Yes: `worker_ai.tap_start` takes its server lane as a `queue.Port`
and an end function, `boot` gains `headless_worker`, and a second template
carries the headless entry (3.11). (Recommended: it is the only way
`tap_start` runs headless, and `boot.test_worker` keeps passing the
WirePort's own.)

[ ] B. No: `test_integrate_worker_ai` builds the worker's topology itself
from each module's register function, and `tap_start` stays in C.

[ ] C. No: the worker's and the page's bring up stay in C, and
`test_integrate_worker_ai` is not written.

Answered A by the maintainer on 2026-10-30.

Question T5: is the driver's standard library HTTP server, answering what
the gold names, the real network for `http` and `media` (3.10)?

[x] A. Yes. (Recommended: no project module is replaced, and the fetch, its
timeouts and its failures are real.)

[ ] B. No, it is a double of the network: the fetch paths of `http` and
`media` go to C, and `test_integrate_http` is not written.

Answered A by the maintainer on 2026-10-30, with T3, as one answer:
nothing stands in for a project part or a platform object that a module
calls, and the far end of a connection, here the driver's server, may
answer with replies the test scripts.

## 10 Outside this plan

10.1 Group C (section 7).

10.2 `test_integrate_http` runs in Node (3.1), so the browser's own fetch,
its CORS checks and its failure texts, is tested only where a B block
fetches, in `test_integrate_media`.

10.3 `ts/tsconfig.node.json` sets no `lib` narrower than the default, so a
use of the DOM in an A block compiles and fails when it runs.

10.4 The ttyd page's two lists in `test_all.ts` repeat the blocks of
`test_all.py` until C is planned.

10.5 The helpers each suite copies, such as `gold_value` and `thrown_get`,
stay copied.

10.6 `PY_GOALPOSTS.md` 9.2, the order of `test_wire.py` before the TS
producer's suite, is met for A and B by the TS pair test; `test_wire.py`
itself stays in C.

## 11 Requirements analysis

The requests are those of this conversation, `tmp/tasks_28_1951.md` item 1,
and the ones of earlier logs that bear on TypeScript: `tmp/tasks_25_1832.md`
item 10.1 and `PY_GOALPOSTS.md` 9.2; and the maintainer's answers of
2026-10-30, with the acceptance of every decision reported to the
maintainer then (`tmp/tasks_29_1354.md` items 21 and 22). A: unsatisfied
or modified without cause. B: unsatisfied or modified with cause but
without confirmation. C: confirmed withdrawn or modified. D: satisfied
without modification or withdrawal.

11.1 Class A: none.

11.2 Class B, each satisfied in this plan with the stated cause, and
wanting confirmation:

1. Integration suites only for modules that serve lines, against
   `PY_GOALPOSTS.md` 2.5 (3.5).
2. The new infrastructure API `unittest.TestResult` (3.8).
3. A DOM event made by the DOM's constructor and `dispatchEvent` counts as
   real (4.5).
4. Question 10 A, which made a handler or a tool a plain function of the
   test, is extended to every function parameter, recorders and throwing
   functions included (4.3).
5. `devtools.py` gains a Linux transport, in place of a new module (3.12).
6. `harness.ts`'s rule on the references of a test module gives way to
   rule 4.1 (5.8 item 3).
7. The driver builds `tap.start` with `jslb` as `bootstrap.py` does, not by
   calling into `bootstrap.py` (3.3).
8. 6.1 and 6.2 are written beside A's tasks, where the plan of 2026-10-28
   put them after 5.12, since they own separate files. No B block runs
   before A passes, so the request of 11.4 item 7 still holds (8.2, 8.3).

11.3 Class C, confirmed by the answers and acceptances of 2026-10-30:

1. "figure out what TS test suites can be run using the TS toolchain
   without mocking apis": answered by blocks, not suites. Eight suites
   (`jslb`, `http`, `media`, `provider`, `wire`, `queue`, `mcp`,
   `substrate`) split between groups, since their classes need different
   realms (3.1, 5.0). Confirmed by Question T3 A and by the accepted moves
   of `test_wire_port` into A and of `test_key_unset` into a block of its
   own.
2. "TAP and jslb driving the high level integration tests, but no tty":
   DevTools carries the realm lane, the first line and the TAP lines, and
   the line cases inside the realm send JSLB straight to the modules (3.3,
   3.6). Confirmed by Questions T1 B and T4 A.
3. "a TAP test producer sending jslb directly to the modules under test
   ... reporting back to a TAP consumer": the producer is the TS one in the
   realm, through `line_case`, and the consumer the Python one in the
   driver, confirmed by Question T2 A. The clause that a module with no line
   entry keeps `unittest` tests of its API rests on 3.5, still class B
   (11.2 item 1).
4. New infrastructure APIs: `TAPTestRunner.block_start` and `block_end`
   (3.7), with the count at the start; `line_case` (3.6); and Python's
   `TAPTestRunner.block_relay` (3.4), by Question T2 A.
5. The lane `realm` and the line type `tap.pair`, with its extra fields
   (5.2).
6. `test_integrate_http` runs in Node, so Chrome's fetch is tested only
   through `test_integrate_media` (10.2). Confirmed by Question T5 A.
7. The decisions of 2026-10-29 and 2026-10-30 that changed this plan, all
   accepted: `queue.LocalPort(far?)` kept as a general capability (4.7);
   the bring up's `test_slots` global (6.2); `test_close_failure` kept as a
   real fault (5.8 item 2); the `ui` lane of `test_queue` and `test_mcp`
   the test's own end of a linked pair (5.9 item 2); `TestClientChecks` and
   `TestClientSet` kept in `test_mcp` (5.0); the Node runner's `--failfast`
   and its `run` blocks (3.3, 5.4); the gold key of `block_run` and blob
   bytes as base64 under `d` (3.6 item 2); an `error` line's `stack`
   compared by its first line (3.6 item 3); `test_integrate_http` with no
   queue (3.6 item 1); `test_wire_port` in A (5.0); `test_key_unset` in a
   block of its own (3.2, 5.0); `ScriptPort.node()` removed (4.7); the
   corrections of table 5.0; and the digest vectors filed under the blocks
   that read them (5.8 item 2).

11.4 Class D:

1. "other agents are running, make a plan only": no source, test, settings
   or existing plan file was changed.
2. "group the plan as follows. A ... B ... C": sections 5, 6 and 7.
3. "C: once the limits of what can be done by running tests in headless
   without a tty, then stop planning": section 7 lists the limit and plans
   nothing past it.
4. "do a review of the current TS test situation": section 2.
5. "your plan will have to include all required changes": sections 3 to 7.
   Questions T1 to T5 decide 5.1, 5.7, 6.1, 6.2, the split of 5.8 and 5.10,
   and `test_integrate_http`.
6. `tmp/tasks_25_1832.md` item 10.1 and `PY_GOALPOSTS.md` 9.2, the TS
   producer read before its own suite runs: task 5.5 and rule 4.1.
7. "make a plan to move those tests first, before the headless browser
   tests start": A runs in two phases before B's (8.2, 8.3); its waits on
   `PY_GOALPOSTS.md` wave 3 and Question T1 are over.
8. A realm per block (3.2), the TS form of `PY_GOALPOSTS.md` 4.3's forked
   child, kept by Question T2 A over its option C.
9. Questions T1 B (3.12, 5.1), T2 A (3.4), T3 A and T5 A (4.4, 3.10) and
   T4 A (3.11), answered on 2026-10-30.

11.5 Unresolved: the confirmations of 11.2, and the question still open
with the maintainer whether an agent may run
`python3 python/third_party_fetch.py` for the SQLite wasm and xterm.js
archives, on which the headless page and every B run wait (5.6 item 2).
