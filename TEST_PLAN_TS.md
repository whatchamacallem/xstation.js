# TEST_PLAN_TS

The execution plan for testing the TypeScript modules of `ts/` in strict
dependency order, with no mock test objects, in three groups: A, the blocks
the TypeScript toolchain runs in Node; B, the blocks run in headless Chrome
with no ttyd and no tty; C, the tests behind ttyd, past the limit of B,
planned since 2026-10-30. Most tests take the shape the maintainer set on 2026-10-28: a TAP
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

On 2026-10-30 the maintainer also let the tests build and start ttyd,
for Linux, testing on Ubuntu only, and start dash, and took the Windows
test path offline (`tmp/tasks_29_1354.md` item 35); dash runs only in the
bubblewrap sandbox the maintainer gave (item 39). Group C, where planning
stopped until then, is planned in section 7; ttyd's build is 3.15, and the
Windows test path's state 3.16.

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
- Group C: what needs ttyd, the console on tty 0, an open WebSocket or
  the real server, planned on 2026-10-30 (section 7). Its TypeScript
  blocks join the one stream on the headless page that ttyd serves, and
  the wire test and the browser test run after the stream on the Linux
  browser.

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
doubles in group C (7.2), which go by 7.6 since 2026-10-30.

## 3 The decisions

Each is class B until the maintainer confirms it (11.2), or rests on a
question of section 9, all answered on 2026-10-30, or was confirmed then
(11.3).

3.1 Three groups. A: every block that runs in Node 22 after tsc with no
double. B: every other block that runs in `chrome-headless-shell` with no
ttyd and no tty. C: the rest, which needs ttyd, planned in section 7 since
2026-10-30. A block runs once, in the first group that can run it. A suite whose classes
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
   Since 2026-10-30 its two lists hold no block, by 3.1, and its bring up
   serves the wire test and the browser test (7.2 item 3).

3.12 Programs (Question T1). A needs `node` and `tsc`; B also needs
`chrome-headless-shell`. The maintainer approved all three on 2026-10-30
for `test_all.py`'s TS phases (Question T1 B). tsc is TypeScript 5.2.2 from
the apt package `node-typescript`, `/usr/bin/tsc`, and no file of the tree
names any other tsc. `devtools.py` gains a transport for a Linux browser
over `--remote-debugging-pipe`, file descriptors 3 and 4, standard library
only, beside its Windows relay. The reason is that the project keeps one
DevTools client, `devtools.Browser`, and not that the module exists.
Since 2026-10-30 the Windows relay is offline with the rest of the Windows
test path (3.16), and every test that drives a browser drives
`chrome-headless-shell` through `devtools.LinuxPipe`. Since 2026-10-30, by
the maintainer's request of `tmp/tasks_30_2127.md` item 2, `test_all.py`,
`test_wire.py`, `test_browser.py` and `test_posix.sh` take `--anthropic`
for Anthropic's cloud container. Since 2026-11-01, by the maintainer's
answer to 11.2 item 29, the three switches `--anthropic`, `--debug` and
`--verbose` are global bools of `python/switches.py` in every Python
process of a run, carried to its children as `XSJS_ANTHROPIC`,
`XSJS_DEBUG` and `XSJS_VERBOSE` set to 1, and to the TypeScript realms in
`tap.start` (3.17). With `switches.anthropic`, `LinuxPipe` starts the one
match of
`/opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell`,
Playwright's chrome-headless-shell, in place of
`/usr/local/bin/chrome-headless-shell`. Without it nothing changes, and
its lines are exempt from `--coverage`, since one of its two paths runs on
each machine; and ttyd is built from the package manager's archive of
ttyd 1.7.7, `third_party/ttyd/ttyd_1.7.7.orig.tar.xz` of Ubuntu's source
package `1.7.7-4build1`, whose tree equals the pin's, checked by its own
digest and placed by `apt-get source --download-only ttyd=1.7.7-4build1`
in the container's setup, with a `deb-src` entry of Ubuntu resolute's
universe, since github.com answers 403 there (Question T11). The
container's other differences are met by its setup, not by code. The runs
are made as a user other than root, and since 2026-11-01 `test_all.py`
refuses to start as root (Question T8).

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

3.15 The ttyd build. On 2026-10-30 the maintainer authorized building ttyd
and running it, on Linux only, no test starting a Windows program. The
ttyd every test runs is `build/ttyd/ttyd`, built from the pin of 3.14 and
the project's patches, never `/usr/bin/ttyd` of the apt package. A module
of the driver's bring up, `python/ttyd_build.py`, stub first in
`API/python/ttyd_build.pyi`, builds it by the steps of `xsjs_install.ps1`'s
`_xsjs_install_step_build_ttyd`, which stays as it is, offline with the
Windows path:

1. The API. `ttyd_build.checkout_build() -> str` reads `settings.json` with
   `settings.settings_load`, the checked reader the driver's `tap.start`
   uses, and builds from the three settings the install script reads, each
   a path from the checkout's top: `powershell.ttyd_archive`, the archive;
   `powershell.ttyd_patches`, the directory of the patches; and
   `powershell.ttyd_build`, the build directory. It returns the path of
   `ttyd` in the build directory. `ttyd_build.inputs_build(archive_path,
   patches_path, build_path) -> str` builds from the paths it is given and
   returns the same path; `checkout_build` calls it with the three
   settings, and the suites call it with scratch directories under
   `build/`, as `page_build.node_build` takes its build directory (5.6).
   No setting has a default, and the names stay, since the offline install
   script reads them too.
2. When it builds. A build directory holds the record `inputs.json`: the
   SHA-256 of the archive, then the name and SHA-256 of each patch in the
   order they apply. When `ttyd` is in the build directory and the record's
   bytes equal the bytes it would write for the inputs now, `inputs_build`
   returns at once, starting no program and changing no file; otherwise it
   builds. So a run builds whenever `build/ttyd/ttyd` is missing
   or was built from another archive or other patches, since `build/` may
   be deleted at any time and a run may start from a clean checkout. A
   record
   of another layout, or one cut short, is a record of other inputs. The
   record is written last, after `ttyd --version` exits 0, so a failed
   build leaves none and the next run builds again.
3. The steps. Every build starts from the archive, since a patch applies
   once: the build directory is removed, made again with `source/` in it,
   and the archive unpacked there by `tarfile`, the first component of each
   path stripped and the `data` filter on, as `tar -xzf ARCHIVE -C SOURCE
   --strip-components=1` does. Each `*.patch` of the patches' directory is
   applied in name order, by code point, with `patch -p1 -d SOURCE -i
   PATCH`, which the standard library has no equal of; then `cmake -S
   SOURCE -B BUILD -DCMAKE_DISABLE_FIND_PACKAGE_Git=TRUE`, `cmake --build
   BUILD` and `BUILD/ttyd --version`. Python starts `patch`, `cmake` and
   the built `ttyd`, nothing else, and `cmake` starts the compiler and
   `make`. The flag, decided on 2026-10-30 and in the install script's
   configure line too, is there because cmake would otherwise start git,
   which runs `git describe` in the enclosing work tree, the checkout's.
   No program has a time limit,
   since the build is outside every limit of the run.
4. Output. Each program's stdout and stderr go to one log, `build.log` in
   the build directory, made after the directory is removed, and the log
   holds their output and nothing else; nothing goes to stdout, the
   driver's TAP stream, and each program's stdin is `/dev/null`, so that
   none reads the driver's. The program writes the log itself, so a hard
   exit loses none of it. A program that exits other than 0 raises naming
   its command line, its exit code and the log's path, with the log's last
   20 lines in the error's `cause`. A missing program raises
   `FileNotFoundError` naming it, and a missing header fails `cmake` or the
   compiler, its line among those 20. The install script's check step,
   which names the apt package of a missing tool or header from
   `powershell.build_tools` and `powershell.build_headers`, is not part of
   the build. The texts are plain English, as those of
   `third_party_fetch.py` and `page_build.py` are, with no key in
   `i18n/en-US.json`.
5. The bring up. `test_all.py` calls `ttyd_build.checkout_build()` in
   process right after `third_party_fetch.pins_fetch()`, on every run,
   `--module` runs too, outside every block timer and before the smoke
   run's 120 s deadline starts. A failed build ends the run with its error
   and a nonzero exit before the first block. A run on the tty builds before
   its stream, and the run of the TAP suite server then finds the build in
   place.
6. The suite, `test_ttyd_build`, smoke-test, through the API alone, on the
   real archive, patches and tools, with no double. Measured on
   2026-10-30, a cold build takes about 1.5 s here, not the few tens of
   seconds first thought, so the suite's cold builds fit the smoke run,
   which already takes about 65 s of its 120, and no normal-test suite is
   split from it. On the run's build, which the bring up made:
   `checkout_build` returns the path of `ttyd` under
   `powershell.ttyd_build`, and a second call changes no file of the build
   directory; `ttyd --version` writes the gold's version line, measured as
   `ttyd version 1.7.7`; the
   patch's option, given as `--srv-buf-size=SIZE` before `--version`, is
   taken with `settings.json`'s `srv_buf_size`, and refused below 0 with
   the patch's line and exit code. Through `inputs_build`, into scratch
   build directories under `build/`: a patch that does not apply, a real
   fault, raises naming `patch` and the log's path, the log's last lines in
   its `cause`, and leaves no record and no `ttyd`; and a build from an
   empty directory of patches, whose `ttyd` names the option unrecognized,
   then one from the project's patches, which the record makes a build,
   whose `ttyd` takes it, then a call that changes no file, then, with
   `ttyd` removed, a build again. The option takes its value after `=`,
   since an unpatched ttyd takes a separate value as its start command and
   starts serving, as measured. The gold is `python.test_ttyd_build`.
7. The order. `ttyd_build` calls into `settings`, so its suite sits in the
   layer after the one of `test_settings`, alphabetical within it: after
   `test_tap_loop`, and before `test_echo_loop`, of the next layer.
8. Left, written here so that nothing is lost: the install script keeps
   its own copy of the steps; when the Windows path comes back, its build
   step could run a command line `python3 python/ttyd_build.py` through WSL
   instead, which is not built now since nothing would run it.

3.16 The Windows test path, offline. On 2026-10-30 the maintainer took the
Windows path offline, to be brought back later and not deleted, and made
automated testing Ubuntu's alone, not through WSL (`tmp/tasks_29_1354.md`
items 35.1 and 35.3). The coordinator read the Windows path as the Windows
test path, and the second answer as no test starting a Windows program
(item 36.2):

1. Offline since 2026-10-30, kept in the tree, run by nothing, and to be
   brought back later: `powershell/test_powershell.ps1`, the official
   target that runs on Windows and calls `python/test_all.py` inside WSL;
   `powershell/test_lint.ps1`, which it runs first; `devtools.WindowsRelay`,
   the transport through `powershell.exe` to Chrome or Edge on Windows; and
   the later suite `test_devtools_powershell`, which drives it. The suites
   that drove the Windows browser, `python/test_wire.py` and
   `python/test_browser.py`, drive `chrome-headless-shell` through
   `devtools.LinuxPipe` instead (the coordinator's decision 36.4, 7.6,
   7.7).
2. As it was: the user facing scripts `xsjs_install.ps1`, `xsjs_start.ps1`,
   `xsjs_status.ps1` and `xsjs_stop.ps1`, and `README.md`, which are not
   tests; the install script's ttyd build, of which `python/ttyd_build.py`
   follows the steps (3.15); and the project rules' two official targets,
   since the Windows one is offline, not withdrawn.
3. Written in the tree by tasks 7.8.6 and 7.8.7: the headers of
   `powershell/test_powershell.ps1`, `powershell/test_lint.ps1`,
   `python/test_devtools_powershell.py`, `python/devtools.py` and its stub,
   and `_LATER`'s reason for `test_devtools_powershell` in
   `python/test_all.py`, each saying that the part is offline since
   2026-10-30, kept, run by nothing, and to be brought back later.
4. Left for its return, so that nothing is lost: the console's shell is
   bubblewrap since 2026-10-30 (7.4), in use too, and the install script
   neither checks for nor names the apt package `bubblewrap`; and its ttyd
   build could run `python/ttyd_build.py` through WSL (3.15 item 8).
5. By the maintainer's answer to Question P1 of task 11's postmortem,
   "powershell will never be made available, i keep telling you to ignore
   it. do everything you can without it, a dependency on it is
   undesirable.": PowerShell is ignored, no question is asked of it,
   nothing of the Linux run waits on it, and the designs written for the
   Windows path's return, 3.27 item 6 among them, stay as written and
   are built by no task.

3.17 The switches, by the maintainer's answer of 2026-11-01 to 11.2 item
29: "so far we have --anthropic --debug and --verbose and i want them all
passed and readable in some native form everywhere. even if as global
bools." `API/python/switches.pyi` holds the design: `options_add` and
`switches_set` on the command lines of `test_all.py`, `test_wire.py`,
`test_browser.py` and `third_party_fetch.py`, which `test_posix.sh` passes
each at most once; each switch given sets its variable, which every child
process inherits, ttyd's commands, Node and Chrome included, and a process
reads the three at import, an unset variable false and a value but 1
refused. The TypeScript threads take them from `tap.start` and
`settings.set`, which carry `switches` as `switches.switches_get()` gives
it, and read them through `API/ts/switches.d.ts`. `anthropic` picks the
container's browser and ttyd's source (3.12); `debug` and `verbose` are
debug mode and the console's verbose level since the answer to Question
T15 (3.18). Dash keeps its scrubbed environment, which
carries none of the three, since the sandbox's shell is the person's.

3.18 The parameters and the gold of each suite, by the maintainer's answer
of 2026-11-01 to Question T15, an option D of their own: "Split the
settings json so that there are separate files for every test suite. have
settings.json just be the settings that were not for a test suite. prefix
all the test settings test_setting_<suite_name>.json add paramters.json
which has the command line parameters for the run. that way settings.json
is not re-written to inject vars." The design:

1. The gold of each suite. `test_settings.json` goes. What it held under
   `python.<suite>` or `typescript.<suite>` is the file
   `test_setting_<suite>.json` beside the suite's module, a suite's name
   being its module's, as the gold keyed it:
   `python/test_setting_test_jslb.json` beside `python/test_jslb.py`,
   `ts/test_setting_test_queue.json` beside `ts/test_queue.ts`. The directory keeps apart the Python and TypeScript
   suites of one name: `test_all`, `test_dispatch`, `test_jslb`,
   `test_mcp`, `test_settings`, `test_substrate`, `test_verbose` and
   `test_wire`. The top keys go to the suites that read them:
   `smoke_seconds` and `module_seconds` to the driver's
   `python/test_setting_test_all.json`, `long_task_ms` to
   `python/test_setting_test_browser.json`, `typescript.run`, which
   `ts/test_all.ts` reads, to `ts/test_setting_test_all.json`,
   `powershell.lint_*` to `powershell/test_setting_test_lint.json` and
   `powershell.test_user` to `powershell/test_setting_test_powershell.json`.
2. Ids. An id stays `<language>.<suite>.<key>`, as
   `python.test_jslb.limits`: `harness.gold_get` reads the suite's file at
   the first call that needs it, and `harness.gold_copy` assembles the files
   into one object of that shape. The four top keys' ids become
   `python.test_all.smoke_seconds`, `python.test_all.module_seconds`,
   `python.test_browser.long_task_ms` and `typescript.test_all.run`.
3. Roots. A root holds the gold that its server carries: the files of the
   TypeScript suites, the only gold a page reads, flat in the root as
   `<root>/test_setting_<suite>.json`, which `harness.gold_write` writes.
   `bootstrap.py` in debug mode reads every `test_setting_*.json` of its
   root by `jslb.json_decode` into `{"typescript": {suite: gold}}`, which
   `tap.start` carries as `test_settings`, the line's field keeping its
   name. A test that changes a root's gold, as `test_wire.py`'s
   `typescript.test_all.run`, writes that suite's file in the root.
4. `parameters.json`, the parameters of one server's run:
   `{"anthropic": bool, "debug": bool, "verbose": bool}`, the three switches
   of 3.17 and nothing else, each key required. `switches.parameters_load`
   reads it by `jslb.json_decode` and refuses a missing or extra key or a
   value that is not a bool; `switches.parameters_write` writes it. A root
   holds one: a test writes the run's, `switches.switches_get()`, or, for
   a root whose test needs its own debug mode or level, its own.
5. Debug mode and the level. `debug` and `verbose_level` leave
   `settings.json`, its stub, `settings.py`'s table and `settings.Settings`.
   A server reads `<root>/parameters.json` beside its settings and sets its
   switches from it by `switches.switches_apply`, its variables too, so
   that every module of the server and every child it starts reads the
   root's parameters: debug mode is `switches.debug` wherever it was the
   setting `debug`, and `tap.start` carries the root's as `switches`. The
   console's verbose level, `verbose_level` until now, is 2 when `verbose`
   is true and 1 otherwise; level 0, which `verbose.exec` keeps and
   `test_verbose` tests, is chosen by no server. The TypeScript threads
   read debug mode as `switches.debug_on()` where they read the setting
   `debug`: `settings.ts`'s freeze, `settings.put` and `names_full`, and the
   `debug_setting` readers of `queue.ts`, `tools_browser.ts` and
   `worker_ai.ts`; each thread sets its switches before its settings.
6. The tests. No test writes a root's `settings.json` to set `debug` or
   `verbose_level`: a root's `settings.json` is the checkout's copy, and a
   test sets the root's `parameters.json`. A test that gives a root other
   settings, as `overflow_bytes`, `chunk_bytes`, `provider.scripted` or a
   wrong value the checker refuses, still writes that root's
   `settings.json` (Question T18). The golds that list the settings' keys
   lose `debug` and `verbose_level`, and the strings that named those
   settings name the parameters.
7. The start script. `root_files` names `settings.json`, `provider.json`
   and `ts/test_setting_*.json`, which `xsjs_start.ps1` copies flat into
   its root; it writes the root's `parameters.json` from its own
   arguments, `.\xsjs_start.ps1 [--debug] [--verbose] [username:password]`,
   `anthropic` false, so that without `--debug` the page runs in normal
   mode and the console role refuses. `test_lint.ps1` and
   `test_powershell.ps1` read their own gold files. None of it runs here,
   since no test starts a Windows program (3.16).

3.19 The largest database enforced, by the maintainer's answer of
2026-11-01 to Question T14: "[x] A. 10 MiB, enforced: both stores set
SQLite's max_page_count, and a write past it fails loud. This is a refusal
you would be requiring. this needs tests." The design:

