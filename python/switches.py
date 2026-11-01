# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The three switches of a run, --anthropic, --debug and --verbose, as global
# bools of this module in every process of the run. A program with a command
# line takes them by options_add and switches_set, which also puts each one
# given in the environment, XSJS_ANTHROPIC, XSJS_DEBUG or XSJS_VERBOSE set
# to 1, so that every child process starts with it, ttyd's commands, Node and
# Chrome included; at import a process reads the three from its environment,
# an unset variable false and any value but 1 refused. No switch turns one
# off. The TypeScript realms take them in tap.start, as switches_get gives
# them. anthropic has the run take the parts of Anthropic's cloud container:
# Playwright's headless shell and ttyd's source from the package manager.
# debug and verbose are carried and read, and nothing changes by them yet.

import argparse, os

# The variable of `--anthropic`.
_ANTHROPIC_VARIABLE = "XSJS_ANTHROPIC"

# The variable of `--debug`.
_DEBUG_VARIABLE = "XSJS_DEBUG"

# The variable of `--verbose`.
_VERBOSE_VARIABLE = "XSJS_VERBOSE"

# The value of a switch's variable when the switch is on.
_ON_VALUE = "1"


# Returns whether the variable is on, unset false, refusing a value but `1`.
def variable_read(variable: str) -> bool:
    value = os.environ.get(variable)
    if value is None:
        return False
    if value != _ON_VALUE:
        raise ValueError(
            f"{variable} is {value!r}, neither {_ON_VALUE!r} nor unset"
        )
    return True


# Whether the run is in Anthropic's cloud container, by `--anthropic`.
anthropic = variable_read(_ANTHROPIC_VARIABLE)

# Whether the run's debug switch is on, by `--debug`.
debug = variable_read(_DEBUG_VARIABLE)

# Whether the run's verbose switch is on, by `--verbose`.
verbose = variable_read(_VERBOSE_VARIABLE)


# Adds `--anthropic`, `--debug` and `--verbose` to the parser.
def options_add(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--anthropic",
        action="store_true",
        help="in Anthropic's cloud container: start its headless shell,"
        " Playwright's, in place of /usr/local/bin/chrome-headless-shell, and"
        " build ttyd from the source the package manager gave, in this"
        " process and its children",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="turn on the debug switch, in this process, its children and"
        " the realms they start",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="turn on the verbose switch, in this process, its children and"
        " the realms they start",
    )


# Turns on each switch the parsed options give, here and in its children.
def switches_set(parsed: argparse.Namespace) -> None:
    global anthropic, debug, verbose
    if parsed.anthropic:
        os.environ[_ANTHROPIC_VARIABLE] = _ON_VALUE
        anthropic = True
    if parsed.debug:
        os.environ[_DEBUG_VARIABLE] = _ON_VALUE
        debug = True
    if parsed.verbose:
        os.environ[_VERBOSE_VARIABLE] = _ON_VALUE
        verbose = True


# The three switches by name, as `tap.start` carries them.
def switches_get() -> dict[str, bool]:
    return {"anthropic": anthropic, "debug": debug, "verbose": verbose}
