# CODE_REVIEW: the code against the plans

## 1 Scope and authority

1.1 Written on 2026-10-21 at the user's request kept in the session log
`tmp/tasks_21_1513.md`, task 1. This file is the plan of a coordinated review
of the code in this checkout against the code the planning documents call
for. A later coordinator session carries it out with its agents; the session
that wrote it only wrote it.

1.2 The review finds and fixes three kinds of thing (2.3):

1.2.1 U, an undocumented deviation: the code differs from what the planning
documents lead a reader to expect, and no record documents the difference.

1.2.2 M, a mistake: code that is simply incorrect, a test that cannot pass, a
seam whose two sides disagree, a breach of the project rules.

1.2.3 S, a shortcut: a short term substitute put where the plan's design was
within reach with more work.

1.3 The review does not revisit judgement calls. Every decision, reading,
assumption, default, approval and chosen option of the planning agents, the
coordinators and the maintainer, in the engineering logs or the two plans,
stands. Every assumption the AI made is accepted for the purpose of this
review (2.1); that acceptance does not change any item's class in
`PLAN_B.md`.

1.4 Sources and how they are cited:

1.4.1 `hyperposition-plan.md`, cited "P <section>".

1.4.2 `PLAN_B.md`, cited "B <section>".

1.4.3 The engineering logs, cited by the time in their name and a record:
"L1413" is `tmp/tasks_19_1413.md`, "L1827" `tmp/tasks_19_1827.md`, "L2016"
`tmp/tasks_19_2016.md`, "L2018" `tmp/tasks_19_2018.md`, "L1601"
`tmp/tasks_20_1601.md`. "L2016 3.100.4" is record 3.100.4 of
`tmp/tasks_19_2016.md`.

1.4.4 The stubs under `API/`, the project rules, which every agent has in
its context, and this file, cited "CR <section>".

1.5 Order of authority: the project rules, which are the maintainer's; then,
as B 0.3, the maintainer's words (B 1), B 2, P and `API/`. A log record is
the history of a decision: a later
record supersedes an earlier one, and the plans supersede the records they
carry forward. Where the plans are silent, the latest record that decides a
point is the decision.

1.6 Baseline. When this file was written HEAD was `7258e51` and
`git status --short` printed only `?? CODE_REVIEW.md`. The coordinator
records both again before the first launch (6.1.2); the commit it records
is the baseline, which every later mention of "the baseline" means and every
prompt carries (12.3). Every change of the review is made against the
baseline and left unstaged for the maintainer, but for the formatter's
staging (11.2).

