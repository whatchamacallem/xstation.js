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

- A run has one of four test levels, and each level holds every level below
  it. With no option `test_posix.sh` runs at the lowest, and an option only
  ever raises the level, so no two options contradict: given two, the run is
  at the higher of them.

  ```text
  option           level       what the run adds
  (none)           end-to-end  the guide tests of Isaiah Cole, Ruth Calloway
                               and Dawa, their smoke-test rungs
  --test-normal    normal      the suites and blocks labelled smoke-test, the
                               checks of test_posix.py, without formatting,
                               and the wire, browser and demo tests, their
                               smoke-test rungs
  --test-all       all         those labelled test-all, the test-all rungs,
                               the formatters and the line count
  --test-disabled  disabled    every disabled suite, test, root and rung, with
                               no line count
  ```

- Suites, blocks, roots and rungs carry one of 2 labels, `smoke-test` and
  `test-all`. The end-to-end and normal levels take the label `smoke-test`, and
  the all and disabled levels take both. The labels are not options. The
  important ones that fit in 3 minutes are labelled `smoke-test`, and the
  end-to-end and normal levels hold that deadline.
- After making changes, run the end to end tests alone, `./test_posix.sh`. Any
  further testing without the maintainer's permission is banned: a run at a
  higher level, a suite or block named by `--module` and a test program run by
  itself alike. Permission is asked for as a question.
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
- Behaviour: Bring up, engine, Store, Audit record, Errors, Console, ttyd
  protocol, queue, Tools
- Build and start: page_build, ttyd_build, vectors_make, xsjs_start,
  xsjs_serve, api_match, devtools, xsjs_screenshot
- Test: test_all, Blocks, Realms, line_case, TAP, Rungs, Guides, audit_read

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
  holds `after_holds`, `hyperposition`, and `after_lacks`. Each of its 9 calls
  is a provider_script.ScriptCall, `{arguments, call_id, name}`, all text.
- analyst's texts: the seed's, repeated in `start` and `menu`, pinned by the
  golds of the C block and the demo test and not by
  `python/test_setting_test_main_loop.json`, whose `analyst` key pins the tool
  names, the note's ref, the console command and timeout, the nodes and texts
  of `after_holds` and the calls of an input whose results lack it.
- TestAnalyst: the coherence test of the seed's table in
  `python/test_main_loop.py`, which walks it as the scripted provider does, by
  `after_tools` and by `after_lacks`, against the browser tools of
  API/mcp/tools.json and the gold's `analyst`, and requires `otherwise` on
  every node with replies and `after_lacks` wherever `after_holds` is. Its
  test_calls_form requires each call to hold exactly the three text fields of
  a ScriptCall, so a call left in the chat form fails.
- `API/python/guide_walk.pyi`: the stub of python/guide_walk.py, one of the
  modules with a stub. Its `__all__` is CheckFailed, guide_main and
  table_build, every other name of the module private, so
  api_match.python_match compares those three, CheckFailed opaque, its base
  alone. The guide programs test_guide_isaiah.py, test_guide_ruth.py and
  test_guide_dawa.py are test modules by their names, with no stub.
- `python/guides/GUIDE/`: the files of one guide, GUIDE `isaiah`, `ruth` or
  `dawa`, read from the checkout by guide_walk.table_build alone and copied
  into no root: `table.json`, the table source; `lib.js`, `spawn.js`,
  `report.js` and one file per system, the sim's scripts by the rule guide
  scripts; `prompt.txt`, the text of the universe's prompt document; and
  `introduction.txt`, the guide's introduction in guides.md, the text after
  `> ` on its one line, exactly. Each text file ends in one newline.
- `python/guides/ecs/`: the core scripts every guide sends, `init.js` and
  `step.js`, named in a table by `{"$ecs": FILE}`, read from the checkout by
  guide_walk.table_build alone, as the directory `ecs` beside the guide's.
- guide golds: `python/test_setting_test_guide_isaiah.json`,
  `python/test_setting_test_guide_ruth.json` and
  `python/test_setting_test_guide_dawa.json`, each the walk of a guide
  program under the id python.test_guide_GUIDE, and
  `python/test_setting_test_guide_walk.json`, the scratch guide of the
  builder's unit suite, its core's files and the whole table it must build.
- `guides.md`: at the checkout's top, the document of the 50 guided
  experiences, moved there from API/ts/guides.md on 2026-11-11, its content
  unchanged, by the maintainer, as no task of that session's swarm moved it.
  Its "Rules every experience follows", 1 to 6, and its "Policy and rating
  flags", 1 to 9, bind the guides; its entries 1, 2 and 4 are Isaiah Cole,
  Ruth Calloway and Dawa.
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
turn.prompt wire AI->SERVER 0 push, commit
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
  ai` before it is written, never its blob bytes: audit.line_received and
  audit.line_sent add to each blob header `sha256`, the lowercase hex digest
  of its bytes, beside its size, so that a kv.put names the value it stored. A
  page thread's record holds the size alone. The audit's own lines, every
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
  scripted. The engine role reads neither provider.json nor the key's variable,
  so the program names base_url https://scripted.invalid/v1, chat_model grok-4.7
  and image_model grok-imagine-image, so that each request is one xAI would
  take and none can resolve.
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
  compact_turns of them, and by the store's turn_compact. Its summary is one
  row `[{role, content}]` at n 1, role system. Nothing of a compaction crosses
  the wire, and the next model request starts a new chain.
- script compaction: disabled for now, by the maintainer on 2026-11-09:
  engine.store holds no turn_compact, so no script compacts, and the seed's
  prompt names none. Compaction by a script is not to be tested yet: no suite,
  block or rung has a script compact. The store keeps turn_compact, as the
  threshold compaction shares its private #turns_compact.
- script compaction return: engine.store gains turn_compact again, with a test
  in test_agent's TestChain of a script that compacts the scene's first turn
  within a turn, whose next request restarts with the prompt, the summary, the
  reply's items, reasoning kept, and the script's output, then chains with the
  next user item alone; and an answer to turn_compact through calls.
- turn_compact through calls: a turn_compact through a reply row with calls
  but not through the rows of their outputs leaves call outputs answering no
  call at the log's head, after the summary, so the next request, a restart, is
  refused by the scripted port at `json.input[k].call_id`, and likely by xAI.
  The threshold compaction cannot do it, as it compacts through the last row
  and a reply with calls is stored with its outputs. Only a script could, and
  a script's compaction is disabled, so the store adds no refusal of its own.
- conversation: the log of one scene, its system prompt then its turns, which
  turn_list returns whole in both stores. A new scene is a new conversation.
- turn row: the content of a row of _turn is a JSON array of input items of
  the Responses API: the player's turn `[{role, content}]`, role user; a reply
  its output items as the door kept them, reasoning included, role assistant;
  each call's output a row of its own, `[{type: "function_call_output",
  call_id, output}]`, role tool; a prompt message `[message]`; the summary.
  turn.append carries the items, and turn_list in TypeScript parses them.
- row key order: the browser writes a row by json_canonical, which puts integer
  keys first and keeps every other key in insertion order, sorting none, so
  every comparison of rows parses them first. The server, by engine_turn,
  stores compact JSON in the order the items came, which equals the browser's
  row while no object holds an integer key.
- agent chain: agent's TurnLoop keeps in memory, per scene, the id of the last
  response and utility.json_text of the parsed content of each row its context
  holds. A request whose log holds more rows than the chain and begins with
  them sends the items of the rows after them, with previous_response_id; any
  other deletes the chain and sends every row's items with none.
- chain restart: a conversation's first call, the first after a page load, as
  the chains live in memory, and the first after the threshold's compaction,
  all start a chain by that one comparison.
- chain kept: once a reply's row is stored the loop reads the log back. When it
  begins with the request's rows and the next row is the reply's, at the n
  turn_append returned, the chain becomes the response's id and those rows;
  otherwise it is deleted, so a log a script changed under the turn restarts
  the next request. A reply with calls is stored with its outputs in one
  transaction, so the next request sends the outputs alone.
- chain deferred: a chain kept across page loads, its response id committed
  beside the log, and a restart of a chain older than 29 days, as xAI keeps a
  response 30 days, are written whole in AUDIT_PLAN.md 6.6 and not built.
- agent prompt: agent's turn_start stores the prompt when the scene holds none,
  before the player's turn and so before the first model call and the first
  possible tool call. A chain's first request sends it as the log's leading
  items and a chained request does not, so it goes once per chain: once per
  conversation, page load and compaction.
- prompt edit: an edit of a prompt document reaches the next new conversation,
  never one that holds its prompt.
- turn_prompt: stores the prompt's messages as rows of _turn at n 0 and below,
  each `[message]`, role system, the last at 0, and sends the messages
  themselves as one turn.prompt push, which the server stores as rows alike. A
  second prompt of one scene fails on the table's key, `UNIQUE constraint
  failed`, in both stores.
- turn_prompted: the flag: whether the scene's row at n 0 exists. As a row of
  the log it cannot disagree with the text, and it travels with the database in
  a whole sync, so a reload stores no second prompt. A turn.prompt line lost to
  a connection loss stores the prompt again after the next load, as the server
  never held it. The browser's store alone reads it; the server only applies.
- prompt and turns: the turns count from 1, compaction counts and deletes n > 0
  alone, and db_view's counts of turns and scenes are of n > 0, so the prompt is
  in no count and outlives every compaction, and the chain a compaction starts
  sends the prompt, the summary, then the rows after it.
- seed prompt: python/seed/prompt.json says nothing the tool list says: the
  tools' names, prefixes and debug mode reach the model in every model request
  outside debug mode, chained or not, as the agent sends the tools on each. In
  debug mode no request lists them, by DEBUG_MODE_TOOL_LIST_OMITTED.
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

## Audit record

- audit.ShownLog: what the document shows of each conversation: items, a dict
  of each conversation's input items keyed by its Document-Ref, a model
  request body's prompt_cache_key or a commit payload's scene; last, the
  conversation last moved; tools, the tool list last shown; output, the last
  model reply's output. tools and output are one of each, shared by every
  conversation. Its line_thin is the writer's and its line_whole the reader's.
  Each moves the same state, last included, on the same lines in the same
  order, so the second undoes the first.
- ShownLog lanes: three are read: `ai to http`, a model request, whose body
  holds input; `http to ai`, a model reply, whose body holds output; `ai to
  server`, a turn.prompt or turn.append commit. An image request and its reply
  hold neither and are written as they are.
- ShownLog counts: each is measured by comparing values as parsed JSON, so key
  order does not matter, and never assumed, so a line that differs writes what
  differs. A count of items compares with its conversation's items, and one of
  a conversation the document has not shown yet with the items of the one last
  shown, so a second scene's prompt, the same text, is written as a count and
  the record holds the prompt once. A move between scenes and back writes
  nothing again, as each keeps its own items. A line of no count reads as
  whole, as a document older than it.
- input_kept: a model request is written with input_kept, always, then input,
  the rest. With no previous_response_id it counts the leading items equal to
  the conversation's items from their start, which become the whole input;
  with one, the largest k whose first k items equal the last k of the
  conversation's items, which gain the rest.
- content_kept: a turn.append is written with content_kept, only when above 0,
  the count of its leading items equal to the held output, then content, the
  rest; the scene's items gain the whole content. A reply's row so writes
  content_kept and an empty content, its items being in the reply's `http to
  ai` record.
- messages_kept: a turn.prompt is written with messages_kept, always, its
  leading messages equal to the scene's items from their start, or to those of
  the conversation last shown when the document has not shown the scene, then
  messages, the rest, and the scene's items become the messages.
- tools_kept: a model request's tool list equal to the one shown, and a reply's
  echo of it, are written as its count. The text DEBUG_MODE_TOOL_LIST_OMITTED is
  no list, so it is written whole and the list shown stays. A request's tools become those shown; a
  reply's echo replaces nothing. A tool list that changed is written whole.
- ShownLog order: as each commit precedes its request on the wire, a request
  usually writes input_kept alone and an empty input. A chain's restart writes
  its input from the first item that differs from its conversation's items,
  so after a compaction the summary, the one item no commit carries, and all
  after it.
- ShownLog reload: a process's first record on one of the three lanes reads
  the document back by line_whole through all three, `http to ai` included, so
  a page load and a system_restart keep what the last process wrote, each
  conversation's items and last alike. It parses each entry by
  jslb.json_decode, as a live record is parsed, so an integer key compares
  equal after a reload, the body cut at its first `}` at the left margin, as
  json.dumps indents every inner brace and escapes every newline, so that the
  blobs line is left out. A record on a lane before audit_open raises
  audit.not_open and reads nothing. No page thread keeps this state, as each
  load starts with nothing.
- record_text: stays whole and keeps no state, for a block's log, which has no
  document.
- audit_read whole lines: entries_parse makes each line whole through ShownLog,
  so ReadEntry.line is the line as sent, ReadEntry.body the entry as written and
  ReadEntry.kept the count written, input_kept, content_kept or messages_kept.
  Every count of a model call reads the former. It parses by json, not
  jslb.json_decode, as line_whole slices by the written counts and compares
  nothing, so a line's header stays at the text key "0".
- prompt_recorded: the copies of the system prompt, the content of the first
  model call's first item, in the written bodies of the three lanes, which
  --check holds to at most one. A dump is a person's request and holds the
  prompt document as a row, so it is not counted.
- audit size: on Chat Completions, chat requests held 86 percent of a long
  audit before messages_kept, 1185230 of 1373079 bytes in
  tmp/audit_tools_09_0633.txt.

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
- tool name: `prefix_name`, as browser_sql_run, the mark an underscore, since xAI
  publishes no pattern and OpenAI's, `^[a-zA-Z0-9_-]{1,64}$`, refuses a dot. A
  prefix holds no underscore, so the first one ends it.
- DEBUG_MODE_TOOL_LIST_OMITTED: provider.tools_omitted, the text a model
  request holds at tools in debug mode in place of the tool list, by the
  maintainer on 2026-11-09. It replaces the 91 percent of the request bytes the
  tool list was, 247500 of 269797 B in the long audit of AUDIT_PLAN.md 8.10,
  and the fake's echo of it. agent.handlers_register and
  provider_script.ScriptPort each take a debug reader, switches.debug_on in the
  engine. Outside debug mode the list is sent whole, as xAI needs it, and the
  fake refuses the text at json.tools; in debug mode the fake refuses a list.
  A debug mode request to xAI itself would be refused, so a hand test against
  xAI runs outside debug mode, with no audit.
- model request: `POST {base_url}/responses`, the headers Authorization and
  Content-Type alone, the body model, previous_response_id when chained, input,
  tools, DEBUG_MODE_TOOL_LIST_OMITTED in debug mode, tool_choice auto,
  prompt_cache_key and include, in that order.
  instructions and store are never sent, so xAI keeps each response, as a chain
  needs.
- prompt_cache_key: in the body of every model request, the scene's
  Document-Ref, by which xAI routes a conversation to the server holding its
  cache. It replaces the header x-grok-conv-id, which no request sends.
- reasoning item: include asks for `reasoning.encrypted_content`, and the door
  keeps each output item as parsed, every field xAI sent, so the reasoning is
  stored in the reply's row and sent back when a chain restarts with the whole
  log, keeping the history the cache needs unchanged.
- model reply: model_response refuses by provider.field_invalid, in order, an
  id or model not text, a status but completed or incomplete, an output not an
  array, then per item its type, a reasoning item's id, a message's role and
  output_text parts, a call's call_id, name and arguments. text_join gives null
  for an output with no message, which the agent throws as agent.reply_empty.
- scripted place: the port holds one place in the table, the current node and
  the calls pending, for the whole port and not per chain, as a place per
  conversation would send a new scene's first turn to the start node. It moves
  only once every check has passed.
- script choice: the last input item picks the reply. Call outputs ending the
  input take the after path of the pending calls, refused by results_unasked or
  results_unmatched; any other last item must be a user message with no type,
  else role_unexpected, naming the item as JSON, then results_pending while
  calls are pending, then input_invalid for a content that is not a string.
  That message's text in normal form, its ends trimmed by JavaScript's trim
  and its letters lowered by toLowerCase, picks the reply the current node's
  replies hold under that key, by script keys, else the node's otherwise, by
  script otherwise. Nothing tells digits apart from other text.
- script keys: a reply key is any text in normal form, a number, a word or a
  phrase, as `60`, `yes` or `i'll fly, you walk`, its punctuation kept, so
  `what if i hate it?` matches "What if I hate it?" and not "what if i hate
  it". The ScriptPort constructor, after checking that start is a node, walks
  every node's replies in the table's order and throws
  provider_script.key_unnormal for the first key whose normal form is not
  itself, naming the node and the key as JSON text so that outer space shows,
  as no input could match that key. The seed's keys are digits, already in
  normal form, so the seed's table and the demo answer as before.
