# Demo Swarm

How a coordinator agent and a swarm of worker agents write the code that
FIRST_DEMO.md plans, on this machine, without running, building or testing
anything. FIRST_DEMO.md is the authority on what is built. This document says
only who writes which file, in what order, and how the writers keep out of
each other's way. Where the two disagree, FIRST_DEMO.md wins and the
disagreement is a discrepancy for the postmortem.

## 1. The coordinator's instructions

Give the coordinator this text, whole, as its task:

```text
You are the agent coordinator. Execute the plan: FIRST_DEMO.md, as
DEMO_SWARM.md directs. The project rules are in your context; read
FIRST_DEMO.md and DEMO_SWARM.md before anything else, and read nothing from
git history.

No testing is allowed between agent handoffs. Use a file renaming scheme
where task ids are appended to filenames for the duration of an edit, as
DEMO_SWARM.md section 3 specifies, so that no worker waits for another except
at one file. Don't run, build or test anything ever: no test run, no page
build, no tsc, no formatter, no linter, no git command, no program of the
project. Your one command is `date`, once, to name the engineering log. Just
be the best coordinator and then stop.

You edit no file of the project. Your writing is the engineering log in tmp/
and the prompts of the workers. Launch the tasks of DEMO_SWARM.md section 5
wave by wave: every task of a wave at once, as many as the harness lets you
run and the rest as slots free, each worker given the prompt of section 4
filled in from its row. Wait for every worker of a wave to report before you
launch the next wave. Add each report to the log as it comes, text added and
never changed. Never fill in a report yourself: a worker that has not reported
is still running, or lost. A worker the harness reports ended without a
report is lost: launch one replacement with the same id and the same prompt,
plus one sentence saying its predecessor was lost and may have left files
under that id's lock names, which the replacement treats as its own. A second
loss of the same task ends the swarm. When the last wave has reported, list the tree for
lock names left behind with your file listing tool, write the postmortem of
section 7, give it in the conversation with a link to the log, and stop.
```

## 2. What the swarm does and does not do

2.1. The swarm writes the API text, the unit tests, the code, the integration
tests, the golds, the seed, the templates and the rule lines for everything
FIRST_DEMO.md section 5 names, stages 5.0 to 5.6 and 5.8. Every task below names
the plan sections it implements, and the worker builds what those sections
say and nothing more.

2.2. The swarm runs nothing. No worker and not the coordinator runs a test, a
build, tsc, a formatter, a linter, a git command or any program of the
project. A worker's shell is for the renames of section 3 and for reading.
The "Proof" line of each stage of FIRST_DEMO.md section 5 is not run by the
swarm: the first run is the maintainer's, after the coordinator stops,
`./test_posix.sh` and then `./test_posix.sh --test-all`. Workers writing
against API text alone will leave failures for that run to find; those
failures are the next session's work, not the swarm's.

2.3. Stage 5.7, the viewing, is outside the swarm. It follows the first
passing run.

2.4. Nothing is staged or committed. No worker reads git history. No file is
reformatted. FIRST_DEMO.md and PROJECT_STATUS.md are not edited; a worker that
finds the plan wrong reports the discrepancy and builds what the plan says.

2.5. Every worker has the project rules in its context and follows them: no
fallbacks, no decorative comments, one line comments, two English names per
function, Python's import form, constants at the top, the
20 line file header, the scripted AI only, no mock objects, no state poked
from a test. The Accidental-Requirements section applies with force here,
since a worker sees the tree before it sees the plan: a decision found in the
code is checked against FIRST_DEMO.md before anything is built on it, and
reuse is chosen by the plan, never because something exists.

2.6. Section 6 names the clauses of the plan this document overrides, each
with its reason. They are the design flaws found before the swarm starts, and
no worker re-decides them.

## 3. The lock: a rename for the duration of an edit

3.1. A task's id is `T` and two digits, from the tables of section 5, as
`T08`. A lock on a file is that file renamed with the id appended after a
dot: `ts/queue.ts` locked by task T08 is `ts/queue.ts.T08`. No file of the
project ends in `.T` and two digits, so a lock name is never a real name.