1.7 Deleted documents. `tmp/PLANNING_UPDATE.md`, the briefs, handoffs,
handovers, review reports and API text files that the logs cite no longer
exist. What a record says about them is what is known; they are not
recovered from git, and no agent looks for them. A record's "brief 9.3",
"work order 4.15" or "handoff G1" is read through the record's own words and
the B section that carried it (B 3 holds the review's code rules).

1.8 Readers: the coordinator, every agent of the review, the maintainer.

## 2 What counts

2.1 Accepted, not a finding. An agent that meets one of these lists it with
its record (7.3.3) and changes nothing:

2.1.1 anything in P 10, built later by design, or P 11, decided against;

2.1.2 every decision, READING, Unconfirmed assumption and approved item of P
and B; the defaults D1 to D31 of B 4; the API additions and departures of B
5;

2.1.3 every log record that decides: a COORDINATOR DECISION, a work order's
prescription, a choice that names the alternatives it rejected, an option an
agent built and marked "(built)" or "as built", a class B or class C item,
and every answer of the maintainer (2.3.4 says how to tell a decision from a
record of a fix not made);

2.1.4 every "API ADDITION" and "API DEPARTURE" a log record names;

2.1.5 every value or behaviour a record marks Unconfirmed, recalled from
memory, not measured or unverified; checking those is the testing phase's;

2.1.6 the HOLD of D22 (B 4.18): `python/bootstrap.html`,
`python/xsjs_screenshot.py`, `python/xsjs_screenshot_wsl.py`, the README
lines on the old design, `xsjs_stop.ps1`'s comment and `xsjs_status.ps1`'s
`pgrep`.

2.2 Open, not decided by the review. A point a record leaves to the
maintainer as a question with options, none of them built, stays open: the
questions of B 6, those of B 10.4 that no answer and no "(built)" mark
closes, and the log questions with options, such as L1601 5.3.3 (the
formatter split the hooked line of `html/test_engine.html`, so
`test_template_hooked` fails). The agent lists each one it meets (7.3.10)
and chooses nothing.

2.2.1 Log markers: a DISAGREEMENT, BLOCKED or FOR THE MAINTAINER item with
options is open unless a later record or B closes it; one that disagrees
with the deleted `DATA/` directory was closed by its deletion (L1601 1.19).
A NEEDS item that needs a run, a measurement or the maintainer's hand is
owed (7.3.11). A class A item is a candidate unless the maintainer accepted
it, as "all A are fine" did for L1601 4.5 (L1601 1.20).

2.3 Finding classes.

2.3.1 U: the code differs from what P, B or an accepted log record states,
and the search of 2.5 finds no record of the difference.

2.3.2 M: the code is wrong whatever the records say: it raises where it must
not, cannot pass, contradicts its own comment or stub, breaks a seam, or
breaks a project rule or a B 3 rule. A record that names a defect and leaves
it unfixed, outside a question with options, does not make it accepted:
L1601 5.9 and L2016 3.100 to 3.106 hold such records (CR 8 lists them by
area).

2.3.3 S: the code or a record shows a substitute taken for effort, time or
the earlier jobs' ban on running anything, and not chosen between designs.
Its marks are words such as "not built", "left", "stand in", "copied",
"duplicated", "kept from", "by hand", "no ... yet", or a gap that asks no
question. It is in scope only where the plan's design is reachable under CR
3 and CR 4.

2.3.4 Decision or candidate. A record decides when it presents the code's
form as chosen: "rejected:", "chose", a COORDINATOR DECISION, "(built)",
"as built", "approved", a class B or C item, or a reason of design for the
form. A record that presents something as missing, untested, left, kept,
not built, unreachable or wrong is a candidate, even when it names the fix
as an "alternative".

2.3.5 Precedence: a record of 2.1 wins. Where such a record breaks a project
rule or a B 3 rule, the point is open (7.3.10), not a finding. Otherwise a
point is M where a rule, a seam or a plan proof breaks, U where no record
exists, and S where a record shows a substitute.

2.4 Severity, fixed in this order:

2.4.1 1, blocking: the system, a runner or a test cannot work as the plan
says: a test that can never pass, a check that stops every run, a seam that
throws, a name used at run time with no entry.

2.4.2 2, defect: wrong behaviour on some input or path.

2.4.3 3, rule: a project rule or a B 3 rule broken with no change of
behaviour.

2.4.4 4, completeness: a proof, test, rung or part the plan names is
missing.

2.5 The search before a U or S finding:

2.5.1 the P section of the module, and P 10 and P 11;

2.5.2 the B sections that name the module or topic, and B 4, B 5 and B 6;

2.5.3 a `grep -n` of the five logs for the file stem, the symbol, the i18n
names and the line types involved, and a read of each record found;

2.5.4 the agent's entry in CR 8 or CR 9, which lists the main accepted items
and the candidates the logs left;

2.5.5 then the finding, with the records searched and why none decides it;
or the item listed as accepted, with the record that decides it.

2.6 Out of scope: `archive.sh` and `clean.sh` (P 7.5); the empty
`python/vectors/`, left for the maintainer (L1601 4.2.3.3); the logs and
every file under `tmp/` but the review's own; values that need a run or a
measurement, which are owed to the testing phase (7.3.11); the project
rules file and its symlink.

## 3 Rules for fixes

3.1 A fix moves the code to what the cited text states, by the smallest
change that meets it. Nothing is added that no requirement motivates (P
1.5): no refactor, no rename for taste, no new module or file that P or B
does not name, no reuse chosen because some code exists. The project rules
ban polish, decorative comments, extra logging, colour, borders and
redesign; a fix makes none of them.

3.2 Public interfaces. A fix that would add, remove or change a public name
or signature that `API/` declares, or that would need a declaration there,
is not made: P 1.1 puts the API before the code, and B 0.3 keeps `API/` the
maintainer's. The agent writes the whole design instead, the stub text and
every code change it would bring, as a proposed edit (7.3.9), so that
nothing reasoned out is lost. Private names, test only exports (D25) and
internal line types already recorded (B 5.17, L2016 3.79) may change. Moving
code to the name or signature its stub already declares is a fix, not an
interface change; when code in another area relies on the code's present
form, it is a seam change (5.6.7).

3.3 B 3.1 to B 3.8 bind every fix; B 3.9, the earlier jobs' working rules,
gives way to CR 4 and CR 5 (14.3.3). Handlers return finished reply lines
built with
`reply_make`; `Store.kv_put` takes bytes; a test that expects an error
compares the `i18n` text; fixtures read thread bound globals in `setUp`; two
English words in every function and class name, private ones included; one
comment line per construct; `cast` in place of a branch that only narrows a
type; `i18n` called with a literal name; `bootstrap.py` owns `hello`; the
error rules of B 3.6; every message of an engine module through `i18n`.

3.4 Tests move with behaviour: a fix that changes what code does changes or
adds its unit test first, in the same area. No test leaves state that
another test sees (P 8.1).

3.5 Strings. A new, reworded or removed `i18n` name goes into the agent's
fragment (7.6), never into `i18n/en-US.json`. An agent writes only names
whose module prefix belongs to its own files; another module's name is a
request (5.6). A prefix used in both languages is written by the owner of
its Python module: `substrate.` by task 1.14; `mcp.`, `dispatch.` and
`verbose.` by task 1.13; `jslb.` by task 1.12. The TypeScript owner sends
that owner a request.

3.6 Names given by the maintainer, by P, by B or by `API/` stay, though they
break the two word rule: `verbose.exec` and `verbose.log` (P 7.1), each
runner's `main` (B 2.18.7), `reformat.reformat` (B 2.21), `idle()` (B 5.12),
`rung_blob_max` (B 2.13.9), `test_test` (B 2.22).

3.7 Values. A timer or size is a named constant whose one line comment says
its writer chose it (P 4.7, B 2.6). A fix never puts in a value that a
measurement should give; such a value is owed to the testing phase.

3.8 Errors fail loud: no swallowed error, no default, no retry, no branch
for a case that cannot happen; the first failure only; nothing tallies
failures.

3.9 Python imports stand on the fewest lines, in alphabetical order; `from`
is used only for `collections.abc`, `typing` and `from i18n import i18n` (P
7.1); constants are `_UPPER_NAME` at the top, after the imports. TypeScript
has one frozen `constants` object per module (P 7.1).

3.10 No agent edits: the project rules file and its symlink, P, B, `API/`,
`README.md`, the D22 files (2.1.6), the logs, `archive.sh`, `clean.sh`.
Proposed edits to P, B and `API/` go in the report (7.3.9).

3.11 Formatting belongs to the formatter run (11.2), by the project rules.
An agent does not reformat code beyond its own edit, and writes its own new
text within 79 columns. Existing comments and strings over 79 columns that
the formatter cannot wrap are listed as open (7.3.10), not wrapped by hand
(L2016 3.97, 3.106.21).

3.12 A finding that cannot be fixed under CR 3 and CR 4 is recorded with
what blocks it and the design that would fix it.

## 4 What is run

4.1 Nothing of the project is run: no test, runner, build, `tsc`, type
checker, linter, ttyd, browser or script of the checkout, by any agent or by
the coordinator. The one run is the formatter of 11.2, because the project
rules make the formatting tools the only way to format. Why: the testing
phase is the maintainer's to start (B 8.5), every earlier job stopped before
it, `tsc` is not installed (P 0.4), and the runners need a built ttyd and
Windows Chrome. Verification is by reading. A verification run is designed
in CR 13.1 and not built; the maintainer turns it on by asking for it when
the review is launched.

4.2 An agent may use: Read, Write and Edit; `ls`, `grep`, `wc`, `test`,
`cmp`, `diff`, and `find` outside `.git`; `git status` and `git diff` against
the baseline; `mv` and `mkdir -p` for locks and under `tmp/review/`. Agents
are launched as the general purpose type, which has these tools.

4.3 An agent may not: change git's index or history, the formatter's staging
of 11.2 excepted; run `git log`, `git show` or read any past commit; use a
package manager or install anything; use the network; delete a tracked
file, which it proposes instead; write a source file by shell redirection,
`sed -i` or `tee`, since every edit goes through Edit or Write on a lock
name; read a session transcript (L1601 3.29 lost an agent to a refusal
doing so); ask the user, since questions go in the report.

4.4 Each report counts its commands by name and names every departure from
4.2 and 4.3.

## 5 Locks, ownership and requests

5.1 Ownership. Every file an agent may edit has exactly one owner task,
listed in CR 8; a new file belongs to the task that creates it; task 1.40
writes `i18n/en-US.json` and the summaries of 11.1, and task 1.41 lets the
formatter rewrite whitelisted files, the two tasks that write files they do
not own. Only the owner edits a file; anybody reads anything. A file no
entry lists is the coordinator's: requests for it go to
`tmp/review/inbox/coordinator/`, and in Phase 2 the coordinator gives each
one to a task by an `mv` of the request into that task's inbox, recorded in
its log.

5.2 The lock. The owner of `F` renames it `F.T<task id>` with `mv`, edits it
under that name, and renames it back. The rename is atomic: when it fails,
someone holds the file, and the agent does not wait (5.5). An agent holds at
most one source file's lock at a time, for one run of edits, and releases it
before it takes the next, so no reader meets a source lock for long; beside
it, it may hold the locks of its own report, its fragment and the requests
it has claimed. No agent ever waits on a lock, so no deadlock can arise.

5.3 A new file, the review's own under `tmp/review/` included, is written as
`F.T<task id>` and renamed `F` when complete. A report stays under its lock
name until the agent publishes it (7.2.8).

5.4 Reading never waits. A reader that does not find `F` reads `F.T*` as it
stands, knowing it may be mid edit. A `grep` hit on a lock name is a hit on
`F`. A glob or a name filter, such as `ts/*.ts`, `--include=*.py` or `find
-name`, does not match a lock name: a check that lists files by pattern
also lists each `F.T*` as `F`, and looks for a file missing under `F` as
`F.T*` before it files anything.

5.5 A lock held by another task on a file the agent owns is a stray lock:
the agent records it, names it in its reply, and goes on with other work. No
agent takes, edits or removes another task's lock.

5.6 Requests. An agent that needs a change in a file it does not own:

5.6.1 writes a request file `tmp/review/inbox/<owner>/<own>_<n>.md`, where
`<owner>` and `<own>` are task ids and `n` is one more than the highest `n`
of `<own>_<n>` under `tmp/review/inbox/*/` and `tmp/review/done/*/`, in the
form of 7.5, made under its lock name and renamed when complete;

5.6.2 sends it as soon as the finding is made, and does not wait: it records
the request as pending in its report and goes on;

5.6.3 sends one request per finding, or one per owner for a batch of hits of
one rule.

The owner, after its own fixes and again before it ends:

5.6.4 claims each request with `mv tmp/review/inbox/<owner>/<s>_<n>.md
tmp/review/inbox/<owner>/<s>_<n>.md.T<owner>`;

5.6.5 applies it, declines it with the record or rule that decides the
point, or forwards it to the right owner as a new request whose
`Forwarded from:` line names it;

5.6.6 appends its resolution line and, after `test ! -e
tmp/review/done/<owner>/<s>_<n>.md`, moves it with `mv
tmp/review/inbox/<owner>/<s>_<n>.md.T<owner>
tmp/review/done/<owner>/<s>_<n>.md`, its lock suffix dropped.

A request that arrives after its owner ended is worked in Phase 2 (6.3).

5.6.7 Seams. A change that two owners must make together starts on the
receiving side. The sender changes nothing on its own side and sends its
request with `Seam: pending`. The owner that applies it writes a request
back for the sender's side, `Seam: <s>_<n> applied`, which the sender works
in its pass or in Phase 2. A declined seam request leaves both sides as they
were. Nobody waits for the other side.

5.7 Shared files and their stewards:

5.7.1 `i18n/en-US.json`: only the closing agent writes it, from the
fragments (11.1).

5.7.2 `python/reformat_whitelist.txt` and `python/reformat_table.json`: task
1.10. A new source file reaches the whitelist by request when it is created.

5.7.3 `ts/tsconfig.json` and `ts/tsconfig.test.json`: task 1.18.

5.7.4 `python/test_all.py` and its `_MODULES`: task 1.9.

5.7.5 `ts/test_all.ts` and its module tables: task 1.20.

5.7.6 `settings.json` and `provider.json`: task 1.13.

5.7.7 `python/test_browser.py`: task 1.19; tasks 1.5 to 1.7 send requests.

5.7.8 `ts/test_substrate.ts`: task 1.24; task 1.8 sends requests.

5.8 Waits. An agent waits only for finished work it needs:

5.8.1 a verifier (CR 10) is launched when the first area of its group has
ended with an empty inbox, and is resumed by SendMessage as each later area
of the group ends so;

5.8.2 the closing agent starts after every writer and verifier has ended;

5.8.3 the formatter starts after the closing agent;

5.8.4 the postmortem follows the formatter.

Nothing else waits on another agent: an owner starts without the reviewers
that write to it, a reviewer without the owners it writes to, and a
request's sender never waits for its answer. The pool of 6.2 limits how many
agents run at once; that is the coordinator's guard against HTTP 429, not a
wait of one agent on another (14.3.5).

5.9 Lost agents. An agent stopped by a limit, a refusal or the user is
logged at once with the locks it holds, which stay its task's. It is resumed
by SendMessage after the reset. No two agents run under one task id: the
coordinator replaces an agent only after its stop is confirmed, by its
notification or by TaskStop. The replacement, a fresh agent with the same
task id and prompt, first renames each of its task's locks back after
reading `git diff <baseline> -- F` and the predecessor's report, which may
stand at `tmp/review/report/<id>.md.T<id>`, and completes or reverts each
half made change; then it starts 7.2. No other task takes those locks.

## 6 Phases

6.1 Phase 0, the coordinator alone:

6.1.1 opens its log under the project rules, task 1 the user's literal text,
the tasks of CR 8 to CR 11 numbered as there;

6.1.2 records `git rev-parse --short HEAD` and `git status --short`; that
HEAD is the baseline (1.6). The tree should be clean but for
`CODE_REVIEW.md` while it is untracked; any other change is recorded, and
the review does not start until the coordinator has logged what it is;

6.1.3 makes `tmp/review/` with `report/`, `i18n/`, and an `inbox/<id>/` and
`done/<id>/` per task and for `coordinator`;

6.1.4 runs the lock check of 12.2, which prints nothing.

6.2 Phase 1, review and fix: tasks 1.1 to 1.30 in a rolling pool of at most
eight at once, a size the coordinator chose (14.3.5); resumed agents count
against it. The order of launch is the largest work first, owners and
reviewers mixed: 1.19, 1.24, 1.15, 1.12, then 1.1 to 1.8, then the rest in
the order of their task ids. Requests that reach an owner after its pass are
worked in Phase 2. After an HTTP 429 the coordinator may lower the pool, and
logs it.

6.3 Phase 2, drain. When an agent has ended and its inbox holds requests,
the coordinator resumes it by SendMessage to work them (the text of 12.3.2),
or, when it cannot, launches a fresh agent under the same task id with the
Phase 2 prompt of 12.3.2. Task 1.19 may be drained by fresh agents run one
at a time, each taking the waiting requests, making its edits to
`python/test_browser.py` in one lock cycle and reading only the parts it
edits. This repeats until, with every Phase 1 agent ended, every inbox is
empty; at most three resumptions per task, the rest going to the
postmortem.

6.4 Phase 3, verification, tasks 1.31 to 1.39 (CR 10), each launched and
resumed as 5.8.1 says. A REJECTED fix goes to its owner as a request and is
worked as in 6.3, once; the closing agent checks the result.

6.5 Phase 4, closing, task 1.40 (11.1).

6.6 Phase 5, formatting, task 1.41 (11.2).

6.7 Phase 6, the postmortem, by the coordinator (12.4).

## 7 The agent's work

7.1 Every agent reads CR 1 to CR 7, its own entry in CR 8 to CR 11 and what
that entry cites. Its prompt names its task id, its entry, the baseline and
its phase (12.3); this file is its brief. The project rules reach every
agent in its context; no agent opens the project rules file.

7.2 An owner works in this order:

7.2.1 reads the cited P and B sections, the records of 2.5.3, the stubs of
its modules, its files, and the code on the other side of each seam;

7.2.2 writes its definition of done (7.4) into its report before any edit;
the definition is the agent's own, and the coordinator does not shorten it;

7.2.3 checks the code against each item and files findings (7.3.4),
sending each request for another owner's file as soon as it is found (5.6);

7.2.4 fixes its own files in severity order, tests first, each file under
its lock;

7.2.5 writes its fragment (7.6);

7.2.6 works its inbox (5.6.4 to 5.6.7);

7.2.7 checks each item of its definition again and marks it met, or unmet
with the finding, request or reason that holds it open;

7.2.8 works its inbox once more; reads the resolutions of its own requests,
`tmp/review/done/*/<own>_*`, into item 6 of its report; publishes the
report; and replies to the coordinator in at most 15 lines: counts by class
and severity, files changed, requests sent, locks held (none), departures.

A read only reviewer does 7.2.1 to 7.2.3 and 7.2.8, with a definition of
done for its review, and writes nothing outside `tmp/review/`.

7.3 The report, `tmp/review/report/<task id>.md`, numbered by ISO 2145:

7.3.1 Scope: the files owned and the files read.

7.3.2 Definition of done.

7.3.3 Accepted, not changed: each item with its record.

7.3.4 Findings, each `4.<n> <class> <severity> <file> <symbol>`, named
`<task id> 4.<n>` outside the report, followed by
Expected (the cited text), Actual (the code, quoted), Records searched (and
why none decides it), Action (fixed in its files; requested, with the
request; proposed in item 9; or not fixed, with the reason) and Checked (how
the fix was confirmed by reading).

7.3.5 Files changed.

7.3.6 Requests sent, each with its state.

7.3.7 Requests received, each with its resolution.

7.3.8 The names of its fragment.

7.3.9 Proposed edits to P, B and `API/`: the exact old and new text and the
reason.

7.3.10 Open questions met (2.2).

7.3.11 Owed to the testing phase.

7.3.12 The definition of done, item by item, met or unmet.

7.3.13 Commands and departures (4.4).

7.4 A definition of done holds at least:

7.4.1 the expected inventory of the area, each item with its source: the
modules, public names and signatures, line types handled and sent, settings
read, `i18n` names, test classes, and the proofs P 8.7 and B give the area;

7.4.2 the checks, each a statement a reader can confirm: conformance to P
and B; each seam; B 3; the project rules; the tests (each proof has its test
or rung, or a record says why not; error tests compare `i18n` text; no test
leaves state);

7.4.3 the accepted items found;

7.4.4 the exit: done when every check holds, or each that does not has a
finding whose action is a fix, a request, a proposed edit or a recorded
reason, which is one of: an open question (2.2), a public interface (3.2), a
run or a measurement (2.6, 4.1), a request pending with another owner, a
seam whose other side is pending (5.6.7). Time, effort and context are not
reasons: an agent short of context says so in its reply, and the
coordinator continues the task (6.3).

7.5 A request file:

```text
Request <from task id>_<n> to <owner task id>
File: <path>
Symbol: <name>
Finding: <class> <severity>, <one sentence>
Expected: <cited text>
Change: <exact old and new text, or the change in words>
Seam: none, pending, or <s>_<n> applied (5.6.7)
Forwarded from: <s>_<n>, or none
```

The owner appends one line: `Resolution: applied`, `Resolution: declined,
<record or rule>`, or `Resolution: forwarded to <task id>`.

7.6 A fragment, `tmp/review/i18n/<task id>.json`, is one JSON object with
the keys `add` and `reword`, each an object of name to text, and `remove`, a
list of names. It stands apart from the older fragments of `tmp/i18n/`
(B 3.7) because it can reword and remove as well as add (14.3.3).

## 8 Areas and their owners

8.0 Files by owner. Each entry below gives its task's files: owned
(edited), read (the seams), cited (the sources), accepted (the main items
that look like deviations and are not), open (questions it must not decide,
2.2), and candidates (what the logs left, to be checked against the current
code and the later records, and filed only if it still holds, its class
fixed by 2.3). The candidates are not the whole review; the definition of
done is. CR 12.5 maps every task to its section and its verifier.

8.1 Task 1.9, the Python test infrastructure.

8.1.1 Owns `python/tap_producer.py`, `python/tap_consumer.py`,
`python/test_tap_producer.py`, `python/test_tap_consumer.py`,
`python/category.py`, `python/test_test.py`, `python/test_all.py` (steward of
`_MODULES`), `python/i18n.py`, `python/test_i18n.py`.

8.1.2 Reads `API/python/tap_producer.pyi`, `tap_consumer.pyi`,
`category.pyi`, `i18n.pyi`; `ts/tap_producer.ts`; the `main(arguments)` of
`python/test_posix.py`, `test_wire.py` and `test_browser.py`.

8.1.3 Cites P 7.1, P 7.2 (the TAP modules and every way a run can fail), P
8.1, P 8.2; B 2.4, 2.18, 2.19.2, 2.22, 3.3, 4.11 (D12); L2016 3.59, 3.84;
L1601 3.7, 3.54, 3.58, 3.62.2, 3.65.

8.1.4 Accepted: D12's grammar; tappy's names as recalled; `set_stream`,
`Tracker(write)`, `module_run`, `run_end` and `TAPTestResult` (L2016 3.59.1,
3.59.2, 3.90.3); a fixture error ending the run with `Bail out! failfast`
(L2016 3.59.7); the `# TODO expected failure` form (L2016 3.59.6); full
option names in `test_all.py` only (B 2.22.2); `alarm_plan` in `category.py`
and the timers in the driver (B 2.22.3); a smoke run ending at its first
failure (B 10.4.54); f-strings in the runners and `category.py` (B 2.18.8).

8.1.5 Candidates:

8.1.5.1 `_STRINGS` stands after a function in `python/i18n.py`, against the
constants rule (L1413 4.3.3, L2016 3.100.17).

8.1.5.2 The two `ValueError` paths of the strings loader have no test (L1413
4.3.6).

8.1.5.3 `del sys.argv[1:]` twice in `test_all.py` (L2016 3.98.9), if it
survived `main(arguments)`.

8.1.5.4 Each way a run can fail of P 7.2 has its expected failure test, and
the TAP modules' tests run first (P 8.2).

8.1.5.5 `test_all.py` writes `<module>: <label>, <s> s` to stderr after each
module and `the <category> run took <s> s` at the end (B 2.18.6).

8.2 Task 1.10, the rules tooling.

8.2.1 Owns `python/test_posix.py`, `python/test_test_posix.py`,
`python/reformat.py`, `python/test_reformat.py`,
`python/reformat_table.json`, `python/reformat_whitelist.txt` (steward),
`python/pyproject.toml`, `test_posix.sh`, `powershell/test_lint.ps1`.

8.2.2 Reads every whitelisted file's extension, `ts/*.ts` for the audit, and
`powershell/test_powershell.ps1` (the lint step).

8.2.3 Cites P 7.5, P 8.2, P 8.6; B 2.12, 2.14 (history), 2.18.5, 2.19.3,
2.21, 3.8; L1413 4.2; L2016 3.52, 3.81, 3.87; L1601 3.38, 3.56, 3.59, 3.62,
3.65, 3.68.

8.2.4 Accepted: the byte order mark through the `utf-8-sig` codec (B
2.21.3); `test_posix.py` stopping at the banner of `xsjs_install.ps1` (B
10.4.45 a); the table as a data file (B 2.21.5); `test_lint.ps1`'s own list
of extensions (B 2.21.7); one matching rule (B 2.21.8); the first failure in
`test_lint.ps1` (B 2.21.9); the formatters rewriting files in every run (B
2.18.5); `audit_probe` in the runner (L2016 3.52.10); `.md`, `.json` and
`.css` outside the whitelist (B 3.8); the whitelist lines `LICENSE.md` and
`README.md`, the maintainer's (L2016 3.81.4).

8.2.5 Candidates:

8.2.5.1 The message of `synchronization_check` says four modules where
`_SYNCHRONIZATION_MODULES` names five (L2016 3.104.22, L1601 3.62.3, 5.9.5).

8.2.5.2 The audit matches tokens literally, so `new  Promise` and `.then (`
escape it and `x.await` is a hit (L1413 4.2.2, 4.2.3; L2016 3.52.11): S.

8.2.5.3 `_SYNCHRONIZATION_MODULES` is exactly `queue.ts`, `wire.ts`,
`http.ts`, `media.ts` and `boot.ts` (P 8.6).

8.2.5.4 A source file the whitelist misses is a discrepancy to fix (the
project rules); the census of task 1.1 sends what it finds. A new row needs
its lexer, and a new line must not change which files the formatter
rewrites beyond the file it adds.

8.2.6 Open: `test_posix.sh` is committed with mode 100644 while P 8.2 runs
`./test_posix.sh`; L1601 5.3.2 gives the `chmod +x` to the maintainer, "which
no agent may", so it is listed and nothing is changed.

8.3 Task 1.11, the Windows administration scripts and third party code.

8.3.1 Owns `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1` and
`xsjs_stop.ps1` (but for their D22 parts), `powershell/xsjs_util.ps1`,
`powershell/test_powershell.ps1`, `powershell/en-US/i18n.psd1`,
`python/third_party_fetch.py`, `python/test_third_party_fetch.py`,
`third_party/ttyd/01_srv_buf_size.patch`.

8.3.2 Reads `settings.json`, `provider.json`, `python/bootstrap.py`'s
arguments, `powershell/test_lint.ps1`, `python/page_build.py`'s archive
names.

8.3.3 Cites P 2.7, P 7.5, P 8.2, P 9; B 2.19.4 to 2.19.6, 2.21.2, 4.18
(D22), 4.26 (D31), 6.4, 6.5; L1413 4.5; L2016 3.17, 3.52, 3.86; L1601 3.54,
3.59.4.

8.3.4 Accepted: D22; the marks as they are (B 10.4.44 a); the three empty
`sha256` pins (L1413 4.5); the key through `WSLENV`; the "exited N" line
with its variable names (L2016 3.17.3, a decision with its rejected
alternatives); the first failed step ending the run with no
cleanup (B 2.19.5); `wsl --cd` of the Windows checkout (B 10.4.40 a); the
ttyd report step (D31); the root layout (B 5.18). Open: `ttyd.log` under
`%LOCALAPPDATA%` (B 6.5).

8.3.5 Candidates:

8.3.5.1 `powershell/test_powershell.ps1` keeps a `Remove-Item ...
-ErrorAction SilentlyContinue`, which swallows an error (L1601 3.62.3,
5.9.6).

8.3.5.2 Its header list of checkout files lacks `provider.json` (L2016
3.86.6, 3.104.21).

8.3.5.3 Other command lines logged with their variables unexpanded, outside
the work order of the time (L2016 3.17.4; the handoff that listed them is
deleted, so the agent finds them).

8.3.5.4 The `Import-LocalizedData` retry with `-UICulture en-US` and a failed
`wsl --update` that only warns (L2016 3.17.7): fallbacks, unless a record
decides them.

8.3.5.5 ttyd starts with `--srv-buf-size 1048576`, and the setting
`srv_buf_size` must have a reader (P 6.9: a constant no module reads is not
there); one of the two is the deviation.

8.3.5.6 The uniqueness of the pins has no test (L2016 3.52.4).

8.4 Task 1.12, JSLB in both languages.

8.4.1 Owns `python/jslb.py`, `python/test_jslb.py`, `python/vectors_make.py`,
`python/test_vectors_make.py`, `ts/jslb.ts`, `ts/test_jslb.ts`.

8.4.2 Reads `API/python/jslb.pyi`, `API/ts/jslb.d.ts`, the decoders' callers
(`main_loop.py`, `bootstrap.py`, `echo_loop.py`, `wire.ts`).

8.4.3 Cites P 1.4, P 3, P 8.3, P 8.7.2; B 2.13.3, 2.13.7, 4.3 to 4.6 (D3 to
D7), 5.12, 5.15; L1413 4.22, 4.32; L2016 3.48, 3.54; L1601 3.9.3, 3.42.

8.4.4 Accepted: the twin contract (L1413 4.22.1 to 4.22.16) and the recorded
language differences (L1413 4.32.1 to 4.32.11, L2016 3.54.5 to 3.54.9); D4's
deferred fault; D5, no slug; D7; doubles beyond 2^53 decoded (L1601 3.9.3);
the vectors in `build/vectors` (B 9.2, 4.6.5; L1601 3.7.2) with small limits
(L1601 3.42.5); `idle()` and `blob_make`'s `size`.

8.4.5 Candidates:

8.4.5.1 Every hard error of P 3.7 has a vector and both decoders refuse it;
the encoder refuses every line the decoder would.

8.4.5.2 The window of B 2.13.3 is checked at the CR before any blob byte,
and `line_max` before the bytes are buffered, in both languages.

8.4.5.3 `line_render` gives the form of P 3.11 identically in both.

8.4.5.4 A number of 5000 digits decodes in TypeScript where Python refuses
it, unpinned by a test (L2016 3.54.6).

8.5 Task 1.13, the Python server core.

8.5.1 Owns `python/dispatch.py`, `python/test_dispatch.py`, `python/mcp.py`,
`python/test_mcp.py`, `python/mcp_stdio.py`, `python/test_mcp_stdio.py`,
`python/settings.py`, `python/test_settings.py`, `python/verbose.py`,
`python/test_verbose.py`, `settings.json`, `provider.json` (steward of
both).

8.5.2 Reads their stubs, `API/settings.json`, `API/mcp/tools.json`, the
`engine_*` handlers, `ts/settings.ts`, `ts/dispatch.ts`, `ts/mcp.ts`.

8.5.3 Cites P 1.2, P 2.4, P 3.9, P 4.5, P 5.4, P 6.9, P 7.2; B 2.5, 2.8.2,
2.10, 2.13.2, 2.15, 2.16.7, 3.4, 3.6, 4.12 (D13), 4.17 (D21), 5.3, 5.11, 6.6;
L1413 4.14, 4.17 to 4.19; L2016 3.37, 3.39, 3.45, 3.73, 3.86; L1601 3.8,
3.41.

8.5.4 Accepted: no stdio refusal (B 2.8.2); level 1 passing output through
(B 10.4.25 a); the trace in header
JSON in debug mode only (B 10.4.26 a); no `level` column; D21; `tail_get`
(D13); exact type identity in the settings check; `system_restart` over
stdio failing loud (L2016 3.73.1); the level 0 flushes (L2016 4.8.5). Open:
`mcp_stdio.py` and `sys.pycache_prefix` (B 6.6); a tool's exception as a
-32603 response (L1413 4.19.4), a decision that L2016 3.100.5 reports as
breaking fail fast (2.3.5).

8.5.5 Candidates:

8.5.5.1 A negative `v` passes the dispatcher's type check (L2016 3.37.1).

8.5.5.2 Invalid JSON in `settings.json` or `provider.json` raises with no
`i18n` message (L2016 3.86.3, 3.100.18), if B 3.7 reaches it.

8.5.5.3 Every key of `settings.json` is P 6.9's and has a reader (with task
1.1).

