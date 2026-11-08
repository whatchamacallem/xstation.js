# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The handlers of the audit, registered in debug mode alone: a page thread's
# record and note into the document, the end of the document back on
# request, and the dumps of both sides' databases at the person's input 0.
# A blob is read whole from memory or from the file the main loop's sink
# finished, which then goes, as nothing names it.

import audit, dispatch, jslb, os, substrate
from internationalization import i18n
from typing import Any, cast


# The state the registration sets, which is empty until then.
class _AuditState:
    # Starts with no bound of a reply and no store.
    def __init__(self) -> None:
        self.line_max: int | None = None
        self.store: substrate.Store | None = None


# The one state of the module.
_STATE = _AuditState()


# The text of blob 1 as `UTF-8`, its sink's file removed once read.
def _blob_text(line: jslb.Object) -> str:
    if 1 not in line:
        kind: str = jslb.field_get(line[0], "type")
        raise ValueError(i18n("engine_audit.blob_missing", kind))
    data: bytes | str = jslb.field_get(line[1], "data")
    if isinstance(data, str):
        with open(data, "rb") as file:
            read = file.read()
        os.remove(data)
        data = read
    return data.decode("utf-8")


# The bound of a reply and the store, raising before the registration.
def _registered() -> tuple[int, substrate.Store]:
    if _STATE.line_max is None or _STATE.store is None:
        raise RuntimeError(i18n("engine_audit.not_registered"))
    return _STATE.line_max, _STATE.store


# `audit.line`: a page thread's record into the document.
def audit_line(
    line: jslb.Object, *, sender: str, receiver: str, at: int
) -> None:
    audit.record_put(sender, receiver, at, _blob_text(line))


# `audit.note`: a page thread's note into the document.
def audit_note(line: jslb.Object, *, thread: str, at: int, text: str) -> None:
    audit.note_put(thread, at, text)


# `audit.tail`: the document's newest entries that fit one reply.
def audit_tail(line: jslb.Object, *, count: int) -> jslb.Object:
    line_max, _ = _registered()
    (empty,) = jslb.line_encode(dispatch.reply_make(line, text=""))
    # The reply's own bytes and its CR, the text's quotes among them.
    limit = line_max - len(cast(bytes, empty))
    return dispatch.reply_make(line, text=audit.tail_read(count, limit))


# `db.dump`: the browser's views from blob 1, then the server's own.
def db_dump(line: jslb.Object) -> None:
    _, store = _registered()
    views = cast(list[dict[str, Any]], jslb.json_decode(_blob_text(line)))
    audit.dump_put(i18n("engine_audit.browser_title"), views)
    own = [store.db_view(name) for name in sorted(store.db_list())]
    audit.dump_put(i18n("engine_audit.server_title"), own)


# Registers the four when `debug` is true, `line_max` bounding the tail.
def handlers_register(
    debug: bool, line_max: int, store: substrate.Store
) -> None:
    if not debug:
        return
    _STATE.line_max = line_max
    _STATE.store = store
    dispatch.handler_register("audit.line", 0, audit_line)
    dispatch.handler_register("audit.note", 0, audit_note)
    dispatch.handler_register("audit.tail", 0, audit_tail)
    dispatch.handler_register("db.dump", 0, db_dump)
