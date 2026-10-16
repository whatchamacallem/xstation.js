#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Drives bootstrap.html in Chrome as a person would: puts the module update,
# typed with the time of day in it and ended with ^D, runs it with
# arguments, types a line to its stdin, checks the whole transcript against
# one built from this script's own measurements, closes the page, checks
# the program is gone, then saves a screenshot of the whole page. ttyd, from
# a checkout of ttyd beside this project, serves the page on a dumb terminal
# and runs bootstrap.py on a modules directory made under build/ for the
# run; its log goes to stderr as it comes:
#
#     python3 python/xsjs_screenshot.py
#     python3 python/xsjs_screenshot.py --typing 'héllo' --out shot.png
#
# It drives Chrome through Chrome's DevTools protocol. How to start Chrome
# and reach its DevTools differs by platform, so each platform has a module,
# xsjs_screenshot_<platform>.py, with a Browser class: a context manager
# whose devtools_reader and devtools_writer carry a connection to DevTools
# at devtools_host and devtools_path. So far there is xsjs_screenshot_wsl.py.

import argparse, base64, contextlib, datetime, hashlib, json, os, platform, re
import shlex, signal, socket, subprocess, sys, tempfile, time, types
from collections.abc import Callable, Generator
from typing import Any

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _PYTHON_PATH)

# Bytecode of the modules imported from there goes in build/.
sys.pycache_prefix = os.path.join(
    os.path.dirname(_PYTHON_PATH), "build", "pycache"
)

# The line `bootstrap.py` writes first, its measurements by name.
_BANNER_PATTERN = re.compile(
    r"bootstrap (?P<bootstrap>.+) sha256 (?P<sha256>[0-9a-f]{64})"
    r" pid (?P<pid>[0-9]+) python (?P<python>\S+) modules (?P<modules>.+)"
)

# The program and the page ttyd serves.
_BOOTSTRAP_PATH = os.path.join(_PYTHON_PATH, "bootstrap.py")
_BOOTSTRAP_PAGE_PATH = os.path.join(_PYTHON_PATH, "bootstrap.html")

# Where the modules directory of each run goes.
_BUILD_PATH = os.path.join(os.path.dirname(_PYTHON_PATH), "build")

# Returns the middle of the element with the id, where a person clicks.
_CENTER_SCRIPT = """id => {
    const box = document.getElementById(id).getBoundingClientRect();
    return [box.x + box.width / 2, box.y + box.height / 2];
}"""

_CLOSE_CODE_NORMAL = 1000

_ENTER_KEY: dict[str, str | int] = {
    "code": "Enter",
    "key": "Enter",
    "nativeVirtualKeyCode": 13,
    "windowsVirtualKeyCode": 13,
}

# Waits until the page has drawn what it holds.
_FRAMES_DRAWN_SCRIPT = (
    "new Promise(done => requestAnimationFrame("
    "() => requestAnimationFrame(done)))"
)

_IMAGE_NAME = "xsjs_screenshot.png"

# The module typed into the page, its arguments, and its text with a stamp.
_MODULE_ARGS = ["--who", "demo", "42"]
_MODULE_NAME = "update"
_MODULE_SOURCE = """\
import os, sys

STAMP = "{stamp}"


def main(args):
    print("stamp", STAMP)
    print("argv", args)
    print("bootstrap", os.environ["XSJS_BOOTSTRAP"])
    print("modules", os.environ["XSJS_MODULES"])
    here = os.path.dirname(os.path.abspath(__file__))
    print("dir", here)
    for name in sorted(os.listdir(here)):
        print(os.path.getsize(os.path.join(here, name)), name)
    print("stdin", sys.stdin.readline(), end="")


if __name__ == "__main__":
    main(sys.argv[1:])
"""

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

_POLL_SECONDS = 0.1

# What `bootstrap.py` writes when it waits for a command.
_PROMPT = "$ "

_REFUSED_ERROR_TEXT = "net::ERR_CONNECTION_REFUSED"

# Covers Chrome's slow first start on a new profile and the whole drive.
_RUN_TIMEOUT_SECONDS = 180

_SERVER_WAIT_SECONDS = 60

_STOP_WAIT_SECONDS = 5

_TTYD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(_PYTHON_PATH)), "ttyd"
)
# ttyd serves the page on this port.
_TTYD_PORT = 7681
_TTYD_PAGE_URL = f"http://localhost:{_TTYD_PORT}/"
_TTYD_REPOSITORY_URL = "https://github.com/tsl0922/ttyd.git"