8.5.5.4 `verbose.log` writes each line before it returns, so a hard exit
loses nothing (the project rules), and `exec` writes its start and exit at
levels 1 and 2 only (B 2.15.4).

8.6 Task 1.14, the Python substrate.

8.6.1 Owns `python/substrate.py`, `python/test_substrate.py`.

8.6.2 Reads `API/python/substrate.pyi`, `API/sql/*.sql`, `ts/substrate.ts`
(the twin), the `engine_*` callers.

8.6.3 Cites P 6.1 to 6.6, P 6.8, P 8.7.4; B 2.3, 2.13.4 to 2.13.8, 2.16.5,
3.2, 4.1 (D1), 4.16 (D18), 5.4; L1413 4.27; L2016 3.50; L1601 3.12, 3.42.

8.6.4 Accepted: D1; the shared cache namespace (L1413 4.27.5); no `fsync`
(L1413 4.27.7); the lazy `BEGIN IMMEDIATE` (L1413 4.27.8); a `COMMIT` inside
`sql_run` ending the transaction early, since its one alternative, an
authorizer, would refuse the AI API (L2016 3.50.1, B 2.8); D18 as scoped
(L2016 3.50.2); doubles above 2^53 stored (B 9.2, 4.6.4); one blob snapshots (B
2.13.8); no `max_page_count` (B 10.4.19 a); the server never compacting by
itself (B 2.16.5).

