#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Writes the synthetic transcripts in this directory: every JSLB line is
# encoded by the rules of `hyperposition-plan.md` section 3 and rendered
# as its 3.11 says, the JSON text followed by one `<blob "n"=K>` tag per
# blob. Sizes and hashes are computed from the synthetic bytes; pids and
# ids are placeholders.
#
#     python3 DATA/transcripts_make.py

import base64, hashlib, json, os, struct, zlib

_DATA_PATH = os.path.dirname(os.path.abspath(__file__))

_API_PATH = os.path.join(os.path.dirname(_DATA_PATH), "API")

# The server's root and what `hello` names.
_ROOT = "/home/t/.cache/xsjs"
_BOOTSTRAP = f"{_ROOT}/bootstrap.py"
_BOOTSTRAP_SHA256 = hashlib.sha256(b"bootstrap.py synthetic 0").hexdigest()
_PAGE_SHA256 = hashlib.sha256(
    b"hyperposition-engine.html synthetic 0"
).hexdigest()
_PID = 4242
_PID_AGAIN = 4250
_PROVIDER_KEY = "xai-SYNTHETIC-KEY"
_BASE_URL = "https://api.x.ai/v1"
_HYPERPOSITION = "/metaverse/hyperposition/1"

# Short header names and their full forms, the debug mode form.
_FULL = {
    "t": "type",
    "v": "version",
    "i": "id",
    "r": "reply",
    "k": "key",
    "b": "blobs",
    "s": "size",
}

# The seeds of a new metaverse in `seq` order: two documents, three rows.
_ANALYST_TEXT = (
    "You are a very bored British psychoanalyst. You hold the"
    " hyperposition, a dark place of fog and a few inexplicable lights."
    " Find the right universe for the player and act on requests without"
    " judgement. Your scripts are the database administrator of every"
    " universe you create: typed tables, indexes, views, no JSON columns"
    " unless a document is what fits."
)
_SEED_DOCS: list[tuple[str, dict[str, object]]] = [
    (
        "hyperposition",
        {"0": {"t": "scene"}, "subtitle": "How can I help you?"},
    ),
    ("prompt/analyst", {"0": {"t": "prompt"}, "text": _ANALYST_TEXT}),
]
_SEED_KV = [
    ("player", "player"),
    ("world", "metaverse"),
    ("scene", _HYPERPOSITION),
]
_METAVERSE_SEQ = len(_SEED_DOCS) + len(_SEED_KV)

# The bootstrap script the server seeds into `_files`, the AI's to edit.
_BOOTSTRAP_SCRIPT = """\
// The database administration the engine seeds: a universe, a world and
// a region, and the player's place in them. Edit freely.
const store = engine.store;
store.db_create(args.universe);
store.sql_run(args.universe, [
  {sql: "CREATE TABLE world (name TEXT PRIMARY KEY, title TEXT NOT NULL)"
    + " STRICT", params: []},
  {sql: "INSERT INTO world VALUES (?, ?)", params: [args.world, args.title]},
]);
store.db_create(args.world);
store.sql_run(args.world, [
  {sql: "CREATE TABLE region (name TEXT PRIMARY KEY, tide INTEGER NOT NULL"
    + " DEFAULT 0) STRICT", params: []},
  {sql: "INSERT INTO region (name) VALUES (?)", params: [args.region]},
]);
store.db_create(args.region);
const player = store.kv_get("/metaverse/player").data;
store.sql_run("metaverse", [
  {sql: "INSERT INTO universe VALUES (?, ?, ?, ?)",
    params: [args.universe, args.title, player, args.world]},
]);
store.kv_put("/metaverse/world", args.world);
return {universe: args.universe, world: args.world, region: args.region};
"""

# A script the AI writes in 08: a simulation step.
_STEP_SCRIPT = """\
// Advances the tide by args.hours in the region table of the world.
const results = engine.store.sql_run("castle_world", [
  {sql: "UPDATE region SET tide = tide + ? WHERE name = ?",
    params: [args.hours, "castle_gatehouse"]},
]);
engine.log(1, "tide advanced by " + args.hours);
return {changes: results[0].changes};
"""

# The universe the scripted provider makes in 02.
_UNIVERSE = "castle"
_UNIVERSE_TITLE = "The castle"
_WORLD = "castle_world"
_REGION = "castle_gatehouse"
_IMAGE_KEY = "/_files/gatehouse/arrival.png"
_IMAGE_PROMPT = (
    "A rain dark castle gatehouse at dusk seen from the far side of a"
    " moat, one lantern lit, painted, wide still frame, no people"
)
_SCENE_ID = "scene/arrival"
_SCENE_REF = f"/{_REGION}/{_SCENE_ID}/1"
_SUBTITLE = (
    "Mind the moat. The gatehouse keeper has been expecting someone,"
    " though not necessarily you."
)

# The statements the bootstrap script commits, as the server receives them.
_WORLD_DDL = (
    "CREATE TABLE world (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT"
)
_REGION_DDL = (
    "CREATE TABLE region (name TEXT PRIMARY KEY, tide INTEGER NOT NULL"
    " DEFAULT 0) STRICT"
)

