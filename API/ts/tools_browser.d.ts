declare namespace tools_browser {
  // Registers the browser's tools of API/mcp/tools.json on the server:
  // sql_run, universe_create, region_create, doc_get, doc_put, doc_head,
  // kv_list, scene_enter, image_make, render. Each runs through the store
  // proxy and the task queue; `image_make` uses the provider and
  // `media.fetch`; the two create tools also `db.open` on the server.
  function tools_register(
    server: mcp.Server,
    store: substrate.StoreProxy,
    tasks: queue.TaskQueue,
    model: provider.Provider,
    image_model: string
  ): void;

  // Runs the permission flow for a tool marked `permit`: `permit.ask` to
  // the UI, then waits for `permit.answer`. Resolves false on deny.
  function permit_run(tasks: queue.TaskQueue, tool: string, input: unknown): Promise<boolean>;
}
