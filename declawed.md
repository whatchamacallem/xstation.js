# CLAUDE.md is a symlink to declawed.md

## Project Rules

The Project Rules section is set by the project maintainer and must not be
modified without request. The maintainer is the final authority and decides
correctness and requirements, however discrepancies are worth fixing.
Authorship is a legal issue and ascribing authorship to a non-person is a
violation of project rules. Human attribution is required for all
contributions. Do not add contributors to a commit without request.

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
item that is not itself in the postmortem.

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
- Python follows PEP 8. Constants go at the top of each `.py` file, after the
  imports, named like `_VALUE_NAME`. Code ordering requirements come before
  code style rules.
- Don't add whitelist entries for new `.md` files.
- Authorship is a legal issue. Ascribing authorship to a non-person, such as
  a `Co-Authored-By` trailer or a generated-by line in a commit or pull
  request, is a violation of the project rules.

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
  `xsjs_status.ps1`, `test_lint.ps1` and `test_terminal.ps1` run; the user
  runs the rest. All but `xsjs_status.ps1` and `test_lint.ps1` write
  `<script>.ps1.md` beside themselves (gitignored): read it, don't ask.
  The logs are LF Markdown that `mdformat --check` accepts, which
  `test_posix.py` checks through the whitelist's `*.ps1.md` globs, so a log
  written before a writer change fails until its script reruns. mdformat
  doubles backslashes in plain text, so i18n strings put paths in code
  spans.
- `_<file>_main` holds a `trap` that logs and exits 1, then calls
  `_<file>_step_*`; shared code is `xsjs_util_*`. Script state
  (`$log_path_`, `$credential_`, `$stream_`...) is `_main` locals that
  callees read by dynamic scope. Text lives in `powershell/en-US/i18n.psd1`.
- `xsjs_util_invoke_native { ... }` logs output and exit code but never
  throws: check `$LASTEXITCODE` after it.
- Runtime: task `xstation.js` → `conhost.exe --headless` → `powershell.exe
  -File %LOCALAPPDATA%\xstation.js\serve.ps1` → Windows `ttyd.exe` on 5768
  → `wsl.exe -e python3 bootstrap.py`. ttyd for Windows cuts its command at
  256 bytes. That folder also holds the TLS cert and `ttyd.log` (ttyd's
  stderr, first place to look when start fails); `serve.ps1` holds the
  password in plain text.
- `bootstrap.py` is a placeholder; the tests key on its exact `CHALLENGE:`
  and `RESPONSE: <answer>` lines.
- When bootstrap.py exits, the Linux ttyd built from `../ttyd` sends all
  its output but ends the connection with no WebSocket close frame. The
  browser reports that as 1006, and ttyd's page then reconnects at once,
  clearing the screen and starting a new bootstrap.py, unless ttyd runs
  with `-t disableReconnect=true`. Ubuntu's libwebsockets 4.3.5 causes
  this, and ttyd 1.7.7 on it does the same. With 4.3.3, the version the
  1.7.7 release was built with, about 1 close in 10 is still 1006, from a
  ttyd race between the end of output and the exit code. The Windows
  ttyd closes with 1000 but loses `RESPONSE` in about half of tries, as
  in ttyd issue #1429 (open); a lone `test_terminal.ps1` failure may be
  this. ttyd's last release, 1.7.7, the one WinGet installs, dates from
  2024-03-30. Windows builds start at 1.7.0.
- `test_powershell.ps1` (admin) is the whole suite and drives the real
  machine: lint, then stop/install/start/stop, each script in its own
  `powershell.exe`. It ends with a full stop, removing the sign-in task.
- `test_lint.ps1` rewrites files in place (OTBS, LF), fails on CRLF or a
  `<# #>` below the top, and reports but doesn't wrap lines over 79
  columns. Run it in its own `powershell.exe`: PSScriptAnalyzer keeps the
  modules it loads locked until exit.
- Python runs in WSL. `python3 python/test_posix.py` fails on non-UTF-8 or
  non-ASCII outside its `_NON_ASCII_ALLOWED`, formats in place (ruff;
  shfmt with defaults; Markdown is only checked with `mdformat --check`),
  then runs `ruff check`. Files are the globs in
  `python/reformat_whitelist.txt`, which leaves out PowerShell; a glob
  matching nothing fails. `python/pyproject.toml` sets ruff's 79 columns
  (its default 88 rewraps every file) and pyright strict. test_posix.py
  doesn't run pyright: use `pyright --project python`, as pyright finds no
  config from the top directory.
- Screenshots: `python3 python/xsjs_screenshot.py` writes
  `python/xsjs_screenshot.png` (gitignored). It clones `../ttyd`, builds
  it and installs `html/`'s packages, each only when missing, and never
  updates them. It serves `bootstrap.py` from `../ttyd/build/ttyd` on 7681
  behind `corepack yarn run start`, ttyd's dev server on 9000; both ports
  must be free. It drives headless Windows Chrome or Edge over DevTools
  through a C# relay in `powershell.exe`, as WSL's NAT can't reach
  Windows' 127.0.0.1. Chrome reaches WSL's 9000 by localhost forwarding,
  which lags a new listener by about a second. Only the WSL `Browser`
  module exists.
- Windows Chrome outlives its WSL-side process and keeps its profile; a new
  Chrome on that profile hands off to it and exits silently.
- ttyd launched straight from WSL fails with `pty_spawn: 0 (No error)`;
  start it with `Start-Process -NoNewWindow` as `serve.ps1` does.
- Linux ttyd (`../ttyd/build/ttyd`) run from WSL: Windows reaches it on
  `localhost` but not on the PC's LAN address (NAT mode). It pings every 5
  s and closes a WebSocket client that doesn't pong by 10 s. PAUSE (`2`)
  does nothing, as `pty_pause` returns early. Output frames split inside
  UTF-8 characters.
- `ROADMAP.md` holds every barrier met so far, with what was measured
  and the potential solutions; read it before retrying a failed approach.
