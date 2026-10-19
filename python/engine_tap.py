# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handler of the `tap.line` line: each line of a test run's TAP stream is
# appended to a file in the root the moment it arrives, so a hang leaves the
# lines before it on disk.

import dispatch, jslb, os
from i18n import i18n

# The languages whose TAP streams the server keeps.
_LANGUAGES = ("python", "typescript")

# The directory in the root that holds the TAP files.
_TAP_DIRECTORY = "tap"

# The extension of a TAP file.
_TAP_EXTENSION = ".tap"


# The state the registration sets, which is empty until then.
class _State:
    # Starts with no root.
    def __init__(self) -> None:
        self.root: str | None = None


# The one state of the module.
_STATE = _State()


# Returns the root, raising before the handler is registered.
def _root_get() -> str:
    if _STATE.root is None:
        raise RuntimeError(i18n("engine_tap.not_registered"))
    return _STATE.root


# Appends the text and a newline to the file of the language, then closes it.
def tap_line(line: jslb.Object, *, language: str, text: str) -> None:
    if language not in _LANGUAGES:
        raise ValueError(i18n("engine_tap.language_unknown", language))
    directory = os.path.join(_root_get(), _TAP_DIRECTORY)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, language + _TAP_EXTENSION)
    with open(path, "ab") as file:
        file.write((text + "\n").encode("utf-8"))


# Registers the handler, with the root that holds the `tap` directory.
def handlers_register(root: str) -> None:
    _STATE.root = root
    dispatch.handler_register("tap.line", 0, tap_line)
