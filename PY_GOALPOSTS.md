# PY_GOALPOSTS

The execution plan for testing the Python modules of `python/` in strict
dependency order, as one TAP stream with no mock test objects:

    python3 python/test_all.py [--smoke-test | --normal-test]

It stands alone. `TEST_PLAN_PY.md`, `TEST_PLAN_PY_QUESTIONS.md` and the
other planning documents are to be deleted, so what this plan needs from
them is written into it: the maintainer's answers in section 2, the rules
of the order in 4.1, and the specs of the work in section 5. "Question N"
names the question an answer came from, and the answer is always stated
beside it. Nothing in this plan has been carried out.

Section 1 lists what will be accomplished, in order of importance; section
2 the decisions; section 3 the tree as it is; section 4 the rules every
task follows; section 5 the tasks; section 6 their order; section 7 how
agents share the tree; section 8 the questions; section 9 what is left
out; section 10 the requirements analysis.

## 1 What will be accomplished, in order of importance

- No suite uses a mock, a patch, a hand-made double or a change of a
  module's internal state. Every test goes through the API of the module
  it tests and shows normal operation. A test that needs an environment
  `python3` alone cannot give moves to a later suite (2.3, 2.4). Tasks 5.5
  and 5.7 to 5.12.
- One run, one TAP stream, three phases in strict dependency order: every
  unit suite by layer, then the integration suites from the bottom layer
  up, the pair test first, then the stdio suites. No line marks a phase
  (2.1). Task 5.13.
- The driver checks each TAP line with the consumer as it is written, and
  stops at the first line that does not fit or after the first failing
  block. Task 5.3.
- The pair test proves that the consumer validates what the producer
  writes. Its counts are checked against `unittest`'s own result, failed
  fixtures included (2.2, 2.16). Task 5.4.
- The loop between `test_jslb` and `vectors_make` is gone (3.4). Task 5.5.
- Every module that calls into a project module other than
  `internationalization` has an integration suite,
  `test_integrate_<module>.py`, run on its real callees, bottom up (2.5).
  Tasks 5.5 and 5.8 to 5.12 write them, task 5.13 orders them.
- Line coverage of each module by its own unit suite is measured with
  `sys.monitoring`, lines marked `# pragma: no cover` exempt, and a run can
  be made to fail at the first line never run. It is not yet required
  (2.12). Task 5.6.
- The whole stream passes, smoke-test and normal-test, in process and over
  the tty, inside the 120 s of the gold `smoke_seconds`. Task 5.14.
- The settled small items: the three digests pinned (2.14) and prettier run
  once on `test_settings.json` (2.15). Tasks 5.1 and 5.2.
- `tap_loop.py` stops importing the driver (2.19). Task 5.8.
- The restart loop is gone: `bootstrap.py` and `mcp_stdio.py` each re-exec
  themselves, and `engine_system` no longer execs (2.9). Task 5.15.

## 2 The decisions the plan rests on

2.1 One run (Questions 1 A, 16 A). One run of `python3
python/test_all.py`, one TAP stream of one block per suite module, in three
phases: every unit suite, then the integration suites from the bottom layer
up, then the stdio suites. The run stops at the first failure. The driver's
list shows the phases by order alone, and no line of the stream marks one,
so the producer, the consumer and the wire test stay as they are.

2.2 The pair first (Question 2 A). The unit suites of `tap_producer` and
`tap_consumer` run first, and the first integration suite is the pair test,
a new module `test_tap_pair.py`, since no module tests the pair today.

2.3 No mock test objects (Questions 3, 4 and 18, and the project rules).
Using mock test objects is banned, and a double of any kind is forbidden.
Modules are tested in dependency order so that each module has tested
dependencies it can use while being tested. If a module can't be fully
tested without mocking environments that are not available, its suites are
split, and the later suites run as it becomes possible to run them on real
code.

2.4 No change of internal state (Question 28, answered 2026-10-28).
Directly changing a module's internal state during testing to emulate a
test environment is forbidden. All tests go through the APIs being tested
and show normal operation. They do not use isolated operation of an
internal component in a way that violates separation of concerns. A
module's own constant set to a test value, such as a wait of 0 s or a path
into a scratch directory, and its own state reset between tests, such as an
engine's root or the dispatch table, are both forbidden (4.7).

2.5 Unit and integration suites (Questions 5 A and 19, and Question 29,
answered 2026-10-28). Tests are broken into suites, first unit, then
integration, proceeding in module order, testing only what is real, and
making accommodations as required, such as delaying or splitting off
tests. Each module that calls into project modules gets one suite
`test_integrate_<module>.py`, which tests it with all its real callees,
each of them integrated earlier, bottom up, one module added at a time so
that a failure names the module just added. `internationalization` does
not count as a module when labelling another module's test a unit test;
otherwise there would be no unit tests. So `jslb`, `stall_loop`,
`substrate` and `verbose`, whose only project callee is
`internationalization`, have no integration suite.

2.6 The stdio route (Question 6 A). The stdio tests reach `bootstrap.py`
through a pty of the standard library's `pty` module: the test runs
`python3 python/bootstrap.py --root ROOT` on the tty as ttyd does, plays
the page on the other side with JSLB lines, and hangs up by closing its
side, as ttyd's close does. No ttyd and no browser.

2.7 The stdio phase (Question 17 A). Every suite that starts
`bootstrap.py` or `mcp_stdio.py` as a program and talks to it over its
stdio: `test_tap_tty`, and the tests of `test_mcp_stdio` that start a
child, which move to a suite of their own. `test_bootstrap`, which runs
`bootstrap_run` in process, stays in the earlier phases.

2.8 What the stdio tests cover (Question 7), all done in `test_tap_tty`:

1. the start: `tap.start` with id 101, its settings, in debug mode its test
   settings, and the Empty reply;
2. every line type the stock main loop registers, once each, the reply and
   the databases checked;
3. the page's `error` line: exit 1 with nothing written back, the cascade
   logged and `Bail out!` ending `tap/typescript.tap`;
