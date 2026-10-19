# DATA

Synthetic transcripts of the engine's standard communication, written by
`transcripts_make.py` from the API in API/ and the design in R4.md.
Nothing here was recorded from a running system.

```text
python3 DATA/transcripts_make.py
```

Each `.txt` is one scenario. A line is `NNNN FROM->TO message`; a `#`
line is a note. The message is the JSLB line rendered as R4.md 3.11: the
JSON text exactly as its encoder writes it, without the CR, followed by
one `<blob "n"=K>` tag per blob, K the blob header's key. On the wire
each message also carries ttyd's `0` prefix, not shown. Sizes and SHA-256
values are computed from the synthetic bytes the blob would hold; pids,
URLs, ids and timestamps are placeholders.

The parties:

```text
UI       the main thread            AI      the AI worker
SERVER   bootstrap.py on tty 1      TTYD    ttyd
BROWSER  the tab's HTTP client      SCRIPT  the scripted provider port
AGENT    the agent loop in AI       MCP     the browser's MCP server in AI
CLIENT   an external MCP client     STDIO   mcp_stdio.py
```

A line from AI to AI is a wake the task manager enqueued for a sleeping
task (R4.md 4.2); together with the lines around it, the queue log is the
timeline of the thread.

- `01_boot.txt`: a new tab: the page, the worker, ttyd's protocol, the
  hello, the settings, the databases replaced from the server, the MCP
  sessions, the hyperposition.
- `02_turn.txt`: the player answers `1`; the scripted provider runs the
  bootstrap script, which makes a universe, a world and a region, then
  makes an image, writes a scene, enters it and renders; every
  modification is forwarded to the server as it commits.
- `03_console.txt`: debug mode, so full header names; the user opens the
  console on tty 0, then the AI runs a command through it after Accept.
- `04_fault_reload.txt`: a handler fault, the one error line, the exit,
  the close, the overlay, Reload.
- `05_sync.txt`: a modification from the UI thread forwarded through the
  AI worker, a value over `overflow_bytes` streamed, a desync refused and
  the reload that follows.
- `06_tap.txt`: a browser test run's TAP lines, each its own line.
- `07_mcp_stdio.txt`: an external agent over the MCP stdio transport.
- `08_script.txt`: the AI edits a script, runs it, and debugs it.
