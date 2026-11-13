# Debugging Guide: Chrome and bwrap fail under the test runs

## The goal

The project's tests run in WSL2 Ubuntu 26.04, distribution user `t`, checkout `/home/t/xstation.js`. An agent running inside WSL (Claude Code) cannot start Chrome or bubblewrap. Find out why, and whether the cause is the agent's sandbox or the WSL system itself. Report what you find. Do not change project files.

## How to reach the checkout

From Windows, the checkout is `\\wsl$\<distro>\home\t\xstation.js`. `wsl -l -v` lists the distribution's name. Run commands inside WSL as the user `t`, for example `wsl -d <distro> -u t -- bash -lc "COMMAND"`. Do not write to the Windows drive from WSL. This WSL mounts only `/mnt/c/Users/ajohn/Downloads` of the Windows drive, which is intended.

## What fails

- `./test_posix.sh` fails at the guide walk's browser rung with `ConnectionError: chrome closed its DevTools pipe`, caused by `RuntimeError: chrome exited with -6` (SIGABRT at start).
- The browser is Chrome for Testing 157.0.8103.78, full Chrome run with `--headless`, at `~/.local/share/chrome-for-testing/chrome/linux-157.0.8103.78/chrome-linux64/chrome`. It was installed with `npx @puppeteer/browsers install chrome@stable`, and its `deb.deps` were installed by `apt-get satisfy`.
- `python/devtools.py`, `LinuxPipe.transport_open`, starts it as:
  `chrome --headless --remote-debugging-pipe --user-data-dir=build/devtools-* --window-size=W,H`, with stdin, stdout and stderr on `/dev/null`, DevTools on descriptors 3 and 4, and `XDG_CACHE_HOME` set to the profile.
- `python/bootstrap.py`'s console role runs `bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --tmpfs /home --tmpfs /mnt --tmpfs /root --unshare-all --new-session --die-with-parent --chdir /tmp ...`. Under the agent this fails with `bwrap: No permissions to create a new namespace`.

## What is known

- The agent's shell runs inside Claude Code's sandbox: PID 1 is `sh -c trap exit TERM; sleep infinity & wait`, and `/proc/self/status` shows `Seccomp: 2`. Inside it, `unshare -Ur true` fails with "Operation not permitted".
- Run inside the agent's sandbox, Chrome printed `FATAL: zygote_host_impl_linux.cc:144 No usable sandbox!` and aborted. It needs unprivileged user namespaces, as bwrap does.
- The kernel allows them: `/proc/sys/user/max_user_namespaces` is 96086, and `/proc/sys/kernel/apparmor_restrict_unprivileged_userns` does not exist.
- The maintainer added `/home/t/xstation.js/.claude/settings.local.json`, holding `{"sandbox": {"excludedCommands": ["./test_posix.sh*", "python3 python/test_all.py*"]}}`, and Chrome still aborted with -6. That setting may not apply until Claude Code restarts. It is not yet known whether this second abort was the sandbox again or a different cause.
- The same tests passed on 2026-11-12 in an earlier environment that used chrome-headless-shell 156.

## Steps

Run each step in a plain WSL shell as `t`, outside Claude Code, and keep the output.

1. User namespaces:
   ```
   unshare -Ur true && echo userns-ok
   bwrap --ro-bind / / --unshare-all true && echo bwrap-ok
   ```
2. Chrome alone, with its errors shown:
   ```
   C=$(ls ~/.local/share/chrome-for-testing/chrome/linux-*/chrome-linux64/chrome)
   "$C" --version
   "$C" --headless --dump-dom about:blank 2>&1 | tail -30
   ```
3. Chrome as the tests start it, on the DevTools pipe, with stderr kept:
   ```
   cd /home/t/xstation.js && mkdir -p build/debug
   python3 - <<'EOF'
   import glob, os, subprocess, time
   c = glob.glob(os.path.expanduser("~/.local/share/chrome-for-testing/chrome/linux-*/chrome-linux64/chrome"))[0]
   r3, w3 = os.pipe(); r4, w4 = os.pipe()
   err = open("build/debug/chrome_stderr.txt", "wb")
   p = subprocess.Popen([c, "--headless", "--remote-debugging-pipe",
       "--user-data-dir=build/debug/profile", "--window-size=800,600"],
       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err,
       pass_fds=(r3, w4), preexec_fn=lambda: (os.dup2(r3, 3), os.dup2(w4, 4)))
   time.sleep(5); print("exit code:", p.poll()); p.kill()
   EOF
   tail -30 build/debug/chrome_stderr.txt
   ```
   An exit code of `None` means Chrome stayed up, which is the healthy result.
4. Shared memory and limits, which Chrome needs:
   ```
   ls -ld /dev/shm; df -h /dev/shm; ulimit -a
   ```
5. If steps 1 to 3 pass in the plain shell, the cause is Claude Code's sandbox. Check whether a restarted Claude Code applies `excludedCommands` to `./test_posix.sh` run as a command of its own, with no pipe or `&&` around it.
6. If any step fails in the plain shell too, the cause is in WSL or in Chrome. Look up the first fatal line of Chrome's stderr. Usual suspects:
   - a missing shared library: check `ldd "$C" | grep "not found"`;
   - `/dev/shm` not writable;
   - the WSL kernel's user namespace support, shown by `uname -r` and `cat /proc/sys/kernel/unprivileged_userns_clone`.

## What to report

Write your findings to `/home/t/xstation.js/build/debug_findings.md`. `build/` is ignored by git. Include:
- each step's command and output;
- the first fatal line of Chrome's stderr, if any;
- your conclusion: the agent's sandbox, WSL, or Chrome;
- the fix you recommend, as a command for the maintainer to run.

Do not run `sudo`, install packages or edit files outside `build/`. Installs are the maintainer's to run, and `admin.md` lists the ones made so far.
