#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The browser test. It builds the one page with page_build.py, makes server
# roots under build/ as the start script makes them, each with settings.json
# and test_settings.json, keeping them after the run, serves each through the
# ttyd xsjs_install.ps1 builds, and drives headless Chrome or Edge through
# devtools.py, rung by rung, each rung under a timer and named by the stage of
# the plan it proves. The suites root runs the TypeScript suites over TAP and
# checks the TAP file the server keeps with the TAP consumer. The other rungs
# drive the one page's modules through the probe kit, a stub HTTP server of
# this process and the server, and check what the page shows and what the
# server holds. Some roots name a main loop file in ttyd's command, and one
# has ttyd ask a credential. PNGs of the surveyed states go to
# build/test_browser/. Each root and each rung is labelled smoke-test or
# normal-test: a smoke-test run, the default, runs the
# rungs labelled smoke-test and starts no ttyd and no page for a root with
# none, a normal-test run runs every rung, and a mislabel fails the run. It
# prints one line per rung that runs, ending with its label and seconds, and
# one per request for /favicon.ico, which the stub answers 404, and exits 0,
# or stops at the first failed check, names its rung and exits 1. ttyd's log
# and the page's console are copied to stderr. Its timers, sizes and the
# roots' pinned settings, the texts it expects and the headers it checks
# come from its gold, python.test_browser of test_settings.json, read through
# harness.py, and the values of settings.json it repeats from that file; the
# server's databases are read with sqlite3 by the substrate's tables. It
# imports the standard library and the infrastructure for testing only, and
# ttyd, the browser and tsc through page_build.py are the programs it starts:
#
#     python3 python/test_browser.py [--smoke-test | --normal-test]

import argparse, base64, contextlib, fcntl, hashlib, http.server, json, os, re
import select, shutil, signal, socket, sqlite3, subprocess, sys, tempfile
import threading, time, traceback, types
from collections.abc import Callable, Generator
from typing import Any, NamedTuple, Protocol, Self, cast

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The checkout, which holds the `python` directory.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# The build directory: the pages, each run's roots, the PNGs and bytecode.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# The id of this driver's gold in `test_settings.json`.
_GOLD_ID = "python.test_browser"

# The script that builds ttyd, which a missing ttyd names.
_INSTALL_SCRIPT = "xsjs_install.ps1"

# The start of the name of the directory each run makes and keeps its roots in.
_WORK_PREFIX = "test_browser-"

# The directory the PNGs of the surveyed states go to, kept after the run.
_PNG_PATH = os.path.join(_BUILD_PATH, "test_browser")

# The name of the test settings, the gold record, in a root.
_TEST_SETTINGS_NAME = "test_settings.json"

# The TypeScript run of the browser test: the unit suites of both threads.
_RUN_UNIT = "unit"

# The strings file, which the start script copies into the root.
_STRINGS_PATH = os.path.join(_CHECKOUT_PATH, "i18n", "en-US.json")

# The seed directory, which the start script copies into the root.
_SEED_PATH = os.path.join(_PYTHON_PATH, "seed")

# The seed of the scripted provider's script, which a fresh root holds.
_SEED_SCRIPT_PATH = os.path.join(_SEED_PATH, "provider_script.json")

# The template the page is built from, that of the ttyd test page.
_PAGE_TEMPLATE = "test"

# The name the one page is built under, as the plan names it.
_PAGE_NAME = "test"

# The page `page_build.py` writes under that name, which each root copies.
_PAGE_PATH = os.path.join(_BUILD_PATH, f"{_PAGE_NAME}.html")

# The directory of a root that holds the main loop files.
_MAIN_LOOP_DIRECTORY = "main_loop"

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

# The file of the root whose lock one engine at a time holds.
_LOCK_FILE = "engine.lock"

# The TAP file in the root that the server appends the page's lines to.
_TAP_FILE = os.path.join("tap", "typescript.tap")

# The line that starts each TAP document.
_TAP_VERSION = "TAP version 14"

# The start of the line the server ends the TAP file with on a page fault.
_BAIL_PREFIX = "Bail out! "

# The TAP documents the page writes: the AI worker's, then the UI thread's.
_TAP_DOCUMENTS = 2

# The modules of the AI worker's stream, in the order the plan runs them.
_AI_MODULES = (
    "test_tap_producer",
    "test_unittest",
    "test_harness",
    "test_error_overlay",
    "test_ui_strings",
    "test_i18n",
    "test_utility",
    "test_settings",
    "test_verbose",
    "test_jslb",
    "test_dispatch",
    "test_queue",
    "test_http",
    "test_wire",
    "test_wire_end",
    "test_provider",
    "test_provider_key_unset",
    "test_provider_key",
    "test_mcp",
    "test_substrate",
    "test_substrate_store",
    "test_jslb_decode",
    "test_wire_port",
    "test_script",
    "test_provider_script",
    "test_tools_browser",
    "test_agent",
    "test_worker_ai",
)

# The modules of the UI thread's stream, in the order the plan runs them.
_UI_MODULES = (
    "test_tap_producer",
    "test_unittest",
    "test_error_overlay",
    "test_media",
    "test_integrate_media",
    "test_console_view",
    "test_overlay",
    "test_page",
    "test_boot",
)

# The name `argparse` shows, as `sys.argv` may be empty.
_PROGRAM_NAME = "test_browser.py"

# The whole seconds wire.ts waits for a token, an open and the first line.
_WIRE_SECONDS = 120

# The option that names the page ttyd serves.
_INDEX_OPTION = "--index"

# The option, patched into the release, that sets ttyd's receive chunk size.
_BUFFER_OPTION = "--srv-buf-size"

# The fields of a `ServerExtras` adding nothing, as the start script serves.
_EXTRAS_NONE = ((), ())

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

# The header that lets the page read a response of another origin.
_CORS_ORIGIN = "Access-Control-Allow-Origin"

# The status of a request that succeeded.
_HTTP_OK = 200

# The status of an answer with no body.
_NO_CONTENT = 204

# The status a missing file gets: a media download's and the stub's icon's.
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

# The icon the browser asks of a page it opens, which the stub answers 404.
_FAVICON_PATH = "/favicon.ico"

# The start of the stub's paths that answer with a status.
_STATUS_PREFIX = "/status/"

# The stub's path that never answers.
_SILENT_PATH = "/silent"

# The stub's path that sends its head and part of its body, then stalls.
_STALL_PATH = "/stall"

# The body length the stalled answer announces, more than it sends.
_STALL_LENGTH = 100

# The stub's path answered only once the rung releases it, after a timeout.
_LATE_PATH = "/late"

# The start of the stub's paths, each held until the order rung releases it.
_ORDER_PREFIX = "/order/"

# The stub's path answered only after the second one.
_FIRST_PATH = "/pair/first"

# The stub's path answered at once.
_SECOND_PATH = "/pair/second"

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

# The ref the `blob_max` rungs put their value under.
_ROUND_REF = "/_files/rung/round.bin"

# A type no handler serves.
_UNKNOWN_TYPE = "rung.unknown"

# The id of the line of the unknown type.
_UNKNOWN_ID = 7

# The close code a browser reports when the connection ended with no frame.
_CLOSE_LOST = 1006

# The period of the byte pattern of the rungs' blobs.
_PATTERN_PERIOD = 251

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

# The command that ends dash.
_EXIT_COMMAND = "exit"

# The prompt dash writes when it waits for a command.
_PROMPT_TEXT = "$ "

# The character that starts a message of ttyd's client carrying input.
_INPUT_KIND = "0"

# The whole seconds wire.ts waits for its socket to send its buffered bytes.
_DRAIN_SECONDS = 120

# The SAH pool the kill rung's workers open, apart from the test page's.
_KILL_POOL = "xsjs-kill-pool"

# The OPFS directory of that pool.
_KILL_DIRECTORY = ".xsjs-kill-pool"

# The OPFS directory of the kill rung's cache files.
_KILL_SLOTS_DIRECTORY = "xsjs-kill-cache"

# The root of the kill rung's store in that pool.
_KILL_ROOT = "/kill"

# The check after the kill: no row of the value, its cache file removed.
_KILL_DUE = {"rows": 0, "removed": 1}

# The thread whose lines the AI worker sends to the server.
_AI_THREAD = "ai"

# The thread under which the server keeps the lines it logs itself.
_SERVER_THREAD = "server"

# The first byte of a ttyd message of program output.
_OUTPUT_KIND = 0x30

# Replaces `Worker` so that the page starts no worker of its own.
_WORKER_STUB = """globalThis.xsjs_worker_original = globalThis.Worker;
globalThis.Worker = class {
  postMessage() {}
  terminate() {}
};
"""