# The TAP lines a browser run sends, one plan, one subtest per module.
_TAP_LINES = [
    "TAP version 14",
    "    1..2",
    "    ok 1 - test_i18n_missing_name_raises",
    "    ok 2 - test_i18n_placeholder_count_mismatch_raises",
    "ok 1 - test_i18n",
    "    1..3",
    "    ok 1 - test_roundtrip_empty_line",
    "    ok 2 - test_blob_split_inside_character",
    "    ok 3 - test_hard_error_gap_in_blob_headers",
    "ok 2 - test_jslb",
    "    1..2",
    "    ok 1 - test_task_sleep_wakes_in_either_order",
    "    ok 2 - test_synchronous_mode_drains_before_input",
    "ok 3 - test_queue",
    "1..3",
]

_NO_CHANGE: dict[str, object] = {"columns": [], "rows": [], "changes": 0}
_ONE_CHANGE: dict[str, object] = {"columns": [], "rows": [], "changes": 1}


# Encodes a JSON object with no whitespace outside strings.
def json_text(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# A 16 by 16 RGB PNG checkerboard of 4 pixel squares: hard edges, real bytes.
def pattern_make() -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body) & 0xFFFFFFFF
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)
        )

    size = 16
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    rows = b""
    for y in range(size):
        row = b"\x00"
        for x in range(size):
            on = (x // 4 + y // 4) % 2 == 0
            row += b"\xff\xff\xff" if on else b"\x00\x00\x00"
        rows += row
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


# Synthetic bytes standing in for a database file, 4096 bytes per page.
def snapshot_make(db: str, pages: int) -> bytes:
    body = b"SQLite format 3\x00" + db.encode()
    return body + b"\x00" * (4096 * pages - len(body))


Blob = tuple[bytes, dict[str, object]]


class Transcript:
    # `full` selects full header names, the debug mode form.
    def __init__(self, name: str, title: str, full: bool) -> None:
        self.name = name
        self.full = full
        self.lines: list[str] = [f"# {title}", "#"]
        self.count = 0
        # The next `i` per direction, from 1.
        self.ids: dict[tuple[str, str], int] = {}

    def note(self, text: str) -> None:
        self.lines.append(f"# {text}")

    # Appends one message with its number and direction.
    def event(self, source: str, target: str, text: str) -> None:
        self.count += 1
        self.lines.append(f"{self.count:04d} {source}->{target} {text}")

    def field(self, name: str) -> str:
        return _FULL[name] if self.full else name

    # Builds the header "0" in the selected form, defaults left out.
    def header(
        self,
        type: str,
        i: int | None,
        r: int | None,
        k: str | None,
        b: int,
    ) -> dict[str, object]:
        header: dict[str, object] = {self.field("t"): type}
        if i is not None:
            header[self.field("i")] = i
        if r is not None:
            header[self.field("r")] = r
        if k is not None:
            header[self.field("k")] = k
        if b:
            header[self.field("b")] = b
        return header

    # Builds the line object: header, blob headers, payload.
    def object(
        self,
        type: str,
        payload: dict[str, object] | None,
        blobs: list[Blob] | None,
        i: int | None = None,
        r: int | None = None,
        k: str | None = None,
    ) -> dict[str, object]:
        blobs = blobs or []
        line: dict[str, object] = {"0": self.header(type, i, r, k, len(blobs))}
        for number, (data, fields) in enumerate(blobs, 1):
            blob: dict[str, object] = {self.field("s"): len(data)}
            for name, value in fields.items():
                blob[self.field(name) if name in _FULL else name] = value
            line[str(number)] = blob
        line.update(payload or {})
        return line

    # Renders a line object: the JSON text, then one tag per blob.
    def render(self, line: dict[str, object]) -> str:
        text = json_text(line)
        number = 1
        while str(number) in line:
            text += f'<blob "n"={number}>'
            number += 1
        return text

    # Sends a request and returns its `i`.
    def request(
        self,
        source: str,
        target: str,
        type: str,
        payload: dict[str, object] | None = None,
        blobs: list[Blob] | None = None,
        k: str | None = None,
    ) -> int:
        i = self.ids.get((source, target), 0) + 1
        self.ids[(source, target)] = i
        line = self.object(type, payload, blobs, i=i, k=k)
        self.event(source, target, self.render(line))
        return i

    # Sends a reply and returns its object, for a wake to carry.
    def reply(
        self,
        source: str,
        target: str,
        r: int,
        type: str,
        payload: dict[str, object] | None = None,
        blobs: list[Blob] | None = None,
    ) -> dict[str, object]:
        line = self.object(type, payload, blobs, r=r)
        self.event(source, target, self.render(line))
        return line

    def notify(
        self,
        source: str,
        target: str,
        type: str,
        payload: dict[str, object] | None = None,
        blobs: list[Blob] | None = None,
        k: str | None = None,
    ) -> None:
        line = self.object(type, payload, blobs, k=k)
        self.event(source, target, self.render(line))

    # A request and its reply: the common exchange. Returns the reply.
    def exchange(
        self,
        source: str,
        target: str,
        type: str,
        payload: dict[str, object] | None,
        reply: dict[str, object] | None,
        blobs: list[Blob] | None = None,
        reply_blobs: list[Blob] | None = None,
        k: str | None = None,
    ) -> dict[str, object]:
        i = self.request(source, target, type, payload, blobs, k)
        return self.reply(target, source, i, type, reply, reply_blobs)

    # The task manager wakes a sleeping task on its own thread.
    def wake(
        self,
        thread: str,
        type: str,
        state: dict[str, object],
        replies: list[dict[str, object]],
    ) -> None:
        self.notify(thread, thread, type, {"state": state, "replies": replies})

    # An event that is not a JSLB line: HTTP, a WebSocket close.
    def raw(self, source: str, target: str, text: str) -> None:
        self.event(source, target, text)

    def write(self) -> str:
        path = os.path.join(_DATA_PATH, f"{self.name}.txt")
        with open(path, "w", encoding="utf-8", newline="\n") as output:
            output.write("\n".join(self.lines) + "\n")
        return path


# The settings the server sends, from the proposal in API/.
def settings_load() -> dict[str, object]:
    with open(os.path.join(_API_PATH, "settings.json"), encoding="utf-8") as f:
        return json.load(f)


# The two tool lists, from the proposal in API/.
def tools_load() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    with open(
        os.path.join(_API_PATH, "mcp", "tools.json"), encoding="utf-8"
    ) as f:
        tools = json.load(f)
    return tools["browser"]["result"]["tools"], tools["server"]["result"][
        "tools"
    ]


# The server's `seq` per database on a seeded root with nothing else.
def server_seq() -> dict[str, int]:
    return {
        "_settings": len(settings_load()),
        "_files": 1,
        "_preferences": 0,
        "metaverse": _METAVERSE_SEQ,
    }


def hello_payload(pid: int, seq: dict[str, int]) -> dict[str, object]:
    return {
        "bootstrap": _BOOTSTRAP,
        "sha256": _BOOTSTRAP_SHA256,
        "pid": pid,
        "root": _ROOT,
        "settings": settings_load(),
        "seq": seq,
        "provider_key": _PROVIDER_KEY,
    }


# The ttyd protocol messages before JSLB, and the hello, on a new socket.
def connection_open(t: Transcript, pid: int, seq: dict[str, int]) -> None:
    t.note("ttyd: the WebSocket, then its own protocol before JSLB.")
    t.raw("AI", "TTYD", "GET /token HTTP/1.1")
    t.raw("TTYD", "AI", '200 {"token":""}')
    t.raw(
        "AI",
        "TTYD",
        "GET /ws HTTP/1.1 Upgrade: websocket Sec-WebSocket-Protocol: tty",
    )
    t.raw("TTYD", "AI", "101 Switching Protocols Sec-WebSocket-Protocol: tty")
    t.raw("AI", "TTYD", '{"AuthToken":"","columns":80,"rows":24}')
    t.raw("TTYD", "AI", f"1python3 {_BOOTSTRAP} --root {_ROOT} (xt)")
    t.raw("TTYD", "AI", "2{}")
    t.note(
        "server: flock on engine.lock, tty.setraw on its pty. From here every"
        " message is '0' followed by JSLB bytes; the '0' is not shown."
    )
    i = t.request("SERVER", "AI", "hello", hello_payload(pid, seq))
    t.note("AI: the settings reach the UI before anything else runs there.")
    t.notify("AI", "UI", "settings.set", {"settings": settings_load()})
    t.reply("AI", "SERVER", i, "hello", {})
    t.notify(
        "AI",
        "UI",
        "boot.hello",
        {
            "bootstrap": _BOOTSTRAP,
            "sha256": _BOOTSTRAP_SHA256,
            "pid": pid,
            "root": _ROOT,
        },
    )


# The MCP sessions: the browser's server locally, the server's by `mcp`.
def mcp_open(t: Transcript) -> None:
    browser_tools, server_tools = tools_load()
    client_info = {"name": "hyperposition-engine", "version": "0"}
    t.note("MCP: the agent initializes both servers and lists their tools.")
    for source, target, name, tools in (
        ("AGENT", "MCP", "xsjs-browser", browser_tools),
        ("AI", "SERVER", "xsjs-server", server_tools),
    ):
        t.exchange(
            source,
            target,
            "mcp",
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": client_info,
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": name, "version": "0"},
                },
            },
        )
        t.notify(
            source,
            target,
            "mcp",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        t.exchange(
            source,
            target,
            "mcp",
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}},
        )


