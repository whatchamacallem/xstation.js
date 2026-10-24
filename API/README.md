# API

No code was written by the maintainer.

The external API of every module TAP_PLAN.md names, before any is written.
Nothing here runs. A file changes only when TAP_PLAN.md changes with it.

- `python/*.pyi`: the public names of each Python module, as stub
  files. A handler module lists one function per
  JSLB line type it serves, with the payload as keyword parameters,
  which is how `dispatch` calls it.
- `ts/*.d.ts`: the public surface of each TypeScript module. Each module
  is one frozen object named after it, so each file is one `declare
  namespace`. `lines.d.ts` is the catalogue of every JSLB line type on
  every lane, with its direction, blobs and reply; it is the wire API.
- `sql/*.sql`: the DDL the engine applies. `substrate.sql` is created on
  first use in every database the substrate opens; `metaverse.sql` adds
  the one fixed experience table and its triggers; `verbose.sql` is the
  server's `_verbose` database. Every other table is the scripts'.
- `mcp/tools.json`: what `tools/list` returns, browser and server tools,
  as JSON-RPC results. The `_meta.xsjs.permit` flag marks a tool the UI
  must confirm.
- `settings.json`: kept equal to the top-level `settings.json`, which the
  server reads and sends in `tap.start` unmodified. It also holds the
  constants of the PowerShell scripts, under `powershell`. The test suite
  settings and the gold record of expected test results are the top-level
  `test_settings.json`, sent after the settings in debug mode.

Lanes, as `lines.d.ts` names them:

```text
wire     AI worker  <->  server         bytes over tty 1
console  AI worker  <->  ttyd's dash    ttyd's protocol over tty 0
ui-ai    UI thread  <->  AI worker      structured clone, buffers moved
mcp      agent      <->  MCP server     JSON-RPC 2.0, see ts/mcp.d.ts
http     any        <->  HTTP port      one fetch per line, see ts/http.d.ts
```

## The first line

The server's first line is `tap.start`, a request with the fixed id 101,
carrying the settings and, in debug mode, the test settings. The AI worker
answers it with an Empty reply. Every later request of the server takes its
id from `dispatch.id_next`, which starts at 102 in both languages. No
program but the test suites runs: the bring up is a TAP run, see
TAP_PLAN.md.

## Name forms

A header field has a short name, `t`, and a full name, `type`. One
function chooses the form of every line a thread builds:
`settings.names_full()`, true until the settings are set, then the setting
`debug`. Code that can run before the settings exist, such as the error
overlay's `fault` line, always uses the full names. A reply takes the form
of the line it answers. Payload keys are always full English words; only
the header fields have single letter names.

## The store protocol

The databases are filesystem accelerators an AI talks to easily, not
replicas. Each store, the browser's and the server's, does its own
maintenance: only the browser compacts turns, and no maintenance crosses
the wire. Each modifying operation the browser's store commits goes to the
server as a plain push line of the same type, which the server applies to
its own store through the same methods as any caller: no sequence number,
no ordering, no consistency check, no reply. A line lost to a connection
loss stays lost, and the server may hold more history than the browser.
Whole databases move only as blobs: `db.restore` carries the database
file, and one `db.file` line after it per cache file its rows name and the
sender holds. A store tolerates a lost cache file: the row stays and a read
of it fails loud with `substrate.file_lost`.

The protocol names operations, never the storage: refs, documents, turns,
SQL statements as text, and whole databases as opaque blobs. Replacing the
database with another kind of backing store changes no line type and no
payload. No tool exposes the backing store beyond routine SQL.

## Bad numbers

The JSLB decoders of both languages are the single door for bad numbers.
At read they refuse an integer token beyond 2^53 either way and a number
token that overflows a double. `jslb.json_decode` applies the same rules to
JSON read from anywhere else. No other layer checks a number. A document
version past 2^53 is the AI's problem over the MCP.

## Errors

A cascading failure is one object: each `error` line, `fault` line and MCP
error result holds the latest failure's `message` and `stack`, and under
`cause` the failure before it, nested, the first failure innermost. The key
is always the full word `cause`. An exception in an MCP request answers
that request, a tool's as an `isError` result, then the server fails.