4. a handler's `Failure`: its reply, then the server's `error` line, then
   exit 1;
5. the hangup that ends a run, with the stock loop and `stall_loop.py`,
   which need not get the very last byte, only handle the hangup
   gracefully;
6. the debug lines `settings.put`, `source.put` and `system.restart`, the
   restart going on over the same tty;
7. `mcp_stdio.py` on the same root while the engine runs.

Left out by the maintainer: a blob over `overflow_bytes` both ways, a
second engine on the same root refused by `engine.lock`, and the console
role.

2.9 The restart (Question 9 E, and Question 27, answered 2026-10-28). A
restart actually requires the process to restart the interpreter. A hangup
is acceptable, and reconnection does not have to be tested yet.
`bootstrap.py` re-execs itself: its only job is to be a shim that allows
rewriting what it boots next in a recovery scenario. The maintainer's
answer to the first restart question removed the choice that
`mcp_stdio.py` not register the restart tool (`tmp/tasks_25_2014.md` item
28), so `mcp_stdio.py` keeps the tool and, by the same rule, re-execs
itself (10.2 item 6).

2.10 Programs (Question 8 A). `python3` alone is approved, for
`bootstrap.py` and `mcp_stdio.py`. `dash`, ttyd, `tsc`, and the formatters
and linters of `reformat_table.json` are not approved. `powershell.exe`
and Chrome were never asked.

2.11 Callbacks (Question 10 A). A module that calls a function it was
handed does not call into the module that handed it over, and the import
graph decides the order. `dispatch.line_dispatch` calls the handlers
registered with `dispatch.handler_register`, and `mcp.Server` calls the
tools registered with it; neither names an engine.

2.12 Line coverage (Questions 11 B, 22 B). Every line of the module is run
by its own unit suite, measured during the run, which fails at the first
line never run. A line that raises "internal error", which no test is
expected to reach, needs a mark that exempts it: a trailing comment,
`# pragma: no cover`, as coverage.py marks one. Immediate 100 percent line
coverage is a non-goal, as some suites may not be able to run; it becomes a
goal once everything is running.

2.13 Outside the run (Questions 12 C, 13 A). `xsjs_screenshot.py` and
`xsjs_screenshot_wsl.py` stay out of the run. `test_posix.py`,
`test_wire.py` and `test_browser.py` stay after the stream, inside the same
120 s.

2.14 The digests (Question 24 A). Pin these sha256 digests in the `_PINS`
of `third_party_fetch.py`. They were measured with `hashlib` from the
archives downloaded from the pinned URLs on 2026-10-25.

    ttyd-1.7.7.tar.gz
    039dd995229377caee919898b7bd54484accec3bba49c118e2d5cd6ec51e3650
    sqlite-wasm-3460100.zip
    79b5fbfd1c5ca35f492624bb6b9323e6c74e483e2a55ff18ce5904a8cdb1b38c
    xterm-5.5.0.tgz
    bd954fa721872170188cc5d7e83e88db3c83c9a18a4e8d24c2783d26491f59d2

2.15 Prettier (Question 25 A). Run prettier on `test_settings.json` once,
so that the array `"data": [ {} ]` in the gold of `test_third_party_fetch`
takes prettier's form, `[{}]`. JSON has no row in `reformat_table.json`,
so no check reads the file.

2.16 One failure (Question 26 A). `test_all.py --failures N` passes a run
only when the consumer counts exactly N failing tests. A failure counts one
per test, however many of its subtests fail, and one per failed fixture.
Measured on `failing_suite.py`, a suite that fails by design, on
2026-10-25: a failed assertion, an error and an unexpected success count
one each; a test with two failed subtests counts one; an expected failure
counts as passed; a skip counts as skipped; with failfast the stream ends
with a bail out after the first failure, which adds none. A failed
`setUpClass` or `setUpModule` was not measured.

2.17 Done (Questions 14 A, 15 A). The consumer stops reading at a bail out
and ignores what follows. `test_bootstrap`'s helper `tests_refused` was
renamed so that the loader no longer collects it. `test_install_pinned`
reads the archive from the setting `powershell.ttyd_archive`.

2.18 Withdrawn. Question 23, whether the answers an earlier postmortem
counted as satisfied are satisfied, was dropped on 2026-10-28, since the
planning documents are to be deleted. Questions 18, 20, 21 and 30 were
withdrawn by the maintainer; 2.19 holds what follows from the last.

2.19 `tap_loop` does not import the driver (2026-10-28). Question 30 was
withdrawn because it rested on the premise of a forbidden implementation:
`tap_loop.py`, a main loop file the engine loads, importing `test_all`.
The import goes (task 5.8). The `--tty` run, in which the driver starts
`bootstrap.py`, which loads `tap_loop`, which runs the driver's stream in a
child, stays: the maintainer asked for it on 2026-10-25
(`tmp/tasks_25_2014.md` item 14). See 10.2 item 7.

## 3 The tree on 2026-10-28

3.1 The driver's `_MODULES` lists 32 suites in one phase. The stream passed
32 of 32 in about 10 s on 2026-10-25 (`tmp/tasks_25_2014.md` item 52.3).
It was not rerun for this plan.

3.2 24 of the 32 suites import `unittest.mock`. Only the suites of
`tap_producer`, `tap_consumer`, `settings`, `stall_loop`, `vectors_make`,
`mcp`, `main_loop` and `tap_tty` do not. The kinds of replacement, every
one of them now forbidden (2.3, 2.4):

1. callee: a project module, or one of its functions, replaced by an object
   that records calls or gives canned answers;
2. system: an OS call, a process attribute or a standard stream replaced;
3. program: a program the module starts replaced;
4. fault: a function replaced by one that raises;
5. own data: the module's own constant, path or state set by the test.