# The databases whose `seq` differs are replaced by the server's snapshot.
def databases_replace(
    t: Transcript, server: dict[str, int], browser: dict[str, int]
) -> None:
    for db, seq in server.items():
        if browser.get(db, 0) == seq:
            continue
        data = snapshot_make(db, 1 + seq)
        t.exchange(
            "AI",
            "SERVER",
            "db.snapshot",
            {"db": db},
            {"sha256": sha256_hex(data), "seq": seq},
            reply_blobs=[(data, {})],
        )


def boot_write() -> str:
    t = Transcript(
        "01_boot", "Boot: a new tab reaches the hyperposition.", False
    )
    t.note("UI: GET / from ttyd is the page; its scripts are inlined.")
    t.raw("BROWSER", "TTYD", "GET / HTTP/1.1")
    t.raw("TTYD", "BROWSER", f"200 text/html sha256 {_PAGE_SHA256}")
    t.note(
        "UI: error_overlay, utility, ui_strings and settings load first;"
        " page.ts makes new Worker(bundle, {name: 'ai'}) and a MessageChannel."
    )
    connection_open(t, _PID, server_seq())
    t.note(
        "AI: a fresh OPFS has seq 0 everywhere; each database whose seq"
        " differs from the server's is replaced by its snapshot."
        " _preferences is 0 on both sides, so it is not."
    )
    databases_replace(t, server_seq(), {})
    t.note(
        "AI: db.restore is local to the worker, no line. Then the scene:"
        " kv_get of /metaverse/world, of /metaverse/scene, and the document."
        " Its headers name no media, so the render carries no image."
    )
    mcp_open(t)
    t.exchange(
        "AI",
        "UI",
        "render",
        {"scene": _HYPERPOSITION, "subtitle": "How can I help you?"},
        {},
    )
    return t.write()


