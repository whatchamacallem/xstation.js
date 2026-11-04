# The schedule of task 13

This document schedules the work that the maintainer's message of
2026-11-04, task 13 of `tmp/tasks_30_2127.md`, asks for, and every other
item of `TEST_PLAN_TS.md` that is unblocked and needs finishing. The
message:

> add to the plan to remove messages that are not required that you are
> reading that contain information that an ai would already know and are
> not part of the TAP protocol. no human will see these messages, and it
> cost electricity to have ai read them all day long for no reason. next ad
> a task to the plan to enhance the tap producers/consumers to emit and
> consume yaml information. [...] write a new planning document scheduling
> all of the above as accepted and resolved in favor of your judgement,
> including the follow up options too. please just keep scheduling everying
> that is unblocked, part of the plan and needs finishing. i need all
> thests passing, don't stop. use all the agents you want if it will make
> this go faster

The designs are in `TEST_PLAN_TS.md`, written before any code; this
document holds only their schedule. Every item below is accepted by the
message, each choice in it resolved in the agent's judgement
(`TEST_PLAN_TS.md` 11.3 item 41).

## 1 Scheduled

1. Wave 1, in parallel, each task on the files it owns:
   1. `TEST_PLAN_TS.md` 3.30, a YAML block of `duration_ms` after every
      point of both producers, the consumer taking that block alone by a
      hardcoded grammar. The lead's task. Owns `python/tap_consumer.py`,
      `python/tap_producer.py`, `ts/tap_producer.ts`, `ts/line_case.ts`,
      the TypeScript callers of `Tracker` (`ts/test_wire_end.ts`,
      `ts/test_wire_rungs.ts`, `ts/test_tap_pair.ts`,
      `ts/test_line_case.ts`), `python/test_all.py`'s relays,
      `python/test_browser.py`'s `tap_failure`, their stubs, their suites
      and the golds that hold TAP lines. Done in a private copy of the
      tree under `build/`, so that no other task's run meets a half made
      protocol, and copied back whole.
   2. `TEST_PLAN_TS.md` 7.4 item 8, dash's controlling tty, the first
      follow up option of task 12's postmortem. An agent's task, in the
      main tree. Owns `python/bootstrap.py`'s argv and console role, its
      stub, the gold copies of the argv and the suites of the console's
      shell; remakes 7.4 item 5's measurements.
   3. `TEST_PLAN_TS.md` 7.9.2, C's layer table by the TypeScript compiler
      API, the second follow up option. An agent's task, which reads the
      tree and writes the table into 7.9.2 alone; a change of
      `_C_INTEGRATION`'s order it finds is the lead's to make.
2. Wave 2, after wave 1's item 1: `TEST_PLAN_TS.md` 3.29, the run's output
   cut to TAP and what a failure needs, the rest under `--verbose`. The
   lead's task, since it removes the seconds lines that 3.30 replaces.
   Owns `python/reformat_table.json`, `python/test_posix.py`,
   `python/test_all.py`'s output lines, the narration and log copies of
   `python/test_wire.py` and `python/test_browser.py`, and the HTTP
   handlers of the suites, with their golds.
3. Wave 3, after waves 1 and 2, the lead alone:
   1. The work copy's changes copied into the main tree, file by file,
      against the agents' changes there.
   2. The whole runs of 7.9.2: `./test_posix.sh --smoke-test --anthropic`
      within the gold's `smoke_seconds`, 180 s since 3.21, which 7.9.2's
      "within 120 s" now means; `./test_posix.sh --normal-test
      --anthropic`; and `python3 python/test_all.py --anthropic --tty
      --stream`. 7.9.2's moves of labels by measured seconds follow 7.2
      item 4: only a smoke run past the deadline moves a label.
   3. 7.9.3's checks: `python/reformat.py` twice with every change staged,
      then unstaged; both tsconfigs; ruff and pyright strict over
      `python/`; nothing staged, no lock left, `tmp/run_lock` in place, no
      file of the tree owned by root, and nothing a run left under
      `build/`.