_TYPING_DEFAULT = "h\u00e9llo w\u00f6rld \u00a9 2026"

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
def browser_module() -> types.ModuleType | None:
    if "microsoft" in platform.uname().release.lower():
        import xsjs_screenshot_wsl

        return xsjs_screenshot_wsl
    return None


# Clicks the element with the id at its middle, as a mouse would.
def click(devtools: DevTools, element_id: str) -> None:
    x, y = devtools.evaluate(f"({_CENTER_SCRIPT})({json.dumps(element_id)})")
    devtools.call(
        "Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}
    )
    for event_type in ("mousePressed", "mouseReleased"):
        devtools.call(
            "Input.dispatchMouseEvent",
            {
                "type": event_type,
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1,
            },
        )


# Runs a command to its end, its output going to stderr.
def command_run(arguments: list[str], cwd: str) -> None:
    completed = subprocess.run(
        arguments,
        check=False,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{' '.join(arguments)} exited with {completed.returncode}"
        )


# Decodes the base64 image into the path, making its directory as needed.
def image_save(image_path: str, data: str) -> None:
    image_dir = os.path.dirname(image_path)
    if image_dir:
        os.makedirs(image_dir, exist_ok=True)
    with open(image_path, "wb") as image_file:
        image_file.write(base64.b64decode(data))


# Returns the directory's entries with their sizes, as update.py prints them.
def listing_lines(path: str) -> list[str]:
    return [
        f"{os.path.getsize(os.path.join(path, name))} {name}"
        for name in sorted(os.listdir(path))
    ]


# Types the text into the page's input and sends it with Enter.
def line_send(devtools: DevTools, text: str) -> None:
    click(devtools, "input")
    if devtools.evaluate("document.activeElement.id") != "input":
        raise RuntimeError("clicking the page's input didn't focus it")
    devtools.call("Input.insertText", {"text": text})
    typed = devtools.evaluate("document.getElementById('input').value")
    if typed != text:
        raise RuntimeError(
            f"the page's input holds {typed!r} where {text!r} was typed"
        )
    devtools.call(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "text": "\r", "unmodifiedText": "\r"} | _ENTER_KEY,
    )
    devtools.call("Input.dispatchKeyEvent", {"type": "keyUp"} | _ENTER_KEY)


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