# The function tools of a chat request, from both servers' lists.
def function_tools() -> list[dict[str, object]]:
    browser_tools, server_tools = tools_load()
    tools: list[dict[str, object]] = []
    for prefix, group in (
        ("browser", browser_tools),
        ("server", server_tools),
    ):
        for tool in group:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": f"{prefix}.{tool['name']}",
                        "description": tool["description"],
                        "parameters": tool["inputSchema"],
                    },
                }
            )
    return tools


def tool_call(
    id: str, name: str, arguments: dict[str, object]
) -> dict[str, object]:
    return {
        "id": id,
        "type": "function",
        "function": {"name": name, "arguments": json_text(arguments)},
    }


# A chat request to the scripted port and the wake. Returns the message.
def chat_exchange(
    t: Transcript,
    state: dict[str, object],
    messages: list[dict[str, object]],
    content: str | None,
    tool_calls: list[dict[str, object]],
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    reply = t.exchange(
        "AI",
        "SCRIPT",
        "http.request",
        {
            "method": "POST",
            "url": f"{_BASE_URL}/chat/completions",
            "headers": {
                "authorization": f"Bearer {_PROVIDER_KEY}",
                "content-type": "application/json",
            },
            "json": {
                "model": "grok-4",
                "messages": messages,
                "tools": function_tools(),
                "tool_choice": "auto",
            },
        },
        {
            "status": 200,
            "headers": {"content-type": "application/json"},
            "json": {
                "id": f"chatcmpl-synthetic-{t.count}",
                "model": "grok-4",
                "choices": [
                    {
                        "index": 0,
                        "message": message,
                        "finish_reason": "tool_calls"
                        if tool_calls
                        else "stop",
                    }
                ],
            },
        },
    )
    t.wake("AI", "ai.model_reply", state, [reply])
    return message


# A turn appended locally and forwarded to the server. Returns the new seq.
def turn_forward(
    t: Transcript, scene: str, message: dict[str, object], since: int
) -> int:
    t.exchange(
        "AI",
        "SERVER",
        "turn.append",
        {
            "scene": scene,
            "role": message["role"],
            "content": message,
            "since": since,
        },
        {"n": since - _METAVERSE_SEQ + 1, "seq": since + 1},
    )
    return since + 1


# A tools/call over the local port, with the result. Returns the reply.
def tool_result(
    t: Transcript, i: int, result: dict[str, object]
) -> dict[str, object]:
    return t.reply(
        "MCP",
        "AGENT",
        i,
        "mcp",
        {
            "jsonrpc": "2.0",
            "id": i,
            "result": {
                "content": [{"type": "text", "text": json_text(result)}]
            },
        },
    )


def tool_request(
    t: Transcript, name: str, arguments: dict[str, object]
) -> int:
    return t.request(
        "AGENT",
        "MCP",
        "mcp",
        {
            "jsonrpc": "2.0",
            "id": t.ids.get(("AGENT", "MCP"), 0) + 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )


# A forwarded sql.run commit. Returns the new seq.
def sql_forward(
    t: Transcript,
    db: str,
    statements: list[dict[str, object]],
    results: list[dict[str, object]],
    since: int,
) -> int:
    t.exchange(
        "AI",
        "SERVER",
        "sql.run",
        {"db": db, "statements": statements, "since": since},
        {"results": results, "seq": since + 1},
    )
    return since + 1


# A forwarded kv.put with its blob. Returns the new seq.
def kv_forward(t: Transcript, ref: str, data: bytes, since: int) -> int:
    t.exchange(
        "AI",
        "SERVER",
        "kv.put",
        {"since": since},
        {"sha256": sha256_hex(data), "seq": since + 1},
        blobs=[(data, {})],
        k=ref,
    )
    return since + 1


def turn_write() -> str:
    t = Transcript(
        "02_turn",
        "A turn: the player answers 1; the scripted provider runs the"
        " bootstrap script, makes an image, writes and enters a scene.",
        False,
    )
    seq = server_seq()
    system = {"role": "system", "content": _ANALYST_TEXT}
    user = {"role": "user", "content": "1"}
    messages: list[dict[str, object]] = [system, user]
    say = t.request("UI", "AI", "ai.say", {"text": "1"})
    t.note(
        "AI: turn_append commits locally, then the same line is forwarded"
        " with since, the browser's seq before the write."
    )
    seq["metaverse"] = turn_forward(t, _HYPERPOSITION, user, seq["metaverse"])
    state: dict[str, object] = {"say": say, "scene": _HYPERPOSITION}
    t.note(
        "AI: the handler submits the chat request to the scripted port and"
        " sleeps with ai.model_reply; the queue wakes it with the reply."
    )
    bootstrap_args = {
        "universe": _UNIVERSE,
        "title": _UNIVERSE_TITLE,
        "world": _WORLD,
        "region": _REGION,
    }
    assistant = chat_exchange(
        t,
        state,
        messages,
        None,
        [
            tool_call(
                "call_1",
                "browser.script_run",
                {"name": "bootstrap", "args": bootstrap_args},
            )
        ],
    )
    messages.append(assistant)
    seq["metaverse"] = turn_forward(
        t, _HYPERPOSITION, assistant, seq["metaverse"]
    )
    i = tool_request(
        t, "browser.script_run", {"name": "bootstrap", "args": bootstrap_args}
    )
    t.note(
        "AI: the bootstrap script runs inside the mcp task; each operation"
        " it commits is forwarded as it happens."
    )
    t.exchange("AI", "SERVER", "db.create", {"db": _UNIVERSE}, {})
    seq[_UNIVERSE] = sql_forward(
        t,
        _UNIVERSE,
        [
            {"sql": _WORLD_DDL, "params": []},
            {
                "sql": "INSERT INTO world VALUES (?, ?)",
                "params": [_WORLD, _UNIVERSE_TITLE],
            },
        ],
        [_NO_CHANGE, _ONE_CHANGE],
        0,
    )
    t.exchange("AI", "SERVER", "db.create", {"db": _WORLD}, {})
    seq[_WORLD] = sql_forward(
        t,
        _WORLD,
        [
            {"sql": _REGION_DDL, "params": []},
            {
                "sql": "INSERT INTO region (name) VALUES (?)",
                "params": [_REGION],
            },
        ],
        [_NO_CHANGE, _ONE_CHANGE],
        0,
    )
    t.exchange("AI", "SERVER", "db.create", {"db": _REGION}, {})
    seq["metaverse"] = sql_forward(
        t,
        "metaverse",
        [
            {
                "sql": "INSERT INTO universe VALUES (?, ?, ?, ?)",
                "params": [_UNIVERSE, _UNIVERSE_TITLE, "player", _WORLD],
            }
        ],
        [_ONE_CHANGE],
        seq["metaverse"],
    )
    seq["metaverse"] = kv_forward(
        t, "/metaverse/world", _WORLD.encode(), seq["metaverse"]
    )
    script_value = {"universe": _UNIVERSE, "world": _WORLD, "region": _REGION}
    reply = tool_result(t, i, {"value": script_value, "lines": []})
    t.wake("AI", "ai.tool_reply", state, [reply])
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": json_text({"value": script_value, "lines": []}),
        }
    )
    image_args = {"prompt": _IMAGE_PROMPT, "key": _IMAGE_KEY}
    assistant = chat_exchange(
        t,
        state,
        messages,
        None,
        [tool_call("call_2", "browser.image_make", image_args)],
    )
    messages.append(assistant)
    seq["metaverse"] = turn_forward(
        t, _HYPERPOSITION, assistant, seq["metaverse"]
    )
    i = tool_request(t, "browser.image_make", image_args)
    t.note(
        "AI: image_make submits the image request and sleeps; the mcp"
        " line's reply waits for the wake."
    )
    png = pattern_make()
    image_reply = t.exchange(
        "AI",
        "SCRIPT",
        "http.request",
        {
            "method": "POST",
            "url": f"{_BASE_URL}/images/generations",
            "headers": {
                "authorization": f"Bearer {_PROVIDER_KEY}",
                "content-type": "application/json",
            },
            "json": {
                "model": "grok-2-image",
                "prompt": _IMAGE_PROMPT,
                "n": 1,
                "response_format": "b64_json",
            },
        },
        {
            "status": 200,
            "headers": {"content-type": "application/json"},
            "json": {"data": [{"b64_json": base64.b64encode(png).decode()}]},
        },
    )
    tool_state: dict[str, object] = {"call": i, "key": _IMAGE_KEY}
    t.wake("AI", "tools.image_reply", tool_state, [image_reply])
    t.note(
        "AI: the bytes are decoded in the worker, written to _files, which"
        " forwards them, and posted to the UI with the buffer transferred."
    )
    seq["_files"] = kv_forward(t, _IMAGE_KEY, png, seq["_files"])
    media_reply = t.exchange(
        "AI",
        "UI",
        "media.store",
        {"k": _IMAGE_KEY},
        {"k": _IMAGE_KEY, "size": len(png), "sha256": sha256_hex(png)},
        blobs=[(png, {})],
    )
    t.wake("AI", "tools.media_reply", tool_state, [media_reply])
    image_result = {
        "key": _IMAGE_KEY,
        "size": len(png),
        "sha256": sha256_hex(png),
    }
    reply = tool_result(t, i, image_result)
    t.wake("AI", "ai.tool_reply", state, [reply])
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_2",
            "content": json_text(image_result),
        }
    )
    scene_doc: dict[str, object] = {
        "0": {"t": "scene"},
        "1": _IMAGE_KEY,
        "subtitle": _SUBTITLE,
        "image": {"$ref": 1},
    }
    doc_args = {"db": _REGION, "id": _SCENE_ID, "body": scene_doc}
    enter_args = {"ref": f"/{_WORLD}/scene", "text": _SCENE_REF}
    render_args = {"image": _IMAGE_KEY, "subtitle": _SUBTITLE}
    assistant = chat_exchange(
        t,
        state,
        messages,
        None,
        [
            tool_call("call_3", "browser.doc_put", doc_args),
            tool_call("call_4", "browser.kv_put", enter_args),
            tool_call("call_5", "browser.render", render_args),
        ],
    )
    messages.append(assistant)
    seq["metaverse"] = turn_forward(
        t, _HYPERPOSITION, assistant, seq["metaverse"]
    )
    t.note(
        "AI: three tool calls, submitted together; the agent sleeps on all"
        " three ids. The MCP server handles each as its own task."
    )
    doc_i = tool_request(t, "browser.doc_put", doc_args)
    enter_i = tool_request(t, "browser.kv_put", enter_args)
    render_i = tool_request(t, "browser.render", render_args)
    t.exchange(
        "AI",
        "SERVER",
        "doc.put",
        {"db": _REGION, "id": _SCENE_ID, "body": scene_doc, "since": 0},
        {"ref": _SCENE_REF, "seq": 1},
    )
    seq[_REGION] = 1
    doc_reply = tool_result(t, doc_i, {"ref": _SCENE_REF})
    seq[_WORLD] = kv_forward(
        t, f"/{_WORLD}/scene", _SCENE_REF.encode(), seq[_WORLD]
    )
    enter_reply = tool_result(
        t,
        enter_i,
        {"sha256": sha256_hex(_SCENE_REF.encode()), "seq": seq[_WORLD]},
    )
    t.note("AI: render sleeps until the UI has painted.")
    render_reply = t.exchange(
        "AI",
        "UI",
        "render",
        {"scene": _SCENE_REF, "subtitle": _SUBTITLE, "image": _IMAGE_KEY},
        {},
    )
    t.wake("AI", "tools.render_reply", {"call": render_i}, [render_reply])
    render_result = tool_result(t, render_i, {})
    t.wake(
        "AI", "ai.tool_reply", state, [doc_reply, enter_reply, render_result]
    )
    for call, result in (
        ("call_3", {"ref": _SCENE_REF}),
        ("call_4", {"seq": seq[_WORLD]}),
        ("call_5", {}),
    ):
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call,
                "content": json_text(result),
            }
        )
    assistant = chat_exchange(t, state, messages, _SUBTITLE, [])
    seq["metaverse"] = turn_forward(
        t, _HYPERPOSITION, assistant, seq["metaverse"]
    )
    turn_end = t.reply(
        "AI",
        "UI",
        say,
        "ai.say",
        {
            "turn": seq["metaverse"] - _METAVERSE_SEQ,
            "scene": _SCENE_REF,
            "subtitle": _SUBTITLE,
        },
    )
    t.wake("UI", "ui.turn_end", {"input": "enabled"}, [turn_end])
    return t.write()


