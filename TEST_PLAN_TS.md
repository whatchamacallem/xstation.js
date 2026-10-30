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
answered Questions T1 to T5, which did 5.1, and the rest of group A was
done the same day, 5.5, 5.6, 5.7, 5.11 and 5.12, so A runs in the official
run, with 6.1 and 6.2 of group B written. The maintainer then answered
Question T6, so the driver fetches the pinned third party files at the
start of every run (3.14); asked for a scripted far end of the AI worker's
lane to the server, task 6.9; and wrote into the project rules that a
scripted AI is expected and allowed in testing (4.4). Section 8 gives what
is done and what follows. "Question Tn" names a question of section 9; the T keeps
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
  T2). Tasks 5.7 and 6.3; 5.7 is done, so A's blocks do.
- No TS suite uses a double or changes a module's state. 18 of the 27
  suites held one on 2026-10-28 (2.6). On 2026-10-30 ten files
  `ts/test_*.ts` still hold one, all of B or C: `test_error_overlay`,
  `test_console_view`, `test_page`, `test_substrate_store`, `test_script`,
  `test_tools_browser`, `test_agent`, `test_worker_ai`,
  `test_integrate_media`, and `test_wire_end`, which keeps its doubles in C
  (7.2). Tasks 5.8 to 5.10, done, then 6.4 to 6.6 and 6.9.
- Group A first: 27 blocks run in Node 22 after tsc, a fresh process per
  block, before any browser starts (section 5). All 27 pass in the official
  run since 2026-10-30 (5.12).
- The TS pair test proves that the Python consumer validates what the TS
  producer writes, against `unittest`'s own counts (`PY_GOALPOSTS.md` 9.2).
  Task 5.5.
- Line cases: an integration suite is a table in the gold of the lines
  sent and the lines expected back, which `line_case` runs on the real
  module behind a real port (3.6). Tasks 5.3, 5.9, 5.10 and 6.7.
- Group B: every other block that needs no ttyd and no tty, in
  `chrome-headless-shell` on Linux, the page served from 127.0.0.1 and the
  realm lane carried over the DevTools protocol (section 6).
- Scripted far ends answer the AI worker's requests of the server and the
  AI's requests of its provider, so that the tests that waited only on such
  an answer run in B (3.9, tasks 6.9 and 6.10).
- Group C is listed and left: what needs ttyd, the console on tty 0, an
  open WebSocket, the real server's store or a tty (section 7).

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

2.3 What blocked a run on this machine, as of 2026-10-28. tsc is not on
PATH; prettier 3.9.8 is the only global npm package. `third_party/` holds
ttyd only, without the SQLite and xterm.js archives page_build reads. `test_wire.py` and
`test_browser.py` need ttyd, which `PY_GOALPOSTS.md` 2.10 does not approve.
Node 22.22.1 is at `/usr/bin/node`, and `chrome-headless-shell` at
`/usr/local/bin/chrome-headless-shell`, installed on 2026-10-23 and named by
no file of the tree. `devtools.py` drives only Windows Chrome or Edge.
Since 2026-10-30 tsc is `/usr/bin/tsc` (3.12), `third_party/` holds the
three pinned archives (3.14), and `devtools.py` also drives
`chrome-headless-shell` (6.1); ttyd is still not approved.

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
for a UI-side block, and for a block of the side `lanes` a page load over
a fresh Worker (6.9 item 5), and for a block of the side `workers` a page
load over a fresh Worker for each case (6.11). Each block starts in a
fresh realm, and no
test resets
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
4. A case never answers a request the module makes. Only a scripted far
   end that the block's topology builds answers one, with the replies the
   gold scripts (3.9, 6.9).

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
answers a request the module makes; only a scripted far end does, below.
A path that waits on a reply from ttyd, from the console on tty 0, or from
a realm that is not running is group C, and so is one that waits on the
server for what no scripted far end can give, such as a database the real
server's store wrote. A push the module sends toward the server, such as a
store's commit or a `tap.line`, is read and compared like a reply.

The scripted far ends, by the answer of 2026-10-30 that the far end of a
connection may answer with replies the test scripts (3.10, Question T5),
and by the project rule, written the same day at the maintainer's
request, that a scripted AI is expected and allowed in testing (4.4):

1. The driver's HTTP server answers the fetches of `http` and `media`.
2. A scripted AI answers the AI's provider: a `provider_script.ScriptPort`,
   or a second real queue whose `http.request` handler is the test's
   function answering with the gold's frames (6.9 item 4).
3. A scripted server answers the AI worker's lane to the server, task 6.9,
   which the maintainer asked for on 2026-10-30, where until then this
   paragraph recorded the design as not planned. It moves to B the tests of
   7.1 items 3, 4 and 6 that waited only on the server's answer (6.9 item
   6).

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
   ThreadPort. `boot.test_worker` passes the WirePort's own. Correction of
   2026-10-30: no block can hand it one, since `boot.headless_worker` runs
   `tap_start` at bring up, before the block runs, and `tap_start` runs
   once per worker. The headless page chooses what stands at the far end
   of the lane it posts the worker, which is how task 6.9 reaches it (6.9
   item 5).
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

3.14 Third party (Question T6). `python/third_party_fetch.py` fetches the
pinned files, each checked against its pinned SHA-256, into one directory
per library: `third_party/ttyd/ttyd-1.7.7.tar.gz`,
`third_party/sqlite/sqlite-wasm-3460100.zip` and
`third_party/xterm/xterm-5.5.0.tgz`. The project's own ttyd patch is
`third_party/ttyd/patches/01_srv_buf_size.patch`, which git tracks, and the
settings `powershell.ttyd_archive` and `powershell.ttyd_patches` name the
archive and the patches. `.gitignore` ignores everything under
`third_party/` but the `patches/` directories, by `third_party/**`,
`!third_party/*/`, `!third_party/*/patches/` and
`!third_party/*/patches/**`. The fetch's API is
`third_party_fetch.pins_fetch() -> list[str]`, which fetches every pin and
returns their paths. `test_all.py` calls it in process at the start of
every run, before the smoke run's 120 s deadline starts and outside every
block timer, as bring up, and the command line `python3
python/third_party_fetch.py` calls it too. A file already in place with its
pinned digest is left alone, so a run makes no network traffic then. A
failed download or a wrong digest ends the run with its error before the
first block. The pins are the only downloads, and no program is started
for them.

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

A scripted AI is expected and allowed, whether it is called a script, a
double or a mock: the project rules make it the primary exception to the
ban on mock test objects since 2026-10-30, as the suites must run without
an AI API endpoint, which is non-deterministic. It is
`provider_script.ScriptPort`, a second real queue whose `http.request`
handler is the test's function answering with the gold's frames, or the
driver's server of 3.10 answering as the AI API from the gold. It may
drive any test whose input is an AI's turn, its tool calls reaching the
real store (6.9 item 4). The exception covers the AI and nothing else: a
cause made up in a platform's text is still fake data (4.6, 6.10 item 4).

4.5 System. Nothing is assigned onto `globalThis` or `self`, no prototype is
patched, and no property of a platform object is redefined. A DOM event a
test needs is made with the DOM's own constructor and sent with
`dispatchEvent`.

4.6 Fault. A real fault, such as a fetch to a closed port, bytes that do not
decode as an image, a cache with no free slot, or a block's worker that its
page terminates mid-transaction (6.11). Otherwise the test is removed and
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
5. Status, 2026-10-30: done. `ts/test_tap_pair.ts` is a `run` block of the
   Node realm, and `python/test_tap_pair_ts.py`, 6 tests, `smoke-test`,
   runs ten fixtures four ways each, failfast off and on, alone and between
   two passing blocks, 40 runs. A deliberate break of `ts/tap_producer.ts`,
   writing a failing test `ok`, made it fail, and was undone. TS `unittest`
   has no subtests and no class or module fixtures, so each test's own
   `setUp` and `tearDown` failures stand in for `PY_GOALPOSTS.md` 5.4 item
   7.