1. Each store, `python/substrate.py` and `ts/substrate.ts`, sets
   `PRAGMA max_page_count` to `blob_max` over the database's `page_size`
   on every connection it opens, before any statement of its own, so that
   no database file of the stores grows past `blob_max`. SQLite refuses a
   write that needs a page past it with `SQLITE_FULL`, "database or disk is
   full", which the store raises and never catches: a refusal the
   maintainer requires (the project rules' Databases section).
2. The limit belongs to a connection, not to the file, so every open sets
   it: the Python store's three `sqlite3.connect` calls and the TypeScript
   store's three `OpfsSAHPoolDb` opens.
3. A database that `db.restore` brings is at most `blob_max` already, the
   wire's bound of its one blob.
4. Not a store: the verbose log `_verbose.sqlite` of `python/verbose.py`
   (Question T19).
5. Tests: the Python store's suite and the TypeScript store's block each
   fill a database through the store's own API until the write past the
   limit fails with SQLite's full error, then check that the file is at
   most `blob_max`, that the database still reads, and that a database
   opened again has the limit again. 10 MiB of rows, no buffer larger;
   labelled smoke or normal by the measured time, the smoke target staying
   within its 120 s.

3.20 The restart's hold, by the maintainer's message of 2026-11-02 on
Question T13: "fix the T13 race. just pick a solution." Option B is taken:

1. `wire.WirePort.line_post` holds every line posted after a line of type
   `system.restart`, unsent; the restart line itself goes. So nothing the
   page posts after the restart's request, as a push of the page's log
   by `verbose.put`, can reach the restarted server, which reads from the
   same pipe that the server before it left.
2. `wire_end`'s `error` line is never held. The restarted server's
   `tap.start` is refused by `wire.start_twice`, which faults the port, and
   the worker's report sends that refusal, the restarted server's first
   line from the page, which it logs before it exits 1.
3. The held lines are never sent: only a reload of the page takes a new
   first line, so no server is left to take them. They are the posts of
   the session that the restart ended.
4. Tests. `test_wire_port`'s `test_restart_held`, with no socket: after the
   first line, a posted `system.restart` is sent, so refused for the
   missing socket, and a line posted after it is held, returning with no
   fault. `test_wire_rungs`'s restart rung posts a TAP diagnostic push
   right after `system.restart`, which, unheld, the restarted server would
   read before the refusal; `test_wire.py`'s restart root takes the page's
   refusal alone, and a push named there fails it. Each case is run once
   with the hold taken out, and must fail.

3.21 The smoke deadline, by the maintainer's message of 2026-11-02:
"extend the smoke test timeout to 3 min." `python.test_all.smoke_seconds`
is 180. By 5.11 item 4, every block is `smoke-test` unless the deadline is
broken, so the blocks labelled `normal-test` for the 120 s alone go back
to `smoke-test`: `test_jslb_decode.ts` (7.11 item 7.7) and the two suites
`test_substrate_limit` (7.11 item 7.3). The comments that said 2 minutes
say 3. The project rules' "fit in 2 minutes" is the maintainer's text,
left as it is (Question T22). On 2026-11-03 the maintainer had the
rules say "fit in 3 minutes" (Question T22 A).

3.22 The limit everywhere, by the maintainer's answer of 2026-11-02 to
Question T19: "[x] B. Yes: verbose.py sets the same limit, and a log line
past 10 MiB fails loud. this is a clear reading of my request to have the
same 10 MiB limit everywhere." `python/verbose.py` sets
`PRAGMA max_page_count` to `blob_max` over the log's `page_size` on every
connection it opens to `_verbose.sqlite`, before its own statements, as the
stores do (3.19); a line that needs a page past it fails with SQLite's
`SQLITE_FULL`, raised, never caught. `blob_max` reaches it as the stores
take it. The TypeScript threads keep no SQLite log: their lines go to the
server's. `test_verbose` fills a log to full through `verbose`'s own API and
checks the error, the file at most `blob_max`, and the log still read; its
label by its measured time. `declawed.md` now says the 10 MiB limit is the
comprehensive plan for size limits.

3.23 The page limit refused, by the maintainer's answer of 2026-11-02 to
Question T21: "[x] B. No: the stores refuse any statement that sets the
page limit." Each store, on every connection it opens, after its own
`max_page_count` (3.19), sets SQLite's authorizer, which denies a
`PRAGMA max_page_count` that has a value, so that SQLite refuses the
statement when it is prepared with `SQLITE_AUTH`, "not authorized", which
the store raises and never catches. Python by `Connection.set_authorizer`,
TypeScript by `sqlite3.capi.sqlite3_set_authorizer` of sqlite-wasm 3.46.1.
A `PRAGMA max_page_count` with no value, a read, stays allowed, as every
other statement. `page_size` cannot change a database that holds a page,
and `VACUUM` and `ATTACH` cannot run inside `sql.run`'s one transaction, so
neither is refused. Tests in `test_substrate_limit`, Python and TypeScript:
`sql_run` of the setting refused, and the limit still read back as it was.

3.24 No gold in a root, by the maintainer's answer of 2026-11-02 to
Question T20: "I didn't design the "expected-values file" and was
expecting html test code, a tty and dash to be served instead. Explain why
this should exist or remove it." It existed because the TypeScript blocks
on the ttyd page need their gold, and the page's only input from its root
was the server's first line: a session's design, never the maintainer's,
carried the gold in `tap.start` in debug mode, and 3.18 item 3 copied the
suites' files into each root. It is removed:

1. The test page carries its gold, as it carries the strings of
   `i18n/en-US.json`: `page_build` writes the TypeScript suites' gold,
   `{"typescript": {suite: gold}}` from `ts/test_setting_*.json`, into the
   test page it builds, and `ts/harness.ts` reads its gold from the page.
   Every realm that runs TypeScript blocks, A's Node realm, B's headless
   pages and C's ttyd pages, reads it there.
2. A root whose test gives its page other gold, as `test_wire.py`'s rungs
   or `typescript.test_all.run`, gets a page of its own: the test page,
   built once, written again into the root with that gold, and served by
   ttyd's `--index`. A debug root then serves the test page, a tty and
   dash, and holds no `test_setting_*.json`.
3. `bootstrap.py` reads no gold, and `tap.start` carries no
   `test_settings`; `harness.gold_write` and the roots' gold files go;
   `root_files` names `settings.json` and `provider.json`; `xsjs_start.ps1`
   copies no gold; Question T20 goes with the files it asked about.
4. Tests: the page build's suites check the gold in the page; the cases of
   `test_bootstrap` that read a root's gold go, with their strings; the
   wire and browser tests write each root's page.

3.25 The formatter suites in the run, by the maintainer's message of
2026-11-03, task 9 of `tmp/tasks_30_2127.md`: "now start iterating on
getting all the tests to pass. do what you can in py and ts."
`python/test_reformat_formatters.py` and
`python/test_test_posix_formatters.py` were later suites, in no phase,
waiting on ruff, shfmt and prettier. `test_posix.py`'s checks run those
same programs through `reformat.py` in every official run, and all three
are on the run's PATH, so both suites join the Python unit phase:
`test_reformat_formatters` after `test_reformat`, and
`test_test_posix_formatters` after `test_test_posix`, each alphabetical
in its layer, their labels by their measured seconds against the smoke
deadline of 3.21. `test_devtools_powershell` stays a later suite, its
PowerShell unrun by the maintainer's answer to Question T24.
Measured on 2026-11-03: 0.378 s and 0.028 s in the smoke run, so both
are labelled `smoke-test`; the smoke target then took 117.391 s. Their
labels are overturned by 3.27: both are `normal-test`.

3.26 ttyd keeps each frame until libwebsockets is done with it, by the
same message of 2026-11-03. The normal run of task 9 failed in
`test_browser.py`'s rung "stage 5: wire drain poll": ttyd 1.7.7 ended
with SIGSEGV after the 80 echo requests of 131072 bytes posted while it
was stopped. Repeating the rung alone failed within 21 passes, with an
echo whose blob had 9 bytes overwritten by a malloc chunk header, and
AddressSanitizer on a ttyd built from the same source named a
heap-use-after-free: `wsi_output` in `src/protocol.c` frees each OUTPUT
frame as soon as `lws_write` returns, while the permessage-deflate
extension that Chrome negotiates keeps zlib's input on that frame and
goes on compressing it on later writeable events. The fix is a patch of
ttyd's source beside those of 3.15 and Question T10,
`third_party/ttyd/patches/03_output_kept.patch`, which keeps
compression:

1. `struct pss_tty` holds `output`, the frame `lws_write` last took.
2. `wsi_output` and `send_initial_message` give their frame, from the
   heap, to `output_keep`, which frees the frame held before and holds
   the new one. libwebsockets calls the protocol's writeable callback
   only once a frame's draining is over, so the frame freed there is
   done with.
3. `LWS_CALLBACK_CLOSED` frees the frame held.
4. Tests: the rung itself, which fails without the patch; repeated
   alone on the release build and on an AddressSanitizer build of the
   patched source, every pass passes and AddressSanitizer reports
   nothing.

Measured on 2026-11-03: without the patch, four repeats of the rung on
the release build failed at passes 1, 1, 2 and 22, and the
AddressSanitizer build reported the use-after-free at pass 2; with it,
40 of 40 passes on the AddressSanitizer build with no report, 60 of 60
on the release build, and the normal target passed in 643.952 s.

3.27 No formatter in a smoke-test run, by the maintainer's message of
2026-11-03, task 10 of `tmp/tasks_30_2127.md`: "remove the formatter runs
from the "smoketest" series of tests and update declawed to say they don't
have to run except before a commit and that can be done manually." The
project rules now say the formatters do not have to run except before a
commit, and that run can be done manually. A smoke-test run starts no
formatter and no checker of `python/reformat_table.json`:

1. `test_posix.py`'s formatter step formats the whitelisted files in a
   normal-test run, as before, and in a smoke-test run only prints its
   advisory, now "test_posix.py: this smoke-test run leaves the
   formatting alone; wait for a normal-test run, which does the
   reformatting.", the gold `format_advisory` of
   `test_integrate_test_posix`. It no longer calls
   `reformat.format_check`, which ran ruff format --check, shfmt --diff
   and prettier --check. The rows' linters, today ruff check alone, run
   in both categories, being linters and not formatters.
2. `test_reformat_formatters` and `test_test_posix_formatters`, which
   start the real formatters, are labelled `normal-test`, in their
   places of 3.25 in the Python unit phase.
3. `test_integrate_test_posix`'s smoke case gives the step a Python file
   that ruff would change, and checks that the step returns, prints the
   advisory alone and leaves the file as it is, starting no command.
   `test_test_posix_formatters` keeps its normal case, which starts
   ruff; its smoke case, which started ruff's checker, goes, the
   integration suite now holding the smoke case.
4. `reformat.format_check`, the checkers of the table and their tests in
   `test_reformat` and `test_reformat_formatters` stay, though no
   official run calls `format_check` any longer; `test_reformat`'s case
   on PowerShell files starts no command.
5. A normal-test run still formats, since the message names the smoke
   series alone; the formatter run before a commit is `reformat.py`, run
   by hand.
6. The Windows target, offline since 2026-10-30, runs
   `powershell/test_lint.ps1`, which formats the PowerShell files, in
   both categories. When it is brought back, `test_powershell.ps1` gives
   `test_lint.ps1` the category, and `test_lint.ps1` formats in a
   normal-test run only, checking line endings and linting in both.
   Nothing of it changes now, the PowerShell left unrun by Question
   T24's answer.
7. ttyd's compression, by the same message: "disable ttyd compression if
   there is a blocking problem using it and continue, it is only being
   used for bring up and may be replaced." permessage-deflate stays, with
   the patch of 3.26, while it causes no blocking problem. On one, a
   patch of ttyd's `src/server.c` sets `info.extensions` to NULL, so that
   ttyd offers no extension and sends every frame uncompressed, and the
   runs go on.

3.28 Each queue runs the lines of its inputs in the order they come, by
the maintainer's answer to Question P4 of task 11's postmortem
(`tmp/tasks_30_2127.md` section 28), "jslb input streams need to be
executed in order. out of order execution is non-deterministic and hard to
test. update and overrule pervious instructions if any.", written here
before any code.

1. In a queue that is not synchronous a reply's wake was held at the end
   of the inbox when the reply's step ran, so a line that came after the
   reply and before that step ran before the wake (7.9.1 item 2). From
   now a wake takes its last reply's place: in a queue that is not
   synchronous it is held at the front of the inbox and runs at the next
   step, before every line that came after that reply. In synchronous
   mode a reply runs only once the queue's own items are done, so its
   wake, held with them, already runs before every later input, and
   nothing changes there.
2. `API/ts/queue.d.ts` says so first: the lines of each input run in the
   order they come, and a wake runs in its last reply's place, in both
   modes.
3. The test: `test_queue`'s tests run in synchronous mode, within the
   test's call, and two lines a test sends on a MessageChannel need not
   both be held before the queue's next step, since the step's own
   message can run between them; so A's `test_integrate_queue`, whose
   queues follow `queue_synchronous`, false in every run, gains a far end
   whose posts reach the queue within the post. Its `ai` queue's lane of
   thread `http`, a name of `queue.ThreadName` it gives no other use, is
   one of a linked pair of `queue.LocalPort`s whose other end's receiver
   is the test's own function (6.9 item 3.2), owning `queue_end.`. The
   new case `wake_ordered` sends `queue_test.order`, whose handler submits
   `queue_end.ask` and sleeps, and then `queue_end.go`, which the queue
   forwards to that end; the end then posts the reply to the request it
   kept and a `queue_test.after`, both within the forward, so that both
   are held before the reply's step runs. The wake answers the order and
   the `queue_test.after` handler notifies `queue_ui.after`, so the case
   expects the order's reply and then that notice; with the wake held at
   the inbox's end the notice comes first and the case fails.
4. What it overrules: 11.2 item 52, the race settled in `console_view`,
   and 7.9.1 item 2's design. With the wake in order, the AI side's reply
   to `console.close`, posted before the socket's close, always runs on
   the UI before tty 0's `console.exit`. An end before the close's wake
   is then a case that cannot happen, so the view's phase `ended`, its
   flag `close_woken`, `TestClosing.test_exit_first` and the stub's
   paragraph on that end go, and `close_done` refuses any phase but
   `closing` again.
5. The order of ttyd's own ends, its socket's close against its process's
   end and the last output, stays as ttyd's design makes it, a known
   limitation by the project rules; the tests wait for the end they need.

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
   `API/ts/lines.d.ts` and the lane table of `API/README.md`. Ignored
   on 2026-10-30 by the maintainer's answer that the designs not needed are
   ignored (`tmp/tasks_29_1354.md` item 35.4): not built, and kept here as
   written.

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
5. Since 2026-10-30 `WindowsRelay` is offline (3.16), and the later suite
   `test_devtools_powershell`, which drives it, is run by nothing; the
   methods of `devtools.Browser` that only it tested are tested on the
   Linux browser first (7.6 item 6).

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
   categories. Planning ended here until 2026-10-30, when section 7 planned
   group C.
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
   run and its page stays as it is (7.2). Since 2026-10-30 the ttyd page's
   lists hold no block (7.2 item 3).
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

## 7 Group C: the tests behind ttyd

Written on 2026-10-30 by the maintainer's answer that the tests may build
and start ttyd, for Linux, testing on Ubuntu only with no Windows program,
and start dash (`tmp/tasks_29_1354.md` items 35.1 and 35.2), and by the
answer that dash runs only in the bubblewrap sandbox the maintainer gave
(item 39). The coordinator's decisions 36.2 to 36.4 and 40.1 to 40.2 bind
it. ttyd is built by 3.15, and the Windows test path is offline by 3.16.
Until that day this section listed the limit of B and planned nothing past
it; each part of that limit is placed by 7.1.

7.1 What C holds: each part of the limit as written until 2026-10-30, and
where it runs now.

1. `wire.WirePort`'s open, its socket send and drain, `wire_end` and
   `wire_close` on an open socket, and `wire.ConsolePort`'s open and input:
   ttyd's protocol on tty 1 and tty 0. `test_wire_end`'s three tests, with
   their doubles, become the block `test_wire_end` of C (7.5 item 4, task
   7.8.3); `wire`'s integration block, which 3.5 left to C, is the new
   block `test_integrate_wire`, `wire.ConsolePort`'s path through tty 0 and
   dash with the binary heredoc of 7.4 item 7 (7.5 item 5, task 7.8.8); the
   browser test's rungs of the two ports stay rungs (7.6); the wire rungs
   drive both (7.7).
2. `test_wire_rungs.ts` and `python/test_wire.py`: the wire test, after the
   stream, on the Linux browser (7.7, task 7.8.5). Its two rungs that type
   into dash on tty 0, `console` and `lines`, run through the console's new
   shell (7.4).
3. `test_worker_ai`'s `test_console_opened`, moved to
   `test_worker_ai_console` with its doubles: the block
   `test_worker_ai_console` of C, on a real queue and a real
   `wire.ConsolePort`, which reaches ttyd's tty 0 and starts no process
   (7.5 item 3, task 7.8.2).
4. `test_tools_browser`'s `test_console_recorded`, `test_permit_always`,
   `test_permits_counted` and `test_console_expired`, moved to
   `test_tools_browser_console` with their doubles: the block
   `test_tools_browser_console` of C, through dash on tty 0 (7.5 item 6,
   task 7.8.4).
5. `console_view`'s open path, its `console.open` to the console owner,
   which no test reached: the new block `test_console_open` of C, wave 3
   (7.5 item 7, task 7.9.1).
6. The requests to the server that only the wire rungs send, `tap.run`,
   `source.put`, `echo`, and `system.restart` with its new `tap.start`: the
   wire test (7.7). `db.restore` with `db.file` of a database the real
   server's store wrote: no code of the server sends them, since
   `engine_db.restore_lines`, which makes those lines, has no caller outside
   the tests, read on 2026-10-30, so no part of C reaches them. The lines
   and the restore run in B, in `test_substrate_store`'s
   `test_restore_answered`, on a snapshot of the real store. Recorded, not
   planned.
7. `python/test_browser.py`'s rungs, with its probe kit's doubles (2.11):
   the browser test, after the wire test, on the Linux browser, each rung
   kept, moved or removed by 7.6 (task 7.8.6).
8. A realm with `debug` false: the browser test's release root, whose page
   gets its settings and runs nothing, and whose console role is refused
   before any shell runs (7.6).
9. The plan of 2026-10-30 for `test_error_overlay` on the ttyd page: met by
   7.2 item 3. It leaves the ttyd page with every block of A and B and runs
   in B, in a page load of its own, where 6.8 item 5 installs the page's
   handlers again after each screen write, so no later suite of the ttyd
   page reports its faults through the listeners it erased.
10. The plan of the same date for a fresh realm per worker suite of the
    ttyd page: met by 7.2 items 2 and 3. No suite runs on the ttyd page,
    and each block of C runs in a page load of its own, a fresh realm
    (3.2). `test_tools_browser` and `test_agent`, which both register
    `http.request`, `mcp` and the tools' wake types, each run in B in a
    realm of its own, so they never share a dispatch table.
11. The later suites: `test_bootstrap_dash`, the console role through dash,
    leaves `_LATER` for the Python unit phase on the console's new shell
    (7.4, task 7.8.1); `test_devtools_powershell` is offline (3.16).

7.2 The decisions, each class B (11.2 item 21) with its cause.

1. One stream for the blocks of C, the two programs after it. Each
   TypeScript block of C is a block of `test_all.py`'s one stream, relayed
   by `TAPTestRunner.block_relay` (3.4), in a new last phase, C
   integration, after B integration. The cause is Question T2 A (log item
   21.3.12): every TypeScript block is a block of the one stream, and no
   exception was made for C; 7.2 kept C after the stream until 2026-10-30
   only because nothing of C could run. The wire test and the browser test
   stay after the stream and `test_posix.py`, run by `test_all.py`'s `main`
   each under its alarm plan cut at the smoke deadline, the run ending at
   the first that fails with its exit code. They are Python programs, not
   TypeScript blocks; the driver makes their checks around the page, ttyd's
   resident size and its kill, the server's exit, log and databases,
   signals sent to ttyd and to the server, and the fault screen; that place
   already meets the first failure, the deadline and the exit code; and
   Question T2 covers TypeScript blocks only. The other design, written so
   that it is not lost: each program as a Python suite of the stream, a test
   per root, the wire rungs' TAP read inside the test as
   `test_tap_pair_ts` reads its realm's. Not planned, since no rule asks
   for it.
2. Where a block of C runs: on the headless page, `build/headless.html`,
   served by ttyd as its `--index`, as B's blocks run on it served by the
   local HTTP server (3.11, 6.3): a page load of its own, the realm lane
   over DevTools, `test_headless.realm_start` and the binding `realm_line`.
   The block's own `wire.WirePort` and `wire.ConsolePort`, at the page's
   own address, reach ttyd's tty 1 and tty 0 under `--check-origin`, which
   takes only a page of ttyd's own origin, and through tty 1 the real
   server. The causes: the ttyd page's bring up opens its own `WirePort`
   on tty 1, whose server holds the root's `engine.lock`, so a block that
   opens its own, as `test_wire_end` must, would find the lock held there,
   and the browser test stops that bring up today only by replacing
   `Worker` (`_WORKER_STUB`), a system double (2.11, 4.5), where the
   headless page starts no worker until a block asks; the ttyd page's UI
   thread registers no handler of the lines a block's test end would take,
   so a block whose test end is on the UI side, as `test_worker_ai_console`
   is, cannot be there; and the driver's page runner of B serves the page
   with one change, its address (7.5 item 1). A worker block takes the
   page's address from its own `location`, whose origin, for a worker made
   from a `Blob` URL, is the page's, measured by its task; no field is
   added to the start.
3. The ttyd page's lists hold no block. By 3.1 a block runs once, in the
   first group that can run it: every block of `ts/test_all.ts`'s
   `first_modules`, `worker_modules` and `page_modules` runs in A or B, and
   the three blocks of C there run on the headless page by item 2, as 10.4
   foresaw. So the three tables hold no entry, and `python/test_browser.py`'s
   mirrors, `_AI_MODULES` and `_UI_MODULES`, hold none. The run
   `typescript.run` "unit" stays: on each thread it runs the page's bring up
   through ttyd and the real server and writes a document of no block, the
   TAP version line and `1..0`, the path the browser test's suites and
   faults roots reach (7.6); "wire" runs the wire rungs as before. Whether
   both producers and the consumer take a document of no block is measured
   by task 7.8.6, and a refusal is reported, not worked around. To
   overturn: the lists keep the blocks of A and B as a second run through
   the real bring up, against 3.1, costing about the time of B's run in
   every smoke run.
4. The smoke deadline. The smoke run takes about 61 s for the stream and
   3 s for `test_posix.py` (6.8 item 8, 3.15 item 6); ttyd's build is bring
   up outside the deadline (3.15 item 5). Each block of C, and each rung and
   root of the two programs, keeps its present label, the blocks of C
   `smoke-test` by 5.11 item 4, until task 7.9.2 measures the whole smoke
   run from its start to the end of `test_browser.py`. If that passes the
   gold's `smoke_seconds`, 120 s, the slowest smoke parts become
   `normal-test`, slowest first, each with its measured seconds, until it
   fits, by the project rule. A ttyd root's start and stop are outside the
   block's timer and inside the deadline, as a B block's server start is
   (6.3). The costs to measure: each page load of the ttyd page or the
   headless page, about 5 MB; the build of `build/test_wire.html` and of
   `build/test.html` by tsc, one in each program; the `lines` rung's 100000
   lines; the two binary heredocs (7.4 item 7); and
   `test_tools_browser_console`'s expired read, which lasts its timeout.
5. Screenshots on the Linux browser. The browser test keeps its PNGs of
   surveyed states, `Page.captureScreenshot` through `devtools.LinuxPipe`
   into `build/test_browser/`, at the gold's window of 1280 by 720:
   `stage0_typescript_suites` and `stage0_thrown_error`;
   `stage0_fault_appended` goes with its rung (7.6). Task 7.8.6 measures
   that each PNG is written with the gold's width and height in its header.
   No screenshot is added, since no product change of task 35 draws
   anything differently; a postmortem links the PNGs the last run wrote.
6. The order of C. The blocks of C follow every block of A and B, since
   each runs modules tested there, `wire`, `queue`, `worker_ai` or
   `tools_browser`, and the real server, whose Python suites run in the
   Python phases; among themselves they are ordered by 6.8 item 7's rules,
   continuing B's count, by task 7.9.2. After the stream come
   `test_posix.py`, the wire test, then the browser test, as before: the
   wire test reaches the ttyd page's bring up through the real server,
   `tap.start`, `boot.test_worker` and `worker_ai.tap_start` on the
   `WirePort`, which the browser test's roots on the ttyd page stand on.
   The browser test's rungs of the bare ports sit lower than the wire rungs
   by 4.1, but each program runs whole, so the order stays.
7. 10.7 stays not planned, its design kept. The console on tty 0 is now
   reached for real, through ttyd and the console's shell (7.4); the
   maintainer asked for a scripted far end of the server's lane only (log
   item 29); and a scripted console would answer `console.read` from the
   gold in place of `wire.ConsolePort`'s read, a project part in the
   block's realm.
