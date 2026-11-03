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
# import; the three options; switches_set, which turns on in the module and
# in the environment the switches the options give and no other; a root's
# parameters file, written by parameters_write and read by parameters_load,
# which refuses a file that is not an object, a missing or extra key and a
# value that is not a bool, its numbers read by the decoders; and
# switches_apply, which sets each switch and its variable on or off. The
# expected texts are the gold's, python/test_setting_test_switches.json.

import argparse, harness, importlib, jslb, json, os, switches, tempfile
import unittest
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

# The checkout's build directory, where each test makes its scratch root.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The file of a root that holds its parameters, as the stub names it.
_PARAMETERS_NAME = "parameters.json"

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_switches"


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


# A text of this module's gold, each `{n}` replaced by the value `n`.
def text_fill(name: str, *values: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    for index, value in enumerate(values):
        text = text.replace("{" + str(index) + "}", value)
    return text


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


# Tests the parameters file of a root, written and read.
class TestParameters(unittest.TestCase):
    # Makes the scratch root under build/.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.root = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.path = os.path.join(self.root, _PARAMETERS_NAME)

    # Writes the text as the root's parameters file.
    def text_write(self, text: str) -> None:
        with open(self.path, "w", encoding="utf-8") as file:
            file.write(text)

    # Asserts the load refuses the file with exactly the expected text.
    def load_fails(self, expected: str, note: str) -> None:
        with self.assertRaises(ValueError, msg=note) as context:
            switches.parameters_load(self.root)
        self.assertEqual(str(context.exception), expected, note)

    # Each write is read back as written, the three by name.
    def test_parameters_written(self) -> None:
        for bits in range(1 << len(_VARIABLES)):
            parameters = {
                name: bool(bits >> index & 1)
                for index, name in enumerate(_VARIABLES)
            }
            switches.parameters_write(self.root, parameters)
            with open(self.path, encoding="utf-8") as file:
                self.assertEqual(json.load(file), parameters)
            loaded = switches.parameters_load(self.root)
            self.assertEqual(loaded, parameters)
            self.assertEqual(list(loaded), list(_VARIABLES))

    # A file whose JSON is not an object is refused naming the file.
    def test_parameters_object(self) -> None:
        for text in ("[]", "true", "null", '"debug"'):
            self.text_write(text)
            expected = text_fill("switches_parameters_not_object", self.path)
            self.load_fails(expected, text)

    # Each missing key is refused, naming the file and the key.
    def test_parameter_missing(self) -> None:
        for name in _VARIABLES:
            parameters = {other: False for other in _VARIABLES}
            del parameters[name]
            self.text_write(json.dumps(parameters))
            expected = text_fill(
                f"switches_parameter_missing_{name}", self.path
            )
            self.load_fails(expected, name)

    # A key that names no switch, the old setting `verbose_level` among, fails.
    def test_parameter_extra(self) -> None:
        for name in ("extra", "verbose_level"):
            parameters: dict[str, object] = {
                other: False for other in _VARIABLES
            }
            parameters[name] = False
            self.text_write(json.dumps(parameters))
            expected = text_fill(f"switches_parameter_extra_{name}", self.path)
            self.load_fails(expected, name)

    # A value that is not a bool is refused, naming its key and the value.
    def test_parameter_type(self) -> None:
        cases = (("anthropic", 1), ("debug", "true"), ("verbose", None))
        for name, value in cases:
            parameters: dict[str, object] = {
                other: False for other in _VARIABLES
            }
            parameters[name] = value
            self.text_write(json.dumps(parameters))
            expected = text_fill(f"switches_parameter_type_{name}", self.path)
            self.load_fails(expected, name)

    # The decoders read the file, refusing a number that overflows a double.
    def test_parameters_door(self) -> None:
        self.text_write(
            '{"anthropic": false, "debug": 1e400, "verbose": false}'
        )
        with self.assertRaises(jslb.WireError) as context:
            switches.parameters_load(self.root)
        expected = text_fill("jslb_number_overflow")
        self.assertEqual(str(context.exception), expected)


# Returns the switches and the three variables, after `switches_apply`.
def apply_run(parameters: dict[str, bool]) -> dict[str, Any]:
    switches.switches_apply(parameters)
    return {
        "switches": switches.switches_get(),
        "variables": {
            name: os.environ.get(variable)
            for name, variable in _VARIABLES.items()
        },
    }


# Tests `switches_apply`, from every switch off and from every switch on.
class TestApply(unittest.TestCase):
    # Each switch takes its parameter, its variable `1` when on, else unset.
    def test_apply_each(self) -> None:
        for start in (False, True):
            for bits in range(1 << len(_VARIABLES)):
                parameters = {
                    name: bool(bits >> index & 1)
                    for index, name in enumerate(_VARIABLES)
                }

                def run() -> dict[str, Any]:
                    if start:
                        arguments = [f"--{name}" for name in _VARIABLES]
                        options_run(arguments)
                    return apply_run(parameters)

                expected = {
                    "switches": parameters,
                    "variables": {
                        name: "1" if on else None
                        for name, on in parameters.items()
                    },
                }
                note = f"from {start} to {parameters}"
                self.assertEqual(child_run(run), {_VALUE_KEY: expected}, note)


if __name__ == "__main__":
    unittest.main()
