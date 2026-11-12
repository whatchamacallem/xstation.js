#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Reads an audit document for a person or an AI, who cannot read it whole: it
# prints the audit digest, every entry told as the player's and the model's
# conversation, a text shown before named by its line, then a summary of what
# the run did. With --check it then stops at the first unexpected failure and
# exits 1, so that a person or a test need not look for one by eye. It is for a
# run that is not expected to fail: the wire and browser tests' roots fail on
# purpose, and the check would be right to refuse them. A line is read whole,
# through `audit.ShownLog`, so a model call counts all it sent though the
# document holds only what was new, and the check then proves that it was new.
# --guide NAME also checks that each message is the one the walk of
# python/guides/NAME expects. databases_check replays the record's commits on
# a copy of a root's databases, database_lines tells databases as text, and
# repeat_check proves that the guide said a sim's output at the end and before.
#
#     python3 python/audit_read.py PATH [--check] [--guide NAME]

import argparse, base64, collections, fcntl, itertools, json, os, re
import shutil, sqlite3, sys
from typing import Any, NamedTuple, cast

# The name `argparse` shows, as `sys.argv` may be empty.
_PROGRAM_NAME = "audit_read.py"

# The folder of the checkout's bytecode.
_PYCACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "build",
    "pycache",
)

# A start heading of the document, which names a process and its start.
_START_PATTERN = re.compile(r"^==== (.*) ====$")

# An entry's heading: its time of day to the millisecond, then its label.
_ENTRY_PATTERN = re.compile(r"^---- (\d\d):(\d\d):(\d\d)\.(\d\d\d), (.*)$")

# The start of the text of a start heading of the engine, not of the console.
_ENGINE_START = "engine started"

# The start of either heading, which no line of a body starts with.
_MARKS = ("====", "----")

# What joins the sender and the receiver in the label of a line entry.
_LANE_MARK = " to "

# The text after a line's JSON in its entry when it carries blobs.
_BLOBS_PATTERN = re.compile(r"\n\[blobs omitted: \d+\]")

# The start of the label of a note of a thread.
_NOTE_PREFIX = "note of "

# The start of the label of a dump of one side's databases.
_DUMP_PREFIX = "databases of the "

# A note of a sleep: the ids of the replies it waits for and its wake.
_SLEEP_PATTERN = re.compile(r"^  sleeps on ([\d, ]+) until (\S+)$")

# A note of the end of the console's program, with its code.
_EXIT_PATTERN = re.compile(r"exited with code (-?\d+)\.$")

# The prefix of the audit's own line types, which no entry records.
_AUDIT_PREFIX = "audit."

# The line types that carry a failure.
_FAILURE_TYPES = ("error", "fault")

# The line types of the provider's port, of an MCP message, of a console read.
_HTTP_TYPE = "http.request"
_MCP_TYPE = "mcp"
_READ_TYPE = "console.read"
_OPEN_TYPE = "console.open"

# The lane of the input the person typed and of the turn's end.
_INPUT_LANE = "dom to ui"
_INPUT_TYPE = "ui.input"

# The lane the browser's commits take to the server.
_COMMIT_LANE = "ai to server"

# The commit that stores a conversation's system prompt.
_PROMPT_TYPE = "turn.prompt"

# The lanes that carry the conversation, which the document writes thin.
_REQUEST_LANE = "ai to http"
_REPLY_LANE = "http to ai"
_CONVERSATION_LANES = (_REQUEST_LANE, _REPLY_LANE, _COMMIT_LANE)

# The end of the url of a model call, the Responses API's.
_RESPONSES_PATH = "/responses"

# The fields of a thin line that count the items the document already showed.
_KEPT_FIELDS = ("input_kept", "content_kept", "messages_kept")

# The field of a model call that chains it to the response before it.
_CHAIN_FIELD = "previous_response_id"

# The item types of the model's output, each of which carries an id.
_OUTPUT_TYPES = ("reasoning", "message", "function_call")

# The item type of a function call, and of the output that answers it.
_CALL_TYPE = "function_call"
_ANSWER_TYPE = "function_call_output"

# The item types of the model's reasoning and message, and a message's part.
_REASONING_TYPE = "reasoning"
_MESSAGE_TYPE = "message"
_TEXT_TYPE = "output_text"

# The roles of a system message and of the player's message.
_SYSTEM_ROLE = "system"
_USER_ROLE = "user"

# The indent of a line's JSON text in the document, by which bytes are counted.
_JSON_INDENT = 2

# What the record shows for a credential.
_MASK = "<masked>"

# The range of the statuses of an HTTP answer that succeeded.
_STATUS_LOW = 200
_STATUS_HIGH = 300

# The milliseconds of an hour, a minute and a second.
_HOUR_MILLISECONDS = 3600000
_MINUTE_MILLISECONDS = 60000
_SECOND_MILLISECONDS = 1000

# The checkout's directory of the guides, each in a directory of its own.
_GUIDES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "guides"
)

# The start of the id of a guide's gold, the guide's name its end.
_GUIDE_GOLD = "python.test_guide_"

# What the program says when its check found nothing, without and with a guide.
_CHECK_PASSED = "check: no unexpected failure"
_GUIDE_PASSED = (
    "check: no unexpected failure, and every message is the guide's"
)

# The kinds of a line: a request holds an id, a reply the id it answers.
_REQUEST_KIND = "request"
_REPLY_KIND = "reply"
_PUSH_KIND = "push"

# The labels of the notes of the two page threads, each note a sleep.
_THREAD_NOTES = ("note of ai", "note of ui")

# The lines a person's turn, a render and a picture take between threads.
_SAY_TYPE = "ai.say"
_RENDER_TYPE = "render"
_MEDIA_TYPE = "media.store"
_RENDER_LANE = "ai to ui"

# The end of the url of an image request.
_IMAGES_PATH = "/images/generations"

# The MCP method of a tool call, and the tool that makes a picture.
_CALL_METHOD = "tools/call"
_IMAGE_TOOL = "image_make"

# The mark that ends the prefix of a tool's name, and each prefix's lane.
_PREFIX_MARK = "_"
_TOOL_LANES = {"browser": "ai to ai", "server": "ai to server"}

# The mark between the members of a scripted reply's quote.
_QUOTE_MARK = "."

# The joint of the text parts of a tool's result in its call's output.
_PART_JOINT = "\n"

# The commits of the browser's store, which tools and scripts send.
_COMMIT_TYPES = (
    "kv.put",
    "kv.delete",
    "doc.put",
    "db.create",
    "db.drop",
    "turn.append",
    "turn.prompt",
    "sql.run",
)

# The lane, type and kind of each line a guide's walk sends.
_GUIDE_LINES = frozenset(
    {
        ("server to ai", "tap.start", _REQUEST_KIND),
        (_COMMIT_LANE, "tap.start", _REPLY_KIND),
        ("ai to ui", "settings.set", _PUSH_KIND),
        ("ai to ai", "engine.start", _PUSH_KIND),
        ("ai to ai", _MCP_TYPE, _REQUEST_KIND),
        ("ai to ai", _MCP_TYPE, _REPLY_KIND),
        ("ai to ai", _MCP_TYPE, _PUSH_KIND),
        (_COMMIT_LANE, _MCP_TYPE, _REQUEST_KIND),
        (_COMMIT_LANE, _MCP_TYPE, _PUSH_KIND),
        ("server to ai", _MCP_TYPE, _REPLY_KIND),
        (_COMMIT_LANE, "db.sync", _REQUEST_KIND),
        ("server to ai", "db.restore", _PUSH_KIND),
        ("server to ai", "db.file", _PUSH_KIND),
        ("server to ai", "db.sync", _REPLY_KIND),
        (_INPUT_LANE, _INPUT_TYPE, _PUSH_KIND),
        ("ui to ai", _SAY_TYPE, _REQUEST_KIND),
        ("ai to ui", _SAY_TYPE, _REPLY_KIND),
        (_REQUEST_LANE, _HTTP_TYPE, _REQUEST_KIND),
        (_REPLY_LANE, _HTTP_TYPE, _REPLY_KIND),
        (_RENDER_LANE, _RENDER_TYPE, _REQUEST_KIND),
        ("ui to ai", _RENDER_TYPE, _REPLY_KIND),
        (_RENDER_LANE, _MEDIA_TYPE, _REQUEST_KIND),
        ("ui to media", _MEDIA_TYPE, _REQUEST_KIND),
        ("media to ui", _MEDIA_TYPE, _REPLY_KIND),
        ("ui to ai", _MEDIA_TYPE, _REPLY_KIND),
        *((_COMMIT_LANE, kind, _PUSH_KIND) for kind in _COMMIT_TYPES),
    }
)