# Adds a prefix and a suffix to the text of every script `Blob`.
_BLOB_PATCH = """(() => {
  const OriginalBlob = globalThis.Blob;
  globalThis.Blob = class extends OriginalBlob {
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
  probe.summary_make = (line) => ({
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
  probe.receiver_make = (name) => {
    probe.lines[name] = [];
    return (line) => {
      probe.lines[name].push(probe.summary_make(line));
    };
  };
  probe.http_port = (name, seconds) => {
    const port = new http.HttpPort(seconds);
    port.line_receive(probe.receiver_make(name));
    probe.ports[name] = port;
    return true;
  };
  probe.media_port = (name, budget, seconds) => {
    const port = new media.MediaPort(budget, seconds);
    port.line_receive(probe.receiver_make(name));
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
  probe.pattern_make = (size) => {
    const data = new Uint8Array(size);
    for (let index = 0; index < size; index += 1) {
      data[index] = index % 251;
    }
    return data;
  };
  probe.thrown_message = (fn) => {
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
    const record = { first: null, lines: [], closes: [] };
    const values = {};
    const port = new wire.WirePort(base, probe.sink, (id) => values[id]);
    port.line_receive((line) => {
      record.lines.push(probe.summary_make(line));
      probe.sink_free(line);
    });
    port.close_receive((code, had_error) => {
      record.closes.push([code, had_error]);
    });
    port.wire_open((first) => {
      record.first = probe.summary_make(first);
      Object.assign(values, jslb.payload_of(first).settings);
      port.line_post(dispatch.reply_make(first, {}), []);
    });
    probe.wire[name] = { port, record };
    return true;
  };
  probe.wire_first = (name) => probe.wire[name].record.first;
  probe.wire_lines = (name, count) => {
    const lines = probe.wire[name].record.lines;
    return lines.length >= count ? lines : null;
  };
  probe.wire_closes = (name) => {
    const closes = probe.wire[name].record.closes;
    return closes.length > 0 ? closes : null;
  };
  probe.put_refused = (name, key, size) =>
    probe.thrown_message(() => {
      const header = jslb.header_make("kv.put", { key });
      const blob = jslb.blob_make(probe.pattern_make(size));
      probe.wire[name].port.line_post(jslb.line_make(header, [blob], {}), []);
    });
  probe.wire_send = (name, type, options, payload) => {
    const header = jslb.header_make(type, options);
    probe.wire[name].port.line_post(jslb.line_make(header, [], payload), []);
    return true;
  };
  probe.wire_close = (name) => {
    probe.wire[name].port.wire_close();
    return true;
  };
  probe.token_read = (url) =>
    fetch(url, { cache: "no-store" }).then((response) =>
      response.text().then((text) => ({ status: response.status, text })),
    );
  probe.hit_test = (element, x, y) => {
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
      center_hit: probe.hit_test(element, x, y),
      text: element.textContent,
      disabled: element.disabled === true,
    };
  };
  probe.fault_text = () => {
    const pre = document.querySelector("body > pre:not(#tap_output)");
    return pre === null ? null : pre.textContent;
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
  probe.tap_kept = () => document.querySelector("#tap_output") !== null;
  probe.settings_shown = () => (settings.names_full() ? null : true);
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
  probe.svg_add = (href) => {
    const space = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(space, "svg");
    const image = document.createElementNS(space, "image");
    const xlink = "http://www.w3.org/1999/xlink";
    image.setAttributeNS(xlink, "xlink:href", href);
    svg.append(image);
    document.body.append(svg);
    return true;
  };
  probe.overlay_again = (message) => {
    error_overlay.overlay_show(message, "");
    return document.querySelectorAll("pre").length;
  };
  probe.history_get = () =>
    verbose.history_get(settings.settings_get("verbose_ring"));
  probe.sink_twice = () =>
    probe.thrown_message(() => verbose.sink_set(() => undefined));
  probe.ring_refused = () =>
    probe.thrown_message(() =>
      new overlay.Overlay(document.createElement("div"), 0),
    );
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
  probe.worker_source = (code) => {
    const scripts = Array.from(
      document.querySelectorAll("script[data-worker]"),
    );
    const texts = scripts.slice(0, -1).map((script) => script.text);
    const source = '"use strict";\n' + texts.join("\n") + "\n" + code;
    return URL.createObjectURL(
      new Blob([source], { type: "text/javascript" }),
    );
  };
  probe.worker_make = (code) =>
    new globalThis.xsjs_worker_original(probe.worker_source(code), {
      name: "probe",
    });
  probe.worker_real = (code, name) =>
    new Worker(probe.worker_source(code), { name });
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
      probe.thread_replies = wake.replies.map((line) =>
        probe.summary_make(line),
      );
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
      probe.pair_replies = wake.replies.map((line) =>
        probe.summary_make(line),
      );
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
      "  const reply = jslb.payload_of(line);",
      "  self.postMessage({ header: line[0], payload: reply });",
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
  probe.console_port = (base) => {
    const record = { lines: [], closes: [] };
    const port = new wire.ConsolePort(base);
    port.line_receive((line) => record.lines.push(probe.console_line(line)));
    port.close_receive((code) => record.closes.push(code));
    probe.console = record;
    probe.console_kept = port;
    return true;
  };
  probe.console_ask = (id) => {
    const header = jslb.header_make("console.open", { id });
    probe.console_kept.line_post(jslb.line_make(header, [], {}), []);
    return true;
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
  probe.echo_burst = (name, count, size) => {
    const port = probe.wire[name].port;
    const data = probe.pattern_make(size);
    for (let number = 1; number <= count; number += 1) {
      const header = jslb.header_make("echo", { id: number });
      port.line_post(jslb.line_make(header, [jslb.blob_make(data)], {}), []);
    }
    return true;
  };
  probe.wire_pending = (name) => {
    const port = probe.wire[name].port;
    return {
      buffered: port.socket.bufferedAmount,
      polling: port.poll_id !== undefined,
    };
  };
  probe.sync_get = () => {
    const request = new XMLHttpRequest();
    request.open("GET", location.href, false);
    request.send();
    return request.status;
  };
  probe.kill_code = (options, body) =>
    [
      "(() => {",
      "  const options = " + JSON.stringify(options) + ";",
      "  const slots_open = () =>",
      "    navigator.storage",
      "      .getDirectory()",
      "      .then((root) =>",
      "        root.getDirectoryHandle(options.slot_directory, {",
      "          create: true,",
      "        }),",
      "      )",
      "      .then((directory) =>",
      "        Promise.all(",
      "          Array.from({ length: options.slots }, (_value, index) =>",
      "            directory",
      "              .getFileHandle(String(index), { create: true })",
      "              .then((file) => file.createSyncAccessHandle()),",
      "          ),",
      "        ),",
      "      );",
      "  const binary = utility.base64_decode(sqlite3_wasm_base64);",
      "  sqlite3InitModule({ wasmBinary: binary })",
      "    .then((sqlite3) =>",
      "      sqlite3",
      "        .installOpfsSAHPoolVfs({",
      "          name: options.pool,",
      "          directory: options.directory,",
      "          initialCapacity: options.capacity,",
      "          clearOnInit: options.clear,",
      "        })",
      "        .then((pool) =>",
      "          slots_open().then((slots) => {",
      "            const cache = new substrate.CacheFiles(slots);",
      ...body,
      "          }),",
      "        ),",
      "    )",
      "    .catch((error) => {",
      "      self.postMessage({ fault: String(error.stack) });",
      "    });",
      "})();",
    ].join("\n");
  probe.kill_put_body = [
    "const store = new substrate.Store(",
    "  sqlite3,",
    "  test_substrate_store.kill_pool(pool, () =>",
    "    test_substrate_store.kill_hold(() =>",
    "      self.postMessage({ paused: true }),",
    "    ),",
    "  ),",
    "  cache,",
    "  options.root,",
    "  options.overflow,",
    "  options.compact,",
    "  { line_notify: () => undefined },",
    ");",
    "test_substrate_store.kill_put(store);",
  ];
  probe.kill_check_body = [
    "const store = new substrate.Store(",
    "  sqlite3,",
    "  pool,",
    "  cache,",
    "  options.root,",
    "  options.overflow,",
    "  options.compact,",
    "  { line_notify: () => undefined },",
    ");",
    "self.postMessage({ checked: test_substrate_store.kill_check(store) });",
  ];
  probe.kill_run = (options) => {
    probe.kill = null;
    const fault_keep = (text) => {
      probe.kill = { fault: text };
    };
    const first = probe.worker_real(
      probe.kill_code({ ...options, clear: true }, probe.kill_put_body),
      "kill_put",
    );
    first.onerror = (event) => fault_keep(String(event.message));
    first.onmessage = (event) => {
      if (event.data.paused !== true) {
        fault_keep(JSON.stringify(event.data));
        return;
      }
      first.terminate();
      const second = probe.worker_real(
        probe.kill_code({ ...options, clear: false }, probe.kill_check_body),
        "kill_check",
      );
      second.onerror = (event) => fault_keep(String(event.message));
      second.onmessage = (event) => {
        probe.kill = event.data;
      };
    };
    return true;
  };
  probe.kill_when = () => probe.kill;
  globalThis.xsjs_probe = probe;
  return true;
})()
"""

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# A check that failed, with the measurement that failed it.
class CheckFailed(Exception):
    pass


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
    text: str


# What a root adds to ttyd's options and to its command.
class ServerExtras(NamedTuple):
    options: tuple[str, ...]
    arguments: tuple[str, ...]


# The DevTools calls the rungs make beyond the browser's own methods.
class DriverClient(Protocol):
    # Returns the result of a DevTools method on the page.
    def method_call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    # Passes events on until the condition holds.
    def events_pump(self, what: str, done: Callable[[], bool]) -> None: ...

    # Ends every later DevTools wait at `end` when that comes first.
    def deadline_set(self, end: float) -> None: ...


# The page loads the browser has seen: loader and event name pairs.
class LifecycleEvents(Protocol):
    lifecycle: set[tuple[str, str]]


# The browser of `devtools.py` as the rungs use it.
class BrowserDriver(Protocol):
    # The page loads seen, read only here so that `PageEvents` matches.
    @property
    def events(self) -> LifecycleEvents: ...

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

    # Pauses the page's worker of that name in its debugger, waiting for it.
    def worker_pause(self, name: str) -> None: ...

    # Starts a trace of the categories on the page.
    def trace_start(self, categories: list[str]) -> None: ...

    # Ends the trace and returns its events.
    def trace_end(self) -> list[dict[str, Any]]: ...


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


