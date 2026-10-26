# TEST_PLAN_PY_QUESTIONS

Question 1 (class A). What is the one run?

[x] A. One run of `python3 python/test_all.py`, one TAP stream of one block
per suite module, in three phases: every unit suite, then the integration
suites from the bottom layer up, then the stdio tests of 0.4. The run stops
at the first failure.

[ ] B. One new Python module that holds every test, run alone.

[ ] C. Two runs: the unit suites, then the integration and stdio suites.

Question 2 (class A). Does the goal's order settle `TEST_PLAN_PY.md` 10.3
and 10.4?

[x] A. Yes: the unit suites of `tap_producer` and `tap_consumer` run first,
and the first integration suite is the pair test of `TEST_PLAN_PY.md`
section 4, a new module `test_tap_pair.py`, since no module tests the pair
today.

[ ] B. No: the pair test runs before any unit suite.

Question 3. What does a unit suite isolate its module from? `harness` and
the TAP modules belong to the tests, not to the module, and stay real.

[x] A. Every project module the module calls into is a double; only the
standard library is real. Every suite changes but those of `category`,
whose one callee is `harness`, and of the 7 modules that call into none:
`tap_producer`, `tap_consumer`, `internationalization`, `harness`,
`reformat`, `devtools` and `third_party_fetch`. (Recommended: the most
traditional form, as asked.)

[ ] B. As A, except `internationalization` stays real, so each text is
still checked against the gold's texts in the unit phase.

[ ] C. Only callees with effects are doubles, as today (0.3): a store, a
process, an exec, a program, the network. The others stay real, the unit
phase keeps the layers of `TEST_PLAN_PY.md` section 6, and the integration
phase tests only the boundaries the doubles cut.

Question 4. How is a double made?

[x] A. From the real module, with `unittest.mock.create_autospec`, so a call
the real signature refuses fails in the unit phase. (Recommended: a double
that drifts from its module is the usual failure of strict unit tests, and
this catches the signature half of it before integration.)

[ ] B. From the module's stub in `API/python/`, read with `ast`, so the
stub, which changes first, is the contract the double holds to.

[ ] C. By hand, as today's doubles are.

Question 5. What is one increment of the integration phase?

[x] A. One module: a suite `test_integrate_<module>.py` for each module that
calls into project modules, testing it with all its real callees, each of
them integrated earlier, in the layers of `TEST_PLAN_PY.md` section 6.
(Recommended: bottom up, one module added at a time, so a failure names
the module just added.)

[ ] B. One call edge: a suite for each pair of a module and one callee, the
other callees doubles.

[ ] C. One layer: a suite for each layer of `TEST_PLAN_PY.md` section 6,
its modules added at once.

Question 6. How do the stdio tests reach `bootstrap.py`?

[x] A. Through a pty of the standard library's `pty` module: the test runs
`python3 python/bootstrap.py --root ROOT` on the tty as ttyd does, plays the
page on the other side with JSLB lines, and hangs up by closing its side,
as ttyd's close does. No ttyd and no browser. (Recommended: the shortest
route that runs the whole program unpatched.)

[ ] B. Through ttyd as `xsjs_install.ps1` builds it, over its WebSocket
with a standard library client, so ttyd and its patches are inside the
proof.

[ ] C. Both, A first.

[ ] D. Over pipes, with raw mode patched as `test_bootstrap` does.

Question 7. What do the stdio tests cover? Mark every box that applies.
(Recommended: all that the answers to Questions 8 and 9 allow.)

[x] A. The start: `tap.start` with id 101, its settings, in debug mode its
test settings, and the Empty reply.

[x] B. Every line type the stock main loop registers, once each, the reply
and the databases checked.

[ ] C. A blob over `overflow_bytes`, both ways.

[ ] D. A second engine on the same root, refused by `engine.lock`.

[x] E. The page's `error` line: exit 1 with nothing written back, the
cascade logged and `Bail out!` ending `tap/typescript.tap`.

[x] F. A handler's `Failure`: its reply, then the server's `error` line,
then exit 1.

[x] G. The hangup that ends a run, with the stock loop and `stall_loop.py`.
    this should not be required to get the very last byte, it just has be
   handled gracefully.

[x] H. The debug lines `settings.put`, `source.put` and `system.restart`,
the restart going on over the same tty, by the answer to Question 9.

[ ] I. The console role, `dash` in the root, if Question 8 approves `dash`.

[x] J. `mcp_stdio.py` on the same root while the engine runs.

Question 8. Which programs may the run start? The project rules require
approval for any command line utility Python runs. Mark every box approved.
(Recommended: A, and B if Question 7 I is marked.)

[x] A. `python3`, for `bootstrap.py` and `mcp_stdio.py`, as `test_mcp_stdio`
and `test_verbose` already start it.

