# The shell's runner, the one place the engine starts an external program. At
# levels 1 and 2 the start and the end of the program are notes of console in
# the root's audit, as the console role, the one role that runs a shell, runs
# in debug mode alone.

# Writes a note of console in the audit, which the role has opened.
def console_note(text: str) -> None: ...

# The shell's runner: `argv` at level 0 or 1, `argv_verbose` raw at 2.
def exec(level: int, argv: list[str], argv_verbose: list[str]) -> int: ...