# The rung that runs, its timer and start, the labels, and each rung's line.
class RungLog:
    # Starts on the build, before any rung, checking the category's labels.
    def __init__(self, chosen: str) -> None:
        import category

        self.book = category.LabelBook(chosen)
        self.rung = "build"
        self.timer = RungTimer(self.rung, gold_value("rung_seconds"))
        self.started = time.monotonic()
        self.lock = threading.Lock()
        self.client: DriverClient | None = None

    # Has each rung's timer from now on bound the client's DevTools waits.
    def client_bind(self, client: DriverClient) -> None:
        self.client = client
        client.deadline_set(self.timer.end)

    # Names the rung that runs now and starts its timer and its seconds.
    def rung_start(self, rung: str, seconds: float) -> None:
        if self.client is None:
            raise RuntimeError(f"the rung {rung} started before the browser")
        self.rung = rung
        self.timer = RungTimer(rung, seconds)
        self.started = time.monotonic()
        self.client.deadline_set(self.timer.end)

    # Prints one whole line, as the stub's threads print notes too.
    def line_print(self, text: str) -> None:
        with self.lock:
            print(text, flush=True)

    # Prints the summary of the rung that ran, its label and its seconds.
    def rung_print(self, summary: str, label: str) -> None:
        seconds = time.monotonic() - self.started
        self.line_print(f"{self.rung}: {summary} ({label}, {seconds:.3f} s)")

    # Prints a setup step's summary and its seconds, as setup has no label.
    def setup_print(self, summary: str) -> None:
        seconds = time.monotonic() - self.started
        self.line_print(f"{self.rung}: {summary} ({seconds:.3f} s)")

    # Prints a note of the rung that runs, such as an answer of the stub.
    def note_print(self, note: str) -> None:
        self.line_print(f"{self.rung}: {note}")

    # Runs a rung under its timer, the gold's `rung_seconds` unless given.
    def rung_run(
        self,
        rung: str,
        label: str,
        check: Callable[[], str],
        seconds: float | None = None,
    ) -> None:
        if not self.book.rung_enter(rung, label):
            return
        timer = gold_value("rung_seconds") if seconds is None else seconds
        self.rung_start(rung, timer)
        self.rung_print(check(), label)


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
        self.version = ttyd_path()
        self.lines: list[str] = []
        self.partial = b""
        self.port = 0
        self.fd, write_fd = os.pipe()
        try:
            self.process = subprocess.Popen(
                [
                    ttyd_path(),
                    "--port",
                    "0",
                    *ttyd_options(),
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
                start_new_session=True,
            )
        finally:
            with failure_held():
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
            seconds = gold_value("stop_seconds")
            raise CheckFailed(
                f"{self.version} still ran {seconds:g} s after SIGTERM and was"
                " killed"
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
        data = os.read(self.fd, gold_value("read_bytes"))
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
        with failure_held():
            stopped = True
            if self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGTERM)
                try:
                    self.process.wait(gold_value("stop_seconds"))
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait()
                    stopped = False
            while data := os.read(self.fd, gold_value("read_bytes")):
                self.lines_take(data)
            os.close(self.fd)
            if self.partial:
                sys.stderr.write(f"{self.partial.decode()}\n")
            return stopped


# A context whose exit runs with the stub's failure signal held off.
class HeldExit[T]:
    # Keeps the context to enter.
    def __init__(self, context: contextlib.AbstractContextManager[T]) -> None:
        self.context = context

    # Enters the context and returns what it gives.
    def __enter__(self) -> T:
        return self.context.__enter__()

    # Exits the context, a failure of the stub landing once the exit is done.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> bool | None:
        with failure_held():
            return self.context.__exit__(exception_type, exception, traceback)


# A local HTTP server the page's ports talk to, answering by path.
class StubServer(http.server.ThreadingHTTPServer):
    # Listens on a port of its choosing with nothing taken yet.
    def __init__(self, log: RungLog) -> None:
        super().__init__((bind_address(), 0), StubHandler)
        self.log = log
        self.condition = threading.Condition()
        self.requests: list[StubRequest] = []
        self.answered: list[str] = []
        self.orders_released: set[int] = set()
        self.late_released = False
        self.late_outcome = ""
        self.released = False
        self.failure = ""
        self.failure_raised = False
        self.png = b""
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.main_id = cast(int, threading.main_thread().ident)
        self.handler_kept = signal.getsignal(signal.SIGUSR1)

    # Starts serving on a thread of its own, a handler's failure raised here.
    def __enter__(self) -> Self:
        signal.signal(signal.SIGUSR1, self.failure_raise)
        self.thread.start()
        return self

    # Lets held requests go, stops, restores the signal, raises a kept failure.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        with failure_held():
            with self.condition:
                self.released = True
                self.condition.notify_all()
            self.shutdown()
            self.thread.join()
            self.server_close()
            # A signal sent before the release waits blocked and is taken here.
            if signal.SIGUSR1 in signal.sigpending():
                signal.sigwait({signal.SIGUSR1})
            signal.signal(signal.SIGUSR1, self.handler_kept)
        if self.failure and not self.failure_raised:
            raise CheckFailed(self.failure)

    # Sends a handler's error, with its stack, in place of printing it.
    def handle_error(self, request: object, client_address: object) -> None:
        self.failure_send(traceback.format_exc())

    # Keeps the first failure, raised in the main thread before the release.
    def failure_send(self, text: str) -> None:
        with self.condition:
            if not self.failure:
                self.failure = text
                if not self.released:
                    signal.pthread_kill(self.main_id, signal.SIGUSR1)

    # Raises in the main thread the failure a handler sent.
    def failure_raise(
        self, number: int, frame: types.FrameType | None
    ) -> None:
        self.failure_raised = True
        raise CheckFailed(self.failure)

    # The address of a path of the stub.
    def url_make(self, path: str) -> str:
        port = cast(tuple[str, int], self.server_address)[1]
        return f"http://{bind_address()}:{port}{path}"

    # The WebSocket address of a path of the stub.
    def socket_make(self, path: str) -> str:
        port = cast(tuple[str, int], self.server_address)[1]
        return f"ws://{bind_address()}:{port}{path}"

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
                lambda: ready() or self.released, gold_value("hold_seconds")
            )

    # Holds a handler until the stub is released, past every wait of a page.
    def release_wait(self) -> None:
        with self.condition:
            self.condition.wait_for(lambda: self.released)

    # The requests of the method and path taken so far, in order.
    def requests_of(self, method: str, path: str) -> list[StubRequest]:
        with self.condition:
            return [
                request
                for request in self.requests
                if request.method == method and request.path == path
            ]

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

    # Lets the held answer of the order request of the number go.
    def order_release(self, number: int) -> None:
        with self.condition:
            self.orders_released.add(number)
            self.condition.notify_all()

    # Lets the held answer of the late path go.
    def late_release(self) -> None:
        with self.condition:
            self.late_released = True
            self.condition.notify_all()

    # Keeps what the late answer's write met, sent or the error it raised.
    def late_record(self, outcome: str) -> None:
        with self.condition:
            self.late_outcome = outcome
            self.condition.notify_all()


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

    # Records a POST with its body and answers it by its path.
    def do_POST(self) -> None:
        length = int(cast(str, self.headers["Content-Length"]))
        self.request_keep(self.rfile.read(length))
        path = self.path
        if path == _ECHO_PATH:
            self.json_send(_ECHO_ANSWER)
        else:
            raise ValueError(f"the stub serves no POST of {path}")

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
        elif path == _FAVICON_PATH:
            self.answer_send(_MISSING_STATUS, _TEXT_MEDIA, b"")
            stub.log.note_print(
                f"the stub answered GET {path} with {_MISSING_STATUS}"
            )
        elif path.startswith(_STATUS_PREFIX):
            status = int(path.removeprefix(_STATUS_PREFIX))
            self.answer_send(status, _TEXT_MEDIA, f"status {status}".encode())
        elif path == _SILENT_PATH:
            stub.hold_wait(lambda: False)
        elif path == _STALL_PATH:
            self.stall_send()
            stub.hold_wait(lambda: False)
        elif path == _LATE_PATH:
            stub.hold_wait(lambda: stub.late_released)
            try:
                self.answer_send(_HTTP_OK, _TEXT_MEDIA, _PLAIN_TEXT.encode())
            except (BrokenPipeError, ConnectionResetError) as error:
                stub.late_record(type(error).__name__)
            else:
                stub.late_record("sent")
        elif path.startswith(_ORDER_PREFIX):
            number = int(path.removeprefix(_ORDER_PREFIX))
            stub.hold_wait(lambda: number in stub.orders_released)
            self.json_send({"n": number})
        elif path == _FIRST_PATH:
            stub.hold_wait(lambda: _SECOND_PATH in stub.answered)
            self.json_send({"name": "first"})
        elif path == _SECOND_PATH:
            self.json_send({"name": "second"})
        elif path == _OPENING_BASE + _SOCKET_PATH:
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
    # Takes the browser, the rung log, ttyd and the root's two settings files.
    def __init__(
        self,
        browser: BrowserDriver,
        log: RungLog,
        ttyd: TtydServer,
        values: dict[str, Any],
        gold: dict[str, Any],
    ) -> None:
        self.browser = browser
        self.log = log
        self.ttyd = ttyd
        self.root = ttyd.root
        self.values = values
        self.gold = gold
        self.url = f"http://{bind_address()}:{ttyd.port}/"
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
            poll: float = gold_value("poll_seconds")
            time.sleep(min(poll, self.log.timer.seconds_left(what)))

    # Opens the page, keeping where ttyd's log stood, and installs the probes.
    def page_open(self) -> None:
        self.mark = len(self.ttyd.lines)
        self.browser.page_open(self.url)
        self.browser.script_evaluate(_PROBE_KIT)

    # Waits for the fault screen and returns its text.
    def fault_wait(self, what: str) -> str:
        return cast(str, self.probe_wait(what, "fault_text"))

    # Fails if the page shows the fault screen.
    def fault_none(self, what: str) -> None:
        fault = self.probe_call("fault_text")
        if fault is not None:
            raise CheckFailed(f"{what}: the page faulted: {fault}")

    # Waits until every program the page started since its mark has ended.
    def programs_wait(self, least: int, what: str) -> int:
        return self.ttyd.programs_wait(self.mark, least, what)

    # Leaves the page for a blank one and waits for its programs to end.
    def page_leave(self) -> None:
        self.browser.page_open(_BLANK_URL)
        self.programs_wait(0, "the end of the programs of the page left")

    # Clicks the left button at a point of the viewport.
    def mouse_click(self, x: float, y: float) -> None:
        client = self.browser.client_get()
        for kind in ("mousePressed", "mouseReleased"):
            client.method_call(
                "Input.dispatchMouseEvent",
                {
                    "type": kind,
                    "x": x,
                    "y": y,
                    "button": "left",
                    "clickCount": 1,
                },
            )

    # Clicks the middle of the box of an element's view.
    def view_click(self, view: dict[str, Any]) -> None:
        x = view["left"] + view["width"] / 2
        y = view["top"] + view["height"] / 2
        self.mouse_click(x, y)

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


# The parts every stage shares: the browser, the log, the page and the stub.
class RunContext(NamedTuple):
    browser: BrowserDriver
    log: RungLog
    work: str
    stack: contextlib.ExitStack
    stubs: list[StubServer]
    closed_port: int
    built: set[str]


# A value of this driver's gold, `python.test_browser` of the test settings.
def gold_value(name: str) -> Any:
    import harness

    return harness.gold_get(f"{_GOLD_ID}.{name}")


# A value of the checkout's `settings.json`, by its id.
def setting_value(name: str) -> Any:
    import harness

    return harness.setting_get(name)


# A text of the gold, each placeholder `values` names replaced by its value.
def text_fill(name: str, values: dict[int, object]) -> str:
    text: str = gold_value(f"texts.{name}")
    for number, value in values.items():
        placeholder = f"{{{number}}}"
        if placeholder not in text:
            raise ValueError(f"the gold text {name} has no {placeholder}")
        text = text.replace(placeholder, str(value))
    return text


# The address ttyd and the stub listen on, the start script's bind address.
def bind_address() -> str:
    address: str = setting_value("powershell.bind_address")
    return address


# The ttyd the install script builds from the pinned release and its patches.
def ttyd_path() -> str:
    build: str = setting_value("powershell.ttyd_build")
    return os.path.join(_CHECKOUT_PATH, build, "ttyd")


# ttyd's options as the start script gives them, but its port and its page.
def ttyd_options() -> tuple[str, ...]:
    return (
        "--interface",
        bind_address(),
        "--writable",
        "--check-origin",
        "--terminal-type",
        setting_value("powershell.terminal_type"),
        "--url-arg",
    )


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


# The bytes the probes' `pattern` makes: each index modulo the period.
def pattern_bytes(size: int) -> bytes:
    period = bytes(range(_PATTERN_PERIOD))
    return (period * (size // _PATTERN_PERIOD + 1))[:size]


# A pattern of a string's text in which each `_ANY` matches any text.
def pattern_make(text: str) -> re.Pattern[str]:
    escaped = re.escape(text).replace(re.escape(_ANY), "(.*)")
    return re.compile(escaped, re.DOTALL)


# The file of a database under the root.
def database_path(root: str, db: str) -> str:
    return os.path.join(root, db + _DB_EXTENSION)


# A file's whole lines, untranslated, or nothing while it does not exist yet.
def file_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    return lines_after(path, 0)


# Copies each console message of the page to stderr.
def console_copy(text: str) -> None:
    sys.stderr.write(f"console: {text}\n")


# A port on the local host held bound for the run and never listening.
def port_closed(stack: contextlib.ExitStack) -> int:
    sock = stack.enter_context(socket.socket())
    sock.bind((bind_address(), 0))
    return cast(int, sock.getsockname()[1])


# The run's stub server, started the first time a rung needs it.
def stub_ready(context: RunContext) -> StubServer:
    if not context.stubs:
        context.stubs.append(
            context.stack.enter_context(StubServer(context.log))
        )
    return context.stubs[0]


# Blocks the stub's failure signal for a cleanup, so a failure lands after it.
@contextlib.contextmanager
def failure_held() -> Generator[None]:
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


# Returns the parent's pid, the second field after the name in brackets.
def process_parent(pid: int) -> int:
    with open(f"/proc/{pid}/stat", "rb") as file:
        stat = file.read()
    return int(stat[stat.rindex(b")") + 2 :].split()[1])


# Fails unless the pid is ttyd's child running its command.
def program_check(ttyd: TtydServer, pid: int) -> None:
    with open(f"/proc/{pid}/cmdline", "rb") as file:
        cmdline = file.read().split(b"\0")[:-1]
    due = [word.encode() for word in ttyd.command]
    if cmdline != due:
        raise CheckFailed(f"the server's pid {pid} runs {cmdline}, not {due}")
    parent = process_parent(pid)
    if parent != ttyd.process.pid:
        raise CheckFailed(
            f"the server's pid {pid} is the child of {parent}, not of ttyd's"
            f" {ttyd.process.pid}"
        )


# Polls a reading of the server until it gives a value other than None.
def server_wait[T](
    session: PageSession, what: str, read: Callable[[], T | None]
) -> T:
    while True:
        found = read()
        if found is not None:
            return found
        session.ttyd.log_poll()
        poll: float = gold_value("poll_seconds")
        time.sleep(min(poll, session.log.timer.seconds_left(what)))


# Makes a root as the start script does, debug, level, scripted and run pinned.
def root_make(
    work: str, name: str, overrides: dict[str, Any]
) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    import harness

    root = os.path.join(work, name)
    python_path = os.path.join(root, "python")
    os.makedirs(python_path)
    for module in setting_value("powershell.runtime_modules"):
        file_name = module + ".py"
        shutil.copyfile(
            os.path.join(_PYTHON_PATH, file_name),
            os.path.join(python_path, file_name),
        )
    shutil.copytree(_SEED_PATH, os.path.join(python_path, "seed"))
    strings_path = os.path.join(root, "i18n")
    os.makedirs(strings_path)
    shutil.copyfile(_STRINGS_PATH, os.path.join(strings_path, "en-US.json"))
    values = harness.settings_copy()
    values["debug"] = gold_value("root_debug")
    values["verbose_level"] = gold_value("root_level")
    scripted = gold_value("root_scripted")
    values["provider"] = {**values["provider"], "scripted": scripted}
    values.update(overrides)
    text = json.dumps(values, ensure_ascii=False, indent=2) + "\n"
    with open(
        os.path.join(root, "settings.json"), "w", encoding="utf-8"
    ) as file:
        file.write(text)
    gold = harness.gold_copy()
    gold["typescript"]["run"] = _RUN_UNIT
    text = json.dumps(gold, ensure_ascii=False, indent=2) + "\n"
    with open(
        os.path.join(root, _TEST_SETTINGS_NAME), "w", encoding="utf-8"
    ) as file:
        file.write(text)
    index = os.path.join(root, os.path.basename(_PAGE_PATH))
    shutil.copyfile(_PAGE_PATH, index)
    return root, index, values, gold


# Copies a main loop file into the root's directory of main loop files.
def loop_place(root: str, source: str, name: str) -> None:
    directory = os.path.join(root, _MAIN_LOOP_DIRECTORY)
    os.makedirs(directory)
    shutil.copyfile(source, os.path.join(directory, name))


# Puts the main loop file whose `loop_prepare` never returns.
def stall_place(root: str, values: dict[str, Any]) -> None:
    loop_place(root, _STALL_LOOP_PATH, _STALL_LOOP_NAME)


# Puts the main loop file that serves `echo`.
def echo_place(root: str, values: dict[str, Any]) -> None:
    loop_place(root, _ECHO_LOOP_PATH, _ECHO_LOOP_NAME)


# Prepares nothing beyond what the start script makes.
def nothing_place(root: str, values: dict[str, Any]) -> None:
    pass


# The value the server holds under an external ref, or None while it has none.
def value_read(session: PageSession, ref: str) -> bytes | None:
    _, db, key = ref.split("/", 2)
    path = database_path(session.root, db)
    if not os.path.exists(path):
        return None
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT sha256, data FROM _kv WHERE key = ?", (key,)
        ).fetchone()
    finally:
        with failure_held():
            connection.close()
    if row is None:
        return None
    sha256, data = cast(tuple[bytes, bytes | None], row)
    if data is None:
        # A NULL `data` is a value the cache holds, its file named by its hash.
        cached = os.path.join(session.root, "cache", sha256.hex())
        with open(cached, "rb") as file:
            return file.read()
    return data


# The lines the server keeps of a thread, in the order it kept them.
def verbose_read(session: PageSession, thread: str) -> list[VerboseRow]:
    path = os.path.join(session.root, _VERBOSE_FILE)
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT seq, at, text FROM line WHERE thread = ? ORDER BY seq",
            (thread,),
        ).fetchall()
    finally:
        with failure_held():
            connection.close()
    return [VerboseRow(int(a), int(b), str(c)) for a, b, c in rows]


