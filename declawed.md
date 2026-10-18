# CLAUDE.md is a symlink to declawed.md

## Project Rules

The Project Rules section and subsections are set by the project maintainer
and must not be modified without request. The maintainer is the final
authority and decides correctness and requirements, however discrepancies are
worth fixing. Authorship is a legal issue and ascribing authorship to a
non-person is a violation of project rules. Human attribution is required for
all contributions. Do not add contributors to a commit without request.

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
- There must be no data loss in the logs from a hard exit because there is no
  buffering beyond a single external command.
- No fake data - every value is a measurement or plain arithmetic on one. If a
  tool can't supply a view's data, the view isn't built.
- Any urge to add decorative comments, "helpful" extra logging, or stylistic
  polish not asked for anywhere above is banned. Adding borders, tooltips,
  using alpha, adjusting shade, using gradients, adding requested style or
  redesigning on your own initiative is actively unwanted.
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
- Do not iterate on formatting `.md` documents. If there is a setting forcing
  you to reformat this document then it has to be disabled, inform the user.
- Never add un-requested documentation because you saw some was missing. Only
  document new code and prefer 1 line comments.
- Provide links to screenshots showing changes in all postmortems.
- Always ask to have required apt packages installed and do not use any package
manager without request.
- Python must not run command line utilities without the maintainer's
  approval. Use the standard library instead.
- Python follows PEP 8. Constants go at the top of each `.py` file, after the
  imports, named like `_VALUE_NAME`. Code ordering requirements come before
  code style rules.
- Each `.py` file imports its modules as `import a, b, c` in alphabetical
  order on one line, or on the fewest lines that stay within 79 columns.
  `from` is banned, except that `collections.abc` and `typing` always use
  `from`, each on one line with its names in alphabetical order.
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

Please consider the effects of Requirements-Data-Loss,
Accidental-Requirements, and Requirements-Refusal at the same time. It is like
requesting a new skyscraper and never getting a call back because they didn't
think you knew how deep a hole they had to dig.

Here are ways to avoid these.

- Nothing concrete exists ahead of the prose that describes it, so there are
  no Accidental-Requirements if nothing is added to the design without being
  motivated by a requirement.
- Injected context and memory notes describe current state, not design. A
  design decision found there is checked against the plan before anything is
  built on it.
- Prevent Requirements-Data-Loss by writing APIs and architecture for as much
  of the system as possible, from the top down, before ever writing any code.
- Write software from the bottom up using unit tests first, and integration
  tests second. Once the APIs are done, the unit tests begin.
- Reuse is chosen by the plan, never by availability. "It exists" is not a
  reason. Code is cheaper than negotiating requirements, and so requirements
  alignment needs to be prioritized over the cost of rewrites.

## Project Direction

### 1 What the project should stop depending on

1.1 The tests key on the last line of a process that exits immediately
after printing it. That is the hardest case for any terminal
multiplexer, and it is not what the product will do: whatever replaces
bootstrap.py is long-lived (ROADMAP 1.3.3). Keep the test, as it is the
regression test for RESEARCH 1, but note in it that a loss there is a
ttyd fault and not a repo fault, so a lone failure is reported with the
ttyd version and not retried silently.

1.2 Do not add waits to bootstrap.py (ROADMAP 1.3.2). A sleep hides the
race instead of removing it and would mask a regression in RESEARCH 1.

1.3 ROADMAP 2.4 stands: never retry by reloading the page.

### 2 Everything else is operations, not research

2.1 Start at boot (ROADMAP 5): one reboot test by the maintainer
decides it. If the log-on trigger is enough, nothing else is needed.

2.2 Certificate (ROADMAP 6): add the LAN address as a subject
alternative name when the certificate is next generated; the 825-day
lifetime decision stands.

2.3 Scripts from the WSL path (ROADMAP 7): document `C:\src` as the
supported checkout for Windows users; `-ExecutionPolicy Bypass` stays
for the agent. The lint hangs in 7.3 are unexplained and nothing here
changes that; keep the 300 s timeout and record each occurrence.

2.4 Screenshot tool on Linux and BSD (ROADMAP 4): blocked on the
maintainer's answers in 4.2 of ROADMAP; no research needed.

## Lookup Accelerator

The Lookup Accelerator section is automatically injected into the context of
every conversation about this project. Update it automatically as a low
priority when it falls behind using the file locking scheme. Do not mention
discrepancies as this is a low priority self healing mechanism.

