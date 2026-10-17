# DATA

Synthetic transcripts of the engine's standard communication, written by
`transcripts_make.py` from the API in API/ and the design in HYPE-2.md.
Nothing here was recorded from a running system.

```text
python3 DATA/transcripts_make.py
```

Each `.txt` is one scenario. A line is `NNNN FROM->TO message`; a `#`
line is a note. The message is the JSLB line exactly as its encoder would
write it, without the CR, and with its blobs replaced by `<N blobs>`
after the line. On the wire each message also carries ttyd's `0` prefix,
not shown. Sizes and SHA-256 values are computed from the synthetic bytes
the blob would hold; pids, the tab id, URLs and timestamps are
placeholders.

The parties:

```text
UI           the main thread           AI       the AI worker
WASM         the WASM worker           SERVER   bootstrap.py
TTYD         ttyd                      BROWSER  the tab's HTTP client
AGENT        the agent loop in AI      MCP_BROWSER  the MCP server in AI
PROVIDER     the AI provider, HTTPS    CLIENT, STDIO  an MCP stdio session
```

- `01_boot.txt`: a new tab: the page, the workers, ttyd's protocol, the
  hello, the first replication, the MCP sessions, the hyperposition.
- `02_turn.txt`: the player answers `1`; the scripted provider creates a
  universe and a region with DDL, makes an image, writes the scene,
  enters it, and the turn is stored, rendered and replicated.
- `03_console.txt`: debug mode, so full header names; the user opens the
  console, then the AI runs a command through it after Accept.
- `04_fault_reconnect.txt`: a handler fault, the one error line, the
  exit, the 1006, the fault display, Reconnect and reconciliation.
- `05_sync.txt`: a push after a write, a pull after a server-side change
  from an external client, and a streamed value over `overflow_bytes`.
- `06_tap.txt`: a browser test run's TAP stream checked by the server.
- `07_mcp_stdio.txt`: an external agent over the MCP stdio transport.