8.6.5 Candidates:

8.6.5.1 The `transaction_none` branch for a case that cannot happen (L2016
3.100.11).

8.6.5.2 `_DESYNC_MESSAGE` compared as a literal and not as `i18n` text, and
the `seq` start state kept from the deleted transcripts (L2016 3.88.4).

8.6.5.3 The fixed restore name with `O_EXCL`: after a `SIGKILL` a restore
raises `FileExistsError` until the file is removed by hand (L2016 3.50.5).

8.6.5.4 Each proof of P 8.7.4 has a test: the tables on first use, KV on
both ref forms, documents, heads, the round trip of P 6.4, `seq` across a
reopen, overflow at exactly `overflow_bytes`, snapshot and restore, a
`SIGKILL` between file and row, `kv_check`, `operation_apply` of a built
sequence, `turn_compact`.

8.7 Task 1.15, the Python engine handlers.

8.7.1 Owns `python/engine_kv.py`, `engine_doc.py`, `engine_db.py`,
`engine_turn.py`, `engine_sql.py`, `engine_verbose.py`, `engine_tap.py`,
`engine_mcp.py`, `engine_system.py`, and their nine `test_engine_*.py`.

8.7.2 Reads `API/ts/lines.d.ts`, their stubs, `python/substrate.py`,
`python/bootstrap.py`'s options, `ts/substrate.ts`'s forwarded lines.

8.7.3 Cites P 4.3, P 5.5 (the server tools), P 6.8, P 7.2, P 8.7.5; B 2.3,
2.8, 2.13.8, 2.15.5, 2.16.5, 4.1 (D1), 4.9 (D10), 5.2, 6.8, 6.9; L1413 4.26;
L2016 3.13, 3.35, 3.45, 3.73, 3.88; L1601 3.12, 3.41, 3.42.

8.7.4 Accepted: `since` on `db.create` and `db.drop` (D1); the `_*State`
holders; `source_put` and `system_restart` without a permit (B 2.8.2).
Open: `engine_turn`'s `json.dumps` without the 2^53 check (B 6.8); `seq` read
before the lock (B 6.9).

8.7.5 Candidates:

8.7.5.1 `system.restart` removes only the two token `--main-loop x` and
appends its own, so a `--main-loop=x` stays (L1413 4.26.5, L2016 3.100.4),
while D10 makes a repeated `--main-loop` an error in `bootstrap.py`: a
restart from such a command line fails. Seam with task 1.16.

8.7.5.2 `option_unfinished` and the nine `not_registered` checks, for cases
that cannot happen (L2016 3.45.9, 3.100.11).

8.7.5.3 The server applies both forwarded `turn.compact` and `turn.append`
(B 2.16.5): each has its handler and test.

8.7.5.4 The `sha256` literals of `test_engine_kv.py` kept from the deleted
transcripts, which `hashlib` can compute in the test (L2016 3.88.4): S.

8.7.5.5 `_main_loop_write` of `test_engine_system.py` has three words (L1601
3.63.3, 5.9.3).

8.8 Task 1.16, the Python platform and the seeds.

8.8.1 Owns `python/main_loop.py`, `python/test_main_loop.py`,
`python/bootstrap.py`, `python/test_bootstrap.py`, `python/echo_loop.py`,
`python/stall_loop.py`, `python/seed/hyperposition.json`,
`python/seed/prompt.json`, `python/seed/provider_script.json`,
`python/seed/bootstrap.js`.

8.8.2 Reads their stubs, `python/engine_system.py`, `python/verbose.py`,
`ts/worker_ai.ts` (the reader of `hello` and of the Script), the tools the
prompt names.

8.8.3 Cites P 2.3, P 2.4, P 3.10, P 4.4, P 4.5, P 5.6, P 6.6, P 6.9, P 7.2, P
8.7.3, P 8.7.5; B 2.10, 2.15.4, 2.15.5, 3.5, 4.7 to 4.9 (D8 to D10), 4.15
(D17), 5.1, 5.18, 6.11, 6.13; L2016 3.7, 3.9, 3.15, 3.35, 3.75, 3.76, 3.85,
3.86, 3.98; L1601 3.6, 3.8, 3.41.

8.8.4 Accepted: `loop_prepare` before `hello` (B 5.1); the seeded `seq` of
`metaverse`, which counts the `universe` DDL (L2016 3.7.1, whose question
went with B 6.1 when `DATA/` was scrubbed, L1601 3.4); the script row
written only while `metaverse` is at `seq` 0 (L2016 3.7.3); a crash before
the log opens reaching the terminal only (B 9.2, 4.6.7); the `error` line in
short names (L2016 3.9.13); the Script at
`/_files/provider/script.json` seeded with no replies (B 6.13); the prompt's
text, the maintainer's to review, but where it states something false.
Open: `-h` (B 6.11).

8.8.5 Candidates:

8.8.5.1 The comment above `stall_loop.loop_run` holds a `;` outside a code
span, which `comments_check` refuses (L1601 3.62.3, 5.3.4): severity 1, as
it stops `test_posix.py` once the banner question is answered.

8.8.5.2 `stall_loop`'s unreachable `loop_run` raises a plain `RuntimeError`,
not an `i18n` message (L2016 3.98.10).

8.8.5.3 A stale comment in `main_loop._line_serve` (L2016 3.100.16).

8.8.5.4 The `not_prepared` branch, for a case that cannot happen (L2016
3.100.11).

8.8.5.5 The prompt's "the same operations as the database tools" for
`engine.store` (L2016 3.103.7), and its permit sentences (L2016 3.75),
against the code.

8.8.5.6 The restart seam of 8.7.5.1.

8.9 Task 1.17, the wire test.

8.9.1 Owns `python/test_wire.py`.

8.9.2 Reads `python/bootstrap.py`, `main_loop.py`, `echo_loop.py`,
`stall_loop.py`, `jslb.py`, the `engine_*` handlers, `category.py`, and the
users of `replay_build` in `python/test_browser.py`.

