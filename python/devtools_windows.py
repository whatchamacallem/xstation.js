# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The Windows transport of devtools.py. WindowsRelay drives Chrome, or else
# Edge, on Windows from WSL: WSL's NAT networking can't reach Windows'
# 127.0.0.1, where Chrome serves DevTools, so a relay in `powershell.exe`
# carries the WebSocket over its stdin and stdout. WindowsRelay is offline
# since 2026-10-30, kept, run by nothing, and to be brought back later. Its one
# suite, test_devtools_powershell.py, is a later suite, so no run counts this
# module's lines until that suite comes back. The relay's helpers that a
# running suite tests stay in devtools.py, and a private constant both modules
# need is copied here.

import devtools, errno, functools, json, os, shutil, subprocess, time, uuid
from typing import IO, cast

# The public names of this module, as its stub declares them.
__all__ = ["WindowsRelay"]

# Where to look for a browser, in order: a Windows variable and a path in it.
_BROWSER_LOCATIONS: tuple[tuple[str, str], ...] = (
    ("ProgramFiles", r"Google\Chrome\Application\chrome.exe"),
    ("ProgramFiles(x86)", r"Google\Chrome\Application\chrome.exe"),
    ("LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe"),
    ("ProgramFiles(x86)", r"Microsoft\Edge\Application\msedge.exe"),
    ("ProgramFiles", r"Microsoft\Edge\Application\msedge.exe"),
)

# The longest a command started here may run, a default chosen by its writer.
_COMMAND_WAIT_SECONDS = 60

# The file the browser writes its DevTools port and path to, in the profile.
_DEVTOOLS_PORT_FILE_NAME = "DevToolsActivePort"

# Seconds for the browser to serve DevTools, a default chosen by its writer.
_DEVTOOLS_WAIT_SECONDS = 60

# Prints the Windows variables the browser is found from, as JSON.
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

# How often a polling wait looks again, a default chosen by its writer.
_POLL_SECONDS = 0.1

# The program that runs scripts on Windows, looked up on the PATH.
_POWERSHELL_NAME = "powershell.exe"

# The errors of removing a file that a browser helper still holds open.
_PROFILE_BUSY_ERRNOS = frozenset(
    (errno.EACCES, errno.EBUSY, errno.ENOTEMPTY, errno.EPERM)
)

# The start of the name of the profile folder each run makes.
_PROFILE_PREFIX = "xsjs_devtools-"

# Seconds for the profile to become removable, a default chosen by its writer.
_PROFILE_REMOVE_SECONDS = 10

# Seconds for one answer, event or page load, a default chosen by its writer.
_REPLY_WAIT_SECONDS = 60

# Stops each process named `$name_` with `$profile_` in its command line.
_STOP_SCRIPT = r"""
$ProgressPreference = 'SilentlyContinue'
$pattern_ = "*$profile_*"
Get-CimInstance Win32_Process -Filter "Name = '$name_'" |
    Where-Object { $_.CommandLine -like $pattern_ } |
    ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
        } catch {
            # A helper gone with the browser is ObjectNotFound, as recalled.
            if ($_.CategoryInfo.Category -ne 'ObjectNotFound') {
                throw
            }
        }
    }
$end_ = [DateTime]::UtcNow.AddSeconds($seconds_)
while ($true) {
    $left_ = @(Get-CimInstance Win32_Process -Filter "Name = '$name_'" |
        Where-Object { $_.CommandLine -like $pattern_ })
    if ($left_.Count -eq 0) {
        break
    }
    if ([DateTime]::UtcNow -gt $end_) {
        throw "$name_ still runs on $profile_ after $seconds_ s"
    }
    Start-Sleep -Milliseconds $milliseconds_
}
"""

# Seconds for a stopped process to be gone, a default chosen by its writer.
_STOP_WAIT_SECONDS = 5