- script quote: a reply's quote is a path of members joined by `.` into the
  JSON of the last call output of the input, read by jslb.json_decode. The
  reply says the string at that path, then one space and its content when its
  content is not null, and output_make writes the message from that text, so
  a reply that only quotes holds content null. A quoting reply that answers a
  user message, which holds no tool result, throws
  provider_script.quote_unreached naming the node, otherwise included. A text
  that is not JSON, its failure the cause by utility.error_wrap, a member
  missing or not reached through objects, or a value at the path that is not a
  string throws provider_script.quote_missing naming the node and the path. A
  call output whose output is not a string is refused before, by
  provider_script.field_invalid at `json.input[k].output`. These refusals come
  in the choice, before the field checks. A quoting reply whose content is ""
  says the quote and a trailing space; no table holds one. The guides quote
  `value.say`, as script_run's result is `{"value":{"say":...}}`.
- scripted port checks: before its choice it refuses the method, a url not
  text, an unknown path, a body not an object, an input not an array or empty
  and a last item not an object. After it, so that the script's own refusals
  keep their texts, it refuses by provider_script.field_invalid the first bad
  field: url not https; headers absent; Authorization; Content-Type; model;
  tools, each flat, a name of `^[a-zA-Z0-9_-]{1,64}$`, at most 1000, or in
  debug mode by its reader DEBUG_MODE_TOOL_LIST_OMITTED alone; tool_choice; prompt_cache_key absent or empty; instructions beside
  previous_response_id, though alone it passes; a previous_response_id it does
  not hold; store not a boolean; each input item from the first; last
  `json.input` for calls still due at its end.
- scripted input checks: an item with no type is a message of role system or
  user with text content; a message is the model's, role assistant, of
  output_text parts; a function_call holds text call_id, name and arguments; no
  other type but reasoning and function_call_output. A run of the model's
  items must begin with reasoning, so a reply resent without its reasoning item
  fails at `.type`, as does any item while calls are due.
- scripted due calls: a function_call_output must answer the first call still
  due, else it fails at `.call_id`. A chained request's input starts with the
  calls of the response it chains from due, a chain's first with none; a run of
  the model's items makes its calls due once it ends, so a reply of several
  calls passes.
- scripted held responses: unless store is false the port keeps each response
  under its id, its context with the output after it and the output's calls,
  and a chained request's context is that, then its input. store false keeps
  none but still moves the key's cache. The port lives in the page, so a load
  forgets every response, as the agent forgets its chains.
- scripted ids: `resp_H`, `rs_H`, `msg_H` and `fc_H_K`, K from 1, H the first 16
  hexadecimal digits of the SHA-256 of the UTF-8 of the canonical text, keys
  sorted at every depth, of `[prompt_cache_key, context]`. They are arithmetic
  on the request and differ across loads, where a counter of the port would
  start again and the audit tool would find one id written twice.
- scripted reply: output a reasoning item, encrypted_content the text scripted,
  then a message of one output_text part when the chosen reply's text, its
  quote then its content by script quote, is not null, then each call as a
  function_call; the body id, object response, model, status completed,
  output, the echoes tools and tool_choice when the request held them,
  previous_response_id always, null when absent, and usage.
- scripted image: every image request, `POST {base_url}/images/generations`,
  gets provider_script.image_pattern() as b64_json, n times, a response_format
  but b64_json refused by provider_script.format_unsupported: a low resolution
  PNG test pattern, 16 px square, a checkerboard of black and white squares of
  4 px with hard pixel edges, built by hand from stored deflate blocks with
  its checksums, each chunk's CRC-32 and the zlib stream's Adler-32, computed
  in code. A guide's picture so shows 16 by 16 of `0 0 0 255` and
  `255 255 255 255`.
- scripted usage: arithmetic on the context, in characters and never tokens, an
  item's size the length of its canonical text: input_tokens the context's;
  input_tokens_details.cached_tokens the leading items equal to the last context
  the port answered under the same prompt_cache_key, its output included;
  output_tokens the output's; output_tokens_details.reasoning_tokens the
  reasoning item's, always the first; total_tokens their sum. A load's first
  call finds nothing cached.
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
- script otherwise: a text whose normal form the node's replies do not hold,
  a number, a word, a phrase or an empty line alike, takes the node's
  otherwise, as a person's bad input is expected; with none it throws
  provider_script.input_unknown naming the node and the text in normal form,
  which stays for a test's own table, a bug of that test, as the seed's table
  and every guide's hold otherwise on each node with replies, TestAnalyst and
  guide_walk.table_build requiring it. A content that is not a string is
  refused in every table. It throws provider_script.input_invalid.
- script after_holds: on a node holding it, tool results are answered by
  after_tools only when every result of the reply holds the text, else by
  after_lacks, whose tool calls move on as after_tools' do. A call output whose
  output is not a string throws provider_script.field_invalid.
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
  compile ts/tsconfig.node.json into ts/node.tsc.js by compile_timed, beside
  ts/node.js, the config's outFile, and writes node.js as the strict line,
  then `var test_vectors = ...;`, `var test_gold = ...;`, then the bundle with
  the strings table in place. Returns its path. Run as `node node.js BLOCK
  [--failfast]`.
- compile check: page_build.compile_timed runs a compile of the checkout's
  own project only when compile_due: its output, or a stamp for a check that
  writes none, is absent or no newer than the newest file or folder of ts/ and
  API/ts/. That is the one check of TypeScript, with no dependency of a
  project on its files tracked. After the compile the output, made empty if
  absent, takes the time the compile started, so an edit during it makes the
  next one due. A failed compile dates nothing, as noEmitOnError keeps the old
  output.
- compile sites: page_build's build/ts/test.js, node_build's ts/node.tsc.js,
  api_check's build/api_check.passed and text_match's
  build/api_match/passed. test_tap_pair_ts builds the Node bundle into build/,
  so it reuses the driver's compile; the unit suites of the compile,
  test_page_build_node and test_page_build_tsc, compile into scratch
  directories for real.
- compile check limits: tsc's own version and api_match.py's code are no
  input, so a new tsc or a changed api_match.py reuses a stamp until a source
  changes or build/ is removed.
- tsc output: both builds and api_check compile through tsc_run, which keeps it
  off stdout, the driver's TAP stream. A failed compile raises, tsc's output in
  its cause, and a PATH with no tsc raises FileNotFoundError.
- api_check: tsc_run on ts/tsconfig.api.json by compile_timed, its stamp
  build/api_check.passed. No page build calls it; test_posix.py does, last.
  In a normal run that is among the checks after the stream, so a mismatch
  does not stop the code's blocks; a full run meets it first in
  test_test_posix_formatters, in the Python unit phase. No other unit suite
  compiles the real API text, and test_page_build reaches api_check in a
  forked child with no tsc on PATH, having dated the stamp to 0 first.
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
  the demo test stderr, and server.txt for its plain rung; guide_walk stderr;
  the unit suites a scratch file.
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
  under the Windows runner, whose pipes are root's. The design: a patch of
  ttyd's pty_spawn duplicates its stderr before forkpty and, in
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
  serve_run, the demo test and guide_walk block them first.
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
  a test-all count checks that module after it and a normal count after
  test_xsjs_serve. No line of the module is reached by that suite alone.
- test_integrate_xsjs_serve: starts the program as a person does on port 0,
  fetches ttyd's token, stops it by SIGTERM and checks the exit code and the
  log, which it reads from stdout; stderr must be empty.

## api_match

- api_match.py: proves the text of API/ against the code, read and never imported, so a module with a fault at import fails its own suite and not this one. test_posix.py calls text_match last, after page_build.api_check, so a normal run meets a difference after the stream and the cloud run skips it. text_match runs typescript_match by page_build.compile_timed, its stamp build/api_match/passed, which typescript_match's removal of that folder takes away first.
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

- test_all: `python3 python/test_all.py [--test-normal] [--test-all]
  [--test-disabled] [--failfast] [--stream] [--module NAME]... [--failures N]
  [--tty] [--coverage] [--anthropic] [--debug] [--verbose]`. It refuses to
  start as root. Standard library only.
- end to end level: with no option, the bring up, then the end to end programs
  alone, the guide tests of Isaiah Cole, Ruth Calloway and Dawa,
  test_guide_isaiah.py, test_guide_ruth.py and test_guide_dawa.py in that
  order, by test_all.programs_chosen(False), ending at the first failure with
  its code: no suite, no block, no check of test_posix.py, no wire, browser or
  demo test and no line count. The smoke-test run's deadline holds.
- end to end programs: test_all.programs_chosen(stream) gives _GUIDE_PROGRAMS,
  the three guide tests, for a run with no stream, and _NORMAL_PROGRAMS,
  test_wire, test_browser and test_demo, then _GUIDE_PROGRAMS for a run with
  one. programs_run(chosen, limit, started, stream) imports each in that order
  and calls its main with category.option_words(chosen), each under
  category.alarm_plan(NAME.py, None, limit, elapsed), so under the run's
  deadline alone with no seconds of its own, and returns the first code not 0.
  main calls it with False when no stream is wanted and with True after the
  checks of test_posix.py.
- level options: each only raises the level, by test_all.stream_wanted and the
  category's action, so a run given two takes the higher in either order.
  TestDriverLevels of python/test_integrate_test_posix.py proves it, and its
  test_default_guides, test_normal_programs and test_programs_present hold
  programs_chosen(False) to the guide tests, programs_chosen(True) to the
  wire, browser and demo tests then the guide tests, and each name of the
  latter to a file python/NAME.py of the checkout, against the test's own
  constants _GUIDE_PROGRAMS and _NORMAL_PROGRAMS.
- stream options: --failfast, --stream, --module, --failures, --tty and
  --coverage need a stream, so each raises an end to end run to the normal
  level, and no higher.
- --test-normal: adds the suites labelled smoke-test, as one stream, the
  checks of test_posix.py, and the wire, browser and demo tests, their
  smoke-test rungs, before the guide tests.
- --test-all: adds the suites of the label test-all and the rungs of that label,
  and test_posix.sh passes --coverage with it.
- --test-disabled: adds every disabled suite, test, root and rung, which have
  no time limit but their own: the wire timers of the browser test wait out 120
  s each. test_posix.sh passes no --coverage with it, as the modules only it
  checks would pass or fail by whether the compile stamps are cold: a warm
  stamp leaves page_build.bundle_compile's lines unrun.
- category.py: holds the two labels, the three categories smoke-test, test-all
  and test-disabled, the options --test-all and --test-disabled, which every
  program takes, and option_words, which gives a category's option for a command
  line, none for smoke-test. --test-normal is the driver's alone, as only it has
  a stream.
- --failfast: the first failing test ends the stream.
- --stream: ends the run once the stream is checked, before the checks after
  it, and writes nothing to stdout but the stream.
- --module: runs only the suites and blocks it names, once each, in order, each
  one the category runs. It alone runs a suite or block that fails by design,
  listed apart, so that a run can check that --failures counts right, and below
  the disabled level it alone runs a disabled suite. Without
  --stream the run goes on to the checks after the stream, the wire, browser,
  demo and guide tests included.
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
  so a full run fails at a module's first line never run. No other level does,
  and the tty run stays separate, as --coverage refuses --tty. A count of
  2026-11-07 found every module complete but api_match, whose two lines a test
  then reached.
- unchecked modules: under --coverage a module is not checked when a disabled
  suite the run lacks counts for it, by test_all.paths_unchecked, or when a
  suite that counts for it had a skipped point in the run. Today those are
  ttyd_build, devtools, page_build, api_match, xsjs_serve and bootstrap.
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
  test_posix.py, the wire test, the browser test, the demo test, then the
  three guide tests, Isaiah Cole's, Ruth Calloway's and Dawa's, by
  programs_chosen(True), ending at the first failure with its exit code.
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
- disabled suites: `_DISABLED` of python/test_all.py, each suite or block with
  why it ran longer than a second. Each keeps its place and label in the phase
  lists, only a --test-disabled run takes it, and `--stream --module NAME` runs
  it, with --test-all for one labelled test-all. Today: test_devtools_chrome,
  test_page_build_tsc, test_xsjs_serve_death, test_integrate_console_view.ts,
  test_tools_browser_console.ts, test_console_open.ts and
  test_jslb_decode_vectors.ts.