3.2. To take a lock, rename the file to its lock name, one command, as
`mv ts/queue.ts ts/queue.ts.T08`. A rename is atomic on this filesystem and
fails when its source is absent, so the command either succeeds, and the
worker holds the file, or fails because another task holds it or it does not
exist. The lock name is unique to the task, so nothing is ever overwritten.
After a failure the worker lists `ts/queue.ts*`: a name ending in another
task's id means that task holds the file, and the worker tries again later;
no name at all means the file does not exist, which for a file the worker
does not own is a discrepancy to report.

3.3. To release a lock, rename the file back, as `mv ts/queue.ts.T08
ts/queue.ts`, the moment the edit of that file is done. The duration of a
lock is the duration of one edit, not of the task. A worker plans its edit
while the file is unlocked: it reads the file, decides the change, then
locks, reads the file again under its lock name, since another task may have
changed it since, applies the change and releases.

3.4. A worker holds one lock at a time and takes the next only after
releasing the last, so no two workers can wait on each other. An edit that
spans two files, as an API file and its module, is two edits, each locked in
turn; the window between them, in which the two disagree, costs nothing,
because nothing is built or run while the swarm works.

3.5. A worker that finds a file held tries again until it succeeds. Between
tries it does the other work of its task, and when none is left it waits a
few seconds between tries by whatever means its harness gives for waiting.

3.6. A file that does not exist yet is created under its lock name, as
`python/xsjs_log.py.T10`, and released by the rename to its real name when
its first version is written. Each new file is owned by exactly one task in
section 5, so no two tasks create the same path. Another task that needs the
file edits it as any other file once it appears, and reads it before then
only if it has appeared under a lock name.

3.7. Reading takes no lock. A worker reads a file at its real name or, when
that is absent, at the one lock name present, knowing the text is mid-edit.
The API files of wave 1 are stable throughout wave 2, since wave 2 starts
once wave 1 has reported.

3.8. A tool that edits a file reads it first; the worker reads the file under
its lock name, since that is the name the edit goes to.

3.9. While a lock is held, git sees the real name as deleted and the lock
name as untracked. That is harmless, since nothing is staged, and it is the
reason a lock is short.

3.10. A lock left behind is a lost worker. The coordinator never renames the
file back, since the text under the lock name is a half edit. The replacement
worker of section 1, which has the same id, finds those lock names as its
own, reads the text under them, and finishes or releases each. A lock still
there at the end goes to the postmortem with the choices, as section 7 says.

3.11. The project rules file is the one file no wave 2 task locks: it reaches
every agent's context through a link read at the agent's start, so a worker
that starts while it is renamed starts without the project rules. The one
task that edits it, T38, runs alone in wave 3, when no worker is starting.

## 4. The worker's prompt

The coordinator fills this in from the task's row in section 5 and gives it
to the worker whole. TASK_ID is the id; TASK_TEXT is the row's "Writes"
cell; SECTIONS its plan sections; FILES_OWNED its "Creates" cell, or "none";
FILES_SHARED its "Edits, shared" cell, or "none".

```text
You are worker TASK_ID of the demo swarm. The project rules are in your
context; read FIRST_DEMO.md and DEMO_SWARM.md first, and read nothing from
git history. Your task is DEMO_SWARM.md section 5, task TASK_ID: TASK_TEXT.
It implements FIRST_DEMO.md sections SECTIONS, which are the authority on
what you build. Build what they say and nothing more.

You write; you run nothing: no test, no build, no tsc, no formatter, no
linter, no git command, no program of the project. Your shell is for the
renames of DEMO_SWARM.md section 3 and for reading. Every file you edit is
locked first by that renaming, one file at a time, read again under its lock
name, and released the moment the edit is done. Files you create, under their
lock names first: FILES_OWNED. Files you may edit, which other tasks may edit
too: FILES_SHARED. Any other file you have to edit is a discrepancy: edit it
under lock and report it. Never edit the project rules file, FIRST_DEMO.md
or PROJECT_STATUS.md; the rule lines its agent-maintained sections need go in
your report.

Write in the order of the stage: the API text, then the unit tests, then the
code, then the integration tests. A string an error needs goes in
i18n/en-US.json under lock, named in the API text. A sentence the 20 line
header limit pushes out of an API file is never cut: put it in your report
for the rule sections. Decide what the plan leaves open, and report each
decision in one line so that it can be overturned cheaply. Ask nothing: when
you cannot decide, do everything else and report the item unfinished with the
choices as a lettered multiple choice list, A first and recommended.

When you are done, make sure no lock of yours is left, then report: every
file created or changed; every decision; every discrepancy between the plan,
the API text and the tree; every sentence pushed out of an API header; every
rule line of the project rules' agent-maintained sections your work makes
wrong or missing, with its replacement, one rule per line starting with its
subject; what is unfinished and why. Then stop.
```

