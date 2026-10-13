# Roadmap

Barriers met while building xstation.js, what was measured, and what
could remove each. Figures are measurements from 2026-10-11 and
2026-10-12; an estimate says so. "Proposed" means not yet tried.

## 1 Windows ttyd drops the last output of a command that exits at once

1.1 What it blocks: the live server runs `python/bootstrap.py` from this
checkout, which prints `RESPONSE: <answer>` and exits.
`test_terminal.ps1` waits for that line, so it can fail with nothing
wrong in this repo. A person using the terminal can miss the last line of
a session.

1.2 Measured: in 5 screenshot runs against the Windows ttyd that WinGet
installs, started by hand, about half of the tries lost the line and were
retried. "About half" is an estimate, as no count was kept. One traffic
recording showed the WebSocket closing 12 ms after bootstrap.py
answered, with no echo. This is the symptom in ttyd issue #1429, "No
ouput on quick processes", open since 2025-03-17 with no comments and no
linked pull request. Reading the source, every Windows release from
1.7.0 to 1.7.7 closes the pseudo console right after the exit callback;
no build was run to check.

1.3 Potential solutions:

1.3.1 Count it first. The maintainer runs `xsjs_start.ps1`, then
`test_terminal.ps1` runs 10 times, as it needs no elevation.

1.3.2 bootstrap.py waits after its last line before it exits. Proposed
for Windows. On Linux a 1 s wait passed 10 of 10 client tries and 10 of
10 screenshot runs, but the loss there had another cause (2).

1.3.3 Whatever replaces bootstrap.py keeps running, so no command exits
right after its output. Then only the tests are exposed.

1.3.4 Build ttyd.exe from ttyd's master with its cross-build.sh, which
uses libwebsockets 4.5.7, and measure. Proposed; running a self-built
ttyd.exe on Windows needs the maintainer's approval.

1.3.5 Run the older Windows releases, 1.7.0 to 1.7.6. Proposed, and
needs approval to download and run them; the source suggests they behave
the same.

1.3.6 Upstream: add these measurements to #1429, or patch ttyd so the
pseudo console's output is read to the end before it is closed.
Proposed; nothing has been filed.

## 2 Linux ttyd's page reconnects and wipes the screen

2.1 What it blocks: `python/xsjs_screenshot.py` uses the Linux ttyd
built from `../ttyd`. With the stock bootstrap.py it made a correct
screenshot in 0 of 26 runs. Five of those reported success with a
screenshot of the reconnected page, so the tool now reads the terminal
again after capturing and fails if the echo is gone.

2.2 Measured: a WebSocket client with no browser received every line, 40
of 40 tries. ttyd then ended the TCP connection without a WebSocket close
frame, which a browser reports as code 1006. ttyd's page reconnects on
any code other than 1000, which it has done since 2019 (0fc275f). It
calls `terminal.reset()` on reconnecting, since 2020-03-07 (339889e), and
ttyd starts a new bootstrap.py.

2.2.1 The missing close frame comes with Ubuntu's libwebsockets 4.3.5.
ttyd master and ttyd 1.7.7 both linked against it gave no close frame in
10 of 10 tries each.

2.2.2 ttyd master linked statically against libwebsockets 4.3.3, the
version the 1.7.7 release was built with, closed with 1000 in 9 of 10
tries. The tenth was 1006, from the race in 3.

2.3 Potential solutions:

2.3.1 Add `-t disableReconnect=true` to the screenshot tool's ttyd
command. Measured: 10 of 10 correct screenshots with stock ttyd and the
stock bootstrap.py. The page then shows its reconnect prompt over the
output. This ttyd option exists since 2020-12-27 (61a9bcd). It awaits
the maintainer's go-ahead. It isn't proposed for `xsjs_start.ps1`, as
Windows ttyd closes with 1000, so its page doesn't reconnect; there the
flag would only stop reconnects after real network faults.

2.3.2 Link libwebsockets 4.3.3 statically. Measured 9 of 10, so it isn't
enough on its own. With this system's newer CMake, libwebsockets 4.3.3
needs `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`. When its configure step
fails, ttyd's build quietly uses Ubuntu's shared libwebsockets instead,
so check with `ldd` that the binary loads no libwebsockets library.

2.3.3 Build libwebsockets 4.3.5 from source and compare it with Ubuntu's
package, to learn whether the fault is that release or Ubuntu's build of
it. Proposed; this decides where a report should go.

2.4 Don't retry by reloading the page. ttyd's page asks "Close terminal?
this will also terminate the command." on unload, which blocks
`Page.navigate`; a retry that reloaded hung for about 175 s, so the retry
was removed. `-t disableLeaveAlert=true` turns the question off; it is
unused.

