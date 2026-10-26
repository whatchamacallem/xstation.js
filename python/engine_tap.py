# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The server's end of the TAP run: each `tap.line`, a line of the TypeScript
# stream, the one that crosses the wire, is appended to
# `<root>/tap/typescript.tap` the moment it arrives, unbuffered, so a hang
# leaves every line before it on disk. Any other language is refused: the
# Python stream, the one `tap.run` runs, crosses the other way. When the
# browser fails, the main loop gives its `error` line to `error_take`, which
# logs the cascade and ends the TypeScript stream with a `Bail out!` line,
# so the TAP results are written out whole, before the main loop exits 1
# without an answer.

import dispatch, jslb, os, verbose
from internationalization import i18n
from typing import cast

# The languages whose TAP streams the server keeps: the one that crosses.
_LANGUAGES = ("typescript",)

# The stream the bail out of the browser's failure ends.
_BAIL_LANGUAGE = "typescript"

# The start of a bail out line, before its reason.
_BAIL_PREFIX = "Bail out! "

# The line breaks a bail out's reason holds as spaces, on its one line.
_LINE_BREAKS = ("\r", "\n")

# The directory in the root that holds the TAP files.
_TAP_DIRECTORY = "tap"

# The extension of a TAP file.
_TAP_EXTENSION = ".tap"


# The state the registration sets, which is empty until then.
class _TapState:
    # Starts with no root.
    def __init__(self) -> None:
        self.root: str | None = None


# The one state of the module.
_STATE = _TapState()


# Returns the root, raising before the handler is registered.
def _root_get() -> str:
    if _STATE.root is None:
        raise RuntimeError(i18n("engine_tap.not_registered"))
    return _STATE.root


# Appends the text and a newline to the file of the language, unbuffered.
def _text_append(language: str, text: str) -> None:
    directory = os.path.join(_root_get(), _TAP_DIRECTORY)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, language + _TAP_EXTENSION)
    data = (text + "\n").encode("utf-8")
    with open(path, "ab", buffering=0) as file:
        written = file.write(data)
    if written != len(data):
        message = i18n("engine_tap.write_short", written, len(data), path)
        raise OSError(message)


# `tap.line`: appends the line to the file of its language.
def tap_line(line: jslb.Object, *, language: str, text: str) -> None:
    if language not in _LANGUAGES:
        raise ValueError(i18n("engine_tap.language_unknown", language))
    _text_append(language, text)


# Logs the browser's failure, every cause, then appends `Bail out!` to it.
def error_take(
    message: str, stack: str, cause: dict[str, object] | None
) -> None:
    verbose.log(i18n("engine_tap.browser_failed", message))
    verbose.log(stack)
    inner = cause
    while inner is not None:
        verbose.log(i18n("engine_tap.browser_cause", inner["message"]))
        verbose.log(cast(str, inner["stack"]))
        inner = cast(dict[str, object] | None, inner.get("cause"))
    reason = message
    for mark in _LINE_BREAKS:
        reason = reason.replace(mark, " ")
    _text_append(_BAIL_LANGUAGE, _BAIL_PREFIX + reason)


# Registers the handler, with the root that holds the `tap` directory.
def handlers_register(root: str) -> None:
    _STATE.root = root
    dispatch.handler_register("tap.line", 0, tap_line)