- Windows code is Windows PowerShell 5.1 (`powershell.exe`, not pwsh). Every
  `.ps1`/`.psd1` must be UTF-8 with BOM and LF, or 5.1 misreads non-ASCII.
- From WSL: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File
  "$(wslpath -w <script>)"`. The agent shell isn't elevated, so only
  `xsjs_status.ps1` and `test_lint.ps1` run; the user runs the rest. All
  but those two write `<script>.ps1.md` beside themselves (gitignored):
  read it, don't ask. The logs are LF Markdown that `mdformat --check`
  accepts; the whitelist names no log, so `test_posix.py` checks none.
  WSL here has `appendWindowsPath = false`: `powershell.exe` is on `PATH`,
  but `wsl.exe`, `net.exe`, `curl.exe` and `explorer.exe` need their
  `/mnt/c/Windows/` paths. mdformat
  doubles backslashes in plain text, so i18n strings put paths in code
  spans.
- `_<file>_main` holds a `trap` that logs and exits 1, then calls
  `_<file>_step_*`; shared code is `xsjs_util_*`. Script state
  (`$log_path_`, `$credential_`, `$stream_`...) is `_main` locals that
  callees read by dynamic scope. Text lives in `powershell/en-US/i18n.psd1`.
- `xsjs_util_invoke_native { ... }` logs output and exit code but never
  throws: check `$LASTEXITCODE` after it.
- Runtime, as the scripts set it up (not yet run as administrator on
  2026-10-15): task `xstation.js` → `conhost.exe --headless` →
  `powershell.exe -File %LOCALAPPDATA%\xstation.js\serve.ps1` →
  `wsl.exe -e ttyd -p 5769 -i 127.0.0.1` → `python3
  ~/.cache/xsjs/bootstrap.py ~/.cache/xsjs/modules`, a copy start makes
  from `python/` on each run. A `netsh` port proxy forwards 5768 (on
  `127.0.0.1`, or `0.0.0.0` with a password) to Windows' 127.0.0.1:5769,
  which `wslrelay` carries into WSL. Stop finds that ttyd with `pgrep` by
  its command line and sends SIGTERM, as ending `wsl.exe` need not end it.
  That folder also holds the TLS cert and `ttyd.log` (ttyd's stderr, first
  place to look when start fails); `serve.ps1` holds the password in plain
  text.
- `bootstrap.py` takes one argument, the modules directory, and is a
  command processor modelled on dash, on ttyd's terminal left in canonical
  mode: a banner line, then `$ `; `shlex` words; the first is a builtin
  (`put NAME` reads to `^D`, `ls`, `restart`) or a module `<name>.py`,
  the rest its `sys.argv[1:]`; `^C` is relayed to the module's group;
  `^D` at the prompt exits 0. No JSON beyond ttyd's own. A module runs in
  an `os.fork` child through `runpy` after `setsid`, never an exec of
  `python3`, so its pid shows the bootstrapper's command line, and a
  module named like a standard module the bootstrapper imported gets that
  one. `restart` execs `sys.orig_argv`. `python/bootstrap.html` is its
  page (`--index`): a transcript with CR removed, an input sent on Enter,
  and `^C`, `^D` and Close buttons; the driver reads `window.boot`.
- The tty echoes input when it arrives, so a driver waits for each
  expected output before sending more. A canonical line holds 4095 bytes
  and the tty silently cuts longer ones, so the page fails on them. `^C`
  flushes the tty's pending input and output. ttyd runs with `-T dumb`
  so Python doesn't colour tracebacks. The page sends no resize; the
  bootstrapper reads no size. ttyd's pty has the kernel's termios
  defaults: `^\` ends the bootstrapper by SIGQUIT, `^Z` is echoed and
  discarded as its group is orphaned, `^S` holds output until `^Q`, and
  `IUTF8` is off, so DEL erases one byte.
- `FORMATS.md` is the registry of every wire, file and URL format and
  constant, under identifiers of two English words, and holds the plan
  for one top-level `settings.json`.
- ttyd with `--credential` answers `/` with 401 but drops `/ws` without
  the Basic header with no HTTP status.
- When its program exits, Linux ttyd on Ubuntu's libwebsockets 4.3.5 (as
  `../ttyd` builds) sends all the output but ends the connection with no
  WebSocket close frame, which the browser reports as 1006; ttyd's stock
  page then reconnects at once unless ttyd runs with
  `-t disableReconnect=true`. Windows ttyd closes with 1000 but loses a
  program's last output in about half of tries, as in ttyd issue #1429
  (open). ttyd's last release, 1.7.7, the one WinGet installs, dates from
  2024-03-30; Ubuntu 26.04 packages it as 1.7.7-4build1. Windows builds
  start at 1.7.0 and cut their command at 256 bytes.
- Ubuntu's `ttyd` package enables `ttyd.service`, which runs
  `ttyd -W -i lo -p 7681 -O login` as root, set in `/etc/default/ttyd`, on
  WSL's 10.255.255.254:7681; installing the package starts it.
- `test_powershell.ps1` (admin) is the whole suite and drives the real
  machine: lint, then stop/install/start/stop, each script in its own
  `powershell.exe`. It ends with a full stop, removing the sign-in task.
- `test_lint.ps1` rewrites files in place (OTBS, LF), fails on CRLF, and
  reports but doesn't wrap lines over 79 columns. Run it in its own
  `powershell.exe`: PSScriptAnalyzer keeps the modules it loads locked
  until exit.
- Python runs in WSL. `python3 python/test_posix.py` fails on non-UTF-8 or
  non-ASCII outside its `_NON_ASCII_ALLOWED`, formats in place (ruff;
  shfmt with defaults; Markdown is only checked with `mdformat --check`),
  then runs `ruff check`. Files are the entries in
  `python/reformat_whitelist.txt`, top-level files by name and
  subdirectory globs, which leave out PowerShell; an entry matching
  nothing fails. Before formatting, its own lexers scan the
  comments of those files and of every PowerShell file: below the
  header (the file's top comment, after any doctype line) a comment is
  one line, not `<# #>`, and outside its code spans holds only letters,
  digits, white space and `_ENGLISH_PUNCT`, so no bare `_`, `-` or `;`.
  Comments support Doxygen markup: write a name, option, value or symbol
  literally in a backtick code span (`C#`, `$null`, `--softly`) rather
  than spelling it out. Comments on consecutive lines are one comment.
  `python/pyproject.toml` sets ruff's
  79 columns (its default 88 rewraps every file) and pyright strict, and
  ignores E401 and I001: ruff has no option that joins `import a, b`
  lines, so the import style is kept by hand.
  test_posix.py doesn't run pyright: use `pyright --project python`, as
  pyright finds no config from the top directory.