| Suite | Replaced | Kind |
| --- | --- | --- |
| `test_bootstrap` | `verbose` by `VerboseDouble` in `sys.modules`; `tty.setraw`; `os.environ`; `substrate` made unimportable; `_MAIN_LOOP_STOCK` | callee, system, own data |
| `test_devtools` | `shutil.which` (powershell.exe), `shutil.rmtree`; pipes and a process by `CannedReader`, `FrameRecorder`, `ClientRig`, `RunningProcess` | system, program |
| `test_dispatch` | handlers made by `unittest.mock.Mock`; the tables `_HANDLERS` and `_IDS` cleared | callee, own data |
| `test_echo_loop` | `engine_tap.error_take` | callee |
| `test_engine_db`, `_doc`, `_kv`, `_sql`, `_turn` | the store by `StoreDouble`; `dispatch.handler_register` by a recorder; `_STATE` | callee, own data |
| `test_engine_mcp` | the server by `ServerDouble`; `handler_register`; `_STATE` | callee, own data |
| `test_engine_system` | `os.execv`, `sys.orig_argv`; the server by `ServerDouble`; `handler_register`; `_STATE` | system, callee, own data |
| `test_engine_tap` | `open` by `mock_open`; `verbose.log`; `handler_register`; `_STATE` | system, callee, own data |
| `test_engine_verbose` | the `verbose` calls by `VerboseDouble`; `handler_register`; `_STATE` | callee, own data |
| `test_internationalization` | the strings table `_STRINGS` | own data |
| `test_jslb` | `open` by `_FailingFile` and `_BrokenFile` | fault |
| `test_mcp_stdio` | `mcp` by `ServerDouble` in `sys.modules` | callee |
| `test_page_build` | its own compile and build functions, `_HTML_PATH`, `sys.argv`, `shutil.which`, `subprocess.run` (tsc); reads `_TSC_SECONDS` | own data, system, program |
| `test_reformat` | `subprocess.run` (the formatters) | program |
| `test_substrate` | `schema_apply` made to raise | fault |
| `test_tap_loop` | `test_all` by a namespace whose file is a driver script | callee |
| `test_test` | `harness._SETTINGS_PATH`, `_TESTS_PATH` and `_STATE` | own data |
| `test_test_posix` | `reformat` by `ReformatDouble` in `sys.modules` | callee, program |
| `test_third_party_fetch` | `_THIRD_PARTY_PATH` | own data |
| `test_verbose` | `sys.stdout` and `sys.stderr` by `io.StringIO` | system |

`test_mcp.py` holds a class `DirectLink`, unchecked: task 5.8 decides
whether it is a double. `test_devtools` passes its wait times through the
API, `devtools.WaitTimer` and the `wait_seconds` of
`devtools.ProtocolClient`, and changes no constant.

3.3 Calls outside the import graph, which a survey of imports with `ast`
does not see:

1. `bootstrap.py` loads `main_loop.py` from its source, or in debug mode a
   main loop file named by `--main-loop`, such as `echo_loop.py`,
   `stall_loop.py` or `tap_loop.py`.
2. `engine_system.py` re-runs the program that loaded it (3.7).
3. `test_all.py` calls `vectors_make.vectors_write` inside the block of
   `test_jslb`, whose `TestVectors` reads the files it writes (3.4).
4. `test_bootstrap.py` runs the stock `main_loop.py` in one test.
5. `test_mcp_stdio.py` runs `mcp_stdio.py` as a child process.
6. `tap_tty.py` runs `bootstrap.py` as a program on a pty, and `tap_loop.py`
   runs the driver as a child, `python3 test_all.py --stream`.
7. `dispatch` and `mcp.Server` call what is registered with them (2.11).
8. `test_internationalization.py` reads the source text of every non-test
   `python/*.py` and `ts/*.ts` file for the names passed to `i18n`, and
   calls none of them.
9. `test_test.py` is the one suite of two modules, `harness` and
   `category`, and `category.limit_seconds` calls `harness.gold_get`. Rule
   4.1 item 2 holds inside its block only because `unittest` loads the
   classes of a module in name order and `TestHarness` sorts before
   `TestLimit`, the one class of `category` that reaches `harness`.
   Renaming either class can break the order with no failure to show it.

3.4 The loop between `test_jslb` and `vectors_make`. `vectors_make` calls
the `jslb` encoder to make the success vectors, so its suite needs the
suite of `jslb` first. The suite of `jslb` reads the vectors that the
driver makes with `vectors_make` inside its block, so it needs the suite of
`vectors_make` first. A bug in `vectors_make` shows as a failure of
`test_jslb`, a bug two modules deep. The driver holds the edge, so the
import graph does not show it.

3.5 `tap_loop` imports `test_all` to find the driver's path (2.19). The
import also runs the driver's module code, which sets
`sys.pycache_prefix`, inside the engine's process.

3.6 Written after the last layer table, and so in none:
`tap_loop.py`, which calls into `dispatch`, `internationalization`, `jslb`,
`settings` and, until task 5.8, `test_all`; `tap_tty.py`, which calls into
`harness` and `jslb` and runs `bootstrap.py` as a program;
`failing_suite.py`; `test_tap_loop.py`; and `test_tap_tty.py`, a stdio
suite (2.7).

3.7 The restart. `engine_system`'s `system.restart` handler and
`system_restart` tool check debug mode and that the main loop file exists,
then exec `sys.executable` with `sys.orig_argv` and `--main-loop NAME` set:
they re-run the program that loaded `engine_system`. Under the engine that
is `bootstrap.py`: `bootstrap` -> `main_loop` -> `engine_system` ->
`bootstrap`, a loop by 4.1 item 4. `mcp_stdio.py` registers the same tools
through `engine_system.tools_register`, so a restart there re-runs
`mcp_stdio.py --root ROOT --main-loop NAME`, an option its parser does not
define, and the request is never answered. That is from reading only and
has not been run.

3.8 Every digest in `third_party_fetch._PINS` is empty, and
`test_settings.json` holds the array `"data": [ {} ]` that prettier writes
as `[{}]`.

3.9 No file outside the planning documents cites one. The citations of the
missing `TAP_PLAN.md` were removed on 2026-10-28 from `python/test_all.py`,
`python/mcp.py`, `API/python/mcp.pyi`, `python/test_wire.py`,
`ts/provider.ts` and `API/README.md` (9.7).

