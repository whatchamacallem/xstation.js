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
# ttyd's source from the package manager. `debug` and `verbose` are carried
# and read, and nothing changes by them yet.

import argparse

anthropic: bool
debug: bool
verbose: bool

# Adds `--anthropic`, `--debug` and `--verbose` to the parser.
def options_add(parser: argparse.ArgumentParser) -> None: ...

# Turns on each switch the parsed options give, here and in its children.
def switches_set(parsed: argparse.Namespace) -> None: ...

# The three switches by name, as `tap.start` carries them.
def switches_get() -> dict[str, bool]: ...