- disabled tests: a slow test of a Python suite that stays is skipped by
  `unittest.skipUnless(category.disabled_taken(), reason)`, its reason starting
  `disabled:`, so the stream shows a SKIP point below the disabled level. The
  driver sets that by category.disabled_set before it imports any suite. Today:
  test_inputs_changed of test_ttyd_build, TestCheckout of test_api_match,
  test_program_served and test_stop_killed of test_xsjs_serve,
  test_hangup_restored of test_integrate_bootstrap, test_lock_refused,
  test_lock_waited and test_lock_hangup of test_bootstrap. A TypeScript block
  has no such reader, as tap.start carries no level, so a slow TypeScript test
  moves to a disabled block of its own, as test_jslb_decode_vectors.ts, on the
  helpers its first block exports.
- fixed waits: a test that waits out a fixed time is labelled test-all and
  runs in no normal run. A label is a suite's, so test_integrate_http.ts,
  test_integrate_media.ts and test_integrate_wire.ts, each holding one such
  case, are test-all whole; the wire block's case first_sent sits in its chain
  of cases on one tty 0. test_local_http's tests of the delayed path, the
  answer of /slow and test_delay_threaded, are the suite
  test_local_http_delay, so that the unit suite of the HTTP server the blocks
  use stays in the normal run.
- test_local_http_delay: test-all, beside test_local_http in the Python unit
  list, on that suite's ServerCase, answers_check and gold, counting for
  local_http.py by its _COUNTED row; test_local_http's answers_check takes the
  paths with no delay.
- ttyd build count: a run builds ttyd in its bring up alone: once when
  build/ttyd holds no ttyd built from the archive and patches of now, and not
  at all when it does. No suite builds ttyd: test_inputs_changed, which built
  it three times in a scratch directory, is skipped, so the build's own lines
  run only in a bring up that builds.
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
- test_guide_walk: the unit suite of guide_walk.table_build, smoke-test,
  directly after test_xsjs_serve_death in the Python unit list. TestScratch
  writes a scratch guide under build/ from its gold's table and files, with
  its core's files, the gold's ecs_files, in `ecs` beside it, and checks each
  step of the build, `$text` and `$ecs` replaced, arguments made text, the
  otherwise and the exit's expansion compared whole with the gold's built
  table, and that a second node that asks gets its own copies of the exit's
  lists; and each refusal by its text: a file of the guide or of the core
  with no final newline, a `$text` or `$ecs` object beside another member,
  `$text` named first when both are, ask beside otherwise, replies with no
  otherwise, the exit's input or resume already a reply, a taken name, the
  exit in the old form, and calls or resume_calls empty or no list.
  TestGuides builds the three guides of python/guides/, each start one of
  its nodes. Its _COUNTED row is
  empty, so it counts for no module: guide_walk.py's other lines need the page
  and run in the guide programs alone, and no --coverage run checks that
  module.
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
  the whole suite again, 0.8 s, and is skipped for that. The lock's 5 s wait
  is paid in no run, as test_lock_refused is skipped too. Inside a whole run
  each forked engine costs about 25 ms, so the suite's 30 tests left take 0.8 s
  and the two that hold the lock for lock_held_seconds are skipped as well.
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
  end that mark's line first, so a case pins the wire's lines, and the model
  replies' `http to ai` records, in order.
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
  the audit's own operation. wire_prompt is expected in choice_1 alone, so a
  second commit of the prompt in a later case fails that case.
- C block reply marks: as a reply's row commits as content_kept and an empty
  content, a reply's calls and texts are pinned in its `http to ai` record, by
  `"type": "function_call"`, call_id and name, or `"type": "output_text"` and
  text; a result's on `ai to server`, by `"type": "function_call_output"` and
  call_id; and wire_stored, a turn.append of role assistant, pins each reply
  row's commit. No part holds a digest id, and no mark pins an `ai to http`
  request, so the chain and the prompt sent once are proved by the demo alone.
- digest ids in a gold: no hand written gold pins the fake's H. A unit suite
  computes the H it expects at run time from a canonical text the test writes
  literally. A block that compares the fake's replies whole checks one H of 16
  digits per answer and writes it as sixteen zeros: test_integrate_provider_script
  in its handlers, which also fill a previous_response_id of `resp_` and zeros
  with the id of the answer before, and test_agent_faults by its ZeroedPort,
  each of whose cases asks the model once.
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
  alone, by `python3 test_all.py --stream` with the option of its category,
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

- rung programs: test_wire.py, test_browser.py and test_demo.py, the end to
  end programs of the normal level, by test_all.programs_chosen(True): a run
  at --test-normal or above runs them in that order, their smoke-test rungs or
  more by the category, after the checks of test_posix.py and before the guide
  tests. A run with no option runs none of them, as the guide tests alone are
  the end to end level.
- test_wire.py: `python3 python/test_wire.py [--test-all] [--test-disabled]
  [--anthropic] [--debug] [--verbose]`. A TAP run: the producer is ts/test_wire_rungs.ts in
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
- test_browser.py: `python3 python/test_browser.py [--test-all]
  [--test-disabled] [--anthropic] [--debug] [--verbose]`. Drives chrome-headless-shell by devtools.LinuxPipe,
  rung by rung, each under a timer and named by the stage of the plan it
  proves.
- browser roots: the suites root runs the ttyd page's bring up over TAP. The
  probe, credential and echo roots serve the headless page. Others serve the
  ttyd page. Roots are removed once the run passes and kept after a failure.
- disabled rungs: `_DISABLED_RUNGS` of python/test_browser.py, each rung with
  why it ran longer than a second, which only --test-disabled takes: the wire
  token, open,
  first line and drain timers, each waiting out a 120 s constant of
  ts/wire.ts; error before the first line, which waits out bootstrap.py's 5 s
  lock wait; wire drain poll; release runs nothing. `_DISABLED_ROOTS` names
  the roots whose every rung is disabled, echo, stalled and locked, which only
  --test-disabled makes.
- console role refused: opens the release root's page and waits for its
  settings itself, as the rung before it, release runs nothing, is disabled.
- http one line per request: its port's timeout is the gold's late_seconds,
  0.2, and its window after the late answer late_quiet_seconds, 0.3, so that
  the rung runs in 0.7 s; the other http rungs keep http_seconds, 2.
- test_demo.py: `python3 python/test_demo.py [--test-all] [--test-disabled]
  [--hold] [--anthropic] [--debug] [--verbose]`. Drives chrome-headless-shell by
  devtools.LinuxPipe over the engine page, rung by rung, each under a timer and
  labelled, through roots and ttyd made by xsjs_serve's functions. Exit 0, 1 at
  the first failed check, naming its rung, 130 at ctrl C, or 128 plus the
  signal's number at SIGHUP or SIGTERM.
- demo rungs: served, choice 1, choice 3, bad input, prompt kept, dump, audit,
  left and plain are smoke-test; reload, choice 2, console, overlay and the
  tools rungs are test-all; they run in the order served, reload, choice 1,
  choice 3, bad input, choice 2, console, overlay, prompt kept, dump, audit,
  left, plain, then tools served, data, console, again, dump, record and
  restart.
- demo prompt kept: loads the page after the turns and types the first bad
  input, then waits for a model call of the new load with every call answered
  in the audit read whole by audit_read.entries_parse, and runs the demo
  conversation check.
- demo conversation check: test_demo.conversation_check requires one
  turn.prompt commit, before the first model call, its first message the
  prompt; a chain started only at a load's first call or after a compaction's
  summary, each with the prompt as its first item and nowhere else; each
  chained call naming a reply of its own load, with no system message and
  exactly the outputs due, in order, or one user message, its reply with some
  cached tokens; every call of these debug roots sending
  DEBUG_MODE_TOOL_LIST_OMITTED, the gold's tools_omitted, as its tools; and the
  prompt once in the written bodies of the three lanes. A load's first call is
  not held to cached tokens, as the fake lives in the page. The list itself is
  sent by the plain rung alone, outside debug mode, which the fake checks flat,
  and test_tools_listed of ts/test_agent.ts proves it lists every tool.
- demo audit check: the audit rung and the tools record rung wait until each
  request of the audit has its reply, as a page thread's record comes late, then
  run audit_read.failure_check on it. The plain root records nothing, and the
  wire and browser roots fail on purpose, so no other root of these programs
  takes that check. The guide roots take it too, by guide_walk's audit rung,
  which also waits until audit_read.requests_open finds no request open.
- demo tools root: `build/test_demo-*/tools`, test-all, a debug root whose
  python/seed/provider_script.json test_demo.table_make replaces before ttyd
  starts, from the chains of the gold's `tools`. Each chain is one input, whose
  calls each take one model call, and a chain of the gold names its list of
  calls, so that 1 and 3 run data_calls and 2 and 4 console_calls with ids of
  their own. Each call is a ScriptCall, its call_id `call_CHAIN_INDEX` and its
  arguments the JSON text of the gold's. table_make fails when
  API/mcp/tools.json lists a tool no chain calls, so a new tool cannot miss the
  rung.
- demo tools order: 1 runs 17 data calls of 15 tools, whose render shows the
  pattern image_make kept. 2 runs the console's 3, answering each permit by a
  click, Always Allow then Accept then Always Allow; 4 then asks only the one
  not always allowed. 3 takes the conversation to 80 turns, so that 4 compacts
  it first. 0 dumps both sides, which differ in their turns alone, 9 and 88.
- demo tools record: the demo conversation check of its root; the first call
  to show the compaction's summary starts a chain of the prompt, the summary
  and the person's text; no turn.append holds the prompt or has the role
  system, and the browser sent the gold's turns_sent; each result is stored
  under its own call's id, which comes once, and holds the gold's text; the
  audit shows each commit; and the server holds the kept row and the main loop
  file, not the dropped database.
- demo tools restart: 5 calls system_restart, which ends the page, so it comes
  after the audit's copy. The fault screen holds `wire.start_twice`, the audit
  holds two engine starts of one pid, and ttyd stops with its code.
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
  whatever the run's switch, as browser_console_run needs debug mode. It goes
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
  choice_1, choice_3, console, overlay, tools_data, tools_console and
  tools_restart as PNGs, `failed_<rung>.png` for a failed rung, and the texts.
  audit.txt, the root's audit, is copied as the left rung starts, and
  audit_tools.txt, the tools root's, at the end of its record rung, each only
  under the run's --debug switch, or when a rung of that root fails.
  server.txt holds the plain rung's ttyd log and stays; it is empty when a run
  fails before that rung.
- demo hold: --hold after a failed rung prints the error, leaves the page,
  keeps ttyd serving the root, prints the address and waits by
  TtydServer.signal_wait; the run still exits 1. After a failed plain rung it
  serves the plain root. A rung that fails once its ttyd has stopped holds
  nothing.
- demo audit table: each row of audit in the gold is a label, a line type or a
  note's words, and a fragment of an entry's laid out text, at least one per
  lane and direction, from choices 1 and 3, the bad input rung and the page
  load, the masks included. The conversation's lanes add rows of the thin
  record: on `ai to http` prompt_cache_key, input_kept, a previous_response_id
  of `resp_` and tools as DEBUG_MODE_TOOL_LIST_OMITTED; on `http to ai` a
  function_call and cached_tokens;
  on `ai to server` the turn.prompt and a turn.append's content_kept and
  function_call_output. No fragment holds an id, a digest or a time, as a
  reload makes two loads. Every line entry's body parses as JSON, no entry is
  of a type under `audit.`, no entry is a ui.control_key of digit 1, each note
  of ui or ai is a sleep and none holds the gold's audit_wake_note, `until audit.`, and the engine
  starts once per load. In the demo test only a test-all run makes such sleeps
  and presses ctrl 1, through the overlay rung, so its smoke-test run, at
  --test-normal, does not prove either refusal; the C block's mark wire_audit_own does prove the sleeps' filter,
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

## Guides

- guide tests: test_guide_isaiah.py, test_guide_ruth.py and
  test_guide_dawa.py, the whole end to end level, which every level runs: with
  no option alone, and in a run with a stream after the checks of
  test_posix.py and the wire, browser and demo tests. Each is a thin main over
  guide_walk.guide_main(arguments, NAME), its bytecode sent to build/ first:
  `python3 python/test_guide_NAME.py [--test-all] [--test-disabled]
  [--anthropic] [--debug] [--verbose]`. Exit 0, 1 at the first failed check
  naming its rung, 130 at ctrl C, or 128 plus the signal's number at SIGHUP or
  SIGTERM. No real AI provider is contacted: the scripted provider answers
  every model and image request.
- guide purpose: task 1.1 of tmp/tasks_11_1519.md, by GUIDES_PLAN.md: three
  guides of guides.md each confirm with the scripted player that they go with
  the guide, talk with the player, build a sim, then guide the player through
  operating it, the player's inputs numbers, words and phrases, offline,
  POSIX, headless, on the fake AI alone.
- guide ecs: by DB_USE.md, task 1.1 of tmp/tasks_12_0737.md, each guide's sim
  is an entity-component-system in its world database: entities and
  components are rows of tables, systems are scripts whose work is SQL over
  those tables, and a step runs the systems in a fixed order, tick by tick.
  The fake guide operates it on the fake player's behalf: the player only
  talks, and the guide's table writes the player's choice into the world
  database as an intent by browser_sql_run, then steps the sim by
  browser_script_run of ecs_step, so every number the page shows is the sim's.
- ecs terms: an entity is one row of `entity`, an id and a unique name. A
  component is a table keyed by `entity`, plain data and no behaviour; an
  entity holds it when the table holds its row, and a tag is a component of
  no column but `entity`. A system is a script that finds the entities
  holding a set of components by SQL joins or correlated subqueries and
  changes them by set-based SQL; a step system runs once a step, a tick system
  once a tick. A step is one run of ecs_step for one decision of the player;
  a tick one unit of the sim's time, fixed per guide in its clock, a day for
  Isaiah, 20 seconds for Ruth and 30 minutes for Dawa; an intent the player's
  choice, a component of the player's entity that the guide writes and one
  step system consumes; an output one fragment of what a step says.
