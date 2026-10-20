#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The browser test. It builds the test page and the engine page with
# page_build.py, makes server roots under build/ as the start script makes
# them, serves each through the ttyd xsjs_install.ps1 builds, and drives
# headless Chrome or Edge through devtools.py, rung by rung, each rung under a
# timer and named by the stage of the plan it proves. The TypeScript suites
# run on the test page and the TAP file the server keeps is checked with the
# TAP consumer. The other rungs drive the pages with keys, clicks and text as
# the browser's input sends them, a stub HTTP server of this process and the
# scripted provider, and check what the page shows and what the server holds.
# Some roots name a main loop file in ttyd's command, and one has ttyd ask a
# credential. PNGs of the surveyed states go to build/test_browser/. It prints
# one line per rung and exits 0, or stops at the first failed check, names its
# rung and exits 1. ttyd's log and the page's console are copied to stderr.
# Standard library only, and ttyd, the browser and tsc through page_build.py
# are the programs it starts:
#
#     python3 python/test_browser.py

import argparse, base64, hashlib, http.server, json, os, re, select, shutil
import signal, socket, sqlite3, subprocess, sys, tempfile, threading, time
import types
from collections.abc import Callable
from typing import Any, NamedTuple, Protocol, Self, cast

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The checkout, which holds the `python` directory.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# The build directory: the pages, each run's roots, the PNGs and bytecode.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# The ttyd the install script builds from the pinned release and its patches.
_TTYD_PATH = os.path.join(_BUILD_PATH, "ttyd", "ttyd")

# The script that builds ttyd, which a missing ttyd names.
_INSTALL_SCRIPT = "xsjs_install.ps1"

# The start of the name of the directory each run makes its roots in.
_WORK_PREFIX = "test_browser-"

# The directory the PNGs of the surveyed states go to, kept after the run.
_PNG_PATH = os.path.join(_BUILD_PATH, "test_browser")

# The checkout's settings, the object each root's settings are made from.
_SETTINGS_PATH = os.path.join(_CHECKOUT_PATH, "settings.json")

# The strings file, which the start script copies into the root.
_STRINGS_PATH = os.path.join(_CHECKOUT_PATH, "i18n", "en-US.json")

# The seed directory, which the start script copies into the root.
_SEED_PATH = os.path.join(_PYTHON_PATH, "seed")

# The seed document of the hyperposition, whose subtitle a new root shows.
_HYPERPOSITION_PATH = os.path.join(_SEED_PATH, "hyperposition.json")

# The stock main loop, which the restart rung serves from the root.
_MAIN_LOOP_PATH = os.path.join(_PYTHON_PATH, "main_loop.py")

# The modules the server runs, which the start script copies into the root.
_RUNTIME_MODULES = (
    "i18n",
    "jslb",
    "verbose",
    "settings",
    "substrate",
    "dispatch",
    "mcp",
    "mcp_stdio",
    "engine_kv",
    "engine_doc",
    "engine_db",
    "engine_turn",
    "engine_sql",
    "engine_verbose",
    "engine_tap",
    "engine_mcp",
    "engine_system",
    "main_loop",
    "bootstrap",
)

# The name the test page is built under, as the plan names it.
_TEST_PAGE = "test"

# The name the engine page is built under, beside the maintainer's page.
_ENGINE_PAGE = "test_engine"

# The directory of a root that holds the main loop files.
_MAIN_LOOP_DIRECTORY = "main_loop"

# The main loop file the restart rung names: the stock one, copied.
_RESTART_NAME = "main_loop.py"

# The fixture main loop file whose `loop_prepare` never returns.
_STALL_LOOP_NAME = "stall_loop.py"

# That file in the checkout, beside this one.
_STALL_LOOP_PATH = os.path.join(_PYTHON_PATH, _STALL_LOOP_NAME)

# The main loop file that serves `echo` and opens no database.
_ECHO_LOOP_NAME = "echo_loop.py"

# That file in the checkout, beside this one.
_ECHO_LOOP_PATH = os.path.join(_PYTHON_PATH, _ECHO_LOOP_NAME)

# bootstrap.py's option that names a main loop file of the root.
_LOOP_OPTION = "--main-loop"

# The extension of a database file under the root.
_DB_EXTENSION = ".sqlite"

# The log's database file in the root, which only the server writes.
_VERBOSE_FILE = "_verbose.sqlite"

# The TAP file in the root that the server appends the page's lines to.
_TAP_FILE = os.path.join("tap", "typescript.tap")

# The line that starts each TAP document.
_TAP_VERSION = "TAP version 14"

# The TAP documents the test page writes: the AI worker's, then the UI's.
_TAP_DOCUMENTS = 2

# The name `argparse` shows, as `sys.argv` may be empty.
_PROGRAM_NAME = "test_browser.py"

# A default chosen by its writer: the seconds a rung runs before it fails.
_RUNG_SECONDS = 120.0

# A default chosen by its writer: the seconds the TypeScript suites may run.
_SUITES_SECONDS = 600.0

# A default chosen by its writer: the seconds between two looks at a state.
_POLL_SECONDS = 0.1

# A default chosen by its writer: the seconds ttyd has to exit on `SIGTERM`.
_STOP_SECONDS = 5.0

# A default chosen by its writer: the whole seconds the HTTP ports wait.
_HTTP_SECONDS = 2

# A default chosen by its writer: the whole seconds the media ports wait.
_MEDIA_SECONDS = 2

# A default chosen by its writer: the seconds a console command may run.
_CONSOLE_SECONDS = 30

# A default chosen by its writer: the seconds before `sleep 600` times out.
_SLEEP_SECONDS = 2

# A default chosen by its writer: the seconds the stub holds a request.
_HOLD_SECONDS = 120.0

# A default chosen by its writer: the seconds the page is left without input.
_QUIET_SECONDS = 5.0

# A default chosen by its writer: the seconds the 128 MiB echo may run.
_ECHO_SECONDS = 600.0

# The whole seconds wire.ts waits for a token, for an open and for hello.
_WIRE_SECONDS = 120

# A default chosen by its writer: the width of the page in CSS pixels.
_WINDOW_WIDTH = 1280

# A default chosen by its writer: the height of the page in CSS pixels.
_WINDOW_HEIGHT = 720

# ttyd's options as the start script gives them, but its port and its page.
_TTYD_OPTIONS = (
    "--interface",
    "127.0.0.1",
    "--writable",
    "--check-origin",
    "--terminal-type",
    "dumb",
    "--url-arg",
)

# The option that names the page ttyd serves.
_INDEX_OPTION = "--index"

# The option, patched into the release, that sets ttyd's receive chunk size.
_BUFFER_OPTION = "--srv-buf-size"

# The environment variable of the provider key, kept from every scripted run.
_PROVIDER_VARIABLE = "XSJS_PROVIDER_KEY"

# The option of ttyd that has it ask a credential by basic authentication.
_CREDENTIAL_OPTION = "--credential"

# The user and password of that credential.
_CREDENTIAL = "rung:browser"

# ttyd's first log line, with its version and that of libwebsockets.
_VERSION_PATTERN = re.compile(r" N: (ttyd \S+ \(libwebsockets \S+\))$")

# ttyd's log line of the port it listens on.
_LISTENING_PATTERN = re.compile(r" Listening on port: (\d+)$")

# ttyd's log line of a program it started, with its pid.
_STARTED_PATTERN = re.compile(r"started process, pid: (\d+)$")

# ttyd's log line of a program's end: how, its code or signal, its pid.
_ENDED_PATTERN = re.compile(
    r"process (killed with signal|exited with code) (\d+), pid: (\d+)$"
)

# How ttyd's log says a program exited with a code.
_EXITED_WORDS = "exited with code"

# The most bytes read from ttyd's log at once.
_READ_BYTES = 1 << 20

# The exit code of a run with a failed check.
_EXIT_FAILED = 1

# The exit code of a run that `^C` ended.
_EXIT_INTERRUPTED = 130

# A shell's exit code for a signal is this plus the signal's number.
_SIGNAL_BASE = 128

# The page the browser shows between two pages of a root.
_BLANK_URL = "about:blank"

# The lifecycle event of a document that finished loading.
_LOAD_EVENT = "load"

# The modifier bit of the control key in DevTools' input events.
_CONTROL_MODIFIER = 2

# The key code of the digit 0, the other digits following it.
_DIGIT_CODE = 48

# The no break space, which the console's rows show for a space.
_NO_BREAK = chr(0xA0)

# How far into an element's first line a point is taken, in CSS pixels.
_CORNER_PIXELS = 4

# The overlays of the ttys, one `pre` each in the debug container.
_OVERLAY_SELECTOR = "#debug > pre"

# The console view's own child of the debug container.
_CONSOLE_SELECTOR = "#debug > div"

# The terminal of the console view.
_TERMINAL_SELECTOR = "#debug .xterm"

# The text area the terminal takes its keys and text from.
_TERMINAL_INPUT = "#debug .xterm-helper-textarea"

# The debug container of the page.
_DEBUG_SELECTOR = "#debug"

# The player's input.
_INPUT_SELECTOR = "#input"

# The subtitle area, which holds the subtitle, the permit and the input.
_SUBTITLE_SELECTOR = "#subtitle"

# The subtitle's text.
_SUBTITLE_TEXT = "#subtitle p"

# The colour black as computed styles give it.
_BLACK = "rgb(0, 0, 0)"

# The address every server of this test listens on.
_LOCAL_HOST = "127.0.0.1"

# The header that lets the page read a response of another origin.
_CORS_ORIGIN = "Access-Control-Allow-Origin"

# The status of a request that succeeded.
_HTTP_OK = 200

# The status of an answer with no body.
_NO_CONTENT = 204

# The status the media download of a missing file gets.
_MISSING_STATUS = 404

# The status of a request without the credential ttyd asks.
_UNAUTHORIZED = 401

# The failing statuses the HTTP port must report.
_STATUSES = (400, 401, 500)

# The media type of JSON.
_JSON_MEDIA = "application/json"

# The media type of plain text.
_TEXT_MEDIA = "text/plain"

# The media type of a PNG.
_PNG_MEDIA = "image/png"

# The stub's path that takes a POST and answers JSON.
_ECHO_PATH = "/echo"

# The stub's path that answers plain text.
_TEXT_PATH = "/text"

# The stub's path that answers JSON.
_JSON_PATH = "/json"

# The stub's path that answers the PNG.
_PNG_STUB_PATH = "/png"

# The start of the stub's paths that answer with a status.
_STATUS_PREFIX = "/status/"

# The stub's path that never answers.
_SILENT_PATH = "/silent"

# The stub's path that sends its head and part of its body, then stalls.
_STALL_PATH = "/stall"

# The body length the stalled answer announces, more than it sends.
_STALL_LENGTH = 100

# The start of the stub's paths answered in reverse order of their number.
_ORDER_PREFIX = "/order/"

# How many requests the order rung sends.
_ORDER_COUNT = 3

# The stub's path answered only after the second one.
_FIRST_PATH = "/pair/first"

# The stub's path answered at once.
_SECOND_PATH = "/pair/second"

# The base whose token request the stub holds until it stops.
_HELD_BASE = "/held/"

# The base whose token the stub answers and whose socket it holds.
_OPENING_BASE = "/opening/"

# The base whose token the stub answers and whose socket it drops unanswered.
_CLOSING_BASE = "/closing/"

# The token's path, which wire.ts resolves against a base.
_TOKEN_PATH = "token"

# The engine socket's path, which wire.ts resolves against a base.
_SOCKET_PATH = "ws"

# The console socket's path, which wire.ts resolves against a base.
_CONSOLE_PATH = "ws?arg=console"

# The token the stub answers.
_STUB_TOKEN = "rung-token"

# The text the stub's text path answers.
_PLAIN_TEXT = "plain text"

# The value the stub's JSON path answers.
_JSON_VALUE: dict[str, Any] = {"a": 1}

# The value the stub's POST path answers.
_ECHO_ANSWER: dict[str, Any] = {"ok": True}

# The type of the line the HTTP port answers.
_HTTP_TYPE = "http.request"

# Text of 2, 3 and 4 byte characters for payloads, built from code points.
_WIDE_TEXT = (
    "na" + chr(0xEF) + "ve " + chr(0x65E5) + chr(0x672C) + " " + chr(0x1F600)
)

# The headers of the POST, which make the browser ask a CORS preflight.
_POST_HEADERS = {
    "authorization": "Bearer test-browser",
    "content-type": "application/json",
}

# The JSON body of the POST.
_POST_JSON: dict[str, Any] = {
    "text": _WIDE_TEXT,
    "count": -3,
    "nested": {"list": [1, "two", None, True]},
}

# The body of the GET that the browser must refuse.
_GET_BODY = "x"

# The database that holds media, scripts and blobs by key.
_FILES_DB = "_files"

# The database of the metaverse.
_METAVERSE_DB = "metaverse"

# The ref the message size rungs put their value under.
_ROUND_REF = "/_files/rung/round.bin"

# The id of the `kv.put` of the round trip.
_PUT_ID = 1

# The id of the `kv.get` of the round trip.
_GET_ID = 2

# The id of the `kv.put` one byte over `message_max`.
_OVER_ID = 3

# A type no handler serves.
_UNKNOWN_TYPE = "rung.unknown"

# The id of the line of the unknown type.
_UNKNOWN_ID = 7

# The close code a browser reports when the connection ended with no frame.
_CLOSE_LOST = 1006

# The tag `line_render` writes after the JSON text for blob 1.
_BLOB_TAG = '<blob "n"=1>'

# Text as long as a digest: 64 hex digits.
_DIGEST_SHAPE = "0" * 64

# The period of the byte pattern of the rungs' blobs.
_PATTERN_PERIOD = 251

# The bytes in a MiB.
_MIB = 1 << 20

# The blob bytes the large echo sends in all, 128 MiB.
_LARGE_BYTES = 128 * _MIB

# The blob of each request of the large echo, 8 MiB, so each fits message_max.
_ECHO_BLOB_BYTES = 8 * _MIB

# Bytes that no image decoder takes.
_UNDECODABLE = b"not an image"

# The message of the error thrown after the page loaded.
_THROWN_MESSAGE = "rung thrown error"

# The message of the fault shown after the first one.
_SECOND_MESSAGE = "rung second fault"

# The message of the promise rejection nothing handles.
_REJECTED_MESSAGE = "rung rejected promise"

# The message the worker throws once its script ran.
_POSTED_MESSAGE = "rung worker fault"

# The message the worker throws before anything of its script ran.
_LOAD_MESSAGE = "rung worker load fault"

# The message the worker constructor throws while the parser runs.
_APPEND_MESSAGE = "rung fault while parsing"

# The message of the HTTP port's receiver that throws.
_RECEIVER_MESSAGE = "rung receiver throws"

# The message of the queue handler that throws.
_HANDLER_MESSAGE = "rung handler throws"

# The start of the fault text of a resource that failed to load.
_RESOURCE_FAILURE = "Failed to load "

# The fault text of a failed element with neither address.
_ADDRESS_MISSING = "Neither src nor href names what failed to load in "

# What the fault screen's Reload button runs.
_RELOAD_CALL = "location.reload()"

# Stands for an argument of a string that the rung cannot know.
_ANY = "\x00any\x00"

# The ref the provider script is read from, which every scripted root holds.
_SCRIPT_REF = "/_files/provider/script.json"

# The start of the ref of a script the AI runs.
_AI_SCRIPT_PREFIX = "/_files/script/"

# The end of the ref of a script the AI runs.
_AI_SCRIPT_EXTENSION = ".js"

# The browser tool that runs a script.
_RUN_TOOL = "browser.script_run"

# The browser tool that asks the player's permit.
_PERMIT_TOOL = "browser.console_run"

# The seeded script that makes a universe, a world and a region.
_BOOTSTRAP_NAME = "bootstrap"

# The universe the scripted turn makes.
_UNIVERSE = "rung_universe"

# The title of that universe.
_UNIVERSE_TITLE = "The rung universe"

# The world the scripted turn makes.
_WORLD = "rung_world"

# The region the scripted turn makes, which holds its scene.
_REGION = "rung_region"

# The id of the scene document the scripted turn writes.
_SCENE_ID = "scene/arrival"

# The `Document-Ref` of the first version of that scene.
_SCENE_REF = "/rung_region/scene/arrival/1"

# The key the image tool keeps the image under, in `_files`.
_IMAGE_KEY = "rung/scene.png"

# The ref of that image.
_IMAGE_REF = "/_files/rung/scene.png"

# The prompt of the image the scripted turn asks for.
_IMAGE_PROMPT = "A test pattern of hard edged squares."

# The subtitle of the scene the scripted turn enters.
_SCENE_SUBTITLE = "The rung scene is entered."

# The node of the script a page starts in.
_NODE_START = "start"

# The node after the bootstrap script ran.
_NODE_BUILT = "built"

# The node after the image was made.
_NODE_IMAGED = "imaged"

# The node after the scene was written, entered and rendered.
_NODE_ENTERED = "entered"

# The input of the scripted turn.
_INPUT_TURN = "1"

# The input whose tool call restarts the server.
_INPUT_RESTART = "2"

# The input whose tool call runs an echo in the console.
_INPUT_RUN = "3"

# The input whose tool call runs `sleep 600` in the console.
_INPUT_TIMEOUT = "4"

# The input whose tool call the player denies.
_INPUT_DENY = "5"

# The input whose tool call sets the AI's verbose level.
_INPUT_LEVEL = "6"

# The input answered with text alone.
_INPUT_PLAIN = "7"

# The input whose script makes a table of strings.
_INPUT_PAIRS = "8"

# The input whose script writes a value over `overflow_bytes`.
_INPUT_OVERFLOW = "9"

# The input whose script fills the cache.
_INPUT_CACHE = "10"

# The input whose script fills the database pool.
_INPUT_POOL = "11"

# The input whose tool call runs an echo while the console is hidden.
_INPUT_HIDDEN = "12"

# The text the console run ends with.
_ENDING_RUN = "The console run ended."

# The text the timed out console run ends with.
_ENDING_TIMEOUT = "The timed out run ended."

# The text the denied console run ends with.
_ENDING_DENY = "The denied run ended."

# The text the verbose level change ends with.
_ENDING_LEVEL = "The level change ended."

# The text the plain turn ends with.
_ENDING_PLAIN = "The plain turn ended."

# The text the table script ends with.
_ENDING_PAIRS = "The table script ended."

# The text the overflow script ends with.
_ENDING_OVERFLOW = "The overflow script ended."

# The text the cache script ends with.
_ENDING_CACHE = "The cache script ended."

# The text the pool script ends with.
_ENDING_POOL = "The pool script ended."

# The text the hidden console run ends with.
_ENDING_HIDDEN = "The hidden run ended."

# The word typed into the console and echoed.
_MARK_TYPED = "rung_typed"

# The word the console run echoes.
_MARK_RUN = "rung_run"

# The word the denied console run would have echoed.
_MARK_DENIED = "rung_denied"

# The word the console run echoes while the console is hidden.
_MARK_HIDDEN = "rung_hidden"

# The command that outlives its timeout until `^C` ends it.
_SLEEP_COMMAND = "sleep 600"

# The command that ends dash.
_EXIT_COMMAND = "exit"

# Text typed into the console after it ended.
_DROPPED_TEXT = "dropped"

# The prompt row of dash, its trailing space trimmed.
_PROMPT_ROW = "$"

# The prompt dash writes when it waits for a command.
_PROMPT_TEXT = "$ "

# The word typed into the console before its first message, then dropped.
_MARK_EARLY = "rung_early"

# The character that starts a message of ttyd's client carrying input.
_INPUT_KIND = "0"

# The columns the probe's first console message gives the terminal.
_PROBE_COLUMNS = 80

# The rows the probe's first console message gives the terminal.
_PROBE_ROWS = 24

# The level the verbose level tool sets.
_TOOL_LEVEL = 2

# The script that makes a table of strings and reads it back.
_PAIRS_NAME = "rung_pairs"

# The database that script makes.
_PAIRS_DB = "rung_pairs"

# The rows of that table, ordered by their key.
_PAIRS_ROWS = [["one", "first"], ["two", "second"]]

# The script that writes a value over `overflow_bytes`.
_OVERFLOW_NAME = "rung_overflow"

# The ref that script writes.
_OVERFLOW_REF = "/_files/rung/overflow.bin"

# The script that writes values until the cache is full.
_CACHE_NAME = "rung_cache"

# The start of the refs that script writes.
_CACHE_PREFIX = "/_files/rung/cache/"

# The script that creates databases until the pool is full.
_POOL_NAME = "rung_pool"

# The start of the names of the databases that script creates.
_POOL_PREFIX = "rung_pool_"

# The most values or databases the filling scripts try.
_SCRIPT_LIMIT = 1000

# The AI script that makes a table of strings and reads it back.
_PAIRS_SCRIPT = """const store = engine.store;
store.db_create(args.db);
store.sql_run(args.db, [
  {
    sql:
      "CREATE TABLE pair (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT",
    params: [],
  },
  { sql: "INSERT INTO pair VALUES (?, ?), (?, ?)", params: args.rows.flat() },
]);
const read = { sql: "SELECT key, value FROM pair ORDER BY key", params: [] };
return store.sql_run(args.db, [read])[0].rows;
"""

# The AI script that writes a value over `overflow_bytes` and reads it back.
_OVERFLOW_SCRIPT = """const data = new Uint8Array(args.size);
for (let index = 0; index < args.size; index += 1) {
  data[index] = index % 251;
}
const put = engine.store.kv_put(args.ref, data);
const value = engine.store.kv_get(args.ref);
return {
  size: put.row.size,
  sha256: put.row.sha256,
  cached: typeof value.data === "string",
};
"""

# The AI script that writes values until the cache refuses, then deletes them.
_CACHE_SCRIPT = """const written = [];
try {
  for (let count = 0; count < args.limit; count += 1) {
    const data = new Uint8Array(args.size);
    new DataView(data.buffer).setUint32(0, count);
    engine.store.kv_put(args.prefix + count, data);
    written.push(args.prefix + count);
  }
} catch (error) {
  for (const ref of written) {
    engine.store.kv_delete(ref);
  }
  return { written: written.length, error: String(error) };
}
return { written: written.length, error: null };
"""

# The AI script that creates databases until the pool refuses, then drops.
_POOL_SCRIPT = """const made = [];
try {
  for (let count = 0; count < args.limit; count += 1) {
    const db = args.prefix + count;
    engine.store.db_create(db);
    made.push(db);
  }
} catch (error) {
  const failed = args.prefix + made.length;
  const listed = engine.store.db_list().includes(failed);
  for (const db of made) {
    engine.store.db_drop(db);
  }
  return { made: made.length, error: String(error), listed };
}
for (const db of made) {
  engine.store.db_drop(db);
}
return { made: made.length, error: null, listed: false };
"""

# The thread whose lines the UI sends to the server.
_UI_THREAD = "ui"

