# TEST_PLAN_PY

The plan for unit testing the Python modules of `python/` in strict
dependency order, as one TAP stream run from the command line:

    python3 python/test_all.py [--smoke-test | --normal-test]

Nothing in this plan has been carried out. Sections 1 to 6 are the plan,
section 7 the order of work, section 8 the questions it needs answered,
section 9 what it leaves out, section 10 the requirements analysis.

## 0 Scope

0.1 In scope: every suite in the TAP stream that `python/test_all.py`
writes, the modules those suites test, and the driver code that orders and
gates them.

0.2 Out of scope, per the maintainer's "i just want tappy from the command
line": screenshots, any browser run, `python/xsjs_screenshot.py` and
`python/xsjs_screenshot_wsl.py`. The driver runs the checks of
`test_posix.py`, then `test_wire.py` and `test_browser.py`, after the stream;
they stay as they are.

## 1 Rules of the order

1.1 Module M calls into module N when M imports N, at module level or
inside a function, loads N's file, runs N as a program, or has N run inside
M's test block, as the driver does when it writes data with N before M's
suite loads.

1.2 The suite of M runs only after the suite of every module M calls into,
directly or transitively, has run and passed.

1.3 A layer is the set of suites whose callees' suites all sit in earlier
layers. Layer 0 holds the suites of modules that call into no project
module.

1.4 Two modules that call into each other, directly or around a longer
loop, are a bug, fixed before the order is relied on.

1.5 Within a layer the suites run in alphabetical order. Any order is
valid, since no suite of a layer calls into another of the same layer; the
alphabet is chosen only to make the order fixed.

1.6 The bootstrap exception: the blocks of layers 0 and 1 are written by the
producer and read by the consumer before the pair test of layer 1 has proven
the two agree. A failure there stops the run like any other. The verdict of
the consumer is trusted from layer 2 on.

## 2 Survey of the tree

2.1 Imports. The standard library `ast` module read every `python/*.py`
file for its imports of project modules, at module level and inside
functions. The import graph has no cycle.

2.2 Calls outside the import graph, found by reading the sources:

1. `bootstrap.py` loads `main_loop.py` from its source, or in debug mode a
   main loop file named by `--main-loop`, such as `echo_loop.py` or
   `stall_loop.py`.
2. `engine_system.py` restarts by `os.execv` of `sys.orig_argv`, with
   `--main-loop NAME` set: it re-runs the program that loaded it.
3. `test_all.py` calls `vectors_make.vectors_write` inside the block of
   `test_jslb`, whose `TestVectors` reads the files it writes.
4. `test_bootstrap.py` runs the stock `main_loop.py` in one test.
5. `test_mcp_stdio.py` runs `mcp_stdio.py` as a child process.
6. `test_engine_system.py` patches `os.execv`, so no suite execs.
7. `dispatch.line_dispatch` calls the handlers registered with
   `dispatch.handler_register`; `mcp.Server` calls the tools registered with
   it. Neither module imports or names an engine.
8. `test_internationalization.py` reads the source text of every non-test
   `python/*.py` and `ts/*.ts` file for the names passed to `i18n`. It reads
   them and calls none of them.

2.3 The producer and consumer relationship. No module tests it.
`test_tap_producer.py` checks the producer's lines against literal lines.
`test_tap_consumer.py` reads hand-written lines in the producer's form.
Neither imports the other module. The only place the consumer reads real
producer output is `test_all.py`, which is the driver, not a suite, and
which checks the stream with `tap_consumer.document_stats` only after the
last module has run.

2.4 The driver's order. The `_MODULES` list of `test_all.py` is a valid
topological order of the import graph except for the pair of 3.1. It is a
flat list, not a list of layers, and its comment cites `TAP_PLAN.md`
section 3.3, which is not in the tree.

## 3 Modules that call into each other

3.1 `test_jslb` and `vectors_make`: a bug.

`vectors_make` calls the `jslb` encoder to make the success vectors, so its
suite needs the suite of `jslb` first. The suite of `jslb` reads the vectors
that the driver makes with `vectors_make` inside its block, so it needs the
suite of `vectors_make` first. A bug in `vectors_make` shows as a failure
of `test_jslb`: a bug two modules deep. The driver holds the edge, so the
import graph does not show it.

The fix:

1. A new module, `python/test_jslb_vectors.py`, takes `TestVectors` and the
   helpers only it uses (`_vector_read`, `_vector_names` and the vectors
   path) out of `test_jslb.py`. It imports `jslb` and `vectors_make`, and
   its `setUpModule` writes the vectors into `build/vectors` with
   `vectors_make.vectors_write` before any of its tests reads them. The
   write is then an import the survey of 2.1 sees.