# The indent of a digest record's lines after its first.
_RECORD_INDENT = "        "

# The first line of the digest, which says how to read a record.
_DIGEST_LEGEND = (
    "each record: L and its line in the audit, seconds from the first entry,"
    " its label, then what it says; `same as L913` names the record that"
    " showed a text before"
)

# The longest text the digest shows again rather than name by its line.
_SAME_LENGTH = 80

# The field of a blob header in the server's record that holds its sha256.
_DIGEST_FIELD = "sha256"

# The file of a database in a directory, after its name.
_DB_EXTENSION = ".sqlite"

# The heading of a database in the text of databases, and a row's indent.
_DB_MARK = "==== "
_ROW_INDENT = "  "

# The longest BLOB the text of databases shows in hex, a sha256's.
_HEX_BYTES = 32

# Every object of a database that has SQL, in name order.
_OBJECTS_SQL = (
    "SELECT type, name, sql FROM sqlite_schema WHERE sql IS NOT NULL"
    " ORDER BY name"
)


sys.pycache_prefix = _PYCACHE_PATH


# One entry: its place, start, time, label, body, whole line, items kept.
class ReadEntry(NamedTuple):
    number: int
    start: int
    at: int
    label: str
    body: str
    line: dict[str, Any] | None
    kept: int


# A failure the check found, naming the line of the document that shows it.
class AuditFailed(Exception):
    pass


# The field of a header under its full name or its short one.
def _field_get(header: dict[str, Any], full: str, short: str) -> Any:
    return header[full] if full in header else header.get(short)


# The header of a line entry, or an empty one for a note or a dump.
def _header_of(entry: ReadEntry) -> dict[str, Any]:
    return {} if entry.line is None else entry.line["0"]


# The type of a line entry, or an empty string for a note or a dump.
def type_of(entry: ReadEntry) -> str:
    kind = _field_get(_header_of(entry), "type", "t")
    return "" if kind is None else str(kind)


# The line of a line entry's body, which is its JSON, then its blobs counted.
def _line_decode(body: str, number: int) -> dict[str, Any]:
    try:
        line, end = json.JSONDecoder().raw_decode(body)
    except json.JSONDecodeError as error:
        raise ValueError(f"line {number}: no JSON: {body!r}") from error
    rest = body[end:]
    if rest and _BLOBS_PATTERN.fullmatch(rest) is None:
        raise ValueError(f"line {number}: the JSON is followed by {rest!r}")
    return line


# The count of items a thin line wrote as kept, 0 for any other line.
def _kept_of(label: str, line: dict[str, Any]) -> int:
    fields = line.get("json", {}) if label == _REQUEST_LANE else line
    for field in _KEPT_FIELDS:
        if field in fields:
            return int(fields[field])
    return 0


# The entry of a heading's parts, its body lines read, its line made whole.
def _entry_make(
    number: int,
    start: int,
    at: int,
    label: str,
    lines: list[str],
    shown: Any,
) -> ReadEntry:
    body = "\n".join(lines).rstrip("\n")
    is_line = _LANE_MARK in label and not label.startswith(_DUMP_PREFIX)
    line = _line_decode(body, number) if is_line else None
    kept = 0
    if line is not None:
        kept = _kept_of(label, line)
        kind = _field_get(line["0"], "type", "t")
        line = shown.line_whole(label, "" if kind is None else str(kind), line)
    return ReadEntry(number, start, at, label, body, line, kept)


# The milliseconds of the day of a heading's match.
def _time_read(found: re.Match[str]) -> int:
    hours, minutes, seconds, milliseconds = found.group(1, 2, 3, 4)
    return (
        int(hours) * _HOUR_MILLISECONDS
        + int(minutes) * _MINUTE_MILLISECONDS
        + int(seconds) * _SECOND_MILLISECONDS
        + int(milliseconds)
    )


# The entries of a document's text in order, a line of no form refused.
def entries_parse(text: str) -> list[ReadEntry]:
    import audit

    entries: list[ReadEntry] = []
    shown = audit.ShownLog()
    start = 0
    held: tuple[int, int, str] | None = None
    lines: list[str] = []
    for number, line in enumerate(text.split("\n"), 1):
        found = _ENTRY_PATTERN.match(line)
        started = _START_PATTERN.match(line)
        if not found and not started:
            if line.startswith(_MARKS):
                raise ValueError(f"line {number}: no heading: {line!r}")
            if held is None and line:
                raise ValueError(f"line {number}: outside any entry: {line!r}")
            lines.append(line)
            continue
        if held is not None:
            entries.append(
                _entry_make(held[0], start, held[1], held[2], lines, shown)
            )
        held = None
        lines = []
        if found:
            held = (number, _time_read(found), found.group(5))
        elif cast(re.Match[str], started).group(1).startswith(_ENGINE_START):
            start += 1
    if held is not None:
        entries.append(
            _entry_make(held[0], start, held[1], held[2], lines, shown)
        )
    return entries


# The document's text, read whole under a shared lock of the file.
def document_read(path: str) -> str:
    with open(path, "rb") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_SH)
        try:
            data = file.read()
        finally:
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)
    return data.decode("utf-8")


# The payload of a line entry: its keys that are no header's.
def _payload_of(entry: ReadEntry) -> dict[str, Any]:
    line = {} if entry.line is None else entry.line
    return {key: value for key, value in line.items() if not key.isdigit()}


# A value whole as one line, its newlines escaped, for a failure's message.
def _text_line(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value)
    return text.replace("\n", "\\n")


# The body of a model call, a request of the Responses API, or None.
def _call_body(entry: ReadEntry) -> dict[str, Any] | None:
    payload = _payload_of(entry)
    body = payload.get("json")
    if (
        type_of(entry) != _HTTP_TYPE
        or _field_get(_header_of(entry), "reply", "r") is not None
        or not isinstance(body, dict)
        or "input" not in body
        or not str(payload["url"]).endswith(_RESPONSES_PATH)
    ):
        return None
    return cast(dict[str, Any], body)


# The body of a model reply, an answer that holds an output, or None.
def _reply_body(entry: ReadEntry) -> dict[str, Any] | None:
    body = _payload_of(entry).get("json")
    if (
        type_of(entry) != _HTTP_TYPE
        or _field_get(_header_of(entry), "reply", "r") is None
        or not isinstance(body, dict)
        or "output" not in body
    ):
        return None
    return cast(dict[str, Any], body)


# The model calls of the record in order, each with its body as sent.
def _calls_of(entries: list[ReadEntry]) -> list[tuple[ReadEntry, Any]]:
    return [
        (entry, body)
        for entry in entries
        if (body := _call_body(entry)) is not None
    ]


# The model replies of the record in order, each with its body.
def _replies_of(entries: list[ReadEntry]) -> list[tuple[ReadEntry, Any]]:
    return [
        (entry, body)
        for entry in entries
        if (body := _reply_body(entry)) is not None
    ]


# The function calls of a reply's output, in order.
def _calls_in(output: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in output if item["type"] == _CALL_TYPE]


# The kind of an item: its type, or the role of a message that has none.
def _kind_of(item: dict[str, Any]) -> str:
    return str(item["type"] if "type" in item else item["role"])


# The kinds of a model call's items counted, as one short text.
def _kinds_text(items: list[dict[str, Any]]) -> str:
    kinds = collections.Counter(_kind_of(item) for item in items)
    return " ".join(f"{kind}={kinds[kind]}" for kind in sorted(kinds))


# The texts of a reply's messages joined, as the agent joins them.
def _said_of(output: list[dict[str, Any]]) -> str:
    return "\n".join(
        part["text"]
        for item in output
        if item["type"] == "message"
        for part in item["content"]
    )


# The input tokens of a model reply and those served from cache, as a text.
def _cached_text(body: dict[str, Any]) -> str:
    usage = body["usage"]
    cached = usage["input_tokens_details"]["cached_tokens"]
    return f"cached {cached} of {usage['input_tokens']}"


# The blobs a line carries, as the header counts them, 0 for a note or a dump.
def _blobs_of(entry: ReadEntry) -> int:
    count = _field_get(_header_of(entry), "blobs", "b")
    return 0 if count is None else int(count)


# The mark of a request's id or a reply's, and none for a push.
def _mark_of(entry: ReadEntry) -> str:
    header = _header_of(entry)
    ident = _field_get(header, "id", "i")
    reply = _field_get(header, "reply", "r")
    if ident is not None:
        return f"i={ident}"
    return "" if reply is None else f"r={reply}"


