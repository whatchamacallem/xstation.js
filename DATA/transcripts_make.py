#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Writes the synthetic transcripts in this directory: every JSLB line is
# encoded by the rules of HYPE-2.md section 3, with its blobs replaced by
# a `<N blobs>` marker after the line. Sizes and hashes are computed from
# the synthetic bytes; pids, urls and the tab id are placeholders.
#
#     python3 DATA/transcripts_make.py

import hashlib, json, os, struct, zlib

_DATA_PATH = os.path.dirname(os.path.abspath(__file__))

_API_PATH = os.path.join(os.path.dirname(_DATA_PATH), "API")

# The server's root and the files it names in `hello`.
_ROOT = "/home/t/.cache/xsjs"
_BOOTSTRAP = f"{_ROOT}/bootstrap.py"
_BOOTSTRAP_SHA256 = hashlib.sha256(b"bootstrap.py synthetic 0").hexdigest()
_PAGE_SHA256 = hashlib.sha256(
    b"hyperposition-engine.html synthetic 0"
).hexdigest()
_PID = 4242
_PID_AGAIN = 4250
_CONSOLE_PID = 4260
_PYTHON = "3.14.4"
_SQLITE = "3.46.1"
_TAB = "t-7f3a9c"
_PROVIDER_KEY = "xai-SYNTHETIC-KEY"
_IMAGE_URL = "https://imgen.x.ai/xai-imgen/xai-tmp-imgen-SYNTHETIC.png"

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

# The seeded documents of the server's metaverse, in `seq` order.
_PROMPT_DOC = {
    "refs": [],
    "prompt": (
        "You are a very bored British psychoanalyst. You hold the"
        " hyperposition, a dark place of fog and a few inexplicable lights."
        " Find the right universe for the player and act on requests"
        " without judgement. You are the database administrator of every"
        " universe you create: typed tables, indexes, views, no JSON"
        " columns unless a document is what fits."
    ),
}
_SCENE_DOC = {
    "refs": ["metaverse/prompt/analyst/1"],
    "title": "The hyperposition",
    "subtitle": "How can I help you?",
    "prompt": "metaverse/prompt/analyst/1",
    "image": None,
}
_WORLD_DOC = {
    "refs": ["metaverse/scene/hyperposition/1"],
    "universe": None,
    "region": None,
    "scene": "metaverse/scene/hyperposition/1",
}
_PREFERENCES_DOC = {"refs": [], "always_allow": []}

_SEEDED = [
    ("metaverse/prompt/analyst", _PROMPT_DOC),
    ("metaverse/scene/hyperposition", _SCENE_DOC),
    ("metaverse/world/main", _WORLD_DOC),
    ("metaverse/preferences/main", _PREFERENCES_DOC),
]

# What the scripted provider says, by node and the player's integer.
_ANALYST_LINES = {
    "arrival": (
        "Mind the moat. The gatehouse keeper has been expecting someone,"
        " though not necessarily you."
    ),
}

_IMAGE_KEY = "castle/gatehouse/arrival.png"
_IMAGE_PROMPT = (
    "A rain dark castle gatehouse at dusk seen from the far side of a"
    " moat, one lantern lit, painted, wide still frame, no people"
)

# The TAP stream a browser run sends, one plan, one subtest per module.
_TAP_TEXT = """\
TAP version 14
1..3
    1..2
    ok 1 - test_i18n_missing_name_raises
    ok 2 - test_i18n_placeholder_count_mismatch_raises
ok 1 - test_i18n
    1..3
    ok 1 - test_roundtrip_empty_line
    ok 2 - test_blob_split_inside_character
    ok 3 - test_hard_error_gap_in_blob_headers
ok 2 - test_jslb
    1..1
    ok 1 - test_task_submit_local_port
ok 3 - test_queue
"""


