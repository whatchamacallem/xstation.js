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
- Bad user input is an exception to the fail early and fail entirely design.
  User error interacting with the web page is not an exception class error,
  instead it is expected and designed for: the page answers it as a normal
  part of its work, with no throw and no fault screen.
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

- Ignore reformatting entirely, unless something observed is expected to
  be reformatted. Always work on formatting last, after testing.
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

- Define 2 categories of test suite `smoke-test` and `test-all`. Have
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
- A real AI provider is never tried as part of a testing run: no run,
  suite, check or demo contacts one, and the only AI any of them uses is
  the scripted AI. The maintainer gets the question of when a real
  provider will first be tried in every status report, and it is not to
  be asked: the maintainer tries one by hand, outside every run, once the
  service passes non-trivial integration tests.
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
- The current environment, Ubuntu under WSL2 on the maintainer's machine,
  is the only environment of interest. Do not ask when another platform,
  such as Docker, the cloud container, Linux off WSL or Windows, will be
  fixed or proven: another environment matters only when a change would
  break it, and then the change is the subject, not the platform.

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

- `grep -n NAME declawed.md` finds a rule. Each rule is one line that names
  its subject, so the match is the whole rule.
- `sed -n '/^## Store/,/^## /p' declawed.md` reads one section. A section
  stands alone.
- `grep -rn NAME API/` adds the top comment of each file of `API/ts` and
  `API/python`, which holds that module's main rules. This file holds the
  rest.
- Correct a rule here when you find it wrong, and add a rule as one line that
  starts with its subject.

## Map

- Format: Files, Lanes, Line form, Line types, Limits, Bad numbers
- Behaviour: Bring up, engine, Store, Errors, Console, ttyd protocol, queue,
  Tools
- Build and start: page_build, ttyd_build, vectors_make, xsjs_start,
  xsjs_serve, api_match, devtools, xsjs_screenshot
- Test: test_all, Blocks, Realms, line_case, TAP, Rungs

## Files

- `python/*.pyi`: the public names of the Python modules, as stubs, but for
  reformat, test_posix, tap_loop, echo_loop, stall_loop, vectors_make,
  failing_suite and the xsjs_screenshot programs, which have none. A handler
  module lists one function per JSLB line type it serves,
  the payload as keyword parameters, which is how dispatch calls it.
- `ts/*.d.ts`: the public surface of each TypeScript module. A module is one
  frozen object named after it, so a file is one `declare namespace`.
- tsc and the API text: ts/tsconfig.test.json and ts/tsconfig.node.json name
  API/ts/lines.d.ts alone, with no glob, as every other API/ts file repeats a
  namespace ts/ implements, so listing it beside the code would declare its
  functions twice. ts/tsconfig.api.json names every file of API/ts and no code,
  and page_build.api_check compiles it, so the API text is proved against
  itself; api_match.typescript_match then proves it against the code.
- ts/tsconfig.api.json: extends ts/tsconfig.json, sets noEmit alone, and lists
  every file of API/ts by name. No config of the chain may set skipLibCheck, or
  tsc checks no .d.ts file.
- `ts/lines.d.ts`: the wire API, the payload of every JSLB line type, one
  interface each.
- `sql/substrate.sql`: DDL created on first use in every database the
  substrate opens.
- `sql/metaverse.sql`: adds the one fixed experience table and its triggers.
  Every other table is the scripts'.
- `mcp/tools.json`: what tools/list returns, browser and server tools, as
  JSON-RPC results. The flag `_meta.xsjs.permit` marks a tool the UI must
  confirm.
- `settings.json`: kept equal to the top-level settings.json, which the server
  reads and sends in tap.start unmodified. PowerShell constants sit under
  powershell, which the browser receives and does not read.
- `test_setting_<suite>.json`: a suite's settings and gold, the record of
  expected results, beside the suite's module. The TypeScript suites' gold is
  built into the test page.
- `ts/test_setting_test_engine.json`: holds its own seed and script, as the
  bundle cannot read `python/seed/`.
- `ts/test_setting_test_engine_image.json`: holds the scene with an image and
  the script of that block; the rest of its seed is test_engine's gold.
- `python/seed/hyperposition.bmp`: the hyperposition's image, 4 px by 4 px,
  black, 24 bits, 102 bytes, under overflow_bytes, so its row holds it inline.
- `python/seed/hyperposition.json`: the scene in its encoded form, the image's
  ref at header key 1 and `{"$ref": 1}` at `image`.
- `python/seed/provider_script.json`: the analyst's table: `start` and `menu`
  hold the inputs 0 to 3 and one `otherwise` alike; `after_render`,
  `after_note`, `after_console` and `after_output` hold no inputs and one
  after_tools each, since a node holds one after_tools; `after_console` also
  holds `after_holds`, `hyperposition`, and `after_lacks`.
- analyst's texts: the seed's, repeated in `start` and `menu`, pinned by the
  golds of the C block and the demo test and not by
  `python/test_setting_test_main_loop.json`, whose `analyst` key pins the tool
  names, the note's ref, the console command and timeout, the nodes and texts
  of `after_holds` and the calls of an input whose results lack it.
- TestAnalyst: the coherence test of the seed's table in
  `python/test_main_loop.py`, which walks it as the scripted provider does, by
  `after_tools` and by `after_lacks`, against the browser tools of
  API/mcp/tools.json and the gold's `analyst`, and requires `otherwise` on
  every node with replies and `after_lacks` wherever `after_holds` is.
- `<root>/parameters.json`: debug mode and the console's verbose level, which
  are parameters of a root and not settings, by `python/switches.pyi`.
- `<root>` outside debug mode: its databases, cache, lock and the files the
  serve program copied or wrote, and nothing that records a run.

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
  the UI thread, its ui.input, ui.control_key, audit.overlay and fault lines
  included.
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
db.sync wire AI->SERVER 0 DbSyncReply, after its db.restore and db.file pushes
audit.line wire AI->SERVER 1 push (debug), a page thread's record
audit.note wire AI->SERVER 0 push (debug), a page thread's sleep
audit.tail wire AI->SERVER 0 AuditTailReply (debug)
audit.dump wire AI->SERVER 1 push (debug), the browser's views
tap.line wire AI->SERVER 0 push (debug)
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
console.show ui-ai AI->UI 0 Empty, once tty 0 opens when idle, else at once
console.open ui-ai UI->AI 0 ConsoleOpenReply
console.input ui-ai UI->AI 1 push, to the writer
console.output ui-ai AI->UI 1 push
console.close ui-ai UI->AI 0 Empty
console.exit ui-ai AI->UI 0 push
console.busy ui-ai AI->UI 0 push, the AI's command runs
console.idle ui-ai AI->UI 0 push, that command ended
audit.line ui-ai UI->AI 1 push (debug), then forwarded
audit.note ui-ai UI->AI 0 push (debug), then forwarded
audit.tail ui-ai UI->AI 0 AuditTailReply (debug), relayed to SERVER
audit.dump ui-ai UI->AI 0 push (debug), at the text 0
tap.line ui-ai UI->AI 0 push (debug), then forwarded
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
audit.overlay ui DOM->UI 0 push, from a listener
ai.model_reply ai AI->AI 0 wake
ai.tool_reply ai AI->AI 0 wake
tools.*_reply ai AI->AI 0 wake, a tool's own
tools.stored_reply ai AI->AI 0 wake, render's image is kept
worker.tests ai AI->AI 0 push, a test page's entry, runs the suites
rungs.next ai AI->AI 0 push, the wire rungs
rungs.reply ai AI->AI 0 wake, the wire rungs
settings.put ai AI->AI 0 push, relayed to SERVER
worker.console_opened ai AI->AI 0 wake
worker.settings_put ai AI->AI 0 wake
audit.tail_relayed ai AI->AI 0 wake
engine.start ai AI->AI 0 push, starts the chain
engine.initialized ai AI->AI 0 wake
engine.listed ai AI->AI 0 wake
engine.synced ai AI->AI 0 wake
engine.stored ai AI->AI 0 wake, a scene's image is kept
engine.rendered ai AI->AI 0 wake
ui.turn_end ui UI->UI 0 wake
ui.permit_reply ui UI->UI 0 wake
ui.media_reply ui UI->UI 0 wake
ui.console_reply ui UI->UI 0 wake
ui.console_closed ui UI->UI 0 wake
ui.console_shown ui UI->UI 0 wake
audit.tail_shown ui UI->UI 0 wake
http.request http any->HTTP 0 HttpResponse
mcp mcp AGENT<->MCP 0 request or push
tap.start realm DRIVER->REALM 0 Empty; `i` is 101
tap.line realm REALM->DRIVER 0 push
tap.pair realm REALM->DRIVER 0 push, a pair test run
audit.line realm REALM->DRIVER 1 push (debug), B's worker
audit.note realm REALM->DRIVER 0 push (debug), B's worker
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
- line_max: bounds the JSON text of one line without its blobs.
- audit.tail reply: holds the newest whole entries of the audit, at most count,
  oldest first, its JSON text and CR below line_max, each entry measured as the
  JSON string the reply carries, so count is a maximum.
  engine_audit.handlers_register takes line_max. An entry that does not fit
  ends the reply, older ones dropped too.
