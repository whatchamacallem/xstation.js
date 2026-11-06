# CLAUDE.md is a symlink to declawed.md

## Project Rules

The Project Rules section and subsections are set by the project maintainer
and must not be modified without request. The maintainer is the final
authority and decides correctness and requirements, however discrepancies are
worth fixing. No code was written by the maintainer. Authorship is a legal
issue and ascribing authorship to a non-person is a violation of project
rules. Human attribution is required for all contributions. Do not add
contributors to a commit without request.

The Lookup Accelerator is a section of declawed.md that is maintained by AI
agents and not the maintainer. Reading CLAUDE.md or declawed.md looking for
the Lookup Accelerator should not be required as it is already in your
context. You have permission to edit the Lookup Accelerator whenever errors
are observed. Do not mention the Lookup Accelerator, just fix it.

### Engineering Log and Postmortems

Maintain an engineering log for each session in `tmp/` following this
format: `tmp/tasks_$day_of_month_$24_hours_and_minutes.md`. This is formal
paperwork with no chit chat required. Text is only added and not modified. Use
ISO 2145 for tasks and do not restart numbering tasks within a single
conversation. Preserve the users literal text in the task list first, and
concatenate additional feature requests to that section. In a second section,
list your intended order of operations to execute the users requests before
starting. Then add a separate postmortem section once no subagent is still
running. Anything like a postmortem at the end of a run must include all
unfinished tasks and lost subagents. Provide the
user with the postmortem text directly in the conversation as well as
providing a link to the task doc. Provide a single sentence bug, task or other
description alongside every in-conversation postmortem reference to a numbered
item that is not itself in the postmortem. Referenced items require enough
context so that no further lookup is required. The task logs are not checked
for column width. Do not add simple questions to the log. Use the `date`
command only to name the log.

### Messages and Questions to the Maintainer

- Do not use the AskUserQuestion tool and use numbered number sub-lists per ISO
  2145.
- A message to the maintainer is understood without opening another file.
  Every identifier it uses, such as a task, question or item number, a test,
  a class or a file, comes with plain words saying what it is and why it
  matters there; a number may follow that description for reference, never
  replace it.
- Never report a problem without its solutions. Anything that waits on the
  maintainer, whether a decision, an approval, an install or a command only
  they may run, is written as a question naming what is being decided, not
  as a blocker, a problem or an instruction to run something.
- Give a question's solutions as multiple choice: each option on a line of
  its own that starts with `[ ]`, so that the maintainer can mark a choice
  `[x]`, lettered from A. Option A is the default, taken when nothing is
  marked, so A is the option recommended.
- The maintainer holds the authority and the intent; the agent holds the
  context, having written and read the code. A question carries authority
  or intent back to the agent, and never makes the maintainer gather
  context the agent already has. Before asking, spend the agent's own
  means: the rules, the plans, the code, an experiment or a measurement.
- Ask only when the answer is worth more than the maintainer's time to give
  it: when only the maintainer may decide, when the right choice depends on
  intent that nothing written settles, or when a wrong guess is costly or
  hard to undo. Otherwise decide, and report the decision so that
  overturning it is cheap. Ask first what blocks the most work, and say
  what each answer unblocks.
- Put a question in the maintainer's terms: the requirement at stake, what
  each choice does and what it costs, with the code's names as references
  only.
- Overconstrained goals introduce failure modes that are best resolved by
  conversations with the user that identify the contradictory requirements.
- Overconstrained solutions introduce failure modes that are best resolved by
  conversations with the user that identify missing long term requirements.
- Asking about deleted prose in a single sentence without further
  explanation is not allowed. A question the maintainer deleted may have
  rested on the premise of a forbidden implementation, which made it
  impossible to answer.
- Always ask to have required apt packages installed and do not use any package
  manager without request.

### Errors and Data

- No fallbacks: broke is broke. Never swallow an error, provide a default, or
  have a "just in case" branch for a case that can't happen - throw so it
  fails loud with a call stack or exit with the right Unix error code.
- Any error is a hard error, reported immediately, first failure only - no
  script collects failures, tallies of failures.
- A cascading failure is described by chaining nested `cause` entries, so
  that one JSLB object holds every error. The key is always the full name
  `cause`, never `c`: only the headers have single letter names.
- An error with no reasonable expectation of being thrown may be represented
  with the "internal error" string in place of a detailed UI string, since
  debugging will be required anyway.
- Sanitization is exclusive: each kind of bad data is identified by one layer
  only, as it passes through. The JSLB decoders are the single door for bad
  numbers, such as a number token that overflows a double, which they refuse
  at read; no other layer checks numbers.
- There must be no data loss in the logs from a hard exit because there is no
  buffering beyond a single external command.
- No fake data - every value is a measurement or plain arithmetic on one. If a
  tool can't supply a view's data, the view isn't built.

### Databases

- Nothing refuses the AI API access to the databases unless the maintainer
  requires it: no protection, permission gate or refusal is added because it
  seems safe. A refusal that was never a requirement is an
  Accidental-Requirement and violates the API agreement between the AI API
  and the databases; when the maintainer lifts it, it is removed, not argued
  for. Trashed databases are part of developing the AI API; recovery is
  added later.
- The databases are filesystem accelerators that an AI talks to easily, not
  replicas. No explicit incremental database synchronization and no database
  replication specific technique is used: entire databases may be synced by
  passing them as blobs, and otherwise the sync is lossy. The server may have
  more history than the browser, and may not have received everything in an
  orderly manner due to a connection loss. The TypeScript code is not
  responsible for database integrity across a wire. It must be possible to
  replace the database with a different kind of backing store without
  changing the protocol.
- The maximum size of everything in the system is set to be the maximum size
  of a single SQLite binary database that Chrome will store: `blob_max` of
  `settings.json`, 10 MiB, 10485760 bytes. A single database of that size is
  transmissible in a single message. This 10 MiB limit is the comprehensive
  plan for size limits: the same limit holds everywhere, since this is not a
  product that needs more than 10 MiB of AI generated content at a time.

### Source Code and Style

- Any urge to add decorative comments, "helpful" extra logging, or stylistic
  polish not asked for anywhere above is banned. Adding borders, tooltips,
  using alpha, adjusting shade, using gradients, adding unrequested style or
  redesigning on your own initiative is actively unwanted.
- Unintentional invisibility is always a bug, not a style issue.
- Never add un-requested documentation because you saw some was missing. Only
  document new code and prefer 1 line comments. Comments are not required:
  the one line limit is an allowance for sentences that improve
  comprehension and optimize code lookup times.
- Function and class identifiers carry two English names; modules and
  their test modules are the exception. The rule is overridden any time
  the maintainer specifies a different identifier.
- Do not reference `CLAUDE.md` or `declawed.md` outside this doc. Do not
  explicitly mention the tests being tested themselves in other source.

### Python and PowerShell

- Python must not run command line utilities without the maintainer's
  approval. Use the standard library instead.
- Python follows PEP 8. Constants go at the top of each `.py` file, after the
  imports, named like `_VALUE_NAME`. Code ordering requirements come before
  code style rules.
- Each `.py` file imports its modules as `import a, b, c` in alphabetical
  order on one line, or on the fewest lines that stay within 79 columns.
  `from` is banned, except that `collections.abc` and `typing` always use
  `from`, each on one line with its names in alphabetical order, and
  `from internationalization import i18n` is the expected form of the import
  of `i18n()`, expected in most modules.
- PowerShell constants go in `settings.json`.

### Formatting

- The source formatters may need to run twice to be stable. Alert the user
  if they are not.
- The formatters do not have to run except before a commit, and that run
  can be done manually.
- If a source reformatting tool can be used to fix an error then stage the
  file to be modified in git and run the tool. Then check the diff and if
  you believe there was an error the change can be reverted and applied
  manually.
- Always use the reformatting tools to reformat code when needed instead of
  doing it manually. Stage code for this reason first if safety is required.