## 5. The tasks

5.1. Three waves. Wave 1 writes the API text, since the project rules put the
prose before the code and every later worker reads it. Wave 2 writes every
test and every module at once; its tasks share files only through the lock,
so their order within the wave does not matter. Wave 3 is the one task that
edits the project rules file. The coordinator launches a wave once every
task of the wave before has reported, a lost task's replacement included.

5.2. A task's "Creates" files are its own: no other task creates them. Its
"Edits, shared" files may be edited by other tasks, each under lock. A gold
is the `test_setting_<suite>.json` beside a suite; a new suite gets one when
it needs values of its own. No task of wave 2 edits a file another task of
wave 2 creates, so no worker waits for another's whole task; a wave 2 task
that needs such a file reads it, or the API text it implements.

5.3. The `files` list of `ts/tsconfig.test.json` is the load order of the
bundle, so a file goes after every module it uses and before every test of
it; a worker that adds a file places it by that rule under lock. A row added
to a list of `python/test_all.py` goes in its layer: after the suites of every
module it calls into, as the driver's own header says.

### 5.4. Wave 1: the API text, stage 5.0

| Task | Writes | Plan sections | Creates | Edits, shared |
|---|---|---|---|---|
| T01 | The wire line `db.sync` and its reply `DbSyncReply`, and `provider.set` written as deferred and not built | 4.1.2, 4.10.1, 5.0 | none | `API/ts/lines.d.ts`, `i18n/en-US.json` |
| T02 | `dispatch.Stream`, the twin of `Failure`; the sync handler among the database handlers; the main loop writing a stream and logging its dispatch and reply lines in full | 4.1.4, 4.5.2, 5.0 | none | `API/python/dispatch.pyi`, `API/python/engine_db.pyi`, `API/python/main_loop.pyi`, `i18n/en-US.json` |
| T03 | The worker's `tap_start` running its function in every mode; the boot's engine worker, `WorkerStart` in place of `TestStart`, the sentence that no program but the suites runs gone; the page's `engine_page` | 4.2.3, 4.3.2, 5.0 | none | `API/ts/worker_ai.d.ts`, `API/ts/boot.d.ts`, `API/ts/page.d.ts`, `i18n/en-US.json` |
| T04 | The `engine` module: the worker's program, the UI thread's program, the engine page's entry, and the pieces of the chain as functions of their own | 4.2.1, 4.2.2, 4.3.2, 5.0 | `API/ts/engine.d.ts` | `i18n/en-US.json` |
| T05 | The queue's timeline lines carrying the full rendering in debug mode, the sized form past `line_max` | 4.5.2, 7.1, 5.0 | none | `API/ts/queue.d.ts`, `i18n/en-US.json` |
| T06 | The public functions of the serve program and of the log program, `lines_read` among them | 4.5.4, 4.6, 5.0 | `API/python/xsjs_serve.pyi`, `API/python/xsjs_log.pyi` | `i18n/en-US.json` |
| T07 | The seed table of the analyst: nodes `start` and `menu`, inputs 1, 2, 3 and 0, the tool calls of the table and the texts in her voice, written now because the C block's and the demo test's golds of wave 2 pin those texts; the coherence test beside the server's seeding tests | 4.4, 5.3 | none | `python/seed/provider_script.json`, `python/test_main_loop.py`, `python/test_setting_test_main_loop.json` |

### 5.5. Wave 2: the tests and the code, stages 5.1 to 5.6 and 5.8