- audit_entries: the setting, the overlay's count of the audit's entries, which
  ctrl 1 asks of the server by audit.tail at each show.
- first_line_max: the wire's fixed bound for the first line, 10 MiB, no blob,
  as it comes before the settings. The settings then size the decoder.
- queue byte count: the blob bytes a queue holds are bounded by blob_max, the
  largest database. A held line counts the blobs it holds in memory,
  line_bytes, so a blob streamed to a cache file counts nothing, and a
  database of blob_max with its cache files passes through as long as the
  lines' bytes are streamed.
- PRAGMA max_page_count: blob_max over the database's page_size, set before
  any statement of the store's own.
- main_loop record: in debug mode the audit records each line read as `ai to
  server` before it is dispatched, and each push, reply and error as `server to
  ai` before it is written, never its blob bytes. The audit's own lines, every
  type under `audit.`, are never recorded.
- main_loop browser failure: engine_tap.error_take, which takes the message
  alone, runs in debug mode alone, in the echo loop too. In either mode the
  `error` line then ends the server with exit 1 and nothing written back, and
  outside debug mode with nothing written at all. That exit ends the
  connection, the close the page waits for, since the page never closes on a
  failure. engine_tap.handlers_register also runs in debug mode alone, so that
  outside it a tap.line is an unknown line, as no page sends one there, and
  `<root>/tap/` exists in debug mode alone.
- full audit: an entry that would carry `_audit.txt` past blob_max raises
  audit.full, having written nothing, and fails the server. The cure is a new
  serve, which removes the audit and costs no database.

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
- second tap.start: as system.restart makes, it throws wire.start_twice. Only
  a reload of the page takes a new first line.
- bootstrap options: `python3 python/bootstrap.py --root ROOT [console]
  [--main-loop NAME]`. Neither option may be given twice.
- bootstrap switches: each role reads the root's settings, then
  parameters.json by switches.parameters_load, and sets its switches by
  switches.switches_apply, so that every module and child reads the root's.
  Debug mode is switches.debug.
- bootstrap engine order: pty to raw mode; take the root's engine.lock, by the
  bootstrap lock wait; read settings and parameters; open the root's audit in
  debug mode; have the main loop file prepare the root; write tap.start with
  switches.switches_get(), in full names in debug mode; read the Empty reply to
  101 a byte at a time; run the main loop.
- bootstrap lock wait: _lock_take tries the root's engine.lock every
  _LOCK_POLL_SECONDS, 0.01, until _LOCK_WAIT_SECONDS, 5, the length of
  engine_wait_seconds, then closes the descriptor and raises
  bootstrap.lock_held from the last BlockingIOError. The wait and the try are
  both constants of python/bootstrap.py, as the lock comes before the settings.
  A reload takes the lock once the old engine has gone.
- bootstrap lock hangup: SIGHUP keeps its default through the wait, so a hangup
  ends the run there with no error line.
- second connection: one page per root, so a second engine on one root waits
  the 5 s, then writes its one error line, and a second tab shows the fault
  screen 5 s late.
- bootstrap imports: the modules beside it are imported inside the functions
  that use them, after their bytecode has been sent to build/.
- bootstrap record: in debug mode the audit records tap.start as `server to ai`
  before it is written, its reply as `ai to server`, and the engine role's own
  error line before it is written.
- main_loop: bootstrap.py has opened the audit in debug mode before
  loop_prepare or loop_run runs.
- main_loop seed: _seed_read reads the bootstrap script, the image and the two
  documents first, so an absent file raises FileNotFoundError before any of
  them is written. The script's row of _files goes first, then one transaction
  runs the DDL, writes the row image/hyperposition of metaverse from
  python/seed/hyperposition.bmp, the two documents, and the rows player, world
  and scene.
- ttyd worker order: error overlay; the page's first message; the wire; the
  platform, setting globals test_sqlite3 and test_pool, cleared at start, and
  test_slots, files cleared at start that no cache holds; the test cache,
  cleared at start, as the wire's sink, so that a reply's blob over
  overflow_bytes streams to a file; worker_ai.tap_start, with the wire its
  server's port, wire_end its end and a wire.ConsolePort at the page's address
  its tty 0.
- engine worker order: the ttyd worker's order, on the pool xsjs-engine-pool,
  its directory .xsjs-engine-pool, capacity 64, and the cache xsjs-engine-cache
  as the wire's sink, 64 files, each cleared at start, with no test slots and
  no globals, the boot file wait first; run gets the platform in its
  boot.WorkerStart.
- boot run: gets the queue and a boot.WorkerStart, which is the first line,
  the page's address, sqlite3, the pool and the cache that is the wire's sink;
  in the headless worker, the queue and the start.
- boot waits: initialization waits on the platform's promises here, the one
  module that does so outside the task manager.
- worker_ai.tap_start order: set this thread's switches; set its settings from
  tap.start and, in debug mode, the harness's values; build the queue with the
  reader of its blob_max and, in debug mode, its audit, then its ports to the
  UI thread and the server; send settings.set, the settings and switches, to
  the UI thread; answer tap.start with Empty; open the audit in debug mode;
  call run, in every mode.
- tap_start run: called at once after the Empty reply and outside any task, so
  it may notify but not submit, as task_submit outside a task throws
  queue.submit_outside.
- test page entries: a test page's run keeps its suites in a task of its own:
  test_all.tests_notify in debug mode, and test_headless.tests_notify always
  since first_read refuses any other start, register worker.tests and notify
  it to the thread itself, so outside debug mode no suite runs. Its task runs
  the suites, and the ttyd page's sends ui.tests when its stream ends.
- tap_start pieces: it runs once per worker, so each piece is a function of
  its own, for the unit suites.
- server lane handover: a queue.Port and an end function: the ttyd page's
  wire.WirePort and wire_end, or the headless page's realm lane, a
  queue.ThreadPort, and a post of the line.
- realm lane end: calls back at once, since the lane keeps its order and the
  page relays each line to the driver as it comes.
- audit hold: the worker's audit holds its records until audit_open, after the
  Empty reply to tap.start, as the engine role reads that reply first and
  alone. The UI thread opens its own at once, its records going to the worker,
  which forwards them.
- engine worker_run: reads provider.scripted off start.first, so a test gives
  it a false one through its argument, and a false one throws
  engine.scripted_off before anything is built, as scripted mode is the only
  one built. It runs outside every task, so it builds the store and the tools,
  registers the chain and notifies engine.start to itself.
- engine chain: engine.start submits the browser client's initialize;
  engine.initialized sends initialized and submits tools/list; engine.listed
  keeps the tools, each sleep holding its client's prefix as its state; the
  server's client then does the same over the wire; db.sync follows with the
  wake engine.synced, which checks the reply and adds the provider port; a
  scene with an image then submits media.store of its bytes with the wake
  engine.stored, and a scene with none skips that step; the first render
  follows, and the wake engine.rendered ends the chain.
- page order: error overlay; the AI worker made from the texts of the worker
  scripts; at settings.set the UI thread's queue, by page_open, which both
  pages share; the test page then sets the harness's values in debug mode and
  registers ui.tests, whose handler runs the UI thread's suites; the engine
  page runs its function at once, in every mode, outside any task, with no
  harness.