# The thread whose lines the AI worker sends to the server.
_AI_THREAD = "ai"

# What a line of the AI's log holds once the start rendered the scene.
_RENDERED_MARK = '"worker.rendered"'

# What a line of the AI's log holds when it asks for a snapshot.
_SNAPSHOT_MARK = '"db.snapshot"'

# The verbose line the UI logs between two items of its queue.
_BATCH_MARK = "rung batched line"

# The subtitle of the hyperposition's second version, written by the test.
_REPLACED_SUBTITLE = "The rung hyperposition is replaced."

# The ref the desync rung writes on the server behind the page's back.
_DESYNC_REF = "/metaverse/rung/desync"

# The first byte of a ttyd message of program output.
_OUTPUT_KIND = 0x30

# Replaces `Worker` so that the engine page starts no worker of its own.
_WORKER_STUB = """globalThis.xsjs_worker_original = globalThis.Worker;
globalThis.Worker = class {
  postMessage() {}
  terminate() {}
};
"""

# Adds a prefix and a suffix to the text of every script `Blob`.
_BLOB_PATCH = """(() => {
  const Original = globalThis.Blob;
  globalThis.Blob = class extends Original {
    constructor(parts, options) {
      const script =
        options !== undefined && options.type === "text/javascript";
      super(script ? [XSJS_PREFIX, ...parts, XSJS_SUFFIX] : parts, options);
    }
  };
})();
"""

# Replaces `Worker` by a class whose constructor throws.
_WORKER_THROW = """globalThis.Worker = class {
  constructor() {
    throw new Error(XSJS_MESSAGE);
  }
};
"""

# The page's probes: functions the rungs call through `Runtime.evaluate`.
_PROBE_KIT = r"""(() => {
  const probe = {
    lines: {},
    ports: {},
    sink_bytes: {},
    sink_count: 0,
    wire: {},
    worker_lines: [],
    kept: {},
    long_tasks: [],
    order: [],
    thread_replies: [],
    pair_replies: [],
    console: null,
  };
  probe.bytes_join = (parts) => {
    let total = 0;
    for (const part of parts) {
      total += part.length;
    }
    const joined = new Uint8Array(total);
    let offset = 0;
    for (const part of parts) {
      joined.set(part, offset);
      offset += part.length;
    }
    return joined;
  };
  probe.sink = {
    sink_open: () => {
      probe.sink_count += 1;
      const handle = "probe/" + probe.sink_count;
      probe.sink_bytes[handle] = [];
      return handle;
    },
    sink_append: (handle, data) => {
      probe.sink_bytes[handle].push(data.slice());
    },
    sink_close: (handle) => {
      const joined = probe.bytes_join(probe.sink_bytes[handle]);
      probe.sink_bytes[handle] = joined;
      return utility.sha256_hex(joined);
    },
  };
  probe.blob_bytes = (blob) => {
    const data = jslb.field_get(blob, "data");
    return typeof data === "string" ? probe.sink_bytes[data] : data;
  };
  probe.summary = (line) => ({
    header: line[0],
    payload: jslb.payload_of(line),
    blobs: jslb
      .headers_of(line)
      .slice(1)
      .map((blob) => {
        const bytes = probe.blob_bytes(blob);
        return { size: bytes.length, sha256: utility.sha256_hex(bytes) };
      }),
  });
  probe.receiver = (name) => {
    probe.lines[name] = [];
    return (line) => {
      probe.lines[name].push(probe.summary(line));
    };
  };
  probe.http_port = (name, seconds) => {
    const port = new http.HttpPort(seconds);
    port.line_receive(probe.receiver(name));
    probe.ports[name] = port;
    return true;
  };
  probe.media_port = (name, budget, seconds) => {
    const port = new media.MediaPort(budget, seconds);
    port.line_receive(probe.receiver(name));
    probe.ports[name] = port;
    return true;
  };
  probe.request_send = (name, type, id, payload, blobs) => {
    const made = blobs.map((bytes) => jslb.blob_make(Uint8Array.from(bytes)));
    const header = jslb.header_make(type, { id });
    probe.ports[name].line_post(jslb.line_make(header, made, payload), []);
    return true;
  };
  probe.lines_when = (name, count) =>
    probe.lines[name].length >= count ? probe.lines[name] : null;
  probe.pattern = (size) => {
    const data = new Uint8Array(size);
    for (let index = 0; index < size; index += 1) {
      data[index] = index % 251;
    }
    return data;
  };
  probe.thrown = (fn) => {
    try {
      fn();
    } catch (error) {
      return String(error.message);
    }
    return null;
  };
  probe.sink_free = (line) => {
    for (const blob of jslb.headers_of(line).slice(1)) {
      const data = jslb.field_get(blob, "data");
      if (typeof data === "string") {
        delete probe.sink_bytes[data];
      }
    }
  };
  probe.wire_open = (name, base) => {
    const record = { hello: null, lines: [], closes: [], after: null };
    const values = {};
    const port = new wire.WirePort(base, probe.sink, (id) => values[id]);
    port.line_receive((line) => {
      record.lines.push(probe.summary(line));
      probe.sink_free(line);
      if (record.after !== null) {
        record.after();
      }
    });
    port.close_receive((code, had_error) => {
      record.closes.push([code, had_error]);
    });
    port.wire_open((hello) => {
      Object.assign(values, hello.settings);
      record.hello = jslb.payload_of(hello);
      port.line_post(dispatch.reply_make(hello, {}), []);
    });
    probe.wire[name] = { port, record };
    return true;
  };
  probe.wire_hello = (name) => probe.wire[name].record.hello;
  probe.wire_lines = (name, count) => {
    const lines = probe.wire[name].record.lines;
    return lines.length >= count ? lines : null;
  };
  probe.wire_closes = (name) => {
    const closes = probe.wire[name].record.closes;
    return closes.length > 0 ? closes : null;
  };
  probe.kv_put = (name, id, key, size, since) => {
    const header = jslb.header_make("kv.put", { id, key });
    const blob = jslb.blob_make(probe.pattern(size));
    const line = jslb.line_make(header, [blob], { since });
    probe.wire[name].port.line_post(line, []);
    return true;
  };
  probe.put_refused = (name, id, key, size, since) =>
    probe.thrown(() => probe.kv_put(name, id, key, size, since));
  probe.wire_send = (name, type, options, payload) => {
    const header = jslb.header_make(type, options);
    probe.wire[name].port.line_post(jslb.line_make(header, [], payload), []);
    return true;
  };
  probe.wire_close = (name) => {
    probe.wire[name].port.wire_close();
    return true;
  };
  probe.echo_run = (name, count, size) => {
    const wired = probe.wire[name];
    const data = probe.pattern(size);
    let sent = 0;
    const post = () => {
      sent += 1;
      const header = jslb.header_make("echo", { id: sent });
      const line = jslb.line_make(header, [jslb.blob_make(data)], {});
      wired.port.line_post(line, []);
    };
    wired.record.after = () => {
      if (sent < count) {
        post();
      }
    };
    post();
    return true;
  };
  probe.token_read = (url) =>
    fetch(url, { cache: "no-store" }).then((response) =>
      response.text().then((text) => ({ status: response.status, text })),
    );
  probe.hit = (element, x, y) => {
    const top = document.elementFromPoint(x, y);
    return top !== null && (top === element || element.contains(top));
  };
  probe.element_view = (element) => {
    const box = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    return {
      left: box.left,
      top: box.top,
      width: box.width,
      height: box.height,
      hidden: element.hidden,
      display: style.display,
      background: style.backgroundColor,
      center_hit: probe.hit(element, x, y),
      text: element.textContent,
      disabled: element.disabled === true,
    };
  };
  probe.view = (selector) => {
    const element = document.querySelector(selector);
    return element === null ? null : probe.element_view(element);
  };
  probe.views = (selector) =>
    Array.from(document.querySelectorAll(selector), (element) =>
      probe.element_view(element),
    );
  probe.viewport = () => ({ width: innerWidth, height: innerHeight });
  probe.center_inside = (selector, outer) => {
    const box = document.querySelector(selector).getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    return probe.hit(document.querySelector(outer), x, y);
  };
  probe.corner_inside = (selector, outer, offset) => {
    const box = document.querySelector(selector).getBoundingClientRect();
    const x = box.left + offset;
    const y = box.top + offset;
    return probe.hit(document.querySelector(outer), x, y);
  };
  probe.widths = () => {
    const debug = document.querySelector("#debug");
    return {
      debug_scroll: debug.scrollWidth,
      debug_client: debug.clientWidth,
      document_scroll: document.documentElement.scrollWidth,
      inner: innerWidth,
    };
  };
  probe.canvas = () => {
    const canvas = document.querySelector("#image");
    return {
      view: probe.element_view(canvas),
      width: canvas.width,
      height: canvas.height,
      inner_width: innerWidth,
      inner_height: innerHeight,
    };
  };
  probe.click_point = (x, y) => {
    const canvas = document.querySelector("#image");
    const box = canvas.getBoundingClientRect();
    const scale = Math.min(
      box.width / canvas.width,
      box.height / canvas.height,
    );
    const left = (box.width - canvas.width * scale) / 2;
    const top = (box.height - canvas.height * scale) / 2;
    const point_x = box.left + left + (x + 0.5) * scale;
    const point_y = box.top + top + (y + 0.5) * scale;
    return { x: point_x, y: point_y, hit: probe.hit(canvas, point_x, point_y) };
  };
  probe.fault = () => {
    const pre = document.querySelector("body > pre");
    return pre === null ? null : pre.textContent;
  };
  probe.outcome = (subtitle) => {
    const fault = probe.fault();
    if (fault !== null) {
      return { fault };
    }
    const text = document.querySelector("#subtitle p");
    const input = document.querySelector("#input");
    if (text === null || input === null) {
      return null;
    }
    return text.textContent === subtitle && !input.disabled
      ? { ended: true }
      : null;
  };
  probe.reload_button = () => {
    const button = document.querySelector("body > button");
    return button === null
      ? null
      : {
          view: probe.element_view(button),
          onclick: button.getAttribute("onclick"),
        };
  };
  probe.image_kept = () => document.querySelector("#image") !== null;
  probe.rows = () =>
    Array.from(
      document.querySelectorAll("#debug .xterm-rows > div"),
      (row) => row.textContent,
    );
  probe.focus = (selector) => {
    document.querySelector(selector).focus();
    return true;
  };
  probe.debug_children = () =>
    document.querySelector("#debug").children.length;
  probe.permit = () => {
    const text = document.querySelector("#permit p");
    const buttons = Array.from(document.querySelectorAll("#permit button"));
    return text === null || buttons.length === 0
      ? null
      : {
          text: probe.element_view(text),
          buttons: buttons.map((button) => probe.element_view(button)),
        };
  };
  probe.throw_later = (message) => {
    setTimeout(() => {
      throw new Error(message);
    }, 0);
    return true;
  };
  probe.reject_later = (message) => {
    setTimeout(() => {
      Promise.reject(new Error(message));
    }, 0);
    return true;
  };
  probe.resource_add = (tag, attributes) => {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      element.setAttribute(name, value);
    }
    document.body.append(element);
    return true;
  };
  probe.overlay_again = (message) => {
    error_overlay.overlay_show(message, "");
    return document.querySelectorAll("pre").length;
  };
  probe.history = () =>
    verbose.history_get(settings.settings_get("verbose_ring"));
  probe.sink_twice = () =>
    probe.thrown(() => verbose.sink_set(() => undefined));
  probe.log_mark = (level, text) => {
    verbose.log(level, text);
    return verbose.history_get(1)[0];
  };
  probe.ring_refused = () =>
    probe.thrown(() => new overlay.Overlay(document.createElement("div"), 0));
  probe.line_of = (type, payload) =>
    jslb.line_make(jslb.header_make(type), [], payload);
  probe.schedule_run = (type) => {
    const tasks = new queue.TaskQueue("ui", {}, false);
    dispatch.handler_register(type, 0, (line) => {
      probe.order.push(line.n);
      queueMicrotask(() => probe.order.push("micro " + line.n));
      return undefined;
    });
    tasks.line_notify(probe.line_of(type, { n: 1 }), "ui");
    tasks.line_notify(probe.line_of(type, { n: 2 }), "ui");
    probe.order.push("returned");
    probe.schedule_tasks = tasks;
    return true;
  };
  probe.order_when = (count) =>
    probe.order.length >= count ? probe.order : null;
  probe.worker_make = (code) => {
    const scripts = Array.from(
      document.querySelectorAll("script[data-worker]"),
    );
    const texts = scripts.slice(0, -1).map((script) => script.text);
    const source = '"use strict";\n' + texts.join("\n") + "\n" + code;
    const url = URL.createObjectURL(
      new Blob([source], { type: "text/javascript" }),
    );
    return new globalThis.xsjs_worker_original(url, { name: "probe" });
  };
  probe.thread_code = [
    "self.onmessage = (event) => {",
    '  const owners = { "probe.": "ai" };',
    '  const tasks = new queue.TaskQueue("ai", owners, false);',
    '  dispatch.handler_register("probe.ask", 0, (line) =>',
    "    dispatch.reply_make(line, { text: line.text, thread: self.name }),",
    "  );",
    '  tasks.port_add("ui", new queue.ThreadPort(event.data));',
    "  self.probe_tasks = tasks;",
    "};",
  ].join("\n");
  probe.thread_run = (begin, done) => {
    const channel = new MessageChannel();
    const worker = probe.worker_make(probe.thread_code);
    worker.postMessage(channel.port2, [channel.port2]);
    const tasks = new queue.TaskQueue("ui", {}, false);
    tasks.port_add("ai", new queue.ThreadPort(channel.port1));
    dispatch.handler_register(begin, 0, () => {
      const ask = probe.line_of("probe.ask", { text: "across" });
      const id = tasks.task_submit(ask, "ai");
      return dispatch.task_sleep({}, [id], done);
    });
    dispatch.handler_register(done, 0, (wake) => {
      probe.thread_replies = wake.replies.map((line) => probe.summary(line));
      return undefined;
    });
    tasks.line_notify(probe.line_of(begin, {}), "ui");
    probe.thread_parts = { tasks, worker };
    return true;
  };
  probe.thread_when = () =>
    probe.thread_replies.length > 0 ? probe.thread_replies : null;
  probe.pair_run = (begin, done, urls, seconds) => {
    const tasks = new queue.TaskQueue("ui", {}, false);
    tasks.port_add("http", new http.HttpPort(seconds));
    dispatch.handler_register(begin, 0, () => {
      const ids = urls.map((url) => {
        const payload = { method: "GET", url, headers: {} };
        return tasks.task_submit(
          probe.line_of("http.request", payload),
          "http",
        );
      });
      return dispatch.task_sleep({}, ids, done);
    });
    dispatch.handler_register(done, 0, (wake) => {
      probe.pair_replies = wake.replies.map((line) => probe.summary(line));
      return undefined;
    });
    tasks.line_notify(probe.line_of(begin, {}), "ui");
    probe.pair_tasks = tasks;
    return true;
  };
  probe.pair_when = () =>
    probe.pair_replies.length > 0 ? probe.pair_replies : null;
  probe.handler_throw = (type, message) => {
    const tasks = new queue.TaskQueue("ui", {}, false);
    dispatch.handler_register(type, 0, () => {
      throw new Error(message);
    });
    tasks.line_notify(probe.line_of(type, {}), "ui");
    probe.throw_tasks = tasks;
    return true;
  };
  probe.receiver_throw = (url, message, seconds) => {
    const port = new http.HttpPort(seconds);
    port.line_receive(() => {
      throw new Error(message);
    });
    const header = jslb.header_make("http.request", { id: 1 });
    const payload = { method: "GET", url, headers: {} };
    port.line_post(jslb.line_make(header, [], payload), []);
    return true;
  };
  probe.worker_http = (url, seconds) => {
    const code = [
      "const port = new http.HttpPort(" + JSON.stringify(seconds) + ");",
      "port.line_receive((line) => {",
      "  self.postMessage({ header: line[0], payload: jslb.payload_of(line) });",
      "});",
      'const header = jslb.header_make("http.request", { id: 1 });',
      "const url = " + JSON.stringify(url) + ";",
      'const payload = { method: "GET", url, headers: {} };',
      "port.line_post(jslb.line_make(header, [], payload), []);",
    ].join("\n");
    const worker = probe.worker_make(code);
    worker.onmessage = (event) => probe.worker_lines.push(event.data);
    probe.http_worker = worker;
    return true;
  };
  probe.worker_when = () =>
    probe.worker_lines.length > 0 ? probe.worker_lines : null;
  probe.png_bytes = () => Array.from(provider_script.image_pattern());
  probe.image_size = (name, key) => {
    const image = probe.ports[name].image_get(key);
    return image === undefined
      ? null
      : { width: image.width, height: image.height };
  };
  probe.image_keep = (name, key) => {
    probe.kept[key] = probe.ports[name].image_get(key);
    return true;
  };
  probe.kept_size = (key) => ({
    width: probe.kept[key].width,
    height: probe.kept[key].height,
  });
  probe.long_start = () => {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        probe.long_tasks.push(entry.duration);
      }
    });
    observer.observe({ type: "longtask" });
    probe.long_observer = observer;
    return true;
  };
  probe.long_list = () => probe.long_tasks;
  probe.console_line = (line) => {
    const messages = jslb
      .headers_of(line)
      .slice(1)
      .map((blob) => jslb.field_get(blob, "data"));
    return {
      header: line[0],
      payload: jslb.payload_of(line),
      kinds: messages.map((data) => data[0]),
      text: messages
        .map((data) => new TextDecoder().decode(data.subarray(1)))
        .join(""),
    };
  };
  probe.console_make = (base, read) => {
    const record = { lines: [], closes: [] };
    const port = new wire.ConsolePort(base, read);
    port.line_receive((line) => record.lines.push(probe.console_line(line)));
    port.close_receive((code) => record.closes.push(code));
    probe.console = record;
    probe.console_kept = port;
    return true;
  };
  probe.console_debug = (base, debug) =>
    probe.console_make(base, (id) => ({ debug })[id]);
  probe.console_ask = (id) => {
    const header = jslb.header_make("console.open", { id });
    probe.console_kept.line_post(jslb.line_make(header, [], {}), []);
    return true;
  };
  probe.console_open = (base) => {
    probe.console_make(base, settings.settings_get);
    return probe.console_ask(1);
  };
  probe.console_send = (text) => {
    const header = jslb.header_make("console.input", {});
    const blob = jslb.blob_make(new TextEncoder().encode(text));
    probe.console_kept.line_post(jslb.line_make(header, [blob], {}), []);
    return true;
  };
  probe.console_shut = () => {
    probe.console_kept.console_close();
    return true;
  };
  probe.console_state = () => probe.console;
  probe.console_when = () =>
    probe.console.closes.length > 0 ? probe.console : null;
  globalThis.xsjs_probe = probe;
  return true;
})()
"""

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# A check that failed, with the measurement that failed it.
class CheckFailed(Exception):
    pass


# One key as the keyboard sends it: its names, its code, modifiers and text.
class KeyStroke(NamedTuple):
    key: str
    code: str
    key_code: int
    modifiers: int
    text: str


# The key that ends a line, in a form or in the console.
_KEY_ENTER = KeyStroke("Enter", "Enter", 13, 0, "\r")

# Control and C, which interrupts the console's command.
_KEY_INTERRUPT = KeyStroke("c", "KeyC", 67, _CONTROL_MODIFIER, "")


# One request the stub server took: its method, path, headers and body.
class StubRequest(NamedTuple):
    method: str
    path: str
    headers: dict[str, str]
    body: bytes


# One line of the server's log of a page thread, in the order it was kept.
class VerboseRow(NamedTuple):
    seq: int
    at: int
    level: int
    text: str


# One input of the script that makes one tool call, and the text it ends on.
class ScriptCall(NamedTuple):
    tool: str
    arguments: dict[str, Any]
    ending: str


# What a root adds to ttyd's options and to the command ttyd runs.
class ServerExtras(NamedTuple):
    options: tuple[str, ...]
    arguments: tuple[str, ...]


# Nothing added: the root served as the start script serves it.
_EXTRAS_NONE = ServerExtras((), ())


# A process's resident size and its peak, in KiB.
class MemoryUse(NamedTuple):
    resident: int
    peak: int


# The DevTools calls the rungs make beyond the browser's own methods.
class DriverClient(Protocol):
    # Returns the result of a DevTools method on the page.
    def method_call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    # Passes events on until the condition holds.
    def events_pump(self, what: str, done: Callable[[], bool]) -> None: ...


# The page loads the browser has seen: loader and event name pairs.
class LifecycleEvents(Protocol):
    lifecycle: set[tuple[str, str]]


# The browser of `devtools.py` as the rungs use it.
class BrowserDriver(Protocol):
    events: LifecycleEvents

    # Navigates to the URL, again while refused, and returns once it loads.
    def page_open(self, url: str) -> None: ...

    # Evaluates JavaScript on the page and returns its JSON value.
    def script_evaluate(self, text: str) -> object: ...

    # Calls `fn` with the text of each console message from now on.
    def console_follow(self, fn: Callable[[str], None]) -> None: ...

    # Saves a PNG of the page to the path.
    def screenshot_save(self, path: str) -> None: ...

    # Returns the DevTools client of the page.
    def client_get(self) -> DriverClient: ...


# A rung's time limit, which fails loud once it has passed.
class RungTimer:
    # Starts the rung's time.
    def __init__(self, rung: str, seconds: float) -> None:
        self.rung = rung
        self.seconds = seconds
        self.end = time.monotonic() + seconds

    # Returns the seconds left, failing the rung once there are none.
    def seconds_left(self, what: str) -> float:
        left = self.end - time.monotonic()
        if left <= 0:
            raise CheckFailed(
                f"the rung {self.rung} ran out of its {self.seconds:g} s"
                f" waiting for {what}"
            )
        return left

    # Whether the rung's time has passed.
    def timer_expired(self) -> bool:
        return time.monotonic() >= self.end


# The rung that runs, its timer, and the line each rung prints.
class RungLog:
    # Starts on the build, before any rung.
    def __init__(self) -> None:
        self.rung = "build"
        self.timer = RungTimer(self.rung, _RUNG_SECONDS)

    # Names the rung that runs now and starts its timer.
    def rung_start(self, rung: str, seconds: float) -> None:
        self.rung = rung
        self.timer = RungTimer(rung, seconds)

    # Prints the summary of the rung that ran.
    def rung_print(self, summary: str) -> None:
        print(f"{self.rung}: {summary}", flush=True)

    # Runs a rung under its timer and prints its summary.
    def rung_run(
        self,
        rung: str,
        check: Callable[[], str],
        seconds: float = _RUNG_SECONDS,
    ) -> None:
        self.rung_start(rung, seconds)
        self.rung_print(check())


