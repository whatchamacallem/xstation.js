# API

The external API of every module R4.md names, before any is written.
Nothing here runs. A file changes only when R4.md changes with it.

- `python/*.pyi` and `python/tap/*.pyi`: the public names of each
  Python module, as stub files. A handler module lists one function per
  JSLB line type it serves, with the payload as keyword parameters,
  which is how `dispatch` calls it.
- `ts/*.d.ts`: the public surface of each TypeScript module. Each module
  is one frozen object named after it, so each file is one `declare
  namespace`. `lines.d.ts` is the catalogue of every JSLB line type on
  every lane, with its direction, blobs and reply; it is the wire API.
- `sql/*.sql`: the DDL the engine applies. `substrate.sql` is created on
  first use in every database the substrate opens; `metaverse.sql` adds
  the one fixed experience table; `verbose.sql` is the server's
  `_verbose` database. Every other table is the scripts'.
- `mcp/tools.json`: what `tools/list` returns, browser and server tools,
  as JSON-RPC results. The `_meta.xsjs.permit` flag marks a tool the UI
  must confirm.
- `settings.json`: the proposed v0 of the top-level file the server reads
  and sends in `hello` unmodified.

Lanes, as `lines.d.ts` names them:

```text
wire     AI worker  <->  server         bytes over tty 1
console  AI worker  <->  ttyd's dash    ttyd's protocol over tty 0
ui-ai    UI thread  <->  AI worker      structured clone, buffers moved
mcp      agent      <->  MCP server     JSON-RPC 2.0, see ts/mcp.d.ts
http     any        <->  HTTP port      one fetch per line, see ts/http.d.ts
```
