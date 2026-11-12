# Walks a guide test on the engine page. `table_build` makes the scripted table
# of a guide's directory, `python/guides/NAME/`, from its `table.json`: each
# object `{"$text": FILE}` becomes that file's text less its last newline, and
# `{"$ecs": FILE}` that of FILE in the directory `ecs` beside the guide's, each
# call's `arguments` its JSON text, and each node holding `ask` gains
# `otherwise`, the table's `puzzled` then `ask`, and the exit, whose `calls`
# and `resume_calls` pause and resume there by three nodes of its own.
# `guide_main` serves a fresh debug root under build/ through xsjs_serve.py,
# the built table as its seed, opens the page in chrome-headless-shell, and
# walks the gold's rungs: each step types a line, waits for its band with the
# box enabled, then checks the picture and polls the rows it names. The audit's
# digest goes to build/audit/NAME.txt; the audit must hold no unexpected
# failure, no message the guide does not expect and one engine start; the page
# leaves and ttyd stops with the gold's code. The server's databases at the end
# must be those at the first render with the audit's commits replayed, and the
# rung `repeated` proves the guide said the output the gold's query reads from
# them at the end and before, both written to build/audit/NAME_db.txt. A failed
# rung keeps its PNG and the audit in build/test_guide_NAME/. Exit 0, 1 at the
# first failed check naming its rung, 130 at ctrl C, 128 plus the signal's
# number at SIGHUP or SIGTERM. No real AI provider is contacted.

from typing import Any

# A check of a walk that failed, with the measurement that failed it.
class CheckFailed(Exception): ...

# The scripted table of the guide in `directory`, a `provider_script.Script`.
def table_build(directory: str) -> dict[str, Any]: ...

# Runs the guide test `name` with its program's arguments. The exit code.
def guide_main(arguments: list[str], name: str) -> int: ...
