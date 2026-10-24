# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The text the engine shows people: the strings of the `en-US.json` file in
# the `i18n` directory, read once at import, with `{0}`, `{1}` placeholders.

import json, os, re
from typing import cast

# The strings file, in the `i18n` directory beside the `python` directory.
_STRINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "i18n",
    "en-US.json",
)

# A placeholder, a decimal index with no leading zero in braces.
_PLACEHOLDER = re.compile(r"\{(0|[1-9][0-9]*)\}")

# The strings, name to text, filled from the strings file once, at import.
_STRINGS: dict[str, str] = {}


# Reads the strings file, a JSON object whose values are all strings.
def _strings_load(path: str) -> dict[str, str]:
    with open(path, encoding="utf-8") as file:
        data: object = json.load(file)
    objects = cast(dict[str, object], data)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a JSON object")
    strings: dict[str, str] = {}
    for name, text in objects.items():
        if not isinstance(text, str):
            raise ValueError(f"{path}: {name!r} is not a string")
        strings[name] = text
    return strings


# Returns the distinct placeholder indices of a text.
def _indices_find(text: str) -> set[int]:
    return {int(index) for index in _PLACEHOLDER.findall(text)}


# Returns the named string with its placeholders filled by the arguments.
def i18n(name: str, *args: object) -> str:
    text = _STRINGS[name]
    indices = _indices_find(text)
    if indices != set(range(len(args))):
        raise ValueError(
            f"{name}: placeholders {sorted(indices)}, arguments {len(args)}"
        )
    return _PLACEHOLDER.sub(lambda match: str(args[int(match[1])]), text)


# Fills the strings table at import, raising unless the file is well formed.
_STRINGS.update(_strings_load(_STRINGS_PATH))
