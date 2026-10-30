# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Offline since 2026-10-30, kept, run by nothing, and to be brought back later.
#
# Tests the parts of devtools.py that need a browser, a later suite that
# waits on powershell.exe and on Chrome or Edge on Windows. Each test starts
# a Browser of its own on the Windows relay, on a profile of its own, at the
# DevTools address its port file gives, and a local HTTP server of the
# standard library, bound to the address of settings.json, that serves a
# scratch directory of pages under build/ once the test has it listen. The
# page opens again while it is refused, and fails on any other error or once
# its timer ends; page methods go on the page's session and browser and
# target methods on the browser's; a console message reaches every follower;
# a trace starts afresh and ends with every event sent, a synchronous load
# among them; a worker is paused in its debugger; and the page closes while
# another page stays. The waits the tests give are the gold's.

import devtools, functools, harness, http.server, os, tempfile, threading, time
import unittest

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_devtools_powershell"

# A wait chosen by its writer: how long a server is bound before it listens.
_LISTEN_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.listen_seconds")

# How often a polling wait looks again.
_POLL_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.poll_seconds")

# A wait no test reaches the end of.
_WAIT_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.wait_seconds")

# The address the servers bind, which the browser on Windows reaches.
_BIND_ADDRESS: str = harness.setting_get("powershell.bind_address")

# The width of the browser's window.
_WIDTH_PX = 800

# The height of the browser's window.
_HEIGHT_PX = 600

# The name of the worker the worker page starts, its target's title.
_WORKER_NAME = "ai"

# A page that loads nothing more.
_INDEX_PAGE = "<!DOCTYPE html>\n<title>index</title>\n"

# A page that loads another synchronously on the UI thread as it is parsed.
_SYNC_PAGE = (
    "<!DOCTYPE html>\n<title>sync</title>\n<script>\n"
    "const request = new XMLHttpRequest();\n"
    'request.open("GET", "index.html", false);\n'
    "request.send();\n"
    "</script>\n"
)

# A page that starts the named worker.
_WORKER_PAGE = (
    "<!DOCTYPE html>\n<title>worker</title>\n<script>\n"
    f'new Worker("worker.js", {{ name: "{_WORKER_NAME}" }});\n'
    "</script>\n"
)

# The worker's script, which runs often, so that a pause stops it soon.
_WORKER_SCRIPT = "setInterval(() => {}, 10);\n"

# The files of each scratch directory the server serves, by name.
_PAGES = {
    "index.html": _INDEX_PAGE,
    "sync.html": _SYNC_PAGE,
    "worker.html": _WORKER_PAGE,
    "worker.js": _WORKER_SCRIPT,
}

# An address whose host never resolves, as RFC 6761 reserves `.invalid`.
_UNRESOLVED_URL = "http://xsjs.invalid/"


# Listens after the seconds, then serves until the server is shut down.
def serve_later(
    server: http.server.ThreadingHTTPServer, seconds: float
) -> None:
    time.sleep(seconds)
    server.server_activate()
    server.serve_forever()


# Gives each test the pages, a server bound to a port, and a browser.
class BrowserCase(unittest.TestCase):
    # Writes the pages, binds the server, then starts the browser.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        pages_path = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        for name, text in _PAGES.items():
            path = os.path.join(pages_path, name)
            with open(path, "w", encoding="utf-8") as file:
                file.write(text)
        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=pages_path
        )
        self.server = http.server.ThreadingHTTPServer(
            (_BIND_ADDRESS, 0), handler, bind_and_activate=False
        )
        # Closed after the browser stops, so no connection of it is open.
        self.addCleanup(self.server.server_close)
        self.server.server_bind()
        self.browser = self.enterContext(
            devtools.Browser(_WIDTH_PX, _HEIGHT_PX, devtools.WindowsRelay())
        )

    # Listens after the seconds and serves on a thread until the test ends.
    def server_start(self, seconds: float) -> None:
        thread = threading.Thread(
            target=serve_later, args=(self.server, seconds)
        )
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)

    # Returns the address of a page of the server.
    def url_make(self, name: str) -> str:
        return f"http://{_BIND_ADDRESS}:{self.server.server_port}/{name}"


