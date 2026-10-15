#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Holds a conversation with bootstrap.py from Chrome through bootstrap.html,
# typing and clicking as a person would, resizes the page, closes it once
# all the page's checks pass, then saves a screenshot of the whole page.
# ttyd, from a checkout of ttyd beside this project, serves them:
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
import datetime
import hashlib
import json
import os
import platform
import pwd
import re
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Generator
from types import FrameType, ModuleType
from typing import Any

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _PYTHON_PATH)

# Bytecode of the modules imported from there goes in build/.
sys.pycache_prefix = os.path.join(
    os.path.dirname(_PYTHON_PATH), "build", "pycache"
)

# The program and the page ttyd serves, from `_PYTHON_PATH`.
_BOOTSTRAP_ARGUMENTS = ["python3", "bootstrap.py"]
_BOOTSTRAP_PAGE_NAME = "bootstrap.html"

# What it asks calc, and the answer as this script computes it.
_CALC_EXPRESSION = "(2**10 + 6*7) / 2"
_CALC_VALUE = (2**10 + 6 * 7) / 2

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

# How bootstrap.html shows a command's exit in its conversation.
_EXIT_PATTERN = re.compile(r"exit code -?\d+, \d+ lines(, cancelled)?")

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

_POLL_SECONDS = 0.1

_REFUSED_ERROR_TEXT = "net::ERR_CONNECTION_REFUSED"

# vmstat's two header lines, then three samples a second apart.
_RUN_LINES_BEFORE_CANCEL = 5

# Covers Chrome's slow first start on a new profile and all the page's checks.
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
# The size the viewport is resized to.
_VIEWPORT_RESIZED_HEIGHT_PX = 1080
_VIEWPORT_RESIZED_WIDTH_PX = 1920

_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_WEBSOCKET_OPCODE_CLOSE = 0x8
_WEBSOCKET_OPCODE_PING = 0x9
_WEBSOCKET_OPCODE_PONG = 0xA
_WEBSOCKET_OPCODE_TEXT = 0x1


# bootstrap.html in the browser, read through its `window.xsjs`.
class BootstrapPage:
    # Holds the DevTools connection and the conversation read so far.
    def __init__(self, devtools: DevTools) -> None:
        self.devtools = devtools
        self.conversation: list[dict[str, str]] = []
        # How many of the conversation's entries are printed.
        self.printed = 0

    # Clicks the element with the id at its middle, as a mouse would.
    def click(self, element_id: str) -> None:
        x, y = self.devtools.evaluate(
            f"({_CENTER_SCRIPT})({json.dumps(element_id)})"
        )
        self.devtools.call(
            "Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}
        )
        for event_type in ("mousePressed", "mouseReleased"):
            self.devtools.call(
                "Input.dispatchMouseEvent",
                {
                    "type": event_type,
                    "x": x,
                    "y": y,
                    "button": "left",
                    "clickCount": 1,
                },
            )

    # Returns the index of the first matching entry from start, once it comes.
    def entry_wait(
        self, start: int, match: Callable[[dict[str, str]], bool]
    ) -> int:
        self.wait(
            lambda results: any(
                match(entry) for entry in results["conversation"][start:]
            )
        )
        return next(
            index
            for index in range(start, len(self.conversation))
            if match(self.conversation[index])
        )

    # Fails on the page's failure, adding ttyd's version when ttyd is at fault.
    def failure_check(self, results: dict[str, Any]) -> None:
        failure = results["failure"]
        if failure is None:
            return
        message = (
            f"the page's {failure['check']} check failed: {failure['detail']}"
        )
        closed = results["closed"]
        if closed is not None and closed["code"] != _CLOSE_CODE_NORMAL:
            message += f" ({ttyd_version(_TTYD_PATH)})"
        raise RuntimeError(message)

    # Returns the next entry's text, the program's reply while no command runs.
    def reply(self, index: int) -> str:
        index = self.entry_wait(index + 1, lambda entry: True)
        return self.conversation[index]["text"]

    # Types the line and presses Enter. Returns the index of the person's line.
    def say(self, text: str) -> int:
        start = len(self.conversation)
        self.devtools.call("Input.insertText", {"text": text})
        self.devtools.call(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "text": "\r", "unmodifiedText": "\r"}
            | _ENTER_KEY,
        )
        self.devtools.call(
            "Input.dispatchKeyEvent", {"type": "keyUp"} | _ENTER_KEY
        )
        index = self.entry_wait(start, lambda entry: entry["who"] == "person")
        if self.conversation[index]["text"] != text:
            raise RuntimeError(
                f"typed {text!r}, the page sent"
                f" {self.conversation[index]['text']!r}"
            )
        return index

    # Returns the results once the condition holds, printing the conversation.
    def wait(
        self, condition: Callable[[dict[str, Any]], bool]
    ) -> dict[str, Any]:
        while True:
            results: dict[str, Any] | None = self.devtools.evaluate(
                "window.xsjs"
            )
            # None until the page's script has run.
            if results is not None:
                self.conversation = results["conversation"]
                for entry in self.conversation[self.printed :]:
                    prefix = "> " if entry["who"] == "person" else ""
                    print(prefix + entry["text"], flush=True)
                self.printed = len(self.conversation)
                self.failure_check(results)
                if condition(results):
                    return results
            time.sleep(_POLL_SECONDS)


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
def browser_module() -> ModuleType | None:
    if "microsoft" in platform.uname().release.lower():
        import xsjs_screenshot_wsl

        return xsjs_screenshot_wsl
    return None


