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
// `tools.show_reply`, then notifies tty 0's writer `console.busy`, types the
// command into tty 0 and sleeps on its output, and notifies `console.idle`
// when the read ends, so that the player watches the command and types once it
// is over. console_write and console_read ask their own permits and show the
// console as console_run does. console_write notifies `console.busy` to tty
// 0's writer at the first write of a turn, sends its text as one
// `console.write` to the writer, which types each line a newline ends and
// holds the rest, and returns `{}` at once. The writer starts the turn, its
// busy to the UI, once tty 0's last command has concluded, the AI's lines and
// reads waiting until then. console_read reads to its text or its timeout,
// from where the last read of the turn ended, or from the turn's start in a
// turn that waits, and returns the output with LF line ends and whether it
// timed out; a read whose output ends with the prompt ends the turn with
// `console.idle` to the writer, which posts it to the UI. console_run starts a
// turn when none is on, types its command line within it, and ends the turn
// when its read ends; its wait for the turn counts against its timeout, past
// which it returns timed out with no output and nothing typed. Outside debug
// mode each of the three throws `tools_browser.debug_off`. Every line a tool
// builds takes the form `settings.names_full()` picks. A tool that throws,
// before or after it submitted a request, fails the server as `mcp.d.ts` says,
// its own message kept.

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