- engine_page: runs its function at settings.set, in every mode and outside
  any task, so it may notify but not submit. It can run on no headless page,
  as the headless worker awaits a HeadlessMessage, not the page's port and
  address, and the realm has already registered the overlay's stop function,
  which refuses a second.
- page pieces: the DOM port of the player's text, clicks, control keys and
  permit buttons, the media port, the console view, the overlays, and the
  handlers that paint renders, keep media, ask permits, carry the player's
  turns and show the console.
- box focus: the box takes the focus each time it opens, at the first render
  and at each turn's end, as a disabled box loses the focus, so that a person
  types on with no click. The focus leaves a terminal the turn showed. When
  ctrl 0 hides the console, which view_toggle returns, an open box takes the
  focus too, and a box still disabled in a turn takes none.
- overlay scroll: a shown overlay's pre goes to the bottom by scrollIntoView
  with block end, which scrolls whatever scrolls it: #debug on the engine page,
  where #overlays does not scroll.
- headless worker order: error overlay; the page's first message, with the
  worker's ends of the realm lane and the UI channel and the start, tap.start,
  the block and failfast; the platform by the ttyd worker's code;
  worker_ai.tap_start with the realm lane its server's port. It has no tty 0,
  as it has no ttyd.
- start clear: the pool and slots are cleared at start unless the start's
  clear is false, when the worker keeps what the worker before it left.
- boot file wait: a headless worker with clear false, on the test pool's and
  slots' directories for its start's wait_seconds, and the engine worker, on
  its pool's and cache's directories for engine_wait_seconds, open each file
  for synchronous access and close it at once. A DOMException named
  NoModificationAllowedError ends the try, which comes again 10 ms later;
  anything else is thrown. A try refused past the limit throws boot.files_busy,
  the refusal its cause.
- engine_wait_seconds: 5, a constant of ts/boot.ts above the 2.05 s measured
  release, as the wait comes before tap_start sets the settings. It guards a
  fast reload, since the platform frees a terminated worker's files later.
- boot wait order: the wait comes before the pool's install, since SQLite
  keeps a failed install as the answer to every later one.
- provider.set: deferred and not built, a push on the wire from the server to
  the AI worker, no blobs, with base_url, chat_model, image_model and key. The
  engine role reads neither the provider file nor the key's variable today.
- provider.set design: the engine role reads provider.json of the root and the
  variable the settings name, XSJS_PROVIDER_KEY, from its environment, which
  the serve program and ttyd pass on. When provider.scripted is false it
  pushes the line at once after the Empty reply to tap.start, before the
  program sends anything.
- provider.set record: the audit writes that one line as its header only, as
  its masks keep every credential out of the document.
- provider.set handler: sets the key in the provider door, keeps the three
  names for the agent and the image tool, and the http owner becomes the HTTP
  port with the provider's timeout_seconds.
- provider.set check: the request format against xAI is then checked by the
  maintainer, by hand, with their key, outside every run, by the rule.

## engine

- engine entry: engine.engine_start(), the engine page's last script, runs
  boot.engine_worker(worker_run) in the worker named ai and
  page.engine_page(page_run) on the main thread.
- engine owners: every chain line names its owner, so worker_ai.owners_make()
  has no engine. row: engine.start goes to ai, and db.sync is submitted to
  server, as the table's db. row says ai.
- engine store: the browser's store under the root /engine on the engine's
  pool, its sizes from overflow_bytes, blob_max and turn_compact_turns, with
  the UI thread's store requests and the server's restore lines registered.
- engine tools: the browser's MCP server xsjs-browser with the browser tools,
  the handler of mcp, a client hyperposition-engine under the prefix browser
  and one under server over the wire, both in one client set, and the agent
  registered with the provider owner http.
- engine provider: the script is the row /_files/provider/script.json of the
  restored store, so the scripted port is added as the http owner in the task
  that wakes on the sync's reply. The scripted port reads no key and the
  provider door throws without one, so the program sets the fixed text
  scripted. base_url, chat_model and image_model are empty strings in scripted
  mode, as the engine role reads neither provider.json nor the key's variable.
- engine sync check: engine.synced compares the reply's databases with
  store.db_list() and throws engine.sync_differs when they differ.
- engine first render: reads the world from /metaverse/world, the scene from
  the world's scene row, the scene document's subtitle and, when it has one,
  its image; a bad scene throws engine.scene_invalid. A scene with an image
  first submits engine.media_make's media.store of the image's bytes, as the
  UI's cache is empty at a load, and the wake engine.stored submits render to
  the UI thread, as the decode is asynchronous. A scene with no image submits
  render at once. A lost image fails the chain as substrate.file_lost, and a
  key with no row as substrate.key_missing.
- engine page_run: finds image, subtitle, input, permit, debug and overlays by
  id before anything else, else throws engine.element_missing, and attaches no
  audit, which the page's bring up has done.
- engine page parts: the media port as the media owner with the budget
  media_db_bytes and the timer provider.timeout_seconds; the DOM port on
  document.body as the dom owner; the console view on debug; the overlays on
  overlays; then page.handlers_register.

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
- db.sync: the browser's pull of the server's databases, a request of the AI
  worker with no blobs and no payload. The server answers with the whole of
  every database it holds: for each in name order its db.restore line and its
  db.file lines, then DbSyncReply, whose one field databases names them in that
  order.
- sync order: the browser's queue runs the pushes in order, before the reply,
  so the task that wakes on the reply finds every database restored and checks
  the list against its own. No count and no end marker is needed: the reply is
  the end.
- sync pull: the browser pulls and the server does not push, so a suite or
  rung that sends no db.sync sees no new line.
- sync lossy: the sync stays lossy by design, as the Databases rules require.
  The browser's store is rebuilt from the server at every page load, nothing
  is reconciled, and the server is the record.
- db.sync handler: engine_db.db_sync returns a dispatch.Stream: restore_lines
  of each database of store.db_list() in name order, each built from
  db_snapshot as the main loop reaches it, then DbSyncReply naming them in
  that order. It sorts db_list itself, as the store's API promises no order.
- db.sync name form: its pushes take the form of the parameter debug,
  switches.debug, as a push answers nothing; its reply takes the request's.
- Store.db_view: one database as a person reads it: each row of _kv as text,
  binary or lost, the current version of each document, the scripts' own tables
  and schema, and counts of older versions, turns and scenes with turns, which
  are not shown. The store's own tables are not listed. The same SQL text picks
  the versions in both languages.
- audit.dump: at the person's input 0 in debug mode the UI thread notifies
  audit.dump to ai before its ai.say. The browser store's handler notifies
  audit.dump to server with blob 1 the JSON of its views in name order, and
  engine_audit.audit_dump writes them under `databases of the browser`, then
  the server's own under `databases of the server`. Being of a type under
  `audit.`, neither line is recorded.
- dispatch.Stream: a handler's answer of pushes then a reply, the twin of
  dispatch.Failure, a reply then a raise. The pushes may be a generator, drawn
  as the main loop writes, so one blob is held at a time. line_dispatch sets r
  on the reply alone and leaves the pushes unread, and refuses a Stream
  returned to a notification with dispatch.notification_replied, with no
  cause. The main loop alone writes one; tap_loop's stream stays its own.
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
- kv_put of the digest a row holds: keeps the row, its cache file written
  first, so a lost file comes back.
- doc_put: takes a body already encoded: doc_decode only checks it, the row is
  its canonical JSON, and a plain reference string in a body stays plain, so a
  seed document writes its refs at key 1 on.
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
  it may come before the settings, and exits 1, by its return or by the write's
  own failure. In debug mode the engine role's audit, once open, records that
  line before it is written. The console role, which runs in debug mode alone
  and whose error line goes to tty 0, first writes the message as a note of
  console in its audit, by verbose.console_note. Outside debug mode only the
  line is written. The error lines echo_loop.py and tap_loop.py write
  themselves are not recorded.
- main_loop Stream: writes its pushes in order, then its reply. A raise while
  a stream's pushes are drawn is a handler's raise: one error line with r set,
  after the pushes already written, and no reply follows.
