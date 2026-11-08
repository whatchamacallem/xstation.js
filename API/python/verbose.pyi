# The server's verbose log and the shell's runner. Outside debug mode a line
# logged goes to the root's `_verbose.sqlite`, held to `blob_max` bytes, so
# that a line past it fails with `SQLITE_FULL`. In debug mode no role opens
# that file, and a line logged is a note of console in the root's audit, as
# the console's start and end of dash are all a server logs there.

# Opens the root's `_verbose.sqlite`, held to `blob_max` bytes.
def log_open(root: str, blob_max: int) -> None: ...

# Closes the file and returns the log to its state before it was opened.
def log_close() -> None: ...

# Writes a line to `_verbose`, or in debug mode a note of console in the audit.
def log(text: str) -> None: ...

# The shell's runner: `argv` at level 0 or 1, `argv_verbose` raw at 2.
def exec(level: int, argv: list[str], argv_verbose: list[str]) -> int: ...