# The browser started at the address of its port file, and its calls.
class TestStart(BrowserCase):
    # The port file's address serves DevTools, and the page evaluates.
    def test_port_written(self) -> None:
        self.assertEqual(self.browser.script_evaluate("1 + 1"), 2)

    # Page methods carry the page's session, browser and target ones do not.
    def test_call_session(self) -> None:
        client = self.browser.client_get()
        evaluated = client.method_call(
            "Runtime.evaluate", {"expression": "1 + 1", "returnByValue": True}
        )
        self.assertEqual(evaluated["result"]["value"], 2)
        listed = client.method_call("Target.getTargets")
        kinds = [target["type"] for target in listed["targetInfos"]]
        self.assertIn("page", kinds)


# Navigation, sent again while refused, failing on any other error.
class TestOpen(BrowserCase):
    # A refused navigation is sent again until one loads.
    def test_open_refused(self) -> None:
        self.server_start(_LISTEN_SECONDS)
        self.browser.page_open(self.url_make("index.html"))
        title = self.browser.script_evaluate("document.title")
        self.assertEqual(title, "index")

    # Any other navigation error fails at once.
    def test_open_error(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            self.browser.page_open(_UNRESOLVED_URL)
        self.assertEqual(
            str(caught.exception),
            _UNRESOLVED_URL + ": net::ERR_NAME_NOT_RESOLVED",
        )

    # A navigation refused until its timer ends fails, naming the address.
    def test_open_timeout(self) -> None:
        url = self.url_make("index.html")
        with self.assertRaises(TimeoutError) as caught:
            self.browser.page_open(url)
        self.assertEqual(
            str(caught.exception),
            f"gave up after 60 s waiting for {url} to accept connections"
            " after net::ERR_CONNECTION_REFUSED",
        )


# The console of the page, passed to every follower as its text.
class TestConsole(BrowserCase):
    # A console message reaches every follower as its text.
    def test_console_followed(self) -> None:
        first: list[str] = []
        second: list[str] = []
        self.browser.console_follow(first.append)
        self.browser.console_follow(second.append)
        self.browser.script_evaluate('console.log("ok 1 - x", 2)')
        self.browser.client_get().events_pump(
            "the console message", lambda: bool(first)
        )
        self.assertEqual(first, ["ok 1 - x 2"])
        self.assertEqual(second, ["ok 1 - x 2"])


# Traces of the page's loads, each started afresh.
class TestTrace(BrowserCase):
    # Ending a trace returns every event sent until it completed.
    def test_trace_end(self) -> None:
        self.server_start(0)
        self.browser.trace_start(devtools.blocking_categories())
        self.browser.page_open(self.url_make("sync.html"))
        events = self.browser.trace_end()
        self.assertTrue(devtools.blocking_find(events))

    # A trace starts afresh, holding none of the loads of the one before.
    def test_trace_start(self) -> None:
        self.server_start(0)
        categories = devtools.blocking_categories()
        self.browser.trace_start(categories)
        self.browser.page_open(self.url_make("sync.html"))
        first = self.browser.trace_end()
        self.browser.trace_start(categories)
        self.browser.page_open(self.url_make("index.html"))
        second = self.browser.trace_end()
        self.assertTrue(devtools.blocking_find(first))
        self.assertEqual(devtools.blocking_find(second), [])


# A worker of the page, paused in its debugger.
class TestWorker(BrowserCase):
    # The worker is attached from the page, its debugger enabled and paused.
    def test_worker_pause(self) -> None:
        self.server_start(0)
        self.browser.page_open(self.url_make("worker.html"))
        self.browser.worker_pause(_WORKER_NAME)
        title = self.browser.script_evaluate("document.title")
        self.assertEqual(title, "worker")


# The page closed, gone from the browser's targets while another stays.
class TestClose(BrowserCase):
    # Returns the ids of the browser's page targets.
    def pages_list(self, client: devtools.ProtocolClient) -> list[str]:
        listed = client.method_call("Target.getTargets")
        return [
            target["targetId"]
            for target in listed["targetInfos"]
            if target["type"] == "page"
        ]

    # Closing the page closes its target, and no more calls to it work.
    def test_close_target(self) -> None:
        client = self.browser.client_get()
        created = client.method_call(
            "Target.createTarget", {"url": "about:blank"}
        )
        other: str = created["targetId"]
        self.browser.page_close()
        timer = devtools.WaitTimer("the page to close", _WAIT_SECONDS)
        while self.pages_list(client) != [other]:
            time.sleep(min(_POLL_SECONDS, timer.seconds_left()))
        with self.assertRaises(RuntimeError) as caught:
            self.browser.script_evaluate("1 + 1")
        self.assertTrue(str(caught.exception).startswith("Runtime.evaluate: "))