6. Deferred, with its design, so that it is not lost. A test with two
   failures, such as one whose body fails and whose `tearDown` then fails,
   is left out of the fixtures: `tap.pair` carries counts per block, and
   `unittest.TestResult` counts that test twice where TAP counts it once.
   The design: `TapPairBlock` of `API/ts/lines.d.ts` gains
   `failed_tests: string[]`, the `id()` of each test with a failure, an
   error or an unexpected success, each id once, in the order the tests
   ran, which `test_tap_pair.ts` writes from its `unittest.TestResult`;
   `python/test_tap_pair_ts.py` counts a block's failures as the number of
   those ids, one per test however many failures it had, as
   `PY_GOALPOSTS.md` 2.16 counts and as Python's own pair test grades test
   by test; and the fixtures gain the test that fails twice, in its body
   and in its `tearDown`, run the four ways. Stub first, in
   `API/ts/lines.d.ts` and the lane table of `API/README.md`.

5.6 The builds (3.13, 3.11 item 1).

1. Owns the builds of the Node bundle and the headless page in
   `python/page_build.py`, its stub, `html/headless.html`, and their tests
   in `test_page_build_tsc.py`, the later suite of `PY_GOALPOSTS.md` 5.12,
   and `test_page_build_node.py` (item 4). Needs `PY_GOALPOSTS.md` wave 3
   and Question T1.
2. The Node bundle is built first. The headless page also needs 6.2, and
   the SQLite wasm and xterm.js archives that page_build.py puts in every
   page. On 2026-10-29 `python/third_party_fetch.py` had not fetched them on
   this machine, and whether an agent might was asked of the maintainer.
   Question T6 answered it on 2026-10-30, and the driver now fetches them
   at the start of every run (3.14).
3. Done when both build and their tests pass.
4. Status, 2026-10-30: the Node bundle is done. `page_build.node_build`
   builds `build/ts/node.js`, and its tests, which need only tsc and node,
   are the new suite `test_page_build_node.py`, a split suite of
   `page_build` in the unit phase, not `test_page_build_tsc.py`. The stub's
   header holds the design of the headless page: `page_build(template,
   name)`, `html/headless.html` with the markers of `html/test.html`.
5. Status, 2026-10-30, later: done. `page_build.page_build(template,
   name)` builds `build/NAME.html` from `html/TEMPLATE.html` and returns its
   SHA-256, and `python3 python/page_build.py headless headless` builds
   `build/headless.html` from the fetched archives, which match their pins.
   `test_page_build_tsc` left the later suites: it sits in the Python unit
   phase after `test_page_build_node`, labelled `smoke-test`, and passes, 4
   tests in 4.42 s.

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
   passes 11 of 11 against it. 5.7.2 is done too: `_A_UNIT` and
   `_A_INTEGRATION` beside `_MODULES`, every entry `smoke-test`;
   `RealmRunner` starts `node build/ts/node.js BLOCK [--failfast]`, writes
   `tap.start`, checks the Empty reply and relays; the bundle is built once
   at the start of A, outside the block timers; a TS block is named by its
   file in `--module`, such as `test_jslb.ts`, since 8 block names are also
   Python suites; and `ts/failing_block.ts`, in `_FAILING`, gives the right
   counts under `--failures`.

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

6.0 The blocks of B, with Question T3 answered A and Question T4 answered A,
and the scripted far ends of 3.9 (6.9).

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
| `test_tools_browser` | worker | all but `TestConsole`'s `test_console_recorded`, `test_permit_always`, `test_permits_counted` and `test_console_expired` | the four doubles, for a real `Server`, `Store`, `CacheFiles` and queue; the provider's answers from the scripted AI (6.9 item 4); `test_tail_asked`'s `verbose.tail` answered by the scripted server, and `test_permit_denied`'s `permit.ask` by the scripted UI (6.9 item 3) |
| `test_agent` | worker | whole | the five doubles, for a real `Store`, `ClientSet` and queue; the turns the test fed by hand, for the scripted AI answering with the castle turn's frames of the gold (6.9 item 4) |
| `test_worker_ai` | UI | whole but `test_console_opened` | `PortDouble`, for a real `LocalPort`; `TasksDouble`, for a real synchronous queue; `register_route`, for the real dispatch; `WireDouble`, for the test's own end function (4.3); the settings relay answered by the scripted server (6.9 item 3) |
| `test_boot` | UI | whole | none |
| `test_integrate_media` | UI | new, and `TestCacheEviction`: `media.store` and `media.fetch` lines, real decode, real fetch from the server of 3.10 | none |
| `test_integrate_substrate` | worker | new: the store lines of the ui-ai lane, their replies and their commit pushes | none |
| `test_integrate_tools_browser` | worker | new: `mcp` tool calls through a real `Server` on a real queue | none |
| `test_integrate_agent` | worker | new: `ai.say` and `ai.click`, the provider a `ScriptPort`, the tool calls through a real `ClientSet` to `tools_browser` on a real `mcp.Server` and the real `Store` | none |
| `test_integrate_console_view` | UI | new: `console.show`, `console.output` and `console.exit` | none |
| `test_integrate_page` | UI | new: the ai-ui lines `page.handlers_register` serves, the DOM read back | none |
| `test_integrate_worker_ai` | lanes | new: `tap_start` in a fresh worker as the headless bring up runs it, `tap.start` answered, `settings.set` sent, a `settings.put` relayed to the scripted server and answered, a UI `fault` sent on as an `error` line (6.9 item 5) | none |
| `test_substrate_crash` | workers | `test_substrate_store`'s `TestCrash.test_kill_between`, removed by 6.5: a put held inside its transaction, its worker terminated, then a second worker on the pool and slots the first left (6.11 item 5) | none |
| `test_agent_faults` | workers | `test_agent`'s eight fault tests, unplaced by 6.6: each fault of the agent's real queue in a worker of its own (6.11 item 6) | none |

The side `lanes` is a block run on the page's main thread over a fresh
worker that the real `boot.headless_worker` brings up (6.9 item 5). The
side `workers` is a block run on the page's main thread over a fresh
worker for each case, which the page terminates before the next (6.11).
`test_worker_ai` runs on the UI side, a page load of its own, where no
`tap_start` has registered the types it registers (6.9 item 3.3). Until
2026-10-30 the row of `test_integrate_worker_ai` read "store lines
answered, commits pushed": `tap_start` registers no store, so no store
line reaches the bring up's queue.

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

1. Owns the B phases of `python/test_all.py` under the lock, and
   `ts/test_headless.ts` for any fix of the bring up, shared with 6.9.
   Needs 5.7, 5.11, 6.1, 6.2 and 5.6, all done, and the archives, fetched
   since Question T6 (3.14).
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
   mid-transaction from the driver, or is removed by 4.6. Correction of
   2026-10-30 (log `tmp/tasks_29_1354.md` items 33.4 and 33.9.1): the page
   terminates the worker, not the driver, and the crash test, removed from
   `test_substrate_store` by 4.6, comes back as the block
   `test_substrate_crash` of 6.11. The driver sees only the page, through
   DevTools, and ends a realm by the next page load, which ends the page and
   all its workers at once; only the page holds the `Worker`, and the crash
   test must terminate one worker and bring up a second one on what the
   first left, within one block and inside its comparison.
3. Done as 5.8 item 4.

6.6 Doubles out on the worker side, the top: `tools_browser`, `agent`, and
`media`'s line cases. `worker_ai` and its line cases went to 6.9 on
2026-10-30.

1. Owns those suites, `test_integrate_tools_browser.ts`,
   `test_integrate_agent.ts`, `test_integrate_media.ts`, and the modules
   for any fix. Needs 6.2, 6.5 and Question T5. The far ends of 6.9 items 3
   and 4 are a pattern each suite builds for itself (10.5), so 6.6 does not
   wait on 6.9.
2. The changes of table 6.0. The scripted AI drives the agent's turns:
   `test_agent` on a second real queue whose `http.request` handler answers
   with the castle turn's frames of the gold, and `test_integrate_agent` on
   a `ScriptPort` (4.4, 6.9 item 4). `test_tail_asked` stays in
   `test_tools_browser`, its `verbose.tail` answered by the scripted server
   of 6.9 item 3.1, and so do `test_permit_denied`, its `permit.ask`
   answered by the scripted UI of the same item, and `test_debug_off`. The
   tests that go to C are recorded (7.1). The agent's eight fault tests,
   each of which fails the agent's queue, are placed by 6.11 item 6 in the
   block `test_agent_faults`, a fresh worker for each: `TestErrors`'
   `test_arguments_unparsed`, `test_arguments_overflow`, the four kinds of
   `test_arguments_invalid`, `test_reply_empty`, and a tool that throws
   mid-round, which 6.6 listed with them (log item 33.8).