# Drives the page as a person would and saves a PNG. Returns the close detail.
def page_meet(
    devtools: DevTools,
    typing: str,
    image_path: str,
    ttyd_pid: int,
    modules_path: str,
) -> str:
    devtools.page_attach()
    viewport_set(devtools, _VIEWPORT_WIDTH_PX, _VIEWPORT_HEIGHT_PX)
    # A headless page has no focus to type into unless it pretends to.
    devtools.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    page_navigate(devtools, _TTYD_PAGE_URL)
    # The banner is whole once the prompt follows it.
    results = page_wait(
        devtools,
        lambda results: (
            len(results["output"].partition("\n")[2]) >= len(_PROMPT)
        ),
    )
    ttyd = results["ttyd"]
    print(f"ttyd title {ttyd['title']}", flush=True)
    print(f"ttyd preferences {ttyd['preferences']}", flush=True)
    banner: str = results["output"].partition("\n")[0]
    print(banner, flush=True)
    due = f"{banner}\n{_PROMPT}"
    transcript_check(results["output"], due)
    match = _BANNER_PATTERN.fullmatch(banner)
    if match is None:
        raise RuntimeError(
            f"the banner doesn't match {_BANNER_PATTERN.pattern}"
        )
    with open(_BOOTSTRAP_PATH, "rb") as bootstrap_file:
        digest = hashlib.sha256(bootstrap_file.read()).hexdigest()
    expected_banner = {
        "bootstrap": _BOOTSTRAP_PATH,
        "sha256": digest,
        "modules": modules_path,
    }
    for name, value in expected_banner.items():
        if match[name] != value:
            raise RuntimeError(
                f"the banner's {name} is {match[name]}, not {value}"
            )
    pid = int(match["pid"])
    command = ttyd_command(modules_path)
    pids = program_pids(ttyd_pid, command)
    if pids != [pid]:
        raise RuntimeError(
            f"ttyd runs {' '.join(command)} as pids {pids}, where the"
            f" banner's pid is {pid}"
        )
    stamp = datetime.datetime.now(datetime.UTC).isoformat()
    source = _MODULE_SOURCE.format(stamp=stamp)
    put_line = f"put {_MODULE_NAME}"
    line_send(devtools, put_line)
    due += f"{put_line}\n"
    transcript_wait(devtools, due)
    # Enter ends the text's last line, then `^D` ends the text.
    line_send(devtools, source.removesuffix("\n"))
    due += source
    transcript_wait(devtools, due)
    click(devtools, "eof")
    data = source.encode()
    file_name = f"{_MODULE_NAME}.py"
    saved = (
        f"saved {file_name} {len(data)} bytes sha256"
        f" {hashlib.sha256(data).hexdigest()}"
    )
    due += f"{saved}\n{_PROMPT}"
    transcript_wait(devtools, due)
    with open(os.path.join(modules_path, file_name), "rb") as module_file:
        if module_file.read() != data:
            raise RuntimeError(
                f"{file_name} on disk differs from what was put"
            )
    print(saved, flush=True)
    run_line = shlex.join([_MODULE_NAME, *_MODULE_ARGS])
    line_send(devtools, run_line)
    printed = "".join(
        f"{line}\n"
        for line in (
            f"stamp {stamp}",
            f"argv {_MODULE_ARGS!r}",
            f"bootstrap {_BOOTSTRAP_PATH}",
            f"modules {modules_path}",
            f"dir {modules_path}",
            *listing_lines(modules_path),
        )
    )
    # The module waits on stdin after its listing.
    due += f"{run_line}\n{printed}"
    transcript_wait(devtools, due)
    module_pids = program_pids(pid, command)
    if len(module_pids) != 1:
        raise RuntimeError(
            f"{_MODULE_NAME} runs as pids {module_pids} where one was due"
        )
    line_send(devtools, typing)
    read = f"stdin {typing}\n"
    # The terminal echoes the line, the module prints it, then the prompt.
    due += f"{typing}\n{read}{_PROMPT}"
    transcript_wait(devtools, due)
    print(printed + read, end="", flush=True)
    print(
        f"run {_MODULE_NAME} pid {module_pids[0]} args"
        f" {shlex.join(_MODULE_ARGS)}, {len((printed + read).splitlines())}"
        " lines as measured here",
        flush=True,
    )
    click(devtools, "close")
    results = page_wait(
        devtools, lambda results: results["closed"] is not None
    )
    closed = results["closed"]
    if closed["code"] != _CLOSE_CODE_NORMAL:
        # A close other than Close's is ttyd's fault, not this repo's.
        raise RuntimeError(
            f"the page closed with {closed} after Close"
            f" ({ttyd_version(_TTYD_PATH)})"
        )
    transcript_check(results["output"], due)
    deadline = time.monotonic() + _STOP_WAIT_SECONDS
    while pids := program_pids(ttyd_pid, command):
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"{' '.join(command)} still runs as pids {pids}"
                f" {_STOP_WAIT_SECONDS} s after the page closed"
            )
        time.sleep(_POLL_SECONDS)
    page_fit(devtools)
    image = devtools.call("Page.captureScreenshot", {"format": "png"})
    image_save(image_path, image["data"])
    return (
        f"{len(results['output'].splitlines())} transcript lines, closed"
        f" {closed['code']} after Close, pid {pid} gone"
    )


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