- wire_end: never closes the socket. fn runs at the server's close, or at once
  on a socket already closed. Its error line is never held.
- wire fault: a fault while the port takes a message stops it taking more but
  leaves the socket open.

## Console

- bootstrap console role: debug mode only, else exits 1. Refuses a root not
  under /home/. Opens the root's audit, gives up the pty as controlling
  terminal by TIOCNOTTY on fd 0, SIGHUP ignored for that call alone, then runs
  the sandbox through verbose.exec with a scrubbed environment, whose start and
  end verbose.console_note writes as notes of console.
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
- console.show: shows the view as ctrl 0 does; when the shown view
  open_wanted(), it answers Empty through open_request(), whose sleep the
  handler takes over with the wake ui.console_shown, which runs open_done; any
  other view answers Empty at once, as tty 0's writer holds the AI's lines
  until dash's prompt.
- view reopen: it asks for tty 0 and its close, and asks again once tty 0 has
  ended.
- view hidden: keeps its scrollback, colours and features.
- view fit: the rows fit the height above the band, the element after the
  container, at each show and whenever the page or the band changes size while
  shown, so every row is seen without scrolling; a height below one row leaves
  one row.
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
- ttyd compression: third_party/ttyd/patches/04_no_compression.patch removes
  `extensions` from src/server.c, so ttyd offers no websocket extension and a
  socket's `extensions` is the empty string on both ttys.
- ttyd deflate crash: with compression, a client frame that repeats an earlier
  one could fail the libwebsockets 4.3.5 assertion `priv->rx.avail_out` and end
  ttyd with -6, the page seeing 1006 with no error line. Measured at 3097,
  4129, 6193, 8257, 9289, 10321, 11353 and 12385 bytes, each 1 modulo 258,
  though not every such length. The cause is unproven.
- patch 03: the frame keeping of third_party/ttyd/patches/03_output_kept.patch
  guarded permessage-deflate's reads, which patch 04 ends; it stays as it is.

## queue

- queue parts: its ports, the owner table, the reader of its blob_max by
  limit_attach, and in debug mode its audit by audit_attach. Its message
  channel only turns a platform event into the next step.
- queue order: a wake runs in its last reply's place, so the order a queue
  runs its lines in is the order its inputs gave them.
- queue audit: in debug mode, before each line a thread sends but to the
  server, and each it receives from a port that is no queue, http, media,
  console or dom, it posts an audit.line to the owner of `audit.`, blob 1 the
  line's jslb.line_json, the payload sender, receiver and at. At each sleep it
  posts an audit.note of the replies' ids and the wake's type. Both are held
  until audit_open. The audit's own lines, every type under `audit.`, are never
  recorded, and a sleep whose wake is under `audit.` is not noted.
- queue audit masks: the record shows `<masked>` for the Authorization header
  of http.request and the token of a console.open reply, on a copy of the line,
  so that the lanes keep the real values and the rest of each line shows.
- line_render bytes: a Uint8Array nested in a value, as a BLOB column of a
  sql.run reply, renders as `<bytes "size"=N>` in TypeScript, in place, and
  line_encode still refuses it by jslb.value_refused. Python's has no such tag.
- line_json bytes: a Uint8Array nested in a value is written as the string
  `[bytes omitted: N]`, the text of audit.bytes_omitted, so the record of a
  sql.run reply with a BLOB column stays JSON.
- audit owners: the UI thread's owner of `audit.` is ai, which forwards its
  records to the server, but for audit.overlay, which the UI thread owns; the
  worker's is server, but for audit.tail and audit.dump, which the worker takes
  itself: it relays audit.tail by tail_register with the wake
  audit.tail_relayed, and the browser store's handler takes audit.dump.
- audit.overlay: ctrl 1, which the DOM port posts with no payload, as that key
  is the audit's own operation, so the queue records nothing of it; every other
  digit stays ui.control_key. The UI thread runs it and sends it nowhere: nothing
  outside debug mode, else it toggles the overlay of tty 1 and, when shown,
  submits audit.tail with the wake audit.tail_shown.
- LocalPort: hands each line as it is to the receiver of its far end, the port
  itself unless made with another as its far end. Each of two linked ports is
  held by one queue, so a line posted at one end runs on the other queue
  within the post. A port already linked cannot be linked again.
- TaskQueue synchronous mode: a line that arrives while no drain runs is run
  in that event, so a port's later answer, as media.MediaPort's after
  createImageBitmap, works on a synchronous queue.
- dispatch: handlers are registered by line type and version.
- test_integrate_queue: its ai queue has the audit attached and opened, and
  `audit.` goes to server, whose handlers keep the traced case's note and
  record and send them back as queue_ui.audit.

## Tools

- tools_browser: exactly those of API/mcp/tools.json in its order, run through
  the store.
- tool results: kv_get returns the value as text; every other tool the JSON
  text of its result: sql_run {results}, kv_put {sha256}, kv_delete, db_create
  and db_drop {}.
- kv_get, doc_get: a lost cache file fails as substrate.file_lost.
- render tool: a render that names an image first submits media.store of the
  image's bytes from the store and sleeps on tools.stored_reply, then submits
  render, as the UI's cache is empty after a reload, evicts within its budget
  and decodes asynchronously, and the worker does not know what it holds. A
  render with no image submits render at once.
- render tool failures: a lost image fails as substrate.file_lost, a key with
  no row as substrate.key_missing, a database not open as substrate.db_closed
  and a bad ref as substrate.ref_bad or substrate.ref_internal, nothing sent to
  the UI, each by tool failure below.
- page.image_missing: stays for a render line that reaches the UI thread with
  no media.store before it, which neither render path now sends.
- image bytes: kv_get hands back a cache handle, the digest as text, for a
  value over overflow_bytes, and the media port demands bytes in memory, so
  both render paths read it by cache_read on store.sink().
- tool failure: a tool that throws, before or after it submitted a request,
  fails the server as mcp.d.ts says; a permit denial and the console tools'
  refusal outside debug mode are `isError` results the tool returns, and fail
  nothing.
- console tools off: outside debug mode console_run, console_write and
  console_read return the `isError` result holding tools_browser.debug_off, the
  form of a permit denial, asking no permit and showing no console, so mcp's
  tool_run keeps no failure and the turn goes on.
- AI and the audit: the AI has no tool that reads the audit, so the audit's
  text never returns to it; a person and development agents read the file.
- script results: `engine` holds `store` and `i18n` alone; script_run returns
  {value} or {error, stack}, with no stack for a thrown value that is no Error;
  script_debug adds trace.
- script otherwise: a string the node's replies does not hold, or that is no
  decimal integer, takes the node's otherwise; with none it throws
  provider_script.input_invalid for a text that is no integer and
  provider_script.input_unknown for an integer, which stay for a test's own
  table. A content that is not a string is refused in every table.
- script after_holds: on a node holding it, tool results are answered by
  after_tools only when every result of the reply holds the text, else by
  after_lacks, whose tool calls move on as after_tools' do. A result whose
  content is not a string throws provider_script.field_invalid.
- script after pair: a node holding one of after_holds and after_lacks and not
  the other throws provider_script.after_unpaired when tool results reach it.
- box closing: the DOM port closes the box in its submit and click listeners,
  before the queue's next step, so that a second Enter or click cannot start a
  second turn.
- box bound: engine.page_run sets the box's maxLength to line_max over 8, so
  that a paste past it is cut and the turn it says fits one line at JSON's 6
  bytes a character at worst.
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
- bundle entry: ts/test_headless.ts and ts/engine.ts are files of the bundle,
  as ts/test_all.ts is, and a template's last script, a worker script, picks
  the entry on both threads.
- gold line: `var test_gold = GOLD;`, each `ts/test_setting_<suite>.json` read
  by jslb.json_decode. The harness reads it there.