- An explicit formatting escape, such as a `<!-- prettier-ignore -->` line, is
  legal when there is no normal solution.
- New source files are added to the reformat whitelist without asking, when
  they are created: top-level files by name, files in subdirectories by
  glob. `.md` files are never added. A source file the whitelist misses is a
  discrepancy to fix, not a file to leave unchecked. Do not suggest
  additions to the whitelist.
- Do not iterate on formatting `.md` documents. If there is a setting forcing
  you to reformat this document then it has to be disabled, inform the user.

### Git and Authorship

- Do not commit, uncommit, stage, unstage changes in git. `git` is the
  permission system for permanent changes and therefore must be reviewed by a
  user. The exceptions: files are staged before running the reformatting tools
  and unstaged once the diff is checked, and changes that become staged during
  a rename are unstaged.
- Do not look at past git commits unless asked or debugging. Deletion of code
  and documents by the maintainer may indicate a desire to remove the
  information from the conversation instead of waiting for AI to re-read it.
- Authorship is a legal issue. Ascribing authorship to a non-person, such as
  a `Co-Authored-By` trailer or a generated-by line in a commit or pull
  request, is a violation of the project rules.

### Testing

- Define 2 categories of test suite `smoke-test` and `normal-test`. Have
  `test_posix.sh` run by default whatever important test suites fit in 3
  minutes by labelling those `smoke-test` and running only them unless asked
  to run the normal tests too.
- The two official test targets for the whole project are
  `powershell/test_powershell.ps1`, which runs on Windows, and
  `test_posix.sh`, which will later run in Docker. Both call
  `python/test_all.py`, the first inside WSL.
- `python/test_all.py` is the test driver: it chooses, orders, times and runs
  the test suites. The infrastructure for testing is the code the drivers and
  tests are built from, such as the test categories and their deadline.
  `python/test_test.py` tests the infrastructure for testing, not the test
  driver.
- Using mock test objects is banned. Modules are tested in dependency order so
  that each module has tested dependencies it can use while being tested. If it
  is not possible to fully test a module without mocking environments that are
  not available then split the test suites for that module and run the later
  suites as it becomes possible to run them on real code.
- A scripted AI is expected and allowed in testing, whether it is called a
  script, a double, a mock or anything else. It is the primary exception to
  the ban on mock test objects: the test suites must run without an AI API
  endpoint, since an AI API endpoint is non-deterministic.
- ttyd's ends are asynchronous by its design: the close of its socket, the
  end of the process behind it and the output around them come in no fixed
  order relative to the lines that asked for them. This is a known limitation
  of ttyd, not a question for the maintainer, however often a race of it is
  found. Tests are designed to work with it: each waits for the end it needs,
  and none expects an order that ttyd does not keep.
- Directly changing a module's internal state during testing to emulate a
  test environment is forbidden. All tests go through the APIs being tested
  and show normal operation. They do not use isolated operation of an
  internal component in a way that violates separation of concerns.
- `internationalization` does not count as a module when labelling another
  module's test a unit test; otherwise there would be no unit tests.
- The cloud environment runs no code formatting, reformatting, scanning or
  checking: not ruff, pyright, shfmt, mdformat or `reformat.py`, and
  `test_posix.py` only with `--anthropic`, which skips all of them. A
  formatting problem never blocks the cloud environment.
- Testing ps1 is never a requirement for testing in a POSIX environment.
  The POSIX environment is tested to stand alone, not to depend on ps1.
- WSL is never a blocker for the POSIX environment.

### Remaining Rules

- Lock files by appending a per-task suffix to the filename for the duration.
- The Lookup Accelerator may only contain information that an AI agent wouldn't
already know. No line numbers are allowed as they are fragile.
- When asked to review a commit or unstaged change do not read this document.
  Report inconsistencies with this document only when encountered through
  knowledge gained when it was injected in your context. That is the only self
  healing documentation mechanism needed.
- System initialization does not have to abide by the rules for how the
  system is used, such as the one synchronization tool and its audit, unless
  it is reasonably convenient for it to do so.
- Intermediates, such as tool caches and Python bytecode, go in `build/`,
  which is gitignored. Point each tool there instead of ignoring what it
  writes beside the sources.

### Accidental-Requirements, Requirements-Data-Loss, and Requirements-Refusal

Accidental-Requirements, Requirements-Data-Loss, and Requirements-Refusal are
a set of processes observed in multiple case studies that can chain together
to make it impossible to specify requirements to an agent at all.

Accidental-Requirements starts when an agent writes code because that code is
handy, illustrative or already lying around, not because the design called for
it. Nothing in the plan motivates the code, so nothing in the plan constrains
it. Then the next session reads the tree before the plan, sees working code,
and treats that code as a decision somebody made: the shape is preserved, the
interfaces built on, the code quoted as prior art. An example nobody chose
becomes architecture by seniority.

The case studies showed three forms of it:

- One planning session surveyed the existing code before writing the plan, and
  the plan carried an older tool's command loop and commands into the new
  design. A decision made for a different problem rode in on the strength of
  its mere existence, and a later round of questions had to remove it.
- Another test plan proposed reusing an existing test driver, the stated
  reason being that the driver existed. That is reuse chosen by availability,
  not by the test plan.
- The injected project context and the memory notes described the old code in
  detail, so every session started with that code in mind before opening the
  plan. The precedent was renewed even in sessions that never read the files.

The Requirements-Data-Loss process has been observed as a compounding input
step to the Accidental-Requirements process. Accidental-Requirements can
operate independently; the pair is simply noted here because it is a wild
ride.

Requirements-Data-Loss happens when a planner reasons its way to a good API,
decides it is too much for the moment, writes down the smaller one, and leaves
at most a clause saying the larger one is for later.

- The reasoning that produced the discarded good API is gone: not in the plan,
  not in the questions, not in the code. The maintainer is left holding the
  wrong interface with no record of the right one to judge it against, and the
  next session cannot tell a better design was ever on the table.
- In the case studies, requirements were both dropped without a trace from the
  planning process, and then incorrect requirements were copied into the next
  plan and from there into the code as if settled.
- The only recovery is for the maintainer to rediscover the design, by keeping
  engineering logs and doing case studies on all planning.

This mode is worse than the first because it destroys information rather than
adding some. A deferred feature with its full design written beside the
deferral costs the maintainer one question. A deferred feature with its design
discarded costs the design.

Put more simply, first Requirements-Data-Loss knowingly produces the wrong
API. Then the Accidental-Requirements process ossifies it, because once the
reduced API is in the tree, that is the thing later sessions preserve.

Requirements-Refusal is when the agent decides not to follow instructions and
silently carries out unrequested (and thereby easily incorrect) work instead.
This behavior may be the result of the agent trying to make a better choice
for the user. However, the end point is a breakdown in communication as
unsatisfied requests accumulate and the user becomes frustrated and confused.

- The pull for an agent is hard to resist because agents are trained not to
  break what exists, and code is more concrete than a sentence in a plan, so a
  conflict between the two is settled in the code's favor without anyone
  noticing a choice was made.
- Clear instructions to work from first principles are ignored and users may
  simply not be informed, so problems remain unaddressed.

Please consider the show stopping effects of Requirements-Data-Loss,
Accidental-Requirements, and Requirements-Refusal at the same time. Check for
these every time you write code and ask if they are interfering with the
requirements specification process. Satisfying multiple requirements
simultaneously may require elaborating existing code, that is not inherently a
problem. The problem is putting the code before the requirements and not the
other way around.

Here are ways to ensure correct requirements are maintained.

- Nothing concrete exists ahead of the prose that describes it, so there are
  no Accidental-Requirements if nothing is added to the design without being
  motivated by a requirement.
- Injected context and memory notes describe current state, not design. A
  design decision found there is checked against the plan before anything is
  built on it.
- Prevent Requirements-Data-Loss by writing APIs and architecture for as much
  of the system as possible, from the top down, before ever writing any code.
- Write software from the bottom up using unit tests first, and integration
  tests second. Once the APIs are done, then the unit tests can begin.