2. Unconfirmed assumption: `TestVectors` derives from `_ScratchCase` of
   `test_jslb.py`, which the other classes there share, so the new module
   imports `test_jslb` for that base class, whose suite has passed by then.
   The gold values the vector tests read stay under `python.test_jslb`.
3. `test_all.py` loses `_VECTORS_READER`, `_VECTORS_PATH` and the write in
   `suite_load`, which becomes the import alone.
4. The header comments of `test_jslb.py` and `test_all.py` drop the vectors.
5. `page_build.py` also writes the vectors, for the page. It is unchanged.

The suite of `jslb` moves to layer 3, that of `vectors_make` to layer 4,
and `test_jslb_vectors` sits at layer 5.

3.2 `engine_system`'s restart and the program that loaded it: a bug.

`engine_system.system_restart` and its restart MCP tool re-run the program
that loaded `engine_system` (2.2 item 2). Under the engine that program is
`bootstrap.py`: `bootstrap` -> `main_loop` -> `engine_system` ->
`bootstrap`, a loop. `mcp_stdio.py` registers the same tools, restart
included, so a restart there re-runs `mcp_stdio.py --root ROOT --main-loop
NAME`, an option the parser of `mcp_stdio.py` does not define, and the
request is never answered. That second part is from reading only and has
not been run.

The layers of section 6 hold either way, since no suite execs. The fix is
a design choice: Question 1. Whatever the answer, `test_mcp_stdio.py` gains
a test of what a restart tool call does over stdio.

3.3 Registered callbacks: not counted as a cycle, pending Question 2.

`dispatch` and `mcp` call functions that the engines hand them (2.2 item
7). Neither names an engine, and `test_dispatch.py` and `test_mcp.py`
register handlers and tools of their own. The plan does not count a call of
a function a module was handed as a call into the module that handed it
over.

3.4 `test_test.py`: recorded, no change.

`test_test.py` is the one suite of two modules, `harness` and `category`,
and `category.limit_seconds` calls `harness.gold_get`. Rule 1.2 holds inside
its block only because `unittest` loads the classes of a module in name
order and `TestHarness` sorts before `TestLimit`, the one class of
`category` that reaches `harness`. Renaming either class can break the
order with no failure to show it. The suite stays one file, since the
project names `test_test.py` as the suite of the infrastructure for testing.

## 4 The pair test: `python/test_tap_pair.py`

4.1 It tests that the consumer validates what the producer writes. It
imports `tap_producer`, `tap_consumer` and the standard library only, so it
needs no suite but those of layer 0. Its label is `smoke-test`.

4.2 Its fixtures are its own test classes, nested in its test class so that
no loader collects them, one per kind of outcome:

1. a pass;
2. a skip, with a reason and without one;
3. a failed assertion;
4. an error;
5. a test with one failed and one passed subtest, and one with two failed
   subtests;
6. an expected failure, and an unexpected success;
7. a failing `setUpClass`, a failing `tearDownClass` and a failing
   `setUpModule`;
8. a module that fails to load;
9. a module with no tests.

Each runs without failfast and with it, alone and as one of several blocks
of one stream.

4.3 For each run, through `tap_producer.TAPTestRunner` into a list of lines:

1. every line parses with `tap_consumer.Parser.parse_line` to a kind other
   than `Unknown`;
2. a `tap_consumer.StreamReader` accepts every line, and `stream_ended` is
   true after the last;
3. `tap_consumer.document_stats` of the whole text is `well_formed`, and its
   `plan`, `passed`, `failed` and `skipped` equal the counts of 4.4;
4. the consumer's verdict, `failed` equal to zero, equals the verdict of
   the runner's `module_run`.

4.4 The oracle is the `unittest.TestResult` of the same fixtures, which is
independent of the literal lines `test_tap_producer.py` pins and of the
hand-written lines `test_tap_consumer.py` reads. `plan` is the sum of
`countTestCases` over the blocks. Unconfirmed assumption, read from the
fixtures of `test_tap_consumer.py` and not yet checked against a produced
stream: a test whose outcomes are all success or expected failure counts
as passed; a test with any failure, error or unexpected success counts as
one failure, however many subtests failed; a failed fixture counts as one
failure; a bail out counts as one failure unless it follows a failed point;
a skip counts as skipped and not as passed.

## 5 The driver's gate

5.1 Today `test_all.py` stops after the first block that fails, by the
verdict the producer returns, and checks the stream with the consumer only
after the last module. A malformed line is reported only after every later
module has run.