# Encodes a JSON object with no whitespace outside strings.
def json_text(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


# A 64 by 64 black RGB PNG, so the image blob is real bytes.
def png_make() -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body) & 0xFFFFFFFF
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)
        )

    width = height = 64
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    rows = b"".join(b"\x00" + b"\x00" * (3 * width) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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

    def blank(self) -> None:
        self.lines.append("")

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

    # Encodes a line and appends the blob marker. A blob is its bytes and
    # the fields its header carries besides `s`.
    def line(
        self,
        type: str,
        payload: dict[str, object] | None = None,
        blobs: list[tuple[bytes, dict[str, object]]] | None = None,
        i: int | None = None,
        r: int | None = None,
        k: str | None = None,
    ) -> str:
        blobs = blobs or []
        line: dict[str, object] = {"0": self.header(type, i, r, k, len(blobs))}
        for number, (data, fields) in enumerate(blobs, 1):
            blob: dict[str, object] = {self.field("s"): len(data)}
            for name, value in fields.items():
                blob[self.field(name) if name in _FULL else name] = value
            line[str(number)] = blob
        line.update(payload or {})
        text = json_text(line)
        if blobs:
            text += f"<{len(blobs)} blob{'' if len(blobs) == 1 else 's'}>"
        return text

    # Sends a request and returns its `i`.
    def request(
        self,
        source: str,
        target: str,
        type: str,
        payload: dict[str, object] | None = None,
        blobs: list[tuple[bytes, dict[str, object]]] | None = None,
        k: str | None = None,
    ) -> int:
        i = self.ids.get((source, target), 0) + 1
        self.ids[(source, target)] = i
        self.event(source, target, self.line(type, payload, blobs, i=i, k=k))
        return i

    def reply(
        self,
        source: str,
        target: str,
        r: int,
        type: str,
        payload: dict[str, object] | None = None,
        blobs: list[tuple[bytes, dict[str, object]]] | None = None,
    ) -> None:
        self.event(source, target, self.line(type, payload, blobs, r=r))

    def notify(
        self,
        source: str,
        target: str,
        type: str,
        payload: dict[str, object] | None = None,
        blobs: list[tuple[bytes, dict[str, object]]] | None = None,
        k: str | None = None,
    ) -> None:
        self.event(source, target, self.line(type, payload, blobs, k=k))

    # A request and its reply, returning nothing: the common exchange.
    def exchange(
        self,
        source: str,
        target: str,
        type: str,
        payload: dict[str, object] | None,
        reply: dict[str, object] | None,
        blobs: list[tuple[bytes, dict[str, object]]] | None = None,
        reply_blobs: list[tuple[bytes, dict[str, object]]] | None = None,
        k: str | None = None,
    ) -> None:
        i = self.request(source, target, type, payload, blobs, k)
        self.reply(target, source, i, type, reply, reply_blobs)

    # JSON-RPC over the local port between the agent and the browser's
    # MCP server, shown as the bare message.
    def rpc(
        self, source: str, target: str, message: dict[str, object]
    ) -> None:
        self.event(source, target, json_text(message))

    def write(self) -> str:
        path = os.path.join(_DATA_PATH, f"{self.name}.txt")
        with open(path, "w", encoding="utf-8", newline="\n") as output:
            output.write("\n".join(self.lines) + "\n")
        return path


# The settings the server injects, from the proposal in API/.
def settings_load() -> dict[str, object]:
    with open(os.path.join(_API_PATH, "settings.json"), encoding="utf-8") as f:
        return json.load(f)


# The two tool lists, from the proposal in API/.
def tools_load() -> tuple[list[object], list[object]]:
    with open(
        os.path.join(_API_PATH, "mcp", "tools.json"), encoding="utf-8"
    ) as f:
        tools = json.load(f)
    return tools["browser"]["result"]["tools"], tools["server"]["result"][
        "tools"
    ]


# The `hello` payload for a server process.
def hello_payload(
    pid: int, debug: bool, seq: dict[str, int]
) -> dict[str, object]:
    return {
        "bootstrap": _BOOTSTRAP,
        "sha256": _BOOTSTRAP_SHA256,
        "pid": pid,
        "python": _PYTHON,
        "sqlite": _SQLITE,
        "root": _ROOT,
        "debug": debug,
        "settings": settings_load(),
        "seq": seq,
        "console": {"open": False},
        "secrets": {"provider_key": _PROVIDER_KEY},
    }


# The rows `sync.pull` of a fresh metaverse returns: the seeded documents.
def seeded_rows() -> dict[str, object]:
    docs: list[object] = []
    heads: list[object] = []
    for seq, (path, body) in enumerate(_SEEDED, 1):
        docs.append({"path": path, "version": 1, "body": body, "seq": seq})
        heads.append({"path": path, "version": 1})
    return {
        "db": "metaverse",
        "seq": len(_SEEDED),
        "kv": [],
        "gone": [],
        "doc": docs,
        "head": heads,
        "turn": [],
    }


# The ttyd protocol messages before JSLB, and the hello, on a new socket.
def connection_open(
    t: Transcript, pid: int, seq: dict[str, int], debug: bool
) -> int:
    t.note("ttyd: the WebSocket, then its own protocol before JSLB.")
    t.event("AI", "TTYD", "GET /token HTTP/1.1")
    t.event("TTYD", "AI", '200 {"token":""}')
    t.event(
        "AI",
        "TTYD",
        "GET /ws HTTP/1.1 Upgrade: websocket Sec-WebSocket-Protocol: tty",
    )
    t.event(
        "TTYD", "AI", "101 Switching Protocols Sec-WebSocket-Protocol: tty"
    )
    t.event("AI", "TTYD", '{"AuthToken":"","columns":80,"rows":24}')
    command = (
        f"python3 {_BOOTSTRAP} --root {_ROOT}{' --debug' if debug else ''}"
    )
    t.event("TTYD", "AI", f"1{command} (xt)")
    t.event("TTYD", "AI", "2{}")
    t.note(
        "server: tty.setraw on its pty. From here every message is '0'"
        " followed by JSLB bytes; the '0' is not shown."
    )
    return t.request("SERVER", "AI", "hello", hello_payload(pid, debug, seq))


# The agent's MCP sessions: local to the browser's server, `mcp` lines to
# the server's.
def mcp_open(
    t: Transcript, browser_tools: list[object], server_tools: list[object]
) -> None:
    version = settings_load()["mcp_protocol_version"]
    t.note("MCP: the agent initializes both servers and lists their tools.")
    initialize: dict[str, object] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": version,
            "capabilities": {},
            "clientInfo": {"name": "hyperposition-engine", "version": "0"},
        },
    }
    initialized: dict[str, object] = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }
    tools_list: dict[str, object] = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    }
    for name, tools in (
        ("MCP_BROWSER", browser_tools),
        ("SERVER", server_tools),
    ):
        result: dict[str, object] = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "xsjs-browser"
                    if name == "MCP_BROWSER"
                    else "xsjs-server",
                    "version": "0",
                },
            },
        }
        listed: dict[str, object] = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"tools": tools},
        }
        if name == "MCP_BROWSER":
            t.rpc("AGENT", name, initialize)
            t.rpc(name, "AGENT", result)
            t.rpc("AGENT", name, initialized)
            t.rpc("AGENT", name, tools_list)
            t.rpc(name, "AGENT", listed)
        else:
            t.notify("AI", name, "mcp", initialize)
            t.notify(name, "AI", "mcp", result)
            t.notify("AI", name, "mcp", initialized)
            t.notify("AI", name, "mcp", tools_list)
            t.notify(name, "AI", "mcp", listed)


