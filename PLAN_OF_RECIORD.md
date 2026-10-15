# xstation.js test plan 2

This plan tests one use case. An administrator PowerShell installs WSL and
ttyd in WSL, then serves `bootstrap.py`, which talks to its page in UTF-8
lines through ttyd. You run only the four scripts at the top of the
checkout, and use the page in a browser.

Run every block in one Windows PowerShell opened with Run as administrator,
except where a step says otherwise. PowerShell 5.1 has no `&&`, so the
scripts in a block are joined with `;`. If a script prints `FAILED:`, stop
there. Each script, except `xsjs_status.ps1`, writes its log beside itself
as `<script>.ps1.md`. When start fails, look first at
`%LOCALAPPDATA%\xstation.js\ttyd.log`.

## 1 What the page speaks

1.1 ttyd runs `python3 ~/.cache/xsjs/bootstrap.py ~/.cache/xsjs/modules` on
a terminal with `TERM=dumb`. The terminal stays in its normal line mode.
It echoes each line as it arrives, and `^C` and `^D` mean what they mean in
a shell.

1.2 The bootstrapper writes one banner line, then the prompt `$ `. It
splits each line into words with `sh` quoting but no expansion. The first
word is a module name, and the rest are the module's arguments, so
`echo a 'b c'` runs `~/.cache/xsjs/modules/echo.py` with `sys.argv[1:]`
equal to `['a', 'b c']`.

1.3 Three words are built in: `put NAME` saves the lines that follow, up to
`^D`, as `NAME.py`; `ls` lists the modules with their sizes and SHA-256; and
`restart` replaces the bootstrapper with a fresh copy of itself, keeping its
pid.

1.4 A module runs on the terminal, so it reads the lines you send. `^C`
interrupts it, and `^D` ends its input. When a module exits with a code
other than 0, the bootstrapper prints `<name>: exit <code>`. `^D` at the
prompt ends the session.

1.5 The page has a transcript, an input where Enter sends the text
(Shift+Enter adds a line), and the buttons `^C`, `^D` and Close. A line
can hold 4095 bytes at most. The page refuses a longer line and records it
as a failure, because the terminal would cut it short.

## 2 Setup

The supported checkout is `C:\src\xstation.js`. This machine's checkout is
`\\wsl.localhost\Ubuntu-24.04\home\t\xstation.js`, and with `Bypass` both
work.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
cd \\wsl.localhost\Ubuntu-24.04\home\t\xstation.js
.\xsjs_status.ps1
```

2.1 The status's first line is `xstation.js: stopped; no sign-in start.`
If it says `running`, a start from earlier is still serving. Section 3
stops that one first.

## 3 Install and start

```powershell
.\xsjs_install.ps1; .\xsjs_start.ps1; .\xsjs_status.ps1
```

3.1 Install ends with
`Installed. Next, run xsjs_start.ps1 as administrator.` In
`xsjs_install.ps1.md`, `wsl --version`, `wsl -e true`,
`wsl -e python3 --version`, `wsl -e openssl version` and
`wsl -e ttyd --version` each exited 0, and ttyd reports
`ttyd version 1.7.7`. If a ttyd for Windows from an earlier install is
still there, a notice says it is no longer used and stays installed. That
is expected.

3.2 Start ends with `OK: http://localhost:5768/ (stop: xsjs_stop.ps1)`. In
`xsjs_start.ps1.md`, the section `Writing the task script` shows
`<...>\wsl.exe -e ttyd -p 5769 -i 127.0.0.1 -W -O -T dumb --index /home/t/.cache/xsjs/bootstrap.html python3 /home/t/.cache/xsjs/bootstrap.py /home/t/.cache/xsjs/modules`.

3.3 The status shows, where `<n>` is any number:

```text
xstation.js: running on port 5768; starts at sign-in.
- Scheduled task xstation.js: Running, serves HTTP when <you> signs in, last result 0x41301.
- ttyd in Linux (PID <n>): HTTP on port 5769.
- Port 5768: svchost.exe (PID <n>) listens on 127.0.0.1.
- Port 5769: wslrelay.exe (PID <n>) listens on 127.0.0.1.
- No firewall rule xstation.js.
- Port proxy (v4tov4): 127.0.0.1/5768 -> 127.0.0.1/5769
- WSL: Ubuntu-24.04 (default) is Running.
- Linux port 5769: listening on 127.0.0.1:5769 users:(("ttyd",pid=<n>,fd=<n>))
- bootstrap.py not running in Linux.
```