5.2 The change: `StreamWriter.line_write` feeds each line, as it writes it,
to a `tap_consumer.StreamReader`, through `Parser.parse_line`, and raises at
the first line that does not fit, naming the module whose block holds it.
After each block the run stops unless the reader's failed count is zero.
After `run_end`, `stream_ended` must be true. The reader replaces the
`document_stats` check at the end, so the stream is checked once. The gate
is per block, which is stricter than a gate per layer and gives the same
order.

5.3 `_MODULES` is rewritten as the layers of section 6, in layer order and
alphabetical within each layer, and its comment cites `TEST_PLAN_PY.md`
section 6 in place of `TAP_PLAN.md` section 3.3.

## 6 The layers

"Calls into" lists the project modules the tested module calls into, by
2.1 and 2.2. Every suite from layer 3 on except `test_vectors_make` and
`test_test_posix` also imports `harness`, whose suite is in layer 2.

| Layer | Suite | Tests | Calls into |
| --- | --- | --- | --- |
| 0 | `test_tap_consumer` | `tap_consumer` | none |
| 0 | `test_tap_producer` | `tap_producer` | none |
| 1 | `test_tap_pair` | the pair, section 4 | `tap_consumer`, `tap_producer` |
| 2 | `test_internationalization` | `internationalization` | none |
| 2 | `test_reformat` | `reformat` | none |
| 2 | `test_test` | `harness`, `category` | `category` calls `harness` (3.4) |
| 3 | `test_devtools` | `devtools` | none |
| 3 | `test_jslb` | `jslb` | `internationalization` |
| 3 | `test_stall_loop` | `stall_loop` | `internationalization` |
| 3 | `test_substrate` | `substrate` | `internationalization` |
| 3 | `test_test_posix` | `test_posix` | `category`, `reformat` |
| 3 | `test_third_party_fetch` | `third_party_fetch` | none |
| 3 | `test_verbose` | `verbose` | `internationalization` |
| 4 | `test_dispatch` | `dispatch` | `internationalization`, `jslb` |
| 4 | `test_settings` | `settings` | `internationalization`, `jslb` |
| 4 | `test_vectors_make` | `vectors_make` | `jslb` |
| 5 | `test_engine_db` | `engine_db` | `dispatch`, `internationalization`, `jslb`, `substrate` |
| 5 | `test_engine_doc` | `engine_doc` | `dispatch`, `internationalization`, `jslb`, `substrate` |
| 5 | `test_engine_kv` | `engine_kv` | `dispatch`, `internationalization`, `jslb`, `substrate` |
| 5 | `test_engine_sql` | `engine_sql` | `dispatch`, `internationalization`, `jslb`, `substrate` |
| 5 | `test_engine_tap` | `engine_tap` | `dispatch`, `internationalization`, `jslb`, `verbose` |
| 5 | `test_engine_turn` | `engine_turn` | `dispatch`, `internationalization`, `jslb`, `substrate` |
| 5 | `test_engine_verbose` | `engine_verbose` | `dispatch`, `internationalization`, `jslb`, `verbose` |
| 5 | `test_jslb_vectors` | the vectors, 3.1 | `jslb`, `vectors_make` |
| 5 | `test_mcp` | `mcp` | `dispatch`, `internationalization` |
| 5 | `test_page_build` | `page_build` | `vectors_make` |
| 6 | `test_echo_loop` | `echo_loop` | `dispatch`, `engine_tap`, `internationalization`, `jslb`, `settings` |
| 6 | `test_engine_mcp` | `engine_mcp` | `dispatch`, `internationalization`, `jslb`, `mcp` |
| 6 | `test_engine_system` | `engine_system` | `dispatch`, `internationalization`, `jslb`, `mcp`, `settings` |
| 7 | `test_main_loop` | `main_loop` | `dispatch`, the nine `engine_*` modules, `internationalization`, `jslb`, `mcp`, `settings`, `substrate`, `verbose` |
| 7 | `test_mcp_stdio` | `mcp_stdio` | `engine_system`, `internationalization`, `jslb`, `mcp`, `settings` |
| 8 | `test_bootstrap` | `bootstrap` | `internationalization`, `jslb`, `settings`, `verbose`, `main_loop` (loaded) |

That is 32 suites: the 30 of today's list and the 2 new ones of 3.1 and 4.

## 7 Order of work

7.1 Answer the questions of section 8. Nothing before 7.6 waits on them.

7.2 Write `python/test_tap_pair.py` (section 4) and add it to `_MODULES`
after `test_tap_consumer`. Run the smoke-test run and fix until layers 0
and 1 are clean.

7.3 Change the driver's gate (5.2).

7.4 Move the vector tests to `python/test_jslb_vectors.py` and drop the
driver's write (3.1).