## 4 The rules every task follows

4.1 The order.

1. Module M calls into module N when M imports N, at module level or inside
   a function, loads N's file, runs N as a program, or has N run inside M's
   test block, as the driver does when it writes data with N before M's
   suite loads. A call of a function M was handed is not a call into the
   module that handed it over (2.11).
2. The suite of M runs only after the suite of every module M calls into,
   directly or transitively, has run and passed.
3. A layer is the set of suites whose callees' suites all sit in earlier
   layers. Layer 0 holds the suites of modules that call into no project
   module.
4. Two modules that call into each other, directly or around a longer loop,
   are a bug, fixed before the order is relied on.
5. Within a layer the suites run in alphabetical order. Any order is valid,
   since no suite of a layer calls into another of the same layer; the
   alphabet only makes the order fixed.
6. The bootstrap exception: the blocks of the unit phase are written by the
   producer and read by the consumer before the pair test, first in the
   integration phase (2.2), has proven the two agree. A failure there stops
   the run like any other. The consumer's verdict is trusted from the pair
   test on.

4.2 Unit and integration (2.5). The unit suite `test_<module>.py` tests the
module through its API with no double, and calls real callees only where
the module calls them. A suite whose module calls into
`internationalization` alone is a unit suite. The integration suite
`test_integrate_<module>.py` drives the module through the entry point that
joins it to its callees, such as a handler registered in the real dispatch
and served a real JSLB line, a tool called through a real `mcp.Server`, or
a main loop serving every engine. It also holds the tests moved out of the
unit suite because they need a callee working as a whole. A test that
needs the whole program on a tty, an exec, or a child `bootstrap.py` or
`mcp_stdio.py` belongs to a stdio suite (2.7, task 5.11).

Rules 4.3 to 4.8 remove each kind of replacement of 3.2.

4.3 Callee: the test calls the real callee, whose unit suite has passed
earlier in the run. When the callee keeps state for the whole process, such
as the dispatch table or an engine's root, the test runs in a forked child,
as `test_main_loop.py` and `test_echo_loop.py` do. That isolates the state
with no double, no new public function and no change of the module's state
by the test (2.4). A recorder of calls is replaced by a check of the effect
in the real callee: the type the real dispatch table answers, or the rows
and files of a real store on a scratch root under `build/`. A handler or a
tool that the test hands to `dispatch` or `mcp` is a plain function of the
test, never a `Mock` (2.11).

4.4 System: the real thing. That means a scratch file under `build/`, a
child process of `python3`, `os.pipe` and `os.dup2` for a standard stream,
an environment set in a forked child, or a pty pair from `pty.openpty` in
process for a module that calls `tty.setraw`.

4.5 Fault: a real fault. Writes to `/dev/full` give ENOSPC. A directory
without write permission refuses new files. `resource.setrlimit` with
`RLIMIT_FSIZE`, with `SIGXFSZ` ignored, gives EFBIG.

4.6 Program: a test that needs a program 2.10 does not approve (`dash`,
`tsc`, the formatters, ttyd, `powershell.exe`, Chrome) moves to a later
suite, `test_<module>_<program>.py`. Each is listed apart in `test_all.py`,
beside `_FAILING`, with the program it waits on, and no category runs it
until the program is approved.

4.7 Own data, forbidden by 2.4. The test sets the module up through its
API: the arguments of its public functions, such as the store, root,
server or debug flag each engine's `handlers_register` takes; its command
line, such as `bootstrap.py --root ROOT --main-loop NAME`; the files of a
scratch root it is pointed at; or the environment of a forked child. State
kept for the whole process starts fresh in a forked child, and the test
never resets it. A module whose API takes no path is tested on its real
files: `harness` on the real `settings.json` and `test_settings.json`,
reading the gold under its suite's own id, and
`third_party_fetch.file_fetch` writing into the real, gitignored
`third_party/` under names no pin uses, which the test removes (10.2 item
8). Bytes a module takes through a parameter, such as the `reader` of
`devtools.ProtocolClient`, go through its API, carried by a real object
such as one end of an `os.pipe`, never by a hand-made reader (2.3). A test
reads no private name of the module it tests.

4.8 Removed: a test that no approval could ever make real, such as a close
that fails after a failed write, a malformed file under a path only a
constant holds, or a module made unimportable, is removed and recorded in
the task's report with the code path it reached. It is never kept with a
double or a change of state.

## 5 Tasks

5.1 Pin the digests (2.14).

1. Owns `_PINS` in `python/third_party_fetch.py`. Needs nothing.
2. Set the sha256 of `ttyd-1.7.7.tar.gz`, `sqlite-wasm-3460100.zip` and
   `xterm-5.5.0.tgz` to the digests of 2.14.
3. Done when `test_third_party_fetch` passes and `_PINS` holds no empty
   digest. Running the fetch itself is left to the maintainer.

5.2 Run prettier once on `test_settings.json` (2.15).

1. Owns `test_settings.json` for its length. Runs first, alone, before any
   task edits a gold.
2. Stage the file, as the reformatting exception of the project rules
   allows, and run prettier on it with the options `reformat_table.json`
   gives prettier.
3. Done when the diff changes only the array of 2.15, a second run changes
   nothing, and the staged state is reported for the maintainer.

5.3 The driver's gate.

1. Owns `StreamWriter` and the end check of `python/test_all.py`. Needs
   nothing.
2. Today the driver stops after the first block that fails, by the verdict
   the producer returns, and checks the stream with the consumer only after
   the last module, so a malformed line is reported only after every later
   module has run.
3. `StreamWriter.line_write` feeds each line, as it writes it, to a
   `tap_consumer.StreamReader` through `Parser.parse_line`, and raises at
   the first line that does not fit, naming the module whose block holds
   it. Lines relayed under `--tty` go through the same reader.
4. The run stops after the first block in which the reader counts a
   failure. The reader's count is then compared with `--failures`.