- The scripts pass ruff an absolute `--cache-dir` under `build/`. A
  `cache-dir` in `pyproject.toml` still leaves an empty `.ruff_cache` in
  the current directory, and under `--config` its relative path resolves
  from the current directory. Scripts set `sys.pycache_prefix` to
  `build/pycache` before importing a sibling module.
- Screenshots: `python3 python/xsjs_screenshot.py` writes
  `python/xsjs_screenshot.png` (gitignored) in about 5 s. It clones
  `../ttyd` and builds it, each only when missing, and never updates them.
  `../ttyd/build/ttyd` alone serves `bootstrap.html` and `bootstrap.py`,
  with a modules directory made under `build/`, on 7681, which must be
  free; Chrome puts and runs a module, types its stdin and closes. It
  drives headless Windows Chrome or Edge over DevTools through a
  C# relay in `powershell.exe`, as WSL's NAT can't reach Windows'
  127.0.0.1. Chrome reaches WSL's 7681 by localhost forwarding, which lags
  a new listener by about a second. Only the WSL `Browser` module exists.
  `Emulation.setDeviceMetricsOverride` fires `resize` in headless Chrome.
- `python3 python/test_wire.py` is the wire test, about 1 s: Linux ttyd
  on `--port 0`, its port and version read from its log, running a copy
  of `bootstrap.py` made under `build/`, which the update rung rewrites.
- Windows Chrome outlives its WSL-side process and keeps its profile; a new
  Chrome on that profile hands off to it and exits silently.
- Windows `ttyd.exe` launched straight from WSL fails with
  `pty_spawn: 0 (No error)`; `Start-Process -NoNewWindow` starts it.
- Linux ttyd (`../ttyd/build/ttyd`) run from WSL: Windows reaches it on
  `localhost` but not on the PC's LAN address (NAT mode). Bound to WSL's
  127.0.0.1, Windows' 127.0.0.1 reaches it through `wslrelay`, and
  `[::1]` doesn't. `--interface lo` binds WSL's 10.255.255.254, not
  127.0.0.1. It pings every 5 s and closes a WebSocket client that
  doesn't pong by 10 s. PAUSE (`2`) does nothing, as `pty_pause` returns
  early. Output frames split inside UTF-8 characters.