| Task | Writes | Plan sections | Creates | Edits, shared |
|---|---|---|---|---|
| T08 | The queue's timeline lines in full, with its unit and integration blocks and their golds | 4.5.2, 5.1 | none | `ts/queue.ts`, `ts/test_queue.ts`, `ts/test_integrate_queue.ts`, `ts/test_setting_test_queue.json`, `ts/test_setting_test_integrate_queue.json`, `i18n/en-US.json` |
| T09 | The main loop: its dispatch and reply lines in full, and a handler's `Stream` written as its pushes then its reply; unit and integration suites | 4.1.4, 4.5.2, 5.1, 5.2 | none | `python/main_loop.py`, `python/test_main_loop.py`, `python/test_integrate_main_loop.py`, `python/test_setting_test_main_loop.json`, `python/test_setting_test_integrate_main_loop.json`, `i18n/en-US.json` |
| T10 | The log program: the timeline printed from `_verbose.sqlite`, filters, follow mode, `lines_read`; a unit suite that writes a log through the server's own log functions and reads it back; an integration suite that runs the program; both suites in the driver's lists in their layers | 4.5.3, 4.5.4, 5.1 | `python/xsjs_log.py`, `python/test_xsjs_log.py`, `python/test_integrate_xsjs_log.py`, their golds | `python/test_all.py`, `i18n/en-US.json` |
| T11 | `dispatch.Stream` with its unit suite | 4.1.4, 5.2 | none | `python/dispatch.py`, `python/test_dispatch.py`, `python/test_setting_test_dispatch.json`, `i18n/en-US.json` |
| T12 | The handler of `db.sync`: every database but `_verbose`, in name order, as restore lines from the store's snapshots, then the reply naming them; unit and integration suites | 4.1.2, 4.1.4, 4.1.5, 5.2 | none | `python/engine_db.py`, `python/test_engine_db.py`, `python/test_integrate_engine_db.py`, `python/test_setting_test_engine_db.json`, `python/test_setting_test_integrate_engine_db.json`, `i18n/en-US.json` |
| T13 | The wire rung `sync` on the stock root: `db.sync` submitted, the restore and file lines of the four seeded databases expected in name order, then the reply naming them | 4.1.6, 5.2 | none | `ts/test_wire_rungs.ts`, `python/test_setting_test_wire.json`, `python/test_wire.py` |
| T14 | The bring up's two changes: `tap_start` runs its function in every mode at once after the Empty reply; the engine worker's bring up on its own pool, directory and cache; `WorkerStart`; the two test pages' entries notify `worker.tests` to themselves in debug mode; the worker's and the boot's unit blocks and golds | 4.2.3, 5.3 | none | `ts/worker_ai.ts`, `ts/boot.ts`, `ts/test_worker_ai.ts`, `ts/test_boot.ts`, `ts/test_setting_test_worker_ai.json`, `ts/test_all.ts`, `ts/test_headless.ts`, `i18n/en-US.json` |
| T16 | The `engine` module whole: the worker's program, with the store, the tools and the two clients, the scripted port built at the sync's reply with the key `scripted`, and the chain of wakes to the first render; the UI thread's program, building the DOM port, the media port, the console view, the overlays and the UI handlers from the document; the engine page's entry, picking by the thread's name; its group B unit block on fresh workers of the headless page, listed in the block table, the tsc config and the driver's B unit list | 4.1.6, 4.2, 4.3.2, 5.3, 5.4 | `ts/engine.ts`, `ts/test_engine.ts`, `ts/test_setting_test_engine.json` | `ts/test_headless.ts`, `ts/tsconfig.test.json`, `python/test_all.py`, `i18n/en-US.json` |
| T17 | The engine's group C integration block against the real ttyd and server: the first render's line holding the seed's remark, `ai.say` of 1 ending in the seed table's text, the `mcp` lines and commits seen on the wire, the console tool's permit answered accept reaching dash; listed in the block table, the tsc config and the driver's C list | 4.7.5, 5.3 | `ts/test_integrate_engine.ts`, `ts/test_setting_test_integrate_engine.json` | `ts/test_headless.ts`, `ts/tsconfig.test.json`, `python/test_all.py` |
| T18 | The page's `engine_page`, which runs the UI thread's program at `settings.set`; the group B unit block on the UI side, written against the engine module's API text: a render paints black with the subtitle and opens the box, a typed number becomes `ai.say`, a permit request shows the buttons and a click answers it; listed in the block table, the tsc config and the driver's B unit list | 4.3.2, 4.3.3, 5.4 | `ts/test_engine_page.ts`, `ts/test_setting_test_engine_page.json` | `ts/page.ts`, `ts/test_page.ts`, `ts/test_headless.ts`, `ts/tsconfig.test.json`, `python/test_all.py`, `i18n/en-US.json` |
| T19 | The engine template, built as `hyperposition-engine` from `engine`: the debug views, the hidden canvas, the band with the subtitle and the disabled box, the permit area, the test page's scripts with the engine's entry last and no TAP element; the style sheet's one rule that keeps the box visible; the page builder's suite extended | 4.3.1, 5.4, decision 16 | `html/engine.html` | `html/engine.css`, `python/page_build.py`, `python/test_page_build.py`, `python/test_integrate_page_build.py` |
| T20 | The serve program: the root made as the start script makes one, kept between runs, `--fresh`, the built ttyd with the start script's options on 127.0.0.1 port 5769, the address printed, SIGINT and SIGTERM ending ttyd's group; a unit suite of the root making and options; an integration suite that serves on port 0, fetches ttyd's token and stops it; both in the driver's lists | 4.6, 5.5 | `python/xsjs_serve.py`, `python/test_xsjs_serve.py`, `python/test_integrate_xsjs_serve.py`, their golds | `python/test_all.py`, `i18n/en-US.json` |
| T21 | The demo test over DevTools: the rungs of 4.7.2 with their labels, pictures to `build/test_demo/`, roots kept on failure, `--hold`, its gold, as a smoke-test check of the driver after the browser test | 4.7, 5.6 | `python/test_demo.py`, `python/test_setting_test_demo.json` | `python/test_all.py` |
| T22 | The line count gate's driver fix: the mapping row that makes the store limit's suite count for the store module, with its test where the driver's mapping is tested. The switch that passes `--coverage` from `./test_posix.sh --test-all` is not written by the swarm, as section 6 says | 4.9.1, 5.8 | none | `python/test_all.py` |