5. After `run_end`, `stream_ended` must be true. The reader replaces the
   `document_stats` check at the end, so the stream is checked once. The
   gate is per block, which is stricter than a gate per layer and gives the
   same order.
6. Done when `--stream` and `--tty --stream` pass in both categories, and
   `--module failing_suite` behaves as measured on 2026-10-25: `--failures
   4` passes a normal-test run, and `--failures 1` passes a smoke-test run
   ended by its bail out. The driver has no suite, since `test_test.py`
   tests the infrastructure for testing and not the driver.

5.4 The pair test (2.2, 2.16).

1. Owns the new `python/test_tap_pair.py` and its gold, and
   `tap_producer.py`, `tap_consumer.py` and their suites for any fix the
   pair test shows. Needs 5.2.
2. It tests that the consumer validates what the producer writes. It
   imports `tap_producer`, `tap_consumer` and the standard library only.
   Its label is `smoke-test`, and it is the first suite of the integration
   phase.
3. Its fixtures are its own test classes, nested in its test class so that
   no loader collects them, one per kind of outcome:
   1. a pass;
   2. a skip, with a reason and without one;
   3. a failed assertion;
   4. an error;
   5. a test with one failed and one passed subtest, and one with two
      failed subtests;
   6. an expected failure, and an unexpected success;
   7. a failing `setUpClass`, a failing `tearDownClass` and a failing
      `setUpModule`;
   8. a module that fails to load;
   9. a module with no tests.

   Each runs without failfast and with it, alone and as one of several
   blocks of one stream.
4. For each run, through `tap_producer.TAPTestRunner` into a list of lines:
   1. every line parses with `tap_consumer.Parser.parse_line` to a kind
      other than `Unknown`;
   2. a `tap_consumer.StreamReader` accepts every line, and `stream_ended`
      is true after the last;
   3. `tap_consumer.document_stats` of the whole text is `well_formed`, and
      its `plan`, `passed`, `failed` and `skipped` equal the counts of item
      5;
   4. the consumer's verdict, `failed` equal to zero, equals the verdict of
      the runner's `module_run`.
5. The oracle is the `unittest.TestResult` of the same fixtures, which is
   independent of the literal lines `test_tap_producer.py` pins and of the
   hand-written lines `test_tap_consumer.py` reads. `plan` is the sum of
   `countTestCases` over the blocks. By 2.16, a test whose outcomes are all
   success or expected failure counts as passed; a test with any failure,
   error or unexpected success counts as one failure, however many
   subtests failed; a failed fixture counts as one failure; a bail out
   counts as one failure unless it follows a failed point; a skip counts as
   skipped and not as passed. A failed `setUpClass`, `tearDownClass` and
   `setUpModule`, unmeasured until now, are measured by the pair test
   itself.
6. Done when it passes alone, and a deliberate break of the consumer's
   failure count, then undone, makes it fail.

5.5 `jslb`: the vectors split and the doubles (3.4).

1. Owns `jslb.py`, `test_jslb.py`, the new `test_jslb_vectors.py`,
   `vectors_make.py`, `test_vectors_make.py` and the new
   `test_integrate_vectors_make.py`. Needs 5.2.
2. A new module, `python/test_jslb_vectors.py`, takes `TestVectors` and
   the helpers only it uses (`_vector_read`, `_vector_names` and the
   vectors path) out of `test_jslb.py`. It imports `jslb` and
   `vectors_make`, and its `setUpModule` writes the vectors into
   `build/vectors` with `vectors_make.vectors_write` before any of its
   tests reads them, so the write is an import that a survey with `ast`
   sees. The gold values the vector tests read stay under
   `python.test_jslb`.
3. Unconfirmed assumption, checked before it is relied on: `TestVectors`
   derives from `_ScratchCase` of `test_jslb.py`, which the other classes
   there share, so the new module imports `test_jslb` for that base class,
   whose suite has passed by then.
4. `test_all.py` loses `_VECTORS_READER`, `_VECTORS_PATH` and the write in
   `suite_load`, which becomes the import alone, under the lock of 7.3. The
   header comments of `test_jslb.py` and `test_all.py` drop the vectors.
   `page_build.py` also writes the vectors, for the page, and is unchanged.
5. Replace the `open` faults of `test_jslb` by real faults (4.5), or remove
   them by 4.8.
6. Write `test_integrate_vectors_make.py` by 4.2. `jslb` gets no
   integration suite (2.5).
7. Done when no suite of the task imports `unittest.mock` or changes a
   module's state, every suite passes alone, and `build/vectors` is written
   by the `setUpModule` of `test_jslb_vectors`.

5.6 Line coverage (2.12).

1. Owns the new `python/line_coverage.py` and
   `API/python/line_coverage.pyi`, `harness.py`, `category.py` and
   `test_test.py`, and the `--coverage` option of `test_all.py` under the
   lock. Needs 5.2.
2. `test_test` tests `harness` on its real files (4.7). The patches of
   `_SETTINGS_PATH`, `_TESTS_PATH` and `_STATE` go, and a test that needs a
   file only those constants could point at is removed by 4.8.
3. Write the stub first. The module uses the standard library only. It
   counts `sys.monitoring` LINE events, and returns `DISABLE` at the first
   event of each location so that the run stays fast.
4. The lines that count are those that hold code: the lines of `co_lines()`
   over every code object of the module, found through `co_consts`. A line
   run at import, at the module's top level or in a class body, counts when
   it ran at any time in the run. A line of a function counts only while
   one of the module's own unit suites runs. Both `test_jslb` and
   `test_jslb_vectors` count for `jslb`, and `test_test` counts for
   `harness`, `category` and `line_coverage`.
5. A statement whose first line ends with `# pragma: no cover` is exempt,
   with the block it opens, as coverage.py does. Statements are found with
   `ast`. The mark is put only on lines that raise "internal error".
6. With `--coverage`, the run fails after a unit suite's block at the first
   line of its modules that never ran, naming the file and the line.
   Without it nothing is measured. It becomes the default once every suite
   runs (2.12).