- ecs core tables: made in each guide's world database by ecs_init, each
  STRICT, as DB_USE.md 3.2.1 writes them: `entity (id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE)`; `system (ord INTEGER PRIMARY KEY, name TEXT NOT
  NULL UNIQUE, kind TEXT NOT NULL CHECK (kind IN ('lib', 'step', 'tick')))`,
  the schedule, exactly one row of kind lib; `clock (entity, step, tick,
  tick_seconds, ticks_max)`, a component of the entity `world` alone, the
  steps taken, the ticks run, the seconds a tick stands for and the most ticks
  one step may run; `intent (entity, verb TEXT, value TEXT)`; `busy (entity)`,
  the tag of an entity a tick system still moves; `output (n INTEGER PRIMARY
  KEY, step, tick, system TEXT, text TEXT)`, every fragment ever said; and
  `beat_log (n INTEGER PRIMARY KEY, step, tick, beat TEXT, choice TEXT,
  outcome TEXT)`, which replaces the one-row sims' logs. Every other column is
  INTEGER NOT NULL, and each component's `entity` is `INTEGER PRIMARY KEY
  REFERENCES entity (id) ON DELETE CASCADE`.
- ecs_init: python/guides/ecs/init.js, kept at /_files/script/ecs_init.js,
  args `{world}`: runs the DDL of the ecs core tables on the world in one
  sql_run and returns `{world}`, its tool result `{"value":{"world":W}}`.
- ecs_step: python/guides/ecs/step.js, kept at /_files/script/ecs_step.js,
  args `{world}`, inside one store.transaction_run: reads the one row of
  clock, the step its step plus 1; reads `system` in ord, each script's text
  by store.kv_get of /_files/script/NAME.js, compiled once by `new
  Function("engine", "args", text)`, a value that is no byte array throwing
  naming the script; runs the lib script with `{}`, its value the library;
  runs each step system once, in ord, with `{ecs}`; throws when an intent is
  left, naming its verb, as no system took it; while `busy` holds a row, runs
  a tick, the tick plus 1, then each tick system in ord, and throws when a
  step reaches ticks_max ticks with an entity still busy; writes the step and
  tick to clock in one statement; reads this step's outputs in n and its
  beat_log rows, throws unless there is at least one output and exactly one
  log row, and returns `{say, outcome}`, the outputs joined by single spaces
  and the log row's outcome, in that key order.
- ecs system contract: each system gets `args.ecs`, a frozen object the step
  makes: `world`, `step`, `tick`, `system`, its own name, and `lib`; `rows(sql,
  params)`, the rows of a SELECT on the world as objects; `run(statements)`, a
  sql_run on the world; `id(name)`, an entity's id, throwing when it is
  absent; `take(verb)`, the intent of that verb as `{entity, name, value}`,
  deleted, or null when none waits, so the system has no work this step;
  `say(text)`, one output row; `log(beat, choice, outcome)`, one beat_log row.
  A system returns nothing, keeps nothing between runs and finds its entities
  by their components alone, never by a list in its code. A step system takes
  at most one verb's intent. A tick system that moves an entity to its end
  deletes its `busy` row; one that starts nothing adds none.
- ecs replay agreement: the server and audit_read.databases_check repeat the
  statements, not the scripts, so every value SQL computes is an integer or
  text, by integer arithmetic, comparison, MIN, MAX or printf of integers;
  floating point is worked in JavaScript alone and bound as a parameter; no
  statement calls a math function, random() or a time function. An UPDATE
  takes its values from correlated subqueries keyed by `entity`, or from an
  UPDATE ... FROM matching at most one row per target row. An INSERT ...
  SELECT of several rows orders them by a key, so the rowids agree. A system
  does its writes of one tick in as few sql_run calls as it can, as each call
  that changes something is one push and one record.
- ecs_init form: args.world must be a non-empty text, else it throws; one
  sql_run of seven CREATE TABLE statements in the order entity, system,
  clock, intent, busy, output, beat_log.
- ecs_step checks: clock is exactly one row, of the entity named world;
  there is exactly one system of kind lib, whose value is a frozen object;
  every system is compiled before the lib runs, its script read as strict
  UTF-8, and a cache handle, a bad encoding or a compile failure throws
  naming the script's key; each step or tick system returns undefined; a
  system's throw is thrown again naming the world, the system's kind and name
  and the thrown value's stack, the value as its cause, so the tool result
  names the system.
- ecs time: clock.tick counts every tick the world has run, across steps; a
  step system's ecs.tick is the clock's tick before the step, a tick
  system's the tick it runs, and output and beat_log rows carry it; ticks_max
  bounds the ticks of one step, and a step that has run ticks_max ticks with a
  row in busy throws naming the busy entities; the clock is written by
  `UPDATE clock SET step = ?, tick = ? WHERE entity = ?`.
- ecs methods: rows(sql, params) takes a text and an array, runs one
  statement and gives each row as an object of its column names, throwing
  when two columns share a name, so every expression is named by AS;
  run(statements) returns store.sql_run of the world; id(name) throws when
  the world lacks the entity; take(verb) takes a non-empty text, may be called
  once in one run of a system, throws when more than one entity holds an
  intent of the verb, and deletes the one it returns by `DELETE FROM intent
  WHERE entity = ?`; say(text) takes a non-empty text and log(beat, choice,
  outcome) three texts, each one INSERT and one push, by the core's design
  and not batched with a system's own writes.
- guide scripts: each guide's directory holds `lib.js`, the number formats,
  units and published formulas with their coefficients, each with a one line
  comment naming its source, returned as a frozen object; `spawn.js`; `report.js`;
  and one file per system, named by the system. Each is kept at
  /_files/script/NAME_STEM.js, as isaiah_travel for
  python/guides/isaiah/travel.js; the core scripts keep the keys ecs_init and
  ecs_step in every guide. Every script is the body of the function script_run
  makes, `new Function("engine", "args", text)`, as python/seed/bootstrap.js
  is, beginning with the SPDX lines and a header of what it does, its args
  and, for a system, the components it reads and writes.
- guide spawn: NAME_spawn, args `{world}` and the guide's own, as Ruth's
  partner: makes every entity, every component row and the clock from the
  guide's constants, each with the one line comment naming its source, and
  returns the setup's say and outcome `ready`, the say also written as one
  `output` row at step 0, tick 0, of the spawn's own name. It runs the lib
  once, read from the schedule's row of kind lib and compiled as ecs_step
  does, for every format and formula its say needs, so no spawn copies the
  lib or formats inline; the three spawns share that one pattern, a function
  `lib_run`, the say built first and the output row ending the spawn's one
  write sql_run, inside one transaction_run. One exception: Ruth's say shows
  WING_SQFT as WING_SQFT_X100 / 100 by String, the inverse of the spawn's own
  scale, as her lib unscales only inside aircraft_read of an ecs. Every
  constant of the guide's
  world, game rules and an aircraft's book figures included, is a component
  value, so the database holds the whole model; a figure that is no whole
  number is an integer of a stated scale, its column named with `_x` and the
  scale, as glide_ratio_x100 1066, divided by it in JavaScript, which gives
  the same double as the literal. An item entity a step system makes when the
  keepsake is given, as Isaiah's trail_name and Ruth's handbill, is the one
  entity spawn does not make.
- guide report: NAME_report, args `{world}`: reads the guide's chosen output
  and what frames it from the components by SELECTs alone, so it commits
  nothing, and returns `{say, outcome: "told"}`. The guide runs it once, at
  the goodbye of the guide end step.
- guide chosen output: Isaiah's herd's `tally.head`, 1980, first said at the
  toll, `1980 head cross the ford`; Ruth's `purse.cents`, 7185, said `$71.85`,
  first at the race; Dawa's spare bottle's `full_l - left_l`, 1080, first said
  at the summit push as Teo's reckoned need, `Teo needs 1080 at 4 litres a
  minute`, 270 minutes of descent at 4 litres, then measured by dawa_breathe
  and said at the decision, `1080 of its 1200 litres`, one quantity reckoned
  then drawn, so repeat_check's first line names the push band. DB_USE.md
  3.9.3.5 names the decision.
- guide time: measured by two passing runs of 2026-11-12 at the end to end
  level: the level took 14.2 s and 13.1 s, bring up included, and each guide
  about 4 s from its ttyd's start to its last rung, Isaiah 4.0 and 3.9 s, Ruth
  4.3 s, Dawa 3.7 s, far inside the 180 s of python.test_all.smoke_seconds.
  Their audits: Isaiah 762 entries in 3.3 s of audit time, 111 sql.run
  commits and 51 model calls; Ruth 817 in 3.7 s, 125 and 59; Dawa 711 in 3.0
  s, 135 and 47; the one-row sims committed 27 sql.run lines in Isaiah's 3.1
  s. A cold compile of the bundle is not measured here.
- guide_walk.py: the one module of the guide tests. It imports nothing of
  test_demo.py, as the default tests must not depend on a program the default
  level no longer runs, so the helpers both need, the page state script, the
  typed keys and the listing of ttyd's children, are written anew. Its project
  imports come inside the functions that use them, after sys.pycache_prefix is
  set to build/pycache.
- guide_main: parses the arguments with prog test_guide_NAME.py,
  category.options_add and switches.options_add; sets the switches; sets
  SIGHUP and SIGTERM to exit with 128 plus the number; reads the gold
  python.test_guide_NAME by harness.gold_get; empties build/test_guide_NAME/,
  the failure directory; makes the work directory build/test_guide_NAME-XXXX/
  by tempfile.mkdtemp; opens devtools.Browser(window_width, window_height,
  devtools.LinuxPipe()) and climbs the rungs in it, under a category.LabelBook
  of the run's category, the root NAME entered with the gold's root_label.
- guide rungs: served, under served_seconds; the gold's rungs in order, each
  under rung_seconds; audit; left; databases and repeated, each under
  rung_seconds. served, audit, left, databases and repeated take root_label,
  and every rung of the three golds is smoke-test, so every level runs all of
  them. Each rung's timer bounds the browser's DevTools waits too.
- guide repeated rung: after databases, runs audit_read.repeat_check on the
  root's audit entries, table_build of the guide, the copy the databases rung
  made in build/test_guide_NAME/databases/ and the gold's `repeated`, reading
  the audit and building the guide's table anew; appends a newline, the
  evidence or `failure: ` and the check's message, then a newline, to
  build/audit/NAME_db.txt in every run that ends in the evidence or an audit
  failure; and only then fails on what it found, raising CheckFailed naming
  the copy of the databases at the end. Any other exception, as sqlite3's for
  a broken gold or the ValueError of repeat_check end turn, appends nothing
  and is raised with the rung's note.
- guide served rung: xsjs_serve.page_ready, then xsjs_serve.root_make with
  fresh true on WORK/root, its parameters the run's switches with debug the
  gold's root_debug, true, and verbose its root_verbose, false; writes
  json.dumps of table_build(python/guides/NAME) to
  ROOT/python/seed/provider_script.json before ttyd starts, as main_loop seeds
  the store's /_files/provider/script.json from it at the root's first engine
  start; starts xsjs_serve.TtydServer(values, root, 0, stderr) with SIGINT and
  SIGTERM blocked around the start; opens the address, waits for the gold's
  served band, "How can I help you?", with the box enabled, and checks its
  picture, the hyperposition's 4 by 4 of `0 0 0 255`; then copies the
  server's databases into WORK/databases_start by the guide copy, before any
  commit, as nothing has been typed.
- guide copy: each `NAME.sqlite` of the root, by a substrate.Store opened on
  the root and its db_snapshot, into a target directory by a second Store's
  db_restore, each cache file passed as its bytes, as db_restore renames a
  file passed by its path: the whole database transfer of db.sync, with no
  wire. The server is idle at the first copy and has ended at the second, and
  each Store closes its databases at the end of the copy.
- guide databases rung: after left, copies the server's databases into
  build/test_guide_NAME/databases/ by the guide copy, the download the user
  asked for; runs audit_read.databases_check of the root's audit with
  WORK/databases_start, that copy and the scratch WORK/databases_replay;
  writes build/audit/NAME_db.txt, a title, audit_read.database_lines of the
  copy, a blank line and the verdict, in every run; and only then fails on
  what the check found.
- guide audit rung: waits until audit_read.requests_open of the root's
  entries is empty, runs audit_read.failure_check then audit_read.guide_check
  on table_build of the guide and the gold, writes build/audit/NAME.txt, the
  audit digest then the verdict, in every run, and only then fails on what the
  checks found, so a failed check keeps its digest; then requires exactly one
  line starting `==== engine started, ` in _audit.txt, the one load, and under
  the run's --debug copies the audit to build/test_guide_NAME/audit.txt.
- guide digest: build/audit/NAME.txt and build/audit/NAME_db.txt, written by
  the audit, databases and repeated rungs of each guide test in every run, never
  removed, each replaced by the guide's next run. A walk that fails before a
  rung writes none of its file; its audit is in
  build/test_guide_NAME/audit.txt, and `audit_read.py PATH --guide NAME >
  FILE` makes the digest.
- guide left rung: lists by /proc the pids of ttyd's children whose command
  line holds the root's bootstrap.py, failing when there is none; opens
  about:blank; waits for them to end; stops ttyd and requires the gold's
  ttyd_code, 0.
- guide failure: an exception of a rung, ctrl C's KeyboardInterrupt aside,
  renews the rung's timer, copies the root's audit to
  build/test_guide_NAME/audit.txt when it exists and saves failed_RUNG.png
  there, the rung's spaces made underscores; ttyd stops in a finally. Only
  CheckFailed prints `error: RUNG: FAILURE` to stderr and returns 1; any other
  exception is raised with a note naming the rung. A pass
  removes the work directory; a failure keeps it. Under --verbose each rung
  prints one line after its name, and the run first prints where its root is.
- guide page state: one Runtime.evaluate of _STATE_SCRIPT: fault, the text of
  `body > pre` or null; subtitle, of #subtitle; disabled, of #input; focused,
  for a timeout's message alone; image_hidden, image_width, image_height and
  image_colours, the distinct `r g b a` texts of #image's pixels by
  getImageData. A state with a fault fails the rung at once.
- guide step: refuses its band by the guide band rule; types each character
  of say as a keyDown with its key and text, then a keyUp, by
  Input.dispatchKeyEvent at the focus, then Enter as a keyDown of key and code
  Enter, key code 13 and text CR, then a keyUp; waits until the band equals
  the step's with the box enabled; then checks its picture and its rows. No
  step clicks, as the box takes the focus at the first render and at each
  turn's end.
- guide band rule: a step whose band equals the band before it, the served
  band or the last step's, is refused as CheckFailed, as typing then waiting
  for a band shown already could pass before the turn ran. A band is the exact
  text of #subtitle; one made of a script's say and a reply's content is the
  say, one space, then the content.
- guide picture check: hidden must equal image_hidden; a shown picture must be
  size by size with the gold's colours, both sorted: the test pattern, 16 by
  16 of `0 0 0 255` and `255 255 255 255`, or the hyperposition, 4 by 4 of
  `0 0 0 255`.
- guide rows rule: a step's rows check, `{db, sql, params, rows}`, opens
  `file:ROOT/DB.sqlite?mode=ro` by Python's sqlite3, runs sql with params,
  makes each row a list and polls until the rows equal the gold's, a timeout
  naming the last rows read, as commits are pushes the server applies after
  the band shows. It reads only a database and table a step before it made, so
  no check meets a table the server has not yet made and no error is caught.
- guide gold: python/test_setting_test_guide_NAME.json holds poll_seconds 0.1,
  rung_seconds 60, served_seconds 240, window_width 1280, window_height 720,
  root_debug true, root_verbose false, root_label smoke-test, ttyd_code 0,
  served {band, picture}, rungs, each {rung, label, steps}, and repeated: a
  step {say, band, picture?, rows?}, a picture {hidden, size, colours}, a rows
  check {db, sql, params, rows}. A guide's walk is data, so a guide is written
  in JSON and JavaScript with no Python. No gold holds a digest or a response
  id.
- guide repeated: the gold's `repeated`, `{db, sql, params}`, the SQL that
  reads the guide's chosen output from the server's databases at the end as
  one row of one text, as `SELECT CAST(tally.head AS TEXT) FROM tally JOIN
  entity ON entity.id = tally.entity WHERE entity.name = ?` with params
  `["herd"]` on drive; Ruth's by `printf('$%d.%02d', cents / 100, cents %
  100)` of ruth's purse, Dawa's by `CAST(full_l - left_l AS TEXT)` of the
  spare. The text is a measurement or plain arithmetic on one; the gold holds
  the query and never the value.
- guide walks: Isaiah's 22 steps in the rungs creation, confirm, talk, build,
  night guard, reading, stampede, tracking, river, toll, dodge, keepsake and
  goodbye; Ruth's 26 in creation, confirm, talk, build, first flight, turns,
  loop, roll, main street, rides, race, wing walk, engine out, keepsake and
  goodbye; Dawa's 20 in creation, confirm, talk, build, icefall, morning,
  window, loads, summit push, decision, keepsake and goodbye. Every band of
  the three was worked by hand, and every band of the one-row sims is kept
  byte for byte by the ecs sims, the oracle that their arithmetic is
  unchanged; the rows checks read the components.
- guide inputs: numbers (`60`, `90`, `10`, `20`, `2`, `7`), words (`Yes`,
  `Sam`, `Settled`, `East`, `Ready`, `Everything`, `Go`) and phrases (`What if
  I hate it?`, `I tap my head twice`, `I'll fly, you walk`, `No thanks, take me
  back`, `Streets of Laredo`, `We take Teo down`, `So long`, `So long, Ruth`,
  `Goodbye, Dawa`), some typed with capitals
  and matched in lower case, which proves the normal form of script keys. Each
  walk types one bad input at a node with ask, Isaiah's `Which way did they
  go?`, Ruth's `lots` and Dawa's `Whenever`, answered by the built otherwise.
- guide table source: python/guides/NAME/table.json, a provider_script.Script
  with these differences, which table_build removes: top level `puzzled`, the
  guide's words before a question asked again; top level `exit`, `{input,
  calls, after, resume, resume_calls, paused}`, input and resume reply keys in
  normal form, calls and resume_calls lists of calls in source form, the two
  calls of the guide intent of the verbs `exit` and `resume`, after the text
  said after the exit's result, paused the answer to anything but resume
  while paused; a node's `ask`, the question it asks; a call's arguments a
  JSON object, not its text; anywhere an object whose one member is `$text`,
  standing for the text of the file it names in the guide's directory; and
  anywhere an object whose one member is `$ecs`, standing for the text of the
  file it names in the directory `ecs` beside the guide's.
- table_build: reads table.json by json.load as UTF-8; replaces every
  `{"$text": NAME}` at any depth by that file's text, and every `{"$ecs":
  NAME}` by the text of NAME in the directory `ecs` beside the guide's, each
  read as UTF-8 with no newline translation, less the one newline that must
  end it, a file not ending in one or a `$text` or `$ecs` object beside
  another member raising ValueError, so a CRLF file keeps its CR and fails its
  band; for each node of the source
  holding ask, in order, refuses it holding otherwise too, sets otherwise to
  `{content: PUZZLED + " " + ASK, next: NODE}`, adds the exit when the table
  holds one and removes ask; refuses any node, generated ones included, with
  replies and no otherwise; turns every call's arguments, generated ones
  included, into json.dumps(arguments, ensure_ascii=False, separators=(",",
  ":")), arguments that are no object raising ValueError; returns {start,
  nodes}, puzzled and exit left out.
- table_build exit form: the table's exit holds exactly the members input,
  calls, after, resume, resume_calls and paused, else ValueError naming them,
  so the old form of call and resume_call is refused; calls and resume_calls
  are each a list of one call or more, else ValueError, as a reply of no call
  would strand the player at `X~exit`; the directory `ecs` is the one beside
  the absolute path of the guide's directory.
- guide exit expansion: at a node X holding ask A, the exit adds to X the
  reply of its input, content null, calling a deep copy of the exit's calls,
  next `X~exit`; `X~exit`, no replies, after_tools of content after and quote
  value.say, next `X~paused`; `X~paused`, the reply of resume, content null,
  calling a deep copy of resume_calls, next `X~resume`, and otherwise of content
  paused, next itself; `X~resume`, no replies, after_tools of content A and
  quote value.say, next X. The page so shows the exit's arithmetic then the
  guide's words, and on resume the resume's arithmetic then the question that
  was pending. Generated nodes take no exit and no puzzled otherwise of their
  own. A node holding the exit's input or resume as a reply already, or a
  generated name already a node, raises ValueError.
- guide exit placement: the builder of the test side, not the provider, gives
  every node holding ask the exit, so the exit promised in the introduction
  works at every point once the sim exists, rule 4 of guides.md. The exit
  writes the intent `exit` and steps, whose exit system brings the player to
  safety by its own arithmetic, and the resume the intent `resume`.
- guide ask rule: a node holds ask exactly when the sim exists by the time the
  player can be in it, as an exit before the build would run a script not yet
  written. The nodes before the build, hyperposition to talk, hold their own
  otherwise.
- guide start: each guide test starts at the hyperposition, as every player
  does, and the fake AI makes the guide's universe, world, region and scene by
  the AI's own tools. No guide state is written at root time but the seed's
  table, as the test rules forbid changing a module's state to emulate an
  environment and the scripted table is the one scripted part allowed.
- guide creation turn: the start node hyperposition answers the guide's
  request, `take me on a cattle drive`, `take me flying` or `take me to
  everest`, with browser_image_make of the scene's prompt at the key
  NAME/SCENE.png, next made, and anything else with an otherwise in the
  analyst's dry voice; made's after_tools calls in one reply
  browser_script_run of the seeded bootstrap with title, region, universe,
  world and scene `{id, subtitle, image}`, the subtitle the introduction, then
  browser_doc_put of `{db: UNIVERSE, id: "prompt", body: {"0": {"t":
  "prompt"}, "text": PROMPT}}`, next booted; booted's calls browser_render of
  the image and the introduction, next shown, the image made a reply before,
  as a render reads its bytes when it runs; shown says the introduction, next
  offer. The band is then the introduction, the picture the 16 by 16 pattern,
  metaverse's universe row the guide's and its world row the guide's world.
- guide confirm: the introduction, verbatim, is the guide's offer, and the
  player's answer is a reply key of offer, whose otherwise leaves the offer
  open. Isaiah's player says `no thanks, take me back`, a kv_put of
  /metaverse/world back to metaverse and a render of the hyperposition, then
  `actually, the cattle drive`, the kv_put of drive and a render of the
  campfire, then `yes`; Ruth's asks `what if i hate it?`, says `yes`, then
  gives the name `sam`; Dawa's says `not yet`, Dawa waits, then `all right,
  i'll come`.
