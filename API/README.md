# API

The external API of every module HYPE-2.md names, before any is written.
Nothing here runs. A file changes only when HYPE-2.md changes with it.

- `python/*.pyi`: the public names of each Python module, as stub files.
  A handler module lists one function per JSLB line type it serves, with
  the payload as keyword parameters, which is how `dispatch` calls it.
- `ts/*.d.ts`: the public surface of each TypeScript module. Each module
  is one frozen object named after it, so each file is one `declare
  namespace`. `lines.d.ts` is the catalogue of every JSLB line type on
  every lane, with its direction, blobs and reply; it is the wire API.
- `sql/*.sql`: the DDL the engine applies. `engine.sql` goes into every
  database; `metaverse.sql` and `log.sql` add their tables. Universe and
  region databases get only `engine.sql`; the rest is the AI's DDL.
- `mcp/tools.json`: what `tools/list` returns, browser and server tools,
  as JSON-RPC results. The `_meta.xsjs.permit` flag marks a tool the UI
  must confirm.
- `settings.json`: the proposed v0 of the top-level file the server reads
  and injects into the page unmodified.

Lanes, as `lines.d.ts` names them:

```text
wire     AI worker  <->  server         bytes over ttyd's WebSocket
ui-ai    UI thread  <->  AI worker      structured clone, buffers moved
ai-wasm  AI worker  <->  WASM worker    structured clone, buffers moved
mcp      agent      <->  MCP server     JSON-RPC 2.0, see ts/mcp.d.ts
http     agent      <->  provider       HTTPS, see ts/provider.d.ts
```
