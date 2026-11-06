// The browser's MCP tools, exactly those of API/mcp/tools.json in its order,
// registered on the AI worker's server and run inside the task of the `mcp`
// line. No tool exposes the backing store beyond routine SQL: no measure, no
// VACUUM, no unloading or loading of a copy, no `seq`. kv_get and doc_get read
// this side's store only. render shows the image and the subtitle and frees
// nothing.
//
// console_run, console_write and console_read work in debug mode only, else
// throw `tools_browser.debug_off`. Each asks its permit and shows the console,
// so that the player watches the command and types once it is over. A turn on
// tty 0 runs from `console.busy` to `console.idle`: console_write starts it at
// its first write and returns `{}` at once, and a read whose output ends with
// the prompt ends it. The writer starts the turn once tty 0's last command has
// concluded, the AI's lines and reads waiting until then. console_read reads
// from where the last read of the turn ended, and returns the output with LF
// line ends and whether it timed out. console_run starts a turn when none is
// on and ends it when its read ends; its wait for the turn counts against its
// timeout, past which it returns timed out with nothing typed. A tool that
// throws fails the server as `mcp.d.ts` says, its own message kept.

declare namespace tools_browser {
  function tools_register(
    server: mcp.Server,
    store: substrate.Store,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo,
    settings_get: (id: string) => unknown,
    debug_on: () => boolean,
  ): void;
}
