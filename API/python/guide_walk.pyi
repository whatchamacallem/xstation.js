# Walks a guide test on the engine page. `table_build` makes the scripted
# table of a guide's directory, `python/guides/NAME/`, from its `table.json`:
# each object `{"$text": FILE}` becomes that file's text less its last
# newline, each call's `arguments` its JSON text, and each node holding `ask`
# gains `otherwise`, the table's `puzzled` then `ask`, and the table's exit,
# answered there by three nodes of its own that pause, then resume there with
# `ask` again. `guide_main` serves a fresh debug root under build/ through
# the functions of xsjs_serve.py, the built table as its seed, opens the page
# in chrome-headless-shell, and walks the rungs of the gold of
# test_guide_NAME.py: each step types a line and waits for its band with the
# box enabled, then checks the picture and polls the rows of the server's
# databases it names. Then the audit must hold no unexpected failure and one
# engine start, the page leaves and ttyd stops with the gold's code. A run
# that passes removes its work directory; a failed rung keeps it, with its PNG
# and the audit in build/test_guide_NAME/. Exit 0, 1 at the first failed check
# naming its rung, 130 at ctrl C, 128 plus the signal's number at SIGHUP or
# SIGTERM. No real AI provider is contacted.

from typing import Any

# A check of a walk that failed, with the measurement that failed it.
class CheckFailed(Exception): ...

# The scripted table of the guide in `directory`, a `provider_script.Script`.
def table_build(directory: str) -> dict[str, Any]: ...

# Runs the guide test `name` with its program's arguments. The exit code.
def guide_main(arguments: list[str], name: str) -> int: ...
