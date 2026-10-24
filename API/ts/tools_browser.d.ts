// The browser's MCP tools, exactly those of API/mcp/tools.json in its order,
// registered on the AI worker's server and run through the store inside the
// task of the `mcp` line. kv_get returns the value as text, every other tool
// the JSON text of its result: sql_run `{results}`, kv_put `{sha256}`,
// kv_delete, db_create and db_drop `{}`. No tool exposes the backing store
// beyond routine SQL: no measure, no VACUUM, no unloading or loading of a
// copy, no `seq`. kv_get and doc_get read this side's store only, a lost
// cache file failing as `substrate.file_lost`. render shows the image and
// the subtitle and frees nothing.
//
// console_run, in debug mode, asks the player's permit unless it was always
// allowed, then submits `console.show` to the UI and sleeps on
// `tools.show_reply`, then types the command into tty 0 and sleeps on its
// output. Outside debug mode it throws `tools_browser.debug_off`. Every line
// a tool builds takes the form `settings.names_full()` picks. A tool that
// throws, before or after it submitted a request, fails the server as
// `mcp.d.ts` says, its own message kept.

declare namespace tools_browser {
  function tools_register(
    server: mcp.Server,
    store: substrate.Store,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo,
    settings_get: (id: string) => unknown,
  ): void;
}