def console_write() -> str:
    t = Transcript(
        "03_console",
        "The console on tty 0, debug mode: full header names; the user"
        " opens it, then the AI runs a command through it after Accept.",
        True,
    )
    first = b'{"AuthToken":"","columns":120,"rows":40}'
    opened = t.request("UI", "AI", "console.open", {})
    t.raw(
        "AI",
        "TTYD",
        "GET /ws?arg=console HTTP/1.1 Upgrade: websocket"
        " Sec-WebSocket-Protocol: tty",
    )
    t.raw("TTYD", "AI", "101 Switching Protocols Sec-WebSocket-Protocol: tty")
    t.note(
        "ttyd runs python3 bootstrap.py --root ... console, which runs dash"
        " through verbose.call because the setting debug is true."
    )
    t.reply("AI", "UI", opened, "console.open", {})
    t.note(
        "UI: console_view sends ttyd's first message; the AI worker's"
        " console port relays each message as it is, both ways."
    )
    t.notify("UI", "AI", "console.input", {}, [(first, {})])
    t.raw("AI", "TTYD", first.decode())
    for message in (
        f"1python3 {_BOOTSTRAP} --root {_ROOT} console (xt)",
        "2{}",
        "0$ ",
    ):
        t.raw("TTYD", "AI", message)
        t.notify("AI", "UI", "console.output", {}, [(message.encode(), {})])
    t.note("The AI runs a command: the permit flow, then the console port.")
    call_args = {"text": "echo hi", "timeout_seconds": 5}
    call = tool_request(t, "browser.console_run", call_args)
    ask = t.request(
        "AI",
        "UI",
        "permit.ask",
        {"permit": 1, "tool": "browser.console_run", "input": call_args},
    )
    t.note(
        "UI: the handler shows Accept, Deny and Always Allow and sleeps on"
        " the DOM port, which answers when a button is clicked."
    )
    choice = t.exchange(
        "UI",
        "DOM",
        "dom.choice",
        {"permit": 1, "choices": ["accept", "deny", "always"]},
        {"choice": "accept"},
    )
    t.wake("UI", "ui.permit_reply", {"ask": ask}, [choice])
    answer = t.reply(
        "UI", "AI", ask, "permit.ask", {"permit": 1, "choice": "accept"}
    )
    t.wake("AI", "tools.permit_reply", {"call": call}, [answer])
    t.notify("AI", "CONSOLE", "console.input", {}, [(b"0echo hi\n", {})])
    read = t.request(
        "AI",
        "CONSOLE",
        "console.read",
        {"until": "$ ", "timeout_seconds": 5},
    )
    t.raw("AI", "TTYD", "0echo hi\\n")
    output = "0echo hi\r\nhi\r\n$ "
    t.raw("TTYD", "AI", output.replace("\r\n", "\\r\\n"))
    t.notify("AI", "UI", "console.output", {}, [(output.encode(), {})])
    read_reply = t.reply(
        "CONSOLE",
        "AI",
        read,
        "console.read",
        {"text": "echo hi\r\nhi\r\n$ ", "timed_out": False},
    )
    t.wake("AI", "tools.console_reply", {"call": call}, [read_reply])
    result = tool_result(t, call, {"output": "hi\n", "timed_out": False})
    t.wake("AI", "ai.tool_reply", {"say": 1}, [result])
    closed = t.request("UI", "AI", "console.close", {})
    t.raw("AI", "TTYD", "close 1000")
    t.reply("AI", "UI", closed, "console.close", {})
    t.raw("TTYD", "AI", "closed 1000")
    t.notify("AI", "UI", "console.exit", {"code": 1000})
    return t.write()