3. Done as 5.8 item 4.

6.7 The integration suites of B are written by 6.4 to 6.6, each by 3.6.

6.8 The B order and the run.

1. Owns the lists of B's blocks in `python/test_all.py`, and on
   2026-10-30 also the limit of a B block (item 4) in `python/test_all.py`
   and `python/devtools.py` with its stub and `python/test_devtools.py`,
   `ts/test_error_overlay.ts` (item 5), and the case of item 6 in
   `test_integrate_page`'s gold. Needs 6.3 to 6.6 and 6.9.
2. As 5.11 and 5.12 for B: by layer, alphabetical within, B unit then B
   integration (item 7).
3. Done when the Python phases, A and B pass inside 120 s, in both
   categories. Planning ends here (section 7).
4. One limit for a B block (log `tmp/tasks_29_1354.md` item 33.1). Until
   2026-10-30 each DevTools wait of a block, the load of its page, the
   `Runtime.evaluate` of `realm_start`, which runs a UI block whole, and
   the wait for each next line, ended after the 60 s `devtools.py` chose,
   so a block was cut at 60 s, under the 120 s of the gold's
   `module_seconds`, by a number no gold holds. Now the block's alarm
   plan, the gold's `module_seconds` cut at the smoke run's deadline by
   `category.alarm_plan`, is the one source: the driver arms the block's
   alarm with it and hands the same end to the browser by the new
   `devtools.ProtocolClient.limit_set(end)`, stub first, which ends every
   later wait at that end alone, in place of the wait's own seconds. A
   wait that reaches it fails as "gave up at the deadline waiting for"
   what it waited for, and the alarm, due at the same instant, names the
   block. The bring up before the first block keeps the waits of
   `devtools.py`, outside every block's timer, as 6.3 has it.
5. The faults of `test_error_overlay` (log item 33.7). The real
   `document.write` of a case erases the page's window listeners, those
   `error_overlay.overlay_install` adds, measured by 6.4 and again here:
   an event listener that throws in the block's last case, after the first
   replacement, left the block passing, its fault reported nowhere. Every
   case of `TestOverlay` replaces the document, so no order runs them all
   before a replacement, and a listener added before a replacement goes
   with it. So right after each call by which a case writes the fault
   screen, the case installs the page's handlers again by
   `error_overlay.overlay_install`, the call the bring up makes, which adds
   nothing where a handler still stands, as the DOM adds a listener once.
   A later fault is then the realm's own: the page's fault screen takes it
   and the stop function sends the driver the `error` line of its cascade,
   which fails the block at once (6.3). Done when a case broken on purpose
   that way fails the block within its first second, with its message.
6. `test_media_fetched` back (log item 33.9.2): it reached `page.media_take`
   for `media.fetch` and the blob branch of `page.media_done`, and 6.4
   removed it since the driver's server sends text bodies. A result that
   arrives after its call is a line case (3.7), so it comes back as the
   case `fetched` of `test_integrate_page`, its last, so that the ids the
   page's queue gives its own requests in the earlier cases do not move: a
   `media.fetch` line sent on the AI lane, which the page passes to its
   real `media.MediaPort`, which downloads the image from the driver's
   server, and its reply expected with the image's bytes as its blob,
   compared by size and SHA-256 (3.6 item 3). The image is the BMP of
   `test_integrate_media`, 70 bytes all below 0x80, which pass through the
   UTF-8 bodies of `python/local_http.py` unchanged, with no change there.
   The block gets a server of its own in `_SERVED`,
   `typescript.test_integrate_page.server` on 127.0.0.1:28749, closed port
   28750, which also serves its page, so the fetch is of the page's own
   origin.
7. The layers, by 5.11 item 5's method, from the graph the TypeScript
   5.2.2 compiler API resolves over both configs: M calls into N when M's
   code references a top level name of N's file, a type-only reference
   not counted. No two modules call into each other. As in A, the TS
   producer, `tap_producer` and `unittest`, is layer 0 and runs in every
   block, a block of line cases also runs `line_case`, the start-up of the
   headless realm, `test_headless` and `boot.headless_worker` with what it
   calls, is bring up and counts for no block, as the Node runner's does,
   and an integration block follows the unit and the integration blocks of
   the modules that run inside it. For B:
   1. A block of B follows every unit block of a module it calls into, in
      A and in B; a block of A only those of A, since B runs after it.
   2. `test_integrate_worker_ai` calls into `worker_ai`: its cases are
      `tap_start`'s lines, though no line of its file names the module.
      So do `test_substrate_crash` and `test_agent_faults` of 6.11, whose
      cases expect `tap_start`'s Empty reply; and `test_substrate_crash`
      runs `test_substrate_store.kill_put` and `kill_check`, so it calls
      into what they call, `queue` among them.
   3. The blocks of one module do not order each other, as the three of
      `provider` share a layer in A, but an integration block follows the
      unit blocks of its own module. So `test_substrate_crash` and
      `test_integrate_substrate`, both integration blocks of `substrate`,
      and `test_agent_faults` and `test_integrate_agent`, both of `agent`,
      are ordered only by their other edges and the alphabet, and every
      other integration block that runs the real `Store`, such as
      `test_integrate_tools_browser` and `test_integrate_agent`, follows
      both of `substrate`'s.
   4. Where two blocks each call into the other's module, one edge goes.
      An edge from a module's own code yields to the edge a test adds
      back, and where both are added the order of the modules' unit
      blocks decides. So `test_jslb_decode`, which hands the decoder a real
      `CacheFiles`, follows `test_substrate_store`, as 5.8 item 2 has it,
      since `substrate` calls only `jslb`'s builders and field readers,
      which A's `test_jslb` tests; and `test_integrate_page` follows
      `test_integrate_console_view`, since `test_page` runs `console_view`
      and `test_console_view` runs no `page`. `test_tap_producer` and
      `test_unittest`, the third such pair, both stay in layer 0.
   5. `test_page` calls into `console_view`, `overlay` and `media`, whose
      real parts it runs (log item 33.6).
   6. The layers of A come out as 5.11 item 5 gives them, and those of B
      continue the count, over the lists of the run, which leave out
      `test_substrate_crash` until the maintainer answers (6.11 item 10).
      Back in the run it is layer 11, and puts `test_integrate_page` and
      `test_integrate_tools_browser` in layer 12 and `test_agent_faults`
      and `test_integrate_agent` in layer 13:

   | Layer | B unit | B integration |
   | --- | --- | --- |
   | 1 | `test_error_overlay`, `test_error_overlay_worker` | |
   | 3 | `test_overlay` | |
   | 7 | `test_substrate_store` | |
   | 8 | `test_jslb_decode` | |
   | 9 | `test_console_view`, `test_media_cache`, `test_script`, `test_worker_ai` | `test_integrate_substrate` |
   | 10 | `test_page`, `test_tools_browser` | `test_integrate_media`, `test_integrate_worker_ai` |
   | 11 | `test_agent`, `test_boot` | `test_integrate_console_view`, `test_integrate_tools_browser` |
   | 12 | | `test_agent_faults`, `test_integrate_agent`, `test_integrate_page` |

8. Status, 2026-10-30: done, with no fix of a product module.
   1. `--stream`, `--normal-test --stream` and `--tty --stream` each pass
      107 of 107 blocks, 1719 points: 59 Python blocks of 820 points, A's
      27 of 512 and B's 21 of 387. The smoke run takes 59.5 s from start
      to end, inside its 120 s, 55.3 s of it inside the block timers:
      Python 24.6 s, A 7.9 s, B 22.8 s, `test_jslb_decode` the slowest
      block at 7.5 s. The normal run takes 59.5 s, the tty run 66.5 s.
   2. Item 4: `ProtocolClient.limit_set` with its test
      `TestClient.test_limit_alone` in `python/test_devtools.py`, which
      waits past the client's own wait to the limit; `PageRunner.block_run`
      takes the block's end from `stream_run`.
   3. Item 5: a listener that throws in the last case, after six
      replacements, passed the block before the change and fails it after,
      at once, the `error` line holding "broken on purpose" and its stack;
      the same in `test_reload_button` right after its own write. The file
      was restored and its SHA-256 checked.
   4. Item 6: `fetched` passes on its first run, its reply equal to the
      gold. One pixel byte of the served BMP changed on purpose failed it
      with the reply's other SHA-256; the gold was restored and its
      SHA-256 checked.
   5. Item 7: `test_substrate_crash` and `test_agent_faults` of 6.11
      landed while this task ran; 6.8 placed them by item 7, and
      `test_substrate_crash` then left the run (6.11 item 10).