7. Its tests are in `test_test.py`, on sample modules written to a scratch
   directory and really run.
8. Done when `test_test` passes, and one whole smoke-test run with
   `--coverage` stays inside 120 s. The first unrun line it names is
   recorded as a measurement, not fixed.

5.7 Doubles out: `internationalization`, `substrate`, `verbose`,
`stall_loop`, `third_party_fetch`.

1. Owns those modules apart from `_PINS` (5.1), and their suites. Needs
   5.2.
2. `test_substrate`: a real fault in place of `schema_apply` (4.5).
   `test_verbose`: the standard streams through `os.pipe` and `os.dup2`, or
   a child (4.4). `test_internationalization`: the real strings table
   through `i18n`, the patch of `_STRINGS` gone (4.7).
   `test_third_party_fetch`: the real `third_party/` (4.7), the patch of
   `_THIRD_PARTY_PATH` gone.
3. No integration suite: `substrate`, `verbose` and `stall_loop` call into
   `internationalization` alone, and `internationalization` and
   `third_party_fetch` call into no project module (2.5).
4. Done when no suite of the task imports `unittest.mock` or changes a
   module's state, and every suite passes alone.

5.8 Doubles out, then integration suites: `dispatch`, `settings`, `mcp`,
`echo_loop`, `tap_loop`.

1. Owns those modules, their suites and their new integration suites.
   Needs 5.2.
2. `test_dispatch`: plain handler functions in place of `Mock`, and each
   test that registers runs in a forked child in place of clearing
   `_HANDLERS` and `_IDS` (4.3, 4.7). `test_echo_loop`: the real
   `engine_tap.error_take`, its effect read from the root. `test_mcp`:
   decide whether `DirectLink` is a double, and replace it by real streams
   if it is (4.4).
3. `tap_loop` finds the driver by its path beside its own file, in place of
   `import test_all` (2.19). `test_tap_loop` runs the real driver as its
   child, with `--module` naming a small suite, `failing_suite` for the
   failure paths. That suite is never `test_tap_loop` itself.
4. Write `test_integrate_dispatch.py`, `test_integrate_settings.py`,
   `test_integrate_mcp.py`, `test_integrate_echo_loop.py` and
   `test_integrate_tap_loop.py` by 4.2.
5. Done as 5.7 item 4.

5.9 Doubles out, then integration suites: the store engines `engine_db`,
`engine_doc`, `engine_kv`, `engine_sql`, `engine_turn`.

1. Owns those modules, their suites and their new integration suites.
   Needs 5.2.
2. A real `substrate` store on a scratch root in place of `StoreDouble`,
   handed to the engine through `handlers_register(store)`, each test in a
   forked child with the real `dispatch.handler_register`, in place of
   setting `_STATE` (4.3, 4.7).
3. Each `test_integrate_engine_*.py` registers the engine in the real
   dispatch and serves lines of the gold through `dispatch.line_dispatch`,
   the replies encoded by the real `jslb`.
4. Done as 5.7 item 4.

5.10 Doubles out, then integration suites: `engine_tap`,
`engine_verbose`, `engine_mcp`, `engine_system`.

1. Owns those modules, their suites and their new integration suites.
   Needs 5.2.
2. `test_engine_tap`: real files, or real faults, in place of `mock_open`,
   and the real `verbose` log on a scratch root. `test_engine_verbose`: the
   real `verbose`. `test_engine_mcp` and `test_engine_system`: a real
   `mcp.Server` in place of `ServerDouble`. The root, debug flag and server
   go through each engine's `handlers_register` in a forked child, the
   patches of `_STATE` gone (4.7).
3. The tests of `engine_system` that patch `os.execv` and `sys.orig_argv`
   leave the unit suite. The exec is tested whole by `test_tap_tty`'s
   `test_restart_served`, and the task reports to 5.11 any behavior the
   removed tests covered that it does not. Task 5.15 changes the restart
   itself.
4. Write the four `test_integrate_engine_*.py` by 4.2.
5. Done as 5.7 item 4.

5.11 Doubles out, the integration suites of the top, and the stdio phase:
`main_loop`, `bootstrap`, `mcp_stdio`, `tap_tty`.

1. Owns those modules, `test_main_loop.py`, `test_bootstrap.py`,
   `test_mcp_stdio.py`, `test_tap_tty.py`, the new
   `test_mcp_stdio_process.py`, any new stdio or later suite of these
   modules, and their integration suites. Needs 5.2.
2. `test_bootstrap`: the real `verbose`. The run happens in process on a
   pty pair in place of pipes with `tty.setraw` patched, which keeps the
   suite in the unit phase (2.7). The environment is set in a forked child.
   The main loop is chosen through the command line, `--main-loop NAME` on
   a scratch root, or is the stock `main_loop.py` itself, in place of
   patching `_MAIN_LOOP_STOCK` (4.7). The console tests that run `dash`
   move to `test_bootstrap_dash.py`, a later suite (4.6). The test of
   `substrate` made unimportable is removed by 4.8.
3. `test_mcp_stdio`: `stdio_run` with a real `mcp.Server`, a `register`
   function of the test and real streams. `TestProcess` moves to
   `test_mcp_stdio_process.py`, a stdio suite (2.7).
4. Write `test_integrate_main_loop.py`, `test_integrate_bootstrap.py` and
   `test_integrate_mcp_stdio.py` by 4.2.
5. Done as 5.7 item 4, and `test_tap_tty` still covers 2.8.

5.12 Doubles out where a program is needed: `page_build`, `devtools`,
`reformat`, `test_posix`.

1. Owns those modules, their suites, their later suites and their
   integration suites. Needs 5.2.
2. The tests that run or replace tsc move to `test_page_build_tsc.py`, with
   those that patch `page_build`'s own compile and build functions or
   `_HTML_PATH`, or read `_TSC_SECONDS`: there the real compile runs into
   the real `html/` (4.7). The tests that replace the formatters move to
   `test_reformat_formatters.py` and `test_test_posix_formatters.py`.
   Those that need `powershell.exe` move to `test_devtools_powershell.py`.
   All are later suites (4.6).