The fifteen gap tasks, stage 5.8 and plan section 4.9.2. Each takes the first
line never counted from the table of 4.9.2, measured at an earlier commit, so
the worker reads the module around that line and finds the statement, reads
the module's unit suite, and decides the gap's kind. Untested code gets a
test through the module's API. Code whose normal path is a started program,
as the engine's bootstrap under ttyd, gets a test that forks and runs the
function in the child, since the counter counts a forked child's lines of the
suite's files; nothing is exempted, and the counter's mark stays where its
API puts it, on a line that raises "internal error" alone. Dead code goes. A
statement that none of these closes is reported unfinished with the choices.
The named gap first, then every other statement of the module the
worker finds no test reaching, since the count stops at the first gap and no
count runs here. Each task edits its module, its unit suite and the suite's
gold, all shared, under lock.

| Task | Module | First line never counted | Unit suite |
|---|---|---|---|
| T23 | `python/bootstrap.py` | 308 | `python/test_bootstrap.py` |
| T24 | `python/devtools.py` | 359 | `python/test_devtools.py` |
| T25 | `python/engine_system.py` | 139 | `python/test_engine_system.py` |
| T26 | `python/internationalization.py` | 27 | `python/test_internationalization.py` |
| T27 | `python/main_loop.py` | 190 | `python/test_main_loop.py` |
| T28 | `python/mcp.py` | 195 | `python/test_mcp.py` |
| T29 | `python/mcp_stdio.py` | 93 | `python/test_mcp_stdio.py` |
| T30 | `python/page_build.py` | 116 | `python/test_page_build.py` |
| T31 | `python/reformat.py` | 135 | `python/test_reformat.py` |
| T32 | `python/substrate.py` | 207 | `python/test_substrate.py` |
| T33 | `python/tap_loop.py` | 150 | `python/test_tap_loop.py` |
| T34 | `python/tap_producer.py` | 266 | `python/test_tap_producer.py` |
| T35 | `python/test_posix.py` | 157 | `python/test_test_posix.py` |
| T36 | `python/third_party_fetch.py` | 132 | `python/test_third_party_fetch.py` |
| T37 | `python/vectors_make.py` | 166 | `python/test_vectors_make.py` |

### 5.6. Wave 3: the rule sections