- Reuse is chosen by the plan, never by availability. "It exists" is not a
  reason. New code is cheaper than failing to meet requirements, and so
  requirements alignment needs to be prioritized over the cost of rewrites.

When asked to write a planning doc, read all the engineering notes related to
the conversation to understand the evolution of the users requirements while
responding to questions. Analyze the users requirements throughout the process
in those planning docs. Separate the requirements into:

- `A`: Request unsatisfied or modified without cause.
- `B`: Request unsatisfied or modified with cause but without confirmation.
- `C`: Request confirmed withdrawn or modified.
- `D`: Request satisfied without modification or withdrawal.

Add both `A` and `B` class requirements in a section to the planning doc at the
end explaining whether you were able to satisfy the requirements in the new
plan, as is preferable, or if multiple choice questions have to be answered to
try to solve for all the requirements simultaneously. Tell the user that these
are unresolved in a postmortem at the end.

## Lookup Accelerator

This section was not written by the maintainer. No code was written by the
maintainer. You have permission to update this file and fix errors.

- `grep -n NAME API/README.md` finds a rule. Each rule is one line that names
  its subject, so the match is the whole rule.
- `sed -n '/^## Store/,/^## /p' API/README.md` reads one section. A section
  stands alone.
- `grep -rn NAME API/` adds the top comment of each file of `API/ts` and
  `API/python`, which holds that module's main rules. This file holds the
  rest.
- Correct a rule here when you find it wrong, and add a rule as one line that
  starts with its subject.

## Map

- Format: Files, Lanes, Line form, Line types, Limits, Bad numbers
- Behaviour: Bring up, Store, Errors, Console, ttyd protocol, queue, Tools
- Build and start: page_build, ttyd_build, vectors_make, xsjs_start, devtools,
  xsjs_screenshot
- Test: test_all, Blocks, Realms, line_case, TAP, Rungs

## Files

- `python/*.pyi`: the public names of each Python module, as stubs. A handler
  module lists one function per JSLB line type it serves, the payload as
  keyword parameters, which is how dispatch calls it.
- `ts/*.d.ts`: the public surface of each TypeScript module. A module is one
  frozen object named after it, so a file is one `declare namespace`.
- `ts/lines.d.ts`: the wire API, the payload of every JSLB line type, one
  interface each.
- `sql/substrate.sql`: DDL created on first use in every database the
  substrate opens.
- `sql/metaverse.sql`: adds the one fixed experience table and its triggers.
- `sql/verbose.sql`: the server's _verbose database. Every other table is the
  scripts'.
- `mcp/tools.json`: what tools/list returns, browser and server tools, as
  JSON-RPC results. The flag `_meta.xsjs.permit` marks a tool the UI must
  confirm.
- `settings.json`: kept equal to the top-level settings.json, which the server
  reads and sends in tap.start unmodified. PowerShell constants sit under
  powershell, which the browser receives and does not read.
- `test_setting_<suite>.json`: a suite's settings and gold, the record of
  expected results, beside the suite's module. The TypeScript suites' gold is
  built into the test page.
- `<root>/parameters.json`: debug mode and the console's verbose level, which
  are parameters of a root and not settings, by `python/switches.pyi`.

## Lanes

- wire: AI worker <-> server, bytes over tty 1.
- console: AI worker <-> ttyd's dash, ttyd's protocol over tty 0.
- ui-ai: UI thread <-> AI worker, structured clone, buffers moved.
- mcp: agent <-> MCP server, JSON-RPC 2.0, see ts/mcp.d.ts.
- http: any <-> HTTP port, one fetch per line, see ts/http.d.ts.
- dom: UI thread <-> DOM port, in the UI thread, see ts/page.d.ts.
- ui: UI thread -> UI thread, its DOM listeners and its wakes.
- ai: AI worker -> AI worker, its own pushes and wakes.
- realm: driver <-> test realm, a node process's stdio or DevTools.

## Line form

- line: one JSON object ending in CR: header at key 0, blob headers at 1 to b,
  the payload at the other keys, then the bytes of each blob the header
  counts. A field at its default is not written.
- JSLB decoder: bounds the blobs of a message by blob_max, streams a blob over
  overflow_bytes into a sink that hashes it on the way, and holds a fault met
  after finished lines for the next feed.
- header names: a header field has a short name, t, and a full name, type.
  Only header fields have single letter names; payload keys are always full
  English words.
- settings.names_full(): the one choice of the form of every line a thread
  builds: true until the settings are set, then the parameter debug, the
  thread's switches.debug_on(). So full names in debug mode and before the
  settings exist, short names otherwise.
- names_full users: the worker, tools, wire ports, MCP client, wake lines and
  the UI thread, its ui.input, ui.control_key and fault lines included.
- reply form: a reply takes the form of the line it answers. An error line
  that answers a line takes that line's form; one that answers none takes the
  names_full() form.
- full names always: code that can run before the settings exist, as the error
  overlay's fault line and bootstrap's error line.
- main_loop error form: the name form of the line it answers, else of the
  parameter debug.

## Line types

- push: a notification the receiver never answers.
- commit: a modifying store operation the browser's store sends to the server
  as a push once its own transaction has committed. A failure to apply it
  fails the server loud. The same types on the ui-ai lane are requests the UI
  submits to the AI thread's store, answered with the replies below.
- wake: a line the task manager enqueues on its own thread when every reply a
  sleeping task waited for has arrived.
- mcp: a request, with i and answered by an mcp reply, when its JSON-RPC
  message is a request, and a push when that message is a notification.
- reply `X + 1`: the reply X carries one blob.

