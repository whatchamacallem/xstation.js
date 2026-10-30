# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the parts of devtools.py that need the Linux browser, a later suite of
# devtools on /usr/local/bin/chrome-headless-shell, which the maintainer
# approved for the test driver on 2026-10-30. Each test starts a Browser of
# its own on the Linux pipe: the first page is about:blank and evaluates, a
# value longer than any pipe's buffer comes back whole, the page's exception
# and DevTools' refusal of an unknown method fail loud; a binding's calls come
# back with their payloads, on the page loaded after the binding too; a data:
# URL loads, and a refused navigation fails at once; a console message reaches
# its follower; and the browser's exit closes its pipe, the exit code the
# cause, whether the browser is closed, crashes or is killed, the last seen by
# the Browser's end alone. The profile is read from the browser's own command
# line, through the process id DevTools gives, and is a directory under build/
# that goes when the browser does, holding the fontconfig cache the browser
# makes. The methods the browser test calls are tested here first, as the
# Windows suite tested them on the relay, the pages served from a scratch
# directory under build/ by a local HTTP server of the standard library on
# 127.0.0.1: a screenshot is a PNG of the window's width and height; a trace
# started afresh ends with every event sent, a synchronous load on the UI
# thread among them, and none of the trace before; a worker that posts every
# 10 ms posts nothing once paused in its debugger; a load the page starts
# itself shows in the lifecycle events under a loader of its own; and the
# page closes while another page stays. The waits are the gold's.

import devtools, functools, harness, http.server, os, signal, socket, struct
import tempfile, threading, time, unittest

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the browser's profile goes.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The name the browser's errors give it.
_BROWSER_NAME = "chrome-headless-shell"

# The width of the browser's window.
_WIDTH_PX = 800

# The height of the browser's window.
_HEIGHT_PX = 600

# The name of the binding the tests add, chosen by its writer.
_BINDING_NAME = "line_send"

# A string far longer than any pipe's buffer, 1 MiB, chosen by its writer.
_LARGE_CHARACTERS = 1 << 20

# The address a refused navigation is sent to, as the driver's server binds.
_LOCAL_ADDRESS = "127.0.0.1"

# The directory fontconfig makes in the browser's cache home.
_FONTCONFIG_NAME = "fontconfig"

# The flag that names the browser's profile on its command line.
_PROFILE_FLAG = b"--user-data-dir="

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_devtools_chrome"

# How often a polling wait looks again.
_POLL_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.poll_seconds")

# How long a paused worker is watched for a message, each of two times.
_QUIET_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.quiet_seconds")

# A wait no test reaches the end of.
_WAIT_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.wait_seconds")

# A PNG's signature, then its first chunk's length, type, width and height.
_PNG_HEAD = struct.Struct(">8sI4sII")

# The signature that starts every PNG.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# The type of a PNG's first chunk, which holds its width and height.
_PNG_SIZE_CHUNK = b"IHDR"

# The name the screenshot is saved under, in a scratch directory.
_SHOT_NAME = "shot.png"

# The lifecycle events every load of a document has, as DevTools names them.
_LOAD_NAMES = frozenset(("DOMContentLoaded", "load"))

# The lifecycle event of a document that finished loading.
_LOAD_EVENT = "load"

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

# A page that starts the named worker and keeps the last count it posted.
_WORKER_PAGE = (
    "<!DOCTYPE html>\n<title>worker</title>\n<script>\n"
    f'const worker = new Worker("worker.js", {{ name: "{_WORKER_NAME}" }});\n'
    "let count = 0;\n"
    "worker.onmessage = (event) => {\n"
    "  count = event.data;\n"
    "};\n"
    "</script>\n"
)

# The worker's script, which posts a count every 10 ms while it runs.
_WORKER_SCRIPT = (
    "let count = 0;\nsetInterval(() => postMessage(++count), 10);\n"
)

# The files of each scratch directory the server serves, by name.
_PAGES = {
    "index.html": _INDEX_PAGE,
    "sync.html": _SYNC_PAGE,
    "worker.html": _WORKER_PAGE,
    "worker.js": _WORKER_SCRIPT,
}


# Returns the process id of the browser, as DevTools gives it.
def browser_pid(browser: devtools.Browser) -> int:
    info = browser.client_get().session_call("", "SystemInfo.getProcessInfo")
    pids: list[int] = [
        process["id"]
        for process in info["processInfo"]
        if process["type"] == "browser"
    ]
    (pid,) = pids
    return pid


# Returns the profile directory named on the browser's command line.
def profile_read(browser: devtools.Browser) -> str:
    with open(f"/proc/{browser_pid(browser)}/cmdline", "rb") as file:
        # The browser rewrites it as one string, its arguments joined by spaces.
        arguments = file.read().replace(b"\0", b" ").split()
    (profile,) = [
        argument.removeprefix(_PROFILE_FLAG)
        for argument in arguments
        if argument.startswith(_PROFILE_FLAG)
    ]
    return os.fsdecode(profile)


