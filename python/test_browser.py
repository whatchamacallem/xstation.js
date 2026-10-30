#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The browser test. It builds two pages with page_build.py, the ttyd page of
# html/test.html, whose bring up runs through ttyd and the server, and the
# headless page of html/headless.html, which starts no worker until a block
# asks. It makes server roots under build/ as the start script makes them,
# each with settings.json and test_settings.json, keeping them after the run,
# serves each through a ttyd of its own, build/ttyd/ttyd as ttyd_build.py
# builds it, and drives chrome-headless-shell through devtools.LinuxPipe, rung
# by rung, each rung under a timer and named by the stage of the plan it
# proves. The suites root runs the ttyd page's bring up over TAP, each thread
# writing a document of no block, as every block runs in group A or B, and
# checks the TAP file the server keeps with the TAP consumer. The probe,
# credential and echo roots serve the headless page, whose binding of the
# realm lane the browser adds before any page loads, and drive its modules on
# the page's main thread through the probe kit, a stub HTTP server of this
# process and the server; the other roots serve the ttyd page. The rungs
# check what the page shows and what the server holds, and a fault the
# headless page's realm reports that no rung waited for fails the run. Some
# roots name a main loop file in ttyd's command, and one has ttyd ask a
# credential. PNGs of the surveyed states go to build/test_browser/, each of
# the gold's window size. Each root and each rung is labelled smoke-test or
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
import select, shutil, signal, sqlite3, subprocess, sys, tempfile, threading
import time, traceback, types
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

# The module that builds ttyd, which a missing ttyd names.
_TTYD_BUILDER = os.path.join("python", "ttyd_build.py")

# The start of the name of the directory each run makes and keeps its roots in.
_WORK_PREFIX = "test_browser-"

# The directory the PNGs of the surveyed states go to, kept after the run.
_PNG_PATH = os.path.join(_BUILD_PATH, "test_browser")

# The name of the test settings, the gold record, in a root.
_TEST_SETTINGS_NAME = "test_settings.json"

# The TypeScript run of the ttyd page: the bring up of both threads.
_RUN_UNIT = "unit"

# The strings file, which the start script copies into the root.
_STRINGS_PATH = os.path.join(_CHECKOUT_PATH, "i18n", "en-US.json")

# The seed directory, which the start script copies into the root.
_SEED_PATH = os.path.join(_PYTHON_PATH, "seed")

# The seed of the scripted provider's script, which a fresh root holds.
_SEED_SCRIPT_PATH = os.path.join(_SEED_PATH, "provider_script.json")

# The template and name of the ttyd page, whose bring up runs both threads.
_TTYD_PAGE = "test"

# The template and name of the headless page, which runs nothing at load.
_HEADLESS_PAGE = "headless"

# The binding the headless page's realm lane calls, one call per line.
_REALM_BINDING = "realm_line"

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

# The modules of the AI worker's stream: none, as each runs in group A or B.
_AI_MODULES: tuple[str, ...] = ()

# The modules of the UI thread's stream: none, as each runs in group A or B.
_UI_MODULES: tuple[str, ...] = ()

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

# The status the stub's icon gets, a missing file's.
_MISSING_STATUS = 404

# The status of a request without the credential ttyd asks.
_UNAUTHORIZED = 401

# The media type of JSON.
_JSON_MEDIA = "application/json"

# The media type of plain text.
_TEXT_MEDIA = "text/plain"

# The stub's path that takes a POST and answers JSON.
_ECHO_PATH = "/echo"

# The stub's path that answers plain text.
_TEXT_PATH = "/text"

# The stub's path that answers JSON.
_JSON_PATH = "/json"

# The icon the browser asks of a page it opens, which the stub answers 404.
_FAVICON_PATH = "/favicon.ico"

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

# The bytes of a PNG through the width and height of its header chunk.
_PNG_HEAD_BYTES = 24

# The message of the error thrown after the page loaded.
_THROWN_MESSAGE = "rung thrown error"

# The message of the fault shown after the first one.
_SECOND_MESSAGE = "rung second fault"

# The message of the promise rejection nothing handles.
_REJECTED_MESSAGE = "rung rejected promise"

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

# The thread under which the server keeps the lines it logs itself.
_SERVER_THREAD = "server"

# The first byte of a ttyd message of program output.
_OUTPUT_KIND = 0x30