# ttyd serving one root and one page, in a session of its own.
class TtydServer:
    # Starts ttyd on a port of its choosing, running the root's bootstrap.
    def __init__(
        self,
        root: str,
        page: str,
        values: dict[str, Any],
        extras: ServerExtras,
        log: RungLog,
    ) -> None:
        self.root = root
        self.log = log
        self.command = [
            "python3",
            os.path.join(root, "python", "bootstrap.py"),
            "--root",
            root,
            *extras.arguments,
        ]
        self.version = _TTYD_PATH
        self.lines: list[str] = []
        self.partial = b""
        self.port = 0
        environment = {
            name: value
            for name, value in os.environ.items()
            if name != _PROVIDER_VARIABLE
        }
        self.fd, write_fd = os.pipe()
        try:
            self.process = subprocess.Popen(
                [
                    _TTYD_PATH,
                    "--port",
                    "0",
                    *_TTYD_OPTIONS,
                    *extras.options,
                    _INDEX_OPTION,
                    page,
                    _BUFFER_OPTION,
                    str(values["srv_buf_size"]),
                    *self.command,
                ],
                stdin=subprocess.DEVNULL,
                stdout=sys.stderr,
                stderr=write_fd,
                env=environment,
                start_new_session=True,
            )
        finally:
            os.close(write_fd)

    # Waits for ttyd's version and port, stopping it when that fails.
    def __enter__(self) -> Self:
        try:
            _, found = self.line_wait(_VERSION_PATTERN, "ttyd's version", 0)
            self.version = found.group(1)
            _, found = self.line_wait(_LISTENING_PATTERN, "ttyd to listen", 0)
            self.port = int(found.group(1))
        except BaseException:
            self.process_stop()
            raise
        return self

    # Stops ttyd whatever ended the block, a slow exit failing a clean run.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        stopped = self.process_stop()
        if not stopped and exception is None:
            raise CheckFailed(
                f"{self.version} still ran {_STOP_SECONDS:g} s after SIGTERM"
                " and was killed"
            )

    # Sends ttyd itself a signal, its programs left alone.
    def signal_send(self, number: int) -> None:
        os.kill(self.process.pid, number)

    # Copies whole log lines to stderr and keeps them.
    def lines_take(self, data: bytes) -> None:
        *complete, self.partial = (self.partial + data).split(b"\n")
        for line in complete:
            text = line.decode()
            self.lines.append(text)
            sys.stderr.write(f"{text}\n")

    # Reads the log once, failing at its end, as ttyd must not exit.
    def log_read(self) -> None:
        data = os.read(self.fd, _READ_BYTES)
        if not data:
            raise CheckFailed(
                f"{self.version} exited with {self.process.wait()}"
            )
        self.lines_take(data)

    # Reads the log while it holds bytes, without waiting.
    def log_poll(self) -> None:
        while select.select([self.fd], [], [], 0)[0]:
            self.log_read()

    # Waits for more of the log, within the rung's timer.
    def log_wait(self, what: str) -> None:
        readable, _, _ = select.select(
            [self.fd], [], [], self.log.timer.seconds_left(what)
        )
        if readable:
            self.log_read()

    # Returns the first log line from `start` on that matches, and its index.
    def line_wait(
        self, pattern: re.Pattern[str], what: str, start: int
    ) -> tuple[int, re.Match[str]]:
        index = start
        while True:
            while index < len(self.lines):
                found = pattern.search(self.lines[index])
                if found is not None:
                    return index, found
                index += 1
            self.log_wait(what)

    # The pids of the log lines from the mark on that match, by group.
    def pids_found(
        self, pattern: re.Pattern[str], group: int, mark: int
    ) -> set[int]:
        pids: set[int] = set()
        for line in self.lines[mark:]:
            found = pattern.search(line)
            if found is not None:
                pids.add(int(found.group(group)))
        return pids

    # Waits until every program started from the mark on has ended.
    def programs_wait(self, mark: int, least: int, what: str) -> int:
        while True:
            self.log_poll()
            started = self.pids_found(_STARTED_PATTERN, 1, mark)
            ended = self.pids_found(_ENDED_PATTERN, 3, mark)
            if len(started) >= least and started <= ended:
                return len(started)
            self.log_wait(what)

    # Stops ttyd, then reads the rest of its log. False when it needed SIGKILL.
    def process_stop(self) -> bool:
        stopped = True
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(_STOP_SECONDS)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
                stopped = False
        while data := os.read(self.fd, _READ_BYTES):
            self.lines_take(data)
        os.close(self.fd)
        if self.partial:
            sys.stderr.write(f"{self.partial.decode()}\n")
        return stopped


# A local HTTP server the page's ports talk to, answering by path.
class StubServer(http.server.ThreadingHTTPServer):
    # Listens on a port of its choosing with nothing taken yet.
    def __init__(self) -> None:
        super().__init__((_LOCAL_HOST, 0), StubHandler)
        self.condition = threading.Condition()
        self.requests: list[StubRequest] = []
        self.answered: list[str] = []
        self.released = False
        self.png = b""
        self.thread = threading.Thread(target=self.serve_forever)

    # Starts serving on a thread of its own.
    def __enter__(self) -> Self:
        self.thread.start()
        return self

    # Lets every held request go, then stops serving and closes the socket.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        with self.condition:
            self.released = True
            self.condition.notify_all()
        self.shutdown()
        self.thread.join()
        self.server_close()

    # The address of a path of the stub.
    def url_make(self, path: str) -> str:
        port = cast(tuple[str, int], self.server_address)[1]
        return f"http://{_LOCAL_HOST}:{port}{path}"

    # The WebSocket address of a path of the stub.
    def socket_make(self, path: str) -> str:
        port = cast(tuple[str, int], self.server_address)[1]
        return f"ws://{_LOCAL_HOST}:{port}{path}"

    # Keeps a request a handler took.
    def request_add(self, request: StubRequest) -> None:
        with self.condition:
            self.requests.append(request)
            self.condition.notify_all()

    # Keeps the path of an answer sent.
    def answer_add(self, path: str) -> None:
        with self.condition:
            self.answered.append(path)
            self.condition.notify_all()

    # Holds a handler until `ready` holds or the stub is released.
    def hold_wait(self, ready: Callable[[], bool]) -> None:
        with self.condition:
            self.condition.wait_for(
                lambda: ready() or self.released, _HOLD_SECONDS
            )

    # Holds a handler until the stub is released, past every wait of a page.
    def release_wait(self) -> None:
        with self.condition:
            self.condition.wait_for(lambda: self.released)

    # Returns the index and the last request of the method and path.
    def request_find(self, method: str, path: str) -> tuple[int, StubRequest]:
        with self.condition:
            found = [
                (index, request)
                for index, request in enumerate(self.requests)
                if request.method == method and request.path == path
            ]
        if not found:
            raise CheckFailed(f"the stub took no {method} {path}")
        return found[-1]

    # The paths answered so far that start with the prefix, in order.
    def answers_list(self, prefix: str) -> list[str]:
        with self.condition:
            return [path for path in self.answered if path.startswith(prefix)]

    # The order request due next, the highest first, once all have come.
    def order_turn(self) -> int | None:
        arrived = [
            request
            for request in self.requests
            if request.path.startswith(_ORDER_PREFIX)
        ]
        done = [
            path for path in self.answered if path.startswith(_ORDER_PREFIX)
        ]
        if len(arrived) < _ORDER_COUNT:
            return None
        return _ORDER_COUNT - 1 - len(done)


# Answers the page's requests by path, recording each in the stub server.
class StubHandler(http.server.BaseHTTPRequestHandler):
    # The stub server this handler answers for.
    def stub_get(self) -> StubServer:
        return cast(StubServer, self.server)

    # Records the request with its body.
    def request_keep(self, body: bytes) -> None:
        headers = {name.lower(): value for name, value in self.headers.items()}
        request = StubRequest(self.command, self.path, headers, body)
        self.stub_get().request_add(request)

    # Sends a whole answer with the CORS header, then records its path.
    def answer_send(self, status: int, media: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(len(body)))
        self.send_header(_CORS_ORIGIN, "*")
        self.end_headers()
        self.wfile.write(body)
        self.stub_get().answer_add(self.path)

    # Sends JSON text of the value.
    def json_send(self, value: object) -> None:
        self.answer_send(_HTTP_OK, _JSON_MEDIA, json_text(value).encode())

    # Sends the head and part of the body it announces, then nothing more.
    def stall_send(self) -> None:
        self.send_response(_HTTP_OK)
        self.send_header("Content-Type", _TEXT_MEDIA)
        self.send_header("Content-Length", str(_STALL_LENGTH))
        self.send_header(_CORS_ORIGIN, "*")
        self.end_headers()
        self.wfile.write(_PLAIN_TEXT.encode())

    # Answers a CORS preflight with the methods and the headers asked.
    def do_OPTIONS(self) -> None:
        self.request_keep(b"")
        asked = cast(str, self.headers["Access-Control-Request-Headers"])
        self.send_response(_NO_CONTENT)
        self.send_header(_CORS_ORIGIN, "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", asked)
        self.end_headers()

    # Records a POST with its body and answers it with JSON.
    def do_POST(self) -> None:
        length = int(cast(str, self.headers["Content-Length"]))
        self.request_keep(self.rfile.read(length))
        self.json_send(_ECHO_ANSWER)

    # Answers a GET by its path.
    def do_GET(self) -> None:
        self.request_keep(b"")
        stub = self.stub_get()
        path = self.path
        if path == _TEXT_PATH:
            self.answer_send(_HTTP_OK, _TEXT_MEDIA, _PLAIN_TEXT.encode())
        elif path == _JSON_PATH:
            self.json_send(_JSON_VALUE)
        elif path == _PNG_STUB_PATH:
            self.answer_send(_HTTP_OK, _PNG_MEDIA, stub.png)
        elif path.startswith(_STATUS_PREFIX):
            status = int(path.removeprefix(_STATUS_PREFIX))
            self.answer_send(status, _TEXT_MEDIA, f"status {status}".encode())
        elif path == _SILENT_PATH:
            stub.hold_wait(lambda: False)
        elif path == _STALL_PATH:
            self.stall_send()
            stub.hold_wait(lambda: False)
        elif path.startswith(_ORDER_PREFIX):
            number = int(path.removeprefix(_ORDER_PREFIX))
            stub.hold_wait(lambda: stub.order_turn() == number)
            self.json_send({"n": number})
        elif path == _FIRST_PATH:
            stub.hold_wait(lambda: _SECOND_PATH in stub.answered)
            self.json_send({"name": "first"})
        elif path == _SECOND_PATH:
            self.json_send({"name": "second"})
        elif path in (_HELD_BASE + _TOKEN_PATH, _OPENING_BASE + _SOCKET_PATH):
            stub.release_wait()
        elif path in (
            _OPENING_BASE + _TOKEN_PATH,
            _CLOSING_BASE + _TOKEN_PATH,
        ):
            self.json_send({"token": _STUB_TOKEN})
        elif path == _CLOSING_BASE + _CONSOLE_PATH:
            # Drops the connection unanswered, as a server that stopped would.
            self.close_connection = True
        else:
            raise ValueError(f"the stub serves no path {path}")


# One root's page in the browser: its address, its probes and its inputs.
class PageSession:
    # Takes the browser, the rung log, ttyd and the root's settings.
    def __init__(
        self,
        browser: BrowserDriver,
        log: RungLog,
        ttyd: TtydServer,
        values: dict[str, Any],
    ) -> None:
        self.browser = browser
        self.log = log
        self.ttyd = ttyd
        self.root = ttyd.root
        self.values = values
        self.url = f"http://{_LOCAL_HOST}:{ttyd.port}/"
        self.mark = len(ttyd.lines)

    # Calls a function of the probe kit with JSON arguments, returns its value.
    def probe_call(self, function: str, *args: object) -> object:
        self.ttyd.log_poll()
        shown = ", ".join(json.dumps(arg) for arg in args)
        return self.browser.script_evaluate(f"xsjs_probe.{function}({shown})")

    # Calls the probe until it returns a value other than null.
    def probe_wait(self, what: str, function: str, *args: object) -> object:
        while True:
            value = self.probe_call(function, *args)
            if value is not None:
                return value
            time.sleep(min(_POLL_SECONDS, self.log.timer.seconds_left(what)))

    # Opens the page, keeping where ttyd's log stood, and installs the probes.
    def page_open(self) -> None:
        self.mark = len(self.ttyd.lines)
        self.browser.page_open(self.url)
        self.browser.script_evaluate(_PROBE_KIT)

    # Opens the page and waits for the start to show the subtitle.
    def engine_open(self, subtitle: str) -> None:
        self.page_open()
        self.outcome_wait(subtitle)

    # Waits until the subtitle shows with the input open, failing on a fault.
    def outcome_wait(self, subtitle: str) -> None:
        found = json_object(
            self.probe_wait(f"the subtitle {subtitle!r}", "outcome", subtitle)
        )
        if "fault" in found:
            raise CheckFailed(
                f"the page faulted where {subtitle!r} was due: {found['fault']}"
            )

    # Waits for the fault screen and returns its text.
    def fault_wait(self, what: str) -> str:
        return cast(str, self.probe_wait(what, "fault"))

    # Fails if the page shows the fault screen.
    def fault_none(self, what: str) -> None:
        fault = self.probe_call("fault")
        if fault is not None:
            raise CheckFailed(f"{what}: the page faulted: {fault}")

    # Waits until every program the page started since its mark has ended.
    def programs_wait(self, least: int, what: str) -> int:
        return self.ttyd.programs_wait(self.mark, least, what)

    # Leaves the page for a blank one and waits for its programs to end.
    def page_leave(self) -> None:
        self.browser.page_open(_BLANK_URL)
        self.programs_wait(0, "the end of the programs of the page left")

    # Presses and releases a key, as the keyboard sends it.
    def key_press(self, stroke: KeyStroke) -> None:
        client = self.browser.client_get()
        fields: dict[str, Any] = {
            "modifiers": stroke.modifiers,
            "key": stroke.key,
            "code": stroke.code,
            "windowsVirtualKeyCode": stroke.key_code,
        }
        client.method_call(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "text": stroke.text, **fields},
        )
        client.method_call("Input.dispatchKeyEvent", {"type": "keyUp", **fields})

    # Types text into the focused element, as an input method sends it.
    def text_insert(self, text: str) -> None:
        self.browser.client_get().method_call(
            "Input.insertText", {"text": text}
        )

    # Clicks the left button at a point of the viewport.
    def mouse_click(self, x: float, y: float) -> None:
        client = self.browser.client_get()
        for kind in ("mousePressed", "mouseReleased"):
            client.method_call(
                "Input.dispatchMouseEvent",
                {"type": kind, "x": x, "y": y, "button": "left", "clickCount": 1},
            )

    # Clicks the middle of the box of an element's view.
    def view_click(self, view: dict[str, Any]) -> None:
        x = view["left"] + view["width"] / 2
        y = view["top"] + view["height"] / 2
        self.mouse_click(x, y)

    # Focuses an element and types the text into it.
    def text_type(self, selector: str, text: str) -> None:
        self.probe_call("focus", selector)
        self.text_insert(text)

    # Types the text into the player's input and presses Enter.
    def turn_send(self, text: str) -> None:
        self.text_type(_INPUT_SELECTOR, text)
        self.key_press(_KEY_ENTER)

    # Sends a turn and waits until it ends with the subtitle.
    def turn_run(self, text: str, ending: str) -> None:
        self.turn_send(text)
        self.outcome_wait(ending)

    # Types a command into the console and presses Enter.
    def command_type(self, command: str) -> None:
        self.text_type(_TERMINAL_INPUT, command)
        self.key_press(_KEY_ENTER)

    # Saves a PNG of the page under the name and returns its path.
    def shot_save(self, name: str) -> str:
        path = os.path.join(_PNG_PATH, name + ".png")
        self.browser.screenshot_save(path)
        return path

    # Adds a script every new document of the page runs first.
    def preload_add(self, source: str) -> str:
        result = self.browser.client_get().method_call(
            "Page.addScriptToEvaluateOnNewDocument", {"source": source}
        )
        return cast(str, result["identifier"])

    # Removes a script `preload_add` added.
    def preload_remove(self, identifier: str) -> None:
        self.browser.client_get().method_call(
            "Page.removeScriptToEvaluateOnNewDocument",
            {"identifier": identifier},
        )

    # Clicks the fault screen's Reload and waits for the new page to load.
    def reload_click(self, view: dict[str, Any]) -> None:
        events = self.browser.events
        seen = set(events.lifecycle)
        self.mark = len(self.ttyd.lines)
        self.view_click(view)
        self.browser.client_get().events_pump(
            "the reloaded page to load",
            lambda: any(
                name == _LOAD_EVENT and (loader, name) not in seen
                for loader, name in events.lifecycle
            ),
        )
        self.browser.script_evaluate(_PROBE_KIT)


# The parts every stage shares: the browser, the log, the pages and the stub.
class RunContext(NamedTuple):
    browser: BrowserDriver
    log: RungLog
    work: str
    stub: StubServer
    test_page: str
    engine_page: str
    closed_port: int


# A JSON value the page returned, as an object.
def json_object(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value)


# A JSON value the page returned, as an array.
def json_list(value: object) -> list[Any]:
    return cast(list[Any], value)