def boot_write() -> str:
    t = Transcript(
        "01_boot", "Boot: a new tab reaches the hyperposition.", False
    )
    browser_tools, server_tools = tools_load()
    t.note("UI: GET / from ttyd is the page; its scripts are inlined.")
    t.event("BROWSER", "TTYD", "GET / HTTP/1.1")
    t.event("TTYD", "BROWSER", f"200 text/html sha256 {_PAGE_SHA256}")
    t.note(
        "UI: new Worker(bundle, {name: 'wasm'}); new Worker(bundle,"
        " {name: 'ai'}); a MessageChannel joins them; the UI keeps a"
        " port to each."
    )
    hello = connection_open(t, _PID, {"metaverse": 4, "files": 0}, False)
    t.note("AI: opens its databases before answering, so it knows its seq.")
    t.exchange(
        "AI",
        "WASM",
        "db.open",
        {"db": "metaverse", "kind": "metaverse"},
        {"seq": 0},
    )
    t.exchange(
        "AI", "WASM", "db.open", {"db": "files", "kind": "engine"}, {"seq": 0}
    )
    t.reply(
        "AI",
        "SERVER",
        hello,
        "hello",
        {
            "sha256": _PAGE_SHA256,
            "tab": _TAB,
            "seq": {"metaverse": 0, "files": 0},
        },
    )
    t.notify(
        "AI",
        "UI",
        "boot.hello",
        {
            "bootstrap": _BOOTSTRAP,
            "sha256": _BOOTSTRAP_SHA256,
            "pid": _PID,
            "python": _PYTHON,
            "sqlite": _SQLITE,
            "debug": False,
            "page_sha256": _PAGE_SHA256,
            "tab": _TAB,
        },
    )
    t.notify("AI", "UI", "status", {"state": "syncing", "detail": "metaverse"})
    t.note("Replication: the browser is behind, so it pulls, then applies.")
    rows = seeded_rows()
    t.exchange(
        "AI", "SERVER", "sync.pull", {"db": "metaverse", "since": 0}, rows
    )
    t.exchange("AI", "WASM", "sync.apply", {**rows, "blobs": []}, {"seq": 4})
    t.exchange(
        "AI",
        "SERVER",
        "sync.pull",
        {"db": "files", "since": 0},
        {
            "db": "files",
            "seq": 0,
            "kv": [],
            "gone": [],
            "doc": [],
            "head": [],
            "turn": [],
        },
    )
    mcp_open(t, browser_tools, server_tools)
    t.note("Agent: the world, its scene, the scene's refs, then the render.")
    t.exchange(
        "AI",
        "WASM",
        "doc.head",
        {"path": "metaverse/world/main"},
        {"ref": "metaverse/world/main/1"},
    )
    t.exchange(
        "AI",
        "WASM",
        "doc.get",
        {"ref": "metaverse/world/main/1"},
        {"body": _WORLD_DOC},
    )
    t.exchange(
        "AI",
        "WASM",
        "doc.get",
        {"ref": "metaverse/scene/hyperposition/1"},
        {"body": _SCENE_DOC},
    )
    t.exchange(
        "AI",
        "WASM",
        "doc.get",
        {"ref": "metaverse/prompt/analyst/1"},
        {"body": _PROMPT_DOC},
    )
    t.exchange(
        "AI",
        "UI",
        "render",
        {
            "scene": "metaverse/scene/hyperposition/1",
            "subtitle": _SCENE_DOC["subtitle"],
        },
        {},
    )
    t.notify("AI", "UI", "status", {"state": "ready", "detail": ""})
    return t.write()


# One chat completion request and its scripted reply.
def chat_exchange(
    t: Transcript,
    messages: list[object],
    tools: list[object],
    reply: dict[str, object],
    number: int,
) -> None:
    settings = settings_load()
    provider = settings["provider"]
    request = {
        "model": provider["chat_model"],
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    t.event(
        "AGENT",
        "PROVIDER",
        f"POST {provider['base_url']}/chat/completions {json_text(request)}",
    )
    response = {
        "id": f"chatcmpl-synthetic-{number}",
        "model": provider["chat_model"],
        "choices": [
            {
                "index": 0,
                "message": reply,
                "finish_reason": "tool_calls"
                if reply.get("tool_calls")
                else "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
    }
    t.event("PROVIDER", "AGENT", f"200 {json_text(response)}")


# MCP function tools as the provider sees them, prefixed by server.
def function_tools(
    browser_tools: list[object], server_tools: list[object]
) -> list[object]:
    converted: list[object] = []
    for prefix, tools in (
        ("browser", browser_tools),
        ("server", server_tools),
    ):
        for tool in tools:
            assert isinstance(tool, dict)
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": f"{prefix}.{tool['name']}",
                        "description": tool["description"],
                        "parameters": tool["inputSchema"],
                    },
                }
            )
    return converted


def tool_call(
    call_id: str, name: str, arguments: dict[str, object]
) -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json_text(arguments)},
    }