After that come the task's processes, the files in the state folder
(including `serve.ps1`) and the certificate line. `bootstrap.py not running`
is right while no page is open: ttyd starts one bootstrapper per page.

## 4 The page

4.1 Open `http://localhost:5768/` in a browser. The status reads
`socket open`, then
`ttyd title python3 /home/t/.cache/xsjs/bootstrap.py /home/t/.cache/xsjs/modules (xt)`,
then `ttyd preferences` followed by the text ttyd sent, which is `{ }`
from the ttyd build tested here. The transcript starts with the banner and
the prompt. Note the pid as P:

```text
bootstrap /home/t/.cache/xsjs/bootstrap.py sha256 <S> pid <P> python 3.14.4 modules /home/t/.cache/xsjs/modules
$
```

4.2 Type the lines below into the input, each followed by Enter, except
where a step says to press a button. For a module, type `put NAME` and
press Enter. Then type or paste the module, using Shift+Enter between its
lines and leaving no blank line at its end. Press Enter, then press `^D`.
The transcript must then read exactly as follows, with the module text
echoed as it was sent:

```text
$ ls
$ put echo
import sys

print("argv", sys.argv[1:])
for line in sys.stdin:
    print("got", line, end="")
print("eof")
saved echo.py 107 bytes sha256 4e36b673d8da513fbaac6a13bef8167c1f2b2aa0c21d287e43fc608304c9bf01
$ ls
107 4e36b673d8da513fbaac6a13bef8167c1f2b2aa0c21d287e43fc608304c9bf01 echo.py
$ echo one "two words" héllo
argv ['one', 'two words', 'héllo']
wörld
got wörld
eof
$
```

4.2.1 `ls` prints nothing the first time, because the modules folder is
new.

4.2.2 The size and SHA-256 after `saved` are exact for that text. A
different value means the text differs, for example by a blank line at the
end or a tab in place of four spaces.

4.2.3 After `echo one "two words" héllo`, the module waits on its input.
Type `wörld` and press Enter, and it prints `got wörld`. Press `^D`, and it
prints `eof`, then the prompt returns with no `exit` line, because the
module exited 0.

4.3 Exit codes. Put this module as `code`, then run `code 3`:

```python
import sys

sys.exit(int(sys.argv[1]))
```

The transcript shows `saved code.py 39 bytes sha256 b7b983fe050af118e6a92d4504e898464a8d677154332f6f3e1b51a70c6c24e6`,
then `$ code 3` and `code: exit 3`.

4.4 Interrupt. Put this module as `sleep`, then run `sleep`:

```python
import time

time.sleep(600)
```

4.4.1 The transcript shows `saved sleep.py 29 bytes sha256 5700a8b646e1def50b24642a6fefd16cd899fdc6497dae22a10bbb14af25576c`,
then `$ sleep`.

4.4.2 While the module runs, run `.\xsjs_status.ps1` in PowerShell. It
shows two `- Linux:` lines, for P and for one more pid, with the same
command line,
`python3 /home/t/.cache/xsjs/bootstrap.py /home/t/.cache/xsjs/modules`.
A module is a fork of the bootstrapper, not a new `python3`.

4.4.3 Press `^C`. The transcript shows `^C`, a Python traceback that ends
in `KeyboardInterrupt`, then `sleep: exit -2` and the prompt.
`.\xsjs_status.ps1` then shows one `- Linux:` line, for P.

4.5 Errors. Each line gives exactly one error line, then the prompt:

```text
$ nope
nope: not found
$ echo.py
echo.py: not a module name
$ echo 'open
echo 'open: No closing quotation
$ put
usage: put NAME
```

4.6 With the input empty, press `^C`. The transcript shows `$ ^C`, then a
new prompt on the next line.

4.7 Type `restart`. A new banner follows with the same P and S, then the
prompt.

4.8 Press Close. The status reads
`socket closed code 1000 reason '' wasClean true`, and the input and the
buttons are disabled. `.\xsjs_status.ps1` shows
`bootstrap.py not running in Linux.`

4.9 Open `http://localhost:5768/` again. A new banner has a new pid, and
`ls` lists the modules from before, which stay in
`~/.cache/xsjs/modules`:

