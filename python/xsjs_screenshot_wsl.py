# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# xsjs_screenshot.py's Browser on WSL: Chrome, or else Edge, on Windows,
# headless, with a profile of its own that goes when it does. WSL's NAT
# networking can't reach Windows' 127.0.0.1, where Chrome serves DevTools,
# so a relay in powershell.exe carries the connection over its stdin and
# stdout.

import base64, contextlib, json, os, shutil, subprocess, sys, time, types, uuid
from typing import IO, NamedTuple, Self


# A browser's executable, below the folder a Windows variable names.
class BrowserLocation(NamedTuple):
    variable_name: str
    relative_path: str


_BROWSER_LOCATIONS: tuple[BrowserLocation, ...] = (
    BrowserLocation("ProgramFiles", r"Google\Chrome\Application\chrome.exe"),
    BrowserLocation(
        "ProgramFiles(x86)", r"Google\Chrome\Application\chrome.exe"
    ),
    BrowserLocation("LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe"),
    BrowserLocation(
        "ProgramFiles(x86)", r"Microsoft\Edge\Application\msedge.exe"
    ),
    BrowserLocation("ProgramFiles", r"Microsoft\Edge\Application\msedge.exe"),
)

_DEVTOOLS_PORT_FILE_NAME = "DevToolsActivePort"
# Chrome can take more than 10 seconds to start on a new profile.
_DEVTOOLS_WAIT_SECONDS = 60

_ENVIRONMENT_SCRIPT = r"""
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$values_ = [ordered]@{}
foreach ($name_ in 'LOCALAPPDATA', 'ProgramFiles', 'ProgramFiles(x86)',
        'TEMP') {
    $values_[$name_] = [Environment]::GetEnvironmentVariable($name_)
}
ConvertTo-Json $values_ -Compress
"""

_POLL_SECONDS = 0.1

_POWERSHELL_NAME = "powershell.exe"
_POWERSHELL_PATH = (
    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
)

_PROFILE_PREFIX = "xsjs_screenshot-"
_PROFILE_REMOVE_SECONDS = 10

# `C#` reading `$port_`, a thread each way, as PowerShell's CopyToAsync hangs.
_RELAY_SCRIPT = r"""
$ProgressPreference = 'SilentlyContinue'
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Net.Sockets;
using System.Threading;

public static class XsjsScreenshotRelay {
    public static void Run(int port) {
        var client = new TcpClient("127.0.0.1", port);
        client.NoDelay = true;
        var network = client.GetStream();
        var input = Console.OpenStandardInput();
        var output = Console.OpenStandardOutput();
        var upload = new Thread(() => {
            Copy(input, network);
            client.Client.Shutdown(SocketShutdown.Send);
        });
        upload.IsBackground = true;
        upload.Start();
        Copy(network, output);
    }

    static void Copy(Stream from, Stream to) {
        var buffer = new byte[65536];
        int count;
        while ((count = from.Read(buffer, 0, buffer.Length)) > 0) {
            to.Write(buffer, 0, count);
            to.Flush();
        }
    }
}
'@
[XsjsScreenshotRelay]::Run($port_)
"""

# Stops every process named `$name_` whose command line holds `$profile_`.
_STOP_SCRIPT = r"""
$ProgressPreference = 'SilentlyContinue'
Get-CimInstance Win32_Process -Filter "Name = '$name_'" |
    Where-Object { $_.CommandLine -like "*$profile_*" } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
"""
_STOP_WAIT_SECONDS = 5


# Where the browser serves DevTools on Windows' 127.0.0.1.
class DevToolsAddress(NamedTuple):
    port: int
    path: str