def fault_write() -> str:
    t = Transcript(
        "04_fault_reload",
        "A handler fault: the one error line, the exit, the close, the"
        " overlay, Reload.",
        False,
    )
    call = tool_request(t, "browser.kv_get", {"ref": "/metaverse/nothing"})
    t.note(
        "AI: the browser lacks the key, so the store asks the server for it"
        " before failing."
    )
    i = t.request("AI", "SERVER", "kv.get", {}, k="/metaverse/nothing")
    stack = (
        "Traceback (most recent call last):\n"
        f'  File "{_ROOT}/main_loop.py", line 88, in loop_run\n'
        "    reply = dispatch.line_dispatch(line)\n"
        f'  File "{_ROOT}/engine_kv.py", line 14, in kv_get\n'
        "    value = store.kv_get(ref)\n"
        "KeyError: '/metaverse/nothing'"
    )
    t.reply(
        "SERVER",
        "AI",
        i,
        "error",
        {"message": "kv_get: /metaverse/nothing: no such key", "stack": stack},
    )
    t.note("server: exit 1. ttyd ends the connection without a close frame.")
    t.raw("TTYD", "AI", "closed 1006")
    t.note(
        "AI: the wire port saw the error line before the close, so the fault"
        " carries it; without one the fault would name the code alone."
    )
    t.notify(
        "AI",
        "UI",
        "fault",
        {
            "thread": "server",
            "message": "kv_get: /metaverse/nothing: no such key",
            "stack": stack,
        },
    )
    t.note(
        f"UI: error_overlay replaces the screen; the mcp request {call} is"
        " never answered. The user presses Reload: location.reload()."
    )
    t.raw("BROWSER", "TTYD", "GET / HTTP/1.1")
    t.raw("TTYD", "BROWSER", f"200 text/html sha256 {_PAGE_SHA256}")
    seq = server_seq()
    connection_open(t, _PID_AGAIN, seq)
    t.note(
        "AI: every seq equals the server's, so no database is replaced;"
        " boot continues as 01_boot."
    )
    return t.write()