```text
type lane from->to blobs reply
tap.start wire SERVER->AI 0 Empty; `i` is 101
error wire either 0 none; see ErrorLine
kv.put wire AI->SERVER 1 push, commit
kv.delete wire AI->SERVER 0 push, commit
doc.put wire AI->SERVER 0 push, commit
db.create wire AI->SERVER 0 push, commit
db.drop wire AI->SERVER 0 push, commit
turn.append wire AI->SERVER 0 push, commit
sql.run wire AI->SERVER 0 push, commit
db.restore wire SERVER->AI 1 push; `files` db.file next
db.file wire SERVER->AI 1 push
verbose.put wire AI->SERVER 0 push (debug)
verbose.tail wire AI->SERVER 0 VerboseTailReply
tap.line wire AI->SERVER 0 push
tap.run wire AI->SERVER 0 TapRunReply (debug)
tap.line wire SERVER->AI 0 push, tap.run's stream
mcp wire either 0 request or push
settings.put wire AI->SERVER 0 Empty (debug)
source.put wire AI->SERVER 1 Sha256Reply (debug)
system.restart wire AI->SERVER 0 push; a new tap.start
echo wire AI->SERVER any the same line, r set
settings.set ui-ai AI->UI 0 push
ui.tests ui-ai AI->UI 0 push
error ui-ai either 0 none, r set
fault ui-ai either 0 push
ai.say ui-ai UI->AI 0 TurnEnd
ai.click ui-ai UI->AI 0 TurnEnd
render ui-ai AI->UI 0 Empty
media.fetch ui-ai AI->UI 0 MediaReply + 1
media.store ui-ai AI->UI 1 MediaReply
permit.ask ui-ai AI->UI 0 PermitAnswer
console.show ui-ai AI->UI 0 Empty, once tty 0 is open
console.open ui-ai UI->AI 0 ConsoleOpenReply
console.input ui-ai UI->AI 1 push, to the writer
console.output ui-ai AI->UI 1 push
console.close ui-ai UI->AI 0 Empty
console.exit ui-ai AI->UI 0 push
console.busy ui-ai AI->UI 0 push, the AI's command runs
console.idle ui-ai AI->UI 0 push, that command ended
overlay.line ui-ai AI->UI 0 push (debug)
verbose.put ui-ai UI->AI 0 push, then forwarded
tap.line ui-ai UI->AI 0 push, then forwarded
settings.put ui-ai UI->AI 0 push, relayed to SERVER
kv.get ui-ai UI->AI 0 KvGetReply + 1
kv.put ui-ai UI->AI 1 KvPutReply
kv.delete ui-ai UI->AI 0 Empty
kv.list ui-ai UI->AI 0 KvListReply
doc.put ui-ai UI->AI 0 DocPutReply
doc.head ui-ai UI->AI 0 DocHeadReply
db.create ui-ai UI->AI 0 Empty
db.drop ui-ai UI->AI 0 Empty
turn.append ui-ai UI->AI 0 TurnAppendReply
sql.run ui-ai UI->AI 0 SqlRunReply
console.input console AI->CONSOLE 1 push: one message
console.open console AI->CONSOLE 0 ConsoleOpenReply
console.read console AI->CONSOLE 0 ConsoleReadReply
console.write console AI->CONSOLE 0 push: the AI's text
console.busy console AI->CONSOLE 0 push, output kept
console.idle console AI->CONSOLE 0 push, the turn ended
dom.choice dom UI->DOM 0 DomChoiceReply
ui.input ui DOM->UI 0 push, from a listener
ui.control_key ui DOM->UI 0 push, from a listener
ai.model_reply ai AI->AI 0 wake
ai.tool_reply ai AI->AI 0 wake
tools.*_reply ai AI->AI 0 wake, a tool's own
worker.tests ai AI->AI 0 push, runs the suites
rungs.next ai AI->AI 0 push, the wire rungs
rungs.reply ai AI->AI 0 wake, the wire rungs
settings.put ai AI->AI 0 push, relayed to SERVER
worker.console_opened ai AI->AI 0 wake
worker.settings_put ai AI->AI 0 wake
ui.turn_end ui UI->UI 0 wake
ui.permit_reply ui UI->UI 0 wake
ui.media_reply ui UI->UI 0 wake
ui.console_reply ui UI->UI 0 wake
ui.console_closed ui UI->UI 0 wake
ui.console_shown ui UI->UI 0 wake
http.request http any->HTTP 0 HttpResponse
mcp mcp AGENT<->MCP 0 request or push
tap.start realm DRIVER->REALM 0 Empty; `i` is 101
tap.line realm REALM->DRIVER 0 push
tap.pair realm REALM->DRIVER 0 push, a pair test run
verbose.put realm REALM->DRIVER 0 push (debug), B's worker
settings.set realm REALM->DRIVER 0 push, B's worker's UI lane
error realm REALM->DRIVER 0 none; fails the block
fault realm REALM->DRIVER 0 push; fails the block
```

## Limits

- blob_max: the largest database, the one hard bound of a database's size, 10
  MiB. A database file is the one blob of its db.restore line; a cache file, a
  value over overflow_bytes or the blob of a db.file line, is at most blob_max
  too.
- message size: at most line_max plus blob_max bytes.
- line_max: bounds the JSON text of one line without its blobs. A verbose.put
  holding one entry stays below it.
- first_line_max: the wire's fixed bound for the first line, 10 MiB, no blob,
  as it comes before the settings. The settings then size the decoder.
- queue byte count: a held line counts the blobs it holds in memory,
  line_bytes, so a blob streamed to a cache file counts nothing, and a
  database of blob_max with its cache files passes through as long as the
  lines' bytes are streamed.
- PRAGMA max_page_count: blob_max over the database's page_size, set before
  any statement of the store's own.
- WireTap: in debug mode logs each line by verbose.log as its jslb.line_render
  rendering. A line whose rendering would not fit one verbose.put below
  line_max, by queue.entry_fits, is logged as its header and the sizes of its
  payload and blobs only. A verbose.put it sends is not logged.

## Bad numbers

- JSLB decoders: the single door for bad numbers, in both languages; no other
  layer checks a number. At read they refuse an integer token beyond 2^53
  either way and a number token that overflows a double.
- jslb.json_decode: the same rules for JSON read from anywhere else.
- Python number check: the hooks of json.loads; a token of more than 16 digits
  is refused before int reads it.
- TypeScript number check: tokens found by scanning the text JSON.parse
  accepted, strings skipped, an integer compared by BigInt.
- document version past 2^53: the AI's problem over the MCP.

## Bring up

- first line: tap.start, a request of the server with the fixed id 101,
  carrying the settings and switches and no gold, which the page carries
  itself. The AI worker answers it with an Empty reply.
- dispatch.id_next: the id of every later request, counted per port from 102
  in both languages, as 101 is the first line's.
- settings debug reader: a store reads debug mode from the reader it was made
  with, the settings module's own store from switches.debug_on(), which each
  thread sets before its settings.
- no program but the test suites runs: the bring up is a TAP run, with no
  hello, start chain or first render.
- second tap.start: as system.restart makes, it throws wire.start_twice. Only
  a reload of the page takes a new first line.
- bootstrap options: `python3 python/bootstrap.py --root ROOT [console]
  [--main-loop NAME]`. Neither option may be given twice.
- bootstrap switches: each role reads the root's settings, then
  parameters.json by switches.parameters_load, and sets its switches by
  switches.switches_apply, so that every module and child reads the root's.
  Debug mode is switches.debug.
- bootstrap engine order: pty to raw mode; take the root's engine.lock; read
  settings and parameters; open the root's log; have the main loop file
  prepare the root; write tap.start with switches.switches_get(), in full
  names in debug mode; read the Empty reply to 101 a byte at a time; run the
  main loop.
- bootstrap imports: the modules beside it are imported inside the functions
  that use them, after their bytecode has been sent to build/.
- bootstrap debug log: traces tap.start.
- main_loop: bootstrap.py has opened the log before loop_prepare or loop_run
  runs.
- ttyd worker order: error overlay; the page's first message; the wire; the
  platform, setting globals test_sqlite3 and test_pool, cleared at start, and
  test_slots, files cleared at start that no cache holds; the test cache,
  cleared at start, as the wire's sink, so that a reply's blob over
  overflow_bytes streams to a file; worker_ai.tap_start, with the wire its
  server's port, wire_end its end and a wire.ConsolePort at the page's address
  its tty 0.
- boot run: gets the queue and, for the wire rungs, the first line and the
  page's address; in the headless worker, the queue and the start.
- boot waits: initialization waits on the platform's promises here, the one
  module that does so outside the task manager.
- worker_ai.tap_start order: set this thread's switches; set its settings from
  tap.start and, in debug mode, the harness's values; build the queue with its
  ports to the UI thread and the server; send settings.set, the settings and
  switches, to the UI thread; answer tap.start with Empty; in debug mode
  notify itself worker.tests, whose task runs the worker's suites by run,
  which sends ui.tests when its stream ends.
- tap_start pieces: it runs once per worker, so each piece is a function of
  its own, for the unit suites.
- server lane handover: a queue.Port and an end function: the ttyd page's
  wire.WirePort and wire_end, or the headless page's realm lane, a
  queue.ThreadPort, and a post of the line.
- overlay note: a piece of the program the suites build toward, run nowhere at
  bring up.
- page order: error overlay; the AI worker made from the texts of the worker
  scripts; at settings.set the UI thread's queue, whose ui.tests handler runs
  the UI thread's suites.
- page pieces: the DOM port of the player's text, clicks, control keys and
  permit buttons, the media port, the console view, the overlays, and the
  handlers that paint renders, keep media, ask permits, carry the player's
  turns and show the console.
- headless worker order: error overlay; the page's first message, with the
  worker's ends of the realm lane and the UI channel and the start, tap.start,
  the block and failfast; the platform by the ttyd worker's code;
  worker_ai.tap_start with the realm lane its server's port. It has no tty 0,
  as it has no ttyd.
- start clear: the pool and slots are cleared at start unless the start's
  clear is false, when the worker keeps what the worker before it left.
- boot file wait: with clear false, the worker opens each file of the pool's
  and slots' directories for synchronous access and closes it at once. A
  DOMException named NoModificationAllowedError ends the try, which comes
  again 10 ms later; anything else is thrown. A try refused after wait_seconds
  throws boot.files_busy, the refusal its cause.