- html/test.html: the ttyd page, runs test_all.suites_run() and shows its TAP
  in pre#tap_output. The start script serves the page `page_build.py test
  hyperposition-engine` builds; the wire and browser tests build from test
  too.
- html/headless.html: the driver builds build/headless.html at the start of
  the B phases by page_build("headless", "headless"), and its HTTP server
  serves it from build/.
- html/engine.html: the engine page, built as build/hyperposition-engine.html
  by `python3 python/page_build.py engine hyperposition-engine`. Its last
  script is engine.engine_start(), it has no pre, and it carries the test
  vectors and gold, since every template is filled from the same pieces.
- engine page body: canvas#image, hidden; div#debug, the console view's
  container, holding div#overlays; div#band, holding p#subtitle, a form of
  input#input, disabled, and div#permit. The image comes first so that the
  debug views show over it by coming later, and the band follows div#debug
  since the console view fits its rows above the element after its container.
- #band: the one rule of html/engine.css for the band, positioned, not
  shrinking and black, so that a shown picture, which is position fixed,
  covers none of it.
- page_copy: writes a built page into a root with other gold on the same line,
  for a test that gives a root's page its own gold.
- node_build: in the build directory given, writes vectors/ anew, has tsc
  compile ts/tsconfig.node.json into ts/node.js, the config's outFile, and
  rewrites that file as the strict line, then `var test_vectors = ...;`, `var
  test_gold = ...;`, then the bundle with the strings table in place. Returns
  its path. Run as `node node.js BLOCK [--failfast]`.
- tsc output: both builds and api_check compile through tsc_run, which keeps it
  off stdout, the driver's TAP stream. A failed compile raises, tsc's output in
  its cause, and a PATH with no tsc raises FileNotFoundError.
- api_check: tsc_run on ts/tsconfig.api.json. No page build calls it;
  test_posix.py does, last. In the default run that is among the checks after
  the stream, so a mismatch does not stop the code's blocks; a full run meets
  it first in test_test_posix_formatters, in the Python unit phase. No other
  unit suite compiles the real API text, and test_page_build reaches api_check
  in a forked child with no tsc on PATH.
- tsc_run: runs tsc --project CONFIG with the options given. bundle_compile
  gives --outFile, which a noEmit project must not get, and a test gives it a
  scratch project, as api_check takes no config.
- tsc exit code: 1 for a failed compile under noEmitOnError, 2 under noEmit, by
  tsc 5.2.2.
- gold_read: takes the folder of the gold files, and both builds pass ts/, so
  that a test can give it a bad file in a scratch directory.
- test_page_build_tsc: builds each template in a forked child through
  page_build.main, a pipe as its stdout, in place of a started python3, so
  that the count sees the lines of page_build and main; the child ends by
  SIGKILL, and a build that failed leaves no page.
- TestApiConfig: the class of python/test_page_build.py that reads
  ts/tsconfig.api.json with no tsc: its files exactly API/ts's, noEmit its only
  option, no skipLibCheck in its base.
- TestCheck: the class of python/test_page_build_tsc.py that runs tsc_run on a
  scratch .d.ts project extending the real base with noEmit: one that compiles
  writes nothing, one naming an undeclared type raises with code 2.

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

## xsjs_serve

- xsjs_serve.py: `python3 python/xsjs_serve.py [--anthropic] [--debug]
  [--verbose] [--port N] [--root PATH] [--fresh]`, the POSIX start, standard
  library only. It builds the engine page, makes the root, serves it through
  build/ttyd/ttyd, prints ttyd's log and the address on stdout and serves until
  SIGINT or SIGTERM, then stops ttyd's group and exits with ttyd's code.
- serve switches: --anthropic, --debug and --verbose turn on the switches, and
  parameters.json holds switches.switches_get().
- serve root: `~/.cache/xsjs/root` unless --root says otherwise, a relative
  --root made absolute before use, made as the start script makes one but
  without ttyd. Each run makes python/, i18n/, the files of
  powershell.root_files, the page and parameters.json anew, removes those of
  powershell.root_records, and keeps every other file, so the databases
  persist.
- serve fresh: --fresh removes the whole root first when one exists, and
  removes nothing when none does.
- root_records: the setting powershell.root_records, `_audit.txt` and `tap`, the
  records of a debug serve in a root, a file and a directory. It repeats the
  private names of audit.py and engine_tap.py. xsjs_serve.root_make and
  xsjs_start.ps1's _xsjs_start_step_install_server remove each at each start, so
  that no record outlives its serve into a serve without --debug.
- serve new record: root_make removes each of powershell.root_records that
  exists, after --fresh's removal and before anything else of the root is made,
  so each serve starts a new record and the last serve's stays readable until
  the next start.
- serve record scope: only the two starts remove the records. A page load within
  one serve adds to the same audit, under a new start heading, and the roots the
  tests make for themselves keep theirs.
- second serve on a live root: root_make runs before ttyd binds, so a second
  start removes the live server's records even when it then fails on the port.
  That server goes on writing to the removed audit with no error, and its record
  is lost. Its next tap line makes `tap` again. The Windows start stops its
  server first.
- ttyd arguments: the start script's, on 127.0.0.1 port 5769 by the settings:
  --port N, default powershell.linux_port; --interface powershell.bind_address;
  --writable; --check-origin; --terminal-type powershell.terminal_type; --index
  ROOT/powershell.engine_page; --url-arg; --srv-buf-size= srv_buf_size; then
  `python3 ROOT/python/` powershell.bootstrap_script `--root ROOT`.
- TtydServer: starts ttyd in a session of its own, its log copied to its fourth
  argument, the descriptor log_fd, and returns once its log names the port. For
  port 0 that is the port ttyd picked. ttyd takes SIGTERM when the thread that
  started it dies, by any signal at any moment, as the session ties its life to
  nothing else. That signal follows the starting thread, the main thread in
  every caller, and a death in the instant between the fork and that request is
  not covered.
- exec_prepare: runs in ttyd's child before its exec: unblocks the stop signals
  and calls prctl(PR_SET_PDEATHSIG, SIGTERM) through ctypes, the C library
  loaded at module level, before any fork. There is no check of prctl's result,
  as it fails only on a bad signal number, which a constant cannot be.
- serve address: `http://localhost:PORT/`, the port read from ttyd's log, so
  --port 0 works.
- serve log: ttyd's stdout and stderr are copied to the descriptor given as
  they come, through a thread after the port line. The program gives stdout;
  the demo test stderr, and server.txt for its plain rung; the unit suites a
  scratch file.
- serve reader that leaves: a reader of the program's stdout that leaves, as
  `xsjs_serve.py | grep -m1 http` does, ends the program by SIGPIPE at the next
  log line, and ttyd follows by its parent death signal. The program sets SIGPIPE
  to its default in its `__main__` statement alone, so that importing the module
  changes no test process's action.
- server's verbose output: ttyd's log and the address on the serve program's
  stdout, in both modes, with no JSLB: the port, each connection, each engine's
  start with its pid and each engine's end. An engine's failure text stays on
  its `error` line, which the fault screen shows. The Windows start's ttyd.log
  holds the same lines.
- engine's failure text on stdout: deferred, as the engine cannot write there
  today. Its descriptors 0, 1 and 2 are the pty, which is the wire; ttyd's
  uv_disable_stdio_inheritance closes every other descriptor across the exec;
  and `/proc/PPID/fd/2` works under the serve program but refuses with EACCES
  under the Windows runner, whose pipes are root's. The design, AUDIT_PLAN.md
  8.3: a patch of ttyd's pty_spawn duplicates its stderr before forkpty and, in
  the child, places the copy at a fixed descriptor, 3, with close-on-exec off;
  `verbose` writes a failure's text there outside debug mode, before the
  `error` line; the console role closes it before the sandbox; a test's engine
  child is given a pipe at 3. The cost is a C patch, a rebuild of ttyd and a
  pipe in each engine test.
- stop signals: serve_run blocks SIGINT and SIGTERM before ttyd starts, and
  ttyd's start unblocks them for ttyd alone, since a ttyd that inherited the
  block would never stop.
- TtydServer start window: a caller that has not blocked the signals can leave
  ttyd running until the process ends if a ctrl C lands while ttyd starts, so
  serve_run and the demo test block them first.
- signal_wait: blocks both signals and returns at either or at ttyd's end,
  leaving them blocked so that a second ctrl C cannot cut the stop short.
- serve stop: no ttyd outlives the program: a failure or signal after ttyd
  starts stops its group by server_stop.