- guide talk: each talk node answers one question with a content reply that
  stays there, Isaiah's `how long have you been riding night guard?`, Ruth's
  `why are you short a partner?` and Dawa's `why have you never left anyone
  behind?`, and starts the build at `let's ride out`, `let's go` or `ready`.
- guide build turn: the reply to `let's ride out`, `let's go` or `ready`,
  its calls in order: browser_kv_put of each script, `{ref:
  "/_files/script/KEY.js", text: {"$ecs": FILE}}` for the core's two and
  `{"$text": FILE}` for each of the guide's; browser_script_run of `{name:
  "ecs_init", args: {world: WORLD}}`; browser_sql_run on the world of the
  guide's component DDL and the INSERTs of `system`, the schedule written by
  the guide in SQL; then browser_script_run of `{name: "NAME_spawn", args:
  {world: WORLD, ...}}`, last, next built, whose after_tools quotes value.say,
  the spawn's say, and asks the first beat.
- guide intent: a beat makes two calls, in one reply or two by guide beat:
  browser_sql_run on the world of `INSERT INTO intent (entity, verb, value)
  SELECT id, ?, ? FROM entity WHERE name = ?` with params `[VERB, VALUE,
  "player"]`, the player's choice written by the guide on the player's
  behalf, VALUE always text, then browser_script_run of `{name: "ecs_step",
  args: {world: WORLD}}`. The quote reads the step's value, the last call's
  output. The player entity is named `player` in every guide, Ruth's partner
  included. VALUE is the player's choice as the guide reads it from the
  player's words: the words in normal form, as `ride out again`, or the
  choice they name, as Ruth's walker `Ruth`, and never a number of the model.
- guide beat: a node holding ask and replies keyed by the walk's inputs, each
  making the two calls of the guide intent with the choice's verb and value,
  next an after node, which always goes on, by after_tools quoting value.say
  with the next node's ask as content, or holds after_holds
  `"outcome":"WORD"`, going on by after_tools and back by after_lacks, whose
  content asks again. Every number the page shows is the sim's arithmetic,
  and the table holds no number of the model.
- guide split beat: a beat whose after node holds after_holds sends the
  intent alone, next a node `NODE_step`, no replies, whose after_tools,
  content null, calls ecs_step, next the after node, which so sees the step's
  result alone: the scripted provider's after_read and audit_read's
  _after_reply take after_tools only when every call output ending the input
  holds the text, and the intent's sql_run result never holds an outcome. A
  beat whose after node always goes on, the exit, the resume and the keepsake
  send both calls in one reply. The design not taken, after_holds reading the
  last call output alone as the quote does, changes ts/provider_script.ts and
  the rules script after_holds and guide_check script, and DB_USE.md 5.9
  changes no TypeScript. A real model's prompt names one reply of both calls;
  the split is the scripted table's alone.
- guide keepsake turn: with a picture, Ruth's and Dawa's, one reply calls
  browser_image_make of the keepsake's picture, next a node, Ruth's printed
  and Dawa's developed, whose after_tools calls browser_render of it, then the
  two calls of the guide intent of the verb `keepsake`, last, so that the
  quote reads the step's result; with none, Isaiah's, the reply makes those
  two calls alone. The node its result reaches quotes value.say with the
  guide's farewell, next end.
- guide end step: each walk's last rung, goodbye, is one step, the end of the
  conversation: the player says goodbye, `So long`, `So long, Ruth` or
  `Goodbye, Dawa`, a reply key of the node end, whose one call is
  browser_script_run of `{name: "NAME_report", args: {world: WORLD}}`, next
  `told`, whose after_tools quotes value.say with the guide's farewell as
  content and goes back to end. end keeps its otherwise of the guide's last
  words for anything else. Its band, the report's say then the farewell, is
  worked by hand from numbers that earlier bands already show, and the end
  turn commits nothing but its turns, as the report only reads.
- guide call ids: `call_` and a short word, unique within each reply: the
  build turn's `call_put_KEY` for the put of /_files/script/KEY.js,
  `call_init`, `call_schema` and `call_spawn`; a beat's `call_` and its verb,
  as `call_track`, and `call_step`, a split beat's `NODE_step` calling
  `call_step` alone; the exit's `call_exit` and
  `call_exit_step`, its resume's `call_resume` and `call_resume_step`; the
  goodbye's `call_report`.
- guide no number by hand: an ask, a content or a puzzled, after or paused
  text states no number of a model; every such number comes from a script's
  say. The intent's value is the player's choice, by guide intent. The
  introductions are verbatim and keep their own words.
- guide prompt: prompt.txt, the universe's prompt document, which
  agent.prompt_build sends after the analyst's prompt: who the guide is, in
  the guide's voice and world; the rules every experience follows of
  guides.md; the guide's beats; the exit and how to resume; the scripts it
  sends at the build, each verb of an intent and its value, the intent's SQL
  and the step, the report at goodbye, and that the AI writes the intent,
  steps the sim and says the step's say; that the guide stays inside its own
  world and answers anything outside
  it in-world, by policy flag 1 of guides.md. The fake AI never reads it; a
  real AI would.
- guide sim contract: a guide's sim is the core scripts and its own, by the
  rules ecs_step, ecs system contract and guide scripts, kept by the build
  turn under /_files/script/; no script but ecs_step, and NAME_spawn for the
  lib named by the schedule's row of kind lib, compiled and run once as
  ecs_step does for a say that needs a published formula, as Dawa's air at
  Base Camp, runs another; none keeps
  state between runs, and only spawn.js and lib.js hold a constant of the
  model, each with a one line comment naming its source. The one-row sims'
  sim.js, one script of actions, is gone.
- guide sim result: ecs_step and NAME_spawn return `{say, outcome}` and
  NAME_report `{say, outcome: "told"}`, say the text the page shows, outcome
  a short word, as `made`; the tool result the fake reads is then
  `{"value":{"say":"...","outcome":"..."}}`, compact JSON in insertion order
  passed unchanged as the call output, so a node's after_holds is
  `"outcome":"WORD"`, quotes and colon as JSON.stringify writes them, and its
  quote `value.say`. Every step, the keepsake's included, logs exactly one
  beat_log row, beat the verb, choice the value, a number of the input logged
  as its text.
- guide sim tables: every table STRICT, every column INTEGER or TEXT and NOT
  NULL: the ecs core tables, and the guide's components, each keyed by
  `entity INTEGER PRIMARY KEY REFERENCES entity (id) ON DELETE CASCADE`, a
  tag of that column alone, the keepsake a component `keepsake (kind, text)`
  of an item entity. A value bound is an integer, made by Math.round or
  Math.floor when not whole already, or a string. No statement uses random(),
  a math function, a time function or anything else that differs when the
  server replays it, by ecs replay agreement.
- guide sim failures: a player's choice that fails is an outcome with its own
  say, never a throw, as bad user input is expected; a throw is a broken
  table, an unknown verb or a value of the wrong form. Branches no walk takes,
  as Isaiah's west flank and swimming the river now, have says and outcomes of
  their own.
- guide number formats: whole, `String(Math.round(x))`; tenths,
  `(Math.round(x * 10) / 10).toFixed(1)`, as 1.5, 6.0 and 8.3; money from
  integer cents, `"$" + Math.floor(c / 100) + "." + String(c %
  100).padStart(2, "0")`, as $46.85; a clock from whole seconds, `Math.floor(s
  / 60) + ":" + String(s % 60).padStart(2, "0")`, as 4:02; an hour of the day,
  `h + ":00"`, as 2:00; a duration from whole minutes, `H hour` or `H hours`,
  then ` M minutes` when M is not 0; a constant as its source writes it, as
  352.56 and 10.66, by String.
- guide compaction: the browser compacts a scene when a player's turn is
  appended to it holding turn_compact_turns, 64, turns or more, counted
  before that turn. The ecs sims store more rows a beat than the one-row sims
  did, a split beat taking two replies and the build turn some 21 calls, so
  compaction comes sooner, as the passing runs of 2026-11-12 measured:
  Isaiah's campfire holds 65 before step 13, Which way did they go?, the bad
  input, and compacts there, the restart answered by the track node's
  otherwise, then ends at row 48 at step 20, Count them in, which moves the
  walk to the stockyard, a new conversation of 9 rows at the end; Ruth's
  hayfield holds 69 before step 14, 90, and compacts there, then 68 before
  step 26, So long, Ruth, and compacts again, so the goodbye's first model
  call restarts the chain and its last, the one repeat_check reads, chains
  from that restart; Dawa's base camp holds 66 before step 13, Go tomorrow,
  and compacts there, then 43 before step 20, Goodbye, Dawa, under 64, and
  does not compact again.
- guide restart: the turn that compacts sends a chain's first request, with no
  previous_response_id, of the prompts, the summary and the player's text. The
  fake takes it, as a chain's first request has no call due and each item is a
  message of role system or user with text, and its place is per port, so a
  compaction moves nothing of the script. audit_read.failure_check passes, as
  the restart is a chain's first call holding the analyst's prompt once as its
  first item, its written body holds the summary and the player's text alone,
  the prompts counted by input_kept, and no model output item is sent again,
  the compacted rows being gone, so no id is written twice.
- guide rule 6: each sim's state persists in its world database, which the
  server keeps, and Isaiah's naming turn, in the stockyard, a new scene and so
  a new conversation, reads it, proving the world's state outlived the scene.
  No walk returns in a second session, by guide deferred serving.
- Isaiah Cole: guides.md entry 1, Two Thousand Head to Dodge: universe
  trail_drive, world drive, region trail, scene campfire with the image
  /_files/isaiah/campfire.png, scripts isaiah_lib, isaiah_spawn,
  isaiah_report and the systems of Isaiah's schedule. The stake is the herd,
  counted at Dodge City in a new scene, /trail/stockyard/1 with
  /_files/isaiah/dodge.png. The exit, designed by rule 4 from his "You don't
  have to say a word" and "if you'd like", is `i'll ride back to the fire`,
  while Isaiah keeps the circle singing, resumed by `ride out again`. The
  keepsake is a trail name, the last word of the song sung, as `Trail name:
  Laredo.`, the `keepsake` row of kind `trail name` of the entity trail_name.
  The song, Streets of Laredo, is public domain, by policy flag 7. The
  goodbye is `so long`, running isaiah_report.
