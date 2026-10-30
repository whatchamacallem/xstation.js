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
# makes.

import devtools, os, signal, socket, unittest

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
