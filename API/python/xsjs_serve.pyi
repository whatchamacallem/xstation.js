# `python3 python/xsjs_serve.py [--anthropic] [--debug] [--verbose] [--port N]
# [--root PATH] [--fresh]`, standard library only, the POSIX start that stands
# alone from the Windows scripts. `serve_run` builds the engine page, makes the
# root and serves it through ttyd, prints the address alone on stdout and keeps
# serving until SIGINT or SIGTERM, when it stops ttyd's process group and exits
# with ttyd's code. ttyd's log goes to stderr as it comes. The demo test makes
# its roots and starts its ttyd through these functions, so that what it proves
# is what the maintainer runs. `values` is the checkout's settings throughout.
#
# A root is made as the start script makes one: `powershell.runtime_modules`
# and the seed in `python/`, `i18n/en-US.json`, `powershell.root_files`, the
# page and `parameters.json`. Each run makes those anew, removes the audit,
# `_audit.txt`, and the log, `_verbose.sqlite` and its `-wal` and `-shm` files,
# so each serve starts a new record, and keeps the rest, so the maintainer's databases persist. The
# root's engine lock means a second connection, as a second tab, waits 5 s,
# then fails loud on the server and shows the fault screen: one page per root.
#
# ttyd is the one the project built, in a session of its own, so that ctrl C
# reaches this program alone. A ttyd not built raises `xsjs_serve.ttyd_missing`
# and a ttyd that ends before its stop raises `xsjs_serve.ttyd_ended`.

from typing import Any

# ttyd takes SIGTERM when the thread that started it dies, by any signal.

# That signal follows the starting thread, the main thread in every caller.

# A death in the instant between the fork and that request is not covered.

# ttyd serving a root, on `port` or, for 0, the port its log then names.
class TtydServer:
    pid: int
    port: int
    # Starts ttyd and returns once its log names the port it listens on.
    def __init__(
        self, values: dict[str, Any], root: str, port: int
    ) -> None: ...
    # Copies the log to stderr up to the port's line. Returns the port.
    def port_read(self) -> int: ...
    # Copies the rest of the log to stderr, leaving the signals to the waiter.
    def log_copy(self) -> None: ...
    # The page's address on this ttyd, `http://localhost:PORT/`.
    def address_get(self) -> str: ...
    # Returns at SIGINT, SIGTERM or ttyd's end, both left blocked for the stop.
    def signal_wait(self) -> None: ...
    # Stops ttyd's group by SIGTERM, by SIGKILL past a wait. Returns its code.
    def server_stop(self) -> int: ...

# The serve program's root, `root` under `powershell.linux_folder` of home.
def root_default(values: dict[str, Any]) -> str: ...

# Builds the engine page from `html/engine.html`. Returns its path in `build/`.
def page_ready(values: dict[str, Any]) -> str: ...

# Makes the root from the built page: its audit and log go, or with `fresh` all.
def root_make(
    values: dict[str, Any],
    page: str,
    root: str,
    parameters: dict[str, bool],
    fresh: bool,
) -> None: ...

# ttyd's command line: the start script's options, the root's `bootstrap.py`.
def ttyd_arguments(
    values: dict[str, Any], root: str, port: int
) -> list[str]: ...

# Serves by the arguments after the program's name. Returns the exit code.
def serve_run(argv: list[str]) -> int: ...
