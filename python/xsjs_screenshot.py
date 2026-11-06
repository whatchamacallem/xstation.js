#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Opens the page in Chrome as a person would and saves a screenshot of it, on a
# root under build/ with debug on, which runs the page's suites. It fails on
# the page's fault screen or a failing point.
#
#     python3 python/xsjs_screenshot.py [--out shot.png] [--browser NAME]
#
# How to start Chrome and reach its DevTools differs by platform, so each
# platform has a module, xsjs_screenshot_<platform>.py, with a Browser class: a
# context manager whose devtools_reader and devtools_writer carry a connection
# to DevTools at devtools_host and devtools_path. There is
# xsjs_screenshot_wsl.py for WSL and xsjs_screenshot_posix.py for elsewhere.
# --browser names one of the browsers of xsjs_screenshot_posix.py, by its path
# or its name on PATH, and starts it through that module, on WSL too.

import argparse, base64, contextlib, hashlib, json, os, platform, shutil
import signal, socket, subprocess, sys, tempfile, time, types
from collections.abc import Generator
from typing import Any

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _PYTHON_PATH)

# Bytecode of the modules imported from there goes in build/.
sys.pycache_prefix = os.path.join(
    os.path.dirname(_PYTHON_PATH), "build", "pycache"
)

_BLANK_URL = "about:blank"

# The checkout, which holds the `python` directory.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# Where the page and the root of each run go.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# Returns the text of the page's fault screen, null with none.
_FAULT_SCRIPT = """(() => {
    const pre = document.querySelector("body > pre:not(#tap_output)");
    return pre === null ? null : pre.textContent;
})()"""

# Waits until the page has drawn what it holds.
_FRAMES_DRAWN_SCRIPT = (
    "new Promise(done => requestAnimationFrame("
    "() => requestAnimationFrame(done)))"
)

_IMAGE_NAME = "xsjs_screenshot.png"

# Returns the viewport's size and how far the page's scrolling parts overflow.
_PAGE_OVERFLOW_SCRIPT = """(() => {
    const overflow = [0, 0];
    for (const element of document.querySelectorAll("*")) {
        const style = getComputedStyle(element);
        if (["auto", "scroll"].includes(style.overflowX)) {
            overflow[0] = Math.max(overflow[0],
                element.scrollWidth - element.clientWidth);
        }
        if (["auto", "scroll"].includes(style.overflowY)) {
            overflow[1] = Math.max(overflow[1],
                element.scrollHeight - element.clientHeight);
        }
    }
    return [window.innerWidth, window.innerHeight, ...overflow];
})()"""

# The page's template, in `html/`.
_PAGE_TEMPLATE = "test"

_POLL_SECONDS = 0.1

_REFUSED_ERROR_TEXT = "net::ERR_CONNECTION_REFUSED"

# Covers Chrome's slow first start on a new profile and the whole drive.
_RUN_TIMEOUT_SECONDS = 180

_SERVER_WAIT_SECONDS = 60

_SETTINGS_PATH = os.path.join(_CHECKOUT_PATH, "settings.json")

_STOP_WAIT_SECONDS = 5

# Returns the stream the page shows.
_STREAM_SCRIPT = "document.getElementById('tap_output').textContent"

_STRINGS_PATH = os.path.join("i18n", "en-US.json")

# The worker's document, then the UI thread's, which the page shows.
_TAP_DOCUMENTS = 2
# The file of the root that the server keeps them in.
_TAP_FILE_PATH = os.path.join("tap", "typescript.tap")
_TAP_VERSION = "TAP version 14\n"

# ttyd serves the page on this port.
_TTYD_PORT = 7681
_TTYD_PAGE_URL = f"http://localhost:{_TTYD_PORT}/"

_VIEWPORT_HEIGHT_PX = 720
_VIEWPORT_WIDTH_PX = 1280

_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_WEBSOCKET_OPCODE_CLOSE = 0x8
_WEBSOCKET_OPCODE_PING = 0x9
_WEBSOCKET_OPCODE_PONG = 0xA
_WEBSOCKET_OPCODE_TEXT = 0x1


