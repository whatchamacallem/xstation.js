# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The audit document of a root, `_audit.txt`, written in debug mode by the
# server's processes alone. API/python/audit.pyi holds its rules. Each entry is
# one write under an exclusive lock of the file, taken for the check of its
# size and the write, so two processes never interleave or pass `blob_max`,
# and a hard exit loses no entry a process took.

import fcntl, jslb, json, os, time
from internationalization import i18n
from typing import Any, NamedTuple, cast

# The file in the root that holds the document.
_FILE_NAME = "_audit.txt"

# The permissions the file is created with: read and write by its owner.
_FILE_MODE = 0o600

# The start of a process's heading, which no line of a body starts with.
_START_MARK = "===="

# The start of an entry's heading, which no line of a body starts with.
_ENTRY_MARK = "----"

# The prefix of every type of the audit's own lines, which are not recorded.
_AUDIT_PREFIX = "audit."

# The server's name in the label of a line entry.
_SERVER_NAME = "server"

# The page thread at the far end of every wire line.
_WIRE_THREAD = "ai"

# The indent of a line's JSON text, as `json.dumps` lays it out.
_JSON_INDENT = 2

# The indent of a note's text and of a dump's database names.
_INDENT = "  "

# How many milliseconds a second counts.
_MILLISECONDS = 1000

# The header fields that count a line's blobs, short and full.
_BLOB_FIELDS = ("b", "blobs")

# The format of a heading's time of day, then its milliseconds.
_TIME_FORMAT = "%H:%M:%S"

# The format of a start heading's date, before its time.
_DATE_FORMAT = "%Y-%m-%d"


# One entry read back: its start from 1, its time, its label, its body.
class AuditEntry(NamedTuple):
    start: int
    time: str
    label: str
    body: str


# The state of the module, which is empty until the document is opened.
class _AuditState:
    # Starts with no file.
    def __init__(self) -> None:
        self.descriptor: int | None = None
        self.path: str | None = None
        self.blob_max = 0


# The one document of the process.
_STATE = _AuditState()


# The document's path in a root.
def _path_of(root: str) -> str:
    return os.path.join(root, _FILE_NAME)


# The descriptor of the open document, raising before it is opened.
def _descriptor_get() -> int:
    if _STATE.descriptor is None:
        raise RuntimeError(i18n("audit.not_open"))
    return _STATE.descriptor


# The time of day of milliseconds since the epoch, to the millisecond.
def _time_text(at: int) -> str:
    seconds, milliseconds = divmod(at, _MILLISECONDS)
    clock = time.strftime(_TIME_FORMAT, time.localtime(seconds))
    return f"{clock}.{milliseconds:03d}"


# The server's clock in milliseconds since the epoch.
def _now() -> int:
    return time.time_ns() // 1_000_000


# Appends the text whole under the file's lock, past `blob_max` refused.
def _text_append(text: str) -> None:
    descriptor = _descriptor_get()
    data = text.encode("utf-8")
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    try:
        size = os.fstat(descriptor).st_size
        if size + len(data) > _STATE.blob_max:
            raise OSError(
                i18n(
                    "audit.full",
                    _STATE.path,
                    size,
                    len(data),
                    _STATE.blob_max,
                )
            )
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


# The text of one entry: its heading, its body and the blank line after it.
def _entry_text(at: int, label: str, body: str) -> str:
    return f"{_ENTRY_MARK} {_time_text(at)}, {label}\n{body}\n\n"


# Each line of the text indented, an empty line left empty.
def _indented(text: str, indent: str) -> str:
    return "\n".join(
        indent + line if line else line for line in text.split("\n")
    )


# A value laid out over many lines by `json.dumps`, its text kept as it is.
def _json_layout(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=_JSON_INDENT)


# The body of a line from its JSON text, then the count of its blobs.
def _line_layout(text: str) -> str:
    line = cast(dict[int | str, Any], jslb.json_decode(text))
    header = cast(dict[str, Any], line[0])
    count = 0
    for field in _BLOB_FIELDS:
        if field in header:
            count = cast(int, header[field])
    body = _json_layout(line)
    if count:
        body += "\n" + i18n("audit.blobs_omitted", count)
    return body


