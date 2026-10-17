# `python3 bootstrap.py --root <root> [--debug]`. Puts the pty in raw mode,
# opens the store, writes `hello`, runs `loop_run`. Exits 2 on a bad
# argument. The restart exec is `os.execv(sys.executable, sys.orig_argv)`.
def main(argv: list[str]) -> int: ...