4. The postmortem of task 13, once no agent runs.

## 2 Not scheduled, with the cause

1. `TEST_PLAN_TS.md` 7.10 item 1, the wire test and the browser test as
   blocks of the stream: 7.2 item 1's cause stands, and by 3.29 both write
   nothing on a pass, their seconds under `--verbose`.
2. 7.10 item 2, the paths no part of the plan reaches: blocked by the
   product, not by the plan. No code of the server sends `db.restore` or
   `db.file` (7.1 item 6), and the page's display of its worker's load
   error and `error_overlay`'s append while the parser runs a script were
   reached only through the system doubles that 4.5 removed (7.6 item 5).
3. 7.10 item 3, 10.7's scripted console: its tests run on the real
   console through ttyd (7.2 item 7), so nothing needs it.
4. 5.5 item 6's `failed_tests`, ignored by the maintainer's answer that
   the designs not needed are ignored, and the Windows target with
   `test_devtools_powershell`, ignored by Question P1's answer.
5. 11.2 items 50 and 51 are decisions, which stand unless the maintainer
   overturns one; item 50's advisory goes by 3.29.

## 3 How the work runs

1. No commit, since the message asks for none.
2. Every run of `python/test_all.py` in the main tree holds `tmp/run_lock`
   (8.6); the work copy has a lock of its own. A shared file is edited
   only under its lock, renamed with the task's suffix (8.5).
3. The tree stays owned by `xsjs`, the user the runs are made as.

## 4 Requirements analysis

The requests of task 13's message, read with the engineering log's earlier
tasks, by the project's four classes.

1. Class A, unsatisfied or modified without cause: none.
2. Class B, unsatisfied or modified with cause but without confirmation:
   `TEST_PLAN_TS.md` 11.2 items 50 and 51, carried from tasks 10 and 11:
   the formatter decisions of 3.27 (the linters in both categories,
   `reformat.format_check` kept with no caller in an official run, the
   normal-test run still formatting, the Windows formatting left as it
   is) and `test_console_open`'s test end on the lane `server`, its copied
   builders and its fixed waits. This schedule satisfies both as built;
   nothing waits on a question.
3. Class C, modified by the message's acceptance of the agent's judgement:
   1. "remove messages that are not required": the lines holding nothing
      the reader lacks go, and the measurements and log copies that a
      failure may need are written only under `--verbose` rather than
      removed, so that 7.2 item 4 can still measure the programs' rungs
      (3.29 item 2).
   2. "have all producers emit duration_ms": every point of both
      producers, the parent points included; a relayed block's parent
      point carries the driver's measurement, the realm's own parent block
      read and dropped (3.30 item 2.3).
   3. "do not allow unrecognized yaml attributes": refused by the parser,
      which gives any other line at a YAML block's indent as `Unknown`
      (3.30 item 4).
   4. "keep scheduling everying that is unblocked": 7.10's three items and
      5.5 item 6 are not scheduled, each with its cause in section 2.
4. Class D, satisfied without modification: the new planning document, the
   two plan items, the follow up options, `TEST_PLAN_TS.md` 7.4 item 8 and
   7.9.2, scheduled, and the agents used for waves that can run apart. Each
   moves to done when its wave's runs pass, as the postmortem of task 13
   records.

## 5 Status

On 2026-11-04, at the end of task 13:

1. Wave 1 and wave 2: done, `TEST_PLAN_TS.md` 3.29 item 6, 3.30 item 8,
   7.4 item 8.7 and 7.9.2 item 3.
2. Wave 3: done, `TEST_PLAN_TS.md` 7.9.2 item 4; the smoke target passed
   119 of 119 in 126.2 s, the normal target 121 of 121 in 664.0 s and
   `--tty --stream` 119 of 119 in 113.6 s, each with nothing on stderr.
3. Section 2's items stay unscheduled, each for its cause.
