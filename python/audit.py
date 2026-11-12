# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The audit document of a root, `_audit.txt`, written in debug mode by the
# server's processes alone. API/python/audit.pyi holds its rules. Each entry is
# one write under an exclusive lock of the file, taken for the check of its
# size and the write, so two processes never interleave or pass `blob_max`,
# and a hard exit loses no entry a process took.

import fcntl, hashlib, jslb, json, os, time
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

# The field of a blob header the server's record adds: its bytes' digest.
_DIGEST_FIELD = "sha256"

# The bytes of a cached blob's file read at a time to hash it.
_HASH_CHUNK = 1048576

# The format of a heading's time of day, then its milliseconds.
_TIME_FORMAT = "%H:%M:%S"

# The format of a start heading's date, before its time.
_DATE_FORMAT = "%Y-%m-%d"

# The lanes of the conversation: the model's requests and replies, the commits.
_REQUEST_LABEL = "ai to http"
_REPLY_LABEL = "http to ai"
_COMMIT_LABEL = "ai to server"
_LANES = (_REQUEST_LABEL, _REPLY_LABEL, _COMMIT_LABEL)

# The commits of the conversation's items.
_PROMPT_TYPE = "turn.prompt"
_TURN_TYPE = "turn.append"

# The field of a line of the provider's port that holds its JSON body.
_BODY_FIELD = "json"

# The fields of a request, a reply and a commit that hold the conversation.
_INPUT_FIELD = "input"
_OUTPUT_FIELD = "output"
_CONTENT_FIELD = "content"
_MESSAGES_FIELD = "messages"
_TOOLS_FIELD = "tools"

# The field of a model request that chains it to the response before it.
_CHAIN_FIELD = "previous_response_id"

# The fields of a model request and of a commit that name the conversation.
_KEY_FIELD = "prompt_cache_key"
_SCENE_FIELD = "scene"

# The end of a line's laid out JSON text, its one brace at the left margin.
_LINE_CLOSE = "\n}"

# The fields of a line that count what the document already shows.
_INPUT_KEPT = "input_kept"
_CONTENT_KEPT = "content_kept"
_MESSAGES_KEPT = "messages_kept"
_TOOLS_KEPT = "tools_kept"


# One entry read back: its start from 1, its time, its label, its body.
class AuditEntry(NamedTuple):
    start: int
    time: str
    label: str
    body: str


# How many of the items lead with the items shown, equal one by one.
def _kept_count(items: list[Any], shown: list[Any]) -> int:
    count = 0
    for given, held in zip(items, shown):
        if given != held:
            break
        count += 1
    return count


# The largest count of the items' leading ones equal to the shown ones' last.
def _tail_count(items: list[Any], shown: list[Any]) -> int:
    for count in range(min(len(items), len(shown)), 0, -1):
        if items[:count] == shown[len(shown) - count :]:
            return count
    return 0


# The fields with the list's first items as their count, a 0 only if `always`.
def _list_cut(
    fields: dict[Any, Any], name: str, counted: str, kept: int, always: bool
) -> dict[Any, Any]:
    cut: dict[Any, Any] = {}
    for key, value in fields.items():
        if key == name and (kept or always):
            cut[counted] = kept
            cut[key] = value[kept:]
        else:
            cut[key] = value
    return cut


# The fields with the list under `name` whole again, the `shown` items first.
def _list_joined(
    fields: dict[Any, Any], name: str, counted: str, shown: list[Any]
) -> dict[Any, Any]:
    joined: dict[Any, Any] = {}
    for key, value in fields.items():
        if key == name:
            joined[key] = [*shown, *value]
        elif key != counted:
            joined[key] = value
    return joined


# The fields with a tool list equal to the one shown written as its count.
def _tools_cut(fields: dict[Any, Any], shown: list[Any]) -> dict[Any, Any]:
    cut: dict[Any, Any] = {}
    for key, value in fields.items():
        if key == _TOOLS_FIELD and isinstance(value, list) and value == shown:
            cut[_TOOLS_KEPT] = len(value)
        else:
            cut[key] = value
    return cut


# The fields with a counted tool list whole again, the one shown.
def _tools_joined(fields: dict[Any, Any], shown: list[Any]) -> dict[Any, Any]:
    joined: dict[Any, Any] = {}
    for key, value in fields.items():
        if key == _TOOLS_KEPT:
            joined[_TOOLS_FIELD] = shown
        else:
            joined[key] = value
    return joined


# Whether a line's JSON body is an object that holds the field.
def _body_holds(line: dict[Any, Any], field: str) -> bool:
    body = line.get(_BODY_FIELD)
    return isinstance(body, dict) and field in body


