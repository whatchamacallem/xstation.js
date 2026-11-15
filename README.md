# xstation.js (Cross-Station JS, xsjs)

No code was written by the maintainer.

These are the user facing scripts. The remaining scripts are for interested
developers.

The supported checkout for Windows users is `C:\src`. Windows' RemoteSigned
execution policy refuses the scripts from a `\\wsl.localhost` path.

Everything runs in the wslc container `hype`, made by hand, as its user
`t`, in its checkout `/home/t/xstation.js`. It must mount the checkout's
parent folder where WSL mounts it and publish port 5768 on Windows'
127.0.0.1; `.\powershell\test_wslc.ps1` makes it so when there is no
`hype`, from the image `hype-base:2026-11-13`. No script needs
administrator.

## xsjs_start.ps1

`.\xsjs_start.ps1 [--debug] [--verbose]`

- Makes `hype`'s checkout a copy of this one with `wslc_sync.sh`.
- Runs `python3 python/xsjs_serve.py` there in the background, which builds
  the page, makes the root `~/.cache/xsjs/root` and serves it through ttyd
  on the container's port 5768, its log `~/.cache/xsjs/ttyd.log`.
- `--debug` runs the page in debug mode, which the console needs,
  `--verbose` the console's shell at verbose level 2; each is off unless
  given.
- Serves `http://localhost:5768/` to Windows alone, through the port `hype`
  publishes on 127.0.0.1.

## xsjs_stop.ps1

`.\xsjs_stop.ps1`

- Stops the serve program and its ttyd, but keeps `hype` and its root.

## xsjs_status.ps1

`.\xsjs_status.ps1`

- Reports whether the serve program runs, `hype`'s state and published
  ports, and what listens on port 5768 in Windows.
- Changes nothing.