8.9.3 Cites P 3.10, P 8.2, P 8.7.3, P 8.7.5; B 2.13.12, 2.18.2 to 2.18.4,
2.18.6; L2016 3.76, 3.88; L1601 3.9.4, 3.41.2, 3.42.4, 3.53.

8.9.4 Accepted: the last line regression on the console role (L2016 3.76.7);
128 MiB as one message (B 2.13.12); the labels (L1601 3.53.3); a public
`replay_build`; ttyd stopped with SIGTERM, then killed.

8.9.5 Candidates:

8.9.5.1 `rung_fit` holds `blob_max` random bytes twice in the test client,
request and echo, because the client has no streaming send (L1601 3.42.4,
5.9.9): S, 4 GiB in one process.

8.9.5.2 Each rung of P 8.7.3 and P 8.7.5 exists, under a timer that names
it, and a lone loss is reported with the ttyd version and never retried (P
3.10).

8.10 Task 1.18, the page build and DevTools.

8.10.1 Owns `python/page_build.py`, `python/test_page_build.py`,
`python/devtools.py`, `python/test_devtools.py`, `html/engine.html`,
`html/test.html`, `html/test_engine.html`, `ts/tsconfig.json` and
`ts/tsconfig.test.json` (steward of both).

8.10.2 Reads `API/python/page_build.pyi`, `devtools.pyi`, `ts/boot.ts`,
`ts/test_hook.ts`, `ts/error_overlay.ts`, the users of `devtools` in
`python/test_browser.py`.

8.10.3 Cites P 2.4 (the bundle's first four scripts), P 2.5, P 8.2, P 8.3, P
8.4; B 4.13 (D15), 4.14 (D16), 5.16, 5.25, 5.26; L1413 4.8, 4.9; L2016 3.52,
3.87; L1601 3.13, 3.16, 3.28, 3.68.3, 5.10.

8.10.4 Accepted: D15's bounded retry; three candidate trace event names (B
9.2, 4.6.18.4); `__all__` of three names (L1601 3.28); the worker source
contract (L1413 4.9); the build markers and `;` the formatter made (L1601
5.10). Open: `test_template_hooked` (2.2).

8.10.5 Candidates:

8.10.5.1 The `from typing` names of `devtools.py` out of order (L2016
3.100.13).

8.10.5.2 `error_overlay.overlay_install()` runs only from the last script,
so a throw while the bundle or xterm.js loads leaves a blank page (L2016
3.105.7), against P 2.4. Seam with tasks 1.21 and 1.28.

8.10.5.3 The production bundle carries no test code (P 2.5): `tsconfig.json`
lists no test module and no `test_hook.ts`; both lists are in reference
order, the first four scripts first.

8.10.5.4 The `tsc` run has no timeout (L2016 3.52.9).

8.11 Task 1.19, the browser test.

8.11.1 Owns `python/test_browser.py`, 8986 lines, the largest file, so it is
launched first (6.2). In Phase 1 it reviews the harness: imports,
constants, `RunContext`, `RungLog`, the roots and `session_run`,
`page_ready`, the stub server, `_PROBE_KIT`, `BrowserDriver`, `tap_check`,
the teardown; and it works its inbox in its pass. The rungs are reviewed by
tasks 1.5 to 1.7, whose requests it works in its pass or, as 6.3 says, in
Phase 2 by fresh agents run one at a time. Of the candidates below, the
items on a rung (8.11.5.1, and the rungs of 8.11.5.6) are checked by the
reviewer of the rung's stage; task 1.19 checks the harness items.

8.11.2 Reads `python/devtools.py`, `python/category.py`, `python/test_wire.py`
(`replay_build`), `python/substrate.py`, the `ts/` code each probe reaches.

8.11.3 Cites P 8.1, P 8.2, P 8.4, P 8.5, P 8.7.1 to 8.7.9; B 2.18 (the labels
and S4, N1 to N6), 2.18.6; L2016 3.92, 3.98, 3.106; L1601 3.17, 3.20, 3.23,
3.25, 3.44, 3.47, 3.53.

8.11.4 Accepted: the roots and ladders as built; stalls by SIGSTOP; the
drain burst; `_STRESS_ROUNDS` 8; the period 251 echo pattern; the test
engine page; the kept roots; local imports after `sys.pycache_prefix`
(L1601 3.53.4 G1); the labels.

8.11.5 Candidates:

8.11.5.1 Three comments hold a `;` outside a code span, above `rung_early`,
`ui_request` and `rung_ui_put_largest` (L1601 3.62.3, 5.3.4): severity 1, as
for 8.8.5.1.

8.11.5.2 `_KEY_ENTER`, `_KEY_INTERRUPT`, `_EXTRAS_NONE` and `_EXTRAS_KEY`
stand after their classes (L1601 3.25.3.2).

8.11.5.3 One word probe names (L1601 3.25.3.6) and three word names:
`rung_test_engine_start` (L1601 3.63.3), `rung_ui_put_largest` (L1601
5.9.3), `rung_level_two` and `rung_compact_auto` (L1601 3.47.6).

8.11.5.4 `probe.fault` finds the TAP `<pre>` on the test page (L1601
3.25.3.7).

8.11.5.5 A smoke run starts the stub HTTP server that no smoke rung needs
(L1601 3.53.4 G6, 5.3.6), against B 2.18.2, "Setup ... runs when a suite
that needs it runs": S, its design written in the record.

8.11.5.6 From L2016 3.106, never scheduled: a rung timer cannot fire during
a DevTools call, and only `CheckFailed` names the rung (3.106.7, against P
8.2); a mutable Protocol attribute fails pyright strict (3.106.8); a racy
`rung_order` (3.106.9); the stub swallows an unexpected path (3.106.10);
`tap_check` tallies failures (3.106.11); the roots inherit `debug` and
`provider.scripted` from the checkout (3.106.12); `rung_long` prints an
unmeasured 0.0 ms (3.106.16, no fake data); `rung_single` proves nothing
(3.106.17); `rung_desync` clicks Reload without the hit check (3.106.18);
`tap_failures` zips two different splits with `strict=True` (3.106.19); the
`SIGALRM` handler left installed and a port released before its reuse
(3.106.23).

8.11.6 Open: about 60 lines over 79 columns that the formatter cannot wrap
(L1601 3.25.3.4; L2016 3.97, 3.106.21), listed by CR 3.11 and not changed.

8.12 Task 1.20, the TypeScript test harness.

8.12.1 Owns `ts/unittest.ts`, `ts/test_unittest.ts`, `ts/tap_producer.ts`,
`ts/test_tap_producer.ts`, `ts/test_all.ts` (steward of its tables),
`ts/test_hook.ts`.

8.12.2 Reads `API/ts/unittest.d.ts`, `tap_producer.d.ts`,
`python/tap_producer.py` (the twin), `ts/boot.ts`, `ts/page.ts`.

8.12.3 Cites P 2.5, P 7.3, P 8.1; B 2.4, 5.10; L1413 4.12; L2016 3.59, 3.84;
L1601 3.7.4, 3.13.

8.12.4 Accepted: two TAP documents, the UI's then the worker's (L2016
3.84.1, L1601 3.7.4); failfast `false` (L2016 3.84.2); the first two modules
on both threads; no per module timer; only the UI stream on the page;
`expectedFailure` through a `WeakSet`; the `unittest` additions (B 5.10).

8.12.5 Candidates:

8.12.5.1 `test_unittest.ts` tests that assert only a base class (L2016
3.102.6).

8.12.5.2 `self.name` tested as `""` here and as `"ai"` in `boot_run` (L2016
3.84.7, 3.105.14).

8.12.5.3 Output identical to Python's for the same outcomes (P 8.1); with
task 1.4.

8.13 Task 1.21, the first TypeScript modules.

8.13.1 Owns `ts/error_overlay.ts`, `ts/utility.ts`, `ts/ui_strings.ts`,
`ts/settings.ts`, `ts/i18n.ts`, `ts/verbose.ts`, `ts/overlay.ts`, and their
seven tests.

8.13.2 Reads their stubs, `ts/page.ts`, `ts/worker_ai.ts`,
`python/settings.py`, `python/i18n.py`.

8.13.3 Cites P 1.2, P 2.4, P 2.6, P 7.3; B 2.15.6, 3.3, 4.22 (D26), 5.3,
5.6; L1413 4.6, 4.7, 4.15, 4.21; L2016 3.39, 3.51, 3.79; L1601 3.9.3,
3.13.3, 3.41.

8.13.4 Accepted: `FaultScreen` and the first fault only (L2016 3.51.1);
worker detection by `typeof document`; computed SHA-256 constants;
`ValueStore`, `Sender`, `i18n_format`, `LineRing`; numbers refused only for
NaN and the infinities (L1601 3.9.3). Open: a line before `settings_set`
throwing (L1601 3.41.3); the 55 byte SHA-256 boundary (L2016 3.51.4).

8.13.5 Candidates:

8.13.5.1 Tests that assert only a base class in `test_verbose.ts`,
`test_overlay.ts` and `test_i18n.ts` (L2016 3.102.6).

8.13.5.2 `thrown_stack` returning `""` and `overlay_show` skipping a missing
stop function (L2016 3.102.10).

8.13.5.3 The worker's `error` listener does not cancel the event, so the
page may show file, line and column without a stack (L2016 3.105.11).

8.13.5.4 `settings_put` in debug mode changes only the UI's copy (L2016
3.79), where P 2.4 changes the live value and sends `settings.put`. Seam
with task 1.28.

8.13.5.5 Tests that leave ring lines or handlers in the thread's live state
(L2016 3.102.14).

8.14 Task 1.22, the TypeScript dispatcher and task manager.

8.14.1 Owns `ts/dispatch.ts`, `ts/test_dispatch.ts`, `ts/queue.ts`,
`ts/test_queue.ts`.

8.14.2 Reads their stubs, `python/dispatch.py`, every `handler_register`
and `task_submit` caller.

8.14.3 Cites P 1.3, P 3.9, P 4.1 to 4.3, P 8.6; B 2.13.7, 2.15.6, 3.1, 4.2
(D2), 5.5, 5.17; L1413 4.25, 4.33, 4.34, 4.36; L2016 3.41, 3.42; L1601 3.41,
3.42, 3.63.2.

8.14.4 Accepted: D2; one item per macrotask through a `MessageChannel`
(L1413 4.33.2); an `error` line as a fault (L1413 4.33.9); `forward_marked`;
the explicit owner; no bound before `sink_attach` (B 2.13.7); the measure of
a held line (L2016 3.41.1).

8.14.5 Candidates:

8.14.5.1 `dispatch.ts` accepts the ids 0, -3 and 1.5 and a string `v` where
Python refuses them (L2016 3.102.5); with task 1.4.