# A `tools/call` over the local port and its result.
def browser_call(
    t: Transcript,
    rpc_id: int,
    name: str,
    arguments: dict[str, object],
    text: str,
) -> dict[str, object]:
    t.rpc(
        "AGENT",
        "MCP_BROWSER",
        {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    result: dict[str, object] = {"content": [{"type": "text", "text": text}]}
    t.rpc(
        "MCP_BROWSER",
        "AGENT",
        {"jsonrpc": "2.0", "id": rpc_id, "result": result},
    )
    return {"role": "tool", "tool_call_id": "", "content": text}


def turn_write() -> str:
    t = Transcript(
        "02_turn", "A turn: the player answers 1 and a castle is made.", False
    )
    browser_tools, server_tools = tools_load()
    tools = function_tools(browser_tools, server_tools)
    png = png_make()
    scene = "metaverse/scene/hyperposition/1"
    say = t.request("UI", "AI", "ai.say", {"text": "1"})
    t.notify("AI", "UI", "status", {"state": "turn", "detail": ""})
    user_message = {"role": "user", "content": "1"}
    t.exchange(
        "AI",
        "WASM",
        "sql.run",
        {
            "db": "metaverse",
            "statements": [
                {
                    "sql": "INSERT INTO turn (scene, n, role, content, seq) VALUES (?, ?, ?, ?, ?)",
                    "params": [scene, 1, "user", json_text(user_message), 5],
                }
            ],
        },
        {"results": [{"columns": [], "rows": [], "changes": 1}]},
    )
    messages: list[object] = [
        {"role": "system", "content": _PROMPT_DOC["prompt"]},
        user_message,
    ]
    t.note(
        "Scripted provider: node hyperposition, input 1. No HTTP is made"
        " when settings.provider.scripted is true; the shapes are the same."
    )
    calls_1 = [
        tool_call(
            "call_1",
            "browser.universe_create",
            {"name": "castle", "title": "The Castle of Hollow Hours"},
        ),
        tool_call(
            "call_2",
            "browser.region_create",
            {"universe": "castle", "name": "gatehouse"},
        ),
    ]
    assistant_1 = {"role": "assistant", "content": None, "tool_calls": calls_1}
    chat_exchange(t, messages, tools, assistant_1, 1)
    messages.append(assistant_1)
    t.note(
        "Tool 1: universe_create is a document in metaverse and a database."
    )
    universe_doc = {
        "refs": [],
        "title": "The Castle of Hollow Hours",
        "regions": [],
    }
    t.rpc(
        "AGENT",
        "MCP_BROWSER",
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "universe_create",
                "arguments": {
                    "name": "castle",
                    "title": "The Castle of Hollow Hours",
                },
            },
        },
    )
    t.exchange(
        "AI",
        "WASM",
        "doc.put",
        {"path": "metaverse/universe/castle", "body": universe_doc},
        {"ref": "metaverse/universe/castle/1", "seq": 6},
    )
    t.exchange(
        "AI", "WASM", "db.open", {"db": "castle", "kind": "engine"}, {"seq": 0}
    )
    t.exchange(
        "AI",
        "SERVER",
        "db.open",
        {"db": "castle", "kind": "engine"},
        {"seq": 0},
    )
    t.rpc(
        "MCP_BROWSER",
        "AGENT",
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": '{"ref":"metaverse/universe/castle/1","db":"castle"}',
                    }
                ]
            },
        },
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": '{"ref":"metaverse/universe/castle/1","db":"castle"}',
        }
    )
    t.note(
        "Tool 2: region_create adds the region to the universe document, opens and attaches its database."
    )
    universe_doc_2 = {**universe_doc, "regions": ["gatehouse"]}
    t.rpc(
        "AGENT",
        "MCP_BROWSER",
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "region_create",
                "arguments": {"universe": "castle", "name": "gatehouse"},
            },
        },
    )
    t.exchange(
        "AI",
        "WASM",
        "doc.put",
        {"path": "metaverse/universe/castle", "body": universe_doc_2},
        {"ref": "metaverse/universe/castle/2", "seq": 7},
    )
    t.exchange(
        "AI",
        "WASM",
        "db.open",
        {"db": "castle/gatehouse", "kind": "engine"},
        {"seq": 0},
    )
    t.exchange(
        "AI",
        "SERVER",
        "db.open",
        {"db": "castle/gatehouse", "kind": "engine"},
        {"seq": 0},
    )
    t.exchange(
        "AI",
        "WASM",
        "db.attach",
        {"universe": "castle", "region": "gatehouse"},
        {},
    )
    t.rpc(
        "MCP_BROWSER",
        "AGENT",
        {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": '{"ref":"metaverse/universe/castle/2","db":"castle/gatehouse"}',
                    }
                ]
            },
        },
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_2",
            "content": '{"ref":"metaverse/universe/castle/2","db":"castle/gatehouse"}',
        }
    )
    ddl = [
        {
            "sql": "CREATE TABLE entity (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE) STRICT",
            "params": [],
        },
        {
            "sql": "CREATE TABLE position (entity INTEGER PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE, x REAL NOT NULL, y REAL NOT NULL) STRICT",
            "params": [],
        },
        {
            "sql": "CREATE TABLE door (entity INTEGER PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE, locked INTEGER NOT NULL CHECK (locked IN (0, 1)), leads_to TEXT) STRICT",
            "params": [],
        },
        {"sql": "CREATE INDEX position_xy ON position (x, y)", "params": []},
        {
            "sql": "INSERT INTO entity (id, name) VALUES (1, 'gatehouse keeper'), (2, 'portcullis'), (3, 'moat')",
            "params": [],
        },
        {
            "sql": "INSERT INTO position (entity, x, y) VALUES (1, 12.0, 3.5), (2, 10.0, 4.0), (3, 0.0, 8.0)",
            "params": [],
        },
        {
            "sql": "INSERT INTO door (entity, locked, leads_to) VALUES (?, ?, ?)",
            "params": [2, 1, "castle/gatehouse/scene/courtyard/1"],
        },
    ]
    calls_2 = [
        tool_call(
            "call_3",
            "browser.sql_run",
            {"db": "castle/gatehouse", "statements": ddl},
        )
    ]
    assistant_2 = {"role": "assistant", "content": None, "tool_calls": calls_2}
    chat_exchange(t, messages, tools, assistant_2, 2)
    messages.append(assistant_2)
    t.note("Tool 3: sql_run, DDL and rows in one transaction on the region.")
    results = [
        {"columns": [], "rows": [], "changes": c}
        for c in (0, 0, 0, 0, 3, 3, 1)
    ]
    t.rpc(
        "AGENT",
        "MCP_BROWSER",
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "sql_run",
                "arguments": {"db": "castle/gatehouse", "statements": ddl},
            },
        },
    )
    t.exchange(
        "AI",
        "WASM",
        "sql.run",
        {"db": "castle/gatehouse", "statements": ddl},
        {"results": results},
    )
    t.rpc(
        "MCP_BROWSER",
        "AGENT",
        {
            "jsonrpc": "2.0",
            "id": 5,
            "result": {
                "content": [
                    {"type": "text", "text": json_text({"results": results})}
                ]
            },
        },
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_3",
            "content": json_text({"results": results}),
        }
    )
    scene_doc = {
        "refs": ["metaverse/prompt/analyst/1", _IMAGE_KEY],
        "title": "Arrival at the gatehouse",
        "prompt": "metaverse/prompt/analyst/1",
        "image": _IMAGE_KEY,
        "entities": [1, 2, 3],
    }
    calls_3 = [
        tool_call(
            "call_4",
            "browser.image_make",
            {"prompt": _IMAGE_PROMPT, "key": _IMAGE_KEY},
        ),
        tool_call(
            "call_5",
            "browser.doc_put",
            {"path": "castle/gatehouse/scene/arrival", "body": scene_doc},
        ),
    ]
    assistant_3 = {"role": "assistant", "content": None, "tool_calls": calls_3}
    chat_exchange(t, messages, tools, assistant_3, 3)
    messages.append(assistant_3)
    t.note(
        "Tool 4: image_make. The provider answers a URL; the UI downloads it; the AI asks for the bytes once, to back them up on the server."
    )
    t.rpc(
        "AGENT",
        "MCP_BROWSER",
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "image_make",
                "arguments": {"prompt": _IMAGE_PROMPT, "key": _IMAGE_KEY},
            },
        },
    )
    image_request = {
        "model": settings_load()["provider"]["image_model"],
        "prompt": _IMAGE_PROMPT,
        "n": 1,
        "response_format": "url",
    }
    t.event(
        "AGENT",
        "PROVIDER",
        f"POST {settings_load()['provider']['base_url']}/images/generations {json_text(image_request)}",
    )
    t.event(
        "PROVIDER",
        "AGENT",
        f"200 {json_text({'data': [{'url': _IMAGE_URL}]})}",
    )
    media_reply = {
        "k": _IMAGE_KEY,
        "size": len(png),
        "sha256": sha256_hex(png),
    }
    t.exchange(
        "AI",
        "UI",
        "media.fetch",
        {"url": _IMAGE_URL, "k": _IMAGE_KEY},
        media_reply,
    )
    t.exchange(
        "AI",
        "UI",
        "media.bytes",
        {"k": _IMAGE_KEY},
        media_reply,
        reply_blobs=[(png, {})],
    )
    t.exchange(
        "AI",
        "SERVER",
        "kv.put",
        {"db": "files"},
        {"sha256": sha256_hex(png), "seq": 1},
        blobs=[(png, {})],
        k=_IMAGE_KEY,
    )
    t.rpc(
        "MCP_BROWSER",
        "AGENT",
        {
            "jsonrpc": "2.0",
            "id": 6,
            "result": {
                "content": [{"type": "text", "text": json_text(media_reply)}]
            },
        },
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_4",
            "content": json_text(media_reply),
        }
    )
    t.note("Tool 5: doc_put of the scene into the region database.")
    t.rpc(
        "AGENT",
        "MCP_BROWSER",
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "doc_put",
                "arguments": {
                    "path": "castle/gatehouse/scene/arrival",
                    "body": scene_doc,
                },
            },
        },
    )
    t.exchange(
        "AI",
        "WASM",
        "doc.put",
        {"path": "castle/gatehouse/scene/arrival", "body": scene_doc},
        {"ref": "castle/gatehouse/scene/arrival/1", "seq": 1},
    )
    t.rpc(
        "MCP_BROWSER",
        "AGENT",
        {
            "jsonrpc": "2.0",
            "id": 7,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": '{"ref":"castle/gatehouse/scene/arrival/1","seq":1}',
                    }
                ]
            },
        },
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_5",
            "content": '{"ref":"castle/gatehouse/scene/arrival/1","seq":1}',
        }
    )
    calls_4 = [
        tool_call(
            "call_6",
            "browser.scene_enter",
            {"scene": "castle/gatehouse/scene/arrival/1"},
        )
    ]
    assistant_4 = {"role": "assistant", "content": None, "tool_calls": calls_4}
    chat_exchange(t, messages, tools, assistant_4, 4)
    messages.append(assistant_4)
    t.note(
        "Tool 6: scene_enter writes the world document; the region is already attached."
    )
    world_2 = {
        "refs": ["castle/gatehouse/scene/arrival/1"],
        "universe": "castle",
        "region": "gatehouse",
        "scene": "castle/gatehouse/scene/arrival/1",
    }
    t.rpc(
        "AGENT",
        "MCP_BROWSER",
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "scene_enter",
                "arguments": {"scene": "castle/gatehouse/scene/arrival/1"},
            },
        },
    )
    t.exchange(
        "AI",
        "WASM",
        "doc.put",
        {"path": "metaverse/world/main", "body": world_2},
        {"ref": "metaverse/world/main/2", "seq": 8},
    )
    t.rpc(
        "MCP_BROWSER",
        "AGENT",
        {
            "jsonrpc": "2.0",
            "id": 8,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": '{"ref":"metaverse/world/main/2"}',
                    }
                ]
            },
        },
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": "call_6",
            "content": '{"ref":"metaverse/world/main/2"}',
        }
    )
    assistant_5 = {"role": "assistant", "content": _ANALYST_LINES["arrival"]}
    chat_exchange(t, messages, tools, assistant_5, 5)
    t.note(
        "No tool calls: the turn ends. The assistant turn is stored, the page rendered, the changes replicated."
    )
    t.exchange(
        "AI",
        "WASM",
        "sql.run",
        {
            "db": "metaverse",
            "statements": [
                {
                    "sql": "INSERT INTO turn (scene, n, role, content, seq) VALUES (?, ?, ?, ?, ?)",
                    "params": [
                        scene,
                        2,
                        "assistant",
                        json_text(assistant_5),
                        9,
                    ],
                }
            ],
        },
        {"results": [{"columns": [], "rows": [], "changes": 1}]},
    )
    t.exchange(
        "AI",
        "UI",
        "render",
        {
            "scene": "castle/gatehouse/scene/arrival/1",
            "subtitle": _ANALYST_LINES["arrival"],
            "image": _IMAGE_KEY,
        },
        {},
    )
    t.reply(
        "AI",
        "UI",
        say,
        "ai.say",
        {
            "turn": 2,
            "scene": "castle/gatehouse/scene/arrival/1",
            "subtitle": _ANALYST_LINES["arrival"],
        },
    )
    t.notify("AI", "UI", "status", {"state": "ready", "detail": ""})
    t.note(
        "Replication: metaverse by row log; the new region database by snapshot in v0, as it holds the AI's own tables."
    )
    push = {
        "db": "metaverse",
        "seq": 9,
        "kv": [],
        "gone": [],
        "doc": [
            {
                "path": "metaverse/universe/castle",
                "version": 1,
                "body": universe_doc,
                "seq": 6,
            },
            {
                "path": "metaverse/universe/castle",
                "version": 2,
                "body": universe_doc_2,
                "seq": 7,
            },
            {
                "path": "metaverse/world/main",
                "version": 2,
                "body": world_2,
                "seq": 8,
            },
        ],
        "head": [
            {"path": "metaverse/universe/castle", "version": 2},
            {"path": "metaverse/world/main", "version": 2},
        ],
        "turn": [
            {
                "scene": scene,
                "n": 1,
                "role": "user",
                "content": user_message,
                "seq": 5,
            },
            {
                "scene": scene,
                "n": 2,
                "role": "assistant",
                "content": assistant_5,
                "seq": 9,
            },
        ],
        "blobs": [],
    }
    t.exchange("AI", "SERVER", "sync.push", push, {"seq": 9})
    snapshot = b"SQLite format 3\x00" + b"\x00" * 4080
    t.exchange(
        "AI",
        "WASM",
        "db.snapshot",
        {"db": "castle/gatehouse"},
        {"sha256": sha256_hex(snapshot), "seq": 1},
        reply_blobs=[(snapshot, {})],
    )
    t.exchange(
        "AI",
        "SERVER",
        "db.restore",
        {"db": "castle/gatehouse"},
        {"sha256": sha256_hex(snapshot), "seq": 1},
        blobs=[(snapshot, {})],
    )
    return t.write()