# Each tool the agent called, counted, in the order of first call.
def _tools_called(entries: list[ReadEntry]) -> dict[str, int]:
    called: dict[str, int] = {}
    for _, body in _replies_of(entries):
        for call in _calls_in(body["output"]):
            name = str(call["name"])
            called[name] = called.get(name, 0) + 1
    return called


# The text of the first model call's first item, its system prompt, or None.
def _prompt_of(entries: list[ReadEntry]) -> Any:
    calls = _calls_of(entries)
    if not calls:
        return None
    return calls[0][1]["input"][0]["content"]


# How many items of a model call hold the system prompt as their content.
def _copies_in(items: list[dict[str, Any]], prompt: Any) -> int:
    return sum(item.get("content") == prompt for item in items)


# The copies of the first model call's system prompt in each model call.
def _prompt_copies(entries: list[ReadEntry]) -> list[int]:
    prompt = _prompt_of(entries)
    calls = _calls_of(entries)
    return [_copies_in(body["input"], prompt) for _, body in calls]


# The copies of the first model call's system prompt the lanes wrote.
def prompt_recorded(entries: list[ReadEntry]) -> int:
    prompt = _prompt_of(entries)
    if prompt is None:
        return 0
    text = json.dumps(prompt, ensure_ascii=False)
    return sum(
        entry.body.count(text)
        for entry in entries
        if entry.label in _CONVERSATION_LANES
    )


# The input tokens of the model calls, those served from cache and the share.
def _usage_text(entries: list[ReadEntry]) -> str:
    total = 0
    cached = 0
    for _, body in _replies_of(entries):
        total += body["usage"]["input_tokens"]
        cached += body["usage"]["input_tokens_details"]["cached_tokens"]
    share = f", {cached / total:.1%}" if total else ""
    return f"{cached} of {total} served from cache{share}"


# The line an entry's body wrote, and the end of its JSON text in the body.
def _written_of(entry: ReadEntry) -> tuple[Any, int]:
    return json.JSONDecoder().raw_decode(entry.body)


# The commits the browser sent the server, counted by type.
def _commits_counted(entries: list[ReadEntry]) -> dict[str, int]:
    commits: dict[str, int] = {}
    for entry in entries:
        kind = type_of(entry)
        if entry.label == _COMMIT_LANE and kind in _COMMIT_TYPES:
            commits[kind] = commits.get(kind, 0) + 1
    return commits


# Each name and its count, or none when there is no name.
def _counts_text(counts: dict[str, int]) -> str:
    told = ", ".join(f"{name} {count}" for name, count in counts.items())
    return told or "none"


# The summary of what the run did, each line one measurement of the record.
def _summary_lines(entries: list[ReadEntry]) -> list[str]:
    calls = _calls_of(entries)
    started = sum(_CHAIN_FIELD not in body for _, body in calls)
    span = entries[-1].at - entries[0].at if entries else 0
    starts = entries[-1].start if entries else 0
    return [
        f"entries: {len(entries)} in {span / _SECOND_MILLISECONDS:.3f} s,"
        f" engine starts: {starts}",
        f"model calls: {len(calls)}, chains started: {started}, copies of the"
        f" system prompt sent: {sum(_prompt_copies(entries))}, input tokens:"
        f" {_usage_text(entries)}",
        f"tools called: {_counts_text(_tools_called(entries))}",
        f"commits: {_counts_text(_commits_counted(entries))}",
    ]


# The kind of a line entry: a request, a reply or a push.
def _line_kind(entry: ReadEntry) -> str:
    header = _header_of(entry)
    if _field_get(header, "id", "i") is not None:
        return _REQUEST_KIND
    if _field_get(header, "reply", "r") is not None:
        return _REPLY_KIND
    return _PUSH_KIND


# A line entry's type, then the mark of its id or reply when it has one.
def _name_of(entry: ReadEntry) -> str:
    mark = _mark_of(entry)
    return f"{type_of(entry)} {mark}" if mark else type_of(entry)


# The first blob a line carries: its size, and its sha256 when the server's.
def _blob_told(entry: ReadEntry) -> str:
    blob: dict[str, Any] = cast(dict[str, Any], entry.line)["1"]
    size = int(_field_get(blob, "size", "s"))
    if _DIGEST_FIELD in blob:
        return f"{size} bytes, sha256 {blob[_DIGEST_FIELD]}"
    return f"{size} bytes"


