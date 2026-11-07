# Chrome, or else Edge, on Windows from WSL, a `devtools.Transport`. WSL's NAT
# networking can't reach Windows' 127.0.0.1, where Chrome serves DevTools, so
# a relay in `powershell.exe` carries the WebSocket over its stdin and stdout.
# WindowsRelay is offline since 2026-10-30, kept, run by nothing, and to be
# brought back later. Its one suite, test_devtools_powershell.py, is a later
# suite, so no run counts this module's lines until that suite comes back.
# The relay's helpers that a running suite tests stay in devtools.py, which
# this module imports.

import devtools, subprocess

# Chrome, or else Edge, on Windows, through a relay in `powershell.exe`.
class WindowsRelay:
    # WSL forwards a new listener to Windows late, so a refusal is sent again.
    refused_retried: bool
    # Finds `powershell.exe` on the PATH, starting nothing yet.
    def __init__(self) -> None: ...
    # Starts the browser on a new profile and opens a relay to its DevTools.
    def transport_open(
        self, width_px: int, height_px: int
    ) -> devtools.SocketChannel: ...
    # Stops the browser and the relay, then removes the profile.
    def transport_close(self) -> None: ...
    # Returns what the script printed in PowerShell, as `UTF-8`.
    def powershell_run(self, what: str, script: str) -> str: ...
    # Returns the WSL path of the first browser installed.
    def browser_find(self, environment: dict[str, str | None]) -> str: ...
    # Returns the DevTools port and path once the browser has written them.
    def devtools_wait(self) -> devtools.EndpointAddress: ...
    # Waits for the process to exit, killing it and failing if it takes long.
    def process_wait(
        self, what: str, process: subprocess.Popen[bytes]
    ) -> None: ...
    # Stops the browser, which outlives its WSL side and holds the profile.
    def browser_stop(self) -> None: ...
    # Ends the relay, which exits once its connection or its input ends.
    def relay_stop(self) -> None: ...
    # Removes the profile, waiting while browser helpers still hold its files.
    def profile_remove(self) -> None: ...