8.14.5.2 `queue.step_empty`, unreachable (L2016 3.102.10).

8.14.5.3 One word names such as `Owed`, `Leaf`, `Entry` (L2016 3.102.9),
where they stand in these files.

8.14.5.4 Tests that leave registered handlers in the live state (L1413
4.33.18, L2016 3.102.14).

8.15 Task 1.23, the TypeScript wire and http lanes.

8.15.1 Owns `ts/wire.ts`, `ts/test_wire.ts`, `ts/http.ts`, `ts/test_http.ts`.

8.15.2 Reads their stubs, `API/ts/lines.d.ts`, `ts/jslb.ts`, `ts/worker_ai.ts`,
`ts/console_view.ts`, `python/bootstrap.py`'s `hello`.

8.15.3 Cites P 3.10, P 4.1, P 4.4, P 4.5, P 4.7, P 8.7.6; B 2.13.7, 4.19
(D23), 4.20 (D24), 4.23 (D27), 5.8, 5.9; L1413 4.24, 4.29; L2016 3.56, 3.57;
L1601 3.9, 3.42.

8.15.4 Accepted: the 120 s waits as defaults (B 2.6.2); `hello_line_max`
10485760 (B 10.4.18 a); `wire.error_first`; the constructors (L2016
3.56.4); the console read (L1413 4.29.18).

8.15.5 Candidates:

8.15.5.1 `ConsolePort.names_full()`, a second reader of the name form,
against D27's one `names_full()` in the worker (L2016 3.102.15).

8.15.5.2 tty 1's first message carries `columns: 80, rows: 24` from the old
`python/bootstrap.html` (L2016 3.102.16), a reuse by availability.

8.15.5.3 `http.ts`'s `.catch` after `.then` reports an error in building the
reply as `http.fetch_failed` and can leave a rejection unhandled (L2016
3.102.11).

8.15.5.4 `close_take` skipping an unset receiver, `wire.read_none`,
`wire.frames_none`, and `http.stack_missing` (L2016 3.102.10, L1413
4.24.13): unreachable or default branches.

8.15.5.5 `test_http.ts` tests that assert only a base class (L2016 3.102.6).

8.16 Task 1.24, the TypeScript substrate.

8.16.1 Owns `ts/substrate.ts` and `ts/test_substrate.ts` (steward; task 1.8
reviews the test).

8.16.2 Reads `API/ts/substrate.d.ts`, `python/substrate.py` (the twin),
`ts/worker_ai.ts`, `ts/tools_browser.ts`, `ts/script.ts`, `ts/utility.ts`.

8.16.3 Cites P 1.3, P 2.2, P 6, P 8.7.7; B 2.2, 2.3, 2.13, 2.16, 3.2, 4.1,
5.4, 5.17, 5.24; L2016 3.61, 3.62; L1601 3.12, 3.39, 3.42, 3.63.2, 3.65.

8.16.4 Accepted: the fixed `CacheFiles` slots and pool (L2016 4.8.2);
`forward_done` checking `since + 1` (L2016 3.62); a forwarded `turn.append`
through `#turn_add`, never compacting (L1601 3.39.2, 5.6.4); VACUUM's rowids
(L2016 3.61.14); `kv_check` sparing a live sink file (L2016 3.61.9); the
step script's `engine.log(1, ...)` (B 2.20.1). Open: `json_canonical`
refusing doubles above 2^53, "the maintainer's call" (L1601 3.12.6).

8.16.5 Candidates:

8.16.5.1 `db_unload` and `db_load` refuse with `substrate.forward_pending`
while forwarded lines of the database are unanswered (L2016 3.61.11), a
refusal between the AI API and a database that no plan asks for (L2016
3.103.3; the project rules, B 2.8): M. The fix removes the refusal; the
owner records the design it chooses, within P 4.2's one synchronization
tool, and proposes it instead where it needs a public API change (CR 3.2).
Seam with task 1.27.

8.16.5.2 The incremental SHA-256 copies `utility`'s block function (L2016
3.61.19), where P 2.4 makes `utility` the single door for `sha256_hex`: S,
whose fix needs a public name in `utility` and so is proposed (CR 3.2).

8.16.5.3 Module level constants outside `constants`, and fields without
their comment (L2016 3.103.14).

8.16.5.4 `db.snapshot` lines in short names always, where P 2.4 wants full
names in debug mode (L2016 3.103.13).

8.17 Task 1.25, MCP and the providers in TypeScript.

8.17.1 Owns `ts/mcp.ts`, `ts/test_mcp.ts`, `ts/provider.ts`,
`ts/test_provider.ts`, `ts/provider_script.ts`, `ts/test_provider_script.ts`.

8.17.2 Reads their stubs, `API/mcp/tools.json`, `python/mcp.py` (the twin),
`ts/http.ts`, `ts/agent.ts`, `ts/tools_browser.ts`.

8.17.3 Cites P 1.1, P 5.2, P 5.4, P 5.7; B 2.8, 2.10, 4.24 (D28), 5.7; L2016
3.31, 3.65, 3.75, 3.89; L1601 3.6.

8.17.4 Accepted: the stored block PNG (L2016 3.31.1); synthetic chat ids;
dotted names unmapped (D28); `wake_register` (L2016 3.65.1); `isError`
copied only when set (L2016 3.65.5); `version_refused` in TypeScript (L2016
3.65.8); `model: ""` when scripted (L2016 3.89.1).

8.17.5 Candidates:

8.17.5.1 No test keeps a tool's `_meta` through `tools/list` or
`tools_convert` (L2016 3.75.3, 3.75.4): S.

8.17.5.2 `key_get` with no key untested (L2016 3.31.13).

8.17.5.3 Module level constants outside `constants` (L2016 3.103.14).

8.18 Task 1.26, the agent loop and scripts.

8.18.1 Owns `ts/agent.ts`, `ts/test_agent.ts`, `ts/script.ts`,
`ts/test_script.ts`.

8.18.2 Reads `API/ts/agent.d.ts`, `script.d.ts`, `ts/substrate.ts`,
`ts/mcp.ts`, `ts/provider.ts`, `python/seed/prompt.json`.

8.18.3 Cites P 5.3, P 5.6, P 6.6, P 6.10, P 8.5; B 2.2.4, 2.15.6, 2.16,
4.15 (D17); L2016 3.64, 3.66; L1601 3.6, 3.39, 3.63.2.

8.18.4 Accepted: a tool call turn stored with its results (B 9.2, 4.6.2);
the over limit message as `json_text` alone (L2016 3.64.5); a click told as
text; `script_run`'s `trace` boolean (B 2.15.6). Open: `universe_ambiguous`
(B 6.7).

8.18.5 Candidates:

8.18.5.1 A script that returns NaN, Infinity, a BigInt or a cyclic object
throws out of its tool, and the trace throws on such arguments (L2016
3.103.6).

8.18.5.2 No remnant of the replaced estimate (P 10.20) in `agent.ts`;
compaction is the store's (B 2.16.5).

8.19 Task 1.27, the browser tools.

8.19.1 Owns `ts/tools_browser.ts`, `ts/test_tools_browser.ts`.

8.19.2 Reads `API/ts/tools_browser.d.ts`, `API/mcp/tools.json`,
`ts/substrate.ts`, `ts/mcp.ts`, `ts/script.ts`, `ts/wire.ts` (the console
port), `ts/page.ts` (`permit.ask`).

8.19.3 Cites P 2.3, P 4.6, P 4.7, P 5.5, P 5.7, P 6.10; B 2.2.3, 2.8,
2.13.8, 2.15.6; L2016 3.66; L1601 3.12, 3.42.

8.19.4 Accepted: the wake states (L2016 3.66.3); the permit flow inside the
tool (L2016 3.66.16); the console output normalized (L2016 3.66.17);
`snapshot_data` private here and in the worker (L1601 3.42.3); the four
database tools registered beside the seventeen of `tools.json` (B 5.19).

8.19.5 Candidates:

8.19.5.1 `console_run` neither checks `debug` nor opens tty 0 (L2016 3.66.18,
3.103.8), where P 5.5 makes it a debug tool and P 2.3 has the AI open the
console with permission.

8.19.5.2 `test_tools_browser.ts` keeps the withdrawn `sql_run` refusal
sentence in a private copy (L2016 3.103.11, 3.104.20).

8.19.5.3 `verbose.tail` lines in short names always (L2016 3.103.13).

8.19.5.4 The `db_unload` and `db_load` seam of 8.16.5.1.

8.20 Task 1.28, the AI worker and boot.

8.20.1 Owns `ts/worker_ai.ts`, `ts/test_worker_ai.ts`, `ts/boot.ts`,
`ts/test_boot.ts`.

8.20.2 Reads `API/ts/boot.d.ts`, `ts/queue.ts`, `ts/wire.ts`,
`ts/substrate.ts`, `ts/mcp.ts`, `ts/agent.ts`, `ts/tools_browser.ts`,
`ts/page.ts`, `ts/overlay.ts`, `python/bootstrap.py`'s `hello`.

8.20.3 Cites P 1.3, P 2.2, P 2.4, P 2.6, P 4.1, P 4.3, P 4.4, P 6.4, P 6.8,
P 6.10, P 8.6; B 2.2.5, 2.7, 2.13.7, 4.8 (D9), 4.23 (D27), 5.17; L2016 3.79;
L1601 3.7.4, 3.10, 3.12, 3.13, 3.42.

8.20.4 Accepted: initialization after `hello` with fixed capacities (L2016
3.79); the start chain; the settings relay as a request; the internal line
types (L2016 3.79); `WireTap` in debug mode; `info_read` (L2016 3.89.4);
the UI upload pacing (B 9.2, 4.6.18.3).

8.20.5 Candidates:

8.20.5.1 The tty 1 overlay never shows `hello` and its reply (L2016
3.105.13), against P 2.6.

8.20.5.2 `script_read` reads the provider Script with `value_text` and no
fetch on a miss, so a Script over `overflow_bytes` faults the start (L1601
3.20.4, 4.7.4), against P 6.4: S.

8.20.5.3 Each start replacement checks the image's `sha256` before it
restores (P 6.8), where L2016 3.79 recorded a check by `seq` only.

8.20.5.4 The seams of 8.10.5.2 and 8.13.5.4.

8.21 Task 1.29, the page.

8.21.1 Owns `ts/page.ts`, `ts/test_page.ts`, `html/engine.css`.

8.21.2 Reads `ts/console_view.ts`, `ts/overlay.ts`, `ts/media.ts`,
`ts/error_overlay.ts`, `ts/worker_ai.ts`, `html/engine.html`.

8.21.3 Cites P 2.2, P 2.4, P 2.6, P 4.6, P 4.7, P 5.7; B 2.11, 9.2 (4.6.8);
L2016 3.79, 3.85; L1601 3.10, 3.13.

