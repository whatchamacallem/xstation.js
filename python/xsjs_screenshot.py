#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Answers bootstrap.py's CHALLENGE from Chrome, typing into the web
# terminal's page as a person would, waits for bootstrap.py to echo the
# answer back, then saves a screenshot of the page. ttyd's own development
# setup serves bootstrap.py, from a checkout of ttyd beside this project:
#
#     python3 python/xsjs_screenshot.py
#     python3 python/xsjs_screenshot.py --typing 'héllo' --out shot.png
#
# It drives Chrome through Chrome's DevTools protocol. How to start Chrome
# and reach its DevTools differs by platform, so each platform has a module,
# xsjs_screenshot_<platform>.py, with a Browser class: a context manager
# whose devtools_reader and devtools_writer carry a connection to DevTools
# at devtools_host and devtools_path. So far there is xsjs_screenshot_wsl.py.

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import os
import platform
import re
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from types import FrameType, ModuleType
from typing import Any

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _PYTHON_PATH)

_BOOTSTRAP_NAME = "bootstrap.py"

_CHALLENGE_PATTERN = re.compile(r"^CHALLENGE:", re.MULTILINE)

# How long the page has to show what came before ttyd closed.
_CLOSED_GRACE_SECONDS = 0.5
_CLOSED_EVENT = "Network.webSocketClosed"

# ttyd's html/webpack.config.js serves the page on this port.
_DEV_SERVER_PORT = 9000
_DEV_SERVER_URL = f"http://localhost:{_DEV_SERVER_PORT}/"

_ENTER_KEY: dict[str, str | int] = {
    "code": "Enter",
    "key": "Enter",
    "nativeVirtualKeyCode": 13,
    "windowsVirtualKeyCode": 13,
}

# Waits until the page has drawn what the terminal holds.
_FRAMES_DRAWN_SCRIPT = (
    "new Promise(done => requestAnimationFrame("
    "() => requestAnimationFrame(done)))"
)

_IMAGE_NAME = "xsjs_screenshot.png"

_POLL_SECONDS = 0.1

_REFUSED_ERROR_TEXT = "net::ERR_CONNECTION_REFUSED"

# Covers Chrome's slow first start on a new profile, and the wait for each
# line of the terminal.
_RUN_TIMEOUT_SECONDS = 180

_SERVER_WAIT_SECONDS = 60

_STOP_WAIT_SECONDS = 5

# ttyd sets window.term to its xterm.js Terminal, which parses what it's
# written later, so let it finish first.
_TERMINAL_TEXT_SCRIPT = """(async () => {
    const terminal = window.term;
    if (!terminal) return "";
    await new Promise(done => terminal.write("", done));
    const buffer = terminal.buffer.active;
    const lines = [];
    for (let row = 0; row < buffer.length; row++) {
        lines.push(buffer.getLine(row).translateToString(true));
    }
    return lines.join("\\n");
})()"""
_TERMINAL_WAIT_SECONDS = 30

_TTYD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(_PYTHON_PATH)), "ttyd"
)
# The dev server forwards /token and /ws to ttyd on this port.
_TTYD_PORT = 7681
_TTYD_REPOSITORY_URL = "https://github.com/tsl0922/ttyd.git"

_TYPING_DEFAULT = "ACCEPTED"

_VIEWPORT_HEIGHT_PX = 720
_VIEWPORT_WIDTH_PX = 1280

_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_WEBSOCKET_OPCODE_CLOSE = 0x8
_WEBSOCKET_OPCODE_PING = 0x9
_WEBSOCKET_OPCODE_PONG = 0xA
_WEBSOCKET_OPCODE_TEXT = 0x1


class DevTools:
    def __init__(self, browser: Any) -> None:
        self.browser = browser
        self.call_id = 0
        self.session_id = ""
        # The names of the events that came while waiting for answers.
        self.event_names: set[str] = set()
        self.handshake()

    def bytes_read(self, count: int) -> bytes:
        data = self.browser.devtools_reader.read(count)
        if len(data) != count:
            raise ConnectionError("DevTools closed the connection")
        return data

    # Asks the browser to close, minding no answer, as it may close first.
    def browser_close(self) -> None:
        with contextlib.suppress(OSError, RuntimeError):
            self.call("Browser.close")

    # Answers the result of a DevTools method, on the page once attached.
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
            if "method" in reply:
                self.event_names.add(reply["method"])
        if "error" in reply:
            raise RuntimeError(f"{method}: {reply['error'].get('message')}")
        return reply.get("result", {})

    # Answers what the page's expression came to, awaiting a promise.
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

    # Answers the next WebSocket message, answering pings on the way.
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