# The TAP documents of the file's whole lines, each from its version line.
def tap_documents(path: str, text: str) -> list[str]:
    documents: list[list[str]] = []
    whole = text[: text.rfind("\n") + 1]
    for line in whole.split("\n")[:-1]:
        if line == _TAP_VERSION:
            documents.append([])
        elif not documents:
            raise CheckFailed(f"{path} starts with {line!r}, not a version")
        documents[-1].append(line + "\n")
    return ["".join(lines) for lines in documents]


# The first failing point and its diagnostics, else the first bail or unknown.
def tap_failure(document: str) -> list[str]:
    import tap_consumer

    shown: list[str] = []
    lines = document.removesuffix("\n").split("\n")
    kinds = tap_consumer.Parser().parse_text(document)
    for text, kind in zip(lines, kinds, strict=True):
        match kind:
            case tap_consumer.Diagnostic() if shown:
                shown.append(text)
            case _ if shown:
                break
            case tap_consumer.Result() if not kind.ok and not kind.todo:
                shown.append(text)
            case tap_consumer.Bail() | tap_consumer.Unknown():
                return [text]
            case _:
                pass
    return shown


# Fails at the first fault: not two documents, then a document's first fault.
def tap_check(path: str, documents: list[str]) -> str:
    import tap_consumer

    if len(documents) != _TAP_DOCUMENTS:
        raise CheckFailed(
            f"{path} holds {len(documents)} TAP documents where"
            f" {_TAP_DOCUMENTS} were due"
        )
    shown: list[str] = []
    for number, document in enumerate(documents, 1):
        stats = tap_consumer.document_stats(document)
        if stats.failed or not stats.well_formed:
            first = "\n".join(tap_failure(document))
            raise CheckFailed(
                f"document {number} of {path} fails, well formed"
                f" {stats.well_formed}, at its first failing point, bail out"
                f" or unknown line:\n{first}"
            )
        shown.append(
            f"document {number}: plan {stats.plan}, {stats.passed} passed,"
            f" {stats.skipped} skipped, well formed"
        )
    return "; ".join(shown)


# The names of the modules whose blocks a TAP document's stream reports.
def tap_modules(document: str) -> list[str]:
    import tap_consumer

    return [
        kind.description
        for kind in tap_consumer.Parser().parse_text(document)
        if isinstance(kind, tap_consumer.Result) and kind.depth == 0
    ]


# Polls the TAP file from `begin` until both streams' documents have ended.
def streams_wait(session: PageSession, begin: int) -> list[str]:
    import tap_consumer

    path = os.path.join(session.root, _TAP_FILE)
    what = f"both TAP documents of {path} past byte {begin}"
    while True:
        text = lines_after(path, begin) if os.path.exists(path) else ""
        documents = tap_documents(path, text)
        if len(documents) > _TAP_DOCUMENTS:
            raise CheckFailed(
                f"{path} holds {len(documents)} TAP documents past byte"
                f" {begin}, where {_TAP_DOCUMENTS} were due"
            )
        if (
            len(documents) == _TAP_DOCUMENTS
            and tap_consumer.document_stats(documents[-1]).well_formed
        ):
            return documents
        session.ttyd.log_poll()
        poll: float = gold_value("poll_seconds")
        time.sleep(min(poll, session.log.timer.seconds_left(what)))


# The size of the TAP file in bytes, 0 while it does not exist yet.
def tap_size(session: PageSession) -> int:
    path = os.path.join(session.root, _TAP_FILE)
    return os.path.getsize(path) if os.path.exists(path) else 0


# Loads the page anew, both streams ended, so its stop function is up.
def fault_page(session: PageSession) -> int:
    session.page_leave()
    begin = tap_size(session)
    session.page_open()
    streams_wait(session, begin)
    return begin


# The last line of the TAP file from `begin` when it bails out, else None.
def bail_read(path: str, begin: int) -> str | None:
    lines = lines_after(path, begin).splitlines()
    if lines and lines[-1].startswith(_BAIL_PREFIX):
        return lines[-1].removeprefix(_BAIL_PREFIX)
    return None


# The server took the browser's failure: logged, the TAP file bailed, exit 1.
def bail_check(session: PageSession, begin: int, text: str) -> str:
    path = os.path.join(session.root, _TAP_FILE)
    message = server_wait(
        session,
        f"the bail out line of {path} past byte {begin}",
        lambda: bail_read(path, begin),
    )
    if text not in message:
        raise CheckFailed(
            f"{path} ends with the bail out {message!r}, where {text!r} was"
            " due in it"
        )
    logged = text_fill("engine_tap_browser_failed", {0: message})
    server_wait(
        session,
        f"the server's log line {logged!r}",
        lambda: next(
            (
                row
                for row in verbose_read(session, _SERVER_THREAD)
                if row.text == logged
            ),
            None,
        ),
    )
    _, ended = session.ttyd.line_wait(
        _ENDED_PATTERN, "the server's end", session.mark
    )
    if ended.group(1, 2) != (_EXITED_WORDS, "1"):
        raise CheckFailed(f"{session.ttyd.version} logged: {ended.string}")
    return message


# Runs the suites on the page, keeping document 1 when document 2 starts.
def rung_suites(session: PageSession, seen: list[str]) -> str:
    import tap_consumer

    path = os.path.join(session.root, _TAP_FILE)
    session.page_open()
    session.probe_call("long_start")
    documents: list[str] = []
    while not session.log.timer.timer_expired():
        session.ttyd.log_poll()
        documents = tap_documents(path, file_text(path))
        if len(documents) > 1 and not seen:
            seen.append(documents[0])
        if len(documents) > _TAP_DOCUMENTS:
            break
        if (
            len(documents) == _TAP_DOCUMENTS
            and tap_consumer.document_stats(documents[-1]).well_formed
        ):
            break
        time.sleep(gold_value("poll_seconds"))
    shown = tap_check(path, documents)
    png = session.shot_save("stage0_typescript_suites")
    return (
        f"{path} holds the AI worker's TAP document, then the UI thread's,"
        f" both well formed with no failing point: {shown}; PNG {png}"
    )


# The worker's modules, then the UI's, in order, the first document whole.
def rung_suites_order(session: PageSession, seen: list[str]) -> str:
    import tap_consumer

    path = os.path.join(session.root, _TAP_FILE)
    documents = tap_documents(path, file_text(path))
    first = seen[0]
    stats = tap_consumer.document_stats(first)
    worker_names = tap_modules(documents[0])
    page_names = tap_modules(documents[1])
    if (
        not stats.well_formed
        or first != documents[0]
        or worker_names != list(_AI_MODULES)
        or page_names != list(_UI_MODULES)
    ):
        raise CheckFailed(
            f"when {path} first held a second {_TAP_VERSION!r} line, its first"
            f" document was {first!r}, well formed {stats.well_formed}; the"
            f" documents now report the modules {worker_names} and"
            f" {page_names}, where {list(_AI_MODULES)} and"
            f" {list(_UI_MODULES)} were due"
        )
    return (
        f"the first time {path} held a second {_TAP_VERSION!r} line, the"
        " document before it was already whole and well formed, plan"
        f" {stats.plan}: the AI worker's, its {len(_AI_MODULES)} modules in"
        " the plan's order, ahead of the UI thread's, its"
        f" {len(_UI_MODULES)} modules in order"
    )