6.9 The scripted server lane (3.9), asked for by the maintainer on
2026-10-30, written here before any code. No product code changes for it
beyond 3.11 item 4, which is done.

1. Owns `ts/test_worker_ai.ts` and the new `ts/test_integrate_worker_ai.ts`,
   both taken from 6.6, their gold, and the side `lanes` of
   `ts/test_headless.ts`, shared with 6.3 under the lock. Needs 6.2, and
   6.3 to run its blocks.
2. What the AI worker's lane to the server carries, by `API/ts/lines.d.ts`
   and the code that sends each line:
   1. Requests the worker sends, each waiting on the server's reply:
      `settings.put`, from the relay of `worker_ai.settings_register`,
      answered Empty; `verbose.tail`, from the tool `verbose_tail` of
      `tools_browser`, answered with a `VerboseTailReply`; and `tap.run`,
      `source.put`, `echo` and `system.restart`, which only the wire rungs
      of `ts/test_wire_rungs.ts` send, to test the real server through
      ttyd.
   2. Pushes the worker sends: `tap.line`; `verbose.put` in debug mode,
      each entry holding a clock reading in `at`; the store's commits, once
      a store is registered, which `tap_start` does not do; and an `error`
      line with a cascade, through the end function.
   3. Lines the server sends: `tap.start`, which the headless worker takes
      from its page's first message, not from the lane, and answers on the
      lane with an Empty reply whose `r` is 101; and the pushes
      `db.restore` and `db.file`, which `substrate`'s handlers take.
3. The far end of a unit block, in the module's own realm, by the pattern
   of 5.9 item 2: the module's real synchronous queue holds its `server`
   lane as one of a linked pair of `queue.LocalPort`s (4.7), so the whole
   exchange runs within the test's call.
   1. Where the module's side handles none of the types the far end must
      handle, the far end is a second real `queue.TaskQueue` of thread
      `server` in synchronous mode holding the other port, whose handlers
      are the test's functions (4.3), registered once per realm by
      `dispatch.handler_register`, each answering its request by
      `dispatch.reply_make` with the payload of the reply line the block's
      gold scripts: `verbose.tail` with `tail_reply`, in `test_tools_browser`'s
      `test_tail_asked`. The same far end on the `ui` lane, of thread `ui`,
      answers `test_permit_denied`'s `permit.ask` with `permit_deny`.
   2. Where the module's side handles the same type, the far end is the
      test's own receiver of the other port (4.3), which keeps each line
      and posts the gold's reply to a request: `settings.put` in
      `test_worker_ai`'s `test_settings_sent`, which the AI thread's relay
      takes from the UI and the server answers, both at version 0. A realm
      has one dispatch table, which refuses a second registration of a type
      and version, so a second queue in that realm cannot hold it.
   3. `test_worker_ai` runs on the UI side, a page load of its own. In a
      headless worker the bring up's `tap_start` has registered
      `settings.put`, `worker.settings_put`, `fault` and `worker.tests`
      before the block runs, so a test that registers them through the real
      dispatch runs only in a realm where `tap_start` never ran. No piece
      the block tests but `tap_start` needs a worker.
4. The scripted AI (4.4) is the far end of the provider's owner, by the
   same pattern. For `test_agent` and `test_tools_browser`'s `TestImages`:
   a second real queue of thread `http` whose `http.request` handler is the
   test's function, which checks each request against the gold's frame and
   answers with the gold's reply frame, in order: the castle turn's four
   chat answers, or the image answer. For `test_integrate_agent`: a
   `provider_script.ScriptPort`, whose script walks the turn. The driver's
   server of 3.10 answers one reply per path, so it scripts single
   exchanges, as in `test_integrate_http`, and not a turn of several chat
   requests on one path. The agent's tool calls go through a real
   `ClientSet` to `tools_browser` on a real `mcp.Server` and the real
   `Store`. The bring up registers no agent, store or tools, so no AI turn
   runs in `test_integrate_worker_ai`: the AI's turns of B are the agent's
   blocks.
5. The far end of the bring up, `test_integrate_worker_ai`, on the
   headless page's main thread, a realm whose dispatch table holds none of
   the worker's handlers:
   1. `test_headless`'s block table gains the side `lanes`, a block run on
      the page over a fresh worker. Its entry is `{side: "lanes", lanes:
      LanesBuild}`, with `type LanesBuild = (first: lines.Line, server:
      MessagePort, ui: MessagePort, relay: (line: lines.Line) => void) =>
      queue.ThreadPort`. For it `realm_start` sets the settings and the
      harness's values and answers the driver's `tap.start` as `main_run`
      does, brings up a fresh worker by the real `boot.headless_worker` as
      `worker_launch` does, with the same start, and runs
      `line_case.block_run` on the page with the topology `() =>
      block.lanes(first, server, ui, line_write)`, `server` and `ui` the
      page's ends of the worker's two channels. The page writes the TAP;
      the worker's `worker_run` runs no block for a `lanes` block.
   2. `test_integrate_worker_ai.lanes_build` joins the test's end to both
      channels by real `queue.ThreadPort`s whose receivers are the block's
      functions (4.3). Every line of the server lane goes to the test's
      end, but `verbose.put`, which goes to `relay`, to the driver, as the
      page relays it now, uncompared, since its clock readings fit no gold;
      a request also goes to the far end. The UI channel's `settings.set`,
      whose payload is all of `tap.start`, `test_settings.json` included,
      and so cannot be a line of the gold, is compared with `first` by
      value, a difference thrown. A line the cases send goes on the UI
      channel.
   3. The far end is a second real `queue.TaskQueue` of thread `server` in
      synchronous mode in the page's realm, joined to the junction of item
      5.2 by a linked pair of `queue.LocalPort`s, whose handlers are the
      block's functions answering each request with the gold's reply:
      `settings.put` with `settings_put_reply`. Its replies go to the
      worker on the server lane.
   4. The cases, in order: `started`, the Empty reply to `tap.start`, `r`
      101, expected; `settings_relayed`, a UI `settings.put` notice sent,
      its relayed request expected, `i` 1, measured, since a queue numbers
      its own requests from 1, which the far end answers; correction of
      2026-10-30: this item read `i` 102, as the ids of `dispatch.id_next`
      start (3.2), which the relay does not use; `fault_relayed`, a UI
      `fault` sent, the
      `error` line of its cascade expected, last, since the worker then
      closes itself.
   5. Lines of two MessageChannels keep no order between them, so no case
      expects lines of both channels.
6. The tests of 7.1 items 3, 4 and 6, as this task places them:
   1. To B by the scripted server: `test_worker_ai`'s `test_settings_sent`,
      by item 3.2, and the same relay at bring up, by
      `test_integrate_worker_ai`'s `settings_relayed`; `test_tools_browser`'s
      `test_tail_asked`, by item 3.1, in 6.6.
   2. To B with no far end of the server: `test_worker_ai`'s
      `test_console_closed`, which closes through the test's own function
      and is answered at once, on a real synchronous queue; `TestFaults`,
      `test_error_sent` and `test_fault_sent`, whose WirePort became an end
      function, the test's own (3.11 item 4, 4.3); `test_tools_browser`'s
      `test_permit_denied`, by the scripted UI of item 3.1, and
      `test_debug_off`, which reads debug mode through the settings reader
      its test hands `tools_register` (4.3) and sends nothing, both in 6.6.
   3. In C: `test_worker_ai`'s `test_console_opened`, and
      `test_tools_browser`'s `test_console_recorded`, `test_permit_always`,
      `test_permits_counted` and `test_console_expired`, which need the
      console on tty 0 (10.7); `tap.run`, `source.put`, `echo` and
      `system.restart` with its new `tap.start`, which only the wire rungs
      send (10.8); and `db.restore` with `db.file` of a database the real
      server's store wrote. The lines and the restore themselves run in B
      already, in `test_substrate_store`'s `test_restore_answered`, on a
      snapshot of the real store.