- Isaiah's entities: world, herd, ridge, creek, draw, player, isaiah,
  cimarron, outfit and dodge, ids 1 to 10, made by isaiah_spawn in one
  sql_run, and trail_name, 11, made by the keepsake. The clock: a tick of a
  day, tick_seconds 86400, ticks_max 10.
- Isaiah's components: of the herd head (count), bed (head), calm (level,
  most), temper (song_calm, settled, milled), breaks (loss), pace (miles),
  losses (lost, tolled, found) and tally (head, tick), made at the count; of
  each bunch share (head) and cover (name, opening), and head and the tag
  hidden while it is out; place (mile) of the herd, cimarron and dodge; of
  the cimarron water (high, per_drowned), high the days of waiting its water
  needs to drop; of the outfit toll (floor); of the player looks (used,
  most), exits (count) and song (title), made by an upsert at the sing; of
  the player and isaiah wage (cents_a_day, earned); while the sim runs travel
  (goal) of an entity under way and wait (days) of the herd holding on the
  bank; of trail_name keepsake (kind, text). Systems find the herd by its
  components alone: losses for head changes, temper and calm for calm, head
  and bed for the tally.
- Isaiah's schedule: ord 1 isaiah_lib; ord 2 to 11 the step systems
  isaiah_sing, isaiah_exit, isaiah_resume, isaiah_read, isaiah_stampede,
  isaiah_track, isaiah_river, isaiah_toll, isaiah_count and isaiah_keepsake,
  each taking the verb of its name; ord 12 to 14 the tick systems
  isaiah_travel, which moves each entity of travel by its pace up to its
  goal's mile and there deletes its travel and busy, isaiah_hold, which adds
  a day to each wait and lowers the water of the river at the waiter's mile,
  at water.high 0 saying the crossing and deleting the wait and busy, and
  isaiah_wage, which adds cents_a_day to every earned. Travel and wage say
  nothing.
- Isaiah's ticks: tracking done sends every entity of pace to the next place
  ahead, the Cimarron, 6 ticks; waiting at the river is 1 tick; the toll paid
  sends it to Dodge City, 4 ticks. The clock ends at step 14, tick 11. The
  count reads 11 days as the tally's tick times tick_seconds over the lib's
  SECONDS_A_DAY, and $11.00 from the player's earned wage. The river beat
  throws when the water is already low, as the table reaches it once.
- Isaiah's says: the river's wait is two outputs, the river system's `You
  hold the herd a day on the south bank of the Cimarron` at the step's tick
  and the hold system's `and the water drops: ...` one tick later; every
  other step says one output of its step system. isaiah_spawn stores its say
  as an output at step 0 and formats by its lib, by guide spawn.
- Isaiah's intents: sing `Streets of Laredo`; read `settled` or `restless`;
  stampede `east` or `west`; track the bunch's entity name, `ridge`, `creek`
  or `draw`; river `wait` or `swim`; toll digits, `10` or `20`; count,
  keepsake, exit and resume the player's words in normal form. read, track
  and toll are split beats, by guide split beat, through `read_step`,
  `track_step` and `toll_step`.
- Isaiah's report: one SELECT of tally, bed and losses, each number cast to
  text by SQL as the gold's query casts it. Its say: `The tally man's book: N
  head counted in at Dodge City, of N bedded on the flat, N paid at the ford
  and N lost on the trail.`; the told farewell: `Isaiah tips his hat and
  turns his horse for the trail back south. "So long. Ride easy."` No content
  of his table holds a digit.
- Isaiah's constants, each the guide's own, from its text or its rules, in
  spawn.js with its source comment: HERD 2000, into head and bed; BED_MILE 0
  and MILES 100, the places of the herd and of dodge, the last hundred miles;
  RIVER_MILE 60, a game rule no band shows; MILES_A_DAY 10, the pace; the
  herd's calm, a game rule of 0 to 10, CALM_START 5 and CALM_MAX 10, and its
  temper SONG_CALM 3, SETTLED_CALM 7 and MILLED_CALM 3; the bunches, ridge 12
  in the cedars, creek 25 in the willows and draw 3 in the plum thicket, into
  share and cover, their sum the forty missing at sunrise, so MISSING is no
  constant; LOOKS 3, the searches before noon; BREAKS_LOSS 60, the run into
  the breaks; HIGH_DAYS 1 and HIGH_WATER_PER 100, a head drowned for each 100
  swum in high water; TOLL_FLOOR 20, the least the outfit takes; WAGE_CENTS
  100, a dollar a day, the wage of both riders; TICK_SECONDS 86400, and
  TICKS_MAX 10, MILES over MILES_A_DAY. lib.js holds SECONDS_A_DAY 86400 and
  the formats whole, money and days.
- Ruth Calloway: guides.md entry 2, The First Ride's Free: universe
  barnstorming, world summer, region county, scene hayfield with the image
  /_files/ruth/hayfield.png, scripts ruth_lib, ruth_spawn, ruth_report and
  the systems of Ruth's systems. The stake is ruth's `purse.cents` for the
  summer and her airplane, the Jenny. The exit is her own rule, `i tap my
  head twice`: the intent exit, a glide from the height flown to the grass,
  like a feather, keeping the height in `resume`, resumed by `go on`, a climb
  back to the height left; offer, name and talk answer it too in her voice,
  before any sim, with no call. The keepsake is a handbill with the player's
  name beside hers, as `RUTH CALLOWAY AND SAM, AERIAL ACROBATS: loops, rolls,
  the wing walk and a motorcar beaten! Rides $5.00 for 10 minutes.`, the
  `keepsake` row of the item entity handbill, its feats those beat_log shows
  made. The goodbye is `so long, ruth`, running ruth_report. Her sim is turn
  based on a real world aviation stunt model, as task 1.1 requires.
- Ruth's entities: world, jenny, ruth, player, the partner, fair, motorcar,
  wind, north and south, ids 1 to 9, made by ruth_spawn; handbill, 10, made
  by ruth_keepsake. `fair` holds the show, prize and course, which DB_USE.md
  3.9.2 gave no owner. The clock: tick_seconds 20, ticks_max 30, a game rule,
  ten minutes of sim time.
- Ruth's components: of the jenny `airframe (gross_lb, wing_sqft_x100, hp,
  max_mph, min_mph, climb_ft, climb_min, tank_gal, burn_gal_hr,
  level_off_ft, cruise_mph, glide_ratio_x100)`, `altitude (ft)` and `resume
  (ft)`, a row only while an exit's height is kept, written by upsert; of
  ruth `technique (loop_pull_g, loop_top_g_x10, roll_seconds, stunt_ft)`,
  `fares (ride_cents, ride_min, gas_cents_gal)` and `purse (cents)`; of the
  player `name (text)` and `exits (count)`; of the fair `show (minutes, ft)`,
  `prize (cents)` and `course (feet)`; of the motorcar `vehicle (top_mph)`;
  of the wind `wind (mph, quarter)`, quarter the side it blows from, as
  `from` is an SQL keyword; of north and south `field (miles_x10, name)`, a
  field's heading its entity's name; while racing `racer (ground_mph, feet,
  ticks)` of each racer, ticks in place of start and finish ticks as NOT NULL
  forbids a finish unknown while racing, and `throttle (setting)` of the
  jenny; of the handbill `keepsake (kind, text)`.
- Ruth's systems: ord 1 ruth_lib; ord 2 to 14 the step systems ruth_climb,
  ruth_exit, ruth_resume, ruth_turn, ruth_loop, ruth_roll, ruth_buzz,
  ruth_rides, ruth_race, ruth_wing_walk, ruth_field, ruth_landing and
  ruth_keepsake, each taking its verb's intent and working today's formula
  in JavaScript from the components; ord 15 and 16 the tick systems
  ruth_drive then ruth_finish. ruth_lib holds the units, standard gravity,
  FPS_PER_MPH as 5280 / 3600, the same double as 22 / 15, the number formats,
  the book's climb and burn, and the shared reads of the aircraft, pilot,
  wind and fields, dividing the scaled figures. The split beats, by guide
  split beat, are turns, loop, roll, buzz, rides and engine.
- Ruth's intents: climb `take her up`; exit `i tap my head twice`; resume `go
  on`; keepsake `yes please`; turn, loop, roll, buzz and rides the number as
  typed; race `full throttle`; landing `into the wind`; wing_walk `Ruth` and
  field `south` or `north`, the guide's reading of the player's words.
- Ruth's race ticks: ruth_race sets the altitude to the book's 50 ft, enters
  the jenny at 75 less 15, 60 mph over the road, and each vehicle at its top
  speed, marks them busy and says the start, ending in a comma. ruth_drive
  moves each busy racer `ground_mph * 5280 * tick_seconds / 3600` whole feet
  a tick by integer SQL, throwing at a fraction, and frees it at the course's
  26400 ft. ruth_finish, once none is busy, says the miles and both times as
  ticks times 20 s, pays the prize and logs the beat race with the throttle
  as its choice. Full throttle runs 15 and 20 ticks, 5:00 against 6:40; at
  the cruise both take 20, a dead heat. clock.tick is 20 after the race.
- Ruth's report: `printf('$%d.%02d')` of the one purse as the gold's query,
  the partner's name as the text of the one `name`, found as its holder and
  not by entity name, and the prize when beat_log holds the race won; read
  only; outcome told. Its say `Sam, the cigar box holds $71.85 for the
  summer, with the fair's $25.00 purse in it.`; the told farewell `The
  Jenny's still mine, and that's your doing too. So long, partner. Come find
  me in the next town.`
- Ruth's aircraft constants: by the Curtiss JN4-D Specifications and
  Operating Instructions, 1918, as reproduced at
  airminded.net/jenny/jn4_spec.html: GROSS_LB 1920, gross weight loaded, with
  pilot 165, passenger 165 and fuel 21 gallons; WING_SQFT 352.56, total
  supporting surface; HP 90, the OX-5 rated at 1400 rpm; MAX_MPH 75 and
  MIN_MPH 45, speed maximum and minimum in horizontal flight, the latter the 1
  g stall; CLIMB_FT 2000 in CLIMB_MIN 10; TANK_GAL 21; BURN_GAL_HR 9; and
  LEVEL_OFF_FT 50, the final leveling off about fifty feet from the ground.
  CRUISE_MPH 60, by P. M. Bowers, Curtiss Aircraft 1907 to 1947 (1979), p.
  156. GLIDE_RATIO 10.66, by B. van der Zalm, aircraftinvestigation.info,
  Curtiss JN-4D (2018), a lift to drag ratio calculated from published data,
  as no period source gives the Jenny's glide. G 32.174 ft/s/s, standard
  gravity; FPS_PER_MPH 22 / 15, 5280 ft over 3600 s.
- Ruth's other constants: her technique, as any stunt model needs the pilot's
  inputs: LOOP_PULL_G 4, the pull at the loop's bottom, LOOP_TOP_G 0.5, light
  over its top, and ROLL_SECONDS 4, her count for a roll. RIDE_CENTS 500 and
  RIDE_MIN 10, the introduction's "Five dollars buys ten minutes";
  GAS_CENTS_GAL 21, U.S. Department of Energy, Vehicle Technologies Office,
  Fact #915 (2016), the average pump price of 1929; MOTORCAR_MPH 45, the Ford
  Model T's top speed of about 45 mph, as The Henry Ford gives it. The guide's
  world: WIND_MPH 15 from the north; RACE_MI 5; PURSE_CENTS 2500; SHOW_MIN 40;
  STUNT_FT 2000, where she teaches; SHOW_FT 1000, the wing walk's height,
  where the engine quits; NORTH_MI 1.5 and SOUTH_MI 3, the fields. Each is a
  component value of ruth_spawn with its source comment: WING_SQFT and
  GLIDE_RATIO as 35256 and 1066 hundredths, LOOP_TOP_G as 5 tenths, the
  fields as 15 and 30 tenths of a mile, RACE_MI as 26400 ft, and the purse
  starting at 0; G and the units sit in lib.js.
- Ruth's formulas: every speed in ft/s inside, mph outside. A level turn at
  bank b pulls n = 1 / cos(b) and stalls at Vs(n) = MIN_MPH sqrt(n), from lift
  L = n W at the wing's greatest lift coefficient, a turn at the cruise
  stalling when Vs(n) > CRUISE_MPH; its radius is V^2 / (G tan b) and its time
  round 2 pi V / (G tan b) at the cruise. A loop is two arcs with energy kept,
  the engine's pull and the drag taken to cancel: Rb = Ve^2 / (G (LOOP_PULL_G
  - 1)), Rt = Vt^2 / (G (LOOP_TOP_G + 1)) and Vt^2 = Ve^2 - 2 G (Rb + Rt), so
  Vt^2 = Ve^2 (1 - 2 / (LOOP_PULL_G - 1)) / (1 + 2 / (LOOP_TOP_G + 1)), Ve^2 /
  7 for 4 and 0.5; it is made when Vt reaches MIN_MPH sqrt(LOOP_TOP_G), the
  entry wanted that speed times sqrt(7), the dive from the cruise costs (Ve^2 -
  Vc^2) / (2 G) of height and the top is Rb + Rt above the pull. A roll at
  MAX_MPH, zero g for ROLL_SECONDS T, changes height by V sin(nose) T - G T^2 /
  2, keeping it when sin(nose) >= G T / (2 V). A glide with the engine off at
  the cruise goes h GLIDE_RATIO in still air, sinks V / GLIDE_RATIO and takes h
  GLIDE_RATIO / V, over the ground times (V - W) / V into the wind and (V + W)
  / V with it. A touchdown at MIN_MPH through the air is MIN_MPH - W over the
  ground into the wind, MIN_MPH + W with it. Fuel is minutes BURN_GAL_HR / 60
  and gas money gallons GAS_CENTS_GAL, in whole cents; the rides sold may burn
  what TANK_GAL spares once SHOW_MIN is kept; the race runs into the wind at
  the throttle's airspeed less WIND_MPH against the motorcar's MOTORCAR_MPH
  over RACE_MI, a dead heat at the cruise.
- Ruth's rounding: every shown value sits at least 0.1 of its last shown digit
  from a rounding boundary but these, each far wider than a double's error:
  the exit's sink, 8.25516, 0.005 above 8.25; n at 30 degrees, 1.1547, 0.047
  tenths above 1.15; the loop's dive, 150.432, 0.068 below 150.5; the roll's
  rise at 40 degrees, 25.4345, 0.066 below 25.5; n at 60 degrees,
  1.9999999999999996 in JavaScript, shown 2.0; and the exact products 21320,
  7995, 13325 and 315, which Math.round takes from a float error under
  0.0000001. 75 * (22 / 15) is 109.99999999999999, shown 110. Every scaled
  figure divided by its power of ten is the double of its literal.
- Dawa: guides.md entry 4, Nobody Left Behind: universe everest, world
  expedition, region khumbu, scene base_camp with the image
  /_files/dawa/base_camp.png, scripts dawa_lib, dawa_spawn, dawa_report and
  the systems of Dawa's schedule. The stake is Dawa's record of never leaving
  anyone behind, dawa's `record` `kept` or `broken`, met at the South Summit,
  where the top and Teo's rescue cannot both happen. The exit, designed by
  rule 4 from his "Tell me if it starts" and "I have never left anyone
  behind", is `take me down`, the intent exit, Dawa taking the rope down the
  fixed line to the camp below, at Base Camp saying they are at the bottom,
  resumed by `let's go up again`, the intent resume. The keepsake is a
  photograph from the high point and a white scarf from Dawa, the items
  photograph and scarf, ids 17 and 18, each with `keepsake (kind, text)`. The
  goodbye is `goodbye, dawa`, running dawa_report.
