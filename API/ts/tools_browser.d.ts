declare namespace tools_browser {
  // Registers the browser's tools of API/mcp/tools.json on the server:
  // sql_run, db_create, db_drop, kv_get, kv_put, kv_delete, kv_list,
  // doc_get, doc_put, doc_head, script_run, script_debug, image_make,
  // render, console_run, verbose_level, verbose_tail. Each runs through
  // the store inside the task; image_make, render and console_run
  // return a sleep.
  function tools_register(
    server: mcp.Server,
    store: substrate.Store,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo
  ): void;
}