# Returns a Browser on the Linux pipe, not yet started.
def browser_make() -> devtools.Browser:
    return devtools.Browser(_WIDTH_PX, _HEIGHT_PX, devtools.LinuxPipe())


# Gives each test a browser of its own, started on the Linux pipe.
class BrowserCase(unittest.TestCase):
    # Starts the browser, stopped when the test ends.
    def setUp(self) -> None:
        self.browser = self.enterContext(browser_make())

    # Checks the error of a closed pipe, its cause the exit with the code.
    def closed_check(self, error: BaseException, code: str) -> None:
        self.assertIsInstance(error, ConnectionError)
        self.assertEqual(
            str(error), f"{_BROWSER_NAME} closed its DevTools pipe"
        )
        self.assertIsInstance(error.__cause__, RuntimeError)
        self.assertEqual(
            str(error.__cause__), f"{_BROWSER_NAME} exited with {code}"
        )


# Gives each test the pages, served on a thread, then a browser.
class ServedCase(BrowserCase):
    # Writes the pages and serves them, then starts the browser.
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
        server = http.server.ThreadingHTTPServer((_LOCAL_ADDRESS, 0), handler)
        # Closed after the browser stops, so no connection of it is open.
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        self.port = server.server_port
        super().setUp()

    # Returns the address of a page of the server.
    def url_make(self, name: str) -> str:
        return f"http://{_LOCAL_ADDRESS}:{self.port}/{name}"