# Whether a line is one of the audit's own, which no entry records.
def _own_is(line: jslb.Object) -> bool:
    kind = cast(str, jslb.field_get(line[0], "type"))
    return kind.startswith(_AUDIT_PREFIX)


# Opens the root's document for appending and writes the role's start heading.
def audit_open(root: str, blob_max: int, role: str) -> None:
    if _STATE.descriptor is not None:
        raise RuntimeError(i18n("audit.open_twice"))
    path = _path_of(root)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC
    _STATE.descriptor = os.open(path, flags, _FILE_MODE)
    _STATE.path = path
    _STATE.blob_max = blob_max
    at = _now()
    date = time.strftime(_DATE_FORMAT, time.localtime(at // _MILLISECONDS))
    started = i18n("audit.started", role, date, _time_text(at), os.getpid())
    _text_append(f"{_START_MARK} {started} {_START_MARK}\n\n")


# Closes the document and returns the module to its state before the open.
def audit_close() -> None:
    os.close(_descriptor_get())
    _STATE.descriptor = None
    _STATE.path = None
    _STATE.blob_max = 0


# The laid out text of a page thread's record, as the document holds it.
def record_text(sender: str, receiver: str, at: int, text: str) -> str:
    label = i18n("audit.line_label", sender, receiver)
    return _entry_text(at, label, _line_layout(text))


# The laid out text of a note, as the document holds it.
def note_text(thread: str, at: int, text: str) -> str:
    label = i18n("audit.note_label", thread)
    return _entry_text(at, label, _indented(text, _INDENT))


# A line entry of a wire line the server read, but the audit's own lines.
def line_received(line: jslb.Object) -> None:
    if not _own_is(line):
        _text_append(
            record_text(
                _WIRE_THREAD, _SERVER_NAME, _now(), jslb.line_json(line)
            )
        )


# A line entry of a wire line the server writes, written before the line.
def line_sent(line: jslb.Object) -> None:
    if not _own_is(line):
        _text_append(
            record_text(
                _SERVER_NAME, _WIRE_THREAD, _now(), jslb.line_json(line)
            )
        )


# A line entry of a page thread's record.
def record_put(sender: str, receiver: str, at: int, text: str) -> None:
    _text_append(record_text(sender, receiver, at, text))


# A note of a thread.
def note_put(thread: str, at: int, text: str) -> None:
    _text_append(note_text(thread, at, text))


# A value with its integer keys first in order, then its names in order.
def _value_ordered(value: object) -> object:
    if isinstance(value, dict):
        source = cast(dict[object, object], value)
        pairs = [(str(key), held) for key, held in source.items()]
        numbers = sorted(
            (pair for pair in pairs if pair[0].isdigit()),
            key=lambda pair: int(pair[0]),
        )
        names = sorted(pair for pair in pairs if not pair[0].isdigit())
        return {key: _value_ordered(held) for key, held in numbers + names}
    if isinstance(value, list):
        return [_value_ordered(item) for item in cast(list[object], value)]
    return value


# The text of a cell of a table: a BLOB as its marker, any other as JSON.
def _cell_value(cell: object) -> object:
    if isinstance(cell, dict):
        size = cast(dict[str, int], cell)["bytes"]
        return i18n("audit.bytes_omitted", size)
    return cell


# The lines of a database's rows: each key and size, its text below it.
def _rows_layout(view: dict[str, Any], indent: str) -> list[str]:
    lines = [indent + i18n("audit.rows_title", len(view["rows"]))]
    for row in view["rows"]:
        kind = row["kind"]
        lines.append(
            indent
            + _INDENT
            + i18n("audit.row_heading", row["key"], row["size"])
        )
        if kind == "text":
            shown = row["text"]
        elif kind == "binary":
            shown = i18n("audit.bytes_omitted", row["size"])
        else:
            shown = i18n("audit.value_lost", row["key"])
        lines.append(_indented(shown, indent + _INDENT * 2))
    return lines


# The lines of a database's documents: each current ref, its body below it.
def _documents_layout(view: dict[str, Any], indent: str) -> list[str]:
    lines = [indent + i18n("audit.documents_title", len(view["documents"]))]
    for document in view["documents"]:
        lines.append(indent + _INDENT + document["ref"])
        body = _json_layout(_value_ordered(document["body"]))
        lines.append(_indented(body, indent + _INDENT * 2))
    return lines


# The lines of a database's tables: each name and columns, a row a line.
def _tables_layout(view: dict[str, Any], indent: str) -> list[str]:
    lines = [indent + i18n("audit.tables_title", len(view["tables"]))]
    for table in view["tables"]:
        columns = ", ".join(table["columns"])
        lines.append(
            indent
            + _INDENT
            + i18n("audit.table_heading", table["name"], columns)
        )
        for row in table["rows"]:
            cells = [_cell_value(cell) for cell in row]
            text = json.dumps(cells, ensure_ascii=False)
            lines.append(indent + _INDENT * 2 + text)
    return lines


# The lines of a database's schema: each statement indented.
def _schema_layout(view: dict[str, Any], indent: str) -> list[str]:
    lines = [indent + i18n("audit.schema_title", len(view["schema"]))]
    for statement in view["schema"]:
        lines.append(_indented(statement, indent + _INDENT))
    return lines


# The text of one database's view, laid out for a person.
def _view_layout(view: dict[str, Any]) -> str:
    inner = _INDENT * 2
    lines = [_INDENT + i18n("audit.database_title", view["db"])]
    lines += _rows_layout(view, inner)
    lines += _documents_layout(view, inner)
    lines += _tables_layout(view, inner)
    lines += _schema_layout(view, inner)
    lines.append(
        inner
        + i18n(
            "audit.hidden",
            view["versions_hidden"],
            view["turns_hidden"],
            view["scenes_hidden"],
        )
    )
    return "\n".join(lines)


# A dump entry of one side's views, in name order, under its title.
def dump_put(title: str, views: list[dict[str, Any]]) -> None:
    ordered = sorted(views, key=lambda view: cast(str, view["db"]))
    body = "\n".join(_view_layout(view) for view in ordered)
    _text_append(_entry_text(_now(), title, body))


# The document's text, read whole under a shared lock of the file.
def _document_read(path: str) -> str:
    with open(path, "rb") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_SH)
        try:
            data = file.read()
        finally:
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)
    return data.decode("utf-8")