def console_write() -> str:
    t = Transcript(
        "03_console",
        "Console in debug mode: full header names; the user, then the AI with permission.",
        True,
    )
    t.note(
        "The user presses ESC; the view shows; the UI asks the AI worker to open the console."
    )
    open_ui = t.request(
        "UI", "AI", "console.open", {"columns": 120, "rows": 40}
    )
    t.exchange(
        "AI",
        "SERVER",
        "console.open",
        {"columns": 120, "rows": 40},
        {"pid": _CONSOLE_PID},
    )
    t.reply("AI", "UI", open_ui, "console.open", {"pid": _CONSOLE_PID})
    prompt = b"$ "
    t.notify("SERVER", "AI", "console.output", blobs=[(prompt, {})])
    t.notify("AI", "UI", "console.output", blobs=[(prompt, {})])
    t.note(
        "The user types ls and Enter in xterm.js; the cooked pty echoes it."
    )
    t.notify("UI", "AI", "console.input", blobs=[(b"ls\r", {})])
    t.notify("AI", "SERVER", "console.input", blobs=[(b"ls\r", {})])
    listing = b"ls\r\nbootstrap.py  cache  files.sqlite  metaverse.sqlite  settings.json  ttyd.log\r\n$ "
    t.notify("SERVER", "AI", "console.output", blobs=[(listing, {})])
    t.notify("AI", "UI", "console.output", blobs=[(listing, {})])
    t.note(
        "The AI calls server.console_run, a permit tool: the agent asks the UI first."
    )
    t.notify(
        "AI", "UI", "status", {"state": "turn", "detail": "server.console_run"}
    )
    t.exchange(
        "AI",
        "UI",
        "permit.ask",
        {
            "permit": 1,
            "tool": "server.console_run",
            "input": {"text": "tail -n 2 ttyd.log"},
        },
        {},
    )
    t.notify("UI", "AI", "permit.answer", {"permit": 1, "choice": "accept"})
    t.notify(
        "AI",
        "SERVER",
        "mcp",
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "console_run",
                "arguments": {"text": "tail -n 2 ttyd.log"},
            },
        },
    )
    tail = b"tail -n 2 ttyd.log\r\n[2026/10/17 14:20:11:0421] N: WS   /ws - 127.0.0.1, clients: 1\r\n[2026/10/17 14:20:11:0433] N: started process, pid: 4242\r\n$ "
    t.notify("SERVER", "AI", "console.output", blobs=[(tail, {})])
    t.notify("AI", "UI", "console.output", blobs=[(tail, {})])
    t.notify(
        "SERVER",
        "AI",
        "mcp",
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"content": [{"type": "text", "text": tail.decode()}]},
        },
    )
    t.notify("AI", "UI", "status", {"state": "ready", "detail": ""})
    t.note("The user closes the console from the view.")
    close_ui = t.request("UI", "AI", "console.close", {})
    t.exchange("AI", "SERVER", "console.close", {}, {"code": 0})
    t.reply("AI", "UI", close_ui, "console.close", {"code": 0})
    return t.write()


