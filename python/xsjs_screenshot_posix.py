# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# xsjs_screenshot.py's Browser off WSL: the first Chrome or Chromium on
# PATH, or the one of those named by its path or its name, headless, with a
# profile of its own that goes when it does. It serves DevTools on its own
# 127.0.0.1, so a socket carries the connection.

import contextlib, os, shutil, signal, socket, subprocess, tempfile, time
import types
from typing import IO, NamedTuple, Self

_BROWSER_NAMES = (
    "google-chrome",
    "chromium",
    "chromium-browser",
    "chrome",
    "chrome-headless-shell",
)

# Where the profile goes, as the run's other intermediates do.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

_DEVTOOLS_PORT_FILE_NAME = "DevToolsActivePort"
# Chrome can take more than 10 seconds to start on a new profile.
_DEVTOOLS_WAIT_SECONDS = 60

_POLL_SECONDS = 0.1

_PROFILE_PREFIX = "xsjs_screenshot-"

_STOP_WAIT_SECONDS = 5


# Where the browser serves DevTools on 127.0.0.1.
class DevToolsAddress(NamedTuple):
    port: int
    path: str


class Browser:
    # Keeps the window size and what to try, starting nothing yet.
    def __init__(
        self, width_px: int, height_px: int, browser_named: str | None = None
    ) -> None:
        self.browser_names = _BROWSER_NAMES
        if browser_named is not None:
            if os.path.basename(browser_named) not in _BROWSER_NAMES:
                raise RuntimeError(
                    f"{browser_named} is none of: " + ", ".join(_BROWSER_NAMES)
                )
            self.browser_names = (browser_named,)
        self.width_px = width_px
        self.height_px = height_px
        self.profile_path = ""
        self.executable_name = ""
        self.browser_process: subprocess.Popen[bytes] | None = None
        self.devtools_socket: socket.socket | None = None
        self.devtools_host = ""
        self.devtools_path = ""
        self.devtools_reader: IO[bytes] | None = None
        self.devtools_writer: IO[bytes] | None = None

    # Starts the browser, cleaning up if starting fails.
    def __enter__(self) -> Self:
        try:
            self.start()
        except BaseException:
            self.close()
            raise
        return self

    # Closes the browser whatever ended the block.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        self.close()

    # Returns the path of the first browser found.
    def browser_find(self) -> str:
        for name in self.browser_names:
            path = shutil.which(name)
            if path is not None:
                return path
        raise RuntimeError(
            "no Chrome or Chromium found. Tried: "
            + ", ".join(self.browser_names)
        )

    # Closes the connection, stops the browser, removes the profile.
    def close(self) -> None:
        for stream in (self.devtools_reader, self.devtools_writer):
            if stream is not None:
                stream.close()
        if self.devtools_socket is not None:
            self.devtools_socket.close()
        if self.browser_process is not None:
            # The session is gone once all of it has exited.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.browser_process.pid, signal.SIGTERM)
            try:
                self.browser_process.wait(_STOP_WAIT_SECONDS)
            except subprocess.TimeoutExpired:
                os.killpg(self.browser_process.pid, signal.SIGKILL)
                self.browser_process.wait()
        if self.profile_path:
            shutil.rmtree(self.profile_path)

    # Returns the DevTools port and path once the browser has written them.
    def devtools_wait(self) -> DevToolsAddress:
        assert self.browser_process is not None, "the browser never started"
        port_path = os.path.join(self.profile_path, _DEVTOOLS_PORT_FILE_NAME)
        deadline = time.monotonic() + _DEVTOOLS_WAIT_SECONDS
        while True:
            try:
                with open(port_path) as port_file:
                    lines = port_file.read().split()
                if len(lines) >= 2:
                    return DevToolsAddress(int(lines[0]), lines[1])
            except FileNotFoundError:
                pass
            exit_code = self.browser_process.poll()
            if exit_code is not None:
                raise RuntimeError(
                    f"{self.executable_name} exited with {exit_code} before"
                    " serving DevTools"
                )
            if time.monotonic() > deadline:
                raise RuntimeError(
                    f"{self.executable_name} served no DevTools in"
                    f" {_DEVTOOLS_WAIT_SECONDS} s"
                )
            time.sleep(_POLL_SECONDS)

    # Starts the browser on a new profile and connects to its DevTools.
    def start(self) -> None:
        browser_path = self.browser_find()
        self.executable_name = os.path.basename(browser_path)
        self.profile_path = tempfile.mkdtemp(
            prefix=_PROFILE_PREFIX, dir=_BUILD_PATH
        )
        self.browser_process = subprocess.Popen(
            [
                browser_path,
                "--headless=new",
                "--hide-scrollbars",
                "--no-default-browser-check",
                "--no-first-run",
                "--remote-debugging-port=0",
                f"--user-data-dir={self.profile_path}",
                f"--window-size={self.width_px},{self.height_px}",
                "about:blank",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            # Its own session keeps a break out and stops its helpers.
            start_new_session=True,
        )
        port, path = self.devtools_wait()
        self.devtools_socket = socket.create_connection(("127.0.0.1", port))
        self.devtools_host = f"127.0.0.1:{port}"
        self.devtools_path = path
        self.devtools_reader = self.devtools_socket.makefile("rb")
        self.devtools_writer = self.devtools_socket.makefile("wb")