class DevTools:
    # Opens a WebSocket over the browser's DevTools connection.
    def __init__(self, browser: Any) -> None:
        self.browser = browser
        self.call_id = 0
        self.session_id = ""
        self.handshake()

    # Returns the next count bytes, failing if DevTools closes first.
    def bytes_read(self, count: int) -> bytes:
        data = self.browser.devtools_reader.read(count)
        if len(data) != count:
            raise ConnectionError("DevTools closed the connection")
        return data

    # Asks the browser to close, minding no answer, as it may close first.
    def browser_close(self) -> None:
        with contextlib.suppress(OSError, RuntimeError):
            self.call("Browser.close")

    # Returns the result of a DevTools method, on the page once attached.
    def call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.call_id += 1
        request: dict[str, Any] = {
            "id": self.call_id,
            "method": method,
            "params": params or {},
        }
        if self.session_id and not method.startswith(("Browser.", "Target.")):
            request["sessionId"] = self.session_id
        self.frame_send(_WEBSOCKET_OPCODE_TEXT, json.dumps(request).encode())
        while True:
            reply = json.loads(self.message_read())
            if reply.get("id") == self.call_id:
                break
        if "error" in reply:
            raise RuntimeError(f"{method}: {reply['error'].get('message')}")
        return reply.get("result", {})

    # Returns what the page's expression came to, awaiting a promise.
    def evaluate(self, expression: str) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        if "exceptionDetails" in result:
            details = result["exceptionDetails"]
            thrown = details.get("exception", {}).get("description")
            raise RuntimeError(f"the page threw {thrown or details['text']}")
        return result["result"].get("value")

    # Sends one WebSocket frame, masked as a client's must be.
    def frame_send(self, opcode: int, payload: bytes) -> None:
        head = bytearray([0x80 | opcode])
        if len(payload) < 126:
            head.append(0x80 | len(payload))
        elif len(payload) < 1 << 16:
            head.append(0x80 | 126)
            head += len(payload).to_bytes(2, "big")
        else:
            head.append(0x80 | 127)
            head += len(payload).to_bytes(8, "big")
        mask = os.urandom(4)
        head += mask
        masked = bytes(
            byte ^ mask[index % 4] for index, byte in enumerate(payload)
        )
        self.browser.devtools_writer.write(bytes(head) + masked)
        self.browser.devtools_writer.flush()

    # Sends the WebSocket upgrade and checks that DevTools accepted the key.
    def handshake(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET {self.browser.devtools_path} HTTP/1.1\r\n"
            f"Host: {self.browser.devtools_host}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.browser.devtools_writer.write(request.encode())
        self.browser.devtools_writer.flush()
        reader = self.browser.devtools_reader
        status = reader.readline().decode("latin-1").strip()
        headers: dict[str, str] = {}
        while (line := reader.readline().decode("latin-1").strip()) != "":
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
        if not status.startswith("HTTP/1.1 101 "):
            raise ConnectionError(f"DevTools answered {status or 'nothing'}")
        accept = base64.b64encode(
            hashlib.sha1((key + _WEBSOCKET_GUID).encode()).digest()
        ).decode()
        if headers.get("sec-websocket-accept") != accept:
            raise ConnectionError("DevTools answered a WebSocket key wrongly")

    # Returns the next WebSocket message, answering pings on the way.
    def message_read(self) -> bytes:
        message = bytearray()
        while True:
            first, second = self.bytes_read(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = int.from_bytes(self.bytes_read(2), "big")
            elif length == 127:
                length = int.from_bytes(self.bytes_read(8), "big")
            payload = self.bytes_read(length)
            if opcode == _WEBSOCKET_OPCODE_CLOSE:
                raise ConnectionError("DevTools closed the connection")
            if opcode == _WEBSOCKET_OPCODE_PING:
                self.frame_send(_WEBSOCKET_OPCODE_PONG, payload)
                continue
            if opcode == _WEBSOCKET_OPCODE_PONG:
                continue
            message += payload
            if first & 0x80:
                return bytes(message)

    # Attaches to the browser's page, so later calls go to it.
    def page_attach(self) -> None:
        targets = self.call("Target.getTargets")["targetInfos"]
        pages = [target for target in targets if target["type"] == "page"]
        if pages:
            target_id = pages[0]["targetId"]
        else:
            target_id = self.call(
                "Target.createTarget", {"url": "about:blank"}
            )["targetId"]
        self.session_id = self.call(
            "Target.attachToTarget", {"targetId": target_id, "flatten": True}
        )["sessionId"]


# Returns the module that starts a browser on this platform.
def browser_module() -> types.ModuleType:
    if "microsoft" in platform.uname().release.lower():
        import xsjs_screenshot_wsl

        return xsjs_screenshot_wsl
    import xsjs_screenshot_posix

    return xsjs_screenshot_posix


# Returns the browser named, by the module off WSL, or else the platform's.
def browser_make(browser_named: str | None) -> Any:
    if browser_named is None:
        return browser_module().Browser(
            _VIEWPORT_WIDTH_PX, _VIEWPORT_HEIGHT_PX
        )
    import xsjs_screenshot_posix

    return xsjs_screenshot_posix.Browser(
        _VIEWPORT_WIDTH_PX, _VIEWPORT_HEIGHT_PX, browser_named
    )


# Returns the root's TAP documents once the last has ended, failing on a fault.
def documents_wait(devtools: DevTools, tap_path: str) -> list[str]:
    import tap_consumer

    while True:
        fault: str | None = devtools.evaluate(_FAULT_SCRIPT)
        if fault is not None:
            raise RuntimeError(f"the page faulted: {fault}")
        documents = tap_documents(tap_path)
        if (
            len(documents) == _TAP_DOCUMENTS
            and tap_consumer.document_stats(documents[-1]).well_formed
        ):
            for document in documents:
                stats = tap_consumer.document_stats(document)
                if stats.failed or not stats.well_formed:
                    raise RuntimeError(f"{tap_path} holds {document!r}")
            return documents
        time.sleep(_POLL_SECONDS)


# Decodes the base64 image into the path, making its directory as needed.
def image_save(image_path: str, data: str) -> None:
    image_dir = os.path.dirname(image_path)
    if image_dir:
        os.makedirs(image_dir, exist_ok=True)
    with open(image_path, "wb") as image_file:
        image_file.write(base64.b64decode(data))


# Grows the viewport until no part scrolls, so a screenshot holds the page.
def page_fit(devtools: DevTools) -> None:
    while True:
        devtools.evaluate(_FRAMES_DRAWN_SCRIPT)
        width_px, height_px, *overflow = devtools.evaluate(
            _PAGE_OVERFLOW_SCRIPT
        )
        if overflow == [0, 0]:
            return
        viewport_set(devtools, width_px + overflow[0], height_px + overflow[1])


# Waits for the page's streams, saves a PNG and leaves. Returns the detail.
def page_meet(
    devtools: DevTools, image_path: str, ttyd_pid: int, root_path: str
) -> str:
    devtools.page_attach()
    viewport_set(devtools, _VIEWPORT_WIDTH_PX, _VIEWPORT_HEIGHT_PX)
    page_navigate(devtools, _TTYD_PAGE_URL)
    tap_path = os.path.join(root_path, _TAP_FILE_PATH)
    documents = documents_wait(devtools, tap_path)
    # The page puts newlines between its lines and none after the last.
    stream_wait(devtools, documents[-1].removesuffix("\n"))
    command = ttyd_command(root_path)
    pids = program_pids(ttyd_pid, command)
    if len(pids) != 1:
        raise RuntimeError(
            f"ttyd runs {' '.join(command)} as pids {pids} where one was due"
        )
    page_fit(devtools)
    image = devtools.call("Page.captureScreenshot", {"format": "png"})
    image_save(image_path, image["data"])
    # The page has no way to close but being left, which ends the program.
    page_navigate(devtools, _BLANK_URL)
    deadline = time.monotonic() + _STOP_WAIT_SECONDS
    while pids_left := program_pids(ttyd_pid, command):
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"{' '.join(command)} still runs as pids {pids_left}"
                f" {_STOP_WAIT_SECONDS} s after the page was left"
            )
        time.sleep(_POLL_SECONDS)
    return f"{len(documents)} TAP documents, pid {pids[0]} gone"


# Opens the URL, retrying refusals, since WSL forwards a new port with a lag.
def page_navigate(devtools: DevTools, url: str) -> None:
    deadline = time.monotonic() + _SERVER_WAIT_SECONDS
    while True:
        navigated = devtools.call("Page.navigate", {"url": url})
        error_text = navigated.get("errorText")
        if not error_text:
            return
        if error_text != _REFUSED_ERROR_TEXT or time.monotonic() > deadline:
            raise RuntimeError(f"{url}: {error_text}")
        # The one retry, before any page exists, so it shows.
        print(f"{url}: {error_text}, navigating again", file=sys.stderr)
        time.sleep(_POLL_SECONDS)


# Builds the page as the start script does and returns its path.
def page_ready(values: dict[str, Any]) -> str:
    import page_build

    page_name: str = values["powershell"]["engine_page"]
    page_build.page_build(_PAGE_TEMPLATE, os.path.splitext(page_name)[0])
    return os.path.join(_BUILD_PATH, page_name)


# Fails if something already listens on the port, as it would answer instead.
def port_check(port: int) -> None:
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            pass
    except ConnectionRefusedError:
        return
    raise RuntimeError(f"something already listens on port {port}")


# Returns once the process listens on the port.
def port_wait(process: subprocess.Popen[bytes], name: str, port: int) -> None:
    deadline = time.monotonic() + _SERVER_WAIT_SECONDS
    while True:
        exit_code = process.poll()
        if exit_code is not None:
            raise RuntimeError(f"{name} exited with {exit_code}")
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return
        except ConnectionRefusedError:
            pass
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"{name} didn't listen on port {port} in"
                f" {_SERVER_WAIT_SECONDS} s"
            )
        time.sleep(_POLL_SECONDS)