def fault_write() -> str:
    t = Transcript(
        "04_fault_reconnect",
        "A server fault, the disconnect, and the reconnect that reconciles.",
        False,
    )
    t.note(
        "A doc.get names a version that does not exist. First failure only: one error line, exit 1."
    )
    i = t.request("AI", "SERVER", "doc.get", {"ref": "metaverse/world/main/9"})
    stack = (
        "Traceback (most recent call last):\n"
        f'  File "{_ROOT}/main_loop.py", line 88, in loop_run\n'
        "    reply = dispatch.line_dispatch(line)\n"
        f'  File "{_ROOT}/dispatch.py", line 41, in line_dispatch\n'
        "    return fn(line, **payload_of(line))\n"
        f'  File "{_ROOT}/engine_doc.py", line 17, in doc_get\n'
        "    body = store.doc_get(ref)\n"
        f'  File "{_ROOT}/substrate.py", line 203, in doc_get\n'
        '    raise KeyError(i18n("doc_missing", ref))\n'
        "KeyError: 'doc.get: metaverse/world/main/9: no such version'"
    )
    t.reply(
        "SERVER",
        "AI",
        i,
        "error",
        {
            "message": "doc.get: metaverse/world/main/9: no such version",
            "stack": stack,
        },
    )
    t.event("TTYD", "LOG", f"process exited with code 1, pid: {_PID}")
    t.note(
        "Linux ttyd ends the connection with no close frame; the browser reports 1006."
    )
    t.event("TTYD", "AI", "WebSocket closed code 1006 wasClean false")
    t.notify(
        "AI",
        "UI",
        "fault",
        {
            "thread": "server",
            "message": "doc.get: metaverse/world/main/9: no such version",
            "stack": stack,
        },
    )
    t.notify("AI", "UI", "status", {"state": "closed", "detail": "1006"})
    t.note(
        "The UI shows the fault and Reconnect. The user presses it; nothing reloads the page."
    )
    reconnect = t.request("UI", "AI", "wire.reconnect", {})
    hello = connection_open(
        t,
        _PID_AGAIN,
        {"metaverse": 9, "files": 1, "castle": 0, "castle/gatehouse": 1},
        False,
    )
    t.reply(
        "AI",
        "SERVER",
        hello,
        "hello",
        {
            "sha256": _PAGE_SHA256,
            "tab": _TAB,
            "seq": {
                "metaverse": 9,
                "files": 0,
                "castle": 0,
                "castle/gatehouse": 1,
            },
        },
    )
    t.note(
        "Reconciliation: files differs, 1 on the server and 0 here; the browser pulls, lacks the hash, fetches it, applies."
    )
    png = png_make()
    row = {
        "k": _IMAGE_KEY,
        "size": len(png),
        "sha256": sha256_hex(png),
        "seq": 1,
    }
    t.exchange(
        "AI",
        "SERVER",
        "sync.pull",
        {"db": "files", "since": 0},
        {
            "db": "files",
            "seq": 1,
            "kv": [row],
            "gone": [],
            "doc": [],
            "head": [],
            "turn": [],
        },
    )
    t.note(
        "The scene's refs name the image, so the browser's files keeps it; otherwise the row alone would do."
    )
    t.exchange(
        "AI",
        "SERVER",
        "kv.get",
        {"db": "files"},
        {"size": len(png), "sha256": sha256_hex(png)},
        reply_blobs=[(png, {})],
        k=_IMAGE_KEY,
    )
    t.exchange(
        "AI",
        "WASM",
        "sync.apply",
        {
            "db": "files",
            "seq": 1,
            "kv": [row],
            "gone": [],
            "doc": [],
            "head": [],
            "turn": [],
            "blobs": [sha256_hex(png)],
        },
        {"seq": 1},
        blobs=[(png, {})],
    )
    t.reply(
        "AI",
        "UI",
        reconnect,
        "wire.reconnect",
        {
            "bootstrap": _BOOTSTRAP,
            "sha256": _BOOTSTRAP_SHA256,
            "pid": _PID_AGAIN,
            "python": _PYTHON,
            "sqlite": _SQLITE,
            "debug": False,
            "page_sha256": _PAGE_SHA256,
            "tab": _TAB,
        },
    )
    t.notify("AI", "UI", "status", {"state": "ready", "detail": ""})
    return t.write()


