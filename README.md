# xstation.js (Cross-Station JS, xsjs)

No code was written by the maintainer.

These are the user facing scripts. The remaining scripts are for interested
developers.

The supported checkout for Windows users is `C:\src`. Windows' RemoteSigned
execution policy refuses the scripts from a `\\wsl.localhost` path.

## xsjs_install.ps1

`.\xsjs_install.ps1` (admin)

- Ensures WSL and Ubuntu are installed.
- Ensures Python 3 and OpenSSL are installed in Linux with apt.
- Builds ttyd in Linux from its pinned source release and patches, after
  checking for the tools and headers the build needs.
- Reports a ttyd for Windows from an earlier install, which is no longer
  used and stays installed.

## xsjs_start.ps1

`.\xsjs_start.ps1 [username:password]` (admin)

- Copies the ttyd that `xsjs_install.ps1` built, the server's Python
  modules and seeds, `i18n/en-US.json`, `settings.json`,
  `test_settings.json`, `provider.json` and the page,
  `build/hyperposition-engine.html`, to `~/.cache/xsjs/` in WSL on each
  run.
- Serves them with ttyd in WSL on 127.0.0.1:5769, which a Windows port
  proxy forwards from port 5768.
- Serves localhost over HTTP, or the network over HTTPS with a password.
- Makes a self-signed TLS certificate and opens the firewall for HTTPS.
- Starts ttyd in WSL on Windows sign-in.

## xsjs_stop.ps1

`.\xsjs_stop.ps1 [--softly]` (admin)

- Stops the ttyd it started in WSL, but keeps the TLS certificate and
  `~/.cache/xsjs/`.
- Removes the sign-in task, port proxy, firewall rule and saved password,
  unless `--softly`.

## xsjs_status.ps1

`.\xsjs_status.ps1`

- Reports whether ttyd is running and starts at sign-in.
- Lists the task, ttyd in WSL, ports 5768 and 5769, firewall rule, port
  proxies, WSL and certificate.
- Changes nothing.