7. Departures from the coordinator's design of 2026-10-30 (log
   `tmp/tasks_29_1354.md` item 30.4), class B, each with its cause (11.2
   item 12). That design had a worker block hand `tap_start` one end of a
   ThreadPort pair, the other end a second real queue in the same realm,
   answering `settings.put` among others. A block cannot hand `tap_start`
   its lane (3.11 item 4). A far queue on `tap_start`'s lane would get its
   Empty reply to `tap.start`, a request that queue never submitted, which
   a `queue.TaskQueue` refuses with `queue.reply_unknown`, so the junction
   of item 5.2 takes that reply. A far queue in the worker's realm cannot
   hold `settings.put`, by item 3.2. So the bring up's far end is on the
   page, and a far end in the module's own realm is a second queue only by
   item 3.1. The task starts once the coordinator confirms them.
8. Done when both configs compile, `test_worker_ai` and
   `test_integrate_worker_ai` pass in the B phases, and no block of the
   task holds a double or changes a module's state.

6.10 The survey of 2026-10-30: every test removed, deferred, or put in C
for want of a stand-in for the AI API or for the server's answer, which
the rule of 4.4 and the far ends of 3.9 now admit, each planned back into a
block, or kept out with its cause.

1. Put in C for want of the server's answer: 7.1 items 3, 4 and 6, placed
   by 6.9 item 6.
2. Given no far end of the provider in table 6.0: `test_agent`, whose turns
   the test fed by hand as gold wake lines, and `test_tools_browser`'s
   `TestImages`, whose image answers it fed the same way. With a real queue
   each needs the provider's answer, which the scripted AI of 6.9 item 4
   gives, in 6.6.
3. The AI's turns with tool calls reaching the real store: `test_agent`, on
   the scripted `http` queue, and `test_integrate_agent`, on a
   `ScriptPort`, both through a real `ClientSet` and `tools_browser` on the
   real `Store` (6.9 item 4). `test_integrate_worker_ai` holds none, since
   the bring up registers no agent; its server lane is scripted by 6.9 item
   5.
4. Removed by 5.10, for a cause made up in a platform's text:
   `test_http`'s `test_failure_text`, `test_failure_other`,
   `test_timeout_distinct` and the failure half of `test_error_full`,
   reaching `HttpExchange.failure_reply`; and `test_media`'s
   `test_decode_text`, `test_decode_other`, `test_download_text`,
   `test_messages_distinct` and the decode and download halves of
   `test_error_full`, reaching `MediaExchange.decode_reply` and
   `download_reply`. They stay removed: the rule of 4.4 admits a scripted
   AI, and a fetch's or a decoder's failure text is the platform's, not the
   AI's. Their real failures are cases of `test_integrate_http`, where the
   driver's server answers as the AI API: `fetch_refused`,
   `timeout_expired`, `status_failed`, `json_malformed` and
   `json_overflow`; and of `test_integrate_media` (6.6, 10.2).
5. Removed by 4.7: `provider_script.ScriptPort.node()` and the 11
   assertions on it in 8 tests, an export for the tests only and not a
   stand-in. It stays removed; those tests still check every line the
   scripted AI answers.
6. Nothing else of this plan was removed, deferred or put in C for want of
   the AI API: the provider was answered by `ScriptPort` and by the
   driver's server from the first.

6.11 The block side `workers`: a fresh worker for each case, task 33.5 of
the log `tmp/tasks_29_1354.md`, by the coordinator's decision of its item
33.9.1, written here before any code.

1. Owns the side `workers` of `ts/test_headless.ts` and its stub
   `API/ts/test_headless.d.ts`, `HeadlessStart.clear` in `ts/boot.ts` and
   `API/ts/boot.d.ts`, the new blocks `ts/test_substrate_crash.ts` and
   `ts/test_agent_faults.ts`, their gold, and their entries in
   `ts/tsconfig.test.json` and `python/test_all.py`, each shared file
   under the lock. Needs 6.2, 6.3, 6.5, 6.6 and 6.9, done.
2. Why. Two kinds of test need a second worker within one block:
   1. The store's crash test, `test_substrate_store`'s
      `TestCrash.test_kill_between`, removed by 6.5 by 4.6 (log item 33.4):
      it reached `kv_put`, `#row_write` and `bytes_store` with the `_kv`
      insert stopped, then `kv_check`. A real kill needs a second worker
      that keeps the first one's pool and slots, and
      `boot.headless_worker` cleared both at every start.
   2. The agent's eight fault tests, unplaced by 6.6 (log item 33.8):
      arguments that are not JSON, a number that overflows, four kinds of
      JSON that are not an object, an empty reply, and a tool that throws
      mid-round. Each fails the agent's queue, as fail loud intends, and a
      realm holds one agent, which registers its types in the realm's one
      dispatch table, so each needs a fresh worker.
   One mechanism serves both: a block whose page brings up a fresh worker
   for each case in turn, compares that worker's lines with the gold inside
   the block, and terminates it before the next case. A block is its file,
   one file and one table entry per block (log item 33.9.1).
3. `boot.HeadlessStart` gains `clear: boolean`, bring up of the headless
   entry, which the maintainer approved (Question T4). True, the worker's
   bring up clears the test pool and the test slots at start, as before;
   false, it installs the pool with `clearOnInit` false and leaves the
   slots' bytes, so the worker finds what the worker before it left.
   `realm_start` gives `clear: true` to the worker of a `worker` or
   `lanes` block, and `boot.test_worker` always clears. A start with
   `clear` false also holds `wait_seconds`, for the wait of item 11.
4. The side `workers`. The block's table entry is `{side: "workers",
   worker: WorkerRun}`, with `type WorkerRun = (tasks: queue.TaskQueue,
   start: boot.HeadlessStart, ready: () => void) => void`, which runs in
   each fresh worker in place of a TAP block, in the task of
   `worker.tests`, with the bring up's queue, the worker's start, and a
   function that sends the notice `test_headless.worker_ready` to the
   server. For such a block `realm_start` sets the settings and the
   harness's values and answers `tap.start`, as for a `lanes` block, and
   runs `line_case.block_run` on the gold `typescript.BLOCK` with a
   topology that `test_headless` builds itself: the test's end of a real
   `queue.ThreadPort` pair whose other end is the junction, a receiver of
   `test_headless`'s own, which, for each case in turn:
   1. at the notice `test_headless.worker_start`, whose payload is
      `{clear}`, with `wait_seconds` too when `clear` is false (item 11),
      and which each case sends first, ends the worker of the case
      before, by item 4.4, then brings up a fresh worker by the real
      `boot.headless_worker`, as a worker block's is, with the page's start
      and that `clear`;
   2. holds every other line the case sends, in order, and posts each on
      the worker's UI channel once the worker has sent
      `test_headless.worker_ready`, the call of `ready` that its
      `WorkerRun` makes once its topology is up. The reason: a topology
      whose set up takes tasks of the worker's queue, as the MCP client's
      handshake does, would otherwise take the case's lines before it is
      up, since the queue runs its lines in the order they come, and a line
      the page posts at the bring up comes before those tasks. A case that
      sends the worker no line needs no `ready`;
   3. passes on to the test's end every line of the worker's server lane,
      the Empty reply to `tap.start`, the `ready` notice and the `error`
      line of a fault among them, but each `verbose.put`, which goes to the
      driver uncompared, as a worker block's does, since its entries hold
      clock readings; and every line of its UI channel but its
      `settings.set`, which goes to the driver, as a worker block's does,
      since its payload is the whole of `tap.start`. The worker's `fault`
      line, which its error overlay posts after the report and which keeps
      no order with the server lane, is held by the junction and checked
      against the worker's `error` line: the same message, stack and
      `cause` chain. A `fault` line that differs, or that came with no
      `error` line by the time the worker ends, goes to the driver, which
      fails the block with its cascade (6.3);
   4. ends a worker by `Worker.terminate`: at once, unless it sent an
      `error` line whose `fault` line has not come, then as soon as it
      comes. The page terminates it, not the driver, since only the page
      holds the `Worker`, and a case must end one worker and bring up the
      next within the block, inside its comparison; the driver ends a whole
      realm by the next page load (6.3). The last worker is ended the same
      way at the block's end, before the stream's last line.
   A case's lines go to the worker and its expected lines come back from
   the server lane alone, which keeps its order (6.9 item 5.5). The page
   writes the TAP. A worker's `error` or `fault` line never reaches the
   driver, which would fail the block, unless item 4.3 sends it there.
5. `test_substrate_crash`, a block of the side `workers`, gold
   `typescript.test_substrate_crash`. Its `WorkerRun` makes a real
   `substrate.Store` on the realm's sqlite3 module and pool, the root of
   its gold, a cache over the test slots, the `overflow_bytes` and
   `turn_compact_turns` of `settings.json`, and the bring up's queue as
   the store's queue, so its pushes go on the server lane. With `clear`
   true it runs `test_substrate_store.kill_put`, whose `paused` sends this
   block's notice `test_substrate_crash.paused` to the server; with `clear`
   false it runs `test_substrate_store.kill_check` and sends the notice
   `test_substrate_crash.checked` with its `rows` and `removed`. The
   cases:
   1. `put_held`: the start with `clear` true; expected, the Empty reply,
      the `db.create` push of `alpha`, and `paused`. It reaches
      `db_create`, then inside `transaction_run` `kv_put`, `#row_write` and
      `bytes_store` of a value over `overflow_bytes`, the `_kv` insert not
      committed, and the worker is held in `kill_hold`'s loop until the
      next case's start terminates it.
   2. `orphan_removed`: the start with `clear` false; expected, the Empty
      reply and `checked` with `rows` 0 and `removed` 1. It reaches the
      pool's install with `clearOnInit` false over the files of the killed
      worker, SQLite's rollback of their hot journal at `db_open`,
      `kv_list`, and `kv_check` removing the cache file no row names.