- boot wait order: the wait comes before the pool's install, since SQLite
  keeps a failed install as the answer to every later one.

## Store

- store sync: lossy by design. Each store does its own maintenance. A
  modifying operation the browser's store commits goes to the server as a
  plain push of the same type, applied through the same methods as any caller:
  no sequence number, ordering, consistency check or reply. A line lost to a
  connection loss stays lost, and the server may hold more history than the
  browser.
- store protocol: names operations, never the storage: refs, documents, turns,
  SQL statements as text, whole databases as opaque blobs. Replacing the
  database with another backing store changes no line type and no payload. No
  tool exposes the backing store beyond routine SQL.
- commit timing: db.create and db.drop go once done, the others once the
  outermost transaction that ran them commits, in order, by
  tasks.line_notify(line, "server"). An operation that changes nothing sends
  nothing, and a rolled back transaction sends nothing.
- kv.put: carries the value's bytes as blob 1, read out of the cache file when
  the value is one, never a cache handle.
- whole databases: move only as blobs: db.restore with the database file, then
  one db.file line per cache file its rows name and the sender holds.
- db.restore handler: waits for its files lines of db.file, then db_restore
  runs, at once when files is 0. A second db.restore while one waits throws
  substrate.restore_pending. A db.file with no restore of its database waiting
  throws substrate.file_unexpected.
- db_snapshot: names only the cache files this side holds.
- db_restore: takes a cache handle or the bytes, keeping each file under the
  digest of its bytes. It tolerates rows whose cache file is missing, so the
  database works but for those values.
- cache handle: a name this store's cache holds, or a blob its sink finished.
- lost value: a row naming a cache file this side does not hold. The row
  stays, kv_list lists it, kv_put replaces it, kv_check counts nothing for it,
  and kv_get throws substrate.file_lost.
- turn compaction: browser only, inside turn_append when a user turn finds
  compact_turns of them, and by turn_compact, which the AI's scripts call
  through engine.store. Nothing of a compaction crosses the wire.
- store methods: every method is synchronous and runs inside the task that
  called it. The browser's store is given an initialized module, an installed
  pool and open cache files, and waits on nothing.
- store handlers: the ui-ai requests of the Line types table, answered with
  their replies, and the server's pushes db.restore and db.file.
- SQLITE_FULL: "database or disk is full", a write that needs a page past
  max_page_count: sqlite3.SQLite3Error in TypeScript, sqlite3.OperationalError
  in Python. Raised, never caught.
- SQLITE_AUTH: "not authorized", at prepare, from the authorizer,
  sqlite3_set_authorizer, that denies a PRAGMA max_page_count with a value:
  sqlite3.SQLite3Error in TypeScript, sqlite3.DatabaseError in Python. Raised,
  never caught. A read of the pragma, with no value, is allowed.
- schema triggers: raise the name of a string of the strings table, as
  agent.content_ambiguous, and the statement throws that string, the SQLite
  error as its cause, __cause__ in Python.

## Errors

- cascade: one object: each error line, fault line and MCP error result holds
  the latest failure's message and stack, and under cause the failure before
  it, nested, the first failure innermost. The key is always the full word
  cause.
- overlay handlers: error and unhandledrejection on both threads, and resource
  load failures in the capture phase on the main thread.
- fault line: holds the cascade of the thrown value, each Error's cause
  nested, written by error_overlay itself. On the main thread the stop
  function posts it on the channel.
- worker report: the report function sends an error line with the cascade of
  the thrown value, by dispatch.cause_make, through the end function. A UI
  fault line goes the same way, its cascade as it came.
- queue.error_line: names the error line's message and stack.
- streamed blob close: a file that fails to close after a fault carries the
  first fault: as __context__ in Python, under the innermost cause by
  utility.cause_append in TypeScript, so one cascade holds both.
- bootstrap failure: any exception writes one error line, in full names since
  it may come before the settings, and exits 1, by its return or by the
  write's own failure. Once the log is open the message is logged first.
- wire_end: never closes the socket. fn runs at the server's close, or at once
  on a socket already closed. Its error line is never held.
- wire fault: a fault while the port takes a message stops it taking more but
  leaves the socket open.

## Console

- bootstrap console role: debug mode only, else exits 1. Refuses a root not
  under /home/. Opens the root's log, gives up the pty as controlling terminal
  by TIOCNOTTY on fd 0, SIGHUP ignored for that call alone, then runs the
  sandbox through verbose.exec with a scrubbed environment.
- console verbose level: 2 when switches.verbose is true, else 1. At level 2,
  -v follows /bin/dash.
- sandbox argv: `bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp
  --tmpfs /home --tmpfs /mnt --tmpfs /root --unshare-all --new-session
  --die-with-parent --chdir /tmp python3 -I -c STEP /bin/dash`
- sandbox STEP: Python of the standard library on one line, statements joined
  by `; `: os.setsid(); fcntl.ioctl(0, termios.TIOCSCTTY, 0); SIGPIPE and
  SIGXFSZ to signal.SIG_DFL; read the environment from /proc/self/environ;
  os.execve(sys.argv[1], sys.argv[1:], given). Dash's arguments follow STEP.
- ConsoleWriter: tty 0's one writer: every line to the port passes through it
  in the order it comes.
- console attach: worker_ai.console_attach adds the wire.ConsolePort, inside a
  ConsoleWriter, as the console owner's port. console_register registers its
  UI relays with the port's console_close. Its close is pushed to the UI as
  console.exit with the code.
- AI lines: console.write text joins the AI's held rest, each line a newline
  ends goes as one console.input message, and the rest waits for a later
  write.
- tty 0 state: concluded when its output ends with the prompt `$ `; running
  from a line's submission until then, and from no prompt yet at a
  console.open.
- turn start: the AI's console.busy starts a turn on a concluded tty 0 only.
  On a running one the writer waits for the prompt, then posts the busy to the
  port and the UI, the AI's lines, and the read with what is left of its
  timeout.
- turn end: the AI's console.idle ends a started turn, posted to the port and
  the UI. On a waiting or lapsed turn it posts nothing, and the AI's waiting
  lines are dropped, never sent.
- view's lines in a turn: wait from the AI's console.busy to its console.idle,
  then go in order. On a running tty 0 they go at once, as input to the
  person's own command.
- waiting read: past its timeout it is answered as timed out with no text, and
  its turn lapses until the AI's next write or read.
- console_run: asks the player's permit unless always allowed; submits
  console.show and sleeps on tools.show_reply; starts a turn when none is on;
  types the command in it and sleeps on its output; ends the turn with
  console.idle when the read ends. Past its timeout it returns timed out with
  no output and nothing typed.
- console_write: asks its permit and shows the console; notifies console.busy
  at the first write of a turn; sends its text as one console.write; returns
  {} at once.
- console_read: asks its permit and shows the console; reads to its text or
  timeout, from where the last read of the turn ended, or from the turn's
  start in a turn that waits. A read whose output ends with the prompt sends
  console.idle to the writer, which posts it to the UI.
- console.show: shows the view as ctrl 0 does, then answers Empty once tty 0
  is open: at once when open_is(), else, when the shown view open_wanted(),
  through open_request(), whose sleep the handler takes over with the wake
  ui.console_shown, which runs open_done.
- view reopen: it asks for tty 0 and its close, and asks again once tty 0 has
  ended.
- view hidden: keeps its scrollback, colours and features.
- view fit: the rows fit the height above the band, the element after the
  container, at each show and whenever the page or the band changes size while
  shown, so every row is seen without scrolling.
- view keys: while the AI's command runs, from console.busy to console.idle,
  the view takes no keystrokes, and the person watches.
- held line: printable text and Tab join it, Backspace removes its last
  character, and Enter submits it whole with its carriage return as one
  console.input. Other control keys and escape sequences are dropped.
- paste: cut at its carriage returns, each whole line submitted in order and
  the rest held.