8.21.4 Accepted: the column layout (L1601 3.10.3); the two states of P 2.6;
the black backgrounds (L2016 3.85); clicks floored; an empty text sent as
`ai.say ""`.

8.21.5 Candidates:

8.21.5.1 The image download timer reuses `provider.timeout_seconds` (L2016
3.102.8, 3.105.8), a reuse by availability, where P 4.7 wants a named
constant; with task 1.30 if the timer is there.

8.21.5.2 The permission flow of P 4.6: `dom.choice` on the DOM port, Always
Allow for the tab only.

8.21.5.3 Every state in which a part of the page is unintentionally
invisible, beyond the two P 2.6 accepts (the project rules).

8.22 Task 1.30, media and the console view.

8.22.1 Owns `ts/media.ts`, `ts/test_media.ts`, `ts/console_view.ts`,
`ts/test_console_view.ts`.

8.22.2 Reads `API/ts/media.d.ts`, `console_view.d.ts`, `ts/page.ts`,
`ts/wire.ts`.

8.22.3 Cites P 2.6, P 4.7, P 5.7, P 6.7; B 5.13, 5.14, 6.12; L2016 3.11,
3.29; L1601 3.10, 3.13.

8.22.4 Accepted: an image counted as width by height by 4 bytes; eviction
oldest first; decode before the reply; the console reopening; rows fitted to
the space (L1601 3.13.3). Open: the xterm options (B 6.12).

8.22.5 Candidates:

8.22.5.1 `media.ts`'s `stack: error.stack` (L2016 3.102.10).

8.22.5.2 The columns, 120, a constant whose comment must say its writer
chose it (L2016 3.105.15).

8.22.5.3 The download timer of 8.21.5.1.

## 9 Read only reviewers

9.0 These tasks edit nothing outside `tmp/review/`. Each writes requests to
the owners of CR 8 and a report as CR 7.3 says, its definition of done
covering its review.

9.1 Task 1.1, the census.

9.1.1 Every literal `i18n("...")` call in `python/` and `ts/`, code and
tests, has an entry in `i18n/en-US.json` with as many placeholders as
arguments; every entry has a call outside the tests; the PowerShell names
of `powershell/en-US/i18n.psd1` against their uses.

9.1.2 The keys of `settings.json` against P 6.9, `API/settings.json`, both
settings checks and every fixture that writes a whole settings object; each
key has a reader.

9.1.3 Every source file outside `.git`, `build/`, `tmp/` and `third_party/`
is matched by a whitelist line, but for B 3.8's exclusions; a miss is a
request to task 1.10.

9.1.4 `ts/tsconfig.json` and `ts/tsconfig.test.json` against `ts/` and P
2.5: requests to task 1.18.

9.1.5 `_MODULES` of `python/test_all.py` against the test modules present,
each once, the TAP modules first: requests to task 1.9. The tables of
`ts/test_all.ts` against the TypeScript test modules: requests to task 1.20.

9.1.6 Each stub of `API/python/` and `API/ts/` against its module: every
public name and signature. A difference recorded in B 5, B 7 or a log's
API ADDITION or API DEPARTURE is accepted and listed. An unrecorded one is a
U finding and a request to the owner, who moves the code to the stub (CR
3.2), as a seam change where other areas call it (5.6.7). A stub edit is
proposed (7.3.9) instead only where P or B states the code's form, or where
the stub's form would break a recorded decision.

9.1.7 `API/mcp/tools.json` against the tools that `ts/tools_browser.ts` and
`python/engine_system.py` register: names, descriptions, schemas,
prefixes. Accepted: the four database tools absent from it (B 7.9).
Candidate: P 5.5's `source_put {name}` against the code's arguments (L2016
3.104.24).

9.2 Task 1.2, the rules sweep, by `grep` over the whitelisted files, one
request per owner per rule with every hit listed:

9.2.1 swallowed errors and fallbacks: an `except` that passes, returns a
default or continues; a bare or `Exception` catch with no raise; an empty
`catch`; `??` and `||` defaults on required values; `-ErrorAction
SilentlyContinue`; `|| true` and `2>/dev/null` in shell;

9.2.2 timers and sizes as literals outside named constants, and named timers
without the comment of P 4.7;

9.2.3 function and class names of one word or of three or more, private ones
included, but for the names of CR 3.6 and of `API/`;

9.2.4 Python import lines and `from` (CR 3.9); constants not at the top;
TypeScript constants outside the frozen `constants` object;

9.2.5 two consecutive comment lines where B 3.4 forbids them, and comments
or strings over 79 columns that the formatter cannot wrap;

9.2.6 `isinstance` or `is None` branches that only narrow a type, and
`i18n` called with a name that is not a literal (B 3.4);

9.2.7 `await`, `.then(`, `new Promise`, `Atomics` and `SharedArrayBuffer`
with any white space, in `ts/*.ts` outside the five modules of P 8.6.

9.3 Task 1.3, the line contract.

9.3.1 Every row of `API/ts/lines.d.ts`, its type, lane, direction, blobs and
payload, against the Python handlers and the TypeScript handlers registered
for it and every line built with its `t`: field names and types, blob
counts, `k`, reply shapes, `since` and `seq`, the name form in debug mode (P
2.4).

9.3.2 The owner tables against P 4.2 and P 4.3, `verbose.` to `server`
among them; the `hello` exchange on both sides (P 4.4); the `error` line (P
4.5); the `mcp` line (P 5.4).

9.3.3 Internal line types: those recorded (B 5.17, L2016 3.29.4, L2016 3.79,
L1601 3.10.7) are accepted; an unrecorded one is a finding.

9.3.4 Accepted, listed as not applied in B 7.9: the `console.open` reply
(D23), `DbName` without `since` (D1). Candidates, review findings never
scheduled, each a proposed edit of `API/ts/lines.d.ts` (7.3.9) where the
code is right: `mcp` called a push while both sides send requests (L2016
3.100.9, 3.103.9); `HttpResponse`'s blob for a `binary` request that
`HttpRequest` cannot ask for (L2016 3.102.12).

9.4 Task 1.4, the twins. What P says behaves the same in both languages,
other than JSLB, which task 1.12 owns whole:

9.4.1 `substrate.py` and `substrate.ts`: `ref_split`, `doc_encode` and
`doc_decode`, canonical JSON, `seq`, overflow at exactly `overflow_bytes`,
`turn_compact` and its summary, `operation_apply` against each forwarded
line. Accepted differences: L2016 3.61.10, 3.61.16; B 9.2, 4.6.4.

9.4.2 `dispatch.py` and `dispatch.ts` (accepted: L1413 4.25.5, L2016 3.37.2,
3.37.3; candidate: L2016 3.102.5); `mcp.py` and `mcp.ts`: codes, texts,
revision (accepted: L2016 3.65.5, 3.65.8); `settings.py` and `settings.ts`;
`verbose.py` and `verbose.ts`; `i18n.py` and `i18n.ts`, one placeholder
rule.

9.4.3 `tap_producer.py` and `tap_producer.ts`: the same TAP text for the
same outcomes (P 8.1), D12.

9.5 Tasks 1.5 to 1.7, the rungs of `python/test_browser.py`, divided by the
stage in each rung's name: task 1.5 the rungs named "stage 0:", "stage 4:",
"stage 6:" and "stage 7:"; task 1.6 "stage 5:"; task 1.7 "stage 8:". The
proof of stage N is P 8.7.(N+1). Each rung, with the rung items of 8.11.5
in its stage, is checked against its proof, B and the decisions of the logs:
it drives what it claims through the real path, checks what it states,
fails first and loud with a timer that names it, holds no fake data, and
carries its label of B 2.18.4. Requests go to task 1.19. The harness is
task 1.19's.

9.6 Task 1.8, `ts/test_substrate.ts`: P 8.7.7's port of the stage 3 suite,
class by class against `python/test_substrate.py`, each test not ported
having a record (accepted: `test_wal_left`, B 9.2, 4.6.19); messages
compared as `i18n` text (L2016 3.103.12); the kill probes; no state left
between tests. Requests go to task 1.24.

## 10 Verifiers

