# Selects on the pty and, when a console is open, its fd; feeds the
# decoder; dispatches each line inside `Store.transaction_run`; writes the
# reply's chunks; pushes `log.line`, `console.output` and `console.exit`
# between tasks; exits on SIGHUP and SIGTERM. On a handler's raise writes
# the `error` line, flushes, and exits 1.
def loop_run(read_fd: int, write_fd: int, root: str, debug: bool) -> None: ...