8. One root and one ttyd for each block of C (7.5 item 1), so that no block
   meets another's server or its lock.

7.3 The order of a whole run, by 3.4 and 7.2.

1. Bring up: the pins (3.14), then ttyd's build (3.15).
2. The stream: the three Python phases, `test_bootstrap_dash` now among the
   Python unit suites after `test_bootstrap` (7.4); A unit, A integration,
   B unit and B integration; then C integration: `test_wire_end`,
   `test_integrate_wire`, `test_worker_ai_console`,
   `test_tools_browser_console` and `test_console_open`, in the order task
   7.9.2 computes.
3. After the stream: `test_posix.py`, `test_wire.py` and `test_browser.py`,
   the run ending at the first that fails, with its exit code.

7.4 The console's shell. The maintainer's answer (log item 39): dash runs
by exactly `bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp
--tmpfs /home --tmpfs /mnt --tmpfs /root --unshare-all --new-session
--die-with-parent --chdir /tmp /bin/dash`. By the coordinator's decision
40.1, that command, in use and in the tests alike, is a constant argv at
the top of `python/bootstrap.py` in place of `_DASH_PATH`, its verbose form
the same argv with `-v` after `/bin/dash`; not a setting, since nothing
asks for the command to vary. Plain dash and `firejail --private dash` are
started by nothing: firejail took this machine for a sandbox already and ran
dash with none (log item 38.1).

1. What it changes (40.2), written before any code: dash no longer runs in
   the root, since `/home`, where every root lives, is an empty tmpfs, and
   it starts in the sandbox's own `/tmp`; nothing it writes outlives it; it
   has no network; `--new-session` takes it out of the pty's session, so
   the pty's hangup no longer reaches it, and `--die-with-parent` ends it
   with the console role instead. The root's log stays the console role's,
   outside the sandbox. The console role's `os.chdir(root)` then changes
   nothing dash sees, and goes with the old shell; its scrub of the
   environment stays, since the sandbox passes the environment it is given.
2. Rules for every part that starts dash, so that a later change of the
   shell edits the fewest files:
   1. Only the console role of `bootstrap.py` starts the shell. A test
      reaches dash only through it: by `bootstrap.bootstrap_run` with the
      role `console`, or through ttyd's tty 0, whose command runs that role.
   2. A test reads only what dash prints on the pty. Nothing it reads
      outlives the shell or lies in the root (40.2), so
      `test_bootstrap_dash`'s `found.txt`, read from the root, goes, and its
      checks are kept through the shell's output.
   3. A test compares dash's output only from its first prompt on, so that
      a line a sandbox writes before dash runs changes no expectation.
   4. The command line a test expects in the root's log, the `Running` and
      `exited` lines of `verbose.exec`, is the test's own copy of the argv
      in its gold, as `test_bootstrap_dash` keeps its own copy today, never
      read from `bootstrap.py`'s private constant. A change of the shell
      then edits `bootstrap.py`, its stub's header and that gold.
3. The parts that start dash, each with its task: `test_bootstrap_dash`'s
   three tests and its binary case (7.8.1); `test_integrate_wire`'s cases
   from ttyd's first message on (7.8.8); the wire test's rungs `console`
   and `lines` (7.8.5); the browser test's rung `stage 7: console open,
   close, exit, open` (7.8.6); `test_tools_browser_console`'s cases
   (7.8.4); and `test_console_open` (7.9.1). Each starts nothing until task 7.8.1 has
   landed the new shell; each is written beside it and run once the
   coordinator says it has.
4. The parts that start no dash, each measured by its task:
   `test_worker_ai_console`, which opens tty 0 with ttyd's token and sends
   no first message, so ttyd starts no process, by `wire.ts`'s annotation
   of ttyd's protocol, the command run once the first message is in; the
   browser test's `stage 7: console role refused`, whose root has `debug`
   false, so the console role exits 1 before any shell; `test_bootstrap`'s
   console tests, refused outside debug mode, refused a process, or refused
   with `--main-loop`, each before the shell starts; and every engine role.
5. Measured by the log's task 40.3.1 on 2026-10-30, bubblewrap 0.11.1,
   not setuid, AppArmor not enforced in this WSL kernel, so the effect of
   Ubuntu's profile `bwrap-userns-restrict` is unmeasured:
   1. On the pty bwrap writes nothing, and dash writes `/bin/dash: 0:
      can't access tty; job control turned off` and CR LF just before its
      first `$ ` prompt, still interactive, `$-` being `si`, or `vsi` with
      `-v`. With `-v` each input line comes back twice, from the tty, then
      from dash. Rule 2.3 keeps that line out of every comparison.
   2. dash starts in `/tmp`; `/home`, `/tmp`, `/root` and `/mnt` are empty;
      `/home/t`, the root and `/mnt/c` cannot be entered; `/` is the real
      root, read only. Writes to `/tmp` and `/home` work, and none outlives
      the sandbox.
   3. The environment is HOME, LANG, PATH and TERM as given, and dash's
      `PWD='/tmp'`; `OLDPWD` only after a `cd`.
   4. The code `verbose.exec` returns, then the console role's: `exit 3`, 3
      and 3; `kill -9 $$` from inside, a normal exit of 137, not a signal,
      and 137; from outside, to the pid the console role forked, SIGKILL
      -9 and 137, SIGTERM -15 and 143, SIGHUP -1 and 129; the pty's master
      closed, -1 and 129; the parent's death, everything gone within 1 ms.
      The interactive dash ignored SIGTERM before; the sandbox ends on it.
   5. The pids: inside, `$$` is 2 and `$PPID` 1. Outside, the bwrap the
      console role forked stays in its session, the pty its controlling
      terminal, over an inner bwrap in a new pid namespace and a new
      session with no tty, over dash. So the pty's hangup still ends the
      shell, through the outer bwrap, which 40.2 expected no longer to
      reach it.
   6. About 8 ms from the fork to the first prompt, 34 ms through
      bootstrap's way, and under 0.5 ms from `exit 0` to reaped, 8.6 ms
      through bootstrap.
   7. Through bootstrap's way at levels 1 and 2 the log's `Running` and
      `exited with code 0` lines name the whole bwrap argv, ending in
      `/bin/dash -v` at level 2. A signal to the console role's Python ends
      it, so only the `Running` line is logged, and bwrap and dash are
      gone.
   So `test_bootstrap_dash` expects the shell's start directory `/tmp` and
   the logged command, `test_console_signal` keeps its 137, and a console
   test that compares the output before the first prompt meets the job
   control line. What ttyd logs when a socket of tty 0 closes is measured
   by the tasks that close one, 7.8.5 and 7.8.6.
6. Left for the Windows path's return: its install neither checks for nor
   names the apt package `bubblewrap` (3.16 item 4).
7. The binary heredoc, by the maintainer's request that the console's
   connection, being binary, carry a binary heredoc to dash and back,
   tested so that a connection that is not binary fails (log item 44), and
   by the coordinator's decisions of item 45. The path carries bytes both
   ways: `console.input`'s blob 1, one ttyd message, is sent as is on a
   socket whose `binaryType` is `arraybuffer`, and `console.output`'s blob
   1 is one message from ttyd. `console.read`, the AI's read, is text by
   design: `ConsoleReader` decodes strict UTF-8 and fails a read holding a
   byte that is not UTF-8 with `wire.output_invalid`.
   1. The heredoc is `cat <<'END'`, its delimiter quoted so that dash
      expands nothing. `cat` runs inside the sandbox, whose boundary item
      39 set.
   2. The payload is every byte value that dash and the pty's line
      discipline can carry. Each control byte the line discipline acts on
      is typed after the line discipline's literal next, `0x16`. It holds
      UTF-8 sequences that are not valid, a lone continuation byte, an
      overlong form, a surrogate and `0xff`, which a connection that decodes
      text replaces or refuses. A byte dash itself cannot hold, NUL if so,
      is left out, and the implementing task writes its cause into this
      item. Its lines stay within the line discipline's limit, and none is
      the delimiter. Measured by the implementing task, 7.8.1 first: which
      bytes the line discipline acts on in the console role's pty, whether
      the literal next carries each, NUL, and the line's limit.
   3. The output is found between two markers that `printf` escapes make,
      so that neither the terminal's echo of the input nor dash's own `-v`
      echo, which 40.3.1 measured as a second echo of each line, holds
      them. It is compared with the payload as the pty's output processing
      changes it, LF becoming CR LF for one, measured by the implementing
      task.
   4. Two cases, one per level, each its own: `test_bootstrap_dash`'s, over
      the console role's pty, through bootstrap, bwrap and dash, with no
      browser (task 7.8.1); and `test_integrate_wire`'s, over the whole
      connection, the page's `console.input` pushes through ttyd, the pty,
      bootstrap, bwrap and dash, and back as `console.output` blobs,
      compared byte for byte (7.5 item 5, task 7.8.8).
   5. `console.read` stays text. The case of `test_integrate_wire` that was
      to read the same binary output through it and expect an `error` line
      of `wire.output_invalid`, `binary_read`, is removed by 4.6, as the
      coordinator decided on 2026-10-30, with the path it reached: a
      `console.read` of output that is not UTF-8 throws
      `wire.output_invalid` inside `ConsolePort.message_take`, in the
      socket's message listener, before the port calls its line receiver.
      That is a fault of the thread that holds the port, by design, and no
      `error` line answers the read. On the headless page's main thread the
      error overlay takes the fault, its stop function sends an `error` line
      to the driver, and the block fails. The refusal stays pinned on the
      real `ConsoleReader` by `test_wire`'s `TestStrictText` in group A.
      The causes: the maintainer's request, log item 44, is met by
      `binary_echoed` with its two breaks; the read case was the
      coordinator's own addition, item 45.6; and the two other designs cost
      a new block or a product change that no requirement asks for. The two
      designs, kept so that nothing is lost: the case in a block of the side
      `workers`, where a fault of the worker's thread reaches the test's end
      as its `error` line, the worker holding the `ConsolePort` with
      `worker_ai.console_register` and a handler of the test's own that
      submits `console.read`; or `ConsolePort` answering a failed read's id
      with an `error` line, as `http.HttpPort` answers a failed fetch.
      Whether the AI's console tool should fault its thread on binary
      output is a product question, which the coordinator takes to the
      maintainer.
   6. Each case is shown to catch a connection that is not binary by a
      deliberate break, measured and then undone, which must fail it at
      once. At the pty: the payload goes through a UTF-8 decode and encode
      with replacement before it is written. In C: `wire.ConsolePort` sends
      the input as a text frame, or decodes the output as text before it
      makes the blob, an edit of `ts/wire.ts` made for one run under the
      run lock and restored byte for byte, its SHA-256 checked, as 5.5's
      break of the TypeScript producer was.
   7. Measured by task 7.8.1 on 2026-10-30 in the console role's pty, a pty
      of `pty.openpty` as the tests and ttyd make it, through bootstrap,
      bwrap and dash 0.5.12 on Linux 6.18, at level 1, each byte value alone
      in a heredoc line of a run of its own, typed plainly and after `0x16`:
      1. The pty's modes, which the console role leaves as the pty starts:
         input `ICRNL` and `IXON`; output `OPOST` and `ONLCR`, no tab
         expansion; local `ISIG`, `ICANON`, `ECHO`, `ECHOE`, `ECHOK`,
         `ECHOCTL`, `ECHOKE` and `IEXTEN`; no `IUTF8`; `VEOL` and `VEOL2` 0,
         which is disabled.
      2. The 12 bytes the line discipline acts on, each typed after `0x16`:
         `0x03`, VINTR, ended the console role with `KeyboardInterrupt`;
         `0x1c`, VQUIT, killed it by SIGQUIT; `0x13`, VSTOP, and `0x1a`,
         VSUSP, left no output within 3 s; `0x04`, VEOF, `0x11`, VSTART,
         `0x12`, VREPRINT, and `0x16`, VLNEXT, were removed; `0x15`, VKILL,
         `0x17`, VWERASE, and `0x7f`, VERASE, erased; `0x0d` became LF by
         `ICRNL`. `0x0a` ends the line, so the payload's line ends are LF
         typed plainly. Every other byte from `0x01` to `0xff` came back
         plainly, `0x0f`, VDISCARD, which Linux does not act on, and `0x80`
         to `0xff` among them.
      3. After `0x16` each of the 12 came back, and `0x0a` still ended the
         line.
      4. NUL is left out: the line discipline carries it, plainly or after
         `0x16`, which `cat` reading the tty showed by giving it back, and
         `printf '\000'` prints it, but dash's heredoc dropped it both ways,
         since dash deletes NUL from its input.
      5. The line's limit is 4095 bytes before its LF: a longer line kept
         4095, the rest dropped with no error. `0x16` is not stored and does
         not count: 4095 pairs, 8190 bytes typed, gave 4095.
      6. The output processing: `printf` of every byte from `0x01` to `0xff`
         came back with only LF made CR LF.
      7. The payload, `python.test_bootstrap_dash.binary` in the gold, as
         `payload` and `output` in base64 under `d`, with the 12 bytes as
         `acted`: four lines, `0x01` to `0x09`, `0x0b` to `0x7f`, `0x80` to
         `0xff`, and the sequences `80`, `c0 af`, `ed a0 80` and `ff`, 265
         bytes with their LFs, every byte value but NUL, printed as 269 bytes,
         each LF as CR LF. The markers are `<<B>>` and `<<E>>`, typed as octal
         `printf` escapes, and the command line is the start marker's
         `printf`, `cat <<'END'`, the end marker's `printf` and `exit 0`,
         joined by `;`, the payload and `END` typed after it. It came back
         byte for byte at levels 0, 1 and 2, about 25 ms a run.
      8. The break at the pty: the payload decoded as UTF-8 and encoded with
         replacement before it is typed gave 539 bytes back for 269, and
         `test_console_binary` failed at its first comparison, on the first
         run; undone, the file's SHA-256 checked.
      9. Measured by task 7.8.8 on 2026-10-30 over the whole connection,
         the page's `console.input` pushes through ttyd, its pty, bootstrap,
         bwrap and dash, and back as `console.output` messages, at level 1:
         1. The payload of `typescript.test_integrate_wire`: 17 lines, one
            `console.input` push each, after the command line's push and
            before `END`'s. Sixteen are the byte values in runs of 16, `0x01`
            to `0xff` but NUL and LF; the last holds the sequences `80`, `c0
            af`, `e0 80 af`, `ed a0 80` and `ff`. That is 281 bytes with their
            LFs, the 12 bytes of item 7.7.2 each after `0x16`. The markers
            are `<<xsjs-begin>>` and `<<xsjs-end>>`, typed as octal `printf`
            escapes.
         2. ttyd changes nothing either way: the 298 bytes between the
            markers are the payload with only LF made CR LF, as item 7.7.6
            measured at the pty, equal by size and SHA-256 to the gold's
            line. ttyd's token is `""` with no `--credential`, and the page's
            close of tty 0 gives the close code 1000, as task 7.8.2
            measured.
         3. The breaks of item 7.6 in C, each on the first run: the input
            sent as a text frame, and the output decoded as text before its
            blob, each gave 574 bytes for 298, every byte that is not UTF-8
            replaced, and `binary_echoed` failed at once, the rest of the
            block ending by failfast. Each was undone, and `ts/wire.ts`'s
            SHA-256 checked equal to its own before.
         4. The block takes about 1.1 s in the stream, and 3.5 s of wall
            time alone with the bring up.