# What the document shows of each conversation: only what is new goes in.
class ShownLog:
    # Starts having shown nothing.
    def __init__(self) -> None:
        self.items: dict[str, list[Any]] = {}
        self.last: str = ""
        self.tools: list[Any] = []
        self.output: list[Any] = []

    # A conversation's items shown, else those of the one last shown.
    def _items_shown(self, key: str) -> list[Any]:
        return self.items.get(key, self.items.get(self.last, []))

    # Keeps the items a conversation shows, the conversation last shown.
    def _items_put(self, key: str, items: list[Any]) -> None:
        self.items[key] = items
        self.last = key

    # A request's body thin of the items shown: at their end if it is chained.
    def _request_thin(self, body: dict[Any, Any]) -> dict[Any, Any]:
        given = cast(list[Any], body[_INPUT_FIELD])
        shown = self._items_shown(cast(str, body[_KEY_FIELD]))
        if _CHAIN_FIELD in body:
            kept = _tail_count(given, shown)
        else:
            kept = _kept_count(given, shown)
        thin = _list_cut(body, _INPUT_FIELD, _INPUT_KEPT, kept, True)
        thin = _tools_cut(thin, self.tools)
        self._request_moved(body, kept)
        return thin

    # A request's body whole again, the shown state moved alike.
    def _request_whole(self, body: dict[Any, Any]) -> dict[Any, Any]:
        kept = cast(int, body.get(_INPUT_KEPT, 0))
        shown = self._items_shown(cast(str, body[_KEY_FIELD]))
        if _CHAIN_FIELD in body:
            shown = shown[len(shown) - kept :]
        else:
            shown = shown[:kept]
        whole = _list_joined(body, _INPUT_FIELD, _INPUT_KEPT, shown)
        whole = _tools_joined(whole, self.tools)
        self._request_moved(whole, kept)
        return whole

    # Moves the items and tools shown by a whole request, `kept` of it shown.
    def _request_moved(self, body: dict[Any, Any], kept: int) -> None:
        given = cast(list[Any], body[_INPUT_FIELD])
        key = cast(str, body[_KEY_FIELD])
        if _CHAIN_FIELD in body:
            self._items_put(key, [*self._items_shown(key), *given[kept:]])
        else:
            self._items_put(key, list(given))
        tools = body.get(_TOOLS_FIELD)
        if isinstance(tools, list):
            self.tools = cast(list[Any], tools)

    # A reply's body thin, its output held.
    def _reply_thin(self, body: dict[Any, Any]) -> dict[Any, Any]:
        thin = _tools_cut(body, self.tools)
        self.output = cast(list[Any], body[_OUTPUT_FIELD])
        return thin

    # A reply's body whole again, its output held.
    def _reply_whole(self, body: dict[Any, Any]) -> dict[Any, Any]:
        whole = _tools_joined(body, self.tools)
        self.output = cast(list[Any], whole[_OUTPUT_FIELD])
        return whole

    # A turn's commit thin of the output it leads with, its items shown.
    def _append_thin(self, line: dict[Any, Any]) -> dict[Any, Any]:
        content = cast(list[Any], line[_CONTENT_FIELD])
        kept = _kept_count(content, self.output)
        thin = _list_cut(line, _CONTENT_FIELD, _CONTENT_KEPT, kept, False)
        self._append_moved(line)
        return thin

    # A turn's commit whole again, its items shown.
    def _append_whole(self, line: dict[Any, Any]) -> dict[Any, Any]:
        kept = cast(int, line.get(_CONTENT_KEPT, 0))
        output = self.output[:kept]
        whole = _list_joined(line, _CONTENT_FIELD, _CONTENT_KEPT, output)
        self._append_moved(whole)
        return whole

    # Adds a whole commit's content to the items its conversation shows.
    def _append_moved(self, line: dict[Any, Any]) -> None:
        key = cast(str, line[_SCENE_FIELD])
        content = cast(list[Any], line[_CONTENT_FIELD])
        self._items_put(key, [*self._items_shown(key), *content])

    # A prompt's commit thin of the items shown, which become its messages.
    def _prompt_thin(self, line: dict[Any, Any]) -> dict[Any, Any]:
        messages = cast(list[Any], line[_MESSAGES_FIELD])
        key = cast(str, line[_SCENE_FIELD])
        kept = _kept_count(messages, self._items_shown(key))
        thin = _list_cut(line, _MESSAGES_FIELD, _MESSAGES_KEPT, kept, True)
        self._items_put(key, list(messages))
        return thin

    # A prompt's commit whole again, its messages the items shown.
    def _prompt_whole(self, line: dict[Any, Any]) -> dict[Any, Any]:
        kept = cast(int, line.get(_MESSAGES_KEPT, 0))
        key = cast(str, line[_SCENE_FIELD])
        shown = self._items_shown(key)[:kept]
        whole = _list_joined(line, _MESSAGES_FIELD, _MESSAGES_KEPT, shown)
        self._items_put(key, list(whole[_MESSAGES_FIELD]))
        return whole

    # The line moved thin or whole by its lane and kind, else as it is.
    def _line_moved(
        self, label: str, kind: str, line: dict[Any, Any], whole: bool
    ) -> dict[Any, Any]:
        if label == _REQUEST_LABEL and _body_holds(line, _INPUT_FIELD):
            move = self._request_whole if whole else self._request_thin
            return {**line, _BODY_FIELD: move(line[_BODY_FIELD])}
        if label == _REPLY_LABEL and _body_holds(line, _OUTPUT_FIELD):
            move = self._reply_whole if whole else self._reply_thin
            return {**line, _BODY_FIELD: move(line[_BODY_FIELD])}
        if label == _COMMIT_LABEL and kind == _PROMPT_TYPE:
            move = self._prompt_whole if whole else self._prompt_thin
            return move(line)
        if label == _COMMIT_LABEL and kind == _TURN_TYPE:
            move = self._append_whole if whole else self._append_thin
            return move(line)
        return line

    # The line as the document holds it, what the document shows left out.
    def line_thin(
        self, label: str, kind: str, line: dict[Any, Any]
    ) -> dict[Any, Any]:
        return self._line_moved(label, kind, line, False)

    # The line whole again, from what the document shows.
    def line_whole(
        self, label: str, kind: str, line: dict[Any, Any]
    ) -> dict[Any, Any]:
        return self._line_moved(label, kind, line, True)


