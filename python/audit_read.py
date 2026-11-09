#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Reads an audit document for a person, who cannot read it whole: one line per
# entry with its line number in the document, then a summary of what the run
# did. With --check it then stops at the first unexpected failure and exits 1,
# so that a person or a test need not look for one by eye. It is for a run that
# is not expected to fail: the wire and browser tests' roots fail on purpose,
# and the check would be right to refuse them. Standard library only.
#
#     python3 python/audit_read.py PATH [--check]

import argparse, collections, fcntl, json, re, sys
from typing import Any, NamedTuple, cast

# The name `argparse` shows, as `sys.argv` may be empty.
_PROGRAM_NAME = "audit_read.py"

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

# The lines on that lane that are not commits of the store.
_NOT_COMMITS = (_MCP_TYPE, "tap.start", "db.sync")

# What the record shows for a credential.
_MASK = "<masked>"

# The range of the statuses of an HTTP answer that succeeded.
_STATUS_LOW = 200
_STATUS_HIGH = 300

# The widest detail of a digest line, so that one line stays one line.
_DETAIL_MAX = 150

# The milliseconds of an hour, a minute and a second.
_HOUR_MILLISECONDS = 3600000
_MINUTE_MILLISECONDS = 60000
_SECOND_MILLISECONDS = 1000


# One entry: where its heading is, its start, time, label, body and line.
class ReadEntry(NamedTuple):
    number: int
    start: int
    at: int
    label: str
    body: str
    line: dict[str, Any] | None


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


# The entry of a heading's parts, its body lines read.
def _entry_make(
    number: int, start: int, at: int, label: str, lines: list[str]
) -> ReadEntry:
    body = "\n".join(lines).rstrip("\n")
    is_line = _LANE_MARK in label and not label.startswith(_DUMP_PREFIX)
    line = _line_decode(body, number) if is_line else None
    return ReadEntry(number, start, at, label, body, line)


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
    entries: list[ReadEntry] = []
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
                _entry_make(held[0], start, held[1], held[2], lines)
            )
        held = None
        lines = []
        if found:
            held = (number, _time_read(found), found.group(5))
        elif cast(re.Match[str], started).group(1).startswith(_ENGINE_START):
            start += 1
    if held is not None:
        entries.append(_entry_make(held[0], start, held[1], held[2], lines))
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


# The messages of a chat request, none for any other line.
def messages_of(entry: ReadEntry) -> list[dict[str, Any]]:
    if (
        type_of(entry) != _HTTP_TYPE
        or _field_get(_header_of(entry), "reply", "r") is not None
    ):
        return []
    return _payload_of(entry).get("json", {}).get("messages", [])


# The roles of a chat request's messages counted, as one short text.
def _roles_text(messages: list[dict[str, Any]]) -> str:
    roles = collections.Counter(str(message["role"]) for message in messages)
    return " ".join(f"{role}={roles[role]}" for role in sorted(roles))


# What a request to the provider's port asks.
def _request_detail(entry: ReadEntry) -> str:
    body: dict[str, Any] = _payload_of(entry).get("json", {})
    messages = messages_of(entry)
    if not messages:
        return f"image {_text_short(body.get('prompt'))}"
    last = messages[-1]
    said = last.get("content")
    return (
        f"chat {len(messages)} messages, {_roles_text(messages)},"
        f" {len(body.get('tools', []))} tools, last {last['role']}:"
        f" {_text_short(said)}"
    )


# What the provider's port answered.
def _answer_detail(entry: ReadEntry) -> str:
    payload = _payload_of(entry)
    body: dict[str, Any] = payload.get("json", {})
    status = payload.get("status")
    if "choices" not in body:
        return f"status {status}, {len(body.get('data', []))} images"
    message = body["choices"][0]["message"]
    calls = [
        call["function"]["name"] for call in message.get("tool_calls", [])
    ]
    said = "" if message.get("content") is None else message["content"]
    return f"status {status}, calls {calls}, says {_text_short(said)}"


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


# The last column of an entry's digest line.
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


# The digest: per entry its line, time from the first, gap, lane and detail.
def digest_lines(entries: list[ReadEntry]) -> list[str]:
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


# The names of the tools the provider was told of, in the first request.
def _tools_listed(entries: list[ReadEntry]) -> list[str]:
    for entry in entries:
        if messages_of(entry):
            tools = _payload_of(entry)["json"].get("tools", [])
            return [tool["function"]["name"] for tool in tools]
    return []


# Each tool the agent called, counted, in the order of first call.
def _tools_called(entries: list[ReadEntry]) -> dict[str, int]:
    called: dict[str, int] = {}
    for entry in entries:
        answer = _payload_of(entry).get("json", {})
        if type_of(entry) == _HTTP_TYPE and "choices" in answer:
            message = answer["choices"][0]["message"]
            for call in message.get("tool_calls", []):
                name = call["function"]["name"]
                called[name] = called.get(name, 0) + 1
    return called


# The copies of the first request's system prompt in each chat request.
def prompt_copies(entries: list[ReadEntry]) -> list[int]:
    chats = [messages_of(entry) for entry in entries if messages_of(entry)]
    if not chats:
        return []
    prompt = chats[0][0]["content"]
    return [
        sum(message.get("content") == prompt for message in messages)
        for messages in chats
    ]


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
    copies = prompt_copies(entries)
    span = entries[-1].at - entries[0].at if entries else 0
    starts = entries[-1].start if entries else 0
    return [
        f"entries: {len(entries)} in {span / _SECOND_MILLISECONDS:.3f} s,"
        f" engine starts: {starts}",
        f"inputs: {len(inputs)}: {inputs}",
        f"model calls: {len(copies)}, copies of the system prompt in each:"
        f" {sorted(set(copies))}",
        f"tools called: {len(called)} of {len(listed)} listed: {called}",
        f"tools not called: {[name for name in listed if name not in called]}",
        f"commits to the server: {_commits_counted(entries)}",
        f"database dumps: {_dumps_text(entries)}",
    ]


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
    stray = _sleep_stray(entries)
    if stray is not None:
        raise AuditFailed(stray)
    copies = prompt_copies(entries)
    if any(count != 1 for count in copies):
        raise AuditFailed(
            f"a model call holds the system prompt other than once: {copies}"
        )


# Prints the digest and summary, checks when asked, returns the exit code.
def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description="Print one line per entry of an audit document with a"
        " summary of the run, for a run not expected to fail.",
        allow_abbrev=False,
    )
    parser.add_argument("path", help="the audit document to read")
    parser.add_argument(
        "--check",
        action="store_true",
        help="then exit 1 at the first unexpected failure, naming its line",
    )
    parsed = parser.parse_args(arguments)
    entries = entries_parse(document_read(parsed.path))
    for line in digest_lines(entries) + summary_lines(entries):
        print(line)
    if parsed.check:
        try:
            failure_check(entries)
        except AuditFailed as failure:
            print(f"failure: {failure}", file=sys.stderr)
            return 1
        print("check: no unexpected failure")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