7.5 Rewrite `_MODULES` as the layers (5.3).

7.6 Run `python3 python/test_all.py --smoke-test`. At the first failing
block, fix the module that block tests: the suites of everything it calls
into have passed, so the bug is in that module or its suite. Run again, and
repeat until the stream is clean; then run `--normal-test` the same way.

7.7 Fix 3.2 by the answer to Question 1. Any change to a public function
changes its stub in `API/python/` first. Add the restart test of 3.2 to
`test_mcp_stdio.py` and rerun from 7.6.

7.8 Run the formatters on every changed file. `python/*.py` is already in
the reformat whitelist, so the new modules are covered.

7.9 The smoke-test run has 120 seconds in all, the gold `smoke_seconds`.
The two new suites run small fixtures and moved tests, so they are not
expected to need more; the run's timings confirm it.

## 8 Questions

Question 1. How is the loop of 3.2 fixed?

[ ] A. The restart handler and tool return a restart request instead of
calling `os.execv`; `main_loop` returns it to `bootstrap`, which alone
re-runs itself. `mcp_stdio` does not register the restart tool.
(Recommended: the program that owns the process owns its restart.)

[ ] B. As A, but `mcp_stdio` forwards the restart tool to the running
server. That needs a channel from `mcp_stdio` to the server, which is not
designed.

[ ] C. Keep the exec in `engine_system`, since a restart never returns and
so is not a call back; `mcp_stdio` does not register the restart tool.

[ ] D. Keep everything as it is.

Question 2. Are registered callbacks (3.3) calls into the module that
registered them?

[ ] A. No: a module that calls a function it was handed does not call into
the module that handed it over, and the import graph decides the order.
(Recommended.)

[ ] B. Yes: each registry is a cycle, and the plan is redone after a design
that removes the registries.

## 9 Outside this plan

9.1 `test_wire.py` reads the stream of the TypeScript producer,
`ts/test_wire_rungs.ts`, with the Python consumer before the TypeScript
suites, `ts/test_tap_producer.ts` among them, run in the suites root of
`test_browser.py`. That is the same two-deep order problem on the TypeScript
side.

9.2 `TAP_PLAN.md` is cited by `python/test_all.py`, `python/mcp.py`,
`python/test_wire.py`, `API/python/mcp.pyi`, `API/README.md` and
`ts/provider.ts`, and is not in the tree. This plan replaces the citation in
`test_all.py` only (5.3).

9.3 `python/xsjs_screenshot.py` and `python/xsjs_screenshot_wsl.py` have no
suite and are left out (0.2).

## 10 Requirements analysis

The requests of the session, each with its class: A, unsatisfied or
modified without cause; B, unsatisfied or modified with cause but without
confirmation; C, confirmed withdrawn or modified; D, satisfied without
modification or withdrawal.

10.1 "i want a plan to unit test the python modules in strict dependancy
order": D, section 6, except for 10.9.

10.2 "no two modules should call into each other, that needs to be
identified as a bug and fixed": D for 3.1, whose fix is planned. B for 3.2,
whose fix waits on Question 1. B for 3.3, whose reading waits on Question 2.

10.3 "start by testing the python TAP consumers's ability to validate the
PY TAP producer modules output": B. The pair test is the first test of the
relationship, at layer 1, but the unit suites of the producer and the
consumer run before it at layer 0, because rule 1.2, the maintainer's own,
puts the suites of what a module calls into first. Satisfied in the plan;
confirmation wanted.

10.4 "there should already be a module for testing this relationship": B.
None exists (2.3); the plan adds `python/test_tap_pair.py`. Satisfied in
the plan; confirmation wanted.

10.5 "the PY files should have a clean acyclic import graph": D. The import
graph is acyclic (2.1); the two loops of section 3 are outside it.

10.6 "just keep picking the next set that can be tested with the available
set of modules using TAP that are already well tested using TAP test
suites": D, sections 1.3, 5 and 6.

10.7 "when any modules test suite is first run, the test suites for all the
moduls it calls into have already been run and fixed": D, rule 1.2 and
section 6, with the in-block caveat of 3.4.

10.8 "write TEST_PLAN_PY.md and stop": D.

10.9 "i didn't ask for screenshots of tappy, i just want tappy from the
command line": D for the plan's scope (0.2). B for its consequence, that
`xsjs_screenshot.py` and `xsjs_screenshot_wsl.py` get no suite though 10.1
asks for the Python modules; confirmation wanted, or a request for their
suites.

10.10 Unresolved: Questions 1 and 2, and the confirmations of 10.3, 10.4
and 10.9.