# The state of the module, which is empty until the document is opened.
class _AuditState:
    # Starts with no file.
    def __init__(self) -> None:
        self.descriptor: int | None = None
        self.path: str | None = None
        self.blob_max = 0
        self.shown: ShownLog | None = None


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
    return _value_layout(cast(dict[Any, Any], jslb.json_decode(text)))


# The body of a line from its value, then the count of its blobs.
def _value_layout(line: dict[Any, Any]) -> str:
    header = cast(dict[str, Any], line[0])
    count = 0
    for field in _BLOB_FIELDS:
        if field in header:
            count = cast(int, header[field])
    body = _json_layout(line)
    if count:
        body += "\n" + i18n("audit.blobs_omitted", count)
    return body


# The JSON text of a line entry's body, the count of its blobs left off.
def _json_text(body: str) -> str:
    return body[: body.index(_LINE_CLOSE) + len(_LINE_CLOSE)]


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
    _STATE.shown = None


# What the document shows, read back the first time this process needs it.
def _shown_get() -> ShownLog:
    _descriptor_get()
    if _STATE.shown is None:
        shown = ShownLog()
        for _, entry in _entries_split(_document_read(cast(str, _STATE.path))):
            heading, _, body = entry.partition("\n")
            label = heading.partition(", ")[2]
            if label in _LANES:
                line = cast(dict[Any, Any], jslb.json_decode(_json_text(body)))
                shown.line_whole(label, jslb.field_get(line[0], "type"), line)
        _STATE.shown = shown
    return _STATE.shown


# The lowercase hex sha256 of a blob's bytes, held or in its cache file.
def _digest_of(data: bytes | str) -> str:
    if isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    digest = hashlib.sha256()
    with open(data, "rb") as file:
        while chunk := file.read(_HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


# The value of a wire line's JSON text, each blob header with its sha256.
def _digests_added(line: jslb.Object) -> dict[Any, Any]:
    value = cast(dict[Any, Any], jslb.json_decode(jslb.line_json(line)))
    number = 1
    while number in value:
        data: bytes | str = jslb.field_get(line[number], "data")
        value[number][_DIGEST_FIELD] = _digest_of(data)
        number += 1
    return value


# A line entry, what the document shows left out of the conversation.
def _record_append(
    sender: str, receiver: str, at: int, line: dict[Any, Any]
) -> None:
    label = i18n("audit.line_label", sender, receiver)
    if label in _LANES:
        kind: str = jslb.field_get(line[0], "type")
        line = _shown_get().line_thin(label, kind, line)
    _text_append(_entry_text(at, label, _value_layout(line)))


# The laid out text of a page thread's record, as the document holds it.
def record_text(sender: str, receiver: str, at: int, text: str) -> str:
    label = i18n("audit.line_label", sender, receiver)
    return _entry_text(at, label, _line_layout(text))


# The laid out text of a note, as the document holds it.
def note_text(thread: str, at: int, text: str) -> str:
    label = i18n("audit.note_label", thread)
    return _entry_text(at, label, _indented(text, _INDENT))


# A line entry of a wire line the server read, its blobs' sha256 added.
def line_received(line: jslb.Object) -> None:
    if not _own_is(line):
        line_value = _digests_added(line)
        _record_append(_WIRE_THREAD, _SERVER_NAME, _now(), line_value)


# A line entry of a wire line the server writes, its blobs' sha256 added.
def line_sent(line: jslb.Object) -> None:
    if not _own_is(line):
        label = i18n("audit.line_label", _SERVER_NAME, _WIRE_THREAD)
        body = _value_layout(_digests_added(line))
        _text_append(_entry_text(_now(), label, body))


# A line entry of a page thread's record.
def record_put(sender: str, receiver: str, at: int, text: str) -> None:
    line = cast(dict[Any, Any], jslb.json_decode(text))
    _record_append(sender, receiver, at, line)


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