# The JSON text of a value as the wire and the page write it.
def json_text(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


# Returns the `SHA-256` of the bytes as 64 lowercase hex digits.
def sha256_text(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Returns the `SHA-256` of a file as 64 lowercase hex digits.
def file_sha256(path: str) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


# The bytes the probes' `pattern` makes: each index modulo the period.
def pattern_bytes(size: int) -> bytes:
    period = bytes(range(_PATTERN_PERIOD))
    return (period * (size // _PATTERN_PERIOD + 1))[:size]


# A pattern of a string's text in which each `_ANY` matches any text.
def pattern_make(text: str) -> re.Pattern[str]:
    escaped = re.escape(text).replace(re.escape(_ANY), "(.*)")
    return re.compile(escaped, re.DOTALL)


# The subtitle a new root shows: the seed's hyperposition's.
def seed_subtitle() -> str:
    with open(_HYPERPOSITION_PATH, encoding="utf-8") as file:
        document: dict[str, Any] = json.load(file)
    return cast(str, document["subtitle"])


# The file of a database under the root.
def database_path(root: str, db: str) -> str:
    return os.path.join(root, db + _DB_EXTENSION)


# A file's text, or nothing while it does not exist yet.
def file_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as file:
        return file.read()


# Copies each console message of the page to stderr.
def console_copy(text: str) -> None:
    sys.stderr.write(f"console: {text}\n")


# A port on the local host that nothing listens on.
def port_closed() -> int:
    with socket.socket() as sock:
        sock.bind((_LOCAL_HOST, 0))
        return cast(int, sock.getsockname()[1])


# The stroke of control and a digit, which the page keeps from the browser.
def digit_stroke(digit: int) -> KeyStroke:
    return KeyStroke(
        str(digit), f"Digit{digit}", _DIGIT_CODE + digit, _CONTROL_MODIFIER, ""
    )


# Returns the parent's pid, the second field after the name in brackets.
def process_parent(pid: int) -> int:
    with open(f"/proc/{pid}/stat", "rb") as file:
        stat = file.read()
    return int(stat[stat.rindex(b")") + 2 :].split()[1])


# Reads a process's resident size and its peak, in KiB, from its status file.
def memory_read(pid: int) -> MemoryUse:
    fields: dict[str, int] = {}
    with open(f"/proc/{pid}/status", encoding="utf-8") as file:
        for row in file:
            name, _, value = row.partition(":")
            if name in ("VmRSS", "VmHWM"):
                fields[name] = int(value.split()[0])
    return MemoryUse(fields["VmRSS"], fields["VmHWM"])


# Fails unless the pid is ttyd's child running its command.
def program_check(ttyd: TtydServer, pid: int) -> None:
    with open(f"/proc/{pid}/cmdline", "rb") as file:
        cmdline = file.read().split(b"\0")[:-1]
    due = [word.encode() for word in ttyd.command]
    if cmdline != due:
        raise CheckFailed(f"hello's pid {pid} runs {cmdline}, not {due}")
    parent = process_parent(pid)
    if parent != ttyd.process.pid:
        raise CheckFailed(
            f"hello's pid {pid} is the child of {parent}, not of ttyd's"
            f" {ttyd.process.pid}"
        )


# Whether a view's box is not empty and lies inside the viewport.
def box_inside(view: dict[str, Any], viewport: dict[str, Any]) -> bool:
    return (
        view["width"] > 0
        and view["height"] > 0
        and view["left"] >= 0
        and view["top"] >= 0
        and view["left"] + view["width"] <= viewport["width"]
        and view["top"] + view["height"] <= viewport["height"]
    )


# The rows of the console that hold text, their spaces trimmed.
def rows_filled(rows: list[Any]) -> list[str]:
    trimmed = [cast(str, row).replace(_NO_BREAK, " ").strip() for row in rows]
    return [row for row in trimmed if row]


# The last row of the console that holds text, or nothing before any text.
def row_last(rows: list[Any]) -> str:
    filled = rows_filled(rows)
    return filled[-1] if filled else ""


# Polls the views of the elements the selector names until `test` holds.
def views_wait(
    session: PageSession,
    what: str,
    selector: str,
    test: Callable[[list[dict[str, Any]]], bool],
) -> list[dict[str, Any]]:
    while True:
        found = json_list(session.probe_call("views", selector))
        views = [json_object(view) for view in found]
        if test(views):
            return views
        time.sleep(min(_POLL_SECONDS, session.log.timer.seconds_left(what)))


# Polls the console's rows until `test` holds.
def rows_wait(
    session: PageSession, what: str, test: Callable[[list[Any]], bool]
) -> list[Any]:
    while True:
        rows = json_list(session.probe_call("rows"))
        if test(rows):
            return rows
        time.sleep(min(_POLL_SECONDS, session.log.timer.seconds_left(what)))


# Polls a reading of the server until it gives a value other than None.
def server_wait[T](
    session: PageSession, what: str, read: Callable[[], T | None]
) -> T:
    while True:
        found = read()
        if found is not None:
            return found
        session.ttyd.log_poll()
        time.sleep(min(_POLL_SECONDS, session.log.timer.seconds_left(what)))


# Makes a root as the start script does, its settings changed as given.
def root_make(
    work: str, name: str, page: str, overrides: dict[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    root = os.path.join(work, name)
    python_path = os.path.join(root, "python")
    os.makedirs(python_path)
    for module in _RUNTIME_MODULES:
        file_name = module + ".py"
        shutil.copyfile(
            os.path.join(_PYTHON_PATH, file_name),
            os.path.join(python_path, file_name),
        )
    shutil.copytree(_SEED_PATH, os.path.join(python_path, "seed"))
    strings_path = os.path.join(root, "i18n")
    os.makedirs(strings_path)
    shutil.copyfile(_STRINGS_PATH, os.path.join(strings_path, "en-US.json"))
    with open(_SETTINGS_PATH, encoding="utf-8") as file:
        values: dict[str, Any] = json.load(file)
    values.update(overrides)
    text = json.dumps(values, ensure_ascii=False, indent=2) + "\n"
    with open(
        os.path.join(root, "settings.json"), "w", encoding="utf-8"
    ) as file:
        file.write(text)
    index = os.path.join(root, os.path.basename(page))
    shutil.copyfile(page, index)
    return root, index, values


# A provider tool call of the name with its arguments as JSON text.
def call_make(
    call_id: str, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json_text(arguments)},
    }


# A reply of the script that calls tools and moves to the node named.
def reply_calls(calls: list[dict[str, Any]], node: str) -> dict[str, Any]:
    return {"content": None, "tool_calls": calls, "next": node}


# A reply of the script that says the text and moves to the node named.
def reply_text(text: str, node: str) -> dict[str, Any]:
    return {"content": text, "next": node}


# The inputs that make one tool call each, by input.
def calls_make(values: dict[str, Any]) -> dict[str, ScriptCall]:
    over = values["overflow_bytes"] + 1
    return {
        _INPUT_RUN: ScriptCall(
            _PERMIT_TOOL,
            {"text": "echo " + _MARK_RUN, "timeout_seconds": _CONSOLE_SECONDS},
            _ENDING_RUN,
        ),
        _INPUT_TIMEOUT: ScriptCall(
            _PERMIT_TOOL,
            {"text": _SLEEP_COMMAND, "timeout_seconds": _SLEEP_SECONDS},
            _ENDING_TIMEOUT,
        ),
        _INPUT_DENY: ScriptCall(
            _PERMIT_TOOL,
            {
                "text": "echo " + _MARK_DENIED,
                "timeout_seconds": _CONSOLE_SECONDS,
            },
            _ENDING_DENY,
        ),
        _INPUT_LEVEL: ScriptCall(
            "browser.verbose_level", {"level": _TOOL_LEVEL}, _ENDING_LEVEL
        ),
        _INPUT_PAIRS: ScriptCall(
            _RUN_TOOL,
            {"name": _PAIRS_NAME, "args": {"db": _PAIRS_DB, "rows": _PAIRS_ROWS}},
            _ENDING_PAIRS,
        ),
        _INPUT_OVERFLOW: ScriptCall(
            _RUN_TOOL,
            {
                "name": _OVERFLOW_NAME,
                "args": {"ref": _OVERFLOW_REF, "size": over},
            },
            _ENDING_OVERFLOW,
        ),
        _INPUT_CACHE: ScriptCall(
            _RUN_TOOL,
            {
                "name": _CACHE_NAME,
                "args": {
                    "prefix": _CACHE_PREFIX,
                    "size": over,
                    "limit": _SCRIPT_LIMIT,
                },
            },
            _ENDING_CACHE,
        ),
        _INPUT_POOL: ScriptCall(
            _RUN_TOOL,
            {
                "name": _POOL_NAME,
                "args": {"prefix": _POOL_PREFIX, "limit": _SCRIPT_LIMIT},
            },
            _ENDING_POOL,
        ),
        _INPUT_HIDDEN: ScriptCall(
            _PERMIT_TOOL,
            {
                "text": "echo " + _MARK_HIDDEN,
                "timeout_seconds": _CONSOLE_SECONDS,
            },
            _ENDING_HIDDEN,
        ),
    }


# The provider script of every scripted root, the scripted turn its input 1.
def script_make(values: dict[str, Any]) -> dict[str, Any]:
    bootstrap = {
        "universe": _UNIVERSE,
        "title": _UNIVERSE_TITLE,
        "world": _WORLD,
        "region": _REGION,
    }
    scene = {
        "0": {"t": "scene"},
        "subtitle": _SCENE_SUBTITLE,
        "image": _IMAGE_REF,
    }
    entering = [
        call_make(
            "call_scene",
            "browser.doc_put",
            {"db": _REGION, "id": _SCENE_ID, "body": scene},
        ),
        call_make(
            "call_enter",
            "browser.kv_put",
            {"ref": f"/{_WORLD}/scene", "text": _SCENE_REF},
        ),
        call_make(
            "call_render",
            "browser.render",
            {"image": _IMAGE_REF, "subtitle": _SCENE_SUBTITLE},
        ),
    ]
    image = {"prompt": _IMAGE_PROMPT, "key": _IMAGE_KEY}
    replies: dict[str, Any] = {
        _INPUT_TURN: reply_calls(
            [
                call_make(
                    "call_bootstrap",
                    _RUN_TOOL,
                    {"name": _BOOTSTRAP_NAME, "args": bootstrap},
                )
            ],
            _NODE_BUILT,
        ),
        _INPUT_RESTART: reply_calls(
            [
                call_make(
                    "call_restart",
                    "server.system_restart",
                    {"main_loop": _RESTART_NAME},
                )
            ],
            _NODE_START,
        ),
        _INPUT_PLAIN: reply_text(_ENDING_PLAIN, _NODE_START),
    }
    nodes: dict[str, Any] = {
        _NODE_BUILT: {
            "replies": {},
            "after_tools": reply_calls(
                [call_make("call_image", "browser.image_make", image)],
                _NODE_IMAGED,
            ),
        },
        _NODE_IMAGED: {
            "replies": {},
            "after_tools": reply_calls(entering, _NODE_ENTERED),
        },
        _NODE_ENTERED: {
            "replies": {},
            "after_tools": reply_text(_SCENE_SUBTITLE, _NODE_START),
        },
    }
    for text, call in calls_make(values).items():
        node = "after_" + text
        made = call_make("call_" + text, call.tool, call.arguments)
        replies[text] = reply_calls([made], node)
        nodes[node] = {
            "replies": {},
            "after_tools": reply_text(call.ending, _NODE_START),
        }
    nodes[_NODE_START] = {"replies": replies}
    return {"start": _NODE_START, "nodes": nodes}


# Puts the provider script and the AI's scripts in a new root's `_files`.
def scripts_place(root: str, values: dict[str, Any]) -> None:
    import substrate

    items = {
        _SCRIPT_REF: json_text(script_make(values)).encode(),
        _AI_SCRIPT_PREFIX
        + _PAIRS_NAME
        + _AI_SCRIPT_EXTENSION: _PAIRS_SCRIPT.encode(),
        _AI_SCRIPT_PREFIX
        + _OVERFLOW_NAME
        + _AI_SCRIPT_EXTENSION: _OVERFLOW_SCRIPT.encode(),
        _AI_SCRIPT_PREFIX
        + _CACHE_NAME
        + _AI_SCRIPT_EXTENSION: _CACHE_SCRIPT.encode(),
        _AI_SCRIPT_PREFIX + _POOL_NAME + _AI_SCRIPT_EXTENSION: _POOL_SCRIPT.encode(),
    }
    store = substrate.Store(root, values["overflow_bytes"])
    store.db_create(_FILES_DB)
    try:
        for ref, data in items.items():
            store.kv_put(ref, data)
    finally:
        store.db_close(_FILES_DB)


# Copies a main loop file into the root's directory of main loop files.
def loop_place(root: str, source: str, name: str) -> None:
    directory = os.path.join(root, _MAIN_LOOP_DIRECTORY)
    os.makedirs(directory)
    shutil.copyfile(source, os.path.join(directory, name))


# Puts the scripts, and the stock main loop the restart rung names.
def restart_place(root: str, values: dict[str, Any]) -> None:
    scripts_place(root, values)
    loop_place(root, _MAIN_LOOP_PATH, _RESTART_NAME)


# Puts the main loop file whose `loop_prepare` never returns.
def stall_place(root: str, values: dict[str, Any]) -> None:
    loop_place(root, _STALL_LOOP_PATH, _STALL_LOOP_NAME)


# Puts the main loop file that serves `echo`.
def echo_place(root: str, values: dict[str, Any]) -> None:
    loop_place(root, _ECHO_LOOP_PATH, _ECHO_LOOP_NAME)


# Prepares nothing beyond what the start script makes.
def nothing_place(root: str, values: dict[str, Any]) -> None:
    pass


# The value the server holds under a ref, or None while it has none.
def value_read(session: PageSession, ref: str) -> bytes | None:
    import substrate

    parts = substrate.ref_split(ref)
    db = cast(str, parts.db)
    if not os.path.exists(database_path(session.root, db)):
        return None
    store = substrate.Store(session.root, session.values["overflow_bytes"])
    store.db_open(db)
    try:
        rows = store.kv_list(db, parts.key)
        held = any(row.key == parts.key for row in rows)
        value = store.kv_get(ref) if held else None
    finally:
        store.db_close(db)
    if value is None:
        return None
    if type(value.data) is str:
        with open(value.data, "rb") as file:
            return file.read()
    return cast(bytes, value.data)


# The text the server holds under a ref, or None while it has none.
def text_read(session: PageSession, ref: str) -> str | None:
    data = value_read(session, ref)
    return None if data is None else data.decode()


# The keys the server holds in a database under a prefix.
def keys_read(session: PageSession, db: str, prefix: str) -> list[str]:
    import substrate

    store = substrate.Store(session.root, session.values["overflow_bytes"])
    store.db_open(db)
    try:
        return [row.key for row in store.kv_list(db, prefix)]
    finally:
        store.db_close(db)


# The `seq` the server holds for a database.
def seq_read(session: PageSession, db: str) -> int:
    import substrate

    store = substrate.Store(session.root, session.values["overflow_bytes"])
    store.db_open(db)
    try:
        return store.seq_get(db)
    finally:
        store.db_close(db)


# The rows of a statement on the server's database, or None while it lacks it.
def rows_read(
    session: PageSession, db: str, sql: str, params: list[Any]
) -> list[list[Any]] | None:
    import substrate

    if not os.path.exists(database_path(session.root, db)):
        return None
    store = substrate.Store(session.root, session.values["overflow_bytes"])
    store.db_open(db)
    try:
        statement = substrate.SqlStatement(sql, params)
        return store.sql_run(db, [statement])[0].rows
    finally:
        store.db_close(db)


# The rows of the table of strings on the server, or None while it lacks it.
def pairs_read(session: PageSession) -> list[list[Any]] | None:
    tables = rows_read(
        session,
        _PAIRS_DB,
        "SELECT count(*) FROM sqlite_master WHERE name = ?",
        ["pair"],
    )
    if tables != [[1]]:
        return None
    return rows_read(
        session, _PAIRS_DB, "SELECT key, value FROM pair ORDER BY key", []
    )


# The messages of a scene's conversation on the server, in order.
def turns_read(session: PageSession, scene: str) -> list[dict[str, Any]]:
    import substrate

    db = cast(str, substrate.ref_split(scene).db)
    store = substrate.Store(session.root, session.values["overflow_bytes"])
    store.db_open(db)
    try:
        rows = store.turn_list(scene)
    finally:
        store.db_close(db)
    return [json_object(json.loads(row.content)) for row in rows]


# The conversation once its last message is the ending, else None.
def turns_ended(
    session: PageSession, scene: str, ending: str
) -> list[dict[str, Any]] | None:
    turns = turns_read(session, scene)
    if turns and turns[-1]["role"] == "assistant":
        if turns[-1]["content"] == ending:
            return turns
    return None


# The text of the last tool result of a turn that ended with the ending.
def tool_result(session: PageSession, scene: str, ending: str) -> str:
    turns = server_wait(
        session,
        f"the server's copy of the turn ending {ending!r}",
        lambda: turns_ended(session, scene, ending),
    )
    tools = [turn for turn in turns if turn["role"] == "tool"]
    return cast(str, tools[-1]["content"])


# The value a script returned in the last tool result of a turn.
def script_value(session: PageSession, scene: str, ending: str) -> Any:
    run = json_object(json.loads(tool_result(session, scene, ending)))
    if "error" in run:
        raise CheckFailed(f"the script threw: {run['error']}")
    return run["value"]


# Writes a value on the server behind the page's back, returns the new `seq`.
def seq_bump(session: PageSession, ref: str) -> int:
    import substrate

    db = cast(str, substrate.ref_split(ref).db)
    store = substrate.Store(session.root, session.values["overflow_bytes"])
    store.db_open(db)
    try:
        _, seq = store.kv_put(ref, b"1")
    finally:
        store.db_close(db)
    return seq


# Writes a new version of the hyperposition, enters it and returns its ref.
def scene_replace(session: PageSession, subtitle: str) -> str:
    import substrate

    store = substrate.Store(session.root, session.values["overflow_bytes"])
    store.db_open(_METAVERSE_DB)
    try:
        body: dict[int | str, Any] = {0: {"t": "scene"}, "subtitle": subtitle}
        ref, _ = store.doc_put(_METAVERSE_DB, "hyperposition", body)
        store.kv_put(f"/{_METAVERSE_DB}/scene", ref.encode())
    finally:
        store.db_close(_METAVERSE_DB)
    return ref


# The lines the server keeps of a page thread, in the order it kept them.
def verbose_read(session: PageSession, thread: str) -> list[VerboseRow]:
    path = os.path.join(session.root, _VERBOSE_FILE)
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT seq, at, level, text FROM line WHERE thread = ?"
            " ORDER BY seq",
            (thread,),
        ).fetchall()
    finally:
        connection.close()
    return [VerboseRow(int(a), int(b), int(c), str(d)) for a, b, c, d in rows]


# The AI's lines after the seq through the first of a rendered start.
def rendered_rows(session: PageSession, after: int) -> list[VerboseRow] | None:
    rows = [row for row in verbose_read(session, _AI_THREAD) if row.seq > after]
    for index, row in enumerate(rows):
        if _RENDERED_MARK in row.text:
            return rows[: index + 1]
    return None


# The seq of the AI's last line on the server.
def verbose_last(session: PageSession) -> int:
    return max(row.seq for row in verbose_read(session, _AI_THREAD))


# The text of a short name line with one blob of the size, its CR counted.
def line_length(line: Any) -> int:
    import jslb

    text = jslb.line_render(line).removesuffix(_BLOB_TAG)
    return len(text.encode("utf-8")) + 1


# The bytes of the `kv.get` reply's line for a value of the size.
def reply_length(reply_id: int, size: int) -> int:
    import jslb

    blob = jslb.Object()
    blob["s"] = size
    header = jslb.header_make("kv.get", reply=reply_id, full=False)
    line = jslb.line_make(header, [blob], size=size, sha256=_DIGEST_SHAPE)
    return line_length(line)


# The bytes of a `kv.put` request's line for a value of the size.
def put_length(request_id: int, ref: str, size: int, since: int) -> int:
    import jslb

    blob = jslb.Object()
    blob["s"] = size
    header = jslb.header_make("kv.put", id=request_id, key=ref, full=False)
    line = jslb.line_make(header, [blob], since=since)
    return line_length(line)


# The blob size that makes a line and its blob exactly the total.
def size_fit(total: int, length_of: Callable[[int], int], what: str) -> int:
    size = total - length_of(total)
    if length_of(size) + size != total:
        raise CheckFailed(f"no blob makes {what} exactly {total} bytes")
    return size


# The TAP documents of the file's whole lines, each from its version line.
def tap_documents(path: str, text: str) -> list[str]:
    documents: list[list[str]] = []
    whole = text[: text.rfind("\n") + 1]
    for line in whole.splitlines(keepends=True):
        if line == _TAP_VERSION + "\n":
            documents.append([])
        elif not documents:
            raise CheckFailed(f"{path} starts with {line!r}, not a version")
        documents[-1].append(line)
    return ["".join(lines) for lines in documents]


# The failing points, their diagnostics, bail outs and unknown lines.
def tap_failures(documents: list[str]) -> list[str]:
    import tap_consumer

    shown: list[str] = []
    for number, document in enumerate(documents, 1):
        kinds = tap_consumer.Parser().parse_text(document)
        following = False
        for text, kind in zip(document.splitlines(), kinds, strict=True):
            match kind:
                case tap_consumer.Result() if not kind.ok and not kind.todo:
                    following = True
                case tap_consumer.Diagnostic() if following:
                    pass
                case tap_consumer.Bail() | tap_consumer.Unknown():
                    following = False
                case _:
                    following = False
                    continue
            shown.append(f"document {number}: {text}")
    return shown


# Fails unless both documents are well formed and none has a failing point.
def tap_check(path: str, documents: list[str]) -> str:
    import tap_consumer

    stats = [tap_consumer.document_stats(document) for document in documents]
    shown = "; ".join(
        f"document {number}: plan {item.plan}, {item.passed} passed,"
        f" {item.failed} failed, {item.skipped} skipped,"
        f" {'well formed' if item.well_formed else 'not well formed'}"
        for number, item in enumerate(stats, 1)
    )
    if (
        len(documents) != _TAP_DOCUMENTS
        or not all(item.well_formed for item in stats)
        or any(item.failed for item in stats)
    ):
        failing = "\n".join(tap_failures(documents))
        raise CheckFailed(
            f"{path} holds {len(documents)} TAP documents where"
            f" {_TAP_DOCUMENTS} were due; {shown}; the failing lines:\n"
            f"{failing}"
        )
    return shown


# Runs the TypeScript suites on the test page and checks the TAP file.
def rung_suites(session: PageSession) -> str:
    import tap_consumer

    path = os.path.join(session.root, _TAP_FILE)
    session.page_open()
    documents: list[str] = []
    while not session.log.timer.timer_expired():
        session.ttyd.log_poll()
        documents = tap_documents(path, file_text(path))
        if len(documents) > _TAP_DOCUMENTS:
            break
        if (
            len(documents) == _TAP_DOCUMENTS
            and tap_consumer.document_stats(documents[-1]).well_formed
        ):
            break
        time.sleep(_POLL_SECONDS)
    shown = tap_check(path, documents)
    png = session.shot_save("stage0_typescript_suites")
    return (
        f"{path} holds the AI worker's TAP document, then the UI thread's,"
        f" both well formed with no failing point: {shown}; PNG {png}"
    )


# Opens the engine page anew once the last page's programs have ended.
def fault_page(session: PageSession, subtitle: str) -> None:
    session.page_leave()
    session.engine_open(subtitle)


# An error thrown after load replaces the page by the fault screen and stops.
def rung_thrown(session: PageSession, subtitle: str) -> str:
    fault_page(session, subtitle)
    session.probe_call("throw_later", _THROWN_MESSAGE)
    text = session.fault_wait("the fault screen of the thrown error")
    if _THROWN_MESSAGE not in text:
        raise CheckFailed(f"the fault screen shows {text!r}")
    if session.probe_call("image_kept") is not False:
        raise CheckFailed(
            "the page's #image is still there, where the fault screen of a"
            " fault after load replaces the document"
        )
    ended = session.programs_wait(1, "the stop function to end the engine")
    png = session.shot_save("stage0_thrown_error")
    return (
        f"an error thrown after the start showed {_THROWN_MESSAGE!r} with its"
        f" stack in the pre that replaced the document; then {ended} engine"
        f" program ended as the stop function closed the worker; PNG {png}"
    )


# A second fault leaves the first one alone on the screen.
def rung_first(session: PageSession) -> str:
    before = session.fault_wait("the fault screen")
    count = session.probe_call("overlay_again", _SECOND_MESSAGE)
    after = session.fault_wait("the fault screen after a second fault")
    if count != 1 or after != before:
        raise CheckFailed(
            f"after a second fault the page shows {count} pre, {after!r},"
            f" where the first fault's {before!r} alone was due"
        )
    return (
        f"overlay_show of {_SECOND_MESSAGE!r} after the first fault left the"
        " one pre and its text unchanged"
    )


# The fault screen's Reload starts the page again from the server.
def rung_reload(session: PageSession, subtitle: str) -> str:
    button = json_object(session.probe_wait("the Reload button", "reload_button"))
    if button["onclick"] != _RELOAD_CALL or not button["view"]["center_hit"]:
        raise CheckFailed(f"the Reload button is {button}")
    session.reload_click(json_object(button["view"]))
    session.outcome_wait(subtitle)
    session.fault_none("the reloaded page")
    return (
        f"a click on Reload, whose onclick is {_RELOAD_CALL!r}, loaded the page"
        f" again and its start showed {subtitle!r} with no fault"
    )


# A rejected promise nothing handles reaches the fault screen.
def rung_rejection(session: PageSession, subtitle: str) -> str:
    fault_page(session, subtitle)
    session.probe_call("reject_later", _REJECTED_MESSAGE)
    text = session.fault_wait("the fault screen of the rejection")
    if not text.startswith(_REJECTED_MESSAGE):
        raise CheckFailed(f"the fault screen shows {text!r}")
    session.programs_wait(1, "the stop function to end the engine")
    return (
        f"an unhandled rejection showed {_REJECTED_MESSAGE!r} on the fault"
        " screen and the engine program ended"
    )


# A resource that fails to load reaches the capture handler's fault text.
def rung_resource(
    session: PageSession,
    subtitle: str,
    tag: str,
    attributes: dict[str, str],
    due: str,
) -> str:
    fault_page(session, subtitle)
    session.probe_call("resource_add", tag, attributes)
    text = session.fault_wait(f"the fault screen of the {tag}")
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    session.programs_wait(1, "the stop function to end the engine")
    return (
        f"a {tag} with {json.dumps(attributes)} that failed to load showed"
        f" {due!r} on the fault screen and the engine program ended"
    )


# A worker that throws once its script ran posts its fault to the page.
def rung_posted(session: PageSession) -> str:
    session.page_leave()
    suffix = f"\nthrow new Error({json.dumps(_POSTED_MESSAGE)});\n"
    identifier = session.preload_add(blob_patch("", suffix))
    session.page_open()
    text = session.fault_wait("the fault the worker posts")
    session.preload_remove(identifier)
    session.programs_wait(0, "the end of the worker's programs")
    if "Error: " + _POSTED_MESSAGE not in text.split("\n"):
        raise CheckFailed(
            f"the fault screen shows {text!r}, where the worker's posted"
            f" fault with its stack line 'Error: {_POSTED_MESSAGE}' was due"
        )
    return (
        "the worker's script, run from its Blob URL, threw at its end after"
        " error_overlay was installed in it, and the page showed the posted"
        f" fault {_POSTED_MESSAGE!r} with the worker's stack"
    )


# A worker that throws before anything ran reaches the page's `onerror`.
def rung_load(session: PageSession) -> str:
    import i18n

    session.page_leave()
    prefix = f"throw new Error({json.dumps(_LOAD_MESSAGE)});\n"
    identifier = session.preload_add(blob_patch(prefix, ""))
    session.page_open()
    text = session.fault_wait("the fault of the worker's load")
    session.preload_remove(identifier)
    session.programs_wait(0, "the end of the worker's programs")
    where = pattern_make(i18n.i18n("page.worker_where", _ANY, _ANY, _ANY))
    lines = text.split("\n")
    if _LOAD_MESSAGE not in lines[0] or not any(
        where.fullmatch(line) for line in lines[1:]
    ):
        raise CheckFailed(
            f"the fault screen shows {text!r}, where {_LOAD_MESSAGE!r} and"
            " the worker's file, line and column were due"
        )
    return (
        "the worker's Blob script threw on its first line, before any"
        f" handler, and the page's onerror showed {_LOAD_MESSAGE!r} with"
        f" {lines[1]!r}"
    )


# A fault while the parser runs a script is appended, not replacing the page.
def rung_append(session: PageSession) -> str:
    session.page_leave()
    source = _WORKER_THROW.replace(
        "XSJS_MESSAGE", json.dumps(_APPEND_MESSAGE)
    )
    identifier = session.preload_add(source)
    session.page_open()
    text = session.fault_wait("the fault of the start script")
    session.preload_remove(identifier)
    if _APPEND_MESSAGE not in text:
        raise CheckFailed(f"the fault screen shows {text!r}")
    if session.probe_call("image_kept") is not True:
        raise CheckFailed(
            "the fault while the parser ran replaced the document, where"
            " document.write appends while a script of the parser runs"
        )
    png = session.shot_save("stage0_fault_appended")
    return (
        f"the worker constructor threw {_APPEND_MESSAGE!r} inside the start"
        " script while the parser ran it: the fault's pre was appended and"
        " the page's #image stayed, where a fault after load replaces the"
        f" document; PNG {png}"
    )


# The preload that adds the prefix and suffix to every script `Blob`.
def blob_patch(prefix: str, suffix: str) -> str:
    return _BLOB_PATCH.replace("XSJS_PREFIX", json.dumps(prefix)).replace(
        "XSJS_SUFFIX", json.dumps(suffix)
    )


# The page answers before any render: the input shows, closed.
def rung_idle(session: PageSession) -> str:
    session.page_open()
    view = json_object(session.probe_call("view", _INPUT_SELECTOR))
    if view["hidden"] or not view["center_hit"] or not view["disabled"]:
        raise CheckFailed(f"#input before the first render is {view}")
    png = session.shot_save("stage5_input_before_render")
    return (
        "on the engine page with no worker, #input before any render is"
        f" disabled and its centre hits #input; PNG {png}"
    )


# The wire port's hello: from ttyd's child, with the root's facts.
def rung_hello(session: PageSession) -> str:
    session.probe_call("wire_open", "first", session.url)
    hello = json_object(session.probe_wait("hello", "wire_hello", "first"))
    path = session.ttyd.command[1]
    due: dict[str, Any] = {
        "bootstrap": path,
        "sha256": file_sha256(path),
        "root": session.root,
        "settings": session.values,
        "provider_key": "",
    }
    wrong = [name for name, value in due.items() if hello[name] != value]
    if wrong:
        raise CheckFailed(f"hello's {wrong} differ: {json.dumps(hello)}")
    pid = cast(int, hello["pid"])
    program_check(session.ttyd, pid)
    return (
        f"a WirePort on the page's main thread got hello from pid {pid},"
        " ttyd's child, with bootstrap.py's path and sha256, the root, its"
        f" settings, seq {hello['seq']} and an empty provider key, and"
        " answered it"
    )


# A `message_max` reply comes back equal by `SHA-256`, sized by the reply.
def rung_round(session: PageSession) -> str:
    message_max: int = session.values["message_max"]
    hello = json_object(session.probe_call("wire_hello", "first"))
    since = cast(int, hello["seq"][_FILES_DB])
    size = size_fit(
        message_max,
        lambda count: reply_length(_GET_ID, count),
        "the reply to kv.get",
    )
    digest = sha256_text(pattern_bytes(size))
    session.probe_call("kv_put", "first", _PUT_ID, _ROUND_REF, size, since)
    lines = json_list(
        session.probe_wait("the reply to kv.put", "wire_lines", "first", 1)
    )
    put_due = {
        "header": {"t": "kv.put", "r": _PUT_ID},
        "payload": {"sha256": digest, "seq": since + 1},
        "blobs": [],
    }
    if lines[0] != put_due:
        raise CheckFailed(f"kv.put got {lines[0]}, not {put_due}")
    options = {"id": _GET_ID, "key": _ROUND_REF}
    session.probe_call("wire_send", "first", "kv.get", options, {})
    lines = json_list(
        session.probe_wait("the reply to kv.get", "wire_lines", "first", 2)
    )
    get_due = {
        "header": {"t": "kv.get", "r": _GET_ID, "b": 1},
        "payload": {"size": size, "sha256": digest},
        "blobs": [{"size": size, "sha256": digest}],
    }
    if lines[1] != get_due:
        raise CheckFailed(f"kv.get got {lines[1]}, not {get_due}")
    sent = put_length(_PUT_ID, _ROUND_REF, size, since) + size
    return (
        f"kv.put of {size} bytes, a message of {sent} bytes, then kv.get"
        f" whose reply is message_max {message_max} bytes, line and blob,"
        f" streamed into the page's sink: equal by sha256 {digest[:12]}"
    )


# The page's wire port refuses to post a message one byte over the limit.
def rung_over(session: PageSession) -> str:
    import i18n

    message_max: int = session.values["message_max"]
    hello = json_object(session.probe_call("wire_hello", "first"))
    since = cast(int, hello["seq"][_FILES_DB]) + 1
    size = size_fit(
        message_max + 1,
        lambda count: put_length(_OVER_ID, _ROUND_REF, count, since),
        "the kv.put",
    )
    message = session.probe_call(
        "put_refused", "first", _OVER_ID, _ROUND_REF, size, since
    )
    due = i18n.i18n("wire.message_over", "kv.put", message_max + 1, message_max)
    if message != due:
        raise CheckFailed(f"line_post threw {message!r}, not {due!r}")
    return (
        f"line_post of a kv.put of {message_max + 1} bytes threw {due!r}"
        " before anything was sent"
    )


# `wire_close` ends the server and reports no close.
def rung_close(session: PageSession) -> str:
    session.probe_call("wire_close", "first")
    ended = session.programs_wait(1, "the end of the closed program")
    closes = session.probe_call("wire_closes", "first")
    if closes is not None:
        raise CheckFailed(f"the close receiver got {closes}")
    session.fault_none("wire_close")
    return (
        f"wire_close closed the socket with 1000, {ended} program ended, the"
        " close receiver was not called and no fault came"
    )


# An `error` line and the server's end are reported as a close with an error.
def rung_error(session: PageSession) -> str:
    import i18n

    session.probe_call("wire_open", "second", session.url)
    session.probe_wait("hello", "wire_hello", "second")
    options = {"id": _UNKNOWN_ID}
    session.probe_call("wire_send", "second", _UNKNOWN_TYPE, options, {})
    closes = session.probe_wait("the close", "wire_closes", "second")
    lines = json_list(session.probe_call("wire_lines", "second", 1))
    error = json_object(lines[0])
    message = i18n.i18n("dispatch.handler_unknown", _UNKNOWN_TYPE, 0)
    if (
        len(lines) != 1
        or error["header"] != {"t": "error", "r": _UNKNOWN_ID}
        or list(error["payload"]) != ["message", "stack"]
        or error["payload"]["message"] != message
        or closes != [[_CLOSE_LOST, True]]
    ):
        raise CheckFailed(f"the page got {lines} and the closes {closes}")
    session.fault_none("a close after an error line")
    session.programs_wait(2, "the end of both programs")
    return (
        f"{_UNKNOWN_TYPE} gave the error {message!r} to the line receiver,"
        f" then the close receiver got {_CLOSE_LOST} with the error noted,"
        " and the page did not fault"
    )


# A reply one byte over the limit is the page decoder's fault, closing it.
def rung_decoder(session: PageSession) -> str:
    import i18n

    message_max: int = session.values["message_max"]
    session.page_leave()
    session.page_open()
    session.probe_call("wire_open", "third", session.url)
    hello = json_object(session.probe_wait("hello", "wire_hello", "third"))
    since = cast(int, hello["seq"][_FILES_DB])
    size = (
        size_fit(
            message_max,
            lambda count: reply_length(_GET_ID, count),
            "the reply to kv.get",
        )
        + 1
    )
    if reply_length(_GET_ID, size) + size != message_max + 1:
        raise CheckFailed(f"no reply of a {size} byte value is one byte over")
    session.probe_call("kv_put", "third", _PUT_ID, _ROUND_REF, size, since)
    session.probe_wait("the reply to kv.put", "wire_lines", "third", 1)
    options = {"id": _GET_ID, "key": _ROUND_REF}
    session.probe_call("wire_send", "third", "kv.get", options, {})
    text = session.fault_wait("the decoder's fault")
    due = i18n.i18n("jslb.message_over", message_max + 1, message_max)
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    session.programs_wait(1, "the end of the program of the closed port")
    return (
        f"a kv.get reply of {message_max + 1} bytes: the page's decoder"
        f" faulted with {due!r} at its CR, the port closed and the server"
        " ended"
    )


# A server that ends with no `error` line is a fault naming the close code.
def rung_silent(session: PageSession) -> str:
    import i18n

    session.page_leave()
    session.page_open()
    session.probe_call("wire_open", "fourth", session.url)
    hello = json_object(session.probe_wait("hello", "wire_hello", "fourth"))
    pid = cast(int, hello["pid"])
    os.kill(pid, signal.SIGKILL)
    text = session.fault_wait("the fault of the silent close")
    due = i18n.i18n("wire.close_silent", _CLOSE_LOST)
    closes = session.probe_call("wire_closes", "fourth")
    if due not in text or closes != [[_CLOSE_LOST, False]]:
        raise CheckFailed(
            f"the fault screen shows {text!r} and the closes {closes}"
        )
    session.programs_wait(1, "the end of the killed program")
    return (
        f"SIGKILL to pid {pid}: the close receiver got {_CLOSE_LOST} with no"
        f" error line, then the page faulted with {due!r}"
    )


# The reply of an HTTP port's request, waiting for the count of lines.
def port_lines(
    session: PageSession, name: str, count: int
) -> list[dict[str, Any]]:
    lines = session.probe_wait(
        f"{count} lines of the port {name}", "lines_when", name, count
    )
    return [json_object(line) for line in json_list(lines)]


# Sends one GET of an HTTP port with the id.
def get_send(session: PageSession, name: str, line_id: int, url: str) -> None:
    payload = {"method": "GET", "url": url, "headers": {}}
    session.probe_call("request_send", name, _HTTP_TYPE, line_id, payload, [])


# The POST carries its exact body and headers and gets its JSON back.
def rung_post(session: PageSession, stub: StubServer) -> str:
    session.probe_call("http_port", "post", _HTTP_SECONDS)
    url = stub.url_make(_ECHO_PATH)
    payload = {
        "method": "POST",
        "url": url,
        "headers": _POST_HEADERS,
        "json": _POST_JSON,
    }
    session.probe_call("request_send", "post", _HTTP_TYPE, 1, payload, [])
    reply = port_lines(session, "post", 1)[0]
    if (
        reply["header"] != {"t": _HTTP_TYPE, "r": 1}
        or reply["payload"]["status"] != _HTTP_OK
        or reply["payload"]["json"] != _ECHO_ANSWER
    ):
        raise CheckFailed(f"the POST got {reply}")
    _, request = stub.request_find("POST", _ECHO_PATH)
    body = json_text(_POST_JSON).encode()
    sent = {name: request.headers.get(name) for name in _POST_HEADERS}
    if request.body != body or sent != _POST_HEADERS:
        raise CheckFailed(
            f"the stub took {request.body!r} with {sent}, not {body!r} with"
            f" {_POST_HEADERS}"
        )
    return (
        f"the POST arrived with its {len(body)} body bytes and its headers"
        f" exactly, and its reply carried status {_HTTP_OK} and the JSON"
    )


# The cross origin POST was preceded by its CORS preflight.
def rung_preflight(stub: StubServer) -> str:
    asked_at, asked = stub.request_find("OPTIONS", _ECHO_PATH)
    posted_at, _ = stub.request_find("POST", _ECHO_PATH)
    method = asked.headers.get("access-control-request-method")
    named = asked.headers.get("access-control-request-headers", "")
    headers = {name.strip() for name in named.split(",")}
    if asked_at > posted_at or method != "POST" or not set(_POST_HEADERS) <= headers:
        raise CheckFailed(
            f"the preflight came at {asked_at}, the POST at {posted_at},"
            f" asking {method} with {named!r}"
        )
    return (
        f"an OPTIONS preflight asking POST with {named!r} came before the"
        " POST, and its answer let the POST through"
    )


# A text answer gives `text`, a JSON answer `json`.
def rung_answers(session: PageSession, stub: StubServer) -> str:
    session.probe_call("http_port", "plain", _HTTP_SECONDS)
    get_send(session, "plain", 1, stub.url_make(_TEXT_PATH))
    get_send(session, "plain", 2, stub.url_make(_JSON_PATH))
    lines = port_lines(session, "plain", 2)
    by_id = {line["header"]["r"]: line["payload"] for line in lines}
    text, value = by_id[1], by_id[2]
    if (
        text["status"] != _HTTP_OK
        or text["text"] != _PLAIN_TEXT
        or "json" in text
        or value["status"] != _HTTP_OK
        or value["json"] != _JSON_VALUE
        or "text" in value
    ):
        raise CheckFailed(f"the answers were {lines}")
    return (
        f"text/plain gave text {_PLAIN_TEXT!r} and application/json gave the"
        " parsed JSON"
    )


# The statuses 400, 401 and 500 are `error` lines naming the body.
def rung_statuses(session: PageSession, stub: StubServer) -> str:
    import i18n

    session.probe_call("http_port", "status", _HTTP_SECONDS)
    for line_id, status in enumerate(_STATUSES, 1):
        url = stub.url_make(f"{_STATUS_PREFIX}{status}")
        get_send(session, "status", line_id, url)
    lines = port_lines(session, "status", len(_STATUSES))
    by_id = {line["header"]["r"]: line for line in lines}
    for line_id, status in enumerate(_STATUSES, 1):
        url = stub.url_make(f"{_STATUS_PREFIX}{status}")
        due = i18n.i18n("http.status_failed", url, status, f"status {status}")
        line = by_id[line_id]
        if line["header"]["t"] != "error" or line["payload"]["message"] != due:
            raise CheckFailed(f"status {status} gave {line}, not {due!r}")
    return f"the statuses {_STATUSES} each gave an error line naming the body"


# A closed port is an `error` line of the failed fetch.
def rung_refused(session: PageSession, closed_port: int) -> str:
    import i18n

    session.probe_call("http_port", "closed", _HTTP_SECONDS)
    url = f"http://{_LOCAL_HOST}:{closed_port}/"
    get_send(session, "closed", 1, url)
    line = port_lines(session, "closed", 1)[0]
    pattern = pattern_make(i18n.i18n("http.fetch_failed", url, _ANY))
    message = cast(str, line["payload"].get("message", ""))
    if line["header"] != {"t": "error", "r": 1} or not pattern.fullmatch(
        message
    ):
        raise CheckFailed(f"the closed port gave {line}")
    return f"a GET of the closed port {closed_port} gave {message!r}"


# A server that never answers is a timeout `error` line.
def rung_never(session: PageSession, stub: StubServer) -> str:
    import i18n

    session.probe_call("http_port", "silent", _HTTP_SECONDS)
    url = stub.url_make(_SILENT_PATH)
    get_send(session, "silent", 1, url)
    line = port_lines(session, "silent", 1)[0]
    due = i18n.i18n("http.timeout_expired", url, _HTTP_SECONDS)
    if line["header"] != {"t": "error", "r": 1} or line["payload"][
        "message"
    ] != due:
        raise CheckFailed(f"the silent server gave {line}, not {due!r}")
    return f"a server that never answered gave {due!r}"


# A body that stalls after its head is a timeout `error` line.
def rung_stall(session: PageSession, stub: StubServer) -> str:
    import i18n

    session.probe_call("http_port", "stall", _HTTP_SECONDS)
    url = stub.url_make(_STALL_PATH)
    get_send(session, "stall", 1, url)
    line = port_lines(session, "stall", 1)[0]
    due = i18n.i18n("http.timeout_expired", url, _HTTP_SECONDS)
    if line["header"] != {"t": "error", "r": 1} or line["payload"][
        "message"
    ] != due:
        raise CheckFailed(f"the stalled body gave {line}, not {due!r}")
    return (
        f"a body stalled after {len(_PLAIN_TEXT)} of {_STALL_LENGTH} bytes"
        f" gave {due!r}"
    )


# After a timeout the port gives no second line for that request.
def rung_single(session: PageSession, stub: StubServer) -> str:
    for name in ("silent", "stall"):
        get_send(session, name, 2, stub.url_make(_TEXT_PATH))
        lines = port_lines(session, name, 2)
        ids = [line["header"]["r"] for line in lines]
        if ids != [1, 2]:
            raise CheckFailed(f"the port {name} gave lines for {ids}")
    return (
        "on both timed out ports a later request's reply came, and each port"
        " gave exactly one line for its timed out request"
    )


# Replies arriving in reverse order each answer their own request.
def rung_order(session: PageSession, stub: StubServer) -> str:
    session.probe_call("http_port", "order", _HTTP_SECONDS)
    for number in range(_ORDER_COUNT):
        url = stub.url_make(f"{_ORDER_PREFIX}{number}")
        get_send(session, "order", number + 1, url)
    lines = port_lines(session, "order", _ORDER_COUNT)
    came = [(line["header"]["r"], line["payload"]["json"]["n"]) for line in lines]
    due = [(number + 1, number) for number in reversed(range(_ORDER_COUNT))]
    answered = stub.answers_list(_ORDER_PREFIX)
    sent = [
        f"{_ORDER_PREFIX}{number}" for number in reversed(range(_ORDER_COUNT))
    ]
    if came != due or answered != sent:
        raise CheckFailed(f"the replies came as {came}, answered {answered}")
    return (
        f"{_ORDER_COUNT} requests answered last first came back in that order,"
        " each reply's r its request's i"
    )


# A GET with a body is refused by the browser, an `error` line.
def rung_body(session: PageSession, stub: StubServer) -> str:
    import i18n

    session.probe_call("http_port", "body", _HTTP_SECONDS)
    url = stub.url_make(_TEXT_PATH)
    payload = {"method": "GET", "url": url, "headers": {}, "body": _GET_BODY}
    session.probe_call("request_send", "body", _HTTP_TYPE, 1, payload, [])
    line = port_lines(session, "body", 1)[0]
    pattern = pattern_make(i18n.i18n("http.fetch_failed", url, _ANY))
    message = cast(str, line["payload"].get("message", ""))
    if line["header"] != {"t": "error", "r": 1} or not pattern.fullmatch(
        message
    ):
        raise CheckFailed(f"the GET with a body gave {line}")
    return f"a GET with a body gave {message!r}"


# The HTTP port works inside a worker made from the bundle.
def rung_worker(session: PageSession, stub: StubServer) -> str:
    session.probe_call("worker_http", stub.url_make(_JSON_PATH), _HTTP_SECONDS)
    lines = json_list(session.probe_wait("the worker's reply", "worker_when"))
    reply = json_object(lines[0])
    if (
        reply["header"] != {"t": _HTTP_TYPE, "r": 1}
        or reply["payload"]["json"] != _JSON_VALUE
    ):
        raise CheckFailed(f"the worker's port gave {reply}")
    return "an HttpPort in a worker of the bundle fetched the JSON and replied"


# A receiver that throws reaches the fault screen as a rejection.
def rung_receiver(session: PageSession, stub: StubServer) -> str:
    session.probe_call(
        "receiver_throw",
        stub.url_make(_TEXT_PATH),
        _RECEIVER_MESSAGE,
        _HTTP_SECONDS,
    )
    text = session.fault_wait("the fault of the throwing receiver")
    if _RECEIVER_MESSAGE not in text:
        raise CheckFailed(f"the fault screen shows {text!r}")
    return f"a receiver that threw {_RECEIVER_MESSAGE!r} reached the fault screen"


# A queue in its normal mode runs one item per task, after the notify.
def rung_schedule(session: PageSession) -> str:
    session.probe_call("schedule_run", "rung_schedule.step")
    order = session.probe_wait("the two items", "order_when", 5)
    due = ["returned", 1, "micro 1", 2, "micro 2"]
    if order != due:
        raise CheckFailed(f"the queue ran {order}, not {due}")
    return (
        "two notified items ran after the notify returned, each in a task of"
        " its own, the first one's microtask before the second item"
    )


# A ThreadPort carries a request and its reply across a real worker.
def rung_thread(session: PageSession) -> str:
    session.probe_call("thread_run", "rung_thread.begin", "rung_thread.done")
    replies = json_list(session.probe_wait("the worker's reply", "thread_when"))
    due = [
        {
            "header": {"t": "probe.ask", "r": 1},
            "payload": {"text": "across", "thread": "probe"},
            "blobs": [],
        }
    ]
    if replies != due:
        raise CheckFailed(f"the wake carried {replies}, not {due}")
    return (
        "a task slept on a request to a worker's queue over ThreadPort and"
        " woke with its reply"
    )


# A task sleeping on two requests wakes with both, in submit order.
def rung_pair(session: PageSession, stub: StubServer) -> str:
    urls = [stub.url_make(_FIRST_PATH), stub.url_make(_SECOND_PATH)]
    session.probe_call(
        "pair_run", "rung_pair.begin", "rung_pair.done", urls, _HTTP_SECONDS
    )
    replies = json_list(session.probe_wait("the wake of two", "pair_when"))
    came = [
        (json_object(reply)["header"]["r"], json_object(reply)["payload"]["json"])
        for reply in replies
    ]
    due = [(1, {"name": "first"}), (2, {"name": "second"})]
    answered = stub.answers_list("/pair/")
    if came != due or answered != [_SECOND_PATH, _FIRST_PATH]:
        raise CheckFailed(f"the wake carried {came}, answered {answered}")
    return (
        "the second request was answered first and the sleeping task woke"
        " once both had come, its replies in submit order"
    )


# A handler that throws reaches the fault screen.
def rung_handler(session: PageSession) -> str:
    session.page_leave()
    session.page_open()
    session.probe_call("handler_throw", "rung_handler.boom", _HANDLER_MESSAGE)
    text = session.fault_wait("the fault of the throwing handler")
    if _HANDLER_MESSAGE not in text:
        raise CheckFailed(f"the fault screen shows {text!r}")
    return f"a handler that threw {_HANDLER_MESSAGE!r} reached the fault screen"


# Polls the record of the probe's console port until `test` holds.
def console_wait(
    session: PageSession, what: str, test: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    while True:
        record = json_object(session.probe_call("console_state"))
        if test(record):
            return record
        time.sleep(min(_POLL_SECONDS, session.log.timer.seconds_left(what)))


# The text of tty 0's output in the probe's console record from a line on.
def output_text(record: dict[str, Any], begun: int) -> str:
    return "".join(
        cast(str, line["text"])
        for line in record["lines"][begun:]
        if line["kinds"] == [_OUTPUT_KIND]
    )


# Opens tty 0 on the probe's port, sends the token, waits for the prompt.
def console_start(session: PageSession, request_id: int) -> None:
    import jslb

    begun = len(json_object(session.probe_call("console_state"))["lines"])
    session.probe_call("console_ask", request_id)
    due = jslb.header_make(
        "console.open", reply=request_id, full=session.values["debug"]
    )
    record = console_wait(
        session,
        f"the reply to console.open {request_id}",
        lambda record: any(
            line["header"] == due for line in record["lines"][begun:]
        ),
    )
    reply = next(
        line for line in record["lines"][begun:] if line["header"] == due
    )
    first = {
        "AuthToken": reply["payload"]["token"],
        "columns": _PROBE_COLUMNS,
        "rows": _PROBE_ROWS,
    }
    session.probe_call("console_send", json_text(first))
    console_wait(
        session,
        f"dash's prompt on console {request_id}",
        lambda record: output_text(record, begun).endswith(_PROMPT_TEXT),
    )


# Waits for the probe's console port to report its count of closes.
def console_closed(session: PageSession, count: int) -> int:
    record = console_wait(
        session,
        f"close {count} of the console port",
        lambda record: len(record["closes"]) >= count,
    )
    return cast(int, record["closes"][count - 1])


# A console port opens again after this side closed it and after `exit`.
def rung_cycle(session: PageSession) -> str:
    session.page_leave()
    session.page_open()
    debug: bool = session.values["debug"]
    session.probe_call("console_debug", session.url, debug)
    console_start(session, 1)
    mark = len(session.ttyd.lines)
    session.probe_call("console_shut")
    shut = console_closed(session, 1)
    _, killed = session.ttyd.line_wait(
        _ENDED_PATTERN, "the first console's end", mark
    )
    console_start(session, 2)
    mark = len(session.ttyd.lines)
    session.probe_call("console_send", _INPUT_KIND + _EXIT_COMMAND + "\r")
    exited = console_closed(session, 2)
    _, ended = session.ttyd.line_wait(
        _ENDED_PATTERN, "the second console's end", mark
    )
    if ended.group(1, 2) != (_EXITED_WORDS, "0"):
        raise CheckFailed(f"{session.ttyd.version} logged: {ended.string}")
    console_start(session, 3)
    session.probe_call("console_shut")
    last = console_closed(session, 3)
    started = session.programs_wait(3, "the end of the three consoles")
    closes = json_object(session.probe_call("console_state"))["closes"]
    if started != 3 or len(closes) != 3:
        raise CheckFailed(
            f"ttyd started {started} consoles and the port got the closes"
            f" {closes}, where three of each were due"
        )
    session.fault_none("the console port opened three times")
    return (
        "one ConsolePort on the page opened tty 0 and dash prompted; closed"
        f" from this side, its close receiver got {shut} and ttyd logged"
        f" {killed.group(1)} {killed.group(2)}; opened again, exit ended dash"
        f" with code 0 and the receiver got {exited}; opened a third time"
        f" dash prompted, and closed it gave {last}"
    )


# The wire port's wait for a token that never comes runs out.
def rung_token(session: PageSession, stub: StubServer) -> str:
    import i18n

    session.page_leave()
    session.page_open()
    session.probe_call("wire_open", "held", stub.url_make(_HELD_BASE))
    text = session.fault_wait("the fault of the wait for the token")
    url = stub.url_make(_HELD_BASE + _TOKEN_PATH)
    what = i18n.i18n("wire.what_token", url)
    due = i18n.i18n("wire.wait_expired", _WIRE_SECONDS, what)
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    stub.request_find("GET", _HELD_BASE + _TOKEN_PATH)
    return (
        f"a WirePort aimed at a server that took GET {url} and never"
        f" answered faulted with {due!r}"
    )


# The wire port's wait for a socket that never opens runs out.
def rung_opening(session: PageSession, stub: StubServer) -> str:
    import i18n

    session.page_leave()
    session.page_open()
    session.probe_call("wire_open", "opening", stub.url_make(_OPENING_BASE))
    text = session.fault_wait("the fault of the wait for the open")
    url = stub.socket_make(_OPENING_BASE + _SOCKET_PATH)
    what = i18n.i18n("wire.what_open", url)
    due = i18n.i18n("wire.wait_expired", _WIRE_SECONDS, what)
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    _, request = stub.request_find("GET", _OPENING_BASE + _SOCKET_PATH)
    upgrade = request.headers.get("upgrade")
    if upgrade != "websocket":
        raise CheckFailed(f"the held request asked the upgrade {upgrade!r}")
    return (
        f"a WirePort that got the token {_STUB_TOKEN!r} and asked {url} for"
        f" a WebSocket the server never answered faulted with {due!r}"
    )


# A console socket that closes before it opens is the port's fault.
def rung_closing(session: PageSession, stub: StubServer) -> str:
    import i18n

    session.page_leave()
    session.page_open()
    debug: bool = session.values["debug"]
    base = stub.url_make(_CLOSING_BASE)
    session.probe_call("console_debug", base, debug)
    session.probe_call("console_ask", 1)
    text = session.fault_wait("the fault of the socket closed unopened")
    url = stub.socket_make(_CLOSING_BASE + _CONSOLE_PATH)
    due = i18n.i18n("wire.open_closed", url, _CLOSE_LOST)
    closes = json_object(session.probe_call("console_state"))["closes"]
    if due not in text or closes != []:
        raise CheckFailed(
            f"the fault screen shows {text!r} and the close receiver got"
            f" {closes}, where {due!r} and no close were due"
        )
    stub.request_find("GET", _CLOSING_BASE + _CONSOLE_PATH)
    return (
        f"a ConsolePort that got the token {_STUB_TOKEN!r} from a server that"
        f" then dropped the upgrade of {url} unanswered faulted with {due!r}"
        " and did not call its close receiver"
    )


# A PNG stored is decoded and kept at its own size.
def rung_store(session: PageSession, png: bytes, budget: int) -> str:
    key = "/_files/rung/stored.png"
    session.probe_call("media_port", "store", budget, _MEDIA_SECONDS)
    session.probe_call(
        "request_send", "store", "media.store", 1, {"k": key}, [list(png)]
    )
    reply = port_lines(session, "store", 1)[0]
    due = {
        "header": {"t": "media.store", "r": 1},
        "payload": {"k": key, "size": len(png), "sha256": sha256_text(png)},
        "blobs": [],
    }
    size = session.probe_call("image_size", "store", key)
    width, height = png_size(png)
    if reply != due or size != {"width": width, "height": height}:
        raise CheckFailed(f"media.store gave {reply} and kept {size}")
    return (
        f"the provider's {len(png)} byte PNG was decoded and kept as"
        f" {width}x{height}, its reply naming its size and sha256"
    )


# The width and height of a PNG from its header chunk.
def png_size(png: bytes) -> tuple[int, int]:
    return int.from_bytes(png[16:20]), int.from_bytes(png[20:24])


# A download is kept and replied with its bytes as blob 1.
def rung_fetch(session: PageSession, stub: StubServer, png: bytes, budget: int) -> str:
    key = "/_files/rung/fetched.png"
    session.probe_call("media_port", "fetch", budget, _MEDIA_SECONDS)
    payload = {"url": stub.url_make(_PNG_STUB_PATH), "k": key}
    session.probe_call("request_send", "fetch", "media.fetch", 1, payload, [])
    reply = port_lines(session, "fetch", 1)[0]
    digest = sha256_text(png)
    due = {
        "header": {"t": "media.fetch", "r": 1, "b": 1},
        "payload": {"k": key, "size": len(png), "sha256": digest},
        "blobs": [{"size": len(png), "sha256": digest}],
    }
    size = session.probe_call("image_size", "fetch", key)
    width, height = png_size(png)
    if reply != due or size != {"width": width, "height": height}:
        raise CheckFailed(f"media.fetch gave {reply} and kept {size}")
    return (
        f"the PNG downloaded from the stub came back as blob 1, {len(png)}"
        f" bytes, sha256 {digest[:12]}, and was kept as {width}x{height}"
    )


# A download that cannot connect is an `error` line naming the failure.
def rung_lost(session: PageSession, closed_port: int, budget: int) -> str:
    import i18n

    key = "/_files/rung/lost.png"
    url = f"http://{_LOCAL_HOST}:{closed_port}/"
    session.probe_call("media_port", "lost", budget, _MEDIA_SECONDS)
    payload = {"url": url, "k": key}
    session.probe_call("request_send", "lost", "media.fetch", 1, payload, [])
    line = port_lines(session, "lost", 1)[0]
    pattern = pattern_make(i18n.i18n("media.download_failed", url, key, _ANY))
    message = cast(str, line["payload"].get("message", ""))
    if line["header"] != {"t": "error", "r": 1} or not pattern.fullmatch(
        message
    ):
        raise CheckFailed(f"the lost download gave {line}")
    return f"a download from a closed port gave {message!r}"


# A download answered 404 is an `error` line naming the status.
def rung_missing(session: PageSession, stub: StubServer, budget: int) -> str:
    import i18n

    key = "/_files/rung/missing.png"
    url = stub.url_make(f"{_STATUS_PREFIX}{_MISSING_STATUS}")
    session.probe_call("media_port", "missing", budget, _MEDIA_SECONDS)
    payload = {"url": url, "k": key}
    session.probe_call("request_send", "missing", "media.fetch", 1, payload, [])
    line = port_lines(session, "missing", 1)[0]
    cause = "Error: " + i18n.i18n("media.status_failed", url, _MISSING_STATUS)
    due = i18n.i18n("media.download_failed", url, key, cause)
    if line["header"] != {"t": "error", "r": 1} or line["payload"][
        "message"
    ] != due:
        raise CheckFailed(f"the missing download gave {line}, not {due!r}")
    return f"a download answered {_MISSING_STATUS} gave {due!r}"


# A download that never comes is a timeout `error` line.
def rung_late(session: PageSession, stub: StubServer, budget: int) -> str:
    import i18n

    key = "/_files/rung/late.png"
    url = stub.url_make(_SILENT_PATH)
    session.probe_call("media_port", "late", budget, _MEDIA_SECONDS)
    payload = {"url": url, "k": key}
    session.probe_call("request_send", "late", "media.fetch", 1, payload, [])
    line = port_lines(session, "late", 1)[0]
    due = i18n.i18n("media.download_expired", url, key, _MEDIA_SECONDS)
    if line["header"] != {"t": "error", "r": 1} or line["payload"][
        "message"
    ] != due:
        raise CheckFailed(f"the late download gave {line}, not {due!r}")
    return f"a download that never came gave {due!r}"


# Bytes that are no image are an `error` line of the decode.
def rung_garbage(session: PageSession, budget: int) -> str:
    import i18n

    key = "/_files/rung/garbage.png"
    session.probe_call("media_port", "garbage", budget, _MEDIA_SECONDS)
    session.probe_call(
        "request_send",
        "garbage",
        "media.store",
        1,
        {"k": key},
        [list(_UNDECODABLE)],
    )
    line = port_lines(session, "garbage", 1)[0]
    pattern = pattern_make(i18n.i18n("media.decode_failed", key, _ANY))
    message = cast(str, line["payload"].get("message", ""))
    if line["header"] != {"t": "error", "r": 1} or not pattern.fullmatch(
        message
    ):
        raise CheckFailed(f"the undecodable bytes gave {line}")
    return f"{len(_UNDECODABLE)} bytes that are no image gave {message!r}"


# Over the budget the oldest image is evicted and its bitmap closed.
def rung_evict(session: PageSession, png: bytes) -> str:
    width, height = png_size(png)
    budget = width * height * 4
    first, second = "/_files/rung/first.png", "/_files/rung/second.png"
    session.probe_call("media_port", "evict", budget, _MEDIA_SECONDS)
    session.probe_call(
        "request_send", "evict", "media.store", 1, {"k": first}, [list(png)]
    )
    port_lines(session, "evict", 1)
    session.probe_call("image_keep", "evict", first)
    session.probe_call(
        "request_send", "evict", "media.store", 2, {"k": second}, [list(png)]
    )
    port_lines(session, "evict", 2)
    gone = session.probe_call("image_size", "evict", first)
    closed = session.probe_call("kept_size", first)
    kept = session.probe_call("image_size", "evict", second)
    if (
        gone is not None
        or closed != {"width": 0, "height": 0}
        or kept != {"width": width, "height": height}
    ):
        raise CheckFailed(
            f"after the second image the first is {gone}, its bitmap"
            f" {closed}, the second {kept}"
        )
    return (
        f"with a budget of {budget} bytes, one {width}x{height} image, the"
        " second store evicted the first and closed its ImageBitmap"
    )


# The UI's hello line reaches the server through the worker unchanged.
def rung_relay(session: PageSession, subtitle: str) -> str:
    import i18n

    session.engine_open(subtitle)
    bootstrap = session.ttyd.command[1]
    pattern = pattern_make(
        i18n.i18n(
            "page.hello_shown",
            bootstrap,
            file_sha256(bootstrap),
            _ANY,
            session.root,
        )
    )
    rows = server_wait(
        session,
        "the UI's hello line on the server",
        lambda: [
            row
            for row in verbose_read(session, _UI_THREAD)
            if pattern.fullmatch(row.text)
        ]
        or None,
    )
    ring = [json_object(line) for line in json_list(session.probe_call("history"))]
    kept = [line for line in ring if line["text"] == rows[0].text]
    if len(kept) != 1 or (kept[0]["at"], kept[0]["level"]) != (
        rows[0].at,
        rows[0].level,
    ):
        raise CheckFailed(
            f"the page's ring holds {kept} for the server's {rows[0]}"
        )
    return (
        f"the start showed {subtitle!r}; the UI logged {rows[0].text!r} once"
        " settings.set and boot.hello came from the worker, and the server's"
        " log holds it for thread ui with the same at and level"
    )


# The live verbose ring of the UI holds the lines at the live level.
def rung_ring(session: PageSession) -> str:
    ring = json_list(session.probe_call("history"))
    size: int = session.values["verbose_ring"]
    level: int = session.values["verbose_level"]
    above = [line for line in ring if json_object(line)["level"] > level]
    if not ring or len(ring) > size or above:
        raise CheckFailed(f"the UI's ring holds {len(ring)} lines: {ring}")
    return (
        f"the UI's verbose singleton holds {len(ring)} lines of at most"
        f" verbose_ring {size}, none above verbose_level {level}"
    )


# The queue installed the live verbose sink, so a second one is refused.
def rung_sink(session: PageSession) -> str:
    import i18n

    message = session.probe_call("sink_twice")
    due = i18n.i18n("verbose.sink_twice")
    if message != due:
        raise CheckFailed(f"sink_set threw {message!r}, not {due!r}")
    return f"a second sink_set on the live verbose threw {due!r}"


# The bundle's strings table holds the overlay's text.
def rung_strings(session: PageSession) -> str:
    import i18n

    message = session.probe_call("ring_refused")
    due = i18n.i18n("overlay.ring_invalid", 0)
    if message != due:
        raise CheckFailed(f"the overlay threw {message!r}, not {due!r}")
    return f"an overlay of ring 0 threw {due!r}, the text of the server's file"


# Control and a digit show and hide the overlay of that tty.
def rung_keys(session: PageSession) -> str:
    states: list[tuple[int, int, bool]] = [
        (1, 1, False),
        (1, 1, True),
        (2, 2, False),
        (2, 2, True),
    ]
    for digit, count, hidden in states:
        session.key_press(digit_stroke(digit))
        views_wait(
            session,
            f"the overlay of tty {digit} after control {digit}",
            _OVERLAY_SELECTOR,
            lambda views: len(views) == count
            and views[digit - 1]["hidden"] == hidden,
        )
    return (
        "control 1 showed and hid the overlay of tty 1, control 2 made, showed"
        " and hid that of tty 2"
    )


# The overlay of tty 1 shows the wire's lines in both directions.
def rung_lines(session: PageSession) -> str:
    import i18n

    session.key_press(digit_stroke(1))
    views = views_wait(
        session,
        "the overlay of tty 1 shown",
        _OVERLAY_SELECTOR,
        lambda views: not views[0]["hidden"],
    )
    rows = cast(str, views[0]["text"]).split("\n")
    sent = pattern_make(i18n.i18n("worker_ai.overlay_sent", _ANY))
    received = pattern_make(i18n.i18n("worker_ai.overlay_received", _ANY))
    sends = [row for row in rows if sent.fullmatch(row) and _SNAPSHOT_MARK in row]
    takes = [
        row for row in rows if received.fullmatch(row) and _SNAPSHOT_MARK in row
    ]
    if not sends or not takes:
        raise CheckFailed(f"the overlay of tty 1 shows {rows}")
    return (
        f"the overlay of tty 1 shows {len(rows)} lines, the db.snapshot"
        f" requests sent, {sends[0]!r} the first, and their replies received"
    )


# A line logged between items goes to the server in the batch after the next.
def rung_batch(session: PageSession) -> str:
    line = json_object(session.probe_call("log_mark", 1, _BATCH_MARK))
    if line["text"] != _BATCH_MARK:
        raise CheckFailed(f"the UI's ring kept {line}")
    session.key_press(digit_stroke(1))
    views_wait(
        session,
        "the overlay of tty 1 hidden",
        _OVERLAY_SELECTOR,
        lambda views: views[0]["hidden"],
    )
    rows = server_wait(
        session,
        "the batched line on the server",
        lambda: [
            row
            for row in verbose_read(session, _UI_THREAD)
            if row.text == _BATCH_MARK
        ]
        or None,
    )
    if (rows[0].at, rows[0].level) != (line["at"], line["level"]):
        raise CheckFailed(f"the server holds {rows[0]} for {line}")
    return (
        f"{_BATCH_MARK!r}, logged outside any item, went to the server in the"
        " verbose.put after the next item, a key, with its at and level"
    )


# The overlay's `pre` is hidden by the real style and shown uncovered.
def rung_style(session: PageSession) -> str:
    views = json_list(session.probe_call("views", _OVERLAY_SELECTOR))
    hidden = json_object(views[0])
    if hidden["display"] != "none":
        raise CheckFailed(f"the hidden overlay is {hidden}")
    session.key_press(digit_stroke(1))
    shown = views_wait(
        session,
        "the overlay of tty 1 shown",
        _OVERLAY_SELECTOR,
        lambda views: not views[0]["hidden"],
    )[0]
    if (
        shown["display"] == "none"
        or shown["width"] <= 0
        or shown["height"] <= 0
        or not shown["center_hit"]
    ):
        raise CheckFailed(f"the shown overlay is {shown}")
    return (
        "the hidden overlay's computed display is none; shown it is"
        f" {shown['display']}, {shown['width']:g}x{shown['height']:g} and"
        " its centre hits it"
    )


# A PNG of the page with the overlay of tty 1 open.
def rung_survey(session: PageSession) -> str:
    png = session.shot_save("stage5_overlay_tty1")
    session.key_press(digit_stroke(1))
    views_wait(
        session,
        "the overlay of tty 1 hidden",
        _OVERLAY_SELECTOR,
        lambda views: views[0]["hidden"],
    )
    return f"PNG {png} with control 1 open, then closed again"


# Keys typed while tty 0 opens are dropped; ttyd is stopped meanwhile.
def rung_early(session: PageSession) -> str:
    ttyd = session.ttyd
    ttyd.signal_send(signal.SIGSTOP)
    try:
        session.key_press(digit_stroke(0))
        views_wait(
            session,
            "the console view shown",
            _CONSOLE_SELECTOR,
            lambda views: len(views) == 1 and not views[0]["hidden"],
        )
        session.command_type("echo " + _MARK_EARLY)
        session.fault_none("typing into the opening console")
    finally:
        ttyd.signal_send(signal.SIGCONT)
    rows = rows_wait(
        session,
        "dash's prompt in the console",
        lambda rows: row_last(rows) == _PROMPT_ROW,
    )
    typed = [row for row in rows_filled(rows) if _MARK_EARLY in row]
    if typed:
        raise CheckFailed(f"the console shows {typed} typed before it opened")
    return (
        "with ttyd stopped, control 0 showed the console view and echo"
        f" {_MARK_EARLY} with Enter typed into it before its first message"
        " reached no handler and made no fault; ttyd continued, the console"
        " opened, and dash prompted with nothing of what was typed"
    )


# Control 0 showed the console view, not an overlay, and dash's prompt came.
def rung_console(session: PageSession) -> str:
    views_wait(
        session,
        "the console view shown",
        _CONSOLE_SELECTOR,
        lambda views: len(views) == 1 and not views[0]["hidden"],
    )
    rows_wait(
        session,
        "dash's prompt in the console",
        lambda rows: row_last(rows) == _PROMPT_ROW,
    )
    overlays = json_list(session.probe_call("views", _OVERLAY_SELECTOR))
    terminal = json_object(session.probe_call("view", _TERMINAL_SELECTOR))
    inside = session.probe_call("center_inside", _TERMINAL_SELECTOR, _DEBUG_SELECTOR)
    if len(overlays) != 2 or terminal["width"] <= 0 or inside is not True:
        raise CheckFailed(
            f"after control 0 there are {len(overlays)} overlays and the"
            f" terminal is {terminal}, its centre inside #debug {inside}"
        )
    png = session.shot_save("stage7_console")
    return (
        "control 0 showed the console view and made no overlay; the view"
        " fetched the token through the worker's console port, ttyd ran the"
        f" console role and dash's prompt shows; PNG {png}"
    )


# Text typed into the console is echoed by dash.
def rung_echo(session: PageSession) -> str:
    session.command_type("echo " + _MARK_TYPED)
    rows_wait(
        session,
        "the echo in the console",
        lambda rows: _MARK_TYPED in rows_filled(rows)
        and row_last(rows) == _PROMPT_ROW,
    )
    return f"echo {_MARK_TYPED} typed into the terminal printed {_MARK_TYPED}"


# Hides the console view with control 0.
def console_hide(session: PageSession) -> None:
    session.key_press(digit_stroke(0))
    views_wait(
        session,
        "the console view hidden",
        _CONSOLE_SELECTOR,
        lambda views: views[0]["hidden"],
    )


# Shows the console view with control 0.
def console_show(session: PageSession) -> None:
    session.key_press(digit_stroke(0))
    views_wait(
        session,
        "the console view shown",
        _CONSOLE_SELECTOR,
        lambda views: not views[0]["hidden"],
    )


# Sends a permit tool's input and checks the request as the player sees it.
def permit_take(
    session: PageSession, text: str, call: ScriptCall
) -> list[dict[str, Any]]:
    import i18n

    session.turn_send(text)
    permit = json_object(session.probe_wait("the permit request", "permit"))
    shown = json_object(permit["text"])
    buttons = [json_object(button) for button in permit["buttons"]]
    viewport = json_object(session.probe_call("viewport"))
    due = i18n.i18n("page.permit_text", _PERMIT_TOOL, json_text(call.arguments))
    labels = [
        i18n.i18n("page.choice_accept"),
        i18n.i18n("page.choice_deny"),
        i18n.i18n("page.choice_always"),
    ]
    if (
        shown["text"] != due
        or [button["text"] for button in buttons] != labels
        or not box_inside(shown, viewport)
        or not all(box_inside(button, viewport) for button in buttons)
        or not all(button["center_hit"] for button in buttons)
    ):
        raise CheckFailed(f"the permit request is {permit}, its text due {due!r}")
    return buttons


# Accept runs the console command and returns its output.
def rung_run(session: PageSession, scene: str, calls: dict[str, ScriptCall]) -> str:
    call = calls[_INPUT_RUN]
    console_hide(session)
    buttons = permit_take(session, _INPUT_RUN, call)
    png = session.shot_save("stage7_permit")
    session.view_click(buttons[0])
    session.outcome_wait(call.ending)
    result = json_object(json.loads(tool_result(session, scene, call.ending)))
    output = cast(str, result["output"])
    if result["timed_out"] is not False or _MARK_RUN not in output.split("\n"):
        raise CheckFailed(f"console_run returned {result}")
    return (
        "the permit request showed its text and Accept, Deny and Always Allow"
        f" in the viewport, each button's centre hitting it, PNG {png}; Accept"
        f" ran echo {_MARK_RUN} and the tool returned {output!r}"
    )


# Deny returns an error to the caller.
def rung_deny(session: PageSession, scene: str, calls: dict[str, ScriptCall]) -> str:
    import i18n

    call = calls[_INPUT_DENY]
    buttons = permit_take(session, _INPUT_DENY, call)
    session.view_click(buttons[1])
    session.outcome_wait(call.ending)
    result = tool_result(session, scene, call.ending)
    due = i18n.i18n("tools_browser.permit_denied", _PERMIT_TOOL)
    if result != due:
        raise CheckFailed(f"the denied tool returned {result!r}, not {due!r}")
    return f"Deny returned {due!r} to the model as the tool's result"


# The console read times out on `sleep 600`.
def rung_timeout(
    session: PageSession, scene: str, calls: dict[str, ScriptCall]
) -> str:
    call = calls[_INPUT_TIMEOUT]
    buttons = permit_take(session, _INPUT_TIMEOUT, call)
    session.view_click(buttons[2])
    session.outcome_wait(call.ending)
    result = json_object(json.loads(tool_result(session, scene, call.ending)))
    if result["timed_out"] is not True:
        raise CheckFailed(f"console_run of {_SLEEP_COMMAND} returned {result}")
    return (
        f"Always Allow ran {_SLEEP_COMMAND}, whose read timed out after"
        f" {_SLEEP_SECONDS} s with timed_out true"
    )


# Control and C typed into the console ends `sleep 600`.
def rung_interrupt(session: PageSession) -> str:
    console_show(session)
    rows_wait(
        session,
        f"{_SLEEP_COMMAND} in the console",
        lambda rows: row_last(rows).endswith(_SLEEP_COMMAND),
    )
    session.probe_call("focus", _TERMINAL_INPUT)
    session.key_press(_KEY_INTERRUPT)
    rows_wait(
        session,
        "dash's prompt after the interrupt",
        lambda rows: row_last(rows) == _PROMPT_ROW,
    )
    return f"control C in the terminal ended {_SLEEP_COMMAND} and dash prompted"


# The console is fed while hidden and shows the output once shown again.
def rung_hidden(
    session: PageSession, scene: str, calls: dict[str, ScriptCall]
) -> str:
    call = calls[_INPUT_HIDDEN]
    console_hide(session)
    session.turn_run(_INPUT_HIDDEN, call.ending)
    console_show(session)
    rows_wait(
        session,
        "the hidden run's output in the console",
        lambda rows: _MARK_HIDDEN in rows_filled(rows),
    )
    result = json_object(json.loads(tool_result(session, scene, call.ending)))
    if _MARK_HIDDEN not in cast(str, result["output"]).split("\n"):
        raise CheckFailed(f"console_run returned {result}")
    return (
        f"with the view hidden and Always Allow given, echo {_MARK_HIDDEN} ran"
        " unasked; shown again, the terminal holds its output"
    )


# The verbose level tool sets the AI's level.
def rung_level(session: PageSession, scene: str, calls: dict[str, ScriptCall]) -> str:
    call = calls[_INPUT_LEVEL]
    session.turn_run(_INPUT_LEVEL, call.ending)
    result = tool_result(session, scene, call.ending)
    if result != json_text({}):
        raise CheckFailed(f"verbose_level returned {result!r}")
    return f"verbose_level {_TOOL_LEVEL} returned {result!r} with no error"


# A table of strings made by the AI's script is replicated to the server.
def rung_pairs(session: PageSession, scene: str, calls: dict[str, ScriptCall]) -> str:
    call = calls[_INPUT_PAIRS]
    session.turn_run(_INPUT_PAIRS, call.ending)
    value = script_value(session, scene, call.ending)
    held = server_wait(
        session,
        "the table of strings on the server",
        lambda: rows if (rows := pairs_read(session)) == _PAIRS_ROWS else None,
    )
    if value != _PAIRS_ROWS:
        raise CheckFailed(f"the script read {value}")
    return (
        f"the AI's script made {_PAIRS_DB} with a table of strings and read"
        f" {value}; the server's copy holds {held}"
    )


# A value over `overflow_bytes` goes through the OPFS cache to the server.
def rung_overflow(
    session: PageSession, scene: str, calls: dict[str, ScriptCall]
) -> str:
    call = calls[_INPUT_OVERFLOW]
    size = session.values["overflow_bytes"] + 1
    data = pattern_bytes(size)
    digest = sha256_text(data)
    session.turn_run(_INPUT_OVERFLOW, call.ending)
    value = script_value(session, scene, call.ending)
    due = {"size": size, "sha256": digest, "cached": True}
    if value != due:
        raise CheckFailed(f"the script returned {value}, not {due}")
    server_wait(
        session,
        "the value on the server",
        lambda: True if value_read(session, _OVERFLOW_REF) == data else None,
    )
    return (
        f"a value of {size} bytes was kept in a cache file of OPFS and"
        " forwarded from it; the server holds the same bytes, sha256"
        f" {digest[:12]}"
    )


# Writing values until the cache is full is an error the script sees.
def rung_cache(session: PageSession, scene: str, calls: dict[str, ScriptCall]) -> str:
    import i18n

    call = calls[_INPUT_CACHE]
    before = seq_read(session, _FILES_DB)
    session.turn_run(_INPUT_CACHE, call.ending)
    value = json_object(script_value(session, scene, call.ending))
    written = cast(int, value["written"])
    full = pattern_make("Error: " + i18n.i18n("substrate.cache_full", _ANY))
    if written < 1 or value["error"] is None or not full.fullmatch(value["error"]):
        raise CheckFailed(f"the script returned {value}")
    server_wait(
        session,
        "the puts and deletes on the server",
        lambda: True
        if seq_read(session, _FILES_DB) == before + 2 * written
        else None,
    )
    left = keys_read(session, _FILES_DB, _CACHE_PREFIX.removeprefix("/_files/"))
    if left:
        raise CheckFailed(f"the server still holds {left}")
    return (
        f"{written} values over overflow_bytes were written before kv_put threw"
        f" {value['error']!r}; deleted again, the server saw every put and"
        " delete and holds none of them"
    )


# Creating databases until the pool is full is an error the script sees.
def rung_pool(session: PageSession, scene: str, calls: dict[str, ScriptCall]) -> str:
    call = calls[_INPUT_POOL]
    session.turn_run(_INPUT_POOL, call.ending)
    value = json_object(script_value(session, scene, call.ending))
    if value["made"] < 1 or value["error"] is None or value["listed"] is not False:
        raise CheckFailed(f"the script returned {value}")
    made = cast(int, value["made"])
    names = [f"{_POOL_PREFIX}{count}" for count in range(made + 1)]
    left = [
        db for db in names if os.path.exists(database_path(session.root, db))
    ]
    if left:
        raise CheckFailed(f"the server still holds {left}")
    session.fault_none("the pool's creates and drops on the server")
    return (
        f"{made} databases were created before db_create threw"
        f" {value['error']!r}; the failed one is not listed, and all were"
        " dropped again; the server, holding the turn's last message, which"
        f" was forwarded after the drops, holds none of the {len(names)}"
    )


# The scripted turn makes a universe, an image and a scene, and renders.
def rung_turn(session: PageSession, scene: str, png: bytes) -> str:
    console_hide(session)
    session.probe_call("long_start")
    session.turn_run(_INPUT_TURN, _SCENE_SUBTITLE)
    canvas = json_object(session.probe_call("canvas"))
    width, height = png_size(png)
    if (
        canvas["view"]["hidden"]
        or (canvas["width"], canvas["height"]) != (width, height)
    ):
        raise CheckFailed(f"the image after the turn is {canvas}")
    player = server_wait(
        session, "the player", lambda: text_read(session, "/metaverse/player")
    )
    facts: list[tuple[str, Callable[[], object], object]] = [
        (
            "the current world",
            lambda: text_read(session, "/metaverse/world"),
            _WORLD,
        ),
        (
            "the world's scene",
            lambda: text_read(session, f"/{_WORLD}/scene"),
            _SCENE_REF,
        ),
        (
            "the scene's head",
            lambda: rows_read(
                session, _REGION, "SELECT version FROM _head WHERE id = ?", [_SCENE_ID]
            ),
            [[1]],
        ),
        (
            "the universe row",
            lambda: rows_read(
                session,
                _METAVERSE_DB,
                "SELECT name, title, player, world FROM universe WHERE name = ?",
                [_UNIVERSE],
            ),
            [[_UNIVERSE, _UNIVERSE_TITLE, player, _WORLD]],
        ),
        ("the image", lambda: value_read(session, _IMAGE_REF), png),
    ]
    for what, read, due in facts:
        server_wait(
            session,
            f"{what} on the server",
            lambda: True if read() == due else None,
        )
    turns = server_wait(
        session,
        "the turn on the server",
        lambda: turns_ended(session, scene, _SCENE_SUBTITLE),
    )
    shot = session.shot_save("stage8_scripted_turn")
    return (
        f"input 1 ran the seeded bootstrap script, made the image, wrote and"
        f" entered {_SCENE_REF} and rendered it: the page paints the"
        f" {width}x{height} PNG, the server holds the universe, the world,"
        f" the scene, the image's bytes and {len(turns)} turns; PNG {shot}"
    )


# What the server and the page hold, to compare across a time with no input.
def still_state(session: PageSession, scene: str) -> dict[str, Any]:
    names = sorted(
        name.removesuffix(_DB_EXTENSION)
        for name in os.listdir(session.root)
        if name.endswith(_DB_EXTENSION) and name != _VERBOSE_FILE
    )
    ring = json_list(session.probe_call("history"))
    subtitle = json_object(session.probe_call("view", _SUBTITLE_TEXT))
    return {
        "seq": {db: seq_read(session, db) for db in names},
        "ai": len(verbose_read(session, _AI_THREAD)),
        "ui": len(verbose_read(session, _UI_THREAD)),
        "turns": len(turns_read(session, scene)),
        "ring": ring[-1:],
        "subtitle": subtitle["text"],
    }


# With no input nothing runs: the server and the page stay as they were.
def rung_still(session: PageSession, scene: str) -> str:
    before = still_state(session, scene)
    time.sleep(_QUIET_SECONDS)
    after = still_state(session, scene)
    if after != before:
        raise CheckFailed(
            f"with no input for {_QUIET_SECONDS:g} s the server and the page"
            f" went from {before} to {after}"
        )
    return (
        f"for {_QUIET_SECONDS:g} s with no input the seq of every database"
        f" {before['seq']}, the {before['ai']} AI and {before['ui']} UI lines"
        f" on the server, the scene's {before['turns']} turns, the UI's"
        " newest ring line and the subtitle stayed as they were"
    )


# After a render with an image, `#image` fills the viewport, uncovered.
def rung_image(session: PageSession) -> str:
    canvas = json_object(session.probe_call("canvas"))
    view = json_object(canvas["view"])
    if (
        view["hidden"]
        or (view["left"], view["top"]) != (0, 0)
        or (view["width"], view["height"])
        != (canvas["inner_width"], canvas["inner_height"])
        or not view["center_hit"]
    ):
        raise CheckFailed(f"#image is {canvas}")
    png = session.shot_save("stage8_image_visible")
    return f"#image is shown, its box the viewport, its centre hits it; PNG {png}"


# The subtitle shows its text inside the viewport on black.
def rung_subtitle(session: PageSession) -> str:
    text = json_object(session.probe_call("view", _SUBTITLE_TEXT))
    area = json_object(session.probe_call("view", _SUBTITLE_SELECTOR))
    viewport = json_object(session.probe_call("viewport"))
    if (
        text["text"] != _SCENE_SUBTITLE
        or not box_inside(text, viewport)
        or not text["center_hit"]
        or area["background"] != _BLACK
    ):
        raise CheckFailed(f"the subtitle is {text} in {area}")
    png = session.shot_save("stage8_subtitle_visible")
    return (
        f"the subtitle shows {_SCENE_SUBTITLE!r} inside the viewport, its"
        f" centre hits it, #subtitle's background is {_BLACK}; PNG {png}"
    )


# The input shows, open, after the first render.
def rung_input(session: PageSession) -> str:
    view = json_object(session.probe_call("view", _INPUT_SELECTOR))
    if view["hidden"] or view["disabled"] or not view["center_hit"]:
        raise CheckFailed(f"#input after the render is {view}")
    png = session.shot_save("stage8_input_visible")
    return f"#input after the render is open and its centre hits it; PNG {png}"


# The console view shows over the rendered image, inside `#debug`.
def rung_terminal(session: PageSession) -> str:
    console_show(session)
    terminal = json_object(session.probe_call("view", _TERMINAL_SELECTOR))
    inside = session.probe_call("center_inside", _TERMINAL_SELECTOR, _DEBUG_SELECTOR)
    if terminal["width"] <= 0 or terminal["height"] <= 0 or inside is not True:
        raise CheckFailed(f"the terminal is {terminal}, inside #debug {inside}")
    png = session.shot_save("stage8_console_visible")
    console_hide(session)
    return (
        "over the image the terminal's box is"
        f" {terminal['width']:g}x{terminal['height']:g} and its centre hits"
        f" inside #debug, not #image; PNG {png}"
    )


# The overlay of tty 1 shows over the rendered image, its first line visible.
def rung_overlay(session: PageSession) -> str:
    session.key_press(digit_stroke(1))
    view = views_wait(
        session,
        "the overlay of tty 1 shown",
        _OVERLAY_SELECTOR,
        lambda views: not views[0]["hidden"],
    )[0]
    corner = session.probe_call(
        "corner_inside", _OVERLAY_SELECTOR, _DEBUG_SELECTOR, _CORNER_PIXELS
    )
    debug = json_object(session.probe_call("view", _DEBUG_SELECTOR))
    if (
        view["width"] <= 0
        or view["height"] <= 0
        or not cast(str, view["text"])
        or corner is not True
        or debug["background"] != _BLACK
    ):
        raise CheckFailed(f"the overlay is {view} in {debug}, corner {corner}")
    png = session.shot_save("stage8_overlay_visible")
    return (
        "over the image the overlay of tty 1 has a box, its first line hits"
        f" inside #debug and #debug's background is {_BLACK}; PNG {png}"
    )


# A line wider than the viewport scrolls inside `#debug`, not the page.
def rung_wide(session: PageSession) -> str:
    widths = json_object(session.probe_call("widths"))
    if (
        widths["debug_scroll"] <= widths["debug_client"]
        or widths["document_scroll"] != widths["inner"]
    ):
        raise CheckFailed(f"the widths are {widths}")
    png = session.shot_save("stage8_overlay_wide")
    return (
        f"#debug scrolls {widths['debug_scroll']} pixels in"
        f" {widths['debug_client']}, the document stays"
        f" {widths['document_scroll']} wide; PNG {png}"
    )


# A tall overlay covers the input until it is toggled off.
def rung_toggle(session: PageSession) -> str:
    covered = json_object(session.probe_call("view", _INPUT_SELECTOR))
    if covered["center_hit"]:
        raise CheckFailed(f"the tall overlay leaves #input uncovered: {covered}")
    shown = session.shot_save("stage8_overlay_covers_input")
    session.key_press(digit_stroke(1))
    views_wait(
        session,
        "the overlay of tty 1 hidden",
        _OVERLAY_SELECTOR,
        lambda views: views[0]["hidden"],
    )
    view = json_object(session.probe_call("view", _INPUT_SELECTOR))
    if not view["center_hit"]:
        raise CheckFailed(f"#input stays covered: {view}")
    hidden = session.shot_save("stage8_overlay_toggled_off")
    return (
        f"the tall overlay covered #input, PNG {shown}; control 1 hid it and"
        f" #input's centre hits it again, PNG {hidden}"
    )


# The long tasks the UI thread ran since the scripted turn began.
def rung_long(session: PageSession) -> str:
    durations = [cast(float, value) for value in json_list(session.probe_call("long_list"))]
    target = session.values["long_task_ms"]
    longest = max(durations, default=0.0)
    return (
        f"the long task observer saw {len(durations)} tasks of 50 ms or more"
        f" on the UI thread, the longest {longest:.1f} ms; long_task_ms"
        f" {target} is a soft target below the observer's 50 ms floor"
    )


# `exit` ends dash, after which typing into the console is dropped.
def rung_exit(session: PageSession) -> str:
    console_show(session)
    mark = len(session.ttyd.lines)
    session.command_type(_EXIT_COMMAND)
    _, found = session.ttyd.line_wait(_ENDED_PATTERN, "the console's end", mark)
    if found.group(1, 2) != (_EXITED_WORDS, "0"):
        raise CheckFailed(f"{session.ttyd.version} logged: {found.string}")
    session.turn_run(_INPUT_PLAIN, _ENDING_PLAIN)
    session.text_type(_TERMINAL_INPUT, _DROPPED_TEXT)
    session.fault_none("typing into the ended console")
    return (
        f"{_EXIT_COMMAND} ended dash with code 0 as ttyd logged; after a turn"
        f" went through both queues, {_DROPPED_TEXT!r} typed into the"
        " terminal was dropped with no fault"
    )


# A new load starts at the scene with its image painted.
def rung_scene(session: PageSession, png: bytes) -> str:
    session.page_leave()
    session.engine_open(_SCENE_SUBTITLE)
    canvas = json_object(session.probe_call("canvas"))
    width, height = png_size(png)
    if (
        canvas["view"]["hidden"]
        or (canvas["width"], canvas["height"]) != (width, height)
        or not canvas["view"]["center_hit"]
    ):
        raise CheckFailed(f"the image at the start is {canvas}")
    shot = session.shot_save("stage8_start_with_image")
    return (
        f"the second load found the rows, started at {_SCENE_REF} and painted"
        f" its {width}x{height} image, uncovered; PNG {shot}"
    )


# A click on the image reaches the AI as a click at that image pixel.
def rung_click(session: PageSession) -> str:
    import i18n

    canvas = json_object(session.probe_call("canvas"))
    pixel_x = cast(int, canvas["width"]) // 3
    pixel_y = cast(int, canvas["height"]) // 3
    point = json_object(session.probe_call("click_point", pixel_x, pixel_y))
    if point["hit"] is not True:
        raise CheckFailed(f"the point {point} does not hit #image")
    session.mouse_click(point["x"], point["y"])
    text = session.fault_wait("the scripted provider's refusal of the click")
    click = i18n.i18n("agent.click_text", pixel_x, pixel_y)
    due = i18n.i18n("provider_script.input_invalid", click)
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    session.programs_wait(1, "the stop function to end the engine")
    return (
        f"a click at ({point['x']:.1f}, {point['y']:.1f}) became ai.click"
        f" {pixel_x}, {pixel_y} and the agent told it as {click!r}, which the"
        " integer script refuses as a fault, as it must"
    )


# A restart's second hello is a fault on the page, and the request unanswered.
def rung_restart(session: PageSession) -> str:
    import i18n

    session.page_leave()
    session.engine_open(_SCENE_SUBTITLE)
    session.turn_send(_INPUT_RESTART)
    text = session.fault_wait("the fault of the second hello")
    due = i18n.i18n("wire.hello_twice")
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    session.programs_wait(1, "the stop function to end the engine")
    return (
        f"system_restart over the server's MCP client got no reply; the"
        f" restarted {_RESTART_NAME} wrote hello again and the page faulted"
        f" with {due!r}, then the stop function ended the engine"
    )


# Control keys outside debug mode change nothing on the page.
def rung_gating(session: PageSession, subtitle: str) -> str:
    session.engine_open(subtitle)
    for digit in (1, 0):
        session.key_press(digit_stroke(digit))
    session.turn_run(_INPUT_PLAIN, _ENDING_PLAIN)
    children = session.probe_call("debug_children")
    if children != 0:
        raise CheckFailed(f"#debug holds {children} children")
    return (
        "with debug false, control 1 and control 0 made no overlay and no"
        " console view, as a turn queued after them showed"
    )


# The console role is refused outside debug mode.
def rung_refused_role(session: PageSession) -> str:
    mark = len(session.ttyd.lines)
    session.probe_call("console_open", session.url)
    record = json_object(session.probe_wait("the console's close", "console_when"))
    _, found = session.ttyd.line_wait(_ENDED_PATTERN, "the console's end", mark)
    lines = [json_object(line) for line in json_list(record["lines"])]
    opened = [
        line
        for line in lines
        if line["header"] == {"t": "console.open", "r": 1}
        and type(line["payload"].get("token")) is str
    ]
    output = [line for line in lines if _OUTPUT_KIND in line["kinds"]]
    if (
        len(opened) != 1
        or output
        or record["closes"] != [_CLOSE_LOST]
        or found.group(1, 2) != (_EXITED_WORDS, "1")
    ):
        raise CheckFailed(
            f"the console port got {lines}, the closes {record['closes']},"
            f" and ttyd logged {found.string}"
        )
    return (
        "with debug false a ConsolePort opened tty 0 with its token, the"
        " console role exited with code 1 and no output, and the port saw"
        f" the close {_CLOSE_LOST}"
    )


# Records the AI's lines of a synchronous start through its render.
def rung_recorded(
    session: PageSession, subtitle: str, recorded: list[list[str]]
) -> str:
    session.engine_open(subtitle)
    rows = server_wait(
        session,
        "the AI's lines through the rendered start",
        lambda: rendered_rows(session, 0),
    )
    recorded.append([row.text for row in rows])
    return (
        f"in synchronous mode the start logged {len(rows)} lines on the AI"
        " thread through the rendered scene"
    )


# A second synchronous run on a new root logs the same lines.
def rung_twice(
    session: PageSession, subtitle: str, recorded: list[list[str]]
) -> str:
    session.engine_open(subtitle)
    rows = server_wait(
        session,
        "the AI's lines through the rendered start",
        lambda: rendered_rows(session, 0),
    )
    texts = [row.text for row in rows]
    first = recorded[0]
    if texts != first:
        index = next(
            (
                number
                for number, (one, other) in enumerate(zip(texts, first))
                if one != other
            ),
            min(len(texts), len(first)),
        )
        raise CheckFailed(
            f"the second run logged {len(texts)} lines, the first"
            f" {len(first)}, unequal from line {index}:"
            f" {texts[index : index + 1]} where {first[index : index + 1]}"
        )
    return f"a second root's synchronous start logged the same {len(texts)} lines"


# A second load opens the browser's copies with no snapshot.
def rung_reopen(session: PageSession, subtitle: str) -> str:
    after = verbose_last(session)
    session.page_leave()
    session.engine_open(subtitle)
    rows = server_wait(
        session,
        "the AI's lines of the second start",
        lambda: rendered_rows(session, after),
    )
    asked = [row.text for row in rows if _SNAPSHOT_MARK in row.text]
    if asked:
        raise CheckFailed(f"the second start asked {asked}")
    return (
        f"the second load's start logged {len(rows)} lines and asked for no"
        " snapshot: the databases in OPFS were found with the server's seq"
    )


# A database the server changed is replaced from its snapshot at the start.
def rung_replace(session: PageSession) -> str:
    after = verbose_last(session)
    session.page_leave()
    ref = scene_replace(session, _REPLACED_SUBTITLE)
    session.engine_open(_REPLACED_SUBTITLE)
    rows = server_wait(
        session,
        "the AI's lines of the replacing start",
        lambda: rendered_rows(session, after),
    )
    asked = [row.text for row in rows if _SNAPSHOT_MARK in row.text]
    if not asked:
        raise CheckFailed(f"the start asked for no snapshot: {rows}")
    return (
        f"with {ref} written on the server between loads, the start asked"
        f" {len(asked)} snapshots and showed {_REPLACED_SUBTITLE!r}"
    )


# A refused push is a fault, and Reload replaces the database and starts.
def rung_desync(session: PageSession) -> str:
    import i18n

    seq = seq_bump(session, _DESYNC_REF)
    session.turn_send(_INPUT_PLAIN)
    text = session.fault_wait("the fault of the refused push")
    due = i18n.i18n("substrate.since_stale", "turn.append", seq - 1, seq, _METAVERSE_DB)
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    session.programs_wait(1, "the stop function to end the engine")
    button = json_object(session.probe_wait("the Reload button", "reload_button"))
    session.reload_click(json_object(button["view"]))
    session.outcome_wait(_REPLACED_SUBTITLE)
    return (
        f"with {_DESYNC_REF} written on the server, the page's next push was"
        f" refused with {due!r}; Reload replaced metaverse and started again"
    )


# A server that never writes hello runs out the worker's wait for it.
def rung_stalled(session: PageSession) -> str:
    import i18n

    session.page_open()
    _, found = session.ttyd.line_wait(
        _STARTED_PATTERN, "the engine program's start", session.mark
    )
    pid = int(found.group(1))
    program_check(session.ttyd, pid)
    text = session.fault_wait("the fault of the wait for hello")
    what = i18n.i18n("wire.what_hello")
    due = i18n.i18n("wire.wait_expired", _WIRE_SECONDS, what)
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    ended = session.programs_wait(1, "the stop function to end the program")
    return (
        f"pid {pid}, ttyd's child running {_LOOP_OPTION} {_STALL_LOOP_NAME},"
        " never wrote hello; the AI worker's wire port faulted with"
        f" {due!r} on the page, and the stop function ended {ended} program"
    )


# A ttyd that asks a credential gives its token to a page that sends it.
def rung_credential(session: PageSession) -> str:
    client = session.browser.client_get()
    secret = base64.b64encode(_CREDENTIAL.encode()).decode()
    client.method_call("Network.enable")
    client.method_call(
        "Network.setExtraHTTPHeaders",
        {"headers": {"Authorization": "Basic " + secret}},
    )
    session.page_open()
    session.probe_call("wire_open", "credential", session.url)
    hello = json_object(
        session.probe_wait("hello", "wire_hello", "credential")
    )
    pid = cast(int, hello["pid"])
    program_check(session.ttyd, pid)
    url = session.url + _TOKEN_PATH
    granted = json_object(session.probe_call("token_read", url))
    client.method_call("Network.setExtraHTTPHeaders", {"headers": {}})
    refused = json_object(session.probe_call("token_read", url))
    client.method_call("Network.disable")
    if granted["status"] != _HTTP_OK or refused["status"] != _UNAUTHORIZED:
        raise CheckFailed(
            f"GET {url} gave {granted} with the credential and {refused}"
            f" without it, where {_HTTP_OK} and {_UNAUTHORIZED} were due"
        )
    token = json_object(json.loads(granted["text"]))["token"]
    if token != secret:
        raise CheckFailed(f"ttyd's token is {token!r}, not {secret!r}")
    return (
        f"with ttyd asking the credential {_CREDENTIAL!r}, a WirePort on the"
        " page, its requests carrying the Authorization header, fetched the"
        " token, which is the credential in base64, and ttyd took it: hello"
        f" came from pid {pid}; without the header GET {url} gave"
        f" {_UNAUTHORIZED}"
    )


# The page echoes 128 MiB through ttyd as messages that each fit.
def rung_large(session: PageSession) -> str:
    session.page_open()
    session.probe_call("wire_open", "echo", session.url)
    hello = json_object(session.probe_wait("hello", "wire_hello", "echo"))
    if hello["seq"] != {}:
        raise CheckFailed(
            f"hello's seq is {hello['seq']}, where the echo main loop, which"
            " opens no database, gives none"
        )
    program_check(session.ttyd, cast(int, hello["pid"]))
    count = _LARGE_BYTES // _ECHO_BLOB_BYTES
    digest = sha256_text(pattern_bytes(_ECHO_BLOB_BYTES))
    ttyd_pid = session.ttyd.process.pid
    before = memory_read(ttyd_pid)
    started = time.monotonic()
    session.probe_call("echo_run", "echo", count, _ECHO_BLOB_BYTES)
    lines = json_list(
        session.probe_wait("the echoes", "wire_lines", "echo", count)
    )
    seconds = time.monotonic() - started
    after = memory_read(ttyd_pid)
    due = [
        {
            "header": {"t": "echo", "r": number, "b": 1},
            "payload": {},
            "blobs": [{"size": _ECHO_BLOB_BYTES, "sha256": digest}],
        }
        for number in range(1, count + 1)
    ]
    if lines != due:
        raise CheckFailed(f"the echoes came back as {lines}, not {due}")
    rate = _LARGE_BYTES / _MIB / seconds
    return (
        f"{_LARGE_BYTES} bytes in {count} echo requests of one"
        f" {_ECHO_BLOB_BYTES} byte blob each, posted one after another by a"
        f" WirePort on the page to {_LOOP_OPTION} {_ECHO_LOOP_NAME}, came"
        f" back equal by sha256 {digest[:12]}; {seconds:.2f} s,"
        f" {rate:.1f} MiB/s each way; ttyd's resident size"
        f" {before.resident} KiB before and {after.resident} KiB after,"
        f" its peak {after.peak} KiB"
    )


# The engine pages of stage 0: every way a fault reaches the screen.
def rungs_faults(session: PageSession) -> None:
    log = session.log
    subtitle = seed_subtitle()
    log.rung_run(
        "stage 0: thrown error", lambda: rung_thrown(session, subtitle)
    )
    log.rung_run("stage 0: first fault only", lambda: rung_first(session))
    log.rung_run("stage 0: reload", lambda: rung_reload(session, subtitle))
    log.rung_run(
        "stage 0: rejection", lambda: rung_rejection(session, subtitle)
    )
    resources: list[tuple[str, str, dict[str, str], str]] = [
        ("script", "script", {"src": "/rung-missing.js"}, "src"),
        ("image", "img", {"src": "/rung-missing.png"}, "src"),
        (
            "link",
            "link",
            {"rel": "stylesheet", "href": "/rung-missing.css"},
            "href",
        ),
    ]
    for name, tag, attributes, address in resources:
        due = f'{_RESOURCE_FAILURE}{tag} {address}="{attributes[address]}"'
        log.rung_run(
            f"stage 0: failing {name}",
            lambda: rung_resource(session, subtitle, tag, attributes, due),
        )
    log.rung_run(
        "stage 0: failing with neither address",
        lambda: rung_resource(
            session,
            subtitle,
            "img",
            {"srcset": "/rung-missing-set.png"},
            _ADDRESS_MISSING + "img",
        ),
    )
    log.rung_run("stage 0: worker fault posted", lambda: rung_posted(session))
    log.rung_run("stage 0: worker throws at load", lambda: rung_load(session))
    log.rung_run("stage 0: write versus append", lambda: rung_append(session))


# The probe page of stages 5 and 8: the ports on the page's main thread.
def rungs_probe(session: PageSession, context: RunContext) -> None:
    log = session.log
    stub = context.stub
    closed = context.closed_port
    identifier = session.preload_add(_WORKER_STUB)
    log.rung_run("stage 5: input before render", lambda: rung_idle(session))
    log.rung_run("stage 5: wire hello", lambda: rung_hello(session))
    log.rung_run("stage 5: message_max round trip", lambda: rung_round(session))
    log.rung_run("stage 5: message_max plus one refused", lambda: rung_over(session))
    log.rung_run("stage 5: wire_close", lambda: rung_close(session))
    log.rung_run("stage 5: error line then close", lambda: rung_error(session))
    log.rung_run("stage 5: http post", lambda: rung_post(session, stub))
    log.rung_run("stage 5: http preflight", lambda: rung_preflight(stub))
    log.rung_run("stage 5: http text and json", lambda: rung_answers(session, stub))
    log.rung_run("stage 5: http statuses", lambda: rung_statuses(session, stub))
    log.rung_run("stage 5: http closed port", lambda: rung_refused(session, closed))
    log.rung_run("stage 5: http never answers", lambda: rung_never(session, stub))
    log.rung_run("stage 5: http stalled body", lambda: rung_stall(session, stub))
    log.rung_run("stage 5: http one line per request", lambda: rung_single(session, stub))
    log.rung_run("stage 5: http out of order", lambda: rung_order(session, stub))
    log.rung_run("stage 5: http get with a body", lambda: rung_body(session, stub))
    log.rung_run("stage 5: http port in a worker", lambda: rung_worker(session, stub))
    log.rung_run("stage 5: queue scheduling", lambda: rung_schedule(session))
    log.rung_run("stage 5: queue thread port", lambda: rung_thread(session))
    log.rung_run("stage 5: queue two replies", lambda: rung_pair(session, stub))
    png = bytes(cast(list[int], session.probe_call("png_bytes")))
    stub.png = png
    budget: int = session.values["media_db_bytes"]
    log.rung_run("stage 8: media png kept", lambda: rung_store(session, png, budget))
    log.rung_run(
        "stage 8: media download as blob 1",
        lambda: rung_fetch(session, stub, png, budget),
    )
    log.rung_run(
        "stage 8: media network failure",
        lambda: rung_lost(session, closed, budget),
    )
    log.rung_run(
        "stage 8: media status", lambda: rung_missing(session, stub, budget)
    )
    log.rung_run("stage 8: media timeout", lambda: rung_late(session, stub, budget))
    log.rung_run("stage 8: media undecodable", lambda: rung_garbage(session, budget))
    log.rung_run("stage 8: media eviction", lambda: rung_evict(session, png))
    log.rung_run(
        "stage 5: http throwing receiver", lambda: rung_receiver(session, stub)
    )
    log.rung_run("stage 5: decoder fault", lambda: rung_decoder(session))
    log.rung_run("stage 5: close without error line", lambda: rung_silent(session))
    log.rung_run("stage 5: queue handler throws", lambda: rung_handler(session))
    log.rung_run(
        "stage 7: console open, close, exit, open",
        lambda: rung_cycle(session),
    )
    waits = _WIRE_SECONDS + _RUNG_SECONDS
    log.rung_run(
        "stage 5: wire token timer", lambda: rung_token(session, stub), waits
    )
    log.rung_run(
        "stage 5: wire open timer", lambda: rung_opening(session, stub), waits
    )
    log.rung_run(
        "stage 7: console closed before open",
        lambda: rung_closing(session, stub),
    )
    session.preload_remove(identifier)


# The root whose ttyd runs a main loop that never writes hello.
def rungs_stalled(session: PageSession) -> None:
    session.log.rung_run(
        "stage 5: wire hello timer",
        lambda: rung_stalled(session),
        _WIRE_SECONDS + _RUNG_SECONDS,
    )


# The root whose ttyd asks a credential, the ports on the page's thread.
def rungs_credential(session: PageSession) -> None:
    identifier = session.preload_add(_WORKER_STUB)
    session.log.rung_run(
        "stage 7: token with a credential",
        lambda: rung_credential(session),
    )
    session.preload_remove(identifier)


# The root whose ttyd runs the echo main loop, the port on the page's thread.
def rungs_echo(session: PageSession) -> None:
    identifier = session.preload_add(_WORKER_STUB)
    session.log.rung_run(
        "stage 5: echo 128 MiB from the page",
        lambda: rung_large(session),
        _ECHO_SECONDS,
    )
    session.preload_remove(identifier)


# The engine page with debug false: the gates of the page and the server.
def rungs_release(session: PageSession) -> None:
    log = session.log
    subtitle = seed_subtitle()
    log.rung_run("stage 5: debug gating", lambda: rung_gating(session, subtitle))
    log.rung_run("stage 7: console role refused", lambda: rung_refused_role(session))


# The first synchronous root: its run recorded, then stage 6's loads.
def rungs_first(session: PageSession, recorded: list[list[str]]) -> None:
    log = session.log
    subtitle = seed_subtitle()
    log.rung_run(
        "stage 5: synchronous run recorded",
        lambda: rung_recorded(session, subtitle, recorded),
    )
    log.rung_run("stage 6: second load", lambda: rung_reopen(session, subtitle))
    log.rung_run("stage 6: start replacement", lambda: rung_replace(session))
    log.rung_run("stage 6: desync reload", lambda: rung_desync(session))


# The second synchronous root: the same run again.
def rungs_second(session: PageSession, recorded: list[list[str]]) -> None:
    subtitle = seed_subtitle()
    session.log.rung_run(
        "stage 5: synchronous run identical twice",
        lambda: rung_twice(session, subtitle, recorded),
    )


# The main engine root: stages 5 to 8 on one page, then two more loads.
def rungs_main(session: PageSession) -> None:
    log = session.log
    subtitle = seed_subtitle()
    calls = calls_make(session.values)
    log.rung_run("stage 5: hello relay", lambda: rung_relay(session, subtitle))
    scene = cast(str, text_read(session, "/metaverse/scene"))
    log.rung_run("stage 5: verbose ring", lambda: rung_ring(session))
    log.rung_run("stage 5: verbose sink", lambda: rung_sink(session))
    log.rung_run("stage 5: overlay strings", lambda: rung_strings(session))
    log.rung_run("stage 5: overlay keys", lambda: rung_keys(session))
    log.rung_run("stage 5: overlay lines", lambda: rung_lines(session))
    log.rung_run("stage 5: verbose batching", lambda: rung_batch(session))
    log.rung_run("stage 5: overlay style", lambda: rung_style(session))
    log.rung_run("stage 5: overlay survey", lambda: rung_survey(session))
    log.rung_run(
        "stage 7: keystrokes dropped before the first message",
        lambda: rung_early(session),
    )
    log.rung_run("stage 7: console open", lambda: rung_console(session))
    log.rung_run("stage 7: console echo", lambda: rung_echo(session))
    log.rung_run("stage 7: console run", lambda: rung_run(session, scene, calls))
    log.rung_run("stage 7: permit deny", lambda: rung_deny(session, scene, calls))
    log.rung_run(
        "stage 7: console run timeout",
        lambda: rung_timeout(session, scene, calls),
    )
    log.rung_run("stage 7: console interrupt", lambda: rung_interrupt(session))
    log.rung_run(
        "stage 7: console fed while hidden",
        lambda: rung_hidden(session, scene, calls),
    )
    log.rung_run(
        "stage 7: verbose level tool", lambda: rung_level(session, scene, calls)
    )
    log.rung_run(
        "stage 6: table from the AI", lambda: rung_pairs(session, scene, calls)
    )
    log.rung_run(
        "stage 6: overflow through OPFS",
        lambda: rung_overflow(session, scene, calls),
    )
    log.rung_run(
        "stage 6: cache exhaustion", lambda: rung_cache(session, scene, calls)
    )
    log.rung_run(
        "stage 6: pool exhaustion", lambda: rung_pool(session, scene, calls)
    )
    png = bytes(cast(list[int], session.probe_call("png_bytes")))
    log.rung_run("stage 8: scripted turn", lambda: rung_turn(session, scene, png))
    log.rung_run(
        "stage 8: time without input", lambda: rung_still(session, scene)
    )
    log.rung_run("stage 8: image visible", lambda: rung_image(session))
    log.rung_run("stage 8: subtitle visible", lambda: rung_subtitle(session))
    log.rung_run("stage 8: input visible", lambda: rung_input(session))
    log.rung_run("stage 8: console visible", lambda: rung_terminal(session))
    log.rung_run("stage 8: overlay visible", lambda: rung_overlay(session))
    log.rung_run("stage 8: overlay wide", lambda: rung_wide(session))
    log.rung_run("stage 8: overlay toggle", lambda: rung_toggle(session))
    log.rung_run("stage 8: long tasks", lambda: rung_long(session))
    log.rung_run("stage 7: console exit", lambda: rung_exit(session))
    log.rung_run("stage 8: start with a scene image", lambda: rung_scene(session, png))
    log.rung_run("stage 8: click on the image", lambda: rung_click(session))
    log.rung_run("stage 5: second hello", lambda: rung_restart(session))


# Makes a root, serves it through ttyd and runs `body` on its page.
def session_run(
    context: RunContext,
    name: str,
    page: str,
    overrides: dict[str, Any],
    extras: ServerExtras,
    place: Callable[[str, dict[str, Any]], None],
    body: Callable[[PageSession], None],
) -> None:
    log = context.log
    root, index, values = root_make(context.work, name, page, overrides)
    place(root, values)
    log.rung_start(f"ttyd for the root {name}", _RUNG_SECONDS)
    with TtydServer(root, index, values, extras, log) as ttyd:
        session = PageSession(context.browser, log, ttyd, values)
        body(session)
        log.rung_start(f"leaving the root {name}", _RUNG_SECONDS)
        session.page_leave()


# The stub's own page, which proves the browser reaches it first.
def rung_reachable(context: RunContext) -> str:
    url = context.stub.url_make(_TEXT_PATH)
    context.browser.page_open(url)
    return f"the browser loaded {url} from the stub HTTP server"


# Builds both pages, then runs every root's rungs in one browser.
def stages_run(log: RungLog, work: str) -> None:
    import devtools, page_build

    pages: list[str] = []
    for name, test in ((_TEST_PAGE, True), (_ENGINE_PAGE, False)):
        log.rung_start(f"build {name}", _RUNG_SECONDS)
        digest = page_build.page_build(name, test)
        pages.append(os.path.join(_BUILD_PATH, f"{name}.html"))
        log.rung_print(f"built {pages[-1]}, sha256 {digest}")
    test_page, engine_page = pages
    os.makedirs(_PNG_PATH, exist_ok=True)
    closed = port_closed()
    synchronous = {"queue_synchronous": True, "verbose_level": 2}
    recorded: list[list[str]] = []
    with (
        StubServer() as stub,
        devtools.Browser(_WINDOW_WIDTH, _WINDOW_HEIGHT) as browser,
    ):
        browser.console_follow(console_copy)
        context = RunContext(
            browser, log, work, stub, test_page, engine_page, closed
        )
        session_run(
            context,
            "suites",
            test_page,
            {},
            _EXTRAS_NONE,
            nothing_place,
            lambda session: log.rung_run(
                "stage 0: typescript suites",
                lambda: rung_suites(session),
                _SUITES_SECONDS,
            ),
        )
        session_run(
            context,
            "faults",
            engine_page,
            {},
            _EXTRAS_NONE,
            scripts_place,
            rungs_faults,
        )
        log.rung_run("stage 5: stub reachable", lambda: rung_reachable(context))
        session_run(
            context,
            "probe",
            engine_page,
            {},
            _EXTRAS_NONE,
            nothing_place,
            lambda session: rungs_probe(session, context),
        )
        session_run(
            context,
            "credential",
            engine_page,
            {},
            ServerExtras((_CREDENTIAL_OPTION, _CREDENTIAL), ()),
            nothing_place,
            rungs_credential,
        )
        session_run(
            context,
            "echo",
            engine_page,
            {"debug": True},
            ServerExtras((), (_LOOP_OPTION, _ECHO_LOOP_NAME)),
            echo_place,
            rungs_echo,
        )
        session_run(
            context,
            "stalled",
            engine_page,
            {"debug": True},
            ServerExtras((), (_LOOP_OPTION, _STALL_LOOP_NAME)),
            stall_place,
            rungs_stalled,
        )
        session_run(
            context,
            "release",
            engine_page,
            {"debug": False},
            _EXTRAS_NONE,
            scripts_place,
            rungs_release,
        )
        session_run(
            context,
            "first",
            engine_page,
            synchronous,
            _EXTRAS_NONE,
            scripts_place,
            lambda session: rungs_first(session, recorded),
        )
        session_run(
            context,
            "second",
            engine_page,
            synchronous,
            _EXTRAS_NONE,
            scripts_place,
            lambda session: rungs_second(session, recorded),
        )
        session_run(
            context,
            "main",
            engine_page,
            {},
            _EXTRAS_NONE,
            restart_place,
            rungs_main,
        )


# Exits with 128 plus the signal's number, so the blocks stop what they run.
def signal_exit(number: int, frame: types.FrameType | None) -> None:
    sys.exit(_SIGNAL_BASE + number)


# Runs the rungs in order, printing a line each, and returns the exit code.
def main() -> int:
    argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description="Run the browser test: the TypeScript suites on the test"
        " page and the rungs of the engine page, in roots under build/,"
        " through the ttyd the install script builds, in headless Chrome.",
    ).parse_args(sys.argv[1:])
    for number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(number, signal_exit)
    log = RungLog()
    try:
        if not os.path.isfile(_TTYD_PATH):
            raise CheckFailed(
                f"{_TTYD_PATH} is missing: {_INSTALL_SCRIPT} builds it"
            )
        with tempfile.TemporaryDirectory(
            prefix=_WORK_PREFIX, dir=_BUILD_PATH
        ) as work:
            stages_run(log, work)
    except CheckFailed as failure:
        print(f"error: {log.rung}: {failure}", file=sys.stderr)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        return _EXIT_INTERRUPTED
    return 0


if __name__ == "__main__":
    sys.exit(main())