- server_stop: stops ttyd's group by SIGTERM, by SIGKILL past 5 s, and returns
  ttyd's code, 128 plus the signal's number for a ttyd a signal ended, so 137
  after SIGKILL. A ttyd that ended first raises xsjs_serve.ttyd_ended with the
  raw code.
- serve failures: a ttyd not built raises xsjs_serve.ttyd_missing; a ttyd that
  ends before its stop raises xsjs_serve.ttyd_ended.
- test_xsjs_serve: the serve program's unit suite. It runs the real ttyd and
  the program whole in a forked child by runpy, so that the count reaches
  every line. Its ProgramCase, the forked program, serves
  test_xsjs_serve_death too, with the gold's address_pattern and page_text,
  which stay here as gold_value reads this module's id.
- test_records_removed: the test of TestRoot in python/test_xsjs_serve.py that a
  plain file under the gold's audit_name and a directory under tap_name, a file
  in it, go at a second making with fresh false and the database stays.
  test_rest_kept shows a root with no record works.
- TestParentDeath: the class of test_xsjs_serve_death: the forked program,
  serving through the real ttyd, is ended by SIGKILL and by SIGHUP's default
  action, and the port it printed stops accepting within the gold's
  gone_seconds. It polls the port and not the pid, as an orphan may stay a
  zombie for a moment. Each test builds the page with the real tsc, as the
  program does.
- test_death_reader: the test of TestParentDeath of a reader that leaves. Once
  the address is read the test closes the read end of the program's stdout, and
  a request of the gold's token_path has ttyd write a log line. The port stops
  accepting within gone_seconds and the program has ended by SIGPIPE. The answer
  stays unread, as it keeps no order with ttyd's end. ProgramCase closes the
  child's copy of the read end, without which no reader could leave.
- test_xsjs_serve_death: the suite of TestParentDeath, labelled test-all for
  its three real page builds, directly after test_xsjs_serve in the Python unit
  list, so that ttyd's death with its parent is proved only in a full run. It
  imports test_xsjs_serve for ProgramCase, and its gold holds gone_seconds,
  poll_seconds and token_path alone.
- test_xsjs_serve_death count: its _COUNTED row counts it for xsjs_serve.py, so
  a test-all count checks that module after it and a default count after
  test_xsjs_serve. No line of the module is reached by that suite alone.
- test_integrate_xsjs_serve: starts the program as a person does on port 0,
  fetches ttyd's token, stops it by SIGTERM and checks the exit code and the
  log, which it reads from stdout; stderr must be empty.

## api_match

- api_match.py: proves the text of API/ against the code, read and never imported, so a module with a fault at import fails its own suite and not this one. test_posix.py calls text_match last, after page_build.api_check, so a default run meets a difference after the stream and the cloud run skips it.
- typescript_match: tsc emits the declarations of the bundle's project into build/api_match/, code_wrap moves them under a namespace `code` with `private` and `#private` members cut, since those make a class nominal and the text never declares them, and one project compiles them beside the API text with a check file. Each pair of the check assigns a member to its twin both ways.
- typescript_match names: compared first, by names_match on members_read of each side: a member the text holds and the code lacks fails, as does one the code exports and the text lacks, a namespace with `export {};` holding only what says `export`. `function` and `const` are both a value. A class in one side is no interface in the other.
- typescript_match failure: tsc's first error in check.ts names the member by its line over _PAIR_LINES, and tsc's whole output is the cause. A failure in another file keeps tsc's own error.
- what typescript_match cannot see: parameter names, as TypeScript calls by position; any type on either side, which agrees with everything; comments. `lines` has no code, as the code is typed by it. A test module's namespace and failing_block have no text. A generic member would fail the check's compile for want of type arguments, as none exists.
- python_match: each stub of API/python against its module by ast: the public functions, classes, their methods and class fields and aliases, each signature's names, kinds, annotations, decorators and whether a parameter has a default, each class's bases. A default's value is not compared, as a stub may write `...`.
- python_match public names: those of the module's `__all__`, with the stub's own, else every name with no `_` first. In a class, a method Python names counts too.
- python_match attributes: an instance attribute the stub names must be assigned in the class, its annotation compared when both have one. One the stub does not name is the class's own.
- python_match opaque: a stub's `class Name: ...` leaves the class's members to the module.
- python_match no stub: a test module, and the modules of _STUB_ABSENT, the programs nothing imports.
- handlers_match: each handler `python/engine_*.py` registers takes as keywords exactly the fields of its payload in API/ts/lines.d.ts, a field that may be left out having a default. A payload's name is its line type spelled in words, or _PAYLOAD_NAMES. A handler that takes `**` is given the whole payload, as mcp, and has no fields to match.
- gold_match: the browser's store and tools cannot be read from Python, so the suites compare them with the gold, and this proves the gold's keys against the text: recorded_tools of test_tools_browser against the browser tools of API/mcp/tools.json, schema_statements of test_substrate_store against API/sql/substrate.sql, comments cut and white space folded.
- API/sql and settings: test_tables_recorded of test_substrate.py and test_substrate_store.ts, metaverse_check of test_main_loop.py and test_copy_equal of test_settings.py hold the real databases and settings to API/sql and API/settings.json.
- test_api_match: scratch checkouts in build/, written by checkout_write, with the real tsc: one that agrees passes text_match, and each kind of difference raises and names its member.

## devtools

- devtools_windows.py: holds WindowsRelay and path_wsl with the constants only
  they use, imports devtools, and copies a private constant both modules need
  rather than reach across modules. Its stub is
  API/python/devtools_windows.pyi.
- WindowsRelay: in devtools_windows.py, offline since 2026-10-30, kept, run by
  nothing and to be brought back later. It exists as WSL's NAT networking can't
  reach Windows' 127.0.0.1, where Chrome serves DevTools, so a relay in
  powershell.exe carries the WebSocket over its stdin and stdout.
- relay helpers: SocketChannel, address_parse, command_run, powershell_command,
  relay_script and the handshake functions stay in devtools.py, so that the
  tests that run on them stay running.
- Transport: the typing.Protocol a Browser takes, of refused_retried,
  transport_open and transport_close. Each method sits on one line, since a
  `...` on a line of its own is a line of a function that never runs, which
  line_coverage would stop at. AnyChannel, the short alias of SocketChannel and
  PipeChannel, keeps that line within 79 columns.
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
- devtools programs: chrome-headless-shell for devtools.py, and powershell.exe
  and wslpath for devtools_windows.py. Standard library only.
- devtools count: devtools.py counts under test_devtools and
  test_devtools_chrome. devtools_windows.py counts under the later suite
  test_devtools_powershell alone, by that suite's _COUNTED row, so no run
  reaches it until the suite comes back, with no exemption mark used.

## xsjs_screenshot

- xsjs_screenshot.py: builds the page as the start script does and serves a
  debug root under build/ through build/ttyd/ttyd on a dumb terminal, its log
  going to stderr as it comes.
- screenshot checks: waits for both TAP documents in the root, fails on the
  fault screen or a failing point, checks that the page shows the last
  document and ttyd runs one bootstrap.py, saves a screenshot of the whole
  page, leaves the page and checks that the program is gone.

## test_all

- test_all: `python3 python/test_all.py [--test-all] [--failfast] [--stream]
  [--module NAME]... [--failures N] [--tty] [--coverage] [--anthropic]
  [--debug] [--verbose]`. It refuses to start as root. Standard library only.
- no category option: runs the suites labelled smoke-test. category.py holds
  the labels and the one option, and its option_words gives a category's
  option for a command line, none for smoke-test.
- --test-all: runs the suites of both labels.
- --failfast: the first failing test ends the stream.
- --stream: ends the run once the stream is checked, before the checks after
  it, and writes nothing to stdout but the stream.
- --module: runs only the suites and blocks it names, once each, in order, each
  one the category runs. It alone runs a suite or block that fails by design,
  listed apart, so that a run can check that --failures counts right. Without
  --stream the run goes on to the checks after the stream, the demo test
  included.
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
- line count run: `./test_posix.sh --test-all` passes --coverage to the driver,
  so a full run fails at a module's first line never run. The default run never
  does, and the tty run stays separate, as --coverage refuses --tty. A count of
  2026-11-07 found every module complete but api_match, whose two lines a test
  then reached.