# Returns a condition that holds once the page's check of the name passes.
def check_passed(name: str) -> Callable[[dict[str, Any]], bool]:
    return lambda results: results["checks"][name]["state"] == "pass"


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


# Says each line to bootstrap.py, checking replies. Returns the pid from stat.
def conversation_hold(page: BootstrapPage, typing: str) -> int:
    page.reply(page.say("help"))
    before = datetime.datetime.now(datetime.UTC)
    reply = page.reply(page.say("time"))
    after = datetime.datetime.now(datetime.UTC)
    found = re.fullmatch(r"local: (\S+)\nUTC: (\S+)", reply)
    if found is None:
        raise RuntimeError(f"time: the program replied {reply!r}")
    local, utc = map(datetime.datetime.fromisoformat, found.groups())
    if not (
        local == utc
        and utc.utcoffset() == datetime.timedelta()
        and before <= utc <= after
    ):
        raise RuntimeError(
            f"time: the program replied {reply!r}, not one instant from"
            f" {before.isoformat()} to {after.isoformat()}"
        )
    reply_check(
        "whoami",
        page.reply(page.say("whoami")),
        f"user: {pwd.getpwuid(os.getuid()).pw_name}\nuid: {os.getuid()}\n"
        f"cwd: {os.path.realpath(_PYTHON_PATH)}",
    )
    reply = page.reply(page.say("stat"))
    figures = {
        name: value
        for name, _, value in (
            line.partition(": ") for line in reply.split("\n")
        )
    }
    uname = os.uname()
    if (figures.get("hostname"), figures.get("kernel")) != (
        uname.nodename,
        uname.release,
    ):
        raise RuntimeError(
            f"stat: the program replied {reply!r} where hostname"
            f" {uname.nodename} and kernel {uname.release} were due"
        )
    session_pid = int(figures["pid"])
    reply_check(
        "ls",
        page.reply(page.say("ls")),
        listing_text(os.path.realpath(_PYTHON_PATH)),
    )
    line = f"calc {_CALC_EXPRESSION}"
    reply_check(line, page.reply(page.say(line)), str(_CALC_VALUE))
    line = f"sha256 {typing}"
    reply_check(
        line,
        page.reply(page.say(line)),
        hashlib.sha256(typing.encode()).hexdigest(),
    )
    line = f"echo {typing}"
    reply_check(
        line,
        page.reply(page.say(line)),
        f"{typing}\n{len(typing)} characters,"
        f" {len(typing.encode())} bytes in UTF-8",
    )
    run_index = page.say("run vmstat 1")
    run_pid = started_pid(page, run_index, "vmstat 1")
    # Its lines follow the person's run and its reply.
    page.wait(
        lambda results: (
            len(results["conversation"])
            >= run_index + 2 + _RUN_LINES_BEFORE_CANCEL
        )
    )
    cancel_index = page.say("cancel")
    reply_index = page.entry_wait(
        cancel_index + 1, lambda entry: entry["text"].startswith("cancel")
    )
    reply_check(
        "cancel",
        page.conversation[reply_index]["text"],
        f"cancelled pid {run_pid}",
    )
    exit_index = page.entry_wait(reply_index + 1, entry_exit)
    # Less the person's cancel and its reply.
    lines = exit_index - (run_index + 2) - 2
    reply_check(
        "cancel",
        page.conversation[exit_index]["text"],
        f"exit code {-signal.SIGTERM}, {lines} lines, cancelled",
    )
    page.wait(check_passed("cancel"))
    run_index = page.say("run ls -l /")
    started_pid(page, run_index, "ls -l /")
    exit_index = page.entry_wait(run_index + 2, entry_exit)
    reply_check(
        "run ls -l /",
        page.conversation[exit_index]["text"],
        f"exit code 0, {exit_index - run_index - 2} lines",
    )
    page.reply(page.say("count"))
    return session_pid


