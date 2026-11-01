# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the switches of a run. A test that sets a variable or turns a switch
# on runs in a forked child, so that neither this process nor a later suite
# starts with it: the child removes the three switches' variables, imports
# the module again so that it reads its environment as a new process does,
# then writes what it read to a pipe as JSON and ends by os._exit. It tests
# the reading of a variable, unset, on and refused; the bools read at
# import; the three options; and switches_set, which turns on in the module
# and in the environment the switches the options give and no other.

import argparse, importlib, json, os, switches, unittest
from collections.abc import Callable
from typing import Any

# A variable no switch uses, which the tests of reading set in a child.
_TEST_VARIABLE = "XSJS_TEST_SWITCH"

# Each switch and its variable, as the stub names them.
_VARIABLES = {
    "anthropic": "XSJS_ANTHROPIC",
    "debug": "XSJS_DEBUG",
    "verbose": "XSJS_VERBOSE",
}

# What a child's run of a function gave: its value, or its exception.
_VALUE_KEY = "value"
_ERROR_KEY = "error"


# Runs the function in a forked child with a fresh module, returning its JSON.
def child_run(fn: Callable[[], Any]) -> dict[str, Any]:
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        for variable in _VARIABLES.values():
            os.environ.pop(variable, None)
        try:
            importlib.reload(switches)
            given: dict[str, Any] = {_VALUE_KEY: fn()}
        except Exception as error:
            given = {_ERROR_KEY: [type(error).__name__, str(error)]}
        with os.fdopen(write_fd, "w") as file:
            file.write(json.dumps(given))
        os._exit(0)
    os.close(write_fd)
    with os.fdopen(read_fd) as file:
        text = file.read()
    _, status = os.waitpid(pid, 0)
    code = os.waitstatus_to_exitcode(status)
    if code != 0:
        raise RuntimeError(f"the child exited with {code}: {text!r}")
    return json.loads(text)


# Returns the switches and the three variables, after `switches_set`.
def options_run(arguments: list[str]) -> dict[str, Any]:
    parser = argparse.ArgumentParser()
    switches.options_add(parser)
    switches.switches_set(parser.parse_args(arguments))
    return {
        "switches": switches.switches_get(),
        "variables": {
            name: os.environ.get(variable)
            for name, variable in _VARIABLES.items()
        },
    }


# Tests the reading of one variable.
class TestVariable(unittest.TestCase):
    # An unset variable is false.
    def test_variable_unset(self) -> None:
        def read() -> bool:
            os.environ.pop(_TEST_VARIABLE, None)
            return switches.variable_read(_TEST_VARIABLE)

        self.assertEqual(child_run(read), {_VALUE_KEY: False})

    # A variable of `1` is true.
    def test_variable_on(self) -> None:
        def read() -> bool:
            os.environ[_TEST_VARIABLE] = "1"
            return switches.variable_read(_TEST_VARIABLE)

        self.assertEqual(child_run(read), {_VALUE_KEY: True})

    # Any other value is refused, naming the variable and the value.
    def test_variable_refused(self) -> None:
        def read() -> bool:
            os.environ[_TEST_VARIABLE] = "true"
            return switches.variable_read(_TEST_VARIABLE)

        given = child_run(read)
        self.assertEqual(given[_ERROR_KEY][0], "ValueError")
        self.assertIn(_TEST_VARIABLE, given[_ERROR_KEY][1])
        self.assertIn("'true'", given[_ERROR_KEY][1])


# Tests the bools a process reads from its environment at import.
class TestImport(unittest.TestCase):
    # With no variable set every switch is off.
    def test_import_off(self) -> None:
        given = child_run(switches.switches_get)
        expected = {name: False for name in _VARIABLES}
        self.assertEqual(given, {_VALUE_KEY: expected})

    # Each variable set before the import turns on its switch alone.
    def test_import_on(self) -> None:
        for name, variable in _VARIABLES.items():

            def read() -> dict[str, bool]:
                os.environ[variable] = "1"
                importlib.reload(switches)
                return switches.switches_get()

            expected = {other: other == name for other in _VARIABLES}
            self.assertEqual(child_run(read), {_VALUE_KEY: expected}, name)


# Tests the options and `switches_set`.
class TestOptions(unittest.TestCase):
    # No option turns nothing on and sets no variable.
    def test_options_none(self) -> None:
        given = child_run(lambda: options_run([]))
        expected = {
            "switches": {name: False for name in _VARIABLES},
            "variables": {name: None for name in _VARIABLES},
        }
        self.assertEqual(given, {_VALUE_KEY: expected})

    # Each option turns on its switch and sets its variable to `1`, alone.
    def test_options_each(self) -> None:
        for name in _VARIABLES:
            given = child_run(lambda: options_run([f"--{name}"]))
            expected = {
                "switches": {other: other == name for other in _VARIABLES},
                "variables": {
                    other: "1" if other == name else None
                    for other in _VARIABLES
                },
            }
            self.assertEqual(given, {_VALUE_KEY: expected}, name)

    # All three together turn on all three.
    def test_options_all(self) -> None:
        arguments = [f"--{name}" for name in _VARIABLES]
        given = child_run(lambda: options_run(arguments))
        expected = {
            "switches": {name: True for name in _VARIABLES},
            "variables": {name: "1" for name in _VARIABLES},
        }
        self.assertEqual(given, {_VALUE_KEY: expected})


if __name__ == "__main__":
    unittest.main()
