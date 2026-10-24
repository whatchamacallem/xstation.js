# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The test harness beside `unittest`: the one door by which a test module
# reads settings.json and test_settings.json, the gold record of expected
# test results, both at the checkout's top. It imports the standard library
# only, so it sits below every module, and its texts are plain English. Each
# file is read once, with `json`, at the first call that needs it. An id is
# a key, nested keys joined by `.`. The copies are deep, so a test that
# writes a root's files from them changes nothing the harness holds.

import copy, json, os
from typing import Any

# The public names of this module, as its stub declares them.
__all__ = ["gold_copy", "gold_get", "setting_get", "settings_copy"]

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The names of the two files, as the refusal of an id names them.
_SETTINGS_NAME = "settings.json"
_TESTS_NAME = "test_settings.json"

# The settings file and the gold record at the checkout's top.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, _SETTINGS_NAME)
_TESTS_PATH = os.path.join(_ROOT_PATH, _TESTS_NAME)

# The module's state: each file read so far, by its path.
_STATE: dict[str, Any] = {}


# Returns the object of the file at `path`, read at the first call only.
def _file_read(path: str) -> Any:
    if path not in _STATE:
        with open(path, encoding="utf-8") as file:
            _STATE[path] = json.load(file)
    return _STATE[path]


# Returns the value an id names in the file, each part a key of an object.
def _value_find(name: str, path: str, id: str) -> Any:
    value: Any = _file_read(path)
    for part in id.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(f"{name} has no value with id {id!r}")
        value = value[part]
    return value


# A value of `settings.json`. Raises `KeyError` on an unknown id.
def setting_get(id: str) -> Any:
    return _value_find(_SETTINGS_NAME, _SETTINGS_PATH, id)


# A value of `test_settings.json`. Raises `KeyError` on an unknown id.
def gold_get(id: str) -> Any:
    return _value_find(_TESTS_NAME, _TESTS_PATH, id)


# A deep copy of the whole of `settings.json`, as a root's settings start.
def settings_copy() -> dict[str, Any]:
    return copy.deepcopy(_file_read(_SETTINGS_PATH))


# A deep copy of the whole of `test_settings.json`, as a root's copy starts.
def gold_copy() -> dict[str, Any]:
    return copy.deepcopy(_file_read(_TESTS_PATH))
