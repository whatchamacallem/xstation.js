# The three switches of a run, `--anthropic`, `--debug` and `--verbose`, as
# global bools of this module in every process of the run. A program with a
# command line takes them by `options_add` and `switches_set`, which also
# puts each one given in the environment, `XSJS_ANTHROPIC`, `XSJS_DEBUG` or
# `XSJS_VERBOSE` set to `1`, so that every child process starts with it,
# ttyd's commands, Node and Chrome included; at import a process reads the
# three from its environment, an unset variable false and any value but `1`
# refused. No switch turns one off. The realms of TypeScript take them in
# `tap.start` (`lines.TapStart.switches`). `anthropic` has the run take the
# parts of Anthropic's cloud container: Playwright's headless shell and
# ttyd's source from the package manager, has `test_posix.py` check nothing,
# and has `test_all.py` take no suite that starts a formatter. `debug` is
# debug mode and `verbose` the console's verbose level, 2 when on and 1
# otherwise.
#
# A server takes its root's instead: `<root>/parameters.json`, the
# parameters of its run, `{"anthropic": bool, "debug": bool, "verbose":
# bool}`, each key required and nothing else, which `parameters_load` reads
# by `jslb.json_decode` and `switches_apply` sets, here and in its children.

import argparse

anthropic: bool
debug: bool
verbose: bool

# Returns whether the variable is on, unset false, refusing a value but `1`.
def variable_read(variable: str) -> bool: ...

# Adds `--anthropic`, `--debug` and `--verbose` to the parser.
def options_add(parser: argparse.ArgumentParser) -> None: ...

# Turns on each switch the parsed options give, here and in its children.
def switches_set(parsed: argparse.Namespace) -> None: ...

# The three switches by name, as `tap.start` carries them.
def switches_get() -> dict[str, bool]: ...

# Reads `<root>/parameters.json`, refusing a missing or extra key, a non bool.
def parameters_load(root: str) -> dict[str, bool]: ...

# Writes the three by name as `<root>/parameters.json`.
def parameters_write(root: str, parameters: dict[str, bool]) -> None: ...

# Sets each switch to its parameter, its variable `1` when true, else unset.
def switches_apply(parameters: dict[str, bool]) -> None: ...