| Task | Writes | Plan sections | Creates | Edits, shared |
|---|---|---|---|---|
| T38 | The agent-maintained rule sections of the project rules file, after its Map heading, from every line the wave 1 and 2 reports gave: the Line types table gains `db.sync` and its reply and the engine's wakes; the Bring up section loses the rule that no program but the suites runs and gains the engine's chain; the Map, Files, page_build, test_all and Rungs sections gain the engine template, the serve, log and demo programs, the count in the full run and the sync rung; and every sentence a header limit pushed out of an API file, one rule per line starting with its subject. The Project Rules are not touched | 4.1 to 4.9 as reported | none | the project rules file |

The coordinator gives T38 the reports' lines verbatim in its prompt, in place
of a row's "Writes" cell, since T38 has no other source for them.

## 6. Names and choices this document fixes, each cheap to overturn

1. A task id is `T` and two digits, the lock suffix a dot and the id.
2. A worker holds one lock at a time.
3. Three waves: the API text and the seed, then every test and module, then
   the project rules file.
4. The engine's blocks are `test_engine.ts`, the worker's B unit block;
   `test_integrate_engine.ts`, the C block; and `test_engine_page.ts`, the
   UI side's B unit block, each with its gold, since the plan names the blocks
   by their group and side only.
5. The serve and log programs get stub files in `API/python`, since stage 5.0
   puts their public functions in the API.
6. The seed's coherence test lives in the main loop's unit suite, beside the
   seeding tests, as 4.4.3 says.
7. The two main loop items of stages 5.1 and 5.2 are one task.
8. The strings go in with the API task that names their errors; no separate
   strings task.
9. Plan clause 4.9.2 overridden: no gap is closed with the counter's
   exemption mark. The counter already counts a forked child's lines of the
   suite's files, so code that a started program runs is tested by a forking
   test, and the mark stays on "internal error" lines alone, as the counter's
   API says. A mark with a reason beside it would make the gate a tally of
   excuses, which the no fallbacks rule forbids. The counter's API text is
   therefore not changed, and no task of wave 1 touches it.
10. The seed table is written in wave 1, as T07, since the golds of the C
    block and of the demo test pin its texts: three workers writing the
    analyst's texts at once would write three different ones.
11. `ts/engine.ts` has one owner, T16, which writes the whole module from its
    API text: a file created in wave 2 cannot be edited by another wave 2
    task without a wait that serializes the two. T18 writes `engine_page` and
    the UI side's block against that API text alone.
12. Plan clause 4.9.3 ordered by its own word "then": the switch that passes
    `--coverage` from the full run lands once a count passes, which the swarm
    cannot see. Until then the full run would stop at the first gap reading
    missed, before the demo's test-all rungs, which the demo cannot afford.
    The maintainer runs the count as section 7 says; the switch is one line
    of `test_posix.sh`.
13. A lost worker is relaunched once with the same id, so its lock names are
    its own again; a second loss ends the swarm.
14. A gap task closes the named gap and what reading finds.
15. The first test run is the maintainer's, after the swarm.

## 7. The postmortem the coordinator writes

The last section of the coordinator's log, and the text it gives in the
conversation with a link to the log, holds:

1. Each task by id with one sentence of what it is, and whether it reported
   done, reported unfinished, or never reported. A worker that never reported
   is a lost subagent and is listed as one.
2. Every lock name found in the tree at the end, with the task that holds it.
   For each, a question in the maintainer's terms with the choices lettered,
   A first: a new worker finishes the task from the text under the lock name;
   or the file is renamed back as it is; or the text under the lock name is
   discarded and the file restored from the tree's last version.
3. Every decision the workers reported, one line each.
4. Every discrepancy the workers reported between the plan, the API text and
   the tree.
5. Every item a worker reported unfinished, with its multiple choice.
6. The next step: `./test_posix.sh`, then `./test_posix.sh --test-all`, run
   by the maintainer, and what to expect: failures the swarm could not see,
   the first of them likely a type error of the bundle, since one stops every
   page block. Once the full run passes, `python3 python/test_all.py
   --test-all --coverage`, which stops at the first gap reading missed, if
   any; and when that passes, the one line of `test_posix.sh` that passes
   `--coverage` with `--test-all`, which ends stage 5.8.
