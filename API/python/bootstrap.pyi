# `python3 bootstrap.py --root <root> [console] [--main-loop NAME]`, the
# command ttyd runs for each connection. Returns the exit code.
#
# Each role reads the root's settings, then the root's parameters,
# `<root>/parameters.json`, by `switches.parameters_load`, and sets its
# switches from them by `switches.switches_apply`, so that every module of
# the server and every child it starts reads the root's: debug mode is
# `switches.debug`. The engine role puts its pty in raw mode, takes the lock
# of the root, reads the settings and the parameters and opens the root's
# log, has the main loop file prepare the root, then writes the first line,
# `tap.start` with the fixed id 101, which carries the settings and the
# root's switches, `switches.switches_get()`, and no gold, which the page
# carries itself; the line goes in full names in debug mode. It reads the
# Empty reply to 101 a byte at a time, then runs the main loop, whose own
# requests take their ids from `dispatch.id_next`, from 102. It reads no provider key and no provider file:
# no program but the test suites runs. `--main-loop` is served to the engine
# role in debug mode only. The console role, in debug mode, gives up the
# pty as its controlling terminal by `TIOCNOTTY` on fd 0, its SIGHUP
# ignored for that call alone and then restored, and runs the console's
# shell, dash in this bubblewrap sandbox, with `-v` after `/bin/dash` at
# level 2, through `verbose.exec` at level 2 when `switches.verbose` is
# true and 1 otherwise, with a scrubbed environment:
#
#     bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --tmpfs /home
#     --tmpfs /mnt --tmpfs /root --unshare-all --new-session
#     --die-with-parent --chdir /tmp python3 -I -c STEP /bin/dash
#
# STEP is this Python of the standard library alone, its statements joined
# by `; ` on one line:
#
#     import fcntl, os, signal, sys, termios
#     os.setsid()
#     fcntl.ioctl(0, termios.TIOCSCTTY, 0)
#     signal.signal(signal.SIGPIPE, signal.SIG_DFL)
#     signal.signal(signal.SIGXFSZ, signal.SIG_DFL)
#     entries = open("/proc/self/environ", "rb").read().split(b"\0")[:-1]
#     given = dict(entry.split(b"=", 1) for entry in entries)
#     os.execve(sys.argv[1], sys.argv[1:], given)
#
# It leads a new session, takes the pty as its controlling terminal, so
# that dash has job control, sets back the two signals Python's start
# ignores, and replaces itself with dash, whose arguments follow STEP, with
# the environment it was given, before Python's start coerced the C locale.
# The console role first refuses a root that is not under `/home/`, which
# the sandbox replaces with an empty tmpfs, so dash starts in the sandbox's
# own `/tmp`, never sees the root, and nothing it writes outlives it.
# Outside debug mode the console role exits 1. A
# failure writes one `error` line, its cascade under `cause`, and exits 1.
# Immediately before it writes that line it sets SIGHUP to be ignored, so
# that the hangup of ttyd's close cannot end it while the line is written:
# it always exits 1 itself, by its return or by the write's own failure.
def bootstrap_run(argv: list[str]) -> int: ...
