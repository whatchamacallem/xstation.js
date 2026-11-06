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
# Playwright's headless shell and ttyd's source from the package manager, has
# test_posix.py check nothing, and has test_all.py take no suite that starts a
# formatter.
# debug is debug mode and verbose the console's verbose level, 2 when on and
# 1 otherwise. A server takes its root's instead: <root>/parameters.json,
# the three by name and nothing else, each a bool, which parameters_load
# reads by jslb.json_decode and switches_apply sets, here and in its
# children.

import argparse, jslb, json, os
from internationalization import i18n
from typing import cast

# The variable of `--anthropic`.
_ANTHROPIC_VARIABLE = "XSJS_ANTHROPIC"

# The variable of `--debug`.
_DEBUG_VARIABLE = "XSJS_DEBUG"

# The variable of `--verbose`.
_VERBOSE_VARIABLE = "XSJS_VERBOSE"

# The value of a switch's variable when the switch is on.
_ON_VALUE = "1"

# The file of a root that holds the parameters of its server's run.
_PARAMETERS_NAME = "parameters.json"

# The parameters' names, each that of a switch, and their variables.
_PARAMETER_VARIABLES = {
    "anthropic": _ANTHROPIC_VARIABLE,
    "debug": _DEBUG_VARIABLE,
    "verbose": _VERBOSE_VARIABLE,
}


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
        " Playwright's, in place of /usr/local/bin/chrome-headless-shell,"
        " build ttyd from the source the package manager gave, have"
        " test_posix.py check nothing, and have test_all.py take no suite"
        " that starts a formatter, in this process and its children",
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


# Reads the root's parameters by the decoders, refusing a key or a non bool.
def parameters_load(root: str) -> dict[str, bool]:
    path = os.path.join(root, _PARAMETERS_NAME)
    with open(path, encoding="utf-8") as file:
        data: object = jslb.json_decode(file.read())
    if not isinstance(data, dict):
        raise ValueError(i18n("switches.parameters_not_object", path))
    parameters = cast(dict[str, object], data)
    for name in _PARAMETER_VARIABLES:
        if name not in parameters:
            raise ValueError(i18n("switches.parameter_missing", path, name))
    for name in parameters:
        if name not in _PARAMETER_VARIABLES:
            raise ValueError(i18n("switches.parameter_extra", path, name))
    for name, value in parameters.items():
        if type(value) is not bool:
            raise ValueError(
                i18n("switches.parameter_type", path, name, json.dumps(value))
            )
    return cast(dict[str, bool], parameters)


# Writes the three parameters by name as the root's parameters file.
def parameters_write(root: str, parameters: dict[str, bool]) -> None:
    path = os.path.join(root, _PARAMETERS_NAME)
    text = json.dumps(parameters, indent=2) + "\n"
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


# Sets each switch to its parameter, its variable `1` or removed.
def switches_apply(parameters: dict[str, bool]) -> None:
    global anthropic, debug, verbose
    for name, variable in _PARAMETER_VARIABLES.items():
        if parameters[name]:
            os.environ[variable] = _ON_VALUE
        else:
            os.environ.pop(variable, None)
    anthropic = parameters["anthropic"]
    debug = parameters["debug"]
    verbose = parameters["verbose"]