8. dash's controlling tty, by the maintainer's message of task 12 of
   `tmp/tasks_30_2127.md`, "re """can't access tty; job control turned
   off""" no this has to be fixed, add that to the plan.", planned and not
   yet built. Measured on 2026-11-03 under `build/repro/tty/` as `xsjs`,
   bubblewrap 0.9.0, each argv on a pty of its own whose child leads its
   session with the pty as its controlling terminal, as ttyd starts the
   console role:
   1. The argv of now: bwrap's `--new-session` gives the shell a session
      with no controlling terminal, so dash writes the line on job
      control, `$-` is `si`, and `exit 7` returns 7.
   2. The argv without `--new-session`: dash shares the console role's
      session and its tty, job control is on and `$-` is `smi`, but at its
      exit dash cannot set back the process group it found, which lies
      outside its pid namespace; it writes "Cannot set tty process group
      (No such process)" and returns 2 for `exit 7`. Refused.
   3. util-linux's `setsid --ctty` before dash inside the sandbox: the pty
      is still the console role's controlling terminal, so taking it is
      refused, "Operation not permitted". Refused.
   4. The design: the console role gives up the pty as its controlling
      terminal by `TIOCNOTTY` on fd 0 just before it starts bwrap, its
      `SIGHUP` ignored for that call alone, since a session leader's
      `TIOCNOTTY` sends its own process group SIGHUP, and then restored to
      the handler it had. Inside the sandbox, where bwrap's init leads the
      session and the shell's process is pid 2 of process group 1, a step
      of Python's standard library, `python3 -I -c`, calls `os.setsid()`
      and `TIOCSCTTY` on fd 0, then `os.execv` of `/bin/dash` with dash's
      own arguments, `-v` in the verbose form. Measured: no line on job
      control, `$-` `smi`, `jobs` lists a background job, and `exit 7`
      returns 7. `--new-session` is kept.
   5. What it changes: the argv constant of `python/bootstrap.py`, the
      maintainer's exact command of this section's first paragraph,
      gains the Python step before dash; its stub's header and the gold
      copies of the argv follow (item 2.4); the console role's start of
      bwrap gains the release; and item 5's measurements are made again,
      `$-` and the codes of item 5.4 among them, since a dash that holds
      the pty as its controlling terminal takes the hangup of its own
      session when ttyd closes the pty. The line on job control leaves
      every output; item 2.3 stays, for whatever a sandbox writes first.
   6. The Python inside the sandbox starts no command line utility: it
      replaces itself with dash, which the maintainer gave, by the
      standard library alone.

7.5 The driver's phase C and its blocks, every new or changed API given
before any code.

1. `python/test_all.py`, which has no stub:
   1. `_C_INTEGRATION`, the blocks of C with their labels, last in
      `_PHASES`. The blocks of C join `_CHROME_BLOCKS`, since a page load
      runs each, and a new set, `_TTYD_BLOCKS`, names the blocks whose page
      ttyd serves.
   2. `RootServer`, a new class. For one block it makes a root under
      `build/` as the start script makes the server's root: the `python/`
      modules of `powershell.runtime_modules`, the seed, `i18n/en-US.json`,
      `settings.json` with `debug` true, and the checkout's gold as
      `test_settings.json`. It starts `build/ttyd/ttyd` (3.15) on it, in a
      session of its own, with the start script's options, `--port 0`,
      `--interface` the bind address, `--writable`, `--check-origin`,
      `--terminal-type`, `--url-arg` and `--srv-buf-size`, and `--index`
      `build/headless.html`, running `python3 ROOT/python/bootstrap.py
      --root ROOT`, with `--main-loop` when the block's gold names one. It
      reads ttyd's version and port from ttyd's log and gives the page's
      address, `http://ADDRESS:PORT/`. At the block's end it stops ttyd's
      process group by SIGTERM, a ttyd still running after the gold's
      seconds being killed and failing the run, then removes the root.
      ttyd's log goes to the block's log, which a failure's cause holds
      (6.3).
   3. The gold of a block of C, `typescript.<block>.root`, an object whose
      `main_loop`, present only when the block's server runs one, names a
      main loop file of `python/` that is copied into the root's
      `main_loop/`. The seconds ttyd has to stop are a value of
      `typescript.test_headless`, the gold of the headless realm's window
      and server.
   4. `PageRunner` takes the page's address of a block of `_TTYD_BLOCKS`
      from its `RootServer`, and that of any other block from the local
      HTTP server, as now. The root and its ttyd start in `block_prepare`,
      outside the block's timer, and stop after the block's `about:blank`,
      before the relay ends.
2. `ts/test_headless.ts`: an entry for each block of C in its block table,
   of a side it has, UI or worker; no new side. A change of the bring up
   that the page served by ttyd needs is task 7.8.2's, under the lock.
3. `test_worker_ai_console`, UI side, a block of line cases (3.6), gold
   `typescript.test_worker_ai_console`: a real synchronous
   `queue.TaskQueue` of thread `ai` in the page's realm, with
   `worker_ai.console_register` registered through the real dispatch; its
   `console` owner a real `wire.ConsolePort` at the page's address; its
   `ui` owner one of a linked pair of `queue.LocalPort`s (4.7), the test's
   end the other, as 5.9 item 2 joins a lane. The cases: `console_opened`,
   the UI's `console.open` relayed to the port, which fetches ttyd's token
   and opens tty 0, then `worker.console_opened` answering the UI with the
   token, which with no `--credential` is ttyd's own, measured; and
   `console_closed`, the UI's `console.close` relayed and tty 0's end
   answered. It sends ttyd no first message, so no process starts (7.4
   item 4). Its doubles, `TasksDouble` and `register_route`, go (4.4).
4. `test_wire_end`, UI side, gold `typescript.test_wire_end`. Its points
   arrive after their calls, so it becomes a block of line cases, or a
   block that writes its own points through `TAPTestRunner.block_start`
   as `test_line_case` does (3.7), on a real `wire.WirePort` at the page's
   address to the block's server, whose replies stream into a real, empty
   `substrate.CacheFiles([])`, as `test_wire_port`'s do in A, its root's
   main loop the stock one or `echo_loop.py`, by what its cases need. Each
   of `TestWireEnd`'s tests becomes a case that reaches its path, `wire_end`
   on an open socket waiting for the drain and then calling its function,
   `wire_end` on a socket already closed, or a fault in a socket message
   leaving the socket open, or is removed by 4.6 with the path it reached.
   `SocketDouble`, written into the private `port["socket"]`, the call of
   the private message event, and `UnusedSink` go (4.4, 4.7). A case that
   opens a `WirePort` waits for its close before the next case opens one,
   so that the next server finds the root's lock free.
5. `test_integrate_wire`, new, UI side, gold `typescript.test_integrate_wire`,
   through dash (7.4) from its second case on: `wire`'s block of line cases
   through ttyd's tty 0, the integration block 3.5 left to C, holding the
   binary heredoc of 7.4 item 7. The test's end speaks to a real
   `wire.ConsolePort` at the page's address itself, with no queue, as
   `test_integrate_http`'s speaks to `http.HttpPort` (3.6 item 1), since
   a queue passes on no request that has an id, as `console.open` has, which
   only a handler's submit sends. The port's receiver is
   the test's own (4.3): it passes each line on to the test's end but the
   `console.output` pushes, whose data of kind `0` it joins, and once the
   end marker has come it passes the bytes between the two markers on as
   one line, its blob compared by size and SHA-256 (3.6 item 3) with the
   gold's line, which holds the payload after the pty's output processing,
   in base64 under `d` (3.6 item 2). The port's other end is the test's own
   too: it posts each line to the port but the push `console.close`, for
   which it calls `ConsolePort.console_close`, the port's API for the
   close, which takes no line; and the port's close receiver passes the
   push `console.exit` with the close code on, as the AI worker pushes it
   (`API/ts/wire.d.ts`). The cases: `console_opened`,
   `console.open` answered with ttyd's token; `first_sent`, ttyd's first
   message with the gold's size, which expects no line, since every output
   push is joined, and waits its seconds; `binary_echoed`, the heredoc typed
   as `console.input` pushes, one per line, its output back between the
   markers, byte for byte; and `console_closed`, `console.close` sent and
   tty 0's end answered as `console.exit` with the code. `binary_read`, a
   `console.read` over that same output, is removed (7.4 item 7.5).
6. `test_tools_browser_console`, worker side, gold
   `typescript.test_tools_browser_console`, through dash (7.4): a block of
   line cases on the topology of B's `test_integrate_tools_browser`, a real
   `mcp.Server` on a real queue with the real `Store`, `CacheFiles` and the
   realm's pool, with `worker_ai.console_register` on the same queue and a
   real `wire.ConsolePort` at the page's address as its `console` owner.
   The far end of its `ui` lane is scripted by 6.9 item 3.1, answering
   `permit.ask` with the gold's `permit_accept` or `permit_always` and
   `console.show` with Empty. The cases: tty 0 opened from the `ui` side,
   its `console.open` relayed and ttyd's first message, with the gold's
   size, sent as `console.input`, as the UI's console view does; then the
   tool's runs as `mcp` tool calls: `recorded`, `echo hi` asked, accepted,
   shown, typed and read back to the prompt, its result the gold's
   `{"output":"hi\n","timed_out":false}`; `always`, Always Allow and then a
   second command with no ask; `counted`, the permits numbered 1 and 2;
   and `expired`, `sleep 600` read until the tool's timeout, its result the
   gold's `result_expired`. tty 0's output on the `ui` lane is not
   compared, by 7.4 item 2.3; the tool's results, which hold only the
   output since their command, are. The four tests and their doubles,
   `StoreDouble`, `ServerDouble`, `TasksDouble` and the wakes called
   directly, go (4.4). Written by task 7.8.4 before its code, each part
   class B (11.2 item 28) with its cause:
   1. The junction. The queue's owners are `worker_ai.owners_make()`, the
      AI thread's, with `mcp` its own, as B's block adds it. Its `server`
      and `ui` lanes are each one of a linked pair of `queue.LocalPort`s
      (4.7), the other end held by the block's junction, whose functions are
      the block's own (4.3), as `test_integrate_worker_ai`'s junction is
      (6.9 item 5.2), and the test's end is a real `queue.ThreadPort` over a
      MessageChannel whose other end the junction holds. A case's `mcp` line
      goes on the `server` lane and every other line it sends on the `ui`
      lane. Every line of the `server` lane goes to the test's end; every
      line of the `ui` lane goes to the test's end but `console.output`,
      which is not compared, and a request also goes to the scripted far end
      of 6.9 item 3.1, a second real queue of thread `ui` in synchronous
      mode joined to the junction by a linked pair of `LocalPort`s, whose
      replies go back on the `ui` lane. The causes: the relay answers a
      `console.open` from the `ui` side on the `ui` lane, and a far queue
      there would refuse that reply, which it never asked for, with
      `queue.reply_unknown`; the asks on the `ui` lane are what `counted` and
      `always` are seen by; and with both lanes local the test's end gets
      the lines in the order the queue sends them.
   2. The first prompt. The junction holds the cases' `mcp` lines until
      dash's first prompt, the gold's `prompt`, has shown in tty 0's output,
      its messages of the gold's `output_kind`, then posts them in order, so
      that the first command's read starts after it (7.4 item 2.3). The
      cause: the console view sends ttyd's first message as soon as the open
      is answered, and a read started before the first prompt ends at it,
      the job control line its output. The other design, not chosen: a case
      that sends the first message and expects nothing, waiting its seconds,
      which costs them in every smoke run and rests on dash starting within
      them.
   3. The cases, in order: `opened`, `console.open` sent from the `ui` side
      and answered with ttyd's token, which with no `--credential` is
      empty, read in ttyd 1.7.7's `http.c`; `recorded`, ttyd's first message
      sent with the gold's size, then `echo hi` asked as permit 1, accepted,
      shown, and its result the gold's; `counted`, `echo 2` asked again, as
      permit 2, since Accept lasts one command; `always`, `echo 3` asked as
      permit 3 and allowed always; `allowed`, `pwd` with no ask, its output
      dash's start directory `/tmp` (7.4 item 5.2); and `expired`, `sleep
      600` with no ask, read until its timeout of 2 s, its result the old
      gold's `result_expired`, now in the expected reply line, as every
      result is. The ids of the asks and shows are the queue's own,
      numbered from 1, the relay's `console.open` taking 1. The far end
      answers each ask with the gold reply its number names, `permit_accept`
      or `permit_always`, the ask's `permit` set in it. The causes of the
      order and of `allowed`: a block has one tool context, whose permit
      count and Always Allow last the realm's life, so the asks are counted
      before Always Allow ends them; and a case sends its lines at once, so
      the command after Always Allow is a case of its own. The old tests by
      case: `test_console_recorded` is `recorded`, `test_permits_counted` is
      `recorded` and `counted`, `test_permit_always` is `always` and
      `allowed`, and `test_console_expired` is `expired`.
   4. The port's close receiver, the block's own, pushes the end of tty 0
      to the UI as `console.exit` with its code, as `test_worker_ai_console`
      does; no case closes tty 0, so that line fails a case or the block if
      it comes. The page's address is `/` at the worker's `location.origin`,
      since a worker made from a Blob URL has a `blob:` address of the
      page's origin, which no relative path resolves against.
   5. The gold's `root` is empty: the stock main loop.
7. `test_console_open`, new, UI side, gold `typescript.test_console_open`,
   through dash (7.4), wave 3: `console_view`'s open path. The page's real
   handlers, with the real `ConsoleView` and the real xterm.js `Terminal`,
   as B's `test_integrate_console_view` builds them, on a real UI queue
   whose `ai` owner is one of a linked pair of `queue.LocalPort`s; at the
   other end, a second real queue of thread `ai` in the same realm with
   `worker_ai.console_register` and a real `wire.ConsolePort` at the page's
   address, the UI side handling none of the types the relay registers, as
   6.9 item 3.1 requires, which the task checks first. The cases: the
   console shown, its `console.open` relayed and answered with ttyd's
   token, ttyd's first message sent with the terminal's measured size,
   dash's first prompt drawn in the terminal and read back from the DOM, a
   key typed and its echo drawn, and the close.

7.6 The browser test's rungs. `python/test_browser.py` keeps its roots,
each served by its own ttyd, and drives `chrome-headless-shell` through
`devtools.LinuxPipe` (36.4). ttyd is `build/ttyd/ttyd` of 3.15's bring up,
and a missing one names `python/ttyd_build.py` in place of
`xsjs_install.ps1`. Its rungs keep the waits they have, the rung timers
bounding `devtools.py`'s through `deadline_set`, since the program runs
after the stream and outside every block. Each rung is kept, moved or
removed by these rules, and task 7.8.6 records each with its fate:

1. A rung that reaches ttyd, the server through it, or the ttyd page's own
   bring up stays, rewritten without doubles.
2. A rung that needs no ttyd goes when an A or B case reaches its code path
   with the same far end, recorded with that case (3.1). Otherwise it
   stays, on the headless page that ttyd serves: only the browser test's
   stub server gives its far end, an answer held, released, stalled or
   recorded, or it needs the browser's own fetch, which 10.2 tests only in
   B's media block. By 4.4 a test moves to the group that can give it its
   real parts, here C.
3. A rung that needs a double with no real replacement is removed by 4.6,
   recorded with the code path it reached.
4. The probe kit's doubles go. `_WORKER_STUB`, which replaced `Worker` so
   that the ttyd page started no worker of its own, goes by the pages of
   the probe, credential and echo roots being the headless page served by
   their ttyd, which starts none (7.2 item 2). `probe.sink`, a hand made
   `jslb.BlobSink`, a double of the cache by Question T3 A, goes for a
   real `substrate.CacheFiles([])` where no blob streams to a file; for the
   drain rungs, whose echoed blobs of 8 MiB are over `overflow_bytes`, for
   either a real cache over real slots in a worker of the page or echoes
   within `overflow_bytes`, whichever keeps the rung's purpose, the socket
   filled while ttyd is stopped, measured by the task. The drain poll rung's
   reads of the port's private `socket.bufferedAmount` and `poll_id` go
   (4.7), its public checks kept: every echo back equal by SHA-256 once
   ttyd continues, and no fault. `_BLOB_PATCH` and `_WORKER_THROW`, which
   replace the platform's `Blob` and `Worker` (4.5), go with their rungs,
   and the kill rung's store queue, `{ line_notify: () => undefined }`,
   with its rung.
5. The rungs by root, with the fate these rules give them now, which the
   task confirms case by case against the gold of A's and B's blocks:

| Root and page | Rungs | Fate |
| --- | --- | --- |
| suites, the ttyd page, smoke | typescript suites; typescript suites in order | kept: the two documents of no block (7.2 item 3), through the real server; the order rung checks that the worker's document is whole before the UI's first line, its lists of modules going with the modules |
| | fresh root; verbose ring; verbose sink; long tasks; traced synchronous load found; no synchronous load on the UI thread | kept |
| | kill between file and row | goes: B's `test_substrate_crash` reaches its path on the real bring up (6.11) |
| | worker hang keeps the TAP lines before it | kept, the UI's cut document holding its version line alone |
| faults, the ttyd page, normal | thrown error; first fault only; reload; rejection; failing script, image and link; failing with neither address; failing object; failing SVG image | kept: real faults (4.6), reaching the page's stop function, the worker's `wire_end`, the server's bail out and its exit 1 |
| | worker fault posted; worker throws at load | removed by 4.5 with `_BLOB_PATCH`: they reached the page's display of a fault its worker posts, which B's `test_error_overlay_worker` reaches on the worker's side, and of a worker's load error, which no block reaches |
| | write versus append | removed by 4.5 with `_WORKER_THROW`: it reached `error_overlay`'s append while the parser runs a script, which no block reaches; its PNG goes |
| none, the stub's page, normal | stub reachable | kept |
| probe, the headless page by its ttyd, normal | wire first line; blob_max plus one refused; wire_close; error line then close; close without error line; wire token timer; wire open timer; console closed before open | kept, with a real `CacheFiles([])` |
| | console open, close, exit, open | kept, through the console's shell (7.4) |
| | http post; http text and json; http statuses; http closed port; http never answers | go, by A's `test_integrate_http`, its `json_parameters`, `text_answered`, `json_answered`, `status_failed`, `fetch_refused` and `timeout_expired`, unless the task finds a path of theirs no case reaches, such as the post's exact body and headers or the three statuses against the gold's one, which then stays |
| | http preflight; http stalled body; http one line per request; http out of order; http get with a body; http port in a worker; http throwing receiver; queue two replies | kept: the stub's far end or the browser's own fetch |
| | queue scheduling; queue thread port; queue handler throws; overlay strings | go when A's `test_integrate_queue` or B's `test_overlay` reaches the path, else kept |
| | media png kept; media download as blob 1; media network failure; media status; media timeout; media undecodable; media eviction | go, by B's `test_integrate_media`, its `store_kept`, `fetch_kept`, `fetch_refused`, `status_failed`, `timeout_expired`, `store_undecodable` and `fetch_undecodable`, and `test_media_cache`'s eviction |
| credential, the headless page by its ttyd with `--credential`, normal | token with a credential | kept |
| echo, the headless page by its ttyd, the echo main loop, normal | wire drain poll; wire drain timer | kept, by item 4 |
| stalled, the ttyd page, normal | wire first line timer | kept |
| release, the ttyd page, debug false, normal | release runs nothing; console role refused | kept; neither starts a shell |
| locked, the ttyd page, normal | error before the first line | kept |

6. The methods of `devtools.Browser` that the browser test calls and that
   no suite tests on the Linux browser, `screenshot_save`, `trace_start`
   and `trace_end`, `worker_pause`, the page's lifecycle `events` and
   `page_close`, were tested only by `test_devtools_powershell` on Windows,
   offline (3.16). By the order of the project rules each is tested on the
   real `chrome-headless-shell` first, in `test_devtools_chrome`, before
   the browser test uses it: a PNG of the window's size, a trace holding a
   synchronous load, a worker paused in its debugger, the load events of a
   page, and a page closed while another stays, as the Windows suite's
   header gives them.

7.7 The wire test. `python/test_wire.py` drives `chrome-headless-shell`
through `devtools.LinuxPipe` (36.4) in place of `devtools.WindowsRelay()`,
and ttyd is `build/ttyd/ttyd` of 3.15's bring up, a missing one naming
`python/ttyd_build.py`. Nothing else of its design changes: three roots,
echo, stock and restart, each with its own ttyd serving `build/test_wire.html`,
the wire rungs on the ttyd page's own bring up, the stream read from the
root's TAP file as it grows, and its checks around the page. The stock
root's `console` and `lines` rungs type into dash on tty 0 through the
console's new shell (7.4), and run once task 7.8.1 has landed; `console_last`
and the `lines` rung's whole output are compared from the typing on, after
the first prompt (7.4 item 2.3). `ts/test_wire_rungs.ts` changes only for a
fix the run shows.
Recorded on 2026-10-30 by the review of commit 2cab3f3, class B: the
restart root's check of the restarted server's log takes a `verbose.put`
push of the page's log in place of the page's refusal, a push in flight
across the exec, as the file's header says (Question T13); and the check of
each root's exit by ttyd's log fails when ttyd logs the exit after the
socket's close, with no code (Question T10). Since 2026-11-01, by Question
T10 A, `third_party/ttyd/patches/02_exit_code.patch` has ttyd log
`process exited with code N` in both orders, keeping `process killed with
signal N` for a signal's death, and `exit_check` is exact unchanged: three
smoke runs passed, the stock root's third with the socket closing first.
Since 2026-11-01, by the maintainer's answer to Question T7, the echo root's
rung `large`, a blob of 128 MiB, is removed, since no size of the system
exceeds `blob_max`, and ttyd's resident size is read after `fit`, the
largest blob.

7.8 Wave 2, in parallel, each task on the files it owns. A shared file is
edited only under its lock (8.5), and every run of `python/test_all.py`,
`python/test_wire.py` or `python/test_browser.py` holds the run lock (8.6).
A task that needs another's landing writes and compiles first, and runs
once the coordinator says that task has landed. Each task follows 4.9, stub
first, and ends with the report of 4.9 item 4.

1. 7.8.1, the console's shell (7.4). Owns `python/bootstrap.py` with its
   header, `API/python/bootstrap.pyi`, `python/test_bootstrap_dash.py`, and
   `python/test_bootstrap.py` where a comment states the old shell. Under
   the lock: the gold `python.test_bootstrap_dash` in `test_settings.json`,
   which gains the argv's copy (7.4 item 2.4) and the values the shell
   prints, by 7.4 item 5; `python/test_all.py`'s `_LATER`, `_MODULES` and
   `_COUNTED`, `test_bootstrap_dash` leaving `_LATER` for the Python unit
   phase after `test_bootstrap`, `smoke-test`, still counted for
   `bootstrap`. Writes the binary case of 7.4 item 7 at the pty's level,
   its deliberate break failing it at once and undone, and writes into
   7.4 item 7, under this plan's lock, the values it leaves to the
   implementing task, which 7.8.8 then takes. Reports any other file of the
   tree that starts dash or states that the console's dash runs in the
   root.
   Runs `python3 python/test_all.py --stream --module test_bootstrap
   --module test_bootstrap_dash`, smoke and normal, then `--stream`. Done
   when both suites pass, the three dash tests kept through the shell's
   output and the binary case with them, a deliberate break of the argv's
   copy in the gold fails `test_console_level` and is undone, and the whole
   stream passes.
2. 7.8.2, the driver's phase C and `test_worker_ai_console` (7.5 items 1
   to 3). Owns the phase C of `python/test_all.py`, under the lock, and
   `ts/test_worker_ai_console.ts`. Under the lock: its gold, the gold
   `typescript.test_headless` for ttyd's stop seconds, and
   `ts/test_headless.ts` for its entry and for any fix of the bring up on
   the page ttyd serves. Needs 3.15's bring up, landed by the log's task
   36.6.1.3. Runs `python3 python/test_all.py --stream --module
   test_worker_ai_console.ts`, smoke and normal, with ttyd's log of the
   block read once to show that no process started, then `--stream`. Done
   when the block passes, a deliberate break of its gold fails it and is
   undone, no root or ttyd it started is left after the run, and the whole
   stream passes.
   1. Status, 2026-10-30: done. `_C_INTEGRATION`, `_TTYD_BLOCKS`,
      `RootServer` and the gold `typescript.test_worker_ai_console.root` and
      `typescript.test_headless.stop_seconds`, 5. A block of C is added by
      one entry in `_C_INTEGRATION`, its gold's `root`, and its entry in
      `ts/test_headless.ts`. `--stream --module test_worker_ai_console.ts`
      passes 2 of 2, smoke 2.45 s and normal 2.81 s from start to end, the
      block about 0.13 s in its timer; `--stream` passes 111 of 111 blocks,
      1739 points, in 69.95 s.
   2. Measured: ttyd serves `build/headless.html` as `--index` whole, 5298729
      bytes of the same SHA-256, and the page holds every script and style
      inline, so no change of the bring up was needed. With no
      `--credential` ttyd's token is `""`; the close code of tty 0 closed by
      the page is 1000; SIGTERM stops ttyd in about 3 ms. ttyd's log of the
      block, read once by a break of `stop_seconds` to 0, which killed ttyd
      and failed the run naming it, holds the page's and the token's HTTP
      lines, one WebSocket opened and closed, logged as `/ws` without its
      query, and no `started process` line.
   3. The break of the block's gold, the expected token, failed
      `console_opened` at once, its diagnostic naming the token `""`; the
      gold was restored and its text checked byte for byte.
   4. Decided by the task, class B, each with its cause. The `ui` owner is a
      `queue.ThreadPort` over a MessageChannel, not one of a linked pair of
      `queue.LocalPort`s as 7.5 item 3 has it, since `line_case.block_run`
      takes the test's end as a `ThreadPort` whose other end the queue owns
      (3.6 item 1). `console_closed` expects, after the Empty reply, the
      `console.exit` push with code 1000, which the port's close receiver,
      the test's own function (4.3), pushes to the UI as the stub of
      `wire.ConsolePort.close_receive` says the AI worker does, since no
      product code pushes it yet. The stop runs outside the block's timer
      by 7.2 item 4 and before the relay ends by 7.5 item 1.4: the block's
      alarm is cancelled and the deadline's armed before it. ttyd's log is a
      file of its own, read every 10 ms for the version and port, and copied
      to the block's log at the stop, so that no pipe fills while the block
      runs. A root made for a block that never ran, as when the deadline
      passes before its timer starts, stops when the browser stops, its log
      to stderr. The realm's parent line is relayed when it comes, so a ttyd
      killed at the stop fails the run after the block's parent line.
3. 7.8.3, `test_wire_end` (7.5 item 4). Owns `ts/test_wire_end.ts`. Under
   the lock: its gold, its entry in `ts/test_headless.ts`, and its entry in
   `_C_INTEGRATION` once 7.8.2 has landed. Writes and compiles at once, and
   runs after 7.8.2 has landed: `--stream --module test_wire_end.ts`,
   smoke and normal, each case broken once on purpose and undone, then
   `--stream`. Done when the block passes and its report names each of
   `TestWireEnd`'s tests as a case or as removed with its path.
   1. Status, recorded on 2026-10-30 by the review of commit 2cab3f3,
      which found no record of it: `test_end_waits` is the point
      `end_waits`, `test_end_closed` the points `end_closed` and
      `close_ended`, and `test_fault_open` is removed by 4.6 with the path
      it reached, `WirePort.message_event`'s catch, which sets `taking`
      false, stops the timers and leaves the socket open, so that a later
      message is not taken and a line can still be posted. No point reaches
      it: the catch throws the fault on in the socket's message listener, a
      fault of the page's thread, which the error overlay takes and which
      fails the block, so no point can read the socket left open after it.
4. 7.8.4, `test_tools_browser_console` (7.5 item 6). Owns
   `ts/test_tools_browser_console.ts`. Under the lock: its gold, its entry
   in `ts/test_headless.ts`, and its entry in `_C_INTEGRATION`. Writes and
   compiles at once, and runs after 7.8.1 and 7.8.2 have landed, as 7.8.3
   runs. Done as 7.8.3, its report naming each of the four tests as a case.
   Done on 2026-10-30: the six cases of 7.5 item 6.3 pass, smoke and
   normal, the block about 2.4 s, `expired` about 2 s of it, its read's
   timeout; each case broken once in its gold fails at once and is undone,
   `allowed`'s break, Always Allow not given, failing the block with the
   scripted UI's missing answer to permit 4 as the cause; `--stream` passes,
   114 blocks; no ttyd, bwrap, dash or root of the block is left.
5. 7.8.5, the wire test on Linux (7.7). Owns `python/test_wire.py` and
   `ts/test_wire_rungs.ts`. Under the lock: the gold `python.test_wire`.
   Runs `python3 python/test_wire.py --smoke-test` and `--normal-test`, the
   stock root's `console` and `lines` rungs once 7.8.1 has landed. Done
   when both categories exit 0. A fault of `devtools.py` goes to 7.8.6.
   1. Status, 2026-10-30, measured in Anthropic's cloud container with
      `--anthropic`: `--smoke-test` exits 0, and `--normal-test` fails at
      the echo root's rung `fit`, the page's `Bail out! Array buffer
      allocation failed`. The rung echoes one blob of `blob_max`,
      2147483391 bytes, and chrome-headless-shell 153.0.8010.12 allocates
      no ArrayBuffer over 2145386496 bytes, 2^31 less 2^21, PartitionAlloc's
      largest direct map, measured by bisection on a page's main thread,
      the same with and without its sandbox, while 2000 MiB is allocated.
      Question T7, answered on 2026-11-01: `blob_max` is 10485760, and
      `fit` echoes a blob of 10 MiB, measured passing in 1.1 s to 1.2 s in
      two normal runs, ttyd's peak resident size 15468 KiB. One of the two
      failed at the restart root's first point (Question T16).
6. 7.8.6, the browser test on Linux (7.6, 7.2 items 3 and 5). Owns
   `python/test_browser.py`, `ts/test_all.ts` under the lock (23.6.1's
   shared list), and, for 7.6 item 6 and any fix the Linux browser needs,
   `python/devtools.py`, `API/python/devtools.pyi`, `python/test_devtools.py`
   and `python/test_devtools_chrome.py`, with `WindowsRelay`'s offline note
   in the headers of `devtools.py` and its stub (3.16 item 3). Under the
   lock: the gold `python.test_browser` and `python.test_devtools_chrome`.
   Runs `python3 python/test_all.py --stream --module test_devtools
   --module test_devtools_chrome` after any change of `devtools.py` or its
   suites, then `python3 python/test_browser.py --smoke-test` and
   `--normal-test`, the console cycle rung once 7.8.1 has landed. Done when
   both categories exit 0, each PNG has the gold's size, a document of no
   block is taken (7.2 item 3), and its report confirms the table of 7.6
   item 5, each moved rung with the case that reaches its path and each
   removed rung with its path.
   1. Status, 2026-10-30, by the review of commit 2cab3f3, which found no
      record of it: the rung `stage 0: worker hang keeps the TAP lines
      before it`, which 7.6 item 5's table keeps, was removed by the commit
      with `_AI_THREAD` and the protocol's `worker_pause`. Restored for
      three runs of `--normal-test` and undone, the file's SHA-256 checked,
      each run failed it after 60 s waiting for the worker `ai` to pause:
      with documents of no block the worker runs no JavaScript once its
      document is written, so `Debugger.pause` has no statement to stop at,
      and the UI's document of two lines is whole once its first line is
      in. Removed, class B, with the path it reached: the worker's relay of
      the UI's TAP lines, cut by a pause of the worker in the middle of the
      UI's document, which no part of the plan reaches now.
      `Browser.worker_pause` stays tested by `test_devtools_chrome` (7.6
      item 6), and no rung calls it.
   2. Status, 2026-10-30, measured in Anthropic's cloud container with
      `--anthropic`: `--smoke-test` exits 0, and `--normal-test` fails at
      the probe root's rung `stage 5: blob_max plus one refused`, whose
      `line_post` of a blob of 2147483392 bytes throws `Array buffer
      allocation failed` before the page's refusal, by the browser's
      largest ArrayBuffer of 7.8.5 item 1. Question T7, answered on
      2026-11-01: the rung posts 10485761 bytes. The drain rungs post
      `blob_max` over `overflow_bytes` echoes, 80 of 128 KiB, in place of
      the gold's `large_bytes`, 128 MiB, which is removed. Measured on
      2026-11-01: the refusal, the drain poll and the drain timer pass,
      80 echoes being more than the stopped socket takes, and the run fails
      later at `stage 5: error before the first line` (Question T17).
7. 7.8.7, the Windows path's documents (3.16). Owns the headers of
   `powershell/test_powershell.ps1`, `powershell/test_lint.ps1` and
   `python/test_devtools_powershell.py`. Under the lock: `_LATER`'s reason
   for `test_devtools_powershell` in `python/test_all.py`. Runs no
   PowerShell, since no test starts a Windows program (35.1). Done when its
   changed files pass the rows of `python/reformat_table.json` for them,
   twice, unchanged on the second run, the comment rule of `test_posix.py`
   holds on them, and ruff and pyright strict pass on its Python files.
8. 7.8.8, `test_integrate_wire` (7.5 item 5, 7.4 item 7). Owns
   `ts/test_integrate_wire.ts`, and `ts/wire.ts` for the deliberate break
   of 7.4 item 7.6 alone. Under the lock: its gold, `ts/tsconfig.test.json`,
   its entry in `ts/test_headless.ts`, its entry in `_C_INTEGRATION`, and
   any string of `i18n/en-US.json`. Writes and compiles at once, and runs
   after 7.8.1 and 7.8.2 have landed: `--stream --module
   test_integrate_wire.ts`, smoke and normal; each break of 7.4 item 7.6,
   under the run lock, failing `binary_echoed` at once, then undone and
   checked by SHA-256; then `--stream`. Done when the block passes, both
   breaks fail it, and any value of 7.4 item 7 it measures beyond 7.8.1's
   is written into this plan under its lock.

7.9 Wave 3, after wave 2:

1. 7.9.1, `test_console_open` (7.5 item 7). Owns `ts/test_console_open.ts`.
   Under the lock: its gold, `ts/tsconfig.test.json`, its entry in
   `ts/test_headless.ts`, its entry in `_C_INTEGRATION`, and any string of
   `i18n/en-US.json`. Needs 7.8.1 and 7.8.2. Runs and is done as 7.8.3.
   1. Design, on 2026-11-03, task 11 of `tmp/tasks_30_2127.md`, before
      its code. The UI side is built as `test_integrate_console_view`
      builds it, the frame fitted to the gold's `rows` and the page's
      elements, on a real UI queue in the mode of `queue_synchronous`,
      the block's file holding its own copy of those builders since the
      task owns no other file. The UI queue's `ai` lane is one of a
      linked pair of `queue.LocalPort`s whose other end is the `ui` lane
      of a second real queue of thread `ai` in synchronous mode, with
      `worker_ai.owners_make()`, `worker_ai.console_register` and a real
      `wire.ConsolePort` at `location.href` as its `console` owner, whose
      close receiver, the test's own, pushes `console.exit` with the
      close code to the UI as `test_worker_ai_console`'s does. The
      test's end is a `queue.ThreadPort` over a MessageChannel on the UI
      queue's lane of thread `server`: `queue.ThreadName` is closed, `ai`
      is the linked port, and the UI thread's table gives `server` no
      type, so a request on it of a type the UI owns runs there and its
      reply goes back on it. The check of 6.9 item 3.1: the relay
      registers `console.open`, `worker.console_opened` and
      `console.close`, and the page's handlers none of them. The probes,
      of the prefix `console_probe.` that the UI owns: `rows`, the
      console's rows read from the DOM as `test_integrate_console_view`
      reads them, from the first that starts with the gold's `prompt` on,
      by 7.4 item 2.3, since dash writes its line on job control first
      (7.4 item 5.1); `phase`, the view's `open_is()` and `open_wanted()`;
      `type`, text typed into the terminal's input; and `close`, the
      view's `close_request()`. The cases: the view hidden and idle;
      `console.show` answered once tty 0 is open; the view open; a wait
      of 2 s, then dash's first prompt read from the rows; `stty size`
      typed and drawn as the view's echo; Enter, a wait of 1 s, then the
      command's line echoed by the tty, its output, the gold's 20 rows
      and the view's 120 columns that ttyd's first message gave, and the
      prompt; the close, a wait of 1 s, then the view shown and idle, so
      that a show would open tty 0 anew. ttyd's token is the empty one,
      the block's ttyd having no credential, and the prompt drawn shows
      that ttyd took the first message. Labelled `smoke-test` (7.2 item
      4), last in `_C_INTEGRATION`, after the blocks of the modules it
      runs; its file in `ts/tsconfig.test.json` before
      `ts/test_headless.ts`, which names it.
   2. Found on 2026-11-03 by the block's breaks, before any change of the
      product for it: in the last break's run, whose own case never ran,
      the page faulted in the case of the close with
      `console_view.closed_phase`, "The console got the reply to
      console.close while it was idle, not closing.". In a queue that is
      not synchronous, `queue_synchronous` being false in
      `settings.json`, a reply's wake is held at the end of the inbox
      when the reply's step runs, so a `console.exit` that came after
      the reply and before that step runs before the wake: `exit_done`
      left the view idle and `close_done` threw. The product has the
      same order across the AI worker's MessagePort; synchronous mode,
      debug only, holds a queue's own items ahead of its inputs and
      hides it. The design, in `API/ts/console_view.d.ts` before its
      code: tty 0's end may come before the wake of the close it
      follows, so the view's new phase `ended` holds an end that came
      while closing; `close_done` takes the wake in `closing`, the
      phase kept until the end, or in `ended`, which leaves the view
      idle, and is refused in any other phase as before; `exit_done` in
      `open` leaves it idle, in `closing` makes it `ended`, and is
      refused otherwise. While `ended` the view takes no input and asks
      for no opening, as while closing. `test_console_view` gains
      `TestClosing.test_exit_first`: the end before the close's wake,
      the view not wanting an opening until the wake, then opened again.
      The other place for it, the queue holding a wake in its last
      reply's place in both modes, is left to the maintainer (11.2 item
      52).
   3. Status, on 2026-11-03: done. Its first run found dash's line on
      job control before the first prompt, which 7.4 item 2.3 keeps out
      of the comparison, so `rows` reads from the gold's `prompt` on; the
      next passed its 11 cases in 4.424 s. Each case broken once in the
      gold failed at that case, the last after the change of item 2,
      before which its run faulted on the race; the gold then restored
      and checked by SHA-256. After the change, 20 runs of 20 passed,
      `test_console_view` with `test_exit_first` passed, and the block
      passed in a `--normal-test` run. `stty size` printed `20 120`. The
      smoke target passed 119 of 119 in 121.303 s of its 180 s, the
      block 4.383 s of it; the normal target passed in 634.118 s.
   4. Overturned on 2026-11-03 by 3.28, the maintainer's answer to
      Question P4: item 2's design in `console_view` goes, the queue's
      wake in its reply's place preventing the race; item 2's finding
      stands.
2. 7.9.2, the order of C and the whole runs. Owns the order of
   `_C_INTEGRATION`, under the lock, and C's layer table, written into this
   plan under its lock. Computes C's layers by 6.8 item 7's method, then
   runs `python3 python/test_all.py` and `python3 python/test_all.py
   --normal-test` whole, and `--tty --stream`, measuring the smoke run from
   its start to the end of `test_browser.py` and moving labels by 7.2 item
   4. Done when both categories pass whole, the smoke run within 120 s,
   each label moved reported with its seconds.
   1. Status, 2026-10-30, the order alone, by the review of commit 2cab3f3:
      `_C_INTEGRATION` is `test_wire_end`, `test_integrate_wire`,
      `test_worker_ai_console`, `test_tools_browser_console`, by 6.8 item
      7's rules read by hand: an integration block follows the unit and the
      integration blocks of the modules that run inside it, so `wire`'s two
      blocks, `WirePort`'s before `ConsolePort`'s, run before the two that
      run a real `ConsolePort`, and `test_tools_browser_console` runs
      `worker_ai.console_register` as `test_worker_ai_console` tests it. C's
      layer table by the compiler API, the whole runs and the label moves
      wait.
   2. Status, 2026-11-03, task 11 of `tmp/tasks_30_2127.md`, the order
      alone, by the same rules read by hand: `test_console_open` last,
      since it runs `wire.ConsolePort` and `worker_ai.console_register`,
      which `test_integrate_wire` and `test_worker_ai_console` test, and no
      other block of C runs `console_view` or `page`. With it the whole
      runs passed: the smoke target 119 of 119 in 121.303 s, the normal
      target 121 of 121 in 634.118 s, and `--tty --stream` 119 of 119 in
      118.573 s. C's layer table by the compiler API and the label moves
      wait.
3. 7.9.3, the check agent, alone, last: `python3 python/reformat.py` twice
   over the whole tree, staged first and unstaged after; both configs; ruff
   and pyright strict over `python/`; nothing staged, no lock left,
   `tmp/run_lock` in place, no stray bytecode, and no root, profile or ttyd
   left under `build/` by a run.

7.10 Left, recorded so that nothing is lost:

1. The wire test and the browser test as suites of the stream, the design
   of 7.2 item 1, not planned.
2. The paths no part of the plan reaches: `db.restore` and `db.file` of a
   database the real server wrote, which no code of the server sends (7.1
   item 6); the page's display of its worker's load error, and
   `error_overlay`'s append while the parser runs a script (7.6 item 5).
3. 10.7's scripted console, not planned (7.2 item 7).
4. No Docker, by the maintainer's answer to Question P2 of task 11's
   postmortem, "remove the use of docker from your plan right now. once
   the script passes in your env it can be assumed to work in any
   container...": `test_posix.sh` passing in this environment is taken to
   pass in any container, and nothing is planned for one.

7.11 Wave 4, by the maintainer's answers of 2026-11-01
(`tmp/tasks_30_2127.md` task 5), each task an agent's, on the files it
owns. A shared file (`i18n/en-US.json`, `settings.json`,
`API/settings.json`, `python/test_all.py`, `API/ts/lines.d.ts`, this plan)
is edited while holding the run lock, renamed with the suffix `.5` for the
edit. Every run is made as `xsjs` with `--anthropic`, under the run lock.

1. 7.11.1, the gold of each suite (3.18 items 1 to 3), alone in the tree
   before the rest, since it moves every gold. Owns `test_settings.json`,
   which it removes, and the new `test_setting_*.json`; `python/harness.py`,
   `ts/harness.ts` and their stubs; the gold's readers and the roots'
   writers: `_tests_read` of `python/bootstrap.py` and its stub,
   `python/test_all.py`, `python/category.py`, `python/test_test.py`,
   `python/tap_tty.py`, every suite that writes a root's gold,
   `powershell/test_lint.ps1`, `powershell/test_powershell.ps1`, the copy of
   `xsjs_start.ps1`, `root_files` and the documents that name
   `test_settings.json`. Done when the smoke target passes, no file named
   `test_settings.json` is left, and every id reads as before but the four
   of 3.18 item 2.
2. 7.11.2, the parameters (3.18 items 4 to 7) and the hangup ignored
   (item 6 of this list). Owns `python/switches.py`, its stub and
   `python/test_switches.py`; `debug` and `verbose_level` in
   `settings.json`, `API/settings.json`, `python/settings.py`,
   `ts/settings.ts` and `API/ts/settings.d.ts`; `python/bootstrap.py`, its
   stub and `python/test_bootstrap.py`; every server module and suite that
   reads `debug` or `verbose_level`; `ts/queue.ts` and the `debug_setting`
   lines of `ts/tools_browser.ts` and `ts/worker_ai.ts`, shared line by line
   with 7.11.5; `xsjs_start.ps1`'s parameters; their golds. Done when the
   smoke and normal targets pass, no test writes a root's `settings.json`
   to set `debug` or `verbose_level`, and `test_bootstrap`'s hangup case
   passes.
3. 7.11.3, the largest database (3.19). Owns `python/substrate.py`,
   `ts/substrate.ts`, their stubs, their suites and golds. Done when both
   cases pass and the smoke target stays within its 120 s.
4. 7.11.4, the restart hold and the reaping, by the answer to Question
   T16, "[x] B. The page's restart step waits until the test has read the
   first check. unreaped processes are reaped before continuing." The
   restart root's page holds its restart rung until a push of the driver,
   which the driver sends once it has read the root's first point, so that
   the first point reads the server before it execs. Before the driver
   goes on past a point at which a server ended, it waits, within the
   point's deadline, until ttyd has reaped that server, its `/proc/PID`
   gone, and fails loud on a server still unreaped at the deadline; and it
   reaps each child of its own, ttyd and the browser, by `waitpid` once
   that child ends, before the next root starts. Owns `python/test_wire.py`,
   `ts/test_wire_rungs.ts`, `ts/test_wire.ts` if the hold needs it, and the
   golds `python.test_wire` and `typescript.test_wire_rungs`. Done when two
   normal runs of `test_wire.py` pass.
5. 7.11.5, the console's tools and lines, `PLAN_AI_CONSOLE.md` 3.6 and 3.7,
   on the files of that plan's section 4.
6. The hangup ignored, by the answer to Question T17, "[x] A. bootstrap.py
   ignores the hangup once it writes an error line, so it always exits 1
   itself; a product change with a test." `bootstrap.py`'s failure path
   sets SIGHUP to be ignored immediately before it writes its error line,
   so that ttyd's hangup after the page's close cannot end the server,
   which exits 1 by itself, and ttyd logs `exited with code 1` in either
   order by patch 02 (7.7). `test_bootstrap` gains a case: a failure whose
   error line is longer than its pipe holds keeps the server blocked in its
   write, the test sends SIGHUP, reads the line whole, and the server exits
   1, not killed by signal 1. The browser test's rung `stage 5: error
   before the first line` keeps `exited with code 1`.

7. Status, 2026-11-01, task 5 of `tmp/tasks_30_2127.md`: items 1 to 6
   built, stubs first, each by an agent on the files it owned, and run in
   the container as `xsjs` with `--anthropic`.
   1. Item 1: 99 gold files, 51 in `python/`, 46 in `ts/` and 2 in
      `powershell/`; `test_settings.json` removed, every value of it read
      back from the new files but the four ids of 3.18 item 2; the PowerShell
      not run (3.16).
   2. Item 2: `switches.parameters_load`, `parameters_write` and
      `switches_apply`, refusing by `switches.parameters_not_object`,
      `parameter_missing`, `parameter_extra` and `parameter_type`; `debug`
      and `verbose_level` refused as unexpected keys of `settings.json`;
      the TypeScript threads reading debug mode through a `debug_on` reader
      given to `settings.ValueStore`, `queue.VerboseBatch`,
      `queue.sink_attach`, `worker_ai.synchronous_read` and
      `tools_browser.tools_register`; `xsjs_start.ps1` edited, not run.
   3. Item 3: `_limit_set` of `python/substrate.py` and `limit_set` of
      `ts/substrate.ts` on each of the three opens, `blob_max` a constructor
      argument of each store, and the new suites `test_substrate_limit`,
      `normal-test`, Python 0.133 s and TypeScript 1.247 s.
      `test_engine_db.test_lines_large` fills its database to full in place
      of padding it past 10 MiB, which the limit now refuses.
   4. Item 4: the restart rung held until the driver's release, posted on a
      `BroadcastChannel` of the page's origin; `reaped_wait` after each
      ended server, ttyd's servers reaped at once and the echo server, which
      PID 1 adopts, 1.266 s and 1.871 s after ttyd's kill; two normal runs
      of `test_wire.py` passed, 9.3 s and 10.0 s. The restart root's first
      point reads "ok 1 - first; the server is pid N, ttyd's child running
      its command".
   5. Item 5: `PLAN_AI_CONSOLE.md` 6.
   6. Item 6: `test_bootstrap`'s `test_hangup_ignored`, an error line of
      1 MiB, passes, and failed with a cut line when the ignore was taken
      out.
   7. The smoke target, with all of them in, passed its 120 s in
      `test_wire.py`; `test_jslb_decode.ts`, the slowest smoke part at
      11.646 s, became `normal-test` by 5.11 item 4, and the smoke target
      then passed in 114.312 s, in 117.005 s after the console's erase by
      the buffer, and in 112.097 s at the end. The normal target passed in 648.071 s, and in
      648.368 s after that erase.

7.12 Task 6 of `tmp/tasks_30_2127.md`, by the maintainer's message of
2026-11-02, built by the session itself:

1. The restart's hold, 3.20: `API/ts/wire.d.ts` first, then `ts/wire.ts`,
   `ts/test_wire_port.ts`, `ts/test_wire_rungs.ts` and `python/test_wire.py`.
   Done when `test_wire_port` and two normal runs of `test_wire.py` pass,
   and each new check fails with the hold taken out.
2. The smoke deadline, 3.21: `python/test_setting_test_all.json`, the
   labels of `python/test_all.py`, and the comments that state the
   deadline. Done when the smoke and normal targets pass.
3. Status, 2026-11-02: both done, run as `xsjs` with `--anthropic`.
   `test_wire_port`'s `test_restart_held` passes, and failed with the hold
   taken out; the restart root failed with the hold taken out, the
   restarted server naming a `verbose.put` push, the race of Question
   T13, and two normal runs of `test_wire.py` passed, 10.9 s and 10.4 s,
   the restart root naming the page's refusal. The smoke target passed in
   126.537 s of its 180 s with `test_jslb_decode.ts` and both
   `test_substrate_limit` suites back in it.

7.13 Task 7 of `tmp/tasks_30_2127.md`, by the maintainer's message of
2026-11-02, each by an agent, stubs first:

1. The limits, 3.22 and 3.23: `python/verbose.py`, `python/substrate.py`,
   `ts/substrate.ts`, their stubs and suites. Done when the new cases pass
   and each fails with its limit or refusal taken out.
2. The console's lines, `PLAN_AI_CONSOLE.md` 3.8: `ts/console_view.ts`,
   `ts/worker_ai.ts`, `ts/tools_browser.ts`, their stubs and blocks. Done
   when the new cases pass and each fails against the code before it.
3. No gold in a root, 3.24, alone after items 1 and 2, since it moves how
   every TypeScript block reads its gold. Done when the smoke and normal
   targets pass and no root holds a `test_setting_*.json`.
4. Status, 2026-11-02: items 1 to 3 done, run as `xsjs` with
   `--anthropic`, each new case failing with its change taken out.
   1. Item 1: `verbose.log_open(root, ring, blob_max)` sets the limit,
      `test_verbose.test_log_full` filling a log to full; each store's
      authorizer denies `max_page_count` with a value, the plain form,
      a schema's and the call form, by `test_limit_refused` of both
      `test_substrate_limit` suites. The largest verbose log of the wire
      and browser normal runs was 28672 bytes, its WAL 251352.
   2. Item 2: `PLAN_AI_CONSOLE.md` 6.
   3. Item 3: `page_build.page_copy` and the line
      `var test_gold = ...;` of every page and of `build/ts/node.js`;
      `bootstrap.py` reads no gold, `tap.start` carries none, and
      `root_files` is `settings.json` and `provider.json`; each wire root
      serves its own copy of the page, and a plain copy in its place
      failed the wire test. No root held a `test_setting_*.json` in any
      run, by a watcher polling every 0.2 s.
   4. The smoke target passed in 125.899 s, 122.246 s and, at the end,
      119.958 s of its 180 s; the normal target passed in 642.244 s.

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
7. Group C, planned on 2026-10-30: wave 1 of the log's task 35 wrote 3.15
   and section 7, and C's waves 2 and 3 are 7.8 and 7.9.

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
7. For group C: `python/test_all.py`, tasks 7.8.1 to 7.8.4, 7.8.7, 7.8.8,
   7.9.1 and 7.9.2; `test_settings.json`, every task of 7.8 and 7.9;
   `ts/test_headless.ts`, tasks 7.8.2, 7.8.3, 7.8.4, 7.8.8 and 7.9.1;
   `ts/test_all.ts`, task 7.8.6; `ts/tsconfig.test.json` and
   `i18n/en-US.json`, tasks 7.8.8 and 7.9.1; and this plan, for a status
   item or a measured value by any task.

8.6 Every run of `python/test_all.py` holds the run lock, since runs share
`build/ts/node.js`, `build/headless.html`, the HTTP server's ports and the
browser: the empty file `tmp/run_lock` renamed with the task number
appended for the run, then renamed back. A missing `tmp/run_lock` is
another task's run, waited for, never recreated. A compile check into
`build/ts_check/<task>/` needs no lock. Since 2026-10-30 a run of
`python/test_wire.py` or `python/test_browser.py` holds it too, since each
builds its page into `build/` with tsc and starts the browser and ttyd.

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

Questions T7 to T13 were asked on 2026-10-30 by the session of
`tmp/tasks_30_2127.md`, after its review and runs of commit 2cab3f3 in
Anthropic's cloud container. Option A is taken when none is marked.

Question T7: what is the largest blob the page takes? chrome-headless-shell
holds at most 2145386496 bytes in one ArrayBuffer, and `blob_max` is
2147483391, so the wire test's normal rung `fit` and the browser test's
normal rung `blob_max plus one refused` cannot pass (7.8.5 item 1, 7.8.6
item 2).

[ ] A. `blob_max` becomes 2145386496 in `settings.json`, the gold's values
made from it following, every reader of the setting checked first.
(Recommended: the limit becomes one the browser meets, and `fit` keeps its
meaning, the largest blob echoed.)

[ ] B. `blob_max` stays, and `fit` echoes a blob of the browser's measured
largest, a value of its gold; the page then takes blobs it cannot hold.

[ ] C. `blob_max` stays, and the page holds a blob over the browser's
largest in parts, a product change of `jslb` and the stores, planned before
any code.

Answered by the maintainer on 2026-11-01 in place of the options: the
maximum size of everything in the system is the maximum size of a single
SQLite binary database that Chrome will store, about 10 MiB by the
maintainer's estimate, a rule of the project's rules; a single database of
that size is transmissible in one message, tested with room for the
message's overhead; and no test allocates a buffer of 1 GiB. Done:
`blob_max` and `media_db_bytes` are 10485760 in `settings.json` and
`API/settings.json`, so that one message is at most `line_max` plus
`blob_max`, 11 MiB, `line_max` the room for its JSON; `fit` echoes 10 MiB
and `blob_max plus one refused` posts 10485761 bytes; the rung `large` and
the gold's `large_bytes`, 128 MiB, are removed (7.7, 7.8.6 item 2); the
vectors at `blob_max`'s edge are made from it as before. From 2026-10-21 to
2026-11-01 `blob_max` was 2147483391, SQLite's default
`SQLITE_MAX_ALLOCATION_SIZE`, the largest image `sqlite3_serialize` makes,
chosen by a planning session of 2026-10-21 as the smallest documented limit
on the path; before it `blob_max` was 10485760. What Chrome itself stores is
Question T14.

Question T8: may the tests run as root, as a Docker container does by
default? As root dash's prompt is `# `, so `test_bootstrap_dash` waits for
`$ ` until its module's alarm; root ignores `RLIMIT_NPROC`, so
`test_bootstrap`'s `test_console_failed` starts a real shell; and Chrome's
sandbox refuses root (3.12, 7.10 item 4).

[ ] A. No: `test_all.py` refuses to start as root, naming the cause, and
the Docker image runs it as a user. (Recommended: the runs then measure what
the maintainer's machine has, by one check at the start.)

[ ] B. Yes: the console's bwrap argv gains `--uid` and `--gid` of a user
that is not root, with the gold's copy, and Chrome takes `--no-sandbox` as
root.

[ ] C. Yes: the gold keeps both prompts, chosen by the effective uid,
`test_console_failed` refuses the process another way, and Chrome takes
`--no-sandbox` as root.

Answered A by the maintainer on 2026-11-01, with "no need for root logins
at this time": `test_all.py` refuses to start as root, raising a
`PermissionError` that names the three causes, before the pins are fetched;
and the console role refuses a root that is not under `/home/`, which the
sandbox hides from dash (`bootstrap_run`, `test_bootstrap`'s
`test_console_outside`), by the maintainer's answer to the review's item of
bootstrap's header (`tmp/tasks_30_2127.md` item 7.2).

Question T9: what does `test_devtools_chrome`'s `test_cache_profile`
measure? It fails wherever the system's font cache, `/var/cache/fontconfig`,
is current, as a Docker image's usually is, since fontconfig then writes no
cache at all; in the container it passed only once that cache was moved
aside.

[ ] A. That the browser runs with `XDG_CACHE_HOME` at its profile, read
from `/proc/PID/environ` of the browser's process, whatever fontconfig
writes. (Recommended: it measures what `LinuxPipe` does, on every machine.)

[ ] B. As now, the Docker image's setup leaving no current system font
cache.

[ ] C. `LinuxPipe` also gives fontconfig a configuration of its own with no
system cache directory, so the cache is always made in the profile, at the
cost of a font scan at each browser start.

Answered A by the maintainer on 2026-11-01. Done: `test_cache_profile` takes
the browser's pid from DevTools' `SystemInfo.getProcessInfo`, its profile
from `--user-data-dir=` of its `/proc/PID/cmdline`, and checks that
`XDG_CACHE_HOME` of its `/proc/PID/environ` is that profile, under `build/`;
3 of 3 runs passed with the container's system font cache current again.

Question T10: how does the wire test read the exit code of the server ttyd
runs? ttyd 1.7.7 logs `process exited with code N` only when the process
ends before its socket closes; when the pty's end closes the socket first,
it logs `process killed with signal 0` with no code, read in its
`protocol.c`. So `exit_check` of the stock and restart roots fails by a
race of ttyd, measured once in three smoke runs in the container (7.7).

[ ] A. A second project patch of ttyd under `third_party/ttyd/patches/`
logs the exit code in both orders, and `exit_check` reads it. (Recommended:
the code stays ttyd's measurement, and the check stays exact.)

[ ] B. `exit_check` takes `killed with signal 0` as a normal exit whose
code ttyd did not log, and takes the failure from the server's own log,
which the rung reads already.

[ ] C. The roots' checks of the exit go, recorded with the path they
reached.

Answered A by the maintainer on 2026-11-01. Done (7.7):
`third_party/ttyd/patches/02_exit_code.patch`.

Question T11: how does a session in Anthropic's cloud container get ttyd's
pinned archive? Its network refuses github.com and codeload.github.com with
403. The session of 2026-10-30 made the archive by `git archive` of ttyd's
tag 1.7.7 through the container's git proxy, piped to `gzip -n`, and its
SHA-256 equals the pin's (3.14).

[ ] A. The maintainer adds github.com and codeload.github.com to the
environment's allowed domains, and `pins_fetch` runs unchanged.
(Recommended: no code changes, and the archive comes from the pin's URL.)

[ ] B. `third_party_fetch.py` gains `--anthropic`, which makes the archive
by `git clone` and `git archive | gzip -n` and checks it against the pin,
Python starting git and gzip by the maintainer's approval.

[ ] C. Each session makes it by hand, as that one did.

Answered by the maintainer on 2026-11-01 in place of the options: "you have
full network access. use the Linux package manager to get the source for
the ttyd normally on the cloud host." github.com and codeload.github.com
still answered 403 through the container's proxy on 2026-11-01, and
noble's own source package is ttyd 1.7.4. Done (3.12): a `deb-src` entry of
Ubuntu resolute's universe, then `apt-get source --download-only
ttyd=1.7.7-4build1`, which gave `ttyd_1.7.7.orig.tar.xz`, checked by apt
against its signed index, SHA-256
48eba3f76af237f4c09cceb5ddbe0f845832557819f7e5c60c88285f8822af88, its tree
equal to the pin's archive's by `diff -r`; under `--anthropic`
`third_party_fetch` checks it in place of ttyd's pin, failing loud with the
command when it is absent, and `ttyd_build` builds from it, both patches
applying. Python runs no package manager.

Question T12: does the AI worker build the console's port? No product code
builds a `wire.ConsolePort` or calls `worker_ai.console_register`, though
the stub of `ConsolePort.close_receive` says that the AI worker pushes
`console.exit`; the blocks of C build the path themselves (7.8.2 item 4).

[ ] A. Yes, a product task planned before any code: the worker's bring up
builds the port at the page's address, registers the relays and pushes
`console.exit` at the port's close, and the blocks of C keep their own
topologies. (Recommended: the stub then states what the product does.)

[ ] B. Not yet: the stub says the worker will, and the blocks' comments say
that no product code does yet, as they do since 2026-10-30.

Answered A by the maintainer on 2026-11-01, with requirements of the AI's
console: a pre-built MCP API in TypeScript for the AI's use of dash, ttyd's
protocol over the wire so that xterm.js is integrated without seams, and
one console that the AI writes to and reads from while the person at the
page watches a running command and types when none runs. Planned in
`PLAN_AI_CONSOLE.md` before any code, with its Questions C1 and C2, then
built on 2026-11-01 but for what C1 and C2 decide (`PLAN_AI_CONSOLE.md` 6):
`worker_ai.console_attach` adds the ttyd page's `wire.ConsolePort` and
pushes `console.exit`, and `console_run`'s `console.busy` and
`console.idle` hold the view's keys while its command runs.

Question T13: is a push in flight across `system.restart`'s exec the
design? `test_wire.py`'s restart root passes when the restarted server's
log names a `verbose.put` push of the page's log, not the page's
`wire.start_twice` refusal, as its header says, "by a race of the design";
the restarted server then exits 1 on a push meant for the one before it.
No item of this plan recorded the check (7.7).

[ ] A. Yes: the check stays, recorded in 7.7 as class B. (Recommended: it
is the behavior the wire test already measures.)

[ ] B. No: the page holds its pushes from the restart's request until the
new `tap.start`, a product change of the worker planned before any code,
and the check takes the refusal alone.

Not answered on 2026-11-01, so A is taken, the default of a question with
none marked: the check stays, class B (11.2 item 30).

Answered again on 2026-11-02 by the maintainer, "fix the T13 race. just
pick a solution.": option B, built by 3.20 and 7.12 item 1.

Questions T14 to T17 were asked on 2026-11-01 by the session of
`tmp/tasks_30_2127.md`, task 3. Option A is taken when none is marked.

Question T14: is the largest database a limit the system enforces, and is
it 10 MiB? Read in Chromium's source and measured on 2026-11-01: Chrome
caps no OPFS file but by the origin's quota, 60% of the disk's total in a
normal profile, and about 5% to 7% of the machine's RAM in
chrome-headless-shell's default profile, which is incognito; one
ArrayBuffer holds at most 2145386496 bytes, PartitionAlloc's largest
allocation; the pinned sqlite3.wasm's memory is at most 2 GiB, and its
largest blob 1000000000 bytes; and 10485760 bytes is exactly Chrome's
localStorage quota of an origin. So 10 MiB is the project's choice, not a
limit of Chrome's, and nothing stops a database from growing past
`blob_max`, past which it no longer moves as one message.

[ ] A. 10 MiB, enforced: each store sets SQLite's `max_page_count` on every
database it opens so that no file grows past `blob_max`, and a write past
it fails loud with SQLite's "database or disk is full"; a product change of
`ts/substrate.ts` and `python/substrate.py`, planned before any code, and a
refusal the maintainer requires, as the rules of the databases ask.
(Recommended: the rule then holds by construction, and no database too big
to move can be made.)

[ ] B. 10 MiB, not enforced: `blob_max` bounds only what moves.

[ ] C. Another value, named by the maintainer; the rule's sentence in the
project rules follows it.

Question T15: what do `--debug` and `--verbose` change? Since 2026-11-01
they are carried to every process and realm and readable there (3.17), and
read by nothing; the settings `debug` and `verbose_level` of
`settings.json` are what turn on debug mode and the shell's verbose level.

[ ] A. Nothing yet: they stay carried and readable until a task names what
reads them. (Recommended: no behavior is invented, and the settings keep
their meaning.)

[ ] B. They override the settings for the run: `--debug` makes `debug`
true and `--verbose` makes `verbose_level` 2 in every settings object a
process loads, and the tests whose roots set `debug` false or a level of
their own keep the file's value by an exception named in each.

[ ] C. They replace the settings `debug` and `verbose_level`, which leave
`settings.json`.

Question T16: how does the restart root's first point find the server's
command once the server has ended? The page runs on past its first point,
so by the time the point is read the server may have execed for the
restart and then exited 1, as the restarted server does by design; a child
ttyd has not yet reaped has an empty `/proc/PID/cmdline`, and `server_find`
then fails with "runs []". Measured on 2026-11-01 in 1 of 2 normal runs of
`test_wire.py`, the other finding it execed in place; the smoke runs passed.

[ ] A. `server_find` takes a child in state Z, a program that has ended
and that ttyd has not yet reaped, as the program ttyd started, its command
read from ttyd's log line of the start in place of its `cmdline`.
(Recommended: the point keeps its checks of the pid and the parent, and the
restart's own point reads the exec from the server's log.)

[ ] B. The page's restart rung waits for the driver to have read the first
point, a change of `ts/test_wire_rungs.ts` and of the wire test's protocol.

[ ] C. The first point reads the server before the page runs on, by a hold
of the page's next rung until a second push of the driver, as B, for every
root.

Question T17: may the server be killed by ttyd's hangup after it has
written its error line? In the browser test's normal rung `stage 5: error
before the first line`, the server writes its error line and exits 1, while
the page, faulted by that line, closes tty 1; ttyd then sends SIGHUP, its
close signal, and kills the server before its own exit, logging `process
killed with signal 1`, where the rung wants `exited with code 1`. Measured
once on 2026-11-01, the first normal run to reach the rung since the 2 GiB
rungs failed before it.

[ ] A. bootstrap ignores SIGHUP from the moment it writes an error line, so
that the server always ends by its own exit 1 and ttyd logs `exited with
code 1` in either order, by the patch of Question T10; a product change of
`python/bootstrap.py`'s failure path, with a case in `test_bootstrap`.
(Recommended: the exit code stays the server's measurement.)

[ ] B. The rung takes `killed with signal 1` after the page's close as the
end of a server whose failure its log records, and reads that log.

[ ] C. The page keeps tty 1 open after an error before the first line
until ttyd's close, a product change of `wire.WirePort`.

Questions T14 to T17 were answered by the maintainer on 2026-11-01
(`tmp/tasks_30_2127.md` task 5): T14 A, "This is a refusal you would be
requiring. this needs tests" (3.19); T15 by an option D of their own (3.18);
T16 B, "unreaped processes are reaped before continuing" (7.11 item 4); and
T17 A, "a product change with a test" (7.11 item 6).

Questions T18 and T19 were asked on 2026-11-01 by the session of
`tmp/tasks_30_2127.md`, task 5. Option A is taken when none is marked.

Question T18: may a test still write a root's `settings.json` for settings
other than the parameters? Since the answer to Question T15, a root's
`debug` and verbose level are its `parameters.json`. Other tests give a
root other settings by writing its `settings.json`: `test_echo_loop`,
`test_integrate_echo_loop`, `test_integrate_main_loop` and `test_tap_loop`
make `overflow_bytes` and `chunk_bytes` small, so that a blob streams to a
cache file within a short test; `test_browser` sets `provider.scripted`;
and `test_engine_system`, `test_integrate_settings` and `test_settings`
write wrong settings to see them refused.

[ ] A. Yes: those are the settings under test, not parameters of the run,
and stay in the root's `settings.json`. (Recommended: each test still shows
the settings it tests, and `parameters.json` holds the run's command line
alone.)

[ ] B. No: a root's `settings.json` is always the checkout's copy, and a
test that needs other values puts them in its suite's `test_setting` file,
which the server reads in debug mode over `settings.json`, a product change
planned before any code.

Question T19: does the 10 MiB limit hold the verbose log too? The log
`_verbose.sqlite` of a root, which `python/verbose.py` writes every line to
the moment it is logged, is an SQLite database outside the two stores, and
a long run grows it past 10 MiB. It is read, never moved as one database.

[ ] A. No: the limit holds the stores' databases, the ones that move as one
blob, and the log grows as the run logs. (Recommended: a log at its limit
would end a long run with an error, and no message carries the log.)

[ ] B. Yes: `verbose.py` sets `max_page_count` as the stores do, and a
line past 10 MiB fails loud.

Question T20, asked on 2026-11-01 by the session of `tmp/tasks_30_2127.md`,
task 5: may a root in debug mode hold no gold? Since 3.18 item 3,
`bootstrap.py` reads every `test_setting_*.json` its root holds, so a root
holding none carries `{"typescript": {}}`, and a page's read of an id then
fails at that read, naming the suite's file. Before, a root without
`test_settings.json` failed at the server's start with `FileNotFoundError`;
`test_bootstrap`'s `test_tests_none` now checks the empty gold in place of
`test_tests_missing`.

[ ] A. Yes, as built: a root's gold is the files it holds, and an id that
none holds fails loud where it is read. (Recommended: the failure is still
loud, at the read that needs the value, and a root whose test reads no
gold needs no file.)

[ ] B. No: `bootstrap.py` in debug mode refuses a root holding no
`test_setting_*.json`, and every test writes one into each debug root.

Question T21, asked on 2026-11-01 by the session of `tmp/tasks_30_2127.md`,
task 5: may the AI lift the database limit? The limit is a pragma of a
connection (3.19 item 2), so the AI's `sql.run` can set
`PRAGMA max_page_count` higher and grow that database past `blob_max`
until the store opens it again. Opened again, a file already past the
limit keeps its larger page count: it reads, and it cannot grow. Nothing
refuses either, and a database past `blob_max` then fails when it moves as
one blob, at the wire's bound.

[ ] A. Yes, as built: nothing refuses the AI access that the maintainer
did not require (the Databases rule), and the wire's bound fails loud on
a database past `blob_max`. (Recommended: the required refusal is the write
past the limit, which holds for every statement but one that sets the
limit.)

[ ] B. No: the stores refuse a statement that sets `max_page_count`, a
refusal the maintainer would be requiring.

[ ] C. As B, and a store refuses to open a database already past
`blob_max`.

Questions T18 to T21 were answered on 2026-11-02 by the maintainer's
message, "you are asking me about default choices that i made by not explicitly
selecting them. if you keep asking then they are not choices, they are
simply remaining unresolved. please accept my default choices in the
past and consider them actionable." Each takes its option A, the default: T18 A,
tests still write a root's `settings.json` for the settings under test;
T19 A, the verbose log is not held by the limit; T20 A, a debug root may
hold no gold; T21 A, nothing refuses the AI's `PRAGMA max_page_count`.
Each A is the code as built.

Corrected on 2026-11-02, the same day, by the maintainer's marks: T19 B
(3.22), T21 B (3.23), and T20 answered by removing the roots' gold
(3.24); T18 A stands.

Question T22, asked on 2026-11-02 by the session of `tmp/tasks_30_2127.md`,
task 6: does the project rules' smoke budget say 3 minutes? The rules'
Testing section says the smoke suites are those that "fit in 2 minutes";
the deadline is now 180 s by the maintainer's message (3.21). The rules
are the maintainer's text, which no session edits unasked.

[ ] A. Yes: the session changes "fit in 2 minutes" to "fit in 3 minutes"
in the rules' Testing section. (Recommended: the rule and the deadline
then agree.)

[ ] B. No: the rule keeps 2 minutes as the aim, and 180 s is the
deadline's slack.

Answered A on 2026-11-03 by the maintainer's message "update declawed,
make the commit, push it": the rules' Testing section says "fit in 3
minutes".

Question T23, asked on 2026-11-03 in the conversation of
`tmp/tasks_30_2127.md`, after task 8: do the decisions of 11.2 items 45
to 47 stand? Answered "[A] A. Confirm all three." on 2026-11-03.

Question T24, asked the same day: how are the PowerShell changes of
tasks 5 to 7 tested, with no `pwsh` in the container? Answered
"Ignore." on 2026-11-03: they stay unrun.

## 10 Outside this plan

10.1 Group C was outside this plan until 2026-10-30, when section 7 planned
it.

10.2 `test_integrate_http` runs in Node (3.1), so the browser's own fetch,
its CORS checks and its failure texts, is tested only where a B block
fetches, in `test_integrate_media`.

10.3 `ts/tsconfig.node.json` sets no `lib` narrower than the default, so a
use of the DOM in an A block compiles and fails when it runs.

10.4 The ttyd page's two lists in `test_all.ts` repeat the blocks of
`test_all.py` until C is planned. Planned on 2026-10-30: the lists hold no
block (7.2 item 3).

10.5 The helpers each suite copies, such as `gold_value` and `thrown_get`,
stay copied.

10.6 `PY_GOALPOSTS.md` 9.2, the order of `test_wire.py` before the TS
producer's suite, is met for A and B by the TS pair test; `test_wire.py`
itself stays in C. Since 2026-10-30 it runs after the stream, on the Linux
browser, and C's TypeScript blocks, in the stream, are met by the pair test
too (7.2 items 1 and 6).

10.7 A scripted far end on the console lane is not planned, since what
needs the console on tty 0 stays in C (3.9). Its design, so that it is not
lost: the `console` owner's port is one of a linked pair of
`queue.LocalPort`s; `console.input` and `console.read`, which the AI side
does not handle, are answered by a second real queue of thread `console`
whose handlers answer from the gold, as 6.9 item 3.1 does; and
`console.open`, which the AI side relays from the UI under the same type,
is answered by the test's own receiver, as 6.9 item 3.2 does. It would move
`test_worker_ai`'s `test_console_opened` and the four console tests of
`test_tools_browser`'s `TestConsole` to B. Kept unplanned on 2026-10-30
(7.2 item 7): those tests run on the real console through ttyd instead
(7.5 items 3 and 6).

10.8 The wire rungs, `ts/test_wire_rungs.ts`, stay in C with `test_wire.py`
(7.1 item 2): a scripted server would test their own code against the gold,
not the real server through ttyd, which is their purpose. They alone send
`tap.run`, `source.put`, `echo` and `system.restart`. Kept on 2026-10-30:
they run in `test_wire.py`, after the stream (7.7).

## 11 Requirements analysis

The requests are those of this conversation, `tmp/tasks_28_1951.md` item 1,
and the ones of earlier logs that bear on TypeScript: `tmp/tasks_25_1832.md`
item 10.1 and `PY_GOALPOSTS.md` 9.2; and the maintainer's answers of
2026-10-30, with the acceptance of every decision reported to the
maintainer then (`tmp/tasks_29_1354.md` items 21 and 22); and the
maintainer's request and answer of 2026-10-30 (item 29), with the decisions
reported to the maintainer before it (item 28.4) and taken by the
coordinator after it (item 30); and the maintainer's answer of 2026-10-30
that the tests may build and start ttyd and dash (item 35), with the
coordinator's decisions after it (item 36), and the answer on how dash
runs (item 39), with the coordinator's decisions after it (item 40); and the
maintainer's request that the console's binary connection carry a binary
heredoc (item 44), with the coordinator's decisions after it (item 45);
and the maintainer's answers and requests of 2026-11-01
(`tmp/tasks_30_2127.md` task 3), with the session's decisions after them;
and the maintainer's answers and confirmations of 2026-11-01
(`tmp/tasks_30_2127.md` task 5), with the session's decisions after them. A:
unsatisfied
or modified without cause. B: unsatisfied or modified with cause but
without confirmation. C: confirmed withdrawn or modified. D: satisfied
without modification or withdrawal.

11.1 Class A: none.

11.2 Class B, each satisfied in this plan with the stated cause, and
wanting confirmation. Every item here was confirmed on 2026-11-02
(11.3 item 26); the text stays for the record:

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
    `failed_tests` field of `tap.pair` (5.5 item 6), whose deferral is
    withdrawn (11.3 item 13).
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
18. The coordinator's decisions of 2026-10-30 after the maintainer's answer
    of item 35: the Windows path read as the Windows test path, offline and
    kept, the user facing scripts and the project rules' targets as they
    were (36.2, 3.16); ttyd built in the driver's bring up by
    `python/ttyd_build.py`, by the install script's steps, `patch` and
    `cmake` counted as building ttyd (36.3, 3.15); and every ttyd suite on
    `chrome-headless-shell` through `devtools.LinuxPipe` (36.4, 7.6, 7.7).
19. The reading of "automated testing should be ubuntu only, not wsl" (item
    35): no test starts a Windows program, and the official run is
    `test_posix.sh`'s on Ubuntu, which here runs inside WSL2 (3.16).
20. The coordinator's decisions after the maintainer's answer of item 39:
    the console's shell a constant argv at the top of `python/bootstrap.py`,
    in use and in the tests alike, not a setting, since nothing asks for the
    command to vary (40.1); and what it changes, written before any code
    (40.2, 7.4 item 1), with 40.3.1's measurement correcting one of its
    expectations, the pty's hangup still ending the shell through the outer
    bwrap (7.4 item 5.5).
21. Group C's decisions of 7.2: its TypeScript blocks in the one stream,
    the wire test and the browser test after it; each block of C on the
    headless page served by ttyd, a worker block taking the page's address
    from its own `location`; the ttyd page's lists holding no block by 3.1,
    its run "unit" kept as the bring up of both threads with documents of no
    block; the smoke deadline met by measured labels; the browser test's PNGs
    kept on the Linux browser and none added; C's order; one root and one
    ttyd per block; and 10.7 left unplanned.
22. The rules for every part that starts dash (7.4 item 2), and the console
    role's `os.chdir(root)` going with the old shell (7.4 item 1).
23. The rules and fates of the browser test's rungs (7.6): the probe kit's
    doubles out; the kill rung going for B's `test_substrate_crash`; the two
    worker fault rungs and the append rung removed by 4.5 with their
    patches of `Blob` and `Worker`; the probe's HTTP, queue, overlay and
    media rungs that A's and B's blocks reach going by 3.1, and those whose
    far end only the browser test's stub gives staying in C by 4.4; the
    drain poll's private reads going by 4.7; and the methods of
    `devtools.Browser` that the browser test calls tested first on the Linux
    browser, in `test_devtools_chrome` (7.6 item 6).
24. `test_worker_ai_console`, `test_wire_end` and
    `test_tools_browser_console` rewritten as blocks of C without doubles;
    the new block `test_integrate_wire`, `wire`'s integration block, with no
    queue so that `console.read`'s `error` line comes back as a line; and
    the new block `test_console_open` for the console view's open path,
    which no test reached (7.5).
25. Recorded and not planned: no code of the server sends `db.restore`, so
    nothing of C reaches a restore of a database the real server wrote (7.1
    item 6); the paths of 7.10 item 2.
26. "continue bringing up suites enabled by your authroization as far as
    possible unless blocked by an auth request" (item 35) and "continue"
    (item 39): every suite and block the authorization enables is planned in
    7.8 and 7.9, none waiting on an authorization; satisfied once they pass.
27. "the dash connection is binary so it should be possible to send a binary
    HEREDOC and read it back. make sure that is tested in a way that would
    catch a non-binary connection" (item 44): planned in 7.4 item 7, with the
    coordinator's decisions of item 45, unconfirmed: two cases, one over the
    console role's pty in `test_bootstrap_dash` and one over the whole
    connection in `test_integrate_wire`; the payload's rules, its bytes that
    dash cannot hold left out with their measured cause; markers that
    `printf` escapes make; a deliberate break at each level that must fail
    it at once; and `console.read` kept text, a case expecting its
    `wire.output_invalid` on the same output. The case of C sits in
    `test_integrate_wire` with no queue, where item 45 named the block that
    owns the console port's path. Correction of 2026-10-30, by task 7.8.8's
    reading of `ts/wire.ts` and the coordinator's decision: no `error` line
    answers the read, whose refusal faults the thread holding the port, so
    the read case, `binary_read`, is removed (7.4 item 7.5), the refusal
    pinned by `test_wire` in A; `binary_echoed` with its two breaks meets
    item 44. Satisfied once 7.8.1 and 7.8.8 pass.
28. `test_tools_browser_console`'s junction, its hold of the `mcp` lines
    until dash's first prompt, and its cases' order with the case `allowed`
    and `opened` beside the four of 7.5 item 6 (7.5 item 6.1 to 6.4),
    written by task 7.8.4.
29. Moved to 11.3 item 14 on 2026-11-01, modified by the maintainer.
30. Moved to 11.3 item 19 on 2026-11-01, confirmed by the maintainer.
31. Moved to 11.3 item 20 on 2026-11-01, confirmed by the maintainer, as
    are items 32 to 36.
32. Moved to 11.3 item 20.
33. Moved to 11.3 item 20.
34. Moved to 11.3 item 20.
35. Moved to 11.3 item 20.
36. Moved to 11.3 item 20.
37. The session's decisions of 2026-11-01 for Question T15's answer
    (3.18): each suite's gold beside its module, a suite's name being its
    module's, so that the directory keeps the Python and TypeScript suites
    of one name apart; the four top keys given to the suites that read
    them; the ids kept but those four; a root holding the TypeScript
    suites' gold alone, the only gold a page reads; the name
    `parameters.json` for the answer's "paramters.json"; its keys the
    three switches; a server's switches set from its root's file; the
    console's level 2 by `verbose` and 1 otherwise, level 0 chosen by no
    server; and the start script's parameters from its own arguments, debug
    mode off without `--debug`.
38. Question T14's answer applied to the two stores' connections only, the
    verbose log left out (Question T19).
39. Question T16's "unreaped processes are reaped before continuing" read
    as the driver waiting for ttyd to reap an ended server, which only ttyd
    can, and reaping its own children itself (7.11 item 4).
40. Question T17's test made by an error line longer than the pipe holds,
    which keeps the server alive in its write for the hangup (7.11 item 6).
41. Task 7.11.1's decisions beyond 3.18: a refused id names its suite's
    file, `python/test_setting_<suite>.json` or
    `ts/test_setting_<suite>.json`, and an id of no language, or of no
    TypeScript suite in the browser, names the gold; `gold_get` of a
    language alone, as `python`, gives that language's gold assembled;
    `test_bootstrap`'s refused case writes its bad text into an extra root
    file, `test_setting_refused.json`, and `test_first_short` proves the
    gold unread by a garbled gold file; the gold files left out of the
    formatter's whitelist, which names no JSON file; and a root in debug
    mode holding no gold carrying an empty one (Question T20).
42. Task 7.11.2's decisions beyond 3.18: `parameters_load` and
    `parameters_write` take the root, the file's name kept in
    `switches.py`; `switches_apply` sets a true switch's variable to 1 and
    removes a false one's; `test_jslb` before `test_switches` in the order,
    since `switches.py` imports `jslb`; debug mode given to the TypeScript
    modules as a `debug_on` reader (7.11 item 7.2), so that a block tests
    both modes on one thread; each root or realm whose test needs debug
    mode given the run's switches with `debug` true, as the checked-in
    `debug: true` was, so that `--debug` changes only the roots that take
    the run's switches as they are; the main loops' unit suites, which run
    the loop in a forked child with no `bootstrap.py`, applying the root's
    parameters in that child; the level-0 cases of `test_bootstrap` gone,
    `test_console_failed` at level 1; the new setting
    `powershell.parameters_file`, by the rule that PowerShell's constants
    are in `settings.json`; `xsjs_start.ps1` taking `--debug` and
    `--verbose` anywhere, each once, and writing the file in its state
    folder, copied into the root by `wslpath` and `cp`; the wrong-type case
    of `test_settings` moved to `queue_synchronous`; the settings overrides
    that set only debug mode replaced by parameters, `root_verbose` false in
    the golds of `test_browser` and `test_wire`; `mcp_stdio.py` checking
    `settings.json` and reading debug mode from `parameters.json`; and the
    hangup case's error line, an invalid role of 1 MiB, the gold's
    `hangup_bytes`, with the server seen sleeping in its write by
    `/proc/PID/stat` before the hangup.
43. Task 7.11.3's decisions beyond 3.19: `blob_max` a constructor argument
    of each store, as `overflow_bytes` is; the cases in the new suites
    `test_substrate_limit`, `normal-test`, since the smoke target had no
    time to spare; `test_engine_db.test_lines_large`, which padded a
    database past the old 10 MiB window, made to fill one to full and to
    check its restore lines sent whole as blob 1, the scenario of a
    database past 10 MiB no longer reachable through the store; the value
    that `PRAGMA max_page_count` answers not checked, so that a file past
    the limit opens (Question T21); and the AI's pragma left unrefused
    (Question T21).
44. Task 7.11.4's decisions beyond its text: the release of the held rung
    posted by the driver on a `BroadcastChannel` of the page's origin,
    through `script_evaluate` on the page, since `python/devtools.py` gives
    the driver no evaluate in the AI worker; `server_find` taking ttyd's
    own command alone, the exec before the first point no longer possible;
    the echo root too waiting for its server's reap, by PID 1, about 1 to
    2 s of the smoke target; no new reaping of ttyd and the browser, which
    `process_stop`, `kill_check` and devtools' `exit_wait` already reap by
    `waitpid`; and the restart root's ending that names a push of
    `verbose.put` read as the race of Question T13, not the restart step.
45. Task 6's decisions beyond 3.20 and 3.21: the held lines kept by the
    port, `posts_held`, never sent; the restart rung's post after
    `system.restart`, the gold's `restart_after`, a TAP comment; the hold
    seen by `test_restart_held` as the missing socket's refusal that a
    held line no longer meets; the three blocks back in smoke by 5.11
    item 4 once the deadline was 180 s.
46. Task 7.13 item 1's decisions beyond 3.22 and 3.23: `blob_max` the third
    argument of `verbose.log_open`; `test_log_full` filling the log through
    `verbose.log` with lines of the gold's `fill_chars`, reading its rows
    back by their first characters only; the refused statements of the
    gold's `limit_setters`; the TypeScript case checking that a refused
    statement pushes nothing; a code but OK from
    `sqlite3_set_authorizer` thrown as "internal error"; the cases in the
    smoke suites `test_verbose` and `test_substrate_limit`.
47. Task 7.13 item 3's decisions beyond 3.24: the gold a line of its own,
    `var test_gold = <JSON>;`, in each page and in `build/ts/node.js`, so
    that `page_copy` replaces one line and compiles nothing;
    `page_copy` refusing a page with no gold line or two, and gold whose
    keys are not `typescript` alone; `gold_read` refusing a gold file that
    is not an object in plain English, as `page_build`'s other errors;
    the harness's values set in debug mode only, the headless and Node
    realms refusing a `tap.start` outside it; the wire roots alone given
    their own page, since the browser test's per-root gold equalled the
    checked-in gold, the group C roots serving `build/headless.html`, and
    `tap_tty`'s roots running Python suites only; `test_browser`'s first
    rung checking the page's `test_gold` by `script_evaluate`; and
    `xsjs_start.ps1`'s copy of `root_files` back to a plain copy.
48. Task 9's decision of 3.25: the two later formatter suites run in
    every category, on the approval of the programs that
    `test_posix.py` already runs, with no new question.
49. Task 9's decision of 3.26: ttyd patched to keep each frame alive,
    keeping permessage-deflate, rather than turned to send
    uncompressed by leaving out its extensions, which would also end
    the fault.
50. Task 10's decisions of 3.27: the smoke-test run's advisory kept,
    reworded, rather than removed; the rows' linters left in both
    categories; `reformat.format_check` and the table's checkers kept
    with no caller in an official run; the normal-test run still
    formatting; the Windows target's formatting in a smoke run left as
    it is, its design written in item 6, while it is offline.
51. Task 11's decisions of 7.9.1 item 1: the test's end on the UI
    queue's lane of thread `server`, since `queue.ThreadName` is closed
    and `ai` is the linked port, rather than a new thread name in the
    API; the builders of `test_integrate_console_view` copied into the
    block's file, which is the only file the task owns, rather than
    exported from that block; and fixed waits of the gold's seconds for
    dash's prompt and output, as `test_integrate_console_view` waits for
    the terminal to draw, rather than a probe that polls the rows.
52. Task 11's decision of 7.9.1 item 2: the race of tty 0's end and the
    close's wake settled in `console_view`, its phase `ended`, rather
    than in `queue`, whose wake would take its last reply's place in
    the order in both modes as synchronous mode already does; the
    queue's change would alter the one synchronization tool for every
    caller, and the view's is cheap to undo. Overturned by 11.3 item 36.

11.3 Class C, confirmed by the answers and acceptances of 2026-10-30 and
2026-11-01:

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
11. The question of item 34.2.1, whether the tests may build and start
    ttyd and start dash: answered A on 2026-10-30, "Yes for Linux", modified
    by the maintainer in the same answer: automated testing on Ubuntu only,
    no Windows program started, and the Windows path taken offline, to come
    back later, not deleted, in place of option A's Windows Chrome path kept
    for `powershell/test_powershell.ps1` (item 35, 3.16).
12. "run "firejail --private dash" as firejail is now installed" (item 35):
    modified by the maintainer's answer of item 39, dash only by the
    bubblewrap command given, after firejail was measured to run dash with
    no sandbox on this machine (item 38.1, 7.4).
13. The designs written down and not needed, the pair test's `failed_tests`
    field of `tap.pair` (5.5 item 6) and base64 bodies in the local test
    server's script (log item 33.9.2): ignored by the maintainer (item
    35.4). Neither is built, and 11.2 item 13's deferral of `failed_tests`
    is withdrawn.

14. "so far we have --anthropic --debug and --verbose and i want them all
    passed and readable in some native form everywhere. even if as global
    bools" (2026-11-01), modifying item 29 of 11.2, the browser path only:
    the three switches, `python/switches.py` and `ts/switches.ts` (3.17).
15. Question T7, answered in place of the options on 2026-11-01: the rule of
    the system's largest size, 10 MiB, in the project rules, one database
    of it moving in one message (11.2 item 31).
16. Question T8 A, with "no need for root logins at this time", and "for Q7
    require the dash root to be under /home/", the review's item 7.2 of
    `tmp/tasks_30_2127.md`.
17. Question T9 A, Question T10 A and Question T12 A.
18. Question T11, answered in place of the options: the package manager's
    source (3.12, 11.2 item 34).

19. The session's decisions of 2026-10-30 after the review of commit
    2cab3f3, confirmed by the maintainer on 2026-11-01, "[x] A. Confirm all
    six", once 11.2 item 30: C's order (7.9.2 item 1); the worker hang rung
    removed with its measured cause (7.8.6 item 1); `test_fault_open`
    recorded as removed (7.8.3 item 1); `test_all.py` stopping ttyd and
    its root on SIGHUP and SIGTERM from the first ttyd root on, not from
    its start, since the Python suites fork children that take a handler
    with them; the ids of `test_worker_ai_console`'s UI requests 102 and
    103, apart from the queue's own; and `test_integrate_wire`'s output
    kind from its gold.
20. The session's decisions of 2026-11-01, confirmed by the maintainer on
    2026-11-01, "[x] A. Confirm all six", once 11.2 items 31 to 36:
    1. The session's decisions of 2026-11-01 for Question T7's answer: the
       largest database is 10 MiB, `blob_max` 10485760, by the maintainer's
       estimate, which is no limit of Chrome's (Question T14); `media_db_bytes`,
       read by no code, lowered from 256 MiB to the same 10 MiB; one message's
       room for its overhead is `line_max`, 1 MiB, unchanged; the rung `large`
       removed and ttyd's resident size read after `fit`; the drain rungs'
       burst made of `blob_max` over `overflow_bytes` echoes; and the rule's
       sentence placed under the project rules' Databases section.
    2. Question T8's refusal raised in `test_all.py`'s `main` after its
       arguments are parsed, so that `--help` still answers as root; and the
       root check of the console role alone, before it reads the settings,
       since only the console runs dash; the engine role keeps any root.
    3. The switches' design (3.17): environment variables set to 1, read at
       import, the options on the four command lines that a person runs and
       not on `bootstrap.py` or `mcp_stdio.py`, which their parent starts with
       the environment; dash's environment kept scrubbed; the TypeScript
       threads reading them from `tap.start` and `settings.set`; and
       `test_switches.py`'s forked children.
    4. Question T11's source: Ubuntu resolute's `1.7.7-4build1`, of the same
       upstream release as the pin, in place of noble's 1.7.4, the one the
       container's own release has, since the plan, the patches and the
       stubs are of ttyd 1.7.7; the archive placed by the container's setup,
       never by Python; and a second pin list in the gold of
       `test_third_party_fetch`, `pins_anthropic`.
    5. `test_cache_profile`'s pid from DevTools' `SystemInfo.getProcessInfo`,
       where the question named `/proc/PID/environ` only.
    6. The AI console's design and its class B items, `PLAN_AI_CONSOLE.md`
       7.2, and its Questions C1 and C2.
21. Question T14 A, "This is a refusal you would be requiring. this needs
    tests" (3.19).
22. Question T15, answered by an option D of the maintainer's own: the gold
    of each suite and `parameters.json` (3.18, 11.2 item 37).
23. Question T16 B, "unreaped processes are reaped before continuing"
    (7.11 item 4, 11.2 item 39).
24. Question T17 A (7.11 item 6, 11.2 item 40).
25. `PLAN_AI_CONSOLE.md`'s Questions C1 B and C2, answered in the
    maintainer's words, recorded in that plan's 7 and 8.
26. 11.2 items 1 to 28 and 37 to 44, and Questions T18 to T21 at their
    option A, confirmed by the maintainer's message of 2026-11-02, an
    unmarked default being the maintainer's choice:
    "you are asking me about default choices that i made by not explicitly
    selecting them. if you keep asking then they are not choices, they are
    simply remaining unresolved. please accept my default choices in the
    past and consider them actionable."
27. Question T13 B, "fix the T13 race. just pick a solution." (3.20),
    and the smoke deadline, "extend the smoke test timeout to 3 min."
    (3.21), of the same message.
28. Questions T19 B and T21 B, marked by the maintainer, and T20's
    answer, which removes the roots' gold (3.22 to 3.24), and the
    10 MiB limit as the comprehensive plan for size limits, now in the
    project rules, of the maintainer's message of 2026-11-02.
29. Question T22 A, "update declawed, make the commit, push it", the
    maintainer's message of 2026-11-03 (3.21).
30. Items 45 to 47 of 11.2, Question T23 A, "[A] A. Confirm all
    three.", the maintainer's message of 2026-11-03.
31. Item 48 of 11.2, its smoke part overturned by the maintainer's
    message of task 10, "remove the formatter runs from the "smoketest"
    series of tests": both formatter suites are `normal-test` (3.27).
32. Item 49 of 11.2, settled by the same message, "disable ttyd
    compression if there is a blocking problem using it and continue, it
    is only being used for bring up and may be replaced": compression
    stays while it causes no blocking problem (3.27 item 7).
33. Question P1 of task 11's postmortem, answered in the maintainer's
    message of task 12: PowerShell is ignored and nothing depends on it
    (3.16 item 5).
34. Question P2, answered in the same message: Docker is out of the plan
    (7.10 item 4).
35. Question P3, answered in the same message, "don't plan. i want the
    current tests all passing.": no suite of a live AI endpoint is
    planned.
36. Question P4, answered in the same message: each queue runs its inputs
    in order, a wake in its last reply's place (3.28), which overturns
    11.2 item 52.
37. The races of ttyd's ends, by the same message, "it is a known part of
    the design of ttyd so there is no reason asking the maintainer about
    it.": a rule of the project, and the tests designed to work with it.
38. dash's line on job control, by the same message, "this has to be
    fixed": the fix planned in 7.4 item 8.

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
11. "you are now authorized to build and run ttyd": 3.15, and section 7.
12. "don't delete it", of the Windows path: nothing of it is deleted
    (3.16).
13. "i just deleted the build dir and didn't see anything in git. feel free
    to delete files": git keeps nothing of `build/`, every run makes it again
    (3.15 item 2), and a task may delete a file its section names.
14. "ignore the rest of your response": nothing of postmortem 34 is carried
    into this plan but the answer to its question.
15. "try bwrap ... /bin/dash" (item 39): the command is the console's shell,
    exactly as given, its verbose form adding `-v` (7.4, task 7.8.1).

11.5 Unresolved on 2026-11-03, at the end of task 12 of
`tmp/tasks_30_2127.md`: items 50 and 51 of 11.2, the decisions of tasks
10 and 11, which stand unless the maintainer overturns one; item 52 is
overturned by 11.3 item 36. Earlier record, at the end of task 11: items
50 to 52 of 11.2, the decisions of tasks 10 and 11, which stand unless the
maintainer overturns one. Earlier
record, at the end of task 10: item 50 of 11.2, the decisions of task
10, which stand unless the maintainer overturns one. Earlier record,
after the
message of task 10: none of 11.2, items 48 and 49 of which 11.3 items 31
and 32 settled. Earlier record, at the end of task 9: items 48 and 49 of
11.2, the decisions of task 9, which stand unless the maintainer
overturns one. Earlier record,
after the answers of task 9: none of 11.2, items 45 to 47 of which
11.3 item 30 settled. Earlier record, on 2026-11-03, after task 8:
items 45 to 47 of 11.2, the decisions of tasks 6 and 7, which stand
unless the maintainer overturns one. Earlier record, on 2026-11-02,
after task 6, Question T22 of which 11.3 item 29 settled:
Question T22, which waits on the maintainer, and items 45 to 47 of 11.2,
the decisions of tasks 6 and 7, which stand unless the maintainer
overturns one. Earlier record, on
2026-11-01, after task 5, every item of which 11.3 items 26 and 27
settled: the
confirmations of 11.2, items 1 to 28 and 37 to 44; Questions T18 to
T21; and `PLAN_AI_CONSOLE.md`'s Questions C3 and C4 and its class B
items 1 to 17.
Earlier record: Each is
satisfied in this plan with its cause, or planned in 7.8 and 7.9 and
satisfied once they pass, and none needs a question of the maintainer: no
requirement of items 35, 39 or 44 is left unmet, and no two rules were found
to contradict. Item 12, the departures of 6.9 item 7 from the coordinator's
design, was confirmed by the coordinator on 2026-10-30
(`tmp/tasks_29_1354.md` item 32.5). Question T6 is answered. The question of
item 34.2.1, on ttyd and dash, is answered (items 35 and 39), and the hold
on dash of item 36.5 ended with the answer of item 39, so group C is planned
in section 7 and waits on no one; its blocks and programs run once 7.8 and
7.9 pass. The deferral of `failed_tests` is withdrawn (11.3 item 13).