# Starts a server in its own session: stops reach its children, `^C` doesn't.
def process_start(arguments: list[str], cwd: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        arguments,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        start_new_session=True,
    )


# Terminates the server's session, killing it if it outlives the wait.
def process_stop(process: subprocess.Popen[bytes]) -> None:
    # The session is gone once all of it has exited.
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(_STOP_WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


# Returns the pids of ttyd's children that run the command.
def program_pids(ttyd_pid: int, command: list[str]) -> list[int]:
    pids: list[int] = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        # A process can end between the listing and the reads.
        with contextlib.suppress(FileNotFoundError, ProcessLookupError):
            with open(f"/proc/{name}/status") as status_file:
                parent = next(
                    line for line in status_file if line.startswith("PPid:")
                )
            with open(f"/proc/{name}/cmdline", "rb") as cmdline_file:
                arguments = cmdline_file.read().decode().split("\0")[:-1]
            if int(parent.split()[1]) == ttyd_pid and arguments == command:
                pids.append(int(name))
    return sorted(pids)


# Makes a root as the start script does, with debug on, and returns its page.
def root_make(values: dict[str, Any], page_path: str, root_path: str) -> str:
    import switches

    settings = values["powershell"]
    python_path = os.path.join(root_path, "python")
    os.makedirs(python_path)
    for module in settings["runtime_modules"]:
        shutil.copy(os.path.join(_PYTHON_PATH, f"{module}.py"), python_path)
    shutil.copytree(
        os.path.join(_PYTHON_PATH, "seed"), os.path.join(python_path, "seed")
    )
    os.makedirs(os.path.join(root_path, os.path.dirname(_STRINGS_PATH)))
    shutil.copy(
        os.path.join(_CHECKOUT_PATH, _STRINGS_PATH),
        os.path.join(root_path, _STRINGS_PATH),
    )
    for name in settings["root_files"]:
        shutil.copy(os.path.join(_CHECKOUT_PATH, name), root_path)
    switches.parameters_write(
        root_path, {**switches.switches_get(), "debug": True}
    )
    return shutil.copy(page_path, root_path)


# Returns the settings of the checkout.
def settings_read() -> dict[str, Any]:
    with open(_SETTINGS_PATH, encoding="utf-8") as settings_file:
        values: dict[str, Any] = json.load(settings_file)
    return values


# Exits with 128 plus the signal's number, so cleanups still run.
def signal_exit(signal_number: int, frame: types.FrameType | None) -> None:
    sys.exit(128 + signal_number)


# Fails the run once its alarm goes off.
def signal_time_out(signal_number: int, frame: types.FrameType | None) -> None:
    raise TimeoutError(f"gave up after {_RUN_TIMEOUT_SECONDS} s")


# Waits until the page shows the text or departs from it.
def stream_wait(devtools: DevTools, due: str) -> None:
    while True:
        shown: str = devtools.evaluate(_STREAM_SCRIPT)
        if shown == due:
            return
        if not due.startswith(shown):
            raise RuntimeError(
                f"the page shows {shown!r} where {due!r} was due"
            )
        time.sleep(_POLL_SECONDS)


# Returns the whole TAP documents of the file, none before the server makes it.
def tap_documents(tap_path: str) -> list[str]:
    try:
        with open(tap_path, "rb") as tap_file:
            data = tap_file.read()
    except FileNotFoundError:
        return []
    before, *documents = (
        data[: data.rfind(b"\n") + 1].decode().split(_TAP_VERSION)
    )
    if before:
        raise RuntimeError(f"{tap_path} starts with {before!r}")
    return [_TAP_VERSION + document for document in documents]


# Returns the command ttyd runs: the root's bootstrap.py on the root.
def ttyd_command(root_path: str) -> list[str]:
    return [
        "python3",
        os.path.join(root_path, "python", "bootstrap.py"),
        "--root",
        root_path,
    ]


# Yields ttyd serving the page with the start script's options but no password.
@contextlib.contextmanager
def ttyd_serve(
    values: dict[str, Any], root_path: str, page_path: str
) -> Generator[subprocess.Popen[bytes]]:
    settings = values["powershell"]
    ttyd_path = os.path.join(_CHECKOUT_PATH, settings["ttyd_build"], "ttyd")
    if not os.path.isfile(ttyd_path):
        raise RuntimeError(f"{ttyd_path} is missing: ttyd_build.py builds it")
    port_check(_TTYD_PORT)
    arguments = [
        ttyd_path,
        "--port",
        str(_TTYD_PORT),
        "--interface",
        settings["bind_address"],
        "--writable",
        "--check-origin",
        "--terminal-type",
        settings["terminal_type"],
        "--index",
        page_path,
        "--url-arg",
        f"--srv-buf-size={values['srv_buf_size']}",
        *ttyd_command(root_path),
    ]
    ttyd = process_start(arguments, root_path)
    try:
        port_wait(ttyd, "ttyd", _TTYD_PORT)
        yield ttyd
    finally:
        process_stop(ttyd)


# Resizes the page's viewport to the width and height, as on a desktop.
def viewport_set(devtools: DevTools, width_px: int, height_px: int) -> None:
    devtools.call(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width_px,
            "height": height_px,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
    )


# Parses the options, runs ttyd and the browser, and returns the exit code.
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Open the page through ttyd in Chrome and save a"
        " screenshot of it."
    )
    parser.add_argument(
        "--out",
        default=os.path.join(_PYTHON_PATH, _IMAGE_NAME),
        help="where the PNG goes (default %(default)s)",
    )
    parser.add_argument(
        "--browser",
        help="start this browser of xsjs_screenshot_posix.py, by its path or"
        " its name on PATH, through that module, on WSL too",
    )
    parsed = parser.parse_args()
    out: str = parsed.out

    for signal_number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(signal_number, signal_exit)
    image_path = os.path.abspath(out)
    started = time.monotonic()
    try:
        browser = browser_make(parsed.browser)
        values = settings_read()
        page_path = page_ready(values)
        # Building the page can take longer than this allows.
        signal.signal(signal.SIGALRM, signal_time_out)
        signal.alarm(_RUN_TIMEOUT_SECONDS)
        with tempfile.TemporaryDirectory(
            prefix="xsjs_screenshot-", dir=_BUILD_PATH
        ) as work_path:
            root_path = os.path.join(work_path, "root")
            index_path = root_make(values, page_path, root_path)
            with ttyd_serve(values, root_path, index_path) as ttyd:
                with browser:
                    devtools = DevTools(browser)
                    try:
                        detail = page_meet(
                            devtools, image_path, ttyd.pid, root_path
                        )
                    finally:
                        devtools.browser_close()
    except (OSError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    print(f"{image_path}: {detail}, {time.monotonic() - started:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