- --anthropic, --debug, --verbose: turn on the switches of switches.py here
  and in every process the run starts. Under --anthropic the run takes no
  suite that starts a formatter, and --module refuses those.
- --verbose output: `"test_posix.py: smoke-test, <s> s"` after those checks,
  and `"the <category> run took <s> s"` at the end of a passing run.
- hangup: main sets SIGHUP to its default first, as the suites expect a hangup
  to end a forked child, so a run under nohup passes.
- run start: before the first block, outside every timer, third_party_fetch.py
  fetches each pinned file not in place and ttyd_build.py builds ttyd. A
  failure fails the run there.
- stream check: the consumer raises at the first line that does not fit,
  naming the block it is in or follows. The run stops after the first block
  with a failure, and raises unless the stream ended with its parent plan or a
  bail out.
- checks after the stream: in this process and given the category,
  test_posix.py, the wire test, the browser test, the demo test, ending at the
  first failure with its exit code.
- timers: every suite and block has python.test_all.module_seconds of the
  driver's gold. A smoke-test run has python.test_all.smoke_seconds in all:
  each alarm ends at that deadline at the latest, a deadline passed before a
  suite starts raises at once, and passing it fails naming the suite. A
  test-all run has no limit of its own.
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
  reformat.py in a test-all run; then the linters of their rows; last
  page_build.api_check and api_match.text_match. reformat_table.json gives each extension its comment
  lexer, codec, checker, formatter and linter. --anthropic does none of this.
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
- test_substrate_limit: counts under --coverage for substrate.py by its row of
  _COUNTED, and as the store's last unit suite it is the one after which that
  module's lines are checked.
- TestDriverCounted: the class of python/test_integrate_test_posix.py that
  tests the driver's mapping by paths_counted, the store limit's suite
  counting for substrate.py and every suite of a test-all run counting for
  modules that exist.
- program line count: a module's `__main__` statement counts through a forked
  child that runs the file by `runpy.run_path(PATH, run_name="__main__")` with
  sys.argv set there, as test_bootstrap's TestProgram does, since the counter
  counts a forked child's lines of the suite's files and a started program's
  not at all.
- import time lines: a function a module runs at its own import runs outside
  every suite, so its lines count only when a test imports the module anew, as
  test_internationalization.py does through a symbolic link in a scratch
  checkout under build/, since the counter compares real paths.
- reply_closed test: test_bootstrap reaches bootstrap.reply_closed with a main
  loop whose loop_prepare puts a pipe nothing writes to on descriptor 0, since
  a hangup ends the engine by SIGHUP before its read returns.
- lock_wait_seconds: of test_bootstrap's gold, repeats bootstrap.py's private
  constant, as a test does not import it. test_lock_refused checks the error
  line came no sooner, and no test catches a wait made longer.
- test_lock_waited: a real child holds the lock for the gold's
  lock_held_seconds while the engine writes nothing, then the lock is freed and
  the first line follows.
- test_lock_hangup: a hangup while a real child holds the lock ends the run by
  SIGHUP.
- _lock_free: ends the holder by SIGKILL and not by closing release alone, as
  EngineChild's fork keeps a copy of that pipe end while the run lives.
- test_bootstrap run time: TestDriverHangup of test_integrate_bootstrap runs
  the whole suite again, so the lock's wait is paid twice in the default run.
- restart exec test: a forked child of `python/test_engine_system.py` sets
  sys.orig_argv and calls system_restart, so the exec's lines count; the `-c`
  program it starts writes the child's ending and kills itself.
- seed refusal test: test_main_loop.py reaches main_loop.seed_invalid and an
  absent seed file through a symbolic link to main_loop.py in ROOT/python
  beside a copy of the seed with a bad document or a file removed, loaded by
  runpy.run_path in a forked child; the module's seed directory follows the
  link and the counter counts the child's lines under the real path.
- test_test_posix_formatters: also runs test_posix.py whole as a program in a
  forked child, as the unit suite runs under --anthropic and the cloud
  environment runs no checks, so that the count reaches main and its last line.
  That run compiles the API text, so a test-all run meets an API failure here,
  before the TypeScript blocks.
- test_posix suites: test_test_posix and test_test_posix_formatters sit in the
  layer after test_api_match's, itself after page_build's suites, and
  test_integrate_test_posix after test_integrate_page_build's layer, as main
  imports api_match and page_build.

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
  worker block also sends audit.line and audit.note, which the relay lays out
  into the block's log with the page's console, and settings.set. Any other
  line fails the block. A record's blob over overflow_bytes fails it too, as
  the relay's decoder refuses a sink.
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
- test_engine: group B unit, side worker, a unittest module on a second
  synchronous queue of thread ai; its far ends are local ports, and the pieces
  run in worker_run's order, as handlers register once per realm.
- test_engine_image: group B unit, side worker, a realm of its own for the
  chain's one registration, on test_engine.bench_build with a scene whose image
  is the seed's value over overflow_bytes. The far end of ui answers render
  alone, so a media.store waits for the test's answer, which shows that no
  render comes before it, on the first render and on the render tool.
- test_engine_page: a ui side block of line cases in the B unit list, making
  the engine page's elements under the ids engine.page_run finds and running
  the program once on a real queue, the test's end its ai lane.
- test_engine_page refusal: read in topology_build before the elements exist,
  on a queue of its own, as the program's handlers register once per thread; a
  case reads it through the probe engine_probe.refusal.
- test_integrate_engine: group C, on the stock root, the engine worker on the
  real wire and tty 0, the main thread a scripted UI on a synchronous queue,
  whose `render`, `media.store` and `ui.media_reply` are the real handlers of
  page.handlers_register, on a real media.MediaPort and real elements, its
  permit.ask and console.show scripted. A case's last line waits while the
  scripted UI asks audit.tail through the worker, and each new entry of the
  tail with the label and parts of a mark of the gold's wire sends the test's
  end that mark's line first, so a case pins the wire's lines in order.
- C block picture: once the first render's reply has gone through the near
  port, the test's end gets the line test_integrate_engine.first_painted: the
  canvas's hidden, width and height and the distinct `r g b a` texts of its
  pixels by getImageData.
- C block permits: the gold's permit_choices answers each permit.ask by its
  number, so the first is accepted and the second denied; the scripted
  console.show opens tty 0 every time, so a second Accept is not a case of the
  block.
- C block marks: a mark is an entry's label and parts of its laid out JSON,
  `"key": value` with a space. wire_result_3 holds the tool's output as
  `hyperposition\\n`, escaped twice in the laid out text. A mark may name a
  line no case expects, wire_audit_own, which fails the case whose tail holds
  the audit's own operation.
- C block tail ids: each tail is a request the worker relays to the server,
  which takes one id of the worker's queue, so each later case's worker ids
  move up by one per tail before it, and the gold counts them.
- C block ceilings: the seconds of the cases sum to 115, below module_seconds,
  so that a case's own diagnostic comes before the block's timer.
- wire mcp lines: only the server client's handshake crosses the wire, since
  the seed's table calls browser tools alone; a turn's mcp lines stay in the
  worker, as `ai to ai` records.

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
  worker named "ai" it brings the worker up by boot.headless_worker; in the
  worker named "engine", by boot.engine_worker running engine.worker_run.
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
- side worker: a fresh Worker named "ai" made from the data-worker scripts. The
  page posts it the worker's ends of two channels and the start. Each TAP line
  is a tap.line on the realm lane, which in debug mode also carries audit.line
  and audit.note. The page holds a queue.ThreadPort at each end, relaying every
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
- side engine: on the main thread over a fresh worker named "engine", posted
  the page's first message of the engine bring up, its UI channel's end and
  location.href. The page sets the settings and the harness's values, answers
  tap.start with Empty, then runs line_case.block_run on the gold
  typescript.BLOCK; the block gives an EngineBuild, which takes the page's end
  of the UI channel and returns the test's end.
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
  alone, by `python3 test_all.py --stream` with --test-all for that category,
  --failfast when asked, --failures, and --module for each suite named, its
  input empty. A blob is refused. A failure writes one error line and exits 1.
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
- test_tap_loop partial output: a forked child sets PYTHONIOENCODING to
  utf-16-le, so the real driver's stdout ends one byte past its last newline
  byte, the way a test reaches the fault with no stand-in driver.