# A count and its noun, the noun plural unless the count is one.
def _count_text(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


# A text under a label, each line of the text after the first indented more.
def _text_block(label: str, text: str) -> list[str]:
    first, *rest = text.split("\n")
    return [
        f"{_RECORD_INDENT}{label}{first}",
        *(f"{_RECORD_INDENT}  {part}" if part else "" for part in rest),
    ]


# The one line that tells a line of a type the digest tells in one, or None.
def _line_told(entry: ReadEntry, payload: dict[str, Any]) -> str | None:
    kind = type_of(entry)
    name = _name_of(entry)
    if kind in ("tap.start", "settings.set") and "switches" in payload:
        switches = json.dumps(payload["switches"])
        return f"{name}, the settings and the switches {switches}"
    if kind == "kv.put":
        key = _field_get(_header_of(entry), "key", "k")
        return f"{name} {key}, {_blob_told(entry)}"
    if kind == "kv.delete":
        return f"{name} {_field_get(_header_of(entry), 'key', 'k')}"
    if kind in ("db.create", "db.drop"):
        return f"{name} {payload['db']}"
    if kind == "db.restore":
        files = _count_text(payload.get("files", 0), "file")
        return f"{name} {payload['db']}, {_blob_told(entry)}, {files}"
    if kind == "db.file":
        return f"{name} {payload['db']}, {_blob_told(entry)}"
    if kind == "db.sync" and "databases" in payload:
        return f"{name}: databases {', '.join(payload['databases'])}"
    if kind == "turn.append":
        return (
            f"{name} to {payload['scene']}, role {payload['role']},"
            f" {_count_text(len(payload['content']), 'item')}"
        )
    if kind == _MEDIA_TYPE and _blobs_of(entry):
        return f"{name} {payload['k']}, {_blob_told(entry)}"
    if kind == _MEDIA_TYPE and _DIGEST_FIELD in payload:
        return (
            f"{name} {payload['k']}, {payload['size']} bytes, sha256"
            f" {payload[_DIGEST_FIELD]}"
        )
    if not payload:
        return name
    return None


# The digest's reading of the record: its times, texts shown, calls and runs.
class _DigestBook:
    # Starts before the record's first entry, at that entry's time.
    def __init__(self, first: int) -> None:
        self.first = first
        self.start = 0
        self.turn = 0
        # The line that showed each text whole, by the text.
        self.shown: dict[str, int] = {}
        # Each MCP request's method, by its start, sender, receiver and id.
        self.methods: dict[tuple[int, str, str, object], str] = {}
        # The calls of the model's last reply that no tool call ran yet.
        self.due: list[dict[str, Any]] = []
        # The call each tool call ran, by its start, sender, receiver and id.
        self.ran: dict[tuple[int, str, str, object], str] = {}

    # The first line of an entry's record: its line, seconds, label and text.
    def head_make(self, entry: ReadEntry, text: str) -> str:
        seconds = (entry.at - self.first) / _SECOND_MILLISECONDS
        return f"L{entry.number} {seconds:.3f} {entry.label} {text}"

    # A text under a label, named by the line that showed it when it is long.
    def text_lines(
        self, label: str, text: str, number: int, always: bool = False
    ) -> list[str]:
        if text in self.shown and (always or len(text) > _SAME_LENGTH):
            return [f"{_RECORD_INDENT}{label}same as L{self.shown[text]}"]
        self.shown.setdefault(text, number)
        return _text_block(label, text)

    # A value with each long string in it shown before named by its line.
    def strings_named(self, value: Any, number: int) -> Any:
        if isinstance(value, str):
            if value in self.shown and len(value) > _SAME_LENGTH:
                return f"same as L{self.shown[value]}"
            self.shown.setdefault(value, number)
            return value
        if isinstance(value, list):
            items = cast(list[Any], value)
            return [self.strings_named(item, number) for item in items]
        if isinstance(value, dict):
            fields = cast(dict[str, Any], value).items()
            return {k: self.strings_named(v, number) for k, v in fields}
        return value

    # A value as one line of JSON, each long string shown before named.
    def json_named(self, value: Any, number: int) -> str:
        named = self.strings_named(value, number)
        return json.dumps(named, ensure_ascii=False)

    # A function call: its name, its id, then its arguments as JSON.
    def call_text(self, call: dict[str, Any], number: int) -> str:
        arguments = self.json_named(json.loads(call["arguments"]), number)
        return f"{call['name']} {call['call_id']} {arguments}"

    # The lines of an input item of a model call or of a commit of turns.
    def item_lines(self, item: dict[str, Any], number: int) -> list[str]:
        kind = _kind_of(item)
        if kind == _ANSWER_TYPE:
            label = f"output {item['call_id']}: "
            return self.text_lines(label, str(item["output"]), number)
        if kind == _CALL_TYPE:
            return [f"{_RECORD_INDENT}call {self.call_text(item, number)}"]
        if kind == _REASONING_TYPE:
            return [f"{_RECORD_INDENT}reasoning {item['id']}"]
        if kind == _MESSAGE_TYPE:
            return self.text_lines("assistant: ", _said_of([item]), number)
        content = str(item["content"])
        always = kind == _SYSTEM_ROLE
        return self.text_lines(f"{kind}: ", content, number, always)

    # A model call: its chain, then each item it sent, as the model reads it.
    def call_record(self, entry: ReadEntry, body: dict[str, Any]) -> list[str]:
        items: list[dict[str, Any]] = body["input"]
        chained = "a chain start"
        if _CHAIN_FIELD in body:
            chained = f"chained to {body[_CHAIN_FIELD]}"
        counted = _count_text(len(items), "item")
        head = f"model call {_mark_of(entry)}, {chained}, {counted}"
        lines = [self.head_make(entry, head)]
        for item in items:
            lines += self.item_lines(item, entry.number)
        return lines

    # A model reply: its id and cache, then what it says and the calls made.
    def reply_record(
        self, entry: ReadEntry, body: dict[str, Any]
    ) -> list[str]:
        output: list[dict[str, Any]] = body["output"]
        cached = _cached_text(body)
        head = f"model reply {_mark_of(entry)}, {body['id']}, {cached} tokens"
        lines = [self.head_make(entry, head)]
        if any(item["type"] == _MESSAGE_TYPE for item in output):
            lines += self.text_lines("says: ", _said_of(output), entry.number)
        self.due = _calls_in(output)
        for call in self.due:
            told = self.call_text(call, entry.number)
            lines.append(f"{_RECORD_INDENT}call {told}")
        return lines

    # The id of the due call a tool call runs, by its name and arguments.
    def call_take(self, name: str, arguments: Any) -> str | None:
        for index, call in enumerate(self.due):
            if str(call["name"]).partition(_PREFIX_MARK)[2] == name and (
                json.loads(call["arguments"]) == arguments
            ):
                del self.due[index]
                return str(call["call_id"])
        return None

    # A tool call: the model's call it runs, else its arguments.
    def tool_record(
        self, entry: ReadEntry, key: tuple[int, str, str, object]
    ) -> list[str]:
        params = _payload_of(entry)["params"]
        head = f"tool call {_mark_of(entry)} {params['name']}"
        ran = self.call_take(str(params["name"]), params["arguments"])
        if ran is None:
            arguments = self.json_named(params["arguments"], entry.number)
            return [self.head_make(entry, head), _RECORD_INDENT + arguments]
        self.ran[key] = ran
        return [self.head_make(entry, f"{head} for {ran}")]

    # A tool's result: the call it answers, then its text.
    def result_record(
        self, entry: ReadEntry, key: tuple[int, str, str, object]
    ) -> list[str]:
        result: dict[str, Any] = _payload_of(entry)["result"]
        texts = _PART_JOINT.join(part["text"] for part in result["content"])
        ran = self.ran.pop(key, None)
        told = "" if ran is None else f" of {ran}"
        failed = " failed" if result.get("isError") is True else ""
        told = f"tool result {_mark_of(entry)}{told}{failed}"
        return [
            self.head_make(entry, told),
            *self.text_lines("", texts, entry.number),
        ]

    # An MCP message: a tool's call and result whole, the rest in one line.
    def mcp_record(
        self, entry: ReadEntry, payload: dict[str, Any]
    ) -> list[str]:
        sender, receiver = entry.label.split(_LANE_MARK)
        header = _header_of(entry)
        ident = _field_get(header, "id", "i")
        reply = _field_get(header, "reply", "r")
        mark = _mark_of(entry)
        if reply is None:
            method = str(payload["method"])
            key = (entry.start, sender, receiver, ident)
            if ident is not None:
                self.methods[key] = method
            if method == _CALL_METHOD:
                return self.tool_record(entry, key)
            told = " ".join(part for part in ("mcp", mark, method) if part)
            return [self.head_make(entry, told)]
        key = (entry.start, receiver, sender, reply)
        method = self.methods[key]
        if "error" in payload:
            error = self.json_named(payload["error"], entry.number)
            head = f"mcp {mark} {method} failed: {error}"
            return [self.head_make(entry, head)]
        result: dict[str, Any] = payload["result"]
        if method == _CALL_METHOD:
            return self.result_record(entry, key)
        if "tools" in result:
            names = [str(tool["name"]) for tool in result["tools"]]
            listed = f"{len(names)} tools: {', '.join(names)}"
            return [self.head_make(entry, f"mcp {mark} {method}, {listed}")]
        told = f"mcp {mark} {method}: {self.json_named(result, entry.number)}"
        return [self.head_make(entry, told)]

    # A line of the provider's port: a model call or reply, a picture's, else.
    def http_record(
        self, entry: ReadEntry, payload: dict[str, Any]
    ) -> list[str]:
        call = _call_body(entry)
        if call is not None:
            return self.call_record(entry, call)
        reply = _reply_body(entry)
        if reply is not None:
            return self.reply_record(entry, reply)
        mark = _mark_of(entry)
        if "url" in payload and str(payload["url"]).endswith(_IMAGES_PATH):
            head = self.head_make(entry, f"image request {mark}")
            prompt = str(payload["json"]["prompt"])
            return [head, *self.text_lines("prompt: ", prompt, entry.number)]
        body = payload.get("json")
        if isinstance(body, dict) and "data" in body:
            images: list[dict[str, Any]] = cast(dict[str, Any], body)["data"]
            sizes = [
                len(base64.b64decode(image["b64_json"])) for image in images
            ]
            told = f"image answer {mark}, status {payload['status']}, sizes"
            return [self.head_make(entry, f"{told} {sizes} bytes")]
        return self.other_record(entry, payload)

    # A sql.run commit: its database, then each statement whole with params.
    def sql_record(
        self, entry: ReadEntry, payload: dict[str, Any]
    ) -> list[str]:
        lines = [
            self.head_make(entry, f"{_name_of(entry)} on {payload['db']}")
        ]
        for statement in payload["statements"]:
            text = str(statement["sql"])
            params = statement.get("params", [])
            if params:
                text += (
                    f"  with params {json.dumps(params, ensure_ascii=False)}"
                )
            lines += _text_block("", text)
        return lines

    # A line no other record tells: its type and mark, then its payload.
    def other_record(
        self, entry: ReadEntry, payload: dict[str, Any]
    ) -> list[str]:
        blobs = _blobs_of(entry)
        told = f", {_count_text(blobs, 'blob')}" if blobs else ""
        head = self.head_make(entry, f"{_name_of(entry)}{told}")
        if type_of(entry) in _FAILURE_TYPES:
            text = json.dumps(payload, ensure_ascii=False, indent=_JSON_INDENT)
            return [
                head,
                *(_RECORD_INDENT + part for part in text.split("\n")),
            ]
        return [head, _RECORD_INDENT + self.json_named(payload, entry.number)]

    # A note in its words, its first line in the head, or a dump whole.
    def note_lines(self, entry: ReadEntry) -> list[str]:
        if entry.label.startswith(_DUMP_PREFIX):
            head = self.head_make(entry, f"{len(entry.body)} bytes")
            return [head, *self.text_lines("", entry.body, entry.number)]
        first, *rest = entry.body.strip().split("\n")
        return [
            self.head_make(entry, first),
            *(_RECORD_INDENT + part for part in rest),
        ]

    # The lines of an entry's record.
    def record_lines(self, entry: ReadEntry) -> list[str]:
        if entry.line is None:
            return self.note_lines(entry)
        kind = type_of(entry)
        name = _name_of(entry)
        payload = _payload_of(entry)
        number = entry.number
        if kind == _INPUT_TYPE:
            self.turn += 1
            player = self.head_make(entry, f"player: {payload['text']}")
            return ["", f"---- turn {self.turn}", player]
        if kind == _SAY_TYPE and "text" in payload:
            return [self.head_make(entry, f"{name}: {payload['text']}")]
        if kind == _SAY_TYPE:
            head = (
                f"{name}, reply stored at row {payload['turn']}, showing"
                f" {payload['scene']}"
            )
            band = str(payload["subtitle"])
            return [
                self.head_make(entry, head),
                *self.text_lines("band: ", band, number),
            ]
        if kind == _RENDER_TYPE and "scene" in payload:
            image = payload.get("image", "none")
            head = f"{name} to {payload['scene']}, image {image}"
            subtitle = str(payload["subtitle"])
            return [
                self.head_make(entry, head),
                *self.text_lines("subtitle: ", subtitle, number),
            ]
        if kind == _PROMPT_TYPE:
            messages: list[dict[str, Any]] = payload["messages"]
            counted = _count_text(len(messages), "message")
            head = f"{name} to {payload['scene']}, {counted}"
            lines = [self.head_make(entry, head)]
            for message in messages:
                lines += self.item_lines(message, number)
            return lines
        if kind == "doc.put":
            head = f"{name} {payload['db']} {payload['id']}"
            body = self.json_named(payload["body"], number)
            return [self.head_make(entry, head), _RECORD_INDENT + body]
        if kind == "sql.run":
            return self.sql_record(entry, payload)
        if kind == _MCP_TYPE:
            return self.mcp_record(entry, payload)
        if kind == _HTTP_TYPE:
            return self.http_record(entry, payload)
        told = _line_told(entry, payload)
        if told is not None:
            return [self.head_make(entry, told)]
        return self.other_record(entry, payload)


# The audit digest: every entry told, a text shown before named, a summary.
def digest_lines(entries: list[ReadEntry]) -> list[str]:
    book = _DigestBook(entries[0].at if entries else 0)
    lines = [_DIGEST_LEGEND]
    for entry in entries:
        if entry.start != book.start:
            book.start = entry.start
            lines += ["", f"==== engine start {entry.start}", "---- bring up"]
        lines += book.record_lines(entry)
    return [*lines, "", *_summary_lines(entries)]


# The requests of the record with no reply, by start, sender, receiver and id.
def requests_open(entries: list[ReadEntry]) -> list[str]:
    asked: collections.Counter[tuple[int, str, str, object]] = (
        collections.Counter()
    )
    answered: collections.Counter[tuple[int, str, str, object]] = (
        collections.Counter()
    )
    numbers: dict[tuple[int, str, str, object], int] = {}
    for entry in entries:
        if entry.line is None:
            continue
        sender, receiver = entry.label.split(_LANE_MARK)
        header = _header_of(entry)
        ident = _field_get(header, "id", "i")
        reply = _field_get(header, "reply", "r")
        if ident is not None:
            key = (entry.start, sender, receiver, ident)
            asked[key] += 1
            numbers[key] = entry.number
        if reply is not None:
            answered[(entry.start, receiver, sender, reply)] += 1
    return [
        f"line {numbers[key]}: {key[1]} to {key[2]} asked {key[3]}"
        f" in start {key[0]} and has no reply"
        for key in (asked - answered)
    ]


# The first reply of the record with no request, or None.
def _reply_stray(entries: list[ReadEntry]) -> str | None:
    asked: set[tuple[int, str, str, object]] = set()
    for entry in entries:
        ident = _field_get(_header_of(entry), "id", "i")
        if ident is not None:
            sender, receiver = entry.label.split(_LANE_MARK)
            asked.add((entry.start, sender, receiver, ident))
    for entry in entries:
        reply = _field_get(_header_of(entry), "reply", "r")
        if reply is not None:
            sender, receiver = entry.label.split(_LANE_MARK)
            if (entry.start, receiver, sender, reply) not in asked:
                return (
                    f"line {entry.number}: {entry.label} answers {reply},"
                    " which was never asked"
                )
    return None


# The first sleep of the record on a reply that never came, or None.
def _sleep_stray(entries: list[ReadEntry]) -> str | None:
    answered: set[tuple[int, str, int]] = set()
    for entry in entries:
        reply = _field_get(_header_of(entry), "reply", "r")
        if reply is not None:
            receiver = entry.label.split(_LANE_MARK)[1]
            answered.add((entry.start, receiver, reply))
    for entry in entries:
        if entry.label.startswith(_NOTE_PREFIX):
            thread = entry.label.removeprefix(_NOTE_PREFIX)
            found = _SLEEP_PATTERN.match(entry.body)
            if found is not None:
                for word in found.group(1).split(", "):
                    if (entry.start, thread, int(word)) not in answered:
                        return (
                            f"line {entry.number}: {thread} sleeps on {word}"
                            " and that reply never came"
                        )
    return None


# What is wrong with a request or answer of the provider's port, or None.
def _http_failure(entry: ReadEntry) -> str | None:
    payload = _payload_of(entry)
    status = payload.get("status")
    if status is not None and not _STATUS_LOW <= status < _STATUS_HIGH:
        return f"the provider's port answered with the status {status}"
    headers = payload.get("headers", {})
    credential = headers.get("Authorization", _MASK)
    if credential != _MASK:
        return "a request's Authorization header is not masked"
    return None


# What is wrong with an MCP message, or None.
def _mcp_failure(entry: ReadEntry) -> str | None:
    payload = _payload_of(entry)
    if "error" in payload:
        return f"an MCP request failed: {_text_line(payload['error'])}"
    result = payload.get("result", {})
    if result.get("isError") is True:
        return f"a tool failed: {_text_line(result.get('content'))}"
    return None


# What is wrong with a line entry alone, or None.
def _line_failure(entry: ReadEntry) -> str | None:
    kind = type_of(entry)
    payload = _payload_of(entry)
    if kind in _FAILURE_TYPES:
        return f"a line of type {kind}: {_text_line(payload)}"
    if kind.startswith(_AUDIT_PREFIX):
        return f"the audit recorded its own line of type {kind}"
    if kind == _HTTP_TYPE:
        return _http_failure(entry)
    if kind == _MCP_TYPE:
        return _mcp_failure(entry)
    if kind == _READ_TYPE and payload.get("timed_out") is True:
        return "a read of the console timed out"
    if kind == _OPEN_TYPE and payload.get("token", _MASK) != _MASK:
        return "the token of a console.open reply is not masked"
    return None


# What is wrong with a note alone, or None.
def _note_failure(entry: ReadEntry) -> str | None:
    found = _EXIT_PATTERN.search(entry.body)
    if found is not None and int(found.group(1)) != 0:
        return f"a program ended badly: {_text_line(entry.body)}"
    return None


# The first conversation whose system prompt was stored again, or None.
def _prompt_stray(entries: list[ReadEntry]) -> str | None:
    scenes: set[str] = set()
    for entry in entries:
        if entry.label == _COMMIT_LANE and type_of(entry) == _PROMPT_TYPE:
            scene = str(_payload_of(entry).get("scene"))
            if scene in scenes:
                return f"line {entry.number}: a second prompt of {scene}"
            scenes.add(scene)
    return None


# What a chained call sends beside the new items, or None when it sends them.
def _chained_failure(body: dict[str, Any], output: Any) -> str | None:
    items: list[dict[str, Any]] = body["input"]
    if output is None:
        return (
            f"a chained call names {body[_CHAIN_FIELD]}, which no reply of its"
            " start holds"
        )
    if any(item.get("role") == _SYSTEM_ROLE for item in items):
        return "a chained call sends a system message"
    calls = [call["call_id"] for call in _calls_in(output)]
    if calls:
        answers = [
            item.get("call_id")
            for item in items
            if item.get("type") == _ANSWER_TYPE
        ]
        new = answers == calls and len(answers) == len(items)
    else:
        new = len(items) == 1 and items[0].get("role") == _USER_ROLE
    if new:
        return None
    return (
        "a chained call sends other than the new items alone:"
        f" {_kinds_text(items)}"
    )


# The first chained call that sends more than the new items, or None.
def _chain_stray(entries: list[ReadEntry]) -> str | None:
    outputs: dict[tuple[int, object], Any] = {}
    for entry in entries:
        reply = _reply_body(entry)
        if reply is not None:
            outputs[(entry.start, reply["id"])] = reply["output"]
        body = _call_body(entry)
        if body is not None and _CHAIN_FIELD in body:
            output = outputs.get((entry.start, body[_CHAIN_FIELD]))
            failure = _chained_failure(body, output)
            if failure is not None:
                return f"line {entry.number}: {failure}"
    return None


# The first chain start not holding the prompt once as its first item, or None.
def _start_stray(entries: list[ReadEntry]) -> str | None:
    prompt = _prompt_of(entries)
    for entry, body in _calls_of(entries):
        items = body["input"]
        copies = _copies_in(items, prompt)
        if _CHAIN_FIELD not in body and (
            copies != 1 or items[0].get("content") != prompt
        ):
            return (
                f"line {entry.number}: a chain's first call holds the system"
                f" prompt {copies} times, not once as its first item"
            )
    return None


# The ids of the model's output items anywhere in a value, in order.
def _ids_in(value: Any) -> list[str]:
    if isinstance(value, list):
        held = cast(list[Any], value)
        return [ident for item in held for ident in _ids_in(item)]
    if not isinstance(value, dict):
        return []
    fields = cast(dict[str, Any], value)
    found: list[str] = []
    if fields.get("type") in _OUTPUT_TYPES and "id" in fields:
        found.append(str(fields["id"]))
    for item in fields.values():
        found += _ids_in(item)
    return found


# The first output item a second body of the lanes wrote again, or None.
def _item_repeated(entries: list[ReadEntry]) -> str | None:
    first: dict[str, int] = {}
    for entry in entries:
        if entry.label in _CONVERSATION_LANES:
            for ident in dict.fromkeys(_ids_in(_written_of(entry)[0])):
                if ident in first:
                    return (
                        f"line {entry.number}: the item {ident} is written"
                        f" again, first at line {first[ident]}"
                    )
                first[ident] = entry.number
    return None


# Raises at the first unexpected failure of the record, naming its line.
def failure_check(entries: list[ReadEntry]) -> None:
    for entry in entries:
        check = _note_failure if entry.line is None else _line_failure
        failure = check(entry)
        if failure is not None:
            raise AuditFailed(f"line {entry.number}: {failure}")
    stray = _reply_stray(entries)
    if stray is not None:
        raise AuditFailed(stray)
    opened = requests_open(entries)
    if opened:
        raise AuditFailed(opened[0])
    for find in (_sleep_stray, _prompt_stray, _chain_stray, _start_stray):
        stray = find(entries)
        if stray is not None:
            raise AuditFailed(stray)
    written = prompt_recorded(entries)
    if written > 1:
        raise AuditFailed(
            f"the conversation's lanes hold the system prompt {written} times"
        )
    stray = _item_repeated(entries)
    if stray is not None:
        raise AuditFailed(stray)


# What is wrong with an entry a guide's walk does not make, or None.
def _guide_stray(entry: ReadEntry) -> str | None:
    if entry.line is not None:
        lane, kind, shape = entry.label, type_of(entry), _line_kind(entry)
        if (lane, kind, shape) in _GUIDE_LINES:
            return None
        return f"a guide sends no {shape} of type {kind} on the lane {lane}"
    if entry.label.startswith(_DUMP_PREFIX):
        return None
    if entry.label in _THREAD_NOTES and _SLEEP_PATTERN.match(entry.body):
        return None
    return f"a guide makes no {entry.label}: {_text_line(entry.body.strip())}"


# The first input, band or first render the gold's walk does not expect.
def _walk_stray(entries: list[ReadEntry], gold: dict[str, Any]) -> str | None:
    steps = [step for rung in gold["rungs"] for step in rung["steps"]]
    served: str = gold["served"]["band"]
    rendered = False
    said: str | None = None
    inputs = 0
    bands = 0
    for entry in entries:
        if entry.line is None:
            continue
        kind = type_of(entry)
        shape = _line_kind(entry)
        payload = _payload_of(entry)
        place = f"line {entry.number}"
        if kind == _RENDER_TYPE and shape == _REQUEST_KIND and not rendered:
            rendered = True
            if payload["subtitle"] != served:
                return (
                    f"{place}: the first render shows {payload['subtitle']!r},"
                    f" not the served band {served!r}"
                )
        elif kind == _INPUT_TYPE:
            if inputs == len(steps):
                return f"{place}: an input after the walk's last step"
            said = str(steps[inputs]["say"])
            inputs += 1
            if payload["text"] != said:
                return (
                    f"{place}: the input {payload['text']!r} is not the"
                    f" step's {said!r}"
                )
        elif kind == _SAY_TYPE and shape == _REQUEST_KIND:
            if payload["text"] != said:
                return (
                    f"{place}: the turn asked {payload['text']!r}, not the"
                    f" input {said!r}"
                )
        elif kind == _SAY_TYPE:
            if bands == len(steps):
                return f"{place}: a band after the walk's last step"
            band = str(steps[bands]["band"])
            bands += 1
            if payload["subtitle"] != band:
                return (
                    f"{place}: the turn ended showing"
                    f" {payload['subtitle']!r}, not the step's band {band!r}"
                )
    if not rendered or inputs != len(steps) or bands != len(steps):
        return (
            f"the record holds {int(rendered)} first render, {inputs} inputs"
            f" and {bands} bands of the walk's {len(steps)} steps"
        )
    return None


# A user message's text in the scripted port's normal form, on ASCII alone.
def _text_normal(text: str) -> str:
    return text.strip().lower()


# The call outputs that end a model call's items, in order.
def _outputs_ending(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = len(items)
    while start > 0 and items[start - 1].get("type") == _ANSWER_TYPE:
        start -= 1
    return items[start:]


# The reply of the node the tools' results reach, by the text each holds.
def _after_reply(node: dict[str, Any], texts: list[str]) -> dict[str, Any]:
    holds = node.get("after_holds")
    if holds is not None and not all(holds in text for text in texts):
        return cast(dict[str, Any], node["after_lacks"])
    return cast(dict[str, Any], node["after_tools"])


# What a reply says: the string its quote names in the last result, content.
def _reply_said(reply: dict[str, Any], texts: list[str]) -> str | None:
    content: str | None = reply["content"]
    if "quote" not in reply:
        return content
    value: Any = json.loads(texts[-1])
    for member in str(reply["quote"]).split(_QUOTE_MARK):
        value = value[member]
    quoted = cast(str, value)
    return quoted if content is None else f"{quoted} {content}"


# A model reply's output items as the guide check compares them.
def _output_shapes(output: list[dict[str, Any]]) -> list[list[Any]]:
    shapes: list[list[Any]] = []
    for item in output:
        if item["type"] == _MESSAGE_TYPE:
            parts = [[part["type"], part["text"]] for part in item["content"]]
            shapes.append([_MESSAGE_TYPE, parts])
        elif item["type"] == _CALL_TYPE:
            fields = [item["call_id"], item["name"], item["arguments"]]
            shapes.append([_CALL_TYPE, *fields])
        else:
            shapes.append([item["type"]])
    return shapes


# The output items a scripted reply makes, as the guide check compares them.
def _reply_shapes(said: str | None, calls: list[Any]) -> list[list[Any]]:
    shapes: list[list[Any]] = [[_REASONING_TYPE]]
    if said is not None:
        shapes.append([_MESSAGE_TYPE, [[_TEXT_TYPE, said]]])
    for call in calls:
        fields = [call["call_id"], call["name"], call["arguments"]]
        shapes.append([_CALL_TYPE, *fields])
    return shapes


# Raises at the first model reply not the table's, moved as the port moves.
def _script_check(entries: list[ReadEntry], table: dict[str, Any]) -> None:
    nodes: dict[str, Any] = table["nodes"]
    current = str(table["start"])
    pending: tuple[str, list[str]] | None = None
    asked: dict[tuple[int, object], list[dict[str, Any]]] = {}
    for entry in entries:
        header = _header_of(entry)
        body = _call_body(entry)
        if body is not None:
            asked[(entry.start, _field_get(header, "id", "i"))] = body["input"]
        reply = _reply_body(entry)
        if reply is None:
            continue
        items = asked[(entry.start, _field_get(header, "reply", "r"))]
        place = f"line {entry.number}"
        if items[-1].get("type") == _ANSWER_TYPE:
            name = cast(tuple[str, list[str]], pending)[0]
            texts = [str(item["output"]) for item in _outputs_ending(items)]
            due = _after_reply(nodes[name], texts)
            said = _reply_said(due, texts)
        else:
            name = current
            node: dict[str, Any] = nodes[name]
            text = _text_normal(str(items[-1]["content"]))
            if text not in node["replies"] and "otherwise" not in node:
                raise AuditFailed(
                    f"{place}: the table's node {name} holds no reply to"
                    f" {text!r}"
                )
            due = node["replies"].get(text, node.get("otherwise"))
            said = cast(str | None, due["content"])
        calls: list[Any] = due.get("tool_calls", [])
        made = _output_shapes(reply["output"])
        shapes = _reply_shapes(said, calls)
        for index, pair in enumerate(itertools.zip_longest(made, shapes)):
            if pair[0] != pair[1]:
                raise AuditFailed(
                    f"{place}: item {index} of the model's reply at the"
                    f" table's node {name} is {json.dumps(pair[0])}, not"
                    f" {json.dumps(pair[1])}"
                )
        current = name
        pending = None
        if calls:
            pending = (str(due["next"]), [call["call_id"] for call in calls])
        else:
            current = str(due["next"])


# Raises at the first tool call, output or image the last reply did not ask.
def _tools_check(entries: list[ReadEntry]) -> None:
    due: list[dict[str, Any]] = []
    made: dict[tuple[int, str, str, object], str] = {}
    results: dict[str, str] = {}
    prompts: list[str] = []
    for entry in entries:
        place = f"line {entry.number}"
        payload = _payload_of(entry)
        reply = _reply_body(entry)
        body = _call_body(entry)
        if reply is not None:
            due = _calls_in(reply["output"])
        elif body is not None:
            if due:
                names = [call["name"] for call in due]
                raise AuditFailed(f"{place}: a model call before {names} ran")
            for output in _outputs_ending(body["input"]):
                if output["output"] != results[output["call_id"]]:
                    raise AuditFailed(
                        f"{place}: the output of {output['call_id']} is not"
                        " its tool's result"
                    )
        elif type_of(entry) == _MCP_TYPE:
            sender, receiver = entry.label.split(_LANE_MARK)
            header = _header_of(entry)
            reply_id = _field_get(header, "reply", "r")
            if payload.get("method") == _CALL_METHOD:
                if not due:
                    raise AuditFailed(f"{place}: a tool call no reply asked")
                call = due.pop(0)
                prefix, _, name = str(call["name"]).partition(_PREFIX_MARK)
                params = payload["params"]
                if (
                    _TOOL_LANES[prefix] != entry.label
                    or params["name"] != name
                    or params["arguments"] != json.loads(call["arguments"])
                ):
                    raise AuditFailed(
                        f"{place}: the tool call {params['name']} on"
                        f" {entry.label} is not {call['name']}"
                        f" {call['call_id']} {call['arguments']}"
                    )
                ident = _field_get(header, "id", "i")
                made[(entry.start, sender, receiver, ident)] = call["call_id"]
                if name == _IMAGE_TOOL:
                    prompts.append(str(params["arguments"]["prompt"]))
            elif (entry.start, receiver, sender, reply_id) in made:
                call_id = made.pop((entry.start, receiver, sender, reply_id))
                parts = payload["result"]["content"]
                results[call_id] = _PART_JOINT.join(
                    part["text"] for part in parts
                )
        elif (
            type_of(entry) == _HTTP_TYPE
            and _line_kind(entry) == _REQUEST_KIND
            and str(payload["url"]).endswith(_IMAGES_PATH)
        ):
            if not prompts or payload["json"]["prompt"] != prompts[0]:
                raise AuditFailed(
                    f"{place}: an image request no image_make call asked"
                )
            prompts.pop(0)
    if due:
        names = [call["name"] for call in due]
        raise AuditFailed(f"the calls {names} of the last reply never ran")


# Raises at the first message a guide's walk does not expect, naming its line.
def guide_check(
    entries: list[ReadEntry], table: dict[str, Any], gold: dict[str, Any]
) -> None:
    for entry in entries:
        failure = _guide_stray(entry)
        if failure is not None:
            raise AuditFailed(f"line {entry.number}: {failure}")
    stray = _walk_stray(entries, gold)
    if stray is not None:
        raise AuditFailed(stray)
    _script_check(entries, table)
    _tools_check(entries)


# The scripted table and the gold of the guide `name`, as its test walks it.
def _guide_read(name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    import guide_walk, harness

    table = guide_walk.table_build(os.path.join(_GUIDES_PATH, name))
    gold = cast(dict[str, Any], harness.gold_get(_GUIDE_GOLD + name))
    return table, gold


# The names of the databases of a directory, each a `NAME.sqlite` file.
def _database_names(root: str) -> list[str]:
    return sorted(
        name.removesuffix(_DB_EXTENSION)
        for name in os.listdir(root)
        if name.endswith(_DB_EXTENSION)
    )


# A BLOB's `UTF-8` text with no control but `\n` and `\t`, else None.
def _blob_text(data: bytes) -> str | None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    shown = text.replace("\n", "").replace("\t", "")
    return text if shown.isprintable() else None


# A cell of a row as text, whole.
def _cell_text(cell: object) -> str:
    if isinstance(cell, bytes):
        text = _blob_text(cell)
        if text is not None:
            return "b" + repr(text)
        if len(cell) <= _HEX_BYTES:
            return f"x'{cell.hex()}'"
        return f"<{len(cell)} bytes>"
    if isinstance(cell, str):
        return repr(cell)
    return "NULL" if cell is None else str(cell)


# A table's rows, in the order of all their columns, each as one line.
def _rows_text(connection: sqlite3.Connection, table: str) -> list[str]:
    quoted = '"' + table.replace('"', '""') + '"'
    count = len(connection.execute(f"SELECT * FROM {quoted}").description)
    order = ", ".join(str(column) for column in range(1, count + 1))
    rows = connection.execute(f"SELECT * FROM {quoted} ORDER BY {order}")
    return [
        _ROW_INDENT + ", ".join(_cell_text(cell) for cell in row)
        for row in rows
    ]


# The databases of a directory as text, each object's SQL and rows whole.
def database_lines(root: str) -> list[str]:
    lines: list[str] = []
    shown: dict[str, str] = {}
    for name in _database_names(root):
        lines.append(f"{_DB_MARK}{name}")
        connection = sqlite3.connect(os.path.join(root, name + _DB_EXTENSION))
        try:
            objects = connection.execute(_OBJECTS_SQL).fetchall()
            for kind, table, sql in objects:
                statement = " ".join(str(sql).split())
                first = shown.setdefault(statement, name)
                if first != name:
                    statement = f"{kind} {table}: the SQL of {first}"
                lines.append(statement)
                if kind == "table":
                    lines += _rows_text(connection, table)
        finally:
            connection.close()
    return lines


# Whether a commit after a put of `ref` replaces its row or drops its database.
def _put_replaced(ref: str, later: list[ReadEntry]) -> bool:
    import substrate

    db = substrate.ref_split(ref).db
    return any(
        _field_get(_header_of(entry), "key", "k") == ref
        or (type_of(entry) == "db.drop" and _payload_of(entry)["db"] == db)
        for entry in later
    )


# The bytes the server holds for a put's ref, once its size and sha256 agree.
def _value_held(ended: Any, entry: ReadEntry, ref: str) -> bytes:
    import substrate

    blob: dict[str, Any] = cast(dict[str, Any], entry.line)["1"]
    put = [(int(_field_get(blob, "size", "s")), str(blob[_DIGEST_FIELD]))]
    db, key, _ = substrate.ref_split(ref)
    rows = ended.kv_list(db, key) if db in ended.db_list() else []
    held = [(row.size, row.sha256.hex()) for row in rows if row.key == key]
    if held != put:
        raise AuditFailed(
            f"line {entry.number}: {ref} was put as {put[0][0]} bytes of"
            f" sha256 {put[0][1]}, and the server holds {held}"
        )
    data: bytes | str = ended.kv_get(ref).data
    if isinstance(data, bytes):
        return data
    with open(data, "rb") as file:
        return file.read()


# The JSON text of turn items, as the server's handler stores them.
def _items_text(items: list[Any]) -> str:
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


# Applies one commit to the store as the server's handler of its type does.
def _commit_replay(
    store: Any, ended: Any, entry: ReadEntry, later: list[ReadEntry]
) -> None:
    import jslb, substrate

    line = jslb.json_decode(json.dumps(entry.line, ensure_ascii=False))
    payload = jslb.payload_of(line)
    kind = type_of(entry)
    ref = _field_get(_header_of(entry), "key", "k")
    if kind == "kv.put" and not _put_replaced(ref, later):
        store.kv_put(ref, _value_held(ended, entry, ref))
    elif kind == "kv.delete":
        store.kv_delete(ref)
    elif kind == "doc.put":
        store.doc_put(payload["db"], payload["id"], payload["body"])
    elif kind == "db.create":
        store.db_create(payload["db"])
    elif kind == "db.drop":
        store.db_drop(payload["db"])
    elif kind == "turn.append":
        content = _items_text(payload["content"])
        store.turn_append(payload["scene"], payload["role"], content)
    elif kind == _PROMPT_TYPE:
        rows = [
            (str(message["role"]), _items_text([message]))
            for message in payload["messages"]
        ]
        store.turn_prompt(payload["scene"], rows)
    elif kind == "sql.run":
        statements = [
            substrate.SqlStatement(statement["sql"], statement["params"])
            for statement in payload["statements"]
        ]
        store.sql_run(payload["db"], statements)


# Applies one commit, a failure of the store raised as the check's at its line.
def _commit_try(
    store: Any, ended: Any, entry: ReadEntry, later: list[ReadEntry]
) -> None:
    try:
        _commit_replay(store, ended, entry, later)
    except AuditFailed:
        raise
    except Exception as error:
        raise AuditFailed(
            f"line {entry.number}: the replay of its {type_of(entry)} failed:"
            f" {error}"
        ) from error


# Raises at the first line where the server's text and the replay's differ.
def _texts_compare(held: list[str], made: list[str]) -> None:
    database = table = ""
    for server, replayed in itertools.zip_longest(held, made):
        if server != replayed:
            raise AuditFailed(
                f"the replay of the record's commits differs from the"
                f" server's databases at {database!r}, {table!r}: the server"
                f" holds {server!r}, the replay {replayed!r}"
            )
        if server.startswith(_DB_MARK):
            database = server
        elif not server.startswith(_ROW_INDENT):
            table = server


# Raises where `end` differs from `start` with the record's commits replayed.
def databases_check(
    entries: list[ReadEntry], start: str, end: str, scratch: str
) -> None:
    import substrate

    starts = [entry for entry in entries if type_of(entry) == "tap.start"]
    values: dict[str, Any] = _payload_of(starts[0])["settings"]
    limits = (values["overflow_bytes"], values["blob_max"])
    shutil.copytree(start, scratch)
    store = substrate.Store(scratch, *limits)
    ended = substrate.Store(end, *limits)
    commits = [
        entry
        for entry in entries
        if entry.label == _COMMIT_LANE and type_of(entry) in _COMMIT_TYPES
    ]
    try:
        for name in _database_names(scratch):
            store.db_open(name)
        for name in _database_names(end):
            ended.db_open(name)
        for index, entry in enumerate(commits):
            _commit_try(store, ended, entry, commits[index + 1 :])
    finally:
        for name in store.db_list():
            store.db_close(name)
        for name in ended.db_list():
            ended.db_close(name)
    _texts_compare(database_lines(end), database_lines(scratch))


# Whether a text holds `token` whole, no letter or digit just before or after.
def _token_held(text: str, token: str) -> bool:
    start = text.find(token)
    while start >= 0:
        end = start + len(token)
        before = text[max(start - 1, 0) : start]
        if not before.isalnum() and not text[end : end + 1].isalnum():
            return True
        start = text.find(token, start + 1)
    return False


# The one text the gold's query reads from its database in `end`, read only.
def _repeated_read(end: str, repeated: dict[str, Any]) -> str:
    db = str(repeated["db"])
    path = os.path.join(end, db + _DB_EXTENSION)
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        cursor = connection.execute(repeated["sql"], repeated["params"])
        rows: list[Any] = cursor.fetchall()
    finally:
        connection.close()
    shapes = [tuple(type(cell) for cell in row) for row in rows]
    if shapes != [(str,)] or not rows[0][0]:
        raise AuditFailed(
            f"the query of repeated on {db} gives {rows!r}, not one row of"
            " one text that is not empty"
        )
    return str(rows[0][0])


# The band an ai.say reply shows the player, or None for any other entry.
def _band_of(entry: ReadEntry) -> str | None:
    if type_of(entry) != _SAY_TYPE or _line_kind(entry) != _REPLY_KIND:
        return None
    return str(_payload_of(entry)["subtitle"])


# Each `content` text in a value at any depth, with the members leading to it.
def _contents_found(
    value: Any, path: list[str | int]
) -> list[tuple[list[str | int], str]]:
    found: list[tuple[list[str | int], str]] = []
    if isinstance(value, dict):
        for key, item in cast(dict[str, Any], value).items():
            if key == "content" and isinstance(item, str):
                found.append(([*path, key], item))
            else:
                found += _contents_found(item, [*path, key])
    elif isinstance(value, list):
        for index, item in enumerate(cast(list[Any], value)):
            found += _contents_found(item, [*path, index])
    return found


# The evidence that the guide said the text the gold's query reads from `end`.
def repeat_check(
    entries: list[ReadEntry],
    table: dict[str, Any],
    end: str,
    repeated: dict[str, Any],
) -> str:
    text = _repeated_read(end, repeated)
    bands = [
        index
        for index, entry in enumerate(entries)
        if _band_of(entry) is not None
    ]
    if not bands:
        raise AuditFailed(
            f"the record holds no ai.say reply, so no band holds {text!r}"
        )
    band = entries[bands[-1]]
    shown = str(_band_of(band))
    if not _token_held(shown, text):
        raise AuditFailed(
            f"line {band.number}: the last band {shown!r} does not hold"
            f" {text!r}"
        )
    # The end turn runs from the last input before the last band to that band.
    began = max(
        index
        for index in range(bands[-1])
        if type_of(entries[index]) == _INPUT_TYPE
    )
    turn = entries[began : bands[-1]]
    reply, answer = _replies_of(turn)[-1]
    said = _said_of(answer["output"])
    if not _token_held(said, text):
        raise AuditFailed(
            f"line {reply.number}: the model reply before the last band says"
            f" {said!r}, which does not hold {text!r}"
        )
    call, asked = _calls_of(turn)[-1]
    endings = _outputs_ending(asked["input"])
    if not any(_token_held(str(item["output"]), text) for item in endings):
        raise AuditFailed(
            f"line {call.number}: the last model call of the end turn carries"
            f" no tool result that holds {text!r}"
        )
    for path, content in _contents_found(table, []):
        if _token_held(content, text):
            raise AuditFailed(
                f"the table's content at {json.dumps(path)} holds {text!r},"
                " so the guide could say it in its own words"
            )
    for entry in turn:
        kind = type_of(entry)
        committed = entry.label == _COMMIT_LANE and kind in _COMMIT_TYPES
        if committed and kind != "turn.append":
            raise AuditFailed(
                f"line {entry.number}: the end turn commits {kind}, where it"
                " should commit nothing but turn.append"
            )
    told = [
        index
        for index in bands[:-1]
        if _token_held(str(_band_of(entries[index])), text)
    ]
    if not told:
        raise AuditFailed(
            f"line {band.number}: no band before the last holds {text!r}, so"
            " it was not told when it was made"
        )
    first = entries[told[0]]
    quoted = json.dumps(text, ensure_ascii=False)
    return (
        f"repeated: {quoted} from {repeated['db']}, first said at"
        f" L{first.number}, said at the end at L{band.number} by the reply"
        f" L{reply.number}, carried by the tool result L{call.number}, in no"
        " text of the guide's own, and the last turn committed nothing but"
        " turns"
    )


# Prints the digest and, when asked, checks and prints the verdict.
def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description="Print the audit digest of an audit document, every entry"
        " told, and check a run not expected to fail when asked.",
        allow_abbrev=False,
    )
    parser.add_argument("path", help="the audit document to read")
    parser.add_argument(
        "--check",
        action="store_true",
        help="then exit 1 at the first unexpected failure, naming its line",
    )
    parser.add_argument(
        "--guide",
        metavar="NAME",
        help="check as --check does, then exit 1 at the first message the"
        " walk of python/guides/NAME does not expect, naming its line",
    )
    parsed = parser.parse_args(arguments)
    entries = entries_parse(document_read(parsed.path))
    lines = [f"audit digest of {parsed.path}", *digest_lines(entries)]
    failed = False
    if parsed.check or parsed.guide is not None:
        try:
            failure_check(entries)
            if parsed.guide is not None:
                table, gold = _guide_read(parsed.guide)
                guide_check(entries, table, gold)
            passed = _CHECK_PASSED if parsed.guide is None else _GUIDE_PASSED
            lines += ["", passed]
        except AuditFailed as failure:
            lines += ["", f"failure: {failure}"]
            failed = True
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
