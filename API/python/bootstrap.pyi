# `python3 bootstrap.py --root <root> [console] [--main-loop NAME]`, the
# command ttyd runs for each connection. Returns the exit code.
#
# The engine role puts its pty in raw mode, takes the lock of the root, reads
# the settings and opens the root's log, has the main loop file prepare the
# root, then writes the first line, `tap.start` with the fixed id 101, which
# carries the settings and, in debug mode, `<root>/test_settings.json` as
# `test_settings`, read by `jslb.json_decode`, in full names in debug mode.
# It reads the Empty reply to 101 a byte at a time, then runs the main loop,
# whose own requests take their ids from `dispatch.id_next`, from 102. It
# reads no provider key and no provider file: no program but the test suites
# runs. The console role runs dash through `verbose.exec` at the setting
# `verbose_level` in debug mode and exits 1 otherwise. A failure writes one
# `error` line, its cascade under `cause`, and exits 1.
def bootstrap_run(argv: list[str]) -> int: ...