## Rungs

- test_wire.py: `python3 python/test_wire.py [--test-all] [--anthropic]
  [--debug] [--verbose]`. A TAP run: the producer is ts/test_wire_rungs.ts in
  the page, and this file is the consumer. Exit 0, or 1 at the first failed
  check, naming its rung.
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
- echo root rungs: first, echo, extensions, control, repeat, repeated, all
  smoke-test, and fit, test-all.
- extensions rung: a socket of its own at the wire's address with the
  subprotocol tty, as a port keeps its socket private. It sends nothing, so no
  program starts, and it requires `extensions` to be empty at its open.
- repeat rungs: repeat and repeated echo one blob of repeat_bytes, 8256, made
  by bytes_varied, so repeated's 8257 byte frame repeats the one before. On a
  ttyd that offers compression it ends ttyd, and the driver's log read fails
  naming the rung. A blob of bytes_counted does not crash it, as its period of
  256 changes the matches.
- stock root rungs: first, mcp, sync, commits, audit, console, lines, unknown,
  all smoke-test.
- audit rung: posts an audit.line and an audit.note of its own to the server,
  then audit.tail, whose text holds the record laid out under `ui to ai` and
  the note after it.
- wire server ends: read in the root's audit, as wire roots run in debug mode:
  the stock server's error line of the unknown push, `server to ai`, and the
  restart server's read of the page's refusal, `ai to server`, then its own
  error line.
- sync rung: on the stock root after mcp, as the page load's order has it, and
  before commits, whose db.create would make a fifth database. It submits
  db.sync to the explicit owner server, as the worker's owner table gives db.
  to ai. A wire run has no store, so rungs_run registers db.restore and db.file
  to RungChain.sync_keep, which keeps each line. At the reply the rung checks
  that the reply has no blob and names the gold's sync_databases, then that
  each database's db.restore came in that order, followed by its files lines
  of db.file, each with one blob not empty, and no other line.
- sync_databases: the stock root's four seeded databases in name order,
  python.test_wire.rungs.sync_databases, which reaches the page as
  typescript.test_wire_rungs.sync_databases.
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
- test_browser.py: `python3 python/test_browser.py [--test-all] [--anthropic]
  [--debug] [--verbose]`. Drives chrome-headless-shell by devtools.LinuxPipe,
  rung by rung, each under a timer and named by the stage of the plan it
  proves.
- browser roots: the suites root runs the ttyd page's bring up over TAP. The
  probe, credential and echo roots serve the headless page. Others serve the
  ttyd page. Roots are removed once the run passes and kept after a failure.
- test_demo.py: `python3 python/test_demo.py [--test-all] [--hold]
  [--anthropic] [--debug] [--verbose]`. Drives chrome-headless-shell by
  devtools.LinuxPipe over the engine page, rung by rung, each under a timer and
  labelled, through roots and ttyd made by xsjs_serve's functions. Exit 0, 1 at
  the first failed check, naming its rung, 130 at ctrl C, or 128 plus the
  signal's number at SIGHUP or SIGTERM.
- demo rungs: served, choice 1, choice 3, bad input, dump, audit, left and
  plain are smoke-test; reload, choice 2, console and overlay are test-all;
  they run in the order served, reload, choice 1, choice 3, bad input, choice
  2, console, overlay, dump, audit, left, plain.
- demo served: _STATE_SCRIPT reads the canvas on the page, and the served rung
  requires it shown, picture_size wide and high and of picture_colours alone;
  rung_choice_render requires it hidden after the first render tool call.
- demo reload: loads the page again at once after the served rung and waits
  for its first render, the proof of the engine worker's boot file wait and,
  when the old server has not yet exited, of the bootstrap lock wait.
- demo typing: the box is clicked once, at choice 1, with the picture shown, on
  the band that paints above the canvas, and every later input is typed with
  no click, so that the run proves typing goes on after a turn.
- demo bad input: `7`, `word` and an empty line typed in turn, each waiting for
  the `otherwise` text with the box enabled and focused; the band's text
  repeats, so the audit table's rows prove each line reached the worker; choice
  1 ends the rung, as choice 2 would let the next rung pass with no turn.
- demo root: one debug root, `build/test_demo-*/root`, with verbose false
  whatever the run's switch, as browser.console_run needs debug mode. It goes
  when the run passes, in run_finish and not in the left rung, so a failed
  plain rung keeps it, and it stays after any failure. A second root,
  `build/test_demo-*/plain`, is the plain rung's.
- demo ttyd: the demo test makes its roots and starts ttyd through xsjs_serve's
  functions, TtydServer.signal_wait serving its --hold, so what it proves is
  what the maintainer runs. DemoRun.server_start, for both roots, blocks SIGINT
  and SIGTERM from before xsjs_serve.TtydServer starts until run.ttyd is set,
  so that a stop signal cannot lose the process; no other signal is blocked, as
  TtydServer unblocks only those two in ttyd.
- demo pictures: `build/test_demo/`, emptied at each run, holds served,
  choice_1, choice_3, console and overlay as PNGs, `failed_<rung>.png` for a
  failed rung, and two texts. audit.txt, the root's audit, is copied as the
  left rung starts only under the run's --debug switch, or when a rung fails.
  server.txt holds the plain rung's ttyd log and stays; it is empty when a run
  fails before that rung.
- demo hold: --hold after a failed rung prints the error, leaves the page,
  keeps ttyd serving the root, prints the address and waits by
  TtydServer.signal_wait; the run still exits 1. After a failed plain rung it
  serves the plain root. A rung that fails once its ttyd has stopped holds
  nothing.
- demo audit table: each row of audit in the gold is a label, a line type or a
  note's words, and a fragment of an entry's laid out text, one per lane and
  direction, from choices 1 and 3, the bad input rung and the page load, the
  masks included. No fragment holds an id or a time, as a reload makes two
  loads. Every line entry's body parses as JSON, no entry is of a type under
  `audit.`, no entry is a ui.control_key of digit 1, each note of ui or ai is a
  sleep and none holds the gold's audit_wake_note, `until audit.`, and the engine
  starts once per load. In the demo test only a test-all run makes such sleeps
  and presses ctrl 1, through the overlay rung, so its smoke run does not prove
  either refusal; the C block's mark wire_audit_own does prove the sleeps' filter,
  for the worker, and test_overlay_unrecorded of ts/test_page.ts the key's.
- demo console end: the console rung ends by ctrl 0 hiding the view, which
  gives the box the focus, as the dump rung types 0 with no click.
- demo dump: typing 0 ends with its answer, and the audit holds in order
  `databases of the browser`, `databases of the server` and the `ui to ai`
  ai.say of the input. The two dumps are the same text, with the seed's image
  as `[bytes omitted: 102]` and each document at its current version alone. The
  dump's own lines are not recorded.
- demo plain: the rung after left, in a root of its own. It serves a root with
  plain_debug false by xsjs_serve.root_make and TtydServer on the page the
  served rung built. It takes the first render, choice 1 and 0, typed with no
  click, then leaves the page.
- demo plain requires: the fragments plain_port and plain_fragments in
  server.txt, waited for before the stop in no order, as ttyd logs no child's
  end after SIGTERM; ttyd_code; no name of the real root's listing fitting
  plain_absent. Its root goes when the rung passes.
- demo engine end: a page that leaves ends the engine by SIGHUP, so ttyd logs
  `process killed with signal 1, pid: `, not an exit code.
- demo audit left: run_finish requires under --debug that audit.txt exists and
  is not empty. A passing run without --debug leaves none, as
  `build/test_demo/` is emptied at each run.
- rung labels: each root and rung is smoke-test or test-all. A smoke-test
  run skips the test-all rungs and starts nothing for a root with none, and
  a mislabel fails the run.
- rung gold: test_wire, test_browser and test_demo read their timers, sizes
  and texts from python.test_wire, python.test_browser and python.test_demo.