# Answers the module that starts a browser on this platform.
def browser_module() -> ModuleType | None:
    if "microsoft" in platform.uname().release.lower():
        import xsjs_screenshot_wsl

        return xsjs_screenshot_wsl
    return None


# Types the answer at bootstrap.py's CHALLENGE, waits for the echo, then
# saves the page as a PNG. Answers the echoed line.
def challenge_meet(
    devtools: DevTools, url: str, answer: str, image_path: str
) -> str:
    devtools.page_attach()
    devtools.call(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": _VIEWPORT_WIDTH_PX,
            "height": _VIEWPORT_HEIGHT_PX,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
    )
    # A headless page has no focus to type into unless it pretends to.
    devtools.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    # Reports, among others, when ttyd closes the terminal's WebSocket.
    devtools.call("Network.enable")
    response = challenge_try(devtools, url, answer)
    devtools.evaluate(_FRAMES_DRAWN_SCRIPT)
    image = devtools.call("Page.captureScreenshot", {"format": "png"})
    # ttyd's page clears the terminal when it reconnects after ttyd drops
    # the connection, so check the echo was still there once captured.
    text = devtools.evaluate(_TERMINAL_TEXT_SCRIPT) or ""
    if response not in text.split("\n"):
        raise RuntimeError(
            "ttyd's page cleared the terminal before the screenshot. The"
            f" terminal shows:\n{text.rstrip() or '(nothing)'}"
        )
    image_dir = os.path.dirname(image_path)
    if image_dir:
        os.makedirs(image_dir, exist_ok=True)
    with open(image_path, "wb") as image_file:
        image_file.write(base64.b64decode(image["data"]))
    return response


# Loads the page, so ttyd starts a bootstrap.py, and answers it. Answers
# the echoed line.
def challenge_try(devtools: DevTools, url: str, answer: str) -> str:
    # WSL forwards Windows' localhost to a port some time after the port
    # opens, so the browser can be refused at first.
    deadline = time.monotonic() + _SERVER_WAIT_SECONDS
    while True:
        devtools.event_names.clear()
        navigated = devtools.call("Page.navigate", {"url": url})
        error_text = navigated.get("errorText")
        if not error_text:
            break
        if error_text != _REFUSED_ERROR_TEXT or time.monotonic() > deadline:
            raise RuntimeError(f"{url}: {error_text}")
        time.sleep(_POLL_SECONDS)
    terminal_wait(devtools, _CHALLENGE_PATTERN, "CHALLENGE")
    devtools.evaluate("window.term.focus()")
    # Arrives as typed text, as from a keyboard's input method, so it may
    # be any Unicode.
    devtools.call("Input.insertText", {"text": answer})
    devtools.call(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "text": "\r", "unmodifiedText": "\r"} | _ENTER_KEY,
    )
    devtools.call("Input.dispatchKeyEvent", {"type": "keyUp"} | _ENTER_KEY)
    response_pattern = re.compile(
        rf"^RESPONSE: {re.escape(answer)}$", re.MULTILINE
    )
    return terminal_wait(devtools, response_pattern, "RESPONSE")


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


# Fails if something already listens on the port, as it would be served in
# place of what this script starts.
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


# Starts a server in a session of its own, so stopping it stops its
# children, and a ^C reaches only this script, which stops it.
def process_start(arguments: list[str], cwd: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        arguments,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        start_new_session=True,
    )