[ ] B. `dash`, for the console role of `bootstrap.py`.

[ ] C. ttyd, for Question 6 B or C.

[ ] D. `tsc`, so the integration suite of `page_build` compiles for real.

[ ] E. The formatters and linters of `reformat_table.json`, so the
integration suite of `reformat` runs them for real.

[ ] F. None: every program stays a double, and `test_posix.py`,
`test_wire.py` and `test_browser.py` remain the only runs of them.

Question 9, `TEST_PLAN_PY.md` Question 1. How is the restart loop fixed?
`engine_system`'s restart execs the program that loaded it: `bootstrap` ->
`main_loop` -> `engine_system` -> `bootstrap`. Under `mcp_stdio.py` it would
re-run `mcp_stdio.py` with `--main-loop`, an option it does not define, and
never answer; that is from reading only.

[x] A. The restart handler and tool return a restart request instead of
calling `os.execv`; `main_loop` returns it to `bootstrap`, which alone
re-runs itself. bootstrap is the natural restart tool.

[ ] B. As A, but `mcp_stdio` forwards the restart tool to the running
server. That needs a channel from `mcp_stdio` to the server, which is not
designed.

[ ] C. Keep the exec in `engine_system`, since a restart never returns and
so is not a call back; `mcp_stdio` does not register the restart tool.

[ ] D. Keep everything as it is.

Question 10 (class A), `TEST_PLAN_PY.md` Question 2. Are registered
callbacks calls into the module that registered them? `dispatch` calls the
handlers the engines register, and `mcp.Server` the tools; neither names an
engine.

[x] A. No: a module that calls a function it was handed does not call into
the module that handed it over, and the import graph decides the order.

[ ] B. Yes: each registry is a cycle, and the plan is redone after a design
that removes the registries.

Question 11. What evidence proves a module correct? Python here is 3.14,
whose `sys.monitoring` measures calls, lines and branches with the standard
library alone.

[ ] A. Every function, class and method of the module's stub in
`API/python/` is called by the module's own unit suite, measured during the
run, which fails at the first one never called. `echo_loop`, `stall_loop`,
`reformat` and `vectors_make` have no stub.

[x] B. Line coverage: every line of the module is run by its own unit
suite, measured during the run, which fails at the first line never run. A
line that raises "internal error", which no test is expected to reach,
needs a mark that exempts it. (Recommended: the usual bar of the
traditional process.)

[ ] C. Branch coverage: as B, for every branch, by `sys.monitoring`'s branch
events.

[ ] D. No measurement: the suites passing is the proof.

Question 12, `TEST_PLAN_PY.md` 10.9. What happens to `xsjs_screenshot.py`
and `xsjs_screenshot_wsl.py`, which have no suite? By its header,
`xsjs_screenshot.py` drives `python/bootstrap.html` in Chrome, typing a
module update ended with ^D: the protocol of the earlier bootstrapper, not
the JSLB that `bootstrap.py` speaks today. No other file of the checkout
names `bootstrap.html`.

[ ] A. Delete both, and `python/bootstrap.html`. (Recommended: a tool for a
protocol that is gone can't be proven correct, only rewritten.)

[ ] B. Rewrite them for today's page, each with a unit suite, `devtools`
a double.

[x] C. Leave them out of the run, as `TEST_PLAN_PY.md` 0.2 does.

Question 13. What happens to the checks that `test_all.py` runs after the
stream: `test_posix.py`, `test_wire.py` and `test_browser.py`?

[x] A. They stay after the stream, inside the same 120 s, as
`TEST_PLAN_PY.md` 0.2 has them. (Recommended: the goal adds to the run
before them and does not ask to move them.)

[ ] B. They leave `test_all.py` for commands of their own in
`test_posix.sh` and `powershell/test_powershell.ps1`, so `test_all.py` is
the Python TAP run alone.

[ ] C. The checks of `test_posix.py` become a block of the stream; the wire
and browser tests stay after it.

Question 14. Which side of `test_bail_between` (0.1 item 1) is wrong? A
bail out at depth 0 ends the stream; the test then has more lines follow.
The producer writes nothing after its own bail out.

[x] A. The consumer: it stops reading at a bail out and ignores what
follows, as the test expects and as TAP 14 asks a harness to stop at a bail
out.

[ ] B. The test: a line after a bail out is a fault, so a producer that
writes past its bail out is caught, and the test expects not well formed.

Question 15 (class A). How are the other two failing suites (0.1 items 2
and 3) fixed? Both are fixed before any new suite is written.

[x] A. `tests_refused` is renamed so the loader no longer collects it, and
`test_install_pinned` reads the archive from the setting
`powershell.ttyd_archive` of `settings.json` instead of the install script.

[ ] B. Otherwise, written in.