3. `test_page_build`'s `sys.argv`: the real argument list through a child
   or through a parameter the function already takes. `test_devtools`: the
   `shutil.rmtree` faults made real (4.5) or removed by 4.8, and
   `CannedReader`, `FrameRecorder`, `ClientRig` and `RunningProcess`
   replaced by real pipes and a real `python3` child (4.4, 4.7).
4. Write `test_integrate_page_build.py` (its `vectors_make` part) and
   `test_integrate_test_posix.py` (its `category` and `reformat` part) by
   4.2. `devtools` and `reformat` call into no project module.
5. Done as 5.7 item 4.

5.13 The three phases (2.1, 2.7).

1. Owns `_MODULES`, the list of later suites and the header comment of
   `python/test_all.py`. Needs 5.3 to 5.12 to have delivered their suites.
   It may start on what exists.
2. Recompute the layers with `ast` by the rules of 4.1, over the tree as
   the tasks leave it, with the edges of 3.3 that `ast` does not see.
3. `_MODULES` becomes the unit suites by layer, alphabetical within each
   layer; then `test_tap_pair`; then the integration suites by the layer of
   their module, alphabetical within; then the stdio suites by layer,
   `test_mcp_stdio_process` before `test_tap_tty`. No line marks a phase.
4. The later suites of 4.6 are listed apart with their programs.
   `failing_suite` stays in `_FAILING`.
5. The header comment states the order of item 3 and the rules of 4.1 that
   produce it, and cites no planning document (3.9).
6. Every new suite is labelled `smoke-test`, unless the run's timings show
   that the 120 s budget is broken. Then the slowest suites become
   `normal-test`, by the project rule.
7. Done when the list holds every suite file in `python/`, each once,
   except `failing_suite`, the later suites and the checks run after the
   stream.

5.14 Run and fix in order.

1. One agent, serial. Needs 5.13.
2. Run `python3 python/test_all.py --stream`. At the first failing block,
   fix the module that block tests, or its suite: the suites of everything
   it calls into have passed, so the bug is in that module or its suite.
   Run again, and repeat until the stream is clean. Then do the same with
   `--normal-test`, then with `--tty` in both categories.
3. Run the whole smoke-test run without `--stream`. It is expected to stop
   at `test_wire.py` for want of ttyd (9.1).
4. Run the formatters twice and pyright strict on every changed file.
5. Done when all four streams pass inside 120 s. The time of one run with
   `--coverage`, and the first unrun line it names, are recorded as
   measurements.

5.15 The restart (2.9, 3.7).

1. Needs 5.14, since it changes modules that tasks 5.8, 5.10 and 5.11 own.
   No question blocks it.
2. The stubs in `API/python/` change first. `dispatch` gains a restart
   value that a handler returns, which `line_dispatch` passes out.
   `engine_system`'s `system_restart` checks debug mode and that the main
   loop file exists, then returns it in place of `os.execv`, and
   `_argv_make` and its use of `sys.orig_argv` go. `main_loop`'s
   `loop_run` returns the restart's main loop name to `bootstrap`, every
   other main loop file returning None. `bootstrap` re-execs itself,
   `python3 bootstrap.py --root ROOT --main-loop NAME`, on the same tty.
3. The restart tool returns its `ToolResult` through `mcp.Server`, so the
   restart goes back by a `restart_take` beside `failure_take`. Under the
   engine, `engine_mcp` hands it on to `main_loop`. Under `mcp_stdio.py`,
   `stdio_run` writes the reply, then `mcp_stdio.py` re-execs itself,
   `python3 mcp_stdio.py --root ROOT`; the named main loop is checked by
   `engine_system` and not served, since `mcp_stdio.py` serves none (10.2
   item 6).
4. `test_tap_tty`'s `test_restart_served` holds unchanged.
   `test_mcp_stdio_process` gains a restart over stdio: the reply is
   written, and the new process answers the next request.
5. Done when task 5.14 passes again.

## 6 Order

6.1 Wave 0: task 5.2 alone.

6.2 Wave 1, in parallel: tasks 5.1 and 5.3 to 5.12. No task waits on a
question.

6.3 Wave 2: task 5.13. Wave 3: task 5.14. Wave 4: task 5.15.

6.4 The phase order puts the pair test after every unit suite, so the
bootstrap exception of 4.1 item 6 covers the whole unit phase. The driver's
gate trusts the consumer before the pair test has proven it, and any
failure still stops the run.

## 7 How agents share the tree

7.1 Every task works in the main tree. Worktrees are not used: nothing is
committed, so a worktree made from `HEAD` would not see the changes of
earlier tasks.

7.2 A task owns the files its section names: the suites, the new suites,
the stubs, and the modules those suites test, for any fix the suites need.
A failure found in a module owned by another task is reported to that
task, with the failing test. It is not fixed across ownership.

7.3 Shared files are edited only under a lock, by the project rule. The
task renames the file with its task number appended, such as
`test_all.py.5.3`, for the length of one edit, then renames it back. A run
or an edit that finds the file missing waits and retries; it never
recreates the file. The shared files:

1. `python/test_all.py`: tasks 5.3 (the gate), 5.5 (the vectors write), 5.6
   (the coverage option) and 5.13 (the list). Any task adds its new suites
   to `_MODULES` so that `--module` runs them; task 5.13 places them.
2. `test_settings.json`: each suite's gold under its own id only, edited in
   place, never rewritten whole, except by task 5.2, which runs before any
   other task.
3. `i18n/en-US.json`: new texts under the module's own keys.

7.4 Every task:

1. runs its suites alone with `python3 python/test_all.py --module NAME`,
   with `--normal-test` for a `normal-test` suite;
2. sets `PYTHONPYCACHEPREFIX=build/pycache` for any direct run of
   `unittest`, so that no bytecode lands beside the sources;
3. changes a public function's stub in `API/python/` before the function;
4. runs `python3 python/reformat.py` twice and pyright strict on the
   changed Python files, and reports it if the second run changes anything;