- echo: the held line at the cursor. It is erased before submit, before
  output, which the echo then follows, and at console.busy; console.idle draws
  it again and the person goes on typing.
- echo start: its row in the whole buffer, the viewport's base plus the
  cursor's row, held by an xterm marker, and the cursor's column. The erase
  moves to that row less the base then, and that column, and erases below, so
  an echo that scrolled the screen is erased from its own start.
- pending wrap: the program's last character is in the row's last column. The
  echo is erased from the next row, then the filled row's last cell is written
  again from xterm's buffer, a wide character from its first column, its
  attributes as SGR, then the attributes of the echo's first cell, so that the
  program's next carriage return goes back to that row.
- wrap scrolled away: an echo whose filled row is above the screen cannot have
  its wrap made pending, and is erased from the screen's top.

## ttyd protocol

- first message: JSON text; on tty 1 only AuthToken, on tty 0 also columns and
  rows, the terminal's size when tty 0 opens. ttyd runs the command once it is
  in, and ends the socket when the command exits.
- ttyd JSON: the token answer and the preferences are read by
  jslb.json_decode.
- tty 1: JSLB in the bodies of '0' messages both ways, split into input frames
  of chunk_bytes, each sent once bufferedAmount is under one chunk.
- tty 1 blobs: every blob it sends is bytes in memory, never a cache handle.
- tty 0 server messages: each is one console.output line, '0' output, '1' the
  title, '2' the preferences as JSON; the view ignores the last two.
- wire modules: wire is one of the four modules that turn platform events into
  lines.

## queue

- queue parts: its ports, the owner table, the verbose sink of the thread, and
  in debug mode a verbose line for every submit, dispatch, sleep, wake and
  reply. Its message channel only turns a platform event into the next step.
- queue order: a wake runs in its last reply's place, so the order a queue
  runs its lines in is the order its inputs gave them.
- LocalPort: hands each line as it is to the receiver of its far end, the port
  itself unless made with another as its far end. Each of two linked ports is
  held by one queue. A port already linked cannot be linked again.
- dispatch: handlers are registered by line type and version.

## Tools

- tools_browser: exactly those of API/mcp/tools.json in its order, run through
  the store.
- tool results: kv_get returns the value as text; every other tool the JSON
  text of its result: sql_run {results}, kv_put {sha256}, kv_delete, db_create
  and db_drop {}.
- kv_get, doc_get: a lost cache file fails as substrate.file_lost.
- tool failure: a tool that throws, before or after it submitted a request,
  fails the server as mcp.d.ts says.
- MCP Python methods: answers initialize, ping, tools/list and tools/call and
  takes notifications/initialized, for the revision in _PROTOCOL_VERSION, with
  the capability tools only.
- MCP TypeScript parts: the server answers the mcp line and continues a tool
  that sleeps in the wakes registered with it; the client submits its requests
  as mcp lines to the owner of its server; the client set is one list of
  prefixed tools for the agent.
- MCP exception: an exception in a request answers that request, a tool's as
  an isError result, then the server fails.

## page_build

- page pieces: html/engine.css; the bundle tsc compiles by
  ts/tsconfig.test.json, with the strings table of i18n/en-US.json in place of
  I18N_TABLE_JSON, found once; build/vectors/ written anew by vectors_make.py,
  as base64; the gold; SQLite's glue and wasm as base64; xterm.js and its css,
  from the archives third_party_fetch.py places in third_party/.
- bundle entry: ts/test_headless.ts is a file of the bundle, as ts/test_all.ts
  is, and a template's last script, a worker script, picks the entry on both
  threads.
- gold line: `var test_gold = GOLD;`, each `ts/test_setting_<suite>.json` read
  by jslb.json_decode. The harness reads it there.
