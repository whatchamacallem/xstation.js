# `python3 bootstrap.py --root <root> [console] [--main-loop NAME]`, the
# command ttyd runs for each connection. Returns the exit code.
#
# Each role sets its switches from the root's parameters. The engine role
# writes the first line, `tap.start`, which carries the settings and the root's
# switches and no gold, which the page carries itself. It reads no provider key
# and no provider file: no program but the test suites runs. `--main-loop` is
# served to the engine role in debug mode only.
#
# The console role, in debug mode only, runs dash in a bubblewrap sandbox with
# a scrubbed environment. A step of Python before dash takes the pty as its
# controlling terminal, so that dash has job control, sets back the two signals
# Python's start ignores and restores the environment from before Python's
# start coerced the C locale. The role refuses a root that is not under
# `/home/`, which the sandbox replaces with an empty tmpfs, so dash never sees
# the root and nothing it writes outlives it.
#
# A failure writes one `error` line, its cascade under `cause`, and exits 1.
# Immediately before that line it ignores SIGHUP, so that the hangup of ttyd's
# close cannot end it while the line is written.
def bootstrap_run(argv: list[str]) -> int: ...
