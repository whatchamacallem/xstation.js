# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The test harness beside `unittest`: the one door by which a test module
# reads settings.json, at the checkout's top, and the gold record of expected
# test results, one file per suite, test_setting_<suite>.json beside the
# suite's module: python/ for python, ts/ for typescript and powershell/ for
# powershell. It imports the standard library only, so it sits below every
# module, and its texts are plain English. Each file is read once, with
# `json`, at the first call that needs it. An id is a key, nested keys joined
# by `.`: the language, the suite, then the keys of the suite's file. The
# copies are deep, so a test that builds a page or a root from them changes
# nothing the harness holds.

import copy, json, os
from typing import Any, cast

# The public names of this module, as its stub declares them.
__all__ = [
    "gold_copy",
    "gold_get",
    "setting_get",
    "settings_copy",
]

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The name of the settings file, as the refusal of an id names it.
_SETTINGS_NAME = "settings.json"

# The settings file at the checkout's top.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, _SETTINGS_NAME)

# The directory of each language's suites, which holds their gold files.
_LANGUAGE_DIRECTORIES = {
    "python": "python",
    "typescript": "ts",
    "powershell": "powershell",
}

# The start and the end of a suite's gold file name, around the suite.
_GOLD_PREFIX = "test_setting_"
_GOLD_SUFFIX = ".json"

# What the refusal of an id names when the id names no suite's file.
_GOLD_NAME = "the gold"

# The mark joining an id's keys.
_ID_MARK = "."

# The module's state: each file read so far, by its path.
_STATE: dict[str, Any] = {}


# Returns the object of the file at `path`, read at the first call only.
def _file_read(path: str) -> Any:
    if path not in _STATE:
        with open(path, encoding="utf-8") as file:
            _STATE[path] = json.load(file)
    return _STATE[path]


# Returns the value under each key in turn, refusing in the name given.
def _keys_follow(name: str, value: Any, keys: list[str], id: str) -> Any:
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(f"{name} has no value with id {id!r}")
        value = cast(dict[str, Any], value)[key]
    return value


# The file name of a suite's gold, as the checkout and a root name it.
def _file_name(suite: str) -> str:
    return f"{_GOLD_PREFIX}{suite}{_GOLD_SUFFIX}"


# The suites of a language that have a gold file, in sorted order.
def _suites_list(directory: str) -> list[str]:
    names = sorted(os.listdir(os.path.join(_ROOT_PATH, directory)))
    return [
        name[len(_GOLD_PREFIX) : -len(_GOLD_SUFFIX)]
        for name in names
        if name.startswith(_GOLD_PREFIX) and name.endswith(_GOLD_SUFFIX)
    ]


# Every suite's gold of a language, `{suite: gold}`, each file read once.
def _language_read(directory: str) -> dict[str, Any]:
    return {
        suite: _file_read(
            os.path.join(_ROOT_PATH, directory, _file_name(suite))
        )
        for suite in _suites_list(directory)
    }


# A value of `settings.json`. Raises `KeyError` on an unknown id.
def setting_get(id: str) -> Any:
    keys = id.split(_ID_MARK)
    return _keys_follow(_SETTINGS_NAME, _file_read(_SETTINGS_PATH), keys, id)


# A value of the gold. Raises `KeyError` naming the suite's file or the gold.
def gold_get(id: str) -> Any:
    keys = id.split(_ID_MARK)
    if keys[0] not in _LANGUAGE_DIRECTORIES:
        raise KeyError(f"{_GOLD_NAME} has no value with id {id!r}")
    directory = _LANGUAGE_DIRECTORIES[keys[0]]
    if len(keys) == 1:
        return _language_read(directory)
    relative = os.path.join(directory, _file_name(keys[1]))
    path = os.path.join(_ROOT_PATH, relative)
    if not os.path.isfile(path):
        raise KeyError(f"{relative} has no value with id {id!r}")
    return _keys_follow(relative, _file_read(path), keys[2:], id)


# A deep copy of the whole of `settings.json`, as a root's settings start.
def settings_copy() -> dict[str, Any]:
    return copy.deepcopy(_file_read(_SETTINGS_PATH))


# A deep copy of every suite's file, `{language: {suite: gold}}`.
def gold_copy() -> dict[str, Any]:
    return copy.deepcopy(
        {
            language: _language_read(directory)
            for language, directory in _LANGUAGE_DIRECTORIES.items()
        }
    )
