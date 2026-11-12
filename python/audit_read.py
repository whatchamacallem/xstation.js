#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Reads an audit document for a person, who cannot read it whole: a listing of
# one line per entry with its line number in the document, then a summary of
# what the run did. With --check it then stops at the first unexpected failure
# and exits 1, so that a person or a test need not look for one by eye. It is
# for a run that is not expected to fail: the wire and browser tests' roots
# fail on purpose, and the check would be right to refuse them. A line is read
# whole, through `audit.ShownLog`, so a model call counts all it sent though
# the document holds only what was new, and the check then proves that it was
# new. --guide NAME also checks that each message is the one the walk of
# python/guides/NAME expects, and --digest FILE writes the audit digest, the
# run told as the player's and the model's conversation, the verdict last.
#
#     python3 python/audit_read.py PATH [--check] [--guide NAME]
#         [--digest FILE]

import argparse, base64, collections, fcntl, itertools, json, os, re, sys
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

# The field of a model call's body that holds its tool list.
_TOOLS_FIELD = "tools"

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

# The lines on the commits' lane that are not commits of the store.
_NOT_COMMITS = (_MCP_TYPE, "tap.start", "db.sync")

# What the record shows for a credential.
_MASK = "<masked>"

# The range of the statuses of an HTTP answer that succeeded.
_STATUS_LOW = 200
_STATUS_HIGH = 300

# The widest detail of a listing line, so that one line stays one line.
_DETAIL_MAX = 150

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

# The lanes of the media port, whose lines repeat the worker's media.store.
_MEDIA_LANES = ("ui to media", "media to ui")

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

# The longest string of a tool's arguments or a body the digest shows whole.
_CUT_LENGTH = 300

# The longest text of a tool's result or a call output the digest shows whole.
_RESULT_LENGTH = 2000

# The indent of a digest record's lines after its first, and the lane's width.
_RECORD_INDENT = "        "
_LANE_WIDTH = 13