# An error thrown after load replaces the page and reaches the server.
def rung_thrown(session: PageSession) -> str:
    begin = fault_page(session)
    session.probe_call("throw_later", _THROWN_MESSAGE)
    text = session.fault_wait("the fault screen of the thrown error")
    if _THROWN_MESSAGE not in text:
        raise CheckFailed(f"the fault screen shows {text!r}")
    if session.probe_call("tap_kept") is not False:
        raise CheckFailed(
            "the page's #tap_output is still there, where the fault screen of"
            " a fault after load replaces the document"
        )
    message = bail_check(session, begin, _THROWN_MESSAGE)
    if message != _THROWN_MESSAGE:
        raise CheckFailed(
            f"the server bailed out with {message!r}, not {_THROWN_MESSAGE!r}"
        )
    png = session.shot_save("stage0_thrown_error")
    return (
        f"an error thrown after both streams ended showed {_THROWN_MESSAGE!r}"
        " with its stack in the pre that replaced the document; the stop"
        " function sent it through the worker to the server, which logged it,"
        f" ended the TAP file with the bail out {message!r} and exited with"
        f" code 1; PNG {png}"
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


# The fault screen's Reload loads the page again and both streams end.
def rung_reload(session: PageSession) -> str:
    button = json_object(
        session.probe_wait("the Reload button", "reload_button")
    )
    if button["onclick"] != _RELOAD_CALL or not button["view"]["center_hit"]:
        raise CheckFailed(f"the Reload button is {button}")
    begin = tap_size(session)
    session.reload_click(json_object(button["view"]))
    streams_wait(session, begin)
    session.fault_none("the reloaded page")
    return (
        f"clicking Reload, whose onclick is {_RELOAD_CALL!r}, loaded the page"
        " again and both TAP streams ended with no fault"
    )


# A rejected promise nothing handles reaches the fault screen and the server.
def rung_rejection(session: PageSession) -> str:
    begin = fault_page(session)
    session.probe_call("reject_later", _REJECTED_MESSAGE)
    text = session.fault_wait("the fault screen of the rejection")
    if not text.startswith(_REJECTED_MESSAGE):
        raise CheckFailed(f"the fault screen shows {text!r}")
    message = bail_check(session, begin, _REJECTED_MESSAGE)
    return (
        f"an unhandled rejection showed {_REJECTED_MESSAGE!r} on the fault"
        f" screen, and the server bailed out with {message!r} and exited with"
        " code 1"
    )


# A resource that fails to load reaches the capture handler and the server.
def rung_resource(
    session: PageSession,
    tag: str,
    attributes: dict[str, str],
    due: str,
) -> str:
    begin = fault_page(session)
    session.probe_call("resource_add", tag, attributes)
    text = session.fault_wait(f"the fault screen of the {tag}")
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    message = bail_check(session, begin, due)
    return (
        f"a {tag} with {json.dumps(attributes)} that failed to load showed"
        f" {due!r} on the fault screen, and the server bailed out with"
        f" {message!r} and exited with code 1"
    )


# An SVG image whose only address is `xlink:href` faults naming no address.
def rung_svg(session: PageSession, href: str) -> str:
    due = _ADDRESS_MISSING + "image"
    begin = fault_page(session)
    session.probe_call("svg_add", href)
    text = session.fault_wait("the fault screen of the SVG image")
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    message = bail_check(session, begin, due)
    return (
        f"an SVG image whose only address, xlink:href, is {href!r} failed to"
        f" load, showed {due!r} on the fault screen, and the server bailed"
        f" out with {message!r} and exited with code 1"
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
    session.page_leave()
    prefix = f"throw new Error({json.dumps(_LOAD_MESSAGE)});\n"
    identifier = session.preload_add(blob_patch(prefix, ""))
    session.page_open()
    text = session.fault_wait("the fault of the worker's load")
    session.preload_remove(identifier)
    session.programs_wait(0, "the end of the worker's programs")
    unknown: dict[int, object] = {0: _ANY, 1: _ANY, 2: _ANY}
    where = pattern_make(text_fill("page_worker_where", unknown))
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
    source = _WORKER_THROW.replace("XSJS_MESSAGE", json.dumps(_APPEND_MESSAGE))
    identifier = session.preload_add(source)
    session.page_open()
    text = session.fault_wait("the fault of the start script")
    session.preload_remove(identifier)
    if _APPEND_MESSAGE not in text:
        raise CheckFailed(f"the fault screen shows {text!r}")
    if session.probe_call("tap_kept") is not True:
        raise CheckFailed(
            "the fault while the parser ran replaced the document, where"
            " document.write appends while a script of the parser runs"
        )
    png = session.shot_save("stage0_fault_appended")
    return (
        f"the worker constructor threw {_APPEND_MESSAGE!r} inside the start"
        " script while the parser ran it: the fault's pre was appended and"
        " the page's #tap_output stayed, where a fault after load replaces"
        f" the document; PNG {png}"
    )


# The preload that adds the prefix and suffix to every script `Blob`.
def blob_patch(prefix: str, suffix: str) -> str:
    return _BLOB_PATCH.replace("XSJS_PREFIX", json.dumps(prefix)).replace(
        "XSJS_SUFFIX", json.dumps(suffix)
    )


# The pid of the server ttyd started since the page opened, from its log.
def server_pid(session: PageSession) -> int:
    _, found = session.ttyd.line_wait(
        _STARTED_PATTERN, "the server's start", session.mark
    )
    return int(found.group(1))


# The wire port's first line: `tap.start` with the root's two settings files.
def rung_first_line(session: PageSession) -> str:
    session.page_open()
    session.probe_call("wire_open", "first", session.url)
    first = json_object(
        session.probe_wait("the first line", "wire_first", "first")
    )
    header: dict[str, Any] = gold_value("lines.first")["0"]
    payload = json_object(first["payload"])
    if (
        first["header"] != header
        or sorted(payload) != ["settings", "test_settings"]
        or payload["settings"] != session.values
        or payload["test_settings"] != session.gold
        or first["blobs"] != []
    ):
        raise CheckFailed(
            f"the first line is {json.dumps(first)}, where the header"
            f" {json.dumps(header)}, the root's settings and test settings"
            " and no blob were due"
        )
    pid = server_pid(session)
    program_check(session.ttyd, pid)
    return (
        f"a WirePort on the page's main thread got {header['type']} with id"
        f" {header['id']} in full names from pid {pid}, ttyd's child, carrying"
        " the root's settings.json and test_settings.json and no blob, and"
        " answered it"
    )


# The page's wire port refuses to post a blob one byte over `blob_max`.
def rung_over(session: PageSession) -> str:
    blob_max: int = session.values["blob_max"]
    size = blob_max + 1
    message = session.probe_call("put_refused", "first", _ROUND_REF, size)
    due = text_fill("wire_blobs_over", {1: size, 2: blob_max})
    if message != due:
        raise CheckFailed(f"line_post threw {message!r}, not {due!r}")
    return (
        f"line_post of a kv.put push of one blob of {size} bytes, blob_max"
        f" plus one, threw {due!r} before anything was sent"
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
    session.probe_call("wire_open", "second", session.url)
    session.probe_wait("the first line", "wire_first", "second")
    options = {"id": _UNKNOWN_ID}
    session.probe_call("wire_send", "second", _UNKNOWN_TYPE, options, {})
    closes = session.probe_wait("the close", "wire_closes", "second")
    lines = json_list(session.probe_call("wire_lines", "second", 1))
    error = json_object(lines[0])
    message = text_fill("dispatch_handler_unknown", {})
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


# A server that ends with no `error` line is a fault naming the close code.
def rung_silent(session: PageSession) -> str:
    session.page_leave()
    session.page_open()
    session.probe_call("wire_open", "fourth", session.url)
    session.probe_wait("the first line", "wire_first", "fourth")
    pid = server_pid(session)
    os.kill(pid, signal.SIGKILL)
    text = session.fault_wait("the fault of the silent close")
    due = text_fill("wire_close_silent", {})
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
    payload: dict[str, Any] = {"method": "GET", "url": url, "headers": {}}
    session.probe_call("request_send", name, _HTTP_TYPE, line_id, payload, [])


# The POST carries its exact body and headers and gets its JSON back.
def rung_post(session: PageSession, stub: StubServer) -> str:
    session.probe_call("http_port", "post", gold_value("http_seconds"))
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
    if (
        asked_at > posted_at
        or method != "POST"
        or not set(_POST_HEADERS) <= headers
    ):
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
    session.probe_call("http_port", "plain", gold_value("http_seconds"))
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
    session.probe_call("http_port", "status", gold_value("http_seconds"))
    for line_id, status in enumerate(_STATUSES, 1):
        url = stub.url_make(f"{_STATUS_PREFIX}{status}")
        get_send(session, "status", line_id, url)
    lines = port_lines(session, "status", len(_STATUSES))
    by_id = {line["header"]["r"]: line for line in lines}
    for line_id, status in enumerate(_STATUSES, 1):
        url = stub.url_make(f"{_STATUS_PREFIX}{status}")
        due = text_fill(f"http_status_failed_{status}", {0: url})
        line = by_id[line_id]
        if line["header"]["t"] != "error" or line["payload"]["message"] != due:
            raise CheckFailed(f"status {status} gave {line}, not {due!r}")
    return f"the statuses {_STATUSES} each gave an error line naming the body"


# A closed port is an `error` line of the failed fetch.
def rung_refused(session: PageSession, closed_port: int) -> str:
    session.probe_call("http_port", "closed", gold_value("http_seconds"))
    url = f"http://{bind_address()}:{closed_port}/"
    get_send(session, "closed", 1, url)
    line = port_lines(session, "closed", 1)[0]
    pattern = pattern_make(text_fill("http_fetch_failed", {0: url, 1: _ANY}))
    message = cast(str, line["payload"].get("message", ""))
    if line["header"] != {"t": "error", "r": 1} or not pattern.fullmatch(
        message
    ):
        raise CheckFailed(f"the closed port gave {line}")
    return f"a GET of the closed port {closed_port} gave {message!r}"


# A server that never answers is a timeout `error` line.
def rung_never(session: PageSession, stub: StubServer) -> str:
    session.probe_call("http_port", "silent", gold_value("http_seconds"))
    url = stub.url_make(_SILENT_PATH)
    get_send(session, "silent", 1, url)
    line = port_lines(session, "silent", 1)[0]
    due = text_fill("http_timeout_expired", {0: url})
    if (
        line["header"] != {"t": "error", "r": 1}
        or line["payload"]["message"] != due
    ):
        raise CheckFailed(f"the silent server gave {line}, not {due!r}")
    return f"a server that never answered gave {due!r}"


# A body that stalls after its head is a timeout `error` line.
def rung_stall(session: PageSession, stub: StubServer) -> str:
    session.probe_call("http_port", "stall", gold_value("http_seconds"))
    url = stub.url_make(_STALL_PATH)
    get_send(session, "stall", 1, url)
    line = port_lines(session, "stall", 1)[0]
    due = text_fill("http_timeout_expired", {0: url})
    if (
        line["header"] != {"t": "error", "r": 1}
        or line["payload"]["message"] != due
    ):
        raise CheckFailed(f"the stalled body gave {line}, not {due!r}")
    return (
        f"a body stalled after {len(_PLAIN_TEXT)} of {_STALL_LENGTH} bytes"
        f" gave {due!r}"
    )


# After a timeout the port gives no second line, though the answer comes late.
def rung_single(session: PageSession, stub: StubServer) -> str:
    session.probe_call("http_port", "late", gold_value("http_seconds"))
    url = stub.url_make(_LATE_PATH)
    get_send(session, "late", 1, url)
    line = port_lines(session, "late", 1)[0]
    due = text_fill("http_timeout_expired", {0: url})
    if (
        line["header"] != {"t": "error", "r": 1}
        or line["payload"]["message"] != due
    ):
        raise CheckFailed(f"the late server gave {line}, not {due!r}")
    stub.late_release()
    outcome = server_wait(
        session, "the stub's late answer", lambda: stub.late_outcome or None
    )
    get_send(session, "late", 2, stub.url_make(_TEXT_PATH))
    port_lines(session, "late", 2)
    quiet: float = gold_value("quiet_seconds")
    time.sleep(quiet)
    lines = json_list(session.probe_call("lines_when", "late", 0))
    ids = [json_object(line)["header"]["r"] for line in lines]
    if ids != [1, 2]:
        raise CheckFailed(f"the port late gave lines for {ids}")
    return (
        f"a GET of {url} timed out with {due!r}; the stub then answered it"
        f" late, its write {outcome}; a later request's reply came, and"
        f" {quiet:g} s on the port held exactly the lines of r 1 and 2"
    )


# Replies arriving in reverse order each answer their own request.
def rung_order(session: PageSession, stub: StubServer) -> str:
    count: int = gold_value("order_count")
    session.probe_call("http_port", "order", gold_value("order_seconds"))
    paths = [f"{_ORDER_PREFIX}{number}" for number in range(count)]
    for number, path in enumerate(paths):
        get_send(session, "order", number + 1, stub.url_make(path))
    server_wait(
        session,
        f"the stub to take the {count} order requests",
        lambda: (
            True
            if all(stub.requests_of("GET", path) for path in paths)
            else None
        ),
    )
    for number in reversed(range(count)):
        stub.order_release(number)
        port_lines(session, "order", count - number)
    lines = port_lines(session, "order", count)
    came = [
        (line["header"]["r"], line["payload"]["json"]["n"]) for line in lines
    ]
    due = [(number + 1, number) for number in reversed(range(count))]
    answered = stub.answers_list(_ORDER_PREFIX)
    sent = [f"{_ORDER_PREFIX}{number}" for number in reversed(range(count))]
    if came != due or answered != sent:
        raise CheckFailed(f"the replies came as {came}, answered {answered}")
    return (
        f"{count} requests answered last first came back in that order, each"
        " reply's r its request's i"
    )


# A GET with a body is refused by the browser, an `error` line.
def rung_body(session: PageSession, stub: StubServer) -> str:
    session.probe_call("http_port", "body", gold_value("http_seconds"))
    url = stub.url_make(_TEXT_PATH)
    payload: dict[str, Any] = {
        "method": "GET",
        "url": url,
        "headers": {},
        "body": _GET_BODY,
    }
    session.probe_call("request_send", "body", _HTTP_TYPE, 1, payload, [])
    line = port_lines(session, "body", 1)[0]
    pattern = pattern_make(text_fill("http_fetch_failed", {0: url, 1: _ANY}))
    message = cast(str, line["payload"].get("message", ""))
    if line["header"] != {"t": "error", "r": 1} or not pattern.fullmatch(
        message
    ):
        raise CheckFailed(f"the GET with a body gave {line}")
    return f"a GET with a body gave {message!r}"


# The HTTP port works inside a worker made from the bundle.
def rung_worker(session: PageSession, stub: StubServer) -> str:
    url = stub.url_make(_JSON_PATH)
    session.probe_call("worker_http", url, gold_value("http_seconds"))
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
        gold_value("http_seconds"),
    )
    text = session.fault_wait("the fault of the throwing receiver")
    if _RECEIVER_MESSAGE not in text:
        raise CheckFailed(f"the fault screen shows {text!r}")
    return (
        f"a receiver that threw {_RECEIVER_MESSAGE!r} reached the fault screen"
    )


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
    replies = json_list(
        session.probe_wait("the worker's reply", "thread_when")
    )
    due: list[dict[str, Any]] = [
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
    seconds = gold_value("http_seconds")
    session.probe_call(
        "pair_run", "rung_pair.begin", "rung_pair.done", urls, seconds
    )
    replies = json_list(session.probe_wait("the wake of two", "pair_when"))
    came = [
        (
            json_object(reply)["header"]["r"],
            json_object(reply)["payload"]["json"],
        )
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
    return (
        f"a handler that threw {_HANDLER_MESSAGE!r} reached the fault screen"
    )


# Polls the record of the probe's console port until `test` holds.
def console_wait(
    session: PageSession, what: str, test: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    while True:
        record = json_object(session.probe_call("console_state"))
        if test(record):
            return record
        poll: float = gold_value("poll_seconds")
        time.sleep(min(poll, session.log.timer.seconds_left(what)))


# The text of tty 0's output in the probe's console record from a line on.
def output_text(record: dict[str, Any], begun: int) -> str:
    return "".join(
        cast(str, line["text"])
        for line in record["lines"][begun:]
        if line["kinds"] == [_OUTPUT_KIND]
    )


# Takes the reply to the probe's `console.open`, sends ttyd's first message.
def console_first(
    session: PageSession, request_id: int, begun: int, full: bool
) -> None:
    name = "console_open_reply_full" if full else "console_open_reply"
    header: dict[str, Any] = gold_value(f"lines.{name}")["0"]
    reply_key = "reply" if full else "r"
    due = {**header, reply_key: request_id}
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
        "columns": gold_value("probe_columns"),
        "rows": gold_value("probe_rows"),
    }
    session.probe_call("console_send", json_text(first))


# Opens tty 0 on the probe's port, sends the token, waits for the prompt.
def console_start(session: PageSession, request_id: int, full: bool) -> None:
    begun = len(json_object(session.probe_call("console_state"))["lines"])
    session.probe_call("console_ask", request_id)
    console_first(session, request_id, begun, full)
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
    # With the worker stubbed the page's settings never come: full names.
    full = True
    session.probe_call("console_port", session.url)
    console_start(session, 1, full)
    mark = len(session.ttyd.lines)
    session.probe_call("console_shut")
    shut = console_closed(session, 1)
    _, killed = session.ttyd.line_wait(
        _ENDED_PATTERN, "the first console's end", mark
    )
    console_start(session, 2, full)
    mark = len(session.ttyd.lines)
    session.probe_call("console_send", _INPUT_KIND + _EXIT_COMMAND + "\r")
    exited = console_closed(session, 2)
    _, ended = session.ttyd.line_wait(
        _ENDED_PATTERN, "the second console's end", mark
    )
    if ended.group(1, 2) != (_EXITED_WORDS, "0"):
        raise CheckFailed(f"{session.ttyd.version} logged: {ended.string}")
    console_start(session, 3, full)
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


# The wire port's wait for a token from a stopped ttyd runs out.
def rung_token(session: PageSession) -> str:
    ttyd = session.ttyd
    session.page_leave()
    session.page_open()
    ttyd.signal_send(signal.SIGSTOP)
    try:
        session.probe_call("wire_open", "held", session.url)
        text = session.fault_wait("the fault of the wait for the token")
    finally:
        with failure_held():
            ttyd.signal_send(signal.SIGCONT)
    url = session.url + _TOKEN_PATH
    due = text_fill("wire_wait_expired_token", {0: url})
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    return (
        f"a WirePort aimed at ttyd, stopped with SIGSTOP so that GET {url}"
        f" was never answered, faulted with {due!r}"
    )


# The wire port's wait for a socket that never opens runs out.
def rung_opening(session: PageSession, stub: StubServer) -> str:
    session.page_leave()
    session.page_open()
    session.probe_call("wire_open", "opening", stub.url_make(_OPENING_BASE))
    text = session.fault_wait("the fault of the wait for the open")
    url = stub.socket_make(_OPENING_BASE + _SOCKET_PATH)
    due = text_fill("wire_wait_expired_open", {0: url})
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
    session.page_leave()
    session.page_open()
    base = stub.url_make(_CLOSING_BASE)
    session.probe_call("console_port", base)
    session.probe_call("console_ask", 1)
    text = session.fault_wait("the fault of the socket closed unopened")
    url = stub.socket_make(_CLOSING_BASE + _CONSOLE_PATH)
    due = text_fill("wire_open_closed", {0: url})
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
    seconds = gold_value("media_seconds")
    session.probe_call("media_port", "store", budget, seconds)
    session.probe_call(
        "request_send", "store", "media.store", 1, {"k": key}, [list(png)]
    )
    reply = port_lines(session, "store", 1)[0]
    due: dict[str, Any] = {
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
def rung_fetch(
    session: PageSession, stub: StubServer, png: bytes, budget: int
) -> str:
    key = "/_files/rung/fetched.png"
    seconds = gold_value("media_seconds")
    session.probe_call("media_port", "fetch", budget, seconds)
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
    key = "/_files/rung/lost.png"
    url = f"http://{bind_address()}:{closed_port}/"
    seconds = gold_value("media_seconds")
    session.probe_call("media_port", "lost", budget, seconds)
    payload = {"url": url, "k": key}
    session.probe_call("request_send", "lost", "media.fetch", 1, payload, [])
    line = port_lines(session, "lost", 1)[0]
    due = text_fill("media_download_failed_lost", {0: url, 2: _ANY})
    pattern = pattern_make(due)
    message = cast(str, line["payload"].get("message", ""))
    if line["header"] != {"t": "error", "r": 1} or not pattern.fullmatch(
        message
    ):
        raise CheckFailed(f"the lost download gave {line}")
    return f"a download from a closed port gave {message!r}"


# A download answered 404 is an `error` line naming the status.
def rung_missing(session: PageSession, stub: StubServer, budget: int) -> str:
    key = "/_files/rung/missing.png"
    url = stub.url_make(f"{_STATUS_PREFIX}{_MISSING_STATUS}")
    seconds = gold_value("media_seconds")
    session.probe_call("media_port", "missing", budget, seconds)
    payload = {"url": url, "k": key}
    session.probe_call(
        "request_send", "missing", "media.fetch", 1, payload, []
    )
    line = port_lines(session, "missing", 1)[0]
    due = text_fill("media_download_failed_missing", {0: url})
    if (
        line["header"] != {"t": "error", "r": 1}
        or line["payload"]["message"] != due
    ):
        raise CheckFailed(f"the missing download gave {line}, not {due!r}")
    return f"a download answered {_MISSING_STATUS} gave {due!r}"


# A download that never comes is a timeout `error` line.
def rung_late(session: PageSession, stub: StubServer, budget: int) -> str:
    key = "/_files/rung/late.png"
    url = stub.url_make(_SILENT_PATH)
    seconds = gold_value("media_seconds")
    session.probe_call("media_port", "late", budget, seconds)
    payload = {"url": url, "k": key}
    session.probe_call("request_send", "late", "media.fetch", 1, payload, [])
    line = port_lines(session, "late", 1)[0]
    due = text_fill("media_download_expired", {0: url})
    if (
        line["header"] != {"t": "error", "r": 1}
        or line["payload"]["message"] != due
    ):
        raise CheckFailed(f"the late download gave {line}, not {due!r}")
    return f"a download that never came gave {due!r}"


# Bytes that are no image are an `error` line of the decode.
def rung_garbage(session: PageSession, budget: int) -> str:
    key = "/_files/rung/garbage.png"
    seconds = gold_value("media_seconds")
    session.probe_call("media_port", "garbage", budget, seconds)
    session.probe_call(
        "request_send",
        "garbage",
        "media.store",
        1,
        {"k": key},
        [list(_UNDECODABLE)],
    )
    line = port_lines(session, "garbage", 1)[0]
    pattern = pattern_make(text_fill("media_decode_failed", {1: _ANY}))
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
    seconds = gold_value("media_seconds")
    session.probe_call("media_port", "evict", budget, seconds)
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


# The live verbose ring of the UI holds its lines, each an at and a text.
def rung_ring(session: PageSession) -> str:
    ring = json_list(session.probe_call("history_get"))
    size: int = session.values["verbose_ring"]
    fields = {"at", "text"}
    other = [line for line in ring if set(json_object(line)) != fields]
    if not ring or len(ring) > size or other:
        raise CheckFailed(f"the UI's ring holds {len(ring)} lines: {ring}")
    return (
        f"the UI's verbose singleton holds {len(ring)} lines of at most"
        f" verbose_ring {size}, each with the fields at and text alone"
    )


# The queue installed the live verbose sink, so a second one is refused.
def rung_sink(session: PageSession) -> str:
    message = session.probe_call("sink_twice")
    due = text_fill("verbose_sink_twice", {})
    if message != due:
        raise CheckFailed(f"sink_set threw {message!r}, not {due!r}")
    return f"a second sink_set on the live verbose threw {due!r}"


# The bundle's strings table holds the overlay's text.
def rung_strings(session: PageSession) -> str:
    message = session.probe_call("ring_refused")
    due = text_fill("overlay_ring_invalid", {})
    if message != due:
        raise CheckFailed(f"the overlay threw {message!r}, not {due!r}")
    return f"an overlay of ring 0 threw {due!r}, the text of the server's file"


# The long tasks the UI thread ran since the observer started.
def rung_long(session: PageSession) -> str:
    import harness

    durations = [
        cast(float, value)
        for value in json_list(session.probe_call("long_list"))
    ]
    target = harness.gold_get("long_task_ms")
    longest = f"{max(durations):.1f} ms" if durations else "none"
    return (
        f"the long task observer saw {len(durations)} tasks of 50 ms or more"
        f" on the UI thread, the longest {longest}; long_task_ms"
        f" {target} is a soft target below the observer's 50 ms floor"
    )


# Outside debug mode the page gets its settings and runs nothing.
def rung_gating(session: PageSession) -> str:
    session.page_open()
    session.probe_wait("the page's settings", "settings_shown")
    quiet: float = gold_value("quiet_seconds")
    time.sleep(quiet)
    size = tap_size(session)
    started = session.ttyd.pids_found(_STARTED_PATTERN, 1, session.mark)
    if size != 0 or len(started) != 1:
        raise CheckFailed(
            f"with debug false the TAP file holds {size} bytes and ttyd"
            f" started {len(started)} programs since the page opened, where"
            " no TAP line and the server of tty 1 alone were due"
        )
    session.fault_none("the page with debug false")
    return (
        "with debug false the page's settings arrived and, after"
        f" {quiet:g} s, no TAP line had reached the server, the page"
        " showed no fault, and ttyd had started the server of tty 1 alone"
    )


# The console role is refused outside debug mode.
def rung_refused_role(session: PageSession) -> str:
    mark = len(session.ttyd.lines)
    session.probe_call("console_port", session.url)
    session.probe_call("console_ask", 1)
    # The page's settings, debug false, arrived before: short names.
    console_first(session, 1, 0, False)
    record = json_object(
        session.probe_wait("the console's close", "console_when")
    )
    _, found = session.ttyd.line_wait(
        _ENDED_PATTERN, "the console's end", mark
    )
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
        "with debug false a ConsolePort opened tty 0 with its token and sent"
        " ttyd's first message, which started the console role; it exited"
        f" with code 1 and no output, and the port saw the close {_CLOSE_LOST}"
    )


# A server that never writes the first line runs out the worker's wait.
def rung_stalled(session: PageSession) -> str:
    session.page_open()
    pid = server_pid(session)
    program_check(session.ttyd, pid)
    text = session.fault_wait("the fault of the wait for the first line")
    due = text_fill("wire_wait_expired_first", {})
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    ended = session.programs_wait(1, "the end of the stalled server")
    return (
        f"pid {pid}, ttyd's child running {_LOOP_OPTION} {_STALL_LOOP_NAME},"
        " never wrote the first line; the AI worker's wire port faulted with"
        f" {due!r}, posted to the page at once, and {ended} program ended"
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
    session.probe_wait("the first line", "wire_first", "credential")
    pid = server_pid(session)
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
        " token, which is the credential in base64, and ttyd took it: the"
        f" first line came from pid {pid}; without the header GET {url} gave"
        f" {_UNAUTHORIZED}"
    )


# A root the test put no provider script in holds the seed's script.
def rung_fresh_root(session: PageSession) -> str:
    held = value_read(session, _SCRIPT_REF)
    with open(_SEED_SCRIPT_PATH, "rb") as file:
        seed = file.read()
    if held != seed:
        raise CheckFailed(
            f"the server's {_SCRIPT_REF} holds {held!r}, not the bytes of"
            f" {_SEED_SCRIPT_PATH}, {seed!r}"
        )
    return (
        "a root made with provider.scripted true and no script of the test"
        f" was prepared by the server before tap.start: its {_SCRIPT_REF} is"
        f" byte equal to {_SEED_SCRIPT_PATH}"
    )


# An `error` line before the first line shows the server's message and stack.
def rung_error_first(session: PageSession) -> str:
    path = os.path.join(session.root, _LOCK_FILE)
    message = text_fill("bootstrap_lock_held", {0: path})
    session.page_open()
    text = session.fault_wait("the fault of the error before the first line")
    due = text_fill("wire_error_first", {0: path, 1: _ANY})
    pattern = pattern_make(due)
    found = pattern.search(text)
    if found is None or f"RuntimeError: {message}" not in found.group(1):
        raise CheckFailed(
            f"the fault screen shows {text!r}, where the server's {message!r}"
            " with its traceback was due"
        )
    _, ended = session.ttyd.line_wait(
        _ENDED_PATTERN, "the server's end", session.mark
    )
    if ended.group(1, 2) != (_EXITED_WORDS, "1"):
        raise CheckFailed(f"{session.ttyd.version} logged: {ended.string}")
    session.programs_wait(1, "the end of the server")
    return (
        f"with this process holding {path}, the server wrote its error line"
        " before the first line and ttyd logged its exit with code 1; the"
        f" page showed {message!r} with the server's traceback as the error"
        " before the first line"
    )


# The root whose engine lock this process holds, so its server fails at once.
def rungs_locked(session: PageSession) -> None:
    path = os.path.join(session.root, _LOCK_FILE)
    with open(path, "ab") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        session.log.rung_run(
            "stage 5: error before the first line",
            "normal-test",
            lambda: rung_error_first(session),
        )


# The echoes due back for that many echo lines of one pattern blob each.
def echoes_due(count: int) -> list[dict[str, Any]]:
    size: int = gold_value("echo_blob_bytes")
    digest = sha256_text(pattern_bytes(size))
    return [
        {
            "header": {"t": "echo", "r": number, "b": 1},
            "payload": {},
            "blobs": [{"size": size, "sha256": digest}],
        }
        for number in range(1, count + 1)
    ]


# Opens the page anew with a wire port named `drain` past its first line.
def drain_open(session: PageSession) -> None:
    session.page_leave()
    session.page_open()
    session.probe_call("wire_open", "drain", session.url)
    session.probe_wait("the first line", "wire_first", "drain")


# Echoes posted while ttyd is stopped wait on the port's poll, then all come.
def rung_drain_poll(session: PageSession) -> str:
    ttyd = session.ttyd
    size: int = gold_value("echo_blob_bytes")
    stall: float = gold_value("stall_seconds")
    count = gold_value("large_bytes") // size
    drain_open(session)
    ttyd.signal_send(signal.SIGSTOP)
    try:
        session.probe_call("echo_burst", "drain", count, size)
        time.sleep(stall)
        pending = json_object(session.probe_call("wire_pending", "drain"))
    finally:
        with failure_held():
            ttyd.signal_send(signal.SIGCONT)
    if pending["polling"] is not True:
        raise CheckFailed(
            f"with ttyd stopped for {stall:g} s the port's socket buffered"
            f" {pending['buffered']} bytes and no poll waited, so the stall"
            " never held a frame back"
        )
    lines = json_list(
        session.probe_wait("the echoes", "wire_lines", "drain", count)
    )
    if lines != echoes_due(count):
        raise CheckFailed(f"the echoes came back as {lines}")
    session.fault_none("the echoes after the stall")
    return (
        f"with ttyd stopped, {count} echo requests of one {size} byte blob"
        " each, posted at once, filled the socket, which buffered"
        f" {pending['buffered']} bytes after {stall:g} s with the port's poll"
        " waiting; continued, ttyd took the rest and every echo came back"
        " equal by sha256, with no fault"
    )


# A socket that takes no bytes for the drain wait faults the port.
def rung_drain_timer(session: PageSession) -> str:
    blob_max: int = session.values["blob_max"]
    ttyd = session.ttyd
    size: int = gold_value("echo_blob_bytes")
    count = blob_max // size
    drain_open(session)
    ttyd.signal_send(signal.SIGSTOP)
    try:
        session.probe_call("echo_burst", "drain", count, size)
        text = session.fault_wait("the fault of the wait for the drain")
    finally:
        with failure_held():
            ttyd.signal_send(signal.SIGCONT)
    url = f"ws://{bind_address()}:{ttyd.port}/{_SOCKET_PATH}"
    due = text_fill("wire_wait_expired_drain", {0: url})
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    return (
        f"with ttyd stopped, {count} echo requests of one {size} byte blob"
        f" each posted at once, their blobs within blob_max {blob_max}, filled"
        f" the socket, and the port faulted with {due!r}"
    )


# A synchronous GET on the UI thread is found in a trace, as its control.
def rung_blocking_control(session: PageSession) -> str:
    import devtools

    browser = session.browser
    browser.trace_start(devtools.blocking_categories())
    status = session.probe_call("sync_get")
    events = browser.trace_end()
    found = devtools.blocking_find(events)
    if status != _HTTP_OK or not found:
        raise CheckFailed(
            f"a synchronous GET of the page gave {status}, and the trace of"
            f" {len(events)} events holds {len(found)} synchronous loads on"
            " the UI thread, where one at least was due"
        )
    return (
        f"a synchronous XMLHttpRequest GET of the page gave {status}, and the"
        f" trace of {len(events)} events found {len(found)} synchronous loads"
        f" on the UI thread, the first {found[0]['name']}"
    )


# The page's bring up and suites make no synchronous load on the UI thread.
def rung_blocking_none(session: PageSession) -> str:
    import devtools

    session.page_leave()
    begin = tap_size(session)
    session.page_open()
    session.browser.trace_start(devtools.blocking_categories())
    streams_wait(session, begin)
    events = session.browser.trace_end()
    found = devtools.blocking_find(events)
    if found:
        shown = "; ".join(
            f"{event['name']} pid {event['pid']} tid {event['tid']} ts"
            f" {event['ts']}"
            for event in found
        )
        raise CheckFailed(
            f"the trace of {len(events)} events holds {len(found)} synchronous"
            f" loads on the UI thread: {shown}"
        )
    return (
        f"the trace of {len(events)} events, from a new load of the page to"
        " the end of both TAP streams, holds no synchronous load on the UI"
        " thread"
    )


# A put killed between its cache file and its row leaves the file to remove.
def rung_kill_between(session: PageSession) -> str:
    slots = gold_value("kill_slots")
    options = {
        "pool": _KILL_POOL,
        "directory": _KILL_DIRECTORY,
        "capacity": gold_value("kill_capacity"),
        "slot_directory": _KILL_SLOTS_DIRECTORY,
        "slots": slots,
        "root": _KILL_ROOT,
        "overflow": session.values["overflow_bytes"],
        "compact": session.values["turn_compact_turns"],
    }
    session.probe_call("kill_run", options)
    found = json_object(
        session.probe_wait("the check after the kill", "kill_when")
    )
    if "fault" in found or found.get("checked") != _KILL_DUE:
        raise CheckFailed(
            f"the kill of a put between its file and its row gave {found},"
            f" where checked {_KILL_DUE} was due"
        )
    return (
        "a worker of the test bundle opened the OPFS pool"
        f" {_KILL_POOL} and {slots} cache files, created a database and"
        " stopped its put of a value over overflow_bytes after the cache"
        " file and before the row; terminated there, a second worker opened"
        f" the same files and found {found['checked']}: no row, and"
        " kv_check removed the one file"
    )


# The whole lines of a file from a byte offset on, as text.
def lines_after(path: str, begin: int) -> str:
    with open(path, "rb") as file:
        file.seek(begin)
        data = file.read()
    return data[: data.rfind(b"\n") + 1].decode("utf-8")


# A worker paused in the UI's stream keeps every TAP line before the pause.
def rung_worker_hang(session: PageSession) -> str:
    import tap_consumer

    path = os.path.join(session.root, _TAP_FILE)
    begin = os.path.getsize(path)
    session.page_leave()
    session.page_open()
    seen = tap_documents(path, lines_after(path, begin))
    while len(seen) < _TAP_DOCUMENTS:
        what = "the first line of the UI thread's TAP document"
        poll: float = gold_value("poll_seconds")
        time.sleep(min(poll, session.log.timer.seconds_left(what)))
        session.ttyd.log_poll()
        seen = tap_documents(path, lines_after(path, begin))
    session.browser.worker_pause(_AI_THREAD)
    documents = tap_documents(path, lines_after(path, begin))
    session.page_leave()
    whole = tap_consumer.document_stats(documents[0])
    cut = tap_consumer.document_stats(documents[1])
    if (
        len(documents) != _TAP_DOCUMENTS
        or documents[0] != seen[0]
        or not whole.well_formed
        or cut.well_formed
    ):
        raise CheckFailed(
            f"with the worker {_AI_THREAD} paused, {path} holds"
            f" {len(documents)} documents past byte {begin}, the first well"
            f" formed {whole.well_formed} and the second {cut.well_formed},"
            " where the worker's whole document and the UI's cut one were"
            " due"
        )
    return (
        f"once {path} held the AI worker's TAP document and the first line"
        f" of the UI thread's past byte {begin}, the worker {_AI_THREAD} was"
        " paused in its debugger: the worker's document stayed whole and"
        f" well formed, plan {whole.plan}, and the UI's, whose lines pass"
        f" through the worker, stopped cut, its {cut.passed} points kept;"
        " the page was left"
    )


# The suites root: the TypeScript suites over TAP, then the page they leave.
def rungs_suites(session: PageSession) -> None:
    log = session.log
    seen: list[str] = []
    suites: float = gold_value("suites_seconds")
    log.rung_run(
        "stage 0: typescript suites",
        "smoke-test",
        lambda: rung_suites(session, seen),
        suites,
    )
    log.rung_run(
        "stage 0: typescript suites in order",
        "smoke-test",
        lambda: rung_suites_order(session, seen),
    )
    log.rung_run(
        "stage 8: fresh root", "smoke-test", lambda: rung_fresh_root(session)
    )
    log.rung_run(
        "stage 5: verbose ring", "normal-test", lambda: rung_ring(session)
    )
    log.rung_run(
        "stage 5: verbose sink", "normal-test", lambda: rung_sink(session)
    )
    log.rung_run(
        "stage 8: long tasks", "normal-test", lambda: rung_long(session)
    )
    log.rung_run(
        "stage 5: traced synchronous load found",
        "normal-test",
        lambda: rung_blocking_control(session),
    )
    log.rung_run(
        "stage 6: kill between file and row",
        "normal-test",
        lambda: rung_kill_between(session),
    )
    log.rung_run(
        "stage 5: no synchronous load on the UI thread",
        "normal-test",
        lambda: rung_blocking_none(session),
        suites,
    )
    log.rung_run(
        "stage 0: worker hang keeps the TAP lines before it",
        "normal-test",
        lambda: rung_worker_hang(session),
        suites,
    )


# The faults root of stage 0: every way a fault reaches the screen.
def rungs_faults(session: PageSession) -> None:
    log = session.log
    log.rung_run(
        "stage 0: thrown error", "normal-test", lambda: rung_thrown(session)
    )
    log.rung_run(
        "stage 0: first fault only", "normal-test", lambda: rung_first(session)
    )
    log.rung_run(
        "stage 0: reload", "normal-test", lambda: rung_reload(session)
    )
    log.rung_run(
        "stage 0: rejection", "normal-test", lambda: rung_rejection(session)
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
            "normal-test",
            lambda: rung_resource(session, tag, attributes, due),
        )
    log.rung_run(
        "stage 0: failing with neither address",
        "normal-test",
        lambda: rung_resource(
            session,
            "img",
            {"srcset": "/rung-missing-set.png"},
            _ADDRESS_MISSING + "img",
        ),
    )
    log.rung_run(
        "stage 0: failing object",
        "normal-test",
        lambda: rung_resource(
            session,
            "object",
            {"data": "/rung-missing.bin"},
            _ADDRESS_MISSING + "object",
        ),
    )
    log.rung_run(
        "stage 0: failing SVG image",
        "normal-test",
        lambda: rung_svg(session, "/rung-missing-svg.png"),
    )
    log.rung_run(
        "stage 0: worker fault posted",
        "normal-test",
        lambda: rung_posted(session),
    )
    log.rung_run(
        "stage 0: worker throws at load",
        "normal-test",
        lambda: rung_load(session),
    )
    log.rung_run(
        "stage 0: write versus append",
        "normal-test",
        lambda: rung_append(session),
    )


# The probe root of stages 5, 7 and 8: the ports on the page's main thread.
def rungs_probe(session: PageSession, context: RunContext) -> None:
    log = session.log
    stub = stub_ready(context)
    closed = context.closed_port
    identifier = session.preload_add(_WORKER_STUB)
    log.rung_run(
        "stage 5: wire first line",
        "normal-test",
        lambda: rung_first_line(session),
    )
    log.rung_run(
        "stage 5: blob_max plus one refused",
        "normal-test",
        lambda: rung_over(session),
        gold_value("window_seconds"),
    )
    log.rung_run(
        "stage 5: wire_close", "normal-test", lambda: rung_close(session)
    )
    log.rung_run(
        "stage 5: error line then close",
        "normal-test",
        lambda: rung_error(session),
    )
    log.rung_run(
        "stage 5: http post", "normal-test", lambda: rung_post(session, stub)
    )
    log.rung_run(
        "stage 5: http preflight", "normal-test", lambda: rung_preflight(stub)
    )
    log.rung_run(
        "stage 5: http text and json",
        "normal-test",
        lambda: rung_answers(session, stub),
    )
    log.rung_run(
        "stage 5: http statuses",
        "normal-test",
        lambda: rung_statuses(session, stub),
    )
    log.rung_run(
        "stage 5: http closed port",
        "normal-test",
        lambda: rung_refused(session, closed),
    )
    log.rung_run(
        "stage 5: http never answers",
        "normal-test",
        lambda: rung_never(session, stub),
    )
    log.rung_run(
        "stage 5: http stalled body",
        "normal-test",
        lambda: rung_stall(session, stub),
    )
    log.rung_run(
        "stage 5: http one line per request",
        "normal-test",
        lambda: rung_single(session, stub),
    )
    log.rung_run(
        "stage 5: http out of order",
        "normal-test",
        lambda: rung_order(session, stub),
    )
    log.rung_run(
        "stage 5: http get with a body",
        "normal-test",
        lambda: rung_body(session, stub),
    )
    log.rung_run(
        "stage 5: http port in a worker",
        "normal-test",
        lambda: rung_worker(session, stub),
    )
    log.rung_run(
        "stage 5: queue scheduling",
        "normal-test",
        lambda: rung_schedule(session),
    )
    log.rung_run(
        "stage 5: queue thread port",
        "normal-test",
        lambda: rung_thread(session),
    )
    log.rung_run(
        "stage 5: queue two replies",
        "normal-test",
        lambda: rung_pair(session, stub),
    )
    log.rung_run(
        "stage 5: overlay strings",
        "normal-test",
        lambda: rung_strings(session),
    )
    png = bytes(cast(list[int], session.probe_call("png_bytes")))
    stub.png = png
    budget: int = session.values["media_db_bytes"]
    log.rung_run(
        "stage 8: media png kept",
        "normal-test",
        lambda: rung_store(session, png, budget),
    )
    log.rung_run(
        "stage 8: media download as blob 1",
        "normal-test",
        lambda: rung_fetch(session, stub, png, budget),
    )
    log.rung_run(
        "stage 8: media network failure",
        "normal-test",
        lambda: rung_lost(session, closed, budget),
    )
    log.rung_run(
        "stage 8: media status",
        "normal-test",
        lambda: rung_missing(session, stub, budget),
    )
    log.rung_run(
        "stage 8: media timeout",
        "normal-test",
        lambda: rung_late(session, stub, budget),
    )
    log.rung_run(
        "stage 8: media undecodable",
        "normal-test",
        lambda: rung_garbage(session, budget),
    )
    log.rung_run(
        "stage 8: media eviction",
        "normal-test",
        lambda: rung_evict(session, png),
    )
    log.rung_run(
        "stage 5: http throwing receiver",
        "normal-test",
        lambda: rung_receiver(session, stub),
    )
    log.rung_run(
        "stage 5: close without error line",
        "normal-test",
        lambda: rung_silent(session),
    )
    log.rung_run(
        "stage 5: queue handler throws",
        "normal-test",
        lambda: rung_handler(session),
    )
    log.rung_run(
        "stage 7: console open, close, exit, open",
        "normal-test",
        lambda: rung_cycle(session),
    )
    waits = _WIRE_SECONDS + gold_value("rung_seconds")
    log.rung_run(
        "stage 5: wire token timer",
        "normal-test",
        lambda: rung_token(session),
        waits,
    )
    log.rung_run(
        "stage 5: wire open timer",
        "normal-test",
        lambda: rung_opening(session, stub),
        waits,
    )
    log.rung_run(
        "stage 7: console closed before open",
        "normal-test",
        lambda: rung_closing(session, stub),
    )
    session.preload_remove(identifier)


# The root whose ttyd runs a main loop that never writes the first line.
def rungs_stalled(session: PageSession) -> None:
    session.log.rung_run(
        "stage 5: wire first line timer",
        "normal-test",
        lambda: rung_stalled(session),
        _WIRE_SECONDS + gold_value("rung_seconds"),
    )


# The root whose ttyd asks a credential, the ports on the page's thread.
def rungs_credential(session: PageSession) -> None:
    identifier = session.preload_add(_WORKER_STUB)
    session.log.rung_run(
        "stage 7: token with a credential",
        "normal-test",
        lambda: rung_credential(session),
    )
    session.preload_remove(identifier)


# The root whose ttyd runs the echo main loop, the port on the page's thread.
def rungs_echo(session: PageSession) -> None:
    identifier = session.preload_add(_WORKER_STUB)
    session.log.rung_run(
        "stage 5: wire drain poll",
        "normal-test",
        lambda: rung_drain_poll(session),
        gold_value("echo_seconds"),
    )
    session.log.rung_run(
        "stage 5: wire drain timer",
        "normal-test",
        lambda: rung_drain_timer(session),
        _DRAIN_SECONDS + gold_value("rung_seconds"),
    )
    session.preload_remove(identifier)


# The root with debug false: the page runs nothing, the console is refused.
def rungs_release(session: PageSession) -> None:
    log = session.log
    log.rung_run(
        "stage 5: release runs nothing",
        "normal-test",
        lambda: rung_gating(session),
    )
    log.rung_run(
        "stage 7: console role refused",
        "normal-test",
        lambda: rung_refused_role(session),
    )


# Builds the one page the first time a root of the run serves it.
def page_ready(context: RunContext) -> None:
    import page_build

    if _PAGE_NAME in context.built:
        return
    context.log.rung_start(f"build {_PAGE_NAME}", gold_value("rung_seconds"))
    digest = page_build.page_build(_PAGE_TEMPLATE, _PAGE_NAME)
    context.log.setup_print(f"built {_PAGE_PATH}, sha256 {digest}")
    context.built.add(_PAGE_NAME)


# When the category runs the root: makes it, serves it, runs `body` on it.
def session_run(
    context: RunContext,
    name: str,
    label: str,
    overrides: dict[str, Any],
    extras: ServerExtras,
    place: Callable[[str, dict[str, Any]], None],
    body: Callable[[PageSession], None],
) -> None:
    log = context.log
    if not log.book.root_enter(name, label):
        return
    page_ready(context)
    root, index, values, gold = root_make(context.work, name, overrides)
    place(root, values)
    seconds: float = gold_value("rung_seconds")
    log.rung_start(f"ttyd for the root {name}", seconds)
    with TtydServer(root, index, values, extras, log) as ttyd:
        session = PageSession(context.browser, log, ttyd, values, gold)
        body(session)
        log.rung_start(f"leaving the root {name}", seconds)
        session.page_leave()
    log.book.root_leave()


# The stub's own page, which proves the browser reaches it first.
def rung_reachable(context: RunContext) -> str:
    url = stub_ready(context).url_make(_TEXT_PATH)
    context.browser.page_open(url)
    return f"the browser loaded {url} from the stub HTTP server"


# Runs the rungs of every root the category runs in one browser.
def stages_run(log: RungLog, work: str) -> None:
    import devtools

    os.makedirs(_PNG_PATH, exist_ok=True)
    width, height = gold_value("window_width"), gold_value("window_height")
    with (
        HeldExit(contextlib.ExitStack()) as stack,
        HeldExit(
            devtools.Browser(width, height, devtools.WindowsRelay())
        ) as browser,
    ):
        browser.console_follow(console_copy)
        log.client_bind(browser.client_get())
        context = RunContext(
            browser, log, work, stack, [], port_closed(stack), set()
        )
        session_run(
            context,
            "suites",
            "smoke-test",
            {},
            ServerExtras(*_EXTRAS_NONE),
            nothing_place,
            rungs_suites,
        )
        session_run(
            context,
            "faults",
            "normal-test",
            {},
            ServerExtras(*_EXTRAS_NONE),
            nothing_place,
            rungs_faults,
        )
        log.rung_run(
            "stage 5: stub reachable",
            "normal-test",
            lambda: rung_reachable(context),
        )
        session_run(
            context,
            "probe",
            "normal-test",
            {},
            ServerExtras(*_EXTRAS_NONE),
            nothing_place,
            lambda session: rungs_probe(session, context),
        )
        session_run(
            context,
            "credential",
            "normal-test",
            {},
            ServerExtras((_CREDENTIAL_OPTION, _CREDENTIAL), ()),
            nothing_place,
            rungs_credential,
        )
        session_run(
            context,
            "echo",
            "normal-test",
            {"debug": True},
            ServerExtras((), (_LOOP_OPTION, _ECHO_LOOP_NAME)),
            echo_place,
            rungs_echo,
        )
        session_run(
            context,
            "stalled",
            "normal-test",
            {"debug": True},
            ServerExtras((), (_LOOP_OPTION, _STALL_LOOP_NAME)),
            stall_place,
            rungs_stalled,
        )
        session_run(
            context,
            "release",
            "normal-test",
            {"debug": False},
            ServerExtras(*_EXTRAS_NONE),
            nothing_place,
            rungs_release,
        )
        session_run(
            context,
            "locked",
            "normal-test",
            {},
            ServerExtras(*_EXTRAS_NONE),
            nothing_place,
            rungs_locked,
        )


# Exits with 128 plus the signal's number, so the blocks stop what they run.
def signal_exit(number: int, frame: types.FrameType | None) -> None:
    sys.exit(_SIGNAL_BASE + number)


# Runs the rungs of the chosen category in order and returns the exit code.
def main(arguments: list[str]) -> int:
    import category

    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description="Run the browser test: the TypeScript suites over TAP and"
        " the rungs of the one page, in roots under build/, through the ttyd"
        " the install script builds, in headless Chrome.",
    )
    category.options_add(parser)
    chosen: str = parser.parse_args(arguments).category
    for number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(number, signal_exit)
    log = RungLog(chosen)
    try:
        ttyd = ttyd_path()
        if not os.path.isfile(ttyd):
            raise CheckFailed(
                f"{ttyd} is missing: {_INSTALL_SCRIPT} builds it"
            )
        work = tempfile.mkdtemp(prefix=_WORK_PREFIX, dir=_BUILD_PATH)
        log.setup_print(f"the roots of this run are kept in {work}")
        stages_run(log, work)
    except CheckFailed as failure:
        # A stub's failure landing after a cleanup prints the failure before.
        if failure.__context__ is not None:
            traceback.print_exception(failure.__context__)
        print(f"error: {log.rung}: {failure}", file=sys.stderr)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        return _EXIT_INTERRUPTED
    except Exception as failure:
        failure.add_note(f"the rung that ran: {log.rung}")
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