- html/test.html: the ttyd page, runs test_all.suites_run() and shows its TAP
  in pre#tap_output. The start script serves the page `page_build.py test
  hyperposition-engine` builds; the wire and browser tests build from test
  too.
- html/headless.html: the driver builds build/headless.html at the start of
  the B phases by page_build("headless", "headless"), and its HTTP server
  serves it from build/.
- page_copy: writes a built page into a root with other gold on the same line,
  for a test that gives a root's page its own gold.
- node_build: in the build directory given, writes vectors/ anew, has tsc
  compile ts/tsconfig.node.json into ts/node.js, the config's outFile, and
  rewrites that file as the strict line, then `var test_vectors = ...;`, `var
  test_gold = ...;`, then the bundle with the strings table in place. Returns
  its path. Run as `node node.js BLOCK [--failfast]`.
- tsc output: both builds compile through one function that keeps it off
  stdout, the driver's TAP stream. A failed compile raises, tsc's output in
  its cause.

## ttyd_build

- ttyd_build order: remove the build directory; unpack the archive by tarfile
  into source/, the first component of each path and of each hard link's
  target stripped; apply each *.patch in name order by `patch --batch -p1 -d
  SOURCE -i PATCH`; `cmake -S SOURCE -B BUILD
  -DCMAKE_DISABLE_FIND_PACKAGE_Git=TRUE`; `cmake --build BUILD`; `BUILD/ttyd
  --version`; write inputs.json last.
- checkout_build: reads powershell.ttyd_archive, powershell.ttyd_patches and
  powershell.ttyd_build, paths from the checkout's top, by
  settings.settings_load. Under switches.anthropic the archive is
  third_party_fetch.package_path().
- ttyd_build programs: Python starts patch, cmake and the built ttyd and
  nothing else, each with stdin /dev/null and no time limit, since the build
  is outside every limit of the run. The program writes build.log itself, so a
  hard exit loses no line.

## vectors_make

- vectors_make: `python3 python/vectors_make.py` writes all vectors into
  build/vectors, the files an earlier run left removed first.
- NAME.json: every key a string and each blob's d in lowercase hex.
- number vectors: error vectors of the decoders' number rules: an integer
  token just past 2^53 either way, integers of 310 and of 4301 digits, and a
  token whose double overflows either way, each refused at read.
- sha256.json: keys sha256_55, sha256_56 and sha256_64 each name an object of
  an input of that many bytes, data, and its digest, sha256, both in lowercase
  hex.
- test_digests.json: each module's entries by name, each an input, data, and
  its digest, sha256, in the same form.

## xsjs_start

- xsjs_start.ps1: serves python\bootstrap.py with
  build\hyperposition-engine.html through ttyd in WSL on port 5768, now and at
  each Windows sign in. Run xsjs_install.ps1 once first, build the page in WSL
  by `python3 python/page_build.py test hyperposition-engine`, then run it
  from an administrator PowerShell. Run it again to change the settings;
  xsjs_stop.ps1 stops it.
- start copy: each run copies the ttyd xsjs_install.ps1 built, the engine's
  modules and seeds from python\, i18n\en-US.json, settings.json,
  provider.json and the page into ~/.cache/xsjs in Linux, and ttyd runs that
  copy on port 5769 of WSL's 127.0.0.1. A Windows port proxy forwards 5768 to
  it.
- XSJS_PROVIDER_KEY: this user environment variable, when set, is passed on to
  ttyd.
- start parameters: --verbose runs the console's shell at level 2; each
  parameter is false unless given, and anthropic is always false.
  parameters.json is written in the state folder and copied into the root.
- start with a username and password: ttyd serves HTTPS and asks for them, the
  port proxy listens on every interface, and a Windows Firewall rule lets
  other computers in. Without, the proxy listens on 127.0.0.1 only.
- TLS certificate: self-signed, so browsers warn the first time; check their
  fingerprint against the one the script prints.

## devtools

- WindowsRelay: exists as WSL's NAT networking can't reach Windows' 127.0.0.1,
  where Chrome serves DevTools, so a relay in powershell.exe carries the
  WebSocket over its stdin and stdout.
- LinuxPipe: starts /usr/local/bin/chrome-headless-shell with
  --remote-debugging-pipe, each message ended by a NUL byte, and
  XDG_CACHE_HOME set to the profile, where fontconfig caches fonts.
- Browser: has a profile of its own that goes when it does, and drives one
  page: open a URL, evaluate JavaScript, pass on the calls of a binding,
  follow the console, save a screenshot, trace, pause one of its workers in
  the debugger, close the page, pick out a trace's synchronous loads on the UI
  thread.
- Browser exit: on Linux it closes the pipe, and the call or wait under way
  raises one ConnectionError whose cause is the exit code. An exit with an
  error code that no call saw fails the Browser's end.
- devtools programs: powershell.exe, wslpath and chrome-headless-shell.
  Standard library only.

## xsjs_screenshot

- xsjs_screenshot.py: builds the page as the start script does and serves a
  debug root under build/ through build/ttyd/ttyd on a dumb terminal, its log
  going to stderr as it comes.
- screenshot checks: waits for both TAP documents in the root, fails on the
  fault screen or a failing point, checks that the page shows the last
  document and ttyd runs one bootstrap.py, saves a screenshot of the whole
  page, leaves the page and checks that the program is gone.

## test_all

- test_all: `python3 python/test_all.py [--smoke-test | --normal-test]
  [--failfast] [--stream] [--module NAME]... [--failures N] [--tty]
  [--coverage] [--anthropic] [--debug] [--verbose]`. It refuses to start as
  root. Standard library only.
- --smoke-test: the default: runs the suites labelled smoke-test. category.py
  holds the labels and options. The first failing test ends the stream.
- --normal-test: runs the suites of both labels.
- --failfast: the first failing test ends the stream.
- --stream: ends the run once the stream is checked, before the checks after
  it, and writes nothing to stdout but the stream.
- --module: runs only the suites and blocks it names, once each, in order,
  each one the category runs. It alone runs a suite or block that fails by
  design, listed apart, so that a run can check that --failures counts right.
- --failures: exit 1 unless the consumer counted exactly the N failing points
  expected, none by default. A bail out counts as one unless it follows a
  failing point.
- --tty: runs the stream on the engine tty: through tap_tty.py, bootstrap.py
  on a new pty serves tap_loop.py on a debug root in build/, which runs
  test_all.py with --stream on the same suites and --failures. Each line goes
  to stdout and the consumer as it comes. The server's stderr is written to
  this stderr at its end, and its exit code must be the stream's verdict.
- --coverage: counts lines by line_coverage.py from before any other project
  module loads, and after the passing block of the last suite that counts for
  a module, fails at that module's first line never run. A unit suite counts
  for the module of its name or those listed for it; integration and stdio
  suites and TypeScript blocks count for none. It refuses --tty.
- --anthropic, --debug, --verbose: turn on the switches of switches.py here
  and in every process the run starts. Under --anthropic the run takes no
  suite that starts a formatter, and --module refuses those.
- --verbose output: `"test_posix.py: smoke-test, <s> s"` after those checks, and
  `"the <category> run took <s> s"` at the end of a passing run.
- run start: before the first block, outside every timer, third_party_fetch.py
  fetches each pinned file not in place and ttyd_build.py builds ttyd. A
  failure fails the run there.
- stream check: the consumer raises at the first line that does not fit,
  naming the block it is in or follows. The run stops after the first block
  with a failure, and raises unless the stream ended with its parent plan or a
  bail out.
- checks after the stream: in this process and given the category,
  test_posix.py, the wire test, the browser test, ending at the first failure
  with its exit code.
- timers: every suite and block has python.test_all.module_seconds of the
  driver's gold. A smoke-test run has python.test_all.smoke_seconds in all:
  each alarm ends at that deadline at the latest, a deadline passed before a
  suite starts raises at once, and passing it fails naming the suite. A
  normal-test run has no limit of its own.
- phases, in order: Python `unit test_<module>.py`; test_tap_pair.py then
  Python integration `test_integrate_<module>.py`; Python stdio suites, which
  start bootstrap.py or mcp_stdio.py; group A unit `test_<module>.ts`;
  test_tap_pair_ts.py then group A integration `test_integrate_<module>.ts`;
  group B unit; group B integration; group C integration; the screenshot
  suite, last as it opens the whole page.
- layers: within a phase, suites run by layer, alphabetical within one. Layer
  0 is the TAP producer and consumer. Each next layer holds the suites whose
  callees' suites all sit in earlier layers.
- test_test: the one suite of harness.py, category.py and line_coverage.py.
- later suites: listed apart with the programs they wait on, not yet approved:
  in no phase, and --module refuses them.
- test_posix.py: the checks of the whitelisted files: UTF-8 with no non-ASCII
  outside _NON_ASCII_ALLOWED; the comment rules; then the formatters of
  reformat.py in a normal-test run; then the linters of their rows.
  reformat_table.json gives each extension its comment lexer, codec, checker,
  formatter and linter. --anthropic does none of this.
- synchronization audit: test_posix.py fails a ts/*.ts file outside
  _SYNCHRONIZATION_MODULES that uses await, .then(, new Promise, Atomics or
  SharedArrayBuffer outside its comments and literals.
- comment rules: a comment below a file's header is one line, not a <# #>
  comment, and outside Doxygen `code` spans holds only letters, digits, white
  space and _ENGLISH_PUNCT, unless its words are a formatter escape of
  _FORMAT_ESCAPES. The header stops within 20 lines.
- line_coverage: the lines that count hold code, by co_lines() over every code
  object found through co_consts, without the __annotate__ code. The callback
  returns DISABLE, so a location fires once, and a suite's start turns every
  location on again.

## Blocks

- block: one TypeScript test file, named by its file in ts, as test_jslb.ts,
  run under the timer of its gold.
- group A: runs in Node. Before the first block the run builds
  build/ts/node.js by page_build.node_build. Each realm runs `node
  build/ts/node.js BLOCK`, with --failfast when the first failing test ends
  the stream. It must exit 0, and is killed when its block ends. A failure
  holds its stderr in the cause.
- group A tap.start: id 101, the settings and the run's switches with debug
  on, as a debug root's engine builds it. It answers Empty, and its gold is
  the bundle's own. The text of each tap.line goes to the TAP producer's
  relay.
- local_http start: from the gold's script, before the first block that needs
  it, and stops when the stream ends, before the checks after it.
- group B: a page load of its own in the run's one chrome-headless-shell, on
  its DevTools pipe.
- group B start: before the first B block, outside every block timer, the run
  builds build/headless.html, starts the browser and adds the binding
  realm_line, which stands on every later load.
- group B page: comes from the server of the block's script if it has one, so
  that its fetches are of the page's own origin, else from that of
  typescript.test_headless.server.
- group B timer: the block loads the page, then calls realm_start by
  Runtime.evaluate. Every DevTools wait ends at the timer's end alone, so the
  gold's seconds are the block's one limit.
- group B lines: the Empty reply first, then each tap.line, to the relay. A
  worker block also sends verbose.put, whose entries go to the block's log
  with the page's console, and settings.set. Any other line fails the block.
- group B end: at the realm's last line, its parent plan or a bail out, the
  block loads about:blank, which ends the page and its worker, before the
  relay ends. A failure holds the block's log in its cause. The browser stops
  when the stream ends, before the servers, so that it holds none of their
  connections.
- group C: as group B, on the headless page that a ttyd of its own serves as
  its index, so that its ports to tty 0 and tty 1 reach that ttyd and its
  server. The block loads http://ADDRESS:PORT/.
- group C root: made in build/ before the block, outside its timer and inside
  the deadline, as the start script makes one: the modules of
  powershell.runtime_modules and the seed in python/, i18n/en-US.json,
  settings.json, parameters.json of the run's switches with debug true, and in
  main_loop/ the file typescript.BLOCK.root names under main_loop, if any.
- group C ttyd: ttyd_build's ttyd in a session of its own with the start
  script's options: --port 0, --interface, --writable, --check-origin,
  --terminal-type, --url-arg, --srv-buf-size, --index build/headless.html,
  running `python3 ROOT/python/bootstrap.py --root ROOT`, with --main-loop
  when the gold names one. Its log goes to a file of its own, from which the
  run reads its version and port. A ttyd that ends first fails the run.
- group C end: after the block's about:blank, outside its timer, the run stops
  ttyd's group by SIGTERM, kills it past
  typescript.test_headless.stop_seconds, copies its log to the block's log,
  removes the root, then fails the run if ttyd was killed or had ended first.
  A root made for a block that did not run stops before the browser, its log
  to stderr.

## Realms

- Node realm: the first line must be tap.start with i 101, decoded by
  jslb.LineDecoder over an empty substrate.CacheFiles. It sets its settings,
  switches and harness's values, answers Empty, and runs BLOCK as the one
  block of a TAP stream, each line a tap.line push the moment it is made. It
  exits 0 after run_end. Any other first line, a second line or any throw
  exits 1 with the cascade on stderr. Node writes to a pipe synchronously on
  Linux, so a hard exit loses no line.
- block kinds: a unittest module, run through TAPTestRunner.module_run; a
  block of line cases, run by line_case.block_run on the gold
  typescript.BLOCK; or a block that writes its own points as they arrive, as
  test_line_case, which may send lines of its own to the driver, as
  test_tap_pair sends tap.pair.
- test_headless page: its last script, a worker script, is
  test_headless.realm_open(), which runs on both threads and reads self.name,
  as test_all.suites_run() does.
- realm_open: on the main thread opens the lane realm; it throws without the
  binding realm_line, which the driver adds by Runtime.addBinding. In the
  worker named "ai" it brings the worker up by boot.headless_worker.
- realm_line: one call per line, with the base64 of its bytes by
  jslb.line_encode.
- realm_start: FAILFAST true means the first failure ends the stream with a
  bail out. LINE must be tap.start, decoded by jslb.LineDecoder over an empty
  substrate.CacheFiles, under the wire's first line bounds. A throw in it, an
  unknown block, a call before realm_open() or after a first call, or in a UI
  block's synchronous run, is the exception of the Runtime.evaluate call, not
  a line of the lane.
- side ui: on the main thread: settings, switches and the harness's values
  set, Empty answers tap.start, and the block runs as the one block of a TAP
  stream.
- side worker: a fresh Worker named "ai" made from the data-worker scripts.
  The page posts it the worker's ends of two channels and the start. Each TAP
  line is a tap.line on the realm lane, which in debug mode also carries
  verbose.put. The page holds a queue.ThreadPort at each end, relaying every
  line and the fault lines to the driver.
- sides lanes and workers: the page sets the settings and the harness's
  values, answers tap.start with Empty, then runs line_case.block_run on the
  gold typescript.BLOCK. In lanes it first brings the worker up with the same
  start.
- side lanes: a block gives a LanesBuild, which line_case.block_run's topology
  calls with the first line, the page's ends of the worker's two channels, its
  lane to the server and its channel to the UI thread, and the writer of a
  line to the driver. It returns the test's end.
- side workers: a block gives a WorkerRun, which runs in the task of
  worker.tests with the queue, the start and ready. line_case.block_run runs
  with a topology whose junction takes the lines each case sends.
- test_headless.worker_ready: the block's WorkerRun sends it by calling ready
  once its topology is up, since a topology whose set up takes tasks of the
  worker's queue would take the case's lines first.
- workers fault check: the fault line keeps no order with the server lane, so
  it is held and checked against the error line: the same message, stack and
  cause chain.
- Worker.terminate: ends a worker at once, unless it sent an error line whose
  fault line has not come, then when it comes. The last worker ends at the
  block's end, before the stream's last line.
- realm faults: a main thread fault goes to the driver as an error line by
  dispatch.cause_make, from the overlay's stop function. A worker's goes as an
  error line on the realm lane, then its fault line; before tap_start, its
  fault line alone.
- realm end: the realm's last line ends its TAP stream, and the driver ends
  the realm by its next page load.

## line_case

- block_run: opens the block by tap_producer.TAPTestRunner.block_start, its
  plan the number of cases; sends each case's lines through the test's end;
  collects every line that comes back; then block_end closes the block.
- point compare: the header and payload by value, each blob header but d by
  value, each blob's bytes by size and utility.sha256_hex, and each stack by
  its first line, the error's name and message.
- point failed: not ok with one diagnostic line naming the first difference, a
  line still missing or a line not expected.

## TAP

- tap_loop.py: bootstrap.py runs it from the root's main_loop directory and
  writes tap.start and reads its reply as for any main loop. loop_prepare
  reads the settings for the decoder's limits and the name form.
- tap_loop loop_run: decodes each line, refuses any reply, and serves tap.run
  alone, by `python3 test_all.py --stream` with the category, --failfast when
  asked, --failures, and --module for each suite named, its input empty. A
  blob is refused. A failure writes one error line and exits 1.
- tap.line of tap_loop: the language python, in the name form of the parameter
  debug.
- document_stats: returns the points a document's blocks plan, how many
  passed, failed and were skipped, and whether it is well formed.
- tap_consumer: reading stops at the first fault, and the counts are those of
  the lines before it. The YAML grammar is hardcoded with no YAML parser,
  refusing any attribute but duration_ms.
- tap_producer: a run that has to stop, by failfast or a failed class or
  module fixture, ends with a bail out line in place of the parent line and
  parent plan.
- block relay: the realm's version line, parent line and parent plan are
  checked by the relay alone.

## Rungs

- test_wire.py: `python3 python/test_wire.py [--smoke-test | --normal-test]
  [--anthropic] [--debug] [--verbose]`. A TAP run: the producer is
  ts/test_wire_rungs.ts in the page, and this file is the consumer. Exit 0, or
  1 at the first failed check, naming its rung.
- wire roots: echo, stock and restart, each with its own ttyd, page copy and
  load of the page. The copy's gold, by page_build.page_copy, has
  typescript.test_all.run "wire" and typescript.test_wire_rungs naming the
  root's rungs. The echo root runs --main-loop echo_loop.py.
- wire stream: one TAP stream of one block, test_wire_rungs, one point per
  rung the gold names, in its order, then the parent point and the parent plan
  1..1. The server appends each line of the page's stream to
  `<root>/tap/typescript.tap`, which test_wire.py reads through tap_consumer.py
  as it grows, a line at a time under the timer of the rung it waits for.
- rung chain: a rung waits on the network and unittest is synchronous, so a
  rung is a task chain on the worker's queue: rungs.next runs the next rung,
  which writes its point, or submits requests and sleeps with rungs.reply,
  whose handler checks the replies against the gold.
- console and lines rungs: drive their own wire.ConsolePort, since the
  worker's owner table routes console.output to the UI thread, which runs
  nothing in a wire run.
- failed rung: writes not ok with its reason, then `Bail out!` and the rung's
  name, and the chain stops: reported in the stream, not thrown on.
- session end: a rung that ends the session, unknown or restart, writes its
  point and the parent lines before its last push.
- restart_after: a TAP comment the restart rung posts after that, which the
  port holds, so that a post the port let through would reach the restarted
  server before the page's refusal of its tap.start.
- held rung: a rung named in held_rungs, restart, waits until the driver posts
  its name on release_channel, a BroadcastChannel of the page's origin, so
  that the driver reads the server before it execs.
- test_browser.py: `python3 python/test_browser.py [--smoke-test |
  --normal-test] [--anthropic] [--debug] [--verbose]`. Drives
  chrome-headless-shell by devtools.LinuxPipe, rung by rung, each under a
  timer and named by the stage of the plan it proves.
- browser roots: the suites root runs the ttyd page's bring up over TAP. The
  probe, credential and echo roots serve the headless page. Others serve the
  ttyd page. Roots are removed once the run passes and kept after a failure.
- rung labels: each root and rung is smoke-test or normal-test. A smoke-test
  run skips the normal-test rungs and starts nothing for a root with none, and
  a mislabel fails the run.
- rung gold: test_wire and test_browser read their timers, sizes and texts
  from python.test_wire and python.test_browser.