6. `test_agent_faults`, a block of the side `workers`, gold
   `typescript.test_agent_faults`. Its `WorkerRun` registers the agent on
   the bring up's own queue, the AI thread's real queue, with a real
   `Store` on the realm's sqlite3 module and pool over the test slots, the
   queue as its queue, so its pushes go on the server lane; a real
   `mcp.ClientSet` whose client reaches `tools_browser` on a real
   `mcp.Server` over the same store; and the scripted AI (4.4), a
   `provider_script.ScriptPort` that the queue owns as `http`, walking the
   gold's `script`, whose start node answers each input with one case's
   reply. It writes the hyperposition the agent reads: the database
   `metaverse`, its universe table, its world, its scene and the
   analyst's prompt; runs the client's handshake by its own handlers; and
   at the handshake's end calls `ready`. Each case sends the start with
   `clear` true, then an `ai.say` request whose text is the case's input,
   as the UI thread sends it on its channel, and expects the Empty reply,
   the hyperposition's pushes, `ready`, the `turn.append` push of the
   player's text, then the `error` line of the queue's fault, compared by
   its message and the first line of each stack down its `cause` chain
   (3.6 item 3), which is the error's name and message. No case expects a
   reply to `ai.say`, since each turn ends in the fault. The cases:
   1. `arguments_unparsed`, input 1: a tool call whose arguments are `{`;
      `agent.arguments_invalid` over `jslb.text_not_json` over the
      platform's SyntaxError. It reaches `call_submit`'s
      `jslb.json_decode` and `utility.error_wrap`.
   2. `arguments_overflow`, input 2: arguments `{"subtitle":1e400}`;
      `agent.arguments_invalid` over `jslb.number_overflow`. It reaches
      the decoder's refusal of a number that overflows a double, the one
      door for bad numbers.
   3. `arguments_array`, `arguments_null`, `arguments_number` and
      `arguments_string`, inputs 3 to 6: arguments `[]`, `null`, `5` and
      `"Fog."`; `agent.arguments_invalid` with no cause. They reach
      `call_submit`'s check that the arguments are an object.
   4. `reply_empty`, input 7: a reply with neither tool calls nor
      content; `agent.reply_empty` naming the reply's id. It reaches
      `model_handle`'s end of a turn.
   5. `tool_thrown`, input 8: a reply that calls two tools, first
      `browser.kv_put` of a key of `metaverse`, which commits and pushes,
      then `browser.kv_get` of a key `metaverse` lacks, which throws; its
      expected lines hold the `kv.put` push before the `error` line of
      `substrate.key_missing`, and no `turn.append` of the round. It
      reaches `mcp.Server`'s `tool_run`, its `isError` answer in a
      `dispatch.Failure`, and the queue's `failure_raise`; the round's
      reply and results are never stored, since `tool_handle` never runs.
7. The order, by 6.8 item 7: each case expects the Empty reply that
   `worker_ai.tap_start` sends, as `test_integrate_worker_ai`'s do, so
   both blocks call into `worker_ai`; both are blocks of line cases, so
   both run in B's integration phase (3.5). `test_substrate_crash` calls
   into `substrate`, `queue`, `line_case` and `worker_ai`, so it follows
   `test_integrate_worker_ai`, layer 11. `test_agent_faults` calls into
   `agent`, `mcp`, `tools_browser`, `substrate`, `provider`,
   `provider_script`, `queue`, `line_case` and `worker_ai`, so it follows
   `test_integrate_agent`, layer 13. Correction by 6.8 on 2026-10-30, by
   6.8 item 7.3: two integration blocks of `agent` do not order each
   other, and `test_integrate_tools_browser` and `test_integrate_agent`
   follow `test_substrate_crash`, an integration block of the `substrate`
   they run, so `test_integrate_agent` is layer 13 too, after
   `test_agent_faults` by the alphabet; with `test_substrate_crash` out of
   the run (item 10), both are layer 12 (6.8 item 7.6).
8. The ttyd page: neither block goes on the lists of `ts/test_all.ts` or
   `python/test_browser.py`. The ttyd page runs unittest modules in one
   realm per thread and has no side but its two threads, and both blocks
   are line cases of a side only the headless page has; group C is not
   run and its page stays as it is (7.2).
9. Done when both configs compile, both blocks pass with `--module`, each
   worker block of B still passes after the change to `boot`, a deliberate
   break of each case fails it, and the whole `--stream` passes.