# JavaScript evaluated on the page, and the errors of the page and DevTools.
class TestEvaluate(BrowserCase):
    # The first page is about:blank, and evaluates.
    def test_evaluate_blank(self) -> None:
        self.assertEqual(
            self.browser.script_evaluate("location.href"), "about:blank"
        )
        self.assertEqual(self.browser.script_evaluate("1 + 1"), 2)

    # A value longer than any pipe's buffer comes back whole.
    def test_evaluate_large(self) -> None:
        value = self.browser.script_evaluate(
            f'"x".repeat({_LARGE_CHARACTERS})'
        )
        self.assertEqual(value, "x" * _LARGE_CHARACTERS)

    # An exception the page throws fails loud with its message.
    def test_evaluate_thrown(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            self.browser.script_evaluate('throw new Error("boom")')
        first_line = str(caught.exception).split("\n")[0]
        self.assertEqual(first_line, "the page threw Error: boom")

    # A method DevTools doesn't have fails loud, naming the method.
    def test_method_unknown(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            self.browser.client_get().method_call("Page.nothingHere")
        self.assertTrue(str(caught.exception).startswith("Page.nothingHere: "))


# A binding's calls, each passed on with its payload.
class TestBinding(BrowserCase):
    # Each call comes back with its payload, in order, before the reply.
    def test_binding_called(self) -> None:
        payloads: list[str] = []
        self.browser.binding_add(_BINDING_NAME, payloads.append)
        self.browser.script_evaluate(
            f'{_BINDING_NAME}("aGk="); {_BINDING_NAME}("Kys/")'
        )
        self.assertEqual(payloads, ["aGk=", "Kys/"])

    # A page loaded after the binding is added calls it as it loads.
    def test_binding_loaded(self) -> None:
        payloads: list[str] = []
        self.browser.binding_add(_BINDING_NAME, payloads.append)
        self.browser.page_open(
            f"data:text/html,<script>{_BINDING_NAME}('loaded')</script>"
        )
        self.assertEqual(payloads, ["loaded"])


# Navigation, failing at once on a refusal, as nothing forwards here.
class TestNavigate(BrowserCase):
    # A data: URL loads, and its page evaluates.
    def test_navigate_data(self) -> None:
        self.browser.page_open("data:text/html,<title>data</title>")
        self.assertEqual(
            self.browser.script_evaluate("document.title"), "data"
        )

    # A port bound but not listening refuses, and the navigation fails at once.
    def test_navigate_refused(self) -> None:
        with socket.socket() as bound:
            bound.bind((_LOCAL_ADDRESS, 0))
            url = f"http://{_LOCAL_ADDRESS}:{bound.getsockname()[1]}/"
            with self.assertRaises(RuntimeError) as caught:
                self.browser.page_open(url)
        self.assertEqual(
            str(caught.exception), url + ": net::ERR_CONNECTION_REFUSED"
        )


# The console of the page, passed to its follower as its text.
class TestConsole(BrowserCase):
    # A console message reaches the follower as its text.
    def test_console_followed(self) -> None:
        texts: list[str] = []
        self.browser.console_follow(texts.append)
        self.browser.script_evaluate('console.log("ok 1 - x", 2)')
        self.browser.client_get().events_pump(
            "the console message", lambda: bool(texts)
        )
        self.assertEqual(texts, ["ok 1 - x 2"])


# A screenshot of the page, saved as a PNG.
class TestScreenshot(BrowserCase):
    # The PNG has the window's width and height in its header.
    def test_screenshot_size(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        shots_path = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        path = os.path.join(shots_path, _SHOT_NAME)
        self.browser.page_open("data:text/html,<title>shot</title>")
        self.browser.screenshot_save(path)
        with open(path, "rb") as file:
            head = file.read(_PNG_HEAD.size)
        signature, _, chunk, width, height = _PNG_HEAD.unpack(head)
        self.assertEqual(signature, _PNG_SIGNATURE)
        self.assertEqual(chunk, _PNG_SIZE_CHUNK)
        self.assertEqual((width, height), (_WIDTH_PX, _HEIGHT_PX))


# Traces of the page's loads, each started afresh.
class TestTrace(ServedCase):
    # Ending a trace returns every event sent until it completed.
    def test_trace_end(self) -> None:
        self.browser.trace_start(devtools.blocking_categories())
        self.browser.page_open(self.url_make("sync.html"))
        events = self.browser.trace_end()
        self.assertTrue(devtools.blocking_find(events))

    # A trace starts afresh, holding none of the loads of the one before.
    def test_trace_start(self) -> None:
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
class TestWorker(ServedCase):
    # A worker that posts while it runs posts nothing once it is paused.
    def test_worker_pause(self) -> None:
        self.browser.page_open(self.url_make("worker.html"))
        timer = devtools.WaitTimer("the worker's first count", _WAIT_SECONDS)
        while not self.browser.script_evaluate("count"):
            time.sleep(min(_POLL_SECONDS, timer.seconds_left()))
        self.browser.worker_pause(_WORKER_NAME)
        # What the worker posted before its pause lands within the first wait.
        time.sleep(_QUIET_SECONDS)
        paused = self.browser.script_evaluate("count")
        time.sleep(_QUIET_SECONDS)
        self.assertEqual(self.browser.script_evaluate("count"), paused)
        title = self.browser.script_evaluate("document.title")
        self.assertEqual(title, "worker")


# The page's loads, as its lifecycle events give them.
class TestLifecycle(ServedCase):
    # A load the page starts itself shows under a loader of its own.
    def test_load_events(self) -> None:
        self.browser.page_open(self.url_make("index.html"))
        lifecycle = self.browser.events.lifecycle
        seen = set(lifecycle)
        self.browser.script_evaluate("location.reload()")
        self.browser.client_get().events_pump(
            "the reloaded page to load",
            lambda: any(
                name == _LOAD_EVENT and (loader, name) not in seen
                for loader, name in lifecycle
            ),
        )
        (loader,) = {
            loader
            for loader, name in lifecycle
            if name == _LOAD_EVENT and (loader, name) not in seen
        }
        self.assertNotIn(loader, {loader for loader, _ in seen})
        names = {name for found, name in lifecycle if found == loader}
        self.assertLessEqual(_LOAD_NAMES, names)


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


# The browser's exit, which closes its pipe, its code the cause.
class TestExit(BrowserCase):
    # Closing the browser ends a wait with its exit, code 0.
    def test_exit_read(self) -> None:
        client = self.browser.client_get()
        client.method_call("Browser.close")
        with self.assertRaises(ConnectionError) as caught:
            client.events_pump("the browser to exit", lambda: False)
        self.closed_check(caught.exception, "0")

    # A call after the exit fails the same way, as its message can't go.
    def test_exit_write(self) -> None:
        client = self.browser.client_get()
        client.method_call("Browser.close")
        with self.assertRaises(ConnectionError):
            client.events_pump("the browser to exit", lambda: False)
        with self.assertRaises(ConnectionError) as caught:
            self.browser.script_evaluate("1 + 1")
        self.closed_check(caught.exception, "0")

    # A crash ends the call under way, its signal the code, and only there.
    def test_exit_crashed(self) -> None:
        with self.assertRaises(ConnectionError) as caught:
            self.browser.client_get().method_call("Browser.crash")
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)
        self.assertTrue(
            str(caught.exception.__cause__).startswith(
                f"{_BROWSER_NAME} exited with -"
            )
        )


# The browser's own profile, and an exit no call saw.
class TestProfile(unittest.TestCase):
    # The profile is a directory under build/ that goes when the browser does.
    def test_profile_removed(self) -> None:
        with browser_make() as browser:
            profile = profile_read(browser)
            self.assertEqual(os.path.dirname(profile), _BUILD_PATH)
            self.assertTrue(os.path.isdir(profile))
        self.assertFalse(os.path.exists(profile))

    # The fontconfig cache is made in the profile, not in the home directory.
    def test_cache_profile(self) -> None:
        with browser_make() as browser:
            profile = profile_read(browser)
            self.assertEqual(os.path.dirname(profile), _BUILD_PATH)
            self.assertTrue(
                os.listdir(os.path.join(profile, _FONTCONFIG_NAME))
            )

    # A browser killed while no call waits fails the Browser's end.
    def test_exit_unseen(self) -> None:
        profiles: list[str] = []
        with self.assertRaises(RuntimeError) as caught:
            with browser_make() as browser:
                profiles.append(profile_read(browser))
                os.kill(browser_pid(browser), signal.SIGKILL)
        self.assertEqual(
            str(caught.exception),
            f"{_BROWSER_NAME} exited with -{signal.SIGKILL.value}",
        )
        (profile,) = profiles
        self.assertFalse(os.path.exists(profile))