# Chrome, or else Edge, on Windows, through a relay in `powershell.exe`.
class WindowsRelay:
    # WSL forwards a new listener to Windows late, so a refusal is sent again.
    refused_retried = True

    # Finds `powershell.exe` and names a profile, starting nothing yet.
    def __init__(self) -> None:
        powershell = shutil.which(_POWERSHELL_NAME)
        if powershell is None:
            raise RuntimeError(f"{_POWERSHELL_NAME} isn't on the PATH")
        self.powershell = powershell
        self.profile_name = _PROFILE_PREFIX + uuid.uuid4().hex
        self.profile_path = ""
        self.executable_name = ""
        self.browser_process: subprocess.Popen[bytes] | None = None
        self.relay_process: subprocess.Popen[bytes] | None = None

    # Returns the WSL path of the first browser installed.
    def browser_find(self, environment: dict[str, str | None]) -> str:
        tried: list[str] = []
        for variable_name, relative_path in _BROWSER_LOCATIONS:
            base_path = environment.get(variable_name)
            if not base_path:
                continue
            windows_path = base_path.rstrip("\\") + "\\" + relative_path
            tried.append(windows_path)
            path = path_wsl(windows_path)
            if os.path.isfile(path):
                return path
        raise RuntimeError(
            "no Chrome or Edge found. Tried: " + ", ".join(tried)
        )

    # Stops the browser, which outlives its WSL side and holds the profile.
    def browser_stop(self) -> None:
        if self.browser_process is None:
            return
        self.powershell_run(
            f"stopping {self.executable_name}",
            f"$name_ = '{self.executable_name}'\n"
            f"$profile_ = '{self.profile_name}'\n"
            f"$seconds_ = {_STOP_WAIT_SECONDS}\n"
            f"$milliseconds_ = {round(_POLL_SECONDS * 1000)}\n" + _STOP_SCRIPT,
        )
        self.process_wait(self.executable_name, self.browser_process)

    # Returns the DevTools port and path once the browser has written them.
    def devtools_wait(self) -> devtools.EndpointAddress:
        process = cast(subprocess.Popen[bytes], self.browser_process)
        port_path = os.path.join(self.profile_path, _DEVTOOLS_PORT_FILE_NAME)
        timer = devtools.WaitTimer(
            f"{self.executable_name} to serve DevTools", _DEVTOOLS_WAIT_SECONDS
        )
        while True:
            try:
                with open(port_path) as port_file:
                    text = port_file.read()
            except FileNotFoundError:
                text = ""
            # Fewer than two fields is a file the browser is still writing.
            if len(text.split()) >= 2:
                return devtools.address_parse(text)
            exit_code = process.poll()
            if exit_code is not None:
                raise RuntimeError(
                    f"{self.executable_name} exited with {exit_code} before"
                    " serving DevTools"
                )
            time.sleep(min(_POLL_SECONDS, timer.seconds_left()))

    # Returns what the script printed in PowerShell, as `UTF-8`.
    def powershell_run(self, what: str, script: str) -> str:
        return devtools.command_run(
            f"{_POWERSHELL_NAME} {what}",
            devtools.powershell_command(self.powershell, script),
            os.path.dirname(self.powershell),
            _COMMAND_WAIT_SECONDS,
        )

    # Waits for the process to exit, killing it and failing if it takes long.
    def process_wait(
        self, what: str, process: subprocess.Popen[bytes]
    ) -> None:
        try:
            process.wait(_STOP_WAIT_SECONDS)
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.wait()
            raise TimeoutError(
                f"gave up after {_STOP_WAIT_SECONDS} s waiting for {what}"
                " to exit"
            ) from error

    # Removes the profile, waiting while browser helpers still hold its files.
    def profile_remove(self) -> None:
        if not self.profile_path or not os.path.isdir(self.profile_path):
            return
        timer = devtools.WaitTimer(
            f"{self.profile_path} to be removable", _PROFILE_REMOVE_SECONDS
        )
        while True:
            try:
                shutil.rmtree(self.profile_path)
                return
            except OSError as error:
                if error.errno not in _PROFILE_BUSY_ERRNOS:
                    raise
                time.sleep(min(_POLL_SECONDS, timer.seconds_left()))

    # Ends the relay, which exits once its connection or its input ends.
    def relay_stop(self) -> None:
        process = self.relay_process
        if process is None:
            return
        cast(IO[bytes], process.stdin).close()
        self.process_wait(f"{_POWERSHELL_NAME} relaying DevTools", process)
        cast(IO[bytes], process.stdout).close()

    # Stops the browser and the relay, then removes the profile.
    def transport_close(self) -> None:
        try:
            self.browser_stop()
        finally:
            try:
                self.relay_stop()
            finally:
                self.profile_remove()

    # Starts the browser on a new profile and opens a relay to its DevTools.
    def transport_open(
        self, width_px: int, height_px: int
    ) -> devtools.SocketChannel:
        environment: dict[str, str | None] = json.loads(
            self.powershell_run(
                "reading the Windows environment", _ENVIRONMENT_SCRIPT
            )
        )
        browser_path = self.browser_find(environment)
        self.executable_name = os.path.basename(browser_path)
        temp_windows_path = environment["TEMP"]
        if not temp_windows_path:
            raise RuntimeError("Windows has no TEMP folder")
        temp_windows_path = temp_windows_path.rstrip("\\")
        temp_path = path_wsl(temp_windows_path)
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
                f"--window-size={width_px},{height_px}",
                "about:blank",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=temp_path,
        )
        address = self.devtools_wait()
        self.relay_process = subprocess.Popen(
            devtools.powershell_command(
                self.powershell, devtools.relay_script(address.port)
            ),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=temp_path,
        )
        relay_input = cast(IO[bytes], self.relay_process.stdin)
        relay_output = cast(IO[bytes], self.relay_process.stdout)
        channel = devtools.SocketChannel(
            functools.partial(devtools.pipe_read, relay_output.fileno()),
            functools.partial(devtools.stream_write, relay_input),
        )
        timer = devtools.WaitTimer(
            "the DevTools handshake answer", _REPLY_WAIT_SECONDS
        )
        channel.handshake_open(
            f"127.0.0.1:{address.port}", address.path, timer
        )
        return channel


# Returns the WSL path of a Windows path, as wslpath maps it.
def path_wsl(windows_path: str) -> str:
    output = devtools.command_run(
        f"wslpath mapping {windows_path}",
        ["wslpath", "-u", windows_path],
        None,
        _COMMAND_WAIT_SECONDS,
    )
    return output.strip()