10. Status, 2026-10-30: `test_agent_faults` done, `test_substrate_crash`
    written and out of the run, waiting on the maintainer.
    1. `test_agent_faults` passes 8 of 8, in about 2 s, alone and in the
       whole `--stream`, which passes 107 of 107 blocks; each case broken
       on purpose in its own gold line failed, and the gold was restored
       byte for byte. The thirteen worker blocks of B pass after the
       change to `boot`. No product module changed but `boot` for `clear`.
    2. `test_substrate_crash`'s `put_held` passes, and fails when broken.
       `orphan_removed` cannot pass as item 5 has it: the second worker's
       bring up fails at once with the platform's `NoModificationAllowedError`,
       "Access Handles cannot be created if there is another open Access
       Handle", since the first worker's OPFS handles are still held.
       Measured in `chrome-headless-shell` 156 on a page of its own: a
       worker busy in a loop, as `kill_hold` is, is torn down by the
       platform about 2.0 s after `Worker.terminate`, and its handles are
       free about 2.05 s after it, whether or not it took a Web Lock first;
       a Web Lock it held is freed about 50 ms before its handles, in each
       of three runs; an idle worker's handles are free within about 10 ms;
       and a `MessagePort` has no `close` event there. So no event of the
       platform tells the page or a worker that a killed worker's handles
       are free: only an open that succeeds does. Every other block of B
       ends its workers idle, so their handles are free long before the
       next worker opens them.
    3. So the block is out of `_B_INTEGRATION` until the maintainer
       chooses how the second worker waits for the first one's handles
       (log item 33.5's report). The ways measured: the bring up of a
       worker started with `clear` false opens the pool and the slots
       again while the platform refuses them with
       `NoModificationAllowedError`, until they open or the case's
       seconds are up, as SQLite's own OPFS file system retries a locked
       handle, a change to `boot` beyond `clear`; or the page brings up
       the second worker once a Web Lock the first one held is freed,
       which leaves the 50 ms between the lock and the handles to the
       second worker's bring up; or a case that ends the first worker and
       expects no line waits its seconds, longer than the measured 2.05 s;
       or the crash test stays removed by 4.6. The file, its table entry
       and its gold stay, so that the chosen way runs it.
11. The wait for a killed worker's files, decided by the coordinator on
    2026-10-30 as the first of the ways of item 10.3 (log
    `tmp/tasks_29_1354.md` item 33.12), written here before any code.
    1. Why: by the measurements of item 10.2, only an open that succeeds
       tells that a file a killed worker held is free. A Web Lock is freed
       about 50 ms before the files and a `MessagePort` has no `close`
       event, so every other signal leaves a race.
    2. Where: before the pool is installed. The pinned SQLite keeps a
       failed `installOpfsSAHPoolVfs` as the answer to every later
       install of the same name, read in its `sqlite3.js`, so the install
       cannot be tried again; and a failed install may leave handles open
       that it took before the refusal. So `boot.headless_worker`, given a
       start with `clear` false, first waits until each file of the test
       pool's directory, those of its subdirectories included, and of the
       test slots' directory opens: it opens a handle for synchronous
       access on each in turn and closes it at once, and then installs the
       pool with `clearOnInit` false and opens the slots as before.
       Measured: after the open and close of every file, opening all of
       them for keeps succeeded in each of three runs, and a close
       followed at once by an open of the same file never failed in 1500.
    3. What it catches: only the platform's refusal of a held file, a
       `DOMException` whose `name` is `NoModificationAllowedError`, the
       name every refusal had in the runs of item 10.2. That refusal ends
       the try, which comes again after 10 ms; anything else is thrown at
       once. The interval: a try of the pool's and the slots' files took
       about 3.5 ms, and the files came free about 2.05 s after
       `Worker.terminate`, so a try every 10 ms ends the wait within 10 ms
       of the files' release at about a third of the time in tries.
    4. Its end: `boot.HeadlessStart` with `clear` false holds
       `wait_seconds`, the seconds the wait may take, from the start
       notice of the case, which then carries `{clear: false,
       wait_seconds}`; a start with `clear` true holds none. When a try is
       refused after `wait_seconds`, the bring up throws `boot.files_busy`
       with the last refusal as its `cause`, which the worker's error
       overlay sends as its `fault` line and the page sends to the driver
       (item 4.3). The gold gives `orphan_removed` a `wait_seconds` of 5,
       over twice the measured 2.05 s, under the case's 10 s, so that the
       throw comes within the case.
    5. Only a start with `clear` false reaches the wait, and only the
       second worker of `test_substrate_crash` gives one, so no other
       bring up changes. The block goes back into `_B_INTEGRATION` by the
       layer table of 6.8 item 7.
    6. To overturn: the fourth way of item 10.3, the crash test removed
       by 4.6 again, takes the wait, `wait_seconds` and `boot.files_busy`
       out with the block.
    7. Status, 2026-10-30: done. `test_substrate_crash` passes 2 of 2 in
       both categories, about 2.5 s in its timer, the wait about 2 s of
       it; `orphan_removed` failed when its gold `removed` was broken, and
       with `wait_seconds` cut to 1 the bring up threw `boot.files_busy`
       over the platform's `NoModificationAllowedError`, which reached the
       driver; the gold was restored byte for byte each time. The block is
       back in `_B_INTEGRATION` by 6.8 item 7, layer 11, `test_integrate_page`
       and `test_integrate_tools_browser` in layer 12 after it, and
       `test_agent_faults` and `test_integrate_agent` in layer 13. The
       thirteen worker blocks of B and the whole `--stream`, 108 of 108
       blocks, pass.

## 7 Group C: the limit

7.1 What no headless realm without a tty can run, by 3.9:

1. `wire.WirePort.wire_open`, its socket send and drain, `wire_end` and
   `wire_close` on an open socket (`TestWireEnd`), and `ConsolePort`'s open
   and input: ttyd's WebSocket protocol on tty 1 and tty 0.
2. `test_wire_rungs.ts` and `python/test_wire.py`: every rung waits on the
   server through ttyd, and two drive dash on tty 0.
3. `test_worker_ai`'s `test_console_opened`, which needs the console owner
   on tty 0. The rest of `TestRelays`, and `TestFaults`, moved to B on
   2026-10-30 (6.9 item 6).
4. `test_tools_browser`'s `test_console_recorded`, `test_permit_always`,
   `test_permits_counted` and `test_console_expired`, which need the
   console owner on tty 0. `test_permit_denied`, `test_debug_off` and
   `test_tail_asked` moved to B on 2026-10-30 (6.9 item 6).
5. `console_view`'s open path: `console.open` to the console owner.
6. The requests to the server that only the wire rungs send, `tap.run`,
   `source.put`, `echo`, and `system.restart` with its new `tap.start`; and
   `db.restore` with `db.file` of a database the real server's store wrote.
   `verbose.tail` and the `settings.put` relay are answered by the scripted
   server in B since 2026-10-30 (6.9).
7. `python/test_browser.py`'s rungs, with its probe kit's doubles (2.11).
8. A realm with `debug` false: `tap.start` carries the gold in debug mode
   only (`API/README.md`), so no test can run there. `test_tools_browser`'s
   `test_debug_off`, recorded here as not run until 2026-10-30, runs in B,
   since the tool reads debug mode through the settings reader its test
   hands it (6.9 item 6.2).
9. Plan for C, written on 2026-10-30 and run by nothing now: on the ttyd
   page `test_error_overlay` gets a page load of its own, since its cases
   replace the document, and with it the page's window listeners that the
   UI suites after it on the same page would report their faults through
   (6.8 item 5). Today `test_all.ts` runs it before the later UI suites of
   that page.
10. Plan for C, of the same date: each worker suite on the ttyd page gets a
    fresh realm, as each B block does (3.2). Today the ttyd page's worker
    suites share one worker, where `test_tools_browser` and `test_agent`
    both register `http.request`, `mcp` and the tools' wake types in the
    realm's one dispatch table, which refuses a second registration of a
    type and version.

7.2 Planning stops here. `test_wire.py` and `test_browser.py` stay after
the stream, where `PY_GOALPOSTS.md` 2.13 puts them, and the ttyd page stays
as it is; 7.1 items 9 and 10 are what the plan of C starts from.

## 8 Order and sharing

8.1 Done. On 2026-10-29, while the agents of `PY_GOALPOSTS.md` ran its
wave 3, which passed the same day: 5.2, 5.3, 5.4, 5.8, 5.9 and 5.10,
compile-checked with a tsc borrowed from outside the tree, which no file
names. 23 of the 24 A blocks then in the Node runner's table passed in
Node, 469 tests, run outside the driver; `test_integrate_http` waits for
the server of 3.10. On 2026-10-30 the maintainer answered Questions T1 to
T5, which did 5.1, and the same day 5.5, 5.6, 5.7, 5.11 and 5.12 were
done, so A runs in the official run, and 6.1 and 6.2 were written. After
Question T6 the archives were fetched (3.14), and the whole `--stream` run
passed 86 of 86 blocks, 59 Python and A's 27, 1331 tests, in 34.2 s.

8.2 What follows, in waves, each after the one before; the tasks of a wave
run in parallel, each on the files it owns. Waves 1 to 4 are done.

1. Wave 1, done on 2026-10-30:
   1. The follow-ups of 2026-10-30 in the files of 5.3, 5.8 and 5.10: the
      count at `block_start` (3.7), the stack's first line (3.6 item 3),
      `test_wire_port` and `test_provider_key_unset` into A (5.0),
      `ScriptPort.node()` out (4.7), and the digest vectors (5.8 item 2).
   2. 5.6, the Node bundle; the headless page waits (5.6 item 2).
   3. 5.7.1, the relay and the server.
   4. 6.1 and 6.2, which run beside A's work since they own separate
      files; 6.2 compiles only, since nothing runs a page yet.
2. Wave 2, done on 2026-10-30: 5.7.2, and 5.5 written beside it; 5.5 is
   done once it passes in the run that 5.7.2 builds.
3. Wave 3, done on 2026-10-30: 5.11, then 5.12, one agent;
   `test_integrate_http` passes here.
4. Wave 4, done on 2026-10-30, after the maintainer answered Question T6:
   the archives, fetched by the driver at the start of every run (3.14);
   the headless page of 5.6 with `html/headless.html`; and
   `test_page_build_tsc` taken out of the later suites (`PY_GOALPOSTS.md`
   9.6).
5. Wave 5, in parallel: 6.3, the driver's B phases, first with the blocks of
   table 6.0 that lose nothing, `test_jslb_decode`, `test_overlay` and
   `test_boot`; and 6.4, 6.5, 6.6 and 6.9, which write and compile while
   6.3 brings the B phases up, and run their blocks once 6.3 has landed.
   Each adds its blocks to the B lists under the lock. 6.9 starts once the
   coordinator confirms the departures of 6.9 item 7.
6. Wave 6: 6.8, the B order and the run, then the whole runs in both
   categories and on a tty, two runs of `python/reformat.py` over the whole
   tree, and both configs.

8.3 No B block runs before A passes in 5.12, though 6.1 and 6.2 are
written beside A's tasks. A passed on 2026-10-30.

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
6. `ts/test_headless.ts`: tasks 6.3, 6.9 and 6.11.

8.6 Every run of `python/test_all.py` holds the run lock, since runs share
`build/ts/node.js`, `build/headless.html`, the HTTP server's ports and the
browser: the empty file `tmp/run_lock` renamed with the task number
appended for the run, then renamed back. A missing `tmp/run_lock` is
another task's run, waited for, never recreated. A compile check into
`build/ts_check/<task>/` needs no lock.

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

Question T6: may the agents download the SQLite wasm and xterm.js archives
that the headless page is built from, through `python/third_party_fetch.py`,
which also fetches ttyd's source archive, each checked against its pinned
SHA-256? Asked on 2026-10-29 and again on 2026-10-30
(`tmp/tasks_29_1354.md` items 24 and 28.2.1).

[ ] A. Yes: an agent runs the fetch once, then the waves of B run.

[ ] B. Yes, but the maintainer runs `python3 python/third_party_fetch.py`,
and agents check for the files before starting.

[ ] C. No: B is written and compiled but not run.

Answered by the maintainer on 2026-10-30 in place of A: the agents may
download the third party files through `python/third_party_fetch.py`,
which runs before the third party files are needed, before every test run,
to confirm that the pinned versions are downloaded, with no network traffic
when they already are, and `third_party/` takes a canonical structure
(3.14).

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

10.7 A scripted far end on the console lane is not planned, since what
needs the console on tty 0 stays in C (3.9). Its design, so that it is not
lost: the `console` owner's port is one of a linked pair of
`queue.LocalPort`s; `console.input` and `console.read`, which the AI side
does not handle, are answered by a second real queue of thread `console`
whose handlers answer from the gold, as 6.9 item 3.1 does; and
`console.open`, which the AI side relays from the UI under the same type,
is answered by the test's own receiver, as 6.9 item 3.2 does. It would move
`test_worker_ai`'s `test_console_opened` and the four console tests of
`test_tools_browser`'s `TestConsole` to B.

10.8 The wire rungs, `ts/test_wire_rungs.ts`, stay in C with `test_wire.py`
(7.1 item 2): a scripted server would test their own code against the gold,
not the real server through ttyd, which is their purpose. They alone send
`tap.run`, `source.put`, `echo` and `system.restart`.

## 11 Requirements analysis

The requests are those of this conversation, `tmp/tasks_28_1951.md` item 1,
and the ones of earlier logs that bear on TypeScript: `tmp/tasks_25_1832.md`
item 10.1 and `PY_GOALPOSTS.md` 9.2; and the maintainer's answers of
2026-10-30, with the acceptance of every decision reported to the
maintainer then (`tmp/tasks_29_1354.md` items 21 and 22); and the
maintainer's request and answer of 2026-10-30 (item 29), with the decisions
reported to the maintainer before it (item 28.4) and taken by the
coordinator after it (item 30). A: unsatisfied
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
9. The decisions reported to the maintainer as decided without asking on
   2026-10-30 (`tmp/tasks_29_1354.md` item 28.4), unconfirmed: Chrome
   started by `os.posix_spawn`, its DevTools pipes on descriptors 3 and 4
   and its font cache in its profile under `build/` (6.1); the local HTTP
   server raising its first failure in the driver's main thread at once,
   by a signal (5.7); the headless bring up opening no wire cache (6.2); a
   TS block named by its file in `--module` (5.7); the Python TAP runner no
   longer extending `TextTestRunner`, with no change of behavior; the pair
   test's per-test `setUp` and `tearDown` failures in place of class and
   module fixtures, and the test failing twice left out, its design kept
   (5.5 items 5 and 6); the page build printing its digest only from its
   command line (5.6); the new Python suites in the unit phase,
   `smoke-test`; the Node runner's start-up counted as bring up for no
   block and the TS producer at layer 0 (5.11); every `stack` down an
   `error` line's chain compared by its first line (3.6 item 3); and
   `PY_GOALPOSTS.md` 4.6 no longer naming tsc and Chrome as unapproved.
10. The third party layout (3.14), by the maintainer's request for a
    canonical structure, laid out as the coordinator would use it, since the
    maintainer does not: one directory per library, the ttyd patch under
    `third_party/ttyd/patches/`, and a `.gitignore` that ignores all of
    `third_party/` but the `patches/` directories.
11. The fetch on every run (3.14): `pins_fetch` in process, at the start of
    every run, before the deadline and outside every block timer, as bring
    up; a failed fetch ends the run before the first block.
12. The scripted server lane as 6.9 writes it, with its departures from the
    coordinator's design (6.9 item 7): the bring up's far end on the
    headless page, a new block side `lanes`, a junction of the test's
    functions, and a far end that is the test's own receiver where a type
    is handled on both sides; and `test_worker_ai` moved to the UI side (6.9
    item 3.3).
13. `test_tools_browser`'s `test_permit_denied` into B with a scripted UI
    answering its `permit.ask`, and `test_debug_off` into B (6.9 item 6.2);
    the corrected row of `test_integrate_worker_ai` (6.0); the deferred
    `failed_tests` field of `tap.pair` (5.5 item 6).
14. The tests removed by 4.6 in 6.4 to 6.6, each because no real part
    reaches its path: `test_input_closed` and the refusal halves of
    `test_input_idle`, `test_input_opening` and `test_close_reply`; the
    closing half of `test_show_busy`; the write half of the short I/O test;
    `test_functions_registered`, `test_texts_joined`,
    `test_content_unsupported`, `test_result_failed`, `test_round_answered`,
    `test_error_line` and `test_info_scripted`. Brought back since: the crash
    test as `test_substrate_crash` (6.11) and `test_media_fetched` as the
    case `fetched` (6.8 item 6).
15. The block side `workers` and `test_agent_faults` (6.11), a fresh worker
    per case, in place of the three placements 6.6 offered.
16. The crash block's wait for the killed worker's files (6.11 item 11):
    synchronous opens retried on `NoModificationAllowedError` only, before
    the pool's install, until the start's `wait_seconds`; overturned by
    leaving the crash test removed.
17. One limit per B block, the block's alarm passed to devtools'
    `limit_set` (6.8 item 4); `test_error_overlay` installing the overlay
    again after each screen write (6.8 item 5).

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
8. Question T6, the downloads, asked as option A, an agent running the
   fetch once: answered on 2026-10-30 with the fetch before every test
   run, no network when the pinned files are there, and a canonical
   structure (3.14).
9. "it is time to move forward with a scripted far end for the AI worker's
   lane to the server": the design 3.9 had recorded as not planned is
   planned as 6.9.
10. The project rule of 2026-10-30 that a scripted AI is expected and
    allowed in testing, the primary exception to the ban on mock test
    objects, since the suites must run without an AI API endpoint, which is
    non-deterministic: it modifies the reading of Question T3 A for the AI
    (4.4).

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
10. "update all obsolete docs you are already aware of": this plan and
    `PY_GOALPOSTS.md` were brought up to date on 2026-10-30.

11.5 Unresolved: the confirmations of 11.2. Each is satisfied in this plan
with its cause, and none needs a question of the maintainer. Item 12, the
departures of 6.9 item 7 from the coordinator's design, was confirmed by
the coordinator on 2026-10-30 (`tmp/tasks_29_1354.md` item 32.5). Question
T6 is answered. Group C (section 7) waits on the maintainer's approval of
ttyd and `dash` (`tmp/tasks_29_1354.md` item 34.2.1).