# Splits a document into its entries' texts and their starts, in order.
def _entries_split(text: str) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    start = 0
    lines: list[str] | None = None
    for line in text.split("\n"):
        if line.startswith(_START_MARK) or line.startswith(_ENTRY_MARK):
            if lines is not None:
                entries.append((start, "\n".join(lines)))
                lines = None
            if line.startswith(_START_MARK):
                start += 1
                continue
            lines = [line]
        elif lines is not None:
            lines.append(line)
    if lines is not None:
        entries.append((start, "\n".join(lines)))
    return entries


# The newest whole entries, at most `count`, whose text fits below `limit`.
def tail_read(count: int, limit: int) -> str:
    _descriptor_get()
    entries = _entries_split(_document_read(cast(str, _STATE.path)))
    kept: list[str] = []
    size = 0
    for _, entry in reversed(entries[max(0, len(entries) - count) :]):
        text = entry.rstrip("\n") + "\n\n"
        # Measured as the JSON string a reply carries, its quotes left off.
        size += len(json.dumps(text, ensure_ascii=False).encode("utf-8")) - 2
        if size >= limit:
            break
        kept.append(text)
    kept.reverse()
    return "".join(kept)


# The entries of a root's document in order, the demo test's check.
def entries_read(root: str) -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    for start, entry in _entries_split(_document_read(_path_of(root))):
        heading, _, body = entry.partition("\n")
        when, _, label = heading.removeprefix(_ENTRY_MARK + " ").partition(
            ", "
        )
        entries.append(AuditEntry(start, when, label, body.rstrip("\n")))
    return entries