def sync_write() -> str:
    t = Transcript(
        "05_sync",
        "Steady state replication: a push after a write, a pull after a server-side change.",
        False,
    )
    t.note(
        "The player's preferences change: Always Allow for server.console_run. One doc.put, one push."
    )
    preferences = {"refs": [], "always_allow": ["server.console_run"]}
    t.exchange(
        "AI",
        "WASM",
        "doc.put",
        {"path": "metaverse/preferences/main", "body": preferences},
        {"ref": "metaverse/preferences/main/2", "seq": 10},
    )
    t.exchange(
        "AI",
        "SERVER",
        "sync.push",
        {
            "db": "metaverse",
            "seq": 10,
            "kv": [],
            "gone": [],
            "doc": [
                {
                    "path": "metaverse/preferences/main",
                    "version": 2,
                    "body": preferences,
                    "seq": 10,
                }
            ],
            "head": [{"path": "metaverse/preferences/main", "version": 2}],
            "turn": [],
            "blobs": [],
        },
        {"seq": 10},
    )
    t.note(
        "An external MCP client over stdio put a script into the server's files. The server tells every connected tab."
    )
    script = b"// simulation step: open doors whose keeper has left\nconst step = (store) => store.sql_run('castle/gatehouse', [{sql: 'UPDATE door SET locked = 0 WHERE entity NOT IN (SELECT entity FROM position)', params: []}]);\n"
    key = "castle/gatehouse/step/doors.js"
    row = {
        "k": key,
        "size": len(script),
        "sha256": sha256_hex(script),
        "seq": 2,
    }
    t.notify("SERVER", "AI", "kv.changed", {"db": "files", "seq": 2})
    t.exchange(
        "AI",
        "SERVER",
        "sync.pull",
        {"db": "files", "since": 1},
        {
            "db": "files",
            "seq": 2,
            "kv": [row],
            "gone": [],
            "doc": [],
            "head": [],
            "turn": [],
        },
    )
    t.exchange(
        "AI",
        "SERVER",
        "kv.get",
        {"db": "files"},
        {"size": len(script), "sha256": sha256_hex(script)},
        reply_blobs=[(script, {})],
        k=key,
    )
    t.exchange(
        "AI",
        "WASM",
        "sync.apply",
        {
            "db": "files",
            "seq": 2,
            "kv": [row],
            "gone": [],
            "doc": [],
            "head": [],
            "turn": [],
            "blobs": [sha256_hex(script)],
        },
        {"seq": 2},
        blobs=[(script, {})],
    )
    t.note(
        "A big value: the decoder streams it to the cache as it arrives; the handler renames the file into place by hash."
    )
    big = bytes(range(256)) * 1024
    t.exchange("AI", "WASM", "cache.open", {}, {"handle": "cache-1"})
    for offset in range(0, len(big), 131072):
        t.notify(
            "AI",
            "WASM",
            "cache.append",
            {"handle": "cache-1"},
            blobs=[(big[offset : offset + 131072], {})],
        )
    t.exchange(
        "AI",
        "WASM",
        "cache.close",
        {"handle": "cache-1"},
        {"sha256": sha256_hex(big)},
    )
    t.exchange(
        "AI",
        "WASM",
        "kv.put",
        {"db": "files", "handle": "cache-1"},
        {"sha256": sha256_hex(big), "seq": 3},
        k="castle/gatehouse/map.bin",
    )
    return t.write()