def sync_write() -> str:
    t = Transcript(
        "05_sync",
        "Replication: a modification from the UI thread, a value over"
        " overflow_bytes, a desync and the reload that follows.",
        False,
    )
    update = [
        {
            "sql": "UPDATE world SET title = ? WHERE name = ?",
            "params": ["The castle at dusk", _WORLD],
        }
    ]
    t.note(
        "UI: a task the UI submits; the AI thread owns the database, runs it"
        " there, commits, and the substrate forwards the same line with since."
    )
    i = t.request(
        "UI", "AI", "sql.run", {"db": _UNIVERSE, "statements": update}
    )
    seq = {_UNIVERSE: 1, "_files": 2}
    seq[_UNIVERSE] = sql_forward(t, _UNIVERSE, update, [_ONE_CHANGE], 1)
    t.reply(
        "AI",
        "UI",
        i,
        "sql.run",
        {"results": [_ONE_CHANGE], "seq": seq[_UNIVERSE]},
    )
    t.note(
        "A script's kv_put of 204800 bytes: over overflow_bytes, so the"
        " server's decoder streams the blob to <root>/cache/<sha256> and"
        " kv_put renames it into place."
    )
    big = bytes(range(256)) * 800
    seq["_files"] = kv_forward(
        t, "/_files/maps/castle.bin", big, seq["_files"]
    )
    t.note(
        "Desync: an external MCP stdio client wrote to _files meanwhile, so"
        " the server's seq is one ahead of the browser's."
    )
    i = t.request(
        "AI",
        "SERVER",
        "kv.put",
        {"since": seq["_files"]},
        [(_STEP_SCRIPT.encode(), {})],
        k="/_files/script/step_tide.js",
    )
    since = seq["_files"]
    message = f"kv.put: since {since} is not seq {since + 1} of _files"
    stack = (
        "Traceback (most recent call last):\n"
        f'  File "{_ROOT}/main_loop.py", line 88, in loop_run\n'
        "    reply = dispatch.line_dispatch(line)\n"
        f'  File "{_ROOT}/engine_kv.py", line 22, in kv_put\n'
        '    seq = store.operation_apply("kv.put", since, **payload)\n'
        f"RuntimeError: {message}"
    )
    t.reply("SERVER", "AI", i, "error", {"message": message, "stack": stack})
    t.raw("TTYD", "AI", "closed 1006")
    t.notify(
        "AI",
        "UI",
        "fault",
        {"thread": "server", "message": message, "stack": stack},
    )
    t.note("UI: Reload. At the hello the browser's _files seq differs.")
    t.raw("BROWSER", "TTYD", "GET / HTTP/1.1")
    server = server_seq()
    server["_files"] = seq["_files"] + 1
    server[_UNIVERSE] = seq[_UNIVERSE]
    connection_open(t, _PID_AGAIN, server)
    browser = dict(server)
    browser["_files"] = seq["_files"]
    databases_replace(t, server, browser)
    return t.write()