- Dawa's entities: world, player, dawa, teo, base_camp, camp_1, camp_2,
  camp_3, camp_4, south_summit, summit, player_bottle, teo_bottle, spare,
  forecast_1 and forecast_3, ids 1 to 16 in that order, made by dawa_spawn.
  The clock: tick_seconds 1800, ticks_max 48, a day of half hours.
- Dawa's schedule: ord 1 dawa_lib; the step systems dawa_icefall,
  dawa_morning, dawa_exit, dawa_resume, dawa_window, dawa_loads, dawa_push,
  dawa_decide and dawa_keepsake; ord 11 to 14 the tick systems dawa_breathe,
  dawa_move, dawa_rescue and dawa_stop, the last two beyond DB_USE.md 3.9.3,
  as a step system's outputs come before every tick's, so a text worked from
  what the ticks measured is said by a tick system after dawa_move. The split
  beats, by guide split beat, are icefall, morning, window and loads.
- Dawa's components: `camp (name, place, altitude_m, ord UNIQUE, way)` of each
  camp, the top as Summit, place "the top"; `leg (up_minutes, down_minutes)`
  of south_summit and summit; `at (camp)` of the rope, player, dawa and teo,
  the rope moving whole; `climb (to_camp, ticks_left)` with the core's busy
  of a climber under way; `day (minute)` of the world, made by the first
  timed start, in place of the plan's climb.start_minute; of the player `ams
  (grade, hidden)`, `rest (days)`, `load (kg)`, `high (m)`, `exits (count)`,
  and `resume (camp)` while an exit is held; of dawa `limits (load_kg,
  wind_kmh)` and `record (text)`; `bottle (full_l, left_l, kg, holder)` of
  each bottle; `breathe (lpm, bottle)` of the player and teo; `down`, the tag
  of a climber whose bottle ran dry; `forecast (days_ahead UNIQUE, kmh)`; of
  the world `sun (loosen_hour)`, `icefall (hours)`, `kit (tent_kg, stove_kg,
  food_kg)`, `oxygen (camp, climb_lpm, sick_lpm)`, `staging (camp)` and
  `departure (hour)`; `keepsake (kind UNIQUE, text)` of each item. A
  reference column is `INTEGER NOT NULL REFERENCES entity (id)`. The player
  is found as the holder of `ams`, the guide as the holder of `limits`.
- Dawa's ticks: timed moves tick, the icefall from 2:00 for 12 ticks, the
  day ending at 480; the push from 23:00 for 10 ticks, Teo's bottle at 0 and
  the player's at 600 at the 10th; the descent 9 ticks, the spare ending at
  120, the player's bottle at 60 and the day at 510. The Western Cwm, the
  Lhotse Face, the Geneva Spur, the exit, the resume and the summit branch,
  not walked, are instant. The clock ends the walk at step 13, tick 31.
  Teo breathes 4 litres a minute from his own bottle from the spawn, so his
  bottle is measured empty at the South Summit.
- Dawa's arrivals: dawa_stop, once a climber who does not hold `ams`
  breathes from an empty bottle and climbs no more, says the hour, the top
  above and the oxygen reckoned from the legs, the player's bottle and the
  spare, throws when the spare covers both the top and Teo, deletes his
  breathe and adds down; dawa_rescue, once the holder of down breathes from
  the bottle the holder of `limits` carries and climbs no more, says the
  litres drawn, the minutes those litres last at his flow, the player's
  litres in those minutes and the camp reached, and removes down; dawa_move
  says the air only at the end of a climb up, for the holder of `ams`, then a
  night over the sleep rule when there is one. The keepsake decides by no
  climber holding down, the record and the high mark.
- Dawa's report: dawa_report, by SELECTs alone, says `Dawa's spare gave 1080
  of its 1200 litres to bring Teo down to Camp 4, and nobody was left
  behind.`; the told farewell `Dawa takes your hand in both of his. Thank you
  for climbing on my rope. Go slowly, my friend.` The chosen output, the
  spare's full_l less left_l, is measured by dawa_breathe over the descent's
  9 ticks.
- Dawa's policy: he stands in a living culture, by policy flag 5 of guides.md:
  his words stay respectful and plain, the scarf is his gift, and nothing
  makes a ritual a mechanic. Teo is invented. No one dies on either branch:
  on the summit's, Teo is carried in alive and the record is broken.
- Dawa's constants: the summit 8849 m, the 8848.86 m of the survey Nepal and
  China announced on 8 December 2020, rounded; the camps of the South Col
  route as commonly given, Base Camp 5364, Camp 1 6065, Camp 2 6400, Camp 3
  7162, Camp 4 7906 and the South Summit 8749 m; a night's sleep at most 500 m
  higher above 3000 m, by the Wilderness Medical Society Clinical Practice
  Guidelines, 2019 update. The guide's world: the icefall takes 6 hours and
  the sun loosens its ice at 9:00; Dawa's wind limit 40 km/h against forecasts
  of 45 tomorrow and 25 in 3 days; loads at most 12 kg, the tent 4, the stove
  2, food 3 and a bottle 3 kg; 1200 litres a bottle, 2 a minute climbing and 4
  for a sick climber; the push leaves at 23:00 and reaches the South Summit at
  4:00, the top 90 minutes up, 60 back and 270 down to Camp 4. ams, the
  headache's grade, a game rule, gains 1 for a night's sleep more than 500 m
  above the last without bottled oxygen, used from Camp 3 up, and 1 by the
  next morning for a headache hidden. Each is a component value made by
  dawa_spawn with its one line source comment, with the camps' ways, the
  Khumbu Glacier, Khumbu Icefall, Western Cwm, Lhotse Face, Geneva Spur,
  Southeast Ridge and the summit ridge, the staging camp Camp 2, bottled
  oxygen from Camp 3 up, Teo's flow 4, the player holding its own bottle and
  the spare and Teo his, and the legs, the South Summit 300 minutes up from
  Camp 4 and 270 down, the top 90 up and 60 back; the sleep rule's 3000 m
  and 500 m, a published rule, sit in dawa_lib.
- Dawa's air: West's formula, J. B. West, J Appl Physiol 81 (1996) 1850: P =
  exp(6.63268 - 0.1112 h - 0.00149 h^2) mmHg at h km, by Math.exp; the oxygen
  breathed in, 0.2094 (P - 47) mmHg, oxygen's share of dry air and the water
  vapour pressure at 37 C; its share of the sea's, 100 times that over the
  same at 0 km, P0 759.515 and 149.2006. air_text says "NAME, M m: the air
  presses P mmHg, and you breathe in O mmHg of oxygen, PCT percent of what the
  sea gives.", each whole by Math.round: Base Camp 401, 74 and 50; Camp 1 366,
  67 and 45; Camp 2 351, 64 and 43; Camp 4 287, 50 and 34; the South Summit
  256, 44 and 29; the nearest to a rounding boundary Camp 2's oxygen, 63.5976.
  It is kept in dawa_lib as air_text(place, m), the same expression in the
  same order, so the same doubles, said by dawa_spawn, dawa_move,
  dawa_morning, dawa_exit, dawa_resume and dawa_loads.
- guide next purchase: the second half of each keepsake paragraph of
  guides.md, the cowboy RPG, the next town, the other route, is marketing no
  walk can build, and is not built.
- guide deferred after_cases: GUIDES_PLAN.md D5, not built. A list
  `after_cases` of `{holds, reply}`, the first whose text every result holds
  taken, else after_tools, was weighed. Every walked branch is two way and
  `quote` carries the many way outcomes as text, so the list is not built. Its
  design stays here for a guide that needs three paths.
- guide deferred exits in the provider: GUIDES_PLAN.md D7, not built. Script
  gains `exits: {[input: string]: ScriptExit}`, ScriptExit being `{tool_calls,
  after: string, paused: string, resume: string, resume_calls}`; the port
  answers an exit's input in every node before the node's own replies,
  remembers the node it left, holds a paused place of its own whose resume
  input calls resume_calls and returns to the node it left, whose question
  asked again is a node field `ask` the port then needs too. It moves state
  into the port and a field into every node, for a structure the builder
  gives a test table already. It is the design to take when a hand written
  experience, not a test table, needs exits.
- guide deferred demo driving: GUIDES_PLAN.md D10, not built. The demo moves
  onto guide_walk.py's page driving by making the state, key and leave methods
  of guide_walk's run, today the private _GuideRun's state_read, key_press and
  line_type and the left rung's leave, public in the stub, and replacing
  DemoRun's copies. Not done, so that the programs the normal level runs
  change in no line.
- guide deferred serving: GUIDES_PLAN.md D17, not built. Serving a guide's root
  for a person to play, `xsjs_serve.py --guide NAME`, which would make the
  root, write the built table as its seed and serve it, was not asked for. A
  return visit that proves rule 6 of guides.md across sessions is not walked:
  the sims keep their state in the world databases, which persist, and no step
  reloads.

## audit_read

- audit_read.py: `python3 python/audit_read.py PATH [--check] [--guide NAME]`
  prints `audit digest of PATH`, then the audit digest of the document, then,
  when --check or --guide is given, a blank line and the verdict, all on
  stdout, and exits 1 at a failure. It is not standard library only:
  entries_parse imports audit for audit.ShownLog, audit imports jslb and
  internationalization, which reads i18n/en-US.json beside the python
  directory, and databases_check imports substrate.
- audit_read model calls: a call is a request whose url ends in `/responses`
  and whose body holds input, a chain's start when it has no
  previous_response_id, and a reply an answer whose body holds output, usage
  required. A call's record tells its chain and items, a reply's its id,
  cache, text and calls.
- audit_read listing: removed on 2026-11-12, with --digest FILE, by task 1.2.1
  of tmp/tasks_12_0354.md: one line per entry cut at 150 characters, a second
  view of what the digest shows whole. The word digest names the audit digest
  alone, and a redirect of stdout writes it to a file.
- audit digest records: a record is `L` and its entry's line in the audit,
  the seconds from the first entry, the entry's label, a lane as `ai to
  server` or a note's `note of ai`, then what it says, single spaces between;
  its later lines indented 8 spaces, a text's own later lines 10. `==== engine
  start N` then `---- bring up` open each start, and `---- turn K` each input.
- audit digest every entry: every entry of the document has a record, none
  hidden or counted apart, as an audit a person cannot read is no audit: a
  note in its own words, as `note of ai sleeps on 9 until tools.x_reply`,
  what a task waits on; an ai.say request with its text; the media port's
  lines and the replies of render and media.store, a media.store reply with
  its key, size and sha256; a dump whole, as a person asked for it.
- audit digest shown whole: the player's input; each ai.say reply's band with
  its turn, told as the row the reply was stored at, and its scene, told as
  the scene shown, as agent.ts sends the row of the conversation the turn ran
  in and the scene on screen at its end, which differ when a turn changes the
  scene; each model call's chain and items, a user's text, a call output's
  text and a system text; each model reply's cache, text and calls; each MCP
  tools/call and its result; each statement of a sql.run commit with its params; each render's scene, image
  and subtitle; each image request's prompt and answer's sizes; an error or
  fault laid out.
- audit digest same text: a text of a label, as `band: ` or `output call_x: `,
  past _SAME_LENGTH, 80 characters, that a record showed before is told as
  `same as L1812`, that record's line, and a system text so at any length: a
  band repeats the model's last words, a call output its tool's result, a
  model's words a render's subtitle, a chain's restart the prompts.
- audit digest tool call: an MCP tools/call that runs a call of the model's
  last reply not yet run, the same name past its prefix and the same
  arguments, is told in one line by that call's id, as `tool call i=9
  image_make for call_image`, the reply having shown the arguments; any other
  shows its arguments, named as below. Its result is told `tool result r=9 of
  call_image`.
- audit digest one line: the bring up's tap.start and settings.set with the
  switches, engine.start, the MCP handshakes, tools/list with its names,
  db.sync, db.restore and db.file with their size and sha256; the commits
  kv.put with its size and sha256, media.store with its size, kv.delete,
  db.create, db.drop, doc.put with its body, turn.append with its role and
  count of items, the items being the conversation shown already.
- audit digest values: a string past _SAME_LENGTH in a value the digest shows
  as JSON, a call's or a tool's arguments, a document's body, an MCP result or
  a line no other record tells, that a record showed before, as a text or in a
  value, is told as `same as L93`, by the one book of texts shown, so a sim's
  script is shown once whole, at the reply that calls kv_put. Nothing is cut:
  the cuts at 300 and 2000 characters went on 2026-11-12, by task 1.3.1 of
  tmp/tasks_12_0354.md, as a cut hides what the audit recorded.
- audit digest summary: after the records, one line each: the entries, their
  seconds and the engine starts; the model calls, the chains they started,
  the copies of the system prompt sent and the input tokens served from cache
  with the share; each tool called and its count; each commit type and its
  count. The inputs, which the turns show, each lane's bytes as sent and as
  written, a measurement of the audit's own thinning, the copies of the
  prompt written, which --check holds to one, the tool list, which no audit
  holds as each is of debug mode, and the dumps, now shown, went on
  2026-11-12.
- guide_check lines: each line entry's lane, type and kind, request, reply or
  push, is one of _GUIDE_LINES: the bring up's tap.start, settings.set,
  engine.start, MCP handshakes and db.sync with its db.restore and db.file
  pushes; ui.input and ai.say; http.request; mcp; the commits of the Line
  types table; render and media.store with the media port's lane. Every note
  is a sleep of ai or ui, and a dump, the answer to an input of 0 in debug
  mode, passes. A console, permit, error, fault or any other line fails.
- guide_check walk: the first render's subtitle is the gold's served band; the
  ui.input texts are the gold's steps' says, all of them, in order; each
  ai.say request's text is the input before it; each ai.say reply's subtitle
  is its step's band.
- guide_check script: a Python twin of provider_script.ScriptPort's choice
  walks the table from start: a model call ending in call outputs takes the
  pending node's after_tools, or after_lacks when after_holds is in a result
  that lacks it, its text the quote at its path in the last output, then the
  content; any other takes the current node's reply for the last user text in
  normal form, else otherwise. The reply must be the reasoning item, then one
  message of one output_text part of that text unless it is null, then the
  calls' call_id, name and arguments exactly, and nothing else; a difference
  names the item and the node. The normal form is Python's strip and lower,
  which equal JavaScript's trim and toLowerCase on ASCII, as the guides' inputs
  are. A table that would make the port throw is not checked again, as the run
  then fails the failure check first.
- guide_check tools: each MCP tools/call is the next function call of the
  model reply before it: the prefix of the call's name gives its lane, browser
  `ai to ai` and server `ai to server`, and the rest its name, and its
  arguments are the call's arguments text parsed. Every call of a reply runs
  before the next model call. The call outputs ending a model call are their
  tools' result texts, the text parts joined by a newline as agent.result_text
  joins them. Each image request's prompt is that of the image_make call
  before it.
- guide_check proof: on 2026-11-11 the three guides' audits pass; Isaiah's
  audit checked as Ruth's fails at its first input, and planted faults fail
  where planted: a reply's number at the script check, a tool's argument at
  the tool check, and a console line at the lane check.
- audit_read use: only on an end to end run not expected to fail, as
  `build/test_demo/audit.txt` or `audit_tools.txt` after a run with --debug,
  or `build/test_guide_GUIDE/audit.txt`, which a guide program copies there
  after its audit rung passes under --debug, and at a failed rung once the
  root holds an audit. The wire and
  browser tests' roots fail on purpose, and a --check of one is right to exit
  1.
- audit_read --check: exits 1 at the first of these, naming the line: an error
  or fault line; a line of the audit's own type; an HTTP status outside 200 to
  299; an MCP error or isError result; a console read timed out; a credential
  not masked; a note of a program ending with a code not 0; a reply with no
  request; a request with no reply; a sleep whose reply never came; a second
  turn.prompt of one scene; a chained call naming an id no reply of its engine
  start holds, sending a system message, or sending other than exactly the
  outputs answering the calls of the reply it chains from, in order, or after a
  reply with none exactly one user message; a chain's first call not holding
  the prompt once, as its first item; the written bodies of the three lanes
  holding the prompt more than once; an item of the model's output, by its id,
  written in two bodies of those lanes.
- audit_read written again: any script compaction inside a turn, whole or
  partial, makes the next call a restart that writes the reply's items again,
  ids and all, so --check fails it at its last check: the reply that called
  the script is stored after the script ran, so its row follows the summary,
  past where the count from the start stops, and a partial one writes the kept
  rows' items again too. That is redundancy the check exists to show, not a
  fault of the tool. No run meets it, as a script's compaction is disabled.
- audit_read seam: rows appended through the store between turns are sent
  chained after the chain's rows, and --check fails that call as other than the
  new items. No run meets it: a script runs inside a turn, where a row it
  appends lands before the reply's row and so ends the chain.
- audit_read starts: requests and replies are paired within one start of the
  engine, as a reload's ids start again. A console's start heading is no such
  start, and each is counted against the engine's alone.
- audit_read databases_check: databases_check(entries, start, end, scratch)
  copies the directory `start`, a root's databases, to `scratch`, opens each
  database there with substrate.Store at the overflow_bytes and blob_max of
  the record's first tap.start, applies each commit of the record in order,
  the `ai to server` lines of _COMMIT_TYPES, by the store method the server's
  handler calls with that payload, read from its whole line by
  jslb.json_decode as the server read it, then raises AuditFailed at the first
  line where database_lines of `scratch` and of `end` differ, naming
  the database and the table above it. A commit the store refuses, as a
  db.create of a database the start holds, raises AuditFailed naming its line,
  the store's error its cause, so that the guide's text of databases is
  written with that verdict.
- replay kv.put: the record holds no blob's bytes, so a put whose ref a later
  kv.put or kv.delete names, or whose database a later db.drop drops, is
  skipped, as it changes nothing the end holds; any other takes its bytes from
  `end` by Store.kv_get once the row there has the record's size and sha256,
  else raises naming the line.
- replay limits: no other line changes the server's databases, as the server's
  tools write none, and main_loop's own writes at an engine start, the
  settings and the provider's script, come before that start's first line and
  write the same rows again while the settings and the seed stay. A sql.run
  that reads `_kv` would read the replay's rows, not the server's, for a
  skipped put; no script does.
- audit_read database_lines: database_lines(root) is each `NAME.sqlite` of a
  directory in name order as text: `==== NAME`, then each object of
  sqlite_schema in name order by its SQL on one line, or, when an earlier
  database showed the same SQL, as `table _kv: the SQL of _files`, the
  substrate's four tables being in every database; a table's rows after it,
  two spaces in and in the order of all their columns, each cell NULL, a
  number, a string as Python's repr, so that a JSON text keeps its quotes,
  whole, or a BLOB as `b` and the repr of its whole text when it is UTF-8 with
  no control character but newline and tab, else `x'HEX'` up to 32 bytes, as
  a sha256, else `<N bytes>`. A value in the cache shows as its row's NULL
  data. Nothing is cut, as the user asked for the contents, so a row is one
  line however long: the scripted provider's table, the sim's script and the
  reply row whose call carries it are 15 to 55 thousand characters each.
- audit_read repeat_check: repeat_check(entries, table, end, repeated) runs
  the gold's query, repeated's sql and params, on `end`'s repeated.db, opened
  read only and immutable, `file:PATH?mode=ro&immutable=1`, so no -wal or
  -shm file is left in the copy, and raises AuditFailed at the first of these
  that fails, naming
  the line of the audit that shows it: the query gives exactly one row of one
  text, not empty, the text T; the last ai.say reply of the audit, the band
  the player saw last, holds T as a whole token, neither a letter nor a digit
  on either side; the model reply before that ai.say holds T in its
  output_text, so the guide said it; the last model call of the end turn, the
  turn of the last ui.input, holds T in a function_call_output, so a tool
  result carried it; no `content` text of the built table holds T, which
  covers every ask, puzzled, otherwise, after and paused text, as table_build
  folds them into contents, a call's arguments being no content; the end
  turn, from its ui.input to its ai.say reply, commits nothing but
  turn.append, so the guide read T and wrote nothing; and an earlier ai.say
  reply holds T, the first one named, so the output was told when it was made
  and told again at the end. Every "holds T" is by the whole token test. It
  returns the evidence, one line: `repeated: "T" from DB, first said at
  L<first>, said at the end at L<band> by the reply L<reply>, carried by the
  tool result L<result>, in no text of the guide's own, and the last turn
  committed nothing but turns`.
- repeat_check limits: audit_read.py's program does not run it, as it holds
  no copy of the databases. It fits the scripted guide, which repeats by
  quoting; a real model could say 1980 as nineteen eighty, and a real
  provider is tried only by the maintainer, by hand, outside every run. The
  tool result is matched as the call output's JSON text, so a T holding a
  quote, a backslash or a control character would never match; no chosen
  output holds one. A whole token match cannot tell a reckoning from a
  measurement of the same number, so the earlier band may be the one where
  the sim reckoned T, as Dawa's push.
- repeat_check end turn: the entries from the last ui.input before the last
  ai.say reply to that reply. Its model reply is the last one in it, its text
  the output_text parts joined as guide_check joins them. Its tool results
  are the call outputs that end its last model call's items, so a chain
  restart that resends older outputs cannot carry T. A record with a band but
  no input, model reply or model call before it fails loud by ValueError or
  IndexError, as the engine never makes one.
- repeat_check evidence lines: L<first> is the first earlier ai.say reply
  holding T, L<band> the last ai.say reply, L<reply> the end turn's last model
  reply, and L<result> the end turn's last model call, whose
  function_call_output carried T. T is written by json.dumps, ensure_ascii
  false, and the texts of a failure by Python's repr.
- repeat_check table: every string under a key `content` at any depth of the
  built table, named in a failure by its path of members as JSON; arguments,
  quote and next are never contents. Any commit of _COMMIT_TYPES but
  turn.append in the end turn fails, turn.prompt included. The whole token
  test is str.isalnum on the one character each side, trying each occurrence.
  The query opens `file:PATH?mode=ro&immutable=1`, which reads no WAL, so
  both sources close their databases first; a missing database or bad SQL raises
  sqlite3's own error, a broken gold and not an audit failure.
- repeat_check messages, in order: `the query of repeated on DB gives ROWS,
  not one row of one text that is not empty`; `the record holds no ai.say
  reply, so no band holds 'T'`; `line N: the last band 'BAND' does not hold
  'T'`; `line N: the model reply before the last band says 'SAID', which does
  not hold 'T'`; `line N: the last model call of the end turn carries no tool
  result that holds 'T'`; `the table's content at PATH holds 'T', so the guide
  could say it in its own words`; `line N: the end turn commits KIND, where it
  should commit nothing but turn.append`; `line N: no band before the last
  holds 'T', so it was not told when it was made`.
- test_audit_read repeat cases: TestRepeated of python/test_audit_read.py.
  Its setUp writes `end/drive.sqlite` by substrate.Store from the gold's
  repeat_database, tables entity and tally, the herd at 1980. repeat_walk is
  a told walk of two turns, the toll, whose band first says 1980, and the
  goodbye, whose report carries and repeats it; it passes failure_check and
  repeat_check, its evidence the gold's repeat_evidence. repeat_queries fail
  by no row, two rows, a number, an empty text and two columns;
  test_read_only shows a writing query raises sqlite3.OperationalError and
  the rows stay; repeat_cut cuts the walk before its first band; each of
  repeat_failures puts one fault in the walk, band `19800`, reply `No1980`,
  result `21980`, a sql.run in the end turn and first `1980th`, each failing
  its own condition at its own line, the whole token test met by a digit and
  by a letter; repeat_own puts T in the end node's otherwise. Its databases
  are written by the real store in a scratch directory, so the line count
  reaches every line of repeat_check.
