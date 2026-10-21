# `python3 bootstrap.py --root <root> [console]`. Returns the exit code.
# The engine role takes the lock, sets raw mode, writes `hello` and runs the
# main loop file. The console role runs dash through `verbose.exec` at the
# setting `verbose_level` in debug mode and exits 1 otherwise. Immutable
# outside debug mode.
def bootstrap_run(argv: list[str]) -> int: ...
