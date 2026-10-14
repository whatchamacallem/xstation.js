# xstation.js (Cross-Station JS, xsjs)

These are the user facing scripts. The remaining scripts are for interested
developers.

The supported checkout for Windows users is `C:\src`. Windows' RemoteSigned
execution policy refuses the scripts from a `\\wsl.localhost` path.

## xsjs_install.ps1

`.\xsjs_install.ps1` (admin)

- Ensures WinGet and its PowerShell module work.
- Ensures ttyd is installed, up to date and working.
- Ensures WSL and Ubuntu are installed.
- Ensures Python 3 and OpenSSL are installed in Linux.

## xsjs_start.ps1

`.\xsjs_start.ps1 [username:password]` (admin)

- Serves `bootstrap.py` with ttyd on port 5768.
- Serves localhost over HTTP, or the network over HTTPS with a password.
- Makes a self-signed TLS certificate and opens the firewall for HTTPS.
- Starts ttyd serving from WSL on Windows sign-in.

## xsjs_stop.ps1

`.\xsjs_stop.ps1 [--softly]` (admin)

- Stops ttyd, but keeps the TLS certificate.
- Removes the sign-in task, firewall rule and saved password, unless
  `--softly`.

## xsjs_status.ps1

`.\xsjs_status.ps1`

- Reports whether ttyd is running and starts at sign-in.
- Lists the task, processes, port, firewall rule, WSL and certificate.
- Changes nothing.
