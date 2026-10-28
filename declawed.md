# CLAUDE.md is a symlink to declawed.md

## Project Rules

The Project Rules section and subsections are set by the project maintainer
and must not be modified without request. The maintainer is the final
authority and decides correctness and requirements, however discrepancies are
worth fixing. No code was written by the maintainer. Authorship is a legal
issue and ascribing authorship to a non-person is a violation of project
rules. Human attribution is required for all contributions. Do not add
contributors to a commit without request.

Do not use the AskUserQuestion tool and use numbered number sub-lists per ISO
2145. Maintain an engineering log for each session in `tmp/` following this
format: `tmp/tasks_$day_of_month_$24_hours_and_minutes.md`. This is formal
paperwork with no chit chat required. Text is only added and not modified. Use
ISO 2145 for tasks and do not restart numbering tasks within a single
conversation. Preserve the users literal text in the task list first, and
concatenate additional feature requests to that section. In a second section,
list your intended order of operations to execute the users requests before
starting. Then add a separate postmortem section only when all subagents are
complete and all tasks are ready for review. Anything like a postmortem at the
end of a run must include all unfinished tasks and lost subagents. Provide the
user with the postmortem text directly in the conversation as well as
providing a link to the task doc. Provide a single sentence bug, task or other
description alongside every in-conversation postmortem reference to a numbered
item that is not itself in the postmortem. Referenced items require enough
context so that no further lookup is required. The task logs are not checked
for column width.

- Lock files by appending a per-task suffix to the filename for the duration.
- The Lookup Accelerator may only contain information that an AI agent wouldn't
already know. No line numbers are allowed as they are fragile.
- Overconstrained goals introduce failure modes that are best resolved by
  conversations with the user that identify the contradictory requirements.
- Overconstrained solutions introduce failure modes that are best resolved by
  conversations with the user that identify missing long term requirements.
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
- System initialization does not have to abide by the rules for how the
  system is used, such as the one synchronization tool and its audit, unless
  it is reasonably convenient for it to do so.
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
- Any urge to add decorative comments, "helpful" extra logging, or stylistic
  polish not asked for anywhere above is banned. Adding borders, tooltips,
  using alpha, adjusting shade, using gradients, adding requested style or
  redesigning on your own initiative is actively unwanted.
- Unintentional invisibility is always a bug, not a style issue.
- When asked to review a commit or unstaged change do not read this document.
  Report inconsistencies with this document only when encountered through
  knowledge gained when it was injected in your context. That is the only self
  healing documentation mechanism needed.
- Do not commit, uncommit, stage, unstage changes in git. If changes become
  staged during a rename then unstage them. `git` is the permission system for
  permanent changes and therefore must be reviewed by a user. The one exception
  is for staging files before running reformatting tools below.
- Do not look at past git commits unless asked or debugging. Deletion of code
  and documents by the maintainer may indicate a desire to remove the
  information from the conversation instead of waiting for AI to re-read it.
- Do not reference `CLAUDE.md` or `declawed.md` outside this doc. Do not
  explicitly mention the tests being tested themselves in other source.
- The source formatters may need to run twice to be stable. Alert the user
  if they are not.
- If a source reformatting tool can be used to fix an error then stage the
  file to be modified in git and run the tool. Then check the diff and if
  you believe there was an error the change can be reverted and applied
  manually.
- An explicit formatting escape, such as a `<!-- prettier-ignore -->` line, is
  legal when there is no normal solution.
- Do not iterate on formatting `.md` documents. If there is a setting forcing
  you to reformat this document then it has to be disabled, inform the user.
- Never add un-requested documentation because you saw some was missing. Only
  document new code and prefer 1 line comments. Comments are not required:
  the one line limit is an allowance for sentences that improve
  comprehension and optimize code lookup times.
- Provide links to screenshots showing changes in all postmortems.
- Always ask to have required apt packages installed and do not use any package
manager without request.
- Python must not run command line utilities without the maintainer's
  approval. Use the standard library instead.
- Python follows PEP 8. Constants go at the top of each `.py` file, after the
  imports, named like `_VALUE_NAME`. Code ordering requirements come before
  code style rules.
- PowerShell constants go in `settings.json`.
- Each `.py` file imports its modules as `import a, b, c` in alphabetical
  order on one line, or on the fewest lines that stay within 79 columns.
  `from` is banned, except that `collections.abc` and `typing` always use
  `from`, each on one line with its names in alphabetical order, and
  `from internationalization import i18n` is the expected form of the import
  of `i18n()`, expected in most modules.
- New source files are added to the reformat whitelist without asking, when
  they are created: top-level files by name, files in subdirectories by
  glob. `.md` files are never added. A source file the whitelist misses is a
  discrepancy to fix, not a file to leave unchecked. Do not suggest
  additions to the whitelist.
- Function and class identifiers carry two English names; modules and
  their test modules are the exception. The rule is overridden any time
  the maintainer specifies a different identifier.
- Authorship is a legal issue. Ascribing authorship to a non-person, such as
  a `Co-Authored-By` trailer or a generated-by line in a commit or pull
  request, is a violation of the project rules.
- Intermediates, such as tool caches and Python bytecode, go in `build/`,
  which is gitignored. Point each tool there instead of ignoring what it
  writes beside the sources.
- Always use the reformatting tools to reformat code when needed instead of
  doing it manually. Stage code for this reason first if safety is required.
- Define 2 categories of test suite `smoke-test` and `normal-test`. Have
  `test_posix.sh` run by default whatever important test suites fit in 2
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