# Returns the state once the condition holds, failing on a failure or close.
def page_wait(
    devtools: DevTools, condition: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    while True:
        results: dict[str, Any] | None = devtools.evaluate("window.boot")
        # None until the page's script has run.
        if results is not None:
            failure = results["failure"]
            closed = results["closed"]
            if failure is not None:
                message = f"the page failed: {failure}"
                # A close other than Close's is ttyd's fault, not this repo's.
                if closed is not None and closed["code"] != _CLOSE_CODE_NORMAL:
                    message += f" ({ttyd_version(_TTYD_PATH)})"
                raise RuntimeError(message)
            if condition(results):
                return results
            if closed is not None:
                raise RuntimeError(
                    f"the page closed with {closed} before Close"
                    f" ({ttyd_version(_TTYD_PATH)})"
                )
        time.sleep(_POLL_SECONDS)


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


# Exits with 128 plus the signal's number, so cleanups still run.
def signal_exit(signal_number: int, frame: types.FrameType | None) -> None:
    sys.exit(128 + signal_number)


# Fails the run once its alarm goes off.
def signal_time_out(signal_number: int, frame: types.FrameType | None) -> None:
    raise TimeoutError(f"gave up after {_RUN_TIMEOUT_SECONDS} s")


# Fails with both texts unless the transcript is the one due.
def transcript_check(output: str, due: str) -> None:
    if output != due:
        raise RuntimeError(f"the page shows {output!r} where {due!r} was due")


# Waits until the transcript is the one due or departs from it, then checks.
def transcript_wait(devtools: DevTools, due: str) -> None:
    results = page_wait(
        devtools,
        lambda results: (
            results["output"] == due or not due.startswith(results["output"])
        ),
    )
    transcript_check(results["output"], due)


# Returns the command ttyd runs: bootstrap.py on the modules directory.
def ttyd_command(modules_path: str) -> list[str]:
    return ["python3", _BOOTSTRAP_PATH, modules_path]


# Clones ttyd and builds it, each only when missing: the maintainer updates it.
def ttyd_prepare(ttyd_path: str) -> None:
    if not os.path.isdir(ttyd_path):
        command_run(
            ["git", "clone", _TTYD_REPOSITORY_URL, ttyd_path],
            os.path.dirname(ttyd_path),
        )
    build_path = os.path.join(ttyd_path, "build")
    if not os.path.isfile(os.path.join(build_path, "ttyd")):
        os.makedirs(build_path, exist_ok=True)
        command_run(["cmake", ".."], build_path)
        command_run(["make"], build_path)


# Yields ttyd serving the page with `xsjs_start.ps1`'s flags but no password.
@contextlib.contextmanager
def ttyd_serve(
    ttyd_path: str, modules_path: str
) -> Generator[subprocess.Popen[bytes]]:
    port_check(_TTYD_PORT)
    arguments = [
        os.path.join(ttyd_path, "build", "ttyd"),
        "--port",
        str(_TTYD_PORT),
        "--writable",
        "--check-origin",
        "--interface",
        "127.0.0.1",
        "--terminal-type",
        "dumb",
        "--index",
        _BOOTSTRAP_PAGE_PATH,
        *ttyd_command(modules_path),
    ]
    ttyd = process_start(arguments, _PYTHON_PATH)
    try:
        port_wait(ttyd, "ttyd", _TTYD_PORT)
        yield ttyd
    finally:
        process_stop(ttyd)


# Returns what ttyd says its version is, for reports of its faults.
def ttyd_version(ttyd_path: str) -> str:
    completed = subprocess.run(
        [os.path.join(ttyd_path, "build", "ttyd"), "--version"],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"ttyd --version exited with {completed.returncode}"
        )
    return completed.stdout.strip()


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
        description="Put and run a module through bootstrap.html from Chrome"
        " and save a screenshot of the page."
    )
    parser.add_argument(
        "--out",
        default=os.path.join(_PYTHON_PATH, _IMAGE_NAME),
        help="where the PNG goes (default %(default)s)",
    )
    parser.add_argument(
        "--typing",
        default=_TYPING_DEFAULT,
        help="the line Chrome types to the module's stdin (default"
        " %(default)s)",
    )
    namespace = parser.parse_args()
    typing: str = namespace.typing
    # The terminal takes these as edits or signals, `DEL` as an erase.
    if any(character < " " or character == "\x7f" for character in typing):
        print("error: --typing can't hold control characters", file=sys.stderr)
        return 2
    out: str = namespace.out

    module = browser_module()
    if module is None:
        print(
            f"error: no xsjs_screenshot_<platform>.py for {platform.system()}"
            f" {platform.release()} yet, only for WSL",
            file=sys.stderr,
        )
        return 2

    for signal_number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(signal_number, signal_exit)
    image_path = os.path.abspath(out)
    started = time.monotonic()
    try:
        ttyd_prepare(_TTYD_PATH)
        # A first build and install can take longer than this allows.
        signal.signal(signal.SIGALRM, signal_time_out)
        signal.alarm(_RUN_TIMEOUT_SECONDS)
        os.makedirs(_BUILD_PATH, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="xsjs_screenshot-", dir=_BUILD_PATH
        ) as work_path:
            modules_path = os.path.join(work_path, "modules")
            with ttyd_serve(_TTYD_PATH, modules_path) as ttyd:
                browser = module.Browser(
                    _VIEWPORT_WIDTH_PX, _VIEWPORT_HEIGHT_PX
                )
                with browser:
                    devtools = DevTools(browser)
                    try:
                        detail = page_meet(
                            devtools,
                            typing,
                            image_path,
                            ttyd.pid,
                            modules_path,
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