class Browser:
    # Keeps the window size and names a profile, starting nothing yet.
    def __init__(self, width_px: int, height_px: int) -> None:
        self.width_px = width_px
        self.height_px = height_px
        self.powershell = shutil.which(_POWERSHELL_NAME) or _POWERSHELL_PATH
        self.profile_name = _PROFILE_PREFIX + uuid.uuid4().hex
        self.profile_path = ""
        self.executable_name = ""
        self.browser_process: subprocess.Popen[bytes] | None = None
        self.relay_process: subprocess.Popen[bytes] | None = None
        self.devtools_host = ""
        self.devtools_path = ""
        self.devtools_reader: IO[bytes] | None = None
        self.devtools_writer: IO[bytes] | None = None

    # Starts the browser and its relay, cleaning up if starting fails.
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

    # Returns the WSL path of the first browser installed.
    def browser_find(self, environment: dict[str, str | None]) -> str:
        tried: list[str] = []
        for variable_name, relative_path in _BROWSER_LOCATIONS:
            base_path = environment.get(variable_name)
            if not base_path:
                continue
            windows_path = base_path.rstrip("\\") + "\\" + relative_path
            tried.append(windows_path)
            path = self.path_wsl(windows_path)
            if os.path.isfile(path):
                return path
        raise RuntimeError(
            "no Chrome or Edge found. Tried: " + ", ".join(tried)
        )

    # Stops the relay and the browser, then removes the profile.
    def close(self) -> None:
        if self.relay_process is not None:
            if self.relay_process.stdin is not None:
                with contextlib.suppress(OSError):
                    self.relay_process.stdin.close()
            self.process_wait(self.relay_process)
        if self.browser_process is not None:
            self.process_wait(self.browser_process)
            # The Windows browser outlives its WSL side and holds the profile.
            try:
                self.powershell_run(
                    f"$name_ = '{self.executable_name}'\n"
                    f"$profile_ = '{self.profile_name}'\n" + _STOP_SCRIPT
                )
            except (OSError, RuntimeError) as error:
                print(f"warning: {error}", file=sys.stderr)
        if self.profile_path:
            self.profile_remove()

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

    # Returns the WSL path of a Windows path, as wslpath maps it.
    def path_wsl(self, windows_path: str) -> str:
        completed = subprocess.run(
            ["wslpath", "-u", windows_path],
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"wslpath can't map {windows_path}")
        return completed.stdout.strip()

    # Returns the arguments that run the script in PowerShell, base64 encoded.
    def powershell_command(self, script: str) -> list[str]:
        encoded = base64.b64encode(script.encode("utf-16-le")).decode()
        return [
            self.powershell,
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded,
        ]

    # Returns what the script printed, as `UTF-8`.
    def powershell_run(self, script: str) -> str:
        completed = subprocess.run(
            self.powershell_command(script),
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            cwd=os.path.dirname(self.powershell),
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"{_POWERSHELL_NAME} exited with {completed.returncode}: "
                + completed.stderr.decode("utf-8", "replace").strip()
            )
        return completed.stdout.decode("utf-8")

    # Waits for the process to exit, killing it if it takes too long.
    def process_wait(self, process: subprocess.Popen[bytes]) -> None:
        try:
            process.wait(_STOP_WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    # Retries while the browser's last helpers let go of their files.
    def profile_remove(self) -> None:
        deadline = time.monotonic() + _PROFILE_REMOVE_SECONDS
        while True:
            try:
                shutil.rmtree(self.profile_path)
                return
            except FileNotFoundError:
                return
            except OSError as error:
                if time.monotonic() > deadline:
                    print(f"warning: {error}", file=sys.stderr)
                    return
            time.sleep(_POLL_SECONDS)

    # Starts the browser on a new profile and a relay to its DevTools.
    def start(self) -> None:
        environment: dict[str, str | None] = json.loads(
            self.powershell_run(_ENVIRONMENT_SCRIPT)
        )
        browser_path = self.browser_find(environment)
        self.executable_name = os.path.basename(browser_path)
        temp_windows_path = str(environment["TEMP"]).rstrip("\\")
        temp_path = self.path_wsl(temp_windows_path)
        self.profile_path = os.path.join(temp_path, self.profile_name)
        self.browser_process = subprocess.Popen(
            [
                browser_path,
                "--headless=new",
                "--hide-scrollbars",
                "--no-default-browser-check",
                "--no-first-run",
                "--remote-debugging-port=0",
                f"--user-data-dir={temp_windows_path}\\{self.profile_name}",
                f"--window-size={self.width_px},{self.height_px}",
                "about:blank",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=temp_path,
        )
        port, path = self.devtools_wait()
        self.relay_process = subprocess.Popen(
            self.powershell_command(f"$port_ = {port}\n" + _RELAY_SCRIPT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=temp_path,
        )
        self.devtools_host = f"127.0.0.1:{port}"
        self.devtools_path = path
        self.devtools_reader = self.relay_process.stdout
        self.devtools_writer = self.relay_process.stdin