# The page's probes: functions the rungs call through `Runtime.evaluate`.
_PROBE_KIT = r"""(() => {
  const probe = {
    lines: {},
    ports: {},
    wire: {},
    worker_lines: [],
    long_tasks: [],
    pair_replies: [],
    console: null,
  };
  probe.summary_make = (line) => ({
    header: line[0],
    payload: jslb.payload_of(line),
    blobs: jslb
      .headers_of(line)
      .slice(1)
      .map((blob) => {
        const bytes = jslb.field_get(blob, "data");
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
  probe.wire_open = (name, base) => {
    const record = { first: null, lines: [], closes: [] };
    const values = {};
    const cache = new substrate.CacheFiles([]);
    const port = new wire.WirePort(base, cache, (id) => values[id]);
    port.line_receive((line) => {
      record.lines.push(probe.summary_make(line));
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
  probe.line_of = (type, payload) =>
    jslb.line_make(jslb.header_make(type), [], payload);
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
    new Worker(probe.worker_source(code), { name: "probe" });
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
  probe.noise_make = (size) => {
    const data = new Uint8Array(size);
    // Each call of getRandomValues fills at most 65536 bytes.
    for (let at = 0; at < size; at += 65536) {
      crypto.getRandomValues(data.subarray(at, at + 65536));
    }
    probe.noise = data;
    let binary = "";
    for (let at = 0; at < size; at += 32768) {
      binary += String.fromCharCode(...data.subarray(at, at + 32768));
    }
    return btoa(binary);
  };
  probe.echo_burst = (name, count) => {
    const port = probe.wire[name].port;
    for (let number = 1; number <= count; number += 1) {
      const header = jslb.header_make("echo", { id: number });
      const blob = jslb.blob_make(probe.noise);
      port.line_post(jslb.line_make(header, [blob], {}), []);
    }
    return true;
  };
  probe.sync_get = () => {
    const request = new XMLHttpRequest();
    request.open("GET", location.href, false);
    request.send();
    return request.status;
  };
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

    # Calls `fn` with each payload the page calls `name` with, on every load.
    def binding_add(self, name: str, fn: Callable[[str], None]) -> None: ...

    # Saves a PNG of the page to the path.
    def screenshot_save(self, path: str) -> None: ...

    # Returns the DevTools client of the page.
    def client_get(self) -> DriverClient: ...

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
        elif path == _FAVICON_PATH:
            self.answer_send(_MISSING_STATUS, _TEXT_MEDIA, b"")
            stub.log.note_print(
                f"the stub answered GET {path} with {_MISSING_STATUS}"
            )
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
    # Takes the browser, the log, ttyd, the root's settings and the realm's.
    def __init__(
        self,
        browser: BrowserDriver,
        log: RungLog,
        ttyd: TtydServer,
        values: dict[str, Any],
        gold: dict[str, Any],
        realm_lines: list[str],
    ) -> None:
        self.browser = browser
        self.log = log
        self.ttyd = ttyd
        self.root = ttyd.root
        self.values = values
        self.gold = gold
        self.realm_lines = realm_lines
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

    # Waits for the fault screen, takes the realm's report of it, its text.
    def fault_wait(self, what: str) -> str:
        text = cast(str, self.probe_wait(what, "fault_text"))
        # The stop function sends it in the task that wrote the screen.
        self.realm_lines.clear()
        return text

    # Fails if the headless page's realm reported a fault no rung waited for.
    def realm_check(self) -> None:
        if self.realm_lines:
            line = base64.b64decode(self.realm_lines[0]).decode()
            raise CheckFailed(
                f"the page's realm lane reported a fault no rung waited for:"
                f" {line}"
            )

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
        self.realm_check()
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

    # Saves a PNG of the page under the name, of the window's size, its path.
    def shot_save(self, name: str) -> str:
        path = os.path.join(_PNG_PATH, name + ".png")
        self.browser.screenshot_save(path)
        with open(path, "rb") as file:
            size = png_size(file.read(_PNG_HEAD_BYTES))
        due = (gold_value("window_width"), gold_value("window_height"))
        if size != due:
            raise CheckFailed(
                f"{path} is {size[0]}x{size[1]} pixels, not the window's"
                f" {due[0]}x{due[1]}"
            )
        return path

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
    stack: contextlib.ExitStack
    stubs: list[StubServer]
    built: set[str]
    realm_lines: list[str]


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


# The ttyd `ttyd_build.py` builds from the pinned release and its patches.
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


# A pattern of a string's text in which each `_ANY` matches any text.
def pattern_make(text: str) -> re.Pattern[str]:
    escaped = re.escape(text).replace(re.escape(_ANY), "(.*)")
    return re.compile(escaped, re.DOTALL)


# The file of a database under the root.
def database_path(root: str, db: str) -> str:
    return os.path.join(root, db + _DB_EXTENSION)


# The file `page_build.py` writes for the page of the name.
def page_path(page: str) -> str:
    return os.path.join(_BUILD_PATH, f"{page}.html")


# A file's whole lines, untranslated, or nothing while it does not exist yet.
def file_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    return lines_after(path, 0)


# Copies each console message of the page to stderr.
def console_copy(text: str) -> None:
    sys.stderr.write(f"console: {text}\n")


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


# The words of a process's command line, none while it has none to read.
def cmdline_read(pid: int) -> list[bytes]:
    with open(f"/proc/{pid}/cmdline", "rb") as file:
        return file.read().split(b"\0")[:-1]


# Fails unless the pid is ttyd's child running its command, once it runs one.
def program_check(session: PageSession, pid: int) -> None:
    ttyd = session.ttyd
    forked = cmdline_read(ttyd.process.pid)
    # Until its exec ends, ttyd's child reads as ttyd's command line or none.
    cmdline = server_wait(
        session,
        f"the server's pid {pid} to run a command",
        lambda: None if (read := cmdline_read(pid)) in ([], forked) else read,
    )
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
    work: str, name: str, page: str, overrides: dict[str, Any]
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
    built = page_path(page)
    index = os.path.join(root, os.path.basename(built))
    shutil.copyfile(built, index)
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
        f" {stats.plan}: the AI worker's, reporting the modules"
        f" {list(_AI_MODULES)}, ahead of the UI thread's, reporting"
        f" {list(_UI_MODULES)}"
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
    program_check(session, pid)
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
    # The headless page runs no worker, so no settings come: full names.
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


# The width and height of a PNG from its header chunk.
def png_size(png: bytes) -> tuple[int, int]:
    return int.from_bytes(png[16:20]), int.from_bytes(png[20:24])


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
    program_check(session, pid)
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
    program_check(session, pid)
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


# Random bytes the page keeps for its echoes, which ttyd's deflate can't shrink.
def noise_make(session: PageSession, size: int) -> bytes:
    text = cast(str, session.probe_call("noise_make", size))
    return base64.b64decode(text, validate=True)


# The echoes due back for that many echo lines of the blob each.
def echoes_due(count: int, blob: bytes) -> list[dict[str, Any]]:
    size = len(blob)
    digest = sha256_text(blob)
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
    # Each blob stays in memory, as no cache file is free to stream into.
    size: int = session.values["overflow_bytes"]
    stall: float = gold_value("stall_seconds")
    count = gold_value("large_bytes") // size
    drain_open(session)
    blob = noise_make(session, size)
    ttyd.signal_send(signal.SIGSTOP)
    try:
        session.probe_call("echo_burst", "drain", count)
        time.sleep(stall)
    finally:
        with failure_held():
            ttyd.signal_send(signal.SIGCONT)
    lines = json_list(
        session.probe_wait("the echoes", "wire_lines", "drain", count)
    )
    if lines != echoes_due(count, blob):
        raise CheckFailed(f"the echoes came back as {lines}")
    session.fault_none("the echoes after the stall")
    return (
        f"with ttyd stopped for {stall:g} s, {count} echo requests of one"
        f" random {size} byte blob each, overflow_bytes, posted at once, more"
        " than the socket takes, as the drain timer rung shows of the same"
        " burst; continued, ttyd took the rest and every echo came back equal"
        " by sha256, with no fault"
    )


# A socket that takes no bytes for the drain wait faults the port.
def rung_drain_timer(session: PageSession) -> str:
    ttyd = session.ttyd
    size: int = session.values["overflow_bytes"]
    count = gold_value("large_bytes") // size
    drain_open(session)
    noise_make(session, size)
    ttyd.signal_send(signal.SIGSTOP)
    try:
        session.probe_call("echo_burst", "drain", count)
        text = session.fault_wait("the fault of the wait for the drain")
    finally:
        with failure_held():
            ttyd.signal_send(signal.SIGCONT)
    url = f"ws://{bind_address()}:{ttyd.port}/{_SOCKET_PATH}"
    due = text_fill("wire_wait_expired_drain", {0: url})
    if due not in text:
        raise CheckFailed(f"the fault screen shows {text!r}, not {due!r}")
    return (
        f"with ttyd stopped, {count} echo requests of one random {size} byte"
        " blob each, overflow_bytes, posted at once, filled the socket past"
        f" what it sends for the drain wait, and the port faulted with {due!r}"
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


# The whole lines of a file from a byte offset on, as text.
def lines_after(path: str, begin: int) -> str:
    with open(path, "rb") as file:
        file.seek(begin)
        data = file.read()
    return data[: data.rfind(b"\n") + 1].decode("utf-8")


# The suites root: the ttyd page's documents over TAP, then the page.
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
        "stage 5: no synchronous load on the UI thread",
        "normal-test",
        lambda: rung_blocking_none(session),
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


# The probe root of stages 5 and 7: the ports on the page's main thread.
def rungs_probe(session: PageSession, context: RunContext) -> None:
    log = session.log
    stub = stub_ready(context)
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
        "stage 5: queue two replies",
        "normal-test",
        lambda: rung_pair(session, stub),
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
    session.log.rung_run(
        "stage 7: token with a credential",
        "normal-test",
        lambda: rung_credential(session),
    )


# The root whose ttyd runs the echo main loop, the port on the page's thread.
def rungs_echo(session: PageSession) -> None:
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


# Builds the page of the name the first time a root of the run serves it.
def page_ready(context: RunContext, page: str) -> None:
    import page_build

    if page in context.built:
        return
    context.log.rung_start(f"build {page}", gold_value("rung_seconds"))
    digest = page_build.page_build(page, page)
    context.log.setup_print(f"built {page_path(page)}, sha256 {digest}")
    context.built.add(page)


# When the category runs the root: makes it, serves its page, runs `body`.
def session_run(
    context: RunContext,
    name: str,
    label: str,
    page: str,
    overrides: dict[str, Any],
    extras: ServerExtras,
    place: Callable[[str, dict[str, Any]], None],
    body: Callable[[PageSession], None],
) -> None:
    log = context.log
    if not log.book.root_enter(name, label):
        return
    page_ready(context, page)
    root, index, values, gold = root_make(context.work, name, page, overrides)
    place(root, values)
    seconds: float = gold_value("rung_seconds")
    log.rung_start(f"ttyd for the root {name}", seconds)
    with TtydServer(root, index, values, extras, log) as ttyd:
        session = PageSession(
            context.browser, log, ttyd, values, gold, context.realm_lines
        )
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
            devtools.Browser(width, height, devtools.LinuxPipe())
        ) as browser,
    ):
        browser.console_follow(console_copy)
        log.client_bind(browser.client_get())
        context = RunContext(browser, log, work, stack, [], set(), [])
        # Before any page loads, as the headless page's start throws without.
        browser.binding_add(_REALM_BINDING, context.realm_lines.append)
        session_run(
            context,
            "suites",
            "smoke-test",
            _TTYD_PAGE,
            {},
            ServerExtras(*_EXTRAS_NONE),
            nothing_place,
            rungs_suites,
        )
        session_run(
            context,
            "faults",
            "normal-test",
            _TTYD_PAGE,
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
            _HEADLESS_PAGE,
            {},
            ServerExtras(*_EXTRAS_NONE),
            nothing_place,
            lambda session: rungs_probe(session, context),
        )
        session_run(
            context,
            "credential",
            "normal-test",
            _HEADLESS_PAGE,
            {},
            ServerExtras((_CREDENTIAL_OPTION, _CREDENTIAL), ()),
            nothing_place,
            rungs_credential,
        )
        session_run(
            context,
            "echo",
            "normal-test",
            _HEADLESS_PAGE,
            {"debug": True},
            ServerExtras((), (_LOOP_OPTION, _ECHO_LOOP_NAME)),
            echo_place,
            rungs_echo,
        )
        session_run(
            context,
            "stalled",
            "normal-test",
            _TTYD_PAGE,
            {"debug": True},
            ServerExtras((), (_LOOP_OPTION, _STALL_LOOP_NAME)),
            stall_place,
            rungs_stalled,
        )
        session_run(
            context,
            "release",
            "normal-test",
            _TTYD_PAGE,
            {"debug": False},
            ServerExtras(*_EXTRAS_NONE),
            nothing_place,
            rungs_release,
        )
        session_run(
            context,
            "locked",
            "normal-test",
            _TTYD_PAGE,
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
        description="Run the browser test: the ttyd page's documents over TAP"
        " and the rungs of the ttyd page and the headless page, in roots"
        " under build/, through the ttyd ttyd_build.py builds, in"
        " chrome-headless-shell.",
    )
    category.options_add(parser)
    chosen: str = parser.parse_args(arguments).category
    for number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(number, signal_exit)
    log = RungLog(chosen)
    try:
        ttyd = ttyd_path()
        if not os.path.isfile(ttyd):
            raise CheckFailed(f"{ttyd} is missing: {_TTYD_BUILDER} builds it")
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