# Returns whether the conversation's entry is a command's exit.
def entry_exit(entry: dict[str, str]) -> bool:
    return _EXIT_PATTERN.fullmatch(entry["text"]) is not None


# Decodes the base64 image into the path, making its directory as needed.
def image_save(image_path: str, data: str) -> None:
    image_dir = os.path.dirname(image_path)
    if image_dir:
        os.makedirs(image_dir, exist_ok=True)
    with open(image_path, "wb") as image_file:
        image_file.write(base64.b64decode(data))


# Returns the directory's entries as bootstrap.py's ls gives them, sorted.
def listing_text(path: str) -> str:
    lines: list[str] = []
    with os.scandir(path) as iterator:
        for entry in sorted(iterator, key=lambda entry: entry.name):
            size = entry.stat(follow_symlinks=False).st_size
            slash = "/" if entry.is_dir(follow_symlinks=False) else ""
            lines.append(f"{size} {entry.name}{slash}")
    return "\n".join(lines)


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
    devtools: DevTools, url: str, typing: str, image_path: str, ttyd_pid: int
) -> str:
    devtools.page_attach()
    viewport_set(devtools, _VIEWPORT_WIDTH_PX, _VIEWPORT_HEIGHT_PX)
    # A headless page has no focus to type into unless it pretends to.
    devtools.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    page_navigate(devtools, url)
    page = BootstrapPage(devtools)
    page.wait(check_passed("hello"))
    page.click("say")
    if devtools.evaluate("document.activeElement.id") != "say":
        raise RuntimeError("clicking the page's input didn't focus it")
    session_pid = conversation_hold(page, typing)
    viewport_set(
        devtools, _VIEWPORT_RESIZED_WIDTH_PX, _VIEWPORT_RESIZED_HEIGHT_PX
    )
    page.wait(check_passed("size"))
    page.wait(
        lambda results: all(
            check["state"] == "pass"
            for name, check in results["checks"].items()
            if name != "close"
        )
    )
    pids = session_pids(ttyd_pid)
    if pids != [session_pid]:
        raise RuntimeError(
            f"ttyd runs bootstrap.py as pids {pids}, where the"
            f" page's program is pid {session_pid}"
        )
    page.click("close")
    results = page.wait(
        lambda results: (
            results["closed"] is not None
            and results["closed"]["code"] == _CLOSE_CODE_NORMAL
            and results["checks"]["close"]["state"] == "pass"
        )
    )
    deadline = time.monotonic() + _STOP_WAIT_SECONDS
    while pids := session_pids(ttyd_pid):
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"bootstrap.py still runs as pids {pids}"
                f" {_STOP_WAIT_SECONDS} s after the page closed"
            )
        time.sleep(_POLL_SECONDS)
    for name, check in results["checks"].items():
        print(f"{name} {check['state']} {check['detail']}", flush=True)
    page_fit(devtools)
    image = devtools.call("Page.captureScreenshot", {"format": "png"})
    image_save(image_path, image["data"])
    return results["checks"]["close"]["detail"]


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