# The first line of the digest, which says how to read a record.
_DIGEST_LEGEND = (
    "each record: its line in the audit, seconds from the first entry, its"
    " lane, then what it says"
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


# A value as one short line.
def _text_short(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value)
    text = text.replace("\n", "\\n")
    if len(text) <= _DETAIL_MAX:
        return text
    return text[:_DETAIL_MAX] + "..."


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


# The input items of a model call as sent, none for any other line.
def input_of(entry: ReadEntry) -> list[dict[str, Any]]:
    body = _call_body(entry)
    return [] if body is None else body["input"]


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


# A request's tool list counted, or the text a debug mode request sends.
def _tools_text(tools: Any) -> str:
    if isinstance(tools, list):
        return f"{len(tools)} tools"
    return f"tools {tools}"


# What a request to the provider's port asks.
def _request_detail(entry: ReadEntry) -> str:
    body = _call_body(entry)
    if body is None:
        asked = _payload_of(entry).get("json", {}).get("prompt")
        return f"image {_text_short(asked)}"
    items = body["input"]
    chained = "a chain start"
    if _CHAIN_FIELD in body:
        chained = f"chained to {body[_CHAIN_FIELD]}"
    return (
        f"model {len(items)} items ({_kinds_text(items)}), {entry.kept} kept,"
        f" {chained}, {_tools_text(body.get(_TOOLS_FIELD, []))}"
    )


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


# What the provider's port answered.
def _answer_detail(entry: ReadEntry) -> str:
    payload = _payload_of(entry)
    status = payload.get("status")
    body = _reply_body(entry)
    if body is None:
        images = payload.get("json", {}).get("data", [])
        return f"status {status}, {len(images)} images"
    output = body["output"]
    calls = [call["name"] for call in _calls_in(output)]
    return (
        f"status {status}, {body['id']}, {_cached_text(body)}, calls {calls},"
        f" says {_text_short(_said_of(output))}"
    )


# What an MCP message asks or answers.
def _mcp_detail(entry: ReadEntry) -> str:
    payload = _payload_of(entry)
    params = payload.get("params", {})
    if "name" in params:
        return f"call {params['name']} {_text_short(params.get('arguments'))}"
    if "method" in payload:
        return str(payload["method"])
    result = payload.get("result", {})
    if "content" in result:
        texts = [part.get("text") for part in result["content"]]
        failed = "failed " if result.get("isError") else ""
        return f"{failed}result {_text_short(texts)}"
    return _text_short(payload)


# The last column of an entry's listing line.
def _detail_of(entry: ReadEntry) -> str:
    if entry.line is None:
        if entry.label.startswith(_DUMP_PREFIX):
            return f"{len(entry.body)} bytes"
        return _text_short(entry.body.strip())
    kind = type_of(entry)
    if kind == _HTTP_TYPE:
        if _field_get(_header_of(entry), "reply", "r") is None:
            return _request_detail(entry)
        return _answer_detail(entry)
    if kind == _MCP_TYPE:
        return _mcp_detail(entry)
    blobs = _blobs_of(entry)
    detail = _text_short(_payload_of(entry))
    return detail + (f" + {blobs} blobs" if blobs else "")


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


# The listing: per entry its line, time from the first, gap, lane and detail.
def listing_lines(entries: list[ReadEntry]) -> list[str]:
    lines: list[str] = []
    start = 0
    first = entries[0].at if entries else 0
    before = first
    for entry in entries:
        if entry.start != start:
            start = entry.start
            lines.append(f"==== engine start {start}")
        elapsed = (entry.at - first) / _SECOND_MILLISECONDS
        lines.append(
            f"L{entry.number:<6} +{elapsed:7.3f} {entry.at - before:5} ms"
            f"  {entry.label:<14} {type_of(entry):<14} {_mark_of(entry):<7}"
            f" {_detail_of(entry)}"
        )
        before = entry.at
    return lines


# The names of the tools the first model call lists, or the text it sends.
def _tools_listed(entries: list[ReadEntry]) -> list[str] | str:
    calls = _calls_of(entries)
    if not calls:
        return []
    tools = calls[0][1].get(_TOOLS_FIELD, [])
    if not isinstance(tools, list):
        return str(tools)
    return [str(tool["name"]) for tool in tools]


# The summary's lines of the tools called and of those listed.
def _tools_lines(listed: list[str] | str, called: dict[str, int]) -> list[str]:
    if isinstance(listed, str):
        return [
            f"tools called: {len(called)}: {called}",
            f"tools listed: none, the first model call sent {listed}",
        ]
    return [
        f"tools called: {len(called)} of {len(listed)} listed: {called}",
        f"tools not called: {[name for name in listed if name not in called]}",
    ]


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
def prompt_copies(entries: list[ReadEntry]) -> list[int]:
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


# Each lane's bytes as sent and as written, both laid out as the document is.
def _bytes_lines(entries: list[ReadEntry]) -> list[str]:
    lines: list[str] = []
    for lane in _CONVERSATION_LANES:
        sent = 0
        written = 0
        for entry in entries:
            if entry.label == lane:
                text = json.dumps(
                    entry.line, ensure_ascii=False, indent=_JSON_INDENT
                )
                sent += len(text.encode("utf-8"))
                end = _written_of(entry)[1]
                written += len(entry.body[:end].encode("utf-8"))
        lines.append(
            f"bytes of the lane {lane}: {sent} as sent, {written} as written"
        )
    return lines


# The commits the browser sent the server, counted by type.
def _commits_counted(entries: list[ReadEntry]) -> dict[str, int]:
    commits: dict[str, int] = {}
    for entry in entries:
        kind = type_of(entry)
        if (
            entry.label == _COMMIT_LANE
            and kind not in _NOT_COMMITS
            and _mark_of(entry) == ""
        ):
            commits[kind] = commits.get(kind, 0) + 1
    return commits


# What the two sides' dumps show, side by side, none when no dump was made.
def _dumps_text(entries: list[ReadEntry]) -> str:
    dumps = [
        entry.body for entry in entries if entry.label.startswith(_DUMP_PREFIX)
    ]
    if not dumps:
        return "none"
    same = all(dump == dumps[0] for dump in dumps)
    return f"{len(dumps)}, {'the same text' if same else 'differing'}"


# The summary of what the run did, each line one measurement of the record.
def summary_lines(entries: list[ReadEntry]) -> list[str]:
    inputs = [
        str(_payload_of(entry).get("text"))
        for entry in entries
        if entry.label == _INPUT_LANE and type_of(entry) == _INPUT_TYPE
    ]
    listed = _tools_listed(entries)
    called = _tools_called(entries)
    calls = _calls_of(entries)
    started = sum(_CHAIN_FIELD not in body for _, body in calls)
    span = entries[-1].at - entries[0].at if entries else 0
    starts = entries[-1].start if entries else 0
    return [
        f"entries: {len(entries)} in {span / _SECOND_MILLISECONDS:.3f} s,"
        f" engine starts: {starts}",
        f"inputs: {len(inputs)}: {inputs}",
        f"model calls: {len(calls)}, chains started: {started}, copies of"
        f" the system prompt sent: {sum(prompt_copies(entries))}",
        f"system prompt written in the conversation's lanes:"
        f" {prompt_recorded(entries)}",
        f"input tokens of the model calls: {_usage_text(entries)}",
        *_bytes_lines(entries),
        *_tools_lines(listed, called),
        f"commits to the server: {_commits_counted(entries)}",
        f"database dumps: {_dumps_text(entries)}",
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


# The bytes of the first blob a line carries, as its blob header counts them.
def _blob_size(entry: ReadEntry) -> int:
    blob: dict[str, Any] = cast(dict[str, Any], entry.line)["1"]
    return int(_field_get(blob, "size", "s"))


# A count and its noun, the noun plural unless the count is one.
def _count_text(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


# A text cut to `limit` characters, its whole length told when cut.
def _text_cut(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... ({len(text)} characters)"


# A value with each string in it past `_CUT_LENGTH` cut.
def _strings_cut(value: Any) -> Any:
    if isinstance(value, str):
        return _text_cut(value, _CUT_LENGTH)
    if isinstance(value, list):
        return [_strings_cut(item) for item in cast(list[Any], value)]
    if isinstance(value, dict):
        fields = cast(dict[str, Any], value)
        return {key: _strings_cut(item) for key, item in fields.items()}
    return value


# A value as one line of JSON, each long string in it cut.
def _json_cut(value: Any) -> str:
    return json.dumps(_strings_cut(value), ensure_ascii=False)


# A function call: its name, its id, then its arguments with long strings cut.
def _call_text(call: dict[str, Any]) -> str:
    arguments = _json_cut(json.loads(call["arguments"]))
    return f"{call['name']} {call['call_id']} {arguments}"


# A text under a label, each line of the text after the first indented more.
def _text_block(label: str, text: str) -> list[str]:
    first, *rest = text.split("\n")
    return [
        f"{_RECORD_INDENT}{label}{first}",
        *(f"{_RECORD_INDENT}  {part}" if part else "" for part in rest),
    ]


# The kind an entry the digest does not show is counted under, else None.
def _hidden_kind(entry: ReadEntry) -> str | None:
    if entry.line is None:
        return None if entry.label.startswith(_DUMP_PREFIX) else entry.label
    kind = type_of(entry)
    shape = _line_kind(entry)
    if (
        entry.label in _MEDIA_LANES
        or (kind == _SAY_TYPE and shape == _REQUEST_KIND)
        or (kind in (_RENDER_TYPE, _MEDIA_TYPE) and shape == _REPLY_KIND)
    ):
        return f"{entry.label} {kind} {shape}"
    return None


# The one line that tells a line of a type the digest tells in one, or None.
def _line_told(entry: ReadEntry, payload: dict[str, Any]) -> str | None:
    kind = type_of(entry)
    name = _name_of(entry)
    if kind in ("tap.start", "settings.set") and "switches" in payload:
        switches = json.dumps(payload["switches"])
        return f"{name}, the settings and the switches {switches}"
    if kind == "kv.put":
        key = _field_get(_header_of(entry), "key", "k")
        return f"{name} {key}, {_blob_size(entry)} bytes"
    if kind == "kv.delete":
        return f"{name} {_field_get(_header_of(entry), 'key', 'k')}"
    if kind in ("db.create", "db.drop"):
        return f"{name} {payload['db']}"
    if kind == "db.restore":
        files = _count_text(payload.get("files", 0), "file")
        return f"{name} {payload['db']}, {_blob_size(entry)} bytes, {files}"
    if kind == "db.sync" and "databases" in payload:
        return f"{name}: databases {', '.join(payload['databases'])}"
    if kind == "turn.append":
        return (
            f"{name} to {payload['scene']}, role {payload['role']},"
            f" {_count_text(len(payload['content']), 'item')}"
        )
    if kind == _MEDIA_TYPE:
        return f"{name} {payload['k']}, {_blob_size(entry)} bytes"
    if not payload:
        return name
    return None


# The digest's reading of the record: its times, prompts shown and requests.
class _DigestBook:
    # Starts before the record's first entry, at that entry's time.
    def __init__(self, first: int) -> None:
        self.first = first
        self.start = 0
        self.turn = 0
        # The line that showed each system text whole, by the text.
        self.shown: dict[str, int] = {}
        # Each MCP request's method, by its start, sender, receiver and id.
        self.methods: dict[tuple[int, str, str, object], str] = {}
        # The entries not shown, counted by kind.
        self.hidden: collections.Counter[str] = collections.Counter()

    # The first line of an entry's record: its line, seconds, lane and text.
    def head_make(self, entry: ReadEntry, text: str) -> str:
        seconds = (entry.at - self.first) / _SECOND_MILLISECONDS
        return (
            f"L{entry.number:<6} {seconds:8.3f}  {entry.label:<{_LANE_WIDTH}}"
            f" {text}"
        )

    # A system text shown whole the first time, then named by that line.
    def system_lines(self, text: str, number: int) -> list[str]:
        if text in self.shown:
            return [f"{_RECORD_INDENT}system: the text of L{self.shown[text]}"]
        self.shown[text] = number
        return _text_block("system: ", text)

    # The lines of an input item of a model call or of a commit of turns.
    def item_lines(self, item: dict[str, Any], number: int) -> list[str]:
        kind = _kind_of(item)
        if kind == _ANSWER_TYPE:
            output = _text_cut(str(item["output"]), _RESULT_LENGTH)
            return _text_block(f"output {item['call_id']}: ", output)
        if kind == _CALL_TYPE:
            return [f"{_RECORD_INDENT}call {_call_text(item)}"]
        if kind == _REASONING_TYPE:
            return [f"{_RECORD_INDENT}reasoning {item['id']}"]
        if kind == _MESSAGE_TYPE:
            return _text_block("assistant: ", _said_of([item]))
        if kind == _SYSTEM_ROLE:
            return self.system_lines(str(item["content"]), number)
        return _text_block(f"{kind}: ", str(item["content"]))

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
            lines += _text_block("says: ", _said_of(output))
        for call in _calls_in(output):
            lines.append(f"{_RECORD_INDENT}call {_call_text(call)}")
        return lines

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
            if ident is not None:
                self.methods[(entry.start, sender, receiver, ident)] = method
            if method != _CALL_METHOD:
                told = " ".join(part for part in ("mcp", mark, method) if part)
                return [self.head_make(entry, told)]
            params = payload["params"]
            head = f"tool call {mark} {params['name']}"
            arguments = _json_cut(params["arguments"])
            return [self.head_make(entry, head), _RECORD_INDENT + arguments]
        method = self.methods[(entry.start, receiver, sender, reply)]
        if "error" in payload:
            head = f"mcp {mark} {method} failed: {_json_cut(payload['error'])}"
            return [self.head_make(entry, head)]
        result: dict[str, Any] = payload["result"]
        if method == _CALL_METHOD:
            texts = _PART_JOINT.join(
                part["text"] for part in result["content"]
            )
            failed = " failed" if result.get("isError") is True else ""
            text = _text_cut(texts, _RESULT_LENGTH)
            head = self.head_make(entry, f"tool result {mark}{failed}")
            return [head, *_text_block("", text)]
        if "tools" in result:
            names = [str(tool["name"]) for tool in result["tools"]]
            listed = f"{len(names)} tools: {', '.join(names)}"
            return [self.head_make(entry, f"mcp {mark} {method}, {listed}")]
        told = f"mcp {mark} {method}: {_json_cut(result)}"
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
            return [head, *_text_block("prompt: ", prompt)]
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
        return [head, _RECORD_INDENT + _json_cut(payload)]

    # The lines of an entry's record, none for an entry the digest counts.
    def record_lines(self, entry: ReadEntry) -> list[str]:
        hidden = _hidden_kind(entry)
        if hidden is not None:
            self.hidden[hidden] += 1
            return []
        if entry.line is None:
            return [self.head_make(entry, f"{len(entry.body)} bytes")]
        kind = type_of(entry)
        name = _name_of(entry)
        payload = _payload_of(entry)
        if kind == _INPUT_TYPE:
            self.turn += 1
            player = self.head_make(entry, f"player: {payload['text']}")
            return ["", f"---- turn {self.turn}", player]
        if kind == _SAY_TYPE:
            head = (
                f"{name}, reply stored at row {payload['turn']}, showing"
                f" {payload['scene']}"
            )
            band = _text_block("band: ", str(payload["subtitle"]))
            return [self.head_make(entry, head), *band]
        if kind == _RENDER_TYPE:
            image = payload.get("image", "none")
            head = f"{name} to {payload['scene']}, image {image}"
            subtitle = _text_block("subtitle: ", str(payload["subtitle"]))
            return [self.head_make(entry, head), *subtitle]
        if kind == _PROMPT_TYPE:
            messages: list[dict[str, Any]] = payload["messages"]
            counted = _count_text(len(messages), "message")
            head = f"{name} to {payload['scene']}, {counted}"
            lines = [self.head_make(entry, head)]
            for message in messages:
                lines += self.item_lines(message, entry.number)
            return lines
        if kind == "doc.put":
            head = f"{name} {payload['db']} {payload['id']}"
            body = _RECORD_INDENT + _json_cut(payload["body"])
            return [self.head_make(entry, head), body]
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


# The audit digest: the shown entries told whole, the rest counted, a summary.
def digest_lines(entries: list[ReadEntry]) -> list[str]:
    book = _DigestBook(entries[0].at if entries else 0)
    lines = [_DIGEST_LEGEND]
    for entry in entries:
        if entry.start != book.start:
            book.start = entry.start
            lines += ["", f"==== engine start {entry.start}", "---- bring up"]
        lines += book.record_lines(entry)
    hidden = sum(book.hidden.values())
    lines += ["", f"not shown: {hidden} of {len(entries)} entries"]
    for kind, count in sorted(book.hidden.items()):
        lines.append(f"{_RECORD_INDENT}{kind}: {count}")
    return [*lines, "", *summary_lines(entries)]


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
        return f"an MCP request failed: {_text_short(payload['error'])}"
    result = payload.get("result", {})
    if result.get("isError") is True:
        return f"a tool failed: {_text_short(result.get('content'))}"
    return None


# What is wrong with a line entry alone, or None.
def _line_failure(entry: ReadEntry) -> str | None:
    kind = type_of(entry)
    payload = _payload_of(entry)
    if kind in _FAILURE_TYPES:
        return f"a line of type {kind}: {_text_short(payload)}"
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
        return f"a program ended badly: {_text_short(entry.body)}"
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
    return f"a guide makes no {entry.label}: {_text_short(entry.body.strip())}"


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


# Prints the listing and summary, checks and writes the digest when asked.
def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description="Print one line per entry of an audit document with a"
        " summary of the run, for a run not expected to fail, and write its"
        " digest when asked.",
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
    parser.add_argument(
        "--digest",
        metavar="FILE",
        help="write the audit digest to FILE, the verdict of a check last",
    )
    parsed = parser.parse_args(arguments)
    entries = entries_parse(document_read(parsed.path))
    for line in listing_lines(entries) + summary_lines(entries):
        print(line)
    verdict: list[str] = []
    failed = False
    if parsed.check or parsed.guide is not None:
        try:
            failure_check(entries)
            if parsed.guide is not None:
                table, gold = _guide_read(parsed.guide)
                guide_check(entries, table, gold)
            passed = _CHECK_PASSED if parsed.guide is None else _GUIDE_PASSED
            verdict = [passed]
        except AuditFailed as failure:
            verdict = [f"failure: {failure}"]
            failed = True
    if parsed.digest is not None:
        told = verdict and ["", *verdict]
        lines = [f"audit digest of {parsed.path}", *digest_lines(entries)]
        with open(parsed.digest, "w", encoding="utf-8") as file:
            file.write("\n".join([*lines, *told]) + "\n")
    for line in verdict:
        print(line, file=sys.stderr if failed else sys.stdout)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