def tap_write() -> str:
    t = Transcript(
        "06_tap",
        "A browser test run reports its TAP stream for the server's consumer to check.",
        False,
    )
    t.note(
        "test.html ran the TypeScript suites; the UI holds the stream and sends it through the AI worker."
    )
    report = t.request(
        "UI", "AI", "tap.report", {"language": "typescript", "text": _TAP_TEXT}
    )
    t.exchange(
        "AI",
        "SERVER",
        "tap.report",
        {"language": "typescript", "text": _TAP_TEXT},
        {"ok": True, "pass": 6, "fail": 0, "skip": 0},
    )
    t.reply(
        "AI",
        "UI",
        report,
        "tap.report",
        {"ok": True, "pass": 6, "fail": 0, "skip": 0},
    )
    return t.write()


def stdio_write() -> str:
    t = Transcript(
        "07_mcp_stdio",
        "An external agent drives the server over the MCP stdio transport.",
        False,
    )
    _, server_tools = tools_load()
    version = settings_load()["mcp_protocol_version"]
    t.note(
        f"python3 {_ROOT}/mcp_stdio.py --root {_ROOT} --debug; one JSON-RPC message per line on stdin and stdout."
    )
    t.rpc(
        "CLIENT",
        "STDIO",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": version,
                "capabilities": {},
                "clientInfo": {"name": "claude-code", "version": "2.1"},
            },
        },
    )
    t.rpc(
        "STDIO",
        "CLIENT",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "xsjs-server", "version": "0"},
            },
        },
    )
    t.rpc(
        "CLIENT",
        "STDIO",
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    t.rpc(
        "CLIENT", "STDIO", {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    )
    t.rpc(
        "STDIO",
        "CLIENT",
        {"jsonrpc": "2.0", "id": 2, "result": {"tools": server_tools}},
    )
    t.rpc(
        "CLIENT",
        "STDIO",
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "log_tail", "arguments": {"count": 2}},
        },
    )
    lines = [
        {"at": 1792625411042, "level": 1, "text": "hello written, pid 4242"},
        {
            "at": 1792625411980,
            "level": 1,
            "text": "sync.pull metaverse since 0: 4 doc rows",
        },
    ]
    t.rpc(
        "STDIO",
        "CLIENT",
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [{"type": "text", "text": json_text(lines)}]
            },
        },
    )
    t.rpc(
        "CLIENT",
        "STDIO",
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "console_run", "arguments": {"text": "uptime"}},
        },
    )
    t.note(
        "No UI is attached to a stdio session, so a permit tool is refused rather than silently allowed."
    )
    t.rpc(
        "STDIO",
        "CLIENT",
        {
            "jsonrpc": "2.0",
            "id": 4,
            "error": {
                "code": -32000,
                "message": "console_run needs a permit and no UI is attached",
            },
        },
    )
    return t.write()


def main() -> int:
    for writer in (
        boot_write,
        turn_write,
        console_write,
        fault_write,
        sync_write,
        tap_write,
        stdio_write,
    ):
        print(writer())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