## 3 ttyd's exit-code race

3.1 Measured once, in 2.2.2: ttyd logged "process killed with signal 0"
instead of "process exited with code 0". The read side saw the end of the
output before the wait thread stored the exit code, which starts at -1.
`src/protocol.c` sends 1000 only when the code is 0, so it sent 1006.
The same code is in 1.7.0, 1.7.7 and master.

3.2 Potential solutions: an upstream patch that waits for the exit code
before choosing the close code, or a report. Proposed; nothing has been
filed. 2.3.1 already hides it from the screenshot tool.

## 4 The screenshot tool runs only on WSL

4.1 The maintainer wants one screenshot tool for WSL, Linux and BSD that
types UTF-8 into bootstrap.py through Chrome, with a module per platform
behind one interface. Only `python/xsjs_screenshot_wsl.py` exists.

4.2 Open questions for the maintainer: what the Linux and BSD modules
should start and point at, and whether the tool should become a pass or
fail test.

4.3 Potential solutions: a `Browser` module for each further platform,
with the contract described in `xsjs_screenshot.py`'s header. A local
Chrome serves DevTools on its own 127.0.0.1, so those modules need no
relay. Not started.

4.4 Weighed and not used, on 2026-10-12:
- Playwright: no BSD, downloads its own browsers, and doesn't get past
  WSL's networking (8.1).
- Selenium: needs a chromedriver matching each Chrome version; judged the
  only option that clearly covers BSD.
- OS screenshot tools: need a display, and WSL here has
  `guiApplications=false`.
- Chrome's one-shot `--screenshot` with `--virtual-time-budget`: can't
  type.
- Wrapping the page in an iframe: blocked by same-origin rules, and
  script-made events are untrusted.

4.5 HTTPS mode: the tool has only been run against plain HTTP. Chrome's
`--ignore-certificate-errors-spki-list` with the certificate's key hash
is proposed for the self-signed certificate (6); untested.

## 5 The server starts at sign-in, not at boot