# Fails unless the program's reply to the line is the one due.
def reply_check(line: str, reply: str, expected: str) -> None:
    if reply != expected:
        raise RuntimeError(
            f"{line}: the program replied {reply!r} where {expected!r} was due"
        )


# Returns the pids of ttyd's children that run bootstrap.py.
def session_pids(ttyd_pid: int) -> list[int]:
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
            if (
                int(parent.split()[1]) == ttyd_pid
                and arguments == _BOOTSTRAP_ARGUMENTS
            ):
                pids.append(int(name))
    return sorted(pids)


# Exits with 128 plus the signal's number, so cleanups still run.
def signal_exit(signal_number: int, frame: FrameType | None) -> None:
    sys.exit(128 + signal_number)


# Fails the run once its alarm goes off.
def signal_time_out(signal_number: int, frame: FrameType | None) -> None:
    raise TimeoutError(f"gave up after {_RUN_TIMEOUT_SECONDS} s")


# Returns the pid of the command the say at the index started, from its reply.
def started_pid(page: BootstrapPage, index: int, words: str) -> int:
    reply = page.reply(index)
    found = re.fullmatch(
        re.escape(f"started {words} as pid ") + r"(\d+)", reply
    )
    if found is None:
        raise RuntimeError(f"run {words}: the program replied {reply!r}")
    return int(found.group(1))


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
def ttyd_serve(ttyd_path: str) -> Generator[subprocess.Popen[bytes]]:
    port_check(_TTYD_PORT)
    arguments = [
        os.path.join(ttyd_path, "build", "ttyd"),
        "--port",
        str(_TTYD_PORT),
        "--cwd",
        _PYTHON_PATH,
        "--writable",
        "--check-origin",
        "--interface",
        "127.0.0.1",
        "--index",
        os.path.join(_PYTHON_PATH, _BOOTSTRAP_PAGE_NAME),
        *_BOOTSTRAP_ARGUMENTS,
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
        description="Hold a conversation with bootstrap.py through"
        " bootstrap.html from Chrome and save a screenshot of the page."
    )
    parser.add_argument(
        "--out",
        default=os.path.join(_PYTHON_PATH, _IMAGE_NAME),
        help="where the PNG goes (default %(default)s)",
    )
    parser.add_argument(
        "--typing",
        default=_TYPING_DEFAULT,
        help="what Chrome types after sha256 and echo (default %(default)s)",
    )
    namespace = parser.parse_args()
    typing: str = namespace.typing
    if any(character < " " for character in typing):
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
    try:
        ttyd_prepare(_TTYD_PATH)
        # A first build and install can take longer than this allows.
        signal.signal(signal.SIGALRM, signal_time_out)
        signal.alarm(_RUN_TIMEOUT_SECONDS)
        with ttyd_serve(_TTYD_PATH) as ttyd:
            browser = module.Browser(_VIEWPORT_WIDTH_PX, _VIEWPORT_HEIGHT_PX)
            with browser:
                devtools = DevTools(browser)
                try:
                    response = page_meet(
                        devtools, _TTYD_PAGE_URL, typing, image_path, ttyd.pid
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