10.1 Tasks 1.31 to 1.39 are fresh agents and edit nothing outside
`tmp/review/`. Each reads the reports of its areas, `git diff <baseline> --`
their files, and every file an area created (its report's item 5), which
`git diff` does not show while untracked, and for every fix and every
declined request states CONFIRMED or REJECTED with its reason. Like every
agent, a verifier takes the project rules from its context and does not
open the project rules file. It checks that:

10.1.1 the fix does what its finding says and meets the cited text;

10.1.2 it reverses no accepted item (2.1) and decides no open question
(2.2);

10.1.3 it adds nothing unmotivated (CR 3.1) and changes no public interface
(CR 3.2);

10.1.4 it breaks no project rule and no B 3 rule, and its test moved with it
(CR 3.4);

10.1.5 its strings are in a fragment, and each seam it changed changed on
both sides, or on neither (5.6.7);

10.1.6 a declined request cites a record or rule that does decide it;

10.1.7 the items its owner marked met in the definition of done hold, by
sample.

10.2 The groups:

10.2.1 task 1.31: tasks 1.9, 1.10, 1.11;

10.2.2 task 1.32: tasks 1.12, 1.13;

10.2.3 task 1.33: tasks 1.14, 1.15;

10.2.4 task 1.34: tasks 1.16, 1.17, 1.18;

10.2.5 task 1.35: task 1.19;

10.2.6 task 1.36: tasks 1.20, 1.21, 1.22, 1.23;

10.2.7 task 1.37: tasks 1.24, 1.27;

10.2.8 task 1.38: tasks 1.25, 1.26;

10.2.9 task 1.39: tasks 1.28, 1.29, 1.30.

## 11 Closing and formatting

11.1 Task 1.40, the closing agent, after every writer and verifier:

11.1.1 merges every fragment into `i18n/en-US.json`, one flat object, keys
sorted by code point, ASCII, as L2016 3.95 built it. Identical additions
from two fragments merge once. A name given two different texts, or written
by a task that does not own it (3.5), is left as at the baseline and becomes
a request to its owner. A removed name that a call still uses is kept and
reported;

11.1.2 checks again every literal `i18n` call against the merged file, with
its placeholder count, and every entry for a call outside the tests; a
mismatch is a request to the owner;

11.1.3 checks again, on the changed tree, the census items 9.1.3 to 9.1.5
for every file the review created or renamed, a miss being a request;

11.1.4 checks each REJECTED fix's resolution, and every request resolved
"applied" after its area's verifier ended, as 10.1 says;

11.1.5 checks that every request with a `Seam:` line has both sides applied
or neither; a half applied seam is severity 1 in `summary.md` and in the
postmortem;

11.1.6 runs the lock check of 12.2. When 11.1.1 to 11.1.5 made requests, or
the check prints a lock name, the coordinator runs one more round of 6.3
and then this task again, before 11.2 starts;

11.1.7 writes `tmp/review/maintainer_edits.md` (every report's item 9),
`tmp/review/open.md` (items 10 and 11) and `tmp/review/summary.md`: counts
by class, severity and area; every finding not fixed, named `<task id>
4.<n>`, with one sentence and its reason.

11.2 Task 1.41, the formatter, after the closing agent, by the project rules
and as L1601 2.25 ordered and L1601 3.68 did:

11.2.1 checks with `git status --short` that only the review's changes are
in the tree, and `CODE_REVIEW.md` while it is untracked;

11.2.2 stages the whitelisted files the review changed, the one staging the
project rules allow, so the formatter's own changes stay apart;

11.2.3 runs `python3 python/reformat.py`, writes `git diff` to
`tmp/review/format_1.diff`, runs it again, writes `tmp/review/format_2.diff`,
and compares the two with `cmp`; a second run that changes anything means
the formatter is not stable, which the postmortem tells the user;

11.2.4 reads the formatter's changes; one it believes wrong may be reverted
and the edit made by hand, as the project rules allow, and is reported;

11.2.5 commits nothing and unstages nothing. The PowerShell files are
Windows's to format (B 2.21) and are not formatted; the ones the review
changed are owed to `powershell/test_lint.ps1` (12.4).

11.2.6 does not revert the formatter's changes to the files of CR 3.10 or
2.6 that the whitelist covers, such as `API/` stubs and
`python/bootstrap.html`, but lists them for the maintainer beside L2016
4.8.9, which recorded that risk.

## 12 The coordinator

12.1 The coordinator writes only its log, the directories of 6.1.3 and the
`mv` of 5.1; it launches, checks and records, and edits no source and no
report. It reads the reports, not the agents' transcripts. It launches
every agent as the general purpose type, and loads SendMessage and TaskStop
with ToolSearch before it first needs them. A coordinator short of context
ends with its log current; a new coordinator session continues from the log
and `tmp/review/`.

12.2 After every agent ends it runs the lock check, `find . -path ./.git
-prune -o -path ./build -prune -o -name '*.T1.*' -print`, which may show
only running agents' locks; a lock of an ended agent is stray, and the
coordinator resumes that task to release it. It lists `tmp/review/inbox/*/`;
runs `git status --short`, which shows nothing staged before 11.2; and
records in its log, with the time from `date '+%d_%H%M'`, the agent's reply
in short and what the checks showed.

12.3 The prompts.

12.3.1 Phase 1 and Phase 3:

```text
You are task <id> of the code review in /home/t/xstation.js. Read
CODE_REVIEW.md sections 1 to 7 and your entry, section <n>, and work as
they say. Baseline: <hash>. Phase: <1 or 3>. Your lock suffix is .T<id>,
your inbox tmp/review/inbox/<id>/, your report tmp/review/report/<id>.md.
Reply in at most 15 lines.
```

12.3.2 Phase 2, sent by SendMessage to the agent, or as the prompt of a
fresh agent under the same task id:

```text
Phase 2 of task <id>. Baseline: <hash>. Read your report (its lock name if
it is not published), work every request in tmp/review/inbox/<id>/ as
CODE_REVIEW.md 5.6.4 to 5.6.7 say, then update items 5 to 7 and 12 of the
report, publish it, and reply in at most 15 lines. A fresh agent reads
CODE_REVIEW.md sections 1 to 7 and its entry, section <n>, first.
```

12.4 The postmortem, in the log and in the conversation with the log's
link, only when every agent has ended and every task is ready for review:
every unfinished task and every lost agent; every finding not fixed, each
with one sentence; every half applied seam; the open questions met; the
proposed edits to P, B and `API/`; the values owed to the testing phase;
the PowerShell files changed, owed to `powershell/test_lint.ps1` on
Windows; the formatter's stability and the changes of 11.2.6; screenshots,
none, since nothing runs (14.3.4); and the A and B items of the requests
the review served.

12.5 Tasks, sections and verifiers:

```text
task  section  verified by    task  section  verified by
1.1   9.1      -              1.22  8.14     1.36
1.2   9.2      -              1.23  8.15     1.36
1.3   9.3      -              1.24  8.16     1.37
1.4   9.4      -              1.25  8.17     1.38
1.5   9.5      -              1.26  8.18     1.38
1.6   9.5      -              1.27  8.19     1.37
1.7   9.5      -              1.28  8.20     1.39
1.8   9.6      -              1.29  8.21     1.39
1.9   8.1      1.31           1.30  8.22     1.39
1.10  8.2      1.31           1.31  10.2.1   -
1.11  8.3      1.31           1.32  10.2.2   -
1.12  8.4      1.32           1.33  10.2.3   -
1.13  8.5      1.32           1.34  10.2.4   -
1.14  8.6      1.33           1.35  10.2.5   -
1.15  8.7      1.33           1.36  10.2.6   -
1.16  8.8      1.34           1.37  10.2.7   -
1.17  8.9      1.34           1.38  10.2.8   -
1.18  8.10     1.34           1.39  10.2.9   -
1.19  8.11     1.35           1.40  11.1     -
1.20  8.12     1.36           1.41  11.2     -
1.21  8.13     1.36
```

A verifier's entry is 10.1 with its group of 10.2; the requests of tasks
1.1 to 1.8 are verified with the owners that applied them.

## 13 Designs not built

13.1 A verification run, for the maintainer to turn on. After Phase 3 and
before Phase 4, one agent runs, from the checkout's top, with
`PYTHONPYCACHEPREFIX=build/pycache`, each Python unit module of
`python/test_all.py`'s `_MODULES` that a review change touched, as
`python3 -X dev -m unittest <module>` from `python/`, under a timer of 600 s
each, a default chosen by the writer of this plan; the first failure stops
it, and its output goes to `tmp/review/run.txt`. A failure becomes a request
to the owner and one more round of 6.3. Nothing TypeScript, no wire or
browser test and no `test_posix.py` run, as those need `tsc`, ttyd, Chrome,
or rewrite the tree. Not built because CR 4.1 holds until the maintainer
lifts it.

13.2 A register of every decision of the logs, built by four agents before
Phase 1 and read by every owner. Not built: it makes every owner wait for
it, against the request that nothing waits when it need not, and the crib
of CR 8 with the search of 2.5 does its work.

13.3 One verifier per area, 22 agents. Not built: the groups of 10.2 cover
the same with fewer launches and the same rules.

13.4 Agents applying their proposed `API/` edits with the code. Not built:
B 0.3 keeps `API/` the maintainer's, and P 1.1 the API before the code.

## 14 The requirements of the request

14.1 The user's request is task 1 of the log `tmp/tasks_21_1513.md`; its
parts are that log's items 1.1 to 1.6, which are not the review's tasks 1.1
to 1.6 of this file.

14.2 D, satisfied without modification: the plans and the logs were read;
the review compares the code that should be there with the code that is
(CR 1.2, 7.4); judgement calls are not revisited and every AI assumption is
accepted (CR 2.1, 2.3.4, 2.3.5); undocumented deviations, mistakes and
shortcuts are its three classes (CR 2.3); a lot of agents, 41 tasks (CR 8 to
11); files are locked by renaming (CR 5.2); no agent waits on another but
for the finished work of 5.8 (CR 5.8); an agent coordinator runs it (CR 12);
this file was reviewed by another agent and updated from its feedback (log
`tmp/tasks_21_1513.md`).

14.3 B, modified with cause, not confirmed:

14.3.1 "have the agents decide what it really means to be done and then do
it": each agent decides its definition of done (CR 7.4) and works to it,
but within three limits the plans and rules impose: it runs nothing (CR
4.1), it changes no public interface and proposes such changes instead (CR
3.2), and it decides no question left to the maintainer (CR 2.2).

14.3.2 "things that are simply incorrect or mistakes that can be fixed":
some broken things are questions the maintainer has not answered, such as
the hooked template test of L1601 5.3.3, the mode of `test_posix.sh` (L1601
5.3.2) and the long lines the formatter cannot wrap (L2016 3.97,
3.106.21); the review lists them and does not fix them, because fixing one
chooses an option or reverses a decision (CR 2.2, 3.11, 8.2.6).

14.3.3 The project's own earlier rules, B 3.7 and B 3.9, are departed from:
CR 4.2 adds the read only commands `cmp`, `diff`, `find`, `git status` and
`git diff` to B 3.9's `mv`, `mkdir -p`, `ls`, `grep`, `wc` and `test`, so
that agents can check their own changes; CR 11.2.2 stages files, which B
3.9 forbids and the project rules allow before a formatter run; CR 7.6 puts
fragments under `tmp/review/i18n/` with an `add`, `reword` and `remove`
shape, apart from B 3.7's add only fragments of `tmp/i18n/`.

14.3.4 The project rules ask for links to screenshots in every postmortem.
Nothing runs in this review (CR 4.1), so none can be made, though tasks
1.29 and 1.30 may change what the page shows.

14.3.5 The pool of at most eight agents at once (CR 6.2) is the writer's
choice, a guard against the HTTP 429 limits that stopped agents of earlier
jobs (L2016 3.46, 3.97; L1601 3.15, 3.40); while the pool is full, a ready
agent waits for a slot.

14.4 A, unsatisfied without cause: none.

14.5 Questions for the B items:

14.5.1 Running during the review:

14.5.1.1 a) nothing run but the formatter (built);

14.5.1.2 b) the verification run of CR 13.1 after Phase 3;

14.5.1.3 c) each owner runs its Python unit modules after its fixes.

14.5.2 Questions left to the maintainer that the review meets:

14.5.2.1 a) listed, not decided (built);

14.5.2.2 b) the review builds the option a record recommends, and marks it
for the maintainer;

14.5.2.3 c) the maintainer answers them before the review is launched.

14.5.3 Changes to public interfaces:

14.5.3.1 a) proposed with their whole design, not made (built);

14.5.3.2 b) made in the code and the stub together, each recorded as an
addition of the kind of B 5.

14.5.4 The earlier working rules of 14.3.3:

14.5.4.1 a) the read only additions, the formatter's staging and the new
fragments, as written (built);

14.5.4.2 b) B 3.9's six commands only, the formatter run left to the
maintainer, and fragments added only, in `tmp/i18n/`.

14.5.5 Screenshots:

14.5.5.1 a) none, since nothing runs (built);

14.5.5.2 b) the verification run of CR 13.1 extended to the browser test's
PNGs, which needs ttyd and Windows Chrome and the maintainer's leave to run
them.

14.5.6 The pool:

14.5.6.1 a) at most eight at once, lowered after a 429 (built);

14.5.6.2 b) no cap: every ready agent is launched at once;

14.5.6.3 c) a number the maintainer names.