def tap_write() -> str:
    t = Transcript(
        "06_tap",
        "A browser test run: each TAP line as its own line, appended by the"
        " server to <root>/tap/typescript.tap unbuffered.",
        False,
    )
    for text in _TAP_LINES:
        t.notify(
            "AI",
            "SERVER",
            "tap.line",
            {"language": "typescript", "text": text},
        )
    t.note(
        "test_browser.py reads the file once the run ends or its timer"
        " expires, and checks it with tap.consumer."
    )
    return t.write()


def stdio_write() -> str:
    t = Transcript(
        "07_mcp_stdio",
        "An external agent drives the server's MCP tools over stdio: one"
        " JSON-RPC message per line on stdin and stdout.",
        False,
    )
    _, server_tools = tools_load()
    t.raw(
        "CLIENT",
        "STDIO",
        json_text(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "external-agent", "version": "0"},
                },
            }
        ),
    )
    t.raw(
        "STDIO",
        "CLIENT",
        json_text(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "xsjs-server", "version": "0"},
                },
            }
        ),
    )
    t.raw(
        "CLIENT",
        "STDIO",
        json_text({"jsonrpc": "2.0", "method": "notifications/initialized"}),
    )
    t.raw(
        "CLIENT",
        "STDIO",
        json_text({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    )
    t.raw(
        "STDIO",
        "CLIENT",
        json_text(
            {"jsonrpc": "2.0", "id": 2, "result": {"tools": server_tools}}
        ),
    )
    t.raw(
        "CLIENT",
        "STDIO",
        json_text({"jsonrpc": "2.0", "id": 3, "method": "ping"}),
    )
    t.raw(
        "STDIO", "CLIENT", json_text({"jsonrpc": "2.0", "id": 3, "result": {}})
    )
    t.note(
        "A permit tool over stdio has no UI to ask: tools/call of one"
        " answers a JSON-RPC error."
    )
    t.raw(
        "CLIENT",
        "STDIO",
        json_text(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "system_restart",
                    "arguments": {"main_loop": "main_loop.py"},
                },
            }
        ),
    )
    t.raw(
        "STDIO",
        "CLIENT",
        json_text(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "error": {
                    "code": -32000,
                    "message": "system_restart needs a permit and stdio has"
                    " no UI to ask",
                },
            }
        ),
    )
    return t.write()


def script_write() -> str:
    t = Transcript(
        "08_script",
        "The AI edits a script, runs it, and debugs it; each is a tool call"
        " and each commit is forwarded.",
        False,
    )
    seq = {"_files": 4, _WORLD: 2}
    script = _STEP_SCRIPT.encode()
    i = tool_request(
        t,
        "browser.kv_put",
        {"ref": "/_files/script/step_tide.js", "text": _STEP_SCRIPT},
    )
    seq["_files"] = kv_forward(
        t, "/_files/script/step_tide.js", script, seq["_files"]
    )
    tool_result(t, i, {"sha256": sha256_hex(script), "seq": seq["_files"]})
    update = [
        {
            "sql": "UPDATE region SET tide = tide + ? WHERE name = ?",
            "params": [1, _REGION],
        }
    ]
    i = tool_request(
        t, "browser.script_run", {"name": "step_tide", "args": {"hours": 1}}
    )
    t.note("AI: the script runs inside the task; its commit is forwarded.")
    seq[_WORLD] = sql_forward(t, _WORLD, update, [_ONE_CHANGE], seq[_WORLD])
    tool_result(
        t,
        i,
        {
            "value": {"changes": 1},
            "lines": [
                {"at": 1760800000000, "level": 1, "text": "tide advanced by 1"}
            ],
        },
    )
    i = tool_request(
        t, "browser.script_debug", {"name": "step_tide", "args": {"hours": 1}}
    )
    t.note("AI: the same run at verbose level 2 traces every substrate call.")
    seq[_WORLD] = sql_forward(t, _WORLD, update, [_ONE_CHANGE], seq[_WORLD])
    tool_result(
        t,
        i,
        {
            "value": {"changes": 1},
            "lines": [
                {
                    "at": 1760800001000,
                    "level": 2,
                    "text": "substrate sql_run castle_world 1 statement",
                },
                {
                    "at": 1760800001001,
                    "level": 1,
                    "text": "tide advanced by 1",
                },
                {
                    "at": 1760800001002,
                    "level": 2,
                    "text": "forward sql.run castle_world since"
                    f" {seq[_WORLD] - 1}",
                },
            ],
        },
    )
    return t.write()


def main() -> int:
    for path in (
        boot_write(),
        turn_write(),
        console_write(),
        fault_write(),
        sync_write(),
        tap_write(),
        stdio_write(),
        script_write(),
    ):
        print(os.path.relpath(path, os.path.dirname(_DATA_PATH)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
