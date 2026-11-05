# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# xsjs_screenshot.py's Browser off WSL: the first Chrome or Chromium on
# PATH, headless, with a profile of its own that goes when it does. It
# serves DevTools on its own 127.0.0.1, so a socket carries the connection.

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from types import TracebackType
from typing import IO, NamedTuple, Self

_BROWSER_NAMES = ("google-chrome", "chromium", "chromium-browser", "chrome")

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
    def __init__(self, width_px: int, height_px: int) -> None:
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

    def __enter__(self) -> Self:
        try:
            self.start()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # Answers the path of the first browser on PATH.
    def browser_find(self) -> str:
        for name in _BROWSER_NAMES:
            path = shutil.which(name)
            if path is not None:
                return path
        raise RuntimeError(
            "no Chrome or Chromium on PATH. Tried: "
            + ", ".join(_BROWSER_NAMES)
        )

    # Closes the connection, stops the browser and its helpers, then removes
    # the profile.
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

    # Answers the DevTools port and path once the browser has written them.
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

    def start(self) -> None:
        browser_path = self.browser_find()
        self.executable_name = os.path.basename(browser_path)
        self.profile_path = tempfile.mkdtemp(prefix=_PROFILE_PREFIX)
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
            # In a session of its own, so a ^C reaches only
            # xsjs_screenshot.py, and stopping the session stops the
            # browser's helpers.
            start_new_session=True,
        )
        port, path = self.devtools_wait()
        self.devtools_socket = socket.create_connection(("127.0.0.1", port))
        self.devtools_host = f"127.0.0.1:{port}"
        self.devtools_path = path
        self.devtools_reader = self.devtools_socket.makefile("rb")
        self.devtools_writer = self.devtools_socket.makefile("wb")