```text
39 b7b983fe050af118e6a92d4504e898464a8d677154332f6f3e1b51a70c6c24e6 code.py
107 4e36b673d8da513fbaac6a13bef8167c1f2b2aa0c21d287e43fc608304c9bf01 echo.py
29 5700a8b646e1def50b24642a6fefd16cd899fdc6497dae22a10bbb14af25576c sleep.py
```

Press `^D` with the input empty. The session ends, and the status reads
`socket closed code 1006 reason '' wasClean false`. When its program
exits, Linux ttyd ends the connection without a WebSocket close frame,
which the browser reports as 1006. `.\xsjs_status.ps1` shows
`bootstrap.py not running in Linux.`

4.10 No `failure` line appears in the status at any point. If one does,
write it down with the ttyd version from `xsjs_start.ps1.md`, and don't
reload the page to get past it.

## 5 Soft stop

```powershell
.\xsjs_stop.ps1 --softly; .\xsjs_status.ps1
```

5.1 Stop prints
`Stopped until next sign-in. Restart now: Start-ScheduledTask xstation.js`.

5.2 The status starts with `xstation.js: stopped until next sign-in.` The
task is `Ready`, ttyd shows `ttyd not running.`, port 5769 shows
`Port 5769: not listening.`, and the port proxy
`127.0.0.1/5768 -> 127.0.0.1/5769` stays.

## 6 HTTPS with a password

6.1 This step is optional. Start keeps the certificate in
`%LOCALAPPDATA%\xstation.js` until it expires on 2029-01-14. That
certificate, made 2026-10-11, names `XT`, `localhost` and `127.0.0.1`, but
not the LAN address. To test making a new one that also names the LAN
address, delete `_cached_cert.pem` and `_cached_key.pem` there first.
Browsers that accepted the old certificate will warn once more.

6.2 Pick a throwaway password, put it in place of `<password>`, and run:

```powershell
.\xsjs_start.ps1 xstation-test:<password>; .\xsjs_status.ps1
```

6.2.1 Start ends with
`OK: https://xt:5768/ https://192.168.0.102:5768/ (stop: xsjs_stop.ps1)`,
then `TLS fingerprint (SHA-256): <F>`.

6.2.2 The status starts with
`xstation.js: running on port 5768; starts at sign-in.` It also shows
`serves HTTPS, user xstation-test`,
`ttyd in Linux (PID <n>): HTTPS, user xstation-test on port 5769.`,
`Port 5768: svchost.exe (PID <n>) listens on 0.0.0.0.`,
`Firewall rule xstation.js: TCP 5768 in, enabled True, profile Any.`,
`Port proxy (v4tov4): 0.0.0.0/5768 -> 127.0.0.1/5769` and
`TLS certificate expires <date>, SHA-256 <F>`, with the same F as start.

6.3 Open `https://localhost:5768/`. The browser warns about the certificate,
and the SHA-256 fingerprint it shows must equal F. It then asks for the
user name `xstation-test` and the password. After you sign in, the page
shows the banner and `$ `. `ls` lists the three modules, and `echo hi`
prints `argv ['hi']` and waits; press `^D`. Then press Close. From
another computer on the network, `https://192.168.0.102:5768/` must work
the same way.

## 7 Full stop

```powershell
.\xsjs_stop.ps1; .\xsjs_status.ps1
```

7.1 Stop prints `Stopped. No longer starts at sign-in.`

7.2 The status shows:

- `xstation.js: stopped; no sign-in start.`
- `No scheduled task xstation.js.`
- `ttyd not running.`
- `not listening` for ports 5768 and 5769
- `No firewall rule xstation.js.`
- `No port proxies.`
- `bootstrap.py not running in Linux.`
- the files `ttyd.log`, `_cached_cert.pem` and `_cached_key.pem`, without
  `serve.ps1`, which held the password

## 8 Start at sign-in

```powershell
.\xsjs_start.ps1; .\xsjs_stop.ps1 --softly
```

Restart Windows and sign in. In a PowerShell that doesn't need to be an
administrator, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
cd \\wsl.localhost\Ubuntu-24.04\home\t\xstation.js
.\xsjs_status.ps1
```

8.1 The status starts with
`xstation.js: running on port 5768; starts at sign-in.`, and the task line
shows `last result 0x41301`. `http://localhost:5768/` shows a banner and
`$ `.

8.2 If not, look first at `%LOCALAPPDATA%\xstation.js\ttyd.log`, then at
the task's last result in the status.

8.3 Finish with `.\xsjs_stop.ps1` from an administrator PowerShell.