5.1 The scheduled task triggers at log on. WSL is reported to fail when
run from a task while nobody is signed in (WSL discussion #14261). An
actual reboot and sign-in has never been tested.

5.2 Potential solutions: test a reboot. For unattended restarts,
Windows automatic sign-in was proposed; untried.

5.3 `Stop-ScheduledTask` leaves ttyd running, so the stop script kills
it explicitly (measured).

## 6 HTTPS certificate and firewall

6.1 The certificate is self-signed, so every browser warns, and Chrome
and Edge remember the exception only for a while. It names the computer,
localhost and 127.0.0.1 but not the machine's LAN address, so the
address URL still warns.

6.2 Potential solutions: import the certificate as a trusted root on
each client, or add the LAN address to it. Proposed. The maintainer's
decisions: `_cached_*.pem` file names, one 825-day lifetime, never
replaced before it expires.

6.3 The firewall rule uses profile Any, so it is open on public
networks too; that is the maintainer's choice.

## 7 Running the scripts from the WSL checkout

7.1 Windows' CurrentUser execution policy is RemoteSigned, and scripts
run from `\\wsl.localhost\...` are refused as "not digitally signed".
`-ExecutionPolicy Bypass` for the one process works (measured).
`Unblock-File` doesn't help, as the refusal comes from the path, not the
file. A user running `.\xsjs_install.ps1` from the WSL checkout meets
this. Potential solution: clone to a Windows path such as `C:\src`;
proposed.

7.2 PSScriptAnalyzer loaded from a `\\wsl.localhost` path fails to load
its DLLs ("Operation is not supported", HRESULT 0x80131515). A copy in
Windows' %TEMP% worked; installing it on Windows removed the problem.

7.3 `powershell.exe` started from WSL hung three times on 2026-10-11
while linting, with no output, until stopped after 300 s, 300 s and
200 s; one of them ran on a copy in Windows' %TEMP%, not the WSL path.
Reruns took 2 s and about 6 s, and each file alone took under 1 s. The
cause is unknown and nothing is proven to prevent it.

## 8 Worked around

8.1 WSL here runs in NAT mode and can't reach Windows' 127.0.0.1, where
Windows Chrome serves DevTools. A C# relay, a thread each way, run by
`powershell.exe` over its stdin and stdout, carries the connection; a
relay written with PowerShell's own `CopyToAsync` hung. WSL's mirrored
networking mode would remove the relay; proposed, and it is a setting on
the maintainer's machine, so the tool can't rely on it.

8.2 Windows reaches a port newly opened in WSL late: a port that opened
3 s in loaded at 3.8 s. The tool retries `Page.navigate` while it gets
`net::ERR_CONNECTION_REFUSED`, for up to 60 s.

8.3 Killing the WSL side of `chrome.exe` leaves the Windows process
running and holding its profile; a new Chrome on that profile hands off
to it and exits silently. Chrome took more than 10 s to start on a new
profile, and its helpers hold profile files for a while after it exits.
The tool uses a new profile each run, stops every Windows process with
that profile on its command line, and retries removing the profile for
up to 10 s.

8.4 Windows' pseudo console rewrites output. A space after `CHALLENGE:`
arrived as the cursor move `ESC[1C`, and it can ask for the cursor
position (`ESC[6n`) before showing anything, which `test_terminal.ps1`
answers. Windows PowerShell 5.1 has no `` `e `` escape, so `` "`e" `` is
the letter e; escapes are built with `[char]27`.

8.5 Windows PowerShell 5.1:
- `$name-` parses as `$name` minus something, so names end in `_`.
- Under `-File`, `--softly` lands in `$args`; under `-Command` it binds
  by position. The scripts declare an empty `param()` and read `$args`.
- PSScriptAnalyzer flags variables read by dynamic scope as unused
  (PSReviewUnusedParameter, PSUseDeclaredVarsMoreThanAssignments); those
  findings are suppressed. A `SuppressMessage` Justification must be a
  plain string constant.
- `Invoke-Formatter` writes CRLF, so the lint writes LF back.
  `.gitattributes` has `* -text`, and CRLF fails the lint, by the
  maintainer's decision.
- Shared code is dot-sourced, not a module: a module can't set the
  caller's `$ErrorActionPreference` or read its locals by dynamic scope.
- Bash quoting around `powershell.exe -Command` broke a CIM query
  ("Invalid query", 0x80041017); scripts go in `.ps1` files or through
  `-EncodedCommand`.
- An AI agent's file-writing tool saves without a BOM, which 5.1 needs
  for non-ASCII; add it after writing.

8.6 WinGet:
- Portable packages such as ttyd have no repair (ERROR_NOT_SUPPORTED),
  so a broken ttyd is uninstalled and installed again.
- `Repair-WinGetPackageManager -AllUsers` needs admin, so the repair
  runs without it, and the WinGet module installs for the current user.
- "Module 'Microsoft.WinGet.Client' is currently in use" came from
  PowerShellGet 1.0.0.1's in-use check after `Invoke-ScriptAnalyzer` had
  loaded the module's DLL into the console. Modules are installed only
  when missing, and the lint runs in its own `powershell.exe`.

8.7 ttyd 1.7.4 and later are read-only unless given `--writable`.

8.8 With no target version set, ruff assumes Python 3.10, so its unsafe
fix for PYI034 imports `Self` from `typing_extensions`, which is not in
the standard library; Python here is 3.14. That fix was made by hand.
Setting the target version in `python/pyproject.toml` would prevent it,
but it adds a setting, and the maintainer asked for the minimum config.
`test_posix.py` doesn't run pyright; adding it was not asked for.

## 9 Constraints that rule solutions in or out

9.1 No Docker. Apt packages are installed by the maintainer; so far
libjson-c-dev and libwebsockets-dev. pwsh, shellcheck and Python's
websockets module are not installed; `powershell.exe` works through WSL
interop.

9.2 `../ttyd` is the maintainer's to update. The screenshot tool clones
it, builds it and installs its page's packages only when they are
missing, and uses ttyd unchanged through ttyd's own development setup.

9.3 The agent's shell isn't elevated, so only the maintainer can start,
stop or reinstall the live server. A UAC prompt raised from
`\\wsl.localhost` showed a network-source warning and the maintainer
cancelled it, so it isn't tried again. Windows' `sudo` reports "Sudo is
disabled on this machine" and gsudo isn't installed. A test that
relaunches itself elevated was rejected, as its output would be lost in
the new window. On 2026-10-12 the live server was stopped, so nothing
could be measured against it.

9.4 ttyd's last release is 1.7.7, from 2024-03-30, and WinGet installs
it for the live server. Windows builds start at 1.7.0 (2022-08-08); the
release before it, 1.6.3, dates from 2021-01-03. Release builds used
libwebsockets 4.3.2 at 1.7.0 and 1.7.4 and 4.3.3 at 1.7.7, and master's
cross-build.sh uses 4.5.7. `../ttyd` was cloned at 2922cb8
(2026-08-12).