def process_stop(process: subprocess.Popen[bytes]) -> None:
    # The session is gone once all of it has exited.
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(_STOP_WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def signal_exit(signal_number: int, frame: FrameType | None) -> None:
    sys.exit(128 + signal_number)


def signal_time_out(signal_number: int, frame: FrameType | None) -> None:
    raise TimeoutError(f"gave up after {_RUN_TIMEOUT_SECONDS} s")


# Answers the line of the terminal the pattern finds, once it's there.
def terminal_wait(
    devtools: DevTools, pattern: re.Pattern[str], waited_for: str
) -> str:
    deadline = time.monotonic() + _TERMINAL_WAIT_SECONDS
    closed_deadline: float | None = None
    while True:
        text = devtools.evaluate(_TERMINAL_TEXT_SCRIPT) or ""
        found = pattern.search(text)
        if found:
            return found.group(0)
        if closed_deadline is None and _CLOSED_EVENT in devtools.event_names:
            closed_deadline = time.monotonic() + _CLOSED_GRACE_SECONDS
        if closed_deadline is not None and time.monotonic() > closed_deadline:
            raise RuntimeError(
                f"ttyd closed the connection before {waited_for} came. The"
                f" terminal shows:\n{text.rstrip() or '(nothing)'}"
            )
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"no {waited_for} in {_TERMINAL_WAIT_SECONDS} s. The"
                f" terminal shows:\n{text.rstrip() or '(nothing)'}"
            )
        time.sleep(_POLL_SECONDS)


# Clones ttyd, builds it and installs its page's packages as its README
# says, each only when missing. Updating them is the maintainer's to do.
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
    html_path = os.path.join(ttyd_path, "html")
    if not os.path.isdir(os.path.join(html_path, "node_modules")):
        command_run(["corepack", "yarn", "install"], html_path)


# Serves bootstrap.py as ttyd's html/README.md serves bash for development:
# ttyd, with the flags xsjs_start.ps1 gives it without a password, behind
# the page's dev server.
@contextlib.contextmanager
def ttyd_serve(ttyd_path: str) -> Generator[None]:
    for port in (_TTYD_PORT, _DEV_SERVER_PORT):
        port_check(port)
    processes: list[subprocess.Popen[bytes]] = []
    try:
        ttyd = process_start(
            [
                os.path.join(ttyd_path, "build", "ttyd"),
                "--port",
                str(_TTYD_PORT),
                "--cwd",
                _PYTHON_PATH,
                "--writable",
                "--check-origin",
                "--interface",
                "127.0.0.1",
                "python3",
                _BOOTSTRAP_NAME,
            ],
            _PYTHON_PATH,
        )
        processes.append(ttyd)
        port_wait(ttyd, "ttyd", _TTYD_PORT)
        dev_server = process_start(
            ["corepack", "yarn", "run", "start"],
            os.path.join(ttyd_path, "html"),
        )
        processes.append(dev_server)
        port_wait(dev_server, "yarn run start", _DEV_SERVER_PORT)
        yield
    finally:
        for process in reversed(processes):
            process_stop(process)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Answer bootstrap.py's CHALLENGE from Chrome and save"
        " a screenshot of the echo."
    )
    parser.add_argument(
        "--out",
        default=os.path.join(_PYTHON_PATH, _IMAGE_NAME),
        help="where the PNG goes (default %(default)s)",
    )
    parser.add_argument(
        "--typing",
        default=_TYPING_DEFAULT,
        help="what Chrome types at the CHALLENGE (default %(default)s)",
    )
    namespace = parser.parse_args()
    if any(character < " " for character in namespace.typing):
        print("error: --typing can't hold control characters", file=sys.stderr)
        return 2

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
    image_path = os.path.abspath(namespace.out)
    try:
        ttyd_prepare(_TTYD_PATH)
        # A first build and install can take longer than this allows.
        signal.signal(signal.SIGALRM, signal_time_out)
        signal.alarm(_RUN_TIMEOUT_SECONDS)
        with ttyd_serve(_TTYD_PATH):
            browser = module.Browser(_VIEWPORT_WIDTH_PX, _VIEWPORT_HEIGHT_PX)
            with browser:
                devtools = DevTools(browser)
                try:
                    response = challenge_meet(
                        devtools, _DEV_SERVER_URL, namespace.typing, image_path
                    )
                finally:
                    devtools.browser_close()
    except (OSError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    print(f"{image_path}: {response}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
