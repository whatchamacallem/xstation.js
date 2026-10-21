# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the `verbose.put` and `verbose.tail` lines: the lines of the
# page threads go into the `_verbose` database in debug mode only, and the
# last lines of a thread go back on request, the server's from its own ring
# and those of a page thread from the database.

import dispatch, jslb, verbose
from i18n import i18n

# The thread whose lines the server's own ring holds.
_SERVER_THREAD = "server"

# The fields of a line from the page, and no others.
_LINE_FIELDS = {"at", "text"}


# The state the registration sets, which is empty until then.
class _VerboseState:
    # Starts with no debug setting.
    def __init__(self) -> None:
        self.debug: bool | None = None


# The one state of the module.
_STATE = _VerboseState()


# Raises unless the handlers are registered and debug mode is on.
def _debug_check() -> None:
    if _STATE.debug is None:
        raise RuntimeError(i18n("engine_verbose.not_registered"))
    if not _STATE.debug:
        raise RuntimeError(i18n("engine_verbose.debug_off"))


# Reads one line of the page, raising unless it has the two typed fields.
def _line_read(entry: dict[str, object]) -> verbose.LogLine:
    if set(entry) != _LINE_FIELDS:
        raise ValueError(i18n("engine_verbose.line_invalid", entry))
    at = entry["at"]
    text = entry["text"]
    if type(at) is not int or type(text) is not str:
        raise ValueError(i18n("engine_verbose.line_invalid", entry))
    return verbose.LogLine(at, text)


# Writes the lines of the page thread to `_verbose`, in debug mode only.
def verbose_put(
    line: jslb.Object, *, thread: str, lines: list[dict[str, object]]
) -> None:
    _debug_check()
    verbose.lines_put(thread, [_line_read(entry) for entry in lines])


# Replies with the last `count` lines of the thread, oldest first.
def verbose_tail(line: jslb.Object, *, thread: str, count: int) -> jslb.Object:
    if thread == _SERVER_THREAD:
        entries = verbose.history_get(count)
    else:
        entries = verbose.tail_get(thread, count)
    return dispatch.reply_make(
        line,
        lines=[{"at": entry.at, "text": entry.text} for entry in entries],
    )


# Registers both handlers, with debug mode as the gate of `verbose.put`.
def handlers_register(debug: bool) -> None:
    _STATE.debug = debug
    dispatch.handler_register("verbose.put", 0, verbose_put)
    dispatch.handler_register("verbose.tail", 0, verbose_tail)