5. ends with a report naming each test moved and where it went, and each
   test removed by 4.8 with the code path it reached.

## 8 Questions

None is open. Questions 27, 28 and 29 were answered and Question 30
withdrawn on 2026-10-28 (2.4, 2.5, 2.9, 2.19).

## 9 Outside this plan

9.1 `test_wire.py` and `test_browser.py` stay after the stream (2.13). They
need ttyd, which 2.10 does not approve. The digests of task 5.1 unblock the
fetch, not the build, which `xsjs_install.ps1` does on Windows.

9.2 The same two-deep order problem on the TypeScript side: `test_wire.py`
reads the stream of the TypeScript producer, `ts/test_wire_rungs.ts`, with
the Python consumer before the TypeScript suites, `ts/test_tap_producer.ts`
among them, run in the suites root of `test_browser.py`.

9.3 `xsjs_screenshot.py` and `xsjs_screenshot_wsl.py` stay out of the run
(2.13).

9.4 Reconnection after a restart that hangs up is not tested yet (2.9).

9.5 Line coverage of 100 percent becomes required once every suite runs
(2.12). Until then, `--coverage` is run on demand.

9.6 The later suites of 4.6 run once their programs are approved.

9.7 The designs that the removed citations of `TAP_PLAN.md` pointed at are
not in the tree: continuing after an exception in `mcp`, the deferred
`provider.set` of `ts/provider.ts`, and the schema of the gold of the wire
rungs in `test_wire.py` (3.9). Each deferral stands without its design.

## 10 Requirements analysis

The requests of the plan's history, from `tmp/tasks_25_1832.md`,
`tmp/tasks_25_2014.md`, `tmp/tasks_28_0952.md` and `tmp/tasks_28_0959.md`,
and the answers of section 2. A: unsatisfied or modified without cause. B:
unsatisfied or modified with cause but without confirmation. C: confirmed
withdrawn or modified. D: satisfied without modification or withdrawal.

10.1 Class A: none.

10.2 Class B, each satisfied in this plan with the stated cause, and
wanting confirmation:

1. 2.12, "fails at the first line never run": the failure is behind
   `--coverage` while 100 percent is a non-goal. Lines run at import count
   when run anywhere in the run (5.6 item 4).
2. 2.12, `# pragma: no cover` "as coverage.py marks one": the mark exempts
   the statement and the block it opens.
3. 2.1 and 2.2: the pair test runs after every unit suite, so the bootstrap
   exception covers the whole unit phase (4.1 item 6).
4. The project rule's later suites: listed apart in `test_all.py` with the
   program each waits on (4.6). A test that nothing could make real is
   removed and recorded (4.8).
5. 2.7 keeps `test_bootstrap` in process in the earlier phases. It runs on
   a pty pair in place of pipes, so that `tty.setraw` needs no patch (5.11
   item 2).
6. 2.9 names `bootstrap.py`. `mcp_stdio.py`, which `bootstrap.py` does not
   start, re-execs itself the same way, `python3 mcp_stdio.py --root ROOT`,
   and checks the named main loop file without serving it, since it serves
   no main loop (5.15 item 3). The cause: 2.9 requires a new interpreter,
   and the choice that `mcp_stdio.py` not register the tool was removed.
7. 2.19 reads the forbidden implementation as the import of `test_all` by
   `tap_loop`. The `--tty` run, in which the driver's stream runs in a child
   of `tap_loop`, stays, because the maintainer asked for it.
8. 2.4 applied to modules whose API takes no path: `harness` is tested on
   the real `settings.json` and `test_settings.json`, and
   `third_party_fetch` writes into the real, gitignored `third_party/` under
   names no pin uses, which the test removes. A test reads no private name
   of its module, and bytes through a parameter ride a real pipe (4.7).
9. `API/README.md` said a file there changes only when `TAP_PLAN.md`
   changes with it. With `TAP_PLAN.md` gone, it now says a file there
   changes before the code it describes, the rule of 7.4 item 3.
10. "`TEST_PLAN_PY.md` is going to need an update" (`tmp/tasks_25_2014.md`
    item 24): this plan carries the update, and the content it took from
    `TEST_PLAN_PY.md`, since that is to be deleted.

10.3 Class C:

1. "start by testing the python TAP consumers's ability to validate the PY
   TAP producer modules output" and "there should already be a module for
   testing this relationship": modified by 2.2, so the pair test is new and
   runs first in the integration phase.
2. Questions 3, 4 and 18: doubles withdrawn by the project rule (2.3).
3. Questions 20, 21, 23 and 30: withdrawn (2.18).
4. Question 9 A to D: replaced by the written-in E (2.9).
5. Question 5 A: modified by the answer to Question 29, so a module whose
   only project callee is `internationalization` has no integration suite
   (2.5).
6. The driver's comment citing a section of `TEST_PLAN_PY.md`: withdrawn
   with the planning documents, so it cites none (5.13 item 5).

10.4 Class D: Questions 1 A (5.13), 2 A (5.4), 6 A, 7 A, B, E, F, G, H and
J (done in `test_tap_tty`, kept by 5.11), 8 A, 10 A, 12 C, 13 A, 14 A and
15 A (done), 16 A (5.13), 17 A (5.11, 5.13), 19 (section 4), 24 A (5.1),
25 A (5.2), 26 A (5.4), 27 for `bootstrap.py` (5.15), 28 (4.7) and 29
(2.5). The requests of `tmp/tasks_25_1832.md`: the strict dependency order
(4.1, 5.13), "no two modules should call into each other" (3.4 and 3.7
fixed by 5.5 and 5.15, 3.5 by 5.8), a clean acyclic import graph, each
suite run only after those of its callees (4.1 item 2, with the in-block
caveat of 3.3 item 9), and the TAP run from the command line alone (2.13).
Those of `tmp/tasks_25_2014.md`: the TAP run over a tty and the expected
failure count (done, kept by 5.3 and 5.8).

10.5 Unresolved: the confirmations of 10.2. No question is open.
