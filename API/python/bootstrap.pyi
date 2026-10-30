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
# runs. The console role, in debug mode, runs the console's shell, dash in
# this bubblewrap sandbox, with `-v` after `/bin/dash` at level 2, through
# `verbose.exec` at the setting `verbose_level` with a scrubbed environment:
#
#     bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --tmpfs /home
#     --tmpfs /mnt --tmpfs /root --unshare-all --new-session
#     --die-with-parent --chdir /tmp /bin/dash
#
# Dash starts in the sandbox's own `/tmp`, never sees the root, and nothing
# it writes outlives it. Outside debug mode the console role exits 1. A
# failure writes one `error` line, its cascade under `cause`, and exits 1.
def bootstrap_run(argv: list[str]) -> int: ...
